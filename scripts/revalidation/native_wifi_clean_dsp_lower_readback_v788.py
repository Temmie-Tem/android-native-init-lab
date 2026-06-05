#!/usr/bin/env python3
"""V788 clean-DSP plus current CNSS-only lower readback.

This runner keeps the custom-kernel route paused and stays on stock v724.  It
first replays the V787 clean-DSP arm-only proof, then refreshes the current boot
SELinux runtime surface, then runs the existing V735 CNSS-only lower companion
observer.  It stops below service-manager, Wi-Fi HAL, scan/connect, credential
use, DHCP/routes, external ping, boot image writes, and custom kernel flashing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import native_wifi_clean_dsp_arm_only_v787 as v787
import native_wifi_current_cnss_only_observer_v735 as v735
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v788-clean-dsp-lower-readback")
LATEST_POINTER = Path("tmp/wifi/latest-v788-clean-dsp-lower-readback.txt")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 60.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v124"
DEFAULT_COMPANION_RUNTIME_SEC = 30
DEFAULT_V786_MANIFEST = Path("tmp/wifi/v786-clean-dsp-v724-gap/manifest.json")
DEFAULT_V787_MANIFEST = Path("tmp/wifi/v787-clean-dsp-arm-only/manifest.json")
DEFAULT_V731_MANIFEST = Path("tmp/wifi/v731-firmware-mounted-modem-holder/manifest.json")
DEFAULT_V732_MANIFEST = Path("tmp/wifi/v732-cnss2-mhi-holder-window/manifest.json")
DEFAULT_V734_MANIFEST = Path("tmp/wifi/v734-current-post-sysmon-route/manifest.json")

V401_APPROVAL = "approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up"
V490_APPROVAL = "approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up"

REDACT_PATTERNS = (
    (re.compile(r"made by [^\r\n]+"), "made by [redacted]"),
    (re.compile(r"creator: made by [^\r\n]+"), "creator: made by [redacted]"),
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--companion-runtime-sec", type=int, default=DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--v786-manifest", type=Path, default=DEFAULT_V786_MANIFEST)
    parser.add_argument("--v787-manifest", type=Path, default=DEFAULT_V787_MANIFEST)
    parser.add_argument("--v731-manifest", type=Path, default=DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=DEFAULT_V732_MANIFEST)
    parser.add_argument("--v734-manifest", type=Path, default=DEFAULT_V734_MANIFEST)
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
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def redact(text: str) -> str:
    result = text
    for pattern, replacement in REDACT_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "invalid": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


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
        "--allow-cnss-start-only": args.allow_cnss_start_only,
        "--allow-cleanup-reboot": args.allow_cleanup_reboot,
    }
    return [name for name, present in checks.items() if not present]


def run_host_script(store: EvidenceStore, name: str, command: list[str], timeout: float) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        rc = result.returncode
        output = redact(result.stdout)
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        rc = 124
        output = redact((exc.stdout or "") + (exc.stderr or "") + f"\n[timeout after {timeout}s]\n")
        timed_out = True
    rel = f"host/{name}.txt"
    store.write_text(rel, "$ " + " ".join(command) + "\n" + output.rstrip() + "\n")
    return {
        "name": name,
        "command": command,
        "rc": rc,
        "ok": rc == 0,
        "timeout": timed_out,
        "file": rel,
        "output_tail": output.splitlines()[-12:],
    }


def run_current_boot_prep(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    prep_dir = repo_path(args.out_dir) / "prep"
    v401_dir = prep_dir / "v401"
    v490_dir = prep_dir / "v490"
    steps: list[dict[str, Any]] = []
    captures: list[v787.Capture] = []
    v787.capture_command(args, store, captures, "prep-mountsystem-ro", ["mountsystem", "ro"], 30.0)
    system_ok = v787.ok(captures, "prep-mountsystem-ro")
    v787.send_hide(args)
    v401_command = [
        sys.executable,
        "scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py",
        "--out-dir",
        str(v401_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--approval-phrase",
        V401_APPROVAL,
        "--apply",
        "--assume-yes",
        "run",
    ]
    steps.append(run_host_script(store, "v401-selinuxfs-mount", v401_command, 150.0))
    v787.send_hide(args)
    v490_command = [
        sys.executable,
        "scripts/revalidation/native_selinux_policy_load_proof_v490.py",
        "--out-dir",
        str(v490_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--expect-version",
        args.expect_version,
        "--helper",
        args.helper,
        "--helper-sha256",
        args.helper_sha256,
        "--approval-phrase",
        V490_APPROVAL,
        "--apply",
        "--assume-yes",
        "run",
    ]
    steps.append(run_host_script(store, "v490-policy-load", v490_command, 300.0))
    v401 = load_json(v401_dir / "manifest.json")
    v490 = load_json(v490_dir / "manifest.json")
    return {
        "mountsystem_ok": system_ok,
        "mountsystem_captures": [asdict(capture) for capture in captures],
        "steps": steps,
        "v401_manifest": str(v401_dir / "manifest.json"),
        "v401_decision": v401.get("decision"),
        "v401_pass": v401.get("pass"),
        "v490_manifest": str(v490_dir / "manifest.json"),
        "v490_decision": v490.get("decision"),
        "v490_pass": v490.get("pass"),
        "v490_policy_load_executed": v490.get("policy_load_executed"),
        "ready": bool(
            system_ok
            and v401.get("decision") == "toybox-selinuxfs-mount-live-executor-run-pass"
            and v490.get("decision") == "v490-selinux-policy-load-proof-pass"
            and v490.get("policy_load_executed") is True
        ),
    }


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
        hold_sec=v735.base.DEFAULT_HOLD_SEC,
        companion_runtime_sec=args.companion_runtime_sec,
        qrtr_rx_timeout_sec=v735.base.DEFAULT_QRTR_RX_TIMEOUT_SEC,
        qrtr_rx_poll_sec=v735.base.DEFAULT_QRTR_RX_POLL_SEC,
        v731_manifest=args.v731_manifest,
        v732_manifest=args.v732_manifest,
        v734_manifest=args.v734_manifest,
        v490_manifest=Path(v490_manifest),
        proof_id=None,
        command="run",
    )


def lower_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    live = manifest.get("live") or {}
    helper = live.get("helper_result") or {}
    readback = live.get("qrtr_readback") or {}
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
            "wlan_surface": live.get("wlan_surface"),
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
                "cnss_diag",
                "cnss_daemon",
                "service_manager",
                "wifi_hal",
                "wificond",
                "scan_connect_linkup",
                "external_ping",
                "result",
            )},
            "qrtr_readback": {key: readback.get(key) for key in (
                "allowed",
                "send_attempted",
                "result",
                "service_events",
                "end_of_list",
                "timeouts",
                "qmi_attempted",
            )},
            "reboot_cleanup": live.get("reboot_cleanup"),
        },
        "safety": {
            "firmware_mounts_executed": manifest.get("firmware_mounts_executed"),
            "subsys_modem_opened": manifest.get("subsys_modem_opened"),
            "lower_companion_start_executed": manifest.get("lower_companion_start_executed"),
            "cnss_diag_start_executed": manifest.get("cnss_diag_start_executed"),
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


def run_lower_readback(args: argparse.Namespace, store: EvidenceStore, prep: dict[str, Any]) -> dict[str, Any]:
    v735.configure_base()
    v735.base.PROOF_PREFIX = "/tmp/a90-v788-"
    largs = lower_args(args, str(prep["v490_manifest"]))
    manifest = v735.build_manifest(largs, store)
    summary = lower_summary(manifest)
    store.write_json("lower-companion-summary.json", summary)
    store.write_text("lower-companion-summary.md", v735.render_summary(manifest))
    return summary


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str],
              next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, evidence, next_step))


def build_checks(args: argparse.Namespace,
                 v787_reference: dict[str, Any],
                 flags_missing: list[str],
                 clean_live: dict[str, Any],
                 prep: dict[str, Any],
                 lower: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    add_check(
        checks,
        "v787-reference",
        "pass" if v787_reference.get("decision") == "v787-clean-dsp-arm-only-proof-pass" and v787_reference.get("pass") is True else "blocked",
        "blocker",
        f"decision={v787_reference.get('decision')} pass={v787_reference.get('pass')}",
        [str(repo_path(args.v787_manifest))],
        "complete V787 before V788",
    )
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run V788 with explicit bounded live flags")
        return checks
    add_check(
        checks,
        "explicit-live-flags",
        "pass" if not flags_missing else "blocked",
        "blocker",
        "missing=" + ",".join(flags_missing),
        [],
        "pass all explicit V788 allow flags",
    )
    add_check(
        checks,
        "clean-dsp-inline",
        "pass" if clean_live.get("decision") == "v787-clean-dsp-arm-only-proof-pass" else "blocked",
        "blocker",
        f"decision={clean_live.get('decision')} reason={clean_live.get('reason')}",
        ["manifest.clean_dsp_inline"],
        "do not run lower companion until clean-DSP proof passes in the same cycle",
    )
    add_check(
        checks,
        "current-boot-selinux-prep",
        "pass" if prep.get("ready") else "blocked",
        "blocker",
        f"v401={prep.get('v401_decision')} v490={prep.get('v490_decision')} policy_load={prep.get('v490_policy_load_executed')}",
        [prep.get("v401_manifest", ""), prep.get("v490_manifest", "")],
        "refresh V401/V490 after the clean-DSP reboot",
    )
    add_check(
        checks,
        "lower-companion-readback",
        "pass" if lower.get("pass") is True else "blocked",
        "blocker",
        f"decision={lower.get('decision')} reason={lower.get('reason')}",
        ["lower-companion-summary.json"],
        "inspect lower companion summary before retrying or widening",
    )
    safety = lower.get("safety") or {}
    forbidden_clear = all(not safety.get(key) for key in (
        "service_manager_start_executed",
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
    ))
    add_check(
        checks,
        "forbidden-actions",
        "pass" if forbidden_clear else "blocked",
        "blocker",
        json.dumps({key: safety.get(key) for key in sorted(safety)}, sort_keys=True),
        ["lower-companion-summary.json"],
        "stop if V788 crossed service-manager/HAL/connect/network boundary",
    )
    lower_live = lower.get("live") or {}
    markers = lower_live.get("markers") or {}
    add_check(
        checks,
        "warning-boundary",
        "pass" if not markers.get("kernel_warning") else "blocked",
        "blocker",
        f"kernel_warning={markers.get('kernel_warning')}",
        ["lower-companion-summary.json"],
        "do not repeat if lower companion produced warning boundary",
    )
    cleanup = lower_live.get("reboot_cleanup") or {}
    add_check(
        checks,
        "cleanup-health",
        "pass" if cleanup.get("version_seen") and cleanup.get("status_healthy") else "blocked",
        "blocker",
        json.dumps(cleanup, sort_keys=True),
        ["lower-companion-summary.json"],
        "recover stock v724 health before continuing",
    )
    return checks


def decide(args: argparse.Namespace, checks: list[Check], lower: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v788-clean-dsp-lower-readback-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V788 clean-DSP plus CNSS-only lower readback with explicit live flags",
        )
    blocked = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blocked:
        return (
            "v788-clean-dsp-lower-readback-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "inspect V788 evidence and recover stock v724 before retrying",
        )
    live = lower.get("live") or {}
    markers = live.get("markers") or {}
    services = live.get("qrtr_services_after_companion") or {}
    readback = live.get("qrtr_readback") or {}
    if markers.get("wlan0") or markers.get("wlfw") or services.get("69") or readback.get("service_events"):
        return (
            "v788-clean-dsp-lower-readback-wlfw-advance",
            True,
            "clean-DSP plus CNSS-only lower readback produced WLFW/service69 or wlan0 evidence",
            "capture BDF/fw-ready/interface state before any scan/connect",
        )
    if markers.get("mhi") or markers.get("qca6390"):
        return (
            "v788-clean-dsp-lower-readback-mhi-advance",
            True,
            "clean-DSP plus CNSS-only lower readback produced MHI/QCA6390 evidence but no WLFW",
            "classify MHI-to-WLFW gap before HAL/connect",
        )
    if markers.get("service_notifier") or markers.get("wlan_pd") or services.get("180") or services.get("74"):
        return (
            "v788-clean-dsp-lower-readback-service-publication",
            True,
            "clean-DSP plus CNSS-only lower readback produced service publication evidence but no MHI/WLFW",
            "classify WLAN-PD-to-MHI gap before HAL/connect",
        )
    if markers.get("qrtr_tx") or markers.get("sysmon_qmi"):
        return (
            "v788-clean-dsp-lower-readback-sysmon-gap",
            True,
            "clean-DSP plus CNSS-only lower readback restored QRTR TX/sysmon but no service publication, MHI, WLFW, or wlan0",
            "focus next on modem/WLAN-PD publication or ICNSS trigger while staying below HAL/connect",
        )
    return (
        "v788-clean-dsp-lower-readback-no-advance",
        True,
        "clean-DSP plus CNSS-only lower readback completed but did not advance beyond QRTR RX",
        "compare current V733/V735 helper transcript before widening live actions",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    lower = manifest.get("lower_readback") or {}
    live = lower.get("live") or {}
    marker_rows = [[name, str(value)] for name, value in sorted((live.get("markers") or {}).items())]
    safety = manifest.get("safety") or {}
    return "\n".join([
        "# V788 Clean-DSP Lower Readback",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- evidence: `{manifest['evidence_dir']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], ", ".join(check["evidence"]), check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Lower Markers",
        "",
        markdown_table(["marker", "count"], marker_rows) if marker_rows else "- none",
        "",
        "## Safety",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in sorted(safety.items())]),
        "",
        "## Interpretation",
        "",
        "- V788 is still not a Wi-Fi scan/connect gate.",
        "- CNSS-only lower companion start is allowed; service-manager, HAL, credentials, DHCP, routes, external ping, and custom kernel flashing remain blocked.",
        "- If no WLFW/service69/wlan0 appears, the next blocker remains below Android Wi-Fi framework.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v787_reference = load_json(args.v787_manifest)
    flags_missing = required_flags(args)
    clean_summary: dict[str, Any] = {}
    prep: dict[str, Any] = {}
    lower: dict[str, Any] = {}
    clean_captures: list[v787.Capture] = []
    if args.command == "run" and not flags_missing:
        v787_args = argparse.Namespace(**vars(args))
        v787_args.v786_manifest = args.v786_manifest
        v787_args.hide_on_busy = True
        clean_captures, clean_live = v787.collect_live(v787_args, store)
        clean_checks = v787.build_checks(v787_args, "run", v787.load_json(args.v786_manifest), clean_captures, clean_live)
        clean_decision, clean_pass, clean_reason, clean_next = v787.decide("run", clean_checks, clean_live)
        clean_summary = {
            "decision": clean_decision,
            "pass": clean_pass,
            "reason": clean_reason,
            "next_step": clean_next,
            "checks": [asdict(check) for check in clean_checks],
            "live": clean_live,
        }
        if clean_pass:
            prep = run_current_boot_prep(args, store)
        if clean_pass and prep.get("ready"):
            lower = run_lower_readback(args, store, prep)
    checks = build_checks(args, v787_reference, flags_missing, clean_summary, prep, lower)
    decision, passed, reason, next_step = decide(args, checks, lower)
    lower_safety = (lower.get("safety") or {}) if lower else {}
    manifest = {
        "cycle": "v788",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "evidence_dir": str(store.run_dir.relative_to(repo_path("."))),
        "v787_reference": {
            "decision": v787_reference.get("decision"),
            "pass": v787_reference.get("pass"),
            "path": str(repo_path(args.v787_manifest)),
        },
        "clean_dsp_inline": clean_summary,
        "current_boot_prep": prep,
        "lower_readback": lower,
        "checks": [asdict(check) for check in checks],
        "safety": {
            "device_commands_executed": args.command == "run" and not flags_missing,
            "clean_dsp_arm_executed": bool(clean_captures and v787.ok(clean_captures, "arm-v641-clean-dsp")),
            "reboot_executed": bool(clean_captures and v787.ok(clean_captures, "reboot-after-arm")),
            "system_mount_executed": bool(prep.get("mountsystem_ok")),
            "selinuxfs_mount_executed": prep.get("v401_decision") == "toybox-selinuxfs-mount-live-executor-run-pass",
            "policy_load_executed": prep.get("v490_policy_load_executed") is True,
            "firmware_mounts_executed": lower_safety.get("firmware_mounts_executed", False),
            "subsys_modem_opened": lower_safety.get("subsys_modem_opened", False),
            "cnss_diag_start_executed": lower_safety.get("cnss_diag_start_executed", False),
            "cnss_daemon_start_executed": lower_safety.get("cnss_daemon_start_executed", False),
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
