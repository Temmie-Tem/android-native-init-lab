"""P367 identity-only successor; consumed P366 namespace sources stay sealed."""
from pathlib import Path
import ast
import hashlib
ROOT=Path(__file__).resolve().parents[5]
P366_SOURCES={'prepare_s22plus_fyg8_p366_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p366_process_v2.py', 'cbcbc4eb17a89436a0a703ce0c9db4100253026543646eb44a37b313e56295e6'), 's22plus_fyg8_p366_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p366_display_renderer.py', 'cbcbc4eb17a89436a0a703ce0c9db4100253026543646eb44a37b313e56295e6'), 's22plus_fyg8_p366_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p366_process_v2_candidate_static.py', '630c97d81794fabd192a9e6f4f36e159dd02a1ba07f4e1afd0c60302f2ef45a3'), 's22plus_fyg8_p366_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p366_stock_candidate_build.py', '45169fe04f82142f0e50cd41966b6ce8f80a9b9559d5f1983fbad5a1a4eeeeba'), 's22plus_fyg8_p366_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p366_artifact_identity.py', '54ba594d97232425428b98e15f4dbaa2e4f1322242e6590a6228c6a823c28d06'), 's22plus_fyg8_p366_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p366_progress.py', '54ba594d97232425428b98e15f4dbaa2e4f1322242e6590a6228c6a823c28d06'), 's22plus_fyg8_p366_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p366_research_shell_observer.py', '54ba594d97232425428b98e15f4dbaa2e4f1322242e6590a6228c6a823c28d06'), 's22plus_fyg8_p366_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p366_research_shell_runtime.py', '54ba594d97232425428b98e15f4dbaa2e4f1322242e6590a6228c6a823c28d06'), 's22plus_fyg8_p366_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p366_return_host.py', 'aa66837c83d175a19063312cff6262ae9851b854a59c882ac6ba0113ff72ab54'), 's22plus_fyg8_p366_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p366_return_spec.py', '54ba594d97232425428b98e15f4dbaa2e4f1322242e6590a6228c6a823c28d06'), 's22plus_fyg8_p366_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p366_stock_process_v2_adapter.py', '3172ba05206315c412f093d1cc1d1b20c5eb44cf03b16f77f5733fc98698ed16')}
NAMESPACE_SHA='ff62d1d4fe5dd0027951563c4d2a91adfedc8f1ef893e67a0d46e3671372703f'
IMAGE_SHA='a5695be0105b87132dead0c8207300d7cc2d50011b29246511ffaf68c6bd4657'
_ns_path=Path(__file__).with_name('s22plus_fyg8_p366_namespace.py')
if hashlib.sha256(_ns_path.read_bytes()).hexdigest()!=NAMESPACE_SHA:
    raise ValueError('P367 sealed namespace differs')
import s22plus_fyg8_p366_namespace as _p366
PREDECESSORS=dict(_p366.PREDECESSORS)|P366_SOURCES|{
    'p366_namespace':(str(_ns_path.relative_to(ROOT)),NAMESPACE_SHA)}

def _read(entry):
    path,digest=entry
    value=(ROOT/path).read_bytes()
    if hashlib.sha256(value).hexdigest()!=digest:
        raise ValueError('P367 sealed source differs: '+path)
    return value

def _definitions(raw):
    tree=ast.parse(raw)
    tree.body=[n for n in tree.body if not(isinstance(n,ast.If) and '__name__' in ast.unparse(n.test))]
    return ast.unparse(ast.fix_missing_locations(tree)).encode()

def _p366_base(name):
    old=name.replace('p366','p365')
    raw=_read(_p366.P365_SOURCES[old])
    header=b'from s22plus_fyg8_p365_namespace import load\nload(globals())'
    if header in raw:raw=raw.replace(header,_definitions(_p366._p365_base(old)))
    raw=raw.replace(b'P365',b'P366').replace(b'p365',b'p366')
    raw=raw.replace(b'c365f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c366f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    return raw.replace(_p366._p365.IMAGE_SHA.encode(),_p366.IMAGE_SHA.encode())

def load(namespace):
    name=Path(namespace['__file__']).name.replace('p367','p366')
    raw=_read(P366_SOURCES[name])
    header=b'from s22plus_fyg8_p366_namespace import load\nload(globals())'
    if header in raw:raw=raw.replace(header,_definitions(_p366_base(name)))
    raw=raw.replace(b'P366',b'P367').replace(b'p366',b'p367')
    raw=raw.replace(b'c366f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c367f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    raw=raw.replace(_p366.IMAGE_SHA.encode(),IMAGE_SHA.encode())
    exec(compile(_definitions(raw),str(ROOT/P366_SOURCES[name][0])+'#p367','exec'),namespace)
