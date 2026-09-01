"""Hostile fake-environment tests for the inactive S20+ runtime primitives."""

from __future__ import annotations

import ast
import contextlib
import copy
import ctypes
import fcntl
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import pickle
import re
import resource
import signal
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_runtime_v1_h0.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s20plus_g986n_autonomous_public_health_runtime_v1_h0_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeNode:
    def __init__(self, payload, identity):
        self.payload = payload
        self.identity = identity


class FakeDirEntry:
    def __init__(self, name):
        self.name = name


class FakeScandir:
    def __init__(self, names):
        self.entries = [FakeDirEntry(name) for name in names]

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False

    def __iter__(self):
        return iter(self.entries)


class FakeNetlinkSocket:
    def __init__(self, packets):
        self.packets = list(packets)

    def recvmsg(self, _payload_cap, _ancillary_cap):
        if not self.packets:
            raise BlockingIOError()
        return self.packets.pop(0)


class FakeSetupSocket:
    def __init__(self, fail_at):
        self.fail_at = fail_at
        self.setsockopt_count = 0
        self.closed = False

    def setblocking(self, _value):
        if self.fail_at == "setblocking":
            raise OSError("setblocking cut")

    def setsockopt(self, *_args):
        self.setsockopt_count += 1
        if self.fail_at == f"setsockopt{self.setsockopt_count}":
            raise OSError("setsockopt cut")

    def bind(self, _address):
        if self.fail_at == "bind":
            raise OSError("bind cut")

    def fileno(self):
        if self.fail_at == "fileno":
            raise OSError("fileno cut")
        return 91

    def close(self):
        self.closed = True


class FakeSelectorKey:
    def __init__(self, descriptor, data):
        self.fd = descriptor
        self.data = data


class FakeCaptureSelector:
    def __init__(self, operations):
        self.operations = operations
        self.registered = {}
        self.closed = False

    def register(self, descriptor, _events, data):
        self.operations.calls.append(("register", descriptor, data))
        ordinal = len(self.registered) + 1
        if self.operations.fail_at == f"register{ordinal}":
            raise OSError("fixture register failure")
        self.registered[descriptor] = data

    def unregister(self, descriptor):
        self.operations.calls.append(("unregister", descriptor))
        self.registered.pop(descriptor)

    def select(self, _timeout=None):
        self.operations.calls.append(("select",))
        self.operations.clock_value += self.operations.select_delay_ns
        if self.operations.child_exits_during_select:
            self.operations.child_exited = True
        if self.operations.fail_at == "select":
            raise OSError("fixture select failure")
        if self.operations.select_plan:
            descriptors = self.operations.select_plan.pop(0)
        else:
            descriptors = []
        return [
            (FakeSelectorKey(descriptor, self.registered[descriptor]), 1)
            for descriptor in descriptors
        ]

    def close(self):
        self.operations.calls.append(("selector_close",))
        self.closed = True
        if self.operations.fail_at == "selector_close":
            raise OSError("fixture selector close failure")


class FakeCaptureOps:
    """Deterministic fake fork/pipe/pidfd/selector lifecycle."""

    def __init__(self, *, fail_at=None, child_initially_exited=True):
        self.fail_at = fail_at
        self.child_pid = 4242
        self.next_fd = 10
        self.pipe_count = 0
        self.calls = []
        self.allocated = set()
        self.closed = []
        self.nonblocking = []
        self.signals = []
        self.kills = []
        self.successful_reaps = 0
        self.child_exited = child_initially_exited
        self.selector_value = None
        self.select_plan = [[10, 12]]
        self.read_plan = {10: [b""], 12: [b""]}
        self.clock_value = 0
        self.clock_step = 100_000_000
        self.clock_values = []
        self.select_delay_ns = 0
        self.child_exits_during_select = False
        self.waitpid_nonblocking_delay_ns = 0

    def _fd(self):
        value = self.next_fd
        self.next_fd += 1
        self.allocated.add(value)
        return value

    def pipe2(self):
        self.pipe_count += 1
        self.calls.append(("pipe2", self.pipe_count))
        if self.fail_at == f"pipe{self.pipe_count}":
            raise OSError("fixture pipe failure")
        return self._fd(), self._fd()

    def fork(self):
        self.calls.append(("fork",))
        if self.fail_at == "fork":
            raise OSError("fixture fork failure")
        return self.child_pid

    def getpid(self):
        self.calls.append(("getpid",))
        return 31337

    def child_exec(self, *_args):
        raise AssertionError("fake parent path must not enter child")

    def child_exit(self, _status):
        raise AssertionError("fake parent path must not exit")

    def close(self, descriptor):
        self.calls.append(("close", descriptor))
        if descriptor in self.closed:
            raise AssertionError("descriptor closed twice")
        self.closed.append(descriptor)

    def set_nonblocking(self, descriptor):
        self.calls.append(("set_nonblocking", descriptor))
        ordinal = len(self.nonblocking) + 1
        if self.fail_at == f"set_nonblocking{ordinal}":
            raise OSError("fixture nonblocking setup failure")
        self.nonblocking.append(descriptor)

    def pidfd_open(self, pid):
        self.calls.append(("pidfd_open", pid))
        if self.fail_at == "pidfd":
            raise OSError("fixture pidfd failure")
        return self._fd()

    def pidfd_signal(self, pidfd, signum):
        self.calls.append(("pidfd_signal", pidfd, signum))
        self.signals.append(signum)
        if self.fail_at == "pidfd_signal":
            raise OSError("fixture pidfd signal failure")
        if signum == 9:
            self.child_exited = True

    def kill(self, pid, signum):
        self.calls.append(("kill", pid, signum))
        self.kills.append(signum)
        if signum == 9:
            self.child_exited = True

    def waitpid(self, pid, options):
        self.calls.append(("waitpid", pid, options))
        if options != 0:
            self.clock_value += self.waitpid_nonblocking_delay_ns
        if self.fail_at == "waitpid" and options != 0:
            self.fail_at = None
            raise OSError("fixture wait failure")
        if options != 0 and not self.child_exited:
            return 0, 0
        self.child_exited = True
        self.successful_reaps += 1
        return pid, 0

    def selector(self):
        self.calls.append(("selector",))
        if self.fail_at == "selector":
            raise OSError("fixture selector failure")
        self.selector_value = FakeCaptureSelector(self)
        return self.selector_value

    def read(self, descriptor, _maximum):
        self.calls.append(("read", descriptor))
        if self.fail_at == "read":
            raise OSError("fixture read failure")
        values = self.read_plan.setdefault(descriptor, [b""])
        return values.pop(0) if values else b""

    def boottime_ns(self):
        if self.clock_values:
            value = self.clock_values.pop(0)
            self.clock_value = value
            return value
        value = self.clock_value
        self.clock_value += self.clock_step
        return value


class FakeEnvironment:
    """No method contacts a real file, process, clock, socket, or USB node."""

    def __init__(self, module):
        self.m = module
        self.nodes = {}
        self.open_errors = {}
        self.handles = {}
        self.closed_descriptors = set()
        self.next_fd = 100
        self.calls = []
        self.listeners = (module.ListenerCandidate(777, 4242),)
        self.start_ticks = {4242: 99_001}
        self.process_uids = {4242: 1000}
        self.euid = 1000
        self.pidfds = set()
        self.dead_pidfds = set()
        self.process_exe_node = None
        self.clock_values = []
        self.last_clock = module.ClockSnapshot(
            "12345678-1234-1234-1234-123456789abc",
            1_700_000_000_000_000_000,
            5_000_000_000,
            4_000_000_000,
        )
        self.monitor_fds = set()
        self.monitor_batches = []
        self.monitor_error = None
        self.usb_by_digest = {}
        self.process_pid = 700
        self.thread_ident = 800
        self.thread_object = object()
        self.thread_alive = True
        self.process_identity_values = []
        self.capabilities = {}
        self.capability_alive_override = None
        self.next_capture = None
        self.exec_calls = []

    def _allocate(self):
        descriptor = self.next_fd
        self.next_fd += 1
        return descriptor

    def add_node(
        self,
        path,
        payload=b"",
        *,
        mode=None,
        inode=None,
        links=1,
        device=11,
        uid=1000,
        gid=1000,
        mtime_ns=10,
        ctime_ns=20,
        rdev=0,
    ):
        if mode is None:
            mode = stat.S_IFREG | 0o755
        if inode is None:
            inode = 10_000 + len(self.nodes)
        identity = self.m.StatSnapshot(
            device=device,
            inode=inode,
            mode=mode,
            links=links,
            uid=uid,
            gid=gid,
            size=len(payload),
            mtime_ns=mtime_ns,
            ctime_ns=ctime_ns,
            rdev=rdev,
        )
        node = FakeNode(payload, identity)
        self.nodes[path] = node
        return node

    def open_file(self, path, flags):
        self.calls.append(("open_file", path, flags))
        if path in self.open_errors:
            raise self.open_errors[path]
        if path not in self.nodes:
            raise FileNotFoundError(path)
        descriptor = self._allocate()
        self.handles[descriptor] = self.nodes[path]
        return descriptor

    def _open_node(self, node):
        descriptor = self._allocate()
        self.handles[descriptor] = node
        return descriptor

    def close(self, descriptor):
        self.calls.append(("close", descriptor))
        if descriptor in self.closed_descriptors:
            raise OSError("double close")
        self.closed_descriptors.add(descriptor)
        self.handles.pop(descriptor, None)
        self.pidfds.discard(descriptor)
        self.monitor_fds.discard(descriptor)

    def fstat(self, descriptor):
        self.calls.append(("fstat", descriptor))
        try:
            return self.handles[descriptor].identity
        except KeyError as exc:
            raise OSError("bad descriptor") from exc

    def pread_all(self, descriptor, maximum):
        self.calls.append(("pread_all", descriptor, maximum))
        return self.handles[descriptor].payload[:maximum]

    def effective_uid(self):
        self.calls.append(("effective_uid",))
        return self.euid

    def listener_candidates(self, socket_spec):
        self.calls.append(("listener_candidates", socket_spec))
        if socket_spec != self.m.ADB_SERVER_SOCKET:
            raise AssertionError("nonfixed server socket")
        return self.listeners

    def process_start_ticks(self, pid):
        self.calls.append(("process_start_ticks", pid))
        return self.start_ticks[pid]

    def process_uid(self, pid):
        self.calls.append(("process_uid", pid))
        return self.process_uids[pid]

    def pidfd_open(self, pid):
        self.calls.append(("pidfd_open", pid))
        descriptor = self._allocate()
        self.pidfds.add(descriptor)
        return descriptor

    def pidfd_alive(self, descriptor):
        self.calls.append(("pidfd_alive", descriptor))
        return descriptor in self.pidfds and descriptor not in self.dead_pidfds

    def open_process_executable(self, pid):
        self.calls.append(("open_process_executable", pid))
        node = self.process_exe_node or self.nodes[self.m.ADB_PATH]
        return self._open_node(node)

    def clock_snapshot(self):
        self.calls.append(("clock_snapshot",))
        if self.clock_values:
            self.last_clock = self.clock_values.pop(0)
        return self.last_clock

    def open_usb_monitor(self):
        self.calls.append(("open_usb_monitor",))
        descriptor = self._allocate()
        self.monitor_fds.add(descriptor)
        return descriptor

    def drain_usb_monitor(self, descriptor):
        self.calls.append(("drain_usb_monitor", descriptor))
        if self.monitor_error is not None:
            error = self.monitor_error
            self.monitor_error = None
            raise error
        if descriptor not in self.monitor_fds:
            return self.m.MonitorBatch((), False, False)
        if self.monitor_batches:
            return self.monitor_batches.pop(0)
        return self.m.MonitorBatch((), False, True)

    def usb_candidates(self, topology_sha256):
        self.calls.append(("usb_candidates", topology_sha256))
        return self.usb_by_digest.get(topology_sha256, ())

    def process_identity(self):
        self.calls.append(("process_identity",))
        if self.process_identity_values:
            return self.process_identity_values.pop(0)
        return self.m.ProcessThreadIdentity(
            self.process_pid,
            self.thread_ident,
            self.thread_object,
            self.thread_alive,
        )

    def new_capability_descriptor(self):
        self.calls.append(("new_capability_descriptor",))
        read_fd = self._allocate()
        write_fd = self._allocate()
        inode = 50_000 + read_fd
        read_identity = self.m.StatSnapshot(
            44, inode, stat.S_IFIFO | 0o600, 1, 1000, 1000, 0, 1, 1
        )
        write_identity = self.m.StatSnapshot(
            44, inode, stat.S_IFIFO | 0o600, 1, 1000, 1000, 0, 1, 1
        )
        value = self.m.CapabilityDescriptor(
            read_fd,
            write_fd,
            read_identity,
            write_identity,
            os.O_RDONLY,
            os.O_WRONLY,
            object(),
        )
        self.capabilities[value.token] = value
        return value

    def capability_alive(self, descriptor):
        self.calls.append(("capability_alive", descriptor))
        if self.capability_alive_override is not None:
            return self.capability_alive_override
        return self.capabilities.get(descriptor.token) is descriptor

    def close_capability(self, descriptor):
        self.calls.append(("close_capability", descriptor))
        if self.capabilities.pop(descriptor.token, None) is not descriptor:
            raise OSError("foreign capability")

    def execute_fixed_adb(self, descriptor, ordinal, serial):
        self.calls.append(("execute_fixed_adb", descriptor, ordinal, serial))
        self.exec_calls.append((descriptor, ordinal, serial))
        if self.next_capture is not None:
            value = self.next_capture
            self.next_capture = None
            return value
        return self.m.CommandCapture(
            argv=self.m._fixed_argv(ordinal, serial),
            timeout_sec=self.m.FIXED_TIMEOUTS[ordinal - 1],
            returncode=0,
            stdout=b"ok\n",
            stderr=b"",
            timed_out=False,
            term_sent=False,
            kill_sent=False,
            post_child_drain_expired=False,
        )


class S20PlusPublicHealthRuntimeV1H0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def setUp(self):
        self.env = FakeEnvironment(self.m)
        self.adb_payload = b"fake-adb-executable-v1"
        self.adb_expectation = self.m.ExactFileExpectation(
            self.m.ADB_PATH,
            len(self.adb_payload),
            self.m._sha256(self.adb_payload),
            True,
        )
        self.adb_node = self.env.add_node(
            self.m.ADB_PATH,
            self.adb_payload,
            mode=stat.S_IFREG | 0o755,
            inode=1200,
        )
        self.enterContext(mock.patch.object(self.m, "ADB_EXPECTATION", self.adb_expectation))

    def bind_adb(self):
        return self.m.AdbClientOwner.bind(self.env)

    def bind_server(self, adb):
        return self.m.AdbServerOwner.bind(self.env, adb)

    def add_usb(self, topology="usb:1-2"):
        digest = self.m._topology_sha256(topology)
        sysfs = "/sys/devices/platform/test/usb1/1-2"
        usbfs = "/dev/bus/usb/001/007"
        self.env.add_node(
            sysfs,
            mode=stat.S_IFDIR | 0o755,
            inode=2200,
            links=2,
        )
        self.env.add_node(
            usbfs,
            mode=stat.S_IFCHR | 0o600,
            inode=2201,
            rdev=os.makedev(189, 6),
        )
        candidate = self.m.UsbCandidate(
            topology=topology,
            topology_sha256=digest,
            sysfs_path=sysfs,
            usbfs_path=usbfs,
            busnum=1,
            devnum=7,
        )
        self.env.usb_by_digest[digest] = (candidate,)
        return topology, digest, candidate

    def bind_bundle(self):
        adb = self.bind_adb()
        server = self.bind_server(adb)
        clock = self.m.HostClockOwner.bind(self.env)
        topology, _digest, _candidate = self.add_usb()
        usb = self.m.UsbGenerationOwner.start(self.env)
        usb.bind(topology)
        return self.m._OwnerBundle.create(adb, server, clock, usb)

    def test_render_plan_is_exact_inactive_h0(self):
        plan = self.m.render_plan()
        self.assertEqual(plan["schema"], self.m.SCHEMA)
        self.assertEqual(plan["status"], self.m.STATUS)
        self.assertEqual(
            plan["target"],
            {
                "model": "SM-G986N",
                "device": "y2q",
                "product": "y2qksx",
                "build": "G986NKSS8IYC2",
            },
        )
        self.assertTrue(plan["gates"])
        self.assertTrue(all(value is False for value in plan["gates"].values()))
        self.assertFalse(plan["authority"]["device_contact"])
        self.assertFalse(plan["authority"]["connected_executor"])
        self.assertFalse(plan["authority"]["durable_bytes_authorize_commands"])
        self.assertFalse(plan["authority"]["python_privacy_is_authority_boundary"])
        self.assertFalse(plan["authority"]["closed_executor_call_graph_implemented"])
        self.assertFalse(plan["adb_server"]["autostart_prevention_implemented"])
        self.assertTrue(plan["adb_server"]["postcheck_only_cannot_prevent_restart"])
        self.assertFalse(plan["child_lifecycle"]["execution_qualified"])
        self.assertFalse(
            plan["child_lifecycle"]["post_child_pipe_deadline_expiry_is_success"]
        )
        self.assertEqual(plan["post_direct_child_pipe_drain_ms"], 250)
        self.assertTrue(plan["process_capability"]["thread_object_identity_bound"])
        self.assertTrue(plan["process_capability"]["fd_number_reuse_rejected"])
        for field in (
            "device_commands",
            "device_writes",
            "root_commands",
            "odin_invocations",
            "partition_transfers",
        ):
            self.assertEqual(plan[field], [])

    def test_plan_pins_exact_phase_a_and_adb_identities(self):
        plan = self.m.render_plan()
        self.assertEqual(plan["phase_a"]["size"], 92_607)
        self.assertEqual(
            plan["phase_a"]["sha256"],
            "43edcfc5bf2c69f96bcef015f305d38be9c310dd92371a2a942e075261dfa8e2",
        )
        self.assertEqual(
            plan["phase_a"]["normalized_sha256"],
            "be1f73de763b7fcce8e1b74da23cb662244b7b1de9bcbb862ffa59c5c296e773",
        )
        self.assertEqual(plan["adb_client"]["path"], self.m.ADB_PATH)
        self.assertEqual(plan["adb_client"]["size"], 716_968)
        self.assertEqual(
            plan["adb_client"]["sha256"],
            "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226",
        )
        self.assertIn("AT_EMPTY_PATH", plan["adb_client"]["exec_primitive"])
        self.assertFalse(plan["adb_client"]["path_exec"])
        self.assertFalse(plan["adb_client"]["proc_self_fd_fallback"])

    def test_self_identity_and_normalized_anchor_are_exact(self):
        source = SCRIPT.read_bytes()
        plan = self.m.render_plan()
        self.assertEqual(plan["self"]["size"], len(source))
        self.assertEqual(plan["self"]["sha256"], hashlib.sha256(source).hexdigest())
        self.assertEqual(
            plan["self"]["normalized_sha256"],
            self.m.EXPECTED_SELF_NORMALIZED_SHA256,
        )

    def test_normalization_masks_only_status_anchor_and_gate_atoms(self):
        source = SCRIPT.read_bytes()
        expected = self.m.normalized_source_sha256(source)
        rotated = re.sub(
            rb'^STATUS = "[A-Z0-9_]+"$',
            b'STATUS = "REVIEWED_TEST_STATUS_NOT_ACTIVE"',
            source,
            count=1,
            flags=re.MULTILINE,
        )
        for name in self.m.NORMALIZED_GATE_NAMES:
            rotated = re.sub(
                rf"^{name} = False$".encode(),
                f"{name} = True".encode(),
                rotated,
                count=1,
                flags=re.MULTILINE,
            )
        self.assertEqual(self.m.normalized_source_sha256(rotated), expected)
        logic_drift = source.replace(
            b"POST_CHILD_DRAIN_NS = 250 * 1_000_000",
            b"POST_CHILD_DRAIN_NS = 251 * 1_000_000",
            1,
        )
        self.assertNotEqual(logic_drift, source)
        self.assertNotEqual(
            self.m.normalized_source_sha256(logic_drift), expected
        )

    def test_cli_is_render_only(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(self.m.main(["--render-plan"]), 0)
        self.assertEqual(json_load(output.getvalue())["status"], self.m.STATUS)
        for argv in ([], ["--serial", "x"], ["--attended-open-and-read"]):
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.m.main(argv)

    def test_operational_entry_is_gate_first_and_still_has_no_executor(self):
        tree = ast.parse(self.source)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "attended_open_and_read"
        )
        first = function.body[1] if isinstance(function.body[0], ast.Expr) else function.body[0]
        self.assertIsInstance(first, ast.Expr)
        self.assertEqual(first.value.func.id, "_require_operational_gate")
        with mock.patch.object(
            self.m, "_PosixEnvironment", side_effect=AssertionError("OS environment touched")
        ):
            with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "inactive"):
                self.m.attended_open_and_read()
            with mock.patch.object(
                self.m,
                "_operational_gates",
                return_value={"all": True},
            ):
                with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "no live executor"):
                    self.m.attended_open_and_read()

    def test_all_declared_operational_flags_are_literal_false(self):
        names = (
            "RUNTIME_PRIMITIVES_REVIEWED",
            "PHASE_A_EXACT_BOUND",
            "ADB_CLIENT_FD_EXEC_REVIEWED",
            "ADB_SERVER_OWNER_REVIEWED",
            "HOST_CLOCK_OWNER_REVIEWED",
            "USB_GENERATION_OWNER_REVIEWED",
            "OPENING_READ_CAPABILITY_REVIEWED",
            "EXECUTOR_IMPLEMENTED",
            "SAME_PROCESS_HANDOFF_IMPLEMENTED",
            "TARGET_COORDINATION_ACTIVE",
            "CROSS_CODE_COORDINATION_ACTIVE",
            "CONTRACT_ACTIVE",
            "MECHANICAL_ACTIVATION",
            "LIVE_AUTHORITY",
        )
        self.assertTrue(all(getattr(self.m, name) is False for name in names))

    def test_fixed_transcript_has_no_caller_command_surface(self):
        serial = "RFCM0000000"
        expected = (
            (self.m.ADB_PATH, "version"),
            (self.m.ADB_PATH, "devices", "-l"),
            (self.m.ADB_PATH, "-s", serial, "get-devpath"),
            (
                self.m.ADB_PATH,
                "-s",
                serial,
                "exec-out",
                "sh",
                "-c",
                self.m.REMOTE_SNAPSHOT,
            ),
            (
                self.m.ADB_PATH,
                "-s",
                serial,
                "exec-out",
                "sh",
                "-c",
                self.m.REMOTE_SNAPSHOT,
            ),
            (self.m.ADB_PATH, "devices", "-l"),
        )
        self.assertEqual(
            tuple(self.m._fixed_argv(i, serial) for i in range(1, 7)), expected
        )
        self.assertEqual(self.m.FIXED_TIMEOUTS, (10, 10, 10, 20, 20, 10))
        for ordinal, serial_value in ((0, serial), (7, serial), (True, serial), (1, "bad\n")):
            with self.subTest(ordinal=ordinal, serial=serial_value):
                with self.assertRaises(self.m.RuntimePrimitiveError):
                    self.m._fixed_argv(ordinal, serial_value)

    def test_exact_file_owner_accepts_one_stable_direct_regular_file(self):
        owner = self.m.HeldExactFile.bind(self.env, self.adb_expectation)
        owner.verify(reopen_path=True)
        self.assertEqual(owner.identity, self.adb_node.identity)
        owner.close()

    def test_phase_a_owner_has_only_the_fixed_source_path_and_identity(self):
        payload = b"fake-phase-a-source"
        expectation = self.m.ExactFileExpectation(
            self.m.PHASE_A_PATH,
            len(payload),
            self.m._sha256(payload),
            False,
        )
        node = self.env.add_node(
            self.m.PHASE_A_PATH,
            payload,
            mode=stat.S_IFREG | 0o644,
            inode=1300,
        )
        with mock.patch.object(self.m, "PHASE_A_EXPECTATION", expectation):
            owner = self.m.PhaseASourceOwner.bind(self.env)
            owner.verify()
            self.assertEqual(owner._file.identity, node.identity)

    def test_exact_file_owner_rejects_hash_size_type_link_and_exec_drift(self):
        cases = ("hash", "size", "type", "links", "exec")
        for case in cases:
            with self.subTest(case=case):
                env = FakeEnvironment(self.m)
                payload = self.adb_payload
                mode = stat.S_IFREG | 0o755
                links = 1
                expectation = self.adb_expectation
                if case == "hash":
                    expectation = self.m.ExactFileExpectation(
                        self.m.ADB_PATH, len(payload), "0" * 64, True
                    )
                elif case == "size":
                    expectation = self.m.ExactFileExpectation(
                        self.m.ADB_PATH, len(payload) + 1, self.m._sha256(payload), True
                    )
                elif case == "type":
                    mode = stat.S_IFDIR | 0o755
                elif case == "links":
                    links = 2
                elif case == "exec":
                    mode = stat.S_IFREG | 0o644
                env.add_node(self.m.ADB_PATH, payload, mode=mode, links=links)
                with self.assertRaises(self.m.RuntimePrimitiveError):
                    self.m.HeldExactFile.bind(env, expectation)

    def test_held_adb_detects_open_inode_and_canonical_path_replacement(self):
        owner = self.bind_adb()
        old = self.adb_node
        self.env.add_node(
            self.m.ADB_PATH,
            self.adb_payload,
            mode=stat.S_IFREG | 0o755,
            inode=9999,
        )
        with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "path was replaced"):
            owner.verify()
        self.env.nodes[self.m.ADB_PATH] = old
        old.identity = self.m.StatSnapshot(
            **{**old.identity.__dict__, "mtime_ns": old.identity.mtime_ns + 1}
        )
        with self.assertRaises(self.m.RuntimePrimitiveError):
            owner.verify()

    def test_adb_capture_rechecks_held_fd_and_exact_receipt(self):
        owner = self.bind_adb()
        with mock.patch.object(
            self.m, "_operational_gates", return_value={"test-only": True}
        ):
            capture = owner.capture(4, "RFCM0000000")
        self.assertEqual(capture.argv, self.m._fixed_argv(4, "RFCM0000000"))
        self.assertEqual(self.env.exec_calls, [(owner._file.descriptor, 4, "RFCM0000000")])

    def test_imported_adb_capture_stops_before_injected_environment_call(self):
        owner = self.bind_adb()
        with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "inactive"):
            owner.capture(1, "RFCM0000000")
        self.assertEqual(self.env.exec_calls, [])

    def test_adb_capture_rejects_forged_or_oversized_child_receipt(self):
        owner = self.bind_adb()
        good = self.m.CommandCapture(
            argv=self.m._fixed_argv(1, "RFCM0000000"),
            timeout_sec=10,
            returncode=0,
            stdout=b"",
            stderr=b"",
            timed_out=False,
            term_sent=False,
            kill_sent=False,
            post_child_drain_expired=False,
        )
        mutations = (
            {"argv": ("evil",)},
            {"timeout_sec": 20},
            {"stdout": b"x" * (self.m.MAX_OUTPUT_BYTES + 1)},
            {"returncode": True},
        )
        for mutation in mutations:
            with self.subTest(mutation=next(iter(mutation))):
                values = {field: getattr(good, field) for field in good.__dataclass_fields__}
                values.update(mutation)
                self.env.next_capture = self.m.CommandCapture(**values)
                with mock.patch.object(
                    self.m, "_operational_gates", return_value={"test-only": True}
                ):
                    with self.assertRaises(self.m.RuntimePrimitiveError):
                        owner.capture(1, "RFCM0000000")

    def test_adb_owner_makes_post_child_drain_expiry_mandatory_non_success(self):
        owner = self.bind_adb()
        self.env.next_capture = self.m.CommandCapture(
            argv=self.m._fixed_argv(1, "RFCM0000000"),
            timeout_sec=10,
            returncode=0,
            stdout=b"apparently complete\n",
            stderr=b"",
            timed_out=False,
            term_sent=False,
            kill_sent=False,
            post_child_drain_expired=True,
        )
        with mock.patch.object(
            self.m, "_operational_gates", return_value={"test-only": True}
        ):
            with self.assertRaisesRegex(
                self.m.RuntimePrimitiveError, "mandatory non-success"
            ):
                owner.capture(1, "RFCM0000000")

    def test_adb_owner_makes_late_child_completion_timeout_mandatory_non_success(self):
        owner = self.bind_adb()
        self.env.next_capture = self.m.CommandCapture(
            argv=self.m._fixed_argv(1, "RFCM0000000"),
            timeout_sec=10,
            returncode=0,
            stdout=b"apparently complete\n",
            stderr=b"",
            timed_out=True,
            term_sent=False,
            kill_sent=False,
            post_child_drain_expired=False,
        )
        with mock.patch.object(
            self.m, "_operational_gates", return_value={"test-only": True}
        ):
            with self.assertRaisesRegex(
                self.m.RuntimePrimitiveError, "mandatory non-success"
            ):
                owner.capture(1, "RFCM0000000")

    def test_server_owner_binds_preexisting_unique_same_uid_exact_exe(self):
        adb = self.bind_adb()
        server = self.bind_server(adb)
        server.verify()
        self.assertIn(("listener_candidates", self.m.ADB_SERVER_SOCKET), self.env.calls)
        self.assertEqual(server._socket_inode, 777)
        self.assertEqual(server._pid, 4242)
        server.close()

    def test_server_owner_rejects_absent_or_ambiguous_listener(self):
        for listeners in ((), (self.m.ListenerCandidate(777, 4242), self.m.ListenerCandidate(778, 4243))):
            with self.subTest(count=len(listeners)):
                env = self.fresh_env()
                env.listeners = listeners
                adb = self.m.AdbClientOwner.bind(env)
                with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "absent or ambiguous"):
                    self.m.AdbServerOwner.bind(env, adb)

    def test_server_owner_rejects_uid_start_and_executable_drift(self):
        for case in ("uid", "start", "exe"):
            with self.subTest(case=case):
                env = self.fresh_env()
                if case == "uid":
                    env.process_uids[4242] = 2000
                elif case == "start":
                    env.start_ticks[4242] = 0
                else:
                    env.process_exe_node = env.add_node(
                        "/fake/other-adb",
                        self.adb_payload,
                        mode=stat.S_IFREG | 0o755,
                        inode=22222,
                    )
                adb = self.m.AdbClientOwner.bind(env)
                with self.assertRaises(self.m.RuntimePrimitiveError):
                    self.m.AdbServerOwner.bind(env, adb)

    def test_server_continuity_rejects_every_bound_axis_drift(self):
        mutations = ("pidfd", "listener", "start", "uid", "exe")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                env = self.fresh_env()
                adb = self.m.AdbClientOwner.bind(env)
                server = self.m.AdbServerOwner.bind(env, adb)
                if mutation == "pidfd":
                    env.dead_pidfds.add(server._pidfd)
                elif mutation == "listener":
                    env.listeners = (self.m.ListenerCandidate(779, 4242),)
                elif mutation == "start":
                    env.start_ticks[4242] += 1
                elif mutation == "uid":
                    env.process_uids[4242] += 1
                else:
                    env.process_exe_node = env.add_node(
                        "/fake/replaced-server-exe",
                        self.adb_payload,
                        mode=stat.S_IFREG | 0o755,
                        inode=33333,
                    )
                with self.assertRaises(self.m.RuntimePrimitiveError):
                    server.verify()

    def test_clock_owner_accepts_suspend_delta_and_exact_total_boundary(self):
        origin = self.env.last_clock
        owner = self.m.HostClockOwner.bind(self.env)
        boundary = self.m.TOTAL_OWNER_MAX_NS
        self.env.clock_values.append(
            self.m.ClockSnapshot(
                origin.boot_id,
                origin.realtime_ns + boundary,
                origin.boottime_ns + boundary,
                origin.monotonic_ns + boundary - 1_000_000_000,
            )
        )
        owner.sample()
        self.assertEqual(owner.elapsed_ns, boundary)

    def test_clock_owner_rejects_boot_reversal_skew_and_expiry(self):
        cases = (
            "boot",
            "realtime",
            "boottime",
            "monotonic",
            "delta",
            "sample-jitter",
            "skew",
            "expiry",
        )
        for case in cases:
            with self.subTest(case=case):
                env = self.fresh_env()
                origin = env.last_clock
                owner = self.m.HostClockOwner.bind(env)
                value = self.m.ClockSnapshot(
                    origin.boot_id,
                    origin.realtime_ns + 1_000_000_000,
                    origin.boottime_ns + 1_000_000_000,
                    origin.monotonic_ns + 1_000_000_000,
                )
                fields = value.__dict__.copy()
                if case == "boot":
                    fields["boot_id"] = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
                elif case == "realtime":
                    fields["realtime_ns"] = origin.realtime_ns - 1
                elif case == "boottime":
                    fields["boottime_ns"] = origin.boottime_ns - 1
                elif case == "monotonic":
                    fields["monotonic_ns"] = origin.monotonic_ns - 1
                elif case == "delta":
                    fields["monotonic_ns"] = (
                        origin.monotonic_ns
                        + 1_000_000_000
                        + self.m.CLOCK_AXIS_SAMPLE_JITTER_MAX_NS
                        + 1
                    )
                elif case == "sample-jitter":
                    fields["monotonic_ns"] = (
                        origin.monotonic_ns
                        + 1_000_000_000
                        + self.m.CLOCK_AXIS_SAMPLE_JITTER_MAX_NS
                        + 1
                    )
                elif case == "skew":
                    fields["realtime_ns"] += self.m.REALTIME_PROJECTION_SKEW_MAX_NS + 1
                elif case == "expiry":
                    delta = self.m.TOTAL_OWNER_MAX_NS + 1
                    fields["realtime_ns"] = origin.realtime_ns + delta
                    fields["boottime_ns"] = origin.boottime_ns + delta
                    fields["monotonic_ns"] = origin.monotonic_ns + delta
                env.clock_values.append(self.m.ClockSnapshot(**fields))
                with self.assertRaises(self.m.RuntimePrimitiveError):
                    owner.sample()

    def test_clock_owner_accepts_exact_cross_axis_jitter_boundary(self):
        origin = self.env.last_clock
        owner = self.m.HostClockOwner.bind(self.env)
        delta = 1_000_000_000
        self.env.clock_values.append(
            self.m.ClockSnapshot(
                origin.boot_id,
                origin.realtime_ns + delta,
                origin.boottime_ns + delta,
                origin.monotonic_ns
                + delta
                + self.m.CLOCK_AXIS_SAMPLE_JITTER_MAX_NS,
            )
        )
        owner.sample()

    def test_clock_owner_enforces_exact_opening_and_handoff_windows(self):
        origin = self.env.last_clock
        owner = self.m.HostClockOwner.bind(self.env)
        owner.mark_opening_start()
        opening_delta = self.m.OPENING_CHAIN_MAX_NS
        self.env.clock_values.append(
            self.m.ClockSnapshot(
                origin.boot_id,
                origin.realtime_ns + opening_delta,
                origin.boottime_ns + opening_delta,
                origin.monotonic_ns + opening_delta,
            )
        )
        owner.mark_opening_complete()
        total_delta = opening_delta + self.m.HANDOFF_MAX_NS
        self.env.clock_values.append(
            self.m.ClockSnapshot(
                origin.boot_id,
                origin.realtime_ns + total_delta,
                origin.boottime_ns + total_delta,
                origin.monotonic_ns + total_delta,
            )
        )
        owner.mark_read_start()

        for window in ("opening", "handoff"):
            with self.subTest(window=window):
                env = self.fresh_env()
                base = env.last_clock
                bounded = self.m.HostClockOwner.bind(env)
                bounded.mark_opening_start()
                first_delta = (
                    self.m.OPENING_CHAIN_MAX_NS + 1
                    if window == "opening"
                    else self.m.OPENING_CHAIN_MAX_NS
                )
                env.clock_values.append(
                    self.m.ClockSnapshot(
                        base.boot_id,
                        base.realtime_ns + first_delta,
                        base.boottime_ns + first_delta,
                        base.monotonic_ns + first_delta,
                    )
                )
                if window == "opening":
                    with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "300"):
                        bounded.mark_opening_complete()
                else:
                    bounded.mark_opening_complete()
                    second_delta = first_delta + self.m.HANDOFF_MAX_NS + 1
                    env.clock_values.append(
                        self.m.ClockSnapshot(
                            base.boot_id,
                            base.realtime_ns + second_delta,
                            base.boottime_ns + second_delta,
                            base.monotonic_ns + second_delta,
                        )
                    )
                    with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "30"):
                        bounded.mark_read_start()

    def test_usb_monitor_must_start_lossless_and_before_selection(self):
        cases = (
            self.m.MonitorBatch((), True, True),
            self.m.MonitorBatch((), False, False),
            self.m.MonitorBatch((self.m.UsbEvent("add", "0" * 64),), False, True),
        )
        for batch in cases:
            with self.subTest(batch=batch):
                env = self.fresh_env()
                env.monitor_batches.append(batch)
                with self.assertRaises(self.m.RuntimePrimitiveError):
                    self.m.UsbGenerationOwner.start(env)
                self.assertEqual(env.calls[0], ("open_usb_monitor",))

    def test_nested_uevent_uses_exact_deepest_device_or_interface_topology(self):
        devpath = (
            "/devices/platform/soc/usb1/1-2/1-2.3/1-2.3:1.0/"
            "host0/target0:0:0"
        )
        self.assertEqual(self.m._deepest_uevent_topology(devpath), "usb:1-2.3")
        payload = (
            b"change@" + devpath.encode("ascii") + b"\0"
            b"ACTION=change\0DEVPATH=" + devpath.encode("ascii") + b"\0"
        )
        event = self.m._parse_uevent(payload)
        self.assertEqual(event.action, "change")
        self.assertEqual(
            event.topology_sha256,
            self.m._topology_sha256("usb:1-2.3"),
        )
        inconsistent = "/devices/platform/usb1/1-2/9-9.3"
        self.assertIsNone(self.m._deepest_uevent_topology(inconsistent))

    def test_uevent_parser_rejects_duplicate_fields_and_field_cap(self):
        duplicate = (
            b"ACTION=add\0ACTION=remove\0"
            b"DEVPATH=/devices/platform/usb1/1-2\0"
        )
        with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "duplicate"):
            self.m._parse_uevent(duplicate)
        mismatched_header = (
            b"add@/devices/platform/usb1/1-2\0"
            b"ACTION=remove\0DEVPATH=/devices/platform/usb1/1-2\0"
        )
        with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "header and fields"):
            self.m._parse_uevent(mismatched_header)
        fields = [b"ACTION=add", b"DEVPATH=/devices/platform/usb1/1-2"]
        fields.extend(
            f"K{index}=v".encode("ascii")
            for index in range(self.m.NETLINK_FIELD_MAX_COUNT)
        )
        with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "field count"):
            self.m._parse_uevent(b"\0".join(fields) + b"\0")

    def test_netlink_drain_event_and_byte_caps_fail_closed(self):
        payload = (
            b"ACTION=change\0"
            b"DEVPATH=/devices/platform/usb1/1-2/1-2.3/1-2.3:1.0\0"
        )
        packet = (payload, [], 0, None)
        environment = self.m._PosixEnvironment()
        environment._monitor_sockets[91] = FakeNetlinkSocket(
            [packet] * (self.m.NETLINK_DRAIN_MAX_EVENTS + 1)
        )
        batch = environment.drain_usb_monitor(91)
        self.assertTrue(batch.overflow)
        self.assertEqual(len(batch.events), self.m.NETLINK_DRAIN_MAX_EVENTS)

        environment._monitor_sockets[92] = FakeNetlinkSocket([packet, packet])
        with mock.patch.object(
            self.m, "NETLINK_DRAIN_MAX_BYTES", len(payload) + 1
        ):
            batch = environment.drain_usb_monitor(92)
        self.assertTrue(batch.overflow)
        self.assertEqual(len(batch.events), 1)

    def test_open_usb_monitor_closes_socket_on_every_setup_fault(self):
        for failure in (
            "setblocking",
            "setsockopt1",
            "setsockopt2",
            "bind",
            "fileno",
        ):
            with self.subTest(failure=failure):
                fake_socket = FakeSetupSocket(failure)
                environment = self.m._PosixEnvironment()
                with mock.patch.object(
                    self.m.socket, "socket", return_value=fake_socket
                ):
                    with self.assertRaisesRegex(
                        self.m.RuntimePrimitiveError, "setup failed closed"
                    ):
                        environment.open_usb_monitor()
                self.assertTrue(fake_socket.closed)
                self.assertEqual(environment._monitor_sockets, {})

    def test_bounded_directory_and_proc_tcp_caps_reject_plus_one(self):
        maximum = 3
        with mock.patch.object(
            os, "scandir", return_value=FakeScandir(["a", "b", "c"])
        ):
            self.assertEqual(
                self.m._bounded_directory_names("/fake", maximum, "fixture"),
                ("a", "b", "c"),
            )
        with mock.patch.object(
            os, "scandir", return_value=FakeScandir(["a", "b", "c", "d"])
        ):
            with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "exceeds cap"):
                self.m._bounded_directory_names("/fake", maximum, "fixture")
        with mock.patch.object(os, "scandir", side_effect=PermissionError("denied")):
            with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "inaccessible"):
                self.m._bounded_directory_names("/fake", maximum, "fixture")

        header = "  sl  local_address rem_address st tx_queue rx_queue tr tm->when retrnsmt uid timeout inode\n"
        row = "0: 00000000:0000 00000000:0000 01 0 0 0 0 0 1\n"
        environment = self.m._PosixEnvironment()
        oversized = (header + row * (self.m.PROC_NET_TCP_MAX_ROWS + 1)).encode()
        with mock.patch.object(environment, "_read_small", return_value=oversized):
            with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "row count"):
                environment.listener_candidates(self.m.ADB_SERVER_SOCKET)

        listener_row = (
            "0: 0100007F:13AD 00000000:0000 0A 0 0 0 1000 0 777\n"
        )

        def bounded_names(path, _maximum, _label):
            return ("1",) if path == "/proc" else ("3", "4", "5")

        with mock.patch.object(
            environment,
            "_read_small",
            return_value=(header + listener_row).encode(),
        ), mock.patch.object(
            self.m,
            "_bounded_directory_names",
            side_effect=bounded_names,
        ), mock.patch.object(
            os,
            "stat",
            return_value=SimpleNamespace(st_uid=os.geteuid()),
        ), mock.patch.object(
            os,
            "readlink",
            return_value="socket:[999]",
        ), mock.patch.object(
            self.m,
            "PROC_TOTAL_PROBES_MAX",
            2,
        ):
            with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "aggregate"):
                environment.listener_candidates(self.m.ADB_SERVER_SOCKET)

    def test_usb_start_closes_monitor_when_initial_drain_raises(self):
        self.env.monitor_error = OSError("fixture drain failure")
        with self.assertRaisesRegex(OSError, "fixture drain failure"):
            self.m.UsbGenerationOwner.start(self.env)
        monitor_fd = next(call[1] for call in self.env.calls if call[0] == "close")
        self.assertIn(monitor_fd, self.env.closed_descriptors)
        self.assertNotIn(monitor_fd, self.env.monitor_fds)

    def test_usb_bind_second_open_failure_closes_sysfs_and_remains_unbound(self):
        topology, _digest, candidate = self.add_usb()
        owner = self.m.UsbGenerationOwner.start(self.env)
        self.env.open_errors[candidate.usbfs_path] = OSError("usbfs open cut")
        with self.assertRaisesRegex(OSError, "usbfs open cut"):
            owner.bind(topology)
        self.assertFalse(owner.bound)
        sysfs_open_index = next(
            index
            for index, call in enumerate(self.env.calls)
            if call[0] == "open_file" and call[1] == candidate.sysfs_path
        )
        sysfs_fd = next(
            call[1]
            for call in self.env.calls[sysfs_open_index + 1 :]
            if call[0] == "close"
        )
        self.assertIn(sysfs_fd, self.env.closed_descriptors)
        owner.close()
        self.assertIn(owner._monitor_fd, self.env.closed_descriptors)

    def test_usb_owner_binds_and_reopens_exact_sysfs_and_usbfs_nodes(self):
        topology, digest, candidate = self.add_usb()
        owner = self.m.UsbGenerationOwner.start(self.env)
        owner.bind(topology)
        self.assertTrue(owner.bound)
        self.assertEqual(self.env.usb_by_digest[digest], (candidate,))
        owner.verify()

    def test_usb_owner_rejects_absent_ambiguous_or_malformed_candidate(self):
        topology, digest, candidate = self.add_usb()
        cases = (
            (),
            (candidate, candidate),
            (
                self.m.UsbCandidate(
                    topology,
                    digest,
                    candidate.sysfs_path,
                    "/dev/bus/usb/001/008",
                    1,
                    7,
                ),
            ),
        )
        for candidates in cases:
            with self.subTest(count=len(candidates)):
                env = self.fresh_env()
                self.copy_usb_nodes(env, candidate)
                env.usb_by_digest[digest] = candidates
                owner = self.m.UsbGenerationOwner.start(env)
                with self.assertRaises(self.m.RuntimePrimitiveError):
                    owner.bind(topology)

    def test_usb_owner_rejects_event_overflow_monitor_mapping_and_fd_drift(self):
        cases = (
            "event",
            "unknown",
            "overflow",
            "closed",
            "mapping",
            "held",
            "path",
            "rdev-path",
        )
        for case in cases:
            with self.subTest(case=case):
                env = self.fresh_env()
                topology, digest, candidate = self.add_usb_to(env)
                owner = self.m.UsbGenerationOwner.start(env)
                owner.bind(topology)
                if case == "event":
                    env.monitor_batches.append(
                        self.m.MonitorBatch((self.m.UsbEvent("remove", digest),), False, True)
                    )
                elif case == "unknown":
                    env.monitor_batches.append(
                        self.m.MonitorBatch((self.m.UsbEvent("mystery", None),), False, True)
                    )
                elif case == "overflow":
                    env.monitor_batches.append(self.m.MonitorBatch((), True, True))
                elif case == "closed":
                    env.monitor_fds.remove(owner._monitor_fd)
                elif case == "mapping":
                    env.usb_by_digest[digest] = ()
                elif case == "held":
                    env.handles[owner._usbfs_fd].identity = self.m.StatSnapshot(
                        **{
                            **env.handles[owner._usbfs_fd].identity.__dict__,
                            "inode": 91919,
                        }
                    )
                elif case == "path":
                    env.add_node(
                        candidate.usbfs_path,
                        mode=stat.S_IFCHR | 0o600,
                        inode=92929,
                        rdev=os.makedev(189, 6),
                    )
                else:
                    original = env.nodes[candidate.usbfs_path].identity
                    env.nodes[candidate.usbfs_path] = FakeNode(
                        b"",
                        self.m.StatSnapshot(
                            **{
                                **original.__dict__,
                                "rdev": os.makedev(189, 7),
                            }
                        ),
                    )
                with self.assertRaises(self.m.RuntimePrimitiveError):
                    owner.verify()

    def test_usb_owner_rejects_wrong_descriptor_types(self):
        topology, digest, candidate = self.add_usb()
        self.env.nodes[candidate.usbfs_path].identity = self.m.StatSnapshot(
            **{
                **self.env.nodes[candidate.usbfs_path].identity.__dict__,
                "mode": stat.S_IFREG | 0o600,
            }
        )
        owner = self.m.UsbGenerationOwner.start(self.env)
        with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "types"):
            owner.bind(topology)

    def test_usb_owner_binds_reviewed_bus_device_to_exact_usbfs_rdev(self):
        self.assertEqual(
            self.m._expected_usbfs_rdev(1, 7),
            os.makedev(self.m.USBFS_MAJOR, 6),
        )
        topology, _digest, candidate = self.add_usb()
        original = self.env.nodes[candidate.usbfs_path].identity
        self.env.nodes[candidate.usbfs_path].identity = self.m.StatSnapshot(
            **{
                **original.__dict__,
                "rdev": os.makedev(self.m.USBFS_MAJOR, 7),
            }
        )
        owner = self.m.UsbGenerationOwner.start(self.env)
        with self.assertRaises(self.m.RuntimePrimitiveError):
            owner.bind(topology)
        for busnum, devnum in ((0, 1), (1, 0), (1, 128), (1000, 1)):
            with self.subTest(busnum=busnum, devnum=devnum):
                with self.assertRaises(self.m.RuntimePrimitiveError):
                    self.m._expected_usbfs_rdev(busnum, devnum)

    def test_capability_is_nonserializable_noncopyable_and_redacted(self):
        capability = self.m.OpeningReadCapability.mint(self.env, self.bind_bundle())
        self.assertEqual(repr(capability), "<OpeningReadCapability process-local>")
        for operation in (
            lambda: pickle.dumps(capability),
            lambda: copy.copy(capability),
            lambda: copy.deepcopy(capability),
        ):
            with self.assertRaises(TypeError):
                operation()

    def test_capability_enforces_opening_then_same_process_read_once(self):
        capability = self.m.OpeningReadCapability.mint(self.env, self.bind_bundle())
        for ordinal in range(1, 7):
            capability.record_opening_ordinal(ordinal)
        self.assertEqual(capability.state, "opening-complete")
        capability.begin_read()
        self.assertEqual(capability.state, "read")
        for ordinal in range(1, 7):
            capability.record_read_ordinal(ordinal)
        self.assertEqual(capability.state, "consumed")
        with self.assertRaises(self.m.RuntimePrimitiveError):
            capability.record_read_ordinal(6)

    def test_capability_rejects_reorder_replay_and_early_handoff(self):
        capability = self.m.OpeningReadCapability.mint(self.env, self.bind_bundle())
        with self.assertRaises(self.m.RuntimePrimitiveError):
            capability.record_opening_ordinal(2)
        capability.record_opening_ordinal(1)
        with self.assertRaises(self.m.RuntimePrimitiveError):
            capability.record_opening_ordinal(1)
        with self.assertRaises(self.m.RuntimePrimitiveError):
            capability.begin_read()

    def test_capability_is_lost_on_process_or_descriptor_change(self):
        for case in ("process", "thread-ident", "thread-reuse", "thread-dead", "descriptor"):
            with self.subTest(case=case):
                env = self.fresh_env()
                bundle = self.bind_bundle_for(env)
                capability = self.m.OpeningReadCapability.mint(env, bundle)
                if case == "process":
                    env.process_pid += 1
                elif case == "thread-ident":
                    env.thread_ident += 1
                elif case == "thread-reuse":
                    env.thread_alive = False
                    env.thread_object = object()
                    env.thread_alive = True
                elif case == "thread-dead":
                    env.thread_alive = False
                else:
                    env.capabilities.clear()
                with self.assertRaises(self.m.RuntimePrimitiveError):
                    capability.record_opening_ordinal(1)

    def test_concrete_capability_rejects_closed_fd_number_recycled_to_other_node(self):
        fifo = self.m.StatSnapshot(
            44, 55_001, stat.S_IFIFO | 0o600, 1, 1000, 1000, 0, 1, 1
        )
        token = object()
        handle = self.m.CapabilityDescriptor(
            30, 31, fifo, fifo, os.O_RDONLY, os.O_WRONLY, token
        )
        environment = self.m._PosixEnvironment()
        environment._capabilities[token] = handle

        def os_value(value):
            return SimpleNamespace(
                st_dev=value.device,
                st_ino=value.inode,
                st_mode=value.mode,
                st_nlink=value.links,
                st_uid=value.uid,
                st_gid=value.gid,
                st_size=value.size,
                st_mtime_ns=value.mtime_ns,
                st_ctime_ns=value.ctime_ns,
                st_rdev=value.rdev,
            )

        with mock.patch.object(
            os, "fstat", side_effect=[os_value(fifo), os_value(fifo)]
        ), mock.patch.object(
            self.m.fcntl,
            "fcntl",
            side_effect=[os.O_RDONLY, os.O_WRONLY],
        ):
            self.assertTrue(environment.capability_alive(handle))
        recycled = self.m.StatSnapshot(
            1,
            3,
            stat.S_IFCHR | 0o666,
            1,
            0,
            0,
            0,
            2,
            2,
            os.makedev(1, 3),
        )
        with mock.patch.object(
            os,
            "fstat",
            side_effect=[os_value(recycled), os_value(fifo)],
        ), mock.patch.object(
            self.m.fcntl,
            "fcntl",
            side_effect=[os.O_RDONLY, os.O_WRONLY],
        ):
            self.assertFalse(environment.capability_alive(handle))
        with mock.patch.object(
            os, "fstat", side_effect=[os_value(fifo), os_value(fifo)]
        ), mock.patch.object(
            self.m.fcntl,
            "fcntl",
            side_effect=[os.O_WRONLY, os.O_WRONLY],
        ):
            self.assertFalse(environment.capability_alive(handle))

    def test_durable_bytes_and_arbitrary_hashes_cannot_mint_capability(self):
        durable = b'{"intent":"complete","sha256":"' + b"0" * 64 + b'"}\n'
        with self.assertRaises(self.m.RuntimePrimitiveError):
            self.m._OwnerBundle(durable, None, None, None, None)
        with self.assertRaises(self.m.RuntimePrimitiveError):
            self.m.OpeningReadCapability(durable, self.env, durable)
        self.assertNotIn("durable", str(self.m.OpeningReadCapability.mint.__signature__) if hasattr(self.m.OpeningReadCapability.mint, "__signature__") else "")
        plan = self.m.render_plan()
        self.assertFalse(plan["process_capability"]["python_factory_inaccessible"])
        self.assertTrue(plan["process_capability"]["future_closed_call_graph_required"])
        self.assertTrue(callable(self.m.OpeningReadCapability.mint))

    def test_owner_bundle_rejects_noop_facades_and_mixed_environments(self):
        class Facade:
            bound = True

            def verify(self):
                return None

            def sample(self):
                return None

        facade = Facade()
        with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "live exact owner"):
            self.m._OwnerBundle(
                self.m._BUNDLE_SEAL,
                facade,
                facade,
                facade,
                facade,
            )
        first = self.bind_bundle()
        second_env = self.fresh_env()
        second_adb = self.m.AdbClientOwner.bind(second_env)
        with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "live exact owner"):
            self.m._OwnerBundle(
                self.m._BUNDLE_SEAL,
                second_adb,
                first.server,
                first.clock,
                first.usb,
            )

        closed_env = self.fresh_env()
        closed_adb = self.m.AdbClientOwner.bind(closed_env)
        closed_server = self.m.AdbServerOwner.bind(closed_env, closed_adb)
        closed_clock = self.m.HostClockOwner.bind(closed_env)
        topology, _digest, _candidate = self.add_usb_to(closed_env)
        closed_usb = self.m.UsbGenerationOwner.start(closed_env)
        closed_usb.bind(topology)
        closed_adb.close()
        with self.assertRaises(self.m.RuntimePrimitiveError):
            self.m._OwnerBundle(
                self.m._BUNDLE_SEAL,
                closed_adb,
                closed_server,
                closed_clock,
                closed_usb,
            )

    def test_capability_rejects_environment_distinct_from_exact_owner_bundle(self):
        bundle = self.bind_bundle()
        foreign_environment = self.fresh_env()
        with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "process-local owner"):
            self.m.OpeningReadCapability.mint(foreign_environment, bundle)

    def test_capability_validates_process_before_pipe_and_closes_late_mint_cut(self):
        environment = self.fresh_env()
        bundle = self.bind_bundle_for(environment)
        environment.thread_alive = False
        before = len(environment.calls)
        with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "not live and exact"):
            self.m.OpeningReadCapability.mint(environment, bundle)
        names = [call[0] for call in environment.calls[before:]]
        self.assertIn("process_identity", names)
        self.assertNotIn("new_capability_descriptor", names)

        environment = self.fresh_env()
        bundle = self.bind_bundle_for(environment)
        original = environment.process_identity()
        environment.process_identity_values = [
            original,
            self.m.ProcessThreadIdentity(
                original.pid,
                original.thread_ident,
                object(),
                True,
            ),
        ]
        with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "changed during mint"):
            self.m.OpeningReadCapability.mint(environment, bundle)
        self.assertEqual(environment.capabilities, {})
        self.assertTrue(
            any(call[0] == "close_capability" for call in environment.calls)
        )

        environment = self.fresh_env()
        bundle = self.bind_bundle_for(environment)
        environment.capability_alive_override = False
        with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "changed during mint"):
            self.m.OpeningReadCapability.mint(environment, bundle)
        self.assertEqual(environment.capabilities, {})

    def test_owner_bundle_rejects_server_bound_to_other_adb_generation(self):
        bundle = self.bind_bundle()
        bundle.server._adb_identity = self.m.StatSnapshot(
            **{
                **bundle.adb.identity.__dict__,
                "inode": bundle.adb.identity.inode + 1,
            }
        )
        with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "live exact owner"):
            self.m._OwnerBundle(
                self.m._BUNDLE_SEAL,
                bundle.adb,
                bundle.server,
                bundle.clock,
                bundle.usb,
            )

    def test_capability_revalidates_all_four_owners_at_each_transition(self):
        bundle = self.bind_bundle()
        capability = self.m.OpeningReadCapability.mint(self.env, bundle)
        before = len(self.env.calls)
        capability.record_opening_ordinal(1)
        names = {call[0] for call in self.env.calls[before:]}
        self.assertTrue(
            {
                "process_identity",
                "capability_alive",
                "listener_candidates",
                "clock_snapshot",
                "drain_usb_monitor",
                "usb_candidates",
            }.issubset(names)
        )

    def test_execveat_candidate_is_false_gate_before_fork(self):
        with mock.patch.object(os, "fork", side_effect=AssertionError("fork reached")):
            with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "inactive"):
                self.m._execveat_capture(9, 1, "RFCM0000000")
        environment = self.m._PosixEnvironment()
        with mock.patch.object(
            self.m, "_execveat_capture", side_effect=AssertionError("exec reached")
        ):
            with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "inactive"):
                environment.execute_fixed_adb(9, 1, "RFCM0000000")
        with mock.patch.object(
            self.m.ctypes, "CDLL", side_effect=AssertionError("libc reached")
        ):
            with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "inactive"):
                self.m._execveat_child(
                    9,
                    (self.m.ADB_PATH, "version"),
                    10,
                    11,
                    31337,
                )

    @unittest.skipUnless(hasattr(os, "fork"), "requires a Linux fork child")
    def test_close_range_closes_inheritable_high_fd_above_lowered_soft_limit(self):
        base_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
        high_fd = fcntl.fcntl(base_fd, fcntl.F_DUPFD, 256)
        os.set_inheritable(high_fd, True)
        report_read, report_write = os.pipe2(os.O_CLOEXEC)
        pid = os.fork()
        if pid == 0:
            try:
                os.close(report_read)
                os.dup2(report_write, 3, inheritable=True)
                _soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
                if hard != resource.RLIM_INFINITY and hard < 64:
                    os.write(3, b"SKIP")
                    os._exit(0)
                resource.setrlimit(resource.RLIMIT_NOFILE, (64, hard))
                self.m._close_child_fds_from_four(
                    ctypes.CDLL(None, use_errno=True)
                )
                try:
                    os.fstat(high_fd)
                except OSError:
                    os.write(3, b"CLOSED")
                    os._exit(0)
                os.write(3, b"SURVIVED")
                os._exit(1)
            except BaseException:
                try:
                    os.write(3, b"ERROR")
                except OSError:
                    pass
                os._exit(2)
        os.close(report_write)
        try:
            payload = os.read(report_read, 32)
            waited, status = os.waitpid(pid, 0)
            self.assertEqual(waited, pid)
            self.assertEqual(os.waitstatus_to_exitcode(status), 0)
            self.assertIn(payload, (b"CLOSED", b"SKIP"))
        finally:
            os.close(report_read)
            os.close(high_fd)
            os.close(base_fd)

    @unittest.skipUnless(hasattr(os, "fork"), "requires a Linux fork child")
    def test_capture_pipes_are_cloexec_and_only_parent_reads_become_nonblocking(self):
        operations = self.m._PosixCaptureOps()
        stdout_read, stdout_write = operations.pipe2()
        stderr_read, stderr_write = operations.pipe2()
        descriptors = (stdout_read, stdout_write, stderr_read, stderr_write)
        try:
            for descriptor in descriptors:
                self.assertTrue(
                    fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
                )
                self.assertFalse(
                    fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_NONBLOCK
                )
            operations.set_nonblocking(stdout_read)
            operations.set_nonblocking(stderr_read)
            self.assertTrue(fcntl.fcntl(stdout_read, fcntl.F_GETFL) & os.O_NONBLOCK)
            self.assertTrue(fcntl.fcntl(stderr_read, fcntl.F_GETFL) & os.O_NONBLOCK)
            self.assertFalse(fcntl.fcntl(stdout_write, fcntl.F_GETFL) & os.O_NONBLOCK)
            self.assertFalse(fcntl.fcntl(stderr_write, fcntl.F_GETFL) & os.O_NONBLOCK)

            pid = os.fork()
            if pid == 0:
                try:
                    os.dup2(stdout_write, 1, inheritable=True)
                    os.dup2(stderr_write, 2, inheritable=True)
                    stdout_flags = fcntl.fcntl(1, fcntl.F_GETFL)
                    stderr_flags = fcntl.fcntl(2, fcntl.F_GETFL)
                    os._exit(
                        1
                        if (stdout_flags | stderr_flags) & os.O_NONBLOCK
                        else 0
                    )
                except BaseException:
                    os._exit(2)
            waited, status = os.waitpid(pid, 0)
            self.assertEqual(waited, pid)
            self.assertEqual(os.waitstatus_to_exitcode(status), 0)
        finally:
            for descriptor in descriptors:
                try:
                    os.close(descriptor)
                except OSError:
                    pass

    def run_fake_capture(self, operations):
        with mock.patch.object(
            self.m, "_operational_gates", return_value={"test-only": True}
        ):
            return self.m._execveat_capture_with_ops(
                9, 1, "RFCM0000000", operations
            )

    def test_direct_child_exit_has_fixed_descendant_held_pipe_deadline(self):
        operations = FakeCaptureOps(child_initially_exited=True)
        operations.select_plan = []  # A hostile descendant keeps both writers open.
        result = self.run_fake_capture(operations)
        self.assertTrue(result.post_child_drain_expired)
        self.assertFalse(result.timed_out)
        self.assertEqual(operations.successful_reaps, 1)
        self.assertEqual(sorted(operations.closed), sorted(operations.allocated))
        self.assertGreaterEqual(operations.clock_value, self.m.POST_CHILD_DRAIN_NS)

    def test_first_child_completion_observed_after_execution_deadline_is_timeout(self):
        operations = FakeCaptureOps(child_initially_exited=False)
        operations.clock_step = 0
        operations.select_delay_ns = 11 * 1_000_000_000
        operations.child_exits_during_select = True
        result = self.run_fake_capture(operations)
        self.assertTrue(result.timed_out)
        self.assertFalse(result.post_child_drain_expired)
        self.assertEqual(operations.successful_reaps, 1)
        self.assertEqual(set(operations.closed), operations.allocated)

    def test_waitpid_deschedule_uses_fresh_post_wait_boottime_for_completion(self):
        operations = FakeCaptureOps(child_initially_exited=True)
        operations.clock_step = 0
        operations.clock_values = [0, 9_900_000_000]
        operations.waitpid_nonblocking_delay_ns = 200_000_000
        result = self.run_fake_capture(operations)
        self.assertTrue(result.timed_out)
        self.assertEqual(operations.successful_reaps, 1)
        self.assertGreaterEqual(operations.clock_value, 10_100_000_000)
        self.assertEqual(set(operations.closed), operations.allocated)

    def test_delayed_eof_after_post_child_drain_deadline_is_not_accepted(self):
        operations = FakeCaptureOps(child_initially_exited=True)
        operations.clock_step = 0
        operations.select_delay_ns = self.m.POST_CHILD_DRAIN_NS + 1
        result = self.run_fake_capture(operations)
        self.assertFalse(result.timed_out)
        self.assertTrue(result.post_child_drain_expired)
        self.assertEqual(operations.successful_reaps, 1)
        self.assertEqual(set(operations.closed), operations.allocated)

    def test_capture_normal_eof_reaps_child_once_and_closes_every_fd_once(self):
        operations = FakeCaptureOps(child_initially_exited=True)
        result = self.run_fake_capture(operations)
        self.assertFalse(result.post_child_drain_expired)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(operations.successful_reaps, 1)
        self.assertEqual(len(operations.closed), len(set(operations.closed)))
        self.assertEqual(set(operations.closed), operations.allocated)
        self.assertTrue(operations.selector_value.closed)

    def test_capture_allocation_and_runtime_failures_cleanup_exactly_once(self):
        cases = (
            "pipe1",
            "pipe2",
            "fork",
            "set_nonblocking1",
            "set_nonblocking2",
            "pidfd",
            "selector",
            "register1",
            "register2",
            "select",
            "read",
            "waitpid",
        )
        for failure in cases:
            with self.subTest(failure=failure):
                child_exists = failure not in {"pipe1", "pipe2", "fork"}
                operations = FakeCaptureOps(
                    fail_at=failure,
                    child_initially_exited=False,
                )
                if failure == "read":
                    operations.select_plan = [[10]]
                with self.assertRaises((OSError, self.m.RuntimePrimitiveError)):
                    self.run_fake_capture(operations)
                self.assertEqual(
                    operations.successful_reaps,
                    1 if child_exists else 0,
                )
                self.assertEqual(len(operations.closed), len(set(operations.closed)))
                self.assertEqual(set(operations.closed), operations.allocated)

    def test_capture_timeout_terms_kills_reaps_once_then_bounds_pipe_drain(self):
        operations = FakeCaptureOps(child_initially_exited=False)
        operations.select_plan = []
        operations.clock_step = 6 * 1_000_000_000
        result = self.run_fake_capture(operations)
        self.assertTrue(result.timed_out)
        self.assertTrue(result.term_sent)
        self.assertTrue(result.kill_sent)
        self.assertTrue(result.post_child_drain_expired)
        self.assertEqual(operations.signals, [signal.SIGTERM, signal.SIGKILL])
        self.assertEqual(operations.successful_reaps, 1)
        self.assertEqual(set(operations.closed), operations.allocated)

    def test_selector_close_error_still_closes_all_descriptors(self):
        operations = FakeCaptureOps(
            fail_at="selector_close", child_initially_exited=True
        )
        result = self.run_fake_capture(operations)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(operations.successful_reaps, 1)
        self.assertEqual(set(operations.closed), operations.allocated)

    def test_pidfd_signal_failure_uses_unreaped_direct_child_cleanup_fallback(self):
        operations = FakeCaptureOps(
            fail_at="pidfd_signal", child_initially_exited=False
        )
        operations.select_plan = []
        operations.clock_step = 6 * 1_000_000_000
        result = self.run_fake_capture(operations)
        self.assertTrue(result.timed_out)
        self.assertTrue(result.kill_sent)
        self.assertIn(signal.SIGKILL, operations.kills)
        self.assertEqual(operations.successful_reaps, 1)
        self.assertEqual(set(operations.closed), operations.allocated)

    def test_capture_overflow_kills_and_reaps_live_direct_child_once(self):
        operations = FakeCaptureOps(child_initially_exited=False)
        operations.select_plan = [[10]]
        operations.read_plan[10] = [b"x" * (self.m.MAX_OUTPUT_BYTES + 1)]
        with self.assertRaisesRegex(self.m.RuntimePrimitiveError, "exceeds 64 KiB"):
            self.run_fake_capture(operations)
        self.assertEqual(operations.successful_reaps, 1)
        self.assertIn(signal.SIGKILL, operations.signals)
        self.assertEqual(set(operations.closed), operations.allocated)

    def test_source_has_exact_file_exec_and_no_generic_process_api(self):
        self.assertIn("libc.execveat", self.source)
        self.assertIn("AT_EMPTY_PATH", self.source)
        self.assertIn("PR_SET_PDEATHSIG", self.source)
        self.assertNotIn("subprocess", self.source)
        self.assertNotIn("os.system", self.source)
        self.assertNotIn("Popen", self.source)
        self.assertNotIn("/proc/self/fd", self.source)
        self.assertNotIn("shell=True", self.source)

    def test_fake_environment_was_the_only_test_owner_backend(self):
        source = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden = {
            "Popen",
            "run",
            "check_call",
            "check_output",
            "system",
            "socket",
        }
        invoked = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue(forbidden.isdisjoint(invoked))

    def fresh_env(self):
        env = FakeEnvironment(self.m)
        env.add_node(
            self.m.ADB_PATH,
            self.adb_payload,
            mode=stat.S_IFREG | 0o755,
            inode=1200,
        )
        return env

    def copy_usb_nodes(self, environment, candidate):
        environment.add_node(
            candidate.sysfs_path,
            mode=stat.S_IFDIR | 0o755,
            inode=2200,
            links=2,
        )
        environment.add_node(
            candidate.usbfs_path,
            mode=stat.S_IFCHR | 0o600,
            inode=2201,
            rdev=os.makedev(189, 6),
        )

    def add_usb_to(self, environment, topology="usb:1-2"):
        digest = self.m._topology_sha256(topology)
        candidate = self.m.UsbCandidate(
            topology,
            digest,
            "/sys/devices/platform/test/usb1/1-2",
            "/dev/bus/usb/001/007",
            1,
            7,
        )
        self.copy_usb_nodes(environment, candidate)
        environment.usb_by_digest[digest] = (candidate,)
        return topology, digest, candidate

    def bind_bundle_for(self, environment):
        adb = self.m.AdbClientOwner.bind(environment)
        server = self.m.AdbServerOwner.bind(environment, adb)
        clock = self.m.HostClockOwner.bind(environment)
        topology, _digest, _candidate = self.add_usb_to(environment)
        usb = self.m.UsbGenerationOwner.start(environment)
        usb.bind(topology)
        return self.m._OwnerBundle.create(adb, server, clock, usb)


def json_load(payload):
    import json

    return json.loads(payload)


if __name__ == "__main__":
    unittest.main()
