"""Resident checkpoints inside the existing ordinary boot-only F1 owner.

Own exact descriptor close/reopen and finite host deadlines. This module adds
no transfer, recovery, discovery fallback, native admission or replay path.
"""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import re
import sys
import termios
import time

import device_action_f1_v2 as core
import s22plus_native_resident_observer_v1 as observer
import s22plus_native_baseline_protocol_v1 as protocol

SCHEMA='s22plus-native-resident-ownership-v1'
GUARD_ARM='p386-resident-guard.json'
GUARD_RELEASE='p386-resident-guard-release.json'
OBSERVATION='p386-resident-observation.json'


def selected(live,bundle):
    return live._shell_bundle(bundle) and live._shell_definition(bundle).native_resident


def guard_derivation(live,bundle):
    if not selected(live,bundle):return None
    if bundle.manifest['observation']['timeout_sec']!=observer.OBSERVATION_SECONDS:
        raise live.F1LiveError('resident observation interval differs')
    # Reuse the reviewed timeout arithmetic, with a distinct resident identity.
    value=live.p313_guard_lifetime.derive(download_request_sec=live.DOWNLOAD_REQUEST_TIMEOUT_SEC,
        download_wait_sec=live.DOWNLOAD_WAIT_SEC,endpoint_revalidate_sec=live.ENDPOINT_REVALIDATE_SEC,
        odin_timeout_sec=live.ODIN_TIMEOUT_SEC,download_departure_wait_sec=live.DISCONNECT_WAIT_SEC,
        candidate_observation_sec=observer.OBSERVATION_SECONDS,
        guard_default_sec=live.cdc_acm_observer.GUARD_DEFAULT_MAX_SEC,
        guard_limit_sec=live.cdc_acm_observer.GUARD_MAX_SEC_LIMIT)
    value.update(schema=SCHEMA,overlay_contract_id=live._shell_definition(bundle).overlay)
    return value


def pin(live,path):return live._receipt(path,'resident ownership record')
def publish(live,path,value):core._write_exclusive(path,value);return pin(live,path)
def host_boot(live):return live.RETURN_HOSTS['p386'].host_boot_sha256()
def idle_wait(seconds):time.sleep(seconds)


@contextmanager
def observer_session(live,prepared,*args,**kwargs):
    derivation=guard_derivation(live,prepared.bundle)
    if prepared.prepared.get('approval_binding',{}).get('resident_guard_lifetime')!=derivation:
        raise live.F1LiveError('resident guard lifetime is not approval-bound')
    start=protocol.host_now_ns();boot=host_boot(live);arm=None
    try:
        with live.p325_guard_adapter.observer_session(*args,**kwargs,max_sec=derivation['max_sec']) as session:
            if session.guard.max_sec!=derivation['max_sec'] or not session.guard.healthy():
                raise live.F1LiveError('resident guard actual lifetime differs')
            record=dict(schema=SCHEMA,kind='guard',binding=live._candidate_observer_binding(prepared),
                derivation=derivation,host_boot_sha256=boot,started_boottime_ns=start,
                expiry_boottime_ns=start+derivation['max_sec']*10**9,
                guard=pin(live,prepared.run_dir/'candidate-observer-guard.json'))
            arm=publish(live,prepared.run_dir/GUARD_ARM,record)
            yield session
    finally:
        if arm is not None:
            # Missing close evidence prevents qualification, but never suppresses
            # the ordinary owner's mandatory preauthorized Android recovery.
            try:
                publish(live,prepared.run_dir/GUARD_RELEASE,dict(schema=SCHEMA,kind='guard-release',
                    arm=arm,guard_release=pin(live,prepared.run_dir/'candidate-observer-guard-release.json'),
                    host_boot_sha256=host_boot(live),completed_boottime_ns=protocol.host_now_ns()))
            except Exception:pass


def validate_guard(live,prepared):
    value=live._read_json(prepared.run_dir/GUARD_ARM,'resident guard');derivation=guard_derivation(live,prepared.bundle)
    if (set(value)!={'schema','kind','binding','derivation','host_boot_sha256','started_boottime_ns','expiry_boottime_ns','guard'}
            or value['schema']!=SCHEMA or value['kind']!='guard' or value['derivation']!=derivation
            or value['binding']!=live._candidate_observer_binding(prepared)
            or prepared.prepared.get('approval_binding',{}).get('resident_guard_lifetime')!=derivation
            or value['guard']!=pin(live,prepared.run_dir/'candidate-observer-guard.json')
            or type(value['host_boot_sha256']) is not str or re.fullmatch('[0-9a-f]{64}',value['host_boot_sha256']) is None
            or type(value['started_boottime_ns']) is not int or value['started_boottime_ns']<=0
            or type(value['expiry_boottime_ns']) is not int
            or value['expiry_boottime_ns']!=value['started_boottime_ns']+derivation['max_sec']*10**9):
        raise live.F1LiveError('resident retained guard differs')
    return value


def validate_guard_release(live,prepared):
    arm=validate_guard(live,prepared);value=live._read_json(prepared.run_dir/GUARD_RELEASE,'resident guard release')
    if (set(value)!={'schema','kind','arm','guard_release','host_boot_sha256','completed_boottime_ns'}
            or value['schema']!=SCHEMA or value['kind']!='guard-release'
            or value['arm']!=pin(live,prepared.run_dir/GUARD_ARM)
            or value['guard_release']!=pin(live,prepared.run_dir/'candidate-observer-guard-release.json')
            or value['host_boot_sha256']!=arm['host_boot_sha256']
            or type(value['completed_boottime_ns']) is not int
            or not arm['started_boottime_ns']<=value['completed_boottime_ns']<arm['expiry_boottime_ns']):
        raise live.F1LiveError('resident guard original lifetime/release differs')
    return value


def name(index,kind):return f'p386-resident-auth-{index:02d}.{kind}.json'


class ObserverMixin:
    @property
    def _live(self):return sys.modules[type(self).__module__]

    def _resident_publish(self,index,kind,**fields):
        stamp=fields.pop('at_boottime_ns',None)
        value=dict(schema=SCHEMA,kind=kind,index=index,binding=dict(self.base.binding),
            endpoint_identity_sha256=self.endpoint.identity_sha256,host_boot_sha256=self.resident_boot,
            at_boottime_ns=protocol.host_now_ns() if stamp is None else stamp,**fields)
        return publish(self._live,self.run_dir/name(index,kind),value)

    def _resident_budget(self,*,session=True):
        now=protocol.host_now_ns()
        limit=min(self.resident_expiry,self.resident_guard['expiry_boottime_ns'])
        if session:limit=min(limit,self.resident_session_expiry)
        if now<getattr(self,'resident_last_now',self.resident_guard['started_boottime_ns']) or now>=limit or not self.base.guard.healthy():
            raise self._live.F1LiveError('resident original budget/clock/guard expired')
        self.resident_last_now=now
        return now

    def observe(self,*,timeout_sec,download_departure):
        live=self._live
        if timeout_sec!=observer.OBSERVATION_SECONDS:raise live.F1LiveError('resident fixed observation duration differs')
        self.resident_guard=validate_guard(live,self.resident_prepared)
        self.resident_boot=host_boot(live)
        if self.resident_boot!=self.resident_guard['host_boot_sha256']:raise live.F1LiveError('resident host boot changed')
        start=protocol.host_now_ns();self.resident_expiry=start+timeout_sec*10**9
        self.resident_index=0;self.resident_reopens=0;self.resident_session_expiry=self.resident_expiry
        self.resident_observation=publish(live,self.run_dir/OBSERVATION,dict(schema=SCHEMA,kind='observation',
            binding=dict(self.base.binding),guard=pin(live,self.run_dir/GUARD_ARM),host_boot_sha256=self.resident_boot,
            started_boottime_ns=start,expiry_boottime_ns=self.resident_expiry,checkpoint_seconds=list(observer.CHECKPOINT_SECONDS)))
        self._resident_budget(session=False)
        return super().observe(timeout_sec=timeout_sec,download_departure=download_departure)

    def _resident_before_auth(self,index):
        live=self._live;now=self._resident_budget(session=False)
        if index!=self.resident_index+1 or not 1<=index<=4 or self.owned_descriptor is None:
            raise live.F1LiveError('resident authentication ordinal/ownership differs')
        if not self._endpoint_exact(self.endpoint,self.owned_descriptor):raise live.F1LiveError('resident authentication endpoint differs')
        now=self._resident_budget(session=False)
        if index==1:self.resident_anchor=now
        if now<self.resident_anchor+observer.CHECKPOINT_SECONDS[index-1]*10**9:
            raise live.F1LiveError('resident checkpoint begins too early')
        self.resident_session_expiry=min(self.resident_expiry,now+observer.SESSION_SECONDS*10**9)
        self.resident_index=index;self.resident_detach=None
        self.resident_auth=self._resident_publish(index,'auth-intent',observation=self.resident_observation,
            session_expiry_boottime_ns=self.resident_session_expiry,at_boottime_ns=now)

    def _resident_before_detach(self,request):
        self._resident_budget()
        if not self._endpoint_exact(self.endpoint,self.owned_descriptor):raise self._live.F1LiveError('resident DETACH endpoint differs')
        lane=self._live._P345ObserverSession._lane_supplement(self,True)
        if lane.get('accepted_for_p324') is not True:raise self._live.F1LiveError('resident DETACH lane differs')
        self.resident_detach=self._resident_publish(self.resident_index,'detach-intent',authentication=self.resident_auth,
            request=request,lane=lane)

    def _resident_close(self,row=None):
        current=self.owned_descriptor
        if current is None:return None
        index=self.resident_index;live=self._live
        try:
            receipt=self._resident_publish(index,'close-intent',authentication=getattr(self,'resident_auth',None),
                detach=getattr(self,'resident_detach',None) if row is not None else None,
                rx={k:row['rx'][k] for k in ('size','sha256')} if row is not None else None,
                tx={k:row['tx'][k] for k in ('size','sha256')} if row is not None else None)
        except BaseException:
            self.owned_descriptor=None
            try:os.close(current)
            except OSError:pass
            raise
        self.owned_descriptor=None;close_error=release_error=None
        if row is not None:
            try:fcntl.ioctl(current,termios.TIOCNXCL)
            except OSError as exc:release_error=type(exc).__name__
        try:os.close(current)
        except OSError as exc:close_error=type(exc).__name__
        result=self._resident_publish(index,'close-result',intent=receipt,closed=close_error is None,
            exclusivity_released=row is not None and release_error is None,close_error=close_error,release_error=release_error)
        if close_error or release_error:
            self.descriptor_close_error=close_error or release_error
            raise live.F1LiveError('resident close uncertain; descriptor cannot be retried')
        return result

    def _resident_reopen(self,row,deadline,index):
        live=self._live
        if row['ending']!='detach' or not row['detach_ack_observed'] or index!=self.resident_index+1:
            raise live.F1LiveError('resident reopening lacks clean DETACH')
        self._resident_budget()
        if not self._endpoint_exact(self.endpoint,self.owned_descriptor):raise live.F1LiveError('resident endpoint differs before close')
        self.trailing_rx=live._p327_trailing_probe(self.owned_descriptor,self.resident_writer)
        if self.trailing_rx:raise live.F1LiveError('resident unexpected bytes after DETACH')
        close=self._resident_close(row)
        self._resident_budget()
        if index==2:
            # Start dwell after the first completed authentication/close. Its
            # handshake latency cannot consume the required native sample span.
            self.resident_anchor=live._read_json(self.run_dir/name(1,'close-result'),'resident first close')['at_boottime_ns']
        due=self.resident_anchor+observer.CHECKPOINT_SECONDS[index-1]*10**9;polls=0
        while True:
            now=self._resident_budget(session=False)
            classification,endpoint=self.delegate._select();polls+=1
            if classification!='accepted' or endpoint is None or endpoint.identity_sha256!=self.endpoint.identity_sha256:
                raise live.F1LiveError('resident endpoint changed while closed')
            if now>=due:break
            idle_wait(min(1,(due-now)/10**9))
        if time.monotonic()>=deadline or not self._endpoint_exact(self.endpoint):raise live.F1LiveError('resident reopening endpoint/deadline differs')
        intent=self._resident_publish(index,'reopen-intent',close=close,not_before_boottime_ns=due,idle_checks=polls)
        descriptor=os.open(self.base.dev_root/self.endpoint.tty_name,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK|os.O_CLOEXEC)
        self.owned_descriptor=descriptor
        self.resident_auth=None;self.resident_detach=None
        # The newly opened descriptor belongs to its next index even when a
        # subsequent ioctl fails before AUTH. Final cleanup must name that slot.
        self.resident_index=index-1
        self.resident_pending_index=index
        fcntl.ioctl(descriptor,termios.TIOCEXCL)
        if not self._endpoint_exact(self.endpoint,descriptor):raise live.F1LiveError('resident reopened descriptor differs')
        self.base._raw_tty(descriptor);self._resident_budget(session=False)
        self._resident_publish(index,'reopen-result',intent=intent,status='reopened')
        self.resident_reopens+=1
        return descriptor

    def _resident_final_close(self):
        pending=getattr(self,'resident_pending_index',None)
        if pending is not None and self.resident_index<pending:self.resident_index=pending
        self._resident_close()

    def _qualify_on_descriptor(self,codec,descriptor,writer,deadline):
        self._require_control_absent();self.resident_writer=writer
        if type(self.root_console_plan_value) is not dict or type(self.root_console_plan_receipt) is not dict:
            raise self._live.F1LiveError('resident sealed empty plan absent')
        return self.qualification_observer.qualify(codec,descriptor,self.auth_key,None,set(),writer,deadline=deadline,
            before_auth=self._resident_before_auth,before_write=self._resident_budget,
            before_detach=self._resident_before_detach,reopen=self._resident_reopen,
            before_control=lambda request:self._resident_control(request),
            evidence=self.run_dir/'p386-root-console-evidence',
            interactive=lambda *_:self._live.ROOT_CONSOLE_PLAN_OWNERS[self.namespace].validate(self.root_console_plan_value))

    def _resident_control(self,request):
        self._resident_budget()
        self._seal_control_intent(request,self.owned_descriptor)


def project_observation(session,value,complete):
    value.update(same_tty_fd=False,physical_reopen_count=session.resident_reopens,framed_session_closed=False)
    if value['accepted'] and value.get('descriptor_close_error') is not None:
        value.update(accepted=False,classification='authenticated-session-error',qualification_complete=False,
            pid1_framed_exec_proof=False,busybox_ash_command_proof=False,root_console=False,protocol_error='resident-close-unproved')


def proof_ok(value,variant):
    proof=value.get('proof',value.get(variant.proof_key))
    return (all(value.get(k) is True for k in ('qualification_complete','pid1_framed_exec_proof',
                'busybox_ash_command_proof','root_console','control_acceptance_observed'))
        and value.get('same_tty_fd') is False and value.get('framed_session_closed') is False
        and type(value.get('session_count')) is int and value['session_count']==4
        and type(value.get('physical_reopen_count')) is int and value['physical_reopen_count']==3
        and value.get('command_count')==proof.get('command_count')==8 and value.get('request_count')==16
        and value.get('descriptor_close_error') is None and value.get('later_action_lease_active') is False
        and value.get('caller_selected_command') is False and type(value.get('root_uid')) is int and value['root_uid']==0
        and type(value.get('root_gid')) is int and value['root_gid']==0
        and value.get('control_requested_mode')=='download' and value.get('control_ack_scope')=='acceptance-only'
        and value.get('software_download_arrival')=='UNPROVED' and value.get('proof_scope')==variant.observer.PROOF_SCOPE
        and all(type(value.get(variant.prefix+'_'+k)) is dict for k in ('control_intent','console_plan','plan_execution','closure_snapshot'))
        and value[variant.prefix+'_plan_execution'].get('all_planned_terminal') is True)


def validate_ownership(live,prepared,value,proof):
    """Reopen descriptor facts against authenticated raw; no receipt-only proof."""
    guard=validate_guard(live,prepared);observation=live._read_json(prepared.run_dir/OBSERVATION,'resident observation')
    binding=live._candidate_observer_binding(prepared);endpoint=value['endpoint_identity_sha256']
    if (set(observation)!={'schema','kind','binding','guard','host_boot_sha256','started_boottime_ns','expiry_boottime_ns','checkpoint_seconds'}
            or observation['schema']!=SCHEMA or observation['kind']!='observation' or observation['binding']!=binding
            or observation['guard']!=pin(live,prepared.run_dir/GUARD_ARM) or observation['host_boot_sha256']!=guard['host_boot_sha256']
            or type(observation['started_boottime_ns']) is not int or observation['started_boottime_ns']<guard['started_boottime_ns']
            or observation['expiry_boottime_ns']!=observation['started_boottime_ns']+observer.OBSERVATION_SECONDS*10**9
            or observation['checkpoint_seconds']!=list(observer.CHECKPOINT_SECONDS)):
        raise live.F1LiveError('resident observation binding differs')
    common={'schema','kind','index','binding','endpoint_identity_sha256','host_boot_sha256','at_boottime_ns'}
    def read(index,kind,fields):
        path=prepared.run_dir/name(index,kind);record=live._read_json(path,'resident '+kind)
        if (set(record)!=common|set(fields) or record['schema']!=SCHEMA or record['kind']!=kind
                or type(record['index']) is not int or record['index']!=index or record['binding']!=binding
                or record['endpoint_identity_sha256']!=endpoint or record['host_boot_sha256']!=guard['host_boot_sha256']
                or type(record['at_boottime_ns']) is not int
                or not observation['started_boottime_ns']<=record['at_boottime_ns']<min(observation['expiry_boottime_ns'],guard['expiry_boottime_ns'])):
            raise live.F1LiveError('resident retained '+kind+' differs')
        return record,pin(live,path)
    anchor=0;previous_close=None
    for index,row in enumerate(proof['sessions'],1):
        auth,ap=read(index,'auth-intent',('observation','session_expiry_boottime_ns'))
        if (auth['observation']!=pin(live,prepared.run_dir/OBSERVATION)
                or index>1 and auth['at_boottime_ns']<anchor+observer.CHECKPOINT_SECONDS[index-1]*10**9
                or type(auth['session_expiry_boottime_ns']) is not int
                or not auth['at_boottime_ns']<auth['session_expiry_boottime_ns']<=min(observation['expiry_boottime_ns'],auth['at_boottime_ns']+observer.SESSION_SECONDS*10**9)):
            raise live.F1LiveError('resident authentication original deadline differs')
        if index>1:
            ri,rip=read(index,'reopen-intent',('close','not_before_boottime_ns','idle_checks'))
            rr,_=read(index,'reopen-result',('intent','status'))
            if (ri['close']!=previous_close or ri['not_before_boottime_ns']!=anchor+observer.CHECKPOINT_SECONDS[index-1]*10**9
                    or ri['at_boottime_ns']<ri['not_before_boottime_ns'] or type(ri['idle_checks']) is not int or ri['idle_checks']<1
                    or rr['intent']!=rip or rr['status']!='reopened'
                    or not ri['at_boottime_ns']<=rr['at_boottime_ns']<=auth['at_boottime_ns']):
                raise live.F1LiveError('resident actual descriptor reopen differs')
        detach_pin=None
        if index<4:
            detach,detach_pin=read(index,'detach-intent',('authentication','request','lane'))
            request=dict(run_id_hex=row['run_id_hex'],mode='detach',sequence=6,nonce_sha256=row['nonce_sha256'],
                kernel_boot_identity_sha256=row['kernel_boot_identity_sha256'],resident_info=row['resident_info'])
            if (detach['authentication']!=ap or detach['request']!=request or detach['lane'].get('accepted_for_p324') is not True
                    or not auth['at_boottime_ns']<=detach['at_boottime_ns']<auth['session_expiry_boottime_ns']):
                raise live.F1LiveError('resident DETACH raw ownership differs')
        close,cp=read(index,'close-intent',('authentication','detach','rx','tx'))
        result,previous_close=read(index,'close-result',('intent','closed','exclusivity_released','close_error','release_error'))
        if (close['authentication']!=ap or close['detach']!=detach_pin
                or close['rx']!=({k:row['rx'][k] for k in ('size','sha256')} if index<4 else None)
                or close['tx']!=({k:row['tx'][k] for k in ('size','sha256')} if index<4 else None)
                or result['intent']!=cp or result['closed'] is not True
                or result['exclusivity_released'] is not (index<4) or result['close_error'] is not None or result['release_error'] is not None
                or not auth['at_boottime_ns']<=close['at_boottime_ns']<=result['at_boottime_ns']<auth['session_expiry_boottime_ns']):
            raise live.F1LiveError('resident actual descriptor close differs')
        if index==1:anchor=result['at_boottime_ns']
    return True
