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
INVENTORY_DUPLICATE_FLAGS_SHA256='9b3fcba0031232ba74096e718102a252df87e1a745e7741904227db22d9ad850'
INVENTORY_METADATA_LIMIT_SHA256='0ebe5cf2dc5751c447354fc45676449c6f462f55a26a114fb9be528c82d30bbc'
INVENTORY_CAPTURE_LABEL_SHA256='d299edef842c4ed502fec2730ffd5368b7c6f8be7083855f7f8201dad05db61b'
METADATA_MAXIMUM=1024*1024
OPEN_FIELDS={'schema','mode','task','closed','review','operator_statement','host_boot',
    'opened_ns','deadline_ns','source_snapshot'}
# Optional consumer apps only. Frameworks, stores, browsers, telephony, providers,
# SystemUI, settings, input, files, connectivity, GMS/WebView and root are absent.
OLD_OPTIONAL=(
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
HISTORICAL_KEEP='docs/plans/S22PLUS_ANDROID_116_PACKAGE_ALLOWLIST_2026-07-06.txt'
DEBUG_KEEP='docs/plans/S22PLUS_ANDROID_DEBUG_CHANNEL_REQUIRED_PACKAGES_2026-07-08.txt'
PASS1='docs/reports/S22PLUS_ANDROID_DEBLOAT_PASS1_2026-07-06.md'
EXTRA_REPORT='docs/reports/S22PLUS_SYSTEM_APP_EXTRA_DEBLOAT_2026-07-06.md'
ADDITIONAL_MODE='additional-known'
USER_APPS_MODE='user-apps'
CHECKPOINT_MODE='checkpoint-complement'
CHECKPOINT_SECONDS=3600
CHECKPOINT_JOURNAL_ROWS=2052
CHECKPOINT_REPORT='docs/reports/S22PLUS_ANDROID_116_PACKAGE_CHECKPOINT_2026-07-06.md'
# Explicit foreground user-app scope. Providers, installers, GMS/GSF, WebView,
# DocumentsUI, home/input and management components are not consumer UI here.
USER_APPS=(
    'com.google.android.youtube','com.android.vending','com.google.android.apps.maps',
    'com.google.android.apps.bard','com.android.chrome','com.google.android.apps.photos',
    'com.google.android.apps.youtube.music','com.google.android.apps.docs','com.google.android.gm',
    'com.google.android.apps.tachyon','com.samsung.android.app.contacts',
    'com.sec.android.app.clockpackage','com.samsung.android.calendar','com.sec.android.gallery3d',
    'com.sec.android.app.camera','com.samsung.android.messaging','com.sec.android.app.sbrowser',
    'com.sec.android.app.myfiles','com.sec.android.app.samsungapps','com.sec.android.app.popupcalculator',
    'com.sec.android.app.voicenote','com.sec.android.daemonapp','com.samsung.android.video',
    'com.sec.android.app.music','com.diotek.sec.lookup.dictionary','com.samsung.android.app.notes',
    'com.samsung.android.voc','com.samsung.android.app.tips','com.sec.android.app.shealth',
    'com.samsung.android.oneconnect','com.samsung.android.app.watchmanager',
)
ADDITIONAL_RETAINED_CLOSE_SHA256='ef96d44b8d2a7566a9d3222cd04b6e2bc37a8807fbfc60995d21503c8ff3e1a4'


def declared_packages():
    root=Path(__file__).resolve().parents[5]
    keep=set((root/HISTORICAL_KEEP).read_text().splitlines())
    debug=(root/DEBUG_KEEP).read_text().split('Required user-0 packages:',1)[1].split('```text\n',1)[1].split('```',1)[0].splitlines()
    prior=(root/PASS1).read_text().split('Packages:\n\n```text\n',1)[1].split('```',1)[0].splitlines()
    require(keep and debug and prior and all(name=='android' or PACKAGE.fullmatch(name)
        for name in (*keep,*debug,*prior)),'historical package declarations differ')
    keep.update(debug)
    return tuple(name for name in dict.fromkeys((*OLD_OPTIONAL,*prior)) if name not in keep),frozenset(keep)


OPTIONAL,KEEP=declared_packages()


def additional_packages():
    text=(Path(__file__).resolve().parents[5]/EXTRA_REPORT).read_text()
    blocks=re.findall(r'Removed:\n\n```text\n(.*?)```',text,re.S)
    names=tuple(name for block in blocks for name in block.strip().splitlines())
    require(len(blocks)==4 and len(names)==38 and len(set(names))==len(names)
        and all(PACKAGE.fullmatch(name) and name not in KEEP for name in names),
        'historical additional-package declaration differs')
    return names


EXTRA_OPTIONAL=additional_packages()


def metadata_label(name,*,checkpoint=False):
    require((checkpoint and PACKAGE.fullmatch(name)) or name in OPTIONAL or name in EXTRA_OPTIONAL or name in USER_APPS,'metadata label is outside the fixed declaration')
    return 'pkg-'+digest(name.encode('ascii'))


LIST=['shell','cmd','package','list','packages','-s','-f','-U','--show-versioncode','--user','0']
HOME=['shell','cmd','package','resolve-activity','--brief','--user','0','-a',
    'android.intent.action.MAIN','-c','android.intent.category.HOME']
IME=['shell','settings','get','secure','default_input_method']
USER=['shell','am','get-current-user']
SAFE_MODE=['shell','getprop','persist.sys.safemode']


def source_paths(root):
    return tuple(sorted(set(task_owner.source_paths(str(Path(root).resolve())))|
        {Path(root)/POLICY,Path(__file__).resolve(),*(Path(root)/name for name in (HISTORICAL_KEEP,DEBUG_KEEP,PASS1,EXTRA_REPORT,CHECKPOINT_REPORT))}))


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


def package_metadata(text,row,*,allow_enabled=False,checkpoint=False):
    # An updated system app may also have a hidden factory copy. Only the
    # active Packages section owns current user state and installation bytes.
    active=text.split('Hidden system packages:',1)[0]
    sections=re.split(r'^Packages:[ \t]*\n',active,flags=re.M)
    require(len(sections)==2,'active Packages section is absent or duplicated')
    active=re.split(r'^\S',sections[1],maxsplit=1,flags=re.M)[0]
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
    flag_rows=re.findall(r'^\s*(pkgFlags|flags)=\[([^\]]*)\]\s*$',block,re.M)
    require(1<=len(flag_rows)<=2 and len({key for key,_ in flag_rows})==len(flag_rows)
        and len({tuple(sorted(value.split())) for _,value in flag_rows})==1,
        'package flags are absent, duplicated or contradictory')
    flags=flag_rows[0][1].split()
    state=one(r'^\s*User 0: (.*)$')
    require(uid==row['uid'] and version==row['version'] and (checkpoint or 'SYSTEM' in flags)
        and (row['path']==code or row['path'].startswith(code+'/')),
        'active package identity changed during inventory')
    values=dict(re.findall(r'([A-Za-z]+)=([^\s]+)',state))
    require('installed' in values and 'enabled' in values,'primary-user package state is incomplete')
    if checkpoint:
        require(all(len(re.findall(r'\b'+key+r'=([^\s]+)',state))==1
            for key in ('installed','enabled','hidden','suspended'))
            and all(values[key] in ('true','false') for key in ('installed','hidden','suspended'))
            and values['enabled'] in ('0','1','2','3','4'),
            'checkpoint primary-user state is incomplete or ambiguous')
    shared=bool(re.search(r'^\s*(?:sharedUser|sharedUserId)=(?!null\b)\S+',block,re.M))
    ordinary=(values['installed']=='true' and values['enabled'] in (('0','1','2','3','4') if checkpoint else ('0','1') if allow_enabled else ('0',))
        and values.get('hidden','false')=='false' and values.get('suspended','false')=='false')
    return dict(**row,code_path=code,flags=sorted(flags),shared_uid=shared,
        ordinary_primary_user=ordinary,persistent='PERSISTENT' in flags or 'coreApp=true' in block)


def selection(all_packages,metadata,home,ime,*,declaration=None,keep=KEEP,checkpoint=False):
    declaration=OPTIONAL if declaration is None else declaration
    counts=Counter(row['uid'] for row in all_packages.values());selected=[];excluded={}
    for name in declaration:
        if name not in all_packages:continue
        row=all_packages[name]
        reason=('required-component' if name in keep or name in (home,ime,'android') or (not checkpoint and row['path'].startswith('/apex/')) else
            'system-or-shared-uid' if not checkpoint and (row['uid']<10000 or counts[row['uid']]!=1) else None)
        if reason:excluded[name]=reason;continue
        row=metadata[name]
        reason=('system-or-shared-uid' if not checkpoint and row['shared_uid'] else
            'persistent-component' if not checkpoint and row['persistent'] else
            'customized-or-disabled-user-state' if not row['ordinary_primary_user'] else None)
        if reason:excluded[name]=reason
        else:selected.append(row)
    return dict(selected=selected,excluded=excluded,home=home,ime=ime,
        declared_optional_count=len(declaration),**{
            'installed_package_count' if checkpoint else 'installed_system_count':len(all_packages)})


EXPECTED_REFUSALS=frozenset({'DELETE_FAILED_INTERNAL_ERROR','DELETE_FAILED_USER_RESTRICTED','DELETE_FAILED_OWNER_BLOCKED'})


def uninstall_response(handle,*,checkpoint=False):
    if not checkpoint:
        require(raw.decode_success_stdout(handle,maximum=16384)=='Success',
            'Package Manager uninstall did not report success')
        return 'SUCCESS'
    require(not handle.timed_out and not handle.output_exceeded and handle.producer_error_type is None
        and handle.returncode in (0,1),'uninstall producer did not complete normally')
    out=raw.read_stdout(handle,maximum=16384).decode('ascii','strict').strip()
    require(raw.read_stderr(handle,maximum=16384)==b'','uninstall has unexpected stderr')
    if out=='Success':
        require(handle.returncode==0,'success response has failing status')
        return 'SUCCESS'
    match=re.fullmatch(r'Failure \[([A-Z_]+)\]',out)
    require(match is not None and match[1] in EXPECTED_REFUSALS,'uninstall response is not a declared refusal')
    return 'REFUSED_'+match[1]


def qualified_readiness_stop(run):
    folder=run.directory/'final/before'
    require((run.directory/'final').is_dir()
        and {p.name for p in (run.directory/'final').iterdir()}=={'before'},
        'user-app stop is outside final readiness')
    handles={p.stem.removesuffix('.capture'):raw.load_handle(p) for p in folder.glob('*.capture.json')}
    require(handles and {p.name for p in folder.iterdir()}=={
        name+suffix for name in handles for suffix in ('.capture.json','.stdout.bin','.stderr.bin')},
        'readiness stop capture set differs')
    inventories=sorted(name for name in handles if name.endswith('-inventory'))
    require(0<len(inventories)<=256 and inventories==[f'wait-{i:03d}-inventory' for i in range(len(inventories))],
        'readiness inventory sequence differs')
    expected=set(inventories);failure=None
    for index,name in enumerate(inventories):
        text=raw.decode_success_stdout(handles[name],maximum=16384)
        lines=text.splitlines();require(lines and lines[0]=='List of devices attached','readiness header differs')
        rows=[line.split() for line in lines[1:] if line.strip()]
        require(all(len(row)>=2 for row in rows),'readiness inventory is malformed')
        selected=[row for row in rows if row[0]==run.task['target']['serial']]
        candidates=[row for row in rows if {'model:SM_S906N','device:g0q'}<=set(row[2:])]
        require(len(selected)<=1 and len(candidates)<=1 and
            (not candidates or candidates[0][0]==run.task['target']['serial']),'readiness target is ambiguous')
        if selected and selected[0][1]=='device':
            target.select_android(text,run.task['target']);boot=f'wait-{index:03d}-boot';expected.add(boot)
            require(boot in handles,'readiness boot capture is missing');handle=handles[boot]
            if index==len(inventories)-1:
                require(handle.returncode==1 and not handle.timed_out and not handle.output_exceeded
                    and handle.producer_error_type is None and raw.read_stdout(handle,maximum=16)==b''
                    and raw.read_stderr(handle,maximum=16384)==b'error: closed\n',
                    'readiness stop is not the qualified closed-read response')
                failure=boot
            else:
                require(raw.decode_success_stdout(handle,maximum=16) in ('','0'),
                    'readiness stopped after an unexpected or already-ready boot result')
    require(failure is not None and set(handles)==expected,'readiness stop has unexpected reads')


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


def child_claim_path(claim):
    value=read(verify(claim))
    return (Path(claim['path']).with_name('android-minimal-inventory-replacement-claim.json')
        if value['schema']==SCHEMA+'-claim' else
        Path(value['open']['path']).parent/'inventory-replacement-claim.json')


def claim_lineage(root,opened,open_pin):
    current=pin(Path(opened['task']['path']).parent/'android-minimal-claim.json')
    value=read(verify(current));ancestors=[];pins=[current];seen=set()
    require(value==dict(schema=SCHEMA+'-claim',task=opened['task'],closed=opened['closed'],
        open=value['open']),'cleanup original claim differs')
    while True:
        identity=(value['open']['path'],value['open']['sha256'])
        require(identity not in seen,'cleanup claim cycle or duplicate open')
        seen.add(identity)
        if value['open']==open_pin:return current,pins,ancestors
        old=read(verify(value['open']));directory=private_path(root,Path(value['open']['path']).parent)
        require(old['operator_statement']==opened['operator_statement']
            and old['host_boot']==opened['host_boot'],'replacement changed its foreground request/host')
        retired=pin(directory/'inventory-no-effect-close.json')
        successor=pin(child_claim_path(current));new=read(verify(successor))
        require(new==dict(schema=SCHEMA+'-inventory-replacement-claim',original_claim=current,
            retired_inventory=retired,task=opened['task'],closed=opened['closed'],open=new['open']),
            'cleanup replacement claim link differs')
        ancestors.append((directory,retired));pins.extend([retired,successor]);current,value=successor,new


def inventory_no_effect_projection(root,directory):
    """H0 proof of a reviewed preparation stop with no cleanup execution."""
    directory=private_path(root,directory);opened=read(directory/'open.json')
    require(set(opened)==OPEN_FIELDS and opened['schema']==SCHEMA and opened['mode']=='minimal-management'
        and opened['deadline_ns']==opened['opened_ns']+900_000_000_000,
        'old inventory open differs')
    require(existing_empty_journal(root,directory)
        and {p.name for p in directory.iterdir()}<=
            {'open.json','source-snapshot','journal','inventory','inventory-no-effect-close.json',
             'inventory-replacement-claim.json'},
        'inventory retirement found execution or reconciliation activity')
    folder=directory/'inventory'
    snapshot=saved_sources(root,directory,opened)
    source=str(Path(root)/'workspace/public/src/scripts/revalidation/s22plus_android_minimal_v1.py')
    sources=[row['original']['sha256'] for row in snapshot['sources'] if row['original']['path']==source]
    require(len(sources)==1 and sources[0] in (INVENTORY_PARSER_V1_SHA256,
        INVENTORY_DUPLICATE_FLAGS_SHA256,INVENTORY_METADATA_LIMIT_SHA256,INVENTORY_CAPTURE_LABEL_SHA256),
        'retirement source is not a known inventory preparation')
    limit_stage=sources[0]==INVENTORY_METADATA_LIMIT_SHA256
    label_stage=sources[0]==INVENTORY_CAPTURE_LABEL_SHA256
    metadata_stage=sources[0]!=INVENTORY_PARSER_V1_SHA256
    labels=('current-user','system-packages','home','ime','storage-stat') if metadata_stage else ('current-user','system-packages')
    expected={'before','after'}|({'packages'} if metadata_stage else set())|{
        name+suffix for name in labels for suffix in ('.capture.json','.stdout.bin','.stderr.bin')}
    require({p.name for p in folder.iterdir()}==expected,'inventory stopped outside its exact parser stage')
    task,closed=census.closed_android(root,opened['task']['path'])
    require(read(verify(opened['task']))==task and closed==opened['closed']
        and read(verify(closed))['gpt']['status']=='RESERVED_ANDROID_REBOOT_VERIFIED',
        'retired inventory lacks its closed Android32 task')
    claim,_,ancestors=claim_lineage(root,opened,pin(directory/'open.json'))
    for parent,receipt in ancestors:
        require(read(verify(receipt))==inventory_no_effect_projection(root,parent),'ancestor retirement differs')
    before=read(folder/'before/health.json');after=read(folder/'after/health.json')
    for health in (before,after):
        require(target.health_projection(health['captures'],task['target'],task['A'])==health,
            'retired inventory health does not rederive')
    require(before['properties']==after['properties'],'retired inventory Android boot changed')
    user=raw.load_handle(folder/'current-user.capture.json')
    require(raw.decode_success_stdout(user,maximum=131072).strip()=='0','retired inventory primary user differs')
    listed=raw.load_handle(folder/'system-packages.capture.json')
    rows=packages(raw.decode_success_stdout(listed,maximum=131072))
    extra={}
    if metadata_stage:
        texts=lambda name:raw.decode_success_stdout(raw.load_handle(folder/(name+'.capture.json')),
            maximum=METADATA_MAXIMUM if label_stage and name.startswith('packages/') else 131072)
        component(texts('home'));component(texts('ime'))
        gpt_android.storage_stat(texts('storage-stat'),dict(layout='proposed',
            geometry=read(verify(closed))['gpt']['geometry']),gpt.vectors(task['N']['gpt']))
        present=[name for name in (OPTIONAL if limit_stage or label_stage else OLD_OPTIONAL) if name in rows]
        captured=[name for name in present if (folder/'packages'/(name+'.capture.json')).exists()]
        require(captured and captured==present[:len(captured)],'metadata captures are not a fixed inventory prefix')
        require({p.name for p in (folder/'packages').iterdir()}=={
            name+suffix for name in captured for suffix in ('.capture.json','.stdout.bin','.stderr.bin')},
            'metadata capture directory differs')
        gaps=[]
        for name in captured:
            if limit_stage and name==captured[-1]:
                handle=raw.load_handle(folder/'packages'/(name+'.capture.json'))
                require(handle.returncode==-15 and handle.output_exceeded is True
                    and handle.timed_out is False and handle.producer_error_type is None
                    and handle.stdout['size']==131072 and handle.stderr['size']==0,
                    'metadata stop is not the known host stdout-limit termination')
                raw.read_stdout(handle,maximum=131072)
                require(raw.read_stderr(handle,maximum=16384)==b'',
                    'metadata stdout-limit diagnostic stream is not empty')
                continue
            text=texts('packages/'+name);package_metadata(text,rows[name])
            block=text.split('Hidden system packages:',1)[0].split('Package ['+name+']',1)[1]
            if not (limit_stage or label_stage) and len(re.findall(r'^\s*(?:pkgFlags|flags)=\[([^\]]*)\]\s*$',block,re.M))==2:gaps.append(name)
        if label_stage:
            require(len(captured)<len(present) and raw.NAME_RE.fullmatch(present[len(captured)]) is None
                and all(raw.NAME_RE.fullmatch(name) for name in captured),
                'metadata stop is not the first invalid prelaunch capture label')
        elif not limit_stage:
            require(gaps==captured[-1:],'metadata stop is not the first identical duplicate-flags result')
        extra=dict(metadata_inputs=[pin(folder/(name+'.capture.json')) for name in labels[2:]]+
            [pin(folder/'packages'/(name+'.capture.json')) for name in captured])
        if limit_stage:extra.update(acquisition_case='METADATA_STDOUT_LIMIT',acquisition_limit_exceeded_count=1)
        elif label_stage:extra.update(acquisition_case='PRELAUNCH_CAPTURE_LABEL',
            rejected_label=present[len(captured)])
        else:extra['parser_case']='IDENTICAL_FLAGS_AND_PKGFLAGS'
    else:
        gaps=[row for row in rows.values() if row['name']=='android' or row['path'].startswith('/apex/')]
        require(gaps,'known android/APEX inventory parser gap is absent')
    return dict(schema=SCHEMA+'-inventory-no-effect-close',status='RETIRED_NO_CLEANUP_EFFECTS',
        open=pin(directory/'open.json'),claim=claim,closed=closed,source_snapshot=opened['source_snapshot'],
        before=pin(folder/'before/health.json'),after=pin(folder/'after/health.json'),
        current_user=pin(user.receipt_path),system_packages=pin(listed.receipt_path),
        parsed_rows=len(rows),old_parser_rejected_rows=len(gaps),cleanup_effect_intents=0,**extra)


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
        additional=self.opened.get('mode')==ADDITIONAL_MODE
        user_apps=self.opened.get('mode')==USER_APPS_MODE
        checkpoint=self.opened.get('mode')==CHECKPOINT_MODE
        successor=additional or user_apps or checkpoint
        require(set(self.opened)==OPEN_FIELDS|({'previous_cleanup'} if successor else set())
            and self.opened['schema']==SCHEMA and self.opened['mode'] in ('minimal-management',ADDITIONAL_MODE,USER_APPS_MODE,CHECKPOINT_MODE)
            and type(self.opened['opened_ns']) is int and self.opened['opened_ns']>0
            and self.opened['deadline_ns']==self.opened['opened_ns']+(CHECKPOINT_SECONDS if checkpoint else 900)*1_000_000_000
            and type(self.opened['operator_statement']) is str
            and 0<len(self.opened['operator_statement'].strip())<=4096,
            'Android-minimal open differs')
        self.task=read(verify(self.opened['task']))
        self.journal=Journal(self.directory/'journal',maximum=CHECKPOINT_JOURNAL_ROWS if checkpoint else 256)
        self.previous_cleanup=None;self.predecessors=[];self.effectful_predecessors=[]
        if successor:
            previous=self.opened['previous_cleanup']
            prior=private_path(self.root,Path(previous['open']['path']).parent)
            require(previous==closed_cleanup(self.root,prior,**(dict(user_apps=True) if checkpoint else dict(additional=user_apps)))
                and previous['task']==self.opened['task'] and previous['closed']==self.opened['closed']
                and (checkpoint or user_apps or not set(previous['removed'])&set(EXTRA_OPTIONAL)),
                'additional cleanup predecessor does not rederive')
            kind='checkpoint' if checkpoint else 'user-apps' if user_apps else 'additional'
            claim=pin(prior/(kind+'-cleanup-claim.json'))
            require(read(verify(claim))==dict(schema=SCHEMA+'-'+kind+'-claim',previous_cleanup=previous,
                task=self.opened['task'],closed=self.opened['closed'],open=self.open_pin),
                'additional cleanup claim differs')
            self.previous_cleanup=previous
            self.effectful_predecessors=[previous,*previous.get('effectful_ancestors',[])]
            self.claim_pins=[claim,*previous['claim_pins'],*(previous[key] for key in
                ('open','terminal','journal_tail','source_snapshot','final'))]
            self.predecessors=[Path(path) for path in previous['retired_preparations']]
        else:
            _,self.claim_pins,ancestors=claim_lineage(self.root,self.opened,self.open_pin)
            for parent,receipt in ancestors:
                require(read(verify(receipt))==inventory_no_effect_projection(self.root,parent),
                    'cleanup ancestor retirement differs')
                self.predecessors.append(parent)
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

    def checkpoint(self):
        return self.opened.get('mode')==CHECKPOINT_MODE

    def list_command(self):
        return [arg for arg in LIST if arg!='-s'] if self.checkpoint() else LIST

    def list_label(self):
        return 'installed-packages' if self.checkpoint() else 'system-packages'

    def attempted(self):
        return {name for old in self.effectful_predecessors for name in old['removed']}

    def declaration(self,listed=None):
        if self.checkpoint():
            if listed is None:
                listed=packages(raw.decode_success_stdout(raw.load_handle(
                    self.directory/'inventory'/(self.list_label()+'.capture.json')),maximum=131072))
            return tuple(sorted(set(listed)-self.keep_set()-self.attempted()))
        if self.opened.get('mode')==USER_APPS_MODE:
            return tuple(name for name in USER_APPS if name not in self.attempted())
        return EXTRA_OPTIONAL if self.opened.get('mode')==ADDITIONAL_MODE else OPTIONAL

    def keep_set(self):
        return KEEP-{'com.android.vending'} if self.opened.get('mode') in (USER_APPS_MODE,CHECKPOINT_MODE) else KEEP

    def require_checkpoint_keep(self,listed,home,ime):
        if self.checkpoint():
            # Root is proved independently. A manager APK already absent after
            # reset need not be installed merely to remove unrelated packages.
            required=(self.keep_set()-{'com.topjohnwu.magisk'})|{home,ime}
            require(required<=set(listed),'checkpoint inventory lacks a required package')

    def parse_metadata(self,text,row):
        return package_metadata(text,row,allow_enabled=self.opened.get('mode')==USER_APPS_MODE,
            checkpoint=self.checkpoint())

    def metadata_label(self,name):
        return metadata_label(name,checkpoint=self.checkpoint())

    def metadata_candidates(self,listed):
        if self.checkpoint():return list(self.declaration(listed))
        counts=Counter(row['uid'] for row in listed.values())
        return [name for name in self.declaration() if name in listed and
            (self.opened.get('mode') not in (ADDITIONAL_MODE,USER_APPS_MODE) or
             (not listed[name]['path'].startswith('/apex/') and listed[name]['uid']>=10000
              and counts[listed[name]['uid']]==1))]

    def safe_mode_projection(self,folder):
        if self.opened.get('mode') not in (ADDITIONAL_MODE,USER_APPS_MODE,CHECKPOINT_MODE):return {}
        value=raw.decode_success_stdout(raw.load_handle(Path(folder)/'safe-mode.capture.json'),maximum=16)
        require(value in ('','0'),'additional cleanup reports Android safe mode')
        return dict(safe_mode_property=value)

    def check(self,*,reserve=0):
        require(not (self.directory/'inventory-no-effect-close.json').exists(),'original inventory preparation is retired')
        for receipt in self.claim_pins:verify(receipt)
        for predecessor in self.predecessors:
            require(existing_empty_journal(self.root,predecessor),'retired preparation gained execution activity')
        for predecessor in self.effectful_predecessors:
            journal=Path(predecessor['open']['path']).parent/'journal'
            require(journal.is_dir() and len(Journal(journal).rows())==predecessor['journal_rows'],
                'previous effectful cleanup gained execution activity')
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
            listed=packages(self.text(folder,self.list_label(),self.list_command()))
            self.text(folder,'home',HOME);self.text(folder,'ime',IME)
            if self.opened.get('mode') in (ADDITIONAL_MODE,USER_APPS_MODE,CHECKPOINT_MODE):
                self.text(folder,'safe-mode',SAFE_MODE,maximum=16)
            self.text(folder,'storage-stat',
                ['shell','su -c '+shlex.quote(gpt_android.STAT_SCRIPT)],maximum=16384)
            for name in self.metadata_candidates(listed):
                self.text(folder/'packages',self.metadata_label(name),
                    ['shell','dumpsys','package',name],maximum=METADATA_MAXIMUM)
        finally:after=self.health(folder/'after')
        require(before['properties']==after['properties'],'Android boot changed during package inventory')
        return publish(folder/'result.json',self.inventory_raw_projection(folder))

    def inventory_raw_projection(self,folder=None):
        folder=Path(folder) if folder is not None else self.directory/'inventory'
        texts=lambda name:raw.decode_success_stdout(raw.load_handle(folder/(name+'.capture.json')),
            maximum=METADATA_MAXIMUM if name.startswith('packages/') else 131072)
        require(texts('current-user').strip()=='0','inventory primary user differs')
        listed=packages(texts(self.list_label()));home=component(texts('home'));ime=component(texts('ime'))
        self.require_checkpoint_keep(listed,home,ime)
        metadata={name:self.parse_metadata(texts('packages/'+self.metadata_label(name)),listed[name])
            for name in self.metadata_candidates(listed)}
        before=read(folder/'before/health.json');after=read(folder/'after/health.json')
        for health in (before,after):
            require(target.health_projection(health['captures'],self.task['target'],self.task['A'])==health,
                'inventory rooted health does not rederive')
        require(before['properties']==after['properties'],'inventory boot differs')
        return dict(schema=SCHEMA,selection=selection(listed,metadata,home,ime,declaration=self.declaration(listed),keep=self.keep_set(),checkpoint=self.checkpoint()),
            storage=gpt_android.storage_stat(texts('storage-stat'),self.basis,self.sealed),
            before=pin(folder/'before/health.json'),after=pin(folder/'after/health.json'),
            **self.safe_mode_projection(folder))

    def inventory_projection(self):
        value=self.inventory_raw_projection()
        require(read(self.directory/'inventory/result.json')==value,'cleanup manifest does not rederive from raw inventory')
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
            present=packages(self.text(folder,self.list_label(),self.list_command()))
            home=component(self.text(folder,'home',HOME));ime=component(self.text(folder,'ime',IME))
            if self.opened.get('mode') in (ADDITIONAL_MODE,USER_APPS_MODE,CHECKPOINT_MODE):
                self.text(folder,'safe-mode',SAFE_MODE,maximum=16)
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
        present=packages(text(self.list_label()));home=component(text('home'));ime=component(text('ime'))
        self.require_checkpoint_keep(present,home,ime)
        if self.opened.get('mode') in (ADDITIONAL_MODE,USER_APPS_MODE,CHECKPOINT_MODE):
            baseline=packages(raw.decode_success_stdout(raw.load_handle(
                self.directory/'inventory'/(self.list_label()+'.capture.json')),maximum=131072))
            require((set(baseline)&self.keep_set())<=set(present),'additional cleanup lost an initially present keep package')
        require((home,ime)==(plan['selection']['home'],plan['selection']['ime']),
            'snapshot required components differ')
        census.require_shell_v2(pin(folder/'gpt/shell-features.capture.json'))
        handle=raw.load_handle(folder/'gpt/metadata.capture.json');raw.require_success(handle)
        proof=gpt_android.metadata(raw.read_stdout(handle,maximum=65536),self.sealed,'proposed')
        storage=gpt_android.storage_stat(text('storage-stat'),self.basis,self.sealed)
        return dict(schema=SCHEMA,before=pin(folder/'before/health.json'),after=pin(folder/'after/health.json'),
            remaining=[row['name'] for row in plan['selection']['selected'] if row['name'] in present],
            home=home,ime=ime,gpt=proof,storage=storage,**self.safe_mode_projection(folder),
            **(dict(remaining_outside_keep=sorted(set(present)-self.keep_set()),
                package_scope='ALL_INSTALLED_USER_0_APKS') if self.checkpoint() else {}))

    def package_outcome(self,folder,row):
        folder=Path(folder);name=row['name']
        response=uninstall_response(raw.load_handle(folder/'uninstall.capture.json'),checkpoint=self.checkpoint())
        present=packages(raw.decode_success_stdout(raw.load_handle(folder/'after-package.capture.json'),maximum=131072))
        if not self.checkpoint():
            require(response=='SUCCESS' and name not in present,'uninstall raw result or post-state differs')
            return 'REMOVED'
        if name in present:
            require(present[name]=={key:row[key] for key in ('name','path','uid','version')},
                'remaining package identity changed during uninstall')
            return 'RETAINED_AFTER_SUCCESS' if response=='SUCCESS' else response
        require(response=='SUCCESS','refused uninstall has an unexpected absent post-state')
        return 'REMOVED'

    def completed_effects_projection(self,*,final_name='final',allow_remaining=False):
        """H0 effect and changed-boot proof; never changes a terminal verdict."""
        require(final_name in ('final','reconciliation'),'unsupported final snapshot')
        plan=self.inventory_projection();rows=self.journal.rows()
        names=[row['name'] for row in plan['selection']['selected']]
        require(names,'completed cleanup has no selected effects')
        intents=[r['data'] for r in rows if r['event']=='intent']
        require([r['key'] for r in intents]==names+['reboot'],'cleanup effect sequence is incomplete')
        initial=read(verify(plan['after']))
        for number,row in enumerate(plan['selection']['selected']):
            folder=self.directory/f'package-{number:03d}';name=row['name'];intent=intents[number]
            require(intent==dict(key=name,kind='uninstall',detail=dict(package=name,metadata=row)),
                'package intent does not join selected manifest')
            text=lambda label:raw.decode_success_stdout(raw.load_handle(folder/(label+'.capture.json')),
                maximum=METADATA_MAXIMUM if label=='before-metadata' else 131072)
            require(text('devpath').strip()==self.task['target']['topology']
                and text('current-user').strip()=='0'
                and target.fields(text('properties'),target.PROPERTY_FIELDS)==initial['properties'],
                'uninstall lacks its same-boot physical target binding')
            current=packages(text('before-package'))
            require(name in current and self.parse_metadata(text('before-metadata'),current[name])==row,
                'uninstall pre-effect metadata differs')
            self.package_outcome(folder,row)
        before=self.snapshot_projection(self.directory/'before-reboot',plan)
        after=self.snapshot_projection(self.directory/final_name,plan)
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
            and (self.checkpoint() or not before['remaining']) and (allow_remaining or not after['remaining']),
            'cleanup reboot persistence is unproved')
        return plan,names,before,after

    def completed_journal(self,names):
        rows=self.journal.rows();events=['started']+['intent','complete']*(len(names)+1)
        require([row['event'] for row in rows] in (events,events+['stopped'])
            and rows[0]['data']==dict(inventory=pin(self.directory/'inventory/result.json')),
            'previous cleanup has pending or unexplained execution activity')
        complete=[row['data'] for row in rows if row['event']=='complete']
        expected=[dict(key=name,capture=pin(self.directory/f'package-{i:03d}'/'uninstall.capture.json'),
            post_state=pin(self.directory/f'package-{i:03d}'/'after-package.capture.json')) for i,name in enumerate(names)]
        expected.append(dict(key='reboot',capture=pin(self.directory/'reboot/reboot.capture.json'),
            departure=pin(self.directory/'reboot/departure.json')))
        require(complete==expected,'previous cleanup completion receipts differ')
        return rows,events

    def retained_partial_projection(self):
        require(self.opened.get('mode')==USER_APPS_MODE,'retained partial close is user-apps only')
        plan,names,before,after=self.completed_effects_projection(allow_remaining=True)
        rows,events=self.completed_journal(names)
        require([row['event'] for row in rows]==events+['stopped'] and after['remaining'],
            'retained partial close requires a completed-effect persistence stop')
        for name,value in (('before-reboot',before),('final',after)):
            require(read(self.directory/name/'result.json')==value,'retained partial aggregate differs')
        require_expected_packages(self,self.directory/'final',names,after['remaining'])
        return dict(schema=SCHEMA,status='INCOMPLETE',terminal_state='ANDROID_CLOSED_HEALTHY',
            final=pin(self.directory/'final/result.json'),remaining=after['remaining'],
            cleanup_replay_permitted=False,reboot_verified=False,source_snapshot=self.opened['source_snapshot'])

    def terminal_projection(self):
        """H0 rederivation of all selected effects, departure and final raw health."""
        plan=self.inventory_projection()
        if not plan['selection']['selected']:
            require(not self.journal.rows(),'empty cleanup unexpectedly has journal actions')
            residual={}
            if self.checkpoint():
                present=packages(raw.decode_success_stdout(raw.load_handle(
                    self.directory/'inventory'/(self.list_label()+'.capture.json')),maximum=131072))
                outside=sorted(set(present)-self.keep_set())
                residual=dict(remaining_outside_keep=outside,checkpoint_reached=not outside,
                    package_scope='ALL_INSTALLED_USER_0_APKS',completion_scope='NEW_CHECKPOINT_CANDIDATES_ONLY')
            return dict(schema=SCHEMA,status='NO_CHANGES_NEEDED',
                terminal_state='ANDROID_CLOSED_HEALTHY',inventory=pin(self.directory/'inventory/result.json'),
                final_health=plan['after'],removed_count=0,reboot_verified=False,
                source_snapshot=self.opened['source_snapshot'],**residual)
        plan,names,before,after=self.completed_effects_projection(allow_remaining=self.checkpoint())
        if self.checkpoint():
            self.completed_journal(names)
            require_expected_packages(self,self.directory/'final',names,after['remaining'])
        for name,value in (('before-reboot',before),('final',after)):
            path=self.directory/name/'result.json'
            if path.exists():require(read(path)==value,'snapshot aggregate differs')
            else:publish(path,value)
        if self.checkpoint():
            outcomes={row['name']:self.package_outcome(self.directory/f'package-{i:03d}',row)
                for i,row in enumerate(plan['selection']['selected'])}
            return dict(schema=SCHEMA,status='INCOMPLETE' if after['remaining'] else 'COMPLETE',
                terminal_state='ANDROID_CLOSED_HEALTHY',inventory=pin(self.directory/'inventory/result.json'),
                before_reboot=pin(self.directory/'before-reboot/result.json'),final=pin(self.directory/'final/result.json'),
                attempted_count=len(names),removed_count=len(names)-len(after['remaining']),remaining=after['remaining'],
                package_outcomes=outcomes,cleanup_replay_permitted=False,reboot_verified=not after['remaining'],
                remaining_outside_keep=after['remaining_outside_keep'],
                package_scope='ALL_INSTALLED_USER_0_APKS',
                checkpoint_reached=not after['remaining_outside_keep'],completion_scope='NEW_CHECKPOINT_CANDIDATES_ONLY',
                observed_available_bytes_change=after['storage']['available_bytes']-plan['storage']['available_bytes'],
                source_snapshot=self.opened['source_snapshot'])
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
            require(2*(len(plan['selection']['selected'])+1)+2<=self.journal.maximum,
                'selected cleanup plan exceeds complete journal capacity')
            self.journal.append('started',inventory=pin(self.directory/'inventory/result.json'))
            try:
                for number,row in enumerate(plan['selection']['selected']):
                    folder=self.directory/f'package-{number:03d}';name=row['name']
                    self.same_boot(folder,initial)
                    current=packages(self.text(folder,'before-package',[*self.list_command(),name]))
                    require(name in current and self.parse_metadata(self.text(folder,'before-metadata',
                        ['shell','dumpsys','package',name],maximum=METADATA_MAXIMUM),current[name])==row,
                        'selected package changed before intent')
                    self.command(folder,'uninstall',['shell','pm','uninstall','--user','0',
                        '--versionCode',str(row['version']),name],
                        maximum=16384,before=lambda:self.intent('uninstall',package=name,metadata=row))
                    # An unknown command result stops before another connected read.
                    uninstall_response(raw.load_handle(folder/'uninstall.capture.json'),checkpoint=self.checkpoint())
                    self.text(folder,'after-package',[*self.list_command(),name])
                    self.package_outcome(folder,row)
                    self.journal.append('complete',key=name,capture=pin(folder/'uninstall.capture.json'),
                        post_state=pin(folder/'after-package.capture.json'))
                before=self.snapshot(self.directory/'before-reboot',plan)
                require(self.checkpoint() or not before['remaining'],'selected optional packages remain installed')
                if self.checkpoint():
                    require_expected_packages(self,self.directory/'before-reboot',
                        [row['name'] for row in plan['selection']['selected']],before['remaining'])
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
                    and before['storage']['total_bytes']==after['storage']['total_bytes']
                    and (self.checkpoint() or not after['remaining']),
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
            if value is None and self.opened.get('mode')==USER_APPS_MODE:
                try:value=self.retained_partial_projection()
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
                source_snapshot=self.opened['source_snapshot'],
                **(dict(remaining_outside_keep=value['remaining_outside_keep'],checkpoint_reached=False,
                    package_scope='ALL_INSTALLED_USER_0_APKS',
                    completion_scope='NEW_CHECKPOINT_CANDIDATES_ONLY') if self.checkpoint() else {})))


def require_expected_packages(run,final_folder,names,remaining):
    initial=packages(raw.decode_success_stdout(raw.load_handle(
        run.directory/'inventory'/(run.list_label()+'.capture.json')),maximum=131072))
    present=packages(raw.decode_success_stdout(raw.load_handle(
        Path(final_folder)/(run.list_label()+'.capture.json')),maximum=131072))
    require(set(initial)-set(present)==set(names)-set(remaining)
        and not (set(present)-set(initial)) and (set(initial)&run.keep_set())<=set(present),
        'previous cleanup package changes or preserved components differ')


def closed_cleanup(root,directory,*,additional=False,user_apps=False):
    """Prove prior effects closed without relabelling its terminal or replaying I/O."""
    directory=private_path(root,directory)
    require((directory/'journal').is_dir(),'previous cleanup journal is missing')
    require(not (additional and user_apps) and read(directory/'open.json')['mode']==
        (USER_APPS_MODE if user_apps else ADDITIONAL_MODE if additional else 'minimal-management'),
        'additional cleanup requires the original management profile')
    run=Run(root,directory);terminal=read(directory/'terminal.json')
    require(terminal['status'] in ('COMPLETE','INCOMPLETE'),
        'previous cleanup has no effectful closed terminal')
    final_name='reconciliation' if terminal['status']=='INCOMPLETE' and not additional else 'final'
    plan,names,before,after=run.completed_effects_projection(final_name=final_name,allow_remaining=additional or user_apps)
    require(read(directory/'before-reboot/result.json')==before
        and read(directory/final_name/'result.json')==after,'previous cleanup snapshot aggregate differs')
    rows,events=run.completed_journal(names)
    require_expected_packages(run,directory/final_name,names,after['remaining'])
    if terminal['status']=='INCOMPLETE' and additional:
        closure=terminal.get('closure_projection',{})
        require(closure.get('sha256')==ADDITIONAL_RETAINED_CLOSE_SHA256,
            'additional predecessor has no qualified retained closure')
        private_path(root,verify(closure))
        require(terminal==dict(schema=SCHEMA,status='INCOMPLETE',terminal_state='ANDROID_CLOSED_HEALTHY',
            final=pin(directory/'final/result.json'),remaining=after['remaining'],cleanup_replay_permitted=False,
            reboot_verified=False,source_snapshot=run.opened['source_snapshot'],closure_projection=closure)
            and after['remaining'] and [row['event'] for row in rows]==events+['stopped']
            and not (directory/'reconcile.json').exists(),
            'additional predecessor partial closure differs')
    elif terminal['status']=='INCOMPLETE' and user_apps:
        require(terminal==dict(schema=SCHEMA,status='INCOMPLETE',terminal_state='ANDROID_CLOSED_HEALTHY',
            final=pin(directory/'reconciliation/result.json'),remaining=after['remaining'],cleanup_replay_permitted=False,
            reboot_verified=False,source_snapshot=run.opened['source_snapshot']),
            'user-app predecessor read-only terminal differs')
        reconciliation=read(directory/'reconcile.json')
        require(reconciliation==dict(open=run.open_pin,opened_ns=reconciliation['opened_ns'],
            deadline_ns=reconciliation['opened_ns']+300_000_000_000,read_only=True)
            and [row['event'] for row in rows]==events+['stopped']
            and rows[-1]['data']==dict(error_type='RawCaptureError'),
            'user-app predecessor does not close a read-only readiness failure')
        qualified_readiness_stop(run)
    elif terminal['status']=='INCOMPLETE':
        require(terminal==dict(schema=SCHEMA,status='INCOMPLETE',terminal_state='ANDROID_CLOSED_HEALTHY',
            final=pin(directory/'reconciliation/result.json'),remaining=[],cleanup_replay_permitted=False,
            reboot_verified=False,source_snapshot=run.opened['source_snapshot']),
            'previous read-only reconciliation terminal differs')
        reconciliation=read(directory/'reconcile.json')
        require(reconciliation['open']==run.open_pin and reconciliation['read_only'] is True
            and reconciliation['deadline_ns']==reconciliation['opened_ns']+300_000_000_000
            and [row['event'] for row in rows]==events+['stopped'],
            'previous reconciliation does not close the stopped execution')
        text=lambda label:raw.decode_success_stdout(raw.load_handle(
            directory/'final/before'/(label+'.capture.json')),maximum=16384)
        target.select_android(text('00-health'),run.task['target'])
        require(text('01-health')==run.task['target']['topology']
            and target.fields(text('02-health'),target.PROPERTY_FIELDS)==read(verify(after['after']))['properties']
            and text('03-health')=='' and text('04-health')=='List of devices attached',
            'previous stop is not the qualified same-boot transport disappearance')
    else:
        require(terminal==run.terminal_projection(),'previous complete terminal does not rederive')
    return dict(schema=SCHEMA+'-closed-predecessor',open=run.open_pin,task=run.opened['task'],
        closed=run.opened['closed'],terminal=pin(directory/'terminal.json'),
        journal_rows=len(rows),journal_tail=pin(directory/'journal'/f'{len(rows)-1:04d}.json'),
        source_snapshot=run.opened['source_snapshot'],final=pin(directory/final_name/'result.json'),
        removed=names,claim_pins=run.claim_pins,
        retired_preparations=[str(path) for path in run.predecessors],
        **(dict(effectful_ancestors=run.effectful_predecessors) if additional or user_apps else {}))


def prepare(root,task_path,output,*,operator_statement,attended,replace_inventory=None,after_cleanup=None,after_additional=None,after_user_apps=None):
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
        replacement=None;previous=None
        require(sum(value is not None for value in (replace_inventory,after_cleanup,after_additional,after_user_apps))<=1,
            'cleanup preparation modes are mutually exclusive')
        user_apps=after_additional is not None
        checkpoint=after_user_apps is not None
        if after_cleanup is not None or user_apps or checkpoint:
            require(replace_inventory is None,'additional cleanup cannot replace an old inventory')
            previous=closed_cleanup(root,after_user_apps if checkpoint else after_additional if user_apps else after_cleanup,
                **(dict(user_apps=True) if checkpoint else dict(additional=user_apps)))
            require(previous['task']==pin(task_path) and previous['closed']==closed
                and (checkpoint or user_apps or not set(previous['removed'])&set(EXTRA_OPTIONAL)),
                'additional declaration overlaps prior effects or changes the closed task')
            kind='checkpoint' if checkpoint else 'user-apps' if user_apps else 'additional'
            claim_path=Path(previous['open']['path']).parent/(kind+'-cleanup-claim.json')
            require(not claim_path.exists(),'this cleanup already has its one additional claim')
            replacement=dict(schema=SCHEMA+'-'+kind+'-claim',previous_cleanup=previous,
                task=pin(task_path),closed=closed)
        elif replace_inventory is None:
            require(not claim_path.exists(),'this closed G2 task already has a cleanup claim; use its reconciliation')
        else:
            retired_pin=pin(private_path(root,replace_inventory));retired=read(verify(retired_pin))
            original=Path(retired['open']['path']).parent
            require(Path(retired_pin['path'])==original/'inventory-no-effect-close.json'
                and retired==inventory_no_effect_projection(root,original),
                'replacement has no exact no-effect inventory retirement')
            old=read(verify(retired['open']))
            require(old['task']==pin(task_path) and old['closed']==closed
                and old['host_boot']==host_boot() and old['operator_statement']==operator_statement,
                'replacement changed the closed task, host or original foreground request')
            parent_claim,_,_=claim_lineage(root,old,retired['open'])
            require(retired['claim']==parent_claim,'retirement claim differs')
            replacement=dict(schema=SCHEMA+'-inventory-replacement-claim',original_claim=parent_claim,
                retired_inventory=retired_pin,task=pin(task_path),closed=closed)
            claim_path=child_claim_path(parent_claim)
            require(not claim_path.exists(),'the one inventory replacement is already claimed')
        output.mkdir(mode=0o700)
        snapshot=census.snapshot_current(root,output/'source-snapshot',qualified)
        now=clock();opened=publish(output/'open.json',dict(schema=SCHEMA,
            mode=CHECKPOINT_MODE if checkpoint else USER_APPS_MODE if user_apps else ADDITIONAL_MODE if previous is not None else 'minimal-management',task=pin(task_path),
            closed=closed,review=qualified,operator_statement=operator_statement,host_boot=host_boot(),
            opened_ns=now,deadline_ns=now+(CHECKPOINT_SECONDS if checkpoint else 900)*1_000_000_000,source_snapshot=snapshot,
            **(dict(previous_cleanup=previous) if previous is not None else {})))
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
    p.add_argument('--after-cleanup',type=Path)
    p.add_argument('--after-additional',type=Path)
    p.add_argument('--after-user-apps',type=Path)
    p=sub.add_parser('execute');p.add_argument('directory',type=Path);p.add_argument('--attended',action='store_true')
    p=sub.add_parser('reconcile');p.add_argument('directory',type=Path)
    p=sub.add_parser('retire-inventory');p.add_argument('directory',type=Path)
    args=parser.parse_args()
    if args.action=='prepare':print(prepare(args.root,args.task,args.output,
        operator_statement=args.operator_statement,attended=args.attended,replace_inventory=args.replace_inventory,
        after_cleanup=args.after_cleanup,after_additional=args.after_additional,after_user_apps=args.after_user_apps))
    elif args.action=='execute':print(Run(args.root,args.directory).execute(attended=args.attended))
    elif args.action=='retire-inventory':print(retire_inventory(args.root,args.directory))
    else:print(Run(args.root,args.directory).reconcile())
