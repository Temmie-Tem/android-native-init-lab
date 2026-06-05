#!/usr/bin/env python3
"""V1241 SDX50M debugfs prerequisite observer.

This follows V1240.  It mounts debugfs only when explicitly allowed and only
to read GPIO, pinctrl, regulator, IRQ, and PCIe debug surfaces.  It must not
open raw eSoC/subsys device nodes, write GPIO/sysfs/debugfs controls, start
Wi-Fi actors, scan/connect, use credentials, DHCP/route, external ping, reboot,
flash, or write any partition.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1241-sdx50m-debugfs-prereq-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1241-sdx50m-debugfs-prereq-live.txt")
DEFAULT_V1240_MANIFEST = Path("tmp/wifi/v1240-sdx50m-response-surface-live/manifest.json")
EXPECTED_V1240 = "v1240-response-inputs-visible-mdm2ap-silent"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEBUGFS_ROOT = "/sys/kernel/debug"
FORBIDDEN_OUTPUT_ENV_KEYS = ("A90_WIFI_SSID", "A90_WIFI_PSK")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
SECRET_RE = re.compile(r"(made by|creator: made by) [^\r\n]+", re.IGNORECASE)
IRQ_RE = re.compile(
    r"^\s*(?P<irq>\d+):(?P<counts>(?:\s+\d+)+)\s+(?P<controller>\S+)\s+(?P<gpio>\d+)\s+(?P<trigger>\S+)\s+(?P<name>.+?)\s*$",
    re.MULTILINE,
)

FORBIDDEN_TERMS = (
    " echo ",
    " tee ",
    " dd ",
    " mknod ",
    " rm ",
    " rmdir ",
    " chmod ",
    " chown ",
    " cp ",
    " mv ",
    "boot_wlan",
    "qcwlanstate on",
    "qcwlanstate off",
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
    "/dev/esoc-0",
    "/dev/subsys_esoc0",
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
    parser.add_argument("--v1240-manifest", type=Path, default=DEFAULT_V1240_MANIFEST)
    parser.add_argument("--allow-live-readonly", action="store_true")
    parser.add_argument("--allow-temp-debugfs", action="store_true")
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


def validate_device_command(name: str, command: list[str]) -> None:
    if name == "debugfs-mount" and command == ["run", DEFAULT_BUSYBOX, "mount", "-t", "debugfs", "debugfs", DEBUGFS_ROOT]:
        return
    if name == "debugfs-umount" and command == ["run", DEFAULT_BUSYBOX, "umount", DEBUGFS_ROOT]:
        return
    joined = " " + " ".join(command).lower() + " "
    if " mount " in joined or " umount " in joined:
        raise RuntimeError(f"forbidden non-debugfs mount command: {' '.join(command)}")
    for term in FORBIDDEN_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden V1241 command term {term!r}: {' '.join(command)}")


def shell_cmd(args: argparse.Namespace, script: str) -> list[str]:
    return ["run", args.busybox, "sh", "-c", script]


def run_step(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    command: list[str],
    timeout: float | None = None,
    allow_error: bool = False,
) -> dict[str, Any]:
    validate_device_command(name, command)
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
    item["ok"] = bool(capture.ok or allow_error)
    item["raw_ok"] = bool(capture.ok)
    if hide_item is not None:
        item["hide_on_busy"] = hide_item
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    if not args.allow_live_readonly:
        missing.append("--allow-live-readonly")
    if not args.allow_temp_debugfs:
        missing.append("--allow-temp-debugfs")
    if not args.assume_yes:
        missing.append("--assume-yes")
    return missing


def proc_mounts_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return f"BB={bb}; $BB cat /proc/mounts 2>&1 | $BB grep -E 'debugfs|tracefs|sysfs|proc' || true"


def debug_gpio_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== debugfs-root ==\\n'; $BB ls -ld /sys/kernel/debug 2>&1 || true; "
        "printf '== debug-gpio-focus ==\\n'; "
        "if [ -r /sys/kernel/debug/gpio ]; then "
        "printf 'GPIO_DEBUG readable=1\\n'; "
        "$BB cat /sys/kernel/debug/gpio 2>&1 | $BB grep -Ei 'gpio-(9|53|87|135|141|142)|mdm|ap2mdm|mdm2ap|esoc|sdx|pcie|wlan|pm8150' | $BB head -220 || true; "
        "else printf 'GPIO_DEBUG readable=0\\n'; $BB ls -la /sys/kernel/debug 2>&1 | $BB head -120 || true; fi; "
        "printf '== pinctrl-focus ==\\n'; "
        "if [ -d /sys/kernel/debug/pinctrl ]; then "
        "printf 'PINCTRL_DEBUG present=1\\n'; "
        "for f in /sys/kernel/debug/pinctrl/*/pins /sys/kernel/debug/pinctrl/*/pinmux-pins /sys/kernel/debug/pinctrl/*/pinconf-pins /sys/kernel/debug/pinctrl/*/gpio-ranges; do "
        "[ -r \"$f\" ] || continue; printf 'PINCTRL_FILE %s\\n' \"$f\"; "
        "$BB grep -Ei 'gpio-(9|53|87|135|141|142)|\\b(9|53|87|135|141|142)\\b|mdm|ap2mdm|mdm2ap|esoc|sdx|pcie|wlan|pm8150' \"$f\" 2>&1 | $BB head -120 || true; "
        "done; "
        "else printf 'PINCTRL_DEBUG present=0\\n'; fi; "
        "true"
    )


def debug_regulator_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== debug-regulator ==\\n'; "
        "for f in /sys/kernel/debug/regulator/regulator_summary /sys/kernel/debug/regulator_summary; do "
        "printf 'REGDEBUG %s\\n' \"$f\"; "
        "if [ -r \"$f\" ]; then $BB cat \"$f\" 2>&1 | $BB grep -Ei 'mdm|sdx|pcie|wlan|pm8150|pm8150l|vreg|s4|s5|l5|l9|l12|l13|l14' | $BB head -260 || true; else $BB ls -la \"$f\" 2>&1 || true; fi; "
        "done; true"
    )


def debug_irq_pcie_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== irq-debug-focus ==\\n'; "
        "for p in /sys/kernel/debug/irq/irqs/290 /sys/kernel/debug/irq/irqs/252 /sys/kernel/debug/irq/irqs/204; do "
        "printf 'IRQPATH %s\\n' \"$p\"; $BB ls -la \"$p\" 2>&1 | $BB head -60 || true; "
        "for f in name chip_name type wake_depth actions; do [ -r \"$p/$f\" ] && { printf 'FILE %s/%s\\n' \"$p\" \"$f\"; $BB cat \"$p/$f\" 2>&1 | $BB head -c 800; printf '\\n'; }; done; "
        "done; "
        "printf '== pcie-debug-focus ==\\n'; "
        "for p in /sys/devices/platform/soc/1c08000.qcom,pcie/debug /sys/kernel/debug/pci_msm /sys/kernel/debug/msm_pcie; do "
        "printf 'PCIEDEBUG %s\\n' \"$p\"; $BB ls -la \"$p\" 2>&1 | $BB head -100 || true; "
        "for f in \"$p\"/*; do [ -r \"$f\" ] || continue; case \"$f\" in *enumerate*|*trigger*|*reset*) continue;; esac; "
        "printf 'PCIEFILE %s\\n' \"$f\"; $BB cat \"$f\" 2>&1 | $BB head -c 1000; printf '\\n'; done; "
        "done; true"
    )


def interrupts_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== interrupts-focus ==\\n'; "
        "$BB grep -Ei 'mdm status|mdm errfatal|pcie|mhi|wlan|icnss|gpio|sdx|esoc' /proc/interrupts 2>&1 | $BB head -280 || true; true"
    )


def post_health_steps(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    run_step(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=20.0)
    run_step(args, store, steps, "post-selftest", ["selftest", "verbose"], timeout=20.0)
    run_step(args, store, steps, "post-netservice-status", ["netservice", "status"], timeout=20.0)


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def debugfs_mounted(text: str) -> bool:
    return re.search(rf"\s{re.escape(DEBUGFS_ROOT)}\s+debugfs\s", text) is not None


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    store.mkdir("native")
    steps: list[dict[str, Any]] = []
    run_step(args, store, steps, "version", ["version"], timeout=20.0)
    run_step(args, store, steps, "bootstatus", ["bootstatus"], timeout=20.0)
    run_step(args, store, steps, "selftest", ["selftest", "verbose"], timeout=20.0)
    run_step(args, store, steps, "proc-mounts-before", shell_cmd(args, proc_mounts_script(args)), timeout=15.0)
    mounted_before = debugfs_mounted(step_payload(steps, "proc-mounts-before"))
    mounted_by_v1241 = False
    if not mounted_before:
        run_step(args, store, steps, "debugfs-mount", ["run", args.busybox, "mount", "-t", "debugfs", "debugfs", DEBUGFS_ROOT], timeout=20.0)
        mounted_by_v1241 = bool((steps[-1] or {}).get("raw_ok"))
    run_step(args, store, steps, "proc-mounts-during", shell_cmd(args, proc_mounts_script(args)), timeout=15.0)
    run_step(args, store, steps, "debug-gpio-pinctrl", shell_cmd(args, debug_gpio_script(args)), timeout=25.0)
    run_step(args, store, steps, "debug-regulator", shell_cmd(args, debug_regulator_script(args)), timeout=25.0)
    run_step(args, store, steps, "debug-irq-pcie", shell_cmd(args, debug_irq_pcie_script(args)), timeout=25.0)
    run_step(args, store, steps, "interrupts-focus", shell_cmd(args, interrupts_script(args)), timeout=20.0)
    if mounted_by_v1241:
        run_step(args, store, steps, "debugfs-umount", ["run", args.busybox, "umount", DEBUGFS_ROOT], timeout=20.0, allow_error=True)
    run_step(args, store, steps, "proc-mounts-after", shell_cmd(args, proc_mounts_script(args)), timeout=15.0)
    post_health_steps(args, store, steps)
    return steps, {"mounted_before": mounted_before, "mounted_by_v1241": mounted_by_v1241}


def find_lines(text: str, pattern: str) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    return [line.strip() for line in text.splitlines() if regex.search(line)]


def parse_line_level(line: str) -> str:
    lowered = line.lower()
    if re.search(r"\bhi\b|high|=\s*1\b", lowered):
        return "high"
    if re.search(r"\blo\b|low|=\s*0\b", lowered):
        return "low"
    return ""


def parse_irq_line(text: str, label: str) -> dict[str, Any]:
    for line in text.splitlines():
        if label.lower() not in line.lower():
            continue
        match = IRQ_RE.search(line)
        if not match:
            continue
        counts = [int(value) for value in match.group("counts").split()]
        return {
            "present": True,
            "line": line.strip(),
            "irq": int(match.group("irq")),
            "gpio": int(match.group("gpio")),
            "trigger": match.group("trigger"),
            "name": match.group("name").strip(),
            "count_total": sum(counts),
        }
    return {"present": False, "line": "", "count_total": 0}


def analyze(args: argparse.Namespace, steps: list[dict[str, Any]], v1240: dict[str, Any], mount_info: dict[str, Any]) -> dict[str, Any]:
    mounts_during = step_payload(steps, "proc-mounts-during")
    mounts_after = step_payload(steps, "proc-mounts-after")
    gpio = step_payload(steps, "debug-gpio-pinctrl")
    regulator = step_payload(steps, "debug-regulator")
    irq_pcie = step_payload(steps, "debug-irq-pcie")
    interrupts = step_payload(steps, "interrupts-focus")
    ap2mdm_lines = find_lines(gpio, r"gpio-135|gpio_135|pin 135|pinctrl:135|ap2mdm")
    mdm2ap_lines = find_lines(gpio, r"gpio-142|gpio_142|pin 142|pinctrl:142|mdm2ap|mdm status")
    soft_reset_lines = find_lines(gpio, r"gpio-9|gpio_9|pin 9|pm8150l.*gpio9|soft.?reset|pm8150.*9")
    pcie_debug_lines = find_lines(irq_pcie, r"pcie|link|ltssm|l0|gen2|rc1")
    regulator_focus_lines = find_lines(regulator, r"mdm|sdx|pcie|wlan|pm8150")
    return {
        "version_ok": args.expect_version in step_payload(steps, "version"),
        "bootstatus_ok": "BOOT OK" in step_payload(steps, "bootstatus"),
        "selftest_ok": "fail=0" in step_payload(steps, "selftest"),
        "post_bootstatus_ok": "BOOT OK" in step_payload(steps, "post-bootstatus"),
        "post_selftest_ok": "fail=0" in step_payload(steps, "post-selftest"),
        "post_netservice_stopped": "enabled=no" in step_payload(steps, "post-netservice-status") and "tcpctl=stopped" in step_payload(steps, "post-netservice-status"),
        "all_steps_ok": all(bool(step.get("ok")) for step in steps),
        "step_status": {str(step.get("name")): bool(step.get("ok")) for step in steps},
        "v1240_decision": v1240.get("decision"),
        "v1240_pass": bool(v1240.get("pass")),
        "mounted_before": bool(mount_info.get("mounted_before")),
        "mounted_by_v1241": bool(mount_info.get("mounted_by_v1241")),
        "mounted_during": debugfs_mounted(mounts_during),
        "mounted_after": debugfs_mounted(mounts_after),
        "cleanup_ok": bool(mount_info.get("mounted_before")) or not debugfs_mounted(mounts_after),
        "gpio_debug_readable": "GPIO_DEBUG readable=1" in gpio,
        "pinctrl_debug_present": "PINCTRL_DEBUG present=1" in gpio,
        "ap2mdm_lines": ap2mdm_lines[:20],
        "mdm2ap_lines": mdm2ap_lines[:20],
        "soft_reset_lines": soft_reset_lines[:20],
        "pinctrl_ap2mdm_seen": bool(ap2mdm_lines),
        "pinctrl_mdm2ap_seen": bool(mdm2ap_lines),
        "pinctrl_soft_reset_seen": bool(soft_reset_lines),
        "ap2mdm_level_guess": parse_line_level(" ".join(ap2mdm_lines)),
        "mdm2ap_level_guess": parse_line_level(" ".join(mdm2ap_lines)),
        "soft_reset_level_guess": parse_line_level(" ".join(soft_reset_lines)),
        "mdm_status_irq": parse_irq_line(interrupts, "mdm status"),
        "pcie_debug_line_count": len(pcie_debug_lines),
        "pcie_debug_sample": pcie_debug_lines[:20],
        "regulator_focus_line_count": len(regulator_focus_lines),
        "regulator_focus_sample": regulator_focus_lines[:20],
    }


def build_checks(command: str, missing: list[str], analysis: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{"name": "plan-only", "status": "pass", "detail": "no device command executed"}]
    return [
        {"name": "explicit-flags", "status": "pass" if not missing else "blocked", "detail": {"missing": missing}},
        {"name": "v1240-input", "status": "pass" if analysis.get("v1240_pass") and analysis.get("v1240_decision") == EXPECTED_V1240 else "blocked", "detail": analysis.get("v1240_decision")},
        {"name": "runtime-health", "status": "pass" if all(analysis.get(k) for k in ("version_ok", "bootstatus_ok", "selftest_ok", "post_bootstatus_ok", "post_selftest_ok", "post_netservice_stopped")) else "blocked", "detail": {k: analysis.get(k) for k in ("version_ok", "bootstatus_ok", "selftest_ok", "post_bootstatus_ok", "post_selftest_ok", "post_netservice_stopped")}},
        {"name": "debugfs-mount", "status": "pass" if analysis.get("mounted_during") else "blocked", "detail": {"mounted_before": analysis.get("mounted_before"), "mounted_by_v1241": analysis.get("mounted_by_v1241"), "mounted_during": analysis.get("mounted_during")}},
        {"name": "debugfs-cleanup", "status": "pass" if analysis.get("cleanup_ok") else "blocked", "detail": {"mounted_before": analysis.get("mounted_before"), "mounted_after": analysis.get("mounted_after")}},
        {"name": "pinctrl-observer", "status": "pass" if analysis.get("pinctrl_debug_present") and analysis.get("pinctrl_ap2mdm_seen") and analysis.get("pinctrl_mdm2ap_seen") else "finding", "detail": {"gpio_debug_readable": analysis.get("gpio_debug_readable"), "pinctrl_debug_present": analysis.get("pinctrl_debug_present"), "ap2mdm_lines": analysis.get("ap2mdm_lines"), "mdm2ap_lines": analysis.get("mdm2ap_lines"), "soft_reset_lines": analysis.get("soft_reset_lines")}},
        {"name": "mdm-status-irq", "status": "pass" if (analysis.get("mdm_status_irq") or {}).get("present") else "blocked", "detail": analysis.get("mdm_status_irq")},
        {"name": "pcie-regulator-surface", "status": "finding", "detail": {"pcie_debug_line_count": analysis.get("pcie_debug_line_count"), "regulator_focus_line_count": analysis.get("regulator_focus_line_count")}},
    ]


def decide(command: str, checks: list[dict[str, Any]], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v1241-sdx50m-debugfs-prereq-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V1241 with --allow-live-readonly --allow-temp-debugfs --assume-yes",
        )
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    if blockers:
        return (
            "v1241-sdx50m-debugfs-prereq-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "inspect mount/cleanup state before any esoc0 retry",
        )
    if analysis.get("pinctrl_debug_present") and analysis.get("pinctrl_ap2mdm_seen") and analysis.get("pinctrl_mdm2ap_seen"):
        return (
            "v1241-pinctrl-observer-ready-no-line-level",
            True,
            "debugfs exposes pinctrl ownership for AP2MDM/MDM2AP, but no direct line-level GPIO values",
            "V1242 can sample pinctrl/IRQ/PCIe around a bounded pm-service esoc0 trigger; do not rely on GPIO line values",
        )
    return (
        "v1241-debugfs-mounted-prereq-surface-partial",
        True,
        "debugfs mounted and cleaned up, but GPIO observer lines were not exposed",
        "use DT-derived GPIO identity plus IRQ count; avoid esoc0 retry until an observer path is chosen",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    rows = [
        ["decision", manifest.get("decision")],
        ["pass", manifest.get("pass")],
        ["mounted_before", analysis.get("mounted_before")],
        ["mounted_by_v1241", analysis.get("mounted_by_v1241")],
        ["mounted_during", analysis.get("mounted_during")],
        ["mounted_after", analysis.get("mounted_after")],
        ["gpio_debug_readable", analysis.get("gpio_debug_readable")],
        ["pinctrl_debug_present", analysis.get("pinctrl_debug_present")],
        ["pinctrl_ap2mdm_seen", analysis.get("pinctrl_ap2mdm_seen")],
        ["pinctrl_mdm2ap_seen", analysis.get("pinctrl_mdm2ap_seen")],
        ["pinctrl_soft_reset_seen", analysis.get("pinctrl_soft_reset_seen")],
        ["ap2mdm_level_guess", analysis.get("ap2mdm_level_guess")],
        ["mdm2ap_level_guess", analysis.get("mdm2ap_level_guess")],
        ["soft_reset_level_guess", analysis.get("soft_reset_level_guess")],
        ["mdm_status_irq", json.dumps(analysis.get("mdm_status_irq"), sort_keys=True)],
        ["pcie_debug_line_count", analysis.get("pcie_debug_line_count")],
        ["regulator_focus_line_count", analysis.get("regulator_focus_line_count")],
    ]
    return "\n".join([
        "# V1241 SDX50M Debugfs Prerequisite Observer",
        "",
        f"- generated: `{manifest.get('generated_at')}`",
        f"- decision: `{manifest.get('decision')}`",
        f"- pass: `{manifest.get('pass')}`",
        f"- reason: {manifest.get('reason')}",
        f"- next_step: {manifest.get('next_step')}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail"], [[c["name"], c["status"], c["detail"]] for c in manifest.get("checks", [])]),
        "",
        "## Summary",
        "",
        markdown_table(["field", "value"], rows),
        "",
        "## Observer Samples",
        "",
        markdown_table(["surface", "lines"], [
            ["AP2MDM", json.dumps(analysis.get("ap2mdm_lines", [])[:8], ensure_ascii=False)],
            ["MDM2AP", json.dumps(analysis.get("mdm2ap_lines", [])[:8], ensure_ascii=False)],
            ["soft reset", json.dumps(analysis.get("soft_reset_lines", [])[:8], ensure_ascii=False)],
            ["PCIe", json.dumps(analysis.get("pcie_debug_sample", [])[:8], ensure_ascii=False)],
        ]),
        "",
        "## Safety",
        "",
        "Live classifier with explicitly allowed temporary debugfs mount only. No raw eSoC/subsys open, GPIO/sysfs/debugfs control write, daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, reboot, flash, boot image write, or partition write occurred.",
        "",
    ])


def check_forbidden_output(manifest: dict[str, Any]) -> list[str]:
    text = json.dumps(manifest, sort_keys=True) + "\n" + render_summary(manifest)
    hits: list[str] = []
    for key in FORBIDDEN_OUTPUT_ENV_KEYS:
        value = os.environ.get(key, "")
        if value and value in text:
            hits.append(key)
    return hits


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1240 = load_json(args.v1240_manifest)
    missing = required_flags(args) if args.command == "run" else []
    steps: list[dict[str, Any]] = []
    mount_info: dict[str, Any] = {}
    analysis: dict[str, Any] = {"v1240_decision": v1240.get("decision"), "v1240_pass": bool(v1240.get("pass"))}
    if args.command == "run" and not missing:
        steps, mount_info = collect_steps(args, store)
        analysis = analyze(args, steps, v1240, mount_info)
    checks = build_checks(args.command, missing, analysis)
    decision, passed, reason, next_step = decide(args.command, checks, analysis)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v1241",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {"v1240_manifest": str(resolve(args.v1240_manifest)), "v1240_decision": v1240.get("decision"), "v1240_pass": v1240.get("pass")},
        "steps": steps,
        "analysis": analysis,
        "checks": checks,
        "device_commands_executed": args.command == "run" and not missing,
        "temporary_debugfs_mount_executed": bool(mount_info.get("mounted_by_v1241")),
        "debugfs_mounted_before": bool(mount_info.get("mounted_before")),
        "raw_esoc_open_executed": False,
        "raw_subsys_esoc0_open_executed": False,
        "gpio_sysfs_write_executed": False,
        "debugfs_control_write_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "reboot_executed": False,
        "flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
    }
    leaks = check_forbidden_output(manifest)
    manifest["forbidden_output_env_hits"] = leaks
    if leaks:
        manifest.update({
            "decision": "v1241-forbidden-output-hit",
            "pass": False,
            "reason": "forbidden environment-backed output string detected",
            "next_step": "remove sensitive output before continuing",
        })
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"next:     {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
