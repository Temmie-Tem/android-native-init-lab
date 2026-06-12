from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


smoke = load_script("workspace/public/src/scripts/revalidation/a90_ncm_transport_smoke.py")


class A90NcmTransportSmokeTests(unittest.TestCase):
    def test_parse_sizes_accepts_decimal_hex_and_empty_items(self) -> None:
        self.assertEqual(smoke.parse_sizes("1, 0x20,, 3"), [1, 32, 3])
        self.assertEqual(smoke.parse_sizes(" , "), [])
        with self.assertRaises(ValueError):
            smoke.parse_sizes("1,bad")

    def test_write_pattern_file_is_deterministic_and_reports_sha(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "a" / "pattern.bin"
            second = Path(tmp) / "b" / "pattern.bin"
            sha1 = smoke.write_pattern_file(first, 33)
            sha2 = smoke.write_pattern_file(second, 33)

            self.assertEqual(first.stat().st_size, 33)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(sha1, sha2)
            self.assertEqual(sha1, hashlib.sha256(first.read_bytes()).hexdigest())
            self.assertIn(b"A90-NCM-BENCHMARK", first.read_bytes())

    def test_shutil_which_searches_path_and_requires_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            non_exec = root / "tool"
            non_exec.write_text("#!/bin/sh\n", encoding="utf-8")
            with mock.patch.dict(smoke.os.environ, {"PATH": str(root)}):
                self.assertEqual(smoke.shutil_which("tool"), "")
            non_exec.chmod(0o700)
            with mock.patch.dict(smoke.os.environ, {"PATH": str(root)}):
                self.assertEqual(smoke.shutil_which("tool"), str(non_exec))
            with mock.patch.dict(smoke.os.environ, {"PATH": ""}):
                self.assertEqual(smoke.shutil_which("tool"), "")

    def test_maybe_force_nm_repair_is_noop_without_nmcli(self) -> None:
        with mock.patch.object(smoke, "shutil_which", return_value=""), \
                mock.patch.object(smoke, "run_command") as run_command, \
                mock.patch.object(smoke, "write_step") as write_step:
            smoke.maybe_force_nm_repair("profile", mock.Mock(), [])
        run_command.assert_not_called()
        write_step.assert_not_called()

    def test_maybe_force_nm_repair_records_down_and_delete_steps(self) -> None:
        store = mock.Mock()
        steps: list[dict[str, object]] = []
        result = {"ok": True, "rc": 0}
        with mock.patch.object(smoke, "shutil_which", return_value="/usr/bin/nmcli"), \
                mock.patch.object(smoke, "run_command", return_value=result) as run_command, \
                mock.patch.object(smoke, "write_step") as write_step:
            smoke.maybe_force_nm_repair("a90-profile", store, steps)

        self.assertEqual(
            [call.args[0] for call in run_command.call_args_list],
            [["nmcli", "con", "down", "a90-profile"], ["nmcli", "con", "delete", "a90-profile"]],
        )
        self.assertEqual([call.args[2] for call in write_step.call_args_list], ["force-nm-repair-down", "force-nm-repair-delete"])
        self.assertTrue(all(call.args[3] is result for call in write_step.call_args_list))

    def test_stream_remote_to_host_returns_unreachable_without_receiver(self) -> None:
        transfer = SimpleNamespace(ensure_device_reachable=lambda: False, reason="no-link")
        with mock.patch.object(smoke.ncm, "TcpArchiveReceiver") as receiver:
            result = smoke.stream_remote_to_host(
                transfer,
                mock.Mock(),
                [],
                label="one",
                remote_path="/cache/file",
                expected_sha256="sha",
                timeout=1.0,
            )
        receiver.assert_not_called()
        self.assertEqual(result, {"ok": False, "reason": "no-link", "method": "ncm-cat-nc", "elapsed_sec": 0.0})

    def test_stream_remote_to_host_success_checks_nc_rc_receiver_sha_and_records_compact_step(self) -> None:
        class Receiver:
            def __init__(self, path, *, bind_host, bind_ifname, timeout):
                self.path = path
                self.bind_host = bind_host
                self.bind_ifname = bind_ifname
                self.timeout = timeout
                self.port = 4567
                self.result = {"ok": True, "sha256": "expected"}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with tempfile.TemporaryDirectory() as tmp:
            store = mock.Mock()
            store.path.side_effect = lambda name: Path(tmp) / name
            steps: list[dict[str, object]] = []
            transfer = SimpleNamespace(
                ensure_device_reachable=lambda: True,
                reason="ok",
                host_link_local="fe80::1",
                ifname="enx0",
                device_ifname="ncm0",
            )
            step = {"ok": True, "stdout": "fast_upload_raw.nc_rc=0\n", "stderr": ""}
            with mock.patch.object(smoke.ncm, "TcpArchiveReceiver", Receiver), \
                    mock.patch.object(smoke, "run_step", return_value=step) as run_step, \
                    mock.patch.object(smoke.ncm, "write_compact_step") as compact, \
                    mock.patch.object(smoke.time, "monotonic", side_effect=[10.0, 12.345]):
                result = smoke.stream_remote_to_host(
                    transfer,
                    store,
                    steps,
                    label="bench",
                    remote_path="/cache/remote.bin",
                    expected_sha256="expected",
                    timeout=7.0,
                )

        self.assertTrue(result["ok"])
        self.assertEqual(result["reason"], "ok")
        self.assertEqual(result["device_nc_rc"], "0")
        self.assertEqual(result["receiver"], {"ok": True, "sha256": "expected"})
        self.assertEqual(result["elapsed_sec"], 2.345)
        self.assertEqual(result["host_ifname"], "enx0")
        self.assertEqual(result["host_link_local"], "fe80::1")
        self.assertIn("/cache/bin/busybox nc -w 1 fe80::1%ncm0 4567", run_step.call_args.args[3][-1])
        self.assertEqual(compact.call_args.args[2], "bench-raw-upload-result")
        self.assertEqual(compact.call_args.kwargs["rc"], 0)

    def test_stream_remote_to_host_marks_failed_on_bad_nc_rc_or_sha(self) -> None:
        class Receiver:
            port = 1111
            result = {"ok": True, "sha256": "wrong"}

            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        store = mock.Mock()
        store.path.return_value = Path("/tmp/upload.bin")
        transfer = SimpleNamespace(
            ensure_device_reachable=lambda: True,
            reason="ok",
            host_link_local="fe80::1",
            ifname="enx0",
            device_ifname="ncm0",
        )
        with mock.patch.object(smoke.ncm, "TcpArchiveReceiver", Receiver), \
                mock.patch.object(smoke, "run_step", return_value={"ok": True, "stdout": "fast_upload_raw.nc_rc=1\n", "stderr": ""}), \
                mock.patch.object(smoke.ncm, "write_compact_step") as compact, \
                mock.patch.object(smoke.time, "monotonic", side_effect=[1.0, 1.5]):
            result = smoke.stream_remote_to_host(
                transfer,
                store,
                [],
                label="bench",
                remote_path="/cache/remote.bin",
                expected_sha256="expected",
                timeout=2.0,
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "upload-or-sha-failed")
        self.assertEqual(result["device_nc_rc"], "1")
        self.assertEqual(compact.call_args.kwargs["rc"], 1)


if __name__ == "__main__":
    unittest.main()
