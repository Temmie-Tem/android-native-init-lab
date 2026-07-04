from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


wsta63 = load_script("workspace/public/src/scripts/server-distro/run_wsta63_persistent_session_controller.py")
wsta64 = load_script("workspace/public/src/scripts/server-distro/run_wsta64_persistent_session_readiness_audit.py")
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta65_persistent_session_status.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta65_persistent_session_status.py")


class ServerDistroWsta65PersistentSessionStatusTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def make_wsta64_ready(self, root: Path, ttl_sec: int = 300) -> Path:
        wsta63_args = wsta63.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta63"),
            "--prepare-session",
            "--ttl-sec",
            str(ttl_sec),
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--native-confirm-token-source",
            "private",
            "--public-confirm-token-source",
            "private",
        ])
        self.assertEqual(wsta63.run(wsta63_args)["decision"], wsta63.PASS_DECISION)
        wsta64_args = wsta64.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta64"),
            "--wsta63-result-json",
            str(root / "wsta63" / "wsta63_result.json"),
            "--min-initial-seconds-remaining",
            "30",
        ])
        self.assertEqual(wsta64.run(wsta64_args)["decision"], wsta64.PASS_DECISION)
        return root / "wsta64" / "wsta64_result.json"

    def valid_args(self, root: Path):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta65"),
            "--wsta64-result-json",
            str(self.make_wsta64_ready(root)),
            "--min-initial-seconds-remaining",
            "30",
        ])

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(Path(tmp) / "run"),
            ]))

        self.assertEqual(result["decision"], "wsta65-blocked-wsta64-result-required")
        for key in (
            "device_action",
            "boot_flash",
            "native_reboot",
            "wifi_connect",
            "dhcp",
            "public_tunnel",
            "public_smoke",
            "userdata_touch",
            "switch_root",
        ):
            self.assertFalse(result["safety"][key])

    def test_ready_wsta64_result_reports_ready_without_live_execution(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            with mock.patch.object(runner.wsta64.wsta58.wsta55, "run", side_effect=AssertionError("unexpected live WSTA55")):
                result = runner.run(self.valid_args(root))
            saved = json.loads((root / "wsta65" / "wsta65_result.json").read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        self.assertEqual(result["session_status"]["session_state"], "READY")
        self.assertTrue(result["session_status"]["ready_for_live"])
        self.assertEqual(result["session_status"]["recommended_next_action"], "operator-may-run-explicit-wsta58-live-gate")
        self.assertFalse(result["checks"]["live_execution_requested"])
        self.assertTrue(result["checks"]["default_public_off"])

    def test_ready_wsta64_result_becomes_stale_when_remaining_margin_is_too_small(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta64_result = self.make_wsta64_ready(root, ttl_sec=60)
            initial = root / "wsta63" / "initial-wsta54" / "wsta54_private_lease.json"
            artifact = json.loads(initial.read_text(encoding="utf-8"))
            expires = runner.wsta64.parse_utc_stamp(artifact["expires_utc"])
            self.assertIsNotNone(expires)
            now = expires - runner._dt.timedelta(seconds=10)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta65"),
                "--wsta64-result-json",
                str(wsta64_result),
                "--min-initial-seconds-remaining",
                "30",
                "--now-utc",
                runner.utc_stamp(now),
            ]))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(result["session_status"]["session_state"], "STALE")
        self.assertFalse(result["session_status"]["ready_for_live"])
        self.assertEqual(result["session_status"]["recommended_next_action"], "rerun-wsta63-then-wsta64")

    def test_ready_wsta64_result_becomes_expired_after_lease_expiry(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta64_result = self.make_wsta64_ready(root, ttl_sec=60)
            initial = root / "wsta63" / "initial-wsta54" / "wsta54_private_lease.json"
            artifact = json.loads(initial.read_text(encoding="utf-8"))
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta65"),
                "--wsta64-result-json",
                str(wsta64_result),
                "--now-utc",
                artifact["expires_utc"],
            ]))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(result["session_status"]["session_state"], "EXPIRED")
        self.assertFalse(result["session_status"]["ready_for_live"])

    def test_nonpass_wsta64_result_reports_not_ready_status(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta64_path = root / "wsta64" / "wsta64_result.json"
            wsta64_path.parent.mkdir(parents=True)
            wsta64_path.write_text(json.dumps({
                "decision": "wsta64-blocked-wsta58-preflight-not-pass",
                "readiness": {},
            }), encoding="utf-8")
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta65"),
                "--wsta64-result-json",
                str(wsta64_path),
            ]))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(result["session_status"]["session_state"], "NOT_READY")
        self.assertEqual(result["session_status"]["recommended_next_action"], "inspect-wsta64-result")

    def test_public_summary_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(self.valid_args(Path(tmp)))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
        tunnel_domain = "try" + "cloudflare.com"
        http_scheme = "http" + "://"
        https_scheme = "https" + "://"

        for text in (summary_text, template_text):
            self.assertNotIn(tunnel_domain, text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn(http_scheme, text.lower())
            self.assertNotIn(https_scheme, text.lower())
            self.assertNotIn(runner.wsta64.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
            self.assertNotIn(runner.wsta64.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, text)

    def test_print_template_exits_without_status(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA65 host-only", payload)
        self.assertIn("--wsta64-result-json", payload)

    def test_source_keeps_live_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("session_state", source)
        self.assertIn("READY", source)
        self.assertIn("STALE", source)
        self.assertIn("EXPIRED", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
