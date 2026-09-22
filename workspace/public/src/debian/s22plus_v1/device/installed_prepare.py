#!/usr/bin/env python3
"""H0-only P404 boot package using the installed P401 root; no archive producer."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[4]
sys.path[:0] = [str(BASE), str(ROOT / 'workspace/public/src/scripts/analysis'),
               str(ROOT / 'workspace/public/src/scripts/revalidation')]
import h0
import s22plus_native_thermal_build_v1 as packaging
from s22plus_native_records_v3 import pin, publish, read, require, verify

SCHEMA = 's22plus-debian-installed-boot-h0-v1'
P401 = ROOT / 'workspace/private/outputs/s22plus-debian-device-prep-20260921-1'
ARTIFACT = dict(path=str(P401 / 'artifact-7/artifact.json'), size=48870,
    sha256='bca7f42259a8e2f30806dfbf11ad213406f17959b9d38113cf5dca95c9ca2d17')
QUALIFIED = dict(path=str(P401 / 'qualification-7.json'), size=9683,
    sha256='a422fab3084612abdad5d3d6ddfc51bf6f3fb9bada5dd7c3893c47c8b0707689')
P403 = ROOT / 'workspace/private/outputs/s22plus-debian-userspace-probe-h0-20260923-1/prepared-1/task'
TERMINAL = dict(path=str(P403 / 'operation-0001/terminal.json'), size=3135,
    sha256='5a567a34ff3262a3dfafc516a4f6d264db1f526b7f384546cf570b5d95f76136')
CLOSED = dict(path=str(P403 / 'closed.json'), size=2954,
    sha256='56e28886e2c22c02158dc3ad28be1224a715d8a5543bf810c637c7eb0606918f')
P399_AP = dict(path=str(ROOT / 'workspace/private/outputs/s22plus-native-ext4-v1/p399/build-1/candidate-a/odin4/AP.tar.md5'),
    size=33372201, sha256='d7f1d82d12af63a45bf9e179560ae100f76316d3543f19a02a8f35acc56ec3df')
P399 = ROOT / 'workspace/private/runs/s22plus-native-session-v3/p399-p400-native-ext4-20260917-1'
P399_ADMISSION = dict(path=str(P399 / 'operation-0001/admission.json'), size=31321,
    sha256='daa4a9e12fe7edfee3bf9ac54e5066809cf60729033101a9a333d0d04e59a1ca')


def source_inputs():
    selected = [Path(__file__), BASE / 'handoff.c', HERE / 'target.inc.c',
        HERE / 'lab-qualify',
        ROOT / 'workspace/public/src/native-init/s22plus_native_ext4_v1.c',
        ROOT / 'workspace/public/src/native-init/s22plus_native_ext4_core_v1.h',
        ROOT / 'workspace/public/src/native-init/s22plus_fyg8_max77705_result_parser.inc.c']
    return [pin(path, maximum=4 * 1024 * 1024) for path in selected]


def inputs():
    artifact = read(verify(ARTIFACT)); qualification = read(verify(QUALIFIED))
    require(qualification['artifact'] == ARTIFACT and
            qualification['verdict'] == 'PASS_H0_READY_FOR_ATTENDED_PREPARATION' and
            artifact['schema'] == 's22plus-debian-device-artifact-h0-v1' and
            artifact['namespace'] == 'p401' and artifact['version'] == 'v0.4.0-rc.1' and
            artifact['ab_identical'] is True, 'retained P401 producer or qualification differs')
    terminal = read(verify(TERMINAL)); closed = read(verify(CLOSED))
    proof = terminal['userspace_probe']
    require(closed['current_android_terminal'] == TERMINAL and
            closed['terminal_state'] == terminal['terminal_state'] == 'ANDROID_CLOSED_HEALTHY' and
            closed['f1_owner_absent'] is True and proof['userspace_proved'] is True and
            proof['root_inspection']['comparison']['matched'] == 8969 and
            proof['root_inspection']['markers'] == dict(start=1, complete=1, witness=1),
            'P403 did not prove the fixed installed root and Android close')
    admission = read(verify(P399_ADMISSION))
    require(admission['schema'] == 's22plus-native-admission-v3' and
            read(verify(admission['terminal']))['terminal_state'] == 'NATIVE_CLOSED_HEALTHY',
            'P399 native admission differs')
    verify(P399_AP, maximum=128 * 1024 * 1024)
    return artifact


def compile_init(output, old):
    source = BASE / 'handoff.c'
    command = ['aarch64-linux-gnu-gcc', '-std=gnu11', '-Os', '-static', '-fno-ident',
        '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections', '-DS22_DEBIAN_DEVICE',
        '-I', str(old), str(source)]
    legacy = output / 'init-legacy-check'
    h0.run([*command, '-o', legacy], output / 'compile-legacy.log')
    require(legacy.read_bytes() == (old / 'init-a').read_bytes(),
            'P401 code path changed before installed-only selection')
    binaries = []
    for side in 'ab':
        path = output / ('init-' + side)
        h0.run([*command, '-I', output, '-DS22_DEBIAN_INSTALLED_ONLY', '-o', path],
               output / ('compile-' + side + '.log'))
        binaries.append(path)
    require(binaries[0].read_bytes() == binaries[1].read_bytes(),
            'installed-only bootstrap A/B differs')
    body = binaries[0].read_bytes()
    require(b'installed-root-not-complete' in body and b'BOOTSTRAP_HANDOFF' in body and
            all(forbidden not in body for forbidden in (b'/rootfs.tar.xz', b'DEBIAN_INSTALL_INTENT_DURABLE',
                b'DEBIAN_INSTALL_COMPLETE', b'/install.meta', b'/install.sha256')),
            'installed-only bootstrap retains an archive or installation path')
    h0.run(['file', binaries[0]], output / 'file.log')
    return binaries[0]


def shutdown_overlay_bytes():
    source = (HERE / 'lab-qualify').read_bytes()
    fixed = b'test "$(cat /var/lib/lab/boot-count)" = 2'
    require(source.count(fixed) == 1, 'P401 shutdown count predicate differs')
    return source.replace(fixed, b'test "$(cat /var/lib/lab/boot-count)" -ge 1')


def shutdown_overlay(output, old):
    import tarfile
    source = (HERE / 'lab-qualify').read_bytes()
    with tarfile.open(old / 'rootfs.tar') as archive:
        installed = archive.extractfile('usr/local/sbin/lab-qualify').read()
    require(source == installed, 'installed P401 qualification command differs')
    replacement = shutdown_overlay_bytes()
    script = output / 'p404-lab-qualify'
    script.write_bytes(replacement)
    script.chmod(0o500)
    (output / 'installed-plan.h').write_text(
        f'static const unsigned long long target_qualify_size={len(replacement)}ULL;\n'
        'static const unsigned char target_qualify_sha256[]={' +
        ','.join(str(x) for x in hashlib.sha256(replacement).digest()) + '};\n')
    return script


def build(output):
    output = output.absolute()
    require(output.parent.is_relative_to(ROOT / 'workspace/private/outputs') and
            output.resolve() == output and not output.exists(), 'fresh private output required')
    original = inputs()
    old = P401 / 'artifact-7'
    verify(original['boot'], maximum=128 * 1024 * 1024)
    output.mkdir(mode=0o700)
    selected = source_inputs()
    overlay = shutdown_overlay(output, old)
    executable = compile_init(output, old)
    baseline = Path(original['boot']['path']).read_bytes()
    parsed, before = packaging.shared.entries(baseline)
    remove = {'rootfs.tar.xz', 'install.meta', 'install.sha256'}
    require(remove <= set(before) and all(before[name].data == (old / name).read_bytes() for name in remove),
            'P401 archive/installation ramdisk inputs differ')
    entries = []
    for name, row in before.items():
        if name in remove: continue
        require(row.uid == row.gid == 0 and row.nlink == 1, 'retained ramdisk metadata differs')
        entries.append((name, row.mode, executable.read_bytes() if name == 'init' else row.data))
    entries.append(('p404-lab-qualify', stat.S_IFREG | 0o500, overlay.read_bytes()))
    require(any(name == 'init' for name, _, _ in entries), 'retained initramfs has no init')
    ramdisk = h0.newc(entries)
    (output / 'ramdisk.cpio').write_bytes(ramdisk)
    tools = packaging.shared.packager._bind_tools()
    for side in 'ab':
        folder = output / ('pack-' + side); folder.mkdir(mode=0o700)
        shutil.copyfile(original['boot']['path'], folder / 'base.img')
        with (folder / 'unpack.log').open('wb') as log:
            subprocess.run([tools['magiskboot'], 'unpack', '-h', str(folder / 'base.img')],
                           cwd=folder, stdout=log, stderr=subprocess.STDOUT, check=True)
        (folder / 'ramdisk.cpio').write_bytes(ramdisk)
        with (folder / 'repack.log').open('wb') as log:
            subprocess.run([tools['magiskboot'], 'repack', 'base.img', 'boot.img'],
                           cwd=folder, stdout=log, stderr=subprocess.STDOUT, check=True)
        image = (folder / 'boot.img').read_bytes()
        actual, inventory = packaging.shared.entries(image)
        require(actual.kernel == parsed.kernel and len(image) == len(baseline) and
                set(inventory) == {name for name, _, _ in entries} and
                all((inventory[name].mode, inventory[name].uid, inventory[name].gid,
                    inventory[name].nlink, inventory[name].data) == (mode, 0, 0, 1, data)
                    for name, mode, data in entries), 'P404 boot/ramdisk join differs')
        h0.run([tools['lz4'], '--content-size', '-B6', '-f', '-q', folder / 'boot.img',
                folder / 'boot.img.lz4'], folder / 'lz4.log')
        packaging.shared.packager._write_deterministic_boot_ap(
            (folder / 'boot.img.lz4').read_bytes(), folder / 'AP.tar.md5')
    require((output / 'pack-a/AP.tar.md5').read_bytes() == (output / 'pack-b/AP.tar.md5').read_bytes(),
            'P404 AP A/B differs')
    for receipt in selected: verify(receipt, maximum=4 * 1024 * 1024)
    result = dict(schema=SCHEMA, status='H0_BUILT_NOT_QUALIFIED', namespace='p404',
        version='v0.4.0-rc.4', run_id=uuid.uuid4().hex, source_inputs=selected,
        p401_artifact=ARTIFACT, p401_qualification=QUALIFIED,
        installed_root_proof=TERMINAL, installed_root_close=CLOSED,
        baseline_native=dict(ap=P399_AP, admission=P399_ADMISSION),
        boot=pin(output / 'pack-a/boot.img', maximum=128 * 1024 * 1024),
        ap=pin(output / 'pack-a/AP.tar.md5', maximum=128 * 1024 * 1024),
        init=pin(executable), removed_members=sorted(remove),
        shutdown_overlay=pin(overlay),
        ramdisk_sha256=hashlib.sha256(ramdisk).hexdigest(), ab_identical=True,
        device_actions=0, grants_device_authority=False)
    return publish(output / 'artifact.json', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    result = build(parser.parse_args().output)
    print(json.dumps({k: result[k] for k in ('size', 'sha256')}))
