import contextlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/device_action_f1_live_v2.py"
)


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        spec = importlib.util.spec_from_file_location(
            "device_action_f1_live_v2_p300_lifecycle_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT.parent))


class P300SidecarLifecycleTest(unittest.TestCase):
    def test_owner_identity_wait_tolerates_pre_exec_proc_race(self) -> None:
        process = mock.Mock(pid=741)
        process.poll.return_value = None
        identity = {
            "pid": 741,
            "state": "S",
            "parent_pid": 100,
            "process_group_id": 741,
            "session_id": 741,
            "start_ticks": 12345,
        }
        with (
            mock.patch.object(
                self.module,
                "_proc_identity",
                side_effect=[None, identity, identity],
            ),
            mock.patch.object(
                self.module, "_proc_has_owner", side_effect=[False, True]
            ),
            mock.patch.object(self.module.time, "sleep"),
            mock.patch.object(
                self.module.time,
                "monotonic",
                side_effect=[0.0, 0.1, 0.2, 0.3],
            ),
        ):
            self.assertEqual(
                self.module._p300_wait_owned_identity(  # noqa: SLF001
                    process, "owner-token", timeout_sec=1.0
                ),
                identity,
            )
        self.assertEqual(process.poll.call_count, 3)

    def test_owner_identity_wait_remains_bounded(self) -> None:
        process = mock.Mock(pid=742)
        process.poll.return_value = None
        with (
            mock.patch.object(self.module, "_proc_identity", return_value=None),
            mock.patch.object(self.module, "_proc_has_owner") as owner,
            mock.patch.object(self.module.time, "sleep"),
            mock.patch.object(
                self.module.time,
                "monotonic",
                side_effect=[0.0, 0.2, 1.1],
            ),
            self.assertRaises(self.module.F1LiveError),
        ):
            self.module._p300_wait_owned_identity(  # noqa: SLF001
                process, "owner-token", timeout_sec=1.0
            )
        owner.assert_not_called()

    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def prepared(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        run_dir = root / "workspace/private/runs/p300"
        run_dir.mkdir(parents=True)
        binding = {"binding_sha256": "b" * 64}
        result = {"schema": "device_action_usb_trace_sidecar_v1"}
        (run_dir / "p300-usb-trace").mkdir()
        (run_dir / "p300-usb-trace/result.json").write_text(
            json.dumps(result), encoding="utf-8"
        )
        bundle = types.SimpleNamespace(
            manifest={
                "observation": {
                    "acceptance": {
                        "source_contract_id": self.module.typed_evidence.P300_SOURCE_CONTRACT_ID
                    }
                }
            }
        )
        prepared = types.SimpleNamespace(
            root=root,
            run_dir=run_dir,
            bundle=bundle,
            prepared={"p300_usb_trace_binding": binding},
        )
        return temporary, prepared, binding, result

    def test_observer_stack_defers_cleanup_after_durable_observation(self):
        session = object.__new__(self.module._P300UsbTraceSession)
        session.defer_stack_close = True
        session.close = mock.Mock()

        with contextlib.ExitStack() as stack:
            stack.callback(session.close_from_observer_stack)
            session.close_from_observer_stack()
        session.close.assert_not_called()

        session.defer_stack_close = False
        session.close_from_observer_stack()
        session.close.assert_called_once_with()

    def test_source_orders_durable_observation_defer_and_seal_boundary(self):
        source = SCRIPT.read_text(encoding="utf-8")
        execute = source[source.index("def _execute_prepared_locked") :]
        observation = execute.index(
            "trace_session.observation_durable(current)"
        )
        defer = execute.index("trace_session.defer_stack_close = True")
        seal = execute.index("_run_deferred_p300_segment(")
        self.assertLess(observation, defer)
        self.assertLess(defer, seal)

    def test_normal_seal_orders_close_before_boot_ready_then_finalize(self):
        calls = []
        trace = mock.Mock()
        trace.close.side_effect = lambda: calls.append("close")
        trace.finalize.side_effect = lambda: calls.append("finalize")
        journal = mock.Mock()
        journal.event.side_effect = lambda *args: calls.append(
            ("event", *args)
        )

        self.module._seal_p300_before_candidate_boot_ready(
            trace, journal, True
        )

        self.assertEqual(
            calls,
            [
                "close",
                ("event", "candidate_boot_ready", {"proof": True}),
                "finalize",
            ],
        )
        trace.close.assert_called_once_with()
        trace.finalize.assert_called_once_with()

    def test_deferred_segment_cleanup_preserves_original_exception(self):
        session = mock.Mock()
        session.defer_stack_close = True
        session.close.side_effect = RuntimeError("cleanup failure")

        def interrupted_segment():
            raise KeyboardInterrupt("post-observation cut")

        with self.assertRaisesRegex(KeyboardInterrupt, "post-observation cut"):
            self.module._run_deferred_p300_segment(
                session, interrupted_segment
            )

        self.assertFalse(session.defer_stack_close)
        session.close.assert_called_once_with()

    def test_observer_exit_fault_also_reaps_deferred_sidecar(self):
        session = object.__new__(self.module._P300UsbTraceSession)
        session.defer_stack_close = True
        session.close = mock.Mock()

        @contextlib.contextmanager
        def faulty_observer():
            yield
            raise RuntimeError("observer exit fault")

        with self.assertRaisesRegex(RuntimeError, "observer exit fault"):
            with contextlib.ExitStack() as stack:
                stack.push(session.close_from_observer_stack)
                stack.enter_context(faulty_observer())

        session.close.assert_called_once_with()

    def test_cut_after_observation_durable_defers_stack_close_then_recovery_adopts(self):
        temporary, prepared, binding, result = self.prepared()
        self.addCleanup(temporary.cleanup)

        live_session = object.__new__(self.module._P300UsbTraceSession)
        live_session.defer_stack_close = True
        live_session.close = mock.Mock()
        live_session.close_from_observer_stack()
        live_session.close.assert_not_called()

        cleanup = {
            "verified": True,
            "group_absent": True,
            "matching_processes_after": 0,
        }
        integrity = {"verified": True, "integrity_clean": True}
        with (
            mock.patch.object(
                self.module,
                "_p300_recovery_process_cleanup",
                return_value=({"status": "launched"}, cleanup),
            ),
            mock.patch.object(
                self.module.p300_usb_trace,
                "verify_binding",
                return_value=binding,
            ),
            mock.patch.object(
                self.module,
                "_p300_owner_token",
                return_value="owner-token",
            ),
            mock.patch.object(
                self.module.p300_usb_trace,
                "verify_capture_directory",
                return_value=integrity,
            ),
            mock.patch.object(
                self.module,
                "_read_json",
                side_effect=lambda _path, label: (
                    binding if "binding" in label else result
                ),
            ),
            mock.patch.object(
                self.module,
                "_receipt",
                return_value={
                    "name": "result.json",
                    "size": 1,
                    "sha256": "1" * 64,
                },
            ),
        ):
            recovered, _lifecycle = self.module._p300_recovery_session(
                prepared, object()
            )

        self.assertTrue(recovered.closed)
        self.assertIsNone(recovered.process)
        self.assertEqual(recovered.result, result)

    def test_attempt_count_zero_recovery_records_unknown_and_never_finalizes(self):
        temporary, prepared, _binding, _result = self.prepared()
        self.addCleanup(temporary.cleanup)
        cleanup = {
            "verified": True,
            "group_absent": True,
            "matching_processes_after": 0,
        }
        session = self.module._P300UsbTraceSession(prepared, object())
        session.result = {"completed": True}
        session.integrity = {"verified": True}
        session.closed = True
        session.finalize = mock.Mock()
        with mock.patch.object(
            self.module,
            "_p300_recovery_session",
            return_value=(session, ({"status": "launched"}, cleanup)),
        ):
            self.module._p300_reconcile_before_candidate(prepared, object())

        state = self.module._state(prepared)
        self.assertEqual(
            state["p300_usb_trace"]["status"],
            "unknown",
        )
        self.assertEqual(
            state["p300_usb_trace"]["reason"],
            "recovery:before-candidate-window",
        )
        session.finalize.assert_not_called()

    def test_normalize_attempt_count_zero_never_promotes_adopted_capture(self):
        temporary, prepared, _binding, _result = self.prepared()
        self.addCleanup(temporary.cleanup)
        cleanup = {
            "verified": True,
            "group_absent": True,
            "matching_processes_after": 0,
        }
        session = self.module._P300UsbTraceSession(prepared, object())
        session.result = {"completed": True}
        session.integrity = {"verified": True}
        session.closed = True
        session.finalize = mock.Mock()
        lifecycle = ({"status": "launched"}, cleanup)
        journal = mock.Mock()
        journal.state.return_value = "APPROVED"
        journal.records.return_value = []
        with (
            mock.patch.object(
                self.module,
                "_p300_recovery_session",
                return_value=(session, lifecycle),
            ),
            mock.patch.object(
                self.module,
                "_global_registry_recovery_state",
                return_value=("registry-unavailable-preclaim", None),
            ),
            mock.patch.object(
                self.module,
                "_reconcile_transfer_attempts",
                return_value=0,
            ),
        ):
            self.assertFalse(
                self.module._normalize_recovery(prepared, journal)
            )

        state = self.module._state(prepared)
        self.assertEqual(state["p300_usb_trace"]["status"], "unknown")
        session.finalize.assert_not_called()

    def test_recovery_adopts_completed_capture_without_rearming(self):
        temporary, prepared, binding, result = self.prepared()
        self.addCleanup(temporary.cleanup)
        cleanup = {
            "verified": True,
            "group_absent": True,
            "matching_processes_after": 0,
        }
        integrity = {"verified": True, "integrity_clean": True}
        receipt = {"name": "result.json", "size": 1, "sha256": "1" * 64}
        session = self.module._P300UsbTraceSession(prepared, object())
        owner = {"status": "launched"}
        with (
            mock.patch.object(
                self.module.p300_usb_trace,
                "verify_binding",
                return_value=binding,
            ),
            mock.patch.object(
                self.module, "_p300_owner_token", return_value="owner-token"
            ),
            mock.patch.object(
                self.module.p300_usb_trace,
                "verify_capture_directory",
                return_value=integrity,
            ),
            mock.patch.object(
                self.module,
                "_read_json",
                side_effect=lambda _path, label: (
                    binding if "binding" in label else result
                ),
            ),
            mock.patch.object(
                self.module,
                "_receipt",
                return_value=receipt,
            ),
            mock.patch.object(self.module.subprocess, "Popen") as popen,
        ):
            self.assertTrue(session.adopt_completed_capture(owner, cleanup))

        self.assertIsNone(session.process)
        self.assertTrue(session.closed)
        self.assertEqual(session.result, result)
        self.assertEqual(session.integrity, integrity)
        self.assertIs(session.owner_receipt, owner)
        self.assertIs(session.cleanup, cleanup)
        popen.assert_not_called()

        session.process_output = {
            "stdout_size": 10,
            "stdout_sha256": "2" * 64,
            "stderr_size": 0,
            "stderr_sha256": "3" * 64,
        }
        with mock.patch.object(
            self.module, "_receipt", return_value=receipt
        ):
            captured = session.captured_state()
        self.assertEqual(
            captured["process_output"], session.process_output
        )

    def test_adoption_refuses_unverified_cleanup_and_never_reopens_result(self):
        temporary, prepared, binding, _result = self.prepared()
        self.addCleanup(temporary.cleanup)
        session = self.module._P300UsbTraceSession(prepared, object())
        with mock.patch.object(
            self.module.p300_usb_trace,
            "verify_binding",
            return_value=binding,
        ):
            with self.assertRaisesRegex(
                self.module.F1LiveError, "cleanup is not verified"
            ):
                session.adopt_completed_capture(
                    {"status": "launched"}, {"verified": False}
                )
        self.assertIsNone(session.result)
        self.assertFalse(session.closed)

    def test_recovery_helper_reaps_then_adopts_once(self):
        temporary, prepared, binding, result = self.prepared()
        self.addCleanup(temporary.cleanup)
        cleanup = {
            "verified": True,
            "group_absent": True,
            "matching_processes_after": 0,
        }
        lifecycle = ({"status": "launched"}, cleanup)
        integrity = {"verified": True, "integrity_clean": True}
        with (
            mock.patch.object(
                self.module,
                "_p300_recovery_process_cleanup",
                return_value=lifecycle,
            ) as reap,
            mock.patch.object(
                self.module.p300_usb_trace,
                "verify_binding",
                return_value=binding,
            ),
            mock.patch.object(
                self.module, "_p300_owner_token", return_value="owner-token"
            ),
            mock.patch.object(
                self.module.p300_usb_trace,
                "verify_capture_directory",
                return_value=integrity,
            ),
            mock.patch.object(
                self.module,
                "_read_json",
                side_effect=lambda _path, label: (
                    binding if "binding" in label else result
                ),
            ),
            mock.patch.object(
                self.module,
                "_receipt",
                return_value={
                    "name": "result.json",
                    "size": 1,
                    "sha256": "1" * 64,
                },
            ),
        ):
            session, reopened_lifecycle = self.module._p300_recovery_session(
                prepared, object()
            )

        reap.assert_called_once_with(prepared)
        self.assertEqual(reopened_lifecycle, lifecycle)
        self.assertTrue(session.closed)
        self.assertEqual(session.result, result)

    def test_group_foreign_member_race_blocks_first_killpg_escalation(self):
        owned = [
            {
                "pid": 700,
                "process_group_id": 700,
                "session_id": 700,
                "state": "S",
            },
            {
                "pid": 701,
                "process_group_id": 700,
                "session_id": 700,
                "state": "S",
            },
        ]
        foreign = {
            "pid": 799,
            "process_group_id": 700,
            "session_id": 700,
            "state": "S",
        }
        with (
            mock.patch.object(
                self.module, "_p300_owner_token", return_value="owner"
            ),
            mock.patch.object(
                self.module, "_p300_owner_sha256", return_value="digest"
            ),
            mock.patch.object(
                self.module,
                "_p300_owned_processes",
                return_value=owned,
            ),
            mock.patch.object(
                self.module,
                "_p300_group_members",
                side_effect=[owned, [foreign]],
            ),
            mock.patch.object(
                self.module,
                "_proc_has_owner",
                side_effect=lambda pid, _token: pid != foreign["pid"],
            ),
            mock.patch.object(
                self.module,
                "_p300_wait_owner_absent",
                return_value=False,
            ),
            mock.patch.object(self.module.os, "kill") as kill,
            mock.patch.object(self.module.os, "killpg") as killpg,
        ):
            with self.assertRaisesRegex(
                self.module.F1LiveError, "foreign member"
            ):
                self.module._p300_cleanup_owned_processes({}, expected_group=700)

        kill.assert_called_once_with(700, self.module.signal.SIGTERM)
        killpg.assert_not_called()

    def test_group_foreign_member_race_blocks_sigkill_escalation(self):
        owned = [
            {
                "pid": 800,
                "process_group_id": 800,
                "session_id": 800,
                "state": "S",
            },
            {
                "pid": 801,
                "process_group_id": 800,
                "session_id": 800,
                "state": "S",
            },
        ]
        foreign = {
            "pid": 899,
            "process_group_id": 800,
            "session_id": 800,
            "state": "S",
        }
        with (
            mock.patch.object(
                self.module, "_p300_owner_token", return_value="owner"
            ),
            mock.patch.object(
                self.module, "_p300_owner_sha256", return_value="digest"
            ),
            mock.patch.object(
                self.module,
                "_p300_owned_processes",
                return_value=owned,
            ),
            mock.patch.object(
                self.module,
                "_p300_group_members",
                side_effect=[owned, owned, [foreign]],
            ),
            mock.patch.object(
                self.module,
                "_proc_has_owner",
                side_effect=lambda pid, _token: pid != foreign["pid"],
            ),
            mock.patch.object(
                self.module,
                "_p300_wait_owner_absent",
                side_effect=[False, False],
            ),
            mock.patch.object(self.module.os, "kill") as kill,
            mock.patch.object(self.module.os, "killpg") as killpg,
        ):
            with self.assertRaisesRegex(
                self.module.F1LiveError, "foreign member"
            ):
                self.module._p300_cleanup_owned_processes({}, expected_group=800)

        kill.assert_called_once_with(800, self.module.signal.SIGTERM)
        killpg.assert_called_once_with(800, self.module.signal.SIGTERM)

    def test_close_timeout_foreign_member_race_blocks_direct_sigkill(self):
        temporary, prepared, _binding, _result = self.prepared()
        self.addCleanup(temporary.cleanup)
        session = self.module._P300UsbTraceSession(prepared, object())
        process = mock.Mock()
        process.pid = 900
        process.returncode = None
        process.poll.return_value = None
        process.communicate.side_effect = subprocess.TimeoutExpired(
            cmd="sidecar", timeout=30
        )
        session.process = process
        session.binding = {"binding_sha256": "b" * 64}
        session._binding = mock.Mock(return_value=session.binding)
        session._refresh_owner_receipt = mock.Mock()
        session._unknown = mock.Mock()

        cleanup = {
            "verified": False,
            "group_absent": False,
            "error_type": "F1LiveError",
        }
        with (
            mock.patch.object(
                self.module,
                "_p300_owner_token",
                return_value="owner-token",
            ),
            mock.patch.object(
                self.module,
                "_p300_revalidate_group_before_kill",
                side_effect=self.module.F1LiveError(
                    "P3.00 observer process group has a foreign member"
                ),
            ) as revalidate,
            mock.patch.object(
                self.module,
                "_p300_cleanup_owned_processes",
                return_value=cleanup,
            ),
            mock.patch.object(self.module.os, "killpg") as killpg,
        ):
            session._close_impl()

        revalidate.assert_called_once_with("owner-token", 900)
        killpg.assert_not_called()
        process.communicate.assert_called_once_with(timeout=30)
        session._unknown.assert_called_once()

    def test_empty_owned_set_with_expected_pgid_900_rejects_foreign_member(self):
        foreign = {
            "pid": 901,
            "process_group_id": 900,
            "session_id": 900,
            "state": "S",
        }
        with (
            mock.patch.object(
                self.module, "_p300_owner_token", return_value="owner-token"
            ),
            mock.patch.object(
                self.module, "_p300_owner_sha256", return_value="digest"
            ),
            mock.patch.object(
                self.module,
                "_p300_owned_processes",
                return_value=[],
            ),
            mock.patch.object(
                self.module,
                "_p300_group_members",
                return_value=[foreign],
            ),
            mock.patch.object(
                self.module,
                "_proc_has_owner",
                return_value=False,
            ),
            mock.patch.object(self.module.os, "kill") as kill,
            mock.patch.object(self.module.os, "killpg") as killpg,
        ):
            with self.assertRaisesRegex(
                self.module.F1LiveError, "foreign member"
            ):
                self.module._p300_cleanup_owned_processes(
                    {}, expected_group=900
                )

        kill.assert_not_called()
        killpg.assert_not_called()


if __name__ == "__main__":
    unittest.main()
