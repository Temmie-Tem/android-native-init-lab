"""Real bounded subprocess transcripts plus optional-package effect state model."""
import base64
from contextlib import nullcontext
import copy
from dataclasses import replace
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

    def test_framework_and_apex_rows_are_inventory_only(self):
        framework=listing(name='android',uid=1000).replace('/system/app/Optional/base.apk',
            '/system/framework/framework-res.apk')
        apex=listing(name='com.android.bluetooth',uid=1002).replace('/system/app/Optional/base.apk',
            '/apex/com.android.btservices/app/Bluetooth@fixture/Bluetooth.apk')
        rows=minimal.packages(framework+apex)
        self.assertEqual(set(rows),{'android','com.android.bluetooth'})
        self.assertEqual(minimal.selection(rows,{},HOME,IME)['selected'],[])
        row=minimal.package_metadata(dump(),minimal.packages(listing())[NAME])
        row['path']='/apex/com.fixture/app/Optional/base.apk'
        result=minimal.selection({NAME:row},{NAME:row},HOME,IME)
        self.assertEqual(result['selected'],[])
        self.assertEqual(result['excluded'][NAME],'required-component')

    def test_equal_flag_aliases_and_historical_s22_protections(self):
        row=minimal.packages(listing())[NAME]
        text=dump().replace('    pkgFlags=', '    flags=[ HAS_CODE SYSTEM ]\n    pkgFlags=')
        self.assertEqual(minimal.package_metadata(text,row),minimal.package_metadata(dump(),row))
        for wrong in (text.replace('flags=[ HAS_CODE SYSTEM ]','flags=[ SYSTEM PERSISTENT ]'),
                text.replace('flags=[ HAS_CODE SYSTEM ]','pkgFlags=[ HAS_CODE SYSTEM ]')):
            with self.assertRaisesRegex(ValueError,'flags'):minimal.package_metadata(wrong,row)
        for name in ('com.android.bluetooth','com.google.android.documentsui',
                'com.sec.android.app.servicemodeapp','com.sec.android.RilServiceModeApp','com.sec.android.app.parser'):
            self.assertIn(name,minimal.KEEP);self.assertNotIn(name,minimal.OPTIONAL)
        self.assertIn('com.samsung.android.aremojieditor',minimal.OPTIONAL)

    def test_package_fields_are_scoped_before_shared_user_and_query_sections(self):
        row=minimal.packages(listing())[NAME]
        text=dump().replace('    pkgFlags=',
            '    sharedUser=SharedUserSetting{fixture shared.uid/10123}\n    pkgFlags=')
        text+='Queries:\n    User 0:\nShared users:\n    appId=10123\n    User 0:\n'
        value=minimal.package_metadata(text,row)
        self.assertTrue(value['shared_uid'])
        self.assertEqual(minimal.selection({NAME:row},{NAME:value},HOME,IME)['excluded'][NAME],
            'system-or-shared-uid')
        with self.assertRaises(ValueError):
            minimal.package_metadata(text.replace('    userId=10123\n',
                '    userId=10123\n    appId=10123\n'),row)
        labels=[minimal.metadata_label(name) for name in minimal.OPTIONAL]
        self.assertEqual(len(labels),len(set(labels)))
        self.assertTrue(all(minimal.raw.NAME_RE.fullmatch(label) for label in labels))


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
        answer(['-s',serial,*minimal.SAFE_MODE],'\n')
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
if args==['devices','-l'] and s['fail']=='inventory-gap':
 s['fail']=None;state.write_text(json.dumps(s));print('List of devices attached');sys.exit(0)
if tail==['shell','su -c '+@ROOTCMD@] and s['reboots'] and s['fail']=='final-disconnect':
 s['fail']='inventory-gap';state.write_text(json.dumps(s));sys.exit(0)
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
            STAT=shlex.quote(minimal.gpt_android.STAT_SCRIPT),RESPONSES=str(self.responses),
            ROOTCMD=shlex.quote(minimal.target.ROOT_HEALTH))
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

    def bind_closed_fixture(self):
        self.run.task['A']['ap']=records.pin(self.program)
        task=records.publish(self.folder/'task.json',self.run.task)
        closed=records.publish(self.folder/'closed.json',dict(gpt=dict(
            status='RESERVED_ANDROID_REBOOT_VERIFIED',geometry=self.run.basis['geometry'])))
        self.run.opened.update(mode='minimal-management',task=task,closed=closed,
            source_snapshot=records.publish(self.folder/'old-source-snapshot.json',dict(fixture='source')))
        self.run.open_pin=records.publish(self.folder/'open.json',self.run.opened)
        self.run.claim_pins=[];self.run.predecessors=[]
        return task,closed

    def test_closed_predecessor_keeps_stopped_terminal_and_requires_known_same_boot_health(self):
        self.bind_closed_fixture();self.prepare();self.change(fail='final-disconnect')
        self.assertEqual(self.run.execute(attended=True)['state'],'STOPPED_RECONCILIATION_REQUIRED')
        def same_run(*args,**kwargs):self.run.recovering=True;return self.run
        with mock.patch.object(minimal,'Run',side_effect=same_run):
            terminal=records.read(records.verify(self.run.reconcile()))
            saved=(self.folder/'terminal.json').read_bytes();calls=self.log.read_bytes()
            proof=minimal.closed_cleanup(self.root,self.folder)
            self.assertEqual(proof['removed'],[NAME])
            self.assertEqual(terminal['status'],'INCOMPLETE');self.assertFalse(terminal['reboot_verified'])
            self.assertEqual((self.folder/'terminal.json').read_bytes(),saved)
            self.assertEqual(self.log.read_bytes(),calls)
            self.run.journal.append('intent',key='late',kind='uninstall',detail={})
            with self.assertRaises(ValueError):minimal.closed_cleanup(self.root,self.folder)

    def test_closed_predecessor_rejects_uncertain_reboot_despite_healthy_reconciliation(self):
        self.bind_closed_fixture();self.prepare();self.change(fail='reboot')
        self.assertEqual(self.run.execute(attended=True)['state'],'STOPPED_RECONCILIATION_REQUIRED')
        self.change(fail=None)
        def same_run(*args,**kwargs):self.run.recovering=True;return self.run
        with mock.patch.object(minimal,'Run',side_effect=same_run):
            terminal=records.read(records.verify(self.run.reconcile()))
            self.assertEqual(terminal['terminal_state'],'ANDROID_CLOSED_HEALTHY')
            with self.assertRaises((ValueError,OSError,minimal.raw.RawCaptureError)):
                minimal.closed_cleanup(self.root,self.folder)
        self.assertEqual(json.loads(self.state.read_text())['reboots'],1)

    def test_additional_mode_uses_its_own_declaration_through_effect_and_terminal(self):
        name=minimal.EXTRA_OPTIONAL[0]
        self.program.write_text(self.program.read_text().replace(NAME,name))
        self.run.task['adb']=records.pin(self.program);self.run.opened['mode']=minimal.ADDITIONAL_MODE
        self.prepare();plan=self.run.inventory_projection()
        self.assertEqual(plan['selection']['declared_optional_count'],38)
        self.assertEqual([row['name'] for row in plan['selection']['selected']],[name])
        result=records.read(records.verify(self.run.execute(attended=True)))
        self.assertEqual((result['status'],result['removed_count']),('COMPLETE',1))
        self.assertFalse(set(minimal.EXTRA_OPTIONAL)&minimal.KEEP)
        self.assertFalse(set(minimal.EXTRA_OPTIONAL)&set(minimal.OPTIONAL))

    def test_additional_safe_mode_property_blocks_effects(self):
        self.run.opened['mode']=minimal.ADDITIONAL_MODE
        entries=json.loads(self.responses.read_text())
        entries[json.dumps(['-s',self.serial,*minimal.SAFE_MODE])]=base64.b64encode(b'1\n').decode()
        self.responses.write_text(json.dumps(entries))
        with self.assertRaisesRegex(ValueError,'safe mode'):self.prepare()
        self.assertFalse(self.run.journal.rows())
        state=json.loads(self.state.read_text());self.assertEqual((state['uninstalls'],state['reboots']),(0,0))

    def test_additional_missing_keep_package_stops_before_reboot(self):
        name=minimal.EXTRA_OPTIONAL[0]
        source=self.program.read_text().replace(repr(listing()),
            repr(listing(name=name)+listing(name='com.android.settings',uid=1000))).replace(NAME,name)
        self.program.write_text(source);self.run.task['adb']=records.pin(self.program)
        self.run.opened['mode']=minimal.ADDITIONAL_MODE
        self.prepare()
        self.assertEqual(self.run.execute(attended=True)['state'],'STOPPED_RECONCILIATION_REQUIRED')
        state=json.loads(self.state.read_text());self.assertEqual((state['uninstalls'],state['reboots']),(1,0))

    def test_additional_prepare_has_one_child_and_rechecks_previous_journal(self):
        task,closed=self.bind_closed_fixture();self.prepare();self.run.execute(attended=True)
        with mock.patch.object(minimal,'Run',return_value=self.run):
            previous=minimal.closed_cleanup(self.root,self.folder)
        _,_,_,_,review,_=self.inventory_stop_fixture()
        def inventory(run,folder):
            folder.mkdir();return records.publish(folder/'result.json',dict(selection=dict(selected=[])))
        fresh=self.root/'workspace/private/additional'
        with mock.patch.object(minimal,'review',return_value=review), \
                mock.patch.object(minimal.census,'closed_android',return_value=(self.run.task,closed)), \
                mock.patch.object(minimal,'closed_cleanup',return_value=previous), \
                mock.patch.object(minimal.Run,'inventory',new=inventory):
            result=minimal.prepare(self.root,Path(task['path']),fresh,operator_statement='continue cleanup',
                attended=True,after_cleanup=self.folder)
            self.assertEqual(result['state'],'READY_FOR_FIXED_CLEANUP')
            loaded=minimal.Run(self.root,fresh)
            self.assertEqual(loaded.declaration(),minimal.EXTRA_OPTIONAL)
            with self.assertRaisesRegex(ValueError,'one additional claim'):
                minimal.prepare(self.root,Path(task['path']),self.root/'workspace/private/another',
                    operator_statement='continue cleanup',attended=True,after_cleanup=self.folder)
            self.run.journal.append('stopped',fixture='late activity')
            with self.assertRaisesRegex(ValueError,'gained execution activity'):loaded.check()
        with self.assertRaisesRegex(ValueError,'original management profile'):
            minimal.closed_cleanup(self.root,fresh)

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

    def test_inventory_projection_survives_missing_aggregate_without_io(self):
        self.prepare();value=records.read(self.folder/'inventory/result.json')
        (self.folder/'inventory/result.json').unlink();calls=self.log.read_bytes()
        self.assertEqual(self.run.inventory_raw_projection(),value)
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
        review=records.publish(self.folder/'review.json',dict(schema=minimal.SCHEMA+'-review',
            verdict='PASS_GO',scope='FIXED_OPTIONAL_PRIMARY_USER_CLEANUP',findings=[],reviewer='fixture',
            sources=[records.pin(original)]))
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

    def test_large_complete_metadata_reaches_real_uninstall_and_terminal_projection(self):
        self.program.write_text(self.program.read_text().replace(repr(dump()),repr('filter data\n'*18000+dump())))
        self.run.task['adb']=records.pin(self.program)
        self.prepare()
        handle=minimal.raw.load_handle(self.folder/'inventory/packages'/(minimal.metadata_label(NAME)+'.capture.json'))
        self.assertGreater(handle.stdout['size'],131072)
        self.assertFalse(handle.output_exceeded)
        result=records.read(records.verify(self.run.execute(attended=True)))
        self.assertEqual((result['status'],result['removed_count']),('COMPLETE',1))

    def test_metadata_above_fixed_limit_stops_before_effect_and_keeps_after_health(self):
        self.program.write_text(self.program.read_text().replace(repr(dump()),
            repr('filter data\n'*100000+dump())))
        self.run.task['adb']=records.pin(self.program)
        with self.assertRaises(minimal.raw.RawCaptureError):self.prepare()
        handle=minimal.raw.load_handle(self.folder/'inventory/packages'/(minimal.metadata_label(NAME)+'.capture.json'))
        self.assertTrue(handle.output_exceeded)
        self.assertEqual(handle.stdout['size'],minimal.METADATA_MAXIMUM)
        self.assertTrue((self.folder/'inventory/after/health.json').exists())
        self.assertFalse(self.run.journal.rows())
        state=json.loads(self.state.read_text());self.assertEqual((state['uninstalls'],state['reboots']),(0,0))

    def test_uppercase_package_identity_survives_canonical_capture_label(self):
        name='com.sec.android.easyMover'
        self.program.write_text(self.program.read_text().replace(NAME,name))
        self.run.task['adb']=records.pin(self.program)
        with mock.patch.object(minimal,'OPTIONAL',(name,)):
            self.prepare()
            self.assertTrue((self.folder/'inventory/packages'/(minimal.metadata_label(name)+'.capture.json')).exists())
            result=records.read(records.verify(self.run.execute(attended=True)))
        self.assertEqual(result['status'],'COMPLETE')
        calls=[json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertIn(['-s',self.serial,'shell','dumpsys','package',name],calls)

    def test_prelaunch_label_retirement_requires_first_invalid_name_and_successful_prefix(self):
        directory,task,task_pin,closed,review,source_sha=self.inventory_stop_fixture()
        inv=directory/'inventory';bad='com.sec.android.easyMover'
        for suffix in ('.capture.json','.stdout.bin','.stderr.bin'):
            (inv/('system-packages'+suffix)).unlink()
        minimal.raw.publish_captured_bytes(inv,'system-packages',stdout=(listing()+listing(name=bad,uid=10124)).encode())
        for name,text in [('home',HOME+'/.Home\n'),('ime',IME+'/.Keyboard\n'),
                ('storage-stat','NATIVE_PARTITION 41 96923648 401516544 native_data\nF2FS_STAT 4096 8388092 1000 2000 f2f52010\n')]:
            minimal.raw.publish_captured_bytes(inv,name,stdout=text.encode())
        folder=inv/'packages';folder.mkdir()
        minimal.raw.publish_captured_bytes(folder,NAME,stdout=dump().encode())
        with mock.patch.object(minimal,'INVENTORY_CAPTURE_LABEL_SHA256',source_sha), \
                mock.patch.object(minimal.census,'closed_android',return_value=(task,closed)):
            value=minimal.inventory_no_effect_projection(self.root,directory)
            self.assertEqual(value['acquisition_case'],'PRELAUNCH_CAPTURE_LABEL')
            self.assertEqual(value['rejected_label'],bad)
            with mock.patch.object(minimal,'OPTIONAL',(NAME,)):
                with self.assertRaisesRegex(ValueError,'first invalid prelaunch'):
                    minimal.inventory_no_effect_projection(self.root,directory)

    def inventory_stop_fixture(self):
        directory=self.root/'workspace/private/parser-stop';directory.mkdir()
        task_dir=self.root/'workspace/private/g2';task_dir.mkdir()
        task=copy.deepcopy(self.run.task)
        task['A']['ap']=records.pin(self.program)
        task_pin=records.publish(task_dir/'task.json',task)
        closed=records.publish(task_dir/'closed.json',dict(gpt=dict(
            status='RESERVED_ANDROID_REBOOT_VERIFIED',geometry=self.run.basis['geometry'])))
        source=self.root/'workspace/public/src/scripts/revalidation/s22plus_android_minimal_v1.py'
        source.parent.mkdir(parents=True);source.write_text('# reviewed old parser fixture\n')
        review=records.publish(task_dir/'review.json',dict(schema=minimal.SCHEMA+'-review',verdict='PASS_GO',
            scope='FIXED_OPTIONAL_PRIMARY_USER_CLEANUP',findings=[],reviewer='fixture',sources=[records.pin(source)]))
        snapshot=minimal.census.snapshot_current(self.root,directory/'source-snapshot',review)
        now=records.clock()
        opened=records.publish(directory/'open.json',dict(schema=minimal.SCHEMA,mode='minimal-management',
            task=task_pin,closed=closed,review=review,operator_statement='fixture cleanup',
            host_boot=records.host_boot(),opened_ns=now,deadline_ns=now+900_000_000_000,source_snapshot=snapshot))
        records.publish(task_dir/'android-minimal-claim.json',dict(schema=minimal.SCHEMA+'-claim',
            task=task_pin,closed=closed,open=opened))
        records.Journal(directory/'journal')
        inv=directory/'inventory';inv.mkdir()
        value=minimal.target.health_projection(self.fixture.captures(),task['target'],task['A'])
        for name in ('before','after'):
            (inv/name).mkdir();records.publish(inv/name/'health.json',value)
        framework=listing(name='android',uid=1000).replace('/system/app/Optional/base.apk',
            '/system/framework/framework-res.apk')
        minimal.raw.publish_captured_bytes(inv,'current-user',stdout=b'0\n',stderr=b'',returncode=0)
        minimal.raw.publish_captured_bytes(inv,'system-packages',stdout=(listing()+framework).encode(),stderr=b'',returncode=0)
        return directory,task,task_pin,closed,review,records.pin(source)['sha256']

    def test_no_effect_retirement_allows_one_claimed_successor_and_preserves_old_open(self):
        directory,task,task_pin,closed,review,source_sha=self.inventory_stop_fixture()
        old_open=(directory/'open.json').read_bytes()
        old_claim=(Path(task_pin['path']).parent/'android-minimal-claim.json').read_bytes()
        with mock.patch.object(minimal,'INVENTORY_PARSER_V1_SHA256',source_sha), \
                mock.patch.object(minimal,'review',return_value=review), \
                mock.patch.object(minimal.census,'closed_android',return_value=(task,closed)):
            retired=minimal.retire_inventory(self.root,directory)
            self.assertEqual(records.read(records.verify(retired))['cleanup_effect_intents'],0)
            with self.assertRaisesRegex(ValueError,'preparation is retired'):
                minimal.Run(self.root,directory).check()
            def inventory(run,folder):
                folder.mkdir();return records.publish(folder/'result.json',dict(selection=dict(selected=[])))
            successor=self.root/'workspace/private/successor'
            with mock.patch.object(minimal.Run,'inventory',new=inventory):
                minimal.prepare(self.root,Path(task_pin['path']),successor,
                    operator_statement='fixture cleanup',attended=True,replace_inventory=Path(retired['path']))
                with self.assertRaisesRegex(ValueError,'replacement is already claimed'):
                    minimal.prepare(self.root,Path(task_pin['path']),self.root/'workspace/private/third',
                        operator_statement='fixture cleanup',attended=True,replace_inventory=Path(retired['path']))
            self.assertEqual((directory/'open.json').read_bytes(),old_open)
            self.assertEqual((Path(task_pin['path']).parent/'android-minimal-claim.json').read_bytes(),old_claim)
            records.Journal(directory/'journal').append('started',fixture=True)
            with self.assertRaisesRegex(ValueError,'execution or reconciliation'):
                minimal.Run(self.root,successor)

    def test_inventory_retirement_rejects_unsuccessful_raw_or_any_execution_start(self):
        directory,task,task_pin,closed,review,source_sha=self.inventory_stop_fixture()
        with mock.patch.object(minimal,'INVENTORY_PARSER_V1_SHA256',source_sha), \
                mock.patch.object(minimal.census,'closed_android',return_value=(task,closed)):
            minimal.inventory_no_effect_projection(self.root,directory)
            (directory/'journal').rmdir()
            with self.assertRaisesRegex(ValueError,'journal is missing'):
                minimal.inventory_no_effect_projection(self.root,directory)
            self.assertFalse((directory/'journal').exists())
            (directory/'journal').mkdir()
            for suffix in ('.capture.json','.stdout.bin','.stderr.bin'):
                (directory/'inventory'/('current-user'+suffix)).unlink()
            minimal.raw.publish_captured_bytes(directory/'inventory','current-user',
                stdout=b'0\n',stderr=b'failed\n',returncode=1)
            with self.assertRaises(minimal.raw.RawCaptureError):
                minimal.inventory_no_effect_projection(self.root,directory)
            records.Journal(directory/'journal').append('intent',key=NAME,kind='uninstall',detail={})
            with self.assertRaisesRegex(ValueError,'execution or reconciliation'):
                minimal.inventory_no_effect_projection(self.root,directory)

    def test_known_host_metadata_limit_retirement_does_not_accept_timeout_or_transport_failure(self):
        directory,task,task_pin,closed,review,source_sha=self.inventory_stop_fixture()
        inv=directory/'inventory'
        for name,text in [('home',HOME+'/.Home\n'),('ime',IME+'/.Keyboard\n'),
                ('storage-stat','NATIVE_PARTITION 41 96923648 401516544 native_data\nF2FS_STAT 4096 8388092 1000 2000 f2f52010\n')]:
            minimal.raw.publish_captured_bytes(inv,name,stdout=text.encode())
        folder=inv/'packages';folder.mkdir()
        handle=minimal.raw.acquire_command([sys.executable,'-c',
            "import sys,time;sys.stdout.buffer.write(b'x'*200000);sys.stdout.flush();time.sleep(30)"],
            folder,NAME,timeout=5,stdout_maximum=131072,stderr_maximum=16384)
        self.assertTrue(handle.output_exceeded);self.assertEqual(handle.returncode,-15)
        with mock.patch.object(minimal,'INVENTORY_METADATA_LIMIT_SHA256',source_sha), \
                mock.patch.object(minimal.census,'closed_android',return_value=(task,closed)):
            value=minimal.inventory_no_effect_projection(self.root,directory)
            self.assertEqual(value['acquisition_case'],'METADATA_STDOUT_LIMIT')
            self.assertEqual(value['old_parser_rejected_rows'],0)
            original=minimal.raw.load_handle
            for changes in (dict(timed_out=True),dict(output_exceeded=False),dict(returncode=1),
                    dict(producer_error_type='OSError')):
                with self.subTest(changes=changes),mock.patch.object(minimal.raw,'load_handle',
                        side_effect=lambda path:replace(handle,**changes) if Path(path)==handle.receipt_path else original(path)):
                    with self.assertRaisesRegex(ValueError,'host stdout-limit'):
                        minimal.inventory_no_effect_projection(self.root,directory)
            stderr=handle.receipt_path.parent/handle.stderr['name']
            stderr.chmod(0o600);stderr.write_bytes(b'changed');stderr.chmod(0o400)
            with self.assertRaises(minimal.raw.RawCaptureError):
                minimal.inventory_no_effect_projection(self.root,directory)

    def test_linked_claims_keep_one_child_and_reject_duplicate_opens(self):
        first,task,task_pin,closed,review,source_sha=self.inventory_stop_fixture()
        initial=records.read(first/'open.json');first_open=records.pin(first/'open.json')
        root_claim=records.pin(Path(task_pin['path']).parent/'android-minimal-claim.json')
        retired1=records.publish(first/'inventory-no-effect-close.json',dict(fixture='first'))
        second=self.root/'workspace/private/second-link';second.mkdir()
        second_open=records.publish(second/'open.json',initial)
        child1=dict(schema=minimal.SCHEMA+'-inventory-replacement-claim',original_claim=root_claim,
            retired_inventory=retired1,task=task_pin,closed=closed,open=second_open)
        first_child=records.publish(minimal.child_claim_path(root_claim),child1)
        retired2=records.publish(second/'inventory-no-effect-close.json',dict(fixture='second'))
        third=self.root/'workspace/private/third-link';third.mkdir()
        third_open=records.publish(third/'open.json',initial)
        child2=records.publish(minimal.child_claim_path(first_child),dict(
            schema=minimal.SCHEMA+'-inventory-replacement-claim',original_claim=first_child,
            retired_inventory=retired2,task=task_pin,closed=closed,open=third_open))
        selected,pins,ancestors=minimal.claim_lineage(self.root,initial,third_open)
        self.assertEqual(selected,child2);self.assertEqual(len(ancestors),2)
        self.assertEqual(minimal.child_claim_path(first_child),second/'inventory-replacement-claim.json')
        Path(first_child['path']).unlink();records.publish(Path(first_child['path']),dict(child1,open=first_open))
        with self.assertRaisesRegex(ValueError,'cycle or duplicate'):
            minimal.claim_lineage(self.root,initial,third_open)


if __name__=='__main__':unittest.main()
