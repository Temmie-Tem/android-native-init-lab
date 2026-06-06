#!/usr/bin/env python3
"""V640 host-only safe sibling trigger reclassifier.

This classifier consolidates V622/V627/V628/V630/V631/V635/V636/V638/V639
evidence after late all-sibling direct writes were blocked. It does not contact
the device, write sysfs, start daemons, start service-manager, start Wi-Fi HAL,
scan/connect/link-up, use credentials, run DHCP, change routes, reboot, flash,
or ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v640-safe-sibling-trigger-reclassifier")
DEFAULT_ANDROID_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_V627_REPORT = Path("docs/reports/NATIVE_INIT_V627_POST_180_OBSERVER_LIVE_2026-05-23.md")
DEFAULT_V628_REPORT = Path("docs/reports/NATIVE_INIT_V628_SERVICE74_PUBLISHER_CLASSIFIER_2026-05-23.md")
DEFAULT_V630_REPORT = Path("docs/reports/NATIVE_INIT_V630_SIBLING_SSCTL_BOOT_WINDOW_PROOF_LIVE_2026-05-23.md")
DEFAULT_V631_REPORT = Path("docs/reports/NATIVE_INIT_V631_PER_NODE_SIBLING_SSCTL_PROOF_LIVE_2026-05-23.md")
DEFAULT_V635_MANIFEST = Path("tmp/wifi/v635-cdsp-proof-20260523-052940/manifest.json")
DEFAULT_V636_MANIFEST = Path("tmp/wifi/v636-cdsp-v598-live-20260523-054728/manifest.json")
DEFAULT_V638_MANIFEST = Path("tmp/wifi/v638-firmware-sibling-live-20260523-060104/manifest.json")
DEFAULT_V639_MANIFEST = Path("tmp/wifi/v639-sibling-warning-attribution-classifier/manifest.json")
DEFAULT_VENDOR_SNAPSHOT = Path("tmp/wifi/v614-mdm3-trigger-path-classifier/native/vendor-init-readonly-snapshot.txt")

FORBIDDEN_ACTIONS = [
    "device command",
    "sysfs write",
    "DSP boot-node write",
    "boot image build/flash/reboot",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
]

BOOT_NODES = {
    "adsp": "/sys/kernel/boot_adsp/boot",
    "cdsp": "/sys/kernel/boot_cdsp/boot",
    "slpi": "/sys/kernel/boot_slpi/boot",
}

SERVICE_PROPS = {
    "qrtr_ns": "qrtr_ns_boottime_ms",
    "pd_mapper": "pd_mapper_boottime_ms",
    "rmt_storage": "rmt_storage_boottime_ms",
    "tftp_server": "tftp_server_boottime_ms",
    "mdm_launcher": "mdm_launcher_boottime_ms",
    "cnss_diag": "cnss_diag_boottime_ms",
    "mdm_helper": "mdm_helper_boottime_ms",
    "cnss_daemon": "cnss_daemon_boottime_ms",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-v622-manifest", type=Path, default=DEFAULT_ANDROID_V622_MANIFEST)
    parser.add_argument("--v627-report", type=Path, default=DEFAULT_V627_REPORT)
    parser.add_argument("--v628-report", type=Path, default=DEFAULT_V628_REPORT)
    parser.add_argument("--v630-report", type=Path, default=DEFAULT_V630_REPORT)
    parser.add_argument("--v631-report", type=Path, default=DEFAULT_V631_REPORT)
    parser.add_argument("--v635-manifest", type=Path, default=DEFAULT_V635_MANIFEST)
    parser.add_argument("--v636-manifest", type=Path, default=DEFAULT_V636_MANIFEST)
    parser.add_argument("--v638-manifest", type=Path, default=DEFAULT_V638_MANIFEST)
    parser.add_argument("--v639-manifest", type=Path, default=DEFAULT_V639_MANIFEST)
    parser.add_argument("--vendor-snapshot", type=Path, default=DEFAULT_VENDOR_SNAPSHOT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def nested(mapping: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def number(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def count_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def marker_delta(manifest: dict[str, Any]) -> dict[str, Any]:
    return nested(manifest, ("proof", "marker_delta"), {}) or nested(manifest, ("live", "cdsp_marker_delta"), {}) or {}


def post_markers(manifest: dict[str, Any]) -> dict[str, Any]:
    return nested(manifest, ("live", "post_cdsp_markers"), {}) or {}


def context_block(text: str, needle: str, before: int = 5, after: int = 4) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if needle in line:
            start = max(0, index - before)
            end = min(len(lines), index + after + 1)
            return "\n".join(lines[start:end])
    return ""


def boot_node_contexts(snapshot: str) -> dict[str, dict[str, Any]]:
    contexts: dict[str, dict[str, Any]] = {}
    for node, path in BOOT_NODES.items():
        contexts[node] = {
            "path": path,
            "present": f"write {path} 1" in snapshot,
            "phase": "early-boot" if re.search(r"on early-boot[\s\S]{0,700}" + re.escape(f"write {path} 1"), snapshot) else "unknown",
            "context": context_block(snapshot, f"write {path} 1"),
        }
    return contexts


def android_timing(android: dict[str, Any]) -> dict[str, Any]:
    summary = android.get("android_summary") or {}
    counts = summary.get("counts") or {}
    timing = summary.get("timing") or {}
    deltas = summary.get("deltas_ms") or {}
    service74_ms = number(timing.get("service_notifier_74_ms"))
    rows: list[list[str]] = []
    pre74_untested: list[str] = []
    already_replayed = {"qrtr_ns", "pd_mapper", "rmt_storage", "tftp_server"}
    for service, key in SERVICE_PROPS.items():
        start_ms = number(timing.get(key))
        relation = "unknown"
        delta = ""
        if start_ms is not None and service74_ms is not None:
            diff = start_ms - service74_ms
            delta = f"{diff:.3f}"
            relation = "before-service74" if diff < 0 else "after-service74"
        replayed = service in already_replayed
        if relation == "before-service74" and not replayed:
            pre74_untested.append(service)
        rows.append([service, "" if start_ms is None else f"{start_ms:.3f}", relation, delta, bool_text(replayed)])
    return {
        "counts": counts,
        "timing": timing,
        "deltas_ms": deltas,
        "service74_ms": service74_ms,
        "service_rows": rows,
        "pre74_untested_nonwrite_services": pre74_untested,
        "has_sibling_sysmon": all(count_value(counts.get(key)) > 0 for key in ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp")),
        "has_service74": count_value(counts.get("service_notifier_74")) > 0,
        "service180_to_74_ms": deltas.get("service_notifier_180_to_service_notifier_74"),
    }


def report_decision(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1) if match else "missing"


def build_checks(manifest: dict[str, Any]) -> dict[str, Any]:
    android = manifest["android_v622"]
    v635_delta = marker_delta(manifest["v635"])
    v636_post = post_markers(manifest["v636"])
    v638_delta = marker_delta(manifest["v638"])
    v639_checks = manifest["v639"].get("checks") or {}
    return {
        "android_has_service74": android["has_service74"],
        "android_has_sibling_sysmon": android["has_sibling_sysmon"],
        "visible_boot_nodes_all_early": all(item["present"] and item["phase"] == "early-boot" for item in manifest["boot_node_contexts"].values()),
        "pre74_nonwrite_untested": len(android["pre74_untested_nonwrite_services"]) > 0,
        "known_pre74_nonwrite_replayed": not android["pre74_untested_nonwrite_services"],
        "v627_service180_only": "service-notifier `180`" in manifest["v627_report"] and "service-notifier `74` | missing" in manifest["v627_report"],
        "v628_sibling_gap": "v628-service74-sibling-sysmon-gap-classified" in manifest["v628_report"],
        "v630_boot_window_attempted": "v630-boot-window-timeout-after-adsp" in manifest["v630_report"],
        "v631_per_node_attempted": "v631-cdsp-timeout-adsp-slpi-ok" in manifest["v631_report"],
        "v635_cdsp_warning_free": count_value(v635_delta.get("pm_qos_warning")) == 0,
        "v635_cdsp_no_service74": count_value(v635_delta.get("service_notifier_74")) == 0,
        "v636_service180_warning_free": count_value(v636_post.get("service_notifier_180")) > 0 and count_value(v636_post.get("kernel_warning")) == 0,
        "v636_service74_missing": count_value(v636_post.get("service_notifier_74")) == 0,
        "v638_late_all_sibling_warning": count_value(v638_delta.get("pm_qos_warning")) > 0 and count_value(v638_delta.get("service_notifier_74")) == 0,
        "v639_late_all_sibling_blocked": bool(v639_checks.get("v638_warning_tied_to_multiple_nodes")) and bool(v639_checks.get("v635_cdsp_only_warning_free")),
    }


def evidence_rows(manifest: dict[str, Any]) -> list[list[str]]:
    checks = manifest["checks"]
    android = manifest["android_v622"]
    return [
        [
            "Android V622",
            "target path",
            f"sibling_sysmon={android['has_sibling_sysmon']}; service74={android['has_service74']}; 180->74={android['service180_to_74_ms']}ms",
            "service 74 remains below HAL/connect",
        ],
        [
            "non-write services",
            "no new pre-74 target",
            f"untested_pre74={android['pre74_untested_nonwrite_services']}; replayed_pre74=qrtr_ns,pd_mapper,rmt_storage,tftp_server",
            "do not add random daemon starts",
        ],
        [
            "boot-node contract",
            "Android early-boot only",
            f"all_early={checks['visible_boot_nodes_all_early']}",
            "late live writes are not equivalent",
        ],
        [
            "V630/V631 boot window",
            "attempted but firmware-incomplete",
            f"v630={checks['v630_boot_window_attempted']}; v631={checks['v631_per_node_attempted']}",
            "boot-window remains the right class, but needs firmware-backed redesign",
        ],
        [
            "V635/V636",
            "warning-free partial positive",
            f"cdsp_warning_free={checks['v635_cdsp_warning_free']}; service180_warning_free={checks['v636_service180_warning_free']}",
            "preserve warning-free baseline",
        ],
        [
            "V638/V639",
            "late direct writes blocked",
            f"late_warning={checks['v638_late_all_sibling_warning']}; blocked={checks['v639_late_all_sibling_blocked']}",
            "do not repeat all-sibling live writes",
        ],
    ]


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    checks = manifest["checks"]
    if (
        checks["android_has_service74"]
        and checks["android_has_sibling_sysmon"]
        and checks["known_pre74_nonwrite_replayed"]
        and checks["v628_sibling_gap"]
        and checks["v630_boot_window_attempted"]
        and checks["v631_per_node_attempted"]
        and checks["v635_cdsp_warning_free"]
        and checks["v636_service180_warning_free"]
        and checks["v638_late_all_sibling_warning"]
        and checks["v639_late_all_sibling_blocked"]
    ):
        return (
            "v640-boot-window-only-sibling-trigger-needed",
            True,
            (
                "No untested non-write pre-service74 Android daemon remains; warning-free native service180 still lacks sibling sysmon/service74, "
                "late all-sibling writes are blocked, and prior boot-window attempts predate firmware-backed CDSP fix."
            ),
            "plan a rollback-ready firmware-backed early-boot sibling trigger proof; keep HAL/connect/credentials blocked",
        )
    if checks["pre74_nonwrite_untested"]:
        return (
            "v640-nonwrite-service74-publisher-candidate",
            True,
            f"untested pre-service74 non-write services remain: {manifest['android_v622']['pre74_untested_nonwrite_services']}",
            "classify those services before boot-image proof",
        )
    if checks["v638_late_all_sibling_warning"] and checks["v639_late_all_sibling_blocked"]:
        return (
            "v640-unsafe-direct-write-paths-exhausted",
            True,
            "late direct write paths are exhausted; service74 still absent",
            "use kernel-source or Android recapture before another live mutation",
        )
    return (
        "v640-kernel-source-or-android-recapture-needed",
        False,
        f"evidence incomplete: {checks}",
        "refresh Android/native evidence before next gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    snapshot = read_text(args.vendor_snapshot)
    android = android_timing(load_json(args.android_v622_manifest))
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "android_v622_manifest": str(repo_path(args.android_v622_manifest)),
            "v627_report": str(repo_path(args.v627_report)),
            "v628_report": str(repo_path(args.v628_report)),
            "v630_report": str(repo_path(args.v630_report)),
            "v631_report": str(repo_path(args.v631_report)),
            "v635_manifest": str(repo_path(args.v635_manifest)),
            "v636_manifest": str(repo_path(args.v636_manifest)),
            "v638_manifest": str(repo_path(args.v638_manifest)),
            "v639_manifest": str(repo_path(args.v639_manifest)),
            "vendor_snapshot": str(repo_path(args.vendor_snapshot)),
        },
        "android_v622": android,
        "boot_node_contexts": boot_node_contexts(snapshot),
        "v627_report": read_text(args.v627_report),
        "v628_report": read_text(args.v628_report),
        "v630_report": read_text(args.v630_report),
        "v631_report": read_text(args.v631_report),
        "v635": load_json(args.v635_manifest),
        "v636": load_json(args.v636_manifest),
        "v638": load_json(args.v638_manifest),
        "v639": load_json(args.v639_manifest),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "sysfs_writes_executed": False,
        "boot_image_write_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    manifest["checks"] = build_checks(manifest)
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v640-safe-sibling-trigger-reclassifier-plan-ready",
            True,
            "plan-only; run will classify existing evidence without device contact",
            "run V640 host-only reclassifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(manifest)
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
    })
    manifest["evidence_rows"] = evidence_rows(manifest)
    manifest["inferences"] = {
        "wifi_goal_not_complete": True,
        "credentials_still_blocked": True,
        "late_all_sibling_live_retry_blocked": True,
        "service180_warning_free_baseline_preserved": manifest["checks"]["v636_service180_warning_free"],
        "firmware_backed_early_boot_proof_is_next_candidate": decision == "v640-boot-window-only-sibling-trigger-needed",
    }
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V640 Safe Sibling Trigger Reclassifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- sysfs_writes_executed: `{manifest['sysfs_writes_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Evidence Matrix",
        "",
        markdown_table(["subject", "classification", "evidence", "next"], manifest["evidence_rows"]),
        "",
        "## Android V622 Service Timing",
        "",
        markdown_table(["service", "start_ms", "relation_to_service74", "delta_ms", "already_replayed"], manifest["android_v622"]["service_rows"]),
        "",
        "## Boot Node Contexts",
        "",
        markdown_table(
            ["node", "path", "present", "phase"],
            [
                [node, data["path"], bool_text(data["present"]), data["phase"]]
                for node, data in manifest["boot_node_contexts"].items()
            ],
        ),
        "",
        "## Checks",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in manifest["checks"].items()]),
        "",
        "## Inferences",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in manifest["inferences"].items()]),
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
    print(f"sysfs_writes_executed: {manifest['sysfs_writes_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
