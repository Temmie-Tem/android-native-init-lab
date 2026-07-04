from __future__ import annotations

import subprocess
import tempfile
import time
import unittest
from pathlib import Path


HELPER = Path("workspace/public/src/scripts/server-distro/a90_native_wifi_service_client.sh")


def parse_kv(path: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        payload[key] = value
    return payload


class NativeWifiServiceClientHelperTests(unittest.TestCase):
    def test_status_roundtrip_filters_response_and_requires_native_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service_dir = Path(tmp) / "svc"
            proc = subprocess.Popen(
                ["sh", str(HELPER), "status", str(service_dir)],
                cwd=Path.cwd(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            request = service_dir / "request"
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline and not request.exists():
                time.sleep(0.05)
            self.assertTrue(request.exists())
            req = parse_kv(request)
            self.assertEqual(req["op"], "status")
            response = service_dir / "response"
            response.write_text(
                "\n".join([
                    "version=a90-native-wifi-service-v1",
                    f"seq={req['seq']}",
                    "op=status",
                    "owner=native-init",
                    "rc=0",
                    "wlan0_present=1",
                    "supplicant_process_count=0",
                    "dhcp_routing=0",
                    "public_tunnel=0",
                    "ssid=should-not-print",
                    "psk=should-not-print",
                    "raw_bssid=should-not-print",
                    "decision=wifi-service-status-pass",
                    "",
                ]),
                encoding="utf-8",
            )

            stdout, stderr = proc.communicate(timeout=10.0)

        self.assertEqual(proc.returncode, 0, stderr)
        self.assertIn("native_wifi_service_client_response_ready=1", stdout)
        self.assertIn("owner=native-init", stdout)
        self.assertIn("native_wifi_service_client_decision=native-wifi-service-client-pass", stdout)
        self.assertIn("native_wifi_service_client_secret_values_logged=0", stdout)
        self.assertNotIn("should-not-print", stdout)
        self.assertNotIn("ssid=", stdout.lower())
        self.assertNotIn("psk=", stdout.lower())

    def test_dangerous_operations_are_denied_before_request_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service_dir = Path(tmp) / "svc"
            completed = subprocess.run(
                ["sh", str(HELPER), "connect", str(service_dir)],
                cwd=Path.cwd(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5.0,
                check=False,
            )

            self.assertEqual(completed.returncode, 64)
            self.assertIn("native_wifi_service_client_decision=native-wifi-service-op-denied", completed.stdout)
            self.assertFalse((service_dir / "request").exists())


if __name__ == "__main__":
    unittest.main()
