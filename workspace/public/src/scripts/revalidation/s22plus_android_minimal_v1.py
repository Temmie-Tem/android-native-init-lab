"""Fixed primary-user optional-app cleanup after a closed Android32 G2 task.

Package Manager only. No caller package list, raw deletion, mount, flash or GPT
write. An uncertain command is never replayed; reconciliation is read-only.
"""
import argparse
from collections import Counter
from pathlib import Path
import re
import shlex

import consumed_candidate_registry_v1 as registry
import device_action_raw_capture_v1 as raw
import s22plus_boot_only_f1_transport as transport
import s22plus_native_android_storage_v1 as census
import s22plus_native_gpt_android_v1 as gpt_android
import s22plus_native_gpt_profile_v1 as gpt
import s22plus_native_target_io_v3 as target
import s22plus_native_task_v3 as task_owner
from s22plus_native_records_v3 import (Journal,clock,digest,host_boot,pin,private_path,
    publish,read,require,verify)

SCHEMA='s22plus-android-minimal-v1'
POLICY='docs/operations/S22PLUS_ANDROID_MINIMAL_V1.md'
REVIEW='workspace/public/src/device-action/bindings/s22plus_android_minimal_v1_review.json'
INVENTORY_PARSER_V1_SHA256='ae5f052259cd98fd554addfcacf998bbd437ef1fc13c2e90c42e46f1ebf54120'
OPEN_FIELDS={'schema','mode','task','closed','review','operator_statement','host_boot',
    'opened_ns','deadline_ns','source_snapshot'}
# Optional consumer apps only. Frameworks, stores, browsers, telephony, providers,
# SystemUI, settings, input, files, connectivity, GMS/WebView and root are absent.
OPTIONAL=(
    'com.samsung.android.app.spage','com.samsung.android.app.tips','com.samsung.android.voc',
    'com.samsung.android.game.gamehome','com.samsung.android.game.gametools',
    'com.samsung.android.arzone','com.samsung.android.aremoji','com.samsung.android.ardrawing',
    'com.samsung.android.app.camera.sticker.facearavatar','com.samsung.android.kidsinstaller',
    'com.samsung.android.app.notes','com.samsung.android.app.reminder','com.sec.android.app.shealth',
    'com.samsung.android.app.watchmanager','com.samsung.android.oneconnect',
    'com.samsung.android.bixby.agent','com.samsung.android.bixby.wakeup',
    'com.microsoft.appmanager','com.microsoft.skydrive','com.microsoft.office.officehubrow',
    'com.microsoft.office.outlook','com.linkedin.android','com.netflix.mediaclient',
    'com.netflix.partner.activation','com.facebook.katana','com.facebook.appmanager',
    'com.facebook.services','com.facebook.system','com.google.android.youtube',
    'com.google.android.apps.youtube.music','com.google.android.apps.tachyon',
    'com.google.android.apps.docs','com.google.android.apps.photos','com.google.android.gm',
    'com.google.android.apps.maps',
)
PACKAGE=re.compile(r'[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+')
LIST=['shell','cmd','package','list','packages','-s','-f','-U','--show-versioncode','--user','0']
HOME=['shell','cmd','package','resolve-activity','--brief','--user','0','-a',
    'android.intent.action.MAIN','-c','android.intent.category.HOME']
IME=['shell','settings','get','secure','default_input_method']
USER=['shell','am','get-current-user']


def source_paths(root):
    return tuple(sorted(set(task_owner.source_paths(str(Path(root).resolve())))|
        {Path(root)/POLICY,Path(__file__).resolve()}))


def review(root):
    receipt=pin(Path(root)/REVIEW);value=read(verify(receipt))
    require(set(value)=={'schema','verdict','scope','sources','reviewer','findings'}
        and value['schema']==SCHEMA+'-review' and value['verdict']=='PASS_GO'
        and value['scope']=='FIXED_OPTIONAL_PRIMARY_USER_CLEANUP' and value['findings']==[],
        'Android-minimal independent review is not PASS_GO')
    require([row['path'] for row in value['sources']]==[str(p) for p in source_paths(root)],
        'Android-minimal reviewed closure differs')
    for row in value['sources']:task_owner.unchanged(row)
    return receipt


def packages(text):
    rows={}
    for line in text.splitlines():
        fields=line.split();require(len(fields)==3 and fields[0].startswith('package:'),
            'Package Manager list row differs')
        path,separator,name=fields[0][8:].rpartition('=')
        require(separator and (PACKAGE.fullmatch(name) or name=='android') and name not in rows
            and path.startswith(('/system/','/product/','/system_ext/','/vendor/','/data/app/','/apex/'))
            and Path(path).as_posix()==path and '..' not in Path(path).parts and path.endswith('.apk'),
            'Package Manager path/name differs')
        values={}
        for item in fields[1:]:
            key,colon,value=item.partition(':')
            require(colon and key not in values and re.fullmatch('[0-9]{1,18}',value),
                'Package Manager numeric field differs')
            values[key]=int(value)
        require(set(values)=={'uid','versionCode'},'Package Manager fields differ')
        rows[name]=dict(name=name,path=path,uid=values['uid'],version=values['versionCode'])
    require(len(rows)<=1024,'Package Manager list exceeds fixed bound')
    return rows


def component(text):
    matches=[line.strip().split('/',1)[0] for line in text.splitlines()
        if re.fullmatch(r'[A-Za-z][A-Za-z0-9_.]+/[A-Za-z0-9_.$]+',line.strip())]
    require(len(matches)==1 and PACKAGE.fullmatch(matches[0]),'default Android component is absent or ambiguous')
    return matches[0]


def package_metadata(text,row):
    # An updated system app may also have a hidden factory copy. Only the
    # active Packages section owns current user state and installation bytes.
    active=text.split('Hidden system packages:',1)[0]
    marker='Package ['+row['name']+']'
    require(active.count(marker)==1,'active package metadata is absent or ambiguous')
    block=active.split(marker,1)[1]
    def one(pattern):
        values=re.findall(pattern,block,re.M)
        require(len(values)==1,'package metadata field is absent or duplicated')
        return values[0]
    uid=int(one(r'^\s*(?:userId|appId)=([0-9]+)\s*$'))
    version=int(one(r'^\s*versionCode=([0-9]+)(?:\s.*)?$'))
    code=one(r'^\s*codePath=(\S+)\s*$')
    flags=one(r'^\s*(?:pkgFlags|flags)=\[([^\]]*)\]\s*$').split()
    state=one(r'^\s*User 0: (.*)$')
    require(uid==row['uid'] and version==row['version'] and 'SYSTEM' in flags
        and (row['path']==code or row['path'].startswith(code+'/')),
        'active package identity changed during inventory')
    values=dict(re.findall(r'([A-Za-z]+)=([^\s]+)',state))
    require('installed' in values and 'enabled' in values,'primary-user package state is incomplete')
    shared=bool(re.search(r'^\s*(?:sharedUser|sharedUserId)=(?!null\b)\S+',block,re.M))
    ordinary=(values['installed']=='true' and values['enabled']=='0'
        and values.get('hidden','false')=='false' and values.get('suspended','false')=='false')
    return dict(**row,code_path=code,flags=sorted(flags),shared_uid=shared,
        ordinary_primary_user=ordinary,persistent='PERSISTENT' in flags or 'coreApp=true' in block)


def selection(all_packages,metadata,home,ime):
    counts=Counter(row['uid'] for row in all_packages.values());selected=[];excluded={}
    for name in OPTIONAL:
        if name not in all_packages:continue
        row=metadata[name]
        reason=('required-component' if name in (home,ime,'android') or row['path'].startswith('/apex/') else
            'system-or-shared-uid' if row['uid']<10000 or counts[row['uid']]!=1 or row['shared_uid'] else
            'persistent-component' if row['persistent'] else
            'customized-or-disabled-user-state' if not row['ordinary_primary_user'] else None)
        if reason:excluded[name]=reason
        else:selected.append(row)
    return dict(selected=selected,excluded=excluded,home=home,ime=ime,
        declared_optional_count=len(OPTIONAL),installed_system_count=len(all_packages))


def saved_sources(root,directory,opened):
    """Verify historical review through its saved bytes, not its moving path."""
    snapshot=read(verify(opened['source_snapshot']))
    base=private_path(root,verify(opened['source_snapshot'])).parent
    require(base==Path(directory)/'source-snapshot'
        and snapshot['schema']=='s22plus-native-v3-source-snapshot-v1'
        and snapshot['review']==opened['review'],'cleanup source snapshot review differs')
    for row in snapshot['sources']:
        require(private_path(root,row['snapshot']['path']).is_relative_to(base),
            'cleanup saved source is outside its snapshot')
        verify(row['snapshot'])
        require(all(row['snapshot'][k]==row['original'][k] for k in ('size','sha256')),
            'cleanup preserved source bytes differ')
    copies=[row['snapshot'] for row in snapshot['sources'] if row['original']==opened['review']]
    require(len(copies)==1,'cleanup snapshot has no unique saved review')
    saved=read(verify(copies[0]))
    require(saved['schema']==SCHEMA+'-review' and saved['verdict']=='PASS_GO'
        and saved['scope']=='FIXED_OPTIONAL_PRIMARY_USER_CLEANUP' and saved['findings']==[]
        and [row['original'] for row in snapshot['sources']]==saved['sources']+[opened['review']],
        'cleanup source snapshot omits reviewed sources')
    return snapshot


def existing_empty_journal(root,directory):
    path=Path(directory)/'journal'
    require(path.is_dir(),'original cleanup journal is missing')
    path=private_path(root,path)
    return not Journal(path).rows()


def inventory_no_effect_projection(root,directory):
    """H0 proof of the known successful-read, android/APEX parser-only stop."""
    directory=private_path(root,directory);opened=read(directory/'open.json')
    require(set(opened)==OPEN_FIELDS and opened['schema']==SCHEMA and opened['mode']=='minimal-management'
        and opened['deadline_ns']==opened['opened_ns']+900_000_000_000,
        'old inventory open differs')
    require(existing_empty_journal(root,directory)
        and {p.name for p in directory.iterdir()}<=
            {'open.json','source-snapshot','journal','inventory','inventory-no-effect-close.json'},
        'inventory retirement found execution or reconciliation activity')
    folder=directory/'inventory'
    expected={'before','after'}|{name+suffix for name in ('current-user','system-packages')
        for suffix in ('.capture.json','.stdout.bin','.stderr.bin')}
    require({p.name for p in folder.iterdir()}==expected,'inventory stopped outside the exact list-parser stage')
    snapshot=saved_sources(root,directory,opened)
    source=str(Path(root)/'workspace/public/src/scripts/revalidation/s22plus_android_minimal_v1.py')
    require(any(row['original']['path']==source and row['original']['sha256']==INVENTORY_PARSER_V1_SHA256
        for row in snapshot['sources']),'retirement source is not the known inventory parser')
    task,closed=census.closed_android(root,opened['task']['path'])
    require(read(verify(opened['task']))==task and closed==opened['closed']
        and read(verify(closed))['gpt']['status']=='RESERVED_ANDROID_REBOOT_VERIFIED',
        'retired inventory lacks its closed Android32 task')
    claim=pin(Path(opened['task']['path']).parent/'android-minimal-claim.json')
    require(read(verify(claim))==dict(schema=SCHEMA+'-claim',task=opened['task'],
        closed=closed,open=pin(directory/'open.json')),'retired inventory is not the original claim')
    before=read(folder/'before/health.json');after=read(folder/'after/health.json')
    for health in (before,after):
        require(target.health_projection(health['captures'],task['target'],task['A'])==health,
            'retired inventory health does not rederive')
    require(before['properties']==after['properties'],'retired inventory Android boot changed')
    user=raw.load_handle(folder/'current-user.capture.json')
    require(raw.decode_success_stdout(user,maximum=131072).strip()=='0','retired inventory primary user differs')
    listed=raw.load_handle(folder/'system-packages.capture.json')
    rows=packages(raw.decode_success_stdout(listed,maximum=131072))
    gaps=[row for row in rows.values() if row['name']=='android' or row['path'].startswith('/apex/')]
    require(gaps,'known android/APEX inventory parser gap is absent')
    return dict(schema=SCHEMA+'-inventory-no-effect-close',status='RETIRED_NO_CLEANUP_EFFECTS',
        open=pin(directory/'open.json'),claim=claim,closed=closed,source_snapshot=opened['source_snapshot'],
        before=pin(folder/'before/health.json'),after=pin(folder/'after/health.json'),
        current_user=pin(user.receipt_path),system_packages=pin(listed.receipt_path),
        parsed_rows=len(rows),old_parser_rejected_rows=len(gaps),cleanup_effect_intents=0)


def retire_inventory(root,directory):
    root=Path(root).resolve();directory=private_path(root,directory)
    with registry.target_session_lease(root):
        registry.require_no_f1_owner(root);review(root)
        value=inventory_no_effect_projection(root,directory)
        path=directory/'inventory-no-effect-close.json'
        if path.exists():require(read(path)==value,'inventory retirement changed');return pin(path)
        return publish(path,value)


class BoundedAndroid(target.Android):
    def __init__(self,*args,deadline,**kwargs):
        super().__init__(*args,**kwargs);self.deadline=deadline

    def command(self,arguments,name,*,timeout,before_launch=None):
        remaining=(self.deadline()-clock())/1e9
        require(remaining>0,'Android-minimal read deadline expired')
        return super().command(arguments,name,timeout=min(timeout,remaining),before_launch=before_launch)


class Run:
    def __init__(self,root,directory,*,recovering=False):
        self.root=Path(root).resolve();self.directory=private_path(self.root,directory)
        self.opened=read(self.directory/'open.json');self.open_pin=pin(self.directory/'open.json')
        require(set(self.opened)==OPEN_FIELDS
            and self.opened['schema']==SCHEMA and self.opened['mode']=='minimal-management'
            and type(self.opened['opened_ns']) is int and self.opened['opened_ns']>0
            and self.opened['deadline_ns']==self.opened['opened_ns']+900_000_000_000
            and type(self.opened['operator_statement']) is str
            and 0<len(self.opened['operator_statement'].strip())<=4096,
            'Android-minimal open differs')
        self.task=read(verify(self.opened['task']));self.journal=Journal(self.directory/'journal')
        primary=pin(Path(self.opened['task']['path']).parent/'android-minimal-claim.json')
        claim=read(verify(primary));self.claim_pins=[primary];self.predecessor=None
        if claim['open']==self.open_pin:
            require(claim==dict(schema=SCHEMA+'-claim',task=self.opened['task'],
                closed=self.opened['closed'],open=self.open_pin),'cleanup original claim differs')
        else:
            replacement=pin(Path(primary['path']).with_name('android-minimal-inventory-replacement-claim.json'))
            value=read(verify(replacement));retired=read(verify(value['retired_inventory']))
            self.predecessor=Path(retired['open']['path']).parent
            require(retired==inventory_no_effect_projection(self.root,self.predecessor)
                and value==dict(schema=SCHEMA+'-inventory-replacement-claim',original_claim=primary,
                    retired_inventory=pin(self.predecessor/'inventory-no-effect-close.json'),
                    task=self.opened['task'],closed=self.opened['closed'],open=self.open_pin),
                'cleanup replacement does not join its no-effect preparation')
            old=read(verify(retired['open']))
            require(old['operator_statement']==self.opened['operator_statement']
                and old['host_boot']==self.opened['host_boot'],'replacement changed its foreground request/host')
            self.claim_pins.extend([replacement,value['retired_inventory']])
        closed_task,closed=census.closed_android(self.root,self.opened['task']['path'])
        require(closed_task==self.task and closed==self.opened['closed']
            and read(verify(closed))['gpt']['status']=='RESERVED_ANDROID_REBOOT_VERIFIED',
            'cleanup requires a rederived completed Android32 G2 task')
        saved_sources(self.root,self.directory,self.opened)
        self.recovering=recovering
        self.deadline_ns=self.opened['deadline_ns']
        if recovering:
            recovery=read(self.directory/'reconcile.json')
            require(recovery['open']==self.open_pin and recovery['read_only'] is True
                and recovery['deadline_ns']==recovery['opened_ns']+300_000_000_000,
                'close-only reconciliation binding differs')
            self.deadline_ns=recovery['deadline_ns']
        self.sealed=gpt.vectors(self.task['N']['gpt'])
        require(gpt.geometry(self.sealed,'proposed')['userdata_sectors']==gpt.ANDROID32_USER,
            'Android-minimal requires the Android32 layout')
        self.basis=dict(layout='proposed',geometry=read(verify(self.opened['closed']))['gpt']['geometry'])

    def check(self,*,reserve=0):
        require(not (self.directory/'inventory-no-effect-close.json').exists(),'original inventory preparation is retired')
        for receipt in self.claim_pins:verify(receipt)
        if self.predecessor is not None:
            require(existing_empty_journal(self.root,self.predecessor),'retired preparation gained execution activity')
        require(pin(self.directory/'open.json')==self.open_pin and host_boot()==self.opened['host_boot']
            and clock()+int(reserve*1e9)<self.deadline_ns,'Android-minimal binding or deadline changed')
        require(review(self.root)==self.opened['review'],'Android-minimal review changed')
        registry.require_no_f1_owner(self.root)
        task_owner.unchanged(self.task['A']['ap'],maximum=128*1024*1024)
        verify(self.opened['task']);verify(self.opened['closed'])

    def android(self,folder):
        Path(folder).parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        return BoundedAndroid(self.task['adb'],self.task['target'],self.task['A'],folder,
            guard=self.check,deadline=lambda:self.deadline_ns)

    def command(self,folder,name,arguments,*,maximum=131072,timeout=20,before=None):
        self.check();folder=Path(folder);folder.mkdir(mode=0o700,parents=True,exist_ok=True)
        remaining=(self.deadline_ns-clock())/1e9;require(remaining>0,'command deadline expired')
        with transport.pin_regular_file(Path(self.task['adb']['path']),label='ADB',
                expected_size=self.task['adb']['size'],expected_sha256=self.task['adb']['sha256']) as tool:
            self.check()
            if before is not None:before()
            return raw.acquire_command([str(tool.path),'-s',self.task['target']['serial'],*arguments],
                folder,name,timeout=min(timeout,remaining),stdout_maximum=maximum,stderr_maximum=16384)

    def text(self,*args,**kwargs):
        return raw.decode_success_stdout(self.command(*args,**kwargs),maximum=kwargs.get('maximum',131072))

    def health(self,folder,*,wait=False):
        client=self.android(folder)
        if wait:client.wait_ready(deadline_ns=min(self.deadline_ns,clock()+180_000_000_000))
        return client.health()

    def inventory(self,folder):
        folder=Path(folder);before=self.health(folder/'before')
        try:
            require(self.text(folder,'current-user',USER).strip()=='0','primary Android user is not active')
            listed=packages(self.text(folder,'system-packages',LIST))
            home=component(self.text(folder,'home',HOME));ime=component(self.text(folder,'ime',IME))
            storage=gpt_android.storage_stat(self.text(folder,'storage-stat',
                ['shell','su -c '+shlex.quote(gpt_android.STAT_SCRIPT)],maximum=16384),self.basis,self.sealed)
            metadata={}
            for name in OPTIONAL:
                if name in listed:metadata[name]=package_metadata(self.text(folder/'packages',name,
                    ['shell','dumpsys','package',name]),listed[name])
        finally:after=self.health(folder/'after')
        require(before['properties']==after['properties'],'Android boot changed during package inventory')
        value=dict(schema=SCHEMA,selection=selection(listed,metadata,home,ime),
            storage=storage,before=pin(folder/'before/health.json'),after=pin(folder/'after/health.json'))
        return publish(folder/'result.json',value)

    def inventory_projection(self):
        folder=self.directory/'inventory';value=read(folder/'result.json')
        texts=lambda name:raw.decode_success_stdout(raw.load_handle(folder/(name+'.capture.json')),maximum=131072)
        require(texts('current-user').strip()=='0','inventory primary user differs')
        listed=packages(texts('system-packages'));home=component(texts('home'));ime=component(texts('ime'))
        metadata={name:package_metadata(texts('packages/'+name),listed[name]) for name in OPTIONAL if name in listed}
        require(value['schema']==SCHEMA and value['selection']==selection(listed,metadata,home,ime),
            'cleanup manifest does not rederive from raw inventory')
        require(value['storage']==gpt_android.storage_stat(texts('storage-stat'),self.basis,self.sealed),
            'initial cleanup capacity does not rederive')
        before=read(verify(value['before']));after=read(verify(value['after']))
        for health in (before,after):
            require(target.health_projection(health['captures'],self.task['target'],self.task['A'])==health,
                'inventory rooted health does not rederive')
        require(before['properties']==after['properties'],'inventory boot differs')
        return value

    def intent(self,kind,**detail):
        self.check(reserve=180)
        require(not self.recovering and not any(r['event']=='stopped' for r in self.journal.rows()),
            'cleanup is stopped or read-only')
        key=detail.get('package',kind)
        require(not any(r['event']=='intent' and r['data']['key']==key for r in self.journal.rows()),
            'cleanup effect already has an intent; replay forbidden')
        self.journal.append('intent',key=key,kind=kind,detail=detail)
        self.check(reserve=180)

    def same_boot(self,folder,initial):
        require(self.text(folder,'current-user',USER).strip()=='0','cleanup user changed before effect')
        require(self.text(folder,'devpath',['get-devpath']).strip()==self.task['target']['topology'],
            'cleanup physical lane changed')
        text=self.text(folder,'properties',['shell','sh -c '+shlex.quote(target.PROPERTIES)],maximum=16384)
        require(target.fields(text,target.PROPERTY_FIELDS)==initial['properties'],
            'cleanup Android boot or properties changed')

    def snapshot(self,folder,plan,*,wait=False):
        folder=Path(folder);before=self.health(folder/'before',wait=wait)
        try:
            require(self.text(folder,'current-user',USER).strip()=='0','final user is not primary')
            present=packages(self.text(folder,'system-packages',LIST))
            home=component(self.text(folder,'home',HOME));ime=component(self.text(folder,'ime',IME))
            require((home,ime)==(plan['selection']['home'],plan['selection']['ime']),
                'required home/input component changed')
            client=self.android(folder/'gpt')
            # The shared census reader owns a fixed 15-second raw acquisition.
            client.guard=lambda:self.check(reserve=15)
            census.command(client)
            proof=gpt_android.metadata(raw.read_stdout(raw.load_handle(folder/'gpt/metadata.capture.json'),
                maximum=65536),self.sealed,'proposed')
            raw.require_success(raw.load_handle(folder/'gpt/metadata.capture.json'))
            stats=self.text(folder,'storage-stat',['shell','su -c '+shlex.quote(gpt_android.STAT_SCRIPT)],maximum=16384)
            storage=gpt_android.storage_stat(stats,self.basis,self.sealed)
        finally:after=self.health(folder/'after')
        require(before['properties']==after['properties'],'Android boot changed during final snapshot')
        result=self.snapshot_projection(folder,plan)
        publish(folder/'result.json',result);return result

    def snapshot_projection(self,folder,plan):
        folder=Path(folder)
        text=lambda name:raw.decode_success_stdout(raw.load_handle(folder/(name+'.capture.json')),maximum=131072)
        before=read(folder/'before/health.json');after=read(folder/'after/health.json')
        for health in (before,after):
            require(target.health_projection(health['captures'],self.task['target'],self.task['A'])==health,
                'snapshot rooted health differs from raw')
        require(before['properties']==after['properties'] and text('current-user').strip()=='0',
            'snapshot boot or primary user differs')
        present=packages(text('system-packages'));home=component(text('home'));ime=component(text('ime'))
        require((home,ime)==(plan['selection']['home'],plan['selection']['ime']),
            'snapshot required components differ')
        census.require_shell_v2(pin(folder/'gpt/shell-features.capture.json'))
        handle=raw.load_handle(folder/'gpt/metadata.capture.json');raw.require_success(handle)
        proof=gpt_android.metadata(raw.read_stdout(handle,maximum=65536),self.sealed,'proposed')
        storage=gpt_android.storage_stat(text('storage-stat'),self.basis,self.sealed)
        return dict(schema=SCHEMA,before=pin(folder/'before/health.json'),after=pin(folder/'after/health.json'),
            remaining=[row['name'] for row in plan['selection']['selected'] if row['name'] in present],
            home=home,ime=ime,gpt=proof,storage=storage)

    def terminal_projection(self):
        """H0 rederivation of all selected effects, departure and final raw health."""
        plan=self.inventory_projection();rows=self.journal.rows()
        names=[row['name'] for row in plan['selection']['selected']]
        if not names:
            require(not rows,'empty cleanup unexpectedly has journal actions')
            return dict(schema=SCHEMA,status='NO_CHANGES_NEEDED',
                terminal_state='ANDROID_CLOSED_HEALTHY',inventory=pin(self.directory/'inventory/result.json'),
                final_health=plan['after'],removed_count=0,reboot_verified=False,
                source_snapshot=self.opened['source_snapshot'])
        intents=[r['data'] for r in rows if r['event']=='intent']
        require([r['key'] for r in intents]==names+['reboot'],'cleanup effect sequence is incomplete')
        initial=read(verify(plan['after']))
        for number,row in enumerate(plan['selection']['selected']):
            folder=self.directory/f'package-{number:03d}';name=row['name'];intent=intents[number]
            require(intent==dict(key=name,kind='uninstall',detail=dict(package=name,metadata=row)),
                'package intent does not join selected manifest')
            text=lambda label:raw.decode_success_stdout(raw.load_handle(folder/(label+'.capture.json')),maximum=131072)
            require(text('devpath').strip()==self.task['target']['topology']
                and text('current-user').strip()=='0'
                and target.fields(text('properties'),target.PROPERTY_FIELDS)==initial['properties'],
                'uninstall lacks its same-boot physical target binding')
            current=packages(text('before-package'))
            require(name in current and package_metadata(text('before-metadata'),current[name])==row
                and text('uninstall').strip()=='Success' and name not in packages(text('after-package')),
                'uninstall raw result or post-state differs')
        before=self.snapshot_projection(self.directory/'before-reboot',plan)
        after=self.snapshot_projection(self.directory/'final',plan)
        folder=self.directory/'reboot';intent=intents[-1]
        require(intent['kind']=='reboot' and intent['detail']['departure']==pin(folder/'before.json'),
            'reboot intent does not join its original USB generation')
        handle=raw.load_handle(folder/'reboot.capture.json');raw.require_success(handle)
        require(raw.read_stdout(handle,maximum=16384)==b'','reboot returned unexpected output')
        departure=read(folder/'departure.json');usb=read(folder/'before.json')
        require(departure['before']==usb and departure['departed'] is True
            and departure['deadline_ns']==intent['detail']['deadline_ns']
            and usb['boottime_ns']<=departure['observed_ns']<departure['deadline_ns'],
            'reboot departure is not bounded to its original generation')
        a=read(verify(before['after']));b=read(verify(after['after']))
        require(a['boot_id_sha256']!=b['boot_id_sha256'] and before['gpt']==after['gpt']
            and before['storage']['total_bytes']==after['storage']['total_bytes']
            and not before['remaining'] and not after['remaining'],'cleanup reboot persistence is unproved')
        for name,value in (('before-reboot',before),('final',after)):
            path=self.directory/name/'result.json'
            if path.exists():require(read(path)==value,'snapshot aggregate differs')
            else:publish(path,value)
        return dict(schema=SCHEMA,status='COMPLETE',terminal_state='ANDROID_CLOSED_HEALTHY',
            inventory=pin(self.directory/'inventory/result.json'),
            before_reboot=pin(self.directory/'before-reboot/result.json'),final=pin(self.directory/'final/result.json'),
            removed_count=len(names),reboot_verified=True,
            observed_available_bytes_change=after['storage']['available_bytes']-plan['storage']['available_bytes'],
            source_snapshot=self.opened['source_snapshot'])

    def execute(self,*,attended):
        require(attended is True,'cleanup effects require actual attendance')
        with registry.target_session_lease(self.root):
            self.check();require(not self.journal.rows(),'cleanup already started; use reconciliation')
            plan=self.inventory_projection();initial=read(verify(plan['after']))
            if not plan['selection']['selected']:
                return publish(self.directory/'terminal.json',self.terminal_projection())
            self.journal.append('started',inventory=pin(self.directory/'inventory/result.json'))
            try:
                for number,row in enumerate(plan['selection']['selected']):
                    folder=self.directory/f'package-{number:03d}';name=row['name']
                    self.same_boot(folder,initial)
                    current=packages(self.text(folder,'before-package',[*LIST,name]))
                    require(name in current and package_metadata(self.text(folder,'before-metadata',
                        ['shell','dumpsys','package',name]),current[name])==row,'selected package changed before intent')
                    answer=self.text(folder,'uninstall',['shell','pm','uninstall','--user','0',
                        '--versionCode',str(row['version']),name],
                        maximum=16384,before=lambda:self.intent('uninstall',package=name,metadata=row))
                    require(answer.strip()=='Success','Package Manager uninstall did not report success')
                    require(name not in packages(self.text(folder,'after-package',[*LIST,name])),
                        'removed package remains installed for primary user')
                    self.journal.append('complete',key=name,capture=pin(folder/'uninstall.capture.json'),
                        post_state=pin(folder/'after-package.capture.json'))
                before=self.snapshot(self.directory/'before-reboot',plan)
                require(not before['remaining'],'selected optional packages remain installed')
                folder=self.directory/'reboot';folder.mkdir(mode=0o700)
                usb=target.usb_snapshot(target.lane.SOURCE_TOPOLOGY,folder)
                publish(folder/'before.json',usb);deadline=min(self.deadline_ns,clock()+30_000_000_000)
                self.command(folder,'reboot',['reboot'],maximum=16384,timeout=15,
                    before=lambda:self.intent('reboot',departure=pin(folder/'before.json'),deadline_ns=deadline))
                raw.require_success(raw.load_handle(folder/'reboot.capture.json'))
                departure=target.wait_departure(usb,folder,deadline_ns=deadline,guard=self.check)
                publish(folder/'departure.json',departure)
                self.journal.append('complete',key='reboot',capture=pin(folder/'reboot.capture.json'),
                    departure=pin(folder/'departure.json'))
                after=self.snapshot(self.directory/'final',plan,wait=True)
                a=read(verify(before['after']));b=read(verify(after['after']))
                require(a['boot_id_sha256']!=b['boot_id_sha256'] and before['gpt']==after['gpt']
                    and before['storage']['total_bytes']==after['storage']['total_bytes'] and not after['remaining'],
                    'post-cleanup reboot/state persistence is unproved')
            except Exception as error:
                self.journal.append('stopped',error_type=type(error).__name__)
                return dict(state='STOPPED_RECONCILIATION_REQUIRED',device_effect_replay=False)
            return publish(self.directory/'terminal.json',self.terminal_projection())

    def reconcile(self):
        """No mutation, reboot or retransmission; one bounded close-only read."""
        with registry.target_session_lease(self.root):
            registry.require_no_f1_owner(self.root)
            require(review(self.root)==self.opened['review'],'reconciliation source review changed')
            try:value=self.terminal_projection()
            except (ValueError,OSError,KeyError,raw.RawCaptureError):value=None
            if value is not None:
                path=self.directory/'terminal.json'
                if path.exists():require(read(path)==value,'terminal differs from retained raw proof');return pin(path)
                return publish(path,value)
            require(not (self.directory/'terminal.json').exists(),'cleanup is already terminal')
            require(host_boot()==self.opened['host_boot'] and review(self.root)==self.opened['review'],
                'reconciliation host or reviewed source changed')
            plan=self.inventory_projection();record=self.directory/'reconcile.json'
            if record.exists():
                value=self.snapshot_projection(self.directory/'reconciliation',plan)
                aggregate=self.directory/'reconciliation/result.json'
                if aggregate.exists():require(read(aggregate)==value,'reconciliation aggregate differs')
                else:publish(aggregate,value)
            else:
                now=clock();publish(record,dict(open=self.open_pin,opened_ns=now,
                    deadline_ns=now+300_000_000_000,read_only=True))
                value=Run(self.root,self.directory,recovering=True).snapshot(
                    self.directory/'reconciliation',plan,wait=True)
            return publish(self.directory/'terminal.json',dict(schema=SCHEMA,status='INCOMPLETE',
                terminal_state='ANDROID_CLOSED_HEALTHY',final=pin(self.directory/'reconciliation/result.json'),
                remaining=value['remaining'],cleanup_replay_permitted=False,reboot_verified=False,
                source_snapshot=self.opened['source_snapshot']))


def prepare(root,task_path,output,*,operator_statement,attended,replace_inventory=None):
    root=Path(root).resolve();require(attended is True and type(operator_statement) is str
        and 0<len(operator_statement.strip())<=4096,'actual minimal-Android request/attendance is required')
    qualified=review(root);task_path=private_path(root,task_path)
    task,closed=census.closed_android(root,task_path)
    require(read(verify(closed))['gpt']['status']=='RESERVED_ANDROID_REBOOT_VERIFIED'
        and gpt.geometry(gpt.vectors(task['N']['gpt']),'proposed')['userdata_sectors']==gpt.ANDROID32_USER,
        'cleanup requires the completed 32 GiB G2 result')
    output=private_path(root,output,exists=False);require(not output.exists(),'cleanup output already exists')
    with registry.target_session_lease(root):
        registry.require_no_f1_owner(root)
        claim_path=task_path.parent/'android-minimal-claim.json'
        replacement=None
        if replace_inventory is None:
            require(not claim_path.exists(),'this closed G2 task already has a cleanup claim; use its reconciliation')
        else:
            retired_pin=pin(private_path(root,replace_inventory));retired=read(verify(retired_pin))
            original=Path(retired['open']['path']).parent
            require(Path(retired_pin['path'])==original/'inventory-no-effect-close.json'
                and retired==inventory_no_effect_projection(root,original)
                and retired['claim']==pin(claim_path),'replacement has no exact no-effect inventory retirement')
            old=read(verify(retired['open']))
            require(old['task']==pin(task_path) and old['closed']==closed
                and old['host_boot']==host_boot() and old['operator_statement']==operator_statement,
                'replacement changed the closed task, host or original foreground request')
            replacement=dict(schema=SCHEMA+'-inventory-replacement-claim',original_claim=pin(claim_path),
                retired_inventory=retired_pin,task=pin(task_path),closed=closed)
            claim_path=task_path.parent/'android-minimal-inventory-replacement-claim.json'
            require(not claim_path.exists(),'the one inventory replacement is already claimed')
        output.mkdir(mode=0o700)
        snapshot=census.snapshot_current(root,output/'source-snapshot',qualified)
        now=clock();opened=publish(output/'open.json',dict(schema=SCHEMA,mode='minimal-management',task=pin(task_path),
            closed=closed,review=qualified,operator_statement=operator_statement,host_boot=host_boot(),
            opened_ns=now,deadline_ns=now+900_000_000_000,source_snapshot=snapshot))
        publish(claim_path,dict(replacement,open=opened) if replacement is not None else
            dict(schema=SCHEMA+'-claim',task=pin(task_path),closed=closed,open=opened))
        run=Run(root,output);receipt=run.inventory(output/'inventory')
        return dict(state='READY_FOR_FIXED_CLEANUP',inventory=receipt,
            selected_count=len(read(verify(receipt))['selection']['selected']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[5])
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('prepare');p.add_argument('task',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--operator-statement',required=True);p.add_argument('--attended',action='store_true')
    p.add_argument('--replace-inventory',type=Path)
    p=sub.add_parser('execute');p.add_argument('directory',type=Path);p.add_argument('--attended',action='store_true')
    p=sub.add_parser('reconcile');p.add_argument('directory',type=Path)
    p=sub.add_parser('retire-inventory');p.add_argument('directory',type=Path)
    args=parser.parse_args()
    if args.action=='prepare':print(prepare(args.root,args.task,args.output,
        operator_statement=args.operator_statement,attended=args.attended,replace_inventory=args.replace_inventory))
    elif args.action=='execute':print(Run(args.root,args.directory).execute(attended=args.attended))
    elif args.action=='retire-inventory':print(retire_inventory(args.root,args.directory))
    else:print(Run(args.root,args.directory).reconcile())
