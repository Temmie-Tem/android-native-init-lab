"""Finite authority and actual common-runner journal/rollback integration."""
import contextlib
from dataclasses import replace
from pathlib import Path
import time
import unittest
from unittest import mock

from tests import test_device_action_f1_live_v2 as baseline
FakeBackend=baseline.FakeBackend


class AttendedSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline.DeviceActionF1LiveV2Test.setUpClass()
        cls.live = baseline.DeviceActionF1LiveV2Test.module
        cls.session = cls.live.attended_f1

    def setUp(self):
        fixture = baseline.DeviceActionF1LiveV2Test()
        temp, prepared = fixture.prepared()
        self.addCleanup(temp.cleanup)
        path = prepared.root/'workspace/private/run-one'
        prepared.run_dir.rename(path)
        self.p = replace(prepared, run_dir=path)
        s = self.session
        self.patch = contextlib.ExitStack()
        self.addCleanup(self.patch.close)
        self.patch.enter_context(mock.patch.object(s, 'reviewed', return_value='a'*64))
        self.entry = dict(manifest='manifest.json', manifest_sha256='b'*64, review='workspace/private/review.json',
                          review_sha256='c'*64, bundle_sha256=self.p.bundle.sha256,
                          closure_sha256='d'*64, candidate={'sha256':'e'*64}, rollback={'sha256':'f'*64})
        self.patch.enter_context(mock.patch.object(s, 'catalog_entry', return_value=self.entry))
        folder = self.p.root/s.BASE/'fixed'
        folder.mkdir(parents=True)
        self.grant = folder/'grant.json'
        now = time.monotonic_ns()
        self.g = dict(schema=s.SCHEMA, goal='fixed two-step batch', target={k:self.p.private_target[k] for k in ('serial','topology')},
                      review_sha256='a'*64, authority='explicit-operator-attended-session', unattended=False,
                      host_boot=s.host_boot(), started_ns=now, deadline_ns=now+10**12,
                      reservations=3, catalog=[self.entry])
        s.publish(self.grant,self.g)

    def rewrite_grant(self, **changes):
        self.grant.unlink()
        self.g.update(changes)
        self.session.publish(self.grant,self.g)

    def reserve(self):
        with self.live.consumed_registry.target_session_lease(self.p.root):
            return self.session.reserve(self.live,self.p,self.grant,attended=True)

    def test_actual_common_execute_attributes_grant_and_reopens_result(self):
        result=self.live.execute_attended_session(self.p,self.grant,FakeBackend(self.live),attended=True)
        self.live.validate_live_result(result,self.p)
        journal=self.live.core.Journal.reopen(self.p.run_dir/'transaction',self.p.binding_sha256)
        approved=[r for r in journal.records() if r['state']=='APPROVED' and r['kind']=='transition'][0]
        self.assertEqual(approved['details']['authorization_kind'],'attended_session')
        self.assertEqual(approved['details']['session_ordinal'],1)
        self.assertEqual(result['current_state'],'CLOSED')
        self.assertTrue(self.session.immutable(self.grant.parent/'01-completed.json')[0]['eligible'])
        self.session.close(self.p.root,self.grant,'withdrawn')
        # Historical result/recovery do not require an active grant or review.
        with mock.patch.object(self.session,'reviewed',side_effect=AssertionError('must not reauthorize recovery')):
            self.live.validate_live_result(result,self.p)
            again=self.live.recover_prepared(self.p,FakeBackend(self.live))
            self.assertEqual(again,result)

    def test_completed_result_publication_cut_reconciles_without_device_replay(self):
        original=self.session.publish
        def cut(path,value):
            if path.name.endswith('-completed.json'):raise OSError('injected completion publication cut')
            original(path,value)
        with mock.patch.object(self.session,'publish',side_effect=cut),self.assertRaises(OSError):
            self.live.execute_attended_session(self.p,self.grant,FakeBackend(self.live),attended=True)
        self.assertTrue((self.grant.parent/'closed.json').exists())
        self.assertFalse((self.grant.parent/'01-completed.json').exists())
        backend=FakeBackend(self.live)
        with mock.patch.object(self.session,'reviewed',side_effect=AssertionError('recovery must not reauthorize')):
            result=self.live.recover_prepared(self.p,backend)
        self.assertEqual(result['current_state'],'CLOSED')
        self.assertTrue((self.grant.parent/'01-completed.json').exists())
        self.assertEqual(backend.calls,[])

    def test_hard_device_cut_closes_grant_before_recovery_effect(self):
        backend=FakeBackend(self.live)
        with mock.patch.object(backend,'observe_candidate',side_effect=KeyboardInterrupt('hard process cut')),self.assertRaises(KeyboardInterrupt):
            self.live.execute_attended_session(self.p,self.grant,backend,attended=True)
        self.assertFalse((self.grant.parent/'closed.json').exists())
        self.assertTrue((self.p.run_dir/'candidate-download-request-intent.json').exists())
        recovery=FakeBackend(self.live)
        transfer=recovery.transfer
        def checked(*args,**kwargs):
            self.assertTrue((self.grant.parent/'closed.json').exists())
            return transfer(*args,**kwargs)
        with mock.patch.object(recovery,'transfer',side_effect=checked):
            result=self.live.recover_prepared(self.p,recovery)
        self.assertEqual(result['current_state'],'CLOSED')
        self.assertFalse(result['recovery_required'])
        self.assertEqual(self.session.immutable(self.grant.parent/'closed.json')[0]['reason'],'interrupted-device-session-recovery')

    def test_late_recovery_pass_cannot_reopen_interrupted_batch(self):
        later=dict(self.entry,manifest='second.json',bundle_sha256='f'*64)
        self.rewrite_grant(catalog=[self.entry,later])
        backend=FakeBackend(self.live)
        with mock.patch.object(backend,'verify_final',side_effect=KeyboardInterrupt('hard health-phase cut')),self.assertRaises(KeyboardInterrupt):
            self.live.execute_attended_session(self.p,self.grant,backend,attended=True)
        self.assertFalse((self.grant.parent/'closed.json').exists())
        recovery=FakeBackend(self.live);verify=recovery.verify_final
        def checked(*args,**kwargs):
            self.assertTrue((self.grant.parent/'closed.json').exists())
            return verify(*args,**kwargs)
        with mock.patch.object(recovery,'verify_final',side_effect=checked):
            result=self.live.recover_prepared(self.p,recovery)
        self.assertTrue(result['verdict'].startswith('PASS_'))
        self.assertEqual(self.session.immutable(self.grant.parent/'closed.json')[0]['reason'],'interrupted-device-session-recovery')

    def test_legacy_execute_cannot_reuse_session_reservation(self):
        self.reserve()
        with self.assertRaises((self.live.F1LiveError,self.session.SessionError)):
            self.live.execute_prepared(self.p,self.p.approval_token,FakeBackend(self.live))
        self.assertFalse((self.p.run_dir/'transaction').exists())

    def test_reservation_cut_blocks_next_and_never_reuses_ordinal(self):
        original=self.session.publish
        def cut(path,value):
            if path.name==self.session.AUTH_FILE:raise OSError('injected publication cut')
            original(path,value)
        with mock.patch.object(self.session,'publish',side_effect=cut),self.assertRaises(OSError):self.reserve()
        self.assertTrue((self.grant.parent/'01-reserved.json').exists())
        with self.assertRaisesRegex(self.session.SessionError,'authoritative'):self.reserve()
        with self.assertRaises(self.session.SessionError):
            self.live.execute_prepared(self.p,self.p.approval_token,FakeBackend(self.live))
        self.assertFalse((self.p.run_dir/'transaction').exists())
        self.assertFalse((self.grant.parent/'02-reserved.json').exists())

    def test_expiry_withdrawal_host_change_and_attendance_reject_before_reservation(self):
        for case in ('expired','host','withdrawn','attendance'):
            with self.subTest(case=case):
                if case=='expired': patch=mock.patch.object(self.session.time,'monotonic_ns',return_value=self.g['deadline_ns'])
                elif case=='host':patch=mock.patch.object(self.session,'host_boot',return_value='another-boot')
                elif case=='withdrawn':
                    self.session.close(self.p.root,self.grant,'stop');patch=contextlib.nullcontext()
                else:
                    (self.grant.parent/'closed.json').unlink();patch=contextlib.nullcontext()
                with patch,self.assertRaises(self.session.SessionError):
                    self.session.reserve(self.live,self.p,self.grant,attended=case!='attendance')
                self.assertFalse((self.grant.parent/'01-reserved.json').exists())

    def test_bool_limit_and_changed_target_reject(self):
        self.rewrite_grant(reservations=True)
        with self.assertRaises(self.session.SessionError):self.reserve()
        self.rewrite_grant(reservations=3,target={'serial':'different','topology':'different'})
        with self.assertRaisesRegex(self.session.SessionError,'target'):self.reserve()

    def test_withdraw_during_observer_arm_aborts_before_download(self):
        backend=FakeBackend(self.live)
        original=backend.candidate_observer_session
        @contextlib.contextmanager
        def arm(prepared):
            with original(prepared) as observer:
                self.session.close(prepared.root,self.grant,'operator-stop')
                yield observer
        with mock.patch.object(backend,'candidate_observer_session',side_effect=arm):
            result=self.live.execute_attended_session(self.p,self.grant,backend,attended=True)
        self.assertEqual(result['current_state'],'ABORTED')
        self.assertFalse((self.p.run_dir/'candidate-download-request-intent.json').exists())
        self.assertFalse(result['recovery_required'])

    def test_foreign_authority_and_record_tamper_reject(self):
        self.reserve()
        auth=self.p.run_dir/self.session.AUTH_FILE
        value,_=self.session.immutable(auth)
        auth.unlink();value['ordinal']=2;self.session.publish(auth,value)
        with self.assertRaises(self.live.core.F1V2Error):self.session.authorization(self.p)

    def test_cli_cannot_mix_session_and_legacy_authority(self):
        self.assertEqual(self.live.main(['--execute-session','--approval','fake']),2)
        self.assertEqual(self.live.main(['--validate','--attended']),2)

    def test_fixed_catalog_order_rejects_later_experiment(self):
        prior=dict(self.entry,manifest='first.json',bundle_sha256='f'*64)
        self.rewrite_grant(catalog=[prior,self.entry])
        with self.assertRaisesRegex(self.session.SessionError,'catalog order'):self.reserve()
        self.assertFalse((self.grant.parent/'01-reserved.json').exists())

    def test_pre_effect_abort_allows_fresh_same_candidate_with_remaining_budget(self):
        backend=FakeBackend(self.live)
        with mock.patch.object(backend,'candidate_observer_session',side_effect=OSError('fixture guard unavailable')):
            first=self.live.execute_attended_session(self.p,self.grant,backend,attended=True)
        self.assertEqual(first['current_state'],'ABORTED')
        self.assertFalse((self.grant.parent/'closed.json').exists())
        run=self.p.root/'workspace/private/run-two';run.mkdir()
        fresh=replace(self.p,run_dir=run,prepared=dict(self.p.prepared,approval_binding_sha256='9'*64))
        with mock.patch.object(self.live,'load_prepared',return_value=self.p):
            second=self.live.execute_attended_session(fresh,self.grant,FakeBackend(self.live),attended=True)
        self.assertEqual(second['current_state'],'CLOSED')
        self.assertEqual(self.session.authorization(fresh)['ordinal'],2)
        self.assertTrue((self.grant.parent/'closed.json').exists())
        self.assertFalse((self.p.run_dir/'candidate-download-request-intent.json').exists())

    def test_concurrent_reservation_has_one_winner(self):
        import concurrent.futures,threading
        barrier=threading.Barrier(2)
        def attempt():
            barrier.wait(timeout=3)
            try:self.reserve();return True
            except (self.session.SessionError,self.live.consumed_registry.RegistryError):return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:attempt(),range(2)))
        self.assertEqual(sum(results),1)
        self.assertFalse((self.grant.parent/'02-reserved.json').exists())

    def test_cross_grant_prior_reservation_rejects_before_following_run(self):
        wrong=dict(grant_sha256='0'*64,ordinal=1,binding_sha256='1'*64,run_dir='workspace/private/other-run',manifest='other.json')
        self.session.publish(self.grant.parent/'01-reserved.json',wrong)
        self.session.publish(self.grant.parent/'01-completed.json',{})
        with mock.patch.object(self.live,'load_prepared',side_effect=AssertionError('must reject before opening run')):
            with self.assertRaisesRegex(self.session.SessionError,'another grant'):self.reserve()

    def test_budget_exhaustion_never_creates_next_reservation(self):
        self.rewrite_grant(reservations=1)
        digest=self.session.immutable(self.grant)[1]
        old=dict(grant_sha256=digest,ordinal=1,binding_sha256='1'*64,run_dir='workspace/private/other-run',manifest=self.entry['manifest'])
        self.session.publish(self.grant.parent/'01-reserved.json',old)
        self.session.publish(self.grant.parent/'01-completed.json',{})
        with mock.patch.object(self.live,'load_prepared',return_value=self.p),mock.patch.object(self.session,'read',wraps=self.session.read) as reader,mock.patch.object(self.session,'finish',return_value=True):
            original=reader._mock_wraps
            reader.side_effect=lambda path:({'current_state':'CLOSED'},'d'*64) if path.name=='live-result.json' else original(path)
            with self.assertRaisesRegex(self.session.SessionError,'budget'):self.reserve()
        self.assertFalse((self.grant.parent/'02-reserved.json').exists())


class CatalogValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline.DeviceActionF1LiveV2Test.setUpClass();cls.live=baseline.DeviceActionF1LiveV2Test.module;cls.s=cls.live.attended_f1
    def setUp(self):
        import tempfile,types
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'workspace/private').mkdir(parents=True)
        self.live.consumed_registry.initialize(self.root)
        (self.root/'engine.py').write_text('fixed reviewed engine')
        self.manifest=self.root/'manifest.json';self.manifest.write_text('{}')
        engine=self.s.identity(self.root/'engine.py');engine['path']='engine.py'
        static=self.root/'workspace/private/static.json';self.s.publish(static,{'source_closure':{'engine':engine}})
        sr=self.s.identity(static);sr['path']=str(static.relative_to(self.root))
        self.review=self.root/'workspace/private/review.json'
        self.review_value=dict(verdict='PASS_GO',findings=[],current_sources={'engine':engine},static_result=sr,
            execution_closure_binding=dict(record=sr,field='source_closure',canonical_sha256=self.live.core.json_sha256({'engine':engine})),candidate_ap={'size':4,'sha256':'b'*64})
        self.s.publish(self.review,self.review_value)
        manifest=dict(target_profile=self.s.PROFILE,status='ready-for-f1-approval',
            observation={'candidate_observer':{'mandatory_rollback':True,'control_mode':'download'},'acceptance':{'contract':{'candidate_static':sr}}},
            candidate_ap={'path':'workspace/private/ap','size':4,'sha256':'b'*64},rollback_ap={'path':'workspace/private/rollback','size':4,'sha256':'c'*64})
        self.bundle=types.SimpleNamespace(manifest=manifest,sha256='a'*64)
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(self.live.core,'verify_bundle',return_value=self.bundle))
        self.stack.enter_context(mock.patch.object(self.live,'_closure',return_value={'engine':engine}))
    def entry(self):return self.s.catalog_entry(self.live,self.root,self.manifest,self.review)
    def test_real_review_file_static_and_source_joins(self):
        self.assertEqual(self.entry()['bundle_sha256'],'a'*64)
        (self.root/'engine.py').write_text('drift')
        with self.assertRaisesRegex(self.s.SessionError,'changed'):self.entry()
    def test_review_wrong_ap_static_and_verdict_reject(self):
        import copy
        for key,value in [('candidate_ap',{'size':4,'sha256':'f'*64}),('static_result',{}),('verdict','BLOCKED')]:
            with self.subTest(key=key):
                self.review.unlink();v=copy.deepcopy(self.review_value);v[key]=value;self.s.publish(self.review,v)
                with self.assertRaises(self.s.SessionError):self.entry()
    def test_duplicate_json_and_symlink_reject(self):
        self.review.unlink();self.review.write_text('{"verdict":"PASS_GO","verdict":"BLOCKED"}')
        with self.assertRaises(self.live.core.F1V2Error):self.entry()
        self.review.unlink();self.review.symlink_to(self.manifest)
        with self.assertRaises(self.live.core.F1V2Error):self.entry()


class ActivationGateTests(CatalogValidationTests):
    test_real_review_file_static_and_source_joins=None
    test_review_wrong_ap_static_and_verdict_reject=None
    test_duplicate_json_and_symlink_reject=None
    def test_missing_or_stale_activation_never_opens_a_grant(self):
        with self.assertRaises(self.live.core.F1V2Error):self.s.reviewed(self.root)
        self.assertFalse((self.root/self.s.BASE).exists())
        with mock.patch.object(self.s,'SOURCES',[Path('engine.py')]):
            cap=self.root/self.s.REVIEW;cap.parent.mkdir(parents=True)
            value=dict(verdict='PASS_GO',findings=[],sources=self.s.sources(self.root),limits={'reservations':3,'seconds':7200},activation=self.s.SCHEMA)
            self.s.publish(cap,value)
            self.assertEqual(self.s.reviewed(self.root),self.s.identity(cap)['sha256'])
            (self.root/'engine.py').write_text('changed engine')
            with self.assertRaisesRegex(self.s.SessionError,'source changed'):self.s.reviewed(self.root)
    def test_actual_grant_open_uses_review_catalog_limits_and_target(self):
        with mock.patch.object(self.s,'SOURCES',[Path('engine.py')]):
            cap=self.root/self.s.REVIEW;cap.parent.mkdir(parents=True)
            self.s.publish(cap,dict(verdict='PASS_GO',findings=[],sources=self.s.sources(self.root),limits={'reservations':3,'seconds':7200},activation=self.s.SCHEMA))
            target=self.root/'workspace/private/target.json'
            self.s.publish(target,dict(serial='fixture-serial',topology='usb:2-1.3'))
            kwargs=dict(goal='one fixed fixture experiment',target_file=target,catalog=[[self.manifest,self.review]],reservations=1,seconds=30)
            with self.assertRaises(self.s.SessionError):self.s.open_session(self.live,self.root,attended=False,**kwargs)
            path=self.s.open_session(self.live,self.root,attended=True,**kwargs)
            grant,_=self.s.load_grant(self.root,path,active=True)
            self.assertEqual(grant['reservations'],1)
            self.assertEqual(grant['deadline_ns']-grant['started_ns'],30*10**9)
            self.assertEqual(grant['catalog'][0],self.entry())
            self.s.close(self.root,path,'operator-withdrawal')
            with self.assertRaisesRegex(self.s.SessionError,'closed'):self.s.load_grant(self.root,path,active=True)


if __name__=='__main__':unittest.main()
