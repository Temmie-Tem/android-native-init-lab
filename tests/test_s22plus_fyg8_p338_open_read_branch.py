from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import s22plus_fyg8_p336_long_idle_acm_observer as p336_observer  # noqa: E402
import s22plus_fyg8_p338_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p338_open_read_branch_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p338_open_read_branch_runtime as runtime  # noqa: E402
import s22plus_fyg8_p338_stock_candidate_build as builder  # noqa: E402
import s22plus_fyg8_p338_stock_process_v2_adapter as adapter  # noqa: E402
import s22plus_fyg8_p338_process_v2_candidate_static as static  # noqa: E402


TEST_KEY = builder.artifact.DEFAULT_AUTH_KEY_PATH.read_bytes()


class P338OpenReadBranchTests(unittest.TestCase):
    def test_runtime_binding_is_fresh_and_four_way(self) -> None:
        value = runtime.audit_binding()
        self.assertEqual(value["run_id_hex"], runtime.P338_RUN_ID_HEX)
        self.assertEqual(value["predecessor_run_id"], runtime.P337_PREDECESSOR_RUN_ID_HEX)
        self.assertEqual(value["open_read_branch_count"], 4)
        self.assertEqual(
            value["open_read_branch_ordinals"],
            {
                0: "header-read-errno",
                1: "header-validation",
                2: "body-read-errno",
                3: "crc",
            },
        )
        self.assertTrue(value["successful_wire_exchange_unchanged"])
        self.assertTrue(value["original_errno_returned_unchanged"])
        self.assertFalse(value["retry_added"])
        self.assertFalse(value["timeout_changed"])
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])

    def test_transform_reopens_only_the_p337_runtime_include(self) -> None:
        predecessor = builder._predecessor()[0]  # noqa: SLF001
        source = builder._stable(  # noqa: SLF001
            builder.P337_OUTPUT / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c",
            "P3.37 runtime",
            2 << 20,
            predecessor["source_closure"]["s22plus_fyg8_p290_e3_runtime.inc.c"],
            mode=0o400,
        )
        transformed, receipt = builder._runtime_transform(source, TEST_KEY)  # noqa: SLF001
        self.assertNotEqual(source, transformed)
        self.assertEqual(receipt["input_lineage"], "p337-runtime-include")
        self.assertEqual(receipt["run_id_hex"], runtime.P338_RUN_ID_HEX)
        self.assertEqual(receipt["open_read_branch_count"], 4)
        self.assertTrue(receipt["per_boot_identity_required"])
        self.assertFalse(receipt["retry_added"])

    def test_observer_decodes_each_branch_without_causal_proof(self) -> None:
        for code, expected in runtime.OPEN_READ_BRANCHES.items():
            with self.subTest(code=code):
                frame = p336_observer.encode_frame(
                    runtime.DIAGNOSTIC_FRAME_TYPE,
                    0,
                    observer.DIAGNOSTIC.pack(
                        runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT, code
                    ),
                )
                value = observer.parse_retained_open_read_branch(
                    runtime.DEVICE_BANNER + frame
                )
                self.assertEqual(value["classification"], expected)
                self.assertEqual(value["branch_ordinal"], code)
                self.assertFalse(value["causal_result_allowed"])
                self.assertFalse(value["candidate_success"])

    def test_adapter_and_artifact_bind_only_fresh_identity(self) -> None:
        value = adapter.audit()
        self.assertEqual(value["run_id"], runtime.P338_RUN_ID_HEX)
        self.assertEqual(value["predecessor_run_id"], runtime.P337_PREDECESSOR_RUN_ID_HEX)
        self.assertEqual(value["open_read_branch_count"], 4)
        self.assertEqual(
            value["open_read_branch_ordinals"],
            {"0": "header-read-errno", "1": "header-validation", "2": "body-read-errno", "3": "crc"},
        )
        acceptance = adapter.acceptance_fixture()
        self.assertEqual(acceptance["open_read_branch_ordinals"], value["open_read_branch_ordinals"])
        round_tripped = json.loads(json.dumps(acceptance))
        self.assertIs(adapter.validate_acceptance_item(round_tripped), round_tripped)
        self.assertFalse(value["candidate_success"])
        self.assertEqual(observer.audit_binding()["run_id_hex"], runtime.P338_RUN_ID_HEX)
        self.assertEqual(artifact.validate_p338_identity()["run_id_hex"], runtime.P338_RUN_ID_HEX)

    def test_builder_is_ab_equal_boot_only_and_rejects_p337(self) -> None:
        value = builder.audit_existing()
        candidate = value["phase2"]["candidate"]
        self.assertEqual(value["run_id_hex"], runtime.P338_RUN_ID_HEX)
        self.assertEqual(candidate["a"], candidate["b"])
        self.assertEqual(candidate["a"]["package"]["members"], ["boot.img.lz4"])
        self.assertNotEqual(candidate["a"]["ap_tar_md5"], artifact.P337_AP_IDENTITY)
        self.assertTrue(value["scope"]["host_only"])
        self.assertFalse(value["scope"]["device_contact"])

    def test_builder_normalizer_rejects_stale_p337_candidate(self) -> None:
        stale = copy.deepcopy(builder._predecessor()[0])  # noqa: SLF001
        with self.assertRaises(builder.AuditError):
            builder._normalize_result(stale)  # noqa: SLF001

    def test_static_projection_regenerates_without_action_or_authority(self) -> None:
        value = static.build_result()
        self.assertEqual(value["run_id"], runtime.P338_RUN_ID_HEX)
        self.assertEqual(value["candidate"]["a"], value["candidate"]["b"])
        self.assertIsNone(value["action_runner"])
        self.assertFalse(value["later_action_authorized"])
        self.assertFalse(value["safety"]["device_contact"])
        self.assertFalse(value["safety"]["f1_authorized"])
        self.assertIn("p338_open_read_branch_runtime", value["source_closure"])
        self.assertIn("p338_open_read_branch_acm_observer", value["source_closure"])


if __name__ == "__main__":
    unittest.main()
