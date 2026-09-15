"""Real subprocess/raw joins for Android GPT, statfs and reboot persistence."""
import base64
import copy
import json
from pathlib import Path
import shlex
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'workspace/public/src/scripts/revalidation'),str(ROOT/'workspace/public/src/scripts/analysis')]
import s22plus_native_gpt_android_v1 as android
import s22plus_native_gpt_profile_v1 as profile
import s22plus_native_gpt_session_v1 as coordinator
import s22plus_native_adapter_v3 as adapter
import s22plus_native_session_v3 as owner
import s22plus_native_records_v3 as records
import test_s22plus_native_target_io_v3 as health_fixture
from test_s22plus_native_gpt_profile_v1 import binding


def metadata(sealed,kind='proposed'):
    user=profile.NEW_USER if kind=='proposed' else profile.OLD_USER
    rows=[b'/sys/devices/platform/soc/1d84000.ufshc/host0/target0:0:0/0:0:0:0/block/sda/sda40',
        b'8:40',str(3726848*8).encode(),str(user).encode(),b'8:0',str(62305280*8).encode(),b'4096',b'8:0']
    bracket=b'\n'.join(rows)+b'\n'
    return b'G0\n'+bracket+sealed[kind]+b'G1\n'+bracket+b'END\n'


class AndroidTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.directory=self.root/'workspace/private/operation'
        self.directory.mkdir(parents=True);self.client=adapter.Adapter(self.root,self.directory)
        self.fixture=health_fixture.TargetTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        bound,self.sealed=binding(self.directory)
        self.request=dict(operation='gpt-reserve',A=self.fixture.android,N=dict(gpt=bound))
        records.publish(self.directory/'operation.json',self.request)
        self.basis=dict(layout='proposed',initialization='stock-reset',geometry=dict(
            status='PASS_GEOMETRY_ONLY',block_count=25023740,segment0_block=512))
        self.configuration=dict(target=self.fixture.binding,adb=None)
        self.outputs={};self.argvlog=self.directory/'argv.jsonl';self.config=self.directory/'responses.json'
        self.program=self.directory/'adb-fixture'
        self.program.write_text('#!/usr/bin/env python3\nimport base64,json,pathlib,sys\n'
            +f'p=pathlib.Path({str(self.config)!r});log=pathlib.Path({str(self.argvlog)!r})\n'
            +'args=sys.argv[1:]\nwith log.open("a") as stream:stream.write(json.dumps(args)+"\\n")\n'
            +'row=json.loads(p.read_text())[json.dumps(args)]\n'
            +'sys.stdout.buffer.write(base64.b64decode(row[0]));sys.stdout.buffer.flush()\n'
            +'sys.stderr.buffer.write(base64.b64decode(row[1]));sys.stderr.buffer.flush()\nsys.exit(row[2])\n')
        self.program.chmod(0o700);self.configuration['adb']=records.pin(self.program)
        serial=self.fixture.binding['serial']
        text=lambda value:'\n'.join(k+'='+v for k,v in value.items())
        self.put(['devices','-l'],self.fixture.inventory)
        self.put(['-s',serial,'get-devpath'],self.fixture.binding['topology'])
        self.put(['-s',serial,'shell','getprop sys.boot_completed'],'1')
        self.put(['-s',serial,'shell','sh -c '+shlex.quote(adapter.target.PROPERTIES)],text(self.fixture.properties))
        self.put(['-s',serial,'shell','su -c '+shlex.quote(adapter.target.ROOT_HEALTH)],
            text(dict(root='uid=0(root) gid=0(root)',**self.fixture.android['partition_sha256'])))
        self.put(['-s',serial,'features'],'shell_v2\n')
        self.metadata_args=['-s',serial,'shell','-T','su -c '+shlex.quote(android.census.SCRIPT)]
        self.stat_args=['-s',serial,'shell','su -c '+shlex.quote(android.STAT_SCRIPT)]
        self.put(self.metadata_args,metadata(self.sealed))
        self.stat_text=f'NATIVE_PARTITION 41 {28750592*8} {profile.NATIVE_SECTORS} native_data\nF2FS_STAT 4096 25023228 900 1000 f2f52010\n'
        self.put(self.stat_args,self.stat_text)
        for patch in (mock.patch.object(self.client,'configuration',return_value=self.configuration),
                mock.patch.object(coordinator,'android_basis',return_value=self.basis)):
            patch.start();self.addCleanup(patch.stop)

    def put(self,args,stdout,stderr=b'',returncode=0):
        if isinstance(stdout,str):stdout=stdout.encode()
        if isinstance(stderr,str):stderr=stderr.encode()
        self.outputs[json.dumps(args)]=[base64.b64encode(stdout).decode(),base64.b64encode(stderr).decode(),returncode]
        self.config.write_text(json.dumps(self.outputs))

    def run_health(self,name='android-initial'):
        step=owner.Step(name,'health','A')
        return step,android.observe(self.client,step,self.request,guard=lambda:None)

    def test_actual_raw_read_and_statfs_are_bracketed_by_rooted_health(self):
        step,value=self.run_health()
        self.assertEqual(value['gpt_android']['metadata']['status'],'PASS_EXACT_GPT')
        self.assertEqual(value['gpt_android']['storage']['total_bytes'],102495141888)
        self.assertTrue(value['gpt_android']['storage']['native_partition_present'])
        calls=[json.loads(line) for line in self.argvlog.read_text().splitlines()]
        self.assertEqual(calls.count(self.metadata_args),1);self.assertEqual(calls.count(self.stat_args),1)
        metadata_index=calls.index(self.metadata_args)
        self.assertLess(calls.index(['devices','-l']),metadata_index)
        self.assertGreater(max(i for i,a in enumerate(calls) if a==['devices','-l']),metadata_index)
        with mock.patch.object(android.raw,'acquire_command',side_effect=AssertionError('H0 replay issued I/O')):
            self.assertEqual(value,android.rederive(self.client,step,self.request))

    def test_failed_metadata_producer_preserves_both_raw_streams_and_final_health(self):
        self.put(self.metadata_args,b'partial',b'read failure',1)
        with self.assertRaises((ValueError,android.raw.RawCaptureError)):self.run_health()
        folder=next(self.client.folder('android-initial').glob('attempt-*'))
        handle=android.raw.load_handle(folder/'read/metadata.capture.json')
        self.assertEqual(android.raw.read_stdout(handle,maximum=65536),b'partial')
        self.assertEqual(android.raw.read_stderr(handle,maximum=16384),b'read failure')
        self.assertTrue((folder/'after/health.json').exists())
        calls=[json.loads(line) for line in self.argvlog.read_text().splitlines()]
        self.assertEqual(calls.count(self.metadata_args),1)

    def test_published_health_can_be_reconstructed_after_aggregate_cut(self):
        original=android.publish
        def fail(path,value):
            if Path(path).name=='result.json':raise OSError('aggregate store unavailable')
            return original(path,value)
        with mock.patch.object(android,'publish',side_effect=fail),self.assertRaises(owner.ResultPublicationError):
            self.run_health()
        before=self.argvlog.read_bytes()
        value=android.rederive(self.client,owner.Step('android-initial','health','A'),self.request)
        self.assertEqual(value['gpt_android']['metadata']['status'],'PASS_EXACT_GPT')
        self.assertEqual(self.argvlog.read_bytes(),before)

    def test_changed_gpt_native_extent_and_old_or_wrong_reported_capacity_fail(self):
        raw=metadata(self.sealed);bad=bytearray(raw);bad[raw.index(b'EFI PART')+16]^=1
        with self.assertRaises(ValueError):android.metadata(bytes(bad),self.sealed,'proposed')
        for text in (self.stat_text.replace('25023228','58577907'),
                self.stat_text.replace('native_data','userdata'),self.stat_text.replace('f2f52010','ef53'),
                self.stat_text.replace(str(profile.NATIVE_SECTORS),str(profile.NATIVE_SECTORS-8))):
            with self.subTest(text=text),self.assertRaises(ValueError):android.storage_stat(text,self.basis)

    def test_reboot_compares_changed_boot_and_total_capacity_but_not_free_space(self):
        _,first=self.run_health();records.publish(self.directory/'android-initial.json',first)
        records.publish(self.directory/'android-reboot.json',dict(fixture='one reboot intent and proof'))
        serial=self.fixture.binding['serial'];props=dict(self.fixture.properties,boot_id='87654321-1234-1234-1234-123456789abc')
        self.put(['-s',serial,'shell','sh -c '+shlex.quote(adapter.target.PROPERTIES)],
            '\n'.join(k+'='+v for k,v in props.items()))
        self.put(self.stat_args,self.stat_text.replace('900 1000','700 850'))
        _,last=self.run_health('android-final')
        with mock.patch.object(self.client,'validate_result'):
            proof=android.reboot_persistence(self.client,self.request,last)
            self.assertEqual(proof['status'],'PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT')
            wrong=copy.deepcopy(last);wrong['health']=first['health']
            with self.assertRaisesRegex(ValueError,'new boot'):android.reboot_persistence(self.client,self.request,wrong)
            wrong=copy.deepcopy(last);wrong['gpt_android']['storage']['total_bytes']-=4096
            with self.assertRaisesRegex(ValueError,'capacity changed'):android.reboot_persistence(self.client,self.request,wrong)


if __name__=='__main__':unittest.main()
