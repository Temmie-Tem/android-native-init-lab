from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


wsta53 = load_script("workspace/public/src/scripts/server-distro/run_wsta53_persistent_exposure_plan.py")
wsta54 = load_script("workspace/public/src/scripts/server-distro/run_wsta54_private_lease_artifact.py")
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta55_short_lived_public_proof.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta55_short_lived_public_proof.py")


class ServerDistroWsta55ShortLivedPublicProofTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def make_artifact(self, root: Path, ttl_sec: int = 60) -> Path:
        wsta53_args = wsta53.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta53"),
            "--ttl-sec",
            str(ttl_sec),
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--native-confirm-token-source",
            "private",
            "--public-confirm-token-source",
            "private",
        ])
        self.assertEqual(wsta53.run(wsta53_args)["decision"], wsta53.PASS_DECISION)
        wsta54_args = wsta54.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta54"),
            "--wsta53-result-json",
            str(root / "wsta53" / "wsta53_result.json"),
        ])
        result = wsta54.run(wsta54_args)
        self.assertEqual(result["decision"], wsta54.PASS_DECISION)
        return runner.REPO_ROOT / result["private_lease_artifact"]

    def preflight_args(self, root: Path):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta55"),
            "--lease-artifact-json",
            str(self.make_artifact(root)),
        ])

    def live_args(self, root: Path):
        args = self.preflight_args(root)
        args.execute_live_short_lease = True
        args.allow_operator_live = True
        args.allow_native_reboot = True
        args.allow_public_live = True
        args.ack_credentialed_wifi = True
        args.ack_public_exposure = True
        args.ack_packet_filter_mutation = True
        args.force_packet_filter_restore_proof = True
        args.force_ttl_expiry_proof = True
        args.native_confirm_token = runner.wsta45.wsta25.NATIVE_CONFIRM_TOKEN
        args.public_confirm_token = runner.wsta45.PUBLIC_CONFIRM_TOKEN
        return args

    def nested_wsta45_pass(self) -> dict:
        return {
            "scope": "WSTA45 appliance operator wrapper for native-uplink D-public publish",
            "started_utc": "20260704T010000Z",
            "ended_utc": "20260704T010030Z",
            "decision": runner.wsta45.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/example/wsta45",
            "mode": "publish",
            "gate_decision": "ok",
            "profile_contract": {"ok": True, "secret_values_logged": 0},
            "operator_publish_template": runner.wsta45.operator_publish_template(),
            "operator_menu": [],
            "checks": {"wsta43_pass": True, "wsta43_profile_requested": True},
            "safety": {"public_url_value_logged": False, "secret_values_logged": 0},
            "wsta43": {
                "decision": runner.wsta45.wsta43.PASS_DECISION,
                "run_dir": "workspace/private/runs/server-distro/example/wsta43",
                "gate_decision": "ok",
                "checks": {"explicit_live_gate": True, "wsta28_scan_green": True, "wsta42_pass": True},
                "safety": {"public_url_value_logged": False, "secret_values_logged": 0},
                "wsta28": {"decision": "wsta28-reboot-materialization-scan-gate-pass"},
                "wsta42": {
                    "scope": "WSTA42 native-owned STA uplink plus Debian D-public quick Tunnel",
                    "started_utc": "20260704T010005Z",
                    "ended_utc": "20260704T010025Z",
                    "decision": runner.wsta45.wsta43.wsta42.PASS_DECISION,
                    "run_dir": "workspace/private/runs/server-distro/example/wsta42",
                    "local_image_expected_sha256": "a" * 64,
                    "remote_clean_image_enabled": True,
                    "remote_clean_sha_before_value": "a" * 64,
                    "remote_clean_sha_after_value": "a" * 64,
                    "remote_clean_sha_after": {"skipped": True, "source": "remote_clean_sha_before"},
                    "remote_sha_before_value": "a" * 64,
                    "remote_sha_after_value": "a" * 64,
                    "remote_sha_after": {"skipped": True, "source": "remote_sha_before"},
                    "remote_work_restore_from_clean": {"skipped": True, "reason": "work-image-already-clean"},
                    "checks": {
                        "use_native_uplink_profile": True,
                        "native_uplink_profile_confirmed": True,
                        "public_smoke_ok": True,
                        "dpublic_cleanup_ok": True,
                        "packet_filter_restore_ok": True,
                        "native_uplink_profile_cleanup_ok": True,
                        "chroot_cleanup_ok": True,
                        "final_selftest_fail_zero": True,
                        "public_url_value_logged": False,
                        "secret_values_logged": 0,
                    },
                    "safety": {"public_url_value_logged": False, "secret_values_logged": 0},
                    "host_public_smoke": {
                        "http_status": 200,
                        "marker_ok": True,
                        "service_ok": True,
                        "public_exposure_marker_ok": True,
                        "url_redacted": True,
                    },
                    "dpublic_cleanup": {"cleaned": True},
                },
            },
        }

    def aggregate_pass(self) -> dict:
        return {
            "scope": "WSTA48 redacted WSTA result aggregation",
            "result_count": 3,
            "all_pass": True,
            "redaction_guard": {"ok": True},
            "public_url_value_logged": False,
            "secret_values_logged": 0,
            "entries": [],
        }

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(runner.build_arg_parser().parse_args(["--run-dir", str(Path(tmp) / "run")]))

        self.assertEqual(result["decision"], "wsta55-blocked-lease-artifact-required")
        for key in ("device_action", "boot_flash", "native_reboot", "userdata_touch", "switch_root"):
            self.assertFalse(result["safety"][key])

    def test_valid_artifact_preflight_does_not_call_live(self) -> None:
        with self.private_tmp() as tmp:
            args = self.preflight_args(Path(tmp))
            with mock.patch.object(runner.wsta45, "run", side_effect=AssertionError("unexpected live call")):
                result = runner.run(args)

        self.assertEqual(result["decision"], runner.PREFLIGHT_DECISION)
        self.assertTrue(result["checks"]["wsta55_live_ready"])
        self.assertFalse(result["checks"]["live_execution_requested"])
        self.assertFalse(result["safety"]["device_action"])
        self.assertTrue(result["lease_redacted"]["lease_id_present"])
        self.assertTrue(result["lease_redacted"]["lease_id_value_redacted"])

    def test_rejects_long_ttl_artifact_for_short_lived_proof(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta55"),
                "--lease-artifact-json",
                str(self.make_artifact(root, ttl_sec=1800)),
            ]))

        self.assertEqual(result["decision"], "wsta55-blocked-lease-ttl-not-short")

    def test_live_gate_blocks_before_wsta45_without_execute_ack_stack(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            args = self.preflight_args(root)
            args.execute_live_short_lease = True
            with mock.patch.object(runner.wsta45, "run", side_effect=AssertionError("unexpected live call")):
                result = runner.run(args)

        self.assertEqual(result["decision"], "wsta55-blocked-operator-live-allow-required")
        self.assertFalse(result["checks"]["explicit_live_gate"])

    def test_live_success_requires_wsta45_wsta48_cleanup_and_ttl_expiry(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            args = self.live_args(root)
            nested = self.nested_wsta45_pass()
            with mock.patch.object(runner, "pre_live_cleanup", return_value={"ok": True}) as cleanup_call, \
                    mock.patch.object(runner.wsta45, "run", return_value=nested) as live_call, \
                    mock.patch.object(runner.wsta48, "build_aggregate", return_value=self.aggregate_pass()):
                result = runner.run(args)

            self.assertTrue(cleanup_call.called)
            called_args = live_call.call_args.args[0]
            self.assertEqual(called_args.mode, "publish")
            self.assertTrue(called_args.use_native_uplink_profile)
            self.assertTrue(called_args.allow_operator_live)
            self.assertTrue(called_args.ack_packet_filter_mutation)
            self.assertTrue(called_args.force_packet_filter_restore_proof)
            self.assertIn("--bridge-host", called_args.wsta43_args)
            self.assertTrue((root / "wsta55" / "wsta48_result.json").is_file())

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(result["checks"]["wsta45_pass"])
        self.assertTrue(result["checks"]["wsta48_redaction_ok"])
        self.assertTrue(result["checks"]["public_smoke_ok"])
        self.assertTrue(result["checks"]["dpublic_cleanup_ok"])
        self.assertTrue(result["checks"]["packet_filter_restore_ok"])
        self.assertTrue(result["checks"]["final_selftest_fail_zero"])
        self.assertTrue(result["checks"]["ttl_expiry_stops_public"])
        self.assertEqual(result["ttl_expiry"]["public_state_after_expiry"], "PUBLIC_OFF")
        public = runner.public_summary(result)
        self.assertEqual(public["image_prep"]["clean_action"], "reused")
        self.assertEqual(public["image_prep"]["work_action"], "reused")
        public_text = json.dumps(public, sort_keys=True).lower()
        self.assertNotIn("wsta54-", public_text)
        self.assertNotIn("a" * 64, public_text)

    def test_wsta45_args_passes_explicit_packet_filter_image_selection(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            args = self.live_args(root)
            args.local_image = root / "packet-filter-ready.img"
            args.local_image_sha256 = "f" * 64
            args.remote_image = "/mnt/sdext/a90/runtime/packet-filter-ready.img"
            args.remote_clean_image = "/mnt/sdext/a90/runtime/packet-filter-ready.img.clean"

            nested = runner.wsta45_args(args, root)

        self.assertTrue(nested.ack_packet_filter_mutation)
        self.assertTrue(nested.force_packet_filter_restore_proof)
        self.assertIn("--local-image", nested.wsta43_args)
        self.assertIn(str(args.local_image), nested.wsta43_args)
        self.assertIn("--local-image-sha256", nested.wsta43_args)
        self.assertIn("f" * 64, nested.wsta43_args)
        self.assertIn("--remote-image", nested.wsta43_args)
        self.assertIn(args.remote_image, nested.wsta43_args)
        self.assertIn("--remote-clean-image", nested.wsta43_args)
        self.assertIn(args.remote_clean_image, nested.wsta43_args)

    def test_live_result_blocks_if_cleanup_missing(self) -> None:
        with self.private_tmp() as tmp:
            args = self.live_args(Path(tmp))
            nested = self.nested_wsta45_pass()
            nested["wsta43"]["wsta42"]["checks"]["dpublic_cleanup_ok"] = False
            with mock.patch.object(runner, "pre_live_cleanup", return_value={"ok": True}), \
                    mock.patch.object(runner.wsta45, "run", return_value=nested), \
                    mock.patch.object(runner.wsta48, "build_aggregate", return_value=self.aggregate_pass()):
                result = runner.run(args)

        self.assertEqual(result["decision"], "wsta55-blocked-dpublic-cleanup")
        self.assertFalse(result["checks"]["ttl_expiry_stops_public"])

    def test_live_result_blocks_if_packet_filter_restore_missing(self) -> None:
        with self.private_tmp() as tmp:
            args = self.live_args(Path(tmp))
            nested = self.nested_wsta45_pass()
            nested["wsta43"]["wsta42"]["checks"]["packet_filter_restore_ok"] = False
            with mock.patch.object(runner, "pre_live_cleanup", return_value={"ok": True}), \
                    mock.patch.object(runner.wsta45, "run", return_value=nested), \
                    mock.patch.object(runner.wsta48, "build_aggregate", return_value=self.aggregate_pass()):
                result = runner.run(args)

        self.assertEqual(result["decision"], "wsta55-blocked-packet-filter-restore")
        self.assertFalse(result["checks"]["ttl_expiry_stops_public"])

    def test_live_blocks_before_wsta45_when_pre_live_cleanup_fails(self) -> None:
        with self.private_tmp() as tmp:
            args = self.live_args(Path(tmp))
            with mock.patch.object(runner, "pre_live_cleanup", return_value={"ok": False}) as cleanup_call, \
                    mock.patch.object(runner.wsta45, "run", side_effect=AssertionError("unexpected live call")):
                result = runner.run(args)

        self.assertTrue(cleanup_call.called)
        self.assertEqual(result["decision"], "wsta55-blocked-pre-live-cleanup")
        self.assertFalse(result["checks"]["pre_live_cleanup_ok"])

    def test_rejects_expired_artifact(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifact = self.make_artifact(root, ttl_sec=60)
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            issued = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=2)
            expires = issued + dt.timedelta(seconds=60)
            payload["issued_utc"] = issued.strftime("%Y%m%dT%H%M%SZ")
            payload["expires_utc"] = expires.strftime("%Y%m%dT%H%M%SZ")
            artifact.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta55"),
                "--lease-artifact-json",
                str(artifact),
            ]))

        self.assertEqual(result["decision"], "wsta55-blocked-lease-already-expired")

    def test_template_is_redacted_and_does_not_run(self) -> None:
        with mock.patch.object(runner.wsta45, "run", side_effect=AssertionError("unexpected live call")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        text = printed.call_args.args[0]
        self.assertIn("<native-confirm-token>", text)
        self.assertIn("<public-confirm-token>", text)
        self.assertNotIn(runner.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
        self.assertNotIn(runner.wsta45.PUBLIC_CONFIRM_TOKEN, text)

    def test_cloudflared_egress_allowlist_gate_and_nested_args(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            args = self.live_args(root)
            args.enable_cloudflared_egress_allowlist = True

            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta55-blocked-cloudflared-egress-allowlist-proof-required"),
            )
            args.force_cloudflared_egress_allowlist_proof = True
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta55-blocked-cloudflared-egress-route-required"),
            )
            args.cloudflared_egress_dns4 = ["dns-route-redacted"]
            args.cloudflared_egress_tls4 = ["tls-route-redacted"]
            self.assertEqual(runner.explicit_live_gate(args), (True, "ok"))

            nested = runner.wsta45_args(args, root)

        self.assertTrue(nested.enable_cloudflared_egress_allowlist)
        self.assertTrue(nested.force_cloudflared_egress_allowlist_proof)
        self.assertEqual(nested.cloudflared_egress_dns4, ["dns-route-redacted"])
        self.assertEqual(nested.cloudflared_egress_tls4, ["tls-route-redacted"])

    def test_source_keeps_flash_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--execute-live-short-lease", source)
        self.assertIn("--force-ttl-expiry-proof", source)
        self.assertIn("pre_live_cleanup", source)
        self.assertIn('"wifi", "autoconnect", "disable"', source)
        self.assertIn('"wifi", "cleanup"', source)
        self.assertIn("wsta48.build_aggregate", source)
        self.assertIn("wsta45.run", source)
        self.assertIn("packet_filter_restore_ok", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("ssid=", source.lower().replace('"ssid=",', ""))
        self.assertNotIn("psk=", source.lower().replace('"psk=",', ""))


if __name__ == "__main__":
    unittest.main()
