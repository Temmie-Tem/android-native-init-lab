"""Reviewed protected-root preparation: fixed Android reads, no control or transfer."""
import argparse
from pathlib import Path
import shlex

import consumed_candidate_registry_v1 as registry
import device_action_raw_capture_v1 as raw
import s22plus_native_root_inspect_profile_v1 as inspection
import s22plus_native_userspace_probe_profile_v1 as probe
import s22plus_native_task_v3 as task
import s22plus_native_adapter_v3 as adapter
import s22plus_native_target_io_v3 as target
import s22plus_native_android_storage_v1 as census
import s22plus_native_gpt_android_v1 as android_storage
import s22plus_native_gpt_profile_v1 as gpt
from s22plus_native_host_v3 import NativeHost
from s22plus_native_records_v3 import pin, private_path, publish, read, require, verify

ROOT = inspection.ROOT
PRIOR_TASK = ROOT / 'workspace/private/runs/s22plus-native-session-v3/p399-p400-native-ext4-20260917-1/task.json'


def projection(folder, target_binding, android, image):
    first = read(folder / 'before/health.json'); last = read(folder / 'after/health.json')
    for value in (first, last):
        require(target.health_projection(value['captures'], target_binding, android) == value,
            'preparation Android health does not rederive')
    require(first['properties'] == last['properties'], 'Android changed during root inspection preparation')
    census.require_shell_v2(pin(folder / 'read/shell-features.capture.json'))
    metadata_capture = raw.load_handle(folder / 'read/metadata.capture.json')
    stat_capture = raw.load_handle(folder / 'read/stat.capture.json')
    raw.require_success(metadata_capture); raw.require_success(stat_capture)
    sealed = gpt.vectors(image['gpt'])
    metadata = android_storage.metadata(raw.read_stdout(metadata_capture, maximum=65536), sealed, 'proposed')
    capacity = android_storage.storage_stat(raw.decode_success_stdout(stat_capture, maximum=16384),
        dict(layout='proposed', geometry=image['android_return']['geometry']), sealed)
    require(capacity['total_bytes'] == 34357624832, 'prepared Android32 capacity differs')
    return dict(before=pin(folder/'before/health.json'), after=pin(folder/'after/health.json'),
        metadata=metadata, capacity=capacity, metadata_capture=pin(metadata_capture.receipt_path),
        stat_capture=pin(stat_capture.receipt_path), boot_id_sha256=last['boot_id_sha256'])


def prepare(directory, image_receipt):
    image = read(verify(image_receipt))
    require(image['profile'] in (inspection.PROFILE, probe.PROFILE), 'not a protected-root candidate')
    selected = probe if image['profile'] == probe.PROFILE else inspection
    task.capability(ROOT, profile=selected.PROFILE)
    adapter.image_valid(image, artifact_bytes=True)
    _, _, previous = selected.prior_inputs()
    old_task = read(PRIOR_TASK)
    require(old_task['target'] == previous['target'] and old_task['A'] == previous['A'],
        'retained host/recovery setup belongs to a different target')
    task.validate_recovery(old_task['recovery_evidence'], previous['target'], previous['A'])
    directory = private_path(ROOT, directory, exists=False)
    require(not directory.exists(), 'fresh stage-2 preparation directory required')
    directory.mkdir(mode=0o700)
    target_receipt = publish(directory/'target.json', previous['target'])
    adb = pin(Path('/usr/bin/adb').resolve(strict=True), maximum=32*1024*1024)
    host = NativeHost(read(verify(old_task['host_installation'])), directory/'host-check')
    lane = target.lane.capture_binding(target.lane.SOURCE_TOPOLOGY)
    def guard():
        task.capability(ROOT, profile=selected.PROFILE)
        registry.require_no_f1_owner(ROOT)
        target.lane.revalidate_binding(lane, source_topology=target.lane.SOURCE_TOPOLOGY)
    try:
        with registry.target_session_lease(ROOT):
            guard(); host.holders()
            registry.preflight_candidate(ROOT, adapter.image_identity(image, image_receipt['sha256']))
            folder = directory/'prepared'; folder.mkdir(mode=0o700)
            target.Android(adb, previous['target'], previous['A'], folder/'before', guard=guard).health()
            reader = target.Android(adb, previous['target'], previous['A'], folder/'read', guard=guard)
            census.command(reader)
            reader.command(['-s', previous['target']['serial'], 'shell',
                'su -c ' + shlex.quote(android_storage.STAT_SCRIPT)], 'stat', timeout=15)
            target.Android(adb, previous['target'], previous['A'], folder/'after', guard=guard).health()
            result = projection(folder, previous['target'], previous['A'], image)
            publish(folder/'result.json', result)
            receipt = task.prepare_task(ROOT, directory/'task', native=image_receipt, experiment=None,
                target=target_receipt, installation=old_task['host_installation'], recovery_evidence=old_task['recovery_evidence'],
                seconds=1800, operation_budget=1, recovery_mode='attended', reentry=False, hud=False,
                usb_reconnect=False, android_exit=False, root_inspect=selected is inspection, userspace_probe=selected is probe)
            publish(directory/'ready.json', dict(schema=selected.SCHEMA+'-ready', task=receipt,
                preparation=pin(folder/'result.json'), grant_opened=False, image_transferred=False,
                native_filesystem_observed=False, userspace_executed=False))
            return receipt
    except BaseException as error:
        publish(directory/'prepare-stop.json', dict(schema=selected.SCHEMA+'-prepare-stop',
            error_type=type(error).__name__, message=str(error)[:512], image_transferred=False, grant_opened=False))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--image', type=Path, required=True)
    args = parser.parse_args()
    print('READY_PROTECTED_ROOT_TASK ' + prepare(args.directory, pin(private_path(ROOT,args.image)))['sha256'])
