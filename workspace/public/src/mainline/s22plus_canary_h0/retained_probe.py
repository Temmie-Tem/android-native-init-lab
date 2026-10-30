"""Finite deferred-probe observations; a record is occurrence, never causality."""
import hmac
from pathlib import Path
import re
import struct

BASE = 0x800200000
REGION = 0x200000
SLOT = 128
MAX_SLOTS = 4096
MAGIC = b'S22PRB9!'
DOMAIN = b'S22PLUS-MAINLINE-DEFERRED-PROBE-V9\0'
SCHEMA = 's22plus-mainline-retained-deferred-probe-v9'
HERE = Path(__file__).resolve().parent
FIXED = (
    'pre-basic-setup', 'post-driver-init', 'pre-regular-initcalls',
    'post-basic-setup', 'post-initramfs-wait', 'post-async-sync',
    'deferred-body-enter', 'post-deferred-debugfs', 'pre-first-trigger',
    'post-first-trigger', 'post-first-flush', 'pre-second-trigger',
    'post-second-trigger', 'post-second-flush', 'post-timeout-schedule-call',
    'deferred-pre-exit', 'phase-1-worker-enter', 'phase-1-worker-return',
    'phase-2-worker-enter', 'phase-2-worker-return')
POINTS = ('pre-pm-move-and-bus-probe', 'post-bus-probe',
          'pre-device-set-driver', 'pre-selected-callback', 'post-selected-callback')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def catalog(nodes):
    """Include compatible/reg nodes and ancestors, without status inference."""
    paths = set()
    for path, properties in nodes.items():
        if 'compatible' not in properties and 'reg' not in properties:
            continue
        while True:
            paths.add(path)
            if path == '/':
                break
            path = path.rsplit('/', 1)[0] or '/'
    return sorted(paths)


def stages(count, ordinals, paths):
    require(type(count) is int and 1 <= count <= 2045,
            'probe initcall table count differs')
    require(type(ordinals) is list and ordinals == sorted(set(ordinals)) and
            ordinals and all(type(i) is int and 0 <= i < count for i in ordinals),
            'probe sparse initcall ordinals differ')
    require(type(paths) is list and paths == sorted(set(paths)) and paths and
            all(type(p) is str and p.startswith('/') and len(p) <= 512 and
                re.fullmatch(r'/[A-Za-z0-9,._+@/#-]*', p) for p in paths),
            'probe node catalog differs')
    names = list(FIXED)
    names += [f'initcall-{i:04d}-{phase}' for i in ordinals for phase in ('enter', 'return')]
    names += [f'phase-{phase}:{path}:{point}' for phase in (1, 2)
              for path in paths + ['NO_OF', 'UNLISTED_OF'] for point in POINTS]
    require(len(names) <= MAX_SLOTS and len(names) == len(set(names)),
            'probe event catalog exceeds finite capacity')
    return dict(enumerate(names))


def configuration(candidate, key, count, ordinals, paths):
    require(type(candidate) is str and re.fullmatch('[0-9a-f]{64}', candidate) and
            type(key) is bytes and len(key) == 32, 'probe candidate/key differs')
    names = stages(count, ordinals, paths)
    frames = {}
    for event in names:
        prefix = (MAGIC + struct.pack('<II', 9, event) + bytes.fromhex(candidate) +
                  struct.pack('<III', len(names), len(paths), count) + bytes(36))
        frames[str(event)] = (prefix + hmac.digest(key, DOMAIN + prefix, 'sha256')).hex()
    return dict(schema=SCHEMA, candidate_id=candidate, base=BASE, region_size=REGION,
                slot_size=SLOT, span=len(names) * SLOT, initcall_count=count,
                initcall_ordinals=ordinals, node_paths=paths, frames=frames)


def validate(config, candidate, key):
    require(config == configuration(candidate, key, config.get('initcall_count'),
                                    config.get('initcall_ordinals'), config.get('node_paths')),
            'retained probe configuration differs')
    return config


def render(config):
    names = stages(config['initcall_count'], config['initcall_ordinals'], config['node_paths'])
    require(config['span'] == len(names) * SLOT and config['slot_size'] == SLOT and
            config['base'] == BASE and config['region_size'] == REGION and
            set(config['frames']) == {str(i) for i in names}, 'probe write scope differs')
    rows = []
    for i in names:
        frame = bytes.fromhex(config['frames'][str(i)])
        require(len(frame) == SLOT, 'probe frame size differs')
        rows.append('\t{' + ','.join(str(v) for v in frame) + '},')
    replacements = {
        '@COUNT@': str(config['initcall_count']), '@SLOTS@': str(len(names)),
        '@NODES_COUNT@': str(len(config['node_paths'])),
        '@ORDINAL_COUNT@': str(len(config['initcall_ordinals'])),
        '@ORDINALS@': ','.join(str(i) for i in config['initcall_ordinals']),
        '@PATHS@': '\n'.join('\t"' + p + '",' for p in config['node_paths']),
        '@FRAMES@': '\n'.join(rows)}
    result = (HERE / 'retained-probe-c.h').read_text()
    for key, value in replacements.items():
        result = result.replace(key, value)
    return result


def instrument_main(old, config):
    stages(config['initcall_count'], config['initcall_ordinals'], config['node_paths'])
    declaration = 'static void __init do_initcall_level(int level, char *command_line)\n'
    loop = ('\tfor (fn = initcall_levels[level]; fn < initcall_levels[level+1]; fn++)\n'
            '\t\tdo_one_initcall(initcall_from_entry(fn));\n')
    require('s22_retained_' not in old and old.count(declaration) == old.count(loop) == 1,
            'probe main source anchors differ')
    externs = ('extern void __init s22_retained_probe_mark(u32 event);\n'
               'extern void __init s22_retained_probe_initcall(initcall_entry_t *entry, u32 phase);\n'
               'extern void __init s22_retained_probe_prepare(void);\n'
               'extern void __init s22_retained_probe_finish(void);\n\n')
    result = old.replace(declaration, externs + declaration).replace(loop,
        '\tfor (fn = initcall_levels[level]; fn < initcall_levels[level+1]; fn++) {\n'
        '\t\ts22_retained_probe_initcall(fn, 0);\n'
        '\t\tdo_one_initcall(initcall_from_entry(fn));\n'
        '\t\ts22_retained_probe_initcall(fn, 1);\n\t}\n')
    sites = [('\tpage_alloc_init_late();\n', '\ts22_retained_probe_prepare();\n\ts22_retained_probe_mark(0);\n'),
             ('\tdriver_init();\n', '\ts22_retained_probe_mark(1);\n'),
             ('\tdo_basic_setup();\n', '\ts22_retained_probe_mark(3);\n'),
             ('\twait_for_initramfs();\n', '\ts22_retained_probe_mark(4);\n'),
             ('\tasync_synchronize_full();\n', '\ts22_retained_probe_mark(5);\n\ts22_retained_probe_finish();\n')]
    require(old.count('\tasync_synchronize_full();\n\n\tsystem_state = SYSTEM_FREEING_INITMEM;\n') == 1,
            'probe init lifetime boundary differs')
    for anchor, addition in sites:
        require(old.count(anchor) == 1, 'probe main milestone anchor differs')
        result = result.replace(anchor, anchor + addition)
    anchor = '\tchar *command_line;\n\n\tcommand_line = kzalloc(len, GFP_KERNEL);\n'
    require(old.count(anchor) == 1, 'probe preallocation anchor differs')
    return result.replace(anchor, anchor.replace('\tcommand_line =',
                                                '\ts22_retained_probe_mark(2);\n\tcommand_line ='))


def instrument_dd(old):
    require('s22_retained_' not in old and old.count('#include "power/power.h"\n') == 1,
            'probe dd source already instrumented')
    result = old.replace('#include "power/power.h"\n',
                         '#include "power/power.h"\n#include "s22-retained-probe.h"\n')
    changes = [
        ('\tstruct device_private *private;\n',
         '\tstruct device_private *private;\n\tu32 s22_worker_token, s22_device_token;\n'
         '\n\ts22_worker_token = s22_probe_hook(S22_WORK_ENTER, NULL, 0);\n'),
        ('\t\tdevice_pm_move_to_tail(dev);\n',
         '\t\ts22_device_token = s22_probe_hook(S22_DEVICE, dev, 0);\n\t\tdevice_pm_move_to_tail(dev);\n'),
        ('\t\tbus_probe_device(dev);\n',
         '\t\tbus_probe_device(dev);\n\t\ts22_probe_hook(S22_RETURN, NULL, s22_device_token);\n'),
        ('\tmutex_unlock(&deferred_probe_mutex);\n}\nstatic DECLARE_WORK',
         '\tmutex_unlock(&deferred_probe_mutex);\n\ts22_probe_hook(S22_WORK_RETURN, NULL, s22_worker_token);\n}\nstatic DECLARE_WORK'),
        ('\tdevice_set_driver(dev, drv);\n',
         '\ts22_probe_hook(S22_DEVICE, dev, 2);\n\tdevice_set_driver(dev, drv);\n'),
        ('static int deferred_probe_initcall(void)\n{\n',
         'static int deferred_probe_initcall(void)\n{\n\ts22_probe_hook(S22_ARM, NULL, 0);\n'),
        ('\tdriver_deferred_probe_enable = true;\n',
         '\ts22_probe_hook(S22_FIXED, NULL, 7);\n\tdriver_deferred_probe_enable = true;\n'
         '\ts22_probe_hook(S22_FIXED, NULL, 8);\n'),
        ('\tdriver_deferred_probe_trigger();\n\t/* Sort as many dependencies as possible before exiting initcalls */\n'
         '\tflush_work(&deferred_probe_work);\n\tinitcalls_done = true;\n',
         '\tdriver_deferred_probe_trigger();\n\ts22_probe_hook(S22_FIXED, NULL, 9);\n'
         '\t/* Sort as many dependencies as possible before exiting initcalls */\n'
         '\tflush_work(&deferred_probe_work);\n\ts22_probe_hook(S22_FIXED, NULL, 10);\n\tinitcalls_done = true;\n'),
        ('\t * that is optional\n\t */\n\tdriver_deferred_probe_trigger();\n\tflush_work(&deferred_probe_work);\n',
         '\t * that is optional\n\t */\n\ts22_probe_hook(S22_PHASE_TWO, NULL, 0);\n'
         '\tdriver_deferred_probe_trigger();\n\ts22_probe_hook(S22_FIXED, NULL, 12);\n'
         '\tflush_work(&deferred_probe_work);\n\ts22_probe_hook(S22_FIXED, NULL, 13);\n'),
        ('\t\t\tdriver_deferred_probe_timeout * HZ);\n',
         '\t\t\tdriver_deferred_probe_timeout * HZ);\n\t\ts22_probe_hook(S22_FIXED, NULL, 14);\n'),
        ('\treturn 0;\n}\nlate_initcall(deferred_probe_initcall);',
         '\ts22_probe_hook(S22_DISARM, NULL, 0);\n\treturn 0;\n}\nlate_initcall(deferred_probe_initcall);')]
    for before, after in changes:
        require(old.count(before) == 1, 'probe dd anchor differs: ' + before[:64])
        result = result.replace(before, after)
    before = ('\tif (dev->bus->probe)\n\t\tret = dev->bus->probe(dev);\n'
              '\telse if (drv->probe)\n\t\tret = drv->probe(dev);\n')
    after = ('\tif (dev->bus->probe) {\n'
             '\t\tu32 token = s22_probe_hook(S22_DEVICE, dev, 3);\n'
             '\t\tret = dev->bus->probe(dev);\n'
             '\t\ts22_probe_hook(S22_RETURN, NULL, token);\n'
             '\t} else if (drv->probe) {\n'
             '\t\tu32 token = s22_probe_hook(S22_DEVICE, dev, 3);\n'
             '\t\tret = drv->probe(dev);\n'
             '\t\ts22_probe_hook(S22_RETURN, NULL, token);\n\t}\n')
    require(old.count(before) == 1, 'probe actual callback branches differ')
    return result.replace(before, after)


def decode(data, candidate, key, config):
    require(type(data) is bytes and len(data) <= 4 * 1024 * 1024, 'retained capture exceeds bound')
    validate(config, candidate, key)
    names = stages(config['initcall_count'], config['initcall_ordinals'], config['node_paths'])
    expected = {event: bytes.fromhex(config['frames'][str(event)]) for event in names}
    found = {}; damaged = foreign = offset = 0
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
            if version != 9 or event not in names or not hmac.compare_digest(piece, expected[event]):
                damaged += 1
            else:
                found.setdefault(event, []).append(offset)
        offset += len(MAGIC)
    events = [dict(event=e, stage=names[e], offsets=o) for e, o in sorted(found.items())]
    return dict(schema='s22plus-mainline-retained-deferred-probe-result-v9',
                status='RETAINED_STAGE_OBSERVED' if events else 'NO_PROOF', events=events,
                record_count=sum(map(len, found.values())), observed_stages=[v['stage'] for v in events],
                damaged_candidates=damaged, foreign_candidates=foreign,
                initcall_count=config['initcall_count'], node_count=len(config['node_paths']),
                occurrence_scope='AT_LEAST_ONCE_IN_CANDIDATE_ATTEMPTS',
                phase_scope='PHASE_SAMPLED_AT_ENTRY_NOT_TRIGGER_PROVENANCE',
                same_boot_pair_proved=False, same_callback_pair_proved=False,
                unique_device_or_driver_proved=False, complete_retry_history=False,
                last_attempt_proved=False, stopped_at_last_record=False, reset_cause_proved=False,
                callback_success_proved=False, mainline_pid1=False,
                authenticated_usb=False, replay_authorized=False)
