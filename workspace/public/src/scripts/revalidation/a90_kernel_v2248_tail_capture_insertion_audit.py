#!/usr/bin/env python3
"""V2248 post-FWREADY tail capture insertion audit.

Host-only guardrail for the next live kernel-observation unit.  V2247 can
score exact-slide PC/LR samples against the post-FWREADY qcacld/HDD target
set, but the target path runs inside the native-init boot helper immediately
after the `boot_wlan` trigger.  This script verifies the source/build anchors
that make a later host-side sampler insufficient and emits the concrete
insertion contract for the next rollbackable test boot.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from a90_kernel_v2241_user_uprobe_offset_base_map import PRIVATE_RUNS, REPO_ROOT, rel

HELPER_SOURCE = REPO_ROOT / "workspace/public/src/native-init/helpers/a90_android_execns_probe.c"
BUILD_V2237 = REPO_ROOT / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2237_supplicant_terminate_poll.py"
RUNNER_V2216 = REPO_ROOT / "workspace/public/src/scripts/revalidation/native_kernel_perf_regs_codeword_sample_ring_v2216.py"
HELPER_V2216 = REPO_ROOT / "workspace/public/src/native-init/helpers/a90_bpf_perf_regs_codeword_sample_ring.c"


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def line_matches(path: Path, pattern: str) -> list[dict[str, Any]]:
    regex = re.compile(pattern)
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if regex.search(line):
            rows.append({"line": index, "text": line.rstrip()})
    return rows


def require_matches(path: Path, label: str, pattern: str) -> list[dict[str, Any]]:
    rows = line_matches(path, pattern)
    if not rows:
        raise RuntimeError(f"missing {label}: {path}:{pattern}")
    return rows


def first_line(rows: list[dict[str, Any]]) -> int:
    return int(rows[0]["line"]) if rows else -1


def helper_tail_anchors() -> dict[str, Any]:
    trigger_def = require_matches(
        HELPER_SOURCE,
        "post-FWREADY boot_wlan trigger function",
        r"static int append_post_fw_ready_boot_wlan_trigger",
    )
    trigger_call = require_matches(
        HELPER_SOURCE,
        "post-FWREADY boot_wlan trigger call",
        r"append_post_fw_ready_boot_wlan_trigger\(stdout_buf\)",
    )
    eight_second_hold = require_matches(
        HELPER_SOURCE,
        "post-trigger fixed hold",
        r"usleep\(8000000\)",
    )
    stack_sampler_call = require_matches(
        HELPER_SOURCE,
        "after_boot_wlan_trigger stack sampler",
        r"append_icnss_register_probe_stack_sampler\(stdout_buf,",
    )
    fwclass_feeder_call = require_matches(
        HELPER_SOURCE,
        "after_boot_wlan_trigger firmware_class feeder",
        r"append_qcacld_firmware_class_fallback_feeder\(stdout_buf,",
    )
    long_window_call = require_matches(
        HELPER_SOURCE,
        "after_boot_wlan_long_window sampler",
        r"after_boot_wlan_long_window",
    )
    wait_macro = require_matches(
        HELPER_SOURCE,
        "FW_READY wait macro",
        r"A90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_WAIT_MS",
    )
    fwclass_gate = require_matches(
        HELPER_SOURCE,
        "post-FWREADY fwclass route gate",
        r"wlan_pd_post_fw_ready_fwclass_bridge",
    )
    return {
        "source": rel(HELPER_SOURCE),
        "post_fw_ready_trigger_function_line": first_line(trigger_def),
        "post_fw_ready_trigger_call_line": first_line(trigger_call),
        "post_trigger_hold_line": first_line(eight_second_hold),
        "after_trigger_stack_sampler_line": first_line(stack_sampler_call),
        "after_trigger_fwclass_feeder_line": first_line(fwclass_feeder_call),
        "long_window_line": first_line(long_window_call),
        "fw_ready_wait_macro_lines": [row["line"] for row in wait_macro],
        "route_gate_lines": [row["line"] for row in fwclass_gate[:8]],
        "ordered_tail_window": first_line(trigger_call) < first_line(eight_second_hold) < first_line(fwclass_feeder_call),
    }


def build_anchors() -> dict[str, Any]:
    bridge_flag = require_matches(BUILD_V2237, "V2237 fwclass bridge flag", r"SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG")
    helper_binary = require_matches(BUILD_V2237, "V2237 helper binary", r"--helper-binary")
    ramdisk_cpio = require_matches(BUILD_V2237, "V2237 ramdisk cpio", r"--ramdisk-cpio|RAMDISK_CPIO")
    init_version = require_matches(BUILD_V2237, "V2237 init version", r'"--init-version": "0\.9\.268"')
    return {
        "source": rel(BUILD_V2237),
        "service_object_fwclass_bridge_flag_present": any(
            "A90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1" in row["text"]
            for row in line_matches(BUILD_V2237, r"A90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE")
        ),
        "bridge_flag_lines": [row["line"] for row in bridge_flag[:6]],
        "helper_binary_line": first_line(helper_binary),
        "ramdisk_cpio_lines": [row["line"] for row in ramdisk_cpio[:6]],
        "init_version_line": first_line(init_version),
        "baseline_init_version": "0.9.268",
        "baseline_build": "v2237-supplicant-terminate-poll",
    }


def v2216_sampler_anchors() -> dict[str, Any]:
    version = require_matches(HELPER_V2216, "V2216 helper version", r'A90_VERSION "a90_bpf_perf_regs_codeword_sample_ring v2216"')
    usage = require_matches(HELPER_V2216, "V2216 usage", r"--duration-ms N.*--period-ns N.*--print-limit N")
    attach_gate = require_matches(HELPER_V2216, "V2216 attach gate", r"--allow-attach")
    complete_marker = require_matches(HELPER_V2216, "V2216 complete marker", r"result=v2216-perf-regs-codeword-sample-ring-complete")
    remote_helper = require_matches(RUNNER_V2216, "V2216 remote helper path", r'REMOTE_HELPER = "/cache/bin/a90_bpf_perf_regs_codeword_sample_ring"')
    live_run = require_matches(RUNNER_V2216, "V2216 live runner allow attach", r'"--allow-attach"')
    install = require_matches(RUNNER_V2216, "V2216 helper install", r"install_helper")
    return {
        "helper_source": rel(HELPER_V2216),
        "runner_source": rel(RUNNER_V2216),
        "version_line": first_line(version),
        "usage_line": first_line(usage),
        "attach_gate_lines": [row["line"] for row in attach_gate[:6]],
        "complete_marker_line": first_line(complete_marker),
        "remote_helper_line": first_line(remote_helper),
        "runner_live_allow_attach_line": first_line(live_run),
        "runner_install_helper_line": first_line(install),
        "remote_helper_path": "/cache/bin/a90_bpf_perf_regs_codeword_sample_ring",
        "default_duration_ms": 1000,
        "default_period_ns": 1000000,
        "supports_tail_window_duration": True,
    }


def build_summary(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    helper = helper_tail_anchors()
    build = build_anchors()
    sampler = v2216_sampler_anchors()
    host_after_boot_sufficient = False
    requires_embedded_concurrent_sampler = True
    decision = "v2248-tail-capture-insertion-audit-pass"
    if not helper["ordered_tail_window"] or not build["service_object_fwclass_bridge_flag_present"]:
        decision = "v2248-tail-capture-insertion-audit-failed"
    contract = {
        "next_cycle": "V2249",
        "goal": "capture exact-slide perf regs/codeword samples during the post-FWREADY firmware_class/qcacld-HDD tail",
        "must_start_before": "append_post_fw_ready_boot_wlan_trigger(stdout_buf)",
        "must_remain_active_through": "append_qcacld_firmware_class_fallback_feeder(stdout_buf, \"after_boot_wlan_trigger\", 30000)",
        "minimum_duration_ms": 45000,
        "period_ns": 1000000,
        "print_limit": 512,
        "required_helper_args": [
            sampler["remote_helper_path"],
            "--duration-ms",
            "45000",
            "--period-ns",
            "1000000",
            "--print-limit",
            "512",
            "--allow-attach",
        ],
        "capture_output_path": "/cache/native-init-v2249-tail-perf-regs-codeword.log",
        "score_with": "workspace/public/src/scripts/revalidation/a90_kernel_v2247_tail_pc_lr_scorer.py",
        "implementation_options": [
            "preferred: package/deploy the V2216 helper and launch it from a compile-gated a90_android_execns_probe child before the boot_wlan write",
            "acceptable: embed the perf regs/codeword sampler logic directly in the helper under a compile gate",
            "not sufficient: run the host-side V2216 runner only after native boot completes",
        ],
    }
    summary = {
        "label": args.label,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "decision": decision,
        "pass": decision.endswith("-pass"),
        "out_dir": rel(out_dir),
        "safety": {
            "host_only": True,
            "device_io": False,
            "bpf_attach": False,
            "tracefs_control_write": False,
            "probe_write_user_executed": False,
            "wifi_scan_connect": False,
            "network_route_change": False,
            "flash_reboot": False,
            "partition_write": False,
            "private_raw_log_copied_to_public": False,
        },
        "anchors": {
            "helper_tail": helper,
            "build_v2237": build,
            "v2216_sampler": sampler,
        },
        "analysis": {
            "host_after_boot_runner_sufficient": host_after_boot_sufficient,
            "requires_embedded_concurrent_sampler": requires_embedded_concurrent_sampler,
            "reason": (
                "The qcacld/HDD tail begins inside the native-init helper immediately after "
                "the post-FWREADY boot_wlan write and the firmware_class feeder runs before "
                "normal host-side post-boot control can reliably attach a new sampler."
            ),
        },
        "next_live_contract": contract,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2248-tail-capture-insertion-audit")
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    out_dir = args.out_dir or (PRIVATE_RUNS / f"{args.label}-{now_label()}")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(args, out_dir)
    print(json.dumps({
        "decision": summary["decision"],
        "pass": summary["pass"],
        "out_dir": summary["out_dir"],
        "host_after_boot_runner_sufficient": summary["analysis"]["host_after_boot_runner_sufficient"],
        "requires_embedded_concurrent_sampler": summary["analysis"]["requires_embedded_concurrent_sampler"],
        "next_cycle": summary["next_live_contract"]["next_cycle"],
    }, indent=2, sort_keys=True))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
