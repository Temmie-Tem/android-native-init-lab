#!/usr/bin/env python3
"""Exercise the actual Android-control loader, including its pre-store guard."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import struct
import sys
import time

from build import COMMON, ROOT, STATUS, digest, pin, require, symbols
sys.path.insert(0,str(COMMON))
from prepare import nodes, memreserve
import qualify_loader as shared
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm64_const import (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2,
    UC_ARM64_REG_X3, UC_ARM64_REG_X5, UC_ARM64_REG_X9, UC_ARM64_REG_X10,
    UC_ARM64_REG_X28, UC_ARM64_REG_PC, UC_ARM64_REG_SP, UC_ARM64_REG_LR)

INPUT_FDT = 0xb4000000


def properties(data):
    """Offsets in a trusted fixture; mutated fixtures go only to the real guard."""
    pos, strings = struct.unpack_from('>II',data,8)
    path=[]; result={}
    while True:
        token_pos=pos; token=struct.unpack_from('>I',data,pos)[0];pos+=4
        if token==1:
            end=data.index(0,pos);path.append(data[pos:end].decode());pos=(end+4)&~3
        elif token==2:path.pop()
        elif token==3:
            length,nameoff=struct.unpack_from('>II',data,pos);pos+=8
            name=data[strings+nameoff:data.index(0,strings+nameoff)].decode()
            result[('/'+'/'.join(path[1:]),name)]=(pos,length,token_pos)
            pos=(pos+length+3)&~3
        elif token==4:pass
        elif token==9:break
        else:raise ValueError('trusted fixture token')
    return result


def set_property(data,path,name,value,*,duplicate=False):
    offsets=properties(data);old=offsets.get((path,name));raw=bytearray(data)
    strings=struct.unpack_from('>I',raw,12)[0]
    string_size=struct.unpack_from('>I',raw,32)[0]
    if old:
        pos,length,token=old
        nameoff=struct.unpack_from('>I',raw,token+8)[0]
        replace_end=token if duplicate else (pos+length+3)&~3
    else:
        # All added properties belong to the already present chosen node.
        require(path=='/chosen','fixture insertion path')
        token=next(v[2] for (p,_),v in offsets.items() if p==path)
        replace_end=token;nameoff=string_size
        raw[strings+string_size:strings+string_size]=name.encode()+b'\0'
        string_size+=len(name)+1
    replacement=struct.pack('>III',3,len(value),nameoff)+value
    replacement+=bytes((-len(value))%4)
    delta=len(replacement)-(replace_end-token)
    raw[token:replace_end]=replacement
    struct.pack_into('>I',raw,4,len(raw))
    struct.pack_into('>I',raw,12,strings+delta)
    struct.pack_into('>I',raw,32,string_size)
    struct.pack_into('>I',raw,36,struct.unpack_from('>I',data,36)[0]+delta)
    return bytes(raw)


def header(data,offset,value):
    raw=bytearray(data);struct.pack_into('>I',raw,offset,value);return bytes(raw)


def add_reservation(data,start,size):
    raw=bytearray(data);reserve=struct.unpack_from('>I',raw,16)[0]
    raw[reserve:reserve]=struct.pack('>QQ',start,size)
    struct.pack_into('>I',raw,4,len(raw))
    for field in (8,12):struct.pack_into('>I',raw,field,struct.unpack_from('>I',data,field)[0]+16)
    return bytes(raw)


def add_root_alias(data,name,props,child=None):
    """Insert a distinct valid root child before the existing root children."""
    raw=bytearray(data);strings=struct.unpack_from('>I',raw,12)[0]
    string_size=struct.unpack_from('>I',raw,32)[0];names=bytes(raw[strings:strings+string_size])
    def node(label):
        text=label.encode()+b'\0'
        return struct.pack('>I',1)+text+bytes((-len(text))%4)
    def property_bytes(key,value):
        off=names.find(key.encode()+b'\0');require(off>=0,'fixture property name missing')
        return struct.pack('>III',3,len(value),off)+value+bytes((-len(value))%4)
    inserted=node(name)+b''.join(property_bytes(k,v) for k,v in props.items())
    if child is not None:
        inserted+=node('alias-block')+property_bytes('reg',child)+struct.pack('>I',2)
    inserted+=struct.pack('>I',2)
    pos=struct.unpack_from('>I',raw,8)[0]+8  # empty root name and token
    while struct.unpack_from('>I',raw,pos)[0] in (3,4):
        if struct.unpack_from('>I',raw,pos)[0]==4:pos+=4
        else:
            size=struct.unpack_from('>I',raw,pos+4)[0];pos=(pos+12+size+3)&~3
    require(struct.unpack_from('>I',raw,pos)[0]==1,'no root-child insertion point')
    raw[pos:pos]=inserted
    struct.pack_into('>I',raw,4,len(raw));struct.pack_into('>I',raw,12,strings+len(inserted))
    struct.pack_into('>I',raw,36,struct.unpack_from('>I',data,36)[0]+len(inserted))
    return bytes(raw)


def linked_path_node(blob,record,syms,data,path):
    """Read the real linked libfdt consumer's selection for an alias fixture."""
    source=record['runtime_symbols']['_head']
    u,s=machine(blob,record,syms,source,data)
    scratch=INPUT_FDT+2*1024*1024
    u.mem_map(scratch,4096);u.mem_write(scratch,path.encode()+b'\0');stop=scratch+2048
    for reg,value in ((UC_ARM64_REG_X0,INPUT_FDT),(UC_ARM64_REG_X1,scratch),
                      (UC_ARM64_REG_SP,s['_stack_end']),(UC_ARM64_REG_LR,stop)):
        u.reg_write(reg,value)
    u.emu_start(s['fdt_path_offset'],stop,count=1000000)
    require(u.reg_read(UC_ARM64_REG_PC)==stop,'linked path lookup did not return')
    offset=u.reg_read(UC_ARM64_REG_X0)
    require(offset<len(data),'linked node offset invalid')
    pos=struct.unpack_from('>I',data,8)[0]+offset
    require(struct.unpack_from('>I',data,pos)[0]==1,'linked lookup did not select a node')
    result=data[pos+4:data.index(0,pos+4)].decode();del u;gc.collect();return result


def machine(blob,record,syms,source,fdt,*,fdt_address=INPUT_FDT):
    s={k:v[0] for k,v in syms.items()}
    intervals=[(source,source+len(blob)),*map(tuple,record['extents'].values()),
               (fdt_address,fdt_address+max(4096,len(fdt)))]
    u,_=shared.machine(intervals)
    u.mem_write(source,blob);u.mem_write(fdt_address,fdt)
    u.reg_write(UC_ARM64_REG_X0,fdt_address)
    return u,s


def run_case(blob,record,syms,source,fdt,*,expected,full=False,fdt_address=INPUT_FDT,state=None,el=1):
    u,s=machine(blob,record,syms,source,fdt,fdt_address=fdt_address)
    head=s['_head'];shift=source-head;terminal=[];passed=[];branched=[];writes=[0]
    sync=[];bss=[];initial_initrd=properties(fdt) if full else {}
    def stop(label):
        def on_stop(uc,address,length,user):terminal.append(label);uc.emu_stop()
        return on_stop
    u.hook_add(UC_HOOK_CODE,stop('reject'),begin=s['_reloc_rejected']+shift,end=s['_reloc_rejected']+shift)
    def guard_passed(uc,address,length,user):
        require(writes[0]==0,'pre-store guard wrote memory')
        require(uc.reg_read(UC_ARM64_REG_X28)==fdt_address,'guard lost current ABL x0')
        passed.append(True)
        if not full:terminal.append('guard');uc.emu_stop()
    u.hook_add(UC_HOOK_CODE,guard_passed,begin=s['_guard_passed']+shift,end=s['_guard_passed']+shift)
    if state is not None:
        def set_state(uc,address,length,user):uc.reg_write(UC_ARM64_REG_X10,state)
        at=s['_reloc_check_state']+shift;u.hook_add(UC_HOOK_CODE,set_state,begin=at,end=at)
    if el!=1:
        def set_el(uc,address,length,user):uc.reg_write(UC_ARM64_REG_X9,el*4)
        at=s['_reloc_check_el']+shift;u.hook_add(UC_HOOK_CODE,set_el,begin=at,end=at)
        if el==2:
            def read_el2(uc,address,length,user):
                uc.reg_write(UC_ARM64_REG_X10,0);uc.reg_write(UC_ARM64_REG_PC,address+4)
            at=s['_reloc_read_el2']+shift;u.hook_add(UC_HOOK_CODE,read_el2,begin=at,end=at)
    def written(uc,kind,address,length,value,user):
        require(passed and full,'input rejected after memory stores')
        require(address%min(length,8)==0,'unaligned loader store')
        require(any(a<=address and address+length<=b for a,b in record['extents'].values()),
                'loader wrote outside the pre-guarded extents')
        require(not (address<fdt_address+len(fdt) and fdt_address<address+length), 'incoming FDT was changed')
        require(not (address<source+s['_stub_end']-head and source<address+length),'live stub overwritten')
        writes[0]+=length
    u.hook_add(UC_HOOK_MEM_WRITE,written)
    def aligned_read(uc,kind,address,length,value,user):
        require(address%min(length,8)==0,'unaligned loader read including pre-store guard')
    u.hook_add(UC_HOOK_MEM_READ,aligned_read)
    if full:
        def at_branch(uc,address,length,user):
            require(uc.reg_read(UC_ARM64_REG_X5)==s['_start'],'wrong relocated branch')
            branched.append(True)
        u.hook_add(UC_HOOK_CODE,at_branch,begin=s['_reloc_branch']+shift,end=s['_reloc_branch']+shift)
        def at_main(uc,address,length,user):
            require(uc.reg_read(UC_ARM64_REG_X0)==fdt_address,'startup lost live FDT')
            require(bytes(uc.mem_read(s['__bss_start'],s['__bss_end']-s['__bss_start']))==
                    bytes(s['__bss_end']-s['__bss_start']),'BSS not zero')
            bss.append(True)
        u.hook_add(UC_HOOK_CODE,at_main,begin=s['main'],end=s['main'])
        def check_access(uc,kind,address,length,value,user):
            if branched:
                require(address%min(length,8)==0,'unaligned runtime access')
                require(s['_stack_end']-4096<=uc.reg_read(UC_ARM64_REG_SP)<=s['_stack_end'],
                        'runtime stack escaped its reserved page')
            start=initial_initrd[('/chosen','linux,initrd-start')][0]
            end=initial_initrd[('/chosen','linux,initrd-end')][0]
            a,b=struct.unpack_from('>Q',fdt,start)[0],struct.unpack_from('>Q',fdt,end)[0]
            require(not (address<b and a<address+length),'loader accessed inherited initrd')
        u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,check_access)
        target=record['extents']['kernel'][0]
        u.hook_add(UC_HOOK_CODE,stop('kernel'),begin=target,end=target)
        jump=s['load_kernel_and_jump']
        sync_offset=blob[jump-head:jump-head+64].find(shared.SYNC)
        require(sync_offset>=0,'kernel sync differs')
        def at_sync(uc,address,length,user):sync.append(True)
        u.hook_add(UC_HOOK_CODE,at_sync,begin=jump+sync_offset,end=jump+sync_offset)
    started=time.monotonic();u.emu_start(source,0,count=180_000_000)
    require(terminal==[expected],'unexpected actual-loader terminal: '+str(terminal))
    if full:
        require(passed==branched==bss==sync==[True],'full-loader stages incomplete')
        require([u.reg_read(v) for v in (UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3)]==[0,0,0],
                'kernel reserved arguments differ')
        require(u.reg_read(UC_ARM64_REG_X0)==record['extents']['fdt'][0],'kernel FDT pointer differs')
        require(bytes(u.mem_read(record['extents']['kernel'][0],record['kernel']['size']))==
                Path(record['kernel']['path']).read_bytes(),'kernel copy differs from exact vendor Image')
        require(bytes(u.mem_read(fdt_address,len(fdt)))==fdt,'incoming FDT bytes differ')
        cloned_address=record['extents']['fdt'][0]
        cloned_size=struct.unpack('>I',bytes(u.mem_read(cloned_address+4,4)))[0]
        require(40<=cloned_size<=record['fdt_capacity'],'cloned size exceeds admitted buffer')
        cloned=bytes(u.mem_read(cloned_address,cloned_size))
    else:cloned=None;require(writes[0]==0,'guard-only case wrote memory')
    row=dict(source=source,terminal=terminal[0],write_bytes=writes[0],entry_el=el,
        currentel_injected=el!=1,sctlr_injected=state,elapsed_seconds=round(time.monotonic()-started,3))
    del u;gc.collect();return row,cloned


def qualification(loader,output):
    loader,output=[Path(p).resolve() for p in (loader,output)]
    require(output.is_relative_to(ROOT/'workspace/private') and not output.exists(),'fresh private qualification')
    record=json.loads((loader/'result.json').read_text())
    require(record['status']==STATUS,'wrong loader family')
    for name in ('loader','elf','kernel','retained_fdt'):
        require(pin(record[name]['path'])==record[name],'artifact changed: '+name)
    output.mkdir(mode=0o700,parents=True)
    blob=Path(record['loader']['path']).read_bytes();fdt=Path(record['retained_fdt']['path']).read_bytes()
    syms=symbols(record['elf']['path']);source=0xa8000000;rows=[]
    def retain(row):
        rows.append(row)
        with (output/'cases.jsonl').open('a') as stream:
            stream.write(json.dumps(row,sort_keys=True)+'\n');stream.flush()
    cases=[('valid-live-FDT',fdt,'guard',{}),('bad-magic',b'BAD!'+fdt[4:],'reject',{}),
        ('short-header',header(fdt,4,39),'reject',{}),('oversize',header(fdt,4,record['fdt_capacity']),'reject',{}),
        ('old-version',header(fdt,20,16),'reject',{}),
        ('overlapping-blocks',header(fdt,12,struct.unpack_from('>I',fdt,8)[0]),'reject',{}),
        ('unbounded-strings',header(fdt,32,len(fdt)),'reject',{}),
        ('FDT-at-staging',fdt,'reject',{'fdt_address':record['extents']['staging'][0]}),
        ('FDT-at-kernel',fdt,'reject',{'fdt_address':record['extents']['kernel'][0]}),
        ('FDT-at-destination',fdt,'reject',{'fdt_address':record['extents']['fdt'][0]}),
        ('source-page-unaligned',fdt,'reject',{'source':source+16}),
        ('EL2-guard-result',fdt,'guard',{'el':2}),('EL3-reject',fdt,'reject',{'el':3})]
    for name,value in [('mmu',1),('dcache',4),('icache',4096),('big-endian',1<<25)]:
        cases.append((name,fdt,'reject',{'state':value}))
    for name,(a,b) in record['extents'].items():
        cases.append(('memreserve-'+name,add_reservation(fdt,a,4096),'reject',{}))
        value=set_property(fdt,'/chosen','linux,initrd-start',struct.pack('>Q',a))
        value=set_property(value,'/chosen','linux,initrd-end',struct.pack('>Q',a+4096))
        cases.append(('initrd-'+name,value,'reject',{}))
    offsets=properties(fdt)
    reserved=next(p for p,n in offsets if p.startswith('/reserved-memory/') and n=='reg')
    for name,(a,b) in record['extents'].items():
        cases.append(('fixed-reserve-'+name,set_property(fdt,reserved,'reg',struct.pack('>QQ',a,4096)),'reject',{}))
    cases.extend([
        ('root-cells',set_property(fdt,'/','#address-cells',struct.pack('>I',1)),'reject',{}),
        ('reserve-cells',set_property(fdt,'/reserved-memory','#size-cells',struct.pack('>I',1)),'reject',{}),
        ('reserve-translation',set_property(fdt,'/reserved-memory','ranges',bytes(16)),'reject',{}),
        ('duplicate-initrd',set_property(fdt,'/chosen','linux,initrd-start',bytes(8),duplicate=True),'reject',{}),
        ('initrd-width',set_property(fdt,'/chosen','linux,initrd-start',bytes(4)),'reject',{}),
        ('initrd-reversed',set_property(fdt,'/chosen','linux,initrd-end',bytes(8)),'reject',{}),
        ('memory-drift',set_property(fdt,'/memory','reg',bytes(80)),'reject',{}),
        ('preexisting-marker',set_property(fdt,'/chosen',record['marker_property'],record['marker'].encode()),'reject',{}),
        ('empty-preexisting-marker',set_property(fdt,'/chosen',record['marker_property'],b''),'reject',{}),
        ('reserve-overflow',add_reservation(fdt,2**64-4096,8192),'reject',{})])
    source_initrd=set_property(fdt,'/chosen','linux,initrd-start',struct.pack('>Q',source+0x100000))
    source_initrd=set_property(source_initrd,'/chosen','linux,initrd-end',struct.pack('>Q',source+0x101000))
    cases.append(('initrd-overlaps-loader-source',source_initrd,'reject',{}))
    stage=record['extents']['staging'][0]
    aliases=[('chosen@0',dict(**{'linux,initrd-start':struct.pack('>Q',stage),
                               'linux,initrd-end':struct.pack('>Q',stage+4096)}),None,'/chosen'),
             ('reserved-memory@0',{'#address-cells':struct.pack('>I',2),'#size-cells':struct.pack('>I',2),
                                    'ranges':b''},struct.pack('>QQ',stage,4096),'/reserved-memory'),
             ('memory@0',{'device_type':b'memory\0','reg':bytes(80)},None,'/memory')]
    for name,props,child,path in aliases:
        data=add_root_alias(fdt,name,props,child)
        require(linked_path_node(blob,record,syms,data,path)==name,'alias fixture lacks actual-consumer mismatch')
        (output/(name.replace('@','-')+'.dtb')).write_bytes(data)
        cases.append(('reject-consumer-alias-'+name,data,'reject',{}))
    cases.append(('reject-other-memory-node',add_root_alias(fdt,'unexpected',
        {'device_type':b'memory\0','reg':bytes(80)},None),'reject',{}))
    for name,data,expected,options in cases:
        options=dict(options);place=options.pop('source',source)
        row,_=run_case(blob,record,syms,place,data,expected=expected,**options)
        row.update(name=name,fixture_sha256=hashlib.sha256(data).hexdigest());retain(row)
        print(json.dumps(dict(case=name,terminal=row['terminal'],seconds=row['elapsed_seconds'])),flush=True)
    # Retained normal EFI path supplies 64 possible 32 KiB source displacements.
    # This is a conditional placement corpus, not measured physical ABL state.
    for ordinal in range(64):
        place=source+(ordinal<<15)
        row,_=run_case(blob,record,syms,place,fdt,expected='guard')
        row.update(name='retained-source-'+str(ordinal));retain(row)
    for label,place in [('normal-first',source),('normal-last',source+(63<<15)),
                        ('same',record['runtime_symbols']['_head']),('forward',0xaf000000)]:
        row,cloned=run_case(blob,record,syms,place,fdt,expected='kernel',full=True)
        path=output/(label+'.dtb');path.write_bytes(cloned)
        tree=nodes(path)
        require(tree['/chosen'].pop(record['marker_property'])==record['marker'].encode(),'loader marker differs')
        require(tree==nodes(record['retained_fdt']['path']) and
                memreserve(path)==memreserve(record['retained_fdt']['path']) and cloned[20:32]==fdt[20:32],
                'clone changed existing FDT properties, reservations, version or boot CPU')
        row.update(name='full-'+label,cloned_fdt=pin(path));retain(row)
        print(json.dumps(dict(case=row['name'],terminal=row['terminal'],seconds=row['elapsed_seconds'])),flush=True)
    copies=shared.copy_cases(blob,syms)
    result=dict(status='PASS_H0_ACTUAL_ARM64_LOADER_ANDROID',loader_sha256=record['loader']['sha256'],
        elf_sha256=record['elf']['sha256'],source_pins=[pin(__file__),pin(COMMON/'qualify_loader.py')],
        retained_fdt=record['retained_fdt'],cases=rows,aligned_copy_cases=copies,
        physical_entry_proved=False,actual_cache_coherency_proved=False,device_actions=0)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],cases=len(rows),copy_cases=copies)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--loader',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();qualification(a.loader,a.output)
