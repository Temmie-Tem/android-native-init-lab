"""Host-only P348 runtime and initial-observer checks."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p328_auth_acm_observer as codec  # noqa: E402
import s22plus_fyg8_p347_research_shell_runtime as p347_runtime  # noqa: E402
import s22plus_fyg8_p348_research_shell_observer as observer  # noqa: E402
import s22plus_fyg8_p348_research_shell_runtime as runtime  # noqa: E402
import s22plus_fyg8_research_shell_exchange as shell_exchange  # noqa: E402


KEY = b"k" * 32
BOOT_ID = b"b" * 32


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


def _command(
    sequence: int,
    command: bytes,
    output: bytes,
    *,
    flags: int = 0,
    exit_code: int = 0,
    term_signal: int = 0,
    duration_ms: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(
        sequence=sequence,
        command=command,
        output=output,
        flags=flags,
        exit_code=exit_code,
        term_signal=term_signal,
        duration_ms=duration_ms,
    )


def _fake_result(index: int, command: bytes) -> shell_exchange.ShellExchange:
    if index == 1:
        middle_output = (
            b"P345-UID=65534\nP345-GID=65534\n123.45 678.90\n"
            + observer.PROBE_DENIED_MARKER
            + observer.PROBE_ABSENT_MARKER
            + observer.CANARY_MARKER
        )
        middle = _command(4, command, middle_output)
        outcome, cancel_sent, cancel_ack = "ok", False, None
    elif index == 2:
        middle = _command(4, command, b"", exit_code=7)
        outcome, cancel_sent, cancel_ack = "command-failed", False, None
    elif index == 3:
        middle = _command(4, command, b"", flags=1, exit_code=-1, term_signal=9,
                           duration_ms=15000)
        outcome, cancel_sent, cancel_ack = "timeout", False, None
    elif index == 4:
        middle = _command(4, command, observer.CANCEL_MARKER,
                          flags=runtime.P345_CANCELLED_FLAG,
                          exit_code=-1, term_signal=9)
        outcome, cancel_sent, cancel_ack = "cancelled", True, 0
    elif index == 5:
        middle = _command(4, command, observer.PIPELINE_MARKER)
        outcome, cancel_sent, cancel_ack = "ok", False, None
    else:
        middle = _command(4, command, observer.REOPEN_WITNESS_MARKER)
        outcome, cancel_sent, cancel_ack = "ok", False, None
    audit = FakeAudit(
        nonce=bytes([index]) * runtime.NONCE_SIZE,
        boot_id=BOOT_ID,
        rx=bytearray(b"rx" + bytes([index])),
        tx=bytearray(b"tx" + bytes([index])),
    )
    first = _command(3, runtime.DEFAULT_COMMANDS[0],
                    b"uid=0(root) gid=0(root) groups=0(root)\n")
    last = _command(
        5,
        runtime.DEFAULT_COMMANDS[2],
        b"P328-NONCE " + runtime.P348_RUN_ID_HEX.encode("ascii") + b"\n",
    )
    session = SimpleNamespace(commands=(first, middle, last), audit=audit)
    return shell_exchange.ShellExchange(session, outcome, cancel_sent, cancel_ack)


class _Writer:
    def current_sizes(self) -> tuple[int, int]:
        return (0, 0)


class _Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def monotonic(self) -> float:
        return self.value


class P348RuntimeObserverTests(unittest.TestCase):
    def test_fresh_identity_and_exact_p347_child_filter_pipe(self) -> None:
        self.assertNotEqual(runtime.P348_RUN_ID_HEX, p347_runtime.P347_RUN_ID_HEX)
        self.assertEqual(
            runtime.DEVICE_BANNER,
            f"S22PLUS-FYG8-E3:{runtime.P348_RUN_ID_HEX}\n".encode("ascii"),
        )
        self.assertIn(runtime.P348_RUN_ID_HEX.encode("ascii"), runtime.P348_COMMAND)
        self.assertEqual(runtime.child_source(), p347_runtime.child_source())

    def test_later_acceptance_table_is_finite_and_json_safe(self) -> None:
        self.assertEqual(
            tuple(observer.LATER_ACCEPTANCE_COMMANDS),
            (
                "checked-snapshot",
                "known-nonzero",
                "timeout",
                "active-cancel",
                "post-cancel-success",
            ),
        )
        checked = observer.LATER_ACCEPTANCE_COMMANDS["checked-snapshot"]
        self.assertIn(b"/proc/version", checked["command"])
        self.assertEqual(checked["middle"]["output"], observer.CHECKED_SNAPSHOT_MARKER)
        self.assertEqual(observer.later_acceptance_binding()["timeout"]["middle"]["duration_ms_min"], 15000)

    def test_qualify_runs_five_same_fd_then_one_idle_reopen(self) -> None:
        calls: list[int] = []
        clock = _Clock()

        def fake_exchange(*args, **kwargs):
            del kwargs
            calls.append(args[1])
            result = _fake_result(len(calls), args[3])
            args[5].add(hashlib.sha256(result.session.audit.nonce).hexdigest())
            return result

        def reopen_after_idle() -> int:
            clock.value += observer.IDLE_SECONDS
            return 24

        with mock.patch.object(observer.shell_exchange, "exchange",
                               side_effect=fake_exchange), mock.patch.object(
                                   observer.time,
                                   "monotonic",
                                   side_effect=clock.monotonic,
                               ):
            result = observer.qualify(
                object(),
                23,
                KEY,
                None,
                set(),
                _Writer(),
                deadline=300,
                reopen_after_idle=reopen_after_idle,
            )

        self.assertEqual(calls, [23, 23, 23, 23, 23, 24])
        self.assertEqual(result.receipt["session_count"], 6)
        self.assertEqual(result.receipt["total_command_count"], 18)
        self.assertTrue(result.receipt["initial_five_same_tty_fd"])
        self.assertFalse(result.receipt["same_tty_fd"])
        self.assertEqual(result.receipt["physical_reopen_count"], 1)
        self.assertEqual(result.receipt["idle_duration_ms"], 120000)
        self.assertEqual(result.receipt["reopen"]["idle_duration_ms"], 120000)
        self.assertFalse(result.receipt["sessions"][5]["descriptor_reused"])
        self.assertTrue(result.receipt["sessions"][5]["semantic"]["reopen_witness"])
        self.assertEqual(observer.validate_qualification(result.receipt), dict(result.receipt))

        bad = dict(result.receipt)
        bad["idle_duration_ms"] = 119999
        with self.assertRaises(observer.QualificationError):
            observer.validate_qualification(bad)
        bad = dict(result.receipt)
        bad["physical_reopen_count"] = True
        with self.assertRaises(observer.QualificationError):
            observer.validate_qualification(bad)
        bad = dict(result.receipt)
        bad["sessions"] = [dict(row) for row in result.receipt["sessions"]]
        bad["sessions"][5]["physical_reopen_index"] = True
        with self.assertRaises(observer.QualificationError):
            observer.validate_qualification(bad)

    def test_raw_reopen_witness_session_reopens_and_rejects_trailing_bytes(self) -> None:
        nonce = bytes(range(1, runtime.NONCE_SIZE + 1))
        run_id = runtime.P348_RUN_ID

        def tag(domain: bytes, sequence: int | None = None, body: bytes = b"") -> bytes:
            message = bytearray(domain + run_id + nonce)
            if sequence is not None:
                message.extend(struct.pack("<I", sequence))
            message.extend(body)
            return hmac.new(KEY, bytes(message), hashlib.sha256).digest()

        def frame(frame_type: int, sequence: int, payload: bytes) -> bytes:
            return codec.encode_frame(frame_type, sequence, payload)

        parsed_observer = SimpleNamespace(
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
                and auth_key == KEY
                and current_run == run_id
                and current_nonce == nonce
                and len(value.payload) == 64
                else (_ for _ in ()).throw(ValueError("boot frame differs"))
            ),
        )
        identity_output = b"uid=0(root) gid=0(root) groups=0(root)\n"
        nonce_output = b"P328-NONCE " + runtime.P348_RUN_ID_HEX.encode("ascii") + b"\n"
        rx = bytearray(runtime.DEVICE_BANNER)
        for stage in (
            runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER,
            runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
            runtime.DIAGNOSTIC_STAGE_RNG,
        ):
            rx.extend(frame(runtime.DIAGNOSTIC_FRAME_TYPE, 0, struct.pack("<Ii", stage, 0)))
        rx.extend(frame(runtime.FRAME_CHALLENGE, 0, nonce))
        rx.extend(frame(runtime.FRAME_READY, 1, tag(runtime.AUTH_DOMAIN_READY)))
        rx.extend(
            frame(
                runtime.FRAME_BOOT_ID,
                runtime.P335_BOOT_ID_SEQUENCE,
                BOOT_ID
                + hmac.new(
                    KEY,
                    runtime.AUTH_DOMAIN_BOOT_ID
                    + run_id
                    + nonce
                    + struct.pack("<I", runtime.P335_BOOT_ID_SEQUENCE)
                    + BOOT_ID,
                    hashlib.sha256,
                ).digest(),
            )
        )
        outputs = (identity_output, observer.REOPEN_WITNESS_MARKER, nonce_output)
        commands = (
            runtime.DEFAULT_COMMANDS[0],
            observer.REOPEN_WITNESS_COMMAND,
            runtime.DEFAULT_COMMANDS[2],
        )
        for sequence, (command, output) in zip((3, 4, 5), zip(commands, outputs)):
            rx.extend(frame(runtime.FRAME_DATA, sequence, output))
            rx.extend(frame(runtime.FRAME_EXIT, sequence,
                            codec.EXIT.pack(0, 0, 0, len(output), 1)))
        rx.extend(frame(runtime.FRAME_DONE, 6, struct.pack("<I", 3)))
        tx = bytearray(frame(runtime.FRAME_OPEN, 0, run_id))
        tx.extend(frame(runtime.FRAME_AUTH, 1, tag(runtime.AUTH_DOMAIN_OPEN)))
        for sequence, command in zip((3, 4, 5), commands):
            tx.extend(frame(runtime.FRAME_EXEC, sequence,
                            tag(runtime.AUTH_DOMAIN_EXEC, sequence, command) + command))
        tx.extend(frame(runtime.FRAME_CLOSE, 6, tag(runtime.AUTH_DOMAIN_CLOSE, 6)))

        parsed = observer.parse_captured_session(parsed_observer, bytes(rx), bytes(tx), KEY)
        self.assertEqual(parsed.outcome, "ok")
        self.assertEqual(
            observer.validate_session_result(parsed, observer.REOPEN_STEP)["semantic"],
            {"reopen_witness": True, "marker_seen": True},
        )
        with self.assertRaises(observer.QualificationError):
            observer.parse_captured_session(parsed_observer, bytes(rx) + b"x", bytes(tx), KEY)


if __name__ == "__main__":
    unittest.main()
