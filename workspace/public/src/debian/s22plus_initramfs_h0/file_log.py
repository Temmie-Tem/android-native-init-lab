#!/usr/bin/env python3
"""Build the USB-independent Debian file pilot; H0 only."""
import argparse
import json
from pathlib import Path
import re
import secrets
import shutil
import sys
import uuid

import early
import fyg8
import h0
import s22plus_native_journal_recovery_h0 as admission
import file_log_faults
import s22plus_debian_file_protocol_v1 as protocol
import s22plus_debian_failure_protocol_v1 as diagnostic_protocol
from s22plus_native_records_v3 import pin,verify

NAMESPACE='p421'
VERSION='v0.5.0-rc.5'
PROFILE='debian-file-pilot-v1'


def validate_identity(namespace,version):
    h0.require((namespace is None)==(version is None),'candidate namespace/version must be supplied together')
    h0.require(namespace is None or isinstance(namespace,str) and re.fullmatch(r'p[0-9]{3,6}',namespace),
        'file candidate namespace differs')
    h0.require(version is None or isinstance(version,str) and re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+',version),
        'file candidate version differs')


def prepare(out,inputs,packages,*,run=None,key=None,virt=False,fresh=True,fault=None,storage_first=False,diagnostic=False,diagnostic_fault=None,namespace=None,version=None,autoboot=False,transition=False,transition_fault=None,rcs=False,watchdog=False,phase=False,single_cpu=False,post_p447=False,script_channel=False,minimal=False,reboot=None,cron=False):
    h0.require(not diagnostic or storage_first,"diagnostics require storage-first")
    h0.require(not autoboot or diagnostic and storage_first,'autoboot requires supervised storage-first')
    h0.require(not transition or autoboot,'transition observer requires automatic startup')
    h0.require(not rcs or transition,'rcS observation requires automatic transition observation')
    h0.require(not watchdog or rcs,'watchdog history requires automatic rcS observation')
    h0.require(not phase or watchdog,'phase history requires the complete predecessor selection')
    h0.require(not single_cpu or watchdog and not phase,'single CPU requires retained watchdog history without phase instrumentation')
    h0.require(transition_fault is None or transition and virt,'transition fault requires the VM')
    validate_identity(namespace,version)
    out=h0.private(out,fresh=fresh);inputs=h0.private(inputs);packages=h0.private(packages)
    sources=snapshot(out) if storage_first and fresh else None
    h0.verify_packages(packages,out);inventory=fyg8.verify_inventory(inputs)
    run=run or uuid.uuid4().hex;key=key or secrets.token_bytes(32)
    h0.require(re.fullmatch('[0-9a-f]{32}',run) and len(key)==32,'file pilot identity differs')
    h0.require(fault is None or virt and fault in file_log_faults.NAMES,'file faults require the VM')
    (out/'key').write_bytes(key);(out/'key').chmod(0o400)
    # Reuse the exact inventory/header generator. This first compile is H0;
    # the module-only helper below is the sole helper included in the image.
    modules=inventory['modules']
    if diagnostic:
        original=(packages/'root/usr/share/initramfs-tools/init').read_bytes()
        needle=b'mount -t devtmpfs -o nosuid,mode=0755 udev /dev\n'
        h0.require(original.count(needle)==1,'diagnostic init adaptation differs')
        initial=original.replace(needle,b'. /scripts/fyg8-dev\n')
        (out/'observer-seal.h').write_text(early.array('early_shell_hash',bytes.fromhex(fyg8.digest(early.shell_input(packages))))+
            early.array('early_init_hash',bytes.fromhex(fyg8.digest(initial))))
    if storage_first:
        import file_first
        modules=file_first.prepare_modules(out,inputs,inventory,run,key,virt,diagnostic=diagnostic,diagnostic_fault=diagnostic_fault,autoboot=autoboot)
    else:fyg8.compile_helper(out,inputs,run_id=run,virt=virt)
    flags=['aarch64-linux-gnu-gcc','-static','-Os','-Wall','-Wextra','-Werror',
        '-Wno-unused-function','-Wno-unused-const-variable','-ffunction-sections','-fdata-sections',
        '-Wl,--gc-sections','-fno-ident','-Wl,--build-id=none','-I',out,'-I',fyg8.ext4.NATIVE,'-I',h0.HERE]
    if not storage_first:
        h0.run([*flags,'-DFYG8_USB_RAM_ONLY',*(['-DFYG8_VM_TEST'] if virt else []),
            h0.HERE/'usb-first-prepare.c','-o',out/'fyg8-prepare'],out/'module-compile.log')
    if autoboot:
        import s22plus_debian_autoboot_profile_v1 as automatic
        generated=automatic.admission_headers(run,transition,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot is not None,cron)
    else:generated=admission.headers(run)
    for name,data in generated['headers'].items():(out/name).write_bytes(data)
    (out/'table.bin').write_bytes(generated['table'])
    checker=verify(admission.profile.execution_binding()['checker'])
    shutil.copyfile(checker,out/'s22-fs-e2fsck');(out/'s22-fs-e2fsck').chmod(0o500)
    original=(packages/'root/usr/share/initramfs-tools/init').read_bytes()
    needle=b'mount -t devtmpfs -o nosuid,mode=0755 udev /dev\n'
    h0.require(original.count(needle)==1,'Debian init adaptation differs')
    init=original.replace(needle,b'. /scripts/fyg8-dev\n');shell=early.shell_input(packages)
    measured=dict(shell_sha256=fyg8.digest(shell),init_sha256=fyg8.digest(init),helper_sha256=h0.sha(out/'fyg8-prepare'))
    text='#ifndef S22_EARLY_SEAL_V1_H\n#define S22_EARLY_SEAL_V1_H\n'+early.array('early_key',key)+early.array('early_run',bytes.fromhex(run))
    for name,field in (('early_shell_hash','shell_sha256'),('early_init_hash','init_sha256'),('early_helper_hash','helper_sha256')):
        text+=early.array(name,bytes.fromhex(measured[field]))
    if storage_first:
        import s22plus_debian_file_first_plan_v1 as first
        text+='static const uint64_t early_helper_size='+str((out/'fyg8-prepare').stat().st_size)+'ULL;\n'
    text+='#define EARLY_DOMAIN '+json.dumps((automatic.reboot_spec.EARLY_DOMAIN if reboot is not None else automatic.DOMAIN).decode() if autoboot else ('S22PLUS-FYG8-DEBIAN-FAILURE-v1' if diagnostic else (first.DOMAIN if storage_first else protocol.DOMAIN).decode()))+'\n'
    text+='#endif\n'
    (out/'early-seal.h').write_text(text)
    if cron:
        h0.require(autoboot and reboot is not None,'cron requires automatic reboot selection')
        (out/'s22plus_debian_cron_seal_v1.h').write_bytes(automatic.cron_variant(cron).seal(run))
    if reboot is not None:
        h0.require(autoboot and minimal,'reboot requires selected automatic minimal path')
        (out/'s22plus_debian_reboot_seal_v1.h').write_bytes(automatic.reboot_spec.seal(run,reboot['initial_mount_count']))
    source,extra=file_log_faults.source(out,h0.HERE/'file-log.c',fault) if fault else (h0.HERE/'file-log.c',[])
    fault_sources=[]
    if transition_fault and autoboot and transition_fault in automatic.cron_variant(cron).RUNTIME_FAULTS:
        h0.require(virt and cron,'cron faults require selected VM')
    elif transition_fault:
        import autoboot_transition_faults
        source,fault_sources=autoboot_transition_faults.source(out,source,transition_fault,fyg8.ext4.NATIVE)
    h0.run([*flags,*(['-DS22_ROOT_INSPECT_VIRT_TEST'] if virt else []),
        *(['-DFL_STORAGE_FIRST'] if storage_first else []),*(['-DS22_FAILURE_OBSERVER'] if diagnostic else []),
        *(['-DS22_DEBIAN_AUTOBOOT'] if autoboot else []),
        *(['-DS22_DEBIAN_REBOOT'] if reboot is not None else []),
        *(['-DS22_DEBIAN_CRON'] if cron else []),
        *(['-DS22_DEBIAN_CRON_CONFIG'] if cron=='config' else []),
        *(['-DS22_AUTOBOOT_SINGLECPU'] if single_cpu else []),
        *(['-DS22_AUTOBOOT_TRACE=1','-DS22_AUTOBOOT_HISTORY'] if transition else []),*extra,
        source,'-o',out/'file-log'],out/'writer-compile.log')
    for name in ('fyg8-prepare','file-log'):
        h0.run(['file',out/name],out/(name+'-file.log'))
        raw=(out/name).read_bytes()
        h0.require(not any(p in raw for p in (*(() if storage_first else (b'/dev/kmsg',b'/proc/last_kmsg')),b'/s22-journal-replay',
            b'/dev/ttyGS',b'/config/usb_gadget',b'/sbin/init')),'file pilot contains an excluded execution path')
    result=dict(namespace='p428' if diagnostic else first.NAMESPACE if storage_first else NAMESPACE,
        version='v0.7.0-rc.1' if diagnostic else first.VERSION if storage_first else VERSION,
        profile='debian-failure-observer-v1' if diagnostic else first.PROFILE if storage_first else PROFILE,run_id=run,virtual=virt,
        inputs=str(inputs),packages=str(packages),modules=modules,measured=measured,fault=fault,
        admission=dict(table_count=generated['count'],boot_count=generated['boot'],
            checker=pin(out/'s22-fs-e2fsck'),table=pin(out/'table.bin')))
    if namespace is not None:result['namespace']=namespace
    if version is not None:result['version']=version
    if diagnostic:result.update(diagnostic=True,diagnostic_fault=diagnostic_fault)
    if autoboot:result.update(profile=automatic.PROFILE,history=generated['history'],automatic=True)
    if transition:result['additional_history']=generated['additional_history']
    if rcs:result['runtime_history']=generated['runtime_history']
    if watchdog:result['watchdog_history']=generated['watchdog_history']
    if phase:result['phase_history']=generated['phase_history']
    if single_cpu:result['current_history']=generated['current_history']
    if transition_fault:result['transition_fault_sources']=fault_sources
    if storage_first:
        if sources is None:sources=json.loads((out/'source-inputs.json').read_text())
        for row in sources:h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'file preparation source changed')
        result['construction']=dict(source_inputs=sources,helper=pin(out/'fyg8-prepare'),writer=pin(out/'file-log'),
            headers={p.name:pin(p) for p in sorted(out.glob('*.h'))})
        if diagnostic and diagnostic_fault:
            result['construction']['fault_sources']=[pin(p) for p in sorted((out/'diagnostic-fault').iterdir()) if p.is_file()]
    h0.publish(out/'request.json',result);return result


def snapshot(out):
    import file_first
    import s22plus_debian_file_first_protocol_v1
    import s22plus_debian_file_first_profile_v1
    rows={r['path']:r for r in early.snapshot(out)}
    paths=set(admission.source_files())|{h0.HERE/'file-hook',Path(protocol.__file__),
        fyg8.ext4.NATIVE/'s22plus_autoboot_singlecpu_v1.h',
        *(fyg8.ext4.NATIVE/n for n in ('s22plus_debian_reboot_common_v1.h',
            's22plus_debian_reboot_root_v1.inc.c','s22plus_debian_evidence_chain_v1.h'))}|set(h0.HERE.glob('*.h'))
    for path in sorted(paths):
        dest=out/'source-snapshot'/path.relative_to(h0.ROOT)
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes())
        rows[str(path.relative_to(h0.ROOT))]=dict(path=str(path.relative_to(h0.ROOT)),sha256=h0.sha(dest))
    rows=sorted(rows.values(),key=lambda r:r['path']);h0.publish(out/'source-inputs.json',rows);return rows


def build(out,inputs,packages,*,run=None,key=None,storage_first=False,diagnostic=False,namespace=None,version=None):
    validate_identity(namespace,version)
    out=h0.private(out,fresh=True);sources=snapshot(out)
    request=prepare(out,inputs,packages,fresh=False,run=run,key=key,storage_first=storage_first,diagnostic=diagnostic,
        namespace=namespace,version=version)
    h0.run(['unshare','--user','--map-auto','--map-root-user','--mount','--pid','--fork','--mount-proc',
        sys.executable,__file__,'inside','--output',out,*(['--storage-first'] if storage_first else [])],out/'namespace-build.log',timeout=700)
    h0.require(h0.sha(out/'initramfs-a.cpio.gz')==h0.sha(out/'initramfs-b.cpio.gz'),'file A/B archive differs')
    entries=fyg8.debian_entries(out/'initramfs-a.cpio.gz');rows={e.name:e for e in entries}
    h0.require(len(rows)==len(entries) and rows['lib'].file_type=='directory','archive/vendor collision')
    h0.require(fyg8.digest(rows['init'].data)==request['measured']['init_sha256'],'actual init differs')
    shell=rows['usr/bin/sh'];bodies=[e.data for e in entries if e.inode==shell.inode and e.file_type=='regular' and e.data]
    h0.require(len(bodies)==1 and fyg8.digest(bodies[0])==request['measured']['shell_sha256'],'actual shell differs')
    for source,target in (('fyg8-prepare','usr/sbin/fyg8-prepare'),('file-log','usr/sbin/file-log'),
            ('s22-fs-e2fsck','s22-fs-e2fsck'),('table.bin','s22-root-inspect.table')):
        h0.require(rows[target].data==(out/source).read_bytes(),'actual file pilot member differs')
    h0.require('usr/sbin/early-observer' not in rows and 's22-journal-replay' not in rows,'excluded child packaged')
    for m in request['modules']:
        e=rows['lab/modules/'+m['name']]
        h0.require(len(e.data)==m['size'] and fyg8.digest(e.data)==m['sha256'] and
            (e.uid,e.gid,e.nlink,e.mode&0o7777)==(0,0,1,0o400),'embedded module differs')
    h0.require({n for n in rows if n.startswith('lab/modules/')}=={'lab/modules/'+m['name'] for m in request['modules']},
        'unexpected embedded module')
    for row in sources:h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'file source changed during build')
    h0.publish(out/'build.json',dict(schema='s22plus-debian-failure-observer-h0-v1' if diagnostic else 's22plus-debian-file-first-h0-v1' if storage_first else 's22plus-debian-file-pilot-h0-v1',status='H0_INITRAMFS_BUILT',
        **request,initramfs=pin(out/'initramfs-a.cpio.gz',maximum=16*1024**2),helper=pin(out/'fyg8-prepare'),
        writer=pin(out/'file-log'),ab_identical=True,source_inputs=sources,device_actions=0,active=False,
        headers={p.name:pin(p) for p in sorted(out.glob('*.h'))}))
    print('PASS: file-pilot A/B initramfs; H0 only')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('build','inside','prepare'))
    for name in ('output','inputs','packages'):p.add_argument('--'+name,type=Path,required=name=='output')
    p.add_argument('--namespace');p.add_argument('--version')
    p.add_argument('--virt',action='store_true');p.add_argument('--storage-first',action='store_true');p.add_argument('--diagnostic',action='store_true');a=p.parse_args()
    if a.action=='build':build(a.output,a.inputs,a.packages,storage_first=a.storage_first,diagnostic=a.diagnostic,namespace=a.namespace,version=a.version)
    elif a.action=='prepare':prepare(a.output,a.inputs,a.packages,virt=a.virt,storage_first=a.storage_first,diagnostic=a.diagnostic,namespace=a.namespace,version=a.version)
    else:
        request=json.loads((a.output/'request.json').read_text())
        fyg8.inside(a.output,Path(request['packages']),Path(request['inputs']),file_pilot=True,storage_first=a.storage_first)
