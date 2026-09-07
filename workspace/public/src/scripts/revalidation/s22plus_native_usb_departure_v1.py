"""Observe one prebound native usbfs departure before strict Odin enumeration.

No inventory retry, device command, Download proof or recovery authority lives
here. The caller owns the existing CONTROL intent and its absolute deadline.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import os
from pathlib import Path
import re
import stat
import time
from typing import Any

import device_action_f1_v2 as core
import s22plus_fyg8_p324_typec_lane_binding as lane_contract
import s22plus_odin_usbfs_identity as usbfs

BINDING_NAME = 'native-usb-departure-binding.json'
RAW_BINDING_NAME = 'native-usb-departure-binding.raw.json'
OBSERVATION_NAME = 'native-usb-departure-observation.json'
RAW_OBSERVATION_NAME = 'native-usb-departure-observation.raw.json'
CAPTURE_NAME = 'raw-native-usb-departure'
POLL_SECONDS = 0.1


class DepartureError(ValueError):
    pass


def _identity(raw: bytes) -> dict[str, Any]:
    return dict(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def _host_boot() -> str:
    raw = Path('/proc/sys/kernel/random/boot_id').read_bytes()
    if re.fullmatch(rb'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}\n', raw) is None:
        raise DepartureError('host boot identity unavailable')
    return hashlib.sha256(raw).hexdigest()


def _read(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        value, receipt = core.load_json(path, 'native USB departure record')
        metadata = path.lstat()
        if (stat.S_IMODE(metadata.st_mode) != 0o400 or metadata.st_nlink != 1
                or metadata.st_uid != os.getuid()):
            raise DepartureError('native USB departure record metadata differs')
        return value, receipt
    except (core.F1V2Error, OSError) as exc:
        raise DepartureError('native USB departure record unavailable') from exc


def _publish(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    core._write_exclusive(path, value)
    actual, receipt = _read(path)
    if actual != value:
        raise DepartureError('native USB departure record reopen differs')
    return receipt


def _parse_coordinate(raw: bytes) -> int:
    if re.fullmatch(rb'[1-9][0-9]{0,2}\n', raw) is None:
        raise DepartureError('native USB coordinate is invalid')
    return int(raw)


def _coordinate(path: Path, capture_dir: Path, name: str):
    writer = usbfs.raw_capture.RawCaptureWriter(capture_dir, name,
        stdout_maximum=17, stderr_maximum=64, argv0_name='native-usb-coordinate-read')
    try:
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            raw = os.read(fd, 17)
            writer.write_stdout(raw)
        finally:
            os.close(fd)
    except OSError as exc:
        writer.write_stderr(('errno='+str(exc.errno)).encode('ascii'))
        writer.finalize(returncode=None, producer_error_type='OSError')
        raise
    handle = writer.finalize(returncode=0)
    _, receipt = _read(handle.receipt_path)
    usbfs.raw_capture.require_success(handle)
    captured = usbfs.raw_capture.read_stdout(handle, maximum=17)
    return _parse_coordinate(captured), receipt


def _mapping(path: Path, capture_dir: Path, phase: str):
    metadata = path.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or path.resolve(strict=True) != path:
        raise DepartureError('native USB sysfs path is not direct')
    bus, bus_receipt = _coordinate(path / 'busnum', capture_dir, phase+'-busnum')
    dev, dev_receipt = _coordinate(path / 'devnum', capture_dir, phase+'-devnum')
    node = f'/dev/bus/usb/{bus:03d}/{dev:03d}'
    usbfs._validated_usbfs_coordinates(node)
    return (dict(sysfs_path=str(path), sysfs_dev=metadata.st_dev,
        sysfs_ino=metadata.st_ino, busnum=bus, devnum=dev, node=node),
        dict(busnum=bus_receipt, devnum=dev_receipt))


def _snapshot(path: str, capture_dir: Path):
    return usbfs.snapshot_node(path,
        birth_reader=lambda current: usbfs.read_birth_time_ns(current, capture_dir))


def _validate_raw_binding(raw: dict[str, Any], endpoint_identity: str, run_dir: Path) -> None:
    if set(raw) != {'schema', 'before', 'after', 'usbfs', 'endpoint_identity_sha256', 'coordinates'}:
        raise DepartureError('native USB raw binding shape differs')
    mapping = raw['before']
    topology = lane_contract.CANDIDATE_TOPOLOGY.removeprefix('usb:')
    if (raw['schema'] != 'native_usb_departure_raw_binding_v1'
            or type(mapping) is not dict
            or set(mapping) != {'sysfs_path','sysfs_dev','sysfs_ino','busnum','devnum','node'}
            or mapping != raw['after']
            or raw['endpoint_identity_sha256'] != endpoint_identity
            or type(endpoint_identity) is not str
            or re.fullmatch('[0-9a-f]{64}', endpoint_identity) is None
            or type(mapping['sysfs_path']) is not str
            or not Path(mapping['sysfs_path']).is_absolute()
            or Path(mapping['sysfs_path']).name != topology
            or any(type(mapping[k]) is not int or mapping[k] < 0
                for k in ('sysfs_dev','sysfs_ino','busnum','devnum'))
            or mapping['busnum'] != int(topology.split('-')[0])
            or mapping['node'] != f"/dev/bus/usb/{mapping['busnum']:03d}/{mapping['devnum']:03d}"):
        raise DepartureError('native USB exact mapping differs')
    coordinates = raw['coordinates']
    if type(coordinates) is not dict or set(coordinates) != {'before','after'}:
        raise DepartureError('native USB coordinate receipts differ')
    try:
        for phase in ('before','after'):
            if type(coordinates[phase]) is not dict or set(coordinates[phase]) != {'busnum','devnum'}:
                raise DepartureError('native USB coordinate receipt shape differs')
            for name in ('busnum','devnum'):
                path = run_dir/CAPTURE_NAME/(phase+'-'+name+'.capture.json')
                _, receipt = _read(path)
                if receipt != coordinates[phase][name]:
                    raise DepartureError('native USB coordinate capture differs')
                handle = usbfs.raw_capture.load_handle(path)
                usbfs.raw_capture.require_success(handle)
                captured = usbfs.raw_capture.read_stdout(handle,maximum=17)
                if _parse_coordinate(captured) != raw[phase][name]:
                    raise DepartureError('native USB coordinate raw projection differs')
    except usbfs.raw_capture.RawCaptureError as exc:
        raise DepartureError('native USB coordinate raw evidence invalid') from exc
    try:
        snapshot = usbfs.UsbfsNodeSnapshot(**raw['usbfs'])
        usbfs.immutable_identity(snapshot)
    except (TypeError, usbfs.UsbfsIdentityError) as exc:
        raise DepartureError('native USB immutable binding invalid') from exc
    if snapshot.path != mapping['node']:
        raise DepartureError('native USB node/mapping differs')


def capture_binding(run_dir: Path, *, endpoint, binding, request) -> dict[str, Any]:
    """Called between the existing exact tty/lane checks, before CONTROL intent."""
    run_dir = Path(run_dir)
    if endpoint.topology != lane_contract.CANDIDATE_TOPOLOGY.removeprefix('usb:'):
        raise DepartureError('native USB endpoint is outside exact candidate lane')
    capture_dir = usbfs.raw_capture.prepare_capture_dir(run_dir, CAPTURE_NAME)
    before, before_coordinates = _mapping(endpoint.usb_path, capture_dir, 'before')
    snapshot = _snapshot(before['node'], capture_dir)
    after, after_coordinates = _mapping(endpoint.usb_path, capture_dir, 'after')
    raw = dict(schema='native_usb_departure_raw_binding_v1', before=before,
        after=after, usbfs=asdict(snapshot), endpoint_identity_sha256=endpoint.identity_sha256,
        coordinates=dict(before=before_coordinates,after=after_coordinates))
    raw_receipt = _publish(run_dir / RAW_BINDING_NAME, raw)
    _validate_raw_binding(raw, endpoint.identity_sha256, run_dir)
    value = dict(schema='native_usb_departure_binding_v1', binding=binding,
        request=request, endpoint_identity_sha256=endpoint.identity_sha256,
        host_boot_sha256=_host_boot(), source=_identity(Path(__file__).read_bytes()),
        raw=raw_receipt)
    return _publish(run_dir / BINDING_NAME, value)


def read_binding(run_dir: Path, intent: dict[str, Any]):
    run_dir = Path(run_dir)
    value, receipt = _read(run_dir / BINDING_NAME)
    if (set(value) != {'schema','binding','request','endpoint_identity_sha256',
            'host_boot_sha256','source','raw'}
            or value['schema'] != 'native_usb_departure_binding_v1'
            or value['binding'] != intent['binding'] or value['request'] != intent['request']
            or value['endpoint_identity_sha256'] != intent['endpoint_identity_sha256']
            or value['host_boot_sha256'] != intent['host_boot_sha256']
            or value['source'] != _identity(Path(__file__).read_bytes())
            or receipt != intent['lane'].get('native_usb_departure_binding')):
        raise DepartureError('native USB departure binding/intent differs')
    raw, raw_receipt = _read(run_dir / RAW_BINDING_NAME)
    if raw_receipt != value['raw']:
        raise DepartureError('native USB departure raw identity differs')
    _validate_raw_binding(raw, value['endpoint_identity_sha256'], run_dir)
    return value, receipt, usbfs.UsbfsNodeSnapshot(**raw['usbfs'])


def read_observation(run_dir: Path, intent: dict[str, Any], intent_receipt: dict[str, Any]):
    _, binding_receipt, snapshot = read_binding(run_dir, intent)
    value, receipt = _read(Path(run_dir) / OBSERVATION_NAME)
    raw, raw_receipt = _read(Path(run_dir) / RAW_OBSERVATION_NAME)
    expected_keys = {'schema','control_intent','native_binding','source',
        'host_boot_sha256','deadline_monotonic_ns','observed_monotonic_ns',
        'node','status','error_class'}
    deadline = intent['created_monotonic_ns'] + intent['software_window_seconds']*1_000_000_000
    if (set(raw) != expected_keys or raw['schema'] != 'native_usb_departure_raw_observation_v1'
            or raw['control_intent'] != intent_receipt or raw['native_binding'] != binding_receipt
            or raw['source'] != _identity(Path(__file__).read_bytes())
            or raw['host_boot_sha256'] != intent['host_boot_sha256']
            or raw['deadline_monotonic_ns'] != deadline or raw['node'] != snapshot.path
            or type(raw['observed_monotonic_ns']) is not int
            or raw['observed_monotonic_ns'] < intent['created_monotonic_ns']
            or raw['status'] not in ('absent','timeout','error')
            or (raw['status'] == 'absent' and (raw['error_class'] != 'UsbfsEndpointDeparture'
                or raw['observed_monotonic_ns'] >= deadline))
            or (raw['status'] == 'timeout' and (raw['error_class'] is not None
                or raw['observed_monotonic_ns'] < deadline))
            or (raw['status'] == 'error' and raw['error_class'] not in
                ('UsbfsIdentityError','OSError','DepartureError'))
            or value != dict(schema='native_usb_departure_observation_v1',
                raw=raw_receipt, status=raw['status'], download_proved=False,
                control_replay_forbidden=True)):
        raise DepartureError('native USB departure observation differs')
    return value, receipt


def observe_departure(run_dir: Path, intent: dict[str, Any], intent_receipt: dict[str, Any],
        *, monotonic_ns=time.monotonic_ns, sleep=time.sleep) -> bool:
    """True is only exact old-native-node absence, never Download arrival."""
    run_dir = Path(run_dir)
    _, binding_receipt, baseline = read_binding(run_dir, intent)
    if _host_boot() != intent['host_boot_sha256']:
        raise DepartureError('native USB departure host boot differs')
    if (run_dir / OBSERVATION_NAME).exists() or (run_dir / OBSERVATION_NAME).is_symlink():
        existing, _ = read_observation(run_dir, intent, intent_receipt)
        if existing['status'] == 'error':
            raise DepartureError('previous native USB departure observation failed')
        return existing['status'] == 'absent'
    # Partial raw output cannot be repaired into another observation or window.
    if (run_dir / RAW_OBSERVATION_NAME).exists() or (run_dir / RAW_OBSERVATION_NAME).is_symlink():
        raise DepartureError('native USB departure observation is incomplete')
    deadline = intent['created_monotonic_ns'] + intent['software_window_seconds']*1_000_000_000
    capture_dir = usbfs.raw_capture.prepare_capture_dir(run_dir, CAPTURE_NAME)
    failure = None
    status, error_class = 'timeout', None
    while monotonic_ns() < deadline:
        try:
            current = _snapshot(baseline.path, capture_dir)
            if usbfs.immutable_identity(current) != usbfs.immutable_identity(baseline):
                raise DepartureError('native USB node was replaced before departure')
        except usbfs.UsbfsEndpointDeparture as exc:
            if exc.path != baseline.path:
                failure = DepartureError('unbound native USB node departure')
                status, error_class = 'error', 'DepartureError'
            else:
                status, error_class = 'absent', 'UsbfsEndpointDeparture'
            break
        except (usbfs.UsbfsIdentityError, OSError, DepartureError) as exc:
            failure = exc
            status, error_class = 'error', ('OSError' if isinstance(exc,OSError)
                else 'UsbfsIdentityError' if isinstance(exc,usbfs.UsbfsIdentityError) else 'DepartureError')
            break
        remaining = (deadline-monotonic_ns())/1e9
        if remaining > 0:
            sleep(min(POLL_SECONDS, remaining))
    observed = monotonic_ns()
    if status == 'absent' and observed >= deadline:
        status, error_class = 'timeout', None
    raw = dict(schema='native_usb_departure_raw_observation_v1',
        control_intent=intent_receipt, native_binding=binding_receipt,
        source=_identity(Path(__file__).read_bytes()), host_boot_sha256=_host_boot(),
        deadline_monotonic_ns=deadline, observed_monotonic_ns=observed,
        node=baseline.path, status=status, error_class=error_class)
    raw_receipt = _publish(run_dir / RAW_OBSERVATION_NAME, raw)
    value = dict(schema='native_usb_departure_observation_v1',raw=raw_receipt,
        status=status, download_proved=False, control_replay_forbidden=True)
    _publish(run_dir / OBSERVATION_NAME, value)
    read_observation(run_dir, intent, intent_receipt)
    if failure is not None:
        raise DepartureError('native USB departure observation failed') from failure
    return status == 'absent'
