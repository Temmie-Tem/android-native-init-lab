from __future__ import annotations

import hashlib
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_revalidation


cpu_thermal = load_revalidation("cpu_mem_thermal_stability")


class PureParsingHelpers(unittest.TestCase):
    def test_parse_size_accepts_plain_k_and_m_suffixes_and_rejects_invalid_values(self) -> None:
        self.assertEqual(cpu_thermal.parse_size("4096"), 4096)
        self.assertEqual(cpu_thermal.parse_size("4K"), 4096)
        self.assertEqual(cpu_thermal.parse_size("8m"), 8 * 1024 * 1024)

        for value in ("", "0", "-1", "12G", "abc"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    cpu_thermal.parse_size(value)

    def test_parse_status_text_extracts_all_known_native_init_fields(self) -> None:
        text = "\n".join([
            "A90P1 END status duration_ms=137",
            "uptime: 42.5s load=0.37",
            "battery: 93% Discharging temp=31.5C",
            "power: now=1.25W avg=0.95W",
            "thermal: cpu=54.5C 67% gpu=43.0C 12%",
            "memory: 512/2048MB used",
            "longsoak: health=ok",
        ])

        sample = cpu_thermal.parse_status_text("cycle-01", text)

        self.assertEqual(sample.label, "cycle-01")
        self.assertIsNone(sample.command_duration_ms)
        self.assertEqual(sample.uptime_sec, 42.5)
        self.assertEqual(sample.load_1m, 0.37)
        self.assertEqual(sample.battery_percent, 93)
        self.assertEqual(sample.battery_temp_c, 31.5)
        self.assertEqual(sample.power_now_w, 1.25)
        self.assertEqual(sample.power_avg_w, 0.95)
        self.assertEqual(sample.cpu_temp_c, 54.5)
        self.assertEqual(sample.cpu_usage_percent, 67)
        self.assertEqual(sample.gpu_temp_c, 43.0)
        self.assertEqual(sample.gpu_usage_percent, 12)
        self.assertEqual(sample.mem_used_mb, 512)
        self.assertEqual(sample.mem_total_mb, 2048)
        self.assertEqual(sample.longsoak_health, "ok")

        empty = cpu_thermal.parse_status_text("empty", "unstructured")
        self.assertEqual(empty.label, "empty")
        self.assertIsNone(empty.uptime_sec)
        self.assertIsNone(empty.longsoak_health)

    def test_zero_sha256_parse_sha256_and_sample_extreme_contracts(self) -> None:
        self.assertEqual(cpu_thermal.zero_sha256(0), hashlib.sha256(b"").hexdigest())
        self.assertEqual(cpu_thermal.zero_sha256(3), hashlib.sha256(b"\0\0\0").hexdigest())

        digest = "A" * 64
        self.assertEqual(cpu_thermal.parse_sha256(f"{digest}  /tmp/file"), "a" * 64)
        self.assertIsNone(cpu_thermal.parse_sha256("not-a-digest"))

        samples = [
            SimpleNamespace(cpu_temp_c=42.0, mem_used_mb=None),
            SimpleNamespace(cpu_temp_c=67.5, mem_used_mb=128),
            SimpleNamespace(cpu_temp_c=None, mem_used_mb=256),
        ]
        self.assertEqual(cpu_thermal.sample_extreme(samples, "cpu_temp_c"), 67.5)
        self.assertEqual(cpu_thermal.sample_extreme(samples, "mem_used_mb"), 256)
        self.assertIsNone(cpu_thermal.sample_extreme([SimpleNamespace(value=None)], "value"))


class ProcessAndHostPingHelpers(unittest.TestCase):
    def test_process_snapshot_counts_global_and_controlled_zombies_and_pid1_fds(self) -> None:
        ps_text = "\n".join([
            "PID STAT COMM",
            "1 S init",
            "2 Z [kworker]",
            "3 Z a90_cpustress",
            "4 Z a90_worker",
            "5 S toybox",
        ])
        fd_text = "\n".join([
            "lrwx------ 1 root root 64 0",
            "lrwx------ 1 root root 64 1",
            "not-an-ls-line",
        ])
        responses = [
            SimpleNamespace(text=ps_text),
            SimpleNamespace(text=fd_text),
        ]

        def fake_run_cmdv1(*_args, **_kwargs):
            return responses.pop(0)

        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(bridge_host="127.0.0.1", bridge_port=54321, bridge_timeout=12.0, toybox="/toybox")
            with mock.patch.object(cpu_thermal, "run_cmdv1_command", side_effect=fake_run_cmdv1):
                snapshot = cpu_thermal.process_snapshot(args, Path(tmp))

            written = Path(tmp, "process-ps.txt").read_text(encoding="utf-8")

        self.assertIn("a90_cpustress", written)
        self.assertEqual(snapshot.pid_count, 5)
        self.assertEqual(snapshot.zombie_count, 3)
        self.assertEqual(snapshot.controlled_zombie_count, 2)
        self.assertEqual(snapshot.pid1_fd_count, 2)

    def test_process_snapshot_tolerates_pid1_fd_listing_failure(self) -> None:
        responses = [SimpleNamespace(text="1 S init\n")]

        def fake_run_cmdv1(*_args, **_kwargs):
            if responses:
                return responses.pop(0)
            raise RuntimeError("fd unavailable")

        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(bridge_host="127.0.0.1", bridge_port=54321, bridge_timeout=12.0, toybox="/toybox")
            with mock.patch.object(cpu_thermal, "run_cmdv1_command", side_effect=fake_run_cmdv1):
                snapshot = cpu_thermal.process_snapshot(args, Path(tmp))

        self.assertEqual(snapshot.pid_count, 1)
        self.assertEqual(snapshot.zombie_count, 0)
        self.assertIsNone(snapshot.pid1_fd_count)

    def test_maybe_host_ping_disabled_success_and_exception_branches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            disabled_args = SimpleNamespace(host_ping=False, ping_count=1)
            disabled = cpu_thermal.maybe_host_ping(disabled_args, "base", out_dir)
            self.assertEqual(disabled, {"label": "base", "enabled": False, "ok": None, "error": ""})
            self.assertFalse((out_dir / "host-ping-base.txt").exists())

            enabled_args = SimpleNamespace(host_ping=True, ping_count=1)
            with mock.patch.object(cpu_thermal, "host_ping", return_value="1 packets transmitted, 0% packet loss"):
                success = cpu_thermal.maybe_host_ping(enabled_args, "ok", out_dir)
            self.assertEqual(success, {"label": "ok", "enabled": True, "ok": True, "error": ""})
            self.assertIn("0% packet loss", (out_dir / "host-ping-ok.txt").read_text(encoding="utf-8"))

            with mock.patch.object(cpu_thermal, "host_ping", side_effect=RuntimeError("no route")):
                failed = cpu_thermal.maybe_host_ping(enabled_args, "fail", out_dir)
            self.assertEqual(failed["label"], "fail")
            self.assertTrue(failed["enabled"])
            self.assertFalse(failed["ok"])
            self.assertEqual(failed["error"], "no route")
            self.assertIn("RuntimeError: no route", (out_dir / "host-ping-fail.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
