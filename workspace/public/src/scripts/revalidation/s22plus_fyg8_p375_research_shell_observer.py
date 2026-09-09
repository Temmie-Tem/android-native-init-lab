"""One authenticated root console on one owned descriptor, raw-first evidence.

Endpoint selection and rollback remain with the existing F1 owner. This module
never opens a device or retries a command/session. Optional attended interaction
runs through the same Session object after fixed qualification.
"""
from dataclasses import dataclass
from pathlib import Path
import copy
import hashlib
import hmac
import os
import select
import struct
import time
import types
import s22plus_fyg8_p375_research_shell_runtime as runtime
import s22plus_fyg8_p375_return_spec as control
import s22plus_fyg8_p375_progress as progress
import s22plus_root_console_v1 as wire

SCHEMA='s22plus-fyg8-p375-root-console-qualification-v1'
CONTRACT_ID='s22plus-fyg8-root-console-v1'
TARGET=runtime.TARGET
RUN_ID=runtime.P375_RUN_ID
RUN_ID_HEX=runtime.P375_RUN_ID_HEX
SESSION_COUNT=SAME_FD_SESSION_COUNT=TOTAL_SESSIONS=MAX_SESSIONS=MAX_INITIAL_SESSIONS=1
RECONNECT_COUNT=MAX_RECONNECTS=PHYSICAL_REOPEN_COUNT=IDLE_SECONDS=0
QUALIFICATION_TIMEOUT_SEC=600.0
PROOF_SCOPE='root-command-console-with-bounded-streams-and-authenticated-return-control'
RAW_MAXIMUM=wire.RAW_CAPTURE_MAXIMUM


@dataclass(frozen=True)
class QualificationStep:
    ordinal:int
    name:str
    command:bytes
    expected_stdout:bytes
    expected_stderr:bytes=b''
    expected_status:int=0


QUALIFICATION_COMMANDS=(
    QualificationStep(1,'numeric-root-and-real-trees',
        b"printf 'RC1_ROOT\\n'; /bin/busybox id -u; /bin/busybox id -g; /bin/busybox awk '/^PPid:/{print $2}' /proc/$$/status; test -r /proc/1/status && test -d /sys/devices && test -c /dev/null && printf 'REAL_TREES\\n'",
        b'RC1_ROOT\n0\n0\n1\nREAL_TREES\n'),
    QualificationStep(2,'ram-write',b"printf 'RAM\\000DATA\\n' > proof; printf 'RAM_WRITTEN\\n'",b'RAM_WRITTEN\n'),
    QualificationStep(3,'ram-read-binary-stderr-nonzero',
        b"/bin/busybox cat proof; printf 'ERR\\000DATA\\n' >&2; exit 7",b'RAM\0DATA\n',b'ERR\0DATA\n',7<<8),
    QualificationStep(4,'cancel-running-group',
        b"printf 'WAITING\\n'; while :; do /bin/busybox sleep 1; done",b'WAITING\n'),
    QualificationStep(5,'after-cancel-same-ram',
        b"test -f proof && printf 'AFTER_CANCEL\\n'",b'AFTER_CANCEL\n'),
)
TOTAL_COMMANDS=len(QUALIFICATION_COMMANDS) # EXEC count; STATUS/CANCEL/CONTROL are separate requests.


def identity(value):return dict(size=len(value),sha256=hashlib.sha256(value).hexdigest())


class QualificationError(ValueError):
    def __init__(self,message,*,audit=None,partial_receipt=None):
        super().__init__(message);self.failed_audit=audit;self.audit=audit
        self.completed_sessions=();self.partial_receipt=partial_receipt or dict(schema=SCHEMA,proved=False,sessions=[])


@dataclass(frozen=True)
class QualificationResult:
    receipt:dict
    sessions:tuple


class IO:
    def __init__(self,codec,key,*,fd=None,writer=None,deadline=None,rx=None,tx=None):
        self.codec,self.key=codec,key;self.fd,self.writer,self.deadline=fd,writer,deadline
        self.raw_rx,self.raw_tx=rx,tx;self.rpos=self.tpos=0
        self.audit=codec.ExchangeAudit(auth_key_sha256=hashlib.sha256(key).hexdigest())
        self.preparation=progress.Progress()
        self.audit.p375_preparation=self.preparation

    def read(self,size):
        if self.raw_rx is not None:
            part=self.raw_rx[self.rpos:self.rpos+size];self.rpos+=len(part);self.audit.rx.extend(part)
            if len(part)!=size:raise EOFError('partial retained RX')
            return part
        out=bytearray()
        while len(out)<size:
            left=self.deadline-time.monotonic()
            if left<=0:raise TimeoutError('original P375 observation deadline')
            ready,_,_=select.select([self.fd],[],[],min(.05,left))
            if not ready:continue
            try:part=os.read(self.fd,size-len(out))
            except (BlockingIOError,InterruptedError):continue
            if not part:raise EOFError('P375 transport closed')
            self.capture(part);out.extend(part)
        return bytes(out)

    def capture(self,part):
        self.writer.write_stdout(part);self.audit.rx.extend(part)

    def send(self,kind,seq,payload):
        if self.raw_tx is not None:
            encoded=self.codec._CODEC.encode_frame(kind,seq,payload)
            part=self.raw_tx[self.tpos:self.tpos+len(encoded)]
            self.tpos+=len(part);self.audit.tx.extend(part)
            if part!=encoded:raise ValueError('retained handshake TX differs')
        else:self.codec._CODEC._send(self.fd,kind,seq,payload,self.deadline,self.audit)

    def frame(self):
        head=self.read(16);size=self.codec._CODEC.HEADER.unpack(head)[3]
        if size>wire.MAX_PAYLOAD:raise ValueError('P375 frame too large')
        return self.codec._CODEC.decode_frame(head+self.read(size))

    def expect(self,kind,seq):return self.codec._CODEC._expect(self.frame(),kind,seq)

    def handshake(self):
        a=self.audit;c=self.codec
        a.current_stage='open-write';self.send(runtime.FRAME_OPEN,0,RUN_ID)
        a.current_stage='banner-read'
        if self.read(len(runtime.DEVICE_BANNER))!=runtime.DEVICE_BANNER:raise ValueError('P375 banner differs')
        a.banner_seen=True
        for stage in (0,runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,runtime.DIAGNOSTIC_STAGE_RNG):
            a.diagnostics.append(c._P333.parse_diagnostic_frame(self.frame(),stage))
        a.rng_eagain_retries=a.diagnostics[-1].code
        if not 0<=a.rng_eagain_retries<=64:raise ValueError('P375 RNG diagnostic differs')
        a.nonce=self.expect(runtime.FRAME_CHALLENGE,0);c._CODEC._validate_nonce(a.nonce);a.challenge_seen=True
        self.send(runtime.FRAME_AUTH,1,c.compute_open_tag(self.key,RUN_ID,a.nonce))
        if not hmac.compare_digest(self.expect(runtime.FRAME_READY,1),c.compute_ready_tag(self.key,RUN_ID,a.nonce)):
            raise ValueError('P375 AUTH READY differs')
        a.ready_seen=True;a.authenticated=True
        a.boot_id=c.decode_boot_id_frame(self.frame(),self.key,RUN_ID,a.nonce)
        a.current_stage='root-preparation'
        while not self.preparation.ready():
            self.preparation.accept(self.frame(),self.key,a.nonce)
            if self.preparation.failure:
                # The native path joins the first failing RETURN with one
                # authenticated terminal record.  Preserve that record before
                # classifying the preparation as failed so the retained raw
                # stream proves both the cause and the native stop boundary.
                while self.preparation.records[-1]['event']!=4:
                    self.preparation.accept(self.frame(),self.key,a.nonce)
                raise ValueError('P375 native preparation failed')
        a.current_stage='root-console'


def _snapshot(session,events):
    commands=[]
    for seq,kind in session.requests.items():
        if kind!=wire.EXEC:continue
        body=session.request_bodies[seq];timeout_ms,cwd_size=struct.unpack('<IH',body[:6])
        streams={stream:b''.join(payload[12:] for k,n,payload in events
                                if k==wire.OUTPUT and n==seq and struct.unpack('<I',payload[8:12])[0]==stream)
                 for stream in (1,2)}
        terminal=next((struct.unpack('<7I',p) for k,n,p in events if k==wire.EXIT and n==seq),None)
        commands.append(dict(sequence=seq,timeout_ms=timeout_ms,command=identity(body[6+cwd_size:]),
            cwd=identity(body[6:6+cwd_size]),accepted=seq in session.accepted,rejected=seq in session.rejected,
            stdout=identity(streams[1]),stderr=identity(streams[2]),
            terminal=list(terminal) if terminal is not None else None))
    return commands


def _qualified_step(row,step,events):
    terminal=row['terminal']
    if (not row['accepted'] or row['rejected'] or terminal is None
            or row['command']!=identity(step.command)
            or row['cwd']!=identity(b'/s22-root-work') or row['timeout_ms']!=15000):
        return False
    if row['stdout']!=identity(step.expected_stdout) or row['stderr']!=identity(step.expected_stderr):return False
    _,flags,status,error,_,dropped,_=terminal
    if error or dropped:return False
    if step.ordinal==4:
        if flags!=1 or status not in (15,9):return False
        statuses=[p for k,n,p in events if k==wire.STATUS_REPLY and struct.unpack('<I',p[:4])[0]==row['sequence']]
        cancels=[p for k,n,p in events if k==wire.ACK and n!=row['sequence'] and struct.unpack('<II',p[:8])==(row['sequence'],0) and struct.unpack('<I',p[16:20])[0]&1]
        return len(statuses)==1 and struct.unpack('<I',statuses[0][8:12])[0]==1 and len(cancels)==1
    return not flags and status==step.expected_status


def _qualification(commands,events):
    return (len(commands)>=len(QUALIFICATION_COMMANDS)
        and all(_qualified_step(row,step,events)
            for row,step in zip(commands,QUALIFICATION_COMMANDS)))


def _receipt(io,session,events):
    rows=_snapshot(session,events)
    control_ack=next((n for k,n,p in events if k==wire.CONTROL_ACK),None)
    closed=all(row['rejected'] or row['terminal'] is not None for row in rows)
    proved=bool(_qualification(rows,events) and io.preparation.ready() and session.ready is not None
                and session.ready[-2:]==(0,0) and control_ack is not None and closed and not session.faulted)
    a=io.audit
    value=dict(schema=SCHEMA,proved=proved,run_id_hex=RUN_ID_HEX,session_count=1,
        command_count=len(rows),request_count=len(session.requests),commands=rows,
        preparation=io.preparation.projection(),root_ready=list(session.ready) if session.ready else None,
        nonce_sha256=hashlib.sha256(a.nonce).hexdigest(),kernel_boot_identity_sha256=hashlib.sha256(a.boot_id).hexdigest(),
        control_sequence=control_ack,control_acceptance_observed=control_ack is not None,
        control_ack_scope='acceptance-only',same_tty_fd=True,physical_reopen_count=0,
        all_commands_terminal_or_rejected=closed,console_reentry=False,
        qualified_command_count=len(QUALIFICATION_COMMANDS) if _qualification(rows,events) else 0,
        qualification_events=[dict(kind=k,sequence=n,payload_hex=p.hex()) for k,n,p in events
                              if (k,n) in ((wire.STATUS_REPLY,7),(wire.ACK,8))],
        sessions=[dict(ordinal=1,rx=identity(bytes(a.rx)),tx=identity(bytes(a.tx)))])
    return value


def validate_qualification(value):
    if type(value) is not dict or value.get('schema')!=SCHEMA or value.get('proved') is not True:
        raise QualificationError('root-console qualification is unproved')
    if value.get('run_id_hex')!=RUN_ID_HEX or value.get('session_count')!=1 or value.get('qualified_command_count')!=5:
        raise QualificationError('root-console identity/count differs')
    if value.get('root_ready')!=[1,600000,300000,1048576,767,255,0,0] or value.get('control_acceptance_observed') is not True:
        raise QualificationError('root-console READY/CONTROL differs')
    if value.get('same_tty_fd') is not True or value.get('physical_reopen_count')!=0 or value.get('console_reentry') is not False or value.get('all_commands_terminal_or_rejected') is not True:
        raise QualificationError('root-console continuity/closure differs')
    expected_events=[dict(kind=wire.STATUS_REPLY,sequence=7,payload_hex=struct.pack('<8I',6,0,1,0,0,8,0,5).hex()),
                     dict(kind=wire.ACK,sequence=8,payload_hex=struct.pack('<8I',6,0,1,0,1,8,0,5).hex())]
    if value.get('qualification_events')!=expected_events:raise QualificationError('fixed STATUS/CANCEL witnesses differ')
    rows=value.get('commands')
    if type(rows) is not list or type(value.get('command_count')) is not int or len(rows)!=value['command_count'] or len(rows)<5:
        raise QualificationError('root command rows/count differ')
    if [row.get('sequence') for row in rows[:5]]!=[3,4,5,6,9]:raise QualificationError('fixed command sequence differs')
    events=[(row['kind'],row['sequence'],bytes.fromhex(row['payload_hex'])) for row in expected_events]
    try:valid=_qualification(rows,events)
    except (KeyError,ValueError,TypeError,IndexError):valid=False
    if not valid:raise QualificationError('fixed root command evidence differs')
    if type(value.get('request_count')) is not int or value['request_count']<8 or value.get('control_sequence')!=value['request_count']+2:
        raise QualificationError('request/CONTROL sequence differs')
    if value.get('control_ack_scope')!='acceptance-only':raise QualificationError('CONTROL scope differs')
    expected_preparation=[dict(stage=stage,event=event,code=0) for stage,event in progress.EXPECTED]
    if value.get('preparation')!=dict(schema='s22plus-fyg8-p375-preparation-progress-v1',records=expected_preparation,failure=None,complete=True):
        raise QualificationError('root preparation proof differs')
    return copy.deepcopy(value)


def qualify(codec,descriptor,auth_key,expected_boot_sha256,seen_nonces,writer,*,deadline,
            before_control,evidence,interactive=None):
    if expected_boot_sha256 is not None or seen_nonces or not time.monotonic()<deadline<=time.monotonic()+QUALIFICATION_TIMEOUT_SEC:
        raise QualificationError('P375 fresh session inputs differ')
    io=IO(codec,auth_key,fd=descriptor,writer=writer,deadline=deadline);session=None;events=[]
    try:
        io.handshake();seen_nonces.add(hashlib.sha256(io.audit.nonce).hexdigest())
        session=wire.Session(descriptor,auth_key,RUN_ID,io.audit.nonce,Path(evidence),
            on_rx=io.capture,on_tx=io.audit.tx.extend)
        def wait(kinds,seq):
            if type(kinds) is int:kinds=(kinds,)
            while time.monotonic()<deadline:
                for k,n,p in events:
                    if n==seq and k in kinds:return k,p
                events.extend(session.poll());time.sleep(.001)
            raise TimeoutError('P375 original session deadline')
        wait(wire.READY,2)
        if session.ready[-2:]!=(0,0):raise ValueError('native effective credentials are not root')
        for step in QUALIFICATION_COMMANDS:
            seq=session.send(wire.EXEC,wire.command(step.command,cwd=b'/s22-root-work'))
            kind,_=wait((wire.ACK,wire.EXIT),seq)
            if kind==wire.EXIT:break
            ack=next(p for k,n,p in events if (k,n)==(wire.ACK,seq))
            if struct.unpack('<8I',ack)[1]!=0:break
            if step.ordinal==4:
                while not any(k in (wire.OUTPUT,wire.EXIT) and n==seq for k,n,p in events):
                    if time.monotonic()>=deadline:raise TimeoutError('cancel witness deadline')
                    events.extend(session.poll());time.sleep(.001)
                if not any(k==wire.EXIT and n==seq for k,n,p in events):
                    status=session.send(wire.STATUS);wait(wire.STATUS_REPLY,status)
                    cancel=session.send(wire.CANCEL,struct.pack('<I',seq));wait(wire.ACK,cancel)
            wait(wire.EXIT,seq)
            rows=_snapshot(session,events)
            if not _qualified_step(rows[-1],step,events):break
        qualified=_qualification(_snapshot(session,events),events)
        if qualified and interactive is not None:interactive(session,events,deadline)
        request=dict(run_id_hex=RUN_ID_HEX,mode='download',sequence=session.sequence,
            nonce_sha256=hashlib.sha256(io.audit.nonce).hexdigest(),
            kernel_boot_identity_sha256=hashlib.sha256(io.audit.boot_id).hexdigest(),
            boot_id_semantic=control.BOOT_ID_SEMANTIC,boot_receipt_semantic=control.BOOT_RECEIPT_SEMANTIC)
        before_control(request)
        seq=session.send(wire.CONTROL);wait(wire.CONTROL_ACK,seq)
        io.audit.done_seen=True;io.audit.current_stage='control-accepted'
        value=_receipt(io,session,events);validate_qualification(value)
        shell=types.SimpleNamespace(session=types.SimpleNamespace(audit=io.audit))
        return QualificationResult(value,(shell,))
    except BaseException as exc:
        io.audit.failure_stage=io.audit.current_stage
        partial=_receipt(io,session,events) if session is not None else dict(schema=SCHEMA,proved=False,sessions=[],preparation=io.preparation.projection())
        partial['proved']=False
        raise QualificationError('P375 root console stopped; no replay',audit=io.audit,partial_receipt=partial) from exc
    finally:
        if session is not None:session.close()


def audit_binding():
    return dict(schema=SCHEMA,contract_id=CONTRACT_ID,session_count=1,
        same_fd_session_count=1,reconnect_count=0,qualification_timeout_sec=QUALIFICATION_TIMEOUT_SEC,
        root_console=True,qualified_exec_count=5,interactive_commands=True,
        control_ack_scope='acceptance-only',raw_replay_required=True,live_authorized=False)


def replay_session(codec,rx,tx,key,*,partial=False):
    io=IO(codec,key,rx=rx,tx=tx)
    io.handshake()
    state,events=wire.replay(key,RUN_ID,io.audit.nonce,rx[io.rpos:],tx[io.tpos:])
    io.audit.rx.extend(rx[io.rpos:]);io.audit.tx.extend(tx[io.tpos:])
    value=_receipt(io,state,events)
    if not partial:validate_qualification(value)
    return value


def progress_projection(audit):
    owner=getattr(audit,"p375_preparation",None)
    if owner is None:
        return dict(schema="s22plus-fyg8-p375-preparation-progress-v1",
                    records=[],failure=None,complete=False)
    return owner.projection()


def replay_progress(codec,rx,tx,key):
    io=IO(codec,key,rx=rx,tx=tx)
    try:
        io.handshake()
    except (ValueError,EOFError):
        pass
    return io.preparation.projection()


def parse_captured_session(codec,rx,tx,key,*args,**kwargs):
    return replay_session(codec,rx,tx,key)
