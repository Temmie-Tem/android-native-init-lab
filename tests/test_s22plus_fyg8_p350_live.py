"""P350 real authenticated wire receipts through the production durable validator."""
import copy
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture, KEY, KEY_SHA256, BOOT_ID
import device_action_f1_live_v2 as live


class P350ReceiptFixture(_ReceiptFixture):
    def __init__(self, run_dir):
        super().__init__(run_dir, variant='p350')

    def _session(self, ordinal: int) -> tuple[bytes, bytes]:
        runtime = self.runtime
        observer = self.observer
        step = observer.QUALIFICATION_COMMANDS[ordinal - 1]
        nonce = bytes([ordinal]) * runtime.NONCE_SIZE
        rx = bytearray(runtime.DEVICE_BANNER)
        for stage in (
            runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER,
            runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
            runtime.DIAGNOSTIC_STAGE_RNG,
        ):
            rx.extend(
                self._frame(
                    runtime.DIAGNOSTIC_FRAME_TYPE,
                    0,
                    struct.pack("<Ii", stage, 0),
                )
            )
        rx.extend(self._frame(runtime.FRAME_CHALLENGE, 0, nonce))
        rx.extend(
            self._frame(
                runtime.FRAME_READY,
                1,
                self._tag(runtime.AUTH_DOMAIN_READY, nonce),
            )
        )
        rx.extend(
            self._frame(
                runtime.FRAME_BOOT_ID,
                runtime.P335_BOOT_ID_SEQUENCE,
                BOOT_ID
                + self.codec.compute_boot_id_tag(
                    KEY, runtime.P345_RUN_ID, nonce, BOOT_ID
                ),
            )
        )

        middle = (observer.PRE_MARKER, observer.display_output(42), observer.POST_MARKER)[ordinal - 1]
        flags, exit_code, term_signal = 0, 0, 0

        outputs = (
            b"uid=0(root) gid=0(root) groups=0(root)\n",
            middle,
            b"P328-NONCE " + runtime.P345_RUN_ID_HEX.encode("ascii") + b"\n",
        )
        for sequence, output in zip((3, 4, 5), outputs):
            for offset in range(0, len(output), 1024):
                rx.extend(self._frame(runtime.FRAME_DATA, sequence, output[offset:offset+1024]))
            rx.extend(
                self._frame(
                    runtime.FRAME_EXIT,
                    sequence,
                    self.codec.EXIT.pack(
                        flags if sequence == 4 else 0,
                        exit_code if sequence == 4 else 0,
                        term_signal if sequence == 4 else 0,
                        len(output),
                        10000 if ordinal == 2 and sequence == 4 else 1,
                    ),
                )
            )
            if ordinal == 4 and sequence == 4:
                rx.extend(
                    self._frame(
                        runtime.FRAME_CANCEL_ACK,
                        4,
                        struct.pack("<I", runtime.P345_CANCEL_STATUS_CONSUMED),
                    )
                )
        rx.extend(self._frame(runtime.FRAME_DONE, 6, struct.pack("<I", 3)))

        commands = (
            runtime.DEFAULT_COMMANDS[0],
            step.command,
            runtime.DEFAULT_COMMANDS[2],
        )
        tx = bytearray(self._frame(runtime.FRAME_OPEN, 0, runtime.P345_RUN_ID))
        tx.extend(
            self._frame(
                runtime.FRAME_AUTH,
                1,
                self._tag(runtime.AUTH_DOMAIN_OPEN, nonce),
            )
        )
        for sequence, command in zip((3, 4), commands[:2]):
            tx.extend(
                self._frame(
                    runtime.FRAME_EXEC,
                    sequence,
                    self._tag(runtime.AUTH_DOMAIN_EXEC, nonce, sequence, command)
                    + command,
                )
            )
        if ordinal == 4:
            tx.extend(
                self._frame(
                    runtime.FRAME_CANCEL,
                    runtime.P345_CANCEL_SEQUENCE,
                    runtime.cancel_tag(KEY, runtime.P345_RUN_ID, nonce),
                )
            )
        command = commands[2]
        tx.extend(
            self._frame(
                runtime.FRAME_EXEC,
                5,
                self._tag(runtime.AUTH_DOMAIN_EXEC, nonce, 5, command) + command,
            )
        )
        tx.extend(
            self._frame(
                runtime.FRAME_CLOSE,
                6,
                self._tag(runtime.AUTH_DOMAIN_CLOSE, nonce, 6),
            )
        )
        return bytes(rx), bytes(tx)

    def _qualification_proof(self):
        parsed = []
        for ordinal in range(1, 4):
            rx, tx = self._session(ordinal)
            shell = self.observer.parse_captured_session(self.codec, rx, tx, KEY)
            self.audits.append(shell.session.audit)
            self.rx_streams.append(rx)
            self.tx_streams.append(tx)
            parsed.append(shell)
        remaining = iter(parsed)
        exchange = lambda *a, **k: next(remaining)
        writer = SimpleNamespace(current_sizes=lambda: (0, 0))
        with mock.patch.object(self.observer._base.shell_exchange, 'exchange', side_effect=exchange), \
             mock.patch.object(self.observer._display_exchange, 'exchange', side_effect=exchange), \
             mock.patch.object(self.observer.time, 'monotonic', return_value=0.0):
            return self.observer.qualify(self.codec, 23, KEY, None, set(), writer, deadline=150).receipt

    def _receipt_value(self):
        value = super()._receipt_value()
        value[self.variant.proof_key] = value.pop('p350_readonly_research_shell_qualification')
        value.update(session_count=3, command_count=9)
        return value


class P350LiveTests(unittest.TestCase):
    def validate(self, fixture):
        with mock.patch.object(live, '_p328_read_auth_key', return_value=(KEY, KEY_SHA256)):
            return live._reopen_candidate_observation(fixture.prepared)

    def test_three_real_wire_sessions_reopen_without_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = P350ReceiptFixture(Path(directory) / 'run')
            durable = self.validate(fixture)
            self.assertTrue(live._p345_proof_ok(durable, prefix='p350'))
            self.assertEqual(durable['session_count'], 3)
            self.assertEqual(durable['command_count'], 9)
            self.assertFalse(live._named_exploration_bundle(fixture.prepared.bundle))
            self.assertFalse(durable['later_action_lease_active'])
            self.assertEqual(fixture.proof['visible_panel_output'], 'UNPROVED')

    def test_forged_counts_and_replayed_transmit_rejected(self):
        for mutation in ('count', 'replay', 'semantic'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                fixture = P350ReceiptFixture(Path(directory) / 'run')
                value = copy.deepcopy(fixture.value)
                if mutation == 'count':
                    value.update(session_count=5, command_count=15)
                elif mutation == 'replay':
                    value['session_tx_hex'][2] = value['session_tx_hex'][1]
                else:
                    value[fixture.variant.proof_key]['sessions'][1]['semantic']['completed_frames'] = 9
                fixture.publish(value)
                with mock.patch.object(live, '_p328_read_auth_key', return_value=(KEY, KEY_SHA256)):
                    with self.assertRaises(live.F1LiveError):
                        live._p345_validate_receipt(fixture.prepared, fixture.run_dir / 'candidate-observer.json', fixture.spec)
                self.assertFalse(live._p345_proof_ok(self.validate(fixture), prefix='p350'))


if __name__ == '__main__':
    unittest.main()
