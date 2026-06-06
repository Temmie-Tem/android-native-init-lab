#!/usr/bin/env python3
"""V1448 host-only classifier for V1447 case-aligned micro endpoint evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_INPUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1447-wifi-test-boot-case-aligned-micro-endpoint-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1448-case-aligned-micro-endpoint-handoff-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1448_CASE_ALIGNED_MICRO_ENDPOINT_HANDOFF_CLASSIFIER_2026-06-01.md"
)

MICRO_SAMPLE_RE = re.compile(
    r"^rc1_micro_sample label=(?P<label>\S+) "
    r"elapsed_ms=(?P<elapsed>-?\d+) "
    r"detect_elapsed_ms=(?P<detect>-?\d+) "
    r"micro_elapsed_ms=(?P<micro>-?\d+)"
)
WRITER_RE = re.compile(
    r"^rc1_micro_writer_summary .* writer_wait_rc=(?P<wait_rc>-?\d+) "
    r"status=0x(?P<status>[0-9a-fA-F]+) "
    r"micro_writer rc=(?P<rc>-?\d+) errno=(?P<errno>\d+) "
    r"rc_sel_elapsed_ms=(?P<rc_sel>-?\d+) "
    r"case_elapsed_ms=(?P<case>-?\d+)"
)
GPIO_RE = re.compile(
    r"^sample=(?P<label>\S+) source=micro_debug_gpio needle=(?P<needle>gpio\d+) "
    r"match=\s*(?P<match>.*)$"
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_window(text: str) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    writer: dict[str, Any] = {}
    gpio: dict[str, dict[str, str]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        sample_match = MICRO_SAMPLE_RE.match(line)
        if sample_match:
            samples.append({
                "label": sample_match.group("label"),
                "elapsed_ms": int(sample_match.group("elapsed")),
                "detect_elapsed_ms": int(sample_match.group("detect")),
                "micro_elapsed_ms": int(sample_match.group("micro")),
            })
            continue
        writer_match = WRITER_RE.match(line)
        if writer_match:
            writer = {
                "writer_wait_rc": int(writer_match.group("wait_rc")),
                "status": int(writer_match.group("status"), 16),
                "rc": int(writer_match.group("rc")),
                "errno": int(writer_match.group("errno")),
                "rc_sel_elapsed_ms": int(writer_match.group("rc_sel")),
                "case_elapsed_ms": int(writer_match.group("case")),
            }
            continue
        gpio_match = GPIO_RE.match(line)
        if gpio_match:
            gpio.setdefault(gpio_match.group("label"), {})[gpio_match.group("needle")] = gpio_match.group("match")

    case_elapsed = writer.get("case_elapsed_ms", -1)
    samples_after_case = [
        sample for sample in samples
        if case_elapsed >= 0 and sample["elapsed_ms"] >= case_elapsed
    ]
    first_after_case = samples_after_case[0] if samples_after_case else None
    first_offset = first_after_case["elapsed_ms"] - case_elapsed if first_after_case else None
    active_labels = [sample["label"] for sample in samples if "after_case_" in sample["label"]]
    gpio135_values = [gpio.get(label, {}).get("gpio135", "") for label in active_labels]
    gpio142_values = [gpio.get(label, {}).get("gpio142", "") for label in active_labels]
    return {
        "sample_count": len(samples),
        "sample_labels": [sample["label"] for sample in samples],
        "writer": writer,
        "writer_ok": writer.get("writer_wait_rc") == 0 and writer.get("rc") == 0 and writer.get("status") == 0,
        "samples_after_case_count": len(samples_after_case),
        "first_after_case": first_after_case,
        "first_after_case_offset_ms": first_offset,
        "all_samples_after_case": len(samples) > 0 and len(samples_after_case) == len(samples),
        "gpio135_all_low": bool(gpio135_values) and all("out 0" in value for value in gpio135_values),
        "gpio142_all_low": bool(gpio142_values) and all("in 0" in value for value in gpio142_values),
        "gpio135_values": gpio135_values[:4],
        "gpio142_values": gpio142_values[:4],
        "post_case_aligned_micro_present": "post_case_aligned_micro_200ms" in text,
    }


def classify(input_dir: Path) -> dict[str, Any]:
    handoff = json.loads(read_text(input_dir / "manifest.json") or "{}")
    window = read_text(input_dir / "test-rc1-window-result.stdout.txt")
    dmesg = read_text(input_dir / "test-v1393-dmesg.stdout.txt")
    wlan0 = read_text(input_dir / "test-wlan0.stdout.txt")
    rollback = read_text(input_dir / "rollback-from-native.stdout.txt")
    parsed = parse_window(window)

    rc1_l0 = "LTSSM_STATE: LTSSM_L0" in dmesg or "PCIe RC1 Current GEN" in dmesg
    rc1_link_failed = "PCIe RC1 link initialization failed" in dmesg
    mhi = any(marker in dmesg for marker in ("mhi_arch_esoc_ops_power_on", "mhi_pci_probe", "mhi_0305"))
    wlfw = any(marker in dmesg for marker in ("wlfw", "WLFW", "icnss_qmi"))
    wlan0_present = "wlan0=present" in wlan0
    rollback_ok = "A90 Linux init 0.9.68 (v724)" in rollback

    if (
        parsed["writer_ok"]
        and parsed["all_samples_after_case"]
        and parsed["gpio135_all_low"]
        and parsed["gpio142_all_low"]
        and rc1_link_failed
        and not rc1_l0
    ):
        decision = "v1448-case-aligned-micro-all-low-no-l0"
        passed = True
        reason = "V1447 proved case-aligned sampling; GPIO135/GPIO142 stayed low from 0ms through 150ms after case completion and RC1 still failed before L0"
    elif parsed["writer_ok"] and parsed["all_samples_after_case"]:
        decision = "v1448-case-aligned-micro-sampled"
        passed = True
        reason = "V1447 proved case-aligned sampling, but endpoint GPIO state needs manual review"
    else:
        decision = "v1448-case-aligned-micro-incomplete"
        passed = False
        reason = "V1447 did not produce a complete case-aligned micro sample set"

    return {
        "cycle": "V1448",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "input_dir": rel(input_dir),
        "handoff_decision": handoff.get("decision", ""),
        "handoff_pass": bool(handoff.get("pass")),
        "rollback_ok": rollback_ok,
        "micro": parsed,
        "progress": {
            "rc1_l0": rc1_l0,
            "rc1_link_failed": rc1_link_failed,
            "mhi_progress": mhi,
            "wlfw_progress": wlfw,
            "wlan0_present": wlan0_present,
            "connect_ready": wlan0_present,
        },
        "guardrails": {
            "host_only": True,
            "device_command_executed": False,
            "flash_executed": False,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
        },
        "next_gate": "V1449 host-only provider-vs-rc1 timing analysis before another live mutation",
    }


def render_report(result: dict[str, Any]) -> str:
    micro = result["micro"]
    progress = result["progress"]
    return "\n".join([
        "# Native Init V1448 Case-Aligned Micro Endpoint Handoff Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1448`",
        "- Type: host-only classifier over V1447 case-aligned micro endpoint evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['input_dir']}`",
        f"- Handoff decision: `{result['handoff_decision']}`",
        f"- Rollback v724 verified: `{result['rollback_ok']}`",
        "",
        "## Case-Aligned Micro Timing",
        "",
        f"- writer ok: `{micro['writer_ok']}`",
        f"- writer case elapsed ms: `{micro['writer'].get('case_elapsed_ms')}`",
        f"- sample count: `{micro['sample_count']}`",
        f"- all samples after case: `{micro['all_samples_after_case']}`",
        f"- first sample after case: `{micro['first_after_case']}`",
        f"- first sample after case offset ms: `{micro['first_after_case_offset_ms']}`",
        f"- GPIO135 all low: `{micro['gpio135_all_low']}`",
        f"- GPIO142 all low: `{micro['gpio142_all_low']}`",
        f"- post case-aligned context present: `{micro['post_case_aligned_micro_present']}`",
        "",
        "## Progress Classification",
        "",
        f"- `rc1_l0`: `{progress['rc1_l0']}`",
        f"- `rc1_link_failed`: `{progress['rc1_link_failed']}`",
        f"- `mhi_progress`: `{progress['mhi_progress']}`",
        f"- `wlfw_progress`: `{progress['wlfw_progress']}`",
        f"- `wlan0_present`: `{progress['wlan0_present']}`",
        f"- `connect_ready`: `{progress['connect_ready']}`",
        "",
        "## Interpretation",
        "",
        "The sampler alignment issue is closed. V1447 sampled after the corrected",
        "RC1 case write returned, but AP2MDM GPIO135 and MDM2AP GPIO142 still stayed",
        "low through the active post-case window. RC1 reached LTSSM polling and then",
        "failed before L0; no MHI, WLFW, BDF, FW-ready, or `wlan0` appeared.",
        "",
        "## Safety Scope",
        "",
        "This classifier was host-only. It did not issue device commands, flash,",
        "reboot, start Wi-Fi HAL, scan/connect, use credentials, configure",
        "DHCP/routes, or perform external ping.",
        "",
        "## Next",
        "",
        "V1449 should be host-only and compare provider-trigger timing against the",
        "RC1 debugfs case timing. The next live mutation should not repeat RC1 case",
        "sampling until the provider-level AP2MDM/MDM2AP timing question is sharper.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = classify(args.input_dir)
    report = render_report(result)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "out_dir": rel(args.out_dir),
        "next_gate": result["next_gate"],
    }, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
