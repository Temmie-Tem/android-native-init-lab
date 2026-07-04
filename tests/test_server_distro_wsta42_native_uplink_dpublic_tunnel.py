from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta42_native_uplink_dpublic_tunnel.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta42_native_uplink_dpublic_tunnel.py")


class ServerDistroWsta42NativeUplinkDpublicTunnelTests(unittest.TestCase):
    def test_explicit_live_gate_is_fail_closed(self) -> None:
        args = SimpleNamespace(
            allow_public_live=False,
            ack_credentialed_wifi=False,
            ack_public_exposure=False,
            native_confirm_token="",
            public_confirm_token="",
        )
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta42-blocked-explicit-public-live-allow-required"),
        )

        args.allow_public_live = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta42-blocked-credentialed-wifi-ack-required"),
        )

        args.ack_credentialed_wifi = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta42-blocked-public-exposure-ack-required"),
        )

        args.ack_public_exposure = True
        args.native_confirm_token = "wrong"
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta42-blocked-native-confirm-token-required"),
        )

        args.native_confirm_token = runner.wsta25.NATIVE_CONFIRM_TOKEN
        args.public_confirm_token = "wrong"
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta42-blocked-public-confirm-token-required"),
        )

        args.public_confirm_token = runner.PUBLIC_CONFIRM_TOKEN
        self.assertEqual(runner.explicit_live_gate(args), (True, "ok"))

    def test_classify_requires_uplink_tunnel_public_smoke_and_cleanup(self) -> None:
        checks = {
            "explicit_live_gate": True,
            "native_supported": True,
            "baseline_selftest_fail_zero": True,
            "final_selftest_fail_zero": True,
            "helpers_built": True,
            "debian_ssh_marker": True,
            "dpublic_binaries_staged": True,
            "native_uplink_confirmed": True,
            "default_route_wlan0": True,
            "resolver_ready": True,
            "local_smoke_ok": True,
            "tunnel_url_observed": True,
            "public_smoke_ok": True,
            "dpublic_cleanup_ok": True,
            "chroot_cleanup_ok": True,
        }
        self.assertEqual(runner.classify({"checks": checks}), runner.PASS_DECISION)

        for key, decision in (
            ("explicit_live_gate", "wsta42-blocked-explicit-live-gate"),
            ("native_supported", "wsta42-blocked-supported-native-not-resident"),
            ("native_uplink_confirmed", "wsta42-blocked-native-uplink-confirmed"),
            ("default_route_wlan0", "wsta42-blocked-default-route-not-wlan0"),
            ("resolver_ready", "wsta42-blocked-resolver-sync"),
            ("local_smoke_ok", "wsta42-blocked-local-smoke"),
            ("tunnel_url_observed", "wsta42-blocked-tunnel-url"),
            ("public_smoke_ok", "wsta42-blocked-public-smoke"),
            ("dpublic_cleanup_ok", "wsta42-blocked-dpublic-cleanup"),
            ("chroot_cleanup_ok", "wsta42-blocked-chroot-cleanup"),
        ):
            variant = {"checks": {**checks, key: False}}
            self.assertEqual(runner.classify(variant), decision)

    def test_fetch_public_url_writes_private_file_without_returning_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            args = SimpleNamespace(ssh_timeout=5.0)
            url = "https://example-test.trycloudflare.com\n"

            with mock.patch.object(runner, "ssh_exec", return_value={
                "returncode": 0,
                "stdout": url,
                "stderr": "",
            }):
                record = runner.fetch_public_url(args, run_dir)

            self.assertTrue(record["url_observed"])
            self.assertTrue(record["stdout_redacted"])
            self.assertNotIn("trycloudflare.com", repr(record))
            self.assertEqual((run_dir / "public-url.txt").read_text(encoding="utf-8"), url)

    def test_resolver_ready_requires_ready_marker_and_nameserver_count(self) -> None:
        self.assertTrue(runner.resolver_ready({"ready": True, "nameserver_count": 1}))
        self.assertFalse(runner.resolver_ready({"ready": False, "nameserver_count": 1}))
        self.assertFalse(runner.resolver_ready({"ready": True, "nameserver_count": 0}))

    def test_start_smoke_parses_diagnostic_without_ssh_failure_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(ssh_timeout=5.0)
            stdout = (
                "A90WSTA42_LOOPBACK_UP rc=0\n"
                "A90WSTA42_SMOKE_STARTED\n"
                "A90_DPUBLIC_SMOKE_OK\n"
                "A90WSTA42_SMOKE_DIAG pid_alive=1 listen=1 http_get_rc=0 log_bytes=48\n"
            )
            with mock.patch.object(runner, "ssh_exec", return_value={
                "returncode": 0,
                "stdout": stdout,
                "stderr": "",
            }):
                record = runner.start_smoke(args, Path(tmp))

            self.assertTrue(record["started"])
            self.assertTrue(record["local_smoke_ok"])
            self.assertTrue(record["pid_alive"])
            self.assertTrue(record["listen"])
            self.assertEqual(record["http_get_rc"], 0)
            self.assertEqual(record["loopback_up_rc"], 0)

    def test_runner_surface_is_fail_closed_and_url_redacted(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--allow-public-live", source)
        self.assertIn("--ack-credentialed-wifi", source)
        self.assertIn("--ack-public-exposure", source)
        self.assertIn("--native-confirm-token", source)
        self.assertIn("--public-confirm-token", source)
        self.assertIn("--host-resolver-conf", source)
        self.assertIn("content_redacted", source)
        self.assertIn("public_url_value_logged", source)
        self.assertIn("public-url.txt", source)
        self.assertIn("stdout_redacted", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"switch_root": False', source)
        self.assertIn('"userdata_touch": False', source)
        self.assertIn("explicit-public-live-gated", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
