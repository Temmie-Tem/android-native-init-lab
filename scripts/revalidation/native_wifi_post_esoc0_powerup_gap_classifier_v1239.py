#!/usr/bin/env python3
"""V1239 host-only classifier for the post-/dev/subsys_esoc0 powerup gap."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1239-post-esoc0-powerup-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1239-post-esoc0-powerup-gap-classifier.txt")
V896_MANIFEST = Path("tmp/wifi/v896-android-mdm-helper-image-contract/manifest.json")
V1160_MANIFEST = Path("tmp/wifi/v1160-pm-esoc-trigger-reconcile/manifest.json")
V1238_MANIFEST = Path("tmp/wifi/v1238-late-per-proxy-only-live/manifest.json")
V1238_OBSERVER = Path("tmp/wifi/v1238-late-per-proxy-only-live/host/pm-server-wchan-tracefs-observer.txt")
FORBIDDEN_OUTPUT_ENV_KEYS = ("A90_WIFI_SSID", "A90_WIFI_PSK")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def read_text(path: Path, limit: int = 4 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].decode("utf-8", errors="replace")


def bool_path(mapping: dict[str, Any], *keys: str) -> bool:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return False
        current = current.get(key)
    return bool(current)


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def count_lines(text: str, *needles: str) -> int:
    count = 0
    for line in text.splitlines():
        if all(needle in line for needle in needles):
            count += 1
    return count


def find_first_time(lines: list[str], pattern: str) -> float | None:
    regex = re.compile(pattern, re.IGNORECASE)
    ts = re.compile(r"^\[\s*([0-9]+\.[0-9]+)\]")
    for line in lines:
        if not regex.search(line):
            continue
        match = ts.search(line)
        if match:
            return float(match.group(1))
    return None


def analyze() -> dict[str, Any]:
    v896 = load_json(V896_MANIFEST)
    v1160 = load_json(V1160_MANIFEST)
    v1238 = load_json(V1238_MANIFEST)
    v1238_text = read_text(V1238_OBSERVER)

    v852 = v896.get("v852") or {}
    v853_flags = v896.get("v853_actor_flags") or {}
    v1160_android = ((v1160.get("analysis") or {}).get("android_v1159") or {})
    v1160_times = v1160_android.get("times") or {}
    v1238_pm = v1238.get("pm_service_trigger_observer") or {}
    v1238_late = v1238.get("late_per_proxy") or {}
    v1238_boundary = v1238.get("post_esoc_boundary") or {}
    selected_lines = [str(item) for item in v852.get("selected_dmesg_lines") or []]
    selected_text = "\n".join(selected_lines)

    android = {
        "v896_pass": bool(v896.get("pass")),
        "mdm3_online": v852.get("mdm3_state") == "ONLINE",
        "gpio142_irq_count": int_value(((v852.get("irq_mdm_status") or {}).get("count_total")), 0),
        "wlan0_present": bool_path(v852, "timeline", "wlan0", "present") or bool_path(v852, "dmesg_hints", "has_wlan0"),
        "wlfw_present": bool_path(v852, "dmesg_hints", "has_wlfw"),
        "bdf_present": bool_path(v852, "dmesg_hints", "has_bdf"),
        "pcie_rc1_lines": count_lines(selected_text, "PCIe", "RC1"),
        "pcie_l0_lines": count_lines(selected_text, "LTSSM_L0"),
        "sysmon_esoc0_lines": count_lines(selected_text, "sysmon-qmi", "esoc0"),
        "service_notifier_wlan_pd_lines": count_lines(selected_text, "service-notifier", "wlan_pd"),
        "ks_mhi_pipe": bool(v853_flags.get("has_ks_mhi_pipe")),
        "per_mgr_subsys_esoc0_fd": bool(v853_flags.get("has_per_mgr_subsys_esoc0_fd")),
        "pm_service_esoc0_time": v1160_times.get("pm_service_esoc0_get"),
        "pcie_reset_time": find_first_time(selected_lines, r"Assert the reset of endpoint of RC1"),
        "pcie_l0_time": find_first_time(selected_lines, r"LTSSM_L0|Current GEN2"),
        "icnss_qmi_time": v1160_times.get("icnss_qmi_connected"),
        "bdf_regdb_time": v1160_times.get("bdf_regdb"),
        "fw_ready_time": v1160_times.get("fw_ready"),
        "wlan0_time": v1160_times.get("wlan0"),
    }
    native = {
        "v1238_pass": bool(v1238.get("pass")),
        "late_per_proxy_started": int_value(v1238_late.get("started"), 0) > 0,
        "direct_trigger_present": bool(v1238_pm.get("direct_subsys_trigger_present")),
        "post_wait_observer_present": bool(v1238_pm.get("post_wait_observer_present")),
        "pm_service_actor_esoc0_attempt": bool(v1238_pm.get("pm_service_actor_esoc0_attempt")),
        "pm_service_binder_mdm_subsys_powerup_lines": count_lines(v1238_text, "Binder:", "mdm_subsys_powerup"),
        "pm_service_binder_subsys_esoc0_path_lines": count_lines(v1238_text, "path.value=/dev/subsys_esoc0"),
        "mdm3_states": v1238_boundary.get("mdm3_state_transitions") or [],
        "wlan0_seen": bool(v1238_boundary.get("wlan0_seen")),
        "wlfw_count": int_value(v1238_boundary.get("max_dmesg_wlfw_count"), 0),
        "esoc_open_count": int_value(v1238_boundary.get("max_dmesg_esoc_open_count"), 0),
        "modem_down_count": int_value(v1238_boundary.get("max_dmesg_modem_down_count"), 0),
        "all_postflight_safe": int_value(v1238_pm.get("all_postflight_safe"), -1),
        "result": v1238.get("decision", ""),
    }

    checks = [
        {
            "name": "android-positive-reference",
            "status": "pass" if all([android["v896_pass"], android["mdm3_online"], android["wlan0_present"], android["wlfw_present"], android["bdf_present"]]) else "blocked",
            "detail": "Android reference reaches mdm3 ONLINE, WLFW/BDF, and wlan0",
        },
        {
            "name": "android-post-esoc0-powerup-chain",
            "status": "pass" if android["gpio142_irq_count"] > 0 and android["pcie_rc1_lines"] > 0 and android["sysmon_esoc0_lines"] > 0 else "blocked",
            "detail": f"gpio142={android['gpio142_irq_count']} pcie_rc1_lines={android['pcie_rc1_lines']} sysmon_esoc0={android['sysmon_esoc0_lines']}",
        },
        {
            "name": "native-reaches-pm-service-esoc0",
            "status": "pass" if native["v1238_pass"] and native["late_per_proxy_started"] and native["pm_service_actor_esoc0_attempt"] else "blocked",
            "detail": f"late_started={native['late_per_proxy_started']} actor_esoc0={native['pm_service_actor_esoc0_attempt']}",
        },
        {
            "name": "native-no-lower-publication",
            "status": "pass" if not native["wlan0_seen"] and native["wlfw_count"] == 0 and "OFFLINING" in native["mdm3_states"] else "blocked",
            "detail": f"mdm3={native['mdm3_states']} wlfw={native['wlfw_count']} wlan0={native['wlan0_seen']}",
        },
        {
            "name": "guardrails-clean",
            "status": "pass" if not any(bool(v1238.get(key)) for key in ("wifi_hal_start_executed", "scan_connect_executed", "credential_use_executed", "dhcp_route_executed", "external_ping_executed", "flash_executed", "partition_write_executed")) else "blocked",
            "detail": "V1238 did not run Wi-Fi HAL/connect/network/flash actions",
        },
    ]
    pass_ok = all(check["status"] == "pass" for check in checks)
    if pass_ok:
        decision = "v1239-gap-is-after-pm-service-esoc0-before-gpio142-pcie-wlfw"
        reason = "native now reaches the same pm-service /dev/subsys_esoc0 powerup entry as Android, but does not receive the downstream GPIO142/PCIe/SSCTL/WLFW response"
        next_step = "design a bounded read-only/cleanup-safe classifier for the SDX50M response inputs around mdm_subsys_powerup; do not start Wi-Fi HAL/connect yet"
    else:
        decision = "v1239-input-evidence-incomplete"
        reason = "one or more Android/native comparison inputs are missing or contradictory"
        next_step = "refresh Android/V1238 evidence before another live gate"
    return {
        "cycle": "v1239",
        "generated_at": now_iso(),
        "inputs": {
            "v896": str(repo_path(V896_MANIFEST)),
            "v1160": str(repo_path(V1160_MANIFEST)),
            "v1238": str(repo_path(V1238_MANIFEST)),
        },
        "host": collect_host_metadata(),
        "android": android,
        "native": native,
        "checks": checks,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
        "partition_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    android = manifest["android"]
    native = manifest["native"]
    return "\n".join([
        "# V1239 Post-esoc0 Powerup Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail"], [[c["name"], c["status"], c["detail"]] for c in manifest["checks"]]),
        "",
        "## Android Reference",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in android.items()]),
        "",
        "## Native V1238",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in native.items()]),
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write occurred.",
        "",
    ])


def check_forbidden_output(manifest: dict[str, Any]) -> list[str]:
    text = json.dumps(manifest, sort_keys=True) + "\n" + render_summary(manifest)
    leaks: list[str] = []
    for key in FORBIDDEN_OUTPUT_ENV_KEYS:
        value = __import__("os").environ.get(key, "")
        if value and value in text:
            leaks.append(key)
    return leaks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    store = EvidenceStore(repo_path(args.out_dir))
    manifest = analyze()
    manifest["command"] = args.command
    if args.command == "plan":
        manifest["decision"] = "v1239-post-esoc0-powerup-gap-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only host classifier; no device command or mutation"
        manifest["next_step"] = "run V1239 host-only classifier"
    leaks = check_forbidden_output(manifest)
    manifest["forbidden_output_env_hits"] = leaks
    if leaks:
        manifest["decision"] = "v1239-forbidden-output-hit"
        manifest["pass"] = False
        manifest["reason"] = "forbidden environment-backed output string detected"
        manifest["next_step"] = "remove sensitive output before continuing"
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"next:     {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
