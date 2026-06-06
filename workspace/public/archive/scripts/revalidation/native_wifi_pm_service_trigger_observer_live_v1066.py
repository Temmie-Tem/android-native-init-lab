#!/usr/bin/env python3
"""V1066 bounded PM-service trigger observer live gate.

Runs deployed helper v184 in `wifi-companion-pm-service-trigger-observer`
mode over the authenticated NCM tcpctl channel.  The live gate starts only the
service-manager trio plus PM actors required to observe whether `pm-service` or
`pm_proxy_helper` opens `/dev/subsys_modem`.

Forbidden in this gate: `mdm_helper`, CNSS actors, Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, external ping, eSoC ioctl/open, subsystem trigger,
firmware mutation, partition write, and boot image write.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1066-pm-service-trigger-observer-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1066-pm-service-trigger-observer-live.txt")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1067-execns-helper-v184-build/a90_android_execns_probe")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "e654b4bdde6842e4723a51bc5c6d267827f8d2c6c0271f3dc80b23857edb6d94"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v184"
DEFAULT_MODE = "wifi-companion-pm-service-trigger-observer"
DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v535/dev/__properties__"
DEFAULT_REAL_LD_CONFIG = "/cache/bin/a90_real_ld.config.txt"
DEFAULT_REAL_APEX_LIBRARIES = "/cache/bin/a90_real_apex.libraries.config.txt"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_DEVICE_IP = "192.168.7.2"
DEFAULT_TCP_PORT = 2325
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"

KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
SECRET_RE = re.compile(r"(made by|creator: made by) [^\r\n]+", re.IGNORECASE)
ACTOR_RE = re.compile(
    r"\b(pm_proxy_helper|pm-service|pm-proxy|mdm_helper|/vendor/bin/ks|"
    r"servicemanager|hwservicemanager|vndservicemanager|cnss_diag|cnss-daemon|"
    r"wificond|supplicant|hostapd|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b"
)
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)
FORBIDDEN_TRUE_KEYS = (
    "pm_service_trigger_observer.mdm_helper_start_executed",
    "pm_service_trigger_observer.cnss_daemon_start_executed",
    "pm_service_trigger_observer.wifi_hal_start_executed",
    "pm_service_trigger_observer.scan_connect_linkup",
    "pm_service_trigger_observer.external_ping",
    "pm_service_trigger_observer.subsys_esoc0_open_attempted",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def redact(text: str) -> str:
    return SECRET_RE.sub(r"\1 [redacted]", text)


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def run_host(store: EvidenceStore, name: str, command: list[str], timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        output = redact(result.stdout)
        rc = result.returncode
    except subprocess.TimeoutExpired as exc:
        output = redact((exc.stdout or "") + "\n[TIMEOUT]\n")
        rc = -1
    rel = f"host/{safe_name(name)}.txt"
    store.write_text(rel, output.rstrip() + "\n")
    return {
        "name": name,
        "command": " ".join(command[:8]) + (" ..." if len(command) > 8 else ""),
        "rc": rc,
        "ok": rc == 0,
        "duration_sec": round(time.monotonic() - started, 3),
        "file": rel,
        "payload": output[:8192] + ("\n[truncated]\n" if len(output) > 8192 else ""),
    }


def run_a90ctl(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    command: list[str],
    timeout: float,
    allow_error: bool = False,
) -> dict[str, Any]:
    argv = [
        sys.executable,
        str(repo_path("scripts/revalidation/a90ctl.py")),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(timeout),
    ]
    if allow_error:
        argv.append("--allow-error")
    argv.extend(command)
    step = run_host(store, name, argv, timeout + 4.0)
    steps.append(step)
    return step


def run_tcpctl(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    run_args: list[str],
    timeout: float,
) -> dict[str, Any]:
    argv = [
        sys.executable,
        str(repo_path("scripts/revalidation/tcpctl_host.py")),
        "--device-ip",
        args.device_ip,
        "--tcp-port",
        str(args.tcp_port),
        "--tcp-timeout",
        str(args.tcp_timeout),
        "run",
    ]
    argv.extend(run_args)
    step = run_host(store, name, argv, timeout)
    steps.append(step)
    return step


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
    info["mode"] = DEFAULT_MODE in strings
    return info


def helper_command(args: argparse.Namespace) -> list[str]:
    return [
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
        DEFAULT_MODE,
        "--allow-pm-service-trigger-observer",
        "--timeout-sec",
        str(min(max(args.helper_timeout_sec, 4), 30)),
        "--property-root",
        args.property_root,
        "--null-device-mode",
        "dev-null",
        "--android-selinux-context-mode",
        "service-defaults",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        DEFAULT_REAL_LD_CONFIG,
        "--apex-libraries-source",
        DEFAULT_REAL_APEX_LIBRARIES,
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
    ]


def remote_helper_state(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    sha = run_tcpctl(args, store, steps, "remote-helper-sha", [args.toybox, "sha256sum", args.helper], timeout=20.0)
    usage = run_tcpctl(args, store, steps, "remote-helper-usage", [args.helper], timeout=20.0)
    sha_text = (store.run_dir / sha["file"]).read_text(encoding="utf-8", errors="replace")
    usage_text = (store.run_dir / usage["file"]).read_text(encoding="utf-8", errors="replace")
    return {
        "sha_ok": args.helper_sha256 in sha_text,
        "marker_ok": args.helper_marker in usage_text,
        "mode_ok": DEFAULT_MODE in usage_text,
        "sha_file": sha["file"],
        "usage_file": usage["file"],
    }


def helper_surface(text: str) -> dict[str, Any]:
    keys = parse_keys(text)
    prefix = "pm_service_trigger_observer"
    contract = {
        key[len(prefix) + 1:]: value
        for key, value in keys.items()
        if key.startswith(prefix + ".")
    }
    return {
        "contract": contract,
        "execns": {
            "stdout_truncated": "A90_EXECNS_STDOUT_END truncated=1" in text,
            "rc0": "A90_EXECNS_END rc=0" in text,
            "outer_signal9": "[signal 9]" in text or "ERR signal=9" in text,
        },
        "node_status": {
            key: value
            for key, value in keys.items()
            if key.startswith("android_node.")
        },
        "property_service_shim": {
            key: value
            for key, value in keys.items()
            if key.startswith("wifi_hal_composite_start.property_service_shim.")
        },
        "forbidden_true": {key: keys.get(key) for key in FORBIDDEN_TRUE_KEYS if keys.get(key) not in (None, "0")},
    }


def shell_script(args: argparse.Namespace, script: str) -> list[str]:
    return [args.busybox, "sh", "-c", script.replace("$BB", args.busybox).replace("$TB", args.toybox)]


def selinuxfs_probe_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        *shell_script(
            args,
            (
                "echo filesystems; "
                "$BB cat /proc/filesystems 2>/dev/null | $BB grep -i selinux || true; "
                "echo mounts; "
                "$BB cat /proc/mounts 2>/dev/null | $BB grep -i selinux || true; "
                "echo status; "
                "$BB ls -l /sys/fs/selinux/status 2>&1 || true"
            ),
        ),
    ]


def selinuxfs_mount_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        *shell_script(
            args,
            (
                "$BB mkdir -p /sys/fs/selinux; "
                "if $BB test ! -e /sys/fs/selinux/status; then "
                "$BB mount -t selinuxfs selinuxfs /sys/fs/selinux; "
                "fi; "
                "$BB ls -l /sys/fs/selinux/status /sys/fs/selinux/enforce 2>&1"
            ),
        ),
    ]


def selinuxfs_umount_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        *shell_script(
            args,
            (
                "if $BB cat /proc/mounts 2>/dev/null | $BB grep -q ' /sys/fs/selinux '; then "
                "$BB umount /sys/fs/selinux; "
                "fi; "
                "$BB cat /proc/mounts 2>/dev/null | $BB grep -i selinux || true"
            ),
        ),
    ]


def post_surface(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    ps = run_tcpctl(args, store, steps, "post-ps", [args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], timeout=25.0)
    net = run_tcpctl(args, store, steps, "post-proc-net-dev", [args.toybox, "cat", "/proc/net/dev"], timeout=20.0)
    subsys = run_tcpctl(
        args,
        store,
        steps,
        "post-subsys-state",
        [args.toybox, "cat", "/sys/bus/msm_subsys/devices/subsys9/state"],
        timeout=20.0,
    )
    dmesg = run_tcpctl(
        args,
        store,
        steps,
        "post-dmesg-wifi-esoc-tail",
        [args.busybox, "dmesg"],
        timeout=25.0,
    )
    ps_text = (store.run_dir / ps["file"]).read_text(encoding="utf-8", errors="replace")
    net_text = (store.run_dir / net["file"]).read_text(encoding="utf-8", errors="replace")
    subsys_text = (store.run_dir / subsys["file"]).read_text(encoding="utf-8", errors="replace")
    dmesg_text = (store.run_dir / dmesg["file"]).read_text(encoding="utf-8", errors="replace")
    actor_lines = [line.strip() for line in ps_text.splitlines() if ACTOR_RE.search(line)]
    return {
        "actor_hits": actor_lines[:20],
        "pm_actor_hits": [
            line
            for line in actor_lines
            if "pm_proxy_helper" in line or "pm-service" in line or "pm-proxy" in line
        ][:12],
        "forbidden_actor_hits": [
            line
            for line in actor_lines
            if "mdm_helper" in line or "cnss" in line or "wificond" in line or "wifi@" in line
        ][:12],
        "wifi_link_hits": [line.strip() for line in net_text.splitlines() if WIFI_RE.search(line)][:16],
        "helper_process_hits": [line.strip() for line in ps_text.splitlines() if "a90_android_execns_probe" in line][:16],
        "subsys_state_tail": subsys_text.splitlines()[-32:],
        "wlfw_or_wlan_dmesg_hits": [
            line.strip()
            for line in dmesg_text.splitlines()
            if re.search(r"wlfw|wlan0|bdf|qcwlan|icnss|cnss", line, re.IGNORECASE)
        ][-40:],
    }


def reboot_cleanup(args: argparse.Namespace, store: EvidenceStore, reason: str) -> dict[str, Any]:
    cleanup: dict[str, Any] = {
        "requested": True,
        "reason": reason,
        "reboot": None,
        "attempts": [],
        "healthy": False,
    }
    cleanup["reboot"] = run_host(
        store,
        "cleanup-reboot-command",
        [
            sys.executable,
            str(repo_path("scripts/revalidation/a90ctl.py")),
            "--host",
            args.host,
            "--port",
            str(args.port),
            "--timeout",
            "3",
            "--allow-error",
            "--retry-unsafe",
            "reboot",
        ],
        timeout=8.0,
    )
    for attempt in range(1, 31):
        time.sleep(2.0)
        boot = run_host(
            store,
            f"cleanup-post-bootstatus-{attempt:02d}",
            [
                sys.executable,
                str(repo_path("scripts/revalidation/a90ctl.py")),
                "--host",
                args.host,
                "--port",
                str(args.port),
                "--timeout",
                "7",
                "bootstatus",
            ],
            timeout=10.0,
        )
        selftest = run_host(
            store,
            f"cleanup-post-selftest-{attempt:02d}",
            [
                sys.executable,
                str(repo_path("scripts/revalidation/a90ctl.py")),
                "--host",
                args.host,
                "--port",
                str(args.port),
                "--timeout",
                "7",
                "selftest",
            ],
            timeout=10.0,
        )
        boot_ok = boot["ok"] and ("BOOT OK" in boot["payload"] or "status=ok" in boot["payload"])
        selftest_ok = selftest["ok"] and "fail=0" in selftest["payload"]
        cleanup["attempts"].append({
            "attempt": attempt,
            "boot_file": boot["file"],
            "selftest_file": selftest["file"],
            "boot_ok": boot_ok,
            "selftest_ok": selftest_ok,
        })
        if boot_ok and selftest_ok:
            cleanup["healthy"] = True
            break
    return cleanup


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    for flag, enabled in (
        ("--allow-mountsystem-ro", args.allow_mountsystem_ro),
        ("--allow-selinuxfs-mount", args.allow_selinuxfs_mount),
        ("--allow-pm-service-trigger-observer", args.allow_pm_service_trigger_observer),
        ("--allow-cleanup-reboot", args.allow_cleanup_reboot),
        ("--assume-yes", args.assume_yes),
    ):
        if not enabled:
            missing.append(flag)
    return missing


def execute(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    run_a90ctl(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    run_a90ctl(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    run_a90ctl(args, store, steps, "pre-netservice-status", ["netservice", "status"], timeout=12.0)
    if args.allow_mountsystem_ro:
        run_a90ctl(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    run_a90ctl(args, store, steps, "pre-selinuxfs-state", selinuxfs_probe_command(args), timeout=12.0, allow_error=True)
    if args.allow_selinuxfs_mount:
        run_a90ctl(args, store, steps, "mount-selinuxfs", selinuxfs_mount_command(args), timeout=12.0, allow_error=True)
    run_a90ctl(args, store, steps, "property-root-stat", ["stat", args.property_root], timeout=12.0, allow_error=True)
    run_a90ctl(args, store, steps, "real-ld-config-stat", ["stat", DEFAULT_REAL_LD_CONFIG], timeout=12.0, allow_error=True)
    run_a90ctl(args, store, steps, "real-apex-libraries-stat", ["stat", DEFAULT_REAL_APEX_LIBRARIES], timeout=12.0, allow_error=True)
    analysis["remote_helper"] = remote_helper_state(args, store, steps)
    helper_step = run_tcpctl(
        args,
        store,
        steps,
        "pm-service-trigger-observer",
        helper_command(args),
        timeout=args.toybox_timeout_sec + 45.0,
    )
    helper_text = (store.run_dir / helper_step["file"]).read_text(encoding="utf-8", errors="replace")
    analysis["helper"] = helper_surface(helper_text)
    run_a90ctl(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    run_a90ctl(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)
    analysis["post_surface"] = post_surface(args, store, steps)
    if args.allow_selinuxfs_mount:
        analysis["selinuxfs_umount"] = run_a90ctl(
            args,
            store,
            steps,
            "umount-selinuxfs",
            selinuxfs_umount_command(args),
            timeout=12.0,
            allow_error=True,
        )
    contract = (analysis.get("helper") or {}).get("contract") or {}
    post = analysis.get("post_surface") or {}
    cleanup_needed = (
        contract.get("result") == "observer-reboot-required"
        or contract.get("all_postflight_safe") == "0"
        or bool(post.get("helper_process_hits"))
        or bool(post.get("pm_actor_hits"))
    )
    analysis["cleanup_needed"] = cleanup_needed
    if cleanup_needed and args.allow_cleanup_reboot:
        analysis["reboot_cleanup"] = reboot_cleanup(args, store, "PM observer actor not proven stopped")
    elif cleanup_needed:
        analysis["reboot_cleanup"] = {
            "requested": False,
            "reason": "cleanup needed but --allow-cleanup-reboot not set",
            "healthy": False,
        }
    else:
        analysis["reboot_cleanup"] = {"requested": False, "reason": "not needed", "healthy": True}
    return steps, analysis


def step_failures(steps: list[dict[str, Any]], helper: dict[str, Any]) -> list[str]:
    contract = helper.get("contract") or {}
    helper_has_evidence = contract.get("begin") == "1" and contract.get("end") == "1"
    ignored = {"remote-helper-usage"}
    if helper_has_evidence:
        ignored.add("pm-service-trigger-observer")
    return [step["name"] for step in steps if not step.get("ok") and step["name"] not in ignored]


def decide(
    args: argparse.Namespace,
    local: dict[str, Any],
    steps: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v1066-plan-helper-v184-missing", False, f"local={local}", "build/deploy helper v184 before V1066"
        return "v1066-pm-service-trigger-observer-plan-ready", True, "plan-only; no device command executed", "run bounded V1066 observer live gate"
    missing = required_flags(args)
    if missing:
        return "v1066-pm-service-trigger-observer-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V1066 flags"
    helper = analysis.get("helper") or {}
    failed_steps = step_failures(steps, helper)
    if failed_steps:
        return "v1066-step-failed", False, f"failed_steps={failed_steps}", "inspect V1066 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v1066-helper-v184-remote-mismatch", False, f"remote={remote}", "redeploy helper v184 before V1066"
    if helper.get("forbidden_true"):
        return "v1066-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    contract = helper.get("contract") or {}
    execns = helper.get("execns") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v1066-helper-mode-not-executed", False, f"contract={contract}", "fix V1066 helper command before retry"
    if contract.get("service_manager_start_executed") != "1" or contract.get("pm_proxy_helper_start_executed") != "1":
        return "v1066-observer-actors-not-started", False, f"contract={contract}", "repair observer child launch order"
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v1066-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify cleanup before continuing"
    result = contract.get("result")
    if result == "pm-service-subsys-modem-observed":
        return (
            "v1066-pm-service-subsys-modem-observed",
            True,
            f"per_mgr_seen={contract.get('per_mgr_subsys_modem_seen')} pm_proxy_helper_seen={contract.get('pm_proxy_helper_subsys_modem_seen')}",
            "classify post-PM-fd WLFW/MDM3 path before Wi-Fi HAL or scan/connect",
        )
    if result == "pm-service-idle-input-gap-observed":
        return (
            "v1066-pm-service-idle-input-gap-observed",
            True,
            f"snapshot_count={contract.get('snapshot_count')} timed_out={contract.get('timed_out')}",
            "classify missing Android runtime input/property/binder trigger before retry",
        )
    if result == "observer-runtime-gap":
        return (
            "v1066-observer-runtime-gap-clean",
            True,
            f"all_observable={contract.get('all_observable')} all_postflight_safe={contract.get('all_postflight_safe')}",
            "inspect child exit details and repair observer runtime contract",
        )
    if contract.get("end") != "1" and execns.get("outer_signal9"):
        return (
            "v1066-observer-runtime-gap-timeout-clean",
            True,
            (
                "observer entered but did not reach final result before outer timeout; "
                f"per_mgr_exit={contract.get('poll_01.per_mgr_subsys_modem_count')} "
                f"pm_proxy_helper_fd={contract.get('poll_01.pm_proxy_helper_subsys_modem_count')}"
            ),
            "classify pm-service exit and pm_proxy_helper D-state before retrying wider PM input",
        )
    if result == "observer-reboot-required":
        return (
            "v1066-observer-reboot-required-cleaned",
            True,
            f"all_postflight_safe={contract.get('all_postflight_safe')}",
            "inspect pre-reboot evidence before continuing",
        )
    return "v1066-pm-service-trigger-observer-review", False, f"contract={contract}", "inspect V1066 helper output before continuing"


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["ok"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V1066 PM-Service Trigger Observer Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: `{manifest['next_step']}`",
        f"- helper_marker: `{manifest['helper_marker']}`",
        f"- helper_sha256: `{manifest['helper_sha256']}`",
        f"- pm_service_subsys_modem_seen: `{manifest['pm_service_subsys_modem_seen']}`",
        f"- pm_proxy_helper_subsys_modem_seen: `{manifest['pm_proxy_helper_subsys_modem_seen']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- mdm_helper_start_executed: `{manifest['mdm_helper_start_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- subsys_esoc0_open_attempted: `{manifest['subsys_esoc0_open_attempted']}`",
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
        markdown_table(["name", "ok", "rc", "duration_sec", "file"], step_rows),
        "",
        "## Guardrails",
        "",
        "- Permits only selinuxfs mount/cleanup, private property shim, service-manager trio, `pm_proxy_helper`, `pm-service`, and `pm-proxy`.",
        "- Forbids `mdm_helper`, CNSS actors, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, eSoC ioctl/open, and subsystem trigger.",
        "- No module load/unload, boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write, or Wi-Fi link-up.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    local = local_helper_info(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    if args.command == "run" and not required_flags(args):
        steps, analysis = execute(args, store)
    decision, pass_ok, reason, next_step = decide(args, local, steps, analysis)
    helper = analysis.get("helper") or {}
    contract = helper.get("contract") or {}
    cleanup = analysis.get("reboot_cleanup") or {}
    return {
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
        "mode": DEFAULT_MODE,
        "property_root": args.property_root,
        "helper_timeout_sec": args.helper_timeout_sec,
        "toybox_timeout_sec": args.toybox_timeout_sec,
        "steps": steps,
        "analysis": analysis,
        "service_manager_start_executed": contract.get("service_manager_start_executed") == "1",
        "pm_proxy_helper_start_executed": contract.get("pm_proxy_helper_start_executed") == "1",
        "pm_service_start_executed": contract.get("per_mgr_start_executed") == "1",
        "pm_proxy_start_executed": contract.get("per_proxy_start_executed") == "1",
        "pm_service_subsys_modem_seen": contract.get("per_mgr_subsys_modem_seen") == "1",
        "pm_proxy_helper_subsys_modem_seen": contract.get("pm_proxy_helper_subsys_modem_seen") == "1",
        "mdm_helper_start_executed": contract.get("mdm_helper_start_executed") == "1",
        "cnss_daemon_start_executed": contract.get("cnss_daemon_start_executed") == "1",
        "subsys_esoc0_open_attempted": contract.get("subsys_esoc0_open_attempted") == "1",
        "cleanup_reboot_executed": bool(cleanup.get("requested")),
        "wifi_hal_start_executed": contract.get("wifi_hal_start_executed") == "1",
        "scan_connect_executed": contract.get("scan_connect_linkup") == "1",
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": contract.get("external_ping") == "1",
        "wifi_bringup_executed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--tcp-port", type=int, default=DEFAULT_TCP_PORT)
    parser.add_argument("--tcp-timeout", type=float, default=60.0)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--property-root", default=DEFAULT_PROPERTY_ROOT)
    parser.add_argument("--helper-timeout-sec", type=int, default=4)
    parser.add_argument("--toybox-timeout-sec", type=int, default=18)
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-pm-service-trigger-observer", action="store_true")
    parser.add_argument("--allow-cleanup-reboot", action="store_true")
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
    print(f"pm_service_subsys_modem_seen: {manifest['pm_service_subsys_modem_seen']}")
    print(f"pm_proxy_helper_subsys_modem_seen: {manifest['pm_proxy_helper_subsys_modem_seen']}")
    print(f"mdm_helper_start_executed: {manifest['mdm_helper_start_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"subsys_esoc0_open_attempted: {manifest['subsys_esoc0_open_attempted']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
