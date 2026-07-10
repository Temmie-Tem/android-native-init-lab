import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3427_transition_selection.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "s22plus_v3427_transition_selection", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusV3427TransitionSelectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.selection = cls.module.build_selection(cls.module.repo_root())

    def setUp(self):
        self.expectation = self.module.observer.make_expectation(
            "0123456789abcdef0123456789abcdef", "1" * 64, "2" * 64
        )
        self.precheck = self.module.observer.encode_marker(
            self.expectation, self.module.observer.PHASE_PRECHECK
        )
        self.final = self.module.observer.encode_marker(
            self.expectation, self.module.observer.PHASE_FINAL
        )

    def classify(self, payload, *, second=None, first_eof=True, second_eof=True):
        return self.module.classify_first_boot_capture(
            payload,
            payload if second is None else second,
            self.expectation,
            first_eof=first_eof,
            second_eof=second_eof,
        )

    def test_static_selection_passes_without_live_authorization(self):
        self.assertEqual(
            self.selection["verdict"], "HOST_TRANSITION_SELECTION_PASS_NO_LIVE"
        )
        self.assertFalse(self.selection["safety"]["device_contact"])
        self.assertFalse(self.selection["safety"]["live_authorized"])
        self.assertTrue(
            self.selection["transition"]["required_before_candidate"]
            ["same_transition_stock_origin_positive_control"]
        )

    def test_exact_pair_is_positive_conclusive(self):
        payload = b"old log" + self.precheck + b"noise" + self.final
        result = self.classify(payload)
        self.assertEqual(
            result["verdict"], "PASS_STAGE_A_AND_CROSS_SESSION_RETENTION"
        )

    def test_absence_is_no_proof_not_retention_fail(self):
        result = self.classify(b"kernel log without current run")
        self.assertEqual(
            result["verdict"],
            "NO_PROOF_STAGE_A_VS_TRANSITION_UNRESOLVED_STOP",
        )

    def test_final_only_is_fail_stop(self):
        result = self.classify(self.final)
        self.assertEqual(result["verdict"], "FAIL_STOP")

    def test_malformed_current_run_is_fail_stop(self):
        malformed = bytearray(self.precheck)
        malformed[-4] ^= 1
        result = self.classify(bytes(malformed) + self.final)
        self.assertEqual(result["verdict"], "FAIL_STOP")

    def test_non_eof_capture_is_unavailable(self):
        result = self.classify(
            self.precheck + self.final, first_eof=False
        )
        self.assertEqual(result["verdict"], "UNAVAILABLE_STOP")

    def test_double_read_mismatch_is_unavailable(self):
        payload = self.precheck + self.final
        result = self.classify(payload, second=payload + b"changed")
        self.assertEqual(result["verdict"], "UNAVAILABLE_STOP")

    def test_oversize_capture_is_unavailable(self):
        payload = b"x" * (self.module.MAX_LAST_KMSG_BYTES + 1)
        result = self.classify(payload)
        self.assertEqual(result["verdict"], "UNAVAILABLE_STOP")

    def test_rejected_transitions_are_explicit(self):
        rejected = self.selection["transition"]["rejected_transitions"]
        self.assertIn("candidate_reboot_download", rejected)
        self.assertIn("cold_power_cycle", rejected)
        self.assertIn("panic_watchdog_sec_debug", rejected)

    def test_committed_json_is_current(self):
        self.assertEqual(
            self.module.TRANSITION_SHA256,
            self.module.PINNED_TRANSITION_SHA256,
        )
        path = Path("docs/plans/s22plus-v3427-transition-selection.json")
        expected = json.dumps(self.selection, indent=2, sort_keys=True) + "\n"
        self.assertEqual(path.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
