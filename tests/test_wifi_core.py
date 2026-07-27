from __future__ import annotations

import unittest

from wifi_core import (
    ConnectionInfo,
    PingResult,
    optical_assessment,
    parse_connection,
    parse_networks,
    parse_ping_output,
    summarize_findings,
)


NETWORK_SAMPLE_EN = """
Interface name : Wi-Fi
There are 2 networks currently visible.

SSID 1 : Home-5G
    Network type            : Infrastructure
    Authentication          : WPA2-Personal
    Encryption              : CCMP
    BSSID 1                 : 10:20:30:40:50:60
         Signal             : 82%
         Radio type         : 802.11ax
         Channel            : 36

SSID 2 : Office
    Network type            : Infrastructure
    Authentication          : WPA3-Personal
    Encryption              : CCMP
    BSSID 1                 : aa:bb:cc:dd:ee:ff
         Signal             : 45%
         Radio type         : 802.11ac
         Channel            : 11
"""


NETWORK_SAMPLE_RU = """
Имя интерфейса: Беспроводная сеть

SSID 1 : Test-RU
    Тип сети               : Инфраструктура
    Проверка подлинности   : WPA2-Personal
    Шифрование             : CCMP
    BSSID 1                : 11:22:33:44:55:66
         Сигнал            : 67%
         Тип радио         : 802.11n
         Канал             : 6
"""


class NetworkParserTests(unittest.TestCase):
    def test_parses_and_sorts_english_networks(self) -> None:
        networks = parse_networks(NETWORK_SAMPLE_EN)
        self.assertEqual(2, len(networks))
        self.assertEqual("Home-5G", networks[0].ssid)
        self.assertEqual(82, networks[0].signal)
        self.assertEqual(36, networks[0].channel)
        self.assertEqual("WPA2-Personal / CCMP", networks[0].security)

    def test_parses_localized_signal_and_channel(self) -> None:
        network = parse_networks(NETWORK_SAMPLE_RU)[0]
        self.assertEqual("Test-RU", network.ssid)
        self.assertEqual(67, network.signal)
        self.assertEqual(6, network.channel)
        self.assertEqual("802.11n", network.radio_type)

    def test_parses_current_connection(self) -> None:
        output = """
            State                  : connected
            SSID                   : Home-5G
            BSSID                  : 10:20:30:40:50:60
            Signal                 : 76%
        """
        info = parse_connection(output)
        self.assertTrue(info.connected)
        self.assertEqual("Home-5G", info.ssid)
        self.assertEqual(76, info.signal)


class PingParserTests(unittest.TestCase):
    def test_parses_successful_ping(self) -> None:
        output = """
        Reply from 1.1.1.1: bytes=32 time=15ms TTL=58
        Reply from 1.1.1.1: bytes=32 time=17ms TTL=58
        Reply from 1.1.1.1: bytes=32 time<1ms TTL=58
        Request timed out.
        """
        result = parse_ping_output("1.1.1.1", output, 4)
        self.assertEqual(3, result.received)
        self.assertEqual(25.0, result.loss_percent)
        self.assertAlmostEqual(11.0, result.average_ms or 0)


class DiagnosisTests(unittest.TestCase):
    def test_detects_local_gateway_failure(self) -> None:
        findings = summarize_findings(
            ConnectionInfo(connected=True, ssid="Test", signal=80),
            "192.168.1.1",
            PingResult("192.168.1.1", 4, 0, 100.0, None),
            PingResult("1.1.1.1", 4, 0, 100.0, None),
            False,
            False,
        )
        self.assertIn("Modemə/gateway-ə cavab yoxdur", findings[0])

    def test_detects_dns_failure(self) -> None:
        findings = summarize_findings(
            ConnectionInfo(connected=True, ssid="Test", signal=80),
            "192.168.1.1",
            PingResult("192.168.1.1", 4, 4, 0.0, 1.0),
            PingResult("1.1.1.1", 4, 4, 0.0, 20.0),
            False,
            True,
        )
        self.assertTrue(any("DNS" in item for item in findings))

    def test_optical_thresholds(self) -> None:
        self.assertEqual("NORMAL", optical_assessment(-21.5, False)[0])
        self.assertEqual("XƏBƏRDARLIQ", optical_assessment(-26.0, False)[0])
        self.assertEqual("KRİTİK", optical_assessment(-29.0, False)[0])
        self.assertEqual("KRİTİK", optical_assessment(-20.0, True)[0])


if __name__ == "__main__":
    unittest.main()
