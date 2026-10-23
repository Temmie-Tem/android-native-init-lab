#!/usr/bin/env python3
"""H0 ext4 interruption evidence on fresh regular-file QEMU disks only."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PRIVATE = ROOT / 'workspace/private/outputs'
sys.path[:0] = [str(ROOT / ('workspace/public/src/scripts/' + name))
               for name in ('revalidation', 'analysis')]
import s22plus_native_root_inspect_vm_h0 as fixture
from s22plus_native_records_v3 import verify

KERNEL = PRIVATE / 's22plus-switch-root-h0-20260930-1/kernel-build/arch/arm64/boot/Image'
CASES = ('before-mount', 'after-mount', 'after-consume', 'clean-error', 'normal')
LIMIT = 256 * 1024


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(path):
    path = Path(path).absolute()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), size=path.stat().st_size, sha256=digest)


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:os.fsync(parent)
    finally:os.close(parent)


def regular(path):
    path = Path(path).absolute()
    require(path.resolve() == path and path.is_relative_to(ROOT/'workspace/private'),
            'direct private regular file required')
    st = path.lstat()
    require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, 'indirect VM disk rejected')
    return path


def run_command(args, log, timeout=60):
    with log.open('xb') as stream:
        result = subprocess.run(list(map(str, args)), stdin=subprocess.DEVNULL,
                                stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        stream.flush(); os.fsync(stream.fileno())
    log.chmod(0o400)
    require(result.returncode == 0, 'H0 command failed: '+str(log))


def superblock(path):
    with regular(path).open('rb') as stream:
        stream.seek(1024); sb = stream.read(1024)
    u16 = lambda at: int.from_bytes(sb[at:at+2], 'little')
    u32 = lambda at: int.from_bytes(sb[at:at+4], 'little')
    require(len(sb) == 1024 and u16(56) == 0xef53, 'ext4 superblock absent')
    return dict(count=u16(52), state=u16(58), recover=bool(u32(96)&4), orphan=u32(232))


def initramfs(out, helper, busybox, case, expected):
    require(case in (*CASES, 'inspect') and type(expected) is int and 0 <= expected < 65535,
            'invalid fixed probe selection')
    init = f'''#!/bin/busybox sh
PATH=/bin
export PATH
/bin/busybox --install -s /bin
mount -t proc proc /proc || exit 90
mount -t sysfs sysfs /sys || exit 91
mount -t tmpfs -o mode=0755 tmpfs /dev || exit 92
mknod /dev/console c 5 1
mknod /dev/null c 1 3
exec </dev/console >/dev/console 2>&1
for n in $(seq 1 100); do [ -e /sys/class/block/vda/dev ] && break; sleep 0.1; done
IFS=: read -r major minor </sys/class/block/vda/dev
mknod /dev/vda b "$major" "$minor" || exit 93
/probe {case} {expected}
status=$?
printf 'P458_EXIT status=%s\\n' "$status"
poweroff -f
'''.encode()
    entries = [(n, stat.S_IFDIR|0o755, b'') for n in ('bin', 'dev', 'proc', 'sys', 'mnt')]
    entries += [('init', stat.S_IFREG|0o750, init),
                ('bin/busybox', stat.S_IFREG|0o755, regular(busybox).read_bytes()),
                ('probe', stat.S_IFREG|0o500, regular(helper).read_bytes())]
    path = out/'initramfs.cpio.gz'
    with path.open('xb') as stream:
        stream.write(gzip.compress(fixture.h0.newc(entries), mtime=0))
    return path


def launch(out, disk, helper, busybox, case, expected):
    out.mkdir(mode=0o700)
    disk = regular(disk)
    archive = initramfs(out, helper, busybox, case, expected)
    serial = out/'serial.log'
    args = [fixture.QEMU/'usr/bin/qemu-system-aarch64', '-machine', 'virt',
            '-cpu', 'cortex-a76', '-m', '256', '-smp', '1', '-nic', 'none',
            '-display', 'none', '-monitor', 'none', '-serial', 'stdio', '-no-reboot',
            '-kernel', regular(KERNEL), '-initrd', archive,
            '-append', 'console=ttyAMA0 rdinit=/init panic=-1',
            '-drive', f'if=none,id=root,file={disk},format=raw,cache=writeback',
            '-device', 'virtio-blk-device,drive=root']
    save(out/'command.json', list(map(str, args)))
    kill_at = case if case in ('before-mount', 'after-mount', 'after-consume') else None
    killed = False
    with serial.open('xb') as stream:
        process = subprocess.Popen(list(map(str, args)), stdin=subprocess.DEVNULL,
            stdout=stream, stderr=subprocess.STDOUT, start_new_session=True,
            env=dict(os.environ, LD_LIBRARY_PATH=str(fixture.QEMU/'usr/lib/x86_64-linux-gnu')))
        deadline = time.monotonic()+45
        try:
            while process.poll() is None:
                require(serial.stat().st_size <= LIMIT, 'VM serial exceeded bound')
                if kill_at and f'P458_POINT {kill_at}\r\n'.encode() in serial.read_bytes():
                    os.killpg(process.pid, signal.SIGKILL); killed = True; break
                require(time.monotonic() < deadline, 'VM probe timed out')
                time.sleep(0.03)
            process.wait(timeout=5)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=5)
            stream.flush(); os.fsync(stream.fileno())
    serial.chmod(0o400)
    text = serial.read_text().replace('\r\n', '\n')
    require('P458_ERROR' not in text, 'guest probe failed')
    require(killed if kill_at else process.returncode == 0 and 'P458_EXIT status=0\n' in text
            and 'reboot: Power down' in text, 'VM terminal differs')
    rows = re.findall(r'^P458_SUPER stage=(\S+) count=(\d+) state=(\d+) recover=(\d+) orphan=(\d+) clean=(\d+)$', text, re.M)
    result = dict(case=case, killed=killed, raw=pin(serial), disk_super=superblock(disk),
                  observations=[dict(zip(('stage','count','state','recover','orphan','clean'),
                      [r[0], *map(int, r[1:])])) for r in rows],
                  admitted='P458_ADMIT\n' in text,
                  rejection=(re.findall(r'^P458_REJECT reason=(\S+)$', text, re.M) or [None])[0],
                  device_actions=0)
    save(out/'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.absolute()
    require(out.resolve() == out and out.is_relative_to(PRIVATE), 'private H0 output required')
    out.mkdir(mode=0o700, parents=False)
    os.umask(0o077)
    helper = out/'probe'
    run_command(['aarch64-linux-gnu-gcc', '-std=c11', '-O2', '-static', '-Wall', '-Wextra', '-Werror',
                 HERE/'mount_probe.c', '-o', helper], out/'compile.log')
    run_command(['file', helper], out/'file.log')
    artifact, _, _ = fixture.profile.prior_inputs()
    busybox = Path(artifact['rootfs']['path']).parent/'busybox'
    verify(artifact['rootfs'], maximum=256*1024**2)
    seed = out/'seed.ext4'
    with seed.open('xb') as stream:
        stream.truncate(64*1024*1024)
    run_command(['mke2fs', '-q', '-F', '-t', 'ext4', '-b', '4096', '-I', '256', '-m', '0',
                 '-O', 'none,has_journal,extent,filetype,sparse_super,large_file,huge_file,dir_nlink,extra_isize',
                 '-E', 'nodiscard,lazy_itable_init=0,lazy_journal_init=0', regular(seed)], out/'format.log')
    initial = superblock(seed)
    require(initial == dict(count=0,state=1,recover=False,orphan=0), 'fresh fixture fields differ')
    save(out/'inputs.json', dict(kernel=pin(KERNEL), helper=pin(helper), busybox=pin(busybox),
        sources=[pin(Path(__file__)), pin(HERE/'mount_probe.c')], seed=pin(seed), device_actions=0))
    results = []
    for case in CASES:
        folder = out/case; folder.mkdir(mode=0o700)
        disk = folder/'disk.ext4'
        run_command(['cp', '--reflink=auto', '--sparse=always', seed, disk], folder/'copy.log')
        first = launch(folder/'first', disk, helper, busybox, case, initial['count'])
        before_reobserve = pin(disk)
        second = launch(folder/'reobserve', disk, helper, busybox, 'inspect', initial['count'])
        require(pin(disk) == before_reobserve, 'read-only reobservation changed disk bytes')
        require(second['admitted'] == (case == 'before-mount'), 'unexpected re-admission')
        require(first['disk_super']['count'] == initial['count']+(case != 'before-mount'),
                'mount counter did not identify reached RW mount')
        if case == 'clean-error':
            require(second['rejection'] == 'mount-count' and not first['disk_super']['recover'],
                    'clean error-unmount did not retain consumption')
        results.append(dict(case=case,first=first,reobserve=second))
        print('PASS_MOUNT_CASE', case, second['rejection'] or 'read-only phase available', flush=True)
    save(out/'result.json', dict(status='PASS_H0_EXT4_MOUNT_FRONTIER', cases=results,
        limitation='QEMU process kill loses guest RAM; not a host power-loss or Samsung durability test',
        device_actions=0))


if __name__ == '__main__':
    main()
