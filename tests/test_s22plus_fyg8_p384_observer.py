"""P384 production helper/renderer and direct observer; hardware is a fixture."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
from types import SimpleNamespace
import unittest
from unittest import mock

import test_s22plus_local_display_observer_v1 as previous
import s22plus_fyg8_p384_candidate as candidate
import s22plus_fyg8_p383_research_shell_runtime as platform

local = previous.local


def fixture_runtime():
    # Fixture support supplies only old hardware/module hooks. The production
    # helper itself comes directly from the P384 declaration and templates.
    value = SimpleNamespace(**vars(platform))
    value.__dict__.update(vars(candidate.runtime))
    value.__file__ = candidate.__file__
    value.P345_RUN_ID_HEX = candidate.IDENTITY.run_id_hex
    value.P345_RUN_ID = bytes.fromhex(candidate.IDENTITY.run_id_hex)
    value.return_spec = SimpleNamespace(**vars(platform.return_spec))
    value.return_spec.render_module_table = lambda: platform.return_spec.render_module_table().replace(b'p383', b'p384')
    return value


class ObserverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runtime = fixture_runtime(); make_source = local.source
        with mock.patch.object(local.hud, 'runtime', runtime), \
                mock.patch.object(local.hud, 'observer', candidate.observer), \
                mock.patch.object(local, 'source', side_effect=lambda: make_source(runtime=runtime)), \
                mock.patch.dict(local.direct_test.VERSIONS, p384=candidate.IDENTITY.display_version):
            previous.IntegrationTests.setUpClass.__func__(cls)

    def exercise(self, case='normal', budget=30, before_control=None):
        run = self.folder/str(time.monotonic_ns()); run.mkdir()
        host, peer = socket.socketpair(); host.setblocking(False); peer.setblocking(False)
        process = subprocess.Popen([str(self.binary), str(peer.fileno()), '1'], pass_fds=(peer.fileno(),),
            env=dict(os.environ, P364_CASE=case, P364_MARK=str(run/'marks'), RC1_WORK=str(run),
                HUD_RENDERER=str(self.real_renderer), METRICS_COLLECTOR=str(self.collector), LOCAL_CLOCK_RATE='1'),
            stderr=subprocess.PIPE, start_new_session=True)
        peer.close(); raw = bytearray(); intents = []; result = error = None
        writer = SimpleNamespace(write_stdout=raw.extend)
        try:
            try:
                result = candidate.observer.qualify(self.codec, host.fileno(), b'k'*32, None, set(), writer,
                    deadline=time.monotonic()+budget, before_control=before_control or intents.append,
                    evidence=run/'console', interactive=lambda *_: None)
            except candidate.observer.QualificationError as exc: error = exc
            audit = result.sessions[0].session.audit if result else error.failed_audit
            self.assertEqual(bytes(audit.rx), bytes(raw))
            return result, error, intents, bytes(raw), bytes(audit.tx)
        finally:
            host.close()
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.communicate(timeout=3)

    def test_complete_optional_failed_and_skipped_hud_replay(self):
        for case, budget, count in (('normal', 30, 2), ('hud-read-fails', 30, 2), ('normal', 5, 1)):
            with self.subTest(case=case, budget=budget):
                result, error, intents, rx, tx = self.exercise(case, budget)
                if error: raise AssertionError(repr(error.__cause__))
                self.assertTrue(result.receipt['proved'])
                self.assertEqual(result.receipt['command_count'], count)
                self.assertEqual(intents[0]['sequence'], count+4)
                self.assertEqual(intents[0]['boot_receipt_semantic'], candidate.CONTROL.BOOT_RECEIPT_SEMANTIC)
                self.assertEqual(result.receipt, candidate.observer.replay_session(self.codec, rx, tx, b'k'*32))
                self.assertEqual(result.receipt['preparation'], candidate.observer.replay_progress(self.codec, rx, tx, b'k'*32))

    def test_health_failure_and_wire_corruption_preserve_raw_without_control(self):
        for case, healthy in (('bad-health', False), ('hud-wire-corrupt', True)):
            with self.subTest(case=case):
                result, error, intents, rx, tx = self.exercise(case)
                self.assertIsNone(result); self.assertEqual(intents, []); self.assertTrue(rx)
                self.assertEqual(error.partial_receipt['local_display']['native_health_proved'], healthy)
                self.assertFalse(error.partial_receipt['proved'])
                self.assertEqual(candidate.observer.progress_projection(error.failed_audit),
                                 candidate.observer.replay_progress(self.codec, rx, tx, b'k'*32))


if __name__ == '__main__': unittest.main()
