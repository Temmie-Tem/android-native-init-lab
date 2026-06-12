"""Regression tests for a90harness.device command client wrappers."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

from _loader import load_harness

broker_stub = types.ModuleType("a90_broker")
broker_stub.PROTO = "A90B1"
broker_stub.connect_and_call = lambda *_args, **_kwargs: {}
sys.modules["a90_broker"] = broker_stub

device = load_harness("device")


class DeviceClientTests(unittest.TestCase):
    def test_init_validates_backend_and_broker_socket(self):
        with self.assertRaisesRegex(ValueError, "unsupported device backend"):
            device.DeviceClient(backend="serial")
        with self.assertRaisesRegex(ValueError, "broker backend requires broker_socket"):
            device.DeviceClient(backend="broker")

    def test_metadata_serializes_direct_and_broker_configuration(self):
        direct = device.DeviceClient(host="host", port=12, timeout=3.5, client_id="cid")
        self.assertEqual(
            direct.metadata(),
            {
                "backend": "direct",
                "host": "host",
                "port": 12,
                "timeout": 3.5,
                "broker_socket": None,
                "client_id": "cid",
            },
        )

        broker = device.DeviceClient(
            backend="broker",
            broker_socket=Path("/tmp/a90.sock"),
            client_id="broker-cid",
        )
        self.assertEqual(broker.metadata()["broker_socket"], "/tmp/a90.sock")
        self.assertEqual(broker.metadata()["backend"], "broker")

    def test_run_direct_delegates_to_cmdv1_and_records_success(self):
        calls = []

        class FakeResult:
            rc = 0
            status = "ok"
            text = "A90 output\n"

        def fake_run_cmdv1_command(host, port, timeout, command, *, retry_unsafe):
            calls.append((host, port, timeout, command, retry_unsafe))
            return FakeResult()

        original = device.run_cmdv1_command
        device.run_cmdv1_command = fake_run_cmdv1_command
        try:
            client = device.DeviceClient(host="127.0.0.2", port=111, timeout=9.0)
            record, output = client.run(
                "status-check",
                ["status"],
                timeout=2.5,
                retry_unsafe=True,
                transcript="transcript.txt",
            )
        finally:
            device.run_cmdv1_command = original

        self.assertEqual(calls, [("127.0.0.2", 111, 2.5, ["status"], True)])
        self.assertTrue(record.ok)
        self.assertEqual(record.name, "status-check")
        self.assertEqual(record.command, ["status"])
        self.assertEqual(record.rc, 0)
        self.assertEqual(record.status, "ok")
        self.assertEqual(record.transcript, "transcript.txt")
        self.assertEqual(record.error, "")
        self.assertEqual(output, "A90 output\n")

    def test_run_direct_marks_non_ok_status_as_failed_without_exception(self):
        class FakeResult:
            rc = 7
            status = "busy"
            text = "busy\n"

        original = device.run_cmdv1_command
        device.run_cmdv1_command = lambda *args, **kwargs: FakeResult()
        try:
            record, output = device.DeviceClient().run("busy", ["wifi", "scan"])
        finally:
            device.run_cmdv1_command = original

        self.assertFalse(record.ok)
        self.assertEqual(record.rc, 7)
        self.assertEqual(record.status, "busy")
        self.assertEqual(record.error, "")
        self.assertEqual(output, "busy\n")

    def test_run_broker_builds_protocol_payload_and_records_success(self):
        calls = []

        def fake_connect_and_call(socket_path, payload, timeout):
            calls.append((socket_path, payload, timeout))
            return {"rc": 0, "status": "ok", "text": "broker output\n"}

        original = device.connect_and_call
        device.connect_and_call = fake_connect_and_call
        try:
            client = device.DeviceClient(
                backend="broker",
                broker_socket=Path("/tmp/a90-broker.sock"),
                client_id="cid-1",
                timeout=4.0,
            )
            record, output = client.run("version", ["version"], timeout=1.25)
        finally:
            device.connect_and_call = original

        self.assertEqual(output, "broker output\n")
        self.assertTrue(record.ok)
        socket_path, payload, timeout = calls[0]
        self.assertEqual(socket_path, Path("/tmp/a90-broker.sock"))
        self.assertEqual(timeout, 6.25)
        self.assertEqual(payload["proto"], "A90B1")
        self.assertRegex(payload["id"], r"^version-[0-9a-f]+$")
        self.assertEqual(payload["client_id"], "cid-1")
        self.assertEqual(payload["op"], "cmd")
        self.assertEqual(payload["argv"], ["version"])
        self.assertEqual(payload["timeout_ms"], 1250)

    def test_run_broker_preserves_error_and_non_int_rc(self):
        def fake_connect_and_call(socket_path, payload, timeout):
            return {"rc": "1", "status": "failed", "text": "", "error": "broker failed"}

        original = device.connect_and_call
        device.connect_and_call = fake_connect_and_call
        try:
            client = device.DeviceClient(backend="broker", broker_socket=Path("/tmp/a90.sock"))
            record, output = client.run("cmd", ["cmd"])
        finally:
            device.connect_and_call = original

        self.assertFalse(record.ok)
        self.assertIsNone(record.rc)
        self.assertEqual(record.status, "failed")
        self.assertEqual(record.error, "broker failed")
        self.assertEqual(output, "broker failed\n")

    def test_run_catches_backend_exception_as_command_record(self):
        def boom(*args, **kwargs):
            raise OSError("socket down")

        original = device.run_cmdv1_command
        device.run_cmdv1_command = boom
        try:
            record, output = device.DeviceClient().run("status", ["status"])
        finally:
            device.run_cmdv1_command = original

        self.assertFalse(record.ok)
        self.assertIsNone(record.rc)
        self.assertEqual(record.status, "exception")
        self.assertEqual(record.error, "OSError: socket down")
        self.assertEqual(output, "OSError: socket down\n")

    def test_exclusive_context_is_reentrant_for_same_client(self):
        class FakeResult:
            rc = 0
            status = "ok"
            text = "nested ok\n"

        original = device.run_cmdv1_command
        device.run_cmdv1_command = lambda *args, **kwargs: FakeResult()
        try:
            client = device.DeviceClient()
            with client.exclusive():
                with client.exclusive():
                    record, output = client.run("noop", ["noop"])
        finally:
            device.run_cmdv1_command = original

        self.assertTrue(record.ok)
        self.assertEqual(record.status, "ok")
        self.assertEqual(output, "nested ok\n")


if __name__ == "__main__":
    unittest.main()
