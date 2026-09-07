"""Read-only, raw-first target Download census after completed rollback.

No Odin calls, transfers, tracker resets or recovery authority live here.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

import device_action_raw_capture_v1 as raw_capture
import s22plus_fyg8_p318_topology_receipt as topology

SCHEMA = 's22plus_final_target_download_census_v1'
MAX_BYTES = 256 * 1024


class FinalHealthError(ValueError):
    pass


def _android(root, lane):
    name = lane['source_topology'].removeprefix('usb:')
    node = root / name
    captured = dict(reads=[],expected_controller=None,error=None)
    for _ in range(2):
        observation = dict(values={},error=None)
        captured['reads'].append(observation)
        try:
            for key in ('idVendor','idProduct','serial','busnum','devnum'):
                observation['values'][key] = topology._text(node/key,key)
            controller, device = topology._controller_and_device(node)
            observation['values'].update(topology=name,controller_path=controller,usb_device_path=device)
        except (OSError,ValueError) as exc:
            observation['error'] = type(exc).__name__
    try:
        captured['expected_controller'] = str((root/('usb'+name.split('-')[0])).resolve(strict=True).parent)
    except OSError as exc:
        captured['error'] = type(exc).__name__
    return captured


def capture(directory: Path, *, usb_root: Path, profile: dict, lane: dict,
            serial: str, context: dict, phase: str) -> dict:
    directory = raw_capture.prepare_capture_dir(directory, 'final-target-health')
    ordinals = [int(m.group(1)) for p in directory.iterdir()
                if (m := re.match(r'^([0-9]+)-',p.name))]
    name = f'{max(ordinals,default=-1)+1:04d}-download-census'
    value = dict(schema=SCHEMA,context=context,phase=phase,android=None,download=None,error=None)
    try:
        value['download'] = json.loads(topology.capture_download_inventory_raw(
            phase='rollback_download',profile=profile,usb_root=usb_root))
        value['android'] = _android(usb_root,lane)
    except (OSError,ValueError) as exc:
        value['error'] = type(exc).__name__
    # Seal even incomplete/error observations before any interpretation.
    handle = raw_capture.publish_captured_bytes(directory,name,
        stdout=topology.canonical(value))
    payload = topology.stable_read(handle.receipt_path,maximum=MAX_BYTES)
    receipt = dict(path=str(handle.receipt_path),size=len(payload),
                   sha256=hashlib.sha256(payload).hexdigest())
    validate(receipt,directory=directory,profile=profile,lane=lane,
             serial=serial,context=context,phase=phase)
    return receipt


def validate(receipt: dict, *, directory: Path, profile: dict, lane: dict,
             serial: str, context: dict, phase: str) -> dict:
    path = Path(receipt['path'])
    if path.parent != directory or path.is_symlink() or re.fullmatch(r'[0-9]+-download-census\.capture\.json',path.name) is None:
        raise FinalHealthError('final census escaped its fixed context')
    payload = topology.stable_read(path,maximum=MAX_BYTES)
    if receipt != dict(path=str(path),size=len(payload),sha256=hashlib.sha256(payload).hexdigest()):
        raise FinalHealthError('final census receipt changed')
    handle = raw_capture.load_handle(path)
    raw_capture.require_success(handle)
    value = json.loads(raw_capture.read_stdout(handle,maximum=MAX_BYTES))
    if (set(value) != {'schema','context','phase','android','download','error'}
        or value['schema'] != SCHEMA or value['context'] != context or value['error'] is not None
        or phase not in {'before','after'} or value['phase'] != phase):
        raise FinalHealthError('final census context or capture failed')
    parsed = topology.parse_raw_snapshot(topology.canonical(value['download']),phase='rollback_download')
    if parsed['capture_complete'] is not True:
        raise FinalHealthError('final Download census is incomplete')
    captured = value['android']
    if (not isinstance(captured,dict) or captured.get('error') is not None
        or len(captured.get('reads',[])) != 2
        or any(row.get('error') is not None for row in captured['reads'])
        or captured['reads'][0]['values'] != captured['reads'][1]['values']):
        raise FinalHealthError('final Android identity acquisition is incomplete or changed')
    android = captured['reads'][0]['values']
    source = lane['source_topology'].removeprefix('usb:')
    if (not isinstance(android,dict) or set(android) != {'idVendor','idProduct','serial','busnum','devnum','topology','controller_path','usb_device_path'} or android.get('topology') != source
        or android.get('serial') != serial or android.get('idVendor') != '04e8'
        or android.get('idProduct') != '6860'
        or android.get('busnum') != source.split('-')[0]
        or re.fullmatch(r'[1-9][0-9]*',android.get('devnum','')) is None
        or android.get('controller_path') != captured['expected_controller']
        or lane['source_lane']['controller'] not in Path(android.get('controller_path','')).parts
        or Path(android.get('usb_device_path','')).name != source
        or Path(android['usb_device_path']).parent.parent != Path(android['controller_path']) / ('usb'+source.split('-')[0])):
        # The source is a downstream hub port, so its parent is the bound hub.
        raise FinalHealthError('final Android identity/path differs')
    target_lanes = {source,lane['candidate_topology'].removeprefix('usb:')}
    endpoints = parsed['endpoints']
    download = profile['target']['download']
    if any(row['mode'] != 'download' or row['identity']['vendor'] != download['usb_vendor_id']
           or row['identity']['product_id'] != download['usb_product_id'] for row in endpoints):
        raise FinalHealthError('final Download census identity class differs')
    if any(row['topology'] in target_lanes for row in endpoints):
        raise FinalHealthError('Download remains on a bound target lane')
    # Every foreign endpoint stays in raw evidence; summaries contain digests.
    return dict(sequence=int(path.name.split('-')[0]),target_odin_endpoint_absent=True,global_odin_endpoint_absent=not endpoints,
        foreign_download_endpoints=[dict(topology_sha256=row['topology_sha256'],
            endpoint_identity_sha256=row['endpoint_identity_sha256'],
            controller_path_sha256=row['controller_path_sha256']) for row in endpoints])
