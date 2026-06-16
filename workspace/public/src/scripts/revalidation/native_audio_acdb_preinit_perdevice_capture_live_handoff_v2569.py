#!/usr/bin/env python3
"""V2569 live handoff for the V2568 ACDB pre-init-tail per-device capture.

This wrapper reuses the V2490 checked Android boot/stage/pull/rollback engine
and selects the V2568 artifacts:

- helper starts acdb_loader_init_v3();
- combined preload stays quiet until INITIALIZE_V2 succeeds, calls the real
  common-topology function, patches the initialized flag, calls
  acdb_loader_send_audio_cal_v5(15, 0, 0x11135, 48000, 48000, 0, 1), and exits
  before returning to the known libacdbloader init-tail crash.

Raw ACDB buffers are private only.  No native replay, speaker write, or real
AUDIO_SET_CALIBRATION pass-through is allowed by this wrapper.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import build_android_acdb_preinit_perdevice_capture_v2568 as v2568
import native_audio_acdb_ownprocess_get_live_handoff_v2490 as v2490
import native_audio_acdb_per_device_manifest_live_handoff_v2560 as v2560

RUN_ID = "V2569"
BUILD_TAG = "v2569-audio-acdb-preinit-perdevice-capture-live"
ROOT = v2568.ROOT
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2569_AUDIO_ACDB_PREINIT_PERDEVICE_CAPTURE_LIVE_HANDOFF_2026-06-16.md"


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"v2569-acdb-preinit-perdevice-capture-{stamp}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return v2560.read_jsonl(path)


def build_v2568_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    build_state = v2568.build(
        args.v2568_build_root,
        clang=v2568.TOOLCHAIN_ROOT / "bin/clang",
        lld=v2568.TOOLCHAIN_ROOT / "bin/ld.lld",
        readelf=args.readelf,
        file_cmd=args.file,
    )
    payload = {
        "run_id": v2568.RUN_ID,
        "build_tag": v2568.BUILD_TAG,
        "host_only_build": True,
        "sources": v2568.source_state(),
        "vendor_libs": v2568.vendor_lib_state(args.readelf),
        "build": build_state,
        "ok": bool(
            build_state.get("ok")
            and v2568.source_state().get("required_ok")
            and v2568.source_state().get("prohibited_ok")
            and v2568.vendor_lib_state(args.readelf).get("required_for_v2568_ok")
        ),
    }
    args.v2568_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.v2568_manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def read_v2568_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "error": f"manifest missing: {rel(path)}"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {"ok": False, "error": f"manifest json error: {error}"}
    build = payload.get("build", {})
    artifacts = build.get("artifacts", {})
    helper = artifacts.get("helper", {})
    preload = artifacts.get("preload", {})
    sources = payload.get("sources", {})
    required = sources.get("required", {})
    checks = {
        "manifest_ok": bool(payload.get("ok")),
        "helper_ok": bool(helper.get("ok")),
        "preload_ok": bool(preload.get("ok")),
        "preinit_exports_common_topology": bool(required.get("preinit_exports_common_topology")),
        "preinit_calls_real_common_topology": bool(required.get("preinit_calls_real_common_topology")),
        "preinit_patches_init_flag": bool(required.get("preinit_patches_init_flag")),
        "preinit_calls_send_audio_cal_v5": bool(required.get("preinit_calls_send_audio_cal_v5")),
        "preinit_exits_before_init_tail": bool(required.get("preinit_exits_before_init_tail")),
        "ioctl_fake_allocate_set": bool(required.get("ioctl_fake_allocate_set")),
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
        state.update(
            {
                "size": stat.st_size,
                "mode": oct(stat.st_mode & 0o777),
                "sha256": digest,
                "sha256_ok": expected is None or digest == expected,
                "group_or_world_writable": bool(stat.st_mode & 0o022),
            }
        )
    state["ok"] = bool(state.get("exists") and state.get("sha256_ok", True) and not state.get("group_or_world_writable"))
    return state


def selected_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    if args.build_v2568_artifacts:
        build_v2568_artifacts(args)
    manifest = read_v2568_manifest(args.v2568_manifest_path)
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


def summarize_preinit_perdevice_capture(artifact_dir: Path) -> dict[str, Any]:
    base_summary = v2490.parse_ownget_artifacts(artifact_dir)
    helper_events_path = artifact_dir / "acdb-v2568-init-driver-events.jsonl"
    preinit_events_path = artifact_dir / "acdb-v2568-preinit-perdevice-events.jsonl"
    helper_events = read_jsonl(helper_events_path)
    preinit_events = read_jsonl(preinit_events_path)
    helper_stages = [
        event.get("stage") for event in helper_events
        if event.get("event") == "v2568_init_driver"
    ]
    preinit_stages = [
        event.get("stage") for event in preinit_events
        if event.get("event") == "v2568_preinit_perdevice"
    ]

    acdbtap_dir = artifact_dir / "acdbtap"
    if not (acdbtap_dir / "acdbtap-events.jsonl").exists() and (artifact_dir / "acdbtap-events.jsonl").exists():
        acdbtap_dir = artifact_dir
    rows = base_summary.get("acdbtap_rows", [])
    record_states = [v2560.row_raw_state(row, acdbtap_dir) for row in rows]
    successful = [
        item for item in record_states
        if item.get("ret") == 0 and item.get("valid_raw") and item.get("nonzero")
    ]
    topology = [item for item in successful if item.get("out_len") == 4916]
    size_queries = [item for item in record_states if item.get("out_len") == 4]
    init_or_topology_cmds = {"0x000131de", "0x00013262", "0x00013296", "0x00013297"}
    send_audio_cal_v5_reached = any(
        stage in {"before_send_audio_cal_v5", "send_audio_cal_v5_return"}
        for stage in preinit_stages
    )
    per_device = [
        item for item in successful
        if send_audio_cal_v5_reached
        and item.get("out_len") not in {4, 4916}
        and str(item.get("cmd")).lower() not in init_or_topology_cmds
    ]
    ioctl_events = base_summary.get("ioctl_trace_events", [])
    fake_set_events = [
        event for event in ioctl_events
        if event.get("name") == "AUDIO_SET_CALIBRATION" and event.get("intercept") == "fake-success"
    ]
    pass_through_set_events = [
        event for event in ioctl_events
        if event.get("name") == "AUDIO_SET_CALIBRATION" and event.get("intercept") != "fake-success"
    ]
    real_common_called = "before_real_common_topology" in preinit_stages and "real_common_topology_return" in preinit_stages
    patch_ok = "patch_initialized_flag_return" in preinit_stages and any(
        event.get("stage") == "patch_initialized_flag_return" and event.get("code") == 0
        for event in preinit_events
    )
    exited_before_tail = "exit_before_init_tail" in preinit_stages

    if pass_through_set_events:
        classification = "v2569-boundary-violation-real-audio-set-passthrough"
    elif per_device:
        classification = "v2569-preinit-perdevice-manifest-captured"
    elif topology and send_audio_cal_v5_reached:
        classification = "v2569-topology-and-send-audio-cal-v5-no-per-device-records"
    elif topology and not send_audio_cal_v5_reached:
        classification = "v2569-topology-captured-before-per-device"
    elif patch_ok and send_audio_cal_v5_reached:
        classification = "v2569-send-audio-cal-v5-no-nonzero-capture"
    elif real_common_called:
        classification = "v2569-real-common-called-no-valid-topology-capture"
    elif preinit_stages:
        classification = "v2569-preinit-hook-entered-no-real-common"
    else:
        classification = f"v2569-{base_summary.get('classification', 'no-acdbtap-capture')}"

    full_success = bool(per_device and topology and not pass_through_set_events)
    partial_success = bool((successful or preinit_stages) and not pass_through_set_events)
    return {
        "classification": classification,
        "full_success": full_success,
        "partial_success": partial_success,
        "topology_success_count": len(topology),
        "per_device_success_count": len(per_device),
        "successful_nonzero_count": len(successful),
        "size_query_count": len(size_queries),
        "fake_audio_set_count": len(fake_set_events),
        "real_audio_set_pass_through_count": len(pass_through_set_events),
        "helper_event_path": rel(helper_events_path),
        "preinit_event_path": rel(preinit_events_path),
        "helper_event_count": len(helper_events),
        "preinit_event_count": len(preinit_events),
        "helper_stages": helper_stages,
        "preinit_stages": preinit_stages,
        "real_common_topology_called": real_common_called,
        "patch_initialized_flag_ok": patch_ok,
        "send_audio_cal_v5_reached": send_audio_cal_v5_reached,
        "exited_before_init_tail": exited_before_tail,
        "ordered_records": record_states,
        "base_summary": base_summary,
    }


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    artifacts = selected_artifacts(args)
    base_args = to_v2490_args(args, artifacts) if artifacts.get("ok") else None
    base_payload = v2490.dry_run_payload(base_args) if base_args else {}
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2569-acdb-preinit-perdevice-capture-live-runner-dry-run",
        "host_only": True,
        "device_action": "none",
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "v2568_artifacts": artifacts,
        "v2490_engine": {
            "run_id": "V2490",
            "decision": base_payload.get("decision"),
            "live_ready": base_payload.get("live_ready", False),
            "command_safety": base_payload.get("command_safety"),
            "commands": base_payload.get("commands", {}),
        },
        "capture_contract": {
            "fake_audio_cal_allocate": True,
            "combined_preload": True,
            "success_requires": "topology ret==0 non-zero 4916 plus at least one ret==0 non-zero non-topology per-device ACDB buffer",
            "real_audio_set_passthrough_allowed": False,
            "raw_private_only": True,
        },
    }
    payload["live_ready"] = bool(artifacts.get("ok") and base_payload.get("live_ready"))
    payload["live_blockers"] = []
    if not artifacts.get("ok"):
        payload["live_blockers"].append("V2568 pre-init-tail helper/preload artifacts are not ready")
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
        raise RuntimeError(f"V2569 live inputs are not ready: {dry.get('live_blockers')}")
    artifacts = dry["v2568_artifacts"]
    base_args = to_v2490_args(args, artifacts)
    result = v2490.run_live(base_args)
    pulled_dir = select_pulled_dir_from_result(result)
    summary = summarize_preinit_perdevice_capture(pulled_dir) if pulled_dir else {
        "classification": "v2569-no-pulled-artifacts",
        "full_success": False,
        "partial_success": False,
    }
    wrapper = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{summary['classification']}-rollback-{ 'pass' if result.get('rolled_back') else 'unknown' }",
        "out_dir": result.get("out_dir"),
        "v2568_artifacts": artifacts,
        "v2490_engine_result": result,
        "preinit_perdevice_summary": summary,
        "ok": bool(result.get("rolled_back") and summary.get("full_success")),
    }
    out_dir_raw = result.get("out_dir")
    if out_dir_raw:
        write_json(ROOT / str(out_dir_raw) / "v2569-result.json", wrapper)
    return wrapper


def write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("preinit_perdevice_summary", {})
    per_device_records = [
        row for row in summary.get("ordered_records", [])
        if row.get("ret") == 0
        and row.get("valid_raw")
        and row.get("nonzero")
        and row.get("out_len") not in {4, 4916}
    ]
    topology_records = [
        row for row in summary.get("ordered_records", [])
        if row.get("ret") == 0
        and row.get("valid_raw")
        and row.get("nonzero")
        and row.get("out_len") == 4916
    ]
    lines = [
        "# NATIVE_INIT V2569 — ACDB pre-init-tail per-device capture live handoff",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Android own-process ACDB capture handoff using the V2490 checked Android boot/stage/pull/rollback engine and the V2568 pre-init-tail helper/preload artifacts.",
        "",
        "## Result",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- ok: `{payload.get('ok')}`",
        f"- out_dir: `{payload.get('out_dir')}`",
        f"- classification: `{summary.get('classification')}`",
        f"- real_common_topology_called: `{summary.get('real_common_topology_called')}`",
        f"- patch_initialized_flag_ok: `{summary.get('patch_initialized_flag_ok')}`",
        f"- send_audio_cal_v5_reached: `{summary.get('send_audio_cal_v5_reached')}`",
        f"- exited_before_init_tail: `{summary.get('exited_before_init_tail')}`",
        f"- topology_success_count: `{summary.get('topology_success_count')}`",
        f"- per_device_success_count: `{summary.get('per_device_success_count')}`",
        f"- successful_nonzero_count: `{summary.get('successful_nonzero_count')}`",
        f"- real_audio_set_pass_through_count: `{summary.get('real_audio_set_pass_through_count')}`",
        "",
        "## Captured Candidates",
        "",
        f"- topology_4916_records: `{len(topology_records)}`",
        f"- per_device_candidate_count: `{len(per_device_records)}`",
    ]
    for row in topology_records[:10]:
        lines.append(
            f"- topology seq=`{row.get('seq')}` cmd=`{row.get('cmd')}` out_len=`{row.get('out_len')}` sha256=`{row.get('raw_sha256')}`"
        )
    for row in per_device_records[:20]:
        lines.append(
            f"- per_device seq=`{row.get('seq')}` cmd=`{row.get('cmd')}` out_len=`{row.get('out_len')}` sha256=`{row.get('raw_sha256')}`"
        )
    lines.extend(
        [
            "",
            "Raw ACDB buffers remain private under the run directory and are not committed.",
            "",
            "## Artifacts",
            "",
            f"- helper_sha256: `{payload.get('v2568_artifacts', {}).get('helper', {}).get('sha256')}`",
            f"- preload_sha256: `{payload.get('v2568_artifacts', {}).get('preload', {}).get('sha256')}`",
            "",
            "## Boundary",
            "",
            "- `A90_ACDB_FAKE_ALLOCATE=1` is forced; any real `AUDIO_SET_CALIBRATION` pass-through is a boundary violation.",
            "- Success requires valid non-zero topology plus at least one non-topology per-device ACDB out-buffer.",
            "- The live route must roll back to V2321 and leave native `selftest fail=0` via the V2490 engine.",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--build-v2568-artifacts", action="store_true")
    parser.add_argument("--v2568-build-root", type=Path, default=v2568.DEFAULT_BUILD_ROOT)
    parser.add_argument("--v2568-manifest-path", type=Path, default=v2568.DEFAULT_MANIFEST)
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
