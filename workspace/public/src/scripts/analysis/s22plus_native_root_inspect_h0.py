"""Build the bounded ARM64 inspector and its table from the consumed P401 tar."""
import hashlib
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s22plus_native_root_inspect_profile_v1 as profile
import s22plus_native_ext4_h0 as fs_build
import s22plus_debian_artifact_v1 as archive
from s22plus_native_records_v3 import pin, private_path, publish, read, require, verify

NATIVE = ROOT / 'workspace/public/src/native-init'
SOURCE_FILES = (
    Path(__file__), Path(profile.__file__),
    NATIVE / 's22plus_native_root_inspect_v1.c',
    NATIVE / 's22plus_native_ext4_v1.c', NATIVE / 's22plus_native_ext4_core_v1.h',
    NATIVE / 's22plus_fyg8_max77705_result_parser.inc.c',
)


def table_bytes():
    artifact, _, _ = profile.prior_inputs()
    body = verify(artifact['rootfs'], maximum=256 * 1024 * 1024).read_bytes()
    members = archive.archive_members(body)
    archive.manifests(Path(artifact['rootfs']['path']).parent, members)
    boot = {name for name in members if name not in archive.MUTABLE and
        name.startswith(('etc/', 'usr/', 'home/lab/.ssh/', 'root/.ssh/'))} | {'bin', 'sbin', 'lib'}
    for name in list(boot):
        boot.update(str(p) for p in Path(name).parents if str(p) != '.')
    require(0 < len(members) <= 20000 and boot <= set(members), 'inspection archive inventory exceeds bounds')
    output = bytearray(b'S22RI01\0' + struct.pack('<I', len(members)))
    for name, (item, data) in sorted(members.items()):
        original = item
        if item.islnk():
            item, data = members[item.linkname]
            require(item.isfile(), 'inspection hardlink target is not a regular file')
        kind = stat.S_IFDIR if original.isdir() else stat.S_IFLNK if original.issym() else stat.S_IFREG
        path = name.encode(); link = original.linkname.encode() if original.issym() else b''
        size = len(link) if original.issym() else item.size if item.isfile() else 0
        require(len(path) < 4096 and len(link) < 4096 and len(name.split('/')) <= 32,
            'inspection path exceeds bounds')
        output += struct.pack('<IIIQHH', kind | original.mode, original.uid, original.gid, size, len(path), len(link))
        output += hashlib.sha256(data).digest() if kind == stat.S_IFREG else bytes(32)
        output += bytes([name in boot]) + path + link
    require(len(output) <= 2 * 1024 * 1024, 'inspection table exceeds bound')
    return bytes(output), len(members), len(boot)


def header(table, count, boot_count):
    artifact, _, _ = profile.prior_inputs()
    identity = f'S22_DEBIAN_INSTALL_V1 {artifact["run_id"]} {artifact["rootfs"]["sha256"]}\\n'
    return ('/* Private generated P401 comparison identity. */\n'
        f'static const uint64_t ri_table_size={len(table)}ULL;\n'
        f'static const unsigned ri_table_count={count}U;\n'
        f'static const unsigned ri_boot_count={boot_count}U;\n'
        'static const uint8_t ri_table_sha256[32]={' + ','.join(map(str, hashlib.sha256(table).digest())) + '};\n'
        f'static const char ri_install_identity[]="{identity}";\n').encode()


def binding(folder, helper):
    value = read(folder / 'result.json')
    return dict(binding=profile.filesystem.BINDING, artifact=profile.ARTIFACT, terminal=profile.TERMINAL,
        helper=helper, table=value['table'], table_count=value['table_count'], boot_count=value['boot_count'],
        max_hashed_bytes=512 * 1024 * 1024, kernel_partition_ro=True, persistent_writes=False)


def build(output, run_id, *, virt=False):
    output = private_path(ROOT, output, exists=False)
    require(not output.exists(), 'fresh root inspector build output required')
    sources = [pin(path, maximum=4 * 1024 * 1024) for path in SOURCE_FILES]
    if virt:
        sources.append(pin(ROOT / 'workspace/public/src/debian/s22plus_v1/device/virt-binding.inc.c'))
    table, count, boot_count = table_bytes()
    output.mkdir(mode=0o700, parents=True)
    (output / 's22plus_native_ext4_seal_v1.h').write_bytes(fs_build.seal(profile.filesystem.BINDING, run_id, initialize=False))
    (output / 's22plus_native_root_inspect_seal_v1.h').write_bytes(header(table, count, boot_count))
    (output / 'table.bin').write_bytes(table)
    flags = ['-std=c11', '-static', '-Os', '-fno-ident', '-ffunction-sections', '-fdata-sections',
        '-Wl,--gc-sections', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-Wno-unused-const-variable',
        '-I', output, '-I', NATIVE]
    if virt: flags += ['-DS22_ROOT_INSPECT_VIRT_TEST']
    compiler = shutil.which('aarch64-linux-gnu-gcc')
    require(compiler is not None, 'ARM64 compiler absent')
    compiler_pin = fs_build.compiler_identity(compiler)
    for side in ('a', 'b'):
        fs_build.run([compiler, *flags, NATIVE / 's22plus_native_root_inspect_v1.c', '-o', output / ('helper-' + side)],
            cwd=ROOT, stdout=output / ('compile-' + side + '.log'), timeout=60)
    require((output / 'helper-a').read_bytes() == (output / 'helper-b').read_bytes(), 'inspector A/B differs')
    value = dict(schema=profile.SCHEMA + '-helper-h0', source_inputs=sources, run_id_hex=run_id,
        artifact=profile.ARTIFACT, terminal=profile.TERMINAL, filesystem_binding=profile.filesystem.BINDING,
        table=pin(output / 'table.bin'), table_count=count, boot_count=boot_count,
        helper=fs_build.tool_identity(output / 'helper-a'), ab_identical=True, compiler=compiler_pin,
        virt=virt, device_effects=0, live_authorized=False)
    require(fs_build.compiler_identity(compiler) == compiler_pin, 'inspector compiler changed')
    for receipt in sources: verify(receipt, maximum=4 * 1024 * 1024)
    return publish(output / 'result.json', value)


def audit(folder, run_id):
    value = read(folder / 'result.json')
    require(value['schema'] == profile.SCHEMA + '-helper-h0' and value['virt'] is False and
        value['run_id_hex'] == run_id and value['artifact'] == profile.ARTIFACT and value['terminal'] == profile.TERMINAL and
        value['filesystem_binding'] == profile.filesystem.BINDING and value['ab_identical'] is True and
        value['source_inputs'] == [pin(path, maximum=4 * 1024 * 1024) for path in SOURCE_FILES],
        'inspector source or consumed comparison identity differs')
    table, count, boot_count = table_bytes()
    require(verify(value['table']).read_bytes() == table and value['table_count'] == count and value['boot_count'] == boot_count and
        (folder / 's22plus_native_root_inspect_seal_v1.h').read_bytes() == header(table, count, boot_count) and
        (folder / 's22plus_native_ext4_seal_v1.h').read_bytes() == fs_build.seal(profile.filesystem.BINDING, run_id, initialize=False),
        'compiled inspector table or seal differs')
    require((folder / 'helper-a').read_bytes() == (folder / 'helper-b').read_bytes() and
        fs_build.tool_identity(folder / 'helper-a') == value['helper'], 'inspector actual binary differs')
    return value


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--virt', action='store_true')
    args = parser.parse_args()
    print(build(args.output, args.run_id, virt=args.virt)['sha256'])
