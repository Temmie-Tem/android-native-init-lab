#!/usr/bin/env python3
"""V1368 bounded live corrected-RC1 pci-msm status-read proof."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import native_wifi_pci_msm_status_case_live_v1365 as base
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1368-pci-msm-corrected-rc1-status-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1368-pci-msm-corrected-rc1-status-live.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1368_PCI_MSM_CORRECTED_RC1_STATUS_LIVE_2026-06-01.md")
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEBUGFS_ROOT = base.DEBUGFS_ROOT
PCI_MSM_DEBUGFS = base.PCI_MSM_DEBUGFS


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("command", choices=("plan", "run", "reclassify"))
    return parser.parse_args()


def capture_native(
    args: argparse.Namespace,
    store: EvidenceStore,
    name: str,
    command: list[str],
    *,
    timeout: float | None = None,
) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = capture.text if capture.text else capture.error + "\n"
    auto_hide = False
    hide_text = ""
    if capture.status == "busy" or "[busy]" in text:
        auto_hide = True
        hide_capture = run_capture(args, f"{name}-hide-on-busy", ["hide"], timeout=min(timeout or args.timeout, 8.0))
        hide_text = hide_capture.text if hide_capture.text else hide_capture.error + "\n"
        retry_capture = run_capture(args, name, command, timeout=timeout)
        retry_text = retry_capture.text if retry_capture.text else retry_capture.error + "\n"
        text = "\n".join([
            text.rstrip(),
            "--- auto-hide-on-busy ---",
            hide_text.rstrip(),
            "--- retry-after-hide ---",
            retry_text.rstrip(),
            "",
        ])
        capture = retry_capture
    stripped = strip_cmdv1_text(text) if text else text
    rel = f"native/{base.safe_name(name)}.txt"
    store.write_text(rel, stripped)
    data = asdict(capture)
    data["auto_hide_on_busy"] = auto_hide
    if len(data["text"]) > 4096:
        data["text_sha256_like"] = "omitted-large-text"
        data["text"] = data["text"][:4096] + "\n[truncated in manifest]\n"
    data["file"] = rel
    return data


def run_text(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    command: list[str],
    timeout: float = 15.0,
) -> None:
    steps.append(capture_native(args, store, name, ["run", *command], timeout=timeout))


def run_shell(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    script: str,
    timeout: float = 15.0,
) -> None:
    run_text(args, store, steps, name, [args.busybox, "sh", "-c", script], timeout=timeout)


def plan_manifest() -> dict[str, Any]:
    return {
        "cycle": "V1368",
        "type": "bounded live corrected-RC1 status-read plan",
        "generated_at": now_iso(),
        "decision": "v1368-corrected-rc1-status-read-plan-ready",
        "pass": True,
        "reason": "plan-only; no device command executed",
        "next_step": "run V1368 bounded corrected-RC1 status-read proof",
        "candidate_writes": [
            "printf '2\\n' > /sys/kernel/debug/pci-msm/rc_sel",
            "printf '26\\n' > /sys/kernel/debug/pci-msm/case",
        ],
        "forbidden": [
            "case=11 enumerate",
            "case=27 or 28 PERST assert/deassert",
            "case=13 MMIO write",
            "boot_option write",
            "platform bind/unbind",
            "PCI rescan",
            "PMIC/GPIO/GDSC direct writes",
            "eSoC notify or BOOT_DONE",
            "Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "flash, boot image write, partition write",
        ],
    }


def collect_power_snapshot(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], prefix: str) -> None:
    base.collect_power_snapshot(args, store, steps, prefix)


def collect_run(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = [
        capture_native(args, store, "version", ["version"], timeout=10.0),
        capture_native(args, store, "selftest", ["selftest", "verbose"], timeout=15.0),
        capture_native(args, store, "status", ["status"], timeout=15.0),
    ]
    run_text(args, store, steps, "mounts-before", [args.toybox, "cat", "/proc/mounts"], timeout=10.0)
    mounted_before = base.debugfs_mounted(base.step_text(store, steps, "mounts-before"))
    if not mounted_before:
        run_text(args, store, steps, "debugfs-mount", [args.busybox, "mount", "-t", "debugfs", "debugfs", DEBUGFS_ROOT], timeout=15.0)

    run_text(args, store, steps, "mounts-during", [args.toybox, "cat", "/proc/mounts"], timeout=10.0)
    run_shell(args, store, steps, "pci-msm-find", f"{args.toybox} find {PCI_MSM_DEBUGFS} -maxdepth 2 -print 2>/dev/null || true", timeout=10.0)
    run_shell(args, store, steps, "pci-msm-case-read", f"{args.toybox} cat {PCI_MSM_DEBUGFS}/case 2>&1 | {args.busybox} head -80 || true", timeout=10.0)
    collect_power_snapshot(args, store, steps, "before")

    run_shell(
        args,
        store,
        steps,
        "write-rc1-bitmask2-case26-status-only",
        f"printf '2\\n' > {PCI_MSM_DEBUGFS}/rc_sel && printf '26\\n' > {PCI_MSM_DEBUGFS}/case",
        timeout=10.0,
    )
    run_shell(args, store, steps, "settle", f"{args.busybox} sleep 1; true", timeout=5.0)
    collect_power_snapshot(args, store, steps, "after")

    if not mounted_before:
        run_text(args, store, steps, "debugfs-umount", [args.busybox, "umount", DEBUGFS_ROOT], timeout=15.0)
    run_text(args, store, steps, "mounts-after", [args.toybox, "cat", "/proc/mounts"], timeout=10.0)
    steps.extend([
        capture_native(args, store, "post-selftest", ["selftest", "verbose"], timeout=15.0),
        capture_native(args, store, "post-status", ["status"], timeout=15.0),
    ])
    return steps


def command_ok(steps: list[dict[str, Any]], name: str) -> bool:
    return base.command_ok(steps, name)


def step_text(store: EvidenceStore, steps: list[dict[str, Any]], name: str) -> str:
    return base.step_text(store, steps, name)


def analyze(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    mounts_before = step_text(store, steps, "mounts-before")
    mounts_during = step_text(store, steps, "mounts-during")
    mounts_after = step_text(store, steps, "mounts-after")
    before_pci = step_text(store, steps, "before-pci-devices")
    after_pci = step_text(store, steps, "after-pci-devices")
    before_mhi = step_text(store, steps, "before-mhi-devices")
    after_mhi = step_text(store, steps, "after-mhi-devices")
    before_reg = step_text(store, steps, "before-regulator-pcie")
    after_reg = step_text(store, steps, "after-regulator-pcie")
    before_clk = step_text(store, steps, "before-clk-pcie")
    after_clk = step_text(store, steps, "after-clk-pcie")
    before_dmesg = step_text(store, steps, "before-dmesg-pcie-tail")
    after_dmesg = step_text(store, steps, "after-dmesg-pcie-tail")
    post_selftest = step_text(store, steps, "post-selftest")

    mounted_before = base.debugfs_mounted(mounts_before)
    mounted_during = base.debugfs_mounted(mounts_during)
    mounts_after_ok = command_ok(steps, "mounts-after")
    mounted_after = base.debugfs_mounted(mounts_after) if mounts_after_ok else None
    mounted_by_v1368 = not mounted_before and command_ok(steps, "debugfs-mount")
    cleanup_ok = (mounted_after == mounted_before) if mounted_by_v1368 and mounts_after_ok else (True if not mounted_by_v1368 else None)
    write_step = base.step_by_name(steps, "write-rc1-bitmask2-case26-status-only")
    write_ok = bool(write_step.get("ok"))
    reset_after_write = any(
        marker in base.step_error_text(step)
        for step in steps
        for marker in ("Connection reset by peer", "END marker not found")
        if step.get("name") in {
            "write-rc1-bitmask2-case26-status-only",
            "settle",
            "after-regulator-pcie",
            "after-clk-pcie",
            "after-gpio-pcie",
            "after-pci-devices",
            "after-mhi-devices",
            "after-interrupts",
            "after-dmesg-pcie-tail",
            "debugfs-umount",
            "mounts-after",
            "post-selftest",
            "post-status",
        }
    )
    after_captures_ok = all(
        command_ok(steps, name)
        for name in (
            "settle",
            "after-regulator-pcie",
            "after-clk-pcie",
            "after-gpio-pcie",
            "after-pci-devices",
            "after-mhi-devices",
            "after-interrupts",
            "after-dmesg-pcie-tail",
            "mounts-after",
            "post-selftest",
            "post-status",
        )
    )
    before_pci_count = base.count_find_children(before_pci, "/sys/bus/pci/devices")
    after_pci_count = base.count_find_children(after_pci, "/sys/bus/pci/devices") if command_ok(steps, "after-pci-devices") else None
    before_mhi_present = base.mhi_nodes_present(before_mhi)
    after_mhi_present = base.mhi_nodes_present(after_mhi) if command_ok(steps, "after-mhi-devices") else None
    gdsc_changed = before_reg != after_reg if command_ok(steps, "after-regulator-pcie") else None
    clk_changed = before_clk != after_clk if command_ok(steps, "after-clk-pcie") else None
    pcie_link_seen = "LTSSM_L0" in after_dmesg or "Current GEN" in after_dmesg
    enumerate_seen = "ENUMERATE" in after_dmesg.upper() or "enumerate" in after_dmesg.lower()
    rc1_status_seen = "PCIe: RC1: PERST and WAKE status" in after_dmesg
    rc1_perst_match = re.search(r"PCIe: RC1: PERST: gpio102 value: (?P<value>[01])", after_dmesg)
    rc1_wake_match = re.search(r"PCIe: RC1: WAKE: gpio104 value: (?P<value>[01])", after_dmesg)
    rc1_perst_value = int(rc1_perst_match.group("value")) if rc1_perst_match else None
    rc1_wake_value = int(rc1_wake_match.group("value")) if rc1_wake_match else None
    post_selftest_fail0 = "fail=0" in post_selftest

    if not mounted_during:
        decision = "v1368-debugfs-mount-unavailable"
        pass_condition = False
        reason = "debugfs was not mounted during the corrected-RC1 proof window"
        next_step = "repair debugfs access before corrected-RC1 status proof"
    elif reset_after_write:
        decision = "v1368-corrected-rc1-status-transport-reset"
        pass_condition = False
        reason = "corrected rc_sel=2 case=26 status-read caused command transport loss before after-captures completed"
        next_step = "stop pci-msm debugfs case writes; use kernel-side shim or Android-reference route"
    elif not write_ok:
        decision = "v1368-corrected-rc1-status-write-failed"
        pass_condition = False
        reason = "rc_sel=2 or case=26 status-read write failed"
        next_step = "inspect write error; do not attempt enumerate"
    elif not after_captures_ok:
        decision = "v1368-corrected-rc1-status-after-capture-incomplete"
        pass_condition = False
        reason = "corrected-RC1 status-read returned but after-captures were incomplete"
        next_step = "inspect after-capture failure before further pci-msm debugfs use"
    elif after_pci_count != before_pci_count or after_mhi_present != before_mhi_present or pcie_link_seen:
        decision = "v1368-corrected-rc1-status-caused-link-transition"
        pass_condition = False
        reason = "status-read unexpectedly changed PCI/MHI/link state"
        next_step = "stop pci-msm debugfs writes and classify side effect"
    elif cleanup_ok and post_selftest_fail0 and rc1_status_seen:
        decision = "v1368-corrected-rc1-status-proof-clean"
        pass_condition = True
        reason = "rc_sel=2 and case=26 emitted RC1 PERST/WAKE status with no PCI/MHI/link transition and device health remained clean"
        next_step = "V1369 decide whether to advance to pcie1 enumerate or prefer kernel-side shim; no enumerate yet"
    elif cleanup_ok and post_selftest_fail0:
        decision = "v1368-corrected-rc1-status-output-missing"
        pass_condition = False
        reason = "corrected-RC1 status-read returned cleanly but RC1 PERST/WAKE status output was not observed"
        next_step = "inspect dmesg/output path before further pci-msm debugfs use"
    else:
        decision = "v1368-corrected-rc1-status-health-or-cleanup-issue"
        pass_condition = False
        reason = "corrected-RC1 status-read completed but cleanup or health check failed"
        next_step = "inspect cleanup/health issue before further pci-msm debugfs use"

    return {
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "next_step": next_step,
        "mounted_before": mounted_before,
        "mounted_by_v1368": mounted_by_v1368,
        "mounted_during": mounted_during,
        "mounted_after": mounted_after,
        "cleanup_ok": cleanup_ok,
        "write_ok": write_ok,
        "reset_after_write": reset_after_write,
        "after_captures_ok": after_captures_ok,
        "before_pci_count": before_pci_count,
        "after_pci_count": after_pci_count,
        "before_mhi_present": before_mhi_present,
        "after_mhi_present": after_mhi_present,
        "gdsc_changed": gdsc_changed,
        "clk_changed": clk_changed,
        "pcie_link_seen": pcie_link_seen,
        "enumerate_seen": enumerate_seen,
        "rc1_status_seen": rc1_status_seen,
        "rc1_perst_gpio102_value": rc1_perst_value,
        "rc1_wake_gpio104_value": rc1_wake_value,
        "post_selftest_fail0": post_selftest_fail0,
        "safety": {
            "debugfs_write_executed": True,
            "rc_sel_2_write_executed": True,
            "case26_status_write_executed": True,
            "case11_enumerate_executed": False,
            "perst_assert_deassert_case_executed": False,
            "mmio_write_case_executed": False,
            "boot_option_write_executed": False,
            "platform_bind_unbind_executed": False,
            "pci_rescan_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "esoc_notify_boot_done_executed": False,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
            "flash_boot_partition_write_executed": False,
        },
    }


def key_rows(analysis: dict[str, Any]) -> list[list[Any]]:
    keys = [
        "mounted_before",
        "mounted_by_v1368",
        "mounted_during",
        "mounted_after",
        "cleanup_ok",
        "write_ok",
        "reset_after_write",
        "after_captures_ok",
        "before_pci_count",
        "after_pci_count",
        "before_mhi_present",
        "after_mhi_present",
        "gdsc_changed",
        "clk_changed",
        "pcie_link_seen",
        "enumerate_seen",
        "rc1_status_seen",
        "rc1_perst_gpio102_value",
        "rc1_wake_gpio104_value",
        "post_selftest_fail0",
    ]
    return [[key, analysis.get(key)] for key in keys]


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    return "\n".join([
        "# V1368 Corrected-RC1 pci-msm Status Live",
        "",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        markdown_table(["field", "value"], key_rows(analysis)) if analysis else "",
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    step_rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("status"), step.get("file")]
        for step in manifest.get("steps") or []
    ]
    return "\n".join([
        "# Native Init V1368 Corrected-RC1 pci-msm Status Live",
        "",
        "## Summary",
        "",
        "- Cycle: `V1368`",
        "- Type: bounded live corrected-RC1 status-read proof",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_pci_msm_corrected_rc1_status_live_v1368.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1368-pci-msm-corrected-rc1-status-live/manifest.json`",
        "  - `tmp/wifi/v1368-pci-msm-corrected-rc1-status-live/summary.md`",
        "  - `tmp/wifi/v1368-pci-msm-corrected-rc1-status-live/native/`",
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "## Key Observations",
        "",
        markdown_table(["field", "value"], key_rows(analysis)) if analysis else "plan-only",
        "",
        "## Captures",
        "",
        markdown_table(["name", "ok", "rc", "status", "file"], step_rows) if step_rows else "plan-only",
        "",
        "## Safety",
        "",
        "- V1368 writes only corrected `rc_sel=2` and status-read `case=26`.",
        "- No `case=11` enumerate, PERST assert/deassert cases, MMIO write cases,",
        "  boot option write, platform bind/unbind, PCI rescan, PMIC/GPIO/GDSC",
        "  direct write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, credential",
        "  handling, DHCP/routes, external ping, flash, boot image write, or partition write.",
        "",
        "## Next",
        "",
        manifest["next_step"],
        "",
    ])


def write_outputs(store: EvidenceStore, manifest: dict[str, Any]) -> None:
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        manifest = plan_manifest()
        manifest["command"] = "plan"
        manifest["host"] = collect_host_metadata()
        write_outputs(store, manifest)
        print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(store.run_dir)}, indent=2))
        return 0

    if args.command == "reclassify":
        manifest = json.loads((store.run_dir / "manifest.json").read_text(encoding="utf-8"))
        analysis = analyze(store, manifest.get("steps") or [])
        manifest["analysis"] = analysis
        manifest["decision"] = analysis["decision"]
        manifest["pass"] = analysis["pass"]
        manifest["reason"] = analysis["reason"]
        manifest["next_step"] = analysis["next_step"]
        manifest["reclassified_at"] = now_iso()
        write_outputs(store, manifest)
        print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(store.run_dir)}, indent=2))
        return 0 if manifest["pass"] else 1

    steps = collect_run(args, store)
    analysis = analyze(store, steps)
    manifest = {
        "cycle": "V1368",
        "type": "bounded live corrected-RC1 status-read proof",
        "generated_at": now_iso(),
        "command": "run",
        "host": collect_host_metadata(),
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "next_step": analysis["next_step"],
        "analysis": analysis,
        "steps": steps,
    }
    write_outputs(store, manifest)
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(store.run_dir)}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
