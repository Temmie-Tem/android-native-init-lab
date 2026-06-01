#!/usr/bin/env python3
"""V1525 host-only classifier for MHI PM-resume position vs TEST:11."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1525-mhi-pm-resume-position-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1525_MHI_PM_RESUME_POSITION_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1525-mhi-pm-resume-position-classifier.txt")

V1524_MANIFEST = Path("tmp/wifi/v1524-endpoint-trigger-attribution-classifier/manifest.json")
V852_DMESG = Path(
    "tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/"
    "v852-android-ext-mdm-provider-surface-run/android/commands/dmesg-focus.txt"
)
V1517_NATIVE_DMESG = Path(
    "tmp/wifi/v1517-wifi-critical-source-pre-l0-handoff/test-v1393-dmesg.stdout.txt"
)
MHI_ARCH_SOURCE = Path(
    "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/bus/mhi/controllers/mhi_arch_qcom.c"
)
MHI_QCOM_SOURCE = Path(
    "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/bus/mhi/controllers/mhi_qcom.c"
)
KERNEL_ROOT = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel")


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


def lines_matching(text: str, pattern: str, limit: int = 20) -> list[str]:
    regex = re.compile(pattern, re.I)
    return [line.strip() for line in text.splitlines() if regex.search(line)][:limit]


def source_lines(text: str, needles: tuple[str, ...], limit: int = 30) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(text.splitlines(), 1):
        if any(needle in line for needle in needles):
            rows.append({"line": index, "text": line.strip()})
            if len(rows) >= limit:
                break
    return rows


def function_body(text: str, signature: str) -> dict[str, Any]:
    line_start, line_end, body = v1498.extract_function(text, signature)
    return {
        "line_start": line_start,
        "line_end": line_end,
        "found": bool(body),
        "body": body,
    }


def grep_kernel_for_enumerate_calls() -> list[dict[str, Any]]:
    root = repo_path(KERNEL_ROOT)
    rows: list[dict[str, Any]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".c", ".h"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for index, line in enumerate(text.splitlines(), 1):
            if "msm_pcie_enumerate" not in line:
                continue
            rel_path = str(path.relative_to(root))
            rows.append({"path": rel_path, "line": index, "text": line.strip()})
    return rows


def analyze_sources(args: argparse.Namespace) -> dict[str, Any]:
    pcie_source, pcie_meta = v1498.read_pcie_source(args)
    mhi_arch = read_text(MHI_ARCH_SOURCE)
    mhi_qcom = read_text(MHI_QCOM_SOURCE)

    mhi_power_on = function_body(mhi_arch, r"\bstatic\s+int\s+mhi_arch_esoc_ops_power_on\s*\(")
    mhi_arch_init = function_body(mhi_arch, r"\bint\s+mhi_arch_pcie_init\s*\(")
    mhi_pci_probe = function_body(mhi_qcom, r"\bint\s+mhi_pci_probe\s*\(")
    pm_control = function_body(pcie_source, r"\bint\s+msm_pcie_pm_control\s*\(")
    pm_resume = function_body(pcie_source, r"\bstatic\s+int\s+msm_pcie_pm_resume\s*\(")
    enumerate = function_body(pcie_source, r"\bint\s+msm_pcie_enumerate\s*\(")
    config_table = function_body(
        pcie_source,
        r"\bstatic\s+int\s+msm_pcie_config_device_table\s*\(",
    )

    enumerate_calls = grep_kernel_for_enumerate_calls()
    concrete_enumerate_callers = [
        row
        for row in enumerate_calls
        if row["path"].endswith(".c")
        and not row["text"].startswith("int msm_pcie_enumerate")
        and not row["text"].startswith("*")
        and not row["text"].startswith("//")
        and "EXPORT_SYMBOL" not in row["text"]
    ]

    return {
        "pcie_source": pcie_meta,
        "mhi_arch": {
            "path": rel(MHI_ARCH_SOURCE),
            "power_on": {k: v for k, v in mhi_power_on.items() if k != "body"},
            "pcie_init": {k: v for k, v in mhi_arch_init.items() if k != "body"},
            "power_on_uses_existing_pci_dev": "struct pci_dev *pci_dev = mhi_dev->pci_dev" in mhi_power_on["body"],
            "power_on_calls_pm_resume": "msm_pcie_pm_control(MSM_PCIE_RESUME" in mhi_power_on["body"],
            "power_on_calls_mhi_probe": "mhi_pci_probe(pci_dev, NULL)" in mhi_power_on["body"],
            "hook_registered_inside_mhi_arch_init": "esoc_ops->esoc_link_power_on" in mhi_arch_init["body"]
            and "mhi_arch_esoc_ops_power_on" in mhi_arch_init["body"],
            "pcie_init_requires_pci_dev": "mhi_dev->pci_dev" in mhi_arch_init["body"],
            "key_lines": source_lines(
                mhi_arch,
                (
                    "static int mhi_arch_esoc_ops_power_on",
                    "struct pci_dev *pci_dev = mhi_dev->pci_dev",
                    "msm_pcie_pm_control(MSM_PCIE_RESUME",
                    "mhi_pci_probe(pci_dev, NULL)",
                    "int mhi_arch_pcie_init",
                    "esoc_ops->esoc_link_power_on",
                    "mhi_arch_esoc_ops_power_on",
                ),
            ),
        },
        "mhi_qcom": {
            "path": rel(MHI_QCOM_SOURCE),
            "mhi_pci_probe": {k: v for k, v in mhi_pci_probe.items() if k != "body"},
            "mhi_pci_probe_requires_pci_dev": "int mhi_pci_probe(struct pci_dev *pci_dev" in mhi_qcom,
            "mhi_pci_driver_id_0305": "{PCI_DEVICE(MHI_PCIE_VENDOR_ID, 0x0305)}" in mhi_qcom,
            "module_pci_driver": "module_pci_driver(mhi_pcie_driver)" in mhi_qcom,
            "key_lines": source_lines(
                mhi_qcom,
                (
                    "int mhi_pci_probe(struct pci_dev *pci_dev",
                    "{PCI_DEVICE(MHI_PCIE_VENDOR_ID, 0x0305)}",
                    "module_pci_driver(mhi_pcie_driver)",
                ),
            ),
        },
        "pcie": {
            "pm_control": {k: v for k, v in pm_control.items() if k != "body"},
            "pm_resume": {k: v for k, v in pm_resume.items() if k != "body"},
            "enumerate": {k: v for k, v in enumerate.items() if k != "body"},
            "config_table": {k: v for k, v in config_table.items() if k != "body"},
            "pm_control_requires_user": "if (!user)" in pm_control["body"],
            "pm_control_casts_user_to_pci_dev": "((struct pci_dev *)user)->bus" in pm_control["body"],
            "pm_control_validates_pcidev_table": "user == pcie_dev->pcidev_table[i].dev" in pm_control["body"],
            "pm_control_requires_drv_ready": "if (!msm_pcie_dev[rc_idx].drv_ready)" in pm_control["body"],
            "pm_resume_requires_link_disabled": "case MSM_PCIE_RESUME:" in pm_control["body"]
            and "MSM_PCIE_LINK_DISABLED" in pm_control["body"],
            "pm_resume_uses_pm_subset": "msm_pcie_enable(pcie_dev, PM_PIPE_CLK | PM_CLK | PM_VREG)" in pm_resume["body"],
            "enumerate_uses_pm_all": "msm_pcie_enable(dev, PM_ALL)" in enumerate["body"],
            "enumerate_creates_pci_bus": "pci_scan_root_bus_bridge" in enumerate["body"]
            or "pci_scan_root_bus" in enumerate["body"],
            "enumerate_sets_enumerated": "dev->enumerated = true" in enumerate["body"],
            "config_table_populates_pcidev": "dev_table_t[index].dev = pcidev" in config_table["body"],
            "key_lines": source_lines(
                pcie_source,
                (
                    "#define PM_ALL",
                    "ret = msm_pcie_enable(dev, PM_ALL)",
                    "pci_scan_root_bus_bridge",
                    "dev->enumerated = true",
                    "dev_table_t[index].dev = pcidev",
                    "int msm_pcie_pm_control",
                    "if (!user)",
                    "((struct pci_dev *)user)->bus",
                    "user == pcie_dev->pcidev_table[i].dev",
                    "if (!msm_pcie_dev[rc_idx].drv_ready)",
                    "case MSM_PCIE_RESUME:",
                    "MSM_PCIE_LINK_DISABLED",
                    "static int msm_pcie_pm_resume",
                    "msm_pcie_enable(pcie_dev, PM_PIPE_CLK | PM_CLK | PM_VREG)",
                ),
            ),
            "enumerate_callers": enumerate_calls,
            "concrete_enumerate_callers": concrete_enumerate_callers,
        },
    }


def analyze_evidence() -> dict[str, Any]:
    v852 = read_text(V852_DMESG)
    native = read_text(V1517_NATIVE_DMESG)
    return {
        "android_v852": {
            "path": rel(V852_DMESG),
            "first_esoc0": first_ts(v852, r"__subsystem_get:\s+esoc0 count:0"),
            "first_rc1_assert": first_ts(v852, r"msm_pcie_enable: PCIe: Assert the reset of endpoint of RC1"),
            "first_l0": first_ts(v852, r"LTSSM_STATE:\s+LTSSM_L0"),
            "first_current_gen": first_ts(v852, r"Current GEN"),
            "first_sysmon_esoc": first_ts(v852, r"ssctl_new_server:.*esoc0"),
            "first_mhi_irq_line_present": bool(re.search(r"\bmsm_pci_msi\b|\bmhi\b", v852, re.I)),
            "has_debugfs_test_marker": bool(re.search(r"PCIe:\s+TEST:|msm_pcie_sel_debug_testcase", v852, re.I)),
            "later_pm_suspend_resume_lines": lines_matching(
                v852,
                r"msm_pcie_pm_suspend|PME_TURNOFF|msm_pcie_disable|PCIe RC1 Current GEN3",
                20,
            ),
            "first_rc1_lines": lines_matching(
                v852,
                r"__subsystem_get.*esoc0|msm_pcie_enable: PCIe|LTSSM_STATE|Current GEN|link initialized|ssctl_new_server:.*esoc0",
                28,
            ),
        },
        "native_v1517": {
            "path": rel(V1517_NATIVE_DMESG),
            "has_test11": bool(re.search(r"PCIe:\s+TEST:\s+11", native, re.I)),
            "first_rc1_assert": first_ts(native, r"msm_pcie_enable: PCIe: Assert the reset of endpoint of RC1"),
            "first_poll_compliance": first_ts(native, r"LTSSM_STATE:\s+LTSSM_POLL_COMPLIANCE"),
            "first_link_failed": first_ts(native, r"link initialization failed"),
            "has_l0": bool(re.search(r"LTSSM_STATE:\s+LTSSM_L0|Current GEN", native, re.I)),
            "key_lines": lines_matching(
                native,
                r"PCIe:\s+TEST:\s+11|msm_pcie_enable: PCIe|LTSSM_STATE|link initialization failed",
                24,
            ),
        },
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1524 = read_json(V1524_MANIFEST)
    sources = analyze_sources(args)
    evidence = analyze_evidence()

    v1524_fixed = (
        v1524.get("pass") is True
        and v1524.get("decision") == "v1524-trigger-attribution-pivots-to-esoc-mhi-pm-resume"
    )
    pm_resume_requires_existing_pci_dev = all(
        [
            sources["mhi_arch"]["power_on_uses_existing_pci_dev"],
            sources["mhi_qcom"]["mhi_pci_probe_requires_pci_dev"],
            sources["pcie"]["pm_control_requires_user"],
            sources["pcie"]["pm_control_casts_user_to_pci_dev"],
            sources["pcie"]["pm_control_validates_pcidev_table"],
        ]
    )
    pm_resume_is_after_pci_probe = all(
        [
            sources["mhi_qcom"]["module_pci_driver"],
            sources["mhi_qcom"]["mhi_pci_driver_id_0305"],
            sources["mhi_arch"]["hook_registered_inside_mhi_arch_init"],
            sources["mhi_arch"]["pcie_init_requires_pci_dev"],
        ]
    )
    pm_resume_not_initial_l0_trigger = pm_resume_requires_existing_pci_dev and pm_resume_is_after_pci_probe
    test11_is_initial_enumerate_path = all(
        [
            sources["pcie"]["enumerate_uses_pm_all"],
            sources["pcie"]["enumerate_creates_pci_bus"],
            sources["pcie"]["enumerate_sets_enumerated"],
            sources["pcie"]["config_table_populates_pcidev"],
        ]
    )
    android_first_l0_before_sysmon_esoc = (
        evidence["android_v852"]["first_l0"] is not None
        and evidence["android_v852"]["first_sysmon_esoc"] is not None
        and evidence["android_v852"]["first_l0"] < evidence["android_v852"]["first_sysmon_esoc"]
    )
    android_initial_not_test11 = (
        evidence["android_v852"]["first_l0"] is not None
        and evidence["android_v852"]["has_debugfs_test_marker"] is False
    )
    native_test11_fail_still_valid = (
        evidence["native_v1517"]["has_test11"]
        and evidence["native_v1517"]["first_link_failed"] is not None
        and not evidence["native_v1517"]["has_l0"]
    )
    active_source_enumerate_callers_limited = all(
        row["path"] == "drivers/net/wireless/cnss2/pci.c" for row in sources["pcie"]["concrete_enumerate_callers"]
    )

    checks = [
        {
            "name": "v1524-fixed-point",
            "status": "pass" if v1524_fixed else "blocked",
            "detail": "V1524 raised MHI PM-resume as the candidate to validate",
        },
        {
            "name": "pm-resume-requires-existing-pci-dev",
            "status": "pass" if pm_resume_requires_existing_pci_dev else "blocked",
            "detail": "MHI PM-resume path dereferences a pci_dev and pci-msm validates it against pcidev_table",
        },
        {
            "name": "pm-resume-hook-is-after-mhi-pci-probe",
            "status": "pass" if pm_resume_is_after_pci_probe else "blocked",
            "detail": "eSoC power-on hook is registered from MHI PCI init/probe, so it is not the first PCI device creation path",
        },
        {
            "name": "pm-resume-not-initial-l0-trigger",
            "status": "pass" if pm_resume_not_initial_l0_trigger else "blocked",
            "detail": "PM-resume can explain later link resumes but cannot create the first pci_dev/L0 by itself",
        },
        {
            "name": "test11-remains-initial-enumerate-path",
            "status": "pass" if test11_is_initial_enumerate_path else "blocked",
            "detail": "TEST:11/enumerate is the source path that creates PCI bus/device state after L0",
        },
        {
            "name": "android-first-l0-before-esoc-ssctl",
            "status": "pass" if android_first_l0_before_sysmon_esoc else "blocked",
            "detail": "Android V852 reaches first L0 before esoc0 SSCTL publication, consistent with initial enumeration before MHI/SSCTL maturity",
        },
        {
            "name": "android-initial-not-debugfs-test11",
            "status": "pass" if android_initial_not_test11 else "blocked",
            "detail": "Android initial L0 has no pci-msm debugfs TEST marker in the positive reference",
        },
        {
            "name": "native-test11-fail-still-valid",
            "status": "pass" if native_test11_fail_still_valid else "blocked",
            "detail": "Native explicit TEST:11 still reaches LTSSM but fails before L0",
        },
        {
            "name": "active-source-enumerate-callers-limited",
            "status": "pass" if active_source_enumerate_callers_limited else "blocked",
            "detail": "Local OSRC only exposes concrete msm_pcie_enumerate callers in the inactive CNSS2 branch; ICNSS path has no direct enumerate caller",
        },
    ]
    pass_ok = all(item["status"] == "pass" for item in checks)
    decision = (
        "v1525-mhi-pm-resume-is-post-enumeration-not-first-l0-trigger"
        if pass_ok
        else "v1525-mhi-pm-resume-position-needs-more-evidence"
    )
    reason = (
        "MHI PM-resume requires an existing pci_dev and is registered after MHI PCI probe, so it is downstream of first L0/PCI device creation; the first native blocker remains the Android-only initial enumerate/readiness trigger, not MHI resume"
        if pass_ok
        else "Source/evidence facts do not yet fully position MHI PM-resume relative to first L0"
    )
    return {
        "cycle": "V1525",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "inputs": {
            "v1524": rel(V1524_MANIFEST),
            "v852_dmesg": rel(V852_DMESG),
            "v1517_native_dmesg": rel(V1517_NATIVE_DMESG),
            "mhi_arch_source": rel(MHI_ARCH_SOURCE),
            "mhi_qcom_source": rel(MHI_QCOM_SOURCE),
            "pcie_source": sources["pcie_source"],
        },
        "host": collect_host_metadata(),
        "checks": checks,
        "sources": sources,
        "evidence": evidence,
        "classification": {
            "v1524_pm_resume_pivot": "corrected",
            "mhi_pm_resume_position": "post-enumeration/post-pci-dev",
            "mhi_pm_resume_explains": "later Android RC1 resume cycles after a pci_dev exists",
            "mhi_pm_resume_does_not_explain": "first L0 / first pci_dev creation",
            "native_current_blocker": "initial Android-only enumerate/readiness trigger before L0",
            "firmware_mhi_wlfw_connect_deferred": True,
        },
        "next_gate": {
            "primary": "V1526 Android initial RC1 trigger capture design",
            "rationale": (
                "Capture or classify the Android-only first-L0 trigger below Wi-Fi connect: endpoint wake IRQ timing, "
                "pci-msm sysfs/client enumerate, or another kernel caller. Prefer read-only Android tracepoint/IRQ/dmesg "
                "capture before adding another native mutation; do not continue the MHI PM-resume branch as the first-L0 fix."
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
    sources = result["sources"]
    lines = [
        "# Native Init V1525 MHI PM-Resume Position Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1525`",
        "- Type: host-only source/evidence classifier",
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
        "## Key Comparison",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["Android first esoc0", evidence["android_v852"]["first_esoc0"]],
                ["Android first RC1 assert", evidence["android_v852"]["first_rc1_assert"]],
                ["Android first L0", evidence["android_v852"]["first_l0"]],
                ["Android first esoc0 SSCTL", evidence["android_v852"]["first_sysmon_esoc"]],
                ["Android has debugfs TEST marker", evidence["android_v852"]["has_debugfs_test_marker"]],
                ["Native TEST:11", evidence["native_v1517"]["has_test11"]],
                ["Native link failed", evidence["native_v1517"]["first_link_failed"]],
                ["Native L0", evidence["native_v1517"]["has_l0"]],
            ],
        ),
        "",
        "## Source Positioning",
        "",
        markdown_table(
            ["fact", "value"],
            [
                ["MHI power-on uses existing pci_dev", sources["mhi_arch"]["power_on_uses_existing_pci_dev"]],
                ["MHI eSoC hook registered inside MHI PCI init", sources["mhi_arch"]["hook_registered_inside_mhi_arch_init"]],
                ["MHI PCI probe requires pci_dev", sources["mhi_qcom"]["mhi_pci_probe_requires_pci_dev"]],
                ["MHI PCI ID includes 17cb:0305", sources["mhi_qcom"]["mhi_pci_driver_id_0305"]],
                ["pci-msm PM control requires user", sources["pcie"]["pm_control_requires_user"]],
                ["pci-msm PM control validates pcidev_table", sources["pcie"]["pm_control_validates_pcidev_table"]],
                ["PM resume uses PM subset", sources["pcie"]["pm_resume_uses_pm_subset"]],
                ["TEST:11 enumerate uses PM_ALL", sources["pcie"]["enumerate_uses_pm_all"]],
                ["TEST:11 creates PCI bus/device state", sources["pcie"]["enumerate_creates_pci_bus"]],
                ["Concrete OSRC enumerate callers", len(sources["pcie"]["concrete_enumerate_callers"])],
            ],
        ),
        "",
        "## Key Lines",
        "",
        "### MHI/eSoC",
        "",
        markdown_table(["line", "text"], [[row["line"], row["text"]] for row in sources["mhi_arch"]["key_lines"]]),
        "",
        "### MHI PCI Probe",
        "",
        markdown_table(["line", "text"], [[row["line"], row["text"]] for row in sources["mhi_qcom"]["key_lines"]]),
        "",
        "### pci-msm",
        "",
        markdown_table(["line", "text"], [[row["line"], row["text"]] for row in sources["pcie"]["key_lines"]]),
        "",
        "### Concrete `msm_pcie_enumerate` Callers In Local OSRC",
        "",
        markdown_table(
            ["path", "line", "text"],
            [[row["path"], row["line"], row["text"]] for row in sources["pcie"]["concrete_enumerate_callers"]],
        ),
        "",
        "## Interpretation",
        "",
        "V1525 corrects the V1524 PM-resume pivot. The MHI/eSoC `MSM_PCIE_RESUME` path is real, but it requires an already existing `pci_dev`: `mhi_arch_esoc_ops_power_on()` reads `mhi_dev->pci_dev`, `msm_pcie_pm_control()` casts the caller to `struct pci_dev`, and pci-msm validates that user against `pcidev_table`. The eSoC hook is registered from MHI PCI initialization/probe, so it cannot be the operation that creates the first PCI device or the first L0 link by itself.",
        "",
        "That makes the Android first-L0 trigger a narrower problem: Android reaches first RC1 L0 without a debugfs TEST marker, while native explicit TEST:11 reaches LTSSM polling and fails before L0. The MHI PM-resume path can explain later Android RC1 suspend/resume cycles after the endpoint has already enumerated, not the missing native first-L0 transition.",
        "",
        "Firmware, MHI deep dive, WLFW, scan/connect, credentials, DHCP/routes, and external ping remain downstream until native first L0 and PCI enumeration exist.",
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
