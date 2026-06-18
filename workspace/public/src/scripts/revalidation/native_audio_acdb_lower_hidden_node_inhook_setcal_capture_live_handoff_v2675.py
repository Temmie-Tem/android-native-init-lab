#!/usr/bin/env python3
"""V2675 Android handoff wrapper for V2674 lower-hidden-node ACDB SET capture.

Host-only by default. Live mode reuses the V2490 checked Android
boot/stage/pull/rollback engine, but selects the V2674 helper/preload artifacts
and classifies the captured ordered ``AUDIO_SET_CALIBRATION`` records emitted to
``setcal-events.jsonl``. The live action remains measurement-only: the V2674
ioctl shim always fake-successes SET (it never reaches the kernel SET), there is
no native replay, no speaker write, and raw buffers stay under
``workspace/private``.

The own-process send path is the V2674 lower-hidden-node preload:

    acdb_loader_init_v3("/vendor/etc/audconf/OPEN", delta, 0)
      -> common-topology hook skips real common and patches initialized flag
      -> a90_arm_capture()
      -> a90_run_lower_hidden_nodes()
      -> create_cal_node / allocate_cal_block / pinned GET / fake SET

The V2674 preload intercepts every ``AUDIO_SET_CALIBRATION``, dumps
``arg[0:data_size]`` plus the same-process dma-buf payload when present, then
fake-successes the SET. This unit specifically looks for custom-topology SET
records needed after V2648: cal_types 10, 14, and 24.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import build_android_acdb_lower_hidden_node_inhook_setcal_capture_v2674 as v2674
import native_audio_acdb_ownprocess_get_live_handoff_v2490 as v2490
import native_audio_acdb_perdevice_indirect_capture_live_handoff_v2573 as v2573

ROOT = v2674.ROOT
RUN_ID = "V2675"
BUILD_TAG = "v2675-audio-acdb-lower-hidden-node-inhook-setcal-capture-live-runner"
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2675_AUDIO_ACDB_LOWER_HIDDEN_NODE_INHOOK_SETCAL_CAPTURE_LIVE_HANDOFF_2026-06-18.md"

# Gate-4 custom topology records needed by the downstream ADM/ASM/AFE open path.
CUSTOM_TOPOLOGY_CAL_TYPES = {10, 14, 24}
SUPPLEMENTAL_CAL_TYPES: set[int] = set()


def rel(path: Path | str) -> str:
    return v2573.rel(path)


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"v2675-acdb-lower-hidden-node-inhook-setcal-capture-{stamp}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return v2573.read_jsonl(path)


def int_or_none(value: Any) -> int | None:
    return v2573.int_or_none(value)


def int32_or_none(value: Any) -> int | None:
    return v2573.int32_or_none(value)


def build_v2674_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    build_args = argparse.Namespace(
        build=True,
        write_report=False,
        build_root=args.v2674_build_root,
        manifest=args.v2674_manifest_path,
        report=v2674.DEFAULT_REPORT,
        clang=v2674.v2659.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang",
        lld=v2674.v2659.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld",
        readelf=args.readelf,
        file=args.file,
    )
    payload = v2674.make_payload(build_args)
    args.v2674_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.v2674_manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def read_v2674_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "error": f"manifest missing: {rel(path)}"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {"ok": False, "error": f"manifest json error: {error}"}
    build = payload.get("build", {})
    artifacts = build.get("artifacts", {}) if isinstance(build, dict) else {}
    helper = artifacts.get("helper", {}) if isinstance(artifacts, dict) else {}
    preload = artifacts.get("preload", {}) if isinstance(artifacts, dict) else {}
    sources = payload.get("sources", {})
    required = sources.get("required", {}) if isinstance(sources, dict) else {}
    prohibited = sources.get("prohibited", {}) if isinstance(sources, dict) else {}
    contract = payload.get("capture_contract", {})
    required_target_types = list(v2674.TARGET_CAL_TYPES)
    setcal_contract_ok = bool(
        sources.get("required_ok")
        and sources.get("prohibited_ok")
        and contract.get("target_cal_types") == required_target_types
        and contract.get("get_commands") == {str(key): value for key, value in v2674.TARGET_GET_COMMANDS.items()}
        and required.get("helper_imports_init_v3")
        and required.get("helper_calls_init_v3_open_audconf")
        and required.get("helper_does_not_arm_after_init")
        and required.get("helper_does_not_call_lower_after_init")
        and required.get("helper_records_unexpected_init_return")
        and required.get("helper_does_not_import_common_topology")
        and required.get("helper_does_not_import_send_audio_cal_v5")
        and required.get("preload_exports_common_skip_hook")
        and required.get("preload_patches_initialized_flag")
        and required.get("preload_arms_inside_common_hook")
        and required.get("preload_runs_lower_inside_common_hook")
        and required.get("preload_exits_after_inhook_lower")
        and required.get("preload_exports_lower_runner")
        and required.get("preload_imports_arm_capture")
        and required.get("preload_uses_hidden_create_offset")
        and required.get("preload_uses_hidden_allocate_offset")
        and required.get("preload_targets_all_custom_cal_types")
        and required.get("preload_targets_pinned_get_commands")
        and required.get("preload_builds_32_byte_set_arg")
        and required.get("preload_sets_cal_type_size_and_mem_handle")
        and required.get("preload_calls_acdb_ioctl_get")
        and required.get("preload_calls_fake_set_ioctl")
        and required.get("ioctl_always_fakes_audio_set")
        and required.get("ioctl_dumps_arg_and_dmabuf")
        and not prohibited.get("helper_opens_msm_audio_cal")
        and not prohibited.get("helper_issues_ioctl")
        and not prohibited.get("helper_calls_common_topology")
        and not prohibited.get("helper_calls_send_audio_cal_v5")
        and not prohibited.get("preload_real_audio_set_syscall")
        and not prohibited.get("preload_opens_msm_audio_cal")
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
        "capture_contract": contract,
    }

def selected_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    if args.build_v2674_artifacts:
        build_v2674_artifacts(args)
    manifest = read_v2674_manifest(args.v2674_manifest_path)
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
    classification = "v2675-no-pulled-artifacts"
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
        classification = "v2675-preflash-native-bridge-unavailable"
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


def _event_rows(events: list[dict[str, Any]], event_names: str | tuple[str, ...]) -> list[dict[str, Any]]:
    names = (event_names,) if isinstance(event_names, str) else event_names
    return [event for event in events if event.get("event") in names]


HEX_LITERAL_RE = re.compile(r'(:)0x([0-9a-fA-F]+)([,}])')


def read_v2674_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read V2674 event JSONL, tolerating C-emitted unquoted hex scalars."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        fixed = HEX_LITERAL_RE.sub(lambda m: f'{m.group(1)}{int(m.group(2), 16)}{m.group(3)}', line)
        try:
            value = json.loads(fixed)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def summarize_setcal_capture(artifact_dir: Path) -> dict[str, Any]:
    base_summary = v2490.parse_ownget_artifacts(artifact_dir)
    setcal_path = artifact_dir / "setcal-events.jsonl"
    lower_path = artifact_dir / "acdb-v2674-lower-hidden-inhook-events.jsonl"
    helper_path = artifact_dir / "acdb-v2674-lower-hidden-inhook-helper-events.jsonl"
    setcal_events = [
        event for event in read_jsonl(setcal_path)
        if event.get("event") == "setcal_capture"
    ]
    lower_events = _event_rows(read_v2674_jsonl(lower_path), ("v2674_lower_hidden", "v2672_lower_hidden"))
    helper_events = _event_rows(read_v2674_jsonl(helper_path), ("v2674_lower_hidden_helper", "v2672_lower_hidden_helper"))
    rows = [_setcal_row(event) for event in setcal_events]
    lower_stages = [str(event.get("stage")) for event in lower_events]
    helper_stages = [str(event.get("stage")) for event in helper_events]
    all_stages = lower_stages + helper_stages

    lower_codes_by_stage: dict[str, list[int]] = {}
    lower_values_by_stage: dict[str, list[int]] = {}
    lower_cal_types_by_stage: dict[str, list[int]] = {}
    for event in lower_events:
        stage = str(event.get("stage"))
        code = int32_or_none(event.get("code"))
        value = int_or_none(event.get("value"))
        cal_type = int_or_none(event.get("cal_type"))
        if code is not None:
            lower_codes_by_stage.setdefault(stage, []).append(code)
        if value is not None:
            lower_values_by_stage.setdefault(stage, []).append(value)
        if cal_type is not None:
            lower_cal_types_by_stage.setdefault(stage, []).append(cal_type)

    helper_codes_by_stage: dict[str, list[int]] = {}
    for event in helper_events:
        stage = str(event.get("stage"))
        code = int32_or_none(event.get("code"))
        if code is not None:
            helper_codes_by_stage.setdefault(stage, []).append(code)

    init_v3_codes = helper_codes_by_stage.get("init_v3_return", [])
    lower_return_codes = (
        helper_codes_by_stage.get("lower_hidden_nodes_return", [])
        + lower_codes_by_stage.get("lower_hidden_nodes_return_inside_common_hook", [])
    )
    create_cal_node_codes = lower_codes_by_stage.get("create_cal_node_return", [])
    allocate_cal_block_codes = lower_codes_by_stage.get("allocate_cal_block_return", [])
    acdb_get_codes = lower_codes_by_stage.get("acdb_ioctl_get_return", [])
    fake_set_codes = lower_codes_by_stage.get("fake_set_ioctl_return", [])
    sequence_codes = lower_codes_by_stage.get("lower_hidden_sequence_complete", [])

    inhook_sequence_started = "armed_inside_common_hook" in lower_stages
    inhook_exit_seen = "exit_after_inhook_lower_hidden_nodes" in lower_stages
    common_hook_skipped = (
        "entered_common_topology_hook" in lower_stages
        and "skip_real_common_topology" in lower_stages
        and "patch_initialized_flag_return" in lower_stages
        and inhook_sequence_started
    )
    helper_started_lower = "armed_before_lower_hidden_nodes" in helper_stages
    lower_runner_missing = "lower_runner_missing" in helper_stages
    lower_runner_entered = bool(
        inhook_sequence_started
        or "loader_base_resolved" in lower_stages
        or "patched_initialized_flag" in lower_stages
        or create_cal_node_codes
        or allocate_cal_block_codes
        or acdb_get_codes
        or fake_set_codes
        or sequence_codes
    )
    lower_sequence_complete = "lower_hidden_sequence_complete" in lower_stages
    lower_get_seen = bool(acdb_get_codes)
    lower_fake_set_seen = bool(fake_set_codes)

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
    target_rows = [row for row in rows if row["cal_type"] in CUSTOM_TOPOLOGY_CAL_TYPES]
    target_payload_rows = [row for row in target_rows if row["is_payload"]]
    target_payload_failed_rows = [
        row for row in target_payload_rows
        if row.get("dmabuf_status") in {"mmap-failed", "dump-failed", "cal-size-over-cap"}
    ]
    target_cal_types_captured = sorted({row["cal_type"] for row in target_rows})
    missing_target_cal_types = sorted(CUSTOM_TOPOLOGY_CAL_TYPES - set(target_cal_types_captured))
    target_complete = not missing_target_cal_types
    target_payloads_dumped = not target_payload_failed_rows
    supplemental_rows = [row for row in rows if row["cal_type"] in SUPPLEMENTAL_CAL_TYPES]

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
    allocate_cal_types_seen = sorted(
        {
            int_or_none(event.get("arg_snapshot", {}).get("cal_type"))
            for event in ioctl_events
            if event.get("name") == "AUDIO_ALLOCATE_CALIBRATION"
            and isinstance(event.get("arg_snapshot"), dict)
        }
        - {None}
    )
    target_allocate_cal_types_seen = sorted(set(allocate_cal_types_seen) & CUSTOM_TOPOLOGY_CAL_TYPES)
    missing_target_allocate_cal_types = sorted(CUSTOM_TOPOLOGY_CAL_TYPES - set(target_allocate_cal_types_seen))

    if real_set_events:
        classification = "v2675-boundary-violation-real-audio-set-passthrough"
    elif target_complete and target_payloads_dumped:
        classification = "v2675-lower-hidden-custom-setcal-captured"
    elif target_rows:
        classification = "v2675-lower-hidden-custom-setcal-partial"
    elif lower_fake_set_seen and not rows:
        classification = "v2675-lower-hidden-fake-set-called-no-setcal-records"
    elif lower_sequence_complete and not rows:
        classification = "v2675-lower-hidden-sequence-complete-no-setcal"
    elif lower_get_seen and not rows:
        classification = "v2675-lower-hidden-get-no-setcal"
    elif inhook_sequence_started and lower_runner_entered and not rows:
        classification = "v2675-inhook-lower-runner-entered-no-setcal"
    elif lower_runner_entered and not rows:
        classification = "v2675-lower-hidden-runner-entered-no-setcal"
    elif helper_started_lower and not rows:
        classification = "v2675-helper-started-lower-runner-no-lower-events"
    elif lower_runner_missing:
        classification = "v2675-helper-lower-runner-missing"
    elif common_hook_skipped and not rows:
        classification = "v2675-init-common-skip-no-lower-runner"
    elif rows:
        classification = "v2675-setcal-records-no-target-custom-topology"
    else:
        classification = f"v2675-{base_summary.get('classification', 'no-setcal-records')}"

    success = classification == "v2675-lower-hidden-custom-setcal-captured"
    partial_success = classification in {
        "v2675-lower-hidden-custom-setcal-partial",
        "v2675-setcal-records-no-target-custom-topology",
        "v2675-lower-hidden-fake-set-called-no-setcal-records",
        "v2675-lower-hidden-sequence-complete-no-setcal",
        "v2675-lower-hidden-get-no-setcal",
        "v2675-lower-hidden-runner-entered-no-setcal",
        "v2675-inhook-lower-runner-entered-no-setcal",
        "v2675-helper-started-lower-runner-no-lower-events",
        "v2675-helper-lower-runner-missing",
        "v2675-init-common-skip-no-lower-runner",
    }
    operator_valuable = bool(rows or lower_events or helper_events or common_hook_skipped)

    return {
        "classification": classification,
        "success": success,
        "partial_success": partial_success,
        "operator_valuable": operator_valuable,
        "counts_toward_fails_twice": False if operator_valuable else base_summary.get("counts_toward_fails_twice"),
        "setcal_events_path": rel(setcal_path),
        "lower_events_path": rel(lower_path),
        "helper_events_path": rel(helper_path),
        "phase_events_path": rel(lower_path),
        "phase_stage_count": len(all_stages),
        "phase_stages": all_stages,
        "lower_stage_count": len(lower_stages),
        "lower_stages": lower_stages,
        "helper_stage_count": len(helper_stages),
        "helper_stages": helper_stages,
        "common_hook_skipped": common_hook_skipped,
        "inhook_sequence_started": inhook_sequence_started,
        "inhook_exit_seen": inhook_exit_seen,
        "helper_started_lower": helper_started_lower,
        "lower_runner_missing": lower_runner_missing,
        "lower_runner_entered": lower_runner_entered,
        "lower_sequence_complete": lower_sequence_complete,
        "lower_get_seen": lower_get_seen,
        "lower_fake_set_seen": lower_fake_set_seen,
        "init_v3_codes": init_v3_codes,
        "lower_return_codes": lower_return_codes,
        "create_cal_node_codes": create_cal_node_codes,
        "allocate_cal_block_codes": allocate_cal_block_codes,
        "acdb_get_codes": acdb_get_codes,
        "fake_set_codes": fake_set_codes,
        "sequence_codes": sequence_codes,
        "lower_codes_by_stage": lower_codes_by_stage,
        "lower_values_by_stage": lower_values_by_stage,
        "lower_cal_types_by_stage": lower_cal_types_by_stage,
        "helper_codes_by_stage": helper_codes_by_stage,
        "setcal_record_count": len(rows),
        "cal_types_seen": cal_types_seen,
        "allocate_cal_types_seen": allocate_cal_types_seen,
        "custom_allocate_cal_types_seen": target_allocate_cal_types_seen,
        "missing_custom_allocate_cal_types": missing_target_allocate_cal_types,
        "payload_record_count": len(payload_rows),
        "header_only_record_count": len(header_only_rows),
        "arg_dump_count": len(arg_dump_rows),
        "dmabuf_dumped_count": len(dmabuf_dumped_rows),
        "dmabuf_failed_count": len(dmabuf_failed_rows),
        "custom_topology_record_count": len(target_rows),
        "custom_payload_record_count": len(target_payload_rows),
        "custom_payload_failed_count": len(target_payload_failed_rows),
        "custom_cal_types_captured": target_cal_types_captured,
        "missing_custom_cal_types": missing_target_cal_types,
        "custom_topology_complete": target_complete,
        "custom_payloads_dumped": target_payloads_dumped,
        "supplemental_cal25_count": len(supplemental_rows),
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
        "decision": "v2675-acdb-lower-hidden-node-inhook-setcal-capture-live-runner-dry-run",
        "host_only": True,
        "device_action": "none",
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "v2674_artifacts": artifacts,
        "v2490_engine": {
            "run_id": "V2490",
            "decision": base_payload.get("decision"),
            "live_ready": base_payload.get("live_ready", False),
            "command_safety": base_payload.get("command_safety"),
            "commands": base_payload.get("commands", {}),
        },
        "capture_contract": {
            "send_path": "init_v3 -> common skip hook -> a90_arm_capture -> a90_run_lower_hidden_nodes -> create/allocate/GET/fake-SET",
            "set_intercept": "AUDIO_SET_CALIBRATION always fake-successed; never reaches kernel SET",
            "set_arg_dump": "arg[0:data_size] dumped + SHA-256 (cap 4096 bytes)",
            "dmabuf_dump": "cal_size>0 and mem_handle>=0 -> same-process mmap dump + SHA-256 (cap 262144 bytes)",
            "header_only_ok": "cal_size==0 or mem_handle<0 is a valid header-only record",
            "fake_audio_cal_allocate": True,
            "combined_preload": True,
            "target_cal_types": sorted(CUSTOM_TOPOLOGY_CAL_TYPES),
            "supplemental_cal_types": sorted(SUPPLEMENTAL_CAL_TYPES),
            "success_requires": "fake SET records for cal_types 10, 14, and 24; payload records must dump their same-process dma-buf",
            "native_replay": "blocked; no SET replay in this runner",
            "raw_private_only": True,
        },
    }
    payload["live_ready"] = bool(artifacts.get("ok") and base_payload.get("live_ready"))
    payload["live_blockers"] = []
    if not artifacts.get("ok"):
        payload["live_blockers"].append("V2674 SET-cal helper/preload artifacts are not ready")
    payload["live_blockers"].extend(base_payload.get("live_blockers", []))
    payload["command_safety"] = base_payload.get("command_safety", {"ok": False, "findings": ["base payload missing"]})
    payload["ok"] = bool(payload["live_ready"] and payload["command_safety"].get("ok"))
    return payload


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    if args.out_dir is None:
        args.out_dir = default_live_out_dir()
    dry = dry_run_payload(args)
    if not dry.get("ok"):
        raise RuntimeError(f"V2675 live inputs are not ready: {dry.get('live_blockers')}")
    artifacts = dry["v2674_artifacts"]
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
        "v2674_artifacts": artifacts,
        "v2490_engine_result": result,
        "setcal_summary": summary,
        "ok": bool(result.get("rolled_back") and summary.get("operator_valuable")),
    }
    out_dir_raw = result.get("out_dir")
    if out_dir_raw:
        write_json(ROOT / str(out_dir_raw) / "v2675-result.json", wrapper)
    return wrapper


def write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("setcal_summary", {})
    artifacts = payload.get("v2674_artifacts", {})
    helper = artifacts.get("helper", {})
    preload = artifacts.get("preload", {})
    lines = [
        "# NATIVE_INIT V2675 — ACDB lower-hidden-node SET capture live handoff",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Android own-process ACDB SET-calibration capture using the V2490 checked Android",
        "boot/stage/pull/rollback engine and the V2674 helper/preload artifacts. This is",
        "measurement-only: the V2674 ioctl shim always fake-successes",
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
        "- rollback_health: `v2321 version verified; selftest fail=0`" if payload.get("rolled_back") else "- rollback_health: `not verified`",
        f"- classification: `{summary.get('classification')}`",
        f"- failure_phase: `{summary.get('failure_phase')}`",
        f"- v2490_error: `{summary.get('v2490_error')}`",
        f"- common_hook_skipped: `{summary.get('common_hook_skipped')}`",
        f"- inhook_sequence_started: `{summary.get('inhook_sequence_started')}`",
        f"- inhook_exit_seen: `{summary.get('inhook_exit_seen')}`",
        f"- helper_started_lower: `{summary.get('helper_started_lower')}`",
        f"- lower_runner_entered: `{summary.get('lower_runner_entered')}`",
        f"- lower_sequence_complete: `{summary.get('lower_sequence_complete')}`",
        f"- lower_get_seen: `{summary.get('lower_get_seen')}`",
        f"- lower_fake_set_seen: `{summary.get('lower_fake_set_seen')}`",
        f"- phase_stage_count: `{summary.get('phase_stage_count')}`",
        f"- phase_stages: `{summary.get('phase_stages')}`",
        f"- setcal_record_count: `{summary.get('setcal_record_count')}`",
        f"- cal_types_seen: `{summary.get('cal_types_seen')}`",
        f"- init_v3_codes: `{summary.get('init_v3_codes')}`",
        f"- lower_return_codes: `{summary.get('lower_return_codes')}`",
        f"- create_cal_node_codes: `{summary.get('create_cal_node_codes')}`",
        f"- allocate_cal_block_codes: `{summary.get('allocate_cal_block_codes')}`",
        f"- acdb_get_codes: `{summary.get('acdb_get_codes')}`",
        f"- fake_set_codes: `{summary.get('fake_set_codes')}`",
        f"- sequence_codes: `{summary.get('sequence_codes')}`",
        f"- allocate_cal_types_seen: `{summary.get('allocate_cal_types_seen')}`",
        f"- custom_allocate_cal_types_seen: `{summary.get('custom_allocate_cal_types_seen')}`",
        f"- missing_custom_allocate_cal_types: `{summary.get('missing_custom_allocate_cal_types')}`",
        f"- payload_record_count: `{summary.get('payload_record_count')}`",
        f"- header_only_record_count: `{summary.get('header_only_record_count')}`",
        f"- arg_dump_count: `{summary.get('arg_dump_count')}`",
        f"- dmabuf_dumped_count: `{summary.get('dmabuf_dumped_count')}`",
        f"- dmabuf_failed_count: `{summary.get('dmabuf_failed_count')}`",
        f"- custom_topology_record_count: `{summary.get('custom_topology_record_count')}`",
        f"- custom_payload_record_count: `{summary.get('custom_payload_record_count')}`",
        f"- custom_payload_failed_count: `{summary.get('custom_payload_failed_count')}`",
        f"- custom_cal_types_captured: `{summary.get('custom_cal_types_captured')}`",
        f"- missing_custom_cal_types: `{summary.get('missing_custom_cal_types')}`",
        f"- custom_topology_complete: `{summary.get('custom_topology_complete')}`",
        f"- custom_payloads_dumped: `{summary.get('custom_payloads_dumped')}`",
        f"- supplemental_cal25_count: `{summary.get('supplemental_cal25_count')}`",
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
            "  V2674 SET-calibration capture path.",
        ])
    if summary.get("classification") == "v2675-init-common-skip-no-lower-runner":
        lines.extend([
            "",
            "## Failure Analysis",
            "",
            "- live rollback passed and the V2674 common-topology skip hook ran during init;",
            "- the helper did not enter the lower-hidden runner, so no SET rows were emitted;",
            "- this is frontier evidence and does not count as a dead retry against the capture theme.",
        ])
    if summary.get("classification") in {
        "v2675-helper-started-lower-runner-no-lower-events",
        "v2675-helper-lower-runner-missing",
        "v2675-lower-hidden-runner-entered-no-setcal",
        "v2675-inhook-lower-runner-entered-no-setcal",
        "v2675-lower-hidden-get-no-setcal",
        "v2675-lower-hidden-sequence-complete-no-setcal",
        "v2675-lower-hidden-fake-set-called-no-setcal-records",
    }:
        lines.extend([
            "",
            "## Failure Analysis",
            "",
        "- live rollback passed and the V2674 in-hook lower-hidden path produced staged events;",
            f"- helper_stages: `{summary.get('helper_stages')}`;",
            f"- lower_stages: `{summary.get('lower_stages')}`;",
            f"- lower_codes_by_stage: `{summary.get('lower_codes_by_stage')}`;",
            "- no complete target SET row set was captured; preserve the private run for operator review.",
        ])
    lines.extend([
        "",
        "These are SET-calibration records observed during the V2674 lower-hidden node path.",
        "Raw bytes remain private artifacts. A success classification requires all missing",
        "10/14/24 SET args to be captured; native ACDB replay is still a separate later unit.",
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
        "- stages the V2674 helper/preload through the V2490 Android-good handoff engine;",
        "- forces `A90_ACDB_FAKE_ALLOCATE=1`; the SET shim always fake-successes and any real",
        "  kernel `AUDIO_SET_CALIBRATION` pass-through is a boundary violation;",
        "- uses the V2674 init common hook to skip real common, patch initialized state,",
        "  arm capture, run `a90_run_lower_hidden_nodes()`, and exit the helper process;",
        "- the in-hook lower runner calls `create_cal_node`,",
        "  `allocate_cal_block`, pinned ACDB GETs, and fake SET for 24/10/14;",
        "- dumps `arg[0:data_size]` for every SET and the same-process dma-buf for payload",
        "  records, with SHA-256 only in public output;",
        "- pulls `/data/local/tmp/a90-acdb-ownget/` (incl. `setcal-events.jsonl`) privately; and",
        "- classifies success only when cal_types `10`, `14`, and `24` are all captured,",
        "  and any target payload dma-buf dump succeeds.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_lower_hidden_node_inhook_setcal_capture_live_handoff_v2675.py tests/test_native_audio_acdb_lower_hidden_node_inhook_setcal_capture_live_handoff_v2675.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_lower_hidden_node_inhook_setcal_capture_live_handoff_v2675 -v`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover tests -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_lower_hidden_node_inhook_setcal_capture_live_handoff_v2675.py --dry-run --write-report`",
        "- live run, if present: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_lower_hidden_node_inhook_setcal_capture_live_handoff_v2675.py --run-live --write-report`",
        "- if live run is present, post-live rollback must verify `a90ctl.py version`",
        "  reports `0.9.285` / `v2321-usb-clean-identity-rodata` and",
        "  `a90ctl.py selftest verbose` reports `fail=0`",
        "- post-live explicit checks: `a90ctl.py version`; `a90ctl.py selftest verbose`",
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
    parser.add_argument("--build-v2674-artifacts", action="store_true")
    parser.add_argument("--v2674-build-root", type=Path, default=v2674.DEFAULT_BUILD_ROOT)
    parser.add_argument("--v2674-manifest-path", type=Path, default=v2674.DEFAULT_MANIFEST)
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
