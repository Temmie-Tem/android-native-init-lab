#!/usr/bin/env python3
"""V618 host-only RFS alias and companion ordering classifier.

V617 left `rfs_access` as an unreplayed candidate. This classifier checks
whether that is a real standalone daemon target or only the init/domain label
for `tftp_server`, then compares Android companion service order with V615.
It does not contact the device, write sysfs, start daemons, start
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v618-rfs-alias-order-classifier")
DEFAULT_V617_MANIFEST = Path("tmp/wifi/v617-android-init-trigger-candidate-classifier/manifest.json")
DEFAULT_V615_DIR = Path("tmp/wifi/v615-dsp-boot-20260523-015352/v615-live")
DEFAULT_V614_SNAPSHOT = Path("tmp/wifi/v614-mdm3-trigger-path-classifier/native/vendor-init-readonly-snapshot.txt")
DEFAULT_ANDROID_V525_DIR = Path(
    "tmp/wifi/v526-android-companion-identity-handoff-run/"
    "v525-android-companion-identity-run"
)
DEFAULT_ANDROID_V521_DIR = Path(
    "tmp/wifi/v524-android-companion-exact-recapture-handoff/"
    "v521-android-companion-recapture-run"
)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")

ANDROID_ORDER = ["qrtr_ns", "pd_mapper", "rmt_storage", "tftp_server"]

MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("init_qrtr_ns_start", re.compile(r"starting service 'vendor\.qrtr-ns'", re.I)),
    ("init_pd_mapper_start", re.compile(r"starting service 'vendor\.pd_mapper'", re.I)),
    ("init_rmt_storage_start", re.compile(r"starting service 'vendor\.rmt_storage'", re.I)),
    ("init_tftp_server_start", re.compile(r"starting service 'vendor\.tftp_server'", re.I)),
    ("sysmon_modem", re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.I)),
    ("sysmon_slpi", re.compile(r"sysmon-qmi:.*slpi's SSCTL service", re.I)),
    ("sysmon_cdsp", re.compile(r"sysmon-qmi:.*cdsp's SSCTL service", re.I)),
    ("sysmon_adsp", re.compile(r"sysmon-qmi:.*adsp's SSCTL service", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("service_locator", re.compile(r"servloc: service_locator_new_server: Connection established", re.I)),
    ("service_locator_fail", re.compile(r"servloc: .*Unable to connect to service locator", re.I)),
    ("rmt_storage_ready", re.compile(r"rmt_storage:INFO:main: Done with init", re.I)),
    ("rmt_storage_open", re.compile(r"rmt_storage_open_cb: Processing: Open Request", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("pm_qos_warning", re.compile(r"pm_qos_add_request\(\) called for already added request", re.I)),
)

TIMELINE_MARKERS = [
    "init_qrtr_ns_start",
    "init_pd_mapper_start",
    "init_rmt_storage_start",
    "init_tftp_server_start",
    "sysmon_modem",
    "sysmon_slpi",
    "sysmon_cdsp",
    "sysmon_adsp",
    "service_notifier_180",
    "service_notifier_74",
    "service_locator_fail",
    "service_locator",
    "rmt_storage_ready",
    "rmt_storage_open",
    "wlan_pd",
    "qmi_server_connected",
    "wlan_fw_ready",
    "wlan0",
    "pm_qos_warning",
]

FORBIDDEN_ACTIONS = [
    "device command",
    "sysfs write",
    "boot_wlan/qcwlanstate write",
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
    parser.add_argument("--v617-manifest", type=Path, default=DEFAULT_V617_MANIFEST)
    parser.add_argument("--v615-dir", type=Path, default=DEFAULT_V615_DIR)
    parser.add_argument("--v614-snapshot", type=Path, default=DEFAULT_V614_SNAPSHOT)
    parser.add_argument("--android-v525-dir", type=Path, default=DEFAULT_ANDROID_V525_DIR)
    parser.add_argument("--android-v521-dir", type=Path, default=DEFAULT_ANDROID_V521_DIR)
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
        line = clean_line(raw_line)
        match = KEY_RE.match(line)
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


def android_v525_text(android_dir: Path) -> dict[str, str]:
    commands = repo_path(android_dir) / "android" / "commands"
    return {
        "dmesg": read_text(commands / "companion-dmesg-identity.txt"),
        "service_blocks": read_text(commands / "service-blocks.txt"),
        "service_props": read_text(commands / "service-props.txt"),
        "processes": read_text(commands / "target-processes.txt"),
        "proc_identity": read_text(commands / "target-proc-identity.txt"),
        "binary_labels": read_text(commands / "binary-labels.txt"),
    }


def android_v521_text(android_dir: Path) -> dict[str, str]:
    commands = repo_path(android_dir) / "android" / "commands"
    return {
        "dmesg": read_text(commands / "companion-dmesg.txt"),
        "logcat": read_text(commands / "companion-logcat.txt"),
        "processes": read_text(commands / "companion-processes.txt"),
    }


def native_v615_text(v615_dir: Path) -> dict[str, str]:
    native = repo_path(v615_dir) / "native"
    return {
        "dmesg": read_text(native / "dmesg-delta.txt"),
        "companion": read_text(native / "companion-start-only-with-dsp-boot.txt"),
        "ps": read_text(native / "ps-before-reboot.txt"),
    }


def companion_order(keys: dict[str, str]) -> list[str]:
    order = keys.get("wifi_companion_start.order", "")
    return [item.strip() for item in order.split(",") if item.strip()]


def child_started(keys: dict[str, str], child: str) -> bool:
    return (
        keys.get(f"wifi_hal_composite_start.child.{child}.child_started") == "1"
        or keys.get(f"wifi_companion_start.child.{child}.start_order", "") != ""
    )


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def has_event(found: dict[str, Event], marker: str) -> bool:
    return marker in found


def extract_android_order(android_found: dict[str, Event]) -> list[str]:
    pairs = [
        ("qrtr_ns", event_time(android_found, "init_qrtr_ns_start")),
        ("pd_mapper", event_time(android_found, "init_pd_mapper_start")),
        ("rmt_storage", event_time(android_found, "init_rmt_storage_start")),
        ("tftp_server", event_time(android_found, "init_tftp_server_start")),
    ]
    if any(value is None for _, value in pairs):
        return []
    return [name for name, _ in sorted(pairs, key=lambda item: float(item[1] or 0.0))]


def first_line_with(text: str, pattern: str) -> str:
    compiled = re.compile(pattern, re.I)
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if compiled.search(line):
            return line
    return "missing"


def snapshot_hits(snapshot: str) -> dict[str, bool]:
    return {
        "start_rfs_access": bool(re.search(r"\bstart rfs_access\b", snapshot, re.I)),
        "service_rfs_access": bool(re.search(r"\bservice\s+(?:vendor\.)?rfs_access\b", snapshot, re.I)),
        "service_tftp_server": bool(re.search(r"\bservice\s+vendor\.tftp_server\s+/vendor/bin/tftp_server", snapshot, re.I)),
        "service_pd_mapper": bool(re.search(r"\bservice\s+vendor\.pd_mapper\s+/vendor/bin/pd-mapper", snapshot, re.I)),
        "service_rmt_storage": bool(re.search(r"\bservice\s+vendor\.rmt_storage\s+/vendor/bin/rmt_storage", snapshot, re.I)),
        "service_qrtr_ns": bool(re.search(r"\bservice\s+vendor\.qrtr-ns\s+/vendor/bin/qrtr-ns", snapshot, re.I)),
    }


def evidence_rows(android_found: dict[str, Event],
                  native_found: dict[str, Event],
                  android_order: list[str],
                  native_order: list[str],
                  keys: dict[str, str],
                  hits: dict[str, bool],
                  android_text: str,
                  native_text: str) -> list[list[str]]:
    return [
        [
            "rfs_access standalone service",
            "not proven / do not start directly",
            (
                f"start_line={bool_text(hits['start_rfs_access'])}; "
                f"service_block={bool_text(hits['service_rfs_access'])}; "
                f"android_process={bool_text(bool(re.search(r'\\brfs_access\\b', android_text, re.I)))}"
            ),
            "do not build a live rfs_access start-only target",
        ],
        [
            "vendor_rfs_access runtime domain",
            "already represented by tftp_server",
            (
                f"android_tftp_domain={bool_text(bool(re.search(r'u:r:vendor_rfs_access:s0.*tftp_server', android_text, re.I)))}; "
                f"native_tftp_domain={bool_text(bool(re.search(r'tftp_server\.selinux\.exec=u:r:vendor_rfs_access:s0', native_text, re.I)))}"
            ),
            "keep tftp_server, but do not add a duplicate rfs daemon",
        ],
        [
            "pd_mapper order",
            "strong actionable delta",
            f"android_order={','.join(android_order) or 'missing'}; native_order={','.join(native_order) or 'missing'}",
            "next live observer should replay qrtr_ns,pd_mapper,rmt_storage,tftp_server",
        ],
        [
            "rmt_storage/tftp readiness",
            "not sufficient as primary trigger",
            (
                f"android service_notifier_180->rmt_ready={delta_ms(android_found, 'rmt_storage_ready', 'service_notifier_180')}ms; "
                f"native rmt_ready but notifier={bool_text(has_event(native_found, 'service_notifier_180'))}"
            ),
            "do not repeat unchanged rmt/tftp-only order",
        ],
        [
            "service-locator",
            "insufficient evidence as sole prerequisite",
            (
                f"native_locator={bool_text(has_event(native_found, 'service_locator'))}; "
                f"native_notifier={bool_text(has_event(native_found, 'service_notifier_180'))}; "
                f"native_locator_failures={count_by_marker([event for event in native_found.values()]).get('service_locator_fail', 0)}"
            ),
            "observe lower QMI publication under Android order",
        ],
        [
            "CNSS/HAL/boot_wlan",
            "still blocked",
            (
                f"android_notifier_before_wlan_pd={bool_text((event_time(android_found, 'service_notifier_180') or 0) < (event_time(android_found, 'wlan_pd') or 999999))}; "
                f"native_pm_qos={count_by_marker(parse_events(native_text, 'native')).get('pm_qos_warning', 0)}"
            ),
            "keep no-CNSS/no-HAL/no-boot_wlan guardrail",
        ],
    ]


def classify(v617: dict[str, Any],
             android_found: dict[str, Event],
             native_found: dict[str, Event],
             android_order: list[str],
             native_order: list[str],
             keys: dict[str, str],
             hits: dict[str, bool],
             android_text: str,
             native_text: str) -> tuple[str, bool, str, str]:
    v617_ok = v617.get("decision") == "v617-qmi-service-registration-trigger-gap-classified" and bool(v617.get("pass"))
    tftp_domain_android = bool(re.search(r"u:r:vendor_rfs_access:s0.*tftp_server", android_text, re.I))
    tftp_domain_native = bool(re.search(r"tftp_server\.selinux\.exec=u:r:vendor_rfs_access:s0", native_text, re.I))
    rfs_is_alias = hits["start_rfs_access"] and not hits["service_rfs_access"] and tftp_domain_android and tftp_domain_native
    native_core_started = all(child_started(keys, child) for child in ("qrtr_ns", "rmt_storage", "tftp_server", "pd_mapper"))
    native_missing_notifier = not has_event(native_found, "service_notifier_180") and not has_event(native_found, "service_notifier_74")
    android_has_notifier = has_event(android_found, "service_notifier_180") and has_event(android_found, "service_notifier_74")
    order_delta = android_order == ANDROID_ORDER and native_order != ANDROID_ORDER

    if v617_ok and rfs_is_alias and native_core_started and native_missing_notifier and android_has_notifier and order_delta:
        return (
            "v618-rfs-alias-pd-mapper-order-gap-classified",
            True,
            (
                "`rfs_access` is not proven as a standalone service; Android maps RFS access to "
                "`vendor.tftp_server` in `vendor_rfs_access`, which V615 already replayed. "
                f"The remaining actionable delta is companion order: android={','.join(android_order)} "
                f"native={','.join(native_order)}"
            ),
            "V619 should implement a bounded no-CNSS/no-HAL Android-order observer: qrtr_ns -> pd_mapper -> rmt_storage -> tftp_server",
        )

    return (
        "v618-review-required",
        False,
        (
            f"v617_ok={v617_ok} rfs_is_alias={rfs_is_alias} native_core_started={native_core_started} "
            f"native_missing_notifier={native_missing_notifier} android_has_notifier={android_has_notifier} "
            f"order_delta={order_delta}"
        ),
        "refresh host-only evidence before designing a live observer",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v617 = load_json(args.v617_manifest)
    v615_texts = native_v615_text(args.v615_dir)
    v615_combined = "\n".join(v615_texts.values())
    keys = parse_key_values(v615_texts["companion"])
    v525_texts = android_v525_text(args.android_v525_dir)
    v521_texts = android_v521_text(args.android_v521_dir)
    android_combined = "\n".join(v525_texts.values()) + "\n" + "\n".join(v521_texts.values())
    snapshot = read_text(args.v614_snapshot)
    hits = snapshot_hits(snapshot)

    android_events = parse_events(android_combined, "android-existing")
    native_events = parse_events(v615_combined, "native-v615")
    android_found = first_by_marker(android_events)
    native_found = first_by_marker(native_events)
    android_counts = count_by_marker(android_events)
    native_counts = count_by_marker(native_events)
    android_order = extract_android_order(android_found)
    native_order = companion_order(keys)

    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v618-rfs-alias-order-classifier-plan-ready",
            True,
            "plan-only; classifier will use existing Android V521/V525 and native V615/V617 evidence",
            "run V618 host-only classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(
            v617,
            android_found,
            native_found,
            android_order,
            native_order,
            keys,
            hits,
            android_combined,
            v615_combined,
        )

    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v617_manifest": str(repo_path(args.v617_manifest)),
            "v615_dir": str(repo_path(args.v615_dir)),
            "v614_snapshot": str(repo_path(args.v614_snapshot)),
            "android_v525_dir": str(repo_path(args.android_v525_dir)),
            "android_v521_dir": str(repo_path(args.android_v521_dir)),
        },
        "prior": {
            "v617_decision": v617.get("decision"),
            "v617_pass": v617.get("pass"),
        },
        "android": {
            "order": android_order,
            "expected_order": ANDROID_ORDER,
            "counts": android_counts,
            "deltas_ms": {
                "pd_mapper_start_to_rmt_storage_start": delta_ms(android_found, "init_rmt_storage_start", "init_pd_mapper_start"),
                "pd_mapper_start_to_tftp_server_start": delta_ms(android_found, "init_tftp_server_start", "init_pd_mapper_start"),
                "pd_mapper_start_to_service_notifier_180": delta_ms(android_found, "service_notifier_180", "init_pd_mapper_start"),
                "sysmon_modem_to_service_notifier_180": delta_ms(android_found, "service_notifier_180", "sysmon_modem"),
                "service_notifier_180_to_rmt_storage_ready": delta_ms(android_found, "rmt_storage_ready", "service_notifier_180"),
            },
            "timeline_rows": timeline_rows(android_found, android_counts),
            "first_lines": {
                "start_rfs_access": first_line_with(snapshot, r"\bstart rfs_access\b"),
                "service_rfs_access": first_line_with(snapshot, r"\bservice\s+(?:vendor\.)?rfs_access\b"),
                "tftp_vendor_rfs_process": first_line_with(v525_texts["processes"], r"u:r:vendor_rfs_access:s0.*tftp_server"),
                "tftp_vendor_rfs_binary": first_line_with(v525_texts["binary_labels"], r"vendor_rfs_access_exec.*tftp_server"),
            },
        },
        "native_v615": {
            "order": native_order,
            "expected_android_order": ANDROID_ORDER,
            "counts": native_counts,
            "deltas_ms": {
                "sysmon_modem_to_service_locator_fail": delta_ms(native_found, "service_locator_fail", "sysmon_modem"),
                "sysmon_modem_to_rmt_storage_ready": delta_ms(native_found, "rmt_storage_ready", "sysmon_modem"),
                "sysmon_modem_to_service_locator": delta_ms(native_found, "service_locator", "sysmon_modem"),
                "sysmon_modem_to_service_notifier_180": delta_ms(native_found, "service_notifier_180", "sysmon_modem"),
            },
            "child_started": {
                child: child_started(keys, child)
                for child in ("qrtr_ns", "pd_mapper", "rmt_storage", "tftp_server", "rfs_access")
            },
            "companion_result": keys.get("wifi_companion_start.result", ""),
            "service_notifier_captured": keys.get("wifi_companion_start.surface_window.service_notifier_captured", ""),
            "timeline_rows": timeline_rows(native_found, native_counts),
            "first_lines": {
                "tftp_vendor_rfs_exec": first_line_with(v615_texts["companion"], r"tftp_server\.selinux\.exec=u:r:vendor_rfs_access:s0"),
                "pd_mapper_start_order": first_line_with(v615_texts["companion"], r"wifi_companion_start\.child\.pd_mapper\.start_order="),
            },
        },
        "vendor_init_hits": hits,
        "evidence_rows": evidence_rows(
            android_found,
            native_found,
            android_order,
            native_order,
            keys,
            hits,
            android_combined,
            v615_combined,
        ),
        "inferences": {
            "rfs_access_direct_start_not_authorized": True,
            "tftp_server_already_replays_vendor_rfs_access_domain": bool(
                re.search(r"tftp_server\.selinux\.exec=u:r:vendor_rfs_access:s0", v615_combined, re.I)
            ),
            "android_pd_mapper_before_rmt_tftp": android_order == ANDROID_ORDER,
            "native_pd_mapper_after_rmt_tftp": native_order == ["qrtr_ns", "rmt_storage", "tftp_server", "pd_mapper"],
            "android_order_observer_is_next_minimal_live_gate": True,
            "wifi_bringup_still_blocked": True,
        },
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
    android = manifest["android"]
    native = manifest["native_v615"]
    return "\n".join([
        "# V618 RFS Alias and Companion Ordering Classifier",
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
        "## Android Order and Timing",
        "",
        markdown_table(
            ["key", "value"],
            [
                ["order", ",".join(android["order"])],
                ["expected_order", ",".join(android["expected_order"])],
            ],
        ),
        "",
        markdown_table(["delta", "ms"], [[key, str(value)] for key, value in android["deltas_ms"].items()]),
        "",
        "## Native V615 Order and Timing",
        "",
        markdown_table(
            ["key", "value"],
            [
                ["order", ",".join(native["order"])],
                ["expected_android_order", ",".join(native["expected_android_order"])],
                ["child_started", str(native["child_started"])],
                ["companion_result", native["companion_result"]],
                ["service_notifier_captured", native["service_notifier_captured"]],
            ],
        ),
        "",
        markdown_table(["delta", "ms"], [[key, str(value)] for key, value in native["deltas_ms"].items()]),
        "",
        "## Android First Lines",
        "",
        markdown_table(["key", "line"], [[key, value] for key, value in android["first_lines"].items()]),
        "",
        "## Native First Lines",
        "",
        markdown_table(["key", "line"], [[key, value] for key, value in native["first_lines"].items()]),
        "",
        "## Android Markers",
        "",
        markdown_table(["marker", "count", "time", "line"], android["timeline_rows"]),
        "",
        "## Native Markers",
        "",
        markdown_table(["marker", "count", "time", "line"], native["timeline_rows"]),
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
