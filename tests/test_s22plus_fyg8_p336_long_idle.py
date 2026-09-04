from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p327_framed_exec_runtime as p327  # noqa: E402
import s22plus_fyg8_p330_auth_exec_runtime as p330  # noqa: E402
import s22plus_fyg8_p332_logical_resident_exec_runtime as p332  # noqa: E402
import s22plus_fyg8_p333_open_entry_diag_runtime as p333  # noqa: E402
import s22plus_fyg8_p334_first_read_rc_runtime as p334  # noqa: E402
import s22plus_fyg8_p335_retained_listener_runtime as p335  # noqa: E402
import s22plus_fyg8_p336_long_idle_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p336_long_idle_action as action  # noqa: E402
import s22plus_fyg8_p336_long_idle_runtime as runtime  # noqa: E402


TEST_KEY = bytes(range(runtime.AUTH_KEY_SIZE))
BOOT_ID = b"B" * runtime.P335_BOOT_ID_SIZE
NONCE = b"N" * runtime.NONCE_SIZE


def p335_source() -> bytes:
    base = (
        p327.P327_HELPER
        + p327.PUBLISHER
        + p327.P327_ENTRY
        + p334.P333_DETAIL_ANCHOR
    )
    value = p330.transform_runtime_include(base, TEST_KEY)
    value = p332.transform_runtime_include(value, TEST_KEY)
    value = p333.transform_runtime_include(value, TEST_KEY)
    value = p334.transform_runtime_include(value, TEST_KEY)
    return p335.transform_runtime_include(value, TEST_KEY)


class P336Server:
    def __init__(self, peer: socket.socket, preamble_count: int, *, mode: str | None = None):
        self.peer = peer
        self.preamble_count = preamble_count
        self.mode = mode
        self.errors: list[BaseException] = []
        self.host_frames: list[observer.Frame] = []

    @staticmethod
    def _receive_exact(peer: socket.socket, size: int) -> bytes:
        value = bytearray()
        while len(value) < size:
            chunk = peer.recv(size - len(value))
            if not chunk:
                raise RuntimeError("peer EOF")
            value.extend(chunk)
        return bytes(value)

    def _receive_frame(self) -> observer.Frame:
        header = self._receive_exact(self.peer, observer.HEADER.size)
        length = observer.HEADER.unpack(header)[3]
        return observer.decode_frame(
            header + self._receive_exact(self.peer, length)
        )

    def _send(self, frame_type: int, sequence: int, payload: bytes) -> None:
        self.peer.sendall(observer.encode_frame(frame_type, sequence, payload))

    def _diagnostic(self, stage: int) -> None:
        self._send(
            runtime.DIAGNOSTIC_FRAME_TYPE,
            0,
            observer.DIAGNOSTIC.pack(stage, 0),
        )

    def _preamble(self) -> bytes:
        pair = runtime.DEVICE_BANNER + observer.encode_frame(
            runtime.DIAGNOSTIC_FRAME_TYPE,
            0,
            observer.DIAGNOSTIC.pack(runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER, 0),
        )
        return pair * self.preamble_count

    def run(self) -> None:
        try:
            if self.mode == "truncated":
                self.peer.sendall(runtime.DEVICE_BANNER[:3])
                return
            if self.mode == "foreign":
                self.peer.sendall(b"NO!")
                return
            if self.mode == "oversized-frame":
                header = struct.pack(
                    "<4sBBHII",
                    runtime.FRAME_MAGIC,
                    runtime.FRAME_VERSION,
                    runtime.FRAME_OPEN,
                    runtime.MAX_FRAME_PAYLOAD + 1,
                    0,
                    0,
                )
                self.peer.sendall(header)
                return
            self.peer.sendall(self._preamble())
            opened = self._receive_frame()
            self.host_frames.append(opened)
            if opened != observer.Frame(runtime.FRAME_OPEN, 0, runtime.P336_RUN_ID):
                raise AssertionError(f"OPEN differs: {opened!r}")
            if self.preamble_count > observer.MAX_PREAMBLE_PAIRS:
                return
            self._diagnostic(runtime.DIAGNOSTIC_STAGE_OPEN_PARSED)
            self._diagnostic(runtime.DIAGNOSTIC_STAGE_RNG)
            self._send(runtime.FRAME_CHALLENGE, 0, NONCE)
            auth = self._receive_frame()
            self.host_frames.append(auth)
            if auth.payload != observer.compute_open_tag(TEST_KEY, runtime.P336_RUN_ID, NONCE):
                raise AssertionError("AUTH differs")
            self._send(
                runtime.FRAME_READY,
                1,
                observer.compute_ready_tag(TEST_KEY, runtime.P336_RUN_ID, NONCE),
            )
            boot_tag = observer.compute_boot_id_tag(
                TEST_KEY, runtime.P336_RUN_ID, NONCE, BOOT_ID
            )
            self._send(
                runtime.FRAME_BOOT_ID,
                runtime.P335_BOOT_ID_SEQUENCE,
                BOOT_ID + boot_tag,
            )
            for sequence, command in enumerate(runtime.DEFAULT_COMMANDS, start=3):
                request = self._receive_frame()
                self.host_frames.append(request)
                if (
                    request.frame_type != runtime.FRAME_EXEC
                    or request.sequence != sequence
                    or request.payload[observer.AUTH_TAG_SIZE :] != command
                    or request.payload[: observer.AUTH_TAG_SIZE]
                    != observer.compute_exec_tag(
                        TEST_KEY, runtime.P336_RUN_ID, NONCE, sequence, command
                    )
                ):
                    raise AssertionError("EXEC differs")
                output = (
                    b"uid=0(root) gid=0(root)\n"
                    if sequence == 3
                    else b"Linux p336 5.10 aarch64 GNU/Linux\n"
                    if sequence == 4
                    else f"P328-NONCE {runtime.P336_RUN_ID_HEX}\n".encode()
                )
                self._send(runtime.FRAME_DATA, sequence, output)
                self._send(
                    runtime.FRAME_EXIT,
                    sequence,
                    observer.EXIT.pack(0, 0, 0, len(output), 1),
                )
            closed = self._receive_frame()
            self.host_frames.append(closed)
            if closed.frame_type != runtime.FRAME_CLOSE or closed.sequence != 6:
                raise AssertionError("CLOSE differs")
            self._send(runtime.FRAME_DONE, 6, observer.DONE.pack(3))
            if self.mode == "trailing":
                self.peer.sendall(b"X")
        except (ConnectionResetError, BrokenPipeError):
            if self.mode not in {"foreign", "truncated", "oversized-frame"}:
                self.errors.append(RuntimeError("unexpected peer close"))
        except BaseException as exc:  # surfaced by the test after join
            self.errors.append(exc)


class FakeLease:
    def __init__(self):
        self.actions: list[tuple[dict[str, object], dict[str, object] | None]] = []
        self.binding = {}
        self.results: list[str] = []

    def snapshot(self):
        return {
            "state": "ACTIVE",
            "rollback_required": False,
            "actions_started": len(self.actions),
            "actions_completed": sum(result is not None for _, result in self.actions),
            "actions_remaining": 16 - len(self.actions),
        }

    def begin_action(self, name, _binding):
        intent = {"action": name, "ordinal": len(self.actions) + 1}
        self.actions.append((intent, None))
        return intent

    def record_action_result(self, intent, result, _binding):
        self.results.append(result["status"])
        self.actions[-1] = (intent, dict(result))


class P336LongIdleTests(unittest.TestCase):
    def test_binding_is_canonical_pending_and_audit_is_host_only(self):
        binding = action.ACTIVATION.read_bytes()
        value = json.loads(binding)
        self.assertEqual(binding, action.canonical(value))
        checked = action.validate_activation(require_pass=False)
        self.assertEqual(checked["value"], value)
        self.assertEqual(
            value["independent_review"],
            {"status": "review-pending", "verdict": None},
        )
        result = action.audit()
        self.assertFalse(result["device_contact"])
        self.assertFalse(result["live_authorized"])

    def _success(self, preamble_count: int) -> observer.LongIdleResult:
        host, peer = socket.socketpair()
        host.setblocking(False)
        server = P336Server(peer, preamble_count)
        thread = threading.Thread(target=server.run)
        thread.start()
        try:
            result = observer.exchange_late_action(
                host,
                TEST_KEY,
                expected_boot_id=BOOT_ID,
                timeout_sec=3,
            )
            self.assertTrue(result.complete)
            self.assertEqual(result.session.preamble_count, preamble_count)
            self.assertEqual(
                [frame.frame_type for frame in server.host_frames],
                [runtime.FRAME_OPEN, runtime.FRAME_AUTH,
                 runtime.FRAME_EXEC, runtime.FRAME_EXEC, runtime.FRAME_EXEC,
                 runtime.FRAME_CLOSE],
            )
            self.assertFalse(server.errors)
            return result
        finally:
            host.close()
            thread.join(timeout=3)
            peer.close()
        self.assertFalse(thread.is_alive())
        self.assertFalse(server.errors)

    def test_zero_one_many_buffered_preambles_and_immediate_clean_stream(self):
        for count in (0, 1, 4):
            with self.subTest(count=count):
                result = self._success(count)
                self.assertEqual(result.session.audit.current_stage, "complete")
                self.assertTrue(result.session.audit.resync_open_before_read)
                self.assertTrue(result.session.audit.resync_open_parsed_seen)

    def test_open_is_first_and_only_open_before_backlog_consumption(self):
        result = self._success(2)
        tx_frames = self._tx_frames(result.session.raw_tx)
        self.assertEqual(
            [frame.frame_type for frame in tx_frames],
            [runtime.FRAME_OPEN, runtime.FRAME_AUTH,
             runtime.FRAME_EXEC, runtime.FRAME_EXEC, runtime.FRAME_EXEC,
             runtime.FRAME_CLOSE],
        )
        self.assertLess(
            tx_frames[0].frame_type,
            tx_frames[1].frame_type,
        )

    @staticmethod
    def _tx_frames(payload: bytes) -> list[observer.Frame]:
        result: list[observer.Frame] = []
        offset = 0
        while offset < len(payload):
            header = payload[offset : offset + observer.HEADER.size]
            if len(header) != observer.HEADER.size:
                raise AssertionError("truncated TX fixture")
            length = observer.HEADER.unpack(header)[3]
            end = offset + observer.HEADER.size + length
            if end > len(payload):
                raise AssertionError("truncated TX frame fixture")
            result.append(observer.decode_frame(payload[offset:end]))
            offset = end
        return result

    def _failure(self, mode: str, preamble_count: int = 0) -> observer.LongIdleObserverError:
        host, peer = socket.socketpair()
        host.setblocking(False)
        server = P336Server(peer, preamble_count, mode=mode)
        thread = threading.Thread(target=server.run)
        thread.start()
        try:
            with self.assertRaises(observer.LongIdleObserverError) as raised:
                observer.exchange_late_action(
                    host,
                    TEST_KEY,
                    expected_boot_id=BOOT_ID,
                    timeout_sec=2,
                )
            failure = raised.exception
            frames = self._tx_frames(failure.raw_tx)
            self.assertEqual([frame.frame_type for frame in frames], [runtime.FRAME_OPEN])
            self.assertIsNotNone(failure.audit)
            self.assertEqual(
                failure.audit.exception_sha256,
                failure.audit.nested_exception_sha256,
            )
            return failure
        finally:
            host.close()
            thread.join(timeout=3)
            peer.close()

    def test_truncated_foreign_and_oversized_frame_fail_before_auth_exec(self):
        for mode in ("truncated", "foreign", "oversized-frame"):
            with self.subTest(mode=mode):
                failure = self._failure(mode)
                self.assertTrue(failure.raw_rx)
                self.assertIsNotNone(failure.audit.failure_stage)

    def test_oversized_valid_backlog_is_bounded_and_raw_is_retained(self):
        failure = self._failure(
            "normal", preamble_count=observer.MAX_PREAMBLE_PAIRS + 1
        )
        self.assertGreaterEqual(failure.result.session.preamble_count, observer.MAX_PREAMBLE_PAIRS)
        self.assertLessEqual(len(failure.raw_rx), observer.MAX_RESYNC_BYTES)

    def test_raw_rx_preserves_exact_foreign_prefix(self):
        failure = self._failure("foreign")
        self.assertEqual(failure.raw_rx, b"NO!")

    def test_pre_read_bound_rejects_without_consuming_oversized_component(self):
        audit = observer.ExchangeAudit(
            auth_key_sha256=hashlib.sha256(TEST_KEY).hexdigest()
        )
        audit.rx.extend(b"R" * (observer.MAX_RESYNC_BYTES - 1))
        with mock.patch.object(observer._CODEC, "_read_exact") as read_exact:
            with self.assertRaises(observer.AuthObserverError):
                observer._read_bounded(17, 2, 10**12, audit, SimpleNamespace())
        read_exact.assert_not_called()

    def test_trailing_byte_failure_retains_completed_exchange_raw_audit(self):
        audit = observer.ExchangeAudit(
            auth_key_sha256=hashlib.sha256(TEST_KEY).hexdigest()
        )
        audit.tx.extend(observer.encode_frame(runtime.FRAME_OPEN, 0, runtime.P336_RUN_ID))
        audit.rx.extend(b"complete")
        audit.current_stage = "complete"
        audit.done_seen = True
        audit.authenticated = True
        session = observer.LongIdleSession(
            42, SimpleNamespace(commands=tuple(runtime.DEFAULT_COMMANDS)), audit,
            bytes(audit.tx), bytes(audit.rx), 0,
        )
        result = observer.LongIdleResult(session, "accepted")
        with (
            mock.patch.object(action, "os", wraps=action.os) as action_os,
            mock.patch.object(action.os, "open", return_value=42),
            mock.patch.object(action.os, "fstat", return_value=SimpleNamespace(st_rdev=os.stat("/dev/null").st_rdev)),
            mock.patch.object(action.os, "close") as closed,
            mock.patch.object(action.fcntl, "ioctl"),
            mock.patch.object(action.tty, "setraw"),
            mock.patch.object(action.cdc, "_resolve_endpoint", return_value=(
                {"kind": "fixture"},
                SimpleNamespace(identity_sha256="e" * 64),
            )),
            mock.patch.object(action.observer, "exchange_late_action", return_value=result),
            mock.patch.object(action.observer, "validate_late_result"),
            mock.patch.object(action.select, "select", return_value=([42], [], [])),
            mock.patch.object(action.os, "read", return_value=b"X"),
        ):
            endpoint = SimpleNamespace(
                tty_name="null", major=os.major(os.stat("/dev/null").st_rdev),
                minor=os.minor(os.stat("/dev/null").st_rdev),
                tty_class="fixture", identity_sha256="e" * 64,
            )
            with self.assertRaises(action.ActionError) as raised:
                action._exchange_full_tuple(
                    endpoint, {"kind": "fixture"}, TEST_KEY,
                    hashlib.sha256(BOOT_ID).hexdigest(), set(),
                )
        error = raised.exception
        self.assertIs(error.audit, audit)
        self.assertEqual(error.raw_rx, bytes(audit.rx))
        self.assertTrue(error.raw_rx.endswith(b"X"))
        self.assertTrue(error.raw_tx)
        closed.assert_called_once_with(42)

    def test_p336_context_dispatch_does_not_call_p335_context(self):
        prepared = SimpleNamespace(
            binding_sha256="a" * 64,
            bundle=SimpleNamespace(
                manifest={
                    "candidate_ap": {"sha256": "b" * 64},
                    "rollback_ap": {"sha256": "c" * 64},
                },
                receipt={
                    "observation_contract": {
                        "verification": {
                            "ap_payload_closure": {
                                "boot_image": {"sha256": "d" * 64}
                            }
                        }
                    }
                },
            ),
        )
        proof = {
            "run_id_hex": runtime.P336_RUN_ID_HEX,
            "session_count": observer.MAX_SESSIONS,
            "physical_reopen_count": observer.PHYSICAL_REOPEN_COUNT,
            "same_boot_id": True,
            "descriptor_reopened": True,
            "listener_replays_commands": False,
            "sessions": [
                {"challenge_nonce_sha256": f"{index + 1:064x}"}
                for index in range(observer.MAX_SESSIONS)
            ],
        }
        durable = {
            "accepted": True,
            "session_count": observer.MAX_SESSIONS,
            "successful_sessions": observer.MAX_SESSIONS,
            "physical_reopen_count": observer.PHYSICAL_REOPEN_COUNT,
            "reconnect_count": observer.MAX_RECONNECTS,
            "reconnect_cap": observer.MAX_RECONNECTS,
            "same_tty_fd": True,
            "fixed_p330_commands": True,
            "logical_resident_proof": True,
            "per_boot_identity_required": True,
            "p336_authenticated_attended_resident": proof,
            "candidate_topology_sha256": "e" * 64,
        }
        class Journal:
            def state(self):
                return "OBSERVED"

        lease = SimpleNamespace(binding={}, actions=[])
        state = {
            "candidate_classification": "odin_transfer_completed",
            "candidate_completed": True,
            "candidate_observer_accepted": True,
            "rollback_classification": None,
            "rollback_completed": False,
            "resident_session_active": True,
            "resident_rollback_required": False,
        }
        with (
            mock.patch.object(action._BOUND_ACTION, "_current_context", side_effect=AssertionError("P335 context used")),
            mock.patch.object(action.live, "load_prepared", return_value=prepared),
            mock.patch.object(action.live.core.Journal, "reopen", return_value=Journal()),
            mock.patch.object(action.live, "_state", return_value=state),
            mock.patch.object(action.live, "_reopen_candidate_observation", return_value=durable),
            mock.patch.object(action.live, "_p324_typec_lane_value"),
            mock.patch.object(action.live, "_p328_bound_auth_key_identity", return_value={"size": 32, "sha256": "f" * 64}),
            mock.patch.object(action.live, "_p328_read_auth_key", return_value=(TEST_KEY, "f" * 64)),
            mock.patch.object(action.resident.ResidentLease, "open", return_value=lease),
            mock.patch.object(
                action,
                "_p336_resident_binding",
                return_value={"p336": True, "key": {"sha256": "f" * 64}},
            ),
        ):
            lease.binding = {"p336": True, "key": {"sha256": "f" * 64}}
            # The helper must stop at a P336-specific validation path before
            # touching endpoint selection or sending any wire frame.
            value = action._p336_current_context()
        self.assertIs(value[0], prepared)
        self.assertIs(value[1], lease)
        self.assertEqual(value[2], {"p336": True, "key": {"sha256": "f" * 64}})
        self.assertEqual(value[3], TEST_KEY)
        self.assertEqual(len(value[4]), observer.MAX_SESSIONS)

    def test_runtime_fresh_identity_changes_only_fixed_command_marker(self):
        before = p335_source()
        after = runtime.transform_runtime_include(before, TEST_KEY)
        self.assertEqual(len(after), len(before))
        self.assertEqual(
            runtime.validate_transform(
                before, after, auth_key_sha256=runtime.auth_key_sha256(TEST_KEY)
            )["run_id_hex"],
            runtime.P336_RUN_ID_HEX,
        )
        self.assertIn(runtime._P336_COMMAND_MARKER, after)
        self.assertNotIn(runtime._P335_COMMAND_MARKER, after)
        self.assertTrue(runtime.audit_binding()["device_behavior_reused"])

    def test_lease_proxy_is_distinct_from_consumed_p335(self):
        self.assertNotEqual(action.resident.SCHEMA, p335.SCHEMA)
        self.assertEqual(action.resident.SCHEMA, action.P336_LEASE_SCHEMA)
        self.assertEqual(
            action.resident.validate_binding.__code__.co_consts[25],
            "magisk_boot_only",
        )
        self.assertIn(
            "s22plus-fyg8-p336-long-idle",
            action.resident.validate_binding.__code__.co_consts,
        )
        self.assertEqual(action.resident.MAX_ACTIONS, 16)

    def test_runner_failure_retains_raw_audit_and_marks_lease_uncertain(self):
        lease = FakeLease()
        audit = observer.ExchangeAudit(auth_key_sha256=hashlib.sha256(TEST_KEY).hexdigest())
        audit.tx.extend(observer.encode_frame(runtime.FRAME_OPEN, 0, runtime.P336_RUN_ID))
        audit.rx.extend(b"partial-backlog")
        audit.current_stage = "resync-stage0"
        audit.failure_stage = "resync-stage0"
        audit.exception_type = "AuthObserverError"
        audit.exception_sha256 = "a" * 64
        audit.nested_exception_sha256 = "a" * 64
        failure = observer.AuthObserverError(
            "fixture failure", audit=audit, stage="resync-stage0"
        )
        endpoint = SimpleNamespace(identity_sha256="e" * 64, tty_class=Path("/unused"))
        binding = {"per_boot_id": hashlib.sha256(BOOT_ID).hexdigest()}
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            evidence = base / "evidence"
            with (
                mock.patch.object(action, "ROOT", base),
                mock.patch.object(action, "EVIDENCE_DIR", evidence),
                mock.patch.object(action, "validate_activation", return_value={"receipt": {}}),
                mock.patch.object(
                    action,
                    "_current_context",
                    return_value=(SimpleNamespace(), lease, binding, TEST_KEY, set()),
                ),
                mock.patch.object(action, "_select_endpoint", return_value=(endpoint, {})),
                mock.patch.object(
                    action.cdc,
                    "_udev_properties",
                    return_value={
                        "ID_MM_DEVICE_IGNORE": "1",
                        "ID_MM_PORT_IGNORE": "1",
                        "ID_USB_INTERFACE_NUM": "00",
                    },
                ),
                mock.patch.object(action, "_exchange_full_tuple", side_effect=failure) as exchanged,
            ):
                with self.assertRaisesRegex(action.ActionError, "no replay"):
                    action.run_action("identity")
            action_dir = evidence / "action-01"
            self.assertEqual((action_dir / "failure.tx.bin").read_bytes(), bytes(audit.tx))
            self.assertEqual((action_dir / "failure.rx.bin").read_bytes(), bytes(audit.rx))
            value = json.loads((action_dir / "failure.json").read_text())
            self.assertEqual(value["failure_stage"], "resync-stage0")
            self.assertEqual(value["nested_exception_sha256"], "a" * 64)
            self.assertEqual(lease.results, ["uncertain"])
            exchanged.assert_called_once()
            with self.assertRaises(action.ActionError):
                action.run_action("identity")
            exchanged.assert_called_once()


if __name__ == "__main__":
    unittest.main()
