from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402
import s22plus_fyg8_p328_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p328_auth_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p328_auth_exec_runtime as runtime  # noqa: E402
import s22plus_fyg8_p328_stock_process_v2_adapter as adapter  # noqa: E402


def acceptance() -> dict[str, object]:
    value = dict(adapter.acceptance_fixture())
    value["auth_key"] = dict(evidence.P328_AUTH_EXEC_AUTH_KEY_IDENTITY)
    return value


class P328CommonRegistrationTests(unittest.TestCase):
    def test_authenticated_observer_is_exact_and_non_pty(self) -> None:
        spec = evidence.p328_authenticated_framed_observer_spec()
        self.assertEqual(
            evidence.validate_candidate_arrival_proof_role(
                evidence.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE,
                spec,
                expected_run_id=runtime.P328_RUN_ID_HEX,
            ),
            evidence.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE,
        )
        self.assertEqual(spec["wire_magic"], "S328")
        self.assertEqual(spec["frame_header_size"], 16)
        self.assertEqual(spec["max_frame_payload"], 1055)
        self.assertEqual(spec["max_commands"], 16)
        self.assertEqual(spec["command_timeout_sec"], 15)
        self.assertEqual(spec["max_output_bytes"], 131072)
        self.assertEqual(spec["auth_algorithm"], "hmac-sha256")
        self.assertEqual(spec["auth_tag_size"], 32)
        self.assertEqual(spec["auth_key_schema"], artifact.AUTH_KEY_SCHEMA)
        self.assertEqual(spec["auth_key_size"], 32)
        self.assertEqual(
            spec["auth_key"], evidence.P328_AUTH_EXEC_AUTH_KEY_IDENTITY
        )
        self.assertTrue(spec["per_session_random_nonce"])
        self.assertTrue(spec["caller_selected_command"])
        self.assertFalse(spec["interactive_pty"])
        self.assertEqual(spec["proof_command_count"], 3)
        self.assertNotIn("auth-key-v1.bin", json.dumps(spec, sort_keys=True))

        changed = copy.deepcopy(spec)
        changed["interactive_pty"] = True
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_candidate_arrival_proof_role(
                evidence.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE,
                changed,
                expected_run_id=runtime.P328_RUN_ID_HEX,
            )
        changed = copy.deepcopy(spec)
        changed["auth_key"] = {"size": 32, "sha256": "0" * 64}
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_candidate_arrival_proof_role(
                evidence.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE,
                changed,
                expected_run_id=runtime.P328_RUN_ID_HEX,
            )
        changed = copy.deepcopy(spec)
        changed["auth_key"] = {"size": True, "sha256": spec["auth_key"]["sha256"]}
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_candidate_arrival_proof_role(
                evidence.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE,
                changed,
                expected_run_id=runtime.P328_RUN_ID_HEX,
            )

    def test_acceptance_key_projection_and_predecessor_are_rejected(self) -> None:
        value = acceptance()
        self.assertIs(evidence.validate_acceptance(value), value)
        for wrong_key in (
            {"size": 31, "sha256": evidence.P328_AUTH_EXEC_AUTH_KEY_IDENTITY["sha256"]},
            {"size": 32, "sha256": "0" * 64},
            {"size": 32, "sha256": evidence.P328_AUTH_EXEC_AUTH_KEY_IDENTITY["sha256"], "path": "private"},
        ):
            changed = copy.deepcopy(value)
            changed["auth_key"] = wrong_key
            with self.subTest(wrong_key=wrong_key), self.assertRaises(
                evidence.EvidenceError
            ):
                evidence.validate_acceptance(changed)

        predecessor = copy.deepcopy(value)
        predecessor["run_id"] = adapter.P327_RUN_ID_HEX
        with self.assertRaises((evidence.EvidenceError, ValueError)):
            evidence.validate_acceptance(predecessor)
        predecessor = copy.deepcopy(value)
        predecessor["userspace_overlay_contract_id"] = (
            evidence.P327_STOCK_OVERLAY_CONTRACT_ID
        )
        with self.assertRaises((evidence.EvidenceError, ValueError)):
            evidence.validate_acceptance(predecessor)

    def test_core_observer_binding_is_p328_only(self) -> None:
        value = acceptance()
        spec = evidence.p328_authenticated_framed_observer_spec()
        core.verify_candidate_observer_binding(value, spec)
        with self.assertRaises(core.F1V2Error):
            core.verify_candidate_observer_binding(value, None)

        changed = copy.deepcopy(value)
        changed["run_id"] = adapter.P327_RUN_ID_HEX
        with self.assertRaises(core.F1V2Error):
            core.verify_candidate_observer_binding(changed, spec)
        changed = copy.deepcopy(value)
        changed["userspace_overlay_contract_id"] = (
            evidence.P327_STOCK_OVERLAY_CONTRACT_ID
        )
        with self.assertRaises(core.F1V2Error):
            core.verify_candidate_observer_binding(changed, spec)

    def test_overlay_role_and_auth_key_identity_are_registered(self) -> None:
        self.assertEqual(
            evidence.STOCK_ADAPTERS[evidence.P328_STOCK_OVERLAY_CONTRACT_ID],
            evidence.p328_stock_adapter,
        )
        self.assertNotEqual(
            evidence.P328_STOCK_OVERLAY_CONTRACT_ID,
            evidence.P327_STOCK_OVERLAY_CONTRACT_ID,
        )
        self.assertNotEqual(evidence.P328_RUN_ID, evidence.P327_RUN_ID)
        self.assertEqual(adapter.P328_RUN_ID_HEX, runtime.P328_RUN_ID_HEX)
        self.assertEqual(
            {"size": 32, "sha256": hashlib.sha256(b"p" * 32).hexdigest()},
            artifact.validate_auth_key(b"p" * 32),
        )
        self.assertEqual(
            evidence.P328_CANDIDATE_STATIC_SCHEMA,
            "s22plus_fyg8_p328_process_v2_candidate_static_v1",
        )
        self.assertEqual(
            evidence.P328_CANDIDATE_STATIC_AUTHORITY_PATH,
            "workspace/public/src/scripts/analysis/"
            "s22plus_fyg8_p328_process_v2_candidate_static.py",
        )

    def test_p328_ap_closure_rejects_wrong_key_and_predecessor(self) -> None:
        identity = {"size": 1, "sha256": "0" * 64}
        closure = {
            "kind": "p328_exact_authenticated_framed_exec_ap_v1",
            "boot_img_lz4": identity,
            "boot_image": identity,
            "image": identity,
            "init": identity,
            "child": identity,
            "busybox": identity,
            "latch": identity,
            "auth_key_schema": evidence.P328_AUTH_EXEC_AUTH_KEY_SCHEMA,
            "auth_key_size": 32,
            "auth_key": dict(evidence.P328_AUTH_EXEC_AUTH_KEY_IDENTITY),
            "auth_key_path_published": False,
            "run_id": evidence.P328_RUN_ID,
            "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": evidence.P328_STOCK_OVERLAY_CONTRACT_ID,
        }
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_e2_ap_payload(b"", closure)
        wrong = copy.deepcopy(closure)
        wrong["auth_key"] = {"size": 32, "sha256": "0" * 64}
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_e2_ap_payload(b"", wrong)
        wrong = copy.deepcopy(closure)
        wrong["run_id"] = evidence.P327_RUN_ID
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_e2_ap_payload(b"", wrong)

    def test_runtime_bound_reopen_does_not_require_private_key(self) -> None:
        with mock.patch.object(
            evidence.p328_artifact_identity,
            "auth_key_identity",
            side_effect=AssertionError("runtime-bound recovery reread the key"),
        ):
            receipts = core.execution_critical_source_receipts(
                acceptance(),
                candidate_arrival_proof_role=(
                    evidence.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE
                ),
                bind_private_inputs=False,
            )
        self.assertEqual(
            receipts["p328_auth_key"],
            evidence.P328_AUTH_EXEC_AUTH_KEY_IDENTITY,
        )


if __name__ == "__main__":
    unittest.main()
