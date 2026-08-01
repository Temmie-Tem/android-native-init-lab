#!/usr/bin/env python3
"""Focused tests for the P2.96 Process-v2 offline-promotion adapter."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as process_v2  # noqa: E402
import prepare_s22plus_fyg8_p234_process_v2 as base  # noqa: E402
import prepare_s22plus_fyg8_p296_process_v2 as adapter  # noqa: E402
import s22plus_fyg8_p296_candidate_static_checker as checker  # noqa: E402
import s22plus_fyg8_p296_e2_stock_closure as closure_selector  # noqa: E402
import s22plus_fyg8_p296_identity_tiers as identity  # noqa: E402
import s22plus_fyg8_p296_source_contract as contract  # noqa: E402
import s22plus_fyg8_p296_telemetry_decoder as telemetry_decoder  # noqa: E402


class P296ProcessV2PromotionAdapterTest(unittest.TestCase):
    def test_adapter_configures_only_the_versioned_frontier(self) -> None:
        adapter._configure()
        self.assertIs(base.static_checker, checker)
        self.assertIs(base.e2_closure_selector, closure_selector)
        self.assertEqual(base.SCHEMA, adapter.SCHEMA)
        self.assertEqual(base.TARGET, checker.TARGET)

    def test_defaults_are_p296_scoped(self) -> None:
        args = adapter.parse_args([])
        for value in (args.candidate_static, args.candidate_ap, args.out):
            self.assertIn("s22plus_fyg8_p296", value.as_posix())

    def test_registered_decoder_and_e2_closure_select_p296(self) -> None:
        decoder = evidence._latest_stage_decoder(contract.CONTRACT_ID, "E2")
        closure = evidence._select_e2_closure(contract.CONTRACT_ID)
        self.assertEqual(decoder.DECODER_ID, telemetry_decoder.DECODER_ID)
        self.assertEqual(closure.source_contract.CONTRACT_ID, contract.CONTRACT_ID)
        self.assertEqual(evidence.P296_CANDIDATE_STATIC_SCHEMA, checker.SCHEMA)
        self.assertEqual(evidence.P296_CANDIDATE_STATIC_VERDICT, checker.VERDICT)

    def test_execution_receipts_bind_all_three_p296_tiers(self) -> None:
        receipts = process_v2.execution_critical_source_receipts(
            {
                "kind": evidence.E1_LATEST_STAGE_KIND,
                "profile": "E2",
                "source_contract_id": contract.CONTRACT_ID,
            }
        )
        self.assertEqual(
            len(
                [
                    name
                    for name in receipts
                    if name.startswith("candidate_source_")
                ]
            ),
            len(contract.SOURCE_KEYS),
        )
        self.assertEqual(
            len([name for name in receipts if name.startswith("p296_tier2_")]),
            len(identity.tier2_materials(ROOT)),
        )
        self.assertEqual(
            len([name for name in receipts if name.startswith("p296_tier3_")]),
            len(identity.tier3_materials(ROOT)),
        )

    def test_static_checker_uses_frozen_builder_safety_producer(self) -> None:
        exact_contract = {
            "profile": "E2",
            "source_contract_id": contract.CONTRACT_ID,
        }
        wrapper = checker.candidate.artifact_safety
        checker._configure()
        expected = checker.candidate.base.artifact_safety(exact_contract)
        actual = checker._CANDIDATE_STATIC_VIEW.artifact_safety(exact_contract)
        self.assertEqual(actual, expected)
        self.assertIs(checker.candidate.artifact_safety, wrapper)
        self.assertNotIn("candidate_module_binaries_injected", actual)
        self.assertNotIn("built_in_telemetry_only", actual)
        wrapped = checker.candidate.artifact_safety(exact_contract)
        self.assertEqual(wrapped["candidate_module_binaries_injected"], 0)
        self.assertIs(wrapped["built_in_telemetry_only"], True)

    def test_adapter_has_no_live_or_device_transport(self) -> None:
        source = (
            SCRIPT_DIR / "prepare_s22plus_fyg8_p296_process_v2.py"
        ).read_text(encoding="utf-8")
        for forbidden in ("subprocess", "device_action_f1_live_v2", "adb ", "flash"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
