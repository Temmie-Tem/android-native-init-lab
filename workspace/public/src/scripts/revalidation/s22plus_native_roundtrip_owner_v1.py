"""P383-only first native baseline qualification inside the existing F1 owner.

The ordinary journal owns N installation and A cleanup. A linked immutable
restoration record owns the single exceptional same-N delivery. Recovery never
calls finish(), creates a new native arrival, or transmits N. No registry claim
is released. All calls execute under the parent's existing target-session lease.
"""
from dataclasses import replace
from pathlib import Path
import hashlib
import os
import re
import time

import device_action_f1_v2 as core
import s22plus_native_baseline_health_v1 as health

SCHEMA = 's22plus-native-roundtrip-owner-v1'
POLICY = 'docs/operations/S22PLUS_NATIVE_ROUNDTRIP_FIRST_QUALIFICATION_V1.md'
ARRIVAL_DIR = 'native-restoration'
INTENT = 'native-restore-attempt-01.start.json'
STOP = 'native-roundtrip-stop.json'
CLAIM = 'workspace/private/device-action/s22plus-native-roundtrip-first-v1.json'


def selected(bundle):
    return bundle.manifest.get('observation', {}).get('acceptance', {}).get('run_id') == 'c383f1e0a90b5e6d7c8a9b0c0d2e3f0b'


def android_identity(bundle):
    """Derive A's member from the exact AP; ordinary Bundle omits that field."""
    expected = bundle.receipt['rollback_ap']
    path = Path(expected['path'])
    if not path.is_absolute():
        raise ValueError('verified Android AP path must be absolute')
    with core.pin_boot_only_ap(path, label='roundtrip Android fallback',
            expected_size=expected['size'], expected_sha256=expected['sha256'],
            require_deterministic_metadata=False) as pinned:
        value = pinned.receipt()
        if core.json_sha256(value) != core.json_sha256(expected):
            raise ValueError('verified Android AP receipt changed')
        member = core.read_boot_only_member(pinned, label='roundtrip Android fallback',
                                            require_deterministic_metadata=False)
        value['member'] = dict(name=core.BOOT_MEMBER, size=len(member),
                               sha256=health.digest(member))
    return value


def plan(bundle, android):
    """Validate the sealed A identity without post-consumption artifact reads."""
    if (type(android) is not dict or set(android) != {'path', 'size', 'sha256', 'member'}
            or core.json_sha256({k:v for k,v in android.items() if k != 'member'})
                != core.json_sha256(bundle.receipt['rollback_ap'])):
        raise ValueError('sealed Android AP identity differs')
    member = android['member']
    if (type(member) is not dict or set(member) != {'name', 'size', 'sha256'}
            or member['name'] != core.BOOT_MEMBER
            or type(member['size']) is not int or not 0 < member['size'] <= 128*1024*1024
            or type(member['sha256']) is not str
            or re.fullmatch('[0-9a-f]{64}', member['sha256']) is None):
        raise ValueError('sealed Android member identity differs')
    if (bundle.receipt['candidate_ap']['sha256'] == android['sha256']
            or bundle.receipt['candidate_ap']['member']['sha256'] == android['member']['sha256']):
        raise ValueError('native candidate and Android fallback must differ')
    return dict(schema=SCHEMA, policy=POLICY,
        roles=['native-install', 'native-restore', 'android-cleanup'],
        effect_limit_per_role=1, native_arrivals=2, control_limit_per_arrival=1,
        release_installation_claim=False, native_health_schema=health.SCHEMA,
        native_health_command_sha256=health.digest(health.COMMAND_BODY),
        native=bundle.receipt['candidate_ap'], android=android,
        arrival_budget_seconds=600, total_research_budget_seconds=1800,
        recovery='one-exact-attended-android-fallback')


def prepare_plan(bundle):
    return plan(bundle, android_identity(bundle))


def bound_plan(prepared):
    actual = prepared.prepared['approval_binding'].get('native_roundtrip')
    if type(actual) is not dict:
        raise ValueError('sealed native roundtrip role binding missing')
    expected = plan(prepared.bundle, actual.get('android'))
    if core.json_sha256(actual) != core.json_sha256(expected):
        raise ValueError('sealed native roundtrip role binding differs')
    return expected


def primary(live, prepared):
    if not selected(prepared.bundle) or prepared.native_parent is not None:
        raise live.F1LiveError('roundtrip requires its primary P383 run')
    return bound_plan(prepared)


def child(live, prepared):
    primary(live, prepared)
    return replace(prepared, run_dir=prepared.run_dir/ARRIVAL_DIR,
                   native_parent=prepared.run_dir)


def claim_value(prepared):
    return dict(schema=SCHEMA, run_dir=str(prepared.run_dir),
                approval_binding_sha256=prepared.binding_sha256)


def preflight(live, prepared):
    primary(live, prepared)
    path = prepared.root/CLAIM
    if path.exists() or path.is_symlink():
        raise live.F1LiveError('first-roundtrip exception budget already consumed')


def consume(live, prepared):
    # Called immediately before the first ordinary candidate attempt intent.
    preflight(live, prepared)
    path = prepared.root/CLAIM
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    core._write_exclusive(path, dict(claim_value(prepared),
        host_boot_sha256=live.p383_return_host.host_boot_sha256(),
        created_monotonic_ns=time.monotonic_ns()))


def require_claim(live, prepared, *, require_owner=True):
    primary(live, prepared)
    record = live._read_json(prepared.root/CLAIM, 'native roundtrip claim')
    if (set(record) != set(claim_value(prepared)) | {'host_boot_sha256', 'created_monotonic_ns'}
            or any(record.get(k) != v for k, v in claim_value(prepared).items())
            or type(record.get('created_monotonic_ns')) is not int
            or record['created_monotonic_ns'] <= 0
            or type(record.get('host_boot_sha256')) is not str
            or len(record['host_boot_sha256']) != 64):
        raise live.F1LiveError('native roundtrip exception claim differs')
    identity = live._bound_candidate_registry_identity(prepared)
    active = live.consumed_registry.active_claim(prepared.root, identity['candidate_key'])
    if active is None or any(active.get(k) != v for k, v in identity.items() if k != 'schema'):
        raise live.F1LiveError('original installation claim is not retained exactly')
    if require_owner:
        live.consumed_registry.require_f1_owner(prepared.root, prepared.run_dir,
                                              prepared.binding_sha256)


def require_research_time(live, prepared):
    require_claim(live, prepared)
    record = live._read_json(prepared.root/CLAIM, 'native roundtrip claim')
    if (record['host_boot_sha256'] != live.p383_return_host.host_boot_sha256()
            or not record['created_monotonic_ns'] <= time.monotonic_ns()
                <= record['created_monotonic_ns'] + 1800 * 1_000_000_000
            or os.path.lexists(prepared.run_dir/STOP)):
        raise live.F1LiveError('native research stopped or original finite window expired')


def stop(live, prepared, reason):
    path = prepared.run_dir/STOP
    if not path.exists() and not path.is_symlink():
        core._write_exclusive(path, dict(schema=SCHEMA,
            approval_binding_sha256=prepared.binding_sha256,
            reason=reason, native_replay_forbidden=True,
            host_monotonic_ns=time.monotonic_ns()))


def native_health(live, prepared, previous=None):
    spec = prepared.bundle.manifest['observation']['candidate_observer']
    value = live._p345_validate_receipt(prepared,
        prepared.run_dir/'candidate-observer.json', spec)
    if value.get('accepted') is not True:
        raise live.F1LiveError('native arrival health was not accepted')
    guard = live._reopen_candidate_guard_release(prepared)
    if not live._observer_guard_supports_result(accepted=True,
            status=guard['status'], released=guard['released']):
        raise live.F1LiveError('native arrival observer guard not closed')
    handle = live.raw_capture.load_handle(prepared.run_dir/'candidate-observer.capture.json')
    rx = live.raw_capture.read_stdout(handle, maximum=health.wire.RAW_CAPTURE_MAXIMUM)
    if value['trailing_bytes_seen']:
        rx = rx[:-value['trailing_bytes_seen']]
    key, _ = live._p328_read_auth_key(prepared)
    shell = live._shell_definition(prepared.bundle)
    codec = live._open_header_initial_observer_module(shell.runtime, shell.observer,
                                                     'native-roundtrip-replay')
    return health.replay(shell.observer, codec, rx,
        bytes.fromhex(value['session_tx_hex'][0]), key,
        arrival=2 if prepared.native_parent is not None else 1, previous=previous)


def restore_intent(live, prepared, endpoint, first):
    require_research_time(live, prepared)
    if (prepared.run_dir/STOP).exists() or (prepared.run_dir/STOP).is_symlink():
        raise live.F1LiveError('native research is stopped')
    if live._validate_transfer_result(prepared, 'candidate', 1)['classification'] != 'odin_transfer_completed':
        raise live.F1LiveError('native installation is not complete')
    if first != native_health(live, prepared) or not live._p363_return_success(prepared, live._state(prepared)):
        raise live.F1LiveError('first native health and Download must be proved')
    arrival = child(live, prepared)
    # Re-verify unchanged AP/member and execution closure without absence checks.
    if live._closure(prepared.root, prepared.bundle) != prepared.prepared['execution_closure']:
        raise live.F1LiveError('native restoration execution closure changed')
    for kind in ('candidate', 'rollback'):
        item = prepared.bundle.manifest[kind+'_ap']
        with core.pin_boot_only_ap(core._artifact_path(prepared.root, item, kind),
                label=kind, expected_size=item['size'], expected_sha256=item['sha256'],
                require_deterministic_metadata=kind == 'candidate') as pinned:
            member = core.read_boot_only_member(pinned, label=kind,
                                               require_deterministic_metadata=kind == 'candidate')
            expected = (prepared.bundle.receipt['candidate_ap'] if kind == 'candidate'
                        else prepared.prepared['approval_binding']['native_roundtrip']['android'])['member']
            if expected['size'] != len(member) or expected['sha256'] != health.digest(member):
                raise live.F1LiveError('native roundtrip exact artifact member changed')
    if endpoint.arrival_receipt is None:
        raise live.F1LiveError('restoration requires a current exact Download receipt')
    live._read_native_download_arrival(prepared, endpoint.arrival_receipt)
    value = dict(schema=SCHEMA, kind='native-restore', attempt=1,
        prefix='native-restore-attempt-01', approval_binding_sha256=prepared.binding_sha256,
        parent_run_dir=str(prepared.run_dir), arrival=2,
        artifact=prepared.bundle.receipt['candidate_ap'], first_native_health=first,
        first_download=live._state(prepared)['p363_return_window'],
        endpoint_identity_sha256=endpoint.identity_sha256,
        restoration_download=endpoint.arrival_receipt,
        created_monotonic_ns=time.monotonic_ns())
    core._write_exclusive(arrival.run_dir/INTENT, value)
    return value


def read_restore_intent(live, parent):
    arrival = child(live, parent)
    value = live._read_json(arrival.run_dir/INTENT, 'native restoration intent')
    expected = dict(schema=SCHEMA, kind='native-restore', attempt=1,
        prefix='native-restore-attempt-01', approval_binding_sha256=parent.binding_sha256,
        parent_run_dir=str(parent.run_dir), arrival=2,
        artifact=parent.bundle.receipt['candidate_ap'],
        first_native_health=native_health(live, parent),
        first_download=live._state(parent)['p363_return_window'])
    if (set(value) != set(expected) | {'endpoint_identity_sha256', 'created_monotonic_ns', 'restoration_download'}
            or any(core.json_sha256(value.get(k)) != core.json_sha256(v) for k, v in expected.items())
            or type(value['created_monotonic_ns']) is not int):
        raise live.F1LiveError('restoration intent no longer binds its first arrival')
    endpoint = live._read_native_download_arrival(parent, value['restoration_download'])
    claim = live._read_json(parent.root/CLAIM, 'native roundtrip claim')
    if (value['endpoint_identity_sha256'] != endpoint['endpoint']['identity_sha256']
            or not claim['created_monotonic_ns'] <= expected['first_download']['record']['closed_monotonic_ns']
                <= endpoint['observed_monotonic_ns'] <= value['created_monotonic_ns']
                <= claim['created_monotonic_ns'] + 1800 * 1_000_000_000
            or endpoint['host_boot_sha256'] != claim['host_boot_sha256']):
        raise live.F1LiveError('restoration exact Download or original time bound differs')
    return value


def validate_restore_arm(live, arrival, endpoint, attempt, prefix):
    if arrival.native_parent is None or arrival.run_dir != arrival.native_parent/ARRIVAL_DIR:
        raise live.F1LiveError('restoration cannot use ordinary candidate dispatch')
    parent = replace(arrival, run_dir=arrival.native_parent, native_parent=None)
    require_research_time(live, parent)
    value = read_restore_intent(live, parent)
    if (attempt != 1 or prefix != 'native-restore-attempt-01'
            or value.get('approval_binding_sha256') != parent.binding_sha256
            or value.get('parent_run_dir') != str(parent.run_dir)
            or value.get('endpoint_identity_sha256') != endpoint.identity_sha256
            or value.get('first_native_health') != native_health(live, parent)
            or value.get('artifact') != parent.bundle.receipt['candidate_ap']
            or (parent.run_dir/STOP).exists()
            or (arrival.run_dir/(prefix+'.result.json')).exists()):
        raise live.F1LiveError('native restoration durable arm differs or is consumed')
    # Invocation marker survives a cut before or during backend delivery.
    core._write_exclusive(arrival.run_dir/'native-restore-delivery.json',
        dict(schema=SCHEMA, intent=live._receipt(arrival.run_dir/INTENT, 'restoration intent')))


def finish(live, prepared, backend, journal, endpoint_dir, lease):
    """Normal execution only: arrival 1 -> N restoration -> arrival 2 -> A."""
    require_claim(live, prepared)
    first = native_health(live, prepared)
    endpoint = live._p363_wait_for_rollback(prepared, backend, endpoint_dir, lease)
    if not live._p363_return_success(prepared, live._state(prepared)):
        stop(live, prepared, 'first-native-download-unproved')
        return live._finish_rollback(prepared, backend, journal, endpoint_dir, lease,
                                      initial_endpoint=endpoint)
    arrival = child(live, prepared)
    arrival.run_dir.mkdir(mode=0o700, exist_ok=False)
    core._fsync_dir(prepared.run_dir)
    with backend.candidate_observer_session(arrival) as observer_session:
        backend.revalidate_candidate_lane(arrival)
        endpoint = backend.wait_download(prepared, endpoint_dir, lease, live.ENDPOINT_REVALIDATE_SEC)
        restore_intent(live, prepared, endpoint, first)
        outcome = backend.transfer(arrival, endpoint, 'native-restore', arrival.run_dir,
                                   1, 'native-restore-attempt-01')
        if not outcome.completed:
            stop(live, prepared, 'native-restoration-failed-or-uncertain')
            raise live.F1LiveError('native restoration stopped; recovery only')
        # The child's endpoint files and observation are distinct from arrival 1.
        child_endpoints = arrival.run_dir/'odin-endpoints'
        child_endpoints.mkdir(mode=0o700, exist_ok=False)
        with backend.endpoint_session(child_endpoints) as child_lease:
            observation = backend.observe_candidate(arrival, child_endpoints,
                                                    child_lease, observer_session)
    current = live._state(arrival)
    current.update(observation)
    live._save_state(arrival, current)
    second = native_health(live, arrival, first)
    with backend.endpoint_session(child_endpoints) as child_lease:
        endpoint = live._p363_wait_for_rollback(arrival, backend, child_endpoints, child_lease)
    if not live._p363_return_success(arrival, live._state(arrival)):
        stop(live, prepared, 'second-native-download-unproved')
    else:
        core._write_exclusive(prepared.run_dir/'native-roundtrip-proof.json',
            dict(schema=SCHEMA, first=first, second=second,
                 restoration=live._receipt(arrival.run_dir/'native-restore-attempt-01.result.json', 'restoration result')))
    # The arrival-2 ticket belongs to its own endpoint lease. Re-observe the
    # exact current Download under the parent's still-held lease before A.
    endpoint = backend.wait_download(prepared, endpoint_dir, lease, live.ROLLBACK_WAIT_SEC)
    return live._finish_rollback(prepared, backend, journal, endpoint_dir, lease,
                                  initial_endpoint=endpoint)


def recovery_endpoint(live, prepared, backend, endpoint_dir, lease):
    primary(live, prepared)
    try:
        completed_native = projection(live, prepared)['proved']
    except (ValueError, OSError, core.F1V2Error, live.F1LiveError):
        completed_native = False
    if not completed_native:
        stop(live, prepared, 'interrupted-roundtrip-recovery-only')
    # Never reuse a cached arrival-1 endpoint after a restoration intent/cut.
    print('P383 research stopped. Enter physical Download for the one preapproved Android fallback.',
          file=live.sys.stderr, flush=True)
    return backend.wait_download(prepared, endpoint_dir, lease, live.ROLLBACK_WAIT_SEC)


def projection(live, prepared):
    primary(live, prepared)
    arrival = child(live, prepared)
    role_paths = [prepared.run_dir/'candidate-attempt-01.start.json',
                  arrival.run_dir/INTENT, prepared.run_dir/'rollback-attempt-01.start.json']
    value = dict(schema=SCHEMA, proved=False, research_stopped=os.path.lexists(prepared.run_dir/STOP),
        role_timeline=[dict(role=role,
            intent=live._receipt(path, 'roundtrip role intent') if path.exists() else None,
            result=live._receipt(path.with_name(path.name.replace('.start.', '.result.')), 'roundtrip role result')
                if path.with_name(path.name.replace('.start.', '.result.')).exists() else None)
            for role, path in zip(('native-install', 'native-restore', 'android-cleanup'), role_paths)],
        first_native_health=None, second_native_health=None)
    proof_path = prepared.run_dir/'native-roundtrip-proof.json'
    if value['research_stopped'] or not proof_path.exists():
        return value
    require_claim(live, prepared, require_owner=False)
    read_restore_intent(live, prepared)
    delivery = live._read_json(arrival.run_dir/'native-restore-delivery.json', 'restoration delivery')
    if delivery != dict(schema=SCHEMA, intent=live._receipt(arrival.run_dir/INTENT, 'restoration intent')):
        raise live.F1LiveError('restoration delivery no longer binds its intent')
    for context, kind in ((prepared, 'candidate'), (arrival, 'native-restore')):
        result = live._validate_transfer_result(context, kind, 1)
        if result is None or result['classification'] != 'odin_transfer_completed':
            raise live.F1LiveError('roundtrip transfer proof differs')
    first = native_health(live, prepared)
    second = native_health(live, arrival, first)
    proof = live._read_json(proof_path, 'native roundtrip proof')
    if (proof != dict(schema=SCHEMA, first=first, second=second,
            restoration=live._receipt(arrival.run_dir/'native-restore-attempt-01.result.json', 'restoration result'))
            or not all(live._p363_return_success(p, live._state(p)) for p in (prepared, arrival))):
        raise live.F1LiveError('native roundtrip retained proof differs')
    value.update(proved=True, first_native_health=first, second_native_health=second)
    return value
