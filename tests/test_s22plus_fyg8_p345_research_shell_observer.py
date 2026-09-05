from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
from pathlib import Path
import sys
import struct
import time
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p345_research_shell_observer as observer  # noqa: E402
import s22plus_fyg8_p345_research_shell_runtime as runtime  # noqa: E402
import s22plus_fyg8_research_shell_exchange as exchange  # noqa: E402
import s22plus_fyg8_p328_auth_acm_observer as codec  # noqa: E402


@dataclass
class FakeAudit:
    nonce: bytes
    boot_id: bytes
    rx: bytearray
    tx: bytearray
    banner_seen: bool = True
    challenge_seen: bool = True
    ready_seen: bool = True
    authenticated: bool = True
    done_seen: bool = True
    current_stage: str = "complete"


def _command_result(
    sequence: int,
    command: bytes,
    output: bytes,
    *,
    flags: int = 0,
    exit_code: int = 0,
    term_signal: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        sequence=sequence,
        command=command,
        output=output,
        flags=flags,
        exit_code=exit_code,
        term_signal=term_signal,
        duration_ms=1,
    )


def _fake_shell_result(index: int, command: bytes) -> exchange.ShellExchange:
    if index == 1:
        middle_output = (
            b"P345-UID=65534\nP345-GID=65534\n"
            b"123.45 678.90\n"
            b"ash: can't create /probe: Read-only file system\n"
            + observer.PROBE_DENIED_MARKER
            + observer.PROBE_ABSENT_MARKER
            + observer.CANARY_MARKER
        )
        middle = _command_result(4, command, middle_output)
        outcome = "ok"
        cancel_sent = False
        cancel_ack = None
    elif index == 2:
        middle = _command_result(4, command, b"", exit_code=7)
        outcome = "command-failed"
        cancel_sent = False
        cancel_ack = None
    elif index == 3:
        middle = _command_result(4, command, b"", flags=1, exit_code=-1, term_signal=9)
        outcome = "timeout"
        cancel_sent = False
        cancel_ack = None
    elif index == 4:
        middle = _command_result(
            4,
            command,
            observer.CANCEL_MARKER,
            flags=runtime.P345_CANCELLED_FLAG,
            exit_code=-1,
            term_signal=9,
        )
        outcome = "cancelled"
        cancel_sent = True
        cancel_ack = runtime.P345_CANCEL_STATUS_CONSUMED
    else:
        middle = _command_result(4, command, observer.PIPELINE_MARKER)
        outcome = "ok"
        cancel_sent = False
        cancel_ack = None
    first = _command_result(
        3,
        runtime.DEFAULT_COMMANDS[0],
        b"uid=0(root) gid=0(root) groups=0(root)\n",
    )
    last = _command_result(
        5,
        runtime.DEFAULT_COMMANDS[2],
        b"P328-NONCE " + runtime.P345_RUN_ID_HEX.encode("ascii") + b"\n",
    )
    nonce = bytes([index]) * runtime.NONCE_SIZE
    audit = FakeAudit(nonce, b"b" * 32, bytearray(b"rx"), bytearray(b"tx"))
    session = SimpleNamespace(commands=(first, middle, last), audit=audit)
    return exchange.ShellExchange(session, outcome, cancel_sent, cancel_ack)


class FakeWriter:
    def __init__(self) -> None:
        self.stdout = bytearray()
        self.stderr = bytearray()

    def write_stdout(self, payload: bytes) -> None:
        self.stdout.extend(payload)

    def current_sizes(self) -> tuple[int, int]:
        return len(self.stdout), len(self.stderr)


class P345ResearchShellObserverTests(unittest.TestCase):
    def test_numeric_parent_identity_shared_with_post_session_validation(self):
        for output in (b"uid=0 gid=0\n", b"uid=0(root) gid=0(root) groups=0(root)\n"):
            result = _fake_shell_result(2, observer.EXIT7_COMMAND)
            result.session.commands[0].output = output
            self.assertTrue(exchange.parent_identity_valid(output))
            observer.validate_session_result(result, observer.QUALIFICATION_COMMANDS[1])
        for output in (b"uid=1 gid=0\n", b"uid=0 gid=1\n", b"uid=00 gid=0\n",
                       b"uid=0 gid=0", b"uid=0 gid=0evil\n", b"uid=0 gid=0\nuid=1 gid=1\n"):
            result = _fake_shell_result(2, observer.EXIT7_COMMAND)
            result.session.commands[0].output = output
            self.assertFalse(exchange.parent_identity_valid(output))
            with self.assertRaises(observer.QualificationError):
                observer.validate_session_result(result, observer.QUALIFICATION_COMMANDS[1])

    def test_numeric_canary_rejects_warning_join_and_conflicting_ids(self):
        good = _fake_shell_result(1, observer.CANARY_COMMAND).session.commands[1].output
        self.assertTrue(observer._canary_semantics(good)["gid_65534"])
        for bad in (good.replace(b"P345-GID=65534\n", b"P345-GID=65534id: can't get groups\n"),
                    good.replace(b"P345-UID=65534", b"P345-UID=0"),
                    good + b"P345-UID=0\n",
                    good.replace(b"P345-UID=65534\nP345-GID=65534\n",
                                 b"uid=65534 gid=65534id: can't get groups\n")):
            with self.assertRaises(observer.QualificationError):
                observer._canary_semantics(bad)
        self.assertIn(b"/bin/busybox id -u;", observer.CANARY_COMMAND)
        self.assertIn(b"/bin/busybox id -g;", observer.CANARY_COMMAND)

    def test_binding_has_exact_five_session_geometry_and_no_authority(self) -> None:
        value = observer.audit_binding()
        self.assertEqual(value["session_count"], 5)
        self.assertEqual(value["same_fd_session_count"], 5)
        self.assertEqual(value["reconnect_count"], 0)
        self.assertEqual(
            [item["name"] for item in value["commands"]],
            [step.name for step in observer.QUALIFICATION_COMMANDS],
        )
        self.assertTrue(value["same_descriptor"])
        self.assertTrue(value["no_endpoint_selection"])
        self.assertTrue(value["no_reconnect_or_retry"])
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])
        self.assertFalse(value["f1_ready"])

    def test_qualify_runs_same_descriptor_and_validates_all_semantics(self) -> None:
        writer = FakeWriter()
        seen_nonces: set[str] = set()
        calls: list[dict[str, object]] = []
        boot_sha = hashlib.sha256(b"b" * 32).hexdigest()

        def fake_exchange(
            selected_observer,
            descriptor,
            key,
            command,
            expected_boot,
            nonces,
            selected_writer,
            *,
            deadline,
            cancel_requested,
        ):
            del selected_observer, key, selected_writer, deadline, cancel_requested
            index = len(calls) + 1
            calls.append(
                {
                    "descriptor": descriptor,
                    "command": command,
                    "expected_boot": expected_boot,
                    "nonces": nonces,
                }
            )
            self.assertEqual(expected_boot, None if index == 1 else boot_sha)
            result = _fake_shell_result(index, command)
            nonces.add(hashlib.sha256(result.session.audit.nonce).hexdigest())
            return result

        with mock.patch.object(exchange, "exchange", side_effect=fake_exchange):
            receipt = observer.qualify(
                object(),
                23,
                b"k" * 32,
                None,
                seen_nonces,
                writer,
                deadline=time.monotonic() + 30,
            )

        self.assertTrue(receipt["proved"])
        self.assertEqual(receipt["session_count"], observer.SESSION_COUNT)
        self.assertFalse(receipt["authority_granted_by_observer"])
        self.assertNotIn("device_contact", receipt)
        self.assertEqual([call["descriptor"] for call in calls], [23] * 5)
        self.assertEqual(calls[0]["expected_boot"], None)
        self.assertTrue(all(call["expected_boot"] == boot_sha for call in calls[1:]))
        self.assertEqual(len(seen_nonces), 5)
        self.assertEqual(receipt["sessions"][0]["semantic"]["uid_65534"], True)
        self.assertEqual(receipt["sessions"][0]["semantic"]["probe_absent"], True)
        self.assertEqual(receipt["sessions"][3]["cancel_ack"], 0)
        self.assertTrue(
            receipt["sessions"][3]["commands"][1]["flags"]
            & runtime.P345_CANCELLED_FLAG
        )
        self.assertEqual(receipt["sessions"][4]["semantic"], {})
        self.assertEqual(observer.validate_qualification(receipt), dict(receipt))
        self.assertEqual(len(receipt.sessions), observer.SESSION_COUNT)

    def test_canary_requires_semantic_markers_even_when_exit_is_zero(self) -> None:
        writer = FakeWriter()
        seen_nonces: set[str] = set()

        def fake_exchange(*args, **kwargs):
            del kwargs
            result = _fake_shell_result(1, args[3])
            result.session.commands[1].output = b"uid=65534 gid=65534\n"
            return result

        with mock.patch.object(exchange, "exchange", side_effect=fake_exchange):
            with self.assertRaises(observer.QualificationError) as raised:
                observer.qualify(
                    object(),
                    23,
                    b"k" * 32,
                    None,
                    seen_nonces,
                    writer,
                    deadline=time.monotonic() + 30,
                )
        self.assertEqual(raised.exception.failed_session, "readonly-canary")
        self.assertEqual(raised.exception.category, "semantic")
        self.assertFalse(raised.exception.partial_receipt["proved"])
        self.assertEqual(raised.exception.partial_receipt["session_count"], 0)
        self.assertEqual(
            raised.exception.partial_receipt["failure"]["audit"]["rx"]["size"],
            2,
        )

    def test_failure_keeps_completed_rows_and_failed_exchange_audit(self) -> None:
        writer = FakeWriter()
        seen_nonces: set[str] = set()
        calls = 0

        def fake_exchange(*args, **kwargs):
            nonlocal calls
            del kwargs
            calls += 1
            if calls == 3:
                audit = FakeAudit(
                    bytes([3]) * runtime.NONCE_SIZE,
                    b"b" * 32,
                    bytearray(b"partial-rx"),
                    bytearray(b"partial-tx"),
                )
                error = RuntimeError("transport stopped")
                error.audit = audit
                raise error
            result = _fake_shell_result(calls, args[3])
            seen_nonces.add(hashlib.sha256(result.session.audit.nonce).hexdigest())
            return result

        with mock.patch.object(exchange, "exchange", side_effect=fake_exchange):
            with self.assertRaises(observer.QualificationError) as raised:
                observer.qualify(
                    object(),
                    23,
                    b"k" * 32,
                    None,
                    seen_nonces,
                    writer,
                    deadline=time.monotonic() + 30,
                )
        error = raised.exception
        self.assertEqual(error.failed_session, "command-timeout")
        self.assertEqual(error.category, "transport")
        self.assertEqual(len(error.sessions), 2)
        self.assertEqual(error.partial_receipt["session_count"], 2)
        self.assertEqual(error.partial_receipt["failure"]["session"], "command-timeout")
        self.assertEqual(
            error.partial_receipt["failure"]["audit"]["rx"]["size"],
            len(b"partial-rx"),
        )

    def test_receipt_validator_rejects_cancel_outside_sequence_four(self) -> None:
        writer = FakeWriter()
        seen_nonces: set[str] = set()

        with self.assertRaises(observer.QualificationError):
            observer.validate_qualification({"schema": observer.SCHEMA})

        # A complete receipt is easiest to obtain from a valid five-call fake;
        # then make the cancellation status inconsistent without touching raw data.
        calls = 0

        def all_exchange(*args, **kwargs):
            nonlocal calls
            del kwargs
            calls += 1
            result = _fake_shell_result(calls, args[3])
            seen_nonces.add(hashlib.sha256(result.session.audit.nonce).hexdigest())
            return result

        with mock.patch.object(exchange, "exchange", side_effect=all_exchange):
            receipt = observer.qualify(
                object(),
                23,
                b"k" * 32,
                None,
                seen_nonces,
                writer,
                deadline=time.monotonic() + 30,
            )
        receipt["sessions"][0]["cancel_sent"] = True
        with self.assertRaises(observer.QualificationError):
            observer.validate_qualification(receipt)

    def test_parse_captured_session_reuses_codec_and_rejects_trailing_bytes(self) -> None:
        key = b"k" * 32
        nonce = bytes(range(1, runtime.NONCE_SIZE + 1))
        boot_id = b"b" * 32
        command = observer.CANCEL_COMMAND
        run_id = runtime.P345_RUN_ID

        def hmac_value(domain: bytes, sequence: int | None = None, body: bytes = b"") -> bytes:
            message = bytearray(domain + run_id + nonce)
            if sequence is not None:
                message.extend(struct.pack("<I", sequence))
            message.extend(body)
            return hmac.new(key, bytes(message), hashlib.sha256).digest()

        def frame(frame_type: int, sequence: int, payload: bytes) -> bytes:
            return codec.encode_frame(frame_type, sequence, payload)

        canary_observer = SimpleNamespace(
            _CODEC=codec,
            _P333=SimpleNamespace(
                parse_diagnostic_frame=lambda value, stage: SimpleNamespace(
                    stage=stage, code=0
                )
            ),
            ExchangeAudit=codec.ExchangeAudit,
            CommandResult=codec.CommandResult,
            SessionResult=codec.SessionResult,
            decode_boot_id_frame=lambda value, auth_key, current_run, current_nonce: (
                value.payload[:32]
                if value.frame_type == runtime.FRAME_BOOT_ID
                and value.sequence == runtime.P335_BOOT_ID_SEQUENCE
                and auth_key == key
                and current_run == run_id
                and current_nonce == nonce
                and len(value.payload) == 64
                else (_ for _ in ()).throw(ValueError("boot frame differs"))
            ),
        )

        identity_output = b"uid=0(root) gid=0(root) groups=0(root)\n"
        nonce_output = b"P328-NONCE " + runtime.P345_RUN_ID_HEX.encode("ascii") + b"\n"
        cancel_output = observer.CANCEL_MARKER
        rx = bytearray(runtime.DEVICE_BANNER)
        for stage in (
            runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER,
            runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
            runtime.DIAGNOSTIC_STAGE_RNG,
        ):
            rx.extend(frame(runtime.DIAGNOSTIC_FRAME_TYPE, 0, struct.pack("<Ii", stage, 0)))
        rx.extend(frame(runtime.FRAME_CHALLENGE, 0, nonce))
        rx.extend(frame(runtime.FRAME_READY, 1, hmac_value(runtime.AUTH_DOMAIN_READY)))
        rx.extend(
            frame(
                runtime.FRAME_BOOT_ID,
                runtime.P335_BOOT_ID_SEQUENCE,
                boot_id + b"x" * runtime.AUTH_TAG_SIZE,
            )
        )
        rx.extend(frame(runtime.FRAME_DATA, 3, identity_output))
        rx.extend(frame(runtime.FRAME_EXIT, 3, codec.EXIT.pack(0, 0, 0, len(identity_output), 1)))
        rx.extend(frame(runtime.FRAME_DATA, 4, cancel_output))
        rx.extend(frame(runtime.FRAME_EXIT, 4, codec.EXIT.pack(8, -1, 9, len(cancel_output), 2)))
        rx.extend(frame(runtime.FRAME_CANCEL_ACK, 4, struct.pack("<I", 0)))
        rx.extend(frame(runtime.FRAME_DATA, 5, nonce_output))
        rx.extend(frame(runtime.FRAME_EXIT, 5, codec.EXIT.pack(0, 0, 0, len(nonce_output), 3)))
        rx.extend(frame(runtime.FRAME_DONE, 6, struct.pack("<I", 3)))

        tx = bytearray()
        tx.extend(frame(runtime.FRAME_OPEN, 0, run_id))
        tx.extend(frame(runtime.FRAME_AUTH, 1, hmac_value(runtime.AUTH_DOMAIN_OPEN)))
        tx.extend(
            frame(
                runtime.FRAME_EXEC,
                3,
                hmac_value(runtime.AUTH_DOMAIN_EXEC, 3, runtime.DEFAULT_COMMANDS[0])
                + runtime.DEFAULT_COMMANDS[0],
            )
        )
        tx.extend(
            frame(
                runtime.FRAME_EXEC,
                4,
                hmac_value(runtime.AUTH_DOMAIN_EXEC, 4, command) + command,
            )
        )
        tx.extend(frame(runtime.FRAME_CANCEL, 4, runtime.cancel_tag(key, run_id, nonce)))
        tx.extend(
            frame(
                runtime.FRAME_EXEC,
                5,
                hmac_value(runtime.AUTH_DOMAIN_EXEC, 5, runtime.DEFAULT_COMMANDS[2])
                + runtime.DEFAULT_COMMANDS[2],
            )
        )
        tx.extend(frame(runtime.FRAME_CLOSE, 6, hmac_value(runtime.AUTH_DOMAIN_CLOSE, 6)))

        parsed = observer.parse_captured_session(
            canary_observer, bytes(rx), bytes(tx), key
        )
        self.assertEqual(parsed.outcome, "cancelled")
        self.assertTrue(parsed.cancel_sent)
        self.assertEqual(parsed.cancel_ack, 0)
        checked = observer.validate_session_result(
            parsed, observer.QUALIFICATION_COMMANDS[3]
        )
        self.assertEqual(checked["outcome"], "cancelled")
        with self.assertRaises(observer.QualificationError):
            observer.parse_captured_session(canary_observer, bytes(rx) + b"x", bytes(tx), key)


if __name__ == "__main__":
    unittest.main()
