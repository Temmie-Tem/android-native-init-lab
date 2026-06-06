#!/usr/bin/env python3
"""V1361 host-only MHI surface ownership/downstream classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v1361-mhi-surface-ownership-classifier")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1361_MHI_SURFACE_OWNERSHIP_CLASSIFIER_2026-06-01.md")
SOURCE_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel')

INPUTS = {
    "v1360_manifest": Path("tmp/wifi/v1360-mhi-platform-surface-verifier-live/manifest.json"),
    "v1360_report": Path("docs/reports/NATIVE_INIT_V1360_MHI_PLATFORM_SURFACE_VERIFIER_LIVE_2026-06-01.md"),
    "mhi_arch_qcom_c": SOURCE_ROOT / "drivers/bus/mhi/controllers/mhi_arch_qcom.c",
    "mhi_qcom_c": SOURCE_ROOT / "drivers/bus/mhi/controllers/mhi_qcom.c",
    "mhi_main_c": SOURCE_ROOT / "drivers/bus/mhi/core/mhi_main.c",
    "mhi_init_c": SOURCE_ROOT / "drivers/bus/mhi/core/mhi_init.c",
    "mhi_pm_c": SOURCE_ROOT / "drivers/bus/mhi/core/mhi_pm.c",
    "mhi_h": SOURCE_ROOT / "include/linux/mhi.h",
    "mhi_uci_c": SOURCE_ROOT / "drivers/bus/mhi/devices/mhi_uci.c",
    "mhi_netdev_c": SOURCE_ROOT / "drivers/bus/mhi/devices/mhi_netdev.c",
    "mhi_dtr_c": SOURCE_ROOT / "drivers/bus/mhi/core/mhi_dtr.c",
    "rmnet_ctl_mhi_c": SOURCE_ROOT / "drivers/soc/qcom/rmnet_ctl/rmnet_ctl_mhi.c",
    "qdss_bridge_c": SOURCE_ROOT / "drivers/soc/qcom/qdss_bridge.c",
    "sm8150_mhi_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-mhi.dtsi",
    "sm8150_pcie_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi",
    "sm8150_sdx50m_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-sdx50m.dtsi",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def first_line(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line:
            return line.strip()
    return ""


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def checks(inputs: dict[str, str], v1360_manifest: dict[str, Any]) -> dict[str, bool]:
    analysis = v1360_manifest.get("analysis") or {}
    client_sources = "\n".join([
        inputs["mhi_uci_c"],
        inputs["mhi_netdev_c"],
        inputs["mhi_dtr_c"],
        inputs["rmnet_ctl_mhi_c"],
        inputs["qdss_bridge_c"],
    ])
    return {
        "v1360_live_has_mhi_topology": bool(analysis.get("dt_has_mhi_1c0b000"))
        and bool(analysis.get("dt_has_esoc_ref"))
        and bool(analysis.get("mhi_bus_present")),
        "v1360_live_has_no_mhi_or_pci_devices": analysis.get("mhi_bus_device_count") == 0
        and analysis.get("dev_mhi_count") == 0
        and analysis.get("pci_device_count") == 0,
        "mhi_pci_controller_requires_pci_dev": "int mhi_pci_probe(struct pci_dev *pci_dev" in inputs["mhi_qcom_c"]
        and "mhi_register_controller(pci_dev)" in inputs["mhi_qcom_c"],
        "mhi_pci_driver_waits_for_pci_enumeration": "static struct pci_driver mhi_pcie_driver" in inputs["mhi_qcom_c"]
        and "module_pci_driver(mhi_pcie_driver)" in inputs["mhi_qcom_c"]
        and "{PCI_DEVICE(MHI_PCIE_VENDOR_ID, 0x0305)}" in inputs["mhi_qcom_c"],
        "mhi_esoc_hook_is_downstream_of_pci_dev": "mhi_arch_esoc_ops_power_on" in inputs["mhi_arch_qcom_c"]
        and "struct pci_dev *pci_dev = mhi_dev->pci_dev" in inputs["mhi_arch_qcom_c"]
        and "msm_pcie_pm_control(MSM_PCIE_RESUME" in inputs["mhi_arch_qcom_c"]
        and "mhi_pci_probe(pci_dev, NULL)" in inputs["mhi_arch_qcom_c"],
        "mhi_devices_created_by_controller_state": "void mhi_create_devices(struct mhi_controller *mhi_cntrl)" in inputs["mhi_main_c"]
        and "mhi_alloc_device(mhi_cntrl)" in inputs["mhi_main_c"]
        and "mhi_create_devices(mhi_cntrl)" in inputs["mhi_pm_c"],
        "mhi_driver_bind_is_client_only": "driver->bus = &mhi_bus_type" in inputs["mhi_init_c"]
        and "return driver_register(driver)" in inputs["mhi_init_c"]
        and "struct mhi_driver" in inputs["mhi_h"],
        "live_mhi_drivers_are_client_drivers": "mhi_driver_register(&mhi_uci_driver)" in client_sources
        and "mhi_driver_register(&mhi_netdev_driver)" in client_sources
        and "module_driver(rmnet_ctl_driver" in client_sources
        and "mhi_driver_register(&qdss_mhi_driver)" in client_sources,
        "client_drivers_probe_mhi_device": "probe(struct mhi_device" in client_sources
        and "struct mhi_device *mhi_dev" in client_sources,
        "dt_binds_sdx50m_to_mhi_pci_path": "esoc-0 = <&mdm3>" in inputs["sm8150_sdx50m_dtsi"]
        and 'pci-ids = "17cb:0305"' in inputs["sm8150_mhi_dtsi"]
        and "mhi_device: mhi_dev@1c0b000" in inputs["sm8150_pcie_dtsi"],
    }


def classify() -> dict[str, Any]:
    missing = [str(path) for path in INPUTS.values() if not repo_path(path).exists()]
    if missing:
        return {
            "cycle": "V1361",
            "generated_at": now_iso(),
            "decision": "v1361-inputs-missing",
            "pass": False,
            "missing": missing,
        }

    inputs = {name: read_text(path) for name, path in INPUTS.items() if name not in {"v1360_manifest"}}
    v1360_manifest = read_json(INPUTS["v1360_manifest"])
    result_checks = checks(inputs, v1360_manifest)
    passed = all(result_checks.values())
    decision = (
        "v1361-mhi-surfaces-downstream-no-safe-mutation"
        if passed
        else "v1361-mhi-surface-ownership-incomplete"
    )
    reason = (
        "V1360 found MHI bus/client-driver surfaces but no MHI or PCI device instances. "
        "OSRC shows the MHI controller is created from pci_dev via mhi_pci_probe, while "
        "the visible MHI bind files belong to client drivers that require existing "
        "mhi_device instances. Therefore these surfaces are downstream of pcie1 "
        "enumeration and are not a narrower safe mutation."
        if passed
        else "one or more MHI ownership/downstream assumptions are not proven"
    )
    next_step = (
        "V1362 host-only pci-msm/pcie1 mutation risk classifier before any bind/rescan attempt"
        if passed
        else "repair missing source/evidence before choosing any pcie1 mutation"
    )
    return {
        "cycle": "V1361",
        "type": "host-only classifier",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "checks": result_checks,
        "v1360_analysis": v1360_manifest.get("analysis") or {},
        "source_facts": {
            "mhi_pci_probe": first_line(inputs["mhi_qcom_c"], "int mhi_pci_probe(struct pci_dev *pci_dev"),
            "mhi_pci_driver": first_line(inputs["mhi_qcom_c"], "static struct pci_driver mhi_pcie_driver"),
            "mhi_esoc_power_on": first_line(inputs["mhi_arch_qcom_c"], "static int mhi_arch_esoc_ops_power_on"),
            "mhi_create_devices": first_line(inputs["mhi_main_c"], "void mhi_create_devices"),
            "mhi_driver_register": first_line(inputs["mhi_init_c"], "int mhi_driver_register"),
            "mhi_uci_register": first_line(inputs["mhi_uci_c"], "mhi_driver_register(&mhi_uci_driver)"),
            "mhi_netdev_register": first_line(inputs["mhi_netdev_c"], "mhi_driver_register(&mhi_netdev_driver)"),
            "rmnet_ctl_register": first_line(inputs["rmnet_ctl_mhi_c"], "module_driver(rmnet_ctl_driver"),
            "qdss_bridge_register": first_line(inputs["qdss_bridge_c"], "mhi_driver_register(&qdss_mhi_driver)"),
        },
        "rejected_next_mutations": [
            "MHI client driver bind/unbind: requires existing mhi_device instances and cannot create PCI/MHI enumeration",
            "/dev/mhi* open: no device nodes exist in V1360 evidence",
            "MHI debugfs/client surfaces: observational or client-side, not pcie1 RC enable controls",
            "pci-msm bind/unbind or global PCI rescan: still too broad until V1362 risk classifier",
        ],
        "hard_exclusions": [
            "host-only; no device command",
            "no MHI bind/unbind",
            "no platform bind/unbind",
            "no PCI rescan",
            "no PMIC/GPIO/GDSC write",
            "no eSoC notify or BOOT_DONE",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no flash, boot image write, or partition write",
        ],
    }


def check_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return [[key, bool_text(bool(value))] for key, value in sorted((manifest.get("checks") or {}).items())]


def fact_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    return [[key, value] for key, value in (manifest.get("source_facts") or {}).items()]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V1361 MHI Surface Ownership Classifier",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        markdown_table(["check", "pass"], check_rows(manifest)) if manifest.get("checks") else "",
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1361 MHI Surface Ownership Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1361`",
        "- Type: host-only classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_mhi_surface_ownership_classifier_v1361.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1361-mhi-surface-ownership-classifier/manifest.json`",
        "  - `tmp/wifi/v1361-mhi-surface-ownership-classifier/summary.md`",
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "## Checks",
        "",
        markdown_table(["check", "pass"], check_rows(manifest)) if manifest.get("checks") else "inputs missing",
        "",
        "## Source Facts",
        "",
        markdown_table(["fact", "value"], fact_rows(manifest)) if manifest.get("source_facts") else "inputs missing",
        "",
        "## Rejected Next Mutations",
        "",
        "\n".join(f"- {item}" for item in manifest.get("rejected_next_mutations", [])),
        "",
        "## Safety",
        "",
        "- Host-only; no device command or live runtime access.",
        "- No MHI bind/unbind, platform bind/unbind, PCI rescan, PMIC/GPIO/GDSC write,",
        "  eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, credential handling,",
        "  DHCP/routes, external ping, flash, boot image write, or partition write.",
        "",
        "## Next",
        "",
        manifest["next_step"],
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("command", choices=("run",), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = classify()
    out_dir = repo_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_private_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "summary.md", render_summary(manifest))
    write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(out_dir)}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
