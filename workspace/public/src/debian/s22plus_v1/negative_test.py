#!/usr/bin/env python3
"""Real ARM64 virt rejection tests, with byte-identical disks after rejection."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid
from vm_test import VM


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def debugfs(disk, command):
    result = subprocess.run(['debugfs', '-w', '-R', command, disk], capture_output=True, check=True)
    # debugfs can return zero while a requested edit failed; each mutation is
    # subsequently exercised by the real bootstrap and checked for its stage.
    return (result.stdout + result.stderr).decode()


def qualify(base, output, kernel, qemu_root, key):
    output.mkdir(mode=0o700)
    cases = {
        'wrong-uuid': 'root-uuid',
        'missing-loader': 'root-metadata',
        'init-not-executable': 'root-metadata',
        'changed-sbin-link': 'root-metadata',
        'changed-content': 'root-content',
        'mount-failure': '/newroot',
    }
    results = []
    for name, stage in cases.items():
        folder = output / name
        folder.mkdir()
        disk = folder / 'root.ext4'
        subprocess.run(['cp', '--reflink=auto', '--sparse=always', base / 'pristine.ext4', disk], check=True)
        edits = ''
        if name == 'wrong-uuid':
            changed = subprocess.run(['tune2fs', '-U', str(uuid.uuid4()), disk], capture_output=True, check=True)
            edits = (changed.stdout + changed.stderr).decode()
        elif name == 'missing-loader':
            edits = debugfs(disk, 'rm /usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1')
        elif name == 'init-not-executable':
            edits = debugfs(disk, 'set_inode_field /usr/sbin/init mode 0100644')
        elif name == 'changed-sbin-link':
            edits = debugfs(disk, 'rm /sbin') + debugfs(disk, 'symlink /sbin usr/bin')
        elif name == 'changed-content':
            raw = subprocess.check_output(['debugfs', '-R', 'blocks /usr/sbin/cron', disk], stderr=subprocess.DEVNULL)
            block = int(raw.split()[0])
            with disk.open('r+b') as stream:
                stream.seek(block * 4096 + 100)
                old = stream.read(1)
                stream.seek(-1, 1)
                stream.write(bytes([old[0] ^ 1]))
        else:
            with disk.open('r+b') as stream:
                stream.seek(1024 + 0x38)
                stream.write(b'\0\0')
        (folder / 'fixture.log').write_text(edits)
        before = sha(disk)
        vm = VM(folder, kernel, qemu_root, key)
        try:
            vm.start('rejection', disk=disk, initrd=base / 'initramfs.cpio.gz')
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                raw = vm.log.read_bytes()
                if b'BOOTSTRAP_STOP ' in raw:
                    break
                if vm.process.poll() is not None:
                    raise RuntimeError('VM exited without expected rejection')
                time.sleep(0.2)
            else:
                raise RuntimeError('rejection deadline: ' + name)
            if ('BOOTSTRAP_STOP stage=' + stage + ' ').encode() not in raw or b'BOOTSTRAP_HANDOFF' in raw:
                raise RuntimeError('wrong rejection stage: ' + name)
        finally:
            vm.stop()
        after = sha(disk)
        if before != after:
            raise RuntimeError('failed preflight modified its filesystem: ' + name)
        results.append(dict(case=name, stage=stage, disk_unchanged=True, sha256=after))
    (output / 'result.json').write_text(json.dumps(dict(
        verdict='PASS_DEBIAN_VIRT_NEGATIVE_H0', device_actions=0, cases=results), indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'output', 'kernel', 'qemu-root', 'key'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    qualify(*(getattr(args, name).resolve() for name in ('base', 'output', 'kernel', 'qemu_root', 'key')))
