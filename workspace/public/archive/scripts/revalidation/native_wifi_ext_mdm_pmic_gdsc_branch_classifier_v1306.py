#!/usr/bin/env python3
"""V1306 host-only ext-mdm PMIC/GDSC branch classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1306-ext-mdm-pmic-gdsc-branch-classifier")
DEFAULT_V1305_MANIFEST = Path("tmp/wifi/v1305-ap2mdm-transition-window-classifier/manifest.json")
DEFAULT_V1244_REPORT = Path("docs/reports/NATIVE_INIT_V1244_ANDROID_POWER_SURFACE_CLASSIFIER_2026-05-31.md")
DEFAULT_MDM3_RESEARCH = Path("docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_ESOC_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1306-ext-mdm-pmic-gdsc-branch-classifier.txt")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1305-manifest", type=Path, default=DEFAULT_V1305_MANIFEST)
    parser.add_argument("--v1244-report", type=Path, default=DEFAULT_V1244_REPORT)
    parser.add_argument("--mdm3-research", type=Path, default=DEFAULT_MDM3_RESEARCH)
    parser.add_argument("--esoc-research", type=Path, default=DEFAULT_ESOC_RESEARCH)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    real_path = repo_path(path)
    if not real_path.exists():
        return ""
    return real_path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    real_path = repo_path(path)
    if not real_path.exists():
        return {}
    try:
        data = json.loads(real_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if value:
        return [str(value)]
    return []


def extract_native(v1305: dict[str, Any]) -> dict[str, Any]:
    window = ((v1305.get("analysis") or {}).get("window") or {})
    pmic_values = as_list(window.get("pmic_soft_reset_values"))
    pcie1_values = as_list(window.get("pcie1_gdsc_values"))
    pcie0_values = as_list(window.get("pcie0_gdsc_values"))
    return {
        "v1305_decision": v1305.get("decision", ""),
        "v1305_pass": bool(v1305.get("pass")),
        "powerup_window_ms": int(window.get("powerup_window_ms") or 0),
        "powerup_sample_count": int(window.get("powerup_sample_count") or 0),
        "gpio135_high_seen": bool(window.get("gpio135_high_seen")),
        "gpio142_high_seen": bool(window.get("gpio142_high_seen")),
        "mdm_status_count_max": int(window.get("mdm_status_count_max") or 0),
        "mhi_bus_count_max": int(window.get("mhi_bus_count_max") or 0),
        "mhi_pipe_seen": bool(window.get("mhi_pipe_seen")),
        "ks_seen": bool(window.get("ks_seen")),
        "wlan0_seen": bool(window.get("wlan0_seen")),
        "pmic_soft_reset_values": pmic_values,
        "pcie1_gdsc_values": pcie1_values,
        "pcie0_gdsc_values": pcie0_values,
        "pmic_soft_reset_unclaimed": any("MUX UNCLAIMED" in value for value in pmic_values),
        "pcie1_gdsc_0mv": any("pcie_1_gdsc" in value and "0mV" in value for value in pcie1_values),
        "pcie0_gdsc_0mv": any("pcie_0_gdsc" in value and "0mV" in value for value in pcie0_values),
    }


def extract_reference(v1244_report: str, mdm3_research: str, esoc_research: str) -> dict[str, Any]:
    return {
        "android_pmic_configured": "gpio9 : out normal" in v1244_report,
        "android_pcie_rc1_positive": "PCIe RC1 link initialized" in v1244_report,
        "android_wlan_positive": all(token in v1244_report for token in ("WLAN-PD", "WLAN FW is ready", "wlan0")),
        "native_prior_pmic_unclaimed": "MUX UNCLAIMED" in v1244_report,
        "native_prior_gdsc_0mv": "`pcie_1_gdsc` and `pcie_0_gdsc` remain `0mV`" in v1244_report,
        "contract_first_power_on_deasserts_pmic": "mdm_toggle_soft_reset(mdm, false)" in mdm3_research,
        "contract_first_power_on_asserts_ap2mdm": "GPIO 135 → HIGH" in mdm3_research,
        "contract_esoc_power_on_calls_first_power_on": "mdm_do_first_power_on" in esoc_research and "ESOC_PWR_ON" in esoc_research,
    }


def decide(command: str, native: dict[str, Any], reference: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v1306-ext-mdm-pmic-gdsc-branch-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V1306 host-only branch classifier",
        )
    if not native["v1305_pass"]:
        return (
            "v1306-input-v1305-not-pass",
            False,
            "V1305 pass evidence is missing",
            "rerun or restore V1305 before branch classification",
        )
    if not (reference["android_pmic_configured"] and reference["android_pcie_rc1_positive"]):
        return (
            "v1306-reference-incomplete",
            False,
            "Android PMIC/PCIe positive reference is incomplete",
            "refresh host-only Android/native power surface evidence",
        )
    if (
        native["pmic_soft_reset_unclaimed"]
        and native["pcie1_gdsc_0mv"]
        and native["pcie0_gdsc_0mv"]
        and native["powerup_window_ms"] >= 1000
        and not native["gpio135_high_seen"]
        and native["mdm_status_count_max"] == 0
        and native["mhi_bus_count_max"] == 0
    ):
        return (
            "v1306-pmic-gdsc-prereq-gap-classified",
            True,
            "During the extended native mdm_subsys_powerup window, PM8150L soft-reset remains MUX UNCLAIMED and PCIe GDSCs remain 0mV while Android-positive evidence has configured PMIC GPIO9 and PCIe RC1 progress; the AP2MDM gap is therefore aligned with an ext-mdm PMIC/GDSC prerequisite branch, not upper PM/CNSS delivery",
            "V1307 should add source/build-only support for a focused no-write PMIC/GDSC transition sampler or classify exact safe init prerequisites; do not write PMIC/GPIO or retry Wi-Fi HAL yet",
        )
    return (
        "v1306-pmic-gdsc-branch-inconclusive",
        True,
        "V1305 proves the AP2MDM gap, but current PMIC/GDSC evidence does not isolate the lower prerequisite branch",
        "add focused read-only PMIC/GDSC sampling before any mutating lower action",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    native = manifest["analysis"]["native"]
    reference = manifest["analysis"]["reference"]
    native_rows = [
        ["V1305 decision", native["v1305_decision"]],
        ["powerup window/sample count", f"{native['powerup_window_ms']}ms / {native['powerup_sample_count']}"],
        ["GPIO135/GPIO142 high seen", f"{native['gpio135_high_seen']} / {native['gpio142_high_seen']}"],
        ["MDM status / MHI max", f"{native['mdm_status_count_max']} / {native['mhi_bus_count_max']}"],
        ["MHI pipe / ks / wlan0", f"{native['mhi_pipe_seen']} / {native['ks_seen']} / {native['wlan0_seen']}"],
        ["PMIC soft-reset values", "; ".join(native["pmic_soft_reset_values"])],
        ["PCIe1 GDSC values", "; ".join(native["pcie1_gdsc_values"])],
        ["PCIe0 GDSC values", "; ".join(native["pcie0_gdsc_values"])],
    ]
    reference_rows = [
        ["Android PMIC GPIO9 configured", reference["android_pmic_configured"]],
        ["Android PCIe RC1 positive", reference["android_pcie_rc1_positive"]],
        ["Android WLAN positive", reference["android_wlan_positive"]],
        ["Prior native PMIC unclaimed", reference["native_prior_pmic_unclaimed"]],
        ["Prior native GDSC 0mV", reference["native_prior_gdsc_0mv"]],
        ["Contract deasserts PMIC first", reference["contract_first_power_on_deasserts_pmic"]],
        ["Contract asserts AP2MDM", reference["contract_first_power_on_asserts_ap2mdm"]],
        ["Contract maps ESOC_PWR_ON to first power-on", reference["contract_esoc_power_on_calls_first_power_on"]],
    ]
    return "\n".join([
        "# V1306 ext-mdm PMIC/GDSC Branch Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Native",
        "",
        markdown_table(["field", "value"], native_rows),
        "",
        "## Reference",
        "",
        markdown_table(["field", "value"], reference_rows),
        "",
        "## Safety",
        "",
        "- host-only classifier; no bridge/device command",
        "- no PMIC write, GPIO request/hold, direct eSoC ioctl, PM/CNSS actor start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    native = extract_native(load_json(args.v1305_manifest))
    reference = extract_reference(
        read_text(args.v1244_report),
        read_text(args.mdm3_research),
        read_text(args.esoc_research),
    )
    decision, passed, reason, next_step = decide(args.command, native, reference)
    manifest = {
        "cycle": "v1306",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "inputs": {
            "v1305_manifest": str(repo_path(args.v1305_manifest)),
            "v1244_report": str(repo_path(args.v1244_report)),
            "mdm3_research": str(repo_path(args.mdm3_research)),
            "esoc_research": str(repo_path(args.esoc_research)),
        },
        "analysis": {
            "native": native,
            "reference": reference,
        },
        "device_commands_executed": False,
        "live_actor_started": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "direct_esoc_ioctl_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_or_partition_write_executed": False,
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
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
