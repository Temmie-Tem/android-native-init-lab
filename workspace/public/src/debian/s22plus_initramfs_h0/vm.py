#!/usr/bin/env python3
"""Exercise Debian's shell /init and real SysVinit on private ARM64 virt disks."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import h0
sys.path.insert(0, str(h0.HERE.parent / 's22plus_v1'))
from vm_test import VM as ExistingVM

QEMU_ROOT = h0.PRIVATE / 'tools/qemu-arm64-10.2.1/root'
KEY = h0.BASE / 'h0-ssh-key'
PRISTINE = h0.BASE / 'vm-final-2/pristine.ext4'


class VM(ExistingVM):
    def start(self, label, disk, initrd):
        h0.require(disk.parent == self.folder and ',' not in str(disk),
                   'only this fresh case disk may be writable')
        h0.regular(disk)
        h0.regular(initrd)
        command = [self.qemu_root / 'usr/bin/qemu-system-aarch64', '-machine', 'virt',
            '-cpu', 'cortex-a76', '-smp', '2', '-m', '1024', '-nographic',
            '-monitor', 'none', '-no-reboot', '-kernel', self.kernel,
            '-initrd', initrd, '-append',
            'console=ttyAMA0 rdinit=/init boot=h0-boot root=/dev/vda rootfstype=ext4 rw panic=-1',
            '-drive', f'if=none,id=root,file={disk},format=raw',
            '-device', 'virtio-blk-device,drive=root', '-netdev',
            f'user,id=net0,hostfwd=tcp:127.0.0.1:{self.port}-:22',
            '-device', 'virtio-net-device,netdev=net0', '-device', 'virtio-rng-device']
        self.log = self.folder / (label + '.serial.log')
        h0.publish(self.folder / (label + '.command.json'), [str(x) for x in command])
        with self.log.open('xb') as log:
            self.process = subprocess.Popen([str(x) for x in command], stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ,
                LD_LIBRARY_PATH=str(self.qemu_root / 'usr/lib/x86_64-linux-gnu')))


def make_case(out, name):
    folder = out / name
    folder.mkdir(mode=0o700)
    disk = folder / 'root.ext4'
    h0.run(['cp', '--reflink=auto', '--sparse=always', h0.regular(PRISTINE), disk], folder / 'copy.log')
    return folder, disk


def positive(out, initrd):
    folder, disk = make_case(out, 'normal')
    vm = VM(folder, h0.KERNEL, QEMU_ROOT, h0.regular(KEY))
    try:
        vm.start('boot', disk, initrd)
        vm.ready('ready')
        proof = vm.ssh('''set -eux
test "$(readlink /proc/1/exe)" = /usr/sbin/init
test "$(readlink /proc/1/root)" = /
test "$(findmnt -n -o FSTYPE /)" = ext4
test "$(findmnt -n -o FSTYPE /dev)" = tmpfs
test "$(findmnt -n -o FSTYPE /dev/pts)" = devpts
test "$(cat /run/initramfs/early-boot-id)" = "$(cat /proc/sys/kernel/random/boot_id)"
test "$(tr '\\000' ' ' </run/initramfs/early-pid1-cmdline)" = '/bin/sh /init '
test -c /dev/null
test -c /dev/pts/ptmx
if pgrep -x h0-root-check; then exit 1; fi
printf 'EARLY_TO_INSTALLED_PID1_SAME_BOOT_PASS\\n'
cat /proc/sys/kernel/random/boot_id
readlink /proc/1/exe
cat /run/lab/boot-receipt
''', 'identity').stdout
        h0.require(b'EARLY_TO_INSTALLED_PID1_SAME_BOOT_PASS\n' in proof,
                   'guest did not establish actual PID1/root result')
        serial = vm.log.read_bytes()
        for marker in (b'DEBIAN_EARLY_H0 FIRST_PID1 pid=1 ',
                       b'DEBIAN_EARLY_H0 ROOT_ADMITTED pid=1',
                       b'DEBIAN_EARLY_H0 READY_FOR_EXEC'):
            h0.require(marker in serial, 'missing actual early boot stage')
        h0.require(b'DEBIAN_EARLY_H0 STOP' not in serial, 'positive boot has a fatal stage')
        vm.ssh('/sbin/shutdown -h now', 'shutdown')
        h0.require(vm.process.wait(timeout=30) == 0 and b'reboot: Power down' in vm.log.read_bytes(),
                   'ordinary VM shutdown unproved')
    finally:
        vm.stop()
    h0.run(['e2fsck', '-fn', disk], folder / 'final-e2fsck.log')
    with disk.open('rb') as stream:
        stream.seek(1024)
        sb = stream.read(1024)
    h0.require(int.from_bytes(sb[0x3a:0x3c], 'little') == 1 and
               not (int.from_bytes(sb[0x60:0x64], 'little') & 4), 'filesystem not clean after shutdown')
    return dict(case='normal', actual_early_pid1=True, installed_pid1_same_boot=True,
                public_key_ssh=True, normal_shutdown=True, clean_ext4=True,
                serial_sha256=h0.sha(vm.log), identity_sha256=h0.sha(folder / 'identity.ssh.log'))


def negative(out, name, initrd):
    folder, disk = make_case(out, name)
    if name == 'wrong-uuid':
        h0.run(['tune2fs', '-U', str(uuid.uuid4()), disk], folder / 'fixture.log')
        expected = b'BOOTSTRAP_STOP stage=root-uuid '
    elif name == 'changed-init':
        result = subprocess.run(['debugfs', '-R', 'blocks /usr/sbin/init', disk], capture_output=True, check=True)
        (folder / 'fixture.log').write_bytes(result.stdout + result.stderr)
        h0.require(result.stdout.split() and result.stdout.split()[0].isdigit(), 'init block unlocated')
        offset = int(result.stdout.split()[0]) * 4096 + 100
        with disk.open('r+b') as stream:
            stream.seek(offset)
            before = stream.read(1)
            h0.require(len(before) == 1, 'short fixture read')
            stream.seek(offset)
            h0.require(stream.write(bytes([before[0] ^ 1])) == 1, 'fixture write failed')
        expected = b'BOOTSTRAP_STOP stage=root-content '
    else:
        raise ValueError('unselected negative case')
    before = h0.sha(disk)
    vm = VM(folder, h0.KERNEL, QEMU_ROOT, h0.regular(KEY))
    try:
        vm.start('boot', disk, initrd)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            raw = vm.log.read_bytes()
            if b'DEBIAN_EARLY_H0 STOP' in raw:
                break
            h0.require(vm.process.poll() is None, 'VM exited before expected rejection')
            time.sleep(0.2)
        else:
            raise ValueError('negative boot deadline')
        h0.require(expected in raw and b'DEBIAN_EARLY_H0 ROOT_ADMITTED' not in raw and
                   b'DEBIAN_EARLY_H0 READY_FOR_EXEC' not in raw,
                   'wrong negative stage or an unexpected continuation')
    finally:
        vm.stop()
    after = h0.sha(disk)
    h0.require(before == after, 'rejected root disk was modified')
    return dict(case=name, expected_rejection=True, disk_unchanged=True,
                disk_sha256=after, serial_sha256=h0.sha(vm.log))


def qualify(build, out):
    build = h0.private(build)
    out = h0.private(out, fresh=True)
    h0.inputs()
    record = json.loads((build / 'build.json').read_text())
    initrd = h0.regular(build / 'initramfs-a.cpio.gz')
    h0.require(record['initramfs_sha256'] == h0.sha(initrd) and record['ab_identical'],
               'unbound initramfs input')
    results = dict(scope='H0 ARM64 virt only; no FYG8 hardware or recovery proof',
                   device_actions=0, initramfs_sha256=h0.sha(initrd), kernel_sha256=h0.KERNEL_SHA,
                   pristine_sha256=h0.sha(h0.regular(PRISTINE)), cases=[])
    try:
        results['cases'].append(positive(out, initrd))
        for name in ('wrong-uuid', 'changed-init'):
            results['cases'].append(negative(out, name, initrd))
        h0.require(results['pristine_sha256'] == h0.sha(PRISTINE), 'retained input fixture changed')
        results['verdict'] = 'PASS_DEBIAN_EARLY_BOOT_VIRT_H0'
    except Exception as error:
        results.update(verdict='FAIL_H0', error=str(error))
        raise
    finally:
        h0.publish(out / 'result.json', results)
    print(results['verdict'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.build, args.output)
