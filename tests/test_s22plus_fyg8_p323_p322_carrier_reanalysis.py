from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
SOURCE = REVALIDATION / "s22plus_fyg8_p323_p322_carrier_reanalysis.py"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p310_carrier_model as carrier  # noqa: E402
import s22plus_fyg8_p313_postlive_carrier_model as p313  # noqa: E402


def load_module():
    spec = importlib.util.spec_from_file_location("p323_p322_reanalysis", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("P322 reanalysis cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P323P322CarrierReanalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        header = carrier._header("E2", cls.module.P322_RUN_ID)  # noqa: SLF001
        prior = carrier.Slot(0, 92, 0x8F, 0, 4, 0)
        active = carrier.Slot(1, 93, 0x90, 2, 0, 0x6726)
        cls.record = (
            header
            + carrier._encode_slot(header, prior)  # noqa: SLF001
            + carrier._encode_slot(header, active)  # noqa: SLF001
        )

    def test_exact_valid_intermediate_failure_is_not_byte_corruption(self) -> None:
        result = self.module.reanalyze(b"prefix" + self.record + b"suffix")
        self.assertEqual(result["classification"], "P322_VALID_INTERMEDIATE_STOCK_ENCODER_FAILURE")
        self.assertTrue(result["carrier_crc_valid"])
        self.assertFalse(result["observer_byte_corruption"])
        self.assertEqual(result["active"]["generation"], 93)
        self.assertEqual(result["active"]["detail"], 0x6726)
        self.assertEqual(result["exact_encoder_predicate"], "UNKNOWN_NOT_RETAINED")
        self.assertFalse(result["candidate_success_promoted"])

    def test_old_p310_semantics_mislabels_the_same_crc_valid_slot(self) -> None:
        old = carrier.decode_record(
            self.record,
            expected_profile="E2",
            expected_run_id=self.module.P322_RUN_ID,
        )
        new = p313.decode_record(
            self.record,
            expected_profile="E2",
            expected_run_id=self.module.P322_RUN_ID,
        )
        self.assertEqual(old["slot_status"], ["valid", "bad-body"])
        self.assertEqual(new["slot_status"], ["valid", "valid"])

    def test_crc_damage_and_wrong_transition_fail_closed(self) -> None:
        damaged = bytearray(self.record)
        damaged[-1] ^= 1
        with self.assertRaises(self.module.ReanalysisError):
            self.module.reanalyze(bytes(damaged))
        header = carrier._header("E2", self.module.P322_RUN_ID)  # noqa: SLF001
        wrong = (
            header
            + carrier._encode_slot(  # noqa: SLF001
                header, carrier.Slot(0, 92, 0x8F, 0, 4, 0)
            )
            + carrier._encode_slot(  # noqa: SLF001
                header, carrier.Slot(1, 93, 0x90, 2, 0, 0x6725)
            )
        )
        with self.assertRaises(self.module.ReanalysisError):
            self.module.reanalyze(wrong)

    def test_wrong_run_id_fails_closed(self) -> None:
        other = bytes.fromhex("c323f1e0a90b5e6d7c8a9b0c1d2e3f4b")
        record = p313.initialize_record("E2", other)
        with self.assertRaises(self.module.ReanalysisError):
            self.module.reanalyze(record)


if __name__ == "__main__":
    unittest.main()
