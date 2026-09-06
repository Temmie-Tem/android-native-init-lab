"""P353 fresh H0 namespace over the sealed P351 template; no device authority."""
from pathlib import Path
import ast
import hashlib

P351_TEMPLATE = Path(__file__).with_name('s22plus_fyg8_p351_process_v2_candidate_static.py')
P351_TEMPLATE_SHA = 'e08b6adb96b1a70a382cf76a2e0c035e833d910abe23af12f0c2f74d7ce35a1e'
_source = P351_TEMPLATE.read_bytes()
if hashlib.sha256(_source).hexdigest() != P351_TEMPLATE_SHA:
    raise ValueError("P353 predecessor template identity differs")
_source = _source.replace(b'P351', b'P353').replace(b'p351', b'p353')
_source = _source.replace(b'c351f1e0a90b5e6d7c8a9b0c1d2e3f0b', b'c353f1e0a90b5e6d7c8a9b0c1d2e3f0b')
_tree = ast.parse(_source)
_tree.body = [n for n in _tree.body if not (isinstance(n, ast.If) and '__name__' in ast.unparse(n.test))]
exec(compile(ast.fix_missing_locations(_tree), str(P351_TEMPLATE) + '#p353', 'exec'), globals())

SOURCE_FILES['p353_p351_static_template'] = P351_TEMPLATE
SOURCE_FILES['p353_closure_snapshot'] = REVALIDATION / 's22plus_fyg8_p318_topology_receipt.py'
SOURCE_FILES['p353_closure_snapshot_shape'] = REVALIDATION / 's22plus_fyg8_p318_cdc_acm_endpoint_transition.py'
DEFAULT_OUTPUT = ROOT / 'workspace/private/outputs/s22plus_fyg8_p353/process-v2-candidate-static-20260907-01.json'

if __name__ == '__main__':
    raise SystemExit(main())
