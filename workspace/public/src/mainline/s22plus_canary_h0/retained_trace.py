"""Finite, candidate-bound regular-initcall records; occurrence is not success.

Ordinal labels are resolved against the qualified final ELF, never a prior
build's symbol addresses. All record bytes are generated on the host.
"""
import hmac
from pathlib import Path
import re
import struct

BASE = 0x800200000
REGION = 0x200000
SLOT = 128
MAX_SLOTS = 4096
FIXED_SLOTS = 6
MAX_INITCALLS = (MAX_SLOTS - FIXED_SLOTS) // 2
MAGIC = b'S22TRC8!'
DOMAIN = b'S22PLUS-MAINLINE-INITCALL-TRACE-V8\0'
SCHEMA = 's22plus-mainline-retained-initcall-trace-v8'
HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def event_count(count):
    require(type(count) is int and 1 <= count <= MAX_INITCALLS,
            'initcall count exceeds finite trace capacity')
    return 2 * count + FIXED_SLOTS


def stages(count):
    event_count(count)
    result = {0: 'pre-basic-setup', 1: 'post-driver-init', 2: 'pre-regular-initcalls',
              3: 'post-basic-setup', 4: 'post-initramfs-wait', 5: 'post-async-sync'}
    for ordinal in range(count):
        result[FIXED_SLOTS + 2 * ordinal] = f'initcall-{ordinal:04d}-enter'
        result[FIXED_SLOTS + 2 * ordinal + 1] = f'initcall-{ordinal:04d}-return'
    return result


def frame(candidate, key, event, count):
    require(re.fullmatch('[0-9a-f]{64}', candidate) is not None and
            type(key) is bytes and len(key) == 32 and
            type(event) is int and 0 <= event < event_count(count),
            'trace candidate/key/event differs')
    prefix = (MAGIC + struct.pack('<II', 8, event) + bytes.fromhex(candidate) +
              struct.pack('<I', count) + bytes(44))
    return prefix + hmac.digest(key, DOMAIN + prefix, 'sha256')


def configuration(candidate, key, count):
    events = stages(count)
    return dict(schema=SCHEMA, candidate_id=candidate, base=BASE,
                region_size=REGION, span=len(events) * SLOT, slot_size=SLOT,
                initcall_count=count,
                frames={str(event): frame(candidate, key, event, count).hex()
                        for event in events})


def validate(config, candidate, key):
    require(config == configuration(candidate, key, config.get('initcall_count')),
            'retained initcall trace configuration differs')
    return config


def render(config):
    count = config['initcall_count']
    require(config['span'] == event_count(count) * SLOT and
            config['base'] == BASE and config['region_size'] == REGION and
            config['slot_size'] == SLOT and
            set(config['frames']) == {str(i) for i in range(event_count(count))},
            'trace write scope differs')
    rows = []
    for event in range(event_count(count)):
        data = bytes.fromhex(config['frames'][str(event)])
        require(len(data) == SLOT, 'trace frame size differs')
        rows.append('\t{\n' + '\n'.join(
            '\t\t' + ','.join(str(x) for x in data[i:i + 16]) + ','
            for i in range(0, SLOT, 16)) + '\n\t},')
    return (HERE / 'retained-trace-c.h').read_text().replace(
        '@COUNT@', str(count)).replace('@FRAMES@', '\n'.join(rows))


def instrument_main(old, config):
    event_count(config['initcall_count'])
    declaration = 'static void __init do_initcall_level(int level, char *command_line)\n'
    loop = ('\tfor (fn = initcall_levels[level]; fn < initcall_levels[level+1]; fn++)\n'
            '\t\tdo_one_initcall(initcall_from_entry(fn));\n')
    replacement = ('\tfor (fn = initcall_levels[level]; fn < initcall_levels[level+1]; fn++) {\n'
                   '\t\ts22_retained_initcall(fn, 0);\n'
                   '\t\tdo_one_initcall(initcall_from_entry(fn));\n'
                   '\t\ts22_retained_initcall(fn, 1);\n\t}\n')
    sites = [('\tpage_alloc_init_late();\n', '\ts22_retained_trace(0);\n'),
             ('\tdriver_init();\n', '\ts22_retained_trace(1);\n'),
             ('\tchar *command_line;\n\n\tcommand_line = kzalloc(len, GFP_KERNEL);\n',
              None),
             ('\tdo_basic_setup();\n', '\ts22_retained_trace(3);\n'),
             ('\twait_for_initramfs();\n', '\ts22_retained_trace(4);\n'),
             ('\tasync_synchronize_full();\n', '\ts22_retained_trace(5);\n')]
    require('s22_retained_' not in old and 's22-retained-early-c.h' not in old and
            old.count(declaration) == 1 and old.count(loop) == 1 and
            all(old.count(anchor) == 1 for anchor, _ in sites) and
            old.count('\tpage_alloc_init_late();\n\n\tdo_basic_setup();\n') == 1 and
            old.count('\tasync_synchronize_full();\n\n\tsystem_state = SYSTEM_FREEING_INITMEM;\n') == 1 and
            old.count('\tkernel_init_freeable();\n') == 1 and
            old.index('\tkernel_init_freeable();\n') < old.index('\tasync_synchronize_full();\n'),
            'trace source anchors or init lifetime differ')
    result = old.replace(declaration, '#include "s22-retained-early-c.h"\n\n' + declaration)
    result = result.replace(loop, replacement)
    for anchor, addition in sites:
        if addition is None:
            result = result.replace(anchor, anchor.replace(
                '\tcommand_line =', '\ts22_retained_trace(2);\n\tcommand_line ='))
        else:
            result = result.replace(anchor, anchor + addition)
    return result


def decode(data, candidate, key, config):
    require(type(data) is bytes and len(data) <= 4 * 1024 * 1024,
            'retained capture exceeds bound')
    validate(config, candidate, key)
    names = stages(config['initcall_count'])
    expected = {event: bytes.fromhex(config['frames'][str(event)]) for event in names}
    found = {}
    damaged = foreign = 0
    offset = 0
    while True:
        offset = data.find(MAGIC, offset)
        if offset < 0:
            break
        piece = data[offset:offset + SLOT]
        if len(piece) != SLOT:
            damaged += 1
        elif piece[16:48] != bytes.fromhex(candidate):
            foreign += 1
        else:
            version, event = struct.unpack_from('<II', piece, 8)
            if version != 8 or event not in names or not hmac.compare_digest(piece, expected[event]):
                damaged += 1
            else:
                found.setdefault(event, []).append(offset)
        offset += len(MAGIC)
    # Group offsets so even a maximum-size duplicate-filled capture fits the
    # existing durable-record bound. Repeated records never count boots.
    events = [dict(event=event, stage=names[event], offsets=offsets)
              for event, offsets in sorted(found.items())]
    return dict(schema='s22plus-mainline-retained-initcall-trace-result-v8',
                status='RETAINED_STAGE_OBSERVED' if events else 'NO_PROOF',
                events=events, record_count=sum(len(v) for v in found.values()),
                observed_stages=[row['stage'] for row in events],
                damaged_candidates=damaged, foreign_candidates=foreign,
                initcall_count=config['initcall_count'],
                occurrence_scope='AT_LEAST_ONCE_IN_CANDIDATE_ATTEMPTS',
                same_boot_pair_proved=False, last_attempt_proved=False,
                stopped_at_last_record=False, reset_cause_proved=False,
                initcall_success_proved=False, mainline_pid1=False,
                authenticated_usb=False, replay_authorized=False)
