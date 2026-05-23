#!/usr/bin/env python3
"""V685 PeripheralManager provider/start-order gap classifier.

This classifier follows V684 by proving whether the A90 vendor image defines a
`vendor.qcom.PeripheralManager` provider path and whether current native init
starts that provider before the CNSS retry. It can optionally capture current
device state read-only. It does not start daemons, service-manager, Wi-Fi HAL,
scan/connect, use credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v685-peripheral-manager-provider")
DEFAULT_V684_MANIFEST = Path("tmp/wifi/v684-cnss-daemon-vndbinder-target/manifest.json")
DEFAULT_V210_RC = Path("tmp/wifi/v210-vendor-asset-classifier/native/commands/cat-etc-init-hw-init.target.rc.txt")
DEFAULT_V209_FIND = Path("tmp/wifi/v209-vendor-ro-mount-probe/native/commands/mounted-find-shallow.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 10.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_SHELL = "/cache/bin/busybox"

FORBIDDEN_ACTIONS = (
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "supplicant or hostapd start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "sysfs or debugfs write",
    "boot image or partition write",
)

LIVE_COMMANDS = {
    "pm-binary-surface": (
        "run",
        DEFAULT_SHELL,
        "sh",
        "-c",
        (
            "BB=/cache/bin/busybox; "
            "for p in "
            "/vendor/bin/pm-service /system/vendor/bin/pm-service /mnt/system/system/vendor/bin/pm-service "
            "/vendor/bin/pm-proxy /system/vendor/bin/pm-proxy /mnt/system/system/vendor/bin/pm-proxy "
            "/dev/vndbinder; do "
            "printf '== %s ==\\n' \"$p\"; \"$BB\" ls -l \"$p\" 2>&1 || true; "
            "done"
        ),
    ),
    "pm-init-block": (
        "run",
        DEFAULT_SHELL,
        "sh",
        "-c",
        (
            "BB=/cache/bin/busybox; "
            "for f in "
            "/vendor/etc/init/hw/init.target.rc /system/vendor/etc/init/hw/init.target.rc "
            "/mnt/system/system/vendor/etc/init/hw/init.target.rc; do "
            "[ -f \"$f\" ] || continue; "
            "printf '== %s ==\\n' \"$f\"; "
            "\"$BB\" grep -n -B 2 -A 12 -E 'Peripheral manager|vendor\\.per_mgr|vendor\\.per_proxy|pm-service|pm-proxy' \"$f\" 2>&1 || true; "
            "done"
        ),
    ),
    "pm-process-surface": (
        "run",
        DEFAULT_SHELL,
        "sh",
        "-c",
        (
            "BB=/cache/bin/busybox; "
            "\"$BB\" ps -A 2>/dev/null | "
            "\"$BB\" grep -E 'pm-service|pm-proxy|vndservicemanager|cnss-daemon|cnss_diag' || true"
        ),
    ),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v684-manifest", type=Path, default=DEFAULT_V684_MANIFEST)
    parser.add_argument("--v210-rc", type=Path, default=DEFAULT_V210_RC)
    parser.add_argument("--v209-find", type=Path, default=DEFAULT_V209_FIND)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--apply", action="store_true", help="capture current device read-only surface")
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


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ready"}


def host_provider_surface(v684: dict[str, Any], rc_text: str, find_text: str, helper_text: str) -> dict[str, Any]:
    return {
        "v684": {
            "decision": v684.get("decision", ""),
            "pass": boolish(v684.get("pass")),
            "next_step": v684.get("next_step", ""),
        },
        "vendor_init": {
            "has_per_mgr_service": bool(re.search(r"service\s+vendor\.per_mgr\s+/vendor/bin/pm-service", rc_text)),
            "has_per_proxy_service": bool(re.search(r"service\s+vendor\.per_proxy\s+/vendor/bin/pm-proxy", rc_text)),
            "per_mgr_class_core": bool(re.search(r"service\s+vendor\.per_mgr[\s\S]{0,160}\n\s+class\s+core", rc_text)),
            "per_mgr_user_system": bool(re.search(r"service\s+vendor\.per_mgr[\s\S]{0,160}\n\s+user\s+system", rc_text)),
            "per_mgr_group_system": bool(re.search(r"service\s+vendor\.per_mgr[\s\S]{0,160}\n\s+group\s+system", rc_text)),
            "per_proxy_disabled": bool(re.search(r"service\s+vendor\.per_proxy[\s\S]{0,180}\n\s+disabled", rc_text)),
            "per_proxy_started_by_per_mgr": bool(
                re.search(r"on\s+property:init\.svc\.vendor\.per_mgr=running[\s\S]{0,120}start\s+vendor\.per_proxy", rc_text)
            ),
        },
        "mounted_vendor_find": {
            "pm_service_path_seen": "/vendor/bin/pm-service" in find_text,
            "pm_proxy_path_seen": "/vendor/bin/pm-proxy" in find_text,
        },
        "helper_gap": {
            "source_has_pm_service_literal": "pm-service" in helper_text,
            "source_has_peripheral_manager_literal": "PeripheralManager" in helper_text,
            "source_has_per_mgr_mode": "per_mgr" in helper_text or "peripheral-manager" in helper_text,
        },
    }


def capture_live(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures = []
    parsed: dict[str, str] = {}
    for name, command in LIVE_COMMANDS.items():
        capture = run_capture(args, name, list(command), timeout=args.timeout)
        captures.append(capture)
        text = strip_cmdv1_text(capture.text) if capture.text else capture.error
        parsed[name] = text
        write_private_text(store.path(f"live/{name}.txt"), text)
    return {
        "commands": [capture_to_manifest(capture) for capture in captures],
        "surface": parse_live_surface(parsed),
    }


def parse_live_surface(parsed: dict[str, str]) -> dict[str, Any]:
    binary_text = parsed.get("pm-binary-surface", "")
    init_text = parsed.get("pm-init-block", "")
    process_text = parsed.get("pm-process-surface", "")
    def ls_has(path_suffix: str) -> bool:
        for line in binary_text.splitlines():
            if path_suffix in line and re.search(r"^[bcdlps-]?[r-][w-][xsStT-]", line.strip()):
                return True
        return False

    process_lines = [
        line for line in process_text.splitlines()
        if "grep -E" not in line and "pm-process-surface" not in line and "BB=/cache/bin/busybox" not in line
    ]
    return {
        "pm_service_exists": ls_has("/pm-service"),
        "pm_proxy_exists": ls_has("/pm-proxy"),
        "vndbinder_exists": ls_has("/dev/vndbinder"),
        "init_per_mgr_seen": "service vendor.per_mgr /vendor/bin/pm-service" in init_text,
        "init_per_proxy_seen": "service vendor.per_proxy /vendor/bin/pm-proxy" in init_text,
        "pm_service_running": any("pm-service" in line for line in process_lines),
        "pm_proxy_running": any("pm-proxy" in line for line in process_lines),
        "vndservicemanager_running": any("vndservicemanager" in line for line in process_lines),
        "cnss_daemon_running": any("cnss-daemon" in line for line in process_lines),
        "matching_process_lines": process_lines[:16],
    }


def build_checks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    host = manifest["host_surface"]
    live = manifest.get("live", {}).get("surface", {})
    checks = [
        {
            "name": "v684-target-candidate-ready",
            "status": "pass" if host["v684"]["pass"] else "blocked",
            "detail": host["v684"],
            "next_step": "refresh V684 if target candidate is stale",
        },
        {
            "name": "vendor-init-defines-peripheral-provider",
            "status": "finding" if all((
                host["vendor_init"]["has_per_mgr_service"],
                host["vendor_init"]["has_per_proxy_service"],
                host["vendor_init"]["per_mgr_user_system"],
                host["vendor_init"]["per_mgr_group_system"],
                host["vendor_init"]["per_proxy_started_by_per_mgr"],
            )) else "review",
            "detail": host["vendor_init"],
            "next_step": "model vendor.per_mgr before another CNSS retry",
        },
        {
            "name": "mounted-vendor-contained-provider-binaries",
            "status": "finding" if all((
                host["mounted_vendor_find"]["pm_service_path_seen"],
                host["mounted_vendor_find"]["pm_proxy_path_seen"],
            )) else "review",
            "detail": host["mounted_vendor_find"],
            "next_step": "verify current boot still exposes provider binaries",
        },
        {
            "name": "current-helper-lacks-provider-start-mode",
            "status": "finding" if not any((
                host["helper_gap"]["source_has_pm_service_literal"],
                host["helper_gap"]["source_has_peripheral_manager_literal"],
                host["helper_gap"]["source_has_per_mgr_mode"],
            )) else "review",
            "detail": host["helper_gap"],
            "next_step": "add a bounded helper mode for vendor.per_mgr/vendor.per_proxy",
        },
    ]
    if manifest["apply"]:
        checks.extend([
            {
                "name": "live-global-provider-materialized",
                "status": "finding" if (
                    live.get("pm_service_exists")
                    and live.get("pm_proxy_exists")
                    and live.get("init_per_mgr_seen")
                    and live.get("init_per_proxy_seen")
                    and live.get("vndbinder_exists")
                ) else "review",
                "detail": live,
                "next_step": "if materialized, proceed to availability query before CNSS retry",
            },
            {
                "name": "live-global-provider-not-materialized",
                "status": "finding" if not any((
                    live.get("pm_service_exists"),
                    live.get("pm_proxy_exists"),
                    live.get("init_per_mgr_seen"),
                    live.get("init_per_proxy_seen"),
                    live.get("vndbinder_exists"),
                )) else "review",
                "detail": live,
                "next_step": "helper must materialize private vendor/dev/vndbinder namespace before starting provider",
            },
            {
                "name": "live-provider-not-running-by-default",
                "status": "finding" if not live.get("pm_service_running") and not live.get("pm_proxy_running") else "review",
                "detail": live,
                "next_step": "start-only proof must explicitly include cleanup and postflight process checks",
            },
        ])
    else:
        checks.append({
            "name": "live-provider-surface",
            "status": "withheld",
            "detail": {"apply": False},
            "next_step": "rerun with --apply when bridge is available",
        })
    return checks


def decide(command: str, apply: bool, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v685-peripheral-manager-provider-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V685 with --apply for current boot read-only provider proof",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v685-peripheral-manager-provider-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh prerequisite evidence before live proof",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    required = {
        "vendor-init-defines-peripheral-provider",
        "mounted-vendor-contained-provider-binaries",
        "current-helper-lacks-provider-start-mode",
    }
    if apply:
        findings_or_review = {check["name"]: check["status"] for check in checks}
        if findings_or_review.get("live-global-provider-materialized") == "finding":
            required |= {"live-global-provider-materialized", "live-provider-not-running-by-default"}
        else:
            required |= {"live-global-provider-not-materialized", "live-provider-not-running-by-default"}
    if required <= findings:
        return (
            "v685-peripheral-manager-provider-start-order-gap",
            True,
            "A90 vendor init defines vendor.per_mgr as /vendor/bin/pm-service and vendor.per_proxy as a property-triggered companion, current native global namespace does not run/materialize that provider surface, and the helper lacks a provider start mode.",
            "implement V686 helper support for bounded vendor.per_mgr/vendor.per_proxy start-only before CNSS retry; still block Wi-Fi HAL, scan/connect, DHCP, and external ping",
        )
    if not apply and required <= findings | {"live-provider-surface"}:
        return (
            "v685-peripheral-manager-provider-host-gap",
            True,
            "host evidence identifies provider/start-order gap; live proof was withheld",
            "rerun V685 with --apply before helper changes",
        )
    return (
        "v685-peripheral-manager-provider-review",
        False,
        "provider/start-order evidence is incomplete",
        "inspect V210/V209/current boot provider paths manually",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v684 = load_json(args.v684_manifest)
    host_surface = host_provider_surface(
        v684,
        read_text(args.v210_rc),
        read_text(args.v209_find),
        read_text(args.helper_source),
    )
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v685",
        "apply": bool(args.apply),
        "host": collect_host_metadata(),
        "inputs": {
            "v684_manifest": str(repo_path(args.v684_manifest)),
            "v210_rc": str(repo_path(args.v210_rc)),
            "v209_find": str(repo_path(args.v209_find)),
            "helper_source": str(repo_path(args.helper_source)),
        },
        "host_surface": host_surface,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": bool(args.apply),
        "device_mutations": False,
        "mount_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    if args.command == "run" and args.apply:
        manifest["live"] = capture_live(args, store)
    checks = build_checks(manifest)
    decision, pass_ok, reason, next_step = decide(args.command, args.apply, checks)
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "routing": {
            "primary_next": "V686 helper mode for vendor.per_mgr/vendor.per_proxy start-only",
            "provider_order": "vendor.per_mgr (/vendor/bin/pm-service) then vendor.per_proxy after init.svc.vendor.per_mgr=running",
            "cnss_retry_policy": "retry cnss-daemon only after provider availability is proven",
            "blocked_until_wlan0": "Wi-Fi HAL, scan/connect, DHCP, routes, external ping",
        },
    })
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    live_rows: list[list[str]] = []
    if "live" in manifest:
        live_rows = [[key, str(value)] for key, value in manifest["live"]["surface"].items()]
    return "\n".join([
        "# V685 PeripheralManager Provider Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- apply: `{manifest['apply']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Live Surface",
        "",
        markdown_table(["item", "value"], live_rows) if live_rows else "- not captured",
        "",
        "## Routing",
        "",
        markdown_table(["item", "value"], [[key, value] for key, value in manifest["routing"].items()]),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
