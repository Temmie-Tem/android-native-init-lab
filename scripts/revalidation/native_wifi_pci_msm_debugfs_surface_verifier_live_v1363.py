#!/usr/bin/env python3
"""V1363 live read-only pci-msm debugfs surface verifier."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1363-pci-msm-debugfs-surface-verifier-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1363-pci-msm-debugfs-surface-verifier-live.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1363_PCI_MSM_DEBUGFS_SURFACE_VERIFIER_LIVE_2026-06-01.md")
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
        "cycle": "V1363",
        "type": "live read-only pci-msm debugfs surface verifier plan",
        "generated_at": now_iso(),
        "decision": "v1363-pci-msm-debugfs-surface-verifier-plan-ready",
        "pass": True,
        "reason": "plan-only; no device command executed",
        "next_step": "run V1363 live read-only pci-msm debugfs surface verifier",
        "scope": [
            "temporarily mount debugfs only if absent",
            "list pci-msm debugfs directories and files",
            "read small pci-msm debugfs files only; no writes",
            "restore debugfs mount state and post-health",
        ],
        "forbidden": [
            "debugfs/sysfs writes",
            "pci-msm debugfs enumerate/linkup/power writes",
            "platform bind/unbind",
            "PCI rescan",
            "PMIC/GPIO/GDSC writes",
            "eSoC notify or BOOT_DONE",
            "Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "flash, boot image write, partition write",
        ],
    }


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
    run_shell(args, store, steps, "pci-msm-ls", f"{args.toybox} ls -lR {PCI_MSM_DEBUGFS} 2>/dev/null || true", timeout=15.0)
    run_shell(args, store, steps, "pci-msm-find", f"{args.toybox} find {PCI_MSM_DEBUGFS} -maxdepth 4 -print 2>/dev/null || true", timeout=15.0)
    run_shell(
        args,
        store,
        steps,
        "pci-msm-file-heads",
        (
            f"for f in $({args.toybox} find {PCI_MSM_DEBUGFS} -maxdepth 3 -type f 2>/dev/null); do "
            "echo \"== $f ==\"; "
            f"{args.toybox} cat \"$f\" 2>&1 | {args.busybox} head -80; "
            "done; true"
        ),
        timeout=25.0,
    )
    run_shell(args, store, steps, "pci-msm-dmesg-tail", f"{args.toybox} dmesg | {args.busybox} grep -iE 'pci-msm|msm_pcie|pcie|LTSSM|enumerate' | {args.busybox} tail -180 || true", timeout=20.0)

    if not mounted_before:
        run_text(args, store, steps, "debugfs-umount", [args.busybox, "umount", DEBUGFS_ROOT], timeout=15.0)
    run_text(args, store, steps, "mounts-after", [args.toybox, "cat", "/proc/mounts"], timeout=10.0)
    steps.extend([
        capture_native(args, store, "post-selftest", ["selftest", "verbose"], timeout=15.0),
        capture_native(args, store, "post-status", ["status"], timeout=15.0),
    ])
    return steps


def text_has_real_entries(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and "No such file" not in stripped and "not found" not in stripped


def analyze(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    mounts_before = step_text(store, steps, "mounts-before")
    mounts_during = step_text(store, steps, "mounts-during")
    mounts_after = step_text(store, steps, "mounts-after")
    pci_msm_find = step_text(store, steps, "pci-msm-find")
    pci_msm_heads = step_text(store, steps, "pci-msm-file-heads")
    post_selftest = step_text(store, steps, "post-selftest")

    mounted_before = debugfs_mounted(mounts_before)
    mounted_during = debugfs_mounted(mounts_during)
    mounted_after = debugfs_mounted(mounts_after)
    mounted_by_v1363 = not mounted_before and command_ok(steps, "debugfs-mount")
    cleanup_ok = (mounted_after == mounted_before) if mounted_by_v1363 else True
    pci_msm_present = text_has_real_entries(pci_msm_find) and PCI_MSM_DEBUGFS in pci_msm_find
    enumerate_name_seen = "enumerate" in pci_msm_find or "enumerate" in pci_msm_heads.lower()
    rc_select_seen = "rc_select" in pci_msm_find or "rc_select" in pci_msm_heads.lower()
    boot_option_seen = "boot_option" in pci_msm_find or "boot_option" in pci_msm_heads.lower()
    linkup_or_power_seen = any(token in pci_msm_find.lower() or token in pci_msm_heads.lower() for token in ("link", "power", "case", "testcase"))
    post_selftest_fail0 = "fail=0" in post_selftest

    if not mounted_during:
        decision = "v1363-debugfs-mount-unavailable"
        pass_condition = False
        reason = "debugfs was not mounted during the verifier window"
        next_step = "repair debugfs access before classifying pci-msm controls"
    elif not pci_msm_present:
        decision = "v1363-no-pci-msm-debugfs-surface"
        pass_condition = cleanup_ok and post_selftest_fail0
        reason = "debugfs mounted, but pci-msm debugfs is absent"
        next_step = "continue V1363 shim feasibility; no pci-msm debugfs userspace surface exists"
    elif enumerate_name_seen or rc_select_seen:
        decision = "v1363-pci-msm-debugfs-rc-control-candidate"
        pass_condition = cleanup_ok and post_selftest_fail0
        reason = "pci-msm debugfs exists and exposes enumerate/RC-selection-like read-only surface names"
        next_step = "V1364 host-only source/kallsyms contract for pci-msm debugfs RC1 control before any write"
    else:
        decision = "v1363-pci-msm-debugfs-present-no-enumerate-name"
        pass_condition = cleanup_ok and post_selftest_fail0
        reason = "pci-msm debugfs exists, but no enumerate or RC-select control name was found in read-only captures"
        next_step = "continue V1363 shim feasibility or classify listed pci-msm debugfs files if any are relevant"

    return {
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "next_step": next_step,
        "mounted_before": mounted_before,
        "mounted_by_v1363": mounted_by_v1363,
        "mounted_during": mounted_during,
        "mounted_after": mounted_after,
        "cleanup_ok": cleanup_ok,
        "pci_msm_present": pci_msm_present,
        "enumerate_name_seen": enumerate_name_seen,
        "rc_select_seen": rc_select_seen,
        "boot_option_seen": boot_option_seen,
        "linkup_or_power_seen": linkup_or_power_seen,
        "post_selftest_fail0": post_selftest_fail0,
        "safety": {
            "temporary_debugfs_mount_executed": mounted_by_v1363,
            "debugfs_write_executed": False,
            "sysfs_write_executed": False,
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
    return [[key, analysis.get(key)] for key in [
        "mounted_before",
        "mounted_by_v1363",
        "mounted_during",
        "mounted_after",
        "cleanup_ok",
        "pci_msm_present",
        "enumerate_name_seen",
        "rc_select_seen",
        "boot_option_seen",
        "linkup_or_power_seen",
        "post_selftest_fail0",
    ]]


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    return "\n".join([
        "# V1363 pci-msm Debugfs Surface Verifier",
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
        "# Native Init V1363 pci-msm Debugfs Surface Verifier Live",
        "",
        "## Summary",
        "",
        "- Cycle: `V1363`",
        "- Type: live read-only verifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_pci_msm_debugfs_surface_verifier_live_v1363.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1363-pci-msm-debugfs-surface-verifier-live/manifest.json`",
        "  - `tmp/wifi/v1363-pci-msm-debugfs-surface-verifier-live/summary.md`",
        "  - `tmp/wifi/v1363-pci-msm-debugfs-surface-verifier-live/native/`",
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
        "- V1363 may temporarily mount debugfs if it is absent, then unmount it before exit.",
        "- No debugfs/sysfs write, pci-msm debugfs control write, platform bind/unbind,",
        "  PCI rescan, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL,",
        "  scan/connect, credential handling, DHCP/routes, external ping, flash,",
        "  boot image write, or partition write.",
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
        "cycle": "V1363",
        "type": "live read-only verifier",
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
