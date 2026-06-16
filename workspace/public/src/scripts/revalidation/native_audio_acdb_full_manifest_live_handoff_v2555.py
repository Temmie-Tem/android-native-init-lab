#!/usr/bin/env python3
"""V2555 Android handoff for the V2553 manual-arm ACDB full-manifest capture.

This wrapper deliberately reuses the proven V2490 Android boot/stage/pull/
rollback engine.  The new behavior is limited to selecting the V2553 helper and
manual-arm combined preload, forcing the fake audio-cal ioctl policy, and adding
a full-manifest classifier over the pulled acdbtap/ioctl event set.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import build_android_acdb_full_manifest_v2553 as v2553
import native_audio_acdb_ownprocess_get_live_handoff_v2490 as v2490

RUN_ID = "V2555"
BUILD_TAG = "v2555-audio-acdb-full-manifest-live"
ROOT = v2553.ROOT
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2555_AUDIO_ACDB_FULL_MANIFEST_LIVE_HANDOFF_2026-06-16.md"


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"v2555-acdb-full-manifest-{stamp}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def int_or_none(value: Any) -> int | None:
    try:
        if isinstance(value, str):
            return int(value, 0)
        return int(value)
    except (TypeError, ValueError):
        return None


def int32_or_none(value: Any) -> int | None:
    parsed = int_or_none(value)
    if parsed is None:
        return None
    parsed &= 0xFFFFFFFF
    if parsed & 0x80000000:
        return parsed - 0x100000000
    return parsed


def zero_sha(length: int) -> str:
    return hashlib.sha256(b"\0" * max(0, length)).hexdigest()


def read_v2553_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "error": f"manifest missing: {rel(path)}"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {"ok": False, "error": f"manifest json error: {error}"}
    build = payload.get("build", {})
    helper = build.get("helper", {})
    preload = build.get("preload", {})
    source_state = payload.get("source_state", {})
    return {
        "ok": bool(payload.get("ok") and helper.get("ok") and preload.get("ok")),
        "path": rel(path),
        "manifest": payload,
        "helper": helper,
        "preload": preload,
        "manual_arm_only": bool(source_state.get("required", {}).get("tap_manual_arm_only")),
        "preload_policy": payload.get("capture_contract", {}).get("preload_policy"),
    }


def artifact_from_manifest(entry: dict[str, Any], explicit_path: Path | None, explicit_sha: str | None) -> dict[str, Any]:
    if explicit_path:
        path = explicit_path
        expected = explicit_sha
    else:
        raw_path = entry.get("path")
        path = ROOT / raw_path if raw_path else Path()
        expected = entry.get("sha256")
    state: dict[str, Any] = {
        "path": rel(path) if path else None,
        "exists": bool(path and path.exists()),
        "expected_sha256": expected,
    }
    if path and path.exists():
        stat = path.stat()
        digest = sha256_file(path)
        state.update({
            "size": stat.st_size,
            "mode": oct(stat.st_mode & 0o777),
            "sha256": digest,
            "sha256_ok": expected is None or digest == expected,
            "group_or_world_writable": bool(stat.st_mode & 0o022),
        })
    state["ok"] = bool(state.get("exists") and state.get("sha256_ok", True) and not state.get("group_or_world_writable"))
    return state


def build_v2553_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    build_args = argparse.Namespace(
        build=True,
        build_root=args.v2553_build_root,
        manifest_path=args.v2553_manifest_path,
        clang=v2553.TOOLCHAIN_ROOT / "bin/clang",
        lld=v2553.TOOLCHAIN_ROOT / "bin/ld.lld",
        readelf=args.readelf,
        file=args.file,
    )
    return v2553.manifest(build_args)


def selected_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    if args.build_v2553_artifacts:
        build_v2553_artifacts(args)
    manifest = read_v2553_manifest(args.v2553_manifest_path)
    helper = artifact_from_manifest(manifest.get("helper", {}), args.helper_path, args.helper_sha256)
    preload = artifact_from_manifest(manifest.get("preload", {}), args.preload_path, args.preload_sha256)
    return {
        "manifest": manifest,
        "helper": helper,
        "preload": preload,
        "ok": bool(manifest.get("ok") and manifest.get("manual_arm_only") and helper.get("ok") and preload.get("ok")),
    }


def to_v2490_args(args: argparse.Namespace, artifacts: dict[str, Any]) -> argparse.Namespace:
    base = v2490.parse_args([])
    base.dry_run = args.dry_run
    base.run_live = args.run_live
    base.build_helper = False
    base.build_combined_preload = False
    base.build_acdbtap = False
    base.build_ioctl_trace = False
    base.use_combined_preload = True
    base.enable_acdbtap_preload = False
    base.disable_ioctl_trace = False
    base.fake_audio_cal_allocate = True
    base.out_dir = args.out_dir
    base.adb = args.adb
    base.serial = args.serial
    base.from_native = args.from_native
    base.android_timeout = args.android_timeout
    base.flash_timeout = args.flash_timeout
    base.adb_command_timeout = args.adb_command_timeout
    base.adb_pull_timeout = args.adb_pull_timeout
    base.helper_timeout = args.helper_timeout
    base.android_root_recheck_attempts = args.android_root_recheck_attempts
    base.android_root_recheck_sleep_sec = args.android_root_recheck_sleep_sec
    base.android_settle_adb_retry_attempts = args.android_settle_adb_retry_attempts
    base.android_settle_adb_retry_sleep_sec = args.android_settle_adb_retry_sleep_sec
    base.helper_path = ROOT / artifacts["helper"]["path"]
    base.helper_sha256 = artifacts["helper"]["sha256"]
    base.combined_preload_so = ROOT / artifacts["preload"]["path"]
    base.combined_preload_sha256 = artifacts["preload"]["sha256"]
    base.readelf = args.readelf
    base.file = args.file
    return base


def row_raw_state(row: dict[str, Any], acdbtap_dir: Path) -> dict[str, Any]:
    out_len = int_or_none(row.get("out_len"))
    ret = int32_or_none(row.get("ret"))
    raw_path = row.get("raw_path")
    state: dict[str, Any] = {
        "seq": row.get("seq"),
        "cmd": row.get("cmd"),
        "in_len": row.get("in_len"),
        "out_len": out_len,
        "ret": ret,
        "sha256": row.get("sha256"),
        "all_zero_flag": row.get("all_zero"),
        "raw_path": raw_path,
        "raw_exists": False,
        "valid_raw": False,
        "nonzero": False,
    }
    if not raw_path:
        return state
    local = acdbtap_dir / Path(str(raw_path)).name
    state["local_raw_path"] = rel(local)
    if not local.exists():
        return state
    data = local.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    state.update({
        "raw_exists": True,
        "raw_size": len(data),
        "raw_sha256": digest,
        "raw_sha256_ok": not row.get("sha256") or str(row.get("sha256")).lower() == digest,
        "valid_raw": out_len is None or len(data) == out_len,
        "nonzero": out_len is not None and digest != zero_sha(out_len),
    })
    return state


def summarize_full_manifest(artifact_dir: Path) -> dict[str, Any]:
    base_summary = v2490.parse_ownget_artifacts(artifact_dir)
    acdbtap_dir = artifact_dir / "acdbtap"
    if not (acdbtap_dir / "acdbtap-events.jsonl").exists() and (artifact_dir / "acdbtap-events.jsonl").exists():
        acdbtap_dir = artifact_dir
    rows = base_summary.get("acdbtap_rows", [])
    record_states = [row_raw_state(row, acdbtap_dir) for row in rows]
    successful = [
        item for item in record_states
        if item.get("ret") == 0 and item.get("valid_raw") and item.get("nonzero")
    ]
    topology = [item for item in successful if item.get("out_len") == 4916]
    size_queries = [item for item in record_states if item.get("out_len") == 4]
    per_device = [item for item in successful if item.get("out_len") not in {4, 4916}]
    ioctl_events = base_summary.get("ioctl_trace_events", [])
    fake_set_events = [
        event for event in ioctl_events
        if event.get("name") == "AUDIO_SET_CALIBRATION" and event.get("intercept") == "fake-success"
    ]
    pass_through_set_events = [
        event for event in ioctl_events
        if event.get("name") == "AUDIO_SET_CALIBRATION" and event.get("intercept") != "fake-success"
    ]
    fake_set_cal_types = []
    for event in fake_set_events:
        snapshot = event.get("arg_snapshot")
        if isinstance(snapshot, dict):
            fake_set_cal_types.append(snapshot.get("cal_type"))
    full_success = bool(topology and per_device and not pass_through_set_events)
    topology_only = bool(topology and not per_device and not pass_through_set_events)
    partial_success = bool((topology or successful) and not full_success and not pass_through_set_events)
    if pass_through_set_events:
        classification = "v2555-boundary-violation-real-audio-set-passthrough"
    elif full_success:
        classification = "v2555-full-manifest-captured"
    elif topology_only:
        classification = "v2555-topology-only-captured"
    elif partial_success:
        classification = "v2555-partial-nonzero-acdbtap-capture"
    else:
        classification = f"v2555-{base_summary.get('classification', 'no-acdbtap-capture')}"
    return {
        "classification": classification,
        "full_success": full_success,
        "partial_success": partial_success,
        "topology_success_count": len(topology),
        "per_device_success_count": len(per_device),
        "successful_nonzero_count": len(successful),
        "size_query_count": len(size_queries),
        "fake_audio_set_count": len(fake_set_events),
        "fake_audio_set_cal_types_observed": fake_set_cal_types,
        "real_audio_set_pass_through_count": len(pass_through_set_events),
        "ordered_records": record_states,
        "base_summary": base_summary,
    }


def select_pulled_dir_from_result(result: dict[str, Any]) -> Path | None:
    out_dir_raw = result.get("out_dir")
    if not out_dir_raw:
        return None
    out_dir = ROOT / str(out_dir_raw)
    pulled = out_dir / "ownget-device-artifacts"
    if not pulled.exists():
        return None
    return v2490.select_pulled_artifact_dir(pulled)


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    artifacts = selected_artifacts(args)
    base_args = to_v2490_args(args, artifacts) if artifacts.get("ok") else None
    base_payload = v2490.dry_run_payload(base_args) if base_args else {}
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2555-acdb-full-manifest-live-runner-dry-run",
        "host_only": True,
        "device_action": "none",
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "v2553_artifacts": artifacts,
        "v2490_engine": {
            "run_id": "V2490",
            "decision": base_payload.get("decision"),
            "live_ready": base_payload.get("live_ready", False),
            "command_safety": base_payload.get("command_safety"),
            "commands": base_payload.get("commands", {}),
        },
        "capture_contract": {
            "manual_arm_after_init_v3": True,
            "fake_audio_cal_allocate": True,
            "combined_preload": True,
            "success_requires": "ret==0 and non-all-zero raw buffer; requested out_len alone is not success",
            "full_manifest_acceptance": "topology 4916 plus at least one ordered non-zero per-device acdb_ioctl record",
            "raw_private_only": True,
        },
    }
    payload["live_ready"] = bool(artifacts.get("ok") and base_payload.get("live_ready"))
    payload["live_blockers"] = []
    if not artifacts.get("ok"):
        payload["live_blockers"].append("V2553 manual-arm helper/preload artifacts are not ready")
    payload["live_blockers"].extend(base_payload.get("live_blockers", []))
    payload["command_safety"] = base_payload.get("command_safety", {"ok": False, "findings": ["base payload missing"]})
    payload["ok"] = bool(payload["live_ready"] and payload["command_safety"].get("ok"))
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    if args.out_dir is None:
        args.out_dir = default_live_out_dir()
    dry = dry_run_payload(args)
    if not dry.get("ok"):
        raise RuntimeError(f"V2555 live inputs are not ready: {dry.get('live_blockers')}")
    artifacts = dry["v2553_artifacts"]
    base_args = to_v2490_args(args, artifacts)
    result = v2490.run_live(base_args)
    pulled_dir = select_pulled_dir_from_result(result)
    full_manifest_summary = summarize_full_manifest(pulled_dir) if pulled_dir else {
        "classification": "v2555-no-pulled-artifacts",
        "full_success": False,
        "partial_success": False,
    }
    wrapper = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{full_manifest_summary['classification']}-rollback-{ 'pass' if result.get('rolled_back') else 'unknown' }",
        "out_dir": result.get("out_dir"),
        "v2553_artifacts": artifacts,
        "v2490_engine_result": result,
        "full_manifest_summary": full_manifest_summary,
        "ok": bool(result.get("rolled_back") and (full_manifest_summary.get("full_success") or full_manifest_summary.get("partial_success"))),
    }
    out_dir_raw = result.get("out_dir")
    if out_dir_raw:
        write_json(ROOT / str(out_dir_raw) / "v2555-result.json", wrapper)
    return wrapper


def write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("full_manifest_summary", {})
    lines = [
        "# NATIVE_INIT V2555 — ACDB full-manifest live handoff",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Android own-process ACDB capture handoff using the V2490 checked Android boot/stage/pull/rollback engine and the V2553 manual-arm helper/preload artifacts.",
        "",
        "## Result",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- ok: `{payload.get('ok')}`",
        f"- out_dir: `{payload.get('out_dir')}`",
        f"- classification: `{summary.get('classification')}`",
        f"- topology_success_count: `{summary.get('topology_success_count')}`",
        f"- per_device_success_count: `{summary.get('per_device_success_count')}`",
        f"- successful_nonzero_count: `{summary.get('successful_nonzero_count')}`",
        f"- real_audio_set_pass_through_count: `{summary.get('real_audio_set_pass_through_count')}`",
        "",
        "Raw ACDB buffers remain private under the run directory and are not committed.",
        "",
        "## Artifacts",
        "",
        f"- helper_sha256: `{payload.get('v2553_artifacts', {}).get('helper', {}).get('sha256')}`",
        f"- preload_sha256: `{payload.get('v2553_artifacts', {}).get('preload', {}).get('sha256')}`",
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--build-v2553-artifacts", action="store_true")
    parser.add_argument("--v2553-build-root", type=Path, default=v2553.DEFAULT_BUILD_ROOT)
    parser.add_argument("--v2553-manifest-path", type=Path, default=v2553.DEFAULT_MANIFEST)
    parser.add_argument("--helper-path", type=Path)
    parser.add_argument("--helper-sha256")
    parser.add_argument("--preload-path", type=Path)
    parser.add_argument("--preload-sha256")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial")
    parser.add_argument("--from-native", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--android-timeout", type=float, default=240.0)
    parser.add_argument("--flash-timeout", type=float, default=420.0)
    parser.add_argument("--adb-command-timeout", type=float, default=90.0)
    parser.add_argument("--adb-pull-timeout", type=float, default=120.0)
    parser.add_argument("--helper-timeout", type=float, default=90.0)
    parser.add_argument("--android-root-recheck-attempts", type=int, default=v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS)
    parser.add_argument("--android-root-recheck-sleep-sec", type=float, default=v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC)
    parser.add_argument("--android-settle-adb-retry-attempts", type=int, default=v2490.DEFAULT_SETTLE_ADB_RETRY_ATTEMPTS)
    parser.add_argument("--android-settle-adb-retry-sleep-sec", type=float, default=v2490.DEFAULT_SETTLE_ADB_RETRY_SLEEP_SEC)
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--file", default="file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.run_live:
        payload = run_live(args)
    else:
        payload = dry_run_payload(args)
    if args.write_report and args.run_live:
        write_report(args.report_path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
