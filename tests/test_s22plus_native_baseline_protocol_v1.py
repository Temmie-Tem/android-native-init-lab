"""Real production baseline C and host raw replay; hardware remains a fixture."""
from contextlib import contextmanager
import os
from pathlib import Path
import pty
import signal
import struct
import subprocess
import time
import tty
from types import SimpleNamespace
import unittest
from unittest import mock

import test_s22plus_local_display_v1 as local
import s22plus_fyg8_p383_research_shell_runtime as platform
import s22plus_fyg8_p385_candidate as candidate
import s22plus_native_baseline_protocol_v1 as protocol
import s22plus_native_source_v1 as direct
import s22plus_root_console_v1 as wire


def fixture_runtime():
    runtime = SimpleNamespace(**vars(platform))
    runtime.__dict__.update(vars(candidate.runtime))
    runtime.__file__ = candidate.__file__
    runtime.return_spec = SimpleNamespace(**vars(platform.return_spec))
    runtime.return_spec.render_module_table = lambda: platform.return_spec.render_module_table().replace(b'p383', b'p385')
    return runtime


def source():
    runtime = fixture_runtime()
    with mock.patch.dict(local.direct_test.VERSIONS, p385=candidate.IDENTITY.display_version):
        text = local.source(runtime, profile=direct.BASELINE_PROFILE)
    before = 'const char*u="01234567-89ab-4cde-8fab-0123456789ab\\n";'
    assert text.count(before) == 1
    text = text.replace(before, 'const char*u=getenv("NB1_UUID");if(!u)u="01234567-89ab-4cde-8fab-0123456789ab\\n";', 1)
    before = 'const char *command=text;'
    assert text.count(before) == 1
    text = text.replace(before, before+r'''
 if(strstr(command,"NB1"))command=fx_case("bad-health")?"printf BAD":
 "printf 'NB1\\n0\\n0\\n1\\nMOUNTS\\nCOMPLETE\\000OUT\\n'; printf 'COMPLETE\\000ERR\\n' >&2";
 if(strstr(command,"cat hud.log")&&fx_case("hud-read-fails"))command="exit 7";
''', 1)
    before = 'static long p385_prepare_return(void) {'
    assert text.count(before) == 1
    text = text.replace(before, before+'\n    fx_mark("baseline-boot-prepare",0);', 1)
    before = 'static long fx_syscall(long nr,long a,long b,long c,long d,long e,long f){'
    assert text.count(before) == 1
    text = text.replace(before, before+'\n if(nr==278&&fx_case("same-nonce")){memset((void*)a,82,b);return b;}\n'
        ' if(nr==278&&fx_case("cycling-nonce")){static unsigned call;memset((void*)a,82+(call++%2),b);return b;}', 1)
    # A socket preserves queued ACK bytes on peer exit; a PTY master close can
    # discard them. Model the nonreturning reboot after its exact-argv check by
    # keeping the fixture descriptor alive until the test owner tears it down.
    before = 'fx_mark("download",0);return -EIO;'
    assert text.count(before) == 1
    text = text.replace(before, 'fx_mark("download",0);for(;;)usleep(10000);', 1)
    before = 'unsigned long rate=getenv("LOCAL_CLOCK_RATE")'
    assert text.count(before) == 1
    text = text.replace(before, '''char advance[4096];
 snprintf(advance,sizeof(advance),"%s/advance-clock",getenv("RC1_WORK"));
 if(fx_case("expiry-after-detach")&&access(advance,F_OK)==0)fx_clock_offset_ms=900001;
 '''+before, 1)
    return text


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runtime = fixture_runtime()
        census = tuple(direct.MemoryModule(*row) for row in local.memory.manifest())
        with mock.patch.object(local.hud, 'runtime', runtime), mock.patch.object(local.hud, 'observer', candidate.observer), \
                mock.patch.object(local.hud, 'source', side_effect=source), \
                mock.patch.object(local.hud.renderer_test.renderer, 'render',
                    side_effect=lambda: direct.render_display(candidate.IDENTITY, census, profile=direct.BASELINE_PROFILE)):
            local.hud.StatusIntegration.setUpClass.__func__(cls)
        cls.codec = local.parent_hud.live._open_header_initial_observer_module(runtime, candidate.observer,
                                                                             'native-baseline-protocol-h0')

    @contextmanager
    def running(self, case='normal'):
        folder = self.folder/str(time.monotonic_ns()); folder.mkdir()
        master, descriptor = pty.openpty(); tty.setraw(descriptor)
        os.set_blocking(master, False); os.set_blocking(descriptor, False)
        name = os.ttyname(descriptor)
        process = subprocess.Popen([str(self.binary), str(master), '1'], pass_fds=(master,),
            start_new_session=True, stderr=subprocess.PIPE,
            env=dict(os.environ, P364_CASE=case, P364_MARK=str(folder/'marks'), RC1_WORK=str(folder),
                HUD_RENDERER=str(self.real_renderer), METRICS_COLLECTOR=str(self.collector), LOCAL_CLOCK_RATE='1'))
        os.close(master)
        context = SimpleNamespace(folder=folder, fd=descriptor, name=name, process=process, raw=bytearray(),
            detach=[], controls=[], reopened=0)
        def reopen(row, deadline):
            self.assertTrue(row['detach_ack_observed']); self.assertLess(time.monotonic(), deadline)
            old = context.fd; context.fd = None; os.close(old)
            if case == 'expiry-after-detach': (folder/'advance-clock').write_text('advance fixture clock')
            context.fd = os.open(name, os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK|os.O_CLOEXEC)
            tty.setraw(context.fd); context.reopened += 1
            return context.fd
        context.reopen = reopen
        try: yield context
        finally:
            if context.fd is not None: os.close(context.fd)
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.communicate(timeout=3)

    def qualify(self, context, mode='pair-detach', budget=10, before_control=None):
        return candidate.observer.qualify(self.codec, context.fd, b'k'*32, None, set(),
            SimpleNamespace(write_stdout=context.raw.extend), deadline=time.monotonic()+budget,
            before_control=before_control or context.controls.append, before_detach=context.detach.append,
            reopen=context.reopen, evidence=context.folder/('console-'+str(time.monotonic_ns())), mode=mode)

    def test_clean_pty_detach_reopen_preserves_boot_preparation_and_raw_proof(self):
        with self.running() as context:
            result = self.qualify(context)
            proof = result.receipt
            self.assertTrue(proof['proved']); self.assertTrue(proof['clean_detach_observed'])
            self.assertFalse(proof['control_acceptance_observed']); self.assertEqual(context.reopened, 1)
            self.assertEqual([r['baseline_info']['authentication_ordinal'] for r in proof['sessions']], [1, 2])
            self.assertEqual([r['baseline_info']['preparation_cached'] for r in proof['sessions']], [False, True])
            self.assertEqual(context.controls, []); self.assertEqual(len(context.detach), 2)
            self.assertEqual(context.folder.joinpath('marks').read_text().count('baseline-boot-prepare'), 1)
            tx = b''.join(bytes(s.session.audit.tx) for s in result.sessions)
            rx = bytes(context.raw)
            self.assertEqual(proof, candidate.observer.replay_session(self.codec, rx, tx, b'k'*32, mode='pair-detach'))
            for bad_rx, bad_tx in ((rx[:-1], tx), (rx, tx[:-1]), (rx+b'x', tx), (rx, tx+tx[-48:])):
                with self.assertRaises((ValueError, EOFError)):
                    candidate.observer.replay_session(self.codec, bad_rx, bad_tx, b'k'*32, mode='pair-detach')
            # Another owner can freshly authenticate on the same native boot.
            context.reopen(proof['sessions'][-1], time.monotonic()+2)
            context.raw.clear()
            third = self.qualify(context, mode='control').receipt
            protocol.fresh_same_boot(proof['sessions'][-1], third['sessions'][0])
            self.assertEqual(third['sessions'][0]['baseline_info']['authentication_ordinal'], 3)
            self.assertEqual(len(context.controls), 1)

    def test_pair_control_and_optional_hud_failure_keep_exact_terminal_scope(self):
        for case, budget in (('normal', 10), ('normal', 40), ('hud-read-fails', 40)):
            with self.subTest(case=case), self.running(case) as context:
                result = self.qualify(context, mode='pair-control', budget=budget)
                self.assertTrue(result.receipt['control_acceptance_observed'])
                self.assertEqual(len(context.detach), 1); self.assertEqual(len(context.controls), 1)
                tx = b''.join(bytes(s.session.audit.tx) for s in result.sessions)
                self.assertEqual(result.receipt,
                    candidate.observer.replay_session(self.codec, bytes(context.raw), tx, b'k'*32))
                if case == 'hud-read-fails':
                    self.assertTrue(result.receipt['sessions'][-1]['hud_requested'])
                    self.assertFalse(result.receipt['sessions'][-1]['hud_acquisition_complete'])
                if result.receipt['sessions'][-1]['hud_requested']:
                    # Reorder intact signed frames, preserving every HMAC/CRC.
                    # The fixed request/response phase order must still reject it.
                    second = result.receipt['sessions'][1]
                    raw = bytes(context.raw); offset = second['rx']['offset']
                    io = candidate.observer.IO(self.codec, b'k'*32, rx=raw[offset:], tx=tx[second['tx']['offset']:])
                    io.handshake(); pos = offset+io.rpos; frames = []
                    while pos < len(raw):
                        _,_,kind,size,seq,_ = struct.unpack_from('<4sBBHII', raw, pos)
                        frames.append((kind,seq,raw[pos:pos+16+size])); pos += 16+size
                    status = next(row for row in frames if row[:2] == (wire.STATUS_REPLY,4))
                    changed = [row for row in frames if row is not status]
                    changed.insert(len(changed)-1,status)
                    with self.assertRaisesRegex(ValueError,'phase order'):
                        candidate.observer.replay_session(self.codec,
                            raw[:offset+io.rpos]+b''.join(row[2] for row in changed), tx, b'k'*32)

    def test_failed_health_nonce_or_expiry_never_emits_control_or_retries_auth(self):
        for case in ('bad-health', 'same-nonce', 'expiry-after-detach'):
            with self.subTest(case=case), self.running(case) as context:
                with self.assertRaises(candidate.observer.QualificationError) as caught:
                    self.qualify(context, mode='pair-control', budget=3)
                error = caught.exception
                self.assertFalse(error.partial_receipt['proved']); self.assertTrue(context.raw)
                self.assertEqual(context.controls, [])
                self.assertEqual(context.reopened, 0 if case == 'bad-health' else 1)
                audits = [s.session.audit for s in error.completed_sessions]
                if error.failed_audit is not None: audits.append(error.failed_audit)
                self.assertEqual(bytes(context.raw), b''.join(bytes(a.rx) for a in audits))
                self.assertLessEqual(len(audits), 2)

    def test_authentication_limit_keeps_last_slot_for_control(self):
        with self.running() as context:
            previous = None
            for ordinal in range(1, protocol.AUTH_LIMIT):
                result = self.qualify(context, mode='detach', budget=5).receipt['sessions'][0]
                self.assertEqual(result['baseline_info']['authentication_ordinal'], ordinal)
                if previous is not None: protocol.fresh_same_boot(previous, result)
                previous = result
                context.reopen(result, time.monotonic()+2)
            final = self.qualify(context, mode='control', budget=5).receipt['sessions'][0]
            protocol.fresh_same_boot(previous, final)
            self.assertEqual(final['baseline_info']['authentication_ordinal'], protocol.AUTH_LIMIT)
            self.assertEqual(context.folder.joinpath('marks').read_text().count('baseline-boot-prepare'), 1)

    def test_nonadjacent_nonce_reuse_stops_third_authentication(self):
        with self.running('cycling-nonce') as context:
            seen = set(); previous = None
            for _ in range(2):
                row = self.qualify(context, mode='detach', budget=3).receipt['sessions'][0]
                if previous: protocol.fresh_same_boot(previous, row, seen_nonce_hashes=seen)
                seen.add(row['nonce_sha256']); previous = row
                context.reopen(row, time.monotonic()+2)
            with self.assertRaises(candidate.observer.QualificationError):
                self.qualify(context, mode='control', budget=1)
            self.assertEqual(context.controls, [])


if __name__ == '__main__': unittest.main()
