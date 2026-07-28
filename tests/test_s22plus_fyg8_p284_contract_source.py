from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p234_candidate_contract as candidate_contract  # noqa: E402
import s22plus_fyg8_p234_candidate_intent as intent  # noqa: E402
import s22plus_fyg8_p282_source_contract as p282  # noqa: E402
import s22plus_fyg8_p284_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p284_source_contract as p284  # noqa: E402
import s22plus_fyg8_source_contracts as registry  # noqa: E402


class P284ContractSourceTests(unittest.TestCase):
    def test_versioned_registry_selects_p284_without_replacing_p282(self) -> None:
        selected = registry.select(p284.CONTRACT_ID, p284.PROFILE)
        self.assertIs(selected.module, p284)
        self.assertIn(p282.CONTRACT_ID, registry.REGISTRY)
        self.assertIs(registry.REGISTRY[p282.CONTRACT_ID], p282)

    def test_p282_is_historical_only_and_new_candidates_require_p284(
        self,
    ) -> None:
        self.assertIs(
            registry.select(p282.CONTRACT_ID, p282.PROFILE).module,
            p282,
        )
        self.assertNotIn(p282.CONTRACT_ID, intent.candidate_contract_ids())
        self.assertIn(p284.CONTRACT_ID, intent.candidate_contract_ids())
        with self.assertRaisesRegex(
            intent.IntentError, "superseded for new candidates"
        ):
            intent.selected_source_contract_for_candidate(
                p282.CONTRACT_ID, p282.PROFILE
            )
        self.assertIs(
            intent.selected_source_contract_for_candidate(
                p284.CONTRACT_ID, p284.PROFILE
            ).module,
            p284,
        )

    def test_candidate_contract_rejects_crafted_p282_intent(self) -> None:
        value = {
            "target": candidate_contract.TARGET,
            "profile": p282.PROFILE,
            "profile_number": intent.profile_number(p282.PROFILE),
            "identity_preimage": {
                "source_contract_id": p282.CONTRACT_ID,
            },
        }
        with tempfile.TemporaryDirectory(
            prefix="p284-superseded-",
            dir=ROOT / "workspace/private",
        ) as raw:
            directory = Path(raw)
            intent_path = directory / "candidate-intent.json"
            patch_path = directory / "candidate.patch"
            intent_path.write_text(
                json.dumps(value, sort_keys=True) + "\n",
                encoding="ascii",
            )
            patch_path.write_bytes(b"not-reached\n")
            with self.assertRaisesRegex(
                candidate_contract.ContractError,
                "superseded for new candidates",
            ):
                candidate_contract.verify(
                    ROOT,
                    intent.resolve(ROOT, intent.DEFAULT_SOURCE),
                    intent_path,
                    patch_path,
                )

    def test_generated_kernel_inputs_and_linked_tables_are_p282_identical(
        self,
    ) -> None:
        self.assertEqual(p284.generate(ROOT), p282.generate(ROOT))
        self.assertEqual(p284.linked_table_bytes(), p282.linked_table_bytes())
        result = p284.implementation_result(ROOT)
        self.assertTrue(result["p282_generated_byte_identical"])
        self.assertTrue(result["linked_userspace"]["two_link_reproducible"])

    def test_descriptor_changes_only_four_readback_defines(self) -> None:
        historical = p282.trace_descriptor_header(ROOT)
        corrected = p284.trace_descriptor_header(ROOT)
        expected = historical
        replacements = (
            (
                b'#define P282_ROLE_NONE_READBACK "none\\n"',
                b'#define P282_ROLE_NONE_READBACK "none"',
            ),
            (
                b'#define P282_ROLE_PERIPHERAL_READBACK "peripheral\\n"',
                b'#define P282_ROLE_PERIPHERAL_READBACK "peripheral"',
            ),
            (
                b'#define P282_CHILD_SUSPENDED_READBACK "suspended\\n"',
                b'#define P282_CHILD_SUSPENDED_READBACK "suspended"',
            ),
            (
                b'#define P282_CHILD_ACTIVE_READBACK "active\\n"',
                b'#define P282_CHILD_ACTIVE_READBACK "active"',
            ),
        )
        for old, new in replacements:
            self.assertEqual(expected.count(old), 1)
            expected = expected.replace(old, new)
        self.assertEqual(corrected, expected)
        self.assertNotEqual(
            hashlib.sha256(corrected).digest(),
            hashlib.sha256(historical).digest(),
        )

    def test_token_and_wire_mutations_fail_closed(self) -> None:
        spec.validate()
        with mock.patch.object(spec, "ROLE_NONE_READBACK", "none\n"):
            with self.assertRaisesRegex(
                spec.SpecError, "readback contains wire framing"
            ):
                spec.validate()
        with mock.patch.object(spec, "ROLE_NONE_WRITE", "none"):
            with self.assertRaisesRegex(
                spec.SpecError, "none write/readback token drifted"
            ):
                spec.validate()

    def test_source_inventory_binds_overlay_and_historical_sources(self) -> None:
        data, receipts = p284.source_receipts(ROOT)
        self.assertEqual(set(data), p284.SOURCE_KEYS)
        self.assertEqual(set(receipts), p284.SOURCE_KEYS)
        self.assertIn("source_contract", data)
        self.assertIn("p284_source_contract", data)
        self.assertNotIn("p284_sysfs_ingestion_oracle", data)

    def test_userspace_audit_uses_p284_source_check_identity(self) -> None:
        generated = p284.generate(ROOT)
        source = p284.source_bytes(ROOT)
        with mock.patch.object(
            p284.p252,
            "_audit_userspace",
            return_value={"verified": True},
        ) as audit, tempfile.TemporaryDirectory(prefix="p284-audit-") as raw:
            result = p284._audit_userspace(ROOT, generated, source, Path(raw))
        self.assertTrue(result["verified"])
        self.assertEqual(
            audit.call_args.kwargs["source_check_run_id"],
            p284.SOURCE_CHECK_RUN_ID,
        )
        self.assertNotEqual(
            p284.SOURCE_CHECK_RUN_ID,
            p282.SOURCE_CHECK_RUN_ID,
        )


if __name__ == "__main__":
    unittest.main()
