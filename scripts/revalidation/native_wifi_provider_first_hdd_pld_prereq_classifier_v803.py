#!/usr/bin/env python3
"""V803 host-only provider-first HDD/PLD prerequisite classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v803-provider-first-hdd-pld-prereq-classifier")
DEFAULT_V802_MANIFEST = Path("tmp/wifi/v802-provider-first-boot-wlan-observe-orchestrated-live-fixed/manifest.json")
DEFAULT_V802_DIRECT_MANIFEST = Path(
    "tmp/wifi/v802-provider-first-boot-wlan-observe-orchestrated-live-fixed/arm-v802-provider-first-boot-wlan/live/manifest.json"
)
DEFAULT_V802_DMESG = Path(
    "tmp/wifi/v802-provider-first-boot-wlan-observe-orchestrated-live-fixed/arm-v802-provider-first-boot-wlan/live/native/dmesg-delta.txt"
)
DEFAULT_V802_BOOT = Path(
    "tmp/wifi/v802-provider-first-boot-wlan-observe-orchestrated-live-fixed/arm-v802-provider-first-boot-wlan/live/native/boot-wlan-observe-after-cnss.txt"
)
DEFAULT_SOURCE_ROOT = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source")

HDD_MAIN = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.c"
HDD_OPS = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c"
PLD_SNOC = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/src/pld_snoc.c"
ICNSS = "drivers/soc/qcom/icnss.c"

SOURCE_ANCHORS = {
    "hdd_loading_driver": ("hdd_main", r"Loading driver v"),
    "hdd_init_call": ("hdd_main", r"errno = hdd_init\(\);"),
    "qcwlanstate_create_call": ("hdd_main", r"wlan_hdd_state_ctrl_param_create\(\);"),
    "pld_init_call": ("hdd_main", r"errno = pld_init\(\);"),
    "register_driver_call": ("hdd_main", r"errno = wlan_hdd_register_driver\(\);"),
    "driver_loaded_marker": ("hdd_main", r"driver loaded"),
    "hdd_wlan_startup": ("hdd_main", r"int hdd_wlan_startup\s*\("),
    "hdd_register_driver_definition": ("hdd_ops", r"int wlan_hdd_register_driver\s*\("),
    "hdd_register_to_pld": ("hdd_ops", r"return pld_register_driver\(&wlan_drv_ops\);"),
    "pld_snoc_register_definition": ("pld_snoc", r"int pld_snoc_register_driver\s*\("),
    "pld_snoc_to_icnss": ("pld_snoc", r"return icnss_register_driver\(&pld_snoc_ops\);"),
    "icnss_register_driver_definition": ("icnss", r"int __icnss_register_driver\s*\("),
    "icnss_qcwlanstate_off_marker": ("icnss", r"Modules not initialized just return"),
}

FORBIDDEN_ACTIONS = (
    "device command",
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "qcwlanstate or boot_wlan write",
    "esoc0 open or hold",
    "bind/unbind, driver_override, or module load/unload",
    "boot image or partition write",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v802-manifest", type=Path, default=DEFAULT_V802_MANIFEST)
    parser.add_argument("--v802-direct-manifest", type=Path, default=DEFAULT_V802_DIRECT_MANIFEST)
    parser.add_argument("--v802-dmesg", type=Path, default=DEFAULT_V802_DMESG)
    parser.add_argument("--v802-boot", type=Path, default=DEFAULT_V802_BOOT)
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
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def line_of(text: str, pattern: str) -> int | None:
    regex = re.compile(pattern)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return None


def count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def path_info(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    return {
        "path": str(resolved),
        "exists": resolved.exists(),
        "is_file": resolved.is_file(),
        "is_dir": resolved.is_dir(),
        "size": resolved.stat().st_size if resolved.exists() and resolved.is_file() else None,
    }


def load_sources(source_root: Path) -> dict[str, str]:
    root = repo_path(source_root)
    return {
        "hdd_main": read_text(root / HDD_MAIN),
        "hdd_ops": read_text(root / HDD_OPS),
        "pld_snoc": read_text(root / PLD_SNOC),
        "icnss": read_text(root / ICNSS),
    }


def analyze_source(args: argparse.Namespace) -> dict[str, Any]:
    sources = load_sources(args.source_root)
    anchors: dict[str, dict[str, Any]] = {}
    for name, (source_key, pattern) in SOURCE_ANCHORS.items():
        anchors[name] = {
            "source": source_key,
            "line": line_of(sources.get(source_key, ""), pattern),
            "pattern": pattern,
        }
    order = [
        anchors["hdd_loading_driver"]["line"],
        anchors["hdd_init_call"]["line"],
        anchors["qcwlanstate_create_call"]["line"],
        anchors["pld_init_call"]["line"],
        anchors["register_driver_call"]["line"],
        anchors["driver_loaded_marker"]["line"],
    ]
    ordered = all(isinstance(item, int) for item in order) and order == sorted(order)
    source_files = {
        HDD_MAIN: path_info(args.source_root / HDD_MAIN),
        HDD_OPS: path_info(args.source_root / HDD_OPS),
        PLD_SNOC: path_info(args.source_root / PLD_SNOC),
        ICNSS: path_info(args.source_root / ICNSS),
    }
    return {
        "source_root": str(repo_path(args.source_root)),
        "source_files": source_files,
        "anchors": anchors,
        "hdd_module_init_order_verified": ordered,
        "register_chain_verified": all(
            anchors[name]["line"]
            for name in (
                "hdd_register_driver_definition",
                "hdd_register_to_pld",
                "pld_snoc_register_definition",
                "pld_snoc_to_icnss",
                "icnss_register_driver_definition",
            )
        ),
    }


def extract_boot_value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}=(.*)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def analyze_v802(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v802_manifest)
    direct = load_json(args.v802_direct_manifest)
    dmesg = read_text(args.v802_dmesg)
    boot = read_text(args.v802_boot)
    arm = manifest.get("arm_v802") if isinstance(manifest.get("arm_v802"), dict) else {}
    counts = arm.get("counts") if isinstance(arm.get("counts"), dict) else {}
    helper = arm.get("helper") if isinstance(arm.get("helper"), dict) else {}
    direct_live = direct.get("live") if isinstance(direct.get("live"), dict) else {}
    direct_counts = ((direct_live.get("markers") or {}).get("counts") or {}) if isinstance(direct_live.get("markers"), dict) else {}
    return {
        "manifest": str(repo_path(args.v802_manifest)),
        "direct_manifest": str(repo_path(args.v802_direct_manifest)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "direct_decision": direct.get("decision", ""),
        "direct_pass": bool(direct.get("pass")),
        "provider_first_context_executed": bool(manifest.get("provider_first_context_executed")),
        "boot_wlan_write_executed": bool(manifest.get("boot_wlan_write_executed")),
        "forbidden_connection_actions_absent": not any(
            bool(manifest.get(key))
            for key in ("wifi_hal_start_executed", "scan_connect_executed", "credential_use_executed", "dhcp_route_executed", "external_ping_executed")
        ),
        "counts": counts or direct_counts,
        "helper": helper,
        "dmesg_counts": {
            "loading_driver": count(dmesg, r"wlan: Loading driver"),
            "driver_loaded": count(dmesg, r"wlan: driver loaded"),
            "modules_not_initialized": count(dmesg, r"Modules not initialized just return"),
            "icnss_qmi": count(dmesg, r"icnss.*qmi|qmi.*icnss"),
            "wlfw": count(dmesg, r"wlfw"),
            "bdf": count(dmesg, r"\bbdf\b|bdwlan|regdb"),
            "wlan0": count(dmesg, r"\bwlan0\b"),
        },
        "boot_after": {
            "qcwlanstate": extract_boot_value(boot, "wlanboot.after.qcwlanstate.value"),
            "sys_class_wlan_dev": extract_boot_value(boot, "wlanboot.after.sys_class_wlan_dev.value"),
            "dev_wlan_exists": extract_boot_value(boot, "wlanboot.after.dev_wlan.exists"),
            "wlan0_exists": extract_boot_value(boot, "wlanboot.after.sys_class_net_wlan0.exists"),
            "ieee80211_count": extract_boot_value(boot, "wlanboot.after.sys_class_ieee80211.count"),
            "result": extract_boot_value(boot, "wlanboot.result"),
        },
    }


def build_checks(command: str, v802: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only classifier; no device command",
            "next_step": "run V803 host-only classifier",
        }]
    counts = v802.get("counts") if isinstance(v802.get("counts"), dict) else {}
    dmesg_counts = v802.get("dmesg_counts") if isinstance(v802.get("dmesg_counts"), dict) else {}
    boot_after = v802.get("boot_after") if isinstance(v802.get("boot_after"), dict) else {}
    return [
        {
            "name": "v802-reference-ready",
            "status": "pass" if v802.get("pass") and v802.get("provider_first_context_executed") and v802.get("boot_wlan_write_executed") else "blocked",
            "detail": {
                "decision": v802.get("decision"),
                "pass": v802.get("pass"),
                "provider_first_context_executed": v802.get("provider_first_context_executed"),
                "boot_wlan_write_executed": v802.get("boot_wlan_write_executed"),
            },
            "next_step": "rerun/fix V802 before V803",
        },
        {
            "name": "connection-boundary-not-crossed",
            "status": "pass" if v802.get("forbidden_connection_actions_absent") else "blocked",
            "detail": {"forbidden_connection_actions_absent": v802.get("forbidden_connection_actions_absent")},
            "next_step": "stop if V802 crossed Wi-Fi HAL/connect boundary",
        },
        {
            "name": "hdd-stall-reproduced",
            "status": "pass" if int_value(counts.get("wlan_loading")) and not int_value(counts.get("wlan_driver_loaded")) else "blocked",
            "detail": {
                "wlan_loading": counts.get("wlan_loading"),
                "hdd_state_major": counts.get("hdd_state_major"),
                "qcwlanstate": counts.get("qcwlanstate"),
                "wlan_driver_loaded": counts.get("wlan_driver_loaded"),
                "dmesg": dmesg_counts,
                "boot_after": boot_after,
            },
            "next_step": "classify source window only after HDD stall is reproduced",
        },
        {
            "name": "wlfw-netdev-absent",
            "status": "pass" if not any(int_value(counts.get(name)) for name in ("icnss_qmi_connected", "fw_ready", "wlfw", "bdf", "wlan0", "wiphy")) else "finding",
            "detail": {name: counts.get(name) for name in ("icnss_qmi_connected", "fw_ready", "wlfw", "bdf", "wlan0", "wiphy")},
            "next_step": "if any appears, route to driver-ready-to-netdev classifier",
        },
        {
            "name": "source-order-verified",
            "status": "pass" if source.get("hdd_module_init_order_verified") and source.get("register_chain_verified") else "blocked",
            "detail": {
                "hdd_module_init_order_verified": source.get("hdd_module_init_order_verified"),
                "register_chain_verified": source.get("register_chain_verified"),
            },
            "next_step": "refresh OSRC staging before deriving the HDD/PLD boundary",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]], v802: dict[str, Any], source: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v803-provider-first-hdd-pld-prereq-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only V803 classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return "v803-provider-first-hdd-pld-prereq-classifier-blocked", False, "blocked by " + ", ".join(blocked), "clear host evidence blocker"
    counts = v802.get("counts") if isinstance(v802.get("counts"), dict) else {}
    if int_value(counts.get("hdd_state_major")) or v802.get("boot_after", {}).get("sys_class_wlan_dev"):
        return (
            "v803-hdd-pld-register-boundary-selected",
            True,
            "V802 reached HDD/qcwlanstate after provider-first boot_wlan, while source order places driver-loaded after PLD/register-driver; next blocker is before or inside PLD/ICNSS register/probe completion",
            "classify PLD/ICNSS register/probe prerequisites without custom-kernel flash",
        )
    return (
        "v803-hdd-entry-boundary-selected",
        True,
        "V802 loading marker appears without enough post-HDD surface; next blocker remains early HDD init",
        "classify hdd_init and qcwlanstate creation prerequisites",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v802 = analyze_v802(args)
    source = analyze_source(args)
    checks = build_checks(args.command, v802, source)
    decision, pass_ok, reason, next_step = decide(args.command, checks, v802, source)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v803",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v802_manifest": str(repo_path(args.v802_manifest)),
            "v802_direct_manifest": str(repo_path(args.v802_direct_manifest)),
            "v802_dmesg": str(repo_path(args.v802_dmesg)),
            "v802_boot": str(repo_path(args.v802_boot)),
            "source_root": str(repo_path(args.source_root)),
        },
        "v802": v802,
        "source": source,
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    v802 = manifest["v802"]
    source = manifest["source"]
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    source_rows = [
        [name, data["source"], str(data["line"]), data["pattern"]]
        for name, data in source["anchors"].items()
    ]
    v802_rows = [
        ["decision", v802.get("decision", "")],
        ["direct_decision", v802.get("direct_decision", "")],
        ["provider_first_context_executed", str(v802.get("provider_first_context_executed"))],
        ["boot_wlan_write_executed", str(v802.get("boot_wlan_write_executed"))],
        ["counts", json.dumps(v802.get("counts", {}), sort_keys=True)],
        ["dmesg_counts", json.dumps(v802.get("dmesg_counts", {}), sort_keys=True)],
        ["boot_after", json.dumps(v802.get("boot_after", {}), sort_keys=True)],
    ]
    return "\n".join([
        "# V803 Provider-first HDD/PLD Prerequisite Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## V802 Evidence",
        "",
        markdown_table(["key", "value"], v802_rows),
        "",
        "## Source Anchors",
        "",
        markdown_table(["anchor", "source", "line", "pattern"], source_rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"credential_use_executed: {manifest['credential_use_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
