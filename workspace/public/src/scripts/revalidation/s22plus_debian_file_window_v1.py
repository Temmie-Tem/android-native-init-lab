"""A host time window only; no USB proof, device query or write/replay command."""
from pathlib import Path
import time

import s22plus_debian_file_profile_v1 as profile
from s22plus_native_records_v3 import Journal,clock,pin,publish,read,require,verify


def basis(adapter,request):
    require(request['N']['profile']==profile.PROFILE,'unselected file window')
    rows=Journal(adapter.directory/'journal').rows()
    completed=[row for row in rows if row['event']=='step-complete' and row['data']['step']=='install-native-first']
    intents=[row for row in rows if row['event']=='effect-intent' and row['data']['step']=='install-native-first']
    require(len(completed)==len(intents)==1 and intents[0]['data']['action']=='transfer' and
        intents[0]['data']['role']=='N','file window lacks its unique automatic-write owner')
    from s22plus_native_session_v3 import Step
    transfer=adapter.recover_transfer_result(Step('install-native-first','transfer','N'),request)
    require(read(verify(completed[0]['data']['result']))==transfer,'file N transfer does not rederive')
    grant=read(verify(request['grant']));end=completed[0]['boottime_ns']+profile.WINDOW_SECONDS*1_000_000_000
    require(end<grant['deadline_ns'],'original grant cannot contain the fixed file window')
    return dict(operation=pin(adapter.directory/'operation.json'),grant=request['grant'],
        transfer=completed[0]['data']['result'],transfer_completed_ns=completed[0]['boottime_ns'],
        host_boot=grant['host_boot'],window_end_ns=end)


def rederive(adapter,request):
    folder=adapter.folder('debian-early-evidence');opened=read(folder/'open.json');closed=read(folder/'close.json')
    bound=basis(adapter,request);grant=read(verify(request['grant']))
    require(set(opened)=={'basis','started_ns'} and opened['basis']==bound and
        bound['transfer_completed_ns']<=opened['started_ns']<grant['deadline_ns'] and
        set(closed)=={'open','completed_ns'} and closed['open']==pin(folder/'open.json') and
        max(opened['started_ns'],bound['window_end_ns'])<=closed['completed_ns']<grant['deadline_ns'],
        'file execution window is incomplete or belongs to another operation')
    return dict(proof=dict(status='AWAITING_OFFLINE_FILE_RECORD',debian_early_pid1=False,
        installed_debian_pid1=False,preparation_complete=False,root_admitted=False,
        live_usb_proved=False,file_write_proved=False,device_activity='UNKNOWN',replay_authorized=False),
        open=pin(folder/'open.json'),close=pin(folder/'close.json'))


def observe(adapter,request,*,guard):
    profile.image_binding(request['N']);bound=basis(adapter,request)
    folder=adapter.folder('debian-early-evidence');folder.mkdir(mode=0o700)
    guard();publish(folder/'open.json',dict(basis=bound,started_ns=clock()))
    last=clock()
    while last<bound['window_end_ns']:
        guard();time.sleep(min(0.2,(bound['window_end_ns']-last)/1_000_000_000))
        now=clock();require(now>=last,'host BOOTTIME moved backward');last=now
    guard();publish(folder/'close.json',dict(open=pin(folder/'open.json'),completed_ns=clock()))
    return rederive(adapter,request)
