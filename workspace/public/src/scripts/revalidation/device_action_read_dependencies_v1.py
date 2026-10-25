"""Context-local identities of bytes already verified by stable read primitives.

Inactive by default. Collection neither reads devices nor replaces a reader's
hash, path or descriptor checks. A ticket belongs to one process/owner only.
"""
from contextvars import ContextVar
from pathlib import Path
import stat

_active = ContextVar('verified_read_dependencies', default=())


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_uid, info.st_gid, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def record_read(path, verified_stat):
    for collector in _active.get():
        collector.add(path, verified_stat)


class ReadSet:
    def __init__(self):
        self.files = {}

    def __enter__(self):
        self.token = _active.set((*_active.get(), self))
        return self

    def __exit__(self, *_):
        _active.reset(self.token)

    def add(self, path, info):
        path = Path(path)
        if not path.is_absolute() or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('qualification dependency is not one direct regular file')
        value = identity(info)
        if path in self.files and self.files[path] != value:
            raise ValueError('qualification dependency changed during validation')
        self.files[path] = value

    def check(self):
        for path, value in self.files.items():
            if path.resolve(strict=True) != path or identity(path.lstat()) != value:
                raise ValueError('qualification dependency changed: ' + str(path))
