#!/usr/bin/env python3
"""V623 host-only lower QMI publication gap classifier.

V622 proved `mdm_helper` and `mdm_launcher` are later than first
service-notifier publication. V623 compares the same-boot Android timing with
native V609/V619 and older Android companion evidence to decide whether
`qmiproxy` is a credible next live target or whether the remaining blocker is a
lower kernel/QMI publication gap.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from native_wifi_qmi_publication_precondition_v610 import (
    TIMELINE_MARKERS,
    count_by_marker,
    first_by_marker,
    parse_events,
    read_binary_text,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v623-lower-publication-gap-classifier")
DEFAULT_V622_GLOB = "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-*/v622-android-mdm-helper-timing-recapture-run/manifest.json"
DEFAULT_V619_MANIFEST = Path("tmp/wifi/v619-android-order-post-sysmon-observer-run/manifest.json")
DEFAULT_V619_DMESG = Path("tmp/wifi/v619-android-order-post-sysmon-observer-run/native/dmesg-delta.txt")
DEFAULT_V609_MANIFEST = Path("tmp/wifi/v609-post-sysmon-20260523-004918/v609-observer-live/manifest.json")
DEFAULT_V609_DMESG = Path("tmp/wifi/v609-post-sysmon-20260523-004918/v609-observer-live/native/dmesg-delta.txt")
DEFAULT_V524_MANIFEST = Path("tmp/wifi/v524-android-companion-exact-recapture-handoff/v521-android-companion-recapture-run/manifest.json")
DEFAULT_VENDOR_SNAPSHOT = Path("tmp/wifi/v614-mdm3-trigger-path-classifier/native/vendor-init-readonly-snapshot.txt")

FORBIDDEN_ACTIONS = [
    "device command",
    "boot image or partition write",
    "sysfs write",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "QRTR/QMI payload",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v622-manifest", type=Path, default=None)
    parser.add_argument("--v622-glob", default=DEFAULT_V622_GLOB)
    parser.add_argument("--v619-manifest", type=Path, default=DEFAULT_V619_MANIFEST)
    parser.add_argument("--v619-dmesg", type=Path, default=DEFAULT_V619_DMESG)
    parser.add_argument("--v609-manifest", type=Path, default=DEFAULT_V609_MANIFEST)
    parser.add_argument("--v609-dmesg", type=Path, default=DEFAULT_V609_DMESG)
    parser.add_argument("--v524-manifest", type=Path, default=DEFAULT_V524_MANIFEST)
    parser.add_argument("--vendor-snapshot", type=Path, default=DEFAULT_VENDOR_SNAPSHOT)
    parser.add_argument("command", choices=("run",), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def latest_v622_manifest(pattern: str) -> Path:
    paths = sorted(repo_path(".").glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    return paths[0] if paths else repo_path(pattern)


def service_block(snapshot: str, name: str) -> str:
    match = re.search(rf"^service\s+{re.escape(name)}\s+.*(?:\n[ \t].*)*", snapshot, re.M)
    return match.group(0) if match else ""


def has_line(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.I | re.M) is not None


def event_time_ms(found: dict[str, Any], marker: str) -> float | None:
    event = found.get(marker)
    if event is None or event.timestamp is None:
        return None
    return round(event.timestamp * 1000.0, 3)


def delta_ms(newer: float | None, older: float | None) -> float | None:
    if newer is None or older is None:
        return None
    return round(newer - older, 3)


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def parse_native_case(dmesg_path: Path, source: str, prior_manifest: dict[str, Any]) -> dict[str, Any]:
    text = read_binary_text(repo_path(dmesg_path))
    events = parse_events(text, source)
    counts = count_by_marker(events)
    found = first_by_marker(events)
    manifest_warning_count = (
        ((prior_manifest.get("live") or {}).get("markers") or {}).get("counts") or {}
    ).get("kernel_warning")
    pm_qos_warnings = int(manifest_warning_count) if manifest_warning_count is not None else len(
        re.findall(r"WARNING: CPU:.*pm_qos_add_request", text, re.I)
    )
    service_locator_fail = len(re.findall(r"Unable to connect to service locator|wait for locator service timed out", text, re.I))
    return {
        "path": str(repo_path(dmesg_path)),
        "counts": {marker: counts.get(marker, 0) for marker in TIMELINE_MARKERS},
        "first_ms": {
            "sysmon_modem": event_time_ms(found, "sysmon_modem"),
            "sysmon_slpi": event_time_ms(found, "sysmon_slpi"),
            "sysmon_cdsp": event_time_ms(found, "sysmon_cdsp"),
            "sysmon_adsp": event_time_ms(found, "sysmon_adsp"),
            "service_locator": event_time_ms(found, "service_locator"),
            "service_notifier_180": event_time_ms(found, "service_notifier_180"),
            "service_notifier_74": event_time_ms(found, "service_notifier_74"),
            "rmt_storage_ready": event_time_ms(found, "rmt_storage_ready"),
        },
        "deltas_ms": {
            "sysmon_modem_to_service_locator": delta_ms(event_time_ms(found, "service_locator"), event_time_ms(found, "sysmon_modem")),
            "sysmon_modem_to_service_notifier_180": delta_ms(event_time_ms(found, "service_notifier_180"), event_time_ms(found, "sysmon_modem")),
            "service_locator_to_service_notifier_180": delta_ms(event_time_ms(found, "service_notifier_180"), event_time_ms(found, "service_locator")),
        },
        "pm_qos_warnings": pm_qos_warnings,
        "service_locator_failures": service_locator_fail,
    }


def qmiproxy_summary(v524: dict[str, Any], snapshot: str) -> dict[str, Any]:
    summary = v524.get("android_summary") or {}
    lines = "\n".join(summary.get("companion_lines") or [])
    binary_lines = "\n".join(summary.get("binary_lines") or [])
    block = service_block(snapshot, "qmiproxy")
    return {
        "init_service_present": bool(block),
        "init_service_disabled": "disabled" in block,
        "init_service_user_radio": bool(re.search(r"\buser\s+radio\b", block)),
        "init_service_group_radio_diag": bool(re.search(r"\bgroup\s+radio\s+diag\b", block)),
        "start_ref_present": has_line(snapshot, r"start\s+qmiproxy"),
        "android_static_candidate": bool(summary.get("has_qmiproxy")) or "qmiproxy" in binary_lines,
        "android_process_running": bool(re.search(r"^\S+\s+\S+\s+\d+\s+\d+.*\bqmiproxy(?:\s|$)", lines, re.M)),
        "first_static_line": next((line for line in binary_lines.splitlines() if "qmiproxy" in line), "missing"),
    }


def evidence_rows(manifest: dict[str, Any]) -> list[list[str]]:
    android = manifest["android_v622"]
    v619 = manifest["native_v619"]
    v609 = manifest["native_v609"]
    qmiproxy = manifest["qmiproxy"]
    timing = android["timing"]
    return [
        [
            "Android lower order",
            "service-notifier precedes mdm/cnss",
            (
                f"pd_mapper={timing.get('pd_mapper_boottime_ms')}ms; "
                f"sysmon={timing.get('sysmon_modem_ms')}ms; "
                f"service180={timing.get('service_notifier_180_ms')}ms; "
                f"mdm_helper={timing.get('mdm_helper_boottime_ms')}ms"
            ),
            "keep mdm_helper/CNSS/HAL blocked as first triggers",
        ],
        [
            "Native V619",
            "locator present, notifier absent",
            (
                f"sysmon={v619['first_ms'].get('sysmon_modem')}ms; "
                f"locator={v619['first_ms'].get('service_locator')}ms; "
                f"service180={v619['first_ms'].get('service_notifier_180')}; "
                f"pm_qos={v619['pm_qos_warnings']}"
            ),
            "do not repeat direct DSP boot-node path",
        ],
        [
            "Native V609",
            "modem-only sysmon path insufficient",
            (
                f"sysmon={v609['first_ms'].get('sysmon_modem')}ms; "
                f"locator={v609['first_ms'].get('service_locator')}ms; "
                f"service180={v609['first_ms'].get('service_notifier_180')}"
            ),
            "needs more than qrtr/rmt/tftp/pd order",
        ],
        [
            "qmiproxy",
            "static/disabled candidate only",
            (
                f"init_present={bool_text(qmiproxy['init_service_present'])}; "
                f"disabled={bool_text(qmiproxy['init_service_disabled'])}; "
                f"start_ref={bool_text(qmiproxy['start_ref_present'])}; "
                f"running={bool_text(qmiproxy['android_process_running'])}"
            ),
            "do not add qmiproxy as a blind live daemon target",
        ],
    ]


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    android = manifest["android_v622"]
    v619 = manifest["native_v619"]
    qmiproxy = manifest["qmiproxy"]
    android_has_pair = android["counts"].get("service_notifier_180", 0) > 0 and android["counts"].get("service_notifier_74", 0) > 0
    v619_has_locator = v619["counts"].get("service_locator", 0) > 0
    v619_lacks_notifier = v619["counts"].get("service_notifier_180", 0) == 0 and v619["counts"].get("service_notifier_74", 0) == 0
    qmiproxy_is_blind = (
        qmiproxy["init_service_present"]
        and qmiproxy["init_service_disabled"]
        and not qmiproxy["start_ref_present"]
        and not qmiproxy["android_process_running"]
    )
    mdm_late = (
        (android["timing"].get("helper_to_service_notifier_180_ms") or 0) < 0
        and (android["timing"].get("launcher_to_service_notifier_180_ms") or 0) < 0
    )
    if android_has_pair and v619_has_locator and v619_lacks_notifier and qmiproxy_is_blind and mdm_late:
        return (
            "v623-lower-qmi-publication-gap-classified",
            True,
            (
                "Android publishes service-notifier before mdm/cnss, native V619 reaches "
                "service-locator without notifier and with pm_qos warnings, and qmiproxy is "
                "only a disabled/static candidate without Android running evidence."
            ),
            "V624 should classify a safe non-DSP-boot-node lower publication trigger; do not add qmiproxy/mdm_helper as blind live targets",
        )
    return (
        "v623-lower-publication-evidence-gap",
        False,
        (
            f"android_has_pair={android_has_pair} v619_has_locator={v619_has_locator} "
            f"v619_lacks_notifier={v619_lacks_notifier} qmiproxy_is_blind={qmiproxy_is_blind} mdm_late={mdm_late}"
        ),
        "refresh host-only inputs before live proof design",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v622_path = repo_path(args.v622_manifest) if args.v622_manifest else latest_v622_manifest(args.v622_glob)
    v622 = load_json(v622_path)
    v619_manifest = load_json(args.v619_manifest)
    v609_manifest = load_json(args.v609_manifest)
    v524 = load_json(args.v524_manifest)
    snapshot = read_text(args.vendor_snapshot)
    android_summary = v622.get("android_summary") or {}
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "v622_manifest": str(v622_path),
            "v619_manifest": str(repo_path(args.v619_manifest)),
            "v619_dmesg": str(repo_path(args.v619_dmesg)),
            "v609_manifest": str(repo_path(args.v609_manifest)),
            "v609_dmesg": str(repo_path(args.v609_dmesg)),
            "v524_manifest": str(repo_path(args.v524_manifest)),
            "vendor_snapshot": str(repo_path(args.vendor_snapshot)),
        },
        "android_v622": {
            "decision": v622.get("decision"),
            "pass": v622.get("pass"),
            "timing": android_summary.get("timing") or {},
            "counts": android_summary.get("counts") or {},
            "first": android_summary.get("first") or {},
        },
        "native_v619": {
            "decision": v619_manifest.get("decision"),
            "pass": v619_manifest.get("pass"),
            **parse_native_case(args.v619_dmesg, "native-v619", v619_manifest),
        },
        "native_v609": {
            "decision": v609_manifest.get("decision"),
            "pass": v609_manifest.get("pass"),
            **parse_native_case(args.v609_dmesg, "native-v609", v609_manifest),
        },
        "qmiproxy": qmiproxy_summary(v524, snapshot),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    decision, pass_ok, reason, next_step = classify(manifest)
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "evidence_rows": evidence_rows(manifest),
    })
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    android_timing = manifest["android_v622"]["timing"]
    native_rows = [
        ["v619", key, str(value)]
        for key, value in manifest["native_v619"]["deltas_ms"].items()
    ] + [
        ["v609", key, str(value)]
        for key, value in manifest["native_v609"]["deltas_ms"].items()
    ]
    return "\n".join([
        "# V623 Lower QMI Publication Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Evidence Matrix",
        "",
        markdown_table(["subject", "classification", "evidence", "next"], manifest["evidence_rows"]),
        "",
        "## Android V622 Timing",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in android_timing.items()]),
        "",
        "## Native Timing Deltas",
        "",
        markdown_table(["case", "delta", "ms"], native_rows),
        "",
        "## qmiproxy",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in manifest["qmiproxy"].items()]),
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
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
