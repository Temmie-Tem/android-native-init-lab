#!/usr/bin/env python3
"""Focused tests for the P2.92 Process-v2 offline-promotion adapter."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import prepare_s22plus_fyg8_p234_process_v2 as base  # noqa: E402
import prepare_s22plus_fyg8_p292_process_v2 as adapter  # noqa: E402
import s22plus_fyg8_p292_candidate_static_checker as checker  # noqa: E402
import s22plus_fyg8_p292_e2_stock_closure as closure_selector  # noqa: E402
import s22plus_fyg8_p292_repair_decoder as repair_decoder  # noqa: E402
import s22plus_fyg8_p292_source_contract as contract  # noqa: E402


class P292ProcessV2PromotionAdapterTest(unittest.TestCase):
    def test_adapter_configures_only_the_versioned_frontier(self) -> None:
        adapter._configure()
        self.assertIs(base.static_checker, checker)
        self.assertEqual(base.SCHEMA, adapter.SCHEMA)
        self.assertEqual(base.VERDICT, adapter.VERDICT)
        self.assertEqual(base.TARGET, checker.TARGET)

    def test_defaults_are_p292_scoped(self) -> None:
        args = adapter.parse_args([])
        self.assertEqual(args.candidate_static, adapter.DEFAULT_STATIC)
        self.assertEqual(args.candidate_ap, adapter.DEFAULT_CANDIDATE_AP)
        self.assertEqual(args.out, adapter.DEFAULT_OUT)
        for value in (args.candidate_static, args.candidate_ap, args.out):
            self.assertIn("s22plus_fyg8_p292", value.as_posix())

    def test_registered_decoder_and_e2_closure_select_p292(self) -> None:
        decoder = evidence._latest_stage_decoder(contract.CONTRACT_ID, "E2")
        adapter._configure()
        self.assertIs(base.e2_closure_selector, closure_selector)
        closure = closure_selector.select(contract.CONTRACT_ID)
        self.assertEqual(decoder.DECODER_ID, repair_decoder.DECODER_ID)
        self.assertEqual(closure.source_contract.CONTRACT_ID, contract.CONTRACT_ID)

    def test_adapter_has_no_live_or_device_transport(self) -> None:
        source = (SCRIPT_DIR / "prepare_s22plus_fyg8_p292_process_v2.py").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "subprocess",
            "device_action_f1_live_v2",
            "adb ",
            "flash",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
