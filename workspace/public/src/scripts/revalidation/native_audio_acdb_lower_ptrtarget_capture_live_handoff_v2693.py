#!/usr/bin/env python3
"""V2693 Android handoff wrapper for V2692 lower ACDB pointer-target capture.

Host-only by default. Live mode reuses the V2490 checked Android
boot/stage/pull/rollback engine, but selects the V2692 helper/preload artifacts
built by ``build_android_acdb_lower_ptrtarget_capture_v2692.py``.

The live action is measurement-only: the V2630 ioctl shim in the combined
preload fake-successes every ``AUDIO_SET_CALIBRATION`` and never lets a real
kernel SET through. V2693's new evidence is the same-process pointer target
behind lower hidden-node GET ``in_word1`` values: the V2692 tap verifies the
range against ``/proc/self/maps`` and privately dumps ``ptrtarget-pre`` bytes
before the real ``acdb_ioctl`` call.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import build_android_acdb_lower_ptrtarget_capture_v2692 as v2692
import native_audio_acdb_lower_hidden_node_inhook_setcal_capture_live_handoff_v2675 as v2675
import native_audio_acdb_ownprocess_get_live_handoff_v2490 as v2490
import native_audio_acdb_perdevice_indirect_capture_live_handoff_v2573 as v2573

ROOT = v2692.ROOT
RUN_ID = "V2693"
BUILD_TAG = "v2693-audio-acdb-lower-ptrtarget-capture-live-runner"
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2693_AUDIO_ACDB_LOWER_PTRTARGET_CAPTURE_LIVE_HANDOFF_2026-06-18.md"
TARGET_CAL_TYPES = {10, 14, 24}
TARGET_CMDS = {0x000130DA: 24, 0x00011394: 10, 0x00012E01: 14, 0x000130DC: 25}
HEX_LITERAL_RE = re.compile(r'(:)0x([0-9a-fA-F]+)([,}])')


def rel(path: Path | str) -> str:
    return v2573.rel(path)


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"v2693-acdb-lower-ptrtarget-capture-{stamp}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def int_or_none(value: Any) -> int | None:
    return v2573.int_or_none(value)


def int32_or_none(value: Any) -> int | None:
    return v2573.int32_or_none(value)


def read_tolerant_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        fixed = HEX_LITERAL_RE.sub(lambda m: f"{m.group(1)}{int(m.group(2), 16)}{m.group(3)}", line)
        try:
            item = json.loads(fixed)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def build_v2692_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    build_args = argparse.Namespace(
        build=True,
        write_report=False,
        build_root=args.v2692_build_root,
        manifest=args.v2692_manifest_path,
        report=v2692.DEFAULT_REPORT,
        clang=v2692.v2674.v2659.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang",
        lld=v2692.v2674.v2659.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld",
        readelf=args.readelf,
        file=args.file,
    )
    payload = v2692.make_payload(build_args)
    args.v2692_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.v2692_manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def read_v2692_manifest(path: Path) -> dict[str, Any]:
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
    get_commands = {int(k): v for k, v in (contract.get("get_commands") or {}).items()}
    ptrtarget_contract_ok = bool(
        payload.get("ok")
        and helper.get("ok")
        and preload.get("ok")
        and sources.get("required_ok")
        and sources.get("prohibited_ok")
        and contract.get("target_cal_types") == [24, 10, 14]
        and get_commands == v2692.TARGET_GET_COMMANDS
        and required.get("preinit_writes_block_snapshot")
        and required.get("preinit_snapshot_before_get")
        and required.get("tap_declares_lower_custom_cmds")
        and required.get("tap_reads_proc_self_maps")
        and required.get("tap_maps_verifies_before_copy")
        and required.get("tap_logs_ptrtarget_status")
        and required.get("tap_dumps_ptrtarget_pre")
        and required.get("tap_ptrtarget_before_real_ioctl")
        and required.get("ioctl_still_fakes_audio_set")
        and not prohibited.get("helper_opens_msm_audio_cal")
        and not prohibited.get("preinit_opens_msm_audio_cal")
        and not prohibited.get("tap_opens_msm_audio_cal")
        and not prohibited.get("combined_native_speaker_write")
        and not prohibited.get("combined_persistent_magisk_install")
    )
    return {
        "ok": bool(payload.get("ok") and helper.get("ok") and preload.get("ok")),
        "path": rel(path),
        "manifest": payload,
        "helper": helper,
        "preload": preload,
        "ptrtarget_contract_ok": ptrtarget_contract_ok,
        "capture_contract": contract,
    }


def selected_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    if args.build_v2692_artifacts:
        build_v2692_artifacts(args)
    manifest = read_v2692_manifest(args.v2692_manifest_path)
    helper = v2573.artifact_from_manifest(manifest.get("helper", {}), args.helper_path, args.helper_sha256)
    preload = v2573.artifact_from_manifest(manifest.get("preload", {}), args.preload_path, args.preload_sha256)
    return {
        "manifest": manifest,
        "helper": helper,
        "preload": preload,
        "ok": bool(manifest.get("ok") and manifest.get("ptrtarget_contract_ok") and helper.get("ok") and preload.get("ok")),
    }


def to_v2490_args(args: argparse.Namespace, artifacts: dict[str, Any]) -> argparse.Namespace:
    return v2675.to_v2490_args(args, artifacts)


def select_pulled_dir_from_result(result: dict[str, Any]) -> Path | None:
    return v2675.select_pulled_dir_from_result(result)


def summarize_no_pulled_artifacts(result: dict[str, Any]) -> dict[str, Any]:
    base = v2675.summarize_no_pulled_artifacts(result)
    base["classification"] = str(base.get("classification", "v2693-no-pulled-artifacts")).replace("v2675", "v2693", 1)
    return base


def _cmd_to_cal_type(cmd: Any) -> int | None:
    value = int_or_none(cmd)
    if value is None:
        return None
    return TARGET_CMDS.get(value)


def _raw_status_for_row(acdbtap_dir: Path, row: dict[str, Any]) -> dict[str, Any]:
    raw_path = row.get("raw_path")
    out_len = int_or_none(row.get("out_len"))
    sha = str(row.get("sha256") or "")
    if not raw_path:
        return {"ok": False, "reason": "missing-raw-path"}
    local = acdbtap_dir / Path(str(raw_path)).name
    if not local.exists():
        return {"ok": False, "reason": "missing-raw-file", "local": rel(local)}
    data = local.read_bytes()
    import hashlib

    actual_sha = hashlib.sha256(data).hexdigest()
    return {
        "ok": (out_len is None or len(data) == out_len) and (not sha or actual_sha == sha),
        "reason": "ok",
        "local": rel(local),
        "len": len(data),
        "sha256": actual_sha,
        "size_matches": out_len is None or len(data) == out_len,
        "sha_matches": not sha or actual_sha == sha,
        "all_zero": all(byte == 0 for byte in data),
    }


def summarize_ptrtarget_capture(artifact_dir: Path) -> dict[str, Any]:
    setcal_summary = v2675.summarize_setcal_capture(artifact_dir)
    acdbtap_dir = artifact_dir / "acdbtap"
    if not (acdbtap_dir / "acdbtap-events.jsonl").exists() and (artifact_dir / "acdbtap-events.jsonl").exists():
        acdbtap_dir = artifact_dir
    acdbtap_events = acdbtap_dir / "acdbtap-events.jsonl"
    lower_events = artifact_dir / "acdb-v2674-lower-hidden-inhook-events.jsonl"
    tap_rows = read_tolerant_jsonl(acdbtap_events)
    lower_rows = read_tolerant_jsonl(lower_events)

    status_rows = [row for row in tap_rows if row.get("event") == "ptrtarget_status"]
    ptr_rows = [row for row in tap_rows if row.get("buffer") == "ptrtarget-pre"]
    block_rows = [row for row in lower_rows if row.get("event") == "v2692_lower_block_snapshot"]
    ptr_records: list[dict[str, Any]] = []
    for row in ptr_rows:
        status = next((item for item in status_rows if item.get("seq") == row.get("seq") and item.get("cmd") == row.get("cmd")), {})
        raw = _raw_status_for_row(acdbtap_dir, row)
        ptr_records.append(
            {
                "seq": int_or_none(row.get("seq")),
                "cmd": int_or_none(row.get("cmd")),
                "cal_type": _cmd_to_cal_type(row.get("cmd")),
                "in_len": int_or_none(row.get("in_len")),
                "out_len": int_or_none(row.get("out_len")),
                "sha256": row.get("sha256"),
                "raw_path": row.get("raw_path"),
                "raw_ok": bool(raw.get("ok")),
                "raw_len": raw.get("len"),
                "raw_sha256": raw.get("sha256"),
                "raw_all_zero": raw.get("all_zero"),
                "status": status.get("status"),
                "ptr": int_or_none(status.get("ptr")),
                "requested_len": int_or_none(status.get("requested_len")),
                "dump_len": int_or_none(status.get("dump_len")),
                "map_start": int_or_none(status.get("map_start")),
                "map_end": int_or_none(status.get("map_end")),
            }
        )
    mapped_cmds = sorted({_cmd_to_cal_type(row.get("cmd")) for row in status_rows if row.get("status") == "ptrtarget_maps_verified"} - {None})
    dumped_cmds = sorted({record.get("cal_type") for record in ptr_records if record.get("raw_ok")} - {None})
    missing_target_cal_types = sorted(TARGET_CAL_TYPES - set(dumped_cmds))
    has_any_ptrtarget_evidence = bool(status_rows or ptr_records or block_rows)
    if any(record.get("raw_ok") and record.get("cal_type") in TARGET_CAL_TYPES for record in ptr_records):
        classification = "v2693-ptrtarget-captured"
    elif status_rows:
        classification = "v2693-ptrtarget-status-only"
    elif block_rows:
        classification = "v2693-block-snapshot-no-ptrtarget"
    else:
        classification = f"v2693-{setcal_summary.get('classification', 'no-ptrtarget-evidence')}"
    return {
        "classification": classification,
        "success": classification == "v2693-ptrtarget-captured",
        "partial_success": bool(has_any_ptrtarget_evidence and classification != "v2693-ptrtarget-captured"),
        "operator_valuable": bool(has_any_ptrtarget_evidence or setcal_summary.get("operator_valuable")),
        "counts_toward_fails_twice": False if has_any_ptrtarget_evidence else setcal_summary.get("counts_toward_fails_twice"),
        "artifact_dir": rel(artifact_dir),
        "acdbtap_event_path": rel(acdbtap_events) if acdbtap_events.exists() else None,
        "lower_event_path": rel(lower_events) if lower_events.exists() else None,
        "ptrtarget_status_count": len(status_rows),
        "ptrtarget_dump_count": len(ptr_records),
        "ptrtarget_maps_verified_cal_types": mapped_cmds,
        "ptrtarget_dumped_cal_types": dumped_cmds,
        "missing_target_cal_types": missing_target_cal_types,
        "block_snapshot_count": len(block_rows),
        "block_snapshot_cal_types": sorted({int_or_none(row.get("cal_type")) for row in block_rows} - {None}),
        "ptrtarget_records": ptr_records,
        "setcal_summary": setcal_summary,
    }


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    artifacts = selected_artifacts(args)
    base_args = to_v2490_args(args, artifacts) if artifacts.get("ok") else None
    base_payload = v2490.dry_run_payload(base_args) if base_args else {}
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2693-acdb-lower-ptrtarget-capture-live-runner-dry-run",
        "host_only": True,
        "device_action": "none",
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "v2692_artifacts": artifacts,
        "v2490_engine": {
            "run_id": "V2490",
            "decision": base_payload.get("decision"),
            "live_ready": base_payload.get("live_ready", False),
            "command_safety": base_payload.get("command_safety"),
            "commands": base_payload.get("commands", {}),
        },
        "capture_contract": {
            "send_path": "init_v3 -> common skip hook -> a90_arm_capture -> a90_run_lower_hidden_nodes -> block snapshots -> ptrtarget-pre -> fake SET",
            "ptrtarget": "lower custom GET in_word1 is maps-verified and dumped privately before real acdb_ioctl",
            "block_snapshot": "v2692_lower_block_snapshot before each lower GET",
            "target_cal_types": sorted(TARGET_CAL_TYPES),
            "target_cmds": {str(cmd): cal for cmd, cal in TARGET_CMDS.items()},
            "native_replay": "blocked; no SET replay in this runner",
            "raw_private_only": True,
        },
    }
    payload["live_ready"] = bool(artifacts.get("ok") and base_payload.get("live_ready"))
    payload["live_blockers"] = []
    if not artifacts.get("ok"):
        payload["live_blockers"].append("V2692 pointer-target helper/preload artifacts are not ready")
    payload["live_blockers"].extend(base_payload.get("live_blockers", []))
    payload["command_safety"] = base_payload.get("command_safety", {"ok": False, "findings": ["base payload missing"]})
    payload["ok"] = bool(payload["live_ready"] and payload["command_safety"].get("ok"))
    return payload


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    if args.out_dir is None:
        args.out_dir = default_live_out_dir()
    dry = dry_run_payload(args)
    if not dry.get("ok"):
        raise RuntimeError(f"V2693 live inputs are not ready: {dry.get('live_blockers')}")
    artifacts = dry["v2692_artifacts"]
    base_args = to_v2490_args(args, artifacts)
    result = v2490.run_live(base_args)
    pulled_dir = select_pulled_dir_from_result(result)
    summary = summarize_ptrtarget_capture(pulled_dir) if pulled_dir else summarize_no_pulled_artifacts(result)
    wrapper = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{summary['classification']}-rollback-{'pass' if result.get('rolled_back') else 'unknown'}",
        "out_dir": result.get("out_dir"),
        "rolled_back": bool(result.get("rolled_back")),
        "counts_toward_fails_twice": summary.get("counts_toward_fails_twice", result.get("counts_toward_fails_twice")),
        "operator_valuable": bool(summary.get("operator_valuable")),
        "partial_success": bool(summary.get("partial_success")),
        "success": bool(summary.get("success")),
        "v2692_artifacts": artifacts,
        "v2490_engine_result": result,
        "ptrtarget_summary": summary,
        "ok": bool(result.get("rolled_back") and summary.get("operator_valuable")),
    }
    out_dir_raw = result.get("out_dir")
    if out_dir_raw:
        write_json(ROOT / str(out_dir_raw) / "v2693-result.json", wrapper)
    return wrapper


def write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("ptrtarget_summary", {})
    artifacts = payload.get("v2692_artifacts", {})
    helper = artifacts.get("helper", {})
    preload = artifacts.get("preload", {})
    lines = [
        "# NATIVE_INIT V2693 — ACDB lower pointer-target capture live handoff",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Android own-process ACDB pointer-target capture using the V2490 checked Android",
        "boot/stage/pull/rollback engine and the V2692 helper/preload artifacts. This is",
        "measurement-only: the SET shim fake-successes `AUDIO_SET_CALIBRATION`, no native replay",
        "runs, no speaker write occurs, and raw pointer-target bytes remain private.",
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
        f"- ptrtarget_status_count: `{summary.get('ptrtarget_status_count')}`",
        f"- ptrtarget_dump_count: `{summary.get('ptrtarget_dump_count')}`",
        f"- ptrtarget_maps_verified_cal_types: `{summary.get('ptrtarget_maps_verified_cal_types')}`",
        f"- ptrtarget_dumped_cal_types: `{summary.get('ptrtarget_dumped_cal_types')}`",
        f"- missing_target_cal_types: `{summary.get('missing_target_cal_types')}`",
        f"- block_snapshot_count: `{summary.get('block_snapshot_count')}`",
        f"- block_snapshot_cal_types: `{summary.get('block_snapshot_cal_types')}`",
        "",
        "## Pointer Target Records (metadata only)",
        "",
        "| seq | cal_type | cmd | requested_len | dump_len | status | raw_ok | raw_len | raw_sha256 |",
        "| ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |",
    ]
    for row in summary.get("ptrtarget_records", []) or []:
        lines.append(
            f"| {row.get('seq')} | {row.get('cal_type')} | {row.get('cmd')} | "
            f"{row.get('requested_len')} | {row.get('dump_len')} | `{row.get('status')}` | "
            f"`{row.get('raw_ok')}` | {row.get('raw_len')} | `{row.get('raw_sha256')}` |"
        )
    if not summary.get("ptrtarget_records"):
        lines.append("| - | - | - | - | - | - | - | - | - |")
    lines.extend([
        "",
        "Raw `ptrtarget-pre` bytes are not committed. Public output records only length, status, and SHA-256.",
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
        "- stages the V2692 helper/preload through the V2490 Android-good handoff engine;",
        "- forces `A90_ACDB_FAKE_ALLOCATE=1`; the SET shim always fake-successes and any real",
        "  kernel `AUDIO_SET_CALIBRATION` pass-through is a boundary violation;",
        "- emits `v2692_lower_block_snapshot` before each lower hidden-node GET;",
        "- emits `ptrtarget_status` and private `ptrtarget-pre` raw dumps only after `/proc/self/maps`",
        "  verifies the requested same-process pointer range;",
        "- pulls `/data/local/tmp/a90-acdb-ownget/` and nested `acdbtap/` privately; and",
        "- classifies success when at least one target cal_type pointer target is dumped with valid raw SHA.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_lower_ptrtarget_capture_live_handoff_v2693.py tests/test_native_audio_acdb_lower_ptrtarget_capture_live_handoff_v2693.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_lower_ptrtarget_capture_live_handoff_v2693 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_lower_ptrtarget_capture_live_handoff_v2693.py --dry-run --write-report`",
        "- live run, if present: `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_lower_ptrtarget_capture_live_handoff_v2693.py --run-live --write-report`",
        "- if live run is present, post-live rollback must verify `a90ctl.py version` reports `0.9.285` / `v2321-usb-clean-identity-rodata` and `a90ctl.py selftest verbose` reports `fail=0`",
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
    parser.add_argument("--build-v2692-artifacts", action="store_true")
    parser.add_argument("--v2692-build-root", type=Path, default=v2692.DEFAULT_BUILD_ROOT)
    parser.add_argument("--v2692-manifest-path", type=Path, default=v2692.DEFAULT_MANIFEST)
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
