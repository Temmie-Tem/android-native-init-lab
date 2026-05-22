#!/usr/bin/env python3
"""V617 host-only Android init/QMI trigger candidate classifier.

This classifier compares existing Android boot evidence with the latest native
V615/V616 post-sibling-sysmon evidence. It does not contact the device, write
sysfs, start daemons, start service-manager, start Wi-Fi HAL, scan, connect,
use credentials, run DHCP, change routes, or ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v617-android-init-trigger-candidate-classifier")
DEFAULT_ANDROID_V521_DIR = Path(
    "tmp/wifi/v524-android-companion-exact-recapture-handoff/"
    "v521-android-companion-recapture-run"
)
DEFAULT_ANDROID_V611_DIR = Path(
    "tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/"
    "v611-android-lower-surface-recapture-run"
)
DEFAULT_V614_MANIFEST = Path("tmp/wifi/v614-mdm3-trigger-path-classifier/manifest.json")
DEFAULT_V614_SNAPSHOT = Path(
    "tmp/wifi/v614-mdm3-trigger-path-classifier/native/vendor-init-readonly-snapshot.txt"
)
DEFAULT_V615_DIR = Path("tmp/wifi/v615-dsp-boot-20260523-015352/v615-live")
DEFAULT_V616_MANIFEST = Path(
    "tmp/wifi/v616-post-sibling-sysmon-service-notifier-classifier/manifest.json"
)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
PROP_RE = re.compile(r"^\[([^]]+)]: \[([^]]*)]$")


@dataclass(frozen=True)
class Event:
    marker: str
    timestamp: float | None
    line: str
    source: str


MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("init_qrtr_ns_start", re.compile(r"starting service 'vendor\.qrtr-ns'", re.I)),
    ("init_rmt_storage_start", re.compile(r"starting service 'vendor\.rmt_storage'", re.I)),
    ("init_tftp_server_start", re.compile(r"starting service 'vendor\.tftp_server'", re.I)),
    ("init_cnss_diag_start", re.compile(r"starting service 'cnss_diag'", re.I)),
    ("init_cnss_daemon_start", re.compile(r"starting service 'cnss-daemon'", re.I)),
    ("init_wifi_hal_legacy_start", re.compile(r"starting service 'vendor\.wifi_hal_legacy'", re.I)),
    ("init_wifi_hal_ext_start", re.compile(r"starting service 'vendor\.wifi_hal_ext'", re.I)),
    ("init_wificond_start", re.compile(r"starting service 'wificond'", re.I)),
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
    ("service_locator", re.compile(r"servloc: service_locator_new_server: Connection established", re.I)),
    ("service_locator_fail", re.compile(r"servloc: .*Unable to connect to service locator", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I)),
    ("wlan_pd_ack_180", re.compile(r"service-notifier: send_ind_ack:.*instance 180", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("cnss_diag_netlink", re.compile(r"cnss_diag.*netlink|diag: In cnss_nl_srv_init", re.I)),
    ("cnss_wlfw_start", re.compile(r"cnss-daemon.*wlfw_start: Starting", re.I)),
    ("tftp_wlanmdsp", re.compile(r"tftp_server:.*wlanmdsp\.mbn", re.I)),
    ("tftp_rfs_request", re.compile(r"tftp_server:.*vendor/rfs/.*/mpss", re.I)),
    ("rmt_storage_ready", re.compile(r"rmt_storage:INFO:main: Done with init", re.I)),
    ("rmt_storage_open", re.compile(r"rmt_storage_open_cb: Processing: Open Request", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("pm_qos_warning", re.compile(r"pm_qos_add_request\(\) called for already added request", re.I)),
)

TIMELINE_MARKERS = [
    "init_qrtr_ns_start",
    "qrtr_rx",
    "qrtr_tx",
    "sysmon_modem",
    "sysmon_cdsp",
    "sysmon_slpi",
    "sysmon_adsp",
    "init_rmt_storage_start",
    "service_notifier_180",
    "init_tftp_server_start",
    "service_notifier_74",
    "rmt_storage_ready",
    "rmt_storage_open",
    "service_locator",
    "service_locator_fail",
    "init_cnss_diag_start",
    "cnss_diag_netlink",
    "init_cnss_daemon_start",
    "cnss_wlfw_start",
    "wlan_pd",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
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


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-v521-dir", type=Path, default=DEFAULT_ANDROID_V521_DIR)
    parser.add_argument("--android-v611-dir", type=Path, default=DEFAULT_ANDROID_V611_DIR)
    parser.add_argument("--v614-manifest", type=Path, default=DEFAULT_V614_MANIFEST)
    parser.add_argument("--v614-snapshot", type=Path, default=DEFAULT_V614_SNAPSHOT)
    parser.add_argument("--v615-dir", type=Path, default=DEFAULT_V615_DIR)
    parser.add_argument("--v616-manifest", type=Path, default=DEFAULT_V616_MANIFEST)
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


def parse_props(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = PROP_RE.match(clean_line(raw_line))
        if match:
            values[match.group(1)] = match.group(2)
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


def android_v521_text(android_dir: Path) -> dict[str, str]:
    commands = repo_path(android_dir) / "android" / "commands"
    return {
        "dmesg": read_text(commands / "companion-dmesg.txt"),
        "logcat": read_text(commands / "companion-logcat.txt"),
        "props": read_text(commands / "companion-props.txt"),
        "processes": "\n".join([
            read_text(commands / "companion-processes-wide.txt"),
            read_text(commands / "companion-processes.txt"),
        ]),
        "initrc": read_text(commands / "companion-initrc.txt"),
        "binaries": read_text(commands / "companion-binaries.txt"),
    }


def android_v611_text(android_dir: Path) -> str:
    commands = repo_path(android_dir) / "android" / "commands"
    return "\n".join([
        read_text(commands / "dmesg-lower-surface-tail.txt"),
        read_text(commands / "dmesg-unfiltered-tail.txt"),
    ])


def native_v615_text(v615_dir: Path) -> dict[str, str]:
    native = repo_path(v615_dir) / "native"
    return {
        "dmesg": read_text(native / "dmesg-delta.txt"),
        "companion": read_text(native / "companion-start-only-with-dsp-boot.txt"),
        "ps": read_text(native / "ps-before-reboot.txt"),
        "rpmsg": read_text(native / "rpmsg-after-companion.txt"),
        "proc_net_qrtr": read_text(native / "proc-net-qrtr-after-companion.txt"),
    }


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def service_props(props: dict[str, str], names: list[str]) -> dict[str, str]:
    return {name: props.get(f"init.svc.{name}", "") for name in names}


def boottime_props(props: dict[str, str], names: list[str]) -> dict[str, str]:
    return {name: props.get(f"ro.boottime.{name}", "") for name in names}


def snapshot_hits(snapshot: str) -> dict[str, bool]:
    return {
        "start_rfs_access": bool(re.search(r"\bstart rfs_access\b", snapshot, re.I)),
        "start_wcnss_service": bool(re.search(r"\bstart wcnss-service\b", snapshot, re.I)),
        "service_mdm_helper": bool(re.search(r"\bservice vendor\.mdm_helper\b", snapshot, re.I)),
        "service_mdm_launcher": bool(re.search(r"\bservice vendor\.mdm_launcher\b", snapshot, re.I)),
        "boot_wlan_permission_only": bool(re.search(r"/sys/kernel/boot_wlan/boot_wlan", snapshot, re.I)),
        "service_cnss_daemon": bool(re.search(r"\bservice cnss-daemon\b", snapshot, re.I)),
        "service_cnss_diag": bool(re.search(r"\bservice cnss_diag\b", snapshot, re.I)),
        "service_qrtr_ns": bool(re.search(r"\bservice vendor\.qrtr-ns\b", snapshot, re.I)),
        "service_rmt_storage": bool(re.search(r"\bservice vendor\.rmt_storage\b", snapshot, re.I)),
        "service_tftp_server": bool(re.search(r"\bservice vendor\.tftp_server\b", snapshot, re.I)),
        "service_pd_mapper": bool(re.search(r"\bservice vendor\.pd_mapper\b", snapshot, re.I)),
    }


def companion_order(keys: dict[str, str]) -> list[str]:
    order = keys.get("wifi_companion_start.order", "")
    return [item.strip() for item in order.split(",") if item.strip()]


def child_started(keys: dict[str, str], child: str) -> bool:
    return (
        keys.get(f"wifi_hal_composite_start.child.{child}.child_started") == "1"
        or keys.get(f"wifi_companion_start.child.{child}.start_order", "") != ""
    )


def sibling_sysmon_present(found: dict[str, Event]) -> bool:
    return all(has(found, marker) for marker in ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp"))


def service_notifier_pair_present(found: dict[str, Event]) -> bool:
    return has(found, "service_notifier_180") and has(found, "service_notifier_74")


def first_line_with(text: str, pattern: str) -> str:
    compiled = re.compile(pattern, re.I)
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if compiled.search(line):
            return line
    return "missing"


def candidate_rows(android_found: dict[str, Event],
                   native_found: dict[str, Event],
                   keys: dict[str, str],
                   props: dict[str, str],
                   processes: str,
                   snapshot: str,
                   hits: dict[str, bool]) -> list[list[str]]:
    order = companion_order(keys)
    rows = [
        [
            "QMI service registration",
            "strong gap",
            (
                f"Android service_notifier_180 after sysmon={delta_ms(android_found, 'service_notifier_180', 'sysmon_modem')}ms; "
                f"native sibling_sysmon={bool_text(sibling_sysmon_present(native_found))}, "
                f"service_notifier={bool_text(service_notifier_pair_present(native_found))}"
            ),
            "classify lower QMI publication prerequisite before daemon retry",
        ],
        [
            "rfs_access",
            "medium candidate",
            (
                f"Android init starts rfs_access={bool_text(hits['start_rfs_access'])}; "
                f"V615 companion_order={','.join(order) or 'missing'}; "
                f"native_replayed={bool_text('rfs_access' in order)}"
            ),
            "next host-only exact dependency/timing classifier; live only after contract is explicit",
        ],
        [
            "rmt_storage/tftp_server/pd_mapper",
            "already replayed",
            (
                f"rmt={bool_text(child_started(keys, 'rmt_storage'))}, "
                f"tftp={bool_text(child_started(keys, 'tftp_server'))}, "
                f"pd_mapper={bool_text(child_started(keys, 'pd_mapper'))}; "
                f"service_notifier_captured={keys.get('wifi_companion_start.surface_window.service_notifier_captured', '')}"
            ),
            "not sufficient alone; preserve order but do not repeat unchanged",
        ],
        [
            "wcnss-service",
            "weak/unproven",
            (
                f"start reference={bool_text(hits['start_wcnss_service'])}; "
                f"init.svc.wcnss-service={props.get('init.svc.wcnss-service', '') or 'absent'}; "
                f"process={bool_text(bool(re.search(r'\\bwcnss-service\\b', processes, re.I)))}"
            ),
            "do not direct-start until service definition/process evidence is found",
        ],
        [
            "vendor.mdm_helper/launcher",
            "weak/unproven",
            (
                f"mdm_helper_service={bool_text(hits['service_mdm_helper'])}; "
                f"mdm_launcher_service={bool_text(hits['service_mdm_launcher'])}; "
                f"init.svc.vendor.mdm_helper={props.get('init.svc.vendor.mdm_helper', '') or 'absent'}"
            ),
            "recapture mdm/rfs terms or statically resolve init.mdm.sh before live start",
        ],
        [
            "boot_wlan/qcwlanstate",
            "blocked",
            (
                f"boot_wlan_permission_only={bool_text(hits['boot_wlan_permission_only'])}; "
                f"native_pm_qos_warnings={count_by_marker(parse_events(keys.get('_native_dmesg', ''), 'native')).get('pm_qos_warning', 0)}"
            ),
            "still below lower readiness; no boot_wlan/qcwlanstate retry",
        ],
        [
            "cnss-daemon/HAL",
            "too late",
            (
                f"service_notifier before cnss_diag={bool_text((event_time(android_found, 'service_notifier_180') or 0) < (event_time(android_found, 'init_cnss_diag_start') or 999999))}; "
                f"native_wlfw={bool_text(has(native_found, 'cnss_wlfw_start'))}"
            ),
            "daemon/HAL remain gated behind QMI publication",
        ],
    ]
    return rows


def classify(android_found: dict[str, Event],
             native_found: dict[str, Event],
             keys: dict[str, str],
             v616: dict[str, Any],
             hits: dict[str, bool]) -> tuple[str, bool, str, str]:
    if not android_found or not native_found:
        return (
            "v617-input-evidence-missing",
            False,
            f"android_events={bool(android_found)} native_events={bool(native_found)}",
            "refresh host-only input evidence before any live action",
        )

    android_notifier = service_notifier_pair_present(android_found)
    native_sibling = sibling_sysmon_present(native_found)
    native_notifier = service_notifier_pair_present(native_found)
    native_service_locator = has(native_found, "service_locator") or has(native_found, "service_locator_fail")
    v616_ok = v616.get("decision") == "v616-post-sibling-sysmon-service-notifier-gap-classified" and bool(v616.get("pass"))
    replayed_core = all(child_started(keys, child) for child in ("qrtr_ns", "rmt_storage", "tftp_server", "pd_mapper"))
    rfs_unreplayed = hits.get("start_rfs_access", False) and "rfs_access" not in companion_order(keys)
    sysmon_to_service = delta_ms(android_found, "service_notifier_180", "sysmon_modem")
    service_before_cnss = (
        event_time(android_found, "service_notifier_180") is not None
        and event_time(android_found, "init_cnss_diag_start") is not None
        and event_time(android_found, "service_notifier_180") < event_time(android_found, "init_cnss_diag_start")
    )

    if (
        v616_ok
        and android_notifier
        and native_sibling
        and not native_notifier
        and native_service_locator
        and replayed_core
        and service_before_cnss
    ):
        return (
            "v617-qmi-service-registration-trigger-gap-classified",
            True,
            (
                "Android publishes service-notifier 180/74 immediately after sysmon and before CNSS/HAL, "
                f"while V615 replays qrtr/rmt_storage/tftp_server/pd_mapper and reaches sibling sysmon/service-locator "
                f"without notifier; sysmon_to_service_notifier_180={sysmon_to_service}ms, rfs_unreplayed={rfs_unreplayed}"
            ),
            "V618 should host-only classify rfs_access/service-locator/QMI-publication dependencies and only then design a bounded no-HAL observer",
        )

    return (
        "v617-review-required",
        False,
        (
            f"v616_ok={v616_ok} android_notifier={android_notifier} native_sibling={native_sibling} "
            f"native_notifier={native_notifier} native_service_locator={native_service_locator} "
            f"replayed_core={replayed_core} service_before_cnss={service_before_cnss}"
        ),
        "inspect evidence drift before choosing the next Wi-Fi gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    android_texts = android_v521_text(args.android_v521_dir)
    android_v611 = android_v611_text(args.android_v611_dir)
    native_texts = native_v615_text(args.v615_dir)
    native_text = "\n".join(native_texts.values())
    keys = parse_key_values(native_texts["companion"])
    keys["_native_dmesg"] = native_texts["dmesg"]
    props = parse_props(android_texts["props"])
    v614 = load_json(args.v614_manifest)
    v616 = load_json(args.v616_manifest)
    snapshot = read_text(args.v614_snapshot)
    hits = snapshot_hits(snapshot)

    android_events = parse_events("\n".join(android_texts.values()), "android-v521-existing")
    android_v611_events = parse_events(android_v611, "android-v611-existing")
    native_events = parse_events(native_text, "native-v615")
    android_found = first_by_marker(android_events)
    native_found = first_by_marker(native_events)
    android_counts = count_by_marker(android_events)
    native_counts = count_by_marker(native_events)

    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v617-android-init-trigger-candidate-plan-ready",
            True,
            "plan-only; classifier will use existing Android V521/V611 and native V615/V616 evidence",
            "run V617 host-only classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(android_found, native_found, keys, v616, hits)

    android_deltas = {
        "sysmon_modem_to_service_notifier_180": delta_ms(android_found, "service_notifier_180", "sysmon_modem"),
        "sysmon_modem_to_service_notifier_74": delta_ms(android_found, "service_notifier_74", "sysmon_modem"),
        "service_notifier_180_to_service_notifier_74": delta_ms(android_found, "service_notifier_74", "service_notifier_180"),
        "service_notifier_180_to_rmt_storage_ready": delta_ms(android_found, "rmt_storage_ready", "service_notifier_180"),
        "service_notifier_180_to_cnss_diag_start": delta_ms(android_found, "init_cnss_diag_start", "service_notifier_180"),
        "service_notifier_180_to_wlan_pd": delta_ms(android_found, "wlan_pd", "service_notifier_180"),
        "wlan_pd_to_qmi_server_connected": delta_ms(android_found, "qmi_server_connected", "wlan_pd"),
    }
    native_deltas = {
        "sysmon_modem_to_service_locator": delta_ms(native_found, "service_locator", "sysmon_modem"),
        "sysmon_modem_to_service_locator_fail": delta_ms(native_found, "service_locator_fail", "sysmon_modem"),
        "sysmon_modem_to_service_notifier_180": delta_ms(native_found, "service_notifier_180", "sysmon_modem"),
        "sysmon_modem_to_rmt_storage_ready": delta_ms(native_found, "rmt_storage_ready", "sysmon_modem"),
    }
    service_names = [
        "vendor.qrtr-ns",
        "vendor.rmt_storage",
        "vendor.tftp_server",
        "vendor.pd_mapper",
        "cnss_diag",
        "cnss-daemon",
        "wcnss-service",
        "vendor.mdm_helper",
        "vendor.mdm_launcher",
        "vendor.wifi_hal_legacy",
        "vendor.wifi_hal_ext",
        "wificond",
    ]

    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "android_v521_dir": str(repo_path(args.android_v521_dir)),
            "android_v611_dir": str(repo_path(args.android_v611_dir)),
            "v614_manifest": str(repo_path(args.v614_manifest)),
            "v614_snapshot": str(repo_path(args.v614_snapshot)),
            "v615_dir": str(repo_path(args.v615_dir)),
            "v616_manifest": str(repo_path(args.v616_manifest)),
        },
        "android": {
            "event_count": len(android_events),
            "v611_supplemental_event_count": len(android_v611_events),
            "counts": android_counts,
            "deltas_ms": android_deltas,
            "timeline_rows": timeline_rows(android_found, android_counts),
            "service_props": service_props(props, service_names),
            "boottime_props": boottime_props(props, service_names),
            "process_presence": {
                "wcnss_service": bool(re.search(r"\bwcnss-service\b", android_texts["processes"], re.I)),
                "mdm_helper": bool(re.search(r"\bmdm_helper\b", android_texts["processes"], re.I)),
                "mdm_launcher": bool(re.search(r"\bmdm_launcher\b", android_texts["processes"], re.I)),
                "tftp_server": bool(re.search(r"\btftp_server\b", android_texts["processes"], re.I)),
                "wcnss_kernel_threads": bool(re.search(r"\[WCNSS_", android_texts["processes"])),
            },
            "first_lines": {
                "rfs_access": first_line_with(snapshot, r"\bstart rfs_access\b"),
                "wcnss_service": first_line_with(snapshot, r"\bstart wcnss-service\b"),
                "mdm_helper": first_line_with(snapshot, r"\bservice vendor\.mdm_helper\b"),
                "boot_wlan": first_line_with(snapshot, r"/sys/kernel/boot_wlan/boot_wlan"),
                "tftp_wlanmdsp": first_line_with(android_texts["logcat"], r"wlanmdsp\.mbn"),
            },
        },
        "native_v615": {
            "event_count": len(native_events),
            "counts": native_counts,
            "deltas_ms": native_deltas,
            "companion_order": companion_order(keys),
            "child_started": {
                child: child_started(keys, child)
                for child in ("qrtr_ns", "rmt_storage", "tftp_server", "pd_mapper", "rfs_access")
            },
            "companion_result": keys.get("wifi_companion_start.result", ""),
            "all_observable": keys.get("wifi_companion_start.all_observable", ""),
            "all_postflight_safe": keys.get("wifi_companion_start.all_postflight_safe", ""),
            "service_notifier_captured": keys.get("wifi_companion_start.surface_window.service_notifier_captured", ""),
            "wlfw_readback_matrix": keys.get("wifi_companion_qrtr_readback.matrix", ""),
            "timeline_rows": timeline_rows(native_found, native_counts),
        },
        "prior_classifiers": {
            "v614_decision": v614.get("decision"),
            "v614_pass": v614.get("pass"),
            "v616_decision": v616.get("decision"),
            "v616_pass": v616.get("pass"),
        },
        "vendor_init_hits": hits,
        "candidate_rows": candidate_rows(
            android_found,
            native_found,
            keys,
            props,
            android_texts["processes"],
            snapshot,
            hits,
        ),
        "inferences": {
            "service_notifier_is_kernel_qmi_callback": True,
            "userspace_cnss_daemon_not_primary_trigger": True,
            "android_service_notifier_precedes_cnss_diag": (
                event_time(android_found, "service_notifier_180") is not None
                and event_time(android_found, "init_cnss_diag_start") is not None
                and event_time(android_found, "service_notifier_180") < event_time(android_found, "init_cnss_diag_start")
            ),
            "native_core_companion_replayed": all(
                child_started(keys, child) for child in ("qrtr_ns", "rmt_storage", "tftp_server", "pd_mapper")
            ),
            "native_rfs_access_unreplayed": hits.get("start_rfs_access", False) and not child_started(keys, "rfs_access"),
            "direct_wcnss_mdm_boot_wlan_live_retry_blocked": True,
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
        "# V617 Android Init/QMI Trigger Candidate Classifier",
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
        "## Candidate Matrix",
        "",
        markdown_table(["candidate", "classification", "evidence", "next"], manifest["candidate_rows"]),
        "",
        "## Android Timing",
        "",
        markdown_table(["delta", "ms"], [[key, str(value)] for key, value in android["deltas_ms"].items()]),
        "",
        "## Native V615 Timing",
        "",
        markdown_table(["delta", "ms"], [[key, str(value)] for key, value in native["deltas_ms"].items()]),
        "",
        "## Android Service Props",
        "",
        markdown_table(["service", "state"], [[key, value or "absent"] for key, value in android["service_props"].items()]),
        "",
        "## Native V615 Companion State",
        "",
        markdown_table(
            ["key", "value"],
            [
                ["companion_order", ",".join(native["companion_order"])],
                ["child_started", str(native["child_started"])],
                ["companion_result", native["companion_result"]],
                ["all_observable", native["all_observable"]],
                ["all_postflight_safe", native["all_postflight_safe"]],
                ["service_notifier_captured", native["service_notifier_captured"]],
                ["wlfw_readback_matrix", native["wlfw_readback_matrix"]],
            ],
        ),
        "",
        "## Android Timeline Markers",
        "",
        markdown_table(["marker", "count", "time", "line"], android["timeline_rows"]),
        "",
        "## Native V615 Timeline Markers",
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
