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
import s22plus_fyg8_p339_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p339_open_read_branch_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p339_open_read_branch_runtime as runtime  # noqa: E402
import s22plus_fyg8_p339_stock_candidate_build as builder  # noqa: E402
import s22plus_fyg8_p339_stock_process_v2_adapter as adapter  # noqa: E402
import s22plus_fyg8_p339_process_v2_candidate_static as static  # noqa: E402


TEST_KEY = builder.artifact.DEFAULT_AUTH_KEY_PATH.read_bytes()


class P339OpenReadBranchTests(unittest.TestCase):
    @staticmethod
    def _diagnostic(stage: int, code: int) -> bytes:
        return p336_observer.encode_frame(
            runtime.DIAGNOSTIC_FRAME_TYPE,
            0,
            observer.DIAGNOSTIC.pack(stage, code),
        )

    @classmethod
    def _captured(cls, branch: int, header: bytes, words: int = 4) -> bytes:
        frames = [
            cls._diagnostic(runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT, branch)
        ]
        for stage, offset in zip(runtime.OPEN_HEADER_WORD_STAGES, range(0, 16, 4)):
            if len(frames) > words:
                break
            frames.append(
                cls._diagnostic(
                    stage,
                    int.from_bytes(header[offset : offset + 4], "little", signed=True),
                )
            )
        return runtime.DEVICE_BANNER + b"".join(frames)

    def test_runtime_binding_is_fresh_and_five_way(self) -> None:
        value = runtime.audit_binding()
        self.assertEqual(value["run_id_hex"], runtime.P339_RUN_ID_HEX)
        self.assertEqual(value["predecessor_run_id"], runtime.P338_PREDECESSOR_RUN_ID_HEX)
        self.assertEqual(value["open_read_branch_count"], 5)
        self.assertEqual(
            value["open_read_branch_ordinals"],
            {
                0: "header-read-errno",
                1: "header-grammar",
                2: "body-read-errno",
                3: "crc",
                4: "open-semantic",
            },
        )
        self.assertTrue(value["successful_wire_exchange_unchanged"])
        self.assertTrue(value["original_errno_returned_unchanged"])
        self.assertFalse(value["retry_added"])
        self.assertFalse(value["timeout_changed"])
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])

    def test_transform_reopens_only_the_p338_runtime_include(self) -> None:
        predecessor = builder._predecessor()[0]  # noqa: SLF001
        source = builder._stable(  # noqa: SLF001
            builder.P338_OUTPUT / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c",
            "P3.37 runtime",
            2 << 20,
            predecessor["source_closure"]["s22plus_fyg8_p290_e3_runtime.inc.c"],
            mode=0o400,
        )
        transformed, receipt = builder._runtime_transform(source, TEST_KEY)  # noqa: SLF001
        self.assertNotEqual(source, transformed)
        self.assertEqual(receipt["input_lineage"], "p338-runtime-include")
        self.assertEqual(receipt["run_id_hex"], runtime.P339_RUN_ID_HEX)
        self.assertEqual(receipt["open_read_branch_count"], 5)
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

    def test_observer_recovers_complete_grammar_and_semantic_headers(self) -> None:
        grammar = observer.HEADER.pack(b"BAD!", 1, runtime.FRAME_OPEN, 16, 0, 0)
        grammar_value = observer.parse_retained_open_read_branch(
            self._captured(runtime.OPEN_READ_BRANCH_HEADER_VALIDATION, grammar)
        )
        self.assertTrue(grammar_value["header_snapshot_complete"])
        self.assertEqual(grammar_value["header_snapshot_hex"], grammar.hex())
        self.assertEqual(grammar_value["mismatch"], "magic")

        semantic = observer.HEADER.pack(
            runtime.FRAME_MAGIC,
            runtime.FRAME_VERSION,
            runtime.FRAME_OPEN + 1,
            len(runtime.P339_RUN_ID),
            0,
            0xF1234567,
        )
        semantic_value = observer.parse_retained_open_read_branch(
            self._captured(runtime.OPEN_READ_BRANCH_OPEN_SEMANTIC, semantic)
        )
        self.assertTrue(semantic_value["header_snapshot_complete"])
        self.assertEqual(semantic_value["header_snapshot_hex"], semantic.hex())
        self.assertEqual(semantic_value["mismatch"], "type")

    def test_header_capture_is_bounded_ordered_and_partial(self) -> None:
        header = observer.HEADER.pack(b"BAD!", 1, runtime.FRAME_OPEN, 16, 0, 0)
        value = observer.parse_retained_open_read_branch(
            self._captured(runtime.OPEN_READ_BRANCH_HEADER_VALIDATION, header, words=2)
        )
        self.assertFalse(value["header_snapshot_complete"])
        self.assertEqual(value["header_word_count"], 2)
        self.assertEqual(value["header_snapshot_hex"], header[:8].hex())
        self.assertIsNone(value["mismatch"])

        reason = self._diagnostic(
            runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
            runtime.OPEN_READ_BRANCH_HEADER_VALIDATION,
        )
        bad_order = runtime.DEVICE_BANNER + reason + self._diagnostic(
            runtime.OPEN_HEADER_WORD_STAGES[1], 0
        )
        with self.assertRaises(observer.P339ObserverBindingError):
            observer.parse_retained_open_read_branch(bad_order)

    def test_adapter_and_artifact_bind_only_fresh_identity(self) -> None:
        value = adapter.audit()
        self.assertEqual(value["run_id"], runtime.P339_RUN_ID_HEX)
        self.assertEqual(value["predecessor_run_id"], runtime.P338_PREDECESSOR_RUN_ID_HEX)
        self.assertEqual(value["open_read_branch_count"], 5)
        self.assertEqual(
            value["open_read_branch_ordinals"],
            {
                "0": "header-read-errno",
                "1": "header-grammar",
                "2": "body-read-errno",
                "3": "crc",
                "4": "open-semantic",
            },
        )
        acceptance = adapter.acceptance_fixture()
        self.assertEqual(acceptance["open_read_branch_ordinals"], value["open_read_branch_ordinals"])
        round_tripped = json.loads(json.dumps(acceptance))
        self.assertIs(adapter.validate_acceptance_item(round_tripped), round_tripped)
        self.assertFalse(value["candidate_success"])
        self.assertEqual(observer.audit_binding()["run_id_hex"], runtime.P339_RUN_ID_HEX)
        self.assertEqual(artifact.validate_p339_identity()["run_id_hex"], runtime.P339_RUN_ID_HEX)

    def test_builder_is_ab_equal_boot_only_and_rejects_p338(self) -> None:
        value = builder.audit_existing()
        candidate = value["phase2"]["candidate"]
        self.assertEqual(value["run_id_hex"], runtime.P339_RUN_ID_HEX)
        self.assertEqual(candidate["a"], candidate["b"])
        self.assertEqual(candidate["a"]["package"]["members"], ["boot.img.lz4"])
        self.assertNotEqual(candidate["a"]["ap_tar_md5"], artifact.P338_AP_IDENTITY)
        self.assertTrue(value["scope"]["host_only"])
        self.assertFalse(value["scope"]["device_contact"])

    def test_builder_normalizer_rejects_stale_p338_candidate(self) -> None:
        stale = copy.deepcopy(builder._predecessor()[0])  # noqa: SLF001
        with self.assertRaises(builder.AuditError):
            builder._normalize_result(stale)  # noqa: SLF001

    def test_static_projection_regenerates_without_action_or_authority(self) -> None:
        value = static.build_result()
        self.assertEqual(value["run_id"], runtime.P339_RUN_ID_HEX)
        self.assertEqual(value["candidate"]["a"], value["candidate"]["b"])
        self.assertIsNone(value["action_runner"])
        self.assertFalse(value["later_action_authorized"])
        self.assertFalse(value["safety"]["device_contact"])
        self.assertFalse(value["safety"]["f1_authorized"])
        self.assertIn("p339_open_read_branch_runtime", value["source_closure"])
        self.assertIn("p339_open_read_branch_acm_observer", value["source_closure"])


if __name__ == "__main__":
    unittest.main()
