#!/usr/bin/env python3
"""V1549 host-only classifier for the V1548 low-overhead handoff result."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1549-low-overhead-result-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1549_LOW_OVERHEAD_RESULT_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1549-low-overhead-result-classifier.txt")

V1548_DIR = Path("tmp/wifi/v1548-low-overhead-handoff")
V1548_MANIFEST = V1548_DIR / "manifest.json"
V1548_DMESG = V1548_DIR / "test-v1393-dmesg.stdout.txt"
V1548_WINDOW = V1548_DIR / "test-rc1-window-result.stdout.txt"
V1548_WLAN0 = V1548_DIR / "test-wlan0.stdout.txt"
V1547_MANIFEST = Path("tmp/wifi/v1547-low-overhead-artifact-sanity/manifest.json")
V1545_MANIFEST = Path("tmp/wifi/v1545-low-overhead-endpoint-observer-design/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def first_payload_line(text: str, prefix: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped
    return ""


def parse_kv_line(line: str) -> dict[str, str]:
    return {match.group(1): match.group(2) for match in re.finditer(r"([A-Za-z0-9_.-]+)=([^ \t\r\n]+)", line)}


def first_ts(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\[\s*([0-9]+\.[0-9]+)\]", line)
        if match:
            return float(match.group(1))
    return None


def embedded_first_ts(line: str) -> float | None:
    match = re.search(r"\[\s*([0-9]+\.[0-9]+)\]", line)
    return float(match.group(1)) if match else None


def source_timing_rows(text: str) -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    regex = re.compile(
        r"sample=([^ ]+)\s+source=([^ ]+)\s+source_timing=(begin|end)"
        r".*?elapsed_ms=(-?\d+).*?micro_elapsed_ms=(-?\d+).*?source_duration_ms=(-?\d+)"
    )
    for line in text.splitlines():
        match = regex.search(line)
        if match:
            rows.append(
                {
                    "sample": match.group(1),
                    "source": match.group(2),
                    "phase": match.group(3),
                    "elapsed_ms": int(match.group(4)),
                    "micro_elapsed_ms": int(match.group(5)),
                    "source_duration_ms": int(match.group(6)),
                }
            )
    return rows


def lines_matching(text: str, pattern: str, limit: int = 32) -> list[str]:
    regex = re.compile(pattern, re.I)
    return [line.strip() for line in text.splitlines() if regex.search(line)][:limit]


def gpio_values_for_samples(text: str, gpio: int, allowed_samples: set[str]) -> list[int]:
    values: list[int] = []
    regex = re.compile(rf"sample=([^ ]+).*?\bgpio{gpio}\s*:\s*(?:in|out)\s+([01])\b")
    for line in text.splitlines():
        match = regex.search(line)
        if not match:
            continue
        sample = match.group(1)
        if sample not in allowed_samples:
            continue
        values.append(int(match.group(2)))
    return values


def irq_totals_for_samples(text: str, gpio: int, allowed_samples: set[str]) -> list[int]:
    totals: list[int] = []
    for line in text.splitlines():
        if f"msmgpio-dc {gpio}" not in line and f"msmgpio-dc  {gpio}" not in line:
            continue
        sample_match = re.search(r"sample=([^ ]+)", line)
        if sample_match and sample_match.group(1) not in allowed_samples:
            continue
        prefix = line.split("msmgpio-dc", 1)[0]
        numbers = [int(value) for value in re.findall(r"\b\d+\b", prefix)]
        if len(numbers) > 1:
            totals.append(sum(numbers[1:]))
    return totals


def pcie_gdsc_zero_before(text: str, max_elapsed_ms: float | None) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        if "pcie_1_gdsc" not in line or "0mV" not in line:
            continue
        elapsed_match = re.search(r"elapsed_ms=(\d+)", line)
        if elapsed_match and max_elapsed_ms is not None and int(elapsed_match.group(1)) > max_elapsed_ms:
            continue
        lines.append(line.strip())
    return lines


def analyze() -> dict[str, Any]:
    manifest = read_json(V1548_MANIFEST)
    v1547 = read_json(V1547_MANIFEST)
    v1545 = read_json(V1545_MANIFEST)
    dmesg = read_text(V1548_DMESG)
    window = read_text(V1548_WINDOW)
    wlan0 = read_text(V1548_WLAN0)
    wp = manifest.get("wifi_progress") if isinstance(manifest.get("wifi_progress"), dict) else {}
    rollback = manifest.get("rollback") if isinstance(manifest.get("rollback"), dict) else {}
    state_line = first_payload_line(window, "state=armed")
    writer_line = first_payload_line(window, "rc1_micro_writer_summary")
    state_kv = parse_kv_line(state_line)
    writer_kv = parse_kv_line(writer_line)
    detect_elapsed_ms = int(state_kv.get("detect_elapsed_ms", "-1"))
    detect_ts = embedded_first_ts(state_line)
    link_failed_ts = first_ts(dmesg, r"link initialization failed")
    link_failed_elapsed_ms = None
    if detect_elapsed_ms >= 0 and detect_ts is not None and link_failed_ts is not None:
        link_failed_elapsed_ms = detect_elapsed_ms + ((link_failed_ts - detect_ts) * 1000.0)
    timing_rows = source_timing_rows(window)
    end_rows = [row for row in timing_rows if row["phase"] == "end"]
    pre_fail_end_rows = [
        row for row in end_rows
        if link_failed_elapsed_ms is not None and int(row["elapsed_ms"]) <= link_failed_elapsed_ms
    ]
    pre_fail_sources = sorted({str(row["source"]) for row in pre_fail_end_rows})
    pre_fail_samples_by_source = {
        source: {str(row["sample"]) for row in pre_fail_end_rows if row["source"] == source}
        for source in pre_fail_sources
    }
    pre_fail_gpio_samples = pre_fail_samples_by_source.get("micro_debug_gpio", set())
    pre_fail_irq_samples = pre_fail_samples_by_source.get("micro_interrupts", set())
    return {
        "paths": {
            "manifest": rel(V1548_MANIFEST),
            "dmesg": rel(V1548_DMESG),
            "window": rel(V1548_WINDOW),
            "wlan0": rel(V1548_WLAN0),
            "v1547_manifest": rel(V1547_MANIFEST),
            "v1545_manifest": rel(V1545_MANIFEST),
        },
        "manifest": {
            "decision": manifest.get("decision"),
            "pass": bool(manifest.get("pass")),
            "handoff_pass": bool(manifest.get("handoff_pass")),
            "rollback_ok": bool(rollback.get("ok")),
            "rollback_attempt": rollback.get("attempt"),
            "wifi_progress": {
                "final_decision": wp.get("final_decision"),
                "provider_trigger": bool(wp.get("provider_trigger")),
                "modem_trigger": bool(wp.get("modem_trigger")),
                "rc1_progress": bool(wp.get("rc1_progress")),
                "rc1_l0": bool(wp.get("rc1_l0")),
                "rc1_link_failed": bool(wp.get("rc1_link_failed")),
                "mhi_progress": bool(wp.get("mhi_progress")),
                "wlfw_progress": bool(wp.get("wlfw_progress")),
                "bdf_progress": bool(wp.get("bdf_progress")),
                "fw_ready_progress": bool(wp.get("fw_ready_progress")),
                "wlan0_present": bool(wp.get("wlan0_present")),
                "connect_ready": bool(wp.get("connect_ready")),
            },
        },
        "prior": {
            "v1547_pass": bool(v1547.get("pass")),
            "v1545_pass": bool(v1545.get("pass")),
        },
        "alignment": {
            "detect_ts": detect_ts,
            "detect_elapsed_ms": detect_elapsed_ms,
            "link_failed_ts": link_failed_ts,
            "link_failed_elapsed_ms": link_failed_elapsed_ms,
            "writer_sysfs_elapsed_ms": int(writer_kv.get("sysfs_elapsed_ms", "-1")),
            "writer_rc": writer_kv.get("rc"),
            "writer_errno": writer_kv.get("errno"),
            "writer_sysfs_rc": writer_kv.get("sysfs_rc"),
            "trigger_mode": writer_kv.get("trigger_mode"),
        },
        "window": {
            "has_micro_critical": "micro_critical_fast_endpoint_sampler=1" in window,
            "has_clk_skip": "micro_critical_clk_summary_skipped=1" in window,
            "has_micro_focused_clk": "micro_focused_clk" in window,
            "timing_row_count": len(timing_rows),
            "pre_fail_end_row_count": len(pre_fail_end_rows),
            "pre_fail_sources": pre_fail_sources,
            "pre_fail_samples_by_source": {
                source: sorted(samples)
                for source, samples in pre_fail_samples_by_source.items()
            },
            "max_pre_fail_source_duration_ms": max(
                (int(row["source_duration_ms"]) for row in pre_fail_end_rows),
                default=None,
            ),
            "gpio_pre_fail": {
                str(gpio): {
                    "samples": len(gpio_values_for_samples(window, gpio, pre_fail_gpio_samples)),
                    "max": max(gpio_values_for_samples(window, gpio, pre_fail_gpio_samples))
                    if gpio_values_for_samples(window, gpio, pre_fail_gpio_samples)
                    else None,
                }
                for gpio in (102, 103, 104, 135, 142)
            },
            "irq_pre_fail": {
                str(gpio): {
                    "samples": len(irq_totals_for_samples(window, gpio, pre_fail_irq_samples)),
                    "max": max(irq_totals_for_samples(window, gpio, pre_fail_irq_samples))
                    if irq_totals_for_samples(window, gpio, pre_fail_irq_samples)
                    else None,
                }
                for gpio in (104, 142)
            },
            "pcie_1_gdsc_zero_pre_fail_lines": pcie_gdsc_zero_before(window, link_failed_elapsed_ms)[:8],
            "key_lines": lines_matching(
                window,
                r"rc1_micro_writer_summary|micro_critical_clk_summary_skipped|micro_interrupts|micro_debug_gpio|micro_critical_regulator|micro_critical_pinmux|pcie_1_gdsc|gpio102\s*:|gpio103\s*:|gpio104\s*:|gpio135\s*:|gpio142\s*:|msmgpio-dc\s+142",
                48,
            ),
        },
        "dmesg": {
            "rc1_assert_ts": first_ts(dmesg, r"Assert the reset of endpoint of RC1"),
            "rc1_phy_ready_ts": first_ts(dmesg, r"PCIe RC1 PHY is ready"),
            "rc1_release_ts": first_ts(dmesg, r"Release the reset of endpoint of RC1"),
            "poll_compliance_ts": first_ts(dmesg, r"LTSSM_POLL_COMPLIANCE"),
            "link_failed_ts": link_failed_ts,
            "has_l0": bool(re.search(r"LTSSM_STATE:\s+LTSSM_L0|Current GEN", dmesg)),
            "has_downstream": bool(re.search(r"mhi_0305|/dev/mhi|wlfw|BDF|FW ready|wlan0", dmesg, re.I)),
            "key_lines": lines_matching(
                dmesg,
                r"Assert the reset of endpoint of RC1|PHY is ready|Release the reset|LTSSM_STATE|link initialization failed|failed to enable RC1",
                32,
            ),
        },
        "wlan0_absent": "wlan0=absent" in wlan0,
    }


def classify() -> dict[str, Any]:
    evidence = analyze()
    wp = evidence["manifest"]["wifi_progress"]
    alignment = evidence["alignment"]
    window = evidence["window"]
    gpio = window["gpio_pre_fail"]
    irq = window["irq_pre_fail"]
    checks = {
        "v1547-artifact-sanity-pass": evidence["prior"]["v1547_pass"],
        "v1548-handoff-and-rollback-pass": evidence["manifest"]["pass"]
        and evidence["manifest"]["handoff_pass"]
        and evidence["manifest"]["rollback_ok"],
        "v1548-sysfs-writer-ok": alignment["trigger_mode"] == "sysfs_client_enumerate"
        and alignment["writer_rc"] == "0"
        and alignment["writer_errno"] == "0"
        and alignment["writer_sysfs_rc"] == "0",
        "v1548-fixed-rc1-no-l0": wp["rc1_progress"]
        and wp["rc1_link_failed"]
        and not wp["rc1_l0"]
        and evidence["dmesg"]["link_failed_ts"] is not None,
        "v1548-no-downstream": not wp["mhi_progress"]
        and not wp["wlfw_progress"]
        and not wp["bdf_progress"]
        and not wp["fw_ready_progress"]
        and not wp["wlan0_present"]
        and evidence["wlan0_absent"],
        "low-overhead-marker-contract-held": window["has_micro_critical"]
        and window["has_clk_skip"]
        and not window["has_micro_focused_clk"],
        "pre-fail-source-set-captured": {"micro_interrupts", "micro_debug_gpio", "micro_pcie1_current_link_state", "micro_pcie1_link_state", "micro_critical_regulator", "micro_critical_pinmux"}.issubset(set(window["pre_fail_sources"])),
        "pre-fail-gpio-no-endpoint-response": gpio["104"]["max"] == 0
        and irq["104"]["max"] == 0
        and gpio["142"]["max"] == 0
        and irq["142"]["max"] == 0,
        "pre-fail-ap2mdm-still-low": gpio["135"]["max"] == 0,
        "pre-fail-pcie1-gdsc-zero-observed": len(window["pcie_1_gdsc_zero_pre_fail_lines"]) > 0,
    }
    pass_ok = all(checks.values())
    return {
        "cycle": "V1549",
        "generated_at": now_iso(),
        "decision": (
            "v1549-low-overhead-confirms-pre-fail-gpio-gdsc-no-l0"
            if pass_ok
            else "v1549-low-overhead-result-needs-review"
        ),
        "pass": pass_ok,
        "reason": (
            "V1548 confirms the no-L0 endpoint gap with low-overhead pre-fail GPIO/GDSC evidence and no micro-focused clk_summary reads"
            if pass_ok
            else "one or more V1548 low-overhead fixed points did not match"
        ),
        "inputs": evidence["paths"],
        "host": collect_host_metadata(),
        "checks": checks,
        "evidence": evidence,
        "classification": {
            "active_blocker": "RC1 link training reaches PHY/POLL_COMPLIANCE but SDX50M endpoint never enters L0",
            "new_information": [
                "micro-focused clk_summary reads are removed from the critical loop",
                "fast pre-fail sources are captured before the link-fail marker",
                "GPIO104/WAKE and GPIO142/MDM2AP remain low with zero IRQ before failure",
                "GPIO135/AP2MDM remains low in captured debug GPIO samples before failure",
                "pcie_1_gdsc remains 0mV in pre-fail regulator-summary samples",
            ],
            "closed": [
                "V1543 ambiguity from slow micro_focused_clk reads",
                "blind sysfs/client enumerate retry",
                "firmware/MHI/WLFW/connect-side work before native L0",
            ],
            "next_focus": "host/source classifier for pcie1 power-domain and debugfs regulator semantics: why msm_pcie reaches PHY/LTSSM while regulator_summary still reports pcie_1_gdsc 0mV",
        },
        "safety": {
            "host_only_classifier": True,
            "device_commands_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "global_pci_rescan_executed": False,
            "platform_bind_unbind_executed": False,
            "boot_or_partition_write_executed": False,
        },
        "next_gate": {
            "cycle": "V1550",
            "summary": "host/source pcie1 power-domain semantics classifier before any new live mutation",
            "guardrails": [
                "no new enumerate retry unless the observer contract adds a new source",
                "no PMIC/GPIO/GDSC direct write",
                "no global PCI rescan or platform bind/unbind",
                "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
                "no firmware/MHI/WLFW branch until native L0 and PCI enumeration exist",
            ],
        },
    }


def render_report(result: dict[str, Any]) -> str:
    evidence = result["evidence"]
    window = evidence["window"]
    dmesg = evidence["dmesg"]
    alignment = evidence["alignment"]
    return "\n".join([
        "# Native Init V1549 Low-Overhead Result Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1549`",
        "- Type: host-only evidence classifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Reason: {result['reason']}",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "path"], [[name, path] for name, path in result["inputs"].items()]),
        "",
        "## Checks",
        "",
        markdown_table(["check", "value"], [[name, value] for name, value in result["checks"].items()]),
        "",
        "## RC1 Alignment",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["detect ts / elapsed ms", f"{alignment['detect_ts']} / {alignment['detect_elapsed_ms']}"],
                ["link failed ts / elapsed ms", f"{alignment['link_failed_ts']} / {alignment['link_failed_elapsed_ms']}"],
                ["writer sysfs elapsed ms", alignment["writer_sysfs_elapsed_ms"]],
                ["trigger mode", alignment["trigger_mode"]],
                ["RC1 assert / PHY ready / release", f"{dmesg['rc1_assert_ts']} / {dmesg['rc1_phy_ready_ts']} / {dmesg['rc1_release_ts']}"],
                ["poll compliance / link failed", f"{dmesg['poll_compliance_ts']} / {dmesg['link_failed_ts']}"],
                ["L0 / downstream", f"{dmesg['has_l0']} / {dmesg['has_downstream']}"],
            ],
        ),
        "",
        "## Pre-Fail Evidence",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["pre-fail end rows", window["pre_fail_end_row_count"]],
                ["pre-fail sources", ", ".join(window["pre_fail_sources"])],
                ["max pre-fail source duration ms", window["max_pre_fail_source_duration_ms"]],
                ["GPIO104 max / IRQ104 max", f"{window['gpio_pre_fail']['104']['max']} / {window['irq_pre_fail']['104']['max']}"],
                ["GPIO135 max", window["gpio_pre_fail"]["135"]["max"]],
                ["GPIO142 max / IRQ142 max", f"{window['gpio_pre_fail']['142']['max']} / {window['irq_pre_fail']['142']['max']}"],
                ["pcie_1_gdsc zero pre-fail lines", len(window["pcie_1_gdsc_zero_pre_fail_lines"])],
                ["micro focused clk present", window["has_micro_focused_clk"]],
                ["critical clk skip present", window["has_clk_skip"]],
            ],
        ),
        "",
        "## Key Dmesg Lines",
        "",
        "\n".join(f"- `{line}`" for line in dmesg["key_lines"]),
        "",
        "## Key Window Lines",
        "",
        "\n".join(f"- `{line}`" for line in window["key_lines"]),
        "",
        "## Interpretation",
        "",
        "V1548 removes the slow `micro_focused_clk` ambiguity from V1543 and still reproduces the same fixed native failure: RC1 reaches PHY/LTSSM and fails at `LTSSM_POLL_COMPLIANCE` without L0. The low-overhead sampler captures pre-fail interrupts, GPIO, link-state files, regulator summary, and pinmux before the dmesg link-fail timestamp. Within those pre-fail samples, GPIO104/WAKE and GPIO142/MDM2AP remain low with zero IRQ, GPIO135/AP2MDM remains low in debug GPIO, and `pcie_1_gdsc` is still reported as 0mV.",
        "",
        "The next useful step is not another enumerate retry. It is a host/source classifier for pcie1 power-domain semantics and debugfs regulator visibility: explain how `msm_pcie` reaches PHY/LTSSM while `regulator_summary` still reports `pcie_1_gdsc` as 0mV, then decide whether a narrower live observer is needed.",
        "",
        "## Next Gate",
        "",
        f"- Cycle: `{result['next_gate']['cycle']}`",
        f"- Summary: {result['next_gate']['summary']}",
        *(f"- Guardrail: {item}" for item in result["next_gate"]["guardrails"]),
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, global PCI rescan, or platform bind/unbind.",
        "",
    ])


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
    result["out_dir"] = str(store.run_dir)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(args.report_path), report)
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "next_gate": result["next_gate"]["cycle"],
                "out_dir": rel(args.out_dir),
                "pass": result["pass"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
