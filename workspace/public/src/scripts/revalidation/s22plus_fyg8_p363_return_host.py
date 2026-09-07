"""P363 durable control intent; no device command or transition implementation.

One no-clobber intent precedes every CONTROL byte. Existing/partial intent means
observation or the existing preauthorized rollback only. It never permits a
second display or control exchange. Window evidence is independent of ACK and
of physical-intervention attribution, which a USB observer cannot establish.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import stat
import time
import device_action_f1_v2 as core
import s22plus_fyg8_p363_return_spec as spec

RUN_ID = 'c363f1e0a90b5e6d7c8a9b0c1d2e3f0b'
INTENT_NAME = 'p363-control-intent.json'
WINDOW_NAME = 'p363-return-window.json'
SOFTWARE_WINDOW_SECONDS = 30


class ReturnControlError(ValueError):
    pass


def identity(raw):
    return dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def _digest(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None


def host_boot_sha256():
    raw = Path('/proc/sys/kernel/random/boot_id').read_bytes()
    if not re.fullmatch(rb'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}\n',raw):
        raise ReturnControlError('host boot UUID unavailable')
    return hashlib.sha256(raw).hexdigest()


def exists(run_dir):
    path = Path(run_dir) / INTENT_NAME
    return path.exists() or path.is_symlink()


def stable_record(path):
    path = Path(path)
    fd = os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or stat.S_IMODE(before.st_mode) != 0o400 or before.st_nlink != 1 or before.st_uid != os.getuid() or not 0 < before.st_size <= 65536:
            raise ReturnControlError('control record metadata differs')
        raw = os.read(fd,65537)
        after = os.fstat(fd)
        if len(raw) != before.st_size or (before.st_ino,before.st_dev,before.st_size,before.st_mtime_ns,before.st_ctime_ns) != (after.st_ino,after.st_dev,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            raise ReturnControlError('control record changed')
    finally:
        os.close(fd)
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:
        raise ReturnControlError('control record encoding or JSON is invalid') from exc
    if type(value) is not dict:
        raise ReturnControlError('control record is not an object')
    return value,dict(path=str(path),**identity(raw))


def write_intent(run_dir, *, binding, endpoint_identity_sha256, lane, request):
    if exists(run_dir):
        raise ReturnControlError('P363 intent exists; display/control replay forbidden')
    expected = dict(run_id_hex=RUN_ID,mode='download',sequence=5,
        boot_id_semantic=spec.BOOT_ID_SEMANTIC,boot_receipt_semantic=spec.BOOT_RECEIPT_SEMANTIC)
    if type(request) is not dict or set(request) != set(expected)|{'nonce_sha256','kernel_boot_identity_sha256'} or any(type(request[k]) is not type(v) or request[k] != v for k,v in expected.items()) or not all(_digest(request[k]) for k in ('nonce_sha256','kernel_boot_identity_sha256')) or not _digest(endpoint_identity_sha256):
        raise ReturnControlError('P363 fixed control binding differs')
    if type(binding) is not dict or not binding or type(lane) is not dict or lane.get('accepted_for_p324') is not True or lane.get('observation_phase') != 'before-native-return-control':
        raise ReturnControlError('P363 pre-control lane/binding missing')
    value = dict(schema='s22plus_fyg8_p363_control_intent_v1',binding=binding,
        endpoint_identity_sha256=endpoint_identity_sha256,request=request,lane=lane,
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        created_monotonic_ns=time.monotonic_ns(),host_boot_sha256=host_boot_sha256(),
        software_window_seconds=SOFTWARE_WINDOW_SECONDS,
        replay_forbidden=True,effect_occurrence='UNKNOWN',
        source=identity(Path(__file__).read_bytes()))
    path = Path(run_dir)/INTENT_NAME
    core._write_exclusive(path,value)
    reopened,receipt = stable_record(path)
    if reopened != value:
        raise ReturnControlError('P363 durable intent reopen differs')
    return receipt


def read_intent(run_dir, *, binding=None, endpoint_identity_sha256=None, proof=None):
    value,receipt = stable_record(Path(run_dir)/INTENT_NAME)
    if set(value) != {'schema','binding','endpoint_identity_sha256','request','lane','created_utc','created_monotonic_ns','host_boot_sha256','software_window_seconds','replay_forbidden','effect_occurrence','source'} or value['schema'] != 's22plus_fyg8_p363_control_intent_v1' or value['replay_forbidden'] is not True or value['effect_occurrence'] != 'UNKNOWN' or type(value['created_monotonic_ns']) is not int or value['created_monotonic_ns'] <= 0 or not _digest(value['host_boot_sha256']) or type(value['software_window_seconds']) is not int or value['software_window_seconds'] != SOFTWARE_WINDOW_SECONDS:
        raise ReturnControlError('P363 durable intent shape differs')
    request = value['request']
    fixed = dict(run_id_hex=RUN_ID,mode='download',sequence=5,
        boot_id_semantic=spec.BOOT_ID_SEMANTIC,boot_receipt_semantic=spec.BOOT_RECEIPT_SEMANTIC)
    if type(request) is not dict or set(request) != set(fixed)|{'nonce_sha256','kernel_boot_identity_sha256'} or any(type(request[k]) is not type(v) or request[k] != v for k,v in fixed.items()) or not all(_digest(request[k]) for k in ('nonce_sha256','kernel_boot_identity_sha256')) or not _digest(value['endpoint_identity_sha256']) or type(value['lane']) is not dict or value['lane'].get('accepted_for_p324') is not True:
        raise ReturnControlError('P363 durable request shape differs')
    if binding is not None and value['binding'] != binding:
        raise ReturnControlError('P363 durable run binding differs')
    if endpoint_identity_sha256 is not None and value['endpoint_identity_sha256'] != endpoint_identity_sha256:
        raise ReturnControlError('P363 durable endpoint differs')
    if value['source'] != identity(Path(__file__).read_bytes()):
        raise ReturnControlError('P363 control source changed')
    if proof is not None:
        request = value['request']; row = proof['sessions'][0]
        expected = dict(run_id_hex=RUN_ID,mode='download',sequence=5,
            nonce_sha256=row['nonce_sha256'],kernel_boot_identity_sha256=row['boot_id_sha256'],
            boot_id_semantic=spec.BOOT_ID_SEMANTIC,boot_receipt_semantic=spec.BOOT_RECEIPT_SEMANTIC)
        if request != expected:
            raise ReturnControlError('P363 intent/raw session join differs')
    return value,receipt


def remaining_window(intent):
    if intent['host_boot_sha256'] != host_boot_sha256():
        return 0.0
    now = time.monotonic_ns()
    started = intent['created_monotonic_ns']
    if now < started:
        return 0.0
    return max(0.0,SOFTWARE_WINDOW_SECONDS-(now-started)/1e9)


def validate_window(value, *, binding, intent, intent_receipt):
    fields = {'schema','binding','control_intent','outcome','observed_within_software_deadline',
        'closed_monotonic_ns','host_boot_sha256','physical_prompt_required',
        'physical_intervention','software_causal_attribution','rollback_topology_record'}
    if type(value) is not dict or set(value) != fields or value['schema'] != 's22plus_fyg8_p363_return_window_v1' or value['binding'] != binding or value['control_intent'] != intent_receipt or type(value['closed_monotonic_ns']) is not int or value['closed_monotonic_ns'] <= 0 or not _digest(value['host_boot_sha256']) or type(value['outcome']) is not str or value['physical_intervention'] != 'UNOBSERVED' or value['software_causal_attribution'] != 'UNPROVED':
        raise ReturnControlError('P363 return window shape/binding differs')
    arrived = value['outcome'] in ('exact-download-within-control-window','exact-download-after-control-window')
    within = value['outcome'] == 'exact-download-within-control-window'
    allowed = {'not-requested','window-expired-before-observation','software-window-timed-out',
        'exact-download-within-control-window','exact-download-after-control-window'}
    if value['outcome'] not in allowed or value['observed_within_software_deadline'] is not within or value['physical_prompt_required'] is not (not arrived):
        raise ReturnControlError('P363 return window status differs')
    if (intent is None) != (value['outcome'] == 'not-requested'):
        raise ReturnControlError('P363 window/control intent relation differs')
    if arrived:
        receipt = value['rollback_topology_record']
        if type(receipt) is not dict or set(receipt) != {'path','size','sha256'} or type(receipt['path']) is not str or type(receipt['size']) is not int or receipt['size'] <= 0 or not _digest(receipt['sha256']):
            raise ReturnControlError('P363 exact Download receipt absent')
    elif value['rollback_topology_record'] is not None:
        raise ReturnControlError('P363 absent Download has a receipt')
    if within and (value['host_boot_sha256'] != intent['host_boot_sha256'] or not
        intent['created_monotonic_ns'] <= value['closed_monotonic_ns']
        <= intent['created_monotonic_ns'] + SOFTWARE_WINDOW_SECONDS*1_000_000_000):
        raise ReturnControlError('P363 return window timestamp differs')
    return value
