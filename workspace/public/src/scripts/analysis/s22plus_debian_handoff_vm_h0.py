"""Real ARM64 installed SysVinit/SSH rehearsal; no physical-device transport."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import select
import shutil
import socket
import subprocess
import tempfile
import time
import s22plus_switch_root_vm_h0 as base
import s22plus_debian_handoff_protocol_v1 as protocol
import s22plus_debian_handoff_profile_v1 as profile
import s22plus_debian_access_v1 as access
import device_action_raw_capture_v1 as raw
from s22plus_native_records_v3 import pin,publish,read,require,verify

ROOT=base.ROOT


def setup(out,helpers,case):
    require(case in ('complete','dirty','mismatch'),'unknown Debian VM root fixture')
    return base.setup(out,helpers,case,handoff=True)


def outside_native(path):
    first=base.vm.fs.FIRST_LBA*4096;last=first+base.vm.fs.SIZE_BYTES
    result=hashlib.sha256()
    with path.open('rb',buffering=0) as source:
        for start,end in ((0,first),(last,path.stat().st_size)):
            position=start
            while position<end:
                try:position=os.lseek(source.fileno(),position,os.SEEK_DATA)
                except OSError as error:
                    if error.errno==6:break
                    raise
                if position>=end:break
                stop=min(end,os.lseek(source.fileno(),position,os.SEEK_HOLE))
                source.seek(position)
                while position<stop:
                    chunk=source.read(min(1024*1024,stop-position));require(chunk,'short VM disk read')
                    result.update(position.to_bytes(8,'little')+chunk);position+=len(chunk)
    return result.hexdigest()


def ssh_command(plan,port,command):
    require(command in ('health','shutdown'),'unselected VM SSH command')
    for name in ('ssh','client_key','known_hosts'):verify(plan[name],maximum=32*1024*1024)
    return [plan['ssh']['path'],'-F','/dev/null','-i',plan['client_key']['path'],
        '-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes',
        '-o','UserKnownHostsFile='+plan['known_hosts']['path'],'-o','GlobalKnownHostsFile=/dev/null',
        '-o','HostKeyAlias='+plan['link']['ssh_address'],'-o','LogLevel=ERROR',
        '-o','ConnectTimeout=1','-o','ConnectionAttempts=1','-p',str(port),'root@127.0.0.1',command]


def inspect_after(out,*,positive,negative):
    """Read an extracted regular-file partition, never a host block device."""
    source=out/'disk.img';destination=out/'native-after.ext4'
    first=base.vm.fs.FIRST_LBA*4096;end=first+base.vm.fs.SIZE_BYTES
    with source.open('rb',buffering=0) as src,destination.open('xb',buffering=0) as dst:
        dst.truncate(base.vm.fs.SIZE_BYTES);position=first
        while position<end:
            try:start=os.lseek(src.fileno(),position,os.SEEK_DATA)
            except OSError as error:
                if error.errno==6:break
                raise
            if start>=end:break
            stop=min(end,os.lseek(src.fileno(),start,os.SEEK_HOLE));src.seek(start);dst.seek(start-first)
            while start<stop:
                data=src.read(min(1024*1024,stop-start));require(data,'short VM extract')
                require(dst.write(data)==len(data),'short VM partition write');start+=len(data)
            position=stop
        dst.flush();os.fsync(dst.fileno())
    handle=raw.acquire_command(['/usr/sbin/debugfs','-R','cat /var/lib/lab/boot-count',str(destination)],out,
        'boot-count-after',timeout=20,stdout_maximum=4096,stderr_maximum=4096)
    require(handle.returncode==0 and not handle.timed_out and not handle.output_exceeded and
        handle.producer_error_type is None,'debugfs producer failed')
    count=raw.read_stdout(handle,maximum=4096)
    diagnostic=raw.read_stderr(handle,maximum=4096)
    require(diagnostic==b'debugfs 1.47.2 (1-Jan-2025)\n' if positive else
        diagnostic==b'debugfs 1.47.2 (1-Jan-2025)\n/var/lib/lab/boot-count: File not found by ext2_lookup \n',
        'VM root read did not have its expected filesystem/lookup result')
    require(count==(b'1\n' if positive else b'') if positive or negative else True,'failed hook let rcS update boot-count')
    with destination.open('rb') as disk:disk.seek(1024);superblock=disk.read(1024)
    clean=int.from_bytes(superblock[0x3a:0x3c],'little')==1 and not int.from_bytes(superblock[0x60:0x64],'little')&4 and not any(superblock[0xe8:0xec])
    if positive:
        require(clean,'VM normal shutdown did not clean ext4')
        checked=raw.acquire_command(['/usr/sbin/e2fsck','-fn',str(destination)],out,'fs-after',timeout=60,
            stdout_maximum=16384,stderr_maximum=16384)
        require(checked.returncode==0 and not checked.timed_out and not checked.output_exceeded and
            checked.producer_error_type is None and raw.read_stderr(checked,maximum=16384)==b'e2fsck 1.47.2 (1-Jan-2025)\n',
            'VM post-shutdown e2fsck producer or result failed')
    return dict(boot_count_raw_sha256=digest(count),clean_ext4=clean)


def digest(data):return hashlib.sha256(data).hexdigest()


def run(out,key,*,negative=False,release_fault=None):
    setup_value=read(out/'setup.json');built=read(verify(setup_value['helpers']));case=setup_value['case']
    require(setup_value['schema']=='s22plus-debian-handoff-vm-v1' and built['virt'] is True and
        built['key_sha256']==protocol.health.digest(key),'VM Debian binding differs')
    require(release_fault in (None,'bad','missing') and (release_fault is None or negative),'invalid VM release fault')
    _,_,plan=profile.prior_inputs();plan=dict(plan,root_run_id=profile.prior_inputs()[0]['run_id'],
        candidate=dict(namespace=built['debian']['namespace'],version=built['debian']['version'],run_id=built['run_id_hex']))
    before=base.vm.fixture_tools.sparse_digest(out/'disk.img');outside=outside_native(out/'disk.img')
    publish(out/'disk-before.json',dict(digest=before,outside_native=outside,device_actions=0))
    scratch=Path(tempfile.mkdtemp(prefix='s22-dhvm-'));endpoint=scratch/'tty.sock'
    with socket.socket() as reserve:reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
    link=plan['link'];network=ipaddress.ip_interface(link['device_address']).network
    # SLIRP needs a distinct DNS endpoint; this test-only broader subnet does
    # not alter the retained guest/host addresses or enable external routing.
    if network.prefixlen>24:network=network.supernet(new_prefix=24)
    net=f'user,id=net,restrict=on,net={network},host={link["host_address"].split("/")[0]},'
    net+=f'dhcpstart={link["ssh_address"]},dns={network.network_address+254},hostfwd=tcp:127.0.0.1:{port}-{link["ssh_address"]}:22'
    command=[verify(setup_value['qemu'],maximum=128*1024*1024),'-machine','virt','-cpu','cortex-a76','-smp','2','-m','1024',
        '-netdev',net,'-device','virtio-net-device,netdev=net,mac='+link['device_mac'],
        '-display','none','-monitor','none','-serial',f'file:{out}/serial.log','-no-reboot',
        '-chardev',f'socket,id=sw,path={endpoint},server=on,wait=off','-device','virtio-serial-device',
        '-device','virtconsole,chardev=sw','-kernel',verify(setup_value['kernel'],maximum=128*1024*1024),
        '-initrd',verify(setup_value['initramfs'],maximum=16*1024*1024),'-append','console=ttyAMA0 rdinit=/init panic=1',
        '-drive',f'if=none,id=root,file={out}/disk.img,format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    (out/'command.json').write_text(json.dumps([str(x) for x in command])+'\n')
    rx=bytearray();tx=bytearray();pending=bytearray();records=None;ssh_health=None;shutdown=None
    try:
        with (out/'qemu.log').open('xb') as log,(out/'rx.bin').open('xb') as capture,(out/'tx.bin').open('xb') as transmit:
            process=subprocess.Popen([str(x) for x in command],stdout=log,stderr=subprocess.STDOUT,
                env=dict(os.environ,LD_LIBRARY_PATH=str(base.vm.QEMU/'usr/lib/x86_64-linux-gnu')))
            try:
                deadline=time.monotonic()+240;negative_end=None
                while not endpoint.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                require(process.poll() is None,'VM exited before console setup')
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as stream:
                    stream.connect(str(endpoint));stream.setblocking(False)
                    while time.monotonic()<deadline:
                        ready,_,_=select.select([stream],[],[],.05)
                        if ready:
                            part=stream.recv(4096)
                            if not part:break
                            capture.write(part);capture.flush();os.fsync(capture.fileno());rx.extend(part);pending.extend(part)
                            require(len(rx)<=protocol.MAXIMUM,'VM handoff stream overflow')
                            while len(pending)>=16:
                                size=protocol.frames.HEADER.unpack(pending[:16])[3];require(size<=1023,'VM frame overflow')
                                if len(pending)<16+size:break
                                frame=protocol.frames.decode_frame(bytes(pending[:16+size]));del pending[:16+size]
                                if records is None:
                                    boot=re.findall(rb'SWVM_BOOT ([0-9a-f]{64})\r?\n',(out/'serial.log').read_bytes())
                                    require(len(boot)==1,'VM kernel identity absent')
                                    records=protocol.reader(key,bytes.fromhex(built['run_id_hex']),base.NONCE,
                                        bytes.fromhex(boot[0].decode()),built)
                                records.accept(frame)
                                if negative and records.continued and negative_end is None:negative_end=time.monotonic()+25
                                kind=protocol.CONTINUE if records.proof is not None and not tx else \
                                    protocol.RELEASE if records.init_proof is not None and len(tx)==48 else None
                                if kind:
                                    data=protocol.encode(key,records.run,base.NONCE,kind,6 if kind==protocol.CONTINUE else 7)
                                    if kind==protocol.RELEASE and release_fault=='missing':continue
                                    if kind==protocol.RELEASE and release_fault=='bad':
                                        data=protocol.encode(key,records.run,b'x'*32,kind,7)
                                    transmit.write(data);transmit.flush();os.fsync(transmit.fileno());tx.extend(data);stream.sendall(data)
                        if records and (records.released or records.stop):break
                        if negative_end is not None and time.monotonic()>=negative_end:break
                        if process.poll() is not None:break
                    if records and records.released and not negative:
                        for ordinal in range(1,61):
                            handle=raw.acquire_command(ssh_command(plan,port,'health'),out,f'health-{ordinal:03d}',
                                timeout=5,stdout_maximum=65536,stderr_maximum=16384)
                            if handle.returncode==0:
                                ssh_health=access.health_projection(handle,plan,boot_sha256=records.boot.hex())
                                require(ssh_health['boot_id_sha256']==records.boot.hex(),'SSH crossed a kernel boot')
                                break
                            require(time.monotonic()<deadline and process.poll() is None,'VM SSH deadline or process failed')
                            time.sleep(.5)
                        require(ssh_health is not None,'VM Debian SSH health absent')
                        handle=raw.acquire_command(ssh_command(plan,port,'shutdown'),out,'shutdown',timeout=20,
                            stdout_maximum=65536,stderr_maximum=16384)
                        shutdown=access.shutdown_projection(handle,plan['link']['ssh_address'])
                    elif negative:
                        require(records and records.continued,'negative VM did not reach installed init')
                        if negative_end is not None:time.sleep(max(0,negative_end-time.monotonic()))
                        handle=raw.acquire_command(ssh_command(plan,port,'health'),out,'negative-health',timeout=3,
                            stdout_maximum=65536,stderr_maximum=16384)
                        require(handle.returncode!=0 and process.poll() is None,'failed hook permitted services or exited')
                    if not negative:process.wait(timeout=max(1,deadline-time.monotonic()))
            finally:
                if process.poll() is None:process.kill();process.wait()
        require(not pending,'VM handoff ended inside a frame')
        after=base.vm.fixture_tools.sparse_digest(out/'disk.img');after_outside=outside_native(out/'disk.img')
        require(outside==after_outside,'Debian VM wrote outside native_data')
        filesystem=inspect_after(out,positive=case=='complete' and not negative,negative=negative)
        if case in ('dirty','mismatch'):
            require(records and records.stop and not records.proof and before==after,'admission negative wrote or proved transition')
        elif not negative:
            require(records and records.released and ssh_health and shutdown and process.returncode==0 and
                b'reboot: Power down' in (out/'serial.log').read_bytes(),'VM actual Debian boot and shutdown unproved')
        return publish(out/'result.json',dict(schema='s22plus-debian-handoff-vm-result-v1',setup=pin(out/'setup.json'),
            result=records.projection() if records else None,ssh_health=ssh_health,shutdown=shutdown,
            disk_changed=before!=after,outside_native_unchanged=True,negative_hook_park=negative,
            filesystem=filesystem,release_fault=release_fault,
            scope='REAL_ARM64_SYSVINIT_NOT_SAMSUNG_USB',device_actions=0,rx=pin(out/'rx.bin'),
            tx=dict(path=str(out/'tx.bin'),size=len(tx),sha256=digest(bytes(tx)))))
    finally:shutil.rmtree(scratch)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('setup','run'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--helpers',type=Path)
    p.add_argument('--case',default='complete');p.add_argument('--key',type=Path);p.add_argument('--negative',action='store_true')
    p.add_argument('--release-fault',choices=('bad','missing'))
    args=p.parse_args();out=args.output.absolute()
    print((setup(out,args.helpers.absolute(),args.case) if args.command=='setup' else
        run(out,args.key.read_bytes(),negative=args.negative,release_fault=args.release_fault))['sha256'])
