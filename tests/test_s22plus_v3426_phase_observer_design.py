import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3426_phase_observer_design.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "s22plus_v3426_phase_observer_design", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusV3426PhaseObserverDesignTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.design = cls.module.build_design(cls.module.repo_root())

    def setUp(self):
        self.expectation = self.module.make_expectation(
            "0123456789abcdef0123456789abcdef",
            "1" * 64,
            "2" * 64,
        )
        self.precheck = self.module.encode_marker(
            self.expectation, self.module.PHASE_PRECHECK
        )
        self.final = self.module.encode_marker(
            self.expectation, self.module.PHASE_FINAL
        )

    def classify(self, stage, blob):
        return self.module.classify_marker_snapshot(stage, blob, self.expectation)

    def test_static_design_inputs_pass(self):
        design = self.design
        self.assertEqual(design["verdict"], "HOST_DESIGN_PASS_NO_LIVE")
        self.assertEqual(
            design["static_evidence"]["source_proofs"]
            ["devkmsg_write_hook_return_is_synchronous"],
            "VERIFIED",
        )
        self.assertFalse(design["safety"]["live_authorized"])

    def test_contract_pin_and_committed_json_are_current(self):
        self.assertEqual(
            self.module.CONTRACT_SHA256,
            self.module.PINNED_CONTRACT_SHA256,
        )
        committed = Path(
            "docs/plans/s22plus-v3426-phase-observer-contract.json"
        ).read_text(encoding="utf-8")
        expected = json.dumps(self.design, indent=2, sort_keys=True) + "\n"
        self.assertEqual(committed, expected)

    def test_marker_roundtrip(self):
        scan = self.module.scan_markers(b"prefix" + self.precheck + b"suffix")
        self.assertEqual(len(scan.markers), 1)
        self.assertEqual(scan.markers[0].run_id, self.expectation.run_id)
        self.assertEqual(scan.markers[0].phase, self.module.PHASE_PRECHECK)
        self.assertFalse(scan.issues)

    def test_baseline_is_negative_control(self):
        result = self.classify("baseline", b"historical kernel text")
        self.assertTrue(result["pass"])
        result = self.classify("baseline", self.precheck)
        self.assertFalse(result["pass"])
        self.assertIn("current-run-marker-present-before-stimulus", result["errors"])

    def test_historical_foreign_marker_is_permitted(self):
        foreign = self.module.make_expectation("f" * 32, "3" * 64, "4" * 64)
        foreign_frame = self.module.encode_marker(foreign, self.module.PHASE_PRECHECK)
        baseline = self.classify("baseline", foreign_frame)
        self.assertTrue(baseline["pass"])
        current = self.classify("precheck", foreign_frame + self.precheck)
        self.assertTrue(current["pass"])
        self.assertEqual(current["foreign_run_marker_count"], 1)

    def test_precheck_requires_exactly_one_current_marker(self):
        self.assertTrue(self.classify("precheck", self.precheck)["pass"])
        self.assertFalse(self.classify("precheck", b"")["pass"])
        duplicate = self.classify("precheck", self.precheck + self.precheck)
        self.assertFalse(duplicate["pass"])
        self.assertIn("precheck-count:2", duplicate["errors"])

    def test_final_requires_precheck_and_final(self):
        self.assertTrue(self.classify("final", self.precheck + self.final)["pass"])
        evicted = self.classify("final", self.final)
        self.assertFalse(evicted["pass"])
        self.assertIn("precheck-count:0", evicted["errors"])

    def test_physical_wrap_order_does_not_override_embedded_sequence(self):
        result = self.classify("final", self.final + b"wrapped" + self.precheck)
        self.assertTrue(result["pass"])

    def test_final_before_precheck_sequence_is_rejected(self):
        bad_precheck = self.module.encode_marker(
            self.expectation, self.module.PHASE_PRECHECK, sequence=3
        )
        result = self.classify("final", bad_precheck + self.final)
        self.assertFalse(result["pass"])
        self.assertIn("precheck-sequence-mismatch", result["errors"])
        self.assertIn("embedded-sequence-order-invalid", result["errors"])

    def test_final_cannot_appear_at_precheck_gate(self):
        result = self.classify("precheck", self.precheck + self.final)
        self.assertFalse(result["pass"])
        self.assertIn("final-present-before-final-stimulus", result["errors"])

    def test_current_run_crc_corruption_is_fatal(self):
        corrupt = bytearray(self.precheck)
        payload_offset = corrupt.find(b"phase=PRECHECK")
        corrupt[payload_offset] = ord("x")
        result = self.classify("precheck", bytes(corrupt))
        self.assertFalse(result["pass"])
        self.assertTrue(
            any(error.startswith("current-run-malformed:") for error in result["errors"])
        )

    def test_missing_length_separator_uses_raw_token_backstop(self):
        malformed = bytearray(self.precheck)
        separator = len(self.module.FRAME_START) + 4
        malformed[separator] = ord("!")
        result = self.classify("precheck", bytes(malformed))
        self.assertFalse(result["pass"])
        self.assertIn("current-run-unframed-or-malformed", result["errors"])

    def test_oversize_length_uses_raw_token_backstop(self):
        malformed = bytearray(self.precheck)
        start = len(self.module.FRAME_START)
        malformed[start : start + 4] = b"ffff"
        result = self.classify("precheck", bytes(malformed))
        self.assertFalse(result["pass"])
        self.assertIn("current-run-unframed-or-malformed", result["errors"])

    def test_truncated_current_frame_is_fatal(self):
        result = self.classify("precheck", self.precheck[:-7])
        self.assertFalse(result["pass"])
        self.assertIn("current-run-malformed:truncated-frame", result["errors"])

    def test_wrap_truncated_current_frame_without_start_is_fatal(self):
        truncated = self.precheck[len(self.module.FRAME_START) + 5 :]
        result = self.classify("precheck", truncated)
        self.assertFalse(result["pass"])
        self.assertIn("current-run-unframed-or-malformed", result["errors"])

    def test_wrong_module_identity_is_rejected(self):
        other = self.module.make_expectation(
            self.expectation.run_id,
            self.expectation.precheck_context_sha256,
            self.expectation.final_context_sha256,
            module_sha256="a" * 64,
        )
        result = self.classify(
            "precheck", self.module.encode_marker(other, self.module.PHASE_PRECHECK)
        )
        self.assertFalse(result["pass"])
        self.assertIn("module-identity-mismatch", result["errors"])

    def test_wrong_contract_identity_is_rejected(self):
        other = self.module.make_expectation(
            self.expectation.run_id,
            self.expectation.precheck_context_sha256,
            self.expectation.final_context_sha256,
            contract_sha256="b" * 64,
        )
        result = self.classify(
            "precheck", self.module.encode_marker(other, self.module.PHASE_PRECHECK)
        )
        self.assertFalse(result["pass"])
        self.assertIn("contract-identity-mismatch", result["errors"])

    def test_wrong_context_is_rejected(self):
        other = self.module.make_expectation(
            self.expectation.run_id,
            "c" * 64,
            self.expectation.final_context_sha256,
        )
        result = self.classify(
            "precheck", self.module.encode_marker(other, self.module.PHASE_PRECHECK)
        )
        self.assertFalse(result["pass"])
        self.assertIn("precheck-context-mismatch", result["errors"])

    def test_foreign_to_current_alias_with_bad_crc_is_fatal(self):
        foreign = self.module.make_expectation("f" * 32, "3" * 64, "4" * 64)
        frame = bytearray(
            self.module.encode_marker(foreign, self.module.PHASE_PRECHECK)
        )
        old = foreign.run_id.encode("ascii")
        offset = frame.find(old)
        frame[offset : offset + len(old)] = self.expectation.run_id.encode("ascii")
        result = self.classify("precheck", bytes(frame))
        self.assertFalse(result["pass"])
        self.assertIn("current-run-malformed:crc-mismatch", result["errors"])

    def test_retention_requires_exact_final(self):
        self.assertTrue(
            self.classify("retention", self.precheck + self.final)["pass"]
        )
        final_only = self.classify("retention", self.final)
        self.assertFalse(final_only["pass"])
        self.assertIn("retained-precheck-count:0", final_only["errors"])
        self.assertFalse(self.classify("retention", self.precheck)["pass"])
        duplicate = self.classify("retention", self.final + self.final)
        self.assertFalse(duplicate["pass"])
        self.assertIn("retained-final-count:2", duplicate["errors"])

    def test_gate_trace_requires_exact_order_and_pass(self):
        events = [
            {"name": name, "status": "PASS"}
            for name, _ in self.module.GATE_ORDER
        ]
        self.assertTrue(self.module.classify_gate_trace(events)["pass"])
        swapped = events.copy()
        swapped[3], swapped[4] = swapped[4], swapped[3]
        self.assertFalse(self.module.classify_gate_trace(swapped)["pass"])
        failed = [dict(event) for event in events]
        failed[5]["status"] = "FAIL"
        self.assertFalse(self.module.classify_gate_trace(failed)["pass"])

    def test_contract_keeps_transition_and_live_disabled(self):
        contract = self.module.CONTRACT_CORE
        self.assertFalse(contract["transition_selected"])
        self.assertFalse(contract["live_authorized"])
        self.assertFalse(contract["candidate_source_authorized"])
        self.assertIn("sec_debug.ko", contract["forbidden_components"])

    def test_run_id_source_is_128_bit_hex(self):
        first = self.module.generate_run_id()
        second = self.module.generate_run_id()
        self.assertRegex(first, r"^[0-9a-f]{32}$")
        self.assertNotEqual(first, second)

    def test_consumed_o3_marker_families_are_denied(self):
        denied = self.module.CONTRACT_CORE["consumed_marker_families"]
        self.assertIn("S22O3ACM01", denied)
        self.assertIn("S22O3FACM01", denied)
        self.assertIn("S22_NATIVE_INIT_RETAINED_O3R1", denied)


if __name__ == "__main__":
    unittest.main()
