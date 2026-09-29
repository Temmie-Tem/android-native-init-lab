"""One Android-origin native inspection; no baseline admission or reuse."""
import s22plus_native_root_inspect_profile_v1 as profile
import s22plus_native_userspace_probe_profile_v1 as probe
import s22plus_native_preflight_profile_v1 as preflight
import s22plus_native_staged_preflight_profile_v1 as staged
import s22plus_switch_root_profile_v1 as switch
import s22plus_debian_handoff_profile_v1 as handoff
from device_action_raw_capture_v1 import RawCaptureError
from s22plus_native_records_v3 import Journal, digest, pin, read, require, verify


ITEMS = (profile, probe, preflight, staged, switch, handoff)
PROFILES = tuple(item.PROFILE for item in ITEMS)
OPERATIONS = tuple(item.OPERATION for item in ITEMS)
SELECTIONS = tuple(item.SELECTION for item in ITEMS)


def selected(operation):
    require(operation in OPERATIONS, 'unknown protected-root operation')
    return next(item for item in ITEMS if operation == item.OPERATION)


def mutates_step(operation,name):
    return operation in OPERATIONS and selected(operation).SELECTION==name and selected(operation).Profile.MUTATES


def normal_steps(operation=profile.OPERATION):
    from s22plus_native_session_v3 import Step
    item = selected(operation)
    if item is handoff:
        from s22plus_debian_handoff_session_v1 import normal_steps as handoff_steps
        return handoff_steps()
    if item is switch:
        return (Step('android-download','download','A'),Step('install-native-first','transfer','N'),
            Step(item.SELECTION,'observe','N','download'),Step('install-android','transfer','A'),
            Step('android-final','health','A'))
    return (Step('android-download', 'download', 'A'),
        Step('install-native-first', 'transfer', 'N'),
        Step(item.SELECTION, 'observe', 'N', 'detach'),
        Step('inspector-return', 'observe', 'N', 'download'),
        Step('install-android', 'transfer', 'A'),
        Step('android-final', 'health', 'A'))


def validate_task(task, *, recovery=False):
    require(task['N']['profile'] in PROFILES, 'unknown protected-root image')
    item = next(item for item in ITEMS if task['N']['profile'] == item.PROFILE)
    require(task['N']['profile'] == item.PROFILE and task['operations'] == [item.OPERATION] and
        task['E'] is None and task['admission'] is None and task['prior_terminal'] is None and
        task.get('bootstrap_start') is None and task['recovery_mode'] == 'attended' and
        task['operation_budget'] == 1 and 60 <= task['seconds'] <= (3600 if item is handoff else 1800) and
        not any(task[k] for k in ('reentry', 'hud', 'usb_reconnect')),
        'inspector profile is restricted to one attended Android-origin operation')
    if not recovery: item.image_binding(task['N'])
    if item is handoff:
        from s22plus_debian_handoff_session_v1 import validate_task as handoff_task
        handoff_task(task,recovery=recovery)
    android_basis_for_image(task['N'], task['target'], task['A'])


def android_basis_for_image(image, target, android):
    _, _, previous = profile.prior_inputs()
    basis = image['android_return']
    require(basis == dict(source_terminal=profile.TERMINAL, target=previous['target'], A=previous['A'],
        layout='proposed', geometry=previous['basis']['geometry'], total_bytes=34357624832) and
        basis['target'] == target and basis['A'] == android and image['gpt'] == previous['basis']['gpt'],
        'inspector Android32 return basis differs from the closed P401 run')
    return dict(layout='proposed', geometry=basis['geometry'])


def android_basis(adapter, request):
    task = adapter.configuration(request)
    return android_basis_for_image(request['N'], task['target'], request['A'])


def validate_result(adapter, step, value, request):
    item = selected(request['operation'])
    if item is handoff:
        from s22plus_debian_handoff_session_v1 import validate_result as handoff_result
        return handoff_result(adapter,step,value,request)
    if step.name != item.SELECTION: return
    status = 'PASS_SWITCH_ROOT_WITNESS' if item is switch else 'PASS_STAGED_PREFLIGHT_OBSERVED' if item is staged else 'PASS_PREFLIGHT_OBSERVED' if item is preflight else 'PASS_PROBE_COMPLETED' if item is probe else 'PASS_INSPECTION_COMPLETED'
    require(value['proof'][item.Profile.RESULT_KEY]['status'] == status,
        'protected-root operation did not finish with bounded raw proof')
    records = [r['data'] for r in Journal(adapter.directory / 'journal').rows()
        if r['event'] == 'effect-intent' and r['data']['step'] == step.name]
    if item is switch:
        require(len(records)==1,'transition has no unique original compound intent')
        detail=records[0]['detail'];proof=value['proof'];folder=adapter.folder(step.name)
        require(detail['mode']=='fixed-pid1-transition' and detail['sequence']==5 and
            detail['body_sha256']==digest(b'') and detail['run_id_hex']==request['N']['run_id_hex'] and
            detail['nonce_sha256']==proof['nonce_sha256'] and
            detail['kernel_boot_identity_sha256']==proof['kernel_boot_identity_sha256'] and
            read(folder/'transition-intent.json')==detail,'transition does not join its original intent')
        returned=read(folder/'witness-return-intent.json')
        require(returned['transition']==pin(folder/'transition-intent.json') and
            returned['request']==dict(detail,mode='switch-root-return',sequence=6) and
            proof['switch_root']['return_accepted'] is True,'witness return is not the fixed original continuation')
        return
    if item is preflight:
        require(not records, 'read-only preflight result retrieval acquired an effect intent')
        proof=value['proof']
        require(proof['preflight']['kernel_boot_identity_sha256']==proof['kernel_boot_identity_sha256'],
            'preflight record belongs to a different authenticated boot')
        installed=[r['data'] for r in Journal(adapter.directory/'journal').rows()
            if r['event']=='effect-intent' and r['data']['step']=='install-native-first']
        require(len(installed)==1,'automatic preflight lacks its unique N transfer intent')
        return
    require(len(records) == 1, 'partition RO control has no unique pre-EXEC intent')
    detail = records[0]['detail']; proof = value['proof']; fixed = item.Profile(request['N'])
    require(detail['mode'] == 'fixed-extra' and detail['sequence'] == 5 and
        detail['body_sha256'] == digest(fixed.BODY) and detail['run_id_hex'] == request['N']['run_id_hex'] and
        detail['nonce_sha256'] == proof['nonce_sha256'] and
        detail['kernel_boot_identity_sha256'] == proof['kernel_boot_identity_sha256'],
        'inspection does not join its original kernel RO control intent')


def terminal(adapter, request, *, recovered):
    from s22plus_native_session_v3 import operation_steps
    item = selected(request['operation'])
    if item is handoff:
        from s22plus_debian_handoff_session_v1 import terminal as handoff_terminal
        return handoff_terminal(adapter,request,recovered=recovered)
    step = next(s for s in operation_steps(request) if s.name == item.SELECTION)
    result = dict(status='NO_PROOF', normal_return=not recovered, native_admitted=False,
        chroot_proved=False, debian_boot_proved=False)
    try:
        value = adapter.recover_step_result(step, request)
        validate_result(adapter, step, value, request)
    except (ValueError, OSError, KeyError, RawCaptureError) as error:
        result.update(evidence_error=dict(type=type(error).__name__, message=str(error)[:512]))
        if item is staged:
            from s22plus_native_staged_preflight_evidence_v1 import rederive
            try:result['diagnostic_prefix']=rederive(adapter,request)
            except (ValueError,OSError,KeyError,IndexError,RawCaptureError) as failure:
                result['diagnostic_error']=dict(type=type(failure).__name__,message=str(failure)[:512])
        if item is switch:
            from s22plus_native_observation_v3 import switch_prefix
            try:
                prefix=switch_prefix(adapter.folder(step.name),request['N'])
                records=[r['data'] for r in Journal(adapter.directory/'journal').rows()
                    if r['event']=='effect-intent' and r['data']['step']==step.name]
                require(len(records)==1 and records[0]['detail']==read(adapter.folder(step.name)/'transition-intent.json') and
                    records[0]['detail']['nonce_sha256']==prefix['nonce_sha256'] and
                    records[0]['detail']['kernel_boot_identity_sha256']==prefix['kernel_boot_identity_sha256'],
                    'partial switch proof has no original compound intent')
                result.update(prefix)
            except (ValueError,OSError,KeyError,IndexError,RawCaptureError) as failure:
                result['diagnostic_error']=dict(type=type(failure).__name__,message=str(failure)[:512])
        return result
    return dict(result, **value['proof'][item.Profile.RESULT_KEY])
