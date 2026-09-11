"""H0 resident wire and retained-log readers. No endpoint discovery or authority.

The caller owns exact IO and finite deadlines. Every command session is bounded;
the local service's indefinite lifetime does not renew a host grant.
"""
import hashlib
import hmac
import re
import struct

import s22plus_native_baseline_protocol_v1 as baseline
import s22plus_native_console_observer_v1 as console
import s22plus_root_console_v1 as wire

MAX_COUNTER = 2**64 - 1
Session = baseline.Session
DETACH, DETACH_ACK = baseline.DETACH, baseline.DETACH_ACK


class Progress(console.Progress):
    def __init__(self, identity):
        super().__init__(identity)
        self.info = None

    def accept(self, frame, key, nonce):
        if self.info is not None:
            return super().accept(frame, key, nonce)
        payload = frame.payload
        if (frame.frame_type, frame.sequence, len(payload)) != (140, 768, 64):
            raise ValueError('resident lifetime frame differs')
        domain = ('S22PLUS-FYG8-'+self.identity.namespace.upper()+'-RESIDENT-INFO-v1').encode()
        tag = hmac.digest(key, domain+bytes.fromhex(self.identity.run_id_hex)+nonce+
                         struct.pack('<I', 768)+payload[:32], 'sha256')
        if not hmac.compare_digest(payload[32:], tag):
            raise ValueError('resident lifetime authentication differs')
        version, cached, ordinal, elapsed, limit = struct.unpack('<IIQQQ', payload[:32])
        if (version != 2 or not 1 <= ordinal <= MAX_COUNTER or cached != int(ordinal > 1) or limit != 0
                or len(nonce) != 32 or struct.unpack('<Q', nonce[24:])[0] != ordinal):
            raise ValueError('resident lifetime/nonce fields differ')
        self.info = dict(version=version, authentication_ordinal=ordinal,
                         preparation_cached=bool(cached), elapsed_ms=elapsed,
                         normal_service_lifetime_ms=None)
        self.expected = baseline.CACHED_PROGRESS if cached else console.EXPECTED

    def ready(self):
        return self.info is not None and super().ready()

    def projection(self):
        return dict(super().projection(), resident_info=self.info)


class IO(baseline.IO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preparation = Progress(self.identity)
        self.audit.native_preparation = self.preparation


def replay_one(codec, identity, key, rx, tx):
    if type(rx) is not bytes or type(tx) is not bytes or len(rx) > wire.RAW_CAPTURE_MAXIMUM or len(tx) > 65536:
        raise ValueError('resident session raw bounds differ')
    io = IO(codec, key, identity, rx=rx, tx=tx)
    io.handshake()
    rend = baseline._root_end(rx, io.rpos, (wire.CONTROL_ACK, DETACH_ACK))
    tend = baseline._root_end(tx, io.tpos, (wire.CONTROL, DETACH))
    session, events = wire.replay(key, bytes.fromhex(identity.run_id_hex), io.audit.nonce,
                                  rx[io.rpos:rend], tx[io.tpos:tend], session_class=Session)
    if (rend, tend) != (len(rx), len(tx)):
        raise ValueError('resident trailing or multiple-session bytes')
    ending = session.requests[max(session.requests)]
    if ending not in (wire.CONTROL, DETACH):
        raise ValueError('resident terminal request differs')
    if ending == DETACH and io.preparation.info['authentication_ordinal'] == MAX_COUNTER:
        raise ValueError('resident counter exhausted before clean reentry')
    return dict(resident_info=io.preparation.info, run_id_hex=identity.run_id_hex,
                kernel_boot_identity_sha256=hashlib.sha256(io.audit.boot_id).hexdigest(),
                nonce_sha256=hashlib.sha256(io.audit.nonce).hexdigest(),
                ending='detach' if ending == DETACH else 'download',
                detach_ack_observed=ending == DETACH, commands=console.command_rows(session, events),
                rx_sha256=hashlib.sha256(rx).hexdigest(), tx_sha256=hashlib.sha256(tx).hexdigest())


def fresh_same_boot(previous, current):
    if (previous['run_id_hex'] != current['run_id_hex']
            or previous['kernel_boot_identity_sha256'] != current['kernel_boot_identity_sha256']
            or previous['nonce_sha256'] == current['nonce_sha256']
            or current['resident_info']['authentication_ordinal'] != previous['resident_info']['authentication_ordinal']+1
            or current['resident_info']['elapsed_ms'] < previous['resident_info']['elapsed_ms']
            or previous['ending'] != 'detach' or not previous['detach_ack_observed']):
        raise ValueError('resident clean same-boot reentry is unproved')


def decode_log(raw):
    if type(raw) is not bytes or len(raw) > 64*768+320+len(b'S22RLOG1 COMPLETE\n') or not raw.endswith(b'S22RLOG1 COMPLETE\n'):
        raise ValueError('resident log is incomplete or oversized')
    lines = raw.splitlines(keepends=True)
    match = re.fullmatch(rb'S22RLOG1 first=(\d+) last=(\d+) records=(\d+) evicted=(\d+) dropped=(\d+) partial_bytes=(\d+) exhausted=([01])\n', lines[0])
    if not match:
        raise ValueError('resident log header differs')
    first, last, count, evicted, dropped, partial, exhausted = map(int, match.groups())
    if (not 0 <= count <= 64 or len(lines) != count+2 or partial >= 768 or not count and evicted
            or any(v > MAX_COUNTER for v in (first, last, evicted, dropped))
            or (first, last) != ((last-count+1, evicted+count) if count else (0, 0))):
        raise ValueError('resident log retained range differs')
    records = lines[1:-1]
    if any(not row.endswith(b'\n') or len(row) > 768 or any(c < 32 or c > 126 for c in row[:-1]) for row in records):
        raise ValueError('resident log contains an incomplete/invalid record')
    return dict(first=first, last=last, records=records, evicted=evicted,
                dropped=dropped, partial_bytes=partial, exhausted=bool(exhausted),
                complete_capture=True, complete_history=False, producer_delivery='UNPROVED')
