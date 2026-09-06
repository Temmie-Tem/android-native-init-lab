"""P351 fresh binding over the unchanged P350 template; no live authority."""
from pathlib import Path
import hashlib

PARENT_TEMPLATE = Path(__file__).with_name('s22plus_fyg8_p350_stock_process_v2_adapter.py')
PARENT_TEMPLATE_SHA = '0efbf7bd2fd0427d88cf70254b1e1d10bd27fc11da5b30add792fdf4c78f6392'
_parent_source = PARENT_TEMPLATE.read_bytes()
if hashlib.sha256(_parent_source).hexdigest() != PARENT_TEMPLATE_SHA:
    raise ValueError('P351 template identity differs')
_parent_source = _parent_source.replace(b'P350', b'P351').replace(b'p350', b'p351')
_parent_source = _parent_source.replace(b'c350f1e0a90b5e6d7c8a9b0c1d2e3f0a', b'c351f1e0a90b5e6d7c8a9b0c1d2e3f0b')
exec(compile(_parent_source, str(PARENT_TEMPLATE) + '#p351', 'exec'), globals())
