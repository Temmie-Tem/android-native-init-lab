"""P365 fresh checked namespace; consumed P364 sources remain unchanged."""
from pathlib import Path
import ast
import hashlib
ROOT=Path(__file__).resolve().parents[5]
P364_SOURCES={'prepare_s22plus_fyg8_p364_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p364_process_v2.py', '4f11aedcc9ed2724a5e1834dd8b63ec0fff026b2e7049e87895fd7d8aca7182e'), 's22plus_fyg8_p364_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p364_display_renderer.py', '6513d21062e252cb0a0b5af8fe14fa97488c31d90efee0387b2e7168bb01bc9f'), 's22plus_fyg8_p364_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p364_process_v2_candidate_static.py', '2b8f7c34c1ae63e0bee540fe40f5c1c077fb9e5a4caf85a802acba16b3cccffc'), 's22plus_fyg8_p364_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p364_stock_candidate_build.py', '64fbcbaad67d4da090f11ac69d1398e2a6ac9ab9626ae5cb1cd3e596086552b9'), 's22plus_fyg8_p364_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p364_artifact_identity.py', '6a3cfa2734ae77ab348290c922c3b64b961bd6cdad2fd47a1f5a4d717ad6e55d'), 's22plus_fyg8_p364_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p364_progress.py', '0a2ddb15bb9c76267f9bc80e830e6fba33463e2a6b47c8f3dbabadee8fb0054a'), 's22plus_fyg8_p364_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p364_research_shell_observer.py', 'b53e49556da1c008bea6641efa09ea5310a197c73ac80dd5a581c2a6f83de7af'), 's22plus_fyg8_p364_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p364_research_shell_runtime.py', 'e984ca3e74e45e2e5e25caf111b70ed20c39513e53e5d4ec5916f6ff93badf25'), 's22plus_fyg8_p364_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p364_return_host.py', '6a3cfa2734ae77ab348290c922c3b64b961bd6cdad2fd47a1f5a4d717ad6e55d'), 's22plus_fyg8_p364_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p364_return_spec.py', 'ac5f1cbca8841192795f7360edb71404769c4b11057b99276101cdd8181f6b85'), 's22plus_fyg8_p364_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p364_stock_process_v2_adapter.py', 'd24ff73c664b9bff0f8ecf282ffdf5ac00175aa9623de400ab34c5bd6a7a7dae')}
NAMESPACE_SHA='2934d814589528b0efb9c1a8c183101a953297918799dbc4f2ccfeab543d7e7f'
IMAGE_SHA='b1314bbdad88fe9df3f90f902a8b9f952a9857eb300ff5ad5fa80ea61c2d4faa'
_ns_path=Path(__file__).with_name('s22plus_fyg8_p364_namespace.py')
if hashlib.sha256(_ns_path.read_bytes()).hexdigest()!=NAMESPACE_SHA:
    raise ValueError('P365 sealed namespace differs')
import s22plus_fyg8_p364_namespace as _p364
PREDECESSORS=dict(_p364.PREDECESSORS)|P364_SOURCES|{
    'p364_namespace':(str(_ns_path.relative_to(ROOT)),NAMESPACE_SHA)}

def _read(entry):
    path,digest=entry
    value=(ROOT/path).read_bytes()
    if hashlib.sha256(value).hexdigest()!=digest:
        raise ValueError('P365 sealed source differs: '+path)
    return value

def _definitions(raw):
    tree=ast.parse(raw)
    tree.body=[n for n in tree.body if not(isinstance(n,ast.If) and '__name__' in ast.unparse(n.test))]
    return ast.unparse(ast.fix_missing_locations(tree)).encode()

def _p364_base(name):
    # Expand the exact sealed loader input, with its original identity substitutions.
    old=name.replace('p364','p363')
    raw=_read(_p364.P363_SOURCES[old])
    header=b'from s22plus_fyg8_p363_namespace import load\nload(globals())'
    if header in raw:
        base=_read(_p364._p363.PREDECESSORS[old.replace('p363','p353')])
        base=base.replace(b'P353',b'P363').replace(b'p353',b'p363')
        base=base.replace(b'c353f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c363f1e0a90b5e6d7c8a9b0c1d2e3f0b')
        base=base.replace(b'68f6aa66cb29cf94cd7c857545cffd54fc0a250f9bb0a98208a7a153a32e84d9',b'd575108eec0dfcffec077817d696bd4a18853c2f26f0cb111c902f118ece5dc5')
        raw=raw.replace(header,_definitions(base))
    raw=raw.replace(b'P363',b'P364').replace(b'p363',b'p364')
    raw=raw.replace(b'c363f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c364f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    return raw.replace(b'd575108eec0dfcffec077817d696bd4a18853c2f26f0cb111c902f118ece5dc5',_p364.IMAGE_SHA.encode())

def load(namespace):
    name=Path(namespace['__file__']).name.replace('p365','p364')
    raw=_read(P364_SOURCES[name])
    header=b'from s22plus_fyg8_p364_namespace import load\nload(globals())'
    if header in raw:raw=raw.replace(header,_definitions(_p364_base(name)))
    raw=raw.replace(b'P364',b'P365').replace(b'p364',b'p365')
    raw=raw.replace(b'c364f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c365f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    raw=raw.replace(_p364.IMAGE_SHA.encode(),IMAGE_SHA.encode())
    raw=_definitions(raw)
    exec(compile(raw,str(ROOT/P364_SOURCES[name][0])+'#p365','exec'),namespace)
