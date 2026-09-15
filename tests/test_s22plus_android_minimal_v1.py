"""Real bounded subprocess transcripts plus optional-package effect state model."""
import base64
from contextlib import nullcontext
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
import s22plus_android_minimal_v1 as minimal
import s22plus_native_records_v3 as records
import test_s22plus_native_target_io_v3 as health_fixture
from test_s22plus_native_gpt_profile_v1 import binding
from test_s22plus_native_gpt_android_v1 import metadata as gpt_metadata

NAME=minimal.OPTIONAL[0]
HOME='com.sec.android.app.launcher'
IME='com.samsung.android.honeyboard'


def listing(name=NAME,uid=10123,version=1):
    return f'package:/system/app/Optional/base.apk={name} versionCode:{version} uid:{uid}\n'


def dump(name=NAME,uid=10123,version=1,flags='SYSTEM HAS_CODE',state='installed=true hidden=false suspended=false enabled=0'):
    return f'Packages:\n  Package [{name}] (fixture):\n    userId={uid}\n    codePath=/system/app/Optional\n    versionCode={version} minSdk=23 targetSdk=35\n    pkgFlags=[ {flags} ]\n    User 0: {state}\n'


class ParserTests(unittest.TestCase):
    def test_fixed_optional_selection_preserves_required_shared_persistent_and_customized_apps(self):
        listed=minimal.packages(listing());row=minimal.package_metadata(dump(),listed[NAME])
        self.assertEqual(minimal.selection(listed,{NAME:row},HOME,IME)['selected'],[row])
        cases=[(dict(row,uid=1000),'system-or-shared-uid'),
            (dict(row,shared_uid=True),'system-or-shared-uid'),
            (dict(row,persistent=True),'persistent-component'),
            (dict(row,ordinary_primary_user=False),'customized-or-disabled-user-state')]
        for value,reason in cases:
            result=minimal.selection({NAME:dict(listed[NAME],uid=value['uid'])},{NAME:value},HOME,IME)
            self.assertEqual(result['selected'],[]);self.assertEqual(result['excluded'][NAME],reason)
        self.assertEqual(minimal.selection(listed,{NAME:row},NAME,IME)['selected'],[])
        shared=dict(listed,**{'com.fixture.peer':dict(listed[NAME],name='com.fixture.peer')})
        self.assertEqual(minimal.selection(shared,{NAME:row},HOME,IME)['selected'],[])
        self.assertNotIn('com.android.settings',minimal.OPTIONAL)
        self.assertNotIn('com.topjohnwu.magisk',minimal.OPTIONAL)

    def test_metadata_identity_ambiguity_and_caller_paths_are_rejected(self):
        row=minimal.packages(listing())[NAME]
        for text in (dump(uid=10124),dump(version=2),dump()+dump(),dump(flags='HAS_CODE')):
            with self.subTest(text=text),self.assertRaises(ValueError):minimal.package_metadata(text,row)
        for text in (listing().replace('/system/app/Optional/base.apk','/dev/block/sda'),
                listing().replace(NAME,NAME+';reboot'),listing()+listing()):
            with self.assertRaises(ValueError):minimal.packages(text)
        self.assertEqual(minimal.component('priority=0\n'+HOME+'/.Home\n'),HOME)
        with self.assertRaises(ValueError):minimal.component('null\n')


class RunTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.folder=self.root/'workspace/private/cleanup';self.folder.mkdir(parents=True)
        self.fixture=health_fixture.TargetTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        vectors,self.sealed=binding(self.folder,android32=True)
        self.state=self.folder/'state.json';self.state.write_text(json.dumps(dict(installed=True,version=1,
            uninstalls=0,reboots=0,fail=None)))
        self.log=self.folder/'argv.jsonl';self.responses=self.folder/'responses.json'
        serial=self.fixture.binding['serial'];self.serial=serial
        entries={}
        def answer(args,data):
            if isinstance(data,str):data=data.encode()
            entries[json.dumps(args)]=base64.b64encode(data).decode()
        answer(['devices','-l'],self.fixture.inventory)
        answer(['-s',serial,'get-devpath'],self.fixture.binding['topology'])
        answer(['-s',serial,'shell','getprop sys.boot_completed'],'1')
        answer(['-s',serial,'features'],'shell_v2\n')
        answer(['-s',serial,'shell','su -c '+shlex.quote(minimal.target.ROOT_HEALTH)],
            '\n'.join(k+'='+v for k,v in dict(root='uid=0(root) gid=0(root)',
                **self.fixture.android['partition_sha256']).items()))
        answer(['-s',serial,*minimal.USER],'0\n')
        answer(['-s',serial,*minimal.HOME],HOME+'/.Home\n')
        answer(['-s',serial,*minimal.IME],IME+'/.Keyboard\n')
        answer(['-s',serial,'shell','-T','su -c '+shlex.quote(minimal.census.SCRIPT)],gpt_metadata(self.sealed))
        self.responses.write_text(json.dumps(entries))
        self.program=self.folder/'adb-fixture'
        source='''#!/usr/bin/env python3
import base64,json,pathlib,sys
args=sys.argv[1:]
state=pathlib.Path(@STATE@);s=json.loads(state.read_text())
with pathlib.Path(@LOG@).open('a') as stream:stream.write(json.dumps(args)+'\\n')
tail=args[2:] if args[:1]==['-s'] else args
if tail==['shell','sh -c '+@PROPERTIES@]:
 p=@PROPS@;p['boot_id']='11111111-1111-1111-1111-'+str(s['reboots']+1).zfill(12)
 print('\\n'.join(k+'='+v for k,v in p.items()));sys.exit(0)
if tail[:5]==['shell','cmd','package','list','packages']:
 if s['installed']:print(@LISTING@.replace('versionCode:1','versionCode:'+str(s['version'])),end='')
 sys.exit(0)
if tail==['shell','dumpsys','package',@NAME@]:
 print(@DUMP@.replace('versionCode=1','versionCode='+str(s['version'])),end='');sys.exit(0)
if tail[:3]==['shell','pm','uninstall']:
 assert tail==['shell','pm','uninstall','--user','0','--versionCode','1',@NAME@]
 s['installed']=False;s['uninstalls']+=1;state.write_text(json.dumps(s))
 if s['fail']=='uninstall':print('response lost',file=sys.stderr);sys.exit(1)
 print('Success');sys.exit(0)
if tail==['reboot']:
 s['reboots']+=1;state.write_text(json.dumps(s))
 if s['fail']=='reboot':print('response lost',file=sys.stderr);sys.exit(1)
 sys.exit(0)
if tail==['shell','su -c '+@STAT@]:
 print('NATIVE_PARTITION 41 96923648 401516544 native_data')
 print('F2FS_STAT 4096 8388092 '+str(1000+(not s['installed'])*100)+' 2000 f2f52010');sys.exit(0)
data=json.loads(pathlib.Path(@RESPONSES@).read_text())[json.dumps(args)]
sys.stdout.buffer.write(base64.b64decode(data))
'''
        values=dict(STATE=str(self.state),LOG=str(self.log),PROPERTIES=shlex.quote(minimal.target.PROPERTIES),
            PROPS=self.fixture.properties,LISTING=listing(),DUMP=dump(),NAME=NAME,
            STAT=shlex.quote(minimal.gpt_android.STAT_SCRIPT),RESPONSES=str(self.responses))
        for key,value in values.items():source=source.replace('@'+key+'@',repr(value))
        self.program.write_text(source);self.program.chmod(0o700)
        run=object.__new__(minimal.Run);self.run=run
        run.root=self.root;run.directory=self.folder;run.deadline_ns=records.clock()+900_000_000_000
        run.recovering=False;run.sealed=self.sealed;run.basis=dict(layout='proposed',geometry=dict(
            block_count=8388604,segment0_block=512))
        run.task=dict(target=self.fixture.binding,A=self.fixture.android,adb=records.pin(self.program),N=dict(gpt=vectors))
        run.journal=records.Journal(self.folder/'journal');run.opened=dict(host_boot=records.host_boot(),
            review=dict(fixture='review'),source_snapshot=dict(fixture='preserved-source'))
        run.open_pin=dict(fixture='open')
        def check(*,reserve=0):
            records.require(records.clock()+int(reserve*1e9)<run.deadline_ns,'fixture deadline expired')
        run.check=check
        for patch in (mock.patch.object(minimal.registry,'target_session_lease',side_effect=lambda *a:nullcontext()),
                mock.patch.object(minimal.registry,'require_no_f1_owner'),
                mock.patch.object(minimal,'review',return_value=run.opened['review']),
                mock.patch.object(minimal.target,'usb_snapshot',side_effect=lambda *a:dict(boottime_ns=records.clock(),fixture='old-generation')),
                mock.patch.object(minimal.target,'wait_departure',side_effect=lambda before,folder,deadline_ns,guard:
                    dict(before=before,departed=True,deadline_ns=deadline_ns,observed_ns=records.clock()))):
            patch.start();self.addCleanup(patch.stop)

    def change(self,**values):
        state=json.loads(self.state.read_text());state.update(values);self.state.write_text(json.dumps(state))

    def prepare(self):return self.run.inventory(self.folder/'inventory')

    def test_real_raw_inventory_uninstall_version_guard_and_reboot_persistence(self):
        self.prepare();self.assertEqual(self.run.inventory_projection()['selection']['selected'][0]['name'],NAME)
        result=records.read(records.verify(self.run.execute(attended=True)))
        self.assertEqual(result['status'],'COMPLETE');self.assertTrue(result['reboot_verified'])
        state=json.loads(self.state.read_text());self.assertEqual((state['uninstalls'],state['reboots']),(1,1))
        self.assertEqual(result['observed_available_bytes_change'],100*4096)
        calls=self.log.read_bytes();(self.folder/'terminal.json').unlink()
        with mock.patch.object(self.run,'command',side_effect=AssertionError('raw repair issued I/O')):
            self.assertEqual(records.read(records.verify(self.run.reconcile()))['status'],'COMPLETE')
        self.assertEqual(self.log.read_bytes(),calls)

    def test_tampered_manifest_and_changed_package_cannot_be_uninstalled(self):
        self.prepare();p=self.folder/'inventory/result.json';original=p.read_text()
        value=json.loads(original);value['selection']['selected'][0]['name']='com.android.settings'
        p.chmod(0o600);p.write_text(json.dumps(value))
        with self.assertRaises(ValueError):self.run.execute(attended=True)
        self.assertEqual(json.loads(self.state.read_text())['uninstalls'],0)
        p.write_text(original);self.change(version=2)
        self.assertEqual(self.run.execute(attended=True)['state'],'STOPPED_RECONCILIATION_REQUIRED')
        self.assertEqual(json.loads(self.state.read_text())['uninstalls'],0)

    def test_uncertain_uninstall_never_replays_and_reconciliation_only_reads(self):
        self.prepare();self.change(fail='uninstall')
        self.assertEqual(self.run.execute(attended=True)['state'],'STOPPED_RECONCILIATION_REQUIRED')
        with self.assertRaises(ValueError):self.run.execute(attended=True)
        task_path=self.folder/'task.json';records.publish(task_path,self.run.task)
        closed=records.publish(self.folder/'closed.json',dict(gpt=dict(status='RESERVED_ANDROID_REBOOT_VERIFIED')))
        records.publish(self.folder/'android-minimal-claim.json',dict(fixture='first consumed cleanup open'))
        with mock.patch.object(minimal.census,'closed_android',return_value=(self.run.task,closed)):
            with self.assertRaisesRegex(ValueError,'already has a cleanup claim'):
                minimal.prepare(self.root,task_path,self.root/'workspace/private/second-cleanup',
                    operator_statement='fixture same request',attended=True)
        self.assertFalse((self.root/'workspace/private/second-cleanup').exists())
        self.change(fail=None)
        def same_run(*args,**kwargs):self.run.recovering=True;return self.run
        with mock.patch.object(minimal,'Run',side_effect=same_run):
            result=records.read(records.verify(self.run.reconcile()))
        self.assertEqual(result['status'],'INCOMPLETE');self.assertFalse(result['reboot_verified'])
        state=json.loads(self.state.read_text());self.assertEqual((state['uninstalls'],state['reboots']),(1,0))

    def test_expiry_before_effect_and_recovery_mode_block_all_mutations(self):
        self.prepare();self.run.deadline_ns=records.clock()-1
        with self.assertRaises(ValueError):self.run.execute(attended=True)
        self.assertEqual(json.loads(self.state.read_text())['uninstalls'],0)
        self.run.deadline_ns=records.clock()+900_000_000_000;self.run.recovering=True
        with self.assertRaises(ValueError):self.run.intent('uninstall',package=NAME)

    def test_no_selected_apps_does_not_reboot(self):
        self.change(installed=False);self.prepare()
        result=records.read(records.verify(self.run.execute(attended=True)))
        self.assertEqual(result['status'],'NO_CHANGES_NEEDED')
        self.assertEqual(json.loads(self.state.read_text())['reboots'],0)
        calls=self.log.read_bytes();self.run.reconcile()
        self.assertEqual(self.log.read_bytes(),calls)

    def test_uncertain_reboot_is_not_replayed_and_reconcile_raw_cut_is_h0(self):
        self.prepare();self.change(fail='reboot')
        self.assertEqual(self.run.execute(attended=True)['state'],'STOPPED_RECONCILIATION_REQUIRED')
        self.change(fail=None)
        def same_run(*args,**kwargs):self.run.recovering=True;return self.run
        with mock.patch.object(minimal,'Run',side_effect=same_run):
            result=records.read(records.verify(self.run.reconcile()))
        self.assertEqual(result['status'],'INCOMPLETE');self.assertFalse(result['reboot_verified'])
        state=json.loads(self.state.read_text());self.assertEqual((state['uninstalls'],state['reboots']),(1,1))
        calls=self.log.read_bytes();(self.folder/'terminal.json').unlink()
        (self.folder/'reconciliation/result.json').unlink()
        with mock.patch.object(self.run,'command',side_effect=AssertionError('raw reconstruction issued I/O')):
            result=records.read(records.verify(self.run.reconcile()))
        self.assertEqual(result['status'],'INCOMPLETE');self.assertEqual(self.log.read_bytes(),calls)

    def test_switch_to_secondary_user_blocks_first_uninstall(self):
        self.prepare();entries=json.loads(self.responses.read_text())
        entries[json.dumps(['-s',self.serial,*minimal.USER])]=base64.b64encode(b'10\n').decode()
        self.responses.write_text(json.dumps(entries))
        self.assertEqual(self.run.execute(attended=True)['state'],'STOPPED_RECONCILIATION_REQUIRED')
        state=json.loads(self.state.read_text());self.assertEqual((state['uninstalls'],state['reboots']),(0,0))

    def test_loading_revalidates_closed_task_and_snapshot_containment(self):
        closed=dict(gpt=dict(status='RESERVED_ANDROID_REBOOT_VERIFIED',geometry=self.run.basis['geometry']))
        closed_pin=records.publish(self.folder/'closed.json',closed)
        task_pin=records.publish(self.folder/'task.json',self.run.task)
        original=self.folder/'original-source';original.write_text('source')
        review=records.publish(self.folder/'review.json',dict(sources=[records.pin(original)]))
        base=self.folder/'source-snapshot';base.mkdir()
        rows=[]
        for number,item in enumerate([records.pin(original),review]):
            saved=base/str(number);saved.write_bytes(records.verify(item).read_bytes())
            rows.append(dict(original=item,snapshot=records.pin(saved)))
        snap=records.publish(base/'manifest.json',dict(schema='s22plus-native-v3-source-snapshot-v1',
            review=review,sources=rows))
        now=records.clock();opened=dict(schema=minimal.SCHEMA,mode='minimal-management',task=task_pin,
            closed=closed_pin,review=review,operator_statement='fixture minimal management',
            host_boot=records.host_boot(),opened_ns=now,deadline_ns=now+900_000_000_000,source_snapshot=snap)
        open_pin=records.publish(self.folder/'open.json',opened)
        records.publish(self.folder/'android-minimal-claim.json',dict(schema=minimal.SCHEMA+'-claim',
            task=task_pin,closed=closed_pin,open=open_pin))
        with mock.patch.object(minimal.census,'closed_android',return_value=(self.run.task,closed_pin)):
            minimal.Run(self.root,self.folder)
            outside=self.folder/'outside';outside.write_bytes(records.verify(rows[0]['snapshot']).read_bytes())
            rows[0]['snapshot']=records.pin(outside)
            (base/'manifest.json').unlink()
            opened['source_snapshot']=records.publish(base/'manifest.json',dict(
                schema='s22plus-native-v3-source-snapshot-v1',review=review,sources=rows))
            (self.folder/'open.json').unlink();open_pin=records.publish(self.folder/'open.json',opened)
            (self.folder/'android-minimal-claim.json').unlink()
            records.publish(self.folder/'android-minimal-claim.json',dict(schema=minimal.SCHEMA+'-claim',
                task=task_pin,closed=closed_pin,open=open_pin))
            with self.assertRaisesRegex(ValueError,'outside its snapshot'):minimal.Run(self.root,self.folder)
        with mock.patch.object(minimal.census,'closed_android',side_effect=ValueError('closure incomplete')):
            with self.assertRaisesRegex(ValueError,'closure incomplete'):minimal.Run(self.root,self.folder)


if __name__=='__main__':unittest.main()
