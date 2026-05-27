#!/usr/bin/env python3
"""V1125 PM-service early-exit trace under helper-private firmware mounts."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_pm_service_instruction_trace_live_v1082 as tracebase
import native_wifi_pm_service_success_path_trace_live_v1086 as v1086
import native_wifi_pm_service_trigger_observer_live_v1066 as base
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1125-private-firmware-pm-service-early-exit-trace")
LATEST_POINTER = Path("tmp/wifi/latest-v1125-private-firmware-pm-service-early-exit-trace.txt")
DEFAULT_V1124_MANIFEST = Path("tmp/wifi/v1124-private-firmware-pm-observer-live/manifest.json")
DEFAULT_EXECNS_HELPER_SHA256 = "65fe14f0d7095786d8228750e309e0a1b5d40c33825d1debb87870d9caba0ef3"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v212"
DEFAULT_PM_BINARY = "/mnt/vendor/bin/pm-service"
DEFAULT_VENDOR_MOUNT = tracebase.DEFAULT_VENDOR_MOUNT
DEFAULT_VENDOR_BLOCK = tracebase.DEFAULT_VENDOR_BLOCK
DEFAULT_TRACEFS_ROOT = tracebase.DEFAULT_TRACEFS_ROOT
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1125"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1125/private-firmware-pm-observer.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1125/private-firmware-pm-tracefs-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1125/private-firmware-pm-observer-output.txt"
EXPECTED_V1124_DECISION = "v1124-private-firmware-provider-regressed"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def repo_path(path: Path | str) -> Path:
    path = Path(path)
    return path if path.is_absolute() else Path.cwd() / path


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def pm_observer_private_firmware_child_command(args: argparse.Namespace) -> list[str]:
    command = base.helper_command(args)
    if len(command) >= 3 and command[0] == args.toybox and command[1] == "timeout":
        command = command[3:]
    command.append("--pm-observer-private-firmware-mounts")
    return command


def patch_tracebase() -> None:
    v1086.patch_tracebase()
    tracebase.pm_observer_child_command = pm_observer_private_firmware_child_command


def required_flags(args: argparse.Namespace) -> list[str]:
    return tracebase.required_flags(args)


def branch_from_counts(counts: dict[str, int]) -> str:
    return v1086.classify_branch(counts)


def decide(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1125-private-firmware-pm-service-early-exit-trace-plan-ready",
            True,
            "plan-only; no tracefs write, PM actor, CNSS actor, or Wi-Fi action executed",
            "run V1125 with explicit tracefs/PM observer allow flags",
        )

    v1124 = manifest.get("v1124") or {}
    if v1124.get("decision") != EXPECTED_V1124_DECISION or not v1124.get("pass"):
        return (
            "v1125-v1124-predecessor-missing",
            False,
            f"unexpected V1124 decision={v1124.get('decision')!r} pass={v1124.get('pass')}",
            "refresh V1124 before tracing private-firmware early exit",
        )
    missing = required_flags(args)
    if missing:
        return (
            "v1125-private-firmware-trace-approval-required",
            False,
            "missing explicit flags: " + ", ".join(missing),
            "rerun with all V1125 allow flags",
        )

    analysis = manifest.get("analysis") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    post = analysis.get("post_surface") or {}
    contract = tracefs.get("pm_contract") or {}
    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1125-execns-helper-sha-mismatch", False, "remote execns helper is not v212", "deploy helper v212")
    if not analysis.get("pm_binary_visible"):
        return ("v1125-pm-service-not-visible", False, "read-only vendor mount did not expose pm-service", "repair vendor mount before retry")
    if tracefs.get("result") != "tracefs-uprobe-pass":
        return ("v1125-tracefs-uprobe-failed", False, f"tracefs result={tracefs.get('result')}", "inspect tracefs collector transcript")
    if tracefs.get("register_failures") or tracefs.get("enable_failures") or tracefs.get("cleanup_failures"):
        return ("v1125-tracefs-uprobe-cleanup-review", False, "register/enable/cleanup failures present", "inspect tracefs cleanup before retry")
    if tracefs.get("forbidden_true"):
        return ("v1125-forbidden-action-observed", False, f"forbidden={tracefs.get('forbidden_true')}", "stop and audit helper contract")
    if post.get("forbidden_actor_hits") or post.get("wifi_link_hits"):
        return ("v1125-postflight-safety-review", False, "forbidden actors or Wi-Fi link appeared", "cleanup device before continuing")
    if contract.get("private_firmware_mounts_requested") != "1":
        return ("v1125-private-firmware-flag-not-applied", False, "helper did not report private firmware request", "repair child command")
    if contract.get("private_firmware_mnt_mounted") != "1" or contract.get("private_firmware_modem_mounted") != "1":
        return (
            "v1125-private-firmware-mount-failed",
            False,
            f"firmware_mnt={contract.get('private_firmware_mnt_mounted')} firmware_modem={contract.get('private_firmware_modem_mounted')}",
            "inspect helper setup_error and partition visibility",
        )
    counts = tracefs.get("counts") or {}
    if counts.get("pm_success_branch_after_get_system_info", 0) <= 0:
        return ("v1125-pm-service-success-branch-not-hit", False, f"counts={counts}", "verify pm-service offsets and private mdmdetect surface")
    branch = branch_from_counts(counts)
    if branch == "post-mdmdetect-terminal-branch-missing":
        return ("v1125-pm-service-terminal-branch-missing", False, f"counts={counts}", "add narrower offsets around PM-service terminal branch")
    return (
        f"v1125-private-firmware-{branch}",
        True,
        f"PM-service private-firmware branch captured: {branch}",
        "route next gate from the captured PM-service terminal branch",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1124 = load_json(args.v1124_manifest)
    patch_tracebase()
    manifest: dict[str, Any] = {
        "cycle": "v1125",
        "generated_at": now_iso(),
        "command": args.command,
        "v1124": {
            "manifest": str(repo_path(args.v1124_manifest)),
            "decision": v1124.get("decision", ""),
            "pass": bool(v1124.get("pass")),
        },
        "event_specs": [f"{label}:0x{offset}" for label, offset in v1086.EVENT_SPECS],
        "steps": [],
        "analysis": {},
        "tracefs_write_executed": False,
        "bpf_attach_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
    }
    if (
        args.command == "run"
        and not required_flags(args)
        and v1124.get("decision") == EXPECTED_V1124_DECISION
        and bool(v1124.get("pass"))
    ):
        steps, analysis = tracebase.run_live(args, store)
        manifest["steps"] = steps
        manifest["analysis"] = analysis
        manifest["tracefs_write_executed"] = True
        manifest["pm_actor_executed"] = True
        tracefs = analysis.get("tracefs_uprobe") or {}
        contract = tracefs.get("pm_contract") or {}
        manifest["cnss_daemon_start_executed"] = contract.get("cnss_daemon_start_executed") == "1"
        manifest["wifi_hal_start_executed"] = contract.get("wifi_hal_start_executed") == "1"
        manifest["scan_connect_executed"] = contract.get("scan_connect_linkup") == "1"
        manifest["external_ping_executed"] = contract.get("external_ping") == "1"
    decision, passed, reason, next_step = decide(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    counts = tracefs.get("counts") or {}
    contract = tracefs.get("pm_contract") or {}
    branch = branch_from_counts(counts) if counts else ""
    step_rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    return "\n".join([
        "# V1125 Private Firmware PM Service Early Exit Trace",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- branch_classification: `{branch}`",
        f"- private_firmware_mounts_requested: `{contract.get('private_firmware_mounts_requested', '')}`",
        f"- private_firmware_mnt_mounted: `{contract.get('private_firmware_mnt_mounted', '')}`",
        f"- private_firmware_modem_mounted: `{contract.get('private_firmware_modem_mounted', '')}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Tracefs Uprobe",
        "",
        f"- result: `{tracefs.get('result', '')}`",
        f"- hit_count: `{tracefs.get('hit_count', '')}`",
        f"- trace_line_count: `{tracefs.get('trace_line_count', '')}`",
        f"- child_rc: `{tracefs.get('child_rc', '')}`",
        "",
        "```json",
        json.dumps(counts, indent=2, sort_keys=True),
        "```",
        "",
        "## Steps",
        "",
        base.markdown_table(["name", "ok", "rc", "duration_sec", "file"], step_rows),
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=base.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=base.DEFAULT_PORT)
    parser.add_argument("--device-ip", default=base.DEFAULT_DEVICE_IP)
    parser.add_argument("--tcp-port", type=int, default=base.DEFAULT_TCP_PORT)
    parser.add_argument("--tcp-timeout", type=float, default=90.0)
    parser.add_argument("--busybox", default=base.DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=base.DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=base.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_EXECNS_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_EXECNS_HELPER_MARKER)
    parser.add_argument("--v1124-manifest", type=Path, default=DEFAULT_V1124_MANIFEST)
    parser.add_argument("--property-root", default=base.DEFAULT_PROPERTY_ROOT)
    parser.add_argument("--helper-timeout-sec", type=int, default=4)
    parser.add_argument("--toybox-timeout-sec", type=int, default=18)
    parser.add_argument("--tracefs-duration-sec", type=int, default=18)
    parser.add_argument("--vendor-block", default=DEFAULT_VENDOR_BLOCK)
    parser.add_argument("--vendor-mount", default=DEFAULT_VENDOR_MOUNT)
    parser.add_argument("--pm-binary", default=DEFAULT_PM_BINARY)
    parser.add_argument("--tracefs-root", default=DEFAULT_TRACEFS_ROOT)
    parser.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    parser.add_argument("--child-script", default=DEFAULT_CHILD_SCRIPT)
    parser.add_argument("--collector-script", default=DEFAULT_COLLECTOR_SCRIPT)
    parser.add_argument("--child-output", default=DEFAULT_CHILD_OUTPUT)
    parser.add_argument("--allow-tracefs-mount", action="store_true")
    parser.add_argument("--allow-tracefs-write", action="store_true")
    parser.add_argument("--allow-vendor-mount", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-pm-service-trigger-observer", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"tracefs_write_executed: {manifest['tracefs_write_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
