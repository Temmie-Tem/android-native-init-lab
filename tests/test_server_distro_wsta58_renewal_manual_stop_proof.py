from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


wsta53 = load_script("workspace/public/src/scripts/server-distro/run_wsta53_persistent_exposure_plan.py")
wsta54 = load_script("workspace/public/src/scripts/server-distro/run_wsta54_private_lease_artifact.py")
wsta55 = load_script("workspace/public/src/scripts/server-distro/run_wsta55_short_lived_public_proof.py")
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta58_renewal_manual_stop_proof.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta58_renewal_manual_stop_proof.py")


class ServerDistroWsta58RenewalManualStopProofTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def make_artifact(self, root: Path, label: str, ttl_sec: int = 60) -> Path:
        wsta53_args = wsta53.build_arg_parser().parse_args([
            "--run-dir",
            str(root / f"{label}-wsta53"),
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
            str(root / f"{label}-wsta54"),
            "--wsta53-result-json",
            str(root / f"{label}-wsta53" / "wsta53_result.json"),
        ])
        result = wsta54.run(wsta54_args)
        self.assertEqual(result["decision"], wsta54.PASS_DECISION)
        return runner.REPO_ROOT / result["private_lease_artifact"]

    def preflight_args(self, root: Path):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta58"),
            "--initial-lease-artifact-json",
            str(self.make_artifact(root, "initial")),
            "--renewal-lease-artifact-json",
            str(self.make_artifact(root, "renewal")),
        ])

    def live_args(self, root: Path):
        args = self.preflight_args(root)
        args.execute_renewal_manual_stop = True
        args.allow_operator_live = True
        args.allow_native_reboot = True
        args.allow_public_live = True
        args.ack_credentialed_wifi = True
        args.ack_public_exposure = True
        args.force_ttl_expiry_proof = True
        args.force_manual_stop_proof = True
        args.native_confirm_token = runner.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN
        args.public_confirm_token = runner.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN
        return args

    def wsta55_pass(self, label: str) -> dict:
        return {
            "scope": "WSTA55 short-lived persistent public proof",
            "decision": runner.wsta55.PASS_DECISION,
            "run_dir": f"workspace/private/runs/server-distro/example/{label}",
            "gate_decision": "ok",
            "checks": {
                "wsta45_pass": True,
                "wsta48_redaction_ok": True,
                "wsta48_all_pass": True,
                "public_smoke_ok": True,
                "dpublic_cleanup_ok": True,
                "native_uplink_profile_cleanup_ok": True,
                "chroot_cleanup_ok": True,
                "final_selftest_fail_zero": True,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
                "ttl_expiry_stops_public": True,
            },
            "ttl_expiry": {"ttl_expiry_stops_public": True},
            "wsta48_redacted": {"all_pass": True, "redaction_guard_ok": True},
            "safety": {"public_url_value_logged": False, "secret_values_logged": 0},
        }

    def aggregate_pass(self) -> dict:
        return {
            "scope": "WSTA48 redacted WSTA result aggregation",
            "result_count": 10,
            "all_pass": True,
            "redaction_guard": {"ok": True},
            "public_url_value_logged": False,
            "secret_values_logged": 0,
            "entries": [],
        }

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(runner.build_arg_parser().parse_args(["--run-dir", str(Path(tmp) / "run")]))

        self.assertEqual(result["decision"], "wsta58-blocked-initial-lease-artifact-required")
        for key in ("device_action", "boot_flash", "native_reboot", "userdata_touch", "switch_root"):
            self.assertFalse(result["safety"][key])

    def test_valid_pair_preflight_does_not_call_live(self) -> None:
        with self.private_tmp() as tmp:
            args = self.preflight_args(Path(tmp))
            with mock.patch.object(runner.wsta55, "run", side_effect=AssertionError("unexpected live call")):
                result = runner.run(args)

        self.assertEqual(result["decision"], runner.PREFLIGHT_DECISION)
        self.assertTrue(result["checks"]["wsta58_live_ready"])
        self.assertTrue(result["checks"]["distinct_lease_ids"])
        self.assertFalse(result["checks"]["live_execution_requested"])
        self.assertFalse(result["safety"]["device_action"])
        self.assertTrue(result["lease_pair_redacted"]["initial"]["lease_id_value_redacted"])
        self.assertTrue(result["lease_pair_redacted"]["renewal"]["lease_id_value_redacted"])

    def test_rejects_same_lease_for_renewal(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifact = self.make_artifact(root, "same")
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta58"),
                "--initial-lease-artifact-json",
                str(artifact),
                "--renewal-lease-artifact-json",
                str(artifact),
            ]))

        self.assertEqual(result["decision"], "wsta58-blocked-renewal-lease-not-distinct")

    def test_live_gate_blocks_before_wsta55_without_execute_ack_stack(self) -> None:
        with self.private_tmp() as tmp:
            args = self.preflight_args(Path(tmp))
            args.execute_renewal_manual_stop = True
            with mock.patch.object(runner.wsta55, "run", side_effect=AssertionError("unexpected live call")):
                result = runner.run(args)

        self.assertEqual(result["decision"], "wsta58-blocked-operator-live-allow-required")
        self.assertFalse(result["checks"]["explicit_live_gate"])

    def test_live_success_requires_two_wsta55_runs_manual_stop_and_redaction(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            args = self.live_args(root)
            with mock.patch.object(runner.wsta55, "run", side_effect=[
                        self.wsta55_pass("initial"),
                        self.wsta55_pass("renewal"),
                    ]) as live_call, \
                    mock.patch.object(runner, "manual_stop_cleanup", return_value={
                        "ok": True,
                        "manual_stop_requested": True,
                        "manual_stop_public_state": "PUBLIC_OFF",
                        "public_url_value_logged": False,
                        "secret_values_logged": 0,
                    }) as stop_call, \
                    mock.patch.object(runner.wsta48, "build_aggregate", return_value=self.aggregate_pass()):
                result = runner.run(args)

        self.assertEqual(live_call.call_count, 2)
        self.assertTrue(stop_call.called)
        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(result["checks"]["initial_wsta55_pass"])
        self.assertTrue(result["checks"]["renewal_wsta55_pass"])
        self.assertTrue(result["checks"]["manual_stop_cleanup_ok"])
        self.assertTrue(result["checks"]["wsta48_redaction_ok"])
        self.assertNotIn("wsta54-", json.dumps(runner.public_summary(result), sort_keys=True).lower())

    def test_live_blocks_when_manual_stop_cleanup_fails(self) -> None:
        with self.private_tmp() as tmp:
            args = self.live_args(Path(tmp))
            with mock.patch.object(runner.wsta55, "run", side_effect=[
                        self.wsta55_pass("initial"),
                        self.wsta55_pass("renewal"),
                    ]), \
                    mock.patch.object(runner, "manual_stop_cleanup", return_value={
                        "ok": False,
                        "manual_stop_public_state": "INCIDENT_STOP",
                        "public_url_value_logged": False,
                        "secret_values_logged": 0,
                    }), \
                    mock.patch.object(runner.wsta48, "build_aggregate", return_value=self.aggregate_pass()):
                result = runner.run(args)

        self.assertEqual(result["decision"], "wsta58-blocked-manual-stop-cleanup")

    def test_template_is_redacted_and_does_not_run(self) -> None:
        with mock.patch.object(runner.wsta55, "run", side_effect=AssertionError("unexpected live call")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        text = printed.call_args.args[0]
        self.assertIn("<native-confirm-token>", text)
        self.assertIn("<public-confirm-token>", text)
        self.assertNotIn(runner.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
        self.assertNotIn(runner.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, text)

    def test_source_keeps_flash_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--execute-renewal-manual-stop", source)
        self.assertIn("--force-manual-stop-proof", source)
        self.assertIn("wsta55.run", source)
        self.assertIn("wsta48.build_aggregate", source)
        self.assertIn("manual_stop_cleanup", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
