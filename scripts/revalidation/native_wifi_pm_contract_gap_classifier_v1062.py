#!/usr/bin/env python3
"""V1062 host-only PM contract gap classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v1062-pm-contract-gap-classifier")
DEFAULT_V1024_MANIFEST = Path("tmp/wifi/v1024-fast-fd-contract-classifier/manifest.json")
DEFAULT_V1061_MANIFEST = Path("tmp/wifi/v1061-global-firmware-pm-full-contract/manifest.json")
DEFAULT_V1061_HELPER = Path("tmp/wifi/v1061-global-firmware-pm-full-contract/native/pm-full-contract-with-global-firmware.txt")
DEFAULT_V1061_DMESG = Path("tmp/wifi/v1061-global-firmware-pm-full-contract/native/dmesg-delta.txt")
LATEST_POINTER = Path("tmp/wifi/latest-v1062-pm-contract-gap-classifier.txt")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1024-manifest", type=Path, default=DEFAULT_V1024_MANIFEST)
    parser.add_argument("--v1061-manifest", type=Path, default=DEFAULT_V1061_MANIFEST)
    parser.add_argument("--v1061-helper", type=Path, default=DEFAULT_V1061_HELPER)
    parser.add_argument("--v1061-dmesg", type=Path, default=DEFAULT_V1061_DMESG)
    parser.add_argument("command", choices=("run",), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def key_values(text: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for raw in text.splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        if key:
            pairs[key] = value.strip().strip('"')
    return pairs


def first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(0) if match else ""


def count_pattern(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.MULTILINE))


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1024 = load_json(args.v1024_manifest)
    v1061 = load_json(args.v1061_manifest)
    helper_text = read_text(args.v1061_helper)
    dmesg_text = read_text(args.v1061_dmesg)
    keys = key_values(helper_text)
    android_early = (((v1024.get("classification") or {}).get("early") or {}).get("fd") or {})
    android_late = (((v1024.get("classification") or {}).get("late") or {}).get("chain") or {})
    live = v1061.get("live") or {}
    contract = live.get("contract") or {}
    native = {
        "modem_pre_holder_confirmed": contract.get("modem_pre_holder_confirmed") == "1",
        "pm_proxy_helper_subsys_modem_fd_count": int(contract.get("pm_proxy_helper_subsys_modem_fd_count") or "0"),
        "per_mgr_subsys_modem_fd_count": int(contract.get("per_mgr_subsys_modem_fd_count") or "0"),
        "pm_full_contract_seen": contract.get("pm_full_contract_seen") == "1",
        "pm_proxy_started": contract.get("pm_proxy_started") == "1",
        "mdm_helper_esoc0_fd_seen": contract.get("mdm_helper_esoc0_fd_seen") == "1",
        "service_manager_start_executed": contract.get("service_manager_start_executed") == "1",
        "subsys_esoc0_open_attempted": contract.get("subsys_esoc0_open_attempted") == "1",
        "kernel_warning_count": ((live.get("markers") or {}).get("counts") or {}).get("kernel_warning", 0),
    }
    native_process = {
        "per_mgr_attr": first_match(helper_text, r"u:r:vendor_per_mgr:s0"),
        "per_mgr_vndbinder_count": keys.get("mdm_helper_provider_readiness.cnss_before_esoc_final.per_mgr_vndbinder_count", ""),
        "per_mgr_binder_count": keys.get("mdm_helper_provider_readiness.cnss_before_esoc_final.per_mgr_binder_count", ""),
        "per_mgr_hwbinder_count": keys.get("mdm_helper_provider_readiness.cnss_before_esoc_final.per_mgr_hwbinder_count", ""),
        "pm_service_process_count": keys.get("mdm_helper_provider_readiness.cnss_before_esoc_final.pm_service_count", ""),
        "pm_proxy_count": keys.get("mdm_helper_provider_readiness.cnss_before_esoc_final.pm_proxy_count", ""),
        "pm_proxy_helper_count": keys.get("mdm_helper_provider_readiness.cnss_before_esoc_final.pm_proxy_helper_count", ""),
        "property_sdx50m_state_offline": count_pattern(helper_text, r"vendor\.peripheral\.SDX50M\.state.*OFFLINE"),
        "property_modem_state_offline": count_pattern(helper_text, r"vendor\.peripheral\.modem\.state.*OFFLINE"),
        "property_shutdown_list": count_pattern(helper_text, r"vendor\.peripheral\.shutdown_critical_list"),
    }
    warning = {
        "reference_count_mismatch": "Reference count mismatch" in dmesg_text,
        "subsystem_put_esoc0_count0": "subsystem_put: esoc0 count:0" in dmesg_text,
        "first_warning": first_match(dmesg_text, r"WARNING: CPU:.*subsystem_put.*"),
    }
    android_positive = bool(
        android_early.get("pm_proxy_helper_subsys_modem_fd")
        and android_early.get("pm_service_subsys_modem_fd")
        and android_early.get("mdm_helper_esoc0_fd")
        and android_late.get("wlfw_chain")
    )
    native_same_prefix = bool(
        native["modem_pre_holder_confirmed"]
        and native["pm_proxy_helper_subsys_modem_fd_count"] > 0
        and native["pm_proxy_started"]
        and native["mdm_helper_esoc0_fd_seen"]
    )
    native_gap = native_same_prefix and native["per_mgr_subsys_modem_fd_count"] == 0
    if android_positive and native_gap and warning["reference_count_mismatch"]:
        decision = "v1062-per-mgr-fd-gap-plus-esoc-warning-classified"
        reason = "Android has pm-service /dev/subsys_modem fd and WLFW chain, while V1061 reaches the prefix but native per_mgr never opens /dev/subsys_modem and cleanup emits esoc0 refcount warning"
        next_step = "classify pm-service binder/property trigger and esoc0 cleanup mismatch before any live retry"
    elif android_positive and native_gap:
        decision = "v1062-per-mgr-subsys-modem-fd-gap-classified"
        reason = "Android has pm-service /dev/subsys_modem fd, while V1061 native per_mgr does not"
        next_step = "classify pm-service binder/property trigger before live retry"
    else:
        decision = "v1062-pm-contract-gap-incomplete"
        reason = "available evidence does not isolate the Android/native PM fd delta"
        next_step = "refresh Android PM fd evidence or V1061 helper transcript"
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": True,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v1024_manifest": str(repo_path(args.v1024_manifest)),
            "v1061_manifest": str(repo_path(args.v1061_manifest)),
            "v1061_helper": str(repo_path(args.v1061_helper)),
            "v1061_dmesg": str(repo_path(args.v1061_dmesg)),
        },
        "android": {
            "pm_proxy_helper_subsys_modem_fd": bool(android_early.get("pm_proxy_helper_subsys_modem_fd")),
            "pm_service_subsys_modem_fd": bool(android_early.get("pm_service_subsys_modem_fd")),
            "mdm_helper_esoc0_fd": bool(android_early.get("mdm_helper_esoc0_fd")),
            "wlfw_chain": bool(android_late.get("wlfw_chain")),
            "wlfw_start": android_late.get("wlfw_start"),
            "subsys_esoc0_get": android_late.get("subsys_esoc0_get"),
            "wlan0": android_late.get("wlan0"),
        },
        "native": native,
        "native_process": native_process,
        "warning": warning,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    android_rows = [[key, str(value)] for key, value in manifest["android"].items()]
    native_rows = [[key, str(value)] for key, value in manifest["native"].items()]
    process_rows = [[key, str(value)] for key, value in manifest["native_process"].items()]
    warning_rows = [[key, str(value)] for key, value in manifest["warning"].items()]
    return "\n".join([
        "# V1062 PM Contract Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Android Positive",
        "",
        markdown_table(["item", "value"], android_rows),
        "",
        "## Native V1061",
        "",
        markdown_table(["item", "value"], native_rows),
        "",
        "## Native Process Surface",
        "",
        markdown_table(["item", "value"], process_rows),
        "",
        "## Warning",
        "",
        markdown_table(["item", "value"], warning_rows),
    ]) + "\n"


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = classify(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    repo_path(LATEST_POINTER).write_text(str(store.run_dir.relative_to(repo_path("."))) + "\n", encoding="utf-8")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
