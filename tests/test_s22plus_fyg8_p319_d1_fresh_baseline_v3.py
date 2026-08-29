from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tests import test_s22plus_fyg8_p319_d1_fresh_baseline_v2 as base


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_d1_fresh_baseline_v3.py"
)
BINDING = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d1_fresh_baseline_v3.json"
)
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_D1_FRESH_BASELINE_CANONICAL_ARM_V3_H0_2026-08-29.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
GOAL = ROOT / "GOAL.md"


class P319D1FreshBaselineV3Test(base.P319D1FreshBaselineV2Test):
    @classmethod
    def setUpClass(cls):
        cls.module = base.load(SOURCE, "p319_d1_v3_test")

    def sandbox(self, *, pass_go=False):
        temporary = tempfile.TemporaryDirectory(prefix="p319-d1-v3-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        parent = root / "run-parent"
        run = parent / "p319-fresh-baseline-3"
        arm = parent / "p319-fresh-baseline-3.arm.json"
        raw_root = parent / "p319-fresh-baseline-3-raw"
        snapshot = root / "adb-snapshot"
        manifest = root / "binding.json"
        patcher = mock.patch.multiple(
            self.module,
            BINDING_MANIFEST=manifest,
            RUN_PARENT=parent,
            RUN_DIR=run,
            RUN_ARM=arm,
            RUN_STOP=run / "stop.json",
            RAW_ROOT=raw_root,
            RAW_ADB_DIR=raw_root / "raw-adb",
            ADB_SNAPSHOT=snapshot,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        payloads = self.module._input_payloads()
        review = (
            {"status": "pass-go", "verdict": self.module.REVIEW_VERDICT}
            if pass_go
            else {"status": "review-pending", "verdict": None}
        )
        manifest.write_bytes(
            self.module.canonical(self.module._expected_manifest(payloads, review))
        )
        return root

    def test_default_self_test_has_no_process_or_device_acquisition(self):
        with mock.patch(
            "subprocess.Popen", side_effect=AssertionError("device/process call")
        ):
            value = self.module.self_test()
        self.assertEqual(value["review_status"], "review-pending")
        self.assertTrue(value["consumed_v2_bound"])
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])

    def test_consumed_v2_evidence_is_exact_semantic_and_never_replayable(self):
        payloads = self.module._input_payloads()
        self.module._validate_consumed_v2(payloads)
        for key, path in (
            ("v2_source", self.module.V2_SOURCE),
            ("v2_binding", self.module.V2_BINDING),
            ("v2_arm", self.module.V2_ARM),
            ("v2_stop", self.module.V2_STOP),
        ):
            self.assertEqual(
                (path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()),
                self.module.EXPECTED[key],
            )
        stop = self.module._strict(payloads["v2_stop"], "consumed V2 stop")
        self.assertFalse(stop["reboot_dispatch_possible"])
        self.assertFalse(stop["private_raw_evidence_preserved"])
        self.assertFalse(stop["result_reusable"])
        self.assertFalse(stop["replay_authorized"])

    def test_canonical_writer_reaches_the_production_validator(self):
        value = self.module.reproduce_canonical_arm_writer_validator(self.inputs())
        self.assertEqual(value["writer"], "pinned_v1._durable_create")
        self.assertEqual(value["validator"], "_arm_complete")
        self.assertTrue(value["canonical"])
        self.assertTrue(value["pre_acquisition_boundary"])
        self.assertFalse(value["device_contact"])

    def test_canonical_arm_duplicate_classification_is_exact(self):
        inputs = self.inputs()
        self.module._durable_arm_canonical(inputs)
        with self.assertRaises(self.module.CanonicalArmAlreadyExists):
            self.module._durable_arm_canonical(inputs)
        original = inputs["v1"]._durable_create

        def unrelated(*_args, **_kwargs):
            raise inputs["v1"].D1FreshBaselineError("other already exists")

        inputs["v1"]._durable_create = unrelated
        try:
            with self.assertRaisesRegex(
                inputs["v1"].D1FreshBaselineError, "other already exists"
            ):
                self.module._durable_arm_canonical(inputs)
        finally:
            inputs["v1"]._durable_create = original

    def test_tracked_binding_is_canonical_pass_go_and_self_bound(self):
        payload = BINDING.read_bytes()
        value = json.loads(payload)
        self.assertEqual(payload, self.module.canonical(value))
        self.assertEqual(
            value["independent_review"],
            {"status": "review-pending", "verdict": None},
        )
        self.assertEqual(value["run"]["ordinal"], "d1-fresh-baseline-3")
        self.assertEqual(value["successor"]["size"], SOURCE.stat().st_size)
        self.assertEqual(
            value["successor"]["sha256"], hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        )
        self.assertEqual(value["consumed_v2"]["ordinal"], "d1-fresh-baseline-2")
        self.assertFalse(value["consumed_v2"]["replay_authorized"])

    def test_report_ledger_and_goal_preserve_v1_and_resolve_only_topic_42(self):
        report = REPORT.read_text(encoding="utf-8")
        for token in (
            "IMPLEMENTED / REVIEW PENDING / NOT ACTIVE",
            "pinned V1 canonical writer",
            "consumed V2",
            "d1-fresh-baseline-3",
            "No token",
            "FRESH_BASELINE_MISSING",
        ):
            self.assertIn(token, report)
        ledger = LEDGER.read_text(encoding="utf-8")
        ordinal = "h0-d1-fresh-baseline-canonical-arm-v3-1"
        rows = [line for line in ledger.splitlines() if f" | {ordinal} | " in line]
        self.assertEqual(len(rows), 1)
        self.assertIn(
            "P319_D1_FRESH_BASELINE_CANONICAL_ARM_V3_IMPLEMENTED_REVIEW_PENDING",
            rows[0],
        )
        self.assertNotIn("PASS_GO", rows[0])
        goal = GOAL.read_text(encoding="utf-8")
        self.assertEqual(len(goal.splitlines()), 900)
        self.assertIn("D1 V3 canonical-arm successor is implemented review-pending", goal)

    def test_run_live_arm_write_cut_is_consumed_and_stopped(self):
        self.sandbox(pass_go=True)
        static = self.module._validated_static_inputs()
        inputs = self.module._validated_execution_inputs(static)

        original_create = inputs["v1"]._durable_create

        def partial_arm(path, value):
            if path == self.module.RUN_ARM:
                path.parent.mkdir(mode=0o700)
                path.write_bytes(b'{"partial":')
                path.chmod(0o400)
                raise OSError("fixture cut")
            return original_create(path, value)

        p318 = inputs["v1"]._load_p318(inputs["v1_inputs"]["p318_payload"])
        with mock.patch.object(
            self.module, "_validated_static_inputs", return_value=static
        ), mock.patch.object(
            self.module, "_validated_execution_inputs", return_value=inputs
        ), mock.patch.object(
            inputs["v1"], "_load_p318", return_value=p318
        ), mock.patch.object(
            inputs["v1"], "_durable_create", side_effect=partial_arm
        ), mock.patch.object(
            p318,
            "_prepare_executable_snapshot",
            side_effect=AssertionError("snapshot must not follow a partial arm"),
        ):
            with self.assertRaisesRegex(
                self.module.SuccessorError, "consumed without replay"
            ):
                self.module.run_live(static["authority"])
        stop = self.module.validate_stop_file()
        self.assertEqual(stop["stage"], "during-arm-publication")
        self.assertFalse(stop["reboot_dispatch_possible"])

    def test_preexisting_or_racing_arm_never_mutates_consumed_namespace(self):
        def snapshot(paths):
            values = {}
            for path in paths:
                if not path.exists() and not path.is_symlink():
                    continue
                if path.is_dir() and not path.is_symlink():
                    children = sorted(
                        item.relative_to(path).as_posix() for item in path.rglob("*")
                    )
                    values[str(path)] = ("directory", children)
                    for item in path.rglob("*"):
                        if item.is_file() and not item.is_symlink():
                            values[str(item)] = (
                                item.stat().st_mode & 0o777,
                                item.stat().st_nlink,
                                hashlib.sha256(item.read_bytes()).hexdigest(),
                            )
                elif path.is_file() and not path.is_symlink():
                    values[str(path)] = (
                        path.stat().st_mode & 0o777,
                        path.stat().st_nlink,
                        hashlib.sha256(path.read_bytes()).hexdigest(),
                    )
            return values

        inputs = self.inputs(pass_go=True)
        static = self.module._validated_static_inputs()
        self.arm(inputs)
        before = snapshot([self.module.RUN_PARENT, self.module.ADB_SNAPSHOT])
        with mock.patch.object(
            self.module, "_validated_static_inputs", return_value=static
        ), mock.patch.object(
            self.module, "_validated_execution_inputs", return_value=inputs
        ):
            with self.assertRaisesRegex(self.module.SuccessorError, "replay is forbidden"):
                self.module.run_live(static["authority"])
        self.assertEqual(snapshot([self.module.RUN_PARENT, self.module.ADB_SNAPSHOT]), before)
        self.assertFalse(self.module.RUN_DIR.exists())
        self.assertFalse(self.module.RAW_ROOT.exists())

        inputs = self.inputs(pass_go=True)
        static = self.module._validated_static_inputs()
        self.complete_host_fixture(inputs)
        before = snapshot([self.module.RUN_PARENT, self.module.ADB_SNAPSHOT])
        with mock.patch.object(
            self.module, "_validated_static_inputs", return_value=static
        ), mock.patch.object(
            self.module, "_validated_execution_inputs", return_value=inputs
        ):
            with self.assertRaisesRegex(self.module.SuccessorError, "replay is forbidden"):
                self.module.run_live(static["authority"])
        self.assertEqual(snapshot([self.module.RUN_PARENT, self.module.ADB_SNAPSHOT]), before)
        self.assertFalse(self.module.RUN_STOP.exists())

        inputs = self.inputs(pass_go=True)
        static = self.module._validated_static_inputs()
        error = inputs["v1"].D1FreshBaselineError(
            f"D1 journal already exists: {self.module.RUN_ARM.name}"
        )
        with mock.patch.object(
            self.module, "_validated_static_inputs", return_value=static
        ), mock.patch.object(
            self.module, "_validated_execution_inputs", return_value=inputs
        ), mock.patch.object(
            self.module, "_preflight_new_run_namespace", return_value=None
        ), mock.patch.object(
            inputs["v1"], "_durable_create", side_effect=error
        ):
            with self.assertRaisesRegex(self.module.SuccessorError, "replay is forbidden"):
                self.module.run_live(static["authority"])
        self.assertFalse(self.module.RUN_ARM.exists())
        self.assertFalse(self.module.RUN_DIR.exists())
        self.assertFalse(self.module.RAW_ROOT.exists())
        self.assertFalse(self.module.ADB_SNAPSHOT.exists())


if __name__ == "__main__":
    unittest.main()
