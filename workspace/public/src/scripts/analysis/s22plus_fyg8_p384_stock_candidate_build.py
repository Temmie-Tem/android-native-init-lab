#!/usr/bin/env python3
"""Build the direct P384 local runtime on the frozen P383 platform; H0 only."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'workspace/public/src/scripts/revalidation')]
import s22plus_fyg8_p384_candidate as candidate
import s22plus_native_source_v1 as direct
import s22plus_native_candidate_artifacts_v1 as artifacts
import s22plus_fyg8_p319_stock_candidate_build as packager
import s22plus_memory_manifest_v1 as memory
import s22plus_boot_verify as boot

REFERENCE = ROOT/'workspace/private/outputs/s22plus-fyg8-v0.2.0-rc.1/candidate-build-verified'
REFERENCE_RESULT = dict(size=109545, sha256='50ba11b7114374bec18a4c0e2c11161ab2317d1805baba6c59e8762328b46597')
REFERENCE_IDENTITY = direct.Identity('p383', 'c383f1e0a90b5e6d7c8a9b0c0d2e3f0b', 'v0.2.0-rc.1')
DEFAULT_OUTPUT_ROOT = ROOT/'workspace/private/outputs/s22plus-fyg8-v0.2.0-rc.2/candidate-build-verified'
HEADERS = ROOT/'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/include/uapi/drm'
SCHEMA = 's22plus-fyg8-p384-stock-candidate-build-v1'
VERDICT = 'PASS_P384_STOCK_CANDIDATE_BUILD_H0'
TARGET = dict(model='SM-S906N', codename='g0q', build='S906NKSS7FYG8')
RENDERER_FLAGS = ('-static', '-O2', '-Wall', '-Wextra', '-Werror', '-Wl,--build-id=none', '-DP350_DISPLAY_VARIANT')

identity = artifacts.identity
stable = artifacts.stable_bytes


def canonical(value): return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def write(path, raw):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    path.chmod(0o400)


def source_receipts():
    paths = set(direct.source_files()) | {Path(__file__), Path(candidate.__file__), Path(artifacts.__file__),
        Path(memory.__file__), Path(packager.__file__), Path(boot.__file__)}
    paths.update(artifacts.reference_source_files())
    paths.update(ROOT/path for path in (
        'workspace/public/src/scripts/analysis/s22plus_fyg8_p350_stock_candidate_build.py',
        'workspace/public/src/scripts/revalidation/s22plus_fyg8_p241_e2_static_checker.py',
        'workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1b_candidate_static_checker.py'))
    return {str(p.relative_to(ROOT)): identity(stable(p)) for p in sorted(paths)}


def reference_inputs():
    # The actual emitted platform C, Image and module bytes are pinned inputs.
    # Historical runtime generators do not regenerate platform C. The retained
    # image/archive parser loaders are separately bound in source_receipts().
    value = json.loads(stable(REFERENCE/'result.json', expected=REFERENCE_RESULT))
    if value['run_id_hex'] != REFERENCE_IDENTITY.run_id_hex: raise ValueError('frozen platform identity differs')
    sources = {name: stable(REFERENCE/'stock-sources'/name, expected=pin) for name, pin in value['source_closure'].items()}
    return value, sources


def join_runtime(raw):
    match = re.findall(rb'static const uint8_t p328_auth_key\[P328_AUTH_KEY_SIZE\] = \{ ([^}]+) \};', raw)
    if len(match) != 1: raise ValueError('frozen platform key declaration differs')
    key = bytes(int(x.strip().removesuffix(b'U'), 16) for x in match[0].split(b','))
    if identity(key) != candidate.AUTH_KEY_IDENTITY: raise ValueError('frozen key identity differs')
    joined = direct.join_platform(raw, REFERENCE_IDENTITY, key, profile=direct.LOCAL_PROFILE)
    before = direct.materialize_helper(REFERENCE_IDENTITY, key, profile=direct.LOCAL_PROFILE)
    after = direct.materialize_helper(candidate.IDENTITY, key, profile=direct.LOCAL_PROFILE)
    if joined.count(before) != 1: raise ValueError('direct local helper join differs')
    result = joined.replace(before, after, 1)
    if REFERENCE_IDENTITY.run_id_hex.encode() in result or b'p383' in result or b'P383' in result:
        raise ValueError('frozen candidate namespace remains in selected runtime')
    return result


def run(argv, cwd, log):
    environment = os.environ.copy()
    for key in packager.COMPILER_ENVIRONMENT_KEYS: environment.pop(key, None)
    environment.update(LANG='C', LC_ALL='C', SOURCE_DATE_EPOCH='0')
    try:
        result = subprocess.run([str(x) for x in argv], cwd=cwd, env=environment,
            stdin=subprocess.DEVNULL, capture_output=True, timeout=180)
    except subprocess.TimeoutExpired as exc:
        write(log, (exc.stdout or b'')+(exc.stderr or b'')); raise
    write(log, result.stdout+result.stderr)
    if result.returncode: raise ValueError('host build failed; see '+str(log))
    return result.stdout


def entries(raw):
    parsed = boot.parse_boot_v4(raw)
    values = boot.parse_newc(boot.decompress_lz4_stream_python(parsed.ramdisk, maximum=128*1024*1024))
    rows = {row.name: row for row in values}
    if len(rows) != len(values): raise ValueError('duplicate boot ramdisk entry')
    return parsed, rows


def row_identity(row):
    return dict(mode=row.mode, uid=row.uid, gid=row.gid, nlink=row.nlink, mtime=row.mtime, **identity(row.data))


def check_boot(raw, baseline, image, init, renderer):
    parsed, rows = entries(raw); _, old = entries(baseline)
    if len(raw) != len(baseline) or set(rows) != set(old) or parsed.kernel != image:
        raise ValueError('candidate boot layout/inventory/Image differs')
    replacements = {'init': init, 's22-display': renderer}
    for name, original in old.items():
        expected = dict(row_identity(original))
        if name in replacements: expected.update(identity(replacements[name]))
        if row_identity(rows[name]) != expected: raise ValueError('candidate ramdisk entry differs: '+name)
    return {name: row_identity(row) for name, row in sorted(rows.items())}


def build_package(out, label, baseline, image, init, renderer, tools):
    scratch = Path(tempfile.mkdtemp(prefix='pack-'+label+'-', dir=out))
    try:
        write(scratch/'base.img', baseline)
        run([tools['magiskboot'], 'unpack', '-h', scratch/'base.img'], scratch, scratch/'unpack.log')
        (scratch/'kernel').write_bytes(image)
        write(scratch/'new-init', init); write(scratch/'new-display', renderer)
        run([tools['magiskboot'], 'cpio', scratch/'ramdisk.cpio', 'add 750 init '+str(scratch/'new-init'),
             'add 750 s22-display '+str(scratch/'new-display')], scratch, scratch/'cpio.log')
        run([tools['magiskboot'], 'repack', scratch/'base.img', scratch/'boot.img'], scratch, scratch/'repack.log')
        raw = stable(scratch/'boot.img'); inventory = check_boot(raw, baseline, image, init, renderer)
        folder = out/('candidate-'+label); folder.mkdir(mode=0o700)
        write(folder/'boot.img', raw)
        run([tools['lz4'], '--content-size', '-B6', '-f', '-q', folder/'boot.img', folder/'boot.img.lz4'], scratch, scratch/'lz4.log')
        (folder/'boot.img.lz4').chmod(0o400)
        structure = packager._write_deterministic_boot_ap(stable(folder/'boot.img.lz4'), folder/'odin4/AP.tar.md5')
        (folder/'odin4/AP.tar.md5').chmod(0o400)
        for log in scratch.glob('*.log'): write(out/'packaging-logs'/label/log.name, stable(log))
        value = dict(boot_img=identity(raw), boot_img_lz4=identity(stable(folder/'boot.img.lz4')),
            ap_tar_md5=identity(stable(folder/'odin4/AP.tar.md5')), inventory=inventory, ap_structure=structure)
    except BaseException:
        write(scratch/'FAILED_H0.json', canonical(dict(output=str(out), role=label)))
        raise
    else:
        shutil.rmtree(scratch)  # Only this successful invocation's private scratch.
    return value


def build_result(output_root=DEFAULT_OUTPUT_ROOT, *, audit_only=False):
    if audit_only: return audit_existing(output_root)
    out = Path(output_root).absolute()
    if out.exists() or out.is_symlink() or not out.resolve().is_relative_to((ROOT/'workspace/private').resolve()):
        raise ValueError('fresh private build output required')
    reference, sources = reference_inputs(); pins = source_receipts()
    print('SOURCE_KEYS', json.dumps(sorted(pins)), flush=True)
    for name, pin in reference['toolchain_inputs'].items(): stable(Path(name), expected=pin)
    out.mkdir(mode=0o700, parents=True); write(out/'source-inputs.json', canonical(pins))
    for name, raw in sources.items():
        write(out/'stock-sources'/name, join_runtime(raw) if name == packager.RUNTIME_INCLUDE_NAME else raw)
    write(out/'inputs/child-source.c', stable(REFERENCE/'inputs/child-source.c', expected=packager.CHILD_SOURCE_IDENTITY))
    image, transform = candidate.artifact.transform_image(stable(REFERENCE/'inputs/fixed-Image', expected=reference['image']))
    write(out/'inputs/fixed-Image', image)
    census = tuple(direct.MemoryModule(*row) for row in memory.manifest())
    renderer_source = direct.render_display(candidate.IDENTITY, census, profile=candidate.PROFILE)
    write(out/'inputs/renderer.c', renderer_source)
    write(out/'inputs/s22plus_native_display_plan.h', stable(REFERENCE/'inputs/s22plus_native_display_plan.h', expected=reference['module_plan']))
    write(out/'configuration.json', canonical(dict(identity=asdict(candidate.IDENTITY), profile=direct.profile_contract(candidate.PROFILE),
        memory_modules=[asdict(row) for row in census], reference_result=REFERENCE_RESULT)))
    tools = packager._bind_tools(); previous = packager.RUN_ID
    try:
        packager.RUN_ID = bytes.fromhex(candidate.IDENTITY.run_id_hex)
        userspace = [packager._compile_userspace(out/'stock-sources', out/('userspace-'+label), label='p384-'+label)
                     for label in ('a', 'b')]
    finally: packager.RUN_ID = previous
    if userspace[0] != userspace[1]: raise ValueError('native userspace A/B differs')
    compiler = [tools['gcc'], *RENDERER_FLAGS, '-I', out/'inputs', '-I', HEADERS,
                '-I', direct.NATIVE, out/'inputs/renderer.c']
    for label in ('a', 'b'):
        run([*compiler, '-o', out/('renderer-'+label)], out, out/('renderer-'+label+'.log'))
        (out/('renderer-'+label)).chmod(0o400)
    init = stable(out/'userspace-a/init'); renderer = stable(out/'renderer-a')
    candidate.artifact._validate_init(init)
    if renderer != stable(out/'renderer-b'): raise ValueError('renderer A/B differs')
    for name, path in (('init', out/'userspace-a/init'), ('renderer', out/'renderer-a')):
        info = run([tools['file'], '-b', path], out, out/(name+'-file.log'))
        headers = run([tools['readelf'], '-W', '-l', path], out, out/(name+'-readelf.log'))
        if b'ARM aarch64' not in info or b'statically linked' not in info or b'INTERP' in headers:
            raise ValueError('candidate static ARM64 ELF differs')
    baseline = stable(REFERENCE/'candidate-a/boot.img', expected=reference['candidate']['a']['boot_img'])
    packages = {label: build_package(out, label, baseline, image, init, renderer, tools) for label in ('a', 'b')}
    if packages['a'] != packages['b']: raise ValueError('candidate package A/B differs')
    if source_receipts() != pins: raise ValueError('candidate sources changed during build')
    for name, pin in reference['toolchain_inputs'].items(): stable(Path(name), expected=pin)
    packager._bind_tools()
    value = dict(schema=SCHEMA, verdict=VERDICT, run_id_hex=candidate.IDENTITY.run_id_hex, target=TARGET,
        source_inputs=pins, source_closure={p.name: identity(stable(p)) for p in (out/'stock-sources').iterdir()},
        reference_result=REFERENCE_RESULT, configuration=identity(stable(out/'configuration.json')),
        toolchain_inputs=reference['toolchain_inputs'], tools=packager.TOOL_IDENTITIES,
        image=identity(image), image_transform=transform, init=identity(init), renderer=identity(renderer),
        child=userspace[0]['child'], candidate=packages, module_plan=reference['module_plan'],
        module_bytes=reference['module_bytes'], byte_identical=True, platform_inputs_frozen=True,
        scope=dict(tier='H0', device_contact=False, candidate_transfers=0, rollback_transfers=0, live_authorized=False))
    write(out/'result.json', canonical(value))
    return audit_existing(out)


def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    out = Path(output_root).absolute(); value = json.loads(stable(out/'result.json'))
    if value.get('schema') != SCHEMA or value.get('verdict') != VERDICT or value.get('run_id_hex') != candidate.IDENTITY.run_id_hex:
        raise ValueError('candidate build result identity differs')
    if value['source_inputs'] != source_receipts() or value['reference_result'] != REFERENCE_RESULT:
        raise ValueError('candidate source binding differs')
    reference, sources = reference_inputs()
    for name, raw in sources.items():
        expected = join_runtime(raw) if name == packager.RUNTIME_INCLUDE_NAME else raw
        if stable(out/'stock-sources'/name, expected=value['source_closure'][name]) != expected:
            raise ValueError('candidate platform source join differs')
    baseline = stable(REFERENCE/'candidate-a/boot.img', expected=reference['candidate']['a']['boot_img'])
    image = stable(out/'inputs/fixed-Image', expected=value['image']); candidate.artifact.validate_image(image)
    init = stable(out/'userspace-a/init', expected=value['init']); renderer = stable(out/'renderer-a', expected=value['renderer'])
    stable(out/'userspace-b/init', expected=value['init']); stable(out/'renderer-b', expected=value['renderer'])
    for label in ('a', 'b'):
        folder = out/('candidate-'+label); package = value['candidate'][label]
        raw = stable(folder/'boot.img', expected=package['boot_img'])
        if check_boot(raw, baseline, image, init, renderer) != package['inventory']: raise ValueError('candidate boot inventory differs')
        stable(folder/'boot.img.lz4', expected=package['boot_img_lz4'])
        candidate.artifact.inspect_ap(folder/'odin4/AP.tar.md5', expected_ap=package['ap_tar_md5'], expected_image=image,
            expected_init=init, expected_child=stable(out/('userspace-'+label)/'s22-e1-child', expected=value['child']))
    if value['candidate']['a'] != value['candidate']['b']: raise ValueError('retained candidate A/B differs')
    for path, pin in value['toolchain_inputs'].items(): stable(Path(path), expected=pin)
    packager._bind_tools()
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args(); result = build_result(args.out, audit_only=args.audit_only)
    print(json.dumps(dict(verdict=result['verdict'], ap=result['candidate']['a']['ap_tar_md5']), sort_keys=True))
