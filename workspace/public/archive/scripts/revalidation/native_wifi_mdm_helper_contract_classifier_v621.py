#!/usr/bin/env python3
"""V621 host-only MDM helper contract classifier.

This classifier follows V620 by resolving whether `vendor.mdm_helper`,
`vendor.mdm_launcher`, or `wcnss-service` is the next safe native-init gate.
It uses existing evidence only and does not contact the device, write sysfs,
start daemons, start service-manager, start Wi-Fi HAL, scan, connect, use
credentials, run DHCP, change routes, or ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v621-mdm-helper-contract-classifier")
DEFAULT_V620_MANIFEST = Path("tmp/wifi/v620-dsp-mdm3-safety-classifier-refined/manifest.json")
DEFAULT_V614_SNAPSHOT = Path("tmp/wifi/v614-mdm3-trigger-path-classifier/native/vendor-init-readonly-snapshot.txt")
DEFAULT_ANDROID_V611_MANIFEST = Path(
    "tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/"
    "v611-android-lower-surface-recapture-run/manifest.json"
)
DEFAULT_ANDROID_V431_PROPS = Path(
    "tmp/wifi/v431-android-runtime-gap-handoff-live-su-quote-20260520-152315/"
    "v431-android-runtime-gap-run/commands/wifi-props-filtered.txt"
)
DEFAULT_ANDROID_V431_COMMANDS = Path(
    "tmp/wifi/v431-android-runtime-gap-handoff-live-su-quote-20260520-152315/"
    "v431-android-runtime-gap-run/commands"
)
DEFAULT_ANDROID_V297_PROPS = Path("tmp/wifi/v297-android-property-capture-android/commands/wifi-property-filter.txt")

PROP_RE = re.compile(r"^\[([^]]+)]: \[([^]]*)]$")

FORBIDDEN_ACTIONS = [
    "device command",
    "sysfs write",
    "DSP boot-node write",
    "boot_wlan/qcwlanstate write",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v620-manifest", type=Path, default=DEFAULT_V620_MANIFEST)
    parser.add_argument("--v614-snapshot", type=Path, default=DEFAULT_V614_SNAPSHOT)
    parser.add_argument("--android-v611-manifest", type=Path, default=DEFAULT_ANDROID_V611_MANIFEST)
    parser.add_argument("--android-v431-props", type=Path, default=DEFAULT_ANDROID_V431_PROPS)
    parser.add_argument("--android-v431-commands", type=Path, default=DEFAULT_ANDROID_V431_COMMANDS)
    parser.add_argument("--android-v297-props", type=Path, default=DEFAULT_ANDROID_V297_PROPS)
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


def parse_props(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = PROP_RE.match(raw_line.strip())
        if match:
            values[match.group(1)] = match.group(2)
    return values


def first_line_with(text: str, pattern: str) -> str:
    compiled = re.compile(pattern, re.I)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if compiled.search(line):
            return line
    return "missing"


def has_line(text: str, pattern: str) -> bool:
    return first_line_with(text, pattern) != "missing"


def service_block(snapshot: str, service_name: str) -> str:
    match = re.search(rf"^service\s+{re.escape(service_name)}\s+.*(?:\n[ \t].*)*", snapshot, re.M)
    return match.group(0) if match else ""


def ns_to_ms(raw_value: str | None) -> float | None:
    if not raw_value:
        return None
    try:
        return round(int(raw_value) / 1_000_000.0, 3)
    except ValueError:
        return None


def ms_delta(newer: float | None, older: float | None) -> float | None:
    if newer is None or older is None:
        return None
    return round(newer - older, 3)


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def evidence_rows(manifest: dict[str, Any]) -> list[list[str]]:
    props = manifest["android_props"]
    static = manifest["vendor_static"]
    timing = manifest["timing"]
    return [
        [
            "vendor.mdm_launcher",
            "oneshot wrapper",
            (
                f"present={bool_text(static['mdm_launcher_service_present'])}; "
                f"oneshot={bool_text(static['mdm_launcher_oneshot'])}; "
                f"android_state={props['init.svc.vendor.mdm_launcher']}; "
                f"boottime_ms={timing['v431_mdm_launcher_ms']}"
            ),
            "not a persistent daemon; wrapper only starts mdm_helper through Android init",
        ],
        [
            "vendor.mdm_helper",
            "real Android service candidate",
            (
                f"present={bool_text(static['mdm_helper_service_present'])}; "
                f"disabled={bool_text(static['mdm_helper_disabled'])}; "
                f"android_state={props['init.svc.vendor.mdm_helper']}; "
                f"boottime_ms={timing['v431_mdm_helper_ms']}; "
                f"fail_action={props['persist.vendor.mdm_helper.fail_action']}"
            ),
            "candidate needs same-boot timing or bounded start-only proof design",
        ],
        [
            "ro.baseband gate",
            "satisfied in Android evidence",
            (
                f"ro.baseband={props['ro.baseband']}; ro.boot.baseband={props['ro.boot.baseband']}; "
                f"script_gate={bool_text(static['init_mdm_sh_baseband_gate'])}; "
                f"script_starts_helper={bool_text(static['init_mdm_sh_starts_mdm_helper'])}"
            ),
            "native proof must provide equivalent property surface or direct helper argv",
        ],
        [
            "wcnss-service",
            "not direct target",
            (
                f"start_ref={bool_text(static['wcnss_service_start_ref_present'])}; "
                f"service_block={bool_text(static['wcnss_service_block_present'])}"
            ),
            "do not start `wcnss-service` by name",
        ],
        [
            "timing evidence",
            "cross-boot, not sufficient for live start",
            (
                f"v611 service_notifier_180={timing['v611_service_notifier_180_s']}s; "
                f"v431 mdm_launcher={timing['v431_mdm_launcher_ms']}ms; "
                f"v431 mdm_helper={timing['v431_mdm_helper_ms']}ms; "
                f"v431_has_dmesg={bool_text(manifest['android_v431_has_dmesg'])}"
            ),
            "same-boot Android recapture is the cleanest next evidence step",
        ],
    ]


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    v620_ok = (
        manifest["prior"]["v620"]["decision"] == "v620-esoc0-notifier-causality-refined"
        and bool(manifest["prior"]["v620"]["pass"])
    )
    static = manifest["vendor_static"]
    props = manifest["android_props"]
    helper_contract = (
        static["mdm_helper_service_present"]
        and static["mdm_helper_disabled"]
        and static["init_mdm_sh_baseband_gate"]
        and static["init_mdm_sh_starts_mdm_helper"]
        and props["ro.baseband"] == "mdm"
        and props["init.svc.vendor.mdm_helper"] == "running"
    )
    launcher_contract = static["mdm_launcher_service_present"] and static["mdm_launcher_oneshot"]
    wcnss_not_direct = static["wcnss_service_start_ref_present"] and not static["wcnss_service_block_present"]
    cross_boot_only = not manifest["android_v431_has_dmesg"]

    if v620_ok and helper_contract and launcher_contract and wcnss_not_direct and cross_boot_only:
        return (
            "v621-mdm-helper-contract-same-boot-recapture-required",
            True,
            (
                "`vendor.mdm_helper` is the real Android service candidate and `vendor.mdm_launcher` "
                "is only a ro.baseband-gated oneshot wrapper, but existing mdm_helper boottime and "
                "service-notifier dmesg are from different Android captures. Live native start-only "
                "should wait for same-boot read-only timing or a stricter bounded proof plan."
            ),
            "V622 should collect Android same-boot mdm_helper/mdm_launcher boottime plus dmesg service-notifier/WLAN-PD/sysmon_esoc0 timing, then decide live start-only",
        )

    return (
        "v621-mdm-helper-contract-evidence-gap",
        False,
        (
            f"v620_ok={v620_ok} helper_contract={helper_contract} launcher_contract={launcher_contract} "
            f"wcnss_not_direct={wcnss_not_direct} cross_boot_only={cross_boot_only}"
        ),
        "refresh host-only inputs before live proof design",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v620 = load_json(args.v620_manifest)
    android_v611 = load_json(args.android_v611_manifest)
    snapshot = read_text(args.v614_snapshot)
    v431_props = parse_props(read_text(args.android_v431_props))
    v297_props = parse_props(read_text(args.android_v297_props))
    v431_commands = repo_path(args.android_v431_commands)

    mdm_helper_block = service_block(snapshot, "vendor.mdm_helper")
    mdm_launcher_block = service_block(snapshot, "vendor.mdm_launcher")
    wcnss_service_block = service_block(snapshot, "wcnss-service")
    first = android_v611.get("android_summary", {}).get("first", {})
    service_notifier = first.get("service_notifier_180", {}) if isinstance(first, dict) else {}

    props = {
        "ro.baseband": v431_props.get("ro.baseband", v297_props.get("ro.baseband", "")),
        "ro.boot.baseband": v431_props.get("ro.boot.baseband", v297_props.get("ro.boot.baseband", "")),
        "init.svc.vendor.mdm_helper": v431_props.get(
            "init.svc.vendor.mdm_helper",
            v297_props.get("init.svc.vendor.mdm_helper", ""),
        ),
        "init.svc.vendor.mdm_launcher": v431_props.get(
            "init.svc.vendor.mdm_launcher",
            v297_props.get("init.svc.vendor.mdm_launcher", ""),
        ),
        "persist.vendor.mdm_helper.fail_action": v431_props.get(
            "persist.vendor.mdm_helper.fail_action",
            v297_props.get("persist.vendor.mdm_helper.fail_action", ""),
        ),
    }
    timing = {
        "v431_mdm_launcher_ms": ns_to_ms(v431_props.get("ro.boottime.vendor.mdm_launcher")),
        "v431_mdm_helper_ms": ns_to_ms(v431_props.get("ro.boottime.vendor.mdm_helper")),
        "v431_cnss_diag_ms": ns_to_ms(v431_props.get("ro.boottime.cnss_diag")),
        "v431_cnss_daemon_ms": ns_to_ms(v431_props.get("ro.boottime.cnss-daemon")),
        "v611_service_notifier_180_s": service_notifier.get("timestamp") if isinstance(service_notifier, dict) else None,
    }
    timing["v431_launcher_to_helper_ms"] = ms_delta(
        timing["v431_mdm_helper_ms"],
        timing["v431_mdm_launcher_ms"],
    )

    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "v620_manifest": str(repo_path(args.v620_manifest)),
            "v614_snapshot": str(repo_path(args.v614_snapshot)),
            "android_v611_manifest": str(repo_path(args.android_v611_manifest)),
            "android_v431_props": str(repo_path(args.android_v431_props)),
            "android_v297_props": str(repo_path(args.android_v297_props)),
        },
        "prior": {
            "v620": {"decision": v620.get("decision"), "pass": v620.get("pass")},
        },
        "android_props": props,
        "android_v431_has_dmesg": any(v431_commands.glob("*dmesg*")) if v431_commands.exists() else False,
        "timing": timing,
        "vendor_static": {
            "mdm_helper_service_present": bool(mdm_helper_block),
            "mdm_helper_disabled": "disabled" in mdm_helper_block,
            "mdm_helper_shutdown_critical": "shutdown critical" in mdm_helper_block,
            "mdm_helper_group_system_wakelock_shell": bool(re.search(r"group\s+system\s+wakelock\s+shell", mdm_helper_block)),
            "mdm_launcher_service_present": bool(mdm_launcher_block),
            "mdm_launcher_oneshot": "oneshot" in mdm_launcher_block,
            "init_mdm_sh_baseband_gate": has_line(snapshot, r"baseband=`getprop ro\.baseband`"),
            "init_mdm_sh_starts_mdm_helper": has_line(snapshot, r"start\s+vendor\.mdm_helper"),
            "wcnss_service_start_ref_present": has_line(snapshot, r"start\s+wcnss-service"),
            "wcnss_service_block_present": bool(wcnss_service_block),
            "boot_wlan_permission_only": has_line(snapshot, r"/sys/kernel/boot_wlan/boot_wlan")
            and not has_line(snapshot, r"write\s+/sys/kernel/boot_wlan/boot_wlan"),
        },
        "first_lines": {
            "mdm_helper_service": first_line_with(snapshot, r"service\s+vendor\.mdm_helper"),
            "mdm_launcher_service": first_line_with(snapshot, r"service\s+vendor\.mdm_launcher"),
            "init_mdm_baseband": first_line_with(snapshot, r"baseband=`getprop ro\.baseband`"),
            "init_mdm_start_helper": first_line_with(snapshot, r"start\s+vendor\.mdm_helper"),
            "wcnss_start_ref": first_line_with(snapshot, r"start\s+wcnss-service"),
            "wcnss_service_block": first_line_with(snapshot, r"service\s+wcnss-service"),
        },
        "forbidden_actions": FORBIDDEN_ACTIONS,
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

    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v621-mdm-helper-contract-classifier-plan-ready",
            True,
            "plan-only; run will classify existing Android/vendor init evidence without device contact",
            "run V621 host-only classifier",
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
        "mdm_helper_is_real_candidate": decision == "v621-mdm-helper-contract-same-boot-recapture-required",
        "mdm_launcher_is_wrapper": manifest["vendor_static"]["mdm_launcher_oneshot"],
        "wcnss_service_direct_start_not_supported": (
            manifest["vendor_static"]["wcnss_service_start_ref_present"]
            and not manifest["vendor_static"]["wcnss_service_block_present"]
        ),
        "same_boot_android_timing_needed_before_live_start": manifest["android_v431_has_dmesg"] is False,
        "wifi_bringup_still_blocked": True,
    }
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V621 MDM Helper Contract Classifier",
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
        "## Android Properties",
        "",
        markdown_table(["key", "value"], [[key, value] for key, value in manifest["android_props"].items()]),
        "",
        "## Timing",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in manifest["timing"].items()]),
        "",
        "## First Lines",
        "",
        markdown_table(["key", "line"], [[key, value] for key, value in manifest["first_lines"].items()]),
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
