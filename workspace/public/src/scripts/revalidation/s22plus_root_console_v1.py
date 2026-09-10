"""Root-console wire codec and single-transport host session; no device opener.

The F1 owner supplies an authenticated, exact-bound nonblocking descriptor and
nonce. This module cannot flash, discover devices, reconnect, or renew grants.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
from pathlib import Path
import struct
import time
import zlib

EXEC, STATUS, CANCEL, CONTROL = range(32, 36)
ACK, OUTPUT, EXIT, STATUS_REPLY, CONTROL_ACK = range(160, 165)
FAULT = 165
READY = 166
DOMAIN = b'S22PLUS-FYG8-ROOT-CONSOLE-v1'
MAX_PAYLOAD = 1055
RAW_CAPTURE_MAXIMUM = 80 * 1024 * 1024
# The outer capture also contains the authenticated OPEN/preparation prefix.
SESSION_RX_LIMIT = RAW_CAPTURE_MAXIMUM - 64 * 1024
OUTPUT_LIMIT = 1024 * 1024
OUTPUT_CHUNK = 768
OUTPUT_FRAME_LIMIT = 2048
MAX_COMMAND_RX_BYTES = (OUTPUT_LIMIT
    + OUTPUT_FRAME_LIMIT * (16 + 12 + 32)
    + 80 + 76 + 72)
CONTROL_RX_RESERVE_BYTES = 80


def tag(key: bytes, run_id: bytes, nonce: bytes, sequence: int,
        kind: int, body: bytes) -> bytes:
    # Matches the existing p328_hmac_message include-sequence encoding.
    if len(key) != 32 or len(run_id) != 16 or len(nonce) != 32:
        raise ValueError('invalid session identity sizes')
    return hmac.digest(key, DOMAIN + run_id + nonce + struct.pack('<I', sequence)
                       + bytes([kind]) + body, 'sha256')


def frame(key: bytes, run_id: bytes, nonce: bytes, sequence: int,
          kind: int, body: bytes = b'') -> bytes:
    payload = body + tag(key, run_id, nonce, sequence, kind, body)
    if len(payload) > MAX_PAYLOAD:
        raise ValueError('payload too large')
    head = struct.pack('<4sBBHI', b'S328', 1, kind, len(payload), sequence)
    return head + struct.pack('<I', zlib.crc32(head + payload)) + payload


def command(command: bytes, *, cwd: bytes = b'/', timeout_ms: int = 15000) -> bytes:
    if not isinstance(command, bytes) or not 1 <= len(command) <= 767 or b'\0' in command:
        raise ValueError('command must be 1..767 non-NUL bytes')
    if not isinstance(cwd, bytes) or not cwd.startswith(b'/') or len(cwd) > 255 or b'\0' in cwd:
        raise ValueError('cwd must be an absolute non-NUL path of at most 255 bytes')
    if type(timeout_ms) is not int or not 1 <= timeout_ms <= 300000:
        raise ValueError('timeout outside finite command budget')
    body = struct.pack('<IH', timeout_ms, len(cwd)) + cwd + command
    if len(body) + 32 > MAX_PAYLOAD:
        raise ValueError('combined command and cwd exceed wire budget')
    return body


def validate_request(kind: int, body: bytes):
    if kind not in (EXEC, STATUS, CANCEL, CONTROL):raise ValueError('unknown request')
    if kind in (STATUS, CONTROL) and body:raise ValueError('unexpected request body')
    if kind == CANCEL and (len(body)!=4 or not struct.unpack('<I',body)[0]):
        raise ValueError('CANCEL requires a nonzero command identity')
    if kind == EXEC:
        if len(body)<8:raise ValueError('invalid EXEC body')
        budget, cwd_size=struct.unpack('<IH',body[:6])
        if command(body[6+cwd_size:],cwd=body[6:6+cwd_size],timeout_ms=budget)!=body:
            raise ValueError('noncanonical EXEC body')


class ProtocolError(ValueError):
    pass


class Decoder:
    def __init__(self, key: bytes, run_id: bytes, nonce: bytes):
        self.key, self.run_id, self.nonce = key, run_id, nonce
        self.pending = bytearray()

    def feed(self, data: bytes) -> list[tuple[int, int, bytes]]:
        self.pending.extend(data)
        frames = []
        while len(self.pending) >= 16:
            magic, version, kind, size, seq, crc = struct.unpack('<4sBBHII', self.pending[:16])
            if magic != b'S328' or version != 1 or not 32 <= size <= MAX_PAYLOAD:
                raise ProtocolError('invalid frame header')
            if len(self.pending) < 16 + size:
                break
            raw = bytes(self.pending[:16+size]);del self.pending[:16+size]
            payload = raw[16:];body, signature = payload[:-32], payload[-32:]
            if zlib.crc32(raw[:12] + payload) != crc:
                raise ProtocolError('frame CRC mismatch')
            if not hmac.compare_digest(signature, tag(self.key, self.run_id, self.nonce, seq, kind, body)):
                raise ProtocolError('frame authentication mismatch')
            frames.append((kind, seq, body))
        return frames


class Session:
    """Fresh private evidence directory; fsync intent before first request byte.

    poll() returns authenticated wire facts. Command stdout is never interpreted
    as PID1 evidence. Any I/O/protocol exception stops further sends. The enclosing
    F1 owner retains journal-bound rollback; no retry/reopen method exists here.
    """
    def __init__(self, fd: int, key: bytes, run_id: bytes, nonce: bytes, evidence: Path,
                 *, on_rx=lambda data: None, on_tx=lambda data: None, before_write=None):
        if os.get_blocking(fd):
            raise ValueError('owner must supply a nonblocking transport')
        self.fd, self.key, self.run_id, self.nonce = fd, key, run_id, nonce
        self.on_rx,self.on_tx=on_rx,on_tx
        self.before_write=before_write
        self.decoder = Decoder(key, run_id, nonce)
        self.evidence = Path(evidence)
        self.evidence.mkdir(mode=0o700, parents=False, exist_ok=False)
        parent = os.open(self.evidence.parent, os.O_DIRECTORY)
        try:os.fsync(parent)
        finally:os.close(parent)
        self.journal = os.open(self.evidence/'journal.jsonl', os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        self.rx = os.open(self.evidence/'rx.bin', os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        self.tx = os.open(self.evidence/'tx.bin', os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        self.sequence = 3
        self.stopped = False
        self.requests: dict[int, int] = {}
        self.request_bodies: dict[int, bytes] = {}
        self.responses: set[int] = set()
        self.accepted: set[int] = set()
        self.rejected: set[int] = set()
        self.pending: int | None = None
        self.control_sequence: int | None = None
        self.faulted = False
        self.finished = False
        self.ready: tuple[int, ...] | None = None
        self.outputs: dict[int, tuple[int, int]] = {}
        self.terminals: set[int] = set()
        self.raw_count = 0
        self._record(dict(event='session', run_id_sha256=hashlib.sha256(run_id).hexdigest(),
                          nonce_sha256=hashlib.sha256(nonce).hexdigest()))
        directory = os.open(self.evidence, os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)

    @staticmethod
    def _write(fd: int, data: bytes):
        while data:
            n = os.write(fd, data)
            if n <= 0:raise OSError('short evidence write')
            data = data[n:]

    def _record(self, value: dict):
        self._write(self.journal, (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode())
        os.fsync(self.journal)

    _validate_request = staticmethod(validate_request)

    @staticmethod
    def _terminal_request(kind: int) -> bool:
        return kind == CONTROL

    def send(self, kind: int, body: bytes = b'', *, timeout: float = 2) -> int:
        if self.stopped:raise ProtocolError('session stopped; replay forbidden')
        if self.ready is None:raise ProtocolError('native READY not observed')
        self._validate_request(kind,body)
        if self.control_sequence is not None:raise ProtocolError('CONTROL already submitted')
        if kind != CONTROL and (self.pending is not None or self.faulted):
            raise ProtocolError('normal request window unavailable')
        seq = self.sequence
        if seq >= 0xffffffff:raise ProtocolError('request sequence exhausted')
        wire = frame(self.key, self.run_id, self.nonce, seq, kind, body)
        try:
            # Full private command bytes precede durable intent and transmission.
            path = self.evidence/f'request-{seq}.bin'
            file = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
            try:self._write(file, body);os.fsync(file)
            finally:os.close(file)
            directory=os.open(self.evidence, os.O_DIRECTORY)
            try:os.fsync(directory)
            finally:os.close(directory)
            self._record(dict(event='intent', sequence=seq, kind=kind,
                              body_sha256=hashlib.sha256(body).hexdigest()))
            self.sequence += 1;self.requests[seq] = kind;self.request_bodies[seq] = body
            if self._terminal_request(kind):self.control_sequence=seq
            else:self.pending=seq
            offset = 0;deadline = time.monotonic()+timeout
            while offset < len(wire):
                if time.monotonic() >= deadline:raise TimeoutError('request delivery uncertain')
                if self.before_write is not None:self.before_write()
                try:n=os.write(self.fd, wire[offset:])
                except (BlockingIOError, InterruptedError):time.sleep(.001);continue
                if n <= 0:raise OSError('request delivery failed')
                self._write(self.tx, wire[offset:offset+n]);os.fsync(self.tx)
                self.on_tx(wire[offset:offset+n]);offset += n
            self._record(dict(event='sent', sequence=seq))
            return seq
        except BaseException:
            self.stopped=True
            raise

    def poll(self) -> list[tuple[int, int, bytes]]:
        if self.stopped:raise ProtocolError('session stopped')
        try:
            try:data=os.read(self.fd, 4096)
            except (BlockingIOError, InterruptedError):return []
            if not data:raise EOFError('transport closed; no reconnect')
            if self.raw_count + len(data) > SESSION_RX_LIMIT:raise ProtocolError('session capture limit exceeded')
            self._write(self.rx, data);os.fsync(self.rx);self.raw_count += len(data)
            self.on_rx(data)
            values=self.decoder.feed(data)
            for kind, seq, body in values:self._validate(kind,seq,body)
            if self.finished and self.decoder.pending:raise ProtocolError('trailing bytes after CONTROL ACK')
            return values
        except BaseException:
            self.stopped=True
            raise

    def _validate(self, kind: int, seq: int, body: bytes):
        if self.finished:raise ProtocolError('response after CONTROL ACK')
        if kind == READY:
            if self.ready is not None or seq!=2 or len(body)!=32:
                raise ProtocolError('duplicate or invalid native READY')
            fields=struct.unpack('<8I',body)
            if fields[:6]!=(1,600000,300000,1048576,767,255):
                raise ProtocolError('native resource profile differs')
            self.ready=fields
            self._record(dict(event='ready',fields=list(fields)))
            return
        if self.ready is None:raise ProtocolError('response before native READY')
        request = self.requests.get(seq)
        if request is None:raise ProtocolError('response has no durable request')
        if kind == OUTPUT:
            if request != EXEC or len(body) < 13 or seq in self.terminals or seq not in self.accepted:
                raise ProtocolError('output outside command lifecycle')
            identity, ordinal, stream = struct.unpack('<III', body[:12])
            old, total = self.outputs.get(seq, (0, 0))
            if identity != seq or ordinal != old+1 or stream not in (1,2):
                raise ProtocolError('output identity/order/stream mismatch')
            if ordinal > OUTPUT_FRAME_LIMIT:raise ProtocolError('command output frame bound exceeded')
            total += len(body)-12
            if total > 1048576:raise ProtocolError('command output bound exceeded')
            self.outputs[seq]=(ordinal,total)
        elif kind == EXIT:
            if request != EXEC or len(body)!=28 or seq in self.terminals or seq in self.rejected:
                raise ProtocolError('duplicate or invalid terminal')
            identity, flags, status, error, total, dropped, ordinal=struct.unpack('<7I',body)
            signed_error=struct.unpack('<i',struct.pack('<I',error))[0]
            if identity!=seq or (ordinal,total)!=self.outputs.get(seq,(0,0)):
                raise ProtocolError('terminal/output mismatch')
            if flags & ~511 or (bool(flags&16) != (signed_error<0)) or signed_error>0:
                raise ProtocolError('invalid terminal flags or exec errno')
            if bool(dropped) != bool(flags&4):raise ProtocolError('truncation/count mismatch')
            if flags&64:
                if status or not flags&8:raise ProtocolError('unavailable wait status has a value')
            elif status&0xffff0000 or (status&0x7f)==0x7f or (status&0x7f and status&0xff00):
                raise ProtocolError('invalid terminal wait status')
            if flags&256 and (error or not flags&8):raise ProtocolError('invalid unknown exec state')
            if flags&32 and (self.control_sequence is None or not flags&8 or not flags&128):
                raise ProtocolError('unjoined CONTROL interruption')
            if seq not in self.accepted:
                if flags!=16 or status or total or dropped or ordinal:
                    raise ProtocolError('terminal without accepted EXEC or pre-spawn failure')
                if seq in self.responses:raise ProtocolError('duplicate EXEC response')
                self.responses.add(seq)
                if self.pending==seq:self.pending=None
            self.terminals.add(seq)
            self._record(dict(event='terminal',sequence=seq,flags=flags,wait_status=status,
                              wait_status_available=not bool(flags&64),exec_state_available=not bool(flags&256),
                              exec_errno=signed_error,
                              output_bytes=total,dropped_bytes=dropped,output_frames=ordinal))
        elif kind in (ACK,STATUS_REPLY,CONTROL_ACK):
            expected={EXEC:ACK,CANCEL:ACK,STATUS:STATUS_REPLY,CONTROL:CONTROL_ACK}[request]
            if kind!=expected or len(body)!=32:raise ProtocolError('unexpected acknowledgement')
            if seq in self.responses:raise ProtocolError('duplicate acknowledgement')
            identity, disposition, active, blocked, flags, total, dropped, last=struct.unpack('<8I',body)
            if active not in (0,1) or blocked not in (0,1) or flags&~511 or total>1048576:
                raise ProtocolError('invalid supervisor state fields')
            if identity and self.requests.get(identity)!=EXEC:raise ProtocolError('unknown current command')
            if last and last not in self.terminals:raise ProtocolError('unobserved last terminal')
            if active and ((identity not in self.accepted or identity in self.terminals) and not (request==EXEC and identity==seq)):
                raise ProtocolError('active command was not accepted')
            if request==EXEC:
                if disposition==0:
                    if identity!=seq or not active or blocked or flags or total or dropped:
                        raise ProtocolError('invalid EXEC acceptance')
                    if self.accepted-self.terminals:raise ProtocolError('overlapping accepted commands')
                    self.accepted.add(seq)
                elif disposition==1:
                    if not (active or blocked) or identity==seq:raise ProtocolError('invalid EXEC rejection')
                    self.rejected.add(seq)
                else:raise ProtocolError('invalid EXEC disposition')
            elif request==CANCEL:
                target=struct.unpack('<I',self.request_bodies[seq])[0]
                if disposition==0:
                    if target!=identity or not active or not flags&1:raise ProtocolError('invalid CANCEL acceptance')
                elif disposition==1:
                    if target!=last or target not in self.terminals:raise ProtocolError('invalid completed CANCEL')
                elif disposition==2:
                    if (target==identity and active) or target==last:raise ProtocolError('invalid stale CANCEL')
                else:raise ProtocolError('invalid CANCEL disposition')
            elif disposition or (request==CONTROL and (active or not blocked)):
                raise ProtocolError('invalid STATUS/CONTROL acknowledgement')
            if request==CONTROL:
                if self.accepted-self.terminals:raise ProtocolError('CONTROL lacks command terminal evidence')
                self.finished=True
            self.responses.add(seq)
            if self.pending==seq:self.pending=None
            self._record(dict(event='response',sequence=seq,kind=kind,fields=list(struct.unpack('<8I',body))))
        elif kind==FAULT:
            if len(body)!=8 or struct.unpack('<II',body)!=(seq,1) or self.faulted:
                raise ProtocolError('invalid overload fault')
            self.faulted=True
            self._record(dict(event='overload',sequence=seq,command_admission_closed=True))
        else:raise ProtocolError('unknown response type')

    def close(self):
        self.stopped=True
        for name in ('journal','rx','tx'):
            fd=getattr(self,name,-1)
            if fd>=0:os.close(fd);setattr(self,name,-1)


def replay(key: bytes, run_id: bytes, nonce: bytes, rx: bytes, tx: bytes, *, session_class=Session):
    """Re-derive lifecycle from complete authenticated root-console streams.

    This has no I/O and creates no evidence files. OPEN/AUTH and preparation
    must be validated by the enclosing owner before calling it.
    """
    requests=Decoder(key,run_id,nonce);responses=Decoder(key,run_id,nonce)
    outgoing=requests.feed(tx);incoming=responses.feed(rx)
    if requests.pending or responses.pending:raise ProtocolError('partial retained root frame')
    state=session_class.__new__(session_class)
    state.requests={};state.request_bodies={};state.responses=set();state.accepted=set()
    state.rejected=set();state.outputs={};state.terminals=set();state.pending=None
    state.control_sequence=None;state.faulted=False;state.finished=False;state.ready=None
    state.records=[];state._record=state.records.append
    expected=3
    for kind,seq,body in outgoing:
        if seq!=expected or state.control_sequence is not None:
            raise ProtocolError('retained request order or post-CONTROL request differs')
        state._validate_request(kind,body);expected+=1
        state.requests[seq]=kind;state.request_bodies[seq]=body
        if state._terminal_request(kind):state.control_sequence=seq
    for kind,seq,body in incoming:state._validate(kind,seq,body)
    if not state.finished:raise ProtocolError('retained CONTROL ACK absent')
    if any(seq not in state.responses and kind!=EXEC for seq,kind in state.requests.items()):
        raise ProtocolError('unanswered retained normal request')
    return state,incoming
