"""Real resident C exchanges and immutable D0 consumers; synthetic USB hardware."""
from contextlib import contextmanager
import copy
import os
from pathlib import Path
import pty
import time
from types import SimpleNamespace
import tty
import unittest
from unittest import mock

import test_s22plus_proportional_research_v1 as research

owner, live = research.owner, research.live
scope, observation = research.scope, research.observation


class Backend:
    def __init__(self, peer, *, silent=False, release=True):
        self.peer = peer; self.silent = silent; self.release = release; self.checks = 0

    @contextmanager
    def connection(self, context, directory, intent, budget):
        master = None
        if self.silent:
            master, descriptor = pty.openpty(); tty.setraw(descriptor)
        else: descriptor = os.open(self.peer.name, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC)
        os.set_blocking(descriptor, False)
        endpoint = SimpleNamespace(identity_sha256=context.base['endpoint_identity_sha256'])
        connection = observation.Connection(descriptor, endpoint, None, directory, intent, context)
        def check():
            self.checks += 1; budget()
        connection.check = check  # USB/MM facts only; real fd close and wire consumers remain.
        try: yield connection
        finally:
            connection.close(clean=False)
            if master is not None: os.close(master)
            owner.publish(directory/'candidate-observer-guard-release.json', dict(released=self.release))


class ObservationTests(unittest.TestCase):
    setUpClass = classmethod(research.ScopeTests.setUpClass.__func__)
    def fixture(self):
        self.retained_native_endpoint = live.p318_topology._endpoint_row(mode='candidate',
            identity=dict(vendor='1d6b', product_id='0104', product='S22+ native fixture', manufacturer='fixture',
                serial='H0_TEST', driver='cdc_acm', interface='00', tty_name='ttyACM0', endpoint_node='/dev/ttyACM0'),
            topology='3-1.3', controller_path='/sys/fixture/controller', usb_device_path='/sys/fixture/usb3/3-1.3')
        return research.ScopeTests.fixture(self)
    exercise_native = research.ScopeTests.exercise_native
    running = research.ScopeTests.running
    grant = research.ScopeTests.grant
    execute = research.ScopeTests.execute
    bootstrap = research.ScopeTests.bootstrap
    task = research.ScopeTests.task
    select = research.ScopeTests.select
    run_child = research.ScopeTests.run_child

    def observe(self, fixture, previous, backend=None):
        output = fixture.prepared.root/observation.BASE/str(time.monotonic_ns())
        result = observation.observe(live, fixture.prepared.root, previous, output,
            purpose='bounded same-boot protocol observation fixture', seconds=2,
            backend=backend or Backend(fixture.backend.peer))
        return result, Path(result['result']['path'])

    def test_fixed_observation_can_feed_scoped_N_E_N_without_promoting_old_owner(self):
        fixture = self.fixture(); previous, first = self.bootstrap(fixture)
        original = previous.read_bytes(); calls = list(fixture.backend.calls)
        result, terminal = self.observe(fixture, previous)
        self.assertEqual(result['state'], 'NATIVE_OBSERVED', result)
        self.assertEqual(result['actual_authentication_ordinal'], 3)
        self.assertEqual(fixture.backend.calls, calls)
        tail = observation.native_tail(live, fixture.prepared.root, terminal)
        self.assertEqual(tail['native'], first['native'])
        self.assertEqual(scope.previous_lane_directory(live, fixture.prepared.root, terminal), previous.parent)
        with self.assertRaises(owner.core.F1V2Error): owner.native_terminal(live, fixture.prepared.root, terminal.parent)
        task = self.task(fixture, terminal); child = self.select(fixture, task)
        result = self.run_child(fixture, child, terminal)
        self.assertEqual(result['state'], 'NATIVE_CLOSED', result)
        self.assertEqual(previous.read_bytes(), original)

    def test_OPEN_timeout_allows_a_new_fixed_attempt_with_old_failure_unchanged(self):
        fixture = self.fixture(); previous, _ = self.bootstrap(fixture)
        failed, stopped = self.observe(fixture, previous, Backend(fixture.backend.peer, silent=True))
        self.assertEqual(failed['state'], 'UNRESOLVED', failed)
        self.assertEqual(failed['failure_type'], 'TimeoutError')
        old = stopped.read_bytes(); context = observation.context(live, fixture.prepared.root, stopped)
        self.assertEqual(context.uncertain_opens, 1)
        self.assertEqual(context.last_good['baseline_info']['authentication_ordinal'], 2)
        fresh, terminal = self.observe(fixture, stopped)
        self.assertEqual(fresh['state'], 'NATIVE_OBSERVED', fresh)
        self.assertEqual(fresh['actual_authentication_ordinal'], 3)
        self.assertEqual(stopped.read_bytes(), old)
        observation.native_tail(live, fixture.prepared.root, terminal)
        with self.assertRaisesRegex(owner.BaselineError, 'later owner'):
            self.observe(fixture, stopped)

    def test_complete_wire_with_failed_guard_close_never_claims_health_and_keeps_nonce_spent(self):
        fixture = self.fixture(); previous, _ = self.bootstrap(fixture)
        failed, stopped = self.observe(fixture, previous, Backend(fixture.backend.peer, release=False))
        self.assertEqual(failed['state'], 'UNRESOLVED', failed)
        self.assertIsNone(owner.read(stopped)[0]['proof'])
        context = observation.context(live, fixture.prepared.root, stopped)
        self.assertEqual(context.uncertain_opens, 1)
        self.assertEqual(len(context.seen), 3)
        fresh, terminal = self.observe(fixture, stopped)
        self.assertEqual(fresh['state'], 'NATIVE_OBSERVED', fresh)
        self.assertEqual(fresh['actual_authentication_ordinal'], 4)
        observation.native_tail(live, fixture.prepared.root, terminal)

    def test_new_boot_is_rejected_before_AUTH_and_failure_cannot_hide_CONTROL(self):
        fixture = self.fixture(); previous, _ = self.bootstrap(fixture)
        context = observation.context(live, fixture.prepared.root, previous)
        fixture.backend.start_peer('native-final')
        failed, stopped = self.observe(fixture, previous)
        self.assertEqual(failed['state'], 'UNRESOLVED', failed)
        value = owner.read(stopped)[0]
        handle = observation.raw.load_handle(owner.verify_pin(fixture.prepared.root, value['raw']))
        tx = observation.raw.read_stderr(handle, maximum=65536)
        encode = context.codec._CODEC.encode_frame
        self.assertEqual(tx, encode(1, 0, bytes.fromhex(context.declared.IDENTITY.run_id_hex)))
        auth = encode(4, 1, bytes(32))
        with self.assertRaisesRegex(owner.BaselineError, 'state-changing'):
            observation._read_only_tx(context, tx+auth+encode(observation.protocol.wire.CONTROL, 3, bytes(32)))
        with self.assertRaisesRegex(owner.BaselineError, 'caller-selected'):
            observation._read_only_tx(context, tx+auth+encode(observation.protocol.wire.EXEC, 3, b'other-command'+bytes(32)))

    def test_raw_publication_failure_preserves_successor_and_forbids_retry_from_prior(self):
        fixture = self.fixture(); previous, _ = self.bootstrap(fixture)
        with mock.patch.object(observation.DurableWriter, 'write_stdout', side_effect=OSError('raw publication fault')):
            failed, stopped = self.observe(fixture, previous)
        self.assertEqual(failed['state'], 'UNRESOLVED', failed)
        self.assertEqual(failed['failure_type'], 'OSError')
        self.assertIsNone(owner.read(stopped)[0]['proof'])
        self.assertTrue((previous.parent/'next-operation.json').exists())
        with self.assertRaisesRegex(owner.BaselineError, 'later owner'): self.observe(fixture, previous)


class OpenerTests(unittest.TestCase):
    def test_real_fuser_profile_accepts_own_PTY_and_rejects_foreign_PID_or_diagnostics(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); master, descriptor = pty.openpty()
            self.addCleanup(os.close, master); self.addCleanup(os.close, descriptor)
            node = os.ttyname(descriptor); endpoint = SimpleNamespace(tty_name=node.removeprefix('/dev/'))
            original = observation.raw.acquire_command
            def local(command, *args, **kwargs):
                return original(command[1:], *args, **kwargs)  # No privilege/UI interaction for owned PTY.
            (root/'actual').mkdir()
            with mock.patch.object(observation.raw, 'acquire_command', side_effect=local):
                observation.own_descriptor_only(endpoint, root/'actual')
            for stdout, stderr in ((b'999999\n', node.encode()+b':\n'),
                                   (str(os.getpid()).encode(), node.encode()+b': warning\n')):
                path = root/str(time.monotonic_ns()); path.mkdir()
                writer = observation.raw.RawCaptureWriter(path, 'fixture', stdout_maximum=4096, stderr_maximum=4096)
                writer.write_stdout(stdout); writer.write_stderr(stderr); handle = writer.finalize(returncode=0)
                with mock.patch.object(observation.raw, 'acquire_command', return_value=handle), self.assertRaises(owner.BaselineError):
                    observation.own_descriptor_only(endpoint, path)


if __name__ == '__main__': unittest.main()
