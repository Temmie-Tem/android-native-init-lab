"""Join automatic early, root-transition and service records from one boot."""
import base64
import hashlib
import re

import s22plus_debian_file_protocol_v1 as early
import s22plus_debian_evidence_v1 as durable
import s22plus_switch_root_protocol_v1 as transition
import s22plus_debian_autoboot_profile_v1 as profile
from s22plus_native_records_v3 import require

MAXIMUM=450000
TRACE_MAXIMUM=262144


def reboot_binding(selected,phase):
    enabled=profile.reboot_selected(selected)
    require((phase in (1,2) and type(phase) is int) if enabled else phase is None,
        'automatic evidence phase does not match selected format')
    if enabled:
        from s22plus_debian_reboot_v1 import declaration
        value=selected['reboot'];require(value==declaration(selected['run_id'],value['initial_mount_count']),
            'reboot declaration differs')
        return dict(phase=phase,initial_mount_count=value['initial_mount_count'])
    return None


def decode(early_bytes,runtime_bytes,trace_bytes,*,key,selected,ssh_boot,phase=None):
    require(type(ssh_boot) is str and re.fullmatch(
        r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',ssh_boot),'SSH boot identity differs')
    reboot=reboot_binding(selected,phase)
    run=bytes.fromhex(selected['run_id']);boot=hashlib.sha256(ssh_boot.encode()).digest()
    first=early.decode(early_bytes,key=key,run=run,expected=selected['measured'],
        module_names=[m['runtime_name'] for m in selected['modules']],storage_first=True,diagnostic=True,autoboot=True,reboot=reboot)
    require(first['pre_unmount_complete'] and first['kernel_boot_identity_sha256']==boot.hex(),
        'automatic early record crosses SSH boot')
    nonce=hashlib.sha256(early_bytes[:256]).digest()
    require(type(trace_bytes) is bytes and 0<len(trace_bytes)<=TRACE_MAXIMUM,'RAM trace exceeds bound')
    state=transition.Records(key,run,nonce,boot,selected['witness']['sha256'],
        root_readonly=False,settlement='early-children-settled',autoboot=True)
    position=0
    while position<len(trace_bytes):
        require(len(trace_bytes)-position>=16,'torn RAM trace header')
        size=int.from_bytes(trace_bytes[position+6:position+8],'little')
        require(32<=size<=1023 and position+16+size<=len(trace_bytes),'torn or oversized RAM trace body')
        state.accept(transition.frames.decode_frame(trace_bytes[position:position+16+size]));position+=16+size
    require(state.proof is not None and state.stop is None and not state.returned,'automatic root witness is incomplete')
    expected=dict(key_sha256=hashlib.sha256(key).hexdigest(),run_id_hex=run.hex(),boot=boot.hex(),
        nonce_sha256=hashlib.sha256(nonce).hexdigest(),init_sha256=selected['installed_init']['sha256'],
        hook_sha256=selected['hook']['sha256'],root_device=state.proof['root_device'])
    runtime=durable.decode(runtime_bytes,key,expected,autoboot=True,single_cpu=profile.singlecpu_selected(selected),reboot=reboot)
    require(runtime['complete_framing'] and runtime['local_runtime_proved'] and not runtime['required_check_stopped'] and
        runtime['automatic_start'] and not runtime['report_disabled'],'automatic service observation is incomplete')
    return dict(schema='s22plus-debian-autoboot-proof-v1',status='PASS_AUTOMATIC_DEBIAN_SERVICES',
        run_id_hex=run.hex(),kernel_boot_identity_sha256=boot.hex(),initial_debian_pid1=True,
        installed_debian_pid1=True,services_120_seconds=True,early=first,transition=state.projection(),runtime=runtime,
        host_start_requests=0,ssh_access_proved=False,clean_shutdown_proved=False,replay_authorized=False)


def envelope(output,*,key,selected,phase=None):
    require(type(output) is bytes and len(output)<=MAXIMUM,'SSH evidence exceeds fixed bound')
    reboot=reboot_binding(selected,phase);lines=output.splitlines()
    if reboot is None:
        require(len(lines)==6 and lines[0]==b'S22_AUTO_EVIDENCE_V1' and
            lines[-1]==b'S22_AUTO_EVIDENCE_END','SSH evidence framing differs')
        body,ssh_boot=lines[2:5],lines[1]
    else:
        cron=profile.cron_selected(selected)
        prefix=b'S22_CRON' if cron else b'S22_REBOOT'
        require(len(lines)==(7 if phase==1 else 9)+int(cron) and lines[0]==prefix+b'_EVIDENCE_V1' and
            lines[1]==f'phase={phase}'.encode() and lines[-1]==prefix+b'_EVIDENCE_END',
            'reboot SSH evidence framing/phase differs')
        body,ssh_boot=lines[3:-1],lines[2]
    require(output.endswith(b'\n'),'SSH evidence has no terminal newline')
    values=[]
    for index,line in enumerate(body):
        data=base64.b64decode(line,validate=True)
        require(0<len(data)<=(TRACE_MAXIMUM if index==2 else 16384),'SSH evidence member exceeds bound')
        values.append(data)
    proof=decode(*values[:3],key=key,selected=selected,ssh_boot=ssh_boot.decode('ascii'),phase=phase)
    if reboot is not None:
        proof.update(schema='s22plus-debian-reboot-proof-v1',phase=phase)
        if phase==2:
            prior=local_records(*values[3:5],key=key,selected=selected,
                root_device=proof['transition']['proof']['root_device'],phase=1)
            require(prior['runtime']['reboot_intent'] and
                prior['kernel_boot_identity_sha256']!=proof['kernel_boot_identity_sha256'],
                'second boot lacks first completed reboot intent or a fresh boot')
            proof['prior']=prior
        if profile.cron_selected(selected):
            require(selected.get('cron')==profile.cron_spec.declaration(selected['run_id']),
                'cron workload declaration differs')
            source=values[0] if phase==1 else values[3]
            source_boot=proof['kernel_boot_identity_sha256'] if phase==1 else prior['kernel_boot_identity_sha256']
            proof['cron']=profile.cron_spec.decode(values[-1],key=key,run=selected['run_id'],
                boot=source_boot,nonce=hashlib.sha256(source[:256]).digest(),
                root_device=proof['transition']['proof']['root_device'],hook_sha256=selected['hook']['sha256'],
                baseline=selected['reboot']['initial_mount_count'])
    return proof,values


def local_records(early_bytes,runtime_bytes,*,key,selected,root_device,phase=None):
    """Storage records alone make no live SSH or transition-receipt claim."""
    reboot=reboot_binding(selected,phase)
    run=bytes.fromhex(selected['run_id'])
    first=early.decode(early_bytes,key=key,run=run,expected=selected['measured'],
        module_names=[m['runtime_name'] for m in selected['modules']],storage_first=True,diagnostic=True,autoboot=True,reboot=reboot)
    require(first['pre_unmount_complete'],'automatic early file is incomplete')
    nonce=hashlib.sha256(early_bytes[:256]).digest()
    expected=dict(key_sha256=hashlib.sha256(key).hexdigest(),run_id_hex=run.hex(),
        boot=first['kernel_boot_identity_sha256'],nonce_sha256=hashlib.sha256(nonce).hexdigest(),
        init_sha256=selected['installed_init']['sha256'],hook_sha256=selected['hook']['sha256'],root_device=root_device)
    runtime=durable.decode(runtime_bytes,key,expected,autoboot=True,single_cpu=profile.singlecpu_selected(selected),reboot=reboot)
    require(runtime['complete_framing'] and runtime['local_runtime_proved'] and
        not runtime['required_check_stopped'] and runtime['automatic_start'] and
        not runtime['report_disabled'],'automatic local service evidence is incomplete')
    return dict(status='PASS_AUTOMATIC_LOCAL_SERVICES',early=first,runtime=runtime,
        kernel_boot_identity_sha256=first['kernel_boot_identity_sha256'],
        ssh_access_proved=False,clean_shutdown_proved=False,replay_authorized=False)
