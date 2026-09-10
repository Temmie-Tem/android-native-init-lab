"""P382 uses the unchanged P381 live receipt corpus with fresh identity."""
from pathlib import Path
import ast
_source=Path(__file__).with_name('test_s22plus_fyg8_p381_live_receipt.py').read_text()
_source=_source.replace('p381','p382').replace('P381','P382').replace('v0.1.2-rc.4','v0.1.2-rc.5').replace('c381','c382').replace('0x81','0x82')
_tree=ast.parse(_source)
_tree.body=[n for n in _tree.body if not (isinstance(n,ast.If) and '__name__' in ast.unparse(n.test))]
exec(compile(ast.fix_missing_locations(_tree),__file__+'#inherited-corpus','exec'),globals())
