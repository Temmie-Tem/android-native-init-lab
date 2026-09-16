"""One filesystem attempt in the existing attended N/E/N/A owner journal."""
from pathlib import Path

import s22plus_native_ext4_profile_v1 as fs
import s22plus_native_gpt_profile_v1 as gpt
from s22plus_native_records_v3 import Journal, canonical, clock, digest, pin, publish, read, require, verify

OPERATION = 'native-ext4'
EXPECTED = dict(zip(fs.SELECTIONS, ('PASS_PARTITION_BINDING',
    'PASS_INITIALIZED_WRITTEN_CLEAN_UNMOUNT', 'PASS_READONLY_WITNESS_CLEAN_UNMOUNT')))


def normal_steps():
    from s22plus_native_session_v3 import Step, steps
    return steps('experiment', reentry=True) + (
        Step('native-exit', 'observe', 'N', 'download'),
        Step('install-android', 'transfer', 'A'), Step('android-final', 'health', 'A'))


def profile_for(step, request):
    image = request[step.role]
    if image.get('profile') not in fs.PROFILES: return None
    if request['operation'] == 'bootstrap' and step.name == 'native-second-2': return 'filesystem-inspect'
    if request['operation'] == OPERATION:
        return {'experiment-first':'filesystem-initialize', 'native-final':'filesystem-verify'}.get(step.name, 'health')
    return 'health'


def validate_task(task):
    require(task['N']['profile'] == fs.READER_PROFILE and task['E']['profile'] == fs.INITIALIZER_PROFILE and
            set(task['operations']) <= {'bootstrap', OPERATION} and OPERATION in task['operations'] and
            task['recovery_mode'] == 'attended' and task['operation_budget'] <= 2 and
            not any(task[k] for k in ('reentry', 'hud', 'usb_reconnect')) and
            task.get('bootstrap_start') is None and
            task['N']['filesystem']['binding'] == task['E']['filesystem']['binding'] and
            task['N']['gpt'] == task['E']['gpt'] and task['N']['android_return'] == task['E']['android_return'],
            'filesystem task is outside the fixed attended reader/initializer sequence')
    for image in (task['N'], task['E']): fs.image_binding(image)
    basis = task['N']['android_return']
    require(basis['target'] == task['target'] and basis['A'] == task['A'] and
            basis['layout'] == 'proposed' and basis['total_bytes'] == 34357624832,
            'filesystem Android32 return target or capacity differs')
    terminal = read(verify(basis['source_terminal']))
    require(terminal['terminal_state'] == 'ANDROID_CLOSED_HEALTHY' and
            terminal['gpt']['status'] == 'RESERVED_ANDROID_REBOOT_VERIFIED' and
            terminal['gpt']['geometry'] == basis['geometry'], 'retained Android32 return proof differs')


def claim_path(adapter, request):
    task = adapter.configuration(request)
    # Filesystem UUID, image identity and output directory cannot renew this key.
    key = digest(canonical(dict(target=task['target'], first_lba=fs.FIRST_LBA,
        last_lba=fs.LAST_LBA, layout=request['N']['gpt']['proposal']['sha256'])))
    return adapter.root / 'workspace/private/runs/s22plus-native-ext4-v1/claims' / (key + '.json')


def claim_effect(adapter, step, request):
    require(request['operation'] == OPERATION and step.name == 'experiment-first', 'unselected format effect')
    path = claim_path(adapter, request); path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    publish(path, dict(schema='s22plus-native-ext4-claim-v1', operation=pin(adapter.directory / 'operation.json'),
                      binding=request['N']['filesystem']['binding'], boottime_ns=clock()))


def preflight(adapter, request):
    require(not claim_path(adapter, request).exists(), 'native partition already has a format attempt; replay forbidden')
    task = adapter.configuration(request); validate_task(task)
    admission = adapter.admission(request['admission'], request['N'], task)
    terminal = read(verify(admission['terminal'])); operation = read(verify(terminal['operation_record']))
    from s22plus_native_session_v3 import operation_steps
    other = type(adapter)(adapter.root, Path(terminal['operation_record']['path']).parent)
    step = operation_steps(operation)[-1]; result = other.recover_step_result(step, operation)
    other.validate_result(step, result, operation)
    require(result['proof']['filesystem']['status'] == EXPECTED['filesystem-inspect'],
            'reader bootstrap did not qualify the actual partition endpoint')


def validate_result(adapter, step, value, request):
    selection = profile_for(step, request)
    if selection not in fs.SELECTIONS: return
    proof = value['proof']; extra = proof['filesystem']
    require(extra['status'] == EXPECTED[selection] and extra['selection'] == selection,
            'native filesystem result is incomplete or negative')
    if selection != 'filesystem-initialize': return
    rows = [r['data'] for r in Journal(adapter.directory / 'journal').rows()
            if r['event'] == 'effect-intent' and r['data']['step'] == step.name]
    require(len(rows) == 1, 'format has no unique durable pre-EXEC intent')
    detail = rows[0]['detail']; selected = fs.Profile(request['E'], selection)
    require(detail['mode'] == 'fixed-extra' and detail['sequence'] == 5 and
            detail['body_sha256'] == digest(selected.BODY) and detail['run_id_hex'] == request['E']['run_id_hex'] and
            detail['nonce_sha256'] == proof['nonce_sha256'] and
            detail['kernel_boot_identity_sha256'] == proof['kernel_boot_identity_sha256'],
            'format proof does not join its original authenticated intent')
    claim = read(claim_path(adapter, request))
    require(claim['operation'] == pin(adapter.directory / 'operation.json') and
            claim['binding'] == request['N']['filesystem']['binding'], 'format claim belongs elsewhere')


def android_basis(adapter, request):
    task = adapter.configuration(request); basis = request['N']['android_return']
    require(basis['target'] == task['target'] and basis['A'] == request['A'] and basis['layout'] == 'proposed',
            'Android32 return basis differs')
    verify(basis['source_terminal'])
    fs.image_binding(request['N'])
    return dict(layout='proposed', geometry=basis['geometry'])


def terminal(adapter, request, *, recovered):
    if recovered:
        return dict(status='NO_PROOF_RECOVERED_ANDROID', format_attempted=claim_path(adapter, request).exists(),
                    fresh_boot_proved=False, initialized_filesystem_preserved='UNPROVED')
    from s22plus_native_session_v3 import operation_steps
    plan = operation_steps(request)
    proofs = {}
    for name in ('experiment-first', 'native-final'):
        step = next(s for s in plan if s.name == name)
        value = adapter.recover_step_result(step, request); validate_result(adapter, step, value, request)
        proofs[name] = value['proof']
    require(proofs['experiment-first']['kernel_boot_identity_sha256'] !=
            proofs['native-final']['kernel_boot_identity_sha256'] and
            proofs['native-final']['baseline_info']['authentication_ordinal'] == 1,
            'filesystem witness was not verified on a fresh restored native boot')
    return dict(status='PASS_INITIALIZED_PERSISTED_ANDROID_RETURN', format_attempted=True,
                fresh_boot_proved=True, witness_sha256=fs.WITNESS_SHA256,
                binding=request['N']['filesystem']['binding'])
