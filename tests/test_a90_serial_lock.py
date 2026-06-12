"""Regression tests for host-side A90 serial bridge locking."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_revalidation

serial_lock = load_revalidation("a90_serial_lock.py")


class SerialLockTests(unittest.TestCase):
    def test_lock_path_uses_explicit_path_or_repo_default(self):
        explicit = Path("/tmp/a90.lock")
        self.assertEqual(serial_lock.lock_path(explicit), explicit)
        default = serial_lock.lock_path()
        self.assertTrue(str(default).endswith(serial_lock.DEFAULT_LOCK_REL))

    def test_default_timeout_prefers_argument_and_reads_env(self):
        with mock.patch.dict(os.environ, {serial_lock.ENV_LOCK_TIMEOUT_SEC: "9.5"}):
            self.assertEqual(serial_lock.default_timeout(1.25), 1.25)
            self.assertEqual(serial_lock.default_timeout(None), 9.5)
        with mock.patch.dict(os.environ, {serial_lock.ENV_LOCK_TIMEOUT_SEC: ""}):
            self.assertIsNone(serial_lock.default_timeout(None))
        with mock.patch.dict(os.environ, {serial_lock.ENV_LOCK_TIMEOUT_SEC: "-3"}):
            self.assertEqual(serial_lock.default_timeout(None), 0.0)

    def test_context_writes_metadata_and_clears_file_on_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "bridge.lock"
            with serial_lock.SerialBridgeLock(path=path, purpose="unit-test", timeout_sec=0.1) as lock:
                self.assertEqual(lock.path, path)
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["pid"], os.getpid())
                self.assertEqual(payload["purpose"], "unit-test")
                self.assertIsInstance(payload["started_monotonic"], float)
                self.assertIsNotNone(lock.handle)

            self.assertEqual(path.read_text(encoding="utf-8"), "")
            self.assertIsNone(lock.handle)

    def test_busy_lock_raises_and_closes_contender_handle(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bridge.lock"
            original_sleep = serial_lock.time.sleep
            serial_lock.time.sleep = lambda _sec: None
            try:
                with serial_lock.SerialBridgeLock(path=path, purpose="owner", timeout_sec=1.0):
                    contender = serial_lock.SerialBridgeLock(path=path, purpose="contender", timeout_sec=0.0)
                    with self.assertRaisesRegex(serial_lock.SerialBridgeLockBusy, "lock busy"):
                        contender.__enter__()
                    self.assertIsNone(contender.handle)
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(payload["purpose"], "owner")
            finally:
                serial_lock.time.sleep = original_sleep

    def test_exit_is_noop_when_never_entered_or_failed_before_handle(self):
        lock = serial_lock.SerialBridgeLock(path="/tmp/unused-a90-lock", timeout_sec=0)
        lock.__exit__(None, None, None)
        self.assertIsNone(lock.handle)


if __name__ == "__main__":
    unittest.main()
