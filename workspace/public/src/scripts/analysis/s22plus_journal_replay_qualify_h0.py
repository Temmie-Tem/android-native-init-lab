#!/usr/bin/env python3
"""Actual ARM64 replay, revocation and failure fixtures on fresh regular files."""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import re
import shlex
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s22plus_native_ext4_h0 as base
import s22plus_journal_replay_tool_h0 as producer
from s22plus_native_records_v3 import pin, private_path, publish, read, require, verify

BLOCKS = 131072
UUID = '11111111-2222-4333-8444-555555555555'
FIXTURE_SOURCE = base.ROOT / 'tests/s22plus_journal_replay_io_fault.c'
RESULT = re.compile(rb'S22_JOURNAL_REPLAY_V1 stage=(\d+) writes=(\d+) bytes=(\d+) error=(\d+) io_error=(\d+) complete=([01])\n$')


def run(argv, out, label, *, env=None, expected=0):
    result = subprocess.run(list(map(str, argv)), capture_output=True, timeout=90,
                            env=env or dict(PATH='/usr/bin:/bin', LC_ALL='C'))
    (out / (label + '.stdout')).write_bytes(result.stdout)
    (out / (label + '.stderr')).write_bytes(result.stderr)
    if expected is not None:
        require(result.returncode == expected, label + ' process failed')
    return result


def copy(source, target):
    subprocess.run(['cp', '--reflink=auto', '--sparse=always', '--', source, target], check=True)


def block(path, number):
    with path.open('rb') as file:
        file.seek(number * 4096)
        return file.read(4096)


def modify_super(path, mutation, *, checksum=True):
    with path.open('r+b') as file:
        file.seek(1024); raw = bytearray(file.read(1024)); mutation(raw)
        if checksum: struct.pack_into('<I', raw, 0x3fc, base.profile.crc32c(raw[:0x3fc]))
        file.seek(1024); file.write(raw)


def compare(before, after):
    changed = []
    before_hash = hashlib.sha256(); after_hash = hashlib.sha256()
    with before.open('rb') as a, after.open('rb') as b:
        for start in range(0, BLOCKS, 256):
            x, y = a.read(4096 * 256), b.read(4096 * 256)
            require(len(x) == len(y) == 4096 * 256, 'fixture was truncated')
            before_hash.update(x); after_hash.update(y)
            if x != y:
                changed.extend(start + n for n in range(256)
                               if x[n*4096:(n+1)*4096] != y[n*4096:(n+1)*4096])
    return dict(before=before_hash.hexdigest(), after=after_hash.hexdigest(), changed_blocks=changed)


def qualify(build_receipt, out):
    build_receipt = private_path(base.ROOT, build_receipt)
    out = private_path(base.ROOT, out, exists=False)
    require(not out.exists(), 'fresh qualification output required')
    value = read(build_receipt); request = read(verify(value['request']))
    require(value['fixture_only'] is True and request['fixture_only'] is True, 'fixture tool required')
    tool = Path(verify(value['replayer']))
    image = out / 'native.img'
    require(Path(verify(request['seal'])).read_bytes() == producer.seal(UUID,
            fixture_path=image, fixture_blocks=BLOCKS), 'fixture tool target differs')
    out.mkdir(mode=0o700, parents=True)
    clean = out / 'clean.img'
    with clean.open('xb') as file: file.truncate(BLOCKS * 4096)
    config = out / 'mke2fs.conf'; config.write_bytes(base.profile.CONFIG)
    formatter = base.ROOT / 'workspace/private/outputs/s22plus-native-ext4-h0-20260917-1/qualified-tools-2/build/misc/mke2fs.static'
    checker = formatter.parent.parent / 'e2fsck/e2fsck.static'
    require(base.tool_identity(checker)['sha256'] == '15e4834df6046e69642f4cec7d59412e83a802e10541d3947dc605c772bc723d', 'retained checker differs')
    run(['qemu-aarch64', *base.profile.formatter_argv(str(formatter), str(clean), UUID, blocks=BLOCKS)],
        out, 'format', env=dict(PATH='/usr/bin:/bin', LC_ALL='C', MKE2FS_CONFIG=str(config)))
    run(['qemu-aarch64', checker, '-fn', clean], out, 'clean-check')
    (out / 'data.bin').write_bytes(b'A' * 4096 + b'B' * 4096)
    (out / 'tail.bin').write_bytes(b'C' * 4096)
    copy(clean, image)
    commands = (f'journal_open -c -v 3\njournal_write -b 100000,100001 {out}/data.bin\n'
                f'journal_write -r 100001\njournal_write -c -b 100002 {out}/tail.bin\njournal_close\n')
    command_file = out / 'journal.commands'; command_file.write_text(commands)
    run(['/usr/sbin/debugfs', '-w', '-f', command_file, image], out, 'journal-producer')
    journal = int(run(['/usr/sbin/debugfs', '-R', 'bmap <8> 0', image], out, 'journal-block').stdout.strip())
    dirty = out / 'dirty.img'; copy(image, dirty)
    # Link test-only syscall wrappers against the actual ARM64 objects; preserve tool bytes.
    wrapper = out / 'io-fault.o'; wrapped = out / 'replayer-fault'
    run(['aarch64-linux-gnu-gcc', '-std=c11', '-static', '-Os', '-Wall', '-Wextra', '-Werror',
         '-c', FIXTURE_SOURCE, '-o', wrapper], out, 'fault-compile')
    link = subprocess.check_output(['make', '-n', '-C', str(tool.parent), '-W', 'journal.o', 'e2fsck.static'], text=True)
    lines = [line for line in link.splitlines() if line.startswith('aarch64-linux-gnu-gcc ')]
    require(len(lines) == 1, 'ambiguous upstream link recipe')
    argv = shlex.split(lines[0]); argv[argv.index('-o')+1] = str(wrapped)
    argv += [str(wrapper), '-Wl,--wrap=pwrite,--wrap=pread,--wrap=fsync,--wrap=close']
    result = subprocess.run(argv, cwd=tool.parent, capture_output=True, timeout=60)
    (out / 'fault-link.log').write_bytes(result.stdout + result.stderr)
    require(result.returncode == 0, 'fault link failed')
    rows = []

    def case(name, *, source=dirty, mutate=None, fault=None, success=False, changed=None):
        copy(source, image)
        if mutate: mutate(image)
        pre = out / (name + '.before.img'); copy(image, pre)
        env = dict(PATH='/usr/bin:/bin', LC_ALL='C')
        if fault: env['S22_H0_IO_FAULT'] = fault
        result = run(['qemu-aarch64', wrapped if fault else tool], out, name, env=env, expected=None)
        match = RESULT.search(result.stdout)
        require(match is not None, name + ' missing final result')
        fields = dict(zip(('stage','writes','bytes','error','io_error','complete'), map(int, match.groups())))
        require((result.returncode == 0) == success == bool(fields['complete']), name + ' false result')
        delta = compare(pre, image)
        if changed is not None: require(delta['changed_blocks'] == sorted(changed), name + ' unexpected write')
        if fault:
            evidence = re.search(rb'H0_IO_FAULT writes=(\d+) flushes=(\d+) fired=1 after_error=0\n$', result.stderr)
            require(evidence is not None, name + ' fault absent or a later write/flush occurred')
        rows.append(dict(name=name, returncode=result.returncode, **fields, **delta))
        return fields

    case('committed-revoked-uncommitted', success=True, changed=[0,journal,100000])
    require(block(image,100000) == b'A'*4096 and block(image,100001) == bytes(4096) and
            block(image,100002) == bytes(4096), 'replay/revoke/tail semantics differ')
    run(['qemu-aarch64', checker, '-fn', image], out, 'recovered-check')
    clean_recovered = out / 'recovered.img'; copy(image,clean_recovered)
    case('already-clean-no-replay', source=clean_recovered, changed=[])
    case('superblock-checksum', mutate=lambda p:modify_super(p,lambda b:b.__setitem__(0x100,b[0x100]^1),checksum=False), changed=[])
    case('external-journal', mutate=lambda p:modify_super(p,lambda b:b.__setitem__(slice(0xd0,0xe0),bytes([1])*16)), changed=[])
    case('orphan-head', mutate=lambda p:modify_super(p,lambda b:struct.pack_into('<I',b,0xe8,12)), changed=[])
    case('wrong-internal-inode', mutate=lambda p:modify_super(p,lambda b:struct.pack_into('<I',b,0xe0,9)), changed=[])

    def bad_journal(p):
        with p.open('r+b') as f: f.seek(journal*4096); f.write(bytes(4))
    case('corrupt-journal-super', mutate=bad_journal, changed=[])
    def checksum_feature_removed(p):
        with p.open('r+b') as f:
            f.seek(journal*4096+0x28); value=struct.unpack('>I',f.read(4))[0]
            f.seek(journal*4096+0x28); f.write(struct.pack('>I',value & ~0x18))
    case('journal-checksum-feature-removed',mutate=checksum_feature_removed,changed=[])
    def inode_field(p,field,value):
        run(['/usr/sbin/debugfs','-w','-R',f'sif <8> {field} {value}',p],out,'inode-'+field)
    case('journal-inode-mode',mutate=lambda p:inode_field(p,'mode',0),changed=[])
    case('journal-inode-partial-block',mutate=lambda p:inode_field(p,'size',4096*4096+1),changed=[])

    def flip_journal(p,logical,byte):
        physical=int(run(['/usr/sbin/debugfs','-R',f'bmap <8> {logical}',p],out,f'map-{logical}').stdout.strip())
        with p.open('r+b') as f:
            f.seek(physical*4096+byte);old=f.read(1);f.seek(-1,1);f.write(bytes([old[0]^1]))
    case('descriptor-checksum',mutate=lambda p:flip_journal(p,1,4095),changed=[])
    case('revoke-checksum',mutate=lambda p:flip_journal(p,5,4095),changed=[])

    def transaction(name,targets):
        path=out/(name+'.img');copy(clean,path)
        script=out/(name+'.commands')
        script.write_text(f'journal_open -c -v 3\njournal_write -b {targets} {out}/data.bin\njournal_close\n')
        run(['/usr/sbin/debugfs','-w','-f',script,path],out,name+'-producer')
        require(struct.unpack_from('<I',block(path,0),1024+0x60)[0]&4,'producer did not create a pending journal')
        return path
    payload=transaction('payload-base','100000,100001')
    case('payload-checksum-partial',source=payload,mutate=lambda p:flip_journal(p,2,0),changed=[100001])
    def out_of_range(p):
        physical=int(run(['/usr/sbin/debugfs','-R','bmap <8> 1',p],out,'outside-descriptor-map').stdout.strip())
        with p.open('r+b') as f:
            f.seek(physical*4096);raw=bytearray(f.read(4096))
            struct.pack_into('>I',raw,12,BLOCKS)
            struct.pack_into('>I',raw,4092,0)
            import uuid
            struct.pack_into('>I',raw,4092,base.profile.crc32c(uuid.UUID(UUID).bytes+raw))
            f.seek(physical*4096);f.write(raw)
    bounded=case('target-out-of-range',source=transaction('outside-target','100000'),mutate=out_of_range,changed=[])
    require(bounded['stage']==2 and bounded['io_error']>0 and bounded['writes']==0,
            'out-of-range fixture did not reach the replay I/O guard')
    case('target-is-journal',source=transaction('journal-target',str(journal)),changed=[])

    # A committed journal block can reveal an orphan head absent before replay.
    orphan = out/'orphan-journal.img'; copy(clean,orphan)
    data = bytearray(block(clean,0)); struct.pack_into('<I',data,1024+0xe8,12)
    struct.pack_into('<I',data,1024+0x60,base.profile.INCOMPAT|4)
    struct.pack_into('<I',data,1024+0x3fc,base.profile.crc32c(data[1024:1024+0x3fc]))
    (out/'orphan.bin').write_bytes(data)
    (out/'orphan.commands').write_text(f'journal_open -c -v 3\njournal_write -b 0 {out}/orphan.bin\njournal_close\n')
    run(['/usr/sbin/debugfs','-w','-f',out/'orphan.commands',orphan],out,'orphan-producer')
    row=case('replayed-orphan-no-cleanup',source=orphan,changed=[0])
    require(row['writes']==1 and struct.unpack_from('<I',block(image,0),1024+0xe8)[0]==12,
            'replayed orphan was cleaned or finalization continued')

    for fault in ('write:1','short:1','write:2','short:2','write:3','short:3',
                  'flush:1','flush:2','flush:3','flush:4','close:1','readback:2','readback:3'):
        case('fault-'+fault.replace(':','-'), fault=fault)
    require(pin(tool)==dict((k,v) for k,v in value['replayer'].items() if k in ('path','size','sha256')),
            'qualified tool changed during fault linking')
    return publish(out/'result.json',dict(schema='s22plus-strict-journal-replay-qualification-h0-v1',
        build=pin(build_receipt), fixture_only=True, rows=rows, count=len(rows),
        tools=[base.compiler_identity('/usr/bin/qemu-aarch64'),base.compiler_identity('/usr/sbin/debugfs')],
        source=pin(Path(__file__)), wrapper=pin(FIXTURE_SOURCE), device_effects=0,
        block_device_kernel_semantics_proved=False, live_authorized=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(); print(qualify(args.build,args.output))
