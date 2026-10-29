#!/usr/bin/env python3
"""Execute actual linked early marker routines in bounded host fixtures."""
import argparse
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn import arm64_const as regs

from prepare import ROOT,digest,require
import retained_marker as marker

def symbols(path):
    with Path(path).open('rb') as f:
        return {s.name:s['st_value'] for s in ELFFile(f).get_section_by_name('.symtab').iter_symbols()}

def linked(raw,symbols,linkbase,physical,name):
    start,end=symbols[name],symbols[name+'_end']
    require(linkbase<=start<end<=linkbase+len(raw),'marker is outside actual image')
    labels={k:physical+v-linkbase for k,v in symbols.items() if k.startswith(name)}
    return dict(code=raw[start-linkbase:end-linkbase],address=physical+start-linkbase,labels=labels,name=name)

def exercise(routine,stage,config,*,idx=marker.PAYLOAD+300,magic=0x4d474f4c,state=0,el=1,change=None,cut=None):
    address=routine['address'];code=routine['code'];labels=routine['labels'];name=routine['name']
    u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.reg_write(regs.UC_ARM64_REG_PSTATE,5)
    u.cpr_write(3,0,1,0,0,0);u.cpr_write(3,4,1,0,0,0)
    low=address&~4095;high=(address+len(code)+4095)&~4095
    u.mem_map(low,high-low);u.mem_write(address,code)
    u.mem_map(marker.BASE,marker.REGION)
    before=struct.pack('<IIII',7,magic,idx,123)+b'\xa5'*marker.PAYLOAD
    u.mem_write(marker.BASE,before)
    stop=0x10000000;u.mem_map(stop,4096)
    protected={i:(0x1234567800000000+i) for i in (*range(9),*range(18,30))}
    for i,value in protected.items():u.reg_write(getattr(regs,'UC_ARM64_REG_X'+str(i)),value)
    u.reg_write(regs.UC_ARM64_REG_LR,stop);u.reg_write(regs.UC_ARM64_REG_SP,stop+2048)
    # Unicorn does not execute at EL2/EL3; inject guard results only. Separate
    # QEMU fixtures execute the real MRS instructions at those actual levels.
    if el!=1:
        def set_el(uc,pc,n,user):uc.reg_write(regs.UC_ARM64_REG_X9,el*4)
        u.hook_add(UC_HOOK_CODE,set_el,begin=labels[name+'_check_el'],end=labels[name+'_check_el'])
        if el==2:
            def read_el2(uc,pc,n,user):uc.reg_write(regs.UC_ARM64_REG_X10,0);uc.reg_write(regs.UC_ARM64_REG_PC,pc+4)
            u.hook_add(UC_HOOK_CODE,read_el2,begin=labels[name+'_read_el2'],end=labels[name+'_read_el2'])
    if state:
        def set_state(uc,pc,n,user):uc.reg_write(regs.UC_ARM64_REG_X10,state)
        u.hook_add(UC_HOOK_CODE,set_state,begin=labels[name+'_check_state'],end=labels[name+'_check_state'])
    if change is not None:
        def interfere(uc,pc,n,user):uc.mem_write(marker.BASE+change,struct.pack('<I',0x12345678))
        u.hook_add(UC_HOOK_CODE,interfere,begin=labels[name+'_recheck'],end=labels[name+'_recheck'])
    c=idx%marker.PAYLOAD;position=(c-marker.SPAN if c>=marker.SPAN else marker.PAYLOAD-marker.SPAN)+marker.slot(config,stage)
    admitted=el in (1,2) and not state&0x2000005 and magic==0x4d474f4c and idx>=marker.SPAN
    writes=[];reads=[]
    def access(uc,kind,a,n,value,user):
        require(a%min(n,8)==0,'unaligned marker access')
        if kind==16: # UC_MEM_READ
            reads.append((a,n))
            require(address<=a<a+n<=address+len(code) or marker.BASE<=a<a+n<=marker.BASE+marker.HEADER,
                    'marker read outside header/literal')
        else:
            writes.append((a,n))
            require(admitted and n==1 and marker.BASE+marker.HEADER+position<=a<marker.BASE+marker.HEADER+position+marker.SLOT,
                    'marker wrote outside its eligible slot')
            if cut is not None and len(writes)==cut:u.emu_stop()
    u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,access)
    u.emu_start(address,stop,count=5000)
    if cut is None:require(u.reg_read(regs.UC_ARM64_REG_PC)==stop,'marker did not return within instruction bound')
    for i,value in protected.items():require(u.reg_read(getattr(regs,'UC_ARM64_REG_X'+str(i)))==value,'startup register changed')
    require(u.reg_read(regs.UC_ARM64_REG_LR)==stop and u.reg_read(regs.UC_ARM64_REG_SP)==stop+2048,'LR/SP changed')
    after=bytes(u.mem_read(marker.BASE,marker.REGION));expected=bytearray(before)
    if cut is not None:
        a=marker.HEADER+position;b=a+marker.SLOT
        require(after[:a]==before[:a] and after[b:]==before[b:],'interrupted writer escaped slot')
        require(after[a:b]!=bytes.fromhex(config['frames'][str(stage)]),'partial store sequence created a complete new frame')
        return dict(stage=stage,cut_after_hook=cut,complete_frame=False,registers_preserved=True)
    if change is not None:struct.pack_into('<I',expected,change,0x12345678)
    if admitted:
        frame=bytes.fromhex(config['frames'][str(stage)])
        expected[marker.HEADER+position:marker.HEADER+position+marker.SLOT]=frame if change is None else bytes(8)+frame[8:]
    require(after==expected,'marker bytes or outside-slot canaries differ')
    if not admitted:require(not writes,'ineligible marker wrote')
    if el not in (1,2) or state&0x2000005:require(not reads,'state rejected after log access')
    return dict(stage=stage,idx=idx,el=el,state=state,header_mutation=change,admitted=admitted,
                committed=admitted and change is None,payload_store_bytes=len(writes),registers_preserved=True)

def matrix(routine,stage,config):
    cases=[]
    indices=sorted({0,255,256,marker.PAYLOAD-1,marker.PAYLOAD,marker.PAYLOAD+1,0xffffffff}|
                   {marker.PAYLOAD+x for x in range(256,272)})
    for idx in indices:cases.append(exercise(routine,stage,config,idx=idx))
    for el in (0,2,3):cases.append(exercise(routine,stage,config,el=el))
    for state in (1,4,5,1<<25,1<<12):cases.append(exercise(routine,stage,config,state=state))
    cases.append(exercise(routine,stage,config,magic=0))
    for change in (0,4,8,12):cases.append(exercise(routine,stage,config,change=change))
    for cut in range(1,136):cases.append(exercise(routine,stage,config,cut=cut))
    return cases

def qualify(loader,output):
    loader,output=loader.resolve(),output.resolve();require(output.is_relative_to(ROOT/'workspace/private'),'private output')
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    record=json.loads((loader/'result.json').read_text());marked=record['retained_marker']
    cfgpath=Path(marked['config']['path']);require(digest(cfgpath)==marked['config']['sha256'],'marker config changed')
    config=json.loads(cfgpath.read_text());manifest=json.loads(Path(record['initramfs_manifest']).read_text())
    key=Path(manifest['key_path']).read_bytes();marker.validate(config,manifest['candidate_id'],key)
    rows=[];routines=[]
    specs=(
        (1,Path(record['loader']['path']),Path(record['elf']['path']),record['runtime_symbols']['_head'],record['runtime_symbols']['_head'],'s22_retained_loader'),
        (2,Path(record['kernel']['image']),Path(record['kernel']['image']).parents[3]/'vmlinux',None,record['extents']['kernel-runtime'][0],'s22_retained_kernel'))
    if marker.version(config)==2:
        specs=((3,Path(record['kernel']['image']),Path(record['kernel']['image']).parents[3]/'vmlinux',None,
                record['extents']['kernel-runtime'][0],'s22_retained_pre_mmu'),)
    elif marker.version(config) in (3,4):specs=()
    for stage,blob,elf,linkbase,physical,name in specs:
        raw=blob.read_bytes();syms=symbols(elf);linkbase=linkbase if linkbase is not None else syms['_text']
        require(digest(blob)==(record['loader']['sha256'] if stage==1 else record['kernel']['sha256']),'actual marker artifact changed')
        routine=linked(raw,syms,linkbase,physical,name)
        fstart=syms[name+'_frame']-linkbase
        require(raw[fstart:fstart+marker.SLOT]==bytes.fromhex(config['frames'][str(stage)]),'actual linked frame differs')
        hook=syms['load_kernel_and_jump' if stage==1 else '__primary_switch' if stage==3 else 'primary_entry']
        instruction=struct.unpack_from('<I',raw,hook-linkbase)[0]
        if stage in (1,3):
            require(instruction==0xd503245f,'loader BTI landing instruction differs')
            hook+=4;instruction=struct.unpack_from('<I',raw,hook-linkbase)[0]
        immediate=instruction&0x3ffffff
        if immediate&(1<<25):immediate-=1<<26
        require(instruction>>26==0b100101 and hook+immediate*4==syms[name],'actual startup BL does not enter marker')
        rows+=matrix(routine,stage,config)
        codepath=output/(name+'.bin');codepath.write_bytes(routine['code'])
        routines.append(dict(stage=stage,name=name,address=routine['address'],code_path=str(codepath),code_sha256=digest(codepath),
                             labels=routine['labels'],elf=dict(path=str(elf),sha256=digest(elf))))
    # Feed actual linked producer literals through the unchanged Samsung reader
    # model and production stage decoder, including a rotated snapshot.
    import sys
    sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
    import s22plus_fyg8_retained_snapshot_model as snapshot
    pair=b''.join(bytes.fromhex(v) for v in config['frames'].values())
    payload,_=snapshot.place_precursor(b'\xa5'*marker.PAYLOAD,marker.PAYLOAD+17,pair)
    returned=snapshot.stock_snapshot(payload,snapshot.Header(7,0x4d474f4c,marker.PAYLOAD+17,123)).data
    decoded=marker.decode(returned,manifest['candidate_id'],key,version=marker.version(config))
    require(decoded['observed_stages']==sorted(marker.FORMATS[marker.version(config)]['stages'].values()),
            'producer/snapshot/decoder join differs')
    result=dict(schema='s22plus-mainline-marker-tests-v1',status='PASS_H0_ACTUAL_RETAINED_MARKERS',
        loader_sha256=record['loader']['sha256'],kernel_sha256=record['kernel']['sha256'],config=marked['config'],
        source_sha256=digest(__file__),codec_sha256=digest(marker.__file__),assembly_sha256=digest(marker.HERE/'retained-marker.S'),
        cases=rows,routines=routines,producer_consumer=decoded,physical_retention_proved=False,device_actions=0)
    if marker.c_stages(config):
        from qualify_retained_c import qualify as qualify_c
        result['mmu_on']=qualify_c(record,config,output/'early-c')
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],cases=len(rows),device_actions=0)))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--loader',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();qualify(a.loader,a.output)
