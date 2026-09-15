"""Small private immutable records for the native session owner.

Exclusive publication, bounded reads and exact receipts are used by both live
execution and H0 reconstruction. This module makes no device decisions.
"""
import hashlib
import ctypes
import json
import os
from pathlib import Path
import re
import stat
import time
import uuid

SCHEMA = 's22plus-native-session-v3'
MAX_RECORD = 2*1024*1024
SHA = re.compile('[0-9a-f]{64}')


class SessionError(ValueError):
    pass


def require(condition, message):
    if not condition: raise SessionError(message)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'


def digest(value):
    return hashlib.sha256(value).hexdigest()


def sync_dir(path):
    fd = os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try: os.fsync(fd)
    finally: os.close(fd)


def private_path(root, path, *, exists=True):
    root = Path(root).resolve(strict=True)
    path = Path(path).absolute()
    require(path.is_relative_to(root/'workspace/private') and '..' not in path.parts,
        'native record is outside private storage')
    require(path.resolve(strict=exists)==path,'native record has an indirect path')
    return path


def _identity(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def read_bytes(path, *, maximum=MAX_RECORD):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True)==path,'record path is indirect')
    before=path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0 < before.st_size <= maximum,
        'record is not one bounded regular file')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        require(_identity(os.fstat(fd))==_identity(before),'record changed before read')
        with os.fdopen(os.dup(fd),'rb') as stream: data=stream.read(maximum+1)
        require(_identity(os.fstat(fd))==_identity(before)==_identity(path.lstat()) and len(data)==before.st_size,
            'record changed during read')
    finally: os.close(fd)
    return data


def pin(path, *, maximum=MAX_RECORD):
    data=read_bytes(path,maximum=maximum)
    return dict(path=str(path),size=len(data),sha256=digest(data))


def verify(receipt, *, maximum=MAX_RECORD):
    require(type(receipt) is dict and set(receipt)=={'path','size','sha256'},'record receipt fields differ')
    require(pin(Path(receipt['path']),maximum=maximum)==receipt,'record receipt changed')
    return Path(receipt['path'])


def read(path):
    def unique(pairs):
        result={}
        for key,value in pairs:
            require(key not in result,'duplicate record key'); result[key]=value
        return result
    return json.loads(read_bytes(path),object_pairs_hook=unique,
        parse_constant=lambda value:require(False,'nonfinite record number'))


def publish(path, value):
    path=Path(path); data=canonical(value)
    require(len(data)<=MAX_RECORD,'record exceeds bound')
    require(path.is_absolute() and path.parent.resolve(strict=True)==path.parent,'record parent is indirect')
    staging=path.parent/('.publish-'+uuid.uuid4().hex+'.tmp')
    fd=os.open(staging,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o400)
    try:
        try:
            offset=0
            while offset<len(data):
                count=os.write(fd,data[offset:]); require(count>0,'record publication made no progress'); offset+=count
            os.fsync(fd)
        finally: os.close(fd)
        # Linux renameat2(RENAME_NOREPLACE) publishes complete bytes atomically
        # without the transient two-link state of link/unlink publication.
        # Constants are the host UAPI AT_FDCWD and RENAME_NOREPLACE.
        libc=ctypes.CDLL(None,use_errno=True)
        rename=libc.renameat2
        rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
        rename.restype=ctypes.c_int
        if rename(-100,os.fsencode(staging),-100,os.fsencode(path),1)!=0:
            error=ctypes.get_errno(); raise OSError(error,os.strerror(error),str(path))
        sync_dir(path.parent)
    finally:
        if staging.exists(): staging.unlink()
    return pin(path)


def clock():
    value=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    require(type(value) is int and value>0,'host boot clock is unavailable')
    return value


def host_boot():
    value=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    require(re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',value),'host boot identity differs')
    return digest(value.encode())


class Journal:
    """One ordered file per event; intent survives every subsequent failure."""
    def __init__(self, directory, *, maximum=256):
        require(type(maximum) is int and maximum in (256,2052),'journal capacity differs')
        self.maximum=maximum
        self.directory=Path(directory)
        if not self.directory.exists():
            self.directory.mkdir(mode=0o700)
            sync_dir(self.directory.parent)

    def rows(self):
        paths=[]
        for path in self.directory.iterdir():
            # A crash before atomic publication can leave only staging bytes.
            # They have no journal ordinal and cannot authorize any effect.
            if re.fullmatch(r'\.publish-[0-9a-f]{32}\.tmp',path.name):
                info=path.lstat()
                require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size<=MAX_RECORD,
                    'journal staging entry differs')
                continue
            paths.append(path)
        paths.sort()
        require(len(paths)<=self.maximum,'native operation journal exceeds bound')
        rows=[]; previous=None
        for index,path in enumerate(paths):
            require(path.name==f'{index:04d}.json','native journal has a gap or unexpected entry')
            row=read(path)
            require(type(row) is dict and set(row)=={'schema','sequence','previous','boottime_ns','event','data'}
                and row['schema']==SCHEMA and type(row['sequence']) is int and row['sequence']==index
                and row['previous']==previous and type(row['boottime_ns']) is int and row['boottime_ns']>0
                and (not rows or rows[-1]['boottime_ns']<=row['boottime_ns'])
                and type(row['event']) is str and type(row['data']) is dict,'native journal chain differs')
            previous=pin(path); rows.append(row)
        return rows

    def append(self,event,**data):
        rows=self.rows(); index=len(rows)
        require(index<self.maximum,'native journal full')
        previous=pin(self.directory/f'{index-1:04d}.json') if index else None
        return publish(self.directory/f'{index:04d}.json',dict(schema=SCHEMA,sequence=index,
            previous=previous,boottime_ns=clock(),event=event,data=data))
