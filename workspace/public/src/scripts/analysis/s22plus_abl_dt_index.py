"""Index LinuxLoader.efi: strings, string xrefs, function starts, call graph.

Usage: python s22plus_abl_dt_index.py <LinuxLoader.efi> <out_dir>
Writes index.json (strings with xref functions, call graph) for later queries.
"""
import json
import re
import sys
from pathlib import Path

import capstone
import pefile

src, out = Path(sys.argv[1]), Path(sys.argv[2])
pe = pefile.PE(str(src))
image = pe.get_memory_mapped_image()
cs = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
cs.detail = True

ins = []
for sec in pe.sections:
    if sec.Characteristics & 0x20000000:
        ins.extend(cs.disasm(sec.get_data(), sec.VirtualAddress))
index = {i.address: k for k, i in enumerate(ins)}

# Function starts: bl targets plus common prologues.
starts = set()
calls = {}
for i in ins:
    if i.mnemonic == 'bl':
        starts.add(i.operands[0].imm)
    elif i.mnemonic == 'paciasp':
        starts.add(i.address)
    elif i.mnemonic == 'stp' and i.op_str.startswith('x29, x30, [sp, #-') and i.op_str.endswith('!'):
        starts.add(i.address)
starts = sorted(starts)


def func_of(addr):
    lo, hi = 0, len(starts) - 1
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if starts[mid] <= addr:
            best = starts[mid]
            lo = mid + 1
        else:
            hi = mid - 1
    return best


for i in ins:
    if i.mnemonic == 'bl':
        calls.setdefault(func_of(i.address), set()).add(i.operands[0].imm)

# Strings anywhere in the mapped image (UTF-8/ASCII, >= 5 chars).
strings = {}
for m in re.finditer(rb'[\x20-\x7e\t\n\r]{5,}', image):
    strings[m.start()] = m.group().decode('ascii', 'replace')
# UTF-16LE strings (EDK2 Print uses L"" often).
for m in re.finditer(rb'(?:[\x20-\x7e]\x00){5,}', image):
    strings.setdefault(m.start(), m.group().decode('utf-16le', 'replace'))

xrefs = {}
for k, i in enumerate(ins):
    if i.mnemonic != 'adrp':
        continue
    reg = i.operands[0].reg
    base = i.operands[1].imm
    for j in ins[k + 1:k + 12]:
        if (j.mnemonic == 'add' and len(j.operands) == 3
                and j.operands[1].type == capstone.arm64.ARM64_OP_REG
                and j.operands[1].reg == reg
                and j.operands[2].type == capstone.arm64.ARM64_OP_IMM):
            addr = base + j.operands[2].imm
            if addr in strings:
                xrefs.setdefault(addr, []).append(j.address)
        _, writes = j.regs_access()
        if reg in writes:
            break

result = {
    'source_sha256': __import__('hashlib').sha256(src.read_bytes()).hexdigest(),
    'functions': len(starts),
    'strings': [
        {'rva': a, 'text': strings[a], 'xrefs': xrefs.get(a, []),
         'funcs': sorted({func_of(x) for x in xrefs.get(a, [])})}
        for a in sorted(strings)
    ],
    'calls': {str(f): sorted(t) for f, t in calls.items() if f is not None},
}
out.mkdir(parents=True, exist_ok=True)
(out / 'index.json').write_text(json.dumps(result))
print('functions', len(starts), 'strings', len(strings), 'xref strings', len(xrefs))
