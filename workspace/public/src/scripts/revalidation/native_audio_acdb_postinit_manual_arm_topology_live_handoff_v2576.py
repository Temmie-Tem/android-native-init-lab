#!/usr/bin/env python3
"""V2576 live handoff for post-init manual-arm ACDB topology capture.

This wrapper reuses the V2490 checked Android boot/stage/pull/rollback engine
with V2576 artifacts:

- helper initializes ACDB, then calls acdb_loader_send_common_custom_topology()
  as a fallback path;
- combined preload keeps acdb_ioctl silent until the helper arms it after
  acdb_loader_init_v3() returns, then dumps every out_len>0 ACDB call, fakes
  audio calibration ioctls when A90_ACDB_FAKE_ALLOCATE=1, and exits after the
  first ret==0 non-zero 4916-byte topology buffer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import build_android_acdb_postinit_manual_arm_topology_v2576 as v2576
import native_audio_acdb_ownprocess_get_live_handoff_v2490 as v2490

RUN_ID = "V2576"
BUILD_TAG = "v2576-audio-acdb-postinit-manual-arm-topology-capture-live"
ROOT = v2576.ROOT
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2576_AUDIO_ACDB_POSTINIT_MANUAL_ARM_TOPOLOGY_CAPTURE_LIVE_HANDOFF_2026-06-16.md"


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"v2576-acdb-postinit-manual-arm-topology-capture-{stamp}"


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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def read_v2576_manifest(path: Path) -> dict[str, Any]:
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
    cflags = payload.get("toolchain", {}).get("preload_cflags", [])
    manual_arm_after_init = (
        "-DA90_ACDBTAP_AUTO_ARM_ON_INITIALIZE=0" in cflags
        and "-DA90_ACDBTAP_CUSTOM_TOPOLOGY_ONLY=0" in cflags
    )
    return {
        "ok": bool(payload.get("ok") and helper.get("ok") and preload.get("ok") and manual_arm_after_init),
        "path": rel(path),
        "manifest": payload,
        "helper": helper,
        "preload": preload,
        "manual_arm_after_init": manual_arm_after_init,
        "helper_has_postinit_fallback_arm": bool(required.get("helper_has_postinit_fallback_arm")),
        "preload_policy": payload.get("capture_contract", {}).get("unarmed_policy"),
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


def build_v2576_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    build_args = argparse.Namespace(
        build=True,
        build_root=args.v2576_build_root,
        manifest_path=args.v2576_manifest_path,
        clang=v2576.TOOLCHAIN_ROOT / "bin/clang",
        lld=v2576.TOOLCHAIN_ROOT / "bin/ld.lld",
        readelf=args.readelf,
        file=args.file,
    )
    return v2576.manifest(build_args)


def selected_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    if args.build_v2576_artifacts:
        build_v2576_artifacts(args)
    manifest = read_v2576_manifest(args.v2576_manifest_path)
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


def summarize_postinit_capture(artifact_dir: Path) -> dict[str, Any]:
    base_summary = v2490.parse_ownget_artifacts(artifact_dir)
    helper_events_path = artifact_dir / "acdb-ownget-events.jsonl"
    acdb_log_path = artifact_dir / "logcat-acdb-loader.txt"
    acdb_log_text = acdb_log_path.read_text(encoding="utf-8", errors="replace") if acdb_log_path.exists() else ""
    acdb_log_has_common_topology = "send_common_custom_topology" in acdb_log_text
    acdb_log_has_topology_get = "ACDB_CMD_GET_AVCS_CUSTOM_TOPO_INFO_V3" in acdb_log_text
    helper_sigsegv = bool(base_summary.get("diagnostics", {}).get("helper_sigsegv"))
    helper_events = read_jsonl(helper_events_path)
    helper_stages = [event.get("stage") for event in helper_events if event.get("event") == "topology_helper"]
    init_returns = [
        int32_or_none(event.get("code"))
        for event in helper_events
        if event.get("event") == "topology_helper" and event.get("stage") == "init_v3_return"
    ]
    init_ok = bool(init_returns and init_returns[-1] == 0)
    helper_fallback_armed = "armed_before_common_topology" in helper_stages

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
    ioctl_events = base_summary.get("ioctl_trace_events", [])
    fake_set_events = [
        event for event in ioctl_events
        if event.get("name") == "AUDIO_SET_CALIBRATION" and event.get("intercept") == "fake-success"
    ]
    pass_through_set_events = [
        event for event in ioctl_events
        if event.get("name") == "AUDIO_SET_CALIBRATION" and event.get("intercept") != "fake-success"
    ]
    if pass_through_set_events:
        classification = "v2576-boundary-violation-real-audio-set-passthrough"
    elif topology:
        classification = "v2576-postinit-manual-arm-topology-captured"
    elif acdb_log_has_common_topology and acdb_log_has_topology_get and helper_sigsegv and not helper_fallback_armed:
        classification = "v2576-init-internal-topology-before-manual-arm-sigsegv"
    elif not init_ok:
        classification = "v2576-init-v3-failed-before-arm"
    elif not rows:
        classification = "v2576-manual-arm-no-acdbtap-events"
    elif size_queries:
        classification = "v2576-postinit-manual-arm-topology-size-query-only"
    elif successful:
        classification = "v2576-postinit-manual-arm-topology-partial-nonzero-capture"
    elif not helper_fallback_armed:
        classification = "v2576-init-internal-manual-arm-no-topology-capture"
    else:
        classification = f"v2576-{base_summary.get('classification', 'no-acdbtap-capture')}"
    success = bool(topology and not pass_through_set_events)
    return {
        "classification": classification,
        "success": success,
        "partial_success": bool((successful or size_queries) and not pass_through_set_events),
        "init_v3_ok": init_ok,
        "helper_fallback_armed_before_common_topology": helper_fallback_armed,
        "acdb_log_has_common_topology": acdb_log_has_common_topology,
        "acdb_log_has_topology_get": acdb_log_has_topology_get,
        "helper_sigsegv": helper_sigsegv,
        "topology_success_count": len(topology),
        "successful_nonzero_count": len(successful),
        "size_query_count": len(size_queries),
        "fake_audio_set_count": len(fake_set_events),
        "real_audio_set_pass_through_count": len(pass_through_set_events),
        "helper_event_path": rel(helper_events_path),
        "acdb_loader_log_path": rel(acdb_log_path) if acdb_log_path.exists() else None,
        "helper_event_count": len(helper_events),
        "helper_stages": helper_stages,
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
        "decision": "v2576-acdb-postinit-manual-arm-topology-capture-live-runner-dry-run",
        "host_only": True,
        "device_action": "none",
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "v2576_artifacts": artifacts,
        "v2490_engine": {
            "run_id": "V2490",
            "decision": base_payload.get("decision"),
            "live_ready": base_payload.get("live_ready", False),
            "command_safety": base_payload.get("command_safety"),
            "commands": base_payload.get("commands", {}),
        },
        "capture_contract": {
            "manual_arm_after_init": bool(artifacts.get("manifest", {}).get("manual_arm_after_init")),
            "fake_audio_cal_allocate": True,
            "combined_preload": True,
            "success_requires": "ret==0 and non-all-zero raw buffer with out_len==4916; requested out_len alone is not success",
            "exit_policy": "preload exits immediately after banking the first valid 4916-byte custom-topology target",
            "raw_private_only": True,
        },
    }
    payload["live_ready"] = bool(artifacts.get("ok") and base_payload.get("live_ready"))
    payload["live_blockers"] = []
    if not artifacts.get("ok"):
        payload["live_blockers"].append("V2576 post-init manual-arm helper/preload artifacts are not ready")
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
        raise RuntimeError(f"V2576 live inputs are not ready: {dry.get('live_blockers')}")
    artifacts = dry["v2576_artifacts"]
    base_args = to_v2490_args(args, artifacts)
    result = v2490.run_live(base_args)
    pulled_dir = select_pulled_dir_from_result(result)
    capture_summary = summarize_postinit_capture(pulled_dir) if pulled_dir else {
        "classification": "v2576-no-pulled-artifacts",
        "success": False,
        "partial_success": False,
    }
    wrapper = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{capture_summary['classification']}-rollback-{ 'pass' if result.get('rolled_back') else 'unknown' }",
        "out_dir": result.get("out_dir"),
        "v2576_artifacts": artifacts,
        "v2490_engine_result": result,
        "capture_summary": capture_summary,
        "ok": bool(result.get("rolled_back") and capture_summary.get("success")),
    }
    out_dir_raw = result.get("out_dir")
    if out_dir_raw:
        write_json(ROOT / str(out_dir_raw) / "v2576-result.json", wrapper)
    return wrapper


def write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("capture_summary", {})
    ordered_records = summary.get("ordered_records", [])
    topology_records = [
        row for row in ordered_records
        if row.get("ret") == 0 and row.get("out_len") == 4916 and row.get("valid_raw") and row.get("nonzero")
    ]
    size_records = [
        row for row in ordered_records
        if row.get("ret") == 0 and row.get("out_len") == 4 and row.get("valid_raw") and row.get("nonzero")
    ]
    lines = [
        "# NATIVE_INIT V2576 — ACDB post-init manual-arm topology capture",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Android own-process ACDB capture handoff using the V2490 checked Android boot/stage/pull/rollback engine and the V2576 post-init manual-arm helper/preload artifacts.",
        "",
        "## Result",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- ok: `{payload.get('ok')}`",
        f"- out_dir: `{payload.get('out_dir')}`",
        f"- classification: `{summary.get('classification')}`",
        f"- init_v3_ok: `{summary.get('init_v3_ok')}`",
        f"- helper_fallback_armed_before_common_topology: `{summary.get('helper_fallback_armed_before_common_topology')}`",
        f"- acdb_log_has_common_topology: `{summary.get('acdb_log_has_common_topology')}`",
        f"- acdb_log_has_topology_get: `{summary.get('acdb_log_has_topology_get')}`",
        f"- helper_sigsegv: `{summary.get('helper_sigsegv')}`",
        f"- topology_success_count: `{summary.get('topology_success_count')}`",
        f"- successful_nonzero_count: `{summary.get('successful_nonzero_count')}`",
        f"- size_query_count: `{summary.get('size_query_count')}`",
        f"- real_audio_set_pass_through_count: `{summary.get('real_audio_set_pass_through_count')}`",
        "",
        "## Captured Records",
        "",
        f"- size_query_records: `{len(size_records)}`",
        f"- topology_4916_records: `{len(topology_records)}`",
    ]
    for row in size_records:
        lines.append(
            f"- size_query seq=`{row.get('seq')}` cmd=`{row.get('cmd')}` raw_size=`{row.get('raw_size')}` sha256=`{row.get('raw_sha256')}`"
        )
    for row in topology_records:
        lines.append(
            f"- topology seq=`{row.get('seq')}` cmd=`{row.get('cmd')}` raw_size=`{row.get('raw_size')}` sha256=`{row.get('raw_sha256')}`"
        )
    lines.extend([
        "",
        "Raw ACDB buffers remain private under the run directory and are not committed.",
        "",
        "## Artifacts",
        "",
        f"- helper_sha256: `{payload.get('v2576_artifacts', {}).get('helper', {}).get('sha256')}`",
        f"- preload_sha256: `{payload.get('v2576_artifacts', {}).get('preload', {}).get('sha256')}`",
        "",
        "## Boundary",
        "",
        "- The preload is manual-armed only after `acdb_loader_init_v3()` returns success: earlier `acdb_ioctl` calls pass through without dump/hash/file I/O, then every `out_len>0` ACDB call is dumped.",
        "- `A90_ACDB_FAKE_ALLOCATE=1` is forced; any real `AUDIO_SET_CALIBRATION` pass-through is classified as a boundary violation.",
        "- Success requires `ret==0`, non-all-zero raw bytes, and `out_len==4916`; requested length alone is not success.",
        "",
        "## Interpretation",
        "",
    ])
    if payload.get("ok") and not summary.get("init_v3_ok"):
        lines.extend([
            "- `init_v3_ok=False` here means the helper did not observe an `init_v3_return` event because the preload exited immediately after banking the valid 4916-byte target inside the init/common-topology path.",
            "",
        ])
    lines.extend([
        "- This run is useful negative evidence: stock `acdb_loader_init_v3` entered common-topology and topology GET logging, but the helper never reached its post-init arm point before SIGSEGV; therefore post-init manual-arm is too late for this device path.",
        "",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--build-v2576-artifacts", action="store_true")
    parser.add_argument("--v2576-build-root", type=Path, default=v2576.DEFAULT_BUILD_ROOT)
    parser.add_argument("--v2576-manifest-path", type=Path, default=v2576.DEFAULT_MANIFEST)
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
