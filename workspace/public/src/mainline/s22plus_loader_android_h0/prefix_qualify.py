"""Actual prefix/ABI/report negatives; full-copy and actual-EL tests are separate."""
import gc
import json
from pathlib import Path
import struct

from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE,UC_MEM_WRITE
from unicorn import arm64_const as regs
from build import pin,require,symbols
import s22plus_loader_prefix_v1 as prefix


def qualify(blob,record,syms,cloned,output):
    from qualify import machine,properties,reduced_fdt,set_property,log_seed,LOG_BASE,LOG_SIZE,INPUT_FDT
    value=record['prefix_control'];cfg=value['configuration'];s={k:v[0] for k,v in syms.items()}
    image=Path(value['image']['path']).read_bytes();target=record['extents']['kernel'][0]
    ps=symbols(value['elf']['path']);origin=ps['_text'][0]
    primary=target+value['entry_offset'];stop=INPUT_FDT+0x1000000
    log='/soc/samsung,kernel_log_buf';reserved='/reserved-memory/sec_debug_region_log@8001FF000'
    keep=('/','/chosen','/soc',log,'/reserved-memory',reserved)
    fresh=reduced_fdt(cloned,lambda p:p in keep,output/'prefix-fixture')
    pos,n,_=properties(fresh)[('/chosen',prefix.PROPERTY)];require(n==256,'prefix report width')
    raw=bytearray(fresh);raw[pos:pos+256]=bytes.fromhex(cfg['report_seed_hex']);fresh=bytes(raw)
    inputs=[dict(name='index-'+str(i),idx=i) for i in
        (0,255,256,257,383,384,prefix.PAYLOAD-1,prefix.PAYLOAD,
         prefix.PAYLOAD+257,0xffffffff)]
    inputs+=[dict(name='bad-magic',magic=0),dict(name='matching-preexisting-frames',preexisting=True)]
    for el,state,name in [(8,0,'EL2'),(12,0,'EL3-skip'),(4,1,'MMU-skip'),(4,4,'DC-skip'),
                           (4,4096,'IC-skip'),(4,1<<25,'EE-skip')]:
        inputs.append(dict(name=name,el=el,state=state))
    for site in (1,2):
        for word in range(4):inputs.append(dict(name=f'drift-site{site}-word{word}',drift=(site,word)))
    for name,path,key,data in [('wrong-reg',log,'reg',bytes(16)),('wrong-region',log,'memory-region',bytes(4)),
        ('wrong-reservation',reserved,'reg',bytes(16)),('no-map',reserved,'no-map',b''),
        ('disabled',log,'status',b'disabled\0'),('wrong-strategy',log,'sec,strategy',bytes(4)),
        ('alternate-phandle',reserved,'linux,phandle',struct.pack('>I',0x999))]:
        inputs.append(dict(name=name,fdt=set_property(fresh,path,key,data),skip_fdt=True))
    for name,path,key in [('duplicate-log-reg',log,'reg'),('duplicate-region',log,'memory-region'),
                          ('duplicate-phandle',reserved,'phandle')]:
        at,n,_=properties(fresh)[(path,key)]
        inputs.append(dict(name=name,fdt=set_property(fresh,path,key,fresh[at:at+n],duplicate=True),skip_fdt=True))
    for corrupt in ('cookie','pc','cpu'):
        inputs.append(dict(name='bad-return-'+corrupt,corrupt=corrupt))
    for count in (4,64,130,270):inputs.append(dict(name='interrupted-store-'+str(count),interrupt=count))
    rows=[]
    for case in inputs:
        fdt=case.get('fdt',fresh);el=case.get('el',4);state=case.get('state',0)
        u,_=machine(blob,record,syms,s['_head'],fdt,fdt_address=record['extents']['fdt'][0])
        u.mem_map(stop,4096);stack=s['_stack_end'];rp=record['extents']['fdt'][0]+properties(fdt)[('/chosen',prefix.PROPERTY)][0]
        idx=case.get('idx',400);magic=case.get('magic',0x4d474f4c)
        original=bytearray(log_seed(idx,magic));cursor=idx%prefix.PAYLOAD
        slot=cursor-256 if cursor>=256 else prefix.PAYLOAD-256
        if case.get('preexisting'):
            for i in range(2):original[16+slot+i*128:16+slot+(i+1)*128]=bytes.fromhex(cfg['retained_marker']['frames'][str(i+1)])
        u.mem_write(LOG_BASE,bytes(original))
        sentinels={n:0x12340000+n for n in range(19,30)}
        for n,v in sentinels.items():u.reg_write(getattr(regs,'UC_ARM64_REG_X'+str(n)),v)
        u.reg_write(regs.UC_ARM64_REG_SP,stack);u.reg_write(regs.UC_ARM64_REG_LR,stop)
        u.reg_write(regs.UC_ARM64_REG_X0,record['extents']['fdt'][0])
        writes=[];reads=[];entered=[];terminal=[];injected=[];copy_count=[];writer_slot=[None];active_site=[None]
        writer_entries={s['s22_retained_loader']:1,target+ps['s22_retained_kernel'][0]-origin:2}
        rechecks={s['s22_retained_loader_recheck']:1,target+ps['s22_retained_kernel_recheck'][0]-origin:2}
        def code(uc,pc,size,user):
            if pc==s['memcpy']:
                # This local corpus isolates diagnostics. Four full-loader
                # cases and real-EL runs execute the actual complete copies.
                a=uc.reg_read(regs.UC_ARM64_REG_X0);b=uc.reg_read(regs.UC_ARM64_REG_X1);n=uc.reg_read(regs.UC_ARM64_REG_X2)
                require((a,b,n)==(target,s['g0q_prefix_image'],len(image)),'unexpected local copy request')
                uc.mem_write(a,bytes(uc.mem_read(b,n)));uc.reg_write(regs.UC_ARM64_REG_PC,uc.reg_read(regs.UC_ARM64_REG_LR))
                copy_count.append(True);return
            if pc==target:
                require(bytes(uc.mem_read(target,len(image)))==image,'local copied Image differs')
                require([uc.reg_read(getattr(regs,'UC_ARM64_REG_X'+str(n))) for n in range(4)]==
                    [record['extents']['fdt'][0],0,0,0],'prefix input ABI differs')
                entered.append(True)
            if pc==primary+ps['record_mmu_state'][0]-ps['primary_entry'][0]:
                raise ValueError('prefix reached record_mmu_state')
            if pc in writer_entries:
                active_site[0]=writer_entries[pc]
                h=struct.unpack('<IIII',bytes(uc.mem_read(LOG_BASE,16)));c=h[2]%prefix.PAYLOAD
                writer_slot[0]=LOG_BASE+16+(c-256 if c>=256 else prefix.PAYLOAD-256)+(active_site[0]-1)*128
            if pc in rechecks and case.get('drift',(-1,-1))[0]==rechecks[pc]:
                word=case['drift'][1];uc.mem_write(LOG_BASE+4*word,struct.pack('<I',0x12345678));injected.append(word)
            if pc==s['g0q_prefix_return'] and case.get('corrupt'):
                register={'cookie':3,'pc':0,'cpu':2}[case['corrupt']]
                uc.reg_write(getattr(regs,'UC_ARM64_REG_X'+str(register)),0xdead)
                injected.append(case['corrupt'])
            op=int.from_bytes(uc.mem_read(pc,4),'little');kind=op&~31
            if op==0xd503205f:
                terminal.append('park');uc.emu_stop();return
            if kind in (0xd5384240,0xd5381000,0xd53c1000):
                uc.reg_write(getattr(regs,'UC_ARM64_REG_X'+str(op&31)),el if kind==0xd5384240 else state)
                uc.reg_write(regs.UC_ARM64_REG_PC,pc+4)
        def memory(uc,kind,a,n,v,user):
            require(a%min(n,8)==0,'prefix unaligned access')
            require(stack-4096<=uc.reg_read(regs.UC_ARM64_REG_SP)<=stack,'prefix stack escaped')
            if kind==UC_MEM_WRITE:
                allowed=(stack-4096<=a and a+n<=stack) or (rp<=a and a+n<=rp+256)
                if LOG_BASE<=a<LOG_BASE+LOG_SIZE:
                    require(n==1 and writer_slot[0] is not None and writer_slot[0]<=a<a+1<=writer_slot[0]+128,
                            'prefix writer escaped its exact slot')
                    writes.append((a,v));allowed=True
                    if len(writes)==case.get('interrupt'):
                        terminal.append('interrupted');uc.emu_stop()
                require(allowed,'prefix wrote outside stack/report/slot')
            elif LOG_BASE<=a<LOG_BASE+LOG_SIZE:
                require((LOG_BASE<=a and a+n<=LOG_BASE+16 and n==4) or
                    (LOG_BASE+16<=a and a+n<=LOG_BASE+LOG_SIZE and n==1),'prefix LOGM read bounds')
                reads.append((a,n))
        u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,memory)
        u.emu_start(s['g0q_prefix_control'],stop,count=5_000_000)
        data=bytes(u.mem_read(rp,256));ring=bytes(u.mem_read(LOG_BASE,LOG_SIZE))
        expected=bytearray(original)
        for a,v in writes:expected[a-LOG_BASE]=v
        for word in injected:
            if type(word) is int:struct.pack_into('<I',expected,4*word,0x12345678)
        require(ring==expected,'prefix changed unobserved LOGM bytes')
        require(len(writes)<=272,'prefix store budget exceeded')
        if case.get('interrupt') or case.get('corrupt'):
            require(terminal==['interrupted' if case.get('interrupt') else 'park'] and data[12:16]==bytes(4),
                    'partial prefix acquired finalized report')
            try:prefix.report(data,cfg,primary)
            except ValueError:pass
            else:raise ValueError('partial prefix accepted')
            outcome=terminal[0]
        else:
            require(not terminal and u.reg_read(regs.UC_ARM64_REG_PC)==stop,'prefix failed to return')
            require(u.reg_read(regs.UC_ARM64_REG_SP)==stack and all(
                u.reg_read(getattr(regs,'UC_ARM64_REG_X'+str(n)))==v for n,v in sentinels.items()),'prefix ABI differs')
            result=prefix.report(data,cfg,primary)
            outcome='SKIP_STATE' if el not in (4,8) or state else 'SKIP_FDT' if case.get('skip_fdt') else 'RETURNED'
            require(result['status']==outcome,'prefix status mismatch')
            require(entered==copy_count==([True] if outcome=='RETURNED' else []),'prefix copy/entry shape differs')
            if outcome!='RETURNED':require(not reads and not writes,'skip accessed LOGM')
            if outcome=='RETURNED' and not case.get('drift') and magic==0x4d474f4c and idx>=256:
                require(len(writes)==272 and all(x['postcall_mismatch_count']==0 for x in result['observations']),
                        'stable prefix writers/readback differ')
            require(result['current_attempt_store_proved'] is False,'static frame promoted to current store proof')
        rows.append(dict(name=case['name'],outcome=outcome,log_store_bytes=len(writes),log_reads=len(reads),
            entered=len(entered),injected=injected,local_memcpy_accelerated=True))
        print(json.dumps(rows[-1]),flush=True);del u;gc.collect()
    result=dict(status='PASS_H0_ACTUAL_LOADER_PREFIX_CONTROL',configuration=cfg,cases=rows,
                local_memcpy_accelerated=True,physical_cache_coherence_proved=False)
    (output/'prefix-cases.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
