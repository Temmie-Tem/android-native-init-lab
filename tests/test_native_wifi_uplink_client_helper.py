from __future__ import annotations

import subprocess
import tempfile
import time
import unittest
from pathlib import Path


HELPER = Path("workspace/public/src/scripts/server-distro/a90_native_wifi_uplink_client.sh")


def parse_kv(path: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        payload[key] = value
    return payload


class NativeWifiUplinkClientHelperTests(unittest.TestCase):
    def test_status_roundtrip_filters_profile_labels_and_requires_native_owner(self) -> None:
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
                    "version=a90-native-wifi-uplink-service-v1",
                    f"seq={req['seq']}",
                    "op=status",
                    "owner=native-init",
                    "credentials=0",
                    "connect=0",
                    "dhcp_routing=observed-only",
                    "external_ping_execution=0",
                    "public_tunnel=0",
                    "secret_values_logged=0",
                    "config_profile_present=1",
                    "autoconnect_profile_present=1",
                    "profile=should-not-print",
                    "ssid=should-not-print",
                    "psk=should-not-print",
                    "decision=wifi-uplink-service-status-pass",
                    "",
                ]),
                encoding="utf-8",
            )

            stdout, stderr = proc.communicate(timeout=10.0)

        self.assertEqual(proc.returncode, 0, stderr)
        self.assertIn("native_wifi_uplink_client_response_ready=1", stdout)
        self.assertIn("owner=native-init", stdout)
        self.assertIn("config_profile_present=1", stdout)
        self.assertIn("autoconnect_profile_present=1", stdout)
        self.assertIn("native_wifi_uplink_client_decision=native-wifi-uplink-client-pass", stdout)
        self.assertIn("native_wifi_uplink_client_secret_values_logged=0", stdout)
        self.assertNotIn("should-not-print", stdout)
        self.assertNotIn("profile=", stdout.lower())
        self.assertNotIn("ssid=", stdout.lower())
        self.assertNotIn("psk=", stdout.lower())

    def test_autoconnect_no_confirm_probe_expects_denial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service_dir = Path(tmp) / "svc"
            proc = subprocess.Popen(
                ["sh", str(HELPER), "autoconnect-no-confirm", str(service_dir)],
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
            self.assertEqual(req["op"], "autoconnect")
            self.assertNotIn("confirm", req)
            response = service_dir / "response"
            response.write_text(
                "\n".join([
                    "version=a90-native-wifi-uplink-service-v1",
                    f"seq={req['seq']}",
                    "op=autoconnect",
                    "owner=native-init",
                    "credentials=private-config-gated",
                    "connect=confirm-gated",
                    "dhcp_routing=config-gated",
                    "external_ping_execution=0",
                    "public_tunnel=0",
                    "secret_values_logged=0",
                    "rc=-13",
                    "decision=wifi-uplink-service-confirm-required",
                    "",
                ]),
                encoding="utf-8",
            )

            stdout, stderr = proc.communicate(timeout=10.0)

        self.assertEqual(proc.returncode, 0, stderr)
        self.assertIn("native_wifi_uplink_client_requested_op=autoconnect-no-confirm", stdout)
        self.assertIn("decision=wifi-uplink-service-confirm-required", stdout)
        self.assertIn("native_wifi_uplink_client_decision=native-wifi-uplink-client-pass", stdout)

    def test_confirmed_and_dangerous_operations_are_denied_before_request_write(self) -> None:
        for op in ("autoconnect", "connect", "dhcp", "ping", "public-tunnel", "confirmed-autoconnect"):
            with self.subTest(op=op), tempfile.TemporaryDirectory() as tmp:
                service_dir = Path(tmp) / "svc"
                completed = subprocess.run(
                    ["sh", str(HELPER), op, str(service_dir)],
                    cwd=Path.cwd(),
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5.0,
                    check=False,
                )

                self.assertEqual(completed.returncode, 64)
                self.assertIn("native_wifi_uplink_client_decision=native-wifi-uplink-client-op-denied", completed.stdout)
                self.assertFalse((service_dir / "request").exists())


if __name__ == "__main__":
    unittest.main()
