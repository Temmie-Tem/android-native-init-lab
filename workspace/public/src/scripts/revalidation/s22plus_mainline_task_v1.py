"""One attended mainline RAM/USB candidate, using the existing V3 owner."""
import argparse
import os
from pathlib import Path
import re
import shutil
import socket
import uuid

import consumed_candidate_registry_v1 as registry
import s22plus_mainline_profile_v1 as profile
import s22plus_mainline_access_v1 as access
import s22plus_native_target_io_v3 as target
import s22plus_native_task_v3 as tasks
from s22plus_native_records_v3 import SCHEMA,Journal,canonical,clock,digest,host_boot,pin,private_path,publish,read,read_bytes,require,verify

# Selected mainline/Android/transport branches only. The shared modules also
# contain vendor-native operations which this exact task cannot select.
MODULES=('s22plus_mainline_task_v1','s22plus_mainline_profile_v1','s22plus_mainline_access_v1',
    's22plus_mainline_retention_v1',
    's22plus_native_android_storage_v1',
    's22plus_mainline_session_v1','s22plus_native_task_v3','s22plus_native_session_v3',
    's22plus_native_adapter_v3','s22plus_native_qualification_v1','s22plus_native_records_v3','s22plus_native_target_io_v3',
    's22plus_native_host_v3','s22plus_native_host_census_v1','s22plus_debian_handoff_session_v1',
    's22plus_boot_only_f1_transport','s22plus_boot_verify','s22plus_boot_only_live_core',
    's22plus_odin_transition_core','s22plus_odin_usbfs_identity','s22plus_fyg8_p324_typec_lane_binding',
    'consumed_candidate_registry_v1','device_action_raw_capture_v1','device_action_read_dependencies_v1')


def selected_profile(image):
    if image.get('profile')==profile.PROFILE:return profile
    if image.get('profile')=='loader-android-v1':
        import s22plus_loader_android_profile_v1 as selected
        return selected
    require(False,'unselected mainline-project comparison profile')


def source_paths(root,selected=profile):
    root=Path(root)
    paths=['workspace/public/src/scripts/revalidation/'+name+'.py' for name in MODULES]
    paths+=['workspace/public/src/scripts/analysis/s22plus_fyg8_p319_max77705_irq_dt_audit.py','AGENTS.md',tasks.DETAILS,tasks.TARGET_CONTRACT,profile.POLICY,tasks.PROFILE,
        'docs/operations/DEVICE_ACTION_PROCESS_V2.md','docs/operations/DEVICE_ACTION_RISK_TIERS.md',
        'workspace/public/src/mainline/s22plus_canary_h0/verify.py',
        'workspace/public/src/mainline/s22plus_canary_h0/debian_ram.py',
        'workspace/public/src/mainline/s22plus_canary_h0/prepare.py',
        'workspace/public/src/mainline/s22plus_canary_h0/retained_marker.py',
        'workspace/public/src/mainline/s22plus_canary_h0/retained_trace.py',
        'workspace/public/src/mainline/s22plus_canary_h0/retained_probe.py',
        'workspace/public/src/mainline/s22plus_canary_h0/retained_probe_v10.py',
        'workspace/public/src/scripts/analysis/s22plus_native_artifact_v3_h0.py',
        'workspace/public/src/scripts/revalidation/device_action_f1_legacy_consumed_candidate_authority_v1.json']
    if selected is not profile:
        require(selected.PROFILE=='loader-android-v1','unselected source closure')
        paths += [selected.POLICY,
            'workspace/public/src/scripts/revalidation/s22plus_loader_android_profile_v1.py',
            'workspace/public/src/scripts/revalidation/s22plus_loader_android_access_v1.py',
            'workspace/public/src/scripts/revalidation/s22plus_loader_prefix_v1.py',
            'workspace/public/src/scripts/revalidation/s22plus_loader_android_session_v1.py']
        paths += ['workspace/public/src/mainline/s22plus_loader_android_h0/'+name for name in
                  ('build.py','guard.c','logm-control.c','logm-layout.h','prefix-control.c','prefix-entry.S',
                   'prefix_image.py','prefix_qualify.py','uniloader-android.patch','qualify.py','entry_vm.py')]
        paths += ['workspace/public/src/mainline/s22plus_canary_h0/'+name for name in
                  ('build_loader.py','build_kernel.py','prepare_marked.py','retained-marker.S',
                   'package_loader.py','qualify_loader.py','uniloader-g0q-entry.patch','sources.json')]
    return tuple(root/path for path in sorted(set(paths)))


def source_pins(root,selected=profile):
    root=Path(root)
    return [dict(pin(path),path=str(path.relative_to(root))) for path in source_paths(root,selected)]


def loader_build_only(path):
    return (path.startswith('workspace/public/src/mainline/s22plus_loader_android_h0/') or
        path in {'workspace/public/src/mainline/s22plus_canary_h0/'+name for name in
            ('build_loader.py','build_kernel.py','prepare_marked.py','retained-marker.S',
             'package_loader.py','qualify_loader.py','uniloader-g0q-entry.patch','sources.json')})


def marker_only(path):
    # Marker observation runs only after proved original-A closure. Marker
    # decoding and Debian candidate validation are lazy imports, unavailable
    # candidate-only code must not become a prerequisite for original A.
    return path in ('workspace/public/src/mainline/s22plus_canary_h0/retained_marker.py',
                    'workspace/public/src/mainline/s22plus_canary_h0/debian_ram.py',
                    'workspace/public/src/mainline/s22plus_canary_h0/retained_trace.py',
                    'workspace/public/src/mainline/s22plus_canary_h0/retained_probe.py',
                    'workspace/public/src/mainline/s22plus_canary_h0/retained_probe_v10.py',
                    'workspace/public/src/scripts/revalidation/s22plus_mainline_retention_v1.py',
                    'workspace/public/src/scripts/revalidation/s22plus_native_android_storage_v1.py')


def capability(root,*,recovery=False,selected=profile):
    root=Path(root);path=root/selected.REVIEW;value=read(path)
    require(set(value)=={'schema','verdict','scope','sources','reviewer','findings'} and
        value['schema']==selected.REVIEW_SCHEMA and value['verdict']=='PASS_GO' and
        value['scope']==selected.REVIEW_SCOPE and value['findings']==[] and
        type(value['reviewer']) is str and value['reviewer'].strip(),'mainline independent review is not PASS_GO')
    expected=[str(path.relative_to(root)) for path in source_paths(root,selected)]
    require([r['path'] for r in value['sources']]==expected,'mainline review source closure differs')
    for row in value['sources']:
        # Loader comparison recovery neither rebuilds nor requalifies N. Keep
        # only its actually imported owner/observer/transport/authority closure
        # mandatory after a stop; candidate build/checker files are not A inputs.
        if recovery and (marker_only(row['path']) or selected is not profile and loader_build_only(row['path'])):continue
        tasks.unchanged(dict(row,path=str(root/row['path'])))
    return pin(path)


def validate_access(plan):
    require(set(plan)=={'uuid','name','nmcli','ip'} and str(uuid.UUID(plan['uuid']))==plan['uuid'] and
        plan['name']=='s22plus-mainline-'+plan['uuid'],'mainline host network ownership differs')
    for name,path in [('nmcli','/usr/bin/nmcli'),('ip','/usr/sbin/ip')]:
        require(plan[name]['path']==str(Path(path).resolve(strict=True)),'host executable path differs')
        tasks.unchanged(plan[name],maximum=32*1024*1024)


def validate_task(root,task,*,live=False,recovery=False,require_android=True):
    root=Path(root)
    selected=selected_profile(task.get('N',{}))
    keys={'schema','target','lane','N','E','A','adb','odin','host_installation','review','recovery_evidence',
        'operations','seconds','operation_budget','recovery_mode','reentry','hud','usb_reconnect',
        'admission','prior_terminal','runtime_scope'}|({'mainline_access'} if selected is profile else set())
    require(set(task)==keys and task['schema']==selected.TASK_SCHEMA and
        task['operations']==[selected.OPERATION] and type(task['seconds']) is int and task['seconds']==selected.SECONDS and
        type(task['operation_budget']) is int and task['operation_budget']==1 and task['recovery_mode']=='attended' and
        all(task[k] is False for k in ('reentry','hud','usb_reconnect')) and
        all(task[k] is None for k in ('E','admission','prior_terminal')) and task['N']['profile']==selected.PROFILE,
        'mainline task exceeds one attended Android-origin operation')
    require(set(task['target'])=={'serial','topology'} and
        re.fullmatch('[A-Za-z0-9._:-]{1,128}',task['target']['serial']) and
        task['target']['topology']==target.lane.SOURCE_TOPOLOGY,'mainline target binding differs')
    target.lane.validate_binding(task['lane'],source_topology=target.lane.SOURCE_TOPOLOGY)
    require(task['review']==capability(root,recovery=recovery,selected=selected),'mainline capability changed')
    require(task['runtime_scope']==task['N']['runtime_sources'],'mainline runtime scope differs')
    if not recovery:
        selected.image_binding(task['N'])
        if selected is profile:validate_access(task['mainline_access'])
    fixed=read(root/tasks.PROFILE)
    require(task['odin']==fixed['transport']['odin'] and
        task['adb']['path']==str(Path('/usr/bin/adb').resolve(strict=True)) and
        task['A']['ap']==dict(fixed['rollback']['ap'],path=str(root/fixed['rollback']['ap']['path'])) and
        task['A']['partition_sha256']==dict(boot=fixed['start_health']['boot_sha256'],
            **fixed['start_health']['supporting_partition_sha256']),'original Android/tool binding differs')
    installation=read(verify(task['host_installation']))
    require(installation['uid']==os.getuid() and
        installation['topology']==target.lane.CANDIDATE_TOPOLOGY.removeprefix('usb:'),'host account/port differs')
    if require_android:
        tasks.unchanged(task['A']['ap'],maximum=128*1024*1024)
        tasks.validate_recovery(task['recovery_evidence'],task['target'],task['A'])
    if live:
        details=read_bytes(root/tasks.DETAILS)
        require(digest(details).encode() in read_bytes(root/'AGENTS.md') and
            Path(selected.POLICY).name.encode() in read_bytes(root/tasks.TARGET_CONTRACT) and
            b'Status: **REVIEW_GATED_CAPABILITY**' in read_bytes(root/selected.POLICY),
            'mainline target adoption or common detail pin differs')
    return task


def validate_operation(adapter,request,*,recovery=False):
    task=adapter.configuration(request)
    selected=selected_profile(task['N'])
    completed=adapter.android_transfer_completed(request)
    validate_task(adapter.root,task,live=True,recovery=recovery or completed,require_android=not completed)
    grant_path=verify(request['grant']);grant=read(grant_path);tasks.validate_grant(task,grant,grant_path)
    expected=dict(schema=SCHEMA,operation=selected.OPERATION,reentry=False,hud=False,grant=request['grant'],
        task=grant['task'],N=task['N'],E=None,A=task['A'],admission=None,prior_terminal=None,usb_reconnect=False)
    require(request==expected,'mainline operation differs from its original finite task')


def host_ready(task,folder):
    if selected_profile(task['N']) is not profile:return None
    plan=task['mainline_access'];validate_access(plan)
    value=access.host_command(plan,'nmcli',['--terse','general','permissions'],folder,'permissions')
    access.require_host(value)
    permissions=dict(line.rsplit(':',1) for line in access.raw.decode_success_stdout(value,maximum=262144).splitlines())
    require(all(permissions.get('org.freedesktop.NetworkManager.'+name)=='yes'
        for name in ('network-control','settings.modify.system')),'noninteractive network authority absent')
    manifest=profile.image_binding(task['N'])
    addresses=access.host_command(plan,'ip',['-j','address','show'],folder,'preflight-addresses')
    access.network_conflicts(addresses,manifest)
    with socket.socket() as client:client.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,b'lo\0')
    return pin(value.receipt_path)


def preflight(adapter,request,guard):
    from s22plus_native_adapter_v3 import image_identity
    guard();task=adapter.configuration(request)
    selected_profile(task['N']).image_binding(task['N'],artifact_bytes=True)
    with adapter.original_android(request):pass
    registry.preflight_candidate(adapter.root,image_identity(request['N'],pin(adapter.directory/'operation.json')['sha256']))
    target.lane.revalidate_binding(task['lane'],source_topology=target.lane.SOURCE_TOPOLOGY)
    adapter.native_host(request).holders()
    folder=adapter.folder('preflight',create=True)
    ready=host_ready(task,folder)
    adapter.android(request,folder,guard).health()
    publish(folder/'complete.json',dict(task=request['task'],host_configuration_verified=True,
        network_permissions=ready,health=pin(folder/'health.json')))


def readiness(root,task_path):
    """Named foreground D0: fresh fixed Android health, no control or payload."""
    from s22plus_native_host_v3 import NativeHost
    root=Path(root).resolve(strict=True);task_path=private_path(root,task_path)
    receipt=pin(task_path);task=read(task_path)
    with registry.target_session_lease(root):
        registry.require_no_f1_owner(root);validate_task(root,task,live=True)
        require(not (task_path.parent/'grant.json').exists(),'task already has a grant')
        folder=task_path.parent/('ready-'+uuid.uuid4().hex);folder.mkdir(mode=0o700)
        journal=Journal(task_path.parent/'journal')
        journal.append('readiness-start',task=receipt,directory=str(folder))
        def guard():
            require(pin(task_path)==receipt,'preapproval task changed')
            validate_task(root,task,live=True);registry.require_no_f1_owner(root)
        guard();target.lane.revalidate_binding(task['lane'],source_topology=target.lane.SOURCE_TOPOLOGY)
        NativeHost(read(verify(task['host_installation'])),folder/'host').holders()
        network=host_ready(task,folder)
        from s22plus_native_adapter_v3 import image_identity
        registry.preflight_candidate(root,image_identity(task['N'],receipt['sha256']))
        target.Android(task['adb'],task['target'],task['A'],folder,guard=guard).health()
        guard()
        result=publish(folder/'ready.json',dict(schema='s22plus-mainline-ready-v1',task=receipt,
            host_boot=host_boot(),observed_ns=clock(),health=pin(folder/'health.json'),
            network_permissions=network,device_controls=0,partition_transfers=0))
        journal.append('readiness-complete',result=result)
        return result


def validate_readiness(task,receipt,task_receipt,*,fresh):
    value=read(verify(receipt))
    require(set(value)=={'schema','task','host_boot','observed_ns','health','network_permissions',
        'device_controls','partition_transfers'} and value['schema']=='s22plus-mainline-ready-v1' and
        value['task']==task_receipt and
        value['device_controls']==value['partition_transfers']==0,'preapproval readiness differs')
    require(Path(receipt['path']).parent.parent==Path(task_receipt['path']).parent,'readiness belongs elsewhere')
    if fresh:require(value['host_boot']==host_boot() and
        0<=clock()-value['observed_ns']<=300_000_000_000,'preapproval health is stale or from another host boot')
    health=read(verify(value['health']))
    require(target.health_projection(health['captures'],task['target'],task['A'])==health,'preapproval raw health differs')
    if selected_profile(task['N']) is profile:
        access.raw.require_success(access.raw.load_handle(verify(value['network_permissions'])))
    else:require(value['network_permissions'] is None,'loader comparison has no network setup')
    rows=Journal(Path(task_receipt['path']).parent/'journal').rows()
    require(any(r['event']=='readiness-complete' and r['data']['result']==receipt for r in rows),
        'readiness lacks its preapproval durable journal')
    return value


def open_grant(root,task_path,*,returned_approval,operator_statement):
    root=Path(root).resolve(strict=True);task_path=private_path(root,task_path)
    receipt=pin(task_path);task=read(task_path);validate_task(root,task,live=True)
    require(returned_approval==tasks.approval_text(task,receipt) and type(operator_statement) is str and
        0<len(operator_statement.strip())<=4096,'actual returned operator task grant is required')
    with registry.target_session_lease(root):
        registry.require_no_f1_owner(root)
        rows=Journal(task_path.parent/'journal').rows()
        require(rows and rows[-1]['event']=='readiness-complete','latest preapproval observation did not finish')
        ready=rows[-1]['data']['result'];validate_readiness(task,ready,receipt,fresh=True)
        now=clock()
        return publish(task_path.parent/'grant.json',dict(schema=SCHEMA,task=receipt,directory=str(task_path.parent),
            host_boot=host_boot(),opened_ns=now,deadline_ns=now+task['seconds']*1_000_000_000,
            operation_budget=1,recovery_mode='attended',operator_statement=operator_statement,
            returned_approval=returned_approval,preapproval=ready))


def prepare(root,output,image,retained_task):
    """H0: reuse target/recovery provenance; live checks occur in the owner."""
    root=Path(root).resolve(strict=True);output=private_path(root,output,exists=False)
    previous=read(private_path(root,retained_task));image=read(private_path(root,image))
    selected_profile_value=selected_profile(image)
    require(not output.exists(),'fresh mainline task directory required')
    selected_profile_value.image_binding(image,artifact_bytes=True)
    selected={k:previous[k] for k in ('target','lane','host_installation','recovery_evidence')}
    ident=str(uuid.uuid4())
    task=dict(selected,schema=selected_profile_value.TASK_SCHEMA,N=image,E=None,A=tasks.android_artifact(root),
        adb=pin(Path('/usr/bin/adb').resolve(strict=True),maximum=32*1024*1024),
        odin=read(root/tasks.PROFILE)['transport']['odin'],review=capability(root,selected=selected_profile_value),
        operations=[selected_profile_value.OPERATION],seconds=selected_profile_value.SECONDS,
        operation_budget=1,recovery_mode='attended',reentry=False,hud=False,
        usb_reconnect=False,admission=None,prior_terminal=None,runtime_scope=image['runtime_sources'])
    if selected_profile_value is profile:
        task['mainline_access']=dict(uuid=ident,name='s22plus-mainline-'+ident,
            nmcli=pin(Path('/usr/bin/nmcli').resolve(strict=True)),ip=pin(Path('/usr/sbin/ip').resolve(strict=True)))
    validate_task(root,task)
    output.mkdir(mode=0o700);Journal(output/'journal');receipt=publish(output/'task.json',task)
    # Source provenance is ordinary private preparation output, not a new
    # authority gate. Preserve the bytes named by the review before effects.
    snapshot=[]
    for source in (*source_paths(root,selected_profile_value),root/selected_profile_value.REVIEW):
        destination=output/'source-snapshot'/source.relative_to(root)
        destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        shutil.copyfile(source,destination);os.chmod(destination,0o400)
        original=pin(source);retained=pin(destination)
        require(all(original[k]==retained[k] for k in ('size','sha256')),'source snapshot changed during copy')
        snapshot.append(dict(original=original,retained=retained))
    publish(output/'source-snapshot.json',dict(task=receipt,review=task['review'],sources=snapshot))
    publish(output/'proposal.json',dict(task=receipt,approval=tasks.approval_text(task,receipt),
        grants_device_authority=False,device_actions=0))
    return receipt


def close_task(root,task_path):
    """H0-only rederivation/publication after exact original-A health."""
    from s22plus_native_adapter_v3 import Adapter
    from s22plus_native_session_v3 import Session
    root=Path(root).resolve(strict=True);task_path=private_path(root,task_path)
    task_pin=pin(task_path);task=read(task_path);selected=selected_profile(task['N'])
    validate_task(root,task,live=True,recovery=True,require_android=False)
    folder=task_path.parent;grant=pin(folder/'grant.json')
    tasks.validate_grant(task,read(verify(grant)),Path(grant['path']))
    operations=sorted(folder.glob('operation-*/operation.json'))
    require(len(operations)==1,'comparison task has no unique operation')
    operation=operations[0];request=read(operation)
    require(request['task']==task_pin and request['grant']==grant and request['operation']==selected.OPERATION,
            'close does not belong to the original comparison task')
    session=Session(root,operation.parent,Adapter(root,operation.parent))
    terminal=session.repair_close()
    require(terminal['terminal_state']=='ANDROID_CLOSED_HEALTHY' and terminal['research_closed'] is True,
            'task lacks raw-proved original-A health')
    registry.require_no_f1_owner(root)
    terminal_pin=pin(operation.parent/'terminal.json')
    def retain(name,value):
        path=folder/name
        if path.exists():
            require(read(path)==value,'retained close artifact differs: '+name)
            return pin(path)
        return publish(path,value)
    captures=[]
    for path in sorted(folder.rglob('*.capture.json')):
        handle=access.raw.load_handle(path)
        access.raw.read_stdout(handle,maximum=max(handle.stdout['size'],1))
        access.raw.read_stderr(handle,maximum=max(handle.stderr['size'],1))
        captures.append(dict(receipt=pin(path),returncode=handle.returncode,timed_out=handle.timed_out))
    raw_index=retain('raw-index.json',dict(schema='s22plus-comparison-raw-index-v1',captures=captures))
    rows=session.rows();effects=[r for r in rows if r['event']=='effect-intent']
    transfers=[r for r in effects if r['data']['action']=='transfer']
    a=[r for r in transfers if r['data']['role']=='A'];n=[r for r in transfers if r['data']['role']=='N']
    require(len(a)==1 and len(n)<=1 and len(a)+len(n)==len(transfers),'comparison transfer count differs')
    opened=read(verify(grant))['opened_ns']
    def event(label,kind,step):
        matches=[r for r in rows if r['event']==kind and r['data'].get('step')==step]
        require(len(matches)<=1,'duplicate timeline transition')
        if not matches:return dict(event=label,seconds=None,status='NOT_PROVED')
        row=matches[0]
        return dict(event=label,seconds=(row['boottime_ns']-opened)/1e9,
                    journal=pin(session.journal.directory/f"{row['sequence']:04d}.json"))
    # The final durable session row supplies a stable end even if publication
    # stops between these H0 artifacts. A retry rederives and retains bytes.
    ended=rows[-1]['boottime_ns']
    timeline=retain('timeline.json',dict(schema='s22plus-canonical-timeline-v1',events=[
        dict(event='live_session_start',seconds=0,grant=grant),
        event('candidate_flash_start','effect-intent','install-native-first'),
        event('candidate_flash_done','step-complete','install-native-first'),
        event('candidate_boot_ready','step-complete',selected.SELECTION),
        event('rollback_flash_start','effect-intent',a[0]['data']['step']),
        event('rollback_flash_done','step-complete',a[0]['data']['step']),
        event('rollback_boot_ready','step-complete',terminal['terminal_step']),
        dict(event='live_session_end',seconds=(ended-opened)/1e9,status='DURABLE_SESSION_CLOSE')]))
    result_key='mainline' if selected is profile else 'loader_android'
    value=dict(schema='s22plus-comparison-task-closed-v1',task=task_pin,grant=grant,operation=pin(operation),
        current_android_terminal=terminal_pin,terminal_state=terminal['terminal_state'],
        scientific_status=terminal[result_key]['status'],recovered=terminal['recovered'],
        closed_boottime_ns=ended,original_N_transfers_total=len(n),original_A_transfers_total=len(a),
        device_controls_total=sum(r['data']['action']=='download' for r in effects),
        automatic_recovery_proved=False,native_admitted=False,raw_captures=raw_index,canonical_timeline=timeline,
        source_binding=task['review'],source_snapshot=pin(folder/'source-snapshot.json'),
        device_actions_by_closure=0,journal_rows=len(rows),journal_tail=pin(session.journal.directory/f'{len(rows)-1:04d}.json'))
    return retain('closed.json',value)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=profile.ROOT)
    sub=parser.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('image',type=Path);prep.add_argument('retained_task',type=Path)
    prep.add_argument('output',type=Path)
    ready=sub.add_parser('ready');ready.add_argument('task',type=Path)
    close=sub.add_parser('close');close.add_argument('task',type=Path)
    grant=sub.add_parser('grant');grant.add_argument('task',type=Path)
    grant.add_argument('--returned-approval',required=True);grant.add_argument('--operator-statement',required=True)
    args=parser.parse_args()
    result=(prepare(args.root,args.output,args.image,args.retained_task) if args.command=='prepare' else
        readiness(args.root,args.task) if args.command=='ready' else
        close_task(args.root,args.task) if args.command=='close' else open_grant(
            args.root,args.task,returned_approval=args.returned_approval,operator_statement=args.operator_statement))
    print(canonical(result).decode(),end='')


if __name__=='__main__':main()
