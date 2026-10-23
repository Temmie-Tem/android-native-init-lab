"""Host-only terminal transport tests; fixture entries only write temp markers."""
import concurrent.futures
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'workspace/public/src/scripts/host_tools/s22plus_approved_terminal_v1.py'
spec = importlib.util.spec_from_file_location('approved_terminal', SOURCE)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
records = bridge.records


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(records.canonical(value))
    return records.pin(path)


def fixture(root, ordinal=1, entry=None, *,
            profile='thermal-v3-reconnect-ufs-drain-root-evidence-v1',
            operation=None, seconds=None, core_changes=None, public_core=None):
    base = root / f'workspace/private/outputs/s22plus-fixture-h0-20261023-{ordinal}'
    directory = base / 'offline-prepared-1/task'
    runtime = save(root / 'runtime.json', {'fixture': True})
    selected_operation, selected_seconds = bridge.PROFILES[profile]
    core_value = dict(status='PASS_GO', findings=[])
    if profile == 'debian-autoboot-v1':
        core_value = dict(schema='s22plus-p999-independent-capability-review-v1',
            verdict='PASS_GO', findings=[], scope='V3_REACHABLE_CAPABILITY',
            candidate='p999', profile=profile, version='fixture-v1')
    core_value.update(core_changes or {})
    core = save(base / 'review/core.json', core_value)
    public = save(base / 'public-review.json', dict(schema='s22plus-native-session-v3-review',
        verdict='PASS_GO', scope='V3_REACHABLE_CAPABILITY', findings=[], sources=[runtime],
        reviewer=dict(review=core if public_core is None else public_core),
        runtime_sources={'runtime.json': {k: v for k, v in runtime.items() if k != 'path'}}))
    task = save(directory / 'task.json', dict(N=dict(namespace='p999',
        profile=profile, version='fixture-v1'), E=None,
        operations=[operation if operation is not None else selected_operation],
        seconds=seconds if seconds is not None else selected_seconds, operation_budget=1,
        recovery_mode='attended', review=public, runtime_scope=records.read(Path(public['path']))['runtime_sources'],
        target={'fixture': 's22plus'}, A={'fixture': 'original-a'}))
    approval = f"APPROVE S22PLUS NATIVE V3 {task['sha256']} {seconds if seconds is not None else selected_seconds}s 1operations attended"
    proposal = save(directory / 'proposal.json', dict(task=task, approval=approval))
    snapshot = save(base / 'snapshot.json', {'fixture': True})
    prepared = save(base / 'prepared-validation.json', dict(status='READY_H0_PRELIVE_ONLY',
        task=task, proposal=proposal, source_snapshot=snapshot, review=public))
    entry_path = base / 'run-approved-p999.py'
    entry_path.write_text(entry or "from pathlib import Path\nimport os,time\np=Path(__file__).parent\n(p/'marker').write_text(str(os.getsid(0)))\nprint('fixture started',flush=True)\ntime.sleep(0.15)\nprint('fixture done',flush=True)\n")
    entry_pin = records.pin(entry_path)
    previous_task = save(base / 'previous/task.json', {'target': {'fixture': 's22plus'}, 'A': {'fixture': 'original-a'}})
    previous = save(base / 'previous/closed.json', dict(task=previous_task, terminal_state='ANDROID_CLOSED_HEALTHY'))
    save(base / 'review/prepared-entry-review.json', dict(schema='s22plus-p999-independent-prepared-entry-review-v1',
        status='PASS_READY_H0_AND_UNEXECUTED_ENTRY', findings=[], entry_once_guards=bridge.GUARDS,
        approved_binding_preserved=True, prepared=prepared, task=task, proposal=proposal,
        entry=entry_pin, source_snapshot=snapshot, public_binding=public, capability_review=core,
        actual_preceding_closed=previous))
    save(base / 'operator-approval.json', dict(task=task, entry=entry_pin, preceding_closed=previous,
        selected_returned_approval=approval, actual_user_text='fixture only'))
    return base


class TerminalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = fixture(self.root)
        self.controller = bridge.Controller(self.root, bridge_check=lambda root: {'fixture': True})
        self.owner = mock.patch.object(bridge.registry, 'require_no_f1_owner')
        self.owner.start()

    def tearDown(self):
        # All launched fixture processes finish before deleting their evidence.
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            running = [p for p in self.root.glob('workspace/private/outputs/*/' + bridge.DISPATCH + '/spawned.json')
                if not (p.parent / 'result.json').exists() and bridge.process_alive(records.read(p)['process'])]
            if not running:
                break
            time.sleep(0.02)
        self.owner.stop()
        self.temp.cleanup()

    def wait_result(self, base=None):
        base = base or self.base
        path = base / bridge.DISPATCH / 'result.json'
        deadline = time.monotonic() + 3
        while not path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(path.exists())
        return records.read(path)

    def close_fixture(self, base=None):
        base = base or self.base
        task = records.pin(base / 'offline-prepared-1/task/task.json')
        terminal = save(base / 'terminal-fixture.json', dict(terminal_state='ANDROID_CLOSED_HEALTHY', research_closed=True))
        save(Path(task['path']).parent / 'closed.json', dict(task=task, terminal_state='ANDROID_CLOSED_HEALTHY', current_android_terminal=terminal))

    def rejected_before_intent(self):
        with self.assertRaises((ValueError, OSError, KeyError)):
            self.controller.start(str(self.base))
        self.assertFalse((self.base / bridge.DISPATCH / 'intent.json').exists())
        self.assertFalse((self.base / 'marker').exists())

    def test_real_dispatch_and_separate_session(self):
        result = self.controller.start(str(self.base))
        self.assertTrue(result['dispatched'])
        self.assertEqual(self.wait_result()['returncode'], 0)
        spawned = records.read(self.base / bridge.DISPATCH / 'spawned.json')
        self.assertEqual(int((self.base / 'marker').read_text()), spawned['process']['pid'])
        self.assertIn('fixture done', self.controller.log(str(self.base))['text'])

    def test_autoboot_actual_socket_dispatch_and_no_replay(self):
        base = fixture(self.root, 2, profile='debian-autoboot-v1')
        endpoint = self.root / 'autoboot.sock'
        with bridge.Server(str(endpoint), bridge.Handler) as server:
            endpoint.chmod(0o600); server.controller = self.controller
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                args = dict(preparation_directory=str(base))
                response = bridge.forward('start_approved_task', args, endpoint=endpoint)
                self.assertTrue(response['ok'])
                started = response['value']
                self.assertTrue(started['dispatched'])
                self.assertEqual(started['operation'], 'debian-autoboot')
                repeated = bridge.forward('start_approved_task', args, endpoint=endpoint)
                self.assertTrue(repeated['ok'])
                self.assertFalse(repeated['value']['dispatched'])
            finally:
                server.shutdown(); thread.join()
        self.assertEqual(self.wait_result(base)['returncode'], 0)
        self.assertTrue((base / 'marker').exists())

    def test_fixed_profile_operation_and_duration_pairs(self):
        cases = [
            ('debian-autoboot-v1', 'debian-autoboot', 1800),
            ('debian-autoboot-v1', 'root-evidence', 3600),
            ('thermal-v3-reconnect-ufs-drain-root-evidence-v1', 'root-evidence', 3600),
            ('thermal-v3-reconnect-ufs-drain-journal-recovery-v1', 'journal-recovery', 3600),
        ]
        for index, (profile, operation, seconds) in enumerate(cases, 10):
            with self.subTest(profile=profile, operation=operation, seconds=seconds):
                base = fixture(self.root, index, profile=profile, operation=operation, seconds=seconds)
                with self.assertRaisesRegex(ValueError, 'unsupported approved task scope'):
                    self.controller.start(str(base))
                self.assertFalse((base / bridge.DISPATCH).exists())

    def test_autoboot_core_identity_and_verdict_are_required(self):
        changes = [dict(schema='wrong'), dict(candidate='p998'), dict(profile='wrong'),
            dict(version='other'), dict(scope='OTHER'), dict(verdict='NO_GO'),
            dict(verdict=None, status='PASS_GO'), dict(findings=['unresolved'])]
        for index, changed in enumerate(changes, 20):
            with self.subTest(changed=changed):
                base = fixture(self.root, index, profile='debian-autoboot-v1', core_changes=changed)
                with self.assertRaisesRegex(ValueError, 'autoboot core review differs'):
                    self.controller.start(str(base))
                self.assertFalse((base / bridge.DISPATCH).exists())

    def test_journal_recovery_retains_its_original_scope(self):
        base = fixture(self.root, 2, profile='thermal-v3-reconnect-ufs-drain-journal-recovery-v1')
        self.assertEqual(self.controller.bundle(str(base), current=True, approval=True)['operation'], 'journal-recovery')

    def test_autoboot_public_review_must_reference_exact_core(self):
        other = save(self.root / 'other-core.json', dict(verdict='PASS_GO', findings=[]))
        base = fixture(self.root, 2, profile='debian-autoboot-v1', public_core=other)
        with self.assertRaisesRegex(ValueError, 'autoboot core review differs'):
            self.controller.start(str(base))
        self.assertFalse((base / bridge.DISPATCH).exists())

    def test_status_exposes_loaded_review_without_dispatch(self):
        value = self.controller.call('bridge_status', {})
        self.assertEqual(value['bridge_review'], self.controller.bridge_identity)
        self.assertFalse(value['device_authority'])
        self.assertFalse((self.base / bridge.DISPATCH).exists())

    def test_concurrent_and_repeated_requests_execute_once(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: self.controller.start(str(self.base)), range(6)))
        self.assertEqual(sum(r['dispatched'] for r in results), 1)
        self.wait_result()
        restarted = bridge.Controller(self.root, bridge_check=lambda root: {'fixture': True})
        self.assertFalse(restarted.start(str(self.base))['dispatched'])

    def test_another_task_blocked_during_child_lifetime(self):
        other = fixture(self.root, 2)
        self.controller.start(str(self.base))
        with self.assertRaisesRegex(ValueError, 'another dispatch'):
            self.controller.start(str(other))
        self.wait_result()
        with self.assertRaisesRegex(ValueError, 'another dispatch'):
            self.controller.start(str(other))
        self.close_fixture()
        self.assertTrue(self.controller.start(str(other))['dispatched'])
        self.wait_result(other)

    def test_failed_entry_exit_without_owner_closure_blocks_next_task(self):
        base = fixture(self.root, 2, entry='raise SystemExit(7)\n')
        self.controller.start(str(base))
        self.assertEqual(self.wait_result(base)['returncode'], 7)
        with self.assertRaisesRegex(ValueError, 'another dispatch'):
            self.controller.start(str(self.base))

    def test_intent_and_directory_are_synced_before_spawn(self):
        synced = []
        real_sync, real_popen = records.sync_dir, subprocess.Popen
        def sync(path):
            synced.append(Path(path)); return real_sync(path)
        def popen(*args, **kwargs):
            self.assertIn(self.base, synced)
            self.assertIn(self.base / bridge.DISPATCH, synced)
            self.assertTrue((self.base / bridge.DISPATCH / 'intent.json').exists())
            self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
            self.assertTrue(kwargs['start_new_session'])
            return real_popen(*args, **kwargs)
        with mock.patch.object(records, 'sync_dir', sync), mock.patch.object(bridge.subprocess, 'Popen', popen):
            self.controller.start(str(self.base)); self.wait_result()

    def test_missing_and_wrong_approval_block(self):
        approval = self.base / 'operator-approval.json'
        value = records.read(approval)
        approval.unlink(); self.rejected_before_intent()
        value['selected_returned_approval'] = 'wrong'
        save(approval, value); self.rejected_before_intent()
        value['selected_returned_approval'] = records.read(self.base / 'offline-prepared-1/task/proposal.json')['approval']; value['actual_user_text'] = ' '
        save(approval, value); self.rejected_before_intent()

    def test_changed_entry_review_or_sources_block(self):
        for relative in ['run-approved-p999.py', 'prepared-validation.json', 'public-review.json',
                         'snapshot.json', 'previous/closed.json']:
            path = self.base / relative; before = path.read_bytes()
            path.write_bytes(before + b' '); self.rejected_before_intent(); path.write_bytes(before)
        (self.root / 'runtime.json').write_text('{"changed":true}')
        self.rejected_before_intent()

    def test_changed_bridge_review_blocks(self):
        self.controller.bridge_check = lambda root: bridge.require(False, 'changed bridge')
        self.rejected_before_intent()

    def test_new_review_requires_restarting_loaded_worker(self):
        self.controller.bridge_check = lambda root: {'fixture': 'new review'}
        self.rejected_before_intent()

    def test_existing_attempts_block(self):
        directory = self.base / 'offline-prepared-1/task'
        for path in [directory / 'grant.json', directory / 'operation-0001',
                     directory / 'grant-host-preflight', self.base / 'execute-1.log']:
            path.touch(); self.rejected_before_intent(); path.unlink()

    def test_existing_global_owner_blocks(self):
        with mock.patch.object(bridge.registry, 'require_no_f1_owner', side_effect=ValueError('owned')):
            self.rejected_before_intent()

    def test_no_replay_after_launch_error_or_uncertainty(self):
        with mock.patch.object(bridge.subprocess, 'Popen', side_effect=OSError('fixture failure')):
            with self.assertRaises(OSError): self.controller.start(str(self.base))
        self.assertEqual(self.controller.dispatch_state(self.base)['state'], 'SPAWN_ERROR')
        self.assertFalse(self.controller.start(str(self.base))['dispatched'])
        (self.base / bridge.DISPATCH / 'result.json').unlink()  # Model a crash before result publication.
        self.assertEqual(self.controller.dispatch_state(self.base)['state'], 'DISPATCH_UNCERTAIN')
        self.assertFalse(self.controller.start(str(self.base))['dispatched'])
        other = fixture(self.root, 2)
        with self.assertRaisesRegex(ValueError, 'another dispatch'):
            self.controller.start(str(other))

    def test_restart_uses_pid_start_identity_and_closed_owner(self):
        self.controller.start(str(self.base)); self.wait_result()
        folder = self.base / bridge.DISPATCH
        (folder / 'result.json').unlink()
        self.assertEqual(self.controller.dispatch_state(self.base)['state'], 'DISPATCH_UNCERTAIN')
        self.close_fixture()
        self.assertEqual(self.controller.dispatch_state(self.base)['state'], 'CLOSED_BY_ORIGINAL_OWNER')
        self.assertFalse(self.controller.start(str(self.base))['dispatched'])

    def test_invalid_paths_arguments_and_bounded_logs(self):
        alias = self.root / 'workspace/private/outputs/s22plus-alias-h0-20261023-1'
        alias.symlink_to(self.base)
        for name in [str(alias), str(self.root), str(self.base) + '/..', 'relative']:
            with self.assertRaises((ValueError, OSError)): self.controller.status(name)
        with self.assertRaises(ValueError): self.controller.call('start_approved_task', {'preparation_directory': str(self.base), 'command': 'anything'})
        self.controller.start(str(self.base)); self.wait_result()
        self.assertEqual(self.controller.log(str(self.base), count=8)['returned_bytes'], 8)
        for count in [0, bridge.MAX_LOG + 1, True]:
            with self.assertRaises(ValueError): self.controller.log(str(self.base), count=count)

    def test_worker_uid_and_nnp_guards_before_review(self):
        for uid, euid, nnp in [(0, 0, 0), (1000, 0, 0), (1000, 1000, 1)]:
            with mock.patch.object(os, 'getuid', return_value=uid), mock.patch.object(os, 'geteuid', return_value=euid), \
                    mock.patch.object(bridge, 'nnp', return_value=nnp), mock.patch.object(bridge, 'verify_bridge') as review:
                with self.assertRaises(ValueError): bridge.serve()
                review.assert_not_called()

    def test_fifo_and_symlink_logs_are_rejected_before_open(self):
        path = self.base / 'execute-1.log'
        os.mkfifo(path)
        with mock.patch.object(bridge.os, 'open', wraps=os.open) as opened:
            with self.assertRaisesRegex(ValueError, 'invalid log path'):
                self.controller.log(str(self.base), stream='execution')
            self.assertFalse(any(call.args[0] == path for call in opened.call_args_list))
        path.unlink()
        path.symlink_to(self.base / 'run-approved-p999.py')
        with self.assertRaisesRegex(ValueError, 'indirect log'):
            self.controller.log(str(self.base), stream='execution')

    def test_actual_nnp_startup_refusal(self):
        script = 'import ctypes,os; assert ctypes.CDLL(None).prctl(38,1,0,0,0)==0; os.execv("/usr/bin/python3",["/usr/bin/python3",' + repr(str(SOURCE)) + ',"serve"])'
        result = subprocess.run(['/usr/bin/python3', '-c', script], capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('NoNewPrivs must be 0', result.stderr)

    def test_real_socket_mcp_framing_and_disconnect(self):
        endpoint = self.root / 'bridge.sock'
        with bridge.Server(str(endpoint), bridge.Handler) as server:
            endpoint.chmod(0o600); server.controller = self.controller
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                transport = lambda name, args: bridge.forward(name, args, endpoint=endpoint)
                requests = [dict(jsonrpc='2.0', id=0, method='server/discover'),
                    dict(jsonrpc='2.0', id=1, method='initialize', params=dict(protocolVersion='2025-11-25', capabilities={}, clientInfo={'name': 'fixture', 'version': '1'})),
                    dict(jsonrpc='2.0', method='notifications/initialized'),
                    dict(jsonrpc='2.0', id=2, method='tools/list'),
                    dict(jsonrpc='2.0', id=3, method='tools/call', params=dict(name='start_approved_task', arguments={'preparation_directory': str(self.base)}))]
                output = io.BytesIO()
                bridge.mcp(io.BytesIO(b''.join(records.canonical(r) for r in requests)), output, transport=transport)
                responses = [json.loads(line) for line in output.getvalue().splitlines()]
                self.assertEqual(responses[0]['error']['code'], -32601)
                self.assertEqual({row['name'] for row in responses[2]['result']['tools']},
                    {'bridge_status', 'task_status', 'task_log', 'start_approved_task',
                     'continue_approved_task', 'resume_approved_health'})
                self.assertFalse(responses[3]['result']['isError'])
            finally:
                server.shutdown(); thread.join()
        self.assertEqual(self.wait_result()['returncode'], 0)
        with self.assertRaises(OSError): bridge.forward('bridge_status', {}, endpoint=endpoint)

    def test_actual_stdio_cli_tools_and_unavailable_worker(self):
        requests = [dict(jsonrpc='2.0', id=1, method='initialize', params=dict(protocolVersion='2025-11-25', capabilities={}, clientInfo={})),
            dict(jsonrpc='2.0', method='notifications/initialized'), dict(jsonrpc='2.0', id=2, method='tools/list')]
        result = subprocess.run(['/usr/bin/python3', str(SOURCE), 'mcp'], input=b''.join(records.canonical(r) for r in requests), capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertEqual({row['name'] for row in json.loads(result.stdout.splitlines()[1])['result']['tools']},
            {'bridge_status', 'task_status', 'task_log', 'start_approved_task',
             'continue_approved_task', 'resume_approved_health'})
        self.assertFalse(result.stderr)
        output = io.BytesIO()
        request = dict(jsonrpc='2.0', id=3, method='tools/call', params=dict(name='bridge_status', arguments={}))
        def unavailable(*args): raise FileNotFoundError('fixture offline')
        bridge.mcp(io.BytesIO(b''.join(records.canonical(r) for r in requests + [request])), output, transport=unavailable)
        self.assertTrue(json.loads(output.getvalue().splitlines()[-1])['result']['isError'])

    def test_worker_process_death_does_not_kill_or_replay_child(self):
        script = (
            'import importlib.util,os\n'
            f's=importlib.util.spec_from_file_location("bridge",{str(SOURCE)!r})\n'
            'm=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n'
            'm.registry.require_no_f1_owner=lambda root:None\n'
            f'c=m.Controller({str(self.root)!r},bridge_check=lambda root:{{"fixture":True}})\n'
            f'c.start({str(self.base)!r})\n'
            'os._exit(0)\n')
        result = subprocess.run(['/usr/bin/python3', '-c', script], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and 'fixture done' not in self.controller.log(str(self.base))['text']:
            time.sleep(0.02)
        self.assertIn('fixture done', self.controller.log(str(self.base))['text'])
        self.assertFalse((self.base / bridge.DISPATCH / 'result.json').exists())
        self.assertFalse(self.controller.start(str(self.base))['dispatched'])


class ContinuationTests(unittest.TestCase):
    """Real immutable grants/journals/owner/lease, harmless fixed CLI fixture."""
    def setUp(self):
        from s22plus_native_adapter_v3 import Adapter
        from s22plus_debian_autoboot_session_v1 import normal_steps
        self.temp = tempfile.TemporaryDirectory(prefix='s22t-', dir='/tmp')
        self.root = Path(self.temp.name)
        self.base = fixture(self.root, profile='debian-autoboot-v1')
        self.controller = bridge.Controller(self.root, bridge_check=lambda root: {'fixture': True})
        self.controller.start(str(self.base))
        self.wait_phase(bridge.DISPATCH)
        self.directory = self.base / 'offline-prepared-1/task'
        self.operation = self.directory / 'operation-0001'; self.operation.mkdir(mode=0o700)
        self.task = records.pin(self.directory / 'task.json')
        task = records.read(self.directory / 'task.json')
        now = records.clock()
        self.grant = save(self.directory / 'grant.json', dict(schema=records.SCHEMA,
            task=self.task, directory=str(self.directory), host_boot=records.host_boot(),
            opened_ns=now-1_000_000_000, deadline_ns=now-1_000_000_000+3600_000_000_000,
            operation_budget=1, recovery_mode='attended', operator_statement='fixture attended',
            returned_approval=records.read(self.directory / 'proposal.json')['approval']))
        self.request = dict(schema=records.SCHEMA, operation='debian-autoboot', task=self.task,
            grant=self.grant, N=task['N'], A=task['A'], E=None, reentry=False, hud=False,
            usb_reconnect=False, admission=None, prior_terminal=None)
        self.op_pin = save(self.operation / 'operation.json', self.request)
        save(self.operation / 'consumed.json', dict(schema=records.SCHEMA,
            operation_sha256=self.op_pin['sha256'], grant=self.grant))
        self.journal = records.Journal(self.operation / 'journal')
        for step in normal_steps()[:4]:
            proof = save(self.operation / (step.name+'.json'), dict(action=step.action, role=step.role))
            self.journal.append('step-start', step=step.name, action=step.action, role=step.role)
            if step.action != 'debian-health':
                self.journal.append('effect-intent', step=step.name, action=step.action, role=step.role)
            self.journal.append('step-complete', step=step.name, result=proof)
        save(self.operation / 'debian-return-ready.json', dict(operation=self.op_pin,
            shutdown=records.pin(self.operation / 'debian-shutdown.json'),
            requested_ns=now, deadline_ns=now+600_000_000_000))
        bridge.registry.initialize(self.root)
        bridge.registry.begin_f1_owner(self.root, self.operation, self.op_pin['sha256'])
        cli = self.root / 'workspace/public/src/scripts/revalidation/s22plus_native_task_v3.py'
        cli.parent.mkdir(parents=True)
        cli.write_text("import sys,time\nfrom pathlib import Path\nassert len(sys.argv)==6\nassert sys.argv[1]=='--root' and sys.argv[5]=='--attended'\nassert sys.argv[3] in ('continue','recover')\np=Path(sys.argv[4])\nwith (p/('fixture-'+sys.argv[3])).open('x') as f:f.write('once')\nprint('fixture '+sys.argv[3],flush=True)\ntime.sleep(0.05)\n")
        # Only device/profile consumers are fixtures; original record, grant,
        # clock, global owner and session lease validation run unmodified.
        self.check = mock.patch.object(Adapter, 'check'); self.check.start()
        self.results = mock.patch.object(Adapter, 'validate_result', side_effect=
            lambda step,value,request: bridge.require(value == dict(action=step.action,role=step.role), 'fixture raw mismatch'))
        self.results.start()
        self.raw = mock.patch.object(Adapter, 'recover_transfer_result', return_value=
            dict(action='transfer', role='A', completed=True, raw='fixture-only'))
        self.raw_mock = self.raw.start()

    def tearDown(self):
        for phase, _ in bridge.CONTINUATIONS.values():
            path = self.base / phase / 'spawned.json'
            if path.exists() and not (path.parent / 'result.json').exists():
                self.wait_phase(phase)
        self.raw.stop(); self.results.stop(); self.check.stop(); self.temp.cleanup()

    def wait_phase(self, phase):
        result = self.base / phase / 'result.json'
        deadline = time.monotonic()+3
        while not result.exists() and time.monotonic()<deadline: time.sleep(0.01)
        self.assertTrue(result.exists())
        return records.read(result)

    def call(self, tool='continue_approved_task'):
        return self.controller.call(tool, dict(preparation_directory=str(self.base)))

    def reject(self, tool='continue_approved_task'):
        with mock.patch.object(bridge.subprocess, 'Popen', side_effect=AssertionError('no process permitted')) as spawn:
            with self.assertRaises((ValueError, OSError, KeyError, bridge.registry.RegistryError)):
                self.call(tool)
            spawn.assert_not_called()
        self.assertFalse((self.base / bridge.CONTINUATIONS[tool][0] / 'intent.json').exists())

    def android_complete(self):
        self.journal.append('step-start', step='install-android', action='transfer', role='A')
        self.journal.append('effect-intent', step='install-android', action='transfer', role='A')
        self.journal.append('stopped', error_type='fixture_adb_read_failure')

    def test_real_socket_continue_is_once_and_preserves_original_records(self):
        protected = {p:p.read_bytes() for p in self.directory.rglob('*.json')}
        endpoint = self.root/'resume.sock'
        with bridge.Server(str(endpoint), bridge.Handler) as server:
            endpoint.chmod(0o600); server.controller=self.controller
            thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
            try:
                args={'preparation_directory':str(self.base)}
                result=bridge.forward('continue_approved_task',args,endpoint=endpoint)
                self.assertTrue(result['ok']); self.assertTrue(result['value']['dispatched'])
                self.assertFalse(bridge.forward('continue_approved_task',args,endpoint=endpoint)['value']['dispatched'])
            finally: server.shutdown(); thread.join()
        self.assertEqual(self.wait_phase(bridge.CONTINUATIONS['continue_approved_task'][0])['returncode'],0)
        self.assertTrue((self.operation/'fixture-continue').exists())
        self.assertIn('fixture continue',self.controller.log(str(self.base),'continuation')['text'])
        for p,data in protected.items(): self.assertEqual(p.read_bytes(),data)

    def test_health_only_after_raw_proved_android_and_preserves_expired_grant(self):
        self.reject('resume_approved_health')
        self.android_complete()
        # Grant expiry does not renew it or change original-A recovery semantics.
        with mock.patch.object(records, 'clock', return_value=records.read(Path(self.grant['path']))['deadline_ns']+1):
            self.assertTrue(self.call('resume_approved_health')['dispatched'])
        self.assertEqual(self.wait_phase(bridge.CONTINUATIONS['resume_approved_health'][0])['returncode'],0)
        self.raw_mock.assert_called()
        self.assertEqual(records.pin(Path(self.grant['path'])),self.grant)
        self.assertTrue((self.operation/'fixture-recover').exists())
        self.assertFalse((self.operation/'fixture-continue').exists())
        self.assertFalse(self.call('resume_approved_health')['dispatched'])

    def test_uncertain_android_raw_never_dispatches_recover(self):
        self.android_complete()
        self.raw_mock.side_effect=ValueError('uncertain transfer')
        self.reject('resume_approved_health')

    def test_stopped_or_prior_return_never_dispatches_continue(self):
        self.android_complete(); self.reject()

    def test_closed_terminal_unused_or_ambiguous_operation_rejected(self):
        for path in (self.directory/'closed.json', self.operation/'terminal.json', self.operation/'unused.json', self.directory/'operation-0002'):
            path.touch(); self.reject(); path.unlink()

    def test_missing_or_wrong_owner_rejected(self):
        owner=self.root/bridge.registry.F1_OWNER; data=owner.read_bytes()
        owner.unlink(); self.reject()
        save(owner,dict(wrong=True)); owner.chmod(0o400); self.reject()
        owner.unlink(); owner.write_bytes(data); owner.chmod(0o400)

    def test_active_original_owner_lease_rejected(self):
        with bridge.registry.target_session_lease(self.root): self.reject()

    def test_unresolved_or_running_entry_rejected(self):
        folder=self.base/bridge.DISPATCH; path=folder/'result.json'; before=path.read_bytes()
        path.unlink(); self.reject(); path.write_bytes(before)
        with mock.patch.object(bridge,'process_alive',return_value=True): self.reject()

    def test_wrong_host_epoch_and_expired_return_request_rejected(self):
        with mock.patch.object(records,'host_boot',return_value='different-host'): self.reject()
        import s22plus_native_session_v3 as native_session
        ready=records.read(self.operation/'debian-return-ready.json')
        with mock.patch.object(records,'clock',return_value=ready['deadline_ns']), \
                mock.patch.object(native_session,'clock',return_value=ready['deadline_ns']): self.reject()

    def test_wrong_ready_pin_missing_prefix_and_changed_approval_rejected(self):
        for path in (self.operation/'debian-shutdown.json', self.operation/'debian-health.json', self.base/'operator-approval.json'):
            before=path.read_bytes(); path.write_bytes(before+b' '); self.reject(); path.write_bytes(before)
        path=self.operation/'debian-return-ready.json'; before=path.read_bytes()
        value=records.read(path); value['operation']=self.task; save(path,value); self.reject(); path.write_bytes(before)

    def test_changed_source_and_review_rejected(self):
        path=self.root/'runtime.json'; before=path.read_bytes()
        path.write_bytes(before+b' '); self.reject(); path.write_bytes(before)
        self.controller.bridge_check=lambda root:{'different':True}; self.reject()

    def test_concurrent_continuations_dispatch_once(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:self.call(),range(4)))
        self.assertEqual(sum(row['dispatched'] for row in results),1)
        self.wait_phase(bridge.CONTINUATIONS['continue_approved_task'][0])

    def test_continuation_spawn_error_is_consumed_after_restart(self):
        with mock.patch.object(bridge.subprocess,'Popen',side_effect=OSError('fixture spawn failure')):
            with self.assertRaises(OSError):self.call()
        restarted=bridge.Controller(self.root,bridge_check=lambda root:{'fixture':True})
        self.assertFalse(restarted.call('continue_approved_task',dict(preparation_directory=str(self.base)))['dispatched'])
        (self.base/bridge.CONTINUATIONS['continue_approved_task'][0]/'result.json').unlink()
        self.assertFalse(self.call()['dispatched'])

    def test_prior_continuation_must_finish_before_health_resume(self):
        self.call(); self.wait_phase(bridge.CONTINUATIONS['continue_approved_task'][0])
        self.android_complete()
        path=self.base/bridge.CONTINUATIONS['continue_approved_task'][0]/'result.json'
        data=path.read_bytes(); path.unlink(); self.reject('resume_approved_health'); path.write_bytes(data)
        self.assertTrue(self.call('resume_approved_health')['dispatched'])
        self.wait_phase(bridge.CONTINUATIONS['resume_approved_health'][0])

    def test_schema_exposes_no_command_or_approval_override(self):
        definitions={row['name']:row for row in bridge.tools()}
        for tool in bridge.CONTINUATIONS:
            schema=definitions[tool]['inputSchema']
            self.assertEqual(set(schema['properties']),{'preparation_directory'})
            self.assertFalse(schema['additionalProperties'])
            self.assertFalse(definitions[tool]['annotations']['readOnlyHint'])
            with self.assertRaises(ValueError):
                self.controller.call(tool,dict(preparation_directory=str(self.base),command='anything'))


if __name__ == '__main__':
    unittest.main()
