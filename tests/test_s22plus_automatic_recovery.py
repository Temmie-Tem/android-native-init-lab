"""Actual C fork/IPC and original-owner recovery admission/failure cases."""
import contextlib
from dataclasses import asdict
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest import mock

import s22plus_mainline_auto_recovery_v1 as auto
import s22plus_native_records_v3 as records
import test_s22plus_mainline_download_ram as prior
from mainline.s22plus_ufs_link_h0 import link_wire as wire

ROOT=Path(__file__).resolve().parents[1]


def measured_ticket(root,name,birth,uid=0):
    from test_s22plus_odin_usbfs_identity import node
    usb=auto.transition.usbfs_identity
    sample=node(usb,birth_time_ns=birth,st_uid=uid)
    identity=usb.immutable_identity(sample)
    evidence=usb.enumeration_evidence({sample.path:sample},{sample.path:sample},(sample.path,))
    receipt=records.publish(root/(name+'.json'),dict(schema=auto.transition.SNAPSHOT_SCHEMA,sequence=0,
        live_devices=[sample.path],live_device_identities=[[sample.path,identity]],endpoint_transition_evidence=evidence))
    return auto.transition.EndpointTicket(sample.path,identity,1,0,receipt['path'],receipt['sha256'])


class ChildTests(unittest.TestCase):
    def test_actual_host_and_arm64_child_single_slot_faults(self):
        with tempfile.TemporaryDirectory() as tmp:
            for compiler,runner in (('cc',()),('aarch64-linux-gnu-gcc',('qemu-aarch64',))):
                exe=Path(tmp)/compiler
                subprocess.run([compiler,'-std=c11','-O2','-static','-Wall','-Wextra','-Werror',
                    '-Wno-unused-function','-Wno-unused-variable',
                    '-I'+str(ROOT/'workspace/public/src/mainline/s22plus_canary_h0'),
                    '-I'+str(ROOT/'workspace/public/src/mainline/s22plus_ufs_link_h0'),
                    ROOT/'tests/s22plus_recovery_fixture.c','-o',exe],check=True)
                if runner:self.assertIn('ARM aarch64',subprocess.check_output(['file',exe],text=True))
                for case in ('normal','timer','early','eof','flood','malformed','killed','expired','commit-expired','child-late-commit',
                             'bad-platform','late-start'):
                    with self.subTest(compiler=compiler,case=case):
                        out=subprocess.check_output([*runner,exe,case],timeout=5,text=True).splitlines()
                        if case in ('bad-platform','late-start'):
                            self.assertTrue(out[-1].startswith('REFUSED '));self.assertEqual(out[-1].split()[-1],'0');continue
                        _,calls,at,user,system,status=out[-1].split()
                        self.assertEqual(int(calls),0 if case in ('killed','expired') else 1)
                        if int(calls):self.assertEqual(int(at),1000 if case=='normal' else 555000)
                        if case=='eof':self.assertLess(int(user)+int(system),100000)
                        frames=[bytes.fromhex(line[6:]) for line in out if line.startswith('FRAME ')]
                        key=b'\1'+bytes(31);identity=b'\2'+bytes(31);base=b'\3'*32;boot=b'\4'*16
                        self.assertTrue(wire.recovery_arm(frames[0],key,identity,base,base,boot)['child_reply_observed'])
                        if case=='normal':
                            self.assertEqual(len(frames),2)
                            wire.recovery_arm(frames[1],key,identity,base,b'\3'+bytes(31),boot,late=True)


class WindowTests(unittest.TestCase):
    report_version=6
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.now=records.clock();self.epoch=records.host_boot()
        cap=records.publish(self.root/'cap.json',dict(schema='s22plus-mainline-ufs-capability-v2',
            scope='S22PLUS_LATE_UFS_KEY_ONLY_V2',fixed=dict(report_version=self.report_version)))
        grant=records.publish(self.root/'grant.json',dict(host_boot=self.epoch,deadline_ns=self.now+1))
        self.request=dict(operation='mainline-ram',grant=grant,N=dict(schema='s22plus-mainline-ufs-image-v2',
            capability=cap,ap={'immutable':'N'},member='boot.img'))
        records.publish(self.root/'operation.json',self.request)
        self.journal=records.Journal(self.root/'journal')
        self.journal.append('effect-intent',step='android-download',action='download',role='A',
                            detail=dict(departure_deadline_ns=self.now+30_000_000_000))
        self.adapter=types.SimpleNamespace(directory=self.root,folder=lambda n:self.root/('io-'+n),
            configuration=lambda q:{'odin':{'path':'/fixture/odin','size':1,'sha256':'a'*64}},
            recover_transfer_result=mock.Mock(side_effect=AssertionError('N completion must not be read')))
        self.session=types.SimpleNamespace(adapter=self.adapter,request=self.request,check=mock.Mock())

    def native(self):
        folder=self.adapter.folder('install-native-first')/'attempt-original';folder.mkdir(parents=True)
        launch=records.publish(folder/'launch.json',dict(step='install-native-first',role='N',
            ap=self.request['N']['ap'],member='boot.img',boottime_ns=self.now,
            ticket=asdict(measured_ticket(self.root,'original-ticket',100)),revalidation={'fixture':'checked'}))
        self.journal.append('effect-intent',step='install-native-first',action='transfer',role='N',detail=dict(launch=launch))
        return launch

    def test_uncertain_n_uses_original_intent_without_candidate_or_completion(self):
        self.native();value=auto.window(self.adapter,self.request)
        self.assertEqual(value['opened_ns'],self.now);self.assertEqual(value['deadline_ns'],self.now+auto.ARRIVAL_NS)
        # Recovery authority remains finite after the research grant expired.
        with mock.patch.object(auto,'clock',return_value=self.now+100_000_000_000):
            self.assertEqual(auto.window(self.adapter,self.request),value)
        self.adapter.recover_transfer_result.assert_not_called()
        receipt=records.publish(self.root/'window.json',value)
        self.assertEqual(auto.deadline(self.adapter,self.request,receipt),value['deadline_ns'])
        unchanged=measured_ticket(self.root,'same-ticket',100)
        changed_permission=measured_ticket(self.root,'permission-ticket',100,uid=1000)
        fresh=measured_ticket(self.root,'fresh-ticket',101)
        self.assertNotEqual(unchanged.device_identity,changed_permission.device_identity)
        for ticket in (unchanged,changed_permission):
            with self.assertRaises(ValueError):auto.admit_ticket(self.adapter,self.request,receipt,ticket)
        auto.admit_ticket(self.adapter,self.request,receipt,fresh)
        with mock.patch.object(auto,'clock',return_value=value['deadline_ns']):
            with self.assertRaises(ValueError):
                auto.admit_ticket(self.adapter,self.request,receipt,fresh)
        bad=records.publish(self.root/'renewed.json',dict(value,deadline_ns=value['deadline_ns']+1))
        with self.assertRaises(ValueError):auto.deadline(self.adapter,self.request,bad)
        with mock.patch.object(auto,'host_boot',return_value='changed'):
            with self.assertRaises(ValueError):auto.window(self.adapter,self.request)

    def test_pre_n_and_duplicate_native_intents(self):
        value=auto.window(self.adapter,self.request)
        self.assertEqual(value['phase'],'PRE_N_DEPARTURE')
        self.assertEqual(value['deadline_ns'],self.now+90_000_000_000)
        launch=self.native()
        self.journal.append('effect-intent',step='install-native-first',action='transfer',role='N',detail=dict(launch=launch))
        with self.assertRaises(ValueError):auto.window(self.adapter,self.request)

    def test_same_download_generation_cannot_spend_a_slot(self):
        self.native();folder=self.root/'observe';folder.mkdir()
        receipt=records.publish(folder/'window.json',auto.window(self.adapter,self.request))
        original=measured_ticket(self.root,'same-generation',100)
        permissions=measured_ticket(self.root,'permissions-only',100,uid=1000)
        fresh=measured_ticket(self.root,'fresh-generation',101)
        results=iter([types.SimpleNamespace(ticket=t,next_sequence=i*2,timed_out=False)
                      for i,t in enumerate((original,permissions,fresh),1)])
        sequences=[]
        def wait(*a,**kw):sequences.append(kw['sequence_start']);kw['endpoint_observer_factory']();return next(results)
        odin=types.SimpleNamespace(path=Path('/fixture/odin'))
        with mock.patch.object(auto.transport,'pin_regular_file',return_value=contextlib.nullcontext(odin)), \
             mock.patch.object(auto.transport,'revalidate_pinned_path'), \
             mock.patch.object(auto.transition,'transaction_session',return_value=contextlib.nullcontext(object())), \
             mock.patch.object(auto.transition,'measured_usbfs_observer',return_value=object()), \
             mock.patch.object(auto.transition,'wait_for_single_live_endpoint',side_effect=wait), \
             mock.patch.object(auto.target,'download_identity',return_value={'exact':'lane'}), \
             mock.patch.object(auto.time,'sleep'):
            outcome=auto.observe(self.session,receipt,folder)
        self.assertEqual(outcome['status'],'EXACT_DOWNLOAD_OBSERVED')
        self.assertEqual(sequences,[0,2,4]);self.assertEqual(outcome['ticket']['device_identity'],fresh.device_identity)
        self.assertFalse(any(p.name.startswith('io-recover') for p in self.root.iterdir()))

    def test_late_or_unresolved_cue_never_enters_transfer(self):
        self.native();folder=self.root/'observe';folder.mkdir()
        receipt=records.publish(folder/'window.json',auto.window(self.adapter,self.request))
        with mock.patch.object(auto,'clock',return_value=self.now+auto.ARRIVAL_NS), \
             mock.patch.object(auto,'cue_settled',return_value=False), \
             mock.patch.object(auto.transition,'wait_for_single_live_endpoint') as wait:
            self.assertEqual(auto.observe(self.session,receipt,folder)['status'],'ATTACH_UNRESOLVED')
            wait.assert_not_called()


class V7WindowTests(WindowTests):
    report_version=7


class V8WindowTests(WindowTests):
    report_version=8


class V9WindowTests(WindowTests):
    report_version=9


class OwnerTests(prior.DownloadOwnerTests):
    def automatic(self,fault='after-control',status='EXACT_DOWNLOAD_OBSERVED'):
        current,device=self.operation(fault=fault)
        device.directory=current.directory
        window=dict(operation=records.pin(current.directory/'operation.json'),deadline_ns=records.clock()+1_000_000_000)
        original=device.transfer;overrides=[]
        def transfer(step,request,*,guard,before_launch,recovery_window=None):
            overrides.append(recovery_window)
            return original(step,request,guard=guard,before_launch=before_launch)
        device.transfer=transfer
        for name,value in (('selected',lambda r:True),('window',lambda *a:window),
                           ('observe',lambda *a:dict(status=status,observed_ns=records.clock()))):
            patch=mock.patch.object(auto,name,value);patch.start();self.addCleanup(patch.stop)
        return current,device,overrides

    def test_unknown_control_auto_a_once_without_new_native_effect(self):
        current,device,overrides=self.automatic()
        self.assertEqual(current.execute(attended=True)['state'],'ANDROID_CLOSED')
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.actions.count('download-control-once'),1)
        self.assertEqual(overrides[-1],records.pin(current.directory/auto.FOLDER/'window.json'))
        self.assertEqual(sum(r['event']=='effect-intent' and r['data']['role']=='A' and
                             r['data']['action']=='transfer' for r in current.rows()),1)
        with self.assertRaises(ValueError):current.recover(attended=True)

    def test_automatic_timeout_leaves_no_a_attempt_and_physical_path_works(self):
        current,device,overrides=self.automatic(status='DOWNLOAD_NOT_OBSERVED')
        self.assertEqual(current.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        self.assertEqual(device.installed,['N'])
        self.assertFalse(any(r['data'].get('step')=='recover-android' for r in current.rows()))
        self.assertEqual(current.recover(attended=True)['state'],'ANDROID_CLOSED')
        self.assertEqual(device.installed,['N','A']);self.assertIsNone(overrides[-1])

    def test_uncertain_a_never_replays_and_completed_a_only_health_resumes(self):
        current,device,_=self.automatic(fault=None)
        device.fail_after='install-android'
        self.assertEqual(current.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        before=list(device.installed)
        with self.assertRaises(KeyError):current.recover(attended=True)
        self.assertEqual(device.installed,before)
        # Complete raw transfer proof may be recovered; it is never retransferred.
        device.proof(prior.owner.Step('install-android','transfer','A'))
        self.assertEqual(current.recover(attended=True)['state'],'ANDROID_CLOSED')
        self.assertEqual(device.installed,['N','A'])


if __name__=='__main__':unittest.main()
