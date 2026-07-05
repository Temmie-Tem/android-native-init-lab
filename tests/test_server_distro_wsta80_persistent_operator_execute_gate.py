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
wsta77 = load_script("workspace/public/src/scripts/server-distro/run_wsta77_persistent_launch_brief_summary.py")
wsta78 = load_script("workspace/public/src/scripts/server-distro/run_wsta78_persistent_operator_packet.py")
wsta79 = load_script("workspace/public/src/scripts/server-distro/run_wsta79_persistent_operator_packet_status.py")
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta80_persistent_operator_execute_gate.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta80_persistent_operator_execute_gate.py")


class ServerDistroWsta80PersistentOperatorExecuteGateTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def prepare_status(self, root: Path, ttl_sec: int = 300) -> dict[str, Path]:
        prepare_args = wsta72.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "prepare"),
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
            str(root / "packet"),
            "--wsta72-prepare-to-arm-json",
            str(root / "prepare" / "wsta72_prepare_to_arm.json"),
        ])
        self.assertEqual(wsta73.run(packet_args)["decision"], wsta73.PASS_DECISION)
        inventory_args = wsta75.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "inventory"),
            "--scan-root",
            str(root),
        ])
        self.assertEqual(wsta75.run(inventory_args)["decision"], wsta75.PASS_DECISION)
        brief_args = wsta76.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "brief"),
            "--wsta75-arming-inventory-json",
            str(root / "inventory" / "wsta75_arming_inventory.json"),
        ])
        self.assertEqual(wsta76.run(brief_args)["decision"], wsta76.PASS_DECISION)
        summary_args = wsta77.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "summary"),
            "--scan-root",
            str(root),
        ])
        self.assertEqual(wsta77.run(summary_args)["decision"], wsta77.PASS_DECISION)
        operator_args = wsta78.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "operator"),
            "--wsta77-launch-summary-json",
            str(root / "summary" / "wsta77_launch_brief_summary.json"),
        ])
        self.assertEqual(wsta78.run(operator_args)["decision"], wsta78.PASS_DECISION)
        status_args = wsta79.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "status"),
            "--wsta78-operator-packet-json",
            str(root / "operator" / "wsta78_operator_packet.json"),
        ])
        self.assertEqual(wsta79.run(status_args)["decision"], wsta79.PASS_DECISION)
        return {
            "status": root / "status" / "wsta79_operator_packet_status.json",
            "operator": root / "operator" / "wsta78_operator_packet.json",
            "brief": root / "brief" / "wsta76_launch_brief.json",
            "packet": root / "packet" / "wsta73_arming_packet.json",
            "initial": root / "prepare" / "wsta63" / "initial-wsta54" / "wsta54_private_lease.json",
        }

    def stale_status(self, root: Path) -> Path:
        artifacts = self.prepare_status(root, ttl_sec=60)
        initial = json.loads(artifacts["initial"].read_text(encoding="utf-8"))
        expires = runner.wsta79.wsta78.wsta77.wsta76.wsta75.wsta74.wsta73.wsta72.wsta67.wsta65.wsta64.parse_utc_stamp(initial["expires_utc"])
        self.assertIsNotNone(expires)
        later = runner.utc_stamp(expires - runner._dt.timedelta(seconds=10))
        stale_args = wsta79.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "stale-status"),
            "--wsta78-operator-packet-json",
            str(artifacts["operator"]),
            "--min-initial-seconds-remaining",
            "30",
            "--now-utc",
            later,
        ])
        self.assertEqual(wsta79.run(stale_args)["decision"], wsta79.PASS_DECISION)
        return root / "stale-status" / "wsta79_operator_packet_status.json"

    def fake_wsta58_pass(self) -> dict:
        return {
            "decision": runner.wsta58.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/example/wsta58",
            "gate_decision": "ok",
            "lease_pair_redacted": {
                "initial": {"lease_id_value_redacted": True},
                "renewal": {"lease_id_value_redacted": True},
            },
            "checks": {
                "initial_wsta55_pass": True,
                "renewal_wsta55_pass": True,
                "manual_stop_cleanup_ok": True,
                "wsta48_redaction_ok": True,
                "wsta48_all_pass": True,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "manual_stop": {"manual_stop_public_state": "PUBLIC_OFF"},
            "wsta48_redacted": {"all_pass": True, "redaction_guard_ok": True},
            "safety": {"public_url_value_logged": False, "secret_values_logged": 0},
        }

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            with mock.patch.object(runner.wsta58, "run", side_effect=AssertionError("unexpected WSTA58 live")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "gate"),
                ]))

        self.assertEqual(result["decision"], "wsta80-blocked-status-required")
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

    def test_ready_status_preflight_writes_execute_gate_without_live(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.prepare_status(root)
            with mock.patch.object(runner.wsta58, "run", side_effect=AssertionError("unexpected WSTA58 live")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "gate"),
                    "--wsta79-operator-packet-status-json",
                    str(artifacts["status"]),
                ]))
            saved = json.loads((root / "gate" / "wsta80_execute_gate.json").read_text(encoding="utf-8"))
            markdown = (root / "gate" / "wsta80_execute_gate.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PREFLIGHT_DECISION)
        self.assertEqual(saved["decision"], runner.PREFLIGHT_DECISION)
        gate = result["execute_gate"]
        self.assertEqual(gate["state"], "READY_FOR_EXPLICIT_WSTA58_LIVE_GATE")
        self.assertEqual(gate["selected_wsta76_launch_brief"], runner.rel(artifacts["brief"]))
        self.assertEqual(gate["selected_wsta73_arming_packet"], runner.rel(artifacts["packet"]))
        self.assertIn("<native-confirm-token>", json.dumps(gate["wsta58_live_command_template"]))
        self.assertIn("<public-confirm-token>", json.dumps(gate["wsta58_live_command_template"]))
        self.assertIn("explicit-wsta58-gate-required", gate["execution_guardrails"])
        self.assertIn("packet-filter-apply-before-public-exposure", gate["execution_guardrails"])
        self.assertTrue(gate["packet_filter_hardening_ready"])
        self.assertEqual(gate["packet_filter_hardening"]["state"], "PACKET_FILTER_REQUIRED_DEFAULT_OFF")
        self.assertFalse(result["checks"]["live_execution_requested"])
        self.assertTrue(result["checks"]["packet_filter_hardening_ready"])
        self.assertIn("WSTA Persistent Operator Execute Gate", markdown)
        self.assertIn("Packet Filter Hardening", markdown)

    def test_stale_status_blocks_before_live(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status = self.stale_status(root)
            with mock.patch.object(runner.wsta58, "run", side_effect=AssertionError("unexpected WSTA58 live")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "gate"),
                    "--wsta79-operator-packet-status-json",
                    str(status),
                ]))

        self.assertEqual(result["decision"], "wsta80-blocked-status-not-ready")
        self.assertEqual(result["gate_detail"]["state"], "STALE_OR_NOT_READY")

    def test_nonpass_status_is_rejected(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status = root / "bad" / "wsta79_operator_packet_status.json"
            status.parent.mkdir(parents=True)
            status.write_text(json.dumps({
                "decision": "wsta79-blocked-operator-packet-not-pass",
                "operator_packet_status": {},
            }), encoding="utf-8")
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "gate"),
                "--wsta79-operator-packet-status-json",
                str(status),
            ]))

        self.assertEqual(result["decision"], "wsta80-blocked-status-not-pass")

    def test_live_gate_blocks_without_full_ack_stack(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.prepare_status(root)
            with mock.patch.object(runner.wsta58, "run", side_effect=AssertionError("unexpected WSTA58 live")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "gate"),
                    "--wsta79-operator-packet-status-json",
                    str(artifacts["status"]),
                    "--execute-wsta58-from-status",
                ]))

        self.assertEqual(result["decision"], "wsta80-blocked-operator-live-allow-required")
        self.assertTrue(result["checks"]["live_execution_requested"])
        self.assertFalse(result["checks"]["explicit_live_gate"])

    def test_live_gate_requires_packet_filter_ack_and_restore_proof(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.prepare_status(root)
            base = [
                "--run-dir",
                str(root / "gate"),
                "--wsta79-operator-packet-status-json",
                str(artifacts["status"]),
                "--execute-wsta58-from-status",
                "--allow-operator-live",
                "--allow-native-reboot",
                "--allow-public-live",
                "--ack-credentialed-wifi",
                "--ack-public-exposure",
                "--force-ttl-expiry-proof",
                "--force-manual-stop-proof",
                "--native-confirm-token",
                runner.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN,
                "--public-confirm-token",
                runner.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN,
            ]
            with mock.patch.object(runner.wsta58, "run", side_effect=AssertionError("unexpected WSTA58 live")):
                missing_ack = runner.run(runner.build_arg_parser().parse_args(base))
                missing_restore = runner.run(runner.build_arg_parser().parse_args([
                    *base,
                    "--ack-packet-filter-mutation",
                ]))

        self.assertEqual(missing_ack["decision"], "wsta80-blocked-packet-filter-mutation-ack-required")
        self.assertFalse(missing_ack["checks"]["explicit_live_gate"])
        self.assertEqual(missing_restore["decision"], "wsta80-blocked-packet-filter-restore-proof-required")
        self.assertFalse(missing_restore["checks"]["explicit_live_gate"])

    def test_cloudflared_egress_allowlist_gate_requires_proof_and_routes(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.prepare_status(root)
            base = [
                "--run-dir",
                str(root / "gate"),
                "--wsta79-operator-packet-status-json",
                str(artifacts["status"]),
                "--execute-wsta58-from-status",
                "--allow-operator-live",
                "--allow-native-reboot",
                "--allow-public-live",
                "--ack-credentialed-wifi",
                "--ack-public-exposure",
                "--ack-packet-filter-mutation",
                "--force-packet-filter-restore-proof",
                "--force-ttl-expiry-proof",
                "--force-manual-stop-proof",
                "--enable-cloudflared-egress-allowlist",
                "--native-confirm-token",
                runner.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN,
                "--public-confirm-token",
                runner.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN,
            ]
            with mock.patch.object(runner.wsta58, "run", side_effect=AssertionError("unexpected WSTA58 live")):
                missing_proof = runner.run(runner.build_arg_parser().parse_args(base))
                missing_route = runner.run(runner.build_arg_parser().parse_args([
                    *base,
                    "--force-cloudflared-egress-allowlist-proof",
                ]))

        self.assertEqual(
            missing_proof["decision"],
            "wsta80-blocked-cloudflared-egress-allowlist-proof-required",
        )
        self.assertEqual(missing_route["decision"], "wsta80-blocked-cloudflared-egress-route-required")
        self.assertFalse(missing_proof["checks"]["explicit_live_gate"])
        self.assertFalse(missing_route["checks"]["explicit_live_gate"])

    def test_live_gate_delegates_to_wsta58_only_after_explicit_ack_stack(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.prepare_status(root)
            with mock.patch.object(runner.wsta58, "run", return_value=self.fake_wsta58_pass()) as delegated:
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "gate"),
                    "--wsta79-operator-packet-status-json",
                    str(artifacts["status"]),
                    "--execute-wsta58-from-status",
                    "--allow-operator-live",
                    "--allow-native-reboot",
                    "--allow-public-live",
                    "--ack-credentialed-wifi",
                    "--ack-public-exposure",
                    "--ack-packet-filter-mutation",
                    "--force-packet-filter-restore-proof",
                    "--force-ttl-expiry-proof",
                    "--force-manual-stop-proof",
                    "--native-confirm-token",
                    runner.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN,
                    "--public-confirm-token",
                    runner.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN,
                    "--local-image",
                    str(root / "packet-filter-ready.img"),
                    "--local-image-sha256",
                    "d" * 64,
                    "--remote-image",
                    "/mnt/sdext/a90/runtime/packet-filter-ready.img",
                    "--remote-clean-image",
                    "/mnt/sdext/a90/runtime/packet-filter-ready.img.clean",
                    "--enable-cloudflared-egress-allowlist",
                    "--force-cloudflared-egress-allowlist-proof",
                    "--cloudflared-egress-dns4",
                    "dns-route-redacted",
                    "--cloudflared-egress-tls4",
                    "tls-route-redacted",
                ]))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(delegated.call_count, 1)
        call_args = delegated.call_args.args[0]
        self.assertTrue(call_args.execute_renewal_manual_stop)
        self.assertEqual(call_args.native_confirm_token, runner.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN)
        self.assertEqual(call_args.public_confirm_token, runner.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN)
        self.assertTrue(call_args.ack_packet_filter_mutation)
        self.assertTrue(call_args.force_packet_filter_restore_proof)
        self.assertEqual(call_args.local_image, root / "packet-filter-ready.img")
        self.assertEqual(call_args.local_image_sha256, "d" * 64)
        self.assertEqual(call_args.remote_image, "/mnt/sdext/a90/runtime/packet-filter-ready.img")
        self.assertEqual(call_args.remote_clean_image, "/mnt/sdext/a90/runtime/packet-filter-ready.img.clean")
        self.assertTrue(call_args.enable_cloudflared_egress_allowlist)
        self.assertTrue(call_args.force_cloudflared_egress_allowlist_proof)
        self.assertEqual(call_args.cloudflared_egress_dns4, ["dns-route-redacted"])
        self.assertEqual(call_args.cloudflared_egress_tls4, ["tls-route-redacted"])
        public_text = json.dumps(runner.public_summary(result), sort_keys=True)
        self.assertNotIn(runner.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, public_text)
        self.assertNotIn(runner.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, public_text)

    def test_public_summary_markdown_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.prepare_status(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "gate"),
                "--wsta79-operator-packet-status-json",
                str(artifacts["status"]),
            ]))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            markdown = (root / "gate" / "wsta80_execute_gate.md").read_text(encoding="utf-8")
        tunnel_domain = "try" + "cloudflare.com"
        http_scheme = "http" + "://"
        https_scheme = "https" + "://"

        for text in (summary_text, template_text, markdown):
            self.assertNotIn(tunnel_domain, text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn(http_scheme, text.lower())
            self.assertNotIn(https_scheme, text.lower())
            self.assertNotIn(runner.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
            self.assertNotIn(runner.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, text)

    def test_print_template_exits_without_gate(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA80 host-only", payload)
        self.assertIn("--wsta79-operator-packet-status-json", payload)
        self.assertIn("<native-confirm-token>", payload)
        self.assertIn("<public-confirm-token>", payload)

    def test_source_keeps_live_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("READY_FOR_EXPLICIT_WSTA58_LIVE_GATE", source)
        self.assertIn("wsta80-persistent-operator-execute-gate-preflight-pass", source)
        self.assertIn("--execute-wsta58-from-status", source)
        self.assertIn("wsta58.run", source)
        self.assertIn("packet_filter_hardening_ready", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
