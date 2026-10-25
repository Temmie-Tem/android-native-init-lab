#!/usr/bin/env python3
"""Build one automatic Debian boot with the existing checked preparation."""
import argparse
from dataclasses import replace
import gzip
import json
from pathlib import Path
import secrets
import shutil
import sys
import uuid

import early
import file_log
import fyg8
import h0
import integrated
import s22plus_debian_reboot_baseline_v1 as baseline
import s22plus_debian_autoboot_profile_v1 as profile
import s22plus_debian_handoff_h0 as handoff
from s22plus_native_records_v3 import pin,read,verify


def sources():
    return sorted(set(handoff.source_files())|set(file_log.admission.source_files())|
        {p for p in h0.HERE.iterdir() if p.is_file() and p.suffix in ('.py','.c','.h')}|
        {Path(profile.__file__),Path(profile.phase_spec.__file__),Path(profile.minimal_spec.__file__),Path(profile.reboot_spec.__file__),Path(profile.cron_spec.__file__),h0.HERE/'autoboot-hook',h0.HERE/'fyg8-dev',
         handoff.base.NATIVE/'s22plus_autoboot_transition_v1.h',
         handoff.base.NATIVE/'s22plus_autoboot_singlecpu_v1.h',
         handoff.base.NATIVE/'s22plus_debian_reboot_common_v1.h',
         handoff.base.NATIVE/'s22plus_debian_reboot_root_v1.inc.c',
         handoff.base.NATIVE/'s22plus_debian_cron_v1.h',
         handoff.base.NATIVE/'s22plus_debian_cron_runtime_v1.inc.c',
         handoff.base.NATIVE/'s22plus_autoboot_transition_stages_v1.def',
         handoff.base.NATIVE/'s22plus_autoboot_phase_v1.h',
         handoff.base.NATIVE/'s22plus_autoboot_phase_parse_v1.h',
         *(handoff.base.NATIVE/name for name in ('s22plus_autoboot_script_v1.h',
             's22plus_autoboot_script_packet_v1.h','s22plus_autoboot_script_channel_v1.h')),
         profile.ROOT/'workspace/public/src/scripts/revalidation/s22plus_debian_autoboot_transition_v1.py',
         *(profile.ROOT/'workspace/public/src/scripts/revalidation'/name for name in (
             's22plus_debian_autoboot_access_v1.py','s22plus_debian_autoboot_protocol_v1.py',
             's22plus_debian_reboot_access_v1.py','s22plus_debian_reboot_baseline_v1.py',
             's22plus_debian_reboot_qualification_v1.py',
             's22plus_debian_autoboot_qualification_v1.py','s22plus_debian_autoboot_retrieval_v1.py')),
         profile.ROOT/'workspace/public/src/debian/s22plus_v1/device/lab-usb-autoboot',
         profile.ROOT/'workspace/public/src/debian/s22plus_v1/device/virt-binding.inc.c'})


def snapshot(out):
    rows=[]
    for path in sources():
        dest=out/'source-snapshot'/path.relative_to(h0.ROOT)
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes())
        rows.append(dict(path=str(path.relative_to(h0.ROOT)),sha256=h0.sha(dest)))
    h0.publish(out/'source-inputs.json',rows);return rows


def dev_script():
    text=(h0.HERE/'fyg8-dev').read_text();anchor='mknod -m 666 /dev/null c 1 3 || fyg8_stop\n'
    h0.require(text.count(anchor)==1 and text.endswith('fyg8_stop\n'),'initial RAM script changed')
    text=text.replace(anchor,anchor+'mknod -m 600 /dev/kmsg c 1 11 || fyg8_stop\n')
    tail=file_log.fyg8.file_script()
    h0.require(tail.endswith('file_status=$?\nfyg8_stop\n'),'file phase settlement script changed')
    tail=tail[:-len('fyg8_stop\n')]+'''[ "$file_status" = 0 ] || fyg8_stop
exec /sbin/autoboot-init
fyg8_stop
'''
    return text[:-len('fyg8_stop\n')]+tail


def compile_unit(out,name,source,headers,virt,transition=False,transition_fault=None,rcs=False,watchdog=False,phase=False,single_cpu=False,script_channel=False,minimal=False,reboot=None,cron=False):
    flags=[*integrated.FLAGS,'-DS22_DEBIAN_HANDOFF','-DS22_DEBIAN_AUTOBOOT',
        '-I',out,'-I',headers,'-I',fyg8.ext4.NATIVE,'-I',h0.HERE]
    if transition:flags+=['-DS22_AUTOBOOT_TRACE='+str(dict(entry=2,witness=3,hook=4)[name]),'-DS22_AUTOBOOT_HISTORY']
    if rcs:flags+=['-DS22_AUTOBOOT_RCS_TRACE']
    if watchdog:flags+=['-DS22_AUTOBOOT_WATCHDOG_TRACE']
    if phase:flags+=['-DS22_AUTOBOOT_PHASE_TRACE']
    if script_channel:flags+=['-DS22_AUTOBOOT_SCRIPT_CHANNEL']
    if minimal:flags+=['-DS22_AUTOBOOT_MINIMAL']
    if reboot is not None:flags+=['-DS22_DEBIAN_REBOOT']
    if cron:flags+=['-DS22_DEBIAN_CRON']
    if single_cpu:flags+=['-DS22_AUTOBOOT_SINGLECPU']
    if virt:flags+=['-DS22_ROOT_INSPECT_VIRT_TEST','-DFYG8_VM_TEST','-DEARLY_VM_TEST']
    if transition_fault in profile.cron_spec.RUNTIME_FAULTS:
        h0.require(virt and cron,'cron faults require the selected VM')
        flags+=['-DCR_VM_FAULT='+str(profile.cron_spec.RUNTIME_FAULTS[transition_fault])]
    elif transition_fault:
        import autoboot_transition_faults
        source,_=autoboot_transition_faults.source(out,source,transition_fault,fyg8.ext4.NATIVE)
    for side in 'ab':
        h0.run(['aarch64-linux-gnu-gcc',*flags,source,'-o',out/(name+'-'+side)],out/(name+'-'+side+'.compile.log'))
    h0.require((out/(name+'-a')).read_bytes()==(out/(name+'-b')).read_bytes(),'automatic helper A/B differs')
    h0.run(['file',out/(name+'-a')],out/(name+'.file.log'))
    return pin(out/(name+'-a'),maximum=8*1024**2)


def prepare(out,inputs,packages,*,run=None,key=None,virt=False,fresh=True,transition=False,transition_fault=None,rcs=False,watchdog=False,idle_policy=None,phase=False,single_cpu=False,post_p447=False,script_channel=False,minimal=False,reboot=None,cron=False):
    h0.require(transition_fault is None or virt and transition,'transition fault requires virtual observation')
    h0.require(not rcs or transition,'rcS observation requires the transition variant')
    h0.require(not watchdog or rcs,'watchdog observation requires the rcS variant')
    h0.require(not phase or watchdog,'phase observation requires the complete predecessor selection')
    h0.require(not single_cpu or watchdog and not phase and idle_policy=='cpuidle-off',
        'single CPU requires its reviewed history and idle selection')
    h0.require(not post_p447 or single_cpu,'P447 history requires single CPU selection')
    h0.require(not minimal or script_channel,'minimal workload requires the current channel/history')
    h0.require(not script_channel or post_p447,'script channel requires the current single CPU history')
    h0.require(idle_policy in profile.IDLE_POLICIES if watchdog else idle_policy is None,
        'idle policy requires the selected watchdog variant')
    h0.require(not cron or reboot is not None and reboot['initial_mount_count']==profile.cron_spec.EXPECTED_MOUNT_COUNT,
        'cron requires the exact post-P458 mount count and reboot selection')
    if reboot is not None:
        h0.require(minimal and reboot==baseline.binding(reboot['receipt']),
            'reboot needs minimal selection and a rederived pre-build baseline')
    out=h0.private(out,fresh=fresh);saved=snapshot(out) if fresh else read(out/'source-inputs.json')
    run=run or uuid.uuid4().hex;key=key or secrets.token_bytes(32)
    namespace=profile.cron_spec.NAMESPACE if cron else profile.reboot_spec.NAMESPACE if reboot is not None else profile.MINIMAL_NAMESPACE if minimal else profile.SCRIPT_NAMESPACE if script_channel else profile.SINGLECPU_P447_NAMESPACE if post_p447 else profile.SINGLECPU_NAMESPACE if single_cpu else profile.PHASE_NAMESPACE if phase else profile.WATCHDOG_NAMESPACE if watchdog else profile.RCS_NAMESPACE if rcs else profile.TRANSITION_NAMESPACE if transition else profile.NAMESPACE
    version=profile.cron_spec.VERSION if cron else profile.reboot_spec.VERSION if reboot is not None else profile.MINIMAL_VERSION if minimal else profile.SCRIPT_VERSION if script_channel else profile.SINGLECPU_P447_VERSION if post_p447 else profile.SINGLECPU_VERSION if single_cpu else profile.PHASE_VERSION if phase else profile.WATCHDOG_VERSION if watchdog else profile.RCS_VERSION if rcs else profile.TRANSITION_VERSION if transition else profile.VERSION
    prefix=out/'early';prefix.mkdir(mode=0o700)
    file_log.snapshot(prefix)
    first=file_log.prepare(prefix,inputs,packages,run=run,key=key,virt=virt,fresh=False,
        storage_first=True,diagnostic=True,autoboot=True,namespace=namespace,version=version,transition=transition,transition_fault=transition_fault,rcs=rcs,watchdog=watchdog,phase=phase,single_cpu=single_cpu,post_p447=post_p447,script_channel=script_channel,minimal=minimal,reboot=reboot,cron=cron)
    destination=out/'installed';destination.mkdir(mode=0o700)
    base=handoff.base
    for name in ('s22plus_native_ext4_seal_v1.h','s22plus_native_root_inspect_seal_v1.h',
            's22plus_native_userspace_probe_seal_v1.h'):
        (destination/name).write_bytes((prefix/name).read_bytes())
    (destination/'s22plus_native_staged_preflight_seal_v1.h').write_bytes(base.staged.header())
    (destination/'s22plus_switch_root_seal_v1.h').write_bytes(base.seal(run,key))
    (destination/'s22plus_debian_handoff_seal_v1.h').write_bytes(profile.header(namespace,version,run,virt=virt,transition=transition,rcs=rcs,watchdog=watchdog,phase=phase,single_cpu=single_cpu,post_p447=post_p447,script_channel=script_channel,minimal=minimal,reboot=reboot is not None,cron=cron))
    if phase:(destination/'s22plus_autoboot_phase_seal_v1.h').write_bytes(profile.phase_spec.header(virt=virt))
    if script_channel:(destination/'s22plus_autoboot_script_seal_v1.h').write_bytes(profile.script_spec(minimal).script_header())
    installed_init,assets=profile.payloads(run,virt=virt,single_cpu=single_cpu,minimal=minimal,reboot=reboot is not None,cron=cron)
    for name,data in assets.items():(destination/name).write_bytes(data)
    hook=compile_unit(destination,'hook',base.NATIVE/'s22plus_debian_handoff_hook_v1.c',prefix,virt,transition,transition_fault,rcs,watchdog,phase,single_cpu,script_channel,minimal,reboot,cron)
    handoff.payload_header(destination,hook,virt,minimal=minimal)
    witness=compile_unit(destination,'witness',base.NATIVE/'s22plus_switch_root_witness_v1.c',prefix,virt,transition,transition_fault,rcs,watchdog,phase,single_cpu,script_channel,minimal,reboot,cron)
    (destination/'s22plus_switch_root_payload_v1.h').write_bytes(base.payload_header(witness))
    entry=compile_unit(destination,'entry',h0.HERE/'autoboot-init.c',prefix,virt,transition,transition_fault,rcs,watchdog,phase,single_cpu,script_channel,minimal,reboot,cron)
    (out/'fyg8-dev').write_text(dev_script())
    result=dict(namespace=namespace,version=version,profile=profile.PROFILE,
        run_id=run,virtual=virt,inputs=str(h0.private(inputs)),packages=str(h0.private(packages)),
        key=pin(prefix/'key'),startup_script=pin(out/'fyg8-dev'),modules=first['modules'],measured=first['measured'],history=first['history'],
        helper=pin(prefix/'fyg8-prepare'),writer=pin(prefix/'file-log'),entry=entry,hook=hook,witness=witness,
        busybox=base.busybox(),checker=pin(prefix/'s22-fs-e2fsck'),table=pin(prefix/'table.bin'),
        admission=first['admission'],assets=dict(handoff.asset_rows(destination,hook,virt,minimal=minimal)),
        installed_init=dict(size=len(installed_init),sha256=fyg8.digest(installed_init)),
        deadline_ms=300000,observer_revision=6 if single_cpu else 5,trace_maximum=262144,device_actions=0,active=False,
        source_inputs=saved,headers={str(p.relative_to(out)):pin(p) for p in
            sorted(list(prefix.glob('*.h'))+list(destination.glob('*.h')))})
    if transition:result.update(transition_observer=profile.observer(rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot is not None,cron),additional_history=first['additional_history'])
    if rcs:result['runtime_history']=first['runtime_history']
    if watchdog:result.update(watchdog_history=first['watchdog_history'],idle_policy=idle_policy)
    if phase:result.update(phase_history=first['phase_history'],phase_declaration=profile.phase_spec.declaration())
    if phase and virt:result['phase_vm_timing']=profile.phase_spec.VM_TIMING
    if script_channel:result['script_declaration']=profile.script_spec(minimal).script_declaration()
    if single_cpu:result.update(cpu_policy=profile.SINGLECPU_POLICY,current_history=first['current_history'])
    if reboot is not None:
        result['reboot']=profile.reboot_spec.declaration(run,reboot['initial_mount_count'])
        result['reboot_baseline']=reboot
    if cron:result['cron']=profile.cron_spec.declaration(run)
    if transition_fault:result.update(transition_fault=transition_fault,transition_fault_sources=
        first['transition_fault_sources']+[pin(p) for p in sorted(destination.glob('*-transition-fault/*'))])
    for row in saved:h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'automatic source changed')
    h0.publish(out/'request.json',result);return result


def payloads(selected):return profile.ramdisk_payloads(selected)

def inside(out):
    selected=read(out/'request.json');inputs=h0.private(selected['inputs']);packages=h0.private(selected['packages'])
    tree=h0.builder_tree(out,packages)
    for name,row in payloads(selected).items():
        target=tree/name;target.write_bytes(verify(row,maximum=8*1024**2).read_bytes())
        target.chmod(0o400 if name in ('s22-root-inspect.table','s22-debian-inittab','s22-debian-crontab') else 0o500)
    (tree/'lab/modules').mkdir(parents=True)
    for row in selected['modules']:
        path=out/'early'/row['name'] if row['runtime_name']=='sec_log_buf' else inputs/'modules'/row['name']
        target=tree/'lab/modules'/row['name'];target.write_bytes(path.read_bytes());target.chmod(0o400)
    conf=tree/'etc/initramfs-tools'
    for name in ('conf.d','hooks','scripts'):(conf/name).mkdir(parents=True,exist_ok=True)
    (conf/'initramfs.conf').write_text('MODULES=list\nBUSYBOX=y\nCOMPRESS=gzip\nKEYMAP=n\nRESUME=none\n')
    (conf/'modules').write_text('')
    shutil.copyfile(h0.HERE/'autoboot-hook',conf/'hooks/zzzz-autoboot');(conf/'hooks/zzzz-autoboot').chmod(0o755)
    (conf/'scripts/fyg8-dev').write_bytes(verify(selected['startup_script']).read_bytes());(conf/'scripts/fyg8-dev').chmod(0o755)
    init=tree/'usr/share/initramfs-tools/init';original=init.read_bytes()
    needle=b'mount -t devtmpfs -o nosuid,mode=0755 udev /dev\n'
    h0.require(original.count(needle)==1,'Debian init changed');init.write_bytes(original.replace(needle,b'. /scripts/fyg8-dev\n'))
    (tree/'boot').mkdir(exist_ok=True);shutil.copyfile(inputs/'kernel.config',tree/'boot'/('config-'+fyg8.KERNEL_RELEASE))
    modules=tree/'usr/lib/modules'/fyg8.KERNEL_RELEASE;modules.mkdir(parents=True,exist_ok=True)
    for name in ('modules.builtin','modules.builtin.modinfo','modules.order'):(modules/name).write_text('')
    h0.generate_archives(out,tree,fyg8.KERNEL_RELEASE)


def repack_template(out,selected):
    """Reuse the identical measured Debian base, replacing only named payloads.

    This unprivileged construction avoids needing host UID mappings. Every
    retained member keeps its metadata; no installed root archive is edited.
    """
    import fyg8_vm
    retrieval=read(verify(profile.reboot_spec.P457_RETRIEVAL))
    source=read(verify(retrieval['writer_build']))
    h0.require(source['namespace']==profile.MINIMAL_NAMESPACE and source['version']==profile.MINIMAL_VERSION and
        source['transition_observer']==profile.MINIMAL_OBSERVER and source['virtual'] is False and
        source['ab_identical'] is True and source['modules']==selected['modules'] and
        all(source['measured'][name]==selected['measured'][name] for name in ('init_sha256','shell_sha256')),
        'repack template differs from the retained measured Debian base')
    template=verify(source['initramfs'],maximum=32*1024**2)
    entries=list(fyg8.debian_entries(template));replacements=payloads(selected)
    original=gzip.decompress(template.read_bytes());root_size=(110+int(original[94:102],16)+3)&~3
    leading_root=original[:root_size]
    replacements['scripts/fyg8-dev']=selected['startup_script']
    names=[e.name for e in entries]
    h0.require(len(names)==len(set(names)) and all(names.count(name)==1 for name in replacements),
        'repack members are missing or duplicate')
    # Assert the original construction's exact source binding before replacement.
    old_payloads=payloads(source);old_payloads['scripts/fyg8-dev']=source['startup_script']
    h0.require(set(old_payloads)==set(replacements),'repack changes the base member vocabulary')
    for item in entries:
        if item.name in old_payloads:
            h0.require(item.data==verify(old_payloads[item.name],maximum=8*1024**2).read_bytes(),
                'template payload does not join its original producer')
    replacement_bytes={name:verify(row,maximum=8*1024**2).read_bytes() for name,row in replacements.items()}
    for label in ('a','b'):
        result=[replace(e,data=replacement_bytes[e.name]) if e.name in replacement_bytes else e for e in entries]
        (out/('initramfs-'+label+'.cpio.gz')).write_bytes(gzip.compress(leading_root+fyg8_vm.newc(result),mtime=0))
    decoded=list(fyg8.debian_entries(out/'initramfs-a.cpio.gz'))
    h0.require(len(decoded)==len(entries),'repack changed member count')
    for old,new in zip(entries,decoded):
        h0.require(replace(new,data=old.data)==old and new.data==replacement_bytes.get(old.name,old.data),
            'repack changed an undeclared member or metadata')
    return dict(method='EXACT_MEASURED_TEMPLATE_REPACK',template_build=retrieval['writer_build'],
        template=source['initramfs'],replaced=sorted(replacements),unmodified_members=len(entries)-len(replacements),
        package_installation=False)


def build(out,inputs,packages,*,transition=False,rcs=False,watchdog=False,idle_policy=None,phase=False,single_cpu=False,post_p447=False,script_channel=False,minimal=False,reboot=None,cron=False):
    out=h0.private(out,fresh=True);saved=snapshot(out)
    selected=prepare(out,inputs,packages,fresh=False,transition=transition,rcs=rcs,watchdog=watchdog,idle_policy=idle_policy,phase=phase,single_cpu=single_cpu,post_p447=post_p447,script_channel=script_channel,minimal=minimal,reboot=reboot,cron=cron)
    if reboot is not None:selected['construction']=repack_template(out,selected)
    else:
        h0.run(['unshare','--user','--map-auto','--map-root-user','--mount','--pid','--fork','--mount-proc',
            sys.executable,__file__,'inside','--output',out],out/'namespace-build.log',timeout=700)
    h0.require((out/'initramfs-a.cpio.gz').read_bytes()==(out/'initramfs-b.cpio.gz').read_bytes(),'automatic initramfs A/B differs')
    rows=fyg8.debian_entries(out/'initramfs-a.cpio.gz');entries={e.name:e for e in rows}
    h0.require(len(rows)==len(entries) and entries['lib'].file_type=='directory','vendor archive layout differs')
    h0.require(fyg8.digest(entries['init'].data)==selected['measured']['init_sha256'] and
        entries['scripts/fyg8-dev'].data==dev_script().encode(),'actual initial owner differs')
    shell=entries['usr/bin/sh'];bodies=[e.data for e in rows if e.inode==shell.inode and e.file_type=='regular' and e.data]
    h0.require(len(bodies)==1 and fyg8.digest(bodies[0])==selected['measured']['shell_sha256'],'actual shell hardlink differs')
    for name,row in payloads(selected).items():
        h0.require(entries[name].data==verify(row,maximum=8*1024**2).read_bytes(),'packaged automatic payload differs')
    h0.require({n for n in entries if n.startswith('lab/modules/')}==
        {'lab/modules/'+row['name'] for row in selected['modules']},'automatic module set differs')
    for row in selected['modules']:
        actual=entries['lab/modules/'+row['name']]
        h0.require(len(actual.data)==row['size'] and fyg8.digest(actual.data)==row['sha256'] and
            (actual.uid,actual.gid,actual.nlink,actual.mode&0o7777)==(0,0,1,0o400),'packaged module differs')
    for row in saved:h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'source changed during build')
    h0.publish(out/'build.json',dict(schema='s22plus-debian-autoboot-h0-v1',status='H0_INITRAMFS_BUILT',
        **selected,initramfs=pin(out/'initramfs-a.cpio.gz',maximum=32*1024**2),ab_identical=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','build','inside'))
    for name in ('output','inputs','packages'):parser.add_argument('--'+name,type=Path,required=name=='output')
    parser.add_argument('--virt',action='store_true')
    parser.add_argument('--single-cpu',action='store_true',help='H0 P446: P441 proc observer, current sealed history, cpuidle.off=1 maxcpus=1')
    parser.add_argument('--post-p447',action='store_true',help='P448: exact authenticated P445 early history')
    parser.add_argument('--script-channel',action='store_true',help='P452: P451-authenticated P448 pair and bounded RAM rcS channel')
    parser.add_argument('--minimal',action='store_true',help='P456: fixed minimal sysinit and exact P455 history')
    parser.add_argument('--cron',action='store_true',help='P459: one packaged-cron workload and exact retained output')
    parser.add_argument('--reboot-baseline',type=Path,help='P458: exact fixed D0 or explicitly H0 synthetic baseline receipt')
    args=parser.parse_args()
    h0.require(not args.minimal or args.script_channel,'--minimal requires --script-channel')
    h0.require(not args.post_p447 or args.single_cpu,'--post-p447 requires --single-cpu')
    h0.require(not args.script_channel or args.post_p447,'--script-channel requires --post-p447 and --single-cpu')
    options=dict(transition=True,rcs=True,watchdog=True,idle_policy='cpuidle-off',single_cpu=True) if args.single_cpu else {}
    if args.post_p447:options['post_p447']=True
    if args.script_channel:options['script_channel']=True
    if args.minimal:options['minimal']=True
    if args.reboot_baseline:
        h0.require(args.minimal,'--reboot-baseline requires --minimal')
        options['reboot']=baseline.binding(pin(h0.private(args.reboot_baseline)))
    if args.cron:
        h0.require(args.reboot_baseline is not None,'--cron requires a fixed reboot baseline')
        options['cron']=True
    if args.action=='inside':inside(h0.private(args.output))
    elif args.action=='prepare':prepare(args.output,args.inputs,args.packages,virt=args.virt,**options)
    else:build(args.output,args.inputs,args.packages,**options)
