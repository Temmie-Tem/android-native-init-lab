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


def fixture(root, ordinal=1, entry=None):
    base = root / f'workspace/private/outputs/s22plus-fixture-h0-20261023-{ordinal}'
    directory = base / 'offline-prepared-1/task'
    runtime = save(root / 'runtime.json', {'fixture': True})
    public = save(base / 'public-review.json', dict(schema='s22plus-native-session-v3-review',
        verdict='PASS_GO', scope='V3_REACHABLE_CAPABILITY', findings=[], sources=[runtime],
        runtime_sources={'runtime.json': {k: v for k, v in runtime.items() if k != 'path'}}))
    task = save(directory / 'task.json', dict(N=dict(namespace='p999',
        profile='thermal-v3-reconnect-ufs-drain-root-evidence-v1'), E=None,
        operations=['root-evidence'], seconds=1800, operation_budget=1,
        recovery_mode='attended', review=public, runtime_scope=records.read(Path(public['path']))['runtime_sources'],
        target={'fixture': 's22plus'}, A={'fixture': 'original-a'}))
    proposal = save(directory / 'proposal.json', dict(task=task, approval='FIXTURE APPROVAL'))
    snapshot = save(base / 'snapshot.json', {'fixture': True})
    prepared = save(base / 'prepared-validation.json', dict(status='READY_H0_PRELIVE_ONLY',
        task=task, proposal=proposal, source_snapshot=snapshot, review=public))
    entry_path = base / 'run-approved-p999.py'
    entry_path.write_text(entry or "from pathlib import Path\nimport os,time\np=Path(__file__).parent\n(p/'marker').write_text(str(os.getsid(0)))\nprint('fixture started',flush=True)\ntime.sleep(0.15)\nprint('fixture done',flush=True)\n")
    entry_pin = records.pin(entry_path)
    previous_task = save(base / 'previous/task.json', {'target': {'fixture': 's22plus'}, 'A': {'fixture': 'original-a'}})
    previous = save(base / 'previous/closed.json', dict(task=previous_task, terminal_state='ANDROID_CLOSED_HEALTHY'))
    core = save(base / 'review/core.json', dict(status='PASS_GO', findings=[]))
    save(base / 'review/prepared-entry-review.json', dict(schema='s22plus-p999-independent-prepared-entry-review-v1',
        status='PASS_READY_H0_AND_UNEXECUTED_ENTRY', findings=[], entry_once_guards=bridge.GUARDS,
        approved_binding_preserved=True, prepared=prepared, task=task, proposal=proposal,
        entry=entry_pin, source_snapshot=snapshot, public_binding=public, capability_review=core,
        actual_preceding_closed=previous))
    save(base / 'operator-approval.json', dict(task=task, entry=entry_pin, preceding_closed=previous,
        selected_returned_approval='FIXTURE APPROVAL', actual_user_text='fixture only'))
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
        value['selected_returned_approval'] = 'FIXTURE APPROVAL'; value['actual_user_text'] = ' '
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
                self.assertEqual(len(responses[2]['result']['tools']), 4)
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
        self.assertEqual(len(json.loads(result.stdout.splitlines()[1])['result']['tools']), 4)
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


if __name__ == '__main__':
    unittest.main()
