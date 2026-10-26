"""Annotated disassembly of one LinuxLoader function.

Usage: python s22plus_abl_dt_func.py <LinuxLoader.efi> <index.json> <rva-hex> [--calls-only]
Annotates string references and bl targets (target labelled by the first
string it references, which is usually its log text).
"""
import json
import sys

import capstone
import pefile

pe = pefile.PE(sys.argv[1])
idx = json.load(open(sys.argv[2]))
start = int(sys.argv[3], 16)
calls_only = '--calls-only' in sys.argv

strings = {s['rva']: s['text'] for s in idx['strings']}
label = {}
for s in idx['strings']:
    for f in s['funcs']:
        if f is not None and f not in label and len(s['text'].strip()) > 6:
            label[f] = s['text'].strip().replace('\n', ' ')[:50]
funcs = sorted({int(k) for k in idx['calls']} | {t for v in idx['calls'].values() for t in v})

end = next((f for f in funcs if f > start), start + 0x4000)
text = next(s for s in pe.sections if s.Characteristics & 0x20000000)
data = text.get_data()
cs = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
cs.detail = True
code = data[start - text.VirtualAddress:end - text.VirtualAddress]
ins = list(cs.disasm(code, start))
pending = {}
for k, i in enumerate(ins):
    note = ''
    if i.mnemonic == 'adrp':
        pending[i.operands[0].reg] = i.operands[1].imm
    elif (i.mnemonic == 'add' and len(i.operands) == 3
          and i.operands[1].type == capstone.arm64.ARM64_OP_REG
          and i.operands[1].reg in pending
          and i.operands[2].type == capstone.arm64.ARM64_OP_IMM):
        a = pending[i.operands[1].reg] + i.operands[2].imm
        if a in strings:
            note = '; "%s"' % strings[a].strip().replace('\n', ' ')[:70]
        else:
            note = '; =0x%x' % a
    elif i.mnemonic == 'bl':
        t = i.operands[0].imm
        note = '; -> %x %s' % (t, label.get(t, ''))
    if calls_only and not note:
        if not i.mnemonic.startswith(('cb', 'tb', 'b.', 'ret')):
            continue
    print('%06x %-7s %-34s %s' % (i.address, i.mnemonic, i.op_str, note))
