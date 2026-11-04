"""Task-local interlock for an actually issued physical attach instruction.

This is not a readiness gate: no issued cue closes immediately. The lock is
independent of the target lease, which the executing Session already holds.
"""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import time

from s22plus_native_records_v3 import clock,host_boot,pin,publish,read,require,verify


@contextmanager
def locked(operation,deadline_ns=None):
    fd=os.open(Path(operation)/'mainline-attach.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        while True:
            if deadline_ns is not None:require(clock()<deadline_ns,'original attach lock window expired')
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                if deadline_ns is None:raise  # Evidence-only resolution may retry, without waiting or authority.
                time.sleep(min(.01,max(0,(deadline_ns-clock())/1e9)))
        yield
    finally:
        fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)


def binding(operation,window,*,live=True):
    operation=Path(operation)
    value=read(verify(window))
    require(value['operation']==pin(operation/'operation.json'),'attach cue belongs to another operation')
    if live:require(value['host_boot']==host_boot(),'attach cue belongs to another host boot')
    return dict(operation=value['operation'],window=window,host_boot=value['host_boot'])


def issue(operation,window,*,evidence,check):
    """Persist before emitting the cue. The caller rechecks its fixed census."""
    operation=Path(operation)
    deadline=read(verify(window))['deadline_ns']
    with locked(operation,deadline):
        require(not (operation/'mainline-attach-closed.json').exists(),'attach issuance is closed')
        value=binding(operation,window);check()
        require(clock()<read(verify(window))['deadline_ns'],'attach window expired')
        receipt=publish(operation/'mainline-attach-cue.json',dict(value,evidence=evidence,issued_ns=clock()))
        require(clock()<deadline,'attach issuance publication exceeded original window')
        return receipt


def resolve(operation,window,*,cue,resolution,operator_statement):
    """Only record an actual returned completion/cancellation, never silence."""
    operation=Path(operation)
    with locked(operation):
        require(not (operation/'mainline-attach-closed.json').exists(),'attach issuance is closed')
        value=binding(operation,window)
        require(cue==pin(operation/'mainline-attach-cue.json') and
                all(read(verify(cue))[k]==v for k,v in value.items()),'wrong attach cue owner')
        require(resolution in ('completed','cancelled') and type(operator_statement) is str and
                0<len(operator_statement.strip())<=4096,'actual operator resolution is required')
        return publish(operation/'mainline-attach-resolution.json',dict(value,cue=cue,resolution=resolution,
            operator_statement=operator_statement,resolved_ns=clock()))


def rederive(operation,window):
    operation=Path(operation);expected=binding(operation,window,live=False)
    value=read(operation/'mainline-attach-closed.json')
    require(set(value)==set(expected)|{'cue','resolution','closed_ns'} and
            all(value[k]==v for k,v in expected.items()),'attach closure binding differs')
    if value['cue'] is None:
        require(value['resolution'] is None and not (operation/'mainline-attach-cue.json').exists() and
                not (operation/'mainline-attach-resolution.json').exists(),'unissued cue has a resolution')
    else:
        require(value['cue']==pin(operation/'mainline-attach-cue.json') and
                value['resolution']==pin(operation/'mainline-attach-resolution.json'),'attach records changed')
        cue=read(verify(value['cue']));resolved=read(verify(value['resolution']))
        require(all(cue[k]==resolved[k]==v for k,v in expected.items()) and resolved['cue']==value['cue'] and
                resolved['resolution'] in ('completed','cancelled') and
                type(resolved['operator_statement']) is str and 0<len(resolved['operator_statement'].strip())<=4096 and
                cue['issued_ns']<=resolved['resolved_ns']<=value['closed_ns'],'attach resolution differs')
    require(read(verify(window))['opened_ns']<=value['closed_ns']<read(verify(window))['deadline_ns'],
            'attach closure outside the original window')
    return pin(operation/'mainline-attach-closed.json')


def close_issuance(operation,window,*,guard):
    operation=Path(operation)
    guard()
    while True:
        with locked(operation,read(verify(window))['deadline_ns']):
            value=binding(operation,window)
            require(clock()<read(verify(window))['deadline_ns'],'original attach/control window expired')
            require(not (operation/'mainline-attach-closed.json').exists(),'attach closure already consumed')
            cue=operation/'mainline-attach-cue.json';resolution=operation/'mainline-attach-resolution.json'
            if not cue.exists() or resolution.exists():
                require(cue.exists() or not resolution.exists(),'resolution without an issued cue')
                publish(operation/'mainline-attach-closed.json',dict(value,cue=pin(cue) if cue.exists() else None,
                    resolution=pin(resolution) if resolution.exists() else None,closed_ns=clock()))
                return rederive(operation,window)
        time.sleep(min(0.25,max(0,(read(verify(window))['deadline_ns']-clock())/1e9)))
