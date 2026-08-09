#!/usr/bin/env python3
"""Focused P3.13 Process-v2, Carrier-v2, and guard-lifetime tests."""

from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as process_v2  # noqa: E402
import s22plus_fyg8_p313_guard_lifetime_fixture as guard_fixture  # noqa: E402
import s22plus_fyg8_p313_overlay_contract as overlay  # noqa: E402
import s22plus_fyg8_p313_process_v2_adapter_fixture as adapter_fixture  # noqa: E402
import s22plus_fyg8_p313_telemetry_decoder as decoder  # noqa: E402


class P313ProcessV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = overlay.verify_intent(ROOT, ROOT / overlay.DEFAULT_INTENT)

    def minimal_acceptance(self) -> dict[str, object]:
        return {
            "kind": evidence.E1_LATEST_STAGE_KIND,
            "profile": overlay.PROFILE,
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        }

    def test_decoder_and_carrier_round_trip_are_p313_bound(self) -> None:
        self.assertIs(
            evidence._latest_stage_observation_decoder(  # noqa: SLF001
                overlay.PARENT_SOURCE_CONTRACT_ID,
                overlay.PROFILE,
                overlay.CONTRACT_ID,
            ),
            decoder,
        )
        result = adapter_fixture.audit(ROOT)
        self.assertEqual(result["verdict"], adapter_fixture.VERDICT)
        self.assertTrue(result["json_safe"])
        self.assertTrue(result["foreign_count_zero"])
        self.assertTrue(result["unknown_overlay_rejected"])

    def test_execution_receipts_bind_the_exact_p313_overlay(self) -> None:
        acceptance = self.minimal_acceptance()
        execution = process_v2.execution_critical_source_receipts(acceptance)
        selected = {
            name: value
            for name, value in execution.items()
            if name.startswith("p313_overlay_source_")
        }
        self.assertEqual(len(selected), len(overlay.SOURCE_KEYS))
        self.assertIn("p313_overlay_intent", execution)
        verification = {
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
            "candidate_source_receipts": evidence.validate_candidate_source_preimage(
                self.contract["parent_candidate_contract"],
                overlay.PROFILE,
                self.contract["run_id"],
            ),
            "p313_overlay_source_receipts": self.contract["source_receipts"],
        }
        process_v2.verify_candidate_source_binding(
            acceptance, verification, execution
        )
        changed = copy.deepcopy(execution)
        first = sorted(overlay.SOURCE_KEYS)[0]
        changed[f"p313_overlay_source_{first}"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(process_v2.F1V2Error, "overlay source differs"):
            process_v2.verify_candidate_source_binding(
                acceptance, verification, changed
            )

    def test_guard_lifetime_fixture_preserves_v2_and_binds_p313(self) -> None:
        result = guard_fixture.audit()
        self.assertEqual(result["verdict"], guard_fixture.VERDICT)
        self.assertEqual(result["v2"]["default_max_sec"], 360)
        self.assertEqual(result["p313"]["derived_max_sec"], 1200)
        self.assertTrue(result["p313"]["partial_upgrade_rejected"])
        self.assertEqual(
            result["expiry_semantics"],
            {
                "accepted_then_expired": True,
                "expired_before_banner": False,
                "normal_release": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
