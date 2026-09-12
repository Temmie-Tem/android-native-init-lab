"""Temperature-only renderer composition over unchanged resident control/IPC.

P387's source files are immutable inputs. This new profile changes only its
own generated renderer and added fixed modules, under a fresh E identity.
"""
from pathlib import Path
import s22plus_native_resident_source_v1 as resident

ROOT,NATIVE = resident.ROOT,resident.NATIVE
PROFILE = resident.PROFILE  # Same control wire, lifetime and private IPC ABI.
THERMAL_PROFILE = 'g0q-r12-tsens-adc-temperature-v1'
TEMPLATES = NATIVE/'s22plus_thermal_v1'
CORE = ROOT/'workspace/public/src/kernel-modules/s22plus_thermal_telemetry_v1/thermal_core.h'
helper_template,materialize_helper = resident.helper_template,resident.materialize_helper


def profile_contract():
    return dict(resident.profile_contract(),thermal_profile=THERMAL_PROFILE,
        cpu_sources='cpu-1-0..8:tsens0:5..13;cpu-0-0..3:tsens1:1..4',
        battery_source='board-adc-temp-0x14b-shared-wpc',battery_units='board-table-decidegree-C',
        thermal_freshness='new-software-acquisition-within-current-collection',
        cpu_hardware_conversion_age='UNPROVED')


def source_files():
    return tuple(sorted(set(resident.source_files())|{Path(__file__),CORE,TEMPLATES/'collect.inc.c.in'}))


def render_display(identity,modules):
    raw = resident.render_display(identity,modules)
    # Embed the shared arithmetic so generated C is self-contained apart from
    # the unchanged resident IPC and existing system headers.
    core = resident.section(resident.common._read(CORE),b'struct s22_thermal_cpu {',b'/* adc-temp',b'')
    part = core+b'\n'+resident.common._read(TEMPLATES/'collect.inc.c.in')
    raw = resident.section(raw,b'/* Exact Waipio CPU thermal-zone names',b'static int resident_clock(',part)
    raw = resident.replace(raw,b'"RESIDENT_FRAME seq=%"',b'"RESIDENT_THERMAL_FRAME seq=%"')
    raw = resident.replace(raw,b'" cpu_temp_mc=%d cpu_mask=%u expected=13"',
        b'" cpu_temp_mc=%d cpu_mask=%u expected=13 battery_temp_deci=%d"')
    raw = resident.replace(raw,b'h->cpu_temp_mc,h->cpu_mask,resident_diagnostic_dropped',
        b'h->cpu_temp_mc,h->cpu_mask,h->battery_temp_deci,resident_diagnostic_dropped')
    return raw
