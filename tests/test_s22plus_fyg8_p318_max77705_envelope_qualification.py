import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s22plus_fyg8_p318_max77705_envelope_qualification.py"


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_p318_max77705_envelope_qualification_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


class S22PlusFyg8P318Max77705EnvelopeQualificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.value = cls.module.audit(ROOT)

    def test_actual_c_matches_python_at_47_and_48(self):
        self.assertEqual(self.value["actual_c_python_case_count"], 5)
        self.assertEqual(self.value["lossless_boundary_encoded_bytes"], 47)
        self.assertEqual(self.value["overflow_boundary_encoded_bytes"], 48)
        self.assertEqual(self.value["overflow_summary_bytes"], 44)
        self.assertEqual(self.value["overflow_spare_bytes"], 3)
        self.assertTrue(self.value["nonzero_overflow_spare_rejected_after_valid_crc"])
        self.assertTrue(self.value["actual_c_bytes_pass_real_carrier_and_host_decoder"])
        self.assertTrue(self.value["carrier_integration"])

    def test_actual_c_observer_sites_survive_carrier_with_exact_authority(self):
        self.assertEqual(self.value["actual_c_python_observer_case_count"], 2)
        self.assertEqual(
            self.value["observer_sites_qualified"],
            ["exposure-gate", "timing-latch"],
        )
        gate, latch = self.value["actual_c_python_observer_cases"]
        self.assertFalse(any(gate["executability_authority"].values()))
        self.assertTrue(gate["binding_authority"]["loader_state"])
        self.assertFalse(
            any(
                value
                for key, value in gate["binding_authority"].items()
                if key != "loader_state"
            )
        )
        self.assertTrue(all(latch["executability_authority"].values()))
        self.assertTrue(all(latch["binding_authority"].values()))

    def test_host_receipt_cross_product_is_fail_closed(self):
        self.assertEqual(
            self.value["host_receipt_cross_product"]["no_event_endpoint_absent"],
            "DEVICE_RESULT_HOST_SILENT",
        )
        self.assertEqual(
            self.value["host_receipt_cross_product"]["no_event_endpoint_present"],
            "NO_PROOF_OBSERVER_LATCHED_EVENT_MISSING",
        )
        self.assertEqual(
            self.value["host_receipt_cross_product"]["event_endpoint_absent"],
            "DEVICE_RESULT_DWC3_HOST_EVENT_NO_ENDPOINT",
        )

    def test_missing_exposure_and_invalid_banner_do_not_gain_authority(self):
        self.assertEqual(self.value["missing_exposure_mask"], 0x2F)
        self.assertFalse(self.value["missing_exposure_causal_authority"])
        self.assertEqual(self.value["invalid_banner_tuple_count"], 5)
        self.assertFalse(self.value["candidate_ready"])
        self.assertTrue(self.value["verified"])


if __name__ == "__main__":
    unittest.main()
