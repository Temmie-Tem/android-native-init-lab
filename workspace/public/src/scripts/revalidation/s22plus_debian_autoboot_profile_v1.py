"""Automatic Debian startup data and RAM assets; no device authority."""
import hashlib
import json
from pathlib import Path
import struct

import s22plus_debian_handoff_profile_v1 as handoff
import s22plus_debian_autoboot_phase_v1 as phase_spec
import s22plus_debian_autoboot_minimal_v1 as minimal_spec
import s22plus_debian_reboot_v1 as reboot_spec
import s22plus_debian_cron_v1 as cron_spec
import s22plus_debian_cron_config_v1 as cron_config_spec
from s22plus_native_records_v3 import read,require,verify

ROOT=handoff.ROOT
SCHEMA='s22plus-debian-autoboot-v1'
PROFILE='debian-autoboot-v1'
POLICY='docs/operations/S22PLUS_DEBIAN_AUTOBOOT_V1.md'
prior_inputs=handoff.prior_inputs
NAMESPACE='p432'
VERSION='v0.8.0-rc.1'
OPERATION=SELECTION='debian-autoboot'
DOMAIN=b'S22PLUS-FYG8-DEBIAN-AUTO-EARLY-v1'
PRIOR=ROOT/'workspace/private/outputs/s22plus-debian-argv-successor-p430-h0-20261015-1'
RETRIEVAL=dict(path=str(PRIOR/'retrieval-1/result.json'),size=4204,
    sha256='fc0cb5de91d6e25d62c1005a6acc24602a2060329e78ead17836a2cf5e0d27c3')
SECONDS=3600
CASES=('normal','changed-receipt','fd-leak','dirty','changed-history','foreign-file',
    'existing-early','existing-runtime','network-absent','module-error')
TRANSITION_NAMESPACE='p435'
TRANSITION_VERSION='v0.9.0-rc.1'
HISTORY_SELECTION='post-autoboot-p432-v1'
TRANSITION_OBSERVER=dict(schema='s22plus-autoboot-transition-v1',maximum_records_per_actor=96,
    maximum_record_bytes=512,logging_budget_ms_per_actor=2000,actors=5,history_selection=HISTORY_SELECTION)
RCS_NAMESPACE='p437'
RCS_VERSION='v0.10.0-rc.1'
RCS_HISTORY_SELECTION='post-autoboot-p436-v1'
RCS_OBSERVER=dict(TRANSITION_OBSERVER,schema='s22plus-autoboot-rcs-v1',actors=7,
    history_selection=RCS_HISTORY_SELECTION)
WATCHDOG_NAMESPACE='p441'
WATCHDOG_VERSION='v0.12.0-rc.0'
WATCHDOG_HISTORY_SELECTION='post-autoboot-p440-v1'
WATCHDOG_OBSERVER=dict(RCS_OBSERVER,schema='s22plus-autoboot-watchdog-v1',actors=8,
    history_selection=WATCHDOG_HISTORY_SELECTION,opportunities_per_owner=5,
    proc_budget_ms_per_owner=250,discovery_budget_ms=100,sample_budget_ms=25,
    latest_sample_ms=12500)
IDLE_POLICIES=('retained-default','cpuidle-off')
SINGLECPU_NAMESPACE='p446'
SINGLECPU_VERSION='v0.15.0-rc.0'
SINGLECPU_P447_NAMESPACE='p448'
SINGLECPU_P447_VERSION='v0.15.0-rc.1'
SINGLECPU_POLICY='maxcpus-1'
SINGLECPU_FAULTS=('singlecpu-disabled',)
SINGLECPU_CASES=('normal','dirty','changed-history','extra-runtime-history',
    'missing-p441-early','changed-p441-runtime','existing-early','existing-runtime',
    'trace-second-admission','rcs-record-fsync','network-absent',
    'singlecpu-unlimited',*SINGLECPU_FAULTS,'changed-receipt','fd-leak','module-error',
    'changed-p441-early','linked-p441-early','mode-p441-early',
    'missing-p441-runtime','linked-p441-runtime','mode-p441-runtime')
WATCHDOG_RETRIEVAL=dict(path=str(ROOT/'workspace/private/outputs/s22plus-autoboot-evidence-p440-h0-20261020-1/retrieval-1/result.json'),
    size=7421,sha256='f22ab47e8a835da42576b634d9650a267edb93f528fd498ddb17358f5a81bd61')
PHASE_NAMESPACE='p445'
PHASE_VERSION='v0.14.0-rc.0'
PHASE_HISTORY_SELECTION='post-autoboot-p444-v1'
PHASE_OBSERVER=dict(RCS_OBSERVER,schema='s22plus-autoboot-phase-v1',actors=8,
    history_selection=PHASE_HISTORY_SELECTION,**phase_spec.LIMITS)
SINGLECPU_OBSERVER=dict(WATCHDOG_OBSERVER,schema='s22plus-autoboot-singlecpu-v1',
    history_selection=PHASE_HISTORY_SELECTION)
SINGLECPU_P447_OBSERVER=dict(SINGLECPU_OBSERVER,history_selection='post-autoboot-p447-v1')
SCRIPT_FAULTS=('script-channel-setup','script-channel-gap')
SCRIPT_NAMESPACE='p452'
SCRIPT_VERSION='v0.17.0-rc.0'
SCRIPT_OBSERVER=dict(RCS_OBSERVER,schema='s22plus-autoboot-script-channel-v1',actors=8,
    history_selection='post-autoboot-p451-v1',**phase_spec.SCRIPT_LIMITS)
MINIMAL_NAMESPACE=minimal_spec.NAMESPACE
MINIMAL_VERSION=minimal_spec.VERSION
MINIMAL_OBSERVER=dict(SCRIPT_OBSERVER,schema='s22plus-autoboot-minimal-v1',
    history_selection='post-autoboot-p455-v1',**minimal_spec.LIMITS)
REBOOT_OBSERVER=dict(MINIMAL_OBSERVER,schema='s22plus-autoboot-reboot-v1',
    history_selection=reboot_spec.HISTORY_SELECTION)
CRON_OBSERVER=dict(REBOOT_OBSERVER,schema='s22plus-autoboot-cron-v1',
    history_selection=cron_spec.HISTORY_SELECTION)
CRON_CONFIG_OBSERVER=dict(REBOOT_OBSERVER,schema='s22plus-autoboot-cron-config-v1',
    history_selection=cron_config_spec.HISTORY_SELECTION)
P455_RETRIEVAL=dict(path=str(ROOT/'workspace/private/outputs/s22plus-autoboot-evidence-p455-h0-20261023-1/retrieval-1/result.json'),
    size=7713,sha256='ce2953428d9df49387387a73beafadaab778ba96685336c2ae4dbd8401ad6fc2')
P451_HISTORY_CASES=tuple(action+'-p448-'+kind for kind in ('early','runtime')
    for action in ('missing','changed','linked','mode'))
P451_RETRIEVAL={'path': '/home/temmie/dev/android-native-init-lab/workspace/private/outputs/s22plus-autoboot-evidence-p451-h0-20261021-1/retrieval-1/result.json', 'size': 7746, 'sha256': '3d1394dccd154902cde308471593c14a06aa89ffc48b6c60ec67961e57cf229b'}
P447_HISTORY_CASES=tuple(action+'-p445-early' for action in ('missing','changed','linked','mode'))+('unexpected-p445-runtime',)
P447_RETRIEVAL=dict(path=str(ROOT/'workspace/private/outputs/s22plus-autoboot-evidence-p447-h0-20261021-1/retrieval-1/result.json'),
    size=5276,sha256='45ceb039062ae9ecaf7e50171b68c6a37b254f6acbfb062b7d0419563183ee06')
PHASE_RETRIEVAL=dict(path=str(ROOT/'workspace/private/outputs/s22plus-autoboot-evidence-p444-h0-20261020-1/retrieval-1/result.json'),
    size=7462,sha256='51f0de292ecb49e077a10b3c91347e6c64ce2076251ec9acc5e6f5070a6ec2a9')
IDLE_VENDOR_BOOT=dict(path=str(ROOT/'workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/raw/vendor_boot.img'),
    size=100663296,sha256='096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7')
TRANSITION_CASES=('trace-file-close','trace-parent-close','trace-root-close','trace-unmount','trace-ro',
    'trace-post-super','trace-receipt','trace-second-admission','trace-root-activate',
    'trace-move-dev','trace-switch-exec','trace-witness','trace-init-exec','trace-init-identity',
    'trace-logger-loss','trace-pending')
HISTORY_CASES=('missing-second-history','linked-second-history','extra-runtime-history','boot-count-leading-zero')
RUNTIME_HISTORY_CASES=('missing-runtime-history','changed-runtime-history','linked-runtime-history','mode-runtime-history')
RCS_CASES=('rcs-record-fsync','rcs-close-range','rcs-exec','rcs-wait','rcs-sleep',
    'rcs-pending-record','rcs-pending-child')
WATCHDOG_HISTORY_CASES=tuple(action+'-p437-'+kind for kind in ('early','runtime')
    for action in ('missing','changed','linked','mode'))
PHASE_HISTORY_CASES=tuple(action+'-p441-'+kind for kind in ('early','runtime')
    for action in ('missing','changed','linked','mode'))


def cases(transition=False,rcs=False,watchdog=False,phase=False,single_cpu=False,post_p447=False,script_channel=False,minimal=False,reboot=False,cron=False):
    require(not rcs or transition,'rcS observer requires the transition variant')
    require(not watchdog or rcs,'watchdog observer requires the rcS variant')
    require(not phase or watchdog,'phase observer requires the complete predecessor history')
    require(not single_cpu or watchdog and not phase,'single CPU requires retained watchdog history without phase instrumentation')
    require(not post_p447 or single_cpu,'P447 history requires single CPU selection')
    require(not minimal or script_channel,'minimal workload requires its script channel selection')
    require(not reboot or minimal,'reboot requires minimal automatic startup')
    cron_variant(cron)
    require(not cron or reboot,'cron requires the two-boot selection')
    require(not script_channel or post_p447,'script channel requires the current single CPU history')
    if minimal:return ('normal','dirty','changed-history','foreign-file','existing-early','existing-runtime',
        'trace-second-admission','changed-receipt','fd-leak','module-error','network-absent',
        'singlecpu-unlimited',*SINGLECPU_FAULTS,*SCRIPT_FAULTS,*minimal_spec.FAULTS,*minimal_spec.HISTORY_CASES)
    if single_cpu:return SINGLECPU_CASES+(P447_HISTORY_CASES if post_p447 else ())+(P451_HISTORY_CASES+SCRIPT_FAULTS if script_channel else ())
    return CASES+(HISTORY_CASES+TRANSITION_CASES if transition else ())+(
        RUNTIME_HISTORY_CASES+RCS_CASES if rcs else ())+(WATCHDOG_HISTORY_CASES if watchdog else ())+(
        PHASE_HISTORY_CASES if phase else ())
AUTO_RETRIEVAL=dict(path=str(ROOT/'workspace/private/outputs/s22plus-autoboot-evidence-p433-h0-20261018-1/retrieval-1/result.json'),
    size=5326,sha256='fd8876ccfec4207437aca4fb214b8219eeea2cbc1f3bff3fe01ba0d331445a0b')
RUNTIME_RETRIEVAL=dict(path=str(ROOT/'workspace/private/outputs/s22plus-autoboot-evidence-p436-h0-20261018-1/retrieval-1/result.json'),
    size=7473,sha256='bf4c7e15eead496e9483b83340b9c037609c1d2f4ee46c01528712d2d9b35a37')


def observer(rcs=False,watchdog=False,phase=False,single_cpu=False,post_p447=False,script_channel=False,minimal=False,reboot=False,cron=False):
    require(not watchdog or rcs,'watchdog observer requires rcS observation')
    require(not phase or watchdog,'phase observer requires the watchdog predecessor')
    require(not single_cpu or watchdog and not phase,'single CPU requires retained watchdog history without phase instrumentation')
    require(not post_p447 or single_cpu,'P447 history requires single CPU selection')
    require(not minimal or script_channel,'minimal workload requires its script channel selection')
    require(not reboot or minimal,'reboot requires minimal automatic startup')
    cron_variant(cron)
    require(not cron or reboot,'cron requires the two-boot selection')
    require(not script_channel or post_p447,'script channel requires the current single CPU history')
    return CRON_CONFIG_OBSERVER if cron=='config' else CRON_OBSERVER if cron else REBOOT_OBSERVER if reboot else MINIMAL_OBSERVER if minimal else SCRIPT_OBSERVER if script_channel else SINGLECPU_P447_OBSERVER if post_p447 else SINGLECPU_OBSERVER if single_cpu else PHASE_OBSERVER if phase else WATCHDOG_OBSERVER if watchdog else RCS_OBSERVER if rcs else TRANSITION_OBSERVER


def variants(built):
    selected=built.get('transition_observer')
    watchdog=selected in (WATCHDOG_OBSERVER,PHASE_OBSERVER,SINGLECPU_OBSERVER,SINGLECPU_P447_OBSERVER,SCRIPT_OBSERVER,MINIMAL_OBSERVER,REBOOT_OBSERVER,CRON_OBSERVER,CRON_CONFIG_OBSERVER)
    return selected is not None,watchdog or selected==RCS_OBSERVER,watchdog


def watchdog_history():
    """The two complete P437 files authenticated by the closed P440 reader."""
    return closed_pair_history(WATCHDOG_RETRIEVAL,'P437')


def phase_history():
    """The two complete P441 files authenticated by the closed P444 reader."""
    return closed_pair_history(PHASE_RETRIEVAL,'P441')


def phase_selected(built):
    return built.get('transition_observer')==PHASE_OBSERVER


def singlecpu_selected(built):
    policy=built.get('cpu_policy')
    require(policy in (None,SINGLECPU_POLICY),'unselected CPU policy')
    if policy is not None:
        require(built.get('transition_observer') in (SINGLECPU_OBSERVER,SINGLECPU_P447_OBSERVER,SCRIPT_OBSERVER,MINIMAL_OBSERVER,REBOOT_OBSERVER,CRON_OBSERVER,CRON_CONFIG_OBSERVER) and
            built.get('idle_policy')=='cpuidle-off','single CPU requires its reviewed history and idle selection')
    else:require(built.get('transition_observer') not in (SINGLECPU_OBSERVER,SINGLECPU_P447_OBSERVER,SCRIPT_OBSERVER,MINIMAL_OBSERVER,REBOOT_OBSERVER,CRON_OBSERVER,CRON_CONFIG_OBSERVER),'single CPU declaration lacks CPU selection')
    return policy is not None


def post_p447_selected(built):
    selected=built.get('transition_observer') in (SINGLECPU_P447_OBSERVER,SCRIPT_OBSERVER,MINIMAL_OBSERVER,REBOOT_OBSERVER,CRON_OBSERVER,CRON_CONFIG_OBSERVER)
    require(not selected or singlecpu_selected(built),'P447 history requires single CPU selection')
    return selected


def script_channel_selected(built):
    selected=built.get('transition_observer') in (SCRIPT_OBSERVER,MINIMAL_OBSERVER,REBOOT_OBSERVER,CRON_OBSERVER,CRON_CONFIG_OBSERVER)
    require(not selected or singlecpu_selected(built),'script channel requires single CPU selection')
    return selected


def minimal_selected(built):
    selected=built.get('transition_observer') in (MINIMAL_OBSERVER,REBOOT_OBSERVER,CRON_OBSERVER,CRON_CONFIG_OBSERVER)
    require(not selected or script_channel_selected(built),'minimal workload lacks its channel selection')
    return selected



def reboot_selected(built):
    return built.get('transition_observer') in (REBOOT_OBSERVER,CRON_OBSERVER,CRON_CONFIG_OBSERVER)

def cron_selected(built):
    return 'config' if cron_config_selected(built) else built.get('transition_observer')==CRON_OBSERVER

def cron_config_selected(built):
    return built.get('transition_observer')==CRON_CONFIG_OBSERVER

def cron_variant(value):
    require(value is False or value is True or type(value) is str and value=='config','unselected cron variant')
    return cron_config_spec if value=='config' else cron_spec

def script_spec(minimal=False):
    return minimal_spec if minimal else phase_spec


def p452_history():
    result=read(verify(P455_RETRIEVAL))
    writer=read(verify(result['writer_build']));artifact=read(verify(result['writer_artifact']))
    acquired=read(verify(result['reader_result']))['proof']['root_evidence']
    require(artifact['build']==result['writer_build'] and writer['virtual'] is False and
        writer['namespace']==SCRIPT_NAMESPACE and writer['version']==SCRIPT_VERSION and
        writer['transition_observer']==SCRIPT_OBSERVER and
        writer['run_id']==result['proof']['early']['proof']['run_id_hex'] and
        result['source_view_clean'] is True and result['reader_journal_replayed'] is False and
        acquired['source_view_clean'] is True and acquired['superblock']==dict(state=1,recover=0,orphan=0),
        'P452 history physical producer or clean reader differs')
    return closed_pair_history(P455_RETRIEVAL,'P452')


def singlecpu_history(post_p447=False,script_channel=False,minimal=False,reboot=False,cron=False):
    require(not minimal or script_channel,'minimal workload requires its script channel selection')
    require(not reboot or minimal,'reboot requires minimal automatic startup')
    cron_variant(cron)
    require(not cron or reboot,'cron requires the two-boot selection')
    require(not script_channel or post_p447,'current script history requires P447 history')
    return phase_history()+([p445_history()] if post_p447 else [])+(p448_history() if script_channel else [])+(p452_history() if minimal else [])+(reboot_spec.history() if reboot else [])+(cron_spec.history() if cron else [])+(cron_config_spec.history() if cron=='config' else [])


def p448_history():
    result=read(verify(P451_RETRIEVAL))
    writer=read(verify(result['writer_build']));artifact=read(verify(result['writer_artifact']))
    require(artifact['build']==result['writer_build'] and writer['virtual'] is False and
        writer['namespace']==SINGLECPU_P447_NAMESPACE and writer['transition_observer']==SINGLECPU_P447_OBSERVER and
        writer['run_id']==result['proof']['early']['proof']['run_id_hex'] and
        result['source_view_clean'] is True,'P448 history physical producer or clean source differs')
    return closed_pair_history(P451_RETRIEVAL,'P448')


def p445_history():
    """Only the complete early file authenticated by the closed P447 reader."""
    result=read(verify(P447_RETRIEVAL));joined=result['proof'];early=joined['early']['proof']
    require(result['schema']=='s22plus-debian-autoboot-retrieval-h0-v1' and
        result['status']=='PASS_AUTHENTICATED_LOCAL_PROGRESS' and
        result['reader_android_healthy'] is True and result['writer_android_healthy'] is True and
        result['source_view_clean'] is True and result['reader_journal_replayed'] is False and
        joined['early']['status']=='AUTHENTICATED' and early['pre_unmount_complete'] is True and
        early['tail_error'] is None and len(early['records'])==14 and
        joined['runtime']==dict(status='NOT_CAPTURED') and joined['join']==dict(status='UNAVAILABLE'),
        'P445 historical authentication differs')
    for label in ('writer_closed','reader_closed'):
        require(read(verify(result[label]))['terminal_state']=='ANDROID_CLOSED_HEALTHY',
            'P445 historical closure differs')
    writer=read(verify(result['writer_build']));artifact=read(verify(result['writer_artifact']))
    require(artifact['build']==result['writer_build'] and writer['virtual'] is False and
        writer['namespace']==PHASE_NAMESPACE and writer['run_id']==early['run_id_hex'] and
        phase_selected(writer),'P445 historical physical producer differs')
    acquired=read(verify(result['reader_result']))['proof']['root_evidence']
    require(acquired['partition_readonly'] is True and acquired['mounted'] is False and
        acquired['persistent_writes'] is False and acquired['source_view_clean'] is True and
        acquired['superblock']==dict(state=1,recover=0,orphan=0) and len(acquired['files'])==2,
        'P445 historical read scope differs')
    body=verify(result['raw']['early']).read_bytes();observed,missing=acquired['files']
    path='var/lib/lab/s22-early-'+early['run_id_hex'];digest=hashlib.sha256(body).hexdigest()
    require(len(body)==10972==early['raw']['size']==early['valid_prefix_bytes'] and
        digest==early['raw']['sha256'] and observed['path']==path and observed['status']=='READ' and
        (observed['mode'],observed['uid'],observed['gid'],observed['links'])==(0o100600,0,0,1) and
        observed['size']==observed['captured']==len(body) and observed['offset']==observed['error']==0 and
        observed['sha256']==digest and bytes.fromhex(observed['raw_hex'])==body and
        missing['path']=='var/lib/lab/s22-evidence-'+early['run_id_hex'] and
        missing['status']=='ABSENT_IN_HOME_VIEW' and missing['captured']==0,
        'P445 historical bytes or metadata differ')
    return dict(path=path,mode=0o100600,uid=0,gid=0,nlink=1,size=len(body),sha256=digest,source=result['raw']['early'])


def closed_pair_history(receipt,label,*,expected_sizes=(10972,1024)):
    """One sealed complete pair; this does not admit arbitrary historical paths."""
    result=read(verify(receipt));joined=result['proof']
    require(result['schema']=='s22plus-debian-autoboot-retrieval-h0-v1' and
        result['status']=='PASS_AUTHENTICATED_LOCAL_PROGRESS' and
        result['reader_android_healthy'] is True and result['writer_android_healthy'] is True and
        joined['join']==dict(status='MATCH',boot_matches=True,nonce_matches=True) and
        joined['early']['status']==joined['runtime']['status']=='AUTHENTICATED',
        label+' historical authentication or boot join differs')
    for closure in ('writer_closed','reader_closed'):
        require(read(verify(result[closure]))['terminal_state']=='ANDROID_CLOSED_HEALTHY',
            label+' '+closure+' historical closure differs')
    early=joined['early']['proof'];runtime=joined['runtime']['proof']
    require(early['pre_unmount_complete'] is True and early['tail_error'] is None and
        runtime['local_init_observed'] is True and runtime['automatic_start'] is True and
        runtime['complete_framing'] is True and runtime['tail_error'] is None and
        early['run_id_hex']==runtime['run_id_hex'],label+' historical records are incomplete')
    acquired=read(verify(result['reader_result']))['proof']['root_evidence']
    require(acquired['partition_readonly'] is True and acquired['mounted'] is False and
        acquired['persistent_writes'] is False and len(acquired['files'])==2,
        label+' historical acquisition scope differs')
    rows=[]
    for index,(kind,prefix,proof,size) in enumerate((
            ('early','s22-early-',early,expected_sizes[0]),('runtime','s22-evidence-',runtime,expected_sizes[1]))):
        body=verify(result['raw'][kind]).read_bytes();observed=acquired['files'][index]
        path='var/lib/lab/'+prefix+proof['run_id_hex'];digest=hashlib.sha256(body).hexdigest()
        require(len(body)==size==proof['raw']['size']==proof['valid_prefix_bytes'] and
            digest==proof['raw']['sha256'] and observed['path']==path and observed['status']=='READ' and
            (observed['mode'],observed['uid'],observed['gid'],observed['links'])==(0o100600,0,0,1) and
            observed['size']==observed['captured']==size and observed['offset']==observed['error']==0 and
            observed['sha256']==digest and bytes.fromhex(observed['raw_hex'])==body,
            label+' historical bytes or metadata differ')
        rows.append(dict(path=path,mode=0o100600,uid=0,gid=0,nlink=1,size=size,
            sha256=digest,source=result['raw'][kind]))
    return rows


def boot_carrier(original,built):
    """Select exact idle/CPU arguments; all other carrier bytes stay fixed."""
    import s22plus_boot_verify as boot
    _,_,watchdog=variants(built);single_cpu=singlecpu_selected(built)
    if not watchdog:
        require('idle_policy' not in built and 'watchdog_history' not in built,
            'legacy producer cannot select watchdog/idle controls')
        return original
    require(built['idle_policy'] in IDLE_POLICIES,'unselected idle policy')
    parsed=boot.parse_boot_v4(original);command=parsed.header['cmdline']
    vendor_pin=dict(IDLE_VENDOR_BOOT,path=str(Path(IDLE_VENDOR_BOOT['path']).resolve(strict=True)))
    vendor=boot.parse_vendor_boot_v4(verify(vendor_pin,maximum=128*1024**2).read_bytes())
    require(not any(token.split('=',1)[0].startswith(('cpuidle.','idle'))
        for token in (command+' '+vendor.cmdline).split()),'retained idle command line conflicts')
    require(original[44:1580]==command.encode().ljust(1536,b'\0'),'retained command-line padding differs')
    if single_cpu:
        tokens=(command+' '+vendor.cmdline).split()
        require('--' not in tokens and not any(token.split('=',1)[0] in
            ('maxcpus','nr_cpus','nosmp') for token in tokens),'retained CPU command line conflicts')
    if built['idle_policy']=='retained-default':return original
    command=(command+(' ' if command else '')+'cpuidle.off=1'+(' maxcpus=1' if single_cpu else '')).encode()
    require(len(command)<1536,'selected idle command line does not fit')
    return original[:44]+command.ljust(1536,b'\0')+original[1580:]


def runtime_history():
    result=read(verify(RUNTIME_RETRIEVAL));old=read(verify(AUTO_RETRIEVAL));joined=result['proof']
    proof=joined['runtime']['proof']
    require(result['schema']=='s22plus-debian-autoboot-retrieval-h0-v1' and
        result['status']=='PASS_AUTHENTICATED_LOCAL_PROGRESS' and
        result['reader_android_healthy'] is True and result['writer_android_healthy'] is True and
        result['writer_artifact']==old['writer_artifact'] and result['writer_closed']==old['writer_closed'] and
        joined['join']==dict(status='MATCH',boot_matches=True,nonce_matches=True) and
        joined['runtime']['status']=='AUTHENTICATED' and proof['local_init_observed'] is True and
        proof['automatic_start'] is True and proof['complete_framing'] is True and proof['tail_error'] is None and
        proof['run_id_hex']==old['proof']['early']['proof']['run_id_hex'],
        'runtime historical authentication or writer join differs')
    for label in ('writer_closed','reader_closed'):
        require(read(verify(result[label]))['terminal_state']=='ANDROID_CLOSED_HEALTHY',
            'runtime historical closure differs')
    require(verify(result['raw']['early']).read_bytes()==verify(old['raw']['early']).read_bytes(),
        'runtime retrieval changed the historical early file')
    raw=verify(result['raw']['runtime']).read_bytes()
    require(len(raw)==proof['raw']['size']==proof['valid_prefix_bytes'] and 256<len(raw)<=15616 and
        hashlib.sha256(raw).hexdigest()==proof['raw']['sha256'],'runtime historical bytes differ')
    return dict(path='var/lib/lab/s22-evidence-'+proof['run_id_hex'],mode=0o100600,uid=0,gid=0,
        nlink=1,size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),source=result['raw']['runtime'])


def additional_history():
    result=read(verify(AUTO_RETRIEVAL));proof=result['proof']['early']['proof']
    require(result['schema']=='s22plus-debian-autoboot-retrieval-h0-v1' and
        result['status']=='PASS_AUTHENTICATED_LOCAL_PROGRESS' and
        result['reader_android_healthy'] is True and result['writer_android_healthy'] is True and
        proof['pre_unmount_complete'] is True and proof['tail_error'] is None,
        'automatic historical qualification differs')
    for label in ('writer_closed','reader_closed'):
        require(read(verify(result[label]))['terminal_state']=='ANDROID_CLOSED_HEALTHY',
            'automatic historical closure differs')
    raw=verify(result['raw']['early']).read_bytes()
    require(len(raw)==proof['raw']['size']==proof['valid_prefix_bytes'] and
        hashlib.sha256(raw).hexdigest()==proof['raw']['sha256'] and len(raw)<=16384,
        'automatic historical bytes differ')
    return dict(path='var/lib/lab/s22-early-'+proof['run_id_hex'],mode=0o100600,uid=0,gid=0,
        nlink=1,size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),source=result['raw']['early'])


def histories(transition=False,rcs=False,watchdog=False,phase=False,single_cpu=False,post_p447=False,script_channel=False,minimal=False,reboot=False,cron=False):
    require(not rcs or transition,'runtime history requires the reviewed rcS selection')
    require(not watchdog or rcs,'P437 history requires the watchdog selection')
    require(not phase or watchdog,'P441 history requires the phase selection')
    require(not single_cpu or watchdog and not phase,'P441 history requires the selected single CPU variant')
    require(not post_p447 or single_cpu,'P447 history requires single CPU selection')
    require(not minimal or script_channel,'minimal workload requires its script channel selection')
    require(not reboot or minimal,'reboot requires minimal automatic startup')
    cron_variant(cron)
    require(not cron or reboot,'cron requires the two-boot selection')
    require(not script_channel or post_p447,'script channel requires the current single CPU history')
    return [history()]+([additional_history()] if transition else [])+([runtime_history()] if rcs else [])+(
        watchdog_history() if watchdog else [])+(singlecpu_history(post_p447,script_channel,minimal,reboot,cron) if single_cpu else phase_history() if phase else [])


def history():
    result=read(verify(RETRIEVAL));proof=result['proof']
    require(result['status']=='PASS_PERSISTED_EARLY_PID1_PRE_UNMOUNT' and
        result['reader_android_healthy'] is True and result['writer_android_healthy'] is True and
        proof['pre_unmount_complete'] is True,'historical record qualification differs')
    for label in ('writer_closed','reader_closed'):
        require(read(verify(result[label]))['terminal_state']=='ANDROID_CLOSED_HEALTHY',
            'historical operation closure differs')
    raw=verify(result['raw']).read_bytes()
    require(len(raw)==proof['raw']['size'] and hashlib.sha256(raw).hexdigest()==proof['raw']['sha256'] and
        len(raw)<=16384,'historical record bytes differ')
    return dict(path='var/lib/lab/s22-evidence-'+proof['run_id_hex'],mode=0o100600,uid=0,gid=0,
        nlink=1,size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),source=result['raw'])


def comparison_table(old,count,transition=False,rcs=False,watchdog=False,phase=False,single_cpu=False,post_p447=False,script_channel=False,minimal=False,reboot=False,cron=False):
    """Add only the exact previously retrieved file to a verified base table."""
    require(old[:8]==b'S22RI01\0' and struct.unpack_from('<I',old,8)[0]==count,'base table identity differs')
    rows={};at=12
    for _ in range(count):
        start=at;plen,llen=struct.unpack_from('<HH',old,at+20);at+=57
        name=old[at:at+plen];at+=plen+llen
        require(name not in rows,'duplicate immutable path');rows[name]=old[start:at]
    require(at==len(old),'immutable table framing differs')
    for item in histories(transition,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot,cron):
        name=item['path'].encode();require(name not in rows,'history overlaps archive')
        rows[name]=struct.pack('<IIIQHH',item['mode'],item['uid'],item['gid'],item['size'],len(name),0)+\
            bytes.fromhex(item['sha256'])+b'\0'+name
    return b'S22RI01\0'+struct.pack('<I',len(rows))+b''.join(rows[n] for n in sorted(rows))


def retained_comparison(transition=False,rcs=False,watchdog=False,phase=False,single_cpu=False,post_p447=False,script_channel=False,minimal=False,reboot=False,cron=False):
    # Reuse the hash-pinned historical base table without importing an old
    # installer or H0 builder into the reachable device-session owner.
    result=read(verify(RETRIEVAL));artifact=read(verify(result['writer_artifact']))
    built=read(verify(artifact['build']));admission=built['admission']
    old=verify(admission['table']).read_bytes()
    return (comparison_table(old,admission['table_count'],transition,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot,cron),
        admission['table_count']+len(histories(transition,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot,cron)),admission['boot_count'])


def admission_headers(run,transition=False,rcs=False,watchdog=False,phase=False,single_cpu=False,post_p447=False,script_channel=False,minimal=False,reboot=False,cron=False):
    """H0 generator: verify the current archive-derived table against history."""
    import s22plus_native_journal_recovery_h0 as admission
    selected=admission.headers(run);table=comparison_table(selected['table'],selected['count'],transition,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot,cron)
    count=selected['count']+len(histories(transition,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot,cron))
    require((table,count,selected['boot'])==retained_comparison(transition,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot,cron),'archive/history table differs')
    selected.update(table=table,count=count,history=history())
    if transition:selected['additional_history']=additional_history()
    if rcs:selected['runtime_history']=runtime_history()
    if watchdog:selected['watchdog_history']=watchdog_history()
    if phase:selected['phase_history']=phase_history()
    if single_cpu:selected['current_history']=singlecpu_history(post_p447,script_channel,minimal,reboot,cron)
    selected['headers']['s22plus_native_root_inspect_seal_v1.h']=admission.base.header(table,selected['count'],selected['boot'])
    selected['headers']['s22plus_native_journal_mutable_seal_v1.h']=mutable_header(transition,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot,cron)
    return selected


def mutable_header(transition=False,rcs=False,watchdog=False,phase=False,single_cpu=False,post_p447=False,script_channel=False,minimal=False,reboot=False,cron=False):
    original=handoff.mutable_header()
    if reboot:
        extra=''.join('{'+json.dumps(path)+f',{mode}U,{gid}U,{minimum}ULL,{maximum}ULL,{int(archive)}U,{int(counter)}U'+'},\n'
            for path,mode,gid,minimum,maximum,archive,counter in reboot_spec.mutable_rows())
        require(original.endswith('};\n'),'mutable declaration terminator differs')
        original=original[:-3]+extra+'};\n'
    needle='"var/lib/lab/boot-count",33188U,0U,2ULL,2ULL'
    require(original.count(needle)==1,'boot-count declaration differs')
    paths=('static const char *const ab_history_paths[]={'+
        ','.join(json.dumps(item['path']) for item in histories(True,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot,cron))+'};\n') if transition else (
        'static const char ab_history_path[]='+json.dumps(history()['path'])+';\n')
    return (original.replace(needle,'"var/lib/lab/boot-count",33188U,0U,2ULL,6ULL')+paths).encode()


def payloads(run,*,virt=False,single_cpu=False,minimal=False,reboot=False,cron=False):
    init,assets=handoff.payloads(virt=virt);assets=dict(assets)
    if not virt:assets['usb']=(ROOT/'workspace/public/src/debian/s22plus_v1/device/lab-usb-autoboot').read_bytes()
    # Ordinary rc2 invokes this one RAM overlay once, before sshd. The original
    # installed script and root archive are never modified.
    assets['defer-usb']=assets['usb']
    script=assets['qualify'];needle=b' health)\n'
    require(script.count(needle)==1,'fixed qualification command changed')
    # The host separately authenticates all records. This shell only exposes
    # fixed bounded files; no caller-supplied filename or command is accepted.
    evidence=f''' evidence)
  test -f /run/s22-debian/autoboot-complete
  test "$(readlink /proc/1/exe)" = /usr/sbin/init
  test "$(stat -c %d /)" = "$(stat -Lc %d /proc/1/root)"
  printf 'S22_AUTO_EVIDENCE_V1\\n'
  cat /proc/sys/kernel/random/boot_id
  for file in /run/s22-debian/early /var/lib/lab/s22-evidence-{run} /run/s22-debian/transition; do
   test -f "$file" && test ! -L "$file"
   test "$(stat -c %h "$file")" = 1
   test "$(stat -c %u:%g "$file")" = 0:0
   size=$(stat -c %s "$file")
   case "$file" in */transition) maximum=262144;; *) maximum=16384;; esac
   test "$size" -gt 0 && test "$size" -le "$maximum"
   base64 -w0 "$file"
   printf '\\n'
  done
  printf 'S22_AUTO_EVIDENCE_END\\n'
  ;;
'''.encode()
    assets['qualify']=script.replace(needle,evidence+needle)
    if single_cpu:
        marker=b"  printf 'DEBIAN_HEALTH_PASS\\n'\n"
        require(assets['qualify'].count(marker)==1,'health completion marker differs')
        assets['qualify']=assets['qualify'].replace(marker,
            b"  IFS= read -r online < /sys/devices/system/cpu/online\n"
            b"  test \"$online\" = 0\n"
            b"  printf 'S22_SINGLECPU_ONLINE %s\\n' \"$online\"\n"
            b"  IFS=' ' read -r uptime idle < /proc/uptime\n"
            b"  printf 'S22_SINGLECPU_UPTIME %s\\n' \"$uptime\"\n"+marker)
    if minimal:assets['rc-minimal']=minimal_spec.dispatcher()
    if reboot:
        require(minimal and single_cpu,'reboot requires the minimal single CPU path')
        assets['qualify']=reboot_spec.qualify(assets['qualify'],run,cron=cron)
    return init,assets


def header(namespace,version,run,*,virt=False,transition=False,rcs=False,watchdog=False,phase=False,single_cpu=False,post_p447=False,script_channel=False,minimal=False,reboot=False,cron=False):
    original=handoff.header(namespace,version,run,virt=virt)
    original=original.replace(handoff.mutable_header().encode(),mutable_header(transition,rcs,watchdog,phase,single_cpu,post_p447,script_channel,minimal,reboot,cron))
    _,old=handoff.payloads(virt=virt);_,new=payloads(run,virt=virt,single_cpu=single_cpu,minimal=minimal,reboot=reboot,cron=cron)
    def declaration(data):
        return (f'static const uint64_t dh_usb_size={len(data)}ULL;\n'+
            'static const uint8_t dh_usb_sha256[]={'+','.join(map(str,hashlib.sha256(data).digest()))+'};\n').encode()
    require(original.count(declaration(old['usb']))==1,'USB source seal differs')
    return original.replace(declaration(old['usb']),declaration(new['usb']))


class Profile:
    RESULT_KEY='debian_autoboot'
    MUTATES=True
    OBSERVATION_SECONDS=360


def image_binding(image):
    from s22plus_debian_autoboot_qualification_v1 import image_binding as qualified
    return qualified(image)


def ramdisk_payloads(selected):
    values={
        'usr/sbin/fyg8-prepare':selected['helper'],'usr/sbin/file-log':selected['writer'],
        'usr/sbin/autoboot-init':selected['entry'],'s22-switch-witness':selected['witness'],
        's22-switch-busybox':selected['busybox'],'s22-fs-e2fsck':selected['checker'],
        's22-root-inspect.table':selected['table']}
    values.update({'s22-debian-'+name:row for name,row in selected['assets'].items()})
    return values
