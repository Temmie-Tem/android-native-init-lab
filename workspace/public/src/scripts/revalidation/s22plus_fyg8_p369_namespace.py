"""P369 fixed userspace-wait successor; consumed P368 sources remain sealed."""
from pathlib import Path
import ast,hashlib
ROOT=Path(__file__).resolve().parents[5]
P368_SOURCES={'prepare_s22plus_fyg8_p368_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p368_process_v2.py', 'bb564f4d26926c867cf277b6d244aab32e3aec32cff7cfae41861c2dbef0b87c'), 's22plus_fyg8_p368_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p368_process_v2_candidate_static.py', 'bb564f4d26926c867cf277b6d244aab32e3aec32cff7cfae41861c2dbef0b87c'), 's22plus_fyg8_p368_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p368_display_renderer.py', '87fb10494d23ff6c70111c00465a5ca9e44320c3a7dea6f89d290d63a802e560'), 's22plus_fyg8_p368_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p368_stock_candidate_build.py', 'f81012949746a92961634364e5a220eb5046ca983957f079c09ee88b4d88b984'), 's22plus_fyg8_p368_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p368_research_shell_runtime.py', '4f787267e86acdd078b6fe02cdcf8cd57b5b459c629cd9cc277861578a3adfa4'), 's22plus_fyg8_p368_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p368_return_host.py', '7393edcb1ab5c49ba7fc89231585d39f914c313dd2adb84d2e6e2c09f8a7c1e0'), 's22plus_fyg8_p368_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p368_progress.py', '7393edcb1ab5c49ba7fc89231585d39f914c313dd2adb84d2e6e2c09f8a7c1e0'), 's22plus_fyg8_p368_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p368_artifact_identity.py', '7393edcb1ab5c49ba7fc89231585d39f914c313dd2adb84d2e6e2c09f8a7c1e0'), 's22plus_fyg8_p368_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p368_research_shell_observer.py', '2b3a51bf3132ccc65400538313dad331278aeb5b2723482d5c38e0597933a8ae'), 's22plus_fyg8_p368_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p368_return_spec.py', '7393edcb1ab5c49ba7fc89231585d39f914c313dd2adb84d2e6e2c09f8a7c1e0'), 's22plus_fyg8_p368_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p368_stock_process_v2_adapter.py', '7393edcb1ab5c49ba7fc89231585d39f914c313dd2adb84d2e6e2c09f8a7c1e0')}
NAMESPACE_SHA='78bec337bd511613aa6f2fdb8de21fa1c36b0df521be3e6f5e2f3a6c3b73d22a'
IMAGE_SHA='8005433404304dd66fbd72af2d8a4dad0d025f3d18d0ce5021f6e48ab9642a8c'
_ns_path=Path(__file__).with_name('s22plus_fyg8_p368_namespace.py')
if hashlib.sha256(_ns_path.read_bytes()).hexdigest()!=NAMESPACE_SHA:raise ValueError('P369 sealed namespace differs')
import s22plus_fyg8_p368_namespace as _p368
PREDECESSORS=dict(_p368.PREDECESSORS)|P368_SOURCES|{'p368_namespace':(str(_ns_path.relative_to(ROOT)),NAMESPACE_SHA)}
_read=_p368._read
_definitions=_p368._definitions

def _p368_base(name):
    old=name.replace('p368','p367')
    raw=_read(_p368.P367_SOURCES[old])
    header=b'from s22plus_fyg8_p367_namespace import load\nload(globals())'
    if header in raw:raw=raw.replace(header,_definitions(_p368._p367_base(old)))
    raw=raw.replace(b'P367',b'P368').replace(b'p367',b'p368')
    raw=raw.replace(b'c367f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c368f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    return raw.replace(_p368._p367.IMAGE_SHA.encode(),_p368.IMAGE_SHA.encode())

def load(namespace):
    name=Path(namespace['__file__']).name.replace('p369','p368')
    raw=_read(P368_SOURCES[name])
    header=b'from s22plus_fyg8_p368_namespace import load\nload(globals())'
    if header in raw:raw=raw.replace(header,_definitions(_p368_base(name)))
    raw=raw.replace(b'P368',b'P369').replace(b'p368',b'p369')
    raw=raw.replace(b'c368f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c369f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    raw=raw.replace(_p368.IMAGE_SHA.encode(),IMAGE_SHA.encode())
    if name.endswith('_research_shell_observer.py'):
        # READY/ACK now describe control availability, not display completion.
        raw=raw.replace(b'ready[3] == 0 and ready[1] != 10',b'ready[3] != 0 or ready[1] != 0')
        raw=raw.replace(b'not child_exited and swaps != 10',b'child_exited or swaps != 0')
    exec(compile(_definitions(raw),str(ROOT/P368_SOURCES[name][0])+'#p369','exec'),namespace)
