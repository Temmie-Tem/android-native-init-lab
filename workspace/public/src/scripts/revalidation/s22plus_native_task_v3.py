"""Prepare a concrete finite task; only an actual returned grant opens it."""
import argparse
import ast
import functools
import os
from pathlib import Path
import re
import stat

from s22plus_native_records_v3 import (SCHEMA, canonical, clock, digest, host_boot, pin,
    private_path, publish, read, read_bytes, require, verify)

POLICY='docs/operations/S22PLUS_NATIVE_SESSION_V3.md'
TARGET_CONTRACT='docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md'
DETAILS='docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md'
CAPABILITY='workspace/public/src/device-action/bindings/s22plus_native_session_v3_review.json'
PROFILE='workspace/public/src/device-action/profiles/s22plus_fyg8.json'
SOURCE_ENTRY=('s22plus_native_task_v3','s22plus_native_adapter_v3','s22plus_native_session_v3',
    's22plus_native_host_install_v3')
_verified={}


@functools.lru_cache(maxsize=4)
def source_paths(root):
    """Literal local Python imports; no historical live-owner closure."""
    root=Path(root); base=root/'workspace/public/src/scripts/revalidation'
    pending=list(SOURCE_ENTRY); paths=set()
    while pending:
        name=pending.pop(); path=base/(name+'.py')
        if not path.is_file() or path in paths: continue
        paths.add(path)
        for node in ast.walk(ast.parse(read_bytes(path))):
            if isinstance(node,ast.Import): pending.extend(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module: pending.append(node.module.split('.')[0])
    forbidden={'device_action_f1_v2.py','device_action_f1_live_v2.py','s22plus_native_baseline_owner_v1.py'}
    require(not forbidden.intersection(path.name for path in paths),'legacy live owner is reachable from V3')
    paths.update(root/name for name in ('AGENTS.md',DETAILS,TARGET_CONTRACT,POLICY,PROFILE,
        'docs/operations/S22PLUS_ANDROID_STORAGE_CENSUS_V1.md',
        'docs/operations/S22PLUS_NATIVE_UFS_V1.md',
        'docs/operations/S22PLUS_NATIVE_GPT_RESERVATION_V1.md',
        'docs/operations/DEVICE_ACTION_RISK_TIERS.md','docs/operations/DEVICE_ACTION_PROCESS_V2.md',
        'workspace/public/src/scripts/analysis/s22plus_native_artifact_v3_h0.py',
        'workspace/public/src/scripts/analysis/s22plus_native_ufs_artifact_v1_h0.py',
        'workspace/public/src/scripts/analysis/s22plus_native_output_drain_artifact_v1_h0.py',
        'workspace/public/src/scripts/analysis/s22plus_native_gpt_artifact_v1_h0.py',
        'workspace/public/src/scripts/revalidation/s22plus_native_baseline_v2_candidates.py'))
    return tuple(sorted(paths))


def execution_sources(root):
    return [pin(path) for path in source_paths(str(Path(root).resolve()))]


def unchanged(receipt, *, maximum=2*1024*1024):
    path=Path(receipt['path']); info=path.lstat()
    current=(info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
    key=(str(path),receipt['sha256'],receipt['size'])
    if _verified.get(key)!=current:
        verify(receipt,maximum=maximum); _verified[key]=current


def capability(root, *, recovery=False):
    path=Path(root)/CAPABILITY; result=read(path)
    require(set(result)=={'schema','verdict','scope','sources','runtime_sources','reviewer','findings'}
        and result['schema']=='s22plus-native-session-v3-review' and result['verdict']=='PASS_GO'
        and result['scope']=='V3_REACHABLE_CAPABILITY' and result['findings']==[],
        'independent V3 capability review is absent or not PASS_GO')
    require([row['path'] for row in result['sources']]==[str(path) for path in source_paths(str(Path(root).resolve()))],
        'reviewed V3 source closure differs')
    for receipt in result['sources']: unchanged(receipt)
    require(type(result['runtime_sources']) is dict and result['runtime_sources'],
        'review has no approved native source closure')
    for name,identity in result['runtime_sources'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'native source path differs')
        if not recovery: unchanged(dict(path=str(Path(root)/name),**identity))
    return pin(path)


def android_artifact(root):
    import s22plus_boot_only_f1_transport as transport
    profile=read(Path(root)/PROFILE); ap=dict(profile['rollback']['ap'])
    ap['path']=str(Path(root)/ap['path'])
    with transport.pin_boot_only_ap(Path(ap['path']),label='original Android A',
            expected_size=ap['size'],expected_sha256=ap['sha256'],require_deterministic_metadata=False) as bound:
        member=transport.boot_only_member_receipt(bound,label='original Android A',require_deterministic_metadata=False)
    return dict(ap=ap,member=member,partition_sha256=dict(boot=profile['start_health']['boot_sha256'],
        **profile['start_health']['supporting_partition_sha256']))


def validate_task(root, task, *, live=False, recovery=False, require_android=True):
    from s22plus_native_adapter_v3 import image_valid
    import s22plus_native_target_io_v3 as target
    keys={'schema','target','lane','N','E','A','adb','odin','host_installation','review','recovery_evidence',
        'operations','seconds','operation_budget','recovery_mode','reentry','hud','usb_reconnect',
        'admission','prior_terminal','runtime_scope'}
    require(set(task) in (keys,keys|{'bootstrap_start'})
        and task['schema']=='s22plus-native-task-v3','native task schema differs')
    require(type(task['seconds']) is int and 60<=task['seconds']<=7200
        and type(task['operation_budget']) is int and 1<=task['operation_budget']<=3,
        'native task exceeds finite scope')
    require(type(task['operations']) is list and task['operations']
        and len(task['operations'])==len(set(task['operations']))
        and set(task['operations'])<={'bootstrap','experiment','android-exit','storage-census','gpt-reserve'}
        and task['recovery_mode'] in ('attended','deferred'),'native task operations or recovery differ')
    require(all(type(task[key]) is bool for key in ('reentry','hud','usb_reconnect'))
        and (not task['usb_reconnect'] or task['reentry'] and task['recovery_mode']=='attended'),
        'physical reconnect requires a selected attended E reentry')
    if task['N']['profile']=='thermal-v3-reconnect-ufs-drain-gpt-v1' or 'gpt-reserve' in task['operations']:
        require(task['N']['profile']=='thermal-v3-reconnect-ufs-drain-gpt-v1'
            and set(task['operations'])<={'bootstrap','gpt-reserve'} and task['recovery_mode']=='attended'
            and task['operation_budget']<=2
            and not any(task[key] for key in ('reentry','hud','usb_reconnect')),
            'GPT reservation requires its exact attended task scope')
    require(task['target']['topology']==target.lane.SOURCE_TOPOLOGY
        and set(task['target'])=={'serial','topology'}
        and re.fullmatch('[A-Za-z0-9._:-]{1,128}',task['target']['serial']),
        'task target identity differs')
    target.lane.validate_binding(task['lane'],source_topology=target.lane.SOURCE_TOPOLOGY)
    require(task['review']==capability(root,recovery=recovery),'task capability review changed')
    if not recovery: image_valid(task['N'])
    require(task['runtime_scope']==task['N']['runtime_sources']==read(verify(task['review']))['runtime_sources'],
        'native runtime scope is not the independently reviewed source closure')
    start=task.get('bootstrap_start')
    if start is not None:
        require(set(start)=={'N','admission','prior_terminal'} and 'bootstrap' in task['operations']
            and task['admission'] is None and task['prior_terminal'] is None,
            'bootstrap start must be a separate admitted predecessor')
        if not recovery: image_valid(start['N'])
        require(start['N']['run_id_hex']!=task['N']['run_id_hex']
            and start['N']['ap']['sha256']!=task['N']['ap']['sha256']
            and all(task['runtime_scope'].get(name)==identity
                for name,identity in start['N']['runtime_sources'].items()),
            'bootstrap predecessor is not an unchanged ancestor of the reviewed native scope')
    if 'experiment' in task['operations']:
        if not recovery: image_valid(task['E'])
        require(task['E']['runtime_sources']==task['runtime_scope'] and task['E']['ap']!=task['N']['ap']
            and task['E']['run_id_hex']!=task['N']['run_id_hex'],'E is not a distinct qualified in-scope image')
    else: require(task['E'] is None,'task contains an unselected E')
    profile=read(Path(root)/PROFILE)
    require(task['odin']==profile['transport']['odin'] and task['A']['ap']==dict(profile['rollback']['ap'],
        path=str(Path(root)/profile['rollback']['ap']['path']))
        and task['A']['partition_sha256']==dict(boot=profile['start_health']['boot_sha256'],
            **profile['start_health']['supporting_partition_sha256']),'task original Android or Odin identity differs')
    # Every guard checks the original A path. Its successful hash remains
    # reusable only while the exact filesystem identity is unchanged.
    if require_android: unchanged(task['A']['ap'],maximum=128*1024*1024)
    installation=read(verify(task['host_installation']))
    require(installation['uid']==os.getuid() and installation['topology']==target.lane.CANDIDATE_TOPOLOGY.removeprefix('usb:'),
        'host native port or invoking account differs')
    if require_android: validate_recovery(task['recovery_evidence'],task['target'],task['A'])
    if live:
        details=read_bytes(Path(root)/DETAILS)
        agents=read_bytes(Path(root)/'AGENTS.md')
        require(digest(details).encode() in agents,'common contract detail pin differs')
        require(b'S22PLUS_NATIVE_SESSION_V3.md' in details
            and b'S22PLUS_NATIVE_SESSION_V3.md' in read_bytes(Path(root)/TARGET_CONTRACT)
            and b'Status: **REVIEW_GATED_CAPABILITY**' in read_bytes(Path(root)/POLICY),
            'V3 is not common-incorporated and adopted by the exact target')
        if task['N']['profile']=='thermal-v3-reconnect-ufs-drain-gpt-v1':
            require(b'S22PLUS_NATIVE_GPT_RESERVATION_V1.md' in details
                and b'S22PLUS_NATIVE_GPT_RESERVATION_V1.md' in read_bytes(Path(root)/TARGET_CONTRACT)
                and b'Status: **REVIEW_GATED_CAPABILITY**' in read_bytes(Path(root)/
                    'docs/operations/S22PLUS_NATIVE_GPT_RESERVATION_V1.md'),
                'GPT profile/exception is not common-incorporated and adopted by the exact target')
    return task


def validate_recovery(receipt, binding, android):
    import device_action_raw_capture_v1 as raw
    import s22plus_native_target_io_v3 as target
    evidence=read(verify(receipt))
    require(set(evidence)=={'schema','target','A','transfer','health','source_terminal','source_health',
        'source_transfer','exporter'} and evidence['schema']=='s22plus-native-recovery-evidence-v3'
        and evidence['target']==binding and evidence['A']==android and evidence['transfer']['ap']==android['ap'],
        'demonstrated recovery belongs to a different physical target or Android A')
    for key in ('source_terminal','source_health','source_transfer','exporter'): verify(evidence[key])
    require(evidence['exporter']['path']==str(Path(__file__).resolve().parents[1]/'analysis/s22plus_native_artifact_v3_h0.py'),
        'recovery evidence exporter differs')
    target.transfer_completed(raw.load_handle(verify(evidence['transfer']['raw'])))
    require(target.health_projection(evidence['health']['captures'],binding,android)==evidence['health'],
        'demonstrated recovery has no exact raw Android health')
    return evidence


def prepare_task(root, output, *, native, experiment, target, installation, recovery_evidence,
                 seconds=3600, operation_budget=3, recovery_mode='attended', reentry=True,
                 hud=False, usb_reconnect=True, admission=None, prior_terminal=None,
                 storage_census=False, android_exit=True, bootstrap_start=None,gpt_reserve=False):
    import s22plus_native_target_io_v3 as target_io
    from s22plus_native_adapter_v3 import image_valid
    root=Path(root).resolve(strict=True); output=private_path(root,output,exists=False)
    require(not output.exists(),'native task preparation path already exists')
    require(type(storage_census) is bool and type(android_exit) is bool and type(gpt_reserve) is bool
        and (not storage_census or (admission is None)==(prior_terminal is None)),
        'storage census needs either fresh bootstrap or an admitted N and its closed tail')
    native=read(verify(native)); experiment=read(verify(experiment)) if experiment else None
    image_valid(native,artifact_bytes=True)
    if experiment is not None: image_valid(experiment,artifact_bytes=True)
    task=dict(schema='s22plus-native-task-v3',target=read(verify(target)),N=native,E=experiment,
        A=android_artifact(root),adb=pin(Path('/usr/bin/adb').resolve(strict=True),maximum=32*1024*1024),
        odin=read(root/PROFILE)['transport']['odin'],host_installation=installation,
        review=capability(root),recovery_evidence=recovery_evidence,
        lane=target_io.lane.capture_binding(target_io.lane.SOURCE_TOPOLOGY),
        operations=(['bootstrap'] if admission is None else [])+(['experiment'] if experiment else [])
            +(['storage-census'] if storage_census else [])+(['android-exit'] if android_exit else [])
            +(['gpt-reserve'] if gpt_reserve else []),
        seconds=seconds,operation_budget=operation_budget,recovery_mode=recovery_mode,reentry=reentry,
        hud=hud,usb_reconnect=usb_reconnect,admission=admission,prior_terminal=prior_terminal,
        runtime_scope=native['runtime_sources'])
    if bootstrap_start is not None: task['bootstrap_start']=bootstrap_start
    validate_task(root,task,live=False)
    output.mkdir(mode=0o700); receipt=publish(output/'task.json',task)
    publish(output/'proposal.json',dict(task=receipt,approval=approval_text(task,receipt),
        grants_device_authority=False))
    return receipt


def approval_text(task, receipt):
    return f"APPROVE S22PLUS NATIVE V3 {receipt['sha256']} {task['seconds']}s {task['operation_budget']}operations {task['recovery_mode']}"


def validate_grant(task, grant, path):
    require(set(grant)=={'schema','task','directory','host_boot','opened_ns','deadline_ns','operation_budget',
        'recovery_mode','operator_statement','returned_approval'} and grant['schema']==SCHEMA,
        'native grant schema differs')
    require(Path(grant['directory'])==Path(path).parent and grant['task']['path']==str(Path(path).parent/'task.json')
        and read(verify(grant['task']))==task,'grant belongs to a different task')
    require(type(grant['opened_ns']) is int and type(grant['deadline_ns']) is int
        and grant['deadline_ns']==grant['opened_ns']+task['seconds']*1_000_000_000
        and type(grant['operation_budget']) is int and grant['operation_budget']==task['operation_budget']
        and grant['recovery_mode']==task['recovery_mode'],
        'grant changed the original time, capacity or recovery scope')
    require(grant['returned_approval']==approval_text(task,grant['task'])
        and type(grant['operator_statement']) is str and 0<len(grant['operator_statement'].strip())<=4096,
        'grant has no exact returned operator statement')


def open_grant(root, task_path, *, returned_approval, operator_statement):
    task_path=private_path(root,task_path); receipt=pin(task_path); task=read(task_path)
    validate_task(root,task,live=True)
    require(returned_approval==approval_text(task,receipt) and type(operator_statement) is str
        and operator_statement.strip(),'actual returned operator task grant is required')
    # Host setup and noninteractive readiness happen before opening this clock.
    from s22plus_native_host_v3 import NativeHost
    host=NativeHost(read(verify(task['host_installation'])),task_path.parent/'grant-host-preflight')
    host.holders()
    now=clock()
    return publish(task_path.parent/'grant.json',dict(schema=SCHEMA,task=receipt,
        directory=str(task_path.parent),host_boot=host_boot(),opened_ns=now,
        deadline_ns=now+task['seconds']*1_000_000_000,operation_budget=task['operation_budget'],
        recovery_mode=task['recovery_mode'],operator_statement=operator_statement,returned_approval=returned_approval))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[5])
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('execute'); run.add_argument('operation',choices=('bootstrap','experiment','android-exit','storage-census','gpt-reserve'))
    run.add_argument('grant',type=Path); run.add_argument('--attended',action='store_true')
    run.add_argument('--reentry',action='store_true'); run.add_argument('--hud',action='store_true')
    run.add_argument('--experiment-image',type=Path)
    for command in ('recover','repair-close','continue'):
        item=sub.add_parser(command); item.add_argument('operation_directory',type=Path)
        if command in ('recover','continue'): item.add_argument('--attended',action='store_true')
        if command=='continue':item.add_argument('--operator-statement')
    census=sub.add_parser('android-storage');census.add_argument('closed_task',type=Path)
    census.add_argument('output',type=Path)
    args=parser.parse_args()
    if args.command=='android-storage':
        from s22plus_native_android_storage_v1 import observe
        value=observe(args.root,args.closed_task,args.output)
        print(canonical(value).decode(),end='')
        return
    from s22plus_native_adapter_v3 import Adapter
    from s22plus_native_session_v3 import Session, prepare_operation
    if args.command=='execute':
        directory=prepare_operation(args.root,args.grant,operation=args.operation,
            adapter=Adapter(args.root,args.grant.parent,experiment=pin(args.experiment_image) if args.experiment_image else None),
            reentry=args.reentry,hud=args.hud)
        value=Session(args.root,directory,Adapter(args.root,directory)).execute(attended=args.attended)
    else:
        directory=args.operation_directory; session=Session(args.root,directory,Adapter(args.root,directory))
        value=(session.recover(attended=args.attended) if args.command=='recover' else
            session.resume(attended=args.attended,operator_statement=args.operator_statement) if args.command=='continue'
            else session.repair_close())
    print(canonical(value).decode(),end='')


if __name__=='__main__': main()
