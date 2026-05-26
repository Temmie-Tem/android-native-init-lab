#!/usr/bin/env python3
"""V1073 host-only classifier for pm-service/per_mgr early exit evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1073-pm-actor-exit-host-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1073-pm-actor-exit-host-classifier.txt")
DEFAULT_V1072_MANIFEST = Path("tmp/wifi/v1072-pm-observer-pm-actor-exit-fd-trace-v192-live/manifest.json")
DEFAULT_V1072_TRANSCRIPT = Path(
    "tmp/wifi/v1072-pm-observer-pm-actor-exit-fd-trace-v192-live/host/pm-service-trigger-observer.txt"
)
DEFAULT_VENDOR_FILES = Path("tmp/wifi/v1073-host-only/vendor-extract/files")
DEFAULT_ANALYSIS_DIR = Path("tmp/wifi/v1073-host-only/analysis")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1072-manifest", type=Path, default=DEFAULT_V1072_MANIFEST)
    parser.add_argument("--v1072-transcript", type=Path, default=DEFAULT_V1072_TRANSCRIPT)
    parser.add_argument("--vendor-files", type=Path, default=DEFAULT_VENDOR_FILES)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    return parser.parse_args()


def read_text(path: Path, limit: int = 8_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def contract(manifest: dict[str, Any]) -> dict[str, str]:
    values = ((manifest.get("analysis") or {}).get("helper") or {}).get("contract") or {}
    return {str(key): str(value) for key, value in values.items()}


def service_block(rc_text: str, service_name: str) -> str:
    pattern = re.compile(
        rf"^service\s+{re.escape(service_name)}\s+.*?(?=^service\s+|^on\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(rc_text)
    return match.group(0).strip() if match else ""


def has_directive(block: str, directive: str) -> bool:
    return any(line.strip().startswith(directive + " ") for line in block.splitlines())


def extract_stderr(text: str) -> str:
    match = re.search(r"A90_EXECNS_STDERR_BEGIN\n(.*?)\nA90_EXECNS_STDERR_END", text, re.DOTALL)
    return match.group(1) if match else ""


def fd_targets(text: str, prefix: str) -> list[str]:
    pattern = re.compile(rf"^capture\.{re.escape(prefix)}\.fd_links\.entry_\d+\.target=(.*)$", re.MULTILINE)
    return [match.group(1).strip() for match in pattern.finditer(text)]


def contains_all(text: str, tokens: tuple[str, ...]) -> bool:
    return all(token in text for token in tokens)


def dependency_summary(dynamic_text: str) -> list[str]:
    values: list[str] = []
    for line in dynamic_text.splitlines():
        match = re.search(r"\(NEEDED\)\s+Shared library: \[(.*?)\]", line)
        if match:
            values.append(match.group(1))
    return values


def build_classification(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v1072_manifest)
    helper_contract = contract(manifest)
    transcript = read_text(args.v1072_transcript)
    vendor_files = args.vendor_files
    analysis_dir = args.analysis_dir

    init_target_rc = read_text(vendor_files / "init.target.rc")
    pm_proxy_helper_rc = read_text(vendor_files / "pm_proxy_helper.rc")
    pm_service_strings = read_text(analysis_dir / "pm-service.strings.txt")
    pm_proxy_strings = read_text(analysis_dir / "pm-proxy.strings.txt")
    pm_proxy_helper_strings = read_text(analysis_dir / "pm_proxy_helper.strings.txt")
    libmdmdetect_strings = read_text(analysis_dir / "libmdmdetect.so.strings.txt")
    libperipheral_client_strings = read_text(analysis_dir / "libperipheral_client.so.strings.txt")
    libqmi_csi_strings = read_text(analysis_dir / "libqmi_csi.so.strings.txt")
    libqmi_cci_strings = read_text(analysis_dir / "libqmi_cci.so.strings.txt")
    pm_service_dynamic = read_text(analysis_dir / "pm-service.dynamic.txt")
    pm_proxy_dynamic = read_text(analysis_dir / "pm-proxy.dynamic.txt")

    per_mgr_block = service_block(init_target_rc, "vendor.per_mgr")
    per_proxy_block = service_block(init_target_rc, "vendor.per_proxy")
    pm_proxy_helper_block = service_block(pm_proxy_helper_rc, "vendor.per_proxy_helper")
    stderr = extract_stderr(transcript)
    per_mgr_fd_targets = fd_targets(transcript, "per_mgr_exit")
    per_proxy_fd_targets = fd_targets(transcript, "per_proxy_exit")

    rc = {
        "init_target_present": bool(init_target_rc),
        "pm_proxy_helper_rc_present": bool(pm_proxy_helper_rc),
        "per_mgr_block_present": bool(per_mgr_block),
        "per_mgr_socket_directive": has_directive(per_mgr_block, "socket"),
        "per_mgr_user_system": "user system" in per_mgr_block,
        "per_mgr_group_system": "group system" in per_mgr_block,
        "per_mgr_ioprio_rt4": "ioprio rt 4" in per_mgr_block,
        "per_proxy_block_present": bool(per_proxy_block),
        "per_proxy_disabled": "disabled" in per_proxy_block,
        "per_proxy_started_by_per_mgr_running": "on property:init.svc.vendor.per_mgr=running" in init_target_rc
        and "start vendor.per_proxy" in init_target_rc,
        "pm_proxy_helper_block_present": bool(pm_proxy_helper_block),
        "pm_proxy_helper_oneshot": "oneshot" in pm_proxy_helper_block,
        "pm_proxy_helper_started_post_fs_data": "on post-fs-data" in pm_proxy_helper_rc
        and "start vendor.per_proxy_helper" in pm_proxy_helper_rc,
    }

    binaries = {
        "pm_service_needed": dependency_summary(pm_service_dynamic),
        "pm_proxy_needed": dependency_summary(pm_proxy_dynamic),
        "pm_service_has_vndbinder": "/dev/vndbinder" in pm_service_strings,
        "pm_service_has_subsys_modem_literal": "/dev/subsys_modem" in pm_service_strings,
        "pm_service_has_peripheral_manager_service": "vendor.qcom.PeripheralManager" in pm_service_strings,
        "pm_service_has_add_service_fail": "Adding Peripheral Manager service fail" in pm_service_strings,
        "pm_service_has_system_info_fail": "Failed to get system information" in pm_service_strings,
        "pm_service_has_init_peripheral_fail": "Failed to init peripheral" in pm_service_strings,
        "pm_service_has_qmi_csi_failure_strings": contains_all(
            pm_service_strings,
            ("QMI service exited", "QMI service select error", "QMI service process event error"),
        ),
        "pm_service_has_property_prefix": "vendor.peripheral." in pm_service_strings,
        "pm_proxy_has_client_connect": "pm_client_connect" in pm_proxy_strings,
        "pm_proxy_has_register_failed": "pm_client_register_failed" in pm_proxy_strings,
        "pm_proxy_helper_has_subsys_modem": "/dev/subsys_modem" in pm_proxy_helper_strings,
        "libmdmdetect_has_esoc_and_msm_subsys_paths": contains_all(
            libmdmdetect_strings,
            ("/sys/bus/esoc/devices", "/sys/bus/msm_subsys/devices"),
        ),
        "libmdmdetect_has_dev_subsys_format": "/dev/subsys_%s" in libmdmdetect_strings,
        "libmdmdetect_has_failed_to_open": "Failed to open %s: %s" in libmdmdetect_strings,
        "libperipheral_client_has_vndbinder_lookup": contains_all(
            libperipheral_client_strings,
            ("/dev/vndbinder", "vendor.qcom.PeripheralManager", "Get service fail"),
        ),
        "libqmi_csi_has_qrtr_register_surface": contains_all(
            libqmi_csi_strings,
            ("qmi_csi_register", "qmi_csi_xport_start", "QRTR"),
        ),
        "libqmi_cci_has_qrtr_lookup_surface": contains_all(
            libqmi_cci_strings,
            ("qmi_client", "open_lookup_sock_fd", "QRTR"),
        ),
    }

    runtime = {
        "v1072_decision": manifest.get("decision", ""),
        "v1072_pass": bool(manifest.get("pass")),
        "all_postflight_safe": helper_contract.get("all_postflight_safe") == "1",
        "per_mgr_exit_code": helper_contract.get("child.per_mgr.exit_code", ""),
        "per_mgr_capture_exit": helper_contract.get("child.per_mgr.capture_exit") == "1",
        "per_mgr_trace_exit_event": helper_contract.get("child.per_mgr.trace_exit_event", ""),
        "per_proxy_exit_code": helper_contract.get("child.per_proxy.exit_code", ""),
        "per_proxy_capture_exit": helper_contract.get("child.per_proxy.capture_exit") == "1",
        "per_proxy_trace_exit_event": helper_contract.get("child.per_proxy.trace_exit_event", ""),
        "per_mgr_fd_targets": per_mgr_fd_targets,
        "per_proxy_fd_targets": per_proxy_fd_targets,
        "per_mgr_fd_has_subsys_modem": any("/dev/subsys_modem" in target for target in per_mgr_fd_targets),
        "per_mgr_fd_has_vndbinder": any("/dev/vndbinder" in target for target in per_mgr_fd_targets),
        "per_proxy_fd_has_vndbinder": any("/dev/vndbinder" in target for target in per_proxy_fd_targets),
        "per_mgr_socket_fd_count": sum(1 for target in per_mgr_fd_targets if target.startswith("socket:")),
        "per_proxy_socket_fd_count": sum(1 for target in per_proxy_fd_targets if target.startswith("socket:")),
    }

    stderr_summary = {
        "captured": bool(stderr),
        "bytes": len(stderr.encode("utf-8")),
        "has_per_mgr_text": any(token in stderr for token in ("PerMgr", "per_mgr", "pm-service", "Peripheral Mananager")),
        "has_pm_proxy_helper_property_context": "debug.ld.app.pm_proxy_helper" in stderr,
        "has_service_context_warning": "Multiple same specifications" in stderr,
        "diagnostic_for_pm_service_exit": False,
    }

    exact_syscall_proven = False
    eliminated = {
        "android_init_socket_missing": rc["per_mgr_block_present"] and not rc["per_mgr_socket_directive"],
        "pm_service_direct_literal_subsys_modem_open": binaries["pm_service_has_subsys_modem_literal"] is False
        and binaries["pm_proxy_helper_has_subsys_modem"],
        "short_lived_fd_missed_by_v1072": runtime["per_mgr_capture_exit"]
        and not runtime["per_mgr_fd_has_subsys_modem"]
        and not runtime["per_mgr_fd_has_vndbinder"],
        "stderr_sufficient_for_root_cause": False,
    }
    candidates = [
        {
            "name": "mdmdetect_system_info_or_peripheral_init_failure",
            "confidence": "medium",
            "host_evidence": [
                "pm-service links libmdmdetect.so",
                "pm-service strings include Failed to get system information / Failed to init peripheral",
                "libmdmdetect references /sys/bus/msm_subsys/devices, /sys/bus/esoc/devices, and /dev/subsys_%s",
            ],
            "missing_proof": "no syscall trace yet for the failed sysfs/device lookup",
        },
        {
            "name": "qmi_csi_qrtr_register_or_control_socket_failure",
            "confidence": "medium",
            "host_evidence": [
                "pm-service links libqmi_csi.so",
                "exit fd snapshot still contains socket fds",
                "libqmi_csi strings include qmi_csi_register and QRTR transport setup",
            ],
            "missing_proof": "socket family, bind/connect errno, and QMI register return code are not captured",
        },
        {
            "name": "vndbinder_add_service_failure",
            "confidence": "low-medium",
            "host_evidence": [
                "pm-service strings include /dev/vndbinder and Adding Peripheral Manager service fail",
                "V1071/V1072 materialized vndbinder but exit snapshot shows no vndbinder fd",
            ],
            "missing_proof": "whether pm-service reaches binder open/addService is not captured",
        },
    ]

    required_inputs = {
        "v1072_manifest": bool(manifest),
        "v1072_transcript": bool(transcript),
        "init_target_rc": bool(init_target_rc),
        "pm_proxy_helper_rc": bool(pm_proxy_helper_rc),
        "pm_service_strings": bool(pm_service_strings),
        "pm_proxy_strings": bool(pm_proxy_strings),
        "pm_proxy_helper_strings": bool(pm_proxy_helper_strings),
        "libmdmdetect_strings": bool(libmdmdetect_strings),
        "libperipheral_client_strings": bool(libperipheral_client_strings),
        "libqmi_csi_strings": bool(libqmi_csi_strings),
        "libqmi_cci_strings": bool(libqmi_cci_strings),
    }
    pass_ok = all(required_inputs.values()) and all(
        (
            rc["per_mgr_block_present"],
            not rc["per_mgr_socket_directive"],
            runtime["per_mgr_exit_code"] == "255",
            runtime["per_mgr_capture_exit"],
            stderr_summary["captured"],
            not exact_syscall_proven,
        )
    )
    decision = "v1073-pm-actor-exit-host-classified" if pass_ok else "v1073-pm-actor-exit-host-inputs-incomplete"
    reason = (
        "host-only rc/strings/evidence eliminate init socket creation and stale fd-observation gaps; "
        "exact exit-255 syscall remains unproven because pm-service logs are not present on stderr"
        if pass_ok
        else "one or more host-only inputs are missing or V1072 did not preserve the expected exit boundary"
    )
    next_step = (
        "V1074 bounded pm-service-only syscall/input classifier for openat/connect/bind/ioctl/property/binder/logd failures"
        if pass_ok
        else "refresh V1072 evidence and vendor string extraction before live work"
    )

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "required_inputs": required_inputs,
        "rc": rc,
        "binaries": binaries,
        "runtime": runtime,
        "stderr": stderr_summary,
        "eliminated": eliminated,
        "exact_syscall_proven": exact_syscall_proven,
        "likely_failure_classes": candidates,
        "host_only": True,
    }


def build_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    rc_rows = [[key, value] for key, value in c["rc"].items()]
    runtime = c["runtime"]
    runtime_rows = [
        ["v1072_decision", runtime["v1072_decision"]],
        ["per_mgr_exit_code", runtime["per_mgr_exit_code"]],
        ["per_mgr_capture_exit", runtime["per_mgr_capture_exit"]],
        ["per_mgr_fd_has_subsys_modem", runtime["per_mgr_fd_has_subsys_modem"]],
        ["per_mgr_fd_has_vndbinder", runtime["per_mgr_fd_has_vndbinder"]],
        ["per_mgr_socket_fd_count", runtime["per_mgr_socket_fd_count"]],
        ["per_proxy_exit_code", runtime["per_proxy_exit_code"]],
        ["per_proxy_socket_fd_count", runtime["per_proxy_socket_fd_count"]],
    ]
    binary_rows = [
        ["pm_service_needed", ", ".join(c["binaries"]["pm_service_needed"])],
        ["pm_service_has_vndbinder", c["binaries"]["pm_service_has_vndbinder"]],
        ["pm_service_has_subsys_modem_literal", c["binaries"]["pm_service_has_subsys_modem_literal"]],
        ["pm_service_has_system_info_fail", c["binaries"]["pm_service_has_system_info_fail"]],
        ["pm_service_has_qmi_csi_failure_strings", c["binaries"]["pm_service_has_qmi_csi_failure_strings"]],
        ["pm_proxy_helper_has_subsys_modem", c["binaries"]["pm_proxy_helper_has_subsys_modem"]],
        ["libmdmdetect_has_subsys_paths", c["binaries"]["libmdmdetect_has_esoc_and_msm_subsys_paths"]],
        ["libqmi_csi_has_qrtr_register_surface", c["binaries"]["libqmi_csi_has_qrtr_register_surface"]],
    ]
    stderr_rows = [[key, value] for key, value in c["stderr"].items()]
    eliminated_rows = [[key, value] for key, value in c["eliminated"].items()]
    candidate_rows = [
        [item["name"], item["confidence"], "; ".join(item["host_evidence"]), item["missing_proof"]]
        for item in c["likely_failure_classes"]
    ]
    return "\n".join(
        [
            "# V1073 PM Actor Exit Host Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            "## Runtime Boundary",
            "",
            markdown_table(["item", "value"], runtime_rows),
            "",
            "## Init RC",
            "",
            markdown_table(["item", "value"], rc_rows),
            "",
            "## Binary Surfaces",
            "",
            markdown_table(["item", "value"], binary_rows),
            "",
            "## Stderr Capture",
            "",
            markdown_table(["item", "value"], stderr_rows),
            "",
            "## Eliminated Causes",
            "",
            markdown_table(["item", "value"], eliminated_rows),
            "",
            "## Remaining Failure Classes",
            "",
            markdown_table(["class", "confidence", "host evidence", "missing proof"], candidate_rows),
            "",
            "## Scope",
            "",
            "- Host-only classifier; no device commands or live actors were executed.",
            "- Exact exit-255 syscall/reason is intentionally not claimed by this gate.",
            "- Next gate should trace `pm-service` only and keep mdm_helper/CNSS/HAL/scan/connect/DHCP/external ping forbidden.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    classification = build_classification(args)
    manifest = {
        "generated_at": now_iso(),
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "classification": classification,
        "device_commands_executed": False,
        "device_mutations": False,
        "live_actor_started": False,
        "service_manager_start_executed": False,
        "mdm_helper_start_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
