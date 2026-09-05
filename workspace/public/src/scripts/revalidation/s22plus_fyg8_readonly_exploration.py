"""Dormant H0 named exploration catalog for a fresh post-P342 candidate.

No transport, lease, approval, artifact publication or device entry point.
Keep the authenticated three-command session: identity, selected read-only
query, run-bound nonce. Existing callers still own timeout/output bounds,
raw capture, fresh boot binding, one-shot intent and mandatory recovery.
"""
from __future__ import annotations

import re
from types import MappingProxyType


# Fixed files only; no caller path, shell text, glob, device/block read or write.
# head gives useful small snapshots without consuming the full output budget.
CATALOG = MappingProxyType({
    'kernel': b'/bin/busybox uname -a',
    'processes': b'/bin/busybox ps',
    'mounts': b'/bin/busybox head -c 8192 /proc/mounts',
    'memory': b'/bin/busybox head -c 4096 /proc/meminfo',
    'usb-state': b'/bin/busybox cat /sys/class/udc/a600000.dwc3/state',
})
IDENTITY = b'/bin/busybox id'
NONCE_PREFIX = b'/bin/busybox echo P328-NONCE '
RUN_RE = re.compile(r'c[0-9a-f]{31}\Z')


def command(action: str) -> bytes:
    if type(action) is not str or action not in CATALOG:
        raise ValueError('unknown named exploration action')
    return CATALOG[action]


def session_commands(action: str, run_id_hex: str) -> tuple[bytes, bytes, bytes]:
    selected = command(action)
    if type(run_id_hex) is not str or RUN_RE.fullmatch(run_id_hex) is None:
        raise ValueError('exploration requires an exact run ID')
    return IDENTITY, selected, NONCE_PREFIX + run_id_hex.encode('ascii')


def command_allowed(sequence: int, payload: bytes, run_id_hex: str) -> bool:
    """Host mirror of the device validator; no execution or authority."""
    identity, _, nonce = session_commands('kernel', run_id_hex)
    if type(sequence) is not int or type(payload) is not bytes:
        return False
    return ((sequence == 3 and payload == identity)
            or (sequence == 4 and payload in CATALOG.values())
            or (sequence == 5 and payload == nonce))


def _literal(payload: bytes) -> str:
    # All values are internal. Deliberately no general shell/C quoting API.
    value = payload.decode('ascii')
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 /._-' for c in value):
        raise ValueError('catalog contains unexpected syntax')
    return '"' + value + '"'


def validator_source() -> bytes:
    """Use existing command_1/command_3 and byte comparator, no new protocol."""
    tests = [
        '(length == sizeof(' + _literal(payload) + ') - 1U && '
        'p260_bytes_equal((const char *)command, ' + _literal(payload) + ', length))'
        for payload in CATALOG.values()
    ]
    return ('''static int p335_command_valid(
    uint32_t sequence, const uint8_t *command, uint16_t length) {
    if (command == NULL) return 0;
    if (sequence == 3U)
        return length == sizeof(p335_command_1) - 1U
            && p260_bytes_equal((const char *)command, p335_command_1, length);
    if (sequence == 4U)
        return ''' + '\n            || '.join(tests) + ''';
    if (sequence == 5U)
        return length == sizeof(p335_command_3) - 1U
            && p260_bytes_equal((const char *)command, p335_command_3, length);
    return 0;
}''').encode('ascii')


def transform_validator(helper: bytes, run_id_hex: str) -> bytes:
    """H0 source transform; caller must package only a qualified fresh ID.

    Leaves framing, HMAC, child execution and cleanup byte-identical. Remove
    only the now-unused command_2 constant to preserve -Werror builds.
    """
    identity, default, nonce = session_commands('kernel', run_id_hex)
    def encoded(value):
        return '"' + ''.join(f'\\x{byte:02x}' for byte in value) + '"'
    for name, value in ((1, identity), (2, default), (3, nonce)):
        anchor = f'static const char p335_command_{name}[] = {encoded(value)};'.encode()
        if helper.count(anchor) != 1:
            raise ValueError('runtime command constants differ')
    start = helper.index(b'static int p335_command_valid(')
    end = helper.index(b'\n}', start) + 2
    original = helper[start:end]
    for anchor in (b'sequence == 3U', b'sequence == 4U', b'sequence == 5U',
                   b'p335_command_1', b'p335_command_2', b'p335_command_3', b'p260_bytes_equal'):
        if original.count(anchor) < 1:
            raise ValueError('runtime validator shape differs')
    result = helper[:start] + validator_source() + helper[end:]
    unused = f'static const char p335_command_2[] = {encoded(default)};\n'.encode()
    if result.count(unused) != 1:
        raise ValueError('runtime default constant differs')
    return result.replace(unused, b'', 1)


def select_private_codec(module, action: str) -> tuple[bytes, bytes, bytes]:
    """Bind a newly private codec's existing producer/parser to one named tuple.

    The live integration must provide its own fresh private codec per action;
    never call this on an imported shared live observer. No exchange occurs.
    """
    import sys
    if any(value is module for value in sys.modules.values()):
        raise ValueError('exploration codec must not be a shared imported module')
    if getattr(module, '_exploration_action', None) is not None:
        raise ValueError('exploration codec selection is one-use')
    selected = session_commands(action, module.runtime.P335_RUN_ID.hex())
    function = module._exchange_one
    if function.__globals__ is not vars(module):
        raise ValueError('codec exchange uses another namespace')
    if tuple(module.DEFAULT_COMMANDS) != session_commands('kernel', module.runtime.P335_RUN_ID.hex()):
        raise ValueError('codec baseline command tuple differs')
    module.DEFAULT_COMMANDS = selected
    module._exploration_action = action
    return selected
