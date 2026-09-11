from __future__ import annotations
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s22plus_goal_research_v1 as m

BOOT1 = '11111111-1111-1111-1111-111111111111'
BOOT2 = '22222222-2222-2222-2222-222222222222'
TARGET = {'serial': 'fixture-device', 'topology': 'usb:1-1'}


class Client:
    def __init__(self, profile):
        self.profile = profile
        self.boot = BOOT1
        self.calls = []
        self.fail_reboot = False
        self.serial = TARGET['serial']

    def bind_raw_capture_dir(self, path):
        self.path = path

    def one_serial(self):
        return self.serial

    def topology(self, serial):
        return TARGET['topology']

    def properties(self, serial):
        return dict(model='SM-S906N', device='g0q', incremental='S906NKSS7FYG8',
                    bootloader='S906NKSS7FYG8', boot_id=self.boot, boot_completed='1',
                    bootanim='stopped', verified_boot_state='orange', kernel_release='fixture')

    def root_health(self, serial):
        expected = self.profile['start_health']
        return dict(root='uid=0(root) gid=0(root)', boot=expected['boot_sha256'],
                    **expected['supporting_partition_sha256'])

    def _shell(self, serial, command, *, root, timeout):
        self.calls.append(('shell', serial, command, root))
        if command == 'getprop sys.boot_completed':
            return '1'
        return 'fixture output'

    def _run(self, arguments, label, timeout=20):
        self.calls.append(tuple(arguments))
        if arguments[-1] == 'reboot':
            if self.fail_reboot:
                raise m.d0.D0Error('uncertain dispatch')
            self.boot = BOOT2
            return ''
        return 'List of devices attached\nfixture-device device model:SM_S906N device:g0q\n'


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in m.SOURCES.values():
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        (self.root / 'workspace/private').mkdir(parents=True)
        m.registry.initialize(self.root)
        review = self.root / m.REVIEW
        review.parent.mkdir(parents=True, exist_ok=True)
        m.publish(review, dict(verdict='PASS_GO', sources=m.source_identity(self.root), actions=sorted(m.ACTIONS)))
        self.target = self.root / 'workspace/private/target.json'
        m.publish(self.target, TARGET)
        self.grant = m.open_goal(self.root, 'explicit fixture research goal', self.target, sorted(m.ACTIONS))
        self.profile = m.read(self.root / m.PROFILE)
        self.client = Client(self.profile)
        p = patch.object(m.d0, 'usb_snapshot', return_value={'download_endpoint_count': 0})
        p.start()
        self.addCleanup(p.stop)

    def execute(self, action, attended=False):
        return m.execute(self.root, self.grant, action, attended=attended, client_factory=lambda: self.client)

    def pending(self):
        return self.root / m.registry.RESEARCH_PENDING

    def test_named_root_read_is_bound_and_does_not_dispatch_control(self):
        self.assertEqual(self.execute('memory')['verdict'], 'PASS')
        self.assertEqual(self.client.calls, [('shell', TARGET['serial'], m.READS['memory'][0], True)])
        self.assertFalse(self.pending().exists())

    def test_status_hud_is_one_fixed_read_without_control(self):
        self.assertEqual(self.execute('status-hud')['verdict'], 'PASS')
        self.assertEqual(self.client.calls,
            [('shell', TARGET['serial'], m.STATUS_HUD_READ, True)])
        self.assertFalse(self.pending().exists())
        self.assertNotIn('uevent', m.STATUS_HUD_READ)
        self.assertNotIn('thermal_zone', m.STATUS_HUD_READ)

    def test_status_hud_shell_retains_missing_fields_and_two_cpu_samples(self):
        import subprocess
        fixture = self.root / 'status-fixture'
        fixture.mkdir()
        files = {'/proc/meminfo': 'MemTotal: 8192 kB\nMemAvailable: 4096 kB\n',
                 '/proc/stat': 'cpu 10 0 4 80 1 0 0 0 0 0\nintr 123\n',
                 '/sys/class/power_supply/battery/type': 'Battery\n',
                 '/sys/class/power_supply/battery/capacity': '73\n',
                 '/sys/class/power_supply/battery/status': 'Charging\n',
                 '/sys/class/power_supply/battery/temp': None}
        command = m.STATUS_HUD_READ
        for index, (path, value) in enumerate(files.items()):
            destination = fixture / str(index)
            if value is not None:
                destination.write_text(value)
            command = command.replace(path, str(destination))
        result = subprocess.run(['/bin/sh', '-c', command],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('cpu 10 0 4 80 1 0 0 0 0 0'), 2)
        self.assertNotIn('intr 123', result.stdout)
        self.assertEqual(result.stdout.count('UNAVAILABLE'), 1)
        self.assertTrue(result.stdout.endswith('STATUS_HUD_V1_END\n'))

    def test_unknown_action_and_missing_attendance_fail_before_client(self):
        for action in ('su -c reboot', 'normal-reboot'):
            with self.assertRaises(m.ResearchError):
                self.execute(action)
        self.assertEqual(self.client.calls, [])

    def test_source_change_invalidates_goal_before_connected_action(self):
        with (self.root / m.SOURCES['runner']).open('a') as f:
            f.write('\n# drift\n')
        with self.assertRaises(m.ResearchError):
            self.execute('memory')
        self.assertEqual(self.client.calls, [])

    def test_wrong_target_never_receives_root_command(self):
        self.client.serial = 'other-target'
        with self.assertRaises(m.ResearchError):
            self.execute('memory')
        self.assertFalse(self.client.calls)
        self.assertTrue((self.grant.parent / 'closed.json').exists())

    def test_d0_boot_drift_closes_goal(self):
        original = self.client._shell
        def changed(*args, **kwargs):
            self.client.boot = BOOT2
            return original(*args, **kwargs)
        self.client._shell = changed
        with self.assertRaises(m.ResearchError):
            self.execute('memory')

    def test_normal_reboot_one_dispatch_real_health_validation_and_intent(self):
        result = self.execute('normal-reboot', attended=True)
        self.assertEqual(result['verdict'], 'PASS')
        self.assertEqual(self.client.calls.count(('-s', TARGET['serial'], 'reboot')), 1)
        run = Path(result['run'])
        self.assertTrue((run / 'intent.json').exists())
        self.assertEqual(m.read(run / 'result.json')['after']['properties']['boot_id'], BOOT2)
        self.assertFalse(self.pending().exists())

    def test_online_early_boot_readiness_through_real_adb_raw_consumer(self):
        # The full properties response is invalid until the third readiness
        # poll. This reproduces the observed successful-but-empty early boot
        # property without relaxing the ordinary properties parser.
        executable = self.root / 'fixture-adb'
        counter = self.root / 'readiness-count'
        props = self.client.properties(TARGET['serial'])
        props['boot_id'] = BOOT2
        health = self.client.root_health(TARGET['serial'])
        executable.write_text(f'''#!{sys.executable}
import sys
from pathlib import Path
args=sys.argv[1:];joined=' '.join(args);counter=Path({str(counter)!r})
count=int(counter.read_text()) if counter.exists() else 0
if args==['devices','-l']:print('List of devices attached\\nfixture-device device model:SM_S906N device:g0q')
elif args[-1:]==['get-devpath']:print('usb:1-1')
elif 'getprop sys.boot_completed' in joined and 'getprop ro.product.model' not in joined:
 count+=1;counter.write_text(str(count));print(['','0','1'][min(count-1,2)])
elif 'getprop ro.product.model' in joined:
 props={props!r};props['boot_completed']='1' if count>=3 else ''
 print(''.join(k+'='+v+'\\n' for k,v in props.items()),end='')
elif 'sha256sum /dev/block/by-name/boot' in joined:print({''.join(k+'='+v+chr(10) for k,v in health.items())!r},end='')
else:raise SystemExit(2)
''')
        executable.chmod(0o700)
        client = m.d0.AdbReadOnlyClient(executable, expected_model='SM-S906N', expected_device='g0q')
        run = self.root / 'return-raw'; run.mkdir(); client.bind_raw_capture_dir(run)
        result = m.wait_return(client, TARGET, self.profile, BOOT1, sleep=lambda _seconds:None)
        self.assertEqual(result['properties']['boot_id'], BOOT2)
        self.assertTrue(result['health']['root_verified'])
        self.assertEqual(counter.read_text(), '3')
        outputs = []
        for path in sorted((run/'raw-adb').glob('*.capture.json')):
            handle = m.d0.raw_capture.load_handle(path)
            outputs.append(m.d0.raw_capture.decode_success_stdout(handle, maximum=m.d0.MAX_TEXT_OUTPUT))
        self.assertEqual([value for value in outputs if value in {'','0','1'}], ['', '0', '1'])
        self.assertEqual(sum('boot_completed=1' in value for value in outputs), 2)

    def test_unready_online_boot_keeps_original_deadline_without_health(self):
        now = [0]
        def sleep(seconds): now[0] += seconds
        with patch.object(m, 'RETURN_SECONDS', 2), \
                patch.object(self.client, '_shell', return_value=''), \
                patch.object(self.client, 'properties', side_effect=AssertionError('premature health')) as props:
            with self.assertRaisesRegex(m.ResearchError, 'bounded reboot return unproved'):
                m.wait_return(self.client, TARGET, self.profile, BOOT1, clock=lambda:now[0], sleep=sleep)
        props.assert_not_called()
        self.assertEqual(now[0], 2)

    def test_readiness_failure_or_wrong_topology_stops_before_health(self):
        for value in ('unexpected', m.d0.D0Error('readiness transport failed')):
            with self.subTest(value=type(value).__name__), \
                    patch.object(self.client, '_shell', side_effect=value if isinstance(value, Exception) else None,
                                 return_value=value) as ready, \
                    patch.object(self.client, 'properties', side_effect=AssertionError('premature health')) as props:
                with self.assertRaises((m.ResearchError,m.d0.D0Error)):
                    m.wait_return(self.client, TARGET, self.profile, BOOT1)
                self.assertEqual(ready.call_count, 1); props.assert_not_called()
        with patch.object(self.client, 'topology', return_value='usb:9-9'), \
                patch.object(self.client, '_shell') as ready, self.assertRaisesRegex(m.ResearchError, 'target drift'):
            m.wait_return(self.client, TARGET, self.profile, BOOT1)
        ready.assert_not_called()

    def test_uncertain_dispatch_blocks_effects_but_allows_readonly_lock(self):
        self.client.fail_reboot = True
        with self.assertRaises(m.d0.D0Error):
            self.execute('normal-reboot', attended=True)
        self.assertTrue(self.pending().exists())
        with self.assertRaises(m.registry.RegistryError):
            with m.registry.target_session_lease(self.root):
                self.fail('F1/default owner must not enter')
        with m.registry.target_session_lease(self.root, research_read_only=True):
            pass
        with self.assertRaises(m.ResearchError):
            self.execute('normal-reboot', attended=True)
        self.assertEqual(self.client.calls.count(('-s', TARGET['serial'], 'reboot')), 1)

    def test_reconciliation_is_readonly_does_not_upgrade_or_reopen_goal(self):
        self.client.fail_reboot = True
        with self.assertRaises(m.d0.D0Error):
            self.execute('normal-reboot', attended=True)
        self.client.boot = BOOT2
        before = list(self.client.calls)
        result = m.reconcile(self.root, client_factory=lambda: self.client)
        self.assertEqual(result['verdict'], 'LATE_HEALTH_OBSERVED_GOAL_CLOSED')
        self.assertEqual(before, self.client.calls)
        self.assertFalse(self.pending().exists())
        self.assertTrue((self.grant.parent / 'closed.json').exists())

    def test_unchanged_boot_does_not_clear_uncertain_intent(self):
        self.client.fail_reboot = True
        with self.assertRaises(m.d0.D0Error):
            self.execute('normal-reboot', attended=True)
        with self.assertRaises(m.ResearchError):
            m.reconcile(self.root, client_factory=lambda: self.client)
        self.assertTrue(self.pending().exists())

    def test_return_inventory_failure_not_retried(self):
        calls = []
        def broken(*args, **kwargs):
            calls.append(args)
            raise m.d0.D0Error('raw acquisition failure')
        self.client._run = broken
        with self.assertRaises(m.d0.D0Error):
            m.wait_return(self.client, TARGET, self.profile, BOOT1)
        self.assertEqual(len(calls), 1)

    def test_expected_offline_then_exact_changed_boot(self):
        items = iter(['List of devices attached\nfixture-device offline\n',
                      'List of devices attached\nfixture-device device model:SM_S906N device:g0q\n'])
        self.client._run = lambda *args: next(items)
        self.client.boot = BOOT2
        result = m.wait_return(self.client, TARGET, self.profile, BOOT1, sleep=lambda _: None)
        self.assertTrue(result['health']['root_verified'])

    def test_return_deadline_applies_to_individual_commands(self):
        time_values = iter([0, 359, 359.5, 361])
        seen = []
        self.client._run = lambda argv, label, timeout: seen.append(timeout) or 'List of devices attached\n'
        with self.assertRaises(m.ResearchError):
            m.wait_return(self.client, TARGET, self.profile, BOOT1, clock=lambda: next(time_values), sleep=lambda _: None)
        self.assertEqual(seen, [0.5])

    def test_production_adb_inventory_parser_selects_only_exact_model(self):
        client = m.d0.AdbReadOnlyClient(Path('/bin/true'), expected_model='SM-S906N', expected_device='g0q')
        client._run = lambda *args: 'List of devices attached\nother device model:SM_G986N device:y2q\nfixture-device device model:SM_S906N device:g0q\n'
        self.assertEqual(client.one_serial(), TARGET['serial'])

    def test_missing_or_mismatched_review_disables_entry(self):
        (self.root / m.REVIEW).unlink()
        with self.assertRaises(m.ResearchError):
            self.execute('memory')
        self.assertFalse(self.client.calls)

    def test_goal_close_blocks_reuse(self):
        m.close_goal(self.root, self.grant)
        with self.assertRaises(m.ResearchError):
            self.execute('memory')
        self.assertFalse(self.client.calls)

    def test_real_adb_raw_capture_and_reboot_producer_consumer(self):
        adb = self.root / 'fixture-adb'
        state = self.root / 'fixture-boot'
        count = self.root / 'fixture-reboot-count'
        state.write_text(BOOT1)
        # Host fixture only: executable exercises real command quoting, bounded
        # subprocess/raw publication, inventory/property/root parsers and joins.
        source = '''#!/usr/bin/python3
import json, sys, shlex
from pathlib import Path
profile = PROFILE_VALUE
state = Path(STATE_VALUE)
count = Path(COUNT_VALUE)
pending = Path(PENDING_VALUE)
args = sys.argv[1:]
if args == ['devices', '-l']:
    print('List of devices attached\\nother device model:SM_G986N device:y2q\\nfixture-device device model:SM_S906N device:g0q')
elif args == ['-s', 'fixture-device', 'get-devpath']:
    print('usb:1-1')
elif args == ['-s', 'fixture-device', 'reboot']:
    intent = json.loads(pending.read_text())
    assert json.loads((Path(intent['run'])/'intent.json').read_text()) == intent
    assert not count.exists()
    count.write_text('1')
    state.write_text(BOOT2_VALUE)
elif len(args) == 4 and args[:3] == ['-s', 'fixture-device', 'shell']:
    command = shlex.split(args[3])[2]
    if command == 'getprop sys.boot_completed':
        print('1')
        raise SystemExit(0)
    if "printf 'model='" in command:
        fields = dict(model='SM-S906N', device='g0q', bootloader='S906NKSS7FYG8', incremental='S906NKSS7FYG8', boot_completed='1', bootanim='stopped', verified_boot_state='orange', boot_id=state.read_text(), kernel_release='fixture')
    elif "printf 'root='" in command:
        health = profile['start_health']
        fields = dict(root='uid=0(root) gid=0(root)', boot=health['boot_sha256'], **health['supporting_partition_sha256'])
    elif command == 'cat /proc/meminfo && cat /proc/vmstat':
        fields = dict(MemTotal='fixture')
    else:
        raise RuntimeError('unexpected shell')
    print('\\n'.join(k+'='+v for k,v in fields.items()))
else:
    raise RuntimeError('unexpected target/command')
'''
        for name, value in [('PROFILE_VALUE', self.profile), ('STATE_VALUE', str(state)), ('COUNT_VALUE', str(count)), ('PENDING_VALUE', str(self.pending())), ('BOOT2_VALUE', BOOT2)]:
            source = source.replace(name, repr(value))
        adb.write_text(source)
        adb.chmod(0o700)
        factory = lambda: m.d0.AdbReadOnlyClient(adb, expected_model='SM-S906N', expected_device='g0q')
        d0_result = m.execute(self.root, self.grant, 'memory', client_factory=factory)
        result = m.execute(self.root, self.grant, 'normal-reboot', attended=True, client_factory=factory)
        self.assertEqual(result['verdict'], 'PASS')
        self.assertEqual(count.read_text(), '1')
        captures = list((Path(result['run']) / 'raw-adb').glob('*.capture.json'))
        self.assertGreater(len(captures), 5)
        self.assertFalse(self.pending().exists())

    def test_result_publication_cut_retains_guard_without_replay(self):
        original = m.publish
        def fail_result(path, value):
            if path.name == 'result.json':
                raise OSError('simulated host publication cut')
            return original(path, value)
        with patch.object(m, 'publish', fail_result):
            with self.assertRaises(OSError):
                self.execute('normal-reboot', attended=True)
        self.assertTrue(self.pending().exists())
        result = m.reconcile(self.root, client_factory=lambda: self.client)
        self.assertEqual(result['verdict'], 'LATE_HEALTH_OBSERVED_GOAL_CLOSED')
        self.assertEqual(self.client.calls.count(('-s', TARGET['serial'], 'reboot')), 1)

    def test_process_cut_after_authoritative_intent_blocks_new_goal_and_f1(self):
        original = m.publish
        def cut_before_mirror(path, value):
            if path.name == 'intent.json':
                raise KeyboardInterrupt('process cut after authoritative intent')
            return original(path, value)
        with patch.object(m, 'publish', cut_before_mirror):
            with self.assertRaises(KeyboardInterrupt):
                self.execute('normal-reboot', attended=True)
        self.assertTrue(self.pending().exists())
        self.assertNotIn(('-s', TARGET['serial'], 'reboot'), self.client.calls)
        for goal in [self.grant, m.open_goal(self.root, 'new goal cannot erase pending', self.target, ['normal-reboot'])]:
            with self.assertRaises(m.registry.RegistryError):
                m.execute(self.root, goal, 'normal-reboot', attended=True, client_factory=lambda: self.client)
        with self.assertRaises(m.registry.RegistryError):
            with m.registry.target_session_lease(self.root):
                self.fail('unguarded default effect')

    def test_process_cut_after_local_mirror_before_dispatch_blocks_effects(self):
        original = m.publish
        def cut_after_mirror(path, value):
            original(path, value)
            if path.name == 'intent.json':
                raise KeyboardInterrupt('process cut before dispatch')
        with patch.object(m, 'publish', cut_after_mirror):
            with self.assertRaises(KeyboardInterrupt):
                self.execute('normal-reboot', attended=True)
        self.assertTrue(self.pending().exists())
        self.assertNotIn(('-s', TARGET['serial'], 'reboot'), self.client.calls)
        with self.assertRaises(m.registry.RegistryError):
            self.execute('normal-reboot', attended=True)

    def test_parked_f1_owner_blocks_reboot_and_foreign_recovery(self):
        run = self.root / 'workspace/private/runs/f1-fixture'
        m.registry.begin_f1_owner(self.root, run, 'a' * 64)
        with self.assertRaises(m.registry.RegistryError):
            self.execute('normal-reboot', attended=True)
        self.assertFalse(self.client.calls)
        m.registry.require_f1_owner(self.root, run, 'a' * 64)
        with self.assertRaises(m.registry.RegistryError):
            m.registry.require_f1_owner(self.root, run, 'b' * 64)
        with self.assertRaises(m.registry.RegistryError):
            m.registry.retire_f1_owner(self.root, run, 'b' * 64)
        self.assertTrue((self.root / m.registry.F1_OWNER).exists())
        m.registry.retire_f1_owner(self.root, run, 'a' * 64)
        self.assertFalse((self.root / m.registry.F1_OWNER).exists())


if __name__ == '__main__':
    unittest.main()
