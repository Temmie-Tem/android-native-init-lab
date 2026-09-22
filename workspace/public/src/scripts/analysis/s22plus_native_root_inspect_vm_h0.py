"""Real ARM64 mount/BLKRO inspection over private, writable regular-file disks."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(ROOT / 'workspace/public/src/scripts/revalidation'),
    str(ROOT / 'workspace/public/src/debian/s22plus_v1/device'),
    str(ROOT / 'workspace/public/src/debian/s22plus_v1')]
import s22plus_native_root_inspect_h0 as producer
import s22plus_native_root_inspect_profile_v1 as profile
import s22plus_native_ext4_profile_v1 as fs
import h0
import vm_install_test as fixture_tools
from s22plus_native_records_v3 import pin, read, require, verify

KERNEL = ROOT / 'workspace/private/outputs/s22plus-debian-bootstrap-h0-20260921-1/kernel-build/arch/arm64/boot/Image'
QEMU = ROOT / 'workspace/private/tools/qemu-arm64-10.2.1/root'


def run(argv, folder, label, *, env=None, timeout=180):
    result = subprocess.run([str(x) for x in argv], capture_output=True, env=env, timeout=timeout)
    (folder / (label + '.stdout')).write_bytes(result.stdout)
    (folder / (label + '.stderr')).write_bytes(result.stderr)
    require(result.returncode == 0, 'fixture command failed: ' + label)
    return result.stdout


def populate(out):
    mapping = Path('/proc/self/uid_map').read_text().split()
    require(os.getuid() == 0 and mapping[:2] != ['0', '0'], 'fixture requires isolated mapped-root namespace')
    artifact, _, _ = profile.prior_inputs()
    binding = read(verify(profile.filesystem.BINDING))
    tree = out / 'tree'; tree.mkdir(mode=0o755)
    run(['tar', '-xf', verify(artifact['rootfs'], maximum=256*1024*1024), '-C', tree], out, 'extract')
    (tree / fs.WITNESS_NAME).write_bytes(fs.WITNESS); (tree / fs.WITNESS_NAME).chmod(0o400)
    marker = f'S22_DEBIAN_INSTALL_V1 {artifact["run_id"]} {artifact["rootfs"]["sha256"]}\n'
    for name in ('.s22-debian-start-v1', '.s22-debian-complete-v1'):
        (tree / name).write_text(marker); (tree / name).chmod(0o400)
    native = out / 'complete.ext4'
    with native.open('xb') as stream: stream.truncate(fs.SIZE_BYTES)
    command = fs.formatter_argv('/usr/sbin/mke2fs', str(native), binding['filesystem_uuid'])
    command[1:1] = ['-F', '-d', str(tree)]
    run(command, out, 'populate', env=dict(os.environ, MKE2FS_CONFIG=binding['configuration']['path']))
    run(['e2fsck', '-fn', native], out, 'populated-check')
    shutil.rmtree(tree)


def make_disk(native, disk, binding):
    require(native.is_file() and native.lstat().st_nlink == 1 and not native.is_symlink(), 'fixture source is indirect')
    gpt = verify(binding['expected_gpt']).read_bytes(); size = 62_305_280 * 4096
    with disk.open('xb') as stream:
        stream.truncate(size); stream.write(gpt[:6*4096]); stream.seek(size-9*4096); stream.write(gpt[6*4096:])
        stream.flush(); os.fsync(stream.fileno())
    fixture_tools.sparse_copy(native, disk, offset=fs.FIRST_LBA*4096)


def setup(out, helper):
    require(not out.exists() and out.resolve() == out and out.is_relative_to(ROOT/'workspace/private/outputs'),
        'fresh direct private VM output required')
    out.mkdir(mode=0o700)
    built = read(helper / 'result.json'); require(built['virt'] is True, 'VM requires an explicitly virtual-board helper')
    artifact, _, _ = profile.prior_inputs(); binding = read(verify(profile.filesystem.BINDING))
    busybox = Path(artifact['rootfs']['path']).parent / 'busybox'
    init = f'''#!/bin/busybox sh
export PATH=/bin
/bin/busybox --install -s /bin
mount -t proc proc /proc || exit 90
mount -t sysfs sysfs /sys || exit 91
mount -t tmpfs -o mode=0755 tmpfs /dev || exit 92
mknod /dev/console c 5 1
mknod /dev/null c 1 3
exec </dev/console >/dev/console 2>&1
mount -t tmpfs -o nodev,nosuid,mode=0700 tmpfs /s22-root-work || exit 93
for n in $(seq 1 100); do [ -e /sys/class/block/vda41/dev ] && break; sleep 0.1; done
printf 'RI_VM_BEGIN\\n'
/s22-root-inspect inspect {built['run_id_hex']}
result=$?
printf 'RI_VM_EXIT status=%s\\n' "$result"
printf 'RI_VM_RO partition=%s disk=%s userdata=%s\\n' "$(cat /sys/class/block/vda41/ro)" "$(cat /sys/class/block/vda/ro)" "$(cat /sys/class/block/vda40/ro)"
poweroff -f
'''.encode()
    entries = [(name, stat.S_IFDIR | 0o755, b'') for name in ('bin','dev','proc','sys','s22-root-work')]
    entries += [('init', stat.S_IFREG|0o750, init), ('bin/busybox', stat.S_IFREG|0o755, busybox.read_bytes()),
        ('s22-root-inspect',stat.S_IFREG|0o500,verify(built['helper']).read_bytes()),
        ('s22-root-inspect.table',stat.S_IFREG|0o400,verify(built['table']).read_bytes())]
    (out/'initramfs.cpio.gz').write_bytes(gzip.compress(h0.newc(entries),mtime=0))
    run(['unshare','--user','--map-auto','--map-root-user','--mount','--pid','--fork','--mount-proc',
        sys.executable,Path(__file__),'populate','--output',out],out,'populate-owner',timeout=240)
    empty = out/'empty'; empty.mkdir(mode=0o700)
    fixture_tools.fixture(empty,binding)
    finish_setup(out, helper)


def finish_setup(out, helper):
    # The unpacked distribution executable has hardlink aliases. Give this H0
    # run its own pinned file without changing any retained tool or alias.
    executable = out/'qemu-system-aarch64'
    shutil.copyfile(QEMU/'usr/bin/qemu-system-aarch64',executable); executable.chmod(0o500)
    (out/'setup.json').write_text(json.dumps(dict(helper=pin(helper/'result.json'), kernel=pin(KERNEL,maximum=128*1024*1024),
        initramfs=pin(out/'initramfs.cpio.gz'), qemu=pin(executable,maximum=128*1024*1024),
        source=pin(Path(__file__)), device_actions=0),indent=2)+'\n')


def debug(native, folder, label, operation):
    return run(['debugfs','-w','-R',operation,native],folder,label)


def check_case(out, name, label=None):
    setup_value = read(out/'setup.json'); built = read(verify(setup_value['helper']))
    folder = out/(label or name); folder.mkdir(mode=0o700)
    source = folder/'producer-source.py'; source.write_bytes(Path(__file__).read_bytes()); source.chmod(0o400)
    native = folder/'native.ext4'
    run(['cp','--reflink=auto','--sparse=always',out/('empty/native.ext4' if name=='empty' else 'complete.ext4'),native],folder,'copy')
    if name == 'partial': debug(native,folder,'partial','rm /.s22-debian-complete-v1')
    if name == 'changed-file':
        bad = folder/'changed'; bad.write_bytes(b'changed\n')
        debug(native,folder,'remove','rm /etc/lab-rootfs-id')
        debug(native,folder,'write',f'write {bad} /etc/lab-rootfs-id')
    if name in ('dirty','orphan','wrong-uuid'):
        with native.open('r+b') as stream:
            stream.seek(1024); superblock = bytearray(stream.read(1024))
            if name == 'dirty': superblock[0x60] |= 4
            elif name == 'orphan': struct.pack_into('<I',superblock,0xe8,2)
            else: superblock[0x68] ^= 1
            struct.pack_into('<I',superblock,0x3fc,fs.crc32c(superblock[:0x3fc]))
            stream.seek(1024); stream.write(superblock); stream.flush(); os.fsync(stream.fileno())
    if name == 'directory-checksum':
        block_text = run(['debugfs','-R','blocks /etc',native],folder,'directory-blocks').decode().strip()
        numbers = block_text.split(); require(numbers and all(n.isdigit() for n in numbers), 'fixture directory block list differs')
        offset = int(numbers[0])*4096+4095
        with native.open('r+b') as stream:
            stream.seek(offset); old=stream.read(1); stream.seek(offset); stream.write(bytes([old[0]^1]))
            stream.flush(); os.fsync(stream.fileno())
    binding = read(verify(profile.filesystem.BINDING)); disk = folder/'disk.img'; make_disk(native,disk,binding)
    if name == 'gpt-byte':
        with disk.open('r+b') as stream:
            stream.seek(400); byte=stream.read(1); stream.seek(400); stream.write(bytes([byte[0]^1])); stream.flush(); os.fsync(stream.fileno())
    before=fixture_tools.sparse_digest(disk)
    command=[verify(setup_value['qemu'],maximum=128*1024*1024),'-machine','virt','-cpu','cortex-a76','-smp','2','-m','768','-nic','none',
        '-nographic','-monitor','none','-no-reboot','-kernel',KERNEL,'-initrd',out/'initramfs.cpio.gz',
        '-append','console=ttyAMA0 rdinit=/init panic=-1',
        '-drive',f'if=none,id=root,file={disk},format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    (folder/'command.json').write_text(json.dumps([str(x) for x in command])+'\n')
    raw=run(command,folder,'serial',env=dict(os.environ,LD_LIBRARY_PATH=str(QEMU/'usr/lib/x86_64-linux-gnu')),timeout=300)
    after=fixture_tools.sparse_digest(disk); require(before==after,'read-only inspector modified the writable backing disk')
    text=raw.replace(b'\r\n',b'\n')
    require(text.count(b'RI_VM_BEGIN\n')==1 and b'reboot: Power down' in text,'VM observation or poweroff boundary missing')
    stdout=b'\n'.join(line for line in text.splitlines() if line.startswith(b'RI1_'))+b'\n'
    status=re.findall(rb'^RI_VM_EXIT status=([0-9]+)$',text,re.M); require(len(status)==1,'VM helper exit missing')
    ro=re.findall(rb'^RI_VM_RO partition=([01]) disk=([01]) userdata=([01])$',text,re.M)
    require(len(ro)==1 and ro[0][1:]==(b'0',b'0'),'block RO leaked beyond native partition')
    expected_ro=b'0' if name=='gpt-byte' else b'1'
    require(ro[0][0]==expected_ro,'partition block protection differs')
    if name in ('wrong-uuid','gpt-byte','directory-checksum'):
        require(status[0]!=b'0' and b'RI1_RESULT complete=0 ' in stdout,'negative fixture did not reject')
        if name=='directory-checksum':
            require(b'RI1_MOUNT readonly=1 ' in stdout and b'checksum' in text.lower(),
                'directory checksum failure did not exercise actual protected ext4 reads')
        result=dict(status='PASS_REJECTED_WITH_DISK_UNCHANGED')
    else:
        require(status[0]==b'0','positive inspection did not complete')
        result=profile.decode(stdout,b'',dict(table_count=built['table_count'],boot_count=built['boot_count'],max_hashed_bytes=512*1024*1024))
        wanted={'complete':'COMPLETE_RECORD_BOOT_INPUTS_MATCH','empty':'NO_INSTALLATION_RECORDS',
            'partial':'INCOMPLETE_INSTALLATION_RECORD','changed-file':'COMPLETE_RECORD_FILES_DIFFER',
            'dirty':'MOUNT_SKIPPED_UNCLEAN','orphan':'MOUNT_SKIPPED_UNCLEAN'}[name]
        require(result['root_state']==wanted,'fixture state was misclassified')
        if name=='complete': require(result['comparison']['matched']==built['table_count'],'complete archive comparison differs')
    value=dict(case=name,scope='REAL_ARM64_VIRT_ONLY',before=before,after=after,unchanged=True,
        helper=setup_value['helper'],producer=pin(source),serial=pin(folder/'serial.stdout'),result=result,device_actions=0)
    (folder/'result.json').write_text(json.dumps(value,indent=2)+'\n')
    print(name,result['status'],flush=True)
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('populate','setup','run'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--helper',type=Path)
    parser.add_argument('--label')
    parser.add_argument('--case',choices=('complete','empty','partial','changed-file','dirty','orphan','wrong-uuid','gpt-byte','directory-checksum'))
    args=parser.parse_args(); out=args.output.absolute()
    if args.command=='populate': populate(out)
    elif args.command=='setup': setup(out,args.helper.absolute())
    else: check_case(out,args.case,args.label)


if __name__=='__main__': main()
