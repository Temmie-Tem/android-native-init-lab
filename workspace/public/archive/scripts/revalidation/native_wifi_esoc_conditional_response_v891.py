#!/usr/bin/env python3
"""V891 bounded live eSoC conditional response proof.

Runs deployed helper v141 in
wifi-companion-esoc-conditional-response-preflight mode. The only newly
allowed live action is the guarded response to an observed ESOC_REQ_IMG:
ESOC_IMG_XFER_DONE first, then ESOC_GET_STATUS polling, then ESOC_BOOT_DONE
only if status becomes ready. It does not start Android actors, Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import native_wifi_esoc_node_parity_preflight_v855 as v855
import native_wifi_pm_service_property_contract_start_only_v857 as v857
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v891-esoc-conditional-response-live")
LATEST_POINTER = Path("tmp/wifi/latest-v891-esoc-conditional-response-live.txt")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v892-execns-helper-v142-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "b11c346581292422328a64ec78d58dc0f8d7b7cbf958fbb3fcb54df81029de26"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v142"
DEFAULT_MARKER = "/tmp/a90-v891-esoc-conditional-response.created"
MODE = "wifi-companion-esoc-conditional-response-preflight"

OUTER_PREFIX = "esoc_req_registered_subsys_hold_preflight"
COND_PREFIX = "esoc_conditional_response_preflight"

FORBIDDEN_TRUE_KEYS = (
    f"{OUTER_PREFIX}.reg_cmd_eng_attempted",
    f"{OUTER_PREFIX}.cmd_exe_attempted",
    f"{OUTER_PREFIX}.pwr_on_attempted",
    f"{OUTER_PREFIX}.daemon_start_executed",
    f"{OUTER_PREFIX}.mdm_helper_start_executed",
    f"{OUTER_PREFIX}.ks_start_executed",
    f"{OUTER_PREFIX}.pm_proxy_helper_start_executed",
    f"{OUTER_PREFIX}.cnss_start_executed",
    f"{OUTER_PREFIX}.service_manager_start_executed",
    f"{OUTER_PREFIX}.wifi_hal_start_executed",
    f"{OUTER_PREFIX}.scan_connect_linkup",
    f"{OUTER_PREFIX}.credentials",
    f"{OUTER_PREFIX}.dhcp_routing",
    f"{OUTER_PREFIX}.external_ping",
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
    parser.add_argument("--allow-esoc-conditional-response-preflight", action="store_true")
    parser.add_argument("--allow-cleanup-reboot", action="store_true")
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
        ("--allow-esoc-conditional-response-preflight", args.allow_esoc_conditional_response_preflight),
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
        "--allow-esoc-conditional-response-preflight",
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


def read_step_file(store: EvidenceStore, step: dict[str, Any]) -> str:
    rel = str(step.get("file") or "")
    path = store.run_dir / rel
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return str(step.get("payload") or "")


def post_surface(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], prefix: str = "post") -> dict[str, Any]:
    ps = v857.run_device(args, store, steps, f"{prefix}-ps", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], timeout=20.0)
    net = v857.run_device(args, store, steps, f"{prefix}-proc-net-dev", ["cat", "/proc/net/dev"], timeout=12.0)
    dmesg = v857.run_device(
        args,
        store,
        steps,
        f"{prefix}-dmesg-wifi-esoc-tail",
        v855.shell_cmd(
            args,
            "$BB dmesg 2>&1 | $BB grep -iE 'esoc|mdm|subsys|wlan|wlfw|qmi|qrtr|mhi|icnss|cnss' | $BB tail -n 180 || true".replace("$BB", args.busybox),
        ),
        timeout=20.0,
    )
    actor_re = re.compile(r"\b(pm_proxy_helper|pm-service|pm-proxy|mdm_helper|servicemanager|hwservicemanager|vndservicemanager|cnss_diag|cnss-daemon|wificond|supplicant|hostapd|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b")
    wifi_re = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)
    ps_text = read_step_file(store, ps)
    net_text = read_step_file(store, net)
    dmesg_text = read_step_file(store, dmesg)
    helper_lines = [line.strip() for line in ps_text.splitlines() if "a90_android_execns_probe" in line]
    return {
        "actor_hits": [line.strip() for line in ps_text.splitlines() if actor_re.search(line)][:16],
        "wifi_link_hits": [line.strip() for line in net_text.splitlines() if wifi_re.search(line)][:16],
        "helper_process_hits": helper_lines[:16],
        "wlfw_or_wlan_dmesg_hits": [
            line.strip()
            for line in dmesg_text.splitlines()
            if re.search(r"wlfw|wlan0|bdf|fw_ready|qmi|qrtr|mdm|esoc|subsys", line, re.IGNORECASE)
        ][-32:],
    }


def helper_surface(text: str) -> dict[str, Any]:
    keys = parse_keys(text)
    outer = {
        "mode": keys.get(f"{OUTER_PREFIX}.mode", ""),
        "allowed": keys.get(f"{OUTER_PREFIX}.allowed", ""),
        "open_req_attempted": keys.get(f"{OUTER_PREFIX}.open_req_attempted", ""),
        "open_req_fd": keys.get(f"{OUTER_PREFIX}.open_req.fd", ""),
        "open_req_errno": keys.get(f"{OUTER_PREFIX}.open_req.errno", ""),
        "reg_req_eng_attempted": keys.get(f"{OUTER_PREFIX}.reg_req_eng_attempted", ""),
        "reg_req_eng_rc": keys.get(f"{OUTER_PREFIX}.ioctl.REG_REQ_ENG.rc", ""),
        "reg_req_eng_errno": keys.get(f"{OUTER_PREFIX}.ioctl.REG_REQ_ENG.errno", ""),
        "req_fd_held": keys.get(f"{OUTER_PREFIX}.req_fd_held", ""),
        "subsys_esoc0_open_attempted": keys.get(f"{OUTER_PREFIX}.subsys_esoc0_open_attempted", ""),
        "subsys_esoc0_opened": keys.get(f"{OUTER_PREFIX}.subsys_esoc0_opened", ""),
        "subsys_esoc0_open_errno": keys.get(f"{OUTER_PREFIX}.subsys_esoc0_open_errno", ""),
        "hold_sec": keys.get(f"{OUTER_PREFIX}.hold_sec", ""),
        "close_req_attempted": keys.get(f"{OUTER_PREFIX}.close_req_attempted", ""),
        "exited": keys.get(f"{OUTER_PREFIX}.exited", ""),
        "exit_code": keys.get(f"{OUTER_PREFIX}.exit_code", ""),
        "signal": keys.get(f"{OUTER_PREFIX}.signal", ""),
        "timed_out": keys.get(f"{OUTER_PREFIX}.timed_out", ""),
        "term_sent": keys.get(f"{OUTER_PREFIX}.term_sent", ""),
        "kill_sent": keys.get(f"{OUTER_PREFIX}.kill_sent", ""),
        "reaped": keys.get(f"{OUTER_PREFIX}.reaped", ""),
        "all_postflight_safe": keys.get(f"{OUTER_PREFIX}.all_postflight_safe", ""),
        "result": keys.get(f"{OUTER_PREFIX}.result", ""),
        "reason": keys.get(f"{OUTER_PREFIX}.reason", ""),
    }
    conditional = {
        "begin": keys.get(f"{COND_PREFIX}.begin", ""),
        "mode": keys.get(f"{COND_PREFIX}.mode", ""),
        "hold_sec": keys.get(f"{COND_PREFIX}.hold_sec", ""),
        "wait_rc": keys.get(f"{COND_PREFIX}.wait_for_req.ioctl.rc", ""),
        "wait_errno": keys.get(f"{COND_PREFIX}.wait_for_req.ioctl.errno", ""),
        "wait_byte_count": keys.get(f"{COND_PREFIX}.wait_for_req.ioctl.byte_count", ""),
        "wait_value": keys.get(f"{COND_PREFIX}.wait_for_req.ioctl.value", ""),
        "wait_request_name": keys.get(f"{COND_PREFIX}.wait_for_req.ioctl.request_name", ""),
        "request_observed": keys.get(f"{COND_PREFIX}.wait_for_req.ioctl.request_observed", ""),
        "wait_result": keys.get(f"{COND_PREFIX}.wait_for_req.result", ""),
        "img_xfer_attempted": keys.get(f"{COND_PREFIX}.notify.ESOC_IMG_XFER_DONE.attempted", ""),
        "img_xfer_sent": keys.get(f"{COND_PREFIX}.notify.ESOC_IMG_XFER_DONE.sent", ""),
        "status_poll_count": keys.get(f"{COND_PREFIX}.status.poll_count", ""),
        "status_ready": keys.get(f"{COND_PREFIX}.status.ready", ""),
        "status_last_value": keys.get(f"{COND_PREFIX}.status.last_value", ""),
        "boot_done_attempted": keys.get(f"{COND_PREFIX}.notify.ESOC_BOOT_DONE.attempted", ""),
        "boot_done_sent": keys.get(f"{COND_PREFIX}.notify.ESOC_BOOT_DONE.sent", ""),
        "elapsed_ms": keys.get(f"{COND_PREFIX}.elapsed_ms", ""),
        "result": keys.get(f"{COND_PREFIX}.result", ""),
        "end": keys.get(f"{COND_PREFIX}.end", ""),
    }
    return {
        "outer": outer,
        "conditional": conditional,
        "snapshots": {
            key: value
            for key, value in keys.items()
            if key.startswith(f"{OUTER_PREFIX}.snapshot.")
        },
        "forbidden_true": {key: keys.get(key) for key in FORBIDDEN_TRUE_KEYS if keys.get(key) not in (None, "0")},
    }


def run_a90ctl_capture(store: EvidenceStore, name: str, command: list[str], timeout: float) -> dict[str, Any]:
    result = subprocess.run(
        ["python3", "scripts/revalidation/a90ctl.py", *command],
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    rel = f"reboot_cleanup/{re.sub(r'[^A-Za-z0-9_.+-]+', '-', name).strip('-')}.txt"
    output = v857.redact(result.stdout)
    store.write_text(rel, output.rstrip() + "\n")
    return {"name": name, "rc": result.returncode, "ok": result.returncode == 0, "file": rel, "output": output[-4096:]}


def reboot_cleanup(args: argparse.Namespace, store: EvidenceStore, reason: str) -> dict[str, Any]:
    cleanup: dict[str, Any] = {
        "requested": True,
        "reason": reason,
        "reboot_command": None,
        "attempts": [],
        "bootstatus_ok": False,
        "selftest_fail0": False,
        "healthy": False,
    }
    reboot_cmd = ["--timeout", "3", "--allow-error", "--retry-unsafe", "reboot"]
    try:
        cleanup["reboot_command"] = run_a90ctl_capture(store, "reboot-command", reboot_cmd, timeout=6.0)
    except subprocess.TimeoutExpired as exc:
        rel = "reboot_cleanup/reboot-command-timeout.txt"
        store.write_text(rel, (exc.stdout or "") + "\n[TIMEOUT]\n")
        cleanup["reboot_command"] = {"name": "reboot-command", "rc": -1, "ok": False, "file": rel, "output": "timeout"}

    for attempt in range(1, 31):
        time.sleep(2.0)
        boot = run_a90ctl_capture(store, f"post-reboot-bootstatus-{attempt:02d}", ["--timeout", "7", "--json", "bootstatus"], timeout=10.0)
        selftest = run_a90ctl_capture(store, f"post-reboot-selftest-{attempt:02d}", ["--timeout", "7", "--json", "selftest"], timeout=10.0)
        boot_ok = boot["ok"] and ("BOOT OK" in boot["output"] or '"status": "ok"' in boot["output"])
        selftest_ok = selftest["ok"] and ("fail=0" in selftest["output"] or "fail=0" in selftest["output"].replace("\\n", "\n"))
        cleanup["attempts"].append({
            "attempt": attempt,
            "bootstatus": boot,
            "selftest": selftest,
            "boot_ok": boot_ok,
            "selftest_ok": selftest_ok,
        })
        if boot_ok and selftest_ok:
            cleanup["bootstatus_ok"] = True
            cleanup["selftest_fail0"] = True
            cleanup["healthy"] = True
            break
    return cleanup


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
        helper = v857.run_device(args, store, steps, "esoc-conditional-response", helper_command(args), timeout=args.toybox_timeout_sec + 25.0)
        helper_payload = read_step_file(store, helper)
        analysis["helper"] = helper_surface(helper_payload)
    finally:
        v857.run_device(args, store, steps, "cleanup-created-nodes", v855.shell_cmd(args, v855.cleanup_script(args)), timeout=20.0)
    v857.run_device(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)
    analysis["post_surface"] = post_surface(args, store, steps)
    analysis["node"] = v855.analyze(steps)
    helper = analysis.get("helper") or {}
    outer = helper.get("outer") or {}
    post = analysis.get("post_surface") or {}
    cleanup_needed = outer.get("all_postflight_safe") == "0" or bool(post.get("helper_process_hits"))
    analysis["cleanup_needed"] = cleanup_needed
    if cleanup_needed and args.allow_cleanup_reboot:
        analysis["reboot_cleanup"] = reboot_cleanup(args, store, "helper child not proven stopped")
    elif cleanup_needed:
        analysis["reboot_cleanup"] = {"requested": False, "reason": "cleanup needed but --allow-cleanup-reboot not set", "healthy": False}
    else:
        analysis["reboot_cleanup"] = {"requested": False, "reason": "not needed", "healthy": True}
    return steps, analysis


def decide(args: argparse.Namespace,
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v891-plan-helper-v142-missing", False, f"local={local}", "build and deploy helper v142 before V891"
        return "v891-esoc-conditional-response-plan-ready", True, "plan-only; no device command executed", "run bounded V891 live proof"
    missing = required_flags(args)
    if missing:
        return "v891-esoc-conditional-response-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V891 flags"
    failed_steps = [step["name"] for step in steps if not step.get("ok") and step.get("name") != "remote-helper-usage"]
    if failed_steps:
        return "v891-step-failed", False, f"failed_steps={failed_steps}", "inspect V891 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v891-helper-v142-remote-mismatch", False, f"remote={remote}", "redeploy helper v142 before V891"
    node = analysis.get("node") or {}
    if not ((node.get("materialize") or {}).get("all_target_nodes_accounted")):
        return "v891-node-materialization-failed", False, f"node={node}", "repair node materialization before retry"
    if not ((node.get("cleanup") or {}).get("removed_all_created")):
        return "v891-node-cleanup-review", False, f"node={node}", "cleanup V891 nodes manually before continuing"
    if not ((node.get("postflight") or {}).get("selftest_fail0")):
        return "v891-postflight-health-review", False, f"node={node}", "restore native health before continuing"
    helper = analysis.get("helper") or {}
    if helper.get("forbidden_true"):
        return "v891-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    outer = helper.get("outer") or {}
    conditional = helper.get("conditional") or {}
    if outer.get("allowed") != "1" or outer.get("open_req_attempted") != "1" or outer.get("reg_req_eng_attempted") != "1":
        return "v891-helper-mode-not-executed", False, f"outer={outer}", "fix V891 helper command before retry"
    if outer.get("reg_req_eng_rc") != "0":
        return "v891-reg-req-eng-review", False, f"outer={outer}", "classify REG_REQ_ENG before retrying response proof"
    if conditional.get("begin") != "1":
        return "v891-conditional-child-not-started", False, f"conditional={conditional}", "fix helper conditional child before retry"
    if conditional.get("request_observed") != "1" or conditional.get("wait_value") != "1":
        return "v891-esoc-req-img-not-observed", False, f"conditional={conditional}", "inspect eSoC request timing before retry"
    if conditional.get("img_xfer_sent") != "1":
        return "v891-img-xfer-not-sent", False, f"conditional={conditional}", "inspect ESOC_NOTIFY failure before retry"
    post = analysis.get("post_surface") or {}
    if post.get("actor_hits") or post.get("wifi_link_hits"):
        return "v891-post-surface-not-clean", False, f"post={post}", "cleanup actor or Wi-Fi surface before continuing"
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v891-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify or rerun recovery reboot before continuing"
    if conditional.get("boot_done_sent") == "1":
        return "v891-boot-done-sent-reboot-cleaned", True, f"conditional={conditional}", "inspect WLFW/service69/wlan0 deltas before actor/HAL work"
    if conditional.get("status_ready") == "0":
        return "v891-img-xfer-done-sent-status-not-ready-reboot-cleaned", True, f"conditional={conditional}", "classify why ESOC_GET_STATUS stayed not-ready"
    return "v891-conditional-response-review", False, f"conditional={conditional}", "inspect V891 conditional response evidence"


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V891 eSoC Conditional Response Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- conditional_response_executed: `{manifest['conditional_response_executed']}`",
        f"- reg_req_eng_ioctl_executed: `{manifest['reg_req_eng_ioctl_executed']}`",
        f"- subsys_esoc0_open_attempted: `{manifest['subsys_esoc0_open_attempted']}`",
        f"- esoc_notify_executed: `{manifest['esoc_notify_executed']}`",
        f"- boot_done_notify_executed: `{manifest['boot_done_notify_executed']}`",
        f"- cleanup_reboot_executed: `{manifest['cleanup_reboot_executed']}`",
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
        "- `REG_REQ_ENG`, `ESOC_WAIT_FOR_REQ`, guarded `ESOC_NOTIFY`, and `ESOC_GET_STATUS` are the only allowed eSoC actions.",
        "- No `REG_CMD_ENG`, direct userspace `CMD_EXE`, explicit userspace `PWR_ON`, or blind `ESOC_BOOT_DONE`.",
        "- No actor start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "- No module load/unload, boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write, or Wi-Fi link-up.",
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
    outer = helper.get("outer") or {}
    conditional = helper.get("conditional") or {}
    cleanup = analysis.get("reboot_cleanup") or {}
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
        "conditional_response_executed": will_execute,
        "reg_req_eng_ioctl_executed": outer.get("reg_req_eng_attempted") == "1",
        "subsys_esoc0_open_attempted": outer.get("subsys_esoc0_open_attempted") == "1",
        "esoc_notify_executed": conditional.get("img_xfer_attempted") == "1" or conditional.get("boot_done_attempted") == "1",
        "boot_done_notify_executed": conditional.get("boot_done_attempted") == "1",
        "cleanup_reboot_executed": bool(cleanup.get("requested")),
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
    print(f"conditional_response_executed: {manifest['conditional_response_executed']}")
    print(f"reg_req_eng_ioctl_executed: {manifest['reg_req_eng_ioctl_executed']}")
    print(f"subsys_esoc0_open_attempted: {manifest['subsys_esoc0_open_attempted']}")
    print(f"esoc_notify_executed: {manifest['esoc_notify_executed']}")
    print(f"boot_done_notify_executed: {manifest['boot_done_notify_executed']}")
    print(f"cleanup_reboot_executed: {manifest['cleanup_reboot_executed']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
