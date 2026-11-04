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
import tempfile
import time

from prepare import ROOT, digest, require
from verify import request, verify, response_size, FDT_LIMIT, has_ssh, has_download
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


def test(prepared, init, output, *, bad_key=False, kernel_label='kernel-1',ssh_case='positive',download_case='positive'):
    prepared,init,output=prepared.resolve(),init.resolve(),output.resolve()
    require(output.is_relative_to(ROOT/'workspace/private'),'private VM output')
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    binding=inputs(prepared,init,kernel_label)
    source=snapshot(output)
    manifest=json.loads((init/'result.json').read_text())
    ssh=has_ssh(manifest)
    download=has_download(manifest)
    require(download_case=='positive' or download and not bad_key,'Download case requires its own runtime')
    require(ssh_case=='positive' or ssh and not bad_key,'SSH case requires an authenticated SSH RAM fixture')
    kernel_record=json.loads((prepared/(kernel_label+'-result.json')).read_text())
    kernel=Path(kernel_record['image'])
    ramdisk=Path(manifest['initramfs']['path'])
    qroot=ROOT/'workspace/private/tools/qemu-arm64-10.2.1/root'
    qemu=qroot/'usr/bin/qemu-system-aarch64'
    with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    ssh_forward=''
    if ssh:
        with socket.socket() as listener:listener.bind(('127.0.0.1',0));ssh_port=listener.getsockname()[1]
        ssh_forward=f',hostfwd=tcp:127.0.0.1:{ssh_port}-:22'
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
             '-netdev',f'user,id=net0,net={prefix},host={net["host_ip"]},dhcpstart={net["device_ip"]},hostfwd=tcp:127.0.0.1:{port}-:{manifest["port"]}'+ssh_forward,
             '-device','virtio-net-device,netdev=net0']
    qmp_directory=None;monitor=None
    if download and not bad_key:
        qmp_directory=tempfile.TemporaryDirectory(prefix='dq-',dir=ROOT/'workspace/private/tmp')
        qmp_path=Path(qmp_directory.name)/'qmp'
        command+=['-qmp','unix:'+str(qmp_path)+',server=on,wait=off']
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
                's22plus-mainline-retained-marker-v7','s22plus-mainline-retained-initcall-trace-v8',
                's22plus-mainline-retained-deferred-probe-v9',
                's22plus-mainline-retained-deferred-probe-v10'):
            from retained_kernel_vm import nomap_fixture
            fixture=nomap_fixture(qemu,env,output,'off')
            command+=['-dtb',str(fixture)]
            (output/'command.json').write_text(json.dumps(dict(command=command,qemu_sha256=digest(qemu),
                fixture_dtb=dict(path=str(fixture),sha256=digest(fixture))),indent=2)+'\n')
    started=time.monotonic();raw=bytearray();nonce=secrets.token_bytes(32)
    persist(output/'nonce.bin',nonce)
    key=Path(manifest['key_path']).read_bytes()
    if bad_key:key=bytes([key[0]^1])+key[1:]
    query=request(key,bytes.fromhex(manifest['candidate_id']),nonce,manifest=manifest)
    maximum=response_size(manifest)+FDT_LIMIT
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
            if download and not bad_key:
                import download_vm
                monitor=download_vm.open_monitor(qmp_path,output,persist)
            with socket.create_connection(('127.0.0.1',port),timeout=5) as client:
                client.settimeout(10)
                client.sendall(query)
                if download and not bad_key:
                    import download_vm
                    raw=download_vm.exchange(client,output,manifest,nonce,download_case,persist)
                else:
                    while len(raw)<=maximum:
                        chunk=client.recv(min(65536,maximum+1-len(raw)))
                        if not chunk:break
                        raw.extend(chunk)
            if not (output/'response.raw').exists():persist(output/'response.raw',bytes(raw))
            if download and not bad_key:download_vm.settled(output,proc,download_case,monitor,persist)
            if ssh and not bad_key:
                import sys
                import ssh_ram
                sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
                import device_action_raw_capture_v1 as capture_raw
                proof=verify(output/'response.raw',manifest,nonce,vm=True)
                require(proof['ssh_ready'], 'packaged SSH listener did not become ready')
                persist(output/'known-hosts',ssh_ram.known_hosts(manifest['debian_ram']))
                argv=ssh_ram.vm_command(manifest['debian_ram'],'/usr/bin/ssh',output/'known-hosts',
                                       ssh_port,ssh_case,output)
                executable=ssh_ram.pin('/usr/bin/ssh')
                command_record=dict(argv=argv,executable=executable,case=ssh_case)
                if ssh_case=='wrong-key':
                    subprocess.run(['/usr/bin/ssh-keygen','-q','-t','ed25519','-N','','-f',str(output/'wrong-key')],check=True)
                    (output/'wrong-key').chmod(0o400);command_record['wrong_key']=ssh_ram.pin(output/'wrong-key')
                persist(output/'ssh-command.json',json.dumps(command_record,indent=2).encode()+b'\n')
                handle=capture_raw.acquire_command(argv,output,'ssh',timeout=20,
                    stdout_maximum=1024,stderr_maximum=16384,env={'LANG':'C','LC_ALL':'C','PATH':'/usr/bin:/bin'})
                require(ssh_ram.pin('/usr/bin/ssh')==executable,'VM SSH client changed during acquisition')
                ssh_proof=ssh_ram.vm_outcome(handle,proof['boot_id'],ssh_case)
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
            if monitor is not None:download_vm.finish_monitor(monitor,output,persist)
            if qmp_directory is not None:qmp_directory.cleanup()
            if sparse is not None and sparse.exists():sparse.unlink()
            # Preserve the settled producer and complete raw set even when a
            # later SSH/result interpreter rejects otherwise complete bytes.
            capture(output,binding,source,bad_key=bad_key,elapsed=round(time.monotonic()-started,3),returncode=proc.returncode)
    require(inputs(prepared,init,kernel_label)==binding,'VM input changed during acquisition')
    if bad_key:
        result={'status':'PASS_H0_VM_UNAUTHENTICATED_REQUEST_REJECTED'}
    else:
        result=verify(output/'response.raw',manifest,nonce,vm=True)
        if ssh:result.update(ssh=ssh_proof,ssh_case=ssh_case)
        if download:result['download_case']=download_case
    result.update(elapsed_seconds=round(time.monotonic()-started,3),
                  kernel_sha256=kernel_record['sha256'],device_actions=0)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'elapsed_seconds':result['elapsed_seconds']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared',type=Path,required=True);p.add_argument('--init',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--bad-key',action='store_true')
    p.add_argument('--kernel-label',default='kernel-1')
    p.add_argument('--ssh-case',choices=('positive','wrong-key','root','forced-command','pty','forwarding','sftp'),default='positive')
    p.add_argument('--download-case',choices=('positive','wrong-control-key','wrong-boot','legacy-command','extra-tail','partial-control','missing-eof'),default='positive')
    p.add_argument('--recheck-run',type=Path,help='revalidate a complete positive capture without starting QEMU')
    a=p.parse_args()
    if a.recheck_run:
        require(not a.bad_key,'recheck supports positive captures only')
        recheck(a.prepared,a.init,a.recheck_run,a.output,kernel_label=a.kernel_label)
    else:test(a.prepared,a.init,a.output,bad_key=a.bad_key,kernel_label=a.kernel_label,ssh_case=a.ssh_case,download_case=a.download_case)
