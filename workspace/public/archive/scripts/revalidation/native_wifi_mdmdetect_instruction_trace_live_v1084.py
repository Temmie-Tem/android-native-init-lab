#!/usr/bin/env python3
"""V1084 libmdmdetect instruction-level tracefs proof."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
from pathlib import Path
from typing import Any

import native_wifi_pm_service_instruction_trace_live_v1082 as tracebase
import native_wifi_pm_service_trigger_observer_live_v1066 as base
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1084-mdmdetect-instruction-trace-live")
DEFAULT_V1083_MANIFEST = Path("tmp/wifi/v1083-mdmdetect-system-info-classifier/manifest.json")
DEFAULT_EXECNS_HELPER_SHA256 = tracebase.DEFAULT_EXECNS_HELPER_SHA256
DEFAULT_EXECNS_HELPER_MARKER = tracebase.DEFAULT_EXECNS_HELPER_MARKER
DEFAULT_TRACE_BINARY = "/mnt/vendor/lib64/libmdmdetect.so"
DEFAULT_VENDOR_MOUNT = tracebase.DEFAULT_VENDOR_MOUNT
DEFAULT_VENDOR_BLOCK = tracebase.DEFAULT_VENDOR_BLOCK
DEFAULT_TRACEFS_ROOT = tracebase.DEFAULT_TRACEFS_ROOT
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1084"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1084/pm-observer.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1084/tracefs-uprobe-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1084/pm-observer-output.txt"
LATEST_POINTER = Path("tmp/wifi/latest-v1084-mdmdetect-instruction-trace-live.txt")

EVENT_SPECS = (
    ("mdm_get_system_info_entry", "2c94"),
    ("mdm_stat_esoc_call", "2d18"),
    ("mdm_esoc_stat_fail_branch", "2d1c"),
    ("mdm_esoc_opendir_call", "2d28"),
    ("mdm_esoc_opendir_fail_branch", "2d2c"),
    ("mdm_esoc_readdir_first", "2d34"),
    ("mdm_esoc_supported_call", "2d74"),
    ("mdm_get_esoc_details_call", "2d94"),
    ("mdm_msm_opendir_call", "2de8"),
    ("mdm_msm_opendir_fail_log", "2e50"),
    ("mdm_msm_readdir_first", "2df4"),
    ("mdm_msm_entry_process", "2e78"),
    ("mdm_get_soc_name_read_call", "2e94"),
    ("mdm_get_subsystem_info_nonmodem_call", "2ee8"),
    ("mdm_get_subsystem_info_modem_call", "2f1c"),
    ("mdm_success_return", "2f3c"),
    ("mdm_failure_after_msm_open", "2e54"),
    ("mdm_failure_get_info_log_nonmodem", "2fc4"),
    ("mdm_failure_get_info_log_modem", "2fe0"),
    ("mdm_failure_return_after_info", "2fec"),
    ("subsys_info_entry", "2aa4"),
    ("subsys_compare_slpi", "2b0c"),
    ("subsys_compare_modem", "2b24"),
    ("subsys_compare_spss", "2b3c"),
    ("subsys_device_path_format", "2c78"),
    ("subsys_success_return", "2c80"),
)

ALLOWED_V1083_DECISIONS = {
    "v1083-mdmdetect-system-info-requirements-classified",
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
GROUP=a90mdm1084
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

echo tracefs_uprobe_collector=v1084
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


def patch_tracebase() -> None:
    tracebase.EVENT_SPECS = EVENT_SPECS
    tracebase.tracefs_collector_script = tracefs_collector_script


def required_flags(args: argparse.Namespace) -> list[str]:
    return tracebase.required_flags(args)


def classify_branch(counts: dict[str, int]) -> str:
    if counts.get("mdm_success_return", 0) > 0:
        return "mdmdetect-success-return-observed"
    if counts.get("mdm_esoc_opendir_fail_branch", 0) > 0:
        return "esoc-root-opendir-failure"
    if counts.get("mdm_failure_after_msm_open", 0) > 0:
        return "msm-subsys-root-opendir-failure"
    if counts.get("mdm_failure_get_info_log_modem", 0) > 0 or counts.get("mdm_get_subsystem_info_modem_call", 0) > 0:
        return "modem-subsystem-info-failure"
    if counts.get("mdm_failure_get_info_log_nonmodem", 0) > 0 or counts.get("mdm_get_subsystem_info_nonmodem_call", 0) > 0:
        return "nonmodem-subsystem-info-failure"
    if counts.get("mdm_get_esoc_details_call", 0) > 0:
        return "esoc-details-path-observed"
    if counts.get("mdm_esoc_stat_fail_branch", 0) > 0 and counts.get("mdm_msm_opendir_call", 0) > 0:
        return "esoc-absent-msm-fallback-observed"
    return "branch-not-terminal"


def decide(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1084-mdmdetect-instruction-trace-plan-ready",
            True,
            "plan-only; no tracefs write, PM actor, BPF attach, or Wi-Fi action executed",
            "run V1084 with explicit allow flags",
        )
    v1083_decision = (manifest.get("v1083") or {}).get("decision")
    if v1083_decision not in ALLOWED_V1083_DECISIONS:
        return (
            "v1084-v1083-predecessor-missing",
            False,
            f"unexpected V1083 decision={v1083_decision!r}",
            "rerun or inspect V1083 before libmdmdetect branch tracing",
        )
    missing = required_flags(args)
    if missing:
        return (
            "v1084-mdmdetect-trace-approval-required",
            False,
            "missing explicit flags: " + ", ".join(missing),
            "rerun with all V1084 allow flags",
        )
    analysis = manifest.get("analysis") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    post = analysis.get("post_surface") or {}
    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1084-execns-helper-sha-mismatch", False, "remote execns helper is not v196", "redeploy V1074 helper v196")
    if not analysis.get("pm_binary_visible"):
        return ("v1084-mdmdetect-not-visible", False, "read-only vendor mount did not expose libmdmdetect.so", "repair vendor mount before retry")
    if tracefs.get("result") != "tracefs-uprobe-pass":
        return ("v1084-tracefs-uprobe-failed", False, f"tracefs result={tracefs.get('result')}", "inspect tracefs collector transcript")
    if tracefs.get("register_failures") or tracefs.get("enable_failures") or tracefs.get("cleanup_failures"):
        return ("v1084-tracefs-uprobe-cleanup-review", False, "register/enable/cleanup failures present", "inspect tracefs cleanup before retry")
    if tracefs.get("forbidden_true"):
        return ("v1084-forbidden-action-observed", False, f"forbidden={tracefs.get('forbidden_true')}", "stop and audit helper contract")
    if post.get("forbidden_actor_hits") or post.get("wifi_link_hits"):
        return ("v1084-postflight-safety-review", False, "forbidden actors or Wi-Fi link appeared", "cleanup device before continuing")
    counts = tracefs.get("counts") or {}
    if counts.get("mdm_get_system_info_entry", 0) <= 0 or counts.get("mdm_stat_esoc_call", 0) <= 0:
        return ("v1084-mdmdetect-entry-not-hit", False, f"counts={counts}", "verify libmdmdetect uprobe file path and offsets")
    branch = classify_branch(counts)
    if branch == "branch-not-terminal":
        return ("v1084-mdmdetect-terminal-branch-missing", False, f"counts={counts}", "increase hold or add narrower offsets around get_system_info")
    return (
        f"v1084-{branch}",
        True,
        f"libmdmdetect get_system_info branch captured: {branch}",
        "use the captured branch to decide whether to repair ESOC/MSM sysfs namespace parity or subsystem device path parity",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1083 = load_json(args.v1083_manifest)
    patch_tracebase()
    manifest: dict[str, Any] = {
        "cycle": "v1084",
        "generated_at": now_iso(),
        "command": args.command,
        "v1083": {
            "manifest": str(repo_path(args.v1083_manifest)),
            "decision": v1083.get("decision", ""),
            "pass": bool(v1083.get("pass")),
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
        and v1083.get("decision") in ALLOWED_V1083_DECISIONS
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
        "# V1084 libmdmdetect Instruction Trace Live",
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
    parser.add_argument("--v1083-manifest", type=Path, default=DEFAULT_V1083_MANIFEST)
    parser.add_argument("--property-root", default=base.DEFAULT_PROPERTY_ROOT)
    parser.add_argument("--helper-timeout-sec", type=int, default=4)
    parser.add_argument("--toybox-timeout-sec", type=int, default=18)
    parser.add_argument("--tracefs-duration-sec", type=int, default=18)
    parser.add_argument("--vendor-block", default=DEFAULT_VENDOR_BLOCK)
    parser.add_argument("--vendor-mount", default=DEFAULT_VENDOR_MOUNT)
    parser.add_argument("--pm-binary", default=DEFAULT_TRACE_BINARY)
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
