#!/usr/bin/env python3
"""V846 host-only mdm3/eSoC state-control contract classifier.

V845 proved the mdm3/ext-sdx50m surface exists but remains OFFLINING. This
classifier maps the live V845 candidates back to Samsung OSRC source so the next
live gate targets the actual exported userspace control path, not a misleading
root-writable test result.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v846-mdm3-esoc-state-control-contract")
LATEST_POINTER = Path("tmp/wifi/latest-v846-mdm3-esoc-state-control-contract.txt")
DEFAULT_V844_MANIFEST = Path("tmp/wifi/v844-mdm3-ext-sdx50m-boot-interface-classifier/manifest.json")
DEFAULT_V845_MANIFEST = Path("tmp/wifi/v845-mdm3-ext-sdx50m-surface-snapshot/manifest.json")
DEFAULT_SOURCE_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel')

SUBSYSTEM_RESTART = Path("drivers/soc/qcom/subsystem_restart.c")
ESOC_HEADER = Path("include/linux/esoc_client.h")
ESOC_UAPI = Path("include/uapi/linux/esoc_ctrl.h")
MHI_ARCH = Path("drivers/bus/mhi/controllers/mhi_arch_qcom.c")
MHI_QCOM = Path("drivers/bus/mhi/controllers/mhi_qcom.c")
ICNSS = Path("drivers/soc/qcom/icnss.c")

EXPECTED_V844 = "v844-mdm3-ext-sdx50m-boot-interface-selected"
EXPECTED_V845 = "v845-mdm3-ext-sdx50m-surface-captured"


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
    parser.add_argument("--v844-manifest", type=Path, default=DEFAULT_V844_MANIFEST)
    parser.add_argument("--v845-manifest", type=Path, default=DEFAULT_V845_MANIFEST)
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


def lines_of(text: str, pattern: str, flags: int = 0) -> list[int]:
    regex = re.compile(pattern, flags)
    return [index for index, line in enumerate(text.splitlines(), start=1) if regex.search(line)]


def source_info(root: Path, relative: Path) -> dict[str, Any]:
    resolved = repo_path(root / relative)
    return {
        "path": str(resolved),
        "exists": resolved.exists(),
        "size": resolved.stat().st_size if resolved.exists() else None,
    }


def extract_device_node_numbers(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    current = ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("== PATH ") and "subsys_esoc0" in line:
            current = "subsys_esoc0"
        elif line.startswith("== PATH "):
            current = ""
        elif current and line.startswith("MAJOR="):
            result["major"] = line.split("=", 1)[1]
        elif current and line.startswith("MINOR="):
            result["minor"] = line.split("=", 1)[1]
        elif current and line.startswith("DEVNAME="):
            result["devname"] = line.split("=", 1)[1]
    return result


def access_rows(v845: dict[str, Any]) -> list[dict[str, Any]]:
    rows = nested(v845, "analysis", "access_rows")
    return rows if isinstance(rows, list) else []


def mode_lines(text: str, paths: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in text.splitlines():
        for path in paths:
            if path in line and re.match(r"^[bcdlps-][rwx-]{9}\s", line):
                found[path] = line.strip()
    return found


def analyze_v845(v845: dict[str, Any]) -> dict[str, Any]:
    evidence_dir = repo_path("tmp/wifi/v845-mdm3-ext-sdx50m-surface-snapshot")
    mdm3_sysfs = read_text(evidence_dir / "native/mdm3-sysfs.txt")
    device_nodes = read_text(evidence_dir / "native/device-nodes.txt")
    paths = [
        "/sys/bus/esoc/devices/esoc0/esoc_link",
        "/sys/bus/esoc/devices/esoc0/esoc_link_info",
        "/sys/bus/esoc/devices/esoc0/esoc_name",
        "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state",
        "/sys/bus/msm_subsys/devices/subsys9/state",
        "/sys/bus/msm_subsys/devices/subsys0/state",
    ]
    return {
        "decision": v845.get("decision"),
        "pass": bool_value(v845.get("pass")),
        "analysis": {
            "mdm3_state": nested(v845, "analysis", "mdm3_state"),
            "mss_state": nested(v845, "analysis", "mss_state"),
            "mdm3_sysfs_present": nested(v845, "analysis", "mdm3_sysfs_present"),
            "esoc0_sysfs_present": nested(v845, "analysis", "esoc0_sysfs_present"),
            "subsys_esoc0_present": nested(v845, "analysis", "subsys_esoc0_present"),
            "dev_esoc_node_present": nested(v845, "analysis", "dev_esoc_node_present"),
            "dev_subsys_node_present": nested(v845, "analysis", "dev_subsys_node_present"),
            "writable_existing_control_candidates": nested(v845, "analysis", "writable_existing_control_candidates"),
            "runtime_counts": nested(v845, "analysis", "runtime_counts"),
        },
        "access_rows": access_rows(v845),
        "mode_lines": mode_lines(mdm3_sysfs, paths),
        "subsys_esoc0_uevent": extract_device_node_numbers(mdm3_sysfs),
        "proc_devices_has_subsys": "236 subsys" in device_nodes,
        "proc_devices_has_esoc": "484 esoc" in device_nodes,
    }


def analyze_sources(source_root: Path) -> dict[str, Any]:
    subsystem = read_text(source_root / SUBSYSTEM_RESTART)
    esoc_header = read_text(source_root / ESOC_HEADER)
    esoc_uapi = read_text(source_root / ESOC_UAPI)
    mhi_arch = read_text(source_root / MHI_ARCH)
    mhi_qcom = read_text(source_root / MHI_QCOM)
    icnss = read_text(source_root / ICNSS)
    provider_impl_present = any(
        line.strip().startswith("struct esoc_desc *devm_register_esoc_client")
        for line in "\n".join([subsystem, mhi_arch, mhi_qcom, icnss]).splitlines()
    )
    return {
        "sources": {
            str(SUBSYSTEM_RESTART): source_info(source_root, SUBSYSTEM_RESTART),
            str(ESOC_HEADER): source_info(source_root, ESOC_HEADER),
            str(ESOC_UAPI): source_info(source_root, ESOC_UAPI),
            str(MHI_ARCH): source_info(source_root, MHI_ARCH),
            str(MHI_QCOM): source_info(source_root, MHI_QCOM),
            str(ICNSS): source_info(source_root, ICNSS),
        },
        "subsystem_restart": {
            "state_show": line_of(subsystem, r"static ssize_t state_show"),
            "state_attr_ro": line_of(subsystem, r"DEVICE_ATTR_RO\(state\)"),
            "subsys_device_open": line_of(subsystem, r"static int subsys_device_open"),
            "open_calls_get_with_fwname": line_of(subsystem, r"subsystem_get_with_fwname\("),
            "subsys_device_close": line_of(subsystem, r"static int subsys_device_close"),
            "close_calls_subsystem_put": line_of(subsystem, r"subsystem_put\(subsys_dev\)"),
            "char_device_add": line_of(subsystem, r"static int subsys_char_device_add"),
            "device_create_subsys_name": line_of(subsystem, r"subsys_%s"),
            "class_create_subsys": line_of(subsystem, r"class_create\(THIS_MODULE,\s*\"subsys\"\)"),
            "get_calls_subsys_start": line_of(subsystem, r"ret = subsys_start\(subsys\)"),
            "put_calls_subsys_stop": line_of(subsystem, r"subsys_stop\(subsys\)"),
            "pm_proxy_esoc_comment": line_of(subsystem, r"pm_proxy_helper put modem, it also shuts down esoc0"),
            "ssctl_instance_parse": line_of(subsystem, r"qcom,ssctl-instance-id"),
            "sysmon_id_parse": line_of(subsystem, r"qcom,sysmon-id"),
        },
        "esoc_header": {
            "hook_power_on": line_of(esoc_header, r"esoc_link_power_on"),
            "hook_power_off": line_of(esoc_header, r"esoc_link_power_off"),
            "hook_mdm_crash": line_of(esoc_header, r"esoc_link_mdm_crash"),
            "desc_name": line_of(esoc_header, r"struct esoc_desc"),
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
            "power_on_pcie_resume": line_of(mhi_arch, r"MSM_PCIE_RESUME"),
            "power_on_mhi_probe": line_of(mhi_arch, r"mhi_pci_probe"),
            "esoc_power_off": line_of(mhi_arch, r"static void mhi_arch_esoc_ops_power_off"),
            "power_off_mhi_down": line_of(mhi_arch, r"mhi_power_down"),
            "register_client_mdm": line_of(mhi_arch, r"devm_register_esoc_client"),
            "register_power_on_hook": line_of(mhi_arch, r"esoc_link_power_on"),
        },
        "mhi_qcom": {
            "power_up_store": line_of(mhi_qcom, r"static ssize_t power_up_store"),
            "power_up_calls_mhi": line_of(mhi_qcom, r"mhi_qcom_power_up"),
            "power_up_attr_wo": line_of(mhi_qcom, r"DEVICE_ATTR_WO\(power_up\)"),
        },
        "icnss": {
            "register_esoc_client": line_of(icnss, r"static int icnss_register_esoc_client"),
            "register_client_mdm": line_of(icnss, r"devm_register_esoc_client"),
            "cnss_power_off_hook": line_of(icnss, r"esoc_ops->esoc_link_power_off"),
            "esoc_off_state": line_of(icnss, r"ICNSS_ESOC_OFF"),
            "wlfw_new_server_dependency": line_of(read_text(source_root / Path("drivers/soc/qcom/icnss_qmi.c")), r"static int wlfw_new_server"),
        },
        "source_gaps": {
            "esoc_client_api_declaration": line_of(esoc_header, r"devm_register_esoc_client"),
            "esoc_provider_definition_present": provider_impl_present,
            "ext_mdm_driver_source_present": False,
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
    v844 = load_json(args.v844_manifest)
    v845 = load_json(args.v845_manifest)
    live = analyze_v845(v845)
    sources = analyze_sources(source_root)
    subsystem = sources["subsystem_restart"]
    mhi = sources["mhi_arch"]
    checks = [
        check(
            "v844-input",
            v844.get("decision") == EXPECTED_V844 and bool_value(v844.get("pass")),
            {"decision": v844.get("decision"), "pass": v844.get("pass")},
            "refresh V844 architecture classifier",
        ),
        check(
            "v845-input",
            v845.get("decision") == EXPECTED_V845 and bool_value(v845.get("pass")),
            live["analysis"],
            "refresh V845 live read-only surface snapshot",
        ),
        check(
            "subsys-state-is-read-only",
            subsystem["state_show"] is not None and subsystem["state_attr_ro"] is not None,
            {
                "state_show": subsystem["state_show"],
                "state_attr_ro": subsystem["state_attr_ro"],
                "live_modes": {
                    path: mode for path, mode in live["mode_lines"].items()
                    if path.endswith("/state")
                },
            },
            "do not write subsystem state; source has no state_store",
        ),
        check(
            "subsys-char-open-is-boot-contract",
            all(subsystem.get(key) is not None for key in (
                "subsys_device_open",
                "open_calls_get_with_fwname",
                "get_calls_subsys_start",
                "subsys_device_close",
                "close_calls_subsystem_put",
                "put_calls_subsys_stop",
                "device_create_subsys_name",
            )),
            {
                "subsys_device_open": subsystem["subsys_device_open"],
                "open_calls_get_with_fwname": subsystem["open_calls_get_with_fwname"],
                "get_calls_subsys_start": subsystem["get_calls_subsys_start"],
                "subsys_device_close": subsystem["subsys_device_close"],
                "close_calls_subsystem_put": subsystem["close_calls_subsystem_put"],
                "put_calls_subsys_stop": subsystem["put_calls_subsys_stop"],
                "device_create_subsys_name": subsystem["device_create_subsys_name"],
                "subsys_esoc0_uevent": live["subsys_esoc0_uevent"],
            },
            "V847 can target a bounded subsys_esoc0 char-device open/hold with watchdog and cleanup reboot",
        ),
        check(
            "mhi-esoc-hooks-present",
            all(mhi.get(key) is not None for key in (
                "esoc_power_on",
                "power_on_pcie_resume",
                "power_on_mhi_probe",
                "esoc_power_off",
                "power_off_mhi_down",
                "register_power_on_hook",
            )),
            mhi,
            "if char-device open advances MHI, observe PCIe/MHI/WLFW markers before HAL/connect",
        ),
        finding(
            "esoc-provider-source-gap",
            sources["source_gaps"],
            "treat esoc_link/esoc_name sysfs writes and raw esoc ioctl paths as opaque until provider source or live behavior is proven",
        ),
        check(
            "host-only-boundary",
            True,
            "V846 reads existing evidence and local OSRC source only",
            "keep V846 non-mutating",
        ),
    ]
    blocked = [item.name for item in checks if item.status == "blocked" and item.severity == "blocker"]
    candidates = [
        candidate(
            "write `/sys/.../subsys9/state`",
            "reject",
            "OSRC exposes subsystem `state` with `DEVICE_ATTR_RO(state)` and no store function; root `test -w` from V845 is not authoritative for sysfs store availability",
            "do not write subsystem state",
        ),
        candidate(
            "write `esoc_link`, `esoc_link_info`, or `esoc_name`",
            "reject",
            "V845 live modes are read-only and the ext-mdm/eSoC provider implementation is absent from the staged OSRC source, so write semantics are opaque",
            "keep these files read-only until provider behavior is proven",
        ),
        candidate(
            "raw `/dev/esoc*` ioctl path",
            "reject",
            "V845 shows no raw `/dev/esoc*` node; UAPI exposes power/reset ioctls that are broad state-changing operations",
            "do not create or open raw esoc nodes as the next gate",
        ),
        candidate(
            "MHI `power_up` sysfs",
            "defer",
            "MHI has a source-backed `power_up` write path, but V845 did not yet prove the live MHI device path or its relation to current mdm3 OFFLINING state",
            "only revisit after char-device path and MHI read-only surface evidence",
        ),
        candidate(
            "`subsys_esoc0` char-device open",
            "select-next",
            "subsystem_restart.c shows open calls `subsystem_get_with_fwname()`, which calls `subsys_start()`, and release calls `subsystem_put()`/`subsys_stop()`; V845 provides major/minor/devname but no `/dev` node",
            "V847 should materialize only `/dev/subsys_esoc0` from V845 uevent and run one bounded open/hold smoke with watchdog, dmesg capture, and cleanup reboot; still no HAL/connect",
        ),
    ]
    result = {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v846",
        "host": collect_host_metadata(),
        "inputs": {
            "v844": {"path": str(repo_path(args.v844_manifest)), "decision": v844.get("decision"), "pass": bool_value(v844.get("pass"))},
            "v845": {"path": str(repo_path(args.v845_manifest)), "decision": v845.get("decision"), "pass": bool_value(v845.get("pass"))},
            "source_root": str(source_root),
        },
        "live_v845": live,
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
        "esoc0_open_executed": False,
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
        result.update({
            "decision": "v846-mdm3-esoc-state-control-contract-plan-ready",
            "pass": True,
            "reason": "plan-only; no device command, mknod, open, sysfs/GPIO write, daemon start, Wi-Fi action, route, ping, or flash executed",
            "next_step": "run V846 host-only source/evidence classifier",
        })
    elif blocked:
        result.update({
            "decision": "v846-mdm3-esoc-state-control-contract-blocked",
            "pass": False,
            "reason": "blocked by " + ", ".join(blocked),
            "next_step": "refresh blocked input or source evidence before any mdm3/eSoC live action",
        })
    else:
        result.update({
            "decision": "v846-mdm3-esoc-char-open-contract-selected",
            "pass": True,
            "reason": "OSRC rejects direct state/sysfs writes as the next gate and maps the exported userspace boot contract to the subsys_esoc0 char-device open path; MHI hooks are source-backed downstream effects",
            "next_step": "V847 should perform a bounded live subsys_esoc0 char-device materialize/open/hold smoke with watchdog, dmesg evidence, and cleanup reboot; no service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or boot-image work",
        })
    return result


def render_summary(result: dict[str, Any]) -> str:
    checks = result["checks"]
    candidates = result["candidate_matrix"]
    subsystem = result["sources"]["subsystem_restart"]
    live = result["live_v845"]
    source_rows = [
        ["state_show", subsystem["state_show"]],
        ["state_attr_ro", subsystem["state_attr_ro"]],
        ["subsys_device_open", subsystem["subsys_device_open"]],
        ["open_calls_get_with_fwname", subsystem["open_calls_get_with_fwname"]],
        ["get_calls_subsys_start", subsystem["get_calls_subsys_start"]],
        ["subsys_device_close", subsystem["subsys_device_close"]],
        ["close_calls_subsystem_put", subsystem["close_calls_subsystem_put"]],
        ["put_calls_subsys_stop", subsystem["put_calls_subsys_stop"]],
        ["device_create_subsys_name", subsystem["device_create_subsys_name"]],
        ["pm_proxy_esoc_comment", subsystem["pm_proxy_esoc_comment"]],
    ]
    live_rows = [
        ["mdm3_state", live["analysis"].get("mdm3_state")],
        ["mss_state", live["analysis"].get("mss_state")],
        ["dev_esoc_node_present", live["analysis"].get("dev_esoc_node_present")],
        ["dev_subsys_node_present", live["analysis"].get("dev_subsys_node_present")],
        ["subsys_esoc0_uevent", json.dumps(live["subsys_esoc0_uevent"], sort_keys=True)],
        ["proc_devices_has_subsys", live["proc_devices_has_subsys"]],
        ["proc_devices_has_esoc", live["proc_devices_has_esoc"]],
    ]
    return "\n".join([
        "# V846 mdm3/eSoC State-Control Contract",
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
        f"- sysfs_write_executed: `{result['sysfs_write_executed']}`",
        f"- gpio_write_executed: `{result['gpio_write_executed']}`",
        f"- wifi_hal_start_executed: `{result['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{result['scan_connect_executed']}`",
        f"- external_ping_executed: `{result['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(
            ["name", "status", "severity", "detail", "next"],
            [[item["name"], item["status"], item["severity"], json.dumps(item["detail"], ensure_ascii=False, sort_keys=True), item["next_step"]] for item in checks],
        ),
        "",
        "## Live V845 Inputs",
        "",
        markdown_table(["signal", "value"], live_rows),
        "",
        "## Source Anchors",
        "",
        markdown_table(["anchor", "line"], source_rows),
        "",
        "## Candidate Matrix",
        "",
        markdown_table(
            ["candidate", "classification", "reason", "next"],
            [[item["candidate"], item["classification"], item["reason"], item["next_step"]] for item in candidates],
        ),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    result = classify(args)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_summary(result))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {result['decision']}")
    print(f"pass: {result['pass']}")
    print(f"reason: {result['reason']}")
    print(f"next: {result['next_step']}")
    print(f"device_commands_executed: {result['device_commands_executed']}")
    print(f"mknod_executed: {result['mknod_executed']}")
    print(f"subsys_char_open_executed: {result['subsys_char_open_executed']}")
    print(f"sysfs_write_executed: {result['sysfs_write_executed']}")
    print(f"wifi_hal_start_executed: {result['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {result['scan_connect_executed']}")
    print(f"external_ping_executed: {result['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
