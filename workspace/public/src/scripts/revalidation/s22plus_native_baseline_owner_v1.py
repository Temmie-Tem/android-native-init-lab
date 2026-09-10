"""Finite attended native-baseline owner; ordinary candidate claims stay consumed.

Preparation is H0. Only a returned exact operator approval and actual attendance
can open a grant. A durable operation or delivery intent is never replayed;
restart enters recovery-only handling. The existing target lease, descriptor
guard, measured Download observer, boot-only Odin transport and D0 reader remain
the device-facing implementations.
"""
from __future__ import annotations

import argparse
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
import uuid

import device_action_f1_v2 as core
import device_action_cdc_acm_observer_v1 as records
import consumed_candidate_registry_v1 as registry
import s22plus_native_baseline_protocol_v1 as protocol
import s22plus_native_roundtrip_owner_v1 as roundtrip
from s22plus_native_console_owner_v1 import ReturnHost

ROOT = Path(__file__).resolve().parents[5]
SCHEMA = 's22plus-native-baseline-owner-v1'
BASE = Path('workspace/private/runs/s22plus-native-baseline-v1')
ADMISSIONS = Path('workspace/private/device-action/s22plus-native-baseline-v1')
REVIEW = Path('workspace/public/src/device-action/bindings/s22plus_native_baseline_v1_review.json')
POLICY = 'docs/operations/S22PLUS_NATIVE_BASELINE_V1.md'
PROFILE = 'workspace/public/src/device-action/profiles/s22plus_fyg8.json'
APPROVAL_PREFIX = 'S22PLUS_NATIVE_BASELINE_V1_APPROVE:'
LIMITS = dict(reservations=3, seconds=600, native_authentications=8, native_boot_ms=900000,
              android_transfers_per_operation=1)
OPERATIONS = ('bootstrap', 'restore', 'android-exit')
PHASES = {'bootstrap-first':'pair-control', 'native-start':'control', 'native-final':'pair-detach',
          'android-start':None, 'android-exit':None}
TRANSFER_NATIVE, TRANSFER_ANDROID = 'native-baseline', 'baseline-android'
STOP = 'research-stop.json'
_READ_CACHE = ContextVar('native_baseline_read_cache', default=None)


def read_transaction(function):
    """Share retained proof only within one read-only rederivation."""
    @wraps(function)
    def call(*args, **kwargs):
        if _READ_CACHE.get() is not None: return function(*args, **kwargs)
        token = _READ_CACHE.set({})
        try: return function(*args, **kwargs)
        finally: _READ_CACHE.reset(token)
    return call


class BaselineError(core.F1V2Error):
    pass


def require(condition, reason):
    if not condition:
        raise BaselineError(reason)


def same(a, b):
    return core.json_sha256(a) == core.json_sha256(b)


def direct(root, path, *, private=True):
    path = Path(path)
    path = path.absolute() if path.is_absolute() else (root/path).absolute()
    require(path.resolve() == path and path.is_relative_to(root/('workspace/private' if private else '')),
            'baseline path is indirect or outside its root')
    return path


def read(path):
    value, receipt = core.load_json(Path(path), 'native baseline record')
    info = Path(path).stat()
    require(stat.S_IMODE(info.st_mode) == 0o400 and info.st_nlink == 1 and info.st_uid == os.getuid(),
            'baseline record ownership, mode or links differ')
    return value, receipt


def pin(path):
    return core._stable_read(Path(path), 'native baseline input', core.MAX_JSON)[1]


def publish(path, value):
    large = (Path(path).name in ('request.json','terminal.json') or 'installation_claim' in value)
    if large:
        payload = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()
        require(len(payload) <= core.MAX_JSON, 'baseline structured result exceeds its one-MiB reader bound')
        records._write_exclusive(Path(path), payload)
    else:
        core._write_exclusive(Path(path), value)
    actual, receipt = read(path)
    require(same(actual, value), 'baseline durable record readback differs')
    return receipt


def verify_pin(root, receipt):
    core._exact(receipt, {'path','size','sha256'}, 'baseline input receipt')
    path = direct(root, receipt['path'], private=False)
    require(same(pin(path), dict(receipt, path=str(path))), 'baseline bound input changed')
    return path


def host_epoch():
    return ReturnHost.host_boot_sha256()


def current_static():
    analysis = ROOT/'workspace/public/src/scripts/analysis'
    if str(analysis) not in sys.path: sys.path.insert(0, str(analysis))
    import s22plus_fyg8_p385_process_v2_candidate_static as static_candidate
    return static_candidate


def reviewed(root):
    value, receipt = core.load_json(root/REVIEW, 'native baseline capability review')
    static_candidate = current_static()
    require(value.get('verdict') == 'PASS_GO' and value.get('findings') == []
            and value.get('activation') == SCHEMA and same(value.get('limits'), LIMITS),
            'native baseline capability has no exact activated independent review')
    require(same(value.get('current_sources'), static_candidate.source_receipts()),
            'native baseline reviewed execution sources changed')
    return receipt


def bundle_snapshot(bundle):
    return dict(profile=bundle.profile, manifest=bundle.manifest, receipt=bundle.receipt, sha256=bundle.sha256)


def snapshot_bundle(value):
    core._exact(value, {'profile','manifest','receipt','sha256'}, 'baseline frozen bundle')
    require(value['sha256'] == core.json_sha256(value['receipt']), 'baseline frozen bundle digest differs')
    bundle = core.Bundle(**value)
    require(bundle.manifest['target_profile'] == PROFILE
            and {k:bundle.profile['target'][k] for k in ('model','device','firmware_incremental')}
                == {'model':'SM-S906N','device':'g0q','firmware_incremental':'S906NKSS7FYG8'},
            'native baseline target differs')
    return bundle


def native_identity(bundle):
    static_candidate = current_static()
    declaration = static_candidate.declaration
    require(bundle.manifest['observation']['acceptance']['run_id'] == declaration.IDENTITY.run_id_hex,
            'native baseline requires the exact direct P385 declaration')
    return dict(candidate=bundle.receipt['candidate_ap'], profile=protocol.source.profile_contract(protocol.source.BASELINE_PROFILE),
        run_id=declaration.IDENTITY.run_id_hex, auth_key=dict(declaration.artifact.auth_key_identity()),
        native_sources=static_candidate.builder.source_receipts())


def prepare_request(live, root, output, *, manifest, target_file, operations, reservations=1, seconds=600):
    """Freeze a reviewable proposal without D0, a grant or an operation owner."""
    root = Path(root).resolve(); output = direct(root, output)
    require(output.is_relative_to(root/BASE) and not os.path.lexists(output), 'fresh baseline request directory required')
    require(type(operations) is list and 0 < len(operations) <= 3
            and len(set(operations)) == len(operations) and all(x in OPERATIONS for x in operations),
            'baseline operation set differs')
    require(type(reservations) is int and 1 <= reservations <= LIMITS['reservations']
            and type(seconds) is int and 1 <= seconds <= LIMITS['seconds'], 'baseline finite limits differ')
    bundle = core.verify_bundle(root, direct(root, manifest, private=False), runtime_bound=True)
    authority = reviewed(root)
    target, _ = core.load_json(direct(root, target_file), 'exact baseline private target')
    core._exact(target, {'serial','topology'}, 'baseline target')
    require(type(target['serial']) is str and live.d0.SERIAL_RE.fullmatch(target['serial'])
            and target['topology'] == live.p324_typec_lane.SOURCE_TOPOLOGY, 'baseline target grammar/lane differs')
    value = request_value(live, root, bundle, target=target, manifest_receipt=pin(direct(root,manifest,private=False)),
        review_receipt=authority, operations=operations, reservations=reservations, seconds=seconds)
    output.mkdir(parents=True, mode=0o700); core._fsync_dir(output.parent)
    receipt = publish(output/'request.json', value)
    return dict(request=receipt, approval=APPROVAL_PREFIX+receipt['sha256'], live_authorized=False)


def request_value(live, root, bundle, *, target, manifest_receipt, review_receipt, operations, reservations, seconds, closure=None):
    """One request layout for real preparation and actual-size H0 serialization."""
    return dict(schema=SCHEMA, kind='request', target=target, manifest=manifest_receipt,
        bundle=bundle_snapshot(bundle), review=review_receipt, closure=live._closure(root, bundle) if closure is None else closure,
        native=native_identity(bundle), android=roundtrip.android_identity(bundle),
        operations=operations, reservations=reservations, seconds=seconds,
        physical_attendance_required=True, recovery='one-exact-android', live_authorized=False)


def load_request(live, root, path, *, current=False):
    path = direct(root, path)
    require(path.is_relative_to(root/BASE) and path.name == 'request.json', 'baseline request path differs')
    value, receipt = read(path)
    core._exact(value, {'schema','kind','target','manifest','bundle','review','closure','native','android',
        'operations','reservations','seconds','physical_attendance_required','recovery','live_authorized'}, 'baseline request')
    require(value['schema'] == SCHEMA and value['kind'] == 'request' and value['live_authorized'] is False
            and value['physical_attendance_required'] is True and value['recovery'] == 'one-exact-android',
            'baseline request authority differs')
    require(type(value['reservations']) is int and 1 <= value['reservations'] <= LIMITS['reservations']
            and type(value['seconds']) is int and 1 <= value['seconds'] <= LIMITS['seconds']
            and type(value['operations']) is list and 0 < len(value['operations']) <= 3
            and len(set(value['operations'])) == len(value['operations'])
            and all(x in OPERATIONS for x in value['operations']), 'baseline request limits differ')
    core._exact(value['target'], {'serial','topology'}, 'baseline request target')
    bundle = snapshot_bundle(value['bundle'])
    if current:
        require(same(reviewed(root), value['review']), 'baseline request review changed')
        fresh = core.verify_bundle(root, verify_pin(root, value['manifest']), runtime_bound=True)
        require(same(bundle_snapshot(fresh), value['bundle']) and same(live._closure(root, fresh), value['closure'])
                and same(native_identity(fresh), value['native']) and same(roundtrip.android_identity(fresh), value['android']),
                'baseline request sources or N/A artifacts changed')
    return value, receipt, bundle


def open_grant(live, root, request, approval, *, attended):
    require(attended is True, 'actual current operator attendance is required')
    root = Path(root).resolve(); request = direct(root, request)
    with registry.target_session_lease(root):
        registry.require_no_f1_owner(root)
        value, receipt, _ = load_request(live, root, request, current=True)
        require(type(approval) is str and approval == APPROVAL_PREFIX+receipt['sha256'],
                'exact returned native-baseline approval required')
        # One proposal can open one grant. Expiry never renews it.
        start = protocol.host_now_ns()
        grant = dict(schema=SCHEMA, kind='grant', request=receipt, operator_approval=approval,
            attended=True, host_boot_sha256=host_epoch(), started_boottime_ns=start,
            deadline_boottime_ns=start+value['seconds']*10**9)
        return publish(request.parent/'grant.json', grant)


def load_grant(live, root, path, *, active=False):
    path = direct(root, path)
    require(path.is_relative_to(root/BASE) and path.name == 'grant.json', 'baseline grant path differs')
    grant, receipt = read(path)
    core._exact(grant, {'schema','kind','request','operator_approval','attended','host_boot_sha256',
        'started_boottime_ns','deadline_boottime_ns'}, 'baseline grant')
    request, request_receipt, bundle = load_request(live, root, path.parent/'request.json')
    require(grant['schema'] == SCHEMA and grant['kind'] == 'grant' and same(grant['request'], request_receipt)
            and grant['operator_approval'] == APPROVAL_PREFIX+request_receipt['sha256'] and grant['attended'] is True,
            'baseline grant authority differs')
    require(type(grant['started_boottime_ns']) is int and grant['started_boottime_ns'] > 0
            and type(grant['deadline_boottime_ns']) is int
            and grant['deadline_boottime_ns']-grant['started_boottime_ns'] == request['seconds']*10**9
            and type(grant['host_boot_sha256']) is str and re.fullmatch('[0-9a-f]{64}', grant['host_boot_sha256']),
            'baseline grant clock binding differs')
    if active:
        require(same(reviewed(root), request['review']), 'baseline active grant review/source changed')
        require(not os.path.lexists(path.parent/'closed.json') and grant['host_boot_sha256'] == host_epoch()
                and grant['started_boottime_ns'] <= protocol.host_now_ns() < grant['deadline_boottime_ns'],
                'baseline grant closed, expired or changed host epoch')
    return grant, receipt, request, bundle


@dataclass(frozen=True)
class Operation:
    root: Path
    directory: Path
    value: dict
    receipt: dict
    grant: dict
    request: dict
    bundle: core.Bundle

    @property
    def binding(self): return self.receipt['sha256']


def load_operation(live, root, directory, *, active=False):
    directory = direct(root, directory)
    value, receipt = read(directory/'operation.json')
    core._exact(value, {'schema','kind','grant','ordinal','operation','origin','prior_native'}, 'baseline operation')
    require(value['schema'] == SCHEMA and value['kind'] == 'operation'
            and type(value['ordinal']) is int and 1 <= value['ordinal'] <= 3
            and value['operation'] in OPERATIONS and value['origin'] in ('android','native','physical-download'),
            'baseline operation shape differs')
    grant_path = directory.parent/'grant.json'
    require(directory.name == f"operation-{value['ordinal']:02d}", 'baseline ordinal path differs')
    grant, gp, request, bundle = load_grant(live, root, grant_path, active=active)
    reservation, _ = read(directory.parent/f"{value['ordinal']:02d}-reserved.json")
    require(same(gp, value['grant']) and same(reservation, value) and value['ordinal'] <= request['reservations']
            and value['operation'] in request['operations'], 'baseline reservation differs')
    require((value['origin'] == 'native') is (value['prior_native'] is not None)
            and (value['operation'] != 'bootstrap' or value['origin'] == 'android')
            and (value['origin'] != 'physical-download' or value['operation'] == 'android-exit'),
            'baseline origin/operation binding differs')
    if active:
        registry.require_f1_owner(root, directory, receipt['sha256'])
        require(not os.path.lexists(directory/STOP) and not os.path.lexists(directory/'terminal.json'),
                'baseline operation is stopped or closed')
    return Operation(root, directory, value, receipt, grant, request, bundle)


def phase_prepared(live, operation, name, *, create=False):
    require(name in PHASES, 'unknown native baseline phase')
    path = operation.directory/name
    context = dict(schema=SCHEMA, operation=str(operation.directory), phase=name, mode=PHASES[name],
                   operation_sha256=operation.binding)
    if create:
        if os.path.lexists(path):
            require(path.is_dir() and not path.is_symlink() and not any(path.iterdir()),
                    'only an empty interrupted phase directory may be completed')
        else:
            path.mkdir(mode=0o700); core._fsync_dir(path.parent)
        publish(path/'phase.json', context)
    stored, _ = read(path/'phase.json')
    require(same(stored, context), 'native baseline phase changed')
    lane_path = operation.directory/live.P324_TYPEC_LANE_NAME
    prepared = dict(approval_binding_sha256=operation.binding, execution_closure=operation.request['closure'],
        p328_auth_key_identity=operation.request['native']['auth_key'],
        approval_binding=dict(p328_auth_key_identity=operation.request['native']['auth_key']),
        p324_typec_lane_binding=pin(lane_path))
    return live.PreparedRun(operation.root, path, operation.bundle, prepared,
        dict(schema=live.PRIVATE_TARGET_SCHEMA, **operation.request['target']),
        native_parent=operation.directory, native_baseline_context=context)


def validate_observation_context(live, prepared):
    context = prepared.native_baseline_context
    require(type(context) is dict and set(context) == {'schema','operation','phase','mode','operation_sha256'},
            'baseline observer context fields differ')
    operation = load_operation(live, prepared.root, context['operation'])
    expected = phase_prepared(live, operation, context['phase'])
    require(PHASES[context['phase']] is not None and same(context, expected.native_baseline_context)
            and expected.run_dir == prepared.run_dir and expected.binding_sha256 == prepared.binding_sha256
            and same(bundle_snapshot(expected.bundle), bundle_snapshot(prepared.bundle))
            and same(expected.prepared, prepared.prepared) and same(expected.private_target, prepared.private_target),
            'baseline observation is outside its exact operation/phase')
    return context


def before_native_auth(live, prepared):
    context = validate_observation_context(live, prepared)
    return load_operation(live, prepared.root, context['operation'], active=True)


def before_native_terminal(live, prepared, request, index, expiry):
    operation = before_native_auth(live, prepared)
    phase = prepared.native_baseline_context['phase']
    require(request['run_id_hex'] == operation.request['native']['run_id']
            and type(index) is int and index in (1,2), 'baseline native request identity differs')
    info = request['baseline_info']
    if phase == 'native-start':
        previous = native_terminal(live, operation.root, verify_pin(operation.root, operation.value['prior_native']).parent)
        row = previous['proof']['sessions'][-1]
        protocol.fresh_same_boot(row, request, seen_nonce_hashes=previous['seen_nonce_hashes'])
        require(index == 1 and expiry <= previous['native_expiry_boottime_ns']
                and previous['host_boot_sha256'] == host_epoch(), 'native start original lifetime differs')
    elif index == 1:
        require(info['authentication_ordinal'] == 1 and info['preparation_cached'] is False,
                'new baseline arrival did not start with its first authentication')
        if phase == 'native-final':
            prior_name = 'bootstrap-first' if operation.value['operation'] == 'bootstrap' else 'native-start'
            if (operation.directory/prior_name/'candidate-observer.json').exists():
                prior = observation(live, phase_prepared(live, operation, prior_name))
                require(request['kernel_boot_identity_sha256'] != prior['proof']['kernel_boot_identity_sha256']
                        and request['nonce_sha256'] not in [row['nonce_sha256'] for row in prior['proof']['sessions']],
                        'baseline restoration new boot/nonce is unproved')


def observation(live, prepared):
    value = live._p345_validate_receipt(prepared, prepared.run_dir/'candidate-observer.json',
        prepared.bundle.manifest['observation']['candidate_observer'])
    require(value['accepted'] is True, 'native baseline observation did not qualify')
    guard = live._reopen_candidate_guard_release(prepared)
    require(live._observer_guard_supports_result(accepted=True, status=guard['status'], released=guard['released']),
            'native baseline descriptor guard did not close')
    return value


def stop(operation, reason):
    if not os.path.lexists(operation.directory/STOP):
        publish(operation.directory/STOP, dict(schema=SCHEMA, operation=operation.receipt,
            reason=reason, native_replay_forbidden=True, stopped_boottime_ns=protocol.host_now_ns()))
    path = operation.directory.parent/'closed.json'
    if not os.path.lexists(path):
        publish(path, dict(schema=SCHEMA, reason='research-stopped', operation=operation.receipt))


def validate_arm(live, prepared, endpoint, kind, attempt, prefix):
    """Final shared-transport gate, after role intent and before its sole delivery."""
    context = prepared.native_baseline_context
    require(type(context) is dict, 'baseline transfer has no exact owner')
    operation = load_operation(live, prepared.root, context['operation'], active=kind == TRANSFER_NATIVE)
    registry.require_f1_owner(operation.root, operation.directory, operation.binding)
    require(kind in (TRANSFER_NATIVE, TRANSFER_ANDROID) and type(attempt) is int and attempt == 1
            and prefix == kind+'-attempt-01', 'baseline transfer role/attempt differs')
    stored = phase_prepared(live, operation, context['phase'])
    require(stored == prepared, 'baseline transfer prepared identity differs')
    intent, intent_pin = read(prepared.run_dir/(prefix+'.start.json'))
    expected = role_intent(live, operation, prepared, endpoint, kind)
    require(same(intent, expected), 'baseline transfer exact role intent differs')
    # Delivery is exclusive even when the transport call never returns.
    publish(prepared.run_dir/(prefix+'.delivery.json'), dict(schema=SCHEMA, intent=intent_pin))


def role_intent(live, operation, prepared, endpoint, kind):
    native = kind == TRANSFER_NATIVE
    name = prepared.native_baseline_context['phase']
    require(kind in (TRANSFER_NATIVE, TRANSFER_ANDROID)
            and (name in ('bootstrap-first','native-final') if native else name == 'android-exit'),
            'baseline transfer phase differs')
    require(endpoint.arrival_receipt is not None, 'baseline transfer requires measured exact Download arrival')
    arrival = live._read_native_download_arrival(prepared, endpoint.arrival_receipt)
    require(same(arrival['endpoint'], dict(device=endpoint.device, sequence=endpoint.sequence,
                identity_sha256=endpoint.identity_sha256)), 'baseline Download ticket changed')
    require(same(live._closure(operation.root, operation.bundle), operation.request['closure']),
            'baseline execution closure changed at transfer')
    if native:
        require(same(native_identity(operation.bundle), operation.request['native']), 'baseline native image sources changed')
        if operation.value['operation'] == 'bootstrap':
            identity = live._bound_candidate_registry_identity(primary_prepared(live, operation))
            claim = registry.active_claim(operation.root, identity['candidate_key'])
            require(claim is not None and all(claim.get(k) == v for k,v in identity.items() if k != 'schema'),
                    'bootstrap original native installation claim is missing')
        else:
            admission(live, operation.root, operation.request['native'], target=operation.request['target'])
        if name == 'bootstrap-first':
            require(operation.value['operation'] == 'bootstrap', 'only bootstrap can install an unregistered baseline')
            android_health(live, operation, operation.directory/'android-start'/'health')
        else:
            require(operation.value['operation'] in ('bootstrap','restore'), 'operation cannot restore native')
            origin_phase = ('bootstrap-first' if operation.value['operation'] == 'bootstrap'
                            else 'native-start' if operation.value['origin'] == 'native' else 'android-start')
            if origin_phase == 'android-start': android_health(live, operation, operation.directory/origin_phase/'health')
            else: timely_return(live, phase_prepared(live, operation, origin_phase))
    return bound_role_value(operation, prepared, endpoint, kind)


def bound_role_value(operation, prepared, endpoint, kind):
    return dict(schema=SCHEMA, kind=kind, attempt=1, operation=operation.receipt,
        phase=prepared.native_baseline_context['phase'],
        endpoint=dict(device=endpoint.device, sequence=endpoint.sequence, identity_sha256=endpoint.identity_sha256),
        arrival=endpoint.arrival_receipt,
        artifact=operation.request['native']['candidate'] if kind == TRANSFER_NATIVE else operation.request['android'])


def primary_prepared(live, operation):
    return live.PreparedRun(operation.root, operation.directory, operation.bundle,
        dict(approval_binding_sha256=operation.binding), dict(schema=live.PRIVATE_TARGET_SCHEMA, **operation.request['target']))


def initial_departure(live, prepared):
    """Known exact Download departure after this phase's completed N transfer."""
    if prepared.native_baseline_context['phase'] == 'native-start': return None
    prefix = TRANSFER_NATIVE+'-attempt-01'
    result = live._validate_transfer_result(prepared, TRANSFER_NATIVE, 1)
    require(result is not None and result['classification'] == 'odin_transfer_completed', 'baseline departure lacks completed transfer')
    intent, intent_pin = read(prepared.run_dir/(prefix+'.start.json'))
    delivery, _ = read(prepared.run_dir/(prefix+'.delivery.json'))
    require(same(delivery, dict(schema=SCHEMA, intent=intent_pin)), 'baseline delivery record differs')
    arrival = live._read_native_download_arrival(prepared, intent['arrival'])
    operation = load_operation(live, prepared.root, prepared.native_parent)
    endpoint = live.Endpoint(**arrival['endpoint'], arrival_receipt=intent['arrival'])
    require(same(intent, bound_role_value(operation,prepared,endpoint,TRANSFER_NATIVE)),
            'native role retained authority/artifact differs')
    return arrival['endpoint']['device'], arrival['revalidation']['device_identity']


def android_health(live, operation, directory):
    value, _ = read(directory/'result.json')
    live.d0.validate_result(value, operation.bundle, directory)
    target = value['target_evidence']['targets']
    require(len(target) == 1 and target[0]['adb_serial_sha256'] == hashlib.sha256(operation.request['target']['serial'].encode()).hexdigest()
            and target[0]['usb_topology_sha256'] == hashlib.sha256(operation.request['target']['topology'].encode()).hexdigest(),
            'baseline Android health belongs to another target')
    return value


def timely_return(live, prepared):
    value = observation(live, prepared)
    require(value['proof']['control_acceptance_observed'] is True, 'normal baseline restoration lacks native CONTROL proof')
    host = live._return_host_for(prepared)
    intent, intent_pin = host.read_intent(prepared.run_dir, binding=live._candidate_observer_binding(prepared), proof=value['proof'])
    window, _ = read(prepared.run_dir/host.WINDOW_NAME)
    host.validate_window(window, binding=live._candidate_observer_binding(prepared), intent=intent, intent_receipt=intent_pin)
    require(window['outcome'] == 'exact-download-within-control-window'
            and window['observed_within_software_deadline'] is True, 'baseline normal return missed original Download window')
    arrival = live._read_native_download_arrival(prepared, window['rollback_topology_record'])
    require(arrival['host_boot_sha256'] == window['host_boot_sha256']
            and intent['created_monotonic_ns'] <= arrival['observed_monotonic_ns'] <= window['closed_monotonic_ns'],
            'baseline return arrival is outside original CONTROL window')
    timing, _ = read(prepared.run_dir/'native-return-boottime.json')
    index = value['proof']['session_count']
    check, check_pin = read(prepared.run_dir/f'p385-native-auth-{index:02d}.terminal-check.json')
    core._exact(timing, {'schema','terminal_check','window','closed_boottime_ns'}, 'native return elapsed time')
    require(timing['schema'] == SCHEMA and same(timing['terminal_check'], check_pin)
            and same(timing['window'], pin(prepared.run_dir/host.WINDOW_NAME))
            and type(timing['closed_boottime_ns']) is int
            and check['created_boottime_ns'] <= timing['closed_boottime_ns'] <= check['created_boottime_ns']+30*10**9,
            'native normal return exceeded its suspend-aware CONTROL window')
    return window


@read_transaction
def native_terminal(live, root, directory):
    """Rederive retained native proof; this is a past health snapshot, not a lease."""
    operation = load_operation(live, root, directory)
    terminal, receipt = read(operation.directory/'terminal.json')
    require(terminal.get('state') == 'NATIVE_CLOSED', 'operation has no native terminal')
    key = (str(operation.directory), receipt['sha256'])
    cache = _READ_CACHE.get()
    if key in cache: return cache[key]
    derived = native_terminal_value(live, operation)
    require(same(terminal, derived), 'native terminal does not rederive from raw/close evidence')
    cache[key] = derived
    return derived


@read_transaction
def native_terminal_value(live, operation):
    final = phase_prepared(live, operation, 'native-final')
    value = observation(live, final)
    proof = value['proof']
    require(proof['mode'] == 'pair-detach' and proof['remaining_authentications'] >= 1
            and value['native_descriptor_close_completed'] is True, 'native terminal is not reattachable')
    first = proof['sessions'][0]
    require(first['baseline_info']['authentication_ordinal'] == 1 and first['baseline_info']['preparation_cached'] is False,
            'final native boot did not begin with its first authentication')
    result = live._validate_transfer_result(final, TRANSFER_NATIVE, 1)
    require(result is not None and result['classification'] == 'odin_transfer_completed', 'native terminal has no completed exact N role')
    initial_departure(live, final)
    native_proofs = []
    if operation.value['operation'] != 'bootstrap':
        admission(live, operation.root, operation.request['native'], target=operation.request['target'])
    if operation.value['operation'] == 'bootstrap':
        previous = phase_prepared(live, operation, 'bootstrap-first')
        initial_departure(live, previous); timely_return(live, previous)
        native_proofs = [observation(live, previous)['proof']]
    elif operation.value['origin'] == 'native':
        previous = phase_prepared(live, operation, 'native-start')
        timely_return(live, previous); native_proofs = [observation(live, previous)['proof']]
    else:
        android_health(live, operation, operation.directory/'android-start'/'health')
    for previous in native_proofs:
        require(proof['kernel_boot_identity_sha256'] != previous['kernel_boot_identity_sha256']
                and not {r['nonce_sha256'] for r in proof['sessions']} & {r['nonce_sha256'] for r in previous['sessions']},
                'native restoration boot/nonce freshness is unproved')
    close, _ = read(final.run_dir/'p385-native-auth-02.close-result.json')
    auth, _ = read(final.run_dir/'p385-native-auth-02.intent.json')
    require(close['completed_boottime_ns'] <= operation.grant['deadline_boottime_ns']
            and auth['host_boot_sha256'] == operation.grant['host_boot_sha256'],
            'native terminal closed outside original grant')
    require(not os.path.lexists(operation.directory/'android-exit'/(TRANSFER_ANDROID+'-attempt-01.start.json')),
            'native terminal follows an Android transfer intent')
    return dict(schema=SCHEMA, state='NATIVE_CLOSED', operation=operation.receipt,
        target=operation.request['target'],
        proof=proof, observer=pin(final.run_dir/'candidate-observer.json'),
        endpoint_identity_sha256=value['endpoint_identity_sha256'],
        host_boot_sha256=auth['host_boot_sha256'], native_expiry_boottime_ns=close['native_expiry_boottime_ns'],
        closed_boottime_ns=close['completed_boottime_ns'], seen_nonce_hashes=[r['nonce_sha256'] for r in proof['sessions']],
        native=operation.request['native'], android_available=operation.request['android'], android_transferred=False,
        recovery_required=False, health_scope='past-authenticated-native-snapshot')


def admission_path(root, native):
    key = core.json_sha256({k:v for k,v in native.items() if k != 'candidate'} | {
        'candidate':{k:v for k,v in native['candidate'].items() if k != 'path'}})
    return root/ADMISSIONS/(key+'.json')


def admission(live, root, native, *, target=None):
    value, receipt = read(admission_path(root, native))
    core._exact(value, {'schema','target','native','qualification','installation_claim'}, 'native admission')
    require(value['schema'] == SCHEMA and same(value['native'], native), 'native admission identity differs')
    path = verify_pin(root, value['qualification'])
    terminal = native_terminal(live, root, path.parent)
    operation = load_operation(live, root, path.parent)
    require(operation.value['operation'] == 'bootstrap' and same(terminal['native'], native),
            'native admission lacks complete bootstrap qualification')
    require(same(value['target'], operation.request['target']) and (target is None or same(target,value['target'])),
            'native admission belongs to another physical target')
    identity = live._bound_candidate_registry_identity(primary_prepared(live, operation))
    claim = registry.active_claim(root, identity['candidate_key'])
    require(claim is not None and same(claim, value['installation_claim'])
            and all(claim.get(k) == v for k,v in identity.items() if k != 'schema'),
            'admitted native original installation claim changed')
    return value, receipt


def register_admission(live, operation):
    require(operation.value['operation'] == 'bootstrap', 'only bootstrap may admit a native image')
    terminal = native_terminal(live, operation.root, operation.directory)
    identity = live._bound_candidate_registry_identity(primary_prepared(live, operation))
    claim = registry.active_claim(operation.root, identity['candidate_key'])
    require(claim is not None and all(claim.get(k) == v for k,v in identity.items() if k != 'schema'),
            'bootstrap claim is missing')
    value = dict(schema=SCHEMA, target=operation.request['target'], native=terminal['native'],
        qualification=pin(operation.directory/'terminal.json'), installation_claim=claim)
    path = admission_path(operation.root, terminal['native'])
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.path.lexists(path): require(same(read(path)[0], value), 'native admission already belongs to another qualification')
    else: publish(path, value)
    return admission(live, operation.root, terminal['native'])[1]


def journal(operation, action=None, **details):
    """Append-only immutable event files; role intents remain effect authority."""
    directory = operation.directory/'journal'
    if not directory.exists(): directory.mkdir(mode=0o700)
    previous = '0'*64; records = []
    for index, path in enumerate(sorted(directory.iterdir()), 1):
        require(path.name == f'{index:03d}.json', 'baseline journal gap or unknown file')
        value, receipt = read(path)
        core._exact(value, {'schema','operation','sequence','previous_sha256','action','details'}, 'baseline journal event')
        require(value['schema'] == SCHEMA and same(value['operation'], operation.receipt)
                and type(value['sequence']) is int and value['sequence'] == index
                and value['previous_sha256'] == previous and type(value['action']) is str
                and type(value['details']) is dict, 'baseline journal chain differs')
        records.append(value); previous = receipt['sha256']
    if action is not None:
        require(len(records) < 64 and action not in [r['action'] for r in records],
                'baseline journal action already consumed or exhausted')
        publish(directory/f'{len(records)+1:03d}.json', dict(schema=SCHEMA, operation=operation.receipt,
            sequence=len(records)+1, previous_sha256=previous, action=action, details=details))
    return records


def reserve(live, root, grant_path, operation_name, origin, prior_native=None):
    """Caller holds target lease. Reservation survives every later failure."""
    grant_path = direct(root, grant_path)
    grant, gp, request, bundle = load_grant(live, root, grant_path, active=True)
    load_request(live, root, grant_path.parent/'request.json', current=True)
    registry.require_no_f1_owner(root)
    require(operation_name in request['operations'] and origin in ('android','native','physical-download'),
            'operation outside the finite grant')
    require((origin == 'native') is (prior_native is not None)
            and (operation_name != 'bootstrap' or origin == 'android')
            and (origin != 'physical-download' or operation_name == 'android-exit'), 'baseline operation origin differs')
    if operation_name != 'bootstrap': admission(live, root, request['native'], target=request['target'])
    else: require(not os.path.lexists(admission_path(root, request['native'])), 'registered image cannot bootstrap again')
    prior = None
    if prior_native is not None:
        prior_path = direct(root, prior_native)
        require(prior_path.name == 'terminal.json', 'native start needs its exact previous terminal')
        prior_value = native_terminal(live, root, prior_path.parent)
        require(same(prior_value['native'], request['native'])
                and same(prior_value['target'], request['target'])
                and prior_value['host_boot_sha256'] == host_epoch()
                and protocol.host_now_ns() < prior_value['native_expiry_boottime_ns'],
                'previous native snapshot is outside its original image/host/boot lifetime')
        require(not os.path.lexists(prior_path.parent/'next-operation.json'), 'native terminal already has a later owner')
        prior = pin(prior_path)
    ordinal = 1
    while os.path.lexists(grant_path.parent/f'{ordinal:02d}-reserved.json'):
        previous = load_operation(live, root, grant_path.parent/f'operation-{ordinal:02d}')
        terminal = validate_terminal(live, previous)
        require(terminal['state'] in ('NATIVE_CLOSED','ANDROID_CLOSED'), 'prior operation is unresolved or failed')
        require(read(previous.directory/'completed.json')[0]['terminal'] == pin(previous.directory/'terminal.json'),
                'prior baseline owner has not completed')
        ordinal += 1
    require(ordinal <= request['reservations'], 'baseline reservation budget exhausted')
    value = dict(schema=SCHEMA, kind='operation', grant=gp, ordinal=ordinal,
        operation=operation_name, origin=origin, prior_native=prior)
    publish(grant_path.parent/f'{ordinal:02d}-reserved.json', value)
    directory = grant_path.parent/f'operation-{ordinal:02d}'
    directory.mkdir(mode=0o700); core._fsync_dir(directory.parent)
    receipt = publish(directory/'operation.json', value)
    registry.begin_f1_owner(root, directory, receipt['sha256'])
    operation = load_operation(live, root, directory)
    if prior is not None:
        publish(Path(prior['path']).parent/'next-operation.json', dict(schema=SCHEMA, operation=receipt))
    journal(operation, 'reserved', operation_name=operation_name, origin=origin)
    return operation


def collect_android(live, operation, backend, phase, *, final=False):
    directory = phase.run_dir/'health'
    if final:
        require(not os.path.lexists(phase.run_dir/'final-health-complete.json'), 'final Android health already complete')
        ordinal = 2
        while os.path.lexists(directory):
            directory = phase.run_dir/f'health-attempt-{ordinal:03d}'; ordinal += 1
    else:
        require(not os.path.lexists(directory), 'Android health acquisition already exists')
    directory.mkdir(mode=0o700)
    client = live.d0.adb_client_for_bundle(backend.adb, operation.bundle)
    client.bind_raw_capture_dir(directory)
    if final:
        # Existing bounded rooted-Android return waiter. The full fixed D0 raw
        # consumer below independently reopens the resulting health evidence.
        backend._wait_final_health(phase, client)
    require(client.one_serial() == operation.request['target']['serial']
            and client.topology(operation.request['target']['serial']) == operation.request['target']['topology'],
            'Android health live target differs')
    live.d0.collect_connected(operation.bundle, directory, client, backend.usb_root)
    result = android_health(live, operation, directory)
    if final:
        publish(phase.run_dir/'final-health-complete.json', dict(schema=SCHEMA, operation=operation.receipt,
            result=pin(directory/'result.json')))
    journal(operation, phase.native_baseline_context['phase']+'-health', result=pin(directory/'result.json'))
    return result


def request_android_download(live, operation, backend, prepared):
    load_operation(live, operation.root, operation.directory, active=True)
    health_path = prepared.run_dir/'health'/'result.json'
    android_health(live, operation, health_path.parent)
    intent = publish(prepared.run_dir/'download-request-intent.json', dict(schema=SCHEMA,
        operation=operation.receipt, health=pin(health_path), mode='download'))
    journal(operation, 'android-download-request', intent=intent)
    backend.client.bind_raw_capture_dir(prepared.run_dir)
    backend.request_download(prepared)
    publish(prepared.run_dir/'download-request-result.json', dict(schema=SCHEMA, intent=intent, status='returned'))


def observe_native(live, operation, backend, prepared, endpoint_dir, lease, observer_session):
    load_operation(live, operation.root, operation.directory, active=True)
    backend.observe_candidate(prepared, endpoint_dir, lease, observer_session)
    # The enclosing guard must leave before observation() proves its release.


def wait_native_return(live, operation, backend, prepared, endpoint_dir, lease):
    load_operation(live, operation.root, operation.directory, active=True)
    value = observation(live, prepared)
    host = live._return_host_for(prepared)
    intent, intent_pin = host.read_intent(prepared.run_dir,
        binding=live._candidate_observer_binding(prepared), proof=value['proof'])
    index = value['proof']['session_count']
    check, check_pin = read(prepared.run_dir/f'p385-native-auth-{index:02d}.terminal-check.json')
    require(host.remaining_window(intent) > 0, 'native CONTROL original window already expired')
    require(live.native_usb_departure.observe_departure(prepared.run_dir, intent, intent_pin),
            'native departure was not observed within its original window')
    remaining = min(host.remaining_window(intent), (operation.grant['deadline_boottime_ns']-protocol.host_now_ns())/1e9,
                    (check['created_boottime_ns']+30*10**9-protocol.host_now_ns())/1e9)
    require(remaining > 0, 'native return exhausted its original control/grant window')
    endpoint = backend.wait_download(prepared, endpoint_dir, lease, remaining)
    closed = time.monotonic_ns()
    closed_boot = protocol.host_now_ns()
    require(endpoint.arrival_receipt is not None and host.host_boot_sha256() == intent['host_boot_sha256']
            and intent['created_monotonic_ns'] <= closed <= intent['created_monotonic_ns']+30*10**9
            and check['created_boottime_ns'] <= closed_boot <= check['created_boottime_ns']+30*10**9,
            'native normal return arrived outside original Download window')
    window = dict(schema=host.window_schema, binding=live._candidate_observer_binding(prepared),
        control_intent=intent_pin, outcome='exact-download-within-control-window',
        observed_within_software_deadline=True, closed_monotonic_ns=closed,
        host_boot_sha256=host.host_boot_sha256(), physical_prompt_required=False,
        physical_intervention='UNOBSERVED', software_causal_attribution='UNPROVED',
        rollback_topology_record=endpoint.arrival_receipt)
    host.validate_window(window, binding=live._candidate_observer_binding(prepared), intent=intent, intent_receipt=intent_pin)
    publish(prepared.run_dir/host.WINDOW_NAME, window)
    publish(prepared.run_dir/'native-return-boottime.json', dict(schema=SCHEMA,
        terminal_check=check_pin, window=pin(prepared.run_dir/host.WINDOW_NAME), closed_boottime_ns=closed_boot))
    timely_return(live, prepared)
    journal(operation, prepared.native_baseline_context['phase']+'-download-return', window=pin(prepared.run_dir/host.WINDOW_NAME))
    return endpoint


def transfer(live, operation, backend, prepared, endpoint_dir, lease, kind):
    native = kind == TRANSFER_NATIVE
    load_operation(live, operation.root, operation.directory, active=native)
    backend.revalidate_candidate_lane(prepared)
    # Each destination phase obtains a fresh ticket and arrival bound to its
    # own observer identity, including after an earlier phase's timely return.
    timeout = (min(60, (operation.grant['deadline_boottime_ns']-protocol.host_now_ns())/1e9)
               if native else live.ROLLBACK_WAIT_SEC)
    require(timeout > 0, 'baseline transfer has no remaining original time')
    endpoint = backend.wait_download(prepared, endpoint_dir, lease, timeout)
    if native and prepared.native_baseline_context['phase'] == 'bootstrap-first':
        primary = primary_prepared(live, operation)
        identity = live._candidate_registry_identity(primary)
        live._claim_candidate_global(primary, identity)
    prefix = kind+'-attempt-01'
    intent = publish(prepared.run_dir/(prefix+'.start.json'), role_intent(live, operation, prepared, endpoint, kind))
    journal(operation, prepared.native_baseline_context['phase']+'-transfer-intent', intent=intent)
    outcome = backend.transfer(prepared, endpoint, kind, prepared.run_dir, 1, prefix)
    durable = live._validate_transfer_result(prepared, kind, 1)
    require(durable is not None and durable['classification'] == 'odin_transfer_completed'
            and outcome.completed is True, 'baseline transfer did not complete exactly; role remains consumed')
    journal(operation, prepared.native_baseline_context['phase']+'-transfer-result', result=pin(prepared.run_dir/(prefix+'.result.json')))
    return outcome


def android_terminal_value(live, operation):
    prepared = phase_prepared(live, operation, 'android-exit')
    result = live._validate_transfer_result(prepared, TRANSFER_ANDROID, 1)
    require(result is not None and result['classification'] == 'odin_transfer_completed', 'Android terminal lacks exact completed A')
    prefix = TRANSFER_ANDROID+'-attempt-01'
    intent, intent_pin = read(prepared.run_dir/(prefix+'.start.json'))
    delivery, _ = read(prepared.run_dir/(prefix+'.delivery.json'))
    arrival=live._read_native_download_arrival(prepared,intent['arrival'])
    endpoint=live.Endpoint(**arrival['endpoint'],arrival_receipt=intent['arrival'])
    require(same(delivery, dict(schema=SCHEMA, intent=intent_pin))
            and same(intent,bound_role_value(operation,prepared,endpoint,TRANSFER_ANDROID)),
            'Android terminal role/delivery differs')
    health_selector, _ = read(prepared.run_dir/'final-health-complete.json')
    core._exact(health_selector, {'schema','operation','result'}, 'baseline final health selection')
    health_path = verify_pin(operation.root, health_selector['result'])
    require(health_selector['schema'] == SCHEMA and same(health_selector['operation'], operation.receipt)
            and health_path.parent.parent == prepared.run_dir and health_path.name == 'result.json'
            and (health_path.parent.name == 'health' or re.fullmatch('health-attempt-[0-9]{3}', health_path.parent.name)),
            'baseline final health attempt is outside the exact Android phase')
    health = android_health(live, operation, health_path.parent)
    return dict(schema=SCHEMA, state='ANDROID_CLOSED', operation=operation.receipt,
        android_transferred=True, android=operation.request['android'], final_health=health_selector['result'],
        target_evidence=health['target_evidence'], recovery_required=False,
        native_admitted=False, research_stopped=os.path.lexists(operation.directory/STOP))


def validate_terminal(live, operation):
    value, _ = read(operation.directory/'terminal.json')
    if value.get('state') == 'NATIVE_CLOSED': expected = native_terminal_value(live, operation)
    elif value.get('state') == 'ANDROID_CLOSED': expected = android_terminal_value(live, operation)
    elif value.get('state') == 'ABORTED_NO_DEVICE_EFFECT':
        require(operation.value['origin'] == 'android' and not has_device_intent(operation),
                'aborted operation owns native/Download state or a durable device intent')
        expected = dict(schema=SCHEMA, state='ABORTED_NO_DEVICE_EFFECT', operation=operation.receipt, recovery_required=False)
    else: raise BaselineError('unknown baseline terminal state')
    require(same(value, expected), 'baseline terminal cannot be rederived')
    journal(operation)
    return value


def finish(live, operation):
    terminal = validate_terminal(live, operation)
    if terminal['state'] == 'NATIVE_CLOSED' and operation.value['operation'] == 'bootstrap':
        register_admission(live, operation)
    record = dict(schema=SCHEMA, operation=operation.receipt, terminal=pin(operation.directory/'terminal.json'))
    if os.path.lexists(operation.directory/'completed.json'):
        require(same(read(operation.directory/'completed.json')[0], record), 'baseline completion changed')
    else: publish(operation.directory/'completed.json', record)
    registry.retire_f1_owner(operation.root, operation.directory, operation.binding)
    if operation.value['ordinal'] == operation.request['reservations']:
        path = operation.directory.parent/'closed.json'
        if not os.path.lexists(path): publish(path, dict(schema=SCHEMA, reason='reservation-budget-exhausted', operation=operation.receipt))
    return terminal


def repair_native_terminal(live, operation):
    """A reporting cut after fully proved native release is H0-only repair."""
    if (operation.value['operation'] == 'android-exit' or os.path.lexists(operation.directory/STOP)
            or not os.path.lexists(operation.directory/'native-final'/'candidate-observer.json')):
        return None
    try:
        value = native_terminal_value(live, operation)
    except (core.F1V2Error, live.F1LiveError, ValueError, OSError, KeyError, TypeError):
        return None
    # Once the complete raw/close graph proves this terminal, publication
    # failures remain H0. They cannot turn this branch into an A delivery.
    publish(operation.directory/'terminal.json', value)
    return finish(live, operation)


def has_device_intent(operation):
    return any(operation.directory.glob('*/download-request-intent.json')) or any(
        operation.directory.glob('*/p385-native-auth-*.intent.json')) or any(
        operation.directory.glob('*/*-attempt-01.start.json'))


def ensure_lane(live, operation, backend):
    """Finish missing H0 lane preparation; never replace a present lane record."""
    path = operation.directory/live.P324_TYPEC_LANE_NAME
    if not os.path.lexists(path):
        prior = operation.value['prior_native']
        if prior is None and operation.value['operation'] != 'bootstrap':
            admitted, _ = admission(live, operation.root, operation.request['native'], target=operation.request['target'])
            prior = admitted['qualification']
        if prior is not None:
            previous_path = verify_pin(operation.root, prior)
            previous, _ = read(previous_path.parent/live.P324_TYPEC_LANE_NAME)
            live.p324_typec_lane.revalidate_binding(previous, source_topology=operation.request['target']['topology'],
                usb_root=backend.usb_root, typec_root=backend.typec_root)
            publish(path, previous)
        else:
            live._prepare_p324_typec_lane(operation.bundle, operation.directory, operation.request['target'],
                usb_root=backend.usb_root, typec_root=backend.typec_root)
    lane, _ = read(path)
    live.p324_typec_lane.revalidate_binding(lane, source_topology=operation.request['target']['topology'],
        usb_root=backend.usb_root, typec_root=backend.typec_root)


def recover(live, operation, backend, *, attended):
    """Caller holds target lease. No native phase can be resumed here."""
    require(attended is True, 'current attendance required for preapproved exact Android recovery')
    if os.path.lexists(operation.directory/'terminal.json'): return finish(live, operation)
    registry.require_f1_owner(operation.root, operation.directory, operation.binding)
    repaired = repair_native_terminal(live, operation)
    if repaired is not None: return repaired
    stop(operation, 'interrupted-or-failed-native-operation')
    journal(operation)
    if operation.value['origin'] == 'android' and not has_device_intent(operation):
        publish(operation.directory/'terminal.json', dict(schema=SCHEMA,
            state='ABORTED_NO_DEVICE_EFFECT', operation=operation.receipt, recovery_required=False))
        return finish(live, operation)
    ensure_lane(live, operation, backend)
    name = 'android-exit'; prepared = phase_prepared(live, operation, name,
        create=not os.path.lexists(operation.directory/name/'phase.json'))
    prefix = TRANSFER_ANDROID+'-attempt-01'
    result = live._validate_transfer_result(prepared, TRANSFER_ANDROID, 1)
    if os.path.lexists(prepared.run_dir/(prefix+'.start.json')):
        require(result is not None and result['classification'] == 'odin_transfer_completed',
                'Android role consumed with missing/uncertain completion; no replay')
    else:
        print('Native research is stopped. Use physical Download for the already bound exact Android recovery.',
              file=sys.stderr, flush=True)
        endpoint_dir = prepared.run_dir/('recovery-endpoints-'+uuid.uuid4().hex)
        endpoint_dir.mkdir(mode=0o700)
        with backend.endpoint_session(endpoint_dir) as lease:
            transfer(live, operation, backend, prepared, endpoint_dir, lease, TRANSFER_ANDROID)
    if not os.path.lexists(prepared.run_dir/'final-health-complete.json'):
        collect_android(live, operation, backend, prepared, final=True)
    publish(operation.directory/'terminal.json', android_terminal_value(live, operation))
    return finish(live, operation)


def execute(live, root, grant, operation_name, origin, *, prior_native=None, attended, backend=None):
    require(attended is True, 'current operator attendance is required throughout baseline effects')
    root = Path(root).resolve()
    with registry.target_session_lease(root):
        operation = reserve(live, root, grant, operation_name, origin, prior_native)
        backend = backend or live.SamsungOdinBackend(root, operation.bundle, live.d0.default_adb())
        try:
            ensure_lane(live, operation, backend)
            if operation_name == 'bootstrap':
                primary = primary_prepared(live, operation)
                registry.preflight_candidate(root, live._candidate_registry_identity(primary))
            if origin == 'android':
                first = phase_prepared(live, operation, 'android-start', create=True)
                collect_android(live, operation, backend, first)
                request_android_download(live, operation, backend, first)
            elif origin == 'native':
                first = phase_prepared(live, operation, 'native-start', create=True)
                endpoint_dir = first.run_dir/'odin-endpoints'; endpoint_dir.mkdir(mode=0o700)
                with backend.endpoint_session(endpoint_dir) as lease:
                    with backend.candidate_observer_session(first) as observer_session:
                        observe_native(live, operation, backend, first, endpoint_dir, lease, observer_session)
                    observation(live, first)
                    wait_native_return(live, operation, backend, first, endpoint_dir, lease)
            if operation_name == 'bootstrap':
                first = phase_prepared(live, operation, 'bootstrap-first', create=True)
                endpoint_dir = first.run_dir/'odin-endpoints'; endpoint_dir.mkdir(mode=0o700)
                with backend.endpoint_session(endpoint_dir) as lease:
                    with backend.candidate_observer_session(first) as observer_session:
                        transfer(live, operation, backend, first, endpoint_dir, lease, TRANSFER_NATIVE)
                        observe_native(live, operation, backend, first, endpoint_dir, lease, observer_session)
                    observation(live, first)
                    wait_native_return(live, operation, backend, first, endpoint_dir, lease)
            if operation_name == 'android-exit':
                final = phase_prepared(live, operation, 'android-exit', create=True)
                endpoint_dir = final.run_dir/'odin-endpoints'; endpoint_dir.mkdir(mode=0o700)
                with backend.endpoint_session(endpoint_dir) as lease:
                    transfer(live, operation, backend, final, endpoint_dir, lease, TRANSFER_ANDROID)
                    collect_android(live, operation, backend, final, final=True)
                terminal = android_terminal_value(live, operation)
            else:
                final = phase_prepared(live, operation, 'native-final', create=True)
                endpoint_dir = final.run_dir/'odin-endpoints'; endpoint_dir.mkdir(mode=0o700)
                with backend.endpoint_session(endpoint_dir) as lease:
                    with backend.candidate_observer_session(final) as observer_session:
                        transfer(live, operation, backend, final, endpoint_dir, lease, TRANSFER_NATIVE)
                        observe_native(live, operation, backend, final, endpoint_dir, lease, observer_session)
                terminal = native_terminal_value(live, operation)
            publish(operation.directory/'terminal.json', terminal)
            return finish(live, operation)
        except Exception as error:
            if os.path.lexists(operation.directory/'terminal.json'):
                # Publication/admission/release repair is H0; a proved native
                # terminal must never cause an Android transfer to be repeated.
                raise
            repaired = repair_native_terminal(live, operation)
            if repaired is not None: return repaired
            stop(operation, type(error).__name__)
            try:
                return recover(live, operation, backend, attended=attended)
            except Exception as recovery_error:
                record = dict(schema=SCHEMA, state='PARKED', operation=operation.receipt,
                    recovery_required=operation.value['origin'] != 'android' or has_device_intent(operation), native_replay_forbidden=True,
                    failure_type=type(error).__name__, recovery_error_type=type(recovery_error).__name__)
                publish(operation.directory/('parked-'+uuid.uuid4().hex+'.json'), record)
                return record


def main(argv=None):
    import device_action_f1_live_v2 as live
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    sub = parser.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('prepare')
    prepare.add_argument('--out', type=Path, required=True); prepare.add_argument('--manifest', type=Path, required=True)
    prepare.add_argument('--target-file', type=Path, required=True)
    prepare.add_argument('--operations', nargs='+', choices=OPERATIONS, required=True)
    prepare.add_argument('--reservations', type=int, default=1); prepare.add_argument('--seconds', type=int, default=600)
    grant = sub.add_parser('grant'); grant.add_argument('--request', type=Path, required=True)
    grant.add_argument('--approval', required=True); grant.add_argument('--attended', action='store_true')
    run = sub.add_parser('execute'); run.add_argument('--grant', type=Path, required=True)
    run.add_argument('--operation', choices=OPERATIONS, required=True)
    run.add_argument('--origin', choices=('android','native','physical-download'), required=True)
    run.add_argument('--prior-native', type=Path); run.add_argument('--attended', action='store_true')
    recovery = sub.add_parser('recover'); recovery.add_argument('--operation-dir', type=Path, required=True)
    recovery.add_argument('--attended', action='store_true')
    status = sub.add_parser('status'); status.add_argument('--operation-dir', type=Path, required=True)
    args = parser.parse_args(argv); root = args.root.resolve()
    if args.command == 'prepare':
        result = prepare_request(live, root, args.out, manifest=args.manifest, target_file=args.target_file,
            operations=args.operations, reservations=args.reservations, seconds=args.seconds)
    elif args.command == 'grant': result = open_grant(live, root, args.request, args.approval, attended=args.attended)
    elif args.command == 'execute': result = execute(live, root, args.grant, args.operation, args.origin,
        prior_native=args.prior_native, attended=args.attended)
    elif args.command == 'recover':
        with registry.target_session_lease(root):
            operation = load_operation(live, root, args.operation_dir)
            result = recover(live, operation, live.SamsungOdinBackend(root, operation.bundle, live.d0.default_adb()), attended=args.attended)
    else:
        operation = load_operation(live, root, args.operation_dir)
        result = validate_terminal(live, operation) if os.path.lexists(operation.directory/'terminal.json') else dict(state='UNFINISHED')
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
