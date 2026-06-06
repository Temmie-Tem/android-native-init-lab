#!/usr/bin/env python3
"""V628 host-only service-74 publisher dependency classifier.

V627 proved the safe V598/v100 path can reproduce service-locator and
service-notifier 180, but not service-notifier 74. This classifier compares
Android V622, native V627, and the unsafe V619 direct-DSP run to decide whether
the next gate should chase HAL/connect or stay below them at the sibling-SSCTL
and service-74 publisher layer.

It does not contact the device, write sysfs, start daemons, start
service-manager, start Wi-Fi HAL, scan/connect/link-up, use credentials, run
DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v628-service74-publisher-classifier")
DEFAULT_ANDROID_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_ANDROID_V622_DMESG = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/android/commands/dmesg-lower-surface-tail.txt"
)
DEFAULT_NATIVE_V627_MANIFEST = Path("tmp/wifi/v627-post-180-observer-live-v2/manifest.json")
DEFAULT_NATIVE_V627_DMESG = Path("tmp/wifi/v627-post-180-observer-live-v2/native/dmesg-delta.txt")
DEFAULT_NATIVE_V619_MANIFEST = Path("tmp/wifi/v619-android-order-post-sysmon-observer-run/manifest.json")
DEFAULT_NATIVE_V619_DMESG = Path("tmp/wifi/v619-android-order-post-sysmon-observer-run/native/dmesg-delta.txt")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")

MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_modem", re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.I)),
    ("sysmon_slpi", re.compile(r"sysmon-qmi:.*slpi's SSCTL service", re.I)),
    ("sysmon_cdsp", re.compile(r"sysmon-qmi:.*cdsp's SSCTL service", re.I)),
    ("sysmon_adsp", re.compile(r"sysmon-qmi:.*adsp's SSCTL service", re.I)),
    ("sysmon_esoc0", re.compile(r"sysmon-qmi:.*esoc0's SSCTL service", re.I)),
    ("service_locator", re.compile(r"servloc: service_locator_new_server:.*Service locator", re.I)),
    ("service_locator_init", re.compile(r"servloc: init_service_locator: Service locator initialized", re.I)),
    ("service_locator_fail", re.compile(r"servloc: .*Unable to connect to service locator", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I)),
    ("wlan_pd_ack_180", re.compile(r"service-notifier: send_ind_ack:.*msm/modem/wlan_pd.*instance 180", re.I)),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("rmt_storage_ready", re.compile(r"rmt_storage:INFO:main: Done with init", re.I)),
    ("rmt_storage_open", re.compile(r"rmt_storage_open_cb: Processing: Open Request", re.I)),
    ("tftp_start", re.compile(r"starting service 'vendor\.tftp_server'|/vendor/bin/tftp_server|tftp_server", re.I)),
    ("pd_mapper_start", re.compile(r"starting service 'vendor\.pd_mapper'|/vendor/bin/pd-mapper|pd-mapper", re.I)),
    ("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_daemon_binder_failure", re.compile(r"cnss-daemon.*binder: .*transaction failed|cnss-daemon.*ioctl .* returned -22", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|pm_qos_add_request\(\) called for already added request|Reference count mismatch", re.I)),
)

TIMELINE = [name for name, _ in MARKERS]
SIBLING_SYSMON = ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp")

FORBIDDEN_ACTIONS = [
    "device command",
    "sysfs write",
    "DSP boot-node write",
    "esoc0 open",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
]


@dataclass(frozen=True)
class Event:
    marker: str
    timestamp: float | None
    line: str
    source: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-v622-manifest", type=Path, default=DEFAULT_ANDROID_V622_MANIFEST)
    parser.add_argument("--android-v622-dmesg", type=Path, default=DEFAULT_ANDROID_V622_DMESG)
    parser.add_argument("--native-v627-manifest", type=Path, default=DEFAULT_NATIVE_V627_MANIFEST)
    parser.add_argument("--native-v627-dmesg", type=Path, default=DEFAULT_NATIVE_V627_DMESG)
    parser.add_argument("--native-v619-manifest", type=Path, default=DEFAULT_NATIVE_V619_MANIFEST)
    parser.add_argument("--native-v619-dmesg", type=Path, default=DEFAULT_NATIVE_V619_DMESG)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {"exists": False, "path": str(repo_path(path))}
    data = json.loads(text)
    if isinstance(data, dict):
        data.setdefault("exists", True)
        data.setdefault("path", str(repo_path(path)))
        return data
    return {"exists": True, "path": str(repo_path(path)), "value": data}


def clean_line(raw_line: str) -> str:
    line = ANSI_RE.sub("", raw_line).strip()
    return line[2:] if line.startswith("$ ") else line


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
        if raw_line.lstrip().startswith("$ "):
            continue
        line = clean_line(raw_line)
        if not line:
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
    counts = {marker: 0 for marker in TIMELINE}
    for event in events:
        counts[event.marker] = counts.get(event.marker, 0) + 1
    return counts


def event_time(found: dict[str, Event], marker: str) -> float | None:
    event = found.get(marker)
    return event.timestamp if event else None


def delta_ms(found: dict[str, Event], newer: str, older: str) -> float | None:
    newer_time = event_time(found, newer)
    older_time = event_time(found, older)
    if newer_time is None or older_time is None:
        return None
    return round((newer_time - older_time) * 1000.0, 3)


def first_line(found: dict[str, Event], marker: str) -> str:
    event = found.get(marker)
    return event.line if event else "missing"


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def has_all_sibling_sysmon(counts: dict[str, int]) -> bool:
    return all(counts.get(marker, 0) > 0 for marker in SIBLING_SYSMON)


def case_summary(source: str, text: str) -> dict[str, Any]:
    events = parse_events(text, source)
    found = first_by_marker(events)
    counts = count_by_marker(events)
    return {
        "counts": counts,
        "first_lines": {
            marker: first_line(found, marker)
            for marker in (
                "qrtr_rx",
                "qrtr_tx",
                "sysmon_modem",
                "sysmon_slpi",
                "sysmon_cdsp",
                "sysmon_adsp",
                "service_locator",
                "service_locator_init",
                "service_notifier_180",
                "service_notifier_74",
                "wlan_pd",
                "wlfw_start",
                "qmi_server_connected",
                "cnss_diag_netlink",
                "cnss_daemon_netlink",
                "cnss_daemon_binder_failure",
                "kernel_warning",
            )
        },
        "deltas_ms": {
            "qrtr_tx_to_sysmon_modem": delta_ms(found, "sysmon_modem", "qrtr_tx"),
            "sysmon_modem_to_sysmon_slpi": delta_ms(found, "sysmon_slpi", "sysmon_modem"),
            "sysmon_modem_to_sysmon_cdsp": delta_ms(found, "sysmon_cdsp", "sysmon_modem"),
            "sysmon_modem_to_sysmon_adsp": delta_ms(found, "sysmon_adsp", "sysmon_modem"),
            "sysmon_modem_to_service_locator": delta_ms(found, "service_locator", "sysmon_modem"),
            "service_locator_to_service_notifier_180": delta_ms(found, "service_notifier_180", "service_locator"),
            "service_notifier_180_to_service_notifier_74": delta_ms(found, "service_notifier_74", "service_notifier_180"),
            "service_notifier_180_to_wlfw_start": delta_ms(found, "wlfw_start", "service_notifier_180"),
            "service_notifier_180_to_wlan_pd": delta_ms(found, "wlan_pd", "service_notifier_180"),
            "service_notifier_180_to_cnss_diag_netlink": delta_ms(found, "cnss_diag_netlink", "service_notifier_180"),
            "service_notifier_180_to_cnss_daemon_netlink": delta_ms(found, "cnss_daemon_netlink", "service_notifier_180"),
            "service_notifier_180_to_binder_failure": delta_ms(found, "cnss_daemon_binder_failure", "service_notifier_180"),
        },
        "has_all_sibling_sysmon": has_all_sibling_sysmon(counts),
        "timeline_rows": [
            [
                marker,
                str(counts.get(marker, 0)),
                "" if marker not in found or found[marker].timestamp is None else f"{found[marker].timestamp:.6f}",
                first_line(found, marker),
            ]
            for marker in TIMELINE
        ],
    }


def android_case(android_manifest: dict[str, Any], android_dmesg: str) -> dict[str, Any]:
    parsed = case_summary("android-v622", android_dmesg)
    summary = android_manifest.get("android_summary") or {}
    counts = parsed["counts"]
    counts.update({key: int(value) for key, value in (summary.get("counts") or {}).items() if isinstance(value, int)})
    deltas = parsed["deltas_ms"]
    deltas.update(summary.get("deltas_ms") or {})
    parsed.update({
        "decision": android_manifest.get("decision"),
        "pass": android_manifest.get("pass"),
        "counts": counts,
        "deltas_ms": deltas,
        "timing": summary.get("timing") or {},
        "props": summary.get("props") or {},
        "has_all_sibling_sysmon": has_all_sibling_sysmon(counts),
    })
    return parsed


def native_v627_case(native_manifest: dict[str, Any], native_dmesg: str) -> dict[str, Any]:
    parsed = case_summary("native-v627", native_dmesg)
    live = native_manifest.get("live") or {}
    observer = live.get("post_180_observer") or {}
    parsed.update({
        "decision": native_manifest.get("decision"),
        "pass": native_manifest.get("pass"),
        "mss_after_companion": live.get("mss_after_companion"),
        "mdm3_after_companion": live.get("mdm3_after_companion"),
        "post_180_window_sec": observer.get("observed_post_180_window_sec"),
        "qrtr_readback": live.get("qrtr_readback") or {},
        "companion_order": (live.get("companion_keys") or {}).get("wifi_companion_start.order"),
        "child_started": (live.get("companion_keys") or {}).get("wifi_companion_start.child_started"),
        "wifi_bringup_executed": native_manifest.get("wifi_bringup_executed"),
        "wifi_hal_start_executed": native_manifest.get("wifi_hal_start_executed"),
        "external_ping_executed": native_manifest.get("external_ping_executed"),
    })
    return parsed


def native_v619_case(native_manifest: dict[str, Any], native_dmesg: str) -> dict[str, Any]:
    parsed = case_summary("native-v619", native_dmesg)
    live = native_manifest.get("live") or {}
    dsp_counts = live.get("dsp_counts") or {}
    marker_counts = ((live.get("markers") or {}).get("counts") or {})
    counts = parsed["counts"]
    if marker_counts.get("kernel_warning") is not None:
        counts["kernel_warning"] = int(marker_counts.get("kernel_warning") or 0)
    parsed.update({
        "decision": native_manifest.get("decision"),
        "pass": native_manifest.get("pass"),
        "dsp_counts": dsp_counts,
        "boot_nodes_written": live.get("boot_nodes_written") or {},
        "kernel_warning_count": counts.get("kernel_warning", 0),
        "has_all_sibling_sysmon": all(int(dsp_counts.get(marker, 0) or 0) > 0 for marker in ("slpi_sysmon", "cdsp_sysmon", "adsp_sysmon")),
    })
    return parsed


def evidence_rows(manifest: dict[str, Any]) -> list[list[str]]:
    android = manifest["android_v622"]
    native = manifest["native_v627"]
    v619 = manifest["native_v619"]
    return [
        [
            "Android V622",
            "full lower sequence",
            (
                f"sibling_sysmon={bool_text(android['has_all_sibling_sysmon'])}; "
                f"locator={android['counts'].get('service_locator', 0)}; "
                f"180={android['counts'].get('service_notifier_180', 0)}; "
                f"74={android['counts'].get('service_notifier_74', 0)}; "
                f"180->74={android['deltas_ms'].get('service_notifier_180_to_service_notifier_74')}ms"
            ),
            "service 74 is a lower publication target before HAL/connect",
        ],
        [
            "Native V627",
            "locator and 180 only",
            (
                f"sibling_sysmon={bool_text(native['has_all_sibling_sysmon'])}; "
                f"locator={native['counts'].get('service_locator', 0)}; "
                f"180={native['counts'].get('service_notifier_180', 0)}; "
                f"74={native['counts'].get('service_notifier_74', 0)}; "
                f"window={native.get('post_180_window_sec')}s"
            ),
            "not a service-locator absence; service 74 publisher is still missing",
        ],
        [
            "Sibling SSCTL delta",
            "correlated but not safely replayed",
            (
                f"android slpi/cdsp/adsp before locator={bool_text(android['has_all_sibling_sysmon'])}; "
                f"native V627 sibling={bool_text(native['has_all_sibling_sysmon'])}; "
                f"native V619 sibling={bool_text(v619['has_all_sibling_sysmon'])}"
            ),
            "classify safe sibling trigger before any more DSP boot-node live retry",
        ],
        [
            "V619 direct DSP path",
            "unsafe negative",
            (
                f"decision={v619.get('decision')}; "
                f"kernel_warning={v619.get('kernel_warning_count')}; "
                f"service74={v619['counts'].get('service_notifier_74', 0)}"
            ),
            "do not repeat direct ADSP/CDSP/SLPI boot-node writes",
        ],
        [
            "CNSS/HAL/connect",
            "still premature",
            (
                f"android service74 before cnss-daemon={android['deltas_ms'].get('service_notifier_180_to_cnss_daemon_netlink')}ms; "
                f"native binder_after_180={native['deltas_ms'].get('service_notifier_180_to_binder_failure')}ms; "
                f"native_wlan0={native['counts'].get('wlan0', 0)}"
            ),
            "keep HAL/qcwlanstate/connect blocked until service 74 or WLAN-PD advances",
        ],
    ]


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    android = manifest["android_v622"]
    native = manifest["native_v627"]
    v619 = manifest["native_v619"]
    android_ready = (
        android["has_all_sibling_sysmon"]
        and android["counts"].get("service_locator", 0) > 0
        and android["counts"].get("service_notifier_180", 0) > 0
        and android["counts"].get("service_notifier_74", 0) > 0
    )
    native_safe_gap = (
        native["counts"].get("kernel_warning", 0) == 0
        and native["counts"].get("service_locator", 0) > 0
        and native["counts"].get("service_notifier_180", 0) > 0
        and native["counts"].get("service_notifier_74", 0) == 0
        and not native["has_all_sibling_sysmon"]
        and float(native.get("post_180_window_sec") or 0.0) >= 25.0
    )
    direct_dsp_unsafe = (
        v619["has_all_sibling_sysmon"]
        and int(v619.get("kernel_warning_count") or 0) > 0
        and v619["counts"].get("service_notifier_74", 0) == 0
    )
    if android_ready and native_safe_gap and direct_dsp_unsafe:
        return (
            "v628-service74-sibling-sysmon-gap-classified",
            True,
            (
                "Android publishes service 74 only after sibling SLPI/CDSP/ADSP SSCTL services are visible; "
                "native V627 reaches service-locator and service 180 safely but lacks those sibling SSCTL markers "
                "and never publishes service 74, while V619 proves direct DSP boot-node writes are unsafe and still negative."
            ),
            "V629 should classify safe sibling-SSCTL bring-up candidates host-only before any live retry; keep HAL/qcwlanstate/connect blocked",
        )
    return (
        "v628-service74-publisher-evidence-gap",
        False,
        f"android_ready={android_ready} native_safe_gap={native_safe_gap} direct_dsp_unsafe={direct_dsp_unsafe}",
        "refresh V622/V627/V619 evidence before designing another live gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    android_manifest = load_json(args.android_v622_manifest)
    native_v627_manifest = load_json(args.native_v627_manifest)
    native_v619_manifest = load_json(args.native_v619_manifest)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "android_v622_manifest": str(repo_path(args.android_v622_manifest)),
            "android_v622_dmesg": str(repo_path(args.android_v622_dmesg)),
            "native_v627_manifest": str(repo_path(args.native_v627_manifest)),
            "native_v627_dmesg": str(repo_path(args.native_v627_dmesg)),
            "native_v619_manifest": str(repo_path(args.native_v619_manifest)),
            "native_v619_dmesg": str(repo_path(args.native_v619_dmesg)),
        },
        "android_v622": android_case(android_manifest, read_text(args.android_v622_dmesg)),
        "native_v627": native_v627_case(native_v627_manifest, read_text(args.native_v627_dmesg)),
        "native_v619": native_v619_case(native_v619_manifest, read_text(args.native_v619_dmesg)),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
    }
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v628-service74-publisher-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V628 host-only classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(manifest)
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
    })
    manifest["evidence_rows"] = evidence_rows(manifest)
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V628 Service-74 Publisher Dependency Classifier",
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
        "## Evidence Matrix",
        "",
        markdown_table(["subject", "classification", "evidence", "next"], manifest["evidence_rows"]),
        "",
        "## Android Deltas",
        "",
        markdown_table(["key", "ms"], [[key, str(value)] for key, value in manifest["android_v622"]["deltas_ms"].items()]),
        "",
        "## Native V627 Deltas",
        "",
        markdown_table(["key", "ms"], [[key, str(value)] for key, value in manifest["native_v627"]["deltas_ms"].items()]),
        "",
        "## Android First Lines",
        "",
        markdown_table(["marker", "line"], [[key, value] for key, value in manifest["android_v622"]["first_lines"].items()]),
        "",
        "## Native V627 First Lines",
        "",
        markdown_table(["marker", "line"], [[key, value] for key, value in manifest["native_v627"]["first_lines"].items()]),
        "",
        "## Native V619 Safety",
        "",
        markdown_table([
            "key",
            "value",
        ], [
            ["decision", str(manifest["native_v619"].get("decision"))],
            ["has_all_sibling_sysmon", str(manifest["native_v619"].get("has_all_sibling_sysmon"))],
            ["kernel_warning_count", str(manifest["native_v619"].get("kernel_warning_count"))],
            ["service_notifier_74", str(manifest["native_v619"]["counts"].get("service_notifier_74", 0))],
        ]),
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
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
