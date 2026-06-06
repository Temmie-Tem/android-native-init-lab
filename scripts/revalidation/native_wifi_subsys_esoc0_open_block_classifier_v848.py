#!/usr/bin/env python3
"""V848 host-only subsys_esoc0 open-block boundary classifier.

V847 proved that a materialized `/dev/subsys_esoc0` open reaches
`__subsystem_get(esoc0)` but does not report open completion within the bounded
window. This classifier folds the V847 evidence back into the Samsung OSRC
`subsystem_restart.c` path and selects the next non-blind live observation.
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
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v848-subsys-esoc0-open-block-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v848-subsys-esoc0-open-block-classifier.txt")
DEFAULT_V846_MANIFEST = Path("tmp/wifi/v846-mdm3-esoc-state-control-contract/manifest.json")
DEFAULT_V847_MANIFEST = Path("tmp/wifi/v847-subsys-esoc0-char-open-smoke/manifest.json")
DEFAULT_V847_EVIDENCE = Path("tmp/wifi/v847-subsys-esoc0-char-open-smoke")
DEFAULT_SOURCE_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel')

SUBSYSTEM_RESTART = Path("drivers/soc/qcom/subsystem_restart.c")
ESOC_CLIENT = Path("include/linux/esoc_client.h")
ESOC_UAPI = Path("include/uapi/linux/esoc_ctrl.h")
MHI_ARCH = Path("drivers/bus/mhi/controllers/mhi_arch_qcom.c")
MHI_QCOM = Path("drivers/bus/mhi/controllers/mhi_qcom.c")
ICNSS = Path("drivers/soc/qcom/icnss.c")
DEFCONFIG = Path("arch/arm64/configs/r3q_kor_single_defconfig")
SDX_EXT_IPC = Path("drivers/soc/qcom/sdx_ext_ipc.c")
ESOC_PROVIDER_CANDIDATES = (
    Path("drivers/soc/qcom/esoc-mdm.c"),
    Path("drivers/soc/qcom/esoc_mdm.c"),
    Path("drivers/soc/qcom/esoc-mdm-4x.c"),
    Path("drivers/soc/qcom/esoc_mdm_4x.c"),
    Path("drivers/soc/qcom/esoc-mdm-drv.c"),
    Path("drivers/soc/qcom/esoc_mdm_drv.c"),
)

EXPECTED_V846 = "v846-mdm3-esoc-char-open-contract-selected"
EXPECTED_V847 = "v847-subsys-esoc0-open-blocked-or-pending"


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
    parser.add_argument("--v846-manifest", type=Path, default=DEFAULT_V846_MANIFEST)
    parser.add_argument("--v847-manifest", type=Path, default=DEFAULT_V847_MANIFEST)
    parser.add_argument("--v847-evidence", type=Path, default=DEFAULT_V847_EVIDENCE)
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


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass"}


def nested(data: Any, *keys: Any) -> Any:
    current: Any = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            return None
    return current


def line_of(text: str, pattern: str, flags: int = 0) -> int | None:
    regex = re.compile(pattern, flags)
    for line_number, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return line_number
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
    for raw_line in text.splitlines():
        line = raw_line.strip()
        for name in names:
            if line == f"{name}=y":
                values[name] = "y"
            elif line == f"{name}=m":
                values[name] = "m"
            elif line == f"# {name} is not set":
                values[name] = "n"
    return values


def grep_lines(text: str, pattern: str, limit: int = 16) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    matches: list[str] = []
    for line in text.splitlines():
        if regex.search(line):
            matches.append(line.strip())
            if len(matches) >= limit:
                break
    return matches


def section_has(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE))


def extract_holder_ids(text: str) -> dict[str, str]:
    ids: dict[str, str] = {}
    for line in text.splitlines():
        if "v847.holder.pid=" in line:
            ids["wrapper_pid"] = line.split("=", 1)[1].strip()
        if "holder.start.pid=" in line:
            ids["inner_pid"] = line.split("=", 1)[1].strip()
    return ids


def extract_state_file_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    current_path = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("FILE "):
            current_path = line.split(" ", 1)[1]
            continue
        if not line or line.startswith("== ") or line.startswith("lrwx"):
            continue
        if current_path.endswith("/name") and "subsys9" in current_path:
            values["subsys9_name"] = line
        elif current_path.endswith("/state") and "subsys9" in current_path:
            values["subsys9_state"] = line
        elif current_path.endswith("/firmware_name") and "subsys9" in current_path:
            values["subsys9_firmware_name"] = line
        elif current_path.endswith("/state") and "subsys0" in current_path:
            values["subsys0_state"] = line
    return values


def analyze_v847(v847: dict[str, Any], evidence_root: Path) -> dict[str, Any]:
    start_holder = read_text(evidence_root / "native/start-holder.txt")
    status_start = read_text(evidence_root / "native/status-after-start.txt")
    status_observe = read_text(evidence_root / "native/status-after-observe.txt")
    state_observe = read_text(evidence_root / "native/state-after-observe.txt")
    dmesg_observe = read_text(evidence_root / "native/dmesg-after-observe.txt")
    cleanup = read_text(evidence_root / "native/cleanup-node-holder.txt")
    combined_status = "\n".join([start_holder, status_start, status_observe])
    return {
        "decision": v847.get("decision"),
        "pass": bool_value(v847.get("pass")),
        "live": {
            "mknod_ok": nested(v847, "live", "mknod_ok"),
            "holder_pid_seen": nested(v847, "live", "holder_pid_seen"),
            "holder_opened": nested(v847, "live", "holder_opened"),
            "holder_open_rc_zero": nested(v847, "live", "holder_open_rc_zero"),
            "mdm3_online": nested(v847, "live", "mdm3_online"),
            "mdm3_offlining_seen": nested(v847, "live", "mdm3_offlining_seen"),
            "markers": nested(v847, "live", "markers"),
            "reboot_cleanup": nested(v847, "live", "reboot_cleanup"),
        },
        "guardrails": {
            "raw_esoc_open_executed": bool_value(v847.get("raw_esoc_open_executed")),
            "sysfs_write_executed": bool_value(v847.get("sysfs_write_executed")),
            "gpio_write_executed": bool_value(v847.get("gpio_write_executed")),
            "service_manager_start_executed": bool_value(v847.get("service_manager_start_executed")),
            "wifi_hal_start_executed": bool_value(v847.get("wifi_hal_start_executed")),
            "scan_connect_executed": bool_value(v847.get("scan_connect_executed")),
            "credential_use_executed": bool_value(v847.get("credential_use_executed")),
            "dhcp_route_executed": bool_value(v847.get("dhcp_route_executed")),
            "external_ping_executed": bool_value(v847.get("external_ping_executed")),
            "boot_image_write_executed": bool_value(v847.get("boot_image_write_executed")),
            "partition_write_executed": bool_value(v847.get("partition_write_executed")),
            "custom_kernel_flash_executed": bool_value(v847.get("custom_kernel_flash_executed")),
        },
        "evidence_files": {
            "start_holder": bool(start_holder),
            "status_after_start": bool(status_start),
            "status_after_observe": bool(status_observe),
            "state_after_observe": bool(state_observe),
            "dmesg_after_observe": bool(dmesg_observe),
            "cleanup_node_holder": bool(cleanup),
        },
        "holder_ids": extract_holder_ids(combined_status),
        "status_signals": {
            "status_file_missing": "can't open '/tmp/a90-v847-subsys-esoc0.status'" in combined_status,
            "holder_opened_status_seen": "holder.opened=1" in combined_status,
            "ps_holder_section_present": "== ps holder ==" in combined_status,
            "cleanup_text_present": bool(cleanup),
        },
        "state_after_observe": extract_state_file_values(state_observe),
        "dmesg": {
            "entered_subsystem_get": section_has(dmesg_observe, r"__subsystem_get: esoc0 count:0"),
            "changed_fw_name": section_has(dmesg_observe, r"Changing subsys fw_name to esoc0"),
            "powering_up_logged": section_has(dmesg_observe, r"Powering up esoc0"),
            "before_wait_for_err_ready_logged": section_has(dmesg_observe, r"before wait_for_err_ready"),
            "error_ready_timeout_logged": section_has(dmesg_observe, r"Error ready timed out"),
            "mhi_or_pcie_logged": section_has(dmesg_observe, r"\bmhi\b|\bpcie\b|mhi_"),
            "wlfw_bdf_wlan0_logged": section_has(dmesg_observe, r"wlfw|bdf|wlan0|FW_READY"),
            "warning_panic_fatal_logged": section_has(dmesg_observe, r"WARNING|panic|fatal"),
            "focused_lines": grep_lines(
                dmesg_observe,
                r"__subsystem_get|Changing subsys|Powering up esoc0|before wait_for_err_ready|Error ready|mhi|pcie|wlfw|bdf|wlan0|WARNING|panic|fatal",
            ),
        },
    }


def analyze_sources(source_root: Path) -> dict[str, Any]:
    subsystem = read_text(source_root / SUBSYSTEM_RESTART)
    esoc_client = read_text(source_root / ESOC_CLIENT)
    esoc_uapi = read_text(source_root / ESOC_UAPI)
    mhi_arch = read_text(source_root / MHI_ARCH)
    mhi_qcom = read_text(source_root / MHI_QCOM)
    icnss = read_text(source_root / ICNSS)
    defconfig = read_text(source_root / DEFCONFIG)
    sdx_ext_ipc = read_text(source_root / SDX_EXT_IPC)
    esoc_config_names = [
        "CONFIG_ESOC",
        "CONFIG_ESOC_DEV",
        "CONFIG_ESOC_CLIENT",
        "CONFIG_ESOC_DEBUG",
        "CONFIG_ESOC_MDM_4x",
        "CONFIG_ESOC_MDM_DRV",
        "CONFIG_ESOC_MDM_DBG_ENG",
    ]
    esoc_configs = parse_defconfig(defconfig, esoc_config_names)
    provider_candidates = {
        str(path): source_info(source_root, path)
        for path in ESOC_PROVIDER_CANDIDATES
    }
    provider_present = any(info["exists"] for info in provider_candidates.values())
    return {
        "sources": {
            str(SUBSYSTEM_RESTART): source_info(source_root, SUBSYSTEM_RESTART),
            str(ESOC_CLIENT): source_info(source_root, ESOC_CLIENT),
            str(ESOC_UAPI): source_info(source_root, ESOC_UAPI),
            str(MHI_ARCH): source_info(source_root, MHI_ARCH),
            str(MHI_QCOM): source_info(source_root, MHI_QCOM),
            str(ICNSS): source_info(source_root, ICNSS),
            str(DEFCONFIG): source_info(source_root, DEFCONFIG),
            str(SDX_EXT_IPC): source_info(source_root, SDX_EXT_IPC),
        },
        "subsystem_restart": {
            "subsys_device_open": line_of(subsystem, r"static int subsys_device_open"),
            "open_calls_get_with_fwname": line_of(subsystem, r"subsystem_get_with_fwname\(subsys_dev->desc->name"),
            "subsystem_get_with_fwname": line_of(subsystem, r"void \*subsystem_get_with_fwname"),
            "__subsystem_get": line_of(subsystem, r"void \*__subsystem_get"),
            "find_subsys_device": line_of(subsystem, r"subsys = retval = find_subsys_device\(name\)"),
            "pon_depends_on_get": line_of(subsystem, r"subsystem_get\(subsys->desc->pon_depends_on\)"),
            "count_log": line_of(subsystem, r"pr_err\(\"%s: %s count:%d"),
            "fw_name_log": line_of(subsystem, r"Changing subsys fw_name to %s"),
            "get_calls_subsys_start": line_of(subsystem, r"ret = subsys_start\(subsys\)"),
            "subsys_start": line_of(subsystem, r"static int subsys_start"),
            "subsys_start_before_powerup_notify": line_of(subsystem, r"SUBSYS_BEFORE_POWERUP"),
            "subsys_start_reinit_err_ready": line_of(subsystem, r"reinit_completion\(&subsys->err_ready\)"),
            "subsys_start_powerup_call": line_of(subsystem, r"ret = subsys->desc->powerup\(subsys->desc\)"),
            "subsys_start_enable_irqs": line_of(subsystem, r"enable_all_irqs\(subsys\)"),
            "subsys_start_wait_for_err_ready": line_of(subsystem, r"ret = wait_for_err_ready\(subsys\)"),
            "subsys_start_set_online": line_of(subsystem, r"subsys_set_state\(subsys, SUBSYS_ONLINE\)"),
            "wait_for_err_ready": line_of(subsystem, r"static int wait_for_err_ready"),
            "wait_for_err_ready_early_return": line_of(subsystem, r"generic_irq <= 0 && !subsys->desc->err_ready_irq"),
            "wait_for_err_ready_completion": line_of(subsystem, r"wait_for_completion_timeout\(&subsys->err_ready"),
            "wait_for_err_ready_timeout": line_of(subsystem, r"msecs_to_jiffies\(10000\)"),
            "wait_for_err_ready_timeout_log": line_of(subsystem, r"Error ready timed out"),
            "wait_for_err_ready_modem_panic_only": line_of(subsystem, r"Modem booting fail"),
            "subsys_device_close": line_of(subsystem, r"static int subsys_device_close"),
            "close_calls_subsystem_put": line_of(subsystem, r"subsystem_put\(subsys_dev\)"),
            "subsys_stop": line_of(subsystem, r"static void subsys_stop"),
        },
        "esoc_client": {
            "api_declaration": line_of(esoc_client, r"devm_register_esoc_client"),
            "hook_power_on": line_of(esoc_client, r"esoc_link_power_on"),
            "hook_power_off": line_of(esoc_client, r"esoc_link_power_off"),
            "hook_mdm_crash": line_of(esoc_client, r"esoc_link_mdm_crash"),
        },
        "esoc_uapi": {
            "cmd_exe": line_of(esoc_uapi, r"ESOC_CMD_EXE"),
            "wait_for_req": line_of(esoc_uapi, r"ESOC_WAIT_FOR_REQ"),
            "notify": line_of(esoc_uapi, r"ESOC_NOTIFY"),
            "get_status": line_of(esoc_uapi, r"ESOC_GET_STATUS"),
            "pwr_on": line_of(esoc_uapi, r"ESOC_PWR_ON"),
            "pwr_off": line_of(esoc_uapi, r"ESOC_PWR_OFF"),
            "reset": line_of(esoc_uapi, r"ESOC_RESET"),
        },
        "mhi_arch": {
            "esoc_power_on": line_of(mhi_arch, r"static int mhi_arch_esoc_ops_power_on"),
            "power_on_enter_log": line_of(mhi_arch, r"Enter: mdm_crashed"),
            "power_on_pcie_resume": line_of(mhi_arch, r"MSM_PCIE_RESUME"),
            "power_on_mhi_probe": line_of(mhi_arch, r"mhi_pci_probe"),
            "register_client_mdm": line_of(mhi_arch, r"devm_register_esoc_client"),
            "register_power_on_hook": line_of(mhi_arch, r"esoc_link_power_on"),
            "failed_register_esoc_client_log": line_of(mhi_arch, r"Failed to register esoc client"),
        },
        "mhi_qcom": {
            "power_up_store": line_of(mhi_qcom, r"static ssize_t power_up_store"),
            "power_up_attr_wo": line_of(mhi_qcom, r"DEVICE_ATTR_WO\(power_up\)"),
            "power_up_calls_mhi": line_of(mhi_qcom, r"mhi_qcom_power_up"),
        },
        "icnss": {
            "register_esoc_client": line_of(icnss, r"static int icnss_register_esoc_client"),
            "register_client_mdm": line_of(icnss, r"devm_register_esoc_client"),
            "cnss_power_off_hook": line_of(icnss, r"esoc_ops->esoc_link_power_off"),
        },
        "defconfig": {
            "source": source_info(source_root, DEFCONFIG),
            "esoc_configs": esoc_configs,
            "esoc_enabled": all(esoc_configs.get(name) == "y" for name in (
                "CONFIG_ESOC",
                "CONFIG_ESOC_DEV",
                "CONFIG_ESOC_CLIENT",
                "CONFIG_ESOC_MDM_4x",
                "CONFIG_ESOC_MDM_DRV",
            )),
        },
        "sdx_ext_ipc": {
            "source": source_info(source_root, SDX_EXT_IPC),
            "references_esoc": line_of(sdx_ext_ipc, r"esoc"),
            "references_mdm3": line_of(sdx_ext_ipc, r"mdm3"),
            "references_ap2mdm_gpio": line_of(sdx_ext_ipc, r"ap2mdm"),
        },
        "source_gaps": {
            "esoc_provider_definition_present": bool(
                re.search(r"struct esoc_desc \*devm_register_esoc_client\s*\(", "\n".join([subsystem, mhi_arch, mhi_qcom, icnss]))
            ),
            "esoc_provider_candidate_files": provider_candidates,
            "esoc_provider_candidate_present": provider_present,
            "ext_mdm_driver_source_present": provider_present,
            "esoc_mdm_config_enabled": all(esoc_configs.get(name) == "y" for name in (
                "CONFIG_ESOC_MDM_4x",
                "CONFIG_ESOC_MDM_DRV",
            )),
            "provider_absent_despite_enabled_config": all(esoc_configs.get(name) == "y" for name in (
                "CONFIG_ESOC_MDM_4x",
                "CONFIG_ESOC_MDM_DRV",
            )) and not provider_present,
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
    evidence_root = repo_path(args.v847_evidence)
    v846 = load_json(args.v846_manifest)
    v847 = load_json(args.v847_manifest)
    live = analyze_v847(v847, evidence_root)
    sources = analyze_sources(source_root)
    subsystem = sources["subsystem_restart"]
    dmesg = live["dmesg"]
    guardrails = live["guardrails"]
    forbidden_guardrail_hits = [name for name, value in guardrails.items() if value]
    checks = [
        check(
            "v846-input",
            v846.get("decision") == EXPECTED_V846 and bool_value(v846.get("pass")),
            {"decision": v846.get("decision"), "pass": v846.get("pass")},
            "refresh V846 state-control contract",
        ),
        check(
            "v847-input",
            v847.get("decision") == EXPECTED_V847 and bool_value(v847.get("pass")),
            {"decision": v847.get("decision"), "pass": v847.get("pass"), "reason": v847.get("reason")},
            "refresh V847 bounded char-open smoke",
        ),
        check(
            "v847-hit-subsystem-get",
            bool_value(nested(live, "live", "holder_pid_seen"))
            and dmesg["entered_subsystem_get"]
            and dmesg["changed_fw_name"],
            {
                "holder_ids": live["holder_ids"],
                "entered_subsystem_get": dmesg["entered_subsystem_get"],
                "changed_fw_name": dmesg["changed_fw_name"],
                "focused_lines": dmesg["focused_lines"],
            },
            "do not classify this as a node/materialization failure",
        ),
        check(
            "v847-blocked-before-open-success",
            not bool_value(nested(live, "live", "holder_opened"))
            and not bool_value(nested(live, "live", "holder_open_rc_zero")),
            {
                "holder_opened": nested(live, "live", "holder_opened"),
                "holder_open_rc_zero": nested(live, "live", "holder_open_rc_zero"),
                "status_signals": live["status_signals"],
            },
            "capture task wait state before retrying a longer hold",
        ),
        check(
            "source-open-path-anchors",
            all(
                subsystem.get(key) is not None
                for key in (
                    "subsys_device_open",
                    "open_calls_get_with_fwname",
                    "__subsystem_get",
                    "get_calls_subsys_start",
                    "subsys_start",
                    "subsys_start_powerup_call",
                    "subsys_start_wait_for_err_ready",
                    "wait_for_err_ready",
                    "subsys_device_close",
                    "close_calls_subsystem_put",
                )
            ),
            subsystem,
            "treat the remaining blocker as below char open and inside/under subsys_start",
        ),
        check(
            "wait-for-err-ready-logic-mapped",
            all(
                subsystem.get(key) is not None
                for key in (
                    "wait_for_err_ready",
                    "wait_for_err_ready_early_return",
                    "wait_for_err_ready_completion",
                    "wait_for_err_ready_timeout",
                    "wait_for_err_ready_timeout_log",
                )
            ),
            {
                "wait_for_err_ready": subsystem["wait_for_err_ready"],
                "early_return": subsystem["wait_for_err_ready_early_return"],
                "completion": subsystem["wait_for_err_ready_completion"],
                "timeout_10s": subsystem["wait_for_err_ready_timeout"],
                "timeout_log": subsystem["wait_for_err_ready_timeout_log"],
                "modem_panic_only": subsystem["wait_for_err_ready_modem_panic_only"],
                "v847_before_wait_log_seen": dmesg["before_wait_for_err_ready_logged"],
                "v847_timeout_log_seen": dmesg["error_ready_timeout_logged"],
            },
            "distinguish provider powerup block from wait_for_err_ready timeout with live wchan/stack sampling",
        ),
        check(
            "esoc-provider-source-gap-explicit",
            bool_value(nested(sources, "defconfig", "esoc_enabled"))
            and bool_value(nested(sources, "source_gaps", "provider_absent_despite_enabled_config")),
            {
                "defconfig": nested(sources, "defconfig", "esoc_configs"),
                "provider_candidates": nested(sources, "source_gaps", "esoc_provider_candidate_files"),
                "sdx_ext_ipc": nested(sources, "sdx_ext_ipc"),
            },
            "treat provider `powerup()` as proprietary/binary-backed in this OSRC tree; classify live behavior by observation, not source guessing",
        ),
        check(
            "v847-no-lower-wifi-progress",
            not dmesg["mhi_or_pcie_logged"] and not dmesg["wlfw_bdf_wlan0_logged"],
            {
                "mhi_or_pcie_logged": dmesg["mhi_or_pcie_logged"],
                "wlfw_bdf_wlan0_logged": dmesg["wlfw_bdf_wlan0_logged"],
                "markers": nested(live, "live", "markers"),
                "state_after_observe": live["state_after_observe"],
            },
            "do not move to HAL/connect until MHI/WLFW/BDF/wlan0 appears",
        ),
        check(
            "v847-cleanup-safe",
            bool_value(nested(live, "live", "reboot_cleanup", "bootstatus_healthy"))
            and bool_value(nested(live, "live", "reboot_cleanup", "selftest_healthy")),
            nested(live, "live", "reboot_cleanup"),
            "restore native health before any follow-up live sampler",
        ),
        check(
            "guardrails-preserved",
            not forbidden_guardrail_hits,
            {"hits": forbidden_guardrail_hits, "guardrails": guardrails},
            "do not widen scope while classifying the char-open boundary",
        ),
        finding(
            "source-gap-esoc-provider",
            sources["source_gaps"],
            "because the provider implementation is not staged in OSRC, the next live gate should observe wait state rather than guessing provider-side GPIO/IRQ behavior; include a read-only `/sys/module` eSoC/module surface capture in that live gate",
        ),
    ]
    blocked = [item.name for item in checks if item.status == "blocked" and item.severity == "blocker"]
    candidates = [
        candidate(
            "blind longer `subsys_esoc0` hold",
            "reject",
            "V847 already proved the open can block without MHI/WLFW progress; a longer hold without task wait-state evidence would only extend an opaque D-state risk window",
            "first capture `/proc/<pid>/wchan`, `/proc/<pid>/stack` if readable, task status, and syscall while the open is blocked",
        ),
        candidate(
            "repeat V847 unchanged",
            "reject",
            "The existing evidence has the same entry markers and cleanup success; repeating it will not locate the wait site",
            "add in-window process and kernel wait-state sampling",
        ),
        candidate(
            "raw `/dev/esoc*` ioctl or opaque eSoC sysfs writes",
            "reject",
            "The provider source is missing from staged OSRC and V847 already reached the source-backed subsystem entry path without raw esoc ioctls",
            "keep raw eSoC ioctls and GPIO/sysfs writes blocked",
        ),
        candidate(
            "MHI `power_up` sysfs write",
            "defer",
            "V847 did not show MHI/PCIe markers and the char open appears blocked before visible downstream MHI progression",
            "only revisit if V849 proves the block is not in subsystem powerup or if live MHI device state becomes source-backed",
        ),
        candidate(
            "Wi-Fi HAL, scan/connect, DHCP, external ping",
            "reject",
            "WLFW/BDF/FW-ready/wlan0 markers remain absent, so upper Wi-Fi layers still lack the required lower event source",
            "stay below HAL until service 69/WLFW/BDF/wlan0 exists",
        ),
        candidate(
            "bounded char-open wait-state sampler",
            "select-next",
            "V847 narrows the boundary below `__subsystem_get(esoc0)` and before visible MHI/WLFW; OSRC shows plausible waits at provider `powerup()` and `wait_for_err_ready()`",
            "V849 should rerun one bounded char-open attempt, sample holder PID tree, `/proc/<pid>/wchan`, `/proc/<pid>/stack` if readable, `/proc/<pid>/status`, `/proc/<pid>/syscall`, read-only `/sys/module` eSoC surface, mdm3 state, and dmesg, then cleanup reboot",
        ),
    ]
    result = {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v848",
        "host": collect_host_metadata(),
        "inputs": {
            "v846": {
                "path": str(repo_path(args.v846_manifest)),
                "decision": v846.get("decision"),
                "pass": bool_value(v846.get("pass")),
            },
            "v847": {
                "path": str(repo_path(args.v847_manifest)),
                "evidence": str(evidence_root),
                "decision": v847.get("decision"),
                "pass": bool_value(v847.get("pass")),
            },
            "source_root": str(source_root),
        },
        "v847_analysis": live,
        "sources": sources,
        "checks": [asdict(item) for item in checks],
        "candidate_matrix": candidates,
        "device_commands_executed": False,
        "device_mutations": False,
        "qmi_payload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "raw_esoc_open_executed": False,
        "subsys_char_open_executed": False,
        "gpio_write_executed": False,
        "sysfs_write_executed": False,
        "mknod_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
    }
    if args.command == "plan":
        result.update(
            {
                "decision": "v848-subsys-esoc0-open-block-classifier-plan-ready",
                "pass": True,
                "reason": "plan-only; no device command, mknod, open, sysfs/GPIO write, daemon start, Wi-Fi action, route, ping, or flash executed",
                "next_step": "run V848 host-only source/evidence classifier",
            }
        )
    elif blocked:
        result.update(
            {
                "decision": "v848-subsys-esoc0-open-block-classifier-blocked",
                "pass": False,
                "reason": "blocked by " + ", ".join(blocked),
                "next_step": "refresh blocked input or source evidence before any live retry",
            }
        )
    else:
        result.update(
            {
                "decision": "v848-subsys-esoc0-open-block-boundary-classified",
                "pass": True,
                "reason": "V847 reached __subsystem_get(esoc0) and changed fw_name but did not complete open or produce MHI/WLFW progress; source narrows the branch to provider powerup() versus wait_for_err_ready(), and the missing OSRC eSoC provider source requires live wait-state sampling rather than a blind retry",
                "next_step": "V849 should run one bounded subsys_esoc0 char-open wait-state sampler that distinguishes provider `powerup()` blocking from `wait_for_err_ready()` blocking with holder PID tree, wchan/stack/status/syscall, read-only `/sys/module` eSoC surface, mdm3 state, focused dmesg, node cleanup, cleanup reboot, and postflight health checks; still no raw esoc ioctl, sysfs/GPIO writes, HAL, scan/connect, DHCP/routes, external ping, or boot-image work",
            }
        )
    return result


def render_summary(result: dict[str, Any]) -> str:
    subsystem = result["sources"]["subsystem_restart"]
    source_rows = [
        ["subsys_device_open", subsystem["subsys_device_open"]],
        ["open_calls_get_with_fwname", subsystem["open_calls_get_with_fwname"]],
        ["__subsystem_get", subsystem["__subsystem_get"]],
        ["pon_depends_on_get", subsystem["pon_depends_on_get"]],
        ["get_calls_subsys_start", subsystem["get_calls_subsys_start"]],
        ["subsys_start", subsystem["subsys_start"]],
        ["subsys_start_powerup_call", subsystem["subsys_start_powerup_call"]],
        ["subsys_start_wait_for_err_ready", subsystem["subsys_start_wait_for_err_ready"]],
        ["wait_for_err_ready", subsystem["wait_for_err_ready"]],
        ["wait_for_err_ready_early_return", subsystem["wait_for_err_ready_early_return"]],
        ["wait_for_err_ready_completion", subsystem["wait_for_err_ready_completion"]],
        ["wait_for_err_ready_timeout", subsystem["wait_for_err_ready_timeout"]],
        ["wait_for_err_ready_timeout_log", subsystem["wait_for_err_ready_timeout_log"]],
        ["wait_for_err_ready_modem_panic_only", subsystem["wait_for_err_ready_modem_panic_only"]],
        ["subsys_device_close", subsystem["subsys_device_close"]],
        ["close_calls_subsystem_put", subsystem["close_calls_subsystem_put"]],
    ]
    defconfig_rows = [
        [name, value]
        for name, value in result["sources"]["defconfig"]["esoc_configs"].items()
    ]
    v847 = result["v847_analysis"]
    live_rows = [
        ["mknod_ok", nested(v847, "live", "mknod_ok")],
        ["holder_pid_seen", nested(v847, "live", "holder_pid_seen")],
        ["holder_opened", nested(v847, "live", "holder_opened")],
        ["holder_open_rc_zero", nested(v847, "live", "holder_open_rc_zero")],
        ["holder_ids", json.dumps(v847["holder_ids"], sort_keys=True)],
        ["entered_subsystem_get", nested(v847, "dmesg", "entered_subsystem_get")],
        ["changed_fw_name", nested(v847, "dmesg", "changed_fw_name")],
        ["mhi_or_pcie_logged", nested(v847, "dmesg", "mhi_or_pcie_logged")],
        ["wlfw_bdf_wlan0_logged", nested(v847, "dmesg", "wlfw_bdf_wlan0_logged")],
        ["state_after_observe", json.dumps(v847["state_after_observe"], sort_keys=True)],
        ["cleanup_healthy", bool_value(nested(v847, "live", "reboot_cleanup", "bootstatus_healthy")) and bool_value(nested(v847, "live", "reboot_cleanup", "selftest_healthy"))],
    ]
    check_rows = [
        [item["name"], item["status"], item["severity"], json.dumps(item["detail"], ensure_ascii=False, sort_keys=True), item["next_step"]]
        for item in result["checks"]
    ]
    candidate_rows = [
        [item["candidate"], item["classification"], item["reason"], item["next_step"]]
        for item in result["candidate_matrix"]
    ]
    focused_lines = "\n".join(f"- `{line}`" for line in nested(v847, "dmesg", "focused_lines") or [])
    return "\n".join(
        [
            "# V848 subsys_esoc0 Open-Block Classifier",
            "",
            f"- generated: `{result['generated_at']}`",
            f"- command: `{result['command']}`",
            f"- decision: `{result['decision']}`",
            f"- pass: `{result['pass']}`",
            f"- reason: {result['reason']}",
            f"- next_step: {result['next_step']}",
            f"- device_commands_executed: `{result['device_commands_executed']}`",
            f"- mknod_executed: `{result['mknod_executed']}`",
            f"- subsys_char_open_executed: `{result['subsys_char_open_executed']}`",
            f"- raw_esoc_open_executed: `{result['raw_esoc_open_executed']}`",
            f"- sysfs_write_executed: `{result['sysfs_write_executed']}`",
            f"- gpio_write_executed: `{result['gpio_write_executed']}`",
            f"- wifi_hal_start_executed: `{result['wifi_hal_start_executed']}`",
            f"- scan_connect_executed: `{result['scan_connect_executed']}`",
            f"- external_ping_executed: `{result['external_ping_executed']}`",
            "",
            "## Checks",
            "",
            markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
            "",
            "## V847 Signals",
            "",
            markdown_table(["signal", "value"], live_rows),
            "",
            "## Focused Dmesg Lines",
            "",
            focused_lines or "- none",
            "",
            "## Source Anchors",
            "",
            markdown_table(["anchor", "line"], source_rows),
            "",
            "## eSoC Provider Source Gap",
            "",
            markdown_table(["config", "value"], defconfig_rows),
            "",
            f"- provider_absent_despite_enabled_config: `{result['sources']['source_gaps']['provider_absent_despite_enabled_config']}`",
            f"- sdx_ext_ipc_references_esoc: `{result['sources']['sdx_ext_ipc']['references_esoc']}`",
            "",
            "## Candidate Matrix",
            "",
            markdown_table(["candidate", "classification", "reason", "next"], candidate_rows),
            "",
        ]
    )


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
    print(f"evidence: {repo_path(args.out_dir)}")
    return 0 if bool_value(result["pass"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
