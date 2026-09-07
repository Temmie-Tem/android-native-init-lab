"""P364 fixed successor over sealed P363 execution sources; no authority."""
from pathlib import Path
import ast
import hashlib
ROOT = Path(__file__).resolve().parents[5]
P363_SOURCES = {'s22plus_fyg8_p363_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p363_return_host.py', 'e91f2321ce49a825e5ac04bef88044199bec5a3bb0616a47ce29145cf033c732'), 's22plus_fyg8_p363_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p363_artifact_identity.py', '9f000606be2fee2092e91062a3f921f70e797e51f0f11c9ab7495d56b773c113'), 's22plus_fyg8_p363_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p363_return_spec.py', 'a6627f1675969316bced75ceae27bbcfd37f2a2530580d3e12be602c5b1e3168'), 's22plus_fyg8_p363_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p363_research_shell_observer.py', '0e430a52a2b13fbe97c61122e0dfff517e849361c050d9dc9d00e87dfc9515f2'), 's22plus_fyg8_p363_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p363_stock_process_v2_adapter.py', '3068a55f7760f8fec7178d86671bf374bbaebadd365abc73e96b7bddb142a6a8'), 's22plus_fyg8_p363_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p363_research_shell_runtime.py', '9263402f235785aa05f7e6149afdb1dfe52317dc31dee844f970a0087c459091'), 's22plus_fyg8_p363_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p363_stock_candidate_build.py', '3466a33e12ca4edc5342af401734f9c2a185ce44e8cee12c41a7ac7df45fc55d'), 's22plus_fyg8_p363_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p363_display_renderer.py', '66dad590e875f896dd7bf7d8c76175c4853758002afc0059b255b38c013eecdb'), 's22plus_fyg8_p363_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p363_process_v2_candidate_static.py', 'debf16a117371db07b1d2c454c75a138a6218eb84b72dbaf7ef5a007d4dee822'), 'prepare_s22plus_fyg8_p363_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p363_process_v2.py', 'c59ee26d3749c0d1404211b3c4fd5e374e987b6a68213e6e5a29404397b7f6f4')}
NAMESPACE_SHA = 'b4fe002fc456aa55c6061530c5c8d8088ccb337138f7461593a93da473b7d02e'
IMAGE_SHA = 'b016cfd9d7999de4c3eab4aec16c9b2b7b3819d361726695944737e3ec678b67'
_ns_path = Path(__file__).with_name('s22plus_fyg8_p363_namespace.py')
if hashlib.sha256(_ns_path.read_bytes()).hexdigest() != NAMESPACE_SHA:
    raise ValueError('P364 sealed namespace differs')
import s22plus_fyg8_p363_namespace as _p363
PREDECESSORS = dict(_p363.PREDECESSORS) | P363_SOURCES | {
    'p363_namespace': (str(_ns_path.relative_to(ROOT)), NAMESPACE_SHA)}


def _read(entry):
    relative, expected = entry
    raw = (ROOT / relative).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('P364 sealed predecessor differs: ' + relative)
    return raw


def load(namespace):
    name = Path(namespace['__file__']).name.replace('p364', 'p363')
    raw = _read(P363_SOURCES[name])
    header = b'from s22plus_fyg8_p363_namespace import load\nload(globals())'
    if header in raw:
        old = name.replace('p363', 'p353')
        base = _read(_p363.PREDECESSORS[old])
        base = base.replace(b'P353', b'P363').replace(b'p353', b'p363')
        base = base.replace(b'c353f1e0a90b5e6d7c8a9b0c1d2e3f0b', b'c363f1e0a90b5e6d7c8a9b0c1d2e3f0b')
        base = base.replace(b'68f6aa66cb29cf94cd7c857545cffd54fc0a250f9bb0a98208a7a153a32e84d9',
            b'd575108eec0dfcffec077817d696bd4a18853c2f26f0cb111c902f118ece5dc5')
        base_tree = ast.parse(base)
        base_tree.body = [n for n in base_tree.body if not (isinstance(n,ast.If) and '__name__' in ast.unparse(n.test))]
        raw = raw.replace(header,ast.unparse(base_tree).encode())
    raw = raw.replace(b'P363',b'P364').replace(b'p363',b'p364')
    raw = raw.replace(b'c363f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c364f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    raw = raw.replace(b'd575108eec0dfcffec077817d696bd4a18853c2f26f0cb111c902f118ece5dc5',IMAGE_SHA.encode())
    tree = ast.parse(raw)
    tree.body = [n for n in tree.body if not (isinstance(n,ast.If) and '__name__' in ast.unparse(n.test))]
    exec(compile(ast.fix_missing_locations(tree),str(ROOT/P363_SOURCES[name][0])+'#p364','exec'),namespace)
