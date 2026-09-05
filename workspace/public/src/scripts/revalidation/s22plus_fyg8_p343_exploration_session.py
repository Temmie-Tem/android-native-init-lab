"""P343 private lease instance; reuse the reviewed P335 one-shot journal.

No device transport. Fresh P343 F1 proof/approval is required by the live owner.
"""
from pathlib import Path
import hashlib
import os
import stat
import types

import s22plus_fyg8_readonly_exploration as exploration

SOURCE = Path(__file__).with_name('s22plus_fyg8_p335_resident_session.py')
SOURCE_SHA256 = '58e507f5932b988e701c2311da0c406784fcc76f9873ce98676c4858caf1f6a1'
SCHEMA = 's22plus_fyg8_p343_exploration_lease_v1'
OWNER = 's22plus-fyg8-p343'
DIRECTORY = 'p343-exploration-session'
ACTION_NAMES = tuple(exploration.CATALOG)


def catalog_for(run_id):
    exploration.session_commands('kernel', run_id)
    return {name: {'argv': value.decode('ascii').split(' ')}
            for name, value in exploration.CATALOG.items()}


def _load():
    before = SOURCE.lstat()
    with SOURCE.open('rb') as stream:
        raw = stream.read(27484)
        inside = os.fstat(stream.fileno())
    after = SOURCE.lstat()
    identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
    if (SOURCE.resolve() != SOURCE.absolute() or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1 or identity(before) != identity(inside)
        or identity(before) != identity(after) or len(raw) != 27483
        or hashlib.sha256(raw).hexdigest() != SOURCE_SHA256):
        raise ValueError('P335 lease source differs')
    # The only literal owner in the predecessor validator; no journal semantics
    # are rewritten and no consumed P335 namespace is opened.
    anchor = b'recovery["owner"] != "s22plus-fyg8-p335"'
    if raw.count(anchor) != 1:
        raise ValueError('lease recovery owner anchor differs')
    source = raw.replace(anchor, b'recovery["owner"] != "s22plus-fyg8-p343"', 1)
    module = types.ModuleType('s22plus_fyg8_p343_bound_lease_core')
    module.__file__ = str(SOURCE)
    exec(compile(source, str(SOURCE), 'exec', dont_inherit=True), vars(module))
    module.SCHEMA = SCHEMA
    module.ACTION_NAMES = ACTION_NAMES
    module.catalog_for = catalog_for
    return module


core = _load()
ResidentLease = core.ResidentLease
LeaseError = core.LeaseError
RollbackRequired = core.RollbackRequired
MAX_ACTIONS = core.MAX_ACTIONS
MAX_LEASE_SECONDS = core.MAX_LEASE_SECONDS
TARGET = core.TARGET
canonical_bytes = core.canonical_bytes
validate_binding = core.validate_binding


def binding_for(live, prepared, observation):
    if not live._p343_bundle(prepared.bundle) or not live._p343_proof_ok(observation):
        raise live.F1LiveError('P343 initial proof differs')
    closure = prepared.bundle.receipt['observation_contract']['verification']['ap_payload_closure']
    proof = observation['p343_authenticated_open_read_branch_resident']
    value = {
        'target': dict(TARGET),
        'topology': {'sha256': observation['candidate_topology_sha256']},
        'candidate': {'run_id': live.typed_evidence.P343_RUN_ID,
                      'boot_sha256': closure['boot_image']['sha256'],
                      'ap_sha256': prepared.bundle.manifest['candidate_ap']['sha256']},
        'key': dict(live.P343_AUTH_KEY_IDENTITY),
        'catalog': catalog_for(live.typed_evidence.P343_RUN_ID),
        'recovery': {'kind': 'magisk_boot_only', 'owner': OWNER,
                     'rollback_ap_sha256': prepared.bundle.manifest['rollback_ap']['sha256']},
        'per_boot_id': proof['sessions'][0]['boot_id_sha256'],
    }
    return validate_binding(value)


def before_guard_release(live, prepared, journal, candidate, observation, trace):
    journal.transition('OBSERVED', 'bounded_candidate_observation_closed', observation)
    durable = live._reopen_candidate_observation(prepared)
    proof = bool(candidate.completed and durable.get('download_endpoint_absent') is True
                 and durable.get('accepted') is True and live._p343_proof_ok(durable))
    live._seal_p300_before_candidate_boot_ready(trace, journal, proof)
    if not proof:
        return {'proof': False, 'resident_session_active': False}
    root = prepared.run_dir / DIRECTORY
    root.mkdir(mode=0o700)
    live.core._fsync_dir(prepared.run_dir)
    lease = ResidentLease.publish(root, binding_for(live, prepared, durable),
        {'state':'OBSERVED', 'candidate_boot_ready':True,
         'journal_sha256':journal.records()[-1]['record_sha256']})
    snapshot = lease.snapshot()
    current = live._state(prepared)
    current.update({'resident_session_state':snapshot['state'], 'resident_session_active':True,
                    'resident_lease_id':snapshot['lease_id'],
                    'resident_lease_receipt':live._receipt(root/'lease.json','P343 resident lease'),
                    'resident_guard_receipt':live._receipt(root/'lease.guard.json','P343 resident guard'),
                    'resident_rollback_required':snapshot['rollback_required']})
    live._save_state(prepared,current)
    return {'proof':True, 'resident_session_active':True, 'snapshot':snapshot}


def mark_rollback_required(live, prepared):
    root = prepared.run_dir / DIRECTORY
    if not root.exists() or root.is_symlink():
        return
    try:
        lease = ResidentLease.open(root)
        if not lease.snapshot()['rollback_required']:
            lease.stop('F1 recovery requested')
    except LeaseError:
        pass  # A malformed lease never blocks the already bound rollback owner.
    current = live._state(prepared)
    current['resident_session_active'] = False
    current['resident_rollback_required'] = True
    live._save_state(prepared,current)


def action_summary(live, prepared):
    """Host-only close accounting, never a prerequisite for rollback transfer."""
    rows = []
    try:
        lease = ResidentLease.open(prepared.run_dir / DIRECTORY)
        expected = binding_for(live, prepared, live._reopen_candidate_observation(prepared))
        if canonical_bytes(lease.binding) != canonical_bytes(expected):
            raise ValueError('P343 close lease does not bind this prepared run')
        for ordinal, (intent, outcome) in enumerate(lease.actions, 1):
            row = {'ordinal':ordinal, 'action':intent['action'], 'status':'uncertain', 'receipt_sha256':None}
            if outcome is not None:
                name = 'result.json' if outcome['status']=='ok' else 'failure.json'
                path = prepared.run_dir / 'p343-exploration-actions' / f'action-{ordinal:02d}' / name
                raw, _ = live.core._stable_read(path, 'P343 action close receipt', 256*1024)
                if len(raw)!=outcome['receipt_bytes'] or hashlib.sha256(raw).hexdigest()!=outcome['receipt_sha256']:
                    raise ValueError('P343 action receipt differs')
                value=live._read_json(path,'P343 action close result')
                if (value.get('schema')!='s22plus_fyg8_p343_exploration_action_result_v1'
                    or value.get('action')!=intent['action'] or value.get('ordinal')!=ordinal):
                    raise ValueError('P343 action receipt owner differs')
                if outcome['status']=='ok':
                    if value.get('classification')!='accepted' or value.get('boot_id_sha256')!=lease.binding['per_boot_id']:
                        raise ValueError('P343 successful action result differs')
                    names=('identity',intent['action'],'session-nonce')
                    commands=value.get('commands')
                    expected=exploration.session_commands(intent['action'],lease.binding['candidate']['run_id'])
                    if not isinstance(commands,list) or len(commands)!=3:
                        raise ValueError('P343 command result tuple differs')
                    for item,name,command in zip(commands,names,expected):
                        if (type(item) is not dict or item.get('name')!=name or item.get('ok') is not True or item.get('exit_code')!=0
                            or item.get('signal_number')!=0
                            or item.get('command')!={'size':len(command),'sha256':hashlib.sha256(command).hexdigest()}):
                            raise ValueError('P343 selected command proof differs')
                row.update(status=outcome['status'],receipt_sha256=outcome['receipt_sha256'])
            rows.append(row)
        completed=sum(row['status']=='ok' for row in rows)
        return {'schema':'s22plus_fyg8_p343_exploration_summary_v1','proved':bool(rows) and completed==len(rows),
                'actions':rows,'completed_actions':completed,'reason':None}
    except (OSError,ValueError,KeyError,TypeError,live.F1LiveError,live.core.F1V2Error):
        return {'schema':'s22plus_fyg8_p343_exploration_summary_v1','proved':False,
                'actions':[],'completed_actions':0,'reason':'retained-lease-or-action-evidence-unproved'}


def after_guard_release(live, prepared, backend, journal, endpoint_dir, endpoint_lease, pending):
    release = live._reopen_candidate_guard_release(prepared)
    current = live._state(prepared)
    current.update({'candidate_observer_guard_release_status':release['status'],
                    'candidate_observer_guard_released':release['released'],
                    'candidate_observer_guard_warning':release['warning'],
                    'candidate_observer_guard_release_receipt_sha256':release['receipt_sha256']})
    supported = live._observer_guard_supports_result(accepted=pending['proof'],
                status=release['status'], released=release['released'] is True)
    live._save_state(prepared,current)
    if not pending['proof'] or not supported:
        mark_rollback_required(live, prepared)
        return live._finish_rollback(prepared,backend,journal,endpoint_dir,endpoint_lease)
    snapshot = ResidentLease.open(prepared.run_dir/DIRECTORY).snapshot()
    if snapshot['rollback_required']:
        mark_rollback_required(live,prepared)
        return live._finish_rollback(prepared,backend,journal,endpoint_dir,endpoint_lease)
    return {'schema':'device_action_f1_p343_exploration_active_v1',
            'verdict':'P343_EXPLORATION_SESSION_ACTIVE', 'outcome_class':'p343_current_boot_exploration_active',
            'manifest_id':prepared.bundle.manifest['manifest_id'],
            'run_id':prepared.bundle.manifest['run_id'], 'ordinary_f1_state':'OBSERVED',
            'candidate_boot_ready':True, 'resident_session':snapshot,
            'f1_closed':False, 'rollback_completed':False, 'recovery_required':False}
