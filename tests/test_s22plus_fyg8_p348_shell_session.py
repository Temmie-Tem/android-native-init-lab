"""Focused H0 tests for the fresh P348 retained-shell lease namespace."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workspace/public/src/scripts/revalidation"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

import s22plus_fyg8_p348_shell_session as session  # noqa: E402


def binding() -> dict:
    run_id = "a1" * 16
    return {
        "target": dict(session.TARGET),
        "topology": {"sha256": "b2" * 32},
        "candidate": {
            "run_id": run_id,
            "boot_sha256": "c3" * 32,
            "ap_sha256": "d4" * 32,
        },
        "key": {"size": 32, "sha256": "e5" * 32},
        "shell": {
            "capability": "read-only-shell",
            "command_encoding": "utf-8",
            "max_command_bytes": session.MAX_COMMAND_BYTES,
            "max_output_bytes": session.MAX_OUTPUT_BYTES,
            "observer_contract": "s22plus-fyg8-p348-observer-v1",
            "runtime_contract": "s22plus-fyg8-p348-runtime-v1",
            "run_id": run_id,
            "session_seconds": session.SESSION_WINDOW_SECONDS,
        },
        "recovery": {
            "kind": "magisk_boot_only",
            "owner": session.OWNER,
            "rollback_ap_sha256": "f6" * 32,
        },
        "per_boot_id": "07" * 32,
    }


def observation() -> dict:
    return {
        "state": "OBSERVED",
        "candidate_boot_ready": True,
        "journal_sha256": "18" * 32,
    }


class P348ShellLeaseTests(unittest.TestCase):
    def publish(self, root: Path, *, duration: int = 120) -> session.ShellLease:
        return session.ShellLease.publish(
            root,
            binding(),
            observation(),
            duration_seconds=duration,
            lease_id="12" * 16,
        )

    def test_fresh_namespace_has_host_clock_guard_and_exact_shell_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease = self.publish(root)
            self.assertEqual(lease.lease["schema"], session.SCHEMA)
            self.assertEqual(lease.lease["clock_kind"], session.CLOCK_KIND)
            self.assertEqual(lease.lease["max_actions"], 16)
            self.assertEqual(lease.lease["shell_capability"]["max_command_bytes"], 1023)
            self.assertEqual(
                session.ShellLease.open(root).binding["candidate"]["run_id"],
                binding()["candidate"]["run_id"],
            )
            with self.assertRaises(session.LeaseError):
                session.ShellLease.publish(root, binding(), observation())

    def test_command_identity_is_bound_before_result_and_mismatch_stops(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease = self.publish(root)
            command = b"cat /proc/version"
            intent = lease.begin_action(
                session.identity(command),
                binding(),
                command_path="p348-shell-actions/action-01/command.bin",
            )
            bad = {
                "status": "completed",
                "command": session.identity(b"uname -a"),
                "session_complete": True,
                "command_outcome": "ok",
                "continuation_allowed": True,
                "receipt_bytes": 1,
                "receipt_sha256": hashlib.sha256(b"x").hexdigest(),
            }
            with self.assertRaises(session.RollbackRequired):
                lease.record_action_result(intent, bad, binding())
            self.assertEqual(session.ShellLease.open(root).snapshot()["terminal_event"], "DRIFT")

    def test_nonzero_command_result_is_completed_but_exec_failure_stops(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease = self.publish(root)
            command = b"exit 7"
            intent = lease.begin_action(session.identity(command), binding(), now_ns=session.clock_now_ns())
            receipt = hashlib.sha256(b"receipt").hexdigest()
            row = lease.record_action_result(
                intent,
                {
                    "status": "completed",
                    "command": session.identity(command),
                    "session_complete": True,
                    "command_outcome": "command-failed",
                    "continuation_allowed": True,
                    "receipt_bytes": 7,
                    "receipt_sha256": receipt,
                },
                binding(),
            )
            self.assertEqual(row["status"], "completed")
            self.assertFalse(session.ShellLease.open(root).snapshot()["rollback_required"])

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease = self.publish(root)
            command = b"/bin/unknown"
            intent = lease.begin_action(session.identity(command), binding())
            lease.record_action_result(
                intent,
                {
                    "status": "failed",
                    "command": session.identity(command),
                    "session_complete": True,
                    "command_outcome": "exec-failed",
                    "continuation_allowed": False,
                    "receipt_bytes": 7,
                    "receipt_sha256": receipt,
                },
                binding(),
            )
            self.assertTrue(session.ShellLease.open(root).snapshot()["rollback_required"])

    def test_sixteen_action_budget_and_full_session_window(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease = self.publish(root, duration=180)
            for ordinal in range(1, session.MAX_ACTIONS + 1):
                command = f"cat /proc/{ordinal}".encode()
                intent = lease.begin_action(session.identity(command), binding())
                lease.record_action_result(
                    intent,
                    {
                        "status": "completed",
                        "command": session.identity(command),
                        "session_complete": True,
                        "command_outcome": "ok",
                        "continuation_allowed": True,
                        "receipt_bytes": ordinal,
                        "receipt_sha256": hashlib.sha256(str(ordinal).encode()).hexdigest(),
                    },
                    binding(),
                )
            state = session.ShellLease.open(root).snapshot()
            self.assertEqual(state["actions_completed"], session.MAX_ACTIONS)
            self.assertEqual(state["terminal_event"], "ACTION_BUDGET")
            with self.assertRaises(session.RollbackRequired):
                session.ShellLease.open(root).begin_action(session.identity(b"id"), binding())

    def test_suspend_and_host_epoch_fail_closed_but_close_reopen_is_parser_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease = self.publish(root)
            current_epoch = lease.lease["host_epoch"]
            with mock.patch.object(session, "host_epoch", return_value=current_epoch), mock.patch.object(
                session,
                "suspend_delta_ns",
                return_value=lease.lease["opened_suspend_delta_ns"] + session.SUSPEND_TOLERANCE_NS + 1,
            ):
                with self.assertRaises(session.RollbackRequired):
                    session.ShellLease.open(root)
            self.assertEqual(
                session.ShellLease.open(root, validate_clock=False).snapshot(now_ns=lease.lease["opened_elapsed_ns"])["terminal_event"],
                "DRIFT",
            )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease = self.publish(root)
            with mock.patch.object(session, "host_epoch", return_value="f" * 64):
                with self.assertRaises(session.RollbackRequired):
                    session.ShellLease.open(root)
            # The immutable close reader can still inspect the durable event
            # after the live host epoch has changed.
            with mock.patch.object(session, "host_epoch", side_effect=session.LeaseError("offline")):
                reopened = session.ShellLease.open(root, validate_clock=False)
            self.assertEqual(
                reopened.snapshot(now_ns=lease.lease["opened_elapsed_ns"])["terminal_event"],
                "DRIFT",
            )

    def test_capability_acceptance_requires_ordered_checked_roles(self) -> None:
        required = [
            "checked-snapshot",
            "known-nonzero",
            "timeout",
            "active-cancel",
            "post-cancel-success",
        ]
        rows = [{"acceptance_role": role} for role in required]
        self.assertTrue(session._acceptance_summary(None, None, rows)["proved"])
        swapped = [rows[1], rows[0], *rows[2:]]
        self.assertFalse(session._acceptance_summary(None, None, swapped)["proved"])
        self.assertFalse(session._acceptance_summary(None, None, rows[:1])["proved"])

    def test_active_hook_requires_actual_guard_release(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease_root = root / session.DIRECTORY
            lease_root.mkdir(mode=0o700)
            lease = self.publish(lease_root)
            state = {
                "p348_shell_session_active": True,
                "p348_shell_rollback_required": False,
            }
            prepared = type(
                "Prepared",
                (),
                {
                    "run_dir": root,
                    "bundle": type("Bundle", (), {"manifest": {"manifest_id": "m", "run_id": "r"}})(),
                },
            )()
            fake_live = type("Live", (), {})()
            fake_live._state = lambda _prepared: dict(state)
            fake_live._save_state = lambda _prepared, value: state.update(value)
            fake_live._reopen_candidate_guard_release = lambda _prepared: {
                "status": "warning",
                "released": False,
                "warning": "non-tainting",
                "receipt_sha256": "r" * 64,
            }
            fake_live._observer_guard_supports_result = lambda **_kwargs: True
            fake_live._finish_rollback = lambda *_args: {"rollback": "requested"}
            result = session.after_guard_release(
                fake_live,
                prepared,
                None,
                None,
                Path("/unused"),
                None,
                {"proof": True},
            )
            self.assertEqual(result, {"rollback": "requested"})
            self.assertFalse(state["p348_shell_session_active"])
            self.assertTrue(state["p348_shell_rollback_required"])


if __name__ == "__main__":
    unittest.main()
