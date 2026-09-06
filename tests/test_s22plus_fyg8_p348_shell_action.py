"""Focused H0 tests for P348 command binding and session outcome semantics."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import hashlib
import hmac
import os
import signal
import stat
import struct
import threading
import sys
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workspace/public/src/scripts/revalidation"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

import s22plus_fyg8_p348_shell_action as action  # noqa: E402
import s22plus_fyg8_p348_shell_session as session  # noqa: E402
import device_action_f1_live_v2 as live  # noqa: E402
from test_s22plus_fyg8_p348_live import P348ReceiptFixture  # noqa: E402
from test_s22plus_fyg8_p345_live_receipt import BOOT_ID, KEY, KEY_SHA256  # noqa: E402


class P348ShellActionTests(unittest.TestCase):
    def prepared(self, root: Path) -> SimpleNamespace:
        run_dir = root / "run"
        run_dir.mkdir()
        return SimpleNamespace(root=root, run_dir=run_dir)

    def test_command_file_is_read_once_and_stays_under_private(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            private = root / "workspace" / "private"
            private.mkdir(parents=True)
            prepared = self.prepared(root)
            path = private / "command.txt"
            path.write_bytes(b"cat /proc/version\n")
            path.chmod(0o600)
            command, identity = action.read_command_file(prepared, path)
            self.assertEqual(command, b"cat /proc/version\n")
            self.assertEqual(identity, session.identity(command))
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

            outside = root / "outside.txt"
            outside.write_bytes(b"id")
            outside.chmod(0o600)
            with self.assertRaises(action.ActionError):
                action.read_command_file(prepared, outside)

    def test_command_file_rejects_controls_and_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            private = root / "workspace" / "private"
            private.mkdir(parents=True)
            prepared = self.prepared(root)
            for payload in (b"echo\x00bad", b"x" * (session.MAX_COMMAND_BYTES + 1)):
                path = private / "command.txt"
                path.write_bytes(payload)
                path.chmod(0o600)
                with self.assertRaises(action.ActionError):
                    action.read_command_file(prepared, path)

    @staticmethod
    def fake_binding() -> dict:
        return {
            "target": dict(session.TARGET),
            "per_boot_id": hashlib.sha256(b"c" * 32).hexdigest(),
            "shell": {"run_id": "a" * 32},
        }

    def fake_variant(self, command: bytes, outcome: str) -> SimpleNamespace:
        runtime = SimpleNamespace(
            DEFAULT_COMMANDS=(b"/bin/busybox id", command, b"nonce"),
            P348_RUN_ID_HEX="a" * 32,
            FLAG_CANCELLED=8,
        )
        observer = SimpleNamespace(
            LATER_ACCEPTANCE_COMMANDS={
                "known-nonzero": {"command": command, "outcome": outcome},
            }
        )
        return SimpleNamespace(runtime=runtime, observer=observer)

    def fake_shell_result(self, command: bytes, *, middle_flags: int, middle_exit: int, outcome: str) -> SimpleNamespace:
        runtime = SimpleNamespace(
            DEFAULT_COMMANDS=(b"/bin/busybox id", b"/bin/busybox echo P348", b"nonce"),
            P348_RUN_ID_HEX="a" * 32,
            FLAG_CANCELLED=8,
        )
        commands = (
            SimpleNamespace(sequence=3, command=runtime.DEFAULT_COMMANDS[0], output=b"uid=0 gid=0\n", flags=0, exit_code=0, term_signal=0, duration_ms=1),
            SimpleNamespace(sequence=4, command=command, output=b"", flags=middle_flags, exit_code=middle_exit, term_signal=9 if middle_flags & 1 else 0, duration_ms=30),
            SimpleNamespace(sequence=5, command=runtime.DEFAULT_COMMANDS[2], output=b"P328-NONCE " + b"a" * 32 + b"\n", flags=0, exit_code=0, term_signal=0, duration_ms=1),
        )
        audit = SimpleNamespace(
            banner_seen=True,
            challenge_seen=True,
            ready_seen=True,
            authenticated=True,
            done_seen=True,
            boot_id=b"c" * 32,
            nonce=b"d" * 32,
        )
        return SimpleNamespace(
            session=SimpleNamespace(commands=commands, audit=audit),
            outcome=outcome,
            cancel_sent=False,
            cancel_ack=None,
        )

    def test_command_failed_is_continuable_but_126_127_is_stop(self) -> None:
        command = b"exit 7"
        binding = self.fake_binding()
        intent = {"ordinal": 1, "action": action.ACTION_NAME}
        variant = self.fake_variant(command, "command-failed")
        result = self.fake_shell_result(command, middle_flags=0, middle_exit=7, outcome="command-failed")
        value = action._session_receipt(
            SimpleNamespace(F1LiveError=RuntimeError),
            variant,
            command,
            binding,
            intent,
            result,
            {"size": 1, "sha256": "1" * 64},
            {"size": 1, "sha256": "2" * 64},
            SimpleNamespace(receipt_path=Path("capture.json"), stdout={}, stderr={}),
        )
        self.assertTrue(value["session_complete"])
        self.assertEqual(value["command_outcome"], "command-failed")
        self.assertTrue(value["continuation_allowed"])
        self.assertEqual(value["acceptance_role"], "known-nonzero")

        stop_command = b"/bin/missing"
        stop_variant = self.fake_variant(stop_command, "exec-failed")
        stop_result = self.fake_shell_result(stop_command, middle_flags=4, middle_exit=126, outcome="exec-failed")
        stopped = action._session_receipt(
            SimpleNamespace(F1LiveError=RuntimeError),
            stop_variant,
            stop_command,
            binding,
            intent,
            stop_result,
            {"size": 1, "sha256": "1" * 64},
            {"size": 1, "sha256": "2" * 64},
            SimpleNamespace(receipt_path=Path("capture.json"), stdout={}, stderr={}),
        )
        self.assertFalse(stopped["continuation_allowed"])
        self.assertEqual(stopped["command_outcome"], "exec-failed")
        combined = self.fake_shell_result(stop_command, middle_flags=6, middle_exit=126, outcome="truncated")
        combined_value = action._session_receipt(
            SimpleNamespace(F1LiveError=RuntimeError),
            stop_variant,
            stop_command,
            binding,
            intent,
            combined,
            {"size": 1, "sha256": "1" * 64},
            {"size": 1, "sha256": "2" * 64},
            SimpleNamespace(receipt_path=Path("capture.json"), stdout={}, stderr={}),
        )
        self.assertEqual(combined_value["command_outcome"], "exec-failed")
        self.assertFalse(combined_value["continuation_allowed"])

    def test_suspend_aware_exchange_clock_raises_before_later_frame(self) -> None:
        lease = SimpleNamespace(_check_clock=mock.Mock())
        clock = action._SuspendAwareClock(lease)
        with mock.patch.object(action.session, "clock_now_ns", return_value=5):
            self.assertIsInstance(clock.monotonic(), float)
        lease._check_clock.side_effect = RuntimeError("suspend")
        with mock.patch.object(action.session, "clock_now_ns", return_value=6):
            with self.assertRaisesRegex(RuntimeError, "suspend"):
                clock.monotonic()

    def test_suspend_after_codec_select_blocks_the_actual_write(self) -> None:
        variant = live.typed_evidence.SHELL_VARIANTS["p348"]
        observer = live._open_header_initial_observer_module(
            variant.runtime, variant.observer, "p348-write-suspend-test"
        )
        codec = observer._CODEC
        read_fd, write_fd = os.pipe()
        writes = []

        class Lease:
            def __init__(self) -> None:
                self.calls = 0

            def _check_clock(self, _now: int) -> None:
                self.calls += 1
                if self.calls >= 2:
                    raise RuntimeError("suspend after select")

        lease = Lease()
        original_codec_os = codec.os
        original_codec_time = codec.time
        original_select = codec.select.select
        base_os = codec.os

        class CountingOS:
            def write(self, descriptor: int, payload: bytes) -> int:
                writes.append(bytes(payload))
                return base_os.write(descriptor, payload)

            def __getattr__(self, name: str):
                return getattr(base_os, name)

        try:
            codec.os = action._SuspendAwareOS(CountingOS(), lease)
            codec.time = action._SuspendAwareClock(lease)
            codec.select.select = lambda *_args: ([], [write_fd], [])
            with self.assertRaisesRegex(RuntimeError, "suspend after select"):
                codec._write_all(write_fd, b"guarded", time.monotonic() + 1, SimpleNamespace(tx=bytearray()))
            self.assertEqual(writes, [])
        finally:
            codec.os = original_codec_os
            codec.time = original_codec_time
            codec.select.select = original_select
            os.close(read_fd)
            os.close(write_fd)

    def test_no_suspend_deadline_crossing_blocks_codec_write(self) -> None:
        variant = live.typed_evidence.SHELL_VARIANTS["p348"]
        observer = live._open_header_initial_observer_module(
            variant.runtime, variant.observer, "p348-deadline-test"
        )
        codec = observer._CODEC
        read_fd, write_fd = os.pipe()
        writes = []

        class Lease:
            def _check_clock(self, _now: int) -> None:
                pass

        lease = Lease()
        original_codec_os = codec.os
        original_codec_time = codec.time
        original_select = codec.select.select
        base_os = codec.os

        class CountingOS:
            def write(self, descriptor: int, payload: bytes) -> int:
                writes.append(bytes(payload))
                return base_os.write(descriptor, payload)

            def __getattr__(self, name: str):
                return getattr(base_os, name)

        try:
            deadline = 1.0
            codec.os = action._SuspendAwareOS(
                CountingOS(), lease, deadline=deadline
            )
            codec.time = action._SuspendAwareClock(lease, deadline=deadline)
            codec.select.select = lambda *_args: ([], [write_fd], [])
            with mock.patch.object(action.time, "monotonic", side_effect=[0.5, 1.5]):
                with self.assertRaisesRegex(
                    TimeoutError, "logical session deadline expired"
                ):
                    codec._write_all(
                        write_fd,
                        b"deadline-guarded",
                        deadline,
                        SimpleNamespace(tx=bytearray()),
                    )
            self.assertEqual(writes, [])
        finally:
            codec.os = original_codec_os
            codec.time = original_codec_time
            codec.select.select = original_select
            os.close(read_fd)
            os.close(write_fd)

    def test_real_run_locked_receipt_replay_and_prior_evidence_gate(self) -> None:
        """Exercise one actual P348 producer/consumer exchange over a PTY."""

        with tempfile.TemporaryDirectory() as temporary:
            fixture = P348ReceiptFixture(Path(temporary) / "run")
            prepared = fixture.prepared
            prepared.bundle.manifest["rollback_ap"] = {"sha256": "d" * 64}
            variant = live.typed_evidence.SHELL_VARIANTS["p348"]
            original_auth_identity = variant.auth_key
            variant.auth_key = {"size": 32, "sha256": KEY_SHA256}
            self.addCleanup(setattr, variant, "auth_key", original_auth_identity)
            durable = {
                "accepted": True,
                "download_endpoint_absent": True,
                "candidate_topology_sha256": hashlib.sha256(
                    live.p324_typec_lane.CANDIDATE_TOPOLOGY.encode()
                ).hexdigest(),
                session.PROOF_KEY: fixture.proof,
            }
            with mock.patch.object(live, "_p348_bundle", return_value=True), mock.patch.object(
                live, "_p348_proof_ok", return_value=True
            ):
                binding_value = session.binding_for(live, prepared, durable)
            lease_root = prepared.run_dir / session.DIRECTORY
            lease_root.mkdir(mode=0o700)
            session.ShellLease.publish(
                lease_root,
                binding_value,
                {"state": "OBSERVED", "candidate_boot_ready": True, "journal_sha256": "a" * 64},
                duration_seconds=120,
                lease_id="1" * 32,
            )

            codec = live._open_header_initial_observer_module(
                variant.runtime, variant.observer, "p348-real-action-server"
            )
            command = b"printf 'P348-REAL-ACTION\\n'"
            nonce = b"\x09" * codec.runtime.NONCE_SIZE
            identity_value = {"fixture": "p348-real-action"}
            endpoint_holder = {}
            master, slave = os.openpty()
            slave_name = os.ttyname(slave)
            slave_stat = os.fstat(slave)
            endpoint = SimpleNamespace(
                tty_name=slave_name.removeprefix("/dev/"),
                major=os.major(slave_stat.st_rdev),
                minor=os.minor(slave_stat.st_rdev),
                tty_class=Path("/sys/class/tty") / Path(slave_name).name,
                identity_sha256="e" * 64,
                topology=live.p324_typec_lane.CANDIDATE_TOPOLOGY,
            )
            endpoint_holder["endpoint"] = endpoint
            server_errors = []
            exec_count = []

            def read_exact(size: int) -> bytes:
                payload = bytearray()
                while len(payload) < size:
                    chunk = os.read(master, size - len(payload))
                    if not chunk:
                        raise EOFError("PTY peer closed")
                    payload.extend(chunk)
                return bytes(payload)

            def receive() -> object:
                header = read_exact(codec.HEADER.size)
                length = codec.HEADER.unpack(header)[3]
                return codec.decode_frame(header + read_exact(length))

            def send(frame_type: int, sequence: int, payload: bytes) -> None:
                data = codec.encode_frame(frame_type, sequence, payload)
                offset = 0
                while offset < len(data):
                    offset += os.write(master, data[offset:])

            def serve() -> None:
                try:
                    opened = receive()
                    assert opened.frame_type == codec.runtime.FRAME_OPEN
                    assert opened.payload == codec.runtime.P335_RUN_ID
                    os.write(master, codec.runtime.DEVICE_BANNER)
                    for stage in (
                        codec.runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER,
                        codec.runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
                        codec.runtime.DIAGNOSTIC_STAGE_RNG,
                    ):
                        send(codec.runtime.DIAGNOSTIC_FRAME_TYPE, 0, codec.DIAGNOSTIC.pack(stage, 0))
                    send(codec.runtime.FRAME_CHALLENGE, 0, nonce)
                    auth = receive()
                    assert auth.payload == codec.compute_open_tag(KEY, codec.runtime.P335_RUN_ID, nonce)
                    send(codec.runtime.FRAME_READY, 1, codec.compute_ready_tag(KEY, codec.runtime.P335_RUN_ID, nonce))
                    send(
                        codec.runtime.FRAME_BOOT_ID,
                        codec.runtime.P335_BOOT_ID_SEQUENCE,
                        BOOT_ID + codec.compute_boot_id_tag(KEY, codec.runtime.P335_RUN_ID, nonce, BOOT_ID),
                    )
                    outputs = (
                        b"uid=0 gid=0\n",
                        b"P348-REAL-ACTION\n",
                        b"P328-NONCE " + codec.runtime.P348_RUN_ID_HEX.encode("ascii") + b"\n",
                    )
                    for sequence, output in zip((3, 4, 5), outputs):
                        frame = receive()
                        assert frame.frame_type == codec.runtime.FRAME_EXEC
                        exec_count.append(sequence)
                        expected_command = (
                            codec.runtime.DEFAULT_COMMANDS[0]
                            if sequence == 3
                            else command
                            if sequence == 4
                            else codec.runtime.DEFAULT_COMMANDS[2]
                        )
                        assert frame.payload[codec.runtime.AUTH_TAG_SIZE:] == expected_command
                        tag = hmac.new(
                            KEY,
                            codec.runtime.AUTH_DOMAIN_EXEC
                            + codec.runtime.P335_RUN_ID
                            + nonce
                            + struct.pack("<I", sequence)
                            + expected_command,
                            hashlib.sha256,
                        ).digest()
                        assert frame.payload[: codec.runtime.AUTH_TAG_SIZE] == tag
                        send(codec.runtime.FRAME_DATA, sequence, output)
                        send(codec.runtime.FRAME_EXIT, sequence, codec.EXIT.pack(0, 0, 0, len(output), 1))
                    closed = receive()
                    assert closed.frame_type == codec.runtime.FRAME_CLOSE
                    send(codec.runtime.FRAME_DONE, 6, codec.DONE.pack(3))
                except BaseException as exc:  # surfaced below without hiding raw evidence
                    server_errors.append(exc)

            thread = threading.Thread(target=serve)
            thread.start()
            state = {
                "candidate_completed": True,
                "candidate_classification": "odin_transfer_completed",
                "p348_shell_session_active": True,
                "p348_shell_rollback_required": False,
                "rollback_completed": False,
                "candidate_observer_guard_release_status": "released",
                "candidate_observer_guard_released": True,
                "candidate_observer_guard_warning": None,
                "candidate_observer_guard_release_receipt_sha256": "r" * 64,
            }
            journal = SimpleNamespace(state=lambda: "OBSERVED")
            journal_type = mock.patch.object(live.core.Journal, "reopen", return_value=journal)
            state_patch = mock.patch.object(live, "_state", return_value=state)
            durable_patch = mock.patch.object(live, "_reopen_candidate_observation", return_value=durable)
            bundle_patch = mock.patch.object(live, "_p348_bundle", return_value=True)
            proof_patch = mock.patch.object(live, "_p348_proof_ok", return_value=True)
            key_patch = mock.patch.object(live, "_p328_read_auth_key", return_value=(KEY, KEY_SHA256))
            lane_patch = mock.patch.object(live, "_p324_typec_lane_value")
            guard_patch = mock.patch.object(
                live,
                "_reopen_candidate_guard_release",
                return_value={"status": "released", "released": True, "warning": None, "receipt_sha256": "r" * 64},
            )
            select_patch = mock.patch.object(action, "_select_endpoint", return_value=(endpoint, identity_value))
            udev_patch = mock.patch.object(action, "_udev_ok")
            resolve_patch = mock.patch.object(live.cdc_acm_observer, "_resolve_endpoint", return_value=(identity_value, endpoint))
            with journal_type, state_patch, durable_patch, bundle_patch, proof_patch, key_patch, lane_patch, guard_patch, select_patch, udev_patch, resolve_patch:
                try:
                    value = action._run_locked(
                        live,
                        prepared,
                        command,
                        session.identity(command),
                        cancel_requested=lambda: False,
                    )
                finally:
                    os.close(slave)
                    thread.join(3)
                    os.close(master)
            self.assertEqual(server_errors, [])
            self.assertEqual(exec_count, [3, 4, 5])
            self.assertEqual(value["command_outcome"], "ok")
            action_dir = prepared.run_dir / action.EVIDENCE_DIRECTORY / "action-01"
            self.assertTrue((action_dir / "result.json").exists())
            self.assertTrue((action_dir / "session-rx.capture.json").exists())
            self.assertEqual(session.ShellLease.open(prepared.run_dir / session.DIRECTORY).snapshot()["actions_completed"], 1)

            # The close consumer reparses the actual retained frames and is
            # stable even though it does not consult the current host clock.
            with mock.patch.object(live, "_reopen_candidate_observation", return_value=durable), mock.patch.object(
                live, "_p328_read_auth_key", return_value=(KEY, KEY_SHA256)
            ), mock.patch.object(live, "_p348_bundle", return_value=True), mock.patch.object(
                live, "_p348_proof_ok", return_value=True
            ):
                summary = session.action_summary(live, prepared)
            self.assertTrue(summary["integrity_proved"])
            self.assertFalse(summary["proved"])

            # Removing the prior receipt blocks _current_context before any
            # endpoint selection or new intent/EXEC can occur.
            (action_dir / "result.json").unlink()
            selected = mock.Mock(side_effect=AssertionError("endpoint selected after prior receipt loss"))
            with mock.patch.object(action, "_select_endpoint", selected), journal_type, state_patch, durable_patch, bundle_patch, proof_patch, key_patch, lane_patch, guard_patch:
                with self.assertRaises(live.F1LiveError):
                    action._current_context(live, prepared)
            selected.assert_not_called()

    def test_sigint_owner_requests_cancel_without_terminating_context(self) -> None:
        called = []
        previous = signal.getsignal(signal.SIGINT)
        with action._cancel_owner(lambda: called.append(True) or False) as requested:
            self.assertFalse(requested())
            self.assertTrue(called)
            signal.raise_signal(signal.SIGINT)
            self.assertTrue(requested())
        self.assertIs(signal.getsignal(signal.SIGINT), previous)
        self.assertIsNotNone(requested)


if __name__ == "__main__":
    unittest.main()
