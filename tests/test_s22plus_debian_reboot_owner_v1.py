"""Finite two-boot owner: uncertainty, durable result repair and no control replay."""
from pathlib import Path
import types
import unittest
from unittest import mock

import test_s22plus_debian_autoboot_v1 as prior
import s22plus_debian_reboot_access_v1 as reboot
import s22plus_debian_access_v1 as access
import s22plus_native_adapter_v3 as adapter
import s22plus_debian_autoboot_session_v1 as coordinator


class Device(prior.Device):
    namespace='p458'
    def prepare(self,*args,**kw):return dict(target='fixture',N=dict(namespace=self.namespace))


class FixtureAccess(prior.previous.FixtureAccess):
    def __init__(self,device,request,*,phase):super().__init__(device,request);self.phase=phase
    def health(self,step,guard):
        guard();self.device.assert_mode('Debian');self.device.actions.append(step.name)
        if self.device.fail_after==step.name:raise OSError('selected boot health failed')
        return self.device.proof(step)
    def reboot(self,step,guard,before):
        guard();self.device.assert_mode('Debian');before(dict(fixed='reboot',phase=1))
        self.device.actions.append('reboot-once')
        if self.device.fail_after=='reboot':raise OSError('reboot delivered; ACK lost')
        return self.device.proof(step)


class OwnerTests(unittest.TestCase):
    setUp=prior.previous.harness.OwnerTests.setUp
    def operation(self):
        device=Device();directory=prior.previous.owner.prepare_operation(self.root,self.grant,
            operation='debian-autoboot',adapter=device)
        patch=mock.patch.object(reboot,'Access',FixtureAccess);patch.start();self.addCleanup(patch.stop)
        return prior.previous.owner.Session(self.root,directory,device),device

    def test_one_n_one_reboot_two_observations_one_shutdown_and_one_a(self):
        session,device=self.operation();value=session.execute(attended=True)
        self.assertEqual(value['state'],'AWAITING_PHYSICAL_DOWNLOAD')
        self.assertEqual(device.installed,['N'])
        self.assertEqual(device.actions.count('reboot-once'),1)
        self.assertEqual(device.actions.count('debian-health'),1);self.assertEqual(device.actions.count('debian-health-second'),1)
        self.assertEqual(device.actions.count('shutdown-once'),1)
        device.mode='Download';session.resume(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertIsNone(self.f1)
        self.assertEqual([r['data']['step'] for r in session.rows() if r['event']=='effect-intent'],
            ['android-download','install-native-first','debian-reboot','debian-shutdown','install-android'])

    def test_uncertain_controls_and_failed_second_window_never_repeat(self):
        for fault in ('reboot','debian-health-second','shutdown'):
            with self.subTest(fault=fault):
                self.setUp();session,device=self.operation();device.fail_after=fault
                self.assertEqual(session.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
                before=list(device.actions);session.recover(attended=True)
                self.assertEqual(device.installed,['N','A'])
                for name in ('reboot-once','shutdown-once','debian-health-second'):
                    self.assertEqual(device.actions.count(name),before.count(name))
                self.assertIsNone(self.f1)

    def test_lost_reboot_result_publication_does_not_send_it_again(self):
        session,device=self.operation();publish=prior.previous.owner.publish
        def cut(path,value):
            if Path(path).name=='debian-reboot.json':raise OSError('result publication cut')
            return publish(path,value)
        with mock.patch.object(prior.previous.owner,'publish',side_effect=cut),self.assertRaises(
                prior.previous.owner.ResultPublicationError):session.execute(attended=True)
        # Resume the same coordinator walk from durable step-start/raw proof.
        self.assertEqual(coordinator.Coordinator(session).walk(allow_return=False)['state'],'AWAITING_PHYSICAL_DOWNLOAD')
        self.assertEqual(device.actions.count('reboot-once'),1)
        device.mode='Download';session.resume(attended=True);self.assertEqual(device.installed,['N','A'])

    def test_second_window_is_reserved_before_transfer(self):
        grant=dict(opened_ns=0,deadline_ns=2000_000_000_000)
        for namespace in ('p458','p459'):
            image=dict(profile='debian-autoboot-v1',namespace=namespace)
            adapter.before_window_transfer(image,grant,439_000_000_000)
            for now in (440_000_000_000,800_000_000_000):
                with self.subTest(namespace=namespace,now=now),self.assertRaises(ValueError):
                    adapter.before_window_transfer(image,grant,now)
        adapter.before_window_transfer(dict(image,namespace='p456'),grant,799_000_000_000)


class CronOwnerTests(OwnerTests):
    def operation(self):
        with mock.patch.object(Device,'namespace','p459'):return super().operation()


class ControlTests(unittest.TestCase):
    def handle(self,body=b'body\nDEBIAN_REBOOT_REQUEST_ACCEPTED\n',error=b'',code=0,**changes):
        value=types.SimpleNamespace(timed_out=False,output_exceeded=False,producer_error_type=None,returncode=code)
        for k,v in changes.items():setattr(value,k,v)
        return value,body,error
    def parse(self,row,command='reboot'):
        handle,stdout,stderr=row
        with mock.patch.object(access.raw,'read_stdout',return_value=stdout),mock.patch.object(access.raw,'read_stderr',return_value=stderr):
            return reboot.capture_body(handle,'example.invalid',command)
    def test_accepted_raw_forms_and_failures(self):
        self.assertEqual(self.parse(self.handle()),b'body\n')
        self.assertEqual(self.parse(self.handle(code=255,error=b'Connection to example.invalid closed by remote host.\r\n')),b'body\n')
        for row in (self.handle(timed_out=True),self.handle(output_exceeded=True),self.handle(producer_error_type='OSError'),
            self.handle(code=1),self.handle(error=b'diagnostic'),self.handle(code=255),self.handle(body=b''),
            self.handle(body=b'DEBIAN_REBOOT_REQUEST_ACCEPTED\ntrailing'),self.handle(body=b'DEBIAN_SHUTDOWN_REQUEST_ACCEPTED\n')):
            with self.assertRaises(ValueError):self.parse(row)


class NetworkTests(unittest.TestCase):
    def fixture(self):
        current=reboot.Access.__new__(reboot.Access);current.reboot_phase=2
        current.request=dict(operation='debian-autoboot',N=dict(namespace='p458'))
        current.plan=dict(candidate=dict(run_id='a'*32),network_uuid='owned-uuid',link=dict(host_mac='fixture-mac'))
        current.adapter=types.SimpleNamespace(folder=lambda name:Path('/fixture')/name)
        return current
    def test_foreign_connection_is_rejected_before_mutation(self):
        selected=self.fixture();previous=dict(interface='old0');found=dict(interface='new0')
        expected=selected.network_expected(previous)
        for index in range(4):
            changed=list(expected);changed[index]='foreign';calls=[]
            selected.host=lambda argv,*args:(calls.append(argv) or {})
            with mock.patch.object(reboot,'read',side_effect=[dict(uuid='owned-uuid',endpoint=previous),previous]),\
                 mock.patch.object(reboot,'verify'),mock.patch.object(access.raw,'load_handle'),\
                 mock.patch.object(access.raw,'require_success'),mock.patch.object(access.raw,'read_stderr',return_value=b''),\
                 mock.patch.object(access.raw,'read_stdout',return_value=('\n'.join(changed)+'\n').encode()):
                with self.assertRaisesRegex(ValueError,'original owned'):selected.configure_link(Path('/new'),found,lambda:None)
            self.assertEqual(len(calls),1);self.assertEqual(calls[0][-4:],['connection','show','uuid','owned-uuid'])
    def test_temporary_rebind_and_interrupted_cleanup_keep_exact_ownership(self):
        selected=self.fixture();previous=dict(interface='old0');found=dict(interface='new0');calls=[]
        selected.host=lambda argv,*args:(calls.append(argv) or {})
        with mock.patch.object(reboot,'read',side_effect=[dict(uuid='owned-uuid',endpoint=previous),previous]),\
             mock.patch.object(reboot,'verify'),mock.patch.object(access.raw,'load_handle'),\
             mock.patch.object(selected,'network_inspection'),mock.patch.object(access,'endpoint',return_value=found),\
             mock.patch.object(reboot,'publish'):
            selected.configure_link(Path('/new'),found,lambda:None)
        self.assertEqual(calls[1],['connection','modify','--temporary','uuid','owned-uuid','connection.interface-name','new0'])
        self.assertEqual(calls[2],['connection','up','uuid','owned-uuid','ifname','new0'])
        with mock.patch.object(reboot,'read',return_value=dict(uuid='owned-uuid',endpoint=previous)):
            self.assertEqual(selected.cleanup_interfaces(dict(endpoint=found)),['old0','new0'])
        with mock.patch.object(reboot,'read',return_value=dict(uuid='foreign',endpoint=previous)),self.assertRaises(ValueError):
            selected.cleanup_interfaces(dict(endpoint=found))

class DeadlineTests(unittest.TestCase):
    def test_second_window_is_fixed_at_durable_intent_and_clipped_to_grant(self):
        method=reboot.Access.basis;selected=reboot.Access.__new__(reboot.Access)
        selected.reboot_phase=2;selected.adapter=types.SimpleNamespace(directory=Path('/fixture'),folder=lambda name:Path('/fixture')/name)
        selected.request=dict(grant={});selected.grant=dict(deadline_ns=500_000_000_000,host_boot='fixture')
        control=dict(action='debian-reboot');detail=dict(command='reboot');receipt={'result':1}
        rows=[dict(event='effect-intent',boottime_ns=100_000_000_000,data=dict(step='debian-reboot',action='debian-reboot',role='N',detail=detail)),
            dict(event='step-complete',boottime_ns=150_000_000_000,data=dict(step='debian-reboot',result=receipt))]
        def reader(path):return detail if str(path).endswith('intent.json') else control
        with mock.patch.object(reboot,'Access') as first,mock.patch.object(reboot,'Journal') as journal,\
             mock.patch.object(reboot,'read',side_effect=reader),mock.patch.object(reboot,'verify',return_value=Path('/result')),\
             mock.patch.object(reboot,'pin',return_value={}):
            first.return_value.rederive_control.return_value=control;journal.return_value.rows.return_value=rows
            value=method(selected);self.assertEqual(value['deadline_ns'],460_000_000_000)
            self.assertEqual(method(selected),value)
            selected.grant['deadline_ns']=400_000_000_000
            self.assertEqual(method(selected)['deadline_ns'],400_000_000_000)
            rows.append(rows[0])
            with self.assertRaises(ValueError):method(selected)


if __name__=='__main__':unittest.main()
