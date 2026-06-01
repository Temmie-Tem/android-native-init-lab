#!/usr/bin/env python3
"""V1522 host-only Android-good/native-fail RC1 source parity classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1522-android-native-rc1-source-parity-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1522_ANDROID_NATIVE_RC1_SOURCE_PARITY_CLASSIFIER_2026-06-01.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1522-android-native-rc1-source-parity-classifier.txt")
V1521_MANIFEST = Path("tmp/wifi/v1521-android-rc1-magisk-postfs-handoff/manifest.json")
V1518_MANIFEST = Path("tmp/wifi/v1518-wifi-critical-source-timing-classifier/manifest.json")
V1517_RC1 = Path("tmp/wifi/v1517-wifi-critical-source-pre-l0-handoff/test-rc1-window-result.stdout.txt")
FIRST_LABEL = "sample=case_aligned_micro_after_case_0ms"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def read_text(path: Path, limit: int = 4 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].decode("utf-8", errors="replace")


def nested(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def first_match(lines: list[str], pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in lines:
        if regex.search(line):
            return line.strip()
    return ""


def low_gpio135(line: str) -> bool:
    return bool(re.search(r"gpio135\s*:.*\bout\s+0\b", line, re.IGNORECASE))


def low_gpio142(line: str) -> bool:
    return bool(re.search(r"gpio142\s*:.*\bin\s+0\b", line, re.IGNORECASE))


def gdsc_0mv(line: str) -> bool:
    return "pcie_1_gdsc" in line and "0mV" in line


def irq142_zero(line: str) -> bool:
    if not re.search(r"msmgpio-dc\s+142", line, re.IGNORECASE):
        return False
    left = line.split("msmgpio-dc", 1)[0]
    if ":" not in left:
        return False
    counts = re.findall(r"\b\d+\b", left.split(":", 1)[1])
    return bool(counts) and all(count == "0" for count in counts)


def extract_native_first_window(rc1_text: str) -> dict[str, Any]:
    lines = [line for line in rc1_text.splitlines() if line.startswith(FIRST_LABEL)]
    return {
        "source_count": len(lines),
        "has_first_window": bool(lines),
        "gpio135_line": first_match(lines, r"gpio135\s*:"),
        "gpio142_line": first_match(lines, r"gpio142\s*:"),
        "gpio142_irq_line": first_match(lines, r"msmgpio-dc\s+142\s+Edge\s+mdm status"),
        "pcie1_gdsc_line": first_match(lines, r"pcie_1_gdsc"),
        "mdm_gpio135_pinmux": first_match(lines, r"pin 135 .*qcom,mdm3"),
        "mdm_gpio142_pinmux": first_match(lines, r"pin 142 .*qcom,mdm3"),
    }


def sample_flags(sample: dict[str, Any] | None) -> dict[str, Any]:
    sample = sample or {}
    gpio135 = str(sample.get("gpio135_line") or "")
    gpio142 = str(sample.get("gpio142_line") or "")
    irq142 = str(sample.get("gpio142_irq_line") or "")
    gdsc = str(sample.get("pcie1_gdsc_line") or "")
    return {
        "index": sample.get("index"),
        "uptime": sample.get("uptime"),
        "gpio135_line": gpio135,
        "gpio142_line": gpio142,
        "gpio142_irq_line": irq142,
        "pcie1_gdsc_line": gdsc,
        "gpio135_low": low_gpio135(gpio135),
        "gpio142_low": low_gpio142(gpio142),
        "gpio142_irq_zero": irq142_zero(irq142),
        "pcie1_gdsc_0mv": gdsc_0mv(gdsc),
    }


def classify() -> dict[str, Any]:
    v1521 = read_json(V1521_MANIFEST)
    v1518 = read_json(V1518_MANIFEST)
    rc1_text = read_text(V1517_RC1)

    v1521_analysis = nested(v1521, "context", "analysis", default={}) or {}
    v1521_dmesg = v1521_analysis.get("dmesg") or {}
    v1521_window = v1521_analysis.get("matched_window") or {}
    native_progress = nested(v1518, "checks", "progress", default={}) or {}
    native_timing = nested(v1518, "checks", "timing", default={}) or {}
    native_window = extract_native_first_window(rc1_text)

    android_before = sample_flags(v1521_window.get("sample_before_lower"))
    android_after = sample_flags(v1521_window.get("sample_after_lower"))
    android_first = sample_flags(v1521_window.get("first_sample"))
    android_last = sample_flags(v1521_window.get("last_sample"))
    native_flags = sample_flags(native_window)

    android_good = all(
        [
            v1521.get("pass") is True,
            v1521.get("decision") == "v1521-magisk-postfs-pre-lower-window-rollback-pass",
            v1521_window.get("has_pre_lower_sample") is True,
            v1521_window.get("has_post_lower_sample") is True,
            int(v1521_dmesg.get("wlfw_lines") or 0) > 0,
            int(v1521_dmesg.get("bdf_lines") or 0) > 0,
            int(v1521_dmesg.get("wlan0_lines") or 0) > 0,
        ]
    )
    native_fail = all(
        [
            v1518.get("pass") is True,
            native_progress.get("final_decision") == "rc1-ltssm-link-failed-no-l0",
            native_progress.get("provider_trigger") is True,
            native_progress.get("rc1_progress") is True,
            native_progress.get("rc1_link_failed") is True,
            native_progress.get("rc1_l0") is False,
            native_progress.get("mhi_progress") is False,
            native_progress.get("wlfw_progress") is False,
            native_progress.get("bdf_progress") is False,
            native_progress.get("fw_ready_progress") is False,
            native_progress.get("wlan0_present") is False,
            native_timing.get("all_expected_before_link_fail") is True,
            native_window["has_first_window"],
        ]
    )
    nondiscriminating_sources = all(
        [
            android_before["gpio135_low"],
            android_before["gpio142_low"],
            android_before["gpio142_irq_zero"],
            android_before["pcie1_gdsc_0mv"],
            android_after["gpio135_low"],
            android_after["gpio142_low"],
            android_after["gpio142_irq_zero"],
            native_flags["gpio135_low"],
            native_flags["gpio142_low"],
            native_flags["pcie1_gdsc_0mv"],
        ]
    )
    no_l0_marker_in_v1521 = not bool(v1521_dmesg.get("pcie_l0_time"))

    checks = [
        {
            "name": "android-good-pre-post-lower-window",
            "status": "pass" if android_good else "blocked",
            "detail": "V1521 brackets WLFW/BDF/wlan0 with post-fs-data samples and rolls back to native v724",
        },
        {
            "name": "native-source-exact-no-l0-window",
            "status": "pass" if native_fail else "blocked",
            "detail": "V1518/V1517 preserve rc1-ltssm-link-failed-no-l0 with selected sources before link fail",
        },
        {
            "name": "sampled-debugfs-sources-nondiscriminating",
            "status": "pass" if nondiscriminating_sources else "blocked",
            "detail": "Android-good and native-fail both show low GPIO135/GPIO142 and 0mV pcie1 GDSC in the sampled windows",
        },
        {
            "name": "pcie-l0-marker-still-needs-better-source",
            "status": "pass" if no_l0_marker_in_v1521 else "review",
            "detail": "V1521 confirms lower Wi-Fi success but does not expose a PCIe L0 dmesg timestamp in this capture",
        },
    ]
    pass_ok = all(item["status"] == "pass" for item in checks)
    decision = (
        "v1522-sampled-sources-nondiscriminating-msm-pcie-static-needed"
        if pass_ok
        else "v1522-source-parity-inputs-incomplete"
    )
    reason = (
        "V1521 Android-good and V1518/V1517 native-fail share the same sampled GPIO/GDSC low/off snapshots, so the next useful branch is msm_pcie TEST:11 vs normal-path semantics"
        if pass_ok
        else "Android-good/native-fail source parity inputs are missing or contradictory"
    )
    return {
        "cycle": "V1522",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "inputs": {
            "v1521": rel(V1521_MANIFEST),
            "v1518": rel(V1518_MANIFEST),
            "v1517_rc1": rel(V1517_RC1),
        },
        "host": collect_host_metadata(),
        "checks": checks,
        "android": {
            "wlfw_time": v1521_dmesg.get("wlfw_time"),
            "bdf_time": v1521_dmesg.get("bdf_time"),
            "wlan0_time": v1521_dmesg.get("wlan0_time"),
            "pcie_l0_time": v1521_dmesg.get("pcie_l0_time"),
            "first_sample": android_first,
            "before_lower": android_before,
            "after_lower": android_after,
            "last_sample": android_last,
        },
        "native": {
            "decision": native_progress.get("final_decision"),
            "link_failed_after_case_ms": native_timing.get("link_failed_after_case_ms"),
            "max_expected_source_end_ms": native_timing.get("max_expected_source_end_ms"),
            "first_window": native_flags,
            "raw_first_window": native_window,
        },
        "next_gate": {
            "primary": "V1523 msm_pcie TEST:11 vs Android normal-path static/callgraph classifier",
            "rationale": "The currently sampled GPIO/IRQ/GDSC sources do not distinguish Android-good from native-fail. The remaining actionable question is whether corrected TEST:11 omits a normal msm_pcie bring-up operation or endpoint preparation semantic.",
        },
        "safety": {
            "host_only": True,
            "device_commands": False,
            "wifi_hal_start": False,
            "scan_connect": False,
            "credentials": False,
            "dhcp_routes_external_ping": False,
            "pmic_gpio_gdsc_write": False,
            "esoc_notify_boot_done_spoof": False,
            "global_pci_rescan": False,
            "platform_bind_unbind": False,
            "boot_or_partition_write": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    android = result["android"]
    native = result["native"]
    lines = [
        "# Native Init V1522 Android/Native RC1 Source Parity Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1522`",
        "- Type: host-only classifier over V1521 Android-good and V1518/V1517 native-fail evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "path"], [[name, path] for name, path in result["inputs"].items()]),
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail"], [[item["name"], item["status"], item["detail"]] for item in result["checks"]]),
        "",
        "## Android-Good Window",
        "",
        f"- WLFW/BDF/wlan0: `{android['wlfw_time']}/{android['bdf_time']}/{android['wlan0_time']}`",
        f"- PCIe L0 dmesg timestamp in V1521: `{android['pcie_l0_time']}`",
        "",
        markdown_table(
            ["sample", "uptime", "GPIO135", "GPIO142", "GPIO142 IRQ zero", "pcie1 GDSC"],
            [
                ["first", android["first_sample"].get("uptime"), android["first_sample"].get("gpio135_line"), android["first_sample"].get("gpio142_line"), android["first_sample"].get("gpio142_irq_zero"), android["first_sample"].get("pcie1_gdsc_line")],
                ["before_lower", android["before_lower"].get("uptime"), android["before_lower"].get("gpio135_line"), android["before_lower"].get("gpio142_line"), android["before_lower"].get("gpio142_irq_zero"), android["before_lower"].get("pcie1_gdsc_line")],
                ["after_lower", android["after_lower"].get("uptime"), android["after_lower"].get("gpio135_line"), android["after_lower"].get("gpio142_line"), android["after_lower"].get("gpio142_irq_zero"), android["after_lower"].get("pcie1_gdsc_line")],
                ["last", android["last_sample"].get("uptime"), android["last_sample"].get("gpio135_line"), android["last_sample"].get("gpio142_line"), android["last_sample"].get("gpio142_irq_zero"), android["last_sample"].get("pcie1_gdsc_line")],
            ],
        ),
        "",
        "## Native-Fail Window",
        "",
        f"- Decision: `{native['decision']}`",
        f"- link failed after TEST:11 case: `{native['link_failed_after_case_ms']}` ms",
        f"- selected source max end: `{native['max_expected_source_end_ms']}` ms",
        "",
        markdown_table(
            ["source", "value"],
            [
                ["GPIO135", native["first_window"].get("gpio135_line")],
                ["GPIO142", native["first_window"].get("gpio142_line")],
                ["GPIO142 IRQ", native["first_window"].get("gpio142_irq_line")],
                ["pcie1 GDSC", native["first_window"].get("pcie1_gdsc_line")],
            ],
        ),
        "",
        "## Interpretation",
        "",
        "V1521 captured the Android-good pre/post lower window early enough, but the sampled debugfs/interrupt/regulator sources still look like the native-fail pre-L0 window: GPIO135/GPIO142 low, GPIO142 IRQ count zero, and `pcie_1_gdsc` 0mV. These sources therefore cannot by themselves explain native `POLL_COMPLIANCE -> link failed -> no L0`.",
        "",
        "The next useful branch is `msm_pcie` path semantics: classify the corrected debugfs `TEST:11` path against Android's normal RC1 bring-up path and identify operations TEST:11 does not perform. Firmware/MHI/WLFW/scan/connect remain downstream until native RC1 reaches L0 and PCI enumeration.",
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.",
        "",
        "## Next",
        "",
        "- V1523 should build the `msm_pcie` TEST:11 vs normal-path static/callgraph classifier.",
        "- Keep firmware/MHI/WLFW/scan/connect parked until native RC1 L0 and PCI enumeration exist.",
        "",
    ]
    return "\n".join(str(line) for line in lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = classify()
    report = render_report(result)
    store = EvidenceStore(repo_path(args.out_dir))
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(args.report_path), report)
    print(json.dumps({"decision": result["decision"], "pass": result["pass"], "out_dir": rel(args.out_dir)}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
