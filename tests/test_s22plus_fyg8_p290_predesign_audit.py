from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p290_predesign_audit as audit  # noqa: E402


class P290PredesignAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ROOT
        cls.intent_path = audit.resolve_shared(ROOT, audit.DEFAULT_INTENT)
        cls.identity, cls.materialized = audit.frozen_sources(
            ROOT, cls.intent_path
        )

    def test_frozen_p288_source_receipts_are_exact(self):
        self.assertEqual(self.identity["source_key_count"], 83)
        self.assertEqual(self.identity["source_keys_changed"], [])

    def test_runtime_ordinal_88_derives_request_pair_0x90_item_0(self):
        result = audit.audit_runtime_request(
            self.materialized,
            ROOT,
            audit.resolve_shared(ROOT, audit.DEFAULT_CANDIDATE_STATIC),
        )
        self.assertEqual(result["symbolic_ordinal"], 88)
        self.assertEqual(result["linked_table_pair"], [0x90, 0])
        self.assertTrue(result["runtime_correct_request_construction_proved"])
        self.assertFalse(result["caller_encodes_wire_pair_directly"])

    def test_retained_slot_rejects_generation_89_crc_clear(self):
        intent, _ = audit.read_json(self.intent_path, "P2.88 intent")
        patch = audit.verify_receipt(
            self.intent_path.parent / "candidate.patch",
            intent["patch"],
            "P2.88 patch",
        )
        result = audit.audit_retained_slot_protocol(
            patch,
            audit.resolve_shared(ROOT, audit.DEFAULT_RETAINED_A),
            audit.resolve_shared(ROOT, audit.DEFAULT_RETAINED_B),
        )
        self.assertEqual(result["active_generation"], 88)
        self.assertEqual(result["generation_89_target_slot"], 1)
        self.assertFalse(result["separate_persistent_staging_region"])
        self.assertFalse(result["generation_89_reached_target_crc_clear"])
        self.assertTrue(result["generation_89_postcommit_estale_rejected"])
        self.assertFalse(result["generation_88_postcommit_estale_rejected"])


if __name__ == "__main__":
    unittest.main()
