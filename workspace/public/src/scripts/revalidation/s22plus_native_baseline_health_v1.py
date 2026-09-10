"""Dormant native health profile; no transport opener or live F1 dispatch.

The future owner must bind the exact transfer/arrival before using this profile.
Raw replay proves console facts only, never the physical target or flashed image.
"""
import hashlib
import struct
import time

import s22plus_root_console_v1 as wire

SCHEMA = 's22plus-native-baseline-health-v1'
COMMAND = (
    b"printf 'NB1\\n'; /bin/busybox id -u; /bin/busybox id -g; "
    b"/bin/busybox awk '/^PPid:/{print $2}' /proc/$$/status; "
    b"test -r /proc/1/status && test -d /sys/devices && test -c /dev/null && "
    b"/bin/busybox awk '$2==\"/proc\"&&$3==\"proc\"{p=1} "
    b"$2==\"/sys\"&&$3==\"sysfs\"{s=1} "
    b"$2==\"/dev\"&&($3==\"tmpfs\"||$3==\"devtmpfs\"){d=1} "
    b"END{if(p&&s&&d)print \"MOUNTS\";else exit 1}' /proc/mounts && "
    b"printf 'COMPLETE\\000OUT\\n' && printf 'COMPLETE\\000ERR\\n' >&2"
)
STDOUT = b'NB1\n0\n0\n1\nMOUNTS\nCOMPLETE\0OUT\n'
STDERR = b'COMPLETE\0ERR\n'
COMMAND_BODY = wire.command(COMMAND, cwd=b'/', timeout_ms=15000)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run_console_checks(session, events, *, deadline):
    """Run one fixed EXEC and a post-terminal STATUS on an already owned session.

    CONTROL and its durable outer intent remain with the future transaction
    owner. On any error this helper stops the session; it never retries.
    """
    def wait(kind, sequence):
        while time.monotonic() < deadline:
            for k, n, body in events:
                if (k, n) == (kind, sequence):
                    return body
            events.extend(session.poll())
            time.sleep(.001)
        raise TimeoutError('native health original deadline')

    try:
        if not time.monotonic() < deadline <= time.monotonic() + 30:
            raise ValueError('native health budget differs')
        if session.sequence != 3 or session.requests:
            raise ValueError('native health requires a fresh declared arrival')
        wait(wire.READY, 2)
        sequence = session.send(wire.EXEC, COMMAND_BODY)
        wait(wire.EXIT, sequence)
        status = session.send(wire.STATUS)
        wait(wire.STATUS_REPLY, status)
        validate_console(session, events)
    except BaseException:
        session.stopped = True
        raise


def validate_console(session, events):
    """Require exact command, lossless streams, terminal, then fresh idle STATUS."""
    if session.ready != (1, 600000, 300000, 1048576, 767, 255, 0, 0):
        raise ValueError('native READY credentials/profile differ')
    requests = dict(session.requests)
    if requests.pop(5, None) not in (None, wire.CONTROL):
        raise ValueError('native departure request differs')
    if requests != {3: wire.EXEC, 4: wire.STATUS} or session.request_bodies[3] != COMMAND_BODY:
        raise ValueError('native health command/request profile differs')
    streams = {1: bytearray(), 2: bytearray()}
    terminal = status = None
    for kind, seq, body in events:
        if (kind, seq) == (wire.OUTPUT, 3):
            streams[struct.unpack('<I', body[8:12])[0]].extend(body[12:])
        elif (kind, seq) == (wire.EXIT, 3):
            terminal = struct.unpack('<7I', body)
        elif (kind, seq) == (wire.STATUS_REPLY, 4):
            if terminal is None:
                raise ValueError('STATUS precedes command terminal')
            status = struct.unpack('<8I', body)
    if (3 not in session.accepted or session.faulted or terminal is None
            or terminal[:4] != (3, 0, 0, 0) or terminal[5] != 0
            or bytes(streams[1]) != STDOUT or bytes(streams[2]) != STDERR):
        raise ValueError('native command health is unproved')
    if status != (3, 0, 0, 0, 0, len(STDOUT) + len(STDERR), 0, 3):
        raise ValueError('fresh idle STATUS differs')


def replay(observer, codec, rx, tx, key, *, arrival, previous=None):
    """Authenticate retained OPEN, kernel boot ID, preparation and console bytes.

    observer/codec are the source-bound candidate modules; no receipt boolean is
    accepted in place of their raw authentication. previous is arrival 1's
    independently rederived health receipt, not an operator-supplied boot ID.
    """
    if type(arrival) is not int or arrival not in (1, 2):
        raise ValueError('native arrival must be 1 or 2')
    if len(rx) > wire.RAW_CAPTURE_MAXIMUM or len(tx) > 65536:
        raise ValueError('native health raw bound exceeded')
    if observer.control.BOOT_ID_SEMANTIC != 'kernel-uuid-lowercase-ascii36-sha256-v2':
        raise ValueError('kernel boot identity semantic differs')
    io = observer.IO(codec, key, rx=rx, tx=tx)
    io.handshake()
    session, events = wire.replay(key, observer.RUN_ID, io.audit.nonce,
                                  rx[io.rpos:], tx[io.tpos:])
    validate_console(session, events)
    if session.requests != {3: wire.EXEC, 4: wire.STATUS, 5: wire.CONTROL}:
        raise ValueError('bounded departure request absent')
    receipt = dict(schema=SCHEMA, arrival=arrival, run_id_hex=observer.RUN_ID.hex(),
                   kernel_boot_identity_sha256=digest(io.audit.boot_id),
                   nonce_sha256=digest(io.audit.nonce), rx_sha256=digest(rx),
                   tx_sha256=digest(tx), console_healthy=True,
                   control_acceptance_observed=True, download_arrival_proved=False)
    return _validate_arrival(receipt, arrival, previous)


def _validate_arrival(receipt, arrival, previous):
    """Shared cross-boot join only; callers already authenticated their raw path."""
    if arrival == 1:
        if previous is not None:
            raise ValueError('first native arrival has no predecessor')
    elif (type(previous) is not dict or previous.get('schema') != SCHEMA
          or previous.get('arrival') != 1 or previous.get('console_healthy') is not True
          or previous.get('run_id_hex') != receipt['run_id_hex']
          or any(previous.get(field) == receipt[field] for field in
                 ('kernel_boot_identity_sha256', 'nonce_sha256'))
          or any(not isinstance(previous.get(field), str) or len(previous[field]) != 64
                 for field in ('kernel_boot_identity_sha256', 'nonce_sha256'))):
        raise ValueError('second native arrival freshness is unproved')
    return receipt


def replay_local(observer, codec, rx, tx, key, *, arrival, previous=None):
    """Local-display consumer with optional HUD, preserving legacy replay strictness.

    Full raw replay validates health EXEC3/STATUS4, optional HUD5 and CONTROL5/6.
    HUD results do not supply health. The owner separately proves transfer,
    physical target and Download arrival under its selected scoped exception.
    """
    if type(arrival) is not int or arrival not in (1, 2):
        raise ValueError('native arrival must be 1 or 2')
    if len(rx) > wire.RAW_CAPTURE_MAXIMUM or len(tx) > 65536:
        raise ValueError('native health raw bound exceeded')
    if (observer.control.BOOT_ID_SEMANTIC != 'kernel-uuid-lowercase-ascii36-sha256-v2'
            or observer.control.BOOT_RECEIPT_SEMANTIC != 'sha256-of-boot-v2-wire-digest'):
        raise ValueError('local native boot identity semantics differ')
    proof = observer.replay_session(codec, rx, tx, key)
    observed = proof['local_display']
    if (proof.get('proved') is not True or observed.get('native_health_proved') is not True
            or observed.get('control_acceptance_observed') is not True):
        raise ValueError('local native health and CONTROL are unproved')
    receipt = dict(schema=SCHEMA, arrival=arrival, run_id_hex=observer.RUN_ID.hex(),
        kernel_boot_identity_sha256=observed['kernel_boot_identity_sha256'],
        nonce_sha256=observed['nonce_sha256'], rx_sha256=digest(rx), tx_sha256=digest(tx),
        console_healthy=True, control_acceptance_observed=True, download_arrival_proved=False)
    return _validate_arrival(receipt, arrival, previous)
