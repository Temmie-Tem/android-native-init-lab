"""Named P343 current-boot exploration; callable only by the reviewed F1 owner.

No standalone CLI, caller command/path, retry, or lease renewal. Reuse the P335
pre-EXEC boot binding and journal, with host-first OPEN and raw-first capture.
"""
import fcntl
import hashlib
import inspect
import os
from pathlib import Path
import select
import stat
import termios
import time
import types
import tty

import device_action_raw_capture_v1 as raw_capture
import s22plus_fyg8_readonly_exploration as exploration
import s22plus_fyg8_p343_exploration_session as resident

SOURCE = Path(__file__).with_name('s22plus_fyg8_p335_resident_action.py')
SOURCE_SHA256 = '1580d18068097b31dbc97795631496fa40338b7610b2e3de1a5cee83a7c4198c'
SCHEMA = 's22plus_fyg8_p343_exploration_action_result_v1'
EVIDENCE_DIRECTORY = 'p343-exploration-actions'


def _base():
    before = SOURCE.lstat()
    with SOURCE.open('rb') as stream:
        raw = stream.read(29082)
        inside = os.fstat(stream.fileno())
    after = SOURCE.lstat()
    inode = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
    if (SOURCE.resolve() != SOURCE.absolute() or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1 or inode(before) != inode(inside) or inode(before) != inode(after)
        or len(raw) != 29081 or hashlib.sha256(raw).hexdigest() != SOURCE_SHA256):
        raise ValueError('P335 action source differs')
    module = types.ModuleType('p343_private_action_core')
    module.__file__ = str(SOURCE)
    exec(compile(raw, str(SOURCE), 'exec', dont_inherit=True), vars(module))
    return module


def action_codec(live, action, timeout):
    """Private producer/consumer tuple, checked current boot before first EXEC."""
    module = live._open_header_initial_observer_module(
        live.p343_open_read_runtime, live.p343_open_read_observer, 'p343')
    live.host_first_open.install_observer(module)
    selected = exploration.select_private_codec(module, action)
    if action != 'kernel':
        validator = inspect.getsource(module._validate_one_session)
        anchor = '        or b"Linux" not in second.output\n        or not second.output.endswith(b"\\n")\n'
        if validator.count(anchor) != 1:
            raise ValueError('kernel-only result predicate differs')
        # Only uname has a Linux/newline content claim. Selected-query success
        # requires its exact command, authenticated session and zero exit,
        # not kernel-shaped output (bounded head can end before a newline).
        exec(compile(validator.replace(anchor, '', 1), '<P343 selected result validator>',
                     'exec', dont_inherit=True), vars(module))
    base = _base()
    class Runtime:
        DEFAULT_COMMANDS = selected
        def __getattr__(self, name):
            return getattr(module.runtime, name)
    base.runtime = Runtime()
    base.observer = module
    base.SESSION_TIMEOUT_SEC = timeout
    source = inspect.getsource(base._exchange_before_exec_bound)
    start = source.index('        stage("open-write")')
    end = source.index('        for name, expected_stage in (', start)
    block = source[start:end]
    if block.count('runtime.FRAME_OPEN') != 1 or source.count('        stage("banner-read")') != 1:
        raise ValueError('action OPEN source anchor differs')
    source = source[:start] + source[end:]
    source = source.replace('        stage("banner-read")', block + '        stage("banner-read")', 1)
    exec(compile(source, '<P343 host-first selected action>', 'exec', dont_inherit=True), vars(base))
    return base, module, selected


def context(live, prepared):
    if not live._p343_bundle(prepared.bundle):
        raise live.F1LiveError('not the exact P343 candidate')
    journal = live.core.Journal.reopen(prepared.run_dir / 'transaction', prepared.binding_sha256)
    state = live._state(prepared)
    if (journal.state() != 'OBSERVED' or state.get('candidate_completed') is not True
        or state.get('candidate_classification') != 'odin_transfer_completed'
        or state.get('resident_session_active') is not True
        or state.get('resident_rollback_required') is not False
        or state.get('rollback_completed') is not False):
        raise live.F1LiveError('P343 resident state is not active')
    durable = live._reopen_candidate_observation(prepared)
    if durable.get('accepted') is not True or not live._p343_proof_ok(durable):
        raise live.F1LiveError('P343 initial proof differs')
    binding = resident.binding_for(live, prepared, durable)
    lease = resident.ResidentLease.open(prepared.run_dir / resident.DIRECTORY)
    if resident.canonical_bytes(binding) != resident.canonical_bytes(lease.binding):
        raise live.F1LiveError('P343 lease binding differs')
    key, key_sha = live._p328_read_auth_key(prepared)
    if key_sha != binding['key']['sha256']:
        raise live.F1LiveError('P343 private key differs')
    live._p324_typec_lane_value(prepared, revalidate=True)
    proof = durable['p343_authenticated_open_read_branch_resident']
    nonces = {row['challenge_nonce_sha256'] for row in proof['sessions']}
    if len(nonces) != 4:
        raise live.F1LiveError('P343 initial nonce history differs')
    return lease, binding, key, nonces


def _exchange(live, base, codec, endpoint, identity, key, binding, nonces, writer, expires_ns):
    path = Path('/dev') / endpoint.tty_name
    before = path.stat()
    if not stat.S_ISCHR(before.st_mode) or (os.major(before.st_rdev), os.minor(before.st_rdev)) != (endpoint.major, endpoint.minor):
        raise live.F1LiveError('P343 tty identity differs')
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW)
    result = None
    try:
        fcntl.ioctl(fd, termios.TIOCEXCL)
        tty.setraw(fd, termios.TCSANOW)
        repeated_identity, repeated = live.cdc_acm_observer._resolve_endpoint(endpoint.tty_class)
        if repeated.identity_sha256 != endpoint.identity_sha256 or repeated_identity != identity or os.fstat(fd).st_rdev != before.st_rdev:
            raise live.F1LiveError('P343 tty changed after open')
        remaining = (expires_ns - time.monotonic_ns()) / 1e9
        if remaining <= 0:
            raise live.F1LiveError('P343 lease expired before OPEN')
        base.SESSION_TIMEOUT_SEC = min(30.0, remaining)
        result = base._exchange_before_exec_bound(fd, key, writer, binding['per_boot_id'], nonces)
        record = codec._record_success(0, 1, fd, result)
        codec._validate_one_session(record, record.boot_id)
        if select.select([fd], [], [], 0)[0]:
            try:
                trailing = os.read(fd, 1)
            except BlockingIOError:
                trailing = b''
            if trailing:
                writer.write_stdout(trailing)
                result.audit.rx.extend(trailing)
                raise live.F1LiveError('P343 trailing bytes after CLOSE')
        return record
    except BaseException as exc:
        if result is not None:
            exc.audit = result.audit
        raise
    finally:
        os.close(fd)


def run_action(live, prepared, action):
    exploration.command(action)  # reject before even opening the lease
    with live.consumed_registry.target_session_lease(prepared.root):
        with live.odin_core.transaction_session(prepared.run_dir / 'f1-session'):
            return _run_locked(live, prepared, action)


def _run_locked(live, prepared, action):
    lease, binding, key, nonces = context(live, prepared)
    snapshot = lease.snapshot()
    if snapshot['rollback_required']:
        raise live.F1LiveError('P343 lease requires rollback')
    remaining = (lease.lease['expires_monotonic_ns'] - time.monotonic_ns()) / 1e9
    if remaining <= 0:
        raise live.F1LiveError('P343 lease expired')
    base, codec, selected = action_codec(live, action, min(30.0, remaining))
    evidence = prepared.run_dir / EVIDENCE_DIRECTORY
    for ordinal, (intent, outcome) in enumerate(lease.actions, 1):
        if outcome is None or outcome['status'] != 'ok':
            raise live.F1LiveError('P343 prior action is unresolved')
        value, payload = base._strict_json(evidence / f'action-{ordinal:02d}' / 'result.json', 'P343 prior action', 256*1024)
        if (base.identity(payload) != {'size': outcome['receipt_bytes'], 'sha256': outcome['receipt_sha256']}
            or value.get('schema') != SCHEMA or value.get('action') != intent['action']
            or value.get('ordinal') != ordinal or value.get('classification') != 'accepted'
            or value.get('boot_id_sha256') != binding['per_boot_id']):
            raise live.F1LiveError('P343 prior action result differs')
        nonce = value['challenge_nonce_sha256']
        if type(nonce) is not str or len(nonce) != 64 or nonce == '0'*64 or nonce in nonces:
            raise live.F1LiveError('P343 prior nonce differs')
        nonces.add(nonce)
    endpoint, endpoint_identity = base._select_endpoint(prepared, binding)
    if not evidence.exists():
        base._mkdir(evidence)
    directory = evidence / f'action-{snapshot["actions_started"]+1:02d}'
    base._mkdir(directory)
    properties = live.cdc_acm_observer._udev_properties(endpoint.tty_class, directory, 'udev-before-intent')
    if any(properties.get(k) != v for k, v in {'ID_MM_DEVICE_IGNORE':'1','ID_MM_PORT_IGNORE':'1','ID_USB_INTERFACE_NUM':'00'}.items()):
        raise live.F1LiveError('P343 udev guard differs')
    intent = lease.begin_action(action, binding)
    writer = None
    record = None
    try:
        repeated, identity = base._select_endpoint(prepared, binding)
        if repeated.identity_sha256 != endpoint.identity_sha256 or identity != endpoint_identity:
            raise live.F1LiveError('P343 endpoint changed after intent')
        properties = live.cdc_acm_observer._udev_properties(repeated.tty_class, directory, 'udev-after-intent')
        if any(properties.get(k) != v for k, v in {'ID_MM_DEVICE_IGNORE':'1','ID_MM_PORT_IGNORE':'1','ID_USB_INTERFACE_NUM':'00'}.items()):
            raise live.F1LiveError('P343 udev guard changed after intent')
        writer = raw_capture.RawCaptureWriter(directory, 'session-rx', stdout_maximum=512*1024, stderr_maximum=4096)
        remaining = (lease.lease['expires_monotonic_ns'] - time.monotonic_ns()) / 1e9
        if remaining <= 0:
            raise live.F1LiveError('P343 lease expired before exchange')
        base.SESSION_TIMEOUT_SEC = min(30.0, remaining)
        record = _exchange(live, base, codec, repeated, identity, key, binding, nonces, writer,
                           lease.lease['expires_monotonic_ns'])
        handle = writer.finalize(returncode=0)
        tx = base._write_once(directory / 'session.tx.bin', record.raw_tx)
        output = base._write_once(directory / 'selected.stdout.bin', record.result.commands[1].output)
        commands = [{'name': name, 'command': base.identity(item.command), 'output': base.identity(item.output),
                     'exit_code': item.exit_code, 'signal_number': item.term_signal, 'duration_ms': item.duration_ms,
                     'ok': item.ok} for name,item in zip(('identity', action, 'session-nonce'), record.result.commands)]
        if tuple(item.command for item in record.result.commands) != selected:
            raise live.F1LiveError('P343 selected tuple differs')
        value = {'schema': SCHEMA, 'classification': 'accepted', 'action': action, 'ordinal': intent['ordinal'],
                 'boot_id_sha256': hashlib.sha256(record.boot_id).hexdigest(),
                 'challenge_nonce_sha256': hashlib.sha256(record.nonce).hexdigest(),
                 'commands': commands, 'selected_output': output, 'raw_tx': tx,
                 'raw_rx': {'path': str(handle.receipt_path)}, 'caller_selected_command': False,
                 'interactive_pty': False, 'persistent_change': False, 'replay_authorized': False}
        receipt = base._write_once(directory / 'result.json', base.canonical(value))
        lease.record_action_result(intent, {'status':'ok', 'receipt_bytes':receipt['size'], 'receipt_sha256':receipt['sha256']}, binding)
    except BaseException as exc:
        audit = record.result.audit if record is not None else getattr(exc, 'audit', None)
        retention_errors = []
        if writer is not None and not writer.finished:
            try:
                writer.finalize(returncode=None, producer_error_type=type(exc).__name__)
            except Exception as retention_error:
                retention_errors.append(type(retention_error).__name__)
        try:
            failure_tx = base._write_once(directory / 'failure.tx.bin', bytes(audit.tx) if audit is not None else b'')
        except Exception as retention_error:
            failure_tx = None
            retention_errors.append(type(retention_error).__name__)
        failure = {'schema':SCHEMA, 'classification':'uncertain', 'action':action, 'ordinal':intent['ordinal'],
                   'failure_stage':getattr(audit,'failure_stage',None) or getattr(audit,'current_stage',None),
                   'error_type':type(exc).__name__, 'error_sha256':hashlib.sha256(str(exc).encode()).hexdigest(),
                   'raw_tx':failure_tx, 'retention_errors':retention_errors, 'replay_authorized':False}
        receipt = base._write_once(directory / 'failure.json', base.canonical(failure))
        lease.record_action_result(intent, {'status':'uncertain','receipt_bytes':receipt['size'],'receipt_sha256':receipt['sha256']}, binding)
        raise live.F1LiveError('P343 action uncertain; only exact rollback may follow') from exc
    return {'schema':SCHEMA, 'verdict':'PASS_P343_NAMED_READONLY_ACTION', 'action':action,
            'result':receipt, 'selected_output':output, 'lease':lease.snapshot(), 'device_contact':True,
            'replay_authorized':False}
