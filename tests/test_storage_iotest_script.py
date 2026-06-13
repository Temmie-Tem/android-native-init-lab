from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_revalidation


storage_iotest = load_revalidation("storage_iotest.py")


def base_args(**overrides):
    values = {
        "bridge_host": "127.0.0.1",
        "bridge_port": 54321,
        "device_ip": "192.168.7.2",
        "toybox": "/cache/bin/toybox",
        "test_root": "/mnt/sdext/a90/test-io",
        "run_id": "run-01",
        "bridge_timeout": 45.0,
        "device_protocol": "auto",
        "busy_retries": 3,
        "busy_retry_sleep": 3.0,
        "menu_hide_sleep": 3.0,
        "connect_timeout": 5.0,
        "transfer_port": storage_iotest.DEFAULT_TRANSFER_PORT,
        "transfer_delay": 0.0,
        "transfer_timeout": 120.0,
        "verbose": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class PureHelpers(unittest.TestCase):
    def test_parse_sizes_accepts_plain_k_m_and_rejects_empty_or_nonpositive(self) -> None:
        self.assertEqual(storage_iotest.parse_sizes("1, 4k,2M"), [1, 4096, 2 * 1024 * 1024])
        self.assertEqual(storage_iotest.parse_sizes(",,8,"), [8])

        for text in ("", "0", "-1", "1,0"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    storage_iotest.parse_sizes(text)

    def test_deterministic_bytes_and_hash_are_stable_and_seed_sensitive(self) -> None:
        first = storage_iotest.deterministic_bytes(48, "seed-a")
        second = storage_iotest.deterministic_bytes(48, "seed-a")
        different = storage_iotest.deterministic_bytes(48, "seed-b")

        self.assertEqual(first, second)
        self.assertNotEqual(first, different)
        self.assertEqual(len(first), 48)
        self.assertEqual(storage_iotest.sha256_bytes(first), storage_iotest.hashlib.sha256(first).hexdigest())

    def test_device_path_validation_accepts_test_root_and_rejects_escape(self) -> None:
        args = base_args(test_root="/mnt/sdext/a90/test-abc", run_id="run_01")
        storage_iotest.validate_common_args(args)
        self.assertEqual(args.test_root, "/mnt/sdext/a90/test-abc")
        self.assertEqual(args.run_id, "run_01")
        self.assertEqual(args.toybox, "/cache/bin/toybox")

        with self.assertRaisesRegex(RuntimeError, "test root"):
            storage_iotest.validate_device_test_root("/mnt/sdext/a90/not-test")
        with self.assertRaisesRegex(RuntimeError, "device path"):
            storage_iotest.validate_device_path("/mnt/sdext/a90/other/file", args.test_root)
        with self.assertRaisesRegex(RuntimeError, "invalid transfer port"):
            storage_iotest.validate_common_args(base_args(transfer_port=70000))


class DeviceOrchestration(unittest.TestCase):
    def test_mkdir_chain_skips_fixed_parents_and_creates_only_test_children(self) -> None:
        args = base_args(test_root="/mnt/sdext/a90/test-io")
        calls: list[str] = []

        with mock.patch.object(storage_iotest, "run_device", side_effect=lambda _args, command, **_kwargs: calls.append(command) or ""):
            storage_iotest.mkdir_chain(args, "/mnt/sdext/a90/test-io/run-01/deep")

        self.assertEqual(calls, [
            "mkdir /mnt/sdext/a90/test-io",
            "mkdir /mnt/sdext/a90/test-io/run-01",
            "mkdir /mnt/sdext/a90/test-io/run-01/deep",
        ])

    def test_run_one_file_transfers_rehashes_renames_syncs_and_unlinks_probe(self) -> None:
        args = base_args()
        run_commands: list[tuple[str, bool]] = []
        transfer_paths: list[str] = []

        def fake_transfer(_args, _local_path: Path, device_path: str) -> str:
            transfer_paths.append(device_path)
            return "[done] run"

        def fake_run_device(_args, command: str, **kwargs) -> str:
            run_commands.append((command, bool(kwargs.get("allow_error"))))
            if command.startswith("stat "):
                return "No such file"
            return "[done]"

        with tempfile.TemporaryDirectory() as tmp:
            expected = storage_iotest.sha256_bytes(storage_iotest.deterministic_bytes(32, "run-01:1:32"))
            with (
                mock.patch.object(storage_iotest, "transfer_file", side_effect=fake_transfer),
                mock.patch.object(storage_iotest, "device_sha256", return_value=expected),
                mock.patch.object(storage_iotest, "run_device", side_effect=fake_run_device),
            ):
                result = storage_iotest.run_one_file(args, Path(tmp), 1, 32)

        self.assertEqual(result.name, "file-01-32.bin")
        self.assertEqual(result.sha256, expected)
        self.assertTrue(result.transfer_ok)
        self.assertTrue(result.sha_ok)
        self.assertTrue(result.rename_ok)
        self.assertTrue(result.fsync_ok)
        self.assertTrue(result.unlink_ok)
        self.assertEqual(transfer_paths, [
            "/mnt/sdext/a90/test-io/run-01/file-01-32.bin",
            "/mnt/sdext/a90/test-io/run-01/file-01-32.bin.unlink-probe",
        ])
        self.assertIn(("sync", False), run_commands)
        self.assertIn(("run /cache/bin/toybox rm -f /mnt/sdext/a90/test-io/run-01/file-01-32.bin.unlink-probe", False), run_commands)
        self.assertTrue(any(command.startswith("stat ") and allow_error for command, allow_error in run_commands))

    def test_transfer_file_cleans_temp_path_when_socket_send_fails(self) -> None:
        args = base_args(test_root="/mnt/sdext/a90/test-io", transfer_port=19001)
        run_commands: list[tuple[str, bool]] = []
        tmp_paths: list[str] = []

        class FakeRunner:
            error = None

            def __init__(_self, _args, command: str, *, echo: bool = False) -> None:
                self.assertIn("netcat", command)
                match = command.split("of=", 1)[1].split()[0]
                tmp_paths.append(match)

            def start(self) -> None:
                return None

            def join(self, _timeout: float) -> None:
                return None

            def is_alive(self) -> bool:
                return False

            def text(self) -> str:
                return "[done] run"

        class FailingSocket:
            def __enter__(self):
                return self

            def __exit__(self, *_exc) -> None:
                return None

            def sendall(self, _chunk: bytes) -> None:
                raise OSError("host send failed")

            def shutdown(self, _how: int) -> None:
                return None

        def fake_run_device(_args, command: str, **kwargs) -> str:
            run_commands.append((command, bool(kwargs.get("allow_error"))))
            return "[done]"

        with tempfile.TemporaryDirectory() as tmp:
            local_path = Path(tmp) / "payload.bin"
            local_path.write_bytes(b"abc")
            with (
                mock.patch.object(storage_iotest, "run_device", side_effect=fake_run_device),
                mock.patch.object(storage_iotest, "BridgeRunThread", FakeRunner),
                mock.patch.object(storage_iotest.socket, "create_connection", return_value=FailingSocket()),
                mock.patch.object(storage_iotest.os, "getpid", return_value=1234),
                mock.patch.object(storage_iotest.time, "time", return_value=5678.0),
                self.assertRaisesRegex(OSError, "host send failed"),
            ):
                storage_iotest.transfer_file(args, local_path, "/mnt/sdext/a90/test-io/run-01/payload.bin")

        self.assertEqual(tmp_paths, ["/mnt/sdext/a90/test-io/run-01/payload.bin.tmp.1234.5678"])
        cleanup_command = "run /cache/bin/toybox rm -f /mnt/sdext/a90/test-io/run-01/payload.bin.tmp.1234.5678"
        self.assertEqual(run_commands[0], (cleanup_command, True))
        self.assertEqual(run_commands[-1], (cleanup_command, True))
        self.assertNotIn(("run /cache/bin/toybox mv -f /mnt/sdext/a90/test-io/run-01/payload.bin.tmp.1234.5678 /mnt/sdext/a90/test-io/run-01/payload.bin", False), run_commands)

    def test_device_sha256_parses_valid_digest_and_rejects_missing_digest(self) -> None:
        args = base_args()
        digest = "a" * 64

        with mock.patch.object(storage_iotest, "run_device", return_value=f"{digest}  /mnt/sdext/a90/test-io/run-01/file.bin\n"):
            self.assertEqual(
                storage_iotest.device_sha256(args, "/mnt/sdext/a90/test-io/run-01/file.bin"),
                digest,
            )

        with mock.patch.object(storage_iotest, "run_device", return_value="not-a-sha file.bin\n"):
            with self.assertRaisesRegex(RuntimeError, "could not parse sha256sum"):
                storage_iotest.device_sha256(args, "/mnt/sdext/a90/test-io/run-01/file.bin")

    def test_command_run_writes_json_markdown_and_residual_cleanup_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = base_args(
                sizes="16,32",
                host_dir=str(root / "host"),
                out_md=str(root / "report.md"),
                out_json=str(root / "report.json"),
            )
            results = [
                storage_iotest.FileResult("file-01-16.bin", 16, "a" * 64, "/mnt/sdext/a90/test-io/run-01/file-01-16.bin", True, True, True, True, True),
                storage_iotest.FileResult("file-02-32.bin", 32, "b" * 64, "/mnt/sdext/a90/test-io/run-01/file-02-32.bin", True, False, True, True, True),
            ]
            with (
                mock.patch.object(storage_iotest, "mkdir_chain") as mkdir_chain,
                mock.patch.object(storage_iotest, "run_one_file", side_effect=results) as run_one,
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = storage_iotest.command_run(args)

            payload = json.loads((root / "report.json").read_text(encoding="utf-8"))
            markdown = (root / "report.md").read_text(encoding="utf-8")

        self.assertEqual(rc, 1)
        self.assertFalse(payload["pass"])
        self.assertEqual(payload["sizes"], [16, 32])
        self.assertEqual(payload["device_run_root"], "/mnt/sdext/a90/test-io/run-01")
        self.assertEqual(payload["residual_state"]["cleanup_required"], True)
        self.assertEqual(payload["residual_state"]["device_files_left"], 2)
        self.assertIn("| `file-02-32.bin` | `32` |", markdown)
        mkdir_chain.assert_called_once_with(args, "/mnt/sdext/a90/test-io/run-01")
        self.assertEqual(run_one.call_count, 2)

    def test_command_clean_removes_only_valid_run_child(self) -> None:
        args = base_args(run_id="run-02")
        with mock.patch.object(storage_iotest, "run_device", return_value="[done] rm\n") as run_device:
            with contextlib.redirect_stdout(io.StringIO()):
                rc = storage_iotest.command_clean(args)

        self.assertEqual(rc, 0)
        run_device.assert_called_once()
        command = run_device.call_args.args[1]
        self.assertEqual(command, "run /cache/bin/toybox rm -rf /mnt/sdext/a90/test-io/run-02")
        self.assertTrue(run_device.call_args.kwargs["allow_error"])

        with self.assertRaises(RuntimeError):
            storage_iotest.command_clean(base_args(run_id="../escape"))


if __name__ == "__main__":
    unittest.main()
