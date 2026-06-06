#!/usr/bin/env python3
"""V900 bounded live mdm_helper/ks image-contract proof.

Runs deployed helper v144 in
wifi-companion-mdm-helper-ks-image-contract-preflight mode. The only newly
allowed live actions are starting /vendor/bin/mdm_helper, then opening
/dev/subsys_esoc0 only after mdm_helper is observable, and observing whether
/vendor/bin/ks or the MHI pipe command line appears. It does not register eSoC
engines, send ESOC_NOTIFY/BOOT_DONE, start service-manager/CNSS/Wi-Fi HAL,
scan/connect, use credentials, configure DHCP/routes, or external ping.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v900-mdm-helper-ks-contract-live")
LATEST_POINTER = Path("tmp/wifi/latest-v900-mdm-helper-ks-contract-live.txt")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v901-execns-helper-v145-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "30c042376ac89f211f597c5a3a17da1e33ce208cfe3b1b839221789a983399c1"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v145"
MODE = "wifi-companion-mdm-helper-ks-image-contract-preflight"
PREFIX = "mdm_helper_ks_image_contract"

FORBIDDEN_TRUE_KEYS = (
    f"{PREFIX}.service_manager_start_executed",
    f"{PREFIX}.cnss_start_executed",
    f"{PREFIX}.wifi_hal_start_executed",
    f"{PREFIX}.scan_connect_linkup",
    f"{PREFIX}.credentials",
    f"{PREFIX}.dhcp_routing",
    f"{PREFIX}.external_ping",
    f"{PREFIX}.reg_req_eng_attempted",
    f"{PREFIX}.notify_attempted",
    f"{PREFIX}.boot_done_attempted",
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
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-mdm-helper-ks-contract-preflight", action="store_true")
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


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


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
        ("--allow-mdm-helper-ks-contract-preflight", args.allow_mdm_helper_ks_contract_preflight),
        ("--allow-cleanup-reboot", args.allow_cleanup_reboot),
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
        "--allow-mdm-helper-ks-contract-preflight",
        "--timeout-sec",
        str(min(max(args.helper_timeout_sec, 4), 30)),
    ]


def read_step_file(store: EvidenceStore, step: dict[str, Any]) -> str:
    rel = str(step.get("file") or "")
    path = store.run_dir / rel
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return str(step.get("payload") or "")


def remote_helper_state(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    sha = v857.run_device(args, store, steps, "remote-helper-sha", ["run", args.toybox, "sha256sum", args.helper], timeout=12.0)
    usage = v857.run_device(args, store, steps, "remote-helper-usage", ["run", args.helper], timeout=12.0)
    sha_payload = read_step_file(store, sha)
    usage_payload = read_step_file(store, usage)
    return {
        "sha_ok": args.helper_sha256 in sha_payload,
        "marker_ok": args.helper_marker in usage_payload,
        "mode_ok": MODE in usage_payload,
        "sha_file": sha.get("file"),
        "usage_file": usage.get("file"),
    }


def post_surface(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], prefix: str = "post") -> dict[str, Any]:
    ps = v857.run_device(args, store, steps, f"{prefix}-ps", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], timeout=20.0)
    net = v857.run_device(args, store, steps, f"{prefix}-proc-net-dev", ["cat", "/proc/net/dev"], timeout=12.0)
    subsys = v857.run_device(
        args,
        store,
        steps,
        f"{prefix}-subsys-state",
        v855.shell_cmd(
            args,
            (
                "$BB cat /sys/bus/msm_subsys/devices/subsys9/state 2>/dev/null || true; "
                "$BB cat /proc/interrupts 2>/dev/null | $BB grep -iE 'mdm|esoc|gpio|142' || true"
            ).replace("$BB", args.busybox),
        ),
        timeout=12.0,
    )
    dmesg = v857.run_device(
        args,
        store,
        steps,
        f"{prefix}-dmesg-wifi-esoc-tail",
        v855.shell_cmd(
            args,
            (
                "$BB dmesg 2>&1 | "
                "$BB grep -iE 'esoc|mdm|subsys|wlan|wlfw|qmi|qrtr|mhi|icnss|cnss|gpio|ap2mdm|mdm2ap|pmic|pm8150' | "
                "$BB tail -n 220 || true"
            ).replace("$BB", args.busybox),
        ),
        timeout=20.0,
    )
    actor_re = re.compile(
        r"\b(pm_proxy_helper|pm-service|pm-proxy|mdm_helper|/vendor/bin/ks|"
        r"servicemanager|hwservicemanager|vndservicemanager|cnss_diag|cnss-daemon|"
        r"wificond|supplicant|hostapd|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b"
    )
    wifi_re = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)
    ps_text = read_step_file(store, ps)
    net_text = read_step_file(store, net)
    subsys_text = read_step_file(store, subsys)
    dmesg_text = read_step_file(store, dmesg)
    helper_lines = [line.strip() for line in ps_text.splitlines() if "a90_android_execns_probe" in line]
    actor_lines = [line.strip() for line in ps_text.splitlines() if actor_re.search(line)]
    return {
        "actor_hits": actor_lines[:20],
        "mdm_helper_or_ks_hits": [line for line in actor_lines if "mdm_helper" in line or "/vendor/bin/ks" in line][:12],
        "wifi_link_hits": [line.strip() for line in net_text.splitlines() if wifi_re.search(line)][:16],
        "helper_process_hits": helper_lines[:16],
        "subsys_state_tail": subsys_text.splitlines()[-32:],
        "wlfw_or_wlan_dmesg_hits": [
            line.strip()
            for line in dmesg_text.splitlines()
            if re.search(r"wlfw|wlan0|bdf|fw_ready|qmi|qrtr|mdm|esoc|subsys|mhi|gpio|ap2mdm|mdm2ap", line, re.IGNORECASE)
        ][-48:],
    }


def helper_surface(text: str) -> dict[str, Any]:
    keys = parse_keys(text)
    data = {
        "begin": keys.get(f"{PREFIX}.begin", ""),
        "mode": keys.get(f"{PREFIX}.mode", ""),
        "order": keys.get(f"{PREFIX}.order", ""),
        "allowed": keys.get(f"{PREFIX}.allowed", ""),
        "mdm_helper_start_attempted": keys.get(f"{PREFIX}.mdm_helper_start_attempted", ""),
        "mdm_helper_observable": keys.get(f"{PREFIX}.mdm_helper_observable", ""),
        "subsys_esoc0_open_gate_open": keys.get(f"{PREFIX}.subsys_esoc0_open_gate_open", ""),
        "subsys_esoc0_open_attempted": keys.get(f"{PREFIX}.subsys_esoc0_open_attempted", ""),
        "subsys_esoc0_opened": keys.get(f"{PREFIX}.subsys_esoc0_opened", ""),
        "subsys_esoc0_open_errno": keys.get(f"{PREFIX}.subsys_esoc0_open_errno", ""),
        "subsys_trigger_started": keys.get(f"{PREFIX}.subsys_trigger.started", ""),
        "subsys_trigger_exited": keys.get(f"{PREFIX}.subsys_trigger.exited", ""),
        "subsys_trigger_exit_code": keys.get(f"{PREFIX}.subsys_trigger.exit_code", ""),
        "subsys_trigger_signal": keys.get(f"{PREFIX}.subsys_trigger.signal", ""),
        "subsys_trigger_term_sent": keys.get(f"{PREFIX}.subsys_trigger.term_sent", ""),
        "subsys_trigger_kill_sent": keys.get(f"{PREFIX}.subsys_trigger.kill_sent", ""),
        "subsys_trigger_reaped": keys.get(f"{PREFIX}.subsys_trigger.reaped", ""),
        "ks_count_before": keys.get(f"{PREFIX}.ks_count.before", ""),
        "ks_count_window": keys.get(f"{PREFIX}.ks_count.window", ""),
        "ks_count_after": keys.get(f"{PREFIX}.ks_count.after", ""),
        "mhi_pipe_cmdline_count_window": keys.get(f"{PREFIX}.mhi_pipe_cmdline_count.window", ""),
        "mdm_helper_postflight_safe": keys.get(f"{PREFIX}.mdm_helper.postflight_safe", ""),
        "all_postflight_safe": keys.get(f"{PREFIX}.all_postflight_safe", ""),
        "timed_out": keys.get(f"{PREFIX}.timed_out", ""),
        "result": keys.get(f"{PREFIX}.result", ""),
        "reason": keys.get(f"{PREFIX}.reason", ""),
        "end": keys.get(f"{PREFIX}.end", ""),
    }
    return {
        "contract": data,
        "path_visibility": {
            key: value
            for key, value in keys.items()
            if key.startswith(f"{PREFIX}.path_visibility.")
        },
        "node_status": {
            key: value
            for key, value in keys.items()
            if key.startswith("android_node.")
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
    rel = f"reboot_cleanup/{safe_name(name)}.txt"
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
    helper_step = v857.run_device(args, store, steps, "mdm-helper-ks-contract", helper_command(args), timeout=args.toybox_timeout_sec + 25.0)
    analysis["helper"] = helper_surface(read_step_file(store, helper_step))
    v857.run_device(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)
    analysis["post_surface"] = post_surface(args, store, steps)
    contract = (analysis.get("helper") or {}).get("contract") or {}
    post = analysis.get("post_surface") or {}
    cleanup_needed = (
        contract.get("result") == "reboot-required"
        or contract.get("all_postflight_safe") == "0"
        or bool(post.get("helper_process_hits"))
        or bool(post.get("mdm_helper_or_ks_hits"))
    )
    analysis["cleanup_needed"] = cleanup_needed
    if cleanup_needed and args.allow_cleanup_reboot:
        analysis["reboot_cleanup"] = reboot_cleanup(args, store, "mdm_helper/ks/subsys trigger not proven stopped")
    elif cleanup_needed:
        analysis["reboot_cleanup"] = {"requested": False, "reason": "cleanup needed but --allow-cleanup-reboot not set", "healthy": False}
    else:
        analysis["reboot_cleanup"] = {"requested": False, "reason": "not needed", "healthy": True}
    return steps, analysis


def step_failures(steps: list[dict[str, Any]], helper: dict[str, Any]) -> list[str]:
    contract = helper.get("contract") or {}
    helper_has_evidence = contract.get("begin") == "1" and contract.get("end") == "1"
    ignored = {"remote-helper-usage"}
    if helper_has_evidence:
        ignored.add("mdm-helper-ks-contract")
    return [step["name"] for step in steps if not step.get("ok") and step.get("name") not in ignored]


def decide(args: argparse.Namespace,
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v900-plan-helper-v144-missing", False, f"local={local}", "build and deploy helper v144 before V900"
        return "v900-mdm-helper-ks-contract-plan-ready", True, "plan-only; no device command executed", "run bounded V900 mdm_helper/ks contract proof"
    missing = required_flags(args)
    if missing:
        return "v900-mdm-helper-ks-contract-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V900 flags"
    helper = analysis.get("helper") or {}
    failed_steps = step_failures(steps, helper)
    if failed_steps:
        return "v900-step-failed", False, f"failed_steps={failed_steps}", "inspect V900 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v900-helper-v144-remote-mismatch", False, f"remote={remote}", "redeploy helper v144 before V900"
    if helper.get("forbidden_true"):
        return "v900-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    contract = helper.get("contract") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1" or contract.get("mdm_helper_start_attempted") != "1":
        return "v900-helper-mode-not-executed", False, f"contract={contract}", "fix V900 helper command before retry"
    if contract.get("subsys_esoc0_open_attempted") == "1" and contract.get("mdm_helper_observable") != "1":
        return "v900-open-order-violation", False, f"contract={contract}", "audit helper ordering before retry"
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v900-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify or rerun recovery reboot before continuing"
    result = contract.get("result")
    if result == "ks-mhi-observed":
        return "v900-ks-mhi-observed", True, f"contract={contract}", "inspect mdm3/GPIO142/WLFW/BDF/wlan0 deltas before HAL or scan work"
    if result == "mdm-helper-window-no-ks":
        return "v900-mdm-helper-observed-no-ks", True, f"contract={contract}", "classify why mdm_helper did not spawn ks or MHI pipe handling"
    if result == "mdm-helper-not-observable":
        return "v900-mdm-helper-not-observable-clean", True, f"contract={contract}", "classify mdm_helper startup/runtime dependency before retry"
    if result == "reboot-required":
        return "v900-reboot-required-cleaned", True, f"contract={contract}", "inspect pre-reboot evidence and plan safer reduced live contract"
    return "v900-mdm-helper-ks-contract-review", False, f"contract={contract}", "inspect V900 helper output before continuing"


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V900 mdm_helper/ks Contract Live Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- mdm_helper_start_executed: `{manifest['mdm_helper_start_executed']}`",
        f"- ks_start_executed: `{manifest['ks_start_executed']}`",
        f"- subsys_esoc0_open_attempted: `{manifest['subsys_esoc0_open_attempted']}`",
        f"- live_esoc_ioctl_executed: `{manifest['live_esoc_ioctl_executed']}`",
        f"- cleanup_reboot_executed: `{manifest['cleanup_reboot_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
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
        "- Only `/vendor/bin/mdm_helper` start and gated `/dev/subsys_esoc0` open are permitted.",
        "- No `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, `PWR_ON`, `WAIT_FOR_REQ`, `ESOC_NOTIFY`, or `BOOT_DONE`.",
        "- No service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
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
    contract = helper.get("contract") or {}
    cleanup = analysis.get("reboot_cleanup") or {}
    ks_window = int(contract.get("ks_count_window") or "0") if str(contract.get("ks_count_window") or "0").lstrip("-").isdigit() else 0
    mhi_window = int(contract.get("mhi_pipe_cmdline_count_window") or "0") if str(contract.get("mhi_pipe_cmdline_count_window") or "0").lstrip("-").isdigit() else 0
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
        "mdm_helper_start_executed": contract.get("mdm_helper_start_attempted") == "1",
        "ks_start_executed": ks_window > 0 or mhi_window > 0,
        "subsys_esoc0_open_attempted": contract.get("subsys_esoc0_open_attempted") == "1",
        "live_esoc_ioctl_executed": False,
        "cleanup_reboot_executed": bool(cleanup.get("requested")),
        "service_manager_start_executed": False,
        "cnss_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
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
    print(f"mdm_helper_start_executed: {manifest['mdm_helper_start_executed']}")
    print(f"ks_start_executed: {manifest['ks_start_executed']}")
    print(f"subsys_esoc0_open_attempted: {manifest['subsys_esoc0_open_attempted']}")
    print(f"live_esoc_ioctl_executed: {manifest['live_esoc_ioctl_executed']}")
    print(f"cleanup_reboot_executed: {manifest['cleanup_reboot_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
