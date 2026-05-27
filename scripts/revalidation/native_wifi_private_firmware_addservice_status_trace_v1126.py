#!/usr/bin/env python3
"""V1126 private-firmware PM addService status trace."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
from pathlib import Path
from typing import Any

import native_wifi_pm_service_instruction_trace_live_v1082 as tracebase
import native_wifi_private_firmware_pm_service_early_exit_trace_v1125 as v1125
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1126-private-firmware-addservice-status-trace")
LATEST_POINTER = Path("tmp/wifi/latest-v1126-private-firmware-addservice-status-trace.txt")
DEFAULT_V1125_MANIFEST = Path("tmp/wifi/v1125-private-firmware-pm-service-early-exit-trace/manifest.json")
EXPECTED_V1125_DECISION = "v1125-private-firmware-binder-add-service-failure"

EVENT_SPECS = (
    ("pm_success_branch_after_get_system_info", "78d4"),
    ("pm_default_service_manager_call", "7904"),
    ("pm_add_service_call", "7990 sm=%x23 service=%x1 binder=%x2 allow_isolated=%x3 dump_flags=%x4"),
    ("pm_add_service_status", "7994 status=%x0"),
    ("pm_add_service_fail_log", "79d4 saved_status=%x22"),
    ("pm_clean_return_zero", "7c28"),
    ("pm_return_epilogue", "7878"),
)

STATUS_RE = re.compile(r"\b(status|saved_status)=(0x[0-9A-Fa-f]+|-?\d+)")
HEX_OR_INT_RE = re.compile(r"^(0x[0-9A-Fa-f]+|-?\d+)$")

STATUS_NAMES = {
    0: "OK",
    -1: "PERMISSION_DENIED",
    -2: "NAME_NOT_FOUND",
    -3: "BAD_TYPE",
    -4: "WOULD_BLOCK_LEGACY",
    -5: "NO_INIT",
    -7: "BAD_INDEX",
    -11: "WOULD_BLOCK",
    -12: "NO_MEMORY",
    -17: "ALREADY_EXISTS",
    -19: "NO_DEVICE",
    -22: "BAD_VALUE",
    -32: "DEAD_OBJECT",
    -38: "INVALID_OPERATION",
    -110: "TIMED_OUT",
    -2147483648: "UNKNOWN_ERROR",
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


def signed(value: int, bits: int) -> int:
    mask = 1 << (bits - 1)
    return (value & (mask - 1)) - (value & mask)


def parse_int_literal(value: str) -> int | None:
    if not HEX_OR_INT_RE.match(value):
        return None
    try:
        return int(value, 0)
    except ValueError:
        return None


def decode_status(value: str) -> dict[str, Any]:
    parsed = parse_int_literal(value)
    if parsed is None:
        return {"raw": value, "parsed": None, "signed64": None, "signed32": None, "name": "unparsed"}
    signed64 = signed(parsed, 64)
    signed32 = signed(parsed, 32)
    name = STATUS_NAMES.get(signed32) or STATUS_NAMES.get(signed64) or "unknown"
    return {
        "raw": value,
        "parsed": parsed,
        "signed64": signed64,
        "signed32": signed32,
        "name": name,
    }


def tracefs_collector_script(args: argparse.Namespace) -> str:
    labels = " ".join(label for label, _spec in EVENT_SPECS)
    grep_pattern = "|".join(re.escape(label) for label, _spec in EVENT_SPECS)
    register_calls = "\n".join(
        f"register_event {shlex.quote(label)} {shlex.quote(spec)}"
        for label, spec in EVENT_SPECS
    )
    enable_calls = "\n".join(
        f"enable_event {shlex.quote(label)}"
        for label, _spec in EVENT_SPECS
    )
    count_calls = "\n".join(
        f"count_event {shlex.quote(label)}"
        for label, _spec in EVENT_SPECS
    )
    child_summary_pattern = (
        r"^(A90_EXECNS_(END|STDOUT_END)|"
        r"pm_service_trigger_observer\."
        r"(begin|mode|order|service_manager_start_executed|"
        r"vndservicemanager_readiness\.[^=]*|"
        r"private_firmware[^=]*|child\.per_mgr[^=]*|child\.pm_proxy_helper[^=]*|child\.per_proxy[^=]*|"
        r"vndservice_provider_seen|result|reason|all_postflight_safe|"
        r"cnss_daemon_start_executed|wifi_hal_start_executed|scan_connect_linkup|"
        r"external_ping|subsys_esoc0_open_attempted)=|"
        r"wifi_hal_composite_start\.property_service_shim\.request\.[0-9]+\.result=)"
    )
    return f"""#!{args.busybox} sh
BB={shlex.quote(args.busybox)}
TRACE={shlex.quote(args.tracefs_root)}
GROUP=a90pm1126
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

echo tracefs_uprobe_collector=v1126
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
  spec="$2"
  echo "-:$GROUP/$label" >> "$TRACE/uprobe_events" 2>/dev/null || true
  if echo "p:$GROUP/$label $BIN:0x$spec" >> "$TRACE/uprobe_events" 2>/dev/null; then
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
    v1125.v1086.EVENT_SPECS = EVENT_SPECS
    v1125.patch_tracebase()
    tracebase.tracefs_collector_script = tracefs_collector_script


def extract_statuses(trace_lines: list[str]) -> dict[str, list[dict[str, Any]]]:
    values: dict[str, list[dict[str, Any]]] = {"status": [], "saved_status": []}
    for line in trace_lines:
        for key, raw_value in STATUS_RE.findall(line):
            values.setdefault(key, []).append(decode_status(raw_value))
    return values


def status_label(status: dict[str, Any] | None) -> str:
    if not status:
        return "missing"
    name = str(status.get("name") or "unknown").lower().replace("_", "-")
    signed32 = status.get("signed32")
    if signed32 is None:
        return name
    return f"{name}-{signed32}"


def required_flags(args: argparse.Namespace) -> list[str]:
    return v1125.required_flags(args)


def decide(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1126-private-firmware-addservice-status-trace-plan-ready",
            True,
            "plan-only; no tracefs write, PM actor, CNSS actor, or Wi-Fi action executed",
            "run V1126 with explicit tracefs/PM observer allow flags",
        )
    v1125_manifest = manifest.get("v1125") or {}
    if v1125_manifest.get("decision") != EXPECTED_V1125_DECISION or not v1125_manifest.get("pass"):
        return (
            "v1126-v1125-predecessor-missing",
            False,
            f"unexpected V1125 decision={v1125_manifest.get('decision')!r} pass={v1125_manifest.get('pass')}",
            "refresh V1125 before tracing addService status",
        )
    missing = required_flags(args)
    if missing:
        return (
            "v1126-private-firmware-addservice-status-approval-required",
            False,
            "missing explicit flags: " + ", ".join(missing),
            "rerun with all V1126 allow flags",
        )
    analysis = manifest.get("analysis") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    post = analysis.get("post_surface") or {}
    contract = tracefs.get("pm_contract") or {}
    counts = tracefs.get("counts") or {}
    statuses = tracefs.get("addservice_statuses") or {}
    first_status = (statuses.get("status") or [None])[0]

    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1126-execns-helper-sha-mismatch", False, "remote execns helper is not v212", "deploy helper v212")
    if not analysis.get("pm_binary_visible"):
        return ("v1126-pm-service-not-visible", False, "read-only vendor mount did not expose pm-service", "repair vendor mount before retry")
    if tracefs.get("result") != "tracefs-uprobe-pass":
        return ("v1126-tracefs-uprobe-failed", False, f"tracefs result={tracefs.get('result')}", "inspect tracefs collector transcript")
    if tracefs.get("register_failures") or tracefs.get("enable_failures") or tracefs.get("cleanup_failures"):
        return ("v1126-tracefs-uprobe-cleanup-review", False, "register/enable/cleanup failures present", "inspect tracefs cleanup before retry")
    if tracefs.get("forbidden_true"):
        return ("v1126-forbidden-action-observed", False, f"forbidden={tracefs.get('forbidden_true')}", "stop and audit helper contract")
    if post.get("forbidden_actor_hits") or post.get("wifi_link_hits"):
        return ("v1126-postflight-safety-review", False, "forbidden actors or Wi-Fi link appeared", "cleanup device before continuing")
    if contract.get("private_firmware_mounts_requested") != "1":
        return ("v1126-private-firmware-flag-not-applied", False, "helper did not report private firmware request", "repair child command")
    if contract.get("private_firmware_mnt_mounted") != "1" or contract.get("private_firmware_modem_mounted") != "1":
        return (
            "v1126-private-firmware-mount-failed",
            False,
            f"firmware_mnt={contract.get('private_firmware_mnt_mounted')} firmware_modem={contract.get('private_firmware_modem_mounted')}",
            "inspect helper setup_error and partition visibility",
        )
    if contract.get("vndservicemanager_readiness.ready") != "1":
        return (
            "v1126-vndservicemanager-readiness-not-proven",
            False,
            f"ready={contract.get('vndservicemanager_readiness.ready')} checked={contract.get('vndservicemanager_readiness.checked')}",
            "prove service-manager readiness before interpreting addService status",
        )
    for label in ("pm_add_service_call", "pm_add_service_status", "pm_add_service_fail_log"):
        if counts.get(label, 0) <= 0:
            return (
                "v1126-addservice-status-trace-incomplete",
                False,
                f"missing {label}; counts={counts}",
                "verify PM-service offsets and tracefs fetch syntax",
            )
    if not first_status:
        return (
            "v1126-addservice-status-value-missing",
            False,
            f"statuses={statuses}",
            "verify ARM64 register fetch syntax for x0 after addService",
        )
    if first_status.get("signed32") == 0:
        return (
            "v1126-addservice-status-inconsistent-zero",
            False,
            f"status={first_status}",
            "inspect failure log offset and addService return capture",
        )
    label = status_label(first_status)
    return (
        f"v1126-private-firmware-addservice-status-{label}",
        True,
        f"addService returned {first_status}",
        "route next gate from decoded addService status",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1125_manifest = load_json(args.v1125_manifest)
    patch_tracebase()
    manifest: dict[str, Any] = {
        "cycle": "v1126",
        "generated_at": now_iso(),
        "command": args.command,
        "v1125": {
            "manifest": str(repo_path(args.v1125_manifest)),
            "decision": v1125_manifest.get("decision", ""),
            "pass": bool(v1125_manifest.get("pass")),
        },
        "event_specs": [f"{label}:0x{spec}" for label, spec in EVENT_SPECS],
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
        and v1125_manifest.get("decision") == EXPECTED_V1125_DECISION
        and bool(v1125_manifest.get("pass"))
    ):
        steps, analysis = v1125.run_live(args, store)
        tracefs = analysis.get("tracefs_uprobe") or {}
        trace_lines = tracefs.get("trace_lines") or []
        tracefs["addservice_statuses"] = extract_statuses(trace_lines)
        manifest["steps"] = steps
        manifest["analysis"] = analysis
        manifest["tracefs_write_executed"] = True
        manifest["pm_actor_executed"] = True
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
    statuses = tracefs.get("addservice_statuses") or {}
    step_rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    return "\n".join([
        "# V1126 Private Firmware addService Status Trace",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- private_firmware_mounts_requested: `{contract.get('private_firmware_mounts_requested', '')}`",
        f"- private_firmware_mnt_mounted: `{contract.get('private_firmware_mnt_mounted', '')}`",
        f"- private_firmware_modem_mounted: `{contract.get('private_firmware_modem_mounted', '')}`",
        f"- vndservicemanager_ready: `{contract.get('vndservicemanager_readiness.ready', '')}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## addService Status",
        "",
        "```json",
        json.dumps(statuses, indent=2, sort_keys=True),
        "```",
        "",
        "## Tracefs Counts",
        "",
        "```json",
        json.dumps(counts, indent=2, sort_keys=True),
        "```",
        "",
        "## Steps",
        "",
        v1125.base.markdown_table(["name", "ok", "rc", "duration_sec", "file"], step_rows),
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v1125.base.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v1125.base.DEFAULT_PORT)
    parser.add_argument("--device-ip", default=v1125.base.DEFAULT_DEVICE_IP)
    parser.add_argument("--tcp-port", type=int, default=v1125.base.DEFAULT_TCP_PORT)
    parser.add_argument("--tcp-timeout", type=float, default=v1125.DEFAULT_TCP_TIMEOUT_SEC)
    parser.add_argument("--busybox", default=v1125.base.DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=v1125.base.DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=v1125.base.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=v1125.DEFAULT_EXECNS_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=v1125.DEFAULT_EXECNS_HELPER_MARKER)
    parser.add_argument("--v1125-manifest", type=Path, default=DEFAULT_V1125_MANIFEST)
    parser.add_argument("--property-root", default=v1125.base.DEFAULT_PROPERTY_ROOT)
    parser.add_argument("--helper-timeout-sec", type=int, default=4)
    parser.add_argument("--toybox-timeout-sec", type=int, default=18)
    parser.add_argument("--tracefs-duration-sec", type=int, default=v1125.DEFAULT_TRACEFS_DURATION_SEC)
    parser.add_argument("--vendor-block", default=v1125.DEFAULT_VENDOR_BLOCK)
    parser.add_argument("--vendor-mount", default=v1125.DEFAULT_VENDOR_MOUNT)
    parser.add_argument("--pm-binary", default=v1125.DEFAULT_PM_BINARY)
    parser.add_argument("--tracefs-root", default=v1125.DEFAULT_TRACEFS_ROOT)
    parser.add_argument("--work-dir", default="/cache/a90-runtime/v1126")
    parser.add_argument("--child-script", default="/cache/a90-runtime/v1126/private-firmware-pm-observer.sh")
    parser.add_argument("--collector-script", default="/cache/a90-runtime/v1126/private-firmware-addservice-tracefs-collector.sh")
    parser.add_argument("--child-output", default="/cache/a90-runtime/v1126/private-firmware-pm-observer-output.txt")
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
