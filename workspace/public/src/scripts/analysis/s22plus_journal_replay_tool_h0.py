#!/usr/bin/env python3
"""Build a separate strict JBD2 replayer; no device access or live authority."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s22plus_native_ext4_h0 as base
from s22plus_native_records_v3 import pin, private_path, publish, require

ROOT = base.ROOT
NATIVE = base.NATIVE
STRICT = NATIVE / 's22plus_journal_replay_strict_v1.inc.c'
CORE = NATIVE / 's22plus_native_ext4_core_v1.h'


def replace_once(text, old, new):
    require(text.count(old) == 1, 'upstream strict-replay patch context differs')
    return text.replace(old, new)


def patch_source(source):
    path = source / 'e2fsck/unix.c'
    text = path.read_text()
    text = replace_once(text, 'int main (int argc, char *argv[])\n{',
                        'extern int s22plus_strict_journal_main(int, char **);\n'
                        'int main (int argc, char *argv[])\n{\n'
                        '\treturn s22plus_strict_journal_main(argc, argv);')
    path.write_text(text)
    path = source / 'e2fsck/journal.c'
    text = path.read_text()
    text = replace_once(text, 'static int bh_count = 0;',
                        'static int bh_count = 0;\nstatic errcode_t jr_io_error;')
    text = replace_once(text, '\t\ttry_backup_journal:\n',
                        '\t\ttry_backup_journal:\n\t\t\tgoto errout; /* No journal-inode repair. */\n')
    text = replace_once(text, '\t\tif ((pb.last_block + 1)',
                        '\t\tif (retval) goto errout;\n\t\tif ((pb.last_block + 1)')
    text = replace_once(text, '\t} else {\n\t\text_journal = 1;',
                        '\t} else {\n\t\tretval = EINVAL; goto errout; /* No external discovery. */\n\t\text_journal = 1;')
    text += '\n#include "s22plus_journal_replay_strict_v1.inc.c"\n'
    path.write_text(text)
    shutil.copyfile(STRICT, source / 'e2fsck' / STRICT.name)
    shutil.copyfile(CORE, source / 'e2fsck' / CORE.name)


def seal(fs_uuid, *, fixture_path=None, fixture_blocks=None):
    raw = uuid.UUID(fs_uuid).bytes
    require((fixture_path is None) == (fixture_blocks is None), 'fixture seal incomplete')
    blocks = fixture_blocks if fixture_path else 50189568
    require(isinstance(blocks, int) and blocks >= 16384, 'invalid filesystem size')
    device = str(fixture_path) if fixture_path else '/dev/.s22-ext4-v1/native'
    return ('/* Generated private seal; fixture binaries have no live role. */\n'
            f'#define JR_DEVICE {json.dumps(device)}\n'
            f'#define JR_FIXTURE_REGULAR {int(bool(fixture_path))}\n'
            f'#define JR_BLOCKS {blocks}ULL\n#define JR_BYTES (JR_BLOCKS * 4096ULL)\n'
            'static const unsigned char jr_uuid[16] = {' +
            ','.join(str(b) for b in raw) + '};\n').encode()


def build(archive, directory, fs_uuid, *, fixture_path=None, fixture_blocks=None):
    archive = private_path(ROOT, archive)
    directory = private_path(ROOT, directory, exists=False)
    require(not directory.exists(), 'fresh replayer build output required')
    upstream = pin(archive, maximum=base.ARCHIVE_MAXIMUM)
    require(upstream['sha256'] == base.UPSTREAM_SHA256, 'upstream archive differs')
    directory.mkdir(mode=0o700, parents=True)
    with tarfile.open(archive) as tar:
        require(all(m.name == 'e2fsprogs-1.47.2' or m.name.startswith('e2fsprogs-1.47.2/')
                    for m in tar.getmembers()), 'source root differs')
        tar.extractall(directory, filter='data')
    source = directory / 'e2fsprogs-1.47.2'
    patch_source(source)
    header = source / 'e2fsck/s22plus_journal_replay_seal_v1.h'
    header.write_bytes(seal(fs_uuid, fixture_path=fixture_path, fixture_blocks=fixture_blocks))
    builddir = directory / 'build'; builddir.mkdir(mode=0o700)
    env = dict(PATH='/usr/bin:/bin', LC_ALL='C', **base.CONFIGURE_ENV)
    commands = [('configure', [str(source / 'configure'), *base.CONFIGURE]),
                ('libraries', ['make', '-j2', 'libs']),
                ('replayer', ['make', '-C', 'e2fsck', '-j2', 'e2fsck.static'])]
    tools = [shutil.which(name) for name in
             ('aarch64-linux-gnu-gcc', 'aarch64-linux-gnu-ar', 'aarch64-linux-gnu-ranlib',
              'aarch64-linux-gnu-as', 'aarch64-linux-gnu-ld', 'make')]
    require(all(tools), 'incomplete cross toolchain')
    for library in ('libc.a', 'libm.a', 'libpthread.a', 'libgcc.a', 'libgcc_eh.a',
                    'crt1.o', 'crti.o', 'crtn.o', 'crtbeginT.o', 'crtend.o'):
        name = subprocess.check_output([tools[0], '-print-file-name=' + library], text=True).strip()
        require(name != library and Path(name).is_file(), 'missing cross link input')
        tools.append(name)
    tools.append(subprocess.check_output([tools[0], '-print-prog-name=cc1'], text=True).strip())
    toolchain = [base.compiler_identity(path) for path in tools]
    for path in (Path(__file__), STRICT, CORE): shutil.copyfile(path, directory / path.name)
    request = publish(directory / 'request.json', dict(
        schema='s22plus-strict-journal-replay-build-request-v1', upstream=upstream,
        sources=[pin(p) for p in (Path(__file__), STRICT, CORE)], seal=pin(header),
        patched_sources=[pin(source/'e2fsck'/name) for name in ('unix.c','journal.c',STRICT.name,CORE.name)],
        toolchain=toolchain,
        fixture_only=bool(fixture_path), commands=commands, environment=env,
        device_effects=0, live_authorized=False))
    def verify_copies():
        for original in (Path(__file__), STRICT, CORE):
            require(original.read_bytes() == (directory / original.name).read_bytes(),
                    'replayer source changed during snapshot/build')
        for original in (STRICT, CORE):
            require((source/'e2fsck'/original.name).read_bytes() == (directory/original.name).read_bytes(),
                    'compiled include differs from retained source')
    verify_copies()
    for label, argv in commands:
        base.run(argv, cwd=builddir, env=env, stdout=directory / (label + '.log'), timeout=300)
    require(toolchain == [base.compiler_identity(path) for path in tools], 'toolchain changed')
    require(upstream == pin(archive, maximum=base.ARCHIVE_MAXIMUM), 'upstream changed')
    verify_copies()
    result = dict(schema='s22plus-strict-journal-replay-tool-h0-v1', request=request,
                  replayer=base.tool_identity(builddir / 'e2fsck/e2fsck.static'),
                  fixture_only=bool(fixture_path), device_effects=0, live_authorized=False,
                  logs=[pin(directory / (label + '.log')) for label, _ in commands])
    return publish(directory / 'result.json', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--uuid', required=True)
    parser.add_argument('--fixture-path', type=Path)
    parser.add_argument('--fixture-blocks', type=int)
    args = parser.parse_args()
    print(json.dumps(build(args.archive, args.output, args.uuid,
                           fixture_path=args.fixture_path, fixture_blocks=args.fixture_blocks)))
