"""Retained-byte tests for the P3.36 initial observation and resync helper.

Two scopes live here, kept separate on purpose:

* `P336InitialObserverFailureTests` drives the code path the P3.36 F1 campaign
  actually executed: `exchange_retained` on `_P336ObserverSession.auth_observer`,
  followed by the real receipt projection.  Its device side emits the exact
  73 bytes the candidate emitted and then falls silent, so the fixture RX is
  byte-identical to `candidate-observer.raw` of the consumed P3.36 run.
* `P336RetainedFrameTests` and `P336LateActionResyncReplayTests` exercise
  `_consume_preambles_until_open_parsed`, a helper of `exchange_late_action` in
  the P3.36 long-idle action module.  That path was **not** executed by the F1
  campaign; the long-idle action runner was never invoked.  Nothing in those
  two classes reproduces, explains, or constrains the `NO_PROOF` result.

Neither scope decides why the candidate stopped after stage 0.  The initial
tests fix what the host must retain when it does, which is the one defect the
campaign established.

Provenance of `RETAINED_STAGE_FRAMES`: the three diagnostic frames that follow
the first 49-byte banner in the retained candidate RX capture of the consumed
P3.35 run (`candidate-observer.raw`, 1,983 bytes, three sessions).  They carry
no private identifier: each is magic/version/type/length/sequence/CRC plus an
8-byte stage ordinal.  `workspace/private/**` is untracked, so the bytes are
embedded here.

See `docs/reports/S22PLUS_FYG8_P336_INITIAL_SESSION_DELTA_H0_2026-09-04.md`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import socket
import sys
import threading
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import device_action_f1_live_v2 as live  # noqa: E402
import s22plus_fyg8_p336_long_idle_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p336_long_idle_runtime as runtime  # noqa: E402


# Retained device output, consumed P3.35 run, session 1, in emission order.
RETAINED_STAGE_FRAMES = (
    bytes.fromhex("5333323801860800000000009fd64dbb0000000000000000"),
    bytes.fromhex("53333238018608000000000001d6e7770100000000000000"),
    bytes.fromhex("533332380186080000000000e2d168f90200000000000000"),
)

REPLAY_TIMEOUT_SEC = 0.4

# `candidate-observer.raw` of the consumed P3.36 F1 run: 73 bytes, one 49-byte
# banner followed by one stage-zero diagnostic frame, and nothing else for the
# observer's whole 30,183 ms.  The digest is reproduced by the fixture below;
# both operands are public (the banner carries P336_RUN_ID_HEX from the tracked
# runtime module), so this pins the live failure without importing private
# evidence.
RETAINED_P336_RX_SHA256 = (
    "19955936676751fff5e9d8643b0b5d4f8a89e27d94da57c80771ef5c1b39b5b6"
)


class _Writer:
    """Minimal raw sink; the replayed helper performs no host TX."""

    def __init__(self) -> None:
        self.rx = bytearray()
        self.tx = bytearray()

    def write_stdout(self, value: bytes) -> None:
        self.rx += value

    def note_tx(self, value: bytes) -> None:
        self.tx += value


class P336InitialObserverFailureTests(unittest.TestCase):
    """The path the P3.36 F1 campaign executed, driven end to end.

    The device side is a socketpair peer that emits the candidate's exact
    banner and stage-zero diagnostic and then stays open and silent.  Nothing
    is mocked between the fixture bytes and the receipt: `exchange_retained`
    writes a real OPEN, blocks on the stage-one read, and the real projection
    turns the failure into the durable receipt.
    """

    def _initial_observer(self):
        return live._P336_INITIAL_OBSERVER  # noqa: SLF001

    def _candidate_prefix(self) -> bytes:
        """The exact 73 bytes the candidate emitted before falling silent."""
        return runtime.DEVICE_BANNER + observer.encode_frame(
            runtime.DIAGNOSTIC_FRAME_TYPE,
            0,
            observer.DIAGNOSTIC.pack(runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER, 0),
        )

    def _run_initial_exchange(self):
        """Return the retained failure of one real initial exchange."""
        auth_observer = self._initial_observer()
        host, peer = socket.socketpair()
        spare_host, spare_peer = socket.socketpair()
        for sock in (host, peer, spare_host, spare_peer):
            self.addCleanup(sock.close)
        released = threading.Event()

        def serve() -> None:
            peer.sendall(self._candidate_prefix())
            # Silence, not EOF: the candidate held the endpoint open.
            released.wait(REPLAY_TIMEOUT_SEC * 8)

        thread = threading.Thread(target=serve)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(released.set)
        with self.assertRaises(
            auth_observer.RetainedListenerObserverError
        ) as caught:
            auth_observer.exchange_retained(
                host,
                bytes(range(runtime.AUTH_KEY_SIZE)),
                reopen=lambda: spare_host,
                timeout_sec=REPLAY_TIMEOUT_SEC,
            )
        return caught.exception

    def test_fixture_rx_is_byte_identical_to_the_candidate_capture(self) -> None:
        """The fixture replays the live bytes rather than a synthesized shape."""
        prefix = self._candidate_prefix()
        self.assertEqual(len(prefix), 73)
        self.assertEqual(len(runtime.DEVICE_BANNER), 49)
        self.assertEqual(
            hashlib.sha256(prefix).hexdigest(), RETAINED_P336_RX_SHA256
        )

    def test_initial_exchange_retains_open_tx_rx_and_failure_stage(self) -> None:
        """A stalled initial session must retain what it sent and received."""
        auth_observer = self._initial_observer()
        result = self._run_initial_exchange().result
        self.assertEqual(result.terminal, "session-failed")
        self.assertEqual(len(result.sessions), 1)
        session = result.sessions[0]
        self.assertFalse(session.authenticated)

        expected_open = observer.encode_frame(
            runtime.FRAME_OPEN, 0, runtime.P336_RUN_ID
        )
        self.assertEqual(len(expected_open), 32)
        self.assertEqual(session.raw_tx, expected_open)
        self.assertEqual(session.raw_rx, self._candidate_prefix())

        audit = session.audit
        self.assertIsNotNone(audit)
        self.assertEqual(audit.current_stage, "open-diagnostic-read")
        self.assertEqual(session.failure_stage, "open-diagnostic-read")
        self.assertEqual(
            [(item.stage, item.code) for item in audit.diagnostics],
            [(runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER, 0)],
        )
        self.assertLess(
            len(audit.diagnostics), auth_observer.MAX_SESSIONS + 1
        )

    def test_no_proof_projection_publishes_the_retained_open_tx(self) -> None:
        """A proofless P3.36 session must still reach a published receipt.

        Regression guard for the loss this campaign actually suffered: the
        P3.36 `observe()` override used to repin the inherited proof
        unconditionally, so an empty proof raised `F1LiveError` before
        publication and the run recorded `interrupted-before-receipt` with no
        TX, RX, diagnostics or partial state at all.
        """
        failure = self._run_initial_exchange()
        session = live._P336ObserverSession(  # noqa: SLF001
            None,
            None,
            {},
            Path("/unused/p336-initial"),
            {},
            {},
            Path("/unused/usb"),
            Path("/unused/typec"),
        )
        session.resident_result = failure.result
        session.protocol_error = str(failure)[:160]
        session.auth_key_sha256 = "0" * 64
        inherited = ({"classification": "authenticated-session-error", "accepted": False}, {})
        published: list[dict[str, object]] = []
        with (
            mock.patch.object(
                live._P327ObserverSession,  # noqa: SLF001
                "_observe_value",
                return_value=inherited,
            ),
            mock.patch.object(
                live._P327ObserverSession,  # noqa: SLF001
                "_publish_value",
                side_effect=(
                    lambda _self, value, _lane, *, label: published.append(value)
                ),
                autospec=False,
            ),
        ):
            value = session.observe(
                timeout_sec=1,
                download_departure={"absent": True},
            )

        self.assertEqual(len(published), 1)
        self.assertIs(published[0], value)
        self.assertEqual(value["schema"], live.P336_OBSERVER_RECEIPT_SCHEMA)
        self.assertEqual(value["classification"], "authenticated-session-error")
        self.assertFalse(value["accepted"])
        self.assertEqual(value["proof"], {})
        self.assertEqual(value["p336_authenticated_attended_resident"], {})
        # The withdrawn override repinned unconditionally.  Repinning an empty
        # proof still raises, so this pins the reason publication was lost
        # without depending on the shape of the old call site.
        with self.assertRaises(live.F1LiveError):
            live._p336_repin_proof({})  # noqa: SLF001

        expected_open = observer.encode_frame(
            runtime.FRAME_OPEN, 0, runtime.P336_RUN_ID
        )
        self.assertEqual(value["session_tx_hex"], [expected_open.hex()])
        self.assertEqual(value["tx"]["size"], len(expected_open))
        self.assertEqual(value["rx"]["size"], 73)
        self.assertEqual(value["rx"]["sha256"], RETAINED_P336_RX_SHA256)
        self.assertEqual(
            value["diagnostics"],
            [[{"stage": runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER, "code": 0}]],
        )
        self.assertEqual(len(value["partial_sessions"]), 1)
        partial = value["partial_sessions"][0]
        self.assertEqual(partial["session_index"], 0)
        self.assertEqual(partial["current_stage"], "open-diagnostic-read")
        self.assertEqual(partial["failure_stage"], "open-diagnostic-read")
        self.assertEqual(partial["exception_type"], "TimeoutError")


class P336RetainedFrameTests(unittest.TestCase):
    """Device-frame identity, independent of any exchange path."""

    def test_tracked_encoder_reproduces_retained_device_frames(self) -> None:
        """The host frame model must match what the candidate actually emitted."""
        for stage, retained in enumerate(RETAINED_STAGE_FRAMES):
            with self.subTest(stage=stage):
                encoded = observer.encode_frame(
                    runtime.DIAGNOSTIC_FRAME_TYPE,
                    0,
                    observer.DIAGNOSTIC.pack(stage, 0),
                )
                self.assertEqual(encoded, retained)

    def test_retained_frames_decode_to_a_monotonic_stage_progression(self) -> None:
        """Within one session the candidate advances stage 0 -> 1 -> 2."""
        stages = [
            observer.DIAGNOSTIC.unpack(observer.decode_frame(frame).payload)[0]
            for frame in RETAINED_STAGE_FRAMES
        ]
        self.assertEqual(stages, [0, 1, 2])
        self.assertEqual(stages[1], runtime.DIAGNOSTIC_STAGE_OPEN_PARSED)


class P336LateActionResyncReplayTests(unittest.TestCase):
    """`exchange_late_action` helper only; not the F1 initial observation path."""

    def _replay(self, payload: bytes):
        host, peer = socket.socketpair()
        self.addCleanup(host.close)
        self.addCleanup(peer.close)
        peer.sendall(payload)
        audit = observer.ExchangeAudit(auth_key_sha256="0" * 64)
        setattr(audit, "resync_preamble_count", 0)
        setattr(audit, "resync_open_parsed_seen", False)
        writer = _Writer()
        error: BaseException | None = None
        count = None
        try:
            count = observer._consume_preambles_until_open_parsed(  # noqa: SLF001
                host.fileno(),
                time.monotonic() + REPLAY_TIMEOUT_SEC,
                audit,
                writer,
            )
        except BaseException as exc:  # noqa: BLE001 - the stall is the assertion
            error = exc
        return count, audit, writer, error

    def test_banner_stage0_stage1_completes_resync(self) -> None:
        """Banner then stages 0 and 1 satisfies the helper's terminator."""
        payload = (
            runtime.DEVICE_BANNER
            + RETAINED_STAGE_FRAMES[0]
            + RETAINED_STAGE_FRAMES[1]
        )
        count, audit, _writer, error = self._replay(payload)
        self.assertIsNone(error)
        self.assertEqual(count, 1)
        self.assertTrue(getattr(audit, "resync_open_parsed_seen"))
        self.assertLessEqual(count, observer.MAX_PREAMBLE_PAIRS)

    def test_banner_stage0_without_stage1_stalls_in_the_prefix_read(self) -> None:
        """Absent the stage-1 terminator the helper waits rather than misparses.

        This characterises the helper.  It is not a model of the P3.36 F1
        failure, which occurred on a different code path; see the module
        docstring.
        """
        payload = runtime.DEVICE_BANNER + RETAINED_STAGE_FRAMES[0]
        count, audit, writer, error = self._replay(payload)
        self.assertIsNone(count)
        self.assertIsNotNone(error)
        self.assertNotIsInstance(error, observer.AuthObserverError)
        self.assertEqual(audit.current_stage, "resync-prefix")
        self.assertEqual(getattr(audit, "resync_preamble_count"), 1)
        self.assertFalse(getattr(audit, "resync_open_parsed_seen"))
        self.assertEqual(len(writer.rx), len(payload))


if __name__ == "__main__":
    unittest.main()
