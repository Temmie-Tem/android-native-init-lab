#!/usr/bin/env python3
"""Real ARM64 installer lifecycle on an exact-geometry private virt disk.

Only board/module/sysfs discovery and the network device are substituted.
The sealed GPT, ARM64 ioctls, installer, archive fd, markers and handoff run.
"""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import stat
import subprocess
import sys
import time
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prepare
from prepare import BASE, ROOT, h0, pin, read, verify
import s22plus_native_ext4_profile_v1 as fs
import vm_test
import device_action_raw_capture_v1 as raw
import s22plus_debian_first_boot_v1 as owner_protocol


def sparse_copy(source, destination, *, offset=0):
    size = source.stat().st_size
    src, dst = os.open(source, os.O_RDONLY), os.open(destination, os.O_WRONLY)
    try:
        current = 0
        while current < size:
            try:
                start = os.lseek(src, current, os.SEEK_DATA)
            except OSError as error:
                if error.errno == errno.ENXIO:
                    break
                raise
            end = os.lseek(src, start, os.SEEK_HOLE)
            while start < end:
                data = os.pread(src, min(8 * 1024 * 1024, end - start), start)
                if not data or os.pwrite(dst, data, offset + start) != len(data):
                    raise OSError('sparse fixture copy failed')
                start += len(data)
            current = end
        os.fsync(dst)
    finally:
        os.close(src); os.close(dst)


def fixture(out, binding):
    native = out / 'native.ext4'
    with native.open('xb') as stream:
        stream.truncate(fs.SIZE_BYTES)
    # A new private regular file, never a host or connected block device.
    if not stat.S_ISREG(native.lstat().st_mode) or native.lstat().st_nlink != 1:
        raise ValueError('unsafe H0 fixture')
    command = fs.formatter_argv('/usr/sbin/mke2fs', str(native), binding['filesystem_uuid'])
    command.insert(1, '-F')
    env = dict(os.environ, MKE2FS_CONFIG=binding['configuration']['path'])
    h0.run(command, out / 'format.log', env)
    (out / 'witness').write_bytes(fs.WITNESS)
    for label, operation in [('write', f'write {out}/witness /{fs.WITNESS_NAME}'),
                             ('mode', f'set_inode_field /{fs.WITNESS_NAME} mode 0100400')]:
        h0.run(['debugfs', '-w', '-R', operation, native], out / ('witness-' + label + '.log'))
    h0.run(['e2fsck', '-fn', native], out / 'check-before.log')
    gpt = verify(binding['expected_gpt']).read_bytes()
    disk = out / 'root.ext4'  # Compatibility with the existing VM wrapper name.
    total = 62_305_280 * 4096
    with disk.open('xb') as stream:
        stream.truncate(total)
        stream.seek(0); stream.write(gpt[:6 * 4096])
        stream.seek(total - 9 * 4096); stream.write(gpt[6 * 4096:])
        stream.flush(); os.fsync(stream.fileno())
    sparse_copy(native, disk, offset=fs.FIRST_LBA * 4096)


class InstallVM(vm_test.VM):
    def start(self, label, disk=None, initrd=None):
        disk = disk or self.folder / 'root.ext4'
        initrd = initrd or self.folder / 'initramfs.cpio.gz'
        command = [self.qemu_root / 'usr/bin/qemu-system-aarch64', '-machine', 'virt',
            '-cpu', 'cortex-a76', '-smp', '2', '-m', '1536', '-nographic', '-monitor', 'none',
            '-no-reboot', '-kernel', self.kernel, '-initrd', initrd,
            '-append', 'console=ttyAMA0 rdinit=/init panic=-1',
            '-drive', f'if=none,id=root,file={disk},format=raw',
            '-device', 'virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096',
            '-netdev', f'user,id=net0,hostfwd=tcp:127.0.0.1:{self.port}-:22',
            '-device', 'virtio-net-device,netdev=net0', '-device', 'virtio-rng-device']
        self.log = self.folder / (label + '.serial.log')
        h0.write_json(self.folder / (label + '.command.json'), [str(x) for x in command])
        with self.log.open('wb') as log:
            self.process = subprocess.Popen([str(x) for x in command], stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ,
                LD_LIBRARY_PATH=str(self.qemu_root / 'usr/lib/x86_64-linux-gnu')))

    def ssh(self, script, label, *, user='root', pty=False, check=True, timeout=30):
        command = ['ssh', '-i', self.key, '-p', str(self.port), '-o', 'BatchMode=yes',
            '-o', 'ConnectTimeout=3', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=' + str(self.folder / 'known_hosts'),
            *(['-tt'] if pty else []), user + '@127.0.0.1', script]
        handle = raw.acquire_command([str(x) for x in command], self.folder, label, timeout=timeout,
            stdout_maximum=65536, stderr_maximum=16384, stdout_name=label + '.stdout', stderr_name=label + '.stderr')
        result = SimpleNamespace(handle=handle, returncode=handle.returncode,
            stdout=raw.read_stdout(handle, maximum=65536), stderr=raw.read_stderr(handle, maximum=16384))
        if check and result.returncode:
            raise RuntimeError(f'{label}: SSH status {result.returncode}')
        return result

    def ready(self, label):
        deadline = time.monotonic() + 240
        attempts = 0
        while time.monotonic() < deadline:
            if self.process.poll() is not None or b'BOOTSTRAP_STOP' in self.log.read_bytes():
                raise RuntimeError('VM installer stopped; see serial log')
            attempts += 1
            result = self.ssh('health', label + '-' + str(attempts), check=False, timeout=6)
            if result.returncode == 0 and result.stdout.endswith(b'DEBIAN_HEALTH_PASS\n'):
                return result
            time.sleep(2)
        raise RuntimeError('VM installer readiness deadline')


def build(out, artifact):
    out = out.absolute()
    if out.exists() or out.resolve() != out or not out.is_relative_to(ROOT / 'workspace/private/outputs'):
        raise ValueError('fresh private VM output required')
    out.mkdir(mode=0o700)
    sources = prepare.source_snapshot(out, extra=(HERE / 'virt-binding.inc.c',))
    value = read(artifact / 'artifact.json')
    for name in ('link.json', 's22plus_native_ext4_seal_v1.h', 'binding.h'):
        shutil.copyfile(artifact / name, out / name)
    prepare.archive(out, value['run_id'], (artifact / 'client-key.pub').read_bytes(),
        (artifact / 'host-key').read_bytes(), (artifact / 'host-key.pub').read_bytes(),
        (artifact / 'hello.deb').read_bytes(), virt=True)
    header = (artifact / 'target-plan.h').read_text()
    for name, file in [('archive', 'rootfs.tar.xz'), ('tar', 'rootfs.tar'), ('busybox', 'busybox')]:
        data = (out / file).read_bytes()
        header = re_replace(header, rf'static const unsigned long long target_{name}_size=\d+ULL;',
                            f'static const unsigned long long target_{name}_size={len(data)}ULL;')
        header = re_replace(header, rf'static const unsigned char target_{name}_sha256\[\]=\{{[^}}]+\}};',
                            prepare.c_bytes('target_' + name + '_sha256', hashlib.sha256(data).digest()).strip())
    # The H0 tar differs only in network service and has its own install identity.
    identity = f'S22_DEBIAN_INSTALL_V1 {value["run_id"]} {prepare.sha((out / "rootfs.tar").read_bytes())}\n'
    header = re_replace(header, r'static const char target_install_identity\[\]=[^;]+;',
                        'static const char target_install_identity[]=' + json.dumps(identity) + ';')
    (out / 'target-plan.h').write_text(header)
    h0.run(['aarch64-linux-gnu-gcc', '-std=gnu11', '-Os', '-static', '-fno-ident', '-ffunction-sections',
        '-fdata-sections', '-Wl,--gc-sections', '-DS22_DEBIAN_DEVICE', '-DS22_DEBIAN_VIRT_TEST',
        '-I', out, BASE / 'handoff.c', '-o', out / 'init'], out / 'compile.log')
    binding = read(verify(value['filesystem_binding']))
    entries = [('bin', stat.S_IFDIR | 0o755, b''), ('etc', stat.S_IFDIR | 0o755, b'')]
    for name, source, mode in [('init', out / 'init', 0o750), ('bin/busybox', out / 'busybox', 0o755),
            ('etc/mdev.conf', out / 'mdev.conf', 0o644), ('rootfs.tar.xz', out / 'rootfs.tar.xz', 0o400),
            ('s22-fs-e2fsck', verify(binding['checker']), 0o500),
            *[(n, out / n, 0o400) for n in ('rootfs.meta', 'rootfs.sha256', 'install.meta', 'install.sha256')]]:
        entries.append((name, stat.S_IFREG | mode, source.read_bytes()))
    import gzip
    (out / 'initramfs.cpio.gz').write_bytes(gzip.compress(h0.newc(entries), mtime=0))
    fixture(out, binding)
    for receipt in sources: verify(receipt, maximum=4 * 1024 * 1024)
    h0.write_json(out / 'build.json', dict(scope='H0_VIRT_EXACT_GEOMETRY_ONLY', device_actions=0,
        artifact_source=pin(artifact / 'artifact.json'), source_inputs=sources))


def re_replace(text, pattern, replacement):
    import re
    result, count = re.subn(pattern, lambda _: replacement, text)
    if count != 1:
        raise ValueError('H0 binding substitution differs')
    return result


def sparse_digest(path):
    """Digest every data extent and its position; all omitted bytes are holes.

    This is an extent-aware equality proof, explicitly not a whole-file SHA256.
    It avoids rereading 237 GiB of known-zero holes for each negative case.
    """
    h = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY)
    try:
        before = os.fstat(fd)
        h.update(str(before.st_size).encode() + b'\n')
        position = 0
        while position < before.st_size:
            try:
                start = os.lseek(fd, position, os.SEEK_DATA)
            except OSError as error:
                if error.errno == errno.ENXIO: break
                raise
            end = os.lseek(fd, start, os.SEEK_HOLE)
            h.update(f'{start}:{end}\n'.encode())
            while start < end:
                body = os.pread(fd, min(8 * 1024 * 1024, end - start), start)
                if not body: raise OSError('short sparse digest read')
                h.update(body); start += len(body)
            position = end
        stable = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if stable(before) != stable(os.fstat(fd)): raise RuntimeError('fixture changed during digest')
        return dict(size=before.st_size, extent_sha256=h.hexdigest(), mtime_ns=before.st_mtime_ns)
    finally:
        os.close(fd)


def negative(base, out, artifact, kernel, qemu_root):
    import gzip
    import tarfile
    import io
    import re
    if out.exists() or out.resolve() != out or not out.is_relative_to(ROOT / 'workspace/private/outputs'):
        raise ValueError('fresh private negative output required')
    out.mkdir(mode=0o700)
    parsed = prepare.packaging.shared.boot.parse_newc(gzip.decompress((base / 'initramfs.cpio.gz').read_bytes()))
    entries = [(entry.name, entry.mode, entry.data) for entry in parsed]
    binding = read(verify(read(artifact / 'artifact.json')['filesystem_binding']))
    results = []
    for case, expected in [('gpt-byte', 'target-storage-binding'), ('wrong-uuid', 'target-storage-binding'),
            ('witness', 'retained-witness'), ('start-only', 'install-consumed-incomplete'),
            ('archive-digest', 'archive-or-extractor-binding'), ('readback', 'root-content')]:
        folder = out / case; folder.mkdir(mode=0o700)
        native = folder / 'native.ext4'
        subprocess.run(['cp', '--reflink=auto', '--sparse=always', base / 'native.ext4', native], check=True)
        def debug(operation, label):
            h0.run(['debugfs', '-w', '-R', operation, native], folder / (label + '.log'))
        if case == 'wrong-uuid':
            h0.run(['tune2fs', '-U', '11111111-2222-4333-8444-555555555555', native], folder / 'mutate.log')
        elif case == 'witness':
            bad = folder / 'bad-witness'; bad.write_bytes(b'X' + fs.WITNESS[1:])
            debug('rm /' + fs.WITNESS_NAME, 'remove-witness')
            debug(f'write {bad} /{fs.WITNESS_NAME}', 'write-witness')
            debug('set_inode_field /' + fs.WITNESS_NAME + ' mode 0100400', 'witness-mode')
        elif case == 'start-only':
            match = re.search(r'static const char target_install_identity\[\]=([^;]+);', (base / 'target-plan.h').read_text())
            marker = folder / 'start'; marker.write_text(json.loads(match[1]))
            debug(f'write {marker} /.s22-debian-start-v1', 'start-marker')
            debug('set_inode_field /.s22-debian-start-v1 mode 0100400', 'start-mode')
        gpt = verify(binding['expected_gpt']).read_bytes()
        disk = folder / 'root.ext4'
        with disk.open('xb') as stream:
            stream.truncate(62_305_280 * 4096)
            stream.write(gpt[:6 * 4096]); stream.seek(62_305_280 * 4096 - 9 * 4096); stream.write(gpt[6 * 4096:])
        sparse_copy(native, disk, offset=fs.FIRST_LBA * 4096)
        if case == 'gpt-byte':
            with disk.open('r+b') as stream:
                stream.seek(400); old = stream.read(1); stream.seek(400); stream.write(bytes([old[0] ^ 1]))
        selected = list(entries)
        if case == 'archive-digest':
            selected = [(name, mode, b'X' + body[1:] if name == 'rootfs.tar.xz' else body) for name, mode, body in selected]
        elif case == 'readback':
            # A producer/inventory inconsistency, authenticated as H0 fixture
            # bytes, must fail the real post-extraction content readback.
            source_tar = (base / 'rootfs.tar').read_bytes()
            with tarfile.open(fileobj=io.BytesIO(source_tar)) as source:
                cron = source.getmember('usr/sbin/cron')
                offset = cron.offset_data
            altered = bytearray(source_tar); altered[offset] ^= 1; altered = bytes(altered)
            packed = prepare.lzma.compress(altered, preset=6)
            header = (base / 'target-plan.h').read_text()
            for name, body in [('tar', altered), ('archive', packed)]:
                header = re_replace(header, rf'static const unsigned long long target_{name}_size=\d+ULL;',
                    f'static const unsigned long long target_{name}_size={len(body)}ULL;')
                header = re_replace(header, rf'static const unsigned char target_{name}_sha256\[\]=\{{[^}}]+\}};',
                    prepare.c_bytes('target_' + name + '_sha256', hashlib.sha256(body).digest()).strip())
            (folder / 'target-plan.h').write_text(header)
            for name in ('binding.h', 's22plus_native_ext4_seal_v1.h'):
                shutil.copyfile(base / name, folder / name)
            h0.run(['aarch64-linux-gnu-gcc', '-std=gnu11', '-Os', '-static', '-fno-ident',
                '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections', '-DS22_DEBIAN_DEVICE',
                '-DS22_DEBIAN_VIRT_TEST', '-I', folder, BASE / 'handoff.c', '-o', folder / 'init'], folder / 'compile.log')
            selected = [(name, mode, packed if name == 'rootfs.tar.xz' else
                         (folder / 'init').read_bytes() if name == 'init' else body) for name, mode, body in selected]
        (folder / 'initramfs.cpio.gz').write_bytes(gzip.compress(h0.newc(selected), mtime=0))
        before = sparse_digest(disk)
        vm = InstallVM(folder, kernel, qemu_root, artifact / 'client-key')
        try:
            vm.start('negative')
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                log = vm.log.read_bytes()
                if b'BOOTSTRAP_STOP' in log:
                    if ('BOOTSTRAP_STOP stage=' + expected + ' ').encode() not in log:
                        raise RuntimeError(case + ': unexpected stop stage')
                    break
                if vm.process.poll() is not None: raise RuntimeError(case + ': exited without typed stop')
                time.sleep(1)
            else:
                raise RuntimeError(case + ': no bounded stop')
        finally:
            vm.stop()
        after = sparse_digest(disk)
        if case != 'readback' and before != after:
            raise RuntimeError(case + ': prewrite rejection changed disk')
        if case == 'readback':
            if before == after or b'DEBIAN_INSTALL_INTENT_DURABLE' not in log or b'DEBIAN_INSTALL_COMPLETE' in log:
                raise RuntimeError('partial install disposition differs')
            # Hard-cut the failed guest, then prove the same candidate cannot
            # touch its consumed dirty filesystem on a subsequent boot.
            vm.start('no-replay')
            try:
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    second = vm.log.read_bytes()
                    if b'BOOTSTRAP_STOP stage=target-storage-binding ' in second: break
                    if b'DEBIAN_INSTALL_INTENT_DURABLE' in second or b'BOOTSTRAP_HANDOFF' in second:
                        raise RuntimeError('partial installation replayed')
                    time.sleep(1)
                else: raise RuntimeError('no-replay stop absent')
            finally:
                vm.stop()
            if sparse_digest(disk) != after:
                raise RuntimeError('consumed reboot mutated partial filesystem')
        row = dict(case=case, expected_stop=expected, before=before, after=after,
                   unchanged=before == after, consumed_no_replay=case == 'readback', device_actions=0)
        h0.write_json(folder / 'result.json', row); results.append(row)
    h0.write_json(out / 'result.json', dict(verdict='PASS_H0_ARM64_INSTALLER_NEGATIVES',
        scope='VIRT_NOT_SAMSUNG', device_actions=0, cases=results))


def qualify(out, artifact, kernel, qemu_root):
    vm = InstallVM(out, kernel, qemu_root, artifact / 'client-key')
    pub = (artifact / 'host-key.pub').read_text().strip()
    (out / 'known_hosts').write_text(f'[127.0.0.1]:{vm.port} {pub}\n')
    try:
        vm.start('install-boot')
        first = vm.ready('first-health')
        protocol_plan = dict(candidate=dict(run_id=read(artifact / 'artifact.json')['run_id']))
        first_proof = owner_protocol.project_debian(first.handle, protocol_plan)
        if b'DEBIAN_INSTALL_COMPLETE' not in first.stdout:
            raise RuntimeError('first boot did not prove complete installation')
        pty = vm.ssh('test -t 0 && test -t 1 && echo PTY_PASS', 'pty', user='lab', pty=True)
        if b'PTY_PASS' not in pty.stdout:
            raise RuntimeError('lab PTY is unproved')
        vm.ssh('workload', 'workload', timeout=60)
        deadline = time.monotonic() + 90
        count = 0
        while time.monotonic() < deadline:
            count += 1
            result = vm.ssh('workload-result', 'workload-result-' + str(count), check=False)
            if result.returncode == 0 and result.stdout.endswith(b'DEBIAN_WORKLOAD_PASS\n'):
                break
            time.sleep(3)
        else:
            raise RuntimeError('cron/package/log result unproved')
        reboot = vm.ssh('reboot', 'reboot', check=False)
        owner_protocol.control_projection(reboot.handle, 'reboot', '127.0.0.1')
        if vm.process.wait(timeout=60) != 0:
            raise RuntimeError('normal reboot did not stop no-reboot VM')
        vm.start('persistent-boot')
        second = vm.ready('second-health')
        second_proof = owner_protocol.project_debian(second.handle, protocol_plan)
        if b'DEBIAN_INSTALL_INTENT_DURABLE' in second.stdout or b'DEBIAN_INSTALL_COMPLETE' in second.stdout:
            raise RuntimeError('second boot repeated the installer')
        vm.ssh('workload-result', 'persistence-result')
        ids = lambda value: [line for line in value.stdout.decode().splitlines() if line.startswith('boot_id=')]
        if len(ids(first)) != 1 or len(ids(second)) != 1 or ids(first) == ids(second) or \
                second_proof['reboot_source_boot_sha256'] != first_proof['boot_id_sha256']:
            raise RuntimeError('distinct Debian boot IDs unproved')
        if b'boot_count=1\n' not in first.stdout or b'boot_count=2\n' not in second.stdout:
            raise RuntimeError('boot-count continuity unproved')
        shutdown = vm.ssh('shutdown', 'shutdown', check=False)
        owner_protocol.control_projection(shutdown.handle, 'shutdown', '127.0.0.1')
        if vm.process.wait(timeout=60) != 0:
            raise RuntimeError('normal poweroff did not terminate VM')
        # Extract only the native partition into a new regular sparse file for
        # host read-only fsck; no loop device or host mount is used.
        native = out / 'after.ext4'
        with native.open('xb') as f:
            f.truncate(fs.SIZE_BYTES)
        src, dst = os.open(out / 'root.ext4', os.O_RDONLY), os.open(native, os.O_WRONLY)
        offset, limit = fs.FIRST_LBA * 4096, (fs.LAST_LBA + 1) * 4096
        try:
            position = offset
            while position < limit:
                try:
                    start = os.lseek(src, position, os.SEEK_DATA)
                except OSError as error:
                    if error.errno == errno.ENXIO: break
                    raise
                end = min(os.lseek(src, start, os.SEEK_HOLE), limit)
                if start >= limit: break
                while start < end:
                    body = os.pread(src, min(8 * 1024 * 1024, end - start), start)
                    if not body or os.pwrite(dst, body, start - offset) != len(body): raise OSError('partition copy failed')
                    start += len(body)
                position = end
            os.fsync(dst)
        finally:
            os.close(src); os.close(dst)
        h0.run(['e2fsck', '-fn', native], out / 'check-after.log')
        h0.write_json(out / 'result.json', dict(verdict='PASS_H0_ARM64_INSTALL_REBOOT_PERSIST_SHUTDOWN',
            scope='VIRT_NOT_SAMSUNG', device_actions=0, first_boot=ids(first), second_boot=ids(second),
            host_key=pin(artifact / 'host-key.pub'), original_build=pin(out / 'build.json')))
    finally:
        vm.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['build', 'qualify', 'negative'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--kernel', type=Path)
    parser.add_argument('--qemu-root', type=Path)
    parser.add_argument('--base', type=Path)
    args = parser.parse_args()
    if args.phase == 'build':
        build(args.output, args.artifact.resolve(strict=True))
    elif args.phase == 'qualify':
        qualify(args.output.resolve(strict=True), args.artifact.resolve(strict=True), args.kernel, args.qemu_root)
    else:
        negative(args.base.resolve(strict=True), args.output.absolute(), args.artifact.resolve(strict=True), args.kernel, args.qemu_root)
