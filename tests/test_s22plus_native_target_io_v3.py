"""Fixed exact-target health brackets and production transfer classification."""
from pathlib import Path
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
        with mock.patch.object(target,'clock',side_effect=[1,3]), \
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
        def command(arguments,name,*,timeout):
            calls.append(arguments)
            return target.raw.publish_captured_bytes(self.directory,name,stdout=next(values).encode())
        with mock.patch.object(client,'command',side_effect=command),mock.patch.object(target.time,'sleep'):
            client.wait_ready(deadline_ns=target.clock()+10_000_000_000)
        self.assertEqual(calls[0],['devices','-l'])
        self.assertEqual(calls[-1],['-s','FIXTURE123','shell','getprop sys.boot_completed'])
        self.assertFalse(any('su' in part for command in calls for part in command))


if __name__=='__main__': unittest.main()
