#!/usr/bin/env python3
"""V850 host-only ext-mdm powerup surface classifier.

V849 captured a blocked `subsys_esoc0` holder in `mdm_subsys_powerup`. This
classifier correlates that stack with DTS GPIO/IRQ contracts, available OSRC
source gaps, native surface evidence, and Android reference evidence to select
the next safe gate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v850-ext-mdm-powerup-surface-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v850-ext-mdm-powerup-surface-classifier.txt")
DEFAULT_V845_MANIFEST = Path("tmp/wifi/v845-mdm3-ext-sdx50m-surface-snapshot/manifest.json")
DEFAULT_V849_MANIFEST = Path("tmp/wifi/v849-subsys-esoc0-wait-state-sampler/manifest.json")
DEFAULT_V849_EVIDENCE = Path("tmp/wifi/v849-subsys-esoc0-wait-state-sampler")
DEFAULT_ANDROID_REPORT = Path("docs/reports/NATIVE_INIT_V591_ANDROID_SUBSYS_STATE_HANDOFF_2026-05-22.md")
DEFAULT_SOURCE_ROOT = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel")

DTS = Path("arch/arm64/boot/dts/samsung/renovation/sm8150-sec-r3q-kor-overlay-r02.dts")
GENERIC_SDX = Path("arch/arm64/boot/dts/qcom/sdx5xm-external-soc.dtsi")
PINCTRL = Path("arch/arm64/boot/dts/qcom/sm8150-pinctrl.dtsi")
DEFCONFIG = Path("arch/arm64/configs/r3q_kor_single_defconfig")
SUBSYSTEM_RESTART = Path("drivers/soc/qcom/subsystem_restart.c")
MHI_ARCH = Path("drivers/bus/mhi/controllers/mhi_arch_qcom.c")
ICNSS = Path("drivers/soc/qcom/icnss.c")
ESOC_PROVIDER_CANDIDATES = (
    Path("drivers/soc/qcom/esoc-mdm.c"),
    Path("drivers/soc/qcom/esoc_mdm.c"),
    Path("drivers/soc/qcom/esoc-mdm-4x.c"),
    Path("drivers/soc/qcom/esoc_mdm_4x.c"),
    Path("drivers/soc/qcom/esoc-mdm-drv.c"),
    Path("drivers/soc/qcom/esoc_mdm_drv.c"),
)

EXPECTED_V845 = "v845-mdm3-ext-sdx50m-surface-captured"
EXPECTED_V849 = {
    "v849-subsys-esoc0-block-provider-powerup-or-opaque",
    "v849-subsys-esoc0-block-in-mdm-subsys-powerup",
}


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: Any
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v845-manifest", type=Path, default=DEFAULT_V845_MANIFEST)
    parser.add_argument("--v849-manifest", type=Path, default=DEFAULT_V849_MANIFEST)
    parser.add_argument("--v849-evidence", type=Path, default=DEFAULT_V849_EVIDENCE)
    parser.add_argument("--android-report", type=Path, default=DEFAULT_ANDROID_REPORT)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "error": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "error": "not-json-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def nested(data: Any, *keys: Any) -> Any:
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            return None
    return current


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass"}


def line_of(text: str, pattern: str, flags: int = 0) -> int | None:
    regex = re.compile(pattern, flags)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return None


def source_info(root: Path, relative: Path) -> dict[str, Any]:
    resolved = repo_path(root / relative)
    return {
        "path": str(resolved),
        "exists": resolved.exists(),
        "size": resolved.stat().st_size if resolved.exists() else None,
    }


def parse_defconfig(text: str, names: list[str]) -> dict[str, str]:
    values = {name: "missing" for name in names}
    for raw in text.splitlines():
        line = raw.strip()
        for name in names:
            if line == f"{name}=y":
                values[name] = "y"
            elif line == f"{name}=m":
                values[name] = "m"
            elif line == f"# {name} is not set":
                values[name] = "n"
    return values


def extract_mdm3_block(text: str) -> str:
    start = text.find("qcom,mdm3 {")
    if start < 0:
        return ""
    depth = 0
    entered = False
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
            entered = True
        elif char == "}":
            depth -= 1
            if entered and depth == 0:
                return text[start:index + 1]
    return ""


def extract_property(block: str, name: str) -> str:
    match = re.search(rf"{re.escape(name)}\s*=\s*([^;]+);", block)
    return match.group(1).strip().strip('"') if match else ""


def grep_lines(text: str, pattern: str, limit: int = 24) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    matches: list[str] = []
    for line in text.splitlines():
        if regex.search(line):
            matches.append(line.strip())
        if len(matches) >= limit:
            break
    return matches


def analyze_v849(v849: dict[str, Any], evidence_root: Path) -> dict[str, Any]:
    sample_start = read_text(evidence_root / "native/sample-after-start.txt")
    sample_observe = read_text(evidence_root / "native/sample-after-observe.txt")
    dmesg = read_text(evidence_root / "native/dmesg-after-observe.txt")
    module_surface = read_text(evidence_root / "native/module-surface-after-start.txt")
    combined = sample_start + "\n" + sample_observe
    lower = combined.lower()
    dmesg_lower = dmesg.lower()
    module_lower = module_surface.lower()
    return {
        "decision": v849.get("decision"),
        "pass": bool_value(v849.get("pass")),
        "runner_reason": v849.get("reason"),
        "branch": nested(v849, "live", "branch"),
        "branch_reason": nested(v849, "live", "branch_reason"),
        "holder_opened": nested(v849, "live", "holder_opened"),
        "mdm3_online": nested(v849, "live", "mdm3_online"),
        "markers": nested(v849, "live", "markers"),
        "cleanup": nested(v849, "live", "reboot_cleanup"),
        "stack": {
            "mdm_subsys_powerup": "mdm_subsys_powerup" in lower,
            "d_state": "State:\tD" in combined or "State: D" in combined,
            "subsystem_get": "__subsystem_get" in lower,
            "subsys_device_open": "subsys_device_open" in lower,
            "wait_for_err_ready": "wait_for_err_ready" in lower or "before wait_for_err_ready" in dmesg_lower,
            "mhi_hook": any(term in lower for term in ("mhi_arch_esoc_ops_power_on", "mhi_pci_probe", "msm_pcie")),
            "focused_lines": grep_lines(combined, r"mdm_subsys_powerup|__subsystem_get|subsys_device_open|State:\s*[DS]|wchan|stack|wait_for_err_ready|mhi|pcie", limit=40),
        },
        "dmesg": {
            "ext_mdm_boot_lines": grep_lines(dmesg, r"ext-mdm|mdm3|MDM_PMIC|mdm_configure_ipc|subsystem_get|wait_for_err_ready|mhi|wlfw|wlan0", limit=40),
            "cannot_config_pmic_power_status": "cannot config mdm_pmic_pwr_status" in dmesg_lower,
            "ap2mdm_errfatal2_remap": "ap2mdm_errfatal2" in dmesg_lower,
            "wait_for_err_ready": "wait_for_err_ready" in dmesg_lower,
            "mhi": "mhi" in dmesg_lower,
            "wlfw": "wlfw" in dmesg_lower,
            "wlan0": "wlan0" in dmesg_lower,
        },
        "module_surface": {
            "has_ext_mdm_module": "ext" in module_lower and "mdm" in module_lower,
            "has_esoc_module": "esoc" in module_lower,
            "has_mhi_qcom": "/sys/module/mhi_qcom" in module_surface,
            "has_icnss": "/sys/module/icnss" in module_surface,
            "has_wlan": "/sys/module/wlan" in module_surface,
            "lines": grep_lines(module_surface, r"MODULE|mhi_qcom|icnss|wlan|esoc|mdm", limit=40),
        },
    }


def analyze_v845(v845: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": v845.get("decision"),
        "pass": bool_value(v845.get("pass")),
        "mdm3_state": nested(v845, "analysis", "mdm3_state"),
        "mss_state": nested(v845, "analysis", "mss_state"),
        "mdm3_sysfs_present": nested(v845, "analysis", "mdm3_sysfs_present"),
        "esoc_bus_present": nested(v845, "analysis", "esoc_bus_present"),
        "esoc0_sysfs_present": nested(v845, "analysis", "esoc0_sysfs_present"),
        "subsys_esoc0_present": nested(v845, "analysis", "subsys_esoc0_present"),
        "gpio_debug_readable": nested(v845, "analysis", "gpio_debug_readable"),
        "gpio135_exported": nested(v845, "analysis", "gpio135_exported"),
        "gpio142_exported": nested(v845, "analysis", "gpio142_exported"),
        "dev_esoc_node_present": nested(v845, "analysis", "dev_esoc_node_present"),
        "dev_subsys_node_present": nested(v845, "analysis", "dev_subsys_node_present"),
        "writable_existing_control_candidates": nested(v845, "analysis", "writable_existing_control_candidates"),
    }


def analyze_android(report_text: str) -> dict[str, Any]:
    return {
        "report_present": bool(report_text),
        "mss_online": "mss_state=ONLINE" in report_text,
        "mdm3_online": "mdm3_state=ONLINE" in report_text,
        "wlan_pd": "has_wlan_pd=True" in report_text,
        "service_notifier": "has_service_notifier=True" in report_text,
        "no_wifi_bringup": "No Wi-Fi enable command" in report_text and "No external ping" in report_text,
    }


def analyze_sources(source_root: Path) -> dict[str, Any]:
    dts = read_text(source_root / DTS)
    generic = read_text(source_root / GENERIC_SDX)
    pinctrl = read_text(source_root / PINCTRL)
    defconfig = read_text(source_root / DEFCONFIG)
    subsystem = read_text(source_root / SUBSYSTEM_RESTART)
    mhi_arch = read_text(source_root / MHI_ARCH)
    icnss = read_text(source_root / ICNSS)
    mdm3_block = extract_mdm3_block(dts)
    generic_block = extract_mdm3_block(generic)
    esoc_configs = parse_defconfig(defconfig, [
        "CONFIG_ESOC",
        "CONFIG_ESOC_DEV",
        "CONFIG_ESOC_CLIENT",
        "CONFIG_ESOC_MDM_4x",
        "CONFIG_ESOC_MDM_DRV",
        "CONFIG_ESOC_MDM_DBG_ENG",
    ])
    provider_candidates = {
        str(path): source_info(source_root, path)
        for path in ESOC_PROVIDER_CANDIDATES
    }
    provider_present = any(info["exists"] for info in provider_candidates.values())
    return {
        "sources": {
            str(DTS): source_info(source_root, DTS),
            str(GENERIC_SDX): source_info(source_root, GENERIC_SDX),
            str(PINCTRL): source_info(source_root, PINCTRL),
            str(DEFCONFIG): source_info(source_root, DEFCONFIG),
            str(SUBSYSTEM_RESTART): source_info(source_root, SUBSYSTEM_RESTART),
            str(MHI_ARCH): source_info(source_root, MHI_ARCH),
            str(ICNSS): source_info(source_root, ICNSS),
        },
        "dts": {
            "mdm3_line": line_of(dts, r"qcom,mdm3\s*\{"),
            "compatible": extract_property(mdm3_block, "compatible"),
            "sysmon_id": extract_property(mdm3_block, "qcom,sysmon-id"),
            "ssctl_instance_id": extract_property(mdm3_block, "qcom,ssctl-instance-id"),
            "interrupt_names": extract_property(mdm3_block, "interrupt-names"),
            "interrupt_map": extract_property(mdm3_block, "interrupt-map"),
            "mdm2ap_errfatal_gpio": extract_property(mdm3_block, "qcom,mdm2ap-errfatal-gpio"),
            "ap2mdm_errfatal_gpio": extract_property(mdm3_block, "qcom,ap2mdm-errfatal-gpio"),
            "mdm2ap_status_gpio": extract_property(mdm3_block, "qcom,mdm2ap-status-gpio"),
            "ap2mdm_status_gpio": extract_property(mdm3_block, "qcom,ap2mdm-status-gpio"),
            "ap2mdm_soft_reset_gpio": extract_property(mdm3_block, "qcom,ap2mdm-soft-reset-gpio"),
            "support_shutdown": "qcom,support-shutdown" in mdm3_block,
            "pil_force_shutdown": "qcom,pil-force-shutdown" in mdm3_block,
            "skip_restart_for_mdm_crash": "qcom,esoc-skip-restart-for-mdm-crash" in mdm3_block,
        },
        "generic_sdx": {
            "mdm3_line": line_of(generic, r"mdm3:\s*qcom,mdm3"),
            "interrupt_map": extract_property(generic_block, "interrupt-map"),
            "mdm2ap_status_gpio": extract_property(generic_block, "qcom,mdm2ap-status-gpio"),
            "ap2mdm_status_gpio": extract_property(generic_block, "qcom,ap2mdm-status-gpio"),
            "ap2mdm_soft_reset_gpio": extract_property(generic_block, "qcom,ap2mdm-soft-reset-gpio"),
        },
        "pinctrl": {
            "ap2mdm_active_line": line_of(pinctrl, r"ap2mdm_active"),
            "mdm2ap_active_line": line_of(pinctrl, r"mdm2ap_active"),
            "gpio135": line_of(pinctrl, r"gpio135"),
            "gpio141": line_of(pinctrl, r"gpio141"),
            "gpio142": line_of(pinctrl, r"gpio142"),
            "gpio53": line_of(pinctrl, r"gpio53"),
        },
        "defconfig": {
            "esoc_configs": esoc_configs,
            "esoc_mdm_enabled": esoc_configs.get("CONFIG_ESOC_MDM_4x") == "y" and esoc_configs.get("CONFIG_ESOC_MDM_DRV") == "y",
        },
        "source_gaps": {
            "provider_candidates": provider_candidates,
            "provider_present": provider_present,
            "provider_absent_despite_config": esoc_configs.get("CONFIG_ESOC_MDM_4x") == "y" and esoc_configs.get("CONFIG_ESOC_MDM_DRV") == "y" and not provider_present,
            "mdm_subsys_powerup_source_present": line_of("\n".join([subsystem, mhi_arch, icnss]), r"mdm_subsys_powerup") is not None,
        },
        "hooks": {
            "subsys_start_powerup": line_of(subsystem, r"ret = subsys->desc->powerup\(subsys->desc\)"),
            "wait_for_err_ready": line_of(subsystem, r"static int wait_for_err_ready"),
            "mhi_esoc_power_on": line_of(mhi_arch, r"mhi_arch_esoc_ops_power_on"),
            "mhi_pci_probe": line_of(mhi_arch, r"mhi_pci_probe"),
            "icnss_register_esoc_client": line_of(icnss, r"icnss_register_esoc_client"),
        },
    }


def check(name: str, status: bool, detail: Any, next_step: str, severity: str = "blocker") -> Check:
    return Check(name, "pass" if status else "blocked", severity, detail, next_step)


def finding(name: str, detail: Any, next_step: str) -> Check:
    return Check(name, "finding", "info", detail, next_step)


def candidate(name: str, classification: str, reason: str, next_step: str) -> dict[str, str]:
    return {
        "candidate": name,
        "classification": classification,
        "reason": reason,
        "next_step": next_step,
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    source_root = repo_path(args.source_root)
    v845 = load_json(args.v845_manifest)
    v849 = load_json(args.v849_manifest)
    android_text = read_text(args.android_report)
    v849_analysis = analyze_v849(v849, repo_path(args.v849_evidence))
    v845_analysis = analyze_v845(v845)
    android = analyze_android(android_text)
    sources = analyze_sources(source_root)
    checks = [
        check(
            "v845-surface-input",
            v845.get("decision") == EXPECTED_V845 and bool_value(v845.get("pass")),
            {"decision": v845.get("decision"), "pass": v845.get("pass"), "mdm3_state": v845_analysis["mdm3_state"]},
            "refresh read-only mdm3/eSoC surface snapshot",
        ),
        check(
            "v849-wait-state-input",
            v849.get("decision") in EXPECTED_V849 and bool_value(v849.get("pass")),
            {"decision": v849.get("decision"), "pass": v849.get("pass"), "branch": v849_analysis["branch"]},
            "refresh V849 bounded wait-state sampler",
        ),
        check(
            "mdm-subsys-powerup-branch",
            bool_value(nested(v849_analysis, "stack", "mdm_subsys_powerup"))
            and bool_value(nested(v849_analysis, "stack", "d_state"))
            and not bool_value(nested(v849_analysis, "stack", "wait_for_err_ready")),
            v849_analysis["stack"],
            "treat current blocker as provider powerup wait, not wait_for_err_ready or upper Wi-Fi",
        ),
        check(
            "android-positive-mdm3-reference",
            bool_value(android["mss_online"]) and bool_value(android["mdm3_online"]) and bool_value(android["wlan_pd"]),
            android,
            "use Android as proof that the same hardware can bring mdm3/WLAN-PD up",
        ),
        check(
            "dts-handshake-surface",
            sources["dts"]["compatible"] == "qcom,ext-sdx50m"
            and "0x87" in sources["dts"]["ap2mdm_status_gpio"].lower()
            and "0x8e" in sources["dts"]["mdm2ap_status_gpio"].lower()
            and bool_value(sources["dts"]["support_shutdown"]),
            sources["dts"],
            "read only GPIO/IRQ/platform surface before considering any state-changing trigger",
        ),
        check(
            "provider-source-gap",
            bool_value(nested(sources, "source_gaps", "provider_absent_despite_config"))
            and not bool_value(nested(sources, "source_gaps", "mdm_subsys_powerup_source_present")),
            sources["source_gaps"],
            "do not infer provider internals from absent source; collect live read-only symbols/surfaces",
        ),
        finding(
            "boot-dmesg-provider-hints",
            v849_analysis["dmesg"],
            "preserve ext-mdm boot hints such as MDM_PMIC_PWR_STATUS and AP2MDM remap for V851",
        ),
        finding(
            "module-surface-gap",
            v849_analysis["module_surface"],
            "ext-mdm appears built-in or otherwise not exposed as a standalone module; use platform/sysfs/kallsyms next",
        ),
    ]
    blocked = [item.name for item in checks if item.status == "blocked" and item.severity == "blocker"]
    candidates = [
        candidate(
            "blind longer `subsys_esoc0` open",
            "reject",
            "V849 captured a D-state wait in `mdm_subsys_powerup`; waiting longer does not identify the missing GPIO/IRQ/provider precondition",
            "collect read-only provider surface first",
        ),
        candidate(
            "direct GPIO/sysfs write or raw eSoC ioctl",
            "reject",
            "The provider source is absent, `mdm_subsys_powerup` blocks in kernel context, and V845 only proves writable-looking sysfs modes, not safe store semantics",
            "keep writes/ioctls blocked until a source-backed or Android-backed trigger is identified",
        ),
        candidate(
            "MHI `power_up` write",
            "reject-now",
            "V849 does not reach MHI hook symbols; mdm_subsys_powerup blocks before visible MHI/WLFW progression",
            "do not bypass ext-mdm provider with MHI writes yet",
        ),
        candidate(
            "Wi-Fi HAL/scan/connect",
            "reject",
            "mdm3 remains OFFLINING and WLFW/BDF/wlan0 are absent, so upper Wi-Fi cannot satisfy the final ping goal",
            "stay below HAL until mdm3/WLFW state advances",
        ),
        candidate(
            "read-only ext-mdm provider surface snapshot",
            "select-next",
            "The next unknown is provider-visible GPIO/IRQ/platform/symbol state around `mdm_subsys_powerup`, and those can be collected without writes",
            "V851 should capture `/proc/kallsyms` filtered symbols, `/proc/interrupts`, platform driver/sysfs/of_node/power state, eSoC sysfs, msm_subsys state, read-only GPIO/debug/pinctrl if available, and ext-mdm dmesg; no writes or opens",
        ),
    ]
    result = {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v850",
        "host": collect_host_metadata(),
        "inputs": {
            "v845": {"path": str(repo_path(args.v845_manifest)), "decision": v845.get("decision"), "pass": bool_value(v845.get("pass"))},
            "v849": {"path": str(repo_path(args.v849_manifest)), "evidence": str(repo_path(args.v849_evidence)), "decision": v849.get("decision"), "pass": bool_value(v849.get("pass"))},
            "android_report": str(repo_path(args.android_report)),
            "source_root": str(source_root),
        },
        "v845_analysis": v845_analysis,
        "v849_analysis": v849_analysis,
        "android_reference": android,
        "sources": sources,
        "checks": [asdict(item) for item in checks],
        "candidate_matrix": candidates,
        "device_commands_executed": False,
        "device_mutations": False,
        "raw_esoc_open_executed": False,
        "subsys_char_open_executed": False,
        "gpio_write_executed": False,
        "sysfs_write_executed": False,
        "module_load_unload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
    }
    if args.command == "plan":
        result.update({
            "decision": "v850-ext-mdm-powerup-surface-classifier-plan-ready",
            "pass": True,
            "reason": "plan-only; no device command or mutation executed",
            "next_step": "run V850 host-only classifier",
        })
    elif blocked:
        result.update({
            "decision": "v850-ext-mdm-powerup-surface-classifier-blocked",
            "pass": False,
            "reason": "blocked by " + ", ".join(blocked),
            "next_step": "refresh blocked evidence before any provider-surface follow-up",
        })
    else:
        result.update({
            "decision": "v850-ext-mdm-powerup-surface-selected",
            "pass": True,
            "reason": "V849 places the blocker in built-in/proprietary `mdm_subsys_powerup`; Android proves mdm3 can reach ONLINE, while DTS maps the AP2MDM/MDM2AP GPIO and IRQ contract and OSRC lacks provider source",
            "next_step": "V851 should run a live read-only ext-mdm provider surface snapshot: filtered kallsyms, interrupts, platform driver/sysfs/of_node/power state, eSoC/sysfs, msm_subsys state, readable GPIO/debug/pinctrl if available, and focused dmesg; no raw eSoC open, GPIO/sysfs writes, HAL/connect, DHCP/routes, external ping, or boot-image work",
        })
    return result


def render_summary(result: dict[str, Any]) -> str:
    checks = result["checks"]
    candidates = result["candidate_matrix"]
    dts = result["sources"]["dts"]
    stack = result["v849_analysis"]["stack"]
    dmesg = result["v849_analysis"]["dmesg"]
    rows = [
        ["v849_decision", result["inputs"]["v849"]["decision"]],
        ["mdm_subsys_powerup", stack["mdm_subsys_powerup"]],
        ["d_state", stack["d_state"]],
        ["wait_for_err_ready_seen", stack["wait_for_err_ready"]],
        ["mhi_hook_seen", stack["mhi_hook"]],
        ["android_mdm3_online", result["android_reference"]["mdm3_online"]],
        ["native_v845_mdm3_state", result["v845_analysis"]["mdm3_state"]],
        ["provider_source_absent", result["sources"]["source_gaps"]["provider_absent_despite_config"]],
        ["dmesg_pmic_status_hint", dmesg["cannot_config_pmic_power_status"]],
        ["dmesg_ap2mdm_remap_hint", dmesg["ap2mdm_errfatal2_remap"]],
    ]
    dts_rows = [
        ["compatible", dts["compatible"]],
        ["sysmon_id", dts["sysmon_id"]],
        ["ssctl_instance_id", dts["ssctl_instance_id"]],
        ["interrupt_names", dts["interrupt_names"]],
        ["interrupt_map", dts["interrupt_map"]],
        ["mdm2ap_errfatal_gpio", dts["mdm2ap_errfatal_gpio"]],
        ["ap2mdm_errfatal_gpio", dts["ap2mdm_errfatal_gpio"]],
        ["mdm2ap_status_gpio", dts["mdm2ap_status_gpio"]],
        ["ap2mdm_status_gpio", dts["ap2mdm_status_gpio"]],
        ["ap2mdm_soft_reset_gpio", dts["ap2mdm_soft_reset_gpio"]],
    ]
    return "\n".join([
        "# V850 ext-mdm Powerup Surface Classifier",
        "",
        f"- generated: `{result['generated_at']}`",
        f"- command: `{result['command']}`",
        f"- decision: `{result['decision']}`",
        f"- pass: `{result['pass']}`",
        f"- reason: {result['reason']}",
        f"- next_step: {result['next_step']}",
        f"- device_commands_executed: `{result['device_commands_executed']}`",
        f"- raw_esoc_open_executed: `{result['raw_esoc_open_executed']}`",
        f"- sysfs_write_executed: `{result['sysfs_write_executed']}`",
        f"- gpio_write_executed: `{result['gpio_write_executed']}`",
        f"- wifi_hal_start_executed: `{result['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{result['scan_connect_executed']}`",
        f"- external_ping_executed: `{result['external_ping_executed']}`",
        "",
        "## Key Classification",
        "",
        markdown_table(["signal", "value"], rows),
        "",
        "## DTS Handshake Surface",
        "",
        markdown_table(["property", "value"], dts_rows),
        "",
        "## Checks",
        "",
        markdown_table(
            ["name", "status", "severity", "detail", "next"],
            [[item["name"], item["status"], item["severity"], json.dumps(item["detail"], ensure_ascii=False, sort_keys=True), item["next_step"]] for item in checks],
        ),
        "",
        "## Candidate Matrix",
        "",
        markdown_table(
            ["candidate", "classification", "reason", "next"],
            [[item["candidate"], item["classification"], item["reason"], item["next_step"]] for item in candidates],
        ),
        "",
    ])


def persist(result: dict[str, Any], out_dir: Path) -> None:
    evidence = EvidenceStore(repo_path(out_dir))
    evidence.write_json("manifest.json", result)
    evidence.write_text("summary.md", render_summary(result))
    write_private_text(repo_path(LATEST_POINTER), str(repo_path(out_dir)) + "\n")


def main() -> int:
    args = parse_args()
    result = classify(args)
    persist(result, args.out_dir)
    print(f"decision: {result['decision']}")
    print(f"pass: {result['pass']}")
    print(f"reason: {result['reason']}")
    print(f"next: {result['next_step']}")
    print(f"device_commands_executed: {result['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {result['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {result['scan_connect_executed']}")
    print(f"external_ping_executed: {result['external_ping_executed']}")
    print(f"evidence: {repo_path(args.out_dir)}")
    return 0 if bool_value(result["pass"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
