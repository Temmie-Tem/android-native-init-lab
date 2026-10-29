#!/usr/bin/env python3
"""Bounded execution of the actual linked early-C writer; mapping calls are fixtures."""
import json
from pathlib import Path
import struct
from elftools.elf.elffile import ELFFile

from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm64_const as regs
from prepare import digest, require
from qualify_retained import symbols
import retained_marker as marker


def exercise(raw, syms, config, *, stage=4, idx=marker.PAYLOAD+300, magic=0x4d474f4c,
             state=1, el=1, fail_map=0, change=None, cut=None):
    name=marker.name(config,stage);base=syms['_text'];start=syms[name]
    stack=0x20000000; stop=stack+0x10000
    u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.reg_write(regs.UC_ARM64_REG_PSTATE,5)
    u.mem_map(base,(len(raw)+0x100000+4095)&~4095);u.mem_write(base,raw)
    u.mem_map(stack,0x11000);u.mem_map(marker.BASE,marker.REGION)
    # The actual kernel uses CONFIG_STACKPROTECTOR_PER_TASK. Preserve its
    # emitted prologue and give SP_EL0 the same mapped init_task it has after
    # __primary_switched; this fixture does not bypass the canary check.
    u.cpr_write(3,0,4,1,0,syms['init_task'])
    before=struct.pack('<IIII',7,magic,idx,123)+b'\xa5'*marker.PAYLOAD
    u.mem_write(marker.BASE,before);u.reg_write(regs.UC_ARM64_REG_SP,stop-16)
    u.reg_write(regs.UC_ARM64_REG_LR,stop)
    protected={i:0x1234000000000000+i for i in range(19,30)}
    for i,v in protected.items():u.reg_write(getattr(regs,'UC_ARM64_REG_X'+str(i)),v)
    cursor=idx%marker.PAYLOAD
    position=(cursor-256 if cursor>=256 else marker.PAYLOAD-256)+marker.slot(config,stage)
    slot=marker.BASE+16+position
    calls=[];active=[];writes=[]
    def code(uc,pc,size,user):
        ins=struct.unpack('<I',uc.mem_read(pc,4))[0]
        # Unicorn does not model these EL/MMU combinations. Only the values
        # returned by the actual MRS instructions are injected here; QEMU
        # separately executes the full unmodified kernel with real mappings.
        system={0xd5384240:el*4,0xd5381000:state,0xd53c1000:state}
        if ins&~31 in system:
            uc.reg_write(getattr(regs,'UC_ARM64_REG_X'+str(ins&31)),system[ins&~31])
            uc.reg_write(regs.UC_ARM64_REG_PC,pc+4);return
        if pc==syms['early_memremap_prot']:
            phys=uc.reg_read(regs.UC_ARM64_REG_X0);length=uc.reg_read(regs.UC_ARM64_REG_X1)
            prot=uc.reg_read(regs.UC_ARM64_REG_X2);number=len(calls)+1
            require((phys,length)==((marker.BASE,16) if number==1 else (slot,128)), 'mapping outside fixed span')
            require(number<=2 and (prot>>2)&7==2 and prot&(1<<53) and prot&(1<<54), 'mapping is not Normal-NC/XN')
            calls.append(dict(physical=phys,length=length,prot=prot,failed=number==fail_map))
            if number!=fail_map:active.append((phys,length))
            uc.reg_write(regs.UC_ARM64_REG_X0,0 if number==fail_map else phys)
            uc.reg_write(regs.UC_ARM64_REG_PC,uc.reg_read(regs.UC_ARM64_REG_LR));return
        if pc==syms['early_memunmap']:
            pair=(uc.reg_read(regs.UC_ARM64_REG_X0),uc.reg_read(regs.UC_ARM64_REG_X1))
            require(active and pair==active.pop(), 'mapping cleanup order/extent differs')
            uc.reg_write(regs.UC_ARM64_REG_PC,uc.reg_read(regs.UC_ARM64_REG_LR));return
        if change is not None and pc==syms[name+'_recheck']:
            uc.mem_write(marker.BASE+change,struct.pack('<I',0x12345678))
    def write(uc,kind,address,size,value,user):
        if stack<=address<address+size<=stop:return
        require(slot<=address<address+size<=slot+128 and size==1, 'writer escaped its fixed slot/stack')
        writes.append((address,size))
        if cut is not None and len(writes)==cut:uc.emu_stop()
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.emu_start(start,stop,count=10000)
    after=bytes(u.mem_read(marker.BASE,marker.REGION));expected=bytearray(before)
    if cut is not None:
        offset=slot-marker.BASE
        require(after[:offset]==before[:offset] and after[offset+128:]==before[offset+128:], 'interrupted C escaped slot')
        require(after[offset:offset+128]!=bytes.fromhex(config['frames'][str(stage)]), 'partial C committed a complete new frame')
        return dict(stage=stage,cut_after_hook=cut,complete_frame=False)
    require(u.reg_read(regs.UC_ARM64_REG_PC)==stop and not active, 'writer failed to return/clean mappings')
    require(u.reg_read(regs.UC_ARM64_REG_SP)==stop-16, 'stack changed')
    for i,v in protected.items():require(u.reg_read(getattr(regs,'UC_ARM64_REG_X'+str(i)))==v, 'callee-saved register changed')
    admitted=el in (1,2) and state&0x2000001==1
    eligible=admitted and magic==0x4d474f4c and idx>=256 and not fail_map
    if eligible:
        frame=bytes.fromhex(config['frames'][str(stage)])
        expected[slot-marker.BASE:slot-marker.BASE+128]=frame if change is None else bytes(8)+frame[8:]
        if change is not None:struct.pack_into('<I',expected,change,0x12345678)
    require(after==expected,'C writer bytes/header/outside-slot differ')
    if not admitted:require(not calls,'ineligible CPU state made a mapping')
    if not eligible:require(not writes,'ineligible C writer wrote')
    return dict(stage=stage,idx=idx,el=el,state=state,fail_map=fail_map,header_mutation=change,
                committed=eligible and change is None,map_calls=calls,mappings_released=True)


def qualify(record,config,output):
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    image=Path(record['kernel']['image']);elf=image.parents[3]/'vmlinux'
    require(digest(image)==record['kernel']['sha256'],'C kernel changed')
    raw=image.read_bytes();syms=symbols(elf)
    placement={}
    if marker.version(config) in (3,4,5,6,7):
        containing=('kernel_init_freeable' if marker.version(config)==7 else
                    'kernel_init' if marker.version(config)==6 else
                    'start_kernel' if marker.version(config) in (4,5) else 'setup_arch')
        with elf.open('rb') as stream:
            symbol=next(s for s in ELFFile(stream).get_section_by_name('.symtab').iter_symbols() if s.name==containing)
            start=syms[containing];length=symbol['st_size']
        calls=[]
        for offset in range(0,length,4):
            instruction=struct.unpack_from('<I',raw,start-syms['_text']+offset)[0]
            if instruction>>26!=0b100101:continue
            immediate=instruction&0x3ffffff
            if immediate&(1<<25):immediate-=1<<26
            calls.append((start+offset,start+offset+4*immediate))
        def call(name):
            matches=[pc for pc,destination in calls if destination==syms[name]]
            require(len(matches)==1,'actual '+containing+' call count differs: '+name)
            return matches[0]
        if marker.version(config)==3:
            post_fdt=call(marker.name(config,5));post_paging=call(marker.name(config,6))
            remaps=[pc for pc,destination in calls if destination==syms['fixmap_remap_fdt']]
            require(len(remaps)==2 and remaps[0]<call('early_init_dt_scan')<remaps[1]<post_fdt<call('jump_label_init')<call('paging_init') and
                    post_paging==call('paging_init')+4<call('early_ioremap_reset'), 'actual V3 call ordering differs')
            placement=dict(post_fdt_call=post_fdt,post_paging_call=post_paging,assembly_marker_absent=True,
                           actual_fdt_scan_and_readonly_remap_before_first=True)
        elif marker.version(config)==4:
            post_arch=call(marker.name(config,7));post_time=call(marker.name(config,8))
            require(post_arch==call('setup_arch')+4<call('mm_core_init_early') and
                    post_arch<call('mm_core_init')<call('sched_init')<call('init_IRQ')<call('time_init') and
                    post_time==call('time_init')+4<call('random_init'), 'actual V4 call ordering differs')
            placement=dict(post_setup_arch_call=post_arch,post_time_init_call=post_time,
                           actual_calls_immediately_after_returns=True,assembly_marker_absent=True)
        elif marker.version(config)==5:
            pre_irq=call(marker.name(config,9));pre_rest=call(marker.name(config,10))
            irq_instruction=struct.unpack_from('<I',raw,pre_irq+4-syms['_text'])[0]
            require(irq_instruction in (0xd50342ff,0xd50343ff) and
                    call('time_init')<call('random_init')<pre_irq<call('console_init')<
                    call('calibrate_delay')<pre_rest and pre_rest+4==call('rest_init'),
                    'actual V5 IRQ-enable/rest_init call ordering differs')
            placement=dict(pre_irq_enable_call=pre_irq,irq_enable_instruction=irq_instruction,
                           pre_rest_init_call=pre_rest,actual_calls_immediately_before_boundaries=True,
                           assembly_marker_absent=True)
        elif marker.version(config)==6:
            post_wait=call(marker.name(config,11));post_async=call(marker.name(config,12))
            require(post_wait==call('wait_for_completion')+4<call('kernel_init_freeable')<
                    call('async_synchronize_full') and post_async==call('async_synchronize_full')+4<call('free_initmem'),
                    'actual V6 kernel-init return boundaries differ')
            placement=dict(post_kthreadd_wait_call=post_wait,post_async_sync_call=post_async,
                           actual_calls_immediately_after_returns=True,before_free_initmem=True,
                           assembly_marker_absent=True)
        else:
            pre_basic=call(marker.name(config,13));post_basic=call(marker.name(config,14))
            initcalls=[pc for pc,destination in calls if destination==syms['do_one_initcall']]
            require(pre_basic==call('page_alloc_init_late')+4 and pre_basic+4==call('cpuset_init_smp') and
                    pre_basic<call('ksysfs_init')<call('driver_init')<call('init_irq_proc') and
                    len(initcalls)==2 and initcalls[0]<pre_basic<call('init_irq_proc')<initcalls[1]<call('kfree') and
                    post_basic==call('kfree')+4 and post_basic+4==call('wait_for_initramfs')<call('console_on_rootfs'),
                    'actual V7 inlined basic-setup boundaries differ')
            placement=dict(pre_basic_setup_call=pre_basic,post_basic_setup_call=post_basic,
                           early_initcall_call=initcalls[0],regular_initcall_call=initcalls[1],
                           command_line_free_call=call('kfree'),initramfs_wait_call=call('wait_for_initramfs'),
                           inlined_basic_setup_boundaries_proved=True,before_free_initmem=True,
                           assembly_marker_absent=True)
        selected={marker.name(config,s) for s in marker.c_stages(config)}
        known={'s22_retained_'+name for fmt in marker.FORMATS.values() for name in fmt['names'].values()}
        require(not ((known-selected)&syms.keys()),'C-only format retains a superseded marker site')
    rows=[]
    for stage in marker.c_stages(config):
        offset=syms[marker.name(config,stage)+'_frame']-syms['_text']
        require(raw[offset:offset+128]==bytes.fromhex(config['frames'][str(stage)]),'actual C frame differs')
        def case(**kw):return exercise(raw,syms,config,stage=stage,**kw)
        for idx in (0,255,256,marker.PAYLOAD-1,marker.PAYLOAD,marker.PAYLOAD+1,
                    marker.PAYLOAD+300,marker.PAYLOAD+4196,marker.PAYLOAD+4324,0xffffffff):
            rows.append(case(idx=idx))
        for el in (0,2,3):rows.append(case(el=el))
        for state in (0,4,5,1|(1<<25)):rows.append(case(state=state))
        rows.append(case(magic=0))
        for fail in (1,2):rows.append(case(fail_map=fail))
        for change in (0,4,8,12):rows.append(case(change=change))
        for cut in range(1,136):rows.append(case(cut=cut))
    result=dict(status='PASS_H0_ACTUAL_EARLY_C',kernel_sha256=digest(image),
        kernel_path=str(image),elf_path=str(elf),elf_sha256=digest(elf),
        source_sha256=digest(__file__),cases=rows,placement=placement,qualified_c_stages=list(marker.c_stages(config)),mapping_api_mocked=True,
        mmu_translation_proved=False,device_actions=0)
    if marker.version(config) in (6,7):
        manifest=json.loads(Path(record['initramfs_manifest']).read_text())
        initrd=manifest['initramfs'];path=Path(initrd['path'])
        require(manifest['vm'] is False and path.stat().st_size==initrd['size'] and digest(path)==initrd['sha256'],
                'init-thread fixture initramfs differs from physical candidate')
        result.update(layout_compiler=record['kernel']['command']['compiler'],
                      layout_config_sha256=record['kernel']['config_sha256'],mapping_initramfs=initrd)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
