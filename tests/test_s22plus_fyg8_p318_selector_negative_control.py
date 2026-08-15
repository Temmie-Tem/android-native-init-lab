from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_selector_negative_control.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "p318_selector_negative_control", SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load P3.18 selector negative control")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P318 = load_module()


class P318SelectorNegativeControlTest(unittest.TestCase):
    def inputs(self):
        return {
            "observer_data": (ROOT / P318.DEFAULT_OBSERVER).read_bytes(),
            "latch_data": (ROOT / P318.DEFAULT_LATCH).read_bytes(),
            "extractor_data": SCRIPT.read_bytes(),
        }

    def mutated_observer(self, data: bytes, old: bytes, new: bytes) -> bytes:
        self.assertEqual(data.count(old), 1)
        return data.replace(old, new, 1)

    def test_real_selectors_reject_all_negative_controls_before_open(self):
        result = P318.build_contract(**self.inputs())
        self.assertEqual(result["verdict"], P318.VERDICT)
        selector = result["real_cdc_acm_selector"]
        self.assertEqual(selector["case_count"], 3)
        self.assertEqual(selector["tty_open_attempts_total"], 0)
        self.assertEqual(
            [row["classification"] for row in selector["cases"]],
            ["endpoint-timeout", "identity-mismatch", "endpoint-ambiguous"],
        )
        for row in selector["cases"]:
            self.assertFalse(row["accepted"])
            self.assertEqual(row["tty_open_attempts"], 0)
            self.assertEqual(row["raw_size"], 0)
            self.assertTrue(row["receipt_reopened"])
        udc = result["actual_latch_udc_filter"]
        self.assertTrue(udc["actual_materialized_helper_executed"])
        self.assertEqual(udc["target_name"], "a600000.dwc3")
        self.assertEqual((udc["positive_count"], udc["negative_count"]), (1, 6))

    def test_topology_suffix_matching_mutation_attempts_tty_open(self):
        values = self.inputs()
        old = b"        endpoint.topology == topology\n        and identity"
        self.assertEqual(values["observer_data"].count(old), 2)
        values["observer_data"] = values["observer_data"].replace(
            old,
            b"        True\n        and identity",
            1,
        )
        with self.assertRaisesRegex(P318.NegativeControlError, "same_suffix"):
            P318.build_contract(**values)

    def test_foreign_serial_acceptance_mutation_attempts_tty_open(self):
        values = self.inputs()
        values["observer_data"] = self.mutated_observer(
            values["observer_data"],
            b'        and identity["serial"] == spec["usb_serial"]\n',
            b"        and True\n",
        )
        with self.assertRaisesRegex(P318.NegativeControlError, "different_samsung"):
            P318.build_contract(**values)

    def test_multiple_exact_ambiguity_mutation_fails(self):
        values = self.inputs()
        values["observer_data"] = self.mutated_observer(
            values["observer_data"],
            b"        if len(exact) > 1:\n",
            b"        if len(exact) > 2:\n",
        )
        with self.assertRaisesRegex(P318.NegativeControlError, "multiple_exact"):
            P318.build_contract(**values)

    def test_udc_prefix_match_mutation_fails(self):
        values = self.inputs()
        old = (
            b"strcmp(dev_name(dwc->dev), S22PLUS_DWC3_TARGET_NAME) == 0;"
        )
        new = (
            b"strncmp(dev_name(dwc->dev), S22PLUS_DWC3_TARGET_NAME, "
            b"strlen(S22PLUS_DWC3_TARGET_NAME)) == 0;"
        )
        self.assertEqual(values["latch_data"].count(old), 1)
        values["latch_data"] = values["latch_data"].replace(old, new, 1)
        with self.assertRaisesRegex(P318.NegativeControlError, "UDC filter"):
            P318.build_contract(**values)

    def test_receipt_encoding_is_deterministic(self):
        first = P318.encode_contract(P318.build_contract(**self.inputs()))
        second = P318.encode_contract(P318.build_contract(**self.inputs()))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
