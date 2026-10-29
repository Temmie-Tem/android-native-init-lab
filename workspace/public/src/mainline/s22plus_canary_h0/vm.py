#!/usr/bin/env python3
"""Boot the actual kernel and VM-marked PID1; use loopback QEMU networking."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time

from prepare import ROOT, digest, require
from verify import request, verify, RESPONSE, FDT_LIMIT
from vm_evidence import inputs, snapshot, capture, recheck


def persist(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,'wb',closefd=False) as stream:stream.write(data);stream.flush()
        os.fchmod(fd,0o400);os.fsync(fd)
    finally:os.close(fd)
    parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(parent)
    finally:os.close(parent)


def test(prepared, init, output, *, bad_key=False, kernel_label='kernel-1'):
    prepared,init,output=prepared.resolve(),init.resolve(),output.resolve()
    require(output.is_relative_to(ROOT/'workspace/private'),'private VM output')
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    binding=inputs(prepared,init,kernel_label)
    source=snapshot(output)
    manifest=json.loads((init/'result.json').read_text())
    kernel_record=json.loads((prepared/(kernel_label+'-result.json')).read_text())
    kernel=Path(kernel_record['image'])
    ramdisk=Path(manifest['initramfs']['path'])
    qroot=ROOT/'workspace/private/tools/qemu-arm64-10.2.1/root'
    qemu=qroot/'usr/bin/qemu-system-aarch64'
    with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    serial=output/'serial.log';stderr=output/'qemu.stderr'
    net=manifest['network'];prefix=str(ipaddress.IPv4Interface(net['device_ip']+'/'+net['netmask']).network)
    # The marked physical kernel intentionally probes the fixed high Samsung
    # log slice before normal MMU setup. Back that address in this emulator;
    # its zero/invalid header exercises the skip path without changing Image.
    memory='36G' if 'retained_marker' in kernel_record else '768'
    sparse=output/'guest-ram.sparse' if 'retained_marker' in kernel_record else None
    memory_args=(['-object',f'memory-backend-file,id=vmram,size=36G,mem-path={sparse},share=on,reserve=off,prealloc=off,dump=off'] if sparse else [])
    command=[str(qemu),*memory_args,'-machine','virt,memory-backend=vmram' if sparse else 'virt','-cpu','cortex-a76','-smp','1','-m',memory,
             '-no-reboot','-display','none','-monitor','none','-serial','file:'+str(serial),
             '-kernel',str(kernel),'-initrd',str(ramdisk),
             # CMDLINE_FORCE comes from the same actual g0q kernel. The VM
             # fixture opens ttyAMA0 directly; -append would be ignored.
             '-netdev',f'user,id=net0,net={prefix},host={net["host_ip"]},dhcpstart={net["device_ip"]},hostfwd=tcp:127.0.0.1:{port}-:{manifest["port"]}',
             '-device','virtio-net-device,netdev=net0']
    (output/'command.json').write_text(json.dumps({'command':command,'qemu_sha256':digest(qemu)},indent=2)+'\n')
    env=dict(os.environ,LD_LIBRARY_PATH=str(qroot/'usr/lib/x86_64-linux-gnu'))
    fixture=None
    if 'retained_marker' in kernel_record:
        marker_source=kernel_record['retained_marker']
        require(digest(marker_source['path'])==marker_source['sha256'],'VM marker provenance changed')
        marker_config=json.loads(Path(marker_source['path']).read_text())['config']
        require(digest(marker_config['path'])==marker_config['sha256'],'VM marker config changed')
        if json.loads(Path(marker_config['path']).read_text())['schema'] in (
                's22plus-mainline-retained-marker-v3','s22plus-mainline-retained-marker-v4',
                's22plus-mainline-retained-marker-v5','s22plus-mainline-retained-marker-v6',
                's22plus-mainline-retained-marker-v7','s22plus-mainline-retained-initcall-trace-v8'):
            from retained_kernel_vm import nomap_fixture
            fixture=nomap_fixture(qemu,env,output,'off')
            command+=['-dtb',str(fixture)]
            (output/'command.json').write_text(json.dumps(dict(command=command,qemu_sha256=digest(qemu),
                fixture_dtb=dict(path=str(fixture),sha256=digest(fixture))),indent=2)+'\n')
    started=time.monotonic();raw=bytearray();nonce=secrets.token_bytes(32)
    persist(output/'nonce.bin',nonce)
    key=Path(manifest['key_path']).read_bytes()
    if bad_key:key=bytes([key[0]^1])+key[1:]
    query=request(key,bytes.fromhex(manifest['candidate_id']),nonce)
    persist(output/'request.raw',query)
    with stderr.open('xb') as err:
        proc=subprocess.Popen(command,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=err)
        try:
            until=time.monotonic()+90
            while time.monotonic()<until:
                require(proc.poll() is None,'QEMU exited early')
                text=serial.read_bytes().replace(b'\r\n',b'\n') if serial.exists() else b''
                require(b'G0Q_RAM_PARK' not in text,'PID1 parked before observer; inspect serial')
                if b'G0Q_RAM_OBSERVER_READY\n' in text:break
                time.sleep(.1)
            else:raise ValueError('VM observer did not become ready')
            with socket.create_connection(('127.0.0.1',port),timeout=5) as client:
                client.settimeout(10)
                client.sendall(query)
                while len(raw)<=RESPONSE+FDT_LIMIT:
                    chunk=client.recv(min(65536,RESPONSE+FDT_LIMIT+1-len(raw)))
                    if not chunk:break
                    raw.extend(chunk)
            persist(output/'response.raw',bytes(raw))
            if bad_key:
                require(not raw,'wrong key produced a response')
                until=time.monotonic()+2
                while time.monotonic()<until and b'G0Q_RAM_PARK error=13' not in serial.read_bytes():time.sleep(.05)
                require(b'G0Q_RAM_PARK error=13' in serial.read_bytes(),'wrong-key failure path absent')
        finally:
            if not (output/'response.raw').exists():persist(output/'response.raw',bytes(raw))
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
            if sparse is not None and sparse.exists():sparse.unlink()
    require(inputs(prepared,init,kernel_label)==binding,'VM input changed during acquisition')
    capture(output,binding,source,bad_key=bad_key,elapsed=round(time.monotonic()-started,3),returncode=proc.returncode)
    if bad_key:
        result={'status':'PASS_H0_VM_UNAUTHENTICATED_REQUEST_REJECTED'}
    else:
        result=verify(output/'response.raw',manifest,nonce,vm=True)
    result.update(elapsed_seconds=round(time.monotonic()-started,3),
                  kernel_sha256=kernel_record['sha256'],device_actions=0)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'elapsed_seconds':result['elapsed_seconds']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared',type=Path,required=True);p.add_argument('--init',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--bad-key',action='store_true')
    p.add_argument('--kernel-label',default='kernel-1')
    p.add_argument('--recheck-run',type=Path,help='revalidate a complete positive capture without starting QEMU')
    a=p.parse_args()
    if a.recheck_run:
        require(not a.bad_key,'recheck supports positive captures only')
        recheck(a.prepared,a.init,a.recheck_run,a.output,kernel_label=a.kernel_label)
    else:test(a.prepared,a.init,a.output,bad_key=a.bad_key,kernel_label=a.kernel_label)
