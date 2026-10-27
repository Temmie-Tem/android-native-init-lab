"""One attended mainline RAM/USB candidate, using the existing V3 owner."""
import argparse
import os
from pathlib import Path
import re
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
    's22plus_mainline_session_v1','s22plus_native_task_v3','s22plus_native_session_v3',
    's22plus_native_adapter_v3','s22plus_native_qualification_v1','s22plus_native_records_v3','s22plus_native_target_io_v3',
    's22plus_native_host_v3','s22plus_native_host_census_v1','s22plus_debian_handoff_session_v1',
    's22plus_boot_only_f1_transport','s22plus_boot_verify','s22plus_boot_only_live_core',
    's22plus_odin_transition_core','s22plus_odin_usbfs_identity','s22plus_fyg8_p324_typec_lane_binding',
    'consumed_candidate_registry_v1','device_action_raw_capture_v1','device_action_read_dependencies_v1')


def source_paths(root):
    root=Path(root)
    paths=['workspace/public/src/scripts/revalidation/'+name+'.py' for name in MODULES]
    paths+=['workspace/public/src/scripts/analysis/s22plus_fyg8_p319_max77705_irq_dt_audit.py','AGENTS.md',tasks.DETAILS,tasks.TARGET_CONTRACT,profile.POLICY,tasks.PROFILE,
        'docs/operations/DEVICE_ACTION_PROCESS_V2.md','docs/operations/DEVICE_ACTION_RISK_TIERS.md',
        'workspace/public/src/mainline/s22plus_canary_h0/verify.py',
        'workspace/public/src/mainline/s22plus_canary_h0/prepare.py',
        'workspace/public/src/scripts/analysis/s22plus_native_artifact_v3_h0.py',
        'workspace/public/src/scripts/revalidation/device_action_f1_legacy_consumed_candidate_authority_v1.json']
    return tuple(root/path for path in sorted(paths))


def source_pins(root):
    root=Path(root)
    return [dict(pin(path),path=str(path.relative_to(root))) for path in source_paths(root)]


def capability(root,*,recovery=False):
    root=Path(root);path=root/profile.REVIEW;value=read(path)
    require(set(value)=={'schema','verdict','scope','sources','reviewer','findings'} and
        value['schema']=='s22plus-mainline-ram-review-v1' and value['verdict']=='PASS_GO' and
        value['scope']=='MAINLINE_RAM_F1_CAPABILITY' and value['findings']==[] and
        type(value['reviewer']) is str and value['reviewer'].strip(),'mainline independent review is not PASS_GO')
    expected=[str(path.relative_to(root)) for path in source_paths(root)]
    require([r['path'] for r in value['sources']]==expected,'mainline review source closure differs')
    for row in value['sources']:tasks.unchanged(dict(row,path=str(root/row['path'])))
    return pin(path)


def validate_access(plan):
    require(set(plan)=={'uuid','name','nmcli','ip'} and str(uuid.UUID(plan['uuid']))==plan['uuid'] and
        plan['name']=='s22plus-mainline-'+plan['uuid'],'mainline host network ownership differs')
    for name,path in [('nmcli','/usr/bin/nmcli'),('ip','/usr/sbin/ip')]:
        require(plan[name]['path']==str(Path(path).resolve(strict=True)),'host executable path differs')
        tasks.unchanged(plan[name],maximum=32*1024*1024)


def validate_task(root,task,*,live=False,recovery=False,require_android=True):
    root=Path(root)
    keys={'schema','target','lane','N','E','A','adb','odin','host_installation','review','recovery_evidence',
        'operations','seconds','operation_budget','recovery_mode','reentry','hud','usb_reconnect',
        'admission','prior_terminal','runtime_scope','mainline_access'}
    require(set(task)==keys and task['schema']=='s22plus-mainline-task-v1' and
        task['operations']==[profile.OPERATION] and type(task['seconds']) is int and task['seconds']==profile.SECONDS and
        type(task['operation_budget']) is int and task['operation_budget']==1 and task['recovery_mode']=='attended' and
        all(task[k] is False for k in ('reentry','hud','usb_reconnect')) and
        all(task[k] is None for k in ('E','admission','prior_terminal')) and task['N']['profile']==profile.PROFILE,
        'mainline task exceeds one attended Android-origin operation')
    require(set(task['target'])=={'serial','topology'} and
        re.fullmatch('[A-Za-z0-9._:-]{1,128}',task['target']['serial']) and
        task['target']['topology']==target.lane.SOURCE_TOPOLOGY,'mainline target binding differs')
    target.lane.validate_binding(task['lane'],source_topology=target.lane.SOURCE_TOPOLOGY)
    require(task['review']==capability(root,recovery=recovery),'mainline capability changed')
    require(task['runtime_scope']==task['N']['runtime_sources'],'mainline runtime scope differs')
    if not recovery:
        profile.image_binding(task['N']);validate_access(task['mainline_access'])
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
            Path(profile.POLICY).name.encode() in read_bytes(root/tasks.TARGET_CONTRACT) and
            b'Status: **REVIEW_GATED_CAPABILITY**' in read_bytes(root/profile.POLICY),
            'mainline target adoption or common detail pin differs')
    return task


def validate_operation(adapter,request,*,recovery=False):
    task=adapter.configuration(request)
    completed=adapter.android_transfer_completed(request)
    validate_task(adapter.root,task,live=True,recovery=recovery or completed,require_android=not completed)
    grant_path=verify(request['grant']);grant=read(grant_path);tasks.validate_grant(task,grant,grant_path)
    expected=dict(schema=SCHEMA,operation=profile.OPERATION,reentry=False,hud=False,grant=request['grant'],
        task=grant['task'],N=task['N'],E=None,A=task['A'],admission=None,prior_terminal=None,usb_reconnect=False)
    require(request==expected,'mainline operation differs from its original finite task')


def host_ready(task,folder):
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
    profile.image_binding(task['N'],artifact_bytes=True)
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
        value['task']==task_receipt and value['host_boot']==host_boot() and
        value['device_controls']==value['partition_transfers']==0,'preapproval readiness differs')
    require(Path(receipt['path']).parent.parent==Path(task_receipt['path']).parent,'readiness belongs elsewhere')
    if fresh:require(0<=clock()-value['observed_ns']<=300_000_000_000,'preapproval health is stale')
    health=read(verify(value['health']))
    require(target.health_projection(health['captures'],task['target'],task['A'])==health,'preapproval raw health differs')
    access.raw.require_success(access.raw.load_handle(verify(value['network_permissions'])))
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
    require(not output.exists(),'fresh mainline task directory required')
    profile.image_binding(image,artifact_bytes=True)
    selected={k:previous[k] for k in ('target','lane','host_installation','recovery_evidence')}
    ident=str(uuid.uuid4())
    task=dict(selected,schema='s22plus-mainline-task-v1',N=image,E=None,A=tasks.android_artifact(root),
        adb=pin(Path('/usr/bin/adb').resolve(strict=True),maximum=32*1024*1024),
        odin=read(root/tasks.PROFILE)['transport']['odin'],review=capability(root),operations=[profile.OPERATION],
        seconds=profile.SECONDS,operation_budget=1,recovery_mode='attended',reentry=False,hud=False,
        usb_reconnect=False,admission=None,prior_terminal=None,runtime_scope=image['runtime_sources'],
        mainline_access=dict(uuid=ident,name='s22plus-mainline-'+ident,
            nmcli=pin(Path('/usr/bin/nmcli').resolve(strict=True)),ip=pin(Path('/usr/sbin/ip').resolve(strict=True))))
    validate_task(root,task)
    output.mkdir(mode=0o700);Journal(output/'journal');receipt=publish(output/'task.json',task)
    publish(output/'proposal.json',dict(task=receipt,approval=tasks.approval_text(task,receipt),
        grants_device_authority=False,device_actions=0))
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=profile.ROOT)
    sub=parser.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('image',type=Path);prep.add_argument('retained_task',type=Path)
    prep.add_argument('output',type=Path)
    ready=sub.add_parser('ready');ready.add_argument('task',type=Path)
    grant=sub.add_parser('grant');grant.add_argument('task',type=Path)
    grant.add_argument('--returned-approval',required=True);grant.add_argument('--operator-statement',required=True)
    args=parser.parse_args()
    result=(prepare(args.root,args.output,args.image,args.retained_task) if args.command=='prepare' else
        readiness(args.root,args.task) if args.command=='ready' else open_grant(
            args.root,args.task,returned_approval=args.returned_approval,operator_statement=args.operator_statement))
    print(canonical(result).decode(),end='')


if __name__=='__main__':main()
