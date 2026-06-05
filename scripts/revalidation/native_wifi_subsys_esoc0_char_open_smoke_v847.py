#!/usr/bin/env python3
"""V847 bounded live subsys_esoc0 char-device open smoke.

V846 selected the source-backed subsystem char-device open path as the next
mdm3/eSoC gate. This runner materializes only the V845-advertised
`subsys_esoc0` node, starts a bounded background open/hold attempt, captures
state/dmesg evidence, removes the node, and reboots back to a clean native
state.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90ctl import run_cmdv1_command
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v847-subsys-esoc0-char-open-smoke")
LATEST_POINTER = Path("tmp/wifi/latest-v847-subsys-esoc0-char-open-smoke.txt")
DEFAULT_V846_MANIFEST = Path("tmp/wifi/v846-mdm3-esoc-state-control-contract/manifest.json")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 60.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
EXPECTED_V846 = "v846-mdm3-esoc-char-open-contract-selected"
NODE_PATH = "/dev/subsys_esoc0"

SECRET_RE = re.compile(r"(made by|creator: made by) [^\r\n]+", re.IGNORECASE)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

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
    "/dev/esoc",
    "/sys/bus/esoc/devices/esoc0/esoc_link>",
    "/sys/bus/esoc/devices/esoc0/esoc_name>",
    "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state>",
    "/sys/bus/msm_subsys/devices/subsys9/state>",
)

FORBIDDEN_ACTIONS = (
    "raw /dev/esoc* open or ioctl",
    "GPIO/sysfs/debugfs write",
    "subsystem state write, bind/unbind, driver override, or module load/unload",
    "daemon start, service-manager start, or Wi-Fi HAL start",
    "Wi-Fi scan/connect/link-up or credential use",
    "DHCP, route change, or external ping",
    "custom kernel flash, boot image write, or partition write",
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
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v846-manifest", type=Path, default=DEFAULT_V846_MANIFEST)
    parser.add_argument("--hold-sec", type=int, default=8)
    parser.add_argument("--observe-sec", type=int, default=10)
    parser.add_argument("--allow-mknod", action="store_true")
    parser.add_argument("--allow-subsys-char-open", action="store_true")
    parser.add_argument("--allow-reboot-cleanup", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--no-hide-on-busy", dest="hide_on_busy", action="store_false")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def load_json(path: Path) -> dict[str, Any]:
    resolved = resolve(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def nested(data: Any, *keys: Any) -> Any:
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            return None
    return current


def redact(text: str) -> str:
    return SECRET_RE.sub(r"\1 [redacted]", ANSI_RE.sub("", text))


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def validate_device_command(command: list[str]) -> None:
    joined = " " + " ".join(command).lower() + " "
    for term in FORBIDDEN_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden V847 command term {term!r}: {' '.join(command)}")


def shell_cmd(args: argparse.Namespace, script: str) -> list[str]:
    return ["run", args.busybox, "sh", "-c", script]


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None,
             expect_disconnect: bool = False) -> dict[str, Any]:
    validate_device_command(command)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    hide_item: dict[str, Any] | None = None
    if args.hide_on_busy and (capture.status == "busy" or "[busy]" in payload):
        hide_capture = run_capture(args, f"{name}-hide-on-busy", ["hide"], timeout=min(args.timeout, 8.0))
        hide_payload = strip_cmdv1_text(hide_capture.text) if hide_capture.text else hide_capture.error + "\n"
        hide_payload = redact(hide_payload)
        hide_item = capture_to_manifest(hide_capture)
        hide_item["payload"] = hide_payload
        hide_item["file"] = f"native/{safe_name(name)}-hide-on-busy.txt"
        hide_item["ok"] = hide_capture.ok
        store.write_text(hide_item["file"], hide_payload.rstrip() + "\n")
        capture = run_capture(args, name, command, timeout=timeout or args.timeout)
        payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    payload = redact(payload)
    item = capture_to_manifest(capture)
    item["payload"] = payload
    item["file"] = f"native/{safe_name(name)}.txt"
    item["ok"] = capture.ok or (expect_disconnect and capture.status == "missing")
    item["expect_disconnect"] = expect_disconnect
    if hide_item is not None:
        item["hide_on_busy"] = hide_item
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    if not args.allow_mknod:
        missing.append("--allow-mknod")
    if not args.allow_subsys_char_open:
        missing.append("--allow-subsys-char-open")
    if not args.allow_reboot_cleanup:
        missing.append("--allow-reboot-cleanup")
    if not args.assume_yes:
        missing.append("--assume-yes")
    return missing


def state_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "for p in /sys/bus/msm_subsys/devices/subsys9 /sys/devices/platform/soc/soc:qcom,mdm3/subsys9 /sys/bus/msm_subsys/devices/subsys0; do "
        "printf '== %s ==\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; "
        "for f in name state crash_count restart_level firmware_name system_debug uevent; do "
        "if [ -e \"$p/$f\" ]; then printf 'FILE %s/%s\\n' \"$p\" \"$f\"; $BB cat \"$p/$f\" 2>&1 | $BB head -c 500; printf '\\n'; fi; "
        "done; done; "
        "true"
    )


def node_probe_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        f"printf 'node={NODE_PATH}\\n'; $BB ls -l {NODE_PATH} 2>&1 || true; "
        "printf 'proc_devices_subsys='; $BB grep -E '^ *236 +subsys$' /proc/devices 2>&1 || true; "
        "printf 'proc_devices_esoc='; $BB grep -E '^ *484 +esoc$' /proc/devices 2>&1 || true; "
        "true"
    )


def materialize_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; NODE={NODE_PATH}; "
        "if [ -e \"$NODE\" ]; then $BB rm -f \"$NODE\"; fi; "
        "$BB mknod \"$NODE\" c 236 9; rc=$?; "
        "$BB chmod 600 \"$NODE\" 2>/dev/null || true; "
        "printf 'v847.mknod.rc=%s\\n' \"$rc\"; $BB ls -l \"$NODE\" 2>&1 || true; "
        "exit \"$rc\""
    )


def holder_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    hold_sec = max(1, int(args.hold_sec))
    return (
        f"BB={bb}; NODE={NODE_PATH}; BASE=/tmp/a90-v847-subsys-esoc0; "
        "STATUS=${BASE}.status; PID=${BASE}.pid; LOG=${BASE}.log; "
        "$BB rm -f \"$STATUS\" \"$PID\" \"$LOG\"; "
        "("
        "printf 'holder.start.pid=%s\\n' \"$$\" >> \"$LOG\"; "
        "exec 9<>\"$NODE\"; rc=$?; "
        "printf 'holder.open.rc=%s\\n' \"$rc\" >> \"$STATUS\"; "
        "if [ \"$rc\" = 0 ]; then "
        "printf 'holder.opened=1\\n' >> \"$STATUS\"; "
        f"$BB sleep {hold_sec}; "
        "printf 'holder.closing=1\\n' >> \"$STATUS\"; "
        "fi"
        ") & "
        "pid=$!; printf '%s\\n' \"$pid\" > \"$PID\"; "
        "$BB sleep 1; "
        "printf 'v847.holder.pid=%s\\n' \"$pid\"; "
        "printf 'v847.status.begin\\n'; $BB cat \"$STATUS\" 2>&1 || true; printf 'v847.status.end\\n'; "
        "$BB ps 2>&1 | $BB grep -E \"($pid|a90-v847|subsys_esoc0)\" | $BB grep -v grep || true; "
        "true"
    )


def status_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; BASE=/tmp/a90-v847-subsys-esoc0; STATUS=${{BASE}}.status; PID=${{BASE}}.pid; LOG=${{BASE}}.log; "
        "printf '== holder files ==\\n'; for f in \"$PID\" \"$STATUS\" \"$LOG\"; do printf 'FILE %s\\n' \"$f\"; $BB cat \"$f\" 2>&1 || true; done; "
        "printf '== ps holder ==\\n'; if [ -r \"$PID\" ]; then pid=$($BB cat \"$PID\" 2>/dev/null); $BB ps 2>&1 | $BB grep -E \"($pid|a90-v847|subsys_esoc0)\" | $BB grep -v grep || true; fi; "
        "true"
    )


def cleanup_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; NODE={NODE_PATH}; BASE=/tmp/a90-v847-subsys-esoc0; STATUS=${{BASE}}.status; PID=${{BASE}}.pid; LOG=${{BASE}}.log; "
        "if [ -r \"$PID\" ]; then pid=$($BB cat \"$PID\" 2>/dev/null); "
        "printf 'cleanup.pid=%s\\n' \"$pid\"; $BB kill \"$pid\" 2>&1 || true; $BB sleep 1; $BB kill -9 \"$pid\" 2>&1 || true; fi; "
        "$BB rm -f \"$NODE\" \"$PID\" \"$STATUS\" \"$LOG\" 2>&1 || true; "
        "printf 'cleanup.node.after='; $BB ls -l \"$NODE\" 2>&1 || true; "
        "true"
    )


def dmesg_filter_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "$BB dmesg 2>&1 | $BB grep -Ei 'subsystem_get|subsystem_put|subsys_start|subsys_stop|subsys|mdm3|esoc|sdx50|mhi|pcie|wlan_pd|wlfw|icnss|qmi|qrtr|BDF|wlan0|warning|panic|fatal' | $BB tail -n 420 || true; "
        "true"
    )


def marker_counts(text: str) -> dict[str, int]:
    lower = text.lower()
    return {
        "subsystem_get": lower.count("subsystem_get"),
        "subsystem_put": lower.count("subsystem_put"),
        "subsys_start": lower.count("subsys_start"),
        "subsys_stop": lower.count("subsys_stop"),
        "mdm3": lower.count("mdm3"),
        "esoc": lower.count("esoc"),
        "sdx50": lower.count("sdx50"),
        "mhi": lower.count("mhi"),
        "pcie": lower.count("pcie"),
        "wlan_pd": lower.count("wlan_pd"),
        "wlfw": lower.count("wlfw"),
        "bdf": lower.count("bdf"),
        "wlan0": lower.count("wlan0"),
        "warning": lower.count("warning:"),
        "panic": lower.count("panic"),
        "fatal": lower.count("fatal"),
    }


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def wait_for_reboot(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    reboot_capture = run_capture(args, "reboot-cleanup", ["reboot"], timeout=5.0)
    store.write_text("native/reboot-cleanup.txt", redact(strip_cmdv1_text(reboot_capture.text) if reboot_capture.text else reboot_capture.error + "\n"))
    started = time.monotonic()
    version_text = ""
    bootstatus_text = ""
    selftest_text = ""
    for _ in range(90):
        try:
            result = run_cmdv1_command(args.host, args.port, 3.0, ["version"], retry_unsafe=False)
            if result.rc == 0 and result.status == "ok":
                version_text = result.text
                boot = run_cmdv1_command(args.host, args.port, 8.0, ["bootstatus"], retry_unsafe=False)
                bootstatus_text = boot.text
                selftest = run_cmdv1_command(args.host, args.port, 8.0, ["selftest", "verbose"], retry_unsafe=False)
                selftest_text = selftest.text
                break
        except Exception:
            time.sleep(2.0)
    store.write_text("native/post-reboot-version.txt", redact(strip_cmdv1_text(version_text) if version_text else "<missing>\n"))
    store.write_text("native/post-reboot-bootstatus.txt", redact(strip_cmdv1_text(bootstatus_text) if bootstatus_text else "<missing>\n"))
    store.write_text("native/post-reboot-selftest.txt", redact(strip_cmdv1_text(selftest_text) if selftest_text else "<missing>\n"))
    return {
        "reboot_command_ok": reboot_capture.ok,
        "reboot_command_status": reboot_capture.status,
        "reboot_command_error": reboot_capture.error,
        "wait_sec": round(time.monotonic() - started, 3),
        "version_seen": args.expect_version in version_text,
        "bootstatus_healthy": "BOOT OK" in bootstatus_text and "fail=0" in bootstatus_text,
        "selftest_healthy": "selftest: pass=" in selftest_text and "fail=0" in selftest_text,
    }


def collect_preflight(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    run_step(args, store, steps, "pre-version", ["version"], timeout=20.0)
    run_step(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=20.0)
    run_step(args, store, steps, "pre-selftest", ["selftest", "verbose"], timeout=20.0)
    run_step(args, store, steps, "pre-node-probe", shell_cmd(args, node_probe_script(args)), timeout=20.0)
    run_step(args, store, steps, "pre-state", shell_cmd(args, state_script(args)), timeout=20.0)
    run_step(args, store, steps, "pre-dmesg-focus", shell_cmd(args, dmesg_filter_script(args)), timeout=30.0)


def run_live(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    reboot: dict[str, Any] = {}
    try:
        run_step(args, store, steps, "materialize-node", shell_cmd(args, materialize_script(args)), timeout=15.0)
        run_step(args, store, steps, "post-mknod-node-probe", shell_cmd(args, node_probe_script(args)), timeout=20.0)
        run_step(args, store, steps, "start-holder", shell_cmd(args, holder_script(args)), timeout=20.0)
        run_step(args, store, steps, "status-after-start", shell_cmd(args, status_script(args)), timeout=20.0)
        run_step(args, store, steps, "state-after-start", shell_cmd(args, state_script(args)), timeout=20.0)
        time.sleep(max(1, int(args.observe_sec)))
        run_step(args, store, steps, "status-after-observe", shell_cmd(args, status_script(args)), timeout=20.0)
        run_step(args, store, steps, "state-after-observe", shell_cmd(args, state_script(args)), timeout=20.0)
        run_step(args, store, steps, "dmesg-after-observe", shell_cmd(args, dmesg_filter_script(args)), timeout=30.0)
        run_step(args, store, steps, "cleanup-node-holder", shell_cmd(args, cleanup_script(args)), timeout=20.0)
    finally:
        if args.allow_reboot_cleanup:
            reboot = wait_for_reboot(args, store)
    dmesg_text = step_payload(steps, "dmesg-after-observe")
    status_text = step_payload(steps, "status-after-start") + "\n" + step_payload(steps, "status-after-observe")
    state_text = step_payload(steps, "state-after-start") + "\n" + step_payload(steps, "state-after-observe")
    return {
        "node": NODE_PATH,
        "mknod_ok": "v847.mknod.rc=0" in step_payload(steps, "materialize-node"),
        "holder_pid_seen": "v847.holder.pid=" in step_payload(steps, "start-holder"),
        "holder_opened": "holder.opened=1" in status_text,
        "holder_open_rc_zero": "holder.open.rc=0" in status_text,
        "mdm3_online": "ONLINE" in state_text and "esoc0" in state_text,
        "mdm3_offlining_seen": "OFFLINING" in state_text,
        "markers": marker_counts(dmesg_text),
        "reboot_cleanup": reboot,
    }


def build_checks(command: str,
                 args: argparse.Namespace,
                 v846: dict[str, Any],
                 steps: list[dict[str, Any]],
                 live: dict[str, Any],
                 missing_flags: list[str]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "no device command, mknod, open, reboot, HAL/connect, route, ping, or flash executed",
            "next_step": "run V847 with explicit live flags",
        }]
    return [
        {
            "name": "explicit-live-flags",
            "status": "pass" if not missing_flags else "blocked",
            "detail": {"missing": missing_flags},
            "next_step": "pass --allow-mknod --allow-subsys-char-open --allow-reboot-cleanup --assume-yes",
        },
        {
            "name": "v846-route-ready",
            "status": "pass" if v846.get("decision") == EXPECTED_V846 and v846.get("pass") is True else "blocked",
            "detail": {"decision": v846.get("decision"), "pass": v846.get("pass")},
            "next_step": "refresh V846 before V847 live smoke",
        },
        {
            "name": "preflight-health",
            "status": "pass" if args.expect_version in step_payload(steps, "pre-version") and "BOOT OK" in step_payload(steps, "pre-bootstatus") and "fail=0" in step_payload(steps, "pre-selftest") else "blocked",
            "detail": {"expect_version": args.expect_version},
            "next_step": "restore healthy native v724 before char-device open",
        },
        {
            "name": "node-materialized",
            "status": "pass" if live.get("mknod_ok") else "blocked",
            "detail": {"node": live.get("node"), "mknod_ok": live.get("mknod_ok")},
            "next_step": "inspect mknod evidence and /proc/devices major/minor",
        },
        {
            "name": "holder-started",
            "status": "pass" if live.get("holder_pid_seen") else "blocked",
            "detail": {
                "holder_pid_seen": live.get("holder_pid_seen"),
                "holder_opened": live.get("holder_opened"),
                "holder_open_rc_zero": live.get("holder_open_rc_zero"),
            },
            "next_step": "inspect whether open blocked, failed, or completed",
        },
        {
            "name": "post-reboot-cleanup",
            "status": "pass" if (live.get("reboot_cleanup") or {}).get("version_seen") and (live.get("reboot_cleanup") or {}).get("bootstatus_healthy") and (live.get("reboot_cleanup") or {}).get("selftest_healthy") else "blocked",
            "detail": live.get("reboot_cleanup") or {},
            "next_step": "restore native health before continuing if cleanup failed",
        },
        {
            "name": "below-hal-contract",
            "status": "pass",
            "detail": {
                "wifi_hal_start_executed": False,
                "scan_connect_executed": False,
                "credential_use_executed": False,
                "dhcp_route_executed": False,
                "external_ping_executed": False,
            },
            "next_step": "continue below HAL/connect until WLFW/BDF/wlan0 exists",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]], live: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v847-subsys-esoc0-char-open-smoke-plan-ready",
            True,
            "plan-only; no live action executed",
            "run bounded V847 char-device open smoke with cleanup reboot",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v847-subsys-esoc0-char-open-smoke-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "restore health or inspect V847 evidence before retrying",
        )
    markers = live.get("markers") or {}
    if live.get("holder_opened") and (live.get("mdm3_online") or markers.get("wlfw", 0) > 0 or markers.get("mhi", 0) > 0):
        return (
            "v847-subsys-esoc0-open-advanced-mdm3-surface",
            True,
            "bounded char open completed and produced mdm3/MHI/WLFW-adjacent progress markers",
            "V848 should classify WLFW/service69/BDF readiness before HAL/connect",
        )
    if live.get("holder_opened"):
        return (
            "v847-subsys-esoc0-open-no-wlfw-progress",
            True,
            "bounded char open completed but did not produce WLFW/BDF/wlan0 progress in the observation window",
            "V848 should classify char-open dmesg/state deltas and decide whether MHI power_up or longer holder window is justified",
        )
    return (
        "v847-subsys-esoc0-open-blocked-or-pending",
        True,
        "holder process started but open did not report success within the bounded observation window; cleanup reboot restored native health",
        "V848 should classify open-block evidence before any retry or wider trigger",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v846 = load_json(args.v846_manifest)
    missing_flags = required_flags(args) if args.command == "run" else []
    steps: list[dict[str, Any]] = []
    live: dict[str, Any] = {}
    if args.command == "run" and not missing_flags:
        collect_preflight(args, store, steps)
        live = run_live(args, store, steps)
    checks = build_checks(args.command, args, v846, steps, live, missing_flags)
    decision, pass_ok, reason, next_step = decide(args.command, checks, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v847",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v846_manifest": str(resolve(args.v846_manifest)),
            "v846_decision": v846.get("decision"),
            "v846_pass": v846.get("pass"),
            "expect_version": args.expect_version,
        },
        "steps": steps,
        "live": live,
        "checks": checks,
        "device_commands_executed": args.command == "run" and not missing_flags,
        "device_mutations": args.command == "run" and not missing_flags,
        "mknod_executed": args.command == "run" and not missing_flags,
        "subsys_char_open_executed": args.command == "run" and not missing_flags,
        "reboot_cleanup_executed": args.command == "run" and not missing_flags and args.allow_reboot_cleanup,
        "qmi_payload_executed": False,
        "raw_esoc_open_executed": False,
        "esoc0_open_executed": False,
        "gpio_write_executed": False,
        "sysfs_write_executed": False,
        "bind_unbind_executed": False,
        "module_load_unload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    step_rows = [
        [str(step.get("name")), str(step.get("ok")), str(step.get("status")), str(step.get("file"))]
        for step in manifest.get("steps", [])
    ]
    live_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in manifest.get("live", {}).items()]
    return "\n".join([
        "# V847 subsys_esoc0 Char-Device Open Smoke",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- mknod_executed: `{manifest['mknod_executed']}`",
        f"- subsys_char_open_executed: `{manifest['subsys_char_open_executed']}`",
        f"- reboot_cleanup_executed: `{manifest['reboot_cleanup_executed']}`",
        f"- raw_esoc_open_executed: `{manifest['raw_esoc_open_executed']}`",
        f"- sysfs_write_executed: `{manifest['sysfs_write_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Live",
        "",
        markdown_table(["signal", "value"], live_rows),
        "",
        "## Steps",
        "",
        markdown_table(["step", "ok", "status", "file"], step_rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"mknod_executed: {manifest['mknod_executed']}")
    print(f"subsys_char_open_executed: {manifest['subsys_char_open_executed']}")
    print(f"reboot_cleanup_executed: {manifest['reboot_cleanup_executed']}")
    print(f"raw_esoc_open_executed: {manifest['raw_esoc_open_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
