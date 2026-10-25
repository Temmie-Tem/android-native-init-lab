"""Exact persistent cron configuration consumption; definition is not authority."""
import hashlib
import hmac
import json
import os
import re
import struct

import s22plus_debian_cron_v1 as previous
from s22plus_native_records_v3 import read,require,verify

ROOT=previous.ROOT
NAMESPACE='p460'
VERSION='v0.21.0-rc.0'
POLICY='docs/operations/S22PLUS_DEBIAN_CRON_CONFIG_V1.md'
HISTORY_SELECTION='post-autoboot-p459-cron-config-v1'
DOMAIN=b'S22PLUS-FYG8-DEBIAN-CRON-CONFIG-v1'
DURABLE_DOMAIN=b'S22PLUS-FYG8-DEBIAN-CRON-CONFIG-DURABLE-v1'
DURABLE_REVISION=8
SIZE=512
EXPECTED_MOUNT_COUNT=26
CREATED,RETIRED=11,12
RUNTIME_FAULTS={'config-create-partial':1,'config-done-failure':2,'config-revoke-failure':3,
    'config-no-job':4,'config-expired-retirement':5,'config-covering-bind':6,'config-proc-error':7,
    'config-orphan-cron':8,'config-unlink-sync':9,'config-manual-invocation':10,
    'config-partial-report':11,'config-done-abort-claim-failure':12}
FIRST_PHASE_FAULTS=('config-create-partial','config-covering-bind')
ROOT_CASES=('config-first-existing','config-first-report','config-second-missing','config-second-changed',
    'config-second-mode','config-second-linked','config-second-symlink','config-second-partial',
    'config-second-mtime','config-second-ctime','config-second-report','config-second-foreign')
IDLE=previous.IDLE
PRIOR=dict(path=str(ROOT/'workspace/private/outputs/s22plus-debian-cron-config-p460-h0-20261025-1/p459-expectations.json'),
    size=4539,sha256='62403c667cb4879310bc97835194eb1b215be39ebb3296ec3fc01fe132453413')
FIELDS=(('root_device',96,'Q'),('phase',104,'I'),('baseline',108,'I'),('installed_count',112,'I'),
    ('armed_ms',120,'Q'),('job_ms',128,'Q'),('hash_completed_ms',136,'Q'),
    ('daemon_pid',160,'Q'),('job_pid',168,'Q'),('parent_pid',176,'Q'),('daemon_ticks',184,'Q'),
    ('cron_size',288,'Q'),('sshd_size',296,'Q'),('config_inode',304,'Q'),('config_size',312,'Q'),
    ('config_created_ms',320,'Q'),('ancestor_count',328,'I'),('config_mtime_sec',384,'Q'),
    ('config_mtime_nsec',392,'Q'),('config_ctime_sec',400,'Q'),('config_ctime_nsec',408,'Q'))


def checked_run(run):
    require(type(run) is str and re.fullmatch('[0-9a-f]{32}',run),'cron configuration run differs')
    return run


def config_path(run):return 'etc/cron.d/s22-lab-'+checked_run(run)
def path(run):return 'var/lib/lab/s22-cron-config-'+checked_run(run)


def schedule(run):
    return ('# S22 finite configuration '+checked_run(run)+'\n').encode()+previous.SCHEDULE


def declaration(run):
    return dict(schema='s22plus-debian-cron-config-v1',config_path=config_path(run),path=path(run),size=SIZE,
        config_size=len(schedule(run)),config_sha256=hashlib.sha256(schedule(run)).hexdigest(),
        writer_phase=2,config_writer_phase=1,config_retirement_phase=2,initial_mount_count=EXPECTED_MOUNT_COUNT,
        maximum_config_creations=1,maximum_report_creations=1,maximum_config_unlinks=1,
        first_lifecycle=['stop','start','restart'],retirement_lifecycle=['stop','start'],
        workload='sha256-installed-cron-and-sshd',durable_revision=DURABLE_REVISION,
        configuration_consumption=True,configuration_retained_after_experiment=False,package_installation=False,
        idle_sha256=hashlib.sha256(IDLE).hexdigest())


def programs():return previous.programs()


def seal(run):
    data=schedule(run)
    lines=['#ifndef S22PLUS_DEBIAN_CRON_SEAL_V1_H','#define S22PLUS_DEBIAN_CRON_SEAL_V1_H',
        f'#define CR_SIZE {SIZE}U',f'#define CF_CONFIG_SIZE {len(data)}U',
        f'#define CF_CREATED {CREATED}U',f'#define CF_RETIRED {RETIRED}U',
        'static const char cr_path[]='+json.dumps(path(run))+';',
        'static const char cf_path[]='+json.dumps(config_path(run))+';',
        'static const char cr_idle[]='+json.dumps(IDLE.decode())+';',
        'static const char cf_schedule[]='+json.dumps(data.decode())+';',
        'static const uint8_t cf_config_sha[]={'+','.join(map(str,hashlib.sha256(data).digest()))+'};']
    for name,offset,kind in FIELDS:lines.append(f'#define CR_{name.upper()} {offset}U')
    # Shared ancestry code names the selected daemon using its original symbol.
    lines+=['#define CR_RESTARTED_PID CR_DAEMON_PID','#define CR_RESTARTED_TICKS CR_DAEMON_TICKS']
    for name,row in programs().items():
        lines += [f'#define CR_{name.upper()}_BYTES {row["size"]}ULL',
            f'static const uint8_t cr_{name}_sha[]={{'+','.join(map(str,bytes.fromhex(row['sha256'])))+'};']
    return ('\n'.join(lines+['#endif'])+'\n').encode()


def history():
    """P459 final producer bytes stay expectations until a new protected read."""
    record=read(verify(PRIOR));closed=read(verify(record['closed']));terminal=read(verify(record['terminal']))
    require(record['schema']=='s22plus-p459-final-producer-expectations-v1' and record['device_actions']==0 and
        record['post_android_retention_proved'] is False and record['current_clean_state_proved'] is False and
        record['expected_post_shutdown_mount_count']==record['source_mount_count']+4==EXPECTED_MOUNT_COUNT and
        closed['terminal_state']==terminal['terminal_state']=='ANDROID_CLOSED_HEALTHY' and
        closed['current_android_terminal']==record['terminal'] and closed['cron_workload_proved'] is True and
        closed['cron_exact_retention_proved'] is True,'P459 final producer expectation basis differs')
    writer=read(verify(record['writer_build']));verify(record['source']);verify(record['operation']);verify(record['source_snapshot'])
    require(writer['namespace']==previous.NAMESPACE and writer['version']==previous.VERSION and
        [(x['phase'],x['kind']) for x in record['files']]==[(p,k) for p in (1,2) for k in ('early','runtime')]+[(1,'cron')],
        'P459 expected file selection differs')
    rows=[]
    for row in record['files']:
        expected=previous.path(writer['run_id']) if row['kind']=='cron' else previous.reboot.paths(writer['run_id'],row['phase'])[row['kind']]
        data=verify(row['source'],maximum=16384).read_bytes()
        require(row['path']==expected and row['mode']==0o100600 and row['uid']==row['gid']==0 and row['nlink']==1 and
            row['size']==len(data) and row['sha256']==hashlib.sha256(data).hexdigest() and
            row['source_kind']=='AUTHENTICATED_FINAL_PRODUCER_SNAPSHOT' and row['post_android_retention_proved'] is False,
            'P459 expected bytes or metadata differs')
        rows.append({k:row[k] for k in ('path','mode','uid','gid','nlink','size','sha256','source')})
    return rows


def decode(data,*,key,run,boot,nonce,root_device,hook_sha256,baseline,first_boot,first_nonce,created):
    require(type(root_device) is dict and set(root_device)=={'major','minor'} and
        all(type(v) is int and v>=0 for v in root_device.values()),'configuration root projection differs')
    require(type(data) is bytes and len(data)==SIZE and data[:8]==b'S22CC01\0' and
        struct.unpack_from('<II',data,8)==(1,SIZE) and data[16:32]==bytes.fromhex(run) and
        data[32:64]==bytes.fromhex(boot) and data[64:96]==nonce and
        hmac.compare_digest(data[480:],hmac.digest(key,DOMAIN+b'\x01'+data[:480],'sha256')),
        'configuration job authentication or source identity differs')
    row={name:struct.unpack_from('<'+kind,data,offset)[0] for name,offset,kind in FIELDS}
    require(row['root_device']==os.makedev(root_device['major'],root_device['minor']) and
        row['phase']==2 and row['baseline']==baseline and row['installed_count']==baseline+4 and
        0<row['armed_ms']<=row['job_ms']<=row['hash_completed_ms']<300000 and
        all(1<row[n]<=2147483647 for n in ('daemon_pid','job_pid','parent_pid')) and
        row['daemon_pid']!=row['job_pid'] and row['daemon_ticks']>0 and 1<=row['ancestor_count']<=6 and
        data[256:288]==bytes.fromhex(hook_sha256),'configuration job phase, ancestry or timing differs')
    require(type(created) is dict and set(created)=={'config_inode','config_size','config_created_ms',
        'config_mtime_sec','config_mtime_nsec','config_ctime_sec','config_ctime_nsec'} and
        all(type(v) is int for v in created.values()) and all(row[k]==v for k,v in created.items()) and
        row['config_inode']>0 and row['config_size']==len(schedule(run)) and 0<row['config_created_ms']<300000 and
        row['config_mtime_sec']>0 and row['config_ctime_sec']>0 and
        0<=row['config_mtime_nsec']<1000000000 and 0<=row['config_ctime_nsec']<1000000000 and
        data[352:384]==hashlib.sha256(schedule(run)).digest() and first_boot!=boot and
        data[416:448]==bytes.fromhex(first_boot) and data[448:480]==first_nonce,
        'configuration was not the same authenticated first-boot file')
    for name,offset in (('cron',192),('sshd',224)):
        expected=programs()[name]
        require(data[offset:offset+32]==bytes.fromhex(expected['sha256']) and row[name+'_size']==expected['size'],
            'configuration job workload differs')
    require(not any(data[116:120]+data[144:160]+data[332:352]),'configuration job reserved bytes are nonzero')
    return dict(schema='s22plus-debian-cron-config-proof-v1',status='PASS_CONFIG_CONSUMPTION',**row,
        sha256=hashlib.sha256(data).hexdigest(),run_id_hex=run,kernel_boot_identity_sha256=boot,
        configuration_sha256=data[352:384].hex(),first_boot=first_boot,source_bound=True,
        configuration_consumed=True,configuration_retired=False,package_installation_proved=False)
