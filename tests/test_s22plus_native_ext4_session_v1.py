"""Filesystem owner sequencing and durable one-shot failures, without device I/O."""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_session_v3 as owner
import s22plus_native_ext4_session_v1 as fs
import s22plus_native_records_v3 as records
import test_s22plus_native_session_v3 as base


class Device(base.DeviceFixture):
    def configuration(self, request): return dict(target={'serial':'fixture','topology':'usb:fixture'})

    def observe(self, step, request, *, guard, before_terminal, consume_observation=None, before_extra=None):
        if step.name == 'experiment-first':
            guard(); self.assert_mode('E')
            if self.fail_before == step.name: raise ValueError('pre-effect fault')
            before_extra(dict(mode='fixed-extra',sequence=5))
            self.actions.append('filesystem-initialize')
            if self.fail_after == step.name: raise OSError('formatter may have executed; result lost')
            before_terminal(); return self.proof(step)
        if step.name == 'native-final':
            self.actions.append('filesystem-verify')
            if self.fail_after == step.name: raise OSError('verification output lost')
        return super().observe(step, request, guard=guard, before_terminal=before_terminal,
                               consume_observation=consume_observation)


class OwnerTests(unittest.TestCase):
    setUp=base.OwnerTests.setUp
    def operation(self, kind='native-ext4', **options):
        if kind != 'native-ext4': return base.OwnerTests.operation(self,kind,**options)
        device=Device();device.mode='N';device.root=self.root
        fake=dict(path='/fixture',size=1,sha256='1'*64)
        request=dict(N={'filesystem':{'binding':fake},'gpt':{'proposal':{'sha256':'2'*64}}},E={'fixture':True})
        with mock.patch.object(device,'prepare',return_value=request):
            directory=owner.prepare_operation(self.root,self.grant,operation=kind,adapter=device,**options)
        device.directory=directory
        session=owner.Session(self.root,directory,device)
        device.on_native_attempt=lambda:owner.registry.begin_f1_owner(self.root,directory,session.binding)
        return session,device

    def test_filesystem_normal_graph_closes_android_with_exactly_one_initialize_and_verify(self):
        session,device=self.operation();terminal=session.execute(attended=True)
        self.assertEqual(device.installed,['E','N','A']);self.assertEqual(terminal['state'],'ANDROID_CLOSED')
        self.assertEqual(device.actions.count('filesystem-initialize'),1)
        self.assertEqual(device.actions.count('filesystem-verify'),1)
        effects=[r['data']['step'] for r in session.rows() if r['event']=='effect-intent']
        self.assertEqual(effects,['native-start','install-experiment','experiment-first','experiment-final',
                                 'restore-native','native-exit','install-android'])
        before=copy.deepcopy(device.actions)
        with self.assertRaises(ValueError):session.execute(attended=True)
        self.assertEqual(before,device.actions)

    def test_uncertain_format_recovers_only_a_and_claim_cannot_renew_with_uuid(self):
        session,device=self.operation();device.fail_after='experiment-first'
        result=session.execute(attended=True)
        self.assertTrue(result['recovered']);self.assertEqual(device.installed,['E','A'])
        self.assertNotIn('filesystem-verify',device.actions)
        claim=fs.claim_path(device,session.request);self.assertTrue(claim.exists())
        changed=copy.deepcopy(session.request);changed['N']['filesystem']['binding']['sha256']='3'*64
        self.assertEqual(fs.claim_path(device,changed),claim)
        with self.assertRaises(FileExistsError):fs.claim_effect(device,owner.Step('experiment-first','observe','E','detach'),changed)

    def test_partition_claim_publication_failure_sends_no_format_and_recovers_a(self):
        session,device=self.operation()
        with mock.patch.object(fs,'claim_effect',side_effect=OSError('durable claim unavailable')):
            result=session.execute(attended=True)
        self.assertTrue(result['recovered']);self.assertNotIn('filesystem-initialize',device.actions)
        self.assertEqual(device.installed,['E','A'])

    def test_readonly_verification_failure_recovers_without_more_filesystem_commands(self):
        session,device=self.operation();device.fail_after='native-final'
        result=session.execute(attended=True)
        self.assertTrue(result['recovered']);self.assertEqual(device.installed,['E','N','A'])
        self.assertEqual(device.actions.count('filesystem-initialize'),1)
        self.assertEqual(device.actions.count('filesystem-verify'),1)
        self.assertNotIn('native-exit',device.actions)

    def test_normal_android_close_publication_fault_repairs_without_recovery_health_or_io(self):
        session,device=self.operation();real=owner.publish
        def fail_terminal(path,value):
            if Path(path).name=='terminal.json':raise OSError('terminal store unavailable')
            return real(path,value)
        with mock.patch.object(owner,'publish',side_effect=fail_terminal),self.assertRaises(OSError):
            session.execute(attended=True)
        before=copy.deepcopy(device.actions)
        result=session.repair_close()
        self.assertFalse(result['recovered']);self.assertEqual(before,device.actions)
        self.assertNotIn('health:recovery-health',device.actions)


if __name__=='__main__':unittest.main()
