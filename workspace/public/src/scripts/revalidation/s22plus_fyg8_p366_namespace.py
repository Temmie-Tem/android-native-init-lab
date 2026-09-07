"""P366 checked successor; consumed P365 sources remain sealed."""
from pathlib import Path
import ast
import hashlib
ROOT=Path(__file__).resolve().parents[5]
P365_SOURCES={'prepare_s22plus_fyg8_p365_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p365_process_v2.py', 'a5cdef7d08afe200a43acc7fabb245399b4963cb716a02a51db070e451cbd016'), 's22plus_fyg8_p365_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p365_display_renderer.py', '4a4a7729f9e07ee1880f599a89ff498e37fb7c3f14fc5ef56587ac659e637428'), 's22plus_fyg8_p365_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p365_process_v2_candidate_static.py', '59be52698b2bf24363483d20d485b5802f22d0b4e873306f2ec3cb13c16b76c3'), 's22plus_fyg8_p365_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p365_stock_candidate_build.py', 'a86c11b139403f8c2159c3f324682a161c222c2187f80271c573dcfd3652e628'), 's22plus_fyg8_p365_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p365_artifact_identity.py', '0d6c30f4d47463306d0aa6c24f47c85306cab5b1a842faf563f11d3acbe5f9eb'), 's22plus_fyg8_p365_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p365_progress.py', '0d6c30f4d47463306d0aa6c24f47c85306cab5b1a842faf563f11d3acbe5f9eb'), 's22plus_fyg8_p365_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p365_research_shell_observer.py', '0d6c30f4d47463306d0aa6c24f47c85306cab5b1a842faf563f11d3acbe5f9eb'), 's22plus_fyg8_p365_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p365_research_shell_runtime.py', '75547ec90ee0abd38b3febffdf5c4a40e456da845d5840afd065249662ca983a'), 's22plus_fyg8_p365_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p365_return_host.py', '0d6c30f4d47463306d0aa6c24f47c85306cab5b1a842faf563f11d3acbe5f9eb'), 's22plus_fyg8_p365_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p365_return_spec.py', '0d6c30f4d47463306d0aa6c24f47c85306cab5b1a842faf563f11d3acbe5f9eb'), 's22plus_fyg8_p365_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p365_stock_process_v2_adapter.py', '2f6be4855f29b50df3bd0885d4d78d740ffccf535612abecd15b0b69f964f49e')}
NAMESPACE_SHA='2f82a5c355bf57cb14fc4532246c3081073df4a761f6acb5590835ef8d857024'
IMAGE_SHA='1272863798d595ae9653a500429c64d929165b4f53610e3e3ef1af5154de45f5'
_ns_path=Path(__file__).with_name('s22plus_fyg8_p365_namespace.py')
if hashlib.sha256(_ns_path.read_bytes()).hexdigest()!=NAMESPACE_SHA:
    raise ValueError('P366 sealed namespace differs')
import s22plus_fyg8_p365_namespace as _p365
PREDECESSORS=dict(_p365.PREDECESSORS)|P365_SOURCES|{
    'p365_namespace':(str(_ns_path.relative_to(ROOT)),NAMESPACE_SHA)}

def _read(entry):
    path,digest=entry
    value=(ROOT/path).read_bytes()
    if hashlib.sha256(value).hexdigest()!=digest:
        raise ValueError('P366 sealed source differs: '+path)
    return value

def _definitions(raw):
    tree=ast.parse(raw)
    tree.body=[n for n in tree.body if not(isinstance(n,ast.If) and '__name__' in ast.unparse(n.test))]
    return ast.unparse(ast.fix_missing_locations(tree)).encode()

def _p365_base(name):
    old=name.replace('p365','p364')
    raw=_read(_p365.P364_SOURCES[old])
    header=b'from s22plus_fyg8_p364_namespace import load\nload(globals())'
    if header in raw:raw=raw.replace(header,_definitions(_p365._p364_base(old)))
    raw=raw.replace(b'P364',b'P365').replace(b'p364',b'p365')
    raw=raw.replace(b'c364f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c365f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    return raw.replace(_p365._p364.IMAGE_SHA.encode(),_p365.IMAGE_SHA.encode())

def load(namespace):
    name=Path(namespace['__file__']).name.replace('p366','p365')
    raw=_read(P365_SOURCES[name])
    header=b'from s22plus_fyg8_p365_namespace import load\nload(globals())'
    if header in raw:raw=raw.replace(header,_definitions(_p365_base(name)))
    raw=raw.replace(b'P365',b'P366').replace(b'p365',b'p366')
    raw=raw.replace(b'c365f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c366f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    raw=raw.replace(_p365.IMAGE_SHA.encode(),IMAGE_SHA.encode())
    exec(compile(_definitions(raw),str(ROOT/P365_SOURCES[name][0])+'#p366','exec'),namespace)
