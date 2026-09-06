"""P352 fresh H0 namespace over the sealed P351 template; no device authority."""
from pathlib import Path
import ast
import hashlib

P351_TEMPLATE = Path(__file__).with_name('s22plus_fyg8_p351_process_v2_candidate_static.py')
P351_TEMPLATE_SHA = 'e08b6adb96b1a70a382cf76a2e0c035e833d910abe23af12f0c2f74d7ce35a1e'
_source = P351_TEMPLATE.read_bytes()
if hashlib.sha256(_source).hexdigest() != P351_TEMPLATE_SHA:
    raise ValueError("P352 predecessor template identity differs")
_source = _source.replace(b'P351', b'P352').replace(b'p351', b'p352')
_source = _source.replace(b'c351f1e0a90b5e6d7c8a9b0c1d2e3f0b', b'c352f1e0a90b5e6d7c8a9b0c1d2e3f0f')
_tree = ast.parse(_source)
_tree.body = [n for n in _tree.body if not (isinstance(n, ast.If) and '__name__' in ast.unparse(n.test))]
exec(compile(ast.fix_missing_locations(_tree), str(P351_TEMPLATE) + '#p352', 'exec'), globals())

SOURCE_FILES['p352_p351_static_template'] = P351_TEMPLATE

if __name__ == '__main__':
    raise SystemExit(main())
