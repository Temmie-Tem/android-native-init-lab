#!/usr/bin/env python3
"""V2564 live handoff for ACDB per-device capture with topology short-circuit.

This wrapper reuses the V2490 checked Android boot/stage/pull/rollback engine
and selects the V2561 artifacts:

- helper initializes ACDB, arms the ACDB tap, and calls
  acdb_loader_send_audio_cal_v5(15, 0, 0x11135, 48000, 48000, 0, 1);
- combined preload fakes audio-cal allocate/deallocate/SET, captures ACDB
  out-buffers without exiting on topology, and short-circuits
  acdb_loader_send_common_custom_topology() so init can return before the helper
  reaches send_audio_cal_v5().

Raw payloads are private only.  No native replay, speaker write, or real
AUDIO_SET_CALIBRATION pass-through is allowed by this wrapper.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import build_android_acdb_toposkip_per_device_manifest_v2561 as v2561
import native_audio_acdb_per_device_manifest_live_handoff_v2560 as v2560
import native_audio_acdb_ownprocess_get_live_handoff_v2490 as v2490

RUN_ID = "V2564"
BUILD_TAG = "v2564-audio-acdb-toposkip-per-device-manifest-live"
ROOT = v2561.ROOT
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2564_AUDIO_ACDB_TOPOSKIP_PER_DEVICE_MANIFEST_LIVE_HANDOFF_2026-06-16.md"


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"v2564-acdb-toposkip-per-device-manifest-{stamp}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return v2560.read_jsonl(path)


def read_v2561_manifest(path: Path) -> dict[str, Any]:
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
    required = source_state.get("required", {})
    checks = {
        "manifest_ok": bool(payload.get("ok")),
        "helper_ok": bool(helper.get("ok")),
        "preload_ok": bool(preload.get("ok")),
        "helper_calls_send_audio_cal_v5": bool(required.get("helper_calls_send_audio_cal_v5")),
        "helper_does_not_call_common_topology": bool(required.get("helper_no_decl_common_topology")),
        "toposkip_exports_common_topology": bool(required.get("toposkip_exports_common_topology")),
        "toposkip_returns_success": bool(required.get("toposkip_returns_success")),
        "toposkip_logs_private_marker": bool(required.get("toposkip_logs_private_marker")),
        "tap_post_initialize_auto_arm": bool(required.get("tap_post_initialize_auto_arm")),
        "ioctl_fake_allocate_mode": bool(required.get("ioctl_fake_allocate_mode")),
    }
    return {
        "ok": all(checks.values()),
        "path": rel(path),
        "manifest": payload,
        "helper": helper,
        "preload": preload,
        "checks": checks,
        "capture_contract": payload.get("capture_contract", {}),
    }


def artifact_from_manifest(entry: dict[str, Any], explicit_path: Path | None, explicit_sha: str | None) -> dict[str, Any]:
    if explicit_path:
        path = explicit_path
        expected = explicit_sha
    else:
        raw_path = entry.get("path")
        path = ROOT / raw_path if raw_path else None
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


def build_v2561_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    build_args = argparse.Namespace(
        build=True,
        build_root=args.v2561_build_root,
        manifest_path=args.v2561_manifest_path,
        clang=v2561.TOOLCHAIN_ROOT / "bin/clang",
        lld=v2561.TOOLCHAIN_ROOT / "bin/ld.lld",
        readelf=args.readelf,
        file=args.file,
    )
    return v2561.manifest(build_args)


def selected_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    if args.build_v2561_artifacts:
        build_v2561_artifacts(args)
    manifest = read_v2561_manifest(args.v2561_manifest_path)
    helper = artifact_from_manifest(manifest.get("helper", {}), args.helper_path, args.helper_sha256)
    preload = artifact_from_manifest(manifest.get("preload", {}), args.preload_path, args.preload_sha256)
    return {
        "manifest": manifest,
        "helper": helper,
        "preload": preload,
        "ok": bool(manifest.get("ok") and helper.get("ok") and preload.get("ok")),
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


def select_pulled_dir_from_result(result: dict[str, Any]) -> Path | None:
    return v2560.select_pulled_dir_from_result(result)


def summarize_toposkip_per_device_manifest(artifact_dir: Path) -> dict[str, Any]:
    summary = v2560.summarize_per_device_manifest(artifact_dir)
    toposkip_events_path = artifact_dir / "acdb-toposkip-events.jsonl"
    toposkip_events = read_jsonl(toposkip_events_path)
    if not toposkip_events:
        nested = artifact_dir / "acdbtap" / "acdb-toposkip-events.jsonl"
        if nested.exists():
            toposkip_events_path = nested
            toposkip_events = read_jsonl(nested)
    toposkip_markers = [
        event for event in toposkip_events
        if event.get("event") == "topology_skip" and event.get("stage") == "common_topology_short_circuit"
    ]
    original_classification = str(summary.get("classification", "unknown"))
    classification = original_classification.replace("v2560-", "v2564-", 1)
    if not toposkip_markers:
        classification = "v2564-topology-skip-marker-missing"
    elif summary.get("real_audio_set_pass_through_count"):
        classification = "v2564-boundary-violation-real-audio-set-passthrough"
    elif summary.get("per_device_success"):
        classification = "v2564-toposkip-per-device-manifest-captured"
    elif summary.get("send_audio_cal_v5_reached"):
        classification = "v2564-toposkip-send-audio-cal-v5-no-per-device-records"
    summary.update({
        "classification": classification,
        "original_v2560_classification": original_classification,
        "topology_skip_event_path": rel(toposkip_events_path),
        "topology_skip_marker_count": len(toposkip_markers),
        "topology_skip_markers": toposkip_markers,
        "full_success": bool(summary.get("per_device_success") and toposkip_markers and not summary.get("real_audio_set_pass_through_count")),
    })
    return summary


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    artifacts = selected_artifacts(args)
    base_args = to_v2490_args(args, artifacts) if artifacts.get("ok") else None
    base_payload = v2490.dry_run_payload(base_args) if base_args else {}
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2564-acdb-toposkip-per-device-manifest-live-runner-dry-run",
        "host_only": True,
        "device_action": "none",
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "v2561_artifacts": artifacts,
        "v2490_engine": {
            "run_id": "V2490",
            "decision": base_payload.get("decision"),
            "live_ready": base_payload.get("live_ready", False),
            "command_safety": base_payload.get("command_safety"),
            "commands": base_payload.get("commands", {}),
        },
        "capture_contract": {
            "topology_skip_required": True,
            "fake_audio_cal_allocate": True,
            "combined_preload": True,
            "success_requires": "topology-skip marker plus send_audio_cal_v5 helper marker plus at least one ret==0 non-zero non-topology ACDB buffer",
            "real_audio_set_passthrough_allowed": False,
            "raw_private_only": True,
        },
    }
    payload["live_ready"] = bool(artifacts.get("ok") and base_payload.get("live_ready"))
    payload["live_blockers"] = []
    if not artifacts.get("ok"):
        payload["live_blockers"].append("V2561 toposkip per-device helper/preload artifacts are not ready")
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
        raise RuntimeError(f"V2564 live inputs are not ready: {dry.get('live_blockers')}")
    artifacts = dry["v2561_artifacts"]
    base_args = to_v2490_args(args, artifacts)
    result = v2490.run_live(base_args)
    pulled_dir = select_pulled_dir_from_result(result)
    summary = summarize_toposkip_per_device_manifest(pulled_dir) if pulled_dir else {
        "classification": "v2564-no-pulled-artifacts",
        "full_success": False,
        "per_device_success": False,
        "partial_success": False,
        "topology_skip_marker_count": 0,
    }
    wrapper = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{summary['classification']}-rollback-{ 'pass' if result.get('rolled_back') else 'unknown' }",
        "out_dir": result.get("out_dir"),
        "v2561_artifacts": artifacts,
        "v2490_engine_result": result,
        "per_device_manifest_summary": summary,
        "ok": bool(result.get("rolled_back") and summary.get("full_success")),
    }
    out_dir_raw = result.get("out_dir")
    if out_dir_raw:
        write_json(ROOT / str(out_dir_raw) / "v2564-result.json", wrapper)
    return wrapper


def write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("per_device_manifest_summary", {})
    init_or_topology_cmds = {"0x000131de", "0x00013262", "0x00013296", "0x00013297"}
    per_device_records = [
        row for row in summary.get("ordered_records", [])
        if row.get("ret") == 0
        and row.get("valid_raw")
        and row.get("nonzero")
        and row.get("out_len") not in {4, 4916}
        and str(row.get("cmd")).lower() not in init_or_topology_cmds
    ]
    lines = [
        "# NATIVE_INIT V2564 — ACDB topology-skip per-device manifest live handoff",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Android own-process ACDB capture handoff using the V2490 checked Android boot/stage/pull/rollback engine and the V2561 topology-skip per-device helper/preload artifacts.",
        "",
        "## Result",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- ok: `{payload.get('ok')}`",
        f"- out_dir: `{payload.get('out_dir')}`",
        f"- classification: `{summary.get('classification')}`",
        f"- topology_skip_marker_count: `{summary.get('topology_skip_marker_count')}`",
        f"- send_audio_cal_v5_reached: `{summary.get('send_audio_cal_v5_reached')}`",
        f"- topology_success_count: `{summary.get('topology_success_count')}`",
        f"- per_device_success_count: `{summary.get('per_device_success_count')}`",
        f"- successful_nonzero_count: `{summary.get('successful_nonzero_count')}`",
        f"- real_audio_set_pass_through_count: `{summary.get('real_audio_set_pass_through_count')}`",
        "",
        "## Captured Per-Device Candidates",
        "",
        f"- candidate_count: `{len(per_device_records)}`",
    ]
    for row in per_device_records[:20]:
        lines.append(
            f"- seq=`{row.get('seq')}` cmd=`{row.get('cmd')}` out_len=`{row.get('out_len')}` sha256=`{row.get('raw_sha256')}`"
        )
    lines.extend([
        "",
        "Raw ACDB buffers remain private under the run directory and are not committed.",
        "",
        "## Artifacts",
        "",
        f"- helper_sha256: `{payload.get('v2561_artifacts', {}).get('helper', {}).get('sha256')}`",
        f"- preload_sha256: `{payload.get('v2561_artifacts', {}).get('preload', {}).get('sha256')}`",
        "",
        "## Boundary",
        "",
        "- The preload short-circuits `acdb_loader_send_common_custom_topology()` and requires a private topology-skip marker as evidence.",
        "- `A90_ACDB_FAKE_ALLOCATE=1` is forced; any real `AUDIO_SET_CALIBRATION` pass-through is a boundary violation.",
        "- Success requires a topology-skip marker, helper reach into `send_audio_cal_v5`, and at least one ret=0 non-zero non-topology ACDB buffer.",
        "",
    ])
    if summary.get("classification") == "v2564-topology-skip-marker-missing":
        lines.extend([
            "## Interpretation",
            "",
            "- The run safely rolled back but did not prove the topology skip path: no `acdb-toposkip-events.jsonl` marker was pulled, `send_audio_cal_v5` was not reached, and the known topology payload was recaptured instead.",
            "- Host `readelf` on the V2561 preload shows `acdb_loader_send_common_custom_topology` is `LOCAL HIDDEN`, not a dynamic `GLOBAL` export, so the intended symbol interposition could not override `libacdbloader.so`.",
            "- The next fix is host-only: rebuild the topology-skip interposer with explicit default symbol visibility and require the dynamic symbol table to export `acdb_loader_send_common_custom_topology` before rerunning live.",
            "",
        ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--build-v2561-artifacts", action="store_true")
    parser.add_argument("--v2561-build-root", type=Path, default=v2561.DEFAULT_BUILD_ROOT)
    parser.add_argument("--v2561-manifest-path", type=Path, default=v2561.DEFAULT_MANIFEST)
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
    parser.add_argument("--helper-timeout", type=float, default=120.0)
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
