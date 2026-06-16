#!/usr/bin/env python3
"""V2596 Android handoff wrapper for the V2595 direct 0x1122e metadata probe.

Host-only by default.  Live mode reuses the proven V2490 Android
boot/stage/pull/rollback engine, but selects the V2595 helper/preload artifacts
and classifies the metadata-only acdb_ioctl(0x1122e, &0x11135, 4, out, 4)
result from acdb-v2595-direct-preget-events.jsonl.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import build_android_acdb_direct_preget_probe_v2595 as v2595
import native_audio_acdb_ownprocess_get_live_handoff_v2490 as v2490
import native_audio_acdb_perdevice_indirect_capture_live_handoff_v2573 as v2573

ROOT = v2595.ROOT
RUN_ID = "V2596"
BUILD_TAG = "v2596-audio-acdb-direct-preget-live-runner"
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2596_AUDIO_ACDB_DIRECT_PREGET_LIVE_RUNNER_2026-06-16.md"


def rel(path: Path | str) -> str:
    return v2573.rel(path)


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"v2596-acdb-direct-preget-{stamp}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return v2573.read_jsonl(path)


def int_or_none(value: Any) -> int | None:
    return v2573.int_or_none(value)


def int32_or_none(value: Any) -> int | None:
    return v2573.int32_or_none(value)


def build_v2595_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    build_args = argparse.Namespace(
        build=True,
        build_root=args.v2595_build_root,
        manifest=args.v2595_manifest_path,
        report_path=v2595.DEFAULT_REPORT,
        clang=v2595.TOOLCHAIN_ROOT / "bin/clang",
        lld=v2595.TOOLCHAIN_ROOT / "bin/ld.lld",
        readelf=args.readelf,
        file=args.file,
        write_report=False,
    )
    payload = v2595.make_payload(build_args)
    args.v2595_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.v2595_manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def read_v2595_manifest(path: Path) -> dict[str, Any]:
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
    return {
        "ok": bool(payload.get("ok") and helper.get("ok") and preload.get("ok")),
        "path": rel(path),
        "manifest": payload,
        "helper": helper,
        "preload": preload,
        "direct_preget_contract_ok": bool(
            required.get("preget_cmd_0x1122e")
            and required.get("preget_app_id_0x11135")
            and required.get("preget_geometry_4_4")
            and required.get("preget_direct_acdb_ioctl_call")
            and not prohibited.get("preget_calls_send_audio_cal")
        ),
        "skips_real_common_topology": bool(required.get("preget_skips_real_common_topology_by_default")),
        "capture_contract": payload.get("capture_contract", {}),
    }


def selected_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    if args.build_v2595_artifacts:
        build_v2595_artifacts(args)
    manifest = read_v2595_manifest(args.v2595_manifest_path)
    helper = v2573.artifact_from_manifest(manifest.get("helper", {}), args.helper_path, args.helper_sha256)
    preload = v2573.artifact_from_manifest(manifest.get("preload", {}), args.preload_path, args.preload_sha256)
    return {
        "manifest": manifest,
        "helper": helper,
        "preload": preload,
        "ok": bool(
            manifest.get("ok")
            and manifest.get("direct_preget_contract_ok")
            and manifest.get("skips_real_common_topology")
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


def summarize_direct_preget_capture(artifact_dir: Path) -> dict[str, Any]:
    base_summary = v2490.parse_ownget_artifacts(artifact_dir)
    helper_events_path = artifact_dir / "acdb-v2595-direct-preget-events.jsonl"
    helper_events = read_jsonl(helper_events_path)
    helper_stages = [
        event.get("stage")
        for event in helper_events
        if event.get("event") == "v2595_direct_preget"
    ]
    direct_rows = [
        event for event in helper_events
        if event.get("event") == "v2595_direct_preget" and event.get("stage") == "direct_preget_return"
    ]
    row = direct_rows[-1] if direct_rows else {}
    ret = int32_or_none(row.get("ret"))
    out_word = int_or_none(row.get("out_word"))
    if out_word is None:
        out_word = 0
    out_word &= 0xFFFFFFFF
    ioctl_events = base_summary.get("ioctl_trace_events", [])
    pass_through_set_events = [
        event for event in ioctl_events
        if event.get("name") == "AUDIO_SET_CALIBRATION" and event.get("intercept") != "fake-success"
    ]
    fake_set_events = [
        event for event in ioctl_events
        if event.get("name") == "AUDIO_SET_CALIBRATION" and event.get("intercept") == "fake-success"
    ]
    if pass_through_set_events:
        classification = "v2596-boundary-violation-real-audio-set-passthrough"
    elif ret == 0 and out_word != 0:
        classification = "v2596-direct-preget-ret0-nonzero"
    elif ret == 0:
        classification = "v2596-direct-preget-ret0-zero"
    elif direct_rows:
        classification = "v2596-direct-preget-ret-nonzero"
    elif "before_direct_preget" in helper_stages:
        classification = "v2596-direct-preget-no-return-row"
    elif helper_events:
        classification = "v2596-no-direct-preget-attempt"
    else:
        classification = f"v2596-{base_summary.get('classification', 'no-artifacts')}"
    return {
        "classification": classification,
        "success": classification == "v2596-direct-preget-ret0-nonzero",
        "partial_success": classification in {"v2596-direct-preget-ret0-zero", "v2596-direct-preget-ret-nonzero"},
        "ret": ret,
        "out_word": f"0x{out_word:08x}",
        "out_nonzero": bool(out_word),
        "helper_event_path": rel(helper_events_path),
        "helper_event_count": len(helper_events),
        "helper_stages": helper_stages,
        "skip_real_common_topology_seen": "skip_real_common_topology" in helper_stages,
        "patch_initialized_flag_ok": any(
            event.get("stage") == "patch_initialized_flag_return" and event.get("code") == 0
            for event in helper_events
        ),
        "before_direct_preget_seen": "before_direct_preget" in helper_stages,
        "direct_preget_rows": direct_rows,
        "fake_audio_set_count": len(fake_set_events),
        "real_audio_set_pass_through_count": len(pass_through_set_events),
        "base_summary": base_summary,
    }


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    artifacts = selected_artifacts(args)
    base_args = to_v2490_args(args, artifacts) if artifacts.get("ok") else None
    base_payload = v2490.dry_run_payload(base_args) if base_args else {}
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2596-acdb-direct-preget-live-runner-dry-run",
        "host_only": True,
        "device_action": "none",
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "v2595_artifacts": artifacts,
        "v2490_engine": {
            "run_id": "V2490",
            "decision": base_payload.get("decision"),
            "live_ready": base_payload.get("live_ready", False),
            "command_safety": base_payload.get("command_safety"),
            "commands": base_payload.get("commands", {}),
        },
        "capture_contract": {
            "direct_query": "acdb_ioctl(0x1122e, &0x11135, 4, &out_word, 4)",
            "fake_audio_cal_allocate": True,
            "combined_preload": True,
            "success_requires": "ret==0 and out_word non-zero; requested length alone is not success",
            "send_audio_cal_v5_not_used": True,
            "raw_private_only": True,
        },
    }
    payload["live_ready"] = bool(artifacts.get("ok") and base_payload.get("live_ready"))
    payload["live_blockers"] = []
    if not artifacts.get("ok"):
        payload["live_blockers"].append("V2595 direct-preget helper/preload artifacts are not ready")
    payload["live_blockers"].extend(base_payload.get("live_blockers", []))
    payload["command_safety"] = base_payload.get("command_safety", {"ok": False, "findings": ["base payload missing"]})
    payload["ok"] = bool(payload["live_ready"] and payload["command_safety"].get("ok"))
    return payload


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    if args.out_dir is None:
        args.out_dir = default_live_out_dir()
    dry = dry_run_payload(args)
    if not dry.get("ok"):
        raise RuntimeError(f"V2596 live inputs are not ready: {dry.get('live_blockers')}")
    artifacts = dry["v2595_artifacts"]
    base_args = to_v2490_args(args, artifacts)
    result = v2490.run_live(base_args)
    pulled_dir = select_pulled_dir_from_result(result)
    summary = summarize_direct_preget_capture(pulled_dir) if pulled_dir else {
        "classification": "v2596-no-pulled-artifacts",
        "success": False,
        "partial_success": False,
    }
    wrapper = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{summary['classification']}-rollback-{'pass' if result.get('rolled_back') else 'unknown'}",
        "out_dir": result.get("out_dir"),
        "v2595_artifacts": artifacts,
        "v2490_engine_result": result,
        "direct_preget_summary": summary,
        "ok": bool(result.get("rolled_back") and (summary.get("success") or summary.get("partial_success"))),
    }
    out_dir_raw = result.get("out_dir")
    if out_dir_raw:
        write_json(ROOT / str(out_dir_raw) / "v2596-result.json", wrapper)
    return wrapper


def write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("direct_preget_summary", {})
    artifacts = payload.get("v2595_artifacts", {})
    helper = artifacts.get("helper", {})
    preload = artifacts.get("preload", {})
    lines = [
        "# NATIVE_INIT V2596 — ACDB direct pre-GET live runner",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Android own-process ACDB direct metadata probe wrapper. Dry-run mode only verifies the checked",
        "V2490 Android handoff plan and selected V2595 private artifacts; live mode is recoverable to V2321.",
        "",
        "## Result",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- ok: `{payload.get('ok')}`",
        f"- out_dir: `{payload.get('out_dir')}`",
        f"- classification: `{summary.get('classification')}`",
        f"- ret: `{summary.get('ret')}`",
        f"- out_word: `{summary.get('out_word')}`",
        f"- out_nonzero: `{summary.get('out_nonzero')}`",
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
        "- stages the V2595 helper/preload via the V2490 Android-good handoff engine;",
        "- sets `A90_ACDB_FAKE_ALLOCATE=1`; the ioctl preload fake-successes audio-cal ALLOC/DEALLOC/SET only;",
        "- executes the helper once and pulls `/data/local/tmp/a90-acdb-ownget/` privately;",
        "- classifies `acdb-v2595-direct-preget-events.jsonl`; and",
        "- success requires `ret==0` and `out_word != 0`, not the requested 4-byte geometry alone.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_direct_preget_live_handoff_v2596.py tests/test_native_audio_acdb_direct_preget_live_handoff_v2596.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_direct_preget_live_handoff_v2596`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -p 'test_native_audio_acdb_direct_preget_live_handoff_v2596.py'`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_direct_preget_live_handoff_v2596.py --dry-run --write-report`",
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
    parser.add_argument("--build-v2595-artifacts", action="store_true")
    parser.add_argument("--v2595-build-root", type=Path, default=v2595.DEFAULT_BUILD_ROOT)
    parser.add_argument("--v2595-manifest-path", type=Path, default=v2595.DEFAULT_MANIFEST)
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
