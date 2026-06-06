#!/usr/bin/env python3
"""V836 host-only classifier after V835 WLAN-PD state remained UNINIT.

V835 proved that the best known native lower window still reports
`msm/modem/wlan_pd` as `UNINIT`, while Android reaches `UP` and then WLFW/BDF.
This classifier compares that delta against existing Android/native evidence
and selects the next non-repeating gate.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v836-post-v835-state-up-contract-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v836-post-v835-state-up-contract-classifier.txt")

INPUTS = {
    "v649": Path("tmp/wifi/v649-final-live-replay-classifier/manifest.json"),
    "v650": Path("tmp/wifi/v650-post-warning-continuation/manifest.json"),
    "v651": Path("tmp/wifi/v651-cnss-wlfw-continuation/manifest.json"),
    "v696": Path("tmp/wifi/v696-post-provider-retry-blocker-classifier-final-check/manifest.json"),
    "v701": Path("tmp/wifi/v701-pre-wlfw-trigger-classifier/manifest.json"),
    "v811": Path("tmp/wifi/v811-wlfw-publication-precondition-classifier/manifest.json"),
    "v835": Path("tmp/wifi/v835-known-asoc-warning-servnotif-replay-live-20260525-131408/manifest.json"),
}

REPORTS = {
    "v649": Path("docs/reports/NATIVE_INIT_V649_ANDROID_FULL_AUDIO_WIFI_RECAPTURE_LIVE_2026-05-23.md"),
    "v650": Path("docs/reports/NATIVE_INIT_V650_POST_WARNING_CONTINUATION_2026-05-23.md"),
    "v651": Path("docs/reports/NATIVE_INIT_V651_CNSS_WLFW_CONTINUATION_2026-05-23.md"),
    "v696": Path("docs/reports/NATIVE_INIT_V696_POST_PROVIDER_RETRY_BLOCKER_CLASSIFIER_2026-05-24.md"),
    "v701": Path("docs/reports/NATIVE_INIT_V701_PRE_WLFW_TRIGGER_CLASSIFIER_2026-05-24.md"),
    "v811": Path("docs/reports/NATIVE_INIT_V811_WLFW_PUBLICATION_PRECONDITION_CLASSIFIER_2026-05-25.md"),
    "v835": Path("docs/reports/NATIVE_INIT_V835_KNOWN_ASOC_WARNING_SERVNOTIF_REPLAY_LIVE_2026-05-25.md"),
}

EXPECTED_DECISIONS = {
    "v649": "v649-android-audio-pm-qos-warning-reference-captured",
    "v650": "v650-post-warning-wlfw-continuation-gap-classified",
    "v651": "v651-cnss-daemon-binder-blocks-wlfw-continuation",
    "v696": "v696-cnss-binder-continuation-remains-primary",
    "v701": "v701-pre-wlfw-kernel-progression-gap-classified",
    "v811": "v811-wlfw-publication-precondition-mdm3-wlanpd-gap-selected",
    "v835": "v835-native-servnotif-still-uninit",
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


def nested(data: dict[str, Any], *keys: str) -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


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
        name: {"path": str(repo_path(path)), "exists": repo_path(path).exists()}
        for name, path in REPORTS.items()
    }


def android_summary(v649: dict[str, Any]) -> dict[str, Any]:
    markers = nested(v649, "android_summary", "markers") or {}
    counts = markers.get("counts") if isinstance(markers.get("counts"), dict) else {}
    deltas = markers.get("deltas_ms") if isinstance(markers.get("deltas_ms"), dict) else {}
    first_times = markers.get("first_times") if isinstance(markers.get("first_times"), dict) else {}
    return {
        "service180": int_value(counts.get("service_notifier_180")),
        "service74": int_value(counts.get("service_notifier_74")),
        "wlan_pd": int_value(counts.get("wlan_pd")),
        "wlfw_start": int_value(counts.get("wlfw_start")),
        "qmi_server_connected": int_value(counts.get("qmi_server_connected")),
        "bdf_regdb": int_value(counts.get("bdf_regdb")),
        "bdf_bdwlan": int_value(counts.get("bdf_bdwlan")),
        "wlan_fw_ready": int_value(counts.get("wlan_fw_ready")),
        "wlan0": int_value(counts.get("wlan0")),
        "sysmon_esoc0": int_value(counts.get("sysmon_esoc0")),
        "service74_to_wlfw_start_ms": deltas.get("service74_to_wlfw_start"),
        "service74_to_wlan_pd_ms": deltas.get("service74_to_wlan_pd"),
        "service74_to_qmi_server_connected_ms": deltas.get("service74_to_qmi_server_connected"),
        "service74_time": first_times.get("service_notifier_74"),
        "wlan_pd_time": first_times.get("wlan_pd"),
        "wlfw_start_time": first_times.get("wlfw_start"),
    }


def native_v835_summary(v835: dict[str, Any]) -> dict[str, Any]:
    service_notifier = nested(v835, "lower_replay", "service_notifier") or {}
    markers = nested(v835, "lower_replay", "live", "markers") or {}
    guard = v835.get("known_asoc_warning_guard") if isinstance(v835.get("known_asoc_warning_guard"), dict) else {}
    events = guard.get("events") if isinstance(guard.get("events"), dict) else {}
    gaps = guard.get("gaps_ms") if isinstance(guard.get("gaps_ms"), dict) else {}
    return {
        "response_success": int_value(service_notifier.get("response_success")),
        "response_state": service_notifier.get("response_curr_state_name", ""),
        "response_raw": service_notifier.get("response_curr_state", ""),
        "indication_seen": int_value(service_notifier.get("indication_seen")),
        "service180": int_value(nested(events, "service180", "count")),
        "service74": int_value(nested(events, "service74", "count")),
        "sysmon_modem": int_value(nested(events, "sysmon_modem", "count")),
        "sysmon_adsp": int_value(nested(events, "sysmon_adsp", "count")),
        "sysmon_cdsp": int_value(nested(events, "sysmon_cdsp", "count")),
        "sysmon_slpi": int_value(nested(events, "sysmon_slpi", "count")),
        "service74_to_pm_qos_duplicate_ms": gaps.get("service74_to_pm_qos_duplicate"),
        "service74_to_wlfw_start_ms": gaps.get("service74_to_wlfw_start"),
        "service_notifier_marker": int_value(markers.get("service_notifier")),
        "wlan_pd": int_value(markers.get("wlan_pd")),
        "wlfw": int_value(markers.get("wlfw")),
        "bdf": int_value(markers.get("bdf")),
        "wlan0": int_value(markers.get("wlan0")),
        "known_asoc_warning": bool(guard.get("exact_known_asoc_warning")),
    }


def candidate(name: str, classification: str, reason: str, next_step: str) -> dict[str, str]:
    return {
        "candidate": name,
        "classification": classification,
        "reason": reason,
        "next_step": next_step,
    }


def classify() -> dict[str, Any]:
    inputs = {name: load_json(path) for name, path in INPUTS.items()}
    android = android_summary(inputs["v649"])
    native = native_v835_summary(inputs["v835"])

    android_reaches_state_up_path = (
        android["service74"] > 0
        and android["wlan_pd"] > 0
        and android["wlfw_start"] > 0
        and android["wlan0"] > 0
    )
    native_best_window_still_uninit = (
        native["service180"] > 0
        and native["service74"] > 0
        and native["response_success"] == 1
        and native["response_state"] == "uninit"
        and native["wlfw"] == 0
        and native["wlan0"] == 0
    )
    android_reference_timing_known = (
        android["service74_to_wlfw_start_ms"] is not None
        and android["service74_to_wlan_pd_ms"] is not None
    )

    candidate_matrix = [
        candidate(
            "repeat V835 same-window listener replay",
            "reject",
            "V835 already queried the corrected listener in the best known native lower window and still got UNINIT",
            "do not rerun without adding timing/source observability",
        ),
        candidate(
            "wait-only extension",
            "weak",
            "Android reaches WLFW/WLAN-PD within about 1.3s/2.4s after service74; V835 lacks proof of listener/send timing relative to service74",
            "if waiting is tested, first add timestamped post-service74 listener evidence instead of blindly extending runtime",
        ),
        candidate(
            "service-manager/HAL/scan/connect/DHCP/external ping",
            "blocked",
            "native still lacks WLAN-PD UP, WLFW service69, BDF, wiphy, and wlan0",
            "keep final Wi-Fi bring-up above the current lower-state blocker",
        ),
        candidate(
            "boot_wlan/qcwlanstate/register-driver retry",
            "reject",
            "V809/V810 classify these as downstream mirrors gated by missing WLFW/FW_READY",
            "return only after WLFW/service69 or WLAN-PD UP appears",
        ),
        candidate(
            "custom OSRC diagnostic kernel flash",
            "paused",
            "V775 classified stock-vs-OSRC boot incompatibility",
            "resume only after boot compatibility is solved host-only",
        ),
        candidate(
            "timestamped post-service74 listener hold",
            "select-next",
            "V835 proves state remains UNINIT but does not timestamp listener send/response/hold against service74 and Android's 1.3s/2.4s continuation window",
            "V837 should add bounded timestamps and hold the listener through the post-service74 window before any wider trigger",
        ),
    ]

    return {
        "inputs": input_summary(inputs),
        "reports": report_summary(),
        "signals": {
            "android_v649": android,
            "native_v835": native,
            "prior_decisions": {name: inputs[name].get("decision", "") for name in ("v650", "v651", "v696", "v701", "v811")},
        },
        "derived": {
            "android_reaches_state_up_path": android_reaches_state_up_path,
            "native_best_window_still_uninit": native_best_window_still_uninit,
            "android_reference_timing_known": android_reference_timing_known,
            "listener_payload_model_closed_by_v833_v835": True,
            "next_gate": "v837-timestamped-post74-listener-hold",
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
            f"refresh {name} evidence before using V836",
        )
    derived = analysis["derived"]
    add_check(
        checks,
        "android-reference-path",
        "pass" if derived["android_reaches_state_up_path"] else "blocked",
        "blocker",
        str(analysis["signals"]["android_v649"]),
        "refresh Android reference before comparing native state-up gap",
    )
    add_check(
        checks,
        "native-best-window-uninit",
        "pass" if derived["native_best_window_still_uninit"] else "blocked",
        "blocker",
        str(analysis["signals"]["native_v835"]),
        "complete V835 before selecting the next lower-state gate",
    )
    add_check(
        checks,
        "host-only-boundary",
        "pass",
        "blocker",
        "V836 reads local manifests/reports only",
        "keep V836 host-only",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v836-post-v835-state-up-contract-plan-ready",
            True,
            "plan-only; no device command, QMI payload, daemon, Wi-Fi action, or flash executed",
            "run V836 host-only classifier",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v836-post-v835-state-up-contract-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "refresh prerequisite evidence before selecting next gate",
        )
    return (
        "v836-timestamped-post74-listener-hold-selected",
        True,
        "Android reaches WLFW/WLAN-PD quickly after service74, while V835 remains UNINIT in the best native lower window; next live gate needs timing/source observability, not a wider stack",
        "V837 should timestamp listener send/response/hold relative to service74 and keep HAL/connect blocked",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    return "\n".join([
        "# V836 Post-V835 State-Up Contract Classifier",
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
        "cycle": "v836",
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
    print(f"qmi_payload_executed: {manifest['qmi_payload_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
