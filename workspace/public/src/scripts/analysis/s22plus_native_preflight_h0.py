"""Build the fixed archive-free, read-only bootstrap measurement on the host."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / 'workspace/public/src/debian/s22plus_v1'
DEVICE = BASE / 'device'
sys.path[:0] = [str(BASE), str(ROOT / 'workspace/public/src/scripts/revalidation')]
import h0
import s22plus_native_root_inspect_profile_v1 as retained
from s22plus_native_records_v3 import pin, publish, read, require, verify

SOURCE_FILES = (Path(__file__), BASE / 'handoff.c', DEVICE / 'target.inc.c',
    DEVICE / 'preflight.inc.c', DEVICE / 'preflight_record.h', DEVICE / 'preflight_read.c',
    ROOT / 'workspace/public/src/native-init/s22plus_native_ext4_v1.c',
    ROOT / 'workspace/public/src/native-init/s22plus_native_ext4_core_v1.h',
    ROOT / 'workspace/public/src/native-init/s22plus_fyg8_max77705_result_parser.inc.c')
MEMBERS = {'s22-prehandoff': ('init-a', 0o500), 's22-prehandoff-read': ('reader-a', 0o500),
    's22-fs-e2fsck': ('checker', 0o500), 'rootfs.meta': ('rootfs.meta', 0o400),
    'rootfs.sha256': ('rootfs.sha256', 0o400), 'busybox': ('busybox', 0o500)}


def c_bytes(name, data):
    return 'static const unsigned char ' + name + '[]={' + ','.join(map(str, data)) + '};\n'


def plan(run_id, artifact):
    require(re.fullmatch('[0-9a-f]{32}', run_id) is not None, 'preflight run identity differs')
    with tarfile.open(verify(artifact['rootfs'], maximum=256*1024*1024)) as archive:
        cache = archive.extractfile('etc/ld.so.cache').read()
    return (c_bytes('bp_run_id', bytes.fromhex(run_id)) +
        'static const char bp_run_hex[]=' + json.dumps(run_id) + ';\n' +
        f'static const unsigned long long bp_cache_size={len(cache)}ULL;\n' +
        c_bytes('bp_cache_sha256', hashlib.sha256(cache).digest())).encode()


def compile_pair(out, source, name, *, virt=False, includes=()):
    command = ['aarch64-linux-gnu-gcc', '-std=gnu11', '-Os', '-static', '-fno-ident',
        '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections', '-Wall',
        '-DS22_DEBIAN_DEVICE', '-DS22_DEBIAN_INSTALLED_ONLY', '-DS22_DEBIAN_PREFLIGHT',
        '-I', str(out)]
    if virt: command.append('-DS22_DEBIAN_VIRT_TEST')
    for directory in includes: command += ['-I', str(directory)]
    for side in 'ab':
        h0.run([*command, source, '-o', out / (name+'-'+side)], out / (name+'-'+side+'.log'))
    require((out/(name+'-a')).read_bytes() == (out/(name+'-b')).read_bytes(), 'preflight A/B differs')
    h0.run(['file', out/(name+'-a')], out/(name+'-file.log'))
    require(b'ARM aarch64' in (out/(name+'-file.log')).read_bytes() and
        b'statically linked' in (out/(name+'-file.log')).read_bytes(), 'preflight ELF differs')


def build(out, run_id):
    require(not out.exists() and out.is_relative_to(ROOT/'workspace/private/outputs'), 'fresh private build required')
    artifact, _, _ = retained.prior_inputs()
    old = Path(artifact['rootfs']['path']).parent
    out.mkdir(mode=0o700, parents=True)
    for name in ('binding.h', 's22plus_native_ext4_seal_v1.h', 'rootfs.meta', 'rootfs.sha256', 'busybox'):
        shutil.copyfile(old/name, out/name)
    # Only immutable member paths change; module order/bytes/parameters remain P405's.
    original_plan = (old/'target-plan.h').read_bytes()
    require(original_plan.count(b'/s22-modules/') == 81 and b'/lib/modules/' not in original_plan,
        'retained preparation module plan differs')
    (out/'target-plan.h').write_bytes(original_plan.replace(b'/s22-modules/', b'/lib/modules/'))
    (out/'preflight-plan.h').write_bytes(plan(run_id, artifact))
    binding = read(verify(artifact['filesystem_binding']))
    shutil.copyfile(verify(binding['checker']), out/'checker')
    compile_pair(out, BASE/'handoff.c', 'init')
    compile_pair(out, DEVICE/'preflight_read.c', 'reader')
    body = (out/'init-a').read_bytes()
    require(b'partition-ro' in body and b'installed-root-not-complete' in body and
        all(word not in body for word in (b'/rootfs.tar.xz', b'BOOTSTRAP_HANDOFF', b'switch_root',
            b'p404-lab-qualify', b'DEBIAN_INSTALL_INTENT_DURABLE', b'errors=remount-ro')),
        'preflight retains a write or root transition branch')
    result = dict(schema='s22plus-native-preflight-helper-h0-v1', run_id_hex=run_id,
        artifact=retained.ARTIFACT, ab_identical=True,
        source_inputs=[pin(path, maximum=4*1024*1024) for path in SOURCE_FILES],
        inputs={name:pin(out/name) for name in ('binding.h', 's22plus_native_ext4_seal_v1.h',
            'target-plan.h', 'preflight-plan.h')},
        members={name:dict(file=pin(out/file), mode=mode) for name,(file,mode) in MEMBERS.items()})
    publish(out/'result.json', result)
    return audit(out, run_id)


def audit(out, run_id):
    value = read(out/'result.json')
    artifact, _, _ = retained.prior_inputs()
    old = Path(artifact['rootfs']['path']).parent
    require(value['schema']=='s22plus-native-preflight-helper-h0-v1' and value['run_id_hex']==run_id
        and value['artifact']==retained.ARTIFACT and value['ab_identical'] is True
        and value['source_inputs']==[pin(path, maximum=4*1024*1024) for path in SOURCE_FILES],
        'preflight source identity differs')
    for row in value['inputs'].values(): verify(row)
    require((out/'preflight-plan.h').read_bytes()==plan(run_id,artifact)
        and (out/'target-plan.h').read_bytes()==(old/'target-plan.h').read_bytes().replace(b'/s22-modules/',b'/lib/modules/'),
        'preflight generated plans differ')
    require(set(value['members'])==set(MEMBERS), 'preflight member set differs')
    for name,(file,mode) in MEMBERS.items():
        require(value['members'][name]==dict(file=pin(out/file),mode=mode), 'preflight member differs')
    for name in ('init','reader'):
        require((out/(name+'-a')).read_bytes()==(out/(name+'-b')).read_bytes(), 'preflight retained A/B differs')
    return value
