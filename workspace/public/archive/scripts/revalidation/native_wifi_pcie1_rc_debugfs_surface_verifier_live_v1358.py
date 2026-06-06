#!/usr/bin/env python3
"""V1358 temporary-debugfs pcie1 RC control-surface verifier."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1358-pcie1-rc-debugfs-surface-verifier-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1358-pcie1-rc-debugfs-surface-verifier-live.txt")
REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1358_PCIE1_RC_DEBUGFS_SURFACE_VERIFIER_LIVE_2026-06-01.md"
)
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


def run_text(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], name: str, command: list[str], timeout: float = 15.0) -> None:
    steps.append(capture_native(args, store, name, ["run", *command], timeout=timeout))


def debugfs_mounted(text: str) -> bool:
    return re.search(rf"\s{re.escape(DEBUGFS_ROOT)}\s+debugfs\s", text) is not None


def plan_manifest() -> dict[str, Any]:
    return {
        "cycle": "V1358",
        "type": "temporary-debugfs live verifier plan",
        "generated_at": now_iso(),
        "decision": "v1358-pcie1-rc-debugfs-surface-verifier-plan-ready",
        "pass": True,
        "reason": "plan-only; no device command executed",
        "next_step": "run V1358 temporary-debugfs read-only verifier",
        "scope": [
            "temporary debugfs mount only if absent",
            "read cnss/dev_boot, cnss debugfs, pcie1 regulator/clock/gpio summaries",
            "unmount debugfs if V1358 mounted it",
        ],
        "forbidden": [
            "cnss/dev_boot write",
            "platform bind/unbind",
            "PCI rescan",
            "PMIC/GPIO/GDSC write",
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
    run_text(args, store, steps, "debugfs-root-ls", [args.toybox, "ls", "-l", DEBUGFS_ROOT], timeout=10.0)
    run_text(args, store, steps, "cnss-debugfs-ls", [args.toybox, "ls", "-l", f"{DEBUGFS_ROOT}/cnss"], timeout=10.0)
    run_text(args, store, steps, "cnss-dev-boot-read", [args.toybox, "cat", f"{DEBUGFS_ROOT}/cnss/dev_boot"], timeout=10.0)
    run_text(args, store, steps, "cnss-debugfs-find", [args.toybox, "find", f"{DEBUGFS_ROOT}/cnss", "-maxdepth", "2"], timeout=10.0)
    run_text(args, store, steps, "icnss-debugfs-ls", [args.toybox, "ls", "-l", f"{DEBUGFS_ROOT}/icnss"], timeout=10.0)
    run_text(args, store, steps, "icnss-debugfs-find", [args.toybox, "find", f"{DEBUGFS_ROOT}/icnss", "-maxdepth", "2"], timeout=10.0)
    run_text(args, store, steps, "icnss-stats-read", [args.toybox, "cat", f"{DEBUGFS_ROOT}/icnss/stats"], timeout=10.0)
    run_text(args, store, steps, "regulator-pcie-grep", [args.busybox, "grep", "-iE", "pcie_1_gdsc|pcie_0_gdsc|pm8150l_l3|pm8150_l5|VDD_CX", f"{DEBUGFS_ROOT}/regulator/regulator_summary", f"{DEBUGFS_ROOT}/regulator_summary"], timeout=15.0)
    run_text(args, store, steps, "clk-pcie-grep", [args.busybox, "grep", "-iE", "pcie_1|PCIE_1|pcie1|PCIE1|phy_refgen|clkref", f"{DEBUGFS_ROOT}/clk/clk_summary"], timeout=15.0)
    run_text(args, store, steps, "gpio-pcie-grep", [args.busybox, "grep", "-iE", "gpio-102|gpio102|GPIO102|gpio-103|gpio103|GPIO103|gpio-104|gpio104|GPIO104|gpio-135|gpio135|GPIO135|gpio-142|gpio142|GPIO142|1270|pm8150", f"{DEBUGFS_ROOT}/gpio"], timeout=15.0)
    run_text(args, store, steps, "pinctrl-pcie-find", [args.toybox, "find", f"{DEBUGFS_ROOT}/pinctrl", "-maxdepth", "4", "-type", "f", "-name", "*pins"], timeout=15.0)
    run_text(args, store, steps, "pcie1-platform-uevent", [args.toybox, "cat", "/sys/bus/platform/devices/1c08000.qcom,pcie/uevent"], timeout=10.0)
    run_text(args, store, steps, "pcie1-platform-driver-readlink", [args.toybox, "readlink", "/sys/bus/platform/devices/1c08000.qcom,pcie/driver"], timeout=10.0)
    run_text(args, store, steps, "dt-wlan-rc-num-find", [args.toybox, "find", "/sys/firmware/devicetree/base", "-name", "qcom,wlan-rc-num"], timeout=20.0)
    run_text(args, store, steps, "dt-pcie-parent-find", [args.toybox, "find", "/sys/firmware/devicetree/base", "-name", "qcom,pcie-parent"], timeout=20.0)
    run_text(args, store, steps, "pci-devices-ls", [args.toybox, "ls", "-l", "/sys/bus/pci/devices"], timeout=10.0)
    run_text(args, store, steps, "mhi-devices-ls", [args.toybox, "ls", "-l", "/sys/bus/mhi/devices"], timeout=10.0)
    run_text(args, store, steps, "proc-interrupts", [args.toybox, "cat", "/proc/interrupts"], timeout=10.0)

    if not mounted_before:
        run_text(args, store, steps, "debugfs-umount", [args.busybox, "umount", DEBUGFS_ROOT], timeout=15.0)
    run_text(args, store, steps, "mounts-after", [args.toybox, "cat", "/proc/mounts"], timeout=10.0)
    steps.extend([
        capture_native(args, store, "post-selftest", ["selftest", "verbose"], timeout=15.0),
        capture_native(args, store, "post-status", ["status"], timeout=15.0),
    ])
    return steps


def count_entries(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip() and not line.strip().startswith("total"))


def first_stat_line(text: str, prefix: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped
    return ""


def trailing_int(text: str, prefix: str) -> int:
    line = first_stat_line(text, prefix)
    if not line:
        return -1
    parts = line.split()
    for item in reversed(parts):
        try:
            return int(item, 0)
        except ValueError:
            continue
    return -1


def analyze(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    mounts_before = step_text(store, steps, "mounts-before")
    mounts_during = step_text(store, steps, "mounts-during")
    mounts_after = step_text(store, steps, "mounts-after")
    cnss_dev_boot = step_text(store, steps, "cnss-dev-boot-read")
    cnss_find = step_text(store, steps, "cnss-debugfs-find")
    icnss_ls = step_text(store, steps, "icnss-debugfs-ls")
    icnss_find = step_text(store, steps, "icnss-debugfs-find")
    icnss_stats = step_text(store, steps, "icnss-stats-read")
    regulator = step_text(store, steps, "regulator-pcie-grep")
    clocks = step_text(store, steps, "clk-pcie-grep")
    gpio = step_text(store, steps, "gpio-pcie-grep")
    pci_ls = step_text(store, steps, "pci-devices-ls")
    mhi_ls = step_text(store, steps, "mhi-devices-ls")
    post_selftest = step_text(store, steps, "post-selftest")

    mounted_before = debugfs_mounted(mounts_before)
    mounted_during = debugfs_mounted(mounts_during)
    mounted_after = debugfs_mounted(mounts_after)
    mounted_by_v1358 = not mounted_before and command_ok(steps, "debugfs-mount")
    cleanup_ok = (mounted_after == mounted_before) if mounted_by_v1358 else True
    cnss_dev_boot_present = command_ok(steps, "cnss-dev-boot-read") and "Usage: echo <action>" in cnss_dev_boot
    dev_boot_enumerate = "enumerate: de-assert PERST, enumerate PCIe" in cnss_dev_boot
    cnss_debugfs_any = bool(cnss_find.strip()) and "No such file" not in cnss_find
    icnss_debugfs_any = bool(icnss_find.strip()) and "No such file" not in icnss_find
    icnss_boot_wlan_seen = "boot_wlan" in icnss_ls or "boot_wlan" in icnss_find
    icnss_stats_readable = command_ok(steps, "icnss-stats-read") and bool(icnss_stats.strip())
    icnss_state_line = first_stat_line(icnss_stats, "State:")
    icnss_server_arrive = trailing_int(icnss_stats, "SERVER_ARRIVE")
    icnss_fw_ready = trailing_int(icnss_stats, "FW_READY")
    icnss_register_driver = trailing_int(icnss_stats, "REGISTER_DRIVER")
    pcie1_gdsc_seen = "pcie_1_gdsc" in regulator
    pcie1_gdsc_nonzero = pcie1_gdsc_seen and "0mV" not in regulator
    pcie_clk_seen = bool(clocks.strip()) and "No such file" not in clocks
    perst_seen = any(token in gpio for token in ("gpio-102", "gpio102", "GPIO102"))

    if not mounted_during:
        decision = "v1358-debugfs-mount-unavailable"
        pass_condition = False
        reason = "debugfs was not mounted during the verifier window"
        next_step = "inspect mount command and native debugfs support before any RC mutation"
    elif cnss_dev_boot_present and dev_boot_enumerate:
        decision = "v1358-cnss-dev-boot-present-rc-mapping-unproven"
        pass_condition = cleanup_ok and "fail=0" in post_selftest
        reason = "cnss/dev_boot is present after debugfs mount, but RC1 mapping is still unproven"
        next_step = "classify cnss/dev_boot backing device/RC mapping before any enumerate write"
    elif cnss_debugfs_any:
        decision = "v1358-cnss-debugfs-present-no-dev-boot"
        pass_condition = cleanup_ok and "fail=0" in post_selftest
        reason = "cnss debugfs exists after mount but dev_boot is absent"
        next_step = "treat cnss/dev_boot enumerate as unavailable and classify narrower pci-msm platform entry options"
    elif icnss_debugfs_any:
        decision = "v1358-icnss-debugfs-only-no-cnss-dev-boot"
        pass_condition = cleanup_ok and "fail=0" in post_selftest
        reason = "debugfs exposes ICNSS, not CNSS2 dev_boot; cnss/dev_boot enumerate is unavailable on this live kernel"
        next_step = "classify ICNSS/pci-msm platform entry options; do not use cnss/dev_boot"
    else:
        decision = "v1358-no-cnss-debugfs-surface"
        pass_condition = cleanup_ok and "fail=0" in post_selftest
        reason = "debugfs mounted and cleaned up, but no cnss or icnss debugfs surface appeared"
        next_step = "classify pci-msm platform driver userspace entry options; do not use cnss/dev_boot"

    return {
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "next_step": next_step,
        "mounted_before": mounted_before,
        "mounted_by_v1358": mounted_by_v1358,
        "mounted_during": mounted_during,
        "mounted_after": mounted_after,
        "cleanup_ok": cleanup_ok,
        "cnss_debugfs_any": cnss_debugfs_any,
        "cnss_dev_boot_present": cnss_dev_boot_present,
        "dev_boot_enumerate": dev_boot_enumerate,
        "icnss_debugfs_any": icnss_debugfs_any,
        "icnss_boot_wlan_seen": icnss_boot_wlan_seen,
        "icnss_stats_readable": icnss_stats_readable,
        "icnss_state_line": icnss_state_line,
        "icnss_server_arrive_count": icnss_server_arrive,
        "icnss_fw_ready_count": icnss_fw_ready,
        "icnss_register_driver_count": icnss_register_driver,
        "pcie1_gdsc_seen": pcie1_gdsc_seen,
        "pcie1_gdsc_nonzero": pcie1_gdsc_nonzero,
        "pcie_clk_seen": pcie_clk_seen,
        "gpio102_perst_seen": perst_seen,
        "pci_device_count": count_entries(pci_ls),
        "mhi_device_count": count_entries(mhi_ls),
        "post_selftest_fail0": "fail=0" in post_selftest,
        "safety": {
            "temporary_debugfs_mount_executed": mounted_by_v1358,
            "debugfs_write_executed": False,
            "cnss_dev_boot_write_executed": False,
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
        "mounted_by_v1358",
        "mounted_during",
        "mounted_after",
        "cleanup_ok",
        "cnss_debugfs_any",
        "cnss_dev_boot_present",
        "dev_boot_enumerate",
        "icnss_debugfs_any",
        "icnss_boot_wlan_seen",
        "icnss_stats_readable",
        "icnss_state_line",
        "icnss_server_arrive_count",
        "icnss_fw_ready_count",
        "icnss_register_driver_count",
        "pcie1_gdsc_seen",
        "pcie1_gdsc_nonzero",
        "pcie_clk_seen",
        "gpio102_perst_seen",
        "pci_device_count",
        "mhi_device_count",
        "post_selftest_fail0",
    ]]


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    return "\n".join([
        "# V1358 pcie1 RC Debugfs Surface Verifier",
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
        "# Native Init V1358 pcie1 RC Debugfs Surface Verifier Live",
        "",
        "## Summary",
        "",
        "- Cycle: `V1358`",
        "- Type: temporary-debugfs live verifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_pcie1_rc_debugfs_surface_verifier_live_v1358.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1358-pcie1-rc-debugfs-surface-verifier-live/manifest.json`",
        "  - `tmp/wifi/v1358-pcie1-rc-debugfs-surface-verifier-live/summary.md`",
        "  - `tmp/wifi/v1358-pcie1-rc-debugfs-surface-verifier-live/native/`",
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
        "- V1358 may temporarily mount debugfs if it is absent, then unmount it before exit.",
        "- No debugfs file write, `cnss/dev_boot` write, platform bind/unbind, PCI rescan,",
        "  PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect,",
        "  credential handling, DHCP/routes, external ping, flash, boot image write,",
        "  or partition write.",
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
        manifest["analysis"] = analyze(store, manifest.get("steps") or [])
        manifest["decision"] = manifest["analysis"]["decision"]
        manifest["pass"] = manifest["analysis"]["pass"]
        manifest["reason"] = manifest["analysis"]["reason"]
        manifest["next_step"] = manifest["analysis"]["next_step"]
        manifest["reclassified_at"] = now_iso()
        write_outputs(store, manifest)
        print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(store.run_dir)}, indent=2))
        return 0 if manifest["pass"] else 1

    steps = collect_run(args, store)
    analysis = analyze(store, steps)
    manifest = {
        "cycle": "V1358",
        "type": "temporary-debugfs live verifier",
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
