"""P352 uses the unchanged fixed-wire qualification with a fresh identity."""
from pathlib import Path
import ast

_source = Path(__file__).with_name('test_s22plus_fyg8_p351_live.py').read_text().replace('P351','P352').replace('p351','p352')
_tree = ast.parse(_source)
_tree.body = [n for n in _tree.body if not (isinstance(n, ast.If) and '__name__' in ast.unparse(n.test))]
exec(compile(ast.fix_missing_locations(_tree), __file__ + '#p352', 'exec'), globals())
