#!/usr/bin/env python3
"""V1199 Option B: ESOC IMG_XFER_DONE + MHI device appearance observation.

Runs helper v238 in wifi-companion-esoc-img-xfer-mhi-observe mode.

Gate: after REG_REQ_ENG + ESOC_WAIT_FOR_REQ → receive ESOC_REQ_IMG → send
ESOC_IMG_XFER_DONE, then poll /sys/bus/mhi/devices/, /dev/mhi_0305_01.01.00_pipe_10,
and GPIO 142 IRQ count for up to hold_sec seconds.

Does NOT send ESOC_BOOT_DONE. Does not start Android actors, Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, or external ping.

Key question: does SDX50M create MHI devices after ESOC_IMG_XFER_DONE, even
without a real firmware image transfer?
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1199-esoc-img-xfer-mhi-observe")
LATEST_POINTER = Path("tmp/wifi/latest-v1199-esoc-img-xfer-mhi-observe.txt")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_LOCAL_HELPER = Path(
    "stage3/linux_init/helpers/a90_android_execns_probe"
)
DEFAULT_HELPER_SHA256 = (
    "867f96632b07481c4244bcd7635cec65fc782e9905cb2313630563f0f4e4516a"
)
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v238"
DEFAULT_MARKER = "/tmp/a90-v1199-esoc-img-xfer-mhi-observe.created"
MODE = "wifi-companion-esoc-img-xfer-mhi-observe"
ALLOW_FLAG = "--allow-esoc-img-xfer-mhi-observe"

OUTER_PREFIX = "esoc_req_registered_subsys_hold_preflight"
MHI_PREFIX = "esoc_img_xfer_mhi_observe"

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
    f"{MHI_PREFIX}.notify.ESOC_BOOT_DONE.attempted",
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
    parser.add_argument("--helper-timeout-sec", type=int, default=30,
                        help="MHI observe window: hold_sec = timeout_sec - 2 (max 30)")
    parser.add_argument("--toybox-timeout-sec", type=int, default=60)
    parser.add_argument("--marker", default=DEFAULT_MARKER)
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-node-materialization", action="store_true")
    parser.add_argument("--allow-node-cleanup", action="store_true")
    parser.add_argument(ALLOW_FLAG, dest="allow_esoc_img_xfer_mhi_observe", action="store_true")
    parser.add_argument("--allow-cleanup-reboot", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--no-hide-on-busy", dest="hide_on_busy", action="store_false")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fobj:
        for chunk in iter(lambda: fobj.read(1024 * 1024), b""):
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
    info: dict[str, Any] = {
        "path": str(path), "exists": path.exists(),
        "sha256": "", "marker": False, "mode": False,
    }
    if not path.exists():
        return info
    info["sha256"] = sha256_file(path)
    try:
        strings = subprocess.run(
            ["strings", str(path)],
            cwd=repo_path("."),
            check=False, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30,
        ).stdout
        info["marker"] = args.helper_marker in strings
        info["mode"] = MODE in strings
    except Exception:
        pass
    return info


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    for flag, enabled in (
        ("--allow-mountsystem-ro", args.allow_mountsystem_ro),
        ("--allow-node-materialization", args.allow_node_materialization),
        ("--allow-node-cleanup", args.allow_node_cleanup),
        (ALLOW_FLAG, args.allow_esoc_img_xfer_mhi_observe),
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
        ALLOW_FLAG,
        "--timeout-sec",
        str(min(max(args.helper_timeout_sec, 4), 30)),
    ]


def remote_helper_state(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    sha = v857.run_device(
        args, store, steps, "remote-helper-sha",
        ["run", args.toybox, "sha256sum", args.helper], timeout=12.0,
    )
    usage = v857.run_device(
        args, store, steps, "remote-helper-usage",
        ["run", args.helper], timeout=12.0,
    )
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


def post_surface(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    prefix: str = "post",
) -> dict[str, Any]:
    ps = v857.run_device(
        args, store, steps, f"{prefix}-ps",
        ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], timeout=20.0,
    )
    net = v857.run_device(
        args, store, steps, f"{prefix}-proc-net-dev",
        ["cat", "/proc/net/dev"], timeout=12.0,
    )
    dmesg = v857.run_device(
        args, store, steps,
        f"{prefix}-dmesg-esoc-mhi-tail",
        v855.shell_cmd(
            args,
            (
                "$BB dmesg 2>&1 | $BB grep -iE "
                "'esoc|mdm|subsys|mhi|pci|wlan|wlfw|qmi|qrtr|icnss|cnss' "
                "| $BB tail -n 180 || true"
            ).replace("$BB", args.busybox),
        ),
        timeout=20.0,
    )
    actor_re = re.compile(
        r"\b(pm_proxy_helper|pm-service|pm-proxy|mdm_helper|servicemanager|"
        r"hwservicemanager|vndservicemanager|cnss_diag|cnss-daemon|wificond|"
        r"supplicant|hostapd|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b"
    )
    wifi_re = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)
    ps_text = read_step_file(store, ps)
    net_text = read_step_file(store, net)
    dmesg_text = read_step_file(store, dmesg)
    helper_lines = [line.strip() for line in ps_text.splitlines() if "a90_android_execns_probe" in line]
    return {
        "actor_hits": [line.strip() for line in ps_text.splitlines() if actor_re.search(line)][:16],
        "wifi_link_hits": [line.strip() for line in net_text.splitlines() if wifi_re.search(line)][:16],
        "helper_process_hits": helper_lines[:16],
        "mhi_dmesg_hits": [
            line.strip()
            for line in dmesg_text.splitlines()
            if re.search(r"mhi|pci|mdm|esoc|subsys", line, re.IGNORECASE)
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
        "hold_sec": keys.get(f"{OUTER_PREFIX}.hold_sec", ""),
        "result": keys.get(f"{OUTER_PREFIX}.result", ""),
        "all_postflight_safe": keys.get(f"{OUTER_PREFIX}.all_postflight_safe", ""),
    }
    mhi_obs = {
        "begin": keys.get(f"{MHI_PREFIX}.begin", ""),
        "mode": keys.get(f"{MHI_PREFIX}.mode", ""),
        "hold_sec": keys.get(f"{MHI_PREFIX}.hold_sec", ""),
        "wait_rc": keys.get(f"{MHI_PREFIX}.wait_for_req.ioctl.rc", ""),
        "wait_value": keys.get(f"{MHI_PREFIX}.wait_for_req.ioctl.value", ""),
        "wait_request_name": keys.get(f"{MHI_PREFIX}.wait_for_req.ioctl.request_name", ""),
        "request_observed": keys.get(f"{MHI_PREFIX}.wait_for_req.ioctl.request_observed", ""),
        "wait_result": keys.get(f"{MHI_PREFIX}.wait_for_req.result", ""),
        "img_xfer_attempted": keys.get(f"{MHI_PREFIX}.notify.ESOC_IMG_XFER_DONE.attempted", ""),
        "img_xfer_sent": keys.get(f"{MHI_PREFIX}.notify.ESOC_IMG_XFER_DONE.sent", ""),
        "img_xfer_rc": keys.get(f"{MHI_PREFIX}.notify.ESOC_IMG_XFER_DONE.rc", ""),
        "img_xfer_elapsed_ms": keys.get(f"{MHI_PREFIX}.notify.ESOC_IMG_XFER_DONE.elapsed_ms", ""),
        "boot_done_attempted": keys.get(f"{MHI_PREFIX}.notify.ESOC_BOOT_DONE.attempted", ""),
        "mhi_appeared": keys.get(f"{MHI_PREFIX}.mhi_poll.mhi_appeared", ""),
        "mhi_appeared_at_ms": keys.get(f"{MHI_PREFIX}.mhi_poll.mhi_appeared_at_ms", ""),
        "mhi_appeared_at_index": keys.get(f"{MHI_PREFIX}.mhi_poll.mhi_appeared_at_index", ""),
        "mhi_total_polls": keys.get(f"{MHI_PREFIX}.mhi_poll.total_polls", ""),
        "result": keys.get(f"{MHI_PREFIX}.result", ""),
        "elapsed_ms": keys.get(f"{MHI_PREFIX}.elapsed_ms", ""),
        "end": keys.get(f"{MHI_PREFIX}.end", ""),
    }
    # Collect per-poll MHI snapshots
    poll_snapshots: list[dict[str, str]] = []
    idx = 0
    while True:
        poll_key = f"{MHI_PREFIX}.mhi_poll.{idx:02d}"
        elapsed = keys.get(f"{poll_key}.elapsed_ms", "")
        if not elapsed:
            break
        poll_snapshots.append({
            "elapsed_ms": elapsed,
            "mhi_pipe_exists": keys.get(f"{poll_key}.mhi_pipe_exists", ""),
            "mhi_bus_count": keys.get(f"{poll_key}.mhi_bus_count", ""),
            "gpio142_count": keys.get(f"{poll_key}.gpio142_count", ""),
        })
        idx += 1
    return {
        "outer": outer,
        "mhi_obs": mhi_obs,
        "poll_snapshots": poll_snapshots,
        "forbidden_true": {
            key: keys.get(key)
            for key in FORBIDDEN_TRUE_KEYS
            if keys.get(key) not in (None, "0")
        },
    }


def run_a90ctl_capture(
    store: EvidenceStore,
    name: str,
    command: list[str],
    timeout: float,
) -> dict[str, Any]:
    result = subprocess.run(
        ["python3", "scripts/revalidation/a90ctl.py", *command],
        cwd=repo_path("."),
        check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    rel = f"reboot_cleanup/{re.sub(r'[^A-Za-z0-9_.+-]+', '-', name).strip('-')}.txt"
    output = v857.redact(result.stdout)
    store.write_text(rel, output.rstrip() + "\n")
    return {
        "name": name, "rc": result.returncode,
        "ok": result.returncode == 0,
        "file": rel, "output": output[-4096:],
    }


def reboot_cleanup(
    args: argparse.Namespace,
    store: EvidenceStore,
    reason: str,
) -> dict[str, Any]:
    cleanup: dict[str, Any] = {
        "requested": True, "reason": reason,
        "reboot_command": None, "attempts": [],
        "bootstatus_ok": False, "selftest_fail0": False, "healthy": False,
    }
    reboot_cmd = ["--timeout", "3", "--allow-error", "--retry-unsafe", "reboot"]
    try:
        cleanup["reboot_command"] = run_a90ctl_capture(
            store, "reboot-command", reboot_cmd, timeout=6.0,
        )
    except subprocess.TimeoutExpired as exc:
        rel = "reboot_cleanup/reboot-command-timeout.txt"
        store.write_text(rel, (exc.stdout or "") + "\n[TIMEOUT]\n")
        cleanup["reboot_command"] = {
            "name": "reboot-command", "rc": -1, "ok": False,
            "file": rel, "output": "timeout",
        }
    for attempt in range(1, 31):
        time.sleep(2.0)
        boot = run_a90ctl_capture(
            store, f"post-reboot-bootstatus-{attempt:02d}",
            ["--timeout", "7", "--json", "bootstatus"], timeout=10.0,
        )
        selftest = run_a90ctl_capture(
            store, f"post-reboot-selftest-{attempt:02d}",
            ["--timeout", "7", "--json", "selftest"], timeout=10.0,
        )
        boot_ok = boot["ok"] and (
            "BOOT OK" in boot["output"] or '"status": "ok"' in boot["output"]
        )
        selftest_ok = selftest["ok"] and (
            "fail=0" in selftest["output"]
            or "fail=0" in selftest["output"].replace("\\n", "\n")
        )
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


def execute(
    args: argparse.Namespace,
    store: EvidenceStore,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    v857.run_device(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    if args.allow_mountsystem_ro:
        v857.run_device(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    analysis["remote_helper"] = remote_helper_state(args, store, steps)
    v857.run_device(
        args, store, steps, "node-preflight",
        v855.shell_cmd(args, v855.preflight_script(args)), timeout=20.0,
    )
    try:
        v857.run_device(
            args, store, steps, "materialize-android-node-parity",
            v855.shell_cmd(args, v855.materialize_script(args)), timeout=20.0,
        )
        helper = v857.run_device(
            args, store, steps, "esoc-img-xfer-mhi-observe",
            helper_command(args), timeout=args.toybox_timeout_sec + 30.0,
        )
        helper_payload = read_step_file(store, helper)
        analysis["helper"] = helper_surface(helper_payload)
    finally:
        v857.run_device(
            args, store, steps, "cleanup-created-nodes",
            v855.shell_cmd(args, v855.cleanup_script(args)), timeout=20.0,
        )
    v857.run_device(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)
    analysis["post_surface"] = post_surface(args, store, steps)
    analysis["node"] = v855.analyze(steps)
    helper_data = analysis.get("helper") or {}
    outer = helper_data.get("outer") or {}
    post = analysis.get("post_surface") or {}
    cleanup_needed = (
        outer.get("all_postflight_safe") == "0"
        or bool(post.get("helper_process_hits"))
    )
    analysis["cleanup_needed"] = cleanup_needed
    if cleanup_needed and args.allow_cleanup_reboot:
        analysis["reboot_cleanup"] = reboot_cleanup(
            args, store, "helper child not proven stopped",
        )
    elif cleanup_needed:
        analysis["reboot_cleanup"] = {
            "requested": False,
            "reason": "cleanup needed but --allow-cleanup-reboot not set",
            "healthy": False,
        }
    else:
        analysis["reboot_cleanup"] = {
            "requested": False, "reason": "not needed", "healthy": True,
        }
    return steps, analysis


def decide(
    args: argparse.Namespace,
    local: dict[str, Any],
    steps: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        ok = local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]
        if not ok:
            return (
                "v1199-plan-helper-v238-missing",
                False,
                f"local helper v238 not found or sha mismatch: {local}",
                "deploy helper v238 before V1199 run",
            )
        return (
            "v1199-esoc-img-xfer-mhi-observe-plan-ready",
            True,
            "plan-only; no device command executed",
            "run bounded V1199 live proof with --allow-esoc-img-xfer-mhi-observe",
        )
    missing = required_flags(args)
    if missing:
        return (
            "v1199-approval-required",
            False,
            f"missing flags: {', '.join(missing)}",
            "rerun with explicit V1199 approval flags",
        )
    failed_steps = [
        step["name"] for step in steps
        if not step.get("ok") and step.get("name") != "remote-helper-usage"
    ]
    if failed_steps:
        return (
            "v1199-step-failed",
            False,
            f"failed_steps={failed_steps}",
            "inspect V1199 evidence before retry",
        )
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return (
            "v1199-helper-v238-remote-mismatch",
            False,
            f"remote={remote}",
            "deploy helper v238 before V1199 run",
        )
    node = analysis.get("node") or {}
    if not ((node.get("materialize") or {}).get("all_target_nodes_accounted")):
        return (
            "v1199-node-materialization-failed",
            False,
            f"node={node}",
            "repair node materialization before retry",
        )
    if not ((node.get("cleanup") or {}).get("removed_all_created")):
        return (
            "v1199-node-cleanup-review",
            False,
            f"node={node}",
            "cleanup V1199 nodes manually before continuing",
        )
    if not ((node.get("postflight") or {}).get("selftest_fail0")):
        return (
            "v1199-postflight-health-review",
            False,
            f"node={node}",
            "restore native health before continuing",
        )
    helper_data = analysis.get("helper") or {}
    if helper_data.get("forbidden_true"):
        return (
            "v1199-forbidden-action-detected",
            False,
            f"forbidden={helper_data.get('forbidden_true')}",
            "stop and audit helper before retry",
        )
    outer = helper_data.get("outer") or {}
    mhi_obs = helper_data.get("mhi_obs") or {}
    if outer.get("allowed") != "1":
        return (
            "v1199-helper-mode-not-executed",
            False,
            f"outer.allowed={outer.get('allowed')}",
            "fix V1199 helper command before retry",
        )
    if outer.get("reg_req_eng_rc") != "0":
        return (
            "v1199-reg-req-eng-review",
            False,
            f"outer.reg_req_eng_rc={outer.get('reg_req_eng_rc')} "
            f"errno={outer.get('reg_req_eng_errno')}",
            "classify REG_REQ_ENG before retrying MHI observe",
        )
    if mhi_obs.get("begin") != "1":
        return (
            "v1199-mhi-observe-child-not-started",
            False,
            f"mhi_obs={mhi_obs}",
            "fix helper MHI observe child before retry",
        )
    if mhi_obs.get("request_observed") != "1" or mhi_obs.get("wait_value") != "1":
        return (
            "v1199-esoc-req-img-not-observed",
            False,
            f"request_observed={mhi_obs.get('request_observed')} "
            f"wait_value={mhi_obs.get('wait_value')}",
            "inspect eSoC request timing; MDM may not have requested image",
        )
    if mhi_obs.get("img_xfer_sent") != "1":
        return (
            "v1199-img-xfer-done-not-sent",
            False,
            f"img_xfer_rc={mhi_obs.get('img_xfer_rc')}",
            "inspect ESOC_NOTIFY failure before retry",
        )
    # Core question: did MHI devices appear?
    mhi_appeared = mhi_obs.get("mhi_appeared", "")
    total_polls = mhi_obs.get("mhi_total_polls", "?")
    elapsed_ms = mhi_obs.get("elapsed_ms", "?")
    poll_snapshots = helper_data.get("poll_snapshots", [])
    post = analysis.get("post_surface") or {}
    if post.get("actor_hits") or post.get("wifi_link_hits"):
        return (
            "v1199-post-surface-not-clean",
            False,
            f"post={post}",
            "cleanup actor or Wi-Fi surface before continuing",
        )
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return (
            "v1199-reboot-cleanup-review",
            False,
            f"cleanup={cleanup}",
            "verify or rerun recovery reboot before continuing",
        )
    if mhi_appeared == "1":
        appeared_ms = mhi_obs.get("mhi_appeared_at_ms", "?")
        appeared_idx = mhi_obs.get("mhi_appeared_at_index", "?")
        # Report the MHI poll snapshot at appearance time
        snap = poll_snapshots[int(appeared_idx)] if appeared_idx.isdigit() and int(appeared_idx) < len(poll_snapshots) else {}
        return (
            "v1199-mhi-appeared-after-img-xfer-done",
            True,
            (
                f"MHI device appeared at t={appeared_ms}ms after IMG_XFER_DONE "
                f"(poll index {appeared_idx}); "
                f"mhi_bus_count={snap.get('mhi_bus_count','?')} "
                f"mhi_pipe_exists={snap.get('mhi_pipe_exists','?')} "
                f"gpio142={snap.get('gpio142_count','?')}; "
                f"total_polls={total_polls} elapsed={elapsed_ms}ms"
            ),
            "MHI bus is live after IMG_XFER_DONE — investigate ks/firmware-download path",
        )
    # MHI did not appear
    max_gpio = max(
        (int(s.get("gpio142_count", "0")) for s in poll_snapshots if s.get("gpio142_count", "0").isdigit()),
        default=0,
    )
    return (
        "v1199-mhi-not-appeared-after-img-xfer-done",
        True,
        (
            f"IMG_XFER_DONE sent; MHI did not appear after {total_polls} polls "
            f"(elapsed={elapsed_ms}ms); max_gpio142={max_gpio}; "
            f"MDM does not create MHI devices from IMG_XFER_DONE alone without firmware"
        ),
        (
            "MHI appearance requires actual firmware bytes via ks/MHI pipe; "
            "Option A (mdm_helper SELinux context repair) is the next gate"
        ),
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    helper_data = analysis.get("helper") or {}
    outer = helper_data.get("outer") or {}
    mhi_obs = helper_data.get("mhi_obs") or {}
    poll_snapshots = helper_data.get("poll_snapshots") or []

    rows = [
        ["helper_version", DEFAULT_HELPER_MARKER],
        ["mode", MODE],
        ["reg_req_eng_rc", outer.get("reg_req_eng_rc", "")],
        ["subsys_esoc0_open_attempted", outer.get("subsys_esoc0_open_attempted", "")],
        ["wait_request_name", mhi_obs.get("wait_request_name", "")],
        ["request_observed", mhi_obs.get("request_observed", "")],
        ["img_xfer_sent", mhi_obs.get("img_xfer_sent", "")],
        ["img_xfer_elapsed_ms", mhi_obs.get("img_xfer_elapsed_ms", "")],
        ["mhi_appeared", mhi_obs.get("mhi_appeared", "")],
        ["mhi_appeared_at_ms", mhi_obs.get("mhi_appeared_at_ms", "")],
        ["total_polls", mhi_obs.get("mhi_total_polls", "")],
        ["result", mhi_obs.get("result", "")],
        ["elapsed_ms", mhi_obs.get("elapsed_ms", "")],
    ]
    for i, snap in enumerate(poll_snapshots[:15]):
        rows.append([
            f"poll[{i:02d}]",
            f"t={snap.get('elapsed_ms','?')}ms "
            f"mhi_bus={snap.get('mhi_bus_count','?')} "
            f"pipe={snap.get('mhi_pipe_exists','?')} "
            f"gpio142={snap.get('gpio142_count','?')}",
        ])
    lines = [
        "# V1199 ESOC IMG_XFER_DONE + MHI Observe",
        "",
        f"**Decision**: `{manifest.get('decision', '')}`",
        f"**Pass**: `{manifest.get('pass', '')}`",
        f"**Reason**: {manifest.get('reason', '')[:400]}",
        f"**Next**: {manifest.get('next_step', '')}",
        "",
        "## MHI Observe Gate",
        "",
        markdown_table(["key", "value"], rows),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    local = local_helper_info(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    if args.command == "run":
        steps, analysis = execute(args, store)
    decision, passed, reason, next_step = decide(args, local, steps, analysis)
    manifest: dict[str, Any] = {
        "cycle": "v1199",
        "generated_at": now_iso(),
        "command": args.command,
        "helper_version": DEFAULT_HELPER_MARKER,
        "mode": MODE,
        "helper_sha256": DEFAULT_HELPER_SHA256,
        "local_helper": local,
        "steps": steps,
        "analysis": analysis,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
    }
    mhi_obs = (analysis.get("helper") or {}).get("mhi_obs") or {}
    poll_snapshots = (analysis.get("helper") or {}).get("poll_snapshots") or []
    manifest["reg_req_eng_executed"] = (
        (analysis.get("helper") or {}).get("outer", {}).get("reg_req_eng_attempted") == "1"
    )
    manifest["img_xfer_done_sent"] = mhi_obs.get("img_xfer_sent") == "1"
    manifest["boot_done_sent"] = mhi_obs.get("boot_done_attempted") == "1"
    manifest["mhi_appeared"] = mhi_obs.get("mhi_appeared") == "1"
    manifest["mhi_appeared_at_ms"] = mhi_obs.get("mhi_appeared_at_ms", "")
    manifest["total_polls"] = mhi_obs.get("mhi_total_polls", "")
    manifest["max_gpio142"] = max(
        (int(s.get("gpio142_count", "0")) for s in poll_snapshots if s.get("gpio142_count", "0").isdigit()),
        default=0,
    )
    manifest["daemon_start_executed"] = False
    manifest["wifi_bringup_executed"] = False
    manifest["external_ping_executed"] = False
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision                 : {manifest['decision']}")
    print(f"pass                     : {manifest['pass']}")
    print(f"reason                   : {manifest['reason'][:200]}")
    print(f"next                     : {manifest['next_step']}")
    print(f"reg_req_eng_executed     : {manifest['reg_req_eng_executed']}")
    print(f"img_xfer_done_sent       : {manifest['img_xfer_done_sent']}")
    print(f"boot_done_sent           : {manifest['boot_done_sent']}")
    print(f"mhi_appeared             : {manifest['mhi_appeared']}")
    print(f"mhi_appeared_at_ms       : {manifest['mhi_appeared_at_ms']}")
    print(f"total_polls              : {manifest['total_polls']}")
    print(f"max_gpio142              : {manifest['max_gpio142']}")
    print(f"wifi_bringup_executed    : {manifest['wifi_bringup_executed']}")
    print(f"manifest                 : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
