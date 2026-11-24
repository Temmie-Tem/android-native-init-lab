"""Decode the Stage 2 MAX77705 route record (max77705-usb-route.h) appended to the signed body."""
import struct

HEADER = 64
EVENTS = 48
EVENT = 16
SIZE = HEADER + EVENTS * EVENT
ADAPTER = ('ok', 'adapter-absent', 'adapter-open-failed', 'identity-mismatch')
KIND = ('begin', 'status', 'periodic', 'on-event', 'udc', 'prewrite', 'write', 'readback', 'deferred', 'request',
        'gap')
CTRL1 = ('ok', 'timeout', 'proto', 'io', 'skipped', 'limit')
GATE = ('pending', 'written', 'udc-left', 'preread-failed', 'not-open', 'vbus', 'chgtyp', 'cc', 'budget',
        'udc-unreadable', 'status-changed', 'stale')
UDC = {0: None, 1: 'not attached', 2: 'attached', 3: 'powered', 4: 'reconnecting', 5: 'unauthenticated',
       6: 'default', 7: 'addressed', 8: 'configured', 9: 'suspended', 0xfe: 'unknown', 0xff: 'read-error'}
COMMAND_LIMIT = 32          # MX_COMMAND_LIMIT
COMMANDED = ('ok', 'timeout', 'proto', 'io')
OPEN = 0x3f
COM_USB = 0x09
UIC_BITS = {7: 'APCmdResI', 6: 'SYSMsgI', 5: 'VBUSDetI', 4: 'VbADCI', 3: 'DCDTmoI', 1: 'CHGTypI', 0: 'UIDADCI'}
# A physical cable change at the IC: any UIC event other than the mailbox
# response, any CC interrupt, or a change of VBUSDet / ChgTyp / CCStat.
PHYSICAL_UIC = 0x7f
ENUMERATING = ('attached', 'powered', 'default', 'addressed', 'configured', 'suspended')
PRECONFIG = ('not attached', 'attached', 'powered', 'default', 'addressed')
PREFIX = EVENTS // 2


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
        raise ValueError('MAX77705 route record size')
    version, adapter, err, number = struct.unpack_from('<IIII', record, 0)
    if version != 2 or adapter >= len(ADAPTER) or record[40] >= len(GATE) or record[42] >= len(CTRL1):
        raise ValueError('MAX77705 route record header')
    if record[47] not in UDC:
        raise ValueError('MAX77705 route UDC state')
    total, = struct.unpack_from('<I', record, 28)
    write_ms, dwell_ms = struct.unpack_from('<II', record, 48)
    if any(record[56:64]) or record[26] or record[27]:
        raise ValueError('MAX77705 route reserved bytes')
    out = {
        'adapter': ADAPTER[adapter], 'adapter_errno': err, 'adapter_number': number,
        'pmic_id': record[16], 'pmic_rev': record[17], 'usbc_hw': record[18], 'usbc_fw': record[19],
        'initial_uic': record[20], 'initial_uic_valid': bool(record[21]),
        'initial_uic_bits': _bits(record[20]),
        'fsa4480': {'read_fail_mask': record[22], 'reg00': record[23], 'reg04': record[24], 'reg05': record[25]},
        'events_total': total, 'commands': record[32], 'io_errors': record[33],
        'writes_rejected': record[34], 'route_writes': record[35],
        'elapsed_ms': struct.unpack_from('<I', record, 36)[0],
        'gate': GATE[record[40]], 'prewrite_ctrl1': record[41], 'write_status': CTRL1[record[42]],
        'write_echo': record[43], 'write_data': record[44], 'begin_bc_status': record[45],
        'begin_cc_status0': record[46], 'udc_last': UDC[record[47]],
        'write_ms': write_ms, 'dwell_start_ms': dwell_ms,
        'events': [],
    }
    if total < EVENTS and any(record[HEADER + total * EVENT:]):
        raise ValueError('MAX77705 route unused event slots are not empty')
    for slot in _order(total):
        p = HEADER + slot * EVENT
        t, kind, uic, cc_int, bc, cc0, st1, ctrl1, status, udc = struct.unpack_from('<IBBBBBBBBB', record, p)
        if kind >= len(KIND) or status >= len(CTRL1) or udc not in UDC or any(record[p + 13:p + 16]):
            raise ValueError('MAX77705 route event field')
        out['events'].append({'t_ms': t, 'kind': KIND[kind], 'uic': uic, 'uic_bits': _bits(uic),
                              'cc_int': cc_int, 'bc_status': bc, 'cc_status0': cc0, 'usbc_status1': st1,
                              'ctrl1': ctrl1 if (status == 0 and KIND[kind] != 'write') else None,
                              'written': ctrl1 if KIND[kind] == 'write' else None,
                              'ctrl1_status': CTRL1[status], 'udc': UDC[udc], 'raw': ctrl1})
    if out['writes_rejected']:
        raise ValueError('observer attempted a disallowed write')
    _consistent(out)
    for e in out['events']:
        del e['raw']
    return out


def _consistent(out):
    """Reject records the producer cannot emit; a signed record is still checked."""
    events = out['events']
    if out['commands'] > COMMAND_LIMIT:
        raise ValueError('MAX77705 command count exceeds the observer limit')
    if len(events) != min(out['events_total'], EVENTS):
        raise ValueError('MAX77705 event count differs from its total')
    if out['route_writes'] > 1:
        raise ValueError('more than one route write')
    if out['adapter'] != 'ok':
        if events or out['commands'] or out['gate'] != 'pending' or out['route_writes']:
            raise ValueError('MAX77705 events without an identified adapter')
        return
    if not events or events[0]['kind'] != 'begin' or any(e['kind'] == 'begin' for e in events[1:]):
        raise ValueError('MAX77705 record lacks exactly one leading begin event')
    if any(b['t_ms'] < a['t_ms'] for a, b in zip(events, events[1:])) or events[-1]['t_ms'] > out['elapsed_ms']:
        raise ValueError('MAX77705 event times are out of order')
    for e in events:
        st, kind = e['ctrl1_status'], e['kind']
        if (kind in ('begin', 'prewrite', 'write') and st not in COMMANDED or
                kind in ('status', 'udc', 'gap') and st != 'skipped' or
                kind in ('on-event', 'periodic', 'readback', 'deferred', 'request') and st == 'skipped'):
            raise ValueError('MAX77705 event kind and read status disagree')
        if kind == 'write' and e['written'] != COM_USB:
            raise ValueError('MAX77705 route write value differs')
    _udc_sequence(out)
    if any(e['kind'] == 'request' for e in events[:-1]):
        raise ValueError('MAX77705 request read is not the final event')
    for kind in ('prewrite', 'write', 'readback', 'request'):
        if sum(e['kind'] == kind for e in events) > 1:
            raise ValueError('MAX77705 single-shot event repeated: ' + kind)
    writes = [e for e in events if e['kind'] == 'write']
    written = out['gate'] == 'written'
    if out['route_writes'] != int(written):
        raise ValueError('MAX77705 gate and route write count disagree')
    if written:
        if out['prewrite_ctrl1'] != OPEN or not out['write_ms'] or not out['dwell_start_ms']:
            raise ValueError('MAX77705 written gate without its preconditions')
        if out['events_total'] <= EVENTS and not writes:
            raise ValueError('MAX77705 route write event missing')
        if writes and (writes[0]['ctrl1_status'] != out['write_status'] or writes[0]['t_ms'] < out['write_ms']):
            raise ValueError('MAX77705 route write event disagrees with the header')
        # The producer writes only with the UDC at "not attached" around its
        # final sample, so the pre-read and the write carry that state.
        if any(e['kind'] in ('prewrite', 'write') and e['udc'] != 'not attached' for e in events):
            raise ValueError('MAX77705 route write without a not-attached UDC')
        if out['write_status'] == 'ok' and out['write_echo'] != 0x06:
            raise ValueError('MAX77705 route write acknowledged without its echo')
        if out['dwell_start_ms'] + 3000 > out['write_ms']:
            raise ValueError('MAX77705 route write before the dwell elapsed')
    elif writes or out['write_ms'] or out['write_status'] != 'ok' or out['write_echo'] or out['write_data']:
        raise ValueError('MAX77705 route write fields without a written gate')
    if any(e['kind'] == 'readback' for e in events) and not written:
        raise ValueError('MAX77705 readback without a write')
    if any(e['ctrl1_status'] == 'limit' for e in events) and out['commands'] != COMMAND_LIMIT:
        raise ValueError('MAX77705 limit status before the command limit')
    if sum(e['ctrl1_status'] in COMMANDED for e in events) > out['commands']:
        raise ValueError('MAX77705 commanded events exceed the command count')
    if out['events_total'] <= EVENTS and sum(e['ctrl1_status'] in COMMANDED for e in events) != out['commands']:
        raise ValueError('MAX77705 command count differs from its complete event list')
    _grammar(out)


def _grammar(out):
    """The producer's event grammar (max77705-usb-route.h), beyond kind/status."""
    events = out['events']
    if out['pmic_id'] != 0x15 or out['pmic_rev'] & 7 != 0x02:
        raise ValueError('MAX77705 identity gate passed without its identity')
    if events[0]['udc'] is not None:
        raise ValueError('MAX77705 begin carries a UDC state')
    for e in events:
        result, kind = e['ctrl1_status'], e['kind']
        # Mailbox encoding: an answered command saw APCmdResI; a failed or
        # skipped read leaves the raw value zero (the write keeps its payload).
        if result in ('ok', 'proto') and not e['uic'] & 0x80:
            raise ValueError('MAX77705 answered command without its response flag')
        if kind != 'write' and result != 'ok' and e['raw']:
            raise ValueError('MAX77705 failed read carries a value')
        if kind != 'begin' and kind in ('periodic', 'prewrite', 'write', 'readback', 'deferred', 'udc') and e['cc_int']:
            raise ValueError('MAX77705 event carries a CC interrupt it never reads')
    if len(events) > 1 and events[-1]['kind'] not in ('request', 'gap'):
        raise ValueError('MAX77705 record does not end at the request')
    if out['adapter_errno']:
        raise ValueError('MAX77705 identified adapter with an error')
    if out['udc_last'] != (events[-1]['udc'] if len(events) > 1 else None):
        raise ValueError('MAX77705 final UDC state differs from the last event')
    if len(events) > 1 and events[-1]['kind'] == 'gap' and not out['io_errors']:
        raise ValueError('MAX77705 terminal gap without an I/O error')
    if out['events_total'] > EVENTS:
        return      # scheduler state across the overwritten middle is unknown
    pending = False
    for i, e in enumerate(events):
        kind = e['kind']
        if kind == 'deferred' and not pending:
            raise ValueError('MAX77705 deferred read without a pending change')
        # Only the gate's own abort (gate 'status-changed', right after the
        # pre-read) leaves no deferred read pending.
        if kind == 'status' and not (out['gate'] == 'status-changed' and events[i - 1]['kind'] == 'prewrite'):
            pending = True
        elif kind in ('on-event', 'deferred', 'readback'):
            pending = False
    if out['gate'] != 'written':
        return
    index = next((i for i, e in enumerate(events) if e['kind'] == 'write'), None)
    if index is None:
        return                                      # dropped; the verdict handles it
    pre = events[index - 1] if index else None
    if (pre is None or pre['kind'] != 'prewrite' or pre['ctrl1_status'] != 'ok' or pre['ctrl1'] != OPEN or
            pre['uic'] & PHYSICAL_UIC or out['prewrite_ctrl1'] != OPEN):
        raise ValueError('MAX77705 route write without its successful pre-read')
    w = events[index]
    if not (w['bc_status'] & 0x80 and w['bc_status'] & 0x03 in (1, 2) and w['cc_status0'] & 0x07 == 1):
        raise ValueError('MAX77705 route write outside its admitted status')
    for e in events[:index - 1]:
        if (e['kind'] in ('on-event', 'status', 'gap') or e['uic'] & PHYSICAL_UIC or
                (e['kind'] != 'begin' and e['cc_int']) or e['udc'] not in (None, 'not attached')):
            raise ValueError('MAX77705 route write after an IC change or UDC departure')
    if any(e['kind'] == 'readback' for e in events[:index]):
        raise ValueError('MAX77705 readback before the write')


def _udc_sequence(out):
    """The producer samples the UDC once per tick. A changed state is carried
    first by that tick's IC-change event or by a dedicated 'udc' event; every
    other event repeats the previous state. Only the request re-samples it.
    Checked within each contiguous run (the kept prefix and the ring tail)."""
    events = out['events']
    runs = [events] if out['events_total'] <= EVENTS else [events[:PREFIX], events[PREFIX:]]
    for run in runs:
        for prev, e in zip(run, run[1:]):
            if e['kind'] == 'udc':
                if e['udc'] == prev['udc'] or e['udc'] is None:
                    raise ValueError('MAX77705 udc event without a state change')
            elif e['kind'] not in ('on-event', 'status', 'gap', 'request') and e['udc'] != prev['udc']:
                raise ValueError('MAX77705 UDC state changed without its udc event')
    if any(e['kind'] == 'udc' and (e['uic'] or e['cc_int']) for e in events):
        raise ValueError('MAX77705 udc event carries interrupt flags')
    # An IC-change event exists only because of a non-mailbox flag or a change
    # in any of the three status bytes: the producer's own comparison.
    for run in runs:
        for prev, e in zip(run, run[1:]):
            if e['kind'] in ('on-event', 'status') and not (
                    e['uic'] & PHYSICAL_UIC or e['cc_int'] or
                    any(prev[k] != e[k] for k in ('bc_status', 'cc_status0', 'usbc_status1'))):
                raise ValueError('MAX77705 change event without a change')
            # These follow an unchanged IC sample, so they repeat its status.
            if e['kind'] in ('udc', 'periodic', 'readback', 'deferred', 'prewrite', 'write') and any(
                    prev[k] != e[k] for k in ('bc_status', 'cc_status0', 'usbc_status1')):
                raise ValueError('MAX77705 status changed without a change event')


def _physical(prev, e):
    if e['uic'] & PHYSICAL_UIC or e['cc_int']:
        return True
    return ((prev['bc_status'] ^ e['bc_status']) & 0x83 or (prev['cc_status0'] ^ e['cc_status0']) & 0x07)


def verdict(decoded):
    """One reading of one boot; the intervention is causal only within this record.

    ROUTE_CONFIGURED_WITHOUT_REPLUG: COM_USB written and acknowledged, read back,
    and the UDC reached "configured" before any physical change at the IC.
    """
    if decoded['adapter'] != 'ok':
        return 'NO_PROOF_' + decoded['adapter'].upper().replace('-', '_')
    events, gate = decoded['events'], decoded['gate']
    reads = [e for e in events if e['ctrl1'] is not None]
    if not reads:
        return 'NO_PROOF_NO_CONTROL1_READ'
    dropped = decoded['events_total'] > EVENTS
    if gate == 'udc-left':
        return 'EVENTS_DROPPED' if dropped else 'ENUMERATED_BEFORE_WRITE'
    if gate == 'not-open':
        return 'SKIP_' + ('INITIAL_COM_USB' if decoded['prewrite_ctrl1'] == COM_USB else 'PREWRITE_NOT_OPEN')
    if gate != 'written':
        return 'SKIP_' + gate.upper().replace('-', '_')
    if decoded['write_status'] != 'ok':
        return 'ROUTE_WRITE_FAILED'
    if dropped:
        # Every written-route verdict depends on the order of events after the
        # write; with the middle overwritten that order is unknown.
        return 'EVENTS_DROPPED'
    index = next((i for i, e in enumerate(events) if e['kind'] == 'write'), None)
    if index is None:
        return 'EVENTS_DROPPED'
    after = events[index + 1:]
    readback = next((e for e in after if e['ctrl1'] is not None), None)
    if readback is None:
        return 'EVENTS_DROPPED' if dropped else 'ROUTE_NO_READBACK'
    # Scan from the write event itself (its mailbox polls read UIC_INT),
    # comparing status with the pre-write sample.
    prev = events[index - 1] if index else events[index]
    physical = left = configured = gap = None
    for i, e in enumerate(events[index:], index):
        if physical is None and _physical(prev, e):
            physical = i
        if gap is None and e['kind'] == 'gap':
            gap = i
        if left is None and e['udc'] in ENUMERATING:
            left = i
        if configured is None and e['udc'] == 'configured':
            configured = i
        prev = e
    # The cable session the write acted on ends at the first physical change
    # or coverage gap. Switch reads after that belong to a later session.
    first_change = min(i for i in (physical, gap, len(events)) if i is not None)
    session = [e['ctrl1'] for e in events[index + 1:first_change] if e['ctrl1'] is not None]
    if any(v != COM_USB for v in session):
        return 'ROUTE_WRITE_NOT_HELD'
    if not session:
        return 'ROUTE_NO_READBACK'          # the write's own session has no switch read
    if configured is not None and configured < first_change:
        return 'ROUTE_CONFIGURED_WITHOUT_REPLUG'
    if configured is not None:
        if gap is not None and gap == first_change and configured > gap:
            return 'ROUTE_COVERAGE_GAP'
        # After the write's session, count only a new configuration inside one
        # new attachment run. A run starts on a clean (non-gap) sample with
        # VBUS and a CC sink that follows a sampled VBUS loss or carries a
        # VBUSDetI edge. A gap, a CC loss or a VBUS loss ends it; a new VBUS
        # edge restarts it. Inside the run, a pre-configuration UDC state must
        # be sampled after the start event, then 'configured' in a later event.
        # A late CHGTypI or other flag without a VBUS edge does not end a run.
        detached = run = fresh = False
        for e in events[first_change:]:
            if e['kind'] == 'gap':
                detached = run = fresh = False
                continue
            vbus, sink = e['bc_status'] & 0x80, e['cc_status0'] & 0x07 == 1
            if not vbus:
                detached, run, fresh = True, False, False
                continue
            if not sink:
                # CC may settle after VBUS returns: a detach seen before the
                # run started stays valid; a CC loss inside a run ends it.
                if run:
                    detached = False
                run = fresh = False
                continue
            if e['uic'] & 0x20 or (detached and not run):
                detached, run, fresh = False, True, False
                continue
            if not run:
                continue
            if e['udc'] in PRECONFIG:
                fresh = True
            elif e['udc'] == 'configured' and fresh:
                return 'ROUTE_CONFIGURED_AFTER_REPLUG'
        # Configured at the change itself, or after a change with no sampled
        # detach and reattach: the order is not established.
        return 'ROUTE_AMBIGUOUS_ORDER'
    if left is not None and left < first_change:
        return 'ROUTE_PARTIAL_ENUMERATION'
    return 'ROUTE_NO_ENUMERATION'
