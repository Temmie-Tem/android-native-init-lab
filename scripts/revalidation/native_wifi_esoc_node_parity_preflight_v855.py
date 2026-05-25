#!/usr/bin/env python3
"""V855 bounded native eSoC/subsys node parity preflight.

V854 selected native Android node/ueventd parity as the next safe live gate.
This runner materializes only Android-equivalent `/dev/esoc-0`,
`/dev/subsys_esoc0`, and `/dev/subsys_modem` metadata, verifies that no actor
opened them, cleans up the nodes it created, and checks native health. It never
opens/ioctls those nodes and never starts Wi-Fi actors or HAL.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v855-esoc-node-parity-preflight")
LATEST_POINTER = Path("tmp/wifi/latest-v855-esoc-node-parity-preflight.txt")
DEFAULT_V854_MANIFEST = Path("tmp/wifi/v854-esoc-actor-parity-classifier/manifest.json")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_MARKER = "/tmp/a90-v855-esoc-node-parity.created"

SECRET_RE = re.compile(r"(made by|creator: made by) [^\r\n]+", re.IGNORECASE)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

TARGET_NODES = (
    ("/dev/esoc-0", "0660", "0", "1001", "484", "0"),
    ("/dev/subsys_esoc0", "0640", "1000", "1000", "236", "9"),
    ("/dev/subsys_modem", "0640", "1000", "1000", "236", "0"),
)

FORBIDDEN_TERMS = (
    "android.hardware.wifi",
    "wificond",
    "wpa_supplicant",
    "hostapd",
    "svc wifi",
    "cmd wifi",
    " iw ",
    "dhcp",
    " ip route",
    " ip addr",
    " ping ",
    "dd ",
    "boot_linux",
    "native_init_flash",
    "fastboot",
    "qcwlanstate on",
    "qcwlanstate off",
    "exec ",
    "cat /dev/esoc",
    "cat /dev/subsys",
    ">/dev/esoc",
    ">/dev/subsys",
    "esoc_link>",
    "esoc_name>",
    "subsys9/state>",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--marker", default=DEFAULT_MARKER)
    parser.add_argument("--v854-manifest", type=Path, default=DEFAULT_V854_MANIFEST)
    parser.add_argument("--allow-node-materialization", action="store_true")
    parser.add_argument("--allow-node-cleanup", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--no-hide-on-busy", dest="hide_on_busy", action="store_false")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def redact(text: str) -> str:
    return SECRET_RE.sub(r"\1 [redacted]", ANSI_RE.sub("", text))


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    if not args.allow_node_materialization:
        missing.append("--allow-node-materialization")
    if not args.allow_node_cleanup:
        missing.append("--allow-node-cleanup")
    if not args.assume_yes:
        missing.append("--assume-yes")
    return missing


def validate_device_command(command: list[str]) -> None:
    joined = " " + " ".join(command).lower() + " "
    for term in FORBIDDEN_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden V855 command term {term!r}: {' '.join(command)}")


def shell_cmd(args: argparse.Namespace, script: str) -> list[str]:
    return ["run", args.busybox, "sh", "-c", script]


def run_step(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    command: list[str],
    timeout: float | None = None,
) -> dict[str, Any]:
    validate_device_command(command)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    if args.hide_on_busy and (capture.status == "busy" or "[busy]" in payload):
        run_capture(args, f"{name}-hide-on-busy", ["hide"], timeout=min(args.timeout, 8.0))
        capture = run_capture(args, name, command, timeout=timeout or args.timeout)
        payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    payload = redact(payload)
    item = {
        "name": name,
        "command": " ".join(command[:3]) + (" ..." if len(command) > 3 else ""),
        "ok": capture.ok,
        "rc": capture.rc,
        "status": capture.status,
        "duration_sec": round(capture.duration_sec, 3),
        "error": redact(capture.error),
        "payload": payload[:4096] + ("\n[truncated]\n" if len(payload) > 4096 else ""),
        "file": f"native/{safe_name(name)}.txt",
    }
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def plan_steps() -> list[dict[str, Any]]:
    return [
        {"name": "v854-manifest-check", "command": "host-read manifest", "mutates": False},
        {"name": "pre-bootstatus", "command": "cmdv1 bootstatus", "mutates": False},
        {"name": "pre-selftest", "command": "cmdv1 selftest", "mutates": False},
        {"name": "node-preflight", "command": "read /proc/devices, sysfs dev values, target node ls", "mutates": False},
        {"name": "materialize-android-node-parity", "command": "mknod/chown/chmod exact Android-equivalent nodes", "mutates": True},
        {"name": "verify-no-holders", "command": "scan /proc/*/fd symlinks only", "mutates": False},
        {"name": "cleanup-created-nodes", "command": "rm only nodes created by this run", "mutates": True},
        {"name": "post-bootstatus", "command": "cmdv1 bootstatus", "mutates": False},
        {"name": "post-selftest", "command": "cmdv1 selftest", "mutates": False},
    ]


def preflight_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    nodes = " ".join(path for path, *_ in TARGET_NODES)
    return (
        f"BB={bb}; "
        "printf '== proc_devices ==\\n'; "
        "$BB grep -E '^ *(236 +subsys|484 +esoc|478 +qcwlanstate|505 +diag)' /proc/devices 2>&1 || true; "
        "printf '== sysfs_dev ==\\n'; "
        "for p in /sys/class/subsys/subsys_esoc0 /sys/class/subsys/subsys_modem /sys/bus/esoc/devices/esoc0; do "
        "printf 'PATH %s\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; "
        "for f in dev name state uevent esoc_link esoc_name esoc_link_info; do [ -e \"$p/$f\" ] && { printf 'FILE %s/%s\\n' \"$p\" \"$f\"; $BB cat \"$p/$f\" 2>&1 | $BB head -c 300; printf '\\n'; }; done; "
        "done; "
        "printf '== target_nodes_before ==\\n'; "
        f"for p in {nodes}; do printf 'NODE %s\\n' \"$p\"; $BB ls -l \"$p\" 2>&1 || true; done; "
        "true"
    )


def materialize_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    marker = args.marker
    lines = [
        f"BB={bb}",
        f"MARKER={marker}",
        ": > \"$MARKER\"",
        "create_node() {",
        "  path=$1 mode=$2 uid=$3 gid=$4 maj=$5 min=$6",
        "  if [ -e \"$path\" ]; then echo \"EXISTING $path\"; return 0; fi",
        "  \"$BB\" mknod -m \"$mode\" \"$path\" c \"$maj\" \"$min\" || return 1",
        "  \"$BB\" chown \"$uid:$gid\" \"$path\" || return 1",
        "  \"$BB\" chmod \"$mode\" \"$path\" || return 1",
        "  echo \"$path\" >> \"$MARKER\"",
        "  echo \"CREATED $path c $maj $min mode=$mode owner=$uid:$gid\"",
        "}",
    ]
    for path, mode, uid, gid, maj, min_ in TARGET_NODES:
        lines.append(f"create_node {path} {mode} {uid} {gid} {maj} {min_}")
    lines.extend([
        "printf '== created_marker ==\\n'",
        "\"$BB\" cat \"$MARKER\" 2>&1 || true",
        "printf '== target_nodes_after ==\\n'",
        "for p in /dev/esoc-0 /dev/subsys_esoc0 /dev/subsys_modem; do \"$BB\" ls -l \"$p\" 2>&1 || true; done",
        "true",
    ])
    return "\n".join(lines)


def holder_scan_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== fd_holders ==\\n'; found=0; "
        "for d in /proc/[0-9]*; do [ -d \"$d/fd\" ] || continue; "
        "hits=$($BB ls -l \"$d/fd\" 2>/dev/null | $BB grep -E '/dev/(esoc-0|subsys_esoc0|subsys_modem)' || true); "
        "if [ -n \"$hits\" ]; then found=1; pid=${d##*/}; comm=$($BB cat \"$d/comm\" 2>/dev/null); "
        "printf 'FDHOLDER pid=%s comm=%s\\n' \"$pid\" \"$comm\"; printf '%s\\n' \"$hits\"; fi; "
        "done; printf 'holder_found=%s\\n' \"$found\"; true"
    )


def cleanup_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    marker = args.marker
    return (
        f"BB={bb}; MARKER={marker}; "
        "printf '== cleanup_marker ==\\n'; $BB cat \"$MARKER\" 2>&1 || true; "
        "if [ -f \"$MARKER\" ]; then while read p; do case \"$p\" in /dev/esoc-0|/dev/subsys_esoc0|/dev/subsys_modem) echo \"REMOVE $p\"; $BB rm -f \"$p\" ;; *) echo \"SKIP $p\" ;; esac; done < \"$MARKER\"; fi; "
        "$BB rm -f \"$MARKER\"; "
        "printf '== target_nodes_cleanup_verify ==\\n'; "
        "for p in /dev/esoc-0 /dev/subsys_esoc0 /dev/subsys_modem; do printf 'NODE %s\\n' \"$p\"; $BB ls -l \"$p\" 2>&1 || true; done; true"
    )


def parse_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def analyze(steps: list[dict[str, Any]]) -> dict[str, Any]:
    preflight = parse_payload(steps, "node-preflight")
    materialize = parse_payload(steps, "materialize-android-node-parity")
    holders = parse_payload(steps, "verify-no-holders")
    cleanup = parse_payload(steps, "cleanup-created-nodes")
    post_boot = parse_payload(steps, "post-bootstatus")
    post_self = parse_payload(steps, "post-selftest")
    created = re.findall(r"^CREATED\s+(\S+)", materialize, flags=re.MULTILINE)
    existing = re.findall(r"^EXISTING\s+(\S+)", materialize, flags=re.MULTILINE)
    removed = re.findall(r"^REMOVE\s+(\S+)", cleanup, flags=re.MULTILINE)
    return {
        "preflight": {
            "subsys_major_visible": "236 subsys" in preflight,
            "esoc_major_visible": "484 esoc" in preflight,
            "subsys_esoc0_sysfs_visible": "FILE /sys/class/subsys/subsys_esoc0/dev" in preflight,
            "subsys_modem_sysfs_visible": "FILE /sys/class/subsys/subsys_modem/dev" in preflight,
            "esoc0_sysfs_visible": "FILE /sys/bus/esoc/devices/esoc0/uevent" in preflight,
        },
        "materialize": {
            "created": created,
            "existing": existing,
            "created_count": len(created),
            "expected_created_count": len(TARGET_NODES),
            "all_target_nodes_accounted": len(created) + len(existing) == len(TARGET_NODES),
        },
        "holders": {
            "holder_found": "holder_found=1" in holders,
            "holder_lines": [line for line in holders.splitlines() if "FDHOLDER" in line or "-> /dev/" in line],
        },
        "cleanup": {
            "removed": removed,
            "removed_count": len(removed),
            "removed_all_created": sorted(removed) == sorted(created),
            "target_absent_after_cleanup": cleanup.count("No such file or directory") >= len(created),
        },
        "postflight": {
            "boot_ok": "BOOT OK" in post_boot,
            "selftest_fail0": "fail=0" in post_self,
        },
    }


def execute(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    run_step(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    run_step(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    run_step(args, store, steps, "node-preflight", shell_cmd(args, preflight_script(args)), timeout=20.0)
    run_step(args, store, steps, "materialize-android-node-parity", shell_cmd(args, materialize_script(args)), timeout=20.0)
    run_step(args, store, steps, "verify-no-holders", shell_cmd(args, holder_scan_script(args)), timeout=20.0)
    run_step(args, store, steps, "cleanup-created-nodes", shell_cmd(args, cleanup_script(args)), timeout=20.0)
    run_step(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    run_step(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)
    return steps, analyze(steps)


def decide(args: argparse.Namespace, v854: dict[str, Any], steps: list[dict[str, Any]], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v855-esoc-node-parity-plan-ready", True, "plan-only; no device command executed", "run V855 with explicit node materialization and cleanup flags"
    missing = required_flags(args)
    if missing:
        return "v855-esoc-node-parity-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V855 materialization/cleanup approval flags"
    if v854.get("decision") != "v854-esoc-actor-parity-selects-node-contract-preflight":
        return "v855-esoc-node-parity-v854-missing", False, "V854 selector evidence is missing or stale", "run V854 classifier before V855"
    failed_steps = [step["name"] for step in steps if not step.get("ok")]
    if failed_steps:
        return "v855-esoc-node-parity-step-failed", False, f"failed steps: {', '.join(failed_steps)}", "inspect failed V855 step before retry"
    preflight = analysis["preflight"]
    materialize = analysis["materialize"]
    holders = analysis["holders"]
    cleanup = analysis["cleanup"]
    postflight = analysis["postflight"]
    if not (preflight["subsys_major_visible"] and preflight["esoc_major_visible"]):
        return "v855-esoc-node-parity-major-missing", False, f"preflight={preflight}", "do not materialize actor nodes until char majors are visible"
    if not materialize["all_target_nodes_accounted"]:
        return "v855-esoc-node-parity-materialize-incomplete", False, f"materialize={materialize}", "repair node materialization before actor replay"
    if holders["holder_found"]:
        return "v855-esoc-node-parity-unexpected-holder", False, f"holders={holders['holder_lines']}", "stop before actor replay; classify unexpected holder"
    if not cleanup["removed_all_created"]:
        return "v855-esoc-node-parity-cleanup-incomplete", False, f"cleanup={cleanup}", "manual cleanup required before continuing"
    if not (postflight["boot_ok"] and postflight["selftest_fail0"]):
        return "v855-esoc-node-parity-postflight-unhealthy", False, f"postflight={postflight}", "restore native health before next gate"
    return (
        "v855-esoc-node-parity-clean",
        True,
        "Android-equivalent eSoC/subsys nodes were materialized, remained unheld, cleaned up, and native health stayed good",
        "plan V856 pm-service start-only with Android node parity; still no mdm_helper/ks/HAL/connect",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    plan_rows = [[step["name"], step["command"], step["mutates"]] for step in manifest.get("plan_steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V855 eSoC Node Parity Preflight",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- raw_esoc_open_executed: `{manifest['raw_esoc_open_executed']}`",
        f"- subsys_char_open_executed: `{manifest['subsys_char_open_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Plan Steps",
        "",
        markdown_table(["name", "command", "mutates"], plan_rows) if plan_rows else "- none",
        "",
        "## Analysis",
        "",
        markdown_table(["section", "value"], analysis_rows) if analysis_rows else "- none",
        "",
        "## Steps",
        "",
        markdown_table(["name", "status", "rc", "duration_sec", "file"], step_rows) if step_rows else "- none",
        "",
        "## Guardrails",
        "",
        "- No eSoC/subsys node open or ioctl.",
        "- No actor service start: no `pm-service`, `mdm_helper`, `ks`, CNSS retry, or Wi-Fi HAL.",
        "- No Wi-Fi scan/connect/link-up, credentials, DHCP/routes, or external ping.",
        "- No GPIO/sysfs/debugfs write, subsystem state write, module load/unload, boot image write, or partition write.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v854 = load_json(args.v854_manifest)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    if args.command == "run" and not required_flags(args) and v854.get("decision") == "v854-esoc-actor-parity-selects-node-contract-preflight":
        steps, analysis = execute(args, store)
    decision, pass_ok, reason, next_step = decide(args, v854, steps, analysis)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "v854_manifest": {
            "path": str(repo_path(args.v854_manifest)),
            "decision": v854.get("decision"),
            "pass": bool(v854.get("pass")),
        },
        "plan_steps": plan_steps(),
        "steps": steps,
        "analysis": analysis,
        "required_flags_missing": required_flags(args),
        "device_commands_executed": args.command == "run" and bool(steps),
        "device_mutations": args.command == "run" and bool(steps),
        "node_materialization_executed": args.command == "run" and bool(steps),
        "node_cleanup_executed": args.command == "run" and bool(steps),
        "raw_esoc_open_executed": False,
        "subsys_char_open_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "sysfs_write_executed": False,
        "debugfs_write_executed": False,
        "gpio_write_executed": False,
        "boot_or_partition_write_executed": False,
    }


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
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"raw_esoc_open_executed: {manifest['raw_esoc_open_executed']}")
    print(f"subsys_char_open_executed: {manifest['subsys_char_open_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
