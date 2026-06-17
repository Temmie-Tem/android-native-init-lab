#!/usr/bin/env python3
"""V2631 Android handoff wrapper for the V2630 ACDB SET-calibration capture.

Host-only by default. Live mode reuses the V2490 checked Android
boot/stage/pull/rollback engine, but selects the V2630 helper/preload artifacts
and classifies the captured ordered ``AUDIO_SET_CALIBRATION`` records emitted to
``setcal-events.jsonl``. The live action remains measurement-only: the V2630
ioctl shim always fake-successes SET (it never reaches the kernel SET), there is
no native replay, no speaker write, and raw buffers stay under
``workspace/private``.

The own-process send path is the V2613/V2614 driver baked into the V2630 helper:

    acdb_loader_init_v3("/vendor/etc/audconf/OPEN", delta, meta_head)
      -> a90_arm_capture()
      -> acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)

The send path internally issues the per-device SET ioctls. The V2630 preload
intercepts each one, dumps ``arg[0:data_size]`` plus the same-process dma-buf
payload (when ``cal_size>0`` and ``mem_handle>=0``), then fakes success. This is
the unit that should yield the full ordered manifest, including the header-only
AFE topology records (cal_type 9/23) that the GET path could not expose
(see docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md, the
2026-06-17 GATE-2 CORRECTION).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import build_android_acdb_setcal_capture_v2630 as v2630
import native_audio_acdb_ownprocess_get_live_handoff_v2490 as v2490
import native_audio_acdb_perdevice_indirect_capture_live_handoff_v2573 as v2573

ROOT = v2630.ROOT
RUN_ID = "V2631"
BUILD_TAG = "v2631-audio-acdb-setcal-capture-live-runner"
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2631_AUDIO_ACDB_SETCAL_CAPTURE_LIVE_HANDOFF_2026-06-18.md"

# AFE-topology header records are the first dmesg blocker; cal_type 9/23 carry the
# topology gate, 8 is the kernel-side AFE topology pair. The send path emits 9/23.
AFE_TOPOLOGY_CAL_TYPES = {8, 9, 23}
# Payload-backed per-device cal that pcm_prepare needs (AUDPROC common 11, ASM/stream 15,
# AFE common 16). These are expected to carry dma-buf payloads.
PAYLOAD_CAL_TYPES = {11, 15, 16}


def rel(path: Path | str) -> str:
    return v2573.rel(path)


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"v2631-acdb-setcal-capture-{stamp}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return v2573.read_jsonl(path)


def int_or_none(value: Any) -> int | None:
    return v2573.int_or_none(value)


def int32_or_none(value: Any) -> int | None:
    return v2573.int32_or_none(value)


def build_v2630_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    build_args = argparse.Namespace(
        build=True,
        write_report=False,
        build_root=args.v2630_build_root,
        manifest=args.v2630_manifest_path,
        report=v2630.DEFAULT_REPORT,
        clang=v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang",
        lld=v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld",
        readelf=args.readelf,
        file=args.file,
    )
    payload = v2630.make_payload(build_args)
    args.v2630_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.v2630_manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def read_v2630_manifest(path: Path) -> dict[str, Any]:
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
    prohibited = sources.get("prohibited", {})
    setcal_contract_ok = bool(
        sources.get("required_ok")
        and sources.get("prohibited_ok")
        and required.get("always_fakes_audio_set")
        and required.get("preserves_full_set_arg")
        and required.get("parses_set_header_words")
        and required.get("same_process_dmabuf_mmap_dump")
        and required.get("header_only_is_not_failure")
        and required.get("sha256_for_arg_and_dmabuf")
        and required.get("retains_v2531_trace_events")
        and required.get("setcal_events_path")
        and required.get("setcal_raw_private_prefix")
        and not prohibited.get("ioctl_opens_msm_audio_cal")
        and not prohibited.get("combined_native_speaker_write")
        and not prohibited.get("combined_persistent_magisk_install")
    )
    return {
        "ok": bool(payload.get("ok") and helper.get("ok") and preload.get("ok")),
        "path": rel(path),
        "manifest": payload,
        "helper": helper,
        "preload": preload,
        "setcal_contract_ok": setcal_contract_ok,
        "capture_contract": payload.get("capture_contract", {}),
    }


def selected_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    if args.build_v2630_artifacts:
        build_v2630_artifacts(args)
    manifest = read_v2630_manifest(args.v2630_manifest_path)
    helper = v2573.artifact_from_manifest(manifest.get("helper", {}), args.helper_path, args.helper_sha256)
    preload = v2573.artifact_from_manifest(manifest.get("preload", {}), args.preload_path, args.preload_sha256)
    return {
        "manifest": manifest,
        "helper": helper,
        "preload": preload,
        "ok": bool(
            manifest.get("ok")
            and manifest.get("setcal_contract_ok")
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


def summarize_no_pulled_artifacts(result: dict[str, Any]) -> dict[str, Any]:
    """Classify V2490 failures that happened before any Android artifact pull.

    The most important case is a checked-helper Android handoff that fails while
    asking the resident native-init bridge to reboot to recovery. In that path no
    Android boot, ACDB helper, or SET-calibration capture happened, so the run is
    not useful evidence against the ACDB capture design and should not consume
    the fails-twice budget.
    """
    classification = "v2631-no-pulled-artifacts"
    failure_phase = None
    counts_toward_fails_twice = result.get("counts_toward_fails_twice")
    failure_evidence: list[str] = []

    out_dir_raw = result.get("out_dir")
    stderr_text = ""
    if out_dir_raw:
        stderr_path = ROOT / str(out_dir_raw) / "flash-android.stderr.txt"
        if stderr_path.exists():
            stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
            failure_evidence.append(rel(stderr_path))

    error = str(result.get("error") or "")
    native_to_recovery_timeout = (
        "flash-android failed" in error
        and "requesting recovery from native init bridge" in stderr_text
        and "native_to_recovery" in stderr_text
        and "bridge command timeout" in stderr_text
    )
    if native_to_recovery_timeout:
        classification = "v2631-preflash-native-bridge-unavailable"
        failure_phase = "native_to_recovery_before_android_flash"
        if counts_toward_fails_twice is None:
            counts_toward_fails_twice = False

    return {
        "classification": classification,
        "success": False,
        "partial_success": False,
        "operator_valuable": False,
        "failure_phase": failure_phase,
        "failure_evidence": failure_evidence,
        "counts_toward_fails_twice": counts_toward_fails_twice,
        "v2490_error": result.get("error"),
    }


def _setcal_row(event: dict[str, Any]) -> dict[str, Any]:
    set_arg = event.get("set_arg", {}) if isinstance(event.get("set_arg"), dict) else {}
    dmabuf = event.get("dmabuf", {}) if isinstance(event.get("dmabuf"), dict) else {}
    cal_size = int_or_none(event.get("cal_size"))
    mem_handle = int32_or_none(event.get("mem_handle"))
    is_payload = bool(cal_size and cal_size > 0 and mem_handle is not None and mem_handle >= 0)
    return {
        "sequence": int_or_none(event.get("sequence")),
        "cal_type": int_or_none(event.get("cal_type")),
        "header_valid": bool(event.get("header_valid")),
        "data_size": int_or_none(event.get("data_size")),
        "cal_type_size": int_or_none(event.get("cal_type_size")),
        "cal_size": cal_size,
        "mem_handle": mem_handle,
        "arg_sha256": set_arg.get("sha256"),
        "arg_len": int_or_none(set_arg.get("len")),
        "arg_dump_rc": int32_or_none(set_arg.get("dump_rc")),
        "arg_all_zero": bool(set_arg.get("all_zero")),
        "dmabuf_status": dmabuf.get("status"),
        "dmabuf_sha256": dmabuf.get("sha256"),
        "dmabuf_len": int_or_none(dmabuf.get("len")),
        "dmabuf_all_zero": bool(dmabuf.get("all_zero")),
        "is_payload": is_payload,
        "is_header_only": not is_payload,
    }


def summarize_setcal_capture(artifact_dir: Path) -> dict[str, Any]:
    base_summary = v2490.parse_ownget_artifacts(artifact_dir)
    setcal_path = artifact_dir / "setcal-events.jsonl"
    setcal_events = [
        event for event in read_jsonl(setcal_path)
        if event.get("event") == "setcal_capture"
    ]
    rows = [_setcal_row(event) for event in setcal_events]

    payload_rows = [row for row in rows if row["is_payload"]]
    header_only_rows = [row for row in rows if row["is_header_only"]]
    arg_dump_rows = [
        row for row in rows
        if row.get("arg_sha256") and not row.get("arg_all_zero") and (row.get("arg_dump_rc") or 0) >= 0
    ]
    dmabuf_dumped_rows = [row for row in payload_rows if row.get("dmabuf_status") == "dumped"]
    dmabuf_failed_rows = [
        row for row in payload_rows
        if row.get("dmabuf_status") in {"mmap-failed", "dump-failed", "cal-size-over-cap"}
    ]

    cal_types_seen = sorted({row["cal_type"] for row in rows if row["cal_type"] is not None})
    afe_topology_rows = [row for row in rows if row["cal_type"] in AFE_TOPOLOGY_CAL_TYPES]
    payload_cal_types_captured = sorted({
        row["cal_type"] for row in dmabuf_dumped_rows if row["cal_type"] in PAYLOAD_CAL_TYPES
    })
    has_cal_type_9 = any(row["cal_type"] == 9 for row in rows)
    has_cal_type_23 = any(row["cal_type"] == 23 for row in rows)
    afe_topology_headers_captured = bool(has_cal_type_9 and has_cal_type_23)
    all_payloads_dumped = bool(payload_rows) and not dmabuf_failed_rows

    ioctl_events = base_summary.get("ioctl_trace_events", [])
    fake_set_events = [
        event for event in ioctl_events
        if event.get("name") == "AUDIO_SET_CALIBRATION"
        and event.get("intercept") in {"fake-success", "fake-set-always"}
    ]
    real_set_events = [
        event for event in ioctl_events
        if event.get("name") == "AUDIO_SET_CALIBRATION"
        and event.get("intercept") not in {"fake-success", "fake-set-always"}
    ]

    if real_set_events:
        classification = "v2631-boundary-violation-real-audio-set-passthrough"
    elif not rows:
        classification = f"v2631-{base_summary.get('classification', 'no-setcal-records')}"
    elif afe_topology_headers_captured and all_payloads_dumped:
        classification = "v2631-setcal-manifest-captured"
    elif afe_topology_headers_captured:
        classification = "v2631-setcal-manifest-partial-dmabuf"
    elif payload_rows or header_only_rows:
        classification = "v2631-setcal-records-no-afe-topology"
    else:
        classification = "v2631-setcal-records-incomplete"

    return {
        "classification": classification,
        "success": classification == "v2631-setcal-manifest-captured",
        "partial_success": classification in {
            "v2631-setcal-manifest-partial-dmabuf",
            "v2631-setcal-records-no-afe-topology",
        },
        "operator_valuable": bool(rows),
        "setcal_events_path": rel(setcal_path),
        "setcal_record_count": len(rows),
        "cal_types_seen": cal_types_seen,
        "payload_record_count": len(payload_rows),
        "header_only_record_count": len(header_only_rows),
        "arg_dump_count": len(arg_dump_rows),
        "dmabuf_dumped_count": len(dmabuf_dumped_rows),
        "dmabuf_failed_count": len(dmabuf_failed_rows),
        "afe_topology_record_count": len(afe_topology_rows),
        "has_cal_type_9": has_cal_type_9,
        "has_cal_type_23": has_cal_type_23,
        "afe_topology_headers_captured": afe_topology_headers_captured,
        "payload_cal_types_captured": payload_cal_types_captured,
        "all_payloads_dumped": all_payloads_dumped,
        "fake_audio_set_count": len(fake_set_events),
        "real_audio_set_pass_through_count": len(real_set_events),
        "ordered_records": rows,
        "base_summary": base_summary,
    }


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    artifacts = selected_artifacts(args)
    base_args = to_v2490_args(args, artifacts) if artifacts.get("ok") else None
    base_payload = v2490.dry_run_payload(base_args) if base_args else {}
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2631-acdb-setcal-capture-live-runner-dry-run",
        "host_only": True,
        "device_action": "none",
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "v2630_artifacts": artifacts,
        "v2490_engine": {
            "run_id": "V2490",
            "decision": base_payload.get("decision"),
            "live_ready": base_payload.get("live_ready", False),
            "command_safety": base_payload.get("command_safety"),
            "commands": base_payload.get("commands", {}),
        },
        "capture_contract": {
            "send_path": "init_v3 -> a90_arm_capture -> send_audio_cal_v5(15,1,0x11135,48000,0,48000,1)",
            "set_intercept": "AUDIO_SET_CALIBRATION always fake-successed; never reaches kernel SET",
            "set_arg_dump": "arg[0:data_size] dumped + SHA-256 (cap 4096 bytes)",
            "dmabuf_dump": "cal_size>0 and mem_handle>=0 -> same-process mmap dump + SHA-256 (cap 262144 bytes)",
            "header_only_ok": "cal_size==0 or mem_handle<0 is a valid header-only record (AFE topology 9/23)",
            "fake_audio_cal_allocate": True,
            "combined_preload": True,
            "success_requires": "AFE topology headers (cal_type 9 and 23) present AND every payload record dma-buf dumped",
            "native_replay": "blocked; no SET replay in this runner",
            "raw_private_only": True,
        },
    }
    payload["live_ready"] = bool(artifacts.get("ok") and base_payload.get("live_ready"))
    payload["live_blockers"] = []
    if not artifacts.get("ok"):
        payload["live_blockers"].append("V2630 SET-cal helper/preload artifacts are not ready")
    payload["live_blockers"].extend(base_payload.get("live_blockers", []))
    payload["command_safety"] = base_payload.get("command_safety", {"ok": False, "findings": ["base payload missing"]})
    payload["ok"] = bool(payload["live_ready"] and payload["command_safety"].get("ok"))
    return payload


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    if args.out_dir is None:
        args.out_dir = default_live_out_dir()
    dry = dry_run_payload(args)
    if not dry.get("ok"):
        raise RuntimeError(f"V2631 live inputs are not ready: {dry.get('live_blockers')}")
    artifacts = dry["v2630_artifacts"]
    base_args = to_v2490_args(args, artifacts)
    result = v2490.run_live(base_args)
    pulled_dir = select_pulled_dir_from_result(result)
    summary = summarize_setcal_capture(pulled_dir) if pulled_dir else summarize_no_pulled_artifacts(result)
    wrapper = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{summary['classification']}-rollback-{'pass' if result.get('rolled_back') else 'unknown'}",
        "out_dir": result.get("out_dir"),
        "rolled_back": bool(result.get("rolled_back")),
        "counts_toward_fails_twice": summary.get(
            "counts_toward_fails_twice",
            result.get("counts_toward_fails_twice"),
        ),
        "operator_valuable": bool(summary.get("operator_valuable")),
        "partial_success": bool(summary.get("partial_success")),
        "success": bool(summary.get("success")),
        "v2630_artifacts": artifacts,
        "v2490_engine_result": result,
        "setcal_summary": summary,
        "ok": bool(result.get("rolled_back") and summary.get("operator_valuable")),
    }
    out_dir_raw = result.get("out_dir")
    if out_dir_raw:
        write_json(ROOT / str(out_dir_raw) / "v2631-result.json", wrapper)
    return wrapper


def write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("setcal_summary", {})
    artifacts = payload.get("v2630_artifacts", {})
    helper = artifacts.get("helper", {})
    preload = artifacts.get("preload", {})
    lines = [
        "# NATIVE_INIT V2631 — ACDB SET-calibration capture live handoff",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Android own-process ACDB SET-calibration capture using the V2490 checked Android",
        "boot/stage/pull/rollback engine and the V2630 helper/preload artifacts. This is",
        "measurement-only: the V2630 ioctl shim always fake-successes",
        "`AUDIO_SET_CALIBRATION` (the kernel SET is never reached), no native replay runs,",
        "no speaker write occurs, and raw buffers remain under `workspace/private`.",
        "",
        "## Result",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- ok: `{payload.get('ok')}`",
        f"- rolled_back: `{payload.get('rolled_back')}`",
        f"- counts_toward_fails_twice: `{payload.get('counts_toward_fails_twice')}`",
        f"- operator_valuable: `{payload.get('operator_valuable')}`",
        f"- partial_success: `{payload.get('partial_success')}`",
        f"- success: `{payload.get('success')}`",
        f"- out_dir: `{payload.get('out_dir')}`",
        f"- classification: `{summary.get('classification')}`",
        f"- failure_phase: `{summary.get('failure_phase')}`",
        f"- v2490_error: `{summary.get('v2490_error')}`",
        f"- setcal_record_count: `{summary.get('setcal_record_count')}`",
        f"- cal_types_seen: `{summary.get('cal_types_seen')}`",
        f"- payload_record_count: `{summary.get('payload_record_count')}`",
        f"- header_only_record_count: `{summary.get('header_only_record_count')}`",
        f"- arg_dump_count: `{summary.get('arg_dump_count')}`",
        f"- dmabuf_dumped_count: `{summary.get('dmabuf_dumped_count')}`",
        f"- dmabuf_failed_count: `{summary.get('dmabuf_failed_count')}`",
        f"- has_cal_type_9: `{summary.get('has_cal_type_9')}`",
        f"- has_cal_type_23: `{summary.get('has_cal_type_23')}`",
        f"- afe_topology_headers_captured: `{summary.get('afe_topology_headers_captured')}`",
        f"- payload_cal_types_captured: `{summary.get('payload_cal_types_captured')}`",
        f"- real_audio_set_pass_through_count: `{summary.get('real_audio_set_pass_through_count')}`",
        "",
        "## Ordered SET Records (metadata only)",
        "",
        "| seq | cal_type | data_size | cal_size | mem_handle | arg_sha256 | dmabuf_status | dmabuf_sha256 |",
        "| ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in summary.get("ordered_records", []) or []:
        lines.append(
            f"| {row.get('sequence')} | {row.get('cal_type')} | {row.get('data_size')} | "
            f"{row.get('cal_size')} | {row.get('mem_handle')} | `{row.get('arg_sha256')}` | "
            f"`{row.get('dmabuf_status')}` | `{row.get('dmabuf_sha256')}` |"
        )
    if not summary.get("ordered_records"):
        lines.append("| - | - | - | - | - | - | - | - |")
    if summary.get("failure_phase") or summary.get("failure_evidence"):
        lines.extend([
            "",
            "## Failure Analysis",
            "",
            "- no Android boot, helper staging, ACDB call, or artifact pull occurred;",
            f"- failure_phase: `{summary.get('failure_phase')}`;",
            f"- failure_evidence: `{summary.get('failure_evidence')}`;",
            "- this is a transport/pre-flash handoff failure, not evidence against the",
            "  V2630 SET-calibration capture path.",
        ])
    lines.extend([
        "",
        "These are candidate SET-calibration records only. They remain private raw artifacts",
        "and require operator Gate-2 mapping before any native ACDB replay manifest update.",
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
        "- stages the V2630 helper/preload through the V2490 Android-good handoff engine;",
        "- forces `A90_ACDB_FAKE_ALLOCATE=1`; the SET shim always fake-successes and any real",
        "  kernel `AUDIO_SET_CALIBRATION` pass-through is a boundary violation;",
        "- runs the V2613/V2614 send path (`send_audio_cal_v5`) once so the per-device SET",
        "  ioctls fire and are intercepted;",
        "- dumps `arg[0:data_size]` for every SET and the same-process dma-buf for payload",
        "  records, with SHA-256 only in public output;",
        "- pulls `/data/local/tmp/a90-acdb-ownget/` (incl. `setcal-events.jsonl`) privately; and",
        "- classifies success only from AFE topology headers (cal_type 9 and 23) plus every",
        "  payload record dma-buf dumped.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_capture_live_handoff_v2631.py tests/test_native_audio_acdb_setcal_capture_live_handoff_v2631.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_capture_live_handoff_v2631 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_capture_live_handoff_v2631.py --dry-run --write-report`",
        "- live run, if present: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_capture_live_handoff_v2631.py --run-live --write-report`",
        "- `git diff --check`",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--build-v2630-artifacts", action="store_true")
    parser.add_argument("--v2630-build-root", type=Path, default=v2630.DEFAULT_BUILD_ROOT)
    parser.add_argument("--v2630-manifest-path", type=Path, default=v2630.DEFAULT_MANIFEST)
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
