#!/usr/bin/env python3
"""V1357 live read-only pcie1 RC control-surface verifier."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1357-pcie1-rc-control-surface-verifier-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1357-pcie1-rc-control-surface-verifier-live.txt")
REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1357_PCIE1_RC_CONTROL_SURFACE_VERIFIER_LIVE_2026-06-01.md"
)
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
MAX_DYNAMIC_DT_READS = 24

FORBIDDEN_ACTIONS = [
    "sysfs/debugfs write",
    "platform bind/unbind",
    "PCI rescan",
    "cnss/dev_boot write",
    "PMIC/GPIO/GDSC write",
    "eSoC notify or BOOT_DONE",
    "Wi-Fi HAL start",
    "scan/connect",
    "credential use",
    "DHCP/routes",
    "external ping",
    "flash, boot image write, or partition write",
]


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


def read_step_text(store: EvidenceStore, step: dict[str, Any]) -> str:
    rel = str(step.get("file") or "")
    if not rel:
        return ""
    path = store.run_dir / rel
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def run_text_command(args: argparse.Namespace, store: EvidenceStore, name: str, words: list[str], timeout: float = 30.0) -> dict[str, Any]:
    return capture_native(args, store, name, ["run", *words], timeout=timeout)


def plan_manifest() -> dict[str, Any]:
    return {
        "cycle": "V1357",
        "type": "live read-only verifier plan",
        "generated_at": now_iso(),
        "decision": "v1357-pcie1-rc-control-surface-verifier-plan-ready",
        "pass": True,
        "reason": "plan-only; no device command executed",
        "next_step": "run the live read-only pcie1 RC surface verifier",
        "collections": [
            "native health",
            "pcie1 platform node and driver symlinks",
            "cnss/dev_boot presence and usage text if readable",
            "live devicetree qcom,wlan-rc-num and qcom,pcie-parent surfaces",
            "pcie1 GDSC/refclk/pipe/PERST/CLKREQ/WAKE baseline",
            "PCI/MHI device counts",
            "focused interrupt and dmesg evidence",
        ],
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def collect_run(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = [
        capture_native(args, store, "version", ["version"], timeout=10.0),
        capture_native(args, store, "status", ["status"], timeout=15.0),
        capture_native(args, store, "selftest", ["selftest", "verbose"], timeout=15.0),
        capture_native(args, store, "netservice-status", ["netservice", "status"], timeout=10.0),
        run_text_command(args, store, "proc-mounts", [args.toybox, "cat", "/proc/mounts"], timeout=10.0),
        run_text_command(args, store, "pcie1-platform-ls-soc", [args.toybox, "ls", "-l", "/sys/devices/platform/soc/1c08000.qcom,pcie"], timeout=10.0),
        run_text_command(args, store, "pcie1-platform-ls-bus", [args.toybox, "ls", "-l", "/sys/bus/platform/devices/1c08000.qcom,pcie"], timeout=10.0),
        run_text_command(args, store, "pcie1-platform-uevent", [args.toybox, "cat", "/sys/bus/platform/devices/1c08000.qcom,pcie/uevent"], timeout=10.0),
        run_text_command(args, store, "pcie1-platform-modalias", [args.toybox, "cat", "/sys/bus/platform/devices/1c08000.qcom,pcie/modalias"], timeout=10.0),
        run_text_command(args, store, "pcie1-platform-driver-readlink", [args.toybox, "readlink", "/sys/bus/platform/devices/1c08000.qcom,pcie/driver"], timeout=10.0),
        run_text_command(args, store, "pcie1-platform-power-runtime", [args.toybox, "cat", "/sys/bus/platform/devices/1c08000.qcom,pcie/power/runtime_status"], timeout=10.0),
        run_text_command(args, store, "pcie1-platform-power-control", [args.toybox, "cat", "/sys/bus/platform/devices/1c08000.qcom,pcie/power/control"], timeout=10.0),
        run_text_command(args, store, "platform-drivers-pcie-find", [args.toybox, "find", "/sys/bus/platform/drivers", "-maxdepth", "2", "-name", "*pcie*"], timeout=15.0),
        run_text_command(args, store, "debugfs-root-ls", [args.toybox, "ls", "-l", "/sys/kernel/debug"], timeout=10.0),
        run_text_command(args, store, "cnss-debugfs-ls", [args.toybox, "ls", "-l", "/sys/kernel/debug/cnss"], timeout=10.0),
        run_text_command(args, store, "cnss-dev-boot-read", [args.toybox, "cat", "/sys/kernel/debug/cnss/dev_boot"], timeout=10.0),
        run_text_command(args, store, "dt-pcie-find", [args.toybox, "find", "/sys/firmware/devicetree/base", "-maxdepth", "6", "-name", "*pcie*"], timeout=20.0),
        run_text_command(args, store, "dt-icnss-find", [args.toybox, "find", "/sys/firmware/devicetree/base", "-maxdepth", "6", "-name", "*icnss*"], timeout=20.0),
        run_text_command(args, store, "dt-cnss-find", [args.toybox, "find", "/sys/firmware/devicetree/base", "-maxdepth", "6", "-name", "*cnss*"], timeout=20.0),
        run_text_command(args, store, "dt-mhi-find", [args.toybox, "find", "/sys/firmware/devicetree/base", "-maxdepth", "6", "-name", "*mhi*"], timeout=20.0),
        run_text_command(args, store, "dt-mdm-find", [args.toybox, "find", "/sys/firmware/devicetree/base", "-maxdepth", "6", "-name", "*mdm*"], timeout=20.0),
        run_text_command(args, store, "dt-wlan-rc-num-find", [args.toybox, "find", "/sys/firmware/devicetree/base", "-name", "qcom,wlan-rc-num"], timeout=20.0),
        run_text_command(args, store, "dt-pcie-parent-find", [args.toybox, "find", "/sys/firmware/devicetree/base", "-name", "qcom,pcie-parent"], timeout=20.0),
        run_text_command(args, store, "regulator-pcie-grep", [args.busybox, "grep", "-iE", "pcie_1_gdsc|pcie_0_gdsc|pm8150l_l3|pm8150_l5|VDD_CX", "/sys/kernel/debug/regulator/regulator_summary", "/sys/kernel/debug/regulator_summary"], timeout=15.0),
        run_text_command(args, store, "clk-pcie-grep", [args.busybox, "grep", "-iE", "pcie_1|PCIE_1|pcie1|PCIE1|phy_refgen|clkref", "/sys/kernel/debug/clk/clk_summary"], timeout=15.0),
        run_text_command(args, store, "gpio-pcie-grep", [args.busybox, "grep", "-iE", "gpio-102|gpio102|GPIO102|gpio-103|gpio103|GPIO103|gpio-104|gpio104|GPIO104|gpio-135|gpio135|GPIO135|gpio-142|gpio142|GPIO142|1270|pm8150", "/sys/kernel/debug/gpio"], timeout=15.0),
        run_text_command(args, store, "pinctrl-pcie-find", [args.toybox, "find", "/sys/kernel/debug/pinctrl", "-maxdepth", "4", "-type", "f", "-name", "*pins"], timeout=15.0),
        run_text_command(args, store, "pci-devices-ls", [args.toybox, "ls", "-l", "/sys/bus/pci/devices"], timeout=10.0),
        run_text_command(args, store, "mhi-devices-ls", [args.toybox, "ls", "-l", "/sys/bus/mhi/devices"], timeout=10.0),
        run_text_command(args, store, "dev-mhi-ls", [args.busybox, "ls", "-l", "/dev/mhi*"], timeout=10.0),
        run_text_command(args, store, "proc-interrupts", [args.toybox, "cat", "/proc/interrupts"], timeout=10.0),
        run_text_command(args, store, "dmesg", [args.toybox, "dmesg"], timeout=20.0),
    ]

    dynamic_paths = []
    for step_name in ("dt-wlan-rc-num-find", "dt-pcie-parent-find"):
        step = next((item for item in steps if item.get("name") == step_name), None)
        if not step:
            continue
        for raw in read_step_text(store, step).splitlines():
            line = raw.strip()
            if line.startswith("/sys/firmware/devicetree/base/"):
                dynamic_paths.append(line)
    for index, path in enumerate(dynamic_paths[:MAX_DYNAMIC_DT_READS], start=1):
        steps.append(
            run_text_command(
                args,
                store,
                f"dt-dynamic-prop-{index:02d}",
                [args.busybox, "hexdump", "-C", path],
                timeout=10.0,
            )
        )

    steps.extend([
        capture_native(args, store, "post-selftest", ["selftest", "verbose"], timeout=15.0),
        capture_native(args, store, "post-status", ["status"], timeout=15.0),
    ])
    return steps


def extract_texts(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, str]:
    return {str(step.get("name")): read_step_text(store, step) for step in steps}


def command_ok(steps: list[dict[str, Any]], name: str) -> bool:
    for step in steps:
        if step.get("name") == name:
            return bool(step.get("ok"))
    return False


def count_listing_entries(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("total") and not stripped.startswith("[") and not stripped.startswith("cat:"):
            count += 1
    return count


def focused_lines(text: str, pattern: str, limit: int = 80) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    result = [line.strip() for line in text.splitlines() if regex.search(line)]
    return result[-limit:]


def analyze(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    texts = extract_texts(store, steps)
    proc_mounts = texts.get("proc-mounts", "")
    pcie_bus_ls = texts.get("pcie1-platform-ls-bus", "")
    pcie_soc_ls = texts.get("pcie1-platform-ls-soc", "")
    pcie_driver = texts.get("pcie1-platform-driver-readlink", "")
    cnss_ls = texts.get("cnss-debugfs-ls", "")
    cnss_dev_boot = texts.get("cnss-dev-boot-read", "")
    dt_wlan_find = texts.get("dt-wlan-rc-num-find", "")
    dt_pcie_parent_find = texts.get("dt-pcie-parent-find", "")
    regulator = texts.get("regulator-pcie-grep", "")
    clocks = texts.get("clk-pcie-grep", "")
    gpio = texts.get("gpio-pcie-grep", "")
    pci_ls = texts.get("pci-devices-ls", "")
    mhi_ls = texts.get("mhi-devices-ls", "")
    dev_mhi_ls = texts.get("dev-mhi-ls", "")
    interrupts = texts.get("proc-interrupts", "")
    dmesg = texts.get("dmesg", "")
    status = texts.get("status", "")
    post_status = texts.get("post-status", "")
    post_selftest = texts.get("post-selftest", "")

    debugfs_mounted = " debugfs " in proc_mounts or "/sys/kernel/debug debugfs" in proc_mounts
    pcie_platform_seen = command_ok(steps, "pcie1-platform-ls-bus") or command_ok(steps, "pcie1-platform-ls-soc")
    pcie_driver_bound = "No such file" not in pcie_driver and bool(pcie_driver.strip())
    cnss_dev_boot_present = command_ok(steps, "cnss-dev-boot-read") and "Usage: echo <action>" in cnss_dev_boot
    dev_boot_usage_enumerate = "enumerate: de-assert PERST, enumerate PCIe" in cnss_dev_boot
    dt_wlan_rc_paths = [line.strip() for line in dt_wlan_find.splitlines() if line.strip().startswith("/sys/")]
    dt_pcie_parent_paths = [line.strip() for line in dt_pcie_parent_find.splitlines() if line.strip().startswith("/sys/")]
    dynamic_hexdumps = {
        name: text
        for name, text in texts.items()
        if name.startswith("dt-dynamic-prop-") and text.strip()
    }
    rc1_hex_seen = any(re.search(r"\b00 00 00 01\b", text) for text in dynamic_hexdumps.values())
    rc0_hex_seen = any(re.search(r"\b00 00 00 00\b", text) for text in dynamic_hexdumps.values())
    pcie1_gdsc_seen = "pcie_1_gdsc" in regulator
    pcie1_gdsc_nonzero = "pcie_1_gdsc" in regulator and "0mV" not in regulator
    pcie1_clk_seen = bool(clocks.strip()) and "No such file" not in clocks
    perst_seen = any(token in gpio for token in ("gpio-102", "gpio102", "GPIO102"))
    pci_device_count = count_listing_entries(pci_ls)
    mhi_device_count = count_listing_entries(mhi_ls)
    mhi_devnode_seen = "/dev/mhi" in dev_mhi_ls and "No such file" not in dev_mhi_ls
    gpio142_lines = focused_lines(interrupts, r"gpio|mdm|142|err|fatal", limit=40)
    dmesg_focus = focused_lines(dmesg, r"pcie1|pcie 1|msm_pcie|ltssm|mhi|mdm|esoc|gpio142|wlfw|wlan0", limit=120)
    forbidden_runtime_clean = all(
        marker not in (status + "\n" + post_status).lower()
        for marker in ("wlan0 up", "dhcp", "external ping")
    )

    if cnss_dev_boot_present and dev_boot_usage_enumerate and rc1_hex_seen and not rc0_hex_seen:
        decision = "v1357-pcie1-rc-dev-boot-enumerate-candidate"
        next_step = "design V1358 bounded cnss/dev_boot enumerate-only experiment"
        reason = "cnss/dev_boot is present and live DT evidence suggests an RC1 mapping"
    elif cnss_dev_boot_present and dev_boot_usage_enumerate:
        decision = "v1357-cnss-dev-boot-present-rc-mapping-unproven"
        next_step = "classify live cnss/dev_boot RC mapping before any write"
        reason = "cnss/dev_boot exists, but V1357 did not prove that it targets pcie1/RC1"
    elif pcie_platform_seen:
        decision = "v1357-pcie1-platform-surface-only"
        next_step = "design a narrower platform-driver/RC1 entry proof or host-only reason why no safe userspace surface exists"
        reason = "pcie1 platform surface is visible, but no RC1-safe userspace enumerate surface is proven"
    else:
        decision = "v1357-no-safe-pcie1-rc-entry-surface"
        next_step = "stop mutation planning and classify why pcie1 platform/debugfs surfaces are absent"
        reason = "no safe live pcie1 RC control surface was found"

    pass_condition = command_ok(steps, "version") and command_ok(steps, "selftest") and "fail=0" in post_selftest
    return {
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "next_step": next_step,
        "debugfs_mounted": debugfs_mounted,
        "pcie_platform_seen": pcie_platform_seen,
        "pcie_driver_bound": pcie_driver_bound,
        "pcie_driver_readlink": pcie_driver.strip(),
        "cnss_debugfs_seen": command_ok(steps, "cnss-debugfs-ls"),
        "cnss_dev_boot_present": cnss_dev_boot_present,
        "dev_boot_usage_enumerate": dev_boot_usage_enumerate,
        "dt_wlan_rc_path_count": len(dt_wlan_rc_paths),
        "dt_pcie_parent_path_count": len(dt_pcie_parent_paths),
        "dt_dynamic_prop_read_count": len(dynamic_hexdumps),
        "dt_rc1_hex_seen": rc1_hex_seen,
        "dt_rc0_hex_seen": rc0_hex_seen,
        "pcie1_gdsc_seen": pcie1_gdsc_seen,
        "pcie1_gdsc_nonzero": pcie1_gdsc_nonzero,
        "pcie1_clk_seen": pcie1_clk_seen,
        "gpio102_perst_seen": perst_seen,
        "pci_device_count": pci_device_count,
        "mhi_device_count": mhi_device_count,
        "mhi_devnode_seen": mhi_devnode_seen,
        "post_selftest_fail0": "fail=0" in post_selftest,
        "forbidden_runtime_clean": forbidden_runtime_clean,
        "gpio142_interrupt_focus": gpio142_lines,
        "dmesg_focus": dmesg_focus,
        "safety": {
            "sysfs_debugfs_write_executed": False,
            "platform_bind_unbind_executed": False,
            "pci_rescan_executed": False,
            "cnss_dev_boot_write_executed": False,
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
        "debugfs_mounted",
        "pcie_platform_seen",
        "pcie_driver_bound",
        "pcie_driver_readlink",
        "cnss_debugfs_seen",
        "cnss_dev_boot_present",
        "dev_boot_usage_enumerate",
        "dt_wlan_rc_path_count",
        "dt_pcie_parent_path_count",
        "dt_dynamic_prop_read_count",
        "dt_rc1_hex_seen",
        "dt_rc0_hex_seen",
        "pcie1_gdsc_seen",
        "pcie1_gdsc_nonzero",
        "pcie1_clk_seen",
        "gpio102_perst_seen",
        "pci_device_count",
        "mhi_device_count",
        "mhi_devnode_seen",
        "post_selftest_fail0",
        "forbidden_runtime_clean",
    ]
    return [[key, analysis.get(key)] for key in keys]


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    return "\n".join(
        [
            "# V1357 pcie1 RC Control Surface Verifier",
            "",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            "",
            markdown_table(["field", "value"], key_rows(analysis)) if analysis else "",
            "",
        ]
    )


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    steps = manifest.get("steps") or []
    step_rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("status"), step.get("file")]
        for step in steps
    ]
    return "\n".join(
        [
            "# Native Init V1357 pcie1 RC Control Surface Verifier Live",
            "",
            "## Summary",
            "",
            "- Cycle: `V1357`",
            "- Type: live read-only verifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
            "- Script: `scripts/revalidation/native_wifi_pcie1_rc_control_surface_verifier_live_v1357.py`",
            "- Evidence:",
            "  - `tmp/wifi/v1357-pcie1-rc-control-surface-verifier-live/manifest.json`",
            "  - `tmp/wifi/v1357-pcie1-rc-control-surface-verifier-live/summary.md`",
            "  - `tmp/wifi/v1357-pcie1-rc-control-surface-verifier-live/native/`",
            "",
            "## Decision",
            "",
            manifest["reason"],
            "",
            "## Key Observations",
            "",
            markdown_table(["field", "value"], key_rows(analysis)) if analysis else "plan-only",
            "",
            "## Focused Interrupt Lines",
            "",
            "\n".join(f"- `{line}`" for line in analysis.get("gpio142_interrupt_focus", [])[:40]) if analysis else "",
            "",
            "## Focused dmesg Lines",
            "",
            "\n".join(f"- `{line}`" for line in analysis.get("dmesg_focus", [])[-80:]) if analysis else "",
            "",
            "## Captures",
            "",
            markdown_table(["name", "ok", "rc", "status", "file"], step_rows) if steps else "plan-only",
            "",
            "## Safety",
            "",
            "- Read-only command set only: `cat`, `ls`, `readlink`, `find`, `grep`,",
            "  `hexdump`, `dmesg`, plus native `version`/`status`/`selftest`.",
            "- No sysfs/debugfs write, platform bind/unbind, PCI rescan,",
            "  `cnss/dev_boot` write, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`,",
            "  Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external",
            "  ping, flash, boot image write, or partition write.",
            "",
            "## Next",
            "",
            manifest["next_step"],
            "",
        ]
    )


def write_outputs(store: EvidenceStore, manifest: dict[str, Any]) -> None:
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")


def main() -> int:
    args = parse_args()
    run_dir = repo_path(args.out_dir)
    store = EvidenceStore(run_dir)

    if args.command == "plan":
        manifest = plan_manifest()
        manifest["command"] = "plan"
        manifest["host"] = collect_host_metadata()
        write_outputs(store, manifest)
        print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(run_dir)}, indent=2))
        return 0

    if args.command == "reclassify":
        manifest_path = run_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["analysis"] = analyze(store, manifest.get("steps") or [])
        manifest["decision"] = manifest["analysis"]["decision"]
        manifest["pass"] = manifest["analysis"]["pass"]
        manifest["reason"] = manifest["analysis"]["reason"]
        manifest["next_step"] = manifest["analysis"]["next_step"]
        manifest["reclassified_at"] = now_iso()
        write_outputs(store, manifest)
        print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(run_dir)}, indent=2))
        return 0 if manifest["pass"] else 1

    steps = collect_run(args, store)
    analysis = analyze(store, steps)
    manifest = {
        "cycle": "V1357",
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
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }
    write_outputs(store, manifest)
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(run_dir)}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
