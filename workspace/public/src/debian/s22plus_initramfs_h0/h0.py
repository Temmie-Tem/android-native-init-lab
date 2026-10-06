#!/usr/bin/env python3
"""Debian-owned /init experiment on regular-file ARM64 virt fixtures only."""
import argparse
import difflib
import email.utils
import hashlib
import json
import lzma
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.request
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PRIVATE = ROOT / 'workspace/private'
PACKAGES = ('initramfs-tools-core', 'initramfs-tools-bin', 'klibc-utils',
            'libklibc', 'cpio', 'dracut-install')
BASE = PRIVATE / 'outputs/s22plus-debian-bootstrap-h0-20260921-1'
ROOTFS_SHA = 'e6d8ec4ef0f85da6668d780c7357314be923946e386ddbbcefd9bc54c0f57789'
KERNEL_SHA = 'd25bca4b3b827ca29e350ae930cf93bc72626ac91e40d83cd1fb248e676b14c7'
CONFIG_SHA = '2659e5470f589d4b550a910df78926b22eaeb313d80a92a6ba4b2db449174f2a'
KERNEL = BASE / 'kernel-build/arch/arm64/boot/Image'
VERSION = '5.10.226'
EPOCH = '1789776000'  # Retained fixture epoch, 2026-09-19 UTC; before this build.


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def publish(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def private(path, *, fresh=False):
    path = Path(path).absolute()
    require(path == path.resolve() and path.is_relative_to(PRIVATE),
            'direct private path required')
    if fresh:
        path.mkdir(parents=True, mode=0o700, exist_ok=False)
    return path


def run(argv, log, *, env=None, timeout=120):
    with Path(log).open('xb') as stream:
        result = subprocess.run([str(x) for x in argv], stdin=subprocess.DEVNULL,
                                stdout=stream, stderr=subprocess.STDOUT,
                                timeout=timeout, env=env)
    require(result.returncode == 0, f'command failed; see {log}')


def download(url, path, maximum):
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read(maximum + 1)
    require(len(data) <= maximum, 'download exceeded bound')
    Path(path).write_bytes(data)


def fetch(out):
    out = private(out, fresh=True)
    base = 'https://deb.debian.org/debian/'
    download(base + 'dists/trixie/InRelease', out / 'InRelease', 4 * 1024**2)
    run(['gpgv', '--keyring', '/usr/share/keyrings/debian-archive-keyring.gpg',
         '--output', out / 'Release', out / 'InRelease'], out / 'signature.log')
    release = (out / 'Release').read_text()
    require('\nCodename: trixie\n' in release, 'wrong Debian release')
    for label in ('Date', 'Valid-Until'):
        match = re.search(r'^' + label + r': (.+)$', release, re.M)
        if match:
            stamp = email.utils.parsedate_to_datetime(match[1]).timestamp()
            require(stamp <= time.time() + 86400 if label == 'Date' else time.time() <= stamp,
                    'Debian Release timestamp rejected')
    index = 'main/binary-arm64/Packages.xz'
    section = release.split('\nSHA256:\n', 1)[1].split('\nSHA512:', 1)[0]
    rows = [line.split() for line in section.splitlines()]
    row = next(row for row in rows if len(row) == 3 and row[2] == index)
    download(base + 'dists/trixie/' + index, out / 'Packages.xz', 32 * 1024**2)
    require((out / 'Packages.xz').stat().st_size == int(row[1]) and
            sha(out / 'Packages.xz') == row[0], 'Packages differs from signed Release')
    content = lzma.decompress((out / 'Packages.xz').read_bytes()).decode()
    selected = {}
    for block in content.split('\n\n'):
        fields = dict(line.split(': ', 1) for line in block.splitlines()
                      if ': ' in line and not line.startswith(' '))
        name = fields.get('Package')
        if name in PACKAGES:
            require(name not in selected and fields['Architecture'] in ('all', 'arm64'),
                    'duplicate or wrong-architecture package')
            selected[name] = fields
    require(set(selected) == set(PACKAGES), 'requested packages missing')
    extracted = out / 'root'
    extracted.mkdir()
    receipts = []
    for name in PACKAGES:
        record = selected[name]
        filename = record['Filename']
        require(filename.startswith('pool/') and '..' not in Path(filename).parts,
                'invalid Debian package path')
        path = out / Path(filename).name
        download(base + filename, path, 32 * 1024**2)
        require(path.stat().st_size == int(record['Size']) and sha(path) == record['SHA256'],
                'package differs from authenticated index')
        run(['dpkg-deb', '-x', path, extracted], out / (name + '.extract.log'))
        receipts.append(dict(package=name, version=record['Version'],
                             architecture=record['Architecture'], file=path.name,
                             sha256=record['SHA256'], size=int(record['Size']),
                             depends=record.get('Depends', '')))
    publish(out / 'packages.json', dict(scope='H0 package inputs only', device_actions=0,
            origin=base, inrelease_sha256=sha(out / 'InRelease'),
            packages_index_sha256=sha(out / 'Packages.xz'), packages=receipts))
    print(json.dumps(receipts, indent=2))


def regular(path):
    path = private(path)
    require(stat.S_ISREG(path.lstat().st_mode) and path.stat().st_nlink == 1,
            'single-link private regular file required')
    return path


def verify_packages(packages, out):
    """Recheck retained inputs against Debian signatures before extraction."""
    run(['gpgv', '--keyring', '/usr/share/keyrings/debian-archive-keyring.gpg',
         '--output', out / 'verified-Release', regular(packages / 'InRelease')],
        out / 'package-signature.log')
    release = (out / 'verified-Release').read_text()
    require('\nCodename: trixie\n' in release, 'wrong signed release')
    section = release.split('\nSHA256:\n', 1)[1].split('\nSHA512:', 1)[0]
    index = regular(packages / 'Packages.xz')
    row = next(row for row in (line.split() for line in section.splitlines())
               if len(row) == 3 and row[2] == 'main/binary-arm64/Packages.xz')
    require(sha(index) == row[0] and index.stat().st_size == int(row[1]),
            'retained index differs from signed Release')
    records = {}
    for block in lzma.decompress(index.read_bytes()).decode().split('\n\n'):
        fields = dict(line.split(': ', 1) for line in block.splitlines()
                      if ': ' in line and not line.startswith(' '))
        if fields.get('Package') in PACKAGES:
            require(fields['Package'] not in records, 'duplicate indexed package')
            records[fields['Package']] = fields
    manifest = json.loads((packages / 'packages.json').read_text())
    require(len(manifest['packages']) == len(PACKAGES) and
            {p['package'] for p in manifest['packages']} == set(PACKAGES),
            'unexpected retained package set')
    for p in manifest['packages']:
        signed = records[p['package']]
        require(p['file'] == Path(signed['Filename']).name and
                p['version'] == signed['Version'] and p['architecture'] == signed['Architecture'] and
                p['sha256'] == signed['SHA256'] and p['size'] == int(signed['Size']),
                'package receipt differs from authenticated index')
        path = regular(packages / p['file'])
        require(sha(path) == p['sha256'] and path.stat().st_size == p['size'],
                'retained package bytes changed')


def snapshot_sources(out):
    paths = [HERE / name for name in ('h0.py', 'root-check.c', 'h0-dev', 'h0-boot',
                                     'h0-bottom', 'h0-hook')]
    paths.append(HERE.parent / 's22plus_v1/handoff.c')
    records = []
    for path in paths:
        target = out / 'source-snapshot' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = path.read_bytes()
        target.write_bytes(data)
        records.append(dict(path=str(path.relative_to(ROOT)), sha256=sha(target)))
    publish(out / 'source-inputs.json', records)
    return records


def inputs():
    archive = regular(BASE / 'rootfs-d/rootfs.tar')
    config = regular(BASE / 'kernel-build/.config')
    require(sha(archive) == ROOTFS_SHA and sha(regular(KERNEL)) == KERNEL_SHA and
            sha(config) == CONFIG_SHA, 'retained H0 construction inputs changed')
    for option in ('DEVTMPFS', 'FHANDLE'):
        require(f'# CONFIG_{option} is not set\n' in config.read_text(),
                'VM kernel no longer has selected FYG8 omission')
    return archive, config


def inside(out, packages):
    mapping = Path('/proc/self/uid_map').read_text().split()
    require(os.getuid() == 0 and mapping[:2] != ['0', '0'],
            'mapped-root namespace required')
    archive, config = inputs()
    tree = out / 'tree'
    tree.mkdir()
    run(['tar', '-xf', archive, '-C', tree, '--exclude=./dev/*', '--exclude=dev/*'],
        out / 'extract-rootfs.log')
    manifest = json.loads((packages / 'packages.json').read_text())
    require({row['package'] for row in manifest['packages']} == set(PACKAGES),
            'complete Debian build package set required')
    for row in manifest['packages']:
        path = regular(packages / row['file'])
        require(sha(path) == row['sha256'], 'Debian input package changed')
        run(['dpkg-deb', '-x', path, tree], out / (row['package'] + '.extract.log'))
    for name in ('null', 'zero', 'random', 'urandom'):
        path = tree / 'dev' / name
        path.touch()
        run(['mount', '--bind', '/dev/' + name, path], out / (name + '.mount.log'))
    (tree / 'proc').mkdir(exist_ok=True)
    run(['mount', '-t', 'proc', 'proc', tree / 'proc'], out / 'proc.mount.log')
    # Only the private builder tree is changed. No host package is installed.
    (tree / 'lab').mkdir()
    for name in ('rootfs.meta', 'rootfs.sha256'):
        shutil.copyfile(BASE / 'vm-final-4' / name, tree / 'lab' / name)
    shutil.copyfile(out / 'h0-root-check', tree / 'usr/sbin/h0-root-check')
    (tree / 'usr/sbin/h0-root-check').chmod(0o755)
    conf = tree / 'etc/initramfs-tools'
    for name in ('conf.d', 'hooks', 'scripts/init-bottom'):
        (conf / name).mkdir(parents=True, exist_ok=True)
    (conf / 'initramfs.conf').write_text(
        'MODULES=list\nBUSYBOX=y\nCOMPRESS=gzip\nKEYMAP=n\nRESUME=none\n')
    (conf / 'modules').write_text('')
    for source, target in [('h0-hook', 'hooks/h0'), ('h0-dev', 'scripts/h0-dev'),
                           ('h0-boot', 'scripts/h0-boot'), ('h0-bottom', 'scripts/init-bottom/h0')]:
        shutil.copyfile(HERE / source, conf / target)
        (conf / target).chmod(0o755)
    init = tree / 'usr/share/initramfs-tools/init'
    original = init.read_text()
    needle = 'mount -t devtmpfs -o nosuid,mode=0755 udev /dev\n'
    require(original.count(needle) == 1, 'Debian early /dev sequence changed')
    adapted = original.replace(needle, '. /scripts/h0-dev\n')
    init.write_text(adapted)
    (out / 'debian-init.original').write_text(original)
    (out / 'debian-init.adapted').write_text(adapted)
    (out / 'debian-init.patch').write_text(''.join(difflib.unified_diff(
        original.splitlines(True), adapted.splitlines(True), fromfile='Debian-0.148.4/init',
        tofile='H0-port/init')))
    (tree / 'boot').mkdir(exist_ok=True)
    shutil.copyfile(config, tree / 'boot' / ('config-' + VERSION))
    modules = tree / 'usr/lib/modules' / VERSION
    modules.mkdir(parents=True, exist_ok=True)
    for name in ('modules.builtin', 'modules.builtin.modinfo', 'modules.order'):
        source = BASE / 'kernel-build' / name
        if source.is_file():
            shutil.copyfile(source, modules / name)
        else:
            require(name == 'modules.order' and '# CONFIG_MODULES is not set\n' in config.read_text(),
                    'missing module build metadata')
            (modules / name).write_text('')
    settings = dict(os.environ, SOURCE_DATE_EPOCH=EPOCH, LC_ALL='C', TZ='UTC')
    for label in ('a', 'b'):
        run(['chroot', tree, '/usr/sbin/mkinitramfs', '-v', '-c', 'gzip',
             '-o', '/lab/initramfs-' + label + '.cpio.gz', VERSION],
            out / ('mkinitramfs-' + label + '.log'), env=settings, timeout=300)
        shutil.copyfile(tree / 'lab' / ('initramfs-' + label + '.cpio.gz'),
                        out / ('initramfs-' + label + '.cpio.gz'))


def build(out, packages):
    out = private(out, fresh=True)
    packages = private(packages)
    inputs()
    verify_packages(packages, out)
    sources = snapshot_sources(out)
    require(int(EPOCH) <= time.time(), 'construction epoch must not be in the future')
    binding_inputs = {}
    for name in ('vm-uuid', 'rootfs.meta', 'rootfs.sha256'):
        source = regular(BASE / 'vm-final-4' / name)
        binding_inputs[name] = dict(path=str(source.relative_to(ROOT)), sha256=sha(source))
    identity = uuid.UUID((BASE / 'vm-final-4/vm-uuid').read_text().strip())
    (out / 'binding.h').write_text('static const unsigned char root_uuid[16] = {' +
                                  ','.join(str(x) for x in identity.bytes) + '};\n')
    run(['aarch64-linux-gnu-gcc', '-static', '-Os', '-Wall', '-Wextra', '-Werror',
         '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
         '-fno-ident', '-Wl,--build-id=none', '-I', out, HERE / 'root-check.c',
         '-o', out / 'h0-root-check'], out / 'compile.log')
    run(['file', out / 'h0-root-check'], out / 'file.log')
    symbols = subprocess.check_output(['aarch64-linux-gnu-nm', out / 'h0-root-check'])
    require(b'unused_old_pid1' not in symbols, 'old PID1 code was not discarded')
    (out / 'symbols.txt').write_bytes(symbols)
    run(['unshare', '--user', '--map-auto', '--map-root-user', '--mount', '--pid',
         '--fork', '--mount-proc', sys.executable, __file__, 'inside', '--output', out,
         '--packages', packages], out / 'namespace-build.log', timeout=700)
    require(sha(out / 'initramfs-a.cpio.gz') == sha(out / 'initramfs-b.cpio.gz'),
            'Debian mkinitramfs outputs are not reproducible')
    for source in sources:
        require(sha(ROOT / source['path']) == source['sha256'], 'source changed during construction')
    for value in binding_inputs.values():
        require(sha(ROOT / value['path']) == value['sha256'], 'binding input changed during construction')
    publish(out / 'build.json', dict(scope='H0 ARM64 virt only', device_actions=0,
            initramfs_sha256=sha(out / 'initramfs-a.cpio.gz'),
            original_init_sha256=sha(out / 'debian-init.original'),
            adapted_init_sha256=sha(out / 'debian-init.adapted'),
            helper_sha256=sha(out / 'h0-root-check'), kernel_sha256=KERNEL_SHA,
            config_sha256=CONFIG_SHA, rootfs_archive_sha256=ROOTFS_SHA,
            packages_manifest_sha256=sha(packages / 'packages.json'),
            binding_header_sha256=sha(out / 'binding.h'), binding_inputs=binding_inputs,
            source_inputs=sources, ab_identical=True))
    print('PASS: Debian mkinitramfs A/B construction; target unqualified')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('fetch', 'build', 'inside'):
        command = sub.add_parser(action)
        command.add_argument('--output', type=Path, required=True)
        if action != 'fetch':
            command.add_argument('--packages', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'fetch':
        fetch(args.output)
    elif args.action == 'build':
        build(args.output, args.packages)
    else:
        inside(private(args.output), private(args.packages))
