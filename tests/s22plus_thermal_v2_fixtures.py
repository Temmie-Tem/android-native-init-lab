"""Fixture facts from exact retained stock base+r12-overlay FDTs, not the provider.

The sealed input reconstruction is documented in the 2026-09-13 census. These
fixed hashes bind that historical input rather than a growing current ledger.
"""
import hashlib
import json
import struct

import s22plus_fyg8_p241_dtbo_role_contract as fdt
import s22plus_native_thermal_source_v2 as source

ROOT=source.ROOT
DTBS=ROOT/'workspace/private/outputs/s22plus-temperature-census-h0-20260913-1'
MERGED_SHA256=(
    '804b6af30601e5487587b4eb5ea662d0f650514a8cfd3ac90a5e9d34ccae9ae1',
    '990ae7ee9cd8d9feaa59f48bad49065dee5cea527293ce798905601a64d4ccda',
    '09c22775b090907e4195ce87b1c12fd1049805dc05ab4ca23ce38035d2308ed6',
    'd327bdda894d6c8302a0b40c0b6d8405f9be14559f6370b8b7cc0cf7ea323c87')


def cells(raw):return struct.unpack('>'+'I'*(len(raw)//4),raw)


def facts(index=0):
    raw=(DTBS/f'merged-g0q-r12-base-{index}.dtb').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MERGED_SHA256[index]:raise ValueError('exact merged DT fixture changed')
    nodes={n.path:n.properties for n in fdt.parse_fdt(raw)}
    zones=nodes['/__symbols__']['thermal_zones'].rstrip(b'\0').decode()
    byph={cells(p['phandle'])[0]:path for path,p in nodes.items() if 'phandle' in p}
    banks=[nodes['/__symbols__'][f'tsens{i}'].rstrip(b'\0').decode() for i in range(2)]
    rows=[]
    for name,_,_ in source.sensor_map():
        reference,sensor=cells(nodes[zones+'/'+name]['thermal-sensors'])
        rows.append((name,banks.index(byph[reference]),sensor))
    battery=nodes['/samsung_mobile_device/battery']
    return dict(zones=zones,old_parent_exists='/thermal-zones' in nodes,banks=banks,sensors=rows,
        resources=[cells(nodes[path]['reg']) for path in banks],
        battery_uv=cells(battery['battery,temp_table_adc']),
        battery_deci=tuple(v if v<1<<31 else v-(1<<32) for v in cells(battery['battery,temp_table_data'])))


def header(value):
    rows=',\n'.join('{'+json.dumps(name)+f',{bank},{sensor}'+'}' for name,bank,sensor in value['sensors'])
    return ('#define FIXTURE_ZONE_PATH '+json.dumps(value['zones'])+'\n'
        'static const char *const fixture_bank_paths[]={'+','.join(map(json.dumps,value['banks']))+'};\n'
        'static const struct s22_thermal_cpu fixture_sensors[]={'+rows+'};\n'
        'static const unsigned long long fixture_resources[2][4]={'+','.join('{'+','.join(map(str,r))+'}' for r in value['resources'])+'};\n'
        'static const unsigned int fixture_battery_uv[]={'+','.join(map(str,value['battery_uv']))+'};\n'
        'static const int fixture_battery_deci[]={'+','.join(map(str,value['battery_deci']))+'};\n').encode()


def kernel_harness():
    raw=(ROOT/'tests/s22plus_thermal_kernel_harness.c').read_bytes()
    raw=raw[:raw.index(b'int main(')]
    raw=source.resident.replace(raw,b'#include "thermal_core.h"',b'#include "thermal_core.h"\n#include "dt-fixture.h"')
    raw=raw.replace(b'"/thermal-zones"',b'FIXTURE_ZONE_PATH')
    raw=source.resident.replace(raw,b'cn[13]',b'cn[S22_THERMAL_SENSOR_COUNT]')
    raw=source.resident.replace(raw,b'if(!strcmp(p,FIXTURE_ZONE_PATH))return &zones;',
        b'if(!strcmp(p,is_case("old-parent")?"/thermal-zones":FIXTURE_ZONE_PATH))return &zones;')
    for i,path in enumerate((b'"/soc/thermal-sensor@c263000"',b'"/soc/thermal-sensor@c265000"')):
        raw=source.resident.replace(raw,path,f'fixture_bank_paths[{i}]'.encode())
    raw=source.resident.replace(raw,b'    assert(0);return NULL;',b'    return NULL;')
    raw=raw.replace(b'i<13',b'i<S22_THERMAL_SENSOR_COUNT').replace(b's22_thermal_cpus[',b'fixture_sensors[')
    raw=source.resident.replace(raw,b'    assert(parent==&zones);',
        b'    assert(parent==&zones);\n'
        b'    if((is_case("missing-gpu")&&!strcmp(name,"gpuss-0")) ||\n'
        b'       (is_case("missing-ddr")&&!strcmp(name,"ddr")))return NULL;')
    raw=source.resident.replace(raw,b's22_thermal_uv[i]+(table_wrong&&i==3)',b'fixture_battery_uv[i]+(table_wrong&&i==3)')
    raw=source.resident.replace(raw,b'(u32)s22_thermal_deci[i]',b'(u32)fixture_battery_deci[i]')
    return raw+(ROOT/'tests/s22plus_thermal_v2_kernel_main.c').read_bytes()
