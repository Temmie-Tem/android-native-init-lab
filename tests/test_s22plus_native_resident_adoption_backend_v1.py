"""Real factory/owner/PTY/raw replay; USB identity and privileged guard are fixtures."""
from contextlib import ExitStack,contextmanager,nullcontext
import copy
import errno
import fcntl
import os
from pathlib import Path
import termios
import time
import tty
from types import SimpleNamespace
import unittest
from unittest import mock

import s22plus_resident_adoption_h0_support as support
from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture,KEY,KEY_SHA256
from s22plus_native_departure_h0_support import Fixture as Platform
import device_action_f1_live_v2 as live
import s22plus_native_resident_backend_v1 as backend


class BackendTests(support.Fixture,unittest.TestCase):
    @classmethod
    def setUpClass(cls):support.compile_components(cls)

    @contextmanager
    def owned_session(self,case='normal',fault=None,*,prepared=None):
        with self.running(case,prepared.run_dir if prepared is not None else None) as peer:
            self.last_guard_folder=peer.folder
            fixture=_ReceiptFixture.__new__(_ReceiptFixture);fixture.run_dir=peer.folder
            fixture.variant=live.typed_evidence.SHELL_VARIANTS['p386']
            fixture.runtime=support.candidate.runtime;fixture.observer=support.candidate.observer
            fixture.spec=live.typed_evidence._shell_observer_spec('p386')
            fixture.prepared=fixture._prepared() if prepared is None else prepared
            fixture.prepared.bundle.manifest['observation']['timeout_sec']=2100
            fixture.prepared.prepared['approval_binding']['resident_guard_lifetime']=backend.guard_derivation(live,fixture.prepared.bundle)
            live.cdc_acm_observer.persist_json(peer.folder/'candidate-observer-baseline.json',{'baseline':'fixture-absent'})
            lane=fixture._lane();partner=dict(entry_dev=1,entry_ino=1,entry_ctime_ns=1,target_dev=1,
                target_ino=1,target_ctime_ns=1,target_sha256='a'*64)
            lane.update(partner_before=partner,partner_after=partner)
            platform=Platform(peer.folder/'native-platform');endpoint=platform.endpoint
            path=Path(peer.name);endpoint.tty_name=path.name;endpoint.identity_sha256='e'*64
            guard=SimpleNamespace(max_sec=0,healthy=lambda **kw:fault!='arm-unhealthy' and
                (fault!='guard-loss' or peer.offset_ms==0),matches_node=lambda _:True)
            base=live.cdc_acm_observer.ObserverSession(spec=live._p327_inherited_spec(fixture.spec),
                topology=live.p324_typec_lane.CANDIDATE_TOPOLOGY,run_dir=peer.folder,
                binding=live._candidate_observer_binding(fixture.prepared),baseline={},baseline_receipt={},
                guard=guard,guard_receipt={},class_tty=path.parent,dev_root=path.parent)
            # Use the production wrappers. Only the underlying hardware seam
            # is synthetic; P324 deliberately exposes no top-level guard.
            p324=live.p325_guard_adapter.p324.P324ObserverSession(base,{},peer.folder,{}, {},{}, {},partner,
                path.parent,Path('/fixture'),Path('/fixture'))
            p324._select=lambda:('identity-mismatch',None) if fault=='idle-endpoint' and peer.offset_ms else ('accepted',endpoint)
            inherited=live.p325_guard_adapter.P325ObserverSession(p324,live.p325_guard_adapter.GuardProbeAudit())
            opens=[];closes=[];owned=set();real_open=os.open;real_close=os.close;real_ioctl=fcntl.ioctl
            def opening(name,flags,*args,**kwargs):
                if Path(name)==path:
                    opens.append(flags)
                    if fault=='reopen' and len(opens)==2:raise OSError(errno.EIO,'reopen cut')
                fd=real_open(name,flags,*args,**kwargs)
                if Path(name)==path:owned.add(fd)
                return fd
            def closing(fd):
                if fd in owned:
                    owned.remove(fd);closes.append(fd);real_close(fd)
                    if fault=='close' or fault=='final-close' and len(opens)==4:raise OSError(errno.EIO,'close cut after actual close')
                else:real_close(fd)
            def ioctl(fd,request,*args):
                if request==termios.TIOCEXCL and len(opens)==2 and fault=='exclusive':raise OSError(errno.EIO,'exclusive cut')
                return real_ioctl(fd,request,*args)
            def exact(ep,fd=None):
                if fd is not None:
                    if os.fstat(fd).st_rdev!=os.stat(path).st_rdev:return False
                    if peer.fd is not None:real_close(peer.fd);peer.fd=None
                return not (fault=='reopen-endpoint' and len(opens)==2)
            @contextmanager
            def guard_context(*args,max_sec,**kwargs):
                guard.max_sec=max_sec-1 if fault=='arm-max-sec' else max_sec
                live.cdc_acm_observer.persist_json(peer.folder/'candidate-observer-guard.json',dict(
                    schema=live.cdc_acm_observer.GUARD_SCHEMA,status='armed',spec_sha256='1'*64,topology_sha256='2'*64,
                    rule_sha256='3'*64,instance_sha256='5'*64,output_sha256='6'*64,raw_capture_receipt={},child_alive=True))
                try:yield inherited
                finally:live.cdc_acm_observer.persist_json(peer.folder/'candidate-observer-guard-release.json',dict(
                    schema=live.cdc_acm_observer.GUARD_SCHEMA,status='released',instance_sha256='5'*64,released=True,returncode=0))
            real_now=backend.protocol.host_now_ns
            def idle(seconds):
                self.advance(peer,2200000 if fault=='expiry' else max(1,int(seconds*1000)))
            raw_snapshot=live.p318_topology.raw_snapshot(phase='candidate_end',capture_complete=True,endpoints=[])
            with ExitStack() as stack:
                for patch in (
                    mock.patch.object(live,'_p328_read_auth_key',return_value=(KEY,KEY_SHA256)),
                    mock.patch.object(live.p325_guard_adapter,'observer_session',side_effect=guard_context),
                    mock.patch.object(live.native_usb_departure,'_snapshot',return_value=platform.snapshot),
                    mock.patch.object(live.p318_topology,'capture_candidate_raw',return_value=raw_snapshot),
                    mock.patch.object(live,'_p324_typec_lane_value',return_value=({},{})),
                    mock.patch.object(live._P345ObserverSession,'_lane_supplement',return_value=lane),
                    mock.patch.object(backend.protocol,'host_now_ns',side_effect=lambda:real_now()+peer.offset_ms*10**6),
                    mock.patch.object(backend,'idle_wait',side_effect=idle),
                    mock.patch.object(os,'open',side_effect=opening),mock.patch.object(os,'close',side_effect=closing),
                    mock.patch.object(fcntl,'ioctl',side_effect=ioctl)):
                    stack.enter_context(patch)
                adapter=live.SamsungOdinBackend.__new__(live.SamsungOdinBackend)
                adapter.usb_root=Path('/fixture');adapter.typec_root=Path('/fixture');adapter.root_console_plan=None
                with adapter.candidate_observer_session(fixture.prepared) as session:
                    self.assertIsInstance(session,live._P386ObserverSession)
                    session._endpoint_exact=exact;session._settle_guard_properties=lambda *_:None
                    if fault=='write-expiry':
                        budget=session._resident_budget
                        def expired_budget(*,session=True):
                            if session: self.advance(peer,2200000)
                            return budget(session=session)
                        session._resident_budget=expired_budget
                    yield fixture,session
                    self.assertIsNone(session.owned_descriptor);self.assertFalse(owned)
                if fault!='expiry' and fault!='write-expiry':backend.validate_guard_release(live,fixture.prepared)
                raw=(peer.folder/'candidate-observer.raw').read_bytes()
                audits=[s.session.audit for s in session.qualification.sessions] if session.qualification else list(
                    s.session.audit for s in getattr(session.qualification_error,'completed_sessions',()))
                failed=getattr(session.qualification_error,'failed_audit',None)
                if failed is not None:audits.append(failed)
                self.assertEqual(raw,b''.join(bytes(a.rx) for a in audits))
                # Keep exact evidence for corruption/reopen checks before the
                # fixture directory is cleaned by the parent TestCase.
                fixture.session=session;fixture.opens=opens;fixture.closes=closes
                fixture.raw=raw;fixture.marks=(peer.folder/'marks').read_text()

    def exercise(self,case='normal',fault=None,*,prepared=None):
        with self.owned_session(case,fault,prepared=prepared) as (fixture,session):
            session.observe(timeout_sec=2100,download_departure=dict(download_endpoint_absent=True,absence_timed_out=False,sequence=1))
            fixture.proof=session.proof
            fixture.value=live._p345_validate_receipt(fixture.prepared,fixture.run_dir/'candidate-observer.json',fixture.spec)
        return fixture

    def test_actual_factory_four_opens_closes_and_retained_owner_replay(self):
        fixture=self.exercise();value=fixture.value
        if not value['accepted']:raise AssertionError({'cause':repr(fixture.session.qualification_error.__cause__),
            'probes':[row['probe'] for row in fixture.session.qualification_error.partial_receipt['sessions']],
            'log':(fixture.run_dir/'hud.log').read_text()[-3000:]})
        self.assertTrue(value['valid_receipt']);self.assertTrue(value['proof']['proved'])
        self.assertEqual(len(fixture.opens),4);self.assertEqual(len(fixture.closes),4)
        self.assertEqual(value['physical_reopen_count'],3);self.assertFalse(value['same_tty_fd'])
        self.assertEqual(fixture.marks.count('download 0'),1)
        path=fixture.run_dir/backend.name(2,'close-result');raw=path.read_bytes()
        import json
        changed=json.loads(raw);changed['closed']=False;path.chmod(0o600);path.write_text(json.dumps(changed))
        with self.assertRaises(live.F1LiveError):backend.validate_ownership(live,fixture.prepared,value,value['proof'])
        path.write_bytes(raw);path.chmod(0o400)

    def test_real_wrapper_arm_rejects_wrong_lifetime_and_unhealthy_base_guard(self):
        for fault in ('arm-max-sec','arm-unhealthy'):
            with self.subTest(fault=fault),self.assertRaisesRegex(live.F1LiveError,'guard actual lifetime differs'):
                with self.owned_session(fault=fault):self.fail('invalid guard was yielded')
            folder=self.last_guard_folder
            release=live._read_json(folder/'candidate-observer-guard-release.json','fixture guard release')
            self.assertTrue(release['released']);self.assertEqual(release['returncode'],0)
            self.assertFalse((folder/backend.GUARD_ARM).exists())
            self.assertFalse((folder/'p386-resident-auth-01.auth-intent.json').exists())

    def test_middle_failure_closes_only_the_current_owned_descriptor(self):
        for fault,attempted,closed in (('reopen',2,1),('exclusive',2,2),('reopen-endpoint',2,2),('close',1,1),
                                      ('idle-endpoint',1,1),('guard-loss',1,1),('expiry',1,1),('write-expiry',1,1)):
            with self.subTest(fault=fault):
                fixture=self.exercise(fault=fault)
                self.assertFalse(fixture.value['accepted']);self.assertFalse(fixture.value['qualification_complete'])
                self.assertEqual(len(fixture.opens),attempted);self.assertEqual(len(fixture.closes),closed)
                self.assertNotIn('download 0',fixture.marks)
                self.assertLessEqual(fixture.value['session_count'],1)


if __name__=='__main__':unittest.main()
