"""V6 original-owner recovery: bounded observation, then the existing A slot.

No candidate decoder, key, builder or completed-N receipt is a prerequisite.
The immutable task/capability is checked by the Session recovery guard. This
module reads only the selected metadata and original durable launch intent.
"""
from dataclasses import asdict
from pathlib import Path
import time

import s22plus_boot_only_f1_transport as transport
import s22plus_mainline_attach_v1 as attach
import s22plus_mainline_profile_v1 as profile
import s22plus_native_target_io_v3 as target
import s22plus_odin_transition_core as transition
from s22plus_native_records_v3 import Journal, clock, host_boot, pin, publish, read, require, verify

def _report_modes():
    """The single report-version declaration beside the module sources."""
    import sys
    source = str(profile.ROOT/'workspace/public/src/mainline/s22plus_ufs_link_h0')
    if source not in sys.path:
        sys.path.insert(0, source)
    import report_modes
    return report_modes


def _automatic(version):
    """Report versions that arm the child-owned automatic Download attempt."""
    modes = _report_modes()
    return type(version) is int and modes.FIRST['hce_handoff'] <= version <= modes.LATEST


ARRIVAL_NS = 660_000_000_000
FOLDER = 'io-mainline-auto-recovery'


def selected(request):
    image=request.get('N',{})
    if request.get('operation') != 'mainline-ram':
        return False
    if profile.timed_return(image):
        return True
    if image.get('schema')!='s22plus-mainline-ufs-image-v2':
        return False
    cap=read(verify(image['capability']))
    require(cap['schema']=='s22plus-mainline-ufs-capability-v2' and
            cap['scope']=='S22PLUS_LATE_UFS_KEY_ONLY_V2','automatic recovery capability scope')
    return _automatic(cap['fixed']['report_version'])


def window(adapter,request,*,epoch=None):
    """The live owner checks the current host boot; a historical projection
    (epoch given) checks the epoch the window recorded against the grant."""
    require(selected(request),'automatic recovery is not selected')
    operation=pin(adapter.directory/'operation.json')
    grant=read(verify(request['grant']))
    require(grant['host_boot']==(host_boot() if epoch is None else epoch),'automatic recovery host epoch changed')
    rows=Journal(adapter.directory/'journal').rows()
    launches=[r for r in rows if r['event']=='effect-intent' and r['data']['action']=='transfer'
              and r['data']['role']=='N']
    require(len(launches)<=1,'automatic recovery has multiple native intents')
    require(launches or not profile.timed_return(request.get('N', {})), 'timed return requires the original N launch')
    if launches:
        row=launches[0];receipt=row['data']['detail']['launch'];path=verify(receipt);launch=read(path)
        require(row['data']['step']==launch['step']=='install-native-first' and launch['role']=='N' and
                launch['ap']==request['N']['ap'] and launch['member']==request['N']['member'] and
                path.name=='launch.json' and path.parent.name.startswith('attempt-') and
                path.parent.parent==adapter.folder('install-native-first') and
                type(launch['boottime_ns']) is int and
                0<launch['boottime_ns']<=row['boottime_ns'] and launch['ticket'] and launch['revalidation'],
                'automatic recovery original native launch differs')
        opened=launch['boottime_ns'];end=opened+ARRIVAL_NS;basis=receipt;phase='N_INTENDED'
    else:
        # A failed original Android->Download can require recovery before N.
        # Reuse that command's existing arrival bound, never open a new one.
        departures=[r for r in rows if r['event']=='effect-intent' and
                    r['data']['step']=='android-download' and r['data']['action']=='download']
        require(len(departures)==1 and departures[0]['data']['role']=='A',
                'automatic recovery has no original departure basis')
        row=departures[0];detail=row['data']['detail']
        opened=row['boottime_ns'];end=detail['departure_deadline_ns']+60_000_000_000
        require(type(end) is int and opened<end<=opened+120_000_000_000,'pre-N departure bound')
        basis=pin(adapter.directory/'journal'/f"{row['sequence']:04d}.json")
        phase='PRE_N_DEPARTURE'
    return dict(operation=operation,host_boot=grant['host_boot'],phase=phase,basis=basis,
                opened_ns=opened,deadline_ns=end)


def deadline(adapter,request,receipt,*,historical=False):
    recorded=read(verify(receipt))
    epoch=recorded['host_boot'] if historical else None
    require(recorded==window(adapter,request,epoch=epoch),'automatic recovery window was renewed or changed')
    return recorded['deadline_ns']


def ticket_generation(ticket):
    if isinstance(ticket,dict):ticket=transition.EndpointTicket(**ticket)
    payload,identity=transition._read_sealed_receipt(Path(ticket.snapshot_receipt))
    require(identity['sha256']==ticket.snapshot_receipt_sha256 and
            payload['schema']==transition.SNAPSHOT_SCHEMA and payload['sequence']==ticket.snapshot_sequence and
            payload['live_devices']==[ticket.device] and
            payload['live_device_identities']==[[ticket.device,ticket.device_identity]],
            'automatic recovery ticket does not join measured snapshot')
    evidence=payload['endpoint_transition_evidence']
    transition.usbfs_identity.validate_enumeration_evidence(evidence)
    require(evidence['live_devices']==[ticket.device],'automatic recovery live-node evidence differs')
    rows=[r for r in evidence['node_transitions'] if r['path']==ticket.device]
    require(len(rows)==1 and rows[0]['identity']==ticket.device_identity,'automatic recovery node identity differs')
    node=rows[0]['after']
    require(node['birth_time_ns']>0,'automatic recovery requires measured node birth')
    return {k:node[k] for k in ('path','st_dev','st_ino','birth_time_ns')}


def after_original_generation(original,ticket):
    # Full identity also includes permissions/ownership. A changed hash alone
    # is not a USB replacement: require a strictly later measured node birth.
    return ticket_generation(ticket)['birth_time_ns']>original['birth_time_ns']


def admit_ticket(adapter,request,receipt,ticket):
    end=deadline(adapter,request,receipt);bound=read(verify(receipt))
    if bound['phase']=='N_INTENDED':
        original=ticket_generation(read(verify(bound['basis']))['ticket'])
        require(after_original_generation(original,ticket),
                'automatic A cannot use the original N Download generation')
    require(clock()<end,'automatic A arrival exceeded original cap')


cue_settled = attach.cue_settled


def observe(session,receipt,folder):
    adapter=session.adapter;request=session.request
    end=deadline(adapter,request,receipt)
    while not cue_settled(adapter.directory):
        session.check(recovery=True)
        if clock()>=end:return dict(status='ATTACH_UNRESOLVED',observed_ns=clock())
        time.sleep(min(.25,max(0,(end-clock())/1e9)))
    if clock()>=end:return dict(status='WINDOW_EXPIRED',observed_ns=clock())
    task=adapter.configuration(request);endpoints=folder/'endpoints';endpoints.mkdir(mode=0o700)
    bound=read(verify(receipt))
    origin=ticket_generation(read(verify(bound['basis']))['ticket']) if bound['phase']=='N_INTENDED' else None
    with transport.pin_regular_file(Path(task['odin']['path']),label='automatic recovery enumeration',
            expected_size=task['odin']['size'],expected_sha256=task['odin']['sha256']) as odin, \
            transition.transaction_session(endpoints) as lease:
        def guard():
            session.check(recovery=True)
            transport.revalidate_pinned_path(odin)
            require(clock()<end,'automatic recovery original observation expired')
            return transition.measured_usbfs_observer(endpoints)
        sequence=0
        while clock()<end:
            # The candidate's own USB node can depart during an empty census at
            # the timer reset (route-timer run 4); that census is retried.
            found=transition.wait_for_single_live_endpoint(odin.path,endpoints,
                timeout_sec=max(.001,(end-clock())/1e9),lease=lease,endpoint_observer_factory=guard,
                sequence_start=sequence,monotonic=lambda:clock()/1e9,allow_empty_census_departure=True)
            sequence=found.next_sequence
            if found.timed_out or found.ticket is None:break
            if origin is not None and not after_original_generation(origin,found.ticket):
                # An uncertain N may still be in its original Download mode.
                # Only a different measured USB generation can select auto A.
                time.sleep(min(1,max(0,(end-clock())/1e9)));continue
            identity=target.download_identity(found.ticket.device)
            require(clock()<end,'automatic Download identity completed late')
            return dict(status='EXACT_DOWNLOAD_OBSERVED',observed_ns=clock(),
                        ticket=asdict(found.ticket),target=identity)
        return dict(status='DOWNLOAD_NOT_OBSERVED',observed_ns=clock())


def attempt(session):
    """Called once on stop, while execute() still owns the target lease."""
    adapter=session.adapter;request=session.request
    if not selected(request):return None
    session.check(recovery=True)
    from consumed_candidate_registry_v1 import require_f1_owner
    require_f1_owner(session.root,session.directory,session.binding)
    android=[r for r in session.rows() if r['event']=='effect-intent' and
             r['data']['action']=='transfer' and r['data']['role']=='A']
    require(len(android)<=1,'automatic recovery has multiple A intents')
    if android:
        # _recover_android rederives the intended A. It cannot dispatch again.
        return session._recover_android(attended=True)
    if profile.timed_return(request.get('N', {})) and not any(
            row['event']=='effect-intent' and row['data']['action']=='transfer' and row['data']['role']=='N'
            for row in session.rows()):
        return None
    folder=adapter.directory/FOLDER
    if folder.exists():return None  # No second autonomous wait/dispatch owner.
    folder.mkdir(mode=0o700)
    receipt=publish(folder/'window.json',window(adapter,request))
    outcome=observe(session,receipt,folder)
    publish(folder/'observation.json',dict(window=receipt,**outcome))
    if outcome['status']!='EXACT_DOWNLOAD_OBSERVED':return None
    # The observation lease ended. The transfer reobserves under its own lease
    # and retains every artifact/target/recovery/no-replay check at the effect.
    result=session._recover_android(attended=True,recovery_window=receipt)
    publish(folder/'complete.json',dict(window=receipt,result=result,finished_ns=clock()))
    return result
