#!/usr/bin/env python3
"""V1761 host-only WLAN-PD autoload/request-trigger contract classifier.

Reads retained Android-good V1753 and native V1736/V1758 evidence.  This does
not contact the device.  It narrows the post-V1760 request-generation blocker:

* Android-good: cnss-daemon reaches WLFW, obtains PeripheralManager
  register/vote evidence, then the modem requests wlanmdsp.mbn.
* Native V1736: cnss-daemon reaches the same WLFW worker, but the
  PeripheralManager object path stays null and wlanmdsp.mbn is never requested.

The output is a contract classifier, not authorization to add PM actors.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1761-wlan-pd-autoload-trigger-contract-classifier"
DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1761_WLAN_PD_AUTOLOAD_TRIGGER_CONTRACT_CLASSIFIER_2026-06-03.md"
)

ANDROID_LOGCAT = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1753-android-good-wlan-pd-firmware-request"
    / "android-postfs-evidence"
    / "a90-v1753-wlan-pd-fwreq"
    / "logcat-filtered.txt"
)
ANDROID_DMESG = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1753-android-good-wlan-pd-firmware-request"
    / "android-postfs-evidence"
    / "a90-v1753-wlan-pd-fwreq"
    / "dmesg-filtered.txt"
)
NATIVE_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"
NATIVE_HELPER_RESULT = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1736-wlan-pd-timestamped-observer-handoff"
    / "test-v1393-helper-result.stdout.txt"
)
V1760_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1760-wlan-pd-request-trigger-surface-classifier" / "manifest.json"
V1758_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1758-wlan-pd-provider-visibility-contract-classifier" / "manifest.json"

ANDROID_PATTERNS: tuple[tuple[str, str], ...] = (
    ("wlfw_start", r"cnss-daemon: wlfw_start: Starting"),
    ("per_mgr_register", r"PerMgrSrv: .*add client cnss-daemon|PerMgrSrv: cnss-daemon registered"),
    ("per_mgr_vote", r"PerMgrLib: cnss-daemon voting for modem|PerMgrSrv: cnss-daemon voting for modem"),
    ("wlfw_service_request", r"wlfw_service_request: Start the pthread"),
    ("wlanmdsp_request", r"tftp_server: .*wlanmdsp\.mbn"),
    ("bdf_regdb", r"wlfw_send_bdf_download_req: BDF file : regdb\.bin"),
)
ANDROID_DMESG_PATTERNS: tuple[tuple[str, str], ...] = (
    ("wlan_pd_up", r"service-notifier: .*msm/modem/wlan_pd, state: 0x1fffffff"),
    ("icnss_qmi_connected", r"icnss_qmi: QMI Server Connected"),
)
NATIVE_KEYS: tuple[str, ...] = (
    "wifi_companion_start.peripheral_manager.enabled",
    "wlan_pd_service_window_trigger.wlfw_start_seen",
    "wlan_pd_service_window_trigger.wlfw_service_request_seen",
    "wlan_pd_service_window_trigger.requested_wlanmdsp",
    "wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_system_info_ok.hit_count",
    "wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_null_peripheral_branch.hit_count",
    "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_service_manager_get_call.hit_count",
    "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_binder_object_present_check.hit_count",
    "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_as_interface_call.hit_count",
    "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_manager_register_tx_call.hit_count",
    "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_success_path.hit_count",
)


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": display_path(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    data["present"] = True
    data["path"] = display_path(path)
    return data


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


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


def find_events(text: str, patterns: tuple[tuple[str, str], ...], dmesg: bool = False) -> dict[str, dict[str, Any]]:
    events: dict[str, dict[str, Any]] = {}
    for line in text.splitlines():
        for name, pattern in patterns:
            if name in events:
                continue
            if re.search(pattern, line, re.IGNORECASE):
                events[name] = {
                    "line": line.strip(),
                    "timestamp": parse_dmesg_time(line) if dmesg else parse_logcat_time(line),
                }
    return events


def parse_native_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in NATIVE_KEYS:
            values[key] = value.strip()
    return values


def as_int(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def hit(values: dict[str, str], key: str) -> bool:
    return as_int(values.get(key)) > 0


def relative_rows(events: dict[str, dict[str, Any]], anchor_name: str) -> list[dict[str, str]]:
    anchor = events.get(anchor_name, {}).get("timestamp")
    rows: list[dict[str, str]] = []
    for name in ("wlfw_start", "per_mgr_register", "per_mgr_vote", "wlfw_service_request", "wlanmdsp_request", "bdf_regdb"):
        timestamp = events.get(name, {}).get("timestamp")
        if isinstance(timestamp, (int, float)) and isinstance(anchor, (int, float)):
            delta = f"{timestamp - anchor:+.3f}s"
            time_text = f"{timestamp:.3f}"
        else:
            delta = "n/a"
            time_text = "n/a"
        rows.append({"event": name, "time": time_text, "delta": delta})
    return rows


def collect() -> dict[str, Any]:
    android_text = read_text(ANDROID_LOGCAT)
    android_dmesg_text = read_text(ANDROID_DMESG)
    native_text = read_text(NATIVE_HELPER_RESULT)
    native_values = parse_native_key_values(native_text)
    android_events = find_events(android_text, ANDROID_PATTERNS)
    android_dmesg_events = find_events(android_dmesg_text, ANDROID_DMESG_PATTERNS, dmesg=True)
    v1760 = load_json(V1760_MANIFEST)
    v1758 = load_json(V1758_MANIFEST)
    native_manifest = load_json(NATIVE_MANIFEST)
    facts = {
        "v1760_request_generation_gap": v1760.get("label") == "request-generation-gap-before-firmware-serving",
        "android_pm_register_seen": "per_mgr_register" in android_events,
        "android_pm_vote_seen": "per_mgr_vote" in android_events,
        "android_wlanmdsp_request_seen": "wlanmdsp_request" in android_events,
        "android_wlan_pd_up_seen": "wlan_pd_up" in android_dmesg_events,
        "native_wlfw_start_seen": hit(native_values, "wlan_pd_service_window_trigger.wlfw_start_seen"),
        "native_wlfw_service_request_seen": hit(
            native_values, "wlan_pd_service_window_trigger.wlfw_service_request_seen"
        ),
        "native_requested_wlanmdsp": hit(native_values, "wlan_pd_service_window_trigger.requested_wlanmdsp"),
        "native_peripheral_manager_enabled": hit(native_values, "wifi_companion_start.peripheral_manager.enabled"),
        "native_pm_system_info_ok": hit(
            native_values, "wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_system_info_ok.hit_count"
        ),
        "native_pm_null_peripheral_branch": hit(
            native_values,
            "wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_null_peripheral_branch.hit_count",
        ),
        "native_periph_service_manager_get_call": hit(
            native_values,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_service_manager_get_call.hit_count",
        ),
        "native_periph_binder_object_present_check": hit(
            native_values,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_binder_object_present_check.hit_count",
        ),
        "native_periph_as_interface_call": hit(
            native_values,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_as_interface_call.hit_count",
        ),
        "native_periph_manager_register_tx_call": hit(
            native_values,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_manager_register_tx_call.hit_count",
        ),
        "native_periph_success_path": hit(
            native_values,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_success_path.hit_count",
        ),
        "v1758_provider_not_composed": v1758.get("label")
        == "compose-provider-positive-vndservice-gate-before-cnss-pm-register",
    }
    return {
        "paths": {
            "android_logcat": display_path(ANDROID_LOGCAT),
            "android_dmesg": display_path(ANDROID_DMESG),
            "native_helper_result": display_path(NATIVE_HELPER_RESULT),
            "native_manifest": display_path(NATIVE_MANIFEST),
            "v1760_manifest": display_path(V1760_MANIFEST),
            "v1758_manifest": display_path(V1758_MANIFEST),
        },
        "android_events": android_events,
        "android_dmesg_events": android_dmesg_events,
        "android_relative_to_wlanmdsp": relative_rows(android_events, "wlanmdsp_request"),
        "native_values": native_values,
        "native_manifest": {
            "decision": native_manifest.get("decision"),
            "pass": native_manifest.get("pass"),
            "reason": native_manifest.get("reason"),
        },
        "facts": facts,
    }


def classify(collected: dict[str, Any]) -> tuple[str, bool, str, str]:
    facts = collected["facts"]
    if not facts["v1760_request_generation_gap"]:
        return (
            "v1761-prerequisite-v1760-request-gap-missing",
            False,
            "V1760 request-generation gap evidence is missing or stale",
            "prerequisite-incomplete",
        )
    android_ok = (
        facts["android_pm_register_seen"]
        and facts["android_pm_vote_seen"]
        and facts["android_wlanmdsp_request_seen"]
    )
    native_wlfw_ok = facts["native_wlfw_start_seen"] and facts["native_wlfw_service_request_seen"]
    native_pm_null = (
        facts["native_pm_system_info_ok"]
        and facts["native_periph_service_manager_get_call"]
        and facts["native_periph_binder_object_present_check"]
        and facts["native_pm_null_peripheral_branch"]
        and not facts["native_periph_as_interface_call"]
        and not facts["native_periph_manager_register_tx_call"]
        and not facts["native_periph_success_path"]
    )
    if android_ok and native_wlfw_ok and native_pm_null and not facts["native_requested_wlanmdsp"]:
        return (
            "v1761-cnss-pm-service-object-gap-before-wlanmdsp-host-pass",
            True,
            "Android-good reaches PM register/vote before wlanmdsp request; native reaches WLFW request but stops at the PeripheralManager null-service-object path and never requests wlanmdsp",
            "pm-service-object-gap-before-wlanmdsp-request",
        )
    return (
        "v1761-autoload-trigger-contract-inconclusive",
        False,
        "required Android PM/request evidence or native PM null-service-object evidence is incomplete",
        "autoload-trigger-contract-inconclusive",
    )


def md_bool(value: bool) -> str:
    return "`true`" if value else "`false`"


def render_report(result: dict[str, Any]) -> str:
    facts = result["facts"]
    rows = result["android_relative_to_wlanmdsp"]
    native_values = result["native_values"]
    lines = [
        "# Native Init V1761 WLAN-PD Autoload Trigger Contract Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1761`",
        "- Type: host-only autoload/request-trigger contract classifier",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Android-good Request Contract",
        "",
        "| Event | Time | Delta to first `wlanmdsp.mbn` request |",
        "| --- | ---: | ---: |",
    ]
    for row in rows:
        lines.append(f"| `{row['event']}` | `{row['time']}` | `{row['delta']}` |")
    lines.extend(
        [
            "",
            "- PM register before request: " + md_bool(facts["android_pm_register_seen"]),
            "- PM vote before request: " + md_bool(facts["android_pm_vote_seen"]),
            "- `wlanmdsp.mbn` request observed: " + md_bool(facts["android_wlanmdsp_request_seen"]),
            "- WLAN-PD UP observed later in dmesg: " + md_bool(facts["android_wlan_pd_up_seen"]),
            "",
            "## Native V1736 Contract",
            "",
            "- WLFW start/request reached: "
            + md_bool(facts["native_wlfw_start_seen"] and facts["native_wlfw_service_request_seen"]),
            "- `wlanmdsp.mbn` requested: " + md_bool(facts["native_requested_wlanmdsp"]),
            "- PeripheralManager actor enabled in V1736 route: "
            + md_bool(facts["native_peripheral_manager_enabled"]),
            "- `pm_init_system_info_ok` hit: " + md_bool(facts["native_pm_system_info_ok"]),
            "- Peripheral service-manager get call hit: "
            + md_bool(facts["native_periph_service_manager_get_call"]),
            "- Peripheral binder-object present check hit: "
            + md_bool(facts["native_periph_binder_object_present_check"]),
            "- PM null PeripheralManager branch hit: "
            + md_bool(facts["native_pm_null_peripheral_branch"]),
            "- `asInterface` / register TX / success path hit: "
            + md_bool(
                facts["native_periph_as_interface_call"]
                or facts["native_periph_manager_register_tx_call"]
                or facts["native_periph_success_path"]
            ),
            "",
            "## Native Uprobe Counts",
            "",
            "| Key | Value |",
            "| --- | ---: |",
        ]
    )
    for key in NATIVE_KEYS:
        if key in native_values:
            lines.append(f"| `{key}` | `{native_values[key]}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- V1760 remains valid: native reaches the WLFW worker but does not generate a `wlanmdsp.mbn` request.",
            "- Android-good shows the missing request is preceded by a successful PeripheralManager register/vote sequence.",
            "- Native V1736 does not merely lack PM log text; it hits the CNSS PM path and then the null-service-object branch before any `asInterface`, register transaction, or success path.",
            "- This classifies the next source/build gate as a service-object visibility/PM-contract gap, not firmware serving, eSoC/RC1, QCACLD registration, Wi-Fi HAL, scan/connect, or credential work.",
            "",
            "## Next",
            "",
            "- V1762 should be source/build-only first: define a bounded helper contract that preserves the V1736 SM route and proves the PeripheralManager service object can become non-null before `wlfw_service_request` observation.",
            "- A later live run must still be one rollbackable discriminator: service object non-null plus PM register/vote observed -> `requested_wlanmdsp=1`, or service object non-null plus PM register/vote observed -> still no request.",
            "- Do not add broad PM/service-window actors, `boot_wlan`, restart-PD, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping in this unit.",
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It reads retained evidence and writes private evidence artifacts. It performs no device contact, flash, reboot, actor start, tracefs write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, or partition write.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    collected = collect()
    decision, pass_ok, reason, label = classify(collected)
    result = {
        "cycle": "V1761",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "label": label,
        "out_dir": display_path(args.out_dir),
        **collected,
    }
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(result))
    write_private_text(args.report_path, render_report(result))
    print(
        json.dumps(
            {
                "decision": decision,
                "pass": pass_ok,
                "label": label,
                "out_dir": display_path(args.out_dir),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
