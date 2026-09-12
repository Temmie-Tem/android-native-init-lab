"""Per-sensor VALID sampling over the frozen V2 native source composition.

TRDY remains diagnostic data. Only the new profile changes its read predicate;
the V2 templates and their consumed native artifacts retain their bytes.
"""
from pathlib import Path

import s22plus_native_thermal_source_v2 as previous

resident = previous.resident
ROOT, NATIVE, PROFILE = previous.ROOT, previous.NATIVE, previous.PROFILE
THERMAL_PROFILE = 'g0q-r12-tsens-adc-temperature-v3'
SAMPLE_MAGIC, VIEW_MAGIC = 0x33525353, 0x33565253


def core_source():
    return resident.replace(previous.core_source(),
        b' || !(s->ready[i]&1U)', b'')


def sensor_map():
    return previous.sensor_map()


def provider_sources():
    files = previous.provider_sources()
    files['thermal_core.h'] = core_source()
    raw = files['s22plus_thermal_telemetry.c']
    first = raw.index(b'static void tsens_sample(')
    last = raw.index(b'static int sample_get(', first)
    sample = raw[first:last]
    sample = resident.replace(sample, b'ready[i]=!!(sample->ready[i]&1U);',
        b'/* V2 getter uses sensor VALID; TRDY is retained only as a diagnostic. */\n'
        b'                ready[i]=1;')
    for before, after in ((b'i,ready[2]', b'i,readable[2]'),
                          (b'ready[i]=1', b'readable[i]=1'),
                          (b'ready[i]?0:', b'readable[i]?0:'),
                          (b'!ready[sensor->bank]', b'!readable[sensor->bank]')):
        sample = resident.replace(sample, before, after)
    raw = raw[:first]+sample+raw[last:]
    if raw.count(b'S22THERM2') != 1 or raw.count(b'S22THERMD2') != 2:
        raise ValueError('frozen V2 provider dialect differs')
    files['s22plus_thermal_telemetry.c'] = raw.replace(b'S22THERM2', b'S22THERM3').replace(
        b'S22THERMD2', b'S22THERMD3')
    return files


def upgrade_wire(raw):
    raw = resident.replace(raw, previous.core_source(), core_source())
    for old, new in ((0x32525353, SAMPLE_MAGIC), (0x32565253, VIEW_MAGIC)):
        raw = resident.replace(raw, f'0x{old:08x}U'.encode(), f'0x{new:08x}U'.encode())
    return raw


def wire_source():
    return upgrade_wire(previous.wire_source())


def helper_template(identity):
    return upgrade_wire(previous.helper_template(identity))


def materialize_helper(identity, key):
    return upgrade_wire(previous.materialize_helper(identity, key))


def render_display(identity, modules):
    raw = upgrade_wire(previous.render_display(identity, modules))
    if raw.count(b'S22THERM2') != 2 or raw.count(b'RESIDENT_THERMAL2_FRAME') != 1:
        raise ValueError('frozen V2 collector/frame dialect differs')
    return raw.replace(b'S22THERM2', b'S22THERM3').replace(
        b'RESIDENT_THERMAL2_FRAME', b'RESIDENT_THERMAL3_FRAME')


def profile_contract():
    return dict(previous.profile_contract(), thermal_profile=THERMAL_PROFILE,
        temperature_validity='one selected STATUS word; VALID bit and signed temperature together',
        trdy_role='diagnostic only; no sampling precondition',
        private_ipc_sample_magic=SAMPLE_MAGIC, private_ipc_view_magic=VIEW_MAGIC)


def source_files():
    return tuple(sorted(set(previous.source_files()) | {Path(__file__)}))


def provider_files():
    return tuple(sorted(set(previous.provider_files()) | {Path(__file__)}))
