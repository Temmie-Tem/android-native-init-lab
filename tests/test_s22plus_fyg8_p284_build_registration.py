from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_s22plus_fyg8_p234_candidate as candidate  # noqa: E402
import s22plus_fyg8_p234_build as build  # noqa: E402
import s22plus_fyg8_p234_build_repro_check as repro  # noqa: E402
import s22plus_fyg8_p253_e2_stock_closure as closure  # noqa: E402
import s22plus_fyg8_p284_source_contract as p284  # noqa: E402


class P284BuildRegistrationTests(unittest.TestCase):
    def test_all_execution_registries_select_p284(self) -> None:
        self.assertIn(p284.CONTRACT_ID, build.QUALIFICATION_MODULES)
        self.assertEqual(
            repro.LINKED_VALIDATOR_ADAPTERS[p284.CONTRACT_ID],
            "s22plus_fyg8_p284_linked_audit",
        )
        self.assertEqual(
            closure.select(p284.CONTRACT_ID).source_contract.CONTRACT_ID,
            p284.CONTRACT_ID,
        )

    def test_candidate_safety_matches_p282_authority(self) -> None:
        safety = candidate.artifact_safety(
            {
                "profile": p284.PROFILE,
                "source_contract_id": p284.CONTRACT_ID,
            }
        )
        self.assertEqual(safety["userspace_parent_role_write_count"], 2)
        self.assertFalse(safety["host_role_authority"])
        self.assertFalse(safety["direct_power_clock_reset_mmio_authority"])

    def test_stock_closure_exposes_qualification_entrypoint_adapter(self) -> None:
        selected = closure.select(p284.CONTRACT_ID)
        self.assertIs(selected._entrypoints, selected.p282._entrypoints)


if __name__ == "__main__":
    unittest.main()
