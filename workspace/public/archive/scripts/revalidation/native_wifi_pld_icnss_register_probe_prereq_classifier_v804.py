#!/usr/bin/env python3
"""V804 host-only PLD/ICNSS register/probe prerequisite classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, config_state, markdown_table, parse_kernel_config, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v804-pld-icnss-register-probe-prereq-classifier")
DEFAULT_V775_MANIFEST = Path("tmp/wifi/v775-boot-incompat-postmortem/manifest.json")
DEFAULT_V803_MANIFEST = Path("tmp/wifi/v803-provider-first-hdd-pld-prereq-classifier/manifest.json")
DEFAULT_V802_MANIFEST = Path("tmp/wifi/v802-provider-first-boot-wlan-observe-orchestrated-live-fixed/manifest.json")
DEFAULT_V802_DMESG = Path(
    "tmp/wifi/v802-provider-first-boot-wlan-observe-orchestrated-live-fixed/arm-v802-provider-first-boot-wlan/live/native/dmesg-delta.txt"
)
DEFAULT_V802_BOOT = Path(
    "tmp/wifi/v802-provider-first-boot-wlan-observe-orchestrated-live-fixed/arm-v802-provider-first-boot-wlan/live/native/boot-wlan-observe-after-cnss.txt"
)
DEFAULT_STOCK_CONFIG = Path("tmp/wifi/v772-boot-incompat-classifier/logs/base-ikconfig.txt")
DEFAULT_SOURCE_ROOT = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source")

HDD_MAIN = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.c"
HDD_OPS = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c"
PLD_COMMON = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/src/pld_common.c"
PLD_SNOC = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/src/pld_snoc.c"
ICNSS = "drivers/soc/qcom/icnss.c"
KBUILD = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/Kbuild"

CONFIG_KEYS = (
    "CONFIG_QCA_CLD_WLAN",
    "CONFIG_WLAN",
    "CONFIG_ICNSS",
    "CONFIG_ICNSS_QMI",
    "CONFIG_CNSS2",
    "CONFIG_CNSS_QCA6390",
    "CONFIG_HIF_PCI",
    "CONFIG_PCIE_FW_SIM",
    "CONFIG_SNOC_FW_SIM",
    "CONFIG_QCA_WIFI_SDIO",
    "CONFIG_HIF_USB",
)

ANCHORS = {
    "hdd_loading_driver": ("hdd_main", r"Loading driver v"),
    "hdd_qcwlanstate_create": ("hdd_main", r"wlan_hdd_state_ctrl_param_create\(\);"),
    "hdd_pld_init_call": ("hdd_main", r"errno = pld_init\(\);"),
    "hdd_register_driver_call": ("hdd_main", r"errno = wlan_hdd_register_driver\(\);"),
    "hdd_driver_loaded_marker": ("hdd_main", r"driver loaded"),
    "hdd_start_modules_enabled": ("hdd_main", r"hdd_ctx->driver_status = DRIVER_MODULES_ENABLED;"),
    "hdd_sysfs_updates_enabled": ("hdd_main", r"hdd_sysfs_update_driver_status\(DRIVER_MODULES_ENABLED\);"),
    "hdd_register_to_pld": ("hdd_ops", r"return pld_register_driver\(&wlan_drv_ops\);"),
    "hdd_ops_probe": ("hdd_ops", r"\.probe\s*=\s*wlan_hdd_pld_probe"),
    "hdd_ops_remove": ("hdd_ops", r"\.remove\s*=\s*wlan_hdd_pld_remove"),
    "hdd_ops_suspend": ("hdd_ops", r"\.suspend\s*=\s*wlan_hdd_pld_suspend"),
    "hdd_ops_resume": ("hdd_ops", r"\.resume\s*=\s*wlan_hdd_pld_resume"),
    "hdd_pld_probe_to_soc_probe": ("hdd_ops", r"return hdd_soc_probe\(dev, bdev, id, bus_type\);"),
    "hdd_soc_probe_to_startup": ("hdd_ops", r"errno = hdd_wlan_startup\(hdd_ctx\);"),
    "pld_init_definition": ("pld_common", r"int pld_init\(void\)"),
    "pld_global_context_set": ("pld_common", r"pld_ctx = pld_context;"),
    "pld_register_definition": ("pld_common", r"int pld_register_driver\(struct pld_driver_ops \*ops\)"),
    "pld_context_null_guard": ("pld_common", r"global context is NULL"),
    "pld_already_registered_guard": ("pld_common", r"driver already registered"),
    "pld_callback_guard": ("pld_common", r"Required callback functions are missing"),
    "pld_pcie_register_call": ("pld_common", r"ret = pld_pcie_register_driver\(\);"),
    "pld_snoc_register_call": ("pld_common", r"ret = pld_snoc_register_driver\(\);"),
    "pld_snoc_to_icnss": ("pld_snoc", r"return icnss_register_driver\(&pld_snoc_ops\);"),
    "pld_snoc_probe": ("pld_snoc", r"static int pld_snoc_probe"),
    "pld_snoc_probe_to_hdd": ("pld_snoc", r"return pld_context->ops->probe\(dev, PLD_BUS_TYPE_SNOC"),
    "icnss_register_definition": ("icnss", r"int __icnss_register_driver"),
    "icnss_penv_pdev_guard": ("icnss", r"if \(!penv \|\| !penv->pdev\)"),
    "icnss_already_registered_guard": ("icnss", r"Driver already registered"),
    "icnss_missing_ops_guard": ("icnss", r"if \(!ops->probe \|\| !ops->remove\)"),
    "icnss_register_event_post": ("icnss", r"icnss_driver_event_post\(ICNSS_DRIVER_EVENT_REGISTER_DRIVER"),
    "icnss_event_register_definition": ("icnss", r"static int icnss_driver_event_register_driver"),
    "icnss_event_register_sets_ops": ("icnss", r"penv->ops = data;"),
    "icnss_fw_not_ready_defer": ("icnss", r"FW is not ready yet"),
    "icnss_fw_ready_ind": ("icnss", r"icnss_driver_event_fw_ready_ind"),
    "icnss_fw_ready_sets_bit": ("icnss", r"set_bit\(ICNSS_FW_READY"),
    "icnss_fw_ready_calls_probe": ("icnss", r"ret = icnss_call_driver_probe\(penv\);"),
    "icnss_call_driver_probe": ("icnss", r"static int icnss_call_driver_probe"),
    "icnss_probe_calls_ops": ("icnss", r"ret = (priv|penv)->ops->probe\(&"),
    "icnss_qcwlanstate_status_source": ("icnss", r"current_driver_status = new_status;"),
    "icnss_qcwlanstate_off_marker": ("icnss", r"Modules not initialized just return"),
    "kbuild_pld_snoc_object": ("kbuild", r"PLD_OBJS \+=\s+\$\(PLD_SRC_DIR\)/pld_snoc\.o"),
    "kbuild_pld_snoc_define": ("kbuild", r"cppflags-y \+= -DCONFIG_PLD_SNOC_ICNSS"),
}

FORBIDDEN_ACTIONS = (
    "device command",
    "custom kernel flash or boot image write",
    "partition write or reboot",
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "qcwlanstate or boot_wlan write",
    "esoc0 open or hold",
    "bind/unbind, driver_override, or module load/unload",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v775-manifest", type=Path, default=DEFAULT_V775_MANIFEST)
    parser.add_argument("--v803-manifest", type=Path, default=DEFAULT_V803_MANIFEST)
    parser.add_argument("--v802-manifest", type=Path, default=DEFAULT_V802_MANIFEST)
    parser.add_argument("--v802-dmesg", type=Path, default=DEFAULT_V802_DMESG)
    parser.add_argument("--v802-boot", type=Path, default=DEFAULT_V802_BOOT)
    parser.add_argument("--stock-config", type=Path, default=DEFAULT_STOCK_CONFIG)
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


def line_of(text: str, pattern: str, flags: int = 0) -> int | None:
    regex = re.compile(pattern, flags)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return None


def contains(text: str, pattern: str, flags: int = re.MULTILINE | re.DOTALL) -> bool:
    return re.search(pattern, text, flags) is not None


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
        "size": resolved.stat().st_size if resolved.exists() and resolved.is_file() else None,
    }


def extract_key_value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}=(.*)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def load_sources(source_root: Path) -> dict[str, str]:
    root = repo_path(source_root)
    return {
        "hdd_main": read_text(root / HDD_MAIN),
        "hdd_ops": read_text(root / HDD_OPS),
        "pld_common": read_text(root / PLD_COMMON),
        "pld_snoc": read_text(root / PLD_SNOC),
        "icnss": read_text(root / ICNSS),
        "kbuild": read_text(root / KBUILD),
    }


def analyze_v775(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v775_manifest)
    return {
        "manifest": str(repo_path(args.v775_manifest)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "flash_pause_supported": bool(manifest.get("pass")) and "incompat" in str(manifest.get("decision", "")),
    }


def analyze_v803(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v803_manifest)
    checks = manifest.get("checks") if isinstance(manifest.get("checks"), list) else []
    return {
        "manifest": str(repo_path(args.v803_manifest)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "next_step": manifest.get("next_step", ""),
        "checks": [(check.get("name"), check.get("status")) for check in checks if isinstance(check, dict)],
        "register_boundary_selected": bool(manifest.get("pass"))
        and "pld-register" in str(manifest.get("decision", "")).replace("_", "-"),
    }


def analyze_v802(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v802_manifest)
    dmesg = read_text(args.v802_dmesg)
    boot = read_text(args.v802_boot)
    arm = manifest.get("arm_v802") if isinstance(manifest.get("arm_v802"), dict) else {}
    counts = arm.get("counts") if isinstance(arm.get("counts"), dict) else {}
    failure_patterns = {
        "failed_init_hdd": r"Failed to init HDD",
        "failed_create_ctrl_param": r"Failed to create ctrl param",
        "failed_init_pld": r"Failed to init PLD",
        "failed_register_driver": r"Failed to register driver",
        "pld_global_context_null": r"global context is NULL",
        "pld_driver_already_registered": r"driver already registered",
        "pld_required_callbacks_missing": r"Required callback functions are missing",
        "icnss_driver_already_registered": r"Driver already registered",
        "icnss_device_not_ready": r"Device is not ready",
        "icnss_driver_probe_failed": r"Driver probe failed",
    }
    return {
        "manifest": str(repo_path(args.v802_manifest)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "counts": counts,
        "dmesg_counts": {
            "wlan_loading": count(dmesg, r"wlan: Loading driver"),
            "wlan_driver_loaded": count(dmesg, r"wlan: driver loaded"),
            "modules_not_initialized": count(dmesg, r"Modules not initialized just return"),
            "icnss_qmi": count(dmesg, r"icnss.*qmi|qmi.*icnss"),
            "fw_ready": count(dmesg, r"FW is ready|fw_ready"),
            "wlfw": count(dmesg, r"wlfw"),
            "bdf": count(dmesg, r"\bbdf\b|bdwlan|regdb"),
            "wlan0": count(dmesg, r"\bwlan0\b"),
        },
        "failure_counts": {name: count(dmesg, pattern) for name, pattern in failure_patterns.items()},
        "boot_after": {
            "qcwlanstate": extract_key_value(boot, "wlanboot.after.qcwlanstate.value"),
            "sys_class_wlan_dev": extract_key_value(boot, "wlanboot.after.sys_class_wlan_dev.value"),
            "dev_wlan_exists": extract_key_value(boot, "wlanboot.after.dev_wlan.exists"),
            "wlan0_exists": extract_key_value(boot, "wlanboot.after.sys_class_net_wlan0.exists"),
            "ieee80211_count": extract_key_value(boot, "wlanboot.after.sys_class_ieee80211.count"),
            "proc_devices_qcwlanstate_present": extract_key_value(boot, "wlanboot.after.proc_devices.qcwlanstate_present"),
            "result": extract_key_value(boot, "wlanboot.result"),
        },
    }


def analyze_config(args: argparse.Namespace) -> dict[str, Any]:
    text = read_text(args.stock_config)
    config = parse_kernel_config(text)
    selected = {key: config_state(config, key) for key in CONFIG_KEYS}
    return {
        "path": str(repo_path(args.stock_config)),
        "exists": bool(text),
        "selected": selected,
        "route": {
            "qca_cld_wlan": selected["CONFIG_QCA_CLD_WLAN"] == "y",
            "icnss": selected["CONFIG_ICNSS"] == "y",
            "icnss_qmi": selected["CONFIG_ICNSS_QMI"] == "y",
            "cnss2_disabled": selected["CONFIG_CNSS2"] in {"n", "unset"},
            "pcie_disabled": selected["CONFIG_HIF_PCI"] in {"n", "unset"},
        },
    }


def analyze_source(args: argparse.Namespace) -> dict[str, Any]:
    sources = load_sources(args.source_root)
    anchors = {
        name: {
            "source": source_key,
            "line": line_of(sources.get(source_key, ""), pattern),
            "pattern": pattern,
        }
        for name, (source_key, pattern) in ANCHORS.items()
    }
    hdd_order_lines = [
        anchors["hdd_loading_driver"]["line"],
        anchors["hdd_qcwlanstate_create"]["line"],
        anchors["hdd_pld_init_call"]["line"],
        anchors["hdd_register_driver_call"]["line"],
        anchors["hdd_driver_loaded_marker"]["line"],
    ]
    hdd_order_verified = all(isinstance(item, int) for item in hdd_order_lines) and hdd_order_lines == sorted(hdd_order_lines)
    icnss_text = sources["icnss"]
    pld_common_text = sources["pld_common"]
    kbuild_text = sources["kbuild"]
    return {
        "source_root": str(repo_path(args.source_root)),
        "source_files": {
            HDD_MAIN: path_info(args.source_root / HDD_MAIN),
            HDD_OPS: path_info(args.source_root / HDD_OPS),
            PLD_COMMON: path_info(args.source_root / PLD_COMMON),
            PLD_SNOC: path_info(args.source_root / PLD_SNOC),
            ICNSS: path_info(args.source_root / ICNSS),
            KBUILD: path_info(args.source_root / KBUILD),
        },
        "anchors": anchors,
        "derived": {
            "hdd_order_verified": hdd_order_verified,
            "hdd_callbacks_complete": all(anchors[name]["line"] for name in ("hdd_ops_probe", "hdd_ops_remove", "hdd_ops_suspend", "hdd_ops_resume")),
            "pld_init_sets_global_context": bool(anchors["pld_global_context_set"]["line"]),
            "pld_register_guards_present": all(
                anchors[name]["line"]
                for name in ("pld_context_null_guard", "pld_already_registered_guard", "pld_callback_guard")
            ),
            "pld_snoc_route_present": all(
                anchors[name]["line"]
                for name in ("kbuild_pld_snoc_object", "kbuild_pld_snoc_define", "pld_snoc_to_icnss")
            )
            and contains(kbuild_text, r"ifeq \(\$\(CONFIG_ICNSS\),\s*y\).*?pld_snoc\.o"),
            "icnss_register_guards_present": all(
                anchors[name]["line"]
                for name in ("icnss_penv_pdev_guard", "icnss_already_registered_guard", "icnss_missing_ops_guard")
            ),
            "icnss_register_posts_non_sync_event": contains(
                icnss_text,
                r"icnss_driver_event_post\(ICNSS_DRIVER_EVENT_REGISTER_DRIVER,\s*0,\s*ops\)",
            ),
            "icnss_event_register_defers_until_fw_ready": all(
                anchors[name]["line"]
                for name in ("icnss_event_register_sets_ops", "icnss_fw_not_ready_defer")
            )
            and contains(icnss_text, r"if \(!test_bit\(ICNSS_FW_READY, &penv->state\)\).*?goto out;"),
            "fw_ready_ind_calls_driver_probe": all(
                anchors[name]["line"]
                for name in ("icnss_fw_ready_sets_bit", "icnss_fw_ready_calls_probe", "icnss_call_driver_probe", "icnss_probe_calls_ops")
            ),
            "qcwlanstate_tracks_post_startup_enabled": all(
                anchors[name]["line"]
                for name in ("hdd_start_modules_enabled", "hdd_sysfs_updates_enabled", "icnss_qcwlanstate_status_source")
            ),
            "pld_register_has_no_wait_loop": not contains(pld_common_text, r"wait_for_completion|msleep|ssleep|schedule_timeout"),
        },
    }


def build_checks(command: str,
                 v775: dict[str, Any],
                 v803: dict[str, Any],
                 v802: dict[str, Any],
                 config: dict[str, Any],
                 source: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only classifier; no device command, flash, reboot, Wi-Fi HAL, or connect action",
            "next_step": "run V804 host-only classifier",
        }]
    route = config.get("route") if isinstance(config.get("route"), dict) else {}
    derived = source.get("derived") if isinstance(source.get("derived"), dict) else {}
    counts = v802.get("counts") if isinstance(v802.get("counts"), dict) else {}
    failure_counts = v802.get("failure_counts") if isinstance(v802.get("failure_counts"), dict) else {}
    dmesg_counts = v802.get("dmesg_counts") if isinstance(v802.get("dmesg_counts"), dict) else {}
    boot_after = v802.get("boot_after") if isinstance(v802.get("boot_after"), dict) else {}
    return [
        {
            "name": "custom-kernel-flash-paused",
            "status": "pass" if v775.get("flash_pause_supported") else "finding",
            "detail": {"v775_decision": v775.get("decision"), "v775_pass": v775.get("pass")},
            "next_step": "keep V773/V774-derived images out of live loop until boot incompatibility is solved",
        },
        {
            "name": "v803-boundary-ready",
            "status": "pass" if v803.get("pass") and v803.get("register_boundary_selected") else "blocked",
            "detail": {"decision": v803.get("decision"), "pass": v803.get("pass"), "next_step": v803.get("next_step")},
            "next_step": "rerun V803 if source/evidence boundary is not ready",
        },
        {
            "name": "stock-config-icnss-snoc-route",
            "status": "pass" if route.get("qca_cld_wlan") and route.get("icnss") and route.get("icnss_qmi") and route.get("cnss2_disabled") else "blocked",
            "detail": config.get("selected", {}),
            "next_step": "do not use CNSS2/QCA6390 PCIe route on this stock kernel",
        },
        {
            "name": "pld-register-prerequisites-source-ready",
            "status": "pass"
            if derived.get("hdd_order_verified")
            and derived.get("hdd_callbacks_complete")
            and derived.get("pld_init_sets_global_context")
            and derived.get("pld_snoc_route_present")
            else "blocked",
            "detail": {
                "hdd_order_verified": derived.get("hdd_order_verified"),
                "hdd_callbacks_complete": derived.get("hdd_callbacks_complete"),
                "pld_init_sets_global_context": derived.get("pld_init_sets_global_context"),
                "pld_snoc_route_present": derived.get("pld_snoc_route_present"),
            },
            "next_step": "if blocked, classify PLD context/callback/Kbuild gap before another live replay",
        },
        {
            "name": "icnss-register-is-nonsync-fw-gated",
            "status": "pass"
            if derived.get("icnss_register_guards_present")
            and derived.get("icnss_register_posts_non_sync_event")
            and derived.get("icnss_event_register_defers_until_fw_ready")
            and derived.get("fw_ready_ind_calls_driver_probe")
            else "blocked",
            "detail": {
                "icnss_register_guards_present": derived.get("icnss_register_guards_present"),
                "icnss_register_posts_non_sync_event": derived.get("icnss_register_posts_non_sync_event"),
                "icnss_event_register_defers_until_fw_ready": derived.get("icnss_event_register_defers_until_fw_ready"),
                "fw_ready_ind_calls_driver_probe": derived.get("fw_ready_ind_calls_driver_probe"),
            },
            "next_step": "focus next live gate on ICNSS FW_READY/WLFW service arrival rather than PLD register return",
        },
        {
            "name": "v802-runtime-still-pre-fw-ready",
            "status": "pass"
            if int_value(counts.get("wlan_loading"))
            and boot_after.get("qcwlanstate") == "OFF"
            and boot_after.get("sys_class_wlan_dev")
            and not any(int_value(counts.get(name)) for name in ("icnss_qmi_connected", "fw_ready", "wlfw", "bdf", "wlan0", "wiphy"))
            else "blocked",
            "detail": {
                "counts": counts,
                "dmesg_counts": dmesg_counts,
                "boot_after": boot_after,
            },
            "next_step": "if FW/WLFW/netdev appears, route to driver-ready-to-netdev classifier",
        },
        {
            "name": "explicit-register-failure-logs-absent",
            "status": "pass" if not any(int_value(value) for value in failure_counts.values()) else "finding",
            "detail": failure_counts,
            "next_step": "if finding, route to exact failure-string classifier",
        },
        {
            "name": "qcwlanstate-off-is-polling-signal",
            "status": "pass" if derived.get("qcwlanstate_tracks_post_startup_enabled") and int_value(dmesg_counts.get("modules_not_initialized")) else "finding",
            "detail": {
                "qcwlanstate_tracks_post_startup_enabled": derived.get("qcwlanstate_tracks_post_startup_enabled"),
                "modules_not_initialized_count": dmesg_counts.get("modules_not_initialized"),
            },
            "next_step": "`Modules not initialized` should be treated as qcwlanstate OFF readback, not a standalone PLD registration error",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]], v802: dict[str, Any], source: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v804-pld-icnss-register-probe-prereq-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only V804 classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return "v804-pld-icnss-register-probe-prereq-classifier-blocked", False, "blocked by " + ", ".join(blocked), "clear host evidence blocker"
    derived = source.get("derived") if isinstance(source.get("derived"), dict) else {}
    dmesg_counts = v802.get("dmesg_counts") if isinstance(v802.get("dmesg_counts"), dict) else {}
    if derived.get("icnss_register_posts_non_sync_event") and derived.get("fw_ready_ind_calls_driver_probe") and not int_value(dmesg_counts.get("fw_ready")):
        return (
            "v804-icnss-fw-ready-probe-gate-selected",
            True,
            "PLD/SNOC registration prerequisites are source-ready and ICNSS driver registration posts a non-sync event; V802 qcwlanstate OFF is consistent with missing ICNSS FW_READY/probe/WLFW, not proof of a PLD register block",
            "classify ICNSS FW_READY/WLFW service arrival with stock-kernel observability and no custom-kernel flash",
        )
    return (
        "v804-pld-register-failure-surface-selected",
        True,
        "source/evidence did not prove the non-sync FW_READY gate; next route remains PLD register failure surface",
        "add read-only PLD/ICNSS runtime surface before another replay",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v775 = analyze_v775(args)
    v803 = analyze_v803(args)
    v802 = analyze_v802(args)
    config = analyze_config(args)
    source = analyze_source(args)
    checks = build_checks(args.command, v775, v803, v802, config, source)
    decision, pass_ok, reason, next_step = decide(args.command, checks, v802, source)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v804",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v775_manifest": str(repo_path(args.v775_manifest)),
            "v803_manifest": str(repo_path(args.v803_manifest)),
            "v802_manifest": str(repo_path(args.v802_manifest)),
            "v802_dmesg": str(repo_path(args.v802_dmesg)),
            "v802_boot": str(repo_path(args.v802_boot)),
            "stock_config": str(repo_path(args.stock_config)),
            "source_root": str(repo_path(args.source_root)),
        },
        "v775": v775,
        "v803": v803,
        "v802": v802,
        "config": config,
        "source": source,
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "reboot_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    source = manifest["source"]
    v802 = manifest["v802"]
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    source_rows = [
        [name, data["source"], str(data["line"]), data["pattern"]]
        for name, data in source["anchors"].items()
    ]
    derived_rows = [[key, str(value)] for key, value in source["derived"].items()]
    config_rows = [[key, value] for key, value in manifest["config"]["selected"].items()]
    v802_rows = [
        ["decision", v802.get("decision", "")],
        ["counts", json.dumps(v802.get("counts", {}), sort_keys=True)],
        ["dmesg_counts", json.dumps(v802.get("dmesg_counts", {}), sort_keys=True)],
        ["failure_counts", json.dumps(v802.get("failure_counts", {}), sort_keys=True)],
        ["boot_after", json.dumps(v802.get("boot_after", {}), sort_keys=True)],
    ]
    return "\n".join([
        "# V804 PLD/ICNSS Register/Probe Prerequisite Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- custom_kernel_flash_executed: `{manifest['custom_kernel_flash_executed']}`",
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
        "## Stock Config",
        "",
        markdown_table(["option", "value"], config_rows),
        "",
        "## Source Derived Facts",
        "",
        markdown_table(["fact", "value"], derived_rows),
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
    print(f"custom_kernel_flash_executed: {manifest['custom_kernel_flash_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"credential_use_executed: {manifest['credential_use_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
