#!/usr/bin/env python3
"""V1102 tracefs-only PM server early-register classifier.

This gate replays the V1095 bounded PM provider + pm-proxy + cnss-daemon
observer, while arming dynamic tracefs uprobes on vendor
libperipheral_client.so and pm-service with ARM64 register fetchargs. It
answers one narrow question: where execution stops between `pm-service`
register entry `0x6048` and supported-peripheral match `0x60cc`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
from pathlib import Path
from typing import Any

import native_wifi_pm_cnss_voter_surface_live_v1095 as v1095
import native_wifi_pm_service_trigger_observer_live_v1066 as base
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1102-pm-server-early-register-tracefs-live")
DEFAULT_V1101_MANIFEST = Path("tmp/wifi/v1101-pm-server-register-path-tracefs-live/manifest.json")
DEFAULT_EXECNS_HELPER_SHA256 = "7920eeb353e1d6f09ded42efc84e7a8549fdb407cdd8236307422ebf2a9108e4"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v206"
DEFAULT_VENDOR_MOUNT = "/mnt/vendor"
DEFAULT_VENDOR_BLOCK = "/dev/block/sda29"
DEFAULT_PERIPHERAL_CLIENT = "/mnt/vendor/lib64/libperipheral_client.so"
DEFAULT_PM_SERVICE = "/mnt/vendor/bin/pm-service"
DEFAULT_TRACEFS_ROOT = "/sys/kernel/tracing"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1102"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1102/pm-cnss-voter-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1102/pm-server-early-register-tracefs-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1102/pm-cnss-voter-output.txt"
LATEST_POINTER = Path("tmp/wifi/latest-v1102-pm-server-early-register-tracefs-live.txt")

EVENT_SPECS = (
    ("pm_client_register_entry", "client", "6ec8", "peripheral=+0(%x2):string client=+0(%x3):string out=%x5"),
    ("pm_client_register_ret", "client", "6ec8", "ret=$retval"),
    ("pm_client_connect_entry", "client", "7544", ""),
    ("pm_client_connect_ret", "client", "7544", "ret=$retval"),
    ("pm_server_register_entry", "service", "6048", "out_client=%x4 out_state=%x5"),
    ("pm_server_register_saved_lr", "service", "604c", ""),
    ("pm_server_register_frame_ready", "service", "6060", ""),
    ("pm_server_register_zero_out_client", "service", "6064", "out_client=%x4"),
    ("pm_server_register_zero_out_state", "service", "6068", "out_state=%x5"),
    ("pm_server_register_list_head_load", "service", "606c", "manager=%x0"),
    ("pm_server_register_request_save", "service", "6074", "peripheral_obj=%x1"),
    ("pm_server_register_list_empty_cmp", "service", "6078", "head=%x28 node=%x27"),
    ("pm_server_register_loop_node", "service", "6094", "node=%x27"),
    ("pm_server_register_name_helper_call", "service", "609c", "entry=%x25"),
    ("pm_server_register_name_helper_return", "service", "60a0", "helper_ret=%x0 request_obj=%x24"),
    ("pm_server_register_candidate_load", "service", "60a4", "helper_ret=%x0"),
    ("pm_server_register_strcmp_call", "service", "60ac", "candidate=+0(%x0):string requested=+0(%x1):string"),
    ("pm_server_register_strcmp_result", "service", "60b0", "strcmp_ret=%x0"),
    ("pm_server_register_loop_advance", "service", "60b4", "node=%x27"),
    ("pm_server_register_loop_compare", "service", "60b8", "head=%x28 node=%x27"),
    ("pm_server_register_no_match_branch", "service", "60c0", ""),
    ("pm_server_register_empty_branch", "service", "60c4", ""),
    ("pm_server_register_match", "service", "60cc", "entry=%x25"),
    ("pm_server_register_ret", "service", "6048", "ret=$retval"),
    ("pm_server_connect_entry", "service", "6270", ""),
    ("pm_server_connect_ret", "service", "6270", "ret=$retval"),
)

SERVER_EVENT_LABELS = {label for label, binary_key, _offset, _fetch in EVENT_SPECS if binary_key == "service"}
RETURN_EVENT_LABELS = {label for label, _binary_key, _offset, _fetch in EVENT_SPECS if label.endswith("_ret")}
PM_SERVER_REGISTER_ORDER = (
    "pm_server_register_entry",
    "pm_server_register_saved_lr",
    "pm_server_register_frame_ready",
    "pm_server_register_zero_out_client",
    "pm_server_register_zero_out_state",
    "pm_server_register_list_head_load",
    "pm_server_register_request_save",
    "pm_server_register_list_empty_cmp",
    "pm_server_register_loop_node",
    "pm_server_register_name_helper_call",
    "pm_server_register_name_helper_return",
    "pm_server_register_candidate_load",
    "pm_server_register_strcmp_call",
    "pm_server_register_strcmp_result",
    "pm_server_register_loop_advance",
    "pm_server_register_loop_compare",
    "pm_server_register_no_match_branch",
    "pm_server_register_empty_branch",
    "pm_server_register_match",
    "pm_server_register_ret",
)
TRANSACTION_METHODS = {
    "0x1": "register",
    "0x2": "unregister",
    "0x3": "connect",
    "0x4": "disconnect",
    "0x5": "event_acknowledge",
    "0x6": "show_peripherals",
    "0x5f4e5446": "interface_transaction",
}

ALLOWED_V1101_DECISIONS = {
    "v1101-cnss-server-register-no-return-at-pm_server_register_entry",
}

KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
EVENT_COUNT_RE = re.compile(r"^event\.([A-Za-z0-9_]+)\.count=(\d+)$", re.MULTILINE)
TRACE_RESULT_RE = re.compile(r"^result=(tracefs-uprobe-[A-Za-z0-9_-]+)$", re.MULTILINE)
TRACE_LINE_RE = re.compile(r"^\s*(?P<comm>.+)-(?P<pid>\d+)\s+\[[^\]]+\].*:\s+(?P<label>[A-Za-z0-9_]+):")
CODE_RE = re.compile(r"\bcode=(0x[0-9A-Fa-f]+|[0-9]+)")
FLAGS_RE = re.compile(r"\bflags=(0x[0-9A-Fa-f]+|[0-9]+)")
RET_RE = re.compile(r"\bret=(0x[0-9A-Fa-f]+|-?[0-9]+)")
CLIENT_RE = re.compile(r'\bclient="?([^"\s]+)"?')
PERIPHERAL_RE = re.compile(r'\bperipheral="?([^"\s]+)"?')
STATE_RE = re.compile(r"\bstate=(0x[0-9A-Fa-f]+|-?[0-9]+)")
STRCMP_RET_RE = re.compile(r"\bstrcmp_ret=(0x[0-9A-Fa-f]+|-?[0-9]+)")


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


def step_payload(store: EvidenceStore, step: dict[str, Any]) -> str:
    file_name = step.get("file")
    if not file_name:
        return ""
    path = store.run_dir / str(file_name)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


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


def synthetic_vendor_block(args: argparse.Namespace) -> str:
    return args.vendor_block


def synthetic_vendor_marker(args: argparse.Namespace) -> str:
    return f"{args.work_dir}/created-devblock-sda29"


def remote_sha_check(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], name: str, path: str, expected: str) -> dict[str, Any]:
    step = base.run_tcpctl(args, store, steps, name, [args.toybox, "sha256sum", path], timeout=30.0)
    text = step_payload(store, step)
    return {"file": step["file"], "ok": expected in text, "expected": expected}


def remote_marker_check(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    step = base.run_tcpctl(args, store, steps, "execns-helper-usage", [args.helper], timeout=30.0)
    text = step_payload(store, step)
    return {
        "file": step["file"],
        "marker_ok": args.helper_marker in text,
        "mode_ok": base.DEFAULT_MODE in text,
        "start_cnss_flag_ok": "--pm-observer-start-cnss-after-provider" in text,
    }


def pm_cnss_child_command(args: argparse.Namespace) -> list[str]:
    command = v1095.helper_command(args)
    if len(command) >= 3 and command[0] == args.toybox and command[1] == "timeout":
        command = command[3:]
    return command


def write_child_script(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    command = pm_cnss_child_command(args)
    grep_pattern = (
        r"^(A90_EXECNS_(BEGIN|END|STDOUT_END)|"
        r"pm_service_trigger_observer\.|"
        r"wifi_vndservice_query\.|"
        r"wifi_companion_qrtr_readback\.)"
    )
    script = "\n".join([
        f"#!{args.busybox} sh",
        f"OUT={shlex.quote(args.child_output)}",
        f"{args.busybox} mkdir -p {shlex.quote(args.work_dir)}",
        " ".join(shlex.quote(part) for part in command) + ' > "$OUT" 2>&1',
        "rc=$?",
        f"{args.busybox} grep -E {shlex.quote(grep_pattern)} \"$OUT\" || true",
        f"echo v1102.child_full_output={shlex.quote(args.child_output)}",
        "echo v1102.child_rc=$rc",
        "exit $rc",
        "",
    ])
    store.write_text("host/pm-cnss-voter-child-script.txt", script)
    base.run_a90ctl(args, store, steps, "workdir-mkdir", ["run", args.busybox, "mkdir", "-p", args.work_dir], timeout=12.0)
    append_device_file(args, store, steps, args.child_script, script, "child-script")


def tracefs_collector_script(args: argparse.Namespace) -> str:
    labels = " ".join(label for label, _binary_key, _offset, _fetch in EVENT_SPECS)
    grep_pattern = "|".join(re.escape(label) for label, _binary_key, _offset, _fetch in EVENT_SPECS)
    register_calls = "\n".join(
        f"register_event {shlex.quote(label)} {shlex.quote(binary_key)} {shlex.quote(offset)} {shlex.quote(fetch)}"
        for label, binary_key, offset, fetch in EVENT_SPECS
    )
    enable_calls = "\n".join(
        f"enable_event {shlex.quote(label)}"
        for label, _binary_key, _offset, _fetch in EVENT_SPECS
    )
    count_calls = "\n".join(
        f"count_event {shlex.quote(label)}"
        for label, _binary_key, _offset, _fetch in EVENT_SPECS
    )
    return f"""#!{args.busybox} sh
BB={shlex.quote(args.busybox)}
TRACE={shlex.quote(args.tracefs_root)}
GROUP=a90pm1102
CLIENT_BIN={shlex.quote(args.peripheral_client)}
SERVICE_BIN={shlex.quote(args.pm_service)}
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

echo tracefs_uprobe_collector=v1102
echo tracefs_root="$TRACE"
echo client_binary="$CLIENT_BIN"
echo service_binary="$SERVICE_BIN"
echo group="$GROUP"
echo child_log="$CHILD_LOG"
echo event_count={len(EVENT_SPECS)}

if ! $BB test -e "$TRACE/uprobe_events"; then
  echo result=tracefs-uprobe-events-missing
  exit 1
fi
if ! $BB test -r "$CLIENT_BIN"; then
  echo result=tracefs-uprobe-client-binary-missing
  exit 1
fi
if ! $BB test -r "$SERVICE_BIN"; then
  echo result=tracefs-uprobe-service-binary-missing
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
  binary_key="$2"
  offset="$3"
  fetch="$4"
  case "$binary_key" in
    client) bin="$CLIENT_BIN" ;;
    service) bin="$SERVICE_BIN" ;;
    *)
      echo "event.$label.binary=unknown"
      echo result=tracefs-uprobe-binary-key-failed
      exit 1
      ;;
  esac
  if $BB test -e "$TRACE/events/$GROUP/$label/enable"; then
    echo 0 > "$TRACE/events/$GROUP/$label/enable" 2>/dev/null || true
  fi
  echo "-:$GROUP/$label" >> "$TRACE/uprobe_events" 2>/dev/null || true
  probe_type=p
  case "$label" in
    *_ret) probe_type=r ;;
  esac
  if $BB test -n "$fetch"; then
    event_line="$probe_type:$GROUP/$label $bin:0x$offset $fetch"
  else
    event_line="$probe_type:$GROUP/$label $bin:0x$offset"
  fi
  if echo "$event_line" >> "$TRACE/uprobe_events" 2>/dev/null; then
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
$BB grep -E '^(A90_EXECNS_(END|STDOUT_END)|pm_service_trigger_observer\\.|wifi_vndservice_query\\.|wifi_companion_qrtr_readback\\.|v1102\\.)' "$CHILD_LOG" 2>/dev/null || true
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
    store.write_text("host/pm-server-early-register-tracefs-collector-script.txt", script)
    append_device_file(args, store, steps, args.collector_script, script, "collector-script")


def collect_trace_lines(text: str) -> list[str]:
    trace_lines: list[str] = []
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
    return trace_lines


def parse_tracefs_output(text: str) -> dict[str, Any]:
    keys = parse_keys(text)
    result_match = TRACE_RESULT_RE.search(text)
    counts = {label: int(value) for label, value in EVENT_COUNT_RE.findall(text)}
    trace_lines = collect_trace_lines(text)
    by_comm: dict[str, dict[str, int]] = {}
    by_label_comm: dict[str, dict[str, int]] = {}
    return_values_by_comm: dict[str, dict[str, list[str]]] = {}
    client_register_args_by_comm: dict[str, list[dict[str, str]]] = {}
    server_register_args_by_comm: dict[str, list[dict[str, str]]] = {}
    state_values_by_comm: dict[str, list[str]] = {}
    strcmp_returns_by_comm: dict[str, list[str]] = {}
    last_label_by_comm: dict[str, str] = {}
    cnss_server_register_comms: set[str] = set()
    pending_cnss_register = False
    cnss_server_register_inferences: list[dict[str, str]] = []
    for line in trace_lines:
        match = TRACE_LINE_RE.match(line)
        if not match:
            continue
        comm = match.group("comm").strip()
        label = match.group("label")
        by_comm.setdefault(comm, {})
        by_comm[comm][label] = by_comm[comm].get(label, 0) + 1
        last_label_by_comm[comm] = label
        by_label_comm.setdefault(label, {})
        by_label_comm[label][comm] = by_label_comm[label].get(comm, 0) + 1
        if label in RETURN_EVENT_LABELS:
            ret_match = RET_RE.search(line)
            if ret_match:
                return_values_by_comm.setdefault(comm, {})
                return_values_by_comm[comm].setdefault(label, [])
                return_values_by_comm[comm][label].append(ret_match.group(1))
        if label == "pm_client_register_entry":
            client_match = CLIENT_RE.search(line)
            peripheral_match = PERIPHERAL_RE.search(line)
            client_register_args_by_comm.setdefault(comm, [])
            client_register_args_by_comm[comm].append({
                "client": client_match.group(1) if client_match else "",
                "peripheral": peripheral_match.group(1) if peripheral_match else "",
            })
            if comm == "cnss-daemon" and client_match and client_match.group(1) == "cnss-daemon":
                pending_cnss_register = True
        if label == "pm_server_register_entry":
            client_match = CLIENT_RE.search(line)
            peripheral_match = PERIPHERAL_RE.search(line)
            client = client_match.group(1) if client_match else ""
            peripheral = peripheral_match.group(1) if peripheral_match else ""
            server_register_args_by_comm.setdefault(comm, [])
            server_register_args_by_comm[comm].append({
                "client": client_match.group(1) if client_match else "",
                "peripheral": peripheral_match.group(1) if peripheral_match else "",
            })
            if client == "cnss-daemon" and peripheral == "modem":
                cnss_server_register_comms.add(comm)
            elif pending_cnss_register:
                cnss_server_register_comms.add(comm)
                cnss_server_register_inferences.append({
                    "comm": comm,
                    "basis": "first-pm_server_register_entry-after-cnss-client-register-entry",
                    "line": line.strip(),
                })
                pending_cnss_register = False
        if label == "pm_server_register_state_read":
            state_match = STATE_RE.search(line)
            if state_match:
                state_values_by_comm.setdefault(comm, [])
                state_values_by_comm[comm].append(state_match.group(1))
        if label == "pm_server_register_strcmp_result":
            strcmp_match = STRCMP_RET_RE.search(line)
            if strcmp_match:
                strcmp_returns_by_comm.setdefault(comm, [])
                strcmp_returns_by_comm[comm].append(strcmp_match.group(1))
    pm_contract = {
        key[len("pm_service_trigger_observer."):]: value
        for key, value in keys.items()
        if key.startswith("pm_service_trigger_observer.")
    }
    per_mgr_pid = (
        pm_contract.get("fd_match.after_cnss_daemon_per_mgr_vndbinder.pid") or
        pm_contract.get("fd_match.after_cnss_daemon_per_mgr_subsys_modem.pid") or
        pm_contract.get("fd_match.after_per_proxy_per_mgr_vndbinder.pid") or
        pm_contract.get("fd_match.after_per_proxy_per_mgr_subsys_modem.pid") or
        ""
    )
    server_hits_by_comm = {
        comm: {
            label: count
            for label, count in labels.items()
            if label in SERVER_EVENT_LABELS
        }
        for comm, labels in by_comm.items()
        if any(label in SERVER_EVENT_LABELS for label in labels)
    }
    per_mgr_binder_prefix = f"Binder:{per_mgr_pid}_" if per_mgr_pid else ""
    per_mgr_binder_server_hits = sum(
        count
        for comm, labels in server_hits_by_comm.items()
        if per_mgr_binder_prefix and comm.startswith(per_mgr_binder_prefix)
        for count in labels.values()
    )
    cnss_hits = {
        label: count
        for label, comms in by_label_comm.items()
        for comm, count in comms.items()
        if "cnss" in comm
    }
    return {
        "result": result_match.group(1) if result_match else keys.get("result", ""),
        "counts": counts,
        "hit_count": sum(counts.values()),
        "trace_lines": trace_lines[:160],
        "trace_line_count": len(trace_lines),
        "by_comm": by_comm,
        "by_label_comm": by_label_comm,
        "cnss_daemon_hit_count": sum(cnss_hits.values()),
        "cnss_daemon_hits": cnss_hits,
        "pm_server_event_hit_count": sum(
            count
            for labels in server_hits_by_comm.values()
            for count in labels.values()
        ),
        "pm_server_ontransact_hit_count": sum(
            count
            for labels in server_hits_by_comm.values()
            for count in labels.values()
        ),
        "pm_server_hits_by_comm": server_hits_by_comm,
        "transaction_methods": TRANSACTION_METHODS,
        "return_values_by_comm": return_values_by_comm,
        "client_register_args_by_comm": client_register_args_by_comm,
        "server_register_args_by_comm": server_register_args_by_comm,
        "cnss_server_register_comms": sorted(cnss_server_register_comms),
        "cnss_server_register_inferences": cnss_server_register_inferences,
        "cnss_server_register_hits_by_comm": {
            comm: {
                label: by_comm.get(comm, {}).get(label, 0)
                for label in PM_SERVER_REGISTER_ORDER
                if by_comm.get(comm, {}).get(label, 0)
            }
            for comm in sorted(cnss_server_register_comms)
        },
        "cnss_server_register_last_label_by_comm": {
            comm: last_label_by_comm.get(comm, "")
            for comm in sorted(cnss_server_register_comms)
        },
        "cnss_server_register_last_label": next(
            (
                last_label_by_comm.get(comm, "")
                for comm in sorted(cnss_server_register_comms)
                if last_label_by_comm.get(comm, "")
            ),
            "",
        ),
        "state_values_by_comm": state_values_by_comm,
        "strcmp_returns_by_comm": strcmp_returns_by_comm,
        "per_mgr_pid": per_mgr_pid,
        "per_mgr_binder_server_hit_count": per_mgr_binder_server_hits,
        "register_failures": [line.strip() for line in text.splitlines() if ".register=failed" in line],
        "enable_failures": [line.strip() for line in text.splitlines() if ".enable=failed" in line],
        "disable_failures": [line.strip() for line in text.splitlines() if ".disable=failed" in line],
        "cleanup_failures": [line.strip() for line in text.splitlines() if ".cleanup=remove-failed" in line],
        "child_rc": keys.get("child.rc", keys.get("v1102.child_rc", "")),
        "pm_contract": pm_contract,
        "forbidden_true": {
            key: value
            for key, value in pm_contract.items()
            if key in {
                "mdm_helper_start_executed",
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
    lib_step = base.run_a90ctl(args, store, steps, "peripheral-client-stat", ["run", args.busybox, "stat", args.peripheral_client], timeout=15.0, allow_error=True)
    analysis["peripheral_client_visible"] = bool(lib_step.get("ok"))
    service_step = base.run_a90ctl(args, store, steps, "pm-service-stat", ["run", args.busybox, "stat", args.pm_service], timeout=15.0, allow_error=True)
    analysis["pm_service_visible"] = bool(service_step.get("ok"))
    analysis["execns_helper"] = remote_sha_check(args, store, steps, "execns-helper-sha", args.helper, args.helper_sha256)
    analysis["execns_usage"] = remote_marker_check(args, store, steps)
    write_child_script(args, store, steps)
    write_collector_script(args, store, steps)

    collector_step = base.run_a90ctl(
        args,
        store,
        steps,
        "pm-server-early-register-tracefs-observer",
        ["run", args.busybox, "sh", args.collector_script],
        timeout=args.tracefs_duration_sec + 100.0,
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
        ("--allow-cnss-daemon-start", args.allow_cnss_daemon_start),
        ("--assume-yes", args.assume_yes),
    ):
        if not enabled:
            missing.append(flag)
    return missing


def decide(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1102-pm-server-early-register-tracefs-plan-ready",
            True,
            "plan-only; no tracefs write, PM actor, CNSS actor, or Wi-Fi action executed",
            "run V1102 with explicit allow flags",
        )
    v1101_decision = (manifest.get("v1101") or {}).get("decision")
    if v1101_decision not in ALLOWED_V1101_DECISIONS:
        return (
            "v1102-v1101-predecessor-missing",
            False,
            f"unexpected V1101 decision={v1101_decision!r}",
            "rerun or inspect V1101 before PM server early-register tracefs classifier",
        )
    missing = required_flags(args)
    if missing:
        return (
            "v1102-pm-server-early-register-tracefs-approval-required",
            False,
            "missing explicit flags: " + ", ".join(missing),
            "rerun with all V1102 allow flags",
        )
    analysis = manifest.get("analysis") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    post = analysis.get("post_surface") or {}
    contract = tracefs.get("pm_contract") or {}
    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1102-execns-helper-sha-mismatch", False, "remote execns helper is not v206", "redeploy helper v206")
    usage = analysis.get("execns_usage") or {}
    if not (usage.get("marker_ok") and usage.get("mode_ok") and usage.get("start_cnss_flag_ok")):
        return ("v1102-execns-helper-usage-mismatch", False, f"usage={usage}", "redeploy or rebuild helper v206")
    if not analysis.get("peripheral_client_visible"):
        return ("v1102-peripheral-client-not-visible", False, "read-only vendor mount did not expose libperipheral_client.so", "repair synthetic sda29 mount before retry")
    if not analysis.get("pm_service_visible"):
        return ("v1102-pm-service-not-visible", False, "read-only vendor mount did not expose pm-service", "repair synthetic sda29 mount before retry")
    if tracefs.get("result") != "tracefs-uprobe-pass":
        return ("v1102-tracefs-uprobe-failed", False, f"tracefs result={tracefs.get('result')}", "inspect tracefs collector transcript")
    if tracefs.get("register_failures") or tracefs.get("enable_failures") or tracefs.get("cleanup_failures"):
        return ("v1102-tracefs-uprobe-cleanup-review", False, "register/enable/cleanup failures present", "inspect tracefs cleanup before retry")
    if tracefs.get("forbidden_true"):
        return ("v1102-forbidden-action-observed", False, f"forbidden={tracefs.get('forbidden_true')}", "stop and audit helper contract")
    if post.get("forbidden_actor_hits") or post.get("wifi_link_hits"):
        return ("v1102-postflight-safety-review", False, "forbidden actors or Wi-Fi link appeared", "cleanup device before continuing")
    if contract.get("cnss_daemon_start_executed") != "1":
        return ("v1102-cnss-daemon-not-started", False, "child did not execute CNSS phase", "repair child command before retry")
    if tracefs.get("hit_count", 0) <= 0:
        return ("v1102-pm-server-uprobe-no-hit", False, "no tracefs lines were captured", "verify binary inode mappings or offsets")
    server_hits = int(tracefs.get("pm_server_event_hit_count") or 0)
    per_mgr_server_hits = int(tracefs.get("per_mgr_binder_server_hit_count") or 0)
    cnss_hits = int(tracefs.get("cnss_daemon_hit_count") or 0)
    mdm3_state = contract.get("post_provider_surface.after_cnss_daemon.mdm3_state") or ""
    return_values = tracefs.get("return_values_by_comm") or {}
    cnss_register_returns: list[str] = []
    cnss_connect_returns: list[str] = []
    for comm, labels in return_values.items():
        if "cnss" not in comm:
            continue
        cnss_register_returns.extend(labels.get("pm_client_register_ret", []))
        cnss_connect_returns.extend(labels.get("pm_client_connect_ret", []))
    by_label_comm = tracefs.get("by_label_comm") or {}
    cnss_register_entries = sum(
        count for comm, count in (by_label_comm.get("pm_client_register_entry") or {}).items()
        if "cnss" in comm
    )
    cnss_connect_entries = sum(
        count for comm, count in (by_label_comm.get("pm_client_connect_entry") or {}).items()
        if "cnss" in comm
    )
    cnss_server_comms = tracefs.get("cnss_server_register_comms") or []
    cnss_server_hits_by_comm = tracefs.get("cnss_server_register_hits_by_comm") or {}
    cnss_server_label_counts: dict[str, int] = {}
    cnss_server_register_returns: list[str] = []
    for comm in cnss_server_comms:
        labels = cnss_server_hits_by_comm.get(comm) or {}
        for label, count in labels.items():
            cnss_server_label_counts[label] = cnss_server_label_counts.get(label, 0) + int(count)
        cnss_server_register_returns.extend(
            (return_values.get(comm) or {}).get("pm_server_register_ret", [])
        )
    cnss_server_register_entries = cnss_server_label_counts.get("pm_server_register_entry", 0)
    last_server_checkpoint = "pm_server_register_entry"
    for label in PM_SERVER_REGISTER_ORDER:
        if cnss_server_label_counts.get(label, 0) > 0:
            last_server_checkpoint = label
    last_server_checkpoint = tracefs.get("cnss_server_register_last_label") or last_server_checkpoint
    nonzero_cnss_register_returns = [value for value in cnss_register_returns if value not in ("0", "0x0")]
    zero_cnss_register_returns = [value for value in cnss_register_returns if value in ("0", "0x0")]
    if cnss_register_entries <= 0:
        return ("v1102-cnss-register-entry-missing", False, "cnss-daemon did not enter pm_client_register", "return to V1096 CNSS PM client path gate")
    if cnss_server_register_entries <= 0:
        return (
            "v1102-cnss-server-register-entry-missing",
            True,
            (
                f"cnss_client_register_entries={cnss_register_entries} "
                f"server_hits={server_hits} per_mgr_pid={tracefs.get('per_mgr_pid')} mdm3_state={mdm3_state}"
            ),
            "classify Binder delivery from cnss-daemon proxy to pm-service register implementation",
        )
    if cnss_server_label_counts.get("pm_server_register_no_peripheral", 0) > 0:
        return (
            "v1102-cnss-register-no-supported-peripheral",
            True,
            f"server_labels={cnss_server_label_counts} mdm3_state={mdm3_state}",
            "classify pm-service supported peripheral table and vendor init inputs",
        )
    if cnss_server_label_counts.get("pm_server_register_permission_denied", 0) > 0:
        return (
            "v1102-cnss-register-permission-denied",
            True,
            f"server_labels={cnss_server_label_counts} mdm3_state={mdm3_state}",
            "classify pm-service UID permission model for cnss-daemon in native init",
        )
    if not cnss_server_register_returns:
        return (
            f"v1102-cnss-server-register-no-return-at-{last_server_checkpoint}",
            True,
            (
                f"server_labels={cnss_server_label_counts} cnss_client_register_ret={cnss_register_returns} "
                f"mdm3_state={mdm3_state}"
            ),
            "trace the next pm-service helper below the last server checkpoint",
        )
    if cnss_server_register_returns and not cnss_register_returns:
        return (
            "v1102-cnss-server-returned-client-still-blocked",
            True,
            (
                f"server_register_ret={cnss_server_register_returns} "
                f"server_labels={cnss_server_label_counts} mdm3_state={mdm3_state}"
            ),
            "classify Binder reply delivery or client-side wait after pm-service returns",
        )
    if not cnss_register_returns:
        return (
            "v1102-cnss-pm-register-blocks-after-code1-mdm3-still-offline",
            True,
            (
                f"cnss_register_entries={cnss_register_entries} cnss_connect_entries={cnss_connect_entries} "
                f"server_labels={cnss_server_label_counts} mdm3_state={mdm3_state}"
            ),
            "classify why PM server code 0x1/register does not return to cnss-daemon",
        )
    if nonzero_cnss_register_returns and cnss_connect_entries <= 0:
        return (
            "v1102-cnss-pm-register-fails-before-connect-mdm3-still-offline",
            True,
            (
                f"cnss_register_ret={cnss_register_returns} cnss_connect_entries={cnss_connect_entries} "
                f"server_register_ret={cnss_server_register_returns} mdm3_state={mdm3_state}"
            ),
            "capture PM server code 0x1 reply fields or server-side register failure reason",
        )
    if zero_cnss_register_returns and cnss_connect_entries <= 0:
        return (
            "v1102-cnss-pm-register-succeeds-but-connect-not-called",
            True,
            (
                f"cnss_register_ret={cnss_register_returns} cnss_connect_entries={cnss_connect_entries} "
                f"server_register_ret={cnss_server_register_returns} mdm3_state={mdm3_state}"
            ),
            "trace cnss-daemon callsite state between register return and pm_client_connect",
        )
    if cnss_connect_entries > 0:
        if any(value not in ("0", "0x0") for value in cnss_connect_returns):
            return (
                "v1102-cnss-pm-connect-fails-mdm3-still-offline",
                True,
                (
                    f"cnss_register_ret={cnss_register_returns} cnss_connect_ret={cnss_connect_returns} "
                    f"server_register_ret={cnss_server_register_returns} mdm3_state={mdm3_state}"
                ),
                "capture PM server code 0x3 reply fields or lower eSoC side effects",
            )
        return (
            "v1102-cnss-pm-connect-succeeds-mdm3-still-offline",
            True,
            (
                f"cnss_register_ret={cnss_register_returns} cnss_connect_ret={cnss_connect_returns} "
                f"server_register_ret={cnss_server_register_returns} per_mgr_server_hits={per_mgr_server_hits} "
                f"cnss_hits={cnss_hits} mdm3_state={mdm3_state}"
            ),
            "classify lower PM/eSoC action after successful CNSS connect",
        )
    if server_hits > 0:
        return (
            "v1102-pm-server-event-hit-unmapped-binder-thread",
            True,
            f"server_hits={server_hits} per_mgr_pid={tracefs.get('per_mgr_pid')} hits={tracefs.get('pm_server_hits_by_comm')}",
            "map Binder server thread ownership before interpreting PM service response",
        )
    if cnss_hits > 0:
        return (
            "v1102-cnss-client-hit-but-pm-server-entry-missing",
            True,
            f"cnss_hits={cnss_hits} by_comm={tracefs.get('by_comm')}",
            "classify Binder delivery or PeripheralManager proxy transaction gap",
        )
    return (
        "v1102-pm-client-and-server-not-called",
        True,
        f"total_hits={tracefs.get('hit_count')} by_comm={tracefs.get('by_comm')}",
        "inspect trace offsets and child sequence before retry",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1101_manifest = load_json(args.v1101_manifest)
    manifest: dict[str, Any] = {
        "cycle": "v1102",
        "generated_at": now_iso(),
        "command": args.command,
        "v1101": {
            "manifest": str(repo_path(args.v1101_manifest)),
            "decision": v1101_manifest.get("decision", ""),
            "pass": bool(v1101_manifest.get("pass")),
        },
        "event_specs": [
            f"{label}:{binary_key}:0x{offset}" + (f":{fetch}" if fetch else "")
            for label, binary_key, offset, fetch in EVENT_SPECS
        ],
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
        and v1101_manifest.get("decision") in ALLOWED_V1101_DECISIONS
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
    by_comm = tracefs.get("by_comm") or {}
    step_rows = [[step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")] for step in manifest.get("steps", [])]
    return "\n".join([
        "# V1102 PM Server Early Register Tracefs Live",
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
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Tracefs Uprobe",
        "",
        f"- result: `{tracefs.get('result', '')}`",
        f"- hit_count: `{tracefs.get('hit_count', '')}`",
        f"- cnss_daemon_hit_count: `{tracefs.get('cnss_daemon_hit_count', '')}`",
        f"- pm_server_event_hit_count: `{tracefs.get('pm_server_event_hit_count', '')}`",
        f"- per_mgr_binder_server_hit_count: `{tracefs.get('per_mgr_binder_server_hit_count', '')}`",
        f"- per_mgr_pid: `{tracefs.get('per_mgr_pid', '')}`",
        f"- return_values_by_comm: `{tracefs.get('return_values_by_comm', {})}`",
        f"- client_register_args_by_comm: `{tracefs.get('client_register_args_by_comm', {})}`",
        f"- server_register_args_by_comm: `{tracefs.get('server_register_args_by_comm', {})}`",
        f"- cnss_server_register_comms: `{tracefs.get('cnss_server_register_comms', [])}`",
        f"- cnss_server_register_inferences: `{tracefs.get('cnss_server_register_inferences', [])}`",
        f"- cnss_server_register_hits_by_comm: `{tracefs.get('cnss_server_register_hits_by_comm', {})}`",
        f"- cnss_server_register_last_label: `{tracefs.get('cnss_server_register_last_label', '')}`",
        f"- strcmp_returns_by_comm: `{tracefs.get('strcmp_returns_by_comm', {})}`",
        f"- trace_line_count: `{tracefs.get('trace_line_count', '')}`",
        f"- child_rc: `{tracefs.get('child_rc', '')}`",
        "",
        "```json",
        json.dumps({
            "counts": counts,
            "by_comm": by_comm,
            "return_values_by_comm": tracefs.get("return_values_by_comm") or {},
            "client_register_args_by_comm": tracefs.get("client_register_args_by_comm") or {},
            "server_register_args_by_comm": tracefs.get("server_register_args_by_comm") or {},
            "cnss_server_register_comms": tracefs.get("cnss_server_register_comms") or [],
            "cnss_server_register_inferences": tracefs.get("cnss_server_register_inferences") or [],
            "cnss_server_register_hits_by_comm": tracefs.get("cnss_server_register_hits_by_comm") or {},
            "cnss_server_register_last_label": tracefs.get("cnss_server_register_last_label") or "",
            "cnss_server_register_last_label_by_comm": tracefs.get("cnss_server_register_last_label_by_comm") or {},
            "state_values_by_comm": tracefs.get("state_values_by_comm") or {},
            "strcmp_returns_by_comm": tracefs.get("strcmp_returns_by_comm") or {},
        }, indent=2, sort_keys=True),
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
    parser.add_argument("--v1101-manifest", type=Path, default=DEFAULT_V1101_MANIFEST)
    parser.add_argument("--property-root", default=base.DEFAULT_PROPERTY_ROOT)
    parser.add_argument("--helper-timeout-sec", type=int, default=4)
    parser.add_argument("--toybox-timeout-sec", type=int, default=18)
    parser.add_argument("--tracefs-duration-sec", type=int, default=18)
    parser.add_argument("--vendor-block", default=DEFAULT_VENDOR_BLOCK)
    parser.add_argument("--vendor-mount", default=DEFAULT_VENDOR_MOUNT)
    parser.add_argument("--peripheral-client", default=DEFAULT_PERIPHERAL_CLIENT)
    parser.add_argument("--pm-service", default=DEFAULT_PM_SERVICE)
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
    parser.add_argument("--allow-cnss-daemon-start", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    v1095.patch_defaults()
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
