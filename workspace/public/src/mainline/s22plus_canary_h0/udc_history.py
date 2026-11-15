"""Decode the optional Debian UDC history extension after base authentication."""
import errno
import hashlib
from pathlib import Path
import struct
import sys

if __package__:
    from ..s22plus_udc_observation_h0 import decode
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from mainline.s22plus_udc_observation_h0 import decode

SCHEMA = 's22plus-mainline-debian-udc-history-v1'
PROTOCOL = (b'G0Q-DEBIAN-UDC-HISTORY-v1', b'G0QUHQ1\0', b'G0QUHS1\0', 492)
PUBLICATIONS = ('no attempt', 'slot readback verified', 'header mapping failed',
                'invalid LOGM magic', 'cursor too short', 'header changed',
                'slot mapping failed', 'slot readback mismatch')


def credentials(binding):
    values = []
    for name, length in (('candidate', 16), ('key', 32)):
        pin = binding[name]
        value = Path(pin['path']).read_bytes()
        if len(value) != length or hashlib.sha256(value).hexdigest() != pin['sha256']:
            raise ValueError('retained observation credential differs')
        values.append(value)
    return values


def unpack(extension, binding, uptime):
    if len(extension) != 140:
        raise ValueError('UDC history extension length')
    error, = struct.unpack_from('<I', extension)
    if error == errno.ENOENT and not any(extension[4:]):
        return {'status': 'observer unavailable'}
    if error:
        raise ValueError('UDC observation read status')
    if not any(extension[4:]):
        return {'status': 'no sample yet'}
    record = decode.record(extension[4:132], *credentials(binding))
    attempt_ms, publication = struct.unpack_from('<II', extension, 132)
    times = [sample['measured_ms'] for sample in record['samples']]
    if (not any(extension[28:44]) or not 0 < publication < len(PUBLICATIONS)
            or attempt_ms not in times or times[-1] > uptime
            or (publication == 1 and attempt_ms != times[-1])):
        raise ValueError('UDC publication status or sample chronology')
    return dict(status='sampled', **record, publication=PUBLICATIONS[publication],
                publication_sample_ms=attempt_ms)
