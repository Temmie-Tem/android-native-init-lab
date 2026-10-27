#!/usr/bin/env python3
"""Prepare private H0 inputs; never contacts a device or creates authority.

The source tree is extracted from the locked kernel tarball. Public inputs are
hash checked; device-specific memory data and all generated blobs stay private.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/analysis'))
from s22plus_fyg8_p319_max77705_irq_dt_audit import FdtBlob, _fdt_props


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nodes(path):
    data = Path(path).read_bytes()
    require(40 <= len(data) <= 2 * 1024 * 1024, 'FDT size')
    require(struct.unpack_from('>I', data, 4)[0] == len(data), 'FDT totalsize')
    result = {}
    for p in _fdt_props(FdtBlob(0, 0, len(data), data)):
        require(p.name not in result.setdefault(p.path, {}), 'duplicate FDT property')
        result[p.path][p.name] = p.value
    return result


def ranges(data):
    require(len(data) % 16 == 0, 'expected two address and two size cells')
    result = []
    for start, size in struct.iter_unpack('>QQ', data):
        require(start + size <= 2**64, 'range overflow')
        if size:
            result.append((start, start + size))
    return result


def merged(items):
    result = []
    for start, end in sorted(items):
        require(start < end, 'empty/reversed interval')
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result


def uncovered(items, coverage):
    result = []
    for start, end in merged(items):
        cursor = start
        for a, b in merged(coverage):
            if a >= end:
                break
            if b <= cursor:
                continue
            if cursor < a:
                result.append((cursor, a))
            cursor = max(cursor, b)
        if cursor < end:
            result.append((cursor, end))
    return result


def fixed_reservations(tree, *, coverage=False):
    # Also preserve disabled fixed reservations conservatively. Size-only CMA
    # requests have no firmware-owned address to copy; their consumers are off.
    return [r for p, props in tree.items()
            if p.startswith('/reserved-memory/') and p.count('/') == 2
            and (not coverage or (props.get('status', b'okay\0') in (b'okay\0', b'ok\0')
                                  and 'no-map' in props and 'reusable' not in props))
            for r in ranges(props.get('reg', b''))]


def memreserve(path):
    data = Path(path).read_bytes()
    require(len(data)>=40 and data[:4]==b'\xd0\x0d\xfe\xed', 'reserve map FDT header')
    require(struct.unpack_from('>I',data,4)[0]==len(data), 'reserve map totalsize')
    pos = struct.unpack_from('>I', data, 16)[0]
    limit=min(struct.unpack_from('>II',data,8))
    require(40<=pos<limit<=len(data) and pos%8==0, 'reserve map bounds/alignment')
    result = []
    while pos + 16 <= limit:
        a, size = struct.unpack_from('>QQ', data, pos)
        pos += 16
        if not a and not size:
            return result
        require(size and a + size <= 2**64, 'bad FDT reserve map')
        result.append((a, a + size))
    raise ValueError('unterminated FDT reserve map')


def cells(items):
    return ', '.join('<0x%x 0x%x 0x%x 0x%x>' %
                     (a >> 32, a & 0xffffffff, (b-a) >> 32, (b-a) & 0xffffffff)
                     for a, b in items)


def run(command, log, cwd=None, env=None):
    with Path(log).open('xb') as stream:
        proc = subprocess.run([str(x) for x in command], cwd=cwd, env=env,
                              stdout=stream, stderr=subprocess.STDOUT)
    require(proc.returncode == 0, f'command failed; see {log}')


def compile_dt(kernel, source, output, logbase):
    pre = output.with_suffix('.preprocessed.dts')
    command = ['aarch64-linux-gnu-gcc', '-E', '-nostdinc', '-undef', '-D__DTS__',
               '-x', 'assembler-with-cpp', '-I', kernel/'arch/arm64/boot/dts/qcom',
               '-I', kernel/'include', source, '-o', pre]
    run(command, str(logbase)+'.cpp.log')
    run(['dtc', '-@', '-I', 'dts', '-O', 'dtb', '-o', output, pre],
        str(logbase)+'.dtc.log')


def config_values(text):
    result = {}
    for line in text.splitlines():
        m = re.fullmatch(r'(CONFIG_\w+)=(.*)', line)
        n = re.fullmatch(r'# (CONFIG_\w+) is not set', line)
        if m:
            result[m[1]] = m[2]
        elif n:
            result[n[1]] = 'n'
    return result


def audit_candidate(live_path, candidate_path):
    live, candidate = nodes(live_path), nodes(candidate_path)
    banks = [n['reg'] for n in live.values() if n.get('device_type') == b'memory\0']
    actual = [n['reg'] for n in candidate.values() if n.get('device_type') == b'memory\0']
    require(len(banks)==1 and actual==banks, 'candidate RAM differs from retained banks')
    retained = fixed_reservations(live) + memreserve(live_path)
    require(not uncovered(retained, fixed_reservations(candidate, coverage=True)),
            'candidate lacks active non-reusable no-map reservation coverage')
    symbols = candidate['/__symbols__']
    usb_path = symbols['usb_1'].rstrip(b'\0').decode()
    usb = candidate[usb_path]
    require(usb_path.rsplit('/',1)[-1]=='usb@a600000' and
            b'qcom,snps-dwc3' in usb['compatible'].split(b'\0') and
            usb['dr_mode']==b'peripheral\0' and usb['maximum-speed']==b'high-speed\0',
            'candidate DWC3 role/speed/node differs')
    candidate_phy = candidate[symbols['usb_1_hsphy'].rstrip(b'\0').decode()]
    require(usb.get('status',b'okay\0') in (b'okay\0',b'ok\0') and
            candidate_phy.get('status',b'okay\0') in (b'okay\0',b'ok\0') and
            candidate_phy['#phy-cells']==bytes(4) and usb['phys']==candidate_phy['phandle'] and
            usb['phy-names']==b'usb2-phy\0', 'candidate USB must use the enabled audited USB2 PHY')
    live_phy = live['/soc/hsphy@88e3000']
    lp = {int.from_bytes(n['phandle'],'big'):p for p,n in live.items() if 'phandle' in n}
    cp = {int.from_bytes(n['phandle'],'big'):p for p,n in candidate.items() if 'phandle' in n}
    result=[]
    for source_name, destination_name in [('vdd-supply','vdda-pll-supply'),
                                          ('vdda18-supply','vdda18-supply'),('vdda33-supply','vdda33-supply')]:
        old=live[lp[int.from_bytes(live_phy[source_name],'big')]]
        name=old['regulator-name'].rstrip(b'\0').decode()
        match=re.fullmatch(r'pm8350(c?)_l([0-9]+)',name)
        require(match is not None,'unexpected retained PHY regulator family')
        pmic='c' if match[1] else 'b'
        path=cp[int.from_bytes(candidate_phy[destination_name],'big')]
        rail=candidate[path];parent=candidate[path.rsplit('/',1)[0]]
        require(path.rsplit('/',1)[-1]=='ldo'+match[2] and parent['qcom,pmic-id']==pmic.encode()+b'\0',
                'candidate PHY RPMh resource differs')
        compatible=b'qcom,pm8350c-rpmh-regulators' if pmic=='c' else b'qcom,pm8350-rpmh-regulators'
        require(compatible in parent['compatible'].split(b'\0'),'candidate PHY PMIC family differs')
        low,high=[int.from_bytes(rail[k],'big') for k in ('regulator-min-microvolt','regulator-max-microvolt')]
        old_low,old_high=[int.from_bytes(old[k],'big') for k in ('regulator-min-microvolt','regulator-max-microvolt')]
        require(old_low<=low<=high<=old_high,'candidate PHY voltage exceeds retained rail range')
        result.append({'supply':destination_name,'resource':'ldo'+pmic+match[2],'minimum':low,'maximum':high})
    return {'status':'PASS_H0_COMPILED_DT_BINDINGS','usb_phy_resources':result,
            'active_nonreusable_nomap_coverage':True,'memory_banks_equal':True}


def prepare(base, live_path, output):
    base, live_path, output = map(lambda p: p.resolve(), (base, live_path, output))
    require(output.is_relative_to(ROOT/'workspace/private'), 'output must be private')
    lock = json.loads((HERE/'sources.json').read_text())
    for relative, expected in lock['files'].items():
        require(digest(base/relative) == expected, 'source changed: '+relative)
    require(digest(base/'linux-7.2.11.tar.xz') == lock['kernel']['sha256'], 'kernel archive changed')
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    kernel = base/'linux-7.2.11'
    live = nodes(live_path)
    require(live['/']['model'].startswith(b'Samsung G0Q PROJECT'), 'not retained g0q FDT')
    memory = [p for p in live if live[p].get('device_type') == b'memory\0']
    require(len(memory) == 1, 'memory node cardinality')
    banks = ranges(live[memory[0]]['reg'])
    require(len(banks) == 5 and all(a % 4096 == b % 4096 == 0 for a,b in banks), 'RAM geometry')
    phandles = {int.from_bytes(p['phandle'], 'big'): n for n,p in live.items() if 'phandle' in p}
    phy = live['/soc/hsphy@88e3000']
    rails = {}
    for prop, name, voltage in [('vdd-supply', b'pm8350_l5\0', 880000),
                               ('vdda18-supply', b'pm8350c_l1\0', 1800000),
                               ('vdda33-supply', b'pm8350_l2\0', 3072000)]:
        rail = live[phandles[int.from_bytes(phy[prop], 'big')]]
        require(rail['regulator-name'] == name, 'USB rail identity')
        low = int.from_bytes(rail['regulator-min-microvolt'], 'big')
        high = int.from_bytes(rail['regulator-max-microvolt'], 'big')
        require(low <= voltage <= high, 'USB rail voltage')
        rails[prop] = {'name': name.rstrip(b'\0').decode(), 'minimum':low,'maximum':high}
    static = '#include "sm8450-samsung-r0q.dts"\n'+(HERE/'g0q.dtsi').read_text()
    intermediate = output/'base-g0q.dts'
    intermediate.write_text(static)
    compile_dt(kernel, intermediate, output/'base-g0q.dtb', output/'base-g0q')
    base_tree = nodes(output/'base-g0q.dtb')
    retained = fixed_reservations(live) + memreserve(live_path)
    added = uncovered(retained, fixed_reservations(base_tree, coverage=True))
    extra = ['\n&{/memory@a0000000} { reg = '+cells(banks)+'; };\n',
             '/ { reserved-memory {\n']
    for i, interval in enumerate(added):
        extra.append('  g0q-retained-%d@%x { reg = %s; no-map; };\n' %
                     (i, interval[0], cells([interval])))
    extra.append('}; };\n')
    generated = output/'g0q-memory.dtsi'
    generated.write_text('/* Private retained g0q memory snapshot; do not commit. */\n'+''.join(extra))
    final = output/'sm8450-samsung-g0q-ram.dts'
    final.write_text(static+'\n#include "g0q-memory.dtsi"\n')
    compile_dt(kernel, final, output/'sm8450-samsung-g0q-ram.dtb', output/'g0q')
    candidate = nodes(output/'sm8450-samsung-g0q-ram.dtb')
    candidate_audit = audit_candidate(live_path, output/'sm8450-samsung-g0q-ram.dtb')
    for label in ['ufs_mem_hc','ufs_mem_phy','pcie0','pcie1','gpu','mdss',
                  'remoteproc_mpss','remoteproc_adsp','remoteproc_cdsp','crypto']:
        path = candidate['/__symbols__'][label].rstrip(b'\0').decode()
        require(candidate[path]['status'] == b'disabled\0', 'forbidden enabled node: '+label)
    build = output/'kernel-build'; build.mkdir()
    values = config_values((base/'r0q-port/kernel/config-r0q.aarch64').read_text())
    wanted = config_values((HERE/'g0q.fragment').read_text()); values.update(wanted)
    (build/'.config').write_text(''.join(f'# {k} is not set\n' if v=='n' else f'{k}={v}\n'
                                       for k,v in values.items()))
    run(['make','-C',kernel,'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
         'olddefconfig'],output/'olddefconfig.log')
    actual = config_values((build/'.config').read_text())
    mismatch = {k: {'wanted':v,'actual':actual.get(k,'n')} for k,v in wanted.items()
                if actual.get(k,'n') != v}
    require(not mismatch, 'configuration mismatch: '+json.dumps(mismatch))
    result = {'status':'H0_PREPARED_NOT_DEVICE_AUTHORITY','live_fdt':{'path':str(live_path),'sha256':digest(live_path)},
              'source_lock_sha256':digest(HERE/'sources.json'), 'memory_banks':banks,
              'live_fixed_reservations':retained,'added_reservations':added,
              'candidate_reservations':fixed_reservations(candidate),
              'size_only_reservations':[p for p,n in live.items() if p.startswith('/reserved-memory/') and 'size' in n and 'reg' not in n],
              'usb_rails':rails,'candidate_audit':candidate_audit,'kernel':str(kernel),'kernel_build':str(build),
              'dtb_sha256':digest(output/'sm8450-samsung-g0q-ram.dtb'),
              'config_sha256':digest(build/'.config'),'device_actions':0}
    (output/'prepared.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'added_reservations':len(added),
                      'usb_rails_verified':len(rails),'output':str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--live-fdt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.base, args.live_fdt, args.output)
