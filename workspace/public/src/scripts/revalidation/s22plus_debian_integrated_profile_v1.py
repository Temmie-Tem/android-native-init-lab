"""Exact Debian-owned initial-PID1 to installed-services capability inputs."""
import hashlib
import gzip
import io
import os
from pathlib import Path
import re
import stat

import device_action_raw_capture_v1 as raw
import s22plus_debian_access_v1 as access
import s22plus_debian_early_profile_v1 as early
import s22plus_debian_handoff_profile_v1 as handoff
import s22plus_debian_integrated_protocol_v1 as protocol
import s22plus_boot_only_f1_transport as transport
import s22plus_debian_profile_v1 as carrier
from s22plus_native_records_v3 import private_path,read,require,verify

ROOT=early.ROOT
SCHEMA='s22plus-debian-integrated-v1'
PROFILE='debian-integrated-v1'
OPERATION=SELECTION='debian-integrated'
POLICY='docs/operations/S22PLUS_DEBIAN_INTEGRATED_V1.md'
CASES=('normal','module-byte','provider-missing','parent-byte','bad-auth','ufs-failure','fd-leak','dirty','mismatch')
prior_inputs=early.prior_inputs


class Profile:
    RESULT_KEY='debian_integrated'
    MUTATES=True


def blob(receipt,maximum):
    """Raw VM streams may be empty; structured-record rules stay unchanged."""
    require(set(receipt)=={'path','size','sha256'} and type(receipt['size']) is int and
        0<=receipt['size']<=maximum,'integrated raw receipt bound differs')
    path=private_path(ROOT,Path(receipt['path']));before=path.lstat()
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        opened=os.fstat(descriptor)
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink==1 and
            opened.st_size==receipt['size'] and (opened.st_dev,opened.st_ino)==(before.st_dev,before.st_ino),
            'integrated VM raw file identity differs')
        data=bytearray()
        while len(data)<=maximum:
            part=os.read(descriptor,min(65536,maximum+1-len(data)))
            if not part:break
            data.extend(part)
        after=os.fstat(descriptor)
        fields=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        require(all(getattr(after,f)==getattr(opened,f) for f in fields) and len(data)==receipt['size'] and
            hashlib.sha256(data).hexdigest()==receipt['sha256'],'integrated raw file changed')
        return bytes(data)
    finally:os.close(descriptor)


def vm_results(tested,built,key):
    require(tested['status']=='PASS' and tested['device_actions']==0 and
        tuple(row['case'] for row in tested['cases'])==CASES,'integrated VM corpus differs')
    sources={row['path']:row['sha256'] for row in built['source_inputs']}
    virtual_sources={row['path']:row['sha256'] for row in tested['source_inputs']}
    require(all(virtual_sources.get(path)==digest for path,digest in sources.items()),
        'VM does not cover the physical source closure')
    for row in tested['cases']:
        require(row['status']=='PASS' and row['device_actions']==0 and row['outside_native_unchanged'] is True and
            row['scope']=='REAL_DEBIAN_INITRAMFS_TO_SYSVINIT_SSH_WITH_SAMSUNG_HARDWARE_SUBSTITUTIONS',
            'integrated VM physical scope was promoted')
        helper=read(verify(row['virtual_helper']));selection=read(verify(helper['handoff']))
        require(helper['virtual'] is True and helper['run_id']==built['run_id'] and helper['modules']==built['modules'] and
            helper['measured']['shell_sha256']==built['measured']['shell_sha256'] and
            helper['measured']['init_sha256']==built['measured']['init_sha256'] and
            all({r['path']:r['sha256'] for r in helper['source_inputs']}.get(path)==digest for path,digest in sources.items()),
            'virtual producer does not join the physical candidate')
        rx=blob(row['rx'],protocol.MAXIMUM);tx=blob(row['tx'],224)
        verify(row['serial'],maximum=4*1024**2)
        if row['case']=='normal':
            proof=protocol.replay(rx,tx,key=key,run=bytes.fromhex(built['run_id']),expected=helper['measured'],
                module_names=[m['runtime_name'] for m in helper['modules']],selection=selection)
            require(proof==row['proof'] and row['ssh_health']['boot_id_sha256']==proof['kernel_boot_proof'] and
                row['ssh_health']['status']=='PASS_INSTALLED_DEBIAN_SSH' and row['shutdown']['request_accepted'] is True and
                row['filesystem']['clean_ext4'] is True and row['filesystem']['home_view_readable'] is True and
                row['filesystem']['boot_count_durability']=='CONTROLLED_SHUTDOWN_VERIFIED' and
                row['durable'] is not None and row['disk_before']!=row['disk_after'],
                'integrated complete lifecycle proof differs')
            root,_,previous=prior_inputs()
            plan=dict(root_run_id=root['run_id'],candidate=dict(namespace=built['namespace'],
                version=built['version'],run_id=built['run_id']))
            require(access.health_projection(raw.load_handle(verify(row['ssh_health']['capture'])),plan,
                boot_sha256=proof['kernel_boot_proof'])==row['ssh_health'] and
                access.shutdown_projection(raw.load_handle(verify(row['shutdown']['dispatch_capture'])),
                    previous['link']['ssh_address'])==row['shutdown'],'integrated SSH raw proof differs')
            durable=read(verify(row['durable']))
            expected=dict(run_id_hex=built['run_id'],boot=proof['kernel_boot_proof'],
                nonce_sha256=proof['nonce_sha256'],key_sha256=hashlib.sha256(key).hexdigest(),
                init_sha256=selection['installed_init']['sha256'],hook_sha256=selection['assets']['hook']['sha256'],
                root_device=proof['debian_handoff']['root_transition']['proof']['root_device'])
            capture=raw.load_handle(verify(durable['source']))
            require(capture.returncode==0 and not capture.timed_out and not capture.output_exceeded and
                capture.producer_error_type is None and
                raw.read_stderr(capture,maximum=4096)==b'debugfs 1.47.2 (1-Jan-2025)\n' and
                durable['expected']==expected and durable['device_actions']==0 and
                durable['proof']==handoff.evidence.decode(raw.read_stdout(capture,maximum=handoff.evidence.MAXIMUM),key,expected) and
                durable['proof']['local_runtime_proved'] is True and durable['proof']['release_authenticated'] is True and
                durable['proof']['report_disabled'] is False,'integrated durable raw evidence differs')
        else:
            require(row['disk_before']==row['disk_after'] and row['ssh_health'] is None and row['shutdown'] is None and
                row['filesystem'] is None and row['durable'] is None,'negative VM has a write or installed access')
            if row['case'] in ('module-byte','provider-missing','parent-byte','bad-auth'):
                require(not rx,'pre-auth negative produced authenticated bytes')
                empty=protocol.Records(key,bytes.fromhex(built['run_id']),b'n'*32,helper['measured'],
                    [m['runtime_name'] for m in helper['modules']],selection).projection()
                require(row['proof']==empty,'pre-auth negative was promoted to execution proof')
                if row['case']=='bad-auth':
                    frame=protocol.frames.decode_frame(tx)
                    require(len(tx)==80 and frame.frame_type==protocol.early.REQUEST and frame.sequence==1 and
                        len(frame.payload)==64 and
                        tx!=protocol.request(key,bytes.fromhex(built['run_id']),frame.payload[:32]),
                        'bad-auth must have valid framing and a rejected tag')
                else:require(not tx,'pre-wire rejection unexpectedly received a host start')
            else:
                proof=protocol.replay(rx,tx,key=key,run=bytes.fromhex(built['run_id']),expected=helper['measured'],
                    module_names=[m['runtime_name'] for m in helper['modules']],selection=selection,complete=False)
                selected=proof['debian_handoff']
                extra={'protocol_complete','diagnostic_error','kernel_boot_proof','nonce_sha256','raw_prefix_bytes',
                    'rx_sha256','tx_sha256'}
                require(row['proof']=={k:v for k,v in proof.items() if k not in extra},
                    'negative VM structured proof differs from its raw prefix')
                require(proof['initial_parent'] is not None and (proof['ufs'] is None if row['case']=='ufs-failure'
                    else selected is not None and selected['stop'] is not None and selected['init_proof'] is None),
                    'negative VM advanced past its expected boundary')
    return tested


def image_binding(image):
    require(set(image)=={'schema','namespace','version','run_id_hex','profile','ap','member','key','runtime_sources',
        'integrated_boot','gpt','android_return','qualification'} and image['schema']=='s22plus-native-image-v3' and
        image['profile']==PROFILE and re.fullmatch(r'p[0-9]{3,6}',image['namespace']) and
        re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.]+)?',image['version']) and
        re.fullmatch('[0-9a-f]{32}',image['run_id_hex']),'integrated image identity differs')
    key=verify(image['key'],maximum=32).read_bytes();require(len(key)==32,'integrated key length differs')
    qualified=read(verify(image['qualification']));artifact=read(verify(image['integrated_boot']))
    require(set(qualified)=={'schema','status','image','vm','device_actions'} and
        qualified['schema']==SCHEMA+'-qualification' and qualified['status']=='PASS_H0_ARTIFACT_AND_VM' and
        qualified['image']=={k:v for k,v in image.items() if k!='qualification'} and qualified['device_actions']==0,
        'integrated qualification binding differs')
    require(set(artifact)=={'schema','namespace','version','run_id','ap','member','key','build','expected','runtime_sources',
        'module_names','ab_identical','active','boot','ramdisk_sha256','inventory','vm','handoff','device_actions'} and
        artifact['schema']==SCHEMA+'-artifact' and artifact['ab_identical'] is True and artifact['active'] is False and
        artifact['device_actions']==0 and artifact['vm']==qualified['vm'],'integrated artifact scope differs')
    for a,b in (('namespace','namespace'),('version','version'),('run_id','run_id_hex'),('ap','ap'),('member','member'),
                ('key','key'),('runtime_sources','runtime_sources')):
        require(artifact[a]==image[b],'integrated artifact/image join differs')
    built=read(verify(artifact['build']));inventory=read(verify(artifact['inventory']))
    require(built['schema']=='s22plus-debian-integrated-h0-v1' and built['virtual'] is False and
        built['ab_identical'] is True and built['active'] is False and built['device_actions']==0 and
        built['namespace']==image['namespace'] and built['version']==image['version'] and
        built['profile']==PROFILE and built['run_id']==image['run_id_hex'] and built['measured']==artifact['expected'] and
        built['handoff']==artifact['handoff'] and built['platform_count']==74 and
        built['provider_barrier_after']=='qcom_spmi_pmic','integrated physical producer differs')
    expected=[early.LOGGER]+inventory['modules']
    require(inventory['platform_count']==73 and len(expected)==82 and built['modules']==expected and
        artifact['module_names']==[m['runtime_name'] for m in expected],'integrated module declaration differs')
    require({r['path']:r['sha256'] for r in built['source_inputs']}==
        {k:v['sha256'] for k,v in image['runtime_sources'].items()},'integrated source closure differs')
    for field in ('helper','parent_measure','entry'):verify(built[field],maximum=8*1024**2)
    for receipt in built['headers'].values():verify(receipt)
    verify(built['initramfs'],maximum=32*1024**2)
    require(set(artifact['expected'])=={'shell_sha256','init_sha256','helper_sha256'} and
        all(re.fullmatch('[0-9a-f]{64}',v) for v in artifact['expected'].values()) and
        built['helper']['sha256']==artifact['expected']['helper_sha256'],'integrated measurements differ')
    selected=read(verify(artifact['handoff']))
    require(selected['virt'] is False and selected['observer_revision']==4 and selected['run_id_hex']==image['run_id_hex'] and
        selected['key_sha256']==hashlib.sha256(key).hexdigest() and selected['ab_identical'] is True and
        selected['debian']==dict(namespace=image['namespace'],version=image['version'],fault=0) and
        selected['fault']==selected['checker_fault']==selected['debian']['fault']==0 and
        selected['durable_evidence']==handoff.evidence.binding(image['run_id_hex']),
        'integrated installed helper scope differs')
    init,assets=handoff.payloads()
    require(selected['installed_init']==dict(size=len(init),sha256=hashlib.sha256(init).hexdigest()) and
        selected['busybox']['sha256']==handoff.switch.BUSYBOX_SHA256 and selected['busybox']['size']==1975064 and
        selected['checker']==handoff.staged.execution_binding()['checker'] and
        set(selected['assets'])=={'hook','inittab','qualify','defer-usb','crontab','usb'},
        'integrated installed root/checker/assets differ')
    for name,data in assets.items():require(verify(selected['assets'][name]).read_bytes()==data,'integrated RAM overlay differs')
    for name in ('witness','busybox','checker','table'):verify(selected[name],maximum=8*1024**2)
    for receipt in selected['assets'].values():verify(receipt,maximum=8*1024**2)
    tested=read(verify(artifact['vm']))
    require(tested['build_sha256']==artifact['build']['sha256'] and
        all(row['build']==artifact['build'] for row in tested['cases']),'integrated VM selected another image')
    vm_results(tested,built,key)
    return artifact


def archive_binding(image,artifact):
    """Connect actual AP bytes to the qualified boot, initramfs and carrier."""
    built=read(verify(artifact['build']))
    with transport.pin_boot_only_ap(Path(image['ap']['path']),label='integrated candidate',
            expected_size=image['ap']['size'],expected_sha256=image['ap']['sha256']) as pinned:
        member=transport.read_boot_only_member(pinned,label='integrated candidate',maximum=128*1024**2)
    require(image['member']==dict(name='boot.img.lz4',size=len(member),sha256=hashlib.sha256(member).hexdigest()),
        'integrated AP member differs')
    boot=transport.boot_verify
    actual=boot.decompress_lz4_stream_python(member,maximum=128*1024**2)
    require(actual==verify(artifact['boot'],maximum=128*1024**2).read_bytes(),
        'integrated AP is not the qualified boot image')
    parsed=boot.parse_boot_v4(actual)
    compressed=verify(built['initramfs'],maximum=32*1024**2).read_bytes()
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:ramdisk=stream.read(128*1024**2+1)
    require(len(ramdisk)<=128*1024**2 and hashlib.sha256(ramdisk).hexdigest()==artifact['ramdisk_sha256'] and
        boot.decompress_lz4_stream_python(parsed.ramdisk,maximum=128*1024**2)==ramdisk,
        'integrated packaged ramdisk differs from the qualified initramfs')
    retained=read(verify(carrier.RETAINED_RESULT))['candidate']['a']['boot_img']
    original=verify(dict(path=str(carrier.RETAINED/'candidate-a/boot.img'),**retained),maximum=128*1024**2).read_bytes()
    if built['profile']=='debian-autoboot-v1':
        import s22plus_debian_autoboot_profile_v1 as automatic
        original=automatic.boot_carrier(original,built)
    old=boot.parse_boot_v4(original)
    def header(value):return {k:v for k,v in value.header.items() if k not in
        ('ramdisk_size','ramdisk_end','signature_start','signature_end')}
    def trailer(data,value):
        footer=boot.parse_avb_footer(data);end=value.header['signature_end'];marker=b'SEANDROIDENFORCE'
        require(data[end:end+16]==marker and footer['original_image_size']==end+16 and
            footer['vbmeta_offset']==boot.align(end+16,4096) and not any(data[end+16:footer['vbmeta_offset']]) and
            not any(data[footer['vbmeta_offset']+footer['vbmeta_size']:-64]),'integrated boot trailer differs')
        return {k:footer[k] for k in ('version_major','version_minor','vbmeta_size','vbmeta_sha256')}
    require(len(actual)==len(original) and actual[:12]+actual[16:4096]==original[:12]+original[16:4096] and
        parsed.kernel==old.kernel and parsed.signature==old.signature and
        header(parsed)==header(old) and trailer(actual,parsed)==trailer(original,old),
        'integrated carrier/kernel/header/signature changed')
