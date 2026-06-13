from __future__ import annotations

import hashlib
import importlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_harness


broker_stub = types.ModuleType("a90_broker")
broker_stub.PROTO = "A90B1"
broker_stub.connect_and_call = lambda *_args, **_kwargs: {}
sys.modules.setdefault("a90_broker", broker_stub)

module_contract = load_harness("module")
cpu_profiles = importlib.import_module("a90harness.modules.cpu_memory_profiles")


class FakeRecord:
    def __init__(self, ok: bool, label: str) -> None:
        self.ok = ok
        self.label = label

    def to_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "label": self.label}


class FakeClient:
    def __init__(self, responses: list[tuple[bool, str]]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, list[str], float | None, str | None]] = []

    def run(self, label: str, command: list[str], *, timeout: float | None = None, transcript: str | None = None):
        self.calls.append((label, command, timeout, transcript))
        ok, text = self.responses.pop(0)
        return FakeRecord(ok, label), text


class FakeStore:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.text: dict[str, str] = {}
        self.json: dict[str, object] = {}

    def path(self, rel: str) -> Path:
        path = self.run_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def write_text(self, rel: str, text: str) -> Path:
        self.text[rel] = text
        path = self.path(rel)
        path.write_text(text, encoding="utf-8")
        return path

    def write_json(self, rel: str, payload: object) -> Path:
        self.json[rel] = payload
        path = self.path(rel)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path


def build_ctx(tmp: str, client: FakeClient | None = None, profile: str = "smoke"):
    root = Path(tmp)
    store = FakeStore(root)
    module_dir = root / "modules" / cpu_profiles.CpuMemoryProfilesModule.name
    module_dir.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(
        repo_root=Path("/repo"),
        store=store,
        module_dir=module_dir,
        client=client or FakeClient([]),
        profile=profile,
        timeout=10.0,
    )


class PureHelpers(unittest.TestCase):
    def test_zero_sha256_matches_incremental_zero_buffer_digest(self) -> None:
        self.assertEqual(cpu_profiles.zero_sha256(0), hashlib.sha256(b"").hexdigest())
        self.assertEqual(cpu_profiles.zero_sha256(3), hashlib.sha256(b"\0\0\0").hexdigest())
        size = (1024 * 1024) + 17
        self.assertEqual(cpu_profiles.zero_sha256(size), hashlib.sha256(b"\0" * size).hexdigest())

    def test_parse_status_extracts_available_status_fields_and_ignores_missing_ones(self) -> None:
        text = "\n".join([
            "uptime: 12.5s load=0.75",
            "thermal: cpu=42.5C 13% gpu=39.0C 7%",
            "memory: 512/2048MB used",
            "battery: 88% Charging temp=31.5C",
        ])

        parsed = cpu_profiles.parse_status(text)

        self.assertEqual(parsed["uptime_sec"], 12.5)
        self.assertEqual(parsed["load_1m"], 0.75)
        self.assertEqual(parsed["cpu_temp_c"], 42.5)
        self.assertEqual(parsed["cpu_usage_percent"], 13)
        self.assertEqual(parsed["gpu_temp_c"], 39.0)
        self.assertEqual(parsed["gpu_usage_percent"], 7)
        self.assertEqual(parsed["mem_used_mb"], 512)
        self.assertEqual(parsed["mem_total_mb"], 2048)
        self.assertEqual(parsed["battery_percent"], 88)
        self.assertEqual(parsed["battery_state"], "Charging")
        self.assertEqual(parsed["battery_temp_c"], 31.5)
        self.assertEqual(cpu_profiles.parse_status("status without known fields"), {})

    def test_profile_dict_and_selection_contracts(self) -> None:
        spec = cpu_profiles.CpuMemoryProfile("tiny", 1, 2, 4096, 0.0)
        self.assertEqual(
            spec.to_dict(),
            {
                "name": "tiny",
                "stress_sec": 1,
                "stress_workers": 2,
                "mem_size_bytes": 4096,
                "cooldown_sec": 0.0,
            },
        )

        module = cpu_profiles.CpuMemoryProfilesModule()
        self.assertEqual([item.name for item in module._profiles("smoke")], ["low", "cooldown"])
        self.assertEqual([item.name for item in module._profiles("quick")], ["low", "medium", "spike", "cooldown"])


class PathAndProfileExecution(unittest.TestCase):
    def test_profile_temp_and_memory_paths_stay_under_device_tmp_root(self) -> None:
        module = cpu_profiles.CpuMemoryProfilesModule()
        module._run_id = "runid"
        spec = cpu_profiles.CpuMemoryProfile("low", 1, 1, 4096, 0.0)

        temp_dir = module._profile_temp_dir(spec)
        memory_path = module._profile_memory_path(temp_dir, spec)

        self.assertEqual(temp_dir, "/tmp/a90-cpumem.runid.low")
        self.assertEqual(memory_path, "/tmp/a90-cpumem.runid.low/low-mem.bin")

        bad = cpu_profiles.CpuMemoryProfile("../bad", 1, 1, 4096, 0.0)
        with self.assertRaises(RuntimeError):
            module._profile_temp_dir(bad)

    def test_run_cmd_records_transcript_and_returns_command_result_tuple(self) -> None:
        client = FakeClient([(True, "status text")])
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp, client)
            module = cpu_profiles.CpuMemoryProfilesModule()

            ok, text, record = module._run_cmd(ctx, "low", "status-before", ["status"], timeout=3.0)

        self.assertTrue(ok)
        self.assertEqual(text, "status text")
        self.assertEqual(record["label"], "cpu-memory-profiles-low-status-before")
        self.assertEqual(ctx.store.text["modules/cpu-memory-profiles/low/commands/status-before.txt"], "status text")
        self.assertEqual(client.calls[0][1], ["status"])
        self.assertTrue(client.calls[0][3].endswith("modules/cpu-memory-profiles/low/commands/status-before.txt"))

    def test_run_profile_success_records_status_memory_hash_and_cleanup(self) -> None:
        status_before = "thermal: cpu=35.0C 5% gpu=33.0C 1%\nmemory: 100/200MB used"
        status_after = "thermal: cpu=61.0C 95% gpu=40.0C 2%\nmemory: 120/200MB used"
        expected_hash = cpu_profiles.zero_sha256(4096)
        client = FakeClient([
            (True, status_before),
            (True, "stress ok"),
            (True, status_after),
            (True, "mkdir ok"),
            (True, "write ok"),
            (True, f"{expected_hash}  /tmp/file\n"),
            (True, "cleanup ok"),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp, client)
            module = cpu_profiles.CpuMemoryProfilesModule()
            module._run_id = "testrun"
            spec = cpu_profiles.CpuMemoryProfile("tiny", 1, 2, 4096, 0.0)

            profile = module._run_profile(ctx, spec)

        self.assertTrue(profile["ok"])
        self.assertEqual(profile["memory"]["expected_sha256"], expected_hash)
        self.assertEqual(profile["memory"]["device_sha256"], expected_hash)
        self.assertTrue(profile["memory"]["hash_ok"])
        self.assertEqual(profile["samples"][1]["status"]["cpu_usage_percent"], 95)
        commands = [call[1] for call in client.calls]
        self.assertIn(["cpustress", "1", "2"], commands)
        self.assertIn(["run", "/cache/bin/toybox", "rm", "-rf", "/tmp/a90-cpumem.testrun.tiny"], commands)

    def test_run_profile_stops_memory_work_after_mkdir_failure(self) -> None:
        client = FakeClient([
            (True, "status before"),
            (True, "stress ok"),
            (True, "status after"),
            (False, "mkdir failed"),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp, client)
            module = cpu_profiles.CpuMemoryProfilesModule()
            module._run_id = "testrun"
            spec = cpu_profiles.CpuMemoryProfile("tiny", 1, 1, 4096, 0.0)

            profile = module._run_profile(ctx, spec)

        self.assertFalse(profile["ok"])
        self.assertFalse(profile["memory"]["mkdir_ok"])
        self.assertFalse(profile["memory"]["write_ok"])
        self.assertEqual(len(client.calls), 4)


class ModuleRunAndVerify(unittest.TestCase):
    def test_run_writes_report_and_returns_ok_only_when_all_profiles_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp)
            module = cpu_profiles.CpuMemoryProfilesModule()
            with mock.patch.object(module, "_run_profile", side_effect=[
                {"ok": True, "spec": {"name": "low"}},
                {"ok": False, "spec": {"name": "cooldown"}},
            ]) as run_profile:
                result = module.run(ctx)

            self.assertFalse(result.ok)
            self.assertEqual(result.detail, "profiles=2 ok=False")
            report = ctx.store.json["modules/cpu-memory-profiles/cpu-memory-profiles-report.json"]
            self.assertEqual(report["schema"], "a90-cpu-memory-profiles-v180")
            self.assertEqual(report["profile"], "smoke")
            self.assertEqual(len(report["profiles"]), 2)
            self.assertEqual(run_profile.call_count, 2)

    def test_verify_accepts_good_report_and_reports_memory_mismatches_or_missing_report(self) -> None:
        good_profile = {
            "ok": True,
            "spec": {"name": "low"},
            "memory": {
                "mkdir_ok": True,
                "write_ok": True,
                "hash_ok": True,
                "cleanup_ok": True,
                "expected_sha256": "abc",
                "device_sha256": "abc",
            },
            "samples": [{"status": {"cpu_usage_percent": 71}}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_ctx(tmp)
            report = ctx.module_dir / "cpu-memory-profiles-report.json"
            report.write_text(json.dumps({"profiles": [good_profile]}), encoding="utf-8")
            module = cpu_profiles.CpuMemoryProfilesModule()

            result = module.verify(ctx)

            self.assertTrue(result.ok)
            self.assertIn("profiles=1", result.detail)
            self.assertIn("max_cpu_usage=71%", result.detail)

            bad_profile = dict(good_profile)
            bad_profile["memory"] = dict(good_profile["memory"], device_sha256="def")
            report.write_text(json.dumps({"profiles": [bad_profile]}), encoding="utf-8")
            failed = module.verify(ctx)
            self.assertFalse(failed.ok)
            self.assertIn("memory-mismatch=1", failed.detail)

        with tempfile.TemporaryDirectory() as tmp:
            missing = cpu_profiles.CpuMemoryProfilesModule().verify(build_ctx(tmp))
        self.assertFalse(missing.ok)
        self.assertIn("missing", missing.detail)


if __name__ == "__main__":
    unittest.main()
