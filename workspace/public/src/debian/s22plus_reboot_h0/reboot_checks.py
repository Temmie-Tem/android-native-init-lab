#!/usr/bin/env python3
"""Interruption, mutation and offline checks for the isolated P458 component."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import struct
import time

import reboot_vm as vm
from reboot_vm import require,regular,pin,save,run_command,superblock,disk_pin,disk_verify,raw,verify


def clone(source,destination,log):
    run_command(['cp','--reflink=auto','--sparse=always',regular(source),destination],log)


def end_guest(guest):
    if getattr(guest,'stream',None) is not None and not guest.stream.closed:
        guest.finish(kill=guest.process.poll() is None)


def observe(guest,point=None,timeout=55):
    deadline=time.monotonic()+timeout
    try:
        guest.start()
        while guest.process.poll() is None and time.monotonic()<deadline:
            data=guest.log()
            if point and f'P458_POINT {point}\n'.encode() in data:
                guest.finish(kill=True);break
            time.sleep(0.03)
        require(guest.process.poll() is not None,'VM observation timeout')
    finally:end_guest(guest)
    data=guest.log()
    errors=re.findall(rb'^P458_GUARD_ERROR stage=(\S+) errno=([0-9]+)$',data,re.M)
    return dict(serial=pin(guest.serial),initramfs=pin(guest.out/'initramfs.cpio.gz'),
        exit=guest.process.returncode,point=point,
        point_seen=bool(point and f'P458_POINT {point}\n'.encode() in data),
        errors=[dict(stage=a.decode(),errno=int(b)) for a,b in errors],
        superblock=superblock(guest.disk))


def reobserve(out,built,disk,expected=None,admissible=False):
    before=disk_pin(disk)
    guest=vm.Guest(out,built,'b2-before-mount',disk)
    row=observe(guest,'b2-before-mount')
    require(disk_pin(disk)==before,'read-only reobservation changed disk contents/extents/mtime')
    if admissible:require(row['point_seen'] and not row['errors'],'read-only phase did not remain admissible')
    else:
        require(not row['point_seen'] and len(row['errors'])==1 and row['errors'][0]['stage']==expected,
                'reobservation did not reject at the selected boundary')
    row['disk_unchanged']=True
    save(out/'result.json',row)
    return row


def boot2_cut(out,built,seed,case):
    out.mkdir(mode=0o700);disk=out/'disk.ext4';clone(seed,disk,out/'copy.log')
    first=observe(vm.Guest(out/'first',built,case,disk),case if case!='b2-clean-error' else None)
    if case=='b2-before-mount':
        require(first['point_seen'] and not first['errors'],'cut point not reached')
        second=reobserve(out/'reobserve',built,disk,admissible=True)
    else:
        if case=='b2-clean-error':
            require(not first['errors'] and first['superblock']['state']==1 and not first['superblock']['recover'],
                    'clean error-unmount failed')
            expected='mount-count'
        else:
            require(first['point_seen'] and not first['errors'],'cut point not reached')
            expected='clean-superblock'
        second=reobserve(out/'reobserve',built,disk,expected)
    result=dict(status='PASS_H0_BOOT2_CUT',case=case,first=first,reobserve=second,device_actions=0)
    save(out/'result.json',result);print('PASS_BOOT2_CUT',case,flush=True)
    return result


def debug(disk,out,label,command):
    regular(disk)
    handle=raw.acquire_command(['/usr/sbin/debugfs','-w','-R',command,str(disk)],out,label,
        timeout=30,stdout_maximum=16384,stderr_maximum=16384)
    require(handle.returncode==0 and not handle.timed_out and not handle.output_exceeded and
            handle.producer_error_type is None,'debugfs mutation producer failed')
    stderr=raw.read_stderr(handle,maximum=16384).decode()
    require(stderr=='debugfs 1.47.2 (1-Jan-2025)\n','debugfs mutation diagnostics differ')
    return pin(handle.receipt_path)


def reseal(record,key):
    record=bytearray(record);record[224:]=hmac.digest(key,vm.DOMAIN+record[:224],'sha256');return bytes(record)


def mutation(out,built,seed,normal,case):
    out.mkdir(mode=0o700);disk=out/'disk.ext4';clone(seed,disk,out/'copy.log')
    key=verify(built['key']).read_bytes();e=(normal/'b1-early.bin').read_bytes();r=(normal/'b1-runtime.bin').read_bytes()
    writes={};expected='record-auth'
    if case=='bad-mac':writes['early-b1']=e[:-1]+bytes([e[-1]^1])
    elif case=='partial-runtime':writes['runtime-b1']=r[:-1];expected='record-metadata'
    elif case=='missing-intent':writes['runtime-b1']=r[:-256];expected='runtime-length'
    elif case=='foreign-run':
        body=bytearray(e);body[160:176]=b'Z'*16;writes['early-b1']=reseal(body,key)
    elif case=='cross-boot':
        changed=[];previous=bytes(32)
        for offset in range(0,len(r),256):
            body=bytearray(r[offset:offset+256]);body[40:72]=b'Z'*32;body[104:136]=previous
            sealed=reseal(body,key);changed.append(sealed);previous=hashlib.sha256(sealed).digest()
        writes['runtime-b1']=b''.join(changed);expected='runtime-early-join'
    elif case=='overflow':
        body=bytearray(e);struct.pack_into('<I',body,20,65532);struct.pack_into('<I',body,24,65533)
        writes['early-b1']=reseal(body,key)
    elif case=='wrong-baseline':
        body=bytearray(e);base=struct.unpack_from('<I',body,20)[0]+1
        struct.pack_into('<I',body,20,base);struct.pack_into('<I',body,24,base+1)
        first=reseal(body,key);writes['early-b1']=first;changed=[];previous=bytes(32)
        for offset in range(0,len(r),256):
            body=bytearray(r[offset:offset+256]);struct.pack_into('<I',body,20,base);struct.pack_into('<I',body,24,base+2)
            body[72:104]=hashlib.sha256(first).digest();body[104:136]=previous
            sealed=reseal(body,key);changed.append(sealed);previous=hashlib.sha256(sealed).digest()
        writes['runtime-b1']=b''.join(changed);expected='mount-count'
    elif case=='existing-empty-b2':writes['early-b2']=b'';expected='record-metadata'
    else:raise ValueError('unknown mutation')
    receipts=[]
    for name,body in writes.items():
        path='/var/lib/lab/p458-'+built['run']+'-'+name;payload=out/(name+'.bin');payload.write_bytes(body)
        if not name.endswith('b2'):receipts.append(debug(disk,out,'remove-'+name,'rm '+path))
        receipts.append(debug(disk,out,'write-'+name,'write '+str(payload)+' '+path))
        receipts.append(debug(disk,out,'mode-'+name,'set_inode_field '+path+' mode 0100600'))
    result=reobserve(out/'reobserve',built,disk,expected)
    value=dict(status='PASS_H0_REAL_READER_REJECTION',case=case,mutations=receipts,reobserve=result,device_actions=0)
    save(out/'result.json',value);print('PASS_READER_REJECTION',case,flush=True)
    return value


def first_failure(out,built,case):
    out.mkdir(mode=0o700);disk=out/'disk.ext4';clone(disk_verify(built['seed']),disk,out/'copy.log')
    guest=vm.Guest(out/'guest',built,case,disk);guest.start()
    try:
        first,last,samples=guest.services(1)
        response=vm.once_control(guest,out,'reboot',first['boot'])
        accepted=b'P458_REBOOT_REQUEST_ACCEPTED\n' in raw.read_stdout(response,maximum=32768)
        if case in ('intent-before-command','rc6-before-remount'):
            guest.wait_point(case);guest.finish(kill=True)
            if case=='intent-before-command':require(not accepted,'intent-only path claimed reboot acceptance')
        else:
            require(case=='failed-root-remount','unknown first-boot failure')
            guest.finish(timeout=40)
            require(b'P458_INJECT root-remount-omitted' in guest.log() and
                    b'P458_GUARD_ERROR stage=clean-superblock' in guest.log(),
                    'failed remount did not reject next boot')
        require(superblock(disk)['recover'],'interrupted first-boot root not dirty')
        observed=reobserve(out/'reobserve',built,disk,'clean-superblock')
        result=dict(status='PASS_H0_FIRST_BOOT_FAILURE',case=case,
            first=vm.public_result(first),last=vm.public_result(last),samples=len(samples),
            accepted_response=accepted,reboot_intent=pin(out/'reboot-intent.json'),
            reboot_capture=pin(response.receipt_path),serial=pin(guest.serial),
            reobserve=observed,device_actions=0)
        save(out/'result.json',result);print('PASS_FIRST_BOOT_FAILURE',case,flush=True)
        return result
    finally:end_guest(guest)


def cuts(out,built,normal):
    out.mkdir(mode=0o700);positive=json.loads((normal/'result.json').read_text())
    require(positive['status']=='PASS_H0_TWO_REAL_DEBIAN_BOOTS','normal producer not complete')
    seed=disk_verify(positive['boot1_clean'])
    save(out/'inputs.json',dict(build=pin(Path(built['_receipt'])),normal=pin(normal/'result.json'),
        source=pin(Path(__file__)),device_actions=0))
    rows=[]
    for case in ('b2-before-mount','b2-after-mount','b2-after-early','b2-clean-error'):
        rows.append(boot2_cut(out/case,built,seed,case))
    for case in ('bad-mac','partial-runtime','missing-intent','foreign-run','cross-boot','overflow','wrong-baseline','existing-empty-b2'):
        rows.append(mutation(out/case,built,seed,normal,case))
    folder=out/'third-boot';folder.mkdir();disk=folder/'disk.ext4';clone(normal/'disk.ext4',disk,folder/'copy.log')
    third=reobserve(folder/'reobserve',built,disk,'second-phase-consumed')
    rows.append(dict(case='third-boot',reobserve=third))
    folder=out/'unexpected-remount';folder.mkdir();disk=folder/'disk.ext4';clone(disk_verify(built['seed']),disk,folder/'copy.log')
    unexpected=observe(vm.Guest(folder/'guest',built,'unexpected-remount',disk))
    require([r['stage'] for r in unexpected['errors']]==['mount-count'],'extra RW remount did not reject')
    rows.append(dict(case='unexpected-remount',observation=unexpected))
    folder=out/'initial-overflow';folder.mkdir();disk=folder/'disk.ext4';clone(disk_verify(built['seed']),disk,folder/'copy.log')
    debug(disk,folder,'overflow','ssv mnt_count 65533')
    overflow=reobserve(folder/'reobserve',built,disk,'mount-count-overflow')
    rows.append(dict(case='initial-overflow',reobserve=overflow))
    result=dict(status='PASS_H0_CUTS_AND_REAL_READER_NEGATIVES',cases=rows,device_actions=0)
    save(out/'result.json',result)
    print(result['status'],len(rows),flush=True)


def failures(out,built):
    out.mkdir(mode=0o700)
    save(out/'inputs.json',dict(build=pin(Path(built['_receipt'])),source=pin(Path(__file__)),device_actions=0))
    cases=('intent-before-command','rc6-before-remount','failed-root-remount')
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows=list(pool.map(lambda case:first_failure(out/case,built,case),cases))
    save(out/'result.json',dict(status='PASS_H0_FIRST_BOOT_FAILURE_CORPUS',cases=rows,device_actions=0))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('cuts','failures'))
    parser.add_argument('--build',required=True,type=Path);parser.add_argument('--normal',type=Path)
    parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();os.umask(0o077)
    out=args.output.absolute();require(out.resolve()==out and out.is_relative_to(vm.PRIVATE),'direct private output required')
    path=regular(args.build/'build.json');built=json.loads(path.read_text());built['_receipt']=str(path)
    for source in built['sources']:verify(source)
    if args.phase=='cuts':require(args.normal is not None,'normal evidence required');cuts(out,built,args.normal.absolute())
    else:failures(out,built)


if __name__=='__main__':main()
