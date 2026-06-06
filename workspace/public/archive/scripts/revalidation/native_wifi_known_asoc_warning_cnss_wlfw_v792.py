#!/usr/bin/env python3
"""V792 known-ASoC-warning-tolerant CNSS/WLFW readback gate.

V791 reclassified the exact ASoC pm_qos warning as a known Android-parity warning
class, not the first Wi-Fi blocker.  V792 repeats the current clean-DSP + CNSS
readback path but only tolerates that exact signature.  It remains below
service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external
ping, boot image writes, partition writes, and custom kernel flashing.
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
import native_wifi_current_warning_route_classifier_v791 as v791
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v792-known-asoc-warning-cnss-wlfw")
LATEST_POINTER = Path("tmp/wifi/latest-v792-known-asoc-warning-cnss-wlfw.txt")
DEFAULT_V791_MANIFEST = Path("tmp/wifi/v791-current-warning-route-classifier/manifest.json")
DEFAULT_COMPANION_RUNTIME_SEC = 30


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
    parser.add_argument("--v791-manifest", type=Path, default=DEFAULT_V791_MANIFEST)
    parser.add_argument("--v731-manifest", type=Path, default=v788.DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=v788.DEFAULT_V732_MANIFEST)
    parser.add_argument("--v734-manifest", type=Path, default=v788.DEFAULT_V734_MANIFEST)
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
    parser.add_argument("--allow-cnss-start-only", action="store_true")
    parser.add_argument("--allow-cleanup-reboot", action="store_true")
    parser.add_argument("--allow-known-asoc-warning", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def required_flags(args: argparse.Namespace) -> list[str]:
    missing = v788.required_flags(args)
    if not args.allow_known_asoc_warning:
        missing.append("--allow-known-asoc-warning")
    return missing


def run_lower_readback(args: argparse.Namespace, store: EvidenceStore, prep: dict[str, Any]) -> dict[str, Any]:
    v788.v735.configure_base()
    v788.v735.base.PROOF_PREFIX = "/tmp/a90-v792-"
    lower_args = v788.lower_args(args, str(prep["v490_manifest"]))
    manifest = v788.v735.build_manifest(lower_args, store)
    summary = v788.lower_summary(manifest)
    store.write_json("lower-companion-summary.json", summary)
    store.write_text("lower-companion-summary.md", v788.v735.render_summary(manifest))
    return summary


def lower_markers(lower: dict[str, Any]) -> dict[str, int]:
    markers = ((lower.get("live") or {}).get("markers") or {})
    return {key: int(value or 0) for key, value in markers.items() if isinstance(value, int)}


def lower_helper(lower: dict[str, Any]) -> dict[str, Any]:
    return ((lower.get("live") or {}).get("helper") or {})


def lower_safety(lower: dict[str, Any]) -> dict[str, Any]:
    return lower.get("safety") or {}


def warning_guard(args: argparse.Namespace, store: EvidenceStore, lower: dict[str, Any]) -> dict[str, Any]:
    markers = lower_markers(lower)
    parsed = v791.parse_dmesg_events(args.out_dir / "native" / "dmesg-delta.txt")
    events = parsed.get("events") or {}
    exact_known = bool(
        events.get("service74", {}).get("count")
        and events.get("asoc_probe", {}).get("count")
        and events.get("pm_qos_duplicate", {}).get("count")
        and events.get("qos_warning", {}).get("count")
        and events.get("sound_card", {}).get("count")
    )
    guard = {
        "kernel_warning": markers.get("kernel_warning", 0),
        "exact_known_asoc_warning": exact_known,
        "events": {
            name: {
                "count": payload.get("count"),
                "first_time": payload.get("first_time"),
                "first_line": payload.get("first_line"),
            }
            for name, payload in events.items()
            if payload.get("count")
        },
        "gaps_ms": parsed.get("gaps_ms"),
        "selected_lines": parsed.get("selected_lines", [])[:80],
    }
    store.write_json("known-asoc-warning-guard.json", guard)
    store.write_text("known-asoc-warning-lines.txt", "\n".join(guard["selected_lines"]) + ("\n" if guard["selected_lines"] else ""))
    return guard


def add_check(checks: list[dict[str, Any]], name: str, status: str, severity: str, detail: Any, next_step: str) -> None:
    checks.append({
        "name": name,
        "status": status,
        "severity": severity,
        "detail": detail,
        "next_step": next_step,
    })


def build_checks(args: argparse.Namespace,
                 v791_reference: dict[str, Any],
                 flags_missing: list[str],
                 clean: dict[str, Any],
                 prep: dict[str, Any],
                 lower: dict[str, Any],
                 guard: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add_check(
        checks,
        "v791-reference",
        "pass" if v791_reference.get("decision") == "v791-known-asoc-warning-wlfw-route-classified" and v791_reference.get("pass") is True else "blocked",
        "blocker",
        {"decision": v791_reference.get("decision"), "pass": v791_reference.get("pass")},
        "complete V791 before V792",
    )
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", "run V792 with explicit live flags")
        return checks
    add_check(checks, "explicit-live-flags", "pass" if not flags_missing else "blocked", "blocker", {"missing": flags_missing}, "pass all explicit V792 allow flags")
    add_check(checks, "clean-dsp-inline", "pass" if clean.get("decision") == "v787-clean-dsp-arm-only-proof-pass" else "blocked", "blocker", {"decision": clean.get("decision"), "reason": clean.get("reason")}, "do not run CNSS readback until clean-DSP passes")
    add_check(checks, "current-boot-prep", "pass" if prep.get("ready") else "blocked", "blocker", {"v401": prep.get("v401_decision"), "v490": prep.get("v490_decision"), "policy_load": prep.get("v490_policy_load_executed")}, "refresh current V401/V490 after clean-DSP reboot")
    helper = lower_helper(lower)
    add_check(checks, "cnss-start-only-contract", "pass" if helper.get("order") == v788.v735.EXPECTED_ORDER and helper.get("cnss_diag") == 1 and helper.get("cnss_daemon") == 1 and helper.get("all_postflight_safe") == 1 else "blocked", "blocker", {"helper": helper}, "inspect helper transcript before interpreting WLFW absence")
    safety = lower_safety(lower)
    forbidden_keys = (
        "service_manager_start_executed",
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
    )
    add_check(checks, "forbidden-actions", "pass" if all(not safety.get(key) for key in forbidden_keys) else "blocked", "blocker", {key: safety.get(key) for key in forbidden_keys}, "stop if V792 crossed HAL/connect/network boundary")
    markers = lower_markers(lower)
    warning_status = "pass" if not markers.get("kernel_warning") or guard.get("exact_known_asoc_warning") else "blocked"
    add_check(checks, "known-asoc-warning-guard", warning_status, "blocker", {"kernel_warning": markers.get("kernel_warning"), "exact_known": guard.get("exact_known_asoc_warning"), "gaps_ms": guard.get("gaps_ms")}, "only exact ASoC pm_qos warning may be tolerated")
    add_check(checks, "wlfw-readback", "pass" if markers.get("wlfw") or markers.get("bdf") or markers.get("wlan0") or ((lower.get("live") or {}).get("qrtr_readback") or {}).get("service_events") else "finding", "info", {"markers": {key: markers.get(key, 0) for key in ("service_notifier", "mhi", "qca6390", "wlfw", "bdf", "wlan0")}, "qrtr_readback": ((lower.get("live") or {}).get("qrtr_readback") or {})}, "if absent, classify the CNSS/WLFW continuation blocker below HAL/connect")
    cleanup = ((lower.get("live") or {}).get("reboot_cleanup") or {})
    add_check(checks, "cleanup-health", "pass" if cleanup.get("version_seen") and cleanup.get("status_healthy") else "blocked", "blocker", cleanup, "recover stock v724 health before continuing")
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], lower: dict[str, Any], guard: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v792-known-asoc-warning-cnss-wlfw-plan-ready", True, "plan-only; no device command executed", "run V792 with explicit bounded live flags"
    blocked = [check["name"] for check in checks if check["severity"] == "blocker" and check["status"] != "pass"]
    if blocked:
        return "v792-known-asoc-warning-cnss-wlfw-blocked", False, "blocked by " + ", ".join(blocked), "repair blocker before retrying CNSS/WLFW readback"
    markers = lower_markers(lower)
    live = lower.get("live") or {}
    services = live.get("qrtr_services_after_companion") or {}
    readback = live.get("qrtr_readback") or {}
    if markers.get("wlan0") or markers.get("bdf") or markers.get("wlfw") or services.get("69") or readback.get("service_events"):
        return "v792-cnss-wlfw-readback-advance", True, "CNSS readback produced WLFW/service69/BDF/wlan0 evidence below HAL/connect", "capture BDF/fw-ready/interface state before any scan/connect"
    if markers.get("mhi") or markers.get("qca6390"):
        return "v792-cnss-mhi-no-wlfw-classified", True, "CNSS readback reached MHI/QCA6390 but not WLFW/BDF/wlan0", "classify MHI-to-WLFW firmware/runtime gap before HAL/connect"
    helper = lower_helper(lower)
    if helper.get("cnss_daemon") == 1 and guard.get("exact_known_asoc_warning"):
        return "v792-known-warning-cnss-no-wlfw-classified", True, "CNSS daemon and cnss_diag started under the known ASoC warning, but WLFW/service69/BDF/wlan0 remained absent", "route V793 to the current CNSS continuation blocker: cnss-daemon runtime/binder/service-manager parity or ICNSS/WLFW trigger evidence, still below HAL/connect"
    return "v792-cnss-readback-no-advance", True, "CNSS readback completed without WLFW advance", "inspect helper and dmesg evidence before widening"


def render_summary(manifest: dict[str, Any]) -> str:
    lower = manifest.get("lower_readback") or {}
    live = lower.get("live") or {}
    markers = live.get("markers") or {}
    helper = live.get("helper") or {}
    return "\n".join([
        "# V792 Known-ASoC-Warning CNSS/WLFW Readback",
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
            [check["name"], check["status"], check["severity"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Markers",
        "",
        markdown_table(["marker", "count"], [[key, value] for key, value in sorted(markers.items())]) if markers else "- none",
        "",
        "## Helper",
        "",
        markdown_table(["key", "value"], [[key, value] for key, value in sorted(helper.items())]) if helper else "- none",
        "",
        "## Known Warning Guard",
        "",
        markdown_table(["key", "value"], [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in sorted((manifest.get("known_asoc_warning_guard") or {}).items()) if key != "selected_lines"]),
        "",
        "## Safety",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in sorted((manifest.get("safety") or {}).items())]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v791_reference = v788.load_json(args.v791_manifest)
    flags_missing = required_flags(args)
    clean: dict[str, Any] = {}
    prep: dict[str, Any] = {}
    lower: dict[str, Any] = {}
    guard: dict[str, Any] = {}
    clean_captures: list[v787.Capture] = []
    if args.command == "run" and not flags_missing:
        v787_args = argparse.Namespace(**vars(args))
        v787_args.v786_manifest = args.v786_manifest
        v787_args.hide_on_busy = True
        clean_captures, clean_live = v787.collect_live(v787_args, store)
        clean_checks = v787.build_checks(v787_args, "run", v787.load_json(args.v786_manifest), clean_captures, clean_live)
        clean_decision, clean_pass, clean_reason, clean_next = v787.decide("run", clean_checks, clean_live)
        clean = {"decision": clean_decision, "pass": clean_pass, "reason": clean_reason, "next_step": clean_next, "checks": [asdict(check) for check in clean_checks], "live": clean_live}
        if clean_pass:
            prep = v788.run_current_boot_prep(args, store)
        if clean_pass and prep.get("ready"):
            lower = run_lower_readback(args, store, prep)
            guard = warning_guard(args, store, lower)
    checks = build_checks(args, v791_reference, flags_missing, clean, prep, lower, guard)
    decision, passed, reason, next_step = decide(args, checks, lower, guard)
    safety = lower_safety(lower)
    manifest = {
        "cycle": "v792",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "v791_reference": {"decision": v791_reference.get("decision"), "pass": v791_reference.get("pass"), "path": str(repo_path(args.v791_manifest))},
        "clean_dsp_inline": clean,
        "current_boot_prep": prep,
        "lower_readback": lower,
        "known_asoc_warning_guard": guard,
        "checks": checks,
        "safety": {
            "device_commands_executed": args.command == "run" and not flags_missing,
            "clean_dsp_arm_executed": bool(clean_captures and v787.ok(clean_captures, "arm-v641-clean-dsp")),
            "reboot_executed": bool(clean_captures and v787.ok(clean_captures, "reboot-after-arm")),
            "system_mount_executed": bool(prep.get("mountsystem_ok")),
            "selinuxfs_mount_executed": prep.get("v401_decision") == "toybox-selinuxfs-mount-live-executor-run-pass",
            "policy_load_executed": prep.get("v490_policy_load_executed") is True,
            "firmware_mounts_executed": safety.get("firmware_mounts_executed", False),
            "subsys_modem_opened": safety.get("subsys_modem_opened", False),
            "cnss_diag_start_executed": safety.get("cnss_diag_start_executed", False),
            "cnss_daemon_start_executed": safety.get("cnss_daemon_start_executed", False),
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
    print(f"service_manager_start_executed: {manifest['safety']['service_manager_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['safety']['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['safety']['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['safety']['external_ping_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
