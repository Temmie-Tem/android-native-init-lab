"""Fixed minimal Debian sysinit program; no device action or authority."""
import hashlib
import json

import s22plus_debian_autoboot_phase_v1 as channel

NAMESPACE='p456'
VERSION='v0.18.0-rc.0'
PATH='/run/s22-debian/rc-minimal'
SCRIPTS=('inherited-ram','S01hostname.sh','S03mdev','S09urandom','S13bootmisc.sh')
LIMITS=dict(channel.SCRIPT_LIMITS,script_record_cap=2+2*len(SCRIPTS))
HISTORY_CASES=tuple(action+'-p452-'+kind for kind in ('early','runtime')
    for action in ('missing','changed','linked','mode'))
FAULTS=('minimal-missing-program','minimal-changed-program',
    'minimal-missing-dependency','minimal-script-error')


def dispatcher():
    # Every external command and packaged script closes the optional endpoint.
    # Required operations use explicit status checks; logging cannot mask them.
    return b'''#!/bin/sh
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
umask 022
[ "$#" = 1 ] && [ "$1" = S ] || exit 2
runlevel=S
previous=${PREVLEVEL:-N}
export runlevel previous
ap_count=0
ap_emit() {
    ap_count=$((ap_count + 1))
    printf '%s %s %s %s\\n' "$ap_count" "$1" "$2" "$3" 2>/dev/null >&3 || :
}
inherited_ram() {
    for item in /proc:proc /sys:sysfs /dev:tmpfs /run:tmpfs /dev/pts:devpts /dev/shm:tmpfs /run/config:configfs; do
        directory=${item%:*}
        expected=${item##*:}
        [ -d "$directory" ] && [ ! -L "$directory" ] || return 20
        actual=$(findmnt -rn -M "$directory" -o FSTYPE) || return 21
        [ "$actual" = "$expected" ] || return 22
    done
    [ -c /dev/null ] && [ ! -L /dev/null ] || return 23
    for item in random:8 urandom:9; do
        node=/dev/${item%:*}
        minor=${item##*:}
        [ ! -L "$node" ] || return 29
        if [ ! -e "$node" ]; then mknod -m 666 "$node" c 1 "$minor" || return 30; fi
        [ -c "$node" ] && [ "$(stat -c %t:%T:%u:%g:%a "$node")" = "1:$minor:0:0:666" ] || return 31
    done
    [ ! -L /run/lock ] || return 24
    if [ ! -e /run/lock ]; then mkdir -m 1777 /run/lock || return 25; fi
    [ -d /run/lock ] && [ "$(stat -c %d /run/lock)" = "$(stat -c %d /run)" ] || return 26
    chown 0:0 /run/lock && chmod 1777 /run/lock || return 27
    [ "$(stat -c %u:%g:%a /run/lock)" = 0:0:1777 ] || return 28
}
ap_emit D 0 0
ap_emit B 1 0
inherited_ram 3>&-
ap_status=$?
ap_emit E 1 "$ap_status"
[ "$ap_status" = 0 ] || exit "$ap_status"
ap_id=1
for script in /etc/init.d/hostname.sh /etc/init.d/mdev /etc/init.d/urandom /etc/init.d/bootmisc.sh; do
    ap_id=$((ap_id + 1))
    ap_emit B "$ap_id" 0
    "$script" start 3>&-
    ap_status=$?
    ap_emit E "$ap_id" "$ap_status"
    [ "$ap_status" = 0 ] || exit "$ap_status"
done
ap_emit X 0 0
exit 0
'''


def script_declaration():
    body=dispatcher()
    return dict(schema='s22plus-autoboot-minimal-declaration-v1',scripts=list(SCRIPTS),
        dispatcher=dict(size=len(body),sha256=hashlib.sha256(body).hexdigest()),
        dispatcher_path=PATH,parent_due_ms=list(channel.SCRIPT_DUE),
        required_workload=True,channel_failure_fallback=False,**LIMITS)


def script_header():
    body=dispatcher()
    lines=['/* Required minimal program; optional bounded channel. */',
        '#define AP_SCRIPT_COUNT '+str(len(SCRIPTS))+'U',
        'static const uint64_t ap_dispatcher_size='+str(len(body))+'ULL;',
        'static const uint8_t ap_dispatcher_sha[]={'+
        ','.join(map(str,hashlib.sha256(body).digest()))+'};']
    lines += [f'#define AP_{name.upper()} {value}U' for name,value in LIMITS.items()]
    lines += ['static const unsigned ap_parent_due[]={'+','.join(map(str,channel.SCRIPT_DUE))+'};']
    return ('\n'.join(lines)+'\n').encode()
