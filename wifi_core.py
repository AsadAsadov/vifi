from __future__ import annotations

import locale
import platform
import re
import socket
import statistics
import subprocess
from dataclasses import dataclass, field
from typing import Iterable


IS_WINDOWS = platform.system() == "Windows"
CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0


class DiagnosticError(RuntimeError):
    """Raised when a Windows diagnostic command cannot be completed."""


@dataclass(slots=True)
class WifiNetwork:
    ssid: str
    bssid: str = ""
    signal: int | None = None
    channel: int | None = None
    authentication: str = ""
    encryption: str = ""
    radio_type: str = ""

    @property
    def security(self) -> str:
        values = [value for value in (self.authentication, self.encryption) if value]
        return " / ".join(values) if values else "Naməlum"


@dataclass(slots=True)
class ConnectionInfo:
    connected: bool = False
    ssid: str = ""
    bssid: str = ""
    signal: int | None = None


@dataclass(slots=True)
class PingResult:
    target: str
    sent: int
    received: int
    loss_percent: float
    average_ms: float | None
    samples_ms: list[int] = field(default_factory=list)
    error: str = ""


@dataclass(slots=True)
class DiagnosticReport:
    connection: ConnectionInfo
    gateway: str
    gateway_ping: PingResult
    internet_ping: PingResult
    dns_ok: bool
    dns_address: str
    tcp_ok: bool
    findings: list[str]


def _decode_windows_output(raw: bytes) -> str:
    encodings: Iterable[str] = (
        locale.getpreferredencoding(False),
        "utf-8",
        "cp1254",
        "cp1251",
        "cp866",
    )
    for encoding in dict.fromkeys(encodings):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode(errors="replace")


def run_command(args: list[str], timeout: int = 25) -> str:
    if not IS_WINDOWS:
        raise DiagnosticError("Bu əməliyyat yalnız Windows-da işləyir.")

    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            check=False,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
    except FileNotFoundError as exc:
        raise DiagnosticError(f"Sistem əmri tapılmadı: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise DiagnosticError("Sistem əmri vaxt limitini keçdi.") from exc

    stdout = _decode_windows_output(completed.stdout)
    stderr = _decode_windows_output(completed.stderr)
    if completed.returncode not in (0, 1) and not stdout.strip():
        raise DiagnosticError(stderr.strip() or "Sistem əmri uğursuz oldu.")
    return stdout


def _value_after_colon(line: str) -> tuple[str, str]:
    if ":" not in line:
        return "", ""
    key, value = line.split(":", 1)
    return key.strip().lower(), value.strip()


def parse_networks(output: str) -> list[WifiNetwork]:
    networks: list[WifiNetwork] = []
    current_ssid = ""
    current_auth = ""
    current_encryption = ""
    current_bss: WifiNetwork | None = None

    channel_words = ("channel", "kanal", "канал", "canal")
    radio_words = ("radio", "радио")
    encryption_words = ("encryption", "şifr", "шифр", "cipher")
    auth_words = ("authentication", "doğrul", "kimlik", "провер", "auth")

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        ssid_match = re.match(r"^SSID\s+\d+\s*:\s*(.*)$", line, re.IGNORECASE)
        if ssid_match:
            current_ssid = ssid_match.group(1).strip() or "<Gizli şəbəkə>"
            current_auth = ""
            current_encryption = ""
            current_bss = None
            continue

        bssid_match = re.match(
            r"^BSSID\s+\d+\s*:\s*([0-9a-f:-]+)$",
            line,
            re.IGNORECASE,
        )
        if bssid_match and current_ssid:
            current_bss = WifiNetwork(
                ssid=current_ssid,
                bssid=bssid_match.group(1),
                authentication=current_auth,
                encryption=current_encryption,
            )
            networks.append(current_bss)
            continue

        key, value = _value_after_colon(line)
        if not value:
            continue

        key_lower = key.casefold()
        value_upper = value.upper()

        if current_bss is None:
            if any(word in key_lower for word in auth_words) or any(
                token in value_upper for token in ("WPA", "WEP", "OPEN")
            ):
                current_auth = value
            elif any(word in key_lower for word in encryption_words) or any(
                token in value_upper for token in ("CCMP", "TKIP", "AES")
            ):
                current_encryption = value
            continue

        signal_match = re.search(r"(\d{1,3})\s*%", value)
        if signal_match and current_bss.signal is None:
            current_bss.signal = min(100, int(signal_match.group(1)))
            continue

        if any(word in key_lower for word in channel_words):
            channel_match = re.search(r"\d+", value)
            if channel_match:
                current_bss.channel = int(channel_match.group())
            continue

        if any(word in key_lower for word in radio_words):
            current_bss.radio_type = value

    return sorted(
        networks,
        key=lambda item: item.signal if item.signal is not None else -1,
        reverse=True,
    )


def scan_wifi_networks() -> list[WifiNetwork]:
    output = run_command(["netsh", "wlan", "show", "networks", "mode=bssid"])
    return parse_networks(output)


def parse_connection(output: str) -> ConnectionInfo:
    info = ConnectionInfo()
    connected_words = ("connected", "qoşul", "bağlı", "подключ")

    for raw_line in output.splitlines():
        line = raw_line.strip()
        key, value = _value_after_colon(line)
        if not key:
            continue

        key_folded = key.casefold()
        value_folded = value.casefold()

        if key_folded == "ssid":
            info.ssid = value
        elif key_folded == "bssid":
            info.bssid = value
        elif any(word in key_folded for word in ("state", "status", "vəziyyət", "состоя")):
            info.connected = any(word in value_folded for word in connected_words)
        elif "%" in value:
            signal_match = re.search(r"(\d{1,3})\s*%", value)
            if signal_match:
                info.signal = min(100, int(signal_match.group(1)))

    if info.ssid and not info.connected:
        info.connected = True
    return info


def get_current_connection() -> ConnectionInfo:
    return parse_connection(run_command(["netsh", "wlan", "show", "interfaces"]))


def get_default_gateway() -> str:
    command = (
        "$route = Get-NetRoute -DestinationPrefix '0.0.0.0/0' "
        "| Where-Object {$_.NextHop -ne '0.0.0.0'} "
        "| Sort-Object RouteMetric,InterfaceMetric "
        "| Select-Object -First 1 -ExpandProperty NextHop; "
        "if ($route) {$route}"
    )
    output = run_command(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        timeout=15,
    )
    for line in output.splitlines():
        candidate = line.strip()
        try:
            socket.inet_aton(candidate)
        except OSError:
            continue
        return candidate
    return ""


def parse_ping_output(target: str, output: str, sent: int) -> PingResult:
    ttl_hits = re.findall(r"\bTTL\s*[=:]\s*\d+", output, re.IGNORECASE)
    samples = [
        int(value)
        for value in re.findall(r"[=<]\s*(\d+)\s*ms\b", output, re.IGNORECASE)
    ]
    received = min(sent, max(len(ttl_hits), len(samples)))
    loss = 100.0 if sent <= 0 else round((sent - received) * 100 / sent, 1)
    average = round(statistics.fmean(samples), 1) if samples else None
    return PingResult(
        target=target,
        sent=sent,
        received=received,
        loss_percent=loss,
        average_ms=average,
        samples_ms=samples,
    )


def ping_target(target: str, count: int = 4, timeout_ms: int = 1200) -> PingResult:
    if not target:
        return PingResult("", count, 0, 100.0, None, error="Hədəf yoxdur.")
    try:
        output = run_command(
            ["ping", "-n", str(count), "-w", str(timeout_ms), target],
            timeout=max(10, count * timeout_ms // 1000 + 5),
        )
    except DiagnosticError as exc:
        return PingResult(target, count, 0, 100.0, None, error=str(exc))
    return parse_ping_output(target, output, count)


def resolve_dns(hostname: str = "example.com") -> tuple[bool, str]:
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(4)
    try:
        return True, socket.gethostbyname(hostname)
    except OSError:
        return False, ""
    finally:
        socket.setdefaulttimeout(old_timeout)


def tcp_probe(host: str = "1.1.1.1", port: int = 443) -> bool:
    try:
        with socket.create_connection((host, port), timeout=4):
            return True
    except OSError:
        return False


def summarize_findings(
    connection: ConnectionInfo,
    gateway: str,
    gateway_ping: PingResult,
    internet_ping: PingResult,
    dns_ok: bool,
    tcp_ok: bool,
) -> list[str]:
    findings: list[str] = []

    if not connection.connected:
        return ["KRİTİK: Kompüter Wi‑Fi şəbəkəsinə qoşulu deyil."]

    if connection.signal is not None:
        if connection.signal < 35:
            findings.append("KRİTİK: Wi‑Fi siqnalı çox zəifdir.")
        elif connection.signal < 55:
            findings.append("XƏBƏRDARLIQ: Wi‑Fi siqnalı zəifdir.")

    if not gateway:
        findings.append("KRİTİK: Default gateway tapılmadı; IP/DHCP problemi ola bilər.")
        return findings

    if gateway_ping.loss_percent >= 100:
        findings.append(
            "KRİTİK: Modemə/gateway-ə cavab yoxdur; Wi‑Fi, LAN və ya modem problemi ehtimalı yüksəkdir."
        )
        return findings

    if gateway_ping.loss_percent > 5:
        findings.append(
            "XƏBƏRDARLIQ: Lokal bağlantıda paket itkisi var; Wi‑Fi maneəsi və ya LAN kabelini yoxla."
        )

    if internet_ping.loss_percent >= 100 and not tcp_ok:
        findings.append(
            "KRİTİK: Modem cavab verir, internet çıxışı yoxdur; WAN/PPPoE/provayder tərəfini yoxla."
        )
    elif internet_ping.loss_percent > 20:
        findings.append("XƏBƏRDARLIQ: İnternet istiqamətində yüksək paket itkisi var.")
    elif internet_ping.loss_percent >= 100 and tcp_ok:
        findings.append("MƏLUMAT: İnternet işləyir, amma ICMP/ping bloklanmış ola bilər.")

    if (internet_ping.received > 0 or tcp_ok) and not dns_ok:
        findings.append("KRİTİK: İnternet çıxışı var, DNS sorğusu işləmir.")

    if not findings:
        findings.append("NORMAL: Əsas Wi‑Fi, gateway, internet və DNS testləri qaydasındadır.")
    return findings


def collect_diagnostics() -> DiagnosticReport:
    connection = get_current_connection()
    gateway = get_default_gateway()
    gateway_ping = ping_target(gateway)
    internet_ping = ping_target("1.1.1.1")
    dns_ok, dns_address = resolve_dns()
    tcp_ok = tcp_probe()
    findings = summarize_findings(
        connection,
        gateway,
        gateway_ping,
        internet_ping,
        dns_ok,
        tcp_ok,
    )
    return DiagnosticReport(
        connection=connection,
        gateway=gateway,
        gateway_ping=gateway_ping,
        internet_ping=internet_ping,
        dns_ok=dns_ok,
        dns_address=dns_address,
        tcp_ok=tcp_ok,
        findings=findings,
    )


def optical_assessment(rx_dbm: float | None, los_active: bool) -> tuple[str, str]:
    if los_active:
        return "KRİTİK", "LOS aktivdir. Fiber xətti, konnektor və qaynaq nöqtələrini yoxla."
    if rx_dbm is None:
        return "MƏLUMAT", "Optik RX dəyərini ONT/modem panelindən daxil et."
    if rx_dbm > -8:
        return "XƏBƏRDARLIQ", "Optik siqnal həddən artıq güclü ola bilər."
    if rx_dbm >= -25:
        return "NORMAL", "Optik RX ümumi GPON orientirinə görə normal aralıqdadır."
    if rx_dbm >= -27:
        return "XƏBƏRDARLIQ", "Optik RX zəifdir; konnektor, bükülmə və qaynaq itkisini yoxla."
    return "KRİTİK", "Optik RX çox zəifdir; xətt qırılması və ya yüksək itki ehtimalı var."


def format_ping(result: PingResult) -> str:
    average = "—" if result.average_ms is None else f"{result.average_ms:.1f} ms"
    return (
        f"{result.target or '—'} | qəbul {result.received}/{result.sent} | "
        f"itki {result.loss_percent:.1f}% | orta {average}"
    )


def format_report(report: DiagnosticReport) -> str:
    signal = "—" if report.connection.signal is None else f"{report.connection.signal}%"
    lines = [
        "Wİ-Fİ VƏ ŞƏBƏKƏ DİAQNOSTİKA HESABATI",
        "=" * 44,
        f"Qoşulma: {'Bəli' if report.connection.connected else 'Xeyr'}",
        f"SSID: {report.connection.ssid or '—'}",
        f"BSSID: {report.connection.bssid or '—'}",
        f"Wi‑Fi siqnalı: {signal}",
        f"Gateway: {report.gateway or '—'}",
        f"Gateway ping: {format_ping(report.gateway_ping)}",
        f"İnternet ping: {format_ping(report.internet_ping)}",
        f"TCP 443 testi: {'Uğurlu' if report.tcp_ok else 'Uğursuz'}",
        f"DNS testi: {'Uğurlu' if report.dns_ok else 'Uğursuz'}"
        + (f" ({report.dns_address})" if report.dns_address else ""),
        "",
        "NƏTİCƏ",
        "-" * 44,
        *report.findings,
        "",
        "Qeyd: Fiziki fiber qırılmasının yerini müəyyənləşdirmək üçün OTDR lazımdır.",
    ]
    return "\n".join(lines)
