from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p324_stock_process_v2_adapter.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p324_stock_adapter", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("P324 adapter cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P324StockProcessAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = load_module()

    def test_fresh_aliases_and_host_only_audit(self) -> None:
        adapter = self.adapter
        for name in (
            "model",
            "spec",
            "SOURCE_KEYS",
            "P320_OBSERVER_SOURCE",
            "TERMINAL_STAGE",
            "LONG_FAMILY",
            "UNSAT_FAMILY",
        ):
            self.assertTrue(hasattr(adapter, name), name)
        self.assertEqual(adapter.RUN_ID, adapter.P324_RUN_ID)
        self.assertEqual(adapter.STOCK_RUN_ID, adapter.P324_RUN_ID)
        self.assertEqual(adapter.P323_PREDECESSOR_RUN_ID, adapter.P323_RUN_ID)
        self.assertEqual(
            adapter.classify_observation.__kwdefaults__["expected_run_id"],
            adapter.P324_RUN_ID,
        )
        receipt = adapter.audit()
        self.assertTrue(receipt["verified"])
        self.assertEqual(receipt["schema"], "s22plus_fyg8_p324_stock_process_v2_adapter_v1")
        self.assertEqual(receipt["run_id"], adapter.P324_RUN_ID_HEX)
        self.assertEqual(receipt["predecessor_run_id"], adapter.P323_RUN_ID_HEX)
        self.assertFalse(receipt["encoder_failure_is_success"])

    def test_fixture_is_rebound_to_p324_and_acm_primary(self) -> None:
        adapter = self.adapter
        record = adapter.encode_fixture()
        decoded = adapter.decode_record(record)
        self.assertEqual(decoded["carrier"]["run_id"], adapter.P324_RUN_ID_HEX)
        self.assertEqual(decoded["schema"], adapter.SCHEMA)
        raw = bytes(adapter.RAW_SIZE - len(record)) + record
        value = adapter.classify_observation(raw)
        self.assertEqual(value["run_id"], adapter.P324_RUN_ID_HEX)
        self.assertEqual(value["classification"], "P320_STOCK_WITNESS_COMPLETE")
        self.assertTrue(value["acm_primary"])
        self.assertTrue(value["carrier_supplemental"])

    def test_exact_encoder_failure_has_distinct_non_success_class(self) -> None:
        adapter = self.adapter
        header = adapter.carrier._header("E2", adapter.P324_RUN_ID)  # noqa: SLF001
        prior = adapter.carrier.Slot(0, 92, 0x8F, 0, 4, 0)
        active = adapter.carrier.Slot(1, 93, 0x90, 2, 0, 0x6726)
        record = (
            header
            + adapter.carrier._encode_slot(header, prior)  # noqa: SLF001
            + adapter.carrier._encode_slot(header, active)  # noqa: SLF001
        )
        raw = bytes(adapter.RAW_SIZE - len(record)) + record
        value = adapter.classify_observation(raw)
        self.assertEqual(value["classification"], "P324_STOCK_ENCODER_FAILURE")
        self.assertEqual(value["proof_class"], "P324_STOCK_ENCODER_FAILURE")
        self.assertTrue(value["producer_failure"])
        self.assertTrue(value["acm_primary"])
        self.assertFalse(value["candidate_success"])
        self.assertFalse(value["causal_result_allowed"])
        self.assertEqual(
            adapter._proof_class_for_value(value),  # noqa: SLF001
            "P324_STOCK_ENCODER_FAILURE",
        )
        self.assertEqual(adapter.proof_class(value), "P324_STOCK_ENCODER_FAILURE")
        with self.assertRaises(adapter.DecodeError):
            adapter.proof_class(value, expected="NONCAUSAL_SUCCESS_PATH")

        changed = copy.deepcopy(value)
        changed["records"][0]["valid_slots"][1]["detail"] = 0x6725
        self.assertNotEqual(
            adapter._proof_class_for_value(changed),  # noqa: SLF001
            "P324_STOCK_ENCODER_FAILURE",
        )

    def test_all_predecessor_ids_fail_closed(self) -> None:
        adapter = self.adapter
        record = adapter.encode_fixture()
        for old_run_id in (
            adapter.P319_RUN_ID,
            adapter.P320_RUN_ID,
            adapter.P321_RUN_ID,
            adapter.P322_RUN_ID,
            adapter.P323_RUN_ID,
        ):
            with self.subTest(old_run_id=old_run_id.hex()):
                with self.assertRaises(adapter.DecodeError):
                    adapter.decode_record(record, expected_run_id=old_run_id)


if __name__ == "__main__":
    unittest.main()
