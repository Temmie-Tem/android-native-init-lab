#!/usr/bin/env python3
"""V790 clean-DSP lower-only warning isolation.

V789 classified the V788 warning as a new audio/deferred-probe pm_qos boundary
after service-notifier activity.  V790 repeats the clean-DSP and current
SELinux prep path, but intentionally omits cnss_diag and cnss-daemon.  It stays
below service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
external ping, boot image writes, and custom kernel flashing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import native_wifi_clean_dsp_arm_only_v787 as v787
import native_wifi_clean_dsp_lower_readback_v788 as v788
import native_wifi_holder_lower_companion_v733 as v733
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v790-clean-dsp-lower-only")
LATEST_POINTER = Path("tmp/wifi/latest-v790-clean-dsp-lower-only.txt")
DEFAULT_V789_MANIFEST = Path("tmp/wifi/v789-v788-warning-classifier/manifest.json")
DEFAULT_COMPANION_RUNTIME_SEC = 12


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v788.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v788.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=v788.DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=v788.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--busybox", default=v788.DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=v788.DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=v788.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=v788.DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=v788.DEFAULT_HELPER_MARKER)
    parser.add_argument("--companion-runtime-sec", type=int, default=DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--v786-manifest", type=Path, default=v788.DEFAULT_V786_MANIFEST)
    parser.add_argument("--v787-manifest", type=Path, default=v788.DEFAULT_V787_MANIFEST)
    parser.add_argument("--v789-manifest", type=Path, default=DEFAULT_V789_MANIFEST)
    parser.add_argument("--v731-manifest", type=Path, default=v788.DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=v788.DEFAULT_V732_MANIFEST)
    parser.add_argument("--wait-timeout", type=float, default=120.0)
    parser.add_argument("--wait-interval", type=float, default=3.0)
    parser.add_argument("--allow-arm-clean-dsp", action="store_true")
    parser.add_argument("--allow-reboot", action="store_true")
    parser.add_argument("--allow-cleanup-umount", action="store_true")
    parser.add_argument("--allow-system-mount", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-policy-load", action="store_true")
    parser.add_argument("--allow-firmware-mounts", action="store_true")
    parser.add_argument("--allow-subsys-modem-holder", action="store_true")
    parser.add_argument("--allow-lower-companion", action="store_true")
    parser.add_argument("--allow-cleanup-reboot", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def required_flags(args: argparse.Namespace) -> list[str]:
    checks = {
        "--assume-yes": args.assume_yes,
        "--allow-arm-clean-dsp": args.allow_arm_clean_dsp,
        "--allow-reboot": args.allow_reboot,
        "--allow-cleanup-umount": args.allow_cleanup_umount,
        "--allow-system-mount": args.allow_system_mount,
        "--allow-selinuxfs-mount": args.allow_selinuxfs_mount,
        "--allow-policy-load": args.allow_policy_load,
        "--allow-firmware-mounts": args.allow_firmware_mounts,
        "--allow-subsys-modem-holder": args.allow_subsys_modem_holder,
        "--allow-lower-companion": args.allow_lower_companion,
        "--allow-cleanup-reboot": args.allow_cleanup_reboot,
    }
    return [name for name, present in checks.items() if not present]


def lower_args(args: argparse.Namespace, v490_manifest: str) -> argparse.Namespace:
    return argparse.Namespace(
        out_dir=args.out_dir,
        host=args.host,
        port=args.port,
        timeout=args.timeout,
        toybox=args.toybox,
        busybox=args.busybox,
        helper=args.helper,
        helper_sha256=args.helper_sha256,
        helper_marker=args.helper_marker,
        expect_version=args.expect_version,
        hold_sec=v733.DEFAULT_HOLD_SEC,
        companion_runtime_sec=args.companion_runtime_sec,
        qrtr_rx_timeout_sec=v733.DEFAULT_QRTR_RX_TIMEOUT_SEC,
        qrtr_rx_poll_sec=v733.DEFAULT_QRTR_RX_POLL_SEC,
        v731_manifest=args.v731_manifest,
        v732_manifest=args.v732_manifest,
        v490_manifest=Path(v490_manifest),
        proof_id=None,
        command="run",
    )


def lower_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    live = manifest.get("live") or {}
    helper = live.get("helper_result") or {}
    counts = ((live.get("markers") or {}).get("counts") or {})
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "reason": manifest.get("reason"),
        "next_step": manifest.get("next_step"),
        "checks": manifest.get("checks", []),
        "live": {
            "holder_opened": live.get("holder_opened"),
            "mss": [live.get("mss_before"), live.get("mss_after_holder"), live.get("mss_after_companion")],
            "mdm3": [live.get("mdm3_before"), live.get("mdm3_after_holder"), live.get("mdm3_after_companion")],
            "qrtr_rx_seen": (live.get("qrtr_rx_wait") or {}).get("seen"),
            "qrtr_services_after_companion": live.get("qrtr_services_after_companion"),
            "markers": {key: counts.get(key, 0) for key in (
                "qrtr_rx",
                "qrtr_tx",
                "sysmon_qmi",
                "service_notifier",
                "wlan_pd",
                "mhi",
                "qca6390",
                "wlfw",
                "bdf",
                "wlan0",
                "kernel_warning",
            )},
            "helper": {key: helper.get(key) for key in (
                "mode",
                "order",
                "child_started",
                "all_observable",
                "all_postflight_safe",
                "cnss_daemon",
                "service_manager",
                "wifi_hal",
                "wificond",
                "scan_connect_linkup",
                "external_ping",
                "result",
            )},
            "reboot_cleanup": live.get("reboot_cleanup"),
        },
        "safety": {
            "firmware_mounts_executed": manifest.get("firmware_mounts_executed"),
            "subsys_modem_opened": manifest.get("subsys_modem_opened"),
            "lower_companion_start_executed": manifest.get("lower_companion_start_executed"),
            "cnss_daemon_start_executed": manifest.get("cnss_daemon_start_executed"),
            "service_manager_start_executed": manifest.get("service_manager_start_executed"),
            "wifi_hal_start_executed": manifest.get("wifi_hal_start_executed"),
            "scan_connect_executed": manifest.get("scan_connect_executed"),
            "credential_use_executed": manifest.get("credential_use_executed"),
            "dhcp_route_executed": manifest.get("dhcp_route_executed"),
            "external_ping_executed": manifest.get("external_ping_executed"),
            "reboot_cleanup_executed": manifest.get("reboot_cleanup_executed"),
        },
    }


def run_lower_only(args: argparse.Namespace, store: EvidenceStore, prep: dict[str, Any]) -> dict[str, Any]:
    v733.PROOF_PREFIX = "/tmp/a90-v790-"
    manifest = v733.build_manifest(lower_args(args, str(prep["v490_manifest"])), store)
    summary = lower_summary(manifest)
    store.write_json("lower-only-summary.json", summary)
    store.write_text("lower-only-summary.md", v733.render_summary(manifest))
    return summary


def add_check(checks: list[dict[str, Any]], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append({"name": name, "status": status, "severity": severity, "detail": detail, "next_step": next_step})


def build_checks(args: argparse.Namespace,
                 v789: dict[str, Any],
                 flags_missing: list[str],
                 clean: dict[str, Any],
                 prep: dict[str, Any],
                 lower: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add_check(
        checks,
        "v789-reference",
        "pass" if v789.get("decision") == "v789-pm-qos-audio-deferred-probe-boundary-classified" and v789.get("pass") is True else "blocked",
        "blocker",
        f"decision={v789.get('decision')} pass={v789.get('pass')}",
        "complete V789 before V790",
    )
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", "run V790 with explicit live flags")
        return checks
    add_check(checks, "explicit-live-flags", "pass" if not flags_missing else "blocked", "blocker", "missing=" + ",".join(flags_missing), "pass all V790 allow flags")
    add_check(checks, "clean-dsp-inline", "pass" if clean.get("decision") == "v787-clean-dsp-arm-only-proof-pass" else "blocked", "blocker", f"decision={clean.get('decision')}", "do not run lower-only until clean-DSP passes")
    add_check(checks, "current-boot-prep", "pass" if prep.get("ready") else "blocked", "blocker", f"v401={prep.get('v401_decision')} v490={prep.get('v490_decision')}", "refresh current V401/V490 after clean-DSP reboot")
    add_check(checks, "lower-only-readback", "pass" if lower.get("pass") is True else "blocked", "blocker", f"decision={lower.get('decision')} reason={lower.get('reason')}", "inspect lower-only evidence")
    safety = lower.get("safety") or {}
    forbidden_clear = all(not safety.get(key) for key in (
        "cnss_daemon_start_executed",
        "service_manager_start_executed",
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
    ))
    add_check(checks, "forbidden-actions", "pass" if forbidden_clear else "blocked", "blocker", json.dumps(safety, sort_keys=True), "stop if lower-only crossed CNSS/HAL/connect boundary")
    markers = ((lower.get("live") or {}).get("markers") or {})
    add_check(checks, "warning-boundary", "pass" if not markers.get("kernel_warning") else "blocked", "blocker", f"kernel_warning={markers.get('kernel_warning')}", "if warning recurs, classify clean-DSP/lower/audio ordering")
    cleanup = ((lower.get("live") or {}).get("reboot_cleanup") or {})
    add_check(checks, "cleanup-health", "pass" if cleanup.get("version_seen") and cleanup.get("status_healthy") else "blocked", "blocker", json.dumps(cleanup, sort_keys=True), "recover stock v724 health")
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], lower: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v790-clean-dsp-lower-only-plan-ready", True, "plan-only; no device command executed", "run lower-only warning isolation with explicit flags"
    blocked = [check["name"] for check in checks if check["severity"] == "blocker" and check["status"] != "pass"]
    if blocked:
        return "v790-clean-dsp-lower-only-blocked", False, "blocked by " + ", ".join(blocked), "inspect V790 evidence before any retry"
    live = lower.get("live") or {}
    markers = live.get("markers") or {}
    if markers.get("service_notifier") or markers.get("wlan_pd"):
        return "v790-clean-dsp-lower-only-service-advance", True, "lower-only replay advanced service publication without CNSS or warning", "classify whether CNSS can be reintroduced with a tighter guard"
    if markers.get("qrtr_tx") or markers.get("sysmon_qmi"):
        return "v790-clean-dsp-lower-only-warning-free-sysmon-gap", True, "lower-only replay was warning-free and restored QRTR/sysmon only", "next compare V790 with V788 to isolate CNSS/audio boundary before CNSS retry"
    return "v790-clean-dsp-lower-only-no-advance", True, "lower-only replay completed warning-free but did not advance beyond QRTR RX", "compare helper output before retrying CNSS"


def render_summary(manifest: dict[str, Any]) -> str:
    lower = manifest.get("lower_only") or {}
    markers = ((lower.get("live") or {}).get("markers") or {})
    return "\n".join([
        "# V790 Clean-DSP Lower-Only Warning Isolation",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Markers",
        "",
        markdown_table(["marker", "count"], [[key, value] for key, value in sorted(markers.items())]) if markers else "- none",
        "",
        "## Safety",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in sorted((manifest.get("safety") or {}).items())]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v789 = v788.load_json(args.v789_manifest)
    flags_missing = required_flags(args)
    clean: dict[str, Any] = {}
    prep: dict[str, Any] = {}
    lower: dict[str, Any] = {}
    captures: list[v787.Capture] = []
    if args.command == "run" and not flags_missing:
        v787_args = argparse.Namespace(**vars(args))
        v787_args.v786_manifest = args.v786_manifest
        v787_args.hide_on_busy = True
        captures, clean_live = v787.collect_live(v787_args, store)
        clean_checks = v787.build_checks(v787_args, "run", v787.load_json(args.v786_manifest), captures, clean_live)
        clean_decision, clean_pass, clean_reason, clean_next = v787.decide("run", clean_checks, clean_live)
        clean = {"decision": clean_decision, "pass": clean_pass, "reason": clean_reason, "next_step": clean_next, "checks": [asdict(check) for check in clean_checks], "live": clean_live}
        if clean_pass:
            prep = v788.run_current_boot_prep(args, store)
        if clean_pass and prep.get("ready"):
            lower = run_lower_only(args, store, prep)
    checks = build_checks(args, v789, flags_missing, clean, prep, lower)
    decision, passed, reason, next_step = decide(args, checks, lower)
    lower_safety = lower.get("safety") or {}
    manifest = {
        "cycle": "v790",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "v789_reference": {"decision": v789.get("decision"), "pass": v789.get("pass"), "path": str(repo_path(args.v789_manifest))},
        "clean_dsp_inline": clean,
        "current_boot_prep": prep,
        "lower_only": lower,
        "checks": checks,
        "safety": {
            "device_commands_executed": args.command == "run" and not flags_missing,
            "clean_dsp_arm_executed": bool(captures and v787.ok(captures, "arm-v641-clean-dsp")),
            "reboot_executed": bool(captures and v787.ok(captures, "reboot-after-arm")),
            "system_mount_executed": bool(prep.get("mountsystem_ok")),
            "selinuxfs_mount_executed": prep.get("v401_decision") == "toybox-selinuxfs-mount-live-executor-run-pass",
            "policy_load_executed": prep.get("v490_policy_load_executed") is True,
            "firmware_mounts_executed": lower_safety.get("firmware_mounts_executed", False),
            "subsys_modem_opened": lower_safety.get("subsys_modem_opened", False),
            "lower_companion_start_executed": lower_safety.get("lower_companion_start_executed", False),
            "cnss_diag_start_executed": False,
            "cnss_daemon_start_executed": False,
            "service_manager_start_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "boot_image_write_executed": False,
            "partition_write_executed": False,
            "custom_kernel_flash_executed": False,
        },
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    store.mkdir("host")
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    print(f"cnss_daemon_start_executed: {manifest['safety']['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['safety']['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['safety']['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['safety']['external_ping_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
