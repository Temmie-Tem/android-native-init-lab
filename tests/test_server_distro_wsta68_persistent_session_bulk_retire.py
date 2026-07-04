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
wsta67 = load_script("workspace/public/src/scripts/server-distro/run_wsta67_persistent_session_inventory.py")
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta68_persistent_session_bulk_retire.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta68_persistent_session_bulk_retire.py")


class ServerDistroWsta68PersistentSessionBulkRetireTests(unittest.TestCase):
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

    def retire_session(self, paths: dict[str, Path]) -> None:
        args = wsta66.build_arg_parser().parse_args([
            "--run-dir",
            str(paths["base"] / "wsta66"),
            "--retire-session",
            "--ack-retire-session",
            "--wsta65-result-json",
            str(paths["wsta65"]),
        ])
        self.assertEqual(wsta66.run(args)["decision"], wsta66.PASS_DECISION)

    def inventory(self, root: Path, now_utc: str | None = None) -> Path:
        args_list = [
            "--run-dir",
            str(root / "inventory"),
            "--scan-root",
            str(root),
            "--max-sessions",
            "20",
            "--max-retire-markers",
            "20",
        ]
        if now_utc:
            args_list.extend(["--now-utc", now_utc])
        args = wsta67.build_arg_parser().parse_args(args_list)
        self.assertEqual(wsta67.run(args)["decision"], wsta67.PASS_DECISION)
        return root / "inventory" / "wsta67_inventory.json"

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(Path(tmp) / "run"),
            ]))

        self.assertEqual(result["decision"], "wsta68-blocked-bulk-retire-required")
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

    def test_bulk_retire_targets_nonliveable_sessions_and_skips_ready_retired(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            ready = self.prepare_session(root, "ready", ttl_sec=300)
            retired = self.prepare_session(root, "retired", ttl_sec=300)
            self.retire_session(retired)
            stale = self.prepare_session(root, "stale", ttl_sec=60)
            artifact = json.loads(stale["initial"].read_text(encoding="utf-8"))
            expires = runner.wsta67.wsta65.wsta64.parse_utc_stamp(artifact["expires_utc"])
            self.assertIsNotNone(expires)
            now = runner.wsta67.utc_stamp(expires - runner._dt.timedelta(seconds=10))
            inventory = self.inventory(root, now)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "bulk-retire"),
                "--bulk-retire",
                "--ack-bulk-retire",
                "--wsta67-inventory-json",
                str(inventory),
            ]))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(result["bulk_retire"]["retired_count"], 1)
        self.assertEqual(result["bulk_retire"]["retired"][0]["previous_session_state"], "STALE")
        skipped_states = {entry["wsta64_result"]: entry["session_state"] for entry in result["bulk_retire"]["skipped"]}
        self.assertEqual(skipped_states[runner.rel(ready["wsta64"])], "READY")
        self.assertEqual(skipped_states[runner.rel(retired["wsta64"])], "RETIRED")
        self.assertFalse(result["checks"]["ready_sessions_retired"])

    def test_bulk_retire_marker_is_consumed_by_next_inventory(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            stale = self.prepare_session(root, "stale", ttl_sec=60)
            artifact = json.loads(stale["initial"].read_text(encoding="utf-8"))
            expires = runner.wsta67.wsta65.wsta64.parse_utc_stamp(artifact["expires_utc"])
            self.assertIsNotNone(expires)
            now = runner.wsta67.utc_stamp(expires - runner._dt.timedelta(seconds=10))
            inventory = self.inventory(root, now)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "bulk-retire"),
                "--bulk-retire",
                "--ack-bulk-retire",
                "--wsta67-inventory-json",
                str(inventory),
            ]))
            self.assertEqual(result["bulk_retire"]["retired_count"], 1)
            second_inventory = wsta67.run(wsta67.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "inventory-after"),
                "--scan-root",
                str(root),
                "--now-utc",
                now,
            ]))

        self.assertEqual(second_inventory["inventory"]["state_counts"]["RETIRED"], 1)
        self.assertEqual(second_inventory["inventory"]["entries"][0]["session_state"], "RETIRED")

    def test_bulk_retire_requires_explicit_ack(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.prepare_session(root, "ready")
            inventory = self.inventory(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "bulk-retire"),
                "--bulk-retire",
                "--wsta67-inventory-json",
                str(inventory),
            ]))

        self.assertEqual(result["decision"], "wsta68-blocked-bulk-retire-ack-required")

    def test_public_summary_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.prepare_session(root, "ready")
            inventory = self.inventory(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "bulk-retire"),
                "--bulk-retire",
                "--ack-bulk-retire",
                "--wsta67-inventory-json",
                str(inventory),
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
            self.assertNotIn(runner.wsta67.wsta65.wsta64.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
            self.assertNotIn(runner.wsta67.wsta65.wsta64.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, text)

    def test_print_template_exits_without_bulk_retire(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA68 host-only", payload)
        self.assertIn("--bulk-retire", payload)

    def test_source_keeps_live_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("DEFAULT_TARGET_STATES", source)
        self.assertIn("ready_sessions_retired", source)
        self.assertIn("wsta66_retire_marker.json", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
