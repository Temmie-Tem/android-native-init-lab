#!/usr/bin/env python3
"""Real ARM64 H0 execution of the installed-only bootstrap on retained virt roots."""
import argparse
import gzip
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[4]
sys.path[:0] = [str(HERE), str(BASE), str(ROOT / 'workspace/public/src/scripts/analysis'),
               str(ROOT / 'workspace/public/src/scripts/revalidation')]
import h0
import installed_prepare
import prepare
import vm_install_test as prior_vm
import s22plus_native_ext4_profile_v1 as fs
from s22plus_native_records_v3 import pin, read, require, verify

P401 = ROOT / 'workspace/private/outputs/s22plus-debian-device-prep-20260921-1'
VIRT = P401 / 'vm-2'
ARTIFACT = P401 / 'artifact-7'
VM_ARTIFACT = P401 / 'artifact-3'
KERNEL = ROOT / 'workspace/private/outputs/s22plus-debian-bootstrap-h0-20260921-1/kernel-build/arch/arm64/boot/Image'
QEMU = ROOT / 'workspace/private/tools/qemu-arm64-10.2.1/root'


def initramfs(out, run_id):
    overlay = installed_prepare.shutdown_overlay(out, VIRT, run_id=run_id)
    command = ['aarch64-linux-gnu-gcc', '-std=gnu11', '-Os', '-static', '-fno-ident',
        '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
        '-DS22_DEBIAN_DEVICE', '-DS22_DEBIAN_VIRT_TEST', '-I', str(out), '-I', str(VIRT),
        str(BASE / 'handoff.c')]
    legacy = out / 'init-legacy'
    h0.run([*command, '-o', legacy], out / 'legacy-compile.log')
    require(legacy.read_bytes() == (VIRT / 'init').read_bytes(),
            'retained P401 virtual installer changed')
    selected = out / 'init-installed'
    h0.run([*command, '-DS22_DEBIAN_INSTALLED_ONLY', '-o', selected],
           out / 'installed-compile.log')
    rows = prepare.packaging.shared.boot.parse_newc(gzip.decompress((VIRT / 'initramfs.cpio.gz').read_bytes()))
    remove = {'rootfs.tar.xz', 'install.meta', 'install.sha256'}
    require(remove <= {row.name for row in rows}, 'retained virtual archive members differ')
    entries = [(row.name, row.mode, selected.read_bytes() if row.name == 'init' else row.data)
        for row in rows if row.name not in remove]
    entries.append(('p404-lab-qualify', stat.S_IFREG | 0o500, overlay.read_bytes()))
    require(all(row.uid == row.gid == 0 and row.nlink == 1 for row in rows),
            'virtual ramdisk metadata differs')
    (out / 'initramfs.cpio.gz').write_bytes(gzip.compress(h0.newc(entries), mtime=0))
    return pin(selected), remove


def cloned_disk(source, target):
    subprocess.run(['cp', '--reflink=auto', '--sparse=always', source, target], check=True)
    require(stat.S_ISREG(target.lstat().st_mode) and target.lstat().st_nlink == 1 and
            target.stat().st_size == source.stat().st_size, 'VM disk copy differs')


def installed_disk(out):
    # The retained completed VM run has already made its sole shutdown request.
    # P401 made no such request on Samsung; remove only that VM receipt from a
    # private clone so the fixed P404 request can be exercised once.
    native = out / 'native-installed.ext4'
    cloned_disk(VIRT / 'after.ext4', native)
    path = '/var/lib/lab/shutdown-start'
    h0.run(['debugfs', '-R', 'stat ' + path, native], out / 'prior-shutdown-stat.log')
    require(b'Inode:' in (out / 'prior-shutdown-stat.log').read_bytes(),
            'retained VM disk has no prior shutdown receipt')
    h0.run(['debugfs', '-w', '-R', 'rm ' + path, native], out / 'prior-shutdown-remove.log')
    h0.run(['e2fsck', '-fn', native], out / 'prior-shutdown-check.log')
    binding = read(verify(read(ARTIFACT / 'artifact.json')['filesystem_binding']))
    gpt = verify(binding['expected_gpt']).read_bytes()
    disk = out / 'root.ext4'
    total = 62_305_280 * 4096
    with disk.open('xb') as stream:
        stream.truncate(total)
        stream.write(gpt[:6 * 4096])
        stream.seek(total - 9 * 4096)
        stream.write(gpt[6 * 4096:])
    prior_vm.sparse_copy(native, disk, offset=fs.FIRST_LBA * 4096)
    return disk


def empty_disk(out):
    binding = read(verify(read(ARTIFACT / 'artifact.json')['filesystem_binding']))
    disk = out / 'empty-root.ext4'
    gpt = verify(binding['expected_gpt']).read_bytes()
    total = 62_305_280 * 4096
    with disk.open('xb') as stream:
        stream.truncate(total)
        stream.write(gpt[:6 * 4096])
        stream.seek(total - 9 * 4096)
        stream.write(gpt[6 * 4096:])
    prior_vm.sparse_copy(VIRT / 'native.ext4', disk, offset=fs.FIRST_LBA * 4096)
    return disk


def qualify(out):
    out = out.absolute()
    require(out.is_relative_to(ROOT / 'workspace/private/outputs') and
            out.resolve() == out and not out.exists(), 'fresh private VM output required')
    require(read(VIRT / 'result.json')['verdict'] == 'PASS_H0_ARM64_INSTALL_REBOOT_PERSIST_SHUTDOWN',
            'retained virtual installed root lacks its completed qualification')
    require(read(VIRT / 'build.json')['artifact_source'] == pin(VM_ARTIFACT / 'artifact.json'),
            'virtual installed disk belongs to another root identity')
    out.mkdir(mode=0o700)
    run_id = uuid.uuid4().hex
    init, remove = initramfs(out, run_id)
    disk = installed_disk(out)
    before = prior_vm.sparse_digest(disk)
    vm = prior_vm.InstallVM(out, KERNEL, QEMU, VM_ARTIFACT / 'client-key')
    (out / 'known_hosts').write_text(
        f'[127.0.0.1]:{vm.port} {(VM_ARTIFACT / "host-key.pub").read_text().strip()}\n')
    try:
        vm.start('installed-root')
        result = vm.ready('installed-health')
        body = result.stdout
        require(body.startswith(('S22PLUS_FYG8_DEBIAN_V1 ' + read(VM_ARTIFACT / 'artifact.json')['run_id'] + '\n').encode())
            and body.endswith(b'DEBIAN_HEALTH_PASS\n') and
            b'pid1_exe=/usr/sbin/init\n' in body and b'pid1_root=/\n' in body and
            b'BOOTSTRAP_HANDOFF pid=1 children=0 backend=h0-virt-installer\n' in body and
            body.count(installed_prepare.boot_identity(run_id).encode()) == 1 and
            b'DEBIAN_INSTALL_INTENT_DURABLE' not in body and b'DEBIAN_INSTALL_COMPLETE' not in body,
            'installed-only Debian PID 1 proof or no-install result differs')
        match = re.findall(rb'^boot_count=([1-9][0-9]*)$', body, re.M)
        require(len(match) == 1 and int(match[0]) >= 2, 'retained installed root did not advance its boot count')
        shutdown = vm.ssh('shutdown', 'installed-shutdown', check=False)
        import s22plus_debian_first_boot_v1 as owner
        owner.control_projection(shutdown.handle, 'shutdown', '127.0.0.1')
        require(vm.process.wait(timeout=60) == 0, 'ordinary Debian shutdown did not finish')
        h0.write_json(out / 'positive.json', dict(status='PASS_INSTALLED_PID1_H0',
            candidate_run_id=run_id, candidate_identity=installed_prepare.boot_identity(run_id),
            boot_count=int(match[0]), installed_root_source=pin(VIRT / 'result.json'),
            init=init, before=before, health_capture=pin(result.handle.receipt_path),
            no_install=True, return_status='SHUTDOWN_COMPLETED',
            shutdown_overlay=pin(out / 'p404-lab-qualify'),
            scope='VIRT_NOT_SAMSUNG',device_actions=0))
    finally:
        vm.stop()
    empty = empty_disk(out)
    before_empty = prior_vm.sparse_digest(empty)
    negative = prior_vm.InstallVM(out, KERNEL, QEMU, VM_ARTIFACT / 'client-key')
    try:
        negative.start('empty-reject',disk=empty)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            log = negative.log.read_bytes()
            if b'BOOTSTRAP_STOP stage=installed-root-not-complete ' in log: break
            require(negative.process.poll() is None and b'BOOTSTRAP_HANDOFF' not in log and
                    b'DEBIAN_INSTALL_INTENT_DURABLE' not in log,
                    'empty root reached installed handoff or installation')
            time.sleep(1)
        else: raise TimeoutError('empty installed-root rejection was not observed')
    finally:
        negative.stop()
    after_empty = prior_vm.sparse_digest(empty)
    require(before_empty == after_empty, 'empty root negative changed backing disk')
    result = dict(schema='s22plus-debian-installed-boot-vm-h0-v1',
        verdict='PASS_H0_ARM64_INSTALLED_BOOT_AND_EMPTY_REJECTION',
        positive=pin(out / 'positive.json'), negative_disk=before_empty,
        omitted_members=sorted(remove), scope='VIRT_NOT_SAMSUNG', device_actions=0)
    h0.write_json(out / 'result.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(qualify(parser.parse_args().output)))
