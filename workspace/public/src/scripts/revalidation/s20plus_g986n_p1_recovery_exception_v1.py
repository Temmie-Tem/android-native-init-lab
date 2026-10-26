#!/usr/bin/env python3
"""One approved P1 recovery after the explained foreign Download collision.

This is a new policy exception, not reuse of the consumed physical observation.
The original journal and activation records remain immutable. Only the exact
run's first resident rollback and its post-transfer health continuation exist.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import stat
import time

ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve()
RUN = ROOT / 'workspace/private/runs/s20plus-g986n-p1-pid1-witness-f1/run-1788813079911545392'
BINDING = '935055acdaa3d7c03c2d61212a682d08638046abb1e099a40fa45ca4841d46be'
REVIEW = ROOT / 'workspace/private/outputs/s20plus_g986n/p1_recovery_exception_20260908/authorization.json'
TEST_LOG = REVIEW.parent / 'focused-tests.log'
POLICY = ROOT / 'docs/operations/S20PLUS_P1_ONE_RUN_RECOVERY_EXCEPTION_2026-09-08.md'
INTENT = 'p1-recovery-exception-intent.json'
ARRIVAL = 'p1-recovery-exception-arrival.json'
MISS = 'p1-recovery-exception-stop.json'
NODES = frozenset((INTENT, ARRIVAL, MISS))
SCOPE = 's20plus-p1-one-run-first-resident-rollback-20260908'
OLD_ENGINE_NORMALIZED = '52f2df6aa1864a956cd4d0e43a3906ffbb613116577d7735788630a43323ea06'
HISTORY = {
    'prepared.json': '8cf44007d1f8e01aed02d7348e590b35cd8f7746b35bd6d775456a3bbbf89b15',
    'candidate-result.json': 'ee34f994aabd44b40c157583f37809a2365794c20e5dd44c00a10f378e060574',
    'candidate-observation.json': '871e2f4d18688895712452cee6d7c6c4640e829d95e4a3dbf8c9cc4ae3e7cd7a',
    'physical-confirmation-intent.json': 'd58003cb4b279c542e1450b69ef865cb0b5c2a09a06da1ee90b12ba7c9fa53e8',
    'physical-observation-miss.json': '42f2121c8269ef1ade66ca37aa60c125a5ea4343a4b18497729ac4fc39c34a02',
}
_owner = None
_runtime = None
_engine = None
_enabled = False
_host_check = False
_inherited_resume = None


def receipt(path):
    path = Path(path)
    metadata = path.lstat()
    if (not stat.S_ISREG(metadata.st_mode) or path.is_symlink()
            or metadata.st_nlink != 1 or path.resolve(strict=True) != path.absolute()):
        raise RuntimeError('exception input is indirect')
    payload = path.read_bytes()
    after = path.stat()
    stable = lambda x: (x.st_dev, x.st_ino, x.st_mode, x.st_nlink, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
    if len(payload) != metadata.st_size or stable(after) != stable(metadata):
        raise RuntimeError('exception input changed')
    return {'path': str(path), 'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}


def closure():
    paths = [SCRIPT, _owner.SCRIPT, _owner.RUNTIME_PATH, _owner.ENGINE_PATH,
             POLICY, ROOT / 'AGENTS.md',
             ROOT / 'docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md',
             ROOT / 'docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md',
             ROOT / 'tests/test_s20plus_g986n_p1_recovery_exception_v1.py']
    return {str(p.relative_to(ROOT)): receipt(p) for p in paths}


def require_review():
    info = receipt(REVIEW)
    if stat.S_IMODE(REVIEW.stat().st_mode) != 0o400:
        raise RuntimeError('exception review must be immutable')
    value = _engine.read_json(REVIEW, 'exception authorization')
    if (set(value) != {'schema', 'scope', 'binding_sha256', 'operator_policy_exception_approved',
                       'independent_review', 'closure', 'expires_unix', 'tests'}
            or value['schema'] != 's20plus_p1_recovery_exception_authorization_v1'
            or value['scope'] != SCOPE or value['binding_sha256'] != BINDING
            or value['operator_policy_exception_approved'] is not True
            or value['independent_review'] != {'verdict': 'PASS_GO', 'high': 0, 'medium': 0, 'low': 0}
            or value['closure'] != closure() or type(value['expires_unix']) is not int
            or value['tests'] != receipt(TEST_LOG)
            or stat.S_IMODE(TEST_LOG.stat().st_mode) != 0o400
            or not TEST_LOG.read_text().rstrip().endswith('OK')):
        raise RuntimeError('exception authorization differs')
    return value, info


def check_history(run_dir):
    if Path(run_dir).absolute() != RUN:
        raise RuntimeError('exception run differs')
    for name, expected in HISTORY.items():
        if receipt(RUN / name)['sha256'] != expected:
            raise RuntimeError('exception historical evidence changed')


def enable(run_dir, *, host_check=False):
    global _enabled, _host_check
    check_history(run_dir)
    if not host_check:
        require_review()
    _host_check = host_check
    _enabled = True


def require_active():
    if not _enabled:
        raise RuntimeError('exception was not selected')
    if not _host_check:
        require_review()
    check_history(RUN)


def entrypoint_allowed(name, run_dir):
    if not _enabled or run_dir != RUN:
        return False
    if name == 'resume_run':
        return True
    if name == 'finalize_resident' and not _host_check:
        try:
            return _runtime._require_live_transaction() == {'entrypoint': 'resume_run', 'run_dir': str(RUN)}
        except Exception:
            return False
    return False


def transfer_allowed(run_dir, kind, binding_sha256):
    if not (_enabled and not _host_check and run_dir == RUN and kind == 'rollback' and binding_sha256 == BINDING):
        return False
    review, _ = require_review()
    if time.time() > review['expires_unix']:
        return False
    if os.path.lexists(RUN / 'rollback-intent.json') or os.path.lexists(RUN / MISS):
        return False
    return arrival_permitted(RUN, {p.name for p in RUN.iterdir()})


def _record(name):
    return _engine.read_json(RUN / name, name)


def _same_target(endpoint):
    _engine._validate_endpoint(endpoint, 'incident Download endpoint')
    prepared = _record('prepared.json')['binding']['endpoint']
    if (endpoint['topology_sha256'] != prepared['topology_sha256']
            or endpoint['usb'] != prepared['usb']):
        raise RuntimeError('incident endpoint differs from prepared S20')


def arrival_permitted(run_dir, actual):
    if not NODES.intersection(actual):
        return False
    check_history(run_dir)
    if INTENT not in actual:
        raise RuntimeError('incident receipt lacks intent')
    intent = _record(INTENT)
    review, review_receipt = require_review()
    if (set(intent) != {'schema', 'binding_sha256', 'history', 'authorization', 'rollback_ap_sha256', 'expires_unix', 'at'}
            or intent['schema'] != SCOPE + '-intent' or intent['binding_sha256'] != BINDING
            or intent['history'] != HISTORY or intent['authorization'] != review_receipt
            or intent['rollback_ap_sha256'] != _engine.ROLLBACK_AP_SHA256
            or intent['expires_unix'] != review['expires_unix'] or not isinstance(intent['at'], str)):
        raise RuntimeError('incident intent differs')
    for name in (ARRIVAL, MISS):
        if name not in actual:
            continue
        value = _record(name)
        common = {'schema', 'binding_sha256', 'intent_sha256', 'at'}
        expected = common | ({'endpoint'} if name == ARRIVAL else {'reason'})
        if (set(value) != expected or value['schema'] != SCOPE + ('-arrival' if name == ARRIVAL else '-stop')
                or value['binding_sha256'] != BINDING or value['intent_sha256'] != _engine.digest(intent)
                or not isinstance(value['at'], str)):
            raise RuntimeError('incident receipt differs')
        if name == ARRIVAL:
            _same_target(value['endpoint'])
        elif not isinstance(value['reason'], str):
            raise RuntimeError('incident stop lacks reason')
    if MISS in actual:
        if 'rollback-intent.json' in actual:
            raise RuntimeError('stopped incident cannot have a rollback effect')
        return False
    if ARRIVAL not in actual:
        return False
    if 'rollback-intent.json' in actual:
        rollback_endpoint = _record('rollback-intent.json')['endpoint']
        _engine._validate_endpoint(rollback_endpoint, 'incident rollback endpoint')
        if not _engine.same_download_session(rollback_endpoint, _record(ARRIVAL)['endpoint']):
            raise RuntimeError('rollback endpoint differs from incident arrival')
    return True


def stop(intent, reason):
    if not os.path.lexists(RUN / MISS):
        _engine.durable_json(RUN / MISS, {
            'schema': SCOPE + '-stop', 'binding_sha256': BINDING,
            'intent_sha256': _engine.digest(intent), 'reason': reason, 'at': _engine.utc_now(),
        })


def resume(run_dir):
    require_active()
    check_history(run_dir)
    transaction = _runtime._require_live_transaction()
    if transaction != {'entrypoint': 'resume_run', 'run_dir': str(RUN)}:
        raise RuntimeError('exception lacks exact resume lease')
    e = _engine
    if os.path.lexists(RUN / 'terminal.json'):
        return _inherited_resume(RUN)
    prepared = e.read_prepared(RUN, phase='rollback')
    if prepared['binding_sha256'] != BINDING:
        raise RuntimeError('exception binding differs')
    e.require_candidate_claim(RUN, BINDING)
    e.require_all_transfer_processes_quiescent(RUN, BINDING)
    if _host_check:
        return {'verdict': 'PASS_P1_RECOVERY_HOST_CLOSURE', 'binding_sha256': BINDING, 'device_commands': 0}
    if os.path.lexists(RUN / 'rollback-intent.json'):
        if not arrival_permitted(RUN, {p.name for p in RUN.iterdir()}):
            raise RuntimeError('rollback lacks incident provenance')
        return _inherited_resume(RUN)
    if os.path.lexists(RUN / MISS):
        raise RuntimeError('incident binding already stopped')
    review, review_receipt = require_review()
    if time.time() > review['expires_unix']:
        raise RuntimeError('incident first-transfer authorization expired')
    if os.path.lexists(RUN / INTENT):
        intent = _record(INTENT)
        if not os.path.lexists(RUN / ARRIVAL):
            stop(intent, 'identification-intent-consumed-without-arrival')
            raise RuntimeError('incident identification cannot repeat')
        arrival_permitted(RUN, {p.name for p in RUN.iterdir()})
        endpoint = _record(ARRIVAL)['endpoint']
    else:
        intent = {'schema': SCOPE + '-intent', 'binding_sha256': BINDING,
                  'history': HISTORY, 'authorization': review_receipt,
                  'rollback_ap_sha256': e.ROLLBACK_AP_SHA256,
                  'expires_unix': review['expires_unix'], 'at': e.utc_now()}
        e.durable_json(RUN / INTENT, intent)
        try:
            endpoint = e.identify_download()
            _same_target(endpoint)
            e.durable_json(RUN / ARRIVAL, {
                'schema': SCOPE + '-arrival', 'binding_sha256': BINDING,
                'intent_sha256': e.digest(intent), 'endpoint': endpoint, 'at': e.utc_now(),
            })
        except Exception as error:
            stop(intent, 'identification-failed-' + type(error).__name__)
            raise
    try:
        return e.rollback_from_arrival(RUN, prepared, endpoint)
    except Exception as error:
        if not os.path.lexists(RUN / 'rollback-intent.json'):
            stop(intent, 'before-transfer-failed-' + type(error).__name__)
        raise


def install(owner, runtime):
    global _owner, _runtime, _engine, _inherited_resume
    _owner, _runtime, _engine = owner, runtime, runtime.engine
    _inherited_resume = _engine.resume_run
    runtime.P0_RECOVERY_PREDECESSOR_NORMALIZED_SHA256 = frozenset((OLD_ENGINE_NORMALIZED,))
    runtime.P0_RUN_NODE_NAMES = runtime.P0_RUN_NODE_NAMES | NODES
    runtime._profile_entrypoint_allowed = entrypoint_allowed
    runtime._profile_transfer_allowed = transfer_allowed
    _engine.profile_recovery_arrival_permitted = arrival_permitted
    _engine.resume_run = resume
