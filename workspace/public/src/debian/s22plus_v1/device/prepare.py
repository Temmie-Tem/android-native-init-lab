#!/usr/bin/env python3
"""H0-only sealed Debian device artifact construction. No transport imports."""
import argparse
import copy
import gzip
import hashlib
import io
import ipaddress
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import uuid

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[4]
sys.path[:0] = [str(BASE), str(ROOT / 'workspace/public/src/scripts/analysis'),
               str(ROOT / 'workspace/public/src/scripts/revalidation')]
import h0
import s22plus_native_thermal_build_v1 as packaging
import s22plus_native_ext4_source_v1 as ext4_source
import s22plus_native_ext4_h0 as ext4_builder
import s22plus_memory_manifest_v1 as memory
import s22plus_debian_profile_v1 as declaration
from s22plus_native_records_v3 import pin, read, verify

ROOTFS_SHA = declaration.ROOTFS_SHA
ROOTFS = ROOT / 'workspace/private/outputs/s22plus-debian-bootstrap-h0-20260921-1/rootfs-c'
STORAGE = ROOT / 'workspace/private/outputs/s22plus-debian-bootstrap-h0-20260921-1/storage-final-2'
RETAINED = declaration.RETAINED
RETAINED_RESULT = declaration.RETAINED_RESULT
PLATFORM_PLAN = declaration.PLATFORM_PLAN
MUTABLE = {'etc/resolv.conf', 'etc/hostname', 'etc/mtab', 'etc/machine-id', 'etc/adjtime', 'etc/ld.so.cache'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def c_bytes(name, raw):
    return f'static const unsigned char {name}[]={{' + ','.join(map(str, raw)) + '};\n'


def source_snapshot(out, *, extra=()):
    # Imported producer/parser modules are provenance, separate from the live
    # capability's much smaller execution closure. Retained images keep their
    # original provenance rather than inheriting current generator contents.
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
             if getattr(module, '__file__', None) and
             Path(module.__file__).resolve().is_relative_to(ROOT / 'workspace/public/src')}
    paths.update(HERE / name for name in ('target.inc.c', 'lab-usb', 'lab-qualify'))
    paths.update(extra)
    paths.update([BASE / 'handoff.c', *[ROOT / 'workspace/public/src/native-init' / name for name in
        ('s22plus_native_ext4_v1.c', 's22plus_native_ext4_core_v1.h', 's22plus_fyg8_max77705_result_parser.inc.c')]])
    receipts = []
    for source in sorted(paths):
        receipt = pin(source, maximum=4 * 1024 * 1024)
        destination = out / 'source' / source.relative_to(ROOT)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        destination.write_bytes(verify(receipt, maximum=4 * 1024 * 1024).read_bytes())
        destination.chmod(0o400)
        receipts.append(receipt)
    h0.write_json(out / 'source-inputs.json', receipts)
    return receipts


def keypair(out, name):
    path = out / name
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', name, '-f', path], check=True)
    return path.read_bytes(), path.with_suffix('.pub').read_bytes()


def hello(out):
    index = ROOTFS / 'apt-lists/deb.debian.org_debian_dists_trixie_main_binary-arm64_Packages'
    release = index.with_name('deb.debian.org_debian_dists_trixie_InRelease')
    with (out / 'hello-signature.log').open('wb') as log:
        subprocess.run(['gpgv', '--keyring', '/usr/share/keyrings/debian-archive-keyring.gpg', release],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    raw = index.read_bytes()
    expected = re.search(r'^ ([0-9a-f]{64}) +(\d+) +main/binary-arm64/Packages$', release.read_text(), re.M)
    if not expected or (sha(raw), len(raw)) != (expected[1], int(expected[2])):
        raise ValueError('signed package index changed')
    rows = [dict(line.split(': ', 1) for line in block.splitlines() if ': ' in line and not line.startswith(' '))
            for block in raw.decode().split('\n\n')]
    selected, = [row for row in rows if row.get('Package') == 'hello' and row.get('Architecture') == 'arm64']
    name = selected['Filename']
    if not name.startswith('pool/main/h/hello/') or '..' in name:
        raise ValueError('hello archive path differs')
    body = urllib.request.urlopen('https://deb.debian.org/debian/' + name, timeout=60).read(1024 * 1024)
    if (sha(body), len(body)) != (selected['SHA256'], int(selected['Size'])):
        raise ValueError('hello archive digest differs')
    (out / 'hello.deb').write_bytes(body)
    h0.write_json(out / 'hello.json', dict(package=selected, release=pin(release),
        index=pin(index, maximum=128 * 1024 * 1024), artifact=pin(out / 'hello.deb')))
    return body


def archive(out, run_id, ssh_public, host_private, host_public, hello_deb, *, virt=False):
    raw = (ROOTFS / 'rootfs.tar').read_bytes()
    if sha(raw) != ROOTFS_SHA:
        raise ValueError('reviewed Debian rootfs changed')
    members = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as source:
        for original in source:
            member = copy.copy(original)
            name = member.name.removeprefix('./').rstrip('/')
            if name in ('', '.'):
                continue
            if name.startswith('dev/'):
                continue  # The bootstrap supplies the entire fresh device tmpfs.
            if name.startswith('/') or '..' in PurePosixPath(name).parts or any(x in name for x in '\r\n\\'):
                raise ValueError('archive path is not canonical')
            if name in members or not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                raise ValueError('duplicate or special archive member: ' + name)
            member.name, member.mtime, member.pax_headers = name, h0.EPOCH, {}
            members[name] = (member, source.extractfile(original).read() if member.isfile() else b'')

    def add(name, data, mode=0o644, uid=0, gid=0, link=None):
        for parent in reversed(PurePosixPath(name).parents):
            text = str(parent)
            if text != '.' and text not in members:
                item = tarfile.TarInfo(text); item.type = tarfile.DIRTYPE
                item.mode, item.uid, item.gid, item.mtime = 0o755, 0, 0, h0.EPOCH
                members[text] = (item, b'')
        item = tarfile.TarInfo(name)
        item.mode, item.uid, item.gid, item.mtime = mode, uid, gid, h0.EPOCH
        item.type = tarfile.SYMTYPE if link else tarfile.REGTYPE
        item.linkname = link or ''
        item.size = len(data) if not link else 0
        members[name] = (item, data)

    # These distro jobs have no role in this storage qualification. Retain their
    # package files but remove startup/shutdown links and scheduled invocations.
    disabled = {'hwclock.sh', 'checkroot.sh', 'checkfs.sh', 'checkroot-bootclean.sh'}
    for name, (member, _) in list(members.items()):
        if (re.fullmatch(r'etc/rc[0-6S]\.d/[SK][0-9]+.+', name) and
            member.issym() and posixpath.basename(member.linkname) in disabled) or name == 'etc/cron.d/e2scrub_all':
            del members[name]
    add('etc/fstab', b'')
    # The existing .depend files describe the old service graph. Use the
    # distro-supported serial rc path so only the reviewed links execute.
    add('etc/init.d/.legacy-bootordering', b'S22 Debian fixed initial qualification\n', 0o644)
    add('etc/lab-device-id', ('S22PLUS_FYG8_DEBIAN_V1 ' + run_id + '\n').encode())
    add('etc/lab-native-version', (declaration.VERSION + '\n').encode(), 0o444)
    add('etc/ssh/ssh_host_ed25519_key', host_private, 0o600)
    add('etc/ssh/ssh_host_ed25519_key.pub', host_public)
    add('etc/ssh/sshd_config.d/10-lab.conf', b'PermitRootLogin prohibit-password\nPasswordAuthentication no\nKbdInteractiveAuthentication no\nPubkeyAuthentication yes\nAuthenticationMethods publickey\nAllowUsers lab root\nHostKey /etc/ssh/ssh_host_ed25519_key\n')
    add('home/lab/.ssh/authorized_keys', ssh_public, 0o600, 1000, 1000)
    add('root/.ssh/authorized_keys', b'restrict,command="/usr/local/sbin/lab-qualify" ' + ssh_public, 0o600)
    for name in ('home/lab/.ssh', 'root/.ssh'):
        member, data = members[name]; member.mode = 0o700
    add('usr/local/sbin/lab-qualify', (HERE / 'lab-qualify').read_bytes(), 0o755)
    add('etc/init.d/lab-usb', (HERE / 'lab-usb').read_bytes(), 0o755)
    if virt:
        add('etc/init.d/lab-usb', b'#!/bin/sh\nset -eu\ntest "$1" = start || exit 0\nip link set lo up\nip address add 10.0.2.15/24 dev eth0\nip link set eth0 up\n', 0o755)
    # Explicit service ordering; no DHCP/client daemon or host routing changes.
    for runlevel in '2345':
        add(f'etc/rc{runlevel}.d/S02lab-usb', b'', 0o777, link='../init.d/lab-usb')
    for name in list(members):
        if re.fullmatch(r'etc/rc[0-6S]\.d/[SK][0-9]+lab-network', name):
            del members[name]
    # Broad IDE disk power-down is unnecessary. Filesystem shutdown remains SysV.
    item, body = members['etc/init.d/halt']
    if body.count(b'hddown="-h"') != 1:
        raise ValueError('halt script differs')
    members[item.name] = (item, body.replace(b'hddown="-h"', b'hddown=""'))
    item.size = len(members[item.name][1])
    # No block aliases created by the device manager; the bootstrap binds its
    # single private native root node before mdev starts.
    add('etc/mdev.conf', b'SUBSYSTEM=block;.* 0:0 0000 !\nnull|zero|full|random|urandom 0:0 0666\ntty 0:5 0666\nptmx 0:5 0666\n.* 0:0 0600\n')
    link = json.loads((out / 'link.json').read_text())
    config = ''.join(f'{key}={value}\n' for key, value in link.items() if key in {'serial', 'device_mac', 'host_mac', 'device_address'})
    add('etc/default/lab-usb', config.encode(), 0o600)
    add('usr/local/lib/lab-offline/hello.deb', hello_deb, 0o400)
    # Avoid firstboot generation of unused host keys. This exact key was pinned
    # on the host before any candidate boot.
    item, body = members['etc/init.d/lab-firstboot']
    if body.count(b'ssh-keygen -A') != 1:
        raise ValueError('firstboot key generator differs')
    body = body.replace(b'ssh-keygen -A', b'test -s /etc/ssh/ssh_host_ed25519_key')
    item.size = len(body); members[item.name] = (item, body)

    # Resolve link parents inside the target root. No member may traverse outside
    # it; tar runs chrooted and receives only this content-bound archive fd.
    for name, (member, _) in members.items():
        if member.islnk():
            member.linkname = member.linkname.removeprefix('./')
            if member.linkname not in members or not members[member.linkname][0].isfile():
                raise ValueError('unexpected hardlink')
        if member.issym() and ('\x00' in member.linkname or '\n' in member.linkname):
            raise ValueError('unsafe symlink')
    with tarfile.open(out / 'rootfs.tar', 'w', format=tarfile.PAX_FORMAT) as target:
        for member, body in members.values():
            target.addfile(member, io.BytesIO(body) if member.isfile() else None)
    tar = (out / 'rootfs.tar').read_bytes()
    (out / 'rootfs.tar.xz').write_bytes(lzma.compress(tar, preset=6))
    for full, prefix in ((True, 'install'), (False, 'rootfs')):
        selected = {name for name in members if full or
                    (name not in MUTABLE and name.startswith(('etc/', 'usr/', 'home/lab/.ssh/', 'root/.ssh/')))}
        selected.update({'bin', 'sbin', 'lib'})
        for name in list(selected):
            selected.update(str(p) for p in PurePosixPath(name).parents if str(p) != '.')
        metadata, hashes = bytearray(), []
        for name in sorted(selected):
            member, body = members[name]
            target_member = members[member.linkname][0] if member.islnk() else member
            mode = (stat.S_IFLNK if member.issym() else stat.S_IFDIR if member.isdir() else stat.S_IFREG) | member.mode
            linktext = member.linkname.encode() if member.issym() else b''
            size = target_member.size if not member.issym() else len(linktext)
            encoded = name.encode()
            metadata += struct.pack('<IIIQHH', mode, member.uid, member.gid, size, len(encoded), len(linktext)) + encoded + linktext
            if member.isfile() or member.islnk():
                data = members[member.linkname][1] if member.islnk() else body
                hashes.append(f'{sha(data)}  {name}\n')
        (out / (prefix + '.meta')).write_bytes(metadata)
        (out / (prefix + '.sha256')).write_text(''.join(hashes))
    for member, destination in [('usr/bin/busybox', 'busybox'), ('etc/mdev.conf', 'mdev.conf')]:
        (out / destination).write_bytes(members[member][1])
    h0.write_json(out / 'rootfs-inventory.json', {name: dict(type=member.type.decode(), mode=member.mode,
        uid=member.uid, gid=member.gid, size=member.size, link=member.linkname,
        sha256=sha(body) if member.isfile() else None) for name, (member, body) in members.items()})


def build(out):
    out = out.absolute()
    if out.resolve() != out or not out.is_relative_to(ROOT / 'workspace/private/outputs') or out.exists():
        raise ValueError('fresh private output required')
    out.mkdir(mode=0o700)
    source_inputs = source_snapshot(out)
    run_id = uuid.uuid4().hex
    _, ssh_public = keypair(out, 'client-key')
    host_private, host_public = keypair(out, 'host-key')
    suffix = uuid.uuid4().bytes[:5]
    mac = lambda leading: ':'.join(f'{x:02x}' for x in bytes([leading]) + suffix)
    # Private per-candidate IPv4 link-local /30, never a tracked device address.
    network = int(ipaddress.IPv4Address(bytes((169, 254, suffix[0] % 254 + 1, suffix[1] & 252))))
    host_address, device_address = str(ipaddress.IPv4Address(network + 1)), str(ipaddress.IPv4Address(network + 2))
    h0.write_json(out / 'link.json', dict(serial='s22debian' + run_id[:16], device_mac=mac(2), host_mac=mac(6),
        device_address=device_address + '/30', host_address=host_address + '/30', ssh_address=device_address))
    (out / 'known_hosts').write_bytes(device_address.encode() + b' ' + host_public)
    archive(out, run_id, ssh_public, host_private, host_public, hello(out))
    binding = read(verify(ext4_source.BINDING))
    (out / 's22plus_native_ext4_seal_v1.h').write_bytes(ext4_builder.seal(ext4_source.BINDING, run_id, initialize=False))
    (out / 'binding.h').write_text(c_bytes('root_uuid', uuid.UUID(binding['filesystem_uuid']).bytes))
    baseline = (RETAINED / 'candidate-a/boot.img').read_bytes()
    old_result = read(verify(RETAINED_RESULT))
    parsed, old_entries = packaging.shared.entries(baseline)
    # The retained build result and image pin are kept as source provenance.
    expected = old_result['candidate']['a']['boot_img']
    if (len(baseline), sha(baseline)) != (expected['size'], expected['sha256']):
        raise ValueError('retained boot image differs')
    platform_plan = PLATFORM_PLAN
    plan = verify(platform_plan).read_text()
    modules = re.findall(r'\{"([^"/]+\.ko)", "[^"]+", "([^"\n]*)"\}', plan)
    if len(modules) != 73:
        raise ValueError('retained platform module plan differs')
    vendor = memory.vendor
    vendor_identity = dict(path=str(ROOT / vendor.DEFAULT_VENDOR_RAMDISK),
        size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE, sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256)
    # Retained read-only firmware inputs may use their established storage alias.
    # Reuse its sealed byte reader; effectful AP paths remain direct regular files.
    vendor_bytes = memory.base.stable(Path(vendor_identity['path']),
        {key: vendor_identity[key] for key in ('size', 'sha256')})
    stock_entries = memory.boot_verify.parse_newc(
        memory.boot_verify.decompress_lz4_stream_python(vendor_bytes, maximum=128 * 1024 * 1024))
    stock = {row.name: row for row in stock_entries}
    if len(stock) != len(stock_entries):
        raise ValueError('duplicate sealed vendor member')
    storage_plan = read(STORAGE / 'storage-plan.json')
    names = {name for name, _ in modules}
    for row in storage_plan['modules']:
        if row['name'] not in names:
            modules.append((row['name'], '')); names.add(row['name'])
    entries = [('bin', stat.S_IFDIR | 0o755, b''), ('s22-modules', stat.S_IFDIR | 0o755, b'')]
    header = ['struct target_module { const char *path; unsigned long long size; unsigned char sha256[32]; const char *parameters; };\n',
              'static const struct target_module target_modules[]={\n']
    module_receipts = []
    for name, params in modules:
        original = old_entries.get('lib/modules/' + name)
        if original:
            expected = old_result['candidate']['a']['inventory']['lib/modules/' + name]
            if packaging.shared.row_identity(original) != expected:
                raise ValueError('retained custom module identity differs: ' + name)
        else:
            original = stock['lib/modules/' + name]
            if (original.mode, original.uid, original.gid, original.nlink) != (stat.S_IFREG | 0o644, 0, 0, 1):
                raise ValueError('stock module metadata differs: ' + name)
        data = original.data
        path = 's22-modules/' + name
        entries.append((path, stat.S_IFREG | 0o400, data))
        header.append('{"/' + path + '",' + str(len(data)) + ',{' + ','.join(map(str, hashlib.sha256(data).digest())) + '},"' + params + '"},\n')
        module_receipts.append(dict(name=name, parameters=params, sha256=sha(data), size=len(data)))
    header.append('};\n')
    for name, file in [('archive', 'rootfs.tar.xz'), ('tar', 'rootfs.tar'), ('busybox', 'busybox')]:
        data = (out / file).read_bytes()
        header += [f'static const unsigned long long target_{name}_size={len(data)}ULL;\n',
                   c_bytes('target_' + name + '_sha256', hashlib.sha256(data).digest())]
    identity = f'S22_DEBIAN_INSTALL_V1 {run_id} {sha((out / "rootfs.tar").read_bytes())}\n'
    header.append('static const char target_install_identity[]=' + json.dumps(identity) + ';\n')
    (out / 'target-plan.h').write_text(''.join(header))
    compile_command = ['aarch64-linux-gnu-gcc', '-std=gnu11', '-Os', '-static', '-fno-ident',
        '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections', '-DS22_DEBIAN_DEVICE',
        '-I', str(out), str(BASE / 'handoff.c')]
    for side in 'ab':
        h0.run([*compile_command, '-o', out / ('init-' + side)], out / ('compile-' + side + '.log'))
    if (out / 'init-a').read_bytes() != (out / 'init-b').read_bytes():
        raise ValueError('bootstrap A/B differs')
    h0.run(['file', out / 'init-a'], out / 'file.log')
    for name, source, mode in [('init', out / 'init-a', 0o750), ('bin/busybox', out / 'busybox', 0o755),
            ('rootfs.tar.xz', out / 'rootfs.tar.xz', 0o400), ('s22-fs-e2fsck', verify(binding['checker']), 0o500),
            *[(name, out / name, 0o400) for name in ('rootfs.meta', 'rootfs.sha256', 'install.meta', 'install.sha256')]]:
        entries.append((name, stat.S_IFREG | mode, source.read_bytes()))
    entries += [('etc', stat.S_IFDIR | 0o755, b''), ('etc/mdev.conf', stat.S_IFREG | 0o644, (out / 'mdev.conf').read_bytes())]
    cpio = h0.newc(entries)
    (out / 'ramdisk.cpio').write_bytes(cpio)
    tools = packaging.shared.packager._bind_tools()
    for side in 'ab':
        scratch = out / ('pack-' + side); scratch.mkdir(mode=0o700)
        (scratch / 'base.img').write_bytes(baseline)
        # magiskboot operates in cwd; use a subprocess wrapper with explicit cwd.
        with (scratch / 'unpack-cwd.log').open('wb') as log:
            subprocess.run([tools['magiskboot'], 'unpack', '-h', str(scratch / 'base.img')], cwd=scratch,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        (scratch / 'ramdisk.cpio').write_bytes(cpio)
        with (scratch / 'repack.log').open('wb') as log:
            subprocess.run([tools['magiskboot'], 'repack', 'base.img', 'boot.img'], cwd=scratch,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        image = (scratch / 'boot.img').read_bytes()
        actual, actual_entries = packaging.shared.entries(image)
        if actual.kernel != parsed.kernel or len(image) != 96 * 1024 * 1024 or set(actual_entries) != {n for n, _, _ in entries}:
            raise ValueError('device boot image layout differs')
        for name, mode, data in entries:
            member = actual_entries[name]
            if (member.mode, member.uid, member.gid, member.nlink, member.data) != (mode, 0, 0, 1, data):
                raise ValueError('device ramdisk differs: ' + name)
        h0.run([tools['lz4'], '--content-size', '-B6', '-f', '-q', scratch / 'boot.img', scratch / 'boot.img.lz4'], scratch / 'lz4.log')
        packaging.shared.packager._write_deterministic_boot_ap((scratch / 'boot.img.lz4').read_bytes(), scratch / 'AP.tar.md5')
    if (out / 'pack-a/AP.tar.md5').read_bytes() != (out / 'pack-b/AP.tar.md5').read_bytes():
        raise ValueError('boot AP A/B differs')
    for receipt in source_inputs:
        verify(receipt, maximum=4 * 1024 * 1024)
    h0.write_json(out / 'artifact.json', dict(schema='s22plus-debian-device-artifact-h0-v1', status='H0_BUILT_NOT_DEVICE_QUALIFIED',
        run_id=run_id, namespace=declaration.NAMESPACE, version=declaration.VERSION,
        rootfs=pin(out / 'rootfs.tar', maximum=256 * 1024 * 1024),
        compressed_rootfs=pin(out / 'rootfs.tar.xz', maximum=128 * 1024 * 1024),
        ap=pin(out / 'pack-a/AP.tar.md5', maximum=128 * 1024 * 1024),
        boot=pin(out / 'pack-a/boot.img', maximum=128 * 1024 * 1024), kernel_sha256=sha(parsed.kernel),
        filesystem_binding=ext4_source.BINDING, modules=module_receipts, ab_identical=True,
        device_actions=0, source_inputs=source_inputs,
        retained_inputs=dict(result=RETAINED_RESULT,
            platform_plan=platform_plan, vendor=vendor_identity)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    build(parser.parse_args().output)
