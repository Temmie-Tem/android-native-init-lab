#!/usr/bin/env python3
"""V839 host-only classifier after V838 ruled out listener timing.

V838 proved the native lower-only listener was registered before service74 and
held through service74+5s, but WLAN-PD stayed UNINIT.  This classifier compares
that result with the Android positive-control and the provider-first CNSS retry
evidence to select the next narrow gate toward native Wi-Fi bring-up.
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
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v839-post-v838-trigger-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v839-post-v838-trigger-classifier.txt")
DEFAULT_V833_HANDOFF_MANIFEST = Path("tmp/wifi/v833-android-servnotif-handoff-live-20260525-125136/manifest.json")
DEFAULT_V833_POSITIVE_MANIFEST = Path(
    "tmp/wifi/v833-android-servnotif-handoff-live-20260525-125136/"
    "v833-android-servnotif-positive-control-run/manifest.json"
)
DEFAULT_V833_HELPER = Path(
    "tmp/wifi/v833-android-servnotif-handoff-live-20260525-125136/"
    "v833-android-servnotif-positive-control-run/android/commands/servnotif-helper.txt"
)
DEFAULT_V833_DMESG = Path(
    "tmp/wifi/v833-android-servnotif-handoff-live-20260525-125136/"
    "v833-android-servnotif-positive-control-run/android/commands/readiness-dmesg-tail.txt"
)
DEFAULT_V700_MANIFEST = Path("tmp/wifi/v700-provider-first-cnss-orchestrated-run/manifest.json")
DEFAULT_V838_MANIFEST = Path("tmp/wifi/v838-concurrent-servnotif-listener-live-retry2-20260525-143057/manifest.json")
DEFAULT_V838_DMESG = Path("tmp/wifi/v838-concurrent-servnotif-listener-live-retry2-20260525-143057/native/dmesg-delta.txt")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
TS_RE = re.compile(r"\[\s*(?P<ts>\d+\.\d+)\]")
KV_RE = re.compile(r"^(?P<key>[^=\s][^=]*?)=(?P<value>.*)$")

MARKERS: dict[str, re.Pattern[str]] = {
    "service180": re.compile(r"service-notifier: .* 180 service", re.I),
    "service74": re.compile(r"service-notifier: .* 74 service", re.I),
    "cnss_diag_netlink": re.compile(r"netlink_create\(694\).*comm:\s*cnss_diag", re.I),
    "cnss_daemon_netlink": re.compile(r"netlink_create\(694\).*comm:\s*cnss-daemon", re.I),
    "cnss_cld80211": re.compile(r"cnss-daemon.*ctrl_getfamily.*cld80211|ctrl_getfamily.*cld80211.*cnss-daemon", re.I),
    "cnss_binder_fail": re.compile(r"cnss-daemon.*binder:.*(?:transaction failed|ioctl).*?-22", re.I),
    "wlfw_start": re.compile(r"cnss-daemon wlfw_start: Starting", re.I),
    "wlfw_service_request": re.compile(r"cnss-daemon wlfw_service_request", re.I),
    "wlan_pd_indication": re.compile(r"service-notifier: root_service_service_ind_cb: .*wlan_pd", re.I),
    "wlan_pd_ack": re.compile(r"service-notifier: send_ind_ack: .*wlan_pd", re.I),
    "icnss_qmi_connected": re.compile(r"icnss_qmi: QMI Server Connected", re.I),
    "bdf_regdb": re.compile(r"BDF file\s*:\s*regdb\.bin", re.I),
    "bdf_bdwlan": re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I),
    "wlan_fw_ready": re.compile(r"icnss: WLAN FW is ready", re.I),
    "wlan0": re.compile(r"\bwlan0\b", re.I),
    "kernel_warning": re.compile(r"WARNING: CPU:|Call trace:", re.I),
}


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v833-handoff-manifest", type=Path, default=DEFAULT_V833_HANDOFF_MANIFEST)
    parser.add_argument("--v833-positive-manifest", type=Path, default=DEFAULT_V833_POSITIVE_MANIFEST)
    parser.add_argument("--v833-helper", type=Path, default=DEFAULT_V833_HELPER)
    parser.add_argument("--v833-dmesg", type=Path, default=DEFAULT_V833_DMESG)
    parser.add_argument("--v700-manifest", type=Path, default=DEFAULT_V700_MANIFEST)
    parser.add_argument("--v838-manifest", type=Path, default=DEFAULT_V838_MANIFEST)
    parser.add_argument("--v838-dmesg", type=Path, default=DEFAULT_V838_DMESG)
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
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(repo_path(path)), "error": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(repo_path(path)), "error": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(repo_path(path)))
    return data


def strip_line(line: str) -> str:
    return ANSI_RE.sub("", line).strip()


def line_ts(line: str) -> float | None:
    match = TS_RE.search(line)
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = strip_line(raw)
        match = KV_RE.match(line)
        if match:
            values[match.group("key").strip()] = match.group("value").strip()
    return values


def parse_timeline(text: str) -> dict[str, Any]:
    events: dict[str, list[dict[str, Any]]] = {name: [] for name in MARKERS}
    for raw in text.splitlines():
        line = strip_line(raw)
        if not line:
            continue
        ts = line_ts(line)
        for name, pattern in MARKERS.items():
            if pattern.search(line):
                events[name].append({"ts": ts, "line": line[:260]})
    return {
        "counts": {name: len(rows) for name, rows in events.items()},
        "first_ts": {name: rows[0]["ts"] for name, rows in events.items() if rows and rows[0]["ts"] is not None},
        "first_lines": {name: rows[0]["line"] for name, rows in events.items() if rows},
    }


def delta_ms(timeline: dict[str, Any], start: str, end: str) -> float | None:
    first_ts = timeline.get("first_ts") if isinstance(timeline.get("first_ts"), dict) else {}
    if start not in first_ts or end not in first_ts:
        return None
    return round((float(first_ts[end]) - float(first_ts[start])) * 1000.0, 3)


def count(timeline: dict[str, Any], name: str) -> int:
    counts = timeline.get("counts") if isinstance(timeline.get("counts"), dict) else {}
    try:
        return int(counts.get(name, 0))
    except (TypeError, ValueError):
        return 0


def int_value(value: Any) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def nested(data: dict[str, Any], *keys: str) -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def android_positive(args: argparse.Namespace) -> dict[str, Any]:
    handoff = load_json(args.v833_handoff_manifest)
    positive = load_json(args.v833_positive_manifest)
    helper_keys = parse_key_values(read_text(args.v833_helper))
    timeline = parse_timeline(read_text(args.v833_dmesg))
    raw_state = helper_keys.get("servnotif.response_curr_state", "")
    return {
        "handoff_manifest": {"path": str(repo_path(args.v833_handoff_manifest)), "decision": handoff.get("decision"), "pass": handoff.get("pass")},
        "positive_manifest": {"path": str(repo_path(args.v833_positive_manifest)), "decision": positive.get("decision"), "pass": positive.get("pass")},
        "listener": {
            "endpoint_found": int_value(helper_keys.get("servnotif.endpoint.found")),
            "response_success": int_value(helper_keys.get("servnotif.response_success")),
            "response_curr_state": raw_state,
            "response_curr_state_name": helper_keys.get("servnotif.response_curr_state_name", ""),
            "raw_state_up": raw_state.lower() == "0x1fffffff",
            "indication_seen": int_value(helper_keys.get("servnotif.indication_seen")),
        },
        "timeline": timeline,
        "deltas_ms": {
            "service74_to_wlfw_start": delta_ms(timeline, "service74", "wlfw_start"),
            "service74_to_wlan_pd": delta_ms(timeline, "service74", "wlan_pd_indication"),
            "wlfw_start_to_wlan_pd": delta_ms(timeline, "wlfw_start", "wlan_pd_indication"),
            "wlfw_start_to_icnss_qmi": delta_ms(timeline, "wlfw_start", "icnss_qmi_connected"),
            "wlfw_start_to_bdf_regdb": delta_ms(timeline, "wlfw_start", "bdf_regdb"),
            "wlfw_start_to_wlan0": delta_ms(timeline, "wlfw_start", "wlan0"),
        },
    }


def native_v838(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v838_manifest)
    timeline = parse_timeline(read_text(args.v838_dmesg))
    service_notifier = nested(manifest, "lower_concurrent", "service_notifier") or {}
    timing = nested(manifest, "lower_concurrent", "timing") or {}
    safety = manifest.get("safety") if isinstance(manifest.get("safety"), dict) else {}
    return {
        "manifest": {"path": str(repo_path(args.v838_manifest)), "decision": manifest.get("decision"), "pass": manifest.get("pass")},
        "listener": {
            "endpoint_found": int_value(service_notifier.get("endpoint_found")),
            "response_success": int_value(service_notifier.get("response_success")),
            "response_curr_state": service_notifier.get("response_curr_state", ""),
            "response_curr_state_name": service_notifier.get("response_curr_state_name", ""),
            "indication_seen": int_value(service_notifier.get("indication_seen")),
            "listener_open_at_service74": timing.get("listener_open_at_service74"),
            "held_5s_after_service74": timing.get("held_5s_after_service74"),
            "send_before_to_service74_ms": timing.get("send_before_to_service74_ms"),
            "close_after_service74_ms": timing.get("close_after_service74_ms"),
        },
        "timeline": timeline,
        "safety": safety,
        "deltas_ms": {
            "service74_to_cnss_daemon_netlink": delta_ms(timeline, "service74", "cnss_daemon_netlink"),
            "cnss_daemon_netlink_to_wlfw_start": delta_ms(timeline, "cnss_daemon_netlink", "wlfw_start"),
            "cnss_daemon_netlink_to_binder_fail": delta_ms(timeline, "cnss_daemon_netlink", "cnss_binder_fail"),
        },
    }


def provider_v700(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v700_manifest)
    arm = manifest.get("arm_v700") if isinstance(manifest.get("arm_v700"), dict) else {}
    counts = arm.get("counts") if isinstance(arm.get("counts"), dict) else {}
    peripheral = arm.get("peripheral") if isinstance(arm.get("peripheral"), dict) else {}
    return {
        "manifest": {"path": str(repo_path(args.v700_manifest)), "decision": manifest.get("decision"), "pass": manifest.get("pass")},
        "arm_decision": arm.get("decision", ""),
        "arm_pass": arm.get("pass"),
        "counts": {key: int_value(counts.get(key)) for key in (
            "service_notifier_180",
            "service_notifier_74",
            "cnss_daemon_netlink",
            "cnss_daemon_cld80211",
            "cnss_binder_transaction_failed",
            "binder_transaction_failed",
            "wlfw_start",
            "wlan_pd",
            "qmi_server_connected",
            "bdf_regdb",
            "bdf_bdwlan",
            "wlan0",
        )},
        "provider": {
            "initial_cnss_suppressed": bool_value(arm.get("initial_cnss_suppressed")),
            "query_exact_match": bool_value(arm.get("query_exact_match")),
            "cnss_retry_started": bool_value(arm.get("cnss_retry_started")),
            "order": peripheral.get("order", ""),
            "peripheral_manager_enabled": peripheral.get("peripheral_manager_enabled", ""),
            "all_postflight_safe": peripheral.get("all_postflight_safe", ""),
        },
    }


def candidate(name: str, classification: str, reason: str, next_step: str) -> dict[str, str]:
    return {"candidate": name, "classification": classification, "reason": reason, "next_step": next_step}


def classify(args: argparse.Namespace) -> dict[str, Any]:
    android = android_positive(args)
    native = native_v838(args)
    provider = provider_v700(args)

    android_reaches_up = (
        android["listener"]["raw_state_up"]
        and count(android["timeline"], "wlan_pd_indication") > 0
        and count(android["timeline"], "wlfw_start") > 0
        and count(android["timeline"], "wlan0") > 0
    )
    native_timing_ruled_out = (
        native["manifest"]["decision"] == "v838-held-through-post74-no-indication"
        and native["listener"]["listener_open_at_service74"] is True
        and native["listener"]["held_5s_after_service74"] is True
        and native["listener"]["response_curr_state_name"] == "uninit"
        and native["listener"]["indication_seen"] == 0
    )
    provider_first_gap = (
        provider["manifest"]["decision"] == "v700-provider-first-cnss-gap-persists"
        and provider["provider"]["query_exact_match"]
        and provider["provider"]["cnss_retry_started"]
        and provider["counts"]["cnss_binder_transaction_failed"] == 0
        and provider["counts"]["binder_transaction_failed"] == 0
        and provider["counts"]["wlfw_start"] == 0
        and provider["counts"]["wlan_pd"] == 0
    )
    native_cnss_without_wlfw = (
        count(native["timeline"], "cnss_daemon_netlink") > 0
        and count(native["timeline"], "wlfw_start") == 0
        and count(native["timeline"], "wlan_pd_indication") == 0
    )

    return {
        "android_positive": android,
        "native_v838": native,
        "provider_v700": provider,
        "derived": {
            "android_reaches_wlanpd_wlfw_wlan0": android_reaches_up,
            "native_listener_timing_ruled_out": native_timing_ruled_out,
            "provider_first_retry_gap_without_binder_failure": provider_first_gap,
            "native_cnss_netlink_without_wlfw": native_cnss_without_wlfw,
            "selected_next_gate": "v840-provider-first-prearmed-servnotif-listener",
        },
        "candidate_matrix": [
            candidate(
                "repeat V838 lower-only listener",
                "reject",
                "V838 already registered before service74 and held through service74+5s with no indication",
                "do not rerun without adding a missing trigger surface",
            ),
            candidate(
                "repeat V700 provider-first CNSS retry unchanged",
                "reject",
                "V700 removed the Binder failure and started provider-first CNSS retry, but did not include a prearmed WLAN-PD listener",
                "combine provider-first retry with the V838 listener instrumentation",
            ),
            candidate(
                "Wi-Fi HAL / scan / connect / DHCP / external ping",
                "blocked",
                "native still lacks WLAN-PD UP, WLFW, BDF, and wlan0",
                "keep final bring-up blocked until lower publication moves",
            ),
            candidate(
                "direct esoc0, wlan.ko, sysfs writes, or custom kernel flash",
                "blocked",
                "these paths are either unsafe or already paused by prior postmortems",
                "stay on bounded userspace/runtime observation first",
            ),
            candidate(
                "provider-first CNSS retry with prearmed service-notifier listener",
                "select-next",
                "this is the smallest gate that combines Android's provider/runtime surface with V838's proven listener timing",
                "V840 should run provider-first start-only below Wi-Fi HAL/scan/connect while keeping the WLAN-PD listener armed",
            ),
        ],
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(analysis: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    android = analysis["android_positive"]
    native = analysis["native_v838"]
    provider = analysis["provider_v700"]
    derived = analysis["derived"]
    add_check(
        checks,
        "android-positive-control",
        "pass" if derived["android_reaches_wlanpd_wlfw_wlan0"] else "blocked",
        "blocker",
        json.dumps({"handoff": android["handoff_manifest"], "listener": android["listener"], "counts": android["timeline"]["counts"]}, sort_keys=True),
        "refresh Android positive-control before selecting a native trigger gate",
    )
    add_check(
        checks,
        "v838-timing-closed",
        "pass" if derived["native_listener_timing_ruled_out"] else "blocked",
        "blocker",
        json.dumps({"manifest": native["manifest"], "listener": native["listener"]}, sort_keys=True),
        "complete V838 before moving past listener timing",
    )
    add_check(
        checks,
        "v700-provider-first-gap",
        "pass" if derived["provider_first_retry_gap_without_binder_failure"] else "blocked",
        "blocker",
        json.dumps({"manifest": provider["manifest"], "counts": provider["counts"], "provider": provider["provider"]}, sort_keys=True),
        "refresh provider-first CNSS retry evidence before combining gates",
    )
    add_check(
        checks,
        "host-only-scope",
        "pass",
        "blocker",
        "V839 reads existing evidence only",
        "keep V839 non-mutating",
    )
    return checks


def blocked(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v839-post-v838-trigger-classifier-plan-ready",
            True,
            "plan-only; no device command, daemon start, Wi-Fi action, credential, route, ping, or flash executed",
            "run V839 host-only classifier",
        )
    blockers = blocked(checks)
    if blockers:
        return (
            "v839-post-v838-trigger-classifier-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "refresh prerequisite evidence before selecting V840",
        )
    return (
        "v839-provider-first-prearmed-listener-selected",
        True,
        "V838 rules out listener timing, Android proves the listener can observe WLAN-PD UP, and V700 proves provider-first CNSS retry runs without Binder failure but lacked the prearmed listener",
        "V840 should combine provider-first CNSS retry with the prearmed WLAN-PD listener, still below Wi-Fi HAL/scan/connect/DHCP/external ping",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    return "\n".join([
        "# V839 Post-V838 Trigger Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Derived",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in analysis["derived"].items()]),
        "",
        "## Android Timing",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in analysis["android_positive"]["deltas_ms"].items()]),
        "",
        "## Native V838 Timing",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in analysis["native_v838"]["deltas_ms"].items()]),
        "",
        "## Candidate Matrix",
        "",
        markdown_table(["candidate", "classification", "reason", "next"], [
            [row["candidate"], row["classification"], row["reason"], row["next_step"]]
            for row in analysis["candidate_matrix"]
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = classify(args)
    checks = build_checks(analysis)
    decision, passed, reason, next_step = decide(args.command, checks)
    manifest: dict[str, Any] = {
        "cycle": "v839",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "qmi_payload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
