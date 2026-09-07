"""Exercise the existing behavioral fixture with the exact P360 namespace."""
from pathlib import Path

_source = Path(__file__).with_name('test_s22plus_fyg8_p357_carrier.py').read_text()
_source = _source.replace('P357', 'P360').replace('p357', 'p360')
exec(compile(_source, __file__ + '#p357-fixture', 'exec'), globals())
