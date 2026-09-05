"""H0 tests: actual generated C validator and privately bound codec; no device."""
import ctypes
import inspect
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s22plus_fyg8_readonly_exploration as catalog
import s22plus_fyg8_p342_open_read_branch_runtime as runtime


class ExplorationTests(unittest.TestCase):
    def test_actual_host_first_authenticated_exchange_uses_selected_command(self):
        sys.path.insert(0, str(ROOT / 'tests'))
        import device_action_f1_live_v2 as live
        import test_s22plus_fyg8_host_first_open as pty
        import test_s22plus_fyg8_p335_retained_listener_acm_observer as fixture
        module = live._open_header_initial_observer_module(
            live.p342_open_read_runtime, live.p342_open_read_observer, 'p342')
        live.host_first_open.install_observer(module)
        selected = catalog.select_private_codec(module, 'memory')
        helper = fixture.P335RetainedListenerObserverTests()
        source = textwrap.dedent(inspect.getsource(helper._serve_sessions))
        old = '            peer.sendall(runtime.DEVICE_BANNER)\n            opened = self._receive_frame(peer)'
        self.assertEqual(source.count(old), 1)
        source = source.replace(old, '            opened = self._receive_frame(peer)\n            peer.sendall(runtime.DEVICE_BANNER)')
        class PeerRuntime:
            DEFAULT_COMMANDS = selected
            def __getattr__(self, name):
                return getattr(module.runtime, name)
        peer_runtime = PeerRuntime()
        scope = dict(vars(fixture), observer=module, runtime=peer_runtime)
        exec(compile(source, '<exploration-test-peer>', 'exec'), scope)
        def receive(peer):
            header = helper._receive_exact(peer, module.HEADER.size)
            length = module.HEADER.unpack(header)[3]
            return module.decode_frame(header + helper._receive_exact(peer, length))
        helper._receive_frame = receive
        serve = types.MethodType(scope['_serve_sessions'], helper)
        master, slave = os.openpty()
        errors, captured = [], bytearray()
        thread = threading.Thread(target=serve, args=(pty.Peer(master), fixture.NONCES[:1], errors))
        try:
            live.cdc_acm_observer.ObserverSession._raw_tty(None, slave)
            os.set_blocking(slave, False)
            thread.start()
            try:
                session = module._exchange_one(slave, fixture.TEST_KEY,
                    types.SimpleNamespace(write_stdout=captured.extend), set(), None, 2)
            except Exception:
                if errors:
                    raise AssertionError(errors) from None
                raise
            thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(tuple(item.command for item in session.commands), selected)
            self.assertTrue(captured)
        finally:
            os.close(slave)
            thread.join(3)
            os.close(master)

    def test_closed_named_catalog_and_tuple(self):
        for action in catalog.CATALOG:
            values = catalog.session_commands(action, runtime.P342_RUN_ID_HEX)
            self.assertEqual(values[0], runtime.DEFAULT_COMMANDS[0])
            self.assertEqual(values[2], runtime.DEFAULT_COMMANDS[2])
            self.assertTrue(all(catalog.command_allowed(n, v, runtime.P342_RUN_ID_HEX)
                                for n, v in enumerate(values, 3)))
        for action in ('reboot', 'kernel;id', '/proc/mounts', '', b'kernel', True):
            with self.assertRaises(ValueError):
                catalog.command(action)
        with self.assertRaises(TypeError):
            catalog.CATALOG['new'] = b'anything'

    def test_rejected_bytes_and_sequence(self):
        for value in (b'/bin/busybox reboot', b'/bin/busybox ps;id',
                      b'/bin/busybox ps\x00', b'/bin/busybox cat /dev/block/bootdevice/by-name/boot'):
            self.assertFalse(catalog.command_allowed(4, value, runtime.P342_RUN_ID_HEX))
        for seq in (True, 0, 2, 6):
            self.assertFalse(catalog.command_allowed(seq, catalog.IDENTITY, runtime.P342_RUN_ID_HEX))

    def test_actual_runtime_transform_only_validator_and_unused_constant(self):
        original = runtime.materialize_helper(bytes(range(32)))
        result = catalog.transform_validator(original, runtime.P342_RUN_ID_HEX)
        start = original.index(b'static int p335_command_valid(')
        end = original.index(b'\n}', start) + 2
        unused = next(line + b'\n' for line in original.splitlines() if line.startswith(b'static const char p335_command_2[]'))
        expected = (original[:start] + catalog.validator_source() + original[end:]).replace(unused, b'', 1)
        self.assertEqual(result, expected)
        with self.assertRaises(ValueError):
            catalog.transform_validator(result, runtime.P342_RUN_ID_HEX)

    def test_compiled_device_validator_matches_host_for_all_actions(self):
        cc = shutil.which('cc')
        if cc is None:
            self.skipTest('C compiler unavailable')
        source = ('#include <stdint.h>\n#include <stddef.h>\n#include <string.h>\n'
                  'static int p260_bytes_equal(const char*a,const char*b,size_t n){return memcmp(a,b,n)==0;}\n'
                  'static const char p335_command_1[]="/bin/busybox id";\n'
                  'static const char p335_command_3[]="/bin/busybox echo P328-NONCE ' + runtime.P342_RUN_ID_HEX + '";\n').encode()
        source += catalog.validator_source()
        source += b'\nint check(uint32_t s,const uint8_t*p,uint16_t n){return p335_command_valid(s,p,n);}\n'
        with tempfile.TemporaryDirectory() as directory:
            output = str(Path(directory) / 'validator.so')
            subprocess.run([cc, '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC', '-x', 'c', '-', '-o', output],
                           input=source, check=True, capture_output=True)
            lib = ctypes.CDLL(output)
            lib.check.argtypes = (ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint16)
            payloads = [*catalog.CATALOG.values(), catalog.IDENTITY, runtime.DEFAULT_COMMANDS[2],
                        b'/bin/busybox reboot', b'/bin/busybox ps\x00', b'', b'/bin/busybox ps;id']
            for sequence in range(7):
                for payload in payloads:
                    self.assertEqual(bool(lib.check(sequence, payload, len(payload))),
                                     catalog.command_allowed(sequence, payload, runtime.P342_RUN_ID_HEX))
            self.assertEqual(lib.check(4, None, 1), 0)

    def test_private_codec_one_selection_no_shared_global_change(self):
        import device_action_f1_live_v2 as live
        module = live._open_header_initial_observer_module(
            live.p342_open_read_runtime, live.p342_open_read_observer, 'p342')
        live.host_first_open.install_observer(module)
        original = tuple(runtime.DEFAULT_COMMANDS)
        selected = catalog.select_private_codec(module, 'memory')
        self.assertEqual(module._exchange_one.__globals__['DEFAULT_COMMANDS'], selected)
        self.assertEqual(tuple(runtime.DEFAULT_COMMANDS), original)
        self.assertEqual(module.runtime.DEFAULT_COMMANDS, original)
        with self.assertRaises(ValueError):
            catalog.select_private_codec(module, 'processes')
        shared = types.ModuleType('exploration_shared_fixture')
        sys.modules[shared.__name__] = shared
        try:
            with self.assertRaises(ValueError):
                catalog.select_private_codec(shared, 'kernel')
        finally:
            del sys.modules[shared.__name__]


if __name__ == '__main__':
    unittest.main()
