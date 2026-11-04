"""Fixed same-connection RAM evidence and one Download control; pure codec/H0 data."""
import hashlib
import hmac
import struct
import uuid

if __package__:
    from .prepare import require
else:
    from prepare import require

SCHEMA = 's22plus-mainline-debian-download-ram-v1'
DOMAIN = b'G0Q-DEBIAN-DOWNLOAD-RAM-v1'
CONTROL_MAGIC = b'G0QDCQ1\0'
ACK_MAGIC = b'G0QDCA1\0'
CONTROL_SIZE = 88
ACK_SIZE = 120


def declaration():
    return dict(schema=SCHEMA, control='download', connections=1, control_requests=1,
                restart2_calls=1, alternate_control=False, linux_storage=False,
                reboot_mode_magic=21, observer_deadline_ms=120000,
                physical_fallback=True, automatic_failure_recovery=False)


def tag(key, identity, kind, payload):
    require(len(key)==len(identity)==32, 'Download authentication binding')
    return hmac.new(key, DOMAIN+identity+bytes([kind])+payload, hashlib.sha256).digest()


def control(key, identity, nonce, boot_id):
    require(len(nonce)==32, 'Download nonce binding')
    boot=uuid.UUID(boot_id).bytes
    require(any(boot), 'empty Download boot identity')
    head=CONTROL_MAGIC+nonce+boot
    return head+tag(key,identity,2,head)


def verify_ack(data, key, identity, nonce, boot_id):
    require(len(data)==ACK_SIZE, 'Download acknowledgment length')
    body,auth=data[:-32],data[-32:]
    require(body==ACK_MAGIC+identity+nonce+uuid.UUID(boot_id).bytes and
            hmac.compare_digest(auth,tag(key,identity,3,body)), 'Download acknowledgment binding')
    return dict(status='AUTHENTICATED_DOWNLOAD_CONTROL_ACCEPTED',boot_id=boot_id,
                restart_completed=False,download_arrival_proved=False)


def frame_size(prefix):
    """Length framing only. Callers seal the complete bytes before authentication."""
    require(len(prefix)==384, 'Download base prefix length')
    size=struct.unpack_from('<I',prefix,248)[0]
    require(40<=size<=2*1024*1024, 'Download base FDT length')
    return len(prefix)+size
