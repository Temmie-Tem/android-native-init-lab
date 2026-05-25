#!/usr/bin/env python3
"""V852 Android read-only ext-mdm provider surface sampler.

This collector runs while Android ADB is available and captures the same
provider-level surface as V851 from Android as the positive-control state. It
does not enable Wi-Fi, scan/connect, change routes, write sysfs/debugfs, or use
credentials.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v852-android-ext-mdm-provider-surface-sample")
DEFAULT_TIMEOUT = 45.0

FOCUS_RE = (
    "mdm_subsys_powerup|subsys_device_open|__subsystem_get|subsys_start|"
    "mdm3|ext-mdm|esoc|sdx50|ap2mdm|mdm2ap|MDM_PMIC|pmic|pm8150|"
    "mhi_arch_esoc_ops_power_on|mhi_pci_probe|msm_pcie|wlfw|bdf|wlan0"
)

SECRET_KEY_RE = "(?i)(ssid|bssid|p" + "sk|pass" + "word|pass" + "phrase)=([^\\s]+)"
SENSITIVE_REPLACEMENTS = (
    (re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"), "<mac>"),
    (re.compile(SECRET_KEY_RE), r"\1=<redacted>"),
    (re.compile(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|ro\.boot\.serialno|serialno)=([^\s]+)"), r"\1=<redacted>"),
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


def run_command(command: list[str], timeout: float) -> tuple[int | None, str, str, float]:
    import time

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


def redact(text: str) -> str:
    redacted = text
    for pattern, replacement in SENSITIVE_REPLACEMENTS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def write_capture(store: EvidenceStore, name: str, command: list[str], rc: int | None, text: str, error: str, duration: float) -> Capture:
    body = f"$ {' '.join(command)}\n{redact(text if text else error).rstrip()}\nrc={rc}\n"
    path = store.write_text(f"android/commands/{safe_name(name)}.txt", body)
    visible = redact(text)
    if len(visible) > 65536:
        visible = visible[:65536] + "\n[truncated in manifest]\n"
    return Capture(
        name=name,
        command=" ".join(command),
        ok=rc == 0,
        rc=rc,
        status="ok" if rc == 0 else "missing",
        duration_sec=duration,
        file=str(path.relative_to(store.run_dir)),
        text=visible,
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
        "printf 'init.svc.vendor.qrtr-ns='; getprop init.svc.vendor.qrtr-ns; "
        "printf 'init.svc.cnss-daemon='; getprop init.svc.cnss-daemon; "
        "printf 'init.svc.cnss_diag='; getprop init.svc.cnss_diag; "
        "printf 'ro.bootmode='; getprop ro.bootmode"
    )


def kallsyms_script() -> str:
    return (
        f"RE='{FOCUS_RE}'; "
        "printf '== kallsyms_focus ==\\n'; "
        "if [ -r /proc/kallsyms ]; then grep -Ei \"$RE\" /proc/kallsyms 2>&1 | head -n 260; "
        "else printf 'kallsyms_readable=0\\n'; fi"
    )


def interrupts_script() -> str:
    return (
        "RE='mdm|esoc|sdx|ap2mdm|mdm2ap|gpio|tlmm|pmic|pm8150|mhi|pcie|icnss|wlan'; "
        "printf '== interrupts_focus ==\\n'; "
        "if [ -r /proc/interrupts ]; then grep -Ei \"$RE\" /proc/interrupts 2>&1 | head -n 260; "
        "else printf 'interrupts_readable=0\\n'; fi"
    )


def platform_surface_script() -> str:
    return (
        "dump_file(){ f=\"$1\"; if [ -e \"$f\" ]; then printf 'FILE %s\\n' \"$f\"; "
        "if [ -r \"$f\" ]; then cat \"$f\" 2>&1 | head -c 1600; printf '\\n'; else printf 'UNREADABLE\\n'; fi; fi; }; "
        "dump_link(){ p=\"$1\"; printf 'LINK %s -> ' \"$p\"; readlink \"$p\" 2>&1 || true; }; "
        "dump_path(){ p=\"$1\"; printf '== PATH %s ==\\n' \"$p\"; ls -ld \"$p\" 2>&1 || true; dump_link \"$p\"; "
        "if [ -d \"$p\" ]; then ls -la \"$p\" 2>&1 | head -n 140; fi; "
        "for f in name state crash_count restart_level firmware_name fw_name edge esoc_link esoc_link_info esoc_name uevent "
        "power/control power/runtime_status power/runtime_suspended_time power/runtime_active_time driver/module/modalias; do dump_file \"$p/$f\"; done; "
        "for l in driver subsystem of_node power; do [ -e \"$p/$l\" ] && dump_link \"$p/$l\"; done; }; "
        "for p in "
        "/sys/devices/platform/soc/soc:qcom,mdm3 "
        "/sys/devices/platform/soc/soc:qcom,mdm3/esoc0 "
        "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9 "
        "/sys/bus/platform/devices/soc:qcom,mdm3 "
        "/sys/bus/esoc/devices/esoc0 "
        "/sys/bus/msm_subsys/devices/subsys9 "
        "/sys/bus/msm_subsys/devices/subsys0; do dump_path \"$p\"; done; true"
    )


def devicetree_surface_script() -> str:
    return (
        "printf '== mdm3_of_node ==\\n'; "
        "for root in /sys/firmware/devicetree/base /proc/device-tree; do "
        "[ -d \"$root\" ] || continue; "
        "for p in $(find \"$root\" -name 'qcom,mdm3' -print 2>/dev/null | head -n 12); do "
        "printf '== DTNODE %s ==\\n' \"$p\"; ls -la \"$p\" 2>&1 | head -n 140; "
        "for f in compatible status qcom,mdm-link-info qcom,sysmon-id qcom,ssctl-instance-id "
        "qcom,mdm2ap-status-gpio qcom,ap2mdm-status-gpio qcom,ap2mdm-errfatal-gpio "
        "qcom,mdm2ap-errfatal-gpio qcom,ap2mdm-soft-reset-gpio qcom,mdm2ap-vddmin-gpio "
        "qcom,mdm-pmic-pwr-status-gpio interrupt-names interrupt-map interrupts; do "
        "if [ -r \"$p/$f\" ]; then printf 'DTPROP %s/%s hex=' \"$p\" \"$f\"; "
        "od -An -tx1 \"$p/$f\" 2>&1 | tr '\\n' ' ' | head -c 900; printf '\\n'; fi; "
        "done; done; done"
    )


def gpio_pinctrl_script() -> str:
    return (
        "RE='mdm|esoc|sdx|wlan|icnss|pmic|pm8150|135|142|141|53|gpio-9'; "
        "printf '== gpio_class ==\\n'; ls -la /sys/class/gpio 2>&1 | head -n 160 || true; "
        "for p in /sys/class/gpio/gpio9 /sys/class/gpio/gpio53 /sys/class/gpio/gpio135 /sys/class/gpio/gpio141 /sys/class/gpio/gpio142; do "
        "printf '== GPIO %s ==\\n' \"$p\"; ls -ld \"$p\" 2>&1 || true; "
        "for f in direction value active_low edge label base ngpio; do [ -r \"$p/$f\" ] && { printf 'FILE %s/%s\\n' \"$p\" \"$f\"; cat \"$p/$f\" 2>&1 | head -c 500; printf '\\n'; }; done; "
        "done; "
        "printf '== gpiochips ==\\n'; "
        "for p in /sys/class/gpio/gpiochip*; do [ -e \"$p\" ] || continue; printf 'GPIOCHIP %s\\n' \"$p\"; "
        "for f in label base ngpio; do [ -r \"$p/$f\" ] && { printf '%s=' \"$f\"; cat \"$p/$f\" 2>&1 | head -c 260; printf '\\n'; }; done; done; "
        "printf '== debug_gpio_focus ==\\n'; "
        "if [ -r /sys/kernel/debug/gpio ]; then printf 'GPIO_DEBUG readable=1\\n'; grep -Ei \"$RE\" /sys/kernel/debug/gpio 2>&1 | head -n 220 || true; "
        "else printf 'GPIO_DEBUG readable=0\\n'; fi; "
        "printf '== debug_pinctrl_focus ==\\n'; "
        "if [ -d /sys/kernel/debug/pinctrl ]; then printf 'PINCTRL_DEBUG present=1\\n'; "
        "for f in /sys/kernel/debug/pinctrl/*/pins /sys/kernel/debug/pinctrl/*/pinmux-pins /sys/kernel/debug/pinctrl/*/pinconf-pins /sys/kernel/debug/pinctrl/*/gpio-ranges; do "
        "[ -r \"$f\" ] || continue; printf 'PINCTRL_FILE %s\\n' \"$f\"; grep -Ei \"$RE\" \"$f\" 2>&1 | head -n 120 || true; done; "
        "else printf 'PINCTRL_DEBUG present=0\\n'; fi"
    )


def proc_devices_script() -> str:
    return (
        "printf '== proc_devices_focus ==\\n'; grep -Ei 'esoc|subsys|mdm|qrtr|qmi|wlan|diag|mhi' /proc/devices 2>&1 || true; "
        "printf '== dev_nodes_presence ==\\n'; ls -ld /dev/* 2>&1 | grep -Ei '/dev/(esoc|subsys|mdm|qrtr|qmi|wlan|qcwlanstate)' || true"
    )


def dmesg_focus_script() -> str:
    return (
        f"RE='{FOCUS_RE}|warning|panic|fatal|PBL|PON|vdd|min|pinctrl|tlmm|service-notifier|wlan_pd|sysmon-qmi|qrtr'; "
        "printf '== dmesg_focus ==\\n'; dmesg 2>&1 | grep -Ei \"$RE\" | tail -n 680 || true"
    )


def collect(args: argparse.Namespace, store: EvidenceStore) -> list[Capture]:
    store.mkdir("android/commands")
    captures: list[Capture] = []
    rc, text, error, duration = run_command([*adb_base(args), "wait-for-device"], timeout=args.timeout)
    captures.append(write_capture(store, "adb-wait-for-device", [*adb_base(args), "wait-for-device"], rc, text, error, duration))
    captures.append(capture_shell(args, store, "boot-props", props_script(), 10.0))
    captures.append(capture_shell(args, store, "kallsyms-focus", kallsyms_script(), 20.0))
    captures.append(capture_shell(args, store, "interrupts-focus", interrupts_script(), 20.0))
    captures.append(capture_shell(args, store, "platform-surface", platform_surface_script(), 25.0))
    captures.append(capture_shell(args, store, "devicetree-surface", devicetree_surface_script(), 25.0))
    captures.append(capture_shell(args, store, "gpio-pinctrl-surface", gpio_pinctrl_script(), 25.0))
    captures.append(capture_shell(args, store, "proc-devices", proc_devices_script(), 15.0))
    captures.append(capture_shell(args, store, "dmesg-focus", dmesg_focus_script(), 25.0))
    return captures


def capture_text(captures: list[Capture], name: str) -> str:
    for capture in captures:
        if capture.name == name:
            return capture.text
    return ""


def boot_completed(captures: list[Capture]) -> bool:
    return "sys.boot_completed=1" in capture_text(captures, "boot-props")


def first_state(text: str, hints: tuple[str, ...]) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        lower = line.lower()
        if line.startswith("FILE ") and lower.endswith("/state") and any(hint in lower for hint in hints):
            if index + 1 < len(lines):
                value = lines[index + 1].strip()
                if value:
                    return value
    return ""


def grep_lines(text: str, pattern: str, limit: int = 80) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    rows: list[str] = []
    for line in text.splitlines():
        if regex.search(line):
            rows.append(line.strip())
        if len(rows) >= limit:
            break
    return rows


def symbol_present(text: str, name: str) -> bool:
    return bool(re.search(rf"\b{re.escape(name)}\b", text))


def count_patterns(text: str) -> dict[str, int]:
    lower = text.lower()
    return {
        "mdm_subsys_powerup": lower.count("mdm_subsys_powerup"),
        "ap2mdm": lower.count("ap2mdm"),
        "mdm2ap": lower.count("mdm2ap"),
        "mdm_pmic": lower.count("mdm_pmic"),
        "pm8150": lower.count("pm8150"),
        "mdm3": lower.count("mdm3"),
        "esoc": lower.count("esoc"),
        "sdx50": lower.count("sdx50"),
        "mhi": lower.count("mhi"),
        "pcie": lower.count("pcie"),
        "wlfw": lower.count("wlfw"),
        "bdf": lower.count("bdf"),
        "wlan0": lower.count("wlan0"),
        "warning": lower.count("warning:"),
        "panic": lower.count("panic"),
        "fatal": lower.count("fatal"),
    }


def summarize(captures: list[Capture]) -> dict[str, Any]:
    kallsyms = capture_text(captures, "kallsyms-focus")
    interrupts = capture_text(captures, "interrupts-focus")
    platform = capture_text(captures, "platform-surface")
    devicetree = capture_text(captures, "devicetree-surface")
    gpio = capture_text(captures, "gpio-pinctrl-surface")
    devices = capture_text(captures, "proc-devices")
    dmesg = capture_text(captures, "dmesg-focus")
    combined = "\n".join([kallsyms, interrupts, platform, devicetree, gpio, devices, dmesg])
    dmesg_lines = [line for line in dmesg.splitlines() if not line.startswith("$")]
    real_panic_or_fatal = any(
        re.search(r"\b(kernel panic|panic:|fatal exception|fatal error|BUG:|Oops:)\b", line, re.IGNORECASE)
        for line in dmesg_lines
    )
    return {
        "boot_completed": boot_completed(captures),
        "all_commands_ok": all(capture.ok for capture in captures),
        "mdm3_state": first_state(platform, ("mdm3", "subsys9", "esoc0")),
        "mss_state": first_state(platform, ("subsys0", "modem")),
        "symbols": {
            "mdm_subsys_powerup": symbol_present(kallsyms, "mdm_subsys_powerup"),
            "subsys_device_open": symbol_present(kallsyms, "subsys_device_open"),
            "__subsystem_get": symbol_present(kallsyms, "__subsystem_get"),
            "mhi_arch_esoc_ops_power_on": symbol_present(kallsyms, "mhi_arch_esoc_ops_power_on"),
            "mhi_pci_probe": symbol_present(kallsyms, "mhi_pci_probe"),
        },
        "surface": {
            "mdm3_sysfs_present": "== PATH /sys/devices/platform/soc/soc:qcom,mdm3 ==" in platform,
            "esoc0_sysfs_present": "== PATH /sys/bus/esoc/devices/esoc0 ==" in platform,
            "subsys9_present": "/sys/bus/msm_subsys/devices/subsys9" in platform,
            "dt_mdm3_present": "== DTNODE " in devicetree,
            "dt_pmic_pwr_status_prop": "qcom,mdm-pmic-pwr-status-gpio" in devicetree,
            "dt_ap2mdm_status_prop": "qcom,ap2mdm-status-gpio" in devicetree,
            "dt_mdm2ap_status_prop": "qcom,mdm2ap-status-gpio" in devicetree,
            "gpio_debug_readable": "GPIO_DEBUG readable=1" in gpio,
            "pinctrl_debug_present": "PINCTRL_DEBUG present=1" in gpio,
            "raw_esoc_node_present": "/dev/esoc" in devices and "No such file or directory" not in devices[devices.find("/dev/esoc"):devices.find("/dev/esoc") + 220],
        },
        "dmesg_hints": {
            "has_wlan_pd": "wlan_pd" in dmesg.lower(),
            "has_wlfw": "wlfw" in dmesg.lower(),
            "has_bdf": "bdf" in dmesg.lower() or "bdwlan" in dmesg.lower() or "regdb" in dmesg.lower(),
            "has_wlan0": "wlan0" in dmesg.lower(),
            "has_mhi": "mhi" in dmesg.lower(),
            "errfatal_signal_seen": "errfatal" in dmesg.lower(),
            "panic_or_fatal_seen": real_panic_or_fatal,
        },
        "irq_focus_lines": grep_lines(interrupts, r"mdm|esoc|sdx|gpio|tlmm|pmic|mhi|pcie|icnss|wlan", limit=100),
        "focused_lines": {
            "kallsyms": grep_lines(kallsyms, r"mdm_subsys_powerup|subsys_device_open|__subsystem_get|mhi_arch_esoc_ops_power_on|mhi_pci_probe", limit=40),
            "dmesg": grep_lines(dmesg, r"MDM_PMIC|AP2MDM|MDM2AP|mdm3|ext-mdm|esoc|mhi|wlfw|wlan0|fatal|panic|wlan_pd", limit=100),
            "gpio_pinctrl": grep_lines(gpio, r"GPIO_DEBUG|PINCTRL|mdm|esoc|sdx|135|142|141|53|pm8150", limit=100),
        },
        "counts": count_patterns(combined),
    }


def decide(args: argparse.Namespace, devices: dict[str, Any], captures: list[Capture], summary: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v852-android-ext-mdm-provider-surface-plan-ready", True, "plan-only; no adb command executed", "boot Android and run V852 collector"
    if devices["device_count"] == 0:
        return "v852-android-adb-unavailable", True, "no Android ADB device is currently visible", "boot Android or run the V852 handoff wrapper"
    if not selected_device_available(args, devices):
        return "v852-android-adb-selection-needed", True, f"device_count={devices['device_count']}", "rerun with --serial"
    if args.command == "preflight":
        return "v852-android-ext-mdm-provider-surface-preflight-ready", True, "one Android ADB device is visible", "run V852 Android read-only provider sample"
    if not captures:
        return "v852-android-ext-mdm-provider-surface-review", False, "run command did not produce captures", "inspect runner failure"
    if not summary.get("boot_completed"):
        return "v852-android-not-boot-complete", False, "Android ADB is visible but sys.boot_completed=1 was not captured", "wait for Android boot-complete and rerun V852"
    if not summary.get("all_commands_ok"):
        return "v852-android-provider-surface-partial", True, "Android provider surface captured with one or more read command failures", "inspect partial evidence and rerun only if required"
    if summary.get("mdm3_state") == "ONLINE":
        return (
            "v852-android-mdm3-online-provider-surface-captured",
            True,
            "Android positive-control provider surface captured with mdm3 ONLINE",
            "compare against V851 native OFFLINING surface and select the smallest native prerequisite",
        )
    return (
        "v852-android-provider-surface-captured-review",
        True,
        f"Android provider surface captured with mdm3_state={summary.get('mdm3_state')!r}",
        "compare against V851 native surface before any GPIO/eSoC write",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    captures = manifest.get("captures") or []
    summary = manifest.get("android_summary") or {}
    capture_rows = [[item["name"], item["status"], item["rc"], item["duration_sec"], item["file"]] for item in captures]
    analysis_rows = [
        [key, json.dumps(value, ensure_ascii=False, sort_keys=True)]
        for key, value in summary.items()
        if key not in {"focused_lines", "irq_focus_lines"}
    ]
    focused = summary.get("focused_lines") or {}
    focused_lines: list[str] = []
    for group, lines in focused.items():
        focused_lines.append(f"### {group}")
        focused_lines.extend(f"- `{line}`" for line in list(lines)[:30])
        if not lines:
            focused_lines.append("- none")
    return "\n".join([
        "# V852 Android ext-mdm Provider Surface Sample",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## ADB Devices",
        "",
        "```text",
        (manifest.get("adb_devices") or {}).get("text", "").rstrip(),
        "```",
        "",
        "## Analysis",
        "",
        markdown_table(["signal", "value"], analysis_rows) if analysis_rows else "- none",
        "",
        "## Focused Lines",
        "",
        "\n".join(focused_lines) or "- none",
        "",
        "## Captures",
        "",
        markdown_table(["name", "status", "rc", "duration_sec", "file"], capture_rows) if capture_rows else "- none",
        "",
        "## Guardrails",
        "",
        "- Android read-only only.",
        "- No Wi-Fi enable/disable, scan/connect/link-up/credential/DHCP/routing changes.",
        "- No external ping or network reachability probe.",
        "- No sysfs/debugfs write, GPIO export, module load/unload, or service start.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    devices = adb_devices(args) if args.command != "plan" else {"rc": None, "text": "", "error": "", "duration_sec": 0.0, "devices": [], "device_count": 0}
    captures: list[Capture] = []
    android_summary: dict[str, Any] = {
        "boot_completed": False,
        "all_commands_ok": False,
        "mdm3_state": "",
        "mss_state": "",
        "symbols": {},
        "surface": {},
        "dmesg_hints": {},
        "irq_focus_lines": [],
        "focused_lines": {},
        "counts": {},
    }
    if args.command == "run" and selected_device_available(args, devices):
        captures = collect(args, store)
        android_summary = summarize(captures)
    decision, pass_ok, reason, next_step = decide(args, devices, captures, android_summary)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "adb_devices": devices,
        "captures": [asdict(capture) for capture in captures],
        "android_summary": android_summary,
        "device_commands_executed": args.command == "run" and bool(captures),
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "sysfs_write_executed": False,
        "debugfs_write_executed": False,
        "gpio_write_executed": False,
        "module_load_unload_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
