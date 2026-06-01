#!/usr/bin/env python3
"""V1449 host-only provider-vs-RC1 timing classifier over V1447 evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1447-wifi-test-boot-case-aligned-micro-endpoint-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1449-provider-rc1-timing-classifier"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1449_PROVIDER_RC1_TIMING_CLASSIFIER_2026-06-01.md"

DMESG_TS_RE = re.compile(r"^\[\s*(?P<ts>\d+\.\d+)\]")
WATCHER_RE = re.compile(r"detect_elapsed_ms=(?P<detect>\d+).*line=<3>\[\s*(?P<ts>\d+\.\d+)\]")
WRITER_RE = re.compile(r"case_elapsed_ms=(?P<case>\d+)")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def first_dmesg_ts(text: str, needle: str) -> float | None:
    for line in text.splitlines():
        if needle not in line:
            continue
        match = DMESG_TS_RE.match(line)
        if match:
            return float(match.group("ts"))
    return None


def parse_timing(input_dir: Path) -> dict[str, Any]:
    dmesg = read_text(input_dir / "test-v1393-dmesg.stdout.txt")
    watcher = read_text(input_dir / "test-v1393-rc1-watcher-result.stdout.txt")
    window = read_text(input_dir / "test-rc1-window-result.stdout.txt")
    watcher_match = WATCHER_RE.search(watcher)
    writer_match = WRITER_RE.search(window)

    detect_elapsed_ms = int(watcher_match.group("detect")) if watcher_match else None
    detect_dmesg_ts = float(watcher_match.group("ts")) if watcher_match else None
    case_elapsed_ms = int(writer_match.group("case")) if writer_match else None
    modem_get_ts = first_dmesg_ts(dmesg, "__subsystem_get: modem")
    esoc_get_ts = first_dmesg_ts(dmesg, "__subsystem_get: esoc0")
    case_ts = first_dmesg_ts(dmesg, "PCIe: TEST: 11")
    phy_ready_ts = first_dmesg_ts(dmesg, "PCIe RC1 PHY is ready")
    link_failed_ts = first_dmesg_ts(dmesg, "PCIe RC1 link initialization failed")

    derived: dict[str, Any] = {}
    if detect_elapsed_ms is not None and detect_dmesg_ts is not None:
        derived["elapsed_to_dmesg_offset_ms"] = round(detect_elapsed_ms - detect_dmesg_ts * 1000.0, 3)
    if case_elapsed_ms is not None and detect_elapsed_ms is not None:
        derived["case_after_detect_elapsed_ms"] = case_elapsed_ms - detect_elapsed_ms
    if case_ts is not None and detect_dmesg_ts is not None:
        derived["case_after_detect_dmesg_ms"] = round((case_ts - detect_dmesg_ts) * 1000.0, 3)
    if esoc_get_ts is not None and detect_dmesg_ts is not None:
        derived["esoc_after_detect_dmesg_ms"] = round((esoc_get_ts - detect_dmesg_ts) * 1000.0, 3)
    if case_ts is not None and esoc_get_ts is not None:
        derived["case_after_esoc_dmesg_ms"] = round((case_ts - esoc_get_ts) * 1000.0, 3)
    if link_failed_ts is not None and case_ts is not None:
        derived["link_fail_after_case_dmesg_ms"] = round((link_failed_ts - case_ts) * 1000.0, 3)

    return {
        "detect_elapsed_ms": detect_elapsed_ms,
        "detect_dmesg_ts": detect_dmesg_ts,
        "case_elapsed_ms": case_elapsed_ms,
        "modem_get_ts": modem_get_ts,
        "esoc_get_ts": esoc_get_ts,
        "case_ts": case_ts,
        "phy_ready_ts": phy_ready_ts,
        "link_failed_ts": link_failed_ts,
        "derived": derived,
    }


def classify(input_dir: Path) -> dict[str, Any]:
    handoff = json.loads(read_text(input_dir / "manifest.json") or "{}")
    timing = parse_timing(input_dir)
    esoc_before_case = (
        timing["esoc_get_ts"] is not None
        and timing["case_ts"] is not None
        and timing["esoc_get_ts"] < timing["case_ts"]
    )
    case_delayed_after_esoc = timing["derived"].get("case_after_esoc_dmesg_ms", -1) > 100
    link_failed = timing["link_failed_ts"] is not None

    if esoc_before_case and case_delayed_after_esoc and link_failed:
        decision = "v1449-provider-precedes-rc1-case-no-l0"
        passed = True
        reason = "Provider esoc0 open occurred before the RC1 debugfs case; V1447 sampled after the later RC1 case, so the next live sampler should target provider-level AP2MDM/MDM2AP timing"
    else:
        decision = "v1449-provider-rc1-timing-needs-review"
        passed = False
        reason = "Provider and RC1 timing could not be cleanly separated from V1447 evidence"

    return {
        "cycle": "V1449",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "input_dir": rel(input_dir),
        "handoff_decision": handoff.get("decision", ""),
        "handoff_pass": bool(handoff.get("pass")),
        "timing": timing,
        "classification": {
            "esoc_before_case": esoc_before_case,
            "case_delayed_after_esoc": case_delayed_after_esoc,
            "link_failed": link_failed,
        },
        "guardrails": {
            "host_only": True,
            "device_command_executed": False,
            "flash_executed": False,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
        },
        "next_gate": "V1450 source/build-only provider-trigger micro sampler",
    }


def render_report(result: dict[str, Any]) -> str:
    timing = result["timing"]
    derived = timing["derived"]
    cls = result["classification"]
    return "\n".join([
        "# Native Init V1449 Provider-vs-RC1 Timing Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1449`",
        "- Type: host-only timing classifier over V1447 evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['input_dir']}`",
        f"- Handoff decision: `{result['handoff_decision']}`",
        "",
        "## Timing",
        "",
        f"- watcher detect elapsed ms: `{timing['detect_elapsed_ms']}`",
        f"- watcher detect dmesg ts: `{timing['detect_dmesg_ts']}`",
        f"- modem `__subsystem_get` ts: `{timing['modem_get_ts']}`",
        f"- esoc0 `__subsystem_get` ts: `{timing['esoc_get_ts']}`",
        f"- RC1 `TEST: 11` ts: `{timing['case_ts']}`",
        f"- RC1 PHY ready ts: `{timing['phy_ready_ts']}`",
        f"- RC1 link failed ts: `{timing['link_failed_ts']}`",
        f"- writer case elapsed ms: `{timing['case_elapsed_ms']}`",
        f"- esoc after detect dmesg ms: `{derived.get('esoc_after_detect_dmesg_ms')}`",
        f"- case after esoc dmesg ms: `{derived.get('case_after_esoc_dmesg_ms')}`",
        f"- link fail after case dmesg ms: `{derived.get('link_fail_after_case_dmesg_ms')}`",
        "",
        "## Classification",
        "",
        f"- esoc before RC1 case: `{cls['esoc_before_case']}`",
        f"- RC1 case delayed after esoc: `{cls['case_delayed_after_esoc']}`",
        f"- link failed: `{cls['link_failed']}`",
        "",
        "## Interpretation",
        "",
        "V1447's RC1 debugfs case was not the first provider-level event. The",
        "`__subsystem_get: esoc0` provider transition happened before the explicit",
        "RC1 `case=11` trigger. Therefore V1447 proves post-case GPIO135/GPIO142",
        "remained low, but it does not yet sample the provider transition itself.",
        "",
        "## Safety Scope",
        "",
        "This classifier was host-only. It did not issue device commands, flash,",
        "reboot, start Wi-Fi HAL, scan/connect, use credentials, configure",
        "DHCP/routes, or perform external ping.",
        "",
        "## Next",
        "",
        "V1450 should be source/build-only and add a provider-trigger micro sampler",
        "that watches for `__subsystem_get: esoc0`/`mdm_subsys_powerup` in PID1",
        "kmsg and samples GPIO135/GPIO142/RC1 status immediately around that",
        "provider event without adding Wi-Fi scan/connect or credential handling.",
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
