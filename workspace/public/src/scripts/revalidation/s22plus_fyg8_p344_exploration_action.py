"""P344 private identity projection of the repaired P343 action; no new authority."""
from pathlib import Path
import hashlib
import os
import stat

_PARENT = Path(__file__).with_name('s22plus_fyg8_p343_exploration_action.py')
_PARENT_SHA256 = '3ef85fe538378523660e7c675c89fdf28134fa6163b57a4e994e26d6e34e5d36'
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
    raise ValueError('P344 parent action source differs')
_projected = _payload.decode().replace('p343', 'p344').replace('P343', 'P344').replace('P3.43', 'P3.44')
exec(compile(_projected, str(_PARENT), 'exec', dont_inherit=True), globals())

