"""Filesystem/run fixtures; only native character-device snapshots are synthetic."""
from dataclasses import replace
from pathlib import Path
import os
import stat
from types import SimpleNamespace
from unittest import mock
import sys
sys.path.insert(0,str(Path('workspace/public/src/scripts/revalidation').resolve()))
import s22plus_native_usb_departure_v1 as departure
import s22plus_fyg8_p366_return_host as return_host


class Fixture:
    def __init__(self, root):
        self.root=Path(root).resolve();self.root.mkdir(exist_ok=True)
        self.usb_path=self.root/'sysfs/3-1.3';self.usb_path.mkdir(parents=True,exist_ok=True)
        (self.usb_path/'busnum').write_text('3\n');(self.usb_path/'devnum').write_text('77\n')
        self.endpoint=SimpleNamespace(topology='3-1.3',usb_path=self.usb_path,identity_sha256='e'*64)
        self.snapshot=departure.usbfs.UsbfsNodeSnapshot(path='/dev/bus/usb/003/077',
            st_dev=1,st_ino=123,st_rdev=os.makedev(189,332),st_nlink=1,
            st_file_type=stat.S_IFCHR,st_mode=0o660,st_uid=0,st_gid=0,
            birth_time_ns=123456789,device_major=189,device_minor=332,
            st_atime_ns=1,st_ctime_ns=1,st_mtime_ns=1)
    def capture(self,run_dir,binding,request):
        with mock.patch.object(departure,'_snapshot',return_value=self.snapshot):
            return departure.capture_binding(run_dir,endpoint=self.endpoint,binding=binding,request=request)
    def intent(self,run_dir):
        run_dir=Path(run_dir);run_dir.mkdir(exist_ok=True)
        request=dict(run_id_hex=return_host.RUN_ID,mode='download',sequence=5,
            boot_id_semantic=return_host.spec.BOOT_ID_SEMANTIC,
            boot_receipt_semantic=return_host.spec.BOOT_RECEIPT_SEMANTIC,
            nonce_sha256='1'*64,kernel_boot_identity_sha256='2'*64)
        binding={'manifest_id':'p366-fixture','binding_sha256':'a'*64}
        receipt=self.capture(run_dir,binding,request)
        lane={'accepted_for_p324':True,'observation_phase':'before-native-return-control',
            'native_usb_departure_binding':receipt}
        ir=return_host.write_intent(run_dir,binding=binding,endpoint_identity_sha256='e'*64,lane=lane,request=request)
        value,_=return_host.read_intent(run_dir,binding=binding)
        return value,ir
    def absent(self,*args):
        raise departure.usbfs.UsbfsEndpointDeparture(self.snapshot.path)


class Clock:
    def __init__(self,intent):self.now=intent['created_monotonic_ns']+1
    def monotonic_ns(self):return self.now
    def sleep(self,seconds):self.now+=int(seconds*1e9)
