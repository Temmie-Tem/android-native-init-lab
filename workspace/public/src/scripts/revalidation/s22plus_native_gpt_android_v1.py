"""Fixed Android GPT/statfs checks within the admitted GPT operation.

Reuse the existing tail-nine read and seven-command rooted health brackets.
All raw bytes stay private. No filesystem, partition or Android setting writes.
"""
from pathlib import Path
import re
import shlex
import uuid

import device_action_raw_capture_v1 as raw
import s22plus_native_android_storage_v1 as census
import s22plus_native_gpt_profile_v1 as gpt
import s22plus_native_ext4_profile_v1 as fs
import s22plus_native_target_io_v3 as target
from s22plus_native_records_v3 import clock, digest, pin, publish, read, require, verify

SCHEMA='s22plus-native-gpt-android-health-v1'
SU_MISSING=b'/system/bin/sh: su: inaccessible or not found\n'


class SetupPending(RuntimeError):
    def __init__(self,receipt):
        super().__init__('Magisk setup is not ready: completed missing-su read')
        self.receipt=receipt


def missing_su_setup(folder,binding):
    """Classify only the observed completed rc127 after exact Android selection."""
    path=Path(folder)/'03-health.capture.json';handle=raw.load_handle(path)
    require(handle.returncode==127 and not handle.timed_out and not handle.output_exceeded
        and handle.producer_error_type is None
        and raw.read_stdout(handle,maximum=16384)==b''
        and raw.read_stderr(handle,maximum=16384)==SU_MISSING,'root failure is not missing-su setup')
    prior=[raw.load_handle(Path(folder)/f'{i:02d}-health.capture.json') for i in range(3)]
    texts=[raw.decode_success_stdout(h,maximum=16384) for h in prior]
    require(all(not raw.read_stderr(h,maximum=16384) for h in prior),'setup selector has diagnostics')
    target.select_android(texts[0],binding)
    require(texts[1]==binding['topology'],'setup physical target differs')
    fields=target.fields(texts[2],target.PROPERTY_FIELDS)
    require(fields['model']=='SM-S906N' and fields['device']=='g0q'
        and fields['bootloader']==fields['incremental']=='S906NKSS7FYG8'
        and fields['boot_completed']=='1' and target.UUID.fullmatch(fields['boot_id']),
        'setup read is not exact booted FYG8')
    return pin(path)


STAT_SCRIPT=r'''set -eu
B=/system/bin/toybox
v=$($B readlink -f /dev/block/by-name/userdata)
case "${v##*/}" in sd?40) ;; *) exit 1;; esac
r=$($B readlink -f "/sys/class/block/${v##*/}")
p=${r%/*}
case "$p" in /sys/devices/platform/soc*/1d84000.ufshc/host*/target*/*:0:0:0/block/sd?) ;; *) exit 1;; esac
n="$p/${p##*/}41"
if [ -d "$n" ]; then
  name=$($B sed -n 's/^PARTNAME=//p' "$n/uevent")
  printf 'NATIVE_PARTITION %s %s %s %s\n' "$($B cat "$n/partition")" "$($B cat "$n/start")" "$($B cat "$n/size")" "$name"
else
  [ ! -e "$n" ]
  printf 'NATIVE_PARTITION absent\n'
fi
$B stat -f -c 'F2FS_STAT %S %b %a %f %t' /data
'''


def metadata(stdout,sealed,kind):
    require(type(stdout) is bytes and len(stdout)<=65536 and stdout.startswith(b'G0\n'),
        'Android GPT read framing differs')
    parts=stdout[3:].split(b'\n',8);require(len(parts)==9,'Android GPT geometry is incomplete')
    before=census.gpt.geometry(parts[:8]);body=parts[8]
    require(body[:gpt.BYTES]==sealed[kind],'Android complete GPT bytes differ')
    tail=body[gpt.BYTES:]
    require(tail.startswith(b'G1\n') and tail.endswith(b'END\n'),'Android GPT final geometry is absent')
    after=census.gpt.geometry(tail[3:-4].splitlines())
    user=gpt.geometry(sealed,kind)['userdata_sectors']
    require(before==after and before['total_lbas']==62305280 and before['userdata_first_lba']==3726848
        and (before['userdata_last_lba']+1-before['userdata_first_lba'])*8==user,
        'Android kernel partition size differs from the selected GPT')
    return dict(status='PASS_EXACT_GPT',layout=kind,userdata_size_bytes=user*512,
        full_metadata=dict(size=gpt.BYTES,sha256=digest(body[:gpt.BYTES])),
        original_duplicate_guids_preserved=True)


def storage_stat(text,basis,sealed):
    lines=text.splitlines();require(len(lines)==2,'Android storage-stat row count differs')
    expected=gpt.geometry(sealed,basis['layout']);native=expected['native_sectors']
    if native:
        require(lines[0]==f'NATIVE_PARTITION 41 {expected["native_first_lba"]*8} {native} native_data',
            'Android native partition publication differs')
    else:require(lines[0]=='NATIVE_PARTITION absent','original GPT still exposes native entry 41')
    match=re.fullmatch(r'F2FS_STAT ([0-9]{1,16}) ([0-9]{1,16}) ([0-9]{1,16}) ([0-9]{1,16}) ([0-9a-f]{1,16})',lines[1])
    require(match is not None,'Android statfs fields differ')
    block,blocks,available,free=map(int,match.groups()[:4]);kind=match[5]
    require(block==4096 and kind=='f2f52010' and 0<=available<=free<=blocks and blocks>0,
        'Android /data is not a coherent F2FS statfs result')
    if 'geometry' in basis:
        geometry=basis['geometry']
        # Exact FYG8 f2fs_statfs: f_blocks = raw_super.block_count - segment0_blkaddr.
        require(blocks==geometry['block_count']-geometry['segment0_block'],
            'Android reported capacity differs from the initialized F2FS geometry')
    else:require(blocks*block<=expected['userdata_sectors']*512,
        'original Android filesystem exceeds original userdata')
    return dict(status='PASS_ANDROID_REPORTED_CAPACITY',block_size=block,total_blocks=blocks,
        total_bytes=blocks*block,available_bytes=available*block,free_bytes=free*block,
        native_partition_present=bool(native))


def projection(folder,adapter,request):
    if request['N'].get('profile') in fs.PROFILES:
        from s22plus_native_ext4_session_v1 import android_basis
    else:
        from s22plus_native_gpt_session_v1 import android_basis
    folder=Path(folder);task=adapter.configuration(request);basis=android_basis(adapter,request)
    intent=read(folder/'read/intent.json')
    require(intent==dict(schema=SCHEMA,operation=pin(adapter.directory/'operation.json'),
        metadata_command_sha256=digest(census.SCRIPT.encode()),stat_command_sha256=digest(STAT_SCRIPT.encode())),
        'Android GPT/statfs fixed read intent differs')
    before=read(folder/'before/health.json');after=read(folder/'after/health.json')
    for value in (before,after):
        require(target.health_projection(value['captures'],task['target'],request['A'])==value,
            'Android GPT health bracket does not rederive')
    require(before['properties']==after['properties'] and before['boot_id_sha256']==after['boot_id_sha256'],
        'Android boot changed during GPT/statfs reads')
    features=pin(folder/'read/shell-features.capture.json');census.require_shell_v2(features)
    capture=raw.load_handle(folder/'read/metadata.capture.json');raw.require_success(capture)
    sealed=gpt.vectors(request['N']['gpt'])
    proof=metadata(raw.read_stdout(capture,maximum=65536),sealed,basis['layout'])
    stat_capture=raw.load_handle(folder/'read/storage-stat.capture.json')
    text=raw.decode_success_stdout(stat_capture,maximum=16384)
    storage=storage_stat(text,basis,sealed)
    return dict(action='health',health=pin(folder/'after/health.json'),initial_health=pin(folder/'before/health.json'),
        gpt_android=dict(schema=SCHEMA,metadata=proof,storage=storage,
            metadata_capture=pin(capture.receipt_path),stat_capture=pin(stat_capture.receipt_path),
            shell_v2_features=features,read_intent=pin(folder/'read/intent.json')))


def rederive(adapter,step,request):
    base=adapter.folder(step.name);path=base/'result.json'
    if path.exists():
        value=read(path);folder=Path(value['health']['path']).parent.parent
        require(folder.parent==base and folder.name.startswith('attempt-'),'Android GPT health result belongs elsewhere')
        require(value==projection(folder,adapter,request),'Android GPT health result differs from raw captures')
        return value
    good=[]
    for folder in sorted(base.glob('attempt-*')):
        try:value=projection(folder,adapter,request)
        except (OSError,ValueError,KeyError,raw.RawCaptureError):continue
        good.append(value)
    require(len(good)==1,'no unique completed Android GPT/statfs health proof')
    return good[0]


def observe(adapter,step,request,*,guard):
    base=adapter.folder(step.name);base.mkdir(mode=0o700,exist_ok=True)
    if (base/'result.json').exists():return rederive(adapter,step,request)
    try:return rederive(adapter,step,request)
    except (OSError,ValueError,KeyError,raw.RawCaptureError):pass
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(mode=0o700)
    before=adapter.android(request,folder/'before',guard)
    before.wait_ready(deadline_ns=clock()+180_000_000_000)
    try:before.health()
    except raw.RawCaptureError as error:
        # Only the fresh 32 GiB operation adopts this prospective setup state.
        # The original P397 failed read/stop and its separate completion remain unchanged.
        if step.name=='android-initial' and gpt.geometry(gpt.vectors(request['N']['gpt']),
                'proposed')['userdata_sectors']==gpt.ANDROID32_USER:
            try:receipt=missing_su_setup(folder/'before',before.target)
            except (ValueError,OSError,raw.RawCaptureError):raise error
            raise SetupPending(receipt) from error
        raise
    reader=adapter.android(request,folder/'read',guard)
    publish(reader.directory/'intent.json',dict(schema=SCHEMA,operation=pin(adapter.directory/'operation.json'),
        metadata_command_sha256=digest(census.SCRIPT.encode()),stat_command_sha256=digest(STAT_SCRIPT.encode())))
    try:
        census.command(reader)
        reader.command(['-s',reader.target['serial'],'shell','su -c '+shlex.quote(STAT_SCRIPT)],
            'storage-stat',timeout=15)
    finally:
        # A bounded failed metadata read still gets one final Android-health bracket.
        adapter.android(request,folder/'after',guard).health()
    value=projection(folder,adapter,request)
    try:publish(base/'result.json',value)
    except Exception as error:
        from s22plus_native_session_v3 import ResultPublicationError
        raise ResultPublicationError(step) from error
    return value


def final_protocol_completed(adapter,step,request):
    if (adapter.folder(step.name)/'result.json').exists():return True
    try:rederive(adapter,step,request)
    except (OSError,ValueError,KeyError,raw.RawCaptureError):return False
    return True


def reboot_persistence(adapter,request,final):
    path=adapter.directory/'android-initial.json'
    reboot=adapter.directory/'android-reboot.json'
    if not path.exists() or not reboot.exists():return dict(status='NO_PROOF',reason='REBOOT_SEQUENCE_INCOMPLETE')
    initial=read(path)
    from s22plus_native_session_v3 import Step
    adapter.validate_result(Step('android-initial','health','A'),initial,request)
    adapter.validate_result(Step('android-reboot','reboot','A'),read(reboot),request)
    a=read(verify(initial['health']));b=read(verify(final['health']))
    require(a['boot_id_sha256']!=b['boot_id_sha256'],'Android reboot did not prove a new boot')
    require(initial['gpt_android']['metadata']==final['gpt_android']['metadata']
        and initial['gpt_android']['storage']['total_bytes']==final['gpt_android']['storage']['total_bytes'],
        'Android GPT or reported capacity changed across reboot')
    return dict(status='PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT',before_health=initial['health'],
        after_health=final['health'],total_bytes=final['gpt_android']['storage']['total_bytes'])
