"""Automatic Debian startup data and RAM assets; no device authority."""
import hashlib
import json
import struct

import s22plus_debian_handoff_profile_v1 as handoff
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
TRANSITION_CASES=('trace-file-close','trace-parent-close','trace-root-close','trace-unmount','trace-ro',
    'trace-post-super','trace-receipt','trace-second-admission','trace-root-activate',
    'trace-move-dev','trace-switch-exec','trace-witness','trace-init-exec','trace-init-identity',
    'trace-logger-loss','trace-pending')
HISTORY_CASES=('missing-second-history','linked-second-history','extra-runtime-history','boot-count-leading-zero')


def cases(transition=False):return CASES+HISTORY_CASES+TRANSITION_CASES if transition else CASES
AUTO_RETRIEVAL=dict(path=str(ROOT/'workspace/private/outputs/s22plus-autoboot-evidence-p433-h0-20261018-1/retrieval-1/result.json'),
    size=5326,sha256='fd8876ccfec4207437aca4fb214b8219eeea2cbc1f3bff3fe01ba0d331445a0b')


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


def histories(transition=False):
    return [history()]+([additional_history()] if transition else [])


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


def comparison_table(old,count,transition=False):
    """Add only the exact previously retrieved file to a verified base table."""
    require(old[:8]==b'S22RI01\0' and struct.unpack_from('<I',old,8)[0]==count,'base table identity differs')
    rows={};at=12
    for _ in range(count):
        start=at;plen,llen=struct.unpack_from('<HH',old,at+20);at+=57
        name=old[at:at+plen];at+=plen+llen
        require(name not in rows,'duplicate immutable path');rows[name]=old[start:at]
    require(at==len(old),'immutable table framing differs')
    for item in histories(transition):
        name=item['path'].encode();require(name not in rows,'history overlaps archive')
        rows[name]=struct.pack('<IIIQHH',item['mode'],item['uid'],item['gid'],item['size'],len(name),0)+\
            bytes.fromhex(item['sha256'])+b'\0'+name
    return b'S22RI01\0'+struct.pack('<I',len(rows))+b''.join(rows[n] for n in sorted(rows))


def retained_comparison(transition=False):
    # Reuse the hash-pinned historical base table without importing an old
    # installer or H0 builder into the reachable device-session owner.
    result=read(verify(RETRIEVAL));artifact=read(verify(result['writer_artifact']))
    built=read(verify(artifact['build']));admission=built['admission']
    old=verify(admission['table']).read_bytes()
    return comparison_table(old,admission['table_count'],transition),admission['table_count']+1+int(transition),admission['boot_count']


def admission_headers(run,transition=False):
    """H0 generator: verify the current archive-derived table against history."""
    import s22plus_native_journal_recovery_h0 as admission
    selected=admission.headers(run);table=comparison_table(selected['table'],selected['count'],transition)
    count=selected['count']+1+int(transition)
    require((table,count,selected['boot'])==retained_comparison(transition),'archive/history table differs')
    selected.update(table=table,count=count,history=history())
    if transition:selected['additional_history']=additional_history()
    selected['headers']['s22plus_native_root_inspect_seal_v1.h']=admission.base.header(table,selected['count'],selected['boot'])
    selected['headers']['s22plus_native_journal_mutable_seal_v1.h']=mutable_header(transition)
    return selected


def mutable_header(transition=False):
    original=handoff.mutable_header();needle='"var/lib/lab/boot-count",33188U,0U,2ULL,2ULL'
    require(original.count(needle)==1,'boot-count declaration differs')
    paths=('static const char *const ab_history_paths[]={'+
        ','.join(json.dumps(item['path']) for item in histories(True))+'};\n') if transition else (
        'static const char ab_history_path[]='+json.dumps(history()['path'])+';\n')
    return (original.replace(needle,'"var/lib/lab/boot-count",33188U,0U,2ULL,6ULL')+paths).encode()


def payloads(run,*,virt=False):
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
    return init,assets


def header(namespace,version,run,*,virt=False,transition=False):
    original=handoff.header(namespace,version,run,virt=virt)
    original=original.replace(handoff.mutable_header().encode(),mutable_header(transition))
    _,old=handoff.payloads(virt=virt);_,new=payloads(run,virt=virt)
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
