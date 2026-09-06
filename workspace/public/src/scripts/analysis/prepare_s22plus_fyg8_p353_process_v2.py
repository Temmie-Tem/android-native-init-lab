"""P353 fresh H0 namespace over the sealed P351 template; no device authority."""
from pathlib import Path
import ast
import hashlib

P351_TEMPLATE = Path(__file__).with_name('prepare_s22plus_fyg8_p351_process_v2.py')
P351_TEMPLATE_SHA = '5f8305143ce9eca6a315a70fa93512c5e834d97e1b5fd8ee377c89ee21271d70'
_source = P351_TEMPLATE.read_bytes()
if hashlib.sha256(_source).hexdigest() != P351_TEMPLATE_SHA:
    raise ValueError("P353 predecessor template identity differs")
_source = _source.replace(b'P351', b'P353').replace(b'p351', b'p353')
_source = _source.replace(b'c351f1e0a90b5e6d7c8a9b0c1d2e3f0b', b'c353f1e0a90b5e6d7c8a9b0c1d2e3f0b')
_tree = ast.parse(_source)
_tree.body = [n for n in _tree.body if not (isinstance(n, ast.If) and '__name__' in ast.unparse(n.test))]
_entry_name = __name__
try:
    # Nested sealed templates also contain an entry guard. Load definitions
    # before applying the P353 manifest settings; invoke main exactly once.
    __name__ = 'p353_preparation_template'
    exec(compile(ast.fix_missing_locations(_tree), str(P351_TEMPLATE) + '#p353', 'exec'), globals())
finally:
    __name__ = _entry_name

_p353_manifest = _manifest
DEFAULT_PROMOTION = ROOT / 'workspace/private/outputs/s22plus_fyg8_p353/process-v2-promotion-20260907-01'


def _manifest(static, pins):
    value = _p353_manifest(static, pins)
    value['observation']['timeout_sec'] = 60
    return value


if __name__ == '__main__':
    raise SystemExit(main())
