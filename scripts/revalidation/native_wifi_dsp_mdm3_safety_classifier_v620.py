#!/usr/bin/env python3
"""V620 host-only DSP/MDM3 safety classifier.

This classifier consolidates V615/V619 direct DSP boot-node observations with
Android lower-surface evidence. It does not contact the device, write sysfs,
start daemons, start service-manager, start Wi-Fi HAL, scan, connect, use
credentials, run DHCP, change routes, or ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v620-dsp-mdm3-safety-classifier")
DEFAULT_ANDROID_V611_MANIFEST = Path(
    "tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/"
    "v611-android-lower-surface-recapture-run/manifest.json"
)
DEFAULT_ANDROID_V611_DIR = Path(
    "tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/"
    "v611-android-lower-surface-recapture-run"
)
DEFAULT_V614_SNAPSHOT = Path(
    "tmp/wifi/v614-mdm3-trigger-path-classifier/native/vendor-init-readonly-snapshot.txt"
)
DEFAULT_V615_DIR = Path("tmp/wifi/v615-dsp-boot-20260523-015352/v615-live")
DEFAULT_V616_MANIFEST = Path("tmp/wifi/v616-post-sibling-sysmon-service-notifier-classifier/manifest.json")
DEFAULT_V617_MANIFEST = Path("tmp/wifi/v617-android-init-trigger-candidate-classifier/manifest.json")
DEFAULT_V618_MANIFEST = Path("tmp/wifi/v618-rfs-alias-order-classifier/manifest.json")
DEFAULT_V619_MANIFEST = Path("tmp/wifi/v619-android-order-post-sysmon-observer-run/manifest.json")
DEFAULT_V619_DIR = Path("tmp/wifi/v619-android-order-post-sysmon-observer-run")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")

ANDROID_ORDER = ["qrtr_ns", "pd_mapper", "rmt_storage", "tftp_server"]

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
    ("pm_qos_warning", re.compile(r"pm_qos_add_request\(\) called for already added request", re.I)),
    ("pm_qos_calltrace", re.compile(r"pm_qos_add_request\+|kernel/power/qos\.c:616", re.I)),
    ("asoc_probe", re.compile(r"msm_asoc_machine_probe", re.I)),
    ("init_mdm_helper_start", re.compile(r"starting service 'vendor\.mdm_helper'", re.I)),
    ("init_mdm_launcher_start", re.compile(r"starting service 'vendor\.mdm_launcher'", re.I)),
    ("init_wcnss_service_start", re.compile(r"starting service 'wcnss-service'", re.I)),
    ("init_cnss_diag_start", re.compile(r"starting service 'cnss_diag'", re.I)),
    ("init_cnss_daemon_start", re.compile(r"starting service 'cnss-daemon'", re.I)),
)

TIMELINE_MARKERS = [
    "modem_pil",
    "qrtr_rx",
    "adsp_pil",
    "cdsp_pil",
    "slpi_pil",
    "qrtr_tx",
    "sysmon_modem",
    "sysmon_slpi",
    "sysmon_cdsp",
    "sysmon_adsp",
    "service_locator",
    "service_locator_fail",
    "service_notifier_180",
    "service_notifier_74",
    "rmt_storage_ready",
    "rmt_storage_open",
    "wlan_pd",
    "wlan_pd_ack_180",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wlan0",
    "sysmon_esoc0",
    "pm_qos_warning",
    "asoc_probe",
]

FORBIDDEN_ACTIONS = [
    "device command",
    "sysfs write",
    "DSP boot-node write",
    "boot_wlan/qcwlanstate write",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
]

EXTERNAL_REFERENCES = [
    {
        "title": "postmarketOS SDM845 Wi-Fi notes",
        "url": "https://wiki.postmarketos.org/wiki/Qualcomm_Snapdragon_845/850_%28SDM845/SDM850%29",
        "relevance": "Adjacent Qualcomm Wi-Fi notes list rmtfs, pd-mapper, and tqftpserv as firmware-loading prerequisites.",
    },
    {
        "title": "pmaports QRTR dependency issue",
        "url": "https://gitlab.com/postmarketOS/pmaports/-/issues/863",
        "relevance": "pmaports discusses pd-mapper/tqftpserv dependence on QRTR or kernel QRTR availability.",
    },
    {
        "title": "Ubuntu tqftpserv package",
        "url": "https://launchpad.net/ubuntu/+source/tqftpserv",
        "relevance": "Distribution metadata identifies tqftpserv as a TFTP server for the QRTR protocol.",
    },
    {
        "title": "postmarketOS tqftpserv init script",
        "url": "https://gitlab.com/postmarketOS/pmaports/-/raw/master/modem/tqftpserv/tqftpserv.initd",
        "relevance": "tqftpserv is ordered before rmtfs and uses qrtr-ns; useful for companion ordering checks, not esoc0 triggering.",
    },
    {
        "title": "postmarketOS pd-mapper init script",
        "url": "https://gitlab.com/postmarketOS/pmaports/-/raw/master/modem/pd-mapper/pd-mapper.initd",
        "relevance": "pd-mapper wants qrtr-ns; aligns with native lower companion sequencing already tested.",
    },
    {
        "title": "postmarketOS SM8150 kernel package",
        "url": "https://pkgs.postmarketos.org/package/master/postmarketos/aarch64/linux-postmarketos-qcom-sm8150",
        "relevance": "SM8150 mainline package confirms adjacent platform work exists, but does not provide a vendor-kernel mdm_helper/esoc recipe.",
    },
]

MDM_HELPER_PATH_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "mdm_helper_service",
        re.compile(r"service\s+vendor\.mdm_helper\s+/vendor/bin/mdm_helper", re.I),
        "Android init declares the long-running mdm_helper service.",
    ),
    (
        "mdm_launcher_service",
        re.compile(r"service\s+vendor\.mdm_launcher\s+/vendor/bin/sh\s+/vendor/bin/init\.mdm\.sh", re.I),
        "Android init declares mdm_launcher as a shell wrapper.",
    ),
    (
        "mdm_launcher_reads_baseband",
        re.compile(r"baseband=`getprop\s+ro\.baseband`", re.I),
        "The wrapper gates mdm_helper through ro.baseband.",
    ),
    (
        "mdm_launcher_starts_helper",
        re.compile(r"\bstart\s+vendor\.mdm_helper\b", re.I),
        "The wrapper starts mdm_helper through Android init.",
    ),
    (
        "static_esoc_path_visible",
        re.compile(r"/dev/esoc|/sys/(?:bus/)?(?:esoc|subsys)|subsys_esoc0|esoc0", re.I),
        "A raw esoc/sysfs path is visible in the init snapshot.",
    ),
    (
        "static_ioctl_hint_visible",
        re.compile(r"\bioctl\b", re.I),
        "An ioctl-style helper path is visible in the init snapshot.",
    ),
)


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
    parser.add_argument("--android-v611-manifest", type=Path, default=DEFAULT_ANDROID_V611_MANIFEST)
    parser.add_argument("--android-v611-dir", type=Path, default=DEFAULT_ANDROID_V611_DIR)
    parser.add_argument("--v614-snapshot", type=Path, default=DEFAULT_V614_SNAPSHOT)
    parser.add_argument("--v615-dir", type=Path, default=DEFAULT_V615_DIR)
    parser.add_argument("--v616-manifest", type=Path, default=DEFAULT_V616_MANIFEST)
    parser.add_argument("--v617-manifest", type=Path, default=DEFAULT_V617_MANIFEST)
    parser.add_argument("--v618-manifest", type=Path, default=DEFAULT_V618_MANIFEST)
    parser.add_argument("--v619-manifest", type=Path, default=DEFAULT_V619_MANIFEST)
    parser.add_argument("--v619-dir", type=Path, default=DEFAULT_V619_DIR)
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


def android_v611_text(android_dir: Path) -> str:
    commands = repo_path(android_dir) / "android" / "commands"
    return "\n".join([
        read_text(commands / "dmesg-lower-surface-tail.txt"),
        read_text(commands / "dmesg-unfiltered-tail.txt"),
    ])


def native_v615_text(v615_dir: Path) -> str:
    native = repo_path(v615_dir) / "native"
    return "\n".join([
        read_text(native / "dmesg-delta.txt"),
        read_text(native / "companion-start-only-with-dsp-boot.txt"),
        read_text(native / "rpmsg-after-companion.txt"),
        read_text(native / "proc-net-qrtr-after-companion.txt"),
    ])


def native_v619_text(v619_dir: Path) -> str:
    native = repo_path(v619_dir) / "native"
    return "\n".join([
        read_text(native / "dmesg-delta.txt"),
        read_text(native / "companion-start-only-with-dsp-boot.txt"),
        read_text(native / "rpmsg-after-companion.txt"),
        read_text(native / "rpmsg-after-dsp-boot.txt"),
        read_text(native / "proc-net-qrtr-after-companion.txt"),
    ])


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def safe_get(mapping: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def companion_order(keys: dict[str, str]) -> list[str]:
    raw_order = keys.get("wifi_companion_start.order", "")
    return [item.strip() for item in raw_order.split(",") if item.strip()]


def first_line_with(text: str, pattern: str) -> str:
    compiled = re.compile(pattern, re.I)
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if compiled.search(line):
            return line
    return "missing"


def vendor_static_hits(snapshot: str, v616: dict[str, Any], v617: dict[str, Any]) -> dict[str, Any]:
    hint_rows = v616.get("vendor_init_hints") or []
    hints = {row[0]: row for row in hint_rows if isinstance(row, list) and row}
    return {
        "boot_adsp_write": hints.get("boot_adsp_write", []),
        "boot_cdsp_write": hints.get("boot_cdsp_write", []),
        "boot_slpi_write": hints.get("boot_slpi_write", []),
        "boot_wlan_permission": hints.get("boot_wlan_permission", []),
        "wcnss_service_trigger": hints.get("wcnss_service_trigger", []),
        "mdm_launcher_service": hints.get("mdm_launcher_service", []),
        "mdm_helper_service": hints.get("mdm_helper_service", []),
        "mdm_helper_baseband_gate": hints.get("mdm_helper_baseband_gate", []),
        "init_mdm_sh_start_helper": first_line_with(snapshot, r"\bstart vendor\.mdm_helper\b"),
        "wcnss_service_start_ref": first_line_with(snapshot, r"\bstart wcnss-service\b"),
        "boot_wlan_permission_line": first_line_with(snapshot, r"/sys/kernel/boot_wlan/boot_wlan"),
        "v617_candidates": v617.get("candidate_rows", []),
    }


def mdm_helper_path_rows(snapshot: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for key, pattern, interpretation in MDM_HELPER_PATH_PATTERNS:
        line = first_line_with(snapshot, pattern.pattern)
        rows.append([
            key,
            bool_text(line != "missing"),
            line,
            interpretation,
        ])
    return rows


def evidence_rows(manifest: dict[str, Any]) -> list[list[str]]:
    android = manifest["android_v611"]
    v615 = manifest["native_v615"]
    v619 = manifest["native_v619"]
    return [
        [
            "service-notifier publication",
            "kernel QMI callback gap",
            (
                f"android 180/74={android['counts'].get('service_notifier_180', 0)}/"
                f"{android['counts'].get('service_notifier_74', 0)}; "
                f"v619 service_notifier={v619['marker_counts'].get('service_notifier', 0)}; "
                f"android sysmon->180={android['deltas_ms'].get('sysmon_modem_to_service_notifier_180')}ms"
            ),
            "do not retry CNSS/HAL until lower QMI publication moves",
        ],
        [
            "mdm3/esoc0 state",
            "state delta, not notifier prerequisite",
            (
                f"android mdm3={android['mdm3_state']}, sysmon_esoc0={android['counts'].get('sysmon_esoc0', 0)}; "
                f"v619 mdm3={v619['mdm3_after_companion']}, sysmon_esoc0={v619['counts'].get('sysmon_esoc0', 0)}; "
                f"android 180->esoc0={android['deltas_ms'].get('service_notifier_180_to_sysmon_esoc0')}ms"
            ),
            "do not claim sysmon_esoc0 is required before service-notifier",
        ],
        [
            "sysmon_esoc0 timing",
            "not causal for first notifier",
            (
                f"android sysmon_modem->180={android['deltas_ms'].get('sysmon_modem_to_service_notifier_180')}ms; "
                f"android 180->esoc0={android['deltas_ms'].get('service_notifier_180_to_sysmon_esoc0')}ms; "
                f"android wlan_pd->esoc0={android['deltas_ms'].get('wlan_pd_to_sysmon_esoc0')}ms"
            ),
            "focus next analysis on mdm_helper/launcher path and same-boot timing",
        ],
        [
            "direct DSP boot nodes",
            "unsafe to repeat",
            (
                f"android pm_qos={android['counts'].get('pm_qos_warning', 0)}; "
                f"v615 pm_qos={v615['counts'].get('pm_qos_warning', 0)}; "
                f"v619 kernel_warning={v619['marker_counts'].get('kernel_warning', 0)}"
            ),
            "block direct ADSP/CDSP/SLPI boot-node observer retries",
        ],
        [
            "Android-order companion",
            "falsified as root cause",
            (
                f"expected_order={','.join(ANDROID_ORDER)}; "
                f"v619_order={','.join(v619['order'])}; "
                f"children={v619['child_started']}"
            ),
            "do not spend another live cycle on companion order alone",
        ],
        [
            "CNSS/HAL/qcwlanstate",
            "still too late",
            (
                f"android service_notifier before wlan_pd={bool_text(android['deltas_ms'].get('service_notifier_180_to_wlan_pd') is not None)}; "
                f"v619 qmi_server_connected={v619['marker_counts'].get('qmi_server_connected', 0)}; "
                f"v619 wlfw={v619['marker_counts'].get('wlfw', 0)}"
            ),
            "no Wi-Fi bring-up attempt until notifier/WLAN-PD exists",
        ],
        [
            "vendor.mdm_helper / launcher",
            "next host-only contract target",
            (
                f"service={bool_text(bool(manifest['vendor_static_hits'].get('mdm_helper_service')))}; "
                f"launcher={bool_text(bool(manifest['vendor_static_hits'].get('mdm_launcher_service')))}; "
                f"baseband_gate={bool_text(bool(manifest['vendor_static_hits'].get('mdm_helper_baseband_gate')))}; "
                f"raw_esoc_visible={manifest['causality_checks'].get('static_raw_esoc_path_visible')}"
            ),
            "classify exact Android trigger/identity and ioctl/property path before any start-only proof",
        ],
    ]


def requested_hypothesis_rows(manifest: dict[str, Any]) -> list[list[str]]:
    android = manifest["android_v611"]
    v619 = manifest["native_v619"]
    checks = manifest["causality_checks"]
    return [
        [
            "sysmon_esoc0 absence",
            (
                f"Android sysmon_esoc0={android['counts'].get('sysmon_esoc0', 0)}; "
                f"native V619 sysmon_esoc0={v619['counts'].get('sysmon_esoc0', 0)}"
            ),
            (
                f"Android 180->esoc0={android['deltas_ms'].get('service_notifier_180_to_sysmon_esoc0')}ms; "
                f"Android wlan_pd->esoc0={android['deltas_ms'].get('wlan_pd_to_sysmon_esoc0')}ms"
            ),
            "missing native sysmon_esoc0 is confirmed, but Android publishes first notifier before esoc0",
        ],
        [
            "mdm_helper ioctl/property path",
            (
                f"init_contract={checks.get('mdm_helper_init_contract_visible')}; "
                f"raw_esoc_visible={checks.get('static_raw_esoc_path_visible')}; "
                f"ioctl_hint_visible={checks.get('static_ioctl_hint_visible')}"
            ),
            "V614 vendor init exposes launcher/helper/property contract but no raw esoc0/ioctl call site",
            "same-boot timing and binary/static inspection are required before any mdm_helper start-only proof",
        ],
        [
            "SM8150/pmaports context",
            "QRTR, pd-mapper, tqftpserv, and rmtfs are adjacent Qualcomm modem/Wi-Fi prerequisites",
            "mainline packaging is supporting context only",
            "do not treat pmaports as proof of Samsung vendor-kernel esoc/mdm_helper semantics",
        ],
        [
            "core hypothesis",
            "esoc0 SSCTL absence blocks service-notifier publication",
            (
                f"supported_for_first_notifier={checks.get('hypothesis_esoc0_pre_notifier_supported')}; "
                f"native_mdm3_offlining={checks.get('native_mdm3_offlining')}"
            ),
            "falsified as first-notifier cause; still useful as later-state delta below CNSS/HAL",
        ],
    ]


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    prior_pass = all(
        bool(manifest["prior"][key].get("pass"))
        for key in ("v616", "v617", "v618")
    )
    android = manifest["android_v611"]
    v619 = manifest["native_v619"]
    android_has_notifier = android["counts"].get("service_notifier_180", 0) > 0 and android["counts"].get("service_notifier_74", 0) > 0
    v619_has_sibling_sysmon = all(v619["counts"].get(marker, 0) > 0 for marker in ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp"))
    v619_missing_notifier = v619["marker_counts"].get("service_notifier", 0) == 0
    v619_mdm3_offlining = v619["mdm3_after_companion"] == "OFFLINING"
    android_mdm3_online = android["mdm3_state"] == "ONLINE"
    android_has_esoc0 = android["counts"].get("sysmon_esoc0", 0) > 0
    v619_lacks_esoc0 = v619["counts"].get("sysmon_esoc0", 0) == 0
    direct_dsp_unsafe = v619["marker_counts"].get("kernel_warning", 0) > 0
    order_falsified = v619["order"] == ANDROID_ORDER and v619_missing_notifier
    esoc0_after_notifier = (android["deltas_ms"].get("service_notifier_180_to_sysmon_esoc0") or 0) > 0

    if (
        prior_pass
        and android_has_notifier
        and v619_has_sibling_sysmon
        and v619_missing_notifier
        and v619_mdm3_offlining
        and android_mdm3_online
        and android_has_esoc0
        and v619_lacks_esoc0
        and direct_dsp_unsafe
        and order_falsified
        and esoc0_after_notifier
    ):
        return (
            "v620-esoc0-notifier-causality-refined",
            True,
            (
                "Android publishes service-notifier after lower sysmon before sysmon_esoc0 appears, "
                "while V619 reproduces sibling sysmon under Android-order companion but leaves "
                "mdm3 OFFLINING, lacks service-notifier, and triggers pm_qos warnings. "
                "Missing sysmon_esoc0 is a later state delta, not a proven pre-notifier cause."
            ),
            "V621 should remain host-only and resolve vendor.mdm_helper/launcher ioctl/property timing before any bounded start-only proof",
        )

    if direct_dsp_unsafe:
        return (
            "v620-direct-dsp-boot-unsafe-blocker",
            True,
            "direct DSP boot-node path produced kernel warnings; live retry is blocked even though trigger attribution is incomplete",
            "refresh Android/native read-only evidence before another live write",
        )

    return (
        "v620-android-evidence-gap-needs-readonly-recapture",
        False,
        (
            f"prior_pass={prior_pass} android_has_notifier={android_has_notifier} "
            f"v619_has_sibling_sysmon={v619_has_sibling_sysmon} v619_missing_notifier={v619_missing_notifier} "
            f"v619_mdm3_offlining={v619_mdm3_offlining} android_mdm3_online={android_mdm3_online} "
            f"android_has_esoc0={android_has_esoc0} v619_lacks_esoc0={v619_lacks_esoc0} "
            f"order_falsified={order_falsified}"
        ),
        "perform Android read-only recapture of mdm helper/wcnss service timing",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    android_manifest = load_json(args.android_v611_manifest)
    v616 = load_json(args.v616_manifest)
    v617 = load_json(args.v617_manifest)
    v618 = load_json(args.v618_manifest)
    v619 = load_json(args.v619_manifest)
    snapshot = read_text(args.v614_snapshot)

    android_text = android_v611_text(args.android_v611_dir)
    v615_text = native_v615_text(args.v615_dir)
    v619_text = native_v619_text(args.v619_dir)

    android_events = parse_events(android_text, "android-v611")
    v615_events = parse_events(v615_text, "native-v615")
    v619_events = parse_events(v619_text, "native-v619")

    android_found = first_by_marker(android_events)
    v615_found = first_by_marker(v615_events)
    v619_found = first_by_marker(v619_events)
    android_counts = count_by_marker(android_events)
    v615_counts = count_by_marker(v615_events)
    v619_counts = count_by_marker(v619_events)

    v619_keys = parse_key_values(read_text(repo_path(args.v619_dir) / "native" / "companion-start-only-with-dsp-boot.txt"))
    marker_counts = safe_get(v619, ("live", "markers", "counts"), {}) or {}
    mdm_path_rows = mdm_helper_path_rows(snapshot)
    mdm_path_values = {row[0]: row[1] == "yes" for row in mdm_path_rows}

    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "android_v611_manifest": str(repo_path(args.android_v611_manifest)),
            "android_v611_dir": str(repo_path(args.android_v611_dir)),
            "v614_snapshot": str(repo_path(args.v614_snapshot)),
            "v615_dir": str(repo_path(args.v615_dir)),
            "v616_manifest": str(repo_path(args.v616_manifest)),
            "v617_manifest": str(repo_path(args.v617_manifest)),
            "v618_manifest": str(repo_path(args.v618_manifest)),
            "v619_manifest": str(repo_path(args.v619_manifest)),
            "v619_dir": str(repo_path(args.v619_dir)),
        },
        "prior": {
            "v616": {"decision": v616.get("decision"), "pass": v616.get("pass")},
            "v617": {"decision": v617.get("decision"), "pass": v617.get("pass")},
            "v618": {"decision": v618.get("decision"), "pass": v618.get("pass")},
            "v619": {"decision": v619.get("decision"), "pass": v619.get("pass")},
        },
        "android_v611": {
            "mdm3_state": safe_get(android_manifest, ("android_summary", "mdm3_state"), ""),
            "mss_state": safe_get(android_manifest, ("android_summary", "mss_state"), ""),
            "counts": {**android_counts, **(safe_get(android_manifest, ("android_summary", "counts"), {}) or {})},
            "deltas_ms": safe_get(android_manifest, ("android_summary", "deltas_ms"), {}) or {},
            "timeline_rows": timeline_rows(android_found, android_counts),
            "first_lines": {
                "sysmon_modem": android_found.get("sysmon_modem", Event("", None, "missing", "")).line,
                "service_notifier_180": android_found.get("service_notifier_180", Event("", None, "missing", "")).line,
                "sysmon_esoc0": android_found.get("sysmon_esoc0", Event("", None, "missing", "")).line,
                "wlan_pd": android_found.get("wlan_pd", Event("", None, "missing", "")).line,
            },
        },
        "native_v615": {
            "counts": v615_counts,
            "deltas_ms": {
                "sysmon_modem_to_service_locator": delta_ms(v615_found, "service_locator", "sysmon_modem"),
                "sysmon_modem_to_service_notifier_180": delta_ms(v615_found, "service_notifier_180", "sysmon_modem"),
                "sysmon_modem_to_pm_qos_warning": delta_ms(v615_found, "pm_qos_warning", "sysmon_modem"),
            },
            "timeline_rows": timeline_rows(v615_found, v615_counts),
        },
        "native_v619": {
            "mdm3_after_companion": safe_get(v619, ("live", "mdm3_after_companion"), ""),
            "mss_after_companion": safe_get(v619, ("live", "mss_after_companion"), ""),
            "marker_counts": marker_counts,
            "counts": v619_counts,
            "order": companion_order(v619_keys),
            "child_started": v619_keys.get("wifi_companion_start.child_started", ""),
            "all_postflight_safe": safe_get(v619, ("live", "all_postflight_safe"), ""),
            "deltas_ms": {
                "sysmon_modem_to_service_notifier_180": delta_ms(v619_found, "service_notifier_180", "sysmon_modem"),
                "sysmon_modem_to_pm_qos_warning": delta_ms(v619_found, "pm_qos_warning", "sysmon_modem"),
                "sysmon_modem_to_asoc_probe": delta_ms(v619_found, "asoc_probe", "sysmon_modem"),
                "qrtr_tx_to_sysmon_modem": delta_ms(v619_found, "sysmon_modem", "qrtr_tx"),
            },
            "timeline_rows": timeline_rows(v619_found, v619_counts),
            "first_lines": {
                "sysmon_modem": v619_found.get("sysmon_modem", Event("", None, "missing", "")).line,
                "pm_qos_warning": v619_found.get("pm_qos_warning", Event("", None, "missing", "")).line,
                "asoc_probe": v619_found.get("asoc_probe", Event("", None, "missing", "")).line,
                "service_notifier_180": v619_found.get("service_notifier_180", Event("", None, "missing", "")).line,
            },
        },
        "vendor_static_hits": vendor_static_hits(snapshot, v616, v617),
        "mdm_helper_path_rows": mdm_path_rows,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "sysfs_writes_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    manifest["android_v611"]["deltas_ms"].update({
        "service_notifier_180_to_sysmon_esoc0": delta_ms(android_found, "sysmon_esoc0", "service_notifier_180"),
        "wlan_pd_to_sysmon_esoc0": delta_ms(android_found, "sysmon_esoc0", "wlan_pd"),
        "qmi_server_connected_to_sysmon_esoc0": delta_ms(android_found, "sysmon_esoc0", "qmi_server_connected"),
    })
    service_to_esoc0 = manifest["android_v611"]["deltas_ms"].get("service_notifier_180_to_sysmon_esoc0")
    wlan_pd_to_esoc0 = manifest["android_v611"]["deltas_ms"].get("wlan_pd_to_sysmon_esoc0")
    manifest["causality_checks"] = {
        "android_service_notifier_before_sysmon_esoc0": bool(service_to_esoc0 is not None and service_to_esoc0 > 0),
        "android_wlan_pd_before_sysmon_esoc0": bool(wlan_pd_to_esoc0 is not None and wlan_pd_to_esoc0 > 0),
        "native_missing_service_notifier": marker_counts.get("service_notifier", 0) == 0,
        "native_missing_sysmon_esoc0": v619_counts.get("sysmon_esoc0", 0) == 0,
        "native_mdm3_offlining": safe_get(v619, ("live", "mdm3_after_companion"), "") == "OFFLINING",
        "direct_dsp_warning_present": marker_counts.get("kernel_warning", 0) > 0,
        "mdm_helper_init_contract_visible": all(
            mdm_path_values.get(key, False)
            for key in (
                "mdm_helper_service",
                "mdm_launcher_service",
                "mdm_launcher_reads_baseband",
                "mdm_launcher_starts_helper",
            )
        ),
        "static_raw_esoc_path_visible": mdm_path_values.get("static_esoc_path_visible", False),
        "static_ioctl_hint_visible": mdm_path_values.get("static_ioctl_hint_visible", False),
        "hypothesis_esoc0_pre_notifier_supported": False,
    }

    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v620-dsp-mdm3-safety-classifier-plan-ready",
            True,
            "plan-only; run will classify existing Android/V615/V616/V617/V618/V619 evidence without device contact",
            "run V620 host-only classifier",
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
    manifest["requested_hypothesis_rows"] = requested_hypothesis_rows(manifest)
    manifest["inferences"] = {
        "service_notifier_is_kernel_qmi_callback": True,
        "userspace_cnss_daemon_not_primary_trigger": True,
        "android_order_lower_companion_falsified": manifest["native_v619"]["order"] == ANDROID_ORDER,
        "direct_dsp_boot_node_retry_blocked_by_warning": manifest["native_v619"]["marker_counts"].get("kernel_warning", 0) > 0,
        "sysmon_esoc0_is_not_pre_notifier_prerequisite": decision == "v620-esoc0-notifier-causality-refined",
        "mdm_helper_ioctl_path_unproven_from_init_snapshot": (
            manifest["causality_checks"]["mdm_helper_init_contract_visible"]
            and not manifest["causality_checks"]["static_ioctl_hint_visible"]
        ),
        "raw_esoc_open_should_not_be_retried": True,
        "mdm3_state_delta_still_unresolved": True,
        "wifi_bringup_still_blocked": True,
    }
    manifest["external_references"] = EXTERNAL_REFERENCES
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    android = manifest["android_v611"]
    v619 = manifest["native_v619"]
    return "\n".join([
        "# V620 DSP/MDM3 Safety Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- sysfs_writes_executed: `{manifest['sysfs_writes_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Evidence Matrix",
        "",
        markdown_table(["subject", "classification", "evidence", "next"], manifest["evidence_rows"]),
        "",
        "## Requested Hypothesis Checks",
        "",
        markdown_table(
            ["item", "observation", "timing_or_context", "classification"],
            manifest["requested_hypothesis_rows"],
        ),
        "",
        "## Prior Decisions",
        "",
        markdown_table(
            ["cycle", "decision", "pass"],
            [[key, str(value.get("decision")), str(value.get("pass"))] for key, value in manifest["prior"].items()],
        ),
        "",
        "## Android V611 Reference",
        "",
        markdown_table(
            ["key", "value"],
            [
                ["mdm3_state", str(android["mdm3_state"])],
                ["mss_state", str(android["mss_state"])],
                ["sysmon_modem_to_service_notifier_180_ms", str(android["deltas_ms"].get("sysmon_modem_to_service_notifier_180"))],
                ["service_notifier_180_to_wlan_pd_ms", str(android["deltas_ms"].get("service_notifier_180_to_wlan_pd"))],
                ["service_notifier_180_to_qmi_server_connected_ms", str(android["deltas_ms"].get("service_notifier_180_to_qmi_server_connected"))],
                ["service_notifier_180_to_sysmon_esoc0_ms", str(android["deltas_ms"].get("service_notifier_180_to_sysmon_esoc0"))],
                ["wlan_pd_to_sysmon_esoc0_ms", str(android["deltas_ms"].get("wlan_pd_to_sysmon_esoc0"))],
            ],
        ),
        "",
        "## Native V619 Comparison",
        "",
        markdown_table(
            ["key", "value"],
            [
                ["mdm3_after_companion", str(v619["mdm3_after_companion"])],
                ["mss_after_companion", str(v619["mss_after_companion"])],
                ["order", ",".join(v619["order"])],
                ["child_started", str(v619["child_started"])],
                ["kernel_warning_count", str(v619["marker_counts"].get("kernel_warning", 0))],
                ["service_notifier_count", str(v619["marker_counts"].get("service_notifier", 0))],
                ["sysmon_qmi_count", str(v619["marker_counts"].get("sysmon_qmi", 0))],
            ],
        ),
        "",
        "## Native V619 First Lines",
        "",
        markdown_table(["key", "line"], [[key, value] for key, value in v619["first_lines"].items()]),
        "",
        "## Causality Checks",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in manifest["causality_checks"].items()]),
        "",
        "## MDM Helper Path Hints",
        "",
        markdown_table(["key", "present", "line", "interpretation"], manifest["mdm_helper_path_rows"]),
        "",
        "## Inferences",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in manifest["inferences"].items()]),
        "",
        "## External References",
        "",
        markdown_table(
            ["title", "url", "relevance"],
            [[item["title"], item["url"], item["relevance"]] for item in manifest["external_references"]],
        ),
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
    print(f"sysfs_writes_executed: {manifest['sysfs_writes_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
