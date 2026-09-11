"""Fixed resident checkpoint qualification on caller-owned exact descriptors.

No endpoint discovery, transfer or authority. The outer owner closes/reopens
the descriptor and enforces its finite BOOTTIME grant across idle intervals.
"""
import copy
import json
from pathlib import Path
import re
import struct
import time
from types import SimpleNamespace

import s22plus_native_resident_protocol_v1 as protocol
import s22plus_native_resident_source_v1 as source
import s22plus_native_baseline_protocol_v1 as baseline
import s22plus_native_baseline_health_v1 as health
import s22plus_native_console_observer_v1 as console
import s22plus_root_console_v1 as wire

CHECKPOINT_SECONDS = (0, 620, 920, 1820)
OBSERVATION_SECONDS = 2100
SESSION_SECONDS = 60
MINIMUM_SPAN_MS = 1800000
HUD_COMMAND = (b"printf 'S22RPROBE1\\n' && /bin/busybox cat /proc/uptime && "
               b"/bin/busybox cat hud.log && printf 'S22RPROBE1 COMPLETE\\n'")
HUD_BODY = wire.command(HUD_COMMAND, cwd=b'/s22-root-work', timeout_ms=15000)
_STATE = rb'(ABSENT|RUNNING|EOF|FAULT|WAIT UNKNOWN|WAITING|STALE|FRESH)'
_FRAME = re.compile(rb'RESIDENT_FRAME seq=(\d+) ms=(\d+) state=(\d+)'
    rb' system_seq=(\d+) system='+_STATE+rb' system_valid=(\d+) system_age=(\d+)'
    rb' hardware_seq=(\d+) hardware='+_STATE+rb' hardware_valid=(\d+) hardware_age=(\d+)'
    rb' gauge_seq=(\d+) gauge_age=(\d+) cpu_temp_mc=(-?\d+) cpu_mask=(\d+) expected=13'
    rb' producer_dropped=(\d+) event=matched visible=UNPROVED\n')
_FIELDS = ('sequence','boottime_ms','state','system_sequence','system_state','system_valid','system_age_ms',
           'hardware_sequence','hardware_state','hardware_valid','hardware_age_ms','gauge_sequence',
           'gauge_age_ms','cpu_temp_mc','cpu_mask','producer_dropped')


def decode_probe(raw):
    if type(raw) is not bytes or len(raw)>50000:
        raise ValueError('resident probe output bound differs')
    parts=raw.split(b'\n',2)
    if len(parts)!=3 or parts[0]!=b'S22RPROBE1' or not parts[2].endswith(b'S22RPROBE1 COMPLETE\n'):
        raise ValueError('resident probe framing differs')
    uptime=re.fullmatch(rb'(\d+)\.(\d{2}) (\d+)\.(\d{2})',parts[1])
    if not uptime:raise ValueError('resident proc BOOTTIME differs')
    seconds,hundredths,_,_=map(int,uptime.groups());now=seconds*1000+hundredths*10
    if not 0<now<=protocol.MAX_COUNTER:raise ValueError('resident proc BOOTTIME range differs')
    retained=protocol.decode_log(parts[2][:-len(b'S22RPROBE1 COMPLETE\n')]);frames=[];last_valid_gauge=0
    for raw_row in retained['records']:
        if not raw_row.startswith(b'RESIDENT_FRAME '):continue
        match=_FRAME.fullmatch(raw_row)
        if not match:raise ValueError('resident matched frame grammar differs')
        row={name:value.decode() if name.endswith('_state') else int(value)
             for name,value in zip(_FIELDS,match.groups(),strict=True)}
        if (any(not 0<=v<=protocol.MAX_COUNTER for k,v in row.items() if type(v) is int and k!='cpu_temp_mc')
                or not row['sequence'] or row['state']>8 or row['system_valid']&~3
                or row['hardware_valid']&~508 or row['cpu_mask']&~8191
                or row['hardware_valid']&256 and (not row['cpu_mask'] or not -40000<=row['cpu_temp_mc']<=150000)
                or row['boottime_ms']>now+9):
            raise ValueError('resident matched frame fields differ')
        if frames and (row['sequence']<=frames[-1]['sequence'] or row['boottime_ms']<frames[-1]['boottime_ms']
                or any(row[k]<frames[-1][k] for k in ('system_sequence','hardware_sequence','producer_dropped'))):
            raise ValueError('resident retained frame order differs')
        if row['hardware_valid']&224:
            if not row['gauge_sequence'] or row['gauge_sequence']<last_valid_gauge:
                raise ValueError('resident valid gauge sequence regressed')
            last_valid_gauge=row['gauge_sequence']
        frames.append(row)
    latest=frames[-1] if frames else None
    # /proc/uptime truncates to 10 ms. Adding 9 gives the upper clock bound.
    # The snapshot stamp precedes record emission, so adding its whole delay to
    # the recorded source age is conservative rather than relabelling old data.
    delay_upper=max(0,now+9-latest['boottime_ms']) if latest else None
    current_ages={key:delay_upper+latest[key] for key in ('system_age_ms','hardware_age_ms','gauge_age_ms')} if latest else None
    fresh=bool(latest and delay_upper<=5000 and
        latest['system_state']=='FRESH' and latest['system_valid']==3 and current_ages['system_age_ms']<=5000 and
        latest['hardware_state']=='FRESH' and latest['hardware_valid']&224==224 and
        current_ages['hardware_age_ms']<=5000 and current_ages['gauge_age_ms']<=5000 and
        all(latest[k]>0 for k in ('system_sequence','hardware_sequence','gauge_sequence')))
    return dict(proc_boottime_ms=now,log={k:v for k,v in retained.items() if k!='records'},
        frame_count=len(frames),latest=latest,current_age_upper_ms=current_ages,fresh_system_and_gauge=fresh,
        cpu_temperature_observed=bool(latest and latest['hardware_valid']&256 and fresh),
        physical_visibility='UNPROVED',continuous_liveness='UNPROVED')


def probe_from_events(session,events):
    rows=console.command_rows(session,events)
    if len(rows)!=2:raise ValueError('resident fixed checkpoint command count differs')
    hud=rows[1]
    if (hud['terminal'] is None or hud['terminal'][:4]!=[5,0,0,0] or hud['terminal'][5]!=0
            or hud['stderr']['size'] or not hud['accepted'] or hud['rejected']):
        raise ValueError('resident checkpoint export is incomplete')
    raw=b''.join(p[12:] for k,n,p in events if (k,n)==(wire.OUTPUT,5) and struct.unpack_from('<I',p,8)[0]==1)
    return decode_probe(raw)


def replay_one(codec,identity,key,rx,tx):
    io=protocol.IO(codec,key,identity,rx=rx,tx=tx);io.handshake()
    rend=baseline._root_end(rx,io.rpos,(wire.CONTROL_ACK,protocol.DETACH_ACK))
    tend=baseline._root_end(tx,io.tpos,(wire.CONTROL,protocol.DETACH))
    session,events=wire.replay(key,bytes.fromhex(identity.run_id_hex),io.audit.nonce,
        rx[io.rpos:rend],tx[io.tpos:tend],session_class=protocol.Session)
    if any(events[i][1]>events[i+1][1] for i in range(len(events)-1)):
        raise ValueError('resident response phase order differs')
    baseline._fixed_health(session,events)
    ending=session.requests.get(6)
    if (session.requests!={3:wire.EXEC,4:wire.STATUS,5:wire.EXEC,6:ending}
            or ending not in (wire.CONTROL,protocol.DETACH) or session.request_bodies[5]!=HUD_BODY):
        raise ValueError('resident fixed checkpoint requests differ')
    rows=console.command_rows(session,events);probe=probe_from_events(session,events)
    info=io.preparation.info
    if ending==protocol.DETACH and info['authentication_ordinal']==protocol.MAX_COUNTER:
        raise ValueError('resident checkpoint exhausted reentry')
    return dict(run_id_hex=identity.run_id_hex,ending='detach' if ending==protocol.DETACH else 'download',
        detach_ack_observed=ending==protocol.DETACH,control_acceptance_observed=ending==wire.CONTROL,
        terminal_sequence=6,resident_info=info,preparation=io.preparation.projection(),root_ready=list(session.ready),
        kernel_boot_identity_sha256=health.digest(io.audit.boot_id),nonce_sha256=health.digest(io.audit.nonce),
        commands=rows,request_count=4,native_health_proved=True,all_commands_terminal_or_rejected=True,
        probe=probe,rx=dict(size=rend,sha256=health.digest(rx[:rend])),
        tx=dict(size=tend,sha256=health.digest(tx[:tend]))),rend,tend


def qualify_one(io,*,ending,evidence,before_terminal,expected_ordinal):
    session=None;events=[]
    def wait(kind,seq):
        while not any((k,n)==(kind,seq) for k,n,_ in events):
            if time.monotonic()>=io.deadline:raise TimeoutError('resident checkpoint original deadline')
            events.extend(session.poll());time.sleep(.001)
    try:
        io.handshake()
        if io.preparation.info['authentication_ordinal']!=expected_ordinal:
            raise ValueError('resident authentication was already consumed outside this observation')
        session=protocol.Session(io.fd,io.key,bytes.fromhex(io.identity.run_id_hex),io.audit.nonce,Path(evidence),
            on_rx=io.capture,on_tx=io.audit.tx.extend,before_write=io.before_write)
        health.run_console_checks(session,events,deadline=min(io.deadline,time.monotonic()+29.9))
        # PID1 freezes the export immediately before EXEC. Allow two collector
        # samples and a matched frame before that freeze, within this session.
        settled=time.monotonic()+3
        while time.monotonic()<settled:
            if time.monotonic()>=io.deadline:raise TimeoutError('resident probe settle deadline')
            if io.before_write is not None:io.before_write()
            time.sleep(.05)
        wait(wire.EXIT,session.send(wire.EXEC,HUD_BODY))
        # Reject malformed/incomplete exports before a terminal intent. A valid
        # unavailable/stale observation remains a feature NO_PROOF, separately
        # from the authenticated terminal and exact Android return.
        probe_from_events(session,events)
        request=dict(run_id_hex=io.identity.run_id_hex,mode=ending,sequence=session.sequence,
            nonce_sha256=health.digest(io.audit.nonce),kernel_boot_identity_sha256=health.digest(io.audit.boot_id),
            resident_info=io.preparation.info)
        before_terminal(request)
        kind,ack=(protocol.DETACH,protocol.DETACH_ACK) if ending=='detach' else (wire.CONTROL,wire.CONTROL_ACK)
        remaining=io.deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('resident terminal admission expired')
        wait(ack,session.send(kind,timeout=min(2,remaining)))
        row,rend,tend=replay_one(io.codec,io.identity,io.key,bytes(io.audit.rx),bytes(io.audit.tx))
        if (rend,tend)!=(len(io.audit.rx),len(io.audit.tx)):raise ValueError('resident trailing checkpoint bytes')
        io.audit.done_seen=True;io.audit.current_stage=ending+'-accepted'
        return row
    finally:
        if session is not None:session.close()


class Observer(console.Observer):
    SESSION_COUNT=4
    QUALIFICATION_TIMEOUT_SEC=OBSERVATION_SECONDS
    PROOF_SCOPE='fixed-resident-health-and-thirty-minute-checkpoint-observation'

    def __init__(self,identity,control):
        super().__init__(identity,control);self.__file__=__file__
        self.SCHEMA='s22plus-fyg8-'+identity.namespace+'-resident-qualification-v1'
        self.CONTRACT_ID='s22plus-fyg8-'+identity.namespace+'-resident-observer-v1'
        self.PROOF_SCOPE=type(self).PROOF_SCOPE
        self.QUALIFICATION_COMMANDS=tuple(SimpleNamespace(ordinal=i*2+j+1,
            name='checkpoint-'+str(i+1)+'-'+name,command=command)
            for i in range(4) for j,(name,command) in enumerate((('health',health.COMMAND),('probe',HUD_COMMAND))))

    def IO(self,codec,key,**kwargs):return protocol.IO(codec,key,self.identity,**kwargs)

    def progress_projection(self,audit):
        return getattr(audit,'native_preparation',protocol.Progress(self.identity)).projection()

    @staticmethod
    def operator_plan_rows(proof):
        if type(proof.get('commands',[])) is not list:raise ValueError('resident command rows differ')
        return []

    def _joined(self,rows):
        if len(rows)!=4:raise ValueError('resident checkpoint count differs')
        if rows[0]['resident_info']['authentication_ordinal']!=1:raise ValueError('resident first authentication is not fresh')
        for before,after in zip(rows,rows[1:]):protocol.fresh_same_boot(before,after)
        if rows[-1]['ending']!='download':raise ValueError('resident final CONTROL missing')
        if any(not row['native_health_proved'] for row in rows):raise ValueError('resident health unproved')
        elapsed=[r['resident_info']['elapsed_ms']-rows[0]['resident_info']['elapsed_ms'] for r in rows]
        span_valid=all(value>=floor for value,floor in zip(elapsed,(0,600000,900000,MINIMUM_SPAN_MS)))
        probe_time_advancing=all(after['probe']['proc_boottime_ms']>before['probe']['proc_boottime_ms']
            for before,after in zip(rows,rows[1:]))
        fresh=all(row['probe']['fresh_system_and_gauge'] for row in rows)
        advancing=all(all(after['probe']['latest'][key]>before['probe']['latest'][key]
            for key in ('sequence','system_sequence','hardware_sequence','gauge_sequence'))
            for before,after in zip(rows,rows[1:])) if fresh else False
        past_sample_limit=bool(fresh and all(rows[-1]['probe']['latest'][key]>601
            for key in ('system_sequence','hardware_sequence','gauge_sequence')))
        last=rows[-1];commands=[dict(row,authentication=i+1) for i,s in enumerate(rows) for row in s['commands']]
        # Store each command once. Session indices join its two fixed commands
        # to the top-level table, keeping the existing bounded final result small.
        sessions=[dict({k:v for k,v in row.items() if k!='commands'},command_indices=[2*i,2*i+1])
            for i,row in enumerate(rows)]
        return dict(schema=self.SCHEMA,run_id_hex=self.RUN_ID_HEX,proved=fresh and advancing and past_sample_limit and span_valid and probe_time_advancing,
            sessions=sessions,session_count=4,command_count=8,request_count=16,commands=commands,
            preparation=rows[0]['preparation'],root_ready=last['root_ready'],nonce_sha256=last['nonce_sha256'],
            kernel_boot_identity_sha256=last['kernel_boot_identity_sha256'],control_sequence=6,
            control_acceptance_observed=True,control_ack_scope='acceptance-only',same_tty_fd=False,
            physical_reopen_count=3,console_reentry=True,all_commands_terminal_or_rejected=True,
            qualified_command_count=8,native_health_proved=True,signed_checkpoint_elapsed_ms=elapsed,
            signed_span_valid=span_valid,probe_time_advancing=probe_time_advancing,
            fresh_system_and_gauge=fresh,advancing_samples=advancing,past_sample_limit=past_sample_limit,source_profile=source.profile_contract(),
            continuous_liveness='UNPROVED',physical_visibility='UNPROVED',automatic_recovery='UNPROVED')

    def replay_session(self,codec,rx,tx,key,*,partial=False):
        if type(rx) is not bytes or type(tx) is not bytes or len(rx)>self.RAW_MAXIMUM or len(tx)>65536:
            raise ValueError('resident combined raw bound differs')
        rows=[];ro=to=0
        for _ in range(4):
            row,rn,tn=replay_one(codec,self.identity,key,rx[ro:],tx[to:])
            row['rx']['offset']=ro;row['tx']['offset']=to;rows.append(row);ro+=rn;to+=tn
        if (ro,to)!=(len(rx),len(tx)):raise ValueError('resident combined trailing bytes')
        value=self._joined(rows)
        if not partial:self.validate_qualification(value)
        return value

    def validate_qualification(self,value):
        try:
            rows=[]
            if len(value['commands'])!=8:raise ValueError('resident fixed command table differs')
            for i,session in enumerate(value['sessions']):
                if session['command_indices']!=[2*i,2*i+1] or 'commands' in session:
                    raise ValueError('resident command table indices differ')
                commands=[value['commands'][j] for j in session['command_indices']]
                if any(type(row['authentication']) is not int or row['authentication']!=i+1 for row in commands):
                    raise ValueError('resident command authentication join differs')
                rows.append(dict({k:v for k,v in session.items() if k!='command_indices'},
                    commands=[{k:v for k,v in row.items() if k!='authentication'} for row in commands]))
            expected=self._joined(rows)
            if expected['proved'] is not True or json.dumps(value,sort_keys=True,allow_nan=False)!=json.dumps(expected,sort_keys=True,allow_nan=False):
                raise ValueError('resident qualification projection differs')
        except (KeyError,ValueError,TypeError) as exc:raise console.QualificationError('resident qualification differs') from exc
        return copy.deepcopy(value)

    def qualify(self,codec,descriptor,auth_key,expected_boot_sha256,seen_nonces,writer,*,deadline,
                before_control,evidence,interactive=None,before_detach=None,reopen=None,before_auth=None,before_write=None):
        if expected_boot_sha256 is not None or seen_nonces or not all(callable(v) for v in (before_detach,reopen,before_auth,before_write)):
            raise console.QualificationError('resident exact checkpoint owner missing')
        if not time.monotonic()<deadline<=time.monotonic()+OBSERVATION_SECONDS:
            raise console.QualificationError('resident original observation budget differs')
        Path(evidence).mkdir(mode=0o700,parents=False,exist_ok=False)
        current=descriptor;sessions=[];rows=[];io=None;complete_proof=None
        def terminal(request):
            if rows:protocol.fresh_same_boot(rows[-1],request)
            if request['mode']=='detach':before_detach(request)
            else:before_control({**{k:v for k,v in request.items() if k!='resident_info'},
                'boot_id_semantic':self.control.BOOT_ID_SEMANTIC,'boot_receipt_semantic':self.control.BOOT_RECEIPT_SEMANTIC})
        try:
            if interactive is not None:interactive(None,[],deadline)
            for index in range(4):
                before_auth(index+1)
                io=self.IO(codec,auth_key,fd=current,writer=writer,deadline=min(deadline,time.monotonic()+SESSION_SECONDS),before_write=before_write)
                row=qualify_one(io,ending='download' if index==3 else 'detach',
                    evidence=Path(evidence)/('auth-'+str(index+1)),before_terminal=terminal,expected_ordinal=index+1)
                if rows:protocol.fresh_same_boot(rows[-1],row)
                rows.append(row);sessions.append(SimpleNamespace(session=SimpleNamespace(audit=io.audit)))
                seen_nonces.add(row['nonce_sha256'])
                if index<3:current=reopen(row,deadline,index+2)
            rx=b''.join(bytes(s.session.audit.rx) for s in sessions);tx=b''.join(bytes(s.session.audit.tx) for s in sessions)
            complete_proof=self.replay_session(codec,rx,tx,auth_key,partial=True)
            self.validate_qualification(complete_proof)
            return console.QualificationResult(complete_proof,tuple(sessions))
        except BaseException as exc:
            failed=io.audit if io is not None and not any(s.session.audit is io.audit for s in sessions) else None
            if failed is not None:failed.failure_stage=failed.current_stage
            error=console.QualificationError('resident checkpoints stopped; no replay',audit=failed,
                partial_receipt=complete_proof if complete_proof is not None else dict(schema=self.SCHEMA,run_id_hex=self.RUN_ID_HEX,proved=False,sessions=rows,
                    commands=[],session_count=len(sessions),preparation=rows[0]['preparation'] if rows else io.preparation.projection() if io else None,
                    failure_type=type(exc).__name__))
            error.completed_sessions=tuple(sessions);raise error from exc

    def audit_binding(self):
        return dict(schema=self.SCHEMA,contract_id=self.CONTRACT_ID,session_count=4,
            qualification_timeout_sec=OBSERVATION_SECONDS,checkpoint_seconds=list(CHECKPOINT_SECONDS),
            minimum_signed_span_ms=MINIMUM_SPAN_MS,root_console=True,qualified_exec_count=8,
            interactive_commands=False,physical_reopen_count=3,source_profile=source.profile_contract(),
            control_sequences=[6],detach_sequences=[6],control_ack_scope='acceptance-only',
            raw_replay_required=True,live_authorized=False)
