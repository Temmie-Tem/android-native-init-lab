"""Direct local-display candidate adapter for the existing F1 transport owner.

Candidate identity is data. Handshake, progress and receipt projection are
shared, without executing projected candidate Python or opening a transport.
"""
from dataclasses import dataclass
import copy
import hashlib
import hmac
import json
import os
from pathlib import Path
import select
import struct
import time
from types import SimpleNamespace

import s22plus_local_display_observer_v1 as local
import s22plus_native_baseline_health_v1 as health
import s22plus_native_source_v1 as source
import s22plus_root_console_v1 as wire

EXPECTED = [(1, 0)]
for _index in range(5):
    if _index == 4:
        for _stage in (30, 31, 32): EXPECTED.extend(((_stage, 0), (_stage, 1)))
    for _stage in range(10+3*_index, 13+3*_index): EXPECTED.extend(((_stage, 0), (_stage, 1)))
EXPECTED.extend(((33, 0), (33, 1), (1, 1)))
for _stage in (60, 61, 62): EXPECTED.extend(((_stage, 0), (_stage, 1)))
EXPECTED = tuple(EXPECTED)


class Progress:
    def __init__(self, identity):
        self.identity = identity
        self.records = []; self.failure = None; self.terminal = False

    def accept(self, frame, key, nonce):
        payload = frame.payload; ordinal = len(self.records)
        if (self.terminal or ordinal >= 49 or frame.frame_type != 139
                or frame.sequence != 256+ordinal or len(payload) != 40):
            raise ValueError('native preparation framing/ordinal differs')
        domain = ('S22PLUS-FYG8-'+self.identity.namespace.upper()+'-PROGRESS-v1').encode()
        tag = hmac.digest(key, domain+bytes.fromhex(self.identity.run_id_hex)+nonce+
                          struct.pack('<I', frame.sequence)+payload[:8], 'sha256')
        if not hmac.compare_digest(tag, payload[8:]):
            raise ValueError('native preparation authentication differs')
        stage, event, reserved, code = struct.unpack('<HBBi', payload[:8])
        if reserved or event not in (0, 1, 4) or not -4095 <= code <= 0:
            raise ValueError('native preparation fields differ')
        if event == 4:
            if stage != 255 or self.failure is None or code != self.failure['code']:
                raise ValueError('native preparation terminal is not joined')
            self.terminal = True
        else:
            if self.failure is not None or ordinal >= len(EXPECTED) or (stage, event) != EXPECTED[ordinal]:
                raise ValueError('native preparation order differs')
            if event == 0 and code: raise ValueError('native ENTER has a return value')
            if code: self.failure = dict(stage=stage, code=code)
        self.records.append(dict(stage=stage, event=event, code=code))

    def ready(self):
        return len(self.records) == len(EXPECTED) and self.failure is None

    def projection(self):
        return dict(schema='s22plus-fyg8-'+self.identity.namespace+'-preparation-progress-v1',
                    records=list(self.records), failure=self.failure, complete=self.ready())


class IO:
    """Existing raw-first bounded handshake over one owner-supplied descriptor."""
    def __init__(self, codec, key, identity, *, fd=None, writer=None, deadline=None, rx=None, tx=None):
        self.codec, self.key, self.identity = codec, key, identity
        self.fd, self.writer, self.deadline = fd, writer, deadline
        self.raw_rx, self.raw_tx = rx, tx; self.rpos = self.tpos = 0
        self.audit = codec.ExchangeAudit(auth_key_sha256=health.digest(key))
        self.audit.current_stage = 'not-started'; self.audit.failure_stage = None
        self.preparation = Progress(identity); self.audit.native_preparation = self.preparation

    def capture(self, part):
        self.writer.write_stdout(part); self.audit.rx.extend(part)

    def read(self, size):
        if self.raw_rx is not None:
            part = self.raw_rx[self.rpos:self.rpos+size]; self.rpos += len(part)
            self.audit.rx.extend(part)
            if len(part) != size: raise EOFError('partial retained native RX')
            return part
        result = bytearray()
        while len(result) < size:
            left = self.deadline-time.monotonic()
            if left <= 0: raise TimeoutError('original native handshake deadline')
            ready, _, _ = select.select([self.fd], [], [], min(.05, left))
            if not ready: continue
            try: part = os.read(self.fd, size-len(result))
            except (BlockingIOError, InterruptedError): continue
            if not part: raise EOFError('native transport closed')
            self.capture(part); result.extend(part)
        return bytes(result)

    def send(self, kind, sequence, payload):
        if self.raw_tx is not None:
            encoded = self.codec._CODEC.encode_frame(kind, sequence, payload)
            part = self.raw_tx[self.tpos:self.tpos+len(encoded)]; self.tpos += len(part)
            self.audit.tx.extend(part)
            if part != encoded: raise ValueError('retained native handshake TX differs')
        else:
            self.codec._CODEC._send(self.fd, kind, sequence, payload, self.deadline, self.audit)

    def frame(self):
        head = self.read(16); size = self.codec._CODEC.HEADER.unpack(head)[3]
        if size > wire.MAX_PAYLOAD: raise ValueError('native handshake frame bound')
        return self.codec._CODEC.decode_frame(head+self.read(size))

    def expect(self, kind, sequence):
        return self.codec._CODEC._expect(self.frame(), kind, sequence)

    def handshake(self):
        a, c = self.audit, self.codec; run = bytes.fromhex(self.identity.run_id_hex)
        a.current_stage = 'open-write'; self.send(1, 0, run)
        a.current_stage = 'banner-read'
        banner = b'S22PLUS-FYG8-E3:'+self.identity.run_id_hex.encode()+b'\n'
        if self.read(len(banner)) != banner: raise ValueError('native banner differs')
        a.banner_seen = True
        for stage in (0, 1, 2): a.diagnostics.append(c._P333.parse_diagnostic_frame(self.frame(), stage))
        a.rng_eagain_retries = a.diagnostics[-1].code
        if not 0 <= a.rng_eagain_retries <= 64: raise ValueError('native RNG diagnostic differs')
        a.nonce = self.expect(133, 0); c._CODEC._validate_nonce(a.nonce); a.challenge_seen = True
        self.send(4, 1, c.compute_open_tag(self.key, run, a.nonce))
        if not hmac.compare_digest(self.expect(129, 1), c.compute_ready_tag(self.key, run, a.nonce)):
            raise ValueError('native AUTH READY differs')
        a.ready_seen = a.authenticated = True
        a.boot_id = c.decode_boot_id_frame(self.frame(), self.key, run, a.nonce)
        a.current_stage = 'root-preparation'
        while not self.preparation.ready():
            self.preparation.accept(self.frame(), self.key, a.nonce)
            if self.preparation.failure:
                while not self.preparation.terminal:
                    self.preparation.accept(self.frame(), self.key, a.nonce)
                raise ValueError('native preparation failed')
        a.current_stage = 'root-console'


class QualificationError(ValueError):
    def __init__(self, message, *, audit=None, partial_receipt=None):
        super().__init__(message)
        self.failed_audit = audit; self.completed_sessions = ()
        self.partial_receipt = partial_receipt or {}


@dataclass(frozen=True)
class QualificationResult:
    receipt: dict
    sessions: tuple


def command_rows(session, events):
    rows = []
    for seq, kind in session.requests.items():
        if kind != wire.EXEC: continue
        body = session.request_bodies[seq]; timeout, cwd_size = struct.unpack('<IH', body[:6])
        streams = {stream: b''.join(p[12:] for k, n, p in events if (k, n) == (wire.OUTPUT, seq)
                   and struct.unpack_from('<I', p, 8)[0] == stream) for stream in (1, 2)}
        terminal = next((list(struct.unpack('<7I', p)) for k, n, p in events if (k, n) == (wire.EXIT, seq)), None)
        identify = lambda data: dict(size=len(data), sha256=health.digest(data))
        rows.append(dict(sequence=seq, timeout_ms=timeout, cwd=identify(body[6:6+cwd_size]),
            command=identify(body[6+cwd_size:]), stdout=identify(streams[1]), stderr=identify(streams[2]),
            terminal=terminal, accepted=seq in session.accepted, rejected=seq in session.rejected))
    return rows


class Observer:
    SESSION_COUNT = 1
    RAW_MAXIMUM = wire.RAW_CAPTURE_MAXIMUM
    QUALIFICATION_TIMEOUT_SEC = 60
    QualificationError = QualificationError

    def __init__(self, identity, control):
        self.identity, self.control = identity, control
        self.__file__ = __file__
        self.RUN_ID_HEX = identity.run_id_hex; self.RUN_ID = bytes.fromhex(identity.run_id_hex)
        self.SCHEMA = 's22plus-fyg8-'+identity.namespace+'-local-console-qualification-v1'
        self.CONTRACT_ID = 's22plus-fyg8-'+identity.namespace+'-local-console-observer-v1'
        self.PROOF_SCOPE = 'fixed-native-health-with-optional-local-display-observation'
        self.QUALIFICATION_COMMANDS = (SimpleNamespace(ordinal=1, name='native-baseline-health', command=health.COMMAND),)

    def binding(self): return local.Binding(self.identity, source.source_receipts())

    @staticmethod
    def operator_plan_rows(proof):
        rows = proof.get('commands', [])
        if type(rows) is not list or len(rows) > 2 or any(row.get('sequence') != seq for row, seq in zip(rows, (3, 5))):
            raise ValueError('native fixed observation command rows differ')
        return []

    def IO(self, codec, key, **kwargs): return IO(codec, key, self.identity, **kwargs)

    def progress_projection(self, audit):
        return getattr(audit, 'native_preparation', Progress(self.identity)).projection()

    def replay_progress(self, codec, rx, tx, key):
        io = self.IO(codec, key, rx=rx, tx=tx)
        try: io.handshake()
        except (ValueError, EOFError): pass
        return io.preparation.projection()

    def _projection(self, io, observation, session=None, events=()):
        rows = command_rows(session, events) if session is not None else []
        proved = observation.get('native_health_proved') is True and observation.get('control_acceptance_observed') is True
        return dict(schema=self.SCHEMA, proved=proved, run_id_hex=self.RUN_ID_HEX,
            session_count=1, command_count=len(rows), request_count=len(session.requests) if session else 0,
            commands=rows, preparation=io.preparation.projection(), root_ready=list(session.ready) if session and session.ready else None,
            nonce_sha256=observation.get('nonce_sha256'), kernel_boot_identity_sha256=observation.get('kernel_boot_identity_sha256'),
            control_sequence=observation.get('control_sequence'), control_acceptance_observed=observation.get('control_acceptance_observed', False),
            control_ack_scope='acceptance-only', same_tty_fd=True, physical_reopen_count=0,
            console_reentry=False, all_commands_terminal_or_rejected=all(r['rejected'] or r['terminal'] is not None for r in rows),
            qualified_command_count=1 if observation.get('native_health_proved') else 0, local_display=observation,
            qualification_events=[dict(kind=k, sequence=n, payload_hex=p.hex()) for k, n, p in events
                                  if (k, n) == (wire.STATUS_REPLY, 4)])

    def replay_session(self, codec, rx, tx, key, *, partial=False):
        io = self.IO(codec, key, rx=rx, tx=tx)
        observation = local.replay(io, self.binding())
        state, events = wire.replay(key, self.RUN_ID, io.audit.nonce, rx[io.rpos:], tx[io.tpos:])
        value = self._projection(io, observation, state, events)
        if not partial: self.validate_qualification(value)
        return value

    def validate_qualification(self, value):
        if (type(value) is not dict or value.get('schema') != self.SCHEMA or value.get('proved') is not True
                or value.get('run_id_hex') != self.RUN_ID_HEX or value.get('session_count') != 1
                or value.get('qualified_command_count') != 1 or value.get('control_acceptance_observed') is not True
                or value.get('root_ready') != [1, 600000, 300000, 1048576, 767, 255, 0, 0]
                or value.get('preparation') != dict(schema='s22plus-fyg8-'+self.identity.namespace+'-preparation-progress-v1',
                    records=[dict(stage=s, event=e, code=0) for s, e in EXPECTED], failure=None, complete=True)):
            raise QualificationError('native local-console qualification differs')
        rows = value.get('commands'); observation = value.get('local_display', {})
        count = 2 if observation.get('hud_requested') is True else 1
        fixed = dict(session_count=1, command_count=count, request_count=count+2, control_sequence=count+4,
            same_tty_fd=True, physical_reopen_count=0, console_reentry=False,
            all_commands_terminal_or_rejected=True, control_ack_scope='acceptance-only',
            qualification_events=[dict(kind=wire.STATUS_REPLY, sequence=4,
                payload_hex=struct.pack('<8I', 3, 0, 0, 0, 0, len(health.STDOUT)+len(health.STDERR), 0, 3).hex())])
        if (any(json.dumps(value.get(k), sort_keys=True) != json.dumps(v, sort_keys=True) for k, v in fixed.items())
                or type(rows) is not list or len(rows) != count
                or observation.get('native_health_proved') is not True or observation.get('control_acceptance_observed') is not True
                or observation.get('run_id_hex') != self.RUN_ID_HEX
                or observation.get('source_profile') != source.profile_contract(source.LOCAL_PROFILE)):
            raise QualificationError('native local-console profile differs')
        identify = lambda data: dict(size=len(data), sha256=health.digest(data))
        expected = dict(sequence=3, timeout_ms=15000, cwd=identify(b'/'), command=identify(health.COMMAND),
                        stdout=identify(health.STDOUT), stderr=identify(health.STDERR), accepted=True, rejected=False)
        terminal = rows[0].get('terminal')
        if (set(rows[0]) != set(expected)|{'terminal'}
                or any(json.dumps(rows[0].get(k), sort_keys=True) != json.dumps(v, sort_keys=True) for k, v in expected.items())
                or type(terminal) is not list or len(terminal) != 7 or any(type(n) is not int for n in terminal)
                or terminal[:6] != [3, 0, 0, 0, len(health.STDOUT)+len(health.STDERR), 0]
                or not 1 <= terminal[6] <= wire.OUTPUT_FRAME_LIMIT):
            raise QualificationError('native fixed-health receipt differs')
        if count == 2:
            hud = rows[1]
            expected = dict(sequence=5, timeout_ms=15000, cwd=identify(b'/s22-root-work'), command=identify(local.HUD_COMMAND))
            if any(hud.get(k) != v for k, v in expected.items()):
                raise QualificationError('native optional HUD request differs')
        return copy.deepcopy(value)

    def qualify(self, codec, descriptor, auth_key, expected_boot_sha256, seen_nonces, writer, *,
                deadline, before_control, evidence, interactive=None):
        if expected_boot_sha256 is not None or seen_nonces:
            raise QualificationError('native local-console fresh inputs differ')
        io = self.IO(codec, auth_key, fd=descriptor, writer=writer, deadline=deadline)
        observation = {}
        def control(request):
            before_control(dict(request, boot_id_semantic=self.control.BOOT_ID_SEMANTIC,
                                boot_receipt_semantic=self.control.BOOT_RECEIPT_SEMANTIC))
        try:
            if interactive is not None: interactive(None, [], deadline)
            observation = local.qualify(io, self.binding(), evidence=evidence, before_control=control)
            value = self.replay_session(codec, bytes(io.audit.rx), bytes(io.audit.tx), auth_key)
            io.audit.done_seen = True; io.audit.current_stage = 'control-accepted'
            seen_nonces.add(health.digest(io.audit.nonce))
            return QualificationResult(value, (SimpleNamespace(session=SimpleNamespace(audit=io.audit)),))
        except BaseException as exc:
            io.audit.failure_stage = io.audit.current_stage
            partial = self._projection(io, getattr(exc, 'partial_receipt', observation))
            partial['proved'] = False
            raise QualificationError('native local-console stopped; no replay', audit=io.audit, partial_receipt=partial) from exc

    def audit_binding(self):
        return dict(schema=self.SCHEMA, contract_id=self.CONTRACT_ID, session_count=1,
            qualification_timeout_sec=60, root_console=True, qualified_exec_count=1,
            optional_hud_exec_count=1, interactive_commands=False, physical_reopen_count=0,
            source_profile=source.profile_contract(source.LOCAL_PROFILE),
            control_sequences=[5, 6], control_ack_scope='acceptance-only', raw_replay_required=True,
            live_authorized=False)
