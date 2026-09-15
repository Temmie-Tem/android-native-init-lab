"""Behavioral owner faults: no-effect failures, uncertain effects and H0 close."""
from contextlib import contextmanager
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_session_v3 as owner
import s22plus_native_records_v3 as records


class DeviceFixture:
    """Separate device model; delivery mutates state before injected host faults."""
    def __init__(self):
        self.mode='A'; self.installed=[]; self.actions=[]; self.proofs={}
        self.fail_before=None; self.fail_after=None; self.health_failure=False
        self.preflight_failure=False; self.admitted=0
        self.native_attempt=False; self.on_native_attempt=lambda:None

    def check(self,request,*,recovery=False): pass
    def native_attempt_started(self,request): return self.native_attempt
    def claim(self,step,request,binding): pass
    def prepare(self,operation,grant,**options): return dict(target='fixture')

    def preflight(self,request,*,guard):
        guard()
        if self.preflight_failure: raise ValueError('host or Android preflight failed')

    def effect(self,step,before):
        if self.fail_before==step.name: raise ValueError('before dispatch')
        before()
        self.actions.append(step.name)
        if step.action=='transfer':
            self.installed.append(step.role); self.mode=step.role
        else:
            self.mode='Download'
        if self.fail_after==step.name: raise OSError('delivery occurred; host result lost')

    def proof(self,step):
        result=dict(step=step.name,role=step.role,action=step.action,ending=step.ending,
            health=step.action in ('observe','health'),closed=step.ending=='detach')
        self.proofs[step.name]=copy.deepcopy(result)
        return result

    def android_download(self,step,request,*,guard,before_dispatch):
        self.assert_mode('A'); self.effect(step,before_dispatch); return self.proof(step)

    def transfer(self,step,request,*,guard,before_launch):
        # Attended recovery's physical Download entry is an explicit fixture.
        if step.role=='A' and step.name=='recover-android': self.mode='Download'
        self.assert_mode('Download'); self.effect(step,before_launch); return self.proof(step)

    def observe(self,step,request,*,guard,before_terminal,consume_observation=None):
        guard(); self.assert_mode(step.role)
        if step.name in ('native-start','native-storage','native-bootstrap-start'):
            if consume_observation is not None:consume_observation()
            else:self.on_native_attempt()
            self.native_attempt=True
        self.actions.append('health:'+step.name)
        if self.health_failure: raise ValueError('required health not proved')
        if step.ending=='download': self.effect(step,before_terminal)
        else: before_terminal()
        return self.proof(step)

    def android_health(self,step,request,*,guard):
        guard(); self.assert_mode('A'); self.actions.append('health:'+step.name)
        if self.health_failure: raise ValueError('Android health unavailable')
        return self.proof(step)

    def assert_mode(self,expected):
        if self.mode!=expected: raise ValueError('fixture state differs: '+self.mode+' vs '+expected)

    def validate_result(self,step,value,request):
        if value!=self.proofs.get(step.name): raise ValueError('raw evidence differs')

    def validate_sequence(self,steps,values,request):
        if [value['step'] for value in values]!=[step.name for step in steps]: raise ValueError('proof order differs')

    def terminal(self,steps,values,request,*,recovered):
        return dict(state='ANDROID_CLOSED' if steps[-1].role=='A' else 'NATIVE_CLOSED')

    def admit(self,request,terminal): self.admitted=1
    def final_protocol_completed(self,step,request): return bool(self.proofs.get(step.name,{}).get('closed'))
    def recover_transfer_result(self,step,request): return copy.deepcopy(self.proofs[step.name])
    recover_step_result=recover_transfer_result


class OwnerTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name); self.private=self.root/'workspace/private'; self.private.mkdir(parents=True)
        self.task=self.private/'task'; self.task.mkdir()
        self.grant=self.task/'grant.json'
        records.publish(self.grant,dict(schema=owner.SCHEMA,host_boot=records.host_boot(),
            opened_ns=records.clock(),deadline_ns=records.clock()+600_000_000_000,
            operation_budget=2,recovery_mode='attended'))
        self.f1=None
        @contextmanager
        def lease(root): yield
        def no_owner(root):
            if self.f1 is not None: raise ValueError('another F1 owner')
        def begin(root,directory,binding):
            no_owner(root); self.f1=(directory,binding)
            path=root/owner.registry.F1_OWNER; path.parent.mkdir(parents=True,exist_ok=True)
            records.publish(path,dict(directory=str(directory),binding=binding))
        def require_owner(root,directory,binding):
            if self.f1!=(directory,binding): raise ValueError('owner differs')
        def retire(root,directory,binding):
            if self.f1 is not None:
                require_owner(root,directory,binding); self.f1=None
                (root/owner.registry.F1_OWNER).unlink()
        for name,impl in [('target_session_lease',lease),('require_no_f1_owner',no_owner),
                ('begin_f1_owner',begin),('require_f1_owner',require_owner),('retire_f1_owner',retire)]:
            patch=mock.patch.object(owner.registry,name,impl); patch.start(); self.addCleanup(patch.stop)

    def operation(self,kind='bootstrap',**options):
        device=DeviceFixture()
        if kind!='bootstrap': device.mode='N'
        directory=owner.prepare_operation(self.root,self.grant,operation=kind,adapter=device,**options)
        session=owner.Session(self.root,directory,device)
        device.on_native_attempt=lambda:owner.registry.begin_f1_owner(self.root,directory,session.binding)
        return session,device

    def test_bootstrap_keeps_two_installations_four_auths_and_one_admission(self):
        session,device=self.operation()
        terminal=session.execute(attended=True)
        self.assertEqual(terminal['state'],'NATIVE_CLOSED')
        self.assertEqual(device.installed,['N','N'])
        self.assertEqual(sum(action.startswith('health:') for action in device.actions),4)
        self.assertEqual(device.admitted,1); self.assertIsNone(self.f1)
        with self.assertRaises(records.SessionError): session.execute(attended=True)
        self.assertEqual(device.installed,['N','N'])

    def test_native_origin_bootstrap_preserves_both_installations_and_four_new_n_healths(self):
        device=DeviceFixture();device.mode='S'
        with mock.patch.object(device,'prepare',return_value=dict(S={'fixture':'admitted predecessor'})):
            directory=owner.prepare_operation(self.root,self.grant,operation='bootstrap',adapter=device)
        session=owner.Session(self.root,directory,device)
        device.on_native_attempt=lambda:owner.registry.begin_f1_owner(self.root,directory,session.binding)
        result=session.execute(attended=True)
        self.assertEqual(result['state'],'NATIVE_CLOSED');self.assertFalse(result['recovered'])
        self.assertEqual(device.installed,['N','N']);self.assertEqual(device.admitted,1)
        self.assertEqual(device.actions[:2],['health:native-bootstrap-start','native-bootstrap-start'])
        self.assertEqual(sum(a.startswith('health:native-first') or a.startswith('health:native-second')
            for a in device.actions),4)
        self.assertNotIn('android-download',device.actions);self.assertIsNone(self.f1)
        self.assertEqual(session.repair_close()['state'],'NATIVE_CLOSED')
        self.assertEqual(device.installed,['N','N'])

    def test_native_origin_bootstrap_auth_failure_recovers_a_without_installing_new_n(self):
        device=DeviceFixture();device.mode='S';device.health_failure=True
        with mock.patch.object(device,'prepare',return_value=dict(S={'fixture':'admitted predecessor'})):
            directory=owner.prepare_operation(self.root,self.grant,operation='bootstrap',adapter=device)
        session=owner.Session(self.root,directory,device)
        device.on_native_attempt=lambda:owner.registry.begin_f1_owner(self.root,directory,session.binding)
        with self.assertRaises(ValueError):session.execute(attended=True)
        self.assertEqual(device.installed,['A']);self.assertIsNotNone(self.f1)
        device.health_failure=False
        self.assertEqual(session.recover(attended=True)['state'],'ANDROID_CLOSED')
        self.assertEqual(device.installed,['A'])
        self.assertEqual(device.actions.count('health:native-bootstrap-start'),1)

    def test_nen_has_one_final_n_health_and_explicit_e_only_options(self):
        for reentry in (False,True):
            with self.subTest(reentry=reentry):
                session,device=self.operation('experiment',reentry=reentry,hud=True)
                terminal=session.execute(attended=True)
                self.assertEqual(terminal['state'],'NATIVE_CLOSED')
                self.assertEqual(device.installed,['E','N'])
                self.assertEqual(sum(action.startswith('health:') for action in device.actions),4 if reentry else 3)
                self.assertEqual(device.actions.count('health:native-final'),1)
                self.assertEqual([step.role for step in owner.steps('experiment',reentry=reentry,hud=True) if step.hud],['E'])

    def test_storage_census_consumes_one_operation_without_a_mode_change_or_transfer(self):
        session,device=self.operation('storage-census')
        result=session.execute(attended=True)
        self.assertEqual(result['state'],'NATIVE_CLOSED')
        self.assertEqual(device.installed,[])
        self.assertEqual(device.actions,['health:native-storage'])
        self.assertIsNotNone(session.consumed());self.assertIsNone(self.f1)
        self.assertFalse(session.has_effect())
        with self.assertRaises(records.SessionError):session.execute(attended=True)

    def test_storage_census_uncertain_protocol_retains_original_a_recovery(self):
        session,device=self.operation('storage-census');device.health_failure=True
        with self.assertRaises(ValueError):session.execute(attended=True)
        self.assertEqual(device.installed,['A']);self.assertIsNotNone(session.consumed())
        device.health_failure=False
        self.assertEqual(session.recover(attended=True)['state'],'ANDROID_CLOSED')
        self.assertEqual(device.installed,['A']);self.assertIsNone(self.f1)

    def test_storage_census_capacity_is_checked_before_another_native_attempt(self):
        for _ in range(2):
            session,device=self.operation('storage-census')
            self.assertEqual(session.execute(attended=True)['state'],'NATIVE_CLOSED')
        session,device=self.operation('storage-census')
        self.assertEqual(session.execute(attended=True)['state'],'STOPPED_BEFORE_EFFECT')
        self.assertFalse(device.native_attempt);self.assertEqual(device.actions,[])
        self.assertEqual(device.installed,[]);self.assertIsNone(self.f1)

    def test_preflight_failure_preserves_budget_and_original_deadline(self):
        before=self.grant.read_bytes()
        session,device=self.operation(); device.preflight_failure=True
        self.assertEqual(session.execute(attended=True)['state'],'STOPPED_BEFORE_EFFECT')
        self.assertIsNone(session.consumed()); self.assertIsNone(self.f1)
        self.assertEqual(device.actions,[]); self.assertEqual(self.grant.read_bytes(),before)
        fresh,device=self.operation(); self.assertEqual(fresh.execute(attended=True)['state'],'NATIVE_CLOSED')

    def test_failure_between_owner_and_consumption_releases_only_unused_owner(self):
        session,device=self.operation()
        original=owner.publish
        def fail(path,value):
            if Path(path).name=='consumed.json': raise OSError('publication cut')
            return original(path,value)
        with mock.patch.object(owner,'publish',side_effect=fail):
            result=session.execute(attended=True)
        self.assertEqual(result['state'],'STOPPED_BEFORE_EFFECT'); self.assertFalse(result['operation_consumed'])
        self.assertIsNone(self.f1); self.assertIsNone(session.consumed()); self.assertEqual(device.actions,[])

    def test_crash_before_effect_can_be_closed_h0_without_recovery(self):
        session,device=self.operation()
        owner.registry.begin_f1_owner(self.root,session.directory,session.binding)
        result=session.repair_close()
        self.assertEqual(result['state'],'STOPPED_BEFORE_EFFECT'); self.assertIsNone(self.f1)
        self.assertEqual(device.actions,[])
        with self.assertRaises(records.SessionError): session.execute(attended=True)

    def test_uncertain_effect_stops_candidate_and_uses_one_original_a(self):
        session,device=self.operation(); device.fail_after='install-native-first'
        terminal=session.execute(attended=True)
        self.assertEqual(terminal['state'],'ANDROID_CLOSED')
        self.assertTrue(terminal['recovered']); self.assertEqual(device.installed,['N','A'])
        self.assertIsNone(self.f1)
        with self.assertRaises(records.SessionError): session.recover(attended=True)
        self.assertEqual(device.installed,['N','A'])

    def test_uncertain_a_is_never_replayed(self):
        session,device=self.operation(); device.fail_after='recover-android'; device.fail_before='install-native-first'
        with self.assertRaises(OSError): session.execute(attended=True)
        self.assertEqual(device.installed,['A'])
        with self.assertRaises(KeyError): session.recover(attended=True)
        self.assertEqual(device.installed,['A']); self.assertIsNotNone(self.f1)

    def test_uncertain_native_start_retains_a_without_charging_experimental_capacity(self):
        session,device=self.operation('experiment'); device.health_failure=True
        with self.assertRaises(ValueError):session.execute(attended=True)
        self.assertEqual(device.installed,['A']);self.assertIsNone(session.consumed())
        self.assertIsNotNone(self.f1)
        self.assertNotIn('native-start',[row['data']['step'] for row in session.rows() if row['event']=='effect-intent'])
        device.health_failure=False
        terminal=session.recover(attended=True)
        self.assertEqual(terminal['state'],'ANDROID_CLOSED');self.assertTrue(terminal['recovered'])
        self.assertEqual(device.actions.count('health:native-start'),1)
        self.assertEqual(device.installed,['A']);self.assertIsNone(self.f1)

    def test_final_native_publication_failure_never_dispatches_recovery(self):
        session,device=self.operation()
        original=owner.publish
        def fail(path,value):
            if Path(path).name=='native-second-2.json': raise OSError('disk fault')
            return original(path,value)
        with mock.patch.object(owner,'publish',side_effect=fail),self.assertRaises(owner.ResultPublicationError):
            session.execute(attended=True)
        self.assertEqual(device.installed,['N','N']); self.assertIsNotNone(self.f1)
        self.assertEqual(session.repair_close()['state'],'NATIVE_CLOSED')
        self.assertEqual(device.installed,['N','N']); self.assertIsNone(self.f1)

    def test_terminal_publish_and_admission_failure_are_h0_only(self):
        session,device=self.operation()
        with mock.patch.object(device,'admit',side_effect=OSError('admission store unavailable')),self.assertRaises(OSError):
            session.execute(attended=True)
        self.assertTrue((session.directory/'terminal.json').exists())
        self.assertEqual(device.installed,['N','N'])
        self.assertEqual(session.repair_close()['state'],'NATIVE_CLOSED'); self.assertIsNone(self.f1)

    def test_recovery_entry_rederives_completed_normal_close_without_terminal_file(self):
        session,device=self.operation()
        with mock.patch.object(session,'close',side_effect=OSError('terminal publication failure')),self.assertRaises(OSError):
            session.execute(attended=True)
        self.assertFalse((session.directory/'terminal.json').exists())
        self.assertEqual(session.recover(attended=True)['state'],'NATIVE_CLOSED')
        self.assertEqual(device.installed,['N','N']); self.assertIsNone(self.f1)

    def test_unreadable_completed_final_proof_never_becomes_a_authority(self):
        session,device=self.operation()
        with mock.patch.object(session,'close',side_effect=OSError('terminal write cut')),self.assertRaises(OSError):
            session.execute(attended=True)
        original=device.recover_step_result
        def unavailable(step,request):
            if step.name=='native-second-2': raise OSError('temporary proof read failure')
            return original(step,request)
        with mock.patch.object(device,'recover_step_result',side_effect=unavailable),self.assertRaises(records.SessionError):
            session.recover(attended=True)
        self.assertEqual(device.installed,['N','N'])

    def test_later_a_intent_prevents_native_prefix_terminal(self):
        session,device=self.operation()
        with mock.patch.object(session,'close',side_effect=OSError('terminal write cut')),self.assertRaises(OSError):
            session.execute(attended=True)
        # Reconstruct a retained journal with a later A from a prior buggy
        # owner. Its earlier valid native prefix must not become the terminal.
        session.journal.append('stopped',error_type='prior-owner-cut',effect_intended=True)
        session.perform(owner.Step('recover-android','transfer','A'),recovery=True)
        session.perform(owner.Step('recovery-health','health','A'),recovery=True)
        result=session.repair_close()
        self.assertEqual(result['state'],'ANDROID_CLOSED'); self.assertTrue(result['recovered'])
        self.assertEqual(device.installed,['N','N','A'])

    def test_expiry_before_effect_does_not_reserve_and_host_suspend_counts(self):
        session,device=self.operation()
        expired=session.grant['deadline_ns']+1
        with mock.patch.object(owner,'clock',return_value=expired),self.assertRaises(records.SessionError):
            session.execute(attended=True)
        self.assertIsNone(session.consumed()); self.assertIsNone(self.f1); self.assertEqual(device.actions,[])

    def test_original_a_health_can_resume_after_transfer_without_renewal(self):
        session,device=self.operation(); device.fail_before='native-first-1'
        # A required health failure after first installation enters recovery;
        # another health failure after A leaves exactly one proved A transfer.
        original=device.observe
        def failed(*args,**kwargs):
            device.health_failure=True
            return original(*args,**kwargs)
        device.observe=failed
        with self.assertRaises(ValueError): session.execute(attended=True)
        self.assertEqual(device.installed,['N','A'])
        device.health_failure=False
        with mock.patch.object(owner,'clock',return_value=session.grant['deadline_ns']+1):
            terminal=session.recover(attended=True)
        self.assertEqual(terminal['state'],'ANDROID_CLOSED'); self.assertEqual(device.installed,['N','A'])

    def test_recovered_terminal_retirement_failure_repairs_without_a_or_health(self):
        session,device=self.operation(); device.fail_after='install-native-first'
        original=owner.registry.retire_f1_owner
        with mock.patch.object(owner.registry,'retire_f1_owner',side_effect=OSError('retirement cut')),self.assertRaises(OSError):
            session.execute(attended=True)
        actions=list(device.actions)
        result=session.repair_close()
        self.assertEqual(result['state'],'ANDROID_CLOSED'); self.assertEqual(device.actions,actions)
        self.assertIsNone(self.f1)


if __name__=='__main__': unittest.main()
