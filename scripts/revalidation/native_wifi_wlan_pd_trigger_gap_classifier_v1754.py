#!/usr/bin/env python3
"""V1754 host-only WLAN-PD autoload trigger-gap classifier."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ANDROID_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1753-android-good-wlan-pd-firmware-request" / "manifest.json"
)
DEFAULT_NATIVE_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"
)
DEFAULT_DIFF_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1753-wlan-pd-firmware-request-diff" / "manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1754-wlan-pd-trigger-gap-classifier"
DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1754_WLAN_PD_TRIGGER_GAP_CLASSIFIER_2026-06-03.md"
)


ANDROID_EVENT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("rmt_storage_ready", r"vendor\.rmt_storage: .*Shared memory initialised successfully"),
    ("tftp_server_started", r"tftp_server: Starting"),
    ("cnss_diag_started", r"cnss_diag: initialized exit socket pair"),
    ("cnss_daemon_started", r"cnss-daemon: initialized exit socket pair"),
    ("cnss_wlfw_start", r"cnss-daemon: wlfw_start: Starting"),
    ("per_mgr_register", r"PerMgrSrv: .*add client cnss-daemon|cnss-daemon registered"),
    ("per_mgr_vote", r"PerMgrLib: cnss-daemon voting for modem|PerMgrSrv: cnss-daemon voting for modem"),
    ("cnss_wlfw_service_request", r"wlfw_service_request: Start the pthread"),
    ("wlanmdsp_request", r"tftp_server: .*wlanmdsp\.mbn"),
    ("wlan_pd_up", r"service-notifier: .*msm/modem/wlan_pd, state: 0x1fffffff"),
    ("icnss_qmi_connected", r"icnss_qmi: QMI Server Connected"),
    ("bdf_regdb", r"wlfw_send_bdf_download_req: BDF file : regdb\.bin"),
    ("bdf_bdwlan", r"wlfw_send_bdf_download_req: BDF file : bdwlan\.bin"),
    ("fw_ready", r"icnss: WLAN FW is ready"),
    ("wlan0", r"dev : wlan0|wlan0:"),
)

NATIVE_EVENT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("rmt_storage_ready", r"rmt_storage:INFO:main: Done with init now waiting for messages"),
    ("modem_reset_out", r"modem: Brought out of reset"),
    ("qrtr_readiness", r"qrtr: Modem QMI Readiness RX"),
    ("wlanmdsp_request", r"wlanmdsp\.mbn"),
    ("wlan_pd_up", r"service-notifier: .*msm/modem/wlan_pd, state: 0x1fffffff"),
    ("icnss_qmi_connected", r"icnss_qmi: QMI Server Connected"),
    ("bdf_regdb", r"BDF file : regdb\.bin"),
    ("bdf_bdwlan", r"BDF file : bdwlan\.bin"),
    ("fw_ready", r"icnss: WLAN FW is ready"),
    ("wlan0", r"dev : wlan0|wlan0:"),
)


@dataclass(frozen=True)
class Event:
    name: str
    timestamp: float | None
    line: str


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path, limit: int = 4_000_000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def str_int(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def android_base(manifest_path: Path) -> Path:
    manifest = load_json(manifest_path)
    return Path(manifest["out_dir"]) / "android-postfs-evidence" / "a90-v1753-wlan-pd-fwreq"


def native_base(manifest_path: Path) -> Path:
    manifest = load_json(manifest_path)
    return Path(manifest["out_dir"])


def parse_logcat_timestamp(line: str) -> float | None:
    match = re.match(r"\d\d-\d\d\s+(\d\d):(\d\d):(\d\d)\.(\d{3})\s+", line)
    if not match:
        return None
    hour, minute, second, millisecond = (int(part) for part in match.groups())
    return ((hour * 60 + minute) * 60 + second) + millisecond / 1000.0


def parse_dmesg_timestamp(line: str) -> float | None:
    match = re.match(r".*?\[\s*(\d+\.\d+)\]", line)
    if not match:
        return None
    return float(match.group(1))


def first_events(text: str, patterns: tuple[tuple[str, str], ...], timestamp_kind: str) -> dict[str, Event]:
    result: dict[str, Event] = {}
    compiled = [(name, re.compile(pattern, re.IGNORECASE)) for name, pattern in patterns]
    for line in text.splitlines():
        for name, pattern in compiled:
            if name in result or not pattern.search(line):
                continue
            timestamp = parse_logcat_timestamp(line) if timestamp_kind == "logcat" else parse_dmesg_timestamp(line)
            result[name] = Event(name, timestamp, line.strip())
    return result


def bool_text(value: bool) -> str:
    return "1" if value else "0"


def classify(android: dict[str, Any], native: dict[str, Any], diff: dict[str, Any]) -> tuple[str, bool, str, str]:
    android_events = android["events"]
    native_events = native["events"]
    native_gate = native["gate"]
    if diff.get("label") != "firmware-not-requested":
        return (
            "v1754-prerequisite-v1753-label-mismatch",
            False,
            "V1753 did not classify the route as firmware-not-requested",
            "prerequisite-mismatch",
        )
    if "wlanmdsp_request" not in android_events:
        return (
            "v1754-android-good-request-timeline-missing",
            False,
            "Android-good evidence no longer exposes the first wlanmdsp request",
            "android-good-request-missing",
        )
    if str_int(native_gate.get("requested_wlanmdsp")) > 0:
        return (
            "v1754-native-request-present-unexpected",
            False,
            "native baseline now reports requested_wlanmdsp > 0 and should be reclassified",
            "native-request-present",
        )
    android_has_pm_vote = "per_mgr_vote" in android_events or "per_mgr_register" in android_events
    native_pm_disabled = str(native["helper_keys"].get("wifi_companion_start.peripheral_manager.enabled")) == "0"
    native_pm_absent = not native["contains"].get("per_mgr_vote") and not native["contains"].get("per_mgr_register")
    if android_has_pm_vote and native_pm_disabled and native_pm_absent:
        return (
            "v1754-android-good-permgr-vote-before-wlanmdsp-native-pm-absent-host-pass",
            True,
            "Android-good shows cnss-daemon PM manager register/vote before the first wlanmdsp request, while the native V1736 SM route has PM disabled/absent and still never requests wlanmdsp",
            "peripheral-manager-vote-delta-before-firmware-request",
        )
    if "cnss_wlfw_service_request" in android_events and str_int(native_gate.get("wlfw_service_request_hit_count")) > 0:
        return (
            "v1754-wlfw-request-reached-but-trigger-still-missing-host-pass",
            True,
            "both Android-good and native reach the cnss-daemon wlfw request path, but only Android-good causes a wlanmdsp request",
            "post-wlfw-request-modem-trigger-gap",
        )
    return (
        "v1754-trigger-gap-incomplete",
        False,
        "available evidence did not isolate a supported Android-only pre-request trigger",
        "incomplete",
    )


def event_dict(events: dict[str, Event]) -> dict[str, dict[str, str | float | None]]:
    return {
        name: {"timestamp": event.timestamp, "line": event.line}
        for name, event in sorted(events.items(), key=lambda item: item[1].timestamp if item[1].timestamp is not None else 1e18)
    }


def relative_table(events: dict[str, Event], anchor: str) -> list[dict[str, str]]:
    anchor_time = events.get(anchor).timestamp if anchor in events else None
    rows: list[dict[str, str]] = []
    for name, event in sorted(events.items(), key=lambda item: item[1].timestamp if item[1].timestamp is not None else 1e18):
        if event.timestamp is None or anchor_time is None:
            delta = "n/a"
        else:
            delta = f"{event.timestamp - anchor_time:+.3f}s"
        rows.append({"event": name, "time": "n/a" if event.timestamp is None else f"{event.timestamp:.3f}", "delta": delta})
    return rows


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip()
    return values


def collect_android(manifest_path: Path) -> dict[str, Any]:
    base = android_base(manifest_path)
    logcat = read_text(base / "logcat-filtered.txt")
    dmesg = read_text(base / "dmesg-filtered.txt")
    events = first_events(logcat, ANDROID_EVENT_PATTERNS, "logcat")
    dmesg_events = first_events(dmesg, ANDROID_EVENT_PATTERNS, "dmesg")
    return {
        "manifest": display_path(manifest_path),
        "base": display_path(base),
        "events": events,
        "dmesg_events": dmesg_events,
        "contains": {
            "per_mgr_vote": bool(re.search(r"cnss-daemon voting for modem", logcat, re.IGNORECASE)),
            "per_mgr_register": bool(re.search(r"cnss-daemon registered|add client cnss-daemon", logcat, re.IGNORECASE)),
            "wlanmdsp": bool(re.search(r"wlanmdsp\.mbn", logcat, re.IGNORECASE)),
        },
    }


def collect_native(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    base = native_base(manifest_path)
    helper_text = read_text(base / "test-v1393-helper-result.stdout.txt")
    dmesg = read_text(base / "test-v1393-dmesg.stdout.txt")
    events = first_events(dmesg, NATIVE_EVENT_PATTERNS, "dmesg")
    helper_keys = parse_key_values(helper_text)
    return {
        "manifest": display_path(manifest_path),
        "base": display_path(base),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "gate": manifest.get("gate") or {},
        "events": events,
        "helper_keys": helper_keys,
        "contains": {
            "per_mgr_vote": bool(re.search(r"cnss-daemon voting for modem", helper_text + "\n" + dmesg, re.IGNORECASE)),
            "per_mgr_register": bool(re.search(r"cnss-daemon registered|add client cnss-daemon", helper_text + "\n" + dmesg, re.IGNORECASE)),
            "wlanmdsp": "wlanmdsp_request" in events,
        },
    }


def render_markdown(result: dict[str, Any]) -> str:
    android_events = result["android_events"]
    native_events = result["native_events"]
    android_rows = result["android_relative_to_wlanmdsp"]
    native_gate = result["native"]["gate"]
    return "\n".join([
        "# Native Init V1754 WLAN-PD Trigger-gap Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1754`",
        "- Type: host-only trigger-gap classifier from retained V1753/V1736 evidence",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Android-good Timeline",
        "",
        "| Event | Time | Delta to first `wlanmdsp` request |",
        "| --- | ---: | ---: |",
        *[
            f"| `{row['event']}` | `{row['time']}` | `{row['delta']}` |"
            for row in android_rows
        ],
        "",
        "## Native V1736 SM-route State",
        "",
        f"- Manifest: `{result['native']['manifest']}`",
        f"- Decision/pass: `{result['native']['decision']}` / `{result['native']['pass']}`",
        f"- `wlfw_start` / `wlfw_service_request` / worker hits: `{native_gate.get('wlfw_start_hit_count')}` / `{native_gate.get('wlfw_service_request_hit_count')}` / `{native_gate.get('wlfw_worker_create_success_hit_count')}`",
        f"- `requested_wlanmdsp`: `{native_gate.get('requested_wlanmdsp')}`",
        f"- firmware label: `{native_gate.get('old_firmware_serve_label')}`",
        f"- `wifi_companion_start.peripheral_manager.enabled`: `{result['native']['helper_keys'].get('wifi_companion_start.peripheral_manager.enabled')}`",
        f"- native PM register/vote text present: `{bool_text(result['native']['contains']['per_mgr_register'] or result['native']['contains']['per_mgr_vote'])}`",
        "",
        "## Android-good Key Lines",
        "",
        "```text",
        "\n".join(event["line"] for event in android_events.values()),
        "```",
        "",
        "## Native Key Lines",
        "",
        "```text",
        "\n".join(event["line"] for event in native_events.values()),
        "```",
        "",
        "## Interpretation",
        "",
        "- V1753 already fixed the redirect label as `firmware-not-requested`.",
        "- Android-good reaches `wlfw_start`, then records `cnss-daemon` PM manager registration/vote, then starts the WLFW request worker, then the internal modem asks `tftp_server` for `wlanmdsp.mbn`.",
        "- Native V1736 reaches the CNSS WLFW worker and has `tftp_server` running, but the PM manager path is disabled/absent in that route and no `wlanmdsp.mbn` request appears.",
        "- This is not authorization to add PM actors blindly. Earlier PM actor attempts still remain a known dead-end unless a new narrow gate repairs the specific native PM registration/vote contract without returning to eSoC/RC1 or Wi-Fi HAL work.",
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only and reads retained evidence. It performs no device contact, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware/partition write, or new actor start.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-manifest", type=Path, default=DEFAULT_ANDROID_MANIFEST)
    parser.add_argument("--native-manifest", type=Path, default=DEFAULT_NATIVE_MANIFEST)
    parser.add_argument("--diff-manifest", type=Path, default=DEFAULT_DIFF_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    android = collect_android(args.android_manifest)
    native = collect_native(args.native_manifest)
    diff = load_json(args.diff_manifest)
    decision, pass_ok, reason, label = classify(android, native, diff)
    result = {
        "cycle": "V1754",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "label": label,
        "android": {
            "manifest": android["manifest"],
            "base": android["base"],
            "events": event_dict(android["events"]),
            "dmesg_events": event_dict(android["dmesg_events"]),
            "contains": android["contains"],
        },
        "native": {
            "manifest": native["manifest"],
            "base": native["base"],
            "decision": native["decision"],
            "pass": native["pass"],
            "gate": native["gate"],
            "events": event_dict(native["events"]),
            "helper_keys": {
                key: value
                for key, value in native["helper_keys"].items()
                if key.startswith("wifi_companion_start.peripheral_manager")
            },
            "contains": native["contains"],
        },
        "android_relative_to_wlanmdsp": relative_table(android["events"], "wlanmdsp_request"),
        "out_dir": display_path(args.out_dir),
        "report_path": display_path(args.report_path),
        "safety": {
            "host_only": True,
            "device_contact": False,
            "flash": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credentials": False,
            "dhcp_routes": False,
            "external_ping": False,
        },
    }
    store.write_json("manifest.json", result)
    report = render_markdown({
        **result,
        "android_events": event_dict(android["events"]),
        "native_events": event_dict(native["events"]),
    })
    write_private_text(store.path("summary.md"), report)
    write_private_text(args.report_path, report)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
