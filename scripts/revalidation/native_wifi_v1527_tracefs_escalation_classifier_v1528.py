#!/usr/bin/env python3
"""V1528 host-only classifier for V1527 Android-good RC1 trigger evidence.

V1527 proved that Android can reach WLFW/BDF/wlan0 while the high-cadence
GPIO104/GPIO142 IRQ counters, GPIO135/GPIO142 debugfs levels, and raw kmsg
PCIe/LTSSM text remain nondiscriminating.  This classifier fixes that result
and selects the next bounded observer: tracefs events around the Android-good
pm-service/eSoC window.

No device command is executed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1528-v1527-tracefs-escalation-classifier")
DEFAULT_REPORT = Path(
    "docs/reports/NATIVE_INIT_V1528_V1527_EVIDENCE_TRACEFS_ESCALATION_2026-06-02.md"
)
DEFAULT_V1527_MANIFEST = Path("tmp/wifi/v1527-android-initial-rc1-trigger-handoff/manifest.json")
DEFAULT_V1527_EVIDENCE = Path(
    "tmp/wifi/v1527-android-initial-rc1-trigger-handoff/android-postfs-evidence/a90-v1527-rc1-trigger-sampler"
)
DEFAULT_V776_MANIFEST = Path("tmp/wifi/v776-tracepoint-inventory/manifest.json")
DEFAULT_V777_REPORT = Path("docs/reports/NATIVE_INIT_V777_TRACEPOINT_FORMAT_CLASSIFIER_2026-05-25.md")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--v1527-manifest", type=Path, default=DEFAULT_V1527_MANIFEST)
    parser.add_argument("--v1527-evidence", type=Path, default=DEFAULT_V1527_EVIDENCE)
    parser.add_argument("--v776-manifest", type=Path, default=DEFAULT_V776_MANIFEST)
    parser.add_argument("--v777-report", type=Path, default=DEFAULT_V777_REPORT)
    parser.add_argument("command", nargs="?", choices=("run",), default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def nested(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value is None else value


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def count_lines(text: str, pattern: str) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    return sum(1 for line in text.splitlines() if regex.search(line))


def first_lines(text: str, pattern: str, limit: int = 5) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    return [line.strip() for line in text.splitlines() if regex.search(line)][:limit]


def contains_event(v776_text: str, event: str) -> bool:
    return bool(re.search(rf"(^|\\n){re.escape(event)}(\\n|$)", v776_text))


def parse_v1527(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v1527_manifest)
    analysis = nested(manifest, "context", "analysis", default={}) or {}
    trigger = analysis.get("trigger_analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    flags = {
        key: bool_value(manifest.get(key))
        for key in (
            "wifi_hal_start_executed",
            "scan_connect_executed",
            "credential_use_executed",
            "dhcp_route_executed",
            "external_ping_executed",
            "pmic_gpio_gdsc_write_executed",
            "blind_esoc_notify_executed",
            "global_pci_rescan_executed",
            "platform_bind_unbind_executed",
            "partition_write_executed",
        )
    }
    evidence = repo_path(args.v1527_evidence)
    samples = read_text(evidence / "irq-gpio-samples.log")
    kmsg = read_text(evidence / "kmsg-stream.txt")
    module_dmesg = read_text(evidence / "dmesg-filtered.txt")
    return {
        "manifest_present": bool(manifest),
        "evidence_present": evidence.is_dir(),
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "sample_count": int_value(analysis.get("sample_count")),
        "sample_first_uptime": analysis.get("sample_first_uptime"),
        "sample_last_uptime": analysis.get("sample_last_uptime"),
        "android_lower_ok": bool_value(trigger.get("android_lower_ok")),
        "wlfw_time": dmesg.get("wlfw_time"),
        "bdf_time": dmesg.get("bdf_time"),
        "wlan0_time": dmesg.get("wlan0_time"),
        "pcie_l0_time": dmesg.get("pcie_l0_time"),
        "kmsg_line_count": int_value(nested(trigger, "kmsg", "line_count")),
        "kmsg_rc1_line_count": int_value(nested(trigger, "kmsg", "rc1_line_count")),
        "kmsg_stream_unavailable": bool_value(nested(trigger, "kmsg", "stream_unavailable")),
        "gpio104_irq_max": int_value(nested(trigger, "gpio104_irq", "max")),
        "gpio142_irq_max": int_value(nested(trigger, "gpio142_irq", "max")),
        "gpio135_high_lines": count_lines(samples, r"gpio135\s*:\s*out\s+1"),
        "gpio142_high_lines": count_lines(samples, r"gpio142\s*:\s*(?:in|out)\s+1"),
        "pcie_text_lines": count_lines(kmsg + "\n" + module_dmesg, r"msm_pcie_enable|LTSSM|Current GEN|link initialized"),
        "esoc0_lines": first_lines(module_dmesg, r"__subsystem_get: esoc0|Changing subsys fw_name to esoc0", 4),
        "lower_lines": first_lines(module_dmesg, r"wlfw_start|BDF file|FW is ready|wlan0", 8),
        "safety_flags": flags,
    }


def parse_tracefs_surface(args: argparse.Namespace) -> dict[str, Any]:
    v776 = load_json(args.v776_manifest)
    v776_text = json.dumps(v776, ensure_ascii=False)
    v777_report = read_text(args.v777_report)
    events = [
        "raw_syscalls:sys_enter",
        "raw_syscalls:sys_exit",
        "sched:sched_switch",
        "sched:sched_process_exec",
        "workqueue:workqueue_execute_start",
        "workqueue:workqueue_execute_end",
        "irq:irq_handler_entry",
        "irq:irq_handler_exit",
        "msm_pil_event:pil_event",
        "msm_pil_event:pil_notif",
        "msm_pil_event:pil_func",
        "binder:binder_command",
        "binder:binder_return",
        "printk:console",
    ]
    return {
        "v776_present": bool(v776),
        "v776_decision": v776.get("decision", ""),
        "v776_pass": bool_value(v776.get("pass")),
        "available_events_total": int_value(re.search(r"v776.available_events_total=(\d+)", v776_text).group(1))
        if re.search(r"v776.available_events_total=(\d+)", v776_text)
        else 0,
        "event_available": {event: contains_event(v776_text, event) for event in events},
        "v777_report_present": bool(v777_report),
        "pil_format_classified": "msm_pil_event:pil_notif" in v777_report and "event_name" in v777_report,
    }


def decide(v1527: dict[str, Any], tracefs: dict[str, Any]) -> tuple[str, bool, str, str]:
    forbidden = [key for key, value in v1527.get("safety_flags", {}).items() if value]
    if not v1527["manifest_present"] or not v1527["evidence_present"]:
        return ("v1528-v1527-evidence-missing", False, "V1527 manifest/evidence missing", "rerun V1527 or restore evidence")
    if not v1527["pass"]:
        return ("v1528-v1527-not-passing", False, f"V1527 decision={v1527['decision']}", "inspect V1527 rollback before continuing")
    if forbidden:
        return ("v1528-v1527-safety-flag-review", False, f"unexpected safety flags={forbidden}", "audit V1527 run")
    if not v1527["android_lower_ok"]:
        return ("v1528-android-lower-not-proven", False, "V1527 did not prove Android lower Wi-Fi markers", "redo Android-good reference")
    nondiscriminating = (
        v1527["kmsg_rc1_line_count"] == 0
        and v1527["gpio104_irq_max"] == 0
        and v1527["gpio142_irq_max"] == 0
        and v1527["gpio135_high_lines"] == 0
        and v1527["gpio142_high_lines"] == 0
        and v1527["pcie_text_lines"] == 0
    )
    required_trace_events = (
        "sched:sched_switch",
        "workqueue:workqueue_execute_start",
        "irq:irq_handler_entry",
        "msm_pil_event:pil_notif",
        "raw_syscalls:sys_enter",
    )
    events_ready = all((tracefs.get("event_available") or {}).get(event) for event in required_trace_events)
    if nondiscriminating and events_ready:
        return (
            "v1528-route-to-android-tracefs-event-capture",
            True,
            "Android reached WLFW/BDF/wlan0 while kmsg PCIe text, GPIO135/142 levels, and GPIO104/142 IRQs stayed nondiscriminating",
            "implement V1529 rollbackable Android tracefs event handoff around pm-service/esoc0 window",
        )
    if nondiscriminating:
        return (
            "v1528-tracefs-events-need-refresh",
            False,
            "V1527 evidence is nondiscriminating but tracefs event readiness is stale or incomplete",
            "refresh tracefs available_events before live trace capture",
        )
    return (
        "v1528-v1527-evidence-has-direct-signal",
        True,
        "V1527 contains a direct GPIO/kmsg/IRQ signal; inspect before tracefs escalation",
        "classify the direct signal first",
    )


def render_report(manifest: dict[str, Any]) -> str:
    v1527 = manifest["v1527"]
    tracefs = manifest["tracefs"]
    event_rows = [[event, available] for event, available in sorted((tracefs.get("event_available") or {}).items())]
    return "\n".join(
        [
            "# Native Init V1528 V1527 Evidence Tracefs Escalation",
            "",
            "## Result",
            "",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next']}",
            f"- evidence: `{manifest['out_dir']}`",
            "",
            "## V1527 Evidence Summary",
            "",
            markdown_table(
                ["signal", "value"],
                [
                    ["V1527 decision", v1527["decision"]],
                    ["Android lower OK", v1527["android_lower_ok"]],
                    ["sample window", f"{v1527['sample_count']} samples, {v1527['sample_first_uptime']}s..{v1527['sample_last_uptime']}s"],
                    ["WLFW/BDF/wlan0", f"{v1527['wlfw_time']}/{v1527['bdf_time']}/{v1527['wlan0_time']}"],
                    ["kmsg lines / RC1 lines", f"{v1527['kmsg_line_count']} / {v1527['kmsg_rc1_line_count']}"],
                    ["GPIO104/GPIO142 IRQ max", f"{v1527['gpio104_irq_max']} / {v1527['gpio142_irq_max']}"],
                    ["GPIO135/GPIO142 high samples", f"{v1527['gpio135_high_lines']} / {v1527['gpio142_high_lines']}"],
                    ["PCIe text lines", v1527["pcie_text_lines"]],
                ],
            ),
            "",
            "## Interpretation",
            "",
            "V1527 captured a successful Android lower Wi-Fi bring-up window: WLFW started, BDF downloads occurred, and `wlan0` appeared. During the same window the chosen high-cadence IRQ/GPIO sources and raw kmsg PCIe/LTSSM text did not expose the first-L0 trigger. That means GPIO135/GPIO142 debugfs levels, GPIO104/GPIO142 IRQ totals, and kmsg PCIe text must not be used as hard Android/native parity requirements for this blocker.",
            "",
            "The next useful observer is not another kmsg/GPIO sampler and not a firmware/MHI deep dive. The next gate should use bounded tracefs events around the Android-good `pm-service`/`subsys_esoc0` window, with rollback to native after evidence pull.",
            "",
            "## Tracefs Event Readiness",
            "",
            markdown_table(["event", "available"], event_rows),
            "",
            "## V1529 Live Gate Contract",
            "",
            "- Reuse the V1527 Android boot/Magisk/native rollback handoff.",
            "- In the temporary Android module, mount/use tracefs only for the capture window and clean up tracing controls before evidence pull.",
            "- Enable a narrow event set: `sched:sched_switch`, `sched:sched_process_exec`, `workqueue:workqueue_execute_start/end`, `irq:irq_handler_entry/exit`, `msm_pil_event:*`, and only a bounded/filtered raw syscall view if volume is acceptable.",
            "- Correlate trace timestamps with `subsys_get modem`, `subsys_get esoc0`, `wlfw_start`, BDF, FW-ready, and `wlan0` markers.",
            "- Do not start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, ping externally, write PMIC/GPIO/GDSC, spoof eSoC/BOOT_DONE, rescan PCI, or bind/unbind platforms.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v1527 = parse_v1527(args)
    tracefs = parse_tracefs_surface(args)
    decision, passed, reason, next_step = decide(v1527, tracefs)
    manifest = {
        "cycle": "V1528",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "v1527": v1527,
        "tracefs": tracefs,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "pmic_gpio_gdsc_write_executed": False,
        "blind_esoc_notify_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
    }
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    write_private_text(repo_path(args.report), report)
    print(f"decision: {decision}")
    print(f"pass:     {passed}")
    print(f"reason:   {reason}")
    print(f"next:     {next_step}")
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
