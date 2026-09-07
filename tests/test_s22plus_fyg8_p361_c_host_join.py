"""Exercise the existing behavioral fixture with the exact P361 namespace."""
from pathlib import Path

_source = Path(__file__).with_name('test_s22plus_fyg8_p357_c_host_join.py').read_text()
_source = _source.replace('P357', 'P361').replace('p357', 'p361')
exec(compile(_source, __file__ + '#p357-fixture', 'exec'), globals())
