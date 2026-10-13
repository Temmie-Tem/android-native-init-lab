"""Reuse unchanged H0 file qualification; never cache device or grant state.

Archive decoding is expensive enough to overrun a 10-second USB snapshot.
Every cached input retains its exact regular-file metadata identity; any change
reopens the ordinary complete validator before the next effect. The fixed
dependency walk follows only the files read by this file-profile validator.
"""
import copy
import hashlib
import json
from pathlib import Path
import stat
from s22plus_native_records_v3 import read,require,verify

_cache={}


def _receipts(value,rows):
    if isinstance(value,dict):
        if set(value)=={'path','size','sha256'}:
            previous=rows.setdefault(value['path'],value)
            require(previous==value,'qualification contains conflicting file identities')
        else:
            for child in value.values():_receipts(child,rows)
    elif isinstance(value,list):
        for child in value:_receipts(child,rows)


def _inputs(image):
    rows={};_receipts(image,rows)
    artifact=read(verify(image['early_boot']));qualified=read(verify(image['qualification']))
    built=read(verify(artifact['build']));tested=read(verify(artifact['vm']))
    for value in (artifact,qualified,built,tested):_receipts(value,rows)
    for case in tested['cases']:
        # This includes the virtual helper, writer, generated headers and CPIO.
        _receipts(read(verify(case['helper_request'])),rows)
    return tuple(rows[path] for path in sorted(rows))


def _state(receipts):
    result=[]
    for row in receipts:
        path=Path(row['path']);st=path.lstat()
        require(path.is_absolute() and path.resolve(strict=True)==path and stat.S_ISREG(st.st_mode) and
            st.st_nlink==1 and st.st_size==row['size'],
            'qualified input is not the same bounded regular file')
        result.append((str(path),st.st_dev,st.st_ino,st.st_mode,st.st_nlink,st.st_size,st.st_mtime_ns,st.st_ctime_ns))
    return tuple(result)


def binding(image,validator):
    from s22plus_debian_early_profile_v1 import CHECKED_FILE_PROFILES
    require(image.get('profile') in CHECKED_FILE_PROFILES,'cache is restricted to checked file qualification')
    key=hashlib.sha256(json.dumps(image,sort_keys=True,separators=(',',':')).encode()).digest()
    previous=_cache.get(key)
    if previous is not None:
        receipts,state,result=previous
        if _state(receipts)==state:return copy.deepcopy(result)
    receipts=_inputs(image);before=_state(receipts)
    result=validator(image)
    require(_state(receipts)==before,'qualification inputs changed during validation')
    if len(_cache)>=4:_cache.clear()
    _cache[key]=(receipts,before,copy.deepcopy(result))
    return result
