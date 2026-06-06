#!/usr/bin/env python3
"""V1539 host-only classifier for the V1538 sysfs/client enumerate handoff."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1539-sysfs-enumerate-result-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1539_SYSFS_ENUMERATE_RESULT_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1539-sysfs-enumerate-result-classifier.txt")

V1538_DIR = Path("tmp/wifi/v1538-wifi-sysfs-client-enumerate-handoff")
V1538_MANIFEST = V1538_DIR / "manifest.json"
V1538_WATCHER = V1538_DIR / "test-v1393-rc1-watcher-result.stdout.txt"
V1538_WINDOW = V1538_DIR / "test-rc1-window-result.stdout.txt"
V1538_DMESG = V1538_DIR / "test-v1393-dmesg.stdout.txt"
V1538_WLAN0 = V1538_DIR / "test-wlan0.stdout.txt"
V1535_MANIFEST = Path("tmp/wifi/v1535-first-l0-trigger-candidate-classifier/manifest.json")
V1523_MANIFEST = Path("tmp/wifi/v1523-msm-pcie-test11-vs-normal-path-classifier/manifest.json")


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


def first_payload_line(text: str, prefix: str | None = None) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if prefix is None:
            if stripped.startswith("a90:/#") or stripped.startswith("A90P1 ") or stripped.startswith("run: "):
                continue
            return stripped
        if stripped.startswith(prefix):
            return stripped
    return ""


def parse_kv_line(line: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in re.finditer(r"([A-Za-z0-9_.-]+)=([^ \t\r\n]+)", line):
        values[match.group(1)] = match.group(2)
    return values


def matching_lines(text: str, pattern: str, limit: int = 20) -> list[str]:
    regex = re.compile(pattern, re.I)
    return [line.strip() for line in text.splitlines() if regex.search(line)][:limit]


def bool_path(data: dict[str, Any], *keys: str) -> bool:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return False
        current = current.get(key)
    return bool(current)


def micro_labels(text: str) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"^rc1_micro_sample\s+label=([^ \t\r\n]+)", text, re.M):
        label = match.group(1)
        if label not in seen:
            labels.append(label)
            seen.add(label)
    return labels


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
        values = [int(value) for value in re.findall(r"\b\d+\b", prefix)]
        if len(values) > 1:
            totals.append(sum(values[1:]))
    return totals


def pcie1_gdsc_rows(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if "pcie_1_gdsc" in line]


def analyze_v1538() -> dict[str, Any]:
    manifest = read_json(V1538_MANIFEST)
    watcher_text = read_text(V1538_WATCHER)
    window_text = read_text(V1538_WINDOW)
    dmesg_text = read_text(V1538_DMESG)
    wlan0_text = read_text(V1538_WLAN0)

    watcher_line = first_payload_line(watcher_text, "state=")
    writer_line = first_payload_line(window_text, "rc1_micro_writer_summary")
    window_header = first_payload_line(window_text, "state=")
    watcher_kv = parse_kv_line(watcher_line)
    writer_kv = parse_kv_line(writer_line)
    window_kv = parse_kv_line(window_header)
    wp = manifest.get("wifi_progress") if isinstance(manifest.get("wifi_progress"), dict) else {}
    rollback = manifest.get("rollback") if isinstance(manifest.get("rollback"), dict) else {}
    labels = micro_labels(window_text)
    gpio135 = gpio_level_values(window_text, 135)
    gpio142 = gpio_level_values(window_text, 142)
    gpio104_irq = irq_totals(window_text, 104)
    gpio142_irq = irq_totals(window_text, 142)
    gdsc_rows = pcie1_gdsc_rows(window_text)

    return {
        "paths": {
            "manifest": rel(V1538_MANIFEST),
            "watcher": rel(V1538_WATCHER),
            "window": rel(V1538_WINDOW),
            "dmesg": rel(V1538_DMESG),
            "wlan0": rel(V1538_WLAN0),
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
                "rc1_failure_markers": wp.get("rc1_failure_markers") or [],
            },
            "rollback_verifier_uses_selftest": any(
                isinstance(step, dict)
                and step.get("ok") is True
                and isinstance(step.get("command"), list)
                and "--verify-protocol" in step["command"]
                and "selftest" in step["command"]
                and str(step["command"][2]).endswith("stage3/boot_linux_v724.img")
                for step in manifest.get("steps", [])
            ),
        },
        "watcher": {
            "line": watcher_line,
            "state": watcher_kv.get("state"),
            "trigger_mode": watcher_kv.get("trigger_mode"),
            "write_rc": watcher_kv.get("write_rc"),
            "errno": watcher_kv.get("errno"),
            "detect_elapsed_ms": watcher_kv.get("detect_elapsed_ms"),
            "write_elapsed_ms": watcher_kv.get("write_elapsed_ms"),
        },
        "window": {
            "header": window_header,
            "writer": writer_line,
            "sysfs_client_enumerate": window_kv.get("sysfs_client_enumerate"),
            "trigger_mode": window_kv.get("trigger_mode"),
            "writer_rc": writer_kv.get("rc"),
            "writer_errno": writer_kv.get("errno"),
            "sysfs_rc": writer_kv.get("sysfs_rc"),
            "sysfs_path": writer_kv.get("sysfs_path"),
            "sample_count": len(labels),
            "sample_labels": labels,
            "gpio135_samples": len(gpio135),
            "gpio135_max": max(gpio135) if gpio135 else None,
            "gpio142_samples": len(gpio142),
            "gpio142_max": max(gpio142) if gpio142 else None,
            "gpio104_irq_samples": len(gpio104_irq),
            "gpio104_irq_max": max(gpio104_irq) if gpio104_irq else None,
            "gpio142_irq_samples": len(gpio142_irq),
            "gpio142_irq_max": max(gpio142_irq) if gpio142_irq else None,
            "pcie1_gdsc_samples": len(gdsc_rows),
            "pcie1_gdsc_has_nonzero": any(" 0mV " not in f" {row} " for row in gdsc_rows),
            "key_lines": matching_lines(
                window_text,
                r"rc1_micro_writer_summary|gpio135\s*:|gpio142\s*:|msmgpio-dc\s+142|pcie_1_gdsc|pin 102|pin 135|pin 142",
                24,
            ),
        },
        "dmesg": {
            "has_provider_trigger": bool(re.search(r"__subsystem_get.*esoc0|mdm_subsys_powerup|cnss-daemon", dmesg_text, re.I)),
            "has_rc1_assert": "Assert the reset of endpoint of RC1" in dmesg_text,
            "has_rc1_release": "Release the reset of endpoint of RC1" in dmesg_text,
            "has_phy_ready": "PCIe RC1 PHY is ready" in dmesg_text,
            "has_poll_active": "LTSSM_POLL_ACTIVE" in dmesg_text,
            "has_poll_compliance": "LTSSM_POLL_COMPLIANCE" in dmesg_text,
            "has_l0": bool(re.search(r"LTSSM_STATE:\s+LTSSM_L0|Current GEN", dmesg_text)),
            "has_link_failed": "PCIe RC1 link initialization failed" in dmesg_text,
            "has_mhi_after_boot": bool(
                re.search(r"\bmhi_(?!region\b)|/dev/mhi|mhi_0305|MHI", dmesg_text)
            ),
            "has_wlfw": bool(re.search(r"\bwlfw|WLFW|icnss_qmi", dmesg_text)),
            "has_bdf": bool(re.search(r"\bBDF\b|bdwlan|regdb", dmesg_text)),
            "has_fw_ready": bool(re.search(r"FW ready|fw_ready", dmesg_text)),
            "has_wlan0": "wlan0" in dmesg_text,
            "key_lines": matching_lines(
                dmesg_text,
                r"__subsystem_get.*esoc0|msm_pcie_enable: PCIe|LTSSM_STATE|link initialization failed|msm_pcie_enumerate|mhi_0305|/dev/mhi|wlfw|BDF|FW ready|wlan0",
                32,
            ),
        },
        "wlan0_text_has_absent": "wlan0=absent" in wlan0_text,
    }


def classify() -> dict[str, Any]:
    v1538 = analyze_v1538()
    v1535 = read_json(V1535_MANIFEST)
    v1523 = read_json(V1523_MANIFEST)
    wp = v1538["manifest"]["wifi_progress"]
    checks = {
        "v1538-handoff-pass": v1538["manifest"]["pass"] and v1538["manifest"]["handoff_pass"],
        "v1538-rollback-pass": v1538["manifest"]["rollback_ok"]
        and v1538["manifest"]["rollback_verifier_uses_selftest"],
        "v1538-sysfs-watcher-triggered": v1538["watcher"]["state"] == "triggered"
        and v1538["watcher"]["trigger_mode"] == "sysfs_client_enumerate",
        "v1538-sysfs-write-ok": v1538["watcher"]["write_rc"] == "0"
        and v1538["watcher"]["errno"] == "0"
        and v1538["window"]["sysfs_rc"] == "0",
        "v1538-window-contract-sysfs": v1538["window"]["sysfs_client_enumerate"] == "1"
        and v1538["window"]["trigger_mode"] == "sysfs_client_enumerate",
        "v1538-rc1-progress-no-l0": wp["rc1_progress"]
        and not wp["rc1_l0"]
        and wp["rc1_link_failed"]
        and v1538["dmesg"]["has_rc1_assert"]
        and v1538["dmesg"]["has_phy_ready"],
        "v1538-poll-compliance-link-failed": v1538["dmesg"]["has_poll_compliance"]
        and v1538["dmesg"]["has_link_failed"]
        and not v1538["dmesg"]["has_l0"],
        "v1538-no-downstream-wifi": not wp["mhi_progress"]
        and not wp["wlfw_progress"]
        and not wp["bdf_progress"]
        and not wp["fw_ready_progress"]
        and not wp["wlan0_present"]
        and not wp["connect_ready"]
        and v1538["wlan0_text_has_absent"],
        "v1535-expected-prior-gate": v1535.get("decision")
        == "v1535-first-l0-candidates-narrowed-to-client-enumerate-or-endpoint-readiness",
        "v1523-common-enumerate-prior": v1523.get("decision")
        == "v1523-test11-shares-enable-normal-trigger-readiness-gap",
    }
    pass_ok = all(checks.values())
    result: dict[str, Any] = {
        "cycle": "V1539",
        "generated_at": now_iso(),
        "decision": (
            "v1539-sysfs-client-enumerate-closes-ap-side-trigger-no-l0"
            if pass_ok
            else "v1539-sysfs-client-enumerate-result-needs-review"
        ),
        "pass": pass_ok,
        "reason": (
            "targeted pci-msm sysfs/client enumerate write succeeded and produced the same RC1 PHY/LTSSM progress but still failed before L0, closing AP-side caller semantics as the active blocker"
            if pass_ok
            else "one or more V1538 fixed points did not match the sysfs enumerate no-L0 model"
        ),
        "inputs": {
            "v1538_manifest": rel(V1538_MANIFEST),
            "v1538_watcher": rel(V1538_WATCHER),
            "v1538_window": rel(V1538_WINDOW),
            "v1538_dmesg": rel(V1538_DMESG),
            "v1538_wlan0": rel(V1538_WLAN0),
            "v1535_manifest": rel(V1535_MANIFEST),
            "v1523_manifest": rel(V1523_MANIFEST),
        },
        "host": collect_host_metadata(),
        "checks": checks,
        "evidence": {"v1538": v1538},
        "classification": {
            "closed_as_active_gap": [
                "targeted sysfs/client enumerate caller path",
                "debugfs TEST:11 caller semantics",
                "probe-time enumerate as active first-L0 caller",
                "MHI PM-resume as first-L0 trigger",
                "visible ICNSS workqueue line as first-L0 trigger",
            ],
            "active_blocker": "SDX50M endpoint readiness/electrical/reset/refclk/PERST response gap before PCIe RC1 L0",
            "fixed_native_failure": "RC1 PHY/LTSSM progresses to polling/compliance, then link initialization fails without L0",
            "firmware_mhi_wlfw_scan_connect_deferred_until_native_l0": True,
            "ap_side_caller_semantics_empirically_closed": pass_ok,
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
            "cycle": "V1540",
            "summary": "host-only endpoint-readiness/electrical classifier focused on PERST/refclk/GDSC/reset/GPIO135/GPIO142 after sysfs-client enumerate closed AP-side caller semantics",
            "guardrails": [
                "no further PCIe enumerate retry until a new endpoint-readiness input is identified",
                "no PMIC/GPIO/GDSC direct write",
                "no global PCI rescan or platform bind/unbind",
                "no Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, or external ping",
                "no firmware/MHI/WLFW deep dive until native RC1 L0 and PCI enumeration exist",
            ],
        },
    }
    return result


def render_report(result: dict[str, Any]) -> str:
    v1538 = result["evidence"]["v1538"]
    wp = v1538["manifest"]["wifi_progress"]
    return "\n".join(
        [
            "# Native Init V1539 Sysfs Enumerate Result Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1539`",
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
            "## V1538 Handoff Outcome",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["manifest decision", v1538["manifest"]["decision"]],
                    ["handoff pass", v1538["manifest"]["handoff_pass"]],
                    ["rollback ok", v1538["manifest"]["rollback_ok"]],
                    ["rollback verifier uses selftest", v1538["manifest"]["rollback_verifier_uses_selftest"]],
                    ["progress decision", wp["final_decision"]],
                    ["provider trigger", wp["provider_trigger"]],
                    ["modem trigger", wp["modem_trigger"]],
                    ["RC1 progress", wp["rc1_progress"]],
                    ["RC1 L0", wp["rc1_l0"]],
                    ["RC1 link failed", wp["rc1_link_failed"]],
                    ["MHI/WLFW/BDF/FW-ready/wlan0/connect", f"{wp['mhi_progress']}/{wp['wlfw_progress']}/{wp['bdf_progress']}/{wp['fw_ready_progress']}/{wp['wlan0_present']}/{wp['connect_ready']}"],
                ],
            ),
            "",
            "## Sysfs Enumerate Evidence",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["watcher state", v1538["watcher"]["state"]],
                    ["watcher trigger mode", v1538["watcher"]["trigger_mode"]],
                    ["watcher write rc/errno", f"{v1538['watcher']['write_rc']}/{v1538['watcher']['errno']}"],
                    ["writer sysfs path", v1538["window"]["sysfs_path"]],
                    ["writer rc/errno/sysfs_rc", f"{v1538['window']['writer_rc']}/{v1538['window']['writer_errno']}/{v1538['window']['sysfs_rc']}"],
                    ["micro sample count", v1538["window"]["sample_count"]],
                    ["GPIO135 samples/max", f"{v1538['window']['gpio135_samples']}/{v1538['window']['gpio135_max']}"],
                    ["GPIO142 samples/max", f"{v1538['window']['gpio142_samples']}/{v1538['window']['gpio142_max']}"],
                    ["GPIO142 IRQ samples/max", f"{v1538['window']['gpio142_irq_samples']}/{v1538['window']['gpio142_irq_max']}"],
                    ["pcie1 GDSC samples/nonzero", f"{v1538['window']['pcie1_gdsc_samples']}/{v1538['window']['pcie1_gdsc_has_nonzero']}"],
                ],
            ),
            "",
            "## RC1 Dmesg Evidence",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["provider trigger text", v1538["dmesg"]["has_provider_trigger"]],
                    ["RC1 assert/release", f"{v1538['dmesg']['has_rc1_assert']}/{v1538['dmesg']['has_rc1_release']}"],
                    ["PHY ready", v1538["dmesg"]["has_phy_ready"]],
                    ["poll active/compliance", f"{v1538['dmesg']['has_poll_active']}/{v1538['dmesg']['has_poll_compliance']}"],
                    ["L0", v1538["dmesg"]["has_l0"]],
                    ["link failed", v1538["dmesg"]["has_link_failed"]],
                    ["MHI/WLFW/BDF/FW-ready/wlan0 text", f"{v1538['dmesg']['has_mhi_after_boot']}/{v1538['dmesg']['has_wlfw']}/{v1538['dmesg']['has_bdf']}/{v1538['dmesg']['has_fw_ready']}/{v1538['dmesg']['has_wlan0']}"],
                ],
            ),
            "",
            "## Key RC1 Lines",
            "",
            "\n".join(f"- `{line}`" for line in v1538["dmesg"]["key_lines"]),
            "",
            "## Key Window Lines",
            "",
            "\n".join(f"- `{line}`" for line in v1538["window"]["key_lines"]),
            "",
            "## Interpretation",
            "",
            "V1538 empirically closes the remaining AP-side caller question from V1535. The sysfs/client enumerate writer targeted `/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate`, returned success, and still produced the fixed native failure: RC1 PHY/LTSSM progress reaches polling/compliance but never reaches L0.",
            "",
            "This means repeating enumerate paths is not the next useful action. The active blocker is below the AP-side caller and before firmware/MHI/WLFW: endpoint readiness/electrical/reset/refclk/PERST response around SDX50M and RC1. Firmware inventory, MHI pipe, WLFW, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain deferred until native RC1 reaches L0 and a PCI device exists.",
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
        ]
    )


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
