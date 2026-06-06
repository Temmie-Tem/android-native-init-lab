#!/usr/bin/env python3
"""V1280 host-only classifier for the post-V1279 SDX50M response gap."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1280-v1279-response-gap-classifier")
DEFAULT_V1279 = Path("tmp/wifi/v1279-tlmm-range-sampler-live/manifest.json")
ANDROID_V1000_REPORT = Path("docs/reports/NATIVE_INIT_V1000_ANDROID_ESOC_GPIO_RECAPTURE_HANDOFF_LIVE_2026-05-26.md")
ANDROID_V968_REPORT = Path("docs/reports/NATIVE_INIT_V968_ANDROID_DMESG_ESOC_GPIO_TIMING_2026-05-26.md")
V1239_REPORT = Path("docs/reports/NATIVE_INIT_V1239_POST_ESOC0_POWERUP_GAP_CLASSIFIER_2026-05-31.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1280-v1279-response-gap-classifier.txt")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1279-manifest", type=Path, default=DEFAULT_V1279)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    full = repo_path(path)
    if not full.exists():
        return {}
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def read_text(path: Path) -> str:
    full = repo_path(path)
    return full.read_text(encoding="utf-8", errors="replace") if full.exists() else ""


def native_summary(v1279: dict[str, Any]) -> dict[str, Any]:
    sampler = v1279.get("response_sampler") or {}
    pm = v1279.get("pm_service_trigger_observer") or {}
    debugfs = v1279.get("debugfs_observer") or {}
    return {
        "decision": v1279.get("decision", ""),
        "pass": bool(v1279.get("pass")),
        "pm_esoc0_attempt": bool(pm.get("pm_service_actor_esoc0_attempt")),
        "late_per_proxy_started": pm.get("late_per_proxy_started"),
        "tlmm_range_visible": bool(
            sampler.get("tlmm_gpio135_debugfs_range_block_seen") and
            sampler.get("tlmm_gpio142_debugfs_range_block_seen")
        ),
        "tlmm_range_windows": sorted(set(
            (sampler.get("tlmm_gpio135_debugfs_range_windows") or []) +
            (sampler.get("tlmm_gpio142_debugfs_range_windows") or [])
        )),
        "exact_line_values_visible": bool(
            sampler.get("tlmm_gpio135_debugfs_seen") or
            sampler.get("tlmm_gpio142_debugfs_seen")
        ),
        "pinmux_visible": bool(sampler.get("pin135_seen") and sampler.get("pin142_seen")),
        "gpio142_irq_progress": int(sampler.get("max_mdm_status_count_total") or 0) > 0,
        "pci_progress": int(sampler.get("max_pci_dev_count") or 0) > 0,
        "mhi_progress": int(sampler.get("max_mhi_bus_count") or 0) > 0 or bool(sampler.get("mhi_pipe_seen")),
        "wlan0_seen": bool(sampler.get("wlan0_seen")),
        "debugfs_cleanup_ok": debugfs.get("mounted_after") is False,
        "safety_zero_action": bool(sampler.get("gpiochip_lineinfo_zero_action_ok")),
        "wifi_bringup_executed": bool(v1279.get("wifi_bringup_executed")),
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    v1279 = load_json(args.v1279_manifest)
    v1000 = read_text(ANDROID_V1000_REPORT)
    v968 = read_text(ANDROID_V968_REPORT)
    v1239 = read_text(V1239_REPORT)
    native = native_summary(v1279)
    android = {
        "v1000_gpio135_value": "gpio135 : out 0 16mA no pull" in v1000,
        "v1000_gpio142_value": "gpio142 : in 0 8mA no pull" in v1000,
        "v1000_wlfw_start": "cnss-daemon wlfw_start" in v1000,
        "v1000_icnss_qmi": "ICNSS QMI connected" in v1000,
        "v968_wlan0_event": "`wlan0` event" in v968,
        "v968_fw_ready": "WLAN FW ready" in v968,
        "v968_gpio_transition_unknown": "GPIO level-transition timing is not directly visible" in v968,
        "v1239_android_pcie_chain": "PCIe RC1" in v1239 and "RC1 reset/L0 present" in v1239,
        "v1239_gap_after_pm_esoc0": "after `pm-service` enters" in v1239,
    }
    return {
        "v1279_manifest": str(repo_path(args.v1279_manifest)),
        "native": native,
        "android": android,
        "source_reports": {
            "v1000": str(repo_path(ANDROID_V1000_REPORT)),
            "v968": str(repo_path(ANDROID_V968_REPORT)),
            "v1239": str(repo_path(V1239_REPORT)),
        },
    }


def checks(command: str, analysis: dict[str, Any]) -> list[dict[str, str]]:
    native = analysis["native"]
    android = analysis["android"]
    rows = [
        {
            "name": "v1279-input",
            "status": "pass" if native["decision"].startswith("v1279-") and native["pass"] else "blocked",
            "detail": f"decision={native['decision']} pass={native['pass']}",
            "next_step": "rerun V1279 before classifying the response gap",
        },
        {
            "name": "native-pm-esoc0-reached",
            "status": "pass" if native["pm_esoc0_attempt"] and native["late_per_proxy_started"] == 1 else "blocked",
            "detail": f"pm_esoc0_attempt={native['pm_esoc0_attempt']} late_per_proxy_started={native['late_per_proxy_started']}",
            "next_step": "repair PM-service trigger path before lower response classification",
        },
        {
            "name": "native-tlmm-range-visible",
            "status": "pass" if native["tlmm_range_visible"] and native["pinmux_visible"] else "blocked",
            "detail": f"range_visible={native['tlmm_range_visible']} windows={native['tlmm_range_windows']} pinmux={native['pinmux_visible']}",
            "next_step": "repair TLMM observer before deciding the next gate",
        },
        {
            "name": "native-no-lower-response",
            "status": "pass" if not any([native["gpio142_irq_progress"], native["pci_progress"], native["mhi_progress"], native["wlan0_seen"]]) else "progress",
            "detail": (
                f"gpio142={native['gpio142_irq_progress']} pci={native['pci_progress']} "
                f"mhi={native['mhi_progress']} wlan0={native['wlan0_seen']}"
            ),
            "next_step": "if progress appeared, preserve evidence before any new gate",
        },
        {
            "name": "android-positive-reference",
            "status": "pass" if android["v1000_wlfw_start"] and android["v1000_icnss_qmi"] and android["v968_fw_ready"] and android["v968_wlan0_event"] else "blocked",
            "detail": json.dumps({k: android[k] for k in sorted(android) if k.startswith("v1000_") or k.startswith("v968_")}, sort_keys=True),
            "next_step": "refresh Android positive evidence if unavailable",
        },
        {
            "name": "line-level-not-next-gate",
            "status": "pass" if android["v968_gpio_transition_unknown"] and not native["exact_line_values_visible"] else "warn",
            "detail": (
                f"native_exact_lines={native['exact_line_values_visible']} "
                f"android_transition_unknown={android['v968_gpio_transition_unknown']}"
            ),
            "next_step": "do not use line-level values as a hard precondition; only collect early Android timing if PCIe route remains insufficient",
        },
        {
            "name": "pcie-response-gap-selected",
            "status": "pass" if android["v1239_android_pcie_chain"] and android["v1239_gap_after_pm_esoc0"] and not native["pci_progress"] else "warn",
            "detail": f"android_pcie_chain={android['v1239_android_pcie_chain']} native_pci_progress={native['pci_progress']}",
            "next_step": "build V1281 read-only PCIe/GDSC/dmesg response sampler support",
        },
        {
            "name": "guardrails",
            "status": "pass" if command == "plan" or (native["debugfs_cleanup_ok"] and native["safety_zero_action"] and not native["wifi_bringup_executed"]) else "blocked",
            "detail": f"debugfs_cleanup_ok={native['debugfs_cleanup_ok']} zero_action={native['safety_zero_action']} wifi_bringup={native['wifi_bringup_executed']}",
            "next_step": "fix cleanup/safety before any further live gate",
        },
    ]
    return rows


def decide(command: str, rows: list[dict[str, str]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return ("v1280-response-gap-classifier-plan-ready", True, "plan-only", "run V1280 host-only classifier")
    blocked = [row["name"] for row in rows if row["status"] == "blocked"]
    if blocked:
        return ("v1280-response-gap-classifier-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before selecting next live gate")
    return (
        "v1280-pcie-gdsc-response-sampler-selected",
        True,
        "V1279 closed TLMM range visibility; remaining gap is downstream PCIe/GDSC/RC1 response after PM-service esoc0 entry",
        "V1281 should add/read a bounded PCIe/GDSC/dmesg response sampler before any Wi-Fi HAL/connect attempt",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[row["name"], row["status"], row["detail"], row["next_step"]] for row in manifest["checks"]]
    native = manifest["analysis"]["native"]
    android = manifest["analysis"]["android"]
    return "\n".join([
        "# V1280 V1279 Response Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], rows),
        "",
        "## Native Summary",
        "",
        markdown_table(["field", "value"], [[key, native[key]] for key in sorted(native)]),
        "",
        "## Android Reference Summary",
        "",
        markdown_table(["field", "value"], [[key, android[key]] for key in sorted(android)]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = analyze(args)
    rows = checks(args.command, analysis)
    decision, passed, reason, next_step = decide(args.command, rows)
    manifest = {
        "cycle": "v1280",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "analysis": analysis,
        "checks": rows,
        "device_commands_executed": False,
        "deploy_executed": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "esoc_ioctl_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
        "partition_write_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
