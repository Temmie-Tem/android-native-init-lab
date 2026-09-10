"""New consumer against production local PID1/renderer and real host IPC.

Numeric root, mounts, module/DRM hardware and health output are explicit H0
fixtures. No device access or physical display/second-boot claim is made.
"""
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import unittest
from unittest import mock

import test_s22plus_local_display_v1 as local
import s22plus_local_display_observer_v1 as observer


class LogTests(unittest.TestCase):
    run_id = '01'*16

    def frame(self, seq=1, up=1000, state=3, **changes):
        row = dict(seq=seq, uptime_ms=up, state=state, metrics_seq=1, valid=227,
            age_ms=1, mem_total=1024, mem_available=512, cpu_permille=50,
            battery_pct=0, charge=0, temp_deci=0, gauge_seq=1, gauge_age_ms=1,
            gauge_soc=500, voltage_uv=4000000, current_ua=-100000)
        row.update(changes)
        return ('HUD_FRAME run='+self.run_id + ''.join(' '+k+'='+str(row[k]) for k in observer._FIELDS)
                + ' event=matched visible=UNPROVED\n').encode()

    def log(self, *frames):
        return b'METRICS_START 42\nHUD_START 43\n' + b''.join(frames or (self.frame(),))

    def test_all_local_states_equal_tick_and_late_stale_samples(self):
        raw = self.log(*(self.frame(i+1, state=i) for i in range(9)),
            self.frame(916, 900000, 8, metrics_seq=601, gauge_seq=601, valid=0,
                       age_ms=299000, gauge_age_ms=299000))
        result = observer.decode_log(raw, self.run_id)
        self.assertTrue(result['valid']); self.assertEqual(result['states'], list(range(9)))
        self.assertEqual(result['fresh_gauge_samples'], 1)
        self.assertEqual(result['physical_visibility'], 'UNPROVED')

    def test_bounds_identity_freshness_and_partial_tail(self):
        for changes in (dict(seq=917), dict(state=9), dict(metrics_seq=602), dict(gauge_seq=602),
                        dict(valid=256), dict(age_ms=5001), dict(gauge_age_ms=5001),
                        dict(mem_available=1025), dict(cpu_permille=1001), dict(voltage_uv=1)):
            with self.subTest(changes=changes):
                self.assertFalse(observer.decode_log(self.log(self.frame(**changes)), self.run_id)['valid'])
        for raw in (self.log()[:-1], self.log()+b'HUD_UNKNOWN 1\n', self.log()+b'x'*observer.HUD_LIMIT,
                    self.log(self.frame(2), self.frame(1)), self.log(self.frame(up=2), self.frame(2, up=1)),
                    self.log().replace(b'HUD_START 43', b'HUD_START 42')):
            self.assertFalse(observer.decode_log(raw, self.run_id)['valid'])
        self.assertFalse(observer.decode_log(self.log(), '02'*16)['valid'])

    def test_signal_is_retained_without_claiming_reap_or_current_display(self):
        result = observer.decode_log(self.log()+b'HUD_SIGNAL_ATTEMPT 43\n', self.run_id)
        self.assertFalse(result['valid'])
        self.assertEqual(result['lifecycle_records'], ['HUD_SIGNAL_ATTEMPT 43'])

    def test_failed_display_kernel_diagnostics_cannot_supply_flip_evidence(self):
        for marker in (b'DISPLAY_DIAG failure\n', b'DISPLAY_KMSG_BEGIN\n', b'DISPLAY_KMSG_END\n'):
            raw = self.log(marker, self.frame())
            self.assertFalse(observer.decode_log(raw, self.run_id)['matched_flip_observed'])


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binding = observer.Binding(local.direct_test.runtime_identity(local.hud.runtime),
                                       local.direct.source_receipts())
        text = local.source().replace('const char *command=text;', r'''const char *command=text;
 if(strstr(command,"NB1"))command=fx_case("bad-health")?"printf BAD":
 "printf 'NB1\\n0\\n0\\n1\\nMOUNTS\\nCOMPLETE\\000OUT\\n'; printf 'COMPLETE\\000ERR\\n' >&2";
 if(strstr(command,"cat hud.log")&&fx_case("hud-read-fails"))command="exit 7";
 if(strstr(command,"cat hud.log")&&fx_case("hud-read-drops"))command="yes x | head -c 2000000";''')
        text = text.replace('static long fx_write(int fd,const void*p,size_t n){', r'''
static long fx_write(int fd,const void*p,size_t n){
 const unsigned char *frame=p;
 if(fx_case("hud-wire-corrupt")&&n>=48&&n<=1080&&frame[5]==160&&frame[8]==5){
  unsigned char bad[1080];memcpy(bad,p,n);bad[12]^=1;return neg(write(fd,bad,n));
 }''')
        census = tuple(local.direct.MemoryModule(*row) for row in local.memory.manifest())
        with mock.patch.object(local.hud, 'source', return_value=text), mock.patch.object(
                local.hud.renderer_test.renderer, 'render', side_effect=lambda:
                local.direct.render_display(cls.binding.identity, census, profile=local.direct.LOCAL_PROFILE)):
            local.hud.StatusIntegration.setUpClass.__func__(cls)
        cls.codec = local.parent_hud.live._open_header_initial_observer_module(
            local.hud.runtime, local.hud.observer, 'local-display-observer-h0')

    def exercise(self, case='normal', before_control=None, budget=30):
        directory = self.folder/str(time.monotonic_ns()); directory.mkdir()
        host, peer = socket.socketpair(); host.setblocking(False); peer.setblocking(False)
        env = dict(os.environ, P364_CASE=case, P364_MARK=str(directory/'marks'), RC1_WORK=str(directory),
                   HUD_RENDERER=str(self.real_renderer) if case != 'hud-stall' else '',
                   METRICS_COLLECTOR=str(self.collector), LOCAL_CLOCK_RATE='1')
        process = subprocess.Popen([str(self.binary), str(peer.fileno()), '1'], pass_fds=(peer.fileno(),),
                                   env=env, stderr=subprocess.PIPE, start_new_session=True)
        peer.close(); raw = bytearray(); intents = []
        writer = type('Writer', (), {'write_stdout': lambda _, data: raw.extend(data)})()
        io = local.hud.observer.IO(self.codec, b'k'*32, fd=host.fileno(), writer=writer,
                                   deadline=time.monotonic()+budget)
        result = error = None
        try:
            # The production local renderer receives WAIT_AUTH before OPEN.
            local.LocalLifecycle.until(self, lambda: b'state=3 ' in local.LocalLifecycle.log(directory)
                                       if case != 'hud-stall' else (directory/'hud.log').exists())
            try:
                result = observer.qualify(io, self.binding, evidence=directory/'console',
                                          before_control=before_control or intents.append)
            except observer.ObservationError as exc:
                error = exc
            return result, error, intents, bytes(raw), bytes(io.audit.tx)
        finally:
            host.close()
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.communicate(timeout=3)

    def replay(self, rx, tx):
        return observer.replay(local.hud.observer.IO(self.codec, b'k'*32, rx=rx, tx=tx), self.binding)

    def test_real_producer_consumer_and_retained_replay(self):
        result, error, intents, rx, tx = self.exercise()
        if error: raise AssertionError(repr(error.__cause__))
        self.assertTrue(result['native_health_proved']); self.assertTrue(result['hud']['valid'])
        self.assertIn(3, result['hud']['states']); self.assertTrue(result['control_acceptance_observed'])
        self.assertEqual(intents[0]['sequence'], 6)
        self.assertEqual(len(intents), 1); self.assertEqual(result, self.replay(rx, tx))
        for bad_rx, bad_tx in ((rx[:-1], tx), (rx[:-1]+bytes([rx[-1]^1]), tx), (rx, tx[:-1]),
                               (rx, tx+tx[-48:])):
            with self.assertRaises((ValueError, EOFError)):
                self.replay(bad_rx, bad_tx)

    def test_optional_failure_stall_and_output_loss_preserve_health_and_control(self):
        for case in ('hud-read-fails', 'hud-stall', 'hud-read-drops'):
            with self.subTest(case=case):
                result, error, intents, rx, tx = self.exercise(case)
                if error: raise AssertionError(repr(error.__cause__))
                self.assertTrue(result['native_health_proved'])
                self.assertTrue(result['control_acceptance_observed'])
                self.assertFalse(result['hud_acquisition_complete'] and result['hud']['valid'])
                self.assertEqual(result, self.replay(rx, tx)); self.assertEqual(len(intents), 1)

    def test_failed_health_and_rejected_owner_preserve_raw_without_control(self):
        def reject(_): raise ValueError('owner freshness rejection')
        for case, callback, healthy in (('bad-health', None, False), ('normal', reject, True)):
            result, error, intents, rx, tx = self.exercise(case, callback)
            self.assertIsNone(result); self.assertIsNotNone(error); self.assertTrue(rx)
            self.assertEqual(error.partial_receipt['native_health_proved'], healthy)
            self.assertFalse(error.partial_receipt['control_acceptance_observed'])
            self.assertEqual(intents, [])
            io = local.hud.observer.IO(self.codec, b'k'*32, rx=rx, tx=tx); io.handshake()
            requests = local.wire.Decoder(b'k'*32, bytes.fromhex(self.binding.identity.run_id_hex), io.audit.nonce)
            self.assertFalse(any(k == local.wire.CONTROL for k, _, _ in requests.feed(tx[io.tpos:])))

    def test_changed_profile_or_source_rejects_before_handshake(self):
        for binding in (observer.Binding(self.binding.identity, {}),
                        observer.Binding(self.binding.identity, self.binding.sources, local.direct.CONSOLE_PROFILE)):
            with self.assertRaises(ValueError):
                observer.qualify(None, binding, evidence='unused', before_control=lambda _: None)

    def test_small_remaining_budget_skips_hud_and_preserves_owned_control(self):
        result, error, intents, rx, tx = self.exercise(budget=5)
        if error: raise AssertionError(repr(error.__cause__))
        self.assertTrue(result['native_health_proved']); self.assertFalse(result['hud_requested'])
        self.assertTrue(result['control_acceptance_observed']); self.assertEqual(intents[0]['sequence'], 5)
        self.assertEqual(result, self.replay(rx, tx))

    def test_early_handshake_failures_return_original_raw_and_partial_receipt(self):
        result, error, _, rx, tx = self.exercise(budget=5)
        self.assertIsNone(error)
        for cut in (1, 100):
            io = local.hud.observer.IO(self.codec, b'k'*32, rx=rx[:cut], tx=tx,
                                       deadline=time.monotonic()+30)
            with self.assertRaises(observer.ObservationError) as raised:
                observer.qualify(io, self.binding, evidence='unused', before_control=lambda _: self.fail('CONTROL'))
            self.assertIsInstance(raised.exception.__cause__, (EOFError, ValueError))
            self.assertTrue(raised.exception.audit.rx)
            self.assertIsNone(raised.exception.partial_receipt['kernel_boot_identity_sha256'])
            self.assertFalse(raised.exception.partial_receipt['native_health_proved'])

    def test_corrupt_peer_frame_after_health_preserves_raw_and_sends_no_control(self):
        result, error, intents, rx, tx = self.exercise('hud-wire-corrupt')
        self.assertIsNone(result); self.assertEqual(intents, [])
        self.assertIsInstance(error.__cause__, local.wire.ProtocolError)
        self.assertTrue(error.partial_receipt['native_health_proved'])
        self.assertFalse(error.partial_receipt['control_acceptance_observed'])
        self.assertEqual(bytes(error.audit.rx), rx)
        io = local.hud.observer.IO(self.codec, b'k'*32, rx=rx, tx=tx); io.handshake()
        requests = local.wire.Decoder(b'k'*32, bytes.fromhex(self.binding.identity.run_id_hex), io.audit.nonce)
        self.assertEqual([(k, n) for k, n, _ in requests.feed(tx[io.tpos:])],
                         [(local.wire.EXEC, 3), (local.wire.STATUS, 4), (local.wire.EXEC, 5)])


if __name__ == '__main__':
    unittest.main()
