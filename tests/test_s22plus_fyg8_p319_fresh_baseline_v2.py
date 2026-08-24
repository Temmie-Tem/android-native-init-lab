from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from tests import test_s22plus_fyg8_p319_d1_fresh_baseline_v2 as d1_fixture_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
REDUCER = SCRIPT_DIR / "s22plus_fyg8_p319_fresh_baseline_capability_v2.py"
D0 = SCRIPT_DIR / "s22plus_fyg8_p319_d0_fresh_baseline_v2.py"
BINDING = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d0_fresh_baseline_v2.json"
)
INTEGRATION = SCRIPT_DIR / "s22plus_fyg8_p319_process_v2_integration_qualification.py"
REPORT = ROOT / (
    "docs/reports/S22PLUS_FYG8_P319_D0_FRESH_BASELINE_V2_REPIN_H0_2026-08-24.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
GOAL = ROOT / "GOAL.md"
V1_IDENTITIES = {
    SCRIPT_DIR / "s22plus_fyg8_p319_d0_fresh_baseline.py": (
        71975,
        "c1a7f82ff9a7e9ca555cf38a9f8addaf7d287f7a5560057b9be49899c631062f",
    ),
    SCRIPT_DIR / "s22plus_fyg8_p319_fresh_baseline_capability.py": (
        64375,
        "2729426d63c512b6fcecd1bb4b6c6b8f399882b317e02b758080ae9add0cb17c",
    ),
    ROOT / (
        "workspace/public/src/device-action/bindings/"
        "s22plus_fyg8_p319_d0_fresh_baseline_v1.json"
    ): (
        14240,
        "34203813fe3c4bf979a7dd2bc575ade80f935eec1ca7fdedbae8096e8822c848",
    ),
}


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class P319FreshBaselineV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reducer = load(REDUCER, "p319_fresh_v2_test")
        cls.d0 = load(D0, "p319_d0_v2_contract_test")
        cls.v1_d0 = load(
            SCRIPT_DIR / "s22plus_fyg8_p319_d0_fresh_baseline.py",
            "p319_d0_v1_preserved_test",
        )
        d1_fixture_module.P319D1FreshBaselineV2Test.setUpClass()

    def d1_fixture(self):
        helper = d1_fixture_module.P319D1FreshBaselineV2Test(methodName="runTest")
        inputs = helper.inputs(pass_go=True)
        result, _client = helper.complete_host_fixture(inputs)
        return helper, inputs, result

    def reducer_d1_context(self, helper, inputs):
        reducer = self.reducer
        return mock.patch.multiple(
            reducer,
            RUN_DIR=helper.module.RUN_DIR,
            RUN_ARM=helper.module.RUN_ARM,
            DEFAULT_D1=helper.module.RUN_DIR / "result.json",
            D1_ADB_SNAPSHOT=helper.module.ADB_SNAPSHOT,
        ), mock.patch.object(
            reducer,
            "_d1_v2_context",
            return_value=(
                helper.module,
                inputs,
                inputs["manifest_receipt"],
                inputs["approval_sha256"],
            ),
        )

    def validate_fixture(self, helper, inputs, value):
        path_patch, context_patch = self.reducer_d1_context(helper, inputs)
        with path_patch, context_patch:
            return self.reducer._validate_d1(
                value,
                self.reducer._baseline_design_identity(),
                self.reducer._current_candidate_identity(),
                self.reducer._profile(),
                helper.module.RUN_DIR / "result.json",
            )

    def test_v1_d0_reducer_and_binding_are_byte_preserved(self):
        for path, expected in V1_IDENTITIES.items():
            payload = path.read_bytes()
            self.assertEqual((len(payload), hashlib.sha256(payload).hexdigest()), expected)

    def test_binding_is_canonical_review_pending_and_binds_exact_d1_v2(self):
        payload = BINDING.read_bytes()
        value = json.loads(payload)
        self.assertEqual(payload, self.d0.canonical(value))
        self.assertEqual(
            value["independent_review"],
            {"status": "review-pending", "verdict": None},
        )
        self.assertEqual(value["schema"], self.d0.BINDING_SCHEMA)
        self.assertEqual(value["binding_id"], self.d0.BINDING_ID)
        self.assertEqual(
            value["inputs"]["d1_source"],
            {
                "path": self.d0._relative(self.d0.D1_SOURCE),
                "size": 66357,
                "sha256": (
                    "9443c81cd51e23a24f48a0f43573e1449cfa188b3cd1c69e6f6f11644d15d478"
                ),
            },
        )
        self.assertEqual(
            value["inputs"]["d1_execution_binding"],
            {
                "path": self.d0._relative(self.d0.D1_BINDING),
                "size": 5351,
                "sha256": (
                    "65e2953ecdcb55a0b5b21614e181c7ed8fe4daafaadda5e7319ae142ad9fbae9"
                ),
            },
        )
        self.assertEqual(value["d1_dependency"]["result_schema"], self.reducer.D1_SCHEMA)
        self.assertEqual(value["d1_dependency"]["result_path"], self.d0._relative(self.d0.D1_RESULT))

    def test_current_missing_d1_v2_result_fails_closed_without_output(self):
        self.assertFalse(self.reducer.DEFAULT_D1.exists())
        self.assertFalse(self.reducer.DEFAULT_D0.exists())
        self.assertFalse(self.reducer.DEFAULT_OUT.exists())
        with self.assertRaises(self.reducer.FreshBaselineError):
            self.reducer.normalize(self.reducer.DEFAULT_D1, self.reducer.DEFAULT_D0)
        self.assertFalse(self.reducer.DEFAULT_OUT.exists())

    def test_review_pending_gate_blocks_before_execution_d1_or_arm(self):
        static = self.d0._validated_static_inputs()
        self.assertEqual(static["manifest"]["independent_review"]["status"], "review-pending")
        with mock.patch.object(self.d0, "_validated_execution_inputs") as execution, mock.patch.object(
            self.d0, "_load_d1_evidence"
        ) as d1, mock.patch.object(self.d0, "_durable_create") as durable:
            with self.assertRaises(self.d0.D0FreshBaselineError):
                self.d0.run_live(static["authority"])
            execution.assert_not_called()
            d1.assert_not_called()
            durable.assert_not_called()

    def test_exact_d1_v2_result_is_validated_by_pinned_v2_authority(self):
        helper, inputs, value = self.d1_fixture()
        self.addCleanup(helper.doCleanups)
        validated = self.validate_fixture(helper, inputs, value)
        self.assertEqual(validated["after"], value["after"])
        self.assertEqual(validated["selection"], value["selection"])
        self.assertTrue(validated["raw_evidence"]["complete"])

    def test_d1_v2_manifest_journal_raw_and_zero_effect_mutations_reject(self):
        mutators = (
            lambda value: value.__setitem__("approval_sha256", "0" * 64),
            lambda value: value["arm"].__setitem__("sha256", "0" * 64),
            lambda value: value["start"].__setitem__("sha256", "0" * 64),
            lambda value: value["adb_snapshot"].__setitem__("present", False),
            lambda value: value["raw_evidence"].__setitem__("complete", False),
            lambda value: value["after"].__setitem__(
                "boot_id_sha256", value["before"]["boot_id_sha256"]
            ),
            lambda value: value["selection"].__setitem__("other_targets_commanded", True),
            lambda value: value.__setitem__("replay_authorized", True),
        )
        for mutate in mutators:
            helper, inputs, value = self.d1_fixture()
            try:
                changed = copy.deepcopy(value)
                mutate(changed)
                with self.assertRaises(self.reducer.FreshBaselineError):
                    self.validate_fixture(helper, inputs, changed)
            finally:
                helper.doCleanups()

    def test_foreign_canonical_arm_or_start_with_matching_result_receipt_rejects(self):
        for journal_name in ("arm", "start"):
            helper, inputs, value = self.d1_fixture()
            try:
                journal = (
                    helper.module.RUN_ARM
                    if journal_name == "arm"
                    else helper.module.RUN_DIR / "start.json"
                )
                journal.chmod(0o600)
                journal.write_bytes(helper.module.canonical({"foreign": journal_name}))
                journal.chmod(0o400)
                changed = copy.deepcopy(value)
                changed[journal_name] = helper.module._direct_receipt(
                    journal, f"foreign {journal_name}"
                )
                result_path = helper.module.RUN_DIR / "result.json"
                result_path.chmod(0o600)
                result_path.write_bytes(helper.module.canonical(changed))
                result_path.chmod(0o400)

                # The reviewed D1 result predicate binds the direct receipt but
                # does not itself apply the arm/start semantic predicates.  The
                # D0 reducer must apply those predicates to the reopened files.
                self.assertTrue(helper.module._result_complete(changed, inputs))
                with self.assertRaises(self.reducer.FreshBaselineError):
                    self.validate_fixture(helper, inputs, changed)
            finally:
                helper.doCleanups()

    def test_schema_valid_start_with_foreign_before_and_selection_rejects(self):
        helper, inputs, value = self.d1_fixture()
        self.addCleanup(helper.doCleanups)
        start_path = helper.module.RUN_DIR / "start.json"
        start_value = helper.module._strict(
            helper.module._stable(
                start_path,
                "fixture D1 V2 start",
                maximum=512 * 1024,
                mode=0o400,
            ),
            "fixture D1 V2 start",
        )
        start_value["before"]["boot_id_sha256"] = "a" * 64
        start_value["selection"]["selected_serial_sha256"] = "b" * 64
        self.assertTrue(helper.module._start_complete(start_value, inputs))
        start_path.chmod(0o600)
        start_path.write_bytes(helper.module.canonical(start_value))
        start_path.chmod(0o400)

        changed = copy.deepcopy(value)
        changed["start"] = helper.module._direct_receipt(
            start_path, "schema-valid foreign start"
        )
        result_path = helper.module.RUN_DIR / "result.json"
        result_path.chmod(0o600)
        result_path.write_bytes(helper.module.canonical(changed))
        result_path.chmod(0o400)

        self.assertTrue(helper.module._result_complete(changed, inputs))
        with self.assertRaises(self.reducer.FreshBaselineError):
            self.validate_fixture(helper, inputs, changed)

    def test_v1_result_and_v2_stop_cannot_substitute_for_d1_v2_success(self):
        helper, inputs, value = self.d1_fixture()
        self.addCleanup(helper.doCleanups)
        v1 = copy.deepcopy(value)
        v1["schema"] = "s22plus_fyg8_p319_d1_fresh_baseline_v1_result"
        with self.assertRaises(self.reducer.FreshBaselineError):
            self.validate_fixture(helper, inputs, v1)
        stop = {
            "schema": helper.module.STOP_SCHEMA,
            "verdict": helper.module.STOP_VERDICT,
        }
        with self.assertRaises(self.reducer.FreshBaselineError):
            self.validate_fixture(helper, inputs, stop)

    def test_d1_d0_and_published_receipt_paths_are_exact_and_cli_closed(self):
        helper, _inputs, value = self.d1_fixture()
        self.addCleanup(helper.doCleanups)
        fixed_d1 = helper.module.RUN_DIR / "result.json"
        alternate_d1 = helper.module.RUN_DIR.parent / "alternate-d1.json"
        alternate_d1.write_bytes(fixed_d1.read_bytes())
        alternate_d1.chmod(0o400)
        relative_d1 = Path(os.path.relpath(fixed_d1, Path.cwd()))
        with mock.patch.object(self.reducer, "DEFAULT_D1", fixed_d1):
            for rejected in (alternate_d1, relative_d1):
                with self.assertRaisesRegex(
                    self.reducer.FreshBaselineError,
                    "outside the fixed namespace",
                ):
                    self.reducer._validate_d1(
                        value, {}, {}, {}, rejected
                    )

        with tempfile.TemporaryDirectory(prefix="p319-fixed-output-") as name:
            root = Path(name).resolve()
            fixed_out = root / "fresh-baseline.json"
            alternate_out = root / "alternate-fresh-baseline.json"
            with mock.patch.object(self.reducer, "DEFAULT_OUT", fixed_out):
                self.reducer.publish_exclusive(fixed_out, {})
                with mock.patch.object(
                    self.reducer, "normalize", return_value={}
                ), mock.patch.object(
                    self.reducer, "validate_result", return_value={}
                ):
                    accepted = self.reducer.validate_published_result(fixed_out)
                self.assertTrue(accepted["authoritative"])
                alternate_out.write_bytes(fixed_out.read_bytes())
                alternate_out.chmod(0o400)
                with mock.patch.object(self.reducer, "normalize") as normalize:
                    with self.assertRaisesRegex(
                        self.reducer.FreshBaselineError,
                        "outside the fixed namespace",
                    ):
                        self.reducer.validate_published_result(alternate_out)
                    normalize.assert_not_called()
                with self.assertRaisesRegex(
                    self.reducer.FreshBaselineError,
                    "outside the fixed namespace",
                ):
                    self.reducer.publish_exclusive(alternate_out, {})

                cli_out = root / "cli-alternate.json"
                with mock.patch.object(
                    self.reducer, "normalize", return_value={}
                ):
                    self.assertEqual(
                        self.reducer.main(
                            [
                                "--d1", str(fixed_d1),
                                "--d0", str(self.reducer.DEFAULT_D0),
                                "--out", str(cli_out),
                            ]
                        ),
                        2,
                    )
                self.assertFalse(cli_out.exists())

            fixed_d0 = root / "fixed-d0.json"
            alternate_d0 = root / "alternate-d0.json"
            with mock.patch.multiple(
                self.reducer,
                DEFAULT_D1=fixed_d1,
                DEFAULT_D0=fixed_d0,
                DEFAULT_OUT=fixed_out,
            ), mock.patch.object(
                self.reducer, "_profile", return_value={}
            ), mock.patch.object(
                self.reducer, "_baseline_design_identity", return_value={}
            ), mock.patch.object(
                self.reducer, "_current_candidate_identity", return_value={}
            ), mock.patch.object(
                self.reducer, "_json", side_effect=[({}, {}), ({}, {})]
            ), mock.patch.object(
                self.reducer, "_validate_d1", return_value={}
            ), mock.patch.object(
                self.reducer, "publish_exclusive"
            ) as publish:
                self.assertEqual(
                    self.reducer.main(
                        [
                            "--d1", str(fixed_d1),
                            "--d0", str(alternate_d0),
                            "--out", str(fixed_out),
                        ]
                    ),
                    2,
                )
                publish.assert_not_called()

    def test_d1_v2_namespace_extra_hardlink_and_symlink_reject(self):
        for mutation in ("extra", "hardlink", "symlink"):
            helper, inputs, value = self.d1_fixture()
            try:
                start = helper.module.RUN_DIR / "start.json"
                if mutation == "extra":
                    extra = helper.module.RUN_DIR / "extra"
                    extra.write_bytes(b"x")
                elif mutation == "hardlink":
                    os.link(start, helper.module.RUN_DIR / "start-link")
                else:
                    start.unlink()
                    start.symlink_to(helper.module.RUN_ARM)
                with self.assertRaises(self.reducer.FreshBaselineError):
                    self.validate_fixture(helper, inputs, value)
            finally:
                helper.doCleanups()

    def test_v2_preserves_reviewed_raw_first_and_typed_stop_core(self):
        for name in ("_execute", "_raw_adb_inventory", "validate_stop", "_publish_stop", "run_live"):
            self.assertEqual(
                inspect.getsource(getattr(self.d0, name)),
                inspect.getsource(getattr(self.v1_d0, name)),
                name,
            )

    def test_v2_has_no_stale_producer_or_journal_schema_literals(self):
        text = (D0.read_text(encoding="utf-8") + REDUCER.read_text(encoding="utf-8"))
        forbidden = (
            "d1_fresh_baseline_binding_v1",
            "d1_fresh_baseline_execution_binding_v1",
            "device-action-d1-p319-v1",
            "d1_fresh_baseline_arm_v1",
            "d1_fresh_baseline_start_v1",
            "d0_fresh_baseline_execution_binding_v1",
            "d0_fresh_baseline_binding_v1",
            "d0_fresh_baseline_arm_v1",
            "device-action-d0-p319-v1",
        )
        for token in forbidden:
            self.assertNotIn(token, text)
        for inherited in (
            "candidate_intent_v1",
            "candidate_qualification_v1",
            "device_action_raw_capture_v1",
            "d0_raw_adb_inventory_v1",
        ):
            self.assertIn(inherited, text)

    def test_integration_consumes_only_v2_and_stays_fresh_missing(self):
        module = load(INTEGRATION, "p319_integration_v2_repin_test")
        self.assertEqual(module.FRESH_BASELINE_CAPABILITY, REDUCER)
        self.assertEqual(module.FRESH_BASELINE, self.reducer.DEFAULT_OUT)
        result = module.build_result()
        codes = {item["code"] for item in result["blockers"]}
        self.assertIn("FRESH_BASELINE_MISSING", codes)
        self.assertFalse(result["ready"])
        self.assertFalse(result["live_authorized"])
        report = REPORT.read_text(encoding="utf-8")
        self.assertIn("P319_D0_FRESH_BASELINE_V2_REPIN_IMPLEMENTED_REVIEW_PENDING", report)
        self.assertIn("b0cc446f5cb9861d1f91a03b375e8eb917da3cd2fbf1c9d8800d1852abe9dfed", report)
        ledger = LEDGER.read_text(encoding="utf-8")
        rows = [
            line
            for line in ledger.splitlines()
            if " | h0-d0-fresh-baseline-v2-repin-43 | " in line
        ]
        self.assertEqual(len(rows), 1)
        self.assertIn("_IMPLEMENTED_REVIEW_PENDING", rows[0])
        self.assertNotIn("PASS_GO", rows[0])
        repair_rows = [
            line
            for line in ledger.splitlines()
            if " | h0-d0-fresh-baseline-v2-repin-repair-43 | " in line
        ]
        self.assertEqual(len(repair_rows), 1)
        repair_action = repair_rows[0].split(" | ")[4]
        self.assertIn("REPAIR_UNDER_EXISTING_REVIEW_OBLIGATION", repair_action)
        self.assertNotIn("PASS_GO", repair_action)
        cross_rows = [
            line
            for line in ledger.splitlines()
            if " | h0-d0-fresh-baseline-v2-repin-cross-binding-repair-43 | "
            in line
        ]
        self.assertEqual(len(cross_rows), 1)
        cross_action = cross_rows[0].split(" | ")[4]
        self.assertIn(
            "CROSS_BINDING_REPAIR_UNDER_EXISTING_REVIEW_OBLIGATION",
            cross_action,
        )
        self.assertNotIn("PASS_GO", cross_action)
        path_rows = [
            line
            for line in ledger.splitlines()
            if " | h0-d0-fresh-baseline-v2-repin-fixed-result-path-repair-43 | "
            in line
        ]
        self.assertEqual(len(path_rows), 1)
        path_action = path_rows[0].split(" | ")[4]
        self.assertIn(
            "FIXED_RESULT_PATH_REPAIR_UNDER_EXISTING_REVIEW_OBLIGATION",
            path_action,
        )
        self.assertNotIn("PASS_GO", path_action)
        goal = GOAL.read_text(encoding="utf-8")
        self.assertEqual(len(goal.splitlines()), 900)
        self.assertIn("Topic 43 adds a review-pending V2 D0 producer/reducer", goal)


if __name__ == "__main__":
    unittest.main()
