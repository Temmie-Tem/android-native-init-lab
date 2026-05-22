#!/usr/bin/env python3
"""V616 host-only post-sibling-sysmon service-notifier classifier.

This classifier compares Android V611, native V615, and prior service-notifier
evidence after V615 proved ADSP/CDSP/SLPI boot nodes can publish sibling
sysmon-qmi. It does not contact the device, write sysfs, start daemons, start
service-manager, start Wi-Fi HAL, scan, connect, use credentials, run DHCP,
change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v616-post-sibling-sysmon-service-notifier-classifier")
DEFAULT_ANDROID_DIR = Path(
    "tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/"
    "v611-android-lower-surface-recapture-run"
)
DEFAULT_V599_MANIFEST = Path("tmp/wifi/v599-service-notifier-instance-gap/manifest.json")
DEFAULT_V614_MANIFEST = Path("tmp/wifi/v614-mdm3-trigger-path-classifier/manifest.json")
DEFAULT_V615_DIR = Path("tmp/wifi/v615-dsp-boot-20260523-015352/v615-live")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")


@dataclass(frozen=True)
class Event:
    marker: str
    timestamp: float | None
    line: str
    source: str


MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("adsp_pil", re.compile(r"subsys-pil.*lpass: adsp: loading", re.I)),
    ("cdsp_pil", re.compile(r"subsys-pil.*turing: cdsp: loading", re.I)),
    ("slpi_pil", re.compile(r"subsys-pil.*ssc: slpi: loading", re.I)),
    ("modem_pil", re.compile(r"subsys-pil.*mss: modem: loading", re.I)),
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_modem", re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.I)),
    ("sysmon_slpi", re.compile(r"sysmon-qmi:.*slpi's SSCTL service", re.I)),
    ("sysmon_cdsp", re.compile(r"sysmon-qmi:.*cdsp's SSCTL service", re.I)),
    ("sysmon_adsp", re.compile(r"sysmon-qmi:.*adsp's SSCTL service", re.I)),
    ("sysmon_esoc0", re.compile(r"sysmon-qmi:.*esoc0's SSCTL service", re.I)),
    ("memshare_request", re.compile(r"memshare_alloc: memory alloc request received", re.I)),
    ("memshare_fail", re.compile(r"memshare_alloc: unable to allocate memory|alloc_resp\.resp\.result:\s*1", re.I)),
    ("service_locator", re.compile(r"servloc: service_locator_new_server: Connection established", re.I)),
    ("service_locator_fail", re.compile(r"servloc: .*Unable to connect to service locator", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I)),
    ("wlan_pd_ack_180", re.compile(r"service-notifier: send_ind_ack:.*msm/modem/wlan_pd.*instance 180", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("rmt_storage_ready", re.compile(r"rmt_storage:INFO:main: Done with init", re.I)),
    ("rmt_storage_open", re.compile(r"rmt_storage_open_cb: Processing: Open Request", re.I)),
    ("pm_qos_warning", re.compile(r"WARNING: CPU: .*kernel/power/qos\.c:616 pm_qos_add_request", re.I)),
    ("kernel_reference_warning", re.compile(r"Reference count mismatch|subsystem_put: esoc0 count:0", re.I)),
)

TIMELINE_MARKERS = [
    "adsp_pil",
    "cdsp_pil",
    "slpi_pil",
    "modem_pil",
    "qrtr_rx",
    "qrtr_tx",
    "sysmon_modem",
    "sysmon_slpi",
    "sysmon_cdsp",
    "sysmon_adsp",
    "memshare_request",
    "memshare_fail",
    "service_locator",
    "service_locator_fail",
    "service_notifier_180",
    "service_notifier_74",
    "wlan_pd",
    "wlan_pd_ack_180",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "sysmon_esoc0",
    "wlan0",
    "rmt_storage_ready",
    "rmt_storage_open",
    "pm_qos_warning",
    "kernel_reference_warning",
]

RC_HINTS: tuple[tuple[str, str], ...] = (
    ("boot_adsp_write", "ADSP boot node write"),
    ("boot_cdsp_write", "CDSP boot node write"),
    ("boot_slpi_write", "SLPI boot node write"),
    ("boot_wlan_permission", "boot_wlan node is prepared but V615 did not write it"),
    ("wcnss_service_trigger", "Android init starts wcnss-service on framework restart"),
    ("mdm_launcher_service", "Android init has vendor.mdm_launcher"),
    ("mdm_helper_service", "Android init has vendor.mdm_helper"),
    ("mdm_helper_baseband_gate", "init.mdm.sh gates mdm_helper on ro.baseband"),
    ("vendor_qrtr_ns_service", "Android init has qrtr-ns"),
    ("vendor_rmt_storage_service", "Android init has rmt_storage"),
    ("vendor_tftp_service", "Android init has tftp_server"),
    ("vendor_pd_mapper_service", "Android init has pd-mapper"),
    ("cnss_diag_trigger", "Android init starts cnss_diag later"),
    ("cnss_daemon_service", "Android init has cnss-daemon"),
)

FORBIDDEN_ACTIONS = [
    "device command",
    "sysfs write",
    "boot_wlan write",
    "CNSS daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "qcwlanstate write",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-dir", type=Path, default=DEFAULT_ANDROID_DIR)
    parser.add_argument("--v599-manifest", type=Path, default=DEFAULT_V599_MANIFEST)
    parser.add_argument("--v614-manifest", type=Path, default=DEFAULT_V614_MANIFEST)
    parser.add_argument("--v615-dir", type=Path, default=DEFAULT_V615_DIR)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def clean_line(raw_line: str) -> str:
    return ANSI_RE.sub("", raw_line).strip()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KEY_RE.match(clean_line(raw_line))
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def line_time(line: str) -> float | None:
    match = TS_RE.match(clean_line(line))
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_events(text: str, source: str) -> list[Event]:
    events: list[Event] = []
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if not line or line.startswith("$ "):
            continue
        for marker, pattern in MARKERS:
            if pattern.search(line):
                events.append(Event(marker, line_time(line), line, source))
    return events


def first_by_marker(events: list[Event]) -> dict[str, Event]:
    found: dict[str, Event] = {}
    for event in events:
        found.setdefault(event.marker, event)
    return found


def count_by_marker(events: list[Event]) -> dict[str, int]:
    counts = {marker: 0 for marker in TIMELINE_MARKERS}
    for event in events:
        counts[event.marker] = counts.get(event.marker, 0) + 1
    return counts


def has(found: dict[str, Event], marker: str) -> bool:
    return marker in found


def event_time(found: dict[str, Event], marker: str) -> float | None:
    event = found.get(marker)
    return event.timestamp if event else None


def delta_ms(found: dict[str, Event], newer: str, older: str) -> float | None:
    newer_time = event_time(found, newer)
    older_time = event_time(found, older)
    if newer_time is None or older_time is None:
        return None
    return round((newer_time - older_time) * 1000.0, 3)


def timeline_rows(found: dict[str, Event], counts: dict[str, int]) -> list[list[str]]:
    rows: list[list[str]] = []
    for marker in TIMELINE_MARKERS:
        event = found.get(marker)
        rows.append([
            marker,
            str(counts.get(marker, 0)),
            "" if event is None or event.timestamp is None else f"{event.timestamp:.6f}",
            "missing" if event is None else event.line,
        ])
    return rows


def sibling_sysmon_present(found: dict[str, Event]) -> bool:
    return all(has(found, marker) for marker in ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp"))


def service_notifier_pair_present(found: dict[str, Event]) -> bool:
    return has(found, "service_notifier_180") and has(found, "service_notifier_74")


def v615_boot_nodes_written(v615_dir: Path) -> dict[str, bool]:
    native_dir = repo_path(v615_dir) / "native"
    return {
        "adsp": "v615.boot_node.write=/sys/kernel/boot_adsp/boot" in read_text(native_dir / "write-boot-adsp.txt"),
        "cdsp": "v615.boot_node.write=/sys/kernel/boot_cdsp/boot" in read_text(native_dir / "write-boot-cdsp.txt"),
        "slpi": "v615.boot_node.write=/sys/kernel/boot_slpi/boot" in read_text(native_dir / "write-boot-slpi.txt"),
        "wlan": "v615.boot_node.write=/sys/kernel/boot_wlan/boot_wlan" in "\n".join(
            read_text(native_dir / name)
            for name in ("write-boot-adsp.txt", "write-boot-cdsp.txt", "write-boot-slpi.txt")
        ),
    }


def android_text(android_dir: Path) -> str:
    root = repo_path(android_dir)
    return "\n".join([
        read_text(root / "android" / "commands" / "dmesg-lower-surface-tail.txt"),
        read_text(root / "android" / "commands" / "dmesg-unfiltered-tail.txt"),
    ])


def v615_text(v615_dir: Path) -> str:
    native_dir = repo_path(v615_dir) / "native"
    return "\n".join([
        read_text(native_dir / "dmesg-delta.txt"),
        read_text(native_dir / "companion-start-only-with-dsp-boot.txt"),
        read_text(native_dir / "rpmsg-after-companion.txt"),
        read_text(native_dir / "ps-before-reboot.txt"),
    ])


def v615_companion_keys(v615_dir: Path) -> dict[str, str]:
    return parse_key_values(read_text(repo_path(v615_dir) / "native" / "companion-start-only-with-dsp-boot.txt"))


def rc_hint_rows(v614: dict[str, Any]) -> list[list[str]]:
    rc_summary = (((v614.get("vendor_init") or {}).get("rc_summary") or {}))
    counts = rc_summary.get("counts") or {}
    first = rc_summary.get("first") or {}
    rows: list[list[str]] = []
    for key, meaning in RC_HINTS:
        item = first.get(key) or {}
        rows.append([key, str(counts.get(key, 0)), meaning, str(item.get("line", "missing"))])
    return rows


def classify(android_found: dict[str, Event],
             v615_found: dict[str, Event],
             v615_counts: dict[str, int],
             boot_nodes: dict[str, bool],
             keys: dict[str, str],
             v599: dict[str, Any],
             v614: dict[str, Any]) -> tuple[str, bool, str, str]:
    if not android_found or not v615_found:
        return (
            "v616-input-evidence-missing",
            False,
            f"android_events={bool(android_found)} v615_events={bool(v615_found)}",
            "refresh Android V611 and native V615 evidence before planning live work",
        )
    if has(v615_found, "wlan0") or has(v615_found, "wlan_fw_ready"):
        return (
            "v616-native-advanced-readiness-review",
            True,
            "V615 evidence advanced past the expected service-notifier gap",
            "refresh classifier and only then consider bounded scan/connect gates",
        )
    android_ready = sibling_sysmon_present(android_found) and service_notifier_pair_present(android_found)
    v615_sibling_ready = sibling_sysmon_present(v615_found)
    v615_notifier_missing = not has(v615_found, "service_notifier_180") and not has(v615_found, "service_notifier_74")
    boot_ok = boot_nodes.get("adsp") and boot_nodes.get("cdsp") and boot_nodes.get("slpi") and not boot_nodes.get("wlan")
    companion_ok = (
        keys.get("wifi_companion_start.result") == "companion-window-pass"
        and keys.get("wifi_companion_start.all_observable") == "1"
        and keys.get("wifi_companion_start.all_postflight_safe") == "1"
    )
    v599_classified = v599.get("decision") == "v599-service-notifier-instance-gap-classified"
    v614_classified = v614.get("decision") == "v614-dsp-boot-trigger-gap-classified"
    warning_count = v615_counts.get("pm_qos_warning", 0) + v615_counts.get("kernel_reference_warning", 0)
    if android_ready and v615_sibling_ready and v615_notifier_missing and boot_ok and companion_ok:
        if warning_count:
            return (
                "v616-post-sibling-sysmon-service-notifier-gap-classified",
                True,
                (
                    "V615 reproduced sibling sysmon and service-locator after ADSP/CDSP/SLPI boot nodes, "
                    f"but service-notifier 180/74 remained absent and kernel warnings={warning_count}; "
                    "direct boot-node retry is blocked"
                ),
                "host-only classify Android init trigger after sibling sysmon; inspect wcnss-service/mdm_helper/boot_wlan dependencies before any live action",
            )
        return (
            "v616-post-sibling-sysmon-gap-no-warning",
            True,
            "V615 reproduced sibling sysmon but still lacks service-notifier 180/74",
            "plan the narrowest service-notifier trigger observer; keep CNSS/HAL/scan/connect blocked",
        )
    return (
        "v616-review-required",
        False,
        (
            f"android_ready={android_ready} v615_sibling_ready={v615_sibling_ready} "
            f"v615_notifier_missing={v615_notifier_missing} boot_ok={boot_ok} companion_ok={companion_ok} "
            f"v599_classified={v599_classified} v614_classified={v614_classified}"
        ),
        "inspect input evidence before selecting the next Wi-Fi live gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    android_events = parse_events(android_text(args.android_dir), "android-v611")
    v615_events = parse_events(v615_text(args.v615_dir), "native-v615")
    android_found = first_by_marker(android_events)
    v615_found = first_by_marker(v615_events)
    android_counts = count_by_marker(android_events)
    v615_counts = count_by_marker(v615_events)
    keys = v615_companion_keys(args.v615_dir)
    boot_nodes = v615_boot_nodes_written(args.v615_dir)
    v599 = load_json(args.v599_manifest)
    v614 = load_json(args.v614_manifest)

    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v616-post-sibling-sysmon-classifier-plan-ready",
            True,
            "plan-only; no evidence classification executed",
            "run V616 host-only classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(
            android_found,
            v615_found,
            v615_counts,
            boot_nodes,
            keys,
            v599,
            v614,
        )

    android_deltas = {
        "sysmon_modem_to_service_locator": delta_ms(android_found, "service_locator", "sysmon_modem"),
        "sysmon_modem_to_service_notifier_180": delta_ms(android_found, "service_notifier_180", "sysmon_modem"),
        "service_locator_to_service_notifier_180": delta_ms(android_found, "service_notifier_180", "service_locator"),
        "service_notifier_180_to_service_notifier_74": delta_ms(android_found, "service_notifier_74", "service_notifier_180"),
        "service_notifier_180_to_wlan_pd": delta_ms(android_found, "wlan_pd", "service_notifier_180"),
        "wlan_pd_to_qmi_server_connected": delta_ms(android_found, "qmi_server_connected", "wlan_pd"),
    }
    native_deltas = {
        "sysmon_modem_to_service_locator": delta_ms(v615_found, "service_locator", "sysmon_modem"),
        "sysmon_modem_to_service_notifier_180": delta_ms(v615_found, "service_notifier_180", "sysmon_modem"),
        "service_locator_to_service_notifier_180": delta_ms(v615_found, "service_notifier_180", "service_locator"),
        "qrtr_tx_to_sysmon_modem": delta_ms(v615_found, "sysmon_modem", "qrtr_tx"),
        "sysmon_modem_to_rmt_storage_ready": delta_ms(v615_found, "rmt_storage_ready", "sysmon_modem"),
    }

    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "android_dir": str(repo_path(args.android_dir)),
            "v599_manifest": str(repo_path(args.v599_manifest)),
            "v614_manifest": str(repo_path(args.v614_manifest)),
            "v615_dir": str(repo_path(args.v615_dir)),
        },
        "android": {
            "event_count": len(android_events),
            "counts": android_counts,
            "deltas_ms": android_deltas,
            "timeline": [asdict(event) for event in android_events if event.marker in TIMELINE_MARKERS],
            "rows": timeline_rows(android_found, android_counts),
        },
        "native_v615": {
            "event_count": len(v615_events),
            "counts": v615_counts,
            "deltas_ms": native_deltas,
            "boot_nodes_written": boot_nodes,
            "companion_result": keys.get("wifi_companion_start.result", ""),
            "companion_all_observable": keys.get("wifi_companion_start.all_observable", ""),
            "companion_all_postflight_safe": keys.get("wifi_companion_start.all_postflight_safe", ""),
            "child_started": keys.get("wifi_companion_start.child_started", ""),
            "rows": timeline_rows(v615_found, v615_counts),
        },
        "prior_classifiers": {
            "v599_decision": v599.get("decision"),
            "v599_pass": v599.get("pass"),
            "v614_decision": v614.get("decision"),
            "v614_pass": v614.get("pass"),
        },
        "vendor_init_hints": rc_hint_rows(v614),
        "inferences": {
            "service_notifier_is_kernel_qmi_callback": True,
            "v615_sibling_sysmon_reproduced": sibling_sysmon_present(v615_found),
            "v615_service_locator_reproduced": has(v615_found, "service_locator"),
            "v615_service_notifier_missing_after_service_locator": has(v615_found, "service_locator") and not service_notifier_pair_present(v615_found),
            "direct_dsp_boot_node_retry_blocked_by_warning": v615_counts.get("pm_qos_warning", 0) > 0,
            "wifi_bringup_still_blocked": True,
        },
        "references": [
            "scripts/revalidation/native_wifi_service_notifier_instance_gap_v599.py",
            "scripts/revalidation/native_wifi_registry_cnss_matrix_v600.py",
            "scripts/revalidation/native_wifi_mdm3_trigger_path_classifier_v614.py",
            "docs/reports/NATIVE_INIT_V615_DSP_BOOT_NODE_OBSERVER_LIVE_2026-05-23.md",
        ],
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    native = manifest["native_v615"]
    android = manifest["android"]
    return "\n".join([
        "# V616 Post-Sibling-Sysmon Service-Notifier Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Native V615 Key State",
        "",
        markdown_table(
            ["key", "value"],
            [
                ["boot_nodes_written", str(native["boot_nodes_written"])],
                ["companion_result", native["companion_result"]],
                ["companion_all_observable", native["companion_all_observable"]],
                ["companion_all_postflight_safe", native["companion_all_postflight_safe"]],
                ["child_started", native["child_started"]],
                ["pm_qos_warning", str(native["counts"].get("pm_qos_warning", 0))],
            ],
        ),
        "",
        "## Android Timing",
        "",
        markdown_table(["delta", "ms"], [[key, str(value)] for key, value in android["deltas_ms"].items()]),
        "",
        "## Native Timing",
        "",
        markdown_table(["delta", "ms"], [[key, str(value)] for key, value in native["deltas_ms"].items()]),
        "",
        "## Android Markers",
        "",
        markdown_table(["marker", "count", "time", "line"], android["rows"]),
        "",
        "## Native V615 Markers",
        "",
        markdown_table(["marker", "count", "time", "line"], native["rows"]),
        "",
        "## Vendor Init Hints",
        "",
        markdown_table(["hint", "count", "meaning", "first_line"], manifest["vendor_init_hints"]),
        "",
        "## Inferences",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in manifest["inferences"].items()]),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
