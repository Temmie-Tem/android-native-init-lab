"""P344 regressions reuse the real P343 cases with a distinct candidate identity."""
from pathlib import Path

_source = Path(__file__).with_name('test_s22plus_fyg8_p343_live.py').read_text()
exec(compile(_source.replace('p343','p344').replace('P343','P344').replace('P3.43','P3.44'),
             str(Path(__file__).with_name('test_s22plus_fyg8_p343_live.py')),
             'exec', dont_inherit=True), globals())

