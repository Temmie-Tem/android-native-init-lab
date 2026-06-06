#!/usr/bin/env python3
"""V1544 host-only classifier for the V1543 endpoint-electrical handoff."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1544-endpoint-electrical-result-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1544_ENDPOINT_ELECTRICAL_RESULT_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1544-endpoint-electrical-result-classifier.txt")

V1543_DIR = Path("tmp/wifi/v1543-endpoint-electrical-handoff")
V1543_MANIFEST = V1543_DIR / "manifest.json"
V1543_DMESG = V1543_DIR / "test-v1393-dmesg.stdout.txt"
V1543_WINDOW = V1543_DIR / "test-rc1-window-result.stdout.txt"
V1543_WLAN0 = V1543_DIR / "test-wlan0.stdout.txt"
V1542_MANIFEST = Path("tmp/wifi/v1542-endpoint-electrical-artifact-sanity/manifest.json")
V1540_MANIFEST = Path("tmp/wifi/v1540-endpoint-readiness-classifier/manifest.json")


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


def first_ts(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\[\s*([0-9]+\.[0-9]+)\]", line)
        if match:
            return float(match.group(1))
    return None


def first_payload_line(text: str, prefix: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped
    return ""


def parse_kv_line(line: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in re.finditer(r"([A-Za-z0-9_.-]+)=([^ \t\r\n]+)", line):
        values[match.group(1)] = match.group(2)
    return values


def matching_lines(text: str, pattern: str, limit: int = 24) -> list[str]:
    regex = re.compile(pattern, re.I)
    return [line.strip() for line in text.splitlines() if regex.search(line)][:limit]


def gpio_level_values(text: str, gpio: int) -> list[int]:
    values: list[int] = []
    regex = re.compile(rf"\bgpio{gpio}\s*:\s*(?:in|out)\s+([01])\b")
    for match in regex.finditer(text):
        values.append(int(match.group(1)))
    return values


def irq_totals(text: str, gpio: int) -> list[int]:
    totals: list[int] = []
    for line in text.splitlines():
        if f"msmgpio-dc {gpio}" not in line and f"msmgpio-dc  {gpio}" not in line:
            continue
        prefix = line.split("msmgpio-dc", 1)[0]
        numbers = [int(value) for value in re.findall(r"\b\d+\b", prefix)]
        if len(numbers) > 1:
            totals.append(sum(numbers[1:]))
    return totals


def source_timing_rows(text: str, source: str) -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    regex = re.compile(
        rf"sample=([^ ]+)\s+source={re.escape(source)}\s+source_timing=(begin|end)"
        r".*?elapsed_ms=(-?\d+).*?micro_elapsed_ms=(-?\d+).*?source_duration_ms=(-?\d+)"
    )
    for line in text.splitlines():
        match = regex.search(line)
        if match:
            rows.append(
                {
                    "sample": match.group(1),
                    "phase": match.group(2),
                    "elapsed_ms": int(match.group(3)),
                    "micro_elapsed_ms": int(match.group(4)),
                    "source_duration_ms": int(match.group(5)),
                }
            )
    return rows


def clock_matches(text: str, needle: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if f"source=micro_focused_clk needle={needle} " in line
        or f"source=focused_clk needle={needle} " in line
    ]


def all_clock_lines_disabled(lines: list[str]) -> bool:
    if not lines:
        return False
    return all(re.search(r"\bmatch=\s+\S+\s+0\s+0\s+", line) is not None for line in lines)


def regulator_zero_lines(text: str, needle: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if f"needle={needle} " in line and "0mV" in line
        or f" {needle} " in line and "0mV" in line
    ]


def analyze() -> dict[str, Any]:
    manifest = read_json(V1543_MANIFEST)
    v1542 = read_json(V1542_MANIFEST)
    v1540 = read_json(V1540_MANIFEST)
    dmesg = read_text(V1543_DMESG)
    window = read_text(V1543_WINDOW)
    wlan0 = read_text(V1543_WLAN0)
    wp = manifest.get("wifi_progress") if isinstance(manifest.get("wifi_progress"), dict) else {}
    rollback = manifest.get("rollback") if isinstance(manifest.get("rollback"), dict) else {}
    writer_line = first_payload_line(window, "rc1_micro_writer_summary")
    writer_kv = parse_kv_line(writer_line)
    clk_timing = source_timing_rows(window, "micro_focused_clk")
    clk_begin = [row for row in clk_timing if row["phase"] == "begin"]
    clk_end = [row for row in clk_timing if row["phase"] == "end"]
    pcie1_clock_needles = (
        "gcc_pcie_1_pipe_clk",
        "gcc_pcie_1_clkref_clk",
        "gcc_pcie_1_cfg_ahb_clk",
        "gcc_pcie_1_mstr_axi_clk",
        "gcc_pcie_1_slv_axi_clk",
        "gcc_pcie_1_slv_q2a_axi_clk",
        "gcc_pcie1_phy_refgen_clk",
    )
    clock_summary = {
        needle: {
            "lines": len(clock_matches(window, needle)),
            "disabled": all_clock_lines_disabled(clock_matches(window, needle)),
            "examples": clock_matches(window, needle)[:2],
        }
        for needle in pcie1_clock_needles
    }
    gpio_summary = {
        str(gpio): {
            "samples": len(gpio_level_values(window, gpio)),
            "max": max(gpio_level_values(window, gpio)) if gpio_level_values(window, gpio) else None,
        }
        for gpio in (102, 103, 104, 135, 142)
    }
    irq_summary = {
        str(gpio): {
            "samples": len(irq_totals(window, gpio)),
            "max": max(irq_totals(window, gpio)) if irq_totals(window, gpio) else None,
        }
        for gpio in (104, 142)
    }
    first_clk_begin_ms = min((int(row["micro_elapsed_ms"]) for row in clk_begin), default=None)
    max_clk_duration_ms = max((int(row["source_duration_ms"]) for row in clk_end), default=None)
    return {
        "paths": {
            "manifest": rel(V1543_MANIFEST),
            "dmesg": rel(V1543_DMESG),
            "window": rel(V1543_WINDOW),
            "wlan0": rel(V1543_WLAN0),
            "v1542_manifest": rel(V1542_MANIFEST),
            "v1540_manifest": rel(V1540_MANIFEST),
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
            "v1542_pass": bool(v1542.get("pass")),
            "v1540_decision": v1540.get("decision"),
            "v1540_pass": bool(v1540.get("pass")),
        },
        "writer": {
            "line": writer_line,
            "trigger_mode": writer_kv.get("trigger_mode"),
            "rc": writer_kv.get("rc"),
            "errno": writer_kv.get("errno"),
            "sysfs_rc": writer_kv.get("sysfs_rc"),
            "sysfs_elapsed_ms": writer_kv.get("sysfs_elapsed_ms"),
        },
        "dmesg": {
            "rc1_assert_ts": first_ts(dmesg, r"Assert the reset of endpoint of RC1"),
            "rc1_phy_ready_ts": first_ts(dmesg, r"PCIe RC1 PHY is ready"),
            "rc1_release_ts": first_ts(dmesg, r"Release the reset of endpoint of RC1"),
            "poll_compliance_ts": first_ts(dmesg, r"LTSSM_POLL_COMPLIANCE"),
            "link_failed_ts": first_ts(dmesg, r"link initialization failed"),
            "has_l0": bool(re.search(r"LTSSM_STATE:\s+LTSSM_L0|Current GEN", dmesg)),
            "has_mhi_wlfw_wlan0": bool(re.search(r"mhi_0305|/dev/mhi|wlfw|BDF|FW ready|wlan0", dmesg, re.I)),
            "key_lines": matching_lines(
                dmesg,
                r"Assert the reset of endpoint of RC1|PHY is ready|Release the reset|LTSSM_STATE|link initialization failed|failed to enable RC1",
                32,
            ),
        },
        "window": {
            "gpio": gpio_summary,
            "irq": irq_summary,
            "pcie_1_gdsc_zero_lines": len(regulator_zero_lines(window, "pcie_1_gdsc")),
            "clock_summary": clock_summary,
            "micro_focused_clk_begin_rows": len(clk_begin),
            "first_clk_begin_micro_elapsed_ms": first_clk_begin_ms,
            "max_clk_source_duration_ms": max_clk_duration_ms,
            "wlan0_absent": "wlan0=absent" in wlan0,
            "key_lines": matching_lines(
                window,
                r"rc1_micro_writer_summary|micro_focused_clk source_timing|gcc_pcie_1_pipe_clk|gcc_pcie_1_clkref_clk|gcc_pcie1_phy_refgen_clk|pcie_1_gdsc|gpio102\s*:|gpio103\s*:|gpio104\s*:|gpio135\s*:|gpio142\s*:|msmgpio-dc\s+142",
                36,
            ),
        },
    }


def classify() -> dict[str, Any]:
    evidence = analyze()
    wp = evidence["manifest"]["wifi_progress"]
    clocks = evidence["window"]["clock_summary"]
    checks = {
        "v1542-artifact-sanity-pass": evidence["prior"]["v1542_pass"],
        "v1543-handoff-and-rollback-pass": evidence["manifest"]["pass"]
        and evidence["manifest"]["handoff_pass"]
        and evidence["manifest"]["rollback_ok"],
        "v1543-sysfs-write-ok": evidence["writer"]["trigger_mode"] == "sysfs_client_enumerate"
        and evidence["writer"]["rc"] == "0"
        and evidence["writer"]["errno"] == "0"
        and evidence["writer"]["sysfs_rc"] == "0",
        "v1543-fixed-rc1-no-l0": wp["rc1_progress"]
        and wp["rc1_link_failed"]
        and not wp["rc1_l0"]
        and evidence["dmesg"]["link_failed_ts"] is not None,
        "v1543-no-downstream": not wp["mhi_progress"]
        and not wp["wlfw_progress"]
        and not wp["bdf_progress"]
        and not wp["fw_ready_progress"]
        and not wp["wlan0_present"]
        and evidence["window"]["wlan0_absent"],
        "v1543-fast-gpio-no-endpoint-response": evidence["window"]["gpio"]["142"]["max"] == 0
        and evidence["window"]["irq"]["142"]["max"] == 0
        and evidence["window"]["gpio"]["104"]["max"] == 0
        and evidence["window"]["irq"]["104"]["max"] == 0,
        "v1543-gdsc-zero-observed": evidence["window"]["pcie_1_gdsc_zero_lines"] > 0,
        "v1543-focused-clock-lines-present": all(item["lines"] > 0 for item in clocks.values()),
        "v1543-focused-clock-lines-disabled": all(item["disabled"] for item in clocks.values()),
        "v1543-clk-summary-too-slow-for-pre-fail-proof": (
            evidence["window"]["first_clk_begin_micro_elapsed_ms"] is not None
            and evidence["window"]["first_clk_begin_micro_elapsed_ms"] >= 100
            and evidence["window"]["max_clk_source_duration_ms"] is not None
            and evidence["window"]["max_clk_source_duration_ms"] >= 500
        ),
    }
    pass_ok = all(checks.values())
    result: dict[str, Any] = {
        "cycle": "V1544",
        "generated_at": now_iso(),
        "decision": (
            "v1544-endpoint-electrical-confirms-no-l0-gpio-gdsc-zero-clk-postfail"
            if pass_ok
            else "v1544-endpoint-electrical-result-needs-review"
        ),
        "pass": pass_ok,
        "reason": (
            "V1543 confirms the no-L0 endpoint gap and captures GPIO/GDSC/clock evidence; focused clk_summary lines are disabled but too slow to prove the pre-fail sub-120ms clock state"
            if pass_ok
            else "one or more V1543 endpoint-electrical fixed points did not match the expected model"
        ),
        "inputs": evidence["paths"],
        "host": collect_host_metadata(),
        "checks": checks,
        "evidence": evidence,
        "classification": {
            "active_blocker": "native RC1 enters LTSSM polling/compliance but SDX50M endpoint still does not reach L0",
            "new_information": [
                "micro-focused observer captured pcie_1 clock/refgen lines",
                "all captured pcie_1 focused clock lines report disabled counts",
                "pcie_1_gdsc remains at 0mV in captured regulator lines",
                "GPIO104/WAKE and GPIO142/MDM2AP stay low with zero IRQ count",
                "clk_summary is too slow for a definitive pre-fail clock-state proof",
            ],
            "closed": [
                "AP-side sysfs/client enumerate writer",
                "firmware/MHI/WLFW/connect-side work before native L0",
                "blind enumerate retry without a new endpoint input",
            ],
            "next_focus": "fast pre-fail endpoint-state proof that avoids slow clk_summary in the critical loop, or a different low-overhead source for pcie1 clock/GDSC/refclk state",
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
            "esoc_notify_boot_done_spoof_executed": False,
            "global_pci_rescan_executed": False,
            "platform_bind_unbind_executed": False,
            "boot_or_partition_write_executed": False,
        },
        "next_gate": {
            "cycle": "V1545",
            "summary": "host/source classifier for a low-overhead pre-fail endpoint-state observer that does not read full clk_summary inside the sub-120ms RC1 window",
            "guardrails": [
                "no new enumerate retry until the observer contract is narrower than V1543",
                "no PMIC/GPIO/GDSC direct write",
                "no global PCI rescan or platform bind/unbind",
                "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
                "no firmware/MHI/WLFW branch until native L0 and PCI enumeration exist",
            ],
        },
    }
    return result


def render_report(result: dict[str, Any]) -> str:
    evidence = result["evidence"]
    window = evidence["window"]
    dmesg = evidence["dmesg"]
    return "\n".join([
        "# Native Init V1544 Endpoint Electrical Result Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1544`",
        "- Type: host-only evidence classifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Reason: {result['reason']}",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "path"], [[name, path] for name, path in result["inputs"].items()]),
        "",
        "## Fixed-Point Checks",
        "",
        markdown_table(["check", "value"], [[name, value] for name, value in result["checks"].items()]),
        "",
        "## RC1 Outcome",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["RC1 assert / PHY ready / release", f"{dmesg['rc1_assert_ts']} / {dmesg['rc1_phy_ready_ts']} / {dmesg['rc1_release_ts']}"],
                ["poll compliance / link failed", f"{dmesg['poll_compliance_ts']} / {dmesg['link_failed_ts']}"],
                ["L0", dmesg["has_l0"]],
                ["MHI/WLFW/wlan0 dmesg text", dmesg["has_mhi_wlfw_wlan0"]],
                ["wlan0 absent output", window["wlan0_absent"]],
            ],
        ),
        "",
        "## Endpoint Electrical Summary",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["GPIO102 max", window["gpio"]["102"]["max"]],
                ["GPIO103 max", window["gpio"]["103"]["max"]],
                ["GPIO104 max / IRQ max", f"{window['gpio']['104']['max']} / {window['irq']['104']['max']}"],
                ["GPIO135 max", window["gpio"]["135"]["max"]],
                ["GPIO142 max / IRQ max", f"{window['gpio']['142']['max']} / {window['irq']['142']['max']}"],
                ["pcie_1_gdsc zero lines", window["pcie_1_gdsc_zero_lines"]],
                ["focused clk first begin micro ms", window["first_clk_begin_micro_elapsed_ms"]],
                ["focused clk max duration ms", window["max_clk_source_duration_ms"]],
            ],
        ),
        "",
        "## Focused Clock Lines",
        "",
        markdown_table(
            ["clock", "lines", "disabled", "example"],
            [
                [name, data["lines"], data["disabled"], (data["examples"] or [""])[0]]
                for name, data in window["clock_summary"].items()
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
        "V1543 confirms the V1540 endpoint-readiness model under a live rollbackable handoff. The sysfs/client enumerate write still reaches RC1 PHY/LTSSM and fails before L0. GPIO104/WAKE and GPIO142/MDM2AP remain low with zero IRQ count, `pcie_1_gdsc` remains 0mV in captured regulator lines, and no MHI/WLFW/BDF/FW-ready/`wlan0` appears.",
        "",
        "The new micro-focused `clk_summary` evidence is useful but not definitive for the sub-120ms pre-fail clock state: the first focused clock read begins at about +117ms and each full `clk_summary` read takes hundreds of milliseconds. Therefore it proves the captured/post-fail focused clock lines are disabled, but it should not be treated as a precise pre-fail clock transition trace.",
        "",
        "## Next Gate",
        "",
        f"- Cycle: `{result['next_gate']['cycle']}`",
        f"- Summary: {result['next_gate']['summary']}",
        *(f"- Guardrail: {item}" for item in result["next_gate"]["guardrails"]),
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.",
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
                "pass": result["pass"],
                "out_dir": rel(args.out_dir),
                "next_gate": result["next_gate"]["cycle"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
