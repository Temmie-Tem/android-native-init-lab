#!/usr/bin/env python3
"""V1535 host-only classifier for native first-L0 trigger candidates."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

import native_wifi_msm_pcie_test11_static_analysis_v1498 as v1498


DEFAULT_OUT_DIR = Path("tmp/wifi/v1535-first-l0-trigger-candidate-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1535_FIRST_L0_TRIGGER_CANDIDATE_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1535-first-l0-trigger-candidate-classifier.txt")

PCIE_SOURCE = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c")
V852_DMESG = Path(
    "tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/"
    "v852-android-ext-mdm-provider-surface-run/android/commands/dmesg-focus.txt"
)
V1496_DMESG = Path("tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff/test-v1393-dmesg.stdout.txt")
V1517_DMESG = Path("tmp/wifi/v1517-wifi-critical-source-pre-l0-handoff/test-v1393-dmesg.stdout.txt")
V1527_GPIO_SAMPLES = Path(
    "tmp/wifi/v1527-android-initial-rc1-trigger-handoff/"
    "android-postfs-evidence/a90-v1527-rc1-trigger-sampler/irq-gpio-samples.log"
)
V1529_TRACE = Path(
    "tmp/wifi/v1529-android-tracefs-rc1-event-handoff/"
    "android-postfs-evidence/a90-v1529-tracefs-rc1-sampler/tracefs-events.txt"
)
V1532_TRACE = Path(
    "tmp/wifi/v1532-android-targeted-tracefs-queue-pair-handoff/"
    "android-postfs-evidence/a90-v1532-tracefs-queue-pair-sampler/tracefs-events.txt"
)

INPUTS = {
    "v1496": Path("tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff/manifest.json"),
    "v1517": Path("tmp/wifi/v1517-wifi-critical-source-pre-l0-handoff/manifest.json"),
    "v1523": Path("tmp/wifi/v1523-msm-pcie-test11-vs-normal-path-classifier/manifest.json"),
    "v1524": Path("tmp/wifi/v1524-endpoint-trigger-attribution-classifier/manifest.json"),
    "v1525": Path("tmp/wifi/v1525-mhi-pm-resume-position-classifier/manifest.json"),
    "v1527": Path("tmp/wifi/v1527-android-initial-rc1-trigger-handoff/manifest.json"),
    "v1529": Path("tmp/wifi/v1529-android-tracefs-rc1-event-handoff/manifest.json"),
    "v1532": Path("tmp/wifi/v1532-android-targeted-tracefs-queue-pair-handoff/manifest.json"),
    "v1533": Path("tmp/wifi/v1533-v1532-queue-pair-classifier/manifest.json"),
    "v1534": Path("tmp/wifi/v1534-pm-route-first-l0-focus-classifier/manifest.json"),
}


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


def matching_lines(text: str, pattern: str, limit: int = 16) -> list[str]:
    regex = re.compile(pattern, re.I)
    return [line.strip() for line in text.splitlines() if regex.search(line)][:limit]


def bool_path(data: dict[str, Any], *keys: str) -> bool:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return False
        current = current.get(key)
    return bool(current)


def function_summary(source: str, signature: str, needles: tuple[str, ...]) -> dict[str, Any]:
    line_start, line_end, body = v1498.extract_function(source, signature)
    key_lines: list[dict[str, Any]] = []
    if line_start is not None:
        for offset, line in enumerate(body.splitlines()):
            if any(needle in line for needle in needles):
                key_lines.append({"line": line_start + offset, "text": line.strip()})
    return {
        "line_start": line_start,
        "line_end": line_end,
        "found": bool(body),
        "key_lines": key_lines,
        "body": body,
    }


def source_lines(source: str, needles: tuple[str, ...], limit: int = 30) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(source.splitlines(), 1):
        if any(needle in line for needle in needles):
            rows.append({"line": index, "text": line.strip()})
        if len(rows) >= limit:
            break
    return rows


def irq_totals(text: str, gpio: int) -> list[int]:
    totals: list[int] = []
    for line in text.splitlines():
        if f"msmgpio-dc {gpio}" not in line and f"msmgpio-dc  {gpio}" not in line:
            continue
        prefix = line.split("msmgpio-dc", 1)[0]
        values = [int(value) for value in re.findall(r"\b\d+\b", prefix)]
        if len(values) > 1:
            totals.append(sum(values[1:]))
    return totals


def gpio_levels(text: str, gpio: int) -> list[int]:
    levels: list[int] = []
    regex = re.compile(rf"\bgpio{gpio}\s*:\s*(?:in|out)\s+([01])\b")
    for match in regex.finditer(text):
        levels.append(int(match.group(1)))
    return levels


def analyze_source() -> dict[str, Any]:
    source = read_text(PCIE_SOURCE)
    test11 = v1498.extract_switch_case(source, "MSM_PCIE_ENUMERATION")
    enumerate = function_summary(
        source,
        r"\bint\s+msm_pcie_enumerate\s*\(",
        ("msm_pcie_enable(dev, PM_ALL)", "pci_scan_root_bus", "dev->enumerated = true"),
    )
    sysfs_store = function_summary(
        source,
        r"\bstatic\s+ssize_t\s+msm_pcie_enumerate_store\s*\(",
        ("msm_pcie_enumerate(pcie_dev->rc_idx)",),
    )
    wake_irq = function_summary(
        source,
        r"\bstatic\s+irqreturn_t\s+handle_wake_irq\s*\(",
        ("MSM_PCIE_NO_WAKE_ENUMERATION", "schedule_work(&dev->handle_wake_work)", "Start enumerating"),
    )
    wake_work = function_summary(
        source,
        r"\bstatic\s+void\s+handle_wake_func\s*\(",
        ("Start enumeration", "msm_pcie_enumerate(dev->rc_idx)", "Linkup callback"),
    )
    probe = function_summary(
        source,
        r"\bstatic\s+int\s+msm_pcie_probe\s*\(",
        ("qcom,boot-option", "MSM_PCIE_NO_PROBE_ENUMERATION", "msm_pcie_enumerate(rc_idx)"),
    )
    return {
        "pcie_source": {
            "path": rel(PCIE_SOURCE),
            "present": bool(source),
            "sha256": v1498.sha256_text(source) if source else "",
        },
        "test11": {
            "case_line_start": test11["line_start"],
            "case_line_end": test11["line_end"],
            "calls_msm_pcie_enumerate": "msm_pcie_enumerate(dev->rc_idx)" in test11["body"],
        },
        "enumerate": {
            "line_start": enumerate["line_start"],
            "line_end": enumerate["line_end"],
            "found": enumerate["found"],
            "calls_msm_pcie_enable_pm_all": "msm_pcie_enable(dev, PM_ALL)" in enumerate["body"],
            "calls_pci_scan": "pci_scan_root_bus" in enumerate["body"],
            "sets_enumerated": "dev->enumerated = true" in enumerate["body"],
            "key_lines": enumerate["key_lines"],
        },
        "sysfs_enumerate": {
            "line_start": sysfs_store["line_start"],
            "line_end": sysfs_store["line_end"],
            "found": sysfs_store["found"],
            "calls_msm_pcie_enumerate": "msm_pcie_enumerate(pcie_dev->rc_idx)" in sysfs_store["body"],
            "key_lines": sysfs_store["key_lines"],
        },
        "endpoint_wake": {
            "irq_line_start": wake_irq["line_start"],
            "irq_line_end": wake_irq["line_end"],
            "work_line_start": wake_work["line_start"],
            "work_line_end": wake_work["line_end"],
            "irq_found": wake_irq["found"],
            "work_found": wake_work["found"],
            "wake_enum_allowed_by_code": "MSM_PCIE_NO_WAKE_ENUMERATION" in wake_irq["body"]
            and "schedule_work(&dev->handle_wake_work)" in wake_irq["body"],
            "work_calls_msm_pcie_enumerate": "msm_pcie_enumerate(dev->rc_idx)" in wake_work["body"],
            "key_lines": wake_irq["key_lines"] + wake_work["key_lines"],
        },
        "probe": {
            "line_start": probe["line_start"],
            "line_end": probe["line_end"],
            "found": probe["found"],
            "checks_no_probe_enum": "MSM_PCIE_NO_PROBE_ENUMERATION" in probe["body"],
            "calls_msm_pcie_enumerate": "msm_pcie_enumerate(rc_idx)" in probe["body"],
            "key_lines": probe["key_lines"],
        },
        "callsite_lines": source_lines(
            source,
            (
                "case MSM_PCIE_ENUMERATION:",
                "msm_pcie_enumerate(dev->rc_idx)",
                "msm_pcie_enumerate(pcie_dev->rc_idx)",
                "msm_pcie_enumerate(rc_idx)",
                "EXPORT_SYMBOL(msm_pcie_enumerate)",
                "MSM_PCIE_NO_PROBE_ENUMERATION",
                "MSM_PCIE_NO_WAKE_ENUMERATION",
                "Start enumeration for RC%d upon the wake",
            ),
        ),
    }


def analyze_evidence() -> dict[str, Any]:
    v852_dmesg = read_text(V852_DMESG)
    v1496_dmesg = read_text(V1496_DMESG)
    v1517_dmesg = read_text(V1517_DMESG)
    v1527_samples = read_text(V1527_GPIO_SAMPLES)
    v1529_trace = read_text(V1529_TRACE)
    v1532_trace = read_text(V1532_TRACE)
    v1527_gpio104_irqs = irq_totals(v1527_samples, 104)
    v1527_gpio142_irqs = irq_totals(v1527_samples, 142)
    v1527_gpio135_levels = gpio_levels(v1527_samples, 135)
    v1527_gpio142_levels = gpio_levels(v1527_samples, 142)
    return {
        "android_v852": {
            "path": rel(V852_DMESG),
            "wlfw_start_ts": first_ts(v852_dmesg, r"wlfw_start: Starting"),
            "esoc0_ts": first_ts(v852_dmesg, r"__subsystem_get.*esoc0 count:0"),
            "rc1_assert_ts": first_ts(v852_dmesg, r"Assert the reset of endpoint of RC1"),
            "rc1_release_ts": first_ts(v852_dmesg, r"Release the reset of endpoint of RC1"),
            "rc1_l0_ts": first_ts(v852_dmesg, r"LTSSM_STATE:\s+LTSSM_L0"),
            "rc1_gen_ts": first_ts(v852_dmesg, r"Current GEN"),
            "bdf_ts": first_ts(v852_dmesg, r"BDF file"),
            "wlan0_ts": first_ts(v852_dmesg, r"dev : wlan0"),
            "has_debugfs_test_marker": bool(re.search(r"PCIe:\s+TEST:|msm_pcie_sel_debug_testcase", v852_dmesg, re.I)),
            "key_lines": matching_lines(
                v852_dmesg,
                r"__subsystem_get.*esoc0|wlfw_start|Assert the reset of endpoint of RC1|Release the reset of endpoint of RC1|LTSSM_STATE|Current GEN|BDF file|dev : wlan0",
                28,
            ),
        },
        "native_v1496": {
            "path": rel(V1496_DMESG),
            "has_rc1_progress": bool(re.search(r"PCIe RC1|LTSSM_STATE", v1496_dmesg)),
            "has_l0": bool(re.search(r"LTSSM_STATE:\s+LTSSM_L0|Current GEN", v1496_dmesg)),
            "has_link_failed": bool(re.search(r"link initialization failed", v1496_dmesg, re.I)),
            "key_lines": matching_lines(
                v1496_dmesg,
                r"PCIe:\s+TEST|msm_pcie_enable: PCIe|LTSSM_STATE|link initialization failed|dev : wlan0|BDF file|FW ready",
                24,
            ),
        },
        "native_v1517": {
            "path": rel(V1517_DMESG),
            "has_test11": bool(re.search(r"PCIe:\s+TEST:\s+11|msm_pcie_sel_debug_testcase", v1517_dmesg, re.I)),
            "has_rc1_progress": bool(re.search(r"PCIe RC1|LTSSM_STATE", v1517_dmesg)),
            "has_l0": bool(re.search(r"LTSSM_STATE:\s+LTSSM_L0|Current GEN", v1517_dmesg)),
            "has_link_failed": bool(re.search(r"link initialization failed", v1517_dmesg, re.I)),
            "has_mhi_wlfw_wlan0": bool(re.search(r"\bmhi\b|wlfw|BDF file|dev : wlan0", v1517_dmesg, re.I)),
            "key_lines": matching_lines(
                v1517_dmesg,
                r"__subsystem_get.*esoc0|PCIe:\s+TEST|msm_pcie_enable: PCIe|LTSSM_STATE|link initialization failed|dev : wlan0|BDF file|FW ready",
                28,
            ),
        },
        "android_v1527_samples": {
            "path": rel(V1527_GPIO_SAMPLES),
            "gpio104_irq_samples": len(v1527_gpio104_irqs),
            "gpio104_irq_max": max(v1527_gpio104_irqs) if v1527_gpio104_irqs else None,
            "gpio142_irq_samples": len(v1527_gpio142_irqs),
            "gpio142_irq_max": max(v1527_gpio142_irqs) if v1527_gpio142_irqs else None,
            "gpio135_level_samples": len(v1527_gpio135_levels),
            "gpio135_level_max": max(v1527_gpio135_levels) if v1527_gpio135_levels else None,
            "gpio142_level_samples": len(v1527_gpio142_levels),
            "gpio142_level_max": max(v1527_gpio142_levels) if v1527_gpio142_levels else None,
        },
        "android_tracefs": {
            "v1529_path": rel(V1529_TRACE),
            "v1532_path": rel(V1532_TRACE),
            "v1529_has_rc1_text": bool(re.search(r"RC1|LTSSM|msm_pcie", v1529_trace, re.I)),
            "v1532_has_rc1_text": bool(re.search(r"RC1|LTSSM|msm_pcie", v1532_trace, re.I)),
            "v1529_has_irq_events": bool(re.search(r"\birq_handler_entry\b|\birq_handler_exit\b", v1529_trace)),
            "v1532_has_irq_events": bool(re.search(r"\birq_handler_entry\b|\birq_handler_exit\b", v1532_trace)),
            "v1532_has_icnss_workqueue": "icnss_driver_event_work" in v1532_trace,
        },
    }


def candidate_table(result: dict[str, Any]) -> list[dict[str, str]]:
    src = result["source"]
    evidence = result["evidence"]
    candidates = [
        {
            "candidate": "current PM/eSoC route",
            "status": "closed as active gap",
            "basis": "V1534 proves current route reaches pm-service/esoc0 and mdm_subsys_powerup; remaining failure is below provider entry.",
        },
        {
            "candidate": "debugfs TEST:11 enumerate",
            "status": "known native fail",
            "basis": "V1496/V1517 reach RC1/LTSSM through TEST:11 but fail before L0.",
        },
        {
            "candidate": "MHI PM-resume",
            "status": "closed downstream",
            "basis": "V1525 places MHI PM-resume after first L0/PCI device creation.",
        },
        {
            "candidate": "ICNSS workqueue",
            "status": "closed non-trigger",
            "basis": "V1533 pairs visible icnss_driver_event_work with macloader driver load, not first L0.",
        },
        {
            "candidate": "probe-time enumeration",
            "status": "not active on this board",
            "basis": "V1523/source shows pcie1 qcom,boot-option defers probe enumeration.",
        },
        {
            "candidate": "endpoint wake GPIO104",
            "status": "source-valid but evidence-weak",
            "basis": (
                "pci-msm wake work can call msm_pcie_enumerate, but V1527 GPIO104 samples stay zero "
                "and V1529/V1532 tracefs exposes no IRQ/RC1 text."
            ),
        },
        {
            "candidate": "sysfs/client enumerate",
            "status": "only remaining AP-side testable trigger",
            "basis": (
                "source-valid caller into the same msm_pcie_enumerate path; Android does not log the caller, "
                "so a bounded rollbackable test can empirically close it."
            ),
        },
        {
            "candidate": "endpoint electrical/readiness",
            "status": "primary technical blocker if client enumerate also fails",
            "basis": "Native can drive LTSSM to polling/compliance but endpoint never reaches L0.",
        },
    ]
    if not src["sysfs_enumerate"]["calls_msm_pcie_enumerate"]:
        candidates[-2]["status"] = "blocked-source-missing"
    if evidence["android_v1527_samples"]["gpio104_irq_max"] not in (0, None):
        candidates[-3]["status"] = "needs-review"
    return candidates


def classify() -> dict[str, Any]:
    manifests = {name: read_json(path) for name, path in INPUTS.items()}
    source = analyze_source()
    evidence = analyze_evidence()
    v1496_wp = manifests["v1496"].get("wifi_progress") or {}
    v1517_wp = manifests["v1517"].get("wifi_progress") or {}
    android = evidence["android_v852"]
    native1517 = evidence["native_v1517"]
    samples = evidence["android_v1527_samples"]
    tracefs = evidence["android_tracefs"]

    checks = {
        "v1534-first-l0-focus-fixed": manifests["v1534"].get("decision")
        == "v1534-current-pm-route-supersedes-old-gap-first-l0-focus",
        "v1496-native-rc1-progress-no-l0": bool(v1496_wp.get("rc1_progress"))
        and not bool(v1496_wp.get("rc1_l0"))
        and bool(v1496_wp.get("rc1_link_failed")),
        "v1517-native-rc1-progress-no-l0": bool(v1517_wp.get("rc1_progress"))
        and not bool(v1517_wp.get("rc1_l0")),
        "v1523-common-enumerate-fixed": manifests["v1523"].get("decision")
        == "v1523-test11-shares-enable-normal-trigger-readiness-gap",
        "v1525-mhi-pm-resume-closed": manifests["v1525"].get("decision")
        == "v1525-mhi-pm-resume-is-post-enumeration-not-first-l0-trigger",
        "v1533-icnss-workqueue-closed": manifests["v1533"].get("decision")
        == "v1533-icnss-queue-pair-is-hdd-register-path-not-first-l0-trigger",
        "android-good-initial-l0-reference": android["esoc0_ts"] is not None
        and android["rc1_l0_ts"] is not None
        and not android["has_debugfs_test_marker"],
        "native-test11-fails-before-l0": native1517["has_test11"]
        and native1517["has_link_failed"]
        and not native1517["has_l0"],
        "source-normal-callers-present": source["test11"]["calls_msm_pcie_enumerate"]
        and source["enumerate"]["calls_msm_pcie_enable_pm_all"]
        and source["sysfs_enumerate"]["calls_msm_pcie_enumerate"]
        and source["endpoint_wake"]["work_calls_msm_pcie_enumerate"],
        "android-wake-irq-not-proven": samples["gpio104_irq_max"] == 0
        and not tracefs["v1529_has_irq_events"]
        and not tracefs["v1532_has_irq_events"],
    }
    pass_ok = all(checks.values())
    result: dict[str, Any] = {
        "cycle": "V1535",
        "generated_at": now_iso(),
        "decision": (
            "v1535-first-l0-candidates-narrowed-to-client-enumerate-or-endpoint-readiness"
            if pass_ok
            else "v1535-first-l0-candidates-need-review"
        ),
        "pass": pass_ok,
        "reason": (
            "PM route, MHI PM-resume, ICNSS workqueue, probe enumeration, and repeated TEST:11 are closed as immediate first-L0 leads; only sysfs/client enumerate remains as an AP-side empirical check before endpoint readiness/electrical focus"
            if pass_ok
            else "one or more fixed points did not match the expected first-L0 candidate model"
        ),
        "inputs": {name: rel(path) for name, path in INPUTS.items()}
        | {
            "pcie_source": rel(PCIE_SOURCE),
            "android_v852_dmesg": rel(V852_DMESG),
            "native_v1496_dmesg": rel(V1496_DMESG),
            "native_v1517_dmesg": rel(V1517_DMESG),
            "android_v1527_gpio_samples": rel(V1527_GPIO_SAMPLES),
            "android_v1529_tracefs": rel(V1529_TRACE),
            "android_v1532_tracefs": rel(V1532_TRACE),
        },
        "host": collect_host_metadata(),
        "checks": checks,
        "source": source,
        "evidence": evidence,
        "classification": {
            "active_blocker": "PCIe RC1 LTSSM progresses but no L0 / no PCI device / no MHI / no WLFW / no wlan0",
            "closed_first_l0_leads": [
                "old PM dependency/actionability gap",
                "MHI PM-resume",
                "visible ICNSS workqueue",
                "probe-time enumeration",
                "blind repeated debugfs TEST:11 timing retry",
            ],
            "remaining_ap_side_candidate": "targeted sysfs/client enumerate path into msm_pcie_enumerate",
            "dominant_if_ap_side_candidate_fails": "endpoint readiness/electrical/reset/refclk/PERST response gap",
            "firmware_mhi_wlfw_scan_connect_deferred_until_native_l0": True,
        },
        "safety": {
            "host_only_classifier": True,
            "device_commands_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "esoc_notify_boot_done_spoof_executed": False,
            "pci_debugfs_write_executed": False,
            "global_pci_rescan_executed": False,
            "platform_bind_unbind_executed": False,
            "boot_or_partition_write_executed": False,
        },
        "next_gate": {
            "cycle": "V1536",
            "summary": "source/build-only rollbackable test-boot variant that replaces debugfs TEST:11 with the targeted pci-msm sysfs/client enumerate entry, then samples the same RC1/LTSSM/L0 outcome",
            "guardrails": [
                "target only the pci-msm RC1 enumerate sysfs/client entry; no global PCI rescan",
                "no platform bind/unbind",
                "no Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, or external ping",
                "no PMIC/GPIO/GDSC direct writes and no eSoC notify/BOOT_DONE spoof",
                "rollbackable handoff with native selftest verification before any live run",
            ],
        },
    }
    result["candidates"] = candidate_table(result)
    return result


def render_report(result: dict[str, Any]) -> str:
    evidence = result["evidence"]
    android = evidence["android_v852"]
    native1496 = evidence["native_v1496"]
    native1517 = evidence["native_v1517"]
    samples = evidence["android_v1527_samples"]
    source = result["source"]
    return "\n".join(
        [
            "# Native Init V1535 First-L0 Trigger Candidate Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1535`",
            "- Type: host-only evidence/source classifier",
            f"- Decision: `{result['decision']}`",
            f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
            f"- Reason: {result['reason']}",
            "",
            "## Inputs",
            "",
            markdown_table(["input", "path"], [[name, str(path)] for name, path in result["inputs"].items()]),
            "",
            "## Fixed-Point Checks",
            "",
            markdown_table(["check", "value"], [[name, value] for name, value in result["checks"].items()]),
            "",
            "## Candidate Classification",
            "",
            markdown_table(
                ["candidate", "status", "basis"],
                [[row["candidate"], row["status"], row["basis"]] for row in result["candidates"]],
            ),
            "",
            "## Android-Good vs Native-Fail Evidence",
            "",
            markdown_table(
                ["field", "Android V852", "Native V1496", "Native V1517"],
                [
                    ["RC1 progress", android["rc1_assert_ts"], native1496["has_rc1_progress"], native1517["has_rc1_progress"]],
                    ["RC1 L0", android["rc1_l0_ts"], native1496["has_l0"], native1517["has_l0"]],
                    ["link failed", "", native1496["has_link_failed"], native1517["has_link_failed"]],
                    ["debugfs TEST marker", android["has_debugfs_test_marker"], "", native1517["has_test11"]],
                    ["MHI/WLFW/wlan0", f"{android['bdf_ts']}/{android['wlan0_ts']}", "", native1517["has_mhi_wlfw_wlan0"]],
                ],
            ),
            "",
            "## Android GPIO/Tracefs Visibility",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["V1527 GPIO104 IRQ samples/max", f"{samples['gpio104_irq_samples']}/{samples['gpio104_irq_max']}"],
                    ["V1527 GPIO142 IRQ samples/max", f"{samples['gpio142_irq_samples']}/{samples['gpio142_irq_max']}"],
                    ["V1527 GPIO135 level samples/max", f"{samples['gpio135_level_samples']}/{samples['gpio135_level_max']}"],
                    ["V1527 GPIO142 level samples/max", f"{samples['gpio142_level_samples']}/{samples['gpio142_level_max']}"],
                    ["V1529 tracefs has RC1 text", evidence["android_tracefs"]["v1529_has_rc1_text"]],
                    ["V1532 tracefs has RC1 text", evidence["android_tracefs"]["v1532_has_rc1_text"]],
                    ["V1529 tracefs has IRQ events", evidence["android_tracefs"]["v1529_has_irq_events"]],
                    ["V1532 tracefs has IRQ events", evidence["android_tracefs"]["v1532_has_irq_events"]],
                ],
            ),
            "",
            "## Source Facts",
            "",
            markdown_table(
                ["fact", "value"],
                [
                    ["pcie source", source["pcie_source"]["path"]],
                    ["TEST:11 calls enumerate", source["test11"]["calls_msm_pcie_enumerate"]],
                    ["enumerate calls PM_ALL enable", source["enumerate"]["calls_msm_pcie_enable_pm_all"]],
                    ["enumerate calls PCI scan", source["enumerate"]["calls_pci_scan"]],
                    ["sysfs enumerate calls enumerate", source["sysfs_enumerate"]["calls_msm_pcie_enumerate"]],
                    ["endpoint wake work calls enumerate", source["endpoint_wake"]["work_calls_msm_pcie_enumerate"]],
                    ["probe checks no-probe enum", source["probe"]["checks_no_probe_enum"]],
                ],
            ),
            "",
            "## Key Android V852 Lines",
            "",
            "\n".join(f"- `{line}`" for line in android["key_lines"]),
            "",
            "## Key Native V1517 Lines",
            "",
            "\n".join(f"- `{line}`" for line in native1517["key_lines"]),
            "",
            "## Key pci-msm Callsite Lines",
            "",
            markdown_table(["line", "text"], [[row["line"], row["text"]] for row in source["callsite_lines"]]),
            "",
            "## Interpretation",
            "",
            "V1535 keeps the active blocker at first L0. PM-service/eSoC actionability is no longer the lowest blocker, and MHI, WLFW, BDF, firmware inventory, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain downstream until native RC1 reaches L0 and a PCI device exists.",
            "",
            "The only AP-side trigger still worth an empirical close-out is the targeted sysfs/client enumerate entry into `msm_pcie_enumerate()`. The source says it converges on the same common enumerate function as TEST:11, so a failure there would move the next focus away from AP-side caller semantics and toward endpoint readiness: PERST/refclk/reset/electrical response around the SDX50M endpoint.",
            "",
            "## Next Gate",
            "",
            f"- Cycle: `{result['next_gate']['cycle']}`",
            f"- Summary: {result['next_gate']['summary']}",
            *(f"- Guardrail: {item}" for item in result["next_gate"]["guardrails"]),
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = classify()
    report = render_report(result)
    store = EvidenceStore(repo_path(args.out_dir))
    result["out_dir"] = str(store.run_dir)
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
                "next_gate": result["next_gate"]["cycle"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
