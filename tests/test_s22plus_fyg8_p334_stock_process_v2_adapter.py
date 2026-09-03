from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p334_first_read_rc_runtime as runtime  # noqa: E402
import s22plus_fyg8_p334_stock_process_v2_adapter as adapter  # noqa: E402


def base_fixture() -> bytes:
    module = next(
        item
        for item in adapter._modules(adapter._P333)
        if hasattr(item, "_full_fixture")
    )
    return module._full_fixture(state="AMBIGUOUS")


def fixture(detail: int) -> bytes:
    raw = base_fixture()
    return adapter._replace_terminal_detail(
        raw, len(raw) - adapter.carrier.LONG_RECORD_SIZE, detail
    )


class P334StockProcessV2AdapterTests(unittest.TestCase):
    def test_exact_return_receipt_normalizes_only_for_stock_decode(self) -> None:
        value = adapter.classify_observation(fixture(0xB047))
        self.assertFalse(value["integrity_issue"])
        self.assertEqual(value["exact_record_count"], 1)
        self.assertEqual(value["foreign_count"], 0)
        self.assertEqual(value["run_id"], runtime.P334_RUN_ID_HEX)
        self.assertEqual(
            value["first_console_return"],
            {
                "valid": True,
                "console_called": True,
                "return_code": -71,
                "encoded_detail": 0xB047,
                "observer_offset": len(fixture(0xB047))
                - adapter.carrier.LONG_RECORD_SIZE,
                "receipt_present": True,
                "attribution_requires_stage0_without_stage1": True,
            },
        )
        self.assertTrue(value["first_console_return_receipt_present"])
        self.assertTrue(value["first_console_return_code_valid"])
        self.assertEqual(value["proof_class"], "NO_PROOF_OBSERVER")

    def test_sentinel_is_present_but_not_interpreted(self) -> None:
        value = adapter.classify_observation(
            fixture(runtime.P334_DETAIL_SENTINEL)
        )
        self.assertTrue(value["first_console_return_receipt_present"])
        self.assertFalse(value["first_console_return_code_valid"])
        self.assertEqual(value["first_console_return"]["console_called"], None)
        self.assertIsNone(value["first_console_return"]["return_code"])

    def test_bad_prefix_crc_duplicate_and_predecessor_binding_fail(self) -> None:
        with self.assertRaises((adapter.AdapterIdentityError, runtime.P334RuntimeError)):
            adapter.classify_observation(fixture(0xA047))
        corrupted = bytearray(fixture(0xB047))
        corrupted[-1] ^= 1
        with self.assertRaises(adapter.AdapterIdentityError):
            adapter.classify_observation(bytes(corrupted))
        one = fixture(0xB047)
        with self.assertRaises(adapter.AdapterIdentityError):
            adapter.classify_observation(one + one[-adapter.carrier.LONG_RECORD_SIZE :])
        with self.assertRaises(adapter.AdapterIdentityError):
            adapter.classify_observation(
                one, expected_run_id=adapter.P333_PREDECESSOR_RUN_ID
            )

    def test_public_binding_names_the_narrow_receipt(self) -> None:
        value = adapter.audit()
        self.assertEqual(value["run_id"], runtime.P334_RUN_ID_HEX)
        self.assertEqual(
            value["verdict"],
            "PASS_P334_STOCK_PROCESS_V2_ADAPTER_H0_FIRST_CONSOLE_RETURN",
        )
        self.assertTrue(value["first_console_return_checkpoint_only"])
        self.assertEqual(
            value["first_console_return_detail_prefix"],
            runtime.P334_DETAIL_PREFIX,
        )
        self.assertTrue(
            value["first_read_attribution_requires_stage0_without_stage1"]
        )


if __name__ == "__main__":
    unittest.main()
