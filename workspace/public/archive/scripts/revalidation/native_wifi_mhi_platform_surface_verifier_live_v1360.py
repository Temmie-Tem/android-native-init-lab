#!/usr/bin/env python3
"""V1360 live read-only MHI platform surface verifier."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1360-mhi-platform-surface-verifier-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1360-mhi-platform-surface-verifier-live.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1360_MHI_PLATFORM_SURFACE_VERIFIER_LIVE_2026-06-01.md")
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEBUGFS_ROOT = "/sys/kernel/debug"


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
        "cycle": "V1360",
        "type": "live read-only MHI platform surface verifier plan",
        "generated_at": now_iso(),
        "decision": "v1360-mhi-platform-surface-verifier-plan-ready",
        "pass": True,
        "reason": "plan-only; no device command executed",
        "next_step": "run V1360 live read-only MHI platform surface verifier",
        "scope": [
            "read live device-tree MHI nodes",
            "read platform and MHI bus sysfs surfaces",
            "temporarily mount debugfs only if absent, read MHI/PCI debugfs entries, then restore mount state",
            "read pcie1/MHI dmesg markers and post-health",
        ],
        "forbidden": [
            "platform bind/unbind",
            "PCI rescan",
            "debugfs/sysfs file writes",
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
    run_shell(args, store, steps, "dt-mhi-nodes", f"{args.toybox} find /sys/firmware/devicetree/base -name '*mhi*' 2>/dev/null || true", timeout=25.0)
    run_shell(args, store, steps, "dt-esoc0-refs", f"{args.toybox} find /sys/firmware/devicetree/base -name 'esoc-0' -o -name 'qcom,pcie-parent' -o -name 'qcom,wlan-rc-num' 2>/dev/null || true", timeout=25.0)
    run_shell(args, store, steps, "platform-mhi-devices", f"{args.toybox} ls -l /sys/bus/platform/devices 2>/dev/null | {args.busybox} grep -iE 'mhi|1c0b000|1c08000|pcie' || true", timeout=15.0)
    run_shell(args, store, steps, "platform-mhi-drivers", f"{args.toybox} ls -l /sys/bus/platform/drivers 2>/dev/null | {args.busybox} grep -iE 'mhi|pcie|pci-msm' || true", timeout=15.0)
    run_shell(args, store, steps, "platform-mhi-find", f"{args.toybox} find /sys/bus/platform -maxdepth 3 \\( -iname '*mhi*' -o -iname '*1c0b000*' -o -iname '*1c08000*' \\) 2>/dev/null || true", timeout=20.0)
    run_text(args, store, steps, "pcie1-platform-uevent", [args.toybox, "cat", "/sys/bus/platform/devices/1c08000.qcom,pcie/uevent"], timeout=10.0)
    run_text(args, store, steps, "pcie1-platform-driver-readlink", [args.toybox, "readlink", "/sys/bus/platform/devices/1c08000.qcom,pcie/driver"], timeout=10.0)
    run_shell(args, store, steps, "mhi-bus-tree", f"{args.toybox} find /sys/bus/mhi -maxdepth 3 -print 2>/dev/null || true", timeout=15.0)
    run_shell(args, store, steps, "mhi-bus-devices", f"{args.toybox} ls -l /sys/bus/mhi/devices 2>/dev/null || true", timeout=10.0)
    run_shell(args, store, steps, "mhi-bus-drivers", f"{args.toybox} ls -l /sys/bus/mhi/drivers 2>/dev/null || true", timeout=10.0)
    run_shell(args, store, steps, "pci-bus-devices", f"{args.toybox} find /sys/bus/pci/devices -maxdepth 2 -print 2>/dev/null || true", timeout=10.0)
    run_shell(args, store, steps, "dev-mhi-nodes", f"{args.toybox} ls -l /dev/mhi* /dev/mhi_* /dev/*mhi* 2>/dev/null || true", timeout=10.0)
    run_shell(args, store, steps, "class-mhi-surfaces", f"{args.toybox} find /sys/class -maxdepth 3 -iname '*mhi*' -print 2>/dev/null || true", timeout=15.0)
    run_shell(args, store, steps, "debugfs-mhi-find", f"{args.toybox} find {DEBUGFS_ROOT} -maxdepth 3 \\( -iname '*mhi*' -o -iname '*pcie*' -o -iname '*pci*' \\) 2>/dev/null || true", timeout=20.0)
    run_shell(args, store, steps, "debugfs-mhi-ls", f"{args.toybox} ls -l {DEBUGFS_ROOT}/mhi {DEBUGFS_ROOT}/mhi_netdev {DEBUGFS_ROOT}/pcie* {DEBUGFS_ROOT}/pci* 2>/dev/null || true", timeout=10.0)
    run_shell(args, store, steps, "proc-modules-mhi", f"{args.toybox} cat /proc/modules 2>/dev/null | {args.busybox} grep -iE 'mhi|pcie|pci|cnss|icnss|wlan' || true", timeout=10.0)
    run_shell(args, store, steps, "dmesg-pcie-mhi-tail", f"{args.toybox} dmesg | {args.busybox} grep -iE 'mhi|pcie|pci|icnss|cnss|qca|sdx|esoc|wlan' | {args.busybox} tail -240 || true", timeout=20.0)

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


def count_listing_entries(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("total"):
            continue
        count += 1
    return count


def count_find_children(text: str, root: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and stripped != root:
            count += 1
    return count


def analyze(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    mounts_before = step_text(store, steps, "mounts-before")
    mounts_during = step_text(store, steps, "mounts-during")
    mounts_after = step_text(store, steps, "mounts-after")
    dt_mhi = step_text(store, steps, "dt-mhi-nodes")
    dt_refs = step_text(store, steps, "dt-esoc0-refs")
    platform_devices = step_text(store, steps, "platform-mhi-devices")
    platform_drivers = step_text(store, steps, "platform-mhi-drivers")
    platform_find = step_text(store, steps, "platform-mhi-find")
    pcie1_driver = step_text(store, steps, "pcie1-platform-driver-readlink")
    mhi_bus_tree = step_text(store, steps, "mhi-bus-tree")
    mhi_bus_devices = step_text(store, steps, "mhi-bus-devices")
    mhi_bus_drivers = step_text(store, steps, "mhi-bus-drivers")
    pci_devices = step_text(store, steps, "pci-bus-devices")
    dev_mhi = step_text(store, steps, "dev-mhi-nodes")
    class_mhi = step_text(store, steps, "class-mhi-surfaces")
    debugfs_mhi_find = step_text(store, steps, "debugfs-mhi-find")
    debugfs_mhi_ls = step_text(store, steps, "debugfs-mhi-ls")
    dmesg = step_text(store, steps, "dmesg-pcie-mhi-tail")
    post_selftest = step_text(store, steps, "post-selftest")

    mounted_before = debugfs_mounted(mounts_before)
    mounted_during = debugfs_mounted(mounts_during)
    mounted_after = debugfs_mounted(mounts_after)
    mounted_by_v1360 = not mounted_before and command_ok(steps, "debugfs-mount")
    cleanup_ok = (mounted_after == mounted_before) if mounted_by_v1360 else True
    post_selftest_fail0 = "fail=0" in post_selftest

    dt_mhi_count = count_listing_entries(dt_mhi)
    dt_has_mhi_1c0b000 = "1c0b000" in dt_mhi or "qcom,mhi@0" in dt_mhi
    dt_has_esoc_ref = "esoc-0" in dt_refs
    platform_mhi_any = text_has_real_entries(platform_devices) or text_has_real_entries(platform_find)
    platform_driver_any = text_has_real_entries(platform_drivers)
    pcie1_bound_pci_msm = "pci-msm" in pcie1_driver
    mhi_bus_present = text_has_real_entries(mhi_bus_tree)
    mhi_bus_device_count = count_listing_entries(mhi_bus_devices)
    mhi_bus_driver_count = count_listing_entries(mhi_bus_drivers)
    pci_device_count = count_find_children(pci_devices, "/sys/bus/pci/devices")
    dev_mhi_count = count_listing_entries(dev_mhi)
    class_mhi_count = count_listing_entries(class_mhi)
    debugfs_mhi_any = text_has_real_entries(debugfs_mhi_find) or text_has_real_entries(debugfs_mhi_ls)
    dmesg_mhi_seen = "mhi" in dmesg.lower()
    dmesg_pcie_link_seen = any(token in dmesg for token in ("LTSSM_L0", "Current GEN", "PCIe RC1 PHY is ready"))

    if not mounted_during:
        decision = "v1360-debugfs-mount-unavailable"
        pass_condition = False
        reason = "debugfs was not mounted during the verifier window"
        next_step = "repair debugfs access before relying on MHI debugfs absence"
    elif mhi_bus_device_count > 0 or dev_mhi_count > 0:
        decision = "v1360-live-mhi-device-surface-present"
        pass_condition = cleanup_ok and post_selftest_fail0
        reason = "live MHI bus or /dev MHI nodes are present; classify ownership and safety before any action"
        next_step = "host-only classify the observed MHI device/control surface before mutation"
    elif platform_mhi_any or platform_driver_any or debugfs_mhi_any:
        decision = "v1360-mhi-surface-present-no-live-device"
        pass_condition = cleanup_ok and post_selftest_fail0
        reason = "MHI-related sysfs/debugfs surface exists, but no live MHI device node is present"
        next_step = "classify the MHI surface ownership and whether it is upstream or downstream of pcie1 enumeration"
    elif dt_mhi_count > 0 or dt_has_mhi_1c0b000 or dt_has_esoc_ref:
        decision = "v1360-mhi-dt-only-no-live-platform-surface"
        pass_condition = cleanup_ok and post_selftest_fail0
        reason = "MHI/eSoC topology exists in live DT, but no live MHI platform, bus, debugfs, or /dev control surface is exposed"
        next_step = "stop MHI userspace-control search; design next host-only pci-msm/pcie1 enumeration risk classifier"
    else:
        decision = "v1360-no-mhi-surface"
        pass_condition = cleanup_ok and post_selftest_fail0
        reason = "no MHI topology or live control surface was found in the collected read-only paths"
        next_step = "re-check DT/source mapping before any pcie1 mutation"

    return {
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "next_step": next_step,
        "mounted_before": mounted_before,
        "mounted_by_v1360": mounted_by_v1360,
        "mounted_during": mounted_during,
        "mounted_after": mounted_after,
        "cleanup_ok": cleanup_ok,
        "dt_mhi_count": dt_mhi_count,
        "dt_has_mhi_1c0b000": dt_has_mhi_1c0b000,
        "dt_has_esoc_ref": dt_has_esoc_ref,
        "platform_mhi_any": platform_mhi_any,
        "platform_driver_any": platform_driver_any,
        "pcie1_bound_pci_msm": pcie1_bound_pci_msm,
        "mhi_bus_present": mhi_bus_present,
        "mhi_bus_device_count": mhi_bus_device_count,
        "mhi_bus_driver_count": mhi_bus_driver_count,
        "pci_device_count": pci_device_count,
        "dev_mhi_count": dev_mhi_count,
        "class_mhi_count": class_mhi_count,
        "debugfs_mhi_any": debugfs_mhi_any,
        "dmesg_mhi_seen": dmesg_mhi_seen,
        "dmesg_pcie_link_seen": dmesg_pcie_link_seen,
        "post_selftest_fail0": post_selftest_fail0,
        "safety": {
            "temporary_debugfs_mount_executed": mounted_by_v1360,
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
    keys = [
        "mounted_before",
        "mounted_by_v1360",
        "mounted_during",
        "mounted_after",
        "cleanup_ok",
        "dt_mhi_count",
        "dt_has_mhi_1c0b000",
        "dt_has_esoc_ref",
        "platform_mhi_any",
        "platform_driver_any",
        "pcie1_bound_pci_msm",
        "mhi_bus_present",
        "mhi_bus_device_count",
        "mhi_bus_driver_count",
        "pci_device_count",
        "dev_mhi_count",
        "class_mhi_count",
        "debugfs_mhi_any",
        "dmesg_mhi_seen",
        "dmesg_pcie_link_seen",
        "post_selftest_fail0",
    ]
    return [[key, analysis.get(key)] for key in keys]


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    return "\n".join([
        "# V1360 MHI Platform Surface Verifier",
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
        "# Native Init V1360 MHI Platform Surface Verifier Live",
        "",
        "## Summary",
        "",
        "- Cycle: `V1360`",
        "- Type: live read-only verifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_mhi_platform_surface_verifier_live_v1360.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1360-mhi-platform-surface-verifier-live/manifest.json`",
        "  - `tmp/wifi/v1360-mhi-platform-surface-verifier-live/summary.md`",
        "  - `tmp/wifi/v1360-mhi-platform-surface-verifier-live/native/`",
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
        "- V1360 may temporarily mount debugfs if it is absent, then unmount it before exit.",
        "- No debugfs/sysfs file write, platform bind/unbind, PCI rescan, PMIC/GPIO/GDSC",
        "  write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, credential handling,",
        "  DHCP/routes, external ping, flash, boot image write, or partition write.",
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
        "cycle": "V1360",
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
