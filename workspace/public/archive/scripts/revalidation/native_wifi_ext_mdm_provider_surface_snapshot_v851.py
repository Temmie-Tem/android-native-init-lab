#!/usr/bin/env python3
"""V851 live read-only ext-mdm provider surface snapshot.

V850 selected the proprietary ext-mdm provider surface as the next gate after
V849 showed a D-state holder in `mdm_subsys_powerup`. This runner captures the
lowest read-only runtime signals around that provider without opening raw eSoC
nodes, writing GPIO/sysfs/debugfs, or starting upper Wi-Fi components.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v851-ext-mdm-provider-surface-snapshot")
LATEST_POINTER = Path("tmp/wifi/latest-v851-ext-mdm-provider-surface-snapshot.txt")
DEFAULT_V850_MANIFEST = Path("tmp/wifi/v850-ext-mdm-powerup-surface-classifier/manifest.json")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 60.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
EXPECTED_V850 = "v850-ext-mdm-powerup-surface-selected"

SECRET_RE = re.compile(r"(made by|creator: made by) [^\r\n]+", re.IGNORECASE)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

FOCUS_RE = (
    "mdm_subsys_powerup|subsys_device_open|__subsystem_get|subsys_start|"
    "mdm3|ext-mdm|esoc|sdx50|ap2mdm|mdm2ap|MDM_PMIC|pmic|pm8150|"
    "mhi_arch_esoc_ops_power_on|mhi_pci_probe|msm_pcie|wlfw|bdf|wlan0"
)

FORBIDDEN_TERMS = (
    " mount ",
    " umount ",
    " echo ",
    " tee ",
    " dd ",
    " mknod ",
    " mkdir ",
    " rm ",
    " rmdir ",
    " chmod ",
    " chown ",
    " cp ",
    " mv ",
    "boot_wlan",
    "qcwlanstate on",
    "qcwlanstate off",
    "/dev/esoc",
    "/dev/subsys",
    "/bind",
    "/unbind",
    "driver_override",
    "drivers_probe",
    "insmod",
    "rmmod",
    "modprobe",
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
    "reboot",
)

FORBIDDEN_ACTIONS = (
    "raw /dev/esoc* or /dev/subsys* open/ioctl",
    "GPIO/sysfs/debugfs write or GPIO export",
    "subsystem state write, bind/unbind, driver override, or module load/unload",
    "daemon start, service-manager start, Wi-Fi HAL start, or wlan.ko load",
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
    parser.add_argument("--v850-manifest", type=Path, default=DEFAULT_V850_MANIFEST)
    parser.add_argument("--allow-live-readonly", action="store_true")
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
            raise RuntimeError(f"forbidden V851 command term {term!r}: {' '.join(command)}")


def shell_cmd(args: argparse.Namespace, script: str) -> list[str]:
    return ["run", args.busybox, "sh", "-c", script]


def run_step(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    command: list[str],
    timeout: float | None = None,
) -> dict[str, Any]:
    validate_device_command(command)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    hide_item: dict[str, Any] | None = None
    if args.hide_on_busy and (capture.status == "busy" or "[busy]" in payload):
        hide_capture = run_capture(args, f"{name}-hide-on-busy", ["hide"], timeout=min(args.timeout, 8.0))
        hide_payload = redact(strip_cmdv1_text(hide_capture.text) if hide_capture.text else hide_capture.error + "\n")
        hide_item = capture_to_manifest(hide_capture)
        hide_item["payload"] = hide_payload
        hide_item["file"] = f"native/{safe_name(name)}-hide-on-busy.txt"
        hide_item["ok"] = hide_capture.ok
        store.write_text(hide_item["file"], hide_payload.rstrip() + "\n")
        capture = run_capture(args, name, command, timeout=timeout or args.timeout)
        payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    payload = redact(payload)
    item = capture_to_manifest(capture)
    item["payload"] = payload[:8192] + ("\n[truncated in manifest]\n" if len(payload) > 8192 else "")
    item["file"] = f"native/{safe_name(name)}.txt"
    item["ok"] = capture.ok
    if hide_item is not None:
        item["hide_on_busy"] = hide_item
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    if not args.allow_live_readonly:
        missing.append("--allow-live-readonly")
    if not args.assume_yes:
        missing.append("--assume-yes")
    return missing


def kallsyms_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; RE='{FOCUS_RE}'; "
        "printf '== kallsyms_focus ==\\n'; "
        "if [ -r /proc/kallsyms ]; then "
        "$BB grep -Ei \"$RE\" /proc/kallsyms 2>&1 | $BB head -n 240; "
        "else printf 'kallsyms_readable=0\\n'; fi; "
        "true"
    )


def interrupts_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; RE='mdm|esoc|sdx|ap2mdm|mdm2ap|gpio|tlmm|pmic|pm8150|mhi|pcie|icnss|wlan'; "
        "printf '== interrupts_focus ==\\n'; "
        "if [ -r /proc/interrupts ]; then "
        "$BB grep -Ei \"$RE\" /proc/interrupts 2>&1 | $BB head -n 240; "
        "else printf 'interrupts_readable=0\\n'; fi; "
        "true"
    )


def platform_surface_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "dump_file(){ f=\"$1\"; if [ -e \"$f\" ]; then printf 'FILE %s\\n' \"$f\"; "
        "if [ -r \"$f\" ]; then $BB cat \"$f\" 2>&1 | $BB head -c 1200; printf '\\n'; else printf 'UNREADABLE\\n'; fi; fi; }; "
        "dump_link(){ p=\"$1\"; printf 'LINK %s -> ' \"$p\"; $BB readlink \"$p\" 2>&1 || true; }; "
        "dump_path(){ p=\"$1\"; printf '== PATH %s ==\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; dump_link \"$p\"; "
        "if [ -d \"$p\" ]; then $BB ls -la \"$p\" 2>&1 | $BB head -n 120; fi; "
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
        "/sys/bus/msm_subsys/devices/subsys0; do dump_path \"$p\"; done; "
        "true"
    )


def devicetree_surface_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== mdm3_of_node ==\\n'; "
        "for root in /sys/firmware/devicetree/base /proc/device-tree; do "
        "[ -d \"$root\" ] || continue; "
        "for p in $($BB find \"$root\" -name 'qcom,mdm3' -print 2>/dev/null | $BB head -n 12); do "
        "printf '== DTNODE %s ==\\n' \"$p\"; $BB ls -la \"$p\" 2>&1 | $BB head -n 120; "
        "for f in compatible status qcom,mdm-link-info qcom,sysmon-id qcom,ssctl-instance-id "
        "qcom,mdm2ap-status-gpio qcom,ap2mdm-status-gpio qcom,ap2mdm-errfatal-gpio "
        "qcom,mdm2ap-errfatal-gpio qcom,ap2mdm-soft-reset-gpio qcom,mdm2ap-vddmin-gpio "
        "qcom,mdm-pmic-pwr-status-gpio interrupt-names interrupt-map interrupts; do "
        "if [ -r \"$p/$f\" ]; then printf 'DTPROP %s/%s hex=' \"$p\" \"$f\"; "
        "$BB od -An -tx1 \"$p/$f\" 2>&1 | $BB tr '\\n' ' ' | $BB head -c 800; printf '\\n'; fi; "
        "done; done; done; true"
    )


def module_surface_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== module_focus ==\\n'; "
        "for p in /sys/module/*esoc* /sys/module/*mdm* /sys/module/*mhi* /sys/module/*icnss* /sys/module/wlan /sys/module/gpiolib /sys/module/pinctrl*; do "
        "[ -e \"$p\" ] || continue; printf '== MODULE %s ==\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; "
        "for f in initstate refcnt taint version; do [ -e \"$p/$f\" ] && { printf 'FILE %s/%s\\n' \"$p\" \"$f\"; $BB cat \"$p/$f\" 2>&1 | $BB head -c 400; printf '\\n'; }; done; "
        "if [ -d \"$p/parameters\" ]; then printf 'PARAMETERS %s\\n' \"$p/parameters\"; $BB ls \"$p/parameters\" 2>&1 | $BB head -n 80; fi; "
        "if [ -d \"$p/holders\" ]; then printf 'HOLDERS %s\\n' \"$p/holders\"; $BB ls \"$p/holders\" 2>&1 | $BB head -n 80; fi; "
        "done; true"
    )


def gpio_pinctrl_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; RE='mdm|esoc|sdx|wlan|icnss|pmic|pm8150|135|142|141|53|gpio-9'; "
        "printf '== gpio_class ==\\n'; $BB ls -la /sys/class/gpio 2>&1 | $BB head -n 140 || true; "
        "for p in /sys/class/gpio/gpio9 /sys/class/gpio/gpio53 /sys/class/gpio/gpio135 /sys/class/gpio/gpio141 /sys/class/gpio/gpio142; do "
        "printf '== GPIO %s ==\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; "
        "for f in direction value active_low edge label base ngpio; do [ -r \"$p/$f\" ] && { printf 'FILE %s/%s\\n' \"$p\" \"$f\"; $BB cat \"$p/$f\" 2>&1 | $BB head -c 400; printf '\\n'; }; done; "
        "done; "
        "printf '== gpiochips ==\\n'; "
        "for p in /sys/class/gpio/gpiochip*; do [ -e \"$p\" ] || continue; printf 'GPIOCHIP %s\\n' \"$p\"; "
        "for f in label base ngpio; do [ -r \"$p/$f\" ] && { printf '%s=' \"$f\"; $BB cat \"$p/$f\" 2>&1 | $BB head -c 240; printf '\\n'; }; done; done; "
        "printf '== debug_gpio_focus ==\\n'; "
        "if [ -r /sys/kernel/debug/gpio ]; then printf 'GPIO_DEBUG readable=1\\n'; "
        "$BB grep -Ei \"$RE\" /sys/kernel/debug/gpio 2>&1 | $BB head -n 180 || true; else printf 'GPIO_DEBUG readable=0\\n'; fi; "
        "printf '== debug_pinctrl_focus ==\\n'; "
        "if [ -d /sys/kernel/debug/pinctrl ]; then printf 'PINCTRL_DEBUG present=1\\n'; "
        "for f in /sys/kernel/debug/pinctrl/*/pins /sys/kernel/debug/pinctrl/*/pinmux-pins /sys/kernel/debug/pinctrl/*/pinconf-pins /sys/kernel/debug/pinctrl/*/gpio-ranges; do "
        "[ -r \"$f\" ] || continue; printf 'PINCTRL_FILE %s\\n' \"$f\"; $BB grep -Ei \"$RE\" \"$f\" 2>&1 | $BB head -n 100 || true; done; "
        "else printf 'PINCTRL_DEBUG present=0\\n'; fi; "
        "true"
    )


def proc_devices_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== proc_devices_focus ==\\n'; $BB grep -Ei 'esoc|subsys|mdm|qrtr|qmi|wlan|diag|mhi' /proc/devices 2>&1 || true; "
        "printf '== dev_nodes_presence ==\\n'; "
        "$BB ls -ld /dev/* 2>&1 | $BB grep -Ei '/dev/(esoc|subsys|mdm|qrtr|qmi|wlan|qcwlanstate)' || true; "
        "true"
    )


def dmesg_focus_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; RE='{FOCUS_RE}|warning|panic|fatal|PBL|PON|vdd|min|pinctrl|tlmm'; "
        "printf '== dmesg_focus ==\\n'; "
        "$BB dmesg 2>&1 | $BB grep -Ei \"$RE\" | $BB tail -n 520 || true; true"
    )


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    steps: list[dict[str, Any]] = []
    run_step(args, store, steps, "version", ["version"], timeout=20.0)
    run_step(args, store, steps, "bootstatus", ["bootstatus"], timeout=20.0)
    run_step(args, store, steps, "selftest", ["selftest", "verbose"], timeout=20.0)
    run_step(args, store, steps, "kallsyms-focus", shell_cmd(args, kallsyms_script(args)), timeout=25.0)
    run_step(args, store, steps, "interrupts-focus", shell_cmd(args, interrupts_script(args)), timeout=20.0)
    run_step(args, store, steps, "platform-surface", shell_cmd(args, platform_surface_script(args)), timeout=30.0)
    run_step(args, store, steps, "devicetree-surface", shell_cmd(args, devicetree_surface_script(args)), timeout=30.0)
    run_step(args, store, steps, "module-surface", shell_cmd(args, module_surface_script(args)), timeout=25.0)
    run_step(args, store, steps, "gpio-pinctrl-surface", shell_cmd(args, gpio_pinctrl_script(args)), timeout=25.0)
    run_step(args, store, steps, "proc-devices", shell_cmd(args, proc_devices_script(args)), timeout=20.0)
    run_step(args, store, steps, "dmesg-focus", shell_cmd(args, dmesg_focus_script(args)), timeout=25.0)
    run_step(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=20.0)
    run_step(args, store, steps, "post-selftest", ["selftest", "verbose"], timeout=20.0)
    return steps


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


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


def analyze(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    kallsyms = step_payload(steps, "kallsyms-focus")
    interrupts = step_payload(steps, "interrupts-focus")
    platform = step_payload(steps, "platform-surface")
    devicetree = step_payload(steps, "devicetree-surface")
    modules = step_payload(steps, "module-surface")
    gpio = step_payload(steps, "gpio-pinctrl-surface")
    devices = step_payload(steps, "proc-devices")
    dmesg = step_payload(steps, "dmesg-focus")
    combined = "\n".join([kallsyms, interrupts, platform, devicetree, modules, gpio, devices, dmesg])
    return {
        "version_ok": args.expect_version in step_payload(steps, "version"),
        "bootstatus_ok": "BOOT OK" in step_payload(steps, "bootstatus"),
        "selftest_ok": "selftest: pass=" in step_payload(steps, "selftest") and "fail=0" in step_payload(steps, "selftest"),
        "post_bootstatus_ok": "BOOT OK" in step_payload(steps, "post-bootstatus"),
        "post_selftest_ok": "selftest: pass=" in step_payload(steps, "post-selftest") and "fail=0" in step_payload(steps, "post-selftest"),
        "all_steps_ok": all(bool(step.get("ok")) for step in steps),
        "step_status": {str(step.get("name")): bool(step.get("ok")) for step in steps},
        "mdm3_state": first_state(platform, ("mdm3", "subsys9", "esoc0")),
        "mss_state": first_state(platform, ("subsys0", "modem")),
        "symbols": {
            "mdm_subsys_powerup": symbol_present(kallsyms, "mdm_subsys_powerup"),
            "subsys_device_open": symbol_present(kallsyms, "subsys_device_open"),
            "__subsystem_get": symbol_present(kallsyms, "__subsystem_get"),
            "mhi_arch_esoc_ops_power_on": symbol_present(kallsyms, "mhi_arch_esoc_ops_power_on"),
            "mhi_pci_probe": symbol_present(kallsyms, "mhi_pci_probe"),
        },
        "irq_focus_lines": grep_lines(interrupts, r"mdm|esoc|sdx|gpio|tlmm|pmic|mhi|pcie|icnss|wlan", limit=80),
        "dmesg_hints": {
            "cannot_config_mdm_pmic_pwr_status": "cannot config mdm_pmic_pwr_status" in dmesg.lower(),
            "ap2mdm_errfatal2_remap": "ap2mdm_errfatal2" in dmesg.lower(),
            "mhi_seen": "mhi" in dmesg.lower(),
            "wlfw_seen": "wlfw" in dmesg.lower(),
            "wlan0_seen": "wlan0" in dmesg.lower(),
            "panic_or_fatal_seen": "panic" in dmesg.lower() or "fatal" in dmesg.lower(),
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
        "focused_lines": {
            "kallsyms": grep_lines(kallsyms, r"mdm_subsys_powerup|subsys_device_open|__subsystem_get|mhi_arch_esoc_ops_power_on|mhi_pci_probe", limit=40),
            "dmesg": grep_lines(dmesg, r"MDM_PMIC|AP2MDM|MDM2AP|mdm3|ext-mdm|esoc|mhi|wlfw|wlan0|fatal|panic", limit=80),
            "gpio_pinctrl": grep_lines(gpio, r"GPIO_DEBUG|PINCTRL|mdm|esoc|sdx|135|142|141|53|pm8150", limit=80),
        },
        "counts": count_patterns(combined),
    }


def build_checks(
    args: argparse.Namespace,
    v850: dict[str, Any],
    steps: list[dict[str, Any]],
    analysis: dict[str, Any],
    missing_flags: list[str],
) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "read-only ext-mdm provider surface plan; no device command executed",
            "next_step": "run with --allow-live-readonly --assume-yes",
        }]
    return [
        {
            "name": "live-readonly-flags",
            "status": "pass" if not missing_flags else "blocked",
            "detail": {"missing": missing_flags},
            "next_step": "supply explicit live-readonly flags",
        },
        {
            "name": "v850-route-ready",
            "status": "pass" if v850.get("pass") is True and v850.get("decision") == EXPECTED_V850 else "blocked",
            "detail": {"decision": v850.get("decision"), "pass": v850.get("pass")},
            "next_step": "refresh V850 classifier before V851 live snapshot",
        },
        {
            "name": "runtime-health-prepost",
            "status": "pass" if all(analysis.get(key) for key in ("version_ok", "bootstatus_ok", "selftest_ok", "post_bootstatus_ok", "post_selftest_ok")) else "blocked",
            "detail": {
                "version_ok": analysis.get("version_ok"),
                "bootstatus_ok": analysis.get("bootstatus_ok"),
                "selftest_ok": analysis.get("selftest_ok"),
                "post_bootstatus_ok": analysis.get("post_bootstatus_ok"),
                "post_selftest_ok": analysis.get("post_selftest_ok"),
            },
            "next_step": "restore healthy native v724 before interpreting ext-mdm provider surface",
        },
        {
            "name": "read-only-command-success",
            "status": "pass" if analysis.get("all_steps_ok") else "blocked",
            "detail": analysis.get("step_status"),
            "next_step": "fix bridge/runtime read failures before selecting a provider action",
        },
        {
            "name": "provider-symbol-surface",
            "status": "pass" if (analysis.get("symbols") or {}).get("mdm_subsys_powerup") else "finding",
            "detail": analysis.get("symbols"),
            "next_step": "use symbol surface for public-source cross-reference; do not patch kernel",
        },
        {
            "name": "provider-runtime-surface",
            "status": "pass" if (analysis.get("surface") or {}).get("mdm3_sysfs_present") and (analysis.get("surface") or {}).get("esoc0_sysfs_present") else "blocked",
            "detail": {
                "mdm3_state": analysis.get("mdm3_state"),
                "mss_state": analysis.get("mss_state"),
                "surface": analysis.get("surface"),
                "dmesg_hints": analysis.get("dmesg_hints"),
            },
            "next_step": "compare with Android provider surface before considering any GPIO or eSoC write",
        },
        {
            "name": "below-upper-wifi-contract",
            "status": "pass",
            "detail": {
                "raw_esoc_open_executed": False,
                "gpio_write_executed": False,
                "sysfs_write_executed": False,
                "wifi_hal_start_executed": False,
                "scan_connect_executed": False,
                "external_ping_executed": False,
            },
            "next_step": "keep upper Wi-Fi blocked until mdm3/WLFW/BDF/wlan0 exists",
        },
    ]


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v851-ext-mdm-provider-surface-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V851 live read-only provider surface snapshot",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v851-ext-mdm-provider-surface-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "restore live read-only evidence before selecting the next ext-mdm gate",
        )
    if analysis.get("mdm3_state") == "ONLINE":
        return (
            "v851-mdm3-online-provider-surface-captured",
            True,
            "read-only snapshot found mdm3 ONLINE; route next gate to WLFW/service69 readiness",
            "capture WLFW/service69/BDF readiness before HAL/connect",
        )
    if (analysis.get("symbols") or {}).get("mdm_subsys_powerup"):
        return (
            "v851-ext-mdm-provider-surface-captured",
            True,
            "captured live read-only provider symbol, IRQ, sysfs, GPIO/pinctrl, and dmesg surface while mdm3 remains below ONLINE",
            "V852 should capture the same provider surface from Android for GPIO/IRQ/PMIC/pinctrl delta comparison",
        )
    return (
        "v851-ext-mdm-provider-surface-limited",
        True,
        "captured live read-only provider surface, but kallsyms did not expose mdm_subsys_powerup",
        "V852 should use Android comparison and existing V849 stack evidence to narrow GPIO/PMIC prerequisites",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v850 = load_json(args.v850_manifest)
    missing_flags = required_flags(args) if args.command == "run" else []
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    if args.command == "run" and not missing_flags:
        steps = collect_steps(args, store)
        analysis = analyze(args, steps)
    checks = build_checks(args, v850, steps, analysis, missing_flags)
    decision, pass_ok, reason, next_step = decide(args, checks, analysis)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v851",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v850_manifest": str(resolve(args.v850_manifest)),
            "v850_decision": v850.get("decision"),
            "v850_pass": v850.get("pass"),
            "expect_version": args.expect_version,
        },
        "steps": steps,
        "analysis": analysis,
        "checks": checks,
        "device_commands_executed": args.command == "run" and not missing_flags,
        "device_mutations": False,
        "live_readonly": args.command == "run" and not missing_flags,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "reboot_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "qmi_payload_executed": False,
        "raw_esoc_open_executed": False,
        "subsys_char_open_executed": False,
        "gpio_write_executed": False,
        "sysfs_write_executed": False,
        "debugfs_write_executed": False,
        "bind_unbind_executed": False,
        "module_load_unload_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    analysis = manifest.get("analysis", {})
    analysis_rows = [
        [key, json.dumps(value, ensure_ascii=False, sort_keys=True)]
        for key, value in analysis.items()
        if key not in {"step_status", "focused_lines", "irq_focus_lines"}
    ]
    step_rows = [
        [str(step.get("name")), str(step.get("ok")), str(step.get("status")), str(step.get("file"))]
        for step in manifest.get("steps", [])
    ]
    focused = analysis.get("focused_lines") or {}
    focus_lines = []
    for group, lines in focused.items():
        focus_lines.append(f"### {group}")
        focus_lines.extend(f"- `{line}`" for line in list(lines)[:24])
        if not lines:
            focus_lines.append("- none")
    return "\n".join([
        "# V851 ext-mdm Provider Surface Snapshot",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- raw_esoc_open_executed: `{manifest['raw_esoc_open_executed']}`",
        f"- subsys_char_open_executed: `{manifest['subsys_char_open_executed']}`",
        f"- gpio_write_executed: `{manifest['gpio_write_executed']}`",
        f"- sysfs_write_executed: `{manifest['sysfs_write_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], checks),
        "",
        "## Analysis",
        "",
        markdown_table(["signal", "value"], analysis_rows),
        "",
        "## Focused Lines",
        "",
        "\n".join(focus_lines) or "- none",
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
    print(f"raw_esoc_open_executed: {manifest['raw_esoc_open_executed']}")
    print(f"subsys_char_open_executed: {manifest['subsys_char_open_executed']}")
    print(f"gpio_write_executed: {manifest['gpio_write_executed']}")
    print(f"sysfs_write_executed: {manifest['sysfs_write_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
