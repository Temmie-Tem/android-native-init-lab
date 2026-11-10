"""Project independently authenticated UDC records from an offline FYG8 snapshot."""
import argparse
import hmac
import json
from pathlib import Path
import struct

MAGIC = b'G0QUDC01'
SIZE = 128
DUE_MS = (7000, 17000, 27000, 60000, 90000, 119000)
STATES = ('not attached', 'attached', 'powered', 'reconnecting', 'unauthenticated',
          'default', 'addressed', 'configured', 'suspended')
MAX_PAYLOAD = 2 * 1024**2 - 16


def record(frame, candidate, key):
    if len(frame) != SIZE or frame[:8] != MAGIC or frame[8:24] != candidate:
        raise ValueError('wrong frame identity or size')
    if not hmac.compare_digest(frame[-32:], hmac.digest(key, frame[:-32], 'sha256')):
        raise ValueError('failed authentication')
    start, end, result = struct.unpack_from('<IIi', frame, 40)
    seen, count = struct.unpack_from('<II', frame, 88)
    if not 0 < seen < 1 << len(DUE_MS) or count > 2:
        raise ValueError('invalid observation mask or bind count')
    samples = []
    latest = 0
    for i, due in enumerate(DUE_MS):
        ms, state = struct.unpack_from('<Ih', frame, 52 + i * 6)
        if seen & (1 << i):
            # jiffy rounding can fire before the nominal millisecond. Retain
            # the measured time; the scheduled time is only the row label.
            if not latest < ms < 120000:
                raise ValueError('invalid or unordered sample time')
            name = {-19: 'UDC absent', -16: 'UDC list busy'}.get(state)
            if name is None:
                if not 0 <= state < len(STATES):
                    raise ValueError('unknown UDC state')
                name = STATES[state]
            samples.append(dict(scheduled_ms=due, measured_ms=ms, state=name))
            latest = ms
        elif ms or state:
            raise ValueError('data in unsampled row')
    if start > latest or end > latest or (end and end < start):
        raise ValueError('bind/sample chronology differs')
    if count == 0 and (start or end or result) or not end and result:
        raise ValueError('bind return without a matching observation')
    if end and result != len(b'a600000.usb') and not -4095 <= result < 0:
        raise ValueError('invalid configfs return')
    status = ('repeated' if count == 2 else 'no callback observed' if not count else
              'callback entered' if not end else 'bound' if result > 0 else 'callback failed')
    for sample in samples:
        sample['after_successful_bind'] = status == 'bound' and sample['measured_ms'] > end
    return dict(boot_tag=frame[24:40].hex(), bind=status, bind_count=count,
                bind_start_ms=start if count else None, bind_end_ms=end or None,
                callback_result=result if end else None, samples=samples)


def project(snapshot, candidate, key):
    if len(snapshot) > MAX_PAYLOAD or len(key) != 32 or len(candidate) != 16:
        raise ValueError('snapshot or observation credentials outside bounds')
    frames, damaged, foreign = [], 0, 0
    offset = 0
    while (position := snapshot.find(MAGIC, offset)) >= 0:
        offset = position + 1
        data = snapshot[position:position + SIZE]
        if len(data) < SIZE:
            damaged += 1
        elif data[8:24] != candidate:
            foreign += 1
        else:
            try:
                frames.append(dict(offset=position, **record(data, candidate, key)))
            except ValueError:
                damaged += 1
    # A frame is cumulative. Never reconstruct a trajectory by joining frames
    # from a returned snapshot, which can contain multiple firmware attempts.
    return dict(frames=frames, damaged=damaged, foreign=foreign)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot', 'candidate', 'key'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    with args.snapshot.open('rb') as stream:
        raw = stream.read(MAX_PAYLOAD + 1)
    print(json.dumps(project(raw, args.candidate.read_bytes(), args.key.read_bytes()), indent=2))
