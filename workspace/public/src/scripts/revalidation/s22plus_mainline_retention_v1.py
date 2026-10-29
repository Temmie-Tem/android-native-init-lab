"""Fixed post-closure mainline marker read; no controls, transfer or replay."""
import argparse
from pathlib import Path

import consumed_candidate_registry_v1 as registry
import device_action_raw_capture_v1 as raw
import s22plus_boot_only_f1_transport as transport
import s22plus_mainline_profile_v1 as profile
import s22plus_mainline_task_v1 as tasks
import s22plus_native_target_io_v3 as target
import s22plus_native_android_storage_v1 as census
from s22plus_native_records_v3 import SCHEMA,Journal,pin,private_path,publish,read,require,verify
from mainline.s22plus_canary_h0 import retained_marker as marker

ROOT=profile.ROOT
MAXIMUM=4*1024**2

def closed_binding(root,task_directory):
    """Read/rederive existing proof only. Never invoke repair or create journals."""
    from s22plus_native_adapter_v3 import Adapter,image_identity
    from s22plus_native_session_v3 import Session,Step,operation_steps
    root=Path(root);directory=private_path(root,task_directory)
    task_pin=pin(directory/'task.json');task=read(verify(task_pin));closed_pin=pin(directory/'closed.json')
    closed=read(verify(closed_pin))
    require(task['schema']==profile.TASK_SCHEMA and task['N']['profile']==profile.PROFILE and
            task['operations']==[profile.OPERATION] and 'retained_marker' in task['N'],
            'not an instrumented mainline task')
    manifest=profile.image_binding(task['N'])
    require(closed['schema']=='s22plus-comparison-task-closed-v1' and closed['task']==task_pin and
            closed['terminal_state']=='ANDROID_CLOSED_HEALTHY' and
            closed['original_N_transfers_total']==closed['original_A_transfers_total']==1 and
            closed['source_binding']==task['review'],'mainline task lacks its original closed outcome')
    operation_path=verify(closed['operation']);require(operation_path.parent.parent==directory,'operation belongs elsewhere')
    operation=read(operation_path);terminal_pin=closed['current_android_terminal'];terminal=read(verify(terminal_pin))
    require(terminal_pin==pin(operation_path.parent/'terminal.json') and
            operation['task']==task_pin and operation['N']==task['N'] and operation['A']==task['A'] and
            operation['grant']==closed['grant'] and operation['operation']==profile.OPERATION and
            terminal['schema']==SCHEMA and terminal['operation_record']==closed['operation'] and
            terminal['operation_sha256']==closed['operation']['sha256'] and terminal['grant']==closed['grant'] and
            terminal['terminal_state']=='ANDROID_CLOSED_HEALTHY' and terminal['research_closed'] is True,
            'mainline operation/terminal join differs')
    require((directory/'journal').is_dir(),'closed task journal missing')
    grant=read(verify(closed['grant']));tasks.tasks.validate_grant(task,grant,Path(closed['grant']['path']))
    require((operation_path.parent/'journal').is_dir(),'closed operation journal missing')
    adapter=Adapter(root,operation_path.parent);session=Session(root,operation_path.parent,adapter)
    require(session.consumed() is not None,'original operation consumption missing')
    rows=session.rows();effects=[r['data'] for r in rows if r['event']=='effect-intent']
    transfers=[e for e in effects if e['action']=='transfer']
    require([e['role'] for e in transfers]==['N','A'] and effects[-1]==transfers[-1] and
            closed['journal_rows']==len(rows) and closed['journal_tail']==pin(session.journal.directory/f'{len(rows)-1:04d}.json'),
            'closed mainline effects/journal differ')
    session.completed((Step('install-native-first','transfer','N'),))
    plan=(Step(transfers[-1]['step'],'transfer','A'),Step('recovery-health','health','A')) if terminal['recovered'] else operation_steps(operation)
    values=session.completed(plan)
    projected=adapter.terminal(plan,values,operation,recovered=terminal['recovered'])
    require(all(terminal.get(k)==v for k,v in projected.items()),'mainline terminal differs from raw evidence')
    if not terminal['recovered']:
        require([e['step'] for e in effects]==[s.name for s in plan if s.action in ('download','transfer')],
                'normal mainline effects differ')
    returned=read(verify(values[-1]['health']));initial=read(operation_path.parent/'io-preflight/health.json')
    for health in (initial,returned):
        require(target.health_projection(health['captures'],task['target'],task['A'])==health,'original health does not rederive')
    require(initial['boot_id_sha256']!=returned['boot_id_sha256'],'original-A returned boot did not change')
    identity=image_identity(task['N'],closed['operation']['sha256']);claim=read(operation_path.parent/'claim-N.json')
    require(claim['candidate_key']==identity['candidate_key'] and
            all(claim['record'].get(k)==v for k,v in identity.items() if k!='schema') and
            registry.active_claim(root,identity['candidate_key'])==claim['record'],'candidate claim differs')
    return dict(task=task,task_receipt=task_pin,closed=closed_pin,terminal=terminal_pin,
                returned=returned,manifest=manifest)

def projection(root,directory,task_directory):
    directory=private_path(root,directory);bound=closed_binding(root,task_directory);task=bound['task']
    started=read(directory/'started.json')
    require(started['schema']=='s22plus-mainline-retention-d0-v1' and started['task']==bound['task_receipt'] and
            started['closed']==bound['closed'] and started['terminal']==bound['terminal'] and
            started['device_controls']==started['partition_transfers']==0,'retention owner differs')
    first=read(directory/'before/health.json');last=read(directory/'after/health.json')
    for health in (first,last):
        require(target.health_projection(health['captures'],task['target'],task['A'])==health,'retention raw health differs')
    require(first['properties']==last['properties'] and
            first['boot_id_sha256']==last['boot_id_sha256']==bound['returned']['boot_id_sha256'],
            'retained read is not on the exact returned Android boot')
    census.require_shell_v2(pin(directory/'transport/features.capture.json'))
    capture=raw.load_handle(directory/'last-kmsg.capture.json');raw.require_success(capture)
    qualified=read(profile.unchanged(task['N']['retained_marker']))
    config=read(profile.unchanged(qualified['config']))
    result=marker.decode(raw.read_stdout(capture,maximum=MAXIMUM),bound['manifest']['candidate_id'],
        verify(task['N']['key'],maximum=32).read_bytes(),version=marker.version(config),config=config)
    result.update(task=bound['task_receipt'],closed=bound['closed'],terminal=bound['terminal'],
        capture=pin(capture.receipt_path),before=pin(directory/'before/health.json'),after=pin(directory/'after/health.json'),
        same_returned_android_boot=True,device_controls=0,partition_transfers=0)
    return result

def capture(root,directory,task_directory):
    root=Path(root);directory=private_path(root,directory,exists=False)
    require(not directory.exists(),'fresh mainline retention invocation required')
    # A fixed reobservation is a new invocation; no partial capture is retried.
    with registry.target_session_lease(root):
        registry.require_no_f1_owner(root);review=tasks.capability(root)
        bound=closed_binding(root,task_directory);task=bound['task']
        tool=pin(Path('/usr/bin/adb').resolve(strict=True),maximum=32*1024**2)
        require(tool==task['adb'],'retention ADB differs')
        directory.mkdir(mode=0o700)
        def guard():
            registry.require_no_f1_owner(root)
            require(tasks.capability(root)==review and pin(Path(bound['task_receipt']['path']))==bound['task_receipt'] and
                    pin(Path(bound['closed']['path']))==bound['closed'],'retention binding changed')
        publish(directory/'started.json',dict(schema='s22plus-mainline-retention-d0-v1',task=bound['task_receipt'],
            closed=bound['closed'],terminal=bound['terminal'],review=review,source=pin(Path(__file__)),device_controls=0,partition_transfers=0))
        try:
            guard();first=target.Android(tool,task['target'],task['A'],directory/'before',guard=guard).health()
            require(first['boot_id_sha256']==bound['returned']['boot_id_sha256'],'Android rebooted since original-A return')
            features=target.Android(tool,task['target'],task['A'],directory/'transport',guard=guard).command(
                ['-s',task['target']['serial'],'features'],'features',timeout=10)
            census.require_shell_v2(pin(features.receipt_path));guard()
            with transport.pin_regular_file(Path(tool['path']),label='mainline retention ADB',expected_size=tool['size'],expected_sha256=tool['sha256']) as adb:
                acquired=raw.acquire_command([str(adb.path),'-s',task['target']['serial'],'shell','-T',
                    "su -c 'cat /proc/last_kmsg'"],directory,'last-kmsg',timeout=30,
                    stdout_maximum=MAXIMUM,stderr_maximum=16384)
            raw.require_success(acquired)
            last=target.Android(tool,task['target'],task['A'],directory/'after',guard=guard).health()
            require(first['properties']==last['properties'] and first['boot_id_sha256']==last['boot_id_sha256'],'Android changed during retained read')
            guard();return publish(directory/'result.json',projection(root,directory,task_directory))
        except Exception as error:
            publish(directory/'stopped.json',dict(error_type=type(error).__name__,message=str(error)[:512],
                device_controls=0,partition_transfers=0,raw_retained=True))
            raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--task',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--project-only',action='store_true');a=p.parse_args()
    result=projection(a.root,a.output,a.task) if a.project_only else capture(a.root,a.output,a.task)
    from s22plus_native_records_v3 import canonical
    print(canonical(result).decode(),end='')
