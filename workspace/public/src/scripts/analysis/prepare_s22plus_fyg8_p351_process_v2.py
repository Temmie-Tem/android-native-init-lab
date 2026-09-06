"""P351 H0-only fresh promotion binding over the unchanged P350 template."""
from pathlib import Path
import ast
import hashlib
PARENT_TEMPLATE = Path(__file__).with_name('prepare_s22plus_fyg8_p350_process_v2.py')
PARENT_TEMPLATE_SHA = '176673e7f9eb027dbda13b9ef8a5b6a26cbc2fb75667a6be80c4c1d559d3589e'
_parent_source = PARENT_TEMPLATE.read_bytes()
if hashlib.sha256(_parent_source).hexdigest() != PARENT_TEMPLATE_SHA:
    raise ValueError('P351 promotion template identity differs')
_parent_source = _parent_source.replace(b'P350', b'P351').replace(b'p350', b'p351')
_tree = ast.parse(_parent_source)
_tree.body = [n for n in _tree.body if not (isinstance(n, ast.If) and '__name__' in ast.unparse(n.test))]
exec(compile(ast.fix_missing_locations(_tree), str(PARENT_TEMPLATE) + '#p351', 'exec'), globals())

if __name__ == '__main__':
    raise SystemExit(main())
