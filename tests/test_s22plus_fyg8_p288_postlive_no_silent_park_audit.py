from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p288_postlive_no_silent_park_audit as audit  # noqa: E402
import s22plus_fyg8_p288_source_contract as source_contract  # noqa: E402


class P288PostliveNoSilentParkAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = source_contract.source_bytes(ROOT)

    def test_exact_gate_lineage_is_historical_8_to_candidate_12(self):
        result = audit.audit_gate_lineage(ROOT, self.source)
        self.assertEqual(result["historical_p241"]["gate_count"], 8)
        self.assertEqual(result["exact_p288"]["gate_count"], 12)
        self.assertFalse(
            result["returned_gate_failure_is_independent_silence_cause"]
        )
        self.assertFalse(
            result["runtime_pm_attribute_resume_mechanism_supported"]
        )

    def test_all_sixteen_p286_quiet_parks_are_enumerated(self):
        result = audit.audit_p286_park_inventory(ROOT)
        self.assertEqual(result["site_count"], 16)
        self.assertEqual(sum(result["function_counts"].values()), 16)
        self.assertTrue(result["all_sites_enumerated"])
        self.assertEqual(result["durable_prepublication_site_count"], 2)
        self.assertEqual(result["attempt_only_or_unproved_site_count"], 14)
        self.assertFalse(result["absolute_no_silent_park_invariant_proved"])

    def test_publication_self_failure_breaks_no_silent_park_claim(self):
        close_return = audit.audit_exact_close_return(
            audit.resolve_shared_input(ROOT, audit.DEFAULT_BASE_ARCHIVE)
        )
        result = audit.audit_publication_self_failure(
            self.source, close_return
        )
        self.assertFalse(result["current_no_silent_park_invariant_holds"])
        self.assertTrue(result["kernel_postcommit_estale_precedes_state_update"])
        self.assertTrue(result["kernel_has_no_error_return_after_state_update"])
        self.assertTrue(
            result["successful_write_then_stale_client_divergence_rejected"]
        )
        self.assertTrue(result["exact_procfs_close_error_rejected"])
        self.assertFalse(result["exact_procfs_close_error_instantiates_model"])
        self.assertFalse(result["proves_live_cause"])

    def test_formal_postbuild_proof_passed_and_is_bounded(self):
        result = audit.audit_postbuild_proof(
            ROOT, ROOT / audit.DEFAULT_CANDIDATE_STATIC
        )
        self.assertEqual(
            result["candidate_static_verdict"],
            "PASS_P288_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY",
        )
        self.assertEqual(
            result["host_native_replay"]["checked_pairs"], 6_815_744
        )
        self.assertEqual(result["host_native_replay"]["accepted_pairs"], 103)
        self.assertTrue(
            result["source_or_table_validator_mismatch_strongly_rejected"]
        )
        self.assertFalse(
            result["runtime_publication_return_or_state_mismatch_rejected"]
        )

    def test_pre_live_park_gate_proved_attempt_not_commit(self):
        result = audit.audit_pre_live_park_gate_scope(self.source)
        self.assertTrue(
            result["proves_publication_attempt_before_raw_park"]
        )
        self.assertFalse(
            result["proves_successful_publication_before_raw_park"]
        )
        self.assertTrue(result["publication_dominance_claim_is_too_strong"])
        self.assertEqual(
            result["exact_p288_e3_include_quiet_park_call_count"], 17
        )


if __name__ == "__main__":
    unittest.main()
