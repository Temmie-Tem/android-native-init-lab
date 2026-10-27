#!/usr/bin/env python3
"""Build a sealed RAM PID1, with an explicitly distinct VM test variant."""
import argparse
import gzip
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess

from prepare import HERE, ROOT, digest, require, run


def build(prepared, output, vm, network_path):
    prepared, output = prepared.resolve(), output.resolve()
    require(output.is_relative_to(ROOT/'workspace/private'), 'private output required')
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    source_paths = [HERE/'init.c',HERE/'protocol.h',HERE/'build_initramfs.py',
                    HERE/'../../native-init/s22plus_fyg8_max77705_result_parser.inc.c',
                    prepared/'kernel-build/.config',prepared/'sm8450-samsung-g0q-ram.dtb',network_path]
    inputs=[{'path':str(p.resolve()),'sha256':digest(p)} for p in source_paths]
    key=secrets.token_bytes(32)
    identity=hashlib.sha256(json.dumps({'inputs':inputs,'vm':vm,'key_commitment':hashlib.sha256(key).hexdigest()},
                                      sort_keys=True,separators=(',',':')).encode()).digest()
    keypath=output/'key.bin';keypath.write_bytes(key);keypath.chmod(0o400)
    net=json.loads(network_path.read_text())
    require(set(net)=={'device_ip','host_ip','netmask'},'network fields')
    local=ipaddress.IPv4Interface(net['device_ip']+'/'+net['netmask'])
    peer=ipaddress.IPv4Address(net['host_ip'])
    require(peer in local.network and peer!=local.ip and
            peer not in (local.network.network_address,local.network.broadcast_address) and
            local.ip not in (local.network.network_address,local.network.broadcast_address),
            'private endpoint geometry')
    require(local.network.is_private and all(not (a.is_multicast or a.is_loopback or a.is_unspecified)
                                             for a in (local.ip,peer)), 'private unicast endpoints required')
    net={'device_ip':str(local.ip),'host_ip':str(peer),'netmask':str(local.network.netmask)}
    # Private provisional endpoint data. A future physical owner must admit
    # the actual host interface/subnet before configuring it; this tool does not.
    net.update(device_mac='02:'+':'.join(f'{x:02x}' for x in identity[:5]),
               host_mac='02:'+':'.join(f'{x:02x}' for x in identity[5:10]),
               serial='g0q-'+identity.hex()[:20],udc='a600000.usb')
    seal='#define CANARY_PORT 47649\n'
    for name,value in [('key',key),('id',identity)]:
        seal+='static const unsigned char canary_'+name+'[32]={'+','.join(str(x) for x in value)+'};\n'
    for name,value in net.items():
        seal+='static const char canary_'+name+'[]='+json.dumps(value)+';\n'
    (output/'seal.h').write_text(seal);(output/'seal.h').chmod(0o400)
    tree=output/'tree';tree.mkdir(mode=0o755)
    for name in ['dev','proc','sys','config']:(tree/name).mkdir(mode=0o755)
    command=['aarch64-linux-gnu-gcc','-std=c11','-static','-Os','-Wall','-Wextra','-Werror',
             '-Wno-unused-function','-Wno-unused-const-variable','-fno-ident','-ffunction-sections',
             '-fdata-sections','-Wl,--gc-sections','-Wl,--build-id=none','-I',output,
             *(['-DCANARY_H0_VM'] if vm else []),HERE/'init.c','-o',tree/'init']
    (output/'compile-command.json').write_text(json.dumps([str(x) for x in command],indent=2)+'\n')
    run(command,output/'compile.log')
    (tree/'init').chmod(0o755)
    run(['file',tree/'init'],output/'file.log')
    run(['aarch64-linux-gnu-readelf','-h','-l',tree/'init'],output/'elf.log')
    require('INTERP' not in (output/'elf.log').read_text(), 'unexpected dynamic interpreter')
    for p in [tree,*tree.iterdir()]:os.utime(p,(0,0))
    names=['.','config','dev','init','proc','sys']
    packed=subprocess.run(['cpio','-o','-H','newc','--owner=0:0','--reproducible'],
                           input=('\n'.join(names)+'\n').encode(),cwd=tree,capture_output=True)
    (output/'cpio.log').write_bytes(packed.stderr)
    require(packed.returncode==0,'cpio failed')
    archive=output/'initramfs.cpio.gz';archive.write_bytes(gzip.compress(packed.stdout,mtime=0))
    listing=subprocess.run(['cpio','-it'],input=packed.stdout,capture_output=True,check=True)
    require(listing.stdout.decode().splitlines()==names,'unexpected archive members')
    release=(prepared/'kernel-build/include/config/kernel.release').read_text().strip()
    result={'status':'H0_INITRAMFS_BUILT_NOT_DEVICE_AUTHORITY','vm':vm,'candidate_id':identity.hex(),
            'key_path':str(keypath),'network':net,'port':47649,'inputs':inputs,
            'kernel_release':release,'init':{'path':str(tree/'init'),'sha256':digest(tree/'init')},
            'initramfs':{'path':str(archive),'sha256':digest(archive),'size':archive.stat().st_size},
            'dtb':{'path':str(prepared/'sm8450-samsung-g0q-ram.dtb'),
                   'sha256':digest(prepared/'sm8450-samsung-g0q-ram.dtb')},
            'initrd_address':0xb6915000,'device_actions':0}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'vm':vm,'init_bytes':(tree/'init').stat().st_size,
                      'archive_bytes':archive.stat().st_size,'output':str(output)}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--network',type=Path,required=True,help='private endpoint JSON; does not configure the host')
    p.add_argument('--vm',action='store_true')
    a=p.parse_args();build(a.prepared,a.output,a.vm,a.network)
