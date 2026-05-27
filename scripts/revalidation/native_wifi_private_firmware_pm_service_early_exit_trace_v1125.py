#!/usr/bin/env python3
"""V1125 PM-service early-exit trace under helper-private firmware mounts."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
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
DEFAULT_TCP_TIMEOUT_SEC = 300.0
DEFAULT_TRACEFS_DURATION_SEC = 300
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


def tracefs_collector_script(args: argparse.Namespace) -> str:
    labels = " ".join(label for label, _offset in v1086.EVENT_SPECS)
    grep_pattern = "|".join(re.escape(label) for label, _offset in v1086.EVENT_SPECS)
    register_calls = "\n".join(
        f"register_event {shlex.quote(label)} {shlex.quote(offset)}"
        for label, offset in v1086.EVENT_SPECS
    )
    enable_calls = "\n".join(
        f"enable_event {shlex.quote(label)}"
        for label, _offset in v1086.EVENT_SPECS
    )
    count_calls = "\n".join(
        f"count_event {shlex.quote(label)}"
        for label, _offset in v1086.EVENT_SPECS
    )
    child_summary_pattern = (
        r"^(A90_EXECNS_(END|STDOUT_END)|"
        r"pm_service_trigger_observer\."
        r"(private_firmware[^=]*|child\.per_mgr[^=]*|child\.pm_proxy_helper[^=]*|child\.per_proxy[^=]*|"
        r"vndservice_provider_seen|result|reason|all_postflight_safe|"
        r"cnss_daemon_start_executed|wifi_hal_start_executed|scan_connect_linkup|"
        r"external_ping|subsys_esoc0_open_attempted)=|"
        r"wifi_hal_composite_start\.property_service_shim\.request\.[0-9]+\.result=)"
    )
    return f"""#!{args.busybox} sh
BB={shlex.quote(args.busybox)}
TRACE={shlex.quote(args.tracefs_root)}
GROUP=a90pm1125
BIN={shlex.quote(args.pm_binary)}
CHILD={shlex.quote(args.child_script)}
CHILD_LOG={shlex.quote(args.child_output)}
LABELS={shlex.quote(labels)}
ORIG_TRACING_ON=
if $BB test -r "$TRACE/tracing_on"; then
  ORIG_TRACING_ON=$($BB cat "$TRACE/tracing_on" 2>/dev/null)
fi

cleanup() {{
  for label in $LABELS; do
    if $BB test -e "$TRACE/events/$GROUP/$label/enable"; then
      if echo 0 > "$TRACE/events/$GROUP/$label/enable" 2>/dev/null; then
        echo "event.$label.disable=ok"
      else
        echo "event.$label.disable=failed"
      fi
    fi
  done
  for label in $LABELS; do
    if ! $BB test -d "$TRACE/events/$GROUP/$label"; then
      echo "event.$label.cleanup=absent"
    elif echo "-:$GROUP/$label" >> "$TRACE/uprobe_events" 2>/dev/null; then
      echo "event.$label.cleanup=removed"
    else
      echo "event.$label.cleanup=remove-failed"
    fi
  done
  if $BB test -n "$ORIG_TRACING_ON"; then
    echo "$ORIG_TRACING_ON" > "$TRACE/tracing_on" 2>/dev/null || true
  fi
}}
trap cleanup EXIT INT TERM

echo tracefs_uprobe_collector=v1125
echo tracefs_root="$TRACE"
echo binary="$BIN"
echo group="$GROUP"
echo child_log="$CHILD_LOG"
echo event_count={len(v1086.EVENT_SPECS)}

if ! $BB test -e "$TRACE/uprobe_events"; then
  echo result=tracefs-uprobe-events-missing
  exit 1
fi
if ! $BB test -x "$CHILD"; then
  echo result=tracefs-uprobe-child-missing
  exit 1
fi

: > "$TRACE/trace" 2>/dev/null || true
echo 1 > "$TRACE/tracing_on" 2>/dev/null || true

register_event() {{
  label="$1"
  offset="$2"
  echo "-:$GROUP/$label" >> "$TRACE/uprobe_events" 2>/dev/null || true
  if echo "p:$GROUP/$label $BIN:0x$offset" >> "$TRACE/uprobe_events" 2>/dev/null; then
    echo "event.$label.register=ok"
  else
    echo "event.$label.register=failed"
    echo result=tracefs-uprobe-register-failed
    exit 1
  fi
  if $BB test -r "$TRACE/events/$GROUP/$label/id"; then
    id=$($BB cat "$TRACE/events/$GROUP/$label/id" 2>/dev/null)
    echo "event.$label.id=$id"
  else
    echo "event.$label.id_read=failed"
    echo result=tracefs-uprobe-id-read-failed
    exit 1
  fi
}}

enable_event() {{
  label="$1"
  if echo 1 > "$TRACE/events/$GROUP/$label/enable" 2>/dev/null; then
    echo "event.$label.enable=ok"
  else
    echo "event.$label.enable=failed"
    echo result=tracefs-uprobe-enable-failed
    exit 1
  fi
}}

count_event() {{
  label="$1"
  count=$($BB grep -c "$label" "$TRACE/trace" 2>/dev/null || true)
  echo "event.$label.count=$count"
}}

{register_calls}
{enable_calls}

echo observe_begin=1
$BB sh "$CHILD" > "$CHILD_LOG" 2>&1
child_rc=$?
echo "child.rc=$child_rc"
if $BB test -r "$CHILD_LOG"; then
  child_bytes=$($BB wc -c < "$CHILD_LOG" 2>/dev/null)
  echo "child.output_bytes=$child_bytes"
fi
echo child_summary_begin
$BB grep -E {shlex.quote(child_summary_pattern)} "$CHILD_LOG" 2>/dev/null || true
echo child_summary_end
$BB sleep 1
echo trace_lines_begin
$BB grep -E {shlex.quote(grep_pattern)} "$TRACE/trace" 2>/dev/null || true
echo trace_lines_end
{count_calls}
echo result=tracefs-uprobe-pass
exit 0
"""


def patch_tracebase() -> None:
    v1086.patch_tracebase()
    tracebase.pm_observer_child_command = pm_observer_private_firmware_child_command
    tracebase.tracefs_collector_script = tracefs_collector_script


def required_flags(args: argparse.Namespace) -> list[str]:
    return tracebase.required_flags(args)


def branch_from_counts(counts: dict[str, int]) -> str:
    return v1086.classify_branch(counts)


def run_live(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {"mounted_tracefs_before": False, "mounted_vendor_before": False}
    base.run_a90ctl(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "pre-netservice-status", ["netservice", "status"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    base.run_a90ctl(args, store, steps, "proc-mounts-before", ["cat", "/proc/mounts"], timeout=15.0)
    mounts_before = tracebase.step_payload(store, steps[-1])
    analysis["mounted_tracefs_before"] = tracebase.tracefs_mounted(mounts_before)
    analysis["mounted_vendor_before"] = tracebase.mount_present(mounts_before, args.vendor_mount)

    base.run_a90ctl(args, store, steps, "selinuxfs-probe", base.selinuxfs_probe_command(args), timeout=12.0, allow_error=True)
    if args.allow_selinuxfs_mount:
        base.run_a90ctl(args, store, steps, "mount-selinuxfs", base.selinuxfs_mount_command(args), timeout=12.0, allow_error=True)
    if not analysis["mounted_tracefs_before"]:
        base.run_a90ctl(
            args,
            store,
            steps,
            "tracefs-mount",
            tracebase.shell_cmd(args, "$BB mkdir -p /sys/kernel/tracing; $BB mount -t tracefs tracefs /sys/kernel/tracing"),
            timeout=20.0,
        )
    if not analysis["mounted_vendor_before"]:
        base.run_a90ctl(
            args,
            store,
            steps,
            "vendor-ro-mount",
            tracebase.shell_cmd(
                args,
                (
                    f"$BB mkdir -p {args.work_dir} {args.vendor_mount}; "
                    "dev=$($BB cat /sys/class/block/sda29/dev); "
                    "maj=${dev%:*}; min=${dev#*:}; "
                    f"$BB rm -f {tracebase.synthetic_vendor_marker(args)}; "
                    f"if $BB test ! -e {tracebase.synthetic_vendor_block(args)}; then "
                    f"$BB mknod {tracebase.synthetic_vendor_block(args)} b $maj $min; "
                    f"echo 1 > {tracebase.synthetic_vendor_marker(args)}; "
                    "fi; "
                    f"$BB mount -t ext4 -o ro,noload {tracebase.synthetic_vendor_block(args)} {args.vendor_mount}"
                ),
            ),
            timeout=25.0,
        )
    pm_binary_step = base.run_a90ctl(args, store, steps, "pm-binary-stat", ["run", args.busybox, "stat", args.pm_binary], timeout=15.0, allow_error=True)
    analysis["pm_binary_visible"] = bool(pm_binary_step.get("ok"))
    analysis["execns_helper"] = tracebase.remote_sha_check(args, store, steps, "execns-helper-sha", args.helper, args.helper_sha256)
    tracebase.write_child_script(args, store, steps)
    tracebase.write_collector_script(args, store, steps)

    collector_step = base.run_a90ctl(
        args,
        store,
        steps,
        "pm-service-tracefs-uprobe-observer",
        ["run", args.busybox, "sh", args.collector_script],
        timeout=args.tracefs_duration_sec + 90.0,
    )
    collector_text = tracebase.step_payload(store, collector_step)
    analysis["tracefs_uprobe"] = tracebase.parse_tracefs_output(collector_text)

    analysis["post_surface"] = base.post_surface(args, store, steps)
    base.run_a90ctl(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "proc-mounts-before-cleanup", ["cat", "/proc/mounts"], timeout=15.0)

    if not analysis["mounted_vendor_before"]:
        base.run_a90ctl(
            args,
            store,
            steps,
            "vendor-umount",
            tracebase.shell_cmd(
                args,
                (
                    f"$BB umount {args.vendor_mount}; "
                    f"if $BB test -e {tracebase.synthetic_vendor_marker(args)}; then "
                    f"$BB rm -f {tracebase.synthetic_vendor_block(args)} {tracebase.synthetic_vendor_marker(args)}; "
                    "fi; "
                    f"$BB rm -f {args.child_script} {args.collector_script} {args.child_output}"
                ),
            ),
            timeout=20.0,
            allow_error=True,
        )
    if not analysis["mounted_tracefs_before"]:
        base.run_a90ctl(args, store, steps, "tracefs-umount", tracebase.shell_cmd(args, "$BB umount /sys/kernel/tracing"), timeout=20.0, allow_error=True)
    if args.allow_selinuxfs_mount:
        base.run_a90ctl(args, store, steps, "umount-selinuxfs", base.selinuxfs_umount_command(args), timeout=12.0, allow_error=True)
    base.run_a90ctl(args, store, steps, "proc-mounts-after-cleanup", ["cat", "/proc/mounts"], timeout=15.0)
    base.run_a90ctl(args, store, steps, "post-netservice-status", ["netservice", "status"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "post-selftest-final", ["selftest"], timeout=12.0)
    mounts_after = tracebase.step_payload(store, steps[-4]) if len(steps) >= 4 else ""
    analysis["mounted_tracefs_after"] = tracebase.tracefs_mounted(mounts_after)
    analysis["mounted_vendor_after"] = tracebase.mount_present(mounts_after, args.vendor_mount)
    return steps, analysis


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
        steps, analysis = run_live(args, store)
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
    parser.add_argument("--tcp-timeout", type=float, default=DEFAULT_TCP_TIMEOUT_SEC)
    parser.add_argument("--busybox", default=base.DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=base.DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=base.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_EXECNS_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_EXECNS_HELPER_MARKER)
    parser.add_argument("--v1124-manifest", type=Path, default=DEFAULT_V1124_MANIFEST)
    parser.add_argument("--property-root", default=base.DEFAULT_PROPERTY_ROOT)
    parser.add_argument("--helper-timeout-sec", type=int, default=4)
    parser.add_argument("--toybox-timeout-sec", type=int, default=18)
    parser.add_argument("--tracefs-duration-sec", type=int, default=DEFAULT_TRACEFS_DURATION_SEC)
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
