#!/usr/bin/env python3
"""V519 host-only Android/native QRTR modem companion-service delta classifier.

This tool does not talk to the device. It compares the Android boot-complete
QRTR/modem/CNSS sequence and companion-service evidence against the latest
native V517/V518 evidence. It classifies the next safe gate before any
qcwlanstate retry, daemon start, Wi-Fi HAL start, scan/connect, link-up, DHCP,
route change, or external ping.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v519-android-native-qrtr-modem-delta")
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/dmesg-wifi-cnss-tail.txt")
DEFAULT_ANDROID_PROCESSES = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/processes-wifi.txt")
DEFAULT_ANDROID_PROPS = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/wifi-props-init-state.txt")
DEFAULT_ANDROID_INITRC = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/initrc-wifi-grep.txt")
DEFAULT_ANDROID_DEVNODES = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/devnodes-sockets-wifi.txt")
DEFAULT_V517_MANIFEST = Path("tmp/wifi/v517-cnss-userspace-private-data-wifi/manifest.json")
DEFAULT_V518_MANIFEST = Path("tmp/wifi/v518-cnss-prereq-classifier/manifest.json")
DEFAULT_BINARY_ROOTS = (
    Path("tmp/wifi/v226-vendor-root-live-export/vendor-source"),
    Path("tmp/wifi/v222-vendor-root-evidence-export/vendor-root"),
    Path("tmp/wifi/v227-android-core-system-library-evidence/system-root"),
    Path("tmp/wifi/v396-frame-elf-pull-20260520-073940/system-root"),
)
SERVICE_BINARY_NAMES = {
    "cnss-daemon",
    "cnss_diag",
    "pd-mapper",
    "qmiproxy",
    "qrtr-ns",
    "rmtfs",
    "service-notifier",
    "sysmon-qmi",
    "tqftpserv",
}
SOURCE_REFERENCES = (
    "https://wiki.postmarketos.org/wiki/SDM845_Mainlining",
    "https://wiki.postmarketos.org/wiki/Qualcomm_Snapdragon_845/850_(SDM845/SDM850)#WiFi",
    "https://gitlab.com/postmarketOS/pmaports/-/issues/863",
    "https://sources.debian.org/src/tqftpserv/1.1-4/tqftpserv.c",
    "https://packages.debian.org/sid/protection-domain-mapper",
    "https://sources.debian.org/src/protection-domain-mapper/1.0-4/pd-mapper.c",
    "https://lists.infradead.org/pipermail/ath10k/2023-August/014701.html",
)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
DMESG_TS_RE = re.compile(r"\[\s*(?P<time>[0-9]+(?:\.[0-9]+)?)\]")
PROCESS_LINE_RE = re.compile(r"\b(qrtr-ns|qmiproxy|service-notifier|sysmon-qmi|pd-mapper|tqftpserv|rmtfs|cnss-daemon|cnss_diag|wificond|wpa_supplicant|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi|\[qrtr_rx\])\b", re.IGNORECASE)


@dataclass(frozen=True)
class Marker:
    name: str
    pattern: re.Pattern[str]
    required_for_qmi: bool
    description: str


@dataclass(frozen=True)
class Event:
    marker: str
    index: int
    time: float | None
    line: str


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


MARKERS: tuple[Marker, ...] = (
    Marker("firmware_mounts", re.compile(r"mount.*(?:firmware_mnt|firmware-modem).*Success", re.IGNORECASE), True,
           "Android mounts WLAN/modem firmware partitions before QRTR/QMI"),
    Marker("wlan_driver_load", re.compile(r"wlan: Loading driver", re.IGNORECASE), True,
           "QCACLD driver load starts"),
    Marker("wlan_state_initialized", re.compile(r"wlan_hdd_state .* initialized", re.IGNORECASE), True,
           "qcwlanstate/dev_wlan layer is present"),
    Marker("qrtr_modem_readiness_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.IGNORECASE), True,
           "kernel receives modem QMI readiness"),
    Marker("qrtr_ns_start", re.compile(r"starting service 'vendor\.qrtr-ns'", re.IGNORECASE), True,
           "Android starts vendor.qrtr-ns"),
    Marker("qrtr_modem_readiness_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.IGNORECASE), True,
           "kernel transmits modem QMI readiness response"),
    Marker("sysmon_qmi_ready", re.compile(r"sysmon-qmi: ssctl_new_server: Connection established", re.IGNORECASE), True,
           "sysmon QMI services connect to modem/subsystems"),
    Marker("service_notifier_ready", re.compile(r"service-notifier: service_notifier_new_server: Connection established", re.IGNORECASE), True,
           "service-notifier QMI service appears"),
    Marker("cnss_diag_start", re.compile(r"starting service 'cnss_diag'", re.IGNORECASE), True,
           "cnss_diag starts"),
    Marker("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag|comm:cnss_diag", re.IGNORECASE), True,
           "cnss_diag reaches CNSS netlink"),
    Marker("cnss_daemon_start", re.compile(r"starting service 'cnss-daemon'", re.IGNORECASE), True,
           "cnss-daemon starts"),
    Marker("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon|comm:cnss-daemon|cnss-daemon.*ctrl_getfamily", re.IGNORECASE), True,
           "cnss-daemon reaches CNSS/cld80211 netlink"),
    Marker("cnss_daemon_wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting", re.IGNORECASE), True,
           "cnss-daemon starts WLFW"),
    Marker("wlfw_thread", re.compile(r"cnss-daemon wlfw_service_request", re.IGNORECASE), True,
           "WLFW service request thread starts"),
    Marker("wlan_pd_indication", re.compile(r"service-notifier:.*msm/modem/wlan_pd", re.IGNORECASE), True,
           "modem WLAN protection-domain indication arrives"),
    Marker("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.IGNORECASE), True,
           "ICNSS QMI server connects"),
    Marker("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.IGNORECASE), True,
           "regulatory BDF download is requested"),
    Marker("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.IGNORECASE), True,
           "board-data BDF download is requested"),
    Marker("wifi_turning_on", re.compile(r"Wifi Turning On from UI", re.IGNORECASE), False,
           "Android framework requests Wi-Fi ON"),
    Marker("wlan_fw_ready", re.compile(r"icnss: WLAN FW is ready", re.IGNORECASE), True,
           "ICNSS reports firmware readiness"),
    Marker("wcnss_cfg_request", re.compile(r"WCNSS_qcom_cfg\.ini", re.IGNORECASE), False,
           "firmware_class requests WCNSS_qcom_cfg.ini"),
    Marker("wma_service_ready", re.compile(r"wma_rx_service_ready_event|FW ready event received", re.IGNORECASE), False,
           "WMA target firmware ready event is observed"),
    Marker("wlan0_event", re.compile(r"dev\s*:\s*wlan0\s*:\s*event", re.IGNORECASE), False,
           "wlan0 netdev appears"),
    Marker("ssgqmigd_missing", re.compile(r"Could not start service 'ssgqmigd'.*Cannot find", re.IGNORECASE), False,
           "Android tolerates missing ssgqmigd while Wi-Fi still reaches firmware ready"),
    Marker("perfd_client_failed", re.compile(r"Failed to become a perfd client", re.IGNORECASE), False,
           "cnss-daemon perfd client warning appears"),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--android-processes", type=Path, default=DEFAULT_ANDROID_PROCESSES)
    parser.add_argument("--android-props", type=Path, default=DEFAULT_ANDROID_PROPS)
    parser.add_argument("--android-initrc", type=Path, default=DEFAULT_ANDROID_INITRC)
    parser.add_argument("--android-devnodes", type=Path, default=DEFAULT_ANDROID_DEVNODES)
    parser.add_argument("--v517-manifest", type=Path, default=DEFAULT_V517_MANIFEST)
    parser.add_argument("--v518-manifest", type=Path, default=DEFAULT_V518_MANIFEST)
    parser.add_argument("--binary-root", action="append", type=Path, default=None,
                        help="Additional extracted root to scan for QRTR/modem companion binaries")
    parser.add_argument("command", choices=("plan", "run"))
    return parser.parse_args()


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def dmesg_time(line: str) -> float | None:
    match = DMESG_TS_RE.search(line)
    if not match:
        return None
    try:
        return float(match.group("time"))
    except ValueError:
        return None


def read_text_if_exists(path: Path) -> tuple[bool, str, str]:
    resolved = repo_path(path)
    if not resolved.exists():
        return False, str(resolved), ""
    return True, str(resolved), resolved.read_text(encoding="utf-8", errors="replace")


def load_json_if_exists(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": True}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def extract_events(text: str) -> dict[str, Any]:
    events: list[Event] = []
    first_by_marker: dict[str, Event] = {}
    counts = {marker.name: 0 for marker in MARKERS}
    for index, raw_line in enumerate(text.splitlines()):
        line = strip_ansi(raw_line).strip()
        if not line:
            continue
        for marker in MARKERS:
            if marker.pattern.search(line):
                event = Event(marker.name, index, dmesg_time(line), line)
                events.append(event)
                counts[marker.name] += 1
                first_by_marker.setdefault(marker.name, event)
    ordered = [asdict(event) for event in sorted(first_by_marker.values(), key=lambda item: item.index)]
    return {
        "counts": counts,
        "first": {name: asdict(event) for name, event in first_by_marker.items()},
        "ordered_first": ordered,
        "focus_tail": [asdict(event) for event in events[-180:]],
    }


def present(summary: dict[str, Any], name: str) -> bool:
    return (summary.get("counts") or {}).get(name, 0) > 0


def first_line(summary: dict[str, Any], name: str) -> str:
    event = (summary.get("first") or {}).get(name) or {}
    return str(event.get("line") or "")


def first_time(summary: dict[str, Any], name: str) -> float | None:
    event = (summary.get("first") or {}).get(name) or {}
    value = event.get("time")
    return value if isinstance(value, float) else None


def native_count(v517: dict[str, Any], name: str) -> int:
    direct_counts = v517.get("counts")
    if isinstance(direct_counts, dict):
        value = direct_counts.get(name)
        return value if isinstance(value, int) else 0
    summary = v517.get("dmesg_summary") if isinstance(v517.get("dmesg_summary"), dict) else {}
    counts = summary.get("counts") if isinstance(summary.get("counts"), dict) else {}
    value = counts.get(name)
    return value if isinstance(value, int) else 0


def native_marker_absent(v517: dict[str, Any], names: list[str]) -> bool:
    return all(native_count(v517, name) == 0 for name in names)


def native_marker_present(v517: dict[str, Any], names: list[str]) -> bool:
    return any(native_count(v517, name) > 0 for name in names)


def process_surface(processes: str, props: str, devnodes: str, initrc: str) -> dict[str, Any]:
    lines = [line.strip() for line in processes.splitlines() if PROCESS_LINE_RE.search(line)]
    props_lines = [line.strip() for line in props.splitlines() if line.startswith("[")]
    initrc_lines = [line.strip() for line in initrc.splitlines() if "service " in line or "on property:" in line]
    return {
        "qrtr_rx_threads": sum(1 for line in processes.splitlines() if "[qrtr_rx]" in line),
        "qrtr_ns_process": any(re.search(r"\bqrtr-ns\b", line) for line in processes.splitlines()),
        "cnss_diag_process": any(re.search(r"\bcnss_diag\b", line) for line in processes.splitlines()),
        "cnss_daemon_process": any(re.search(r"\bcnss-daemon\b", line) for line in processes.splitlines()),
        "qmiproxy_process": any(re.search(r"\bqmiproxy\b", line) for line in processes.splitlines()),
        "service_notifier_process": any(re.search(r"\bservice-notifier\b", line) for line in processes.splitlines()),
        "sysmon_qmi_process": any(re.search(r"\bsysmon-qmi\b", line) for line in processes.splitlines()),
        "pd_mapper_process": any(re.search(r"\bpd-mapper\b", line) for line in processes.splitlines()),
        "tqftpserv_process": any(re.search(r"\btqftpserv\b", line) for line in processes.splitlines()),
        "rmtfs_process": any(re.search(r"\brmtfs\b", line) for line in processes.splitlines()),
        "wifi_hal_process": any(re.search(r"android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi", line) for line in processes.splitlines()),
        "wificond_process": "wificond" in processes,
        "supplicant_process": "wpa_supplicant" in processes,
        "process_hits": lines[:80],
        "init_service_qrtr_ns": any("vendor.qrtr-ns" in line for line in initrc_lines),
        "init_service_qmiproxy": any("service qmiproxy" in line for line in initrc_lines),
        "init_service_pd_mapper": any("service pd-mapper" in line or "pd-mapper" in line for line in initrc_lines),
        "init_service_tqftpserv": any("service tqftpserv" in line or "tqftpserv" in line for line in initrc_lines),
        "init_service_rmtfs": any("service rmtfs" in line or "rmtfs" in line for line in initrc_lines),
        "init_service_service_notifier": any("service service-notifier" in line or "service-notifier" in line for line in initrc_lines),
        "init_service_sysmon_qmi": any("service sysmon-qmi" in line or "sysmon-qmi" in line for line in initrc_lines),
        "init_service_ssgqmigd": any("service ssgqmigd" in line for line in initrc_lines),
        "init_service_cnss_daemon": any("service cnss-daemon" in line for line in initrc_lines),
        "init_service_cnss_diag": any("service cnss_diag" in line for line in initrc_lines),
        "prop_cnss_daemon_running": "[init.svc.cnss-daemon]: [running]" in props,
        "prop_cnss_diag_running": "[init.svc.cnss_diag]: [running]" in props,
        "prop_wifi_hal_running": "[init.svc.vendor.wifi_hal_legacy]: [running]" in props and "[init.svc.vendor.wifi_hal_ext]: [running]" in props,
        "prop_wlan_driver_ok": "[wlan.driver.status]: [ok]" in props,
        "prop_wifi_interface_wlan0": "[wifi.interface]: [wlan0]" in props or "[wifi.active.interface]: [wlan0]" in props,
        "devnodes_qrtr_visible_in_sample": "qrtr" in devnodes.lower(),
        "devnodes_wifi_socket_visible": "wifihal" in devnodes or "wpa_wlan0" in devnodes,
        "props_focus": props_lines[:80],
    }


def binary_roots(args: argparse.Namespace) -> list[Path]:
    roots = list(DEFAULT_BINARY_ROOTS)
    if args.binary_root:
        roots.extend(args.binary_root)
    return roots


def companion_inventory(roots: list[Path]) -> dict[str, Any]:
    found: dict[str, list[dict[str, Any]]] = {name: [] for name in sorted(SERVICE_BINARY_NAMES)}
    scanned: list[dict[str, Any]] = []
    for root in roots:
        resolved = repo_path(root)
        item = {"path": str(resolved), "exists": resolved.exists()}
        scanned.append(item)
        if not resolved.exists() or not resolved.is_dir():
            continue
        for path in resolved.rglob("*"):
            if not path.is_file():
                continue
            if path.name not in SERVICE_BINARY_NAMES:
                continue
            try:
                stat_info = path.stat()
                mode = stat_info.st_mode & 0o7777
                rel = path.relative_to(resolved)
            except OSError:
                continue
            found[path.name].append({
                "root": str(resolved),
                "relative_path": str(rel),
                "size": stat_info.st_size,
                "mode": oct(mode),
                "executable": bool(mode & 0o111),
            })
    summary = {
        name: {
            "count": len(entries),
            "paths": entries,
        }
        for name, entries in found.items()
    }
    return {
        "roots": scanned,
        "summary": summary,
        "has_cnss_daemon": bool(found["cnss-daemon"]),
        "has_cnss_diag": bool(found["cnss_diag"]),
        "has_qrtr_ns": bool(found["qrtr-ns"]),
        "has_qmiproxy": bool(found["qmiproxy"]),
        "has_pd_mapper": bool(found["pd-mapper"]),
        "has_tqftpserv": bool(found["tqftpserv"]),
        "has_rmtfs": bool(found["rmtfs"]),
        "has_mainline_companion_set": bool(found["pd-mapper"] and found["tqftpserv"] and found["rmtfs"]),
    }


def runtime_surface(v518: dict[str, Any]) -> dict[str, Any]:
    surface = v518.get("runtime_surface")
    return surface if isinstance(surface, dict) else {}


def v517_summary(v517: dict[str, Any]) -> dict[str, Any]:
    live = v517.get("live_result") if isinstance(v517.get("live_result"), dict) else {}
    keys = live.get("keys") if isinstance(live.get("keys"), dict) else {}
    dmesg = v517.get("dmesg_summary") if isinstance(v517.get("dmesg_summary"), dict) else {}
    counts = dmesg.get("counts") if isinstance(dmesg.get("counts"), dict) else {}
    return {
        "exists": v517.get("exists") is True and not v517.get("invalid"),
        "path": v517.get("path"),
        "decision": v517.get("decision"),
        "pass": v517.get("pass"),
        "reason": v517.get("reason"),
        "qcwlanstate_write": keys.get("cnss_userspace_readiness.qcwlanstate_write"),
        "scan_connect_linkup": keys.get("cnss_userspace_readiness.scan_connect_linkup"),
        "external_ping": keys.get("cnss_userspace_readiness.external_ping"),
        "readiness_markers": dmesg.get("readiness_markers") or [],
        "counts": {name: counts.get(name, 0) for name in sorted(counts)},
        "perfd_warning": "Failed to become a perfd client" in json.dumps(v517, ensure_ascii=False),
        "private_data_gap_closed": "private /data/vendor/wifi/sockets was present" in str(v517.get("reason")),
    }


def v518_summary(v518: dict[str, Any]) -> dict[str, Any]:
    surface = runtime_surface(v518)
    return {
        "exists": v518.get("exists") is True and not v518.get("invalid"),
        "path": v518.get("path"),
        "decision": v518.get("decision"),
        "pass": v518.get("pass"),
        "reason": v518.get("reason"),
        "surface": surface,
        "qipcrtr_protocol_present": bool(surface.get("qipcrtr_protocol_present")),
        "proc_net_qrtr_present": bool(surface.get("proc_net_qrtr_present")),
        "dev_qrtr_present": bool(surface.get("dev_qrtr_present")),
        "perfd_socket_present": bool(surface.get("perfd_socket_present")),
        "perfd_binary_present": bool(surface.get("perfd_binary_present")),
        "property_socket_present": bool(surface.get("property_socket_present")),
        "property_area_present": bool(surface.get("property_area_present")),
        "process_hits": surface.get("process_hits") if isinstance(surface.get("process_hits"), list) else [],
        "wifi_hits": surface.get("wifi_hits") if isinstance(surface.get("wifi_hits"), list) else [],
        "qrtr_paths": surface.get("qrtr_paths") if isinstance(surface.get("qrtr_paths"), list) else [],
        "qmi_paths": surface.get("qmi_paths") if isinstance(surface.get("qmi_paths"), list) else [],
        "perfd_paths": surface.get("perfd_paths") if isinstance(surface.get("perfd_paths"), list) else [],
    }


def android_sequence_rows(android: dict[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for marker in MARKERS:
        if not present(android, marker.name):
            continue
        timestamp = first_time(android, marker.name)
        rows.append([
            marker.name,
            "" if timestamp is None else f"{timestamp:.3f}",
            (android.get("counts") or {}).get(marker.name, 0),
            "required" if marker.required_for_qmi else "context",
            marker.description,
            first_line(android, marker.name)[:220],
        ])
    return rows


def delta_rows(android: dict[str, Any], v517: dict[str, Any], v518: dict[str, Any], android_surface: dict[str, Any], inventory: dict[str, Any]) -> list[list[Any]]:
    return [
        ["qrtr readiness RX/TX", present(android, "qrtr_modem_readiness_rx") and present(android, "qrtr_modem_readiness_tx"),
         "not observed in V517", "native QRTR/modem readiness gap"],
        ["qrtr-ns", android_surface["qrtr_ns_process"], not v518.get("dev_qrtr_present") and not v518.get("proc_net_qrtr_present"),
         "Android has running qrtr-ns; native has QIPCRTR protocol only, no /dev/qrtr or /proc/net/qrtr"],
        ["mainline companion set", "rmtfs/pd-mapper/tqftpserv required by SDM845 mainline references",
         inventory["has_mainline_companion_set"], "local extracted roots do not contain the full companion-service set"],
        ["vendor companion evidence", f"qmiproxy_rc={android_surface['init_service_qmiproxy']} sysmon={present(android, 'sysmon_qmi_ready')} service_notifier={present(android, 'service_notifier_ready')}",
         f"qrtr_ns_bin={inventory['has_qrtr_ns']} qmiproxy_bin={inventory['has_qmiproxy']}", "Android reaches vendor QMI support; native export lacks direct start candidates"],
        ["sysmon/service-notifier QMI", present(android, "sysmon_qmi_ready") and present(android, "service_notifier_ready"),
         "not observed in V517", "Android reaches subsystem QMI services before CNSS QMI"],
        ["cnss netlink", present(android, "cnss_diag_netlink") and present(android, "cnss_daemon_netlink"),
         native_marker_present(v517, ["cnss_diag_netlink", "cnss_daemon_netlink"]), "netlink path is not the remaining blocker"],
        ["WLFW/QMI/BDF", present(android, "cnss_daemon_wlfw_start") and present(android, "qmi_server_connected") and present(android, "bdf_bdwlan"),
         "absent in V517" if native_marker_absent(v517, ["wlfw_start", "qmi_server_connected", "bdf_bdwlan"]) else "present in V517", "native stops before WLFW/QMI/BDF"],
        ["firmware ready/wlan0", present(android, "wlan_fw_ready") and present(android, "wlan0_event"),
         "absent in V517" if native_marker_absent(v517, ["wlan_fw_ready", "wlan0_event"]) else "present in V517", "no scan/connect gate yet"],
        ["perfd", "unproven in Android sample", v518.get("perfd_socket_present") or v518.get("perfd_binary_present"),
         "warning context; not enough to explain absent QMI by itself"],
        ["property runtime", android_surface["prop_cnss_daemon_running"] and android_surface["prop_wlan_driver_ok"],
         v518.get("property_socket_present") or v518.get("property_area_present"), "runtime delta exists; causality unproven"],
    ]


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(command: str,
                 input_status: dict[str, dict[str, Any]],
                 android: dict[str, Any],
                 android_surface: dict[str, Any],
                 v517: dict[str, Any],
                 v518: dict[str, Any],
                 inventory: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "host-only; no device command executed", [], "run V519 classifier")
        return checks

    missing_inputs = [name for name, item in input_status.items() if not item["exists"]]
    add_check(checks, "inputs-present", "pass" if not missing_inputs else "blocked", "blocker",
              "missing=" + ",".join(missing_inputs), [item["path"] for item in input_status.values()],
              "refresh Android/V517/V518 evidence before classifying")
    add_check(checks, "v517-gap-current", "pass" if v517["exists"] and v517["decision"] == "v517-cnss-userspace-readiness-no-fw-marker" and v517["pass"] is True else "blocked", "blocker",
              f"decision={v517['decision']} pass={v517['pass']}", [str(v517.get("path"))],
              "rerun V517 private data proof if stale")
    add_check(checks, "v518-prereq-current", "pass" if v518["exists"] and v518["decision"] == "v518-cnss-prereq-classified" and v518["pass"] is True else "blocked", "blocker",
              f"decision={v518['decision']} pass={v518['pass']}", [str(v518.get("path"))],
              "rerun V518 read-only prerequisite classifier if stale")
    android_qrtr_ready = present(android, "qrtr_modem_readiness_rx") and present(android, "qrtr_ns_start") and present(android, "qrtr_modem_readiness_tx")
    android_qmi_ready = present(android, "sysmon_qmi_ready") and present(android, "service_notifier_ready") and present(android, "wlan_pd_indication") and present(android, "qmi_server_connected")
    android_fw_ready = present(android, "cnss_daemon_wlfw_start") and present(android, "bdf_bdwlan") and present(android, "wlan_fw_ready") and present(android, "wlan0_event")
    add_check(checks, "android-qrtr-modem-sequence", "pass" if android_qrtr_ready and android_qmi_ready and android_fw_ready else "blocked", "blocker",
              f"qrtr_ready={android_qrtr_ready} qmi_ready={android_qmi_ready} fw_ready={android_fw_ready}",
              [first_line(android, "qrtr_modem_readiness_rx"), first_line(android, "qrtr_ns_start"), first_line(android, "qmi_server_connected"), first_line(android, "wlan_fw_ready")],
              "refresh Android boot-complete baseline")
    native_qmi_absent = native_marker_absent(v517, ["wlfw_start", "wlfw_thread", "qmi_server_connected", "bdf_regdb", "bdf_bdwlan", "wlan_fw_ready", "wlan0_event"])
    add_check(checks, "native-qmi-wlfw-absent", "pass" if native_qmi_absent and not v517["readiness_markers"] else "blocked", "blocker",
              f"counts={json.dumps(v517['counts'], sort_keys=True)}", v517["readiness_markers"][:8],
              "if native has WLFW/QMI markers, move to scan-only gate")
    netlink_ok = native_marker_present(v517, ["cnss_diag_netlink"]) and native_marker_present(v517, ["cnss_daemon_netlink"])
    add_check(checks, "native-cnss-netlink-present", "pass" if netlink_ok else "blocked", "blocker",
              f"cnss_diag_netlink={v517['counts'].get('cnss_diag_netlink')} cnss_daemon_netlink={v517['counts'].get('cnss_daemon_netlink')}",
              [], "fix CNSS userspace launch before QRTR/QMI analysis")
    no_residual = not v518["process_hits"] and not v518["wifi_hits"]
    add_check(checks, "native-runtime-clean", "pass" if no_residual else "blocked", "blocker",
              f"process_hits={len(v518['process_hits'])} wifi_hits={len(v518['wifi_hits'])}",
              list(v518["process_hits"][:4]) + list(v518["wifi_hits"][:4]), "cleanup native residual process/link state")
    qrtr_delta = android_surface["qrtr_ns_process"] and v518["qipcrtr_protocol_present"] and not v518["proc_net_qrtr_present"] and not v518["dev_qrtr_present"]
    add_check(checks, "qrtr-modem-delta", "pass" if qrtr_delta else "review", "warning",
              f"android_qrtr_ns={android_surface['qrtr_ns_process']} android_qrtr_rx_threads={android_surface['qrtr_rx_threads']} native_qipcrtr={v518['qipcrtr_protocol_present']} native_proc_net_qrtr={v518['proc_net_qrtr_present']} native_dev_qrtr={v518['dev_qrtr_present']}",
              [first_line(android, "qrtr_modem_readiness_rx"), first_line(android, "qrtr_modem_readiness_tx")],
              "plan read-only native qrtr-ns/modem readiness surface")
    companion_android = android_surface["init_service_qmiproxy"] and present(android, "sysmon_qmi_ready") and present(android, "service_notifier_ready")
    add_check(checks, "android-companion-qmi-surface", "pass" if companion_android else "review", "warning",
              f"qmiproxy_rc={android_surface['init_service_qmiproxy']} qrtr_ns_process={android_surface['qrtr_ns_process']} sysmon_qmi={present(android, 'sysmon_qmi_ready')} service_notifier={present(android, 'service_notifier_ready')} wlan_pd={present(android, 'wlan_pd_indication')}",
              [first_line(android, "sysmon_qmi_ready"), first_line(android, "service_notifier_ready"), first_line(android, "wlan_pd_indication")],
              "capture broader Android process list if companion service names are filtered out")
    add_check(checks, "mainline-companion-model", "pass", "info",
              "SDM845 mainline references identify rmtfs, pd-mapper, and tqftpserv as modem/Wi-Fi firmware companion services",
              list(SOURCE_REFERENCES[:4]), "map those services to Android vendor equivalents before live start")
    add_check(checks, "local-companion-binaries", "pass" if inventory["has_mainline_companion_set"] else "review", "warning",
              f"cnss_daemon={inventory['has_cnss_daemon']} cnss_diag={inventory['has_cnss_diag']} qrtr_ns={inventory['has_qrtr_ns']} qmiproxy={inventory['has_qmiproxy']} rmtfs={inventory['has_rmtfs']} pd_mapper={inventory['has_pd_mapper']} tqftpserv={inventory['has_tqftpserv']}",
              [json.dumps(item, sort_keys=True) for item in inventory["roots"]],
              "if absent, do not assume /vendor/bin start-only is available; plan build/deploy or Android recapture")
    add_check(checks, "perfd-warning-not-root-cause-yet", "pass", "warning",
              f"v517_perfd_warning={v517['perfd_warning']} native_socket={v518['perfd_socket_present']} native_binary={v518['perfd_binary_present']} native_paths={len(v518['perfd_paths'])}",
              list(v518["perfd_paths"][:6]), "do not repair perfd before proving it gates QMI")
    add_check(checks, "property-runtime-delta-unproven", "pass", "warning",
              f"android_props_cnss={android_surface['prop_cnss_daemon_running']} android_wlan_driver_ok={android_surface['prop_wlan_driver_ok']} native_socket={v518['property_socket_present']} native_area={v518['property_area_present']}",
              android_surface["props_focus"][:8], "treat property runtime as context until a property lookup blocker is observed")
    add_check(checks, "qcwlanstate-retry-blocked", "pass" if native_qmi_absent else "blocked", "blocker",
              "WLFW/QMI/BDF markers absent; qcwlanstate would likely repeat timeout", [],
              "retry qcwlanstate only after native WLFW marker is observed")
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], android: dict[str, Any], v517: dict[str, Any], v518: dict[str, Any], inventory: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v519-android-native-qrtr-modem-delta-plan-ready", True, "host-only plan; no device command executed", "run V519 classifier"
    blockers = blocking_checks(checks)
    if blockers:
        return "v519-android-native-qrtr-modem-delta-blocked", False, "blocked by " + ", ".join(blockers), "refresh missing evidence before live work"
    if present(android, "qmi_server_connected") and native_marker_absent(v517, ["qmi_server_connected", "wlfw_start", "bdf_bdwlan"]) and v518["qipcrtr_protocol_present"]:
        if not inventory["has_mainline_companion_set"]:
            return (
                "v519-qrtr-companion-service-gap-classified",
                True,
                "Android reaches QRTR/QMI/service-notifier/WLAN-PD/BDF/FW-ready while native reaches only CNSS netlink; SDM845 references point to rmtfs/pd-mapper/tqftpserv as companion services, but the local extracted roots do not contain that full startable set",
                "plan companion-service availability proof before any qcwlanstate retry",
            )
        return (
            "v519-qrtr-modem-delta-classified",
            True,
            "Android reaches QRTR modem readiness, qrtr-ns, sysmon/service-notifier, ICNSS QMI, BDF, and FW-ready; native has CNSS netlink and QIPCRTR protocol but no QRTR device/proc surface and no WLFW/QMI markers",
            "plan read-only native qrtr-ns/modem readiness proof before any qcwlanstate retry",
        )
    return "v519-android-native-qrtr-modem-delta-review", True, "comparison completed but gap shape is not canonical", "inspect marker and runtime delta tables"


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"], item["next_step"]] for item in checks]
    sequence_rows = manifest.get("android_sequence_rows") or []
    delta = manifest.get("delta_rows") or []
    ordered = manifest.get("android_summary", {}).get("ordered_first") or []
    inventory_rows = []
    for name, item in (manifest.get("companion_inventory", {}).get("summary") or {}).items():
        inventory_rows.append([name, item.get("count"), json.dumps(item.get("paths") or [], ensure_ascii=False, sort_keys=True)])
    return "\n".join([
        "# V519 Android/Native QRTR Modem Companion-Service Delta",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Delta",
        "",
        markdown_table(["surface", "android", "native", "interpretation"], delta),
        "",
        "## Companion Inventory",
        "",
        markdown_table(["name", "count", "paths"], inventory_rows),
        "",
        "## Android QRTR/QMI Sequence",
        "",
        markdown_table(["marker", "time", "count", "class", "description", "evidence"], sequence_rows),
        "",
        "## Android Ordered First Markers",
        "",
        "\n".join(f"- `{item['marker']}` `{item.get('time')}` {item['line'][:220]}" for item in ordered[:50]) if ordered else "- none",
        "",
        "## Evidence",
        "",
        f"- `{manifest['out_dir']}`",
        "",
        "## Source References",
        "",
        *[f"- {item}" for item in manifest["source_references"]],
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    if args.command == "plan":
        inputs = {
            "android_dmesg": {"exists": True, "path": str(repo_path(args.android_dmesg))},
            "android_processes": {"exists": True, "path": str(repo_path(args.android_processes))},
            "android_props": {"exists": True, "path": str(repo_path(args.android_props))},
            "android_initrc": {"exists": True, "path": str(repo_path(args.android_initrc))},
            "android_devnodes": {"exists": True, "path": str(repo_path(args.android_devnodes))},
            "v517_manifest": {"exists": True, "path": str(repo_path(args.v517_manifest))},
            "v518_manifest": {"exists": True, "path": str(repo_path(args.v518_manifest))},
        }
        android_dmesg = android_processes = android_props = android_initrc = android_devnodes = ""
        v517_raw: dict[str, Any] = {"exists": True, "decision": "plan-only", "pass": True}
        v518_raw: dict[str, Any] = {"exists": True, "decision": "plan-only", "pass": True, "runtime_surface": {}}
    else:
        android_dmesg_exists, android_dmesg_path, android_dmesg = read_text_if_exists(args.android_dmesg)
        android_processes_exists, android_processes_path, android_processes = read_text_if_exists(args.android_processes)
        android_props_exists, android_props_path, android_props = read_text_if_exists(args.android_props)
        android_initrc_exists, android_initrc_path, android_initrc = read_text_if_exists(args.android_initrc)
        android_devnodes_exists, android_devnodes_path, android_devnodes = read_text_if_exists(args.android_devnodes)
        v517_raw = load_json_if_exists(args.v517_manifest)
        v518_raw = load_json_if_exists(args.v518_manifest)
        inputs = {
            "android_dmesg": {"exists": android_dmesg_exists, "path": android_dmesg_path},
            "android_processes": {"exists": android_processes_exists, "path": android_processes_path},
            "android_props": {"exists": android_props_exists, "path": android_props_path},
            "android_initrc": {"exists": android_initrc_exists, "path": android_initrc_path},
            "android_devnodes": {"exists": android_devnodes_exists, "path": android_devnodes_path},
            "v517_manifest": {"exists": v517_raw.get("exists") is True and not v517_raw.get("invalid"), "path": str(v517_raw.get("path"))},
            "v518_manifest": {"exists": v518_raw.get("exists") is True and not v518_raw.get("invalid"), "path": str(v518_raw.get("path"))},
        }
        for name, text in (
            ("android-dmesg-wifi-cnss-tail.txt", android_dmesg),
            ("android-processes-wifi.txt", android_processes),
            ("android-wifi-props-init-state.txt", android_props),
            ("android-initrc-wifi-grep.txt", android_initrc),
            ("android-devnodes-sockets-wifi.txt", android_devnodes),
        ):
            if text:
                store.write_text(f"inputs/{name}", text.rstrip() + "\n")

    android_summary = extract_events(android_dmesg)
    android_surface = process_surface(android_processes, android_props, android_devnodes, android_initrc)
    v517 = v517_summary(v517_raw)
    v518 = v518_summary(v518_raw)
    inventory = companion_inventory(binary_roots(args))
    checks = build_checks(args.command, inputs, android_summary, android_surface, v517, v518, inventory)
    decision, pass_ok, reason, next_step = decide(args.command, checks, android_summary, v517, v518, inventory)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "inputs": inputs,
        "checks": [asdict(check) for check in checks],
        "android_summary": android_summary,
        "android_surface": android_surface,
        "v517_summary": v517,
        "v518_summary": v518,
        "companion_inventory": inventory,
        "android_sequence_rows": android_sequence_rows(android_summary),
        "delta_rows": delta_rows(android_summary, v517_raw, v518, android_surface, inventory),
        "source_references": list(SOURCE_REFERENCES),
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("inputs")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
