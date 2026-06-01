#!/usr/bin/env python3
"""V1498 host-only msm_pcie TEST:11 versus normal enumerate path classifier."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_V1496_DIR = REPO_ROOT / "tmp" / "wifi" / "v1496-wifi-rc1-window-short-hold-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1498-msm-pcie-test11-static-analysis"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1498_MSM_PCIE_TEST11_STATIC_ANALYSIS_2026-06-01.md"
)
DEFAULT_PCIE_SOURCE_URL = (
    "https://android.googlesource.com/kernel/msm/+/"
    "0f3994dddbd64529255b281be6df783792110892/"
    "drivers/pci/host/pci-msm.c?format=TEXT"
)
PCIE_SOURCE_PAGE_URL = (
    "https://android.googlesource.com/kernel/msm/+/"
    "0f3994dddbd64529255b281be6df783792110892/"
    "drivers/pci/host/pci-msm.c"
)
PCIE_DTS = (
    REPO_ROOT
    / "kernel_build"
    / "SM-A908N_KOR_12_Opensource"
    / "Kernel"
    / "arch"
    / "arm64"
    / "boot"
    / "dts"
    / "qcom"
    / "sm8150-pcie.dtsi"
)
MHI_DTS = PCIE_DTS.with_name("sm8150-mhi.dtsi")
SDX50M_DTS = PCIE_DTS.with_name("sm8150-sdx50m.dtsi")
DMESG_TS_RE = re.compile(r"^\[\s*(?P<ts>\d+\.\d+)\]")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def first_ts(text: str, needle: str) -> float | None:
    for line in text.splitlines():
        if needle not in line:
            continue
        match = DMESG_TS_RE.match(line)
        if match is None:
            return None
        return float(match.group("ts"))
    return None


def matching_lines(text: str, needles: tuple[str, ...], limit: int = 24) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        if any(needle in line for needle in needles):
            lines.append(line.strip())
        if len(lines) >= limit:
            break
    return lines


def read_pcie_source(args: argparse.Namespace) -> tuple[str, dict[str, Any]]:
    if args.pcie_source:
        text = read_text(args.pcie_source)
        if not text:
            raise RuntimeError(f"empty --pcie-source: {args.pcie_source}")
        return text, {
            "kind": "local",
            "path": rel(args.pcie_source),
            "url": "",
            "sha256": sha256_text(text),
        }

    with urllib.request.urlopen(args.pcie_source_url, timeout=args.fetch_timeout) as response:
        payload = response.read()
    try:
        text = base64.b64decode(payload).decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 - classify fetch failure clearly
        raise RuntimeError(f"failed to decode Gitiles TEXT payload from {args.pcie_source_url}") from exc
    if "MSM PCIe controller driver" not in text or "msm_pcie_enable" not in text:
        raise RuntimeError("downloaded pci-msm.c did not match expected content")
    return text, {
        "kind": "gitiles",
        "url": PCIE_SOURCE_PAGE_URL,
        "raw_url": args.pcie_source_url,
        "sha256": sha256_text(text),
    }


def line_number(text: str, needle: str) -> int | None:
    for idx, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return idx
    return None


def extract_function(text: str, signature_re: str) -> tuple[int | None, int | None, str]:
    lines = text.splitlines()
    start = None
    pattern = re.compile(signature_re)
    for idx, line in enumerate(lines, 1):
        if pattern.search(line):
            start = idx
            break
    if start is None:
        return None, None, ""

    body_lines: list[str] = []
    depth = 0
    seen_open = False
    for idx in range(start, len(lines) + 1):
        line = lines[idx - 1]
        body_lines.append(line)
        depth += line.count("{")
        if "{" in line:
            seen_open = True
        depth -= line.count("}")
        if seen_open and depth == 0:
            return start, idx, "\n".join(body_lines)
    return start, None, "\n".join(body_lines)


def extract_enum_value(text: str, enum_name: str, item_name: str) -> dict[str, Any]:
    start, end, body = extract_function_like_block(text, rf"enum\s+{re.escape(enum_name)}\s*\{{")
    value = -1
    found = False
    for raw_line in body.splitlines()[1:]:
        line = raw_line.split("/*", 1)[0].split("//", 1)[0].strip()
        if not line or line == "};":
            continue
        name = line.rstrip(",").strip()
        if "=" in name:
            left, right = [part.strip() for part in name.split("=", 1)]
            name = left
            try:
                value = int(right, 0)
            except ValueError:
                value += 1
        else:
            value += 1
        if name == item_name:
            found = True
            break
    return {"line_start": start, "line_end": end, "value": value if found else None, "found": found}


def extract_function_like_block(text: str, start_re: str) -> tuple[int | None, int | None, str]:
    lines = text.splitlines()
    start = None
    pattern = re.compile(start_re)
    for idx, line in enumerate(lines, 1):
        if pattern.search(line):
            start = idx
            break
    if start is None:
        return None, None, ""
    depth = 0
    seen_open = False
    block: list[str] = []
    for idx in range(start, len(lines) + 1):
        line = lines[idx - 1]
        block.append(line)
        depth += line.count("{")
        if "{" in line:
            seen_open = True
        depth -= line.count("}")
        if seen_open and depth == 0:
            return start, idx, "\n".join(block)
    return start, None, "\n".join(block)


def extract_switch_case(text: str, case_label: str) -> dict[str, Any]:
    lines = text.splitlines()
    case_line = None
    for idx, line in enumerate(lines, 1):
        if f"case {case_label}:" in line:
            case_line = idx
            break
    if case_line is None:
        return {"line_start": None, "line_end": None, "body": "", "found": False}
    body: list[str] = []
    for idx in range(case_line, len(lines) + 1):
        line = lines[idx - 1]
        if idx > case_line and re.match(r"\s*case\s+\w+:", line):
            return {"line_start": case_line, "line_end": idx - 1, "body": "\n".join(body), "found": True}
        body.append(line)
        if idx > case_line and re.match(r"\s*break\s*;", line):
            return {"line_start": case_line, "line_end": idx, "body": "\n".join(body), "found": True}
    return {"line_start": case_line, "line_end": len(lines), "body": "\n".join(body), "found": True}


def find_keyword_lines(text: str, keywords: tuple[str, ...], limit: int = 80) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, line in enumerate(text.splitlines(), 1):
        if any(keyword in line for keyword in keywords):
            out.append({"line": idx, "text": line.strip()})
        if len(out) >= limit:
            break
    return out


def extract_dts_node(text: str, start_needle: str) -> tuple[int | None, int | None, str]:
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines, 1):
        if start_needle in line:
            start = idx
            break
    if start is None:
        return None, None, ""
    depth = 0
    seen_open = False
    block: list[str] = []
    for idx in range(start, len(lines) + 1):
        line = lines[idx - 1]
        block.append(line)
        depth += line.count("{")
        if "{" in line:
            seen_open = True
        depth -= line.count("}")
        if seen_open and depth == 0 and line.strip().endswith("};"):
            return start, idx, "\n".join(block)
    return start, None, "\n".join(block)


def property_value(block: str, name: str) -> str | None:
    pattern = re.compile(rf"^\s*{re.escape(name)}\s*=\s*(.*?);", re.MULTILINE | re.DOTALL)
    match = pattern.search(block)
    if match is None:
        return None
    return " ".join(part.strip() for part in match.group(1).splitlines())


def string_list(value: str | None) -> list[str]:
    if not value:
        return []
    return re.findall(r'"([^"]+)"', value)


def parse_tlmm_gpio(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"<&tlmm\s+(\d+)\s+\d+>", value)
    return int(match.group(1)) if match else None


def parse_dts() -> dict[str, Any]:
    pcie_text = read_text(PCIE_DTS)
    mhi_text = read_text(MHI_DTS)
    sdx_text = read_text(SDX50M_DTS)
    pcie_start, pcie_end, pcie_block = extract_dts_node(pcie_text, "pcie1: qcom,pcie@1c08000")
    rc1_start, rc1_end, rc1_block = extract_dts_node(pcie_text, "pcie_rc1: pcie_rc1")
    mhi_start, mhi_end, mhi_block = extract_dts_node(mhi_text, "mhi_0: qcom,mhi@0")
    sdx_mhi_start, sdx_mhi_end, sdx_mhi_block = extract_dts_node(sdx_text, "&mhi_0")
    mdm3_start, mdm3_end, mdm3_block = extract_dts_node(sdx_text, "&mdm3")

    return {
        "files": {
            "pcie_dts": rel(PCIE_DTS),
            "mhi_dts": rel(MHI_DTS),
            "sdx50m_dts": rel(SDX50M_DTS),
        },
        "pcie1": {
            "line_start": pcie_start,
            "line_end": pcie_end,
            "found": bool(pcie_block),
            "compatible": string_list(property_value(pcie_block, "compatible")),
            "cell_index": property_value(pcie_block, "cell-index"),
            "perst_gpio": parse_tlmm_gpio(property_value(pcie_block, "perst-gpio")),
            "wake_gpio": parse_tlmm_gpio(property_value(pcie_block, "wake-gpio")),
            "gdsc_supply": property_value(pcie_block, "gdsc-vdd-supply"),
            "vreg_1v8_supply": property_value(pcie_block, "vreg-1.8-supply"),
            "vreg_0v9_supply": property_value(pcie_block, "vreg-0.9-supply"),
            "vreg_cx_supply": property_value(pcie_block, "vreg-cx-supply"),
            "boot_option": property_value(pcie_block, "qcom,boot-option"),
            "linux_pci_domain": property_value(pcie_block, "linux,pci-domain"),
            "ep_latency": property_value(pcie_block, "qcom,ep-latency"),
            "phy_status_offset": property_value(pcie_block, "qcom,phy-status-offset"),
            "phy_status_bit": property_value(pcie_block, "qcom,phy-status-bit"),
            "clock_names": string_list(property_value(pcie_block, "clock-names")),
            "reset_names": string_list(property_value(pcie_block, "reset-names")),
        },
        "pcie_rc1": {
            "line_start": rc1_start,
            "line_end": rc1_end,
            "found": bool(rc1_block),
            "pci_ids": string_list(property_value(rc1_block, "pci-ids")),
        },
        "mhi_0": {
            "line_start": mhi_start,
            "line_end": mhi_end,
            "found": bool(mhi_block),
            "pci_ids": string_list(property_value(mhi_block, "pci-ids")),
            "name": string_list(property_value(mhi_block, "mhi,name")),
        },
        "sdx50m": {
            "mdm3_line_start": mdm3_start,
            "mdm3_line_end": mdm3_end,
            "mdm3_found": bool(mdm3_block),
            "mdm3_compatible": string_list(property_value(mdm3_block, "compatible")),
            "mdm_link_info": string_list(property_value(mdm3_block, "qcom,mdm-link-info")),
            "mhi_override_line_start": sdx_mhi_start,
            "mhi_override_line_end": sdx_mhi_end,
            "mhi_override_found": bool(sdx_mhi_block),
            "esoc_names": string_list(property_value(sdx_mhi_block, "esoc-names")),
            "esoc_0": property_value(sdx_mhi_block, "esoc-0"),
        },
    }


def parse_v1496(v1496_dir: Path) -> dict[str, Any]:
    manifest = read_json(v1496_dir / "manifest.json")
    dmesg = read_text(v1496_dir / "test-v1393-dmesg.stdout.txt")
    window = read_text(v1496_dir / "test-rc1-window-result.stdout.txt")
    watcher = read_text(v1496_dir / "test-v1393-rc1-watcher-result.stdout.txt")
    progress = manifest.get("wifi_progress", {})
    timestamps = {
        "provider_esoc0_ts": first_ts(dmesg, "__subsystem_get: esoc0"),
        "rc_sel_ts": first_ts(dmesg, "PCIe: rc_sel is now: 0x2"),
        "case11_ts": first_ts(dmesg, "PCIe: TEST: 11"),
        "assert_reset_ts": first_ts(dmesg, "Assert the reset of endpoint of RC1"),
        "phy_ready_ts": first_ts(dmesg, "PCIe RC1 PHY is ready"),
        "release_reset_ts": first_ts(dmesg, "Release the reset of endpoint of RC1"),
        "ltssm_detect_quiet_ts": first_ts(dmesg, "LTSSM_DETECT_QUIET"),
        "ltssm_poll_active_ts": first_ts(dmesg, "LTSSM_POLL_ACTIVE"),
        "ltssm_poll_compliance_ts": first_ts(dmesg, "LTSSM_POLL_COMPLIANCE"),
        "link_failed_ts": first_ts(dmesg, "PCIe RC1 link initialization failed"),
    }
    derived: dict[str, float] = {}
    if timestamps["case11_ts"] is not None and timestamps["provider_esoc0_ts"] is not None:
        derived["case_after_provider_ms"] = round(
            (timestamps["case11_ts"] - timestamps["provider_esoc0_ts"]) * 1000.0,
            3,
        )
    if timestamps["phy_ready_ts"] is not None and timestamps["case11_ts"] is not None:
        derived["phy_ready_after_case_ms"] = round(
            (timestamps["phy_ready_ts"] - timestamps["case11_ts"]) * 1000.0,
            3,
        )
    if timestamps["link_failed_ts"] is not None and timestamps["case11_ts"] is not None:
        derived["link_fail_after_case_ms"] = round(
            (timestamps["link_failed_ts"] - timestamps["case11_ts"]) * 1000.0,
            3,
        )

    return {
        "dir": rel(v1496_dir),
        "manifest_decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "handoff_pass": manifest.get("handoff_pass"),
        "rollback_ok": manifest.get("rollback", {}).get("ok"),
        "progress": {
            "provider_trigger": progress.get("provider_trigger"),
            "rc1_progress": progress.get("rc1_progress"),
            "rc1_l0": progress.get("rc1_l0"),
            "rc1_link_failed": progress.get("rc1_link_failed"),
            "mhi_progress": progress.get("mhi_progress"),
            "wlfw_progress": progress.get("wlfw_progress"),
            "bdf_progress": progress.get("bdf_progress"),
            "fw_ready_progress": progress.get("fw_ready_progress"),
            "wlan0_present": progress.get("wlan0_present"),
        },
        "timestamps": timestamps,
        "derived": derived,
        "watcher": {
            "triggered": "state=triggered" in watcher or bool(progress.get("pid1_rc1_watcher_result_file")),
            "write_rc_zero": "write_rc=0" in watcher or "write_rc=0" in str(progress.get("pid1_rc1_watcher_result_file", "")),
            "debugfs_write_confirmed": "PCIe: rc_sel is now: 0x2" in dmesg and "PCIe: TEST: 11" in dmesg,
        },
        "window": {
            "gpio102_low": "gpio102 : out 0" in window,
            "gpio103_high": "gpio103 : in 1" in window,
            "gpio104_low": "gpio104 : in 0" in window,
            "gpio135_low": "gpio135 : out 0" in window,
            "gpio142_low": "gpio142 : in 0" in window,
        },
        "dmesg_lines": matching_lines(
            dmesg,
            (
                "__subsystem_get: esoc0",
                "PCIe: rc_sel is now: 0x2",
                "PCIe: TEST: 11",
                "Assert the reset of endpoint of RC1",
                "PCIe RC1 PHY is ready",
                "Release the reset of endpoint of RC1",
                "LTSSM_",
                "PCIe RC1 link initialization failed",
            ),
        ),
    }


def analyze_pcie_source(text: str) -> dict[str, Any]:
    enum = extract_enum_value(text, "msm_pcie_debugfs_option", "MSM_PCIE_ENUMERATION")
    case = extract_switch_case(text, "MSM_PCIE_ENUMERATION")
    enumerate_start, enumerate_end, enumerate_body = extract_function(
        text,
        r"\bint\s+msm_pcie_enumerate\s*\(\s*u32\s+rc_idx\s*\)",
    )
    enable_start, enable_end, enable_body = extract_function(
        text,
        r"\bstatic\s+int\s+msm_pcie_enable\s*\(\s*struct\s+msm_pcie_dev_t\s+\*dev,\s*u32\s+options\s*\)",
    )
    probe_start, probe_end, probe_body = extract_function(
        text,
        r"\bstatic\s+int\s+msm_pcie_probe\s*\(\s*struct\s+platform_device\s+\*pdev\s*\)",
    )
    enable_keywords = {
        "assert_perst": "Assert the reset of endpoint" in enable_body,
        "vreg_init": "msm_pcie_vreg_init" in enable_body,
        "clk_init": "msm_pcie_clk_init" in enable_body,
        "phy_init": "pcie_phy_init" in enable_body,
        "pipe_clk_init": "msm_pcie_pipe_clk_init" in enable_body,
        "phy_ready": "PCIe RC%d PHY is ready" in enable_body,
        "release_perst": "Release the reset of endpoint" in enable_body,
        "ltssm_enable": "PCIE20_PARF_LTSSM" in enable_body and "BIT(8)" in enable_body,
        "ltssm_poll": "LTSSM_STATE" in enable_body,
        "confirm_linkup": "msm_pcie_confirm_linkup" in enable_body,
        "link_fail_message": "PCIe RC%d link initialization failed" in enable_body,
    }
    return {
        "source_line_count": len(text.splitlines()),
        "enum": enum,
        "case_enumeration": {
            "line_start": case["line_start"],
            "line_end": case["line_end"],
            "found": case["found"],
            "calls_msm_pcie_enumerate": "msm_pcie_enumerate" in case["body"],
        },
        "functions": {
            "msm_pcie_enumerate": {
                "line_start": enumerate_start,
                "line_end": enumerate_end,
                "found": bool(enumerate_body),
                "calls_msm_pcie_enable_pm_all": "msm_pcie_enable(dev, PM_ALL)" in enumerate_body,
                "calls_pci_scan_root_bus": "pci_scan_root_bus" in enumerate_body or "pci_scan_child_bus" in enumerate_body,
            },
            "msm_pcie_enable": {
                "line_start": enable_start,
                "line_end": enable_end,
                "found": bool(enable_body),
                "keywords": enable_keywords,
                "operation_lines": find_keyword_lines(
                    enable_body,
                    (
                        "Assert the reset of endpoint",
                        "msm_pcie_vreg_init",
                        "msm_pcie_clk_init",
                        "pcie_phy_init",
                        "msm_pcie_pipe_clk_init",
                        "PCIe RC%d PHY is ready",
                        "Release the reset of endpoint",
                        "PCIE20_PARF_LTSSM",
                        "LTSSM_STATE",
                        "msm_pcie_confirm_linkup",
                        "link initialization failed",
                    ),
                ),
            },
            "msm_pcie_probe": {
                "line_start": probe_start,
                "line_end": probe_end,
                "found": bool(probe_body),
                "boot_option_no_probe_enum_check": "MSM_PCIE_NO_PROBE_ENUMERATION" in probe_body,
                "calls_msm_pcie_enumerate": "msm_pcie_enumerate(rc_idx)" in probe_body,
            },
        },
        "global_line_refs": {
            "debugfs_enum_desc": line_number(text, '"ENUMERATE"'),
            "case_msm_pcie_enumeration": line_number(text, "case MSM_PCIE_ENUMERATION:"),
            "msm_pcie_enumerate": line_number(text, "int msm_pcie_enumerate"),
            "msm_pcie_enable": line_number(text, "static int msm_pcie_enable"),
            "probe_no_probe_enumeration": line_number(text, "MSM_PCIE_NO_PROBE_ENUMERATION"),
        },
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    pcie_source, source_meta = read_pcie_source(args)
    source = analyze_pcie_source(pcie_source)
    dts = parse_dts()
    v1496 = parse_v1496(args.v1496_dir)

    source_confirms_test11_enumerate = (
        source["enum"]["found"]
        and source["enum"]["value"] == 11
        and source["case_enumeration"]["calls_msm_pcie_enumerate"]
        and source["functions"]["msm_pcie_enumerate"]["calls_msm_pcie_enable_pm_all"]
    )
    enable_contract_complete = all(source["functions"]["msm_pcie_enable"]["keywords"].values())
    dts_contract_present = (
        dts["pcie1"]["found"]
        and dts["pcie1"]["compatible"] == ["qcom,pci-msm"]
        and dts["pcie1"]["perst_gpio"] == 102
        and dts["pcie1"]["wake_gpio"] == 104
        and "pcie_1_pipe_clk" in dts["pcie1"]["clock_names"]
        and "pcie_1_ref_clk_src" in dts["pcie1"]["clock_names"]
        and dts["pcie_rc1"]["pci_ids"] == ["17cb:0108"]
        and "17cb:0305" in dts["mhi_0"]["pci_ids"]
        and dts["sdx50m"]["mdm3_compatible"] == ["qcom,ext-sdx50m"]
        and dts["sdx50m"]["mdm_link_info"] == ["0305_01.01.00"]
    )
    v1496_rc1_failure_fixed = (
        v1496["manifest_decision"] == "v1496-test-boot-downstream-progress-rollback-pass"
        and v1496["handoff_pass"] is True
        and v1496["rollback_ok"] is True
        and v1496["watcher"]["debugfs_write_confirmed"]
        and v1496["progress"]["rc1_progress"] is True
        and v1496["progress"]["rc1_l0"] is False
        and v1496["progress"]["rc1_link_failed"] is True
        and v1496["timestamps"]["ltssm_poll_compliance_ts"] is not None
        and v1496["timestamps"]["link_failed_ts"] is not None
    )
    downstream_absent = not any(
        bool(v1496["progress"].get(key))
        for key in ("mhi_progress", "wlfw_progress", "bdf_progress", "fw_ready_progress", "wlan0_present")
    )
    pass_condition = (
        source_confirms_test11_enumerate
        and enable_contract_complete
        and dts_contract_present
        and v1496_rc1_failure_fixed
        and downstream_absent
    )
    if pass_condition:
        decision = "v1498-msm-pcie-test11-enumerate-path-confirmed-endpoint-response-gap"
        reason = (
            "Public pci-msm source maps debugfs TEST:11 to the enumerate path, and enumerate calls msm_pcie_enable(PM_ALL). "
            "The device DTS binds RC1 to PERST GPIO102, wake GPIO104, pcie_1 clocks/resets, and SDX50M/MHI. "
            "V1496 therefore did exercise the intended RC1 enumerate/link-training path, but the endpoint still failed before L0."
        )
        next_gate = (
            "V1499 should be source/build-only: add a pre-L0 endpoint parity observer that captures RC1 PERST/refclk/clock/GDSC/GPIO102/GPIO103/GPIO104/"
            "GPIO135/GPIO142 and LTSSM timing around the provider-trigger plus corrected RC1 enumerate window. Do not start Wi-Fi HAL or use credentials."
        )
    else:
        decision = "v1498-msm-pcie-test11-static-analysis-needs-review"
        reason = "The source, DTS, or V1496 evidence did not satisfy the TEST:11 enumerate-path contract."
        next_gate = "Review missing classifier fields before any new live test boot or lower-level write."

    return {
        "cycle": "V1498",
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "inputs": {
            "v1496_dir": rel(args.v1496_dir),
            "pcie_source": source_meta,
            "dts": dts["files"],
        },
        "source_analysis": source,
        "dts_analysis": dts,
        "v1496": v1496,
        "classification": {
            "source_confirms_test11_enumerate": source_confirms_test11_enumerate,
            "enable_contract_complete": enable_contract_complete,
            "dts_contract_present": dts_contract_present,
            "v1496_rc1_failure_fixed": v1496_rc1_failure_fixed,
            "downstream_absent": downstream_absent,
            "firmware_mhi_wlfw_deep_dive_deferred_until_l0": pass_condition,
            "debugfs_case_number_not_primary_suspect": pass_condition,
            "remaining_gap": "pre-L0 endpoint response / PERST-refclk-power-sequence parity",
        },
        "guardrails": {
            "host_only": True,
            "device_command_executed": False,
            "flash_executed": False,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "pci_debugfs_write_executed_by_classifier": False,
        },
        "next_gate": next_gate,
    }


def md_bool(value: Any) -> str:
    return f"`{value}`"


def render_report(result: dict[str, Any]) -> str:
    source = result["source_analysis"]
    dts = result["dts_analysis"]
    v1496 = result["v1496"]
    pcie1 = dts["pcie1"]
    lines = [
        "# Native Init V1498 MSM PCIe TEST:11 Static Analysis",
        "",
        "## Summary",
        "",
        "- Cycle: `V1498`",
        "- Type: host-only static classifier over V1496 evidence, local DTS, and public `pci-msm.c` reference source",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- V1496 evidence: `{result['inputs']['v1496_dir']}`",
        f"- Public PCIe source reference: {result['inputs']['pcie_source'].get('url') or result['inputs']['pcie_source'].get('path')}",
        "",
        "## V1496 Failure Fixed Point",
        "",
        f"- V1496 decision: `{v1496['manifest_decision']}`",
        f"- handoff/rollback pass: `{v1496['handoff_pass']}` / `{v1496['rollback_ok']}`",
        f"- corrected RC1 enumerate dmesg confirmed: `{v1496['watcher']['debugfs_write_confirmed']}`",
        f"- provider trigger: `{v1496['progress']['provider_trigger']}`",
        f"- RC1 progress: `{v1496['progress']['rc1_progress']}`",
        f"- RC1 L0: `{v1496['progress']['rc1_l0']}`",
        f"- RC1 link failed: `{v1496['progress']['rc1_link_failed']}`",
        f"- MHI/WLFW/BDF/FW-ready/wlan0: `{v1496['progress']['mhi_progress']}` / `{v1496['progress']['wlfw_progress']}` / `{v1496['progress']['bdf_progress']}` / `{v1496['progress']['fw_ready_progress']}` / `{v1496['progress']['wlan0_present']}`",
        f"- case after provider ms: `{v1496['derived'].get('case_after_provider_ms')}`",
        f"- PHY ready after case ms: `{v1496['derived'].get('phy_ready_after_case_ms')}`",
        f"- link fail after case ms: `{v1496['derived'].get('link_fail_after_case_ms')}`",
        "",
        "## TEST:11 Source Contract",
        "",
        f"- `MSM_PCIE_ENUMERATION` enum value: `{source['enum']['value']}`",
        f"- enum line range: `{source['enum']['line_start']}-{source['enum']['line_end']}`",
        f"- TEST case line range: `{source['case_enumeration']['line_start']}-{source['case_enumeration']['line_end']}`",
        f"- TEST case calls `msm_pcie_enumerate`: `{source['case_enumeration']['calls_msm_pcie_enumerate']}`",
        f"- `msm_pcie_enumerate` line range: `{source['functions']['msm_pcie_enumerate']['line_start']}-{source['functions']['msm_pcie_enumerate']['line_end']}`",
        f"- `msm_pcie_enumerate` calls `msm_pcie_enable(dev, PM_ALL)`: `{source['functions']['msm_pcie_enumerate']['calls_msm_pcie_enable_pm_all']}`",
        f"- `msm_pcie_enable` line range: `{source['functions']['msm_pcie_enable']['line_start']}-{source['functions']['msm_pcie_enable']['line_end']}`",
        "",
        "The relevant public `pci-msm.c` source maps debugfs TEST case `11` to the",
        "enumeration path. That path calls the same enable routine that covers the",
        "PERST, vreg, clock, PHY, pipe-clock, LTSSM, and link-check sequence used by",
        "the observed RC1 dmesg markers. Samsung's exact vendor driver source is not",
        "present in the local OSRC tree, so this remains a reference-source",
        "classifier; matching dmesg strings make it actionable, but live evidence",
        "still has priority.",
        "",
        "## Enable-path Operations Seen In Source",
        "",
    ]
    for key, value in source["functions"]["msm_pcie_enable"]["keywords"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Local DTS Contract",
        "",
        f"- `pcie1` file: `{dts['files']['pcie_dts']}`",
        f"- `pcie1` line range: `{pcie1['line_start']}-{pcie1['line_end']}`",
        f"- compatible: `{pcie1['compatible']}`",
        f"- cell-index: `{pcie1['cell_index']}`",
        f"- PERST GPIO: `{pcie1['perst_gpio']}`",
        f"- WAKE GPIO: `{pcie1['wake_gpio']}`",
        f"- GDSC supply: `{pcie1['gdsc_supply']}`",
        f"- vreg supplies: `{pcie1['vreg_1v8_supply']}`, `{pcie1['vreg_0v9_supply']}`, `{pcie1['vreg_cx_supply']}`",
        f"- clock names: `{', '.join(pcie1['clock_names'])}`",
        f"- reset names: `{', '.join(pcie1['reset_names'])}`",
        f"- RC1 bridge PCI ID: `{dts['pcie_rc1']['pci_ids']}`",
        f"- MHI PCI IDs: `{dts['mhi_0']['pci_ids']}`",
        f"- SDX50M compatible/link-info: `{dts['sdx50m']['mdm3_compatible']}` / `{dts['sdx50m']['mdm_link_info']}`",
        f"- MHI eSoC mapping: `{dts['sdx50m']['esoc_names']}` / `{dts['sdx50m']['esoc_0']}`",
        "",
        "## Interpretation",
        "",
        "- V1496 no longer supports a provider-entry failure model: provider trigger occurred and RC1 entered PHY/LTSSM progress.",
        "- TEST:11 is not just a no-op status probe in the reference source; it is the enumerate path and reaches `msm_pcie_enable(PM_ALL)`.",
        "- The failure is still pre-L0: LTSSM reaches polling/compliance and then link initialization fails; no downstream MHI/WLFW/BDF/FW-ready/`wlan0` marker appears.",
        "- Firmware, MHI pipe, WLFW, BDF, scan/connect, credentials, DHCP/routes, and external ping stay parked until RC1 reaches L0 and PCI enumeration exists.",
        "",
        "## Safety Scope",
        "",
        "This classifier was host-only. It fetched/read source and local DTS files,",
        "parsed existing V1496 evidence, and wrote private evidence output. It did",
        "not issue device commands, flash, reboot, start Wi-Fi HAL, scan/connect,",
        "use credentials, configure DHCP/routes, perform external ping, write",
        "PMIC/GPIO/GDSC controls, or write pci-msm debugfs controls.",
        "",
        "## Next",
        "",
        result["next_gate"],
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1496-dir", type=Path, default=DEFAULT_V1496_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--pcie-source", type=Path, default=None)
    parser.add_argument("--pcie-source-url", default=DEFAULT_PCIE_SOURCE_URL)
    parser.add_argument("--fetch-timeout", type=float, default=30.0)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = classify(args)
    report = render_report(result)
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "out_dir": rel(args.out_dir),
        "next_gate": result["next_gate"],
    }, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
