#!/usr/bin/env python3
"""V913 Android read-only eSoC GPIO timeline collector.

This runner is intended for a normal Android boot with ADB available. It
captures bounded, read-only evidence for the external MDM3 / SDX50M eSoC boot
timeline before the native-init V912-derived subsystem trigger is attempted.
It does not enable Wi-Fi, scan/connect, route traffic, ping externally, open
eSoC/subsystem device nodes, or write sysfs/debugfs/GPIO state.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v913-android-esoc-gpio-timeline")
LATEST_POINTER = Path("tmp/wifi/latest-v913-android-esoc-gpio-timeline.txt")
DEFAULT_TIMEOUT = 45.0

FOCUS_RE = (
    "mdm3|ext-mdm|sdx50|esoc|ap2mdm|mdm2ap|gpio|pmic|pm8150|pon|pbl|"
    "mhi_arch_esoc_ops_power_on|mhi_pci_probe|mhi_0305|msm_pcie|pcie|"
    "subsys_device_open|__subsystem_get|mdm_subsys_powerup|mdm_helper|"
    " ks |/vendor/bin/ks|wlan_pd|wlfw|BDF|bdwlan|regdb|wlan0|icnss|cnss"
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
        "for svc in ueventd vendor.per_mgr vendor.mdm_helper cnss-daemon cnss_diag vendor.qrtr-ns "
        "rmt_storage tftp_server vendor.wifi_hal_ext wificond; do "
        "printf 'init.svc.%s=' \"$svc\"; getprop \"init.svc.$svc\"; done"
    )


def dmesg_script() -> str:
    return "dmesg 2>&1"


def dmesg_focus_script() -> str:
    return f"RE='{FOCUS_RE}'; dmesg 2>&1 | grep -Ei \"$RE\" | tail -n 1200 || true"


def interrupts_script() -> str:
    return (
        "RE='mdm|esoc|sdx|ap2mdm|mdm2ap|gpio|tlmm|pmic|pm8150|mhi|pcie|icnss|wlan'; "
        "printf '== interrupts_focus ==\\n'; "
        "if [ -r /proc/interrupts ]; then grep -Ei \"$RE\" /proc/interrupts 2>&1 | head -n 320; "
        "else printf 'interrupts_readable=0\\n'; fi"
    )


def subsys_state_script() -> str:
    return (
        "printf '== subsys_state ==\\n'; "
        "for p in /sys/bus/msm_subsys/devices/subsys9 "
        "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9 "
        "/sys/bus/esoc/devices/esoc0 "
        "/sys/devices/platform/soc/soc:qcom,mdm3/esoc0; do "
        "printf 'PATH %s\\n' \"$p\"; ls -ld \"$p\" 2>&1 || true; "
        "for f in name state crash_count restart_level firmware_name uevent power/runtime_status; do "
        "[ -r \"$p/$f\" ] && { printf 'FILE %s/%s\\n' \"$p\" \"$f\"; cat \"$p/$f\" 2>&1 | head -c 1200; printf '\\n'; }; "
        "done; done"
    )


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
        "grep -Ei \"$RE\" /sys/kernel/debug/gpio 2>&1 | head -n 260 || true; "
        "else printf 'GPIO_DEBUG readable=0\\n'; fi"
    )


def process_fd_script() -> str:
    return (
        "printf '== process_focus ==\\n'; "
        "ps -AZ 2>&1 | grep -Ei 'mdm_helper|/vendor/bin/ks| per_mgr|pm-service|ueventd|cnss|wlan|wifi|rmt|tftp|qrtr' | head -n 260 || true; "
        "printf '== bounded_fd_focus ==\\n'; "
        "for d in /proc/[0-9]*; do "
        "pid=${d##*/}; comm=$(cat \"$d/comm\" 2>/dev/null); cmd=$(tr '\\000' ' ' < \"$d/cmdline\" 2>/dev/null); "
        "case \"$comm $cmd\" in *mdm_helper*|*/vendor/bin/ks*|*pm-service*|*per_mgr*|*cnss*|*wlan*|*wifi*) "
        "attr=$(cat \"$d/attr/current\" 2>/dev/null); "
        "printf 'PROC pid=%s comm=%s attr=%s cmd=%s\\n' \"$pid\" \"$comm\" \"$attr\" \"$cmd\"; "
        "[ -d \"$d/fd\" ] && ls -lZ \"$d/fd\" 2>/dev/null | grep -Ei '/dev/(esoc|subsys|mhi|wlan|qcwlanstate)' | head -n 80 || true; "
        ";; esac; done"
    )


def dmesg_time(line: str) -> float | None:
    match = TIME_RE.search(line)
    return float(match.group("time")) if match else None


def first_timed_line(lines: list[str], pattern: str) -> dict[str, Any]:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in lines:
        if line.lstrip().startswith("$ "):
            continue
        if regex.search(line):
            return {"present": True, "time": dmesg_time(line), "line": line.strip()}
    return {"present": False, "time": None, "line": ""}


def matching_lines(text: str, pattern: str, limit: int = 80) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    results: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line in seen:
            continue
        if regex.search(line):
            seen.add(line)
            results.append(line)
            if len(results) >= limit:
                break
    return results


def parse_irq_line(text: str) -> dict[str, Any]:
    for line in text.splitlines():
        lowered = line.lower()
        if "mdm status" not in lowered and "gpio 142" not in lowered and "gpio142" not in lowered:
            continue
        match = IRQ_RE.search(line)
        if not match:
            continue
        counts = [int(value) for value in match.group("counts").split()]
        return {
            "present": True,
            "line": line.strip(),
            "irq": int(match.group("irq")),
            "controller": match.group("controller"),
            "gpio": int(match.group("gpio")),
            "trigger": match.group("trigger"),
            "name": match.group("name").strip(),
            "count_total": sum(counts),
        }
    return {"present": False, "line": "", "count_total": 0}


def parse_props(text: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            props[key] = value.strip()
    return props


def process_has_current_ks(process_text: str) -> bool:
    for line in process_text.splitlines():
        if not line.startswith("PROC "):
            continue
        if re.search(r"\bcomm=ks\b|cmd=/vendor/bin/ks(?:\s|$)", line):
            return True
    return False


def process_has_mhi_pipe(process_text: str) -> bool:
    for line in process_text.splitlines():
        if line.lstrip().startswith("$ "):
            continue
        if re.search(r"->\s*/dev/mhi_0305_01\.01\.00_pipe_10\b|/dev/mhi_0305_01\.01\.00_pipe_10\b", line):
            return True
    return False


def classify(captures: dict[str, Capture]) -> dict[str, Any]:
    dmesg_text = captures.get("dmesg-full", Capture("", "", False, None, "", 0.0, "", "", "")).text
    focus_text = captures.get("dmesg-focus", Capture("", "", False, None, "", 0.0, "", "", "")).text
    interrupts_text = captures.get("interrupts", Capture("", "", False, None, "", 0.0, "", "", "")).text
    props_text = captures.get("props", Capture("", "", False, None, "", 0.0, "", "", "")).text
    process_text = captures.get("process-fd", Capture("", "", False, None, "", 0.0, "", "", "")).text
    subsys_text = captures.get("subsys-state", Capture("", "", False, None, "", 0.0, "", "", "")).text
    gpio_text = captures.get("gpio", Capture("", "", False, None, "", 0.0, "", "", "")).text

    timeline_source = focus_text if focus_text.strip() else dmesg_text
    lines = timeline_source.splitlines()
    timeline = {
        "ap2mdm_status": first_timed_line(lines, r"ap2mdm|gpio\s*135|gpio135"),
        "pmic_gpio9_or_reset": first_timed_line(lines, r"pmic.*gpio.*9|gpio.*9.*pmic|pm8150|pon|pbl|reset|de-assert|deassert"),
        "mdm2ap_gpio142": first_timed_line(lines, r"mdm2ap|gpio\s*142|gpio142|mdm status"),
        "pcie_link": first_timed_line(
            lines,
            r"LTSSM_L0|link initialized|msm_pcie.*(?:link|enable|RC)|mhi_pci_probe|mhi_arch_esoc_ops_power_on",
        ),
        "mdm3_online": first_timed_line(lines, r"mdm3.*ONLINE|subsys.*mdm3.*ONLINE"),
        "ks": first_timed_line(lines, r"/vendor/bin/ks|\bks\b|mhi_0305"),
        "mhi_pipe": first_timed_line(lines, r"mhi_0305|pipe_10|mhi"),
        "wlan_pd": first_timed_line(lines, r"wlan_pd|service-notifier.*74|service-notifier.*180"),
        "wlfw": first_timed_line(lines, r"wlfw|service\s+69"),
        "bdf": first_timed_line(lines, r"BDF file|bdwlan\.bin|regdb\.bin"),
        "wlan0": first_timed_line(lines, r"\bwlan0\b"),
    }
    irq = parse_irq_line(interrupts_text)
    props = parse_props(props_text)
    mdm3_state_online = bool(re.search(r"state\s*\n?ONLINE|FILE .*subsys9/state\s*\nONLINE", subsys_text, re.IGNORECASE))
    ks_observed = process_has_current_ks(process_text)
    mhi_observed = process_has_mhi_pipe(process_text)
    gpio_debug_readable = "GPIO_DEBUG readable=1" in gpio_text
    upper_wifi_positive = (
        props.get("sys.boot_completed") == "1"
        and timeline["wlan_pd"]["present"]
        and timeline["wlfw"]["present"]
        and timeline["bdf"]["present"]
        and timeline["wlan0"]["present"]
    )
    positive_markers = {
        "boot_completed": props.get("sys.boot_completed") == "1",
        "upper_wifi_positive": upper_wifi_positive,
        "mdm3_online": mdm3_state_online or timeline["mdm3_online"]["present"],
        "gpio142_irq_positive": irq.get("count_total", 0) > 0,
        "pcie_link": timeline["pcie_link"]["present"],
        "ks_observed": ks_observed or timeline["ks"]["present"],
        "mhi_observed": mhi_observed or timeline["mhi_pipe"]["present"],
        "wlfw": timeline["wlfw"]["present"],
        "bdf": timeline["bdf"]["present"],
        "wlan0": timeline["wlan0"]["present"],
    }
    if upper_wifi_positive:
        decision = "v913-android-upper-wifi-positive-lower-gpio-postboot-negative"
        pass_ok = True
        reason = (
            "Android boot proves WLAN-PD, WLFW, BDF, and wlan0 despite post-boot "
            "mdm3/GPIO142/MHI markers not being positive; do not require those sampled lower markers for V912 success."
        )
        next_step = "Run the post-V913 route classifier and adjust V912-derived native trigger success criteria before live subsystem-open."
    else:
        decision = "v913-android-esoc-gpio-timeline-incomplete"
        pass_ok = False
        reason = "Android read-only capture did not prove the complete GPIO/eSoC positive timeline."
        next_step = "Review missing Android timeline markers before native subsystem trigger."

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "timeline": timeline,
        "irq": irq,
        "props": props,
        "positive_markers": positive_markers,
        "gpio_debug_readable": gpio_debug_readable,
        "selected_lines": {
            "gpio": matching_lines(gpio_text, r"mdm|esoc|sdx|135|142|gpio-9|pmic|pm8150", limit=40),
            "process_fd": matching_lines(process_text, r"mdm_helper|/vendor/bin/ks|mhi_0305|/dev/esoc|/dev/subsys", limit=60),
            "dmesg": matching_lines(
                timeline_source,
                r"mdm3|esoc|ap2mdm|mdm2ap|gpio|pmic|mhi|pcie|wlan_pd|wlfw|BDF|wlan0",
                limit=80,
            ),
        },
    }


def build_summary(manifest: dict[str, Any]) -> str:
    classification = manifest.get("classification") or {}
    timeline = classification.get("timeline") or {}
    rows = []
    for name, data in timeline.items():
        rows.append([name, str(data.get("present")), str(data.get("time")), data.get("line", "")[:160]])
    marker_rows = [
        [key, str(value)] for key, value in (classification.get("positive_markers") or {}).items()
    ]
    return "\n".join(
        [
            "# V913 Android eSoC GPIO Timeline Summary",
            "",
            f"decision: {manifest.get('decision')}",
            f"pass: {manifest.get('pass')}",
            f"reason: {manifest.get('reason')}",
            f"next: {manifest.get('next_step')}",
            "",
            "## Positive Markers",
            "",
            markdown_table(["marker", "value"], marker_rows),
            "",
            "## Timeline",
            "",
            markdown_table(["marker", "present", "time", "line"], rows),
            "",
            "## IRQ",
            "",
            "```json",
            json.dumps(classification.get("irq") or {}, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )


def write_outputs(store: EvidenceStore, manifest: dict[str, Any]) -> None:
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")


def run_plan_or_preflight(args: argparse.Namespace, store: EvidenceStore, devices: dict[str, Any]) -> int:
    android_available = selected_device_available(args, devices)
    if args.command == "plan":
        decision = "v913-android-esoc-gpio-timeline-plan-ready"
        pass_ok = True
        reason = "plan only; no ADB shell command executed"
    elif android_available:
        decision = "v913-android-esoc-gpio-timeline-preflight-ready"
        pass_ok = True
        reason = "exactly one selected Android ADB device is available"
    else:
        decision = "v913-android-adb-unavailable"
        pass_ok = False
        reason = "selected Android ADB device is not available"
    manifest = {
        "schema": "v913-android-esoc-gpio-timeline",
        "created_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": "boot Android and rerun V913 run" if not pass_ok else "run V913 capture on Android boot",
        "host": collect_host_metadata(),
        "adb_devices": devices,
        "guardrails": guardrails(),
    }
    write_outputs(store, manifest)
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"evidence: {store.run_dir}")
    return 0 if pass_ok or args.command == "plan" else 2


def guardrails() -> dict[str, bool]:
    return {
        "adb_shell_read_only": True,
        "native_subsys_trigger_executed": False,
        "esoc_ioctl_executed": False,
        "gpio_write_executed": False,
        "sysfs_write_executed": False,
        "debugfs_write_executed": False,
        "module_load_unload_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_linkup": False,
        "credentials_used": False,
        "dhcp_routing": False,
        "external_ping": False,
        "boot_image_write": False,
        "partition_write": False,
    }


def run_capture(args: argparse.Namespace, store: EvidenceStore, devices: dict[str, Any]) -> int:
    if not selected_device_available(args, devices):
        return run_plan_or_preflight(args, store, devices)

    capture_specs = [
        ("props", props_script(), 12.0),
        ("dmesg-full", dmesg_script(), 25.0),
        ("dmesg-focus", dmesg_focus_script(), 25.0),
        ("interrupts", interrupts_script(), 12.0),
        ("subsys-state", subsys_state_script(), 12.0),
        ("gpio", gpio_script(), 16.0),
        ("process-fd", process_fd_script(), 18.0),
    ]
    captures: dict[str, Capture] = {}
    for name, shell_command, timeout in capture_specs:
        captures[name] = capture_shell(args, store, name, shell_command, timeout)
    classification = classify(captures)
    manifest = {
        "schema": "v913-android-esoc-gpio-timeline",
        "created_at": now_iso(),
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
    write_outputs(store, manifest)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 2


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    devices = adb_devices(args)
    if args.command in {"plan", "preflight"}:
        return run_plan_or_preflight(args, store, devices)
    return run_capture(args, store, devices)


if __name__ == "__main__":
    raise SystemExit(main())
