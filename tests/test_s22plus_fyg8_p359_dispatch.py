"""Exercise the existing behavioral fixture with the exact P359 namespace."""
from pathlib import Path

_source = Path(__file__).with_name('test_s22plus_fyg8_p357_dispatch.py').read_text()
_source = _source.replace('P357', 'P359').replace('p357', 'p359')
exec(compile(_source, __file__ + '#p357-fixture', 'exec'), globals())
