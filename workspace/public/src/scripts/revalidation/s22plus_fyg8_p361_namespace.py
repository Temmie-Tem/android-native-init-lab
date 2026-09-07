"""Fixed P361 namespace over sealed P353 H0 machinery; no device authority."""
from pathlib import Path
import ast
import hashlib

ROOT = Path(__file__).resolve().parents[5]
PREDECESSORS = {
    'prepare_s22plus_fyg8_p353_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p353_process_v2.py', '09d1dea3daa24f39988a5b7aa147fd1650a158df0ee77af67dfa071e30af590c'),
    's22plus_fyg8_p353_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p353_artifact_identity.py', '2746cd0d42a880e3567528043391ef6b2cc9d9a4648e604276fc395bec4d7686'),
    's22plus_fyg8_p353_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p353_research_shell_runtime.py', '5a28af5f4a019b357eee7456b204308f553c441b2527bca9127019af4143adbe'),
    's22plus_fyg8_p353_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p353_research_shell_observer.py', '58558820655175365427c4cf58e465139f2d323e0f097dbb6b12dc945626a274'),
    's22plus_fyg8_p353_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p353_stock_process_v2_adapter.py', '057b1bfd7493488b5b0028651daa15332c7640192fbaeab85397c5cc60065a5c'),
    's22plus_fyg8_p353_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p353_stock_candidate_build.py', '9864299bfd61afe6ba33556ce18f844976695f9c746775cf83d3314ffde4c8db'),
    's22plus_fyg8_p353_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p353_process_v2_candidate_static.py', 'b21d6ed0e54654214200b8222aa702cc99e0ce8ce0e77d2541798aba05fb9c94'),
}


def load(namespace):
    name = Path(namespace['__file__']).name.replace('p361', 'p353')
    relative, expected = PREDECESSORS[name]
    path = ROOT / relative
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('P361 sealed predecessor changed: ' + name)
    raw = raw.replace(b'P353', b'P361').replace(b'p353', b'p361')
    raw = raw.replace(b'c353f1e0a90b5e6d7c8a9b0c1d2e3f0b', b'c361f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    raw = raw.replace(b'68f6aa66cb29cf94cd7c857545cffd54fc0a250f9bb0a98208a7a153a32e84d9',
                      b'fd7c92f95ba00650378721df651d1dea7e289a9c3a46748c6704d97f8d5d6881')
    tree = ast.parse(raw)
    tree.body = [n for n in tree.body if not (isinstance(n, ast.If) and '__name__' in ast.unparse(n.test))]
    entry = namespace['__name__']
    try:
        namespace['__name__'] = entry if entry != '__main__' else 'p361_h0_template'
        exec(compile(ast.fix_missing_locations(tree), str(path) + '#p361', 'exec'), namespace)
    finally:
        namespace['__name__'] = entry
