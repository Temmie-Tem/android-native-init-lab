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
SCHEMA='s22plus-debian-handoff-v1'
PROFILE='thermal-v3-reconnect-ufs-drain-debian-handoff-v1'
OPERATION=SELECTION='debian-handoff'
prior_inputs=inspection.prior_inputs
P409=ROOT/'workspace/private/outputs/s22plus-switch-root-h0-20260930-1/prepared-2/task'
PREVIOUS_CLOSE=dict(path=str(P409/'closed.json'),size=3676,
    sha256='50c44354e4f1d21c88ab4ccd1b2399dce32e4996f4f3e1c3b44de8e027780194')
INIT='usr/sbin/init'
INITTAB='etc/inittab'
QUALIFY='usr/local/sbin/lab-qualify'
HOOK='/run/s22-debian/hook'
STATE='/run/s22-debian/state'
SECONDS=3600


def image_binding(image):
    require(image['profile']==PROFILE,'unselected Debian handoff image')
    root=inspection.image_binding(dict(image,profile=inspection.PROFILE,root_inspection=image['root_admission']))
    value=image['debian_handoff']
    require(set(value)=={'prepare','witness','busybox','checker','assets','installed_init','seconds','request',
        'init_request','release_request','root_readonly','installed_exec','persistent_writes','helpers_result'} and
        value['seconds']==300 and value['request']==37 and value['init_request']==39 and value['release_request']==40 and
        value['root_readonly'] is False and value['installed_exec'] is True and value['persistent_writes'] is True and
        value['prepare']==root['helper'] and value['busybox']['size']==1975064 and
        value['busybox']['sha256']==switch.BUSYBOX_SHA256 and value['checker']==staged.execution_binding()['checker'] and
        set(value['assets'])=={'hook','inittab','qualify'},'Debian handoff scope differs')
    init,assets=payloads()
    require(value['installed_init']==dict(size=len(init),sha256=hashlib.sha256(init).hexdigest()),'installed init differs')
    for name,data in assets.items():require(verify(value['assets'][name]).read_bytes()==data,'RAM overlay differs')
    for name in ('prepare','witness','busybox','checker','helpers_result'):verify(value[name])
    verify(value['assets']['hook'])
    previous=read(verify(PREVIOUS_CLOSE))
    require(previous['terminal_state']=='ANDROID_CLOSED_HEALTHY','P409 is not closed healthy')
    return root


def root_files():
    """Only three immutable regular files from the hash-pinned retained tar.

    Do not import the first-boot qualifier/owner into the live V3 closure.
    The full archive grammar/comparison remains the existing H0 admission.
    """
    artifact,_,_=prior_inputs();result={}
    with tarfile.open(verify(artifact['rootfs'],maximum=256*1024*1024),'r:*') as archive:
        for name in (INIT,INITTAB,QUALIFY):
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
    inittab=inittab.replace(b'si::sysinit:/etc/init.d/rcS\n',
        b'dh::sysinit:/run/s22-debian/hook\nsi::sysinit:/etc/init.d/rcS\n')
    # Keep exact retained health, but select only health and one shutdown.
    start=qualify.index(b' workload)\n');end=qualify.index(b' shutdown)\n')
    require(start<end and qualify.count(b'test "$(cat /var/lib/lab/boot-count)" = 2')==1,
        'retained fixed command grammar differs')
    qualify=qualify[:start]+qualify[end:]
    qualify=qualify.replace(b'test "$(cat /var/lib/lab/boot-count)" = 2',
        b'test "$(cat /var/lib/lab/boot-count)" -ge 1')
    require(b' workload)' not in qualify and b' reboot)' not in qualify,'unselected Debian command retained')
    values={'inittab':inittab,'qualify':qualify}
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


def header(namespace,version,run,*,virt=False):
    require(re.fullmatch(r'p[0-9]{3,6}',namespace) and
        re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.]+)?',version) and
        re.fullmatch(r'[0-9a-f]{32}',run),'Debian candidate identity differs')
    init,_=payloads(virt=virt)
    marker=f'BOOTSTRAP_CANDIDATE {namespace} {version} {run}\n'
    return (f'static const uint64_t dh_init_size={len(init)}ULL;\n'+
        'static const uint8_t dh_init_sha256[]={'+','.join(map(str,hashlib.sha256(init).digest()))+'};\n'+
        'static const char dh_boot_identity[]='+json.dumps(marker)+';\n').encode()


class Profile:
    RESULT_KEY='debian_handoff'
    MUTATES=True
    OBSERVATION_SECONDS=360
