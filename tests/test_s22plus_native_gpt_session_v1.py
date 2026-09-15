"""Independent device-state model for phased GPT effects and recovery cuts."""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_gpt_session_v1 as gpt
import s22plus_native_gpt_android_v1 as android
import s22plus_native_session_v3 as owner
import s22plus_native_records_v3 as records
import test_s22plus_native_session_v3 as base


class GptDevice(base.DeviceFixture):
    def __init__(self,root):
        super().__init__();self.root=root;self.mode='N';self.gpt='original';self.fs='old'
        self.boot=1;self.apply_count=self.restore_count=self.reset_count=self.reboot_count=0
        self.directory=None;self.publish_cut=None
        self.task=dict(target=dict(serial='FIXTURE123',topology='usb:2-1.3'))
        self.image=dict(profile='thermal-v3-reconnect-ufs-drain-gpt-v1',ap=dict(sha256='a'*64),
            gpt=dict(proposal=dict(sha256='b'*64)),run_id_hex='c'*32)

    def prepare(self,operation,grant,**options):
        return dict(N=self.image,A=dict(ap=dict(sha256='d'*64)),E=None,task={},prior_terminal={},
            admission={},usb_reconnect=False)

    def configuration(self,request):return self.task

    def folder(self,name,*,create=False):
        path=self.directory/('io-'+name)
        if create:path.mkdir(mode=0o700)
        return path

    def preflight(self,request,*,guard):
        guard()
        if gpt.claim_path(self,request).exists():raise ValueError('target/proposal already attempted')
        self.assert_mode('N')
        if self.gpt!='original':raise ValueError('initial GPT not original')

    def claim(self,step,request,binding):
        if step.name=='recover-native':
            if any(row['action']=='transfer' and row['role']=='A' for row in gpt.intents(self)):
                raise ValueError('recovery N may not overwrite intended A')

    def transfer(self,step,request,*,guard,before_launch):
        if step.role=='A':gpt.android_basis(self,request)
        if step.name in ('recover-native','recover-android'):self.mode='Download'
        self.assert_mode('Download');self.effect(step,before_launch);self.boot+=1
        value=self.proof(step)
        if self.publish_cut==step.name:raise owner.ResultPublicationError(step)
        return value

    def observe(self,step,request,*,guard,before_terminal,consume_observation=None,before_extra=None):
        guard();self.assert_mode('N')
        if step.name=='gpt-apply':self.on_native_attempt();self.native_attempt=True
        self.actions.append('health:'+step.name)
        if self.fail_before==step.name:raise ValueError('before modeled effect')
        if step.name in gpt.MUTATING:
            before_extra(dict(fixture='pre-EXEC callback'))
            if step.name=='gpt-apply':
                if self.gpt!='original':raise ValueError('apply requires original')
                self.apply_count+=1;self.gpt='proposed'
            else:self.restore_count+=1;self.gpt='original'
        if step.name=='gpt-proposed' and self.gpt!='proposed':raise ValueError('proposed missing')
        if step.name=='gpt-after-reset' and (self.gpt,self.fs)!=('proposed','new'):
            raise ValueError('new filesystem missing')
        if step.name=='gpt-after-original-reset' and (self.gpt,self.fs)!=('original','original-reset'):
            raise ValueError('original reset missing')
        if self.fail_after==step.name:raise OSError('modeled effect delivered, host evidence lost')
        if step.ending=='download':self.effect(step,before_terminal)
        else:before_terminal()
        value=self.proof(step)
        if step.name in ('gpt-apply','gpt-restore','gpt-proposed','gpt-after-reset','gpt-after-original-reset'):
            value['proof']=dict(gpt=dict(status='PASS_EXACT_GPT',selection=step.name,final_pair=self.gpt,
                full_metadata=dict(size=61440,sha256='1'*64 if self.gpt=='original' else '2'*64)))
            if 'reset' in step.name:
                value['proof']['gpt']['filesystem']=dict(status='PASS_GEOMETRY_ONLY',
                    block_count=25023740 if self.gpt=='proposed' else 58578419,segment0_block=512)
        self.proofs[step.name]=copy.deepcopy(value);return value

    def android_health(self,step,request,*,guard):
        guard();self.assert_mode('A');basis=gpt.android_basis(self,request)
        if self.health_failure:raise ValueError('Android health unavailable')
        self.actions.append('health:'+step.name)
        folder=self.folder(step.name);folder.mkdir(mode=0o700,exist_ok=True)
        health=records.publish(folder/'health.json',dict(boot_id_sha256=f'{self.boot:064x}',rooted_android_health=True))
        value=self.proof(step);value.update(health=health,gpt_android=dict(metadata=dict(layout=self.gpt),
            storage=dict(total_bytes=102495141888 if self.gpt=='proposed' else 239_000_000_000)))
        self.proofs[step.name]=copy.deepcopy(value);return value

    def android_reboot(self,step,request,*,guard,before_dispatch):
        guard();self.assert_mode('A');before_dispatch();self.actions.append(step.name)
        self.reboot_count+=1;self.boot+=1
        if self.fail_after==step.name:raise OSError('reboot occurred; response lost')
        return self.proof(step)

    def recover_step_result(self,step,request):
        if step.action=='physical':return gpt.physical_result(self,step,request)
        return copy.deepcopy(self.proofs[step.name])

    recover_transfer_result=recover_step_result

    def validate_result(self,step,value,request):
        if value!=self.recover_step_result(step,request):raise ValueError('modeled proof differs')

    def validate_sequence(self,steps,values,request):
        for step,value in zip(steps,values):self.validate_result(step,value,request)
        if steps[-1].role=='A':gpt.android_basis(self,request)
        if any(step.name=='android-reboot' for step in steps):
            if android.reboot_persistence(self,request,values[-1])['status']!='PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT':
                raise ValueError('reboot persistence unproved')

    def terminal(self,steps,values,request,*,recovered):
        basis=gpt.android_basis(self,request)
        return dict(state='ANDROID_CLOSED',layout=basis['layout'],
            reboot=android.reboot_persistence(self,request,values[-1]))


class GptOwnerTests(unittest.TestCase):
    setUp=base.OwnerTests.setUp

    def operation(self):
        device=GptDevice(self.root)
        directory=owner.prepare_operation(self.root,self.grant,operation='gpt-reserve',adapter=device)
        device.directory=directory;session=owner.Session(self.root,directory,device)
        device.on_native_attempt=lambda:owner.registry.begin_f1_owner(self.root,directory,session.binding)
        def snapshot(topology,folder):
            return dict(topology=topology,snapshot={'path':'fixture-generation'},identity={'boot':device.boot},
                boottime_ns=records.clock())
        def departure(before,folder,*,deadline_ns,guard):
            guard();context=records.read(Path(folder)/'context.json');device.boot+=1
            if context['action']=='stock-factory-reset':device.fs='new';device.reset_count+=1
            if context['action']=='stock-factory-reset-original':device.fs='original-reset';device.reset_count+=1
            return dict(before=before,departed=True,observed_ns=records.clock(),deadline_ns=deadline_ns)
        for name,value in (('usb_snapshot',snapshot),('wait_departure',departure)):
            patch=mock.patch.object(gpt.target,name,side_effect=value);patch.start();self.addCleanup(patch.stop)
        return session,device

    def through_reset(self,session):
        self.assertEqual(session.execute(attended=True)['action'],'restart-native')
        self.assertIsNotNone(self.f1)
        self.assertEqual(session.resume(attended=True,operator_statement='Native restarted')['action'],'stock-factory-reset')
        return session.resume(attended=True,operator_statement='Stock factory reset completed')

    def test_success_retains_owner_across_physical_stages_and_ends_android_after_reboot(self):
        session,device=self.operation()
        self.assertEqual(self.through_reset(session)['action'],'android-setup');self.assertIsNotNone(self.f1)
        result=session.resume(attended=True,operator_statement='Android and Magisk root setup completed')
        self.assertEqual((result['state'],result['layout']),('ANDROID_CLOSED','proposed'))
        self.assertEqual(result['reboot']['status'],'PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT')
        self.assertEqual((device.mode,device.apply_count,device.restore_count,device.reset_count,device.reboot_count),
            ('A',1,0,1,1))
        self.assertEqual(device.installed,['A']);self.assertIsNone(self.f1)
        with self.assertRaises(ValueError):session.execute(attended=True)
        with self.assertRaises(ValueError):session.resume(attended=True)
        self.assertEqual(session.repair_close()['reboot']['status'],'PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT')
        self.assertEqual(device.installed,['A']);self.assertEqual(device.reboot_count,1)

    def test_unknown_apply_recovers_native_and_original_gpt_before_one_a(self):
        session,device=self.operation();device.fail_after='gpt-apply'
        self.assertEqual(session.execute(attended=True)['state'],'AWAITING_GPT_RECOVERY')
        self.assertEqual(device.gpt,'proposed');self.assertEqual(device.installed,[])
        result=session.recover(attended=True)
        self.assertTrue(result['recovered']);self.assertEqual(result['layout'],'original')
        self.assertEqual((device.apply_count,device.restore_count,device.reset_count),(1,1,0))
        self.assertEqual(device.installed,['N','A']);self.assertIsNone(self.f1)

    def test_uncertain_original_restore_never_repeats_or_reaches_a(self):
        session,device=self.operation();device.fail_after='gpt-apply';session.execute(attended=True)
        device.fail_after='gpt-restore'
        self.assertEqual(session.recover(attended=True)['state'],'GPT_RECOVERY_STOPPED')
        self.assertEqual(session.recover(attended=True)['state'],'GPT_RECOVERY_STOPPED')
        self.assertEqual((device.apply_count,device.restore_count),(1,1))
        self.assertEqual(device.installed,['N']);self.assertIsNotNone(self.f1)

    def test_reset_failure_needs_original_geometry_reset_before_a(self):
        session,device=self.operation()
        session.execute(attended=True);session.resume(attended=True,operator_statement='Native restarted')
        device.fail_after='gpt-after-reset'
        self.assertEqual(session.resume(attended=True,operator_statement='Stock reset completed')['state'],'AWAITING_GPT_RECOVERY')
        device.fail_after=None
        self.assertEqual(session.recover(attended=True)['action'],'stock-factory-reset-original')
        self.assertEqual(device.installed,['N']);self.assertEqual(device.gpt,'original')
        self.assertEqual(session.resume(attended=True,operator_statement='Original-size reset completed')['action'],'android-setup')
        result=session.resume(attended=True,operator_statement='Android root setup completed')
        self.assertEqual(result['layout'],'original');self.assertEqual(device.reset_count,2)
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.restore_count,1)

    def test_a_is_forbidden_before_reset_or_original_restore_proof(self):
        session,device=self.operation();session.execute(attended=True)
        with self.assertRaises(ValueError):gpt.android_basis(device,session.request)
        self.assertEqual(device.installed,[]);self.assertIsNotNone(self.f1)

    def test_uncertain_a_is_not_overwritten_by_n_or_replayed(self):
        session,device=self.operation();device.fail_after='install-android'
        self.assertEqual(self.through_reset(session)['state'],'AWAITING_GPT_RECOVERY')
        for _ in range(2):
            with self.assertRaises(KeyError):session.recover(attended=True)
        self.assertEqual(device.installed,['A']);self.assertEqual(device.restore_count,0)
        self.assertIsNotNone(self.f1)

    def test_a_result_publication_cut_repairs_h0_without_a_second_transfer(self):
        session,device=self.operation();device.publish_cut='install-android'
        session.execute(attended=True);session.resume(attended=True,operator_statement='Native restarted')
        with self.assertRaises(owner.ResultPublicationError):
            session.resume(attended=True,operator_statement='Stock reset completed')
        self.assertEqual(session.repair_close()['state'],'H0_REPAIRED_PREFIX')
        self.assertEqual(session.resume(attended=True)['action'],'android-setup')
        result=session.resume(attended=True,operator_statement='Android root setup completed')
        self.assertEqual(result['layout'],'proposed');self.assertEqual(device.installed,['A'])

    def test_target_proposal_claim_blocks_another_operation_before_authentication(self):
        session,device=self.operation();self.through_reset(session)
        session.resume(attended=True,operator_statement='Android root setup completed')
        other,second=self.operation()
        self.assertEqual(other.execute(attended=True)['state'],'STOPPED_BEFORE_EFFECT')
        self.assertFalse(second.native_attempt);self.assertEqual(second.apply_count,0);self.assertIsNone(self.f1)

    def test_unknown_android_reboot_is_not_repeated_during_a_only_recovery(self):
        session,device=self.operation();self.through_reset(session);device.fail_after='android-reboot'
        self.assertEqual(session.resume(attended=True,operator_statement='Android root setup completed')['state'],
            'AWAITING_GPT_RECOVERY')
        result=session.recover(attended=True)
        self.assertEqual(result['layout'],'proposed');self.assertEqual(result['reboot']['status'],'NO_PROOF')
        self.assertEqual(device.reboot_count,1);self.assertEqual(device.installed,['A']);self.assertEqual(device.restore_count,0)

    def setup_pending(self,*,publication_cut=False):
        session,device=self.operation();self.through_reset(session)
        failed=device.folder('android-initial')/'attempt-setup/before/03-health.capture.json'
        original=device.android_health;first=[True]
        def health(step,request,*,guard):
            if step.name=='android-initial' and first[0]:
                first[0]=False;failed.parent.mkdir(parents=True)
                failed.write_text('modeled completed missing-su receipt')
                raise android.SetupPending(records.pin(failed))
            return original(step,request,guard=guard)
        def missing(folder,*_):
            if Path(folder)!=failed.parent:raise ValueError('unclassified later attempt')
            return records.pin(failed)
        # Actual byte classification and 32 GiB vector decoding are covered by
        # their real producer tests; this model exercises effect/owner ordering.
        for patch in (mock.patch.object(device,'android_health',side_effect=health),
                mock.patch.object(android,'missing_su_setup',side_effect=missing),
                mock.patch.object(gpt.gpt,'vectors',return_value={}),
                mock.patch.object(gpt.gpt,'geometry',return_value=dict(userdata_sectors=gpt.gpt.ANDROID32_USER))):
            patch.start();self.addCleanup(patch.stop)
        if publication_cut:
            append=session.journal.append
            def cut(event,**data):
                if event=='android-setup-pending':raise OSError('pending journal publication cut')
                return append(event,**data)
            with mock.patch.object(session.journal,'append',side_effect=cut),self.assertRaises(owner.ResultPublicationError):
                session.resume(attended=True,operator_statement='Initial setup reported')
            self.assertFalse(any(r['event']=='android-setup-pending' for r in session.rows()))
            # The retained raw file must reconstruct the waiting state without
            # reading Android again or treating the old setup report as new.
            result=session.resume(attended=True)
        else:result=session.resume(attended=True,operator_statement='Initial setup reported')
        self.assertEqual(result['action'],'android-setup')
        self.assertFalse(any(row['event']=='stopped' for row in session.rows()))
        self.assertEqual(device.reboot_count,0);self.assertIsNotNone(self.f1)
        return session,device,failed

    def test_known_setup_pending_waits_for_new_report_then_one_remaining_reboot(self):
        session,device,failed=self.setup_pending();before=failed.read_bytes();actions=list(device.actions)
        self.assertEqual(session.resume(attended=True)['action'],'android-setup')
        self.assertEqual(device.actions,actions);self.assertEqual(device.reboot_count,0)
        result=session.resume(attended=True,operator_statement='Magisk setup now completed')
        self.assertEqual(result['reboot']['status'],'PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT')
        self.assertEqual((device.apply_count,device.reset_count,device.reboot_count),(1,1,1))
        self.assertEqual(device.installed,['A']);self.assertEqual(failed.read_bytes(),before)
        self.assertEqual(len([r for r in session.rows() if r['event']=='android-setup-reported']),1)

    def test_setup_pending_cannot_renew_an_expired_original_grant(self):
        session,device,_=self.setup_pending();actions=list(device.actions)
        with mock.patch.object(owner,'clock',return_value=session.grant['deadline_ns']+1), \
                self.assertRaises(ValueError):
            session.resume(attended=True,operator_statement='Setup reported after deadline')
        self.assertEqual(device.actions,actions);self.assertEqual(device.reboot_count,0)

    def test_cut_after_raw_before_pending_journal_never_repeats_read_without_new_report(self):
        session,device,failed=self.setup_pending(publication_cut=True)
        self.assertTrue(failed.exists());self.assertEqual(device.reboot_count,0)
        self.assertFalse((session.directory/'android-initial.json').exists())
        result=session.resume(attended=True,operator_statement='Magisk setup now completed')
        self.assertEqual(result['reboot']['status'],'PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT')
        self.assertEqual(device.reboot_count,1);self.assertEqual(device.installed,['A'])

    def test_unclassified_later_read_before_stop_publication_cannot_reopen_normal_work(self):
        session,device,failed=self.setup_pending()
        session.journal.append('android-setup-reported',failed_root=records.pin(failed),
            statement='Magisk setup completed',reported_ns=records.clock())
        (device.folder('android-initial')/'attempt-unclassified/before').mkdir(parents=True)
        before=list(device.actions)
        result=session.resume(attended=True)
        self.assertEqual(result['state'],'AWAITING_GPT_RECOVERY')
        self.assertEqual(device.actions,before);self.assertEqual(device.reboot_count,0)
        self.assertTrue(any(r['event']=='stopped' for r in session.rows()))

    def test_setup_report_publication_cut_preserves_pending_and_does_not_stop_or_read(self):
        session,device,_=self.setup_pending();actions=list(device.actions);append=session.journal.append
        def cut(event,**data):
            if event=='android-setup-reported':raise OSError('setup report publication cut')
            return append(event,**data)
        with mock.patch.object(session.journal,'append',side_effect=cut),self.assertRaises(owner.ResultPublicationError):
            session.resume(attended=True,operator_statement='Magisk setup now completed')
        self.assertEqual(device.actions,actions);self.assertEqual(device.reboot_count,0)
        self.assertFalse(any(r['event']=='stopped' for r in session.rows()))
        self.assertEqual(session.resume(attended=True)['action'],'android-setup')
        result=session.resume(attended=True,operator_statement='Magisk setup now completed')
        self.assertEqual(result['reboot']['status'],'PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT')
        self.assertEqual(device.reboot_count,1)


if __name__=='__main__':unittest.main()
