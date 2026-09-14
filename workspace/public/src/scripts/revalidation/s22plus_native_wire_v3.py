"""Authority-free S22+ resident handshake codec; no runtime loaders or discovery.

Wire domains retain their original meanings. The candidate namespace selects
only the authenticated kernel boot identity domain, never a transport or grant.
"""
from dataclasses import dataclass, field
import binascii
import hashlib
import hmac
import re
import struct
from types import SimpleNamespace

HEADER = struct.Struct('<4sBBHII')
MAX_PAYLOAD = 1055


@dataclass(frozen=True)
class Frame:
    frame_type: int
    sequence: int
    payload: bytes


@dataclass(frozen=True)
class Diagnostic:
    stage: int
    code: int


@dataclass
class ExchangeAudit:
    auth_key_sha256: str = ''
    tx: bytearray = field(default_factory=bytearray)
    rx: bytearray = field(default_factory=bytearray)
    diagnostics: list = field(default_factory=list)
    nonce: bytes = b''
    boot_id: bytes = b''
    banner_seen: bool = False
    challenge_seen: bool = False
    ready_seen: bool = False
    authenticated: bool = False
    done_seen: bool = False


def exact_bytes(value, size, *, nonzero=False):
    if type(value) is not bytes or len(value) != size or nonzero and not any(value):
        raise ValueError('native wire byte identity differs')
    return value


def _validate_nonce(nonce):
    return exact_bytes(nonce, 32, nonzero=True)


def tag(domain, key, run, nonce, tail=b''):
    return hmac.digest(exact_bytes(key, 32), domain+exact_bytes(run, 16)+_validate_nonce(nonce)+tail, 'sha256')


def compute_open_tag(key, run, nonce):
    return tag(b'S22PLUS-FYG8-P328-AUTH-OPEN-v1', key, run, nonce)


def compute_ready_tag(key, run, nonce):
    return tag(b'S22PLUS-FYG8-P328-AUTH-READY-v1', key, run, nonce)


def encode_frame(kind, sequence, payload):
    if (type(kind) is not int or not 0 <= kind <= 255
            or type(sequence) is not int or not 0 <= sequence <= 0xffffffff
            or type(payload) is not bytes or len(payload) > MAX_PAYLOAD):
        raise ValueError('native frame fields differ')
    prefix = struct.pack('<4sBBHI', b'S328', 1, kind, len(payload), sequence)
    crc = binascii.crc32(payload, binascii.crc32(prefix)) & 0xffffffff
    return prefix+struct.pack('<I', crc)+payload


def decode_frame(raw):
    if type(raw) is not bytes or len(raw) < HEADER.size:
        raise ValueError('native frame is short')
    magic, version, kind, size, sequence, crc = HEADER.unpack(raw[:HEADER.size])
    payload = raw[HEADER.size:]
    if ((magic,version) != (b'S328',1) or size != len(payload) or size > MAX_PAYLOAD
            or crc != binascii.crc32(payload, binascii.crc32(raw[:12])) & 0xffffffff):
        raise ValueError('native framing or CRC differs')
    return Frame(kind, sequence, payload)


def _expect(frame, kind, sequence):
    if type(frame) is not Frame or (frame.frame_type,frame.sequence) != (kind,sequence):
        raise ValueError('native frame order differs')
    return frame.payload


def parse_diagnostic_frame(frame, expected_stage):
    payload = _expect(frame, 134, 0)
    exact_bytes(payload, 8)
    stage, code = struct.unpack('<Ii', payload)
    if (stage != expected_stage or stage not in (0,1,2)
            or stage < 2 and code != 0 or stage == 2 and not -4095 <= code <= 64):
        raise ValueError('native diagnostic order or fields differ')
    return Diagnostic(stage, code)


class Codec:
    """The small facade consumed by resident IO and retained raw readers."""
    _CODEC = SimpleNamespace(HEADER=HEADER, encode_frame=encode_frame,
        decode_frame=decode_frame, _expect=_expect, _validate_nonce=_validate_nonce)
    _P333 = SimpleNamespace(parse_diagnostic_frame=parse_diagnostic_frame)
    ExchangeAudit = ExchangeAudit
    compute_open_tag = staticmethod(compute_open_tag)
    compute_ready_tag = staticmethod(compute_ready_tag)

    def __init__(self, namespace):
        if type(namespace) is not str or not re.fullmatch('p[0-9]{3,6}', namespace):
            raise ValueError('native namespace differs')
        self.boot_domain = ('S22PLUS-FYG8-'+namespace.upper()+'-AUTH-KERNEL-BOOT-ID-v2').encode()

    def decode_boot_id_frame(self, frame, key, run, nonce):
        payload = _expect(frame, 135, 2)
        exact_bytes(payload, 64)
        boot = exact_bytes(payload[:32], 32, nonzero=True)
        expected = tag(self.boot_domain, key, run, nonce, struct.pack('<I',2)+boot)
        if not hmac.compare_digest(payload[32:], expected):
            raise ValueError('native kernel boot authentication differs')
        return boot
