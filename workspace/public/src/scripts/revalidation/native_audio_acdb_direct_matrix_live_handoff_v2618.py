#!/usr/bin/env python3
"""V2618 Android handoff wrapper for the V2617 ACDB direct matrix.

Host-only by default. Live mode reuses the V2490 checked Android
boot/stage/pull/rollback engine, but selects the V2617 helper/preload artifacts
and classifies the direct matrix helper events plus any direct/indirect
acdbtap records. The live action remains measurement-only: no native replay SET,
no speaker write, and raw buffers stay under workspace/private.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import build_android_acdb_direct_matrix_v2617 as v2617
import native_audio_acdb_ownprocess_get_live_handoff_v2490 as v2490
import native_audio_acdb_perdevice_indirect_capture_live_handoff_v2573 as v2573

ROOT = v2617.ROOT
RUN_ID = "V2618"
BUILD_TAG = "v2618-audio-acdb-direct-matrix-live-runner"
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2618_AUDIO_ACDB_DIRECT_MATRIX_LIVE_HANDOFF_2026-06-16.md"


def rel(path: Path | str) -> str:
    return v2573.rel(path)


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"v2618-acdb-direct-matrix-{stamp}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return v2573.read_jsonl(path)


def int_or_none(value: Any) -> int | None:
    return v2573.int_or_none(value)


def int32_or_none(value: Any) -> int | None:
    return v2573.int32_or_none(value)


def build_v2617_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    build_args = argparse.Namespace(
        build=True,
        write_report=False,
        build_root=args.v2617_build_root,
        manifest=args.v2617_manifest_path,
        report=v2617.DEFAULT_REPORT,
        clang=v2617.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang",
        lld=v2617.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld",
        readelf=args.readelf,
        file=args.file,
    )
    payload = v2617.make_payload(build_args)
    args.v2617_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.v2617_manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def read_v2617_manifest(path: Path) -> dict[str, Any]:
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
    source_state = payload.get("sources", {})
    required = source_state.get("required", {})
    prohibited = source_state.get("prohibited", {})
    armed_contract = source_state.get("armed_capture_contract", {})
    return {
        "ok": bool(payload.get("ok") and helper.get("ok") and preload.get("ok")),
        "path": rel(path),
        "manifest": payload,
        "helper": helper,
        "preload": preload,
        "direct_matrix_contract_ok": bool(
            required.get("helper_calls_init_v3_with_meta_head")
            and required.get("helper_arms_after_init_before_matrix")
            and required.get("helper_has_v2614_base_commands")
            and required.get("helper_has_bounded_vol_sweep")
            and required.get("tap_auto_arm_disabled_by_build_flags")
            and required.get("tap_exit_on_target_disabled_by_build_flags")
            and not prohibited.get("helper_calls_send_audio_cal_v5")
            and not prohibited.get("helper_audio_set_literal")
        ),
        "armed_contract_ok": bool(
            armed_contract.get("auto_arm_on_initialize") is False
            and armed_contract.get("exit_on_first_4916") is False
        ),
        "capture_contract": payload.get("capture_contract", {}),
    }


def selected_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    if args.build_v2617_artifacts:
        build_v2617_artifacts(args)
    manifest = read_v2617_manifest(args.v2617_manifest_path)
    helper = v2573.artifact_from_manifest(manifest.get("helper", {}), args.helper_path, args.helper_sha256)
    preload = v2573.artifact_from_manifest(manifest.get("preload", {}), args.preload_path, args.preload_sha256)
    return {
        "manifest": manifest,
        "helper": helper,
        "preload": preload,
        "ok": bool(
            manifest.get("ok")
            and manifest.get("direct_matrix_contract_ok")
            and manifest.get("armed_contract_ok")
            and helper.get("ok")
            and preload.get("ok")
        ),
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
    return v2573.select_pulled_dir_from_result(result)


def _cmd_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).lower()
    if text.startswith("0x"):
        try:
            return f"0x{int(text, 16):08x}"
        except ValueError:
            return text
    try:
        return f"0x{int(text, 0):08x}"
    except ValueError:
        return text


def summarize_direct_matrix_capture(artifact_dir: Path) -> dict[str, Any]:
    base_summary = v2490.parse_ownget_artifacts(artifact_dir)
    helper_events_path = artifact_dir / "acdb-v2617-direct-matrix-events.jsonl"
    helper_events = read_jsonl(helper_events_path)
    helper_stages = [
        event.get("stage")
        for event in helper_events
        if event.get("event") == "v2617_direct_matrix"
    ]
    case_rows = [
        event for event in helper_events
        if event.get("event") == "v2617_direct_matrix" and event.get("stage") == "case_return"
    ]
    case_names = [str(event.get("case", "")) for event in case_rows]
    vol_ret0_steps = [
        int_or_none(event.get("step"))
        for event in case_rows
        if event.get("case") in {"vol-size", "vol-data"} and int32_or_none(event.get("ret")) == 0
    ]
    vol_ret0_steps = [step for step in vol_ret0_steps if step is not None]
    acdbtap_dir = artifact_dir / "acdbtap"
    if not (acdbtap_dir / "acdbtap-events.jsonl").exists() and (artifact_dir / "acdbtap-events.jsonl").exists():
        acdbtap_dir = artifact_dir
    rows = base_summary.get("acdbtap_rows", [])
    record_states = [v2573.row_raw_state(row, acdbtap_dir) for row in rows]
    successful = [
        item for item in record_states
        if item.get("ret") == 0 and item.get("valid_raw") and item.get("nonzero")
    ]
    direct_size_rows = [
        item for item in record_states
        if item.get("ret") == 0 and item.get("valid_raw") and item.get("out_len") == 4
    ]
    topology = [item for item in successful if item.get("out_len") == 4916]
    per_device_cmds = {"0x00013265", "0x00013269", "0x0001326e", "0x0001326f"}
    per_device = [
        item for item in successful
        if item.get("out_len") not in {4, 4916} and _cmd_text(item.get("cmd")) in per_device_cmds
    ]
    vol_payloads = [item for item in per_device if _cmd_text(item.get("cmd")) == "0x0001326e"]
    afe_payloads = [item for item in per_device if _cmd_text(item.get("cmd")) == "0x0001326f"]
    audproc_payloads = [item for item in per_device if _cmd_text(item.get("cmd")) in {"0x00013265", "0x00013269"}]
    ioctl_events = base_summary.get("ioctl_trace_events", [])
    pass_through_set_events = [
        event for event in ioctl_events
        if event.get("name") == "AUDIO_SET_CALIBRATION" and event.get("intercept") != "fake-success"
    ]
    fake_set_events = [
        event for event in ioctl_events
        if event.get("name") == "AUDIO_SET_CALIBRATION" and event.get("intercept") == "fake-success"
    ]
    matrix_complete = "done" in helper_stages and len(case_rows) >= 42
    if pass_through_set_events:
        classification = "v2618-boundary-violation-real-audio-set-passthrough"
    elif per_device and vol_payloads:
        classification = "v2618-direct-matrix-perdevice-and-vol-captured"
    elif per_device:
        classification = "v2618-direct-matrix-perdevice-partial-no-vol"
    elif direct_size_rows and matrix_complete:
        classification = "v2618-direct-matrix-metadata-only"
    elif case_rows:
        classification = "v2618-direct-matrix-no-acdbtap-payloads"
    elif helper_events:
        classification = "v2618-helper-events-before-matrix"
    else:
        classification = f"v2618-{base_summary.get('classification', 'no-artifacts')}"
    return {
        "classification": classification,
        "success": classification == "v2618-direct-matrix-perdevice-and-vol-captured",
        "partial_success": classification in {
            "v2618-direct-matrix-perdevice-partial-no-vol",
            "v2618-direct-matrix-metadata-only",
        },
        "operator_valuable": bool(per_device or direct_size_rows or case_rows or rows),
        "helper_event_path": rel(helper_events_path),
        "helper_event_count": len(helper_events),
        "helper_stages": helper_stages,
        "case_return_count": len(case_rows),
        "case_names": case_names,
        "matrix_complete": matrix_complete,
        "base_matrix_seen": "before_base_matrix" in helper_stages,
        "vol_sweep_seen": "before_vol_sweep" in helper_stages,
        "done_seen": "done" in helper_stages,
        "vol_ret0_steps": vol_ret0_steps,
        "direct_size_row_count": len(direct_size_rows),
        "successful_nonzero_count": len(successful),
        "topology_success_count": len(topology),
        "per_device_success_count": len(per_device),
        "audproc_payload_count": len(audproc_payloads),
        "afe_payload_count": len(afe_payloads),
        "vol_payload_count": len(vol_payloads),
        "fake_audio_set_count": len(fake_set_events),
        "real_audio_set_pass_through_count": len(pass_through_set_events),
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
        "decision": "v2618-acdb-direct-matrix-live-runner-dry-run",
        "host_only": True,
        "device_action": "none",
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "v2617_artifacts": artifacts,
        "v2490_engine": {
            "run_id": "V2490",
            "decision": base_payload.get("decision"),
            "live_ready": base_payload.get("live_ready", False),
            "command_safety": base_payload.get("command_safety"),
            "commands": base_payload.get("commands", {}),
        },
        "capture_contract": {
            "direct_matrix": "V2616 base geometry plus VOL gain-step sweep 0..15",
            "manual_arm_after_init": True,
            "auto_arm_on_initialize": False,
            "exit_on_first_4916": False,
            "fake_audio_cal_allocate": True,
            "combined_preload": True,
            "success_requires": "ret==0 plus non-all-zero raw buffers; requested length alone is not success",
            "native_replay": "blocked; no SET replay in this runner",
            "raw_private_only": True,
        },
    }
    payload["live_ready"] = bool(artifacts.get("ok") and base_payload.get("live_ready"))
    payload["live_blockers"] = []
    if not artifacts.get("ok"):
        payload["live_blockers"].append("V2617 direct-matrix helper/preload artifacts are not ready")
    payload["live_blockers"].extend(base_payload.get("live_blockers", []))
    payload["command_safety"] = base_payload.get("command_safety", {"ok": False, "findings": ["base payload missing"]})
    payload["ok"] = bool(payload["live_ready"] and payload["command_safety"].get("ok"))
    return payload


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    if args.out_dir is None:
        args.out_dir = default_live_out_dir()
    dry = dry_run_payload(args)
    if not dry.get("ok"):
        raise RuntimeError(f"V2618 live inputs are not ready: {dry.get('live_blockers')}")
    artifacts = dry["v2617_artifacts"]
    base_args = to_v2490_args(args, artifacts)
    result = v2490.run_live(base_args)
    pulled_dir = select_pulled_dir_from_result(result)
    summary = summarize_direct_matrix_capture(pulled_dir) if pulled_dir else {
        "classification": "v2618-no-pulled-artifacts",
        "success": False,
        "partial_success": False,
        "operator_valuable": False,
    }
    wrapper = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{summary['classification']}-rollback-{'pass' if result.get('rolled_back') else 'unknown'}",
        "out_dir": result.get("out_dir"),
        "rolled_back": bool(result.get("rolled_back")),
        "counts_toward_fails_twice": result.get("counts_toward_fails_twice"),
        "operator_valuable": bool(summary.get("operator_valuable")),
        "partial_success": bool(summary.get("partial_success")),
        "success": bool(summary.get("success")),
        "v2617_artifacts": artifacts,
        "v2490_engine_result": result,
        "direct_matrix_summary": summary,
        "ok": bool(result.get("rolled_back") and summary.get("operator_valuable")),
    }
    out_dir_raw = result.get("out_dir")
    if out_dir_raw:
        write_json(ROOT / str(out_dir_raw) / "v2618-result.json", wrapper)
    return wrapper


def write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("direct_matrix_summary", {})
    artifacts = payload.get("v2617_artifacts", {})
    helper = artifacts.get("helper", {})
    preload = artifacts.get("preload", {})
    lines = [
        "# NATIVE_INIT V2618 — ACDB direct matrix live handoff",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Android own-process ACDB direct matrix handoff using the V2490 checked Android",
        "boot/stage/pull/rollback engine and the V2617 helper/preload artifacts. This",
        "is measurement-only: no native replay `SET`, no speaker write, and raw buffers",
        "remain under `workspace/private`.",
        "",
        "## Result",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- ok: `{payload.get('ok')}`",
        f"- rolled_back: `{payload.get('rolled_back')}`",
        f"- counts_toward_fails_twice: `{payload.get('counts_toward_fails_twice')}`",
        f"- operator_valuable: `{payload.get('operator_valuable')}`",
        f"- partial_success: `{payload.get('partial_success')}`",
        f"- out_dir: `{payload.get('out_dir')}`",
        f"- classification: `{summary.get('classification')}`",
        f"- matrix_complete: `{summary.get('matrix_complete')}`",
        f"- case_return_count: `{summary.get('case_return_count')}`",
        f"- direct_size_row_count: `{summary.get('direct_size_row_count')}`",
        f"- per_device_success_count: `{summary.get('per_device_success_count')}`",
        f"- audproc_payload_count: `{summary.get('audproc_payload_count')}`",
        f"- afe_payload_count: `{summary.get('afe_payload_count')}`",
        f"- vol_payload_count: `{summary.get('vol_payload_count')}`",
        f"- real_audio_set_pass_through_count: `{summary.get('real_audio_set_pass_through_count')}`",
        "",
        "## Artifact Selection",
        "",
        f"- helper: `{helper.get('path')}`",
        f"- helper_sha256: `{helper.get('sha256')}`",
        f"- preload: `{preload.get('path')}`",
        f"- preload_sha256: `{preload.get('sha256')}`",
        "",
        "## Contract",
        "",
        "- stages the V2617 helper/preload through the V2490 Android-good handoff engine;",
        "- forces `A90_ACDB_FAKE_ALLOCATE=1`; any real audio-cal SET pass-through is a boundary violation;",
        "- keeps `acdb_ioctl` capture silent before `init_v3` returns and helper calls `a90_arm_capture()`;",
        "- executes the direct V2616 matrix plus VOL gain-step sweep once;",
        "- pulls `/data/local/tmp/a90-acdb-ownget/` and `acdbtap/` privately; and",
        "- classifies success only from `ret==0` plus non-all-zero raw buffers.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_direct_matrix_live_handoff_v2618.py tests/test_native_audio_acdb_direct_matrix_live_handoff_v2618.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_direct_matrix_live_handoff_v2618 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_direct_matrix_live_handoff_v2618.py --dry-run --write-report`",
        "- live run, if present: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_direct_matrix_live_handoff_v2618.py --run-live --write-report`",
        "- `git diff --check`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--build-v2617-artifacts", action="store_true")
    parser.add_argument("--v2617-build-root", type=Path, default=v2617.DEFAULT_BUILD_ROOT)
    parser.add_argument("--v2617-manifest-path", type=Path, default=v2617.DEFAULT_MANIFEST)
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
    if args.write_report:
        write_report(args.report_path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
