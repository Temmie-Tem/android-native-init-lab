"""Native-first installed Debian PID1/basic-access scope; no live authority."""
import hashlib
import functools
import json
from pathlib import Path
import re
import tarfile

import s22plus_native_root_inspect_profile_v1 as inspection
import s22plus_native_staged_preflight_profile_v1 as staged
import s22plus_switch_root_profile_v1 as switch
from s22plus_native_records_v3 import read,require,verify

ROOT=inspection.ROOT
SCHEMA='s22plus-debian-handoff-v2'
PROFILE='thermal-v3-reconnect-ufs-drain-debian-handoff-v2'
OPERATION=SELECTION='debian-handoff'
prior_inputs=inspection.prior_inputs
P410=ROOT/'workspace/private/outputs/s22plus-debian-handoff-h0-20260930-1/prepared-2/task'
PREVIOUS_CLOSE=dict(path=str(P410/'closed.json'),size=3814,
    sha256='848e6425eaceffda91ebfa8498f9b6a7bc99c2680317a33b52c94c655bbf7410')
INIT='usr/sbin/init'
INITTAB='etc/inittab'
QUALIFY='usr/local/sbin/lab-qualify'
HOOK='/run/s22-debian/hook'
STATE='/run/s22-debian/state'
SECONDS=3600
MUTABLE=(
    ('var/log/wtmp',0o100664,43,0,65536,True,False),
    ('var/lib/lab',0o40755,0,0,0,False,False),
    ('var/lib/lab/boot-count',0o100644,0,2,2,False,True),
    ('var/lib/urandom/random-seed',0o100600,0,32,32,False,False),
    ('var/log/dmesg',0o100640,4,0,1048576,False,False),
    *((name,0o100644,0,0,133248,False,False) for name in
        ('var/log/messages','var/log/messages.0','var/log/messages.1','var/log/messages.2')),
)


def image_binding(image):
    require(image['profile']==PROFILE,'unselected Debian handoff image')
    root=inspection.image_binding(dict(image,profile=inspection.PROFILE,root_inspection=image['root_admission']))
    value=image['debian_handoff']
    require(set(value)=={'prepare','witness','busybox','checker','assets','installed_init','seconds','request',
        'init_request','start_request','release_request','root_readonly','installed_exec','persistent_writes','helpers_result'} and
        value['seconds']==300 and value['request']==37 and value['init_request']==39 and value['release_request']==40 and
        value['start_request']==41 and value['root_readonly'] is False and value['installed_exec'] is True and value['persistent_writes'] is True and
        value['prepare']==root['helper'] and value['busybox']['size']==1975064 and
        value['busybox']['sha256']==switch.BUSYBOX_SHA256 and value['checker']==staged.execution_binding()['checker'] and
        set(value['assets'])=={'hook','inittab','qualify','defer-usb','crontab','usb'},'Debian handoff scope differs')
    init,assets=payloads()
    require(value['installed_init']==dict(size=len(init),sha256=hashlib.sha256(init).hexdigest()),'installed init differs')
    for name,data in assets.items():require(verify(value['assets'][name]).read_bytes()==data,'RAM overlay differs')
    for name in ('prepare','witness','busybox','checker','helpers_result'):verify(value[name])
    verify(value['assets']['hook'])
    previous=read(verify(PREVIOUS_CLOSE))
    require(previous['terminal_state']=='ANDROID_CLOSED_HEALTHY','P410 is not closed healthy')
    return root


def root_files():
    """Fixed immutable regular files from the hash-pinned retained tar.

    Do not import the first-boot qualifier/owner into the live V3 closure.
    The full archive grammar/comparison remains the existing H0 admission.
    """
    artifact,_,_=prior_inputs();result={}
    with tarfile.open(verify(artifact['rootfs'],maximum=256*1024*1024),'r:*') as archive:
        for name in (INIT,INITTAB,QUALIFY,'usr/sbin/cron','usr/sbin/sshd'):
            member=archive.getmember(name)
            require(member.isreg() and member.uid==member.gid==0 and 0<member.size<=2*1024*1024,
                'retained Debian input is not a bounded root-owned regular file')
            with archive.extractfile(member) as stream:result[name]=stream.read(member.size+1)
            require(len(result[name])==member.size,'short retained Debian input')
    return result


@functools.lru_cache(maxsize=2)
def payloads(*,virt=False):
    members=root_files()
    init=members[INIT];inittab=members[INITTAB];qualify=members[QUALIFY]
    require(inittab.count(b'si::sysinit:/etc/init.d/rcS\n')==1 and b's22-debian/hook' not in inittab,
        'retained SysVinit ordering differs')
    require(inittab.count(b'l2:2:wait:/etc/init.d/rc 2\n')==1,'retained runlevel order differs')
    inittab=inittab.replace(b'si::sysinit:/etc/init.d/rcS\n',
        b'dh::sysinit:/run/s22-debian/hook init\nsi::sysinit:/run/s22-debian/hook rcs\n')
    inittab=inittab.replace(b'l2:2:wait:/etc/init.d/rc 2\n',
        b'l2:2:wait:/run/s22-debian/hook runlevel\n')
    # Keep exact retained health, but select only health and one shutdown.
    start=qualify.index(b' workload)\n');end=qualify.index(b' shutdown)\n')
    require(start<end and qualify.count(b'test "$(cat /var/lib/lab/boot-count)" = 2')==1,
        'retained fixed command grammar differs')
    qualify=qualify[:start]+qualify[end:]
    qualify=qualify.replace(b'test "$(cat /var/lib/lab/boot-count)" = 2',
        b'test "$(cat /var/lib/lab/boot-count)" -ge 1')
    require(b' workload)' not in qualify and b' reboot)' not in qualify,'unselected Debian command retained')
    values={'inittab':inittab,'qualify':qualify,
        'defer-usb':b'#!/bin/sh\n# USB belongs to the finite post-rc2 observer until release.\ntest "$1" = start || exit 0\n',
        'crontab':b'# No periodic jobs during the finite handoff observation.\n',
        'usb':(ROOT/'workspace/public/src/debian/s22plus_v1/device/lab-usb-adopt-g1').read_bytes()}
    if virt:
        values['usb']=b'''#!/bin/sh
set -eu
test "$1" = start || exit 0
. /etc/default/lab-usb
ip link set lo up
ip link set eth0 name usb0
ip address add "$device_address" dev usb0
ip link set usb0 up
'''
    return init,values


def mutable_header():
    return ('struct dh_mutable { const char *path; unsigned mode,gid; uint64_t minimum,maximum; unsigned archive,count; };\n'+
        'static const struct dh_mutable dh_mutable[]={\n'+''.join(
            '{'+json.dumps(path)+f',{mode}U,{gid}U,{minimum}ULL,{maximum}ULL,{int(archive)}U,{int(count)}U'+'},\n'
            for path,mode,gid,minimum,maximum,archive,count in MUTABLE)+'};\n')


def header(namespace,version,run,*,virt=False):
    require(re.fullmatch(r'p[0-9]{3,6}',namespace) and
        re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.]+)?',version) and
        re.fullmatch(r'[0-9a-f]{32}',run),'Debian candidate identity differs')
    init,assets=payloads(virt=virt);members=root_files()
    marker=f'BOOTSTRAP_CANDIDATE {namespace} {version} {run}\n'
    return ('#ifndef S22_DEBIAN_HANDOFF_SEAL_V1_H\n#define S22_DEBIAN_HANDOFF_SEAL_V1_H\n'+
        mutable_header()+
        f'static const uint64_t dh_init_size={len(init)}ULL;\n'+
        'static const uint8_t dh_init_sha256[]={'+','.join(map(str,hashlib.sha256(init).digest()))+'};\n'+
        f'static const uint64_t dh_usb_size={len(assets["usb"])}ULL;\n'+
        'static const uint8_t dh_usb_sha256[]={'+','.join(map(str,hashlib.sha256(assets['usb']).digest()))+'};\n'+
        'static const char dh_boot_identity[]='+json.dumps(marker)+';\n'+''.join(
            f'static const uint64_t dh_{name}_size={len(members["usr/sbin/"+name])}ULL;\n'+
            'static const uint8_t dh_'+name+'_sha256[]={'+','.join(map(str,hashlib.sha256(members['usr/sbin/'+name]).digest()))+'};\n'
            for name in ('cron','sshd'))+'#endif\n').encode()


class Profile:
    RESULT_KEY='debian_handoff'
    MUTATES=True
    OBSERVATION_SECONDS=360
