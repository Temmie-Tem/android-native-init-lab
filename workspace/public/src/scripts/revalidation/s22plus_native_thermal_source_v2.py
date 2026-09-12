"""CPU/GPU/SoC-DDR thermal composition over frozen P387/P389 source inputs.

Only the new E gets the extended private IPC. The resident control wire, fixed
health command and one-shot role/recovery owner are unchanged.
"""
from pathlib import Path
import re

import s22plus_native_thermal_source_v1 as previous

resident = previous.resident
ROOT, NATIVE, PROFILE = resident.ROOT, resident.NATIVE, resident.PROFILE
THERMAL_PROFILE = 'g0q-r12-tsens-adc-temperature-v2'
TEMPLATES = NATIVE/'s22plus_thermal_v2'
PROVIDER = ROOT/'workspace/public/src/kernel-modules/s22plus_thermal_telemetry_v1'
PARTS = ('core.inc.h','provider-map.inc.c.in','provider-probe.inc.c.in',
         'provider-sample.inc.c.in','collect.inc.c.in','ipc-validate.inc.c.in',
         'record.inc.c.in','render.inc.c.in')


def read(name):
    if name not in PARTS: raise ValueError('unknown thermal V2 source')
    return resident.common._read(TEMPLATES/name)


def core_source():
    return resident.replace(resident.common._read(previous.CORE),b'#endif\n',read('core.inc.h')+b'\n#endif\n')


def sensor_map():
    rows=[(name.decode(),int(bank),int(sensor)) for name,bank,sensor in
          re.findall(rb'\{"([a-z0-9-]+)",(\d+),(\d+)\}',core_source())]
    if len(rows)!=16 or len({(b,s) for _,b,s in rows})!=16 or any(b>1 or s>15 for _,b,s in rows):
        raise ValueError('thermal sensor declaration differs')
    return tuple(rows)


def provider_sources():
    raw = resident.common._read(PROVIDER/'s22plus_thermal_telemetry.c')
    raw = resident.section(raw,b'static int exact_cpu_map(',b'static int thermal_probe(',read('provider-map.inc.c.in'))
    raw = resident.section(raw,b'static int thermal_probe(',b'static int thermal_remove(',read('provider-probe.inc.c.in'))
    raw = resident.replace(raw,b'memset(&banks[i],0,sizeof(banks[i])); bank_error[i] = -ENODEV;',
        b'memset(&banks[i],0,sizeof(banks[i])); bank_error[i] = -ENODEV; clear_bank_state(i);')
    raw = resident.section(raw,b'static unsigned int cpu_sample(',b'static const struct kernel_param_ops sample_ops',
        read('provider-sample.inc.c.in'))
    raw = resident.replace(raw,b'S22THERMD1 seq=0 state=unread',b'S22THERMD2 seq=0 state=unread')
    return {'Makefile':resident.common._read(PROVIDER/'Makefile'),'thermal_core.h':core_source(),
            's22plus_thermal_telemetry.c':raw}


def wire_source():
    raw = resident.read('wire.h')
    raw = resident.replace(raw,b'#define STATUS_CPU_TEMP 256U',
        b'#define STATUS_CPU_TEMP 256U\n#define STATUS_GPU_TEMP 512U\n#define STATUS_DDR_TEMP 1024U')
    raw = resident.replace(raw,b'0x31525353U',b'0x32525353U')
    raw = resident.replace(raw,b'0x31565253U',b'0x32565253U')
    raw = resident.replace(raw,b'uint32_t cpu_mask,cpu_expected,reserved2[2];',
        b'uint32_t cpu_mask,cpu_expected,reserved2[2];\n    struct s22_thermal_data thermal;')
    raw = resident.replace(raw,b'sizeof(struct status_metrics)==128',b'sizeof(struct status_metrics)==304')
    raw = resident.replace(raw,b'sizeof(struct hud_snapshot)==304',b'sizeof(struct hud_snapshot)==656')
    raw = resident.replace(raw,b'(source?508U:3U)',b'(source?2044U:3U)')
    raw = resident.replace(raw,b'    return 1;\n}',read('ipc-validate.inc.c.in')+b'    return 1;\n}')
    return core_source()+b'\n'+raw


def inline_wire(raw):
    return resident.replace(raw,b'#include "s22plus_resident_v1/wire.h"',wire_source())


def transform_native(raw):
    raw=inline_wire(raw)
    raw=resident.replace(raw,b'struct status_metrics sample[2],gauge_baseline;',
        b'struct status_metrics sample[2],gauge_baseline;\n    uint64_t thermal_sequence,thermal_ms;')
    raw=resident.replace(raw,b'if(i){baseline.gauge_sequence=h->gauge_baseline.gauge_sequence;',
        b'if(i){baseline.thermal.sequence=h->thermal_sequence;baseline.thermal.start_ms=h->thermal_ms;\n'
        b'            baseline.gauge_sequence=h->gauge_baseline.gauge_sequence;')
    raw=resident.replace(raw,b'h->sample[i]=next;if(i && (next.valid&224U))h->gauge_baseline=next;',
        b'h->sample[i]=next;if(i && (next.valid&224U))h->gauge_baseline=next;\n'
        b'        if(i && next.thermal.sequence){h->thermal_sequence=next.thermal.sequence;h->thermal_ms=next.thermal.start_ms;}')
    return raw


def helper_template(identity):
    return transform_native(resident.helper_template(identity))


def materialize_helper(identity,key):
    return transform_native(resident.materialize_helper(identity,key))


def render_display(identity,modules):
    raw = resident.render_display(identity,modules)
    raw = inline_wire(raw)
    raw = resident.section(raw,b'/* Exact Waipio CPU thermal-zone names',b'static int resident_clock(',read('collect.inc.c.in'))
    raw = resident.section(raw,b'static void hud_record(',b'static void hud_single_encoder(',read('record.inc.c.in'))
    anchor=b'    if(hv&STATUS_GAUGE_SOC)snprintf(text,sizeof(text),"GAUGE SOC: %u.%u%%"'
    raw = resident.replace(raw,anchor,read('render.inc.c.in')+anchor)
    for before,after in ((1340,1490),(1450,1590),(1560,1690),(1670,1790)):
        raw = resident.replace(raw,f'hud_text(b,120,{before},text,5);'.encode(),
            f'hud_text(b,120,{after},text,5);'.encode())
    return raw


def profile_contract():
    return dict(previous.profile_contract(),thermal_profile=THERMAL_PROFILE,
        gpu_sources='gpuss-0..1:tsens0:14..15',ddr_source='SoC-DDR-region:tsens1:9',
        thermal_sensor_count=16,private_ipc_sample_bytes=304,private_ipc_view_bytes=656,
        diagnostics='frame-and-acquisition-joined; per-bank-read-presence-and-probe/acquisition-phase')


def source_files():
    return tuple(sorted(set(previous.source_files())|{Path(__file__)}|
        {TEMPLATES/name for name in PARTS}|{PROVIDER/name for name in ('Makefile','s22plus_thermal_telemetry.c')}))


def provider_files():
    return tuple(sorted({Path(__file__),Path(previous.__file__),previous.CORE,
        PROVIDER/'Makefile',PROVIDER/'s22plus_thermal_telemetry.c',
        *(TEMPLATES/name for name in ('core.inc.h','provider-map.inc.c.in',
            'provider-probe.inc.c.in','provider-sample.inc.c.in'))}))
