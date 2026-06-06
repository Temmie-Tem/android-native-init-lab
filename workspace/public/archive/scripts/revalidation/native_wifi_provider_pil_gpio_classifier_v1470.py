#!/usr/bin/env python3
"""V1470 host-only classifier for V1469 provider PIL+GPIO evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_V1469_DIR = REPO_ROOT / "tmp" / "wifi" / "v1469-wifi-test-boot-exact-provider-pil-gpio-tracepoint-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1470_PROVIDER_PIL_GPIO_CLASSIFIER_2026-06-01.md"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1470-provider-pil-gpio-classifier"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    return json.loads(text)


def parse_trace(window_text: str) -> dict[str, Any]:
    pil_events: list[dict[str, Any]] = []
    gpio_events: list[dict[str, Any]] = []
    pil_seen: set[tuple[float, str, int, str]] = set()
    gpio_seen: set[tuple[float, str, int, str]] = set()
    for line in window_text.splitlines():
        pil = re.search(
            r"(?P<time>\d+\.\d+): pil_notif: event_name=(?P<event>\S+) code=(?P<code>\d+) fw=(?P<fw>\S+)",
            line,
        )
        if pil:
            key = (float(pil.group("time")), pil.group("event"), int(pil.group("code")), pil.group("fw"))
            if key in pil_seen:
                continue
            pil_seen.add(key)
            pil_events.append({
                "time": key[0],
                "event": pil.group("event"),
                "code": key[2],
                "fw": pil.group("fw"),
            })
        gpio = re.search(
            r"(?P<time>\d+\.\d+): gpio_(?P<kind>value|direction): (?P<gpio>\d+) (?P<op>.*)$",
            line,
        )
        if gpio:
            key = (float(gpio.group("time")), gpio.group("kind"), int(gpio.group("gpio")), gpio.group("op"))
            if key in gpio_seen:
                continue
            gpio_seen.add(key)
            gpio_events.append({
                "time": key[0],
                "kind": gpio.group("kind"),
                "gpio": key[2],
                "op": gpio.group("op"),
            })

    esoc_pil = [event for event in pil_events if event["fw"] == "esoc0"]
    gpio1270_set0 = [event for event in gpio_events if event["gpio"] == 1270 and "set 0" in event["op"]]
    gpio1270_set1 = [event for event in gpio_events if event["gpio"] == 1270 and "set 1" in event["op"]]
    gpio135_set1 = [event for event in gpio_events if event["gpio"] == 135 and "set 1" in event["op"]]
    gpio142_events = [event for event in gpio_events if event["gpio"] == 142]
    esoc_start = min((event["time"] for event in esoc_pil), default=None)

    def delta_ms(events: list[dict[str, Any]]) -> list[float]:
        if esoc_start is None:
            return []
        return [round((event["time"] - esoc_start) * 1000.0, 3) for event in events]

    return {
        "pil_events": pil_events,
        "gpio_events": gpio_events,
        "esoc_pil_count": len(esoc_pil),
        "esoc_pil_codes": sorted({event["code"] for event in esoc_pil}),
        "esoc_pil_event_names": sorted({event["event"] for event in esoc_pil}),
        "esoc_pil_start_time": esoc_start,
        "gpio1270_set0_count": len(gpio1270_set0),
        "gpio1270_set1_count": len(gpio1270_set1),
        "gpio1270_set0_delta_ms": delta_ms(gpio1270_set0),
        "gpio1270_set1_delta_ms": delta_ms(gpio1270_set1),
        "gpio135_set1_count": len(gpio135_set1),
        "gpio135_set1_delta_ms": delta_ms(gpio135_set1),
        "gpio142_event_count": len(gpio142_events),
    }


def parse_samples(window_text: str) -> dict[str, Any]:
    labels: list[str] = []
    gpio135_states: dict[str, str] = {}
    gpio142_states: dict[str, str] = {}
    mdm_status_irq_lines: dict[str, str] = {}
    pcie_wake_irq_lines: dict[str, str] = {}
    wchan_by_label: dict[str, str] = {}
    for line in window_text.splitlines():
        if line.startswith("rc1_micro_sample label="):
            labels.append(line.split("label=", 1)[1].split()[0])
            continue
        label_match = re.search(r"sample=(?P<label>\S+)", line)
        if not label_match:
            continue
        label = label_match.group("label")
        if "needle=gpio135 match=" in line:
            gpio135_states[label] = line.split("match=", 1)[1].strip()
        elif "needle=gpio142 match=" in line:
            gpio142_states[label] = line.split("match=", 1)[1].strip()
        elif "msmgpio-dc 142 Edge mdm status" in line:
            mdm_status_irq_lines[label] = line.split("source=micro_interrupts", 1)[-1].strip()
        elif "msmgpio-dc 104 Edge msm_pcie_wake" in line:
            pcie_wake_irq_lines[label] = line.split("source=micro_interrupts", 1)[-1].strip()
        elif "source=provider_thread_wchan" in line and "value=" in line:
            wchan_by_label[label] = line.split("value=", 1)[1].strip()

    gpio135_high_samples = {
        label: value
        for label, value in gpio135_states.items()
        if re.search(r"\bgpio135\s*:\s*out\s+1\b", value)
    }
    gpio142_high_samples = {
        label: value
        for label, value in gpio142_states.items()
        if re.search(r"\bgpio142\s*:\s*in\s+1\b", value)
    }
    mdm_status_nonzero = {
        label: value
        for label, value in mdm_status_irq_lines.items()
        if not re.search(r":\s+0\s+0\s+0\s+0\s+0\s+0\s+0\s+0\s+", value)
    }
    pcie_wake_nonzero = {
        label: value
        for label, value in pcie_wake_irq_lines.items()
        if not re.search(r":\s+0\s+0\s+0\s+0\s+0\s+0\s+0\s+0\s+", value)
    }
    return {
        "labels": labels,
        "label_count": len(labels),
        "gpio135_states": gpio135_states,
        "gpio142_states": gpio142_states,
        "gpio135_high_samples": gpio135_high_samples,
        "gpio142_high_samples": gpio142_high_samples,
        "mdm_status_irq_nonzero": mdm_status_nonzero,
        "pcie_wake_irq_nonzero": pcie_wake_nonzero,
        "wchan_by_label": wchan_by_label,
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    manifest = read_json(args.v1469_dir / "manifest.json")
    summary_text = read_text(args.v1469_dir / "test-v1393-summary.stdout.txt")
    dmesg_text = read_text(args.v1469_dir / "test-v1393-dmesg.stdout.txt")
    window_text = read_text(args.v1469_dir / "test-rc1-window-result.stdout.txt")
    trace = parse_trace(window_text)
    samples = parse_samples(window_text)
    progress = manifest.get("wifi_progress", {})

    handoff_pass = (
        manifest.get("decision") == "v1469-test-boot-provider-trigger-no-downstream-rollback-pass"
        and bool(manifest.get("pass"))
        and bool(manifest.get("rollback", {}).get("ok"))
        and progress.get("provider_trigger") is True
    )
    esoc_pil_seen = trace["esoc_pil_count"] >= 2 and 2 in trace["esoc_pil_codes"]
    pon_toggled = trace["gpio1270_set0_count"] > 0 and trace["gpio1270_set1_count"] > 0
    ap2mdm_set_called = trace["gpio135_set1_count"] > 0
    ap2mdm_effective_high_absent = len(samples["gpio135_high_samples"]) == 0
    mdm2ap_absent = (
        trace["gpio142_event_count"] == 0
        and len(samples["gpio142_high_samples"]) == 0
        and len(samples["mdm_status_irq_nonzero"]) == 0
    )
    pcie_wake_absent = len(samples["pcie_wake_irq_nonzero"]) == 0
    downstream_absent = not any(
        bool(progress.get(key))
        for key in ("rc1_progress", "mhi_progress", "wlfw_progress", "bdf_progress", "fw_ready_progress", "wlan0_present")
    )
    provider_blocked_in_powerup = "mdm_subsys_powerup" in set(samples["wchan_by_label"].values())

    pass_condition = (
        handoff_pass
        and esoc_pil_seen
        and pon_toggled
        and ap2mdm_set_called
        and ap2mdm_effective_high_absent
        and mdm2ap_absent
        and pcie_wake_absent
        and downstream_absent
        and provider_blocked_in_powerup
    )
    if pass_condition:
        decision = "v1470-ap2mdm-set-called-but-not-effective-no-mdm2ap-no-rc1"
        reason = (
            "V1469 proves the exact provider PIL branch runs, PON toggles, and AP2MDM set is called, "
            "but GPIO135 never samples high, GPIO142/MDM2AP and PCIe wake IRQs stay zero, and no "
            "RC1/MHI/WLFW/wlan0 progress appears."
        )
        next_gate = "V1471 host-only AP2MDM effective-level and pinctrl ownership classifier"
    else:
        decision = "v1470-provider-pil-gpio-needs-review"
        reason = "The V1469 evidence did not satisfy the provider PIL/GPIO classifier contract."
        next_gate = "review V1469 evidence before any new live mutation"

    return {
        "cycle": "V1470",
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "inputs": {
            "v1469_dir": rel(args.v1469_dir),
            "v1469_manifest": rel(args.v1469_dir / "manifest.json"),
        },
        "handoff": {
            "pass": handoff_pass,
            "decision": manifest.get("decision"),
            "rollback": manifest.get("rollback", {}),
            "summary_has_final_timeout": "helper_timed_out=1" in summary_text,
        },
        "trace": {
            "esoc_pil_seen": esoc_pil_seen,
            "esoc_pil_count": trace["esoc_pil_count"],
            "esoc_pil_codes": trace["esoc_pil_codes"],
            "gpio1270_set0_count": trace["gpio1270_set0_count"],
            "gpio1270_set1_count": trace["gpio1270_set1_count"],
            "gpio1270_set0_delta_ms": trace["gpio1270_set0_delta_ms"],
            "gpio1270_set1_delta_ms": trace["gpio1270_set1_delta_ms"],
            "gpio135_set1_count": trace["gpio135_set1_count"],
            "gpio135_set1_delta_ms": trace["gpio135_set1_delta_ms"],
            "gpio142_event_count": trace["gpio142_event_count"],
        },
        "samples": {
            "label_count": samples["label_count"],
            "labels": samples["labels"],
            "gpio135_high_sample_count": len(samples["gpio135_high_samples"]),
            "gpio142_high_sample_count": len(samples["gpio142_high_samples"]),
            "mdm_status_irq_nonzero_count": len(samples["mdm_status_irq_nonzero"]),
            "pcie_wake_irq_nonzero_count": len(samples["pcie_wake_irq_nonzero"]),
            "wchan_values": sorted(set(samples["wchan_by_label"].values())),
        },
        "progress": {
            "provider_trigger": progress.get("provider_trigger"),
            "modem_trigger": progress.get("modem_trigger"),
            "rc1_progress": progress.get("rc1_progress"),
            "mhi_progress": progress.get("mhi_progress"),
            "wlfw_progress": progress.get("wlfw_progress"),
            "bdf_progress": progress.get("bdf_progress"),
            "fw_ready_progress": progress.get("fw_ready_progress"),
            "wlan0_present": progress.get("wlan0_present"),
            "downstream_absent": downstream_absent,
        },
        "dmesg": {
            "rc1_marker_count": len(re.findall(r"PCIe RC1|LTSSM|mhi|MHI|wlfw|WLFW|BDF|wlan0", dmesg_text)),
        },
        "guardrails": {
            "host_only": True,
            "device_command_executed": False,
            "flash_executed": False,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
        },
        "next_gate": next_gate,
    }


def render_report(result: dict[str, Any]) -> str:
    trace = result["trace"]
    samples = result["samples"]
    progress = result["progress"]
    return "\n".join([
        "# Native Init V1470 Provider PIL/GPIO Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1470`",
        "- Type: host-only classifier over V1469 rollbackable test-boot evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        "",
        "## Evidence Inputs",
        "",
        f"- V1469 evidence: `{result['inputs']['v1469_dir']}`",
        f"- V1469 manifest: `{result['inputs']['v1469_manifest']}`",
        "",
        "## Handoff",
        "",
        f"- handoff pass: `{result['handoff']['pass']}`",
        f"- V1469 decision: `{result['handoff']['decision']}`",
        f"- rollback: `{result['handoff']['rollback']}`",
        f"- final timeout summary captured: `{result['handoff']['summary_has_final_timeout']}`",
        "",
        "## Provider PIL/GPIO Trace",
        "",
        f"- esoc0 PIL notification seen: `{trace['esoc_pil_seen']}`",
        f"- esoc0 PIL count: `{trace['esoc_pil_count']}`",
        f"- esoc0 PIL codes: `{trace['esoc_pil_codes']}`",
        f"- GPIO1270/PON set-low count: `{trace['gpio1270_set0_count']}`",
        f"- GPIO1270/PON set-high count: `{trace['gpio1270_set1_count']}`",
        f"- GPIO1270/PON set-low delta ms: `{trace['gpio1270_set0_delta_ms']}`",
        f"- GPIO1270/PON set-high delta ms: `{trace['gpio1270_set1_delta_ms']}`",
        f"- GPIO135/AP2MDM set-high call count: `{trace['gpio135_set1_count']}`",
        f"- GPIO135/AP2MDM set-high call delta ms: `{trace['gpio135_set1_delta_ms']}`",
        f"- GPIO142/MDM2AP trace event count: `{trace['gpio142_event_count']}`",
        "",
        "## Live Readback Samples",
        "",
        f"- sample labels: `{samples['labels']}`",
        f"- GPIO135 high sample count: `{samples['gpio135_high_sample_count']}`",
        f"- GPIO142 high sample count: `{samples['gpio142_high_sample_count']}`",
        f"- MDM status IRQ nonzero count: `{samples['mdm_status_irq_nonzero_count']}`",
        f"- PCIe wake IRQ nonzero count: `{samples['pcie_wake_irq_nonzero_count']}`",
        f"- provider thread wchan values: `{samples['wchan_values']}`",
        "",
        "## Wi-Fi Progress",
        "",
        f"- provider trigger: `{progress['provider_trigger']}`",
        f"- modem trigger: `{progress['modem_trigger']}`",
        f"- RC1 progress: `{progress['rc1_progress']}`",
        f"- MHI progress: `{progress['mhi_progress']}`",
        f"- WLFW progress: `{progress['wlfw_progress']}`",
        f"- BDF progress: `{progress['bdf_progress']}`",
        f"- FW-ready progress: `{progress['fw_ready_progress']}`",
        f"- wlan0 present: `{progress['wlan0_present']}`",
        f"- downstream absent: `{progress['downstream_absent']}`",
        "",
        "## Interpretation",
        "",
        "V1469 closes the earlier V1466 uncertainty: the test boot now captures",
        "`fw=esoc0` PIL notification parity and the lower provider does call the",
        "AP2MDM set-high path. The remaining gap is not an upper CNSS/HAL issue.",
        "The AP2MDM set call is not observed as an effective high level in the",
        "debug GPIO readback, MDM2AP/GPIO142 never asserts, PCIe wake remains",
        "zero, and RC1/MHI/WLFW/`wlan0` markers remain absent.",
        "",
        "The next aligned work is to classify GPIO135 effective-level ownership",
        "and pinctrl state before any write-based workaround. Do not proceed to",
        "Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, blind",
        "eSoC notify/`BOOT_DONE`, global PCI rescan, or direct PMIC/GPIO/GDSC",
        "writes from this evidence alone.",
        "",
        "## Safety Scope",
        "",
        "This classifier was host-only. It did not issue device commands, flash,",
        "reboot, start Wi-Fi HAL, scan/connect, use credentials, configure",
        "DHCP/routes, perform external ping, or write PMIC/GPIO/GDSC/eSoC controls.",
        "",
        "## Next",
        "",
        result["next_gate"],
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1469-dir", type=Path, default=DEFAULT_V1469_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = classify(args)
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(result))
    if args.write_report:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "pass": result["pass"], "next": result["next_gate"]}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
