"""Finite ordinary-reboot selection; data and H0 generation, no device calls."""
import hashlib
import json
import re
from pathlib import Path

from s22plus_native_records_v3 import read,require,verify

ROOT=Path(__file__).resolve().parents[5]
NAMESPACE='p458'
VERSION='v0.19.0-rc.0'
POLICY='docs/operations/S22PLUS_DEBIAN_REBOOT_V1.md'
HISTORY_SELECTION='post-autoboot-p457-reboot-v1'
EARLY_DOMAIN=b'S22PLUS-FYG8-DEBIAN-REBOOT-EARLY-v1'
DURABLE_DOMAIN=b'S22PLUS-FYG8-DEBIAN-REBOOT-DURABLE-v1'
REBOOT_INTENT,SHUTDOWN_INTENT=9,10
EARLY_VERSION=4
DURABLE_REVISION=7
PHASES=(1,2)
ROOT_CASES=('changed-current-receipt','baseline-mismatch','dirty','changed-p456-runtime','foreign-file','existing-early','existing-runtime',
    'rotation-mode','rotation-link','rotation-size','rotation-extra','marker-changed','marker-mode',
    'boot-count-overflow','prior-early-missing','prior-runtime-changed','prior-runtime-incomplete',
    'prior-runtime-mode','second-file-exists','second-count-mismatch','third-start','clean-error-retry')
FAULTS=('reboot-clean-error',)
EVIDENCE_MAXIMUM=450000
P457_RETRIEVAL=dict(path=str(ROOT/'workspace/private/outputs/s22plus-autoboot-persistence-p457-h0-20261024-1/retrieval-1/result.json'),
    size=11561,sha256='a3bdad174f33384e8bb4e92699064288763fa30e332d20b824c9bacca91f9d6b')
ROTATIONS=('var/log/dmesg.0',*(f'var/log/dmesg.{n}.gz' for n in range(1,5)))
# gzip can add a small header/trailer and incompressible-block overhead.
ROTATION_MAXIMUM=1048576+16384
HISTORY_CASES=tuple(action+'-p456-'+kind for kind in ('early','runtime')
    for action in ('missing','changed','linked','mode'))
SHUTDOWN_MARKER_SHA256='dcf5a734dee3f28011282eef015d8b1698f152f9649cad36f8fbeb0cc5da4005'


def paths(run,phase):
    require(type(run) is str and re.fullmatch('[0-9a-f]{32}',run) and
        type(phase) is int and phase in PHASES,'reboot run/phase differs')
    return {kind:f'var/lib/lab/s22-{prefix}-{run}-b{phase}'
            for kind,prefix in (('early','early'),('runtime','evidence'))}


def count(value):
    require(type(value) is int and 0<=value<=65531,'sealed mount count would wrap')
    return value


def declaration(run,mount_count):
    return dict(schema='s22plus-debian-reboot-selection-v1',initial_mount_count=count(mount_count),
        phases=[dict(phase=p,paths=paths(run,p),early_before=mount_count+2*(p-1),
                     installed_before=mount_count+2*p-1,installed_after=mount_count+2*p) for p in PHASES],
        early_version=EARLY_VERSION,durable_revision=DURABLE_REVISION,
        reboot_intents=1,shutdown_intents=1,per_boot_deadline_ms=300000,
        observation_seconds_per_boot=360,second_window_origin='durable-reboot-intent',
        writable_lifetimes=4,ordinary_reboots=1,physical_boot_count_proved=False)


def seal(run,mount_count):
    from s22plus_debian_evidence_v1 import wire_seal
    from s22plus_debian_handoff_profile_v1 import root_files,INIT
    selected=declaration(run,mount_count)
    text=['#ifndef S22PLUS_DEBIAN_REBOOT_SEAL_V1_H',
        '#define S22PLUS_DEBIAN_REBOOT_SEAL_V1_H',
        f'#define RB_BASE_COUNT {selected["initial_mount_count"]}U',
        f'#define RB_REBOOT_INTENT {REBOOT_INTENT}U',
        f'#define RB_SHUTDOWN_INTENT {SHUTDOWN_INTENT}U',
        wire_seal().decode(),
        'static const uint8_t rb_shutdown_sha256[]={'+','.join(map(str,bytes.fromhex(shutdown_marker()['sha256'])))+'};',
        'static const uint8_t rb_init_sha256[]={'+','.join(map(str,hashlib.sha256(root_files()[INIT]).digest()))+'};',
        'static const char *const rb_paths[2][2]={']
    text += ['{'+','.join(json.dumps(row['paths'][kind]) for kind in ('early','runtime'))+'},'
             for row in selected['phases']]
    return ('\n'.join(text+['};','#endif'])+'\n').encode()


def history():
    from s22plus_debian_autoboot_profile_v1 import closed_pair_history,MINIMAL_NAMESPACE,MINIMAL_VERSION,MINIMAL_OBSERVER
    result=read(verify(P457_RETRIEVAL));writer=read(verify(result['writer_build']))
    artifact=read(verify(result['writer_artifact']))
    acquired=read(verify(result['reader_result']))['proof']['root_evidence']
    require(writer['namespace']==MINIMAL_NAMESPACE and writer['version']==MINIMAL_VERSION and
        writer['transition_observer']==MINIMAL_OBSERVER and writer['virtual'] is False and
        artifact['build']==result['writer_build'] and result['source_view_clean'] is True and
        result['reader_journal_replayed'] is False and acquired['source_view_clean'] is True and
        acquired['superblock']==dict(state=1,recover=0,orphan=0) and
        result['proof']['runtime']['proof']['local_runtime_proved'] is True,
        'P456 completed physical pair/clean P457 reader differs')
    return closed_pair_history(P457_RETRIEVAL,'P456',expected_sizes=(10972,3456))


def mutable_rows():
    return tuple((name,0o100640,4,0,1048576 if name.endswith('.0') else ROTATION_MAXIMUM,False,False)
                 for name in ROTATIONS)


def shutdown_marker():
    """Restrictive producer-derived expectation, not a retrieved-history row."""
    import device_action_raw_capture_v1 as raw
    result=read(verify(P457_RETRIEVAL));terminal=read(verify(result['writer_terminal']))
    require(terminal['terminal_state']=='ANDROID_CLOSED_HEALTHY' and
        terminal['debian_autoboot']['ssh_access_proved'] is True,'P456 terminal lacks SSH proof')
    health=terminal['debian_autoboot']['ssh_health'];capture=raw.load_handle(verify(health['capture']))
    raw.require_success(capture)
    boots=re.findall(rb'^boot_id=([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})$',
        raw.read_stdout(capture,maximum=65536),re.M)
    require(len(boots)==1 and hashlib.sha256(boots[0]).hexdigest()==health['boot_id_sha256']==
        result['proof']['early']['proof']['kernel_boot_identity_sha256'],
        'P456 raw SSH boot does not join authenticated early evidence')
    body=boots[0]+b'\n';require(hashlib.sha256(body).hexdigest()==SHUTDOWN_MARKER_SHA256,
        'producer-derived shutdown marker differs from independently reviewed bytes')
    built=read(verify(result['writer_build']));script=verify(built['assets']['qualify']).read_bytes()
    require(script.count(b'(set -C; cat /proc/sys/kernel/random/boot_id > /var/lib/lab/shutdown-start)')==1 and
        b'sync -f /\n  /sbin/shutdown -h now\n' in script,'P456 sealed shutdown producer differs')
    operation=verify(terminal['operation_record']).parent
    accepted=raw.load_handle(operation/'io-debian-shutdown/shutdown.capture.json');raw.require_success(accepted)
    require(raw.read_stdout(accepted,maximum=65536)==b'DEBIAN_SHUTDOWN_REQUEST_ACCEPTED\n',
        'P456 shutdown was not accepted by its actual fixed command')
    return dict(path='var/lib/lab/shutdown-start',mode=0o100644,uid=0,gid=0,nlink=1,size=37,
        sha256=SHUTDOWN_MARKER_SHA256,optional=True,source_kind='P456_FIXED_PRODUCER_AND_RAW_SSH_BOOT',
        presence_previously_observed=False,metadata_previously_observed=False)


def qualify(script,run):
    """Fixed forced-command vocabulary; no new standalone persistent marker."""
    first,second=paths(run,1),paths(run,2)
    function=f'''rb_phase() {{
  phase=$(/run/s22-debian/hook phase)
  case "$phase" in 1|2) ;; *) exit 65;; esac
}}
rb_evidence() {{
  rb_phase
  test -f /run/s22-debian/autoboot-complete
  printf 'S22_REBOOT_EVIDENCE_V1\\nphase=%s\\n' "$phase"
  cat /proc/sys/kernel/random/boot_id
  case "$phase" in
   1) set -- /run/s22-debian/early /{first['runtime']} /run/s22-debian/transition;;
   2) set -- /run/s22-debian/early /{second['runtime']} /run/s22-debian/transition /{first['early']} /{first['runtime']};;
  esac
  for file in "$@"; do
   test -f "$file" && test ! -L "$file"
   test "$(stat -c %h "$file")" = 1
   test "$(stat -c %u:%g "$file")" = 0:0
   size=$(stat -c %s "$file")
   case "$file" in */transition) maximum=262144;; *) maximum=16384;; esac
   test "$size" -gt 0 && test "$size" -le "$maximum"
   base64 -w0 "$file"
   printf '\\n'
  done
  printf 'S22_REBOOT_EVIDENCE_END\\n'
}}
'''.encode()
    anchor=b'case "${SSH_ORIGINAL_COMMAND:-}" in\n'
    require(script.count(anchor)==1,'fixed forced-command selector differs')
    script=script.replace(anchor,function+anchor)
    begin=script.index(b' evidence)\n');end=script.index(b' health)\n',begin)
    script=script[:begin]+b' evidence)\n  rb_evidence\n  ;;\n'+script[end:]
    marker=b"  printf 'DEBIAN_HEALTH_PASS\\n'\n"
    require(script.count(marker)==1,'health terminal differs')
    script=script.replace(marker,b"  rb_phase\n  printf 'S22_REBOOT_PHASE %s\\n' \"$phase\"\n"+marker)
    begin=script.index(b' shutdown)\n');end=script.index(b' *) exit 64',begin)
    controls=b''' reboot)
  /run/s22-debian/hook reboot-intent
  rb_evidence
  /sbin/shutdown -r now
  printf 'DEBIAN_REBOOT_REQUEST_ACCEPTED\\n'
  ;;
 shutdown)
  /run/s22-debian/hook shutdown-intent
  rb_evidence
  /sbin/shutdown -h now
  printf 'DEBIAN_SHUTDOWN_REQUEST_ACCEPTED\\n'
  ;;
'''
    return script[:begin]+controls+script[end:]
