#!/usr/bin/env python3
"""V1086 PM-service post-mdmdetect success path tracefs proof."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_mdmdetect_instruction_trace_live_v1084 as mdmtrace
import native_wifi_pm_service_instruction_trace_live_v1082 as tracebase
import native_wifi_pm_service_trigger_observer_live_v1066 as base
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1086-pm-service-success-path-trace-live")
DEFAULT_V1085_MANIFEST = Path("tmp/wifi/v1085-mdmdetect-sysfs-parity-live/manifest.json")
DEFAULT_EXECNS_HELPER_SHA256 = "8dbf5aed1a3d087fc59c308bd674132e19c9cf2da0c42843b64c9c4efaf1672f"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v197"
DEFAULT_PM_BINARY = "/mnt/vendor/bin/pm-service"
DEFAULT_VENDOR_MOUNT = tracebase.DEFAULT_VENDOR_MOUNT
DEFAULT_VENDOR_BLOCK = tracebase.DEFAULT_VENDOR_BLOCK
DEFAULT_TRACEFS_ROOT = tracebase.DEFAULT_TRACEFS_ROOT
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1086"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1086/pm-observer.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1086/tracefs-uprobe-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1086/pm-observer-output.txt"
LATEST_POINTER = Path("tmp/wifi/latest-v1086-pm-service-success-path-trace-live.txt")

EVENT_SPECS = (
    ("pm_success_branch_after_get_system_info", "78d4"),
    ("pm_init_with_driver_call", "78e0"),
    ("pm_default_service_manager_call", "7904"),
    ("pm_string16_ctor", "7948"),
    ("pm_add_service_call", "7990"),
    ("pm_add_service_fail_log", "79d4"),
    ("pm_pthread_create_call", "79fc"),
    ("pm_pthread_create_fail_log", "7bb4"),
    ("pm_qmi_service_start_log", "7a34"),
    ("pm_start_thread_pool_call", "7a98"),
    ("pm_sigwait_call", "7afc"),
    ("pm_sigwait_error_log", "7af0"),
    ("pm_signal_value_load", "7b04"),
    ("pm_signal_shutdown_target", "7b44"),
    ("pm_shutdown_pipe_write", "7b50"),
    ("pm_pthread_join_call", "7b88"),
    ("pm_cleanup_join_target", "7bb8"),
    ("pm_close_pipe_read", "7bbc"),
    ("pm_close_pipe_write", "7bc4"),
    ("pm_clean_exit_log", "7c24"),
    ("pm_clean_return_zero", "7c28"),
    ("pm_failure_return_minus1", "7848"),
    ("pm_return_epilogue", "7878"),
)

ALLOWED_V1085_DECISIONS = {
    "v1084-mdmdetect-success-return-observed",
}


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


def patch_tracebase() -> None:
    mdmtrace.EVENT_SPECS = EVENT_SPECS
    tracebase.EVENT_SPECS = EVENT_SPECS
    tracebase.tracefs_collector_script = mdmtrace.tracefs_collector_script


def required_flags(args: argparse.Namespace) -> list[str]:
    return tracebase.required_flags(args)


def classify_branch(counts: dict[str, int]) -> str:
    if counts.get("pm_add_service_fail_log", 0) > 0:
        return "binder-add-service-failure"
    if counts.get("pm_pthread_create_fail_log", 0) > 0:
        return "qmi-thread-create-failure"
    if counts.get("pm_signal_shutdown_target", 0) > 0 and counts.get("pm_clean_return_zero", 0) > 0:
        return "signal-driven-clean-shutdown"
    if counts.get("pm_sigwait_call", 0) > 0 and counts.get("pm_clean_return_zero", 0) == 0:
        return "sigwait-still-active-or-observer-window"
    if counts.get("pm_clean_return_zero", 0) > 0:
        return "clean-return-zero"
    if counts.get("pm_failure_return_minus1", 0) > 0:
        return "failure-return-minus1"
    return "post-mdmdetect-terminal-branch-missing"


def decide(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1086-pm-service-success-path-trace-plan-ready",
            True,
            "plan-only; no tracefs write, PM actor, BPF attach, or Wi-Fi action executed",
            "run V1086 with explicit allow flags",
        )
    v1085_decision = (manifest.get("v1085") or {}).get("decision")
    if v1085_decision not in ALLOWED_V1085_DECISIONS:
        return (
            "v1086-v1085-predecessor-missing",
            False,
            f"unexpected V1085 decision={v1085_decision!r}",
            "rerun or inspect V1085 before PM-service success-path tracing",
        )
    missing = required_flags(args)
    if missing:
        return (
            "v1086-pm-service-success-path-approval-required",
            False,
            "missing explicit flags: " + ", ".join(missing),
            "rerun with all V1086 allow flags",
        )
    analysis = manifest.get("analysis") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    post = analysis.get("post_surface") or {}
    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1086-execns-helper-sha-mismatch", False, "remote execns helper is not v197", "redeploy V1085 helper v197")
    if not analysis.get("pm_binary_visible"):
        return ("v1086-pm-service-not-visible", False, "read-only vendor mount did not expose pm-service", "repair vendor mount before retry")
    if tracefs.get("result") != "tracefs-uprobe-pass":
        return ("v1086-tracefs-uprobe-failed", False, f"tracefs result={tracefs.get('result')}", "inspect tracefs collector transcript")
    if tracefs.get("register_failures") or tracefs.get("enable_failures") or tracefs.get("cleanup_failures"):
        return ("v1086-tracefs-uprobe-cleanup-review", False, "register/enable/cleanup failures present", "inspect tracefs cleanup before retry")
    if tracefs.get("forbidden_true"):
        return ("v1086-forbidden-action-observed", False, f"forbidden={tracefs.get('forbidden_true')}", "stop and audit helper contract")
    if post.get("forbidden_actor_hits") or post.get("wifi_link_hits"):
        return ("v1086-postflight-safety-review", False, "forbidden actors or Wi-Fi link appeared", "cleanup device before continuing")
    counts = tracefs.get("counts") or {}
    if counts.get("pm_success_branch_after_get_system_info", 0) <= 0:
        return ("v1086-pm-service-success-branch-not-hit", False, f"counts={counts}", "verify v197 mdmdetect success predecessor and pm-service offsets")
    branch = classify_branch(counts)
    if branch == "post-mdmdetect-terminal-branch-missing":
        return ("v1086-pm-service-terminal-branch-missing", False, f"counts={counts}", "add narrower offsets around PM-service loop")
    return (
        f"v1086-{branch}",
        True,
        f"PM-service post-mdmdetect branch captured: {branch}",
        "use this branch to decide whether to suppress observer SIGTERM or trace the signal source",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1085 = load_json(args.v1085_manifest)
    patch_tracebase()
    manifest: dict[str, Any] = {
        "cycle": "v1086",
        "generated_at": now_iso(),
        "command": args.command,
        "v1085": {
            "manifest": str(repo_path(args.v1085_manifest)),
            "decision": v1085.get("decision", ""),
            "pass": bool(v1085.get("pass")),
        },
        "event_specs": [f"{label}:0x{offset}" for label, offset in EVENT_SPECS],
        "steps": [],
        "analysis": {},
        "tracefs_write_executed": False,
        "bpf_attach_executed": False,
        "pm_actor_executed": False,
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
        and v1085.get("decision") in ALLOWED_V1085_DECISIONS
    ):
        steps, analysis = tracebase.run_live(args, store)
        manifest["steps"] = steps
        manifest["analysis"] = analysis
        manifest["tracefs_write_executed"] = True
        manifest["pm_actor_executed"] = True
        tracefs = analysis.get("tracefs_uprobe") or {}
        contract = tracefs.get("pm_contract") or {}
        manifest["wifi_hal_start_executed"] = contract.get("wifi_hal_start_executed") == "1"
        manifest["scan_connect_executed"] = contract.get("scan_connect_linkup") == "1"
        manifest["external_ping_executed"] = contract.get("external_ping") == "1"
    decision, passed, reason, next_step = decide(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    counts = tracefs.get("counts") or {}
    branch = classify_branch(counts) if counts else ""
    step_rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    return "\n".join([
        "# V1086 PM Service Success Path Trace Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- branch_classification: `{branch}`",
        f"- tracefs_write_executed: `{manifest['tracefs_write_executed']}`",
        f"- bpf_attach_executed: `{manifest['bpf_attach_executed']}`",
        f"- pm_actor_executed: `{manifest['pm_actor_executed']}`",
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
    parser.add_argument("--v1085-manifest", type=Path, default=DEFAULT_V1085_MANIFEST)
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
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
