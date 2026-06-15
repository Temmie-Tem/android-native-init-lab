#!/usr/bin/env python3
"""V2490 live runner for the own-process ACDB pure-read GET helper.

This path intentionally avoids the V2477-V2488 in-HAL LD_PRELOAD lines.  It
boots stock Android through the checked helper, runs the current ARM32 helper once
from /data/local/tmp under su, pulls private artifacts, cleans up, and rolls
back to V2321.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_android_acdb_ownprocess_get_v2489 as v2489
import build_android_acdb_ownprocess_get_exec_linked_v2512 as v_helper
import build_android_ioctl_trace_preload_v2531 as v_ioctltrace
import native_audio_acdb_android_measurement_planner_v2396 as v2396
import native_audio_android_route_delta_handoff_v2365 as route

RUN_ID = "V2490"
BUILD_TAG = "v2490-audio-acdb-ownprocess-get-live"
ROOT = v_helper.ROOT
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
REMOTE_DIR = "/data/local/tmp/a90-acdb-ownget"
REMOTE_HELPER = f"{REMOTE_DIR}/{v_helper.ARTIFACT_NAME}"
REMOTE_IOCTL_TRACE_SO = f"{REMOTE_DIR}/{v_ioctltrace.ARTIFACT_NAME}"
REMOTE_EVENTS = f"{REMOTE_DIR}/acdb-ownget-events.jsonl"
ACDB_DEP_CLOSURE_DIR = ROOT / "workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib"
ACDB_DEP_LEGACY_DIR = v2489.VENDOR_DUMP
ACDB_DEP_LIBS = (
    "libaudcal.so",
    "libdiag.so",
    "libacdb-fts.so",
    "libacdbrtac.so",
    "libadiertac.so",
    "libacdbloader.so",
)
ACDB_DEP_LEGACY_LIBS = (
    "libaudcal.so",
    "libacdbloader.so",
)
ACDB_RUNTIME_EXTERNAL_LIBS = (
    "libtinyalsa.so",
    "libion.so",
    "libcutils.so",
    "libutils.so",
    "liblog.so",
    "libc++.so",
)
DEFAULT_SETTLE_ADB_RETRY_ATTEMPTS = 3
DEFAULT_SETTLE_ADB_RETRY_SLEEP_SEC = 2.0
TRANSIENT_SETTLE_ADB_FAILURE_MARKERS = (
    "error: closed",
    "adb: no devices/emulators found",
    "no devices/emulators found",
    "device offline",
    "failed to get feature set",
    "protocol fault",
)


def rel(path: Path | str) -> str:
    return v_helper.rel(Path(path) if not isinstance(path, Path) else path)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"v2490-acdb-ownprocess-get-{stamp}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def route_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        adb=args.adb,
        serial=args.serial,
        android_timeout=args.android_timeout,
        from_native=args.from_native,
        adb_command_timeout=args.adb_command_timeout,
        flash_timeout=args.flash_timeout,
    )


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command.extend(["-s", args.serial])
    return command


def adb_su(args: argparse.Namespace, script: str) -> list[str]:
    return adb_base(args) + ["shell", f"su -c {shlex.quote(script)}"]


def adb_push(args: argparse.Namespace, source: str, destination: str) -> list[str]:
    return adb_base(args) + ["push", source, destination]


def settle_adb_retry_attempts(args: argparse.Namespace) -> int:
    return max(1, int(getattr(args, "android_settle_adb_retry_attempts", DEFAULT_SETTLE_ADB_RETRY_ATTEMPTS)))


def settle_adb_retry_sleep_sec(args: argparse.Namespace) -> float:
    return max(0.0, float(getattr(args, "android_settle_adb_retry_sleep_sec", DEFAULT_SETTLE_ADB_RETRY_SLEEP_SEC)))


def sha256_file(path: Path) -> str:
    return v2489.sha256_file(path)


def sha256_zero(length: int) -> str:
    return hashlib.sha256(b"\0" * max(0, length)).hexdigest()


def int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def helper_artifact_state(path: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    state: dict[str, Any] = {"path": rel(path), "exists": path.exists()}
    if not path.exists():
        state["ok"] = False
        return state
    stat_result = path.stat()
    state.update({
        "size": stat_result.st_size,
        "mode": oct(stat_result.st_mode & 0o777),
        "group_or_world_writable": bool(stat_result.st_mode & 0o022),
        "sha256": sha256_file(path),
    })
    if expected_sha256:
        state["expected_sha256"] = expected_sha256
        state["sha256_ok"] = state["sha256"] == expected_sha256
    state["ok"] = bool(state["exists"] and state["size"] > 0 and state.get("sha256_ok", True))
    return state


def build_helper(args: argparse.Namespace) -> dict[str, Any]:
    build_args = argparse.Namespace(
        dry_run=False,
        build=True,
        build_root=args.helper_build_root,
        manifest_path=args.helper_manifest_path,
        clang=v_helper.TOOLCHAIN_ROOT / "bin/clang",
        lld=v_helper.TOOLCHAIN_ROOT / "bin/ld.lld",
        readelf=args.readelf,
        file=args.file,
    )
    return v_helper.manifest(build_args)


def build_ioctl_trace(args: argparse.Namespace) -> dict[str, Any]:
    build_args = argparse.Namespace(
        build=True,
        build_root=args.ioctl_trace_build_root,
        manifest_path=args.ioctl_trace_manifest_path,
        clang=None,
        lld=v_ioctltrace.TOOLCHAIN_ROOT / "bin/ld.lld",
        readelf=args.readelf,
        file=args.file,
    )
    return v_ioctltrace.manifest(build_args)


def selected_helper_state(args: argparse.Namespace) -> dict[str, Any]:
    if args.helper_path:
        return helper_artifact_state(args.helper_path, expected_sha256=args.helper_sha256)
    manifest_path = args.helper_manifest_path
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifact = manifest.get("build", {}).get("artifact", {})
            path = ROOT / artifact.get("path", "")
            expected = artifact.get("sha256")
            state = helper_artifact_state(path, expected_sha256=expected)
            state["manifest"] = rel(manifest_path)
            return state
        except Exception as error:
            return {"path": None, "exists": False, "ok": False, "error": str(error)}
    default_path = args.helper_build_root / "bin" / v_helper.ARTIFACT_NAME
    return helper_artifact_state(default_path)


def selected_ioctl_trace_state(args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "disable_ioctl_trace", False):
        return {"enabled": False, "ok": True, "path": None}
    if args.ioctl_trace_so:
        state = helper_artifact_state(args.ioctl_trace_so, expected_sha256=args.ioctl_trace_sha256)
        state["enabled"] = True
        return state
    manifest_path = args.ioctl_trace_manifest_path
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            binary = manifest.get("build", {}).get("binary", {})
            path = ROOT / binary.get("path", "")
            expected = binary.get("sha256")
            state = helper_artifact_state(path, expected_sha256=expected)
            state["manifest"] = rel(manifest_path)
            state["enabled"] = True
            return state
        except Exception as error:
            return {"enabled": True, "path": None, "exists": False, "ok": False, "error": str(error)}
    default_path = args.ioctl_trace_build_root / "bin" / v_ioctltrace.ARTIFACT_NAME
    state = helper_artifact_state(default_path)
    state["enabled"] = True
    return state



def fake_audio_cal_allocate_enabled(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "fake_audio_cal_allocate", False)) and not getattr(args, "disable_ioctl_trace", False)

def acdb_dependency_source() -> tuple[str, Path, tuple[str, ...]]:
    if all((ACDB_DEP_CLOSURE_DIR / name).exists() for name in ACDB_DEP_LIBS):
        return "v2506-vendor-ext4-closure", ACDB_DEP_CLOSURE_DIR, ACDB_DEP_LIBS
    return "v2324-legacy-two-lib-dump", ACDB_DEP_LEGACY_DIR, ACDB_DEP_LEGACY_LIBS


def acdb_dependency_states() -> dict[str, Any]:
    source_kind, source_dir, names = acdb_dependency_source()
    libs: list[dict[str, Any]] = []
    ok = True
    for name in names:
        path = source_dir / name
        state = helper_artifact_state(path)
        state["name"] = name
        state["remote_path"] = f"{REMOTE_DIR}/{name}"
        libs.append(state)
        ok = bool(ok and state.get("ok"))
    closure_missing = [name for name in ACDB_DEP_LIBS if not (ACDB_DEP_CLOSURE_DIR / name).exists()]
    return {
        "source_kind": source_kind,
        "source_dir": rel(source_dir),
        "closure_dir": rel(ACDB_DEP_CLOSURE_DIR),
        "closure_missing": closure_missing,
        "remote_dir": REMOTE_DIR,
        "libs": libs,
        "runtime_external_libs": list(ACDB_RUNTIME_EXTERNAL_LIBS),
        "ok": ok,
    }


def setup_command(args: argparse.Namespace) -> list[str]:
    script = f"""
set -eu
rm -rf {shlex.quote(REMOTE_DIR)}
mkdir -p {shlex.quote(REMOTE_DIR)} {shlex.quote(REMOTE_DIR + '/delta')}
chown shell:shell {shlex.quote(REMOTE_DIR)} {shlex.quote(REMOTE_DIR + '/delta')} 2>/dev/null || true
chmod 700 {shlex.quote(REMOTE_DIR)} {shlex.quote(REMOTE_DIR + '/delta')}
ls -ld {shlex.quote(REMOTE_DIR)} {shlex.quote(REMOTE_DIR + '/delta')}
ls -l /vendor/etc/acdbdata 2>/dev/null || true
ls -ld /vendor/etc/audconf /vendor/etc/audconf/OPEN 2>/dev/null || true
find /vendor/etc/audconf -maxdepth 2 -type f -name '*.acdb' -exec ls -l {{}} \\; 2>/dev/null | sort || true
ls -l /vendor/lib/libacdbloader.so /vendor/lib/libaudcal.so 2>/dev/null || true
""".strip()
    return adb_su(args, script)


def chmod_helper_command(args: argparse.Namespace) -> list[str]:
    script = f"""
set -eu
chmod 700 {shlex.quote(REMOTE_HELPER)}
chmod 600 {shlex.quote(REMOTE_IOCTL_TRACE_SO)} 2>/dev/null || true
chmod 600 {shlex.quote(REMOTE_DIR)}/*.so 2>/dev/null || true
sha256sum {shlex.quote(REMOTE_HELPER)} 2>/dev/null || toybox sha256sum {shlex.quote(REMOTE_HELPER)}
sha256sum {shlex.quote(REMOTE_IOCTL_TRACE_SO)} 2>/dev/null || true
ls -l {shlex.quote(REMOTE_DIR)}/*.so 2>/dev/null || true
file {shlex.quote(REMOTE_HELPER)} 2>/dev/null || true
file {shlex.quote(REMOTE_IOCTL_TRACE_SO)} 2>/dev/null || true
""".strip()
    return adb_su(args, script)


def execution_context_probe_command(args: argparse.Namespace) -> list[str]:
    context_path = f"{REMOTE_DIR}/ownget-exec-context.txt"
    script = f"""
set +e
{{
  echo '### adb-su-shell-id'
  id 2>&1 || true
  id -Z 2>&1 || true
  echo '### getenforce'
  getenforce 2>&1 || true
  echo '### proc-self-status'
  grep -E '^(Name|Uid|Gid|Groups|Cap(Inh|Prm|Eff|Bnd|Amb)|NoNewPrivs|Seccomp):' /proc/self/status 2>&1 || true
  echo '### ps-self'
  ps -AZ -p $$ 2>&1 || ps -Z -p $$ 2>&1 || ps -p $$ -o USER,PID,PPID,ARGS 2>&1 || true
  echo '### helper-label'
  ls -lZ {shlex.quote(REMOTE_HELPER)} 2>&1 || ls -l {shlex.quote(REMOTE_HELPER)} 2>&1 || true
  echo '### msm-audio-cal-node'
  ls -lZ /dev/msm_audio_cal 2>&1 || ls -l /dev/msm_audio_cal 2>&1 || true
  echo '### vendor-audio-prop-file'
  ls -lZ /dev/__properties__/u:object_r:vendor_audio_prop:s0 2>&1 || ls -l /dev/__properties__/u:object_r:vendor_audio_prop:s0 2>&1 || true
  echo '### vendor-audio-calfile0-prop'
  getprop persist.vendor.audio.calfile0 2>&1 || true
}} > {shlex.quote(context_path)} 2>&1
exit 0
""".strip()
    return adb_su(args, script)


def run_helper_command(args: argparse.Namespace) -> list[str]:
    ld_library_path = ":".join([REMOTE_DIR, "/vendor/lib", "/system/lib", "/system_ext/lib", "/product/lib"])
    trace_enabled = not getattr(args, "disable_ioctl_trace", False)
    fake_allocate = fake_audio_cal_allocate_enabled(args)
    fake_allocate_prefix = "A90_ACDB_FAKE_ALLOCATE=1 " if fake_allocate else ""
    preload_prefix = f"LD_PRELOAD={shlex.quote(REMOTE_IOCTL_TRACE_SO)} " if trace_enabled else ""
    script = f"""
set +e
cd {shlex.quote(REMOTE_DIR)} || exit 61
rm -f ownget.stdout.txt ownget.stderr.txt ownget.rc ownget-run-context.txt ioctl-trace-events.jsonl
{{
  echo '### run-shell-id'
  id 2>&1 || true
  id -Z 2>&1 || true
  echo '### run-env'
  echo 'LD_PRELOAD={REMOTE_IOCTL_TRACE_SO if trace_enabled else ""}'
  echo 'A90_ACDB_FAKE_ALLOCATE={"1" if fake_allocate else ""}'
  echo 'LD_LIBRARY_PATH={ld_library_path}'
  echo '### run-proc-self-status'
  grep -E '^(Name|Uid|Gid|Groups|Cap(Inh|Prm|Eff|Bnd|Amb)|NoNewPrivs|Seccomp):' /proc/self/status 2>&1 || true
}} > ownget-run-context.txt 2>&1
{fake_allocate_prefix}{preload_prefix}LD_LIBRARY_PATH={shlex.quote(ld_library_path)} {shlex.quote(REMOTE_HELPER)} > ownget.stdout.txt 2> ownget.stderr.txt
rc=$?
echo "$rc" > ownget.rc
cat ownget.rc
exit 0
""".strip()
    return adb_su(args, script)


def clear_logcat_command(args: argparse.Namespace) -> list[str]:
    script = """
set +e
logcat -c >/dev/null 2>&1
exit 0
""".strip()
    return adb_su(args, script)


def capture_logcat_command(args: argparse.Namespace) -> list[str]:
    acdb_log = f"{REMOTE_DIR}/logcat-acdb-loader.txt"
    filtered_log = f"{REMOTE_DIR}/logcat-avc-acdb-filter.txt"
    dmesg_log = f"{REMOTE_DIR}/dmesg-avc-acdb-filter.txt"
    script = f"""
set +e
logcat -d -v threadtime -s ACDB-LOADER > {shlex.quote(acdb_log)} 2>&1
logcat -d -b all -v threadtime 2>/dev/null | grep -Ei 'avc:|denied|ACDB-LOADER|acdb|audcal' > {shlex.quote(filtered_log)} 2>/dev/null || true
dmesg 2>/dev/null | grep -Ei 'avc:|denied|ACDB-LOADER|acdb|audcal' > {shlex.quote(dmesg_log)} 2>/dev/null || true
exit 0
""".strip()
    return adb_su(args, script)


def collect_prepare_command(args: argparse.Namespace) -> list[str]:
    script = f"""
set +e
cd {shlex.quote(REMOTE_DIR)} || exit 0
ls -la > listing.txt 2>&1
[ -f {shlex.quote(REMOTE_EVENTS)} ] && cat {shlex.quote(REMOTE_EVENTS)} > events.copy.jsonl 2>/dev/null
find . -maxdepth 1 -type f -name 'acdb-ownget-*.bin' -exec sha256sum {{}} \\; > raw-sha256s.txt 2>/dev/null
chmod 755 . 2>/dev/null || true
find . -maxdepth 1 -type f -exec chmod 644 {{}} \\; 2>/dev/null || true
chmod 755 ./delta 2>/dev/null || true
exit 0
""".strip()
    return adb_su(args, script)


def pull_artifacts_command(args: argparse.Namespace, destination: str) -> list[str]:
    return adb_base(args) + ["pull", REMOTE_DIR, destination]


def cleanup_command(args: argparse.Namespace) -> list[str]:
    return adb_su(args, f"rm -rf {shlex.quote(REMOTE_DIR)}")


def timeout_step_record(name: str, command: list[str], out_dir: Path, timeout_sec: float, error: Exception) -> dict[str, Any]:
    stdout_path = out_dir / f"{name}.stdout.txt"
    stderr_path = out_dir / f"{name}.stderr.txt"
    return {
        "name": name,
        "command": command,
        "timeout_sec": timeout_sec,
        "timeout": True,
        "ok": False,
        "stdout": rel(stdout_path),
        "stderr": rel(stderr_path),
        "error": str(error),
        "finished_at": now_iso(),
    }


def command_safety(payload: dict[str, Any]) -> dict[str, Any]:
    flat = json.dumps(payload.get("commands", payload), sort_keys=True)
    forbidden = {
        "magisk_install": "magisk --install-module",
        "hal_restart": "android.hardware.audio.service",
        "audio_track": "AudioTrack",
        "tinyplay": "tinyplay",
        "tinymix": "tinymix",
        "native_cal_set_constant": "0xc00461cb",
        "native_msm_audio_cal_set_combo": "/dev/msm_audio_cal 0xc00461cb",
        "broad_module_delete": "rm -rf /data/adb/modules",
        "fastboot": "fastboot",
    }
    findings = [
        {"name": name, "needle": needle}
        for name, needle in forbidden.items()
        if needle in flat
    ]
    return {"ok": not findings, "findings": findings, "forbidden": sorted(forbidden)}


def step_output_text(step: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("stdout", "stderr"):
        value = step.get(key)
        if not isinstance(value, str) or not value:
            continue
        path = Path(value)
        if not path.is_absolute():
            path = ROOT / path
        try:
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(parts)


def step_has_transient_settle_adb_failure(step: dict[str, Any]) -> bool:
    if step.get("ok"):
        return False
    lower_text = step_output_text(step).lower()
    return any(marker.lower() in lower_text for marker in TRANSIENT_SETTLE_ADB_FAILURE_MARKERS)


def step_has_transient_staging_adb_failure(step: dict[str, Any]) -> bool:
    return step_has_transient_settle_adb_failure(step)


def step_failure_message(name: str, step: dict[str, Any]) -> str:
    return f"{name} failed rc={step.get('rc')}; see {step.get('stdout')} {step.get('stderr')}"


def run_settle_command_with_transport_retry(
    args: argparse.Namespace,
    *,
    index: int,
    command: list[str],
    out_dir: Path,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    attempts = settle_adb_retry_attempts(args)
    sleep_sec = settle_adb_retry_sleep_sec(args)
    last_step: dict[str, Any] | None = None
    for attempt in range(1, attempts + 1):
        if attempt > 1:
            steps.append(route.run_step(
                f"android-post-handoff-settle-{index}-retry-{attempt}-wait-for-device",
                adb_base(args) + ["wait-for-device"],
                out_dir,
                timeout_sec=args.adb_command_timeout,
                check=False,
            ))
        name = f"android-post-handoff-settle-{index}" if attempt == 1 else f"android-post-handoff-settle-{index}-retry-{attempt}"
        step = route.run_step(name, command, out_dir, timeout_sec=args.adb_command_timeout, check=False)
        steps.append(step)
        last_step = step
        if step.get("ok"):
            if attempt > 1:
                step["settle_retry_recovered"] = True
                step["settle_retry_attempt"] = attempt
            return step
        if not step_has_transient_settle_adb_failure(step):
            raise RuntimeError(step_failure_message(name, step))
        step["settle_retry_reason"] = "transient-adb-transport"
        if attempt < attempts:
            time.sleep(sleep_sec)
    assert last_step is not None
    raise RuntimeError(
        f"android-post-handoff-settle-{index} transient ADB transport failure persisted "
        f"after {attempts} attempts; see {last_step.get('stdout')} {last_step.get('stderr')}"
    )


def run_android_post_handoff_settle_with_transport_retry(
    args: argparse.Namespace,
    out_dir: Path,
    steps: list[dict[str, Any]],
) -> None:
    commands = v2396.android_post_handoff_settle_commands(args)
    for index, command in enumerate(commands):
        if index in {0, 1}:
            run_settle_command_with_transport_retry(args, index=index, command=command, out_dir=out_dir, steps=steps)
            continue

        attempts = max(1, int(getattr(args, "android_root_recheck_attempts", v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS)))
        sleep_sec = max(0.0, float(getattr(args, "android_root_recheck_sleep_sec", v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC)))
        last_record: dict[str, Any] | None = None
        for attempt in range(1, attempts + 1):
            name = "android-post-handoff-settle-2" if attempt == 1 else f"android-post-handoff-settle-2-retry-{attempt}"
            record = route.run_step(name, command, out_dir, timeout_sec=args.adb_command_timeout, check=False)
            steps.append(record)
            summary = v2396.android_root_recheck_summary(record)
            summary["attempt"] = attempt
            summary["max_attempts"] = attempts
            record["root_recheck"] = summary
            last_record = record
            if summary["root_ready"]:
                record["settle_decision"] = "android-root-ready"
                return
            record["settle_decision"] = summary["classification"]
            if attempt != attempts:
                time.sleep(sleep_sec)

        if last_record is not None:
            v2396.validate_android_root_recheck(last_record)
        raise RuntimeError("android root recheck did not run")


def append_android_staging_resettle_steps(
    args: argparse.Namespace,
    *,
    label: str,
    attempt: int,
    out_dir: Path,
    steps: list[dict[str, Any]],
) -> None:
    settle_commands = v2396.android_post_handoff_settle_commands(args)
    probes = (
        ("wait-for-device", adb_base(args) + ["wait-for-device"]),
        ("boot-complete", settle_commands[1]),
        ("root-id", settle_commands[2]),
    )
    for suffix, command in probes:
        record = route.run_step(
            f"{label}-retry-{attempt}-resettle-{suffix}",
            command,
            out_dir,
            timeout_sec=args.adb_command_timeout,
            check=False,
        )
        record["staging_retry_resettle"] = True
        record["staging_retry_attempt"] = attempt
        steps.append(record)


def run_early_staging_command_with_transport_retry(
    args: argparse.Namespace,
    *,
    name: str,
    command: list[str],
    out_dir: Path,
    steps: list[dict[str, Any]],
    timeout_sec: float,
) -> dict[str, Any]:
    attempts = settle_adb_retry_attempts(args)
    sleep_sec = settle_adb_retry_sleep_sec(args)
    last_step: dict[str, Any] | None = None
    for attempt in range(1, attempts + 1):
        if attempt > 1:
            append_android_staging_resettle_steps(args, label=name, attempt=attempt, out_dir=out_dir, steps=steps)
        step_name = name if attempt == 1 else f"{name}-retry-{attempt}"
        step = route.run_step(step_name, command, out_dir, timeout_sec=timeout_sec, check=False)
        step["early_staging_retry_attempt"] = attempt
        steps.append(step)
        last_step = step
        if step.get("ok"):
            if attempt > 1:
                step["early_staging_retry_recovered"] = True
            return step
        if not step_has_transient_staging_adb_failure(step):
            raise RuntimeError(step_failure_message(step_name, step))
        step["early_staging_retry_reason"] = "transient-adb-transport"
        if attempt < attempts:
            time.sleep(sleep_sec)
    assert last_step is not None
    raise RuntimeError(
        f"{name} transient ADB transport failure persisted after {attempts} attempts; "
        f"see {last_step.get('stdout')} {last_step.get('stderr')}"
    )


def parse_ownget_artifacts(path: Path) -> dict[str, Any]:
    events = path / "acdb-ownget-events.jsonl"
    acdb_log = path / "logcat-acdb-loader.txt"
    filtered_log = path / "logcat-avc-acdb-filter.txt"
    dmesg_log = path / "dmesg-avc-acdb-filter.txt"
    exec_context = path / "ownget-exec-context.txt"
    run_context = path / "ownget-run-context.txt"
    helper_rc_file = path / "ownget.rc"
    helper_stderr_file = path / "ownget.stderr.txt"
    ioctl_trace = path / "ioctl-trace-events.jsonl"
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    namespace_events: list[dict[str, Any]] = []
    symbol_events: list[dict[str, Any]] = []
    ioctl_trace_events: list[dict[str, Any]] = []
    malformed = 0
    if events.exists():
        for line in events.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if item.get("event") == "acdb_ioctl":
                rows.append(item)
            elif item.get("event") == "error":
                errors.append(item)
            elif item.get("event") == "symbol_probe":
                symbol_events.append(item)
            elif str(item.get("event", "")).startswith("namespace_"):
                namespace_events.append(item)
    if ioctl_trace.exists():
        for line in ioctl_trace.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if item.get("event") == "ioctl_trace":
                ioctl_trace_events.append(item)
    acdb_log_text = acdb_log.read_text(encoding="utf-8", errors="replace") if acdb_log.exists() else ""
    filtered_log_text = filtered_log.read_text(encoding="utf-8", errors="replace") if filtered_log.exists() else ""
    dmesg_log_text = dmesg_log.read_text(encoding="utf-8", errors="replace") if dmesg_log.exists() else ""
    exec_context_text = exec_context.read_text(encoding="utf-8", errors="replace") if exec_context.exists() else ""
    run_context_text = run_context.read_text(encoding="utf-8", errors="replace") if run_context.exists() else ""
    helper_stderr_text = helper_stderr_file.read_text(encoding="utf-8", errors="replace") if helper_stderr_file.exists() else ""
    helper_rc = int_or_none(helper_rc_file.read_text(encoding="utf-8", errors="replace").strip()) if helper_rc_file.exists() else None
    diagnostic_text = "\n".join([
        acdb_log_text,
        filtered_log_text,
        dmesg_log_text,
        exec_context_text,
        run_context_text,
        helper_stderr_text,
    ]).lower()
    helper_sigsegv = helper_rc == 139 or "segmentation fault" in helper_stderr_text.lower() or "sigsegv" in diagnostic_text
    allocate_ioctl_events = [
        event for event in ioctl_trace_events
        if str(event.get("request", "")).lower() == "0xc00461c8"
        or event.get("name") == "AUDIO_ALLOCATE_CALIBRATION"
    ]
    set_ioctl_events = [
        event for event in ioctl_trace_events
        if str(event.get("request", "")).lower() == "0xc00461cb"
        or event.get("name") == "AUDIO_SET_CALIBRATION"
    ]
    deallocate_ioctl_events = [
        event for event in ioctl_trace_events
        if str(event.get("request", "")).lower() == "0xc00461c9"
        or event.get("name") == "AUDIO_DEALLOCATE_CALIBRATION"
    ]
    audio_set_fake_success_count = sum(
        1 for event in set_ioctl_events if event.get("intercept") == "fake-success"
    )
    audio_set_pass_through_count = sum(
        1 for event in set_ioctl_events if event.get("intercept") != "fake-success"
    )
    has_msm_audio_cal_open_denied = "cannot open /dev/msm_audio_cal errno: 13" in diagnostic_text
    has_audio_allocate_calibration_failed = (
        "sending audio_allocate_calibration" in diagnostic_text
        or "allocate_cal_block failed" in diagnostic_text
        or "cannot allocate memory" in diagnostic_text
    )
    has_vendor_audio_prop_denied = (
        'access denied finding property "persist.vendor.audio.calfile0"' in diagnostic_text
        or "access denied finding property 'persist.vendor.audio.calfile0'" in diagnostic_text
        or "denied finding property \"persist.vendor.audio.calfile0\"" in diagnostic_text
        or (
            "vendor_audio_prop" in filtered_log_text.lower()
            and ("avc: denied" in filtered_log_text.lower() or "access denied" in filtered_log_text.lower())
        )
        or (
            "vendor_audio_prop" in dmesg_log_text.lower()
            and ("avc: denied" in dmesg_log_text.lower() or "access denied" in dmesg_log_text.lower())
        )
    )
    has_shell_domain_context = "u:r:shell:s0" in diagnostic_text
    target = [row for row in rows if row.get("is_target_4916") is True or row.get("out_len") == 4916]
    raw_files = sorted(path.glob("acdb-ownget-*.bin"))
    missing_raw = []
    raw_size_mismatch = []
    raw_sha_mismatch = []
    zero_raw_seq = []
    successful_rows = []
    successful_nonzero_rows = []
    target_success = []
    target_ret_failed = []
    ret_values = set()
    zero_hash_by_len: dict[int, str] = {}
    for row in rows:
        ret = int_or_none(row.get("ret"))
        out_len = int_or_none(row.get("out_len"))
        if ret is not None:
            ret_values.add(ret)
        if out_len is not None:
            zero_hash_by_len[out_len] = sha256_zero(out_len)
        if row.get("is_target_4916") is True or out_len == 4916:
            if ret != 0:
                target_ret_failed.append(row.get("seq"))
        raw_path = row.get("raw_path")
        if not raw_path:
            missing_raw.append(row.get("seq"))
            continue
        local = path / Path(str(raw_path)).name
        if not local.exists():
            missing_raw.append(row.get("seq"))
            continue
        raw_data = local.read_bytes()
        raw_sha = hashlib.sha256(raw_data).hexdigest()
        if out_len is not None and len(raw_data) != out_len:
            raw_size_mismatch.append(row.get("seq"))
        if row.get("sha256") and str(row.get("sha256")).lower() != raw_sha:
            raw_sha_mismatch.append(row.get("seq"))
        is_zero = out_len is not None and raw_sha == zero_hash_by_len[out_len]
        if is_zero:
            zero_raw_seq.append(row.get("seq"))
        valid_raw = out_len is None or len(raw_data) == out_len
        if ret == 0 and valid_raw:
            successful_rows.append(row)
            if not is_zero:
                successful_nonzero_rows.append(row)
            if (row.get("is_target_4916") is True or out_len == 4916) and not is_zero:
                target_success.append(row)
    context_only = bool(
        exec_context.exists()
        or run_context.exists()
        or helper_rc_file.exists()
        or helper_stderr_file.exists()
        or acdb_log.exists()
        or filtered_log.exists()
        or dmesg_log.exists()
    )
    no_raw_problems = not missing_raw and not raw_size_mismatch
    if audio_set_pass_through_count:
        classification = "ownprocess-real-audio-set-passthrough"
    elif target_success and no_raw_problems:
        classification = "acdb-get-success-4916"
    elif successful_nonzero_rows and no_raw_problems:
        classification = "acdb-get-full-outbuf-set-no-4916"
    elif rows and no_raw_problems and not successful_rows and len(zero_raw_seq) == len(rows):
        classification = "acdb-get-dispatch-ret-failed-zero-outbuf"
    elif rows and no_raw_problems and not successful_rows:
        classification = "acdb-get-dispatch-ret-failed"
    elif rows and no_raw_problems:
        classification = "acdb-get-no-successful-nonzero-outbuf"
    elif rows:
        classification = "acdb-get-outbuf-set-missing-or-invalid-raw"
    elif errors and not rows:
        stage = str(errors[-1].get("stage", "unknown"))
        if stage in {"dlsym-android_get_exported_namespace", "dlsym-android_dlopen_ext"}:
            classification = "namespace-api-symbol-missing"
        elif stage == "namespace-none-visible":
            classification = "namespace-none-visible"
        elif stage == "namespace-visible-load-failed-libaudcal":
            classification = "namespace-visible-load-failed"
        elif stage == "android_dlopen_ext-libacdbloader":
            classification = "libaudcal-loaded-libacdbloader-block"
        elif stage == "acdb_loader_init_v3":
            if "could not load .acdb files" in diagnostic_text:
                classification = "init-v3-block-acdb-files-load"
            elif "error initializing acph returned" in diagnostic_text:
                classification = "init-v3-block-acph-init"
            elif has_audio_allocate_calibration_failed:
                classification = "init-v3-block-audio-allocate-calibration-failed"
            elif has_msm_audio_cal_open_denied:
                classification = "init-v3-block-msm-audio-cal-open-denied"
            elif has_vendor_audio_prop_denied:
                classification = "init-v3-block-vendor-audio-prop-denied"
            elif "avc:" in diagnostic_text or "denied" in diagnostic_text:
                classification = "init-v3-block-avc-denial"
            else:
                classification = "init-v3-block"
        else:
            classification = f"ownprocess-error-{stage}"
    elif malformed:
        classification = "ownprocess-events-malformed"
    elif helper_sigsegv:
        classification = "ownprocess-helper-sigsegv-no-events"
    elif context_only:
        classification = "ownprocess-context-only-no-events"
    else:
        classification = "ownprocess-no-events"
    partial_success = classification == "acdb-get-full-outbuf-set-no-4916"
    full_success = classification == "acdb-get-success-4916"
    return {
        "classification": classification,
        "event_path": rel(events) if events.exists() else None,
        "rows": rows,
        "errors": errors,
        "namespace_events": namespace_events,
        "symbol_events": symbol_events,
        "ioctl_trace_events": ioctl_trace_events,
        "diagnostics": {
            "acdb_loader_log_path": rel(acdb_log) if acdb_log.exists() else None,
            "filtered_log_path": rel(filtered_log) if filtered_log.exists() else None,
            "dmesg_filter_path": rel(dmesg_log) if dmesg_log.exists() else None,
            "exec_context_path": rel(exec_context) if exec_context.exists() else None,
            "run_context_path": rel(run_context) if run_context.exists() else None,
            "helper_rc_path": rel(helper_rc_file) if helper_rc_file.exists() else None,
            "helper_stderr_path": rel(helper_stderr_file) if helper_stderr_file.exists() else None,
            "helper_rc": helper_rc,
            "helper_sigsegv": helper_sigsegv,
            "helper_stderr_tail": helper_stderr_text[-256:],
            "ioctl_trace_path": rel(ioctl_trace) if ioctl_trace.exists() else None,
            "acdb_loader_line_count": len(acdb_log_text.splitlines()),
            "filtered_log_line_count": len(filtered_log_text.splitlines()),
            "dmesg_filter_line_count": len(dmesg_log_text.splitlines()),
            "exec_context_line_count": len(exec_context_text.splitlines()),
            "run_context_line_count": len(run_context_text.splitlines()),
            "ioctl_trace_event_count": len(ioctl_trace_events),
            "audio_allocate_ioctl_count": len(allocate_ioctl_events),
            "audio_allocate_ioctl_errno_values": sorted({
                int_or_none(event.get("errno"))
                for event in allocate_ioctl_events
                if int_or_none(event.get("errno")) is not None
            }),
            "audio_allocate_ioctl_ret_values": sorted({
                int_or_none(event.get("ret"))
                for event in allocate_ioctl_events
                if int_or_none(event.get("ret")) is not None
            }),
            "audio_allocate_ioctl_intercepts": sorted({
                str(event.get("intercept"))
                for event in allocate_ioctl_events
                if event.get("intercept") is not None
            }),
            "audio_allocate_ioctl_fake_success_count": sum(
                1 for event in allocate_ioctl_events if event.get("intercept") == "fake-success"
            ),
            "audio_allocate_arg_snapshots": [
                event.get("arg_snapshot")
                for event in allocate_ioctl_events
                if isinstance(event.get("arg_snapshot"), dict)
            ],
            "audio_deallocate_ioctl_count": len(deallocate_ioctl_events),
            "audio_deallocate_ioctl_intercepts": sorted({
                str(event.get("intercept"))
                for event in deallocate_ioctl_events
                if event.get("intercept") is not None
            }),
            "audio_deallocate_ioctl_fake_success_count": sum(
                1 for event in deallocate_ioctl_events if event.get("intercept") == "fake-success"
            ),
            "audio_set_ioctl_count": len(set_ioctl_events),
            "audio_set_ioctl_intercepts": sorted({
                str(event.get("intercept"))
                for event in set_ioctl_events
                if event.get("intercept") is not None
            }),
            "audio_set_ioctl_fake_success_count": audio_set_fake_success_count,
            "audio_set_ioctl_pass_through_count": audio_set_pass_through_count,
            "has_acdb_files_load_error": "could not load .acdb files" in diagnostic_text,
            "has_acph_init_error": "error initializing acph returned" in diagnostic_text,
            "has_audio_allocate_calibration_failed": has_audio_allocate_calibration_failed,
            "has_avc_or_denial": "avc:" in diagnostic_text or "denied" in diagnostic_text,
            "has_msm_audio_cal_open_denied": has_msm_audio_cal_open_denied,
            "has_vendor_audio_prop_denied": has_vendor_audio_prop_denied,
            "has_shell_domain_context": has_shell_domain_context,
            "ret_values": sorted(ret_values),
            "successful_row_count": len(successful_rows),
            "successful_nonzero_row_count": len(successful_nonzero_rows),
            "target_4916_success_count": len(target_success),
            "target_4916_ret_failed_seq": target_ret_failed,
            "zero_outbuf_count": len(zero_raw_seq),
            "zero_outbuf_seq": zero_raw_seq,
            "zero_hash_by_len": {str(key): value for key, value in sorted(zero_hash_by_len.items())},
            "raw_size_mismatch_seq": raw_size_mismatch,
            "raw_sha_mismatch_seq": raw_sha_mismatch,
        },
        "malformed_lines": malformed,
        "row_count": len(rows),
        "error_count": len(errors),
        "namespace_event_count": len(namespace_events),
        "symbol_event_count": len(symbol_events),
        "target_4916_count": len(target),
        "raw_file_count": len(raw_files),
        "missing_raw_seq": missing_raw,
        "full_success": full_success,
        "partial_success": partial_success,
        "operator_valuable": bool(full_success or partial_success or rows or errors or context_only),
        "counts_toward_fails_twice": not bool(full_success or partial_success),
    }


def select_pulled_artifact_dir(path: Path) -> Path:
    nested = path / "a90-acdb-ownget"
    if (nested / "acdb-ownget-events.jsonl").exists() or (nested / "listing.txt").exists():
        return nested
    return path


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    android_boot = route.select_android_boot_candidate()
    rollback = route.file_state(route.ROLLBACK_IMAGE, expected_sha256=route.ROLLBACK_SHA256)
    helper = selected_helper_state(args)
    ioctl_trace = selected_ioctl_trace_state(args)
    deps = acdb_dependency_states()
    sealed_boot = "<private-run-dir>/android_boot_0600.img"
    helper_remote = REMOTE_HELPER
    commands = {
        "flash_android": route.flash_android_command(route_args(args), sealed_boot),
        "post_handoff_settle": ["adb wait-for-device + boot-complete + su id with bounded retries"],
        "setup": setup_command(args),
        "push_helper": adb_push(args, helper.get("path") or "<helper>", helper_remote),
        "push_ioctl_trace_preload": (
            adb_push(args, ioctl_trace.get("path") or "<ioctl-trace-so>", REMOTE_IOCTL_TRACE_SO)
            if ioctl_trace.get("enabled")
            else ["disabled"]
        ),
        "push_acdb_dependencies": [
            adb_push(args, item.get("path") or "<missing>", item.get("remote_path") or "<remote>")
            for item in deps["libs"]
        ],
        "chmod_helper": chmod_helper_command(args),
        "probe_execution_context": execution_context_probe_command(args),
        "clear_logcat_before_helper": clear_logcat_command(args),
        "run_helper": run_helper_command(args),
        "capture_logcat_after_helper": capture_logcat_command(args),
        "collect_prepare": collect_prepare_command(args),
        "pull_artifacts": pull_artifacts_command(args, "<private-run-dir>/ownget-device-artifacts"),
        "cleanup": cleanup_command(args),
        "android_reboot_recovery_for_rollback": route.android_reboot_recovery_command(route_args(args)),
        "rollback_v2321": route.rollback_command(route_args(args)),
    }
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2490-acdb-ownprocess-get-live-runner-dry-run",
        "host_only": True,
        "device_action": "none",
        "android_boot": android_boot,
        "rollback": rollback,
        "helper": helper,
        "ioctl_trace_preload": ioctl_trace,
        "acdb_dependencies": deps,
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "commands": commands,
        "android_settle_adb_retry": {
            "enabled": settle_adb_retry_attempts(args) > 1,
            "attempts": settle_adb_retry_attempts(args),
            "sleep_sec": settle_adb_retry_sleep_sec(args),
            "scope": (
                "android-post-handoff-settle-0/1 plus early staging transport-only failures "
                "before helper execution"
            ),
            "retry_markers": list(TRANSIENT_SETTLE_ADB_FAILURE_MARKERS),
            "semantic_failures_fail_closed": True,
            "early_staging_scope": [
                "ownget-setup",
                "ownget-push-helper",
                "ownget-push-ioctl-trace-preload",
                "ownget-push-<acdb-dependency>",
                "ownget-chmod-helper",
                "ownget-probe-execution-context",
                "ownget-logcat-clear",
            ],
            "helper_execution_retry": False,
            "v2515_gap": "android-post-handoff-settle-1 failed with adb 'error: closed' before helper staging",
            "v2532_gap": "ownget-setup failed with adb 'error: closed' after root settle and before helper staging",
        },
        "ioctl_trace_policy": {
            "enabled": bool(ioctl_trace.get("enabled")),
            "mechanism": (
                "own-process LD_PRELOAD ioctl observer; optional fake-success for "
                "AUDIO_ALLOCATE/DEALLOCATE/SET only"
            ),
            "fake_audio_cal_allocate": fake_audio_cal_allocate_enabled(args),
            "fake_mode_env": "A90_ACDB_FAKE_ALLOCATE=1" if fake_audio_cal_allocate_enabled(args) else "",
            "target_request": "AUDIO_ALLOCATE_CALIBRATION 0xc00461c8",
            "required_evidence": ["ioctl-trace-events.jsonl", "dmesg-avc-acdb-filter.txt", "logcat-avc-acdb-filter.txt"],
        },
        "partial_success_policy": "captured-ownprocess-outbuf-set-no-4916 is preserved as operator-valuable partial evidence; ACDB tap no-4916 policy remains non-dead-run",
        "hard_boundary": [
            "own-process helper only; no in-HAL LD_PRELOAD/injection",
            "own-process LD_PRELOAD ioctl trace observes existing calls by default",
            "if --fake-audio-cal-allocate is set, AUDIO_ALLOCATE/DEALLOCATE/SET are no-op success in-process only",
            "no Magisk module install",
            "no HAL restart",
            "no AudioTrack/playback",
            "no native speaker write",
            "no /dev/msm_audio_cal SET path",
            "only read-only identity/label probes of /dev/msm_audio_cal",
            "boot partition only through native_init_flash.py",
            "rollback to V2321 after capture",
        ],
        "live_ready": bool(
            android_boot.get("ok")
            and rollback.get("ok")
            and helper.get("ok")
            and ioctl_trace.get("ok")
            and deps.get("ok")
        ),
        "live_blockers": [],
    }
    if not android_boot.get("ok"):
        payload["live_blockers"].append("Android boot candidate missing or invalid")
    if not rollback.get("ok"):
        payload["live_blockers"].append("V2321 rollback image missing or invalid")
    if not helper.get("ok"):
        payload["live_blockers"].append("V2489 helper artifact missing or invalid; run V2489 builder first")
    if not ioctl_trace.get("ok"):
        payload["live_blockers"].append("V2531 ioctl trace preload missing or invalid; run V2531 builder first")
    if not deps.get("ok"):
        payload["live_blockers"].append("ACDB dependency set missing from selected private dependency source")
    if deps.get("source_kind") != "v2506-vendor-ext4-closure":
        payload["live_blockers"].append("V2506 ACDB dependency closure not prepared; run prepare_audio_acdb_dependency_closure_v2506.py")
    payload["command_safety"] = command_safety(payload)
    payload["ok"] = bool(payload["live_ready"] and payload["command_safety"]["ok"])
    return payload


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    if args.build_helper:
        build_helper(args)
    if args.build_ioctl_trace and not args.disable_ioctl_trace:
        build_ioctl_trace(args)
    payload = dry_run_payload(args)
    if not payload.get("live_ready"):
        raise RuntimeError(f"live inputs are not ready: {payload.get('live_blockers')}")
    if not payload.get("command_safety", {}).get("ok"):
        raise RuntimeError(f"command safety failed: {payload['command_safety']}")

    out_dir = args.out_dir or default_live_out_dir()
    out_dir.mkdir(parents=True, exist_ok=False)
    os.chmod(out_dir, 0o700)
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2490-acdb-ownprocess-get-live-started",
        "out_dir": rel(out_dir),
        "plan": payload,
        "steps": steps,
        "rolled_back": False,
        "ok": False,
    }
    write_json(out_dir / "result.json", result)

    android_boot_state = route.copy_sealed_android_boot(payload["android_boot"]["selected"], out_dir)
    result["sealed_android_boot"] = android_boot_state
    write_json(out_dir / "result.json", result)

    rollback_needed = False
    try:
        rollback_needed = True
        steps.append(route.run_step(
            "flash-android",
            route.flash_android_command(route_args(args), str(out_dir / "android_boot_0600.img")),
            out_dir,
            timeout_sec=args.flash_timeout,
        ))
        run_android_post_handoff_settle_with_transport_retry(args, out_dir, steps)
        run_early_staging_command_with_transport_retry(
            args,
            name="ownget-setup",
            command=setup_command(args),
            out_dir=out_dir,
            steps=steps,
            timeout_sec=args.adb_command_timeout,
        )
        helper_path = ROOT / payload["helper"]["path"]
        run_early_staging_command_with_transport_retry(
            args,
            name="ownget-push-helper",
            command=adb_push(args, rel(helper_path), REMOTE_HELPER),
            out_dir=out_dir,
            steps=steps,
            timeout_sec=args.adb_command_timeout,
        )
        if payload["ioctl_trace_preload"].get("enabled"):
            trace_path = ROOT / payload["ioctl_trace_preload"]["path"]
            run_early_staging_command_with_transport_retry(
                args,
                name="ownget-push-ioctl-trace-preload",
                command=adb_push(args, rel(trace_path), REMOTE_IOCTL_TRACE_SO),
                out_dir=out_dir,
                steps=steps,
                timeout_sec=args.adb_command_timeout,
            )
        for dep in payload["acdb_dependencies"]["libs"]:
            dep_path = ROOT / dep["path"]
            run_early_staging_command_with_transport_retry(
                args,
                name=f"ownget-push-{dep['name']}",
                command=adb_push(args, rel(dep_path), dep["remote_path"]),
                out_dir=out_dir,
                steps=steps,
                timeout_sec=args.adb_command_timeout,
            )
        run_early_staging_command_with_transport_retry(
            args,
            name="ownget-chmod-helper",
            command=chmod_helper_command(args),
            out_dir=out_dir,
            steps=steps,
            timeout_sec=args.adb_command_timeout,
        )
        run_early_staging_command_with_transport_retry(
            args,
            name="ownget-probe-execution-context",
            command=execution_context_probe_command(args),
            out_dir=out_dir,
            steps=steps,
            timeout_sec=args.adb_command_timeout,
        )
        run_early_staging_command_with_transport_retry(
            args,
            name="ownget-logcat-clear",
            command=clear_logcat_command(args),
            out_dir=out_dir,
            steps=steps,
            timeout_sec=args.adb_command_timeout,
        )
        helper_timeout = False
        try:
            steps.append(route.run_step("ownget-run-helper", run_helper_command(args), out_dir, timeout_sec=args.helper_timeout, check=False))
        except RuntimeError as helper_error:
            helper_timeout = "timed out" in str(helper_error).lower()
            if not helper_timeout:
                raise
            steps.append(timeout_step_record("ownget-run-helper", run_helper_command(args), out_dir, args.helper_timeout, helper_error))
            result["helper_timeout_error"] = str(helper_error)
            result["decision"] = "v2490-ownget-run-helper-timeout-before-salvage"
        steps.append(route.run_step("ownget-logcat-capture", capture_logcat_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step("ownget-collect-prepare", collect_prepare_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        local_artifacts = out_dir / "ownget-device-artifacts"
        steps.append(route.run_step("ownget-pull-artifacts", pull_artifacts_command(args, str(local_artifacts)), out_dir, timeout_sec=args.adb_pull_timeout, check=False))
        summary = parse_ownget_artifacts(select_pulled_artifact_dir(local_artifacts))
        result["ownget_summary"] = summary
        if helper_timeout:
            result["decision"] = f"v2490-helper-timeout-{summary['classification']}-before-rollback"
        else:
            result["decision"] = f"v2490-{summary['classification']}-before-rollback"
        result["partial_success"] = bool(summary.get("partial_success"))
        result["target_4916_success"] = bool(summary.get("full_success"))
        result["counts_toward_fails_twice"] = bool(summary.get("counts_toward_fails_twice", True))
        result["ok"] = bool(summary.get("operator_valuable"))
        steps.append(route.run_step("ownget-cleanup", cleanup_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
    except Exception as error:
        result.setdefault("decision", "v2490-acdb-ownprocess-get-failed-before-rollback")
        result["error"] = str(error)
    finally:
        if rollback_needed:
            try:
                steps.append(route.run_step("ownget-cleanup-finally", cleanup_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
                v2396.rollback_to_v2321_with_android_recovery(args, route_args(args), out_dir, steps, result)
                result["decision"] = f"{result['decision']}-rollback-pass"
            except Exception as rollback_error:
                result["rollback_fallback_error"] = str(rollback_error)
                result["rolled_back"] = False
        write_json(out_dir / "result.json", result)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--build-helper", action="store_true", help="Build the V2489 helper before planning/running")
    parser.add_argument("--build-ioctl-trace", action="store_true", help="Build the V2531 ioctl trace preload before planning/running")
    parser.add_argument("--disable-ioctl-trace", action="store_true", help="Run without the V2531 ioctl trace preload")
    parser.add_argument(
        "--fake-audio-cal-allocate",
        action="store_true",
        help="Set A90_ACDB_FAKE_ALLOCATE=1 so the preload returns success for AUDIO_ALLOCATE/DEALLOCATE/SET only",
    )
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial")
    parser.add_argument("--from-native", action="store_true")
    parser.add_argument("--android-timeout", type=float, default=240.0)
    parser.add_argument("--flash-timeout", type=float, default=420.0)
    parser.add_argument("--adb-command-timeout", type=float, default=90.0)
    parser.add_argument("--adb-pull-timeout", type=float, default=120.0)
    parser.add_argument("--helper-timeout", type=float, default=60.0)
    parser.add_argument("--android-root-recheck-attempts", type=int, default=v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS)
    parser.add_argument("--android-root-recheck-sleep-sec", type=float, default=v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC)
    parser.add_argument("--android-settle-adb-retry-attempts", type=int, default=DEFAULT_SETTLE_ADB_RETRY_ATTEMPTS)
    parser.add_argument("--android-settle-adb-retry-sleep-sec", type=float, default=DEFAULT_SETTLE_ADB_RETRY_SLEEP_SEC)
    parser.add_argument("--helper-path", type=Path)
    parser.add_argument("--helper-sha256")
    parser.add_argument("--helper-build-root", type=Path, default=v_helper.DEFAULT_BUILD_ROOT)
    parser.add_argument("--helper-manifest-path", type=Path, default=v_helper.DEFAULT_MANIFEST)
    parser.add_argument("--ioctl-trace-so", type=Path)
    parser.add_argument("--ioctl-trace-sha256")
    parser.add_argument("--ioctl-trace-build-root", type=Path, default=v_ioctltrace.DEFAULT_BUILD_ROOT)
    parser.add_argument("--ioctl-trace-manifest-path", type=Path, default=v_ioctltrace.DEFAULT_MANIFEST)
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--file", default="file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.build_helper and not args.run_live:
        build_helper(args)
    if args.build_ioctl_trace and not args.run_live:
        build_ioctl_trace(args)
    if args.run_live:
        result = run_live(args)
    else:
        result = dry_run_payload(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", False) or not args.run_live else 1


if __name__ == "__main__":
    raise SystemExit(main())
