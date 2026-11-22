"""Decode the MAX77705 observation record appended to the signed body."""
import struct

HEADER = 40
EVENTS = 48
EVENT = 12
SIZE = HEADER + EVENTS * EVENT
ADAPTER = ('ok', 'adapter-absent', 'adapter-open-failed', 'identity-mismatch')
KIND = ('begin', 'status', 'periodic', 'on-event')
CTRL1 = ('ok', 'timeout', 'proto', 'io', 'skipped', 'limit')
COMMAND_LIMIT = 32          # MX_COMMAND_LIMIT in max77705-usb-observe.h
COMMANDED = ('ok', 'timeout', 'proto', 'io')  # statuses that consumed a mailbox command
OPEN = 0x3f                 # COM_OPEN: D+ and D- switches open
COM_USB = 0x09
UIC_BITS = {7: 'APCmdResI', 6: 'SYSMsgI', 5: 'VBUSDetI', 4: 'VbADCI', 3: 'DCDTmoI', 1: 'CHGTypI', 0: 'UIDADCI'}


def _bits(value):
    return [name for bit, name in sorted(UIC_BITS.items(), reverse=True) if value & (1 << bit)]


def _order(total):
    """Slot order oldest to newest: first half kept from boot, second half a ring."""
    if total <= EVENTS:
        return list(range(total))
    half = EVENTS // 2
    start = half + (total - half) % half
    return list(range(half)) + [half + (start - half + i) % half for i in range(half)]


def decode(record):
    if len(record) != SIZE:
        raise ValueError('MAX77705 record size')
    version, adapter, err, number = struct.unpack_from('<IIII', record, 0)
    if version != 1 or adapter >= len(ADAPTER):
        raise ValueError('MAX77705 record header')
    total, = struct.unpack_from('<I', record, 28)
    out = {
        'adapter': ADAPTER[adapter], 'adapter_errno': err, 'adapter_number': number,
        'pmic_id': record[16], 'pmic_rev': record[17], 'usbc_hw': record[18], 'usbc_fw': record[19],
        'initial_uic': record[20], 'initial_uic_valid': bool(record[21]),
        'initial_uic_bits': _bits(record[20]),
        'fsa4480': {'read_fail_mask': record[22], 'reg00': record[23], 'reg04': record[24], 'reg05': record[25]},
        'events_total': total, 'commands': record[32], 'io_errors': record[33],
        'writes_rejected': record[34], 'elapsed_ms': struct.unpack_from('<I', record, 36)[0],
        'events': [],
    }
    for slot in _order(total):
        p = HEADER + slot * EVENT
        t, kind, uic, cc_int, bc, cc0, st1, ctrl1, status = struct.unpack_from('<IBBBBBBBB', record, p)
        if kind >= len(KIND) or status >= len(CTRL1):
            raise ValueError('MAX77705 event field')
        out['events'].append({'t_ms': t, 'kind': KIND[kind], 'uic': uic, 'uic_bits': _bits(uic),
                              'cc_int': cc_int, 'bc_status': bc, 'cc_status0': cc0,
                              'usbc_status1': st1,
                              'ctrl1': ctrl1 if status == 0 else None, 'ctrl1_status': CTRL1[status]})
    if out['writes_rejected']:
        raise ValueError('observer attempted a disallowed write')
    _consistent(out)
    return out


def _consistent(out):
    """Reject records the observer cannot produce; a signed record is still checked."""
    events = out['events']
    if out['commands'] > COMMAND_LIMIT:
        raise ValueError('MAX77705 command count exceeds the observer limit')
    if len(events) != min(out['events_total'], EVENTS):
        raise ValueError('MAX77705 event count differs from its total')
    if out['adapter'] != 'ok':
        if events or out['commands']:
            raise ValueError('MAX77705 events without an identified adapter')
        return
    if not events or events[0]['kind'] != 'begin' or any(e['kind'] == 'begin' for e in events[1:]):
        raise ValueError('MAX77705 record lacks exactly one leading begin event')
    if any(b['t_ms'] < a['t_ms'] for a, b in zip(events, events[1:])) or events[-1]['t_ms'] > out['elapsed_ms']:
        raise ValueError('MAX77705 event times are out of order')
    # Kind/status pairs the producer can emit (max77705-usb-observe.h mx_begin/mx_tick):
    # begin always attempts the first command; a status event is a skipped read;
    # on-event and periodic events attempt a command or hit the limit.
    for e in events:
        st, kind = e['ctrl1_status'], e['kind']
        if (kind == 'begin' and st not in COMMANDED or
                kind == 'status' and st != 'skipped' or
                kind in ('on-event', 'periodic') and st == 'skipped'):
            raise ValueError('MAX77705 event kind and read status disagree')
    if any(e['ctrl1_status'] == 'limit' for e in events) and out['commands'] != COMMAND_LIMIT:
        raise ValueError('MAX77705 limit status before the command limit')
    if sum(e['ctrl1_status'] in COMMANDED for e in events) > out['commands']:
        raise ValueError('MAX77705 commanded events exceed the command count')
    if out['events_total'] <= EVENTS and sum(e['ctrl1_status'] in COMMANDED for e in events) != out['commands']:
        raise ValueError('MAX77705 command count differs from its complete event list')


def verdict(decoded):
    """Coarse reading of one record; not causal. OPEN_* verdicts require a first read of COM_OPEN."""
    if decoded['adapter'] != 'ok':
        return 'NO_PROOF_' + decoded['adapter'].upper().replace('-', '_')
    reads = [e for e in decoded['events'] if e['ctrl1'] is not None]
    if not reads:
        return 'NO_PROOF_NO_CONTROL1_READ'
    first = reads[0]['ctrl1']
    if first == COM_USB:
        return 'INITIAL_COM_USB'
    if first != OPEN:
        return 'OTHER_INITIAL_CONTROL1'
    attach = next((e for e in decoded['events'] if 'VBUSDetI' in e['uic_bits'] or 'CHGTypI' in e['uic_bits']), None)
    if attach is None:
        return 'OPEN_NO_ATTACH_SEEN'
    after = [e['ctrl1'] for e in reads if e['t_ms'] >= attach['t_ms']]
    if not after:
        return 'OPEN_NO_READ_AFTER_ATTACH'
    if after[-1] == COM_USB:
        return 'OPEN_THEN_COM_USB_AFTER_ATTACH'
    if all(v == OPEN for v in after):
        return 'OPEN_UNCHANGED_AFTER_ATTACH'
    return 'OPEN_THEN_OTHER_AFTER_ATTACH'
