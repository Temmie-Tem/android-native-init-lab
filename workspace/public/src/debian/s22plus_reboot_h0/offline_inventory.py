#!/usr/bin/env python3
"""Content/path deltas from stopped, regular-file H0 ext4 disks; no replay.

debugfs rdump copies file bodies and links. Its known post-copy ownership
warnings are retained and explicitly excluded from any ownership claim. Actual
inode metadata for changed paths is separately captured with read-only stat.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

import reboot_vm as vm
from reboot_vm import require,regular,pin,save,disk_pin,raw


def inventory(out,disk):
    out.mkdir(mode=0o700);tree=out/'tree';tree.mkdir(mode=0o700)
    disk=regular(disk);before=disk_pin(disk)
    handle=raw.acquire_command(['/usr/sbin/debugfs','-R','rdump / '+str(tree),str(disk)],out,'dump',
        timeout=120,stdout_maximum=16384,stderr_maximum=4*1024**2)
    require(handle.returncode==0 and not handle.timed_out and not handle.output_exceeded and
            handle.producer_error_type is None,'rdump producer failed')
    require(not raw.read_stdout(handle,maximum=16384),'unexpected rdump stdout')
    lines=raw.read_stderr(handle,maximum=4*1024**2).decode().splitlines()
    require(lines and lines[0]=='debugfs 1.47.2 (1-Jan-2025)','debugfs version differs')
    warnings=[]
    for line in lines[1:]:
        match=re.fullmatch(r'(?:rdump|dump_file): Operation not permitted while changing ownership of (.+)',line)
        require(match is not None,'rdump has a non-ownership failure')
        path=Path(match[1]);require(path.is_relative_to(tree),'ownership diagnostic escaped output')
        warnings.append(str(path.relative_to(tree)))
    entries={};total=0
    for path in sorted(tree.rglob('*')):
        rel=path.relative_to(tree).as_posix();st=path.lstat()
        require(len(entries)<20000 and len(Path(rel).parts)<=32,'tree exceeds bound')
        if stat.S_ISLNK(st.st_mode):row=dict(type='symlink',target=os.readlink(path))
        elif stat.S_ISDIR(st.st_mode):row=dict(type='directory')
        elif stat.S_ISREG(st.st_mode):
            total+=st.st_size;require(st.st_size<=64*1024**2 and total<=512*1024**2,'content exceeds bound')
            with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            row=dict(type='file',size=st.st_size,sha256=digest)
        else:raise ValueError('unexpected special file in dumped VM root')
        entries[rel]=row
    require(entries and disk_pin(disk)==before,'offline dump changed source disk')
    result=dict(schema='p458-h0-content-path-inventory-v1',disk=before,dump_capture=pin(handle.receipt_path),
        entries=entries,total_regular_bytes=total,ownership_warnings=warnings,
        metadata_preservation_claim=False,replay=False,device_actions=0)
    save(out/'inventory.json',result)
    require(json.loads((out/'inventory.json').read_text())==result,'inventory did not reopen')
    return result


def inode(out,disk,name,label):
    require(re.fullmatch(r'[A-Za-z0-9_./-]+',name) and '..' not in Path(name).parts,'unselected stat path')
    handle=raw.acquire_command(['/usr/sbin/debugfs','-R','stat /'+name,str(regular(disk))],out,label,
        timeout=15,stdout_maximum=16384,stderr_maximum=16384)
    require(handle.returncode==0 and not handle.timed_out and not handle.output_exceeded and
            handle.producer_error_type is None,'inode stat producer failed')
    require(raw.read_stderr(handle,maximum=16384)==b'debugfs 1.47.2 (1-Jan-2025)\n','inode stat failed')
    text=raw.read_stdout(handle,maximum=16384).decode()
    mode=re.search(r'^Inode: ([0-9]+)\s+Type: ([a-z]+)\s+Mode:\s+([0-7]+)',text,re.M)
    owner=re.search(r'^User:\s+([0-9]+)\s+Group:\s+([0-9]+)\s+(?:Project:\s+[0-9]+\s+)?Size:\s+([0-9]+)',text,re.M)
    links=re.search(r'^Links:\s+([0-9]+)',text,re.M)
    require(mode and owner and links,'inode stat grammar differs')
    return dict(type=mode[2],mode=mode[3],uid=int(owner[1]),gid=int(owner[2]),
                size=int(owner[3]),links=int(links[1]),capture=pin(handle.receipt_path))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--build',required=True,type=Path)
    parser.add_argument('--normal',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();os.umask(0o077)
    out=args.output.absolute();require(out.resolve()==out and out.is_relative_to(vm.PRIVATE),'private direct output required')
    out.mkdir(mode=0o700);normal=args.normal.absolute()
    built=json.loads(regular(args.build/'build.json').read_text())
    result=json.loads(regular(normal/'result.json').read_text())
    require(result['status']=='PASS_H0_TWO_REAL_DEBIAN_BOOTS','closed normal VM required')
    disks=[vm.disk_verify(built['seed']),vm.disk_verify(result['boot1_clean']),regular(normal/'disk.ext4')]
    save(out/'inputs.json',dict(build=pin(args.build/'build.json'),normal=pin(normal/'result.json'),
        source=pin(Path(__file__)),debugfs=pin(Path('/usr/sbin/debugfs').resolve()),device_actions=0))
    inventories=[inventory(out/name,disk) for name,disk in zip(('before','after-boot1','after-boot2'),disks)]
    deltas=[]
    for index in (1,2):
        before=inventories[index-1]['entries'];after=inventories[index]['entries']
        changed=sorted(name for name in set(before)|set(after) if before.get(name)!=after.get(name))
        entries=[]
        for ordinal,name in enumerate(changed):
            entry=dict(path=name,before=before.get(name),after=after.get(name))
            if name in after:entry['actual_inode']=inode(out,disks[index],name,f'stat-{index}-{ordinal:03d}')
            entries.append(entry)
        deltas.append(dict(from_phase=index-1,to_phase=index,changes=entries))
    value=dict(status='PASS_H0_OFFLINE_CONTENT_PATH_DELTAS',deltas=deltas,
        inventories=[pin(out/name/'inventory.json') for name in ('before','after-boot1','after-boot2')],
        complete_root_admission=False,device_actions=0)
    save(out/'result.json',value)
    print('PASS_OFFLINE_CONTENT_PATH_DELTAS',[len(x['changes']) for x in deltas],flush=True)


if __name__=='__main__':main()
