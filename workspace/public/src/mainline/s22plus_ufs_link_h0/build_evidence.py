"""Actual observer compiler inputs for bounded, key-only candidate reuse."""
import hashlib
from pathlib import Path
import shlex
import shutil
import subprocess


def pin(path):
    path = Path(path).resolve(strict=True)
    data = path.read_bytes()
    return dict(path=str(path), size=len(data), sha256=hashlib.sha256(data).hexdigest())


def compile_observer(command, output):
    """Compile once and retain full dependencies, linked libraries and tools.

    Only observer.c and seal.h are generated per candidate. All other compiler
    inputs, including system headers and static libraries, are fixed inputs.
    No CPATH, LIBRARY_PATH, GCC_EXEC_PREFIX or caller-injected specs are used.
    """
    output = Path(output)
    dep = output/'observer.d'
    log = output/'compile.log'
    env = dict(PATH='/usr/bin:/bin', LC_ALL='C', SOURCE_DATE_EPOCH='0')
    compiler = Path(shutil.which(command[0], path=env['PATH'])).resolve(strict=True)
    tools = {compiler}
    for name in ('cc1', 'as', 'ld', 'collect2'):
        value = subprocess.check_output([compiler, '-print-prog-name='+name],
                                        env=env, text=True).strip()
        tools.add(Path(shutil.which(value, path=env['PATH']) or value).resolve(strict=True))
    # Include the actual host libraries needed to execute the toolchain too.
    for tool in tuple(tools):
        result = subprocess.run(['/usr/bin/ldd', tool], env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for word in result.stdout.split():
            if word.startswith('/') and Path(word).is_file():
                tools.add(Path(word).resolve(strict=True))
    before = [pin(p) for p in sorted(tools)]
    actual = [str(compiler), *command[1:], '-MD', '-MF', str(dep), '-Wl,-t']
    with log.open('xb') as stream:
        subprocess.run(actual, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
    if before != [pin(p) for p in sorted(tools)]:
        raise ValueError('compiler changed during build')
    deps = shlex.split(dep.read_text().replace('\\\n', ' ').split(':', 1)[1])
    # GNU ld -t lists the actual crt objects, archives and linker scripts.
    linked = [Path(line.strip()) for line in log.read_text().splitlines()
              if line.strip().startswith('/') and Path(line.strip()).is_file()]
    if not linked or not any(p.name == 'libc.a' for p in linked):
        raise ValueError('static linker input trace is incomplete')
    generated = {Path(command[command.index('-o')-1]).resolve(),
                 (Path(command[command.index('-o')-1]).parent/'seal.h').resolve()}
    fixed = sorted({Path(p).resolve(strict=True) for p in deps} | {p.resolve(strict=True) for p in linked} | tools)
    return dict(schema='s22plus-observer-build-inputs-v1',
                fixed=[pin(p) for p in fixed if p not in generated],
                generated=[pin(p) for p in sorted(generated)],
                command=actual, environment=env, dependency=pin(dep), log=pin(log))
