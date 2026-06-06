#!/usr/bin/env python3
"""V878 bounded live eSoC CMD/REQ engine registration preflight.

Uses deployed helper v137 to register CMD and REQ engines on `/dev/esoc-0`
inside a bounded helper window. This must not issue CMD_EXE, PWR_ON,
WAIT_FOR_REQ, NOTIFY, `/dev/subsys_esoc0` open, actor starts, Wi-Fi HAL,
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v878-esoc-engine-register-preflight")
LATEST_POINTER = Path("tmp/wifi/latest-v878-esoc-engine-register-preflight.txt")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v876-execns-helper-v137-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "e47eb52b0b2b2fb601fdbc4ecebdf72e2fda9519eac37e776d62c11d2d469aa3"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v137"
DEFAULT_MARKER = "/tmp/a90-v878-esoc-engine-register-preflight.created"
MODE = "wifi-companion-esoc-engine-register-preflight"
FORBIDDEN_TRUE_KEYS = (
    "esoc_engine_register_preflight.cmd_exe_attempted",
    "esoc_engine_register_preflight.pwr_on_attempted",
    "esoc_engine_register_preflight.wait_for_req_attempted",
    "esoc_engine_register_preflight.notify_attempted",
    "esoc_engine_register_preflight.subsys_esoc0_open_attempted",
    "esoc_engine_register_preflight.daemon_start_executed",
    "esoc_engine_register_preflight.mdm_helper_start_executed",
    "esoc_engine_register_preflight.ks_start_executed",
    "esoc_engine_register_preflight.pm_proxy_helper_start_executed",
    "esoc_engine_register_preflight.cnss_start_executed",
    "esoc_engine_register_preflight.service_manager_start_executed",
    "esoc_engine_register_preflight.wifi_hal_start_executed",
    "esoc_engine_register_preflight.scan_connect_linkup",
    "esoc_engine_register_preflight.credentials",
    "esoc_engine_register_preflight.dhcp_routing",
    "esoc_engine_register_preflight.external_ping",
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
    parser.add_argument("--allow-esoc-engine-register-preflight", action="store_true")
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
        ("--allow-esoc-engine-register-preflight", args.allow_esoc_engine_register_preflight),
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
        "--allow-esoc-engine-register-preflight",
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
    ioctl_names = ("REG_CMD_ENG", "REG_REQ_ENG")
    return {
        "keys": {
            "mode": keys.get("esoc_engine_register_preflight.mode", ""),
            "allowed": keys.get("esoc_engine_register_preflight.allowed", ""),
            "open_cmd_attempted": keys.get("esoc_engine_register_preflight.open_cmd_attempted", ""),
            "open_req_attempted": keys.get("esoc_engine_register_preflight.open_req_attempted", ""),
            "open_cmd_fd": keys.get("esoc_engine_register_preflight.open_cmd.fd", ""),
            "open_req_fd": keys.get("esoc_engine_register_preflight.open_req.fd", ""),
            "open_cmd_errno": keys.get("esoc_engine_register_preflight.open_cmd.errno", ""),
            "open_req_errno": keys.get("esoc_engine_register_preflight.open_req.errno", ""),
            "reg_cmd_eng_attempted": keys.get("esoc_engine_register_preflight.reg_cmd_eng_attempted", ""),
            "reg_req_eng_attempted": keys.get("esoc_engine_register_preflight.reg_req_eng_attempted", ""),
            "hold_sec": keys.get("esoc_engine_register_preflight.hold_sec", ""),
            "close_req_attempted": keys.get("esoc_engine_register_preflight.close_req_attempted", ""),
            "close_cmd_attempted": keys.get("esoc_engine_register_preflight.close_cmd_attempted", ""),
            "result": keys.get("esoc_engine_register_preflight.result", ""),
        },
        "forbidden_true": {key: keys.get(key) for key in FORBIDDEN_TRUE_KEYS if keys.get(key) not in (None, "0")},
        "ioctls": {
            name: {
                "request": keys.get(f"esoc_engine_register_preflight.ioctl.{name}.request", ""),
                "rc": keys.get(f"esoc_engine_register_preflight.ioctl.{name}.rc", ""),
                "errno": keys.get(f"esoc_engine_register_preflight.ioctl.{name}.errno", ""),
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
        helper = v857.run_device(args, store, steps, "esoc-engine-register-preflight", helper_command(args), timeout=args.runtime_sec + 25.0)
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
            return "v878-plan-helper-v137-missing", False, f"local={local}", "build and deploy helper v137 before V878"
        return "v878-esoc-engine-register-preflight-plan-ready", True, "plan-only; no device command executed", "run bounded V878 live preflight"
    missing = required_flags(args)
    if missing:
        return "v878-esoc-engine-register-preflight-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V878 flags"
    failed_steps = [step["name"] for step in steps if not step.get("ok") and step.get("name") != "remote-helper-usage"]
    if failed_steps:
        return "v878-step-failed", False, f"failed_steps={failed_steps}", "inspect V878 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v878-helper-v137-remote-mismatch", False, f"remote={remote}", "redeploy helper v137 before V878"
    node = analysis.get("node") or {}
    if not ((node.get("materialize") or {}).get("all_target_nodes_accounted")):
        return "v878-node-materialization-failed", False, f"node={node}", "repair node materialization before retry"
    if not ((node.get("cleanup") or {}).get("removed_all_created")):
        return "v878-node-cleanup-review", False, f"node={node}", "cleanup V878 nodes manually before continuing"
    if not ((node.get("postflight") or {}).get("selftest_fail0")):
        return "v878-postflight-health-review", False, f"node={node}", "restore native health before continuing"
    post = analysis.get("post_surface") or {}
    if post.get("actor_hits") or post.get("wifi_link_hits"):
        return "v878-post-surface-not-clean", False, f"post={post}", "cleanup actor or Wi-Fi surface before continuing"
    helper = analysis.get("helper") or {}
    if helper.get("forbidden_true"):
        return "v878-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    keys = helper.get("keys") or {}
    if keys.get("allowed") != "1" or keys.get("open_cmd_attempted") != "1" or keys.get("open_req_attempted") != "1":
        return "v878-helper-mode-not-executed", False, f"keys={keys}", "fix V878 helper command before retry"
    if keys.get("result") == "open-failed":
        return "v878-esoc-open-failed", False, f"helper={helper}", "classify /dev/esoc-0 open failure before retry"
    if keys.get("result") != "engine-register-preflight-complete":
        return "v878-esoc-engine-register-review", False, f"helper={helper}", "inspect V878 helper result before next gate"
    if keys.get("reg_cmd_eng_attempted") != "1" or keys.get("reg_req_eng_attempted") != "1":
        return "v878-esoc-engine-register-not-attempted", False, f"helper={helper}", "inspect helper command and allow flag"
    ioctls = helper.get("ioctls") or {}
    cmd_ok = (ioctls.get("REG_CMD_ENG") or {}).get("rc") == "0"
    req_ok = (ioctls.get("REG_REQ_ENG") or {}).get("rc") == "0"
    if not (cmd_ok and req_ok):
        return "v878-esoc-engine-register-ioctl-review", False, f"helper={helper}", "classify REG_CMD_ENG/REG_REQ_ENG ioctl result before PWR_ON work"
    if keys.get("close_cmd_attempted") != "1" or keys.get("close_req_attempted") != "1":
        return "v878-esoc-engine-register-close-review", False, f"helper={helper}", "confirm fd cleanup before continuing"
    return "v878-esoc-engine-register-preflight-pass", True, f"helper={helper}", "classify V879 PWR_ON request-loop guardrails"


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V878 eSoC Engine Register Preflight",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- esoc_engine_register_preflight_executed: `{manifest['esoc_engine_register_preflight_executed']}`",
        f"- reg_cmd_req_ioctl_executed: `{manifest['reg_cmd_req_ioctl_executed']}`",
        f"- power_or_request_loop_executed: `{manifest['power_or_request_loop_executed']}`",
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
        "- `REG_CMD_ENG` and `REG_REQ_ENG` are the only mutating eSoC ioctls allowed.",
        "- No `CMD_EXE`, `PWR_ON`, `WAIT_FOR_REQ`, `NOTIFY`, or `/dev/subsys_esoc0` open.",
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
        "esoc_engine_register_preflight_executed": will_execute,
        "reg_cmd_req_ioctl_executed": will_execute,
        "power_or_request_loop_executed": False,
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
    print(f"esoc_engine_register_preflight_executed: {manifest['esoc_engine_register_preflight_executed']}")
    print(f"reg_cmd_req_ioctl_executed: {manifest['reg_cmd_req_ioctl_executed']}")
    print(f"power_or_request_loop_executed: {manifest['power_or_request_loop_executed']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
