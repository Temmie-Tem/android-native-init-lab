#!/usr/bin/env python3
"""Fresh per-request owner for the reviewed S22+ terminal transport."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = ROOT / 'workspace/public/src/scripts/revalidation'
sys.path.insert(0, str(REVALIDATION))
import consumed_candidate_registry_v1 as registry
import s22plus_native_records_v3 as records

UID = 1000
REVIEW = 'workspace/public/src/device-action/bindings/s22plus_approved_terminal_persistent_current.json'
POLICY = 'docs/operations/S22PLUS_APPROVED_TERMINAL_PERSISTENT_V1.md'
DISPATCH = 'terminal-tool-dispatch-v1'
CONTINUATIONS = {'continue_approved_task': ('terminal-tool-continue-v1', 'continue'),
    'resume_approved_health': ('terminal-tool-health-v1', 'recover')}
MAX_REQUEST = 65536
MAX_RESPONSE = 262144
MAX_LOG = 32768
PROFILES = {
    'thermal-v3-reconnect-ufs-drain-root-evidence-v1': ('root-evidence', 1800),
    'thermal-v3-reconnect-ufs-drain-journal-recovery-v1': ('journal-recovery', 1800),
    'debian-autoboot-v1': ('debian-autoboot', 3600),
}
GUARDS = dict(guard_uid=UID, guard_euid=UID, guard_nnp=0, guard_argc=1,
    no_prior_grant_operation_preflight=True, exclusive_attempt_log=True,
    one_original_open_grant=True, one_original_attended_execute=True,
    no_retry_loop=True, actual_approval_record_required=True)
INSTRUCTIONS = (
    'S22+ approved task launcher, status and bounded private logs only. '
    'Use start_approved_task only after the human returned the exact attended '
    'approval and its existing operator-approval record was saved. Review or '
    'readiness alone grants nothing. Never retry a consumed dispatch, fabricate '
    'approval, bypass the original runner, or infer non-execution from absence. '
    'The operator must remain physically present through original-A return. '
    'continue_approved_task resumes only the existing automatic-boot physical '
    'return after physical Download. resume_approved_health is '
    'limited to an already raw-proved original-A transfer; it cannot flash. '
    'No shell, cancellation, general recovery or other-target execution is exposed.')


def require(value, message):
    records.require(value, message)


def decode(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique,
        parse_constant=lambda value: require(False, 'nonfinite JSON number'))


def nnp():
    rows = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    return int(rows['NoNewPrivs'].strip())


def runtime_directory():
    return Path('/run/user') / str(UID) / 's22-approved-terminal-v1'


def direct_directory(path, *, create=False):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=False) == path, 'indirect directory')
    if create:
        path.mkdir(mode=0o700, exist_ok=True)
        records.sync_dir(path.parent)
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == UID and
        stat.S_IMODE(info.st_mode) == 0o700, 'directory owner/mode differs')
    return path


def checked_file(root, receipt, *, maximum=4 * 1024 * 1024):
    path = Path(receipt['path'])
    require(path.is_absolute() and path.is_relative_to(root) and '..' not in path.parts,
        'receipt is outside the selected repository')
    return records.verify(receipt, maximum=maximum)


def review_sources(root):
    return sorted([root / name for name in (
        'AGENTS.md', 'docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md',
        'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md',
        'docs/operations/DEVICE_ACTION_RISK_TIERS.md', POLICY,
        'workspace/public/src/scripts/host_tools/s22plus_approved_terminal_tasks_v1.py',
        'workspace/public/src/scripts/host_tools/s22plus_approved_terminal_persistent_v1.py',
        'workspace/public/src/scripts/revalidation/s22plus_native_records_v3.py',
        'workspace/public/src/scripts/revalidation/s22plus_native_task_v3.py',
        'workspace/public/src/scripts/revalidation/s22plus_native_session_v3.py',
        'workspace/public/src/scripts/revalidation/s22plus_native_adapter_v3.py',
        'workspace/public/src/scripts/revalidation/s22plus_debian_handoff_session_v1.py',
        'workspace/public/src/scripts/revalidation/s22plus_debian_autoboot_session_v1.py',
        'workspace/public/src/scripts/revalidation/consumed_candidate_registry_v1.py')])


def verify_bridge(root, expected=None):
    from s22plus_approved_terminal_persistent_v1 import selected_review
    value, receipt = selected_review(root, expected=expected)
    require([row['path'] for row in value['sources']] == [str(p) for p in review_sources(root)],
        'backend review source closure differs')
    return receipt


class AdmissionLock:
    """Share admission across fresh backends, while never waiting on a device."""
    def __init__(self, root):
        self.path = root / 'workspace/private/terminal-tool-admission-v1.lock'
        self.local = threading.Lock()

    def __enter__(self):
        self.local.acquire()
        self.fd = None
        try:
            require(self.path.resolve(strict=False) == self.path, 'indirect admission lock')
            self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            info = os.fstat(self.fd)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == UID and info.st_nlink == 1 and
                stat.S_IMODE(info.st_mode) == 0o600 and self.path.stat().st_ino == info.st_ino,
                'admission lock identity differs')
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return self
        except BaseException:
            if self.fd is not None: os.close(self.fd)
            self.local.release()
            raise

    def __exit__(self, *error):
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
        finally:
            self.local.release()


def process_identity(pid):
    try:
        text = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return dict(pid=pid, start_ticks=int(text[19]), host_boot=records.host_boot())
    except (OSError, ValueError, IndexError):
        return None


def process_alive(value):
    return value is not None and process_identity(value['pid']) == value


class Controller:
    def __init__(self, root, *, bridge_check=verify_bridge):
        self.root = Path(root).resolve(strict=True)
        self.outputs = self.root / 'workspace/private/outputs'
        self.bridge_check = bridge_check
        self.bridge_identity = bridge_check(self.root)
        self.lock = AdmissionLock(self.root)

    def bundle(self, name, *, current=False, approval=False):
        require(type(name) is str and len(name) <= 512, 'invalid preparation directory')
        base = Path(name)
        require(base.is_absolute() and base.parent == self.outputs and
            re.fullmatch(r's22plus-[a-z0-9-]+-h0-[0-9]{8}-[0-9]+', base.name) and
            base.resolve(strict=True) == base, 'not a direct S22+ preparation directory')
        task_dir = base / 'offline-prepared-1/task'
        prepared_pin = records.pin(base / 'prepared-validation.json')
        prepared = records.read(checked_file(self.root, prepared_pin))
        task_pin = records.pin(task_dir / 'task.json')
        require(prepared['status'] == 'READY_H0_PRELIVE_ONLY' and prepared['task'] == task_pin,
            'preparation/task binding differs')
        task = records.read(checked_file(self.root, task_pin))
        namespace = task['N']['namespace']
        require(re.fullmatch(r'p[0-9]{3,6}', namespace) and
            task['N']['profile'] in PROFILES and
            task['operations'] == [PROFILES[task['N']['profile']][0]] and
            task['seconds'] == PROFILES[task['N']['profile']][1] and task['operation_budget'] == 1 and
            task['recovery_mode'] == 'attended' and task['E'] is None,
            'unsupported approved task scope')
        entry_pin = records.pin(base / f'run-approved-{namespace}.py')
        proposal_pin = records.pin(task_dir / 'proposal.json')
        proposal = records.read(checked_file(self.root, proposal_pin))
        require(proposal['task'] == task_pin and prepared['proposal'] == proposal_pin,
            'proposal differs')
        narrow_pin = records.pin(base / 'review/prepared-entry-review.json')
        narrow = records.read(checked_file(self.root, narrow_pin))
        require(narrow['schema'] == f's22plus-{namespace}-independent-prepared-entry-review-v1' and
            narrow['status'] == 'PASS_READY_H0_AND_UNEXECUTED_ENTRY' and narrow['findings'] == [] and
            narrow['entry_once_guards'] == GUARDS and narrow['approved_binding_preserved'] is True and
            narrow['prepared'] == prepared_pin and narrow['task'] == task_pin and
            narrow['proposal'] == proposal_pin and narrow['entry'] == entry_pin and
            narrow['source_snapshot'] == prepared['source_snapshot'] and
            narrow['public_binding'] == prepared['review'] == task['review'],
            'independent prepared-entry review does not match')
        checked_file(self.root, entry_pin)
        checked_file(self.root, prepared['source_snapshot'])
        core = records.read(checked_file(self.root, narrow['capability_review']))
        public = records.read(checked_file(self.root, task['review']))
        require(public['schema'] == 's22plus-native-session-v3-review' and
            public['verdict'] == 'PASS_GO' and public['scope'] == 'V3_REACHABLE_CAPABILITY' and
            public['findings'] == [] and task['runtime_scope'] == public['runtime_sources'],
            'capability binding differs')
        if task['N']['profile'] == 'debian-autoboot-v1':
            require(core.get('schema') == f's22plus-{namespace}-independent-capability-review-v1' and
                core.get('verdict') == 'PASS_GO' and core.get('findings') == [] and
                core.get('scope') == 'V3_REACHABLE_CAPABILITY' and
                core.get('candidate') == namespace and core.get('profile') == task['N']['profile'] and
                core.get('version') == task['N']['version'] and
                public['reviewer']['review'] == narrow['capability_review'], 'autoboot core review differs')
        else:
            require(core['status'] == 'PASS_GO' and core['findings'] == [], 'core review differs')
        previous_pin = narrow['actual_preceding_closed']
        previous = records.read(checked_file(self.root, previous_pin))
        previous_task = records.read(checked_file(self.root, previous['task']))
        require(previous['terminal_state'] == 'ANDROID_CLOSED_HEALTHY' and
            previous_task['target'] == task['target'] and previous_task['A'] == task['A'],
            'preceding closure target or original A differs')
        if current:
            for row in public['sources']:
                checked_file(self.root, row)
            for path, identity in public['runtime_sources'].items():
                require(not Path(path).is_absolute() and '..' not in Path(path).parts, 'invalid runtime path')
                checked_file(self.root, dict(path=str(self.root / path), **identity))
        approved = None
        if approval:
            approval_pin = records.pin(base / 'operator-approval.json')
            approved = records.read(checked_file(self.root, approval_pin))
            require(approved['task'] == task_pin and approved['entry'] == entry_pin and
                approved['preceding_closed'] == previous_pin and
                approved['selected_returned_approval'] == proposal['approval'] and
                type(approved['actual_user_text']) is str and approved['actual_user_text'].strip(),
                'actual returned operator approval does not match')
            approved = approval_pin
        return dict(base=base, directory=task_dir, task=task_pin, task_value=task,
            entry=entry_pin, review=narrow_pin, approval=approved,
            preceding_closed=previous_pin, namespace=namespace, operation=task['operations'][0])

    def dispatch_state(self, base, phase=DISPATCH):
        folder = base / phase
        intent_path = folder / 'intent.json'
        if not intent_path.exists():
            return dict(state='NOT_DISPATCHED')
        intent = records.read(intent_path)
        result_path = folder / 'result.json'
        result = None
        if result_path.exists():
            result = records.read(result_path)
            require(result['intent'] == records.pin(intent_path), 'dispatch result binding differs')
        spawned_path = folder / 'spawned.json'
        if spawned_path.exists():
            spawned = records.read(spawned_path)
            require(spawned['intent'] == records.pin(intent_path), 'spawn binding differs')
            if process_alive(spawned['process']):
                return dict(state='RUNNING', pid=spawned['process']['pid'])
        closed_path = Path(intent['task']['path']).parent / 'closed.json'
        if closed_path.exists():
            closed = records.read(closed_path)
            terminal = records.read(checked_file(self.root, closed['current_android_terminal']))
            if closed['task'] == intent['task'] and closed['terminal_state'] == 'ANDROID_CLOSED_HEALTHY' and \
                    terminal['terminal_state'] == 'ANDROID_CLOSED_HEALTHY' and terminal['research_closed'] is True:
                return dict(state='CLOSED_BY_ORIGINAL_OWNER', returncode=None)
        if result is not None:
            return dict(state=result['state'], returncode=result.get('returncode'),
                detail='Process exit is not device closure; this dispatch remains unresolved.')
        return dict(state='DISPATCH_UNCERTAIN', returncode=None,
            detail='Preserve intent and original journals; do not launch again.')

    def status(self, name):
        bound = self.bundle(name)
        base, directory = bound['base'], bound['directory']
        value = dict(namespace=bound['namespace'], operation=bound['operation'],
            task_sha256=bound['task']['sha256'], dispatch=self.dispatch_state(base),
            approval_record_present=(base / 'operator-approval.json').exists(),
            grant_opened=(directory / 'grant.json').exists(),
            closed=(directory / 'closed.json').exists(), terminal_state=None)
        value['continuations'] = {name: self.dispatch_state(base, phase)
            for name, (phase, _) in CONTINUATIONS.items()}
        terminal_paths = sorted(directory.glob('operation-*/terminal.json'))
        if terminal_paths:
            require(len(terminal_paths) == 1, 'multiple operation terminals')
            value['terminal_state'] = records.read(terminal_paths[0]).get('terminal_state')
        return value

    def start(self, name):
        with self.lock:
            bridge = self.bridge_check(self.root)
            require(bridge == self.bridge_identity, 'bridge review changed; restart the worker before dispatch')
            bound = self.bundle(name, current=True, approval=True)
            base, directory = bound['base'], bound['directory']
            state = self.dispatch_state(base)
            if state['state'] != 'NOT_DISPATCHED':
                return dict(dispatched=False, repeated_request=True, **self.status(name))
            registry.require_no_f1_owner(self.root)
            for other in self.outputs.glob('*/' + DISPATCH + '/intent.json'):
                require(self.dispatch_state(other.parent.parent)['state'] == 'CLOSED_BY_ORIGINAL_OWNER',
                    'another dispatch is running or unresolved')
            require(not (directory / 'grant.json').exists() and not list(directory.glob('operation-*')) and
                not (directory / 'grant-host-preflight').exists() and not (base / 'execute-1.log').exists(),
                'original attempt already exists; inspect its original owner')
            folder = direct_directory(base / DISPATCH, create=True)
            intent = records.publish(folder / 'intent.json', dict(schema='s22plus-terminal-dispatch-v1',
                task=bound['task'], entry=bound['entry'], approval=bound['approval'],
                entry_review=bound['review'], bridge_review=bridge,
                preceding_closed=bound['preceding_closed'], host_boot=records.host_boot(),
                boottime_ns=records.clock(), command=['/usr/bin/python3', bound['entry']['path']]))
            try:
                with (folder / 'launcher.log').open('xb') as output:
                    os.chmod(folder / 'launcher.log', 0o600)
                    process = subprocess.Popen(['/usr/bin/python3', bound['entry']['path']],
                        cwd=self.root, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                        close_fds=True, start_new_session=True)
                    identity = process_identity(process.pid)
                    require(identity is not None, 'spawned process identity unavailable; dispatch remains consumed')
                    records.publish(folder / 'spawned.json', dict(intent=intent, process=identity))
            except BaseException as error:
                records.publish(folder / 'result.json', dict(intent=intent, state='SPAWN_ERROR',
                    error_type=type(error).__name__, error=str(error), returncode=None))
                raise
            def finish():
                result = process.wait()
                records.publish(folder / 'result.json', dict(intent=intent, state='PROCESS_EXITED',
                    process=identity, returncode=result, boottime_ns=records.clock()))
            threading.Thread(target=finish, daemon=False).start()
            return dict(dispatched=True, repeated_request=False, **self.status(name))

    def finished_dispatch(self, base, phase, task):
        folder = base / phase
        intent_pin = records.pin(folder / 'intent.json')
        intent = records.read(folder / 'intent.json')
        result = records.read(folder / 'result.json')
        require(intent['task'] == task and intent['host_boot'] == records.host_boot() and
            result['intent'] == intent_pin and result['state'] == 'PROCESS_EXITED' and
            type(result['returncode']) is int, 'original dispatch is unresolved')
        spawned = records.read(folder / 'spawned.json')
        require(spawned['intent'] == intent_pin and result['process'] == spawned['process'] and
            not process_alive(spawned['process']), 'original dispatch is still running or differs')
        return intent_pin

    def continuation_binding(self, bound, tool):
        """Read the existing owner and raw evidence; never create a grant or operation."""
        from s22plus_native_task_v3 import validate_grant
        from s22plus_native_session_v3 import Session, Step
        from s22plus_native_adapter_v3 import Adapter
        from s22plus_native_session_v3 import operation_steps
        base, directory = bound['base'], bound['directory']
        require(bound['operation'] == 'debian-autoboot', 'continuation requires automatic boot')
        require(not (directory / 'closed.json').exists(), 'task is already closed')
        operation = directory / 'operation-0001'
        require(list(directory.glob('operation-*')) == [operation] and
            not (operation / 'terminal.json').exists() and not (operation / 'unused.json').exists(),
            'operation is missing, ambiguous or terminal')
        original = self.finished_dispatch(base, DISPATCH, bound['task'])
        start = records.read(checked_file(self.root, original))
        require(start['entry'] == bound['entry'] and start['approval'] == bound['approval'] and
            start['entry_review'] == bound['review'], 'original dispatch binding differs')
        for phase, _ in CONTINUATIONS.values():
            if (base / phase / 'intent.json').exists():
                self.finished_dispatch(base, phase, bound['task'])
        session = Session(self.root, operation, Adapter(self.root, operation))
        request = session.request
        grant_pin = records.pin(directory / 'grant.json')
        require(request['task'] == bound['task'] and request['grant'] == grant_pin and
            request['operation'] == 'debian-autoboot' and request['N'] == bound['task_value']['N'] and
            request['A'] == bound['task_value']['A'] and request['E'] is None and
            request['reentry'] is False and request['hud'] is False and request['usb_reconnect'] is False,
            'original operation scope differs')
        validate_grant(bound['task_value'], session.grant, directory / 'grant.json')
        health_only = tool == 'resume_approved_health'
        session.check(recovery=health_only)
        require(session.consumed() is not None, 'operation has no original consumption')
        registry.require_f1_owner(self.root, operation, session.binding)
        rows = session.rows()
        evidence = dict(original_dispatch=original, task=bound['task'], grant=grant_pin,
            operation=records.pin(operation / 'operation.json'), approval=bound['approval'],
            journal_tail=records.pin(session.journal.directory / f'{len(rows)-1:04d}.json'))
        android = [row for row in rows if row['event'] == 'effect-intent' and
            row['data']['action'] == 'transfer' and row['data']['role'] == 'A']
        if health_only:
            require(len(android) == 1 and android[0]['data']['step'] == 'install-android',
                'health continuation requires one original-A intent')
            # This raw consumer raises on uncertainty. The original recover CLI
            # also follows its existing-A branch and has no second-transfer path.
            step = Step('install-android', 'transfer', 'A')
            proof = session.adapter.recover_transfer_result(step, request)
            require(proof['completed'] is True, 'original-A completion is unproved')
            evidence['android_transfer'] = proof
        else:
            require(not android and not any(row['event'] == 'stopped' for row in rows),
                'normal continuation is stopped or already returning')
            plan = operation_steps(request)
            require(not any(row['event'] in ('step-start', 'step-complete', 'effect-intent') and
                row['data'].get('step') in ('install-android', 'android-final', 'recovery-health')
                for row in rows) and not any((operation / (step.name + '.json')).exists()
                for step in plan[-2:]), 'Android return has already started')
            for step in plan[:-2]:
                completed = [row for row in rows if row['event'] == 'step-complete' and
                    row['data']['step'] == step.name]
                require(len(completed) == 1 and completed[0]['data']['result'] ==
                    records.pin(operation / (step.name + '.json')), 'preceding step is incomplete')
                session.adapter.validate_result(step,
                    records.read(checked_file(self.root, completed[0]['data']['result'])), request)
            ready_pin = records.pin(operation / 'debian-return-ready.json')
            ready = records.read(checked_file(self.root, ready_pin))
            require(ready['operation'] == evidence['operation'] and
                ready['shutdown'] == records.pin(operation / 'debian-shutdown.json') and
                type(ready['requested_ns']) is int and type(ready['deadline_ns']) is int and
                ready['deadline_ns'] == min(session.grant['deadline_ns'], ready['requested_ns'] + 600_000_000_000) and
                session.grant['opened_ns'] <= ready['requested_ns'] <= records.clock() < ready['deadline_ns'],
                'physical return request differs or expired')
            evidence['return_ready'] = ready_pin
        return operation, evidence

    def continue_task(self, name, tool):
        phase, command = CONTINUATIONS[tool]
        with self.lock:
            bridge = self.bridge_check(self.root)
            require(bridge == self.bridge_identity, 'bridge review changed; restart the worker before dispatch')
            bound = self.bundle(name, current=True, approval=True)
            base = bound['base']
            if self.dispatch_state(base, phase)['state'] != 'NOT_DISPATCHED':
                return dict(dispatched=False, repeated_request=True, **self.status(name))
            with registry.target_session_lease(self.root):
                operation, evidence = self.continuation_binding(bound, tool)
                argv = ['/usr/bin/python3', str(self.root / 'workspace/public/src/scripts/revalidation/s22plus_native_task_v3.py'),
                    '--root', str(self.root), command, str(operation), '--attended']
                folder = direct_directory(base / phase, create=True)
                intent = records.publish(folder / 'intent.json', dict(schema='s22plus-terminal-continuation-v1',
                    tool=tool, **evidence, bridge_review=bridge, host_boot=records.host_boot(),
                    boottime_ns=records.clock(), command=argv))
            # The original CLI takes the same target lease and rechecks its
            # durable owner/journal before any action. A manual CLI racing this
            # boundary cannot turn an existing transfer intent into a replay.
            try:
                with (folder / 'launcher.log').open('xb') as output:
                    os.chmod(folder / 'launcher.log', 0o600)
                    process = subprocess.Popen(argv, cwd=self.root, stdin=subprocess.DEVNULL,
                        stdout=output, stderr=subprocess.STDOUT, close_fds=True, start_new_session=True)
                    identity = process_identity(process.pid)
                    require(identity is not None, 'continuation process identity unavailable; dispatch remains consumed')
                    records.publish(folder / 'spawned.json', dict(intent=intent, process=identity))
            except BaseException as error:
                records.publish(folder / 'result.json', dict(intent=intent, state='SPAWN_ERROR',
                    error_type=type(error).__name__, error=str(error), returncode=None))
                raise
            def finish():
                result = process.wait()
                records.publish(folder / 'result.json', dict(intent=intent, state='PROCESS_EXITED',
                    process=identity, returncode=result, boottime_ns=records.clock()))
            threading.Thread(target=finish, daemon=False).start()
            return dict(dispatched=True, repeated_request=False, **self.status(name))

    def log(self, name, stream='launcher', count=8192):
        bound = self.bundle(name)
        paths = {'launcher': DISPATCH + '/launcher.log', 'execution': 'execute-1.log',
            'continuation': CONTINUATIONS['continue_approved_task'][0] + '/launcher.log',
            'health': CONTINUATIONS['resume_approved_health'][0] + '/launcher.log'}
        require(stream in paths and type(count) is int and 1 <= count <= MAX_LOG,
            'invalid log selection or byte limit')
        path = bound['base'] / paths[stream]
        if not path.exists():
            return dict(exists=False, stream=stream, text='')
        require(path.resolve(strict=True) == path, 'indirect log')
        before = path.lstat()
        require(stat.S_ISREG(before.st_mode) and before.st_uid == UID and before.st_nlink == 1,
            'invalid log path')
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == UID and info.st_nlink == 1, 'invalid log file')
            start = max(0, info.st_size - count)
            data = os.pread(fd, count, start)
        finally:
            os.close(fd)
        return dict(exists=True, stream=stream, observed_size=info.st_size, offset=start,
            returned_bytes=len(data), text=data.decode('utf-8', errors='replace'))

    def call(self, name, arguments):
        require(type(arguments) is dict, 'arguments must be an object')
        if name == 'bridge_status':
            require(not arguments, 'bridge_status takes no arguments')
            return dict(worker_connected=True, uid=os.getuid(), euid=os.geteuid(),
                no_new_privileges=nnp(), root=str(self.root), device_authority=False,
                bridge_review=self.bridge_identity)
        allowed = {'preparation_directory'} | ({'stream', 'bytes'} if name == 'task_log' else set())
        require(name in ('task_status', 'start_approved_task', 'task_log', *CONTINUATIONS) and
            set(arguments) <= allowed and 'preparation_directory' in arguments, 'unsupported tool or arguments')
        directory = arguments['preparation_directory']
        if name == 'task_status':
            return self.status(directory)
        if name == 'start_approved_task':
            return self.start(directory)
        if name in CONTINUATIONS:
            return self.continue_task(directory, name)
        return self.log(directory, arguments.get('stream', 'launcher'), arguments.get('bytes', 8192))


def main():
    require(os.getuid() == os.geteuid() == UID and nnp() == 0,
        'backend must inherit the ordinary-terminal worker identity')
    try:
        line = sys.stdin.buffer.readline(MAX_REQUEST + 1)
        require(0 < len(line) <= MAX_REQUEST and line.endswith(b'\n'), 'backend request framing differs')
        request = decode(line)
        require(type(request) is dict and set(request) == {'tool', 'arguments', 'review'},
            'backend request fields differ')
        selected = request['review']
        controller = Controller(ROOT, bridge_check=lambda root: verify_bridge(root, expected=selected))
        value = controller.call(request['tool'], request['arguments'])
        response = dict(ok=True, value=value, backend_review=controller.bridge_identity)
    except Exception as error:
        response = dict(ok=False, error=type(error).__name__ + ': ' + str(error))
    try:
        sys.stdout.buffer.write(records.canonical(response))
        sys.stdout.buffer.flush()
    except (BrokenPipeError, OSError):
        # Loss of the RPC client never cancels or retries a dispatched entry.
        pass
    finally:
        try: sys.stdout.close()
        except (BrokenPipeError, OSError): pass
    # Non-daemon result owners keep this fresh process alive until the existing
    # entry exits and its durable result is published; RPC stdout is closed.


if __name__ == '__main__': main()
