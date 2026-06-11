#!/usr/bin/env python3
"""Compile the V2223 approved boot-window capture plan.

This is a host-only planner. It consumes the latest V2222 preflight contract,
checks that the helper/source route still exists, records current baseline boot
images, and emits an execution plan for the next approved boot-window capture.
It does not flash, reboot, run device commands, or mutate tracefs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
BOOT_INPUTS = REPO_ROOT / "workspace/private/inputs/boot_images"
HELPER_SOURCE = REPO_ROOT / "workspace/public/src/native-init/helpers/a90_android_execns_probe.c"

REQUIRED_SOURCE_MARKERS = {
    "mode": "wifi-companion-wlan-pd-cnss-output-visibility-start-only",
    "allow_flag": "--allow-wlan-pd-cnss-output-visibility",
    "summary_func": "append_wlan_pd_cnss_nonlog_control_flow_summary",
    "collect_func": "cnss_wlfw_uprobe_collect_trace",
    "result_output_path": "--result-output-path",
}

BASELINE_BOOT_CANDIDATES = [
    "boot_linux_v2189_security_p0_stage_fix.img",
    "boot_linux_v725_fasttransport.img",
    "boot_linux_v724.img",
]


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def latest_v2222_summary() -> Path | None:
    candidates = sorted(
        PRIVATE_RUNS.glob("v2222-boot-window-preflight-*/summary.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def source_marker_audit() -> dict[str, Any]:
    text = HELPER_SOURCE.read_text(errors="replace")
    markers: dict[str, Any] = {}
    for key, marker in REQUIRED_SOURCE_MARKERS.items():
        markers[key] = {
            "needle": marker,
            "present": marker in text,
            "count": text.count(marker),
        }
    mode_guard_ok = (
        "is_wifi_companion_wlan_pd_cnss_output_visibility_mode" in text
        and "wifi-companion-wlan-pd-cnss-output-visibility-start-only requires --allow-wlan-pd-cnss-output-visibility" in text
        and "--allow-wlan-pd-cnss-output-visibility requires wifi-companion-wlan-pd-cnss-output-visibility-start-only mode" in text
    )
    markers["mode_guard_ok"] = mode_guard_ok
    markers["all_present"] = all(
        item.get("present") is True for item in markers.values() if isinstance(item, dict)
    ) and mode_guard_ok
    return markers


def boot_image_inventory() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in BASELINE_BOOT_CANDIDATES:
        path = BOOT_INPUTS / name
        row: dict[str, Any] = {
            "path": rel(path),
            "exists": path.exists(),
        }
        if path.exists():
            stat = path.stat()
            row.update(
                {
                    "size": stat.st_size,
                    "sha256": sha256_file(path),
                    "mode": oct(stat.st_mode & 0o777),
                }
            )
        rows.append(row)
    return rows


def contract_summary(v2222_summary_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    summary = load_json(v2222_summary_path)
    contract_path = REPO_ROOT / summary["contract_path"]
    contract = load_json(contract_path)
    return summary, contract


def build_capture_plan(
    *,
    out_dir: Path,
    v2222_summary_path: Path,
    v2222_summary: dict[str, Any],
    v2222_contract: dict[str, Any],
    source_audit: dict[str, Any],
    boot_images: list[dict[str, Any]],
) -> dict[str, Any]:
    v2223_label = out_dir.name
    helper_result_remote = f"/mnt/sdext/a90/logs/{v2223_label}-helper.result"
    helper_mode = "wifi-companion-wlan-pd-cnss-output-visibility-start-only"
    return {
        "plan_version": 1,
        "label": v2223_label,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_v2222_summary": rel(v2222_summary_path),
        "source_v2222_contract": v2222_summary.get("contract_path"),
        "requires_explicit_user_approval": True,
        "host_only_plan": True,
        "ready_for_approval": bool(
            v2222_summary.get("pass")
            and v2222_contract.get("current_preflight_pass")
            and source_audit.get("all_present")
            and any(row.get("exists") and "v2189" in row["path"] for row in boot_images)
        ),
        "execution_routes": {
            "preferred": "build-or-use-rollbackable-test-boot-with-supervised-helper-window",
            "reason": (
                "The WLFW/QMI events fire in the early boot/helper window. "
                "Late manual helper invocation can validate tooling but cannot replace boot-window capture."
            ),
            "manual_late_window_command_for_debug_only": [
                "/bin/a90_android_execns_probe",
                "--system-root",
                "/mnt/system/system",
                "--vendor-block",
                "/dev/block/sda29",
                "--vendor-fstype",
                "ext4",
                "--target-profile",
                "cnss-daemon",
                "--mode",
                helper_mode,
                "--allow-wlan-pd-cnss-output-visibility",
                "--result-output-path",
                helper_result_remote,
                "--timeout-sec",
                "95",
            ],
        },
        "approved_run_phases": [
            {
                "name": "preflight",
                "command": [
                    "PYTHONPATH=workspace/public/src/scripts/revalidation",
                    "python3",
                    "workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_preflight_v2222.py",
                ],
                "mutates_device": False,
            },
            {
                "name": "test_boot_or_existing_boot_window",
                "command": ["<approval-required rollbackable test-boot handoff>"],
                "mutates_device": True,
                "approval_required": True,
            },
            {
                "name": "postprocess",
                "command": [
                    "PYTHONPATH=workspace/public/src/scripts/revalidation",
                    "python3",
                    "workspace/public/src/scripts/revalidation/a90_kernel_v2220_helper_summary_trace_parser.py",
                    "--input",
                    "<helper-summary-or-collector-summary.json>",
                ],
                "mutates_device": False,
            },
        ],
        "expected_event_sequence": v2222_contract.get("expected_event_sequence"),
        "forbidden_without_new_approval": v2222_contract.get("forbidden_without_new_approval"),
        "baseline_boot_images": boot_images,
        "source_audit": source_audit,
        "helper_runtime": {
            "mode": helper_mode,
            "allow_flag": "--allow-wlan-pd-cnss-output-visibility",
            "timeout_sec": 95,
            "result_output_path": helper_result_remote,
        },
        "next_artifact_gap": {
            "dedicated_v2223_test_boot_image_exists": any(
                "v2223" in row["path"] and row.get("exists") for row in boot_images
            ),
            "needed_before_live_capture": (
                "build or select a rollbackable test boot that supervises the helper "
                "during the early boot WLFW/QMI window, then run it only with explicit approval"
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2223-boot-window-plan")
    parser.add_argument("--v2222-summary", default="", help="Specific V2222 summary.json to consume.")
    parser.add_argument("--out-dir", default="", help="Output directory. Defaults under workspace/private/runs/kernel.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir) if args.out_dir else PRIVATE_RUNS / f"{args.label}-{now_label()}"
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.v2222_summary:
        v2222_summary_path = Path(args.v2222_summary)
        if not v2222_summary_path.is_absolute():
            v2222_summary_path = REPO_ROOT / v2222_summary_path
    else:
        latest = latest_v2222_summary()
        if latest is None:
            raise SystemExit("no V2222 preflight summary found")
        v2222_summary_path = latest

    v2222_summary, v2222_contract = contract_summary(v2222_summary_path)
    source_audit = source_marker_audit()
    boot_images = boot_image_inventory()
    plan = build_capture_plan(
        out_dir=out_dir,
        v2222_summary_path=v2222_summary_path,
        v2222_summary=v2222_summary,
        v2222_contract=v2222_contract,
        source_audit=source_audit,
        boot_images=boot_images,
    )

    decision = (
        "v2223-boot-window-plan-ready-approval-required"
        if plan["ready_for_approval"]
        else "v2223-boot-window-plan-not-ready"
    )
    summary = {
        "label": args.label,
        "decision": decision,
        "pass": plan["ready_for_approval"],
        "out_dir": rel(out_dir),
        "plan_path": rel(out_dir / "boot_window_execution_plan.json"),
        "source_v2222_summary": rel(v2222_summary_path),
        "source_v2222_decision": v2222_summary.get("decision"),
        "source_v2222_pass": v2222_summary.get("pass"),
        "source_audit_all_present": source_audit.get("all_present"),
        "baseline_v2189_present": any(row.get("exists") and "v2189" in row["path"] for row in boot_images),
        "requires_explicit_user_approval": True,
        "host_only": True,
        "device_io": False,
        "safety": {
            "tracefs_control_write": False,
            "bpf_attach": False,
            "probe_write_user_executed": False,
            "cgroup_bpf_attach": False,
            "wifi_scan_connect": False,
            "network_route_change": False,
            "flash_reboot": False,
            "partition_write": False,
        },
        "next_artifact_gap": plan["next_artifact_gap"],
    }

    (out_dir / "boot_window_execution_plan.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n"
    )
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
