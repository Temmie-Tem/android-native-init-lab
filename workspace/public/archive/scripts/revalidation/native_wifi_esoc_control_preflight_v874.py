#!/usr/bin/env python3
"""V874 bounded live eSoC control preflight.

Uses deployed helper v136 to prove `/dev/esoc-0` visibility and read-only eSoC
status ioctl behavior. This must not issue REG_REQ_ENG, REG_CMD_ENG, CMD_EXE,
WAIT_FOR_REQ, NOTIFY, PWR_ON, mdm_helper, ks, pm_proxy_helper, CNSS, Wi-Fi HAL,
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v874-esoc-control-preflight")
LATEST_POINTER = Path("tmp/wifi/latest-v874-esoc-control-preflight.txt")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v872-execns-helper-v136-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "76dce733b8444073fc615a44df240aa7f8256dfb7f6c123c3f5e388907356980"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v136"
DEFAULT_MARKER = "/tmp/a90-v874-esoc-control-preflight.created"
MODE = "wifi-companion-esoc-control-preflight"
FORBIDDEN_TRUE_KEYS = (
    "esoc_control_preflight.reg_req_eng_attempted",
    "esoc_control_preflight.reg_cmd_eng_attempted",
    "esoc_control_preflight.cmd_exe_attempted",
    "esoc_control_preflight.wait_for_req_attempted",
    "esoc_control_preflight.notify_attempted",
    "esoc_control_preflight.pwr_on_attempted",
    "esoc_control_preflight.mdm_helper_start_executed",
    "esoc_control_preflight.ks_start_executed",
    "esoc_control_preflight.wifi_hal_start_executed",
    "esoc_control_preflight.scan_connect_linkup",
    "esoc_control_preflight.credentials",
    "esoc_control_preflight.dhcp_routing",
    "esoc_control_preflight.external_ping",
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
    parser.add_argument("--runtime-sec", type=int, default=8)
    parser.add_argument("--marker", default=DEFAULT_MARKER)
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-node-materialization", action="store_true")
    parser.add_argument("--allow-node-cleanup", action="store_true")
    parser.add_argument("--allow-esoc-control-preflight", action="store_true")
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


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.strip().split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.-]+", key):
            keys[key] = value.strip()
    return keys


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    for flag, enabled in (
        ("--allow-mountsystem-ro", args.allow_mountsystem_ro),
        ("--allow-node-materialization", args.allow_node_materialization),
        ("--allow-node-cleanup", args.allow_node_cleanup),
        ("--allow-esoc-control-preflight", args.allow_esoc_control_preflight),
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
        str(args.runtime_sec),
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
        "--allow-esoc-control-preflight",
        "--timeout-sec",
        str(min(max(args.runtime_sec, 1), 30)),
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
    return {
        "actor_hits": [line.strip() for line in ps_text.splitlines() if actor_re.search(line)][:16],
        "wifi_link_hits": [line.strip() for line in net_text.splitlines() if wifi_re.search(line)][:16],
    }


def helper_surface(text: str) -> dict[str, Any]:
    keys = parse_keys(text)
    ioctl_names = ("GET_STATUS", "GET_ERR_FATAL", "GET_LINK_ID")
    return {
        "keys": {
            "mode": keys.get("mode", ""),
            "allowed": keys.get("esoc_control_preflight.allowed", ""),
            "open_attempted": keys.get("esoc_control_preflight.open_attempted", ""),
            "open_fd": keys.get("esoc_control_preflight.open.fd", ""),
            "open_errno": keys.get("esoc_control_preflight.open.errno", ""),
            "result": keys.get("esoc_control_preflight.result", ""),
            "pwr_on_attempted": keys.get("esoc_control_preflight.pwr_on_attempted", ""),
        },
        "forbidden_true": {key: keys.get(key) for key in FORBIDDEN_TRUE_KEYS if keys.get(key) not in (None, "0")},
        "ioctls": {
            name: {
                "request": keys.get(f"esoc_control_preflight.ioctl.{name}.request", ""),
                "rc": keys.get(f"esoc_control_preflight.ioctl.{name}.rc", ""),
                "errno": keys.get(f"esoc_control_preflight.ioctl.{name}.errno", ""),
                "value": keys.get(f"esoc_control_preflight.ioctl.{name}.value", ""),
            }
            for name in ioctl_names
        },
        "private_nodes": {
            "esoc_0": keys.get("wifi_companion_start.private_node.esoc_0.exists", ""),
            "subsys_esoc0": keys.get("wifi_companion_start.private_node.subsys_esoc0.exists", ""),
            "subsys_modem": keys.get("wifi_companion_start.private_node.subsys_modem.exists", ""),
        },
    }


def execute(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    v857.run_device(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    v857.run_device(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    analysis["remote_helper"] = remote_helper_state(args, store, steps)
    v857.run_device(args, store, steps, "node-preflight", v855.shell_cmd(args, v855.preflight_script(args)), timeout=20.0)
    try:
        v857.run_device(args, store, steps, "materialize-android-node-parity", v855.shell_cmd(args, v855.materialize_script(args)), timeout=20.0)
        helper = v857.run_device(args, store, steps, "esoc-control-preflight", helper_command(args), timeout=args.runtime_sec + 25.0)
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
            return "v874-plan-helper-v136-missing", False, f"local={local}", "build helper v136 before V874"
        return "v874-esoc-control-preflight-plan-ready", True, "plan-only; no device command executed", "run bounded V874 live preflight"
    missing = required_flags(args)
    if missing:
        return "v874-esoc-control-preflight-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V874 flags"
    failed_steps = [step["name"] for step in steps if not step.get("ok") and step.get("name") != "remote-helper-usage"]
    if failed_steps:
        return "v874-step-failed", False, f"failed_steps={failed_steps}", "inspect V874 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v874-helper-v136-remote-mismatch", False, f"remote={remote}", "redeploy helper v136 before V874"
    node = analysis.get("node") or {}
    if not ((node.get("materialize") or {}).get("all_target_nodes_accounted")):
        return "v874-node-materialization-failed", False, f"node={node}", "repair node materialization before retry"
    if not ((node.get("cleanup") or {}).get("removed_all_created")):
        return "v874-node-cleanup-review", False, f"node={node}", "cleanup V874 nodes manually before continuing"
    if not ((node.get("postflight") or {}).get("selftest_fail0")):
        return "v874-postflight-health-review", False, f"node={node}", "restore native health before continuing"
    post = analysis.get("post_surface") or {}
    if post.get("actor_hits") or post.get("wifi_link_hits"):
        return "v874-post-surface-not-clean", False, f"post={post}", "cleanup actor or Wi-Fi surface before continuing"
    helper = analysis.get("helper") or {}
    if helper.get("forbidden_true"):
        return "v874-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    keys = helper.get("keys") or {}
    if keys.get("allowed") != "1" or keys.get("open_attempted") != "1":
        return "v874-helper-mode-not-executed", False, f"keys={keys}", "fix V874 helper command before retry"
    if keys.get("result") == "read-only-ioctl-probe-complete":
        return "v874-esoc-readonly-ioctl-probe-pass", True, f"helper={helper}", "classify V875 mutating eSoC state-machine preconditions"
    if keys.get("result") == "open-failed":
        return "v874-esoc-open-failed", False, f"helper={helper}", "classify /dev/esoc-0 open failure before mutating eSoC work"
    return "v874-esoc-control-preflight-review", False, f"helper={helper}", "inspect V874 helper result before next gate"


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V874 eSoC Control Preflight",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- esoc_control_preflight_executed: `{manifest['esoc_control_preflight_executed']}`",
        f"- mutating_esoc_ioctl_executed: `{manifest['mutating_esoc_ioctl_executed']}`",
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
        "- No `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, `WAIT_FOR_REQ`, `NOTIFY`, or `PWR_ON`.",
        "- No `mdm_helper`, `ks`, `pm_proxy_helper`, CNSS, service-manager trio, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "- No module load/unload, boot image write, partition write, or firmware mutation.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    local = local_helper_info(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    if args.command == "run":
        steps, analysis = execute(args, store)
    decision, pass_ok, reason, next_step = decide(args, local, steps, analysis)
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
        "runtime_sec": args.runtime_sec,
        "steps": steps,
        "analysis": analysis,
        "esoc_control_preflight_executed": args.command == "run" and args.allow_esoc_control_preflight,
        "mutating_esoc_ioctl_executed": False,
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
    print(f"esoc_control_preflight_executed: {manifest['esoc_control_preflight_executed']}")
    print(f"mutating_esoc_ioctl_executed: {manifest['mutating_esoc_ioctl_executed']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
