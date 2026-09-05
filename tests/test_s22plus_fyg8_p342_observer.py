from __future__ import annotations

from pathlib import Path
import struct
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p335_retained_listener_acm_observer as encoder  # noqa: E402
import s22plus_fyg8_p342_open_read_branch_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p342_open_read_branch_runtime as runtime  # noqa: E402


class P342ObserverTests(unittest.TestCase):
    def _diagnostic(self, stage: int, code: int) -> bytes:
        return encoder.encode_frame(
            runtime.DIAGNOSTIC_FRAME_TYPE,
            0,
            struct.pack("<Ii", stage, code),
        )

    def test_binding_is_fresh_and_strict_four_session_geometry(self) -> None:
        value = observer.audit_binding()
        self.assertEqual(value["run_id_hex"], runtime.P342_RUN_ID_HEX)
        self.assertEqual(observer.MAX_INITIAL_SESSIONS, 3)
        self.assertEqual(observer.MAX_SESSIONS, 4)
        self.assertEqual(observer.MAX_RECONNECTS, 1)
        self.assertEqual(observer.PHYSICAL_REOPEN_COUNT, 1)
        self.assertEqual(observer.SAME_FD_SESSIONS, 3)
        self.assertEqual(observer.TOTAL_COMMANDS, 12)
        self.assertEqual(observer.IDLE_SECONDS, 120)
        self.assertTrue(value["runtime_behavior_unchanged"])
        self.assertTrue(value["idle_listener_unchanged"])

    def test_no_banner_diagnostic_is_rejected_as_raw_no_proof(self) -> None:
        with self.assertRaises(observer.P342ObserverBindingError):
            observer.parse_retained_open_read_branch(self._diagnostic(0, 0))

    def test_valid_p342_diagnostic_binds_fresh_banner(self) -> None:
        raw = (
            runtime.DEVICE_BANNER
            + self._diagnostic(0, 0)
            + self._diagnostic(3, 1)
        )
        value = observer.parse_retained_open_read_branch(raw)
        self.assertTrue(value["banner_seen"])
        self.assertEqual(value["run_id_hex"], runtime.P342_RUN_ID_HEX)
        self.assertFalse(value["candidate_success"])
        self.assertFalse(value["causal_result_allowed"])

    def test_serialized_four_session_validator_requires_three_same_fd_then_reopen(self) -> None:
        commands = [
            {"command_sha256": __import__("hashlib").sha256(item).hexdigest()}
            for item in observer.DEFAULT_COMMANDS
        ]
        proof = {
            "sessions": [
                {"physical_reopen_index": 1 if index == 3 else 0, "commands": list(commands)}
                for index in range(4)
            ],
            "session_count": 4,
            "successful_sessions": 4,
            "session_cap": 4,
            "reconnect_count": 1,
            "reconnect_cap": 1,
            "physical_reopen_count": 1,
            "command_count": 12,
        }
        self.assertIs(observer.validate_four_session_proof(proof), proof)
        changed = {**proof, "sessions": [dict(item) for item in proof["sessions"]]}
        changed["sessions"][2]["physical_reopen_index"] = 1
        with self.assertRaises(observer.P342ObserverBindingError):
            observer.validate_four_session_proof(changed)


if __name__ == "__main__":
    unittest.main()
