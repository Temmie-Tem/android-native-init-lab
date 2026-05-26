#!/usr/bin/env python3
"""V1028 host-only classifier for the native pm_proxy_helper modem-get blocker."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1028-pm-proxy-helper-modem-get-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1028-pm-proxy-helper-modem-get-classifier.txt")
DEFAULT_V1024_MANIFEST = Path("tmp/wifi/v1024-fast-fd-contract-classifier/manifest.json")
DEFAULT_V1027_MANIFEST = Path("tmp/wifi/v1027-pm-full-contract-live/manifest.json")
DEFAULT_V1027_DIR = Path("tmp/wifi/v1027-pm-full-contract-live")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1024-manifest", type=Path, default=DEFAULT_V1024_MANIFEST)
    parser.add_argument("--v1027-manifest", type=Path, default=DEFAULT_V1027_MANIFEST)
    parser.add_argument("--v1027-dir", type=Path, default=DEFAULT_V1027_DIR)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path, limit: int = 8_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {"_missing": True, "_path": str(path)}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"_invalid": True, "_path": str(path)}
    if not isinstance(payload, dict):
        return {"_invalid": True, "_path": str(path)}
    payload["_path"] = str(path)
    return payload


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "pass"}
    return False


def intish(value: Any, default: int = -1) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def contract_from_manifest(manifest: dict[str, Any]) -> dict[str, str]:
    helper = ((manifest.get("analysis") or {}).get("helper") or {})
    contract = helper.get("contract") or {}
    return {str(key): str(value) for key, value in contract.items()}


def selected_lines(text: str, pattern: str, limit: int = 12) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line and regex.search(line):
            lines.append(line)
            if len(lines) >= limit:
                break
    return lines


def android_contract(v1024: dict[str, Any]) -> dict[str, Any]:
    classification = v1024.get("classification") or {}
    early = classification.get("early") or {}
    late = classification.get("late") or {}
    fd = early.get("fd") or {}
    chain = late.get("chain") or {}
    return {
        "manifest_path": v1024.get("_path", str(DEFAULT_V1024_MANIFEST)),
        "decision": v1024.get("decision"),
        "pass": boolish(v1024.get("pass")),
        "pm_proxy_helper_subsys_modem_fd": boolish(fd.get("pm_proxy_helper_subsys_modem_fd")),
        "pm_service_subsys_modem_fd": boolish(fd.get("pm_service_subsys_modem_fd")),
        "mdm_helper_esoc0_fd": boolish(fd.get("mdm_helper_esoc0_fd")),
        "wlfw_chain": boolish(chain.get("wlfw_chain")),
        "native_rollback_verified": boolish(((classification.get("wrapper") or {}).get("native_rollback_verified"))),
        "handoff_dir": classification.get("handoff_dir", ""),
    }


def native_contract(v1027: dict[str, Any], v1027_dir: Path) -> dict[str, Any]:
    contract = contract_from_manifest(v1027)
    post_ps = read_text(v1027_dir / "native/post-ps.txt")
    post_dmesg = read_text(v1027_dir / "native/post-dmesg-wifi-esoc-tail.txt")

    helper_fd_count = intish(contract.get("pm_proxy_helper_subsys_modem_fd_count"))
    per_mgr_fd_count = intish(contract.get("per_mgr_subsys_modem_fd_count"))
    mdm_helper_esoc0_fd_count = intish(contract.get("mdm_helper_esoc0_fd_count"))
    pm_full_contract_poll_count = intish(contract.get("pm_full_contract_poll_count"))

    dmesg_modem_get_lines = selected_lines(
        post_dmesg,
        r"pm_proxy_helper.*(__subsystem_get:\s+modem|Changing subsys fw_name to modem|modem: loading)",
    )
    ps_pm_helper_lines = selected_lines(post_ps, r"\bpm_proxy_helper\b", limit=6)

    return {
        "manifest_path": v1027.get("_path", str(DEFAULT_V1027_MANIFEST)),
        "decision": v1027.get("decision"),
        "pass": boolish(v1027.get("pass")),
        "cleanup_reboot_executed": boolish(v1027.get("cleanup_reboot_executed")),
        "pm_proxy_helper_start_executed": (
            boolish(v1027.get("pm_proxy_helper_start_executed"))
            or boolish(contract.get("pm_proxy_helper_start_executed"))
            or boolish(contract.get("pm_proxy_helper_start_attempted"))
        ),
        "per_mgr_start_executed": (
            boolish(v1027.get("per_mgr_light_start_executed"))
            or boolish(contract.get("per_mgr_start_attempted"))
        ),
        "pm_proxy_start_executed": (
            boolish(v1027.get("pm_proxy_start_executed"))
            or boolish(contract.get("pm_proxy_start_attempted"))
        ),
        "mdm_helper_start_executed": (
            boolish(v1027.get("mdm_helper_start_executed"))
            or boolish(contract.get("mdm_helper_start_attempted"))
        ),
        "pm_proxy_helper_subsys_modem_fd_count": helper_fd_count,
        "per_mgr_subsys_modem_fd_count": per_mgr_fd_count,
        "mdm_helper_esoc0_fd_count": mdm_helper_esoc0_fd_count,
        "pm_full_contract_seen": boolish(v1027.get("pm_full_contract_seen")) or boolish(contract.get("pm_full_contract_seen")),
        "pm_full_contract_poll_count": pm_full_contract_poll_count,
        "pm_proxy_helper_postflight_safe": boolish(contract.get("pm_proxy_helper.postflight_safe")),
        "contract_result": contract.get("result", ""),
        "service_manager_start_executed": boolish(v1027.get("service_manager_start_executed")) or boolish(contract.get("service_manager_start_executed")),
        "cnss_diag_start_executed": boolish(v1027.get("cnss_diag_start_executed")),
        "cnss_daemon_start_executed": boolish(v1027.get("cnss_daemon_start_executed")),
        "subsys_esoc0_open_attempted": boolish(v1027.get("subsys_esoc0_open_attempted")) or boolish(contract.get("subsys_esoc0_open_attempted")),
        "wifi_hal_start_executed": boolish(v1027.get("wifi_hal_start_executed")) or boolish(contract.get("wifi_hal_start_executed")),
        "scan_connect_executed": boolish(v1027.get("scan_connect_executed")) or boolish(contract.get("scan_connect_linkup")),
        "credential_use_executed": boolish(v1027.get("credential_use_executed")) or boolish(contract.get("credentials")),
        "dhcp_route_executed": boolish(v1027.get("dhcp_route_executed")) or boolish(contract.get("dhcp_routing")),
        "external_ping_executed": boolish(v1027.get("external_ping_executed")) or boolish(contract.get("external_ping")),
        "dmesg_modem_get_present": bool(dmesg_modem_get_lines),
        "dmesg_modem_get_lines": dmesg_modem_get_lines,
        "pm_proxy_helper_ds_present": any(" Ds " in line and "pm_proxy_helper" in line for line in ps_pm_helper_lines),
        "pm_proxy_helper_ps_lines": ps_pm_helper_lines,
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1024 = load_json(args.v1024_manifest)
    v1027 = load_json(args.v1027_manifest)
    android = android_contract(v1024)
    native = native_contract(v1027, args.v1027_dir)

    android_positive_contract = (
        android["pass"]
        and android["decision"] == "v1024-android-pm-esoc-fd-contract-captured"
        and android["pm_proxy_helper_subsys_modem_fd"]
        and android["pm_service_subsys_modem_fd"]
        and android["mdm_helper_esoc0_fd"]
        and android["wlfw_chain"]
    )
    native_process_order_reproduced = (
        native["pass"]
        and native["decision"] == "v1027-pm-full-contract-missing-no-open"
        and native["pm_proxy_helper_start_executed"]
        and native["per_mgr_start_executed"]
        and native["pm_proxy_start_executed"]
        and native["mdm_helper_start_executed"]
    )
    native_pm_fd_missing = (
        native["pm_proxy_helper_subsys_modem_fd_count"] == 0
        and native["per_mgr_subsys_modem_fd_count"] == 0
        and not native["pm_full_contract_seen"]
        and native["pm_full_contract_poll_count"] > 0
    )
    native_lower_guardrails_clean = (
        native["mdm_helper_esoc0_fd_count"] >= 1
        and not native["service_manager_start_executed"]
        and not native["cnss_diag_start_executed"]
        and not native["cnss_daemon_start_executed"]
        and not native["subsys_esoc0_open_attempted"]
        and not native["wifi_hal_start_executed"]
        and not native["scan_connect_executed"]
        and not native["credential_use_executed"]
        and not native["dhcp_route_executed"]
        and not native["external_ping_executed"]
    )
    native_modem_get_blocker = (
        native["dmesg_modem_get_present"]
        and native["pm_proxy_helper_ds_present"]
        and not native["pm_proxy_helper_postflight_safe"]
        and native["contract_result"] == "reboot-required"
        and native["cleanup_reboot_executed"]
    )

    checks = {
        "v1024_input_present": not v1024.get("_missing") and not v1024.get("_invalid"),
        "v1027_input_present": not v1027.get("_missing") and not v1027.get("_invalid"),
        "android_positive_pm_fd_contract": android_positive_contract,
        "native_process_order_reproduced": native_process_order_reproduced,
        "native_pm_fd_missing": native_pm_fd_missing,
        "native_lower_guardrails_clean": native_lower_guardrails_clean,
        "native_modem_get_blocker": native_modem_get_blocker,
    }

    if all(checks.values()):
        decision = "v1028-pm-proxy-helper-modem-get-blocker-classified"
        passed = True
        reason = (
            "Android proves the PM fd contract, while native V1027 starts the PM actors but "
            "pm_proxy_helper blocks in modem subsystem-get before an observable /dev/subsys_modem fd appears"
        )
        route = "v1029-pm-proxy-helper-runtime-input-delta"
        next_step = (
            "Classify Android/native pm_proxy_helper runtime inputs and service context before another live retry; "
            "do not repeat V1027 unchanged"
        )
    elif android_positive_contract and native_process_order_reproduced and native_pm_fd_missing:
        decision = "v1028-pm-fd-gap-confirmed-but-blocker-evidence-incomplete"
        passed = True
        reason = "native PM fd gap is reproduced, but dmesg/postflight cleanup evidence is incomplete"
        route = "v1029-targeted-pm-proxy-helper-wchan-capture"
        next_step = "Add a bounded live capture for pm_proxy_helper wchan/stack/fdinfo before cleanup"
    else:
        missing = ", ".join(name for name, ok in checks.items() if not ok)
        decision = "v1028-pm-proxy-helper-classifier-inputs-incomplete"
        passed = False
        reason = f"required evidence missing or contradictory: {missing}"
        route = "repair-v1024-or-v1027-evidence"
        next_step = "Recreate the missing Android or native evidence before changing helper behavior"

    return {
        "decision": decision,
        "pass": passed,
        "route": route,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "android": android,
        "native": native,
        "guardrails": {
            "device_contact_executed": False,
            "device_mutations": False,
            "actor_start_executed": False,
            "daemon_start_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "boot_image_write_executed": False,
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    android = classification["android"]
    native = classification["native"]
    checks = classification["checks"]
    native_rows = [
        ["decision", native["decision"]],
        ["pm_proxy_helper_start_executed", native["pm_proxy_helper_start_executed"]],
        ["per_mgr_start_executed", native["per_mgr_start_executed"]],
        ["pm_proxy_start_executed", native["pm_proxy_start_executed"]],
        ["mdm_helper_start_executed", native["mdm_helper_start_executed"]],
        ["pm_proxy_helper_subsys_modem_fd_count", native["pm_proxy_helper_subsys_modem_fd_count"]],
        ["per_mgr_subsys_modem_fd_count", native["per_mgr_subsys_modem_fd_count"]],
        ["mdm_helper_esoc0_fd_count", native["mdm_helper_esoc0_fd_count"]],
        ["pm_full_contract_poll_count", native["pm_full_contract_poll_count"]],
        ["pm_proxy_helper_postflight_safe", native["pm_proxy_helper_postflight_safe"]],
        ["contract_result", native["contract_result"]],
        ["cleanup_reboot_executed", native["cleanup_reboot_executed"]],
    ]
    android_rows = [
        ["decision", android["decision"]],
        ["pm_proxy_helper_subsys_modem_fd", android["pm_proxy_helper_subsys_modem_fd"]],
        ["pm_service_subsys_modem_fd", android["pm_service_subsys_modem_fd"]],
        ["mdm_helper_esoc0_fd", android["mdm_helper_esoc0_fd"]],
        ["wlfw_chain", android["wlfw_chain"]],
    ]
    return "\n".join(
        [
            "# V1028 PM Proxy Helper Modem-Get Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- route: `{classification['route']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            "## Checks",
            "",
            markdown_table(["check", "value"], [[key, value] for key, value in checks.items()]),
            "",
            "## Android Positive Contract",
            "",
            markdown_table(["item", "value"], android_rows),
            "",
            "## Native V1027 Delta",
            "",
            markdown_table(["item", "value"], native_rows),
            "",
            "## Native Evidence Lines",
            "",
            "### Dmesg",
            "",
            "\n".join(f"- `{line}`" for line in native["dmesg_modem_get_lines"]) or "- none",
            "",
            "### Process",
            "",
            "\n".join(f"- `{line}`" for line in native["pm_proxy_helper_ps_lines"]) or "- none",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        classification = {
            "decision": "v1028-pm-proxy-helper-modem-get-classifier-plan-ready",
            "pass": True,
            "route": "host-only-v1024-v1027-comparison",
            "reason": "plan-only; no live device contact required",
            "next_step": "run classifier against V1024 Android and V1027 native evidence",
            "checks": {},
            "android": {},
            "native": {"dmesg_modem_get_lines": [], "pm_proxy_helper_ps_lines": []},
            "guardrails": {"device_contact_executed": False, "device_mutations": False},
        }
    else:
        classification = classify(args)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "classification": classification,
        "device_commands_executed": False,
        "device_mutations": False,
        "actor_start_executed": False,
        "daemon_start_executed": False,
        "wifi_command_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
