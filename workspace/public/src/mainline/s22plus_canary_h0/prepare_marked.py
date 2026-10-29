#!/usr/bin/env python3
"""Fresh private source/preparation for the two-site marker; no device effects."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from prepare import ROOT,HERE,digest,require,nodes,ranges,uncovered,fixed_reservations
import retained_marker as marker

def pin(p):
    p=Path(p);return dict(path=str(p.resolve()),size=p.stat().st_size,sha256=digest(p))

def instrumented_head(old,cfg):
    end='SYM_CODE_END(primary_entry)\n'
    if marker.version(cfg) in (3,4,5,6,7):
        require(old.count(end)==1 and 's22_retained_' not in old,'C-only format requires unmarked assembly entry')
        return old
    if marker.version(cfg)==2:
        site='SYM_FUNC_START_LOCAL(__primary_switch)\n'
        require(old.count(site)==old.count(end)==1 and 's22_retained_' not in old,'kernel MMU hook differs')
        return old.replace(site,site+'\tbl\ts22_retained_pre_mmu\n').replace(end,end+'\n'+marker.render(cfg,3)+'\n')
    site='SYM_CODE_START(primary_entry)\n\tbl\trecord_mmu_state\n'
    require(old.count(site)==old.count(end)==1 and 's22_retained_' not in old,'kernel entry hook differs')
    return old.replace(site,'SYM_CODE_START(primary_entry)\n\tbl\ts22_retained_kernel\n\tbl\trecord_mmu_state\n').replace(end,end+'\n'+marker.render(cfg,2)+'\n')

def instrumented_setup(old,cfg=None):
    declaration='void __init __no_sanitize_address setup_arch(char **cmdline_p)\n'
    if cfg is not None and marker.version(cfg) in (4,5,6,7):
        require(old.count(declaration)==1 and 's22_retained_' not in old and
                's22-retained-early-c.h' not in old,'main.c format requires unmarked setup_arch')
        return old
    sites=[('\tearly_ioremap_init();\n','s22_retained_early_c')]
    if cfg is not None and marker.version(cfg)==3:
        sites=[('\tsetup_machine_fdt(__fdt_pointer);\n',marker.name(cfg,5)),
               ('\tpaging_init();\n',marker.name(cfg,6))]
    require(old.count(declaration)==1 and all(old.count(site)==1 for site,_ in sites) and 's22_retained_' not in old and
            's22-retained-early-c.h' not in old,'early C hook differs')
    result=old.replace(declaration,'#include "s22-retained-early-c.h"\n\n'+declaration)
    for site,name in sites:result=result.replace(site,site+'\t'+name+'();\n')
    return result

def instrumented_main(old,cfg):
    require(marker.version(cfg) in (4,5,6,7),'selected format does not mark main.c')
    declaration=('asmlinkage __visible __init __no_sanitize_address __noreturn __no_stack_protector\n'
                 'void start_kernel(void)\n')
    if marker.version(cfg)==4:
        sites=[('\tsetup_arch(&command_line);\n',marker.name(cfg,7)),
               ('\ttime_init();\n',marker.name(cfg,8))]
    elif marker.version(cfg)==5:
        sites=[('\tearly_boot_irqs_disabled = false;\n',marker.name(cfg,9)),
               ("\t/* Do the rest non-__init'ed, we're now alive */\n",marker.name(cfg,10))]
    elif marker.version(cfg)==6:
        declaration='static int __ref kernel_init(void *unused)\n'
        sites=[('\twait_for_completion(&kthreadd_done);\n',marker.name(cfg,11)),
               ('\tasync_synchronize_full();\n',marker.name(cfg,12))]
        require(old.count('\tasync_synchronize_full();\n\n\tsystem_state = SYSTEM_FREEING_INITMEM;\n')==1,
                'V6 init-memory lifetime boundary differs')
    else:
        declaration='static noinline void __init kernel_init_freeable(void)\n'
        sites=[('\tpage_alloc_init_late();\n',marker.name(cfg,13)),
               ('\tdo_basic_setup();\n',marker.name(cfg,14))]
        require(old.count('\tpage_alloc_init_late();\n\n\tdo_basic_setup();\n\n\tkunit_run_all_tests();\n')==1 and
                old.count('\tkernel_init_freeable();\n')==1 and
                old.index('\tkernel_init_freeable();\n')<old.index('\tsystem_state = SYSTEM_FREEING_INITMEM;\n'),
                'V7 basic-setup and init-memory lifetime boundaries differ')
    if marker.version(cfg)==5:
        require(old.count('\tearly_boot_irqs_disabled = false;\n\tlocal_irq_enable();\n')==1 and
                old.count("\tkcsan_init();\n\n\t/* Do the rest non-__init'ed, we're now alive */\n\trest_init();\n")==1,
                'V5 bootstrap boundaries differ')
    require(old.count(declaration)==1 and all(old.count(site)==1 for site,_ in sites) and
            's22_retained_' not in old and 's22-retained-early-c.h' not in old,'main.c hook differs')
    result=old.replace(declaration,'#include "s22-retained-early-c.h"\n\n'+declaration)
    for site,name in sites:result=result.replace(site,site+'\t'+name+'();\n')
    return result

def prepare(previous,output):
    previous,output=previous.resolve(),output.resolve()
    require(output.is_relative_to(ROOT/'workspace/private') and not output.exists(),'fresh private marked preparation')
    old=json.loads((previous/'prepared.json').read_text())
    require(digest(Path(old['kernel_build'])/'.config')==old['config_sha256'] and
            digest(previous/'sm8450-samsung-g0q-ram.dtb')==old['dtb_sha256'] and
            digest(old['live_fdt']['path'])==old['live_fdt']['sha256'],'retained preparation changed')
    live=nodes(old['live_fdt']['path']);log=live['/soc/samsung,kernel_log_buf']
    require(ranges(log['reg'])==[(marker.BASE,marker.BASE+marker.REGION)] and
            log['compatible']==b'samsung,kernel_log_buf\0' and log['status']==b'okay\0' and
            int.from_bytes(log['sec,strategy'],'big')==3,'fixed retained logger differs')
    candidate=nodes(previous/'sm8450-samsung-g0q-ram.dtb')
    require(not uncovered([(marker.BASE,marker.BASE+marker.REGION)],fixed_reservations(candidate,coverage=True)),
            'marker slice lacks active reserved no-map coverage')
    output.mkdir(mode=0o700,parents=True)
    kernel=output/'kernel-source'
    # Never hardlink mutable source/build output back to a consumed artifact.
    subprocess.run(['cp','-a','--reflink=auto',old['kernel'],kernel],check=True)
    build=output/'kernel-build';(build/'include/config').mkdir(parents=True)
    for a,b in [(Path(old['kernel_build'])/'.config',build/'.config'),
                (Path(old['kernel_build'])/'include/config/kernel.release',build/'include/config/kernel.release'),
                (previous/'sm8450-samsung-g0q-ram.dtb',output/'sm8450-samsung-g0q-ram.dtb')]:shutil.copyfile(a,b)
    value=dict(old,kernel=str(kernel),kernel_build=str(build),retained_preparation=pin(previous/'prepared.json'))
    (output/'prepared.json').write_text(json.dumps(value,indent=2)+'\n')
    return value

def instrument(prepared,init,*,version=1):
    prepared,init=prepared.resolve(),init.resolve()
    require(prepared.is_relative_to(ROOT/'workspace/private'),'private marker source')
    value=json.loads((prepared/'prepared.json').read_text());manifest=json.loads((init/'result.json').read_text())
    require(manifest['vm'] is False,'physical marker must use physical candidate identity')
    key=Path(manifest['key_path']).read_bytes();cfg=marker.configuration(manifest['candidate_id'],key,version=version)
    cfgpath=prepared/'retained-marker.json';require(not cfgpath.exists(),'marker already prepared')
    head=Path(value['kernel'])/'arch/arm64/kernel/head.S';old=head.read_text()
    (prepared/'original-head.S').write_text(old)
    new=instrumented_head(old,cfg)
    head.write_text(new)
    cfgpath.write_text(json.dumps(cfg,indent=2)+'\n')
    receipt=dict(schema='s22plus-mainline-marker-kernel-source-v1',config=pin(cfgpath),
        init_manifest=pin(init/'result.json'),original_head=pin(prepared/'original-head.S'),
        instrumented_head=pin(head),sources=[pin(HERE/x) for x in ('retained-marker.S','retained_marker.py','prepare_marked.py')],
        device_actions=0)
    if marker.c_stages(cfg):
        setup=Path(value['kernel'])/'arch/arm64/kernel/setup.c';original=prepared/'original-setup.c'
        original.write_bytes(setup.read_bytes());setup.write_text(instrumented_setup(original.read_text(),cfg))
        source=Path(value['kernel'])/marker.c_source(cfg)
        header=source.parent/'s22-retained-early-c.h';require(not header.exists(),'early C header already present')
        header.write_text(marker.render_c(cfg))
        receipt.update(schema='s22plus-mainline-marker-kernel-source-v'+str(version),original_setup=pin(original),
            instrumented_setup=pin(setup),generated_header=pin(header))
        if version in (4,5,6,7):
            original_main=prepared/'original-main.c';original_main.write_bytes(source.read_bytes())
            source.write_text(instrumented_main(original_main.read_text(),cfg))
            receipt.update(original_main=pin(original_main),instrumented_main=pin(source))
        receipt['sources'].append(pin(HERE/'retained-early-c.h'))
    (prepared/'marker-source.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('prepare');a.add_argument('previous',type=Path);a.add_argument('output',type=Path)
    a=s.add_parser('instrument');a.add_argument('prepared',type=Path);a.add_argument('init',type=Path)
    a.add_argument('--version',type=int,choices=tuple(marker.FORMATS),default=1)
    a=p.parse_args();os.umask(0o077)
    result=prepare(a.previous,a.output) if a.command=='prepare' else instrument(a.prepared,a.init,version=a.version)
    print(json.dumps(dict(status='H0_ONLY',device_actions=0)))
