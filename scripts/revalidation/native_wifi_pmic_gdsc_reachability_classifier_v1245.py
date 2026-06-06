#!/usr/bin/env python3
"""V1245 host-only PMIC/GDSC reachability classifier.

This classifier ties three already-captured facts together:

* V918 proves the native path can enter the proprietary SDX50M soft-reset stack.
* V1243 proves the current late per_proxy path reaches /dev/subsys_esoc0 but
  leaves PM8150L soft-reset and PCIe GDSC observer outputs unchanged.
* V1244 proves Android-positive boot does claim the PM8150L soft-reset surface
  and reaches PCIe RC1/WLAN-PD/ICNSS/FW-ready/wlan0.

No device command is executed here.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, workspace_private_input_path, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1245-pmic-gdsc-reachability-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1245-pmic-gdsc-reachability-classifier.txt")
DEFAULT_V918_REPORT = Path("docs/reports/NATIVE_INIT_V918_MDM_HELPER_SUBSYS_TRIGGER_WAIT_LIVE_2026-05-26.md")
DEFAULT_V1243_MANIFEST = Path("tmp/wifi/v1243-sdx50m-power-prereq-response-live/manifest.json")
DEFAULT_V1244_MANIFEST = Path("tmp/wifi/v1244-android-power-surface-classifier/manifest.json")
DEFAULT_DTS = workspace_private_input_path(
    "kernel_source",
    "SM-A908N_KOR_12_Opensource",
    "Kernel",
    "arch",
    "arm64",
    "boot",
    "dts",
    "samsung",
    "renovation",
    "sm8150-sec-r3q-kor-overlay-r00.dts",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v918-report", type=Path, default=DEFAULT_V918_REPORT)
    parser.add_argument("--v1243-manifest", type=Path, default=DEFAULT_V1243_MANIFEST)
    parser.add_argument("--v1244-manifest", type=Path, default=DEFAULT_V1244_MANIFEST)
    parser.add_argument("--dts", type=Path, default=DEFAULT_DTS)
    parser.add_argument("command", nargs="?", choices=("run",), default="run")
    return parser.parse_args()


def read_text(path: Path, limit: int = 4 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def sample_values(samples: list[dict[str, Any]], key: str) -> list[Any]:
    values: list[Any] = []
    for sample in samples:
        value = sample.get(key)
        if value not in values:
            values.append(value)
    return values


def first_line(text: str, *needles: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if all(needle in line for needle in needles):
            return line
    return ""


def contains_all(text: str, *needles: str) -> bool:
    return all(needle in text for needle in needles)


def parse_v1243(manifest: dict[str, Any]) -> dict[str, Any]:
    sampler = manifest.get("response_sampler") or {}
    samples = sampler.get("samples") or []
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "pm_service_actor_esoc0_attempt": bool((manifest.get("pm_service_trigger_observer") or {}).get("pm_service_actor_esoc0_attempt")),
        "sample_count": len(samples),
        "pmic_soft_reset_line_values": sample_values(samples, "pmic_soft_reset_line"),
        "pcie1_gdsc_line_values": sample_values(samples, "pcie1_gdsc_line"),
        "pcie0_gdsc_line_values": sample_values(samples, "pcie0_gdsc_line"),
        "mdm_status_count_values": sample_values(samples, "mdm_status_count_total"),
        "pci_dev_count_values": sample_values(samples, "pci_dev_count"),
        "mhi_bus_count_values": sample_values(samples, "mhi_bus_count"),
        "wlan0_exists_values": sample_values(samples, "wlan0_exists"),
    }


def parse_v1244(manifest: dict[str, Any]) -> dict[str, Any]:
    android = manifest.get("android") or {}
    native = manifest.get("native") or {}
    timeline = android.get("timeline") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "android_pmic_soft_reset": android.get("pm8150l_gpio9_line", ""),
        "android_pcie_rc1": android.get("pcie_rc1_report_line", ""),
        "android_chain_present": all((timeline.get(name) or {}).get("present") for name in (
            "subsys_esoc0_get",
            "wlfw_start",
            "wlan_pd",
            "icnss_qmi",
            "fw_ready",
            "wlan0",
        )),
        "native_pmic_soft_reset": native.get("pmic_soft_reset_line_values", []),
        "native_pcie1_gdsc": native.get("pcie1_gdsc_line_values", []),
        "native_pcie0_gdsc": native.get("pcie0_gdsc_line_values", []),
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    v918_report = read_text(args.v918_report)
    v1243_manifest = load_json(args.v1243_manifest)
    v1244_manifest = load_json(args.v1244_manifest)
    dts = read_text(args.dts)

    v918 = {
        "report_present": bool(v918_report),
        "decision_line": first_line(v918_report, "wait-gated trigger live gate"),
        "soft_reset_location_line": first_line(v918_report, "Kernel wait location:", "sdx50m_toggle_soft_reset"),
        "stack_line": first_line(v918_report, "Kernel stack includes"),
        "reaches_soft_reset_stack": contains_all(
            v918_report,
            "sdx50m_toggle_soft_reset",
            "mdm4x_do_first_power_on",
            "mdm_cmd_exe",
            "mdm_subsys_powerup",
            "__subsystem_get",
            "subsys_device_open",
        ),
        "cleanup_recovered": contains_all(v918_report, "Cleanup reboot", "fail=0"),
    }
    v1243 = parse_v1243(v1243_manifest)
    v1244 = parse_v1244(v1244_manifest)
    dts_contract = {
        "dts_present": bool(dts),
        "compatible": first_line(dts, 'compatible = "qcom,ext-sdx50m"'),
        "ap2mdm_soft_reset_gpio": first_line(dts, "qcom,ap2mdm-soft-reset-gpio"),
        "ap2mdm_status_gpio": first_line(dts, "qcom,ap2mdm-status-gpio"),
        "mdm2ap_status_gpio": first_line(dts, "qcom,mdm2ap-status-gpio"),
    }

    native_pmic_unclaimed = any("MUX UNCLAIMED" in str(value) for value in v1243["pmic_soft_reset_line_values"])
    native_gdsc_zero = all(
        "0mV" in str(value)
        for value in v1243["pcie1_gdsc_line_values"] + v1243["pcie0_gdsc_line_values"]
        if value
    )
    native_no_response = (
        v1243["pm_service_actor_esoc0_attempt"]
        and v1243["sample_count"] > 0
        and v1243["mdm_status_count_values"] == [0]
        and v1243["pci_dev_count_values"] == [0]
        and v1243["mhi_bus_count_values"] == [0]
        and v1243["wlan0_exists_values"] == [0]
    )
    android_positive_power = (
        v1244["pass"]
        and "out" in v1244["android_pmic_soft_reset"]
        and "PCIe RC1" in v1244["android_pcie_rc1"]
        and v1244["android_chain_present"]
    )

    checks = [
        {
            "name": "native-soft-reset-stack-reached",
            "status": "pass" if v918["reaches_soft_reset_stack"] else "blocked",
            "detail": v918["stack_line"] or "missing V918 soft-reset stack line",
        },
        {
            "name": "native-current-esoc0-attempt",
            "status": "pass" if v1243["pm_service_actor_esoc0_attempt"] else "blocked",
            "detail": v1243["decision"],
        },
        {
            "name": "native-pmic-soft-reset-not-applied",
            "status": "pass" if native_pmic_unclaimed else "blocked",
            "detail": "; ".join(str(value) for value in v1243["pmic_soft_reset_line_values"]),
        },
        {
            "name": "native-pcie-gdsc-not-enabled",
            "status": "pass" if native_gdsc_zero else "blocked",
            "detail": "; ".join(str(value) for value in v1243["pcie1_gdsc_line_values"] + v1243["pcie0_gdsc_line_values"]),
        },
        {
            "name": "native-no-downstream-response",
            "status": "pass" if native_no_response else "blocked",
            "detail": f"gpio142={v1243['mdm_status_count_values']} pci={v1243['pci_dev_count_values']} mhi={v1243['mhi_bus_count_values']} wlan0={v1243['wlan0_exists_values']}",
        },
        {
            "name": "android-positive-power-surface",
            "status": "pass" if android_positive_power else "blocked",
            "detail": f"pmic={v1244['android_pmic_soft_reset']} pcie={v1244['android_pcie_rc1']}",
        },
        {
            "name": "dts-sdx50m-gpio-contract",
            "status": "pass" if all(dts_contract.values()) else "blocked",
            "detail": dts_contract["ap2mdm_soft_reset_gpio"],
        },
    ]
    pass_ok = all(check["status"] == "pass" for check in checks)
    decision = "v1245-soft-reset-reached-pmic-gdsc-not-applied" if pass_ok else "v1245-reachability-input-incomplete"
    reason = (
        "existing native evidence reaches the proprietary SDX50M soft-reset stack, but current native V1243 keeps PM8150L soft-reset unclaimed, PCIe GDSC at 0mV, and no GPIO142/PCI/MHI/wlan0 response while Android-positive evidence claims the PMIC surface and reaches wlan0"
        if pass_ok else
        "one or more reachability inputs are missing or contradictory"
    )
    next_step = (
        "V1246 should add a bounded same-run stack+power sampler or reproduce Android PM8150L pinctrl setup before another esoc0 trigger; do not start Wi-Fi HAL/connect yet"
        if pass_ok else
        "refresh V918/V1243/V1244 evidence before designing a PMIC/GDSC mutation gate"
    )

    return {
        "cycle": "v1245",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v918_report": str(repo_path(args.v918_report)),
            "v1243_manifest": str(repo_path(args.v1243_manifest)),
            "v1244_manifest": str(repo_path(args.v1244_manifest)),
            "dts": str(repo_path(args.dts)),
        },
        "v918": v918,
        "v1243": v1243,
        "v1244": v1244,
        "dts_contract": dts_contract,
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
    return "\n".join([
        "# V1245 PMIC/GDSC Reachability Classifier",
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
        "## Native Soft-reset Reachability",
        "",
        markdown_table(["field", "value"], [
            ["v918_reaches_soft_reset_stack", manifest["v918"]["reaches_soft_reset_stack"]],
            ["v918_soft_reset_location_line", manifest["v918"]["soft_reset_location_line"]],
            ["v918_stack_line", manifest["v918"]["stack_line"]],
            ["v1243_decision", manifest["v1243"]["decision"]],
            ["v1243_pm_service_actor_esoc0_attempt", manifest["v1243"]["pm_service_actor_esoc0_attempt"]],
            ["v1243_sample_count", manifest["v1243"]["sample_count"]],
        ]),
        "",
        "## Power Surface Delta",
        "",
        markdown_table(["field", "value"], [
            ["android_pmic_soft_reset", manifest["v1244"]["android_pmic_soft_reset"]],
            ["android_pcie_rc1", manifest["v1244"]["android_pcie_rc1"]],
            ["android_chain_present", manifest["v1244"]["android_chain_present"]],
            ["native_pmic_soft_reset_values", manifest["v1243"]["pmic_soft_reset_line_values"]],
            ["native_pcie1_gdsc_values", manifest["v1243"]["pcie1_gdsc_line_values"]],
            ["native_pcie0_gdsc_values", manifest["v1243"]["pcie0_gdsc_line_values"]],
            ["native_gpio142_values", manifest["v1243"]["mdm_status_count_values"]],
            ["native_pci_values", manifest["v1243"]["pci_dev_count_values"]],
            ["native_mhi_values", manifest["v1243"]["mhi_bus_count_values"]],
            ["native_wlan0_values", manifest["v1243"]["wlan0_exists_values"]],
        ]),
        "",
        "## DTS Contract",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in manifest["dts_contract"].items()]),
        "",
        "## Safety",
        "",
        "- host-only classifier; no device command or mutation executed",
        "- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = analyze(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
