"""Task-scoped S22+ research authority over the existing native-baseline owner.

Only the parent requires returned operator approval. A child binds its actual
candidate and current reviewed machinery at selection; ordinary/historical
grants retain their own readers. No transport implementation lives here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace

import s22plus_native_baseline_owner_v1 as owner
import s22plus_native_baseline_v2_candidates as candidates

ROOT = owner.ROOT
MODE = owner.RESEARCH_MODE
SCHEMA = 's22plus-proportional-research-v1'
POLICY = 'docs/operations/S22PLUS_PROPORTIONAL_RESEARCH_V1.md'
BASE = Path('workspace/private/runs/s22plus-proportional-research-v1')
REPEATS = Path('workspace/private/device-action/s22plus-proportional-research-v1/repeat-admissions')
REVIEW = Path('workspace/public/src/device-action/bindings/s22plus_proportional_research_v1_review.json')
APPROVAL_PREFIX = 'S22PLUS_RESEARCH_SCOPE_V1_APPROVE:'
OPERATIONS = ('observe', 'experiment', 'restore', 'android-exit')
# Integer/reader bounds, not a per-experiment six-hundred-second policy.
MAX_SECONDS = 2**31-1
MAX_RESERVATIONS = owner.registry.MAX_RECORDS
MUTABLE_INPUTS = frozenset({
    'workspace/public/src/native-init/s22plus_resident_v1/collect.inc.c.in',
    'workspace/public/src/native-init/s22plus_resident_v1/render.inc.c.in',
})
CONSTRAINTS = dict(target='SM-S906N/g0q/S906NKSS7FYG8', operations=list(OPERATIONS),
    profiles=sorted(candidates.RESEARCH_PROFILES), mutable_inputs=sorted(MUTABLE_INPUTS),
    boot_only=True, prospective_repeats=True, legacy_repeat_adoption=False,
    native_observation_seconds=60, deferred_physical_recovery=True,
    functional_change_review='independent-byte-bound-v1')
_SOURCE_CACHE = {}


def _file_state(paths):
    values = []
    for path in paths:
        info = path.stat()
        values.append((str(path), *(getattr(info, field) for field in
            ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))))
    return tuple(values)


def _list(value, allowed, label, *, empty=False):
    owner.require(type(value) is list and (empty or value) and len(value) == len(set(value))
                  and all(type(item) is str and item in allowed for item in value), label+' differs')


def _clock(value):
    owner.require(type(value) is int and 0 < value < 2**63, 'scope clock differs')
    return value


def authority(root):
    """Keep common rules; remove only other-target registry/history records.

    The full common details, risk policy, selected target and new policy remain
    byte-bound. This does not claim a normalized digest is a raw file digest.
    """
    root = Path(root)
    text = (root/'AGENTS.md').read_text()
    paragraphs = []
    for paragraph in text.split('\n\n'):
        if paragraph.startswith('The operator-approved [one-run S20+ '):
            owner.require(paragraph.endswith('grants no further device effect.'), 'other-target root record changed shape')
            continue
        lines = [line for line in paragraph.splitlines()
                 if not line.startswith(('| Samsung Galaxy A90 ', '| Samsung Galaxy S20+ '))]
        paragraphs.append('\n'.join(lines))
    details = owner.pin(root/'docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md')
    owner.require(details['sha256'] in text, 'root common-contract digest is stale')
    for name in ('docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md',
                 'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md'):
        owner.require(Path(POLICY).name in (root/name).read_text(), 'proportional research has not been adopted by the binding contracts')
    return dict(schema='s22plus-selected-authority-v1', root_selected_sha256=hashlib.sha256(
        '\n\n'.join(paragraphs).encode()).hexdigest(), inputs={name: dict(owner.pin(root/name), path=name)
        for name in ('docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md',
            'docs/operations/DEVICE_ACTION_RISK_TIERS.md',
            'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md', POLICY, owner.PROFILE)})


def review_sources(root=ROOT):
    # Reuse byte-verified inputs while ordinary filesystem identity is unchanged.
    # The declared threat model excludes a malicious host owner replacing files
    # between individual syscalls; there is no per-frame build/hash ceremony.
    key = str(Path(root).resolve()); cached = _SOURCE_CACHE.get(key)
    if cached is not None and _file_state(cached[0]) == cached[1]: return cached[2]
    sources = {key: value for key, value in candidates.review_sources(research_profiles=True).items()
               if value['path'] not in MUTABLE_INPUTS and value['path'] != 'AGENTS.md'}
    # The fixed observer and scope implementation are reached through lazy
    # imports from the shared owner, so name them explicitly in its review.
    for name in ('s22plus_native_research_scope_v1.py', 's22plus_native_reobservation_v1.py'):
        path = Path(__file__).with_name(name)
        relative = str(path.relative_to(ROOT))
        sources['source_'+hashlib.sha256(relative.encode()).hexdigest()[:16]] = dict(owner.pin(path), path=relative)
    sources['selected_authority'] = authority(root)
    sources = dict(sorted(sources.items()))
    paths = {ROOT/value['path'] for value in sources.values() if 'path' in value}
    paths.update(Path(root)/value['path'] for value in sources['selected_authority']['inputs'].values())
    paths.add(Path(root)/'AGENTS.md')
    paths = tuple(sorted(paths)); _SOURCE_CACHE[key] = (paths, _file_state(paths), sources)
    return sources


def reviewed(root=ROOT):
    value, receipt = owner.core.load_json(Path(root)/REVIEW, 'proportional research capability review')
    owner.require(value.get('verdict') == 'PASS_GO' and value.get('findings') == []
                  and value.get('activation') == MODE and owner.same(value.get('constraints'), CONSTRAINTS)
                  and owner.same(value.get('current_sources'), review_sources(root)),
                  'proportional research has no current source-bound independent review')
    _reference(value.get('functional_reference_inputs'))
    return receipt


def _reference(value):
    owner.require(type(value) is dict and set(value) == MUTABLE_INPUTS, 'reviewed functional references differ')
    for receipt in value.values():
        owner.core._exact(receipt, {'size', 'sha256'}, 'functional reference input')
        owner.require(type(receipt['size']) is int and receipt['size'] > 0
                      and type(receipt['sha256']) is str and re.fullmatch('[0-9a-f]{64}', receipt['sha256']),
                      'functional reference receipt differs')
    return value


def functional_reference(root=ROOT):
    value, _ = owner.core.load_json(Path(root)/REVIEW, 'reviewed functional reference')
    return _reference(value.get('functional_reference_inputs'))


def execution_closure(live, root, bundle, native):
    current = dict(live._closure(root, bundle))
    def relative(path):
        path = Path(path)
        if not path.is_absolute(): return str(path)
        return str(path.relative_to(ROOT if path.is_relative_to(ROOT) else root))
    current['sources'] = {key: value for key, value in current['sources'].items()
        if relative(value['path']) not in MUTABLE_INPUTS | {'AGENTS.md'}}
    for name in ('s22plus_native_research_scope_v1.py', 's22plus_native_reobservation_v1.py'):
        current['sources'][name.removesuffix('.py')] = owner.pin(Path(__file__).with_name(name))
    current['sha256'] = owner.core.json_sha256(current['sources'])
    current['selected_authority'] = authority(root)
    current['native_binding_sha256'] = owner.core.json_sha256(native)
    return current


def recovery_closure(live, root):
    # Native build inputs and mutable candidate data are not A recovery inputs.
    paths = [Path(__file__).with_name(name+'.py') for name in (
        's22plus_native_research_scope_v1', 's22plus_native_baseline_owner_v1',
        's22plus_native_baseline_protocol_v1', 's22plus_native_console_owner_v1',
        's22plus_native_roundtrip_owner_v1', 's22plus_boot_verify',
        's22plus_fyg8_p324_typec_lane_binding', 's22plus_native_usb_departure_v1',
        's22plus_native_baseline_v2_candidates', 's22plus_native_candidate_definition_v1')]
    common = dict(live._closure(root))
    common['sources'] = {key: receipt for key, receipt in common['sources'].items()
                         if Path(receipt['path']).name != 'AGENTS.md'}
    common['sha256'] = owner.core.json_sha256(common['sources'])
    return dict(schema=SCHEMA, common=common, selected_authority=authority(root),
                owner_sources=[owner.pin(path) for path in paths])


def _native_inputs(profiles):
    values = {}
    seen = set()
    for prefix, declared in candidates.DECLARATIONS.items():
        try: profile = candidates.research_profile(declared)
        except ValueError: continue
        if profile not in profiles or profile in seen: continue
        seen.add(profile)
        for name, receipt in candidates.static(prefix).builder.source_receipts().items():
            owner.require(name not in values or values[name] == receipt, 'native source profile collision')
            values[name] = receipt
    owner.require(seen == set(profiles), 'requested runtime profile has no reviewed factory')
    return values


def previous_native(live, root, path):
    value, _ = owner.read(path)
    if value.get('schema') == 's22plus-native-reobservation-v1':
        import s22plus_native_reobservation_v1 as observation
        return observation.native_tail(live, root, path)
    return owner.native_terminal(live, root, path.parent)


def previous_lane_directory(live, root, path):
    value, _ = owner.read(path)
    if value.get('schema') == 's22plus-native-reobservation-v1':
        snapshot = previous_native(live, root, path)
        return owner.verify_pin(root, snapshot['operation']).parent
    return path.parent


def prepare(live, root, output, *, baseline_terminal, operations, profiles, mutable_paths,
            seconds, reservations, recovery, purpose):
    """H0 proposal: no candidate list, grant, target lease or device access."""
    root = Path(root).resolve(); output = owner.direct(root, output)
    owner.require(output.is_relative_to(root/BASE) and not os.path.lexists(output), 'fresh scope directory required')
    _list(operations, OPERATIONS, 'scope operations')
    _list(profiles, candidates.RESEARCH_PROFILES, 'scope profiles')
    _list(mutable_paths, MUTABLE_INPUTS, 'functional source scope', empty=True)
    owner.require(type(seconds) is int and 1 <= seconds <= MAX_SECONDS
                  and type(reservations) is int and 1 <= reservations <= MAX_RESERVATIONS
                  and recovery in ('attended', 'deferred') and type(purpose) is str
                  and 0 < len(purpose.strip()) <= 2000, 'scope budget, recovery or purpose differs')
    path = owner.direct(root, baseline_terminal)
    native = previous_native(live, root, path)
    admission, _ = owner.admission(live, root, native['native'], target=native['target'])
    original = owner.load_operation(live, root, owner.verify_pin(root, admission['qualification']).parent)
    owner.require(owner.v2(original.request), 'scope requires an admitted resident N')
    review = reviewed(root)
    inputs = _native_inputs(profiles)
    references = functional_reference(root)
    # A new scope cannot bless an edited fragment merely by sampling the current
    # checkout. Its functional reference comes from the independent capability
    # review; changed executable bytes require the assessment below.
    inputs.update({name: receipt for name, receipt in references.items() if name in inputs})
    value = dict(schema=SCHEMA, kind='scope-request', purpose=purpose.strip(), target=native['target'],
        baseline=dict(terminal=owner.pin(path), manifest=original.request['manifest'],
            bundle=owner.bundle_snapshot(original.bundle), native=native['native']),
        android=native['android_available'], operations=operations, profiles=profiles,
        mutable_paths=mutable_paths, native_inputs=inputs,
        seconds=seconds, reservations=reservations, recovery=recovery,
        selected_authority=authority(root), review_at_prepare=review, live_authorized=False)
    output.mkdir(parents=True, mode=0o700); owner.core._fsync_dir(output.parent)
    receipt = owner.publish(output/'request.json', value)
    return dict(request=receipt, approval=APPROVAL_PREFIX+receipt['sha256'], live_authorized=False)


def load_request(live, root, path, *, current=False):
    path = owner.direct(root, path)
    value, receipt = owner.read(path)
    owner.core._exact(value, {'schema', 'kind', 'purpose', 'target', 'baseline', 'android', 'operations',
        'profiles', 'mutable_paths', 'native_inputs', 'seconds', 'reservations', 'recovery',
        'selected_authority', 'review_at_prepare', 'live_authorized'}, 'research scope request')
    owner.require(path.name == 'request.json' and path.is_relative_to(Path(root)/BASE)
                  and value['schema'] == SCHEMA and value['kind'] == 'scope-request'
                  and value['live_authorized'] is False and type(value['seconds']) is int
                  and 1 <= value['seconds'] <= MAX_SECONDS and type(value['reservations']) is int
                  and 1 <= value['reservations'] <= MAX_RESERVATIONS and value['recovery'] in ('attended', 'deferred'),
                  'scope request identity or bounds differ')
    _list(value['operations'], OPERATIONS, 'scope operations')
    _list(value['profiles'], candidates.RESEARCH_PROFILES, 'scope profiles')
    _list(value['mutable_paths'], MUTABLE_INPUTS, 'functional source scope', empty=True)
    owner.core._exact(value['baseline'], {'terminal', 'manifest', 'bundle', 'native'}, 'scope baseline')
    bundle = owner.snapshot_bundle(value['baseline']['bundle'])
    owner.require(value['baseline']['native']['candidate'] == bundle.receipt['candidate_ap']
                  and {k: v for k, v in value['android'].items() if k != 'member'} == bundle.receipt['rollback_ap'],
                  'scope N/A byte mapping differs')
    owner.core._exact(value['target'], {'serial', 'topology'}, 'scope target')
    owner.require(type(value['target']['serial']) is str and live.d0.SERIAL_RE.fullmatch(value['target']['serial'])
                  and value['target']['topology'] == live.p324_typec_lane.SOURCE_TOPOLOGY,
                  'scope physical target differs')
    if current:
        reviewed(root)
        owner.require(owner.same(value['selected_authority'], authority(root)), 'accepted scope policy changed')
        owner.admission(live, root, value['baseline']['native'], target=value['target'])
        _artifacts(live, root, bundle, value['baseline']['native'], value['android'])
    return value, receipt


def open_grant(live, root, request, approval, *, attended):
    with owner.registry.target_session_lease(root):
        owner.registry.require_no_f1_owner(root)
        value, receipt = load_request(live, root, request, current=True)
        owner.require(type(attended) is bool and (attended or value['recovery'] == 'deferred'),
                      'attended scope needs actual attendance')
        owner.require(approval == APPROVAL_PREFIX+receipt['sha256'], 'exact returned scope approval required')
        start = _clock(owner.protocol.host_now_ns()); end = _clock(start+value['seconds']*10**9)
        return owner.publish(Path(request).parent/'grant.json', dict(schema=SCHEMA, kind='scope-grant',
            request=receipt, operator_approval=approval, attended=attended,
            host_boot_sha256=owner.host_epoch(), started_boottime_ns=start, deadline_boottime_ns=end))


def load_grant(live, root, path, *, active=False):
    path = owner.direct(root, path); grant, receipt = owner.read(path)
    owner.core._exact(grant, {'schema', 'kind', 'request', 'operator_approval', 'attended',
        'host_boot_sha256', 'started_boottime_ns', 'deadline_boottime_ns'}, 'research scope grant')
    request, rp = load_request(live, root, path.parent/'request.json')
    owner.require(path.name == 'grant.json' and grant['schema'] == SCHEMA and grant['kind'] == 'scope-grant'
                  and grant['request'] == rp and grant['operator_approval'] == APPROVAL_PREFIX+rp['sha256']
                  and type(grant['attended']) is bool and (grant['attended'] or request['recovery'] == 'deferred')
                  and type(grant['host_boot_sha256']) is str and re.fullmatch('[0-9a-f]{64}', grant['host_boot_sha256'])
                  and _clock(grant['deadline_boottime_ns'])-_clock(grant['started_boottime_ns']) == request['seconds']*10**9,
                  'research scope grant differs')
    if active:
        reviewed(root)
        owner.require(owner.same(request['selected_authority'], authority(root)), 'accepted scope policy changed')
        owner.require(not os.path.lexists(path.parent/'closed.json') and grant['host_boot_sha256'] == owner.host_epoch()
                      and grant['started_boottime_ns'] <= owner.protocol.host_now_ns() < grant['deadline_boottime_ns'],
                      'research scope closed, expired or changed host epoch')
        _current_budget(live, root, path.parent, request)
    return grant, receipt, request


def _current_budget(live, root, directory, request):
    children = directory/'children'
    entries = sorted(children.iterdir()) if children.exists() else []
    owner.require(len(entries) <= MAX_RESERVATIONS
                  and [entry.name for entry in entries] == [f'{i:06d}' for i in range(1, len(entries)+1)]
                  and all(entry.is_dir() and not entry.is_symlink() for entry in entries), 'scope child sequence differs')
    cancelled = 0
    for child in entries:
        if (child/'cancelled.json').exists():
            validate_cancelled(live, root, child); cancelled += 1
    owner.require(len(entries)-cancelled <= request['reservations'], 'scope operation budget exceeded')


def validate_child_shape(value):
    owner.require(owner.v2(value) and value.get('reservations') == 1
                  and type(value.get('reservations')) is int and type(value.get('operations')) is list
                  and len(value['operations']) == 1 and value['operations'][0] in OPERATIONS[1:]
                  and type(value.get('research_scope')) is dict, 'research child operation differs')
    owner.core._exact(value['research_scope'], {'grant', 'index', 'repeat_admission', 'source_assessment'}, 'child scope binding')
    owner.require(type(value['research_scope']['index']) is int
                  and 1 <= value['research_scope']['index'] <= MAX_RESERVATIONS, 'child scope ordinal differs')


def configure_child(root, value):
    # Used only while constructing a child. Full validation joins its later
    # reservation to this exact request before any grant or effect can pass.
    import device_action_f1_live_v2 as live
    binding = value['research_scope']
    path = owner.verify_pin(root, binding['grant'])
    _, _, request = load_grant(live, root, path)
    value['physical_attendance_required'] = request['recovery'] == 'attended'
    value['recovery'] = ('one-exact-android' if value['physical_attendance_required']
                         else 'deferred-attended-one-exact-android')


def _artifacts(live, root, bundle, native, android):
    prepared = live.PreparedRun(Path(root), Path(root)/BASE, bundle,
        dict(approval_binding_sha256='0'*64), dict(schema=live.PRIVATE_TARGET_SCHEMA, serial='H0_UNBOUND',
                                                  topology=live.p324_typec_lane.SOURCE_TOPOLOGY))
    live._candidate_registry_identity(prepared)
    owner.require(native['candidate'] == bundle.receipt['candidate_ap']
                  and owner.same(owner.roundtrip.android_identity(bundle), android), 'bound N/E/A artifacts changed')


def source_assessment_binding(native, profile):
    sources = native['native_sources']
    return dict(constraints_sha256=owner.core.json_sha256(CONSTRAINTS), profile=profile,
        native_context_sha256=owner.core.json_sha256({name: value for name, value in sources.items() if name not in MUTABLE_INPUTS}),
        functional_inputs={name: value for name, value in sources.items() if name in MUTABLE_INPUTS})


def _scope_sources(root, request, native, profile, assessment=None):
    actual = native['native_sources']; expected = request['native_inputs']
    owner.require(type(actual) is dict and type(expected) is dict and actual
                  and set(actual) <= set(expected), 'candidate introduced native inputs outside the accepted profiles')
    changed = {name for name, receipt in actual.items() if receipt != expected[name]}
    owner.require(changed <= set(request['mutable_paths']), 'candidate changed source outside the accepted functional scope')
    if not changed: return
    owner.require(assessment is not None, 'changed executable fragments require an independent source-effect assessment')
    value, _ = owner.read(owner.verify_pin(root, assessment))
    owner.core._exact(value, {'schema', 'verdict', 'findings', 'independent_review', 'reviewer',
        'constraints_sha256', 'profile', 'native_context_sha256', 'functional_inputs'}, 'functional source assessment')
    binding = source_assessment_binding(native, profile)
    owner.require(value['schema'] == 's22plus-functional-source-assessment-v1' and value['verdict'] == 'PASS_GO'
                  and value['findings'] == [] and value['independent_review'] is True
                  and type(value['reviewer']) is str and 0 < len(value['reviewer']) <= 200
                  and all(value[name] == expected for name, expected in binding.items()),
                  'functional source assessment does not cover these exact executable bytes/context')


def _profile(bundle):
    return candidates.research_profile(candidates.declared_for(bundle))


def select(live, root, grant_path, *, operation, manifest=None, repeat=None, source_assessment=None):
    """Bind a spontaneous candidate to the original task; no human child token."""
    root = Path(root).resolve(); grant_path = owner.direct(root, grant_path)
    with owner.registry.target_session_lease(root):
        grant, gp, request = load_grant(live, root, grant_path, active=True)
        owner.require(operation in request['operations'] and operation != 'observe', 'operation outside research scope')
        owner.require((manifest is not None or repeat is not None) is (operation == 'experiment')
                      and not (manifest is not None and repeat is not None)
                      and (source_assessment is None or operation == 'experiment'), 'experiment selection differs')
        experiment = None; repeat_pin = None
        assessment_pin = owner.pin(owner.direct(root, source_assessment)) if source_assessment is not None else None
        if repeat is not None:
            repeat_path = owner.direct(root, repeat)
            admitted, repeat_pin = repeat_admission(live, root, repeat_path)
            old = owner.load_operation(live, root, owner.verify_pin(root, admitted['operation']).parent)
            experiment = dict(old.request['experiment'])
            if assessment_pin is None: assessment_pin = old.request['research_scope']['source_assessment']
        elif manifest is not None:
            manifest_path = owner.direct(root, manifest, private=False)
            bundle = owner.core.verify_bundle(root, manifest_path, runtime_bound=True)
            native = owner.native_identity(bundle)
            experiment = dict(manifest=owner.pin(manifest_path), bundle=owner.bundle_snapshot(bundle), native=native,
                              closure=execution_closure(live, root, bundle, native))
        if experiment is not None:
            bundle = owner.snapshot_bundle(experiment['bundle'])
            owner.require(_profile(bundle) in request['profiles'], 'candidate runtime profile is outside scope')
            _scope_sources(root, request, experiment['native'], _profile(bundle), assessment_pin)
            _artifacts(live, root, bundle, experiment['native'], request['android'])
            experiment['closure'] = execution_closure(live, root, bundle, experiment['native'])
        directory = grant_path.parent/'children'
        directory.mkdir(mode=0o700, exist_ok=True)
        entries = sorted(directory.iterdir())
        owner.require(len(entries) < MAX_RESERVATIONS
                      and [p.name for p in entries] == [f'{i:06d}' for i in range(1, len(entries)+1)]
                      and all(p.is_dir() and not p.is_symlink() for p in entries), 'scope reservation budget or sequence differs')
        cancelled = 0
        for path in entries:
            if (path/'cancelled.json').exists():
                validate_cancelled(live, root, path); cancelled += 1
            else: owner.require((path/'grant.json').is_file(), 'unfinished child selection needs H0 completion or cancellation')
        owner.require(len(entries)-cancelled < request['reservations'], 'scope operation budget exhausted')
        index = len(entries)+1
        base = request['baseline']; bundle = owner.snapshot_bundle(base['bundle'])
        value = owner.request_value(live, root, bundle, target=request['target'],
            manifest_receipt=base['manifest'], review_receipt=reviewed(root), operations=[operation],
            reservations=1, seconds=request['seconds'], policy=owner.V2_POLICY, experiment=experiment,
            execution_mode=MODE, research_scope=dict(grant=gp, index=index, repeat_admission=repeat_pin, source_assessment=assessment_pin),
            native_binding=base['native'], closure=execution_closure(live, root, bundle, base['native']))
        owner.validate_native_roles(value)
        if operation == 'experiment':
            candidate = live.PreparedRun(root, directory, owner.snapshot_bundle(experiment['bundle']),
                dict(approval_binding_sha256=gp['sha256']), dict(schema=live.PRIVATE_TARGET_SCHEMA, **request['target']))
            candidate_preflight(live, root, value, candidate)
        child = directory/f'{index:06d}'; child.mkdir(mode=0o700); owner.core._fsync_dir(directory)
        rp = owner.publish(child/'request.json', value)
        owner.publish(child/'selection.json', dict(schema=SCHEMA, scope=gp, index=index, request=rp))
        delegated = _delegated(grant, rp)
        owner.publish(child/'grant.json', delegated)
        return dict(request=rp, grant=owner.pin(child/'grant.json'), operation=operation,
                    scope=gp, additional_operator_approval_required=False)


def validate_child(live, root, path, value, receipt, *, current=False):
    binding = value['research_scope']; parent = owner.verify_pin(root, binding['grant'])
    _, gp, request = load_grant(live, root, parent, active=current)
    owner.require(path.parent == parent.parent/'children'/f"{binding['index']:06d}"
                  and value['operations'][0] in request['operations']
                  and value['seconds'] == request['seconds'] and value['physical_attendance_required'] is (request['recovery'] == 'attended')
                  and value['target'] == request['target'] and value['native'] == request['baseline']['native']
                  and value['bundle'] == request['baseline']['bundle'] and value['manifest'] == request['baseline']['manifest']
                  and value['android'] == request['android'], 'child exceeds or differs from its original scope')
    selection, _ = owner.read(path.parent/'selection.json')
    owner.require(selection == dict(schema=SCHEMA, scope=gp, index=binding['index'], request=receipt), 'child reservation differs')
    experiment = value['experiment']
    if experiment is not None:
        exp = owner.snapshot_bundle(experiment['bundle'])
        owner.require(_profile(exp) in request['profiles'], 'child experiment runtime profile differs')
        _scope_sources(root, request, experiment['native'], _profile(exp), binding['source_assessment'])
    owner.require((binding['repeat_admission'] is None) or experiment is not None, 'nonexperiment repeat binding')
    if current:
        owner.require(owner.same(reviewed(root), value['review'])
                      and owner.same(recovery_closure(live, root), value['recovery_closure']), 'child machinery or recovery changed')
        for bundle, native, closure in [(owner.snapshot_bundle(value['bundle']), value['native'], value['closure'])] + (
                [(exp, experiment['native'], experiment['closure'])] if experiment is not None else []):
            _artifacts(live, root, bundle, native, request['android'])
            owner.require(owner.same(execution_closure(live, root, bundle, native), closure), 'child execution sources changed')
        if experiment is not None and binding['repeat_admission'] is None:
            owner.require(owner.same(owner.native_identity(exp), experiment['native']), 'fresh candidate native inputs changed')
        if binding['repeat_admission'] is not None:
            repeat_admission(live, root, owner.verify_pin(root, binding['repeat_admission']), expected=experiment)


def validate_child_grant(live, root, path, grant, request, receipt, *, active=False):
    parent = owner.verify_pin(root, request['research_scope']['grant'])
    original, _, _ = load_grant(live, root, parent, active=active)
    expected = _delegated(original, receipt)
    owner.require(grant == expected, 'child grant is not delegated by its original scope')
    if active:
        owner.require(not os.path.lexists(path.parent/'closed.json') and not os.path.lexists(path.parent/'cancelled.json')
                      and owner.same(request['review'], reviewed(root)),
                      'child grant closed or reviewed machinery changed')


def _delegated(original, receipt):
    return dict(schema=owner.SCHEMA, kind='grant', request=receipt, execution_mode=MODE,
        **{name: original[name] for name in ('operator_approval', 'attended', 'host_boot_sha256',
                                           'started_boottime_ns', 'deadline_boottime_ns')})


def _unexecuted(live, root, child):
    child = owner.direct(root, child)
    owner.require(child.parent.name == 'children' and re.fullmatch('[0-9]{6}', child.name)
                  and child.is_dir() and not child.is_symlink(), 'unexecuted child path differs')
    parent = child.parent.parent/'grant.json'; _, gp, request = load_grant(live, root, parent)
    owner.require(1 <= int(child.name) <= MAX_RESERVATIONS, 'unexecuted child index differs')
    names = {path.name for path in child.iterdir()}
    owner.require(names <= {'request.json', 'selection.json', 'grant.json', 'cancelled.json'},
                  'child has an operation/reservation or unexpected effect records; H0 cancellation forbidden')
    pending = Path(root)/owner.registry.F1_OWNER
    if os.path.lexists(pending):
        value, _ = owner.read(pending)
        owner.require(type(value.get('run_dir')) is str and not Path(value['run_dir']).is_relative_to(child),
                      'child has an unresolved F1 owner')
    inputs = {name: owner.pin(child/name) for name in sorted(names-{'cancelled.json'})}
    return child, parent, gp, inputs


def validate_cancelled(live, root, child):
    child, _, gp, inputs = _unexecuted(live, root, child)
    value, receipt = owner.read(child/'cancelled.json')
    owner.core._exact(value, {'schema', 'scope', 'index', 'inputs', 'no_device_effect', 'reason'}, 'H0 cancellation')
    owner.require(value['schema'] == SCHEMA and value['scope'] == gp and value['index'] == int(child.name)
                  and value['inputs'] == inputs and value['no_device_effect'] is True
                  and type(value['reason']) is str and value['reason'], 'H0 child cancellation differs')
    return receipt


def cancel_child(live, root, child, *, reason):
    """Preserve its ordinal/bytes, return only demonstrably unused capacity."""
    with owner.registry.target_session_lease(root, research_read_only=True):
        child, _, gp, inputs = _unexecuted(live, root, child)
        owner.require(type(reason) is str and 0 < len(reason.strip()) <= 2000, 'H0 cancellation reason differs')
        path = child/'cancelled.json'
        if not os.path.lexists(path):
            owner.publish(path, dict(schema=SCHEMA, scope=gp, index=int(child.name), inputs=inputs,
                                     no_device_effect=True, reason=reason.strip()))
        return validate_cancelled(live, root, child)


def complete_selection(live, root, child):
    """Finish interrupted H0 publication only while the same request is current."""
    with owner.registry.target_session_lease(root):
        child, parent, gp, _ = _unexecuted(live, root, child)
        owner.require(not os.path.lexists(child/'cancelled.json'), 'cancelled selection cannot reopen')
        original, _, _ = load_grant(live, root, parent, active=True)
        value, rp = owner.read(child/'request.json'); validate_child_shape(value)
        owner.require(value['research_scope']['grant'] == gp and value['research_scope']['index'] == int(child.name),
                      'interrupted selection belongs to another scope')
        selection = child/'selection.json'; expected = dict(schema=SCHEMA, scope=gp, index=int(child.name), request=rp)
        if os.path.lexists(selection): owner.require(owner.read(selection)[0] == expected, 'interrupted selection differs')
        else: owner.publish(selection, expected)
        owner.load_request(live, root, child/'request.json', current=True)
        delegated = _delegated(original, rp); path = child/'grant.json'
        if os.path.lexists(path): owner.require(owner.read(path)[0] == delegated, 'interrupted child grant differs')
        else: owner.publish(path, delegated)
        return owner.pin(path)


def before_operation(live, root, child_grant):
    _, _, request, _ = owner.load_grant(live, root, child_grant, active=True)
    parent = owner.verify_pin(root, request['research_scope']['grant'])
    # Scope order follows completed operations. Selecting future data is H0,
    # but cannot overtake an unexecuted or unresolved earlier reservation.
    for index in range(1, request['research_scope']['index']):
        child = parent.parent/'children'/f'{index:06d}'
        if (child/'cancelled.json').exists():
            validate_cancelled(live, root, child); continue
        directory = child/'operation-01'
        operation = owner.load_operation(live, root, directory)
        owner.validate_terminal(live, operation)
        owner.require(owner.read(directory/'completed.json')[0]['terminal'] == owner.pin(directory/'terminal.json'),
                      'previous scoped operation has not completed')


def validate_phase(live, operation, prepared):
    phase = prepared.native_baseline_context['phase']
    native = owner.phase_native(operation, phase)
    _artifacts(live, operation.root, prepared.bundle, native, operation.request['android'])
    if phase == 'experiment' and operation.request['research_scope']['repeat_admission'] is None:
        owner.require(owner.same(owner.native_identity(prepared.bundle), native), 'fresh E source identity changed')


def _repeat_path(root, identity):
    return Path(root)/REPEATS/(identity['candidate_key']+'.json')


def repeat_admission(live, root, path, *, expected=None):
    value, receipt = owner.read(path)
    owner.core._exact(value, {'schema', 'kind', 'operation', 'terminal', 'claim', 'native', 'target'}, 'repeat admission')
    owner.require(value['schema'] == SCHEMA and value['kind'] == 'prospective-repeat-admission', 'repeat admission identity differs')
    original_path = owner.verify_pin(root, value['operation'])
    original = owner.load_operation(live, root, original_path.parent)
    owner.require(owner.research(original.request) and original.value['operation'] == 'experiment'
                  and original.request['research_scope']['repeat_admission'] is None, 'historical or repeated attempt cannot admit E')
    terminal_path = owner.verify_pin(root, value['terminal'])
    terminal = owner.validate_terminal(live, original)
    owner.require(terminal_path == original.directory/'terminal.json'
                  and terminal['state'] == 'NATIVE_CLOSED'
                  and terminal.get('recovery_required') is False
                  and owner.read(original.directory/'completed.json')[0]['terminal'] == value['terminal']
                  and value['native'] == original.request['experiment']['native']
                  and value['target'] == original.request['target'], 'repeat admission lacks original closed health')
    # E must have a complete exact transfer and fixed health; the optional
    # scientific/HUD result does not have to meet a research hypothesis.
    owner.experiment_outcome(live, original)
    identity = live._bound_candidate_registry_identity(owner.primary_prepared(live, original))
    claim = owner.registry.active_claim(root, identity['candidate_key'])
    owner.require(Path(path) == _repeat_path(root, identity) and claim == value['claim']
                  and all(claim.get(k) == v for k, v in identity.items() if k != 'schema'), 'repeat original global claim differs')
    if expected is not None:
        owner.require(expected['native'] == value['native']
                      and expected['bundle'] == original.request['experiment']['bundle']
                      and expected['manifest'] == original.request['experiment']['manifest'], 'repeat candidate changed')
    return value, receipt


def candidate_preflight(live, root, request, prepared):
    identity = live._candidate_registry_identity(prepared)
    repeat = request['research_scope']['repeat_admission']
    if repeat is None:
        owner.registry.preflight_candidate(root, identity)
    else:
        value, _ = repeat_admission(live, root, owner.verify_pin(root, repeat), expected=request['experiment'])
        owner.require(value['target'] == request['target'] and value['claim']['candidate_key'] == identity['candidate_key'],
                      'repeat belongs to another target or content')
    return identity


def claim_candidate(live, operation, primary, identity):
    candidate_preflight(live, operation.root, operation.request, primary)
    repeat = operation.request['research_scope']['repeat_admission']
    if repeat is None:
        return live._claim_candidate_global(primary, identity)
    # This exclusive new intent consumes only this prospective repetition. The
    # original registry entry is neither released nor rewritten.
    return owner.publish(operation.directory/'repeat-intent.json', dict(schema=SCHEMA,
        operation=operation.receipt, admission=repeat, candidate=identity))


def installation_claim(live, operation):
    primary = owner.primary_prepared(live, operation)
    identity = live._bound_candidate_registry_identity(primary)
    repeat = operation.request['research_scope']['repeat_admission']
    if repeat is None:
        claim = owner.registry.active_claim(operation.root, identity['candidate_key'])
        owner.require(claim is not None and all(claim.get(k) == v for k, v in identity.items() if k != 'schema'),
                      'research original candidate claim differs')
        return claim
    value, _ = repeat_admission(live, operation.root, owner.verify_pin(operation.root, repeat), expected=operation.request['experiment'])
    intent, _ = owner.read(operation.directory/'repeat-intent.json')
    owner.require(intent == dict(schema=SCHEMA, operation=operation.receipt, admission=repeat, candidate=identity)
                  and value['target'] == operation.request['target'], 'prospective repeat role intent differs')
    return value['claim']


def complete_operation(live, operation, terminal):
    if operation.value['operation'] != 'experiment' or operation.request['research_scope']['repeat_admission'] is not None:
        return
    if terminal['state'] != 'NATIVE_CLOSED': return
    owner.experiment_outcome(live, operation)
    identity = live._bound_candidate_registry_identity(owner.primary_prepared(live, operation))
    claim = installation_claim(live, operation)
    value = dict(schema=SCHEMA, kind='prospective-repeat-admission', operation=operation.receipt,
        terminal=owner.pin(operation.directory/'terminal.json'), claim=claim,
        native=operation.request['experiment']['native'], target=operation.request['target'])
    path = _repeat_path(operation.root, identity); path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if os.path.lexists(path): owner.require(owner.read(path)[0] == value, 'repeat admission already belongs to another operation')
    else: owner.publish(path, value)


def status(live, root, grant_path):
    grant, gp, request = load_grant(live, root, grant_path)
    children = []
    directory = Path(grant_path).parent/'children'
    for child in sorted(directory.iterdir()) if directory.exists() else ():
        operation = child/'operation-01'
        if (child/'cancelled.json').exists():
            validate_cancelled(live, root, child); state = dict(state='CANCELLED_NO_DEVICE_EFFECT')
        else: state = owner.operation_status(live, owner.load_operation(live, root, operation)) if (operation/'operation.json').exists() else dict(state='PREPARED')
        children.append(dict(child=str(child), **state))
    return dict(schema=SCHEMA, scope=gp, purpose=request['purpose'], children=children,
        reservations=request['reservations'], selected=len(children),
        remaining_seconds=max(0, (grant['deadline_boottime_ns']-owner.protocol.host_now_ns())//10**9),
        host_epoch_matches=grant['host_boot_sha256'] == owner.host_epoch(),
        closed=(Path(grant_path).parent/'closed.json').exists())


def main(argv=None):
    import device_action_f1_live_v2 as live
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    prepare_parser = commands.add_parser('prepare')
    prepare_parser.add_argument('--output', type=Path, required=True)
    prepare_parser.add_argument('--baseline-terminal', type=Path, required=True)
    prepare_parser.add_argument('--operations', nargs='+', choices=OPERATIONS, required=True)
    prepare_parser.add_argument('--profiles', nargs='+', choices=tuple(candidates.RESEARCH_PROFILES), required=True)
    prepare_parser.add_argument('--mutable-paths', nargs='*', choices=tuple(sorted(MUTABLE_INPUTS)), default=[])
    prepare_parser.add_argument('--seconds', type=int, required=True); prepare_parser.add_argument('--reservations', type=int, required=True)
    prepare_parser.add_argument('--recovery', choices=('attended', 'deferred'), required=True)
    prepare_parser.add_argument('--purpose', required=True)
    grant_parser = commands.add_parser('grant'); grant_parser.add_argument('--request', type=Path, required=True)
    grant_parser.add_argument('--approval', required=True); grant_parser.add_argument('--attended', action='store_true')
    select_parser = commands.add_parser('select'); select_parser.add_argument('--grant', type=Path, required=True)
    select_parser.add_argument('--operation', choices=OPERATIONS[1:], required=True)
    select_parser.add_argument('--manifest', type=Path); select_parser.add_argument('--repeat', type=Path)
    select_parser.add_argument('--source-assessment', type=Path)
    execute_parser = commands.add_parser('execute'); execute_parser.add_argument('--grant', type=Path, required=True)
    execute_parser.add_argument('--origin', choices=('native', 'android', 'physical-download'), required=True)
    execute_parser.add_argument('--prior-native', type=Path); execute_parser.add_argument('--attended', action='store_true')
    status_parser = commands.add_parser('status'); status_parser.add_argument('--grant', type=Path, required=True)
    close_parser = commands.add_parser('close'); close_parser.add_argument('--grant', type=Path, required=True)
    cancel_parser = commands.add_parser('cancel-child'); cancel_parser.add_argument('--child', type=Path, required=True)
    cancel_parser.add_argument('--reason', required=True)
    complete_parser = commands.add_parser('complete-selection'); complete_parser.add_argument('--child', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        result = prepare(live, ROOT, args.output, baseline_terminal=args.baseline_terminal, operations=args.operations,
            profiles=args.profiles, mutable_paths=args.mutable_paths, seconds=args.seconds, reservations=args.reservations,
            recovery=args.recovery, purpose=args.purpose)
    elif args.command == 'grant': result = open_grant(live, ROOT, args.request, args.approval, attended=args.attended)
    elif args.command == 'select': result = select(live, ROOT, args.grant, operation=args.operation, manifest=args.manifest,
                                                repeat=args.repeat, source_assessment=args.source_assessment)
    elif args.command == 'execute':
        _, _, request, _ = owner.load_grant(live, ROOT, args.grant)
        owner.require(owner.research(request), 'execute requires a child selected under a research scope')
        result = owner.execute(live, ROOT, args.grant, request['operations'][0], args.origin,
                               prior_native=args.prior_native, attended=args.attended)
    elif args.command == 'status': result = status(live, ROOT, args.grant)
    elif args.command == 'cancel-child': result = cancel_child(live, ROOT, args.child, reason=args.reason)
    elif args.command == 'complete-selection': result = complete_selection(live, ROOT, args.child)
    else:
        with owner.registry.target_session_lease(ROOT):
            _, gp, _ = load_grant(live, ROOT, args.grant)
            result = owner.publish(args.grant.parent/'closed.json', dict(schema=SCHEMA, scope=gp, reason='operator-closed'))
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == '__main__': main()
