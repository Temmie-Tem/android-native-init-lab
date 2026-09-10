"""Production factory, descriptor owner, raw writer and reader with a PTY peer."""
from contextlib import contextmanager, nullcontext
import copy
import errno
import fcntl
import hashlib
import os
from pathlib import Path
import signal
import termios
import time
import tty
from types import SimpleNamespace
import unittest
from unittest import mock

import test_s22plus_native_baseline_protocol_v1 as native
from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture, KEY, KEY_SHA256
import device_action_f1_live_v2 as live
from s22plus_native_departure_h0_support import Fixture as PlatformFixture


class BackendTests(native.ProtocolTests):
    # Reuse the real native producer fixture; these tests exercise the actual
    # factory/owner instead of the protocol fixture's manual reopen callback.
    test_clean_pty_detach_reopen_preserves_boot_preparation_and_raw_proof = None
    test_pair_control_and_optional_hud_failure_keep_exact_terminal_scope = None
    test_failed_health_nonce_or_expiry_never_emits_control_or_retries_auth = None
    test_authentication_limit_keeps_last_slot_for_control = None
    test_nonadjacent_nonce_reuse_stops_third_authentication = None

    def exercise(self, mode='pair-detach', fault=None, case='normal', *, prepared=None, external_peer=None):
        with (self.running(case) if external_peer is None else nullcontext(external_peer)) as peer:
            fixture = _ReceiptFixture.__new__(_ReceiptFixture)
            fixture.run_dir = peer.folder if prepared is None else prepared.run_dir
            run = fixture.run_dir
            fixture.variant = live.typed_evidence.SHELL_VARIANTS['p385']
            fixture.runtime = native.candidate.runtime
            fixture.observer = native.candidate.observer
            fixture.spec = live.typed_evidence._shell_observer_spec('p385')
            fixture.prepared = fixture._prepared() if prepared is None else prepared
            fixture._write_supporting_receipts()
            lane = fixture._lane()
            partner = dict(entry_dev=1,entry_ino=1,entry_ctime_ns=1,
                target_dev=1,target_ino=1,target_ctime_ns=1,target_sha256='a'*64)
            lane.update(partner_before=partner, partner_after=partner)
            fixture._lane = lambda: lane
            lane_binding = {'fixture':'current-lane'}
            lane_receipt = {'path':str(run/'lane.json'), 'size':1, 'sha256':'a'*64}
            if prepared is not None:
                lane_binding,lane_receipt=live._p324_typec_lane_value(prepared)
            baseline_path = run/'candidate-observer-baseline.json'
            baseline_path.unlink()
            baseline = dict(schema=live.cdc_acm_observer.BASELINE_SCHEMA,
                spec_sha256=live.cdc_acm_observer.digest(live._p327_inherited_spec(fixture.spec)),
                topology_sha256=hashlib.sha256(b'3-1.3').hexdigest(), identity_sha256=[], exact_candidate_absent=True)
            live.cdc_acm_observer.persist_json(baseline_path, baseline)
            inventory = copy.deepcopy(lane['end_inventory'])
            inventory['all_endpoint_count'] = 0; inventory['all_endpoint_identity_sha256'] = []
            candidate_row = inventory['rows'][live.p324_typec_lane.CANDIDATE_TOPOLOGY]
            candidate_row.update(endpoint_count=0, exact_candidate_count=0, candidate_like_count=0,
                endpoint_identity_sha256=[], present=False)
            arm = dict(schema=live.p324_cdc_observer.ARM_SCHEMA, contract_id=live.p324_cdc_observer.CONTRACT_ID,
                target=live.p324_cdc_observer.TARGET, lane_binding=lane_receipt,
                lane_binding_sha256=live.p324_cdc_observer._digest(lane_binding),
                source_topology=live.p324_typec_lane.SOURCE_TOPOLOGY, candidate_topology=live.p324_typec_lane.CANDIDATE_TOPOLOGY,
                selector_topology_count=1, partner_before=partner, inventory=inventory,
                both_topologies_inventory_complete=True, candidate_absent_on_both=True,
                candidate_like_absent_everywhere=True, opens_candidate_acm=False, device_commands=False)
            retained = live.native_baseline.guard.retained(live, fixture.prepared)
            if retained is not None:
                baseline.update(schema=live.native_baseline.guard.BASELINE_SCHEMA,
                    exact_candidate_absent=False, identity_sha256=['e'*64], retained_native=retained)
                baseline_path.unlink(); live.cdc_acm_observer.persist_json(baseline_path, baseline)
                arm.update(schema=live.native_baseline.guard.ARM_SCHEMA, candidate_absent_on_both=False,
                    candidate_like_absent_everywhere=False, inventory=copy.deepcopy(lane['end_inventory']), retained_native=retained)
            live.cdc_acm_observer.persist_json(run/live.p324_cdc_observer.ARM_NAME, arm)
            guard_path = run/'candidate-observer-guard.json'; guard_path.unlink()
            live.cdc_acm_observer.persist_json(guard_path, dict(schema=live.cdc_acm_observer.GUARD_SCHEMA,
                status='armed', spec_sha256='1'*64, topology_sha256='2'*64, rule_sha256='3'*64,
                instance_sha256='5'*64, output_sha256='6'*64, raw_capture_receipt={}, child_alive=True))
            path = Path(peer.name)
            base = SimpleNamespace(dev_root=path.parent,
                binding=live._candidate_observer_binding(fixture.prepared), _raw_tty=tty.setraw)
            inherited = SimpleNamespace(delegate=SimpleNamespace(delegate=base))
            platform = PlatformFixture(run/'native-platform')
            endpoint = platform.endpoint
            endpoint.tty_name = path.name
            endpoint.identity_sha256 = 'e'*64
            opens = []; closes = []; opened_fds = set(); real_open = os.open; real_close = os.close
            real_ioctl = fcntl.ioctl
            def opening(name, flags, *args, **kwargs):
                if Path(name) == path:
                    opens.append(flags)
                    if fault == 'reopen' and len(opens) == 2:
                        raise OSError(errno.EIO, 'fixture reopen cut')
                result = real_open(name, flags, *args, **kwargs)
                if Path(name) == path: opened_fds.add(result)
                return result
            def closing(fd):
                if fd in opened_fds:
                    closes.append(fd); opened_fds.remove(fd)
                    real_close(fd)
                    if fault == 'close': raise OSError(errno.EIO, 'fixture close uncertainty')
                    return
                return real_close(fd)
            def ioctl(fd, request, *args):
                if request == termios.TIOCEXCL and len(opens) == 2 and fault == 'exclusive':
                    raise OSError(errno.EIO, 'fixture exclusive cut')
                return real_ioctl(fd, request, *args)
            def exact(ep, fd=None):
                if fd is not None:
                    if os.fstat(fd).st_rdev != os.stat(path).st_rdev: return False
                    if peer.fd is not None:
                        fd0 = peer.fd; peer.fd = None; real_close(fd0)
                return not (fault == 'endpoint' and len(opens) == 2)
            @contextmanager
            def guard(*args, **kwargs):
                try: yield inherited
                finally:
                    live.cdc_acm_observer.persist_json(run/'candidate-observer-guard-release.json',
                        dict(schema=live.cdc_acm_observer.GUARD_SCHEMA,status='released',instance_sha256='5'*64,
                            released=True,returncode=0))
            writer = live.raw_capture.RawCaptureWriter(run, 'candidate-observer',
                stdout_maximum=fixture.observer.RAW_MAXIMUM, stderr_maximum=1,
                argv0_name='p385-real-owner-pty', stdout_name='candidate-observer.raw',
                stderr_name='candidate-observer.raw.stderr')
            patches = [mock.patch.object(live, '_p328_read_auth_key', return_value=(KEY, KEY_SHA256)),
                mock.patch.object(live.native_baseline, 'observer_session', side_effect=guard),
                mock.patch.object(live.native_usb_departure, '_snapshot', return_value=platform.snapshot),
                mock.patch.object(live._P345ObserverSession, '_lane_supplement', return_value=lane),
                mock.patch.object(os, 'open', side_effect=opening),
                mock.patch.object(os, 'close', side_effect=closing),
                mock.patch.object(fcntl, 'ioctl', side_effect=ioctl)]
            if prepared is None:
                patches.append(mock.patch.object(live.native_baseline,'mode',return_value=mode))
                patches.append(mock.patch.object(live,'_p324_typec_lane_value',return_value=(lane_binding,lane_receipt)))
            from contextlib import ExitStack
            with ExitStack() as stack:
                for patch in patches: stack.enter_context(patch)
                with live._p345_candidate_observer_session(fixture.prepared, fixture.spec,
                        lane_value={}, lane_receipt={}, usb_root=Path('/fixture'),
                        typec_root=Path('/fixture')) as session:
                    self.assertIsInstance(session, live._P385ObserverSession)
                    session._settle_guard_properties = lambda *_: None
                    session._endpoint_exact = exact
                    if fault == 'before-auth-expiry':
                        original_auth = session._baseline_before_auth
                        def expired_auth(index):
                            session.baseline_native_expiry_ns = live.native_baseline.protocol.host_now_ns()
                            return original_auth(index)
                        session._baseline_before_auth = expired_auth
                    if fault == 'write-budget-expiry':
                        original_write = session._baseline_write_budget
                        def expired_write():
                            session.baseline_observation_expiry_ns = live.native_baseline.protocol.host_now_ns()
                            return original_write()
                        session._baseline_write_budget = expired_write
                    classification = session._read_endpoint(endpoint, time.monotonic()+5, writer)
                    handle = writer.finalize(returncode=0)
                    fixture.capture_path = handle.receipt_path
                    fixture.payload = live.raw_capture.read_stdout(handle, maximum=fixture.observer.RAW_MAXIMUM)
                    result = session.qualification; error = session.qualification_error
                    audits = [s.session.audit for s in result.sessions] if result else [s.session.audit for s in error.completed_sessions]
                    if error is not None and error.failed_audit is not None: audits.append(error.failed_audit)
                    fixture.audits = audits; fixture.rx_streams = [bytes(a.rx) for a in audits]
                    fixture.tx_streams = [bytes(a.tx) for a in audits]; fixture.proof = session.proof
                    self.assertEqual(fixture.payload, b''.join(fixture.rx_streams))
                    value = fixture._receipt_value()
                    value.pop('p385_readonly_research_shell_qualification', None)
                    selected_lane = session._lane_supplement(classification == 'accepted')
                    value.update(accepted=classification == 'accepted', classification=classification, lane=selected_lane)
                    raw = live.p318_topology.raw_snapshot(phase='candidate_end', capture_complete=True, endpoints=[])
                    with mock.patch.object(live._P327ObserverSession, '_observe_value', return_value=(value, selected_lane)), \
                            mock.patch.object(live.p318_topology, 'capture_candidate_raw', return_value=raw):
                        value = session.observe(timeout_sec=5, download_departure={})
                    reopened = live._p345_validate_receipt(fixture.prepared,
                        fixture.run_dir/'candidate-observer.json', fixture.spec)
                    self.assertIsNone(session.owned_descriptor)
            return fixture, session, reopened, opens, closes

    def test_factory_real_pair_detach_and_control_reopen(self):
        for mode in ('pair-detach', 'pair-control'):
            with self.subTest(mode=mode):
                fixture, session, value, opens, closes = self.exercise(mode)
                if not value['accepted']:
                    raise AssertionError(repr(session.qualification_error.__cause__ if session.qualification_error else session.protocol_error))
                self.assertTrue(value['valid_receipt']); self.assertEqual(len(opens), 2)
                self.assertEqual(len(closes), 2); self.assertEqual(value['physical_reopen_count'], 1)
                self.assertIs(value['native_descriptor_close_completed'], mode == 'pair-detach')
                self.assertTrue(live._p345_proof_ok(value, prefix='p385'))

    def test_close_reopen_and_second_auth_cuts_preserve_raw_and_no_control(self):
        for fault, case in (('close', 'normal'), ('reopen', 'normal'), ('exclusive', 'normal'),
                            ('endpoint', 'normal'), (None, 'same-nonce'), (None, 'bad-health')):
            with self.subTest(fault=fault, case=case):
                fixture, session, value, opens, closes = self.exercise('pair-control', fault, case)
                self.assertFalse(value['accepted']); self.assertTrue(fixture.payload)
                self.assertFalse(value.get('control_acceptance_observed'))
                self.assertFalse((fixture.run_dir/native.candidate.return_host.INTENT_NAME).exists())
                self.assertLessEqual(len(opens), 2); self.assertLessEqual(len(closes), 2)

    def test_expiry_before_auth_or_first_wire_write_preserves_zero_delivery_failure(self):
        for fault in ('before-auth-expiry', 'write-budget-expiry'):
            with self.subTest(fault=fault):
                fixture, session, value, opens, closes = self.exercise('pair-detach', fault)
                self.assertFalse(value['accepted'])
                self.assertEqual(fixture.payload, b'')
                self.assertEqual(b''.join(fixture.tx_streams), b'')
                self.assertEqual(len(opens), 1)
                self.assertEqual(len(closes), 1)
                self.assertFalse((fixture.run_dir/native.candidate.return_host.INTENT_NAME).exists())
                self.assertIs((fixture.run_dir/'p385-native-auth-01.intent.json').exists(),
                              fault == 'write-budget-expiry')


if __name__ == '__main__': unittest.main()
