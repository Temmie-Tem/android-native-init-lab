"""Actual P384 observer factory and strict key reader; guard/hardware are fixtures."""
import contextlib
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

import test_device_action_f1_live_v2 as generic
import test_s22plus_fyg8_p384_lifecycle as ordinary
import test_s22plus_fyg8_p384_roundtrip as roundtrip

live = ordinary.live
KEY = b'P384-startup-fixture-key-only!!!'
KEY_PIN = dict(size=len(KEY), sha256=hashlib.sha256(KEY).hexdigest())


class Startup(unittest.TestCase):
    def prepared(self, followup=False):
        prepared = (roundtrip.Roundtrip.prepared(self) if followup
                    else ordinary.Lifecycle.prepared(self))
        self.assertEqual(len(KEY), 32)
        prepared.prepared['p384_auth_key_identity'] = dict(KEY_PIN)
        prepared.prepared['approval_binding']['p384_auth_key_identity'] = dict(KEY_PIN)
        path = prepared.run_dir / 'fixture-key.bin'
        path.write_bytes(KEY); path.chmod(0o400)
        return prepared, path

    def backend(self, prepared):
        # Only constructor setup is a fixture. The actual backend method,
        # variant selection, plan sealing, key reader and session class run.
        backend = live.SamsungOdinBackend.__new__(live.SamsungOdinBackend)
        backend.usb_root = prepared.run_dir / 'fixture-usb'
        backend.typec_root = prepared.run_dir / 'fixture-typec'
        backend.root_console_plan = None
        return backend

    def hardware(self, key_path, calls, *, guard_error=None):
        @contextlib.contextmanager
        def guard(*args, **kwargs):
            calls.append('guard-enter')
            if guard_error is not None: raise guard_error
            try: yield SimpleNamespace(delegate=SimpleNamespace(delegate=object()))
            finally: calls.append('guard-exit')
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(live, 'P328_AUTH_KEY_PATH', key_path))
        stack.enter_context(mock.patch.object(live, '_p324_typec_lane_value',
            return_value=({'accepted_for_p324': True}, {'fixture': True})))
        stack.enter_context(mock.patch.object(live.p325_guard_adapter, 'observer_session',
            side_effect=guard))
        return stack

    def test_real_factory_reads_key_and_builds_ordinary_and_v2_sessions(self):
        for followup in (False, True):
            with self.subTest(followup=followup):
                prepared, key_path = self.prepared(followup); calls = []
                backend = self.backend(prepared)
                with self.hardware(key_path, calls), \
                        backend.candidate_observer_session(prepared) as session:
                    self.assertIsInstance(session, live._P375ObserverSession)
                    self.assertEqual(session.namespace, 'p384')
                    self.assertEqual(session.auth_key, KEY)
                    self.assertEqual(session.auth_key_sha256, KEY_PIN['sha256'])
                    registered = live.typed_evidence.SHELL_VARIANTS['p384']
                    self.assertIs(session.qualification_observer, registered.observer)
                    self.assertIs(session.auth_runtime, registered.runtime)
                    self.assertEqual(session.root_console_plan_value['commands'], [])
                    if followup:
                        self.assertEqual(session.native_transaction.run_dir, prepared.run_dir)
                    else: self.assertIsNone(session.native_transaction)
                    self.assertIsNone(session.native_previous)
                self.assertEqual(calls, ['guard-enter', 'guard-exit'])
                for path in prepared.run_dir.glob('*.json'):
                    serialized = path.read_bytes()
                    self.assertNotIn(KEY, serialized)
                    self.assertNotIn(KEY.hex().encode(), serialized)
                    self.assertNotIn(str(key_path).encode(), serialized)

    def test_invalid_fixed_key_stops_real_factory_before_guard(self):
        for case in ('missing', 'bad-mode', 'symlink', 'hardlink', 'short', 'wrong-key'):
            with self.subTest(case=case):
                prepared, path = self.prepared(); calls = []
                if case == 'missing': path.unlink()
                elif case == 'bad-mode': path.chmod(0o600)
                elif case == 'symlink':
                    target = path.with_name('fixture-key-target.bin')
                    path.rename(target); path.symlink_to(target)
                elif case == 'hardlink': os.link(path, path.with_name('fixture-key-link.bin'))
                else:
                    path.chmod(0o600)
                    path.write_bytes(KEY[:-1] if case == 'short' else b'X' * 32)
                    path.chmod(0o400)
                with self.hardware(path, calls), self.assertRaises(live.F1LiveError):
                    with self.backend(prepared).candidate_observer_session(prepared):
                        self.fail('invalid key opened observer')
                self.assertEqual(calls, [])
                self.assertFalse((prepared.run_dir / 'candidate-observer.json').exists())

    def test_actual_factory_failures_abort_owner_without_download_or_claim(self):
        class Backend(generic.FakeBackend):
            def __init__(self, prepared):
                super().__init__(live)
                self.usb_root = prepared.run_dir / 'fixture-usb'
                self.typec_root = prepared.run_dir / 'fixture-typec'
                self.root_console_plan = None

            candidate_observer_session = live.SamsungOdinBackend.candidate_observer_session

        for case in ('wrong-key', 'guard-start'):
            with self.subTest(case=case):
                prepared, path = self.prepared(followup=True); calls = []
                if case == 'wrong-key':
                    path.chmod(0o600); path.write_bytes(b'X' * 32); path.chmod(0o400)
                backend = Backend(prepared)
                with self.hardware(path, calls, guard_error=(
                        live.cdc_acm_observer.ObserverError('fixture guard startup failed')
                        if case == 'guard-start' else None)):
                    result = live.execute_prepared(prepared, prepared.approval_token, backend)
                self.assertEqual(result['verdict'], 'FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD')
                self.assertEqual(result['current_state'], 'ABORTED')
                self.assertFalse(result['recovery_required'])
                self.assertEqual(backend.calls, ['recheck'])
                self.assertEqual(calls, ['guard-enter'] if case == 'guard-start' else [])
                self.assertFalse((prepared.root / live.native_roundtrip.FOLLOWUP.claim).exists())
                for name in ('candidate-download-request-intent.json',
                             'candidate-attempt-01.start.json', 'rollback-attempt-01.start.json'):
                    self.assertFalse((prepared.run_dir / name).exists())
                journal = prepared.run_dir / 'transaction' / 'journal'
                before = {p.name: p.read_bytes() for p in journal.iterdir()}
                with self.assertRaises(live.F1LiveError):
                    live.execute_prepared(prepared, prepared.approval_token, backend)
                self.assertEqual(before, {p.name: p.read_bytes() for p in journal.iterdir()})
                self.assertEqual(backend.calls, ['recheck'])


if __name__ == '__main__': unittest.main()
