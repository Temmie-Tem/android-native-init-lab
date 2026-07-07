#!/usr/bin/env python3
"""Host-only postmortem for the S22+ ramoops-DTBO + M18 capture run.

This script reads committed source plus private run artifacts. It does not use
ADB, Odin, reboot, flash, or touch a connected device.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RUN_DIR = Path("workspace/private/runs/s22plus_ramoops_dtbo_m18_capture_20260707T164400Z")
DEFAULT_M18_MANIFEST = Path(
    "workspace/private/outputs/s22plus_native_init/inplace_m18_full_firststage_usb_v0_1/manifest.json"
)
DEFAULT_M18_SOURCE = Path("workspace/public/src/native-init/s22plus_init_usb_acm_m18_full_firststage_park.c")
DEFAULT_LIVE_LOG_NAME = "s22plus_ramoops_dtbo_m18_capture_live_gate.txt"
DEFAULT_LAST_KMSG = Path("android_pstore/post_m18_boot_rollback_last_kmsg.bin")

M18_MARKERS = [
    "S22_NATIVE_INIT_USB_ACM_M18_FULL",
    "S22M18FULL0001",
    "module_group=full_firststage_usb",
    "full_firststage_usb",
]

ABL_MARKERS = [
    "bootloader_mode = 1",
    "reboot_reason = 0x9",
    "Failed to get KlogOffset",
    "SamsungLogFlush KlogOffset:0x0",
]

REQUIRED_LOG_FLAGS = [
    "dtbo_candidate_odin_rc=0",
    "patched_dtbo_android_ok=",
    "m18_candidate_odin_rc=0",
    "m18_odin_seen=1",
    "magisk_boot_rollback_odin_rc=0",
    "post_m18_boot_rollback_pstore_files=[]",
    "post_m18_boot_rollback_pstore_marker_found=0",
    "post_m18_boot_rollback_last_kmsg_rc=0",
    "post_m18_boot_rollback_last_kmsg_marker_found=0",
    "m18_capture_pstore_marker_found=0",
    "stock_dtbo_rollback_after_capture_odin_rc=0",
    "final_android_after_stock_dtbo=",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def count_text(haystack: str, needles: list[str]) -> dict[str, int]:
    return {needle: haystack.count(needle) for needle in needles}


def parse_log(log_text: str) -> dict[str, Any]:
    observe_iterations = sorted(
        {
            int(match.group(1))
            for match in re.finditer(r"m18_capture_observe_(\d{3})", log_text)
        }
    )
    observed_acm_empty = len(re.findall(r"m18_capture_observe_\d{3}_acm_devices=\[\]", log_text))
    last_kmsg_match = re.search(r"post_m18_boot_rollback_last_kmsg_bytes=(\d+)", log_text)
    return {
        "required_flags": {flag: flag in log_text for flag in REQUIRED_LOG_FLAGS},
        "all_required_flags_present": all(flag in log_text for flag in REQUIRED_LOG_FLAGS),
        "observe_iteration_count": len(observe_iterations),
        "observe_first": observe_iterations[0] if observe_iterations else None,
        "observe_last": observe_iterations[-1] if observe_iterations else None,
        "observed_acm_empty_count": observed_acm_empty,
        "m18_odin_seen": "m18_odin_seen=1" in log_text,
        "last_kmsg_bytes_logged": int(last_kmsg_match.group(1)) if last_kmsg_match else None,
    }


def analyze_m18_source(source_text: str) -> dict[str, Any]:
    main_match = re.search(r"static void M18_FULL_main\(void\) \{(?P<body>.*?)\n\}", source_text, re.S)
    if not main_match:
        raise SystemExit("M18_FULL_main not found")
    body = main_match.group("body")
    ordered_calls = [
        "setup_minimal_fs();",
        "emit(k_marker);",
        "load_full_firststage_usb_modules();",
        "force_usb_roles_device();",
        "(void)create_acm_gadget();",
        "serial_probe_loop();",
    ]
    positions = {call: body.find(call) for call in ordered_calls}
    missing = [call for call, pos in positions.items() if pos < 0]
    if missing:
        raise SystemExit(f"M18_FULL_main missing expected calls: {missing}")
    call_order_ok = list(positions.values()) == sorted(positions.values())
    return {
        "main_call_order": ordered_calls,
        "main_call_order_ok": call_order_ok,
        "first_emit_phase": "S22_NATIVE_INIT_USB_ACM_M18_FULL phase=mounts",
        "version_marker_after_mounts": "emit(k_marker);" in body,
        "marker_output_path": "/dev/kmsg only",
        "retained_marker_absence_localizes_execution": False,
        "reason": "The first M18 emissions are /dev/kmsg writes, so missing retained markers do not prove pre-marker death.",
    }


def analyze_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    vendor = manifest.get("vendor_ramdisk", {}).get("m18_full_firststage_usb", {})
    missing = vendor.get("non_reset_missing_tail_deps", {})
    if not isinstance(missing, dict):
        missing = {}
    missing_edges = sum(len(value) for value in missing.values() if isinstance(value, list))
    return {
        "subset_count": vendor.get("subset_count"),
        "usb_tail_count": vendor.get("usb_tail_count"),
        "non_reset_missing_tail_dep_module_count": len(missing),
        "non_reset_missing_tail_dep_edge_count": missing_edges,
        "non_reset_missing_tail_deps": missing,
        "m18_is_dependency_closed_usb_tail": len(missing) == 0,
    }


def analyze_last_kmsg(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    m18_counts = count_text(text, M18_MARKERS)
    abl_counts = count_text(text, ABL_MARKERS)
    return {
        "path": str(path),
        "bytes": len(data),
        "m18_marker_counts": m18_counts,
        "any_m18_marker": any(value > 0 for value in m18_counts.values()),
        "abl_marker_counts": abl_counts,
        "any_abl_download_marker": any(value > 0 for value in abl_counts.values()),
    }


def classify(log: dict[str, Any], source: dict[str, Any], manifest: dict[str, Any], last_kmsg: dict[str, Any]) -> dict[str, Any]:
    recovered_cleanly = bool(log["all_required_flags_present"])
    retained_channel_captured_m18 = bool(last_kmsg["any_m18_marker"])
    has_dependency_gap = not bool(manifest["m18_is_dependency_closed_usb_tail"])
    return {
        "device_recovered_cleanly": recovered_cleanly,
        "capture_channel_captured_m18_marker": retained_channel_captured_m18,
        "retained_channel_interpretation": (
            "dead-or-nonlocalizing-for-m18-printk"
            if not retained_channel_captured_m18 and source["retained_marker_absence_localizes_execution"] is False
            else "contains-m18-marker"
        ),
        "m18_failure_localized_to": "not-localized-with-retained-channel",
        "m18_dependency_closure_caveat": has_dependency_gap,
        "m18_dependency_closure_interpretation": (
            "M18 was not a fully dependency-closed USB tail; unresolved non-reset deps remain host-visible."
            if has_dependency_gap
            else "M18 USB tail manifest is dependency-closed under modules.dep."
        ),
        "recommended_next": (
            "Do not repeat the same M18 live. Prefer UART/kernel-console capture. "
            "If a no-UART fallback is pursued, design it host-only as a checkpoint/download "
            "discriminator or a dependency-closed USB-tail candidate, then require a fresh gate."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--m18-manifest", type=Path, default=DEFAULT_M18_MANIFEST)
    parser.add_argument("--m18-source", type=Path, default=DEFAULT_M18_SOURCE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    root = repo_root()
    run_dir = resolve(root, args.run_dir)
    log_path = run_dir / DEFAULT_LIVE_LOG_NAME
    last_kmsg_path = run_dir / DEFAULT_LAST_KMSG
    manifest_path = resolve(root, args.m18_manifest)
    source_path = resolve(root, args.m18_source)

    for path in (run_dir, log_path, last_kmsg_path, manifest_path, source_path):
        if not path.exists():
            raise SystemExit(f"required postmortem input missing: {path}")

    log = parse_log(read_text(log_path))
    source = analyze_m18_source(read_text(source_path))
    manifest = analyze_manifest(json.loads(read_text(manifest_path)))
    last_kmsg = analyze_last_kmsg(last_kmsg_path)
    classification = classify(log, source, manifest, last_kmsg)

    result = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purpose": "host-only S22+ M18 capture postmortem",
        "device_action": False,
        "inputs": {
            "run_dir": str(run_dir),
            "log": str(log_path),
            "last_kmsg": str(last_kmsg_path),
            "manifest": str(manifest_path),
            "source": str(source_path),
        },
        "live_log": log,
        "m18_source": source,
        "m18_manifest": manifest,
        "last_kmsg": last_kmsg,
        "classification": classification,
        "result": "pass" if log["all_required_flags_present"] else "warn",
    }
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        output_path = resolve(root, args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
