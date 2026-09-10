"""Bounded native clean-detach protocol on owner-supplied exact IO.

No endpoint discovery, reconnect, image selection or device authority lives
here. The owner supplies the descriptor and preserves its physical handoff.
"""
import hashlib
import hmac
import os
from pathlib import Path
import struct
import time
from types import SimpleNamespace

import s22plus_native_console_observer_v1 as console
import s22plus_native_baseline_health_v1 as health
import s22plus_local_display_observer_v1 as display
import s22plus_native_source_v1 as source
import s22plus_root_console_v1 as wire

DETACH, DETACH_ACK = 36, 167
INFO_FRAME, INFO_SEQUENCE = 140, 768
BOOT_LIMIT_MS, AUTH_LIMIT = 900000, 8
SCHEMA = 's22plus-native-baseline-protocol-v1'
CACHED_PROGRESS = ((64, 1), (60, 0), (60, 1), (61, 0), (61, 1), (62, 0), (62, 1))


def host_now_ns():
    """Host elapsed time includes suspend; unavailable clock fails closed."""
    value = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    if type(value) is not int or value <= 0: raise ValueError('host boot clock is invalid')
    return value


class Progress(console.Progress):
    def __init__(self, identity):
        super().__init__(identity)
        self.info = None

    def accept(self, frame, key, nonce):
        if self.info is None:
            payload = frame.payload
            if (frame.frame_type != INFO_FRAME or frame.sequence != INFO_SEQUENCE
                    or len(payload) != 64):
                raise ValueError('baseline authenticated lifetime frame differs')
            domain = ('S22PLUS-FYG8-'+self.identity.namespace.upper()+'-BASELINE-INFO-v1').encode()
            tag = hmac.digest(key, domain+bytes.fromhex(self.identity.run_id_hex)+nonce+
                             struct.pack('<I', INFO_SEQUENCE)+payload[:32], 'sha256')
            if not hmac.compare_digest(payload[32:], tag):
                raise ValueError('baseline lifetime authentication differs')
            version, ordinal, maximum, cached, elapsed, limit = struct.unpack('<4I2Q', payload[:32])
            if (version != 1 or not 1 <= ordinal <= AUTH_LIMIT or maximum != AUTH_LIMIT
                    or cached != int(ordinal > 1) or limit != BOOT_LIMIT_MS or not elapsed < limit):
                raise ValueError('baseline lifetime fields differ')
            self.info = dict(version=version, authentication_ordinal=ordinal,
                authentication_limit=maximum, preparation_cached=bool(cached),
                elapsed_ms=elapsed, limit_ms=limit)
            self.expected = CACHED_PROGRESS if cached else console.EXPECTED
            return
        super().accept(frame, key, nonce)

    def ready(self):
        return self.info is not None and super().ready()

    def projection(self):
        return dict(super().projection(), baseline_info=self.info)


class IO(console.IO):
    def __init__(self, *args, **kwargs):
        self.before_write = kwargs.pop('before_write', None)
        super().__init__(*args, **kwargs)
        self.preparation = Progress(self.identity)
        self.audit.native_preparation = self.preparation

    def send(self, kind, sequence, payload):
        if self.raw_tx is not None:
            return super().send(kind,sequence,payload)
        encoded = self.codec._CODEC.encode_frame(kind,sequence,payload)
        offset = 0
        while offset < len(encoded):
            if time.monotonic() >= self.deadline: raise TimeoutError('baseline original handshake deadline')
            if self.before_write is not None:self.before_write()
            try: count=os.write(self.fd,encoded[offset:])
            except (BlockingIOError,InterruptedError):time.sleep(.001);continue
            if count <= 0:raise OSError('baseline handshake delivery uncertain')
            self.audit.tx.extend(encoded[offset:offset+count]);offset += count


class Session(wire.Session):
    @staticmethod
    def _validate_request(kind, body):
        if kind == DETACH:
            if body: raise ValueError('DETACH has no payload')
        else:
            wire.validate_request(kind, body)

    @staticmethod
    def _terminal_request(kind):
        return kind in (wire.CONTROL, DETACH)

    def send(self, kind, body=b'', *, timeout=2):
        if kind == DETACH and (self.pending is not None or self.faulted
                or self.accepted-self.terminals or self.decoder.pending):
            raise wire.ProtocolError('DETACH requires a complete idle session')
        return super().send(kind, body, timeout=timeout)

    def _validate(self, kind, seq, body):
        if kind != DETACH_ACK:
            return super()._validate(kind, seq, body)
        if (self.finished or self.ready is None or self.requests.get(seq) != DETACH
                or seq != self.control_sequence or seq in self.responses or len(body) != 32
                or self.faulted or self.accepted-self.terminals):
            raise wire.ProtocolError('unjoined clean DETACH acknowledgement')
        identity, disposition, active, blocked, flags, total, dropped, last = struct.unpack('<8I', body)
        if ((disposition, active, blocked, flags, dropped) != (0, 0, 1, 0, 0)
                or identity != last or last not in self.terminals or last not in self.accepted
                or last != max(self.terminals) or total != self.outputs.get(last, (0, 0))[1]
                or any(n not in self.responses for n, k in self.requests.items()
                       if k not in (wire.EXEC, DETACH))):
            raise wire.ProtocolError('DETACH lacks exact idle terminal state')
        self.finished = True
        self.responses.add(seq)
        self._record(dict(event='response', sequence=seq, kind=kind,
                          fields=list(struct.unpack('<8I', body))))


def _fixed_health(session, events):
    end = next(i+1 for i, (kind, seq, _) in enumerate(events)
               if (kind, seq) == (wire.STATUS_REPLY, 4))
    prefix = events[:end]
    view = SimpleNamespace(ready=session.ready, requests={n: k for n, k in session.requests.items() if n <= 4},
        request_bodies=session.request_bodies, accepted=session.accepted,
        faulted=any(k == wire.FAULT for k, _, _ in prefix))
    health.validate_console(view, prefix)


def _root_end(raw, offset, terminal_kinds):
    """Find only a bounded complete-frame boundary; replay verifies every byte."""
    start = offset
    while offset < len(raw):
        if len(raw)-offset < 16: raise ValueError('partial baseline root header')
        magic, version, kind, size, seq, _ = struct.unpack('<4sBBHII', raw[offset:offset+16])
        if magic != b'S328' or version != 1 or not 32 <= size <= wire.MAX_PAYLOAD:
            raise ValueError('baseline root framing differs')
        offset += 16+size
        if offset > len(raw): raise ValueError('partial baseline root payload')
        if kind in terminal_kinds: return offset
        if offset-start > wire.SESSION_RX_LIMIT: raise ValueError('baseline root stream limit')
    raise ValueError('baseline terminal frame absent')


def _projection(io, session, events, rx, tx):
    if any(events[i][1] > events[i+1][1] for i in range(len(events)-1)):
        raise ValueError('baseline retained response phase order differs')
    _fixed_health(session, events)
    requests = dict(session.requests)
    ending = requests.pop(max(requests))
    if ending not in (wire.CONTROL, DETACH): raise ValueError('baseline ending differs')
    optional = requests.pop(5, None)
    if (requests != {3: wire.EXEC, 4: wire.STATUS} or optional not in (None, wire.EXEC)
            or optional is not None and session.request_bodies[5] != display.HUD_BODY):
        raise ValueError('baseline fixed request profile differs')
    info = io.preparation.info
    if ending == DETACH and info['authentication_ordinal'] >= AUTH_LIMIT:
        raise ValueError('native terminal has no future authentication slot')
    rows = console.command_rows(session, events)
    hud_stdout = b''.join(p[12:] for k, n, p in events if (k, n) == (wire.OUTPUT, 5)
                        and struct.unpack_from('<I', p, 8)[0] == 1)
    hud_stderr = b''.join(p[12:] for k, n, p in events if (k, n) == (wire.OUTPUT, 5)
                        and struct.unpack_from('<I', p, 8)[0] == 2)
    hud_terminal = next((struct.unpack('<7I', p) for k, n, p in events
                         if (k, n) == (wire.EXIT, 5)), None)
    hud_complete = bool(optional and hud_terminal is not None and hud_terminal[:4] == (5, 0, 0, 0)
                        and hud_terminal[5] == 0 and not hud_stderr)
    return dict(schema=SCHEMA, run_id_hex=io.identity.run_id_hex, native_health_proved=True,
        ending='detach' if ending == DETACH else 'download', terminal_sequence=session.control_sequence,
        detach_ack_observed=ending == DETACH, control_acceptance_observed=ending == wire.CONTROL,
        kernel_boot_identity_sha256=health.digest(io.audit.boot_id), nonce_sha256=health.digest(io.audit.nonce),
        preparation=io.preparation.projection(), baseline_info=info, root_ready=list(session.ready),
        commands=rows, request_count=len(session.requests),
        all_commands_terminal_or_rejected=all(row['terminal'] is not None or row['rejected'] for row in rows),
        rx=dict(size=len(rx), sha256=health.digest(rx)), tx=dict(size=len(tx), sha256=health.digest(tx)),
        hud_requested=bool(optional), hud_acquisition_complete=hud_complete,
        hud=display.decode_log(hud_stdout, io.identity.run_id_hex) if hud_complete else None,
        physical_visibility='UNPROVED', source_profile=source.profile_contract(source.BASELINE_PROFILE))


def replay_one(codec, identity, key, rx, tx):
    if type(rx) is not bytes or type(tx) is not bytes or len(rx) > wire.RAW_CAPTURE_MAXIMUM or len(tx) > 65536:
        raise ValueError('baseline raw stream bounds differ')
    io = IO(codec, key, identity, rx=rx, tx=tx)
    io.handshake()
    rend = _root_end(rx, io.rpos, (wire.CONTROL_ACK, DETACH_ACK))
    tend = _root_end(tx, io.tpos, (wire.CONTROL, DETACH))
    session, events = wire.replay(key, bytes.fromhex(identity.run_id_hex), io.audit.nonce,
        rx[io.rpos:rend], tx[io.tpos:tend], session_class=Session)
    value = _projection(io, session, events, rx[:rend], tx[:tend])
    return value, rend, tend


def fresh_same_boot(previous, current, *, seen_nonce_hashes=()):
    if (previous['run_id_hex'] != current['run_id_hex']
            or previous['kernel_boot_identity_sha256'] != current['kernel_boot_identity_sha256']
            or previous['nonce_sha256'] == current['nonce_sha256']
            or current['nonce_sha256'] in seen_nonce_hashes
            or current['baseline_info']['authentication_ordinal'] != previous['baseline_info']['authentication_ordinal']+1
            or current['baseline_info']['elapsed_ms'] < previous['baseline_info']['elapsed_ms']
            or previous['ending'] != 'detach' or not previous['detach_ack_observed']):
        raise ValueError('clean same-boot native reauthentication is unproved')


def qualify_one(io, *, ending, evidence, before_terminal, hud=False):
    """One owner-bound authentication and fixed health, followed by one ending."""
    if ending not in ('detach', 'download') or not callable(before_terminal):
        raise ValueError('baseline owner ending differs')
    if not time.monotonic() < io.deadline <= time.monotonic()+60:
        raise ValueError('baseline observation deadline differs')
    session = None; events = []
    def wait(kind, seq):
        while not any((k, n) == (kind, seq) for k, n, _ in events):
            if time.monotonic() >= io.deadline: raise TimeoutError('baseline original observation deadline')
            events.extend(session.poll()); time.sleep(.001)
    try:
        io.handshake()
        session = Session(io.fd, io.key, bytes.fromhex(io.identity.run_id_hex), io.audit.nonce,
            Path(evidence), on_rx=io.capture, on_tx=io.audit.tx.extend, before_write=io.before_write)
        health.run_console_checks(session, events, deadline=min(io.deadline, time.monotonic()+29.9))
        if hud and io.deadline-time.monotonic() >= display.HUD_ADMISSION_SECONDS:
            seq = session.send(wire.EXEC, display.HUD_BODY)
            while seq not in session.terminals and seq not in session.rejected:
                if time.monotonic() >= io.deadline: raise TimeoutError('baseline HUD original deadline')
                events.extend(session.poll()); time.sleep(.001)
        kind, ack = (DETACH, DETACH_ACK) if ending == 'detach' else (wire.CONTROL, wire.CONTROL_ACK)
        if ending == 'detach' and io.preparation.info['authentication_ordinal'] >= AUTH_LIMIT:
            raise ValueError('no native reauthentication remains after DETACH')
        request = dict(run_id_hex=io.identity.run_id_hex, mode=ending, sequence=session.sequence,
            nonce_sha256=health.digest(io.audit.nonce), kernel_boot_identity_sha256=health.digest(io.audit.boot_id),
            baseline_info=io.preparation.info)
        before_terminal(request)
        remaining = io.deadline-time.monotonic()
        if remaining <= 0: raise TimeoutError('baseline terminal admission expired')
        wait(ack, session.send(kind, timeout=min(2, remaining)))
        raw_rx, raw_tx = bytes(io.audit.rx), bytes(io.audit.tx)
        value, rend, tend = replay_one(io.codec, io.identity, io.key, raw_rx, raw_tx)
        if (rend, tend) != (len(raw_rx), len(raw_tx)):
            raise ValueError('baseline trailing raw bytes')
        io.audit.done_seen = True; io.audit.current_stage = ending+'-accepted'
        return value
    finally:
        if session is not None: session.close()
