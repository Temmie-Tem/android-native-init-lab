#!/usr/bin/env python3
"""V658 host-only vndbinder/service-manager surface classifier.

This classifier consumes existing V653, V657, V655, and V654 evidence. It does
not contact the device, write sysfs, start daemons, start service-manager,
start Wi-Fi HAL, scan/connect, use credentials, run DHCP, change routes, or
ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_binder_runtime_mismatch_classifier_v654 as v654
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v658-vndbinder-surface-classifier")
DEFAULT_V653_MANIFEST = Path("tmp/wifi/v653-service74-gated-live-20260523-085337/manifest.json")
DEFAULT_V653_DMESG = Path("tmp/wifi/v653-service74-gated-live-20260523-085337/native/dmesg-delta.txt")
DEFAULT_V653_HELPER = Path("tmp/wifi/v653-service74-gated-live-20260523-085337/native/companion-start-only-with-holder.txt")
DEFAULT_V657_MANIFEST = Path("tmp/wifi/v657-service74-v106-replay-live/manifest.json")
DEFAULT_V657_DMESG = Path("tmp/wifi/v657-service74-v106-replay-live/native/dmesg-delta.txt")
DEFAULT_V657_HELPER = Path("tmp/wifi/v657-service74-v106-replay-live/native/companion-start-only-with-holder.txt")
DEFAULT_V655_MANIFEST = Path("tmp/wifi/v655-vndservicemanager-cnss-retry-live/manifest.json")
DEFAULT_V655_DMESG = Path("tmp/wifi/v655-vndservicemanager-cnss-retry-live/native/dmesg-delta.txt")
DEFAULT_V655_HELPER = Path("tmp/wifi/v655-vndservicemanager-cnss-retry-live/native/companion-start-only-with-holder.txt")
DEFAULT_V654_MANIFEST = Path("tmp/wifi/v654-binder-runtime-mismatch-classifier/manifest.json")

FORBIDDEN_ACTIONS = (
    "device command",
    "sysfs write",
    "DSP boot-node write",
    "esoc0 open",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v653-manifest", type=Path, default=DEFAULT_V653_MANIFEST)
    parser.add_argument("--v653-dmesg", type=Path, default=DEFAULT_V653_DMESG)
    parser.add_argument("--v653-helper", type=Path, default=DEFAULT_V653_HELPER)
    parser.add_argument("--v657-manifest", type=Path, default=DEFAULT_V657_MANIFEST)
    parser.add_argument("--v657-dmesg", type=Path, default=DEFAULT_V657_DMESG)
    parser.add_argument("--v657-helper", type=Path, default=DEFAULT_V657_HELPER)
    parser.add_argument("--v655-manifest", type=Path, default=DEFAULT_V655_MANIFEST)
    parser.add_argument("--v655-dmesg", type=Path, default=DEFAULT_V655_DMESG)
    parser.add_argument("--v655-helper", type=Path, default=DEFAULT_V655_HELPER)
    parser.add_argument("--v654-manifest", type=Path, default=DEFAULT_V654_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    text = v654.read_text(path)
    return json.loads(text) if text else {}


def source(path: Path, label: str) -> dict[str, Any]:
    return v654.source_summary(v654.parse_events(v654.read_text(path), label))


def helper_keys(path: Path) -> dict[str, str]:
    return v654.parse_key_values(v654.read_text(path))


def value(mapping: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def count_case(name: str,
               manifest: dict[str, Any],
               summary: dict[str, Any],
               keys: dict[str, str],
               helper_version: str) -> dict[str, Any]:
    service_surface = value(manifest, ("live", "service_manager"), {}) or value(manifest, ("live", "v655_surface"), {})
    gate = service_surface.get("service74_gate") or {}
    counts = value(manifest, ("live", "v653_counts"), {}) or value(manifest, ("live", "v655_counts"), {})
    surface = v654.process_surface(keys)
    return {
        "name": name,
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "helper_version": helper_version,
        "mode": keys.get("wifi_companion_start.order", ""),
        "child_started": keys.get("wifi_companion_start.child_started", ""),
        "service74_status": gate.get("status", ""),
        "service74_seen": gate.get("seen", ""),
        "service74_wait_ms": gate.get("wait_ms", ""),
        "service_manager_started": service_surface.get("service_manager_started", ""),
        "vndservicemanager_readiness_enabled": value(service_surface, ("vndservicemanager_readiness", "enabled"), "0"),
        "cnss_retry_enabled": keys.get("wifi_companion_start.cnss_retry.enabled", "0"),
        "cnss_retry_initial_cleanup_safe": keys.get("wifi_companion_start.cnss_retry.initial_cleanup_safe", ""),
        "service_notifier_180": counts.get("service_notifier_180", summary["counts"].get("service_notifier_180", 0)),
        "service_notifier_74": counts.get("service_notifier_74", summary["counts"].get("service_notifier_74", 0)),
        "cnss_binder_transaction_failed": counts.get(
            "cnss_binder_transaction_failed",
            summary["counts"].get("cnss_binder_transaction_failed", 0),
        ),
        "binder_transaction_failed": counts.get("binder_transaction_failed", summary["counts"].get("generic_binder_transaction_failed", 0)),
        "binder_ioctl_unsupported": counts.get("binder_ioctl_unsupported", summary["counts"].get("generic_binder_ioctl_unsupported", 0)),
        "cnss_daemon_netlink": counts.get("cnss_daemon_netlink", summary["counts"].get("cnss_daemon_netlink", 0)),
        "wlfw_start": counts.get("wlfw_start", summary["counts"].get("cnss_wlfw_start", 0)),
        "wlan_pd": counts.get("wlan_pd", summary["counts"].get("wlan_pd", 0)),
        "qmi_server_connected": counts.get("qmi_server_connected", summary["counts"].get("qmi_server_connected", 0)),
        "kernel_warning": counts.get("kernel_warning", summary["counts"].get("kernel_warning", 0)),
        "cnss_daemon_start_order": surface.get("cnss_daemon_start_order"),
        "vndservicemanager_start_order": surface.get("vndservicemanager_start_order"),
        "cnss_daemon_before_vndservicemanager": surface.get("cnss_daemon_before_vndservicemanager"),
        "cnss_daemon_vndbinder_fd": surface.get("cnss_daemon_vndbinder_fd"),
        "vndservicemanager_vndbinder_fd": surface.get("vndservicemanager_vndbinder_fd"),
        "deltas_ms": summary["deltas_ms"],
    }


def boolish(value_: Any) -> bool:
    return value_ in (True, 1, "1", "true", "True", "yes")


def matrix_rows(cases: list[dict[str, Any]]) -> list[list[str]]:
    fields = (
        "decision",
        "helper_version",
        "child_started",
        "service74_status",
        "service74_wait_ms",
        "service_manager_started",
        "vndservicemanager_readiness_enabled",
        "cnss_retry_enabled",
        "service_notifier_74",
        "cnss_binder_transaction_failed",
        "binder_ioctl_unsupported",
        "wlfw_start",
        "wlan_pd",
        "qmi_server_connected",
        "kernel_warning",
    )
    return [[case["name"], field, str(case.get(field, ""))] for case in cases for field in fields]


def evidence_rows(cases: dict[str, dict[str, Any]], v654_manifest: dict[str, Any]) -> list[list[str]]:
    v653_case = cases["v653"]
    v657_case = cases["v657"]
    v655_case = cases["v655"]
    return [
        [
            "helper v106 exact-mode replay",
            "confirmed",
            (
                f"V657 service74={v657_case['service_notifier_74']} "
                f"gate={v657_case['service74_status']} wait_ms={v657_case['service74_wait_ms']}"
            ),
            "do not blame helper v106 generically",
        ],
        [
            "V653/V657 binder blocker parity",
            "confirmed",
            (
                f"V653 cnss_tx={v653_case['cnss_binder_transaction_failed']} "
                f"V657 cnss_tx={v657_case['cnss_binder_transaction_failed']} "
                f"V657 wlfw={v657_case['wlfw_start']}"
            ),
            "post-service74 blocker remains vndbinder transaction before WLFW",
        ],
        [
            "V655 retry mode before gate",
            "regressed",
            (
                f"service74={v655_case['service_notifier_74']} "
                f"cnss_tx={v655_case['cnss_binder_transaction_failed']} "
                f"service_manager_started={v655_case['service_manager_started']}"
            ),
            "do not retry full V655 tail unchanged",
        ],
        [
            "vndservicemanager readiness",
            "still unproven",
            (
                f"V657 readiness_enabled={v657_case['vndservicemanager_readiness_enabled']} "
                f"V655 readiness_enabled={v655_case['vndservicemanager_readiness_enabled']} "
                f"V655 gate={v655_case['service74_status']}"
            ),
            "next live gate should isolate vndservicemanager readiness without CNSS retry tail",
        ],
        [
            "V654 prior classification",
            "still valid",
            str(v654_manifest.get("decision")),
            "retain binder namespace/SELinux framing but update next gate using V657 evidence",
        ],
    ]


def classify(cases: dict[str, dict[str, Any]], v654_manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    v653_case = cases["v653"]
    v657_case = cases["v657"]
    v655_case = cases["v655"]
    if (
        v657_case["service74_status"] == "open"
        and int(v657_case["service_notifier_74"] or 0) > 0
        and int(v657_case["cnss_binder_transaction_failed"] or 0) > 0
        and int(v657_case["wlfw_start"] or 0) == 0
        and int(v653_case["cnss_binder_transaction_failed"] or 0) > 0
        and v655_case["service74_status"] == "timeout"
        and int(v655_case["cnss_binder_transaction_failed"] or 0) > int(v657_case["cnss_binder_transaction_failed"] or 0)
        and v654_manifest.get("decision") == "v654-vndbinder-readiness-gap-classified"
    ):
        return (
            "v658-vndservicemanager-readiness-isolation-ready",
            True,
            (
                "V657 proves helper v106 can reproduce the V653 service74 gate, while "
                "V653/V657 both stop at the cnss-daemon vndbinder transaction before WLFW. "
                "V655's combined readiness+CNSS retry mode times out before service74 and "
                "amplifies cnss binder failures, so the next gate should isolate "
                "vndservicemanager readiness without the retry tail."
            ),
            (
                "plan V659 as service74-gated vndservicemanager readiness-only proof; "
                "no fresh cnss-daemon retry, no Wi-Fi HAL, no scan/connect, no external ping"
            ),
        )
    return (
        "v658-vndbinder-surface-review-required",
        False,
        "V653/V657/V655 evidence did not match expected binder-surface progression",
        "inspect manifests and helper transcripts before another live gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v653_manifest = load_json(args.v653_manifest)
    v657_manifest = load_json(args.v657_manifest)
    v655_manifest = load_json(args.v655_manifest)
    v654_manifest = load_json(args.v654_manifest)
    cases_list = [
        count_case("v653", v653_manifest, source(args.v653_dmesg, "native-v653"), helper_keys(args.v653_helper), "v105"),
        count_case("v657", v657_manifest, source(args.v657_dmesg, "native-v657"), helper_keys(args.v657_helper), "v106"),
        count_case("v655", v655_manifest, source(args.v655_dmesg, "native-v655"), helper_keys(args.v655_helper), "v106"),
    ]
    cases = {case["name"]: case for case in cases_list}
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v658-vndbinder-surface-classifier-plan-ready",
            True,
            "plan-only; no device contact, no daemon start, no Wi-Fi bring-up",
            "run V658 host-only classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(cases, v654_manifest)
    rows = evidence_rows(cases, v654_manifest)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": v654.collect_host_metadata(),
        "inputs": {
            "v653_manifest": str(v654.repo_path(args.v653_manifest)),
            "v653_dmesg": str(v654.repo_path(args.v653_dmesg)),
            "v653_helper": str(v654.repo_path(args.v653_helper)),
            "v657_manifest": str(v654.repo_path(args.v657_manifest)),
            "v657_dmesg": str(v654.repo_path(args.v657_dmesg)),
            "v657_helper": str(v654.repo_path(args.v657_helper)),
            "v655_manifest": str(v654.repo_path(args.v655_manifest)),
            "v655_dmesg": str(v654.repo_path(args.v655_dmesg)),
            "v655_helper": str(v654.repo_path(args.v655_helper)),
            "v654_manifest": str(v654.repo_path(args.v654_manifest)),
        },
        "prior": {
            "v653": {"decision": v653_manifest.get("decision"), "pass": v653_manifest.get("pass")},
            "v654": {"decision": v654_manifest.get("decision"), "pass": v654_manifest.get("pass")},
            "v655": {"decision": v655_manifest.get("decision"), "pass": v655_manifest.get("pass")},
            "v657": {"decision": v657_manifest.get("decision"), "pass": v657_manifest.get("pass")},
        },
        "cases": cases,
        "evidence_rows": rows,
        "evidence_matrix": v654.rows_to_dicts(["subject", "classification", "evidence", "next"], rows),
        "case_matrix_rows": matrix_rows(cases_list),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
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
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V658 Vndbinder Surface Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Evidence Matrix",
        "",
        v654.markdown_table(["subject", "classification", "evidence", "next"], manifest["evidence_rows"]),
        "",
        "## Case Matrix",
        "",
        v654.markdown_table(["case", "field", "value"], manifest["case_matrix_rows"]),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(v654.repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"service_manager_start_executed: {manifest['service_manager_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
