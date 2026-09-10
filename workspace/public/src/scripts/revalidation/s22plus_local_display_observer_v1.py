"""Dormant local-display-v1 observer on an owner's existing authenticated IO.

No endpoint discovery, transport open, candidate registration or live authority.
The owner binds the platform/IO closure; this adapter binds the direct local
source profile. Fixed native health precedes optional display observation.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import re
import struct
import time
from types import SimpleNamespace

import s22plus_native_baseline_health_v1 as health
import s22plus_native_source_v1 as source
import s22plus_root_console_v1 as wire

SCHEMA = 's22plus-local-display-observer-v1'
HUD_LIMIT = 1048576
# A bounded collection window; a failed or stale sample never qualifies health.
HUD_COMMAND = b'/bin/busybox sleep 3; /bin/busybox cat hud.log'
HUD_BODY = wire.command(HUD_COMMAND, cwd=b'/s22-root-work', timeout_ms=15000)
# Delivery2 + command15 + native cleanup2 + CONTROL delivery2/flush5 seconds.
HUD_ADMISSION_SECONDS = 26
_FIELDS = ('seq uptime_ms state metrics_seq valid age_ms mem_total mem_available '
           'cpu_permille battery_pct charge temp_deci gauge_seq gauge_age_ms '
           'gauge_soc voltage_uv current_ua').split()
_FRAME = re.compile(rb'HUD_FRAME run=([0-9a-f]{32})' + b''.join(
    b' ' + name.encode() + rb'=(-?[0-9]{1,20})' for name in _FIELDS)
    + rb' event=matched visible=UNPROVED')
_MEM = re.compile(rb'HUD_MEM seq=([0-9]{1,3}) ms=([0-9]{1,20}) alloc=([0-9]{1,3})'
                  rb' retired=([0-9]{1,3}) live=([0-9]+) peak=([0-9]+) bytes=([0-9]+)')
_LIFECYCLE = re.compile(rb'(HUD|METRICS)_(EXIT|SIGNAL_ATTEMPT|SIGNAL_ERROR|WAIT_ERROR|START_ERROR|INPUT_ERROR) ([0-9]{1,20})')


@dataclass(frozen=True)
class Binding:
    identity: source.Identity
    sources: dict
    profile: str = source.LOCAL_PROFILE

    def validate(self):
        if (type(self.identity) is not source.Identity or self.profile != source.LOCAL_PROFILE
                or self.sources != source.source_receipts()):
            raise ValueError('local display source/profile binding differs')


def decode_log(raw, run_id_hex):
    """Decode reported flips; neither physical pixels nor PID1 are inferred."""
    result = dict(schema=SCHEMA + '-log', log_sha256=health.digest(raw), size=len(raw),
                  valid=False, frame_count=0, states=[], fresh_memory_cpu_samples=0,
                  fresh_gauge_samples=0, matched_flip_observed=False,
                  physical_visibility='UNPROVED', lifecycle_records=[])
    if len(raw) > HUD_LIMIT or not raw.endswith(b'\n'):
        return result
    starts = {}; frames = []; memory = set(); gauge = set(); mem_lines = diag_lines = 0
    failed = False
    for line in raw.split(b'\n')[:-1]:
        if len(line) > 1152:
            return result
        if line.startswith((b'HUD_START ', b'METRICS_START ')):
            match = re.fullmatch(rb'(HUD|METRICS)_START ([0-9]{1,10})', line)
            if not match or match[1] in starts or not 1 < int(match[2]) <= 2**31-1:
                return result
            starts[match[1]] = int(match[2])
        elif line.startswith(b'HUD_FRAME '):
            match = _FRAME.fullmatch(line)
            if not match or match[1].decode() != run_id_hex:
                return result
            row = dict(zip(_FIELDS, map(int, match.groups()[1:]), strict=True))
            seq, up, flags, ms, gs = (row[k] for k in ('seq', 'uptime_ms', 'valid', 'metrics_seq', 'gauge_seq'))
            if (any(not 0 <= v <= 2**64-1 for k, v in row.items() if k not in ('temp_deci', 'current_ua'))
                    or not 1 <= seq <= 916 or not up or not 0 <= row['state'] <= 8
                    or flags & ~255 or not 0 <= ms <= 601 or not 0 <= gs <= 601
                    or frames and (seq <= frames[-1]['seq'] or up < frames[-1]['uptime_ms']
                                   or ms < frames[-1]['metrics_seq'] or gs < frames[-1]['gauge_seq'])):
                return result
            if (flags & 31 and (not ms or row['age_ms'] > 5000)
                    or flags & 224 and (not gs or row['gauge_age_ms'] > 5000)
                    or flags & 1 and not 0 <= row['mem_available'] <= row['mem_total'] <= 2**30
                    or flags & 1 and not row['mem_total']
                    or flags & 2 and row['cpu_permille'] > 1000
                    or flags & 4 and row['battery_pct'] > 100
                    or flags & 8 and row['charge'] > 4
                    or flags & 16 and not -500 <= row['temp_deci'] <= 1500
                    or flags & 32 and row['gauge_soc'] > 1000
                    or flags & 64 and not 2000000 <= row['voltage_uv'] <= 5000000
                    or flags & 128 and not -25600000 <= row['current_ua'] <= 25599218):
                return result
            frames.append(row)
            if flags & 3 == 3:
                memory.add(ms)
            if flags & 227 == 227:
                gauge.add(gs)
        elif line.startswith(b'HUD_MEM '):
            match = _MEM.fullmatch(line); mem_lines += 1
            if not match or mem_lines > 32:
                return result
            seq, ms, alloc, retired, live, peak, size = map(int, match.groups())
            if not (1 <= seq <= 916 and 0 < ms <= 2**64-1 and
                    1 <= alloc <= 916 and retired == alloc-1 and live == 1 and
                    1 <= peak <= 2 and 0 < size <= 64*1024*1024):
                return result
        elif line.startswith(b'GAUGE_DIAG '):
            # Diagnostic text is retained but makes no telemetry/probe claim.
            diag_lines += 1
            if diag_lines > 8 or any(c < 32 or c > 126 for c in line):
                return result
        elif (match := _LIFECYCLE.fullmatch(line)):
            result['lifecycle_records'].append(line.decode())
            failed = True  # A signal attempt is never reported as a reap.
        elif line.startswith((b'HUD_', b'METRICS_', b'DISPLAY_FAIL', b'DISPLAY_DIAG', b'DISPLAY_KMSG_')):
            return result
        # Other bounded renderer startup/kernel diagnostic text is uninterpreted.
    if set(starts) != {b'HUD', b'METRICS'} or len(set(starts.values())) != 2 or not frames:
        return result
    result.update(valid=not failed, frame_count=len(frames),
                  states=sorted({r['state'] for r in frames}),
                  fresh_memory_cpu_samples=len(memory), fresh_gauge_samples=len(gauge),
                  matched_flip_observed=not failed)
    return result


def _handshake_binding(io, binding):
    binding.validate()
    audit = io.audit
    preparation = io.preparation.projection()
    run_id = bytes.fromhex(binding.identity.run_id_hex)
    if (not all(getattr(audit, name, False) for name in ('banner_seen', 'challenge_seen', 'ready_seen', 'authenticated'))
            or bytes(audit.tx)[16:32] != run_id or len(audit.nonce) != 32 or len(audit.boot_id) != 32
            or preparation.get('schema') != 's22plus-fyg8-' + binding.identity.namespace + '-preparation-progress-v1'
            or preparation.get('complete') is not True or preparation.get('failure') is not None):
        raise ValueError('local display authenticated preparation binding differs')


def _health_prefix(session, events):
    end = next(i+1 for i, (k, n, _) in enumerate(events) if (k, n) == (wire.STATUS_REPLY, 4))
    prefix = events[:end]
    view = SimpleNamespace(ready=session.ready, requests={n: k for n, k in session.requests.items() if n <= 4},
        request_bodies=session.request_bodies, accepted=session.accepted,
        faulted=any(k == wire.FAULT for k, _, _ in prefix))
    health.validate_console(view, prefix)


def _receipt(io, binding, session, events, *, healthy):
    hud_requested = session is not None and session.requests.get(5) == wire.EXEC
    control_sequence = 6 if hud_requested else 5
    stdout = b''.join(p[12:] for k, n, p in events if (k, n) == (wire.OUTPUT, 5)
                      and struct.unpack_from('<I', p, 8)[0] == 1)
    stderr = b''.join(p[12:] for k, n, p in events if (k, n) == (wire.OUTPUT, 5)
                      and struct.unpack_from('<I', p, 8)[0] == 2)
    terminal = next((struct.unpack('<7I', p) for k, n, p in events if (k, n) == (wire.EXIT, 5)), None)
    complete = (session is not None and 5 in session.accepted and terminal is not None
                and terminal[:4] == (5, 0, 0, 0) and terminal[5] == 0 and not stderr)
    return dict(schema=SCHEMA, source_profile=source.profile_contract(binding.profile),
        direct_sources_sha256=health.digest(json.dumps(binding.sources, sort_keys=True, separators=(',', ':')).encode()),
        run_id_hex=binding.identity.run_id_hex, native_health_proved=healthy,
        control_sequence=control_sequence,
        control_acceptance_observed=any((k, n) == (wire.CONTROL_ACK, control_sequence) for k, n, _ in events),
        download_arrival_proved=False, hud_acquisition_complete=bool(complete),
        hud_requested=hud_requested,
        hud=decode_log(stdout, binding.identity.run_id_hex) if complete else None,
        hud_stdout_sha256=health.digest(stdout), hud_stderr_sha256=health.digest(stderr),
        hud_terminal=list(terminal) if terminal else None,
        kernel_boot_identity_sha256=health.digest(io.audit.boot_id) if getattr(io.audit, 'boot_id', b'') else None,
        nonce_sha256=health.digest(io.audit.nonce) if io.audit.nonce else None,
        rx_sha256=health.digest(bytes(io.audit.rx)), tx_sha256=health.digest(bytes(io.audit.tx)))


class ObservationError(ValueError):
    def __init__(self, io, receipt):
        super().__init__('local display observation stopped; no retry or reopen')
        self.audit = io.audit
        self.partial_receipt = receipt


def qualify(io, binding, *, evidence, before_control):
    """One owner-supplied IO, fixed health, optional HUD read, owned CONTROL."""
    binding.validate()
    if not callable(before_control) or not time.monotonic() < io.deadline <= time.monotonic()+60:
        raise ValueError('local display owner/deadline differs')
    session = None; events = []; healthy = False
    def wait(kind, seq):
        while not any((k, n) == (kind, seq) for k, n, _ in events):
            if time.monotonic() >= io.deadline:
                raise TimeoutError('local display original deadline')
            events.extend(session.poll()); time.sleep(.001)
    try:
        io.handshake()
        _handshake_binding(io, binding)
        session = wire.Session(io.fd, io.key, bytes.fromhex(binding.identity.run_id_hex), io.audit.nonce,
            Path(evidence), on_rx=io.capture, on_tx=io.audit.tx.extend)
        health.run_console_checks(session, events, deadline=min(io.deadline, time.monotonic()+29.9))
        healthy = True
        if io.deadline-time.monotonic() >= HUD_ADMISSION_SECONDS:
            seq = session.send(wire.EXEC, HUD_BODY)
            # A rejection is optional-observation failure; no new EXEC is attempted.
            while seq not in session.terminals and seq not in session.rejected:
                if time.monotonic() >= io.deadline:
                    raise TimeoutError('local display HUD original deadline')
                events.extend(session.poll()); time.sleep(.001)
        request = dict(run_id_hex=binding.identity.run_id_hex, mode='download', sequence=session.sequence,
            nonce_sha256=health.digest(io.audit.nonce), kernel_boot_identity_sha256=health.digest(io.audit.boot_id))
        before_control(request)
        remaining = io.deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError('local display CONTROL original deadline')
        wait(wire.CONTROL_ACK, session.send(wire.CONTROL, timeout=min(2, remaining)))
        return _receipt(io, binding, session, events, healthy=healthy)
    except BaseException as exc:
        raise ObservationError(io, _receipt(io, binding, session, events, healthy=healthy)) from exc
    finally:
        if session is not None:
            session.close()


def replay(io, binding):
    """Use the same source-bound handshake consumer on complete retained bytes."""
    binding.validate()
    if io.raw_rx is None or io.raw_tx is None or len(io.raw_rx) > wire.RAW_CAPTURE_MAXIMUM or len(io.raw_tx) > 65536:
        raise ValueError('local display retained raw bounds differ')
    io.handshake(); _handshake_binding(io, binding)
    session, events = wire.replay(io.key, bytes.fromhex(binding.identity.run_id_hex), io.audit.nonce,
        io.raw_rx[io.rpos:], io.raw_tx[io.tpos:])
    if not (session.requests == {3: wire.EXEC, 4: wire.STATUS, 5: wire.CONTROL}
            or session.requests == {3: wire.EXEC, 4: wire.STATUS, 5: wire.EXEC, 6: wire.CONTROL}
            and session.request_bodies[5] == HUD_BODY):
        raise ValueError('local display retained request profile differs')
    if any(events[i][1] > events[i+1][1] for i in range(len(events)-1)):
        raise ValueError('local display retained response phase order differs')
    _health_prefix(session, events)
    io.audit.rx = bytearray(io.raw_rx); io.audit.tx = bytearray(io.raw_tx)
    return _receipt(io, binding, session, events, healthy=True)
