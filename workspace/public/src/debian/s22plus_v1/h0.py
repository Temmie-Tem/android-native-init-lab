#!/usr/bin/env python3
"""Host-only construction of the Debian/SysVinit prototype and virt test pair.

Every output is a regular file below workspace/private. No connected transport
or block-device argument exists. A virt test is not Samsung UFS qualification.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
EPOCH = 1789776000  # 2026-09-19 UTC; fixed, before construction.
PACKAGES = ('sysvinit-core', 'sysvinit-utils', 'sysv-rc', 'initscripts',
            'busybox-static', 'e2fsprogs', 'util-linux', 'kmod', 'procps',
            'iproute2', 'ifupdown', 'openssh-server', 'ca-certificates', 'cron')
FEATURES = ('has_journal,ext_attr,dir_index,filetype,extent,64bit,flex_bg,'
            'sparse_super,large_file,huge_file,dir_nlink,extra_isize,metadata_csum')
PROVIDER_ROOTS = ('qcom_hwspinlock', 'smem', 'qcom_scm', 'cmd_db',
    'gdsc_regulator', 'clk_qcom', 'gcc_waipio', 'qcom_iommu_util', 'qnoc_qos',
    'pinctrl_msm', 'pinctrl_waipio', 'qcom_rpmh', 'clk_rpmh', 'rpmh_regulator',
    'icc_bcm_voter', 'icc_rpmh', 'qnoc_waipio', 'arm_smmu', 'spmi_pmic_arb',
    'regmap_spmi', 'qcom_spmi_pmic')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def private_output(value):
    path = Path(value).absolute()
    if path.resolve() != path or not path.is_relative_to(ROOT / 'workspace/private'):
        raise ValueError('output must be a direct private path')
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    return path


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def run(command, log, env=None):
    with log.open('wb') as stream:
        subprocess.run([str(x) for x in command], env=env, check=True,
                       stdout=stream, stderr=subprocess.STDOUT)


def rootfs(out, key, lock=None):
    key = Path(key).resolve(strict=True)
    if (out / 'rootfs.tar').exists():
        raise ValueError('rootfs output already exists')
    packages = list(PACKAGES)
    if lock:
        packages = [f'{p}={v}' for p, v, _ in
                    (line.split('\t') for line in Path(lock).read_text().splitlines())]
    command = ['unshare', '--user', '--map-auto', '--map-root-user', '--mount',
               '--pid', '--fork', '--mount-proc', 'mmdebstrap', '--mode=root',
               '--architectures=arm64', '--variant=minbase',
               '--include=' + ','.join(packages),
               '--keyring=/usr/share/keyrings/debian-archive-keyring.gpg',
               '--aptopt=Acquire::Languages "none"',
               '--extract-hook=' + str(HERE / 'retain-packages.sh'),
               '--customize-hook=' + str(HERE / 'customize.sh'), '--verbose',
               'trixie', out / 'rootfs.tar',
               'deb https://deb.debian.org/debian trixie main',
               'deb https://security.debian.org/debian-security trixie-security main']
    settings = dict(LAB_SOURCE=str(HERE), LAB_OUTPUT=str(out), LAB_AUTH_KEY=str(key),
                    SOURCE_DATE_EPOCH=str(EPOCH), TZ='UTC', LC_ALL='C.UTF-8')
    write_json(out / 'command.json', dict(argv=[str(x) for x in command], env=settings))
    run(command, out / 'build.log', dict(os.environ, **settings))
    write_json(out / 'archive.json', dict(sha256=digest((out / 'rootfs.tar').read_bytes()),
                                         size=(out / 'rootfs.tar').stat().st_size))


def newc(entries):
    """Small deterministic newc writer; directories/files/symlinks only."""
    result = bytearray()
    for ino, (name, mode, data) in enumerate([*entries, ('TRAILER!!!', 0, b'')], 1):
        encoded = name.encode() + b'\0'
        fields = [ino, mode, 0, 0, 1, EPOCH, len(data), 0, 0, 0, 0, len(encoded), 0]
        result.extend(b'070701' + ''.join(f'{v:08x}' for v in fields).encode())
        result.extend(encoded)
        result.extend(b'\0' * (-len(result) % 4))
        result.extend(data)
        result.extend(b'\0' * (-len(result) % 4))
    return bytes(result)


def image_inside(out, archive):
    # The subuid mapping preserves Debian owners without running host-root.
    mapping = Path('/proc/self/uid_map').read_text().split()
    if os.getuid() != 0 or len(mapping) < 3 or mapping[:2] == ['0', '0']:
        raise ValueError('isolated mapped-root namespace required')
    tree = out / 'tree'
    tree.mkdir(mode=0o755)
    subprocess.run(['tar', '-xf', archive, '-C', tree, '--exclude=./dev/*'], check=True)
    (tree / 'etc/default/lab-network').write_text('interface=eth0\n')
    # VM evidence helpers are deliberately outside the reusable rootfs archive.
    (tree / 'etc/lab-h0-virt').write_text('VIRTUAL_MACHINE_ONLY\n')
    # Root SSH is confined to the virt image and a loopback-only QEMU forward.
    # It lets the H0 harness exercise service shutdown and normal reboot.
    (tree / 'etc/ssh/sshd_config.d/00-h0.conf').write_text(
        'PermitRootLogin prohibit-password\nAllowUsers root lab\n')
    (tree / 'root/.ssh').mkdir(mode=0o700, exist_ok=True)
    (tree / 'root/.ssh').chmod(0o700)
    shutil.copyfile(tree / 'home/lab/.ssh/authorized_keys', tree / 'root/.ssh/authorized_keys')
    (tree / 'root/.ssh/authorized_keys').chmod(0o600)
    disk = out / 'root.ext4'
    with disk.open('xb') as stream:
        stream.truncate(1536 * 1024 * 1024)
    vm_uuid = uuid.UUID((out / 'vm-uuid').read_text().strip())
    run(['mke2fs', '-q', '-F', '-t', 'ext4', '-b', '4096', '-I', '256', '-m', '0',
         '-L', 'S22H0', '-U', str(vm_uuid), '-O', 'none,' + FEATURES,
         '-E', 'nodiscard,lazy_itable_init=0,lazy_journal_init=0,root_owner=0:0',
         '-d', tree, disk], out / 'mke2fs.log')
    # Hash regular execution/configuration inputs, excluding first-boot changes.
    mutable = {'etc/resolv.conf', 'etc/hostname', 'etc/mtab', 'etc/machine-id',
               'etc/adjtime', 'etc/ld.so.cache'}
    lines, metadata, bound = [], bytearray(), {}
    for p in sorted(tree.rglob('*')):
        rel = p.relative_to(tree).as_posix()
        if (p.is_symlink() or not p.is_file() or rel in mutable or
                not rel.startswith(('usr/', 'etc/', 'home/lab/.ssh/', 'root/.ssh/'))):
            continue
        lines.append(f'{digest(p.read_bytes())}  {rel}\n')
        bound[rel] = p
    for p in sorted(tree.rglob('*')):
        rel = p.relative_to(tree).as_posix()
        if p.is_symlink() and rel not in mutable and rel.startswith(('usr/', 'etc/')):
            bound[rel] = p
    for name in ('bin', 'sbin', 'lib'):
        bound[name] = tree / name
    for p in list(bound.values()):
        for parent in p.parents:
            if parent == tree:
                break
            bound[parent.relative_to(tree).as_posix()] = parent
    for rel, p in sorted(bound.items()):
        st = p.lstat()
        path = rel.encode()
        link = os.readlink(p).encode() if p.is_symlink() else b''
        if len(path) >= 4096 or len(link) >= 4096:
            raise ValueError('overlong metadata binding')
        metadata.extend(struct.pack('<IIIQHH', st.st_mode, st.st_uid, st.st_gid,
                                     st.st_size, len(path), len(link)) + path + link)
    (out / 'rootfs.sha256').write_text(''.join(lines))
    (out / 'rootfs.meta').write_bytes(metadata)
    shutil.copyfile(tree / 'usr/bin/busybox', out / 'busybox')
    shutil.copyfile(tree / 'etc/mdev.conf', out / 'mdev.conf')


def vm_image(out, archive):
    archive = Path(archive).resolve(strict=True)
    (out / 'vm-uuid').write_text(str(uuid.uuid4()) + '\n')
    run(['unshare', '--user', '--map-auto', '--map-root-user', '--mount', '--pid',
         '--fork', '--mount-proc', sys.executable, __file__, 'image-inside',
         '--output', out, '--archive', archive], out / 'image-build.log')
    initramfs(out)


def initramfs(out):
    vm_uuid = uuid.UUID((out / 'vm-uuid').read_text().strip())
    (out / 'binding.h').write_text('static const unsigned char root_uuid[16] = {' +
                                   ','.join(str(x) for x in vm_uuid.bytes) + '};\n')
    run(['aarch64-linux-gnu-gcc', '-static', '-Os', '-Wall', '-Wextra', '-Werror',
         '-fno-ident', '-Wl,--build-id=none', '-I', out, HERE / 'handoff.c',
         '-o', out / 'init'], out / 'compile.log')
    entries = [(name, stat.S_IFDIR | 0o755, b'') for name in
               ['bin', 'etc', 'dev', 'proc', 'sys', 'run', 'newroot']]
    entries += [('init', stat.S_IFREG | 0o755, (out / 'init').read_bytes()),
                ('bin/busybox', stat.S_IFREG | 0o755, (out / 'busybox').read_bytes()),
                ('etc/mdev.conf', stat.S_IFREG | 0o644, (out / 'mdev.conf').read_bytes()),
                ('rootfs.meta', stat.S_IFREG | 0o444, (out / 'rootfs.meta').read_bytes()),
                ('rootfs.sha256', stat.S_IFREG | 0o444, (out / 'rootfs.sha256').read_bytes())]
    (out / 'initramfs.cpio.gz').write_bytes(gzip.compress(newc(entries), mtime=0))
    write_json(out / 'pair.json', dict(scope='H0 virt; no Samsung boot qualification',
        device_actions=0, init_sha256=digest((out / 'init').read_bytes()),
        initramfs_sha256=digest((out / 'initramfs.cpio.gz').read_bytes()),
        rootfs_manifest_sha256=digest((out / 'rootfs.sha256').read_bytes())))


def dependency_order(rows, roots):
    ordered, visiting = [], set()
    def visit(name):
        if name in ordered:
            return
        if name in visiting:
            raise ValueError('module dependency cycle: ' + name)
        visiting.add(name)
        for dependency in rows[name]['depends']:
            visit(dependency)
        visiting.remove(name)
        ordered.append(name)
    for name in roots:
        visit(name)
    return ordered


def storage(out):
    # Reuse the exact retained FYG8 vendor-archive verifier, never a live tool.
    sys.path[:0] = [str(ROOT / 'workspace/public/src/scripts/analysis'),
                    str(ROOT / 'workspace/public/src/scripts/revalidation')]
    import s22plus_memory_manifest_v1 as memory
    import s22plus_native_ufs_build_v1 as ufs
    provenance = ufs.stock_inputs()
    vendor = memory.vendor
    raw = memory.base.stable(ROOT / vendor.DEFAULT_VENDOR_RAMDISK,
        dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE,
             sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256))
    entries = memory.boot_verify.parse_newc(
        memory.boot_verify.decompress_lz4_stream_python(raw, maximum=128 * 1024 * 1024))
    inventory = out / 'inventory'
    inventory.mkdir()
    rows = {}
    for entry in entries:
        if not entry.name.startswith('lib/modules/') or not entry.name.endswith('.ko'):
            continue
        name = Path(entry.name).name
        if entry.name != 'lib/modules/' + name or (entry.mode, entry.uid, entry.gid, entry.nlink) != (0o100644, 0, 0, 1):
            raise ValueError('unexpected stock module metadata')
        path = inventory / name
        path.write_bytes(entry.data)
        def info(field):
            return subprocess.check_output(['modinfo', '-F', field, path], text=True).strip()
        runtime, deps, version = info('name'), info('depends'), info('vermagic')
        if version != '5.10.226-android12-9-gki-30958166-abS906NKSS7FYG8 SMP preempt mod_unload modversions aarch64':
            raise ValueError('unexpected module kernel')
        key = runtime.replace('-', '_')
        if key in rows:
            raise ValueError('duplicate runtime module name')
        rows[key] = dict(name=name, runtime_name=runtime, vermagic=version,
            depends=[d.replace('-', '_') for d in deps.split(',')] if deps else [],
            size=len(entry.data), sha256=digest(entry.data))
    roots = [*PROVIDER_ROOTS, *[m[1] for m in ufs.source.MODULES]]
    selected = [rows[name] for name in dependency_order(rows, roots)]
    write_json(out / 'storage-plan.json', dict(active=False, device_actions=0,
        claim='prospective provider roots and symbol closure; hardware readiness unproved',
        provenance=provenance, roots=roots, modules=selected))
    module_dir = out / 's22-storage'
    module_dir.mkdir()
    header = ['struct storage_module { const char *name; unsigned long long size; unsigned char sha256[32]; };',
              'static const struct storage_module storage_plan[] = {']
    for row in selected:
        shutil.copyfile(inventory / row['name'], module_dir / row['name'])
        (module_dir / row['name']).chmod(0o644)
        header.append('{"%s", %dULL, {%s}},' % (row['name'], row['size'],
            ','.join(str(x) for x in bytes.fromhex(row['sha256']))))
    (out / 'storage-plan.h').write_text('\n'.join(header) + '\n};\n')
    run(['aarch64-linux-gnu-gcc', '-c', '-Os', '-Wall', '-Wextra', '-Werror',
         '-Wno-unused-function', '-fno-ident', '-I', out, HERE / 'storage.c',
         '-o', out / 'storage.o'], out / 'compile.log')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['rootfs', 'vm-image', 'image-inside', 'initramfs', 'storage'])
    parser.add_argument('--output', required=True)
    parser.add_argument('--authorized-key')
    parser.add_argument('--lock')
    parser.add_argument('--archive')
    args = parser.parse_args()
    out = private_output(args.output)
    if args.phase == 'rootfs':
        rootfs(out, args.authorized_key, args.lock)
    elif args.phase == 'vm-image':
        vm_image(out, args.archive)
    elif args.phase == 'image-inside':
        image_inside(out, args.archive)
    elif args.phase == 'initramfs':
        initramfs(out)
    else:
        storage(out)


if __name__ == '__main__':
    main()
