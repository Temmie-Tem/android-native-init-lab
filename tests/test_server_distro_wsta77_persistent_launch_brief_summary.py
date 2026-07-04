from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


wsta72 = load_script("workspace/public/src/scripts/server-distro/run_wsta72_persistent_prepare_to_arm.py")
wsta73 = load_script("workspace/public/src/scripts/server-distro/run_wsta73_persistent_arming_packet.py")
wsta75 = load_script("workspace/public/src/scripts/server-distro/run_wsta75_persistent_arming_inventory.py")
wsta76 = load_script("workspace/public/src/scripts/server-distro/run_wsta76_persistent_launch_brief.py")
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta77_persistent_launch_brief_summary.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta77_persistent_launch_brief_summary.py")


class ServerDistroWsta77PersistentLaunchBriefSummaryTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def prepare_brief(self, root: Path, label: str, ttl_sec: int = 300) -> dict[str, Path]:
        base = root / label
        prepare_args = wsta72.build_arg_parser().parse_args([
            "--run-dir",
            str(base / "prepare"),
            "--prepare-to-arm",
            "--ttl-sec",
            str(ttl_sec),
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--native-confirm-token-source",
            "private",
            "--public-confirm-token-source",
            "private",
        ])
        self.assertEqual(wsta72.run(prepare_args)["decision"], wsta72.PASS_DECISION)
        packet_args = wsta73.build_arg_parser().parse_args([
            "--run-dir",
            str(base / "packet"),
            "--wsta72-prepare-to-arm-json",
            str(base / "prepare" / "wsta72_prepare_to_arm.json"),
        ])
        self.assertEqual(wsta73.run(packet_args)["decision"], wsta73.PASS_DECISION)
        inventory_args = wsta75.build_arg_parser().parse_args([
            "--run-dir",
            str(base / "inventory"),
            "--scan-root",
            str(root),
        ])
        self.assertEqual(wsta75.run(inventory_args)["decision"], wsta75.PASS_DECISION)
        brief_args = wsta76.build_arg_parser().parse_args([
            "--run-dir",
            str(base / "brief"),
            "--wsta75-arming-inventory-json",
            str(base / "inventory" / "wsta75_arming_inventory.json"),
        ])
        self.assertEqual(wsta76.run(brief_args)["decision"], wsta76.PASS_DECISION)
        return {
            "base": base,
            "inventory": base / "inventory" / "wsta75_arming_inventory.json",
            "brief": base / "brief" / "wsta76_launch_brief.json",
            "packet": base / "packet" / "wsta73_arming_packet.json",
            "initial": base / "prepare" / "wsta63" / "initial-wsta54" / "wsta54_private_lease.json",
        }

    def test_default_summary_scan_is_host_only_and_private(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            with mock.patch.object(runner.wsta76.wsta75.wsta74.wsta73.wsta71.wsta65.wsta64.wsta58.wsta55, "run", side_effect=AssertionError("unexpected live WSTA55")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "summary"),
                    "--scan-root",
                    str(root),
                ]))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(result["launch_summary"]["brief_count"], 0)
        self.assertEqual(result["launch_summary"]["overall_state"], "NO_LAUNCH_BRIEFS_FOUND")
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

    def test_summary_rechecks_ready_brief_and_selects_it(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.prepare_brief(root, "ready")
            with mock.patch.object(runner.wsta76.wsta75.wsta74.wsta73.wsta71.wsta65.wsta64.wsta58.wsta55, "run", side_effect=AssertionError("unexpected live WSTA55")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "summary"),
                    "--scan-root",
                    str(root),
                ]))
            saved = json.loads((root / "summary" / "wsta77_launch_brief_summary.json").read_text(encoding="utf-8"))
            markdown = (root / "summary" / "wsta77_launch_brief_summary.md").read_text(encoding="utf-8")

        summary = result["launch_summary"]
        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        self.assertEqual(summary["brief_count"], 1)
        self.assertEqual(summary["ready_count"], 1)
        self.assertEqual(summary["overall_state"], "READY_BRIEF_PRESENT_DEFAULT_OFF")
        self.assertEqual(summary["selected_ready_brief"]["wsta76_launch_brief"], runner.rel(artifacts["brief"]))
        self.assertEqual(summary["selected_ready_brief"]["state"], "READY_TO_EXECUTE_DEFAULT_OFF")
        self.assertEqual(summary["recommended_next_action"], "operator-may-run-explicit-wsta58-live-gate-from-selected-brief")
        self.assertFalse(result["checks"]["live_execution_requested"])
        self.assertIn("WSTA Persistent Launch Brief Summary", markdown)

    def test_summary_marks_stale_brief_after_fresh_recheck(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.prepare_brief(root, "stale", ttl_sec=60)
            initial = json.loads(artifacts["initial"].read_text(encoding="utf-8"))
            expires = runner.wsta76.wsta75.wsta74.wsta73.wsta72.wsta67.wsta65.wsta64.parse_utc_stamp(initial["expires_utc"])
            self.assertIsNotNone(expires)
            later = runner.utc_stamp(expires - runner._dt.timedelta(seconds=10))
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "summary"),
                "--scan-root",
                str(root),
                "--min-initial-seconds-remaining",
                "30",
                "--now-utc",
                later,
            ]))

        summary = result["launch_summary"]
        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(summary["ready_count"], 0)
        self.assertEqual(summary["stale_count"], 1)
        self.assertEqual(summary["overall_state"], "NO_READY_BRIEF")
        self.assertEqual(summary["entries"][0]["state"], "STALE_OR_NOT_READY")

    def test_summary_marks_drift_when_fresh_recheck_selects_newer_packet(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            old = self.prepare_brief(root, "old", ttl_sec=180)
            new = self.prepare_brief(root, "new", ttl_sec=300)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "summary"),
                "--scan-root",
                str(old["base"]),
            ]))

        summary = result["launch_summary"]
        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(summary["brief_count"], 1)
        self.assertEqual(summary["drift_count"], 1)
        self.assertEqual(summary["overall_state"], "DRIFT_RECHECK_REQUIRED")
        self.assertEqual(summary["entries"][0]["state"], "DRIFT_RECHECK_REQUIRED")
        self.assertEqual(summary["entries"][0]["original_selected_wsta73_arming_packet"], runner.rel(old["packet"]))
        self.assertEqual(summary["entries"][0]["fresh_selected_wsta73_arming_packet"], runner.rel(new["packet"]))

    def test_summary_excludes_nested_wsta76_recheck_briefs(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.prepare_brief(root, "ready")
            first = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "summary1"),
                "--scan-root",
                str(root),
            ]))
            self.assertEqual(first["decision"], runner.PASS_DECISION)
            second = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "summary2"),
                "--scan-root",
                str(root),
            ]))

        self.assertEqual(second["decision"], runner.PASS_DECISION)
        self.assertEqual(second["launch_summary"]["brief_count"], 1)
        self.assertEqual(second["launch_summary"]["entries"][0]["wsta76_launch_brief"], runner.rel(artifacts["brief"]))

    def test_nonprivate_scan_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(runner.DEFAULT_RUN_BASE / "wsta77-nonprivate-test"),
                "--scan-root",
                tmp,
            ]))

        self.assertEqual(result["decision"], "wsta77-blocked-nonprivate-scan-root")

    def test_public_summary_markdown_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.prepare_brief(root, "ready")
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "summary"),
                "--scan-root",
                str(root),
            ]))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            markdown = (root / "summary" / "wsta77_launch_brief_summary.md").read_text(encoding="utf-8")
        tunnel_domain = "try" + "cloudflare.com"
        http_scheme = "http" + "://"
        https_scheme = "https" + "://"

        for text in (summary_text, template_text, markdown):
            self.assertNotIn(tunnel_domain, text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn(http_scheme, text.lower())
            self.assertNotIn(https_scheme, text.lower())
            self.assertNotIn(runner.wsta76.wsta75.wsta74.wsta73.wsta72.wsta63.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
            self.assertNotIn(runner.wsta76.wsta75.wsta74.wsta73.wsta72.wsta63.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, text)

    def test_print_template_exits_without_summary(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA77 host-only", payload)
        self.assertIn("--scan-root", payload)

    def test_source_keeps_live_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("READY_BRIEF_PRESENT_DEFAULT_OFF", source)
        self.assertIn("wsta77-persistent-launch-brief-summary-pass", source)
        self.assertIn("wsta76_rechecked", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
