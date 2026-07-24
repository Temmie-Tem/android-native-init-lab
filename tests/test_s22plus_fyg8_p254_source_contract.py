import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p234_candidate_intent as intent  # noqa: E402
import s22plus_fyg8_p252_source_contract as p252  # noqa: E402
import s22plus_fyg8_p254_e1_decoder as decoder  # noqa: E402
import s22plus_fyg8_p254_source_contract as p254  # noqa: E402
import s22plus_fyg8_source_contracts as contracts  # noqa: E402


class S22PlusFyg8P254SourceContractTest(unittest.TestCase):
    def test_contract_preserves_runtime_and_binds_both_proof_adapters(self):
        self.assertEqual(p254.generate(ROOT), p252.generate(ROOT))
        data, receipts = p254.source_receipts(ROOT)
        self.assertEqual(set(data), p254.SOURCE_KEYS)
        self.assertIn("linked_validator_adapter", data)
        self.assertIn("stock_closure_adapter", data)
        self.assertIn("linked_adapter_dispatch", data)
        self.assertIn("candidate_repro_enforcement", data)
        self.assertEqual(
            receipts["linked_validator_adapter"],
            p254.receipt(data["linked_validator_adapter"]),
        )
        selected = contracts.select(p254.CONTRACT_ID, "E2")
        self.assertIs(selected.module, p254)
        self.assertIs(selected.decoder, decoder)

    def test_adapter_receipt_mutation_changes_derived_run_id(self):
        _data, receipts = p254.source_receipts(ROOT)
        preimage = intent.identity_preimage(
            bytes.fromhex("54" * 16),
            receipts,
            "E2",
            p254.CONTRACT_ID,
        )
        original = intent.derive_run_id(preimage)
        for key in (
            "linked_validator_adapter",
            "stock_closure_adapter",
            "linked_adapter_dispatch",
            "candidate_repro_enforcement",
        ):
            with self.subTest(key=key):
                changed_receipts = copy.deepcopy(receipts)
                changed_receipts[key]["sha256"] = "00" * 32
                changed = intent.identity_preimage(
                    bytes.fromhex("54" * 16),
                    changed_receipts,
                    "E2",
                    p254.CONTRACT_ID,
                )
                self.assertNotEqual(intent.derive_run_id(changed), original)

    def test_implementation_rejects_legacy_global_mutation_tokens(self):
        data = p254.source_bytes(ROOT)
        self.assertNotIn(
            b"legacy.EXPECTED_ELF_ENTRYPOINTS =",
            data["stock_closure_adapter"],
        )
        self.assertNotIn(
            b"_ENTRYPOINT_LOCK",
            data["stock_closure_adapter"],
        )

    def test_reachable_records_use_p254_decoder_identity(self):
        result = p254.validate_reachable_records(bytes.fromhex("54" * 16))
        self.assertTrue(result["verified"])
        self.assertEqual(result["decoder_policy_id"], decoder.POLICY_ID)


if __name__ == "__main__":
    unittest.main()
