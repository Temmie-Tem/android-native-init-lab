#!/usr/bin/env python3
"""V1444 host-only classifier for V1443 micro endpoint test-boot evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_INPUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1443-wifi-test-boot-micro-endpoint-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1444-micro-endpoint-handoff-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1444_MICRO_ENDPOINT_HANDOFF_CLASSIFIER_2026-06-01.md"
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


def parse_micro_window(text: str) -> dict[str, Any]:
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
    micro_start_elapsed = samples[0]["elapsed_ms"] if samples else -1
    case_after_micro_start_ms = (
        case_elapsed - micro_start_elapsed
        if case_elapsed >= 0 and micro_start_elapsed >= 0
        else None
    )
    samples_after_case = [
        sample for sample in samples
        if case_elapsed >= 0 and sample["elapsed_ms"] >= case_elapsed
    ]
    first_after_case = samples_after_case[0] if samples_after_case else None
    first_after_case_offset_ms = (
        first_after_case["elapsed_ms"] - case_elapsed
        if first_after_case is not None
        else None
    )

    gpio135_values = [
        values.get("gpio135", "")
        for label, values in gpio.items()
        if label.startswith("micro_after_case_")
    ]
    gpio142_values = [
        values.get("gpio142", "")
        for label, values in gpio.items()
        if label.startswith("micro_after_case_")
    ]
    return {
        "sample_count": len(samples),
        "sample_labels": [sample["label"] for sample in samples],
        "samples": samples,
        "writer": writer,
        "writer_ok": writer.get("writer_wait_rc") == 0 and writer.get("rc") == 0 and writer.get("status") == 0,
        "micro_start_elapsed_ms": micro_start_elapsed,
        "case_after_micro_start_ms": case_after_micro_start_ms,
        "samples_after_case_count": len(samples_after_case),
        "first_after_case": first_after_case,
        "first_after_case_offset_ms": first_after_case_offset_ms,
        "gpio135_all_low": bool(gpio135_values) and all("out 0" in value for value in gpio135_values),
        "gpio142_all_low": bool(gpio142_values) and all("in 0" in value for value in gpio142_values),
        "gpio135_values": gpio135_values[:4],
        "gpio142_values": gpio142_values[:4],
        "post_micro_present": "post_micro_200ms" in text,
    }


def classify(input_dir: Path) -> dict[str, Any]:
    handoff = json.loads(read_text(input_dir / "manifest.json") or "{}")
    rc1_window = read_text(input_dir / "test-rc1-window-result.stdout.txt")
    dmesg = read_text(input_dir / "test-v1393-dmesg.stdout.txt")
    wlan0 = read_text(input_dir / "test-wlan0.stdout.txt")
    version = read_text(input_dir / "test-version.stdout.txt")
    rollback = read_text(input_dir / "rollback-from-native.stdout.txt")
    micro = parse_micro_window(rc1_window)

    rc1_l0 = "LTSSM_STATE: LTSSM_L0" in dmesg or "PCIe RC1 Current GEN" in dmesg
    rc1_link_failed = "PCIe RC1 link initialization failed" in dmesg
    mhi = any(marker in dmesg for marker in ("mhi_arch_esoc_ops_power_on", "mhi_pci_probe", "mhi_0305"))
    wlfw = any(marker in dmesg for marker in ("wlfw", "WLFW", "icnss_qmi"))
    wlan0_present = "wlan0=present" in wlan0
    rollback_ok = "A90 Linux init 0.9.68 (v724)" in rollback
    test_version_ok = "A90 Linux init 0.9.81 (v1441-wifitest)" in version

    if micro["writer_ok"] and micro["case_after_micro_start_ms"] is not None and micro["case_after_micro_start_ms"] > 0:
        decision = "v1444-micro-sampler-case-write-late-no-l0"
        passed = True
        reason = "V1443 rollback passed and proved the V1441 micro reader started before the actual case write; evidence still stops at RC1 link failure before L0"
    elif micro["writer_ok"]:
        decision = "v1444-micro-sampler-aligned-no-l0"
        passed = True
        reason = "V1443 rollback passed and micro samples were case-aligned, but RC1 still failed before L0"
    else:
        decision = "v1444-micro-sampler-incomplete"
        passed = False
        reason = "V1443 evidence is missing a successful micro writer contract"

    return {
        "cycle": "V1444",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "input_dir": rel(input_dir),
        "handoff_decision": handoff.get("decision", ""),
        "handoff_pass": bool(handoff.get("pass")),
        "rollback_ok": rollback_ok,
        "test_version_ok": test_version_ok,
        "micro": micro,
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
        "next_gate": "V1445 source/build-only case-aligned micro sampler if V1444 confirms case-write-late",
    }


def render_report(result: dict[str, Any]) -> str:
    micro = result["micro"]
    progress = result["progress"]
    return "\n".join([
        "# Native Init V1444 Micro Endpoint Handoff Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1444`",
        "- Type: host-only classifier over V1443 micro endpoint evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['input_dir']}`",
        f"- Handoff decision: `{result['handoff_decision']}`",
        f"- Rollback v724 verified: `{result['rollback_ok']}`",
        "",
        "## Micro Timing",
        "",
        f"- writer ok: `{micro['writer_ok']}`",
        f"- writer case elapsed ms: `{micro['writer'].get('case_elapsed_ms')}`",
        f"- micro start elapsed ms: `{micro['micro_start_elapsed_ms']}`",
        f"- case after micro start ms: `{micro['case_after_micro_start_ms']}`",
        f"- sample count: `{micro['sample_count']}`",
        f"- samples after case: `{micro['samples_after_case_count']}`",
        f"- first sample after case: `{micro['first_after_case']}`",
        f"- first sample after case offset ms: `{micro['first_after_case_offset_ms']}`",
        f"- GPIO135 all low in micro samples: `{micro['gpio135_all_low']}`",
        f"- GPIO142 all low in micro samples: `{micro['gpio142_all_low']}`",
        f"- post micro context present: `{micro['post_micro_present']}`",
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
        "The V1441 micro sampler reduced active-window reads, but the parent started",
        "sampling before the writer completed the corrected RC1 `case=11` write.",
        "Only the last micro sample landed after the actual case write. The evidence",
        "therefore proves continued RC1 link failure, but does not yet fully resolve",
        "sub-100ms endpoint GPIO state after the exact case-write completion point.",
        "",
        "## Safety Scope",
        "",
        "This classifier was host-only. It did not issue device commands, flash,",
        "reboot, start Wi-Fi HAL, scan/connect, use credentials, configure",
        "DHCP/routes, or perform external ping.",
        "",
        "## Next",
        "",
        "V1445 should be source/build-only and align the micro reader to the actual",
        "writer completion signal: the writer should perform `rc_sel=2` and",
        "`case=11`, send its elapsed timestamps through the pipe immediately after",
        "the case write returns, and only then should the parent sample `0ms` through",
        "`150ms` after the confirmed case write.",
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
