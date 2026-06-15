#!/usr/bin/env python3
"""V2490 live runner for the own-process ACDB pure-read GET helper.

This path intentionally avoids the V2477-V2488 in-HAL LD_PRELOAD lines.  It
boots stock Android through the checked helper, runs the V2489 ARM32 helper once
from /data/local/tmp under su, pulls private artifacts, cleans up, and rolls
back to V2321.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_android_acdb_ownprocess_get_v2489 as v2489
import native_audio_acdb_android_measurement_planner_v2396 as v2396
import native_audio_android_route_delta_handoff_v2365 as route

RUN_ID = "V2490"
BUILD_TAG = "v2490-audio-acdb-ownprocess-get-live"
ROOT = v2489.ROOT
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
REMOTE_DIR = "/data/local/tmp/a90-acdb-ownget"
REMOTE_HELPER = f"{REMOTE_DIR}/a90_acdb_ownprocess_get_v2489"
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


def rel(path: Path | str) -> str:
    return v2489.rel(Path(path) if not isinstance(path, Path) else path)


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
    return adb_base(args) + ["shell", "su", "-c", script]


def adb_push(args: argparse.Namespace, source: str, destination: str) -> list[str]:
    return adb_base(args) + ["push", source, destination]


def sha256_file(path: Path) -> str:
    return v2489.sha256_file(path)


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
        clang=v2489.TOOLCHAIN_ROOT / "bin/clang",
        lld=v2489.TOOLCHAIN_ROOT / "bin/ld.lld",
        readelf=args.readelf,
        file=args.file,
    )
    return v2489.manifest(build_args)


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
    default_path = args.helper_build_root / "bin" / v2489.ARTIFACT_NAME
    return helper_artifact_state(default_path)


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
chmod 600 {shlex.quote(REMOTE_DIR)}/*.so 2>/dev/null || true
sha256sum {shlex.quote(REMOTE_HELPER)} 2>/dev/null || toybox sha256sum {shlex.quote(REMOTE_HELPER)}
ls -l {shlex.quote(REMOTE_DIR)}/*.so 2>/dev/null || true
file {shlex.quote(REMOTE_HELPER)} 2>/dev/null || true
""".strip()
    return adb_su(args, script)


def run_helper_command(args: argparse.Namespace) -> list[str]:
    ld_library_path = ":".join([REMOTE_DIR, "/vendor/lib", "/system/lib", "/system_ext/lib", "/product/lib"])
    script = f"""
set +e
cd {shlex.quote(REMOTE_DIR)} || exit 61
rm -f ownget.stdout.txt ownget.stderr.txt ownget.rc
LD_LIBRARY_PATH={shlex.quote(ld_library_path)} {shlex.quote(REMOTE_HELPER)} > ownget.stdout.txt 2> ownget.stderr.txt
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
exit 0
""".strip()
    return adb_su(args, script)


def pull_artifacts_command(args: argparse.Namespace, destination: str) -> list[str]:
    return adb_base(args) + ["pull", REMOTE_DIR, destination]


def cleanup_command(args: argparse.Namespace) -> list[str]:
    return adb_su(args, f"rm -rf {shlex.quote(REMOTE_DIR)}")


def command_safety(payload: dict[str, Any]) -> dict[str, Any]:
    flat = json.dumps(payload.get("commands", payload), sort_keys=True)
    forbidden = {
        "magisk_install": "magisk --install-module",
        "hal_restart": "android.hardware.audio.service",
        "audio_track": "AudioTrack",
        "tinyplay": "tinyplay",
        "tinymix": "tinymix",
        "native_cal_set_constant": "0xc00461cb",
        "native_msm_audio_cal": "/dev/msm_audio_cal",
        "broad_module_delete": "rm -rf /data/adb/modules",
        "fastboot": "fastboot",
    }
    findings = [
        {"name": name, "needle": needle}
        for name, needle in forbidden.items()
        if needle in flat
    ]
    return {"ok": not findings, "findings": findings, "forbidden": sorted(forbidden)}


def parse_ownget_artifacts(path: Path) -> dict[str, Any]:
    events = path / "acdb-ownget-events.jsonl"
    acdb_log = path / "logcat-acdb-loader.txt"
    filtered_log = path / "logcat-avc-acdb-filter.txt"
    dmesg_log = path / "dmesg-avc-acdb-filter.txt"
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    namespace_events: list[dict[str, Any]] = []
    symbol_events: list[dict[str, Any]] = []
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
    acdb_log_text = acdb_log.read_text(encoding="utf-8", errors="replace") if acdb_log.exists() else ""
    filtered_log_text = filtered_log.read_text(encoding="utf-8", errors="replace") if filtered_log.exists() else ""
    dmesg_log_text = dmesg_log.read_text(encoding="utf-8", errors="replace") if dmesg_log.exists() else ""
    diagnostic_text = "\n".join([acdb_log_text, filtered_log_text, dmesg_log_text]).lower()
    target = [row for row in rows if row.get("is_target_4916") is True or row.get("out_len") == 4916]
    raw_files = sorted(path.glob("acdb-ownget-*.bin"))
    missing_raw = []
    for row in rows:
        raw_path = row.get("raw_path")
        if not raw_path:
            missing_raw.append(row.get("seq"))
            continue
        local = path / Path(str(raw_path)).name
        if not local.exists():
            missing_raw.append(row.get("seq"))
    if target and not missing_raw:
        classification = "acdb-get-success-4916"
    elif rows and not missing_raw:
        classification = "acdb-get-full-outbuf-set-no-4916"
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
            elif "avc:" in diagnostic_text or "denied" in diagnostic_text:
                classification = "init-v3-block-avc-denial"
            else:
                classification = "init-v3-block"
        else:
            classification = f"ownprocess-error-{stage}"
    elif malformed:
        classification = "ownprocess-events-malformed"
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
        "diagnostics": {
            "acdb_loader_log_path": rel(acdb_log) if acdb_log.exists() else None,
            "filtered_log_path": rel(filtered_log) if filtered_log.exists() else None,
            "dmesg_filter_path": rel(dmesg_log) if dmesg_log.exists() else None,
            "acdb_loader_line_count": len(acdb_log_text.splitlines()),
            "filtered_log_line_count": len(filtered_log_text.splitlines()),
            "dmesg_filter_line_count": len(dmesg_log_text.splitlines()),
            "has_acdb_files_load_error": "could not load .acdb files" in diagnostic_text,
            "has_acph_init_error": "error initializing acph returned" in diagnostic_text,
            "has_avc_or_denial": "avc:" in diagnostic_text or "denied" in diagnostic_text,
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
        "operator_valuable": bool(full_success or partial_success or rows or errors),
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
    deps = acdb_dependency_states()
    sealed_boot = "<private-run-dir>/android_boot_0600.img"
    helper_remote = REMOTE_HELPER
    commands = {
        "flash_android": route.flash_android_command(route_args(args), sealed_boot),
        "post_handoff_settle": ["adb wait-for-device + boot-complete + su id with bounded retries"],
        "setup": setup_command(args),
        "push_helper": adb_push(args, helper.get("path") or "<helper>", helper_remote),
        "push_acdb_dependencies": [
            adb_push(args, item.get("path") or "<missing>", item.get("remote_path") or "<remote>")
            for item in deps["libs"]
        ],
        "chmod_helper": chmod_helper_command(args),
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
        "acdb_dependencies": deps,
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "commands": commands,
        "partial_success_policy": "captured-ownprocess-outbuf-set-no-4916 is preserved as operator-valuable partial evidence; ACDB tap no-4916 policy remains non-dead-run",
        "hard_boundary": [
            "own-process helper only; no in-HAL LD_PRELOAD/injection",
            "no Magisk module install",
            "no HAL restart",
            "no AudioTrack/playback",
            "no native speaker write",
            "no /dev/msm_audio_cal SET path",
            "boot partition only through native_init_flash.py",
            "rollback to V2321 after capture",
        ],
        "live_ready": bool(android_boot.get("ok") and rollback.get("ok") and helper.get("ok") and deps.get("ok")),
        "live_blockers": [],
    }
    if not android_boot.get("ok"):
        payload["live_blockers"].append("Android boot candidate missing or invalid")
    if not rollback.get("ok"):
        payload["live_blockers"].append("V2321 rollback image missing or invalid")
    if not helper.get("ok"):
        payload["live_blockers"].append("V2489 helper artifact missing or invalid; run V2489 builder first")
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
        v2396.run_android_post_handoff_settle(args, out_dir, steps)
        steps.append(route.run_step("ownget-setup", setup_command(args), out_dir, timeout_sec=args.adb_command_timeout))
        helper_path = ROOT / payload["helper"]["path"]
        steps.append(route.run_step("ownget-push-helper", adb_push(args, rel(helper_path), REMOTE_HELPER), out_dir, timeout_sec=args.adb_command_timeout))
        for dep in payload["acdb_dependencies"]["libs"]:
            dep_path = ROOT / dep["path"]
            steps.append(route.run_step(
                f"ownget-push-{dep['name']}",
                adb_push(args, rel(dep_path), dep["remote_path"]),
                out_dir,
                timeout_sec=args.adb_command_timeout,
            ))
        steps.append(route.run_step("ownget-chmod-helper", chmod_helper_command(args), out_dir, timeout_sec=args.adb_command_timeout))
        steps.append(route.run_step("ownget-logcat-clear", clear_logcat_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step("ownget-run-helper", run_helper_command(args), out_dir, timeout_sec=args.helper_timeout, check=False))
        steps.append(route.run_step("ownget-logcat-capture", capture_logcat_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step("ownget-collect-prepare", collect_prepare_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        local_artifacts = out_dir / "ownget-device-artifacts"
        steps.append(route.run_step("ownget-pull-artifacts", pull_artifacts_command(args, str(local_artifacts)), out_dir, timeout_sec=args.adb_pull_timeout, check=False))
        summary = parse_ownget_artifacts(select_pulled_artifact_dir(local_artifacts))
        result["ownget_summary"] = summary
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
    parser.add_argument("--helper-path", type=Path)
    parser.add_argument("--helper-sha256")
    parser.add_argument("--helper-build-root", type=Path, default=v2489.DEFAULT_BUILD_ROOT)
    parser.add_argument("--helper-manifest-path", type=Path, default=v2489.DEFAULT_MANIFEST)
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--file", default="file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.build_helper and not args.run_live:
        build_helper(args)
    if args.run_live:
        result = run_live(args)
    else:
        result = dry_run_payload(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", False) or not args.run_live else 1


if __name__ == "__main__":
    raise SystemExit(main())
