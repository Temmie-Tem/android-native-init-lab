#!/usr/bin/env python3
"""V884 bounded live REQ-registered subsystem-hold observer preflight.

Runs deployed helper v139 in the fail-closed
wifi-companion-esoc-req-registered-subsys-hold-preflight mode. The allowed
live action is limited to REG_REQ_ENG on /dev/esoc-0, then a bounded
/dev/subsys_esoc0 open attempt while a passive ESOC_WAIT_FOR_REQ observer records
whether SDX50M emits a request. It never starts Android actors, Wi-Fi HAL,
scan/connect, DHCP/routes, credentials, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import native_wifi_esoc_node_parity_preflight_v855 as v855
import native_wifi_pm_service_property_contract_start_only_v857 as v857
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v884-esoc-req-registered-subsys-hold")
LATEST_POINTER = Path("tmp/wifi/latest-v884-esoc-req-registered-subsys-hold.txt")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v882-execns-helper-v139-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "077ced65ae5b0b546ecdf3b1bb0c808d3ec34bfa2462516e6ceba170b18f23c5"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v139"
DEFAULT_MARKER = "/tmp/a90-v884-esoc-req-registered-subsys-hold.created"
MODE = "wifi-companion-esoc-req-registered-subsys-hold-preflight"

FORBIDDEN_TRUE_KEYS = (
    "esoc_req_registered_subsys_hold_preflight.reg_cmd_eng_attempted",
    "esoc_req_registered_subsys_hold_preflight.cmd_exe_attempted",
    "esoc_req_registered_subsys_hold_preflight.pwr_on_attempted",
    "esoc_req_registered_subsys_hold_preflight.notify_attempted",
    "esoc_req_registered_subsys_hold_preflight.daemon_start_executed",
    "esoc_req_registered_subsys_hold_preflight.mdm_helper_start_executed",
    "esoc_req_registered_subsys_hold_preflight.ks_start_executed",
    "esoc_req_registered_subsys_hold_preflight.pm_proxy_helper_start_executed",
    "esoc_req_registered_subsys_hold_preflight.cnss_start_executed",
    "esoc_req_registered_subsys_hold_preflight.service_manager_start_executed",
    "esoc_req_registered_subsys_hold_preflight.wifi_hal_start_executed",
    "esoc_req_registered_subsys_hold_preflight.scan_connect_linkup",
    "esoc_req_registered_subsys_hold_preflight.credentials",
    "esoc_req_registered_subsys_hold_preflight.dhcp_routing",
    "esoc_req_registered_subsys_hold_preflight.external_ping",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v857.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v857.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=v857.DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=v857.DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=v857.DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--helper-timeout-sec", type=int, default=12)
    parser.add_argument("--toybox-timeout-sec", type=int, default=24)
    parser.add_argument("--marker", default=DEFAULT_MARKER)
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-node-materialization", action="store_true")
    parser.add_argument("--allow-node-cleanup", action="store_true")
    parser.add_argument("--allow-esoc-req-registered-subsys-hold-preflight", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--no-hide-on-busy", dest="hide_on_busy", action="store_false")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.strip().split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.-]+", key):
            keys[key] = value.strip()
    return keys


def local_helper_info(args: argparse.Namespace) -> dict[str, Any]:
    path = repo_path(args.local_helper)
    info: dict[str, Any] = {"path": str(path), "exists": path.exists(), "sha256": "", "marker": False, "mode": False}
    if not path.exists():
        return info
    info["sha256"] = sha256_file(path)
    strings = subprocess.run(
        ["strings", str(path)],
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=30,
    ).stdout
    info["marker"] = args.helper_marker in strings
    info["mode"] = MODE in strings
    return info


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    for flag, enabled in (
        ("--allow-mountsystem-ro", args.allow_mountsystem_ro),
        ("--allow-node-materialization", args.allow_node_materialization),
        ("--allow-node-cleanup", args.allow_node_cleanup),
        ("--allow-esoc-req-registered-subsys-hold-preflight", args.allow_esoc_req_registered_subsys_hold_preflight),
        ("--assume-yes", args.assume_yes),
    ):
        if not enabled:
            missing.append(flag)
    return missing


def helper_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        args.toybox,
        "timeout",
        str(args.toybox_timeout_sec),
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        MODE,
        "--null-device-mode",
        "dev-null",
        "--allow-esoc-req-registered-subsys-hold-preflight",
        "--timeout-sec",
        str(min(max(args.helper_timeout_sec, 4), 30)),
    ]


def remote_helper_state(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    sha = v857.run_device(args, store, steps, "remote-helper-sha", ["run", args.toybox, "sha256sum", args.helper], timeout=12.0)
    usage = v857.run_device(args, store, steps, "remote-helper-usage", ["run", args.helper], timeout=12.0)
    sha_payload = str(sha.get("payload") or "")
    usage_payload = str(usage.get("payload") or "")
    return {
        "sha_ok": args.helper_sha256 in sha_payload,
        "marker_ok": args.helper_marker in usage_payload,
        "mode_ok": MODE in usage_payload,
        "sha_file": sha.get("file"),
        "usage_file": usage.get("file"),
    }


def post_surface(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    ps = v857.run_device(args, store, steps, "post-ps", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], timeout=20.0)
    net = v857.run_device(args, store, steps, "post-proc-net-dev", ["cat", "/proc/net/dev"], timeout=12.0)
    actor_re = re.compile(r"\b(pm_proxy_helper|pm-service|pm-proxy|mdm_helper|servicemanager|hwservicemanager|vndservicemanager|cnss_diag|cnss-daemon|wificond|supplicant|hostapd|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b")
    wifi_re = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)
    ps_text = str(ps.get("payload") or "")
    net_text = str(net.get("payload") or "")
    ps_file = store.run_dir / str(ps.get("file") or "")
    net_file = store.run_dir / str(net.get("file") or "")
    if ps_file.exists():
        ps_text = ps_file.read_text(encoding="utf-8", errors="replace")
    if net_file.exists():
        net_text = net_file.read_text(encoding="utf-8", errors="replace")
    helper_lines = [line.strip() for line in ps_text.splitlines() if "a90_android_execns_probe" in line]
    return {
        "actor_hits": [line.strip() for line in ps_text.splitlines() if actor_re.search(line)][:16],
        "wifi_link_hits": [line.strip() for line in net_text.splitlines() if wifi_re.search(line)][:16],
        "helper_process_hits": helper_lines[:16],
    }


def helper_surface(text: str) -> dict[str, Any]:
    keys = parse_keys(text)
    prefix = "esoc_req_registered_subsys_hold_preflight"
    observer = f"{prefix}.wait_for_req_observer"
    observer_rc = keys.get(f"{observer}.ioctl.rc", "")
    observer_errno = keys.get(f"{observer}.ioctl.errno", "")
    observer_value = keys.get(f"{observer}.ioctl.value", "")
    observer_semantic = "unknown"
    try:
        if int(observer_errno or "-1") == 0 and int(observer_rc or "-1") >= 0 and observer_value:
            observer_semantic = "request-observed"
        elif int(observer_errno or "0") != 0:
            observer_semantic = "ioctl-error"
    except ValueError:
        observer_semantic = "parse-error"
    return {
        "keys": {
            "mode": keys.get(f"{prefix}.mode", ""),
            "allowed": keys.get(f"{prefix}.allowed", ""),
            "open_req_attempted": keys.get(f"{prefix}.open_req_attempted", ""),
            "open_req_fd": keys.get(f"{prefix}.open_req.fd", ""),
            "open_req_errno": keys.get(f"{prefix}.open_req.errno", ""),
            "reg_req_eng_attempted": keys.get(f"{prefix}.reg_req_eng_attempted", ""),
            "reg_req_eng_rc": keys.get(f"{prefix}.ioctl.REG_REQ_ENG.rc", ""),
            "reg_req_eng_errno": keys.get(f"{prefix}.ioctl.REG_REQ_ENG.errno", ""),
            "req_fd_held": keys.get(f"{prefix}.req_fd_held", ""),
            "subsys_esoc0_open_attempted": keys.get(f"{prefix}.subsys_esoc0_open_attempted", ""),
            "subsys_esoc0_opened": keys.get(f"{prefix}.subsys_esoc0_opened", ""),
            "subsys_esoc0_open_errno": keys.get(f"{prefix}.subsys_esoc0_open_errno", ""),
            "hold_sec": keys.get(f"{prefix}.hold_sec", ""),
            "close_req_attempted": keys.get(f"{prefix}.close_req_attempted", ""),
            "exited": keys.get(f"{prefix}.exited", ""),
            "exit_code": keys.get(f"{prefix}.exit_code", ""),
            "signal": keys.get(f"{prefix}.signal", ""),
            "timed_out": keys.get(f"{prefix}.timed_out", ""),
            "term_sent": keys.get(f"{prefix}.term_sent", ""),
            "kill_sent": keys.get(f"{prefix}.kill_sent", ""),
            "reaped": keys.get(f"{prefix}.reaped", ""),
            "all_postflight_safe": keys.get(f"{prefix}.all_postflight_safe", ""),
            "result": keys.get(f"{prefix}.result", ""),
            "reason": keys.get(f"{prefix}.reason", ""),
        },
        "observer": {
            "child_started": keys.get(f"{observer}.child_started", ""),
            "begin": keys.get(f"{observer}.begin", ""),
            "mode": keys.get(f"{observer}.mode", ""),
            "ioctl_request": keys.get(f"{observer}.ioctl.request", ""),
            "ioctl_rc": keys.get(f"{observer}.ioctl.rc", ""),
            "ioctl_errno": keys.get(f"{observer}.ioctl.errno", ""),
            "ioctl_value": keys.get(f"{observer}.ioctl.value", ""),
            "elapsed_ms": keys.get(f"{observer}.elapsed_ms", ""),
            "result": keys.get(f"{observer}.result", ""),
            "semantic_result": observer_semantic,
            "term_sent": keys.get(f"{observer}.term_sent", ""),
            "kill_sent": keys.get(f"{observer}.kill_sent", ""),
            "reaped": keys.get(f"{observer}.reaped", ""),
            "exit_code": keys.get(f"{observer}.exit_code", ""),
            "signal": keys.get(f"{observer}.signal", ""),
        },
        "snapshots": {
            key: value
            for key, value in keys.items()
            if key.startswith(f"{prefix}.snapshot.")
        },
        "forbidden_true": {key: keys.get(key) for key in FORBIDDEN_TRUE_KEYS if keys.get(key) not in (None, "0")},
    }


def execute(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    v857.run_device(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    if args.allow_mountsystem_ro:
        v857.run_device(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    analysis["remote_helper"] = remote_helper_state(args, store, steps)
    v857.run_device(args, store, steps, "node-preflight", v855.shell_cmd(args, v855.preflight_script(args)), timeout=20.0)
    try:
        v857.run_device(args, store, steps, "materialize-android-node-parity", v855.shell_cmd(args, v855.materialize_script(args)), timeout=20.0)
        helper = v857.run_device(args, store, steps, "esoc-req-registered-subsys-hold", helper_command(args), timeout=args.toybox_timeout_sec + 25.0)
        helper_payload = str(helper.get("payload") or "")
        helper_file = store.run_dir / str(helper.get("file") or "")
        if helper_file.exists():
            helper_payload = helper_file.read_text(encoding="utf-8", errors="replace")
        analysis["helper"] = helper_surface(helper_payload)
    finally:
        v857.run_device(args, store, steps, "cleanup-created-nodes", v855.shell_cmd(args, v855.cleanup_script(args)), timeout=20.0)
    v857.run_device(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)
    analysis["post_surface"] = post_surface(args, store, steps)
    analysis["node"] = v855.analyze(steps)
    return steps, analysis


def decide(args: argparse.Namespace,
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v884-plan-helper-v139-missing", False, f"local={local}", "build and deploy helper v139 before V884"
        return "v884-esoc-req-registered-subsys-hold-plan-ready", True, "plan-only; no device command executed", "run bounded V884 live preflight"
    missing = required_flags(args)
    if missing:
        return "v884-esoc-req-registered-subsys-hold-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V884 flags"
    failed_steps = [step["name"] for step in steps if not step.get("ok") and step.get("name") != "remote-helper-usage"]
    if failed_steps:
        return "v884-step-failed", False, f"failed_steps={failed_steps}", "inspect V884 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v884-helper-v139-remote-mismatch", False, f"remote={remote}", "redeploy helper v139 before V884"
    node = analysis.get("node") or {}
    if not ((node.get("materialize") or {}).get("all_target_nodes_accounted")):
        return "v884-node-materialization-failed", False, f"node={node}", "repair node materialization before retry"
    if not ((node.get("cleanup") or {}).get("removed_all_created")):
        return "v884-node-cleanup-review", False, f"node={node}", "cleanup V884 nodes manually before continuing"
    if not ((node.get("postflight") or {}).get("selftest_fail0")):
        return "v884-postflight-health-review", False, f"node={node}", "restore native health before continuing"
    post = analysis.get("post_surface") or {}
    if post.get("actor_hits") or post.get("wifi_link_hits"):
        return "v884-post-surface-not-clean", False, f"post={post}", "cleanup actor or Wi-Fi surface before continuing"
    helper = analysis.get("helper") or {}
    if helper.get("forbidden_true"):
        return "v884-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    keys = helper.get("keys") or {}
    if keys.get("allowed") != "1" or keys.get("open_req_attempted") != "1" or keys.get("reg_req_eng_attempted") != "1":
        return "v884-helper-mode-not-executed", False, f"keys={keys}", "fix V884 helper command before retry"
    if keys.get("reg_req_eng_rc") != "0":
        return "v884-reg-req-eng-review", False, f"helper={helper}", "classify REG_REQ_ENG before retrying subsystem hold"
    observer = helper.get("observer") or {}
    if observer.get("child_started") != "1":
        return "v884-wait-for-req-observer-not-started", False, f"helper={helper}", "fix helper observer before retry"
    if keys.get("all_postflight_safe") != "1":
        return "v884-reboot-required", False, f"helper={helper}", "perform recovery reboot before next live gate"
    if keys.get("result") == "req-registered-subsys-hold-window-pass":
        return "v884-req-registered-subsys-hold-window-pass", True, f"helper={helper}", "classify mdm3/SSCTL/WLFW deltas from V884 evidence"
    if keys.get("result") == "subsys-esoc0-open-failed":
        return "v884-subsys-esoc0-open-failed", False, f"helper={helper}", "classify subsystem open errno before retry"
    return "v884-req-registered-subsys-hold-review", False, f"helper={helper}", "inspect V884 helper result before next gate"


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V884 REQ-registered Subsystem-hold Observer Preflight",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- req_registered_subsys_hold_executed: `{manifest['req_registered_subsys_hold_executed']}`",
        f"- reg_req_eng_ioctl_executed: `{manifest['reg_req_eng_ioctl_executed']}`",
        f"- subsys_esoc0_open_attempted: `{manifest['subsys_esoc0_open_attempted']}`",
        f"- wait_for_req_observer_executed: `{manifest['wait_for_req_observer_executed']}`",
        f"- power_or_notify_executed: `{manifest['power_or_notify_executed']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Analysis",
        "",
        markdown_table(["section", "value"], analysis_rows),
        "",
        "## Steps",
        "",
        markdown_table(["name", "status", "rc", "duration_sec", "file"], step_rows),
        "",
        "## Guardrails",
        "",
        "- `REG_REQ_ENG` is the only allowed eSoC registration ioctl.",
        "- No `REG_CMD_ENG`, direct userspace `CMD_EXE`, explicit userspace `PWR_ON`, or `ESOC_NOTIFY`.",
        "- No actor start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "- No module load/unload, boot image write, partition write, or firmware mutation.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    local = local_helper_info(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    will_execute = args.command == "run" and not required_flags(args)
    if will_execute:
        steps, analysis = execute(args, store)
    decision, pass_ok, reason, next_step = decide(args, local, steps, analysis)
    helper = analysis.get("helper") or {}
    keys = helper.get("keys") or {}
    observer = helper.get("observer") or {}
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "local_helper": local,
        "helper": args.helper,
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "mode": MODE,
        "helper_timeout_sec": args.helper_timeout_sec,
        "toybox_timeout_sec": args.toybox_timeout_sec,
        "steps": steps,
        "analysis": analysis,
        "req_registered_subsys_hold_executed": will_execute,
        "reg_req_eng_ioctl_executed": keys.get("reg_req_eng_attempted") == "1",
        "subsys_esoc0_open_attempted": keys.get("subsys_esoc0_open_attempted") == "1",
        "wait_for_req_observer_executed": observer.get("child_started") == "1",
        "power_or_notify_executed": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    return manifest


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
    print(f"req_registered_subsys_hold_executed: {manifest['req_registered_subsys_hold_executed']}")
    print(f"reg_req_eng_ioctl_executed: {manifest['reg_req_eng_ioctl_executed']}")
    print(f"subsys_esoc0_open_attempted: {manifest['subsys_esoc0_open_attempted']}")
    print(f"wait_for_req_observer_executed: {manifest['wait_for_req_observer_executed']}")
    print(f"power_or_notify_executed: {manifest['power_or_notify_executed']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
