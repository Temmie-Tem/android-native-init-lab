from __future__ import annotations

import importlib.util
from pathlib import Path
import stat
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p325_stock_process_v2_adapter.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p325_stock_adapter", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("P325 stock adapter cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P325StockAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = load_module()

    def test_fresh_run_overlay_and_immediate_predecessor_are_exact(self) -> None:
        adapter = self.adapter
        self.assertEqual(adapter.RUN_ID, adapter.P325_RUN_ID)
        self.assertEqual(adapter.RUN_ID.hex(), adapter.P325_RUN_ID_HEX)
        self.assertEqual(
            adapter.P324_PREDECESSOR_RUN_ID_HEX,
            "c324f1e0a90b5e6d7c8a9b0c1d2e3f4b",
        )
        self.assertEqual(
            adapter.OVERLAY_CONTRACT_ID,
            "s22plus-fyg8-p325-observer-v4-carrier-v1",
        )
        self.assertEqual(
            adapter.DECODER_ID,
            "s22plus_fyg8_p325_observer_v4_carrier_v1",
        )
        self.assertNotEqual(adapter.OVERLAY_CONTRACT_ID, adapter.P324_OVERLAY_CONTRACT_ID)

    def test_acceptance_fixture_reopens_without_authority(self) -> None:
        adapter = self.adapter
        value = adapter.acceptance_fixture()
        checked = adapter.validate_acceptance_item(value)
        self.assertEqual(checked["run_id"], adapter.P325_RUN_ID_HEX)
        self.assertEqual(checked["overlay_contract_id"], adapter.OVERLAY_CONTRACT_ID)
        self.assertFalse(checked["candidate_success"])
        self.assertFalse(checked["causal_result_allowed"])
        self.assertEqual(
            value["contract"]["candidate_static"]["path"],
            "p325-stock-observer-v4-fixture",
        )

    def test_lineage_pins_this_source_and_rejects_predecessor_bytes(self) -> None:
        adapter = self.adapter
        lineage = adapter.bind_exact_sources()
        source = ROOT / lineage["source_adapter"]["path"]
        self.assertEqual(source, SOURCE)
        self.assertEqual(
            lineage["source_adapter"],
            {
                "path": "workspace/public/src/scripts/revalidation/"
                "s22plus_fyg8_p325_stock_process_v2_adapter.py",
                "size": 16_978,
                "sha256": "6c4ae9a981ac30523275bc261857605d4c263113ceb9a4a3e079508d408919f0",
            },
        )
        self.assertEqual(lineage["predecessor_run_id_rejected"], adapter.P324_RUN_ID_HEX)
        with self.assertRaises(adapter.DecodeError):
            adapter.decode_record(adapter.P324_RUN_ID, expected_run_id=adapter.P324_RUN_ID)

    def test_adapter_source_is_private_regular_single_link(self) -> None:
        metadata = SOURCE.stat()
        self.assertTrue(stat.S_ISREG(metadata.st_mode))
        self.assertEqual(metadata.st_nlink, 1)
        self.assertEqual(stat.S_IMODE(metadata.st_mode), 0o664)


if __name__ == "__main__":
    unittest.main()
