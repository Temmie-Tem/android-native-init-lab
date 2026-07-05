#!/usr/bin/env python3
"""WSTA233 attended cold-boot persistence smoke measurement.

This runner performs the single persistence measurement requested by the
2026-07-05 server-distro close-out charter:

  * capture a pre-cold-boot native/service baseline;
  * wait for an attended physical USB serial disconnect/reconnect;
  * capture the same post-cold-boot baseline and classify what persisted;
  * optionally roll boot back to v2321 through the checked flash helper.

It is not a service scaffold or productization unit.  Default execution is
fail-closed and host-only; live phases require explicit flags.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = SCRIPT_DIR.parent / "revalidation"
DEFAULT_RUN_BASE = REPO_ROOT / "workspace/private/runs/server-distro"
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_SERIAL_PATH = Path("/dev/serial/by-id/usb-A90-LNX_A90_Linux_ARM64_A90NATIVE001-if00")
DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 54321
DEFAULT_TCPCTL_PORT = 2325
DEFAULT_ADMIN_SSH_PORT = 2222
DEFAULT_SMOKE_PORT = 8080
ROLLBACK_IMAGE = (
    REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img"
)
ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
DEEP_FALLBACK_IMAGE = (
    REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img"
)
DEEP_FALLBACK_SHA256 = "b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f"
FINAL_FALLBACK_IMAGE = REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_v48.img"
NATIVE_FLASH = REVAL_DIR / "native_init_flash.py"
RESULT_NAME = "wsta233_result.json"
SUMMARY_NAME = "wsta233_private_summary.json"
PASS_DECISION = "wsta233-cold-boot-persistence-smoke-live-pass"
PREBASELINE_DECISION = "wsta233-cold-boot-persistence-prebaseline-pass"
POST_CLASSIFIED_DECISION = "wsta233-cold-boot-persistence-post-classified-rollback-required"


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def resolve_path(path: Path | str) -> Path:
    path_obj = path if isinstance(path, Path) else Path(path)
    return path_obj if path_obj.is_absolute() else REPO_ROOT / path_obj


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def summary_path(run_dir: Path) -> Path:
    return run_dir / SUMMARY_NAME


def result_path(run_dir: Path) -> Path:
    return run_dir / RESULT_NAME


def ensure_private_run_dir(path: Path) -> tuple[bool, str]:
    if not is_under(path, PRIVATE_ROOT):
        return False, "wsta233-blocked-nonprivate-run-dir"
    return True, "ok"


def append_event(summary: dict[str, Any], name: str) -> None:
    summary.setdefault("events", []).append({"name": name, "timestamp_utc": utc_iso()})


def save_summary(run_dir: Path, summary: dict[str, Any]) -> None:
    write_json(summary_path(run_dir), summary)


def command_record(run_dir: Path, phase: str, name: str, command: list[str], timeout: float) -> dict[str, Any]:
    started = utc_iso()
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    record = {
        "name": name,
        "phase": phase,
        "command": command,
        "started_utc": started,
        "ended_utc": utc_iso(),
        "returncode": completed.returncode,
        "output": completed.stdout,
    }
    write_json(run_dir / f"{phase}-{name}.json", record)
    return record


def a90ctl_json_command(args: argparse.Namespace, command: list[str]) -> list[str]:
    return [
        sys.executable,
        str(REVAL_DIR / "a90ctl.py"),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--json",
        *command,
    ]


def bridge_status_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(REVAL_DIR / "a90_bridge.py"),
        "status",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--json",
    ]


def restart_bridge_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(REVAL_DIR / "a90_bridge.py"),
        "restart",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--discovered",
        "--allow-device-change",
        "--wait-timeout",
        str(args.bridge_wait_timeout),
    ]


def a90ctl_text(record: dict[str, Any]) -> str:
    try:
        payload = json.loads(str(record.get("output", "")))
    except json.JSONDecodeError:
        return str(record.get("output", ""))
    return str(payload.get("text", ""))


def first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1) if match else None


def parse_uptime(status_text: str) -> float | None:
    value = first_match(r"uptime:\s+([0-9.]+)s", status_text)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def port_probe(run_dir: Path, phase: str, name: str, host: str, port: int, timeout: float) -> dict[str, Any]:
    started = utc_iso()
    reachable = False
    error_type = ""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            reachable = True
    except Exception as exc:  # noqa: BLE001 - probe result is diagnostic
        error_type = type(exc).__name__
    record = {
        "name": name,
        "phase": phase,
        "started_utc": started,
        "ended_utc": utc_iso(),
        "reachable": reachable,
        "error_type": error_type,
        "host_redacted": True,
        "port": port,
    }
    write_json(run_dir / f"{phase}-port-{name}.json", record)
    return record


def compact_from_records(records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    version_text = a90ctl_text(records.get("version", {}))
    selftest_text = a90ctl_text(records.get("selftest", {}))
    status_text = a90ctl_text(records.get("status", {}))
    runtime_text = a90ctl_text(records.get("runtime", {}))
    service_text = a90ctl_text(records.get("service-status", {}))
    netservice_text = a90ctl_text(records.get("netservice-status", {}))
    rshell_text = a90ctl_text(records.get("rshell-status", {}))
    return {
        "native_version": first_match(r"version:\s+([^\r\n]+)", version_text),
        "selftest_fail_zero": "fail=0" in selftest_text,
        "boot_ok": "boot: BOOT OK" in status_text,
        "uptime_sec": parse_uptime(status_text),
        "runtime_sd_writable": "backend=sd" in runtime_text and "writable=yes" in runtime_text,
        "autohud_running": "service: autohud" in service_text and "running=yes" in service_text,
        "tcpctl_running": "tcpctl=running" in netservice_text
        or ("service: tcpctl" in service_text and "running=yes" in service_text),
        "rshell_running": "rshell: enabled=yes running=yes" in rshell_text,
        "tcpctl_port_reachable": records.get("port-tcpctl", {}).get("reachable") is True,
        "admin_ssh_port_reachable": records.get("port-admin-ssh", {}).get("reachable") is True,
        "loopback_smoke_port_reachable": records.get("port-loopback-smoke", {}).get("reachable") is True,
    }


def capture_phase(args: argparse.Namespace, run_dir: Path, phase: str) -> dict[str, Any]:
    records: dict[str, dict[str, Any]] = {}
    records["bridge-status"] = command_record(
        run_dir, phase, "bridge-status", bridge_status_command(args), args.timeout
    )
    for name, command in (
        ("version", ["version"]),
        ("selftest", ["selftest"]),
        ("status", ["status"]),
        ("runtime", ["runtime"]),
        ("service-status", ["service", "status"]),
        ("netservice-status", ["netservice", "status"]),
        ("rshell-status", ["rshell", "status"]),
    ):
        records[name] = command_record(run_dir, phase, name, a90ctl_json_command(args, command), args.timeout + 5.0)
    records["port-tcpctl"] = port_probe(
        run_dir, phase, "tcpctl", args.device_ncm_host, args.tcpctl_port, args.port_probe_timeout
    )
    records["port-admin-ssh"] = port_probe(
        run_dir, phase, "admin-ssh", args.device_ncm_host, args.admin_ssh_port, args.port_probe_timeout
    )
    records["port-loopback-smoke"] = port_probe(
        run_dir, phase, "loopback-smoke", args.device_ncm_host, args.smoke_port, args.port_probe_timeout
    )
    return {
        "records": {
            name: {
                "returncode": record.get("returncode"),
                "reachable": record.get("reachable"),
            }
            for name, record in records.items()
        },
        "compact_redacted": compact_from_records(records),
    }


def monitor_serial(args: argparse.Namespace, run_dir: Path, summary: dict[str, Any]) -> dict[str, Any]:
    serial_path = args.serial_path
    monitor = {
        "serial_path": str(serial_path),
        "started_utc": utc_iso(),
        "disconnect_seen": False,
        "reconnect_seen": False,
        "timeout": False,
    }
    summary["cold_boot_monitor"] = monitor
    append_event(summary, "operator_cold_boot_wait_start")
    save_summary(run_dir, summary)
    deadline = time.monotonic() + args.wait_timeout
    while time.monotonic() < deadline:
        exists = serial_path.exists()
        if not monitor["disconnect_seen"] and not exists:
            monitor["disconnect_seen"] = True
            monitor["disconnect_utc"] = utc_iso()
            append_event(summary, "serial_disconnect_seen")
            save_summary(run_dir, summary)
        if monitor["disconnect_seen"] and exists:
            stable_start = time.monotonic()
            while time.monotonic() - stable_start < args.reconnect_stable_sec:
                if not serial_path.exists():
                    stable_start = time.monotonic()
                time.sleep(0.25)
            monitor["reconnect_seen"] = True
            monitor["reconnect_utc"] = utc_iso()
            monitor["ended_utc"] = utc_iso()
            append_event(summary, "serial_reconnect_stable")
            save_summary(run_dir, summary)
            return monitor
        time.sleep(args.poll_sec)
    monitor["timeout"] = True
    monitor["ended_utc"] = utc_iso()
    append_event(summary, "operator_cold_boot_wait_timeout")
    save_summary(run_dir, summary)
    return monitor


def cold_boot_evidence(pre: dict[str, Any], post: dict[str, Any], monitor: dict[str, Any]) -> dict[str, Any]:
    pre_uptime = pre.get("uptime_sec")
    post_uptime = post.get("uptime_sec")
    uptime_drop = isinstance(pre_uptime, (int, float)) and isinstance(post_uptime, (int, float)) and post_uptime < pre_uptime
    serial_cycle = monitor.get("disconnect_seen") is True and monitor.get("reconnect_seen") is True
    return {
        "serial_disconnect_reconnect": serial_cycle,
        "uptime_drop": uptime_drop,
        "cold_boot_evidence": bool(serial_cycle or uptime_drop),
        "pre_uptime_sec": pre_uptime,
        "post_uptime_sec": post_uptime,
    }


def classify_persistence(pre: dict[str, Any], post: dict[str, Any], monitor: dict[str, Any]) -> dict[str, Any]:
    evidence = cold_boot_evidence(pre, post, monitor)
    native_pid1 = bool(post.get("boot_ok") and post.get("selftest_fail_zero"))
    sd_runtime = bool(post.get("runtime_sd_writable"))
    native_control = bool(post.get("tcpctl_running") and post.get("tcpctl_port_reachable"))
    admin_auto = bool(post.get("admin_ssh_port_reachable"))
    smoke_auto = bool(post.get("loopback_smoke_port_reachable"))
    if not evidence["cold_boot_evidence"]:
        gap = "cold-boot-evidence-missing"
    elif native_pid1 and sd_runtime and native_control and not admin_auto and not smoke_auto:
        gap = "native-pid1-and-usb-control-persisted-debian-admin-services-manual-rebringup-required"
    elif native_pid1 and sd_runtime and native_control and (admin_auto or smoke_auto):
        gap = "native-and-some-debian-services-persisted"
    else:
        gap = "native-pid1-or-control-plane-persistence-failed"
    return {
        **evidence,
        "native_pid1_returned": native_pid1,
        "sd_runtime_persisted": sd_runtime,
        "native_control_plane_persisted": native_control,
        "admin_ssh_auto_started": admin_auto,
        "loopback_smoke_auto_started": smoke_auto,
        "admin_ssh_was_running_pre": bool(pre.get("admin_ssh_port_reachable")),
        "loopback_smoke_was_running_pre": bool(pre.get("loopback_smoke_port_reachable")),
        "gap_classification": gap,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def checked_rollback_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(NATIVE_FLASH),
        "--from-native",
        "--verify-protocol",
        "selftest",
        "--bridge-host",
        args.host,
        "--bridge-port",
        str(args.port),
        "--bridge-timeout",
        str(args.rollback_bridge_timeout),
        "--expect-sha256",
        ROLLBACK_SHA256,
        "--expect-readback-sha256",
        ROLLBACK_SHA256,
        str(ROLLBACK_IMAGE),
    ]


def rollback_preflight() -> dict[str, Any]:
    return {
        "rollback_image_present": ROLLBACK_IMAGE.is_file(),
        "rollback_sha256": ROLLBACK_SHA256,
        "deep_fallback_present": DEEP_FALLBACK_IMAGE.is_file(),
        "deep_fallback_sha256": DEEP_FALLBACK_SHA256,
        "final_fallback_present": FINAL_FALLBACK_IMAGE.is_file(),
        "checked_flash_helper_present": NATIVE_FLASH.is_file(),
    }


def safety_flags(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "device_action": bool(
            args.capture_pre_baseline
            or args.wait_serial_cold_boot
            or args.capture_post_classify
            or args.rollback_v2321
        ),
        "boot_flash": bool(args.rollback_v2321 and args.ack_rollback_to_v2321),
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "packet_filter_mutation": False,
        "userdata_touch": False,
        "rootfs_mutation": False,
        "switch_root": False,
        "lsm_profile_load": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "pre_compact_redacted": result.get("pre_compact_redacted"),
        "post_compact_redacted": result.get("post_compact_redacted"),
        "classification": result.get("classification"),
        "rollback": result.get("rollback_summary"),
        "safety": result.get("safety", {}),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    run_id = args.run_id or f"wsta233-cold-boot-persistence-smoke-{utc_stamp()}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    private_ok, private_decision = ensure_private_run_dir(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA233 attended cold-boot persistence smoke measurement",
        "started_utc": utc_iso(),
        "run_dir": rel(run_dir),
        "decision": "wsta233-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(args),
    }
    if not private_ok:
        result["decision"] = private_decision
        result["gate_decision"] = private_decision
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    if not any((args.capture_pre_baseline, args.wait_serial_cold_boot, args.capture_post_classify, args.rollback_v2321)):
        result["decision"] = "wsta233-blocked-explicit-phase-required"
        result["gate_decision"] = result["decision"]
        write_json(result_path(run_dir), result)
        return result

    summary = load_json(summary_path(run_dir)) if summary_path(run_dir).is_file() else {
        "scope": "WSTA233 cold-boot persistence smoke private evidence",
        "run_dir": rel(run_dir),
        "events": [],
    }

    if args.capture_pre_baseline:
        append_event(summary, "pre_baseline_start")
        pre = capture_phase(args, run_dir, "pre")
        summary["pre"] = pre["records"]
        summary["pre_compact_redacted"] = pre["compact_redacted"]
        append_event(summary, "pre_baseline_done")
        result["pre_compact_redacted"] = pre["compact_redacted"]
        result["decision"] = PREBASELINE_DECISION
        result["gate_decision"] = "ok"
        save_summary(run_dir, summary)

    if args.wait_serial_cold_boot:
        monitor = monitor_serial(args, run_dir, summary)
        result["cold_boot_monitor"] = monitor
        if not (monitor.get("disconnect_seen") and monitor.get("reconnect_seen")):
            result["decision"] = "wsta233-blocked-cold-boot-disconnect-not-seen"
            result["gate_decision"] = result["decision"]
            write_json(result_path(run_dir), result)
            return result

    if args.capture_post_classify:
        if "pre_compact_redacted" not in summary:
            result["decision"] = "wsta233-blocked-pre-baseline-required"
            result["gate_decision"] = result["decision"]
            write_json(result_path(run_dir), result)
            return result
        command_record(run_dir, "post", "bridge-restart", restart_bridge_command(args), args.bridge_wait_timeout + 5.0)
        append_event(summary, "post_baseline_start")
        post = capture_phase(args, run_dir, "post")
        summary["post"] = post["records"]
        summary["post_compact_redacted"] = post["compact_redacted"]
        classification = classify_persistence(
            summary["pre_compact_redacted"],
            summary["post_compact_redacted"],
            summary.get("cold_boot_monitor", {}),
        )
        summary["classification"] = classification
        append_event(summary, "post_baseline_done")
        result["pre_compact_redacted"] = summary["pre_compact_redacted"]
        result["post_compact_redacted"] = summary["post_compact_redacted"]
        result["classification"] = classification
        result["decision"] = (
            POST_CLASSIFIED_DECISION
            if classification["cold_boot_evidence"]
            else "wsta233-blocked-cold-boot-evidence-missing"
        )
        result["gate_decision"] = "ok" if classification["cold_boot_evidence"] else result["decision"]
        save_summary(run_dir, summary)
        if not classification["cold_boot_evidence"]:
            write_json(result_path(run_dir), result)
            return result

    if args.rollback_v2321:
        preflight = rollback_preflight()
        result["rollback_preflight"] = preflight
        if not args.ack_rollback_to_v2321:
            result["decision"] = "wsta233-blocked-explicit-v2321-rollback-ack-required"
            result["gate_decision"] = result["decision"]
            write_json(result_path(run_dir), result)
            return result
        if not all(preflight[key] for key in ("rollback_image_present", "deep_fallback_present", "final_fallback_present", "checked_flash_helper_present")):
            result["decision"] = "wsta233-blocked-rollback-preflight-failed"
            result["gate_decision"] = result["decision"]
            write_json(result_path(run_dir), result)
            return result
        rollback = command_record(
            run_dir,
            "rollback",
            "v2321-checked-helper",
            checked_rollback_command(args),
            args.rollback_timeout,
        )
        result["rollback_summary"] = {
            "returncode": rollback.get("returncode"),
            "checked_helper_used": True,
            "target": "v2321",
        }
        if rollback.get("returncode") != 0:
            result["decision"] = "wsta233-blocked-v2321-rollback-failed"
            result["gate_decision"] = result["decision"]
            write_json(result_path(run_dir), result)
            return result
        command_record(run_dir, "rollback", "bridge-restart", restart_bridge_command(args), args.bridge_wait_timeout + 5.0)
        final = capture_phase(args, run_dir, "rollback-final")
        summary["rollback_final"] = final["records"]
        summary["rollback_final_compact_redacted"] = final["compact_redacted"]
        result["rollback_final_compact_redacted"] = final["compact_redacted"]
        final_ok = (
            final["compact_redacted"].get("selftest_fail_zero") is True
            and "v2321" in str(final["compact_redacted"].get("native_version", ""))
        )
        result["rollback_summary"]["final_v2321_selftest_fail_zero"] = final_ok
        result["decision"] = PASS_DECISION if final_ok else "wsta233-blocked-final-v2321-health-failed"
        result["gate_decision"] = "ok" if final_ok else result["decision"]
        append_event(summary, "rollback_v2321_done")
        save_summary(run_dir, summary)

    result["ended_utc"] = utc_iso()
    write_json(result_path(run_dir), result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--bridge-wait-timeout", type=float, default=8.0)
    parser.add_argument("--device-ncm-host", default="192.168.7.2")
    parser.add_argument("--tcpctl-port", type=int, default=DEFAULT_TCPCTL_PORT)
    parser.add_argument("--admin-ssh-port", type=int, default=DEFAULT_ADMIN_SSH_PORT)
    parser.add_argument("--smoke-port", type=int, default=DEFAULT_SMOKE_PORT)
    parser.add_argument("--port-probe-timeout", type=float, default=2.0)
    parser.add_argument("--serial-path", type=Path, default=DEFAULT_SERIAL_PATH)
    parser.add_argument("--wait-timeout", type=float, default=480.0)
    parser.add_argument("--poll-sec", type=float, default=0.5)
    parser.add_argument("--reconnect-stable-sec", type=float, default=5.0)
    parser.add_argument("--rollback-bridge-timeout", type=float, default=60.0)
    parser.add_argument("--rollback-timeout", type=float, default=180.0)
    parser.add_argument("--capture-pre-baseline", action="store_true")
    parser.add_argument("--wait-serial-cold-boot", action="store_true")
    parser.add_argument("--capture-post-classify", action="store_true")
    parser.add_argument("--rollback-v2321", action="store_true")
    parser.add_argument("--ack-rollback-to-v2321", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        result = {"decision": "wsta233-runner-error", "error": str(exc)}
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") in {PREBASELINE_DECISION, POST_CLASSIFIED_DECISION, PASS_DECISION} else 1


if __name__ == "__main__":
    raise SystemExit(main_with_args())
