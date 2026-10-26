"""Exact Debian final Download selection; generation is H0, never authority."""
import hashlib
import json
import re
import tarfile
from dataclasses import replace

import s22plus_debian_cron_config_v1 as previous
import s22plus_fyg8_p363_return_spec as stock
from s22plus_native_records_v3 import read,require,verify

ROOT=previous.ROOT
NAMESPACE='p461'
VERSION='v0.22.0-rc.0'
POLICY='docs/operations/S22PLUS_DEBIAN_DOWNLOAD_RETURN_V1.md'
HISTORY_SELECTION='post-autoboot-p460-download-v1'
DURABLE_DOMAIN=b'S22PLUS-FYG8-DEBIAN-DOWNLOAD-DURABLE-v1'
DURABLE_REVISION=9
EXPECTED_MOUNT_COUNT=30
SIZE=previous.SIZE
IDLE=previous.IDLE
RUNTIME_FAULTS=previous.RUNTIME_FAULTS
ROOT_CASES=previous.ROOT_CASES
FIRST_PHASE_FAULTS=previous.FIRST_PHASE_FAULTS
config_path,path,schedule=previous.config_path,previous.path,previous.schedule
programs,seal,decode=previous.programs,previous.seal,previous.decode
PRIOR=dict(path=str(ROOT/'workspace/private/outputs/s22plus-debian-download-p461-h0-20261026-1/p460-expectations.json'),
    size=4563,sha256='3338c6203f970718b075b743107d24f622dc9e93221e9f791fab286eb8478ac2')
ASSET_NAMES=('rc-return',*(('return-'+name) for name,_,_,_ in stock.MODULES))


def ramdisk_additions(selected):
    from s22plus_debian_package_v1 import NAMESPACE as package_namespace, VERSION as package_version
    versions={NAMESPACE:VERSION,package_namespace:package_version}
    if selected['namespace'] not in versions:return {}
    require(selected['version']==versions[selected['namespace']] and selected['download_return']==return_declaration(),
        'unselected Download RAM additions')
    return {'s22-debian-'+name:0o100400 if name.endswith('.ko') else 0o100500 for name in ASSET_NAMES}


def repack_entries(entries,additions,payloads):
    if not additions:return []
    prototype=next(e for e in entries if e.name=='s22-debian-qualify')
    inode=max(e.inode for e in entries)+1
    return [replace(prototype,encoded_name=name,name=name,inode=inode+i,mode=mode,
        uid=0,gid=0,nlink=1,mtime=0,data=payloads[name]) for i,(name,mode) in enumerate(additions.items())]


def declaration(run):
    return dict(previous.declaration(run),initial_mount_count=EXPECTED_MOUNT_COUNT,
        durable_revision=DURABLE_REVISION)


def return_declaration():
    return dict(schema='s22plus-debian-download-return-v1',ordinary_phase=1,download_phase=2,
        ordinary_restart_calls=1,download_restart_calls=1,alternate_control=False,
        final_root_superblock_readonly=True,preparation='late-k06-after-sysv-cleanup',
        modules=[dict(name=name,size=size,sha256=sha,parameters=params) for name,size,sha,params in stock.MODULES],
        registry_window_ms=5000,host_window_origin='original-final-control-intent',
        original_A_transfers=1,attended=True,automatic_failure_recovery=False)


def validate_vm_return(serial):
    controls=re.findall(rb'^S22_DOWNLOAD_VM_CONTROL phase=(\d+) mode=([^\r\n]+)\r?$',serial,re.M)
    stages=re.findall(rb'^S22_DOWNLOAD_STAGE phase=(\d+) stage=(\d+) errno=(-?\d+)\r?$',serial,re.M)
    require(controls==[(b'1',b'ordinary'),(b'2',b'download-substituted-poweroff')] and
        stages==[(str(p).encode(),str(s).encode(),b'0') for p,ss in ((1,(1,2,50)),(2,(1,2,40,50))) for s in ss] and
        b'S22_DOWNLOAD_PARK' not in serial,'fixed final RAM helper did not exclusively own both VM controls')


def history():
    record=read(verify(PRIOR));closed=read(verify(record['closed']));terminal=read(verify(record['terminal']))
    require(record['schema']=='s22plus-p460-final-producer-expectations-v1' and record['device_actions']==0 and
        record['post_android_retention_proved'] is False and record['current_clean_state_proved'] is False and
        record['expected_post_shutdown_mount_count']==record['source_mount_count']+4==EXPECTED_MOUNT_COUNT and
        closed['terminal_state']==terminal['terminal_state']=='ANDROID_CLOSED_HEALTHY' and
        closed['current_android_terminal']==record['terminal'] and
        terminal['debian_autoboot']['cron_configuration_preserved'] is True and
        terminal['debian_autoboot']['cron_configuration_consumed'] is True and
        terminal['debian_autoboot']['cron_configuration_retired'] is True,
        'P460 final producer/retirement basis differs')
    writer=read(verify(record['writer_build']));verify(record['source']);verify(record['operation']);verify(record['source_snapshot'])
    require(writer['namespace']==previous.NAMESPACE and writer['version']==previous.VERSION and
        [(x['phase'],x['kind']) for x in record['files']]==[(p,k) for p in (1,2) for k in ('early','runtime')]+[(2,'cron')],
        'P460 expected file selection differs')
    rows=[]
    for row in record['files']:
        expected=previous.path(writer['run_id']) if row['kind']=='cron' else previous.previous.reboot.paths(writer['run_id'],row['phase'])[row['kind']]
        data=verify(row['source'],maximum=16384).read_bytes()
        require(row['path']==expected and row['mode']==0o100600 and row['uid']==row['gid']==0 and row['nlink']==1 and
            row['size']==len(data) and row['sha256']==hashlib.sha256(data).hexdigest() and
            row['source_kind']=='AUTHENTICATED_FINAL_PRODUCER_SNAPSHOT' and row['post_android_retention_proved'] is False,
            'P460 expected bytes or metadata differs')
        rows.append({k:row[k] for k in ('path','mode','uid','gid','nlink','size','sha256','source')})
    return rows


def dispatcher():
    from s22plus_debian_handoff_profile_v1 import prior_inputs
    artifact,_,_=prior_inputs()
    with tarfile.open(verify(artifact['rootfs'],maximum=256*1024**2),'r:*') as archive:
        member=archive.getmember('usr/lib/init/rc')
        require(member.isreg() and member.uid==member.gid==0 and 0<member.size<32768,'packaged rc input differs')
        with archive.extractfile(member) as source:data=source.read(member.size+1)
    require(len(data)==member.size and data.count(b'\t\t\t\t"$script" "$action"\n')==1 and
        data.endswith(b'trap - EXIT # Disable emergency handler\n\nexit 0\n'),'packaged serial rc shape differs')
    data=data.replace(b'\t\t\t\t"$script" "$action"\n',b'''                case "$script" in
                  /etc/rc6.d/K06reboot) exec /run/s22-debian/hook return-final ;;
                  *) "$script" "$action" ;;
                esac
''')
    # Any unexpected dispatcher completion has no reboot/sulogin fall-through.
    return data[:-len(b'exit 0\n')]+b'exec /run/s22-debian/hook return-park\n'


def assets(values):
    result=dict(values);text=result['inittab']
    for old,new in ((b'l6:6:wait:/etc/init.d/rc 6\n',b'l6:6:wait:/run/s22-debian/rc-return 6\n'),
                    (b'z6:6:respawn:/sbin/sulogin --force\n',b'z6:6:respawn:/run/s22-debian/hook return-park\n')):
        require(text.count(old)==1,'packaged terminal runlevel differs');text=text.replace(old,new)
    result['inittab']=text;result['rc-return']=dispatcher()
    result.update({'return-'+name:data for name,data in stock.module_bytes().items()})
    qualify=result['qualify']
    old=b''' shutdown)
  /run/s22-debian/hook shutdown-intent
  rb_evidence
  /sbin/shutdown -h now
  printf 'DEBIAN_SHUTDOWN_REQUEST_ACCEPTED\\n'
  ;;
'''
    new=b''' download)
  /run/s22-debian/hook download-intent
  rb_evidence
  /sbin/shutdown -r now
  printf 'DEBIAN_DOWNLOAD_REQUEST_ACCEPTED\\n'
  ;;
'''
    require(qualify.count(old)==1,'final forced control differs')
    result['qualify']=qualify.replace(old,new)
    return result


def return_header():
    lines=['#ifndef S22PLUS_DEBIAN_DOWNLOAD_SEAL_V1_H','#define S22PLUS_DEBIAN_DOWNLOAD_SEAL_V1_H',
        'struct dl_module {const char *path,*params; uint64_t size; uint8_t sha[32];};',
        'static const struct dl_module dl_modules[]={']
    for name,size,sha,params in stock.MODULES:
        lines.append('{'+json.dumps('/run/s22-debian/return-'+name)+','+json.dumps(params)+','+
            str(size)+'ULL,{'+','.join(map(str,bytes.fromhex(sha)))+'}},')
    return ('\n'.join(lines+['};','#endif'])+'\n').encode()
