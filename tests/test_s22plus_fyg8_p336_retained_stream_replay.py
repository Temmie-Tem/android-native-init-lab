"""Retained-byte unit tests for the P3.36 long-idle action resync helper.

Scope, stated plainly because an earlier revision of this module overstated it:

* These tests exercise `_consume_preambles_until_open_parsed`, a helper of
  `exchange_late_action` in the P3.36 long-idle action module.
* That path was **not** executed by the P3.36 F1 campaign.  The F1 initial
  observation runs `exchange_retained` through `_P336ObserverSession`, and the
  long-idle action runner was never invoked.  Nothing here reproduces,
  explains, or constrains the P3.36 `NO_PROOF` result.
* The value they do carry is that their device input is replayed from bytes the
  candidate actually emitted, rather than synthesized by the fixture.

Provenance of `RETAINED_STAGE_FRAMES`: the three diagnostic frames that follow
the first 49-byte banner in the retained candidate RX capture of the consumed
P3.35 run (`candidate-observer.raw`, 1,983 bytes, three sessions).  They carry
no private identifier: each is magic/version/type/length/sequence/CRC plus an
8-byte stage ordinal.  `workspace/private/**` is untracked, so the bytes are
embedded here.

See `docs/reports/S22PLUS_FYG8_P336_INITIAL_SESSION_DELTA_H0_2026-09-04.md`.
"""

from __future__ import annotations

from pathlib import Path
import socket
import sys
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p336_long_idle_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p336_long_idle_runtime as runtime  # noqa: E402


# Retained device output, consumed P3.35 run, session 1, in emission order.
RETAINED_STAGE_FRAMES = (
    bytes.fromhex("5333323801860800000000009fd64dbb0000000000000000"),
    bytes.fromhex("53333238018608000000000001d6e7770100000000000000"),
    bytes.fromhex("533332380186080000000000e2d168f90200000000000000"),
)

REPLAY_TIMEOUT_SEC = 0.4


class _Writer:
    """Minimal raw sink; the replayed helper performs no host TX."""

    def __init__(self) -> None:
        self.rx = bytearray()
        self.tx = bytearray()

    def write_stdout(self, value: bytes) -> None:
        self.rx += value

    def note_tx(self, value: bytes) -> None:
        self.tx += value


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
