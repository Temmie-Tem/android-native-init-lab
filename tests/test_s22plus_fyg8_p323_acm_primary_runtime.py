from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p323_acm_primary_runtime.py"
)
P322_RUNTIME = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p322/"
    "stock-candidate-build-v1-20260831-02/stock-sources/"
    "s22plus_fyg8_p290_e3_runtime.inc.c"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p323_acm_primary", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("P323 ACM-primary transform cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P323AcmPrimaryRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.before = P322_RUNTIME.read_bytes()
        cls.after = cls.module.transform_runtime_include(cls.before)

    def test_real_p322_runtime_changes_only_publisher_entry(self) -> None:
        receipt = self.module.validate_transform(self.before, self.after)
        self.assertTrue(receipt["changed_only_in_anchor"])
        self.assertTrue(receipt["acm_primary"])
        self.assertEqual(receipt["banner_attempts"], 1)
        self.assertTrue(receipt["retained_path_always_continues"])
        self.assertFalse(receipt["scientific_result_claimed_by_banner"])
        self.assertEqual(
            self.after,
            self.before.replace(
                self.module.P322_ENTRY_PREIMAGE,
                self.module.P323_ENTRY_POSTIMAGE,
                1,
            ),
        )

    def test_duplicate_or_already_transformed_input_is_rejected(self) -> None:
        with self.assertRaises(self.module.AcmPrimaryError):
            self.module.transform_runtime_include(
                self.before + self.module.P322_ENTRY_PREIMAGE
            )
        with self.assertRaises(self.module.AcmPrimaryError):
            self.module.validate_p322_runtime(self.after)

    def test_banner_precedes_every_fallible_stock_publication_step(self) -> None:
        publisher = self.after.index(self.module.PUBLISHER)
        banner = self.after.index(b"s22plus_p318_banner_attempt(tty_fd)", publisher)
        copy = self.after.index(b"p319_witness_summary_state_v2_copy", banner)
        encode = self.after.index(b"s22plus_max77705_p319_stock_encode", copy)
        bridge = self.after.index(b"p319_stock_bypass_to_pair();", encode)
        self.assertLess(publisher, banner)
        self.assertLess(banner, copy)
        self.assertLess(copy, encode)
        self.assertLess(encode, bridge)

    def test_banner_result_does_not_gate_the_retained_path(self) -> None:
        publisher = self.after.index(self.module.PUBLISHER)
        end = self.after.index(b"\n}\n", publisher)
        body = self.after[publisher:end]
        self.assertIn(b"(void)s22plus_p318_banner_attempt(tty_fd);", body)
        self.assertEqual(body.count(b"s22plus_p318_banner_attempt(tty_fd)"), 1)
        self.assertNotIn(b"acm.outcome", body)
        self.assertIn(b"p319_stock_bypass_to_pair();", body)

    def test_only_named_runtime_member_changes(self) -> None:
        source = {"other": b"stable", self.module.RUNTIME_KEY: self.before}
        result = self.module.transform_artifacts(source)
        self.assertEqual(result["other"], b"stable")
        self.assertNotEqual(result[self.module.RUNTIME_KEY], self.before)


if __name__ == "__main__":
    unittest.main()
