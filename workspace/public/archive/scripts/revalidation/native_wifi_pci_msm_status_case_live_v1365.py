#!/usr/bin/env python3
"""V1365 bounded live pci-msm debugfs status-only proof."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1365-pci-msm-status-case-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1365-pci-msm-status-case-live.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1365_PCI_MSM_STATUS_CASE_LIVE_2026-06-01.md")
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEBUGFS_ROOT = "/sys/kernel/debug"
PCI_MSM_DEBUGFS = f"{DEBUGFS_ROOT}/pci-msm"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._+-" else "-" for ch in value).strip("-") or "capture"


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
    stripped = strip_cmdv1_text(text) if capture.text else text
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, stripped)
    data = asdict(capture)
    if len(data["text"]) > 4096:
        data["text_sha256_like"] = "omitted-large-text"
        data["text"] = data["text"][:4096] + "\n[truncated in manifest]\n"
    data["file"] = rel
    return data


def step_text(store: EvidenceStore, steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            rel = str(step.get("file") or "")
            path = store.run_dir / rel
            return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return ""


def command_ok(steps: list[dict[str, Any]], name: str) -> bool:
    return any(step.get("name") == name and step.get("ok") for step in steps)


def step_by_name(steps: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for step in steps:
        if step.get("name") == name:
            return step
    return {}


def step_error_text(step: dict[str, Any]) -> str:
    return " ".join(str(step.get(key) or "") for key in ("status", "error", "text"))


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


def debugfs_mounted(text: str) -> bool:
    return re.search(rf"\s{re.escape(DEBUGFS_ROOT)}\s+debugfs\s", text) is not None


def plan_manifest() -> dict[str, Any]:
    return {
        "cycle": "V1365",
        "type": "bounded live pci-msm status-only proof plan",
        "generated_at": now_iso(),
        "decision": "v1365-pci-msm-status-case-plan-ready",
        "pass": True,
        "reason": "plan-only; no device command executed",
        "next_step": "run V1365 bounded status-only pci-msm debugfs proof",
        "candidate_writes": [
            "echo 1 > /sys/kernel/debug/pci-msm/rc_sel",
            "echo 26 > /sys/kernel/debug/pci-msm/case",
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
    run_shell(args, store, steps, f"{prefix}-regulator-pcie", f"{args.busybox} grep -iE 'pcie_1_gdsc|pcie_0_gdsc|pm8150l_l3|pm8150_l5|VDD_CX' {DEBUGFS_ROOT}/regulator/regulator_summary {DEBUGFS_ROOT}/regulator_summary 2>/dev/null || true", timeout=15.0)
    run_shell(args, store, steps, f"{prefix}-clk-pcie", f"{args.busybox} grep -iE 'pcie_1|PCIE_1|pcie1|PCIE1|phy_refgen|clkref' {DEBUGFS_ROOT}/clk/clk_summary 2>/dev/null || true", timeout=15.0)
    run_shell(args, store, steps, f"{prefix}-gpio-pcie", f"{args.busybox} grep -iE 'gpio-102|gpio102|GPIO102|gpio-135|gpio135|GPIO135|gpio-142|gpio142|GPIO142|1270|pm8150' {DEBUGFS_ROOT}/gpio 2>/dev/null || true", timeout=15.0)
    run_shell(args, store, steps, f"{prefix}-pci-devices", f"{args.toybox} find /sys/bus/pci/devices -maxdepth 2 -print 2>/dev/null || true", timeout=10.0)
    run_shell(args, store, steps, f"{prefix}-mhi-devices", f"{args.toybox} ls -l /sys/bus/mhi/devices /dev/mhi* /dev/*mhi* 2>/dev/null || true", timeout=10.0)
    run_shell(args, store, steps, f"{prefix}-interrupts", f"{args.toybox} cat /proc/interrupts | {args.busybox} grep -iE 'gpio|pcie|mhi|msi|142|102' || true", timeout=10.0)
    run_shell(args, store, steps, f"{prefix}-dmesg-pcie-tail", f"{args.toybox} dmesg | {args.busybox} grep -iE 'pci-msm|msm_pcie|pcie|LTSSM|PERST|WAKE|enumerate|mhi|gpio' | {args.busybox} tail -220 || true", timeout=20.0)


def collect_run(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = [
        capture_native(args, store, "version", ["version"], timeout=10.0),
        capture_native(args, store, "selftest", ["selftest", "verbose"], timeout=15.0),
        capture_native(args, store, "status", ["status"], timeout=15.0),
    ]
    run_text(args, store, steps, "mounts-before", [args.toybox, "cat", "/proc/mounts"], timeout=10.0)
    mounted_before = debugfs_mounted(step_text(store, steps, "mounts-before"))
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
        "write-rc1-case26-status-only",
        f"printf '1\\n' > {PCI_MSM_DEBUGFS}/rc_sel && printf '26\\n' > {PCI_MSM_DEBUGFS}/case",
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


def count_find_children(text: str, root: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip() and line.strip() != root)


def mhi_nodes_present(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "total 0":
            continue
        if "/sys/bus/mhi/devices" in stripped and stripped.endswith("/sys/bus/mhi/devices:"):
            continue
        return True
    return False


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

    mounted_before = debugfs_mounted(mounts_before)
    mounted_during = debugfs_mounted(mounts_during)
    mounts_after_ok = command_ok(steps, "mounts-after")
    mounted_after = debugfs_mounted(mounts_after) if mounts_after_ok else None
    mounted_by_v1365 = not mounted_before and command_ok(steps, "debugfs-mount")
    cleanup_ok = (mounted_after == mounted_before) if mounted_by_v1365 and mounts_after_ok else (True if not mounted_by_v1365 else None)
    write_step = step_by_name(steps, "write-rc1-case26-status-only")
    write_ok = bool(write_step.get("ok"))
    reset_after_write = any(
        marker in step_error_text(step)
        for step in steps
        for marker in ("Connection reset by peer", "END marker not found")
        if step.get("name") in {
            "write-rc1-case26-status-only",
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
    before_pci_count = count_find_children(before_pci, "/sys/bus/pci/devices")
    after_pci_count = count_find_children(after_pci, "/sys/bus/pci/devices") if command_ok(steps, "after-pci-devices") else None
    before_mhi_present = mhi_nodes_present(before_mhi)
    after_mhi_present = mhi_nodes_present(after_mhi) if command_ok(steps, "after-mhi-devices") else None
    gdsc_changed = before_reg != after_reg if command_ok(steps, "after-regulator-pcie") else None
    clk_changed = before_clk != after_clk if command_ok(steps, "after-clk-pcie") else None
    pcie_link_seen = "LTSSM_L0" in after_dmesg or "Current GEN" in after_dmesg
    enumerate_seen = "ENUMERATE" in after_dmesg.upper() or "enumerate" in after_dmesg.lower()
    new_dmesg = after_dmesg.replace(before_dmesg, "")
    post_selftest_fail0 = "fail=0" in post_selftest

    if not mounted_during:
        decision = "v1365-debugfs-mount-unavailable"
        pass_condition = False
        reason = "debugfs was not mounted during the status-only proof window"
        next_step = "repair debugfs access before pci-msm status proof"
    elif reset_after_write:
        decision = "v1365-case26-transport-reset-reboot-risk"
        pass_condition = False
        reason = "case=26 status-only proof caused command transport loss before after-captures completed"
        next_step = "treat pci-msm debugfs case writes as unsafe; do not attempt enumerate without source/disasm proof"
    elif not write_ok:
        decision = "v1365-status-only-write-failed"
        pass_condition = False
        reason = "rc_sel=1 or case=26 status-only write failed"
        next_step = "inspect write error; do not attempt enumerate"
    elif not after_captures_ok:
        decision = "v1365-status-only-after-capture-incomplete"
        pass_condition = False
        reason = "status-only proof returned but one or more after-captures failed"
        next_step = "inspect after-capture failure before further pci-msm debugfs use"
    elif after_pci_count != before_pci_count or after_mhi_present != before_mhi_present or pcie_link_seen:
        decision = "v1365-status-only-caused-link-transition"
        pass_condition = False
        reason = "status-only case unexpectedly changed PCI/MHI/link state"
        next_step = "stop pci-msm debugfs writes and classify side effect"
    elif cleanup_ok and post_selftest_fail0:
        decision = "v1365-status-only-proof-clean"
        pass_condition = True
        reason = "rc_sel=1 and case=26 completed with no PCI/MHI/link transition and device health remained clean"
        next_step = "V1366 host-only enumerate live contract using V1365 status proof; no enumerate yet"
    else:
        decision = "v1365-status-only-health-or-cleanup-issue"
        pass_condition = False
        reason = "status-only proof completed but cleanup or health check failed"
        next_step = "inspect cleanup/health issue before further pci-msm debugfs use"

    return {
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "next_step": next_step,
        "mounted_before": mounted_before,
        "mounted_by_v1365": mounted_by_v1365,
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
        "new_dmesg_tail": new_dmesg[-1200:],
        "post_selftest_fail0": post_selftest_fail0,
        "safety": {
            "debugfs_write_executed": True,
            "rc_sel_write_executed": True,
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
        "mounted_by_v1365",
        "mounted_during",
        "mounted_after",
        "cleanup_ok",
        "write_ok",
        "before_pci_count",
        "after_pci_count",
        "before_mhi_present",
        "after_mhi_present",
        "gdsc_changed",
        "clk_changed",
        "pcie_link_seen",
        "enumerate_seen",
        "post_selftest_fail0",
        "reset_after_write",
        "after_captures_ok",
    ]
    return [[key, analysis.get(key)] for key in keys]


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    return "\n".join([
        "# V1365 pci-msm Status-only Case Live",
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
        "# Native Init V1365 pci-msm Status-only Case Live",
        "",
        "## Summary",
        "",
        "- Cycle: `V1365`",
        "- Type: bounded live status-only proof",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_pci_msm_status_case_live_v1365.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1365-pci-msm-status-case-live/manifest.json`",
        "  - `tmp/wifi/v1365-pci-msm-status-case-live/summary.md`",
        "  - `tmp/wifi/v1365-pci-msm-status-case-live/native/`",
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
        "- V1365 writes only `rc_sel=1` and status-only `case=26`.",
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
        "cycle": "V1365",
        "type": "bounded live status-only proof",
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
