"""Offline regular-file root faults, exercised by the actual ARM64 admission."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import subprocess

import autoboot_vm as automatic
import h0
import s22plus_debian_reboot_v1 as spec
import s22plus_debian_cron_v1 as cron_spec
import s22plus_debian_cron_config_v1 as config_spec
import s22plus_debian_package_v1 as package_spec
import s22plus_debian_apt_v1 as apt_spec
from s22plus_debian_reboot_qualification_v1 import rejection
from s22plus_native_records_v3 import pin,publish,read,require,verify

CASES=spec.ROOT_CASES
SECOND=tuple(c for c in CASES if c.startswith('prior-') or c.startswith('second-') or c=='third-start')+('second-root-control',)


def debug(native,out,label,command):
    value=automatic.vm.fixture.debug(native,out,label,command)
    diagnostic=(out/(label+'.stderr')).read_bytes()
    header=b'debugfs 1.47.2 (1-Jan-2025)\n'
    allowed=[header]
    if command.startswith('rm '):allowed.append(header+b'rm: File not found by ext2_lookup while trying to resolve filename\n')
    if command.startswith('dump '):
        path=command.split()[1]
        allowed.append(header+path.encode()+b': File not found by ext2_lookup \n')
    require(diagnostic in allowed,'VM fixture command has unexpected diagnostics: '+label)
    return value


def put(native,out,label,path,body,mode=0o100644,gid=0):
    source=out/(label+'.bin');source.write_bytes(body)
    debug(native,out,label+'-remove',f'rm /{path}')
    debug(native,out,label+'-write',f'write {source} /{path}')
    debug(native,out,label+'-mode',f'set_inode_field /{path} mode 0{mode:o}')
    debug(native,out,label+'-gid',f'set_inode_field /{path} gid {gid}')
    return pin(source)


def marker_body():
    result=read(verify(spec.P457_RETRIEVAL));terminal=read(verify(result['writer_terminal']))
    raw=automatic.raw;capture=raw.load_handle(verify(terminal['debian_autoboot']['ssh_health']['capture']))
    return re.findall(rb'^boot_id=([0-9a-f-]{36})$',raw.read_stdout(capture,maximum=65536),re.M)[0]+b'\n'


def boundaries(native,out):
    """Positive optional files and original counter ceiling, synthetic only."""
    marker=spec.shutdown_marker();body=marker_body()
    rows={marker['path']:put(native,out,'optional-marker',marker['path'],body)}
    for i,path in enumerate(spec.ROTATIONS):
        # Size limits are metadata admission bounds; gzip contents are mutable.
        rows[path]=put(native,out,f'rotation-{i}',path,b'log\n',0o100640,4)
    rows['var/lib/lab/boot-count']=put(native,out,'ceiling-count','var/lib/lab/boot-count',b'99998\n')
    publish(out/'boundary-fixture.json',dict(kind='H0_SYNTHETIC',files=rows,device_actions=0))


def run(out,build,helper,positive,case,clean=None):
    require(case in CASES+cron_spec.ROOT_CASES+config_spec.ROOT_CASES+package_spec.PACKAGE_ROOT_CASES+apt_spec.APT_ROOT_CASES+('clean-error-unmount','second-root-control'),'unselected reboot root fault')
    selected=automatic.prepare(out,build,helper,'changed-receipt' if case=='changed-current-receipt' else 'normal')
    config=automatic.build_api.profile.cron_config_selected(selected)
    native=out/'native.ext4';fixture=automatic.vm.fixture
    provenance='INITIAL_ROOT'
    if case=='clean-error-retry':
        require(clean is not None,'retry needs the original counted error-unmount fixture')
        h0.run(['cp','--reflink=auto','--sparse=always',clean/'native-after.ext4',native],out/'copy-error.log')
        provenance='ORIGINAL_COUNTED_ERROR_UNMOUNT'
    if case in SECOND or case in cron_spec.ROOT_CASES and case!='cron-existing-first' or case.startswith(('config-second-','package-second-','apt-second-')):
        source=positive/('native-first.ext4' if config and case!='third-start' else 'native-after.ext4')
        if config and case!='third-start':
            snap=read(positive/'first-root.json')
            require(source.is_file() and not source.is_symlink() and snap['path']==str(source) and
                snap['origin']=='ACTUAL_FIRST_KERNEL_REBOOT_EXIT' and
                fixture.fixture_tools.sparse_digest(source)==snap['sparse_sha256'],'first-boot root snapshot changed')
        h0.run(['cp','--reflink=auto','--sparse=always',source,native],out/'copy-final.log')
        provenance='ACTUAL_FIRST_KERNEL_REBOOT_ROOT' if config and case!='third-start' else 'RECONSTRUCTED_SECOND_ROOT_FROM_CLOSED_VM_ONLY'
        if case!='third-start' and not config:
            for kind,path in spec.paths(selected['run_id'],2).items():debug(native,out,'remove-second-'+kind,f'rm /{path}')
            debug(native,out,'second-count',f'ssv mnt_count {selected["reboot"]["initial_mount_count"]+2}')
            first=read(positive/'result.json')['boots'][0]['ssh_120_seconds']['last']['health']['boot_count']
            put(native,out,'first-boot-count','var/lib/lab/boot-count',(str(first)+'\n').encode())
    if case in ('baseline-mismatch','second-count-mismatch'):
        count=selected['reboot']['initial_mount_count']+(3 if case.startswith('second') else 1)
        debug(native,out,'mismatch',f'ssv mnt_count {count}')
    elif case=='dirty':debug(native,out,'dirty','ssv state 0')
    elif case=='changed-p456-runtime':
        row=spec.history()[1];body=verify(row['source']).read_bytes()
        put(native,out,'changed-p456',row['path'],body[:-1]+bytes([body[-1]^1]),0o100600)
    elif case in ('foreign-file','existing-early','existing-runtime','second-file-exists'):
        if case=='foreign-file':path='etc/unexpected-reboot'
        elif case=='second-file-exists':path=spec.paths(selected['run_id'],2)['early']
        else:path=spec.paths(selected['run_id'],1)[case.removeprefix('existing-')]
        put(native,out,'unexpected',path,b'UNEXPECTED\n',0o100600)
    elif case.startswith('rotation-'):
        path='var/log/dmesg.5.gz' if case=='rotation-extra' else 'var/log/dmesg.4.gz'
        put(native,out,'rotation',path,b'x'*(spec.ROTATION_MAXIMUM+1) if case=='rotation-size' else b'log\n',
            0o100644 if case=='rotation-mode' else 0o100640,4)
        if case=='rotation-link':
            debug(native,out,'rotation-alias','ln /var/log/dmesg.4.gz /var/log/dmesg.3.gz')
            debug(native,out,'rotation-link',f'set_inode_field /{path} links_count 2')
    elif case.startswith('marker-'):
        put(native,out,'marker','var/lib/lab/shutdown-start',marker_body() if case=='marker-mode' else b'0'*36+b'\n',0o100600 if case=='marker-mode' else 0o100644)
    elif case=='boot-count-overflow':put(native,out,'count','var/lib/lab/boot-count',b'99999\n')
    elif case.startswith('prior-'):
        kind='early' if case=='prior-early-missing' else 'runtime';path=spec.paths(selected['run_id'],1)[kind]
        if case=='prior-early-missing':debug(native,out,'prior-missing',f'rm /{path}')
        elif case=='prior-runtime-mode':debug(native,out,'prior-mode',f'set_inode_field /{path} mode 0100644')
        else:
            original=(positive/'boot-1/runtime.bin').read_bytes()
            body=original[:-128] if case.endswith('incomplete') else original[:-1]+bytes([original[-1]^1])
            put(native,out,'prior-mutated',path,body,0o100600)
    if case in cron_spec.ROOT_CASES:
        require(automatic.build_api.profile.cron_selected(selected),'unselected cron fault')
        path=cron_spec.path(selected['run_id']);body=(positive/'boot-1/cron.bin').read_bytes()
        if case=='cron-missing':debug(native,out,'cron-missing',f'rm /{path}')
        elif case=='cron-symlink':
            debug(native,out,'cron-remove',f'rm /{path}')
            debug(native,out,'cron-symlink',f'symlink /{path} /etc/passwd')
        else:
            if case=='cron-changed':body=body[:-1]+bytes([body[-1]^1])
            if case=='cron-oversized':body+=b'X'
            if case=='cron-wrong-boot':
                import hmac
                value=bytearray(body);value[32]^=1
                value[480:]=hmac.digest(verify(selected['key']).read_bytes(),cron_spec.DOMAIN+b'\x01'+value[:480],'sha256');body=bytes(value)
            put(native,out,'cron-fault',path,body,0o100644 if case=='cron-mode' else 0o100600)
            if case=='cron-linked':
                debug(native,out,'cron-alias',f'ln /{path} /var/lib/lab/s22-cron-alias')
                debug(native,out,'cron-linked',f'set_inode_field /{path} links_count 2')
    if case in config_spec.ROOT_CASES:
        require(config,'unselected persistent configuration root fault')
        path=config_spec.config_path(selected['run_id']);body=config_spec.schedule(selected['run_id'])
        if case.endswith('-report'):
            put(native,out,'unexpected-report',config_spec.path(selected['run_id']),b'PARTIAL',0o100600)
        elif case=='config-second-missing':debug(native,out,'config-missing',f'rm /{path}')
        elif case=='config-second-symlink':
            debug(native,out,'config-remove',f'rm /{path}')
            debug(native,out,'config-symlink',f'symlink /{path} /etc/passwd')
        elif case=='config-second-mode':debug(native,out,'config-mode',f'set_inode_field /{path} mode 0100600')
        elif case=='config-second-linked':
            debug(native,out,'config-alias',f'ln /{path} /etc/cron.d/unexpected-alias')
            debug(native,out,'config-linked',f'set_inode_field /{path} links_count 2')
        elif case in ('config-second-mtime','config-second-ctime'):
            field=case.rsplit('-',1)[1]
            debug(native,out,'config-time',f'set_inode_field /{path} {field} 1')
        elif case=='config-second-foreign':put(native,out,'foreign-config','etc/cron.d/unselected',body)
        else:
            if case=='config-second-changed':body=body[:-2]+b'X\n'
            if case=='config-second-partial':body=body[:31]
            put(native,out,'config-mutated',path,body)
    if case in package_spec.PACKAGE_ROOT_CASES:
        require(automatic.build_api.profile.package_selected(selected),'unselected package root fault')
        apt=automatic.build_api.profile.apt_selected(selected)
        package='tree' if apt else 'hello';path='usr/bin/'+package
        if case=='package-first-existing':put(native,out,'package-existing',path,b'UNEXPECTED',0o100755)
        elif case in ('package-first-remnant','package-second-remnant'):
            put(native,out,'package-remnant',path+'.dpkg-tmp',b'UNEXPECTED',0o100755)
        elif case=='package-second-missing':debug(native,out,'package-missing',f'rm /{path}')
        elif case=='package-second-linked':
            debug(native,out,'package-alias',f'ln /{path} /usr/bin/{package}-unexpected-alias')
            debug(native,out,'package-linked',f'set_inode_field /{path} links_count 2')
        elif case=='package-second-mode':debug(native,out,'package-mode',f'set_inode_field /{path} mode 0100600')
        elif case=='package-second-foreign':put(native,out,'package-foreign','etc/unexpected-package',b'UNEXPECTED')
        elif case=='package-second-no-install-proof':
            import struct
            import s22plus_debian_evidence_v1 as evidence
            path=spec.paths(selected['run_id'],1)['runtime'];original=(positive/'boot-1/runtime.bin').read_bytes()
            body=bytearray(original[:256]);prior=body[224:256];count=0;key=verify(selected['key']).read_bytes()
            for at in range(256,len(original),128):
                record=bytearray(original[at:at+128])
                if int.from_bytes(record[12:16],'little') in (13,14):continue
                struct.pack_into('<I',record,8,count);record[64:96]=prior
                prior=evidence.tag(key,record[:96],autoboot=True,reboot=True,cron_config=True,download=True,package=True,apt=apt)
                record[96:]=prior;body+=record;count+=1
            put(native,out,'package-proof',path,bytes(body),0o100600)
        else:
            if case in ('package-first-status','package-second-status'):path='var/lib/dpkg/status'
            elif case=='package-second-status-old':path='var/lib/dpkg/status-old'
            elif case=='package-second-info':path='var/lib/dpkg/info/'+package+'.list'
            target=out/'package-original.bin';debug(native,out,'package-read',f'dump /{path} {target}')
            body=target.read_bytes();require(body,'package fixture is empty')
            put(native,out,'package-changed',path,body[:-1]+bytes([body[-1]^1]),0o100755 if path=='usr/bin/'+package else 0o100644)
    if case in apt_spec.APT_ROOT_CASES:
        require(automatic.build_api.profile.apt_selected(selected),'unselected retained package fault')
        if case=='apt-first-retained-hello-changed':put(native,out,'retained-hello','usr/bin/hello',b'CHANGED',0o100755)
        else:debug(native,out,'retained-hello-missing','rm /usr/bin/hello')
    (out/'disk.img').unlink()
    fixture.make_disk(native,out/'disk.img',read(verify(fixture.profile.filesystem.BINDING)))
    before=fixture.fixture_tools.sparse_digest(out/'disk.img');outside=automatic.lifecycle.outside_native(out/'disk.img')
    command=[fixture.QEMU/'usr/bin/qemu-system-aarch64','-machine','virt','-cpu','cortex-a76','-smp','8','-m','768',
        '-nic','none','-display','none','-monitor','none','-serial',f'file:{out}/serial.log','-no-reboot',
        '-kernel',h0.regular(automatic.vm.KERNEL),'-initrd',out/'initramfs.cpio.gz','-append',automatic.kernel_command_line(selected),
        '-drive',f'if=none,id=root,file={out}/disk.img,format=raw',
        '-device','virtio-blk-device,drive=root,logical_block_size=4096,physical_block_size=4096']
    publish(out/'command.json',list(map(str,command)))
    with (out/'qemu.log').open('xb') as log:
        result=subprocess.run(list(map(str,command)),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
            timeout=120,env=dict(os.environ,LD_LIBRARY_PATH=str(fixture.QEMU/'usr/lib/x86_64-linux-gnu')))
    serial=(out/'serial.log').read_bytes();after=fixture.fixture_tools.sparse_digest(out/'disk.img')
    require(result.returncode==0 and (b'AUTO_VM_EARLY_STOP' in serial or case=='changed-current-receipt') and b'reboot: Power down' in serial and
        automatic.lifecycle.outside_native(out/'disk.img')==outside,'root fault did not stop in isolation')
    extra={}
    if case in ('clean-error-unmount','second-root-control'):
        require(b'RI1_RESULT complete=1' in serial and b'FILE_PILOT result=REJECTED error=5 records=0 bytes=0' in serial and
            before!=after,'counted error-unmount was not exercised')
        native=automatic.file_log_vm.extract_native(out)
        with native.open('rb') as stream:block=stream.read(4096)
        projected=automatic.build_api.baseline.block_projection(block)
        require(projected['initial_mount_count']==selected['reboot']['initial_mount_count']+(3 if case=='second-root-control' else 1),
            'error-unmount did not consume one clean RW setup')
        (out/'final-block.bin').write_bytes(block)
        for phase in ((2,) if case=='second-root-control' else (1,2)):
            for kind,path in spec.paths(selected['run_id'],phase).items():
                target=out/f'absent-{phase}-{kind}'
                debug(native,out,f'absence-{phase}-{kind}',f'dump /{path} {target}')
                require(not target.exists(),'error before file creation left a current file')
        extra=dict(final_superblock=projected,final_block=pin(out/'final-block.bin'),current_files_absent=True)
    elif case=='changed-current-receipt':
        require(b'AUTO_VM_RECEIPT_MUTATED' in serial and before!=after,'current RAM receipt fault was not exercised')
        native=automatic.file_log_vm.extract_native(out)
        with native.open('rb') as stream:block=stream.read(4096)
        projected=automatic.build_api.baseline.block_projection(block)
        require(projected['initial_mount_count']==selected['reboot']['initial_mount_count']+1,
            'changed receipt advanced beyond the early lifetime')
        (out/'final-block.bin').write_bytes(block)
        for kind,path in spec.paths(selected['run_id'],1).items():
            target=out/('current-'+kind)
            debug(native,out,'current-'+kind,f'dump /{path} {target}')
            require(target.exists() is (kind=='early'),'changed receipt reached installed write or lost early record')
        extra=dict(final_superblock=projected,final_block=pin(out/'final-block.bin'),runtime_absent=True)
    else:require(rejection(serial,case) and before==after,'root rejection changed storage')
    value=dict(status='PASS',case=case,scope='H0_REGULAR_FILE_PRODUCTION_ROOT_ADMISSION',device_actions=0,
        build=pin(build/'build.json'),helper=pin(helper/'request.json'),setup=pin(out/'setup.json'),
        source=pin(Path(__file__)),positive=pin(positive/'result.json'),fixture=provenance,
        disk_before=before,disk_after=after,serial=pin(out/'serial.log',maximum=4*1024**2),
        outside_native_unchanged=True,physical_readiness=False,**extra)
    if case=='clean-error-retry':value['clean_error']=pin(clean/'result.json')
    publish(out/'result.json',value);print('PASS '+case,flush=True);return value


def suite(out,build,helper,positive):
    out=h0.private(out,fresh=True)
    built=read(build/'build.json');builder=automatic.build_api
    fault=out/'clean-helper'
    generated=builder.prepare(fault,Path(built['inputs']),Path(built['packages']),
        run=built['run_id'],key=verify(built['key']).read_bytes(),virt=True,transition=True,
        transition_fault='reboot-clean-error',rcs=True,watchdog=True,idle_policy='cpuidle-off',
        single_cpu=True,post_p447=True,script_channel=True,minimal=True,reboot=built['reboot_baseline'],cron=automatic.build_api.profile.cron_selected(built))
    require(generated['source_inputs']==built['source_inputs'] and
        generated['hook']['sha256']==read(helper/'request.json')['hook']['sha256'],
        'fault helper sources or unchanged prior runtime producer differ')
    clean=run(out/'clean-error-unmount',build,fault,positive,'clean-error-unmount')
    second=run(out/'second-root-control',build,fault,positive,'second-root-control')
    def single(case):
        try:return run(out/case,build,fault if case=='clean-error-retry' else helper,positive,case,out/'clean-error-unmount')
        except Exception as error:
            publish(out/(case+'-failure.json'),dict(error_type=type(error).__name__,message=str(error),device_actions=0));raise
    cron=builder.profile.cron_selected(built)
    with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(single,CASES+(builder.profile.cron_variant(cron).ROOT_CASES if cron else ())))
    value=dict(status='PASS',cases=[clean,second,*rows],device_actions=0);publish(out/'result.json',value);return value
