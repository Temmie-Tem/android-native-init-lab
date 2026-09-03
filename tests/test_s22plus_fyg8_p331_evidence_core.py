from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402


class P331EvidenceCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.acceptance = evidence.p331_stock_adapter.acceptance_fixture()
        self.acceptance["auth_key"] = dict(evidence.P331_AUTH_EXEC_AUTH_KEY_IDENTITY)
        self.observer = evidence.p331_authenticated_resident_framed_observer_spec()

    def test_exact_resident_role_and_predecessor_ids_are_bound(self) -> None:
        self.assertEqual(
            evidence.validate_acceptance(self.acceptance), self.acceptance
        )
        self.assertEqual(
            evidence.validate_candidate_arrival_proof_role(
                evidence.CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE,
                self.observer,
                expected_run_id=evidence.P331_RUN_ID,
            ),
            evidence.CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE,
        )
        for predecessor in (evidence.P330_RUN_ID, evidence.P329_RUN_ID):
            with self.assertRaises(evidence.EvidenceError):
                evidence.validate_candidate_arrival_proof_role(
                    evidence.CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE,
                    self.observer,
                    expected_run_id=predecessor,
                )
        stale = copy.deepcopy(self.acceptance)
        stale["predecessor_run_id_rejected"] = evidence.P329_RUN_ID
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_acceptance(stale)

    def test_resident_proof_requires_two_distinct_nonce_hashes_and_fixed_status(self) -> None:
        command = {
            "size": len(evidence.P331_AUTH_EXEC_HEARTBEAT_COMMAND),
            "sha256": hashlib.sha256(
                evidence.P331_AUTH_EXEC_HEARTBEAT_COMMAND
            ).hexdigest(),
        }
        output = {
            "size": len(evidence.P331_AUTH_EXEC_HEARTBEAT_OUTPUT),
            "sha256": hashlib.sha256(
                evidence.P331_AUTH_EXEC_HEARTBEAT_OUTPUT
            ).hexdigest(),
        }
        session = lambda index, nonce: {
            "session_index": index,
            "reconnect_index": index,
            "challenge_nonce_sha256": nonce,
            "auth_key_sha256": evidence.P331_AUTH_EXEC_AUTH_KEY_IDENTITY["sha256"],
            "tx": {"size": 1, "sha256": "1" * 64},
            "rx": {"size": 1, "sha256": "2" * 64},
            "authenticated": True,
            "clean_close": True,
            "command": command,
            "output": output,
        }
        proof = {
            "schema": evidence.p331_resident_acm_observer.SCHEMA,
            "contract_id": evidence.P331_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "target": evidence.p331_resident_exec_runtime.TARGET,
            "run_id_hex": evidence.P331_RUN_ID,
            "session_cap": 2,
            "reconnect_cap": 1,
            "session_count": 2,
            "successful_sessions": 2,
            "reconnect_count": 1,
            "sessions": [session(0, "a" * 64), session(1, "b" * 64)],
            "banner_attempts": 2,
            "banner_scope": "resident_loop_per_session",
            "fixed_heartbeat_status": True,
            "caller_selected_command": False,
            "interactive_pty": False,
            "arbitrary_file_transfer": False,
            "persistent_state": False,
            "resident_loop_proof": True,
            "partial_raw_retention": True,
        }
        self.assertEqual(evidence.validate_p331_resident_proof(proof), proof)
        duplicate = copy.deepcopy(proof)
        duplicate["sessions"][1]["challenge_nonce_sha256"] = "a" * 64
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_p331_resident_proof(duplicate)
        for malformed in (
            {**proof, "session_cap": 2.0},
            {**proof, "banner_attempts": True},
        ):
            with self.assertRaises(evidence.EvidenceError):
                evidence.validate_p331_resident_proof(malformed)
        malformed_index = copy.deepcopy(proof)
        malformed_index["sessions"][0]["session_index"] = False
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_p331_resident_proof(malformed_index)

    def test_core_binds_exact_observer_and_p331_source_receipts(self) -> None:
        core.verify_candidate_observer_binding(self.acceptance, self.observer)
        with self.assertRaises(core.F1V2Error):
            core.verify_candidate_observer_binding(
                self.acceptance, {**self.observer, "caller_selected_command": True}
            )
        receipts = core.execution_critical_source_receipts(
            self.acceptance,
            candidate_arrival_proof_role=evidence.CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE,
            bind_private_inputs=False,
        )
        self.assertTrue(
            {
                "p331_resident_acm_observer",
                "p331_resident_exec_runtime",
                "p331_artifact_identity",
                "p331_auth_key",
            }.issubset(receipts)
        )


if __name__ == "__main__":
    unittest.main()
