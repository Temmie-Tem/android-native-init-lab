"""Read the current boot's sealed, already-consumed preparation record."""
import hashlib
from pathlib import Path
import re
import struct
import s22plus_root_console_v1 as wire
import s22plus_native_root_inspect_profile_v1 as retained
from s22plus_native_records_v3 import require, verify

SCHEMA='s22plus-native-preflight-v1'
PROFILE='thermal-v3-reconnect-ufs-drain-prehandoff-v1'
SELECTION='preflight-observation'
OPERATION='preflight'
KEYS=('magic','version','header_size','log_size','stage','error','cleanup_error','complete',
    'modules_completed','children_started','children_reaped','children_executed','child_status',
    'child_error','timed_out','output_exceeded','partition_ro','super_unchanged','gpt_unchanged',
    'mounts_released','descriptors_closed','children_settled','virtual_board','root_mounts')
MEMBERS={'s22-prehandoff':0o500,'s22-prehandoff-read':0o500,'s22-fs-e2fsck':0o500,
    'rootfs.meta':0o400,'rootfs.sha256':0o400,'busybox':0o500}
prior_inputs=retained.prior_inputs


def image_binding(image):
    value=image['preflight']
    require(image['profile']==PROFILE and value['schema']=='s22plus-native-preflight-helper-h0-v1'
        and value['run_id_hex']==image['run_id_hex'] and value['artifact']==retained.ARTIFACT
        and value['ab_identical'] is True and set(value['members'])==set(MEMBERS),
        'preflight image identity differs')
    retained.prior_inputs()
    for name,mode in MEMBERS.items():
        require(value['members'][name]['mode']==mode,'preflight immutable member mode differs')
        verify(value['members'][name]['file'])
    for row in value['source_inputs']:verify(row,maximum=4*1024*1024)
    for row in value['inputs'].values():verify(row)
    return value


def decode(stdout,stderr,run_id,*,virtual=False):
    require(not stderr and 212<=len(stdout)<=212+65536,'preflight framing incomplete')
    p=dict(zip(KEYS,struct.unpack('<24I',stdout[:96]),strict=True))
    require(p['magic']==0x31504642 and p['version']==1 and p['header_size']==212
        and len(stdout)==212+p['log_size'] and stdout[96:112]==bytes.fromhex(run_id),
        'preflight record belongs elsewhere')
    boot=stdout[112:149]
    require(re.fullmatch(rb'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\n',boot),
        'preflight boot identity malformed')
    stop_raw=stdout[149:212]; stop=stop_raw.split(b'\0')[0]
    require(b'\0' in stop_raw and stop_raw==stop+b'\0'*(63-len(stop))
        and (not stop or re.fullmatch(rb'[a-z0-9/-]+',stop)), 'preflight stop framing differs')
    require(3<=p['stage']<=12 and p['complete'] in (0,1) and p['error']<=4095
        and not any(p[k] for k in ('cleanup_error','timed_out','output_exceeded'))
        and p['partition_ro'] in (0,1) and p['super_unchanged']==p['gpt_unchanged']==p['partition_ro']
        and all(p[k]==1 for k in ('mounts_released','descriptors_closed','children_settled'))
        and p['virtual_board']==int(virtual) and p['modules_completed']==(0 if virtual else 81)
        and p['children_reaped']==p['children_started']<=8 and p['children_executed']<=p['children_reaped']
        and p['root_mounts']<=2 and (not p['root_mounts'] or p['partition_ro']),
        'preflight settled/protected boundary differs')
    if p['complete']:
        require(not p['error'] and not p['child_error'] and not p['child_status'] and not stop
            and p['stage']==12 and p['children_started']==8 and p['children_executed']==6
            and p['root_mounts']==2 and p['partition_ro']==1,'preflight completion lacks exact stages')
    else:require(p['error']>0 and stop,'preflight rejection lacks its first failure')
    # The authenticated native wire carries SHA256(ascii36); its host identity
    # field hashes those 32 bytes once more. Match the existing exact semantic.
    boot_identity=hashlib.sha256(hashlib.sha256(boot[:36]).digest()).hexdigest()
    return dict(status='PASS_PREFLIGHT_OBSERVED',outcome='PREFLIGHT_COMPLETED' if p['complete'] else 'BOOTSTRAP_STOPPED',
        preflight_completed=bool(p['complete']),record=p,stop=stop.decode(),
        kernel_boot_identity_sha256=boot_identity,log=dict(size=p['log_size'],sha256=hashlib.sha256(stdout[212:]).hexdigest()),
        persistent_writes=False,installed_loader_unprivileged=True,pid1_handoff=False,
        debian_boot_proved=False)


class Profile:
    RESULT_KEY='preflight'
    MUTATES=False  # The N transfer already owns the automatic boot measurement.
    SETTLE_SECONDS=0
    OBSERVATION_SECONDS=60
    ADMISSION_SECONDS=10

    def __init__(self,image):
        self.binding=image_binding(image);self.run_id=image['run_id_hex']
        self.BODY=wire.command(('exec /s22-prehandoff-read '+self.run_id).encode(),
            cwd=b'/',timeout_ms=5000)

    def project(self,stdout,stderr,terminal,*,requested):
        result=dict(schema=SCHEMA,status='NO_PROOF',requested=requested,
            stdout=dict(size=len(stdout),sha256=hashlib.sha256(stdout).hexdigest()),
            stderr=dict(size=len(stderr),sha256=hashlib.sha256(stderr).hexdigest()))
        if not requested:return dict(result,reason='OBSERVATION_BUDGET_INSUFFICIENT')
        if terminal is None or terminal[:4]!=(5,0,0,0) or terminal[4]!=len(stdout)+len(stderr) or terminal[5]!=0:
            return dict(result,reason='PREFLIGHT_READER_INCOMPLETE')
        try:proof=decode(stdout,stderr,self.run_id)
        except (ValueError,UnicodeError,struct.error) as error:return dict(result,reason=str(error))
        return dict(result,**proof)
