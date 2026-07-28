from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p282_linked_audit as p282_audit  # noqa: E402
import s22plus_fyg8_p284_linked_audit as p284_audit  # noqa: E402
import s22plus_fyg8_p284_source_contract as p284  # noqa: E402


class P284LinkedAuditTests(unittest.TestCase):
    def test_adapter_identity_is_versioned(self) -> None:
        self.assertEqual(
            p284_audit.EXPECTED_SOURCE_CONTRACT_ID, p284.CONTRACT_ID
        )
        self.assertEqual(
            p284_audit.ADAPTER_ID, "s22plus-fyg8-p284-linked-audit-v1"
        )

    def test_adapter_includes_inherited_validator_functions(self) -> None:
        self.assertEqual(
            p284_audit.LINKED_VALIDATOR_SYMBOLS,
            tuple(
                dict.fromkeys(
                    (
                        *p284.LINKED_VALIDATOR_SYMBOLS,
                        *p282_audit.P282_VALIDATOR_FUNCTIONS,
                    )
                )
            ),
        )

    def test_storage_normalization_is_p282_identical(self) -> None:
        logical = p284.linked_table_bytes()
        self.assertEqual(
            p284_audit.linked_table_storage_bytes(logical),
            p282_audit.linked_table_storage_bytes(logical),
        )

    def test_adapter_context_restores_historical_globals(self) -> None:
        historical = (
            p282_audit.ADAPTER_ID,
            p282_audit.EXPECTED_SOURCE_CONTRACT_ID,
            p282_audit.p282,
        )
        with p284_audit._p284_adapter():
            self.assertEqual(p282_audit.ADAPTER_ID, p284_audit.ADAPTER_ID)
            self.assertIs(p282_audit.p282, p284)
        self.assertEqual(
            (
                p282_audit.ADAPTER_ID,
                p282_audit.EXPECTED_SOURCE_CONTRACT_ID,
                p282_audit.p282,
            ),
            historical,
        )


if __name__ == "__main__":
    unittest.main()
