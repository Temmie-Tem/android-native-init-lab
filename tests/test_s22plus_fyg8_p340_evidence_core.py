from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
for directory in (
    ROOT / "workspace/public/src/scripts/revalidation",
    ROOT / "workspace/public/src/scripts/analysis",
):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402
import s22plus_fyg8_p340_open_read_branch_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p340_open_read_branch_runtime as runtime  # noqa: E402


def _proof_fixture() -> dict[str, object]:
    commands = [
        {
            "size": len(command),
            "sha256": hashlib.sha256(command).hexdigest(),
        }
        for command in runtime.DEFAULT_COMMANDS
    ]
    sessions = []
    for index in range(observer.MAX_SESSIONS):
        sessions.append(
            {
                "session_index": index,
                "physical_reopen_index": 0 if index < 2 else 1,
                "challenge_nonce_sha256": hashlib.sha256(
                    f"nonce-{index}".encode("ascii")
                ).hexdigest(),
                "boot_id_sha256": hashlib.sha256(b"boot").hexdigest(),
                "auth_key_sha256": hashlib.sha256(b"auth-key").hexdigest(),
                "commands": [
                    {
                        "sequence": sequence,
                        "command_sha256": hashlib.sha256(command).hexdigest(),
                    }
                    for sequence, command in zip((3, 4, 5), runtime.DEFAULT_COMMANDS)
                ],
                "tx": {},
                "raw_tx": {},
                "rx": {},
                "raw_rx": {},
                "diagnostics": [],
                "pid1_authenticated_framed_exec_proof": True,
                "busybox_ash_command_proof": True,
                "interactive_pty_proof": False,
                "caller_selected_command": False,
            }
        )
    return {
        "schema": observer.SCHEMA,
        "contract_id": observer.CONTRACT_ID,
        "target": runtime.TARGET,
        "run_id_hex": runtime.P340_RUN_ID_HEX,
        "session_cap": observer.MAX_SESSIONS,
        "reconnect_cap": observer.MAX_RECONNECTS,
        "session_count": observer.MAX_SESSIONS,
        "successful_sessions": observer.MAX_SESSIONS,
        "reconnect_count": observer.MAX_RECONNECTS,
        "physical_reopen_count": observer.PHYSICAL_REOPEN_COUNT,
        "fixed_command_count": len(runtime.DEFAULT_COMMANDS),
        "hmac_authenticated": True,
        "pid1_authenticated_framed_exec_proof": True,
        "busybox_ash_command_proof": True,
        "diagnostic_order_proof": True,
        "per_boot_identity_proof": True,
        "same_initial_fd": True,
        "same_tty_fd": True,
        "same_boot_id": True,
        "descriptor_reopened": True,
        "retained_listener_proof": True,
        "partial_raw_retention": True,
        "caller_selected_command": False,
        "interactive_pty": False,
        "arbitrary_file_transfer": False,
        "persistent_state": False,
        "listener_replays_commands": False,
        "fixed_commands": commands,
        "sessions": sessions,
    }


class P340EvidenceCoreTests(unittest.TestCase):
    def test_acceptance_and_decoder_are_bound_to_fresh_p340_namespace(self) -> None:
        acceptance = evidence.p340_stock_adapter.acceptance_fixture()
        acceptance["auth_key"] = dict(evidence.P340_AUTH_EXEC_AUTH_KEY_IDENTITY)
        self.assertIs(evidence.validate_acceptance(acceptance), acceptance)
        record = evidence.p340_stock_adapter.encode_fixture()
        decoded = evidence.p340_stock_adapter.decode_record(record)
        self.assertEqual(decoded["run_id"], evidence.P340_RUN_ID)
        self.assertNotEqual(decoded["run_id"], evidence.P339_RUN_ID)

    def test_p340_proof_is_strict_and_not_p339(self) -> None:
        value = _proof_fixture()
        self.assertIs(evidence.validate_p340_open_read_branch_proof(value), value)
        changed = copy.deepcopy(value)
        changed["sessions"][2]["commands"][1]["command_sha256"] = "0" * 64  # type: ignore[index]
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_p340_open_read_branch_proof(changed)
        stale = copy.deepcopy(value)
        stale["run_id_hex"] = evidence.P339_RUN_ID
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_p340_open_read_branch_proof(stale)

    def test_p340_baseline_uses_strict_clean_classifier(self) -> None:
        acceptance = evidence.p340_stock_adapter.acceptance_fixture()
        acceptance["auth_key"] = dict(evidence.P340_AUTH_EXEC_AUTH_KEY_IDENTITY)
        clean = evidence.classify_clean_baseline(
            bytes(evidence.p340_stock_adapter.RAW_SIZE), acceptance
        )
        self.assertTrue(clean["baseline_clean"])
        current = bytearray(evidence.p340_stock_adapter.RAW_SIZE)
        record = evidence.p340_stock_adapter.encode_fixture()
        current[: len(record)] = record
        with self.assertRaises(ValueError):
            evidence.classify_clean_baseline(bytes(current), acceptance)

    def test_core_binds_p340_sources_and_keeps_other_census_out(self) -> None:
        acceptance = evidence.p340_stock_adapter.acceptance_fixture()
        acceptance["auth_key"] = dict(evidence.P340_AUTH_EXEC_AUTH_KEY_IDENTITY)
        receipts = core.execution_critical_source_receipts(
            acceptance,
            candidate_arrival_proof_role=(
                evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
            ),
            bind_private_inputs=True,
        )
        for key in (
            "p340_stock_adapter",
            "p340_open_read_branch_acm_observer",
            "p340_open_read_branch_runtime",
            "p340_artifact_identity",
            "p340_open_failure_capture",
        ):
            self.assertIn(key, receipts)
        self.assertNotEqual(
            receipts["p340_open_read_branch_acm_observer"],
            receipts.get("p339_open_read_branch_acm_observer"),
        )
        self.assertFalse(
            any(
                token in key.lower()
                for key in receipts
                for token in ("census", "other_target", "target_external")
            )
        )


if __name__ == "__main__":
    unittest.main()
