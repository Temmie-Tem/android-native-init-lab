#!/usr/bin/env python3
"""Produce the fixed returning primary_entry variant from retained unmarked source."""
import argparse
import json
from pathlib import Path
import secrets
import sys

HERE=Path(__file__).resolve().parent
COMMON=HERE.parent/'s22plus_canary_h0'
ROOT=HERE.parents[4]
sys.path[:0]=[str(COMMON),str(ROOT/'workspace/public/src/scripts/revalidation')]
from prepare import digest,require
from prepare_marked import prepare
import s22plus_loader_prefix_v1 as protocol


def pin(path):
    p=Path(path).resolve(strict=True)
    return dict(path=str(p),size=p.stat().st_size,sha256=digest(p))


def instrumented_head(old,config):
    site='SYM_CODE_START(primary_entry)\n\tbl\trecord_mmu_state\n'
    end='SYM_CODE_END(primary_entry)\n'
    require(old.count(site)==old.count(end)==1 and 's22_retained_' not in old and 'g0q_prefix' not in old,
            'unmarked mainline primary_entry differs')
    prefix='''SYM_CODE_START(primary_entry)
\tmov x18, x30
\tbl s22_retained_kernel
\tadr x0, primary_entry
\tmrs x1, CurrentEL
\tcmp x1, #4
\tb.eq .Lg0q_prefix_el1
\tmrs x2, sctlr_el2
\tb .Lg0q_prefix_return
.Lg0q_prefix_el1:
\tmrs x2, sctlr_el1
.Lg0q_prefix_return:
\tmovz w3, #0x5831
\tmovk w3, #0x5033, lsl #16
\t.global g0q_prefix_stop
g0q_prefix_stop:
\tbr x18
\tbl record_mmu_state
'''
    return old.replace(site,prefix).replace(end,end+'\n'+protocol.marker_module().render(config['retained_marker'],2)+'\n')


def verify(prepared):
    prepared=Path(prepared);value=json.loads((prepared/'prepared.json').read_text())
    receipt=json.loads((prepared/'prefix-source.json').read_text())
    require(receipt['schema']=='s22plus-prefix-kernel-source-v1' and receipt['device_actions']==0,
            'prefix source schema differs')
    for name in ('original_head','instrumented_head','key'):
        require(pin(receipt[name]['path'])==receipt[name],'prefix source changed: '+name)
    key=Path(receipt['key']['path']).read_bytes();cfg=receipt['configuration']
    require(cfg==protocol.configuration(cfg['marker'],key),'prefix source candidate/key differs')
    head=Path(value['kernel'])/'arch/arm64/kernel/head.S'
    require(pin(head)==receipt['instrumented_head'] and head.read_text()==
        instrumented_head(Path(receipt['original_head']['path']).read_text(),cfg),
        'complete prefix source does not rederive')
    return receipt


def create(previous,output):
    value=prepare(Path(previous),Path(output));output=Path(output)
    key=secrets.token_bytes(32);candidate=secrets.token_hex(32)
    cfg=protocol.configuration(candidate,key)
    (output/'prefix-key.bin').write_bytes(key)
    head=Path(value['kernel'])/'arch/arm64/kernel/head.S';old=head.read_text()
    (output/'original-head.S').write_text(old);head.write_text(instrumented_head(old,cfg))
    receipt=dict(schema='s22plus-prefix-kernel-source-v1',configuration=cfg,
        key=pin(output/'prefix-key.bin'),original_head=pin(output/'original-head.S'),
        instrumented_head=pin(head),sources=[pin(__file__),pin(protocol.__file__),
            pin(COMMON/'retained-marker.S'),pin(COMMON/'retained_marker.py')],device_actions=0)
    (output/'prefix-source.json').write_text(json.dumps(receipt,indent=2)+'\n')
    verify(output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('previous',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();create(a.previous.resolve(),a.output.resolve())
