from __future__ import annotations

import datetime as dt
import platform
import threading
import webbrowser
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    BooleanVar,
    StringVar,
    Text,
    Tk,
    filedialog,
    messagebox,
    ttk,
)

import wifi_core


APP_NAME = "Wi‑Fi Texnik"
APP_VERSION = "1.0.0"


class WifiTechnicianApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("1120x730")
        self.root.minsize(900, 620)

        self.status = StringVar(value="Hazırdır")
        self.rx_value = StringVar()
        self.los_active = BooleanVar(value=False)
        self.last_gateway = ""
        self.last_report = ""

        self._configure_style()
        self._build_header()
        self._build_tabs()
        self._build_statusbar()

        if platform.system() != "Windows":
            self.status.set("Bu tətbiqin şəbəkə əmrləri yalnız Windows-da işləyir.")

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#101723", foreground="#E8EEF7", font=("Segoe UI", 10))
        style.configure("TFrame", background="#101723")
        style.configure("Card.TFrame", background="#172131")
        style.configure("TLabel", background="#101723", foreground="#E8EEF7")
        style.configure(
            "Title.TLabel",
            background="#101723",
            foreground="#FFFFFF",
            font=("Segoe UI Semibold", 20),
        )
        style.configure(
            "Muted.TLabel",
            background="#101723",
            foreground="#91A0B5",
        )
        style.configure(
            "Card.TLabel",
            background="#172131",
            foreground="#E8EEF7",
        )
        style.configure(
            "Accent.TButton",
            background="#1E88E5",
            foreground="#FFFFFF",
            padding=(16, 9),
            font=("Segoe UI Semibold", 10),
        )
        style.map("Accent.TButton", background=[("active", "#42A5F5")])
        style.configure("TButton", padding=(12, 8))
        style.configure("TNotebook", background="#101723", borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background="#172131",
            foreground="#AEBBD0",
            padding=(18, 10),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#23344B")],
            foreground=[("selected", "#FFFFFF")],
        )
        style.configure(
            "Treeview",
            background="#131D2B",
            fieldbackground="#131D2B",
            foreground="#E8EEF7",
            rowheight=30,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background="#23344B",
            foreground="#FFFFFF",
            font=("Segoe UI Semibold", 10),
        )
        style.map("Treeview", background=[("selected", "#1E5F99")])
        style.configure("TEntry", fieldbackground="#0D1520", foreground="#FFFFFF")
        style.configure("TCheckbutton", background="#172131", foreground="#E8EEF7")

    def _build_header(self) -> None:
        header = ttk.Frame(self.root, padding=(22, 18, 22, 12))
        header.pack(fill="x")
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Windows üçün lokal Wi‑Fi və internet diaqnostikası",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(3, 0))

    def _build_tabs(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=BOTH, expand=True, padx=20, pady=(0, 14))

        wifi_tab = ttk.Frame(notebook, padding=16)
        diagnostic_tab = ttk.Frame(notebook, padding=16)
        gpon_tab = ttk.Frame(notebook, padding=16)
        info_tab = ttk.Frame(notebook, padding=16)

        notebook.add(wifi_tab, text="Wi‑Fi şəbəkələri")
        notebook.add(diagnostic_tab, text="Diaqnostika")
        notebook.add(gpon_tab, text="GPON yoxlaması")
        notebook.add(info_tab, text="Məlumat")

        self._build_wifi_tab(wifi_tab)
        self._build_diagnostic_tab(diagnostic_tab)
        self._build_gpon_tab(gpon_tab)
        self._build_info_tab(info_tab)

    def _build_wifi_tab(self, parent: ttk.Frame) -> None:
        controls = ttk.Frame(parent)
        controls.pack(fill="x", pady=(0, 12))
        ttk.Button(
            controls,
            text="Şəbəkələri yenilə",
            style="Accent.TButton",
            command=self.refresh_networks,
        ).pack(side=LEFT)
        ttk.Label(
            controls,
            text="Yaxınlıqdakı access point-lər siqnal gücünə görə sıralanır.",
            style="Muted.TLabel",
        ).pack(side=LEFT, padx=14)

        columns = ("ssid", "signal", "channel", "security", "bssid", "radio")
        self.network_tree = ttk.Treeview(parent, columns=columns, show="headings")
        headings = {
            "ssid": "SSID",
            "signal": "Siqnal",
            "channel": "Kanal",
            "security": "Təhlükəsizlik",
            "bssid": "BSSID",
            "radio": "Radio",
        }
        widths = {
            "ssid": 220,
            "signal": 85,
            "channel": 70,
            "security": 205,
            "bssid": 160,
            "radio": 115,
        }
        for column in columns:
            self.network_tree.heading(column, text=headings[column])
            self.network_tree.column(column, width=widths[column], anchor="w")

        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.network_tree.yview)
        self.network_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill="y")
        self.network_tree.pack(fill=BOTH, expand=True)

    def _build_diagnostic_tab(self, parent: ttk.Frame) -> None:
        controls = ttk.Frame(parent)
        controls.pack(fill="x", pady=(0, 12))
        ttk.Button(
            controls,
            text="Tam testi başlat",
            style="Accent.TButton",
            command=self.run_diagnostics,
        ).pack(side=LEFT)
        ttk.Button(
            controls,
            text="Modem panelini aç",
            command=self.open_modem_panel,
        ).pack(side=LEFT, padx=8)
        ttk.Button(
            controls,
            text="Hesabatı saxla",
            command=self.save_report,
        ).pack(side=LEFT)

        self.report_text = Text(
            parent,
            wrap="word",
            background="#0D1520",
            foreground="#E8EEF7",
            insertbackground="#FFFFFF",
            relief="flat",
            padx=18,
            pady=16,
            font=("Consolas", 10),
        )
        self.report_text.pack(fill=BOTH, expand=True)
        self.report_text.insert(
            END,
            "“Tam testi başlat” düyməsi gateway, internet, DNS və Wi‑Fi vəziyyətini yoxlayacaq.\n",
        )
        self.report_text.configure(state="disabled")

    def _build_gpon_tab(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=22)
        card.pack(fill="x")

        ttk.Label(
            card,
            text="Optik RX (dBm)",
            style="Card.TLabel",
            font=("Segoe UI Semibold", 11),
        ).grid(row=0, column=0, sticky="w")
        ttk.Entry(card, textvariable=self.rx_value, width=18).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(7, 16),
        )
        ttk.Checkbutton(
            card,
            text="ONT-də LOS indikatoru aktivdir",
            variable=self.los_active,
        ).grid(row=2, column=0, sticky="w")
        ttk.Button(
            card,
            text="Optik vəziyyəti qiymətləndir",
            style="Accent.TButton",
            command=self.assess_optical,
        ).grid(row=3, column=0, sticky="w", pady=(18, 0))

        self.optical_result = ttk.Label(
            card,
            text="RX dəyərini ONT panelindən daxil et.",
            style="Card.TLabel",
            wraplength=600,
            font=("Segoe UI", 11),
        )
        self.optical_result.grid(row=0, column=1, rowspan=4, sticky="nw", padx=(45, 0))

        note = (
            "Bu qiymətləndirmə ümumi orientirdir. Dəqiq hədlər ONT modeli və provayder "
            "profilinə görə dəyişir. Fiziki qırılmanın yerini yalnız OTDR göstərə bilər."
        )
        ttk.Label(
            parent,
            text=note,
            style="Muted.TLabel",
            wraplength=900,
        ).pack(anchor="w", pady=18)

    def _build_info_tab(self, parent: ttk.Frame) -> None:
        text = (
            f"{APP_NAME} {APP_VERSION}\n\n"
            "Tətbiq yalnız lokal diaqnostika aparır. Yaxın şəbəkələrə qoşulmağa, "
            "şifrə sınamağa və saxlanmış Wi‑Fi profillərini silməyə cəhd etmir.\n\n"
            "Əsas imkanlar:\n"
            "• SSID, BSSID, siqnal, kanal və təhlükəsizlik məlumatları\n"
            "• Gateway, internet, TCP və DNS testləri\n"
            "• Paket itkisi və orta ping\n"
            "• GPON RX/LOS üzrə ilkin qiymətləndirmə\n"
            "• Mətn formatında texniki hesabat"
        )
        ttk.Label(
            parent,
            text=text,
            justify=LEFT,
            wraplength=850,
            font=("Segoe UI", 11),
        ).pack(anchor="nw")

    def _build_statusbar(self) -> None:
        ttk.Label(
            self.root,
            textvariable=self.status,
            style="Muted.TLabel",
            padding=(22, 0, 22, 14),
        ).pack(fill="x")

    def _set_busy(self, message: str) -> None:
        self.status.set(message)

    def refresh_networks(self) -> None:
        self._set_busy("Wi‑Fi şəbəkələri skan edilir…")

        def worker() -> None:
            try:
                networks = wifi_core.scan_wifi_networks()
            except Exception as exc:
                self.root.after(0, lambda: self._show_error(str(exc)))
                return
            self.root.after(0, lambda: self._display_networks(networks))

        threading.Thread(target=worker, daemon=True).start()

    def _display_networks(self, networks: list[wifi_core.WifiNetwork]) -> None:
        self.network_tree.delete(*self.network_tree.get_children())
        for network in networks:
            signal = "—" if network.signal is None else f"{network.signal}%"
            channel = "—" if network.channel is None else str(network.channel)
            self.network_tree.insert(
                "",
                END,
                values=(
                    network.ssid,
                    signal,
                    channel,
                    network.security,
                    network.bssid or "—",
                    network.radio_type or "—",
                ),
            )
        self.status.set(f"{len(networks)} access point tapıldı.")

    def run_diagnostics(self) -> None:
        self._set_busy("Tam diaqnostika aparılır…")

        def worker() -> None:
            try:
                report = wifi_core.collect_diagnostics()
                text = wifi_core.format_report(report)
            except Exception as exc:
                self.root.after(0, lambda: self._show_error(str(exc)))
                return

            def finish() -> None:
                self.last_gateway = report.gateway
                self.last_report = text
                self.report_text.configure(state="normal")
                self.report_text.delete("1.0", END)
                self.report_text.insert(END, text)
                self.report_text.configure(state="disabled")
                self.status.set("Diaqnostika tamamlandı.")

            self.root.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def open_modem_panel(self) -> None:
        if self.last_gateway:
            webbrowser.open(f"http://{self.last_gateway}")
            return

        self._set_busy("Gateway müəyyən edilir…")

        def worker() -> None:
            try:
                gateway = wifi_core.get_default_gateway()
            except Exception as exc:
                self.root.after(0, lambda: self._show_error(str(exc)))
                return

            def finish() -> None:
                if not gateway:
                    self._show_error("Gateway tapılmadı.")
                    return
                self.last_gateway = gateway
                self.status.set(f"Modem paneli açılır: {gateway}")
                webbrowser.open(f"http://{gateway}")

            self.root.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def save_report(self) -> None:
        if not self.last_report:
            messagebox.showinfo(APP_NAME, "Əvvəlcə tam diaqnostika apar.")
            return
        default_name = f"wifi_hesabat_{dt.datetime.now():%Y%m%d_%H%M%S}.txt"
        path = filedialog.asksaveasfilename(
            title="Hesabatı saxla",
            initialfile=default_name,
            defaultextension=".txt",
            filetypes=[("Mətn faylı", "*.txt")],
        )
        if not path:
            return
        Path(path).write_text(self.last_report, encoding="utf-8")
        self.status.set(f"Hesabat saxlanıldı: {path}")

    def assess_optical(self) -> None:
        raw = self.rx_value.get().strip().replace(",", ".")
        rx: float | None
        if not raw:
            rx = None
        else:
            try:
                rx = float(raw)
            except ValueError:
                self._show_error("RX dəyərini rəqəm kimi yaz. Nümunə: -21.5")
                return
        level, message = wifi_core.optical_assessment(rx, self.los_active.get())
        self.optical_result.configure(text=f"{level}\n\n{message}")
        self.status.set("Optik qiymətləndirmə tamamlandı.")

    def _show_error(self, message: str) -> None:
        self.status.set("Əməliyyat uğursuz oldu.")
        messagebox.showerror(APP_NAME, message)


def main() -> None:
    root = Tk()
    WifiTechnicianApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
