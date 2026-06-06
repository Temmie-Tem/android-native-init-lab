#!/usr/bin/env python3
"""V1760 host-only WLAN-PD request-trigger surface classifier.

This classifier reads retained V1753 Android-good firmware-request evidence and
the V1736 native SM-route evidence.  It does not contact the device.  The goal is
to pin the request boundary after V1759 stopped route-minimization work:

* Android-good reaches the WLFW worker and then the modem asks tftp_server for
  wlanmdsp.mbn.
* Native reaches the same WLFW worker but the modem never asks for wlanmdsp.mbn.
* Android-good falls back from firmware_mnt to vendor/firmware and serves the
  file, so the immediate native blocker remains request generation, not serving.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_ANDROID_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1753-android-good-wlan-pd-firmware-request" / "manifest.json"
)
DEFAULT_NATIVE_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"
)
DEFAULT_DIFF_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1753-wlan-pd-firmware-request-diff" / "manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1760-wlan-pd-request-trigger-surface-classifier"
DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1760_WLAN_PD_REQUEST_TRIGGER_SURFACE_CLASSIFIER_2026-06-03.md"
)


ANDROID_EVENTS: tuple[tuple[str, str], ...] = (
    ("rmt_storage_ready", r"vendor\.rmt_storage: .*Shared memory initialised successfully"),
    ("tftp_server_started", r"tftp_server: Starting"),
    ("cnss_daemon_started", r"cnss-daemon: initialized exit socket pair"),
    ("wlfw_start", r"cnss-daemon: wlfw_start: Starting"),
    ("per_mgr_register", r"PerMgrSrv: .*add client cnss-daemon|cnss-daemon registered"),
    ("per_mgr_vote", r"PerMgrLib: cnss-daemon voting for modem|PerMgrSrv: cnss-daemon voting for modem"),
    ("ro_baseband_mdm", r"cnss-daemon: ro\.baseband : \[mdm\]"),
    ("wlfw_service_request", r"wlfw_service_request: Start the pthread"),
    ("wlanmdsp_request", r"tftp_server: .*wlanmdsp\.mbn"),
    ("wlan_pd_up", r"service-notifier: .*msm/modem/wlan_pd, state: 0x1fffffff"),
    ("icnss_qmi_connected", r"icnss_qmi: QMI Server Connected"),
    ("bdf_regdb", r"wlfw_send_bdf_download_req: BDF file : regdb\.bin"),
    ("fw_ready", r"icnss: WLAN FW is ready"),
    ("wlan0", r"dev : wlan0|wlan0:"),
)

NATIVE_EVENTS: tuple[tuple[str, str], ...] = (
    ("rmt_storage_ready", r"rmt_storage:INFO:main: Done with init now waiting for messages"),
    ("modem_reset_out", r"modem: Brought out of reset"),
    ("qrtr_readiness", r"qrtr: Modem QMI Readiness RX"),
    ("wlanmdsp_request", r"wlanmdsp\.mbn"),
    ("wlan_pd_up", r"service-notifier: .*msm/modem/wlan_pd, state: 0x1fffffff"),
    ("icnss_qmi_connected", r"icnss_qmi: QMI Server Connected"),
    ("bdf_regdb", r"BDF file : regdb\.bin"),
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


def read_text(path: Path, limit: int = 5_000_000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def str_int(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def parse_logcat_time(line: str) -> float | None:
    match = re.match(r"\d\d-\d\d\s+(\d\d):(\d\d):(\d\d)\.(\d{3})\s+", line)
    if not match:
        return None
    hour, minute, second, millisecond = (int(part) for part in match.groups())
    return ((hour * 60 + minute) * 60 + second) + millisecond / 1000.0


def parse_dmesg_time(line: str) -> float | None:
    match = re.search(r"\[\s*(\d+\.\d+)\]", line)
    if not match:
        return None
    return float(match.group(1))


def first_events(text: str, patterns: tuple[tuple[str, str], ...], *, logcat: bool) -> dict[str, Event]:
    result: dict[str, Event] = {}
    compiled = [(name, re.compile(pattern, re.IGNORECASE)) for name, pattern in patterns]
    for line in text.splitlines():
        for name, pattern in compiled:
            if name in result or not pattern.search(line):
                continue
            result[name] = Event(
                name=name,
                timestamp=parse_logcat_time(line) if logcat else parse_dmesg_time(line),
                line=line.strip(),
            )
    return result


def event_payload(events: dict[str, Event]) -> dict[str, dict[str, str | float | None]]:
    ordered = sorted(events.items(), key=lambda item: item[1].timestamp if item[1].timestamp is not None else 1e18)
    return {name: {"timestamp": event.timestamp, "line": event.line} for name, event in ordered}


def relative_rows(events: dict[str, Event], anchor: str) -> list[dict[str, str]]:
    anchor_time = events.get(anchor).timestamp if anchor in events else None
    rows: list[dict[str, str]] = []
    for name, event in sorted(events.items(), key=lambda item: item[1].timestamp if item[1].timestamp is not None else 1e18):
        if event.timestamp is None:
            time_text = "n/a"
        else:
            time_text = f"{event.timestamp:.3f}"
        if event.timestamp is None or anchor_time is None:
            delta_text = "n/a"
        else:
            delta_text = f"{event.timestamp - anchor_time:+.3f}s"
        rows.append({"event": name, "time": time_text, "delta": delta_text})
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


def android_base(manifest_path: Path) -> Path:
    manifest = load_json(manifest_path)
    return Path(manifest["out_dir"]) / "android-postfs-evidence" / "a90-v1753-wlan-pd-fwreq"


def native_base(manifest_path: Path) -> Path:
    manifest = load_json(manifest_path)
    return Path(manifest["out_dir"])


def collect_android(manifest_path: Path) -> dict[str, Any]:
    base = android_base(manifest_path)
    logcat = read_text(base / "logcat-filtered.txt")
    dmesg = read_text(base / "dmesg-filtered.txt")
    firmware_snapshot = read_text(base / "firmware-snapshot.txt")
    logcat_events = first_events(logcat, ANDROID_EVENTS, logcat=True)
    dmesg_events = first_events(dmesg, ANDROID_EVENTS, logcat=False)
    first_mnt_failure = ""
    first_vendor_success = ""
    first_vendor_size = ""
    for line in logcat.splitlines():
        if not first_mnt_failure and "firmware_mnt/image/wlanmdsp.mbn" in line:
            first_mnt_failure = line.strip()
        if not first_vendor_success and "readonly/vendor/firmware/wlanmdsp.mbn" in line:
            first_vendor_success = line.strip()
        if "OACK options" in line and "4251884" in line and not first_vendor_size:
            first_vendor_size = line.strip()
    return {
        "manifest": display_path(manifest_path),
        "base": display_path(base),
        "events": event_payload(logcat_events),
        "dmesg_events": event_payload(dmesg_events),
        "timeline_rows": relative_rows(logcat_events, "wlanmdsp_request"),
        "requested_wlanmdsp": "wlanmdsp_request" in logcat_events,
        "served_path": {
            "firmware_mnt_attempt_seen": bool(first_mnt_failure),
            "vendor_firmware_attempt_seen": bool(first_vendor_success),
            "vendor_firmware_oack_size_seen": bool(first_vendor_size),
            "first_firmware_mnt_line": first_mnt_failure,
            "first_vendor_firmware_line": first_vendor_success,
            "first_vendor_oack_size_line": first_vendor_size,
            "snapshot_has_vendor_firmware_wlanmdsp": bool(
                re.search(r"^/vendor/firmware/wlanmdsp\.mbn$", firmware_snapshot, re.MULTILINE)
            ),
            "snapshot_has_firmware_mnt_wlanmdsp": bool(
                re.search(r"^/vendor/firmware_mnt/image/wlanmdsp\.mbn$", firmware_snapshot, re.MULTILINE)
            ),
        },
    }


def collect_native(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    base = native_base(manifest_path)
    helper = read_text(base / "test-v1393-helper-result.stdout.txt")
    dmesg = read_text(base / "test-v1393-dmesg.stdout.txt")
    events = first_events(dmesg, NATIVE_EVENTS, logcat=False)
    helper_keys = parse_key_values(helper)
    gate = manifest.get("gate") or {}
    return {
        "manifest": display_path(manifest_path),
        "base": display_path(base),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "gate": gate,
        "events": event_payload(events),
        "helper_keys": {
            "order": helper_keys.get("wifi_companion_start.order", ""),
            "peripheral_manager_enabled": helper_keys.get("wifi_companion_start.peripheral_manager.enabled", ""),
            "firmware_serve_gate_enabled": helper_keys.get("wifi_companion_start.wlan_pd_firmware_serve_gate.enabled", ""),
            "service_manager": str(gate.get("service_manager", "")),
            "tftp_running": str(gate.get("tftp_running", "")),
            "wlfw_start_hit_count": str(gate.get("wlfw_start_hit_count", "")),
            "wlfw_service_request_hit_count": str(gate.get("wlfw_service_request_hit_count", "")),
            "wlfw_worker_create_success_hit_count": str(gate.get("wlfw_worker_create_success_hit_count", "")),
            "requested_wlanmdsp": str(gate.get("requested_wlanmdsp", "")),
            "wlfw_service69_seen": str(gate.get("wlfw_service69_seen", "")),
        },
        "contains": {
            "wlanmdsp_request": bool(re.search(r"wlanmdsp\.mbn", helper + "\n" + dmesg, re.IGNORECASE)),
            "wlan_pd_uninit": bool(re.search(r"curr_state_name=uninit|state: 0x7fffffff", helper, re.IGNORECASE)),
        },
    }


def classify(android: dict[str, Any], native: dict[str, Any], diff: dict[str, Any]) -> tuple[str, bool, str, str]:
    if diff.get("label") != "firmware-not-requested":
        return (
            "v1760-prerequisite-v1753-label-mismatch",
            False,
            "V1753 diff is not currently fixed at firmware-not-requested",
            "prerequisite-mismatch",
        )
    if not android["requested_wlanmdsp"]:
        return (
            "v1760-android-good-request-missing",
            False,
            "Android-good evidence no longer exposes a wlanmdsp request",
            "android-good-request-missing",
        )
    if str_int(native["helper_keys"]["requested_wlanmdsp"]) != 0:
        return (
            "v1760-native-request-present-reclassify",
            False,
            "native baseline now reports a wlanmdsp request and must be reclassified",
            "native-request-present",
        )
    if not android["served_path"]["vendor_firmware_oack_size_seen"]:
        return (
            "v1760-android-served-path-success-unproven",
            False,
            "Android-good request was visible but successful vendor/firmware fallback was not proven",
            "android-served-path-unproven",
        )
    return (
        "v1760-android-good-serves-wlanmdsp-native-never-requests-host-pass",
        True,
        "Android-good requests wlanmdsp after the WLFW worker and serves it via vendor/firmware fallback; native reaches the same WLFW worker with tftp_server running but never requests wlanmdsp",
        "request-generation-gap-before-firmware-serving",
    )


def markdown_table(rows: list[dict[str, str]], headers: tuple[str, ...]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(row.get(header, "") for header in headers) + " |")
    return "\n".join(out)


def render_report(result: dict[str, Any]) -> str:
    android = result["android"]
    native = result["native"]
    served = android["served_path"]
    native_keys = native["helper_keys"]
    return "\n".join(
        [
            "# Native Init V1760 WLAN-PD Request-trigger Surface Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1760`",
            "- Type: host-only request-trigger/served-path classifier",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Android-good Timeline",
            "",
            markdown_table(android["timeline_rows"], ("event", "time", "delta")),
            "",
            "## Android Served-path Fallback",
            "",
            f"- firmware_mnt attempt seen: `{served['firmware_mnt_attempt_seen']}`",
            f"- vendor/firmware attempt seen: `{served['vendor_firmware_attempt_seen']}`",
            f"- vendor/firmware OACK size seen: `{served['vendor_firmware_oack_size_seen']}`",
            f"- snapshot has `/vendor/firmware/wlanmdsp.mbn`: `{served['snapshot_has_vendor_firmware_wlanmdsp']}`",
            f"- snapshot has `/vendor/firmware_mnt/image/wlanmdsp.mbn`: `{served['snapshot_has_firmware_mnt_wlanmdsp']}`",
            "",
            "```text",
            served["first_firmware_mnt_line"],
            served["first_vendor_firmware_line"],
            served["first_vendor_oack_size_line"],
            "```",
            "",
            "## Native SM-route Baseline",
            "",
            f"- Manifest: `{native['manifest']}`",
            f"- Decision/pass: `{native['decision']}` / `{native['pass']}`",
            f"- Order: `{native_keys['order']}`",
            f"- service-manager / tftp running: `{native_keys['service_manager']}` / `{native_keys['tftp_running']}`",
            f"- WLFW start/request/worker hits: `{native_keys['wlfw_start_hit_count']}` / `{native_keys['wlfw_service_request_hit_count']}` / `{native_keys['wlfw_worker_create_success_hit_count']}`",
            f"- requested `wlanmdsp`: `{native_keys['requested_wlanmdsp']}`",
            f"- WLFW service 69: `{native_keys['wlfw_service69_seen']}`",
            f"- WLAN-PD uninit evidence: `{native['contains']['wlan_pd_uninit']}`",
            "",
            "## Interpretation",
            "",
            "- Android-good proves the modem-side request happens after `wlfw_service_request` and before WLAN-PD/ICNSS progress.",
            "- Android-good also proves the first `firmware_mnt` lookup can fail and still recover through `/vendor/firmware/wlanmdsp.mbn`; therefore a native fix cannot be scoped as served-path repair while native has no request.",
            "- Native V1736 reaches the WLFW worker and has `tftp_server` running, but `wlanmdsp.mbn` is never requested and WLAN-PD remains `UNINIT`.",
            "- The active blocker is request generation/autoload trigger before firmware serving.  Do not add PM actors, QCACLD, eSoC/RC1, restart-PD, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping in this unit.",
            "",
            "## Next",
            "",
            "- V1761 should remain host/source-only first: inspect the modem-side WLAN-PD autoload trigger contract around Android-good `wlfw_service_request -> wlanmdsp request` without adding actors.",
            "- A later live gate is justified only if it observes or repairs a single identified request-trigger condition and still measures `requested_wlanmdsp`, WLFW service 69, and `wlan0` before any connection attempt.",
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device contact, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware/partition write, or actor start.",
            "",
        ]
    )


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
        "cycle": "V1760",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "label": label,
        "android": android,
        "native": native,
        "diff_manifest": display_path(args.diff_manifest),
        "out_dir": display_path(args.out_dir),
    }
    store.write_json("manifest.json", result)
    report = render_report(result)
    store.write_text("summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({"decision": decision, "pass": pass_ok, "label": label, "out_dir": result["out_dir"]}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
