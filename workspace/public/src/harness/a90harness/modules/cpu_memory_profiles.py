"""CPU/memory workload profile module for mixed-soak validation."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import secrets
import time
from dataclasses import asdict, dataclass
from typing import Any

from a90harness.path_safety import require_path_under, require_safe_component
from a90harness.module import ModuleContext, StepResult, TestModule

DEVICE_TMP_ROOT = "/tmp"
DEVICE_TMP_PREFIX = "a90-cpumem"


@dataclass(frozen=True)
class CpuMemoryProfile:
    name: str
    stress_sec: int
    stress_workers: int
    mem_size_bytes: int
    cooldown_sec: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SMOKE_PROFILES: tuple[CpuMemoryProfile, ...] = (
    CpuMemoryProfile("low", 1, 1, 4 * 1024 * 1024, 1.0),
    CpuMemoryProfile("cooldown", 1, 1, 4 * 1024 * 1024, 1.0),
)

QUICK_PROFILES: tuple[CpuMemoryProfile, ...] = (
    CpuMemoryProfile("low", 1, 1, 4 * 1024 * 1024, 1.0),
    CpuMemoryProfile("medium", 2, 2, 8 * 1024 * 1024, 1.0),
    CpuMemoryProfile("spike", 3, 4, 16 * 1024 * 1024, 2.0),
    CpuMemoryProfile("cooldown", 1, 1, 4 * 1024 * 1024, 1.0),
)


def zero_sha256(size: int) -> str:
    digest = hashlib.sha256()
    chunk = b"\0" * min(size, 1024 * 1024)
    remaining = size
    while remaining > 0:
        take = min(remaining, len(chunk))
        digest.update(chunk[:take])
        remaining -= take
    return digest.hexdigest()


def parse_status(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    if match := re.search(r"uptime:\s*([0-9.]+)s\s+load=([0-9.]+)", text):
        parsed["uptime_sec"] = float(match.group(1))
        parsed["load_1m"] = float(match.group(2))
    if match := re.search(r"thermal:\s*cpu=([0-9.]+)C\s+([0-9]+)%\s+gpu=([0-9.]+)C\s+([0-9]+)%", text):
        parsed["cpu_temp_c"] = float(match.group(1))
        parsed["cpu_usage_percent"] = int(match.group(2))
        parsed["gpu_temp_c"] = float(match.group(3))
        parsed["gpu_usage_percent"] = int(match.group(4))
    if match := re.search(r"memory:\s*([0-9]+)/([0-9]+)MB used", text):
        parsed["mem_used_mb"] = int(match.group(1))
        parsed["mem_total_mb"] = int(match.group(2))
    if match := re.search(r"battery:\s*([0-9]+)%\\s+([^\\r\\n]+?)\\s+temp=([0-9.]+)C", text):
        parsed["battery_percent"] = int(match.group(1))
        parsed["battery_state"] = match.group(2).strip()
        parsed["battery_temp_c"] = float(match.group(3))
    return parsed


class CpuMemoryProfilesModule(TestModule):
    name = "cpu-memory-profiles"
    description = "run low/medium/spike/cooldown CPU and memory workload profiles"
    cycle_label = "v180"
    read_only = False

    def __init__(self) -> None:
        self._run_id = f"v180-cpumem-{int(time.time())}-{secrets.token_hex(8)}"

    def _profiles(self, profile: str) -> tuple[CpuMemoryProfile, ...]:
        return QUICK_PROFILES if profile == "quick" else SMOKE_PROFILES

    def _run_cmd(self,
                 ctx: ModuleContext,
                 profile: str,
                 label: str,
                 command: list[str],
                 *,
                 timeout: float | None = None) -> tuple[bool, str, dict[str, Any]]:
        record, text = ctx.client.run(
            f"{self.name}-{profile}-{label}",
            command,
            timeout=timeout,
            transcript=str(ctx.store.path(f"modules/{self.name}/{profile}/commands/{label}.txt")),
        )
        ctx.store.write_text(f"modules/{self.name}/{profile}/commands/{label}.txt", text)
        return record.ok, text, record.to_dict()

    def _profile_temp_dir(self, spec: CpuMemoryProfile) -> str:
        component = require_safe_component(
            f"{DEVICE_TMP_PREFIX}.{self._run_id}.{spec.name}",
            "cpu memory temp dir",
        )
        temp_dir = posixpath.join(DEVICE_TMP_ROOT, component)
        return require_path_under(temp_dir, DEVICE_TMP_ROOT, "cpu memory temp dir")

    def _profile_memory_path(self, temp_dir: str, spec: CpuMemoryProfile) -> str:
        filename = require_safe_component(f"{spec.name}-mem.bin", "cpu memory filename")
        return require_path_under(
            posixpath.join(temp_dir, filename),
            temp_dir,
            "cpu memory file",
        )

    def _run_profile(self, ctx: ModuleContext, spec: CpuMemoryProfile) -> dict[str, Any]:
        profile: dict[str, Any] = {
            "spec": spec.to_dict(),
            "commands": [],
            "samples": [],
            "memory": {},
            "ok": False,
        }
        temp_dir = self._profile_temp_dir(spec)
        path = self._profile_memory_path(temp_dir, spec)
        expected_hash = zero_sha256(spec.mem_size_bytes)

        ok, text, record = self._run_cmd(ctx, spec.name, "status-before", ["status"], timeout=ctx.timeout)
        profile["commands"].append(record)
        profile["samples"].append({"label": "before", "ok": ok, "status": parse_status(text)})

        ok, _text, record = self._run_cmd(
            ctx,
            spec.name,
            "cpustress",
            ["cpustress", str(spec.stress_sec), str(spec.stress_workers)],
            timeout=max(ctx.timeout, spec.stress_sec + 30.0),
        )
        profile["commands"].append(record)

        ok_after, text_after, record = self._run_cmd(ctx, spec.name, "status-after", ["status"], timeout=ctx.timeout)
        profile["commands"].append(record)
        profile["samples"].append({"label": "after", "ok": ok_after, "status": parse_status(text_after)})

        mkdir_ok, _text, record = self._run_cmd(
            ctx,
            spec.name,
            "mem-mkdir",
            ["run", "/cache/bin/toybox", "mkdir", "-m", "700", temp_dir],
            timeout=max(ctx.timeout, 20.0),
        )
        profile["commands"].append(record)

        write_ok = False
        hash_ok = False
        device_hash = None
        cleanup_ok = False

        if not mkdir_ok:
            memory = {
                "temp_dir": temp_dir,
                "path": path,
                "size_bytes": spec.mem_size_bytes,
                "expected_sha256": expected_hash,
                "device_sha256": device_hash,
                "mkdir_ok": mkdir_ok,
                "write_ok": write_ok,
                "hash_ok": hash_ok,
                "cleanup_ok": cleanup_ok,
            }
            profile["memory"] = memory
            if spec.cooldown_sec > 0:
                time.sleep(spec.cooldown_sec)
            return profile

        write_ok, _text, record = self._run_cmd(
            ctx,
            spec.name,
            "mem-write",
            [
                "run",
                "/cache/bin/toybox",
                "dd",
                "if=/dev/zero",
                f"of={path}",
                f"bs={spec.mem_size_bytes}",
                "count=1",
            ],
            timeout=max(ctx.timeout, 45.0),
        )
        profile["commands"].append(record)

        hash_ok, hash_text, record = self._run_cmd(
            ctx,
            spec.name,
            "mem-sha256",
            ["run", "/cache/bin/toybox", "sha256sum", path],
            timeout=max(ctx.timeout, 45.0),
        )
        profile["commands"].append(record)
        match = re.search(r"\b([0-9a-fA-F]{64})\b", hash_text)
        device_hash = match.group(1).lower() if match else None

        cleanup_ok, _text, record = self._run_cmd(
            ctx,
            spec.name,
            "mem-cleanup",
            ["run", "/cache/bin/toybox", "rm", "-rf", temp_dir],
            timeout=max(ctx.timeout, 20.0),
        )
        profile["commands"].append(record)

        memory = {
            "temp_dir": temp_dir,
            "path": path,
            "size_bytes": spec.mem_size_bytes,
            "expected_sha256": expected_hash,
            "device_sha256": device_hash,
            "mkdir_ok": mkdir_ok,
            "write_ok": write_ok,
            "hash_ok": hash_ok and device_hash == expected_hash,
            "cleanup_ok": cleanup_ok,
        }
        profile["memory"] = memory
        if spec.cooldown_sec > 0:
            time.sleep(spec.cooldown_sec)
        profile["ok"] = (
            ok and ok_after and write_ok and hash_ok and cleanup_ok and
            memory["hash_ok"]
        )
        return profile

    def run(self, ctx: ModuleContext) -> StepResult:
        profiles = [self._run_profile(ctx, spec) for spec in self._profiles(ctx.profile)]
        report = {
            "schema": "a90-cpu-memory-profiles-v180",
            "run_id": self._run_id,
            "profile": ctx.profile,
            "profiles": profiles,
        }
        ctx.store.write_json(f"modules/{self.name}/cpu-memory-profiles-report.json", report)
        ok = all(profile.get("ok") is True for profile in profiles)
        return StepResult("run", ok, f"profiles={len(profiles)} ok={ok}", 0.0)

    def verify(self, ctx: ModuleContext) -> StepResult:
        report_path = ctx.module_dir / "cpu-memory-profiles-report.json"
        if not report_path.exists():
            return StepResult("verify", False, f"missing {report_path}", 0.0)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        profiles = report.get("profiles", [])
        failures: list[str] = []
        max_cpu_usage = 0
        memory_mismatch = 0
        for profile in profiles:
            if profile.get("ok") is not True:
                failures.append(f"profile-failed:{profile.get('spec', {}).get('name')}")
            memory = profile.get("memory", {})
            if not (
                memory.get("mkdir_ok") is True and
                memory.get("write_ok") is True and
                memory.get("hash_ok") is True and
                memory.get("cleanup_ok") is True and
                memory.get("expected_sha256") == memory.get("device_sha256")
            ):
                memory_mismatch += 1
            for sample in profile.get("samples", []):
                status = sample.get("status", {})
                max_cpu_usage = max(max_cpu_usage, int(status.get("cpu_usage_percent") or 0))
        if memory_mismatch:
            failures.append(f"memory-mismatch={memory_mismatch}")
        ok = bool(profiles) and not failures
        detail = f"profiles={len(profiles)} max_cpu_usage={max_cpu_usage}% memory_mismatch={memory_mismatch}"
        if failures:
            detail += " failures=" + ",".join(failures)
        return StepResult("verify", ok, detail, 0.0)
