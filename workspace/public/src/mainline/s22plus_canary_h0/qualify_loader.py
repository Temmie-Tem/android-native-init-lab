#!/usr/bin/env python3
"""Execute the actual linked ARM64 loader in Unicorn. H0, no device access.

Unicorn checks instruction/data behavior, not cache coherency, stage-2 memory
attributes, ABL placement, hardware health or recovery. SCTLR-negative cases
inject a register value at the actual guard; they do not emulate an active MMU.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import time

from elftools.elf.elffile import ELFFile
from unicorn import (Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE,
                     UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MEM_READ)
from unicorn.arm64_const import (UC_ARM64_REG_PC, UC_ARM64_REG_PSTATE, UC_ARM64_REG_X0,
                                UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X3,
                                UC_ARM64_REG_X5, UC_ARM64_REG_X9, UC_ARM64_REG_X10, UC_ARM64_REG_LR,
                                UC_ARM64_REG_SP)

from prepare import ROOT, digest, require, merged, uncovered, nodes, memreserve
import retained_marker as marker

PAGE=4096
SYNC=struct.pack('<IIII',0xd5033f9f,0xd508751f,0xd5033f9f,0xd5033fdf)


def symbols(path):
    with Path(path).open('rb') as stream:
        elf=ELFFile(stream)
        return {s.name:(s['st_value'],s['st_size']) for s in elf.get_section_by_name('.symtab').iter_symbols()}


def admitted(source, record):
    s=record['runtime_symbols'];size=record['loader']['size'];start=s['_start']
    end=source+size
    return (source%16==0 and end<2**64 and
            any(a<=source<end<=b for a,b in record['source_ram_ranges']) and
            (source<=s['_head'] or s['_file_end']<=source))


def machine(intervals):
    u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    u.reg_write(UC_ARM64_REG_PSTATE,5)  # EL1h; the real stub must mask DAIF.
    u.cpr_write(3,0,1,0,0,0)  # SCTLR_EL1
    u.cpr_write(3,4,1,0,0,0)  # SCTLR_EL2
    mapped=merged([(a//PAGE*PAGE,(b+PAGE-1)//PAGE*PAGE) for a,b in intervals])
    for a,b in mapped:
        u.mem_map(a,b-a)
        u.mem_write(a,b'\xa5'*(b-a))
    return u,mapped


def case(blob,record,all_symbols,source,*,state=None,el=1,full=False,bad_fdt=False):
    s={k:v[0] for k,v in all_symbols.items()};head=s['_head'];file_end=s['_file_end']
    size=len(blob);stub=s['_start']-head;source_limit=min(source+size,2**64)
    intervals=[(source,source_limit),(head,s['_stack_end'])]
    if full:intervals+=list(map(tuple,record['extents'].values()))
    marked=record.get('retained_marker') if full else None
    if marked:intervals.append((marker.BASE,marker.BASE+marker.REGION))
    u,mapped=machine(intervals)
    if marked:
        marker_header=struct.pack('<IIII',7,0x4d474f4c,marker.PAYLOAD+300,123)
        u.mem_write(marker.BASE,marker_header)
    # Unicorn 2.1.4 returns CurrentEL=EL1 even after changing PSTATE mode.
    # Exercise other actual guard branches by injecting the MRS result only.
    if el != 1:
        guard=source+s['_reloc_check_el']-head
        def inject_el(uc,address,length,user):uc.reg_write(UC_ARM64_REG_X9,el*4)
        u.hook_add(UC_HOOK_CODE,inject_el,begin=guard,end=guard)
        if el==2:
            # Unicorn cannot raise this core from EL1 to EL2. QEMU separately
            # executes real EL2 entry; here only simulate that MRS result.
            read=source+s['_reloc_read_el2']-head
            def read_el2(uc,address,length,user):
                uc.reg_write(UC_ARM64_REG_X10,0);uc.reg_write(UC_ARM64_REG_PC,address+4)
            u.hook_add(UC_HOOK_CODE,read_el2,begin=read,end=read)
    material=bytearray(blob[:source_limit-source])
    if bad_fdt:material[s['dtb']-head:s['dtb']-head+4]=b'BAD!'
    u.mem_write(source,bytes(material))
    expected=admitted(source,record) and state is None and el in (1,2)
    before={a:bytes(u.mem_read(a,b-a)) for a,b in mapped} if not full else {}
    terminal=[];branched=[];writes=[0];bss_checked=[];sync_seen=[]
    branch=source+s['_reloc_branch']-head
    reject=source+s['_reloc_rejected']-head
    def on_branch(uc,address,length,user):
        require(uc.reg_read(UC_ARM64_REG_X5)==s['_start'],'relocation branch target')
        branched.append(True)
    u.hook_add(UC_HOOK_CODE,on_branch,begin=branch,end=branch)
    def on_start(uc,address,length,user):
        if branched and not full:terminal.append('entry');uc.emu_stop()
    u.hook_add(UC_HOOK_CODE,on_start,begin=s['_start'],end=s['_start'])
    def on_reject(uc,address,length,user):terminal.append('reject');uc.emu_stop()
    u.hook_add(UC_HOOK_CODE,on_reject,begin=reject,end=reject)
    if state is not None:
        guard=source+s['_reloc_check_state']-head
        def inject(uc,address,length,user):uc.reg_write(UC_ARM64_REG_X10,state)
        u.hook_add(UC_HOOK_CODE,inject,begin=guard,end=guard)
    def write_guard(uc,access,address,length,value,user):
        writes[0]+=length
        require(expected,'rejected placement wrote memory')
        require(address%min(length,8)==0,'unaligned write')
        require(not (address<source+stub and address+length>source),'live stub overwritten')
        require(s['_start']<=address and address+length<=file_end,'write outside copy extent')
    if not full:u.hook_add(UC_HOOK_MEM_WRITE,write_guard)
    # Reject any data read beyond file-backed input before _start runs.
    if source_limit<2**64-PAGE and not full:
        def overread(uc,access,address,length,value,user):raise ValueError('source tail overread')
        u.hook_add(UC_HOOK_MEM_READ,overread,begin=source_limit,end=source_limit+PAGE-1)
    if full:
        def aligned(uc,access,address,length,value,user):
            require(address%min(length,8)==0,'unaligned loader access')
            if branched:
                require(s['_stack_end']-PAGE<=uc.reg_read(UC_ARM64_REG_SP)<=s['_stack_end'],
                        'loader stack escaped its reserved page')
        u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,aligned)
        def at_main(uc,address,length,user):
            require(bytes(uc.mem_read(s['__bss_start'],s['__bss_end']-s['__bss_start']))==
                    bytes(s['__bss_end']-s['__bss_start']),'BSS not zero before C')
            bss_checked.append(True)
        u.hook_add(UC_HOOK_CODE,at_main,begin=s['main'],end=s['main'])
        target=record['extents']['kernel-runtime'][0]
        def at_kernel(uc,address,length,user):terminal.append('kernel');uc.emu_stop()
        u.hook_add(UC_HOOK_CODE,at_kernel,begin=target,end=target)
        def at_sync(uc,address,length,user):sync_seen.append(address)
        jump=s['load_kernel_and_jump']
        sync_offset=blob[jump-head:jump-head+64].find(SYNC)
        require(sync_offset>=0,'kernel cache sequence missing')
        u.hook_add(UC_HOOK_CODE,at_sync,begin=jump+sync_offset,end=jump+sync_offset)
        if bad_fdt:
            fdt_start,fdt_size=all_symbols['patch_dtb']
            code=blob[fdt_start-head:fdt_start-head+fdt_size]
            parks=[fdt_start+i for i in range(0,len(code),4)
                   if code[i:i+4]==b'\x00\x00\x00\x14' or
                   code[i:i+8]==b'\x1f\x20\x03\xd5\xff\xff\xff\x17']
            require(len(parks)==1,'expected one FDT failure park')
            def at_fdt_park(uc,address,length,user):terminal.append('fdt-reject');uc.emu_stop()
            u.hook_add(UC_HOOK_CODE,at_fdt_park,begin=parks[0],end=parks[0])
    started=time.monotonic()
    u.emu_start(source,0,count=150_000_000)
    if full:
        require(terminal==(['fdt-reject'] if bad_fdt else ['kernel']),'full-loader terminal')
        require(bss_checked==[True],'BSS observation missing')
        if bad_fdt:
            require(not sync_seen,'bad FDT reached kernel jump')
            a,b=record['extents']['kernel-runtime']
            require(bytes(u.mem_read(a,b-a))==b'\xa5'*(b-a),'bad FDT copied kernel')
        else:
            require(len(sync_seen)==1,'kernel synchronization not reached')
            require([u.reg_read(r) for r in (UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3)]==[0,0,0],
                    'kernel reserved argument registers')
            require(u.reg_read(UC_ARM64_REG_X0)==record['extents']['rewritten-dtb'][0],'kernel DT argument')
            for symbol,key,length in [('kernel','kernel-runtime',s['kernel_size']),
                                      ('ramdisk','initramfs',s['ramdisk_size'])]:
                require(bytes(u.mem_read(record['extents'][key][0],length))==
                        blob[s[symbol]-head:s[symbol]-head+length],key+' final bytes')
        if marked:
            cfg=json.loads(Path(marked['config']['path']).read_text())
            expected_marker=bytearray(b'\xa5'*marker.PAYLOAD)
            if not bad_fdt:expected_marker[44:44+marker.SLOT]=bytes.fromhex(cfg['frames']['1'])
            require(bytes(u.mem_read(marker.BASE,marker.HEADER))==marker_header and
                    bytes(u.mem_read(marker.BASE+marker.HEADER,marker.PAYLOAD))==expected_marker,
                    'full loader marker/header/write extent differs')
    else:
        require(terminal==(['entry'] if expected else ['reject']),'placement terminal differs')
        if expected:
            require(bytes(u.mem_read(s['_start'],size-stub))==blob[stub:],'relocated file differs')
            require(writes[0]==(0 if source==head else size-stub),'copy byte count')
            require(u.reg_read(UC_ARM64_REG_PSTATE)&0x3c0==0x3c0,'DAIF not masked')
        for a,b in mapped:
            for low,high in uncovered([(a,b)],[(s['_start'],file_end)] if expected else []):
                require(bytes(u.mem_read(low,high-low))==before[a][low-a:high-a],'outside-copy canary changed')
    return u,{'source':source,'expected':expected,'terminal':terminal[0],
              'copy_bytes':writes[0] if not full else None,'elapsed_seconds':round(time.monotonic()-started,3),
              'state_injection':state,'entry_el':el,'currentel_result_injected':el!=1}


def copy_cases(blob,all_symbols):
    """Exercise the linked memcpy/memmove with exact access bounds and aliases."""
    s={k:v[0] for k,v in all_symbols.items()};base=0x10000000;stop=base+2*PAGE
    u,_=machine([(s['_head'],s['_head']+len(blob)),(base,stop+PAGE)])
    u.mem_write(s['_head'],blob)
    current={};count=0
    def access(uc,kind,address,length,value,user):
        require(address%min(length,8)==0,'copy unaligned memory access')
        low,high=current['read' if kind==UC_MEM_READ else 'write']
        require(low<=address and address+length<=high,'copy access outside declared bytes')
    u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,access)
    initial=bytes((i*31+7)%256 for i in range(2*PAGE))
    cases=[]
    for size in (0,1,7,8,9,15,16,17,31,32,33,127,128,129,257):
        for a in range(8):
            for b in range(8):cases.append(('memcpy',256+a,2048+b,size))
    for size in (1,7,8,16,32,129,257):
        for shift in (0,1,7,8,15,16,31,-1,-7,-8,-15,-16,-31):
            cases.append(('memmove',512,512+shift,size))
    for name,src,dst,size in cases:
        expected=bytearray(initial);expected[dst:dst+size]=initial[src:src+size]
        current.update(read=(base+src,base+src+size),write=(base+dst,base+dst+size))
        u.mem_write(base,initial)
        for reg,value in [(UC_ARM64_REG_X0,base+dst),(UC_ARM64_REG_X1,base+src),
                          (UC_ARM64_REG_X2,size),(UC_ARM64_REG_LR,stop)]:u.reg_write(reg,value)
        u.emu_start(s[name],stop,count=100000)
        require(u.reg_read(UC_ARM64_REG_PC)==stop,'copy did not return')
        require(u.reg_read(UC_ARM64_REG_X0)==base+dst,'copy return pointer')
        require(bytes(u.mem_read(base,len(initial)))==expected,'copy bytes/canaries differ')
        count+=1
    return count


def qualify(loader,output):
    source_sha256=digest(__file__)
    loader,output=loader.resolve(),output.resolve()
    require(output.is_relative_to(ROOT/'workspace/private'),'private qualification output')
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    record=json.loads((loader/'result.json').read_text());raw=Path(record['loader']['path']).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==record['loader']['sha256'],'loader hash changed')
    require(digest(record['elf']['path'])==record['elf']['sha256'],'ELF hash changed')
    syms=symbols(record['elf']['path']);s={k:v[0] for k,v in syms.items()}
    h=s['_head'];size=len(raw);stub=s['_start']-h
    require(raw[s['_reloc_branch']-h-20:s['_reloc_branch']-h-4]==SYNC,'relocation cache sequence missing')
    candidates=[('same',h),('backward-16',h-16),('backward-page',h-PAGE),
                ('backward-adjacent',h+stub-size),('forward-adjacent',h+size),
                ('live-stub-16',h+16),('live-stub-page',h+PAGE),('live-stub-tail',h+size-16),
                ('unaligned',h-4),('outside-RAM',0x100000),('overflow',2**64-PAGE)]
    # A real file ending exactly on a page boundary exercises bounded tail reads.
    for a,b in record['source_ram_ranges']:
        source=((a+size+PAGE-1)//PAGE*PAGE)-size
        if source+size<=b and source+size<=h:
            candidates.append(('page-exact-tail',source));break
    rows=[]
    for name,source in candidates:
        _,result=case(raw,record,syms,source)
        rows.append(dict(name=name,**result));print(json.dumps(rows[-1]),flush=True)
    require(all(next(r for r in rows if r['name']==name)['expected'] for name in
                ('same','backward-16','backward-page','backward-adjacent','forward-adjacent','page-exact-tail')),
            'placement corpus did not exercise every admitted branch')
    for name,kwargs in [('EL2-result-injected',{'el':2}),('EL3-result-injected',{'el':3}),('MMU',{'state':1}),
                        ('D-cache',{'state':4}),('I-cache',{'state':4096}),('big-endian',{'state':1<<25})]:
        _,result=case(raw,record,syms,h,**kwargs)
        rows.append(dict(name=name,**result));print(json.dumps(rows[-1]),flush=True)
    u,result=case(raw,record,syms,h,full=True)
    fdt_start,fdt_end=record['extents']['rewritten-dtb'];fdt=bytes(u.mem_read(fdt_start,fdt_end-fdt_start))
    fdt_path=output/'rewritten.dtb';fdt_path.write_bytes(fdt)
    ir=json.loads(Path(record['initramfs_manifest']).read_text());tree=nodes(fdt_path);chosen=tree['/chosen']
    require(chosen.pop('linux,initrd-start')==struct.pack('>Q',ir['initrd_address']),'initrd start property')
    require(chosen.pop('linux,initrd-end')==struct.pack('>Q',ir['initrd_address']+ir['initramfs']['size']),'initrd end property')
    require(tree==nodes(ir['dtb']['path']) and memreserve(fdt_path)==memreserve(ir['dtb']['path']),
            'full-loader FDT properties/reservations changed')
    require(fdt[20:32]==Path(ir['dtb']['path']).read_bytes()[20:32],'FDT version/boot CPU changed')
    rows.append(dict(name='full-loader-to-kernel',**result));print(json.dumps(rows[-1]),flush=True)
    _,result=case(raw,record,syms,h,full=True,bad_fdt=True)
    rows.append(dict(name='malformed-FDT-parks',**result));print(json.dumps(rows[-1]),flush=True)
    copies=copy_cases(raw,syms);print(json.dumps({'aligned_copy_cases':copies}),flush=True)
    require(digest(__file__)==source_sha256,'qualification source changed during execution')
    result={'status':'PASS_H0_ACTUAL_ARM64_LOADER','loader_sha256':record['loader']['sha256'],
            'elf_sha256':record['elf']['sha256'],'cases':rows,'aligned_copy_cases':copies,
            'source_sha256':source_sha256,
            'actual_cache_coherency_proved':False,'physical_entry_proved':False,'device_actions':0}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'cases':len(rows)}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--loader',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();qualify(a.loader,a.output)
