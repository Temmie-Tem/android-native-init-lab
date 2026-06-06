#!/usr/bin/env python3
"""V1287 host-only classifier for the V1286 SDX50M power response gap.

V1286 supersedes the older V1243/V1246 response-window evidence with a working
syslog/klogctl collector. This classifier decides whether the current blocker is
still PM8150L gpio9 soft-reset setup, or whether the shortest next gate should
move to TLMM GPIO135/142 and PCIe GDSC response visibility.

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1287-v1286-sdx50m-power-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1287-v1286-sdx50m-power-gap-classifier.txt")
DEFAULT_V1286_MANIFEST = Path("tmp/wifi/v1286-pcie-klogctl-sampler-live/manifest.json")
DEFAULT_V1244_MANIFEST = Path("tmp/wifi/v1244-android-power-surface-classifier/manifest.json")
DEFAULT_V1246_MANIFEST = Path("tmp/wifi/v1246-same-run-power-stack-classifier/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1286-manifest", type=Path, default=DEFAULT_V1286_MANIFEST)
    parser.add_argument("--v1244-manifest", type=Path, default=DEFAULT_V1244_MANIFEST)
    parser.add_argument("--v1246-manifest", type=Path, default=DEFAULT_V1246_MANIFEST)
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


def sample_values(samples: list[dict[str, Any]], key: str) -> list[Any]:
    values: list[Any] = []
    for sample in samples:
        value = sample.get(key)
        if value not in values:
            values.append(value)
    return values


def all_samples(samples: list[dict[str, Any]], predicate) -> bool:
    return bool(samples) and all(predicate(sample) for sample in samples)


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def has_pmic9_android_shape(text: str) -> bool:
    return all(token in text for token in (
        "gpio9 : out",
        "normal",
        "vin-1",
        "pull-down 10uA",
        "push-pull",
        "high low",
    ))


def parse_v1286(manifest: dict[str, Any]) -> dict[str, Any]:
    pm = manifest.get("pm_service_trigger_observer") or {}
    sampler = manifest.get("response_sampler") or {}
    samples = sampler.get("samples") or []
    first = samples[0] if samples else {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "pm_service_actor_esoc0_attempt": bool(pm.get("pm_service_actor_esoc0_attempt")),
        "late_per_proxy_started": int_value(pm.get("late_per_proxy_started")) > 0,
        "all_postflight_safe": int_value(pm.get("all_postflight_safe"), -1),
        "sample_count": int_value(sampler.get("sample_count"), len(samples)),
        "kmsg_sources": sampler.get("kmsg_sources") or [],
        "kmsg_open_seen": bool(sampler.get("kmsg_open_seen")),
        "max_kmsg_filtered_count": int_value(sampler.get("max_kmsg_filtered_count")),
        "max_kmsg_pcie_count": int_value(sampler.get("max_kmsg_pcie_count")),
        "max_kmsg_mhi_count": int_value(sampler.get("max_kmsg_mhi_count")),
        "max_kmsg_wlfw_count": int_value(sampler.get("max_kmsg_wlfw_count")),
        "max_kmsg_sdx50m_count": int_value(sampler.get("max_kmsg_sdx50m_count")),
        "max_mdm_status_count_total": int_value(sampler.get("max_mdm_status_count_total")),
        "max_pci_dev_count": int_value(sampler.get("max_pci_dev_count")),
        "max_mhi_bus_count": int_value(sampler.get("max_mhi_bus_count")),
        "mhi_pipe_seen": bool(sampler.get("mhi_pipe_seen")),
        "wlan0_seen": bool(sampler.get("wlan0_seen")),
        "gpiochip_lineinfo_seen": bool(sampler.get("gpiochip_lineinfo_seen")),
        "gpiochip_lineinfo_kernel_owned_seen": bool(sampler.get("gpiochip_lineinfo_kernel_owned_seen")),
        "gpiochip_lineinfo_ap2mdm_consumer_seen": bool(sampler.get("gpiochip_lineinfo_ap2mdm_consumer_seen")),
        "gpiochip_lineinfo_zero_action_ok": bool(sampler.get("gpiochip_lineinfo_zero_action_ok")),
        "pmic_soft_reset_values": sample_values(samples, "pmic_soft_reset_line"),
        "pmic_gpio1270_blocks": sample_values(samples, "pmic_gpio1270_debugfs_block"),
        "pcie1_gdsc_values": sample_values(samples, "pcie1_gdsc_line"),
        "pcie0_gdsc_values": sample_values(samples, "pcie0_gdsc_line"),
        "pin135_values": sample_values(samples, "pin135_line"),
        "pin142_values": sample_values(samples, "pin142_line"),
        "first_pmic_gpio1270_block": str(first.get("pmic_gpio1270_debugfs_block", "")),
        "first_pmic_soft_reset_line": str(first.get("pmic_soft_reset_line", "")),
        "first_pcie1_gdsc_line": str(first.get("pcie1_gdsc_line", "")),
        "first_pcie0_gdsc_line": str(first.get("pcie0_gdsc_line", "")),
        "safety": {
            key: bool(manifest.get(key))
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
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "android_pmic_soft_reset": android.get("pm8150l_gpio9_line", ""),
        "android_pcie_rc1": android.get("pcie_rc1_report_line", ""),
        "android_tlmm_gpio135": android.get("tlmm_gpio135_line", ""),
        "android_tlmm_gpio142": android.get("tlmm_gpio142_line", ""),
        "android_chain_present": all((timeline.get(name) or {}).get("present") for name in (
            "subsys_esoc0_get",
            "wlfw_start",
            "wlan_pd",
            "icnss_qmi",
            "fw_ready",
            "wlan0",
        )),
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    v1286 = parse_v1286(load_json(args.v1286_manifest))
    v1244 = parse_v1244(load_json(args.v1244_manifest))
    v1246 = load_json(args.v1246_manifest)

    native_pmic9_matches_android_shape = any(
        has_pmic9_android_shape(str(value))
        for value in v1286["pmic_gpio1270_blocks"]
    )
    native_pmic9_pinmux_unclaimed = any(
        "MUX UNCLAIMED" in str(value)
        for value in v1286["pmic_soft_reset_values"]
    )
    native_gdsc_zero = all(
        "0mV" in str(value)
        for value in v1286["pcie1_gdsc_values"] + v1286["pcie0_gdsc_values"]
        if value
    )
    native_no_downstream = (
        v1286["max_mdm_status_count_total"] == 0
        and v1286["max_pci_dev_count"] == 0
        and v1286["max_mhi_bus_count"] == 0
        and not v1286["mhi_pipe_seen"]
        and not v1286["wlan0_seen"]
        and v1286["max_kmsg_pcie_count"] == 0
        and v1286["max_kmsg_mhi_count"] == 0
        and v1286["max_kmsg_wlfw_count"] == 0
        and v1286["max_kmsg_sdx50m_count"] == 0
    )
    android_positive = (
        v1244["pass"]
        and has_pmic9_android_shape(v1244["android_pmic_soft_reset"])
        and "PCIe RC1" in v1244["android_pcie_rc1"]
        and v1244["android_chain_present"]
    )
    safety_clean = not any(v1286["safety"].values())
    checks = [
        {
            "name": "v1286-live-path-valid",
            "status": "pass" if v1286["pass"] and v1286["pm_service_actor_esoc0_attempt"] and v1286["late_per_proxy_started"] else "blocked",
            "detail": f"decision={v1286['decision']} samples={v1286['sample_count']}",
        },
        {
            "name": "v1286-klogctl-valid",
            "status": "pass" if v1286["kmsg_open_seen"] and "syslog-read-all" in v1286["kmsg_sources"] and v1286["max_kmsg_filtered_count"] > 0 else "blocked",
            "detail": f"sources={v1286['kmsg_sources']} filtered={v1286['max_kmsg_filtered_count']}",
        },
        {
            "name": "native-pmic9-shape-matches-android",
            "status": "pass" if native_pmic9_matches_android_shape and v1286["gpiochip_lineinfo_ap2mdm_consumer_seen"] else "blocked",
            "detail": v1286["first_pmic_gpio1270_block"],
        },
        {
            "name": "native-pmic9-pinmux-conflict-demoted",
            "status": "pass" if native_pmic9_pinmux_unclaimed and native_pmic9_matches_android_shape else "blocked",
            "detail": v1286["first_pmic_soft_reset_line"],
        },
        {
            "name": "native-pcie-gdsc-still-zero",
            "status": "pass" if native_gdsc_zero else "blocked",
            "detail": f"pcie1={v1286['pcie1_gdsc_values']} pcie0={v1286['pcie0_gdsc_values']}",
        },
        {
            "name": "native-no-pcie-mhi-wlfw-response",
            "status": "pass" if native_no_downstream else "blocked",
            "detail": f"gpio142={v1286['max_mdm_status_count_total']} pci={v1286['max_pci_dev_count']} mhi={v1286['max_mhi_bus_count']} kmsg_pcie={v1286['max_kmsg_pcie_count']} kmsg_mhi={v1286['max_kmsg_mhi_count']} kmsg_wlfw={v1286['max_kmsg_wlfw_count']}",
        },
        {
            "name": "android-positive-contrast",
            "status": "pass" if android_positive else "blocked",
            "detail": f"pmic={v1244['android_pmic_soft_reset']} pcie={v1244['android_pcie_rc1']}",
        },
        {
            "name": "safety-clean",
            "status": "pass" if safety_clean and v1286["gpiochip_lineinfo_zero_action_ok"] else "blocked",
            "detail": f"safety={v1286['safety']} lineinfo_zero_action={v1286['gpiochip_lineinfo_zero_action_ok']}",
        },
    ]
    pass_ok = all(check["status"] == "pass" for check in checks)
    decision = "v1287-klogctl-confirms-post-esoc0-power-response-gap" if pass_ok else "v1287-input-incomplete"
    reason = (
        "V1286 proves the klogctl collector works and demotes PM8150L gpio9 shape as the shortest blocker: native gpio9 already matches Android's out/high PMIC shape, while PCIe GDSC remains 0mV and GPIO142/PCIe/MHI/WLFW/SDX50M response stays absent after PM-service enters the eSoC path"
        if pass_ok else
        "one or more V1286/Android contrast inputs are missing or contradictory"
    )
    next_step = (
        "V1288 should build a no-write TLMM/PCIe response observer that captures untruncated GPIO135/GPIO142, PMIC9, and PCIe GDSC state deltas before considering any PMIC/GPIO mutation gate"
        if pass_ok else
        "refresh V1286 or Android positive evidence before selecting a wider live gate"
    )

    return {
        "cycle": "v1287",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1286_manifest": str(repo_path(args.v1286_manifest)),
            "v1244_manifest": str(repo_path(args.v1244_manifest)),
            "v1246_manifest": str(repo_path(args.v1246_manifest)),
        },
        "v1286": v1286,
        "v1244": v1244,
        "v1246_decision": v1246.get("decision", ""),
        "native_pmic9_matches_android_shape": native_pmic9_matches_android_shape,
        "native_pmic9_pinmux_unclaimed": native_pmic9_pinmux_unclaimed,
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
    v1286 = manifest["v1286"]
    v1244 = manifest["v1244"]
    return "\n".join([
        "# V1287 V1286 SDX50M Power Gap Classifier",
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
        "## V1286 Native",
        "",
        markdown_table(["field", "value"], [
            ["decision", v1286["decision"]],
            ["sample_count", v1286["sample_count"]],
            ["kmsg_sources", ", ".join(v1286["kmsg_sources"])],
            ["max_kmsg_filtered_count", v1286["max_kmsg_filtered_count"]],
            ["first_pmic_soft_reset_line", v1286["first_pmic_soft_reset_line"]],
            ["native_pmic9_matches_android_shape", manifest["native_pmic9_matches_android_shape"]],
            ["first_pcie1_gdsc_line", v1286["first_pcie1_gdsc_line"]],
            ["first_pcie0_gdsc_line", v1286["first_pcie0_gdsc_line"]],
            ["max_mdm_status_count_total", v1286["max_mdm_status_count_total"]],
            ["max_pci_dev_count", v1286["max_pci_dev_count"]],
            ["max_mhi_bus_count", v1286["max_mhi_bus_count"]],
            ["mhi_pipe_seen", v1286["mhi_pipe_seen"]],
            ["wlan0_seen", v1286["wlan0_seen"]],
            ["kmsg_pcie_mhi_wlfw_sdx50m", f"{v1286['max_kmsg_pcie_count']}/{v1286['max_kmsg_mhi_count']}/{v1286['max_kmsg_wlfw_count']}/{v1286['max_kmsg_sdx50m_count']}"],
        ]),
        "",
        "## Android Contrast",
        "",
        markdown_table(["field", "value"], [
            ["decision", v1244["decision"]],
            ["android_pmic_soft_reset", v1244["android_pmic_soft_reset"]],
            ["android_pcie_rc1", v1244["android_pcie_rc1"]],
            ["android_tlmm_gpio135", v1244["android_tlmm_gpio135"]],
            ["android_tlmm_gpio142", v1244["android_tlmm_gpio142"]],
            ["android_chain_present", v1244["android_chain_present"]],
        ]),
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
