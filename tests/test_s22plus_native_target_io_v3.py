"""Fixed exact-target health brackets and production transfer classification."""
from pathlib import Path
from dataclasses import replace
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_target_io_v3 as target
from s22plus_native_records_v3 import pin


class TargetTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.directory=Path(temporary.name)
        self.binding=dict(serial='FIXTURE123',topology=target.lane.SOURCE_TOPOLOGY)
        self.android=dict(partition_sha256={name:str(index)*64 for index,name in enumerate(('boot','vendor_boot','dtbo','recovery'),1)})
        self.properties=dict(model='SM-S906N',device='g0q',bootloader='S906NKSS7FYG8',incremental='S906NKSS7FYG8',
            boot_completed='1',bootanim='stopped',verified_boot_state='orange',
            boot_id='12345678-1234-1234-1234-123456789abc',kernel_release='fixture-kernel')
        self.inventory='List of devices attached\nFIXTURE123 device model:SM_S906N device:g0q transport_id:1\n'

    def captures(self, *, last=None, root=None, inventory=None):
        properties=lambda value:'\n'.join(key+'='+item for key,item in value.items())
        health=dict(root=root or 'uid=0(root) gid=0(root) groups=0(root)',**self.android['partition_sha256'])
        texts=[inventory or self.inventory,self.binding['topology'],properties(self.properties),properties(health),
            self.inventory,self.binding['topology'],properties(last or self.properties)]
        folder=self.directory/str(len(list(self.directory.iterdir()))); folder.mkdir()
        return [pin(target.raw.publish_captured_bytes(folder,str(index),stdout=text.encode()).receipt_path)
            for index,text in enumerate(texts)]

    def test_seven_command_same_boot_bracket_and_numeric_root(self):
        value=target.health_projection(self.captures(),self.binding,self.android)
        self.assertTrue(value['rooted_android_health'])
        self.assertEqual(value['partition_sha256'],self.android['partition_sha256'])
        for root in ('uid=1000(root) gid=0(root)','uid=root gid=root','uid=0(root) gid=1000(root)'):
            with self.subTest(root=root),self.assertRaises(ValueError):
                target.health_projection(self.captures(root=root),self.binding,self.android)

    def test_changed_boot_wrong_target_and_duplicate_fields_rejected(self):
        for changes in (dict(boot_id='87654321-1234-1234-1234-123456789abc'),dict(boot_completed='0'),dict(verified_boot_state='green')):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                target.health_projection(self.captures(last=dict(self.properties,**changes)),self.binding,self.android)
        foreign=self.inventory.replace('FIXTURE123','WRONG456')
        with self.assertRaises(ValueError): target.health_projection(self.captures(inventory=foreign),self.binding,self.android)
        with self.assertRaises(ValueError): target.fields('root=0\nroot=0',{'root'})

    def test_inventory_selection_precedes_target_command(self):
        calls=[]
        client=target.Android(dict(path='/fixture'),self.binding,self.android,self.directory,guard=lambda:None)
        def command(arguments,name,*,timeout):
            calls.append(arguments)
            return target.raw.publish_captured_bytes(self.directory,name,
                stdout=self.inventory.replace('FIXTURE123','WRONG456').encode())
        with mock.patch.object(client,'command',side_effect=command),self.assertRaises(ValueError): client.health()
        self.assertEqual(calls,[['devices','-l']])

    def test_download_requires_stable_exact_coordinates_and_no_serial(self):
        root=self.directory/'usb'; root.mkdir()
        node=root/target.lane.SOURCE_TOPOLOGY.removeprefix('usb:'); node.mkdir()
        fields=dict(busnum='2',devnum='7',idVendor='04e8',idProduct='685d',product='SAMSUNG USB',manufacturer='Samsung')
        for key,value in fields.items(): (node/key).write_text(value+'\n')
        self.assertEqual(target.download_identity('/dev/bus/usb/002/007',usb_root=root)['fields']['serial'],None)
        with self.assertRaises(ValueError): target.download_identity('/dev/bus/usb/002/008',usb_root=root)
        with self.assertRaises(ValueError):
            target.download_identity('/dev/bus/usb/003/007',topology=target.lane.CANDIDATE_TOPOLOGY,usb_root=root)
        (node/'serial').write_text('foreign')
        with self.assertRaises(ValueError): target.download_identity('/dev/bus/usb/002/007',usb_root=root)

    def test_odin_completion_needs_markers_and_complete_producer(self):
        complete=b'Setup Connection\nUpload Binaries\nboot.img.lz4 100%\nClose Connection\n'
        for index,(stdout,stderr,rc,expected) in enumerate(((complete,b'',0,True),(b'',complete,0,True),
                (complete,b'',1,False),(b'ok',b'',0,False),(b'Fail parse',b'',0,False))):
            handle=target.raw.publish_captured_bytes(self.directory,'odin-'+str(index),stdout=stdout,stderr=stderr,returncode=rc)
            if expected: self.assertTrue(target.transfer_completed(handle))
            else:
                with self.assertRaises(ValueError): target.transfer_completed(handle)

    def test_departure_keeps_original_deadline_and_rejects_identity_drift(self):
        before=dict(snapshot=dict(path='/dev/bus/usb/002/007'),identity={'generation':'old'})
        with mock.patch.object(target,'clock',side_effect=[1,2,3]), \
                mock.patch.object(target.usbfs,'snapshot_node',side_effect=target.usbfs.UsbfsEndpointDeparture('/dev/bus/usb/002/007')):
            result=target.wait_departure(before,self.directory,deadline_ns=4,guard=lambda:None)
        self.assertEqual((result['observed_ns'],result['deadline_ns']),(3,4))
        with mock.patch.object(target,'clock',side_effect=[1,5]), \
                mock.patch.object(target.usbfs,'snapshot_node',side_effect=target.usbfs.UsbfsEndpointDeparture('/dev/bus/usb/002/007')), \
                self.assertRaises(ValueError):
            target.wait_departure(before,self.directory,deadline_ns=4,guard=lambda:None)

        with mock.patch.object(target,'clock',return_value=1), \
                mock.patch.object(target.usbfs,'snapshot_node',return_value=object()), \
                mock.patch.object(target.usbfs,'immutable_identity',return_value={'generation':'changed'}), \
                self.assertRaisesRegex(ValueError,'without proved departure'):
            target.wait_departure(before,self.directory,deadline_ns=4,guard=lambda:None)

    def test_android_readiness_observes_only_bound_target_before_health(self):
        client=target.Android(dict(path='/fixture'),self.binding,self.android,self.directory,guard=lambda:None)
        values=iter(('List of devices attached\n',self.inventory,'0',self.inventory,'1'))
        calls=[]
        def command(arguments,name,*,timeout,before_launch=None):
            if before_launch:before_launch()
            calls.append(arguments)
            return target.raw.publish_captured_bytes(self.directory,name,stdout=next(values).encode())
        with mock.patch.object(client,'command',side_effect=command),mock.patch.object(target.time,'sleep'):
            client.wait_ready(deadline_ns=target.clock()+10_000_000_000)
        self.assertEqual(calls[0],['devices','-l'])
        self.assertEqual(calls[-1],['-s','FIXTURE123','shell','getprop sys.boot_completed'])
        self.assertFalse(any('su' in part for command in calls for part in command))

    def return_client(self, *, partial=True, diagnostics=None, root_rc=1, second_failure=False,
                      changed_boot=False):
        """Sanitized P462 shape: partial rc0 properties, then completed missing device."""
        prop='\n'.join(k+'='+v for k,v in self.properties.items())
        root='\n'.join(k+'='+v for k,v in dict(root='uid=0(root) gid=0(root)',
            **self.android['partition_sha256']).items())
        missing=b"adb: device 'FIXTURE123' not found\n"
        prefix=[dict(stdout=self.inventory.encode()),dict(stdout=self.binding['topology'].encode()),
            dict(stdout=('\n'.join(prop.splitlines()[:6]) if partial else prop).encode()),
            dict(stdout=b'',stderr=missing if diagnostics is None else diagnostics,returncode=root_rc)]
        newprop=prop.replace(self.properties['boot_id'],'87654321-1234-1234-1234-123456789abc') if changed_boot else prop
        texts=[self.inventory.replace('transport_id:1','transport_id:2'),self.binding['topology'],
            newprop,root,self.inventory.replace('transport_id:1','transport_id:2'),self.binding['topology'],newprop]
        replacement=[dict(stdout=t.encode()) for t in texts]
        if second_failure:replacement[3]=dict(stdout=b'',stderr=missing,returncode=1)
        values=iter(prefix+[dict(stdout=self.inventory.encode()),dict(stdout=b'1')]+replacement)
        calls=[]
        class Client(target.Android):
            def command(self, arguments, name, *, timeout, before_launch=None):
                if before_launch:before_launch()
                calls.append((self.directory,name,arguments,timeout))
                return target.raw.publish_captured_bytes(self.directory,name,**next(values))
        client=Client(dict(path='/fixture'),self.binding,self.android,self.directory,guard=lambda:None)
        return client,calls

    def test_return_disappearance_replaces_whole_bracket_and_keeps_failure(self):
        client,calls=self.return_client()
        result=client.health(reobserve_root_disappearance=True)
        self.assertEqual(len(calls),13)
        failed=target.raw.load_handle(self.directory/'03-health.capture.json')
        self.assertEqual(failed.returncode,1)
        self.assertTrue(all(Path(c['path']).parent==self.directory/'reobservation-1' for c in result['captures']))
        self.assertEqual(target.health_projection(result['captures'],self.binding,self.android),result)
        self.assertTrue((self.directory/'health.json').is_file())
        self.assertEqual(client.directory,self.directory)

    def test_legacy_health_and_nonmatching_diagnostic_do_not_reobserve(self):
        for index,kwargs in enumerate(({},dict(diagnostics=b'permission denied\n'),
                dict(diagnostics=b"adb: device 'OTHER' not found\n"),dict(root_rc=127))):
            with self.subTest(kwargs=kwargs):
                self.directory=self.directory/str(index);self.directory.mkdir()
                client,calls=self.return_client(**kwargs)
                with self.assertRaises((ValueError,target.raw.RawCaptureError)):
                    client.health(reobserve_root_disappearance=bool(index))
                self.assertEqual(len(calls),4)
                self.assertFalse((self.directory/'health.json').exists())

    def test_replacement_has_no_third_attempt_and_keeps_complete_boot_anchor(self):
        for index,kwargs in enumerate((dict(second_failure=True),dict(partial=False,changed_boot=True))):
            with self.subTest(kwargs=kwargs):
                self.directory=self.directory/str(index);self.directory.mkdir()
                client,calls=self.return_client(**kwargs)
                with self.assertRaises((ValueError,target.raw.RawCaptureError)):
                    client.health(reobserve_root_disappearance=True)
                self.assertLessEqual(len(calls),13)
                self.assertFalse((self.directory/'health.json').exists())

    def test_reobservation_does_not_renew_deadline_after_guard_or_late_result(self):
        client,calls=self.return_client()
        with mock.patch.object(target,'clock',return_value=100),self.assertRaisesRegex(ValueError,'deadline'):
            client.health(reobserve_root_disappearance=True,deadline_ns=99)
        self.assertEqual(calls,[])
        now=[1_000_000_000]
        def guard():now[0]+=1_000_000_000
        client.guard=guard
        with mock.patch.object(target,'clock',side_effect=lambda:now[0]),self.assertRaisesRegex(ValueError,'deadline'):
            client.health(reobserve_root_disappearance=True,deadline_ns=5_000_000_000)
        self.assertLessEqual(len(calls),2)
        self.assertFalse((self.directory/'health.json').exists())

    def test_zero_deadline_and_late_final_projection_do_not_publish_health(self):
        client,calls=self.return_client()
        with self.assertRaisesRegex(ValueError,'deadline'):
            client.health(reobserve_root_disappearance=True,deadline_ns=0)
        self.assertEqual(calls,[])
        now=[1_000_000_000];original=target.health_projection
        def late(*args):
            result=original(*args);now[0]=300_000_000_000;return result
        with mock.patch.object(target,'clock',side_effect=lambda:now[0]), \
                mock.patch.object(target,'health_projection',side_effect=late), \
                self.assertRaisesRegex(ValueError,'deadline'):
            client.health(reobserve_root_disappearance=True)
        self.assertFalse((self.directory/'health.json').exists())

    def test_owner_guard_failure_after_fourth_capture_cannot_trigger_reobservation(self):
        client,calls=self.return_client()
        def guard():
            if len(calls)==4:raise target.raw.RawCaptureError('owner source check stopped')
        client.guard=guard
        with self.assertRaisesRegex(target.raw.RawCaptureError,'owner source check stopped'):
            client.health(reobserve_root_disappearance=True)
        self.assertEqual(len(calls),4)
        self.assertFalse((self.directory/'reobservation-1').exists())

    def test_root_capture_handle_mismatch_cannot_become_a_disappearance(self):
        client,calls=self.return_client();original=type(client).command
        def forged(instance,*args,**kwargs):
            handle=original(instance,*args,**kwargs)
            return replace(handle,returncode=0) if len(calls)==4 else handle
        with mock.patch.object(type(client),'command',new=forged),self.assertRaisesRegex(ValueError,'handle differs'):
            client.health(reobserve_root_disappearance=True)
        self.assertEqual(len(calls),4)
        self.assertFalse((self.directory/'reobservation-1').exists())


if __name__=='__main__': unittest.main()
