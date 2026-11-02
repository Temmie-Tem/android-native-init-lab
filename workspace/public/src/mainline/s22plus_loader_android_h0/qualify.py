#!/usr/bin/env python3
"""Exercise the actual Android-control loader, including its pre-store guard."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import time

from build import COMMON, ROOT, STATUS, digest, pin, require, symbols
import s22plus_loader_android_profile_v1 as profile
sys.path.insert(0,str(COMMON))
from prepare import nodes, memreserve
import qualify_loader as shared
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MEM_WRITE
from unicorn.arm64_const import (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2,
    UC_ARM64_REG_X3, UC_ARM64_REG_X5, UC_ARM64_REG_X9, UC_ARM64_REG_X10,
    UC_ARM64_REG_X28, UC_ARM64_REG_PC, UC_ARM64_REG_SP, UC_ARM64_REG_LR)

INPUT_FDT = 0xb4000000
LOG_BASE = 0x800200000
LOG_SIZE = 0x200000


def log_seed(idx=profile.LOGM_PAYLOAD+300,magic=0x4d474f4c):
    return struct.pack('<IIII',7,magic,idx,19)+bytes([0xa5])*(LOG_SIZE-16)


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
        require(any(p==path for p,_ in offsets),'fixture insertion path')
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


def reduced_fdt(data,keep,stem):
    """A named instruction fixture; the complete real tree stays in EL tests."""
    offsets=properties(data);tree={'props':{},'children':{}}
    for (path,name),(pos,length,_) in offsets.items():
        if not keep(path):continue
        node=tree
        for part in path.split('/')[1:]:
            if part:node=node['children'].setdefault(part,{'props':{},'children':{}})
        node['props'][name]=data[pos:pos+length]
    def render(node,label):
        return label+' {\n'+''.join(name+' = ['+' '.join(f'{b:02x}' for b in value)+'];\n'
            for name,value in node['props'].items())+''.join(render(child,label) for label,child in node['children'].items())+'};\n'
    reserve=struct.unpack_from('>I',data,16)[0];declarations=''
    while True:
        start,size=struct.unpack_from('>QQ',data,reserve);reserve+=16
        if not start and not size:break
        declarations+=f'/memreserve/ 0x{start:x} 0x{size:x};\n'
    source=stem.with_suffix('.dts');output=stem.with_suffix('.dtb')
    source.write_text('/dts-v1/;\n'+declarations+render(tree,'/'))
    subprocess.run(['dtc','-q','-b',str(struct.unpack_from('>I',data,28)[0]),'-I','dts','-O','dtb',
                    '-o',str(output),str(source)],check=True)
    return output.read_bytes()


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
    if 'logm_control' in record:intervals.append((LOG_BASE,LOG_BASE+LOG_SIZE))
    u,_=shared.machine(intervals)
    if 'logm_control' in record:u.mem_write(LOG_BASE,log_seed())
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
        log_write='logm_control' in record and LOG_BASE+16<=address and address+length<=LOG_BASE+LOG_SIZE
        if log_write:require(length==1,'LOGM write was not one byte')
        require(log_write or any(a<=address and address+length<=b for a,b in record['extents'].values()),
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
    require(terminal==[expected],'unexpected actual-loader terminal: '+str(terminal)+
        '; pc='+hex(u.reg_read(UC_ARM64_REG_PC))+'; nearest='+
        str(sorted(((v[0],k) for k,v in syms.items() if v[0]<=u.reg_read(UC_ARM64_REG_PC)),reverse=True)[:2]))
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
        if 'logm_control' in record:
            pos,length,_=properties(cloned)[('/chosen',profile.LOGM_PROPERTY)]
            report=profile.logm_report(cloned[pos:pos+length],record['logm_control']['configuration'])
            require(report['status']=='READBACK_MATCH','full loader did not complete LOGM readback')
            expected=bytearray(log_seed());at=16+report['slot_offset']
            expected[at:at+128]=bytes.fromhex(record['logm_control']['configuration']['frame_hex'])
            require(bytes(u.mem_read(LOG_BASE,LOG_SIZE))==expected,'full-loader LOGM write escaped exact slot/header')
    else:cloned=None;require(writes[0]==0,'guard-only case wrote memory')
    row=dict(source=source,terminal=terminal[0],write_bytes=writes[0],entry_el=el,
        currentel_injected=el!=1,sctlr_injected=state,elapsed_seconds=round(time.monotonic()-started,3))
    del u;gc.collect();return row,cloned


def logm_cases(blob,record,syms,cloned,output):
    """Actual linked C/ABI/volatile-access behavior; no emulated physical claim."""
    from unicorn import arm64_const as regs
    config=profile.logm_binding(record['logm_control'],record['marker'])
    frame=bytes.fromhex(config['frame_hex']);seed=bytes.fromhex(config['report_seed_hex'])
    # The local writer corpus uses just its actual retained DT declarations.
    # Whole real-tree traversal remains in full-loader and actual-EL fixtures;
    # thousands of unrelated nodes need not recur in every header mutation.
    selected=('/', '/chosen','/reserved-memory','/reserved-memory/sec_debug_region_log@8001FF000',
              '/soc','/soc/samsung,kernel_log_buf')
    cloned=reduced_fdt(cloned,lambda path:path in selected,output/'logm-fixture')
    pos,length,_=properties(cloned)[('/chosen',profile.LOGM_PROPERTY)]
    require(length==128,'LOGM report size differs')
    fresh=bytearray(cloned);fresh[pos:pos+128]=seed
    fdt_address=record['extents']['fdt'][0];report_address=fdt_address+pos
    cases=[];s={k:v[0] for k,v in syms.items()}
    indices=(0,255,256,257,383,384,profile.LOGM_PAYLOAD-1,profile.LOGM_PAYLOAD,
             profile.LOGM_PAYLOAD+1,profile.LOGM_PAYLOAD+255,profile.LOGM_PAYLOAD+256,
             profile.LOGM_PAYLOAD+257,2*profile.LOGM_PAYLOAD+129,0xffffffff)
    inputs=[('index-'+str(i),i,0x4d474f4c,None,None,4,0,bytes(fresh)) for i in indices]
    inputs.append(('bad-magic',400,0,None,None,4,0,bytes(fresh)))
    for word in range(4):inputs.append(('header-drift-'+str(word),400,0x4d474f4c,word,None,4,0,bytes(fresh)))
    inputs += [('readback-mismatch',400,0x4d474f4c,None,'body',4,0,bytes(fresh)),
               ('postcommit-header-drift',400,0x4d474f4c,None,'header',4,0,bytes(fresh))]
    for count in (4,64,130,135):
        inputs.append(('interrupted-store-'+str(count),400,0x4d474f4c,None,'interrupt-'+str(count),4,0,bytes(fresh)))
    for name,el,state in [('EL2',8,0),('EL3-skip',12,0),('MMU-skip',4,1),('cache-skip',4,4),('endian-skip',4,1<<25)]:
        inputs.append((name,400,0x4d474f4c,None,None,el,state,bytes(fresh)))
    log='/soc/samsung,kernel_log_buf';reserved='/reserved-memory/sec_debug_region_log@8001FF000'
    for name,path,key,value in [('wrong-reg',log,'reg',bytes(16)),('wrong-region',log,'memory-region',bytes(4)),
        ('wrong-reservation',reserved,'reg',bytes(16)),('no-map',reserved,'no-map',b''),
        ('disabled',log,'status',b'disabled\0'),('wrong-strategy',log,'sec,strategy',bytes(4)),
        ('alternate-phandle',reserved,'linux,phandle',struct.pack('>I',0x999)),
        ('ibm-phandle',reserved,'ibm,phandle',struct.pack('>I',0x999))]:
        inputs.append((name,400,0x4d474f4c,None,None,4,0,set_property(bytes(fresh),path,key,value)))
    for name,path,key in [('duplicate-log-reg',log,'reg'),('duplicate-region',log,'memory-region'),
                          ('duplicate-phandle',reserved,'phandle'),('duplicate-compatible',log,'compatible')]:
        at,n,_=properties(fresh)[(path,key)]
        inputs.append((name,400,0x4d474f4c,None,None,4,0,
                       set_property(bytes(fresh),path,key,bytes(fresh[at:at+n]),duplicate=True)))
    for name,props in [('duplicate-log-node',{'compatible':b'samsung,kernel_log_buf\0'}),
                       ('duplicate-reference',{'phandle':struct.pack('>I',0x5ad)})]:
        inputs.append((name,400,0x4d474f4c,None,None,4,0,add_root_alias(bytes(fresh),'unexpected',props)))
    for name,idx,magic,drift,corrupt,el,state,fdt in inputs:
        u,_=machine(blob,record,syms,s['_head'],fdt,fdt_address=fdt_address)
        original=log_seed(idx,magic);u.mem_write(LOG_BASE,original)
        rp=properties(fdt)[('/chosen',profile.LOGM_PROPERTY)][0]+fdt_address
        stop=INPUT_FDT+0x1000000;u.mem_map(stop,4096)
        before_regs={n:0x12340000+n for n in range(19,30)}
        for n,value in before_regs.items():u.reg_write(getattr(regs,'UC_ARM64_REG_X'+str(n)),value)
        stack=s['_stack_end'];u.reg_write(UC_ARM64_REG_SP,stack);u.reg_write(UC_ARM64_REG_LR,stop)
        u.reg_write(UC_ARM64_REG_X0,fdt_address)
        cursor=idx%profile.LOGM_PAYLOAD;slot=cursor-256 if cursor>=256 else profile.LOGM_PAYLOAD-256
        address=LOG_BASE+16+slot;writes=[];reads=[];injected=[]
        def code(uc,pc,size,user):
            op=int.from_bytes(uc.mem_read(pc,4),'little');kind=op&~31
            if kind in (0xd5384240,0xd5381000,0xd53c1000):
                uc.reg_write(getattr(regs,'UC_ARM64_REG_X'+str(op&31)),el if kind==0xd5384240 else state)
                uc.reg_write(UC_ARM64_REG_PC,pc+4)
        def memory(uc,kind,a,n,value,user):
            require(a%min(n,8)==0,'LOGM fixture observed an unaligned access')
            require(stack-4096<=uc.reg_read(UC_ARM64_REG_SP)<=stack,'LOGM C stack escaped reserved page')
            if kind==UC_MEM_WRITE:
                require((stack-4096<=a and a+n<=stack) or (rp<=a and a+n<=rp+128) or
                        (address<=a and a+n<=address+128),'LOGM C wrote outside stack/report/slot')
                if LOG_BASE<=a<LOG_BASE+LOG_SIZE:
                    require(n==1 and address<=a<a+1<=address+128,'LOGM payload store width/bound differs')
                    writes.append((a,value))
                    if corrupt and corrupt.startswith('interrupt-') and len(writes)==int(corrupt.split('-')[1]):
                        injected.append(corrupt);uc.emu_stop()
                    if drift is not None and a==address+127:
                        uc.mem_write(LOG_BASE+4*drift,struct.pack('<I',0x12345678));injected.append('header-before-commit')
                    if corrupt and len(writes)==136:
                        if corrupt=='body':uc.mem_write(address+64,b'\xff')
                        else:uc.mem_write(LOG_BASE,struct.pack('<I',0x12345678))
                        injected.append(corrupt)
            if LOG_BASE<=a<LOG_BASE+LOG_SIZE:
                if kind!=UC_MEM_WRITE:
                    require((LOG_BASE<=a and a+n<=LOG_BASE+16 and n==4) or
                        (address<=a and a+n<=address+128 and n==1),'LOGM read width/bound differs')
                    reads.append((a,n))
        u.hook_add(UC_HOOK_CODE,code)
        u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,memory)
        u.emu_start(s['g0q_logm_control'],stop,count=5_000_000)
        if corrupt and corrupt.startswith('interrupt-'):
            actual=bytes(u.mem_read(LOG_BASE,LOG_SIZE));report=bytes(u.mem_read(rp,128))
            require(injected==[corrupt] and report[12:16]==bytes(4),
                    'interrupted writer acquired a finalized report')
            require(actual[:16+slot]==original[:16+slot] and actual[16+slot+128:]==original[16+slot+128:] and
                    actual[16+slot:16+slot+128]!=frame,'interrupted store escaped slot or forged a complete frame')
            try:profile.logm_report(report,config)
            except ValueError:pass
            else:raise ValueError('interrupted writer report was accepted')
            cases.append(dict(name=name,status='INTERRUPTED_UNFINALIZED',log_store_attempts=len(writes),injected=injected))
            print(json.dumps(dict(logm_case=name,outcome='INTERRUPTED_UNFINALIZED')),flush=True)
            del u;gc.collect();continue
        require(u.reg_read(UC_ARM64_REG_PC)==stop,'LOGM writer did not return')
        require(u.reg_read(UC_ARM64_REG_SP)==stack and all(u.reg_read(getattr(regs,'UC_ARM64_REG_X'+str(n)))==v
                for n,v in before_regs.items()),'LOGM C violated callee-saved registers/stack')
        result=profile.logm_report(bytes(u.mem_read(rp,128)),config)
        expected=('SKIP_STATE' if el not in (4,8) or state else 'SKIP_FDT' if fdt!=bytes(fresh)
            else 'SKIP_MAGIC' if magic!=0x4d474f4c else 'SKIP_INDEX' if idx<256 else
            'HEADER_CHANGED' if drift is not None else 'READBACK_MISMATCH' if corrupt=='body' else 'READBACK_MATCH')
        require(result['status']==expected,'LOGM outcome mismatch: '+name+' '+str(result))
        require(len(writes)==(0 if expected.startswith('SKIP') else 128 if drift is not None else 136),'LOGM store budget differs')
        if expected in ('SKIP_STATE','SKIP_FDT'):require(not reads,'LOGM guard read shared memory')
        actual=bytes(u.mem_read(LOG_BASE,LOG_SIZE));expected_ring=bytearray(original)
        if writes:
            expected_ring[16+slot:16+slot+128]=(bytes(8)+frame[8:] if drift is not None else frame)
        if drift is not None:struct.pack_into('<I',expected_ring,4*drift,0x12345678)
        if corrupt=='body':expected_ring[16+slot+64]=255
        if corrupt=='header':struct.pack_into('<I',expected_ring,0,0x12345678)
        require(actual==expected_ring,'LOGM fixture changed bytes outside declared effect/injection')
        if expected=='READBACK_MATCH' and corrupt is None:
            from s22plus_fyg8_retained_snapshot_model import stock_snapshot,Header
            snapshot=stock_snapshot(actual[16:],Header(*struct.unpack_from('<IIII',actual)))
            require(frame in snapshot.data,'actual writer frame is invisible to Samsung snapshot model')
        row=dict(name=name,writer=result,log_store_bytes=len(writes),log_reads=len(reads),injected=injected,
                 context_from_instruction_fixture=True)
        cases.append(row);print(json.dumps(dict(logm_case=name,outcome=expected)),flush=True)
        del u;gc.collect()
    value=dict(status='PASS_H0_ACTUAL_LOADER_LOGM_CONTROL',configuration=config,cases=cases,
               physical_cache_coherence_proved=False)
    (output/'logm-cases.json').write_text(json.dumps(value,indent=2)+'\n')
    return value


def logm_fdt_capacity(blob,record,syms,fdt,output):
    limit=record['fdt_capacity']-512
    empty=set_property(fdt,'/chosen','codex,h0-padding',b'')
    count=(limit-len(empty))&~3
    require(count>0,'headroom fixture needs no padding')
    padded=set_property(fdt,'/chosen','codex,h0-padding',bytes(count))
    padded+=bytes(limit-len(padded));padded=header(padded,4,limit)
    too_large=header(padded+b'\0',4,limit+1)
    rows=[]
    for name,data,expected in [('maximum-input',padded,'guard'),('maximum-plus-one',too_large,'reject')]:
        row,_=run_case(blob,record,syms,0xa8000000,data,expected=expected)
        row.update(name=name,fixture_sha256=digest_bytes(data));rows.append(row)
    s={k:v[0] for k,v in syms.items()};buf=s['fdt_buf'];stack=s['_stack_end'];stop=INPUT_FDT+0x1000000
    for name,capacity,success in [('exact-admitted-buffer',record['fdt_capacity'],True),
                                  ('insufficient-property-space',limit+64,False)]:
        u,_=machine(blob,record,syms,s['_head'],padded)
        u.mem_map(stop,4096)
        for reg,value in ((UC_ARM64_REG_X0,INPUT_FDT),(UC_ARM64_REG_X1,buf),
                          (UC_ARM64_REG_X2,capacity),(UC_ARM64_REG_SP,stack),(UC_ARM64_REG_LR,stop)):
            u.reg_write(reg,value)
        writes=[0]
        def access(uc,kind,address,length,value,user):
            require(address%min(length,8)==0,'FDT capacity case used an unaligned access')
            require(not (address<LOG_BASE+LOG_SIZE and LOG_BASE<address+length),
                    'FDT allocation/packing accessed LOGM')
            if kind==UC_MEM_WRITE:
                require(buf<=address and address+length<=buf+capacity or
                        stack-4096<=address and address+length<=stack,'FDT allocation escaped its buffer/stack')
                writes[0]+=length
        u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,access)
        u.emu_start(s['ramdisk_handler_patch_dtb'],stop,count=128_000_000)
        require(u.reg_read(UC_ARM64_REG_PC)==stop,'FDT capacity function did not return')
        result=u.reg_read(UC_ARM64_REG_X0)&0xffffffff
        require((result==0)==success,'FDT allocation boundary result differs')
        if success:
            size=struct.unpack('>I',bytes(u.mem_read(buf+4,4)))[0]
            packed=bytes(u.mem_read(buf,size));props=properties(packed)
            p,n,_=props[('/chosen',profile.LOGM_PROPERTY)]
            require(n==128 and packed[p:p+n]==bytes.fromhex(record['logm_control']['configuration']['report_seed_hex']),
                    'preallocated report did not fit at maximum input')
            (output/'maximum-packed.dtb').write_bytes(packed)
        rows.append(dict(name=name,buffer_capacity=capacity,input_bytes=limit,
                         returncode=result if result<2**31 else result-2**32,write_bytes=writes[0],logm_accesses=0))
        del u;gc.collect()
    return rows


def digest_bytes(data):return hashlib.sha256(data).hexdigest()


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
    if 'logm_control' in record:
        cases.extend([
            ('preexisting-logm-report',set_property(fdt,'/chosen',profile.LOGM_PROPERTY,bytes(128)),'reject',{}),
            ('FDT-in-LOGM',fdt,'reject',{'fdt_address':LOG_BASE}),
            ('source-in-LOGM',fdt,'reject',{'source':LOG_BASE})])
        overlap=set_property(fdt,'/chosen','linux,initrd-start',struct.pack('>Q',LOG_BASE))
        overlap=set_property(overlap,'/chosen','linux,initrd-end',struct.pack('>Q',LOG_BASE+4096))
        cases.append(('initrd-in-LOGM',overlap,'reject',{}))
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
    full_fdt=fdt
    if 'logm_control' in record:
        full_fdt=reduced_fdt(fdt,lambda path:path in ('/','/chosen','/memory','/soc','/soc/samsung,kernel_log_buf') or
                            path.startswith('/reserved-memory'),output/'full-geometry-fixture')
    for label,place in [('normal-first',source),('normal-last',source+(63<<15)),
                        ('same',record['runtime_symbols']['_head']),('forward',0xaf000000)]:
        row,cloned=run_case(blob,record,syms,place,full_fdt,expected='kernel',full=True)
        path=output/(label+'.dtb');path.write_bytes(cloned)
        tree=nodes(path)
        require(tree['/chosen'].pop(record['marker_property'])==record['marker'].encode(),'loader marker differs')
        if 'logm_control' in record:tree['/chosen'].pop(profile.LOGM_PROPERTY)
        fixture_path=output/'full-geometry-fixture.dtb' if 'logm_control' in record else Path(record['retained_fdt']['path'])
        require(tree==nodes(fixture_path) and
                memreserve(path)==memreserve(fixture_path) and cloned[20:32]==full_fdt[20:32],
                'clone changed existing FDT properties, reservations, version or boot CPU')
        row.update(name='full-'+label,cloned_fdt=pin(path));retain(row)
        print(json.dumps(dict(case=row['name'],terminal=row['terminal'],seconds=row['elapsed_seconds'])),flush=True)
    copies=shared.copy_cases(blob,syms)
    result=dict(status='PASS_H0_ACTUAL_ARM64_LOADER_ANDROID',loader_sha256=record['loader']['sha256'],
        elf_sha256=record['elf']['sha256'],source_pins=[pin(__file__),pin(COMMON/'qualify_loader.py')],
        retained_fdt=record['retained_fdt'],cases=rows,aligned_copy_cases=copies,
        physical_entry_proved=False,actual_cache_coherency_proved=False,device_actions=0)
    if 'logm_control' in record:
        result['logm_control']=logm_cases(blob,record,syms,cloned,output)
        result['logm_control']['fdt_capacity_cases']=logm_fdt_capacity(blob,record,syms,fdt,output)
    if 'logm_control' in record:result['full_copy_fixture']=pin(output/'full-geometry-fixture.dtb')
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],cases=len(rows),copy_cases=copies)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--loader',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();qualification(a.loader,a.output)
