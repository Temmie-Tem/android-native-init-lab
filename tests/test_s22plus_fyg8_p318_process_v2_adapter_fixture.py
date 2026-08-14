import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p318_process_v2_adapter_fixture as fixture


class P318ProcessV2AdapterFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = fixture.audit()

    def test_actual_c_rows_reach_real_process_v2_decoder(self):
        self.assertEqual(self.value["actual_c_base_preimages"], 121)
        self.assertEqual(self.value["actual_c_boundary_preimages"], 5)
        self.assertEqual(self.value["retained_vector_preimages"], 126)
        self.assertEqual(self.value["observer_site_error_rows"], 98)
        self.assertEqual(self.value["mux_rows"], 5)
        self.assertEqual(self.value["pending_mux_rows"], 3)
        self.assertEqual(self.value["observable_eagain_rows"], 6)
        self.assertTrue(self.value["native_envelope_adapter_input_byte_identity"])
        self.assertTrue(self.value["native_envelope_reverse_map_complete"])
        self.assertTrue(self.value["retained_vector_cross_group_unique"])

    def test_host_correlation_and_negative_obligations_are_distinct(self):
        self.assertTrue(self.value["event_present_same_accepted"])
        self.assertTrue(self.value["event_present_absent_distinct"])
        self.assertTrue(self.value["no_event_absent_host_silent_accepted"])
        self.assertTrue(self.value["no_event_present_rejected"])
        self.assertTrue(self.value["drift_never_accepted"])
        self.assertTrue(self.value["claim_busy_decoder_preimage_empty"])
        self.assertTrue(self.value["unknown_overlay_rejected"])
        self.assertTrue(self.value["verified"])


if __name__ == "__main__":
    unittest.main()
