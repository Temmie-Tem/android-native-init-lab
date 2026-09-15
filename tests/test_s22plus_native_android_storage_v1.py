"""Android census transport, raw GPT/health joins and no-retry failure paths."""
import copy
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from unittest import mock
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_android_storage_v1 as census
import s22plus_native_records_v3 as records
import s22plus_native_task_v3 as tasks
from test_s22plus_native_storage_census_v1 import fixture
import test_s22plus_native_target_io_v3 as health_fixture


class AndroidStorageTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.private=self.root/'workspace/private';self.private.mkdir(parents=True)
        census.registry.initialize(self.root)
        self.health=health_fixture.TargetTests();self.health.setUp();self.addCleanup(self.health.doCleanups)
        self.tool=self.private/'adb-fixture'
        source='''#!/usr/bin/python3
from pathlib import Path
import hashlib,shlex,sys
p=Path(__file__).parent
assert sys.argv[1:3]==['-s','FIXTURE123']
if sys.argv[3:]==['features']:
 print((p/'features').read_text());sys.exit(0)
assert sys.argv[3:5]==['shell','-T']
parts=shlex.split(sys.argv[5]);assert parts[:2]==['su','-c'] and len(parts)==3
assert hashlib.sha256(parts[2].encode()).hexdigest()==EXPECTED
with (p/'dispatches').open('ab') as f:f.write(b'1')
sys.stdout.buffer.write((p/'dataset').read_bytes())
sys.stderr.buffer.write((p/'remote-stderr').read_bytes())
sys.exit(int((p/'remote-exit').read_text()))
'''.replace('EXPECTED',repr(records.digest(census.SCRIPT.encode())))
        self.tool.write_text(source);self.tool.chmod(0o700)
        (self.private/'dataset').write_bytes(fixture(count=44,backup_blocks=9))
        (self.private/'features').write_text('cmd\nshell_v2\nstat_v2\n')
        (self.private/'remote-stderr').write_bytes(b'');(self.private/'remote-exit').write_text('0')
        self.task=dict(adb=records.pin(self.tool),target=self.health.binding,A=self.health.android)
        src=self.private/'fixture-source.py';src.write_text('# fixture reviewed source\n')
        self.review=records.publish(self.private/'review.json',dict(schema='s22plus-native-session-v3-review',
            scope='V3_REACHABLE_CAPABILITY',verdict='PASS_GO',findings=[],sources=[records.pin(src)]))
        self.task['review']=self.review
        self.task_path=self.private/'old-task.json';records.publish(self.task_path,self.task)
        snap=self.private/'snapshot';snap.mkdir();rows=[]
        for original in [records.pin(src),self.review]:
            path=snap/Path(original['path']).name;path.write_bytes(Path(original['path']).read_bytes())
            rows.append(dict(original=original,snapshot=records.pin(path)))
        manifest=records.publish(snap/'manifest.json',dict(schema='s22plus-native-v3-source-snapshot-v1',
            review=self.review,sources=rows))
        self.closed=records.publish(self.private/'closed.json',dict(source_snapshot=manifest))

    def client(self, name):
        return census.target_io.Android(self.task['adb'],self.task['target'],self.task['A'],
            self.private/name,guard=lambda:None)

    def health_result(self, client):
        value=census.target_io.health_projection(self.health.captures(),self.task['target'],self.task['A'])
        records.publish(client.directory/'health.json',value)
        return value

    def observe(self, output, *, health=None):
        callback=health or self.health_result
        def run_health(client):return callback(client)
        with mock.patch.object(tasks,'capability',return_value=self.review), \
                mock.patch.object(census,'closed_android',return_value=(self.task,self.closed)), \
                mock.patch.object(census.target_io.Android,'health',new=run_health):
            return census.observe(self.root,self.task_path,output)

    def test_actual_subprocess_preserves_binary_above_health_capture_bound(self):
        client=self.client('read');handle=census.command(client)
        value=census.projection(records.pin(handle.receipt_path),profile=census.CURRENT_PROFILE)
        self.assertGreater(value['stdout']['size'],16384)
        self.assertEqual(value['status'],'PASS_METADATA_ONLY')
        self.assertFalse(value['node_creation'])
        self.assertNotIn('ram_block_alias_removed',value)
        self.assertEqual((self.private/'dispatches').read_bytes(),b'1')

    def test_complete_command_failure_and_corrupt_gpt_remain_no_proof(self):
        for i,(data,stderr,rc) in enumerate(((b'',b'S22_GPT_STAGE=ancestry RC=1\n',1),
                (fixture()[:-1],b'',0),(fixture(),b'diagnostic\n',0))):
            folder=self.private/str(i);folder.mkdir()
            handle=census.raw.publish_captured_bytes(folder,'metadata',stdout=data,stderr=stderr,returncode=rc)
            value=census.projection(records.pin(handle.receipt_path))
            self.assertEqual(value['status'],'NO_PROOF')
            self.assertEqual(value['stdout']['sha256'],records.digest(data))

    def test_missing_shell_v2_prevents_metadata_dispatch(self):
        for index,text in enumerate(('cmd\nstat_v2\n','cmd,shell_v2,stat_v2')):
            (self.private/'features').write_text(text)
            with self.assertRaisesRegex(ValueError,'no legacy fallback'):
                census.command(self.client('unsupported-'+str(index)))
        self.assertFalse((self.private/'dispatches').exists())

    def test_remote_exit_and_stderr_are_preserved_by_selected_shell_v2_contract(self):
        (self.private/'dataset').write_bytes(b'')
        (self.private/'remote-stderr').write_bytes(b'S22_GPT_STAGE=ancestry RC=1\n')
        (self.private/'remote-exit').write_text('1')
        value=self.observe(self.private/'child-failure')
        handle=census.raw.load_handle(records.verify(value['metadata']['capture']))
        self.assertEqual(handle.returncode,1)
        self.assertEqual(census.raw.read_stderr(handle,maximum=16384),b'S22_GPT_STAGE=ancestry RC=1\n')
        self.assertEqual(value['metadata']['status'],'NO_PROOF')
        self.assertEqual(value['terminal_state'],'ANDROID_CLOSED_HEALTHY')
        self.assertEqual((self.private/'dispatches').read_bytes(),b'1')

    def test_full_same_boot_observation_rederives_without_another_command(self):
        output=self.private/'complete';value=self.observe(output)
        self.assertEqual(value['terminal_state'],'ANDROID_CLOSED_HEALTHY')
        self.assertEqual(value['metadata']['status'],'PASS_METADATA_ONLY')
        with mock.patch.object(census,'command',side_effect=AssertionError('H0 must not dispatch')):
            self.assertEqual(census.rederive(output,self.task,root=self.root),value)
        with self.assertRaisesRegex(ValueError,'already exists'):self.observe(output)
        self.assertEqual((self.private/'dispatches').read_bytes(),b'1')

    def test_current_source_update_uses_saved_old_provenance_without_a_new_android_return(self):
        original=self.review;source=self.private/'fixture-source.py';source.write_text('# reviewed successor source\n')
        path=self.private/'review.json';temporary=self.private/'replacement.json'
        records.publish(temporary,dict(schema='s22plus-native-session-v3-review',verdict='PASS_GO',
            scope='V3_REACHABLE_CAPABILITY',findings=[],sources=[records.pin(source)]))
        temporary.replace(path);self.review=records.pin(path)
        self.assertNotEqual(self.review,original)
        output=self.private/'source-update';value=self.observe(output)
        opened=records.read(output/'open.json')
        self.assertEqual(opened['source_review'],self.review)
        self.assertEqual(self.task['review'],original)
        self.assertNotEqual(opened['source_snapshot'],opened['android_return_source_snapshot'])
        self.assertEqual(value['metadata']['status'],'PASS_METADATA_ONLY')
        self.assertEqual(census.rederive(output,self.task,root=self.root),value)

    def test_historical_tail5_remains_unproved_and_unknown_profile_is_rejected(self):
        value=fixture(count=44,backup_blocks=9);fields=value[3:].split(b'\n',8)
        head=b'G0\n'+b'\n'.join(fields[:8])+b'\n';payload=fields[8]
        old=head+payload[:24576]+payload[24576+4*4096:]
        folder=self.private/'old-capture';folder.mkdir()
        handle=census.raw.publish_captured_bytes(folder,'metadata',stdout=old)
        result=census.projection(records.pin(handle.receipt_path))
        self.assertEqual(result['status'],'NO_PROOF')
        self.assertEqual(result['reason'],'GPT entry array is outside its capture or overlaps its header')
        with self.assertRaisesRegex(ValueError,'unknown Android metadata profile'):
            census.projection(records.pin(handle.receipt_path),profile='arbitrary-range')

    def test_failed_metadata_gets_one_final_health_and_no_reread(self):
        (self.private/'dataset').write_bytes(b'not GPT');calls=[]
        def health(client):calls.append(client.directory.name);return self.health_result(client)
        result=self.observe(self.private/'negative',health=health)
        self.assertEqual(calls,['before','after'])
        self.assertEqual(result['terminal_state'],'ANDROID_CLOSED_HEALTHY')
        self.assertEqual(result['metadata']['status'],'NO_PROOF')
        self.assertEqual((self.private/'dispatches').read_bytes(),b'1')

    def test_changed_boot_or_failed_final_health_never_publishes_healthy_terminal(self):
        for name,change in (('changed',True),('failed',False)):
            original=copy.deepcopy(self.health.properties)
            def health(client):
                if client.directory.name=='after':
                    if not change:raise OSError('fixture lost Android')
                    self.health.properties['boot_id']='87654321-1234-1234-1234-123456789abc'
                return self.health_result(client)
            output=self.private/name
            with self.assertRaises((ValueError,OSError)):self.observe(output,health=health)
            self.assertFalse((output/'terminal.json').exists());self.assertTrue((output/'stopped.json').exists())
            self.health.properties=original
        self.assertEqual((self.private/'dispatches').read_bytes(),b'11')

    def test_initial_health_failure_prevents_metadata_dispatch(self):
        with self.assertRaises(OSError):
            self.observe(self.private/'bad-before',health=lambda client:(_ for _ in ()).throw(OSError('fixture before')))
        self.assertFalse((self.private/'dispatches').exists())

    def test_native_close_and_pending_recovery_cannot_enter_android_d0(self):
        task=self.private/'native';task.mkdir();path=task/'task.json';records.publish(path,self.task)
        records.publish(task/'closed.json',dict(schema='s22plus-native-session-v3-task-close-v1',
            task=records.pin(path),terminal_state='NATIVE_CLOSED_HEALTHY',operations=[{}]))
        with self.assertRaisesRegex(ValueError,'closed original-A'):census.closed_android(self.root,path)
        owner=self.private/'owner';owner.mkdir()
        census.registry.begin_f1_owner(self.root,owner,'a'*64)
        with self.assertRaises(census.registry.RegistryError):self.observe(self.private/'blocked')
        self.assertFalse((self.private/'dispatches').exists())

    def test_closed_gpt_feature_must_match_rederived_normal_or_recovered_proof(self):
        import s22plus_native_adapter_v3 as adapters
        import s22plus_native_session_v3 as sessions
        for recovered in (False,True):
            folder=self.private/('gpt-recovered' if recovered else 'gpt-normal');folder.mkdir()
            task_path=folder/'task.json';records.publish(task_path,self.task)
            operation=dict(task=records.pin(task_path),operation='gpt-reserve')
            operation_pin=records.publish(folder/'operation.json',operation)
            step='recovery-health' if recovered else 'android-final'
            final=records.publish(folder/(step+'.json'),dict(fixture='raw-health'))
            feature=dict(status='RESERVED_ANDROID_REBOOT_VERIFIED',geometry=dict(block_count=123))
            terminal=dict(terminal_state='ANDROID_CLOSED_HEALTHY',research_closed=True,
                operation_record=operation_pin,recovered=recovered,terminal_result=final,gpt=feature)
            terminal_pin=records.publish(folder/'terminal.json',terminal)
            close=dict(schema='s22plus-native-session-v3-task-close-v1',task=records.pin(task_path),
                terminal_state='ANDROID_CLOSED_HEALTHY',operations=[dict(terminal=terminal_pin)],gpt=feature)
            records.publish(folder/'closed.json',close)
            adapter=mock.Mock();adapter.terminal.return_value=dict(gpt=feature)
            session=mock.Mock();session.completed.return_value=[dict(fixture='validated-step')]
            session.rows.return_value=[dict(event='effect-intent',data=dict(action='transfer',role='A',step='install-android'))]
            with mock.patch.object(adapters,'Adapter',return_value=adapter), \
                    mock.patch.object(sessions,'Session',return_value=session), \
                    mock.patch.object(tasks,'android_artifact',return_value=self.task['A']):
                self.assertEqual(census.closed_android(self.root,task_path)[0],self.task)
                close['gpt']=dict(feature,geometry=dict(block_count=999))
                (folder/'closed.json').unlink();records.publish(folder/'closed.json',close)
                with self.assertRaisesRegex(ValueError,'closed GPT feature'):
                    census.closed_android(self.root,task_path)

    def test_fixed_android_shell_syntax_and_failure_stage_are_observable(self):
        subprocess.run(['/bin/sh','-n','-c',census.SCRIPT],capture_output=True,check=True,timeout=5)
        root=Path(__file__).resolve().parents[1]
        busybox=root/'workspace/private/inputs/s22plus_fyg8_p326/busybox/bin/busybox-aarch64-static-1.36.1'
        subprocess.run(['/usr/bin/qemu-aarch64',str(busybox),'sh','-n','-c',census.SCRIPT],
            capture_output=True,check=True,timeout=5)
        # Execute only the fixed trap + first explicit guard, with no device paths.
        prefix=census.SCRIPT.split('v=$',1)[0]
        value=subprocess.run(['/bin/sh','-c',prefix+'stage=ancestry; false\n'],capture_output=True,timeout=5)
        self.assertEqual(value.returncode,1);self.assertEqual(value.stdout,b'')
        self.assertEqual(value.stderr,b'S22_GPT_STAGE=ancestry RC=1\n')

    def test_tail9_guard_rejects_userdata_overlap_before_any_metadata_read(self):
        u=self.private/'sysfs-userdata';u.mkdir();(u/'start').write_text('1000\n')
        for size,expected in ((7928,0),(7929,1)):
            (u/'size').write_text(str(size)+'\n')
            script='set -eu; B=/usr/bin/busybox; s=9000; u='+shlex.quote(str(u))+'; '+census.TAIL9_GUARD+'; printf READ_PERMITTED'
            value=subprocess.run(['/bin/sh','-c',script],capture_output=True,timeout=5)
            self.assertEqual(value.returncode,expected)
            self.assertEqual(value.stdout,b'READ_PERMITTED' if expected==0 else b'')

    def test_tail9_guard_requires_complete_numeric_sysfs_reads(self):
        u=self.private/'sysfs-userdata';u.mkdir()
        for start,size in ((None,'7929'),('1000',None),('', '7929'),('1000',''),
                ('invalid','7929'),('1000','-1'),('9'*17,'1'),('1','9'*17)):
            with self.subTest(start=start,size=size):
                for name,text in (('start',start),('size',size)):
                    path=u/name
                    if path.exists():path.unlink()
                    if text is not None:path.write_text(text+'\n')
                script='set -eu; B=/usr/bin/busybox; s=9000; u='+shlex.quote(str(u))+'; '+census.TAIL9_GUARD+'; printf READ_PERMITTED'
                value=subprocess.run(['/bin/sh','-c',script],capture_output=True,timeout=5)
                self.assertNotEqual(value.returncode,0)
                self.assertEqual(value.stdout,b'')


if __name__=='__main__':unittest.main()
