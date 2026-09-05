from __future__ import annotations

from pathlib import Path
import hashlib
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p344_open_read_branch_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p344_open_read_branch_runtime as runtime  # noqa: E402


class P344ObserverTests(unittest.TestCase):
    def test_binding_is_fresh_and_retains_p343_geometry(self) -> None:
        value = observer.audit_binding()
        self.assertEqual(value["run_id_hex"], runtime.P344_RUN_ID_HEX)
        self.assertEqual(
            value["predecessor_run_id"], runtime.P343_PREDECESSOR_RUN_ID_HEX
        )
        self.assertEqual(observer.SAME_FD_SESSIONS, 3)
        self.assertEqual(observer.IDLE_SECONDS, 120)
        self.assertEqual(observer.TOTAL_SESSIONS, 4)
        self.assertEqual(observer.TOTAL_COMMANDS, 12)
        self.assertTrue(value["host_first_open"])
        self.assertTrue(value["idle_listener_unchanged"])
        self.assertTrue(value["catalog_unchanged"])
        self.assertFalse(value["catalog_allowlist_expanded"])
        self.assertTrue(value["runtime_behavior_unchanged"])
        self.assertFalse(value["device_contact"])

    def test_retained_stream_requires_fresh_banner(self) -> None:
        with self.assertRaises(observer.P344ObserverBindingError):
            observer.parse_retained_open_read_branch(b"not-a-banner")

    def test_four_session_validator_uses_default_kernel_tuple(self) -> None:
        commands = [
            {"command_sha256": hashlib.sha256(item).hexdigest()}
            for item in observer.DEFAULT_COMMANDS
        ]
        proof = {
            "sessions": [
                {
                    "physical_reopen_index": 1 if index == 3 else 0,
                    "commands": list(commands),
                }
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
        with self.assertRaises(observer.P344ObserverBindingError):
            observer.validate_four_session_proof(changed)

    def test_p343_observer_globals_remain_untouched(self) -> None:
        import s22plus_fyg8_p343_open_read_branch_acm_observer as predecessor

        self.assertEqual(
            predecessor.P343_RUN_ID_HEX, runtime.P343_PREDECESSOR_RUN_ID_HEX
        )
        self.assertEqual(observer.P344_RUN_ID_HEX, runtime.P344_RUN_ID_HEX)
        self.assertNotEqual(observer.DEFAULT_COMMANDS, predecessor.DEFAULT_COMMANDS)


if __name__ == "__main__":
    unittest.main()
