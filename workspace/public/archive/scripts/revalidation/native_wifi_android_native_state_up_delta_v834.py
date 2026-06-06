#!/usr/bin/env python3
"""V834 host-only Android/native service-notifier state-up delta classifier.

V833 proved that the same `msm/modem/wlan_pd` service-notifier listener request
returns `UP` on Android while V830/V831 return `UNINIT` in native init.  This
classifier turns that delta into the next native gate without contacting the
device or repeating already-closed service-locator/listener timing work.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v834-android-native-state-up-delta")
LATEST_POINTER = Path("tmp/wifi/latest-v834-android-native-state-up-delta.txt")

INPUTS = {
    "v775": Path("tmp/wifi/v775-boot-incompat-postmortem/manifest.json"),
    "v792": Path("tmp/wifi/v792-known-asoc-warning-cnss-wlfw/manifest.json"),
    "v817": Path("tmp/wifi/v817-in-window-sysmon-sampler/manifest.json"),
    "v829": Path("tmp/wifi/v829-servloc-domain-list-probe-retry-20260525-113735/manifest.json"),
    "v830": Path("tmp/wifi/v830-service-notifier-listener-run-20260525-115840/manifest.json"),
    "v831": Path("tmp/wifi/v831-service-notifier-early-listener-run-20260525-121658/manifest.json"),
    "v833_handoff": Path("tmp/wifi/v833-android-servnotif-handoff-live-20260525-125136/manifest.json"),
    "v833_collector": Path(
        "tmp/wifi/v833-android-servnotif-handoff-live-20260525-125136/"
        "v833-android-servnotif-positive-control-run/manifest.json"
    ),
}

REPORTS = {
    "v775": Path("docs/reports/NATIVE_INIT_V775_BOOT_INCOMPAT_POSTMORTEM_2026-05-25.md"),
    "v792": Path("docs/reports/NATIVE_INIT_V792_KNOWN_ASOC_WARNING_CNSS_WLFW_2026-05-25.md"),
    "v817": Path("docs/reports/NATIVE_INIT_V817_IN_WINDOW_SYSMON_SAMPLER_2026-05-25.md"),
    "v829": Path("docs/reports/NATIVE_INIT_V829_SERVLOC_DOMAIN_LIST_PROBE_2026-05-25.md"),
    "v830": Path("docs/reports/NATIVE_INIT_V830_SERVICE_NOTIFIER_LISTENER_PROBE_2026-05-25.md"),
    "v831": Path("docs/reports/NATIVE_INIT_V831_EARLY_SERVICE_NOTIFIER_LISTENER_2026-05-25.md"),
    "v833": Path("docs/reports/NATIVE_INIT_V833_ANDROID_SERVNOTIF_POSITIVE_CONTROL_LIVE_2026-05-25.md"),
}

EXPECTED_DECISIONS = {
    "v775": "v775-non-dtb-custom-kernel-incompat-classified",
    "v792": "v792-known-warning-cnss-no-wlfw-classified",
    "v817": "v817-in-window-mdm3-service-gap-confirmed",
    "v829": "v829-servloc-domain-list-response-success",
    "v830": "v830-service-notifier-listener-state-not-up",
    "v831": "v831-service-notifier-early-listener-state-not-up",
    "v833_handoff": "v833-handoff-pass",
}

STATE_NAMES = {
    0x0FFFFFFF: "down",
    0x1FFFFFFF: "up",
    0x2FFFFFFF: "early-down",
    0x7FFFFFFF: "uninit",
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
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "error": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "error": "not-json-object"}
    data["exists"] = True
    data["path"] = str(resolved)
    return data


def int_value(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(str(value), 0)
    except ValueError:
        return default


def nested(manifest: dict[str, Any], *keys: str) -> Any:
    value: Any = manifest
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def canonical_state(raw_state: Any, helper_name: Any = "") -> str:
    raw_int = int_value(raw_state, -1)
    if raw_int in STATE_NAMES:
        return STATE_NAMES[raw_int]
    name = str(helper_name or "")
    return name if name else "unknown"


def input_summary(inputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "path": item.get("path"),
            "exists": item.get("exists", False),
            "decision": item.get("decision", ""),
            "pass": bool(item.get("pass")),
            "reason": item.get("reason", ""),
            "next_step": item.get("next_step", ""),
        }
        for name, item in inputs.items()
    }


def report_summary() -> dict[str, dict[str, Any]]:
    return {
        name: {
            "path": str(repo_path(path)),
            "exists": repo_path(path).exists(),
        }
        for name, path in REPORTS.items()
    }


def get_v829_domain(v829: dict[str, Any]) -> dict[str, Any]:
    servloc = nested(v829, "live", "servloc")
    if not isinstance(servloc, dict):
        servloc = {}
    domains = servloc.get("domains") if isinstance(servloc.get("domains"), list) else []
    first = domains[0] if domains and isinstance(domains[0], dict) else {}
    return {
        "qmi_result": int_value(servloc.get("qmi_result"), -1),
        "qmi_error": int_value(servloc.get("qmi_error"), -1),
        "domain_count": int_value(servloc.get("domain_count")),
        "total_domains": int_value(servloc.get("total_domains")),
        "wlan_like_domains": int_value(servloc.get("wlan_like_domains")),
        "name": first.get("name", ""),
        "instance_id": int_value(first.get("instance_id")),
    }


def get_native_listener(manifest: dict[str, Any]) -> dict[str, Any]:
    listener = nested(manifest, "live", "service_notifier")
    if not isinstance(listener, dict):
        listener = {}
    state = listener.get("response_curr_state", "")
    state_name = canonical_state(state, listener.get("response_curr_state_name", ""))
    return {
        "endpoint_found": int_value(listener.get("endpoint_found")),
        "endpoint_node": int_value(listener.get("endpoint_node"), -1),
        "endpoint_port": int_value(listener.get("endpoint_port"), -1),
        "service": int_value(listener.get("service")),
        "instance": int_value(listener.get("instance")),
        "service_name": listener.get("service_name", ""),
        "response_success": int_value(listener.get("response_success")),
        "qmi_result": int_value(listener.get("register_response_qmi_result"), -1),
        "qmi_error": int_value(listener.get("register_response_qmi_error"), -1),
        "raw_state": state,
        "state": state_name,
        "indication_seen": int_value(listener.get("indication_seen")),
    }


def get_android_listener(v833_collector: dict[str, Any]) -> dict[str, Any]:
    helper = nested(v833_collector, "android", "helper_output")
    if not isinstance(helper, dict):
        helper = {}
    raw_state = helper.get("servnotif.register_response.curr_state", "")
    helper_state = helper.get("servnotif.register_response.curr_state_name", "")
    state = canonical_state(raw_state, helper_state)
    return {
        "endpoint_found": int_value(helper.get("servnotif.endpoint.found")),
        "endpoint_node": int_value(helper.get("servnotif.endpoint.node"), -1),
        "endpoint_port": int_value(helper.get("servnotif.endpoint.port"), -1),
        "service": int_value(helper.get("servnotif.probe.service")),
        "instance": int_value(helper.get("servnotif.probe.instance")),
        "service_name": helper.get("servnotif.probe.service_name", ""),
        "response_success": int_value(helper.get("servnotif.response_success")),
        "qmi_result": int_value(helper.get("servnotif.register_response.qmi_result"), -1),
        "qmi_error": int_value(helper.get("servnotif.register_response.qmi_error"), -1),
        "raw_state": raw_state,
        "state": state,
        "helper_state_name": helper_state,
        "indication_seen": int_value(helper.get("servnotif.indication_seen")),
    }


def get_v817_lower_window(v817: dict[str, Any]) -> dict[str, Any]:
    live = v817.get("live") if isinstance(v817.get("live"), dict) else {}
    markers = live.get("markers") if isinstance(live.get("markers"), dict) else {}
    return {
        "mss_before": live.get("mss_before", ""),
        "mss_after_holder": live.get("mss_after_holder", ""),
        "mss_after_companion": live.get("mss_after_companion", ""),
        "mdm3_before": live.get("mdm3_before", ""),
        "mdm3_after_holder": live.get("mdm3_after_holder", ""),
        "mdm3_after_companion": live.get("mdm3_after_companion", ""),
        "qrtr_rx": int_value(markers.get("qrtr_rx")),
        "qrtr_tx": int_value(markers.get("qrtr_tx")),
        "sysmon_qmi": int_value(markers.get("sysmon_qmi")),
        "service_notifier": int_value(markers.get("service_notifier")),
        "wlan_pd": int_value(markers.get("wlan_pd")),
        "wlfw": int_value(markers.get("wlfw")),
        "wlan0": int_value(markers.get("wlan0")),
    }


def get_v792_window(v792: dict[str, Any]) -> dict[str, Any]:
    guard = v792.get("known_asoc_warning_guard") if isinstance(v792.get("known_asoc_warning_guard"), dict) else {}
    events = guard.get("events") if isinstance(guard.get("events"), dict) else {}
    lower = v792.get("lower_readback") if isinstance(v792.get("lower_readback"), dict) else {}
    lower_live = lower.get("live") if isinstance(lower.get("live"), dict) else {}
    markers = lower_live.get("markers") if isinstance(lower_live.get("markers"), dict) else {}
    return {
        "exact_known_asoc_warning": bool(guard.get("exact_known_asoc_warning")),
        "kernel_warning": int_value(guard.get("kernel_warning")),
        "service180": int_value(nested(events, "service180", "count")),
        "service74": int_value(nested(events, "service74", "count")),
        "sysmon_modem": int_value(nested(events, "sysmon_modem", "count")),
        "sysmon_adsp": int_value(nested(events, "sysmon_adsp", "count")),
        "sysmon_cdsp": int_value(nested(events, "sysmon_cdsp", "count")),
        "sysmon_slpi": int_value(nested(events, "sysmon_slpi", "count")),
        "wlfw": int_value(nested(events, "wlfw", "count")),
        "wlan_pd": int_value(nested(events, "wlan_pd", "count")),
        "wlan0": int_value(nested(events, "wlan0", "count")),
        "lower_qrtr_rx": int_value(markers.get("qrtr_rx")),
        "lower_qrtr_tx": int_value(markers.get("qrtr_tx")),
        "lower_sysmon_qmi": int_value(markers.get("sysmon_qmi")),
        "lower_service_notifier": int_value(markers.get("service_notifier")),
        "lower_wlfw": int_value(markers.get("wlfw")),
        "lower_wlan0": int_value(markers.get("wlan0")),
    }


def candidate(label: str, classification: str, reason: str, next_step: str) -> dict[str, str]:
    return {
        "candidate": label,
        "classification": classification,
        "reason": reason,
        "next_step": next_step,
    }


def classify() -> dict[str, Any]:
    inputs = {name: load_json(path) for name, path in INPUTS.items()}
    v829_domain = get_v829_domain(inputs["v829"])
    v830_listener = get_native_listener(inputs["v830"])
    v831_listener = get_native_listener(inputs["v831"])
    android_listener = get_android_listener(inputs["v833_collector"])
    v817_window = get_v817_lower_window(inputs["v817"])
    v792_window = get_v792_window(inputs["v792"])

    pd_mapper_domain_ready = (
        v829_domain["qmi_result"] == 0
        and v829_domain["qmi_error"] == 0
        and v829_domain["name"] == "msm/modem/wlan_pd"
        and v829_domain["instance_id"] == 180
    )
    native_uninit = (
        v830_listener["response_success"] == 1
        and v830_listener["state"] == "uninit"
        and v831_listener["response_success"] == 1
        and v831_listener["state"] == "uninit"
    )
    android_state_up = (
        android_listener["response_success"] == 1
        and android_listener["qmi_result"] == 0
        and android_listener["qmi_error"] == 0
        and android_listener["state"] == "up"
    )
    v817_lower_gap = (
        v817_window["mss_after_companion"] == "ONLINE"
        and v817_window["mdm3_after_companion"] == "OFFLINING"
        and v817_window["wlfw"] == 0
        and v817_window["wlan0"] == 0
    )
    v792_replay_window_known = (
        inputs["v792"].get("decision") == EXPECTED_DECISIONS["v792"]
        and bool(inputs["v792"].get("pass"))
        and v792_window["service180"] > 0
        and v792_window["service74"] > 0
        and v792_window["exact_known_asoc_warning"]
        and v792_window["wlfw"] == 0
        and v792_window["wlan0"] == 0
    )

    candidate_matrix = [
        candidate(
            "repeat V829 service-locator GET_DOMAIN_LIST",
            "reject",
            "V829 already returned msm/modem/wlan_pd instance 180",
            "use V829 as a prerequisite, not a repeated live probe",
        ),
        candidate(
            "repeat V830/V831 native listener timing",
            "reject",
            "both native windows registered successfully and returned UNINIT",
            "change the lower-state precondition before another identical listener query",
        ),
        candidate(
            "service-manager, Wi-Fi HAL, scan/connect, DHCP, external ping",
            "blocked",
            "native still lacks WLAN-PD state-up, WLFW service69, BDF, wiphy, and wlan0",
            "do not cross into final Wi-Fi bring-up before lower state advances",
        ),
        candidate(
            "custom OSRC diagnostic kernel flash",
            "paused",
            "V775 classified custom-kernel boot incompatibility after V771/V774 failures",
            "resume only after a host-only compatibility contract exists",
        ),
        candidate(
            "known-ASoC-warning clean-DSP/CNSS state listener replay",
            "select-next",
            "V792 is the best current native lower window with service180/service74 evidence; V833 proves the listener model is valid",
            "V835 should query the corrected service-notifier listener inside that bounded window and then reboot-clean",
        ),
    ]

    return {
        "inputs": input_summary(inputs),
        "reports": report_summary(),
        "signals": {
            "v829_domain": v829_domain,
            "v830_native_listener": v830_listener,
            "v831_native_listener": v831_listener,
            "v833_android_listener": android_listener,
            "v817_lower_window": v817_window,
            "v792_known_warning_window": v792_window,
        },
        "derived": {
            "pd_mapper_domain_ready": pd_mapper_domain_ready,
            "native_listener_uninit_reproduced": native_uninit,
            "android_listener_state_up_confirmed": android_state_up,
            "listener_payload_model_valid": android_state_up and native_uninit,
            "v817_lower_gap_confirmed": v817_lower_gap,
            "v792_replay_window_known": v792_replay_window_known,
            "next_gate": "v835-known-asoc-warning-clean-dsp-cnss-servnotif-state-replay",
        },
        "candidate_matrix": candidate_matrix,
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(analysis: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    inputs = analysis["inputs"]
    for name, expected in EXPECTED_DECISIONS.items():
        item = inputs[name]
        add_check(
            checks,
            f"{name}-input",
            "pass" if item.get("exists") and item.get("pass") and item.get("decision") == expected else "blocked",
            "blocker",
            f"decision={item.get('decision')} pass={item.get('pass')} expected={expected}",
            f"refresh {name} evidence before using V834 route selection",
        )

    collector = inputs["v833_collector"]
    add_check(
        checks,
        "v833-collector-input",
        "pass" if collector.get("exists") and collector.get("pass") else "blocked",
        "blocker",
        f"decision={collector.get('decision')} pass={collector.get('pass')}",
        "refresh V833 Android collector before using positive-control state",
    )

    derived = analysis["derived"]
    add_check(
        checks,
        "pd-mapper-domain-ready",
        "pass" if derived["pd_mapper_domain_ready"] else "blocked",
        "blocker",
        str(analysis["signals"]["v829_domain"]),
        "complete V829 before comparing listener state",
    )
    add_check(
        checks,
        "native-uninit-reproduced",
        "pass" if derived["native_listener_uninit_reproduced"] else "blocked",
        "blocker",
        f"v830={analysis['signals']['v830_native_listener']} v831={analysis['signals']['v831_native_listener']}",
        "refresh native listener evidence before selecting a new lower gate",
    )
    add_check(
        checks,
        "android-up-confirmed",
        "pass" if derived["android_listener_state_up_confirmed"] else "blocked",
        "blocker",
        str(analysis["signals"]["v833_android_listener"]),
        "complete Android positive control before treating native UNINIT as real",
    )
    add_check(
        checks,
        "v792-replay-window-known",
        "pass" if derived["v792_replay_window_known"] else "blocked",
        "blocker",
        str(analysis["signals"]["v792_known_warning_window"]),
        "refresh known-ASoC-warning lower replay before selecting V835",
    )
    add_check(
        checks,
        "host-only-boundary",
        "pass",
        "blocker",
        "V834 reads local manifests/reports only",
        "keep V834 host-only",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v834-android-native-state-up-delta-plan-ready",
            True,
            "plan-only; no device command, QMI payload, daemon, Wi-Fi action, or flash executed",
            "run V834 host-only classifier",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v834-android-native-state-up-delta-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "refresh prerequisite evidence before selecting the next native lower-state gate",
        )
    return (
        "v834-known-warning-state-listener-replay-selected",
        True,
        "Android state-up positive control is valid, native basic windows stay UNINIT, and V792 is the best bounded native service180/service74 window",
        "V835 should run a bounded corrected service-notifier listener replay inside the known-ASoC-warning clean-DSP/CNSS window",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    return "\n".join([
        "# V834 Android/Native State-Up Delta Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- qmi_payload_executed: `{manifest['qmi_payload_executed']}`",
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
        "## Derived Signals",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in analysis["derived"].items()]),
        "",
        "## Candidate Matrix",
        "",
        markdown_table(["candidate", "classification", "reason", "next"], [
            [row["candidate"], row["classification"], row["reason"], row["next_step"]]
            for row in analysis["candidate_matrix"]
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = classify()
    checks = build_checks(analysis)
    decision, ok, reason, next_step = decide(args.command, checks)
    manifest: dict[str, Any] = {
        "cycle": "v834",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
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
        "esoc0_open_executed": False,
        "subsystem_write_executed": False,
        "module_load_unload_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path(Path(".")))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"qmi_payload_executed: {manifest['qmi_payload_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
