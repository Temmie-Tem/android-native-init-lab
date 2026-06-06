#!/usr/bin/env python3
"""V586 QRTR/control-plane blocker classifier after V585.

This classifier is intentionally read-only. It compares the latest V585
companion/private-firmware-mount evidence with Android reference markers and
the current native QRTR surface. It does not start daemons, write qcwlanstate,
start HALs, scan, connect, route, ping externally, reboot, or flash anything.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v586-qrtr-companion-blocker")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_V585_MANIFEST = Path("tmp/wifi/v585-companion-firmware-mount-start-only/manifest.json")
DEFAULT_V585_HELPER_STDOUT = Path("tmp/wifi/v585-companion-firmware-mount-start-only/native/helper-stdout-section.txt")
DEFAULT_V585_DMESG_DELTA = Path("tmp/wifi/v585-companion-firmware-mount-start-only/native/dmesg-delta.txt")
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/dmesg-wifi-cnss-tail.txt")
DEFAULT_ANDROID_PROCESSES = Path("tmp/wifi/v524-android-companion-exact-recapture-handoff/v521-android-companion-recapture-run/android/commands/processes-wifi.txt")
DEFAULT_V571_MANIFEST = Path("tmp/wifi/v571-qrtr-modem-readiness-delta/manifest.json")
DEFAULT_V582_MANIFEST = Path("tmp/wifi/v582-modem-companion-classifier/manifest.json")

SOURCE_REFERENCES = (
    "https://codebrowser.dev/linux/linux/net/qrtr/af_qrtr.c.html",
    "https://android.googlesource.com/kernel/common/+/d4d74449367e/net/qrtr/qrtr.c",
    "https://android.googlesource.com/kernel/msm/+/refs/heads/android-msm-crosshatch-4.9-s-preview-1/drivers/soc/qcom/service-notifier.c",
    "https://android.googlesource.com/kernel/msm/+/refs/heads/android-msm-crosshatch-4.9-s-preview-1/drivers/soc/qcom/sysmon-qmi.c",
)

KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
QIPCRTR_RE = re.compile(r"^QIPCRTR\s+\S+\s+(?P<sockets>-?\d+)\b", re.MULTILINE)

MARKER_PATTERNS: dict[str, re.Pattern[str]] = {
    "qrtr_modem_readiness_rx": re.compile(r"qrtr: Modem QMI Readiness RX", re.I),
    "qrtr_modem_readiness_tx": re.compile(r"qrtr: Modem QMI Readiness TX", re.I),
    "sysmon_qmi_ready": re.compile(r"sysmon-qmi: .*Connection established", re.I),
    "service_notifier_ready": re.compile(r"service-notifier: .*Connection established", re.I),
    "wlan_pd_indication": re.compile(r"service-notifier:.*(?:wlan_pd|msm/modem/wlan)", re.I),
    "cnss_diag_netlink": re.compile(r"netlink_create.*comm:\s*cnss_diag|comm:cnss_diag", re.I),
    "cnss_daemon_netlink": re.compile(r"netlink_create.*comm:\s*cnss-daemon|comm:cnss-daemon|cnss-daemon.*ctrl_getfamily", re.I),
    "wlfw_start": re.compile(r"cnss-daemon wlfw_start: Starting", re.I),
    "wlfw_thread": re.compile(r"cnss-daemon wlfw_service_request", re.I),
    "qmi_server_connected": re.compile(r"icnss_qmi: QMI Server Connected", re.I),
    "bdf_regdb": re.compile(r"BDF file\s*:\s*regdb\.bin|regdb\.bin", re.I),
    "bdf_bdwlan": re.compile(r"BDF file\s*:\s*bdwlan\.bin|bdwlan\.bin", re.I),
    "wlan_fw_ready": re.compile(r"icnss: WLAN FW is ready|FW ready event received|wma_wait_for_ready_event", re.I),
    "wlan0_event": re.compile(r"dev\s*:\s*wlan0\s*:\s*event|\bwlan0\b", re.I),
}

LOWER_READINESS_MARKERS = (
    "qrtr_modem_readiness_rx",
    "qrtr_modem_readiness_tx",
    "sysmon_qmi_ready",
    "service_notifier_ready",
    "wlan_pd_indication",
    "wlfw_start",
    "wlfw_thread",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wlan0_event",
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--v585-manifest", type=Path, default=DEFAULT_V585_MANIFEST)
    parser.add_argument("--v585-helper-stdout", type=Path, default=DEFAULT_V585_HELPER_STDOUT)
    parser.add_argument("--v585-dmesg-delta", type=Path, default=DEFAULT_V585_DMESG_DELTA)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--android-processes", type=Path, default=DEFAULT_ANDROID_PROCESSES)
    parser.add_argument("--v571-manifest", type=Path, default=DEFAULT_V571_MANIFEST)
    parser.add_argument("--v582-manifest", type=Path, default=DEFAULT_V582_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"))
    return parser.parse_args()


def clean_text(text: str) -> str:
    return ANSI_RE.sub("", text.replace("\x00", ""))


def read_text_if_exists(path: Path) -> tuple[bool, str, str]:
    resolved = repo_path(path)
    if not resolved.exists():
        return False, str(resolved), ""
    return True, str(resolved), resolved.read_text(encoding="utf-8", errors="replace")


def load_json_if_exists(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "invalid": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    return item


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def manifest_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: value for key, value in step.items() if key != "payload"} for step in steps]


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    return [
        run_step(args, store, "version", ["version"], 15.0),
        run_step(args, store, "status", ["status"], 25.0),
        run_step(args, store, "selftest", ["selftest"], 25.0),
        run_step(args, store, "proc-net-protocols", ["run", args.toybox, "cat", "/proc/net/protocols"], 20.0),
        run_step(args, store, "proc-net-qrtr", ["run", args.toybox, "cat", "/proc/net/qrtr"], 10.0),
        run_step(args, store, "stat-dev-qrtr", ["run", args.toybox, "stat", "/dev/qrtr"], 10.0),
        run_step(args, store, "find-dev-qmi-qrtr-cnss", ["run", args.toybox, "find", "/dev", "-maxdepth", "4", "-name", "*qmi*", "-o", "-name", "*qrtr*", "-o", "-name", "*cnss*", "-o", "-name", "*diag*"], 30.0),
        run_step(args, store, "find-sys-qrtr-modem", ["run", args.toybox, "find", "/sys", "-maxdepth", "7", "-iname", "*qrtr*", "-o", "-iname", "*rpmsg*", "-o", "-iname", "*subsys*", "-o", "-iname", "*sysmon*", "-o", "-iname", "*service*notifier*", "-o", "-iname", "*wlan*", "-o", "-iname", "*icnss*"], 40.0),
        run_step(args, store, "proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
        run_step(args, store, "ps", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 25.0),
        run_step(args, store, "dmesg", ["run", args.toybox, "dmesg"], 60.0),
    ]


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in clean_text(text).splitlines():
        line = raw_line.strip()
        match = KEY_RE.match(line)
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def parse_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def qipcrtr_sockets(protocols: str) -> int | None:
    match = QIPCRTR_RE.search(clean_text(protocols))
    if not match:
        return None
    return parse_int(match.group("sockets"))


def proc_qrtr_present(text: str, ok: bool | None = None) -> bool:
    cleaned = clean_text(text).strip()
    if ok is False:
        return False
    if not cleaned:
        return ok is True
    if "No such file or directory" in cleaned:
        return False
    return True


def count_markers(text: str) -> dict[str, int]:
    counts = {name: 0 for name in MARKER_PATTERNS}
    for line in clean_text(text).splitlines():
        for name, pattern in MARKER_PATTERNS.items():
            if pattern.search(line):
                counts[name] += 1
    return counts


def present_markers(counts: dict[str, int], names: tuple[str, ...] = LOWER_READINESS_MARKERS) -> list[str]:
    return [name for name in names if int(counts.get(name, 0) or 0) > 0]


def extract_socket_counts(keys: dict[str, str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    prefix = "capture.wifi_hal_composite_"
    suffix = ".fd_links.socket_count"
    for key, value in keys.items():
        if key.startswith(prefix) and key.endswith(suffix):
            label = key[len(prefix):-len(suffix)]
            parsed = parse_int(value, 0)
            counts[label] = int(parsed or 0)
    return counts


def v585_evidence(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json_if_exists(args.v585_manifest)
    stdout_exists, stdout_path, stdout = read_text_if_exists(args.v585_helper_stdout)
    delta_exists, delta_path, delta = read_text_if_exists(args.v585_dmesg_delta)
    keys = parse_keys(stdout)
    live = manifest.get("live_result") if isinstance(manifest.get("live_result"), dict) else {}
    dmesg_counts = count_markers(delta)
    socket_counts = extract_socket_counts(keys)
    return {
        "manifest": {
            "exists": manifest.get("exists"),
            "path": manifest.get("path"),
            "decision": manifest.get("decision"),
            "pass": manifest.get("pass"),
            "reason": manifest.get("reason"),
            "next_step": manifest.get("next_step"),
        },
        "helper_stdout": {"exists": stdout_exists, "path": stdout_path},
        "dmesg_delta": {"exists": delta_exists, "path": delta_path},
        "private_firmware_mounts_ready": bool(live.get("private_firmware_mounts_ready")),
        "helper_result": live.get("helper_result"),
        "all_observable": live.get("all_observable"),
        "all_postflight_safe": live.get("all_postflight_safe"),
        "qipcrtr_sockets_net_before": parse_int(keys.get("wifi_companion_start.net_before.qipcrtr_sockets")),
        "qipcrtr_sockets_net_after_spawn": parse_int(keys.get("wifi_companion_start.net_after_spawn.qipcrtr_sockets")),
        "qipcrtr_sockets_net_window": parse_int(keys.get("wifi_companion_start.net_window.qipcrtr_sockets")),
        "qipcrtr_sockets_net_after_cleanup": parse_int(keys.get("wifi_companion_start.net_after_cleanup.qipcrtr_sockets")),
        "net_window_qrtr_captured": keys.get("wifi_companion_start.net_window.qrtr_captured"),
        "net_window_qipcrtr_present": keys.get("wifi_companion_start.net_window.qipcrtr_present"),
        "qrtr_proc_open_error": "A90_EXECNS_CNSS_PROC_wifi_companion_net_qrtr_BEGIN" in stdout and "open-error=No such file or directory" in stdout,
        "qrtr_nameservice_readback": keys.get("wifi_companion_start.qrtr_nameservice_readback"),
        "qmi_payload": keys.get("wifi_companion_start.qmi_payload"),
        "scan_connect_linkup": keys.get("wifi_companion_start.scan_connect_linkup"),
        "external_ping": keys.get("wifi_companion_start.external_ping"),
        "socket_counts": socket_counts,
        "dmesg_counts": dmesg_counts,
        "readiness_markers": present_markers(dmesg_counts),
    }


def android_evidence(args: argparse.Namespace) -> dict[str, Any]:
    dmesg_exists, dmesg_path, dmesg = read_text_if_exists(args.android_dmesg)
    processes_exists, processes_path, processes = read_text_if_exists(args.android_processes)
    counts = count_markers(dmesg)
    process_patterns = {
        "qrtr_ns": re.compile(r"\bqrtr-ns\b", re.I),
        "pd_mapper": re.compile(r"\bpd-mapper\b", re.I),
        "cnss_diag": re.compile(r"\bcnss_diag\b", re.I),
        "cnss_daemon": re.compile(r"\bcnss-daemon\b", re.I),
        "wifi_hal": re.compile(r"android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi", re.I),
    }
    process_counts = {name: len(pattern.findall(processes)) for name, pattern in process_patterns.items()}
    return {
        "dmesg": {"exists": dmesg_exists, "path": dmesg_path},
        "processes": {"exists": processes_exists, "path": processes_path},
        "dmesg_counts": counts,
        "readiness_markers": present_markers(counts),
        "process_counts": process_counts,
    }


def current_evidence(steps: list[dict[str, Any]]) -> dict[str, Any]:
    version = step_payload(steps, "version")
    status = step_payload(steps, "status")
    selftest = step_payload(steps, "selftest")
    protocols = step_payload(steps, "proc-net-protocols")
    proc_qrtr = step_payload(steps, "proc-net-qrtr")
    stat_dev_qrtr = step_payload(steps, "stat-dev-qrtr")
    dmesg = step_payload(steps, "dmesg")
    proc_qrtr_step = next((step for step in steps if step.get("name") == "proc-net-qrtr"), {})
    dev_qrtr_step = next((step for step in steps if step.get("name") == "stat-dev-qrtr"), {})
    counts = count_markers(dmesg)
    return {
        "version_ok": DEFAULT_EXPECT_VERSION in version,
        "selftest_ok": "fail=0" in status and "fail=0" in selftest,
        "qipcrtr_protocol_present": "QIPCRTR" in protocols,
        "qipcrtr_sockets": qipcrtr_sockets(protocols),
        "proc_net_qrtr_present": proc_qrtr_present(proc_qrtr, proc_qrtr_step.get("ok")),
        "dev_qrtr_present": dev_qrtr_step.get("ok") is True and "No such file or directory" not in stat_dev_qrtr,
        "dmesg_counts": counts,
        "readiness_markers": present_markers(counts),
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace,
                 steps: list[dict[str, Any]],
                 android: dict[str, Any],
                 v585: dict[str, Any],
                 current: dict[str, Any],
                 v571: dict[str, Any],
                 v582: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run V586 read-only classifier")
        return checks
    add_check(checks, "native-health", "pass" if current.get("version_ok") and current.get("selftest_ok") else "blocked", "blocker",
              f"version_ok={current.get('version_ok')} selftest_ok={current.get('selftest_ok')}",
              [DEFAULT_EXPECT_VERSION], "restore stable native baseline before Wi-Fi work")
    add_check(checks, "android-reference-markers", "pass" if android.get("readiness_markers") else "blocked", "blocker",
              "markers=" + ",".join(android.get("readiness_markers") or []),
              [str((android.get("dmesg") or {}).get("path"))], "recapture Android baseline if reference evidence is stale")
    add_check(checks, "v585-bounded-proof", "pass" if (v585.get("manifest") or {}).get("decision") == "v585-companion-firmware-mount-start-only-no-fw-marker" and (v585.get("manifest") or {}).get("pass") is True else "blocked", "blocker",
              f"decision={(v585.get('manifest') or {}).get('decision')} pass={(v585.get('manifest') or {}).get('pass')}",
              [str((v585.get("manifest") or {}).get("path"))], "rerun V585 before V586 comparison")
    add_check(checks, "v585-private-mounts", "pass" if v585.get("private_firmware_mounts_ready") else "blocked", "blocker",
              f"private_firmware_mounts_ready={v585.get('private_firmware_mounts_ready')}",
              [str((v585.get("helper_stdout") or {}).get("path"))], "fix helper private firmware mount setup before QRTR retry")
    add_check(checks, "v585-companion-clean", "pass" if v585.get("all_observable") and v585.get("all_postflight_safe") else "blocked", "blocker",
              f"helper_result={v585.get('helper_result')} observable={v585.get('all_observable')} safe={v585.get('all_postflight_safe')}",
              [str((v585.get("manifest") or {}).get("path"))], "inspect cleanup before any further live companion run")
    add_check(checks, "v571-v582-context", "pass" if v571.get("pass") is True and v582.get("pass") is True else "warn", "info",
              f"v571={v571.get('decision')} v582={v582.get('decision')}",
              [str(v571.get("path")), str(v582.get("path"))], "refresh classifiers if source evidence changes")
    add_check(checks, "current-qipcrtr-family", "pass" if current.get("qipcrtr_protocol_present") else "blocked", "blocker",
              f"qipcrtr_present={current.get('qipcrtr_protocol_present')} sockets={current.get('qipcrtr_sockets')}",
              [], "kernel QRTR family must be present before companion QRTR proof")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def classify(args: argparse.Namespace,
             checks: list[Check],
             android: dict[str, Any],
             v585: dict[str, Any],
             current: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v586-qrtr-companion-blocker-plan-ready", True, "plan-only; no device command executed", "run V586 read-only classifier"
    blocked = blockers(checks)
    if blocked:
        return "v586-qrtr-companion-blocker-prereq-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before interpreting QRTR delta"
    current_markers = current.get("readiness_markers") or []
    v585_markers = v585.get("readiness_markers") or []
    if current_markers or v585_markers:
        markers = ",".join(sorted(set(current_markers + v585_markers)))
        return "v586-readiness-marker-observed", True, "lower readiness marker observed: " + markers, "plan bounded qcwlanstate/HAL retry without scan/connect"

    v585_window_sockets = v585.get("qipcrtr_sockets_net_window")
    current_sockets = current.get("qipcrtr_sockets")
    if v585_window_sockets == 0 and current_sockets == 0 and v585.get("qrtr_proc_open_error"):
        return (
            "v586-qrtr-control-plane-not-entered",
            True,
            "V585 companions and private firmware mounts were alive, but QRTR proc table was absent, QIPCRTR sockets stayed 0, and Android-only QRTR/QMI/WLAN-PD/WLFW markers remain missing",
            "do not retry qcwlanstate/HAL yet; next prove the modem/QRTR readiness input path in a host-controlled post-boot window",
        )
    return (
        "v586-qrtr-companion-review-required",
        False,
        f"unexpected QRTR state: v585_window_sockets={v585_window_sockets} current_sockets={current_sockets} qrtr_proc_open_error={v585.get('qrtr_proc_open_error')}",
        "inspect V586 evidence before choosing the next live gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[item["name"], item["status"], item["severity"], item["detail"], item["next_step"]] for item in manifest["checks"]]
    android_counts = [[key, value] for key, value in sorted((manifest["android_evidence"].get("dmesg_counts") or {}).items())]
    v585_counts = [[key, value] for key, value in sorted((manifest["v585_evidence"].get("dmesg_counts") or {}).items())]
    current_counts = [[key, value] for key, value in sorted((manifest["current_evidence"].get("dmesg_counts") or {}).items())]
    socket_rows = [[key, value] for key, value in sorted((manifest["v585_evidence"].get("socket_counts") or {}).items())]
    return "\n".join([
        "# V586 QRTR Companion Blocker Classifier",
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
        markdown_table(["name", "status", "severity", "detail", "next"], checks),
        "",
        "## QRTR State",
        "",
        markdown_table(["key", "value"], [
            ["current_qipcrtr_protocol_present", manifest["current_evidence"].get("qipcrtr_protocol_present")],
            ["current_qipcrtr_sockets", manifest["current_evidence"].get("qipcrtr_sockets")],
            ["current_proc_net_qrtr_present", manifest["current_evidence"].get("proc_net_qrtr_present")],
            ["current_dev_qrtr_present", manifest["current_evidence"].get("dev_qrtr_present")],
            ["v585_private_firmware_mounts_ready", manifest["v585_evidence"].get("private_firmware_mounts_ready")],
            ["v585_qipcrtr_sockets_net_window", manifest["v585_evidence"].get("qipcrtr_sockets_net_window")],
            ["v585_qrtr_proc_open_error", manifest["v585_evidence"].get("qrtr_proc_open_error")],
            ["v585_qrtr_nameservice_readback", manifest["v585_evidence"].get("qrtr_nameservice_readback")],
        ]),
        "",
        "## V585 Companion Socket Counts",
        "",
        markdown_table(["child", "socket_count"], socket_rows) if socket_rows else "- none",
        "",
        "## Android Marker Counts",
        "",
        markdown_table(["marker", "count"], android_counts),
        "",
        "## V585 Dmesg Delta Counts",
        "",
        markdown_table(["marker", "count"], v585_counts),
        "",
        "## Current Native Dmesg Counts",
        "",
        markdown_table(["marker", "count"], current_counts),
        "",
        "## Source References",
        "",
        "\n".join(f"- `{ref}`" for ref in manifest["source_references"]),
        "",
        "## Evidence",
        "",
        f"- `{manifest['out_dir']}`",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    if args.command == "run":
        steps = collect_steps(args, store)
    android = android_evidence(args)
    v585 = v585_evidence(args)
    current = current_evidence(steps) if steps else {}
    v571 = load_json_if_exists(args.v571_manifest)
    v582 = load_json_if_exists(args.v582_manifest)
    checks = build_checks(args, steps, android, v585, current, v571, v582)
    decision, pass_ok, reason, next_step = classify(args, checks, android, v585, current)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "steps": manifest_steps(steps),
        "checks": [asdict(check) for check in checks],
        "android_evidence": android,
        "v585_evidence": v585,
        "current_evidence": current,
        "v571_manifest": {
            "exists": v571.get("exists"),
            "path": v571.get("path"),
            "decision": v571.get("decision"),
            "pass": v571.get("pass"),
        },
        "v582_manifest": {
            "exists": v582.get("exists"),
            "path": v582.get("path"),
            "decision": v582.get("decision"),
            "pass": v582.get("pass"),
        },
        "source_references": list(SOURCE_REFERENCES),
        "device_commands_executed": args.command == "run",
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
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
