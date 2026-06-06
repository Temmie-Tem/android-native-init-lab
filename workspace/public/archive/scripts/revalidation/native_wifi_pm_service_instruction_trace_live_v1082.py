#!/usr/bin/env python3
"""V1082 instruction-level PM-service early path tracefs proof."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

import native_wifi_pm_service_trigger_observer_live_v1066 as base
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1082-pm-service-instruction-trace-live")
DEFAULT_V1081_MANIFEST = Path("tmp/wifi/v1081-pm-service-early-path-classifier/manifest.json")
DEFAULT_EXECNS_HELPER_SHA256 = "61b8ac54460f05e1d3a6fc6b68d8873c04537c171054921b4266be1ef6a0fb59"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v196"
DEFAULT_VENDOR_MOUNT = "/mnt/vendor"
DEFAULT_VENDOR_BLOCK = "/dev/block/sda29"
DEFAULT_PM_BINARY = "/mnt/vendor/bin/pm-service"
DEFAULT_TRACEFS_ROOT = "/sys/kernel/tracing"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1082"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1082/pm-observer.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1082/tracefs-uprobe-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1082/pm-observer-output.txt"
LATEST_POINTER = Path("tmp/wifi/latest-v1082-pm-service-instruction-trace-live.txt")

KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
EVENT_COUNT_RE = re.compile(r"^event\.([A-Za-z0-9_]+)\.count=(\d+)$", re.MULTILINE)
TRACE_RESULT_RE = re.compile(r"^result=(tracefs-uprobe-[A-Za-z0-9_-]+)$", re.MULTILINE)

EVENT_SPECS = (
    ("main_entry", "7650"),
    ("main_pipe_call", "7748"),
    ("main_helper_call", "77c8"),
    ("main_helper_return_branch", "77cc"),
    ("main_error_close0", "77d4"),
    ("main_error_close1", "77dc"),
    ("main_binder_driver_call", "78e0"),
    ("helper_entry", "6b6c"),
    ("helper_get_system_info_call", "6bc0"),
    ("helper_get_system_info_branch", "6bc4"),
    ("helper_get_system_info_failure_log", "6bdc"),
    ("helper_get_system_info_failure_return", "6be0"),
    ("helper_get_system_info_success_path", "6be8"),
)

ALLOWED_V1081_DECISIONS = {
    "v1081-pm-service-early-exit-path-classified",
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


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def tracefs_mounted(text: str) -> bool:
    return re.search(r"\s/sys/kernel/tracing\s+tracefs\s", text) is not None


def mount_present(text: str, target: str) -> bool:
    return re.search(rf"\s{re.escape(target)}\s+", text) is not None


def shell_cmd(args: argparse.Namespace, script: str) -> list[str]:
    return [
        "run",
        args.busybox,
        "sh",
        "-c",
        script.replace("$BB", args.busybox).replace("$TB", args.toybox),
    ]


def step_payload(store: EvidenceStore, step: dict[str, Any]) -> str:
    file_name = step.get("file")
    if not file_name:
        return ""
    path = store.run_dir / str(file_name)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def synthetic_vendor_block(args: argparse.Namespace) -> str:
    return args.vendor_block


def synthetic_vendor_marker(args: argparse.Namespace) -> str:
    return f"{args.work_dir}/created-devblock-sda29"


def pm_observer_child_command(args: argparse.Namespace) -> list[str]:
    child = base.helper_command(args)
    if len(child) >= 3 and child[0] == args.toybox and child[1] == "timeout":
        child = child[3:]
    return child


def remote_sha_check(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], name: str, path: str, expected: str) -> dict[str, Any]:
    step = base.run_tcpctl(args, store, steps, name, [args.toybox, "sha256sum", path], timeout=30.0)
    text = step_payload(store, step)
    return {"file": step["file"], "ok": expected in text, "expected": expected}


def append_device_file(args: argparse.Namespace,
                       store: EvidenceStore,
                       steps: list[dict[str, Any]],
                       path: str,
                       text: str,
                       label: str) -> None:
    base.run_a90ctl(args, store, steps, f"{label}-rm", ["run", args.busybox, "rm", "-f", path], timeout=12.0, allow_error=True)
    for index in range(0, len(text), 1200):
        chunk = text[index:index + 1200]
        base.run_a90ctl(args, store, steps, f"{label}-append-{index // 1200:03d}", ["appendfile", path, chunk], timeout=15.0)
    base.run_a90ctl(args, store, steps, f"{label}-chmod", ["run", args.busybox, "chmod", "755", path], timeout=12.0)


def write_child_script(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    child = pm_observer_child_command(args)
    script = "#!" + args.busybox + " sh\nexec " + " ".join(shlex.quote(part) for part in child) + "\n"
    store.write_text("host/pm-observer-child-script.txt", script)
    base.run_a90ctl(args, store, steps, "workdir-mkdir", ["run", args.busybox, "mkdir", "-p", args.work_dir], timeout=12.0)
    append_device_file(args, store, steps, args.child_script, script, "child-script")


def tracefs_collector_script(args: argparse.Namespace) -> str:
    labels = " ".join(label for label, _offset in EVENT_SPECS)
    grep_pattern = "|".join(re.escape(label) for label, _offset in EVENT_SPECS)
    register_calls = "\n".join(
        f"register_event {shlex.quote(label)} {shlex.quote(offset)}"
        for label, offset in EVENT_SPECS
    )
    enable_calls = "\n".join(
        f"enable_event {shlex.quote(label)}"
        for label, _offset in EVENT_SPECS
    )
    count_calls = "\n".join(
        f"count_event {shlex.quote(label)}"
        for label, _offset in EVENT_SPECS
    )
    return f"""#!{args.busybox} sh
BB={shlex.quote(args.busybox)}
TRACE={shlex.quote(args.tracefs_root)}
GROUP=a90pm1082
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

echo tracefs_uprobe_collector=v1082
echo tracefs_root="$TRACE"
echo binary="$BIN"
echo group="$GROUP"
echo child_log="$CHILD_LOG"
echo event_count={len(EVENT_SPECS)}

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
$BB grep -E '^(A90_EXECNS_(END|STDOUT_END)|pm_service_trigger_observer\\.|wifi_hal_composite_start\\.property_service_shim\\.request\\.[0-9]+\\.result=)' "$CHILD_LOG" 2>/dev/null || true
echo child_summary_end
$BB sleep 1
echo trace_lines_begin
$BB grep -E {shlex.quote(grep_pattern)} "$TRACE/trace" 2>/dev/null || true
echo trace_lines_end
{count_calls}
echo result=tracefs-uprobe-pass
exit 0
"""


def write_collector_script(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    script = tracefs_collector_script(args)
    store.write_text("host/tracefs-uprobe-collector-script.txt", script)
    append_device_file(args, store, steps, args.collector_script, script, "collector-script")


def parse_tracefs_output(text: str) -> dict[str, Any]:
    result_match = TRACE_RESULT_RE.search(text)
    counts = {label: int(value) for label, value in EVENT_COUNT_RE.findall(text)}
    keys = parse_keys(text)
    pm_contract = {
        key[len("pm_service_trigger_observer."):]: value
        for key, value in keys.items()
        if key.startswith("pm_service_trigger_observer.")
    }
    trace_lines = []
    in_trace = False
    for line in text.splitlines():
        if line.strip() == "trace_lines_begin":
            in_trace = True
            continue
        if line.strip() == "trace_lines_end":
            in_trace = False
            continue
        if in_trace:
            trace_lines.append(line.rstrip())
    return {
        "result": result_match.group(1) if result_match else keys.get("result", ""),
        "counts": counts,
        "hit_count": sum(1 for value in counts.values() if value > 0),
        "entry_hit": counts.get("main_entry", 0) > 0,
        "main_hit": counts.get("main_entry", 0) > 0,
        "trace_lines": trace_lines[:100],
        "trace_line_count": len(trace_lines),
        "register_failures": [line.strip() for line in text.splitlines() if ".register=failed" in line],
        "enable_failures": [line.strip() for line in text.splitlines() if ".enable=failed" in line],
        "disable_failures": [line.strip() for line in text.splitlines() if ".disable=failed" in line],
        "cleanup_failures": [line.strip() for line in text.splitlines() if ".cleanup=remove-failed" in line],
        "pm_contract": pm_contract,
        "child_rc": keys.get("child.rc", ""),
        "forbidden_true": {
            key: value
            for key, value in pm_contract.items()
            if key in {
                "mdm_helper_start_executed",
                "cnss_daemon_start_executed",
                "wifi_hal_start_executed",
                "scan_connect_linkup",
                "external_ping",
                "subsys_esoc0_open_attempted",
            } and value not in ("0", "False", "false", "")
        },
    }


def run_live(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {"mounted_tracefs_before": False, "mounted_vendor_before": False}
    base.run_a90ctl(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "pre-netservice-status", ["netservice", "status"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    base.run_a90ctl(args, store, steps, "proc-mounts-before", ["cat", "/proc/mounts"], timeout=15.0)
    mounts_before = step_payload(store, steps[-1])
    analysis["mounted_tracefs_before"] = tracefs_mounted(mounts_before)
    analysis["mounted_vendor_before"] = mount_present(mounts_before, args.vendor_mount)

    base.run_a90ctl(args, store, steps, "selinuxfs-probe", base.selinuxfs_probe_command(args), timeout=12.0, allow_error=True)
    if args.allow_selinuxfs_mount:
        base.run_a90ctl(args, store, steps, "mount-selinuxfs", base.selinuxfs_mount_command(args), timeout=12.0, allow_error=True)
    if not analysis["mounted_tracefs_before"]:
        base.run_a90ctl(
            args,
            store,
            steps,
            "tracefs-mount",
            shell_cmd(args, "$BB mkdir -p /sys/kernel/tracing; $BB mount -t tracefs tracefs /sys/kernel/tracing"),
            timeout=20.0,
        )
    if not analysis["mounted_vendor_before"]:
        base.run_a90ctl(
            args,
            store,
            steps,
            "vendor-ro-mount",
            shell_cmd(
                args,
                (
                    f"$BB mkdir -p {args.work_dir} {args.vendor_mount}; "
                    "dev=$($BB cat /sys/class/block/sda29/dev); "
                    "maj=${dev%:*}; min=${dev#*:}; "
                    f"$BB rm -f {synthetic_vendor_marker(args)}; "
                    f"if $BB test ! -e {synthetic_vendor_block(args)}; then "
                    f"$BB mknod {synthetic_vendor_block(args)} b $maj $min; "
                    f"echo 1 > {synthetic_vendor_marker(args)}; "
                    "fi; "
                    f"$BB mount -t ext4 -o ro,noload {synthetic_vendor_block(args)} {args.vendor_mount}"
                ),
            ),
            timeout=25.0,
        )
    pm_binary_step = base.run_a90ctl(args, store, steps, "pm-binary-stat", ["run", args.busybox, "stat", args.pm_binary], timeout=15.0, allow_error=True)
    analysis["pm_binary_visible"] = bool(pm_binary_step.get("ok"))
    analysis["execns_helper"] = remote_sha_check(args, store, steps, "execns-helper-sha", args.helper, args.helper_sha256)
    write_child_script(args, store, steps)
    write_collector_script(args, store, steps)

    collector_step = base.run_tcpctl(
        args,
        store,
        steps,
        "pm-service-tracefs-uprobe-observer",
        [args.busybox, "sh", args.collector_script],
        timeout=args.tracefs_duration_sec + 90.0,
    )
    collector_text = step_payload(store, collector_step)
    analysis["tracefs_uprobe"] = parse_tracefs_output(collector_text)

    analysis["post_surface"] = base.post_surface(args, store, steps)
    base.run_a90ctl(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "proc-mounts-before-cleanup", ["cat", "/proc/mounts"], timeout=15.0)

    if not analysis["mounted_vendor_before"]:
        base.run_a90ctl(
            args,
            store,
            steps,
            "vendor-umount",
            shell_cmd(
                args,
                (
                    f"$BB umount {args.vendor_mount}; "
                    f"if $BB test -e {synthetic_vendor_marker(args)}; then "
                    f"$BB rm -f {synthetic_vendor_block(args)} {synthetic_vendor_marker(args)}; "
                    "fi; "
                    f"$BB rm -f {args.child_script} {args.collector_script} {args.child_output}"
                ),
            ),
            timeout=20.0,
            allow_error=True,
        )
    if not analysis["mounted_tracefs_before"]:
        base.run_a90ctl(args, store, steps, "tracefs-umount", shell_cmd(args, "$BB umount /sys/kernel/tracing"), timeout=20.0, allow_error=True)
    if args.allow_selinuxfs_mount:
        base.run_a90ctl(args, store, steps, "umount-selinuxfs", base.selinuxfs_umount_command(args), timeout=12.0, allow_error=True)
    base.run_a90ctl(args, store, steps, "proc-mounts-after-cleanup", ["cat", "/proc/mounts"], timeout=15.0)
    base.run_a90ctl(args, store, steps, "post-netservice-status", ["netservice", "status"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "post-selftest-final", ["selftest"], timeout=12.0)
    mounts_after = step_payload(store, steps[-4]) if len(steps) >= 4 else ""
    analysis["mounted_tracefs_after"] = tracefs_mounted(mounts_after)
    analysis["mounted_vendor_after"] = mount_present(mounts_after, args.vendor_mount)
    return steps, analysis


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    for flag, enabled in (
        ("--allow-tracefs-mount", args.allow_tracefs_mount),
        ("--allow-tracefs-write", args.allow_tracefs_write),
        ("--allow-vendor-mount", args.allow_vendor_mount),
        ("--allow-selinuxfs-mount", args.allow_selinuxfs_mount),
        ("--allow-pm-service-trigger-observer", args.allow_pm_service_trigger_observer),
        ("--assume-yes", args.assume_yes),
    ):
        if not enabled:
            missing.append(flag)
    return missing


def decide(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1082-pm-service-tracefs-uprobe-plan-ready",
            True,
            "plan-only; no tracefs write, PM actor, BPF attach, or Wi-Fi action executed",
            "run V1082 with explicit allow flags",
        )
    v1081_decision = (manifest.get("v1081") or {}).get("decision")
    if v1081_decision not in ALLOWED_V1081_DECISIONS:
        return (
            "v1082-v1081-predecessor-missing",
            False,
            f"unexpected V1081 decision={v1081_decision!r}",
            "rerun or inspect V1081 before tracefs-only collector",
        )
    missing = required_flags(args)
    if missing:
        return (
            "v1082-pm-service-tracefs-uprobe-approval-required",
            False,
            "missing explicit flags: " + ", ".join(missing),
            "rerun with all V1082 allow flags",
        )
    analysis = manifest.get("analysis") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    post = analysis.get("post_surface") or {}
    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1082-execns-helper-sha-mismatch", False, "remote execns helper is not v196", "redeploy V1074 helper v196")
    if not analysis.get("pm_binary_visible"):
        return ("v1082-pm-binary-not-visible", False, "read-only vendor mount did not expose pm-service", "repair synthetic sda29 mount before retry")
    if tracefs.get("result") != "tracefs-uprobe-pass":
        return ("v1082-tracefs-uprobe-failed", False, f"tracefs result={tracefs.get('result')}", "inspect tracefs collector transcript")
    if tracefs.get("register_failures") or tracefs.get("enable_failures") or tracefs.get("cleanup_failures"):
        return ("v1082-tracefs-uprobe-cleanup-review", False, "register/enable/cleanup failures present", "inspect tracefs cleanup before retry")
    if tracefs.get("forbidden_true"):
        return ("v1082-forbidden-action-observed", False, f"forbidden={tracefs.get('forbidden_true')}", "stop and audit helper contract")
    if post.get("forbidden_actor_hits") or post.get("wifi_link_hits"):
        return ("v1082-postflight-safety-review", False, "forbidden actors or Wi-Fi link appeared", "cleanup device before continuing")
    if tracefs.get("hit_count", 0) <= 0:
        return ("v1082-pm-service-tracefs-uprobe-no-hit", False, "no pm-service uprobe trace lines were captured", "verify uprobe offset/file mapping or child runtime")
    counts = tracefs.get("counts") or {}
    expected_present = (
        counts.get("main_entry", 0) > 0
        and counts.get("main_pipe_call", 0) > 0
        and counts.get("main_helper_call", 0) > 0
        and counts.get("main_helper_return_branch", 0) > 0
        and counts.get("helper_entry", 0) > 0
        and counts.get("helper_get_system_info_call", 0) > 0
        and counts.get("helper_get_system_info_branch", 0) > 0
        and counts.get("helper_get_system_info_failure_log", 0) > 0
        and counts.get("helper_get_system_info_failure_return", 0) > 0
        and counts.get("main_error_close0", 0) > 0
        and counts.get("main_error_close1", 0) > 0
    )
    expected_absent = (
        counts.get("helper_get_system_info_success_path", 0) == 0
        and counts.get("main_binder_driver_call", 0) == 0
    )
    if not expected_present:
        return ("v1082-instruction-failure-path-incomplete", False, f"counts={counts}", "inspect instruction trace transcript")
    if not expected_absent:
        return ("v1082-instruction-success-or-binder-path-reached", False, f"counts={counts}", "reclassify PM-service branch path")
    return (
        "v1082-pm-service-get-system-info-failure-branch-confirmed",
        True,
        "get_system_info failure branch hit; success path and Binder setup not reached",
        "classify get_system_info Android-state requirements before another PM live retry",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1081 = load_json(args.v1081_manifest)
    manifest: dict[str, Any] = {
        "cycle": "v1082",
        "generated_at": now_iso(),
        "command": args.command,
        "v1081": {
            "manifest": str(repo_path(args.v1081_manifest)),
            "decision": v1081.get("decision", ""),
            "pass": bool(v1081.get("pass")),
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
        and v1081.get("decision") in ALLOWED_V1081_DECISIONS
    ):
        steps, analysis = run_live(args, store)
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
    step_rows = [[step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")] for step in manifest.get("steps", [])]
    return "\n".join([
        "# V1082 PM Service Instruction Trace Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
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
        f"- entry_hit: `{tracefs.get('entry_hit', '')}`",
        f"- main_hit: `{tracefs.get('main_hit', '')}`",
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
    parser.add_argument("--v1081-manifest", type=Path, default=DEFAULT_V1081_MANIFEST)
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
