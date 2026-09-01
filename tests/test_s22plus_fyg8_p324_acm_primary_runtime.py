from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p324_acm_primary_runtime.py"
)
P323_RUNTIME = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p323/"
    "stock-candidate-build-v1-20260831-03/stock-sources/"
    "s22plus_fyg8_p290_e3_runtime.inc.c"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p324_acm_primary", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("P324 ACM-primary runtime cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P324AcmPrimaryRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.before = P323_RUNTIME.read_bytes()

    def test_runtime_is_byte_equivalent_and_keeps_acm_order(self) -> None:
        after = self.module.transform_runtime_include(self.before)
        self.assertEqual(after, self.before)
        receipt = self.module.validate_transform(self.before, after)
        self.assertTrue(receipt["acm_primary"])
        self.assertTrue(receipt["runtime_byte_equivalent_to_p323"])
        self.assertFalse(receipt["changed_only_in_anchor"])
        self.assertIsNone(receipt["changed_anchor"])
        self.assertEqual(receipt["banner_attempts"], 1)
        self.assertTrue(receipt["retained_path_always_continues"])
        publisher = after.index(self.module.PUBLISHER)
        banner = after.index(b"s22plus_p318_banner_attempt(tty_fd)", publisher)
        copy = after.index(b"p319_witness_summary_state_v2_copy", banner)
        encode = after.index(b"s22plus_max77705_p319_stock_encode", copy)
        bridge = after.index(b"p319_stock_bypass_to_pair();", encode)
        self.assertLess(publisher, banner)
        self.assertLess(banner, copy)
        self.assertLess(copy, encode)
        self.assertLess(encode, bridge)

    def test_runtime_delta_or_missing_member_fails_closed(self) -> None:
        mutated = self.before[:-1] + bytes([self.before[-1] ^ 1])
        with self.assertRaises(self.module.AcmPrimaryError):
            self.module.transform_runtime_include(mutated)
        with self.assertRaises(self.module.AcmPrimaryError):
            self.module.transform_artifacts({"other": b"stable"})


if __name__ == "__main__":
    unittest.main()
