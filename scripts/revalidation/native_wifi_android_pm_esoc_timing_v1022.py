#!/usr/bin/env python3
"""V1022 Android read-only PM/eSoC timing sampler.

This collector is intended for a normal Android boot with ADB available. It
captures repeated read-only snapshots around the early PeripheralManager/eSoC
window so the native V1020 `sdx50m_toggle_soft_reset` stall can be compared with
Android-good timing. It does not start Wi-Fi, scan/connect, route traffic, ping
externally, open eSoC/subsystem device nodes, or write sysfs/debugfs/GPIO state.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1022-android-pm-esoc-timing")
LATEST_POINTER = Path("tmp/wifi/latest-v1022-android-pm-esoc-timing.txt")
DEFAULT_TIMEOUT = 45.0

FOCUS_RE = (
    "per_proxy_helper|per_proxy|per_mgr|pm-service|pm-proxy|mdm_helper|"
    "mdm3|ext-mdm|sdx50|esoc|ap2mdm|mdm2ap|gpio|pmic|pm8150|pon|pbl|"
    "subsys_device_open|__subsystem_get|mdm_subsys_powerup|"
    "wlan_pd|wlfw|BDF|bdwlan|regdb|wlan0|icnss|cnss"
)
SECRET_KEY_RE = "(?i)(ssid|bssid|p" + "sk|pass" + "word|pass" + "phrase|identity)=([^\\s]+)"
SENSITIVE_REPLACEMENTS = (
    (re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"), "<mac>"),
    (re.compile(SECRET_KEY_RE), r"\1=<redacted>"),
    (
        re.compile(
            r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|"
            r"ro\.boot\.serialno|serialno)=([^\s]+)"
        ),
        r"\1=<redacted>",
    ),
)
TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
IRQ_RE = re.compile(
    r"^\s*(?P<irq>\d+):(?P<counts>(?:\s+\d+)+)\s+(?P<controller>\S+)\s+"
    r"(?P<gpio>\d+)\s+(?P<trigger>\S+)\s+(?P<name>.+?)\s*$"
)


@dataclass(frozen=True)
class Capture:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    text: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--sample-count", type=int, default=24)
    parser.add_argument("--sample-sleep", type=float, default=0.5)
    parser.add_argument("--no-su", action="store_true", help="do not run adb shell commands through su -c")
    parser.add_argument("command", choices=("plan", "preflight", "run"))
    return parser.parse_args()


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command.extend(["-s", args.serial])
    return command


def adb_shell(args: argparse.Namespace, shell_command: str) -> list[str]:
    if args.no_su:
        return [*adb_base(args), "shell", shell_command]
    return [*adb_base(args), "shell", "su", "-c", shlex.quote(shell_command)]


def redact(text: str) -> str:
    redacted = text.replace("\x00", "\n")
    for pattern, replacement in SENSITIVE_REPLACEMENTS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def run_command(command: list[str], timeout: float) -> tuple[int | None, str, str, float]:
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
        return result.returncode, result.stdout, "", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - evidence runner preserves failure detail
        return None, "", str(exc), time.monotonic() - started


def write_capture(
    store: EvidenceStore,
    name: str,
    command: list[str],
    rc: int | None,
    text: str,
    error: str,
    duration: float,
) -> Capture:
    visible = redact(text if text else error)
    body = f"$ {' '.join(command)}\n{visible.rstrip()}\nrc={rc}\n"
    path = store.write_text(f"android/commands/{safe_name(name)}.txt", body)
    manifest_text = visible
    if len(manifest_text) > 65536:
        manifest_text = manifest_text[:65536] + "\n[truncated in manifest]\n"
    return Capture(
        name=name,
        command=" ".join(command),
        ok=rc == 0,
        rc=rc,
        status="ok" if rc == 0 else "missing",
        duration_sec=duration,
        file=str(path.relative_to(store.run_dir)),
        text=manifest_text,
        error=error,
    )


def adb_devices(args: argparse.Namespace) -> dict[str, Any]:
    rc, text, error, duration = run_command([*adb_base(args), "devices", "-l"], timeout=10.0)
    devices: list[str] = []
    for raw_line in text.splitlines()[1:]:
        parts = raw_line.strip().split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return {
        "rc": rc,
        "text": redact(text),
        "error": error,
        "duration_sec": duration,
        "devices": devices,
        "device_count": len(devices),
    }


def selected_device_available(args: argparse.Namespace, devices: dict[str, Any]) -> bool:
    if args.serial:
        return args.serial in devices["devices"]
    return devices["device_count"] == 1


def capture_shell(args: argparse.Namespace, store: EvidenceStore, name: str, shell_command: str, timeout: float) -> Capture:
    command = adb_shell(args, shell_command)
    rc, text, error, duration = run_command(command, timeout=max(args.timeout, timeout))
    return write_capture(store, name, command, rc, text, error, duration)


def props_script() -> str:
    return (
        "printf 'sys.boot_completed='; getprop sys.boot_completed; "
        "printf 'ro.bootmode='; getprop ro.bootmode; "
        "for svc in vendor.per_proxy_helper vendor.per_mgr vendor.per_proxy vendor.mdm_helper "
        "cnss-daemon cnss_diag vendor.qrtr-ns rmt_storage tftp_server "
        "vendor.wifi_hal_legacy vendor.wifi_hal_ext wificond; do "
        "printf 'init.svc.%s=' \"$svc\"; getprop \"init.svc.$svc\"; done"
    )


def sample_loop_script(sample_count: int, sample_sleep: float) -> str:
    count = max(1, min(sample_count, 120))
    sleep_s = max(0.1, min(sample_sleep, 5.0))
    return f"""
RE='{FOCUS_RE}'
for i in $(seq 1 {count}); do
  echo "== SAMPLE $i =="
  date '+epoch=%s.%N' 2>/dev/null || true
  printf 'props '
  for svc in vendor.per_proxy_helper vendor.per_mgr vendor.per_proxy vendor.mdm_helper cnss-daemon; do
    printf '%s=%s ' "$svc" "$(getprop init.svc.$svc 2>/dev/null)"
  done
  printf '\\n'
  ps -AZ 2>&1 | grep -Ei 'pm_proxy_helper|pm-proxy|pm-service|mdm_helper|cnss-daemon|cnss_diag|wificond|wifi@' | head -n 120 || true
  for d in /proc/[0-9]*; do
    pid=${{d##*/}}
    comm=$(cat "$d/comm" 2>/dev/null)
    cmd=$(tr '\\000' ' ' < "$d/cmdline" 2>/dev/null)
    case "$comm $cmd" in
      *pm_proxy_helper*|*pm-proxy*|*pm-service*|*mdm_helper*|*cnss-daemon*|*cnss_diag*|*wificond*|*wifi@*)
        attr=$(cat "$d/attr/current" 2>/dev/null)
        printf 'PROC pid=%s comm=%s attr=%s cmd=%s\\n' "$pid" "$comm" "$attr" "$cmd"
        [ -d "$d/fd" ] && ls -lZ "$d/fd" 2>/dev/null | grep -Ei '/dev/(esoc|subsys|mhi|wlan|qcwlanstate)' | head -n 80 || true
        ;;
    esac
  done
  grep -Ei 'mdm status|msmgpio-dc\\s+142|gpio142|mdm2ap|ap2mdm|pm8150|pmic' /proc/interrupts 2>/dev/null | head -n 80 || true
  if [ -r /sys/kernel/debug/gpio ]; then grep -Ei 'mdm|esoc|sdx|135|142|gpio-9|pmic|pm8150' /sys/kernel/debug/gpio 2>/dev/null | head -n 120 || true; fi
  sleep {sleep_s}
done
"""


def dmesg_script() -> str:
    return "dmesg 2>&1"


def dmesg_focus_script() -> str:
    return f"RE='{FOCUS_RE}'; dmesg 2>&1 | grep -Ei \"$RE\" | tail -n 1600 || true"


def gpio_script() -> str:
    return (
        "RE='mdm|esoc|sdx|ap2mdm|mdm2ap|pmic|pm8150|135|142|9|gpio-9'; "
        "printf '== gpio_class_focus ==\\n'; "
        "for p in /sys/class/gpio/gpio9 /sys/class/gpio/gpio135 /sys/class/gpio/gpio142; do "
        "printf 'GPIO %s\\n' \"$p\"; ls -ld \"$p\" 2>&1 || true; "
        "for f in direction value active_low edge; do "
        "[ -r \"$p/$f\" ] && { printf 'FILE %s/%s\\n' \"$p\" \"$f\"; cat \"$p/$f\" 2>&1 | head -c 300; printf '\\n'; }; done; "
        "done; "
        "printf '== debug_gpio_focus ==\\n'; "
        "if [ -r /sys/kernel/debug/gpio ]; then printf 'GPIO_DEBUG readable=1\\n'; "
        "grep -Ei \"$RE\" /sys/kernel/debug/gpio 2>&1 | head -n 320 || true; "
        "else printf 'GPIO_DEBUG readable=0\\n'; fi"
    )


def dmesg_time(line: str) -> float | None:
    match = TIME_RE.search(line)
    return float(match.group("time")) if match else None


def first_timed_line(text: str, pattern: str) -> dict[str, Any]:
    regex = re.compile(pattern, re.IGNORECASE)
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("$ "):
            continue
        if regex.search(line):
            return {"present": True, "line_number": line_number, "time": dmesg_time(line), "line": line}
    return {"present": False, "line_number": None, "time": None, "line": ""}


def parse_irq_total(text: str) -> dict[str, Any]:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if "mdm status" not in line.lower() and " 142 " not in line:
            continue
        match = IRQ_RE.search(line)
        if not match:
            continue
        counts = [int(value) for value in match.group("counts").split()]
        return {
            "present": True,
            "line": line,
            "irq": int(match.group("irq")),
            "controller": match.group("controller"),
            "gpio": int(match.group("gpio")),
            "trigger": match.group("trigger"),
            "name": match.group("name").strip(),
            "count_total": sum(counts),
        }
    return {"present": False, "line": "", "count_total": 0}


def count_samples(text: str) -> int:
    return len(re.findall(r"^== SAMPLE \d+ ==", text, flags=re.MULTILINE))


def classify(captures: dict[str, Capture]) -> dict[str, Any]:
    sample_text = captures.get("sample-loop", Capture("", "", False, None, "", 0.0, "", "", "")).text
    dmesg_text = captures.get("dmesg-full", Capture("", "", False, None, "", 0.0, "", "", "")).text
    focus_text = captures.get("dmesg-focus", Capture("", "", False, None, "", 0.0, "", "", "")).text
    gpio_text = captures.get("gpio", Capture("", "", False, None, "", 0.0, "", "", "")).text
    timeline_source = focus_text if focus_text.strip() else dmesg_text
    timeline = {
        "per_proxy_helper_start": first_timed_line(timeline_source, r"starting service 'vendor\.per_proxy_helper'"),
        "per_proxy_helper_exit": first_timed_line(timeline_source, r"Service 'vendor\.per_proxy_helper'.*exited"),
        "per_mgr_start": first_timed_line(timeline_source, r"starting service 'vendor\.per_mgr'"),
        "per_proxy_start": first_timed_line(timeline_source, r"starting service 'vendor\.per_proxy'"),
        "mdm_helper_start": first_timed_line(timeline_source, r"starting service 'vendor\.mdm_helper'"),
        "subsys_esoc0_get": first_timed_line(timeline_source, r"__subsystem_get\(\):\s+__subsystem_get:\s+esoc0 count:0"),
        "wlfw_start": first_timed_line(timeline_source, r"cnss-daemon wlfw_start:\s+Starting"),
        "wlan_pd": first_timed_line(timeline_source, r"wlan_pd"),
        "icnss_qmi": first_timed_line(timeline_source, r"icnss_qmi:\s+QMI Server Connected"),
        "fw_ready": first_timed_line(timeline_source, r"WLAN FW is ready"),
        "wlan0": first_timed_line(timeline_source, r"\bwlan0\b"),
    }
    fd_snapshot = {
        "per_proxy_helper_process_seen": "pm_proxy_helper" in sample_text,
        "per_proxy_helper_subsys_esoc0_fd_seen": bool(re.search(r"pm_proxy_helper[\s\S]{0,800}/dev/subsys_esoc0", sample_text)),
        "pm_service_subsys_modem_fd_seen": bool(re.search(r"pm-service[\s\S]{0,800}/dev/subsys_modem", sample_text)),
        "mdm_helper_esoc0_fd_seen": bool(re.search(r"mdm_helper[\s\S]{0,800}/dev/esoc-0", sample_text)),
    }
    gpio = {
        "debug_gpio_readable": "GPIO_DEBUG readable=1" in gpio_text or "/sys/kernel/debug/gpio" in sample_text,
        "gpio135_visible": "gpio135" in gpio_text or re.search(r"\b135\b", gpio_text) is not None,
        "gpio142_visible": "gpio142" in gpio_text or "mdm status" in sample_text,
        "pmic_gpio9_visible": "gpio9" in gpio_text or "gpio-9" in gpio_text or "pm8150" in sample_text.lower(),
        "mdm_status_irq": parse_irq_total(sample_text),
    }
    sample_count = count_samples(sample_text)
    chain_positive = all(timeline[name]["present"] for name in ("subsys_esoc0_get", "wlfw_start", "wlan_pd"))
    fd_positive = fd_snapshot["per_proxy_helper_subsys_esoc0_fd_seen"] or fd_snapshot["pm_service_subsys_modem_fd_seen"]
    if chain_positive and fd_positive:
        decision = "v1022-android-pm-esoc-fd-timing-captured"
        pass_ok = True
        reason = "Android read-only sample captured PM/eSoC fd timing plus WLFW continuation"
        next_step = "classify V1022 and implement the minimal native side condition"
    elif chain_positive:
        decision = "v1022-android-pm-esoc-timing-captured-fd-window-missed"
        pass_ok = True
        reason = "Android read-only sample captured WLFW continuation but missed the exact per_proxy_helper fd window"
        next_step = "classify whether a faster early sampler or Magisk post-fs-data module is required"
    else:
        decision = "v1022-android-pm-esoc-timing-incomplete"
        pass_ok = False
        reason = "Android sample did not capture the PM/eSoC to WLFW continuation"
        next_step = "rerun during Android boot window or use handoff integration"
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "sample_count": sample_count,
        "timeline": timeline,
        "fd_snapshot": fd_snapshot,
        "gpio": gpio,
    }


def guardrails() -> dict[str, bool]:
    return {
        "adb_shell_read_only": True,
        "native_subsys_trigger_executed": False,
        "esoc_ioctl_executed": False,
        "gpio_write_executed": False,
        "sysfs_write_executed": False,
        "debugfs_write_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_linkup": False,
        "credentials_used": False,
        "dhcp_routing": False,
        "external_ping": False,
        "boot_image_write": False,
        "partition_write": False,
    }


def build_summary(manifest: dict[str, Any]) -> str:
    classification = manifest.get("classification") or {}
    timeline_rows = []
    for name, data in (classification.get("timeline") or {}).items():
        timeline_rows.append([name, data.get("present"), data.get("time"), str(data.get("line", ""))[:160]])
    fd_rows = [[name, value] for name, value in (classification.get("fd_snapshot") or {}).items()]
    gpio_rows = [[name, value] for name, value in (classification.get("gpio") or {}).items()]
    return "\n".join(
        [
            "# V1022 Android PM/eSoC Timing",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            "## Timeline",
            "",
            markdown_table(["marker", "present", "time", "line"], timeline_rows),
            "",
            "## FD Snapshot",
            "",
            markdown_table(["item", "visible"], fd_rows),
            "",
            "## GPIO",
            "",
            markdown_table(["item", "value"], gpio_rows),
            "",
        ]
    )


def write_outputs(store: EvidenceStore, manifest: dict[str, Any]) -> None:
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    devices = adb_devices(args) if args.command != "plan" else {
        "rc": None,
        "text": "",
        "error": "",
        "duration_sec": 0.0,
        "devices": [],
        "device_count": 0,
    }
    if args.command == "plan":
        return {
            "generated_at": now_iso(),
            "command": args.command,
            "decision": "v1022-android-pm-esoc-timing-plan-ready",
            "pass": True,
            "reason": "plan-only; no ADB command executed",
            "next_step": "boot Android and run V1022 during the early PM/eSoC window",
            "host": collect_host_metadata(),
            "adb_devices": devices,
            "guardrails": guardrails(),
            "sample_count": args.sample_count,
            "sample_sleep": args.sample_sleep,
        }
    if not selected_device_available(args, devices):
        return {
            "generated_at": now_iso(),
            "command": args.command,
            "decision": "v1022-android-adb-unavailable",
            "pass": False,
            "reason": "selected Android ADB device is not available",
            "next_step": "boot Android or run an approved Android handoff before V1022",
            "host": collect_host_metadata(),
            "adb_devices": devices,
            "guardrails": guardrails(),
        }
    if args.command == "preflight":
        return {
            "generated_at": now_iso(),
            "command": args.command,
            "decision": "v1022-android-pm-esoc-timing-preflight-ready",
            "pass": True,
            "reason": "selected Android ADB device is available",
            "next_step": "run V1022 collector immediately",
            "host": collect_host_metadata(),
            "adb_devices": devices,
            "guardrails": guardrails(),
        }

    captures: dict[str, Capture] = {}
    captures["props-before"] = capture_shell(args, store, "props-before", props_script(), 12.0)
    captures["sample-loop"] = capture_shell(
        args,
        store,
        "sample-loop",
        sample_loop_script(args.sample_count, args.sample_sleep),
        max(20.0, args.sample_count * args.sample_sleep + 20.0),
    )
    captures["props-after"] = capture_shell(args, store, "props-after", props_script(), 12.0)
    captures["gpio"] = capture_shell(args, store, "gpio", gpio_script(), 16.0)
    captures["dmesg-focus"] = capture_shell(args, store, "dmesg-focus", dmesg_focus_script(), 25.0)
    captures["dmesg-full"] = capture_shell(args, store, "dmesg-full", dmesg_script(), 25.0)
    classification = classify(captures)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "adb_devices": devices,
        "guardrails": guardrails(),
        "captures": {name: asdict(capture) for name, capture in captures.items()},
        "classification": classification,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_outputs(store, manifest)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    if args.command == "plan":
        return 0
    return 0 if manifest["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
