"""H0. Run inside a fresh user/network namespace with only its loopback link."""
import argparse
import gzip
import ipaddress
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[2]
sys.path.insert(0, str(SRC / 'scripts/revalidation'))
sys.path.insert(0, str(SRC))
from mainline.s22plus_canary_h0 import debian_ram, download_vm, verify, udc_history
from mainline.s22plus_canary_h0.prepare import digest, require
from mainline.s22plus_udc_observation_h0 import decode
from mainline.s22plus_udc_observation_h0.live_vm.run import BASE, CASES, SIZE
import device_action_raw_capture_v1 as raw
import s22plus_mainline_access_v1 as access

TAP = 'udcvm0'


def archive(package, build, output, bridge, absent):
    wrapper = output/'vm-init'
    subprocess.run(['aarch64-linux-gnu-gcc', '-static', '-Os', '-Wall', '-Wextra', '-Werror',
                    bridge, '-o', wrapper], check=True)
    description = f'file /init {wrapper} 0755 0 0\n'
    if absent:
        (output/'empty').touch(exist_ok=False)
        description += f"file /vm-no-peer {output/'empty'} 0400 0 0\n"
    (output/'overlay.list').write_text(description)
    overlay = subprocess.check_output([build/'usr/gen_init_cpio', output/'overlay.list'])
    # The VM-only second archive replaces /init and execs the packaged PID 1.
    # It contains neither an observer nor an inittab override.
    original = Path(package['initramfs']['path']).read_bytes()
    path = output/'vm-initramfs.gz'
    path.write_bytes(gzip.compress(gzip.decompress(original) + overlay, mtime=0))
    return path


def configure_tap(net):
    require(set(os.listdir('/sys/class/net')) == {'lo'}, 'fresh network namespace required')
    subnet = ipaddress.IPv4Network((net['host_ip'], net['netmask']), strict=False)
    for args in (['tuntap','add','dev',TAP,'mode','tap'],
                 ['addr','add',f"{net['host_ip']}/{subnet.prefixlen}",'dev',TAP],
                 ['link','set',TAP,'up']):
        subprocess.run(['ip', *args], check=True)


def wait_ready(proc, serial):
    until = time.monotonic()+120
    while proc.poll() is None and time.monotonic() < until:
        text = serial.read_text(errors='replace') if serial.exists() else ''
        if 'VM_BRIDGE_FAIL' in text or 'G0Q_RAM_PARK' in text:
            raise RuntimeError('guest parked during startup; see private serial capture')
        if 'VM_NCM_BRIDGE_READY' in text and 'G0Q_RAM_OBSERVER_READY' in text:
            return
        time.sleep(.03)
    raise RuntimeError('guest/bridge not ready within wall deadline')


def capture_guest(proc, manifest, output, case):
    wait_ready(proc, output/'serial.log')
    wire_manifest = manifest
    if case == 'wrong-key':
        key = bytearray(Path(manifest['key_path']).read_bytes())
        key[0] ^= 1
        path = output/'wrong.key'
        path.write_bytes(key)
        wire_manifest = dict(manifest, key_path=str(path))
    handle = access.capture_connection(output, wire_manifest, {'interface': TAP},
                                      deadline_ns=access.clock()+20_000_000_000,
                                      guard=lambda: require(proc.poll() is None, 'guest exited'))
    connection = json.loads((output/'connection.json').read_bytes())
    attempt = json.loads((output/'attempt.json').read_bytes())
    require(connection['sent_complete_request'] and connection['descriptor_closed'] and connection['eof'],
            'PC did not capture a complete exchange')
    nonce = bytes.fromhex(attempt['nonce'])
    if case == 'wrong-key':
        raw.require_success(handle)
        require(not raw.read_stdout(handle,maximum=1024), 'wrong-key response had bytes')
        until = time.monotonic()+2
        while time.monotonic()<until and 'G0Q_RAM_PARK error=13' not in (output/'serial.log').read_text():
            time.sleep(.02)
        require('G0Q_RAM_PARK error=13' in (output/'serial.log').read_text(), 'wrong-key park absent')
        return dict(status='wrong-key request rejected')
    return verify.verify_vm_capture(handle, manifest, nonce)


def compare(result, case, region, initial, manifest, capture_dir, before, after):
    evidence = result['udc_history']
    pre = [s for s in evidence['samples'] if s['after_successful_bind'] and s['measured_ms'] < before]
    require(pre and before <= after <= result['uptime_ms'], 'pre-cable sample or cable chronology absent')
    sample = pre[-1]
    require(any(s['state']=='configured' and after < s['measured_ms'] <= result['uptime_ms']
                for s in evidence['samples']), 'post-connect configured state missing')
    require(sample['state']=='not attached' and evidence['bind_count']==1 and evidence['callback_result']==11,
            'pre-cable evidence differs')
    expected = {'bad-magic':'invalid LOGM magic','short-cursor':'cursor too short','readback':'slot readback verified'}
    require(evidence['publication']==expected[case], 'wrong retained publication reason')
    creds = manifest['debian_ram']['retained']
    decoded = decode.project(region[16:], *(Path(creds[k]['path']).read_bytes() for k in ('candidate','key')))
    if case == 'readback':
        cursor = struct.unpack_from('<I', initial, 8)[0] % (SIZE-16)
        begin = 16+cursor-256
        require(region[:begin]==initial[:begin] and region[begin+256:]==initial[begin+256:]
                and not (decoded['damaged'] or decoded['foreign']), 'retained slot boundary')
        wire = raw.read_stdout(raw.load_handle(capture_dir/'response.capture.json'),
                               maximum=verify.response_size(manifest)+verify.FDT_LIMIT)
        slot = wire[356:484]
        require(any(region[start:start+decode.SIZE]==slot for start in (begin, begin+decode.SIZE)),
                'authenticated live record is absent from both retained slots')
        require(any(record['boot_tag']==evidence['boot_tag'] and sample in record['samples']
                    for record in decoded['frames']), 'retained record differs from USB sample on this boot')
    else:
        require(region==initial and not decoded['frames'], 'rejected writer changed the region')
    return dict(pre_connect_sample=sample, before_connect_ms=before, after_connect_ms=after,
                retained_frames=len(decoded['frames']), retained_bytes_changed=region!=initial)


def run(args):
    output=args.output.resolve()
    require(output.is_relative_to(SRC.parents[1]/'private/outputs'), 'private output required')
    output.mkdir(mode=0o700, exist_ok=False)
    mapping = Path('/proc/self/uid_map').read_text().split()
    require(len(mapping)==3 and mapping[0]=='0' and int(mapping[1])>0 and mapping[2]=='1',
            'VM runner requires a single-user root mapping')
    manifest=json.loads(args.manifest.read_bytes())
    require(manifest['vm'] is True and manifest.get('udc_timer_return') is True, 'timed VM artifact required')
    require(manifest['debian_ram']['schema']==udc_history.SCHEMA, 'expected Debian UDC history protocol')
    debian_ram.validate(manifest, allow_h0_udc_history=True)
    require(all(digest(row['path']) == row['sha256'] for row in manifest['inputs']),
            'packaged source closure changed')
    configure_tap(manifest['network'])
    absent=args.case=='no-peer'
    initrd=archive(manifest,args.build,output,HERE/'bridge.c',absent)
    magic,cursor,_=CASES.get(args.case, CASES['bad-magic'])
    initial=struct.pack('<4I',22,magic,cursor,7901)+bytes([0xa5])*(SIZE-16)
    ram=output/'guest.sparse'
    with ram.open('xb') as f:
        f.truncate(36*1024**3); f.seek(BASE); f.write(initial)
    qemu=args.qroot/'usr/bin/qemu-system-aarch64'
    env=dict(os.environ, LD_LIBRARY_PATH=str(args.qroot/'usr/lib/x86_64-linux-gnu'))
    with tempfile.TemporaryDirectory(prefix='udcvm-') as tmp:
        qmp=Path(tmp)/'qmp'
        cmd=[str(qemu), '-machine','virt,memory-backend=ram,dtb-randomness=off','-m','36G',
             '-object',f'memory-backend-file,id=ram,size=36G,mem-path={ram},share=on,reserve=off,prealloc=off,dump=off',
             '-smp','1','-cpu','cortex-a76','-nodefaults','-no-reboot','-display','none','-monitor','none',
             '-serial',f'file:{output}/serial.log','-kernel',str(args.build/'arch/arm64/boot/Image'),
             '-dtb',str(args.dtb),'-initrd',str(initrd),'-netdev',f'tap,id=n,ifname={TAP},script=no,downscript=no',
             '-device','virtio-net-device,netdev=n']
        if absent:
            cmd+=['-icount','shift=4,sleep=off','-qmp',f'unix:{qmp},server=on,wait=on']
        (output/'command.json').write_text(json.dumps(cmd,indent=2))
        monitor=None
        def save(path, data):
            with path.open('xb') as f: f.write(data)
        try:
            with (output/'qemu.log').open('xb') as log:
                proc=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=env)
                try:
                    if absent:
                        until=time.monotonic()+10
                        while not qmp.exists() and proc.poll() is None and time.monotonic()<until: time.sleep(.02)
                        monitor=download_vm.open_monitor(qmp,output,save)
                        require(proc.wait(120)==0,'VM failed to return')
                        download_vm.finish_monitor(monitor,output,save)
                        download_vm.reset_event(output,expected=True)
                        require('G0Q_RAM_PARK error=110' in (output/'serial.log').read_text(),'no unanswered-request timeout')
                        result=dict(status='guest reset after USB timeout')
                    else:
                        result=capture_guest(proc,manifest,output,args.case)
                finally:
                    if proc.poll() is None: proc.terminate()
                    try: proc.wait(5)
                    except subprocess.TimeoutExpired: proc.kill();proc.wait()
                    if monitor and not monitor['closed']: download_vm.finish_monitor(monitor,output,save)
        finally:
            with ram.open('rb') as f:
                f.seek(BASE);region=f.read(SIZE)
            (output/'region.bin').write_bytes(region)
            ram.unlink()
    if args.case in CASES:
        cable=re.findall(r'^VM_CABLE before=(\d+) after=(\d+)$',(output/'serial.log').read_text(),re.M)
        require(len(cable)==1, 'missing or repeated virtual cable event')
        result.update(compare(result,args.case,region,initial,manifest,output,*map(int,cable[0])))
    result.update(case=args.case,manifest_sha256=digest(args.manifest),kernel_sha256=digest(args.build/'arch/arm64/boot/Image'),
                  initrd_sha256=digest(initrd),region_sha256=digest(output/'region.bin'),device_actions=0)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(args.case,result['status'],result.get('udc_history',{}).get('publication',''))


if __name__=='__main__':
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case',choices=[*CASES,'wrong-key','no-peer'])
    for name in ('manifest','build','dtb','qroot','output'): parser.add_argument('--'+name,type=Path,required=True)
    run(parser.parse_args())
