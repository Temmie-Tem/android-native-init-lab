#!/usr/bin/env python3
"""V849 bounded live subsys_esoc0 wait-state sampler.

V848 narrowed the V847 block to provider `powerup()` versus
`wait_for_err_ready()`. This runner repeats one bounded `subsys_esoc0` char
open and captures the blocked holder's task wait-state evidence before cleanup.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, repo_path, run_capture, strip_cmdv1_text
from a90ctl import run_cmdv1_command
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v849-subsys-esoc0-wait-state-sampler")
LATEST_POINTER = Path("tmp/wifi/latest-v849-subsys-esoc0-wait-state-sampler.txt")
DEFAULT_V848_MANIFEST = Path("tmp/wifi/v848-subsys-esoc0-open-block-classifier/manifest.json")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 60.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
EXPECTED_V848 = "v848-subsys-esoc0-open-block-boundary-classified"
NODE_PATH = "/dev/subsys_esoc0"
BASE_PATH = "/tmp/a90-v849-subsys-esoc0"

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
    "esoc_link>",
    "esoc_name>",
    "subsys9/state>",
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
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v848-manifest", type=Path, default=DEFAULT_V848_MANIFEST)
    parser.add_argument("--hold-sec", type=int, default=12)
    parser.add_argument("--observe-sec", type=int, default=8)
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


def redact(text: str) -> str:
    return SECRET_RE.sub(r"\1 [redacted]", ANSI_RE.sub("", text))


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def validate_device_command(command: list[str]) -> None:
    joined = " " + " ".join(command).lower() + " "
    for term in FORBIDDEN_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden V849 command term {term!r}: {' '.join(command)}")


def shell_cmd(args: argparse.Namespace, script: str) -> list[str]:
    return ["run", args.busybox, "sh", "-c", script]


def run_step(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    command: list[str],
    timeout: float | None = None,
    expect_disconnect: bool = False,
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
        "ok": capture.ok or (expect_disconnect and capture.status == "missing"),
        "rc": capture.rc,
        "status": capture.status,
        "duration_sec": round(capture.duration_sec, 3),
        "error": redact(capture.error),
        "payload": payload[:4096] + ("\n[truncated]\n" if len(payload) > 4096 else ""),
        "file": f"native/{safe_name(name)}.txt",
        "expect_disconnect": expect_disconnect,
    }
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


def node_probe_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; NODE={NODE_PATH}; "
        "printf 'node=%s\\n' \"$NODE\"; $BB ls -l \"$NODE\" 2>&1 || true; "
        "printf 'proc_devices_subsys='; $BB grep -E '^ *236 +subsys$' /proc/devices 2>&1 || true; "
        "printf 'proc_devices_esoc='; $BB grep -E '^ *484 +esoc$' /proc/devices 2>&1 || true; "
        "true"
    )


def state_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "for p in /sys/bus/msm_subsys/devices/subsys9 /sys/devices/platform/soc/soc:qcom,mdm3/subsys9 /sys/bus/msm_subsys/devices/subsys0; do "
        "printf '== %s ==\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; "
        "for f in name state crash_count restart_level firmware_name system_debug uevent; do "
        "if [ -e \"$p/$f\" ]; then printf 'FILE %s/%s\\n' \"$p\" \"$f\"; $BB cat \"$p/$f\" 2>&1 | $BB head -c 500; printf '\\n'; fi; "
        "done; done; true"
    )


def module_surface_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "for p in /sys/module/*esoc* /sys/module/*mdm* /sys/module/*mhi* /sys/module/*icnss* /sys/module/wlan; do "
        "[ -e \"$p\" ] || continue; printf '== MODULE %s ==\\n' \"$p\"; "
        "$BB ls -ld \"$p\" 2>&1 || true; "
        "for f in initstate refcnt taint version; do [ -e \"$p/$f\" ] && { printf 'FILE %s/%s\\n' \"$p\" \"$f\"; $BB cat \"$p/$f\" 2>&1 | $BB head -c 300; printf '\\n'; }; done; "
        "if [ -d \"$p/parameters\" ]; then printf 'PARAMETERS %s\\n' \"$p/parameters\"; $BB ls \"$p/parameters\" 2>&1 | $BB head -n 40; fi; "
        "if [ -d \"$p/holders\" ]; then printf 'HOLDERS %s\\n' \"$p/holders\"; $BB ls \"$p/holders\" 2>&1 | $BB head -n 40; fi; "
        "done; true"
    )


def materialize_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; NODE={NODE_PATH}; "
        "if [ -e \"$NODE\" ]; then $BB rm -f \"$NODE\"; fi; "
        "$BB mknod \"$NODE\" c 236 9; rc=$?; $BB chmod 600 \"$NODE\" 2>/dev/null || true; "
        "printf 'v849.mknod.rc=%s\\n' \"$rc\"; $BB ls -l \"$NODE\" 2>&1 || true; exit \"$rc\""
    )


def holder_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    hold_sec = max(1, int(args.hold_sec))
    return (
        f"BB={bb}; NODE={NODE_PATH}; BASE={BASE_PATH}; "
        "STATUS=${BASE}.status; PID=${BASE}.pid; LOG=${BASE}.log; "
        "$BB rm -f \"$STATUS\" \"$PID\" \"$LOG\"; "
        "("
        "printf 'holder.inner.pid=%s\\n' \"$$\" >> \"$LOG\"; "
        "exec 9<>\"$NODE\"; rc=$?; "
        "printf 'holder.open.rc=%s\\n' \"$rc\" >> \"$STATUS\"; "
        "if [ \"$rc\" = 0 ]; then printf 'holder.opened=1\\n' >> \"$STATUS\"; "
        f"$BB sleep {hold_sec}; printf 'holder.closing=1\\n' >> \"$STATUS\"; fi"
        ") & "
        "pid=$!; printf '%s\\n' \"$pid\" > \"$PID\"; $BB sleep 1; "
        "printf 'v849.holder.pid=%s\\n' \"$pid\"; "
        "printf 'v849.status.begin\\n'; $BB cat \"$STATUS\" 2>&1 || true; printf 'v849.status.end\\n'; "
        "printf 'v849.log.begin\\n'; $BB cat \"$LOG\" 2>&1 || true; printf 'v849.log.end\\n'; "
        "$BB ps 2>&1 | $BB grep -E \"($pid|a90-v849|subsys_esoc0)\" | $BB grep -v grep || true; true"
    )


def status_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; BASE={BASE_PATH}; STATUS=${{BASE}}.status; PID=${{BASE}}.pid; LOG=${{BASE}}.log; "
        "printf '== holder files ==\\n'; for f in \"$PID\" \"$STATUS\" \"$LOG\"; do printf 'FILE %s\\n' \"$f\"; $BB cat \"$f\" 2>&1 || true; done; "
        "printf '== ps holder ==\\n'; if [ -r \"$PID\" ]; then pid=$($BB cat \"$PID\" 2>/dev/null); $BB ps 2>&1 | $BB grep -E \"($pid|a90-v849|subsys_esoc0)\" | $BB grep -v grep || true; fi; true"
    )


def proc_sample_script(args: argparse.Namespace, label: str) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; BASE={BASE_PATH}; PIDFILE=${{BASE}}.pid; LABEL={label}; "
        "printf '== sample %s ==\\n' \"$LABEL\"; "
        "PIDS=''; [ -r \"$PIDFILE\" ] && PIDS=\"$PIDS $($BB cat \"$PIDFILE\" 2>/dev/null)\"; "
        "for d in /proc/[0-9]*; do p=${d##*/}; "
        "comm=$($BB cat \"$d/comm\" 2>/dev/null); "
        "cmd=$($BB tr '\\000' ' ' < \"$d/cmdline\" 2>/dev/null); "
        "case \"$cmd $comm\" in *a90-v849*|*subsys_esoc0*) PIDS=\"$PIDS $p\";; esac; "
        "done; "
        "SEEN=' '; "
        "for p in $PIDS; do case \"$SEEN\" in *\" $p \"*) continue;; esac; SEEN=\"$SEEN$p \"; "
        "[ -d /proc/$p ] || { printf '== PROC %s missing ==\\n' \"$p\"; continue; }; "
        "printf '== PROC %s ==\\n' \"$p\"; "
        "for f in comm wchan stat syscall; do printf 'FILE /proc/%s/%s\\n' \"$p\" \"$f\"; $BB cat \"/proc/$p/$f\" 2>&1 | $BB head -c 1200; printf '\\n'; done; "
        "printf 'FILE /proc/%s/status\\n' \"$p\"; $BB cat \"/proc/$p/status\" 2>&1 | $BB head -c 3500; printf '\\n'; "
        "printf 'FILE /proc/%s/stack\\n' \"$p\"; if [ -r \"/proc/$p/stack\" ]; then $BB cat \"/proc/$p/stack\" 2>&1 | $BB head -c 4096; else printf '<not-readable>'; fi; printf '\\n'; "
        "printf 'FD /proc/%s/fd\\n' \"$p\"; $BB ls -l \"/proc/$p/fd\" 2>&1 | $BB head -n 40; "
        "done; true"
    )


def cleanup_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; NODE={NODE_PATH}; BASE={BASE_PATH}; PID=${{BASE}}.pid; STATUS=${{BASE}}.status; LOG=${{BASE}}.log; "
        "if [ -r \"$PID\" ]; then pid=$($BB cat \"$PID\" 2>/dev/null); printf 'cleanup.pid=%s\\n' \"$pid\"; $BB kill \"$pid\" 2>&1 || true; $BB sleep 1; $BB kill -9 \"$pid\" 2>&1 || true; fi; "
        "$BB rm -f \"$NODE\" \"$PID\" \"$STATUS\" \"$LOG\" 2>&1 || true; "
        "printf 'cleanup.node.after='; $BB ls -l \"$NODE\" 2>&1 || true; true"
    )


def dmesg_filter_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "$BB dmesg 2>&1 | $BB grep -Ei 'subsystem_get|subsystem_put|subsys_start|subsys_stop|Powering up esoc0|before wait_for_err_ready|Error ready|mdm3|esoc|sdx50|mhi|pcie|wlan_pd|wlfw|icnss|qmi|qrtr|BDF|wlan0|warning|panic|fatal' | $BB tail -n 520 || true; true"
    )


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def marker_counts(text: str) -> dict[str, int]:
    lower = text.lower()
    return {
        "subsystem_get": lower.count("subsystem_get"),
        "wait_for_err_ready": lower.count("wait_for_err_ready"),
        "error_ready_timeout": lower.count("error ready timed out"),
        "esoc": lower.count("esoc"),
        "mdm3": lower.count("mdm3"),
        "mhi": lower.count("mhi"),
        "pcie": lower.count("pcie"),
        "wlfw": lower.count("wlfw"),
        "bdf": lower.count("bdf"),
        "wlan0": lower.count("wlan0"),
        "warning": lower.count("warning:"),
        "panic": lower.count("panic"),
        "fatal": lower.count("fatal"),
    }


def wait_state_summary(text: str) -> dict[str, Any]:
    lower = text.lower()
    matches = {
        "stack_readable": "FILE /proc/" in text and "<not-readable>" not in text,
        "wchan_present": "FILE /proc/" in text and "/wchan" in text,
        "wait_for_err_ready_seen": "wait_for_err_ready" in lower,
        "wait_for_completion_seen": "wait_for_completion" in lower,
        "provider_powerup_hints": any(term in lower for term in ("mdm_subsys_powerup", "esoc_mdm", "ap2mdm", "mdm2ap", "gpio", "subsys_start")),
        "mhi_hook_hints": any(term in lower for term in ("mhi_arch_esoc_ops_power_on", "mhi_pci_probe", "msm_pcie")),
        "uninterruptible_sleep_seen": "State:\tD" in text or "State: D" in text,
    }
    focused: list[str] = []
    for line in text.splitlines():
        low = line.lower()
        if any(term in low for term in ("wchan", "stack", "wait_for", "subsys", "esoc", "mdm", "gpio", "mhi", "pcie", "state:")):
            focused.append(line.strip())
        if len(focused) >= 80:
            break
    return {"matches": matches, "focused_lines": focused}


def classify_wait_branch(samples: str, dmesg: str, status: str) -> tuple[str, str]:
    lower_samples = samples.lower()
    lower_dmesg = dmesg.lower()
    if "holder.opened=1" in status:
        return "v849-subsys-esoc0-open-completed", "holder open completed during the bounded window"
    if "wait_for_err_ready" in lower_samples or "before wait_for_err_ready" in lower_dmesg or "error ready timed out" in lower_dmesg:
        return "v849-subsys-esoc0-block-wait-for-err-ready", "blocked after provider powerup reached the err_ready wait path"
    if "mdm_subsys_powerup" in lower_samples:
        return "v849-subsys-esoc0-block-in-mdm-subsys-powerup", "blocked inside the proprietary ext-mdm provider powerup path before wait_for_err_ready/MHI/WLFW"
    if any(term in lower_samples for term in ("mhi_arch_esoc_ops_power_on", "mhi_pci_probe", "msm_pcie")):
        return "v849-subsys-esoc0-block-after-esoc-mhi-hook", "blocked after eSoC provider reached MHI/PCIe hook context"
    if "__subsystem_get" in lower_dmesg or "changing subsys fw_name" in lower_dmesg:
        return "v849-subsys-esoc0-block-provider-powerup-or-opaque", "blocked after __subsystem_get entry but before observable wait_for_err_ready/MHI/WLFW markers"
    return "v849-subsys-esoc0-wait-state-captured-unresolved", "captured wait-state evidence but did not match a stronger branch"


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
        "reboot_command_error": redact(reboot_capture.error),
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
    run_step(args, store, steps, "pre-module-surface", shell_cmd(args, module_surface_script(args)), timeout=20.0)


def run_live(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    reboot: dict[str, Any] = {}
    try:
        run_step(args, store, steps, "materialize-node", shell_cmd(args, materialize_script(args)), timeout=15.0)
        run_step(args, store, steps, "post-mknod-node-probe", shell_cmd(args, node_probe_script(args)), timeout=20.0)
        run_step(args, store, steps, "start-holder", shell_cmd(args, holder_script(args)), timeout=20.0)
        run_step(args, store, steps, "sample-after-start", shell_cmd(args, proc_sample_script(args, "after-start")), timeout=25.0)
        run_step(args, store, steps, "status-after-start", shell_cmd(args, status_script(args)), timeout=20.0)
        run_step(args, store, steps, "state-after-start", shell_cmd(args, state_script(args)), timeout=20.0)
        run_step(args, store, steps, "module-surface-after-start", shell_cmd(args, module_surface_script(args)), timeout=20.0)
        time.sleep(max(1, int(args.observe_sec)))
        run_step(args, store, steps, "sample-after-observe", shell_cmd(args, proc_sample_script(args, "after-observe")), timeout=25.0)
        run_step(args, store, steps, "status-after-observe", shell_cmd(args, status_script(args)), timeout=20.0)
        run_step(args, store, steps, "state-after-observe", shell_cmd(args, state_script(args)), timeout=20.0)
        run_step(args, store, steps, "dmesg-after-observe", shell_cmd(args, dmesg_filter_script(args)), timeout=30.0)
        run_step(args, store, steps, "cleanup-node-holder", shell_cmd(args, cleanup_script(args)), timeout=20.0)
    finally:
        if args.allow_reboot_cleanup:
            reboot = wait_for_reboot(args, store)
    samples = step_payload(steps, "sample-after-start") + "\n" + step_payload(steps, "sample-after-observe")
    status = step_payload(steps, "status-after-start") + "\n" + step_payload(steps, "status-after-observe")
    state = step_payload(steps, "state-after-start") + "\n" + step_payload(steps, "state-after-observe")
    dmesg = step_payload(steps, "dmesg-after-observe")
    branch, branch_reason = classify_wait_branch(samples, dmesg, status)
    return {
        "node": NODE_PATH,
        "mknod_ok": "v849.mknod.rc=0" in step_payload(steps, "materialize-node"),
        "holder_pid_seen": "v849.holder.pid=" in step_payload(steps, "start-holder"),
        "holder_opened": "holder.opened=1" in status,
        "holder_open_rc_zero": "holder.open.rc=0" in status,
        "sample_summary": wait_state_summary(samples),
        "branch": branch,
        "branch_reason": branch_reason,
        "mdm3_online": "ONLINE" in state and "esoc0" in state,
        "mdm3_offlining_seen": "OFFLINING" in state,
        "markers": marker_counts(dmesg),
        "reboot_cleanup": reboot,
    }


def build_checks(args: argparse.Namespace, v848: dict[str, Any], steps: list[dict[str, Any]], live: dict[str, Any], missing_flags: list[str]) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{"name": "plan-only", "status": "pass", "detail": "no live action executed", "next_step": "run V849 with explicit live flags"}]
    return [
        {"name": "explicit-live-flags", "status": "pass" if not missing_flags else "blocked", "detail": {"missing": missing_flags}, "next_step": "pass required --allow flags"},
        {"name": "v848-route-ready", "status": "pass" if v848.get("decision") == EXPECTED_V848 and v848.get("pass") is True else "blocked", "detail": {"decision": v848.get("decision"), "pass": v848.get("pass")}, "next_step": "refresh V848 classifier"},
        {"name": "preflight-health", "status": "pass" if args.expect_version in step_payload(steps, "pre-version") and "BOOT OK" in step_payload(steps, "pre-bootstatus") and "fail=0" in step_payload(steps, "pre-selftest") else "blocked", "detail": {"expect_version": args.expect_version}, "next_step": "restore healthy native v724"},
        {"name": "node-materialized", "status": "pass" if live.get("mknod_ok") else "blocked", "detail": {"node": live.get("node"), "mknod_ok": live.get("mknod_ok")}, "next_step": "inspect node evidence"},
        {"name": "holder-sampled", "status": "pass" if live.get("holder_pid_seen") and (live.get("sample_summary") or {}).get("matches", {}).get("wchan_present") else "blocked", "detail": {"holder_pid_seen": live.get("holder_pid_seen"), "sample_matches": (live.get("sample_summary") or {}).get("matches")}, "next_step": "inspect proc sampler evidence"},
        {"name": "post-reboot-cleanup", "status": "pass" if (live.get("reboot_cleanup") or {}).get("version_seen") and (live.get("reboot_cleanup") or {}).get("bootstatus_healthy") and (live.get("reboot_cleanup") or {}).get("selftest_healthy") else "blocked", "detail": live.get("reboot_cleanup") or {}, "next_step": "restore native health before continuing"},
        {"name": "below-hal-contract", "status": "pass", "detail": {"wifi_hal_start_executed": False, "scan_connect_executed": False, "credential_use_executed": False, "dhcp_route_executed": False, "external_ping_executed": False}, "next_step": "continue below HAL/connect until WLFW/BDF/wlan0 exists"},
    ]


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], live: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return ("v849-subsys-esoc0-wait-state-sampler-plan-ready", True, "plan-only; no live action executed", "run bounded V849 wait-state sampler")
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return ("v849-subsys-esoc0-wait-state-sampler-blocked", False, "blocked by " + ", ".join(blocked), "restore health or inspect V849 evidence before retrying")
    branch = str(live.get("branch") or "v849-subsys-esoc0-wait-state-captured-unresolved")
    if branch == "v849-subsys-esoc0-open-completed":
        return (branch, True, str(live.get("branch_reason")), "classify mdm3/MHI/WLFW deltas before HAL/connect")
    return (branch, True, str(live.get("branch_reason")), "use V849 wait-state evidence to select the next lowest mdm3/eSoC trigger; no HAL/connect yet")


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v848 = load_json(args.v848_manifest)
    missing_flags = required_flags(args) if args.command == "run" else []
    steps: list[dict[str, Any]] = []
    live: dict[str, Any] = {}
    if args.command == "run" and not missing_flags:
        collect_preflight(args, store, steps)
        live = run_live(args, store, steps)
    checks = build_checks(args, v848, steps, live, missing_flags)
    decision, pass_ok, reason, next_step = decide(args, checks, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v849",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v848_manifest": str(resolve(args.v848_manifest)),
            "v848_decision": v848.get("decision"),
            "v848_pass": v848.get("pass"),
            "expect_version": args.expect_version,
        },
        "steps": steps,
        "live": live,
        "checks": checks,
        "device_commands_executed": args.command == "run" and not missing_flags,
        "device_mutations": args.command == "run" and not missing_flags,
        "mknod_executed": args.command == "run" and not missing_flags,
        "subsys_char_open_executed": args.command == "run" and not missing_flags,
        "proc_wait_state_sampled": args.command == "run" and not missing_flags,
        "reboot_cleanup_executed": args.command == "run" and not missing_flags and args.allow_reboot_cleanup,
        "qmi_payload_executed": False,
        "raw_esoc_open_executed": False,
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
    checks = "\n".join(f"- `{item['name']}`: `{item['status']}` — {item['next_step']}" for item in manifest["checks"])
    live = manifest.get("live", {})
    steps = "\n".join(f"- `{step.get('name')}`: `{step.get('ok')}` `{step.get('file')}`" for step in manifest.get("steps", []))
    focus = "\n".join(f"- `{line}`" for line in ((live.get("sample_summary") or {}).get("focused_lines") or [])[:30])
    return "\n".join([
        "# V849 subsys_esoc0 Wait-State Sampler",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- mknod_executed: `{manifest['mknod_executed']}`",
        f"- subsys_char_open_executed: `{manifest['subsys_char_open_executed']}`",
        f"- proc_wait_state_sampled: `{manifest['proc_wait_state_sampled']}`",
        f"- reboot_cleanup_executed: `{manifest['reboot_cleanup_executed']}`",
        f"- raw_esoc_open_executed: `{manifest['raw_esoc_open_executed']}`",
        f"- sysfs_write_executed: `{manifest['sysfs_write_executed']}`",
        f"- gpio_write_executed: `{manifest['gpio_write_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        checks,
        "",
        "## Live Branch",
        "",
        f"- branch: `{live.get('branch')}`",
        f"- branch_reason: {live.get('branch_reason')}",
        f"- holder_opened: `{live.get('holder_opened')}`",
        f"- mdm3_online: `{live.get('mdm3_online')}`",
        f"- markers: `{json.dumps(live.get('markers') or {}, sort_keys=True)}`",
        f"- sample_matches: `{json.dumps((live.get('sample_summary') or {}).get('matches') or {}, sort_keys=True)}`",
        "",
        "## Focused Wait-State Lines",
        "",
        focus or "- none",
        "",
        "## Steps",
        "",
        steps,
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
    print(f"proc_wait_state_sampled: {manifest['proc_wait_state_sampled']}")
    print(f"reboot_cleanup_executed: {manifest['reboot_cleanup_executed']}")
    print(f"raw_esoc_open_executed: {manifest['raw_esoc_open_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
