"""H0 research-shell exchange on an already-owned descriptor.

No endpoint selection, device CLI, approval, lease or candidate activation.
The eventual reviewed live owner must supply the private exact codec, raw
writer and current-boot binding. This module grants no device authority.
"""
from dataclasses import dataclass
import hashlib
import hmac
import math
import os
import re
import select
import struct
import time

FRAME_CANCEL = 5
FRAME_CANCEL_ACK = 0x88
FLAG_CANCELLED = 8
AUTH_DOMAIN_CANCEL = b'S22PLUS-FYG8-P345-AUTH-CANCEL-v1'
MAX_COMMAND = 1023
MAX_OUTPUT = 128 * 1024
SESSION_TIMEOUT_SEC = 30.0


def parent_identity_valid(output):
    """Numeric root IDs; optional NSS names are presentation only."""
    if type(output) is not bytes:
        return False
    name = rb"(?:\([^()\r\n]*\))?"
    return re.fullmatch(
        rb"uid=0" + name + rb" gid=0" + name
        + rb"(?: groups=[0-9]+" + name
        + rb"(?:,[0-9]+" + name + rb")*)?\n", output
    ) is not None


def command_bytes(command):
    if type(command) is str:
        command = command.encode('utf-8')
    if type(command) is not bytes or not 1 <= len(command) <= MAX_COMMAND:
        raise ValueError('shell command size/type differs')
    command.decode('utf-8')
    if any(x < 32 and x not in (9, 10) for x in command) or 127 in command:
        raise ValueError('shell command contains a control byte')
    return command


def cancel_tag(key, run_id, nonce):
    if type(key) is not bytes or len(key)!=32 or type(run_id) is not bytes or len(run_id)!=16:
        raise ValueError('cancel identity differs')
    if type(nonce) is not bytes or len(nonce)!=32 or not any(nonce):
        raise ValueError('cancel nonce differs')
    return hmac.new(key, AUTH_DOMAIN_CANCEL+run_id+nonce+struct.pack('<I',4),hashlib.sha256).digest()


def parse_exit(codec, payload, size):
    if len(payload)!=codec.EXIT.size or not 0<=size<=MAX_OUTPUT:
        raise codec.AuthObserverError('shell EXIT size differs')
    flags,code,signal,forwarded,duration=codec.EXIT.unpack(payload)
    if flags & ~15 or forwarded!=size or signal>127 or duration>0x7fffffffffffffff:
        raise codec.AuthObserverError('shell EXIT accounting differs')
    if (signal==0 and not 0<=code<=255) or (signal!=0 and code!=-1):
        raise codec.AuthObserverError('shell EXIT status differs')
    if flags & 1 and (signal!=9 or code!=-1):
        raise codec.AuthObserverError('shell timeout status differs')
    if bool(flags & 4)!=(code in (126,127)):
        raise codec.AuthObserverError('shell exec status differs')
    # TRUNCATED can also mean deadline-bounded descendant drain, below byte cap.
    return flags,code,signal,duration


@dataclass(frozen=True)
class ShellExchange:
    session: object
    outcome: str
    cancel_sent: bool
    cancel_ack: int | None


def exchange(observer, descriptor, key, command, expected_boot_sha, seen_nonces,
             writer, *, deadline, cancel_requested=lambda: False):
    """One id/arbitrary-readonly-shell/nonce session; no descriptor reopen/retry."""
    codec=observer._CODEC
    runtime=observer.runtime
    command=command_bytes(command)
    if (writer is None or type(deadline) not in (int,float)
            or not math.isfinite(deadline) or deadline<=time.monotonic()):
        raise ValueError('raw writer and live deadline required')
    # Keep the existing logical-session bound even when the qualification
    # owner supplies its larger outer observation deadline.
    deadline = min(deadline, time.monotonic() + SESSION_TIMEOUT_SEC)
    if type(seen_nonces) is not set:
        raise ValueError('mutable consumed nonce set required')
    if expected_boot_sha is not None and (
            type(expected_boot_sha) is not str or len(expected_boot_sha)!=64
            or any(c not in '0123456789abcdef' for c in expected_boot_sha)):
        raise ValueError('expected boot digest differs')
    if expected_boot_sha is None and seen_nonces:
        raise ValueError('initial boot binding requires an unused observation')
    key=codec._validate_key(key)
    run_id=runtime.P335_RUN_ID
    commands=(runtime.DEFAULT_COMMANDS[0],command,runtime.DEFAULT_COMMANDS[2])
    audit=observer.ExchangeAudit(auth_key_sha256=hashlib.sha256(key).hexdigest())
    cancel_sent=False
    cancel_ack=None

    def send(kind,seq,payload):
        codec._send(descriptor,kind,seq,payload,deadline,audit)

    def exact(size, cancellable=False):
        nonlocal cancel_sent
        value=bytearray()
        while len(value)<size:
            if time.monotonic()>=deadline:
                raise TimeoutError('shell exchange deadline expired')
            if cancellable and not cancel_sent and cancel_requested():
                send(FRAME_CANCEL,4,cancel_tag(key,run_id,audit.nonce))
                cancel_sent=True
            ready,_,_=select.select([descriptor],[],[],min(.05,max(0,deadline-time.monotonic())))
            if ready:
                try:chunk=os.read(descriptor,size-len(value))
                except BlockingIOError:continue
                if not chunk:raise codec.AuthObserverError('shell endpoint EOF')
                writer.write_stdout(chunk)
                audit.rx.extend(chunk)
                value.extend(chunk)
        return bytes(value)

    def frame(cancellable=False):
        header=exact(codec.HEADER.size,cancellable)
        length=codec.HEADER.unpack(header)[3]
        if length>runtime.MAX_FRAME_PAYLOAD:
            raise codec.AuthObserverError('shell frame exceeds bound')
        return codec.decode_frame(header+exact(length,cancellable))

    def expect(kind,seq):
        return codec._expect(frame(),kind,seq)

    try:
        audit.current_stage='open-write'
        send(runtime.FRAME_OPEN,0,run_id)
        audit.current_stage='banner-read'
        if exact(len(runtime.DEVICE_BANNER))!=runtime.DEVICE_BANNER:
            raise codec.AuthObserverError('shell banner differs')
        audit.banner_seen=True
        for stage in (0,runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,runtime.DIAGNOSTIC_STAGE_RNG):
            audit.current_stage='diagnostic-read'
            audit.diagnostics.append(observer._P333.parse_diagnostic_frame(frame(),stage))
        if audit.diagnostics[-1].code<0:
            raise codec.AuthObserverError('shell RNG failed')
        audit.rng_eagain_retries=audit.diagnostics[-1].code
        audit.current_stage='challenge-read'
        nonce=expect(runtime.FRAME_CHALLENGE,0)
        codec._validate_nonce(nonce)
        if hashlib.sha256(nonce).hexdigest() in seen_nonces:
            raise codec.AuthObserverError('shell nonce replay')
        seen_nonces.add(hashlib.sha256(nonce).hexdigest())
        audit.nonce=nonce; audit.challenge_seen=True
        send(runtime.FRAME_AUTH,1,observer.compute_open_tag(key,run_id,nonce))
        if not hmac.compare_digest(expect(runtime.FRAME_READY,1),observer.compute_ready_tag(key,run_id,nonce)):
            raise codec.AuthObserverError('shell READY differs')
        audit.ready_seen=True; audit.authenticated=True
        audit.current_stage='boot-id-read'
        boot=observer.decode_boot_id_frame(frame(),key,run_id,nonce)
        audit.boot_id=boot
        # Initial candidate qualification has no prior candidate boot nonce.
        # READY and this BOOT frame authenticate it before the first EXEC;
        # the owner must bind subsequent sessions to this exact digest.
        if expected_boot_sha is not None and hashlib.sha256(boot).hexdigest()!=expected_boot_sha:
            raise codec.AuthObserverError('shell boot changed before EXEC')
        results=[]
        for seq,cmd in enumerate(commands,3):
            audit.current_stage='exec-write'
            tag=hmac.new(key,runtime.AUTH_DOMAIN_EXEC+run_id+nonce+struct.pack('<I',seq)+cmd,hashlib.sha256).digest()
            send(runtime.FRAME_EXEC,seq,tag+cmd)
            output=bytearray()
            while True:
                audit.current_stage='exec-read'
                item=frame(cancellable=seq==4)
                if item.sequence!=seq:
                    raise codec.AuthObserverError('shell response sequence differs')
                if item.frame_type==runtime.FRAME_DATA:
                    if not item.payload or len(output)+len(item.payload)>MAX_OUTPUT:
                        raise codec.AuthObserverError('shell DATA bound differs')
                    output.extend(item.payload)
                    continue
                if item.frame_type!=runtime.FRAME_EXIT:
                    raise codec.AuthObserverError('shell response type differs')
                flags,code,signal,duration=parse_exit(codec,item.payload,len(output))
                if seq!=4 and (flags or code or signal):
                    raise codec.AuthObserverError('shell identity/nonce command failed')
                result=observer.CommandResult(seq,cmd,bytes(output),flags,code,signal,duration)
                results.append(result)
                if seq==4:
                    if cancel_sent:
                        audit.current_stage='cancel-ack-read'
                        payload=expect(FRAME_CANCEL_ACK,4)
                        if len(payload)!=4:raise codec.AuthObserverError('cancel ACK length differs')
                        cancel_ack=struct.unpack('<I',payload)[0]
                        if cancel_ack not in (0,1) or bool(flags&FLAG_CANCELLED)!=(cancel_ack==0):
                            raise codec.AuthObserverError('cancel ACK outcome differs')
                    elif flags&FLAG_CANCELLED:
                        raise codec.AuthObserverError('unsolicited cancellation')
                break
        if not parent_identity_valid(results[0].output):
            raise codec.AuthObserverError('parent identity witness differs')
        if results[2].output!=b'P328-NONCE '+run_id.hex().encode()+b'\n':
            raise codec.AuthObserverError('session nonce witness differs')
        audit.current_stage='close-write'
        send(runtime.FRAME_CLOSE,6,observer.compute_close_tag(key,run_id,nonce,6))
        audit.current_stage='done-read'
        payload=expect(runtime.FRAME_DONE,6)
        if len(payload)!=observer.DONE.size or observer.DONE.unpack(payload)[0]!=3:
            raise codec.AuthObserverError('shell DONE differs')
        audit.done_seen=True; audit.current_stage='complete'
        query=results[1]
        outcome=('cancelled' if query.flags&8 else 'timeout' if query.flags&1 else
                 'truncated' if query.flags&2 else 'exec-failed' if query.flags&4 else
                 'command-failed' if query.exit_code or query.term_signal else 'ok')
        return ShellExchange(observer.SessionResult(tuple(results),audit),outcome,cancel_sent,cancel_ack)
    except BaseException as exc:
        audit.failure_stage=audit.current_stage
        exc.audit=audit
        exc.cancel_sent=cancel_sent
        raise
