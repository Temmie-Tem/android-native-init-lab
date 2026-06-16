#!/usr/bin/env python3
"""V2592 Android handoff wrapper for V2591 corrected send_audio_cal_v5 artifacts.

Host-only by default.  Live mode reuses the V2490 Android boot/stage/pull/rollback
engine through the V2573 per-device indirect classifier, but selects the V2591
private helper/preload where send_audio_cal_v5 arg2 is RX cap mask 1 and stack args are corrected.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import build_android_acdb_perdevice_rx_capmask_argorder_v2591 as v2591
import native_audio_acdb_perdevice_indirect_capture_live_handoff_v2573 as v2573

ROOT = v2591.ROOT
RUN_ID = "V2592"
BUILD_TAG = "v2592-audio-acdb-perdevice-rx-capmask-argorder-live"
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2592_AUDIO_ACDB_PERDEVICE_RX_CAPMASK_ARGORDER_RUNNER_2026-06-16.md"
EXACT_GATE = (
    "AUD-ACDB-V2592-perdevice-rx-capmask-argorder go: one-shot send_audio_cal_v5 arg2=1 corrected-stack-order "
    "per-device capture on Android, fake allocate preload, no SET replay, no speaker write, "
    "rollback to V2321"
)


def rel(path: Path | str) -> str:
    return v2573.rel(path)


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"v2592-acdb-perdevice-rx-capmask-argorder-{stamp}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_v2591_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    build_args = argparse.Namespace(
        build=True,
        build_root=args.v2591_build_root,
        readelf=args.readelf,
        file=args.file,
        clang=args.clang,
        lld=args.lld,
    )
    payload = v2591.make_payload(build_args)
    args.v2591_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.v2591_manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def read_v2591_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "error": f"manifest missing: {rel(path)}"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {"ok": False, "error": f"manifest json error: {error}"}
    artifacts = payload.get("build", {}).get("artifacts", {})
    helper = artifacts.get("helper", {})
    preload = artifacts.get("preload", {})
    contract = payload.get("capture_contract", {})
    sources = payload.get("sources", {})
    return {
        "ok": bool(payload.get("ok") and helper.get("ok") and preload.get("ok")),
        "path": rel(path),
        "manifest": payload,
        "helper": helper,
        "preload": preload,
        "corrected_arg_order_contract": str(contract.get("per_device_call", ""))
        == "acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)",
        "source_overrides_ok": bool(
            sources.get("required", {}).get("preinit_rx_path_compile_override_guard")
            and sources.get("required", {}).get("preinit_fixed_stack_order_compile_override_guard")
        ),
        "capture_contract": contract,
    }


def selected_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    if args.build_v2591_artifacts:
        build_v2591_artifacts(args)
    manifest = read_v2591_manifest(args.v2591_manifest_path)
    helper = v2573.artifact_from_manifest(manifest.get("helper", {}), args.helper_path, args.helper_sha256)
    preload = v2573.artifact_from_manifest(manifest.get("preload", {}), args.preload_path, args.preload_sha256)
    return {
        "manifest": manifest,
        "helper": helper,
        "preload": preload,
        "ok": bool(
            manifest.get("ok")
            and manifest.get("corrected_arg_order_contract")
            and manifest.get("source_overrides_ok")
            and helper.get("ok")
            and preload.get("ok")
        ),
    }


def to_v2490_args(args: argparse.Namespace, artifacts: dict[str, Any]) -> argparse.Namespace:
    return v2573.to_v2490_args(args, artifacts)


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    artifacts = selected_artifacts(args)
    base_args = to_v2490_args(args, artifacts) if artifacts.get("ok") else None
    base_payload = v2573.v2490.dry_run_payload(base_args) if base_args else {}
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2592-acdb-perdevice-rx-capmask-argorder-live-runner-dry-run",
        "host_only": True,
        "device_action": "none",
        "exact_live_gate": EXACT_GATE,
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "v2591_artifacts": artifacts,
        "v2490_engine": {
            "run_id": "V2490",
            "decision": base_payload.get("decision"),
            "live_ready": base_payload.get("live_ready", False),
            "command_safety": base_payload.get("command_safety"),
            "commands": base_payload.get("commands", {}),
        },
        "capture_contract": {
            "send_audio_cal_v5_arg2": 1,
            "send_audio_cal_v5_stack_args_5_6_7": [0, 48000, 1],
            "per_device_call": "acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)",
            "reuses_v2573_classifier": True,
            "fake_audio_cal_allocate": True,
            "combined_preload": True,
            "success_requires": "ret==0 and non-all-zero raw buffer; requested out_len alone is not success",
            "raw_private_only": True,
            "native_replay_blocked": True,
        },
    }
    payload["live_ready"] = bool(artifacts.get("ok") and base_payload.get("live_ready"))
    payload["live_blockers"] = []
    if not artifacts.get("ok"):
        payload["live_blockers"].append("V2591 arg2=1 corrected-order helper/preload artifacts are not ready")
    payload["live_blockers"].extend(base_payload.get("live_blockers", []))
    payload["command_safety"] = base_payload.get("command_safety", {"ok": False, "findings": ["base payload missing"]})
    payload["ok"] = bool(payload["live_ready"] and payload["command_safety"].get("ok"))
    return payload


def select_pulled_dir_from_result(result: dict[str, Any]) -> Path | None:
    return v2573.select_pulled_dir_from_result(result)


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    if args.exact_gate != EXACT_GATE:
        raise RuntimeError("exact V2592 live gate mismatch")
    if args.out_dir is None:
        args.out_dir = default_live_out_dir()
    dry = dry_run_payload(args)
    if not dry.get("ok"):
        raise RuntimeError(f"V2592 live inputs are not ready: {dry.get('live_blockers')}")
    artifacts = dry["v2591_artifacts"]
    base_args = to_v2490_args(args, artifacts)
    result = v2573.v2490.run_live(base_args)
    pulled_dir = select_pulled_dir_from_result(result)
    per_device_summary = v2573.summarize_perdevice_indirect_capture(pulled_dir) if pulled_dir else {
        "classification": "v2592-no-pulled-artifacts",
        "full_success": False,
        "per_device_success": False,
        "partial_success": False,
    }
    classification = str(per_device_summary.get("classification", "unknown")).replace("v2573-", "v2592-")
    wrapper = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{classification}-rollback-{'pass' if result.get('rolled_back') else 'unknown'}",
        "out_dir": result.get("out_dir"),
        "v2591_artifacts": artifacts,
        "v2490_engine_result": result,
        "perdevice_rx_capmask_summary": per_device_summary,
        "ok": bool(result.get("rolled_back") and (per_device_summary.get("full_success") or per_device_summary.get("partial_success"))),
    }
    out_dir_raw = result.get("out_dir")
    if out_dir_raw:
        write_json(ROOT / str(out_dir_raw) / "v2592-result.json", wrapper)
    return wrapper


def write_report(path: Path, payload: dict[str, Any]) -> None:
    artifacts = payload.get("v2591_artifacts", {})
    helper = artifacts.get("helper", {})
    preload = artifacts.get("preload", {})
    lines = [
        "# NATIVE_INIT V2592 — ACDB per-device RX cap-mask runner",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Host-only runner unit after V2591. No live Android handoff, native replay SET, speaker write,",
        "or raw ACDB payload publication was performed in this iteration.",
        "",
        "## Decision",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- ok: `{payload.get('ok')}`",
        f"- live_ready: `{payload.get('live_ready')}`",
        f"- live_blockers: `{payload.get('live_blockers')}`",
        "",
        "## Runner Contract",
        "",
        f"- exact live gate: `{EXACT_GATE}`",
        "- stages the V2591 helper/preload artifacts where `send_audio_cal_v5` arg2 is `1` and stack args are `(0, 48000, 1)`.",
        "- reuses V2573 generic direct/indirect ACDB tap classification.",
        "- forces `A90_ACDB_FAKE_ALLOCATE=1`; native replay SET and speaker playback remain blocked.",
        "- success requires `ret==0` and non-all-zero raw payload; requested length alone is not success.",
        "",
        "## Artifacts",
        "",
        f"- helper_sha256: `{helper.get('sha256')}`",
        f"- preload_sha256: `{preload.get('sha256')}`",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_perdevice_rx_capmask_argorder_live_handoff_v2592.py tests/test_native_audio_acdb_perdevice_rx_capmask_argorder_live_handoff_v2592.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_perdevice_rx_capmask_argorder_live_handoff_v2592`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_perdevice_rx_capmask_argorder_live_handoff_v2592.py --build-v2591-artifacts --write-report`",
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
    parser.add_argument("--exact-gate")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--build-v2591-artifacts", action="store_true")
    parser.add_argument("--v2591-build-root", type=Path, default=v2591.DEFAULT_BUILD_ROOT)
    parser.add_argument("--v2591-manifest-path", type=Path, default=v2591.DEFAULT_MANIFEST)
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
    parser.add_argument("--android-root-recheck-attempts", type=int, default=v2573.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS)
    parser.add_argument("--android-root-recheck-sleep-sec", type=float, default=v2573.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC)
    parser.add_argument("--android-settle-adb-retry-attempts", type=int, default=v2573.v2490.DEFAULT_SETTLE_ADB_RETRY_ATTEMPTS)
    parser.add_argument("--android-settle-adb-retry-sleep-sec", type=float, default=v2573.v2490.DEFAULT_SETTLE_ADB_RETRY_SLEEP_SEC)
    parser.add_argument("--clang", type=Path, default=v2591.v2572.TOOLCHAIN_ROOT / "bin/clang")
    parser.add_argument("--lld", type=Path, default=v2591.v2572.TOOLCHAIN_ROOT / "bin/ld.lld")
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
