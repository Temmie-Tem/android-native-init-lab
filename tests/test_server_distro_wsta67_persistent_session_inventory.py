from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


wsta63 = load_script("workspace/public/src/scripts/server-distro/run_wsta63_persistent_session_controller.py")
wsta64 = load_script("workspace/public/src/scripts/server-distro/run_wsta64_persistent_session_readiness_audit.py")
wsta65 = load_script("workspace/public/src/scripts/server-distro/run_wsta65_persistent_session_status.py")
wsta66 = load_script("workspace/public/src/scripts/server-distro/run_wsta66_persistent_session_retire.py")
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta67_persistent_session_inventory.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta67_persistent_session_inventory.py")


class ServerDistroWsta67PersistentSessionInventoryTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def prepare_session(self, root: Path, label: str, ttl_sec: int = 300) -> dict[str, Path]:
        base = root / label
        wsta63_args = wsta63.build_arg_parser().parse_args([
            "--run-dir",
            str(base / "wsta63"),
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
            str(base / "wsta64"),
            "--wsta63-result-json",
            str(base / "wsta63" / "wsta63_result.json"),
            "--min-initial-seconds-remaining",
            "30",
        ])
        self.assertEqual(wsta64.run(wsta64_args)["decision"], wsta64.PASS_DECISION)
        wsta65_args = wsta65.build_arg_parser().parse_args([
            "--run-dir",
            str(base / "wsta65-ready"),
            "--wsta64-result-json",
            str(base / "wsta64" / "wsta64_result.json"),
        ])
        self.assertEqual(wsta65.run(wsta65_args)["decision"], wsta65.PASS_DECISION)
        return {
            "base": base,
            "wsta64": base / "wsta64" / "wsta64_result.json",
            "wsta65": base / "wsta65-ready" / "wsta65_result.json",
            "initial": base / "wsta63" / "initial-wsta54" / "wsta54_private_lease.json",
        }

    def retire_session(self, paths: dict[str, Path]) -> Path:
        args = wsta66.build_arg_parser().parse_args([
            "--run-dir",
            str(paths["base"] / "wsta66"),
            "--retire-session",
            "--ack-retire-session",
            "--wsta65-result-json",
            str(paths["wsta65"]),
            "--reason",
            "operator-retired",
        ])
        self.assertEqual(wsta66.run(args)["decision"], wsta66.PASS_DECISION)
        return paths["base"] / "wsta66" / "wsta66_retire_marker.json"

    def test_default_inventory_scan_is_host_only_and_private(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            with mock.patch.object(runner.wsta65.wsta64.wsta58.wsta55, "run", side_effect=AssertionError("unexpected live WSTA55")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "inventory"),
                    "--scan-root",
                    str(root),
                ]))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(result["inventory"]["session_count"], 0)
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

    def test_inventory_counts_ready_retired_and_stale_sessions(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            ready = self.prepare_session(root, "ready", ttl_sec=300)
            retired = self.prepare_session(root, "retired", ttl_sec=300)
            self.retire_session(retired)
            stale = self.prepare_session(root, "stale", ttl_sec=60)
            stale_artifact = json.loads(stale["initial"].read_text(encoding="utf-8"))
            expires = runner.wsta65.wsta64.parse_utc_stamp(stale_artifact["expires_utc"])
            self.assertIsNotNone(expires)
            now = expires - runner._dt.timedelta(seconds=10)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "inventory"),
                "--scan-root",
                str(root),
                "--min-initial-seconds-remaining",
                "30",
                "--now-utc",
                runner.utc_stamp(now),
            ]))

        counts = result["inventory"]["state_counts"]
        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(counts["READY"], 1)
        self.assertEqual(counts["RETIRED"], 1)
        self.assertEqual(counts["STALE"], 1)
        self.assertNotIn("EXPIRED", counts)
        states = {entry["wsta64_result"]: entry["session_state"] for entry in result["inventory"]["entries"]}
        self.assertEqual(states[runner.rel(retired["wsta64"])], "RETIRED")
        self.assertEqual(states[runner.rel(stale["wsta64"])], "STALE")
        self.assertEqual(states[runner.rel(ready["wsta64"])], "READY")
        self.assertTrue(all(entry["state"] == "PUBLIC_OFF" for entry in result["inventory"]["entries"]))

    def test_inventory_reclassifies_expired_when_now_is_at_expiry(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            expired = self.prepare_session(root, "expired", ttl_sec=60)
            artifact = json.loads(expired["initial"].read_text(encoding="utf-8"))
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "inventory"),
                "--scan-root",
                str(root),
                "--now-utc",
                artifact["expires_utc"],
            ]))

        self.assertEqual(result["inventory"]["state_counts"]["EXPIRED"], 1)
        self.assertFalse(result["inventory"]["entries"][0]["ready_for_live"])

    def test_nonprivate_scan_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(runner.DEFAULT_RUN_BASE / "wsta67-nonprivate-test"),
                "--scan-root",
                tmp,
            ]))

        self.assertEqual(result["decision"], "wsta67-blocked-nonprivate-scan-root")

    def test_public_summary_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.prepare_session(root, "ready")
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "inventory"),
                "--scan-root",
                str(root),
            ]))
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
            self.assertNotIn(runner.wsta65.wsta64.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
            self.assertNotIn(runner.wsta65.wsta64.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, text)

    def test_print_template_exits_without_inventory(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA67 host-only", payload)
        self.assertIn("--scan-root", payload)

    def test_source_keeps_live_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("session_state", source)
        self.assertIn("state_counts", source)
        self.assertIn("retire_marker_map", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
