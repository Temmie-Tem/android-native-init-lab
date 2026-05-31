#!/usr/bin/env python3
"""V1240 read-only SDX50M response surface classifier.

This follows V1239.  The live commands are limited to read-only sysfs,
procfs, devicetree, device-node metadata, interrupt, PCIe, regulator, and dmesg
inspection.  It must not open /dev/esoc-0 or /dev/subsys_esoc0, write GPIO/sysfs,
start Wi-Fi actors, scan/connect, DHCP, route, ping, reboot, flash, or write any
partition.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1240-sdx50m-response-surface-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1240-sdx50m-response-surface-live.txt")
DEFAULT_V1239_MANIFEST = Path("tmp/wifi/v1239-post-esoc0-powerup-gap-classifier/manifest.json")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 60.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
EXPECTED_V1239 = "v1239-gap-is-after-pm-service-esoc0-before-gpio142-pcie-wlfw"
FORBIDDEN_OUTPUT_ENV_KEYS = ("A90_WIFI_SSID", "A90_WIFI_PSK")

SECRET_RE = re.compile(r"(made by|creator: made by) [^\r\n]+", re.IGNORECASE)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

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
    parser.add_argument("--v1239-manifest", type=Path, default=DEFAULT_V1239_MANIFEST)
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
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def redact(text: str) -> str:
    return SECRET_RE.sub(r"\1 [redacted]", ANSI_RE.sub("", text))


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def validate_device_command(command: list[str]) -> None:
    joined = " " + " ".join(command).lower() + " "
    for term in FORBIDDEN_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden V1240 command term {term!r}: {' '.join(command)}")


def shell_cmd(args: argparse.Namespace, script: str) -> list[str]:
    return ["run", args.busybox, "sh", "-c", script]


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
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


def subsys_sysfs_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "dump_file(){ f=\"$1\"; if [ -e \"$f\" ]; then printf 'FILE %s\\n' \"$f\"; "
        "if [ -r \"$f\" ]; then $BB cat \"$f\" 2>&1 | $BB head -c 1000; printf '\\n'; else printf 'UNREADABLE\\n'; fi; fi; }; "
        "dump_path(){ p=\"$1\"; printf '== PATH %s ==\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; "
        "if [ -d \"$p\" ]; then $BB ls -la \"$p\" 2>&1 | $BB head -100; fi; "
        "for f in name state crash_count restart_level firmware_name fw_name edge esoc_link esoc_link_info esoc_name link_state uevent power/control power/runtime_status; do dump_file \"$p/$f\"; done; }; "
        "for p in "
        "/sys/bus/esoc/devices /sys/bus/esoc/devices/esoc0 "
        "/sys/devices/platform/soc/soc:qcom,mdm3 /sys/devices/platform/soc/soc:qcom,mdm3/esoc0 /sys/devices/platform/soc/soc:qcom,mdm3/subsys9 "
        "/sys/class/subsys/subsys_modem /sys/bus/msm_subsys/devices/subsys0 /sys/bus/msm_subsys/devices/subsys9; do dump_path \"$p\"; done; "
        "true"
    )


def pcie_surface_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "for p in /sys/devices/platform/soc/1c08000.qcom,pcie /sys/bus/platform/devices/1c08000.qcom,pcie; do "
        "printf '== PCIE %s ==\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; [ -d \"$p\" ] && $BB ls -la \"$p\" 2>&1 | $BB head -120 || true; "
        "for f in current_link_state link_state power/control power/runtime_status vendor device class enable irq resource modalias uevent; do "
        "if [ -r \"$p/$f\" ]; then printf 'FILE %s/%s\\n' \"$p\" \"$f\"; $BB cat \"$p/$f\" 2>&1 | $BB head -c 800; printf '\\n'; fi; done; done; "
        "true"
    )


def interrupts_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== interrupts_focus ==\\n'; "
        "if [ -r /proc/interrupts ]; then $BB grep -Ei 'mdm|esoc|sdx|gpio|142|135|pcie|mhi|wlan|icnss|cnss' /proc/interrupts 2>&1 | $BB head -260 || true; else printf 'interrupts_readable=0\\n'; fi; "
        "true"
    )


def gpio_surface_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== gpio_class ==\\n'; $BB ls -la /sys/class/gpio 2>&1 | $BB head -120 || true; "
        "for p in /sys/class/gpio/gpio9 /sys/class/gpio/gpio135 /sys/class/gpio/gpio142; do "
        "printf '== GPIO %s ==\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; "
        "for f in direction value active_low edge label base ngpio; do if [ -r \"$p/$f\" ]; then printf 'FILE %s/%s\\n' \"$p\" \"$f\"; $BB cat \"$p/$f\" 2>&1 | $BB head -c 400; printf '\\n'; fi; done; done; "
        "printf '== debug_gpio_focus ==\\n'; "
        "if [ -r /sys/kernel/debug/gpio ]; then printf 'GPIO_DEBUG readable=1\\n'; $BB cat /sys/kernel/debug/gpio 2>&1 | $BB grep -Ei 'mdm|esoc|sdx|wlan|135|142|gpio-9' | $BB head -120 || true; else printf 'GPIO_DEBUG readable=0\\n'; fi; "
        "printf '== debug_pinctrl_focus ==\\n'; "
        "if [ -d /sys/kernel/debug/pinctrl ]; then printf 'PINCTRL_DEBUG present=1\\n'; for f in /sys/kernel/debug/pinctrl/*/pins /sys/kernel/debug/pinctrl/*/pinmux-pins /sys/kernel/debug/pinctrl/*/pinconf-pins /sys/kernel/debug/pinctrl/*/gpio-ranges; do [ -r \"$f\" ] || continue; printf 'PINCTRL_FILE %s\\n' \"$f\"; $BB grep -Ei 'mdm|esoc|sdx|135|142|gpio-9|pm8150' \"$f\" 2>&1 | $BB head -80 || true; done; else printf 'PINCTRL_DEBUG present=0\\n'; fi; "
        "true"
    )


def regulator_surface_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== regulators_focus ==\\n'; "
        "count=0; for r in /sys/class/regulator/regulator*; do [ -d \"$r\" ] || continue; count=$((count + 1)); [ \"$count\" -le 260 ] || break; "
        "name=$($BB cat \"$r/name\" 2>/dev/null | $BB head -c 160); "
        "case \"$name $r\" in *mdm*|*MDM*|*sdx*|*SDX*|*pcie*|*PCIE*|*wlan*|*WLAN*|*pm8150*|*PM8150*) "
        "printf 'REG %s name=%s\\n' \"$r\" \"$name\"; for f in state status microvolts min_microvolts max_microvolts num_users type uevent; do if [ -r \"$r/$f\" ]; then printf 'FILE %s/%s\\n' \"$r\" \"$f\"; $BB cat \"$r/$f\" 2>&1 | $BB head -c 500; printf '\\n'; fi; done;; esac; done; "
        "printf 'regulator_scan_count=%s\\n' \"$count\"; true"
    )


def devicetree_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== dt_mdm3_paths ==\\n'; "
        "for root in /sys/firmware/devicetree/base /proc/device-tree; do [ -d \"$root\" ] || continue; $BB find \"$root\" -name 'qcom,mdm3' -print 2>&1 | $BB head -20; done; "
        "for p in $($BB find /sys/firmware/devicetree/base /proc/device-tree -name 'qcom,mdm3' -print 2>/dev/null | $BB head -20); do "
        "printf '== DTNODE %s ==\\n' \"$p\"; $BB ls -la \"$p\" 2>&1 | $BB head -100 || true; "
        "for f in compatible status qcom,mdm-link-info qcom,sysmon-id qcom,ssctl-instance-id qcom,mdm2ap-status-gpio qcom,ap2mdm-status-gpio qcom,ap2mdm-soft-reset-gpio interrupt-names; do "
        "if [ -r \"$p/$f\" ]; then printf 'DTPROP %s/%s hex=' \"$p\" \"$f\"; $BB od -An -tx1 \"$p/$f\" 2>&1 | $BB tr '\\n' ' ' | $BB head -c 500; printf '\\n'; fi; done; done; "
        "true"
    )


def device_nodes_metadata_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "for p in /dev/esoc* /dev/subsys* /dev/mdm* /dev/mhi* /dev/wlan /dev/qcwlanstate; do printf '== DEV %s ==\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; done; "
        "printf '== proc_devices_focus ==\\n'; $BB cat /proc/devices 2>&1 | $BB grep -Ei 'esoc|subsys|mdm|mhi|wlan|diag' || true; "
        "true"
    )


def dmesg_focus_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "$BB dmesg 2>&1 | $BB grep -Ei 'mdm3|esoc|ext-sdx|sdx50|ap2mdm|mdm2ap|ssctl|sysmon|service-notifier|wlan_pd|wlfw|icnss|qmi|BDF file|wlan0|subsys|pil|modem|pcie|mhi|pm8150|pmic|gpio' | $BB tail -n 360 || true; "
        "true"
    )


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    steps: list[dict[str, Any]] = []
    run_step(args, store, steps, "version", ["version"], timeout=20.0)
    run_step(args, store, steps, "bootstatus", ["bootstatus"], timeout=20.0)
    run_step(args, store, steps, "selftest", ["selftest", "verbose"], timeout=20.0)
    run_step(args, store, steps, "subsys-sysfs", shell_cmd(args, subsys_sysfs_script(args)), timeout=25.0)
    run_step(args, store, steps, "pcie-surface", shell_cmd(args, pcie_surface_script(args)), timeout=20.0)
    run_step(args, store, steps, "interrupts-focus", shell_cmd(args, interrupts_script(args)), timeout=20.0)
    run_step(args, store, steps, "gpio-surface", shell_cmd(args, gpio_surface_script(args)), timeout=20.0)
    run_step(args, store, steps, "regulator-surface", shell_cmd(args, regulator_surface_script(args)), timeout=25.0)
    run_step(args, store, steps, "devicetree-mdm3", shell_cmd(args, devicetree_script(args)), timeout=25.0)
    run_step(args, store, steps, "device-nodes-metadata", shell_cmd(args, device_nodes_metadata_script(args)), timeout=20.0)
    run_step(args, store, steps, "dmesg-focus", shell_cmd(args, dmesg_focus_script(args)), timeout=20.0)
    run_step(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=20.0)
    run_step(args, store, steps, "post-selftest", ["selftest", "verbose"], timeout=20.0)
    run_step(args, store, steps, "post-netservice-status", ["netservice", "status"], timeout=20.0)
    return steps


def payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def state_after_file(text: str, suffix: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("FILE ") and line.endswith(suffix):
            if index + 1 < len(lines):
                value = lines[index + 1].strip()
                if value:
                    return value
    return ""


def parse_mdm_status_irq(text: str) -> dict[str, Any]:
    for line in text.splitlines():
        if "mdm status" not in line.lower():
            continue
        numbers = [int(item) for item in re.findall(r"\b\d+\b", line)]
        count_total = sum(numbers[1:9]) if len(numbers) >= 9 else 0
        return {"present": True, "line": line.strip(), "count_total": count_total, "gpio142_hint": "142" in line}
    return {"present": False, "line": "", "count_total": 0, "gpio142_hint": False}


def parse_pcie_state(text: str) -> dict[str, Any]:
    return {
        "surface_present": "== PCIE " in text and "No such file or directory" not in text[:240],
        "current_link_state": state_after_file(text, "/current_link_state"),
        "link_state": state_after_file(text, "/link_state"),
        "runtime_status": state_after_file(text, "/power/runtime_status"),
        "uevent_present": "FILE " in text and "/uevent" in text,
    }


def analyze(args: argparse.Namespace, steps: list[dict[str, Any]], v1239: dict[str, Any]) -> dict[str, Any]:
    subsys = payload(steps, "subsys-sysfs")
    pcie = payload(steps, "pcie-surface")
    interrupts = payload(steps, "interrupts-focus")
    gpio = payload(steps, "gpio-surface")
    regulators = payload(steps, "regulator-surface")
    dt = payload(steps, "devicetree-mdm3")
    devnodes = payload(steps, "device-nodes-metadata")
    dmesg = payload(steps, "dmesg-focus")
    return {
        "version_ok": args.expect_version in payload(steps, "version"),
        "bootstatus_ok": "BOOT OK" in payload(steps, "bootstatus"),
        "selftest_ok": "fail=0" in payload(steps, "selftest"),
        "post_bootstatus_ok": "BOOT OK" in payload(steps, "post-bootstatus"),
        "post_selftest_ok": "fail=0" in payload(steps, "post-selftest"),
        "post_netservice_stopped": "enabled=no" in payload(steps, "post-netservice-status") and "tcpctl=stopped" in payload(steps, "post-netservice-status"),
        "all_steps_ok": all(bool(step.get("ok")) for step in steps),
        "step_status": {str(step.get("name")): bool(step.get("ok")) for step in steps},
        "v1239_decision": v1239.get("decision"),
        "v1239_pass": bool(v1239.get("pass")),
        "mdm3_state": state_after_file(subsys, "/subsys9/state") or state_after_file(subsys, "/state"),
        "mss_state": state_after_file(subsys, "/subsys0/state"),
        "esoc_name": state_after_file(subsys, "/esoc_name"),
        "esoc_link": state_after_file(subsys, "/esoc_link"),
        "esoc_link_info": state_after_file(subsys, "/esoc_link_info"),
        "mdm_status_irq": parse_mdm_status_irq(interrupts),
        "pcie": parse_pcie_state(pcie),
        "gpio_debug_readable": "GPIO_DEBUG readable=1" in gpio,
        "pinctrl_debug_present": "PINCTRL_DEBUG present=1" in gpio,
        "gpio135_exported": "== GPIO /sys/class/gpio/gpio135 ==" in gpio and "No such file or directory" not in gpio[gpio.find("== GPIO /sys/class/gpio/gpio135 =="):gpio.find("== GPIO /sys/class/gpio/gpio135 ==") + 180],
        "gpio142_exported": "== GPIO /sys/class/gpio/gpio142 ==" in gpio and "No such file or directory" not in gpio[gpio.find("== GPIO /sys/class/gpio/gpio142 =="):gpio.find("== GPIO /sys/class/gpio/gpio142 ==") + 180],
        "dt_mdm3_present": "== DTNODE " in dt,
        "dt_ap2mdm_gpio_present": "qcom,ap2mdm-status-gpio" in dt,
        "dt_mdm2ap_gpio_present": "qcom,mdm2ap-status-gpio" in dt,
        "dt_soft_reset_gpio_present": "qcom,ap2mdm-soft-reset-gpio" in dt,
        "regulator_focus_count": len(re.findall(r"^REG ", regulators, re.MULTILINE)),
        "dev_esoc_metadata_seen": "== DEV /dev/esoc" in devnodes,
        "dev_subsys_metadata_seen": "== DEV /dev/subsys" in devnodes,
        "dmesg_wlfw_count": dmesg.lower().count("wlfw"),
        "dmesg_wlan0_count": dmesg.lower().count("wlan0"),
        "dmesg_pcie_count": dmesg.lower().count("pcie"),
        "dmesg_mdm_down_count": len(re.findall(r"modem went down|crashed: 1|collecting msa0", dmesg, re.IGNORECASE)),
    }


def build_checks(command: str, missing: list[str], analysis: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{"name": "plan-only", "status": "pass", "detail": "no device command executed"}]
    return [
        {"name": "live-readonly-flags", "status": "pass" if not missing else "blocked", "detail": {"missing": missing}},
        {"name": "v1239-input", "status": "pass" if analysis.get("v1239_pass") and analysis.get("v1239_decision") == EXPECTED_V1239 else "blocked", "detail": analysis.get("v1239_decision")},
        {"name": "runtime-health", "status": "pass" if all(analysis.get(k) for k in ("version_ok", "bootstatus_ok", "selftest_ok", "post_bootstatus_ok", "post_selftest_ok", "post_netservice_stopped")) else "blocked", "detail": {k: analysis.get(k) for k in ("version_ok", "bootstatus_ok", "selftest_ok", "post_bootstatus_ok", "post_selftest_ok", "post_netservice_stopped")}},
        {"name": "read-only-steps", "status": "pass" if analysis.get("all_steps_ok") else "blocked", "detail": analysis.get("step_status")},
        {"name": "mdm3-response-state", "status": "pass" if analysis.get("mdm3_state") else "blocked", "detail": {"mdm3_state": analysis.get("mdm3_state"), "esoc_name": analysis.get("esoc_name"), "esoc_link": analysis.get("esoc_link"), "esoc_link_info": analysis.get("esoc_link_info")}},
        {"name": "mdm-status-irq-surface", "status": "pass" if (analysis.get("mdm_status_irq") or {}).get("present") else "blocked", "detail": analysis.get("mdm_status_irq")},
        {"name": "pcie-surface", "status": "pass" if (analysis.get("pcie") or {}).get("surface_present") else "finding", "detail": analysis.get("pcie")},
        {"name": "gpio-dt-surface", "status": "finding", "detail": {"gpio_debug_readable": analysis.get("gpio_debug_readable"), "pinctrl_debug_present": analysis.get("pinctrl_debug_present"), "gpio135_exported": analysis.get("gpio135_exported"), "gpio142_exported": analysis.get("gpio142_exported"), "dt_ap2mdm": analysis.get("dt_ap2mdm_gpio_present"), "dt_mdm2ap": analysis.get("dt_mdm2ap_gpio_present"), "dt_soft_reset": analysis.get("dt_soft_reset_gpio_present")}},
    ]


def decide(command: str, checks: list[dict[str, Any]], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return ("v1240-sdx50m-response-surface-plan-ready", True, "plan-only; no device command executed", "run V1240 with --allow-live-readonly --assume-yes")
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    if blockers:
        return ("v1240-sdx50m-response-surface-blocked", False, "blocked by " + ", ".join(blockers), "restore read-only baseline before another live gate")
    if analysis.get("mdm3_state") == "OFFLINING" and (analysis.get("mdm_status_irq") or {}).get("count_total", 0) == 0:
        return ("v1240-response-inputs-visible-mdm2ap-silent", True, "read-only surface is visible; mdm3 remains OFFLINING and mdm status/GPIO142 IRQ count is still zero", "design V1241 around the AP2MDM/PMIC/PCIe prerequisites before retrying pm-service esoc0")
    return ("v1240-response-surface-captured", True, "read-only SDX50M response surface captured", "compare against Android GPIO/PCIe timing before the next live gate")


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    rows = [
        ["decision", manifest.get("decision")],
        ["pass", manifest.get("pass")],
        ["mdm3_state", analysis.get("mdm3_state")],
        ["mss_state", analysis.get("mss_state")],
        ["esoc_name", analysis.get("esoc_name")],
        ["esoc_link", analysis.get("esoc_link")],
        ["esoc_link_info", analysis.get("esoc_link_info")],
        ["mdm_status_irq", json.dumps(analysis.get("mdm_status_irq"), sort_keys=True)],
        ["pcie", json.dumps(analysis.get("pcie"), sort_keys=True)],
        ["gpio_debug_readable", analysis.get("gpio_debug_readable")],
        ["pinctrl_debug_present", analysis.get("pinctrl_debug_present")],
        ["gpio135_exported", analysis.get("gpio135_exported")],
        ["gpio142_exported", analysis.get("gpio142_exported")],
        ["dt_ap2mdm_gpio_present", analysis.get("dt_ap2mdm_gpio_present")],
        ["dt_mdm2ap_gpio_present", analysis.get("dt_mdm2ap_gpio_present")],
        ["dt_soft_reset_gpio_present", analysis.get("dt_soft_reset_gpio_present")],
        ["regulator_focus_count", analysis.get("regulator_focus_count")],
        ["dmesg_wlfw_count", analysis.get("dmesg_wlfw_count")],
        ["dmesg_wlan0_count", analysis.get("dmesg_wlan0_count")],
    ]
    return "\n".join([
        "# V1240 SDX50M Response Surface Live Classifier",
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
        "## Safety",
        "",
        "Read-only live classifier. No raw eSoC/subsys open, GPIO/sysfs write, daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, reboot, flash, boot image write, or partition write occurred.",
        "",
    ])


def check_forbidden_output(manifest: dict[str, Any]) -> list[str]:
    text = json.dumps(manifest, sort_keys=True) + "\n" + render_summary(manifest)
    leaks: list[str] = []
    for key in FORBIDDEN_OUTPUT_ENV_KEYS:
        value = os.environ.get(key, "")
        if value and value in text:
            leaks.append(key)
    return leaks


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1239 = load_json(args.v1239_manifest)
    missing = required_flags(args) if args.command == "run" else []
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {"v1239_decision": v1239.get("decision"), "v1239_pass": bool(v1239.get("pass"))}
    if args.command == "run" and not missing:
        steps = collect_steps(args, store)
        analysis = analyze(args, steps, v1239)
    checks = build_checks(args.command, missing, analysis)
    decision, passed, reason, next_step = decide(args.command, checks, analysis)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v1240",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {"v1239_manifest": str(resolve(args.v1239_manifest)), "v1239_decision": v1239.get("decision"), "v1239_pass": v1239.get("pass")},
        "steps": steps,
        "analysis": analysis,
        "checks": checks,
        "device_commands_executed": args.command == "run" and not missing,
        "device_mutations": False,
        "raw_esoc_open_executed": False,
        "raw_subsys_esoc0_open_executed": False,
        "gpio_sysfs_write_executed": False,
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
        manifest.update({"decision": "v1240-forbidden-output-hit", "pass": False, "reason": "forbidden environment-backed output string detected", "next_step": "remove sensitive output before continuing"})
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
