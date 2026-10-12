"""Fixed post-closure same-Android-boot last_kmsg D0; no control or write."""
from pathlib import Path

import consumed_candidate_registry_v1 as registry
import device_action_raw_capture_v1 as raw
import s22plus_boot_only_f1_transport as transport
import s22plus_native_android_storage_v1 as census
import s22plus_native_target_io_v3 as target
import s22plus_native_task_v3 as owner
import s22plus_debian_early_profile_v1 as profile
import s22plus_debian_usb_protocol_v1 as protocol
from s22plus_native_records_v3 import pin,private_path,publish,read,require,verify


def stage_projection(directory,task_directory):
    """H0 replay of the new stage capture; no device acquisition or journal edit."""
    from s22plus_debian_file_retrieval_v1 import closed_operation
    import s22plus_debian_stage_protocol_v1 as stage_protocol
    directory=private_path(profile.ROOT,directory);task_directory=private_path(profile.ROOT,task_directory)
    task=read(task_directory/'task.json');closed=read(task_directory/'closed.json')
    require(task['N']['profile']==profile.STAGE_PROFILE,'not a stage-only capture')
    outcome=read(verify(closed['current_android_terminal']))
    operation=Path(verify(outcome['operation_record'])).parent
    bound=closed_operation(operation,profile.STAGE_PROFILE)
    require(bound['task']==task and bound['closed']==pin(task_directory/'closed.json'),'stage owner differs')
    artifact=profile.image_binding(task['N'])
    returned=read(verify(read(verify(outcome['terminal_result']))['health']))
    started=read(directory/'started.json')
    require(started['schema']=='s22plus-stage-retention-d0-v1' and started['task']==pin(task_directory/'task.json') and
        started['closed']==pin(task_directory/'closed.json') and started['device_effects']==0,'stage capture binding differs')
    first=read(directory/'before/health.json');last=read(directory/'after/health.json')
    for health in (first,last):
        require(target.health_projection(health['captures'],task['target'],task['A'])==health,
            'stage D0 health does not rederive')
    require(first['properties']==last['properties'] and
        first['boot_id_sha256']==last['boot_id_sha256']==returned['boot_id_sha256'],
        'stage D0 is not the same original-A returned boot')
    census.require_shell_v2(pin(directory/'transport/features.capture.json'))
    handle=raw.load_handle(directory/'last-kmsg.capture.json');raw.require_success(handle)
    result=stage_protocol.retained(raw.read_stdout(handle,maximum=4*1024**2),
        key=verify(task['N']['key'],maximum=32).read_bytes(),run=bytes.fromhex(task['N']['run_id_hex']),
        expected=artifact['expected'],logger_sha256=profile.LOGGER['sha256'])
    result.update(provenance='POST_CANDIDATE_PHYSICAL_ORIGINAL_A_RETURN_LAST_KMSG',
        retained_any_stage=bool(result['records']),device_effects=0,same_returned_android_boot=True,
        before=pin(directory/'before/health.json'),after=pin(directory/'after/health.json'),
        capture=pin(handle.receipt_path),closed=pin(task_directory/'closed.json'))
    return result


def capture(directory,task_directory):
    root=profile.ROOT;directory=private_path(root,directory,exists=False)
    task_directory=private_path(root,task_directory)
    task=read(task_directory/'task.json');closed=read(task_directory/'closed.json')
    artifact=read(verify(task['N']['early_boot']))
    stage=task['N'].get('profile')==profile.STAGE_PROFILE
    if stage:
        from s22plus_debian_file_retrieval_v1 import closed_operation
        artifact=profile.image_binding(task['N'])
        outcome=read(verify(closed['current_android_terminal']))
        bound=closed_operation(Path(verify(outcome['operation_record'])).parent,profile.STAGE_PROFILE)
        require(bound['task']==task and bound['closed']==pin(task_directory/'closed.json'),'stage closed owner differs')
    else:
        require(profile.usb_logging_mode(read(verify(artifact['build'])))=='retained',
            'RAM-only USB candidate has no retained-log capture scope')
    require(closed['task']==pin(task_directory/'task.json') and
        task['N'].get('profile') in (profile.USB_PROFILE,profile.STAGE_PROFILE) and task['operations']==[profile.OPERATION] and
        closed['terminal_state']=='ANDROID_CLOSED_HEALTHY' and closed['consumed_operations']==1,
        'USB trial is not closed healthy')
    outcome=read(verify(closed['current_android_terminal']))
    require(outcome['operation']==profile.OPERATION and outcome['terminal_state']=='ANDROID_CLOSED_HEALTHY' and
        read(verify(outcome['operation_record']))['N']==task['N'],'closed USB operation identity differs')
    terminal=read(verify(outcome['terminal_result']))
    returned=read(verify(terminal['health']))
    tool=pin(Path('/usr/bin/adb').resolve(strict=True),maximum=32*1024**2)
    require(tool==task['adb'],'post-return ADB changed')
    require(not directory.exists(),'fresh D0 capture directory required');directory.mkdir(mode=0o700)
    def guard():
        owner.capability(root,profile=task['N']['profile'])
        registry.require_no_f1_owner(root)
    try:
        with registry.target_session_lease(root):
            guard();publish(directory/'started.json',dict(schema='s22plus-stage-retention-d0-v1' if stage else 's22plus-usb-retention-d0-v1',source=pin(Path(__file__)),
                task=pin(task_directory/'task.json'),closed=pin(task_directory/'closed.json'),device_effects=0))
            first=target.Android(tool,task['target'],task['A'],directory/'before',guard=guard).health()
            require(first['boot_id_sha256']==returned['boot_id_sha256'],'Android changed since candidate return')
            features=target.Android(tool,task['target'],task['A'],directory/'transport',guard=guard).command(
                ['-s',task['target']['serial'],'features'],'features',timeout=10)
            census.require_shell_v2(pin(features.receipt_path));guard()
            with transport.pin_regular_file(Path(tool['path']),label='USB retention D0 ADB',expected_size=tool['size'],expected_sha256=tool['sha256']) as adb:
                handle=raw.acquire_command([str(adb.path),'-s',task['target']['serial'],'shell','-T',
                    "su -c 'cat /proc/last_kmsg'"],directory,'last-kmsg',timeout=30,
                    stdout_maximum=4*1024**2,stderr_maximum=16384)
            raw.require_success(handle)
            last=target.Android(tool,task['target'],task['A'],directory/'after',guard=guard).health()
            require(first['properties']==last['properties'] and first['boot_id_sha256']==last['boot_id_sha256'],
                'Android changed during fixed retention read')
            if stage:return publish(directory/'result.json',stage_projection(directory,task_directory))
            boot=outcome.get('debian_early',{}).get('kernel_boot_identity_sha256')
            result=protocol.retained(raw.read_stdout(handle,maximum=4*1024**2),
                key=verify(task['N']['key'],maximum=32).read_bytes(),run=bytes.fromhex(task['N']['run_id_hex']),boot=boot)
            result.update(provenance='POST_CANDIDATE_PHYSICAL_ORIGINAL_A_RETURN_LAST_KMSG',
                retained_any_stage=bool(result['records']),
                device_effects=0,same_returned_android_boot=True,before=pin(directory/'before/health.json'),
                after=pin(directory/'after/health.json'),capture=pin(handle.receipt_path),closed=pin(task_directory/'closed.json'))
            return publish(directory/'result.json',result)
    except BaseException as error:
        publish(directory/'stop.json',dict(status='STOP_D0',error_type=type(error).__name__,device_effects=0))
        raise
