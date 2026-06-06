#!/usr/bin/env python3
"""V1244 host-only Android/native SDX50M power-surface comparator."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, workspace_private_input_path, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1244-android-power-surface-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1244-android-power-surface-classifier.txt")
DEFAULT_ANDROID_GPIO = Path(
    "tmp/wifi/v1024-fast-fd-android-timing-handoff-live-20260526-181232/"
    "v1022-late-android-pm-esoc-timing/android/commands/gpio.txt"
)
DEFAULT_ANDROID_DMESG = Path(
    "tmp/wifi/v1024-fast-fd-android-timing-handoff-live-20260526-181232/"
    "v1022-late-android-pm-esoc-timing/android/commands/dmesg-full.txt"
)
DEFAULT_ANDROID_SUMMARY = Path(
    "tmp/wifi/v1024-fast-fd-android-timing-handoff-live-20260526-181232/"
    "v1022-late-android-pm-esoc-timing/summary.md"
)
DEFAULT_ANDROID_PCIE_REPORT = Path("docs/reports/NATIVE_INIT_V1045_PM_PIL_PREREQUISITE_DELTA_2026-05-26.md")
DEFAULT_NATIVE_V1243 = Path("tmp/wifi/v1243-sdx50m-power-prereq-response-live/manifest.json")
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

TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+\.[0-9]+)\]")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-gpio", type=Path, default=DEFAULT_ANDROID_GPIO)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--android-summary", type=Path, default=DEFAULT_ANDROID_SUMMARY)
    parser.add_argument("--android-pcie-report", type=Path, default=DEFAULT_ANDROID_PCIE_REPORT)
    parser.add_argument("--native-v1243", type=Path, default=DEFAULT_NATIVE_V1243)
    parser.add_argument("--dts", type=Path, default=DEFAULT_DTS)
    parser.add_argument("command", nargs="?", choices=("run",), default="run")
    return parser.parse_args()


def read_text(path: Path, limit: int = 8 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def first_line(text: str, *needles: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if all(needle in line for needle in needles):
            return line
    return ""


def first_line_regex(text: str, pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for raw in text.splitlines():
        line = raw.strip()
        if regex.search(line):
            return line
    return ""


def time_for_line(line: str) -> float | None:
    match = TS_RE.match(line)
    if not match:
        return None
    return float(match.group("ts"))


def section_line_after(text: str, section_pattern: str, line_pattern: str) -> str:
    section_re = re.compile(section_pattern, re.IGNORECASE)
    line_re = re.compile(line_pattern, re.IGNORECASE)
    in_section = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if section_re.search(line):
            in_section = True
            continue
        if in_section and line.startswith("gpiochip"):
            in_section = False
        if in_section and line_re.search(line):
            return line.strip()
    return ""


def dmesg_marker(text: str, pattern: str) -> dict[str, Any]:
    line = first_line_regex(text, pattern)
    return {"present": bool(line), "time": time_for_line(line), "line": line}


def sample_values(samples: list[dict[str, Any]], key: str) -> list[Any]:
    values: list[Any] = []
    for sample in samples:
        value = sample.get(key)
        if value not in values:
            values.append(value)
    return values


def parse_native_v1243(manifest: dict[str, Any]) -> dict[str, Any]:
    sampler = manifest.get("response_sampler") or {}
    samples = sampler.get("samples") or []
    first = samples[0] if samples else {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "sample_count": len(samples),
        "pm_service_actor_esoc0_attempt": bool((manifest.get("pm_service_trigger_observer") or {}).get("pm_service_actor_esoc0_attempt")),
        "mdm_status_count_values": sample_values(samples, "mdm_status_count_total"),
        "mdm3_state_values": sample_values(samples, "mdm3_state"),
        "pmic_soft_reset_line_values": sample_values(samples, "pmic_soft_reset_line"),
        "pmic_soft_reset_source_values": sample_values(samples, "pmic_soft_reset_source"),
        "pcie1_gdsc_line_values": sample_values(samples, "pcie1_gdsc_line"),
        "pcie0_gdsc_line_values": sample_values(samples, "pcie0_gdsc_line"),
        "pci_dev_count_values": sample_values(samples, "pci_dev_count"),
        "mhi_bus_count_values": sample_values(samples, "mhi_bus_count"),
        "mhi_pipe_exists_values": sample_values(samples, "mhi_pipe_exists"),
        "wlan0_exists_values": sample_values(samples, "wlan0_exists"),
        "first_sample": first,
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    android_gpio = read_text(args.android_gpio)
    android_dmesg = read_text(args.android_dmesg)
    android_summary = read_text(args.android_summary)
    android_pcie_report = read_text(args.android_pcie_report)
    dts = read_text(args.dts)
    native_manifest = load_json(args.native_v1243)
    native = parse_native_v1243(native_manifest)

    android = {
        "gpio_file_present": bool(android_gpio),
        "dmesg_file_present": bool(android_dmesg),
        "summary_file_present": bool(android_summary),
        "debug_gpio_readable": "GPIO_DEBUG readable=1" in android_gpio,
        "tlmm_gpio135_line": first_line_regex(android_gpio, r"^gpio135\s*:"),
        "tlmm_gpio142_line": first_line_regex(android_gpio, r"^gpio142\s*:"),
        "pm8150l_gpio9_line": section_line_after(android_gpio, r"pm8150l@4:pinctrl@c000", r"^\s*gpio9\s*:"),
        "pm8150_gpio9_line": section_line_after(android_gpio, r"pm8150@0:pinctrl@c000", r"^\s*gpio9\s*:"),
        "timeline": {
            "wlfw_start": dmesg_marker(android_dmesg, r"cnss-daemon wlfw_start: Starting"),
            "subsys_esoc0_get": dmesg_marker(android_dmesg, r"__subsystem_get: esoc0 count:0"),
            "wlan_pd": dmesg_marker(android_dmesg, r"msm/modem/wlan_pd"),
            "icnss_qmi": dmesg_marker(android_dmesg, r"icnss_qmi: QMI Server Connected"),
            "fw_ready": dmesg_marker(android_dmesg, r"icnss: WLAN FW is ready"),
            "wlan0": dmesg_marker(android_dmesg, r"dev : wlan0 : event"),
        },
        "pcie_rc1_report_line": first_line(android_pcie_report, "PCIe RC1 link initialized"),
        "pcie_rc1_report_present": "PCIe RC1 link initialized" in android_pcie_report,
    }
    dts_contract = {
        "dts_present": bool(dts),
        "ap2mdm_status_gpio": first_line(dts, "qcom,ap2mdm-status-gpio"),
        "mdm2ap_status_gpio": first_line(dts, "qcom,mdm2ap-status-gpio"),
        "ap2mdm_soft_reset_gpio": first_line(dts, "qcom,ap2mdm-soft-reset-gpio"),
        "compatible": first_line(dts, 'compatible = "qcom,ext-sdx50m"'),
    }

    android_wifi_chain = all(
        android["timeline"][name]["present"]
        for name in ("subsys_esoc0_get", "wlfw_start", "wlan_pd", "icnss_qmi", "fw_ready", "wlan0")
    )
    android_pmic_claimed = "out" in android["pm8150l_gpio9_line"] and "normal" in android["pm8150l_gpio9_line"]
    native_pmic_unclaimed = any("MUX UNCLAIMED" in str(value) for value in native["pmic_soft_reset_line_values"])
    native_pcie_gdsc_zero = all("0mV" in str(value) for value in native["pcie1_gdsc_line_values"] + native["pcie0_gdsc_line_values"] if value)
    native_no_downstream = (
        native["sample_count"] > 0 and
        native["mdm_status_count_values"] == [0] and
        native["pci_dev_count_values"] == [0] and
        native["mhi_bus_count_values"] == [0] and
        native["wlan0_exists_values"] == [0]
    )

    checks = [
        {
            "name": "android-positive-chain",
            "status": "pass" if android_wifi_chain else "blocked",
            "detail": "Android dmesg has esoc0 get, WLFW, WLAN-PD, ICNSS-QMI, FW ready, and wlan0",
        },
        {
            "name": "android-pmic-soft-reset-surface",
            "status": "pass" if android_pmic_claimed else "blocked",
            "detail": android["pm8150l_gpio9_line"] or "missing PM8150L gpio9 line",
        },
        {
            "name": "native-pmic-soft-reset-unclaimed",
            "status": "pass" if native_pmic_unclaimed else "blocked",
            "detail": "; ".join(str(value) for value in native["pmic_soft_reset_line_values"]),
        },
        {
            "name": "native-pcie-gdsc-zero",
            "status": "pass" if native_pcie_gdsc_zero else "blocked",
            "detail": "; ".join(str(value) for value in native["pcie1_gdsc_line_values"] + native["pcie0_gdsc_line_values"]),
        },
        {
            "name": "native-no-downstream-response",
            "status": "pass" if native_no_downstream else "blocked",
            "detail": f"gpio142={native['mdm_status_count_values']} pci={native['pci_dev_count_values']} mhi={native['mhi_bus_count_values']} wlan0={native['wlan0_exists_values']}",
        },
        {
            "name": "dts-contract-present",
            "status": "pass" if all(dts_contract.values()) else "blocked",
            "detail": dts_contract["ap2mdm_soft_reset_gpio"],
        },
    ]
    pass_ok = all(check["status"] == "pass" for check in checks)
    decision = "v1244-android-pmic-pcie-delta-classified" if pass_ok else "v1244-power-surface-input-incomplete"
    reason = (
        "Android-positive boot has PM8150L gpio9 claimed/output and reaches WLFW/wlan0, while native V1243 reaches pm-service esoc0 but leaves PM8150L gpio9 unclaimed, PCIe GDSC at 0mV, and no GPIO142/PCI/MHI/wlan0 response"
        if pass_ok else
        "one or more Android/native power-surface inputs are missing or contradictory"
    )
    next_step = (
        "V1245 should prove whether native mdm_subsys_powerup reaches PM8150L soft-reset/GDSC operations, or reproduce Android PMIC pinctrl setup before another esoc0 trigger"
        if pass_ok else
        "refresh Android-positive PMIC/GDSC evidence before another live native trigger"
    )

    return {
        "cycle": "v1244",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "android_gpio": str(repo_path(args.android_gpio)),
            "android_dmesg": str(repo_path(args.android_dmesg)),
            "android_summary": str(repo_path(args.android_summary)),
            "android_pcie_report": str(repo_path(args.android_pcie_report)),
            "native_v1243": str(repo_path(args.native_v1243)),
            "dts": str(repo_path(args.dts)),
        },
        "android": android,
        "native": native,
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
    android = manifest["android"]
    native = manifest["native"]
    timeline_rows = [
        [name, item["present"], item["time"], item["line"]]
        for name, item in android["timeline"].items()
    ]
    native_rows = [
        ["decision", native["decision"]],
        ["sample_count", native["sample_count"]],
        ["pm_service_actor_esoc0_attempt", native["pm_service_actor_esoc0_attempt"]],
        ["mdm_status_count_values", native["mdm_status_count_values"]],
        ["pmic_soft_reset_line_values", native["pmic_soft_reset_line_values"]],
        ["pcie1_gdsc_line_values", native["pcie1_gdsc_line_values"]],
        ["pcie0_gdsc_line_values", native["pcie0_gdsc_line_values"]],
        ["pci_dev_count_values", native["pci_dev_count_values"]],
        ["mhi_bus_count_values", native["mhi_bus_count_values"]],
        ["wlan0_exists_values", native["wlan0_exists_values"]],
    ]
    return "\n".join([
        "# V1244 Android/native SDX50M Power Surface Classifier",
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
        "## Android Power Surface",
        "",
        markdown_table(["field", "value"], [
            ["debug_gpio_readable", android["debug_gpio_readable"]],
            ["tlmm_gpio135_line", android["tlmm_gpio135_line"]],
            ["tlmm_gpio142_line", android["tlmm_gpio142_line"]],
            ["pm8150l_gpio9_line", android["pm8150l_gpio9_line"]],
            ["pm8150_gpio9_line", android["pm8150_gpio9_line"]],
            ["pcie_rc1_report_line", android["pcie_rc1_report_line"]],
        ]),
        "",
        "## Android Timeline",
        "",
        markdown_table(["marker", "present", "time", "line"], timeline_rows),
        "",
        "## Native V1243 Power Surface",
        "",
        markdown_table(["field", "value"], native_rows),
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
