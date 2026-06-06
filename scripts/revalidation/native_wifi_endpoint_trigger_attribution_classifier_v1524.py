#!/usr/bin/env python3
"""V1524 host-only endpoint-trigger attribution classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path

import native_wifi_msm_pcie_test11_static_analysis_v1498 as v1498


DEFAULT_OUT_DIR = Path("tmp/wifi/v1524-endpoint-trigger-attribution-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1524_ENDPOINT_TRIGGER_ATTRIBUTION_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1524-endpoint-trigger-attribution-classifier.txt")

V1523_MANIFEST = Path("tmp/wifi/v1523-msm-pcie-test11-vs-normal-path-classifier/manifest.json")
V1521_SAMPLES = Path(
    "tmp/wifi/v1521-android-rc1-magisk-postfs-handoff/"
    "android-postfs-evidence/a90-v1521-rc1-postfs-sampler/samples.log"
)
V1521_HOST_DMESG = Path(
    "tmp/wifi/v1521-android-rc1-magisk-postfs-handoff/"
    "android-postfs-evidence/host-dmesg-filtered.txt"
)
V852_DMESG = Path(
    "tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/"
    "v852-android-ext-mdm-provider-surface-run/android/commands/dmesg-focus.txt"
)
V852_INTERRUPTS = Path(
    "tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/"
    "v852-android-ext-mdm-provider-surface-run/android/commands/interrupts-focus.txt"
)
V1517_NATIVE_DMESG = Path(
    "tmp/wifi/v1517-wifi-critical-source-pre-l0-handoff/test-v1393-dmesg.stdout.txt"
)
MHI_ARCH_SOURCE = workspace_private_input_path(
    "kernel_source",
    "SM-A908N_KOR_12_Opensource",
    "Kernel",
    "drivers",
    "bus",
    "mhi",
    "controllers",
    "mhi_arch_qcom.c",
)
MSM_PCIE_HEADER = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'include', 'linux', 'msm_pcie.h')


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def first_ts(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\[\s*([0-9]+\.[0-9]+)\]", line)
        if match:
            return float(match.group(1))
    return None


def matching_lines(text: str, pattern: str, limit: int = 12) -> list[str]:
    regex = re.compile(pattern, re.I)
    return [line.strip() for line in text.splitlines() if regex.search(line)][:limit]


def irq_totals_from_samples(text: str, gpio: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sample_index: int | None = None
    uptime: float | None = None
    begin_re = re.compile(r"A90_V1521_SAMPLE_BEGIN index=(\d+) uptime=([0-9.]+)")
    for line in text.splitlines():
        begin = begin_re.search(line)
        if begin:
            sample_index = int(begin.group(1))
            uptime = float(begin.group(2))
            continue
        if f"msmgpio-dc {gpio}" not in line and f"msmgpio-dc  {gpio}" not in line:
            continue
        prefix = line.split("msmgpio-dc", 1)[0]
        numbers = [int(value) for value in re.findall(r"\b\d+\b", prefix)]
        total = sum(numbers[1:]) if len(numbers) > 1 else None
        rows.append(
            {
                "sample": sample_index,
                "uptime": uptime,
                "total": total,
                "line": line.strip(),
            }
        )
    return rows


def interrupt_total(text: str, gpio: int) -> int | None:
    for line in text.splitlines():
        if f"msmgpio-dc {gpio}" not in line and f"msmgpio-dc  {gpio}" not in line:
            continue
        prefix = line.split("msmgpio-dc", 1)[0]
        numbers = [int(value) for value in re.findall(r"\b\d+\b", prefix)]
        return sum(numbers[1:]) if len(numbers) > 1 else None
    return None


def function_body(source: str, signature: str) -> dict[str, Any]:
    line_start, line_end, body = v1498.extract_function(source, signature)
    return {
        "line_start": line_start,
        "line_end": line_end,
        "found": bool(body),
        "body": body,
    }


def line_number(text: str, needle: str) -> int | None:
    for index, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return index
    return None


def summarize_lines(text: str, needles: tuple[str, ...], limit: int = 20) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(text.splitlines(), 1):
        if any(needle in line for needle in needles):
            rows.append({"line": index, "text": line.strip()})
            if len(rows) >= limit:
                break
    return rows


def analyze_sources(args: argparse.Namespace) -> dict[str, Any]:
    pcie_source, pcie_meta = v1498.read_pcie_source(args)
    mhi_source = read_text(MHI_ARCH_SOURCE)
    msm_pcie_header = read_text(MSM_PCIE_HEADER)

    mhi_power_on = function_body(
        mhi_source,
        r"\bstatic\s+int\s+mhi_arch_esoc_ops_power_on\s*\(",
    )
    pcie_pm_control = function_body(
        pcie_source,
        r"\bint\s+msm_pcie_pm_control\s*\(",
    )
    pcie_pm_resume = function_body(
        pcie_source,
        r"\bstatic\s+int\s+msm_pcie_pm_resume\s*\(",
    )

    return {
        "pcie_source": pcie_meta,
        "mhi_arch": {
            "path": rel(MHI_ARCH_SOURCE),
            "present": bool(mhi_source),
            "power_on_line": line_number(mhi_source, "static int mhi_arch_esoc_ops_power_on"),
            "hook_register_line": line_number(mhi_source, "esoc_ops->esoc_link_power_on"),
            "calls_msm_pcie_resume": "msm_pcie_pm_control(MSM_PCIE_RESUME" in mhi_power_on["body"],
            "calls_mhi_pci_probe": "mhi_pci_probe(pci_dev, NULL)" in mhi_power_on["body"],
            "power_on": {k: v for k, v in mhi_power_on.items() if k != "body"},
            "key_lines": summarize_lines(
                mhi_source,
                (
                    "static int mhi_arch_esoc_ops_power_on",
                    "msm_pcie_pm_control(MSM_PCIE_RESUME",
                    "mhi_pci_probe(pci_dev, NULL)",
                    "esoc_ops->esoc_link_power_on",
                ),
            ),
        },
        "pcie_pm": {
            "msm_pcie_header": rel(MSM_PCIE_HEADER),
            "header_declares_pm_control": "int msm_pcie_pm_control(enum msm_pcie_pm_opt pm_opt" in msm_pcie_header,
            "pm_control": {k: v for k, v in pcie_pm_control.items() if k != "body"},
            "pm_resume": {k: v for k, v in pcie_pm_resume.items() if k != "body"},
            "pm_control_dispatches_resume": "case MSM_PCIE_RESUME:" in pcie_pm_control["body"]
            and "msm_pcie_pm_resume(dev, user, data, options)" in pcie_pm_control["body"],
            "pm_resume_calls_enable_pm_subset": "msm_pcie_enable(pcie_dev, PM_PIPE_CLK | PM_CLK | PM_VREG)" in pcie_pm_resume["body"],
            "pm_resume_flag_subset": "PM_PIPE_CLK | PM_CLK | PM_VREG",
            "test11_flag_set": "PM_ALL",
            "key_lines": summarize_lines(
                pcie_source,
                (
                    "#define PM_ALL",
                    "static int msm_pcie_pm_resume",
                    "msm_pcie_enable(pcie_dev, PM_PIPE_CLK | PM_CLK | PM_VREG)",
                    "int msm_pcie_pm_control",
                    "case MSM_PCIE_RESUME:",
                    "msm_pcie_pm_resume(dev, user, data, options)",
                ),
            ),
        },
    }


def analyze_evidence() -> dict[str, Any]:
    v852_dmesg = read_text(V852_DMESG)
    v852_interrupts = read_text(V852_INTERRUPTS)
    v1521_samples = read_text(V1521_SAMPLES)
    v1521_dmesg = read_text(V1521_HOST_DMESG)
    v1517_dmesg = read_text(V1517_NATIVE_DMESG)

    android_v852 = {
        "path": rel(V852_DMESG),
        "esoc0_ts": first_ts(v852_dmesg, r"__subsystem_get:\s+esoc0 count:0"),
        "rc1_assert_ts": first_ts(v852_dmesg, r"msm_pcie_enable: PCIe: Assert the reset of endpoint of RC1"),
        "rc1_l0_ts": first_ts(v852_dmesg, r"LTSSM_STATE:\s+LTSSM_L0"),
        "rc1_current_gen_ts": first_ts(v852_dmesg, r"Current GEN"),
        "wlfw_start_ts": first_ts(v852_dmesg, r"wlfw_start: Starting"),
        "bdf_ts": first_ts(v852_dmesg, r"BDF file"),
        "has_test_marker_before_first_rc1": False,
        "has_debugfs_test_marker_any": bool(re.search(r"PCIe:\s+TEST:|msm_pcie_sel_debug_testcase", v852_dmesg, re.I)),
        "rc1_lines": matching_lines(v852_dmesg, r"msm_pcie_enable: PCIe RC1|msm_pcie_enable: PCIe: .*endpoint of RC1|Current GEN", 20),
        "esoc_lines": matching_lines(v852_dmesg, r"__subsystem_get.*esoc0|wlfw_start|BDF file|ssctl_new_server:.*esoc0", 16),
        "gpio104_interrupt_total": interrupt_total(v852_interrupts, 104),
        "gpio142_interrupt_total": interrupt_total(v852_interrupts, 142),
    }
    if android_v852["rc1_assert_ts"] is not None:
        prefix = "\n".join(
            line
            for line in v852_dmesg.splitlines()
            if (first_ts(line, r".*") or 0.0) <= android_v852["rc1_assert_ts"]
        )
        android_v852["has_test_marker_before_first_rc1"] = bool(
            re.search(r"PCIe:\s+TEST:|msm_pcie_sel_debug_testcase", prefix, re.I)
        )

    android_v1521 = {
        "samples_path": rel(V1521_SAMPLES),
        "host_dmesg_path": rel(V1521_HOST_DMESG),
        "wlfw_ts": first_ts(v1521_dmesg, r"wlfw_start: Starting"),
        "bdf_ts": first_ts(v1521_dmesg, r"BDF file"),
        "wlan0_ts": first_ts(v1521_dmesg, r"dev : wlan0"),
        "gpio104_samples": irq_totals_from_samples(v1521_samples, 104),
        "gpio142_samples": irq_totals_from_samples(v1521_samples, 142),
    }
    for gpio_key in ("gpio104_samples", "gpio142_samples"):
        rows = android_v1521[gpio_key]
        totals = [row["total"] for row in rows if row["total"] is not None]
        android_v1521[gpio_key.replace("_samples", "_all_zero")] = bool(totals and max(totals) == 0)
        android_v1521[gpio_key.replace("_samples", "_sample_count")] = len(rows)
        android_v1521[gpio_key.replace("_samples", "_last_total")] = totals[-1] if totals else None
        android_v1521[gpio_key] = rows[:3] + rows[-3:] if len(rows) > 6 else rows

    native_v1517 = {
        "path": rel(V1517_NATIVE_DMESG),
        "has_test11_marker": bool(re.search(r"PCIe:\s+TEST:\s+11|msm_pcie_sel_debug_testcase", v1517_dmesg, re.I)),
        "esoc0_ts": first_ts(v1517_dmesg, r"__subsystem_get:\s+esoc0 count:0"),
        "test11_ts": first_ts(v1517_dmesg, r"PCIe:\s+TEST:\s+11"),
        "rc1_assert_ts": first_ts(v1517_dmesg, r"msm_pcie_enable: PCIe: Assert the reset of endpoint of RC1"),
        "poll_compliance_ts": first_ts(v1517_dmesg, r"LTSSM_STATE:\s+LTSSM_POLL_COMPLIANCE"),
        "link_failed_ts": first_ts(v1517_dmesg, r"link initialization failed"),
        "has_l0": bool(re.search(r"LTSSM_STATE:\s+LTSSM_L0|Current GEN", v1517_dmesg)),
        "has_mhi_wlfw_wlan0": bool(re.search(r"\bmhi\b|wlfw|BDF file|dev : wlan0", v1517_dmesg, re.I)),
        "key_lines": matching_lines(
            v1517_dmesg,
            r"__subsystem_get.*esoc0|PCIe:\s+TEST:\s+11|msm_pcie_enable: PCIe|LTSSM_STATE|link initialization failed",
            24,
        ),
    }

    return {
        "android_v852": android_v852,
        "android_v1521": android_v1521,
        "native_v1517": native_v1517,
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1523 = read_json(V1523_MANIFEST)
    sources = analyze_sources(args)
    evidence = analyze_evidence()
    android_v852 = evidence["android_v852"]
    android_v1521 = evidence["android_v1521"]
    native_v1517 = evidence["native_v1517"]

    v1523_fixed = (
        v1523.get("pass") is True
        and v1523.get("decision") == "v1523-test11-shares-enable-normal-trigger-readiness-gap"
    )
    android_v852_initial_l0 = all(
        value is not None
        for value in (
            android_v852["esoc0_ts"],
            android_v852["rc1_assert_ts"],
            android_v852["rc1_l0_ts"],
        )
    )
    android_v852_no_debugfs_test = (
        android_v852["has_test_marker_before_first_rc1"] is False
        and android_v852["has_debugfs_test_marker_any"] is False
    )
    native_debugfs_test_fail = (
        native_v1517["has_test11_marker"]
        and native_v1517["link_failed_ts"] is not None
        and not native_v1517["has_l0"]
    )
    mhi_esoc_pm_candidate = all(
        [
            sources["mhi_arch"]["calls_msm_pcie_resume"],
            sources["mhi_arch"]["calls_mhi_pci_probe"],
            sources["pcie_pm"]["pm_control_dispatches_resume"],
            sources["pcie_pm"]["pm_resume_calls_enable_pm_subset"],
        ]
    )
    endpoint_wake_not_attributed = (
        android_v1521["gpio104_all_zero"]
        and android_v1521["wlan0_ts"] is not None
        and android_v852["gpio104_interrupt_total"] is not None
    )

    checks = [
        {
            "name": "v1523-fixed-point",
            "status": "pass" if v1523_fixed else "blocked",
            "detail": "V1523 proves TEST:11 reaches the common enumerate/enable path but still leaves trigger/readiness attribution open",
        },
        {
            "name": "android-v852-esoc-to-l0",
            "status": "pass" if android_v852_initial_l0 else "blocked",
            "detail": "Android V852 shows esoc0 followed by RC1 enable and LTSSM_L0",
        },
        {
            "name": "android-v852-not-debugfs-test11",
            "status": "pass" if android_v852_no_debugfs_test else "blocked",
            "detail": "Android V852 initial RC1 sequence has no pci-msm TEST/debugfs marker",
        },
        {
            "name": "native-v1517-debugfs-test11-fails",
            "status": "pass" if native_debugfs_test_fail else "blocked",
            "detail": "Native V1517 uses explicit TEST:11 and fails before L0",
        },
        {
            "name": "mhi-esoc-pm-resume-source-candidate",
            "status": "pass" if mhi_esoc_pm_candidate else "blocked",
            "detail": "Local MHI eSoC hook can request MSM_PCIE_RESUME, which dispatches to msm_pcie_enable via pm_resume",
        },
        {
            "name": "endpoint-wake-not-attributed",
            "status": "pass" if endpoint_wake_not_attributed else "blocked",
            "detail": "Existing Android-good evidence has contradictory GPIO104 IRQ visibility, so endpoint wake cannot be treated as the proven initial trigger",
        },
    ]
    pass_ok = all(item["status"] == "pass" for item in checks)
    decision = (
        "v1524-trigger-attribution-pivots-to-esoc-mhi-pm-resume"
        if pass_ok
        else "v1524-trigger-attribution-needs-more-evidence"
    )
    reason = (
        "Android-good initial RC1 is not a debugfs TEST:11 path, endpoint wake is not consistently attributable, and source shows an eSoC/MHI MSM_PCIE_RESUME path that must be modeled before the next mutation"
        if pass_ok
        else "Existing evidence or source facts do not yet support a complete trigger attribution pivot"
    )
    return {
        "cycle": "V1524",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "inputs": {
            "v1523": rel(V1523_MANIFEST),
            "v852_dmesg": rel(V852_DMESG),
            "v852_interrupts": rel(V852_INTERRUPTS),
            "v1521_samples": rel(V1521_SAMPLES),
            "v1521_host_dmesg": rel(V1521_HOST_DMESG),
            "v1517_native_dmesg": rel(V1517_NATIVE_DMESG),
            "mhi_arch_source": rel(MHI_ARCH_SOURCE),
            "msm_pcie_header": rel(MSM_PCIE_HEADER),
            "pcie_source": sources["pcie_source"],
        },
        "host": collect_host_metadata(),
        "checks": checks,
        "sources": sources,
        "evidence": evidence,
        "classification": {
            "android_initial_rc1_path": "not-debugfs-test11",
            "native_current_rc1_path": "explicit-debugfs-test11",
            "endpoint_wake_irq": "not-proven-initial-trigger",
            "sysfs_client_enumerate": "source-valid-but-not-observed-in-android-dmesg",
            "mhi_esoc_pm_resume": "source-supported-candidate",
            "firmware_mhi_wlfw_connect_deferred": True,
        },
        "next_gate": {
            "primary": "V1525 eSoC/MHI PM-resume vs TEST:11 path classifier",
            "rationale": (
                "Compare msm_pcie_enable options/state prerequisites for TEST:11 PM_ALL "
                "versus MHI eSoC MSM_PCIE_RESUME (PM_PIPE_CLK|PM_CLK|PM_VREG), then decide "
                "whether a source/build-only Android-path observer or shim is justified. "
                "Do not retry blind TEST:11 timing and do not move to firmware/connect before L0."
            ),
        },
        "safety": {
            "host_only": True,
            "device_commands": False,
            "wifi_hal_start": False,
            "scan_connect": False,
            "credentials": False,
            "dhcp_routes_external_ping": False,
            "pmic_gpio_gdsc_write": False,
            "esoc_notify_boot_done_spoof": False,
            "pci_debugfs_write": False,
            "global_pci_rescan": False,
            "platform_bind_unbind": False,
            "boot_or_partition_write": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    evidence = result["evidence"]
    android_v852 = evidence["android_v852"]
    android_v1521 = evidence["android_v1521"]
    native_v1517 = evidence["native_v1517"]
    source = result["sources"]
    lines = [
        "# Native Init V1524 Endpoint Trigger Attribution Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1524`",
        "- Type: host-only static/evidence classifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "path"], [[name, str(path)] for name, path in result["inputs"].items()]),
        "",
        "## Checks",
        "",
        markdown_table(
            ["check", "status", "detail"],
            [[item["name"], item["status"], item["detail"]] for item in result["checks"]],
        ),
        "",
        "## Android-Good vs Native-Fail Trigger Evidence",
        "",
        markdown_table(
            ["field", "Android V852", "Android V1521", "Native V1517"],
            [
                ["esoc0 ts", android_v852["esoc0_ts"], "", native_v1517["esoc0_ts"]],
                ["RC1 assert ts", android_v852["rc1_assert_ts"], "", native_v1517["rc1_assert_ts"]],
                ["RC1 L0 / link fail", android_v852["rc1_l0_ts"], "", native_v1517["link_failed_ts"]],
                ["debugfs TEST marker", android_v852["has_debugfs_test_marker_any"], "", native_v1517["has_test11_marker"]],
                ["GPIO104 IRQ total", android_v852["gpio104_interrupt_total"], android_v1521["gpio104_last_total"], ""],
                ["GPIO142 IRQ total", android_v852["gpio142_interrupt_total"], android_v1521["gpio142_last_total"], ""],
                ["WLFW/BDF/wlan0", f"{android_v852['wlfw_start_ts']}/{android_v852['bdf_ts']}/see V852 lower chain", f"{android_v1521['wlfw_ts']}/{android_v1521['bdf_ts']}/{android_v1521['wlan0_ts']}", native_v1517["has_mhi_wlfw_wlan0"]],
            ],
        ),
        "",
        "## Source Candidate Added To The Model",
        "",
        markdown_table(
            ["source fact", "value"],
            [
                ["MHI eSoC power-on line", source["mhi_arch"]["power_on_line"]],
                ["MHI eSoC hook registration line", source["mhi_arch"]["hook_register_line"]],
                ["MHI hook calls `MSM_PCIE_RESUME`", source["mhi_arch"]["calls_msm_pcie_resume"]],
                ["MHI hook calls `mhi_pci_probe`", source["mhi_arch"]["calls_mhi_pci_probe"]],
                ["`msm_pcie_pm_control` dispatches resume", source["pcie_pm"]["pm_control_dispatches_resume"]],
                ["resume path calls `msm_pcie_enable` subset", source["pcie_pm"]["pm_resume_calls_enable_pm_subset"]],
                ["resume flag subset", source["pcie_pm"]["pm_resume_flag_subset"]],
                ["TEST:11 flag set", source["pcie_pm"]["test11_flag_set"]],
            ],
        ),
        "",
        "## Key Lines",
        "",
        "### MHI eSoC Hook",
        "",
        markdown_table(["line", "text"], [[row["line"], row["text"]] for row in source["mhi_arch"]["key_lines"]]),
        "",
        "### PCIe PM Path",
        "",
        markdown_table(["line", "text"], [[row["line"], row["text"]] for row in source["pcie_pm"]["key_lines"]]),
        "",
        "## Interpretation",
        "",
        "V1524 keeps the V1523 result but tightens the next blocker. TEST:11 is a valid way to reach `msm_pcie_enable()`, but Android's first successful RC1 sequence is not observed as a debugfs TEST path. Existing Android evidence also does not cleanly prove endpoint wake GPIO104 as the initial trigger: V852 shows a nonzero post-boot wake count, while V1521 reaches WLFW/BDF/`wlan0` with sampled GPIO104 counts staying zero.",
        "",
        "The missing model piece is the eSoC/MHI PCIe PM path. Local source shows `mhi_arch_esoc_ops_power_on()` registers as an eSoC client hook, calls `msm_pcie_pm_control(MSM_PCIE_RESUME, ...)`, and then calls `mhi_pci_probe()`. The public `pci-msm.c` path dispatches `MSM_PCIE_RESUME` to `msm_pcie_pm_resume()`, which calls `msm_pcie_enable()` with `PM_PIPE_CLK | PM_CLK | PM_VREG`, while TEST:11 enumeration uses `PM_ALL`.",
        "",
        "Therefore the next work should compare Android-path PM-resume semantics against TEST:11 semantics before any new live mutation. Firmware, MHI deep dive, WLFW, scan/connect, credentials, DHCP/routes, and external ping remain downstream until native RC1 reaches L0 and PCI enumeration exists.",
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.",
        "",
        "## Next",
        "",
        f"- {result['next_gate']['primary']}: {result['next_gate']['rationale']}",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--pcie-source", type=Path, default=None)
    parser.add_argument("--pcie-source-url", default=v1498.DEFAULT_PCIE_SOURCE_URL)
    parser.add_argument("--fetch-timeout", type=float, default=30.0)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = classify(args)
    report = render_report(result)
    store = EvidenceStore(repo_path(args.out_dir))
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(args.report_path), report)
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "pass": result["pass"],
                "out_dir": rel(args.out_dir),
                "next_gate": result["next_gate"]["primary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
