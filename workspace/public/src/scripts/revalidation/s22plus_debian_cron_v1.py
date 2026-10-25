"""One packaged-cron workload and exact retained output; no device authority."""
import hashlib
import hmac
import json
import os
import re
import struct

import s22plus_debian_reboot_v1 as reboot
from s22plus_native_records_v3 import read,require,verify

ROOT=reboot.ROOT
NAMESPACE='p459'
VERSION='v0.20.0-rc.0'
POLICY='docs/operations/S22PLUS_DEBIAN_CRON_V1.md'
HISTORY_SELECTION='post-autoboot-p458-cron-v1'
DOMAIN=b'S22PLUS-FYG8-DEBIAN-CRON-v1'
SIZE=512
EXPECTED_MOUNT_COUNT=22
RUNTIME_FAULTS={'cron-no-job':1,'cron-partial-write':2,'cron-lifecycle-failure':3,
    'cron-revoke-failure':4,'cron-expired-dispatch':5,'cron-expired-parent':6,'cron-noop-service':7,
    'cron-manual-invocation':8,'cron-cached-revocation':9,'cron-start-delayed':10,
    'cron-start-timeout':11,'cron-start-identity':12}
IDLE=b'# No periodic jobs during the finite handoff observation.\n'
SCHEDULE=(b'SHELL=/bin/sh\nPATH=/usr/sbin:/usr/bin:/sbin:/bin\nMAILTO=""\n'
          b'* * * * * root exec /run/s22-debian/hook cron-job >/dev/null 2>&1\n')
PRIOR=dict(path=str(ROOT/'workspace/private/outputs/s22plus-debian-cron-p459-h0-20261025-1/p458-expectations.json'),
    size=3743,sha256='5d8d83804aa5181b0c3c8cab3adc1935842d7ad206281f1a87f82ecd61b5b6fb')
FIELDS=(('root_device',96,'Q'),('phase',104,'I'),('baseline',108,'I'),('installed_count',112,'I'),
    ('armed_ms',120,'Q'),('job_ms',128,'Q'),('hash_completed_ms',136,'Q'),('initial_pid',144,'Q'),
    ('started_pid',152,'Q'),('restarted_pid',160,'Q'),('job_pid',168,'Q'),('parent_pid',176,'Q'),
    ('restarted_ticks',184,'Q'),('cron_size',288,'Q'),('sshd_size',296,'Q'),('stop_ms',304,'Q'),
    ('start_ms',312,'Q'),('restart_ms',320,'Q'),('ancestor_count',328,'I'),
    ('initial_ticks',336,'Q'),('started_ticks',344,'Q'))
ROOT_CASES=('cron-missing','cron-changed','cron-mode','cron-linked','cron-symlink','cron-oversized',
            'cron-wrong-boot','cron-existing-first')


def path(run):
    require(type(run) is str and re.fullmatch('[0-9a-f]{32}',run),'cron run differs')
    return 'var/lib/lab/s22-cron-'+run


def declaration(run):
    return dict(schema='s22plus-debian-cron-v1',path=path(run),size=SIZE,writer_phase=1,
        initial_mount_count=EXPECTED_MOUNT_COUNT,maximum_disk_creations=1,maximum_schedule_arms=1,maximum_schedule_retirements=1,
        lifecycle=['stop','start','restart'],workload='sha256-installed-cron-and-sshd',
        persistent_configuration=False,package_installation=False,
        idle_sha256=hashlib.sha256(IDLE).hexdigest(),schedule_sha256=hashlib.sha256(SCHEDULE).hexdigest())


def programs():
    from s22plus_debian_handoff_profile_v1 import root_files
    files=root_files()
    return {name:dict(size=len(files['usr/sbin/'+name]),sha256=hashlib.sha256(files['usr/sbin/'+name]).hexdigest())
            for name in ('cron','sshd')}


def seal(run):
    lines=['#ifndef S22PLUS_DEBIAN_CRON_SEAL_V1_H','#define S22PLUS_DEBIAN_CRON_SEAL_V1_H',
           f'#define CR_SIZE {SIZE}U',f'static const char cr_path[]={json.dumps(path(run))};',
           'static const char cr_idle[]='+json.dumps(IDLE.decode())+';',
           'static const char cr_schedule[]='+json.dumps(SCHEDULE.decode())+';']
    for name,offset,kind in FIELDS:lines.append(f'#define CR_{name.upper()} {offset}U')
    for name,row in programs().items():
        lines += [f'#define CR_{name.upper()}_BYTES {row["size"]}ULL',
            f'static const uint8_t cr_{name}_sha[]={{'+','.join(map(str,bytes.fromhex(row['sha256'])))+'};']
    return ('\n'.join(lines+['#endif'])+'\n').encode()


def history():
    """Exact final producer expectations, never an asserted returned-disk read."""
    record=read(verify(PRIOR));closed=read(verify(record['closed']));terminal=read(verify(record['terminal']))
    require(record['schema']=='s22plus-p458-final-producer-expectations-v1' and record['device_actions']==0 and
        record['post_android_retention_proved'] is False and record['current_clean_state_proved'] is False and
        record['expected_post_shutdown_mount_count']==record['source_mount_count']+4==22 and
        closed['terminal_state']==terminal['terminal_state']=='ANDROID_CLOSED_HEALTHY' and
        closed['scientific_status']=='PASS_TWO_DEBIAN_BOOTS_SSH' and
        closed['current_android_terminal']==record['terminal'],'P458 producer expectation basis differs')
    writer=read(verify(record['writer_build']));verify(record['source']);verify(record['operation'])
    require(writer['namespace']==reboot.NAMESPACE and writer['version']==reboot.VERSION and
        [(x['phase'],x['kind']) for x in record['files']]==[(p,k) for p in (1,2) for k in ('early','runtime')],
        'P458 expectation selection differs')
    rows=[]
    for row in record['files']:
        raw=verify(row['source'],maximum=16384).read_bytes()
        require(row['path']==reboot.paths(writer['run_id'],row['phase'])[row['kind']] and
            row['mode']==0o100600 and row['uid']==row['gid']==0 and row['nlink']==1 and
            row['size']==len(raw) and row['sha256']==hashlib.sha256(raw).hexdigest() and
            row['source_kind']=='AUTHENTICATED_FINAL_PRODUCER_SNAPSHOT' and row['post_android_retention_proved'] is False,
            'P458 final producer expectation changed')
        rows.append({k:row[k] for k in ('path','mode','uid','gid','nlink','size','sha256','source')})
    return rows


def decode(data,*,key,run,boot,nonce,root_device,hook_sha256,baseline):
    require(type(root_device) is dict and set(root_device)=={'major','minor'} and
        all(type(v) is int and v>=0 for v in root_device.values()),'cron root device projection differs')
    require(type(data) is bytes and len(data)==SIZE and data[:8]==b'S22CR01\0' and
        struct.unpack_from('<II',data,8)==(1,SIZE) and data[16:32]==bytes.fromhex(run) and
        data[32:64]==bytes.fromhex(boot) and data[64:96]==nonce and
        hmac.compare_digest(data[480:],hmac.digest(key,DOMAIN+b'\x01'+data[:480],'sha256')),
        'cron record authentication or source identity differs')
    row={name:struct.unpack_from('<'+kind,data,offset)[0] for name,offset,kind in FIELDS}
    require(row['root_device']==os.makedev(root_device['major'],root_device['minor']) and row['phase']==1 and row['baseline']==baseline and
        row['installed_count']==baseline+2 and
        0<row['stop_ms']<=row['start_ms']<=row['restart_ms']<=row['armed_ms']<=row['job_ms']<=row['hash_completed_ms']<300000 and
        len({row[n] for n in ('initial_pid','started_pid','restarted_pid')})==3 and
        all(1<row[n]<=2147483647 for n in ('initial_pid','started_pid','restarted_pid','job_pid','parent_pid')) and
        row['job_pid']!=row['restarted_pid'] and row['initial_ticks'] and row['started_ticks'] and row['restarted_ticks'] and
        1<=row['ancestor_count']<=6 and data[256:288]==bytes.fromhex(hook_sha256),
        'cron lifecycle, ancestry or deadline differs')
    for name,offset in (('cron',192),('sshd',224)):
        expected=programs()[name]
        require(data[offset:offset+32]==bytes.fromhex(expected['sha256']) and row[name+'_size']==expected['size'],
            'cron workload digest differs')
    require(not any(data[116:120]+data[332:336]+data[352:480]),'cron reserved bytes are nonzero')
    return dict(schema='s22plus-debian-cron-proof-v1',status='PASS_CRON_WORKLOAD',**row,
        sha256=hashlib.sha256(data).hexdigest(),run_id_hex=run,kernel_boot_identity_sha256=boot,
        source_bound=True,persistent_configuration_proved=False,package_installation_proved=False)
