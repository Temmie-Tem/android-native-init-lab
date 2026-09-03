from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_twrp_fastbootd_prep_q1.py"
)
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("s20_fastbootd_prep_q1_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FastbootdPrepQ1Tests(unittest.TestCase):
    def _run_dir(self, root: Path) -> Path:
        path = root / MODULE.RUN_ROOT_REL / "run-test"
        path.mkdir(parents=True)
        return path

    def _recovery(self) -> dict:
        return {
            "serial": "SERIAL",
            "node": "1-2.3",
            "serial_sha256": MODULE.base.sha256_text("SERIAL"),
            "topology_sha256": MODULE.base.sha256_text("usb:1-2.3"),
            "boot_id_sha256": MODULE.base.sha256_text("recovery-boot"),
            "other_serial_sha256": [],
            "identity": {
                "uid": "0",
                "twrp_version": "3.7.1_12-AstroForge_v2",
                "incremental": "eng.codeby.20260803.123008",
                "ro_secure": "0",
                "ro_debuggable": "1",
                "usb_config": "mtp,adb",
                "adbd_state": "running",
                "marker_sha256": MODULE.t2_profile.MARKER_SHA256,
            },
            "preflight": dict(MODULE.census.PREFLIGHT_EXPECTED),
        }

    def _prepared(self, run_dir: Path) -> dict:
        recovery = self._recovery()
        return {
            "schema": "s20plus_g986n_twrp_fastbootd_prep_q1_prepared_v1",
            "version": MODULE.VERSION,
            "run_dir": str(run_dir),
            "target": {
                "model": "SM-G986N",
                "device": "y2q",
                "product": "y2qksx",
                "incremental": "G986NKSS8IYC2",
                "serial_sha256": recovery["serial_sha256"],
                "topology_sha256": recovery["topology_sha256"],
                "recovery_boot_id_sha256": recovery["boot_id_sha256"],
                "other_serial_sha256": [],
            },
            "old_terminal_sha256": MODULE.OLD_FINAL_SHA256,
            "old_consumed_sha256": MODULE.OLD_CONSUMED_SHA256,
            "support_sha256": "a" * 64,
            "t2_predecessor_sha256": "b" * 64,
            "starting_identity": recovery["identity"],
            "starting_preflight": dict(MODULE.census.PREFLIGHT_EXPECTED),
            "usb_role_switch_attempts": 0,
            "fastboot_commands": 0,
            "persistent_writes": 0,
            "partition_operations": 0,
            "at": "time",
        }

    def test_plan_is_active_and_never_switches_usb_or_sends_fastboot(self) -> None:
        plan = MODULE.plan()
        self.assertTrue(plan["live_active"])
        self.assertEqual(
            MODULE.normalized_self_sha256(),
            MODULE.EXPECTED_REVIEWED_NORMALIZED_SHA256,
        )
        self.assertEqual(plan["functionfs_mount_attempts"], 1)
        self.assertEqual(plan["service_start_attempts"], 1)
        self.assertEqual(plan["usb_role_switch_attempts"], 0)
        self.assertEqual(plan["fastboot_commands"], 0)
        self.assertEqual(plan["persistent_writes"], 0)
        self.assertEqual(plan["partition_operations"], 0)

    def test_scripts_are_staged_and_do_not_detach_or_rebind(self) -> None:
        prepare = MODULE.PREPARE_SCRIPT
        post = MODULE.POST_SCRIPT
        self.assertEqual(prepare.count("/system/bin/mount -t functionfs"), 1)
        self.assertLess(
            prepare.index('/system/bin/mkdir "$g/functions/ffs.fastboot"'),
            prepare.index("/system/bin/mount -t functionfs"),
        )
        self.assertIn("stage=functionfs-mounted", prepare)
        self.assertIn("stage=configfs-function-created", prepare)
        self.assertIn("stage=service-running", prepare)
        self.assertIn("stage=endpoints-ready", prepare)
        self.assertIn("prep_state=ready-adb-retained", post)
        for forbidden in (
            'printf \'%s\' none > "$g/UDC"',
            'idVendor 0x18D1',
            'idProduct 0x4EE0',
            " fastboot getvar",
            "flash",
            "erase",
            "/dev/block",
            "/data/",
            "reboot",
        ):
            self.assertNotIn(forbidden, prepare + post)

    def test_prepare_classification_preserves_each_stage_prefix(self) -> None:
        lines = MODULE.SUCCESS_OUTPUT.splitlines(keepends=True)
        payload = b""
        for index, line in enumerate(lines, start=1):
            payload += line
            result = MODULE.classify_prepare((0, payload, b""))
            self.assertEqual(result["last_stage"], MODULE.STAGES[index])
            self.assertEqual(result["success"], index == len(lines))
        malformed = MODULE.classify_prepare((0, b"stage=unknown\n", b""))
        self.assertEqual(malformed["last_stage"], "invalid-output")
        self.assertFalse(malformed["success"])

    def test_real_predecessor_terminal_is_exact_and_consumed(self) -> None:
        value = MODULE.validate_predecessor(ROOT)
        self.assertEqual(
            value["verdict"],
            "NO_PROOF_S20PLUS_G986N_TWRP_FASTBOOTD_PREP_RETURNED_HEALTHY",
        )
        self.assertFalse(value["replay_permitted"])
        self.assertFalse(value["prep_proved"])

    def test_connected_probe_writes_intent_before_one_synchronous_prepare(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = self._run_dir(root)
            recovery = self._recovery()
            support = {"support": True}
            calls: list[list[str]] = []

            def command(argv: list[str], _timeout: float, _maximum: int):
                calls.append(argv)
                self.assertEqual(argv[-1], MODULE.PREPARE_SCRIPT)
                self.assertTrue((run_dir / "prep-intent.json").exists())
                return 0, MODULE.SUCCESS_OUTPUT, b""

            with (
                mock.patch.object(MODULE, "LIVE_ACTIVE", True),
                mock.patch.object(MODULE, "require_support", return_value=support),
                mock.patch.object(MODULE, "validate_predecessor", return_value={}),
                mock.patch.object(MODULE.twrp_d0, "validate_t2_predecessor", return_value={}),
                mock.patch.object(MODULE.census, "recovery_snapshot", return_value=recovery),
                mock.patch.object(MODULE, "final_recovery_check", return_value=recovery["identity"]),
                mock.patch.object(MODULE, "validate_probe"),
            ):
                result = MODULE.connected_probe(root, run_dir, command)
            self.assertEqual(len(calls), 1)
            self.assertEqual(result["verdict"], MODULE.PENDING)
            self.assertTrue(result["adb_retained"])
            self.assertEqual(result["usb_role_switch_attempts"], 0)
            self.assertEqual(result["fastboot_commands"], 0)
            self.assertTrue((root / MODULE.RUN_ROOT_REL / MODULE.CONSUMED_NAME).exists())

    def test_non_success_stage_never_runs_post_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = self._run_dir(root)
            recovery = self._recovery()
            support = {"support": True}

            with (
                mock.patch.object(MODULE, "LIVE_ACTIVE", True),
                mock.patch.object(MODULE, "require_support", return_value=support),
                mock.patch.object(MODULE, "validate_predecessor", return_value={}),
                mock.patch.object(MODULE.twrp_d0, "validate_t2_predecessor", return_value={}),
                mock.patch.object(MODULE.census, "recovery_snapshot", return_value=recovery),
                mock.patch.object(MODULE, "final_recovery_check") as post,
            ):
                with self.assertRaises(MODULE.ReturnRequiredError):
                    MODULE.connected_probe(
                        root,
                        run_dir,
                        lambda *_args: (0, b"stage=configfs-function-created\n", b""),
                    )
            post.assert_not_called()
            self.assertFalse((run_dir / "probe-result.json").exists())

    def test_local_intent_cut_reconstructs_consumed_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = self._run_dir(root)
            prepared = self._prepared(run_dir)
            MODULE.acquire_guard(root, run_dir)
            MODULE.base.durable_write(run_dir / "prepared.json", prepared)
            intent = MODULE.create_intent(root, run_dir, prepared)
            (root / MODULE.RUN_ROOT_REL / MODULE.CONSUMED_NAME).unlink()
            self.assertEqual(MODULE.resolve_run(root), run_dir)
            self.assertEqual(
                MODULE.classic.load_json(
                    root / MODULE.RUN_ROOT_REL / MODULE.CONSUMED_NAME, "consumed"
                ),
                intent,
            )

    def test_pre_effect_abort_is_resumable_and_zero_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = self._run_dir(root)
            MODULE.acquire_guard(root, run_dir)
            first = MODULE.abort_pre_effect(root)
            self.assertEqual(first["device_effects"], 0)
            self.assertFalse((root / MODULE.SHARED_GUARD_REL).exists())

            MODULE.acquire_guard(root, run_dir)
            second = MODULE.abort_pre_effect(root)
            self.assertEqual(second, first)
            self.assertFalse((root / MODULE.SHARED_GUARD_REL).exists())

    def test_final_result_validator_rejects_minimal_forgery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = self._run_dir(Path(temporary))
            prepared = self._prepared(run_dir)
            with self.assertRaises(MODULE.PrepProbeError):
                MODULE.validate_final_result(
                    run_dir, prepared, False, {"verdict": MODULE.FINAL_NO_PROOF}
                )

    def test_missing_command_result_is_no_proof_not_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = self._run_dir(root)
            prepared = self._prepared(run_dir)
            MODULE.base.durable_write(run_dir / "prepared.json", prepared)
            MODULE.create_intent(root, run_dir, prepared)
            loaded, proved = MODULE.validate_journal(root, run_dir)
            self.assertEqual(loaded, prepared)
            self.assertFalse(proved)

    def test_forged_success_without_raw_capture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = self._run_dir(root)
            prepared = self._prepared(run_dir)
            MODULE.base.durable_write(run_dir / "prepared.json", prepared)
            intent = MODULE.create_intent(root, run_dir, prepared)
            result = MODULE.classify_prepare((0, MODULE.SUCCESS_OUTPUT, b""))
            result["intent_sha256"] = MODULE.classic.object_sha256(intent)
            MODULE.base.durable_write(run_dir / "prep-command-result.json", result)
            with self.assertRaises(MODULE.PrepProbeError):
                MODULE.validate_journal(root, run_dir)

    def test_abort_refuses_guard_run_outside_probe_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            path = root / MODULE.SHARED_GUARD_REL
            path.parent.mkdir(parents=True)
            MODULE.base.durable_write(
                path,
                {
                    "schema": "s20plus_g986n_twrp_fastbootd_prep_q1_guard_v1",
                    "version": MODULE.VERSION,
                    "action": "attended-t2-fastbootd-prep-q1",
                    "run_dir": str(outside),
                    "unresolved": True,
                    "at": "time",
                },
            )
            with self.assertRaises(MODULE.PrepProbeError):
                MODULE.abort_pre_effect(root)
            self.assertTrue(path.exists())

    def test_contract_records_consumed_q1_pass(self) -> None:
        contract = (
            ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
        ).read_text()
        agents = (ROOT / "AGENTS.md").read_text()
        self.assertIn("TWRP FASTBOOTD PREP Q1 CONSUMED - PASS RETURNED HEALTHY", contract)
        self.assertIn("staged fastbootd preparation Q1 consumed with PASS healthy return", agents)


if __name__ == "__main__":
    unittest.main()
