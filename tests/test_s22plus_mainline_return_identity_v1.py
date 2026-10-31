"""Observed boot IDs survive bounded partial reads without replacing health."""
from pathlib import Path
import shlex
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_target_io_v3 as target
import s22plus_native_adapter_v3 as adapter
from s22plus_native_records_v3 import publish
import test_s22plus_native_target_io_v3 as baseline


class ReturnIdentityTests(unittest.TestCase):
    def setUp(self):
        self.fixture=baseline.TargetTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.directory=self.fixture.directory
        self.client=target.MainlineReturnAndroid(dict(path='/fixture'),self.fixture.binding,
            self.fixture.android,self.directory,guard=lambda:None)
        self.wire='boot_id='+self.fixture.properties['boot_id']+'\nboot_completed=1'

    def test_every_successful_eof_prefix_waits_without_becoming_ready(self):
        for end in range(len(self.wire)):
            with self.subTest(end=end):self.assertFalse(self.client.readiness_complete(self.wire[:end]))
        self.assertTrue(self.client.readiness_complete(self.wire))
        self.assertFalse(self.client.readiness_complete(self.wire[:-1]+'0'))

    def test_malformed_output_is_not_a_retry_or_readiness(self):
        for value in ('1','boot_id=x',self.wire.replace('-','x',1),self.wire.replace('boot_id','bootid'),
                self.wire.replace('=1','=2'),self.wire+'\nextra=1',self.wire.replace('\n','\n\n'),
                self.wire.replace('boot_completed','boot_complete'),self.wire.replace('abc','abC')):
            with self.subTest(value=value),self.assertRaises(ValueError):self.client.readiness_complete(value)

    def test_real_wait_loop_retains_all_truncations_and_only_uses_existing_commands(self):
        outputs=iter([self.wire[:end] for end in range(len(self.wire))]+[self.wire])
        calls=[]
        def command(arguments,name,*,timeout,before_launch=None):
            before_launch();calls.append((arguments,name,timeout))
            text=self.fixture.inventory if arguments==['devices','-l'] else next(outputs)
            return target.raw.publish_captured_bytes(self.directory,name,stdout=text.encode())
        with mock.patch.object(self.client,'command',side_effect=command),mock.patch.object(target.time,'sleep'):
            self.client.wait_ready(deadline_ns=target.clock()+10_000_000_000)
        self.assertEqual(len(calls),2*(len(self.wire)+1))
        self.assertTrue(all(args==['-s','FIXTURE123','shell',self.client.READY_COMMAND]
            for args,name,_ in calls if name.endswith('-boot')))
        self.assertFalse((self.directory/'health.json').exists())
        sample=target.raw.load_handle(self.directory/'wait-044-boot.capture.json')
        self.assertEqual(target.raw.read_stdout(sample,maximum=96),self.wire[:44].encode())

    def test_existing_vanished_read_continues_but_other_producer_failures_stop(self):
        for index,mode in enumerate(('vanished','stderr','rc','malformed')):
            folder=self.directory/mode;folder.mkdir();self.client.directory=folder;calls=[]
            def command(arguments,name,*,timeout,before_launch=None):
                before_launch();calls.append(name)
                if name.endswith('-inventory'):kw=dict(stdout=self.fixture.inventory.encode())
                elif name=='wait-001-boot':kw=dict(stdout=self.wire.encode())
                elif mode=='vanished':kw=dict(stdout=b'',returncode=1,stderr=b"adb: device 'FIXTURE123' not found\n")
                elif mode=='stderr':kw=dict(stdout=self.wire.encode(),stderr=b'error\n')
                elif mode=='rc':kw=dict(stdout=self.wire.encode(),returncode=7)
                else:kw=dict(stdout=b'boot_id=wrong')
                return target.raw.publish_captured_bytes(folder,name,**kw)
            with mock.patch.object(self.client,'command',side_effect=command),mock.patch.object(target.time,'sleep'):
                if mode=='vanished':self.client.wait_ready(deadline_ns=target.clock()+10_000_000_000)
                else:
                    with self.assertRaises((ValueError,target.raw.RawCaptureError)):
                        self.client.wait_ready(deadline_ns=target.clock()+10_000_000_000)
            self.assertEqual(len(calls),4 if mode=='vanished' else 2)
            self.assertTrue((folder/'wait-000-boot.capture.json').exists())

    def test_health_still_requires_all_seven_reads_and_same_boot(self):
        root='\n'.join(k+'='+v for k,v in dict(root='uid=0(root) gid=0(root)',
            **self.fixture.android['partition_sha256']).items())
        properties='\n'.join(k+'='+self.fixture.properties[k] for k in
            ('boot_id',*(k for k in self.fixture.properties if k!='boot_id')))
        for changed in (False,True):
            folder=self.directory/str(changed);folder.mkdir();self.client.directory=folder;calls=[]
            last=properties.replace(self.fixture.properties['boot_id'],'87654321-1234-1234-1234-123456789abc') if changed else properties
            texts=iter((self.fixture.inventory,self.fixture.binding['topology'],properties,root,
                self.fixture.inventory,self.fixture.binding['topology'],last))
            def command(arguments,name,*,timeout):
                calls.append(arguments)
                return target.raw.publish_captured_bytes(folder,name,stdout=next(texts).encode())
            with mock.patch.object(self.client,'command',side_effect=command):
                if changed:
                    with self.assertRaisesRegex(ValueError,'boot changed'):self.client.health()
                else:
                    value=self.client.health()
                    self.assertEqual(value,target.health_projection(value['captures'],self.fixture.binding,self.fixture.android))
            self.assertEqual(len(calls),7)
            self.assertEqual(calls[2][-1],'sh -c '+shlex.quote(self.client.PROPERTIES_COMMAND))
            self.assertTrue(self.client.PROPERTIES_COMMAND.startswith(self.client.BOOT_ID_COMMAND+'\n'))
            self.assertEqual((folder/'health.json').exists(),not changed)
        self.assertEqual(target.Android.PROPERTIES_COMMAND,target.PROPERTIES)
        self.assertTrue(target.Android.PROPERTIES_COMMAND.startswith("printf 'model='"))
        self.assertEqual(target.Android.READY_COMMAND,'getprop sys.boot_completed')

    def test_partial_read_loop_keeps_poll_bound_and_original_deadline(self):
        calls=[]
        def command(arguments,name,*,timeout,before_launch=None):
            before_launch();calls.append(name)
            text=self.fixture.inventory if name.endswith('-inventory') else self.wire[:20]
            return target.raw.publish_captured_bytes(self.directory,name,stdout=text.encode())
        with mock.patch.object(self.client,'command',side_effect=command),mock.patch.object(target.time,'sleep'), \
                mock.patch.object(target,'clock',return_value=1),self.assertRaisesRegex(ValueError,'exceeds bound'):
            self.client.wait_ready(deadline_ns=10_000_000_001)
        self.assertEqual(len(calls),512)
        calls.clear()
        with mock.patch.object(self.client,'command',side_effect=command), \
                mock.patch.object(target,'clock',return_value=2),self.assertRaises(TimeoutError):
            self.client.wait_ready(deadline_ns=1)
        self.assertEqual(calls,[])

    def test_every_truncated_first_property_read_fails_complete_health_projection(self):
        properties='\n'.join(k+'='+self.fixture.properties[k] for k in
            ('boot_id',*(k for k in self.fixture.properties if k!='boot_id')))
        complete=self.fixture.captures()
        for end in range(len(properties)):
            folder=self.directory/('prefix-'+str(end));folder.mkdir()
            partial=target.raw.publish_captured_bytes(folder,'02-health',stdout=properties[:end].encode())
            captures=list(complete);captures[2]=target.pin(partial.receipt_path)
            with self.subTest(end=end),self.assertRaises(ValueError):
                target.health_projection(captures,self.fixture.binding,self.fixture.android)

    def test_mainline_does_not_inherit_other_profiles_in_call_reobservation(self):
        with mock.patch.object(self.client,'command') as command,self.assertRaisesRegex(ValueError,'does not select'):
            self.client.health(reobserve_root_disappearance=True)
        command.assert_not_called()

    def test_adapter_selects_only_mainline_return_and_keeps_other_factories(self):
        for operation,step_name in ((op,step) for op in ('mainline-ram','loader-android','bootstrap')
                for step in ('android-final','recovery-health')):
            folder=self.directory/'workspace/private'/operation/step_name;folder.mkdir(parents=True)
            instance=adapter.Adapter(self.directory,folder)
            request=dict(operation=operation,N={'profile':'fixture'},A=self.fixture.android)
            task=dict(adb={'path':'/fixture'},target=self.fixture.binding)
            def health():publish(folder/('io-'+step_name)/'attempt-fixture/health.json',{'fixture':True})
            client=mock.Mock();client.health.side_effect=health
            step=mock.Mock(name='step');step.name=step_name
            with mock.patch.object(instance,'configuration',return_value=task), \
                    mock.patch.object(instance,'android',return_value=client) as ordinary, \
                    mock.patch.object(target,'MainlineReturnAndroid',return_value=client) as mainline, \
                    mock.patch.object(adapter.uuid,'uuid4',return_value=mock.Mock(hex='fixture')):
                result=instance.android_health(step,request,guard=lambda:None)
            self.assertEqual(mainline.call_count,operation=='mainline-ram')
            self.assertEqual(ordinary.call_count,operation!='mainline-ram')
            self.assertEqual(result['action'],'health');client.wait_ready.assert_called_once();client.health.assert_called_once()


if __name__=='__main__':unittest.main()
