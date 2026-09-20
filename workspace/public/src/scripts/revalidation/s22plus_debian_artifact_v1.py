#!/usr/bin/env python3
"""Read-only joins of actual Debian boot bytes and retained ARM64 evidence.

This is H0 qualification, never device authority. The virtual-board execution
and physical FYG8 artifact have separate identities and explicit substitutions.
"""
import argparse
from dataclasses import replace
import gzip
import io
import ipaddress
import lzma
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import tarfile
import tempfile

import device_action_raw_capture_v1 as raw
import s22plus_boot_verify as boot
import s22plus_boot_only_f1_transport as transport
import s22plus_debian_profile_v1 as declaration
from s22plus_native_records_v3 import digest, pin, private_path, publish, read, require, verify

ROOT = declaration.ROOT
SCHEMA = 's22plus-debian-device-qualification-v1'
LIMIT = 256 * 1024 * 1024
MUTABLE = {'etc/resolv.conf', 'etc/hostname', 'etc/mtab', 'etc/machine-id', 'etc/adjtime', 'etc/ld.so.cache'}
UFS = ('phy-qcom-ufs.ko', 'phy-qcom-ufs-qmp-v4-waipio.ko', 'tmecom-intf.ko', 'hwkm.ko',
       'crypto-qti-hwkm.ko', 'crypto-qti-common.ko', 'ufshcd-crypto-qti.ko', 'ufs_qcom.ko')
VENDOR_SHA = '41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193'


def bytes_at(receipt, maximum=LIMIT):
    return verify(receipt, maximum=maximum).read_bytes()


def sources(folder, receipts, *, current):
    names = [item['path'] for item in receipts]
    require(len(names) == len(set(names)), 'duplicate source provenance')
    for item in receipts:
        source = Path(item['path'])
        require(source.is_relative_to(ROOT / 'workspace/public/src'), 'source provenance leaves public source')
        saved = folder / 'source' / source.relative_to(ROOT)
        require(pin(saved) == dict(item, path=str(saved)), 'saved build provenance differs')
        if current or str(source.relative_to(ROOT)) in declaration.EXECUTION_FILES:
            verify(item, maximum=4 * 1024 * 1024)
    require({str(ROOT / name) for name in declaration.EXECUTION_FILES}.issubset(names),
            'build omits execution-critical source provenance')


def cpio(image):
    parsed = boot.parse_boot_v4(image)
    rows = boot.parse_newc(boot.decompress_lz4_stream_python(parsed.ramdisk, maximum=128 * 1024 * 1024))
    result = {row.name: row for row in rows}
    require(len(result) == len(rows), 'duplicate ramdisk member')
    return parsed, result


def static_arm64(body):
    require(len(body) >= 64 and body[:7] == b'\x7fELF\x02\x01\x01' and
            struct.unpack_from('<H', body, 18)[0] == 183, 'bootstrap is not little-endian ARM64 ELF')
    offset = struct.unpack_from('<Q', body, 32)[0]
    width, count = struct.unpack_from('<HH', body, 54)
    require(width >= 56 and count > 0 and offset + width * count <= len(body) and
            all(struct.unpack_from('<I', body, offset + width * i)[0] != 3 for i in range(count)),
            'bootstrap has an interpreter or invalid program table')


def archive_members(body):
    members = {}
    with tarfile.open(fileobj=io.BytesIO(body)) as archive:
        for item in archive:
            name = item.name
            require(name and not name.startswith('/') and str(PurePosixPath(name)) == name and
                    '..' not in PurePosixPath(name).parts and not any(c in name for c in '\r\n\\') and
                    name not in members and (item.isfile() or item.isdir() or item.issym() or item.islnk()),
                    'root archive has a noncanonical, duplicate or special member')
            members[name] = (item, archive.extractfile(item).read() if item.isfile() else b'')
    require(not any(name.startswith('dev/') for name in members), 'root archive installs device nodes')
    return members


def manifests(folder, members):
    for full, prefix in ((True, 'install'), (False, 'rootfs')):
        wanted = {name for name in members if full or (name not in MUTABLE and
            name.startswith(('etc/', 'usr/', 'home/lab/.ssh/', 'root/.ssh/')))} | {'bin', 'sbin', 'lib'}
        for name in list(wanted):
            wanted.update(str(p) for p in PurePosixPath(name).parents if str(p) != '.')
        metadata, hashes = bytearray(), []
        for name in sorted(wanted):
            item, body = members[name]
            if item.islnk():
                target_item, body = members[item.linkname]
                require(target_item.isfile(), 'root archive hardlink target is not a regular file')
            else:
                target_item = item
            kind = stat.S_IFLNK if item.issym() else stat.S_IFDIR if item.isdir() else stat.S_IFREG
            link = item.linkname.encode() if item.issym() else b''
            path = name.encode()
            metadata += struct.pack('<IIIQHH', kind | item.mode, item.uid, item.gid,
                len(link) if item.issym() else target_item.size, len(path), len(link)) + path + link
            if item.isfile() or item.islnk(): hashes.append(digest(body) + '  ' + name + '\n')
        require((folder / (prefix + '.meta')).read_bytes() == metadata and
                (folder / (prefix + '.sha256')).read_text() == ''.join(hashes),
                'archive content/metadata manifests differ: ' + prefix)


def replace_header(text, name, body):
    for pattern, replacement in (
        (rf'static const unsigned long long target_{name}_size=\d+ULL;',
         f'static const unsigned long long target_{name}_size={len(body)}ULL;'),
        (rf'static const unsigned char target_{name}_sha256\[\]=\{{[^}}]+\}};',
         f'static const unsigned char target_{name}_sha256[]={{' + ','.join(str(b) for b in bytes.fromhex(digest(body))) + '};')):
        text, count = re.subn(pattern, lambda _: replacement, text)
        require(count == 1, 'fixture header substitution is not unique')
    return text


def reproduce_virt_init(folder):
    with tempfile.TemporaryDirectory(prefix='s22-debian-h0-qualify-') as temporary:
        destination = Path(temporary) / 'init'
        command = ['aarch64-linux-gnu-gcc', '-std=gnu11', '-Os', '-static', '-fno-ident',
            '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections', '-DS22_DEBIAN_DEVICE',
            '-DS22_DEBIAN_VIRT_TEST', '-I', str(folder),
            str(ROOT / 'workspace/public/src/debian/s22plus_v1/handoff.c'), '-o', str(destination)]
        result = subprocess.run(command, capture_output=True, timeout=30)
        require(result.returncode == 0 and not result.stdout and not result.stderr,
                'retained ARM64 fixture init did not rebuild cleanly')
        require(destination.read_bytes() == (folder / 'init').read_bytes(),
                'retained ARM64 fixture init differs from its current matched critical sources/headers')


def vm_inputs(folder, product, vm_id, product_id):
    vm_sources = read(folder / 'build.json')['source_inputs']
    for name in ('virt-binding.inc.c', 'vm_install_test.py'):
        wanted = str(ROOT / 'workspace/public/src/debian/s22plus_v1/device' / name)
        selected = [r for r in vm_sources if r['path'] == wanted]
        require(len(selected) == 1, 'virtual fixture producer provenance is absent')
        verify(selected[0])
    for name in ('binding.h', 's22plus_native_ext4_seal_v1.h'):
        require((folder / name).read_bytes().replace(vm_id.encode(), b'CANDIDATE') ==
                (product / name).read_bytes().replace(product_id.encode(), b'CANDIDATE'),
                'virtual filesystem seal differs from physical candidate')
    tar_bytes = (folder / 'rootfs.tar').read_bytes()
    virtual_members = archive_members(tar_bytes)
    product_members = archive_members((product / 'rootfs.tar').read_bytes())
    substitutions = {'etc/default/lab-usb', 'etc/lab-device-id', 'etc/lab-native-version',
        'etc/ssh/ssh_host_ed25519_key', 'etc/ssh/ssh_host_ed25519_key.pub',
        'home/lab/.ssh/authorized_keys', 'root/.ssh/authorized_keys', 'etc/init.d/lab-usb'}
    def identity(member):
        item, body = member
        return item.type, item.mode, item.uid, item.gid, item.size, item.linkname, body
    for name in set(virtual_members) | set(product_members):
        if name in substitutions: continue
        require(name in virtual_members and name in product_members and
                identity(virtual_members[name]) == identity(product_members[name]),
                'virtual root differs beyond declared candidate/network data: ' + name)
    manifests(folder, virtual_members)
    require(lzma.decompress((folder / 'rootfs.tar.xz').read_bytes(), memlimit=LIMIT) == tar_bytes,
            'virtual archive compression differs')
    header = (product / 'target-plan.h').read_text()
    for name, file in [('archive', 'rootfs.tar.xz'), ('tar', 'rootfs.tar'), ('busybox', 'busybox')]:
        header = replace_header(header, name, (folder / file).read_bytes())
    header = header.replace(product_id, vm_id).replace(digest((product / 'rootfs.tar').read_bytes()), digest(tar_bytes))
    require(header == (folder / 'target-plan.h').read_text(), 'virtual bootstrap header differs beyond declared archive identity')
    reproduce_virt_init(folder)
    rows = boot.parse_newc(gzip.decompress((folder / 'initramfs.cpio.gz').read_bytes()))
    expected = {'bin': (stat.S_IFDIR | 0o755, b''), 'etc': (stat.S_IFDIR | 0o755, b'')}
    for name, file, mode in [('init', 'init', 0o750), ('bin/busybox', 'busybox', 0o755),
            ('etc/mdev.conf', 'mdev.conf', 0o644), ('rootfs.tar.xz', 'rootfs.tar.xz', 0o400),
            *[(name, name, 0o400) for name in ('rootfs.meta', 'rootfs.sha256', 'install.meta', 'install.sha256')]]:
        expected[name] = (stat.S_IFREG | mode, (folder / file).read_bytes())
    binding = read(verify(read(product / 'artifact.json')['filesystem_binding']))
    expected['s22-fs-e2fsck'] = (stat.S_IFREG | 0o500, bytes_at(binding['checker']))
    require(len(rows) == len(expected) and {row.name for row in rows} == set(expected), 'virtual initramfs inventory differs')
    for row in rows:
        mode, body = expected[row.name]
        require((row.mode, row.uid, row.gid, row.nlink, row.data) == (mode, 0, 0, 1, body),
                'virtual initramfs bytes differ: ' + row.name)
    return rows, tar_bytes


def validate_artifact(receipt):
    path = verify(receipt)
    folder = private_path(ROOT, path.parent)
    value = read(path)
    require(value['schema'] == 's22plus-debian-device-artifact-h0-v1' and
            value['status'] == 'H0_BUILT_NOT_DEVICE_QUALIFIED' and value['device_actions'] == 0 and
            value['namespace'] == declaration.NAMESPACE and value['version'] == declaration.VERSION and
            re.fullmatch('[0-9a-f]{32}', value['run_id']) and value['ab_identical'] is True,
            'artifact kind or candidate identity differs')
    sources(folder, value['source_inputs'], current=True)
    retained = value['retained_inputs']
    require(retained['result'] == declaration.RETAINED_RESULT and retained['platform_plan'] == declaration.PLATFORM_PLAN,
            'retained FYG8 origin differs')
    previous = read(verify(declaration.RETAINED_RESULT))
    baseline_image = bytes_at(dict(previous['candidate']['a']['boot_img'], path=str(declaration.RETAINED / 'candidate-a/boot.img')))
    baseline, old = cpio(baseline_image)
    image = bytes_at(value['boot'])
    require(len(image) == 96 * 1024 * 1024 and image == (folder / 'pack-b/boot.img').read_bytes(),
            'actual boot size or A/B identity differs')
    actual, entries = cpio(image)
    fixed_header = ('header_version', 'header_size', 'kernel_size', 'signature_size', 'os_version', 'cmdline',
                    'kernel_start', 'kernel_end', 'ramdisk_start')
    require(actual.kernel == baseline.kernel and digest(actual.kernel) == value['kernel_sha256'] and
            all(actual.header[key] == baseline.header[key] for key in fixed_header) and
            actual.signature == baseline.signature, 'retained kernel/boot envelope changed')
    footer, old_footer = boot.parse_avb_footer(image), boot.parse_avb_footer(baseline_image)
    require(all(footer[key] == old_footer[key] for key in ('version_major', 'version_minor', 'vbmeta_size', 'vbmeta_sha256')) and
            footer['original_image_size'] == actual.header['signature_end'] + 16 and
            image[actual.header['signature_end']:footer['original_image_size']] == b'SEANDROIDENFORCE' and
            footer['vbmeta_offset'] == boot.align(footer['original_image_size'], 4096) and
            not any(image[footer['original_image_size']:footer['vbmeta_offset']]) and
            not any(image[footer['vbmeta_offset'] + footer['vbmeta_size']:-64]), 'retained AVB/footer envelope differs')
    with transport.pin_boot_only_ap(Path(value['ap']['path']), label='Debian H0 qualification',
            expected_size=value['ap']['size'], expected_sha256=value['ap']['sha256']) as pinned:
        compressed = transport.read_boot_only_member(pinned, label='Debian H0 qualification')
        member = transport.boot_only_member_receipt(pinned, label='Debian H0 qualification')
    require(boot.decompress_lz4_stream_python(compressed, maximum=128 * 1024 * 1024) == image and
            bytes_at(value['ap']) == (folder / 'pack-b/AP.tar.md5').read_bytes(), 'AP/boot or AP A/B join differs')
    plan = re.findall(r'\{"([^"/]+\.ko)", "[^\"]+", "([^"\n]*)"\}', bytes_at(declaration.PLATFORM_PLAN).decode())
    require(len(plan) == 73 and not set(UFS) & {name for name, _ in plan}, 'retained module plan differs')
    plan += [(name, '') for name in UFS]
    vendor = retained['vendor']
    require(vendor['size'] == 21813545 and vendor['sha256'] == VENDOR_SHA, 'vendor source identity differs')
    vendor_bytes = Path(vendor['path']).read_bytes()  # Established read-only firmware storage alias.
    require(len(vendor_bytes) == vendor['size'] and digest(vendor_bytes) == VENDOR_SHA, 'vendor source bytes changed')
    stock = {row.name: row for row in boot.parse_newc(boot.decompress_lz4_stream_python(vendor_bytes, maximum=128 * 1024 * 1024))}
    expected_modules = []
    wanted = {'bin': (stat.S_IFDIR | 0o755, b''), 'etc': (stat.S_IFDIR | 0o755, b''),
              's22-modules': (stat.S_IFDIR | 0o755, b'')}
    for name, parameters in plan:
        source = old.get('lib/modules/' + name) or stock['lib/modules/' + name]
        expected_modules.append(dict(name=name, parameters=parameters, size=len(source.data), sha256=digest(source.data)))
        wanted['s22-modules/' + name] = (stat.S_IFREG | 0o400, source.data)
    require(value['modules'] == expected_modules, 'actual module order/source identity differs')
    binding = read(verify(value['filesystem_binding']))
    for name, source, mode in [('init', folder / 'init-a', 0o750), ('bin/busybox', folder / 'busybox', 0o755),
            ('rootfs.tar.xz', verify(value['compressed_rootfs'], maximum=LIMIT), 0o400),
            ('s22-fs-e2fsck', verify(binding['checker']), 0o500), ('etc/mdev.conf', folder / 'mdev.conf', 0o644),
            *[(name, folder / name, 0o400) for name in ('rootfs.meta', 'rootfs.sha256', 'install.meta', 'install.sha256')]]:
        wanted[name] = (stat.S_IFREG | mode, source.read_bytes())
    require(set(entries) == set(wanted), 'ramdisk inventory contains missing or unexpected members')
    for name, (mode, body) in wanted.items():
        item = entries[name]
        require((item.mode, item.uid, item.gid, item.nlink, item.data) == (mode, 0, 0, 1, body),
                'ramdisk content or metadata differs: ' + name)
    init = entries['init'].data
    static_arm64(init)
    require(init == (folder / 'init-b').read_bytes() and b'backend=s22plus-fyg8' in init and
            b'backend=h0-virt' not in init, 'device binary is not the physical-board build')
    rootfs = bytes_at(value['rootfs'])
    require(lzma.decompress(entries['rootfs.tar.xz'].data, memlimit=LIMIT) == rootfs,
            'compressed root archive differs')
    require(('S22_DEBIAN_INSTALL_V1 ' + value['run_id'] + ' ' + digest(rootfs) + '\n').encode() in init and
            bytes.fromhex(digest(rootfs)) in init and bytes.fromhex(digest(entries['rootfs.tar.xz'].data)) in init,
            'bootstrap archive identity differs')
    members = archive_members(rootfs)
    manifests(folder, members)
    for name, source in [('usr/local/sbin/lab-qualify', 'lab-qualify'), ('etc/init.d/lab-usb', 'lab-usb')]:
        require(members[name][1] == (ROOT / 'workspace/public/src/debian/s22plus_v1/device' / source).read_bytes(),
                'Debian execution service differs')
    require(members['etc/lab-native-version'][1] == (declaration.VERSION + '\n').encode() and
            members['etc/lab-device-id'][1] == ('S22PLUS_FYG8_DEBIAN_V1 ' + value['run_id'] + '\n').encode() and
            members['etc/fstab'][1] == b'' and 'etc/init.d/.legacy-bootordering' in members and
            'etc/cron.d/e2scrub_all' not in members, 'Debian identity or fixed startup differs')
    for name, (item, _) in members.items():
        if re.fullmatch(r'etc/rc[0-6S]\.d/[SK][0-9]+.+', name):
            require(PurePosixPath(item.linkname).name not in
                {'hwclock.sh', 'checkroot.sh', 'checkfs.sh', 'checkroot-bootclean.sh', 'lab-network'},
                'unqualified storage/network startup link remains')
    link = read(folder / 'link.json')
    require(set(link) == {'serial', 'device_mac', 'host_mac', 'device_address', 'host_address', 'ssh_address'} and
            link['serial'] == 's22debian' + value['run_id'][:16], 'USB link candidate binding differs')
    host, device = ipaddress.ip_interface(link['host_address']), ipaddress.ip_interface(link['device_address'])
    require(host.version == device.version == 4 and host.network == device.network and host.network.prefixlen == 30 and
            host.ip.is_link_local and device.ip.is_link_local and int(device.ip) == int(host.ip) + 1 and
            link['ssh_address'] == str(device.ip), 'local-only host/device address binding differs')
    config = ''.join(f'{key}={val}\n' for key, val in link.items() if key in {'serial', 'device_mac', 'host_mac', 'device_address'})
    # JSON serialization sorts keys; compare assignments independently of order.
    require(set(members['etc/default/lab-usb'][1].decode().splitlines()) == set(config.splitlines()), 'target USB configuration differs')
    for name in ('client-key', 'host-key'):
        pub = (folder / (name + '.pub')).read_bytes()
        actual_pub = subprocess.run(['ssh-keygen', '-y', '-f', folder / name], check=True,
            capture_output=True, timeout=5).stdout
        require(actual_pub.split()[:2] == pub.split()[:2], 'private/public SSH key binding differs')
    client = (folder / 'client-key.pub').read_bytes()
    require(members['home/lab/.ssh/authorized_keys'][1] == client and members['root/.ssh/authorized_keys'][1] ==
            b'restrict,command="/usr/local/sbin/lab-qualify" ' + client and
            members['etc/ssh/ssh_host_ed25519_key'][1] == (folder / 'host-key').read_bytes() and
            (folder / 'known_hosts').read_bytes() == link['ssh_address'].encode() + b' ' + (folder / 'host-key.pub').read_bytes(),
            'SSH identity or root command restriction differs')
    hello = read(folder / 'hello.json')
    require(members['usr/local/lib/lab-offline/hello.deb'][1] == bytes_at(hello['artifact']) and
            hello['package']['SHA256'] == hello['artifact']['sha256'], 'offline package bytes differ')
    return dict(run_id=value['run_id'], namespace=value['namespace'], version=value['version'], ap=value['ap'],
        member=member, filesystem_binding=value['filesystem_binding'], module_count=len(plan),
        rootfs=value['rootfs'], client_key=pin(folder / 'client-key'), known_hosts=pin(folder / 'known_hosts'),
        link=pin(folder / 'link.json'))


def vm_evidence(folder, negative, product):
    # Imported only for pure projections; importing never opens a device.
    import s22plus_debian_first_boot_v1 as owner
    result = read(folder / 'result.json')
    require(result['verdict'] == 'PASS_H0_ARM64_INSTALL_REBOOT_PERSIST_SHUTDOWN' and
            result['scope'] == 'VIRT_NOT_SAMSUNG' and result['device_actions'] == 0, 'ARM64 lifecycle evidence absent')
    build = read(verify(result['original_build']))
    sources(folder, build['source_inputs'], current=False)
    source_artifact = read(verify(build['artifact_source']))
    plan = dict(candidate=dict(run_id=source_artifact['run_id']))
    baseline, tar_bytes = vm_inputs(folder, product, source_artifact['run_id'], read(product / 'artifact.json')['run_id'])
    handles = {}
    def success(prefix, suffix):
        found = []
        for path in sorted(folder.glob(prefix + '*.capture.json')):
            handle = raw.load_handle(path)
            if handle.returncode == 0 and raw.read_stdout(handle, maximum=65536).endswith(suffix):
                raw.require_success(handle); found.append(handle)
        require(len(found) == 1, 'ARM64 terminal evidence is absent or ambiguous: ' + prefix)
        handles[prefix] = pin(found[0].receipt_path)
        return found[0]
    first = owner.project_debian(success('first-health-', b'DEBIAN_HEALTH_PASS\n'), plan)
    second = owner.project_debian(success('second-health-', b'DEBIAN_HEALTH_PASS\n'), plan)
    require(first['boot_count'] == 1 and second['boot_count'] == 2 and
            first['boot_id_sha256'] != second['boot_id_sha256'] and
            second['reboot_source_boot_sha256'] == first['boot_id_sha256'], 'ARM64 reboot/persistence continuity differs')
    success('workload-result-', b'DEBIAN_WORKLOAD_PASS\n')
    success('persistence-result', b'DEBIAN_WORKLOAD_PASS\n')
    pty = raw.load_handle(folder / 'pty.capture.json')
    require(pty.returncode == 0 and not pty.timed_out and not pty.output_exceeded and pty.producer_error_type is None and
            raw.read_stdout(pty, maximum=65536) == b'PTY_PASS\r\n' and
            raw.read_stderr(pty, maximum=16384) == b'Connection to 127.0.0.1 closed.\r\n', 'ARM64 PTY proof differs')
    handles['pty'] = pin(pty.receipt_path)
    for command in ('reboot', 'shutdown'):
        handle = raw.load_handle(folder / (command + '.capture.json'))
        owner.control_projection(handle, command, '127.0.0.1')
        handles[command] = pin(handle.receipt_path)
    bad = read(negative / 'result.json')
    require(bad['verdict'] == 'PASS_H0_ARM64_INSTALLER_NEGATIVES' and bad['scope'] == 'VIRT_NOT_SAMSUNG' and
            bad['device_actions'] == 0 and [r['case'] for r in bad['cases']] ==
            ['gpt-byte', 'wrong-uuid', 'witness', 'start-only', 'archive-digest', 'readback'], 'negative corpus differs')
    evidence = []
    for row in bad['cases']:
        case = negative / row['case']
        selected = tuple(baseline)
        if row['case'] == 'archive-digest':
            selected = tuple(replace(item, data=b'X' + item.data[1:]) if item.name == 'rootfs.tar.xz' else item for item in baseline)
        elif row['case'] == 'readback':
            with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as archive:
                offset = archive.getmember('usr/sbin/cron').offset_data
            altered = bytearray(tar_bytes); altered[offset] ^= 1; altered = bytes(altered)
            packed = lzma.compress(altered, preset=6)
            header = replace_header(replace_header((folder / 'target-plan.h').read_text(), 'tar', altered), 'archive', packed)
            require((case / 'target-plan.h').read_text() == header and
                    all((case / name).read_bytes() == (folder / name).read_bytes() for name in
                        ('binding.h', 's22plus_native_ext4_seal_v1.h')), 'readback fixture source/header mutation differs')
            reproduce_virt_init(case)
            selected = tuple(replace(item, data=packed) if item.name == 'rootfs.tar.xz' else
                replace(item, data=(case / 'init').read_bytes()) if item.name == 'init' else item for item in baseline)
        actual = boot.parse_newc(gzip.decompress((case / 'initramfs.cpio.gz').read_bytes()))
        require(actual == selected, 'negative initramfs does not join this VM baseline and declared mutation: ' + row['case'])
        require(read(case / 'result.json') == row and row['device_actions'] == 0 and
                row['before']['size'] == row['after']['size'] == 255202426880, 'negative fixture identity differs')
        log = (case / 'negative.serial.log').read_bytes()
        require(('BOOTSTRAP_STOP stage=' + row['expected_stop'] + ' ').encode() in log and
                b'DEBIAN_INSTALL_COMPLETE' not in log and b'BOOTSTRAP_HANDOFF' not in log, 'negative typed stop absent')
        if row['case'] == 'readback':
            require(row['before'] != row['after'] and row['unchanged'] is False and row['consumed_no_replay'] is True and
                    b'DEBIAN_INSTALL_INTENT_DURABLE' in log, 'partial install was not preserved')
            retry = (case / 'no-replay.serial.log').read_bytes()
            require(b'BOOTSTRAP_STOP stage=target-storage-binding ' in retry and
                    b'DEBIAN_INSTALL_INTENT_DURABLE' not in retry, 'partial installation replayed')
            evidence.append(pin(case / 'no-replay.serial.log'))
        else:
            require(row['before'] == row['after'] and row['unchanged'] is True and row['consumed_no_replay'] is False,
                    'prewrite negative changed the sparse disk')
        evidence += [pin(case / 'result.json'), pin(case / 'negative.serial.log'), pin(case / 'initramfs.cpio.gz', maximum=LIMIT)]
    return dict(build=result['original_build'], lifecycle=pin(folder / 'result.json'), raw=handles,
        negatives=pin(negative / 'result.json'), negative_evidence=evidence,
        limits=['virtual board discovery, module loading and Ethernet replace FYG8 hardware',
                'matched critical C and qualification service; separate candidate keys, version and root archive identities',
                'no Samsung boot, USB, storage-write, poweroff or physical recovery proof'])


def qualify(artifact, vm, negative):
    return dict(schema=SCHEMA, verdict='PASS_H0_READY_FOR_ATTENDED_PREPARATION', device_actions=0,
        artifact=artifact, actual=validate_artifact(artifact), evidence=vm_evidence(vm, negative, Path(artifact['path']).parent),
        vm_directory=str(vm), negative_directory=str(negative))


def revalidate(receipt):
    value = read(verify(receipt))
    current = qualify(value['artifact'], private_path(ROOT, Path(value['vm_directory'])),
                      private_path(ROOT, Path(value['negative_directory'])))
    require(value == current, 'retained artifact qualification no longer rederives')
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--vm', type=Path, required=True)
    parser.add_argument('--negative', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    publish(private_path(ROOT, args.output, exists=False), qualify(pin(args.artifact.resolve(strict=True)),
        private_path(ROOT, args.vm), private_path(ROOT, args.negative)))
