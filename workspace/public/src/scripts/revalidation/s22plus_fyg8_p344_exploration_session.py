"""P344 private identity projection of the repaired P343 session; no new authority."""
from pathlib import Path
import hashlib
import os
import stat

_PARENT = Path(__file__).with_name('s22plus_fyg8_p343_exploration_session.py')
_PARENT_SHA256 = 'e013f06823e3176b54c6249514c6ea8db2cd2e59e72928eeee289edfa01c9195'
_before = _PARENT.lstat()
with _PARENT.open('rb') as _stream:
    _payload = _stream.read(65537)
    _inside = os.fstat(_stream.fileno())
_after = _PARENT.lstat()
def _node(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
if (_PARENT.resolve() != _PARENT.absolute() or not stat.S_ISREG(_before.st_mode)
        or _before.st_nlink != 1 or _node(_before) != _node(_inside)
        or _node(_before) != _node(_after)
        or hashlib.sha256(_payload).hexdigest() != _PARENT_SHA256):
    raise ValueError('P344 parent session source differs')
_projected = _payload.decode().replace('p343', 'p344').replace('P343', 'P344').replace('P3.43', 'P3.44')
exec(compile(_projected, str(_PARENT), 'exec', dont_inherit=True), globals())

