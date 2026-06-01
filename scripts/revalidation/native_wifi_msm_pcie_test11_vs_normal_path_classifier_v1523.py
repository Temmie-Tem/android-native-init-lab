#!/usr/bin/env python3
"""V1523 host-only msm_pcie TEST:11 vs normal-path classifier."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1523-msm-pcie-test11-vs-normal-path-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1523_MSM_PCIE_TEST11_VS_NORMAL_PATH_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1523-msm-pcie-test11-vs-normal-path-classifier.txt")
V1498_MANIFEST = Path("tmp/wifi/v1498-msm-pcie-test11-static-analysis/manifest.json")
V1522_MANIFEST = Path("tmp/wifi/v1522-android-native-rc1-source-parity-classifier/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def parse_angle_int(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"<\s*(0x[0-9a-fA-F]+|\d+)\s*>", value)
    return int(match.group(1), 0) if match else None


def body_contains(body: str, needle: str) -> bool:
    return needle in body


def function_info(source: str, signature: str) -> dict[str, Any]:
    start, end, body = v1498.extract_function(source, signature)
    return {
        "line_start": start,
        "line_end": end,
        "found": bool(body),
        "body": body,
    }


def line_snippets(source: str, needles: tuple[str, ...]) -> list[dict[str, Any]]:
    snippets: list[dict[str, Any]] = []
    for idx, line in enumerate(source.splitlines(), 1):
        if any(needle in line for needle in needles):
            snippets.append({"line": idx, "text": line.strip()})
    return snippets


def summarize_body_lines(body: str, keywords: tuple[str, ...], start_line: int | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if start_line is None:
        return out
    for offset, line in enumerate(body.splitlines()):
        if any(keyword in line for keyword in keywords):
            out.append({"line": start_line + offset, "text": line.strip()})
    return out


def analyze_source(args: argparse.Namespace) -> dict[str, Any]:
    pcie_source, source_meta = v1498.read_pcie_source(args)
    dts = v1498.parse_dts()
    source = v1498.analyze_pcie_source(pcie_source)
    test_case = v1498.extract_switch_case(pcie_source, "MSM_PCIE_ENUMERATION")
    sysfs = function_info(
        pcie_source,
        r"\bstatic\s+ssize_t\s+msm_pcie_enumerate_store\s*\(",
    )
    wake_irq = function_info(
        pcie_source,
        r"\bstatic\s+irqreturn_t\s+handle_wake_irq\s*\(",
    )
    wake_work = function_info(
        pcie_source,
        r"\bstatic\s+void\s+handle_wake_func\s*\(",
    )
    probe = source["functions"]["msm_pcie_probe"]
    enumerate = source["functions"]["msm_pcie_enumerate"]
    enable = source["functions"]["msm_pcie_enable"]

    boot_option = parse_angle_int(dts["pcie1"]["boot_option"])
    no_probe_bit = 0x1
    no_wake_bit = 0x2
    pcie1_no_probe_enum = bool(boot_option is not None and boot_option & no_probe_bit)
    pcie1_wake_enum_allowed = bool(boot_option is not None and not (boot_option & no_wake_bit))

    callsite_snippets = line_snippets(
        pcie_source,
        (
            "case MSM_PCIE_ENUMERATION:",
            "msm_pcie_enumerate(dev->rc_idx)",
            "msm_pcie_enumerate(pcie_dev->rc_idx)",
            "msm_pcie_enumerate(rc_idx)",
            "ret = msm_pcie_enumerate(dev->rc_idx)",
            "int msm_pcie_enumerate(u32 rc_idx)",
            "EXPORT_SYMBOL(msm_pcie_enumerate)",
            "MSM_PCIE_NO_PROBE_ENUMERATION",
            "MSM_PCIE_NO_WAKE_ENUMERATION",
            "schedule_work(&dev->handle_wake_work)",
            "Start enumeration for RC%d upon the wake",
        ),
    )

    chains = {
        "debugfs_test11": [
            "debugfs pci-msm case write",
            "case MSM_PCIE_ENUMERATION",
            "msm_pcie_enumerate(dev->rc_idx)",
            "msm_pcie_enable(dev, PM_ALL)",
            "pci_scan_root_bus_bridge / pci_bus_add_devices if link succeeds",
        ],
        "sysfs_enumerate": [
            "platform sysfs enumerate attribute",
            "msm_pcie_enumerate(pcie_dev->rc_idx)",
            "msm_pcie_enable(dev, PM_ALL)",
        ],
        "endpoint_wake": [
            "GPIO104/WAKE falling IRQ",
            "handle_wake_irq",
            "schedule_work(handle_wake_work)",
            "handle_wake_func",
            "msm_pcie_enumerate(dev->rc_idx)",
            "msm_pcie_enable(dev, PM_ALL)",
        ],
        "probe_boot": [
            "msm_pcie_probe",
            "read qcom,boot-option",
            "return before probe enumeration if MSM_PCIE_NO_PROBE_ENUMERATION is set",
            "otherwise msm_pcie_enumerate(rc_idx)",
        ],
    }

    return {
        "source_meta": source_meta,
        "dts": dts,
        "source": source,
        "boot_option": {
            "raw": dts["pcie1"]["boot_option"],
            "value": boot_option,
            "no_probe_enumeration_bit_set": pcie1_no_probe_enum,
            "no_wake_enumeration_bit_set": bool(boot_option is not None and boot_option & no_wake_bit),
            "wake_enumeration_allowed": pcie1_wake_enum_allowed,
        },
        "normal_path_functions": {
            "probe": {
                **probe,
                "body": "",
                "key_lines": summarize_body_lines(
                    function_info(pcie_source, r"\bstatic\s+int\s+msm_pcie_probe\s*\(")["body"],
                    (
                        "qcom,boot-option",
                        "MSM_PCIE_NO_PROBE_ENUMERATION",
                        "msm_pcie_enumerate(rc_idx)",
                    ),
                    probe.get("line_start"),
                ),
            },
            "sysfs_enumerate_store": {
                "line_start": sysfs["line_start"],
                "line_end": sysfs["line_end"],
                "found": sysfs["found"],
                "calls_msm_pcie_enumerate": body_contains(sysfs["body"], "msm_pcie_enumerate(pcie_dev->rc_idx)"),
            },
            "handle_wake_irq": {
                "line_start": wake_irq["line_start"],
                "line_end": wake_irq["line_end"],
                "found": wake_irq["found"],
                "checks_no_wake_bit": "MSM_PCIE_NO_WAKE_ENUMERATION" in wake_irq["body"],
                "schedules_wake_work": "schedule_work(&dev->handle_wake_work)" in wake_irq["body"],
                "key_lines": summarize_body_lines(
                    wake_irq["body"],
                    ("MSM_PCIE_NO_WAKE_ENUMERATION", "schedule_work", "Start enumerating"),
                    wake_irq["line_start"],
                ),
            },
            "handle_wake_func": {
                "line_start": wake_work["line_start"],
                "line_end": wake_work["line_end"],
                "found": wake_work["found"],
                "calls_msm_pcie_enumerate": "msm_pcie_enumerate(dev->rc_idx)" in wake_work["body"],
                "key_lines": summarize_body_lines(
                    wake_work["body"],
                    ("Start enumeration", "msm_pcie_enumerate", "Linkup callback"),
                    wake_work["line_start"],
                ),
            },
        },
        "test11": {
            "enum_value": source["enum"]["value"],
            "case_line_start": test_case["line_start"],
            "case_line_end": test_case["line_end"],
            "calls_msm_pcie_enumerate": "msm_pcie_enumerate(dev->rc_idx)" in test_case["body"],
        },
        "common_enumerate": {
            **enumerate,
            "calls_msm_pcie_enable_pm_all": enumerate["calls_msm_pcie_enable_pm_all"],
            "calls_pci_scan_root_bus": enumerate["calls_pci_scan_root_bus"],
        },
        "common_enable": {
            "line_start": enable["line_start"],
            "line_end": enable["line_end"],
            "found": enable["found"],
            "keywords": enable["keywords"],
        },
        "callsite_snippets": callsite_snippets,
        "chains": chains,
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1498_manifest = read_json(V1498_MANIFEST)
    v1522_manifest = read_json(V1522_MANIFEST)
    analysis = analyze_source(args)
    source = analysis["source"]
    normal = analysis["normal_path_functions"]
    boot_option = analysis["boot_option"]
    test11 = analysis["test11"]
    common_enable_keywords = analysis["common_enable"]["keywords"]

    v1498_fixed = (
        v1498_manifest.get("pass") is True
        and v1498_manifest.get("decision") == "v1498-msm-pcie-test11-enumerate-path-confirmed-endpoint-response-gap"
    )
    v1522_fixed = (
        v1522_manifest.get("pass") is True
        and v1522_manifest.get("decision") == "v1522-sampled-sources-nondiscriminating-msm-pcie-static-needed"
    )
    test11_reaches_common_enable = all(
        [
            test11["enum_value"] == 11,
            test11["calls_msm_pcie_enumerate"],
            analysis["common_enumerate"]["calls_msm_pcie_enable_pm_all"],
            all(common_enable_keywords.values()),
        ]
    )
    probe_deferred_by_dts = all(
        [
            boot_option["value"] == 0x1,
            boot_option["no_probe_enumeration_bit_set"],
            normal["probe"]["boot_option_no_probe_enum_check"],
        ]
    )
    normal_alternate_callers_present = all(
        [
            normal["sysfs_enumerate_store"]["calls_msm_pcie_enumerate"],
            normal["handle_wake_irq"]["checks_no_wake_bit"],
            normal["handle_wake_irq"]["schedules_wake_work"],
            normal["handle_wake_func"]["calls_msm_pcie_enumerate"],
            boot_option["wake_enumeration_allowed"],
        ]
    )
    no_missing_enable_operation = test11_reaches_common_enable and normal_alternate_callers_present

    checks = [
        {
            "name": "v1498-test11-fixed-point",
            "status": "pass" if v1498_fixed else "blocked",
            "detail": "V1498 already proves TEST:11 enters corrected RC1 enumerate and native fails pre-L0",
        },
        {
            "name": "v1522-sampled-sources-closed",
            "status": "pass" if v1522_fixed else "blocked",
            "detail": "V1522 closes sampled GPIO/GDSC/IRQ low/off states as a discriminating root cause",
        },
        {
            "name": "test11-reaches-common-enable",
            "status": "pass" if test11_reaches_common_enable else "blocked",
            "detail": "debugfs TEST:11 calls msm_pcie_enumerate, which calls msm_pcie_enable(PM_ALL)",
        },
        {
            "name": "pcie1-probe-enumeration-deferred",
            "status": "pass" if probe_deferred_by_dts else "blocked",
            "detail": "SM8150 pcie1 has qcom,boot-option=<0x1>, setting NO_PROBE_ENUMERATION",
        },
        {
            "name": "normal-alternate-callers-converge",
            "status": "pass" if normal_alternate_callers_present else "blocked",
            "detail": "sysfs/client or endpoint-wake paths converge on the same msm_pcie_enumerate function",
        },
        {
            "name": "no-ap-side-enable-op-missing-from-test11",
            "status": "pass" if no_missing_enable_operation else "blocked",
            "detail": "The AP-side enable sequence is shared after enumerate; remaining difference is trigger/readiness semantics before enumerate",
        },
    ]
    pass_ok = all(item["status"] == "pass" for item in checks)
    decision = (
        "v1523-test11-shares-enable-normal-trigger-readiness-gap"
        if pass_ok
        else "v1523-msm-pcie-path-classifier-blocked"
    )
    reason = (
        "TEST:11 is not missing the core AP-side enable sequence; pcie1 probe is intentionally deferred and normal callers converge on msm_pcie_enumerate, so the remaining gap is endpoint readiness/trigger semantics before enumerate"
        if pass_ok
        else "The source/DTS/evidence inputs do not support a complete TEST:11 vs normal-path classification"
    )
    return {
        "cycle": "V1523",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "inputs": {
            "v1498": rel(V1498_MANIFEST),
            "v1522": rel(V1522_MANIFEST),
            "pcie_source": analysis["source_meta"],
            "pcie_dts": analysis["dts"]["files"]["pcie_dts"],
        },
        "host": collect_host_metadata(),
        "checks": checks,
        "path_analysis": {
            "boot_option": boot_option,
            "test11": test11,
            "common_enumerate": analysis["common_enumerate"],
            "common_enable": analysis["common_enable"],
            "normal_path_functions": analysis["normal_path_functions"],
            "chains": analysis["chains"],
            "callsite_snippets": analysis["callsite_snippets"],
        },
        "classification": {
            "test11_reaches_common_enable": test11_reaches_common_enable,
            "probe_deferred_by_dts": probe_deferred_by_dts,
            "normal_alternate_callers_present": normal_alternate_callers_present,
            "no_missing_ap_side_enable_operation": no_missing_enable_operation,
            "remaining_gap": "endpoint readiness / normal trigger semantics before msm_pcie_enumerate",
            "firmware_mhi_wlfw_scan_connect_deferred_until_native_l0": pass_ok,
        },
        "next_gate": {
            "primary": "V1524 endpoint-readiness trigger classifier",
            "rationale": "Classify Android-good and native-fail evidence for the trigger that causes normal msm_pcie_enumerate: endpoint wake IRQ/GPIO104, sysfs/client caller, or vendor client request. Do this host-only/read-only first; do not add another blind TEST:11 timing retry.",
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
    paths = result["path_analysis"]
    boot = paths["boot_option"]
    test11 = paths["test11"]
    normal = paths["normal_path_functions"]
    common = paths["common_enumerate"]
    enable = paths["common_enable"]
    lines = [
        "# Native Init V1523 MSM PCIe TEST:11 vs Normal Path Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1523`",
        "- Type: host-only static/callgraph classifier",
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
        markdown_table(["check", "status", "detail"], [[item["name"], item["status"], item["detail"]] for item in result["checks"]]),
        "",
        "## Path Summary",
        "",
        f"- pcie1 `qcom,boot-option`: `{boot['raw']}` / parsed `{boot['value']}`",
        f"- NO_PROBE_ENUMERATION set: `{boot['no_probe_enumeration_bit_set']}`",
        f"- NO_WAKE_ENUMERATION set: `{boot['no_wake_enumeration_bit_set']}`",
        f"- wake enumeration allowed: `{boot['wake_enumeration_allowed']}`",
        f"- TEST:11 enum value: `{test11['enum_value']}`",
        f"- TEST:11 calls `msm_pcie_enumerate`: `{test11['calls_msm_pcie_enumerate']}`",
        f"- common enumerate calls `msm_pcie_enable(PM_ALL)`: `{common['calls_msm_pcie_enable_pm_all']}`",
        f"- common enumerate calls PCI root scan: `{common['calls_pci_scan_root_bus']}`",
        "",
        "## Call Chains",
        "",
    ]
    for name, chain in paths["chains"].items():
        lines.append(f"- `{name}`: " + " -> ".join(f"`{item}`" for item in chain))
    lines.extend(
        [
            "",
            "## Shared Enable Operations",
            "",
        ]
    )
    for key, value in enable["keywords"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Normal-Path Entry Points",
            "",
            f"- `msm_pcie_probe`: lines `{normal['probe']['line_start']}-{normal['probe']['line_end']}`, checks NO_PROBE_ENUMERATION `{normal['probe']['boot_option_no_probe_enum_check']}`, calls enumerate `{normal['probe']['calls_msm_pcie_enumerate']}`.",
            f"- `msm_pcie_enumerate_store`: lines `{normal['sysfs_enumerate_store']['line_start']}-{normal['sysfs_enumerate_store']['line_end']}`, calls enumerate `{normal['sysfs_enumerate_store']['calls_msm_pcie_enumerate']}`.",
            f"- `handle_wake_irq`: lines `{normal['handle_wake_irq']['line_start']}-{normal['handle_wake_irq']['line_end']}`, checks NO_WAKE_ENUMERATION `{normal['handle_wake_irq']['checks_no_wake_bit']}`, schedules wake work `{normal['handle_wake_irq']['schedules_wake_work']}`.",
            f"- `handle_wake_func`: lines `{normal['handle_wake_func']['line_start']}-{normal['handle_wake_func']['line_end']}`, calls enumerate `{normal['handle_wake_func']['calls_msm_pcie_enumerate']}`.",
            "",
            "## Key Source Lines",
            "",
            markdown_table(
                ["line", "text"],
                [[item["line"], item["text"]] for item in paths["callsite_snippets"]],
            ),
            "",
            "## Interpretation",
            "",
            "V1523 does not find a missing AP-side `msm_pcie_enable()` operation in TEST:11. The debugfs TEST:11 path, sysfs/client path, endpoint-wake work path, and non-deferred probe path all converge on `msm_pcie_enumerate()`, which calls `msm_pcie_enable(dev, PM_ALL)` and then scans the PCI root bus if link training succeeds.",
            "",
            "For this board, DTS sets `qcom,boot-option=<0x1>`, so probe-time enumeration is intentionally skipped. Android's successful RC1 path therefore comes from a later normal trigger, not from immediate probe enumeration. Since V1522 shows sampled GPIO/GDSC states are not discriminating, the next blocker is the pre-enumerate trigger/readiness condition that Android satisfies and native TEST:11 does not.",
            "",
            "Firmware, MHI, WLFW, scan/connect, credentials, DHCP/routes, and external ping remain downstream until native RC1 reaches L0 and PCI enumeration exists.",
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
    )
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
