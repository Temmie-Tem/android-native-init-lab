#!/usr/bin/env python3
"""Build the published loader patch with explicit g0q placement deltas.

The result remains H0: initial ABL source/stub overlap has not been admitted.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess

from prepare import HERE, ROOT, digest, require, run, config_values, uncovered, audit_candidate

TEXT=0xa8000000
PAYLOAD=0x80ba00000
DTB=0xb6000000
INITRD=0xb6915000


def build(base,prepared,init,output,reuse=False,kernel_label='kernel-1'):
    base,prepared,init,output=[p.resolve() for p in (base,prepared,init,output)]
    require(output.is_relative_to(ROOT/'workspace/private'),'private loader output')
    lock=json.loads((HERE/'sources.json').read_text())
    upstream=base/'uniloader-upstream'
    head=subprocess.check_output(['git','-C',upstream,'rev-parse','HEAD'],text=True).strip()
    require(head==lock['uniloader']['commit'],'loader source revision')
    require(not subprocess.check_output(['git','-C',upstream,'status','--porcelain']),'loader upstream dirty')
    patch=base/'r0q-port/kernel/uniloader-patches/0001-dtb-relocate.patch'
    require(digest(patch)==lock['files']['r0q-port/kernel/uniloader-patches/0001-dtb-relocate.patch'],'loader patch changed')
    ir=json.loads((init/'result.json').read_text());require(ir['vm'] is False,'VM image forbidden in carrier')
    require(bool(kernel_label) and all(c.isalnum() or c=='-' for c in kernel_label),'kernel label')
    kr=json.loads((prepared/(kernel_label+'-result.json')).read_text())
    prep=json.loads((prepared/'prepared.json').read_text())
    require(kr['command']['prepared_sha256']==digest(prepared/'prepared.json'),'kernel preparation differs')
    require(kr['config_sha256']==prep['config_sha256']==digest(Path(prep['kernel_build'])/'.config'),
            'kernel/config preparation differs')
    require(ir['dtb']['sha256']==prep['dtb_sha256'] and ir['initrd_address']==INITRD,'initramfs/DT placement preparation differs')
    config_inputs=[x for x in ir['inputs'] if Path(x['path']).resolve()==Path(prep['kernel_build'])/'.config']
    require(len(config_inputs)==1 and config_inputs[0]['sha256']==prep['config_sha256'],'initramfs config preparation differs')
    require(ir['kernel_release']==(Path(prep['kernel_build'])/'include/config/kernel.release').read_text().strip(),
            'initramfs kernel release differs')
    for item in ir['inputs']:require(digest(item['path'])==item['sha256'],'initramfs source/input changed')
    require(digest(prep['live_fdt']['path'])==prep['live_fdt']['sha256'],'retained live FDT changed')
    dt_audit=audit_candidate(prep['live_fdt']['path'],ir['dtb']['path'])
    for record in [ir['initramfs'],ir['dtb']]:require(digest(record['path'])==record['sha256'],'member changed')
    require(digest(kr['image'])==kr['sha256'],'kernel changed')
    if not reuse:output.mkdir(mode=0o700,parents=True,exist_ok=False)
    require(not (output/'result.json').exists(),'result already published')
    source=output/'source'
    if not reuse:
        shutil.copytree(upstream,source)
        run(['patch','--batch','--fuzz=0','-p1','-i',patch],output/'patch.log',cwd=source)
    require('fuzz' not in (output/'patch.log').read_text().lower(),'fuzzy patch application')
    config=(upstream/'configs/r0q_defconfig').read_text()
    config=re.sub(r'^CONFIG_TEXT_BASE=.*$',f'CONFIG_TEXT_BASE={TEXT:#x}',config,flags=re.M)
    config=re.sub(r'^CONFIG_PAYLOAD_ENTRY=.*$',f'CONFIG_PAYLOAD_ENTRY={PAYLOAD:#x}',config,flags=re.M)
    config+='\nCONFIG_DTB_RELOCATE=y\nCONFIG_DTB_ENTRY=0xb6000000\n# CONFIG_SIMPLE_FB is not set\n'
    if not reuse:(source/'configs/r0q_defconfig').write_text(config)
    require((source/'configs/r0q_defconfig').read_text()==config,'loader defconfig changed')
    for name,path in [('Image',kr['image']),('dtb',ir['dtb']['path']),('ramdisk',ir['initramfs']['path'])]:
        if not reuse:shutil.copyfile(path,source/'blob'/name)
        require(digest(source/'blob'/name)==digest(path),'embedded input changed')
    env=dict(os.environ,SOURCE_DATE_EPOCH='0')
    make=['make','ARCH=aarch64','CROSS_COMPILE=aarch64-linux-gnu-',
          'BUILD_DATE=1970-01-01 00:00:00','GIT_VERSION_TAG='+head]
    if not reuse:
        (output/'command.json').write_text(json.dumps({'make':make,'patch_sha256':digest(patch),
                                                     'config':config},indent=2)+'\n')
        run(make+['r0q_defconfig'],output/'config.log',cwd=source,env=env)
    effective=config_values((source/'.config').read_text())
    for key,value in {'CONFIG_TEXT_BASE':hex(TEXT),'CONFIG_PAYLOAD_ENTRY':hex(PAYLOAD),
                      'CONFIG_RAMDISK_ENTRY':hex(INITRD),'CONFIG_DTB_ENTRY':hex(DTB),
                      'CONFIG_DTB_RELOCATE':'y','CONFIG_SIMPLE_FB':'n','CONFIG_LIBFDT':'y',
                      'CONFIG_POSITION_INDEPENDENT':'y','CONFIG_LINUX_KRNL_HEADER_IMG':'y'}.items():
        actual=effective.get(key,'n')
        require(int(actual,16)==int(value,16) if value.startswith('0x') else actual==value,'loader config '+key)
    if not reuse:run(make+['-j4'],output/'build.log',cwd=source,env=env)
    # Artifact names are fixed by the pinned upstream Makefile.
    elf=source/'uniLoader.o';blob=source/'uniLoader'
    require(elf.is_file() and blob.is_file(),'loader artifacts absent')
    symbol_text=subprocess.check_output(['aarch64-linux-gnu-nm','-n',elf],text=True)
    (output/'symbols.txt').write_text(symbol_text)
    symbols={m[3]:int(m[1],16) for line in symbol_text.splitlines()
             if (m:=re.fullmatch(r'([0-9a-fA-F]+)\s+(\w)\s+(\S+)',line))}
    required=['_start','_reloc_start','_reloc_end','_stack_end','kernel_size','ramdisk_size','dtb']
    require(all(k in symbols for k in required),'missing linker geometry')
    reloc_size=symbols['_reloc_end']-symbols['_reloc_start']
    stage_end=max(symbols['_stack_end'],symbols['_start']+reloc_size)
    require(symbols['_reloc_start']==TEXT and symbols['_start']>=TEXT and
            symbols['kernel_size']==Path(kr['image']).stat().st_size,'embedded kernel geometry')
    require(symbols['ramdisk_size']==ir['initramfs']['size'],'embedded initrd size')
    require(symbols['dtb']%8==0 and DTB%8==0 and
            Path(ir['dtb']['path']).stat().st_size<int(effective['CONFIG_FDT_BUF_SIZE']), 'DTB alignment/buffer geometry')
    header=blob.read_bytes()[:64]
    require(len(header)==64 and header[56:60]==b'ARM\x64','loader ARM64 Image header')
    offset,declared_size,flags=struct.unpack_from('<QQQ',header,8)
    require(offset==0 and declared_size>=blob.stat().st_size and
            declared_size==symbols['_stack_end']-symbols['_start'], 'loader Image header geometry')
    payload_end=PAYLOAD+kr['runtime_size'];dtb_end=DTB+int(effective['CONFIG_FDT_BUF_SIZE'])
    extents={'loader-runtime-and-copy':(TEXT,stage_end),'kernel-runtime':(PAYLOAD,payload_end),
             'rewritten-dtb':(DTB,dtb_end),'initramfs':(INITRD,INITRD+ir['initramfs']['size'])}
    reserved=prep['candidate_reservations']
    for name,(start,end) in extents.items():
        require(not uncovered([(start,end)],prep['memory_banks']),name+' outside RAM')
        require(all(end<=a or start>=b for a,b in reserved),name+' intersects reservation')
    for i,(name,(start,end)) in enumerate(extents.items()):
        for other,(a,b) in list(extents.items())[i+1:]:require(end<=a or start>=b,name+' overlaps '+other)
    require(PAYLOAD%(2*1024*1024)==0,'unaligned Image placement')
    run(['file',elf,blob],output/'file.log')
    run(['aarch64-linux-gnu-readelf','-h','-l','-r',elf],output/'elf.log')
    run(['aarch64-linux-gnu-objdump','-d',elf],output/'disassembly.txt')
    result={'status':'H0_LOADER_BUILT_INITIAL_ABL_SOURCE_UNBOUND','loader':{'path':str(blob),'sha256':digest(blob),'size':blob.stat().st_size},
            'elf':{'path':str(elf),'sha256':digest(elf)},'extents':extents,
            'relocation_copy_bytes':reloc_size,'runtime_symbols':{k:symbols[k] for k in required},
            'configuration':effective,'source_commit':head,'patch_sha256':digest(patch),
            'loader_image_header':{'text_offset':offset,'image_size':declared_size,'flags':flags,
                                   'copy_bytes_beyond_header_size':reloc_size-declared_size},
            'candidate_dt_audit':dt_audit,
            'kernel':kr,'initramfs_manifest':str(init/'result.json'),
            'initial_abl_source_and_stub_overlap':'UNRESOLVED_NOT_DEVICE_ADMISSIBLE',
            'device_actions':0}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'loader_bytes':blob.stat().st_size,'fixed_reservation_overlap':False}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['base','prepared','init','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--reuse',action='store_true',help='qualify an existing successful H0 build; no rebuild')
    p.add_argument('--kernel-label',default='kernel-1')
    a=p.parse_args();build(a.base,a.prepared,a.init,a.output,a.reuse,a.kernel_label)
