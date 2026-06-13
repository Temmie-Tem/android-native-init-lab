from __future__ import annotations

import argparse
import json
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


bridge = load_script("workspace/public/src/scripts/revalidation/a90_bridge.py")


class PathSafetyHelpers(unittest.TestCase):
    def test_validate_private_repair_path_accepts_only_workspace_private_children(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            allowed = root / "workspace" / "private" / "logs" / "bridge"
            allowed.mkdir(parents=True)

            bridge.validate_private_repair_path(root, allowed)

            with self.assertRaisesRegex(RuntimeError, "outside workspace/private"):
                bridge.validate_private_repair_path(root, root / "workspace" / "public")

    def test_validate_private_repair_path_rejects_symlink_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private = root / "workspace" / "private"
            private.mkdir(parents=True)
            target = root / "target"
            target.mkdir()
            symlink = private / "link"
            symlink.symlink_to(target)

            with self.assertRaisesRegex(RuntimeError, "symlink repair path component"):
                bridge.validate_private_repair_path(root, symlink / "child")

    def test_ensure_private_repair_dir_creates_plain_directory_and_revalidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "workspace" / "private" / "run"

            bridge.ensure_private_repair_dir(root, path)

            self.assertTrue(path.is_dir())
            self.assertFalse(path.is_symlink())


class ProcessAndSocketParsing(unittest.TestCase):
    def test_cmdline_port_match_handles_flag_forms_and_default_port(self) -> None:
        self.assertTrue(bridge.cmdline_port_match("python serial_tcp_bridge.py --port 1234", 1234))
        self.assertTrue(bridge.cmdline_port_match("python serial_tcp_bridge.py --port=2345", 2345))
        self.assertTrue(bridge.cmdline_port_match("python serial_tcp_bridge.py", bridge.DEFAULT_PORT))
        self.assertFalse(bridge.cmdline_port_match("python serial_tcp_bridge.py --port 1234", 54321))
        self.assertFalse(bridge.cmdline_port_match("python serial_tcp_bridge.py", 1234))

    def test_parse_proc_tcp_line_decodes_little_endian_ipv4_port_state_inode_uid(self) -> None:
        line = (
            "  0: 0100007F:D431 00000000:0000 0A 00000000:00000000 "
            "00:00000000 00000000 1000 0 12345 1 0000000000000000"
        )

        self.assertEqual(
            bridge.parse_proc_tcp_line(line),
            ("127.0.0.1", 54321, "0A", "12345", 1000),
        )
        self.assertIsNone(bridge.parse_proc_tcp_line("too short"))
        self.assertIsNone(bridge.parse_proc_tcp_line("0: no-colon 0 0 0 0 0 0 0 0"))

    def test_listen_sockets_filters_by_host_port_and_listen_state(self) -> None:
        tcp = "\n".join([
            "sl local_address rem_address st tx_queue rx_queue tr tm->when retrnsmt uid timeout inode",
            "0: 0100007F:D431 00000000:0000 0A 0 0 0 1000 0 111",
            "1: 00000000:D431 00000000:0000 0A 0 0 0 1001 0 222",
            "2: 0200007F:D431 00000000:0000 0A 0 0 0 1002 0 333",
            "3: 0100007F:D431 00000000:0000 01 0 0 0 1003 0 444",
            "4: 0100007F:0001 00000000:0000 0A 0 0 0 1004 0 555",
        ])
        with mock.patch.object(bridge.Path, "read_text", return_value=tcp):
            sockets = bridge.listen_sockets("127.0.0.1", 54321)

        self.assertEqual(
            sockets,
            [
                {"address": "127.0.0.1", "port": 54321, "inode": "111", "uid": 1000},
                {"address": "0.0.0.0", "port": 54321, "inode": "222", "uid": 1001},
            ],
        )


class StatusAndSelectionHelpers(unittest.TestCase):
    def test_selected_device_info_tracks_explicit_single_and_ambiguous_auto_candidates(self) -> None:
        candidates = [
            bridge.SerialCandidate("/dev/a", "/real/a", True),
            bridge.SerialCandidate("/dev/b", "/real/b", True),
        ]
        with mock.patch.object(bridge, "serial_candidates", return_value=candidates):
            explicit = bridge.selected_device_info("/dev/custom", "/ignored")
            ambiguous = bridge.selected_device_info("auto", "/ignored")
            single = bridge.selected_device_info("auto", "/ignored")

        self.assertEqual(explicit["selected_device"], "/dev/custom")
        self.assertEqual(explicit["selected_realpath"], "/dev/custom")
        self.assertTrue(ambiguous["ambiguous"])
        self.assertEqual(ambiguous["selected_device"], "/dev/a")
        self.assertEqual(len(ambiguous["serial_candidates"]), 2)
        self.assertTrue(single["ambiguous"])

        with mock.patch.object(bridge, "serial_candidates", return_value=[candidates[0]]):
            info = bridge.selected_device_info("auto", "/ignored")
        self.assertFalse(info["ambiguous"])
        self.assertEqual(info["selected_device"], "/dev/a")

    def test_collect_status_prefers_managed_running_process_and_uses_cmdline_pid_fallback(self) -> None:
        args = SimpleNamespace(
            metadata="",
            host="127.0.0.1",
            port=54321,
            no_client_probe=True,
            device="auto",
            device_glob="/dev/serial/*",
        )
        managed = bridge.BridgeProcess(
            pid=111,
            cmdline="python serial_tcp_bridge.py --port 54321",
            managed=True,
            port_match=True,
        )
        discovered = bridge.BridgeProcess(
            pid=222,
            cmdline="python serial_tcp_bridge.py --port 54321",
            managed=False,
            port_match=True,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(bridge, "listen_sockets", return_value=[]), \
                    mock.patch.object(bridge, "pid_lookup_for_socket_inodes", return_value={
                        "pids": [],
                        "source": "none",
                        "scanned_fd_dirs": 0,
                        "inaccessible_fd_dirs": 0,
                    }), \
                    mock.patch.object(bridge, "discover_bridge_processes", return_value=[managed, discovered]), \
                    mock.patch.object(bridge, "process_exists", return_value=True), \
                    mock.patch.object(bridge, "selected_device_info", return_value={
                        "serial_candidates": [],
                        "selected_device": "",
                        "selected_realpath": "",
                        "ambiguous": False,
                    }):
                status = bridge.collect_status(args, root)

        self.assertEqual(status["bridge_process"], "running")
        self.assertEqual(status["port_pids"], [111, 222])
        self.assertEqual(status["port_pid_source"], "cmdline-fallback")
        self.assertEqual(status["bridge_probe"], "skipped")
        self.assertFalse(status["port_listening"])

    def test_print_status_text_renders_compact_machine_readable_fields(self) -> None:
        status = {
            "wrapper_contract": 1,
            "bridge_process": "running",
            "listen_host": "127.0.0.1",
            "listen_port": 54321,
            "port_listening": True,
            "bridge_probe": "data",
            "port_pids": [123],
            "port_pid_source": "fd",
            "port_pid_inaccessible_fd_dirs": 0,
            "metadata_path": "workspace/private/run/a90_bridge.json",
            "metadata_present": True,
            "capture_path": "workspace/private/logs/bridge/raw.log",
            "selected_device": "/dev/ttyACM0",
            "selected_realpath": "/dev/bus/usb/001/001",
            "ambiguous": False,
            "serial_candidates": [{"path": "/dev/ttyACM0"}],
            "processes": [{"pid": 123, "managed": True, "port_match": True}],
        }

        with mock.patch("builtins.print") as printer:
            bridge.print_status_text(status)

        lines = [call.args[0] for call in printer.call_args_list]
        self.assertIn("bridge_process=running", lines)
        self.assertIn("listen=127.0.0.1:54321", lines)
        self.assertIn("port_pids=123", lines)
        self.assertIn("process=123 managed port_match=1", lines)


class CommandRenderingAndFilesystemHelpers(unittest.TestCase):
    def test_build_bridge_command_includes_contract_flags_and_effective_expect_realpath(self) -> None:
        args = argparse.Namespace(
            python="/usr/bin/python3",
            host="127.0.0.1",
            port=54321,
            device="auto",
            device_glob="/dev/serial/*",
            expect_realpath="/tmp/../tmp/device",
            pin_selected_realpath=True,
            allow_device_change=True,
            no_pin_device=True,
            allow_multiple_auto_matches=True,
            assert_dtr_rts=True,
            no_exclusive_tty=True,
        )
        root = Path("/repo")
        command = bridge.build_bridge_command(args, root, Path("/tmp/capture.log"))

        self.assertEqual(command[:2], ["/usr/bin/python3", "/repo/workspace/public/src/scripts/revalidation/serial_tcp_bridge.py"])
        self.assertIn("--capture", command)
        self.assertIn("/tmp/capture.log", command)
        self.assertIn("--allow-device-change", command)
        self.assertIn("--no-pin-device", command)
        self.assertIn("--allow-multiple-auto-matches", command)
        self.assertIn("--assert-dtr-rts", command)
        self.assertIn("--no-exclusive-tty", command)
        self.assertEqual(command[command.index("--expect-realpath") + 1], "/tmp/device")

    def test_effective_expect_realpath_can_pin_selected_auto_device(self) -> None:
        args = argparse.Namespace(
            expect_realpath="",
            pin_selected_realpath=True,
            device="auto",
            device_glob="/dev/serial/*",
        )
        with mock.patch.object(bridge, "selected_device_info", return_value={"selected_realpath": "/real/tty"}):
            self.assertEqual(bridge.effective_expect_realpath(args), "/real/tty")

        args.pin_selected_realpath = False
        self.assertEqual(bridge.effective_expect_realpath(args), "")

    def test_write_metadata_creates_parent_and_writes_sorted_json_with_newline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace" / "private" / "run" / "bridge.json"
            bridge.write_metadata(path, {"b": 2, "a": 1})

            text = path.read_text(encoding="utf-8")
        self.assertTrue(text.endswith("\n"))
        self.assertEqual(json.loads(text), {"a": 1, "b": 2})
        self.assertLess(text.index('"a"'), text.index('"b"'))

    def test_path_detail_and_stat_info_report_missing_and_present_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "workspace" / "private" / "missing"
            detail = bridge.path_detail(missing, root)
            self.assertIn("exists=0", detail)

            present = root / "file.txt"
            present.write_text("data", encoding="utf-8")
            info = bridge.stat_info(present)
            self.assertTrue(info["exists"])
            self.assertTrue(stat.S_ISREG(present.stat().st_mode))
            self.assertIn("owner=", bridge.path_detail(present, root))


if __name__ == "__main__":
    unittest.main()
