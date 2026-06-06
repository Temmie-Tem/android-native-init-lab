#!/usr/bin/env python3
"""V1291 host-only classifier for V1290 static GPIO parity.

V1290 added exact TLMM GPIO135/GPIO142 debugfs target-line sampling around the
bounded PM-service `/dev/subsys_esoc0` response window. This classifier compares
that native no-write surface with Android-positive evidence and decides whether
static GPIO shape remains a plausible shortest blocker.

No device command is executed here.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1291-static-gpio-parity-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1291-static-gpio-parity-classifier.txt")
DEFAULT_V1290_MANIFEST = Path("tmp/wifi/v1290-tlmm-pcie-sampler-live/manifest.json")
DEFAULT_V1244_MANIFEST = Path("tmp/wifi/v1244-android-power-surface-classifier/manifest.json")
DEFAULT_V1287_MANIFEST = Path("tmp/wifi/v1287-v1286-sdx50m-power-gap-classifier/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1290-manifest", type=Path, default=DEFAULT_V1290_MANIFEST)
    parser.add_argument("--v1244-manifest", type=Path, default=DEFAULT_V1244_MANIFEST)
    parser.add_argument("--v1287-manifest", type=Path, default=DEFAULT_V1287_MANIFEST)
    parser.add_argument("command", nargs="?", choices=("run",), default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def norm_space(value: Any) -> str:
    return " ".join(str(value or "").split())


def sample_values(samples: list[dict[str, Any]], key: str) -> list[str]:
    values: list[str] = []
    for sample in samples:
        value = str(sample.get(key, ""))
        if value and value not in values:
            values.append(value)
    return values


def normalize_gpio_line(line: Any) -> str:
    return norm_space(line)


def parse_v1290(manifest: dict[str, Any]) -> dict[str, Any]:
    pm = manifest.get("pm_service_trigger_observer") or {}
    sampler = manifest.get("response_sampler") or {}
    samples = sampler.get("samples") or []
    first = samples[0] if samples else {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "pm_service_actor_esoc0_attempt": bool_value(pm.get("pm_service_actor_esoc0_attempt")),
        "sample_count": int_value(sampler.get("sample_count"), len(samples)),
        "kmsg_sources": sampler.get("kmsg_sources") or [],
        "max_kmsg_filtered_count": int_value(sampler.get("max_kmsg_filtered_count")),
        "max_kmsg_pcie_count": int_value(sampler.get("max_kmsg_pcie_count")),
        "max_kmsg_mhi_count": int_value(sampler.get("max_kmsg_mhi_count")),
        "max_kmsg_wlfw_count": int_value(sampler.get("max_kmsg_wlfw_count")),
        "max_kmsg_sdx50m_count": int_value(sampler.get("max_kmsg_sdx50m_count")),
        "max_mdm_status_count_total": int_value(sampler.get("max_mdm_status_count_total")),
        "max_pci_dev_count": int_value(sampler.get("max_pci_dev_count")),
        "max_mhi_bus_count": int_value(sampler.get("max_mhi_bus_count")),
        "mhi_pipe_seen": bool_value(sampler.get("mhi_pipe_seen")),
        "wlan0_seen": bool_value(sampler.get("wlan0_seen")),
        "pcie1_gdsc_seen": bool_value(sampler.get("pcie1_gdsc_seen")),
        "pcie0_gdsc_seen": bool_value(sampler.get("pcie0_gdsc_seen")),
        "tlmm_gpio135_seen": bool_value(sampler.get("tlmm_gpio135_debugfs_target_line_seen")),
        "tlmm_gpio142_seen": bool_value(sampler.get("tlmm_gpio142_debugfs_target_line_seen")),
        "tlmm_gpio135_lines": sampler.get("tlmm_gpio135_debugfs_target_lines") or [],
        "tlmm_gpio142_lines": sampler.get("tlmm_gpio142_debugfs_target_lines") or [],
        "tlmm_gpio135_block_seen": bool_value(sampler.get("tlmm_gpio135_debugfs_target_block_seen")),
        "tlmm_gpio142_block_seen": bool_value(sampler.get("tlmm_gpio142_debugfs_target_block_seen")),
        "pcie1_gdsc_values": sample_values(samples, "pcie1_gdsc_line"),
        "pcie0_gdsc_values": sample_values(samples, "pcie0_gdsc_line"),
        "first_pcie1_gdsc_line": str(first.get("pcie1_gdsc_line", "")),
        "first_pcie0_gdsc_line": str(first.get("pcie0_gdsc_line", "")),
        "first_tlmm_gpio135_block": str(first.get("tlmm_gpio135_debugfs_target_block", "")),
        "first_tlmm_gpio142_block": str(first.get("tlmm_gpio142_debugfs_target_block", "")),
        "safety": {
            key: bool_value(manifest.get(key))
            for key in (
                "wifi_hal_start_executed",
                "scan_connect_executed",
                "credential_use_executed",
                "dhcp_route_executed",
                "external_ping_executed",
                "wifi_bringup_executed",
                "flash_executed",
                "partition_write_executed",
            )
        },
    }


def parse_v1244(manifest: dict[str, Any]) -> dict[str, Any]:
    android = manifest.get("android") or {}
    timeline = android.get("timeline") or {}
    chain_names = (
        "subsys_esoc0_get",
        "wlfw_start",
        "wlan_pd",
        "icnss_qmi",
        "fw_ready",
        "wlan0",
    )
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "tlmm_gpio135_line": android.get("tlmm_gpio135_line", ""),
        "tlmm_gpio142_line": android.get("tlmm_gpio142_line", ""),
        "pm8150l_gpio9_line": android.get("pm8150l_gpio9_line", ""),
        "pcie_rc1_report_line": android.get("pcie_rc1_report_line", ""),
        "chain_present": all(bool_value((timeline.get(name) or {}).get("present")) for name in chain_names),
    }


def has_zero_gdsc(values: list[str]) -> bool:
    return bool(values) and all("0mV" in value for value in values)


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    v1290 = parse_v1290(load_json(args.v1290_manifest))
    v1244 = parse_v1244(load_json(args.v1244_manifest))
    v1287_manifest = load_json(args.v1287_manifest)

    native_gpio135_lines = [normalize_gpio_line(line) for line in v1290["tlmm_gpio135_lines"]]
    native_gpio142_lines = [normalize_gpio_line(line) for line in v1290["tlmm_gpio142_lines"]]
    android_gpio135_line = normalize_gpio_line(v1244["tlmm_gpio135_line"])
    android_gpio142_line = normalize_gpio_line(v1244["tlmm_gpio142_line"])

    gpio135_static_parity = android_gpio135_line in native_gpio135_lines
    gpio142_static_parity = android_gpio142_line in native_gpio142_lines
    native_gdsc_zero = has_zero_gdsc(v1290["pcie1_gdsc_values"]) and has_zero_gdsc(v1290["pcie0_gdsc_values"])
    native_no_downstream = (
        v1290["max_mdm_status_count_total"] == 0
        and v1290["max_pci_dev_count"] == 0
        and v1290["max_mhi_bus_count"] == 0
        and not v1290["mhi_pipe_seen"]
        and not v1290["wlan0_seen"]
        and v1290["max_kmsg_pcie_count"] == 0
        and v1290["max_kmsg_mhi_count"] == 0
        and v1290["max_kmsg_wlfw_count"] == 0
        and v1290["max_kmsg_sdx50m_count"] == 0
    )
    android_positive = (
        v1244["pass"]
        and v1244["chain_present"]
        and "PCIe RC1" in str(v1244["pcie_rc1_report_line"])
        and bool(android_gpio135_line)
        and bool(android_gpio142_line)
    )
    safety_clean = not any(v1290["safety"].values())
    v1287_demoted_pmic = (
        bool_value(v1287_manifest.get("pass"))
        and v1287_manifest.get("decision") == "v1287-klogctl-confirms-post-esoc0-power-response-gap"
    )

    checks = [
        {
            "name": "v1290-live-path-valid",
            "status": "pass" if v1290["pass"] and v1290["pm_service_actor_esoc0_attempt"] and v1290["sample_count"] > 0 else "blocked",
            "detail": f"decision={v1290['decision']} samples={v1290['sample_count']} pm_esoc0={v1290['pm_service_actor_esoc0_attempt']}",
        },
        {
            "name": "v1290-klogctl-valid",
            "status": "pass" if "syslog-read-all" in v1290["kmsg_sources"] and v1290["max_kmsg_filtered_count"] > 0 else "blocked",
            "detail": f"sources={v1290['kmsg_sources']} filtered={v1290['max_kmsg_filtered_count']}",
        },
        {
            "name": "tlmm-gpio135-static-parity",
            "status": "pass" if v1290["tlmm_gpio135_seen"] and gpio135_static_parity else "blocked",
            "detail": f"native={native_gpio135_lines} android={android_gpio135_line}",
        },
        {
            "name": "tlmm-gpio142-static-parity",
            "status": "pass" if v1290["tlmm_gpio142_seen"] and gpio142_static_parity else "blocked",
            "detail": f"native={native_gpio142_lines} android={android_gpio142_line}",
        },
        {
            "name": "pmic9-already-demoted-by-v1287",
            "status": "pass" if v1287_demoted_pmic else "blocked",
            "detail": f"v1287_decision={v1287_manifest.get('decision', '')}",
        },
        {
            "name": "native-pcie-gdsc-still-zero",
            "status": "pass" if native_gdsc_zero else "blocked",
            "detail": f"pcie1={v1290['pcie1_gdsc_values']} pcie0={v1290['pcie0_gdsc_values']}",
        },
        {
            "name": "native-no-downstream-response",
            "status": "pass" if native_no_downstream else "blocked",
            "detail": f"gpio142={v1290['max_mdm_status_count_total']} pci={v1290['max_pci_dev_count']} mhi={v1290['max_mhi_bus_count']} pipe={v1290['mhi_pipe_seen']} wlan0={v1290['wlan0_seen']} kmsg_pcie/mhi/wlfw/sdx50m={v1290['max_kmsg_pcie_count']}/{v1290['max_kmsg_mhi_count']}/{v1290['max_kmsg_wlfw_count']}/{v1290['max_kmsg_sdx50m_count']}",
        },
        {
            "name": "android-positive-contrast",
            "status": "pass" if android_positive else "blocked",
            "detail": f"pcie={v1244['pcie_rc1_report_line']} chain={v1244['chain_present']}",
        },
        {
            "name": "safety-clean",
            "status": "pass" if safety_clean else "blocked",
            "detail": f"safety={v1290['safety']}",
        },
    ]
    pass_ok = all(check["status"] == "pass" for check in checks)
    decision = "v1291-static-gpio-parity-dynamic-power-gap" if pass_ok else "v1291-input-incomplete"
    reason = (
        "V1290 proves native TLMM GPIO135/GPIO142 static debugfs shape matches Android-positive GPIO135/GPIO142 lines, and V1287 already demoted PMIC9 shape. The active gap remains dynamic: after PM-service enters the eSoC path, PCIe GDSC stays at 0mV and GPIO142/PCIe/MHI/WLFW/SDX50M/wlan0 response stays absent."
        if pass_ok else
        "one or more V1290/V1244/V1287 inputs are missing or contradictory"
    )
    next_step = (
        "V1292 should classify dynamic PCIe/GDSC/eSoC power sequencing observability before any PMIC write, userspace GPIO hold, direct eSoC ioctl, or Wi-Fi bring-up gate"
        if pass_ok else
        "refresh V1290 or Android-positive evidence before selecting a dynamic power sequencing gate"
    )

    return {
        "cycle": "v1291",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1290_manifest": str(repo_path(args.v1290_manifest)),
            "v1244_manifest": str(repo_path(args.v1244_manifest)),
            "v1287_manifest": str(repo_path(args.v1287_manifest)),
        },
        "v1290": v1290,
        "v1244": v1244,
        "v1287_decision": v1287_manifest.get("decision", ""),
        "gpio135_static_parity": gpio135_static_parity,
        "gpio142_static_parity": gpio142_static_parity,
        "native_gdsc_zero": native_gdsc_zero,
        "native_no_downstream": native_no_downstream,
        "android_positive": android_positive,
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
    v1290 = manifest["v1290"]
    v1244 = manifest["v1244"]
    return "\n".join([
        "# V1291 Static GPIO Parity Classifier",
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
        "## Native V1290",
        "",
        markdown_table(["field", "value"], [
            ["decision", v1290["decision"]],
            ["sample_count", v1290["sample_count"]],
            ["kmsg_sources", ", ".join(v1290["kmsg_sources"])],
            ["gpio135_lines", v1290["tlmm_gpio135_lines"]],
            ["gpio142_lines", v1290["tlmm_gpio142_lines"]],
            ["first_gpio135_block", v1290["first_tlmm_gpio135_block"]],
            ["first_gpio142_block", v1290["first_tlmm_gpio142_block"]],
            ["first_pcie1_gdsc_line", v1290["first_pcie1_gdsc_line"]],
            ["first_pcie0_gdsc_line", v1290["first_pcie0_gdsc_line"]],
            ["max_mdm_status_count_total", v1290["max_mdm_status_count_total"]],
            ["max_pci_dev_count", v1290["max_pci_dev_count"]],
            ["max_mhi_bus_count", v1290["max_mhi_bus_count"]],
            ["mhi_pipe_seen", v1290["mhi_pipe_seen"]],
            ["wlan0_seen", v1290["wlan0_seen"]],
            ["kmsg_pcie_mhi_wlfw_sdx50m", f"{v1290['max_kmsg_pcie_count']}/{v1290['max_kmsg_mhi_count']}/{v1290['max_kmsg_wlfw_count']}/{v1290['max_kmsg_sdx50m_count']}"],
        ]),
        "",
        "## Android Contrast",
        "",
        markdown_table(["field", "value"], [
            ["decision", v1244["decision"]],
            ["android_gpio135", v1244["tlmm_gpio135_line"]],
            ["android_gpio142", v1244["tlmm_gpio142_line"]],
            ["android_pcie_rc1", v1244["pcie_rc1_report_line"]],
            ["android_chain_present", v1244["chain_present"]],
        ]),
        "",
        "## Safety",
        "",
        "- host-only classifier; no device command or mutation executed",
        "- no PMIC write, userspace GPIO line request/hold, direct eSoC ioctl, new daemon/HAL start, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write",
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
