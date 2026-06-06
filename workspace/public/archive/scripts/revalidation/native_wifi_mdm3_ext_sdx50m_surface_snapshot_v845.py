#!/usr/bin/env python3
"""V845 read-only mdm3/ext-sdx50m eSoC surface snapshot.

V844 corrected the model: the missing WLFW service 69 publication is gated by
the external mdm3/ext-sdx50m path, not by another service-notifier listener
retry. This runner captures the live read-only GPIO/sysfs/devicetree/device-node
surface needed before any bounded state-changing attempt.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v845-mdm3-ext-sdx50m-surface-snapshot")
LATEST_POINTER = Path("tmp/wifi/latest-v845-mdm3-ext-sdx50m-surface-snapshot.txt")
DEFAULT_V844_MANIFEST = Path("tmp/wifi/v844-mdm3-ext-sdx50m-boot-interface-classifier/manifest.json")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 60.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
EXPECTED_V844 = "v844-mdm3-ext-sdx50m-boot-interface-selected"

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
)

FORBIDDEN_ACTIONS = (
    "raw esoc0 open or hold",
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
    parser.add_argument("--v844-manifest", type=Path, default=DEFAULT_V844_MANIFEST)
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
            raise RuntimeError(f"forbidden V845 command term {term!r}: {' '.join(command)}")


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


def mdm3_sysfs_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "dump_file(){ f=\"$1\"; if [ -e \"$f\" ]; then printf 'FILE %s\\n' \"$f\"; "
        "if [ -r \"$f\" ]; then $BB cat \"$f\" 2>&1 | $BB head -c 1200; printf '\\n'; else printf 'UNREADABLE\\n'; fi; fi; }; "
        "dump_path(){ p=\"$1\"; printf '== PATH %s ==\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; $BB readlink \"$p\" 2>&1 || true; "
        "if [ -d \"$p\" ]; then $BB ls -la \"$p\" 2>&1 | $BB head -120; fi; "
        "for f in name state crash_count restart_level firmware_name fw_name edge esoc_link esoc_link_info esoc_name link_state modem uevent power/control power/runtime_status power/runtime_suspended_time power/runtime_active_time; do dump_file \"$p/$f\"; done; }; "
        "for p in "
        "/sys/bus/esoc/devices "
        "/sys/bus/esoc/devices/esoc0 "
        "/sys/devices/platform/soc/soc:qcom,mdm3 "
        "/sys/devices/platform/soc/soc:qcom,mdm3/esoc0 "
        "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9 "
        "/sys/class/subsys/subsys_esoc0 "
        "/sys/bus/msm_subsys/devices/subsys9 "
        "/sys/class/subsys/subsys_modem "
        "/sys/bus/msm_subsys/devices/subsys0 "
        "/sys/bus/platform/devices/soc:qcom,mdm3; do dump_path \"$p\"; done; "
        "true"
    )


def access_matrix_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "for f in "
        "/sys/bus/esoc/devices/esoc0/esoc_link "
        "/sys/bus/esoc/devices/esoc0/esoc_link_info "
        "/sys/bus/esoc/devices/esoc0/esoc_name "
        "/sys/devices/platform/soc/soc:qcom,mdm3/esoc0/esoc_link "
        "/sys/devices/platform/soc/soc:qcom,mdm3/esoc0/esoc_link_info "
        "/sys/devices/platform/soc/soc:qcom,mdm3/esoc0/esoc_name "
        "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state "
        "/sys/class/subsys/subsys_esoc0/state "
        "/sys/bus/msm_subsys/devices/subsys9/state "
        "/sys/class/subsys/subsys_modem/state "
        "/sys/bus/msm_subsys/devices/subsys0/state; do "
        "printf 'ACCESS %s exists=' \"$f\"; [ -e \"$f\" ] && printf '1' || printf '0'; "
        "printf ' readable='; [ -r \"$f\" ] && printf '1' || printf '0'; "
        "printf ' writable='; [ -w \"$f\" ] && printf '1' || printf '0'; "
        "printf ' executable='; [ -x \"$f\" ] && printf '1' || printf '0'; printf '\\n'; "
        "$BB ls -ld \"$f\" 2>&1 || true; "
        "done; "
        "true"
    )


def gpio_surface_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== gpio_class ==\\n'; $BB ls -la /sys/class/gpio 2>&1 | $BB head -120 || true; "
        "for p in /sys/class/gpio/gpio9 /sys/class/gpio/gpio135 /sys/class/gpio/gpio142; do "
        "printf '== GPIO %s ==\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; "
        "for f in direction value active_low edge label base ngpio; do "
        "if [ -r \"$p/$f\" ]; then printf 'FILE %s/%s\\n' \"$p\" \"$f\"; $BB cat \"$p/$f\" 2>&1 | $BB head -c 400; printf '\\n'; fi; "
        "done; "
        "done; "
        "printf '== gpiochips ==\\n'; "
        "for p in /sys/class/gpio/gpiochip*; do [ -e \"$p\" ] || continue; printf 'GPIOCHIP %s\\n' \"$p\"; "
        "for f in label base ngpio; do if [ -r \"$p/$f\" ]; then printf '%s=' \"$f\"; $BB cat \"$p/$f\" 2>&1 | $BB head -c 200; printf '\\n'; fi; done; done; "
        "printf '== debug_gpio_focus ==\\n'; "
        "if [ -r /sys/kernel/debug/gpio ]; then printf 'GPIO_DEBUG readable=1\\n'; $BB cat /sys/kernel/debug/gpio 2>&1 | $BB grep -Ei 'mdm|esoc|sdx|wlan|135|142|gpio-9' | $BB head -120 || true; else printf 'GPIO_DEBUG readable=0\\n'; fi; "
        "true"
    )


def devicetree_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== dt_mdm3_paths ==\\n'; "
        "for root in /sys/firmware/devicetree/base /proc/device-tree; do "
        "[ -d \"$root\" ] || continue; $BB find \"$root\" -name 'qcom,mdm3' -print 2>&1 | $BB head -20; "
        "done; "
        "for p in $($BB find /sys/firmware/devicetree/base /proc/device-tree -name 'qcom,mdm3' -print 2>/dev/null | $BB head -20); do "
        "printf '== DTNODE %s ==\\n' \"$p\"; $BB ls -la \"$p\" 2>&1 | $BB head -120 || true; "
        "for f in compatible status qcom,mdm-link-info qcom,sysmon-id qcom,ssctl-instance-id qcom,mdm2ap-status-gpio qcom,ap2mdm-status-gpio qcom,ap2mdm-soft-reset-gpio interrupt-names; do "
        "if [ -r \"$p/$f\" ]; then printf 'DTPROP %s/%s hex=' \"$p\" \"$f\"; $BB od -An -tx1 \"$p/$f\" 2>&1 | $BB tr '\\n' ' ' | $BB head -c 500; printf '\\n'; fi; "
        "done; "
        "done; "
        "true"
    )


def device_nodes_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "for p in /dev/esoc* /dev/subsys* /dev/mdm* /dev/qrtr* /dev/qmi* /dev/wlan /dev/qcwlanstate; do "
        "printf '== DEV %s ==\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; "
        "done; "
        "printf '== proc_devices_focus ==\\n'; $BB cat /proc/devices 2>&1 | $BB grep -Ei 'esoc|subsys|mdm|qrtr|qmi|wlan|diag' || true; "
        "true"
    )


def kernel_log_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "$BB dmesg 2>&1 | $BB grep -Ei 'mdm3|esoc|ext-sdx|sdx50|ap2mdm|mdm2ap|ssctl|sysmon|service-notifier|servreg|service.loc|qrtr: Modem QMI Readiness|wlan_pd|wlfw|icnss|qmi|BDF file|wlan0|subsys|pil|modem' | $BB tail -n 360 || true; "
        "true"
    )


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    steps: list[dict[str, Any]] = []
    run_step(args, store, steps, "version", ["version"], timeout=20.0)
    run_step(args, store, steps, "bootstatus", ["bootstatus"], timeout=20.0)
    run_step(args, store, steps, "selftest", ["selftest", "verbose"], timeout=20.0)
    run_step(args, store, steps, "mdm3-sysfs", shell_cmd(args, mdm3_sysfs_script(args)), timeout=25.0)
    run_step(args, store, steps, "access-matrix", shell_cmd(args, access_matrix_script(args)), timeout=20.0)
    run_step(args, store, steps, "gpio-surface", shell_cmd(args, gpio_surface_script(args)), timeout=20.0)
    run_step(args, store, steps, "devicetree-mdm3", shell_cmd(args, devicetree_script(args)), timeout=25.0)
    run_step(args, store, steps, "device-nodes", shell_cmd(args, device_nodes_script(args)), timeout=20.0)
    run_step(args, store, steps, "dmesg-focus", shell_cmd(args, kernel_log_script(args)), timeout=20.0)
    run_step(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=20.0)
    run_step(args, store, steps, "post-selftest", ["selftest", "verbose"], timeout=20.0)
    return steps


def payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def bool_from_text(text: str, marker: str) -> bool:
    return marker in text and "No such file or directory" not in text[text.find(marker):text.find(marker) + 200]


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


def parse_access(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pattern = re.compile(r"^ACCESS (?P<path>\S+) exists=(?P<exists>[01]) readable=(?P<readable>[01]) writable=(?P<writable>[01]) executable=(?P<executable>[01])$")
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        rows.append({
            "path": match.group("path"),
            "exists": match.group("exists") == "1",
            "readable": match.group("readable") == "1",
            "writable": match.group("writable") == "1",
            "executable": match.group("executable") == "1",
        })
    return rows


def count_patterns(text: str) -> dict[str, int]:
    lower = text.lower()
    return {
        "mdm3": lower.count("mdm3"),
        "esoc": lower.count("esoc"),
        "ext_sdx": lower.count("ext-sdx") + lower.count("sdx50"),
        "ap2mdm": lower.count("ap2mdm"),
        "mdm2ap": lower.count("mdm2ap"),
        "sysmon": lower.count("sysmon"),
        "ssctl": lower.count("ssctl"),
        "service_notifier": lower.count("service-notifier"),
        "wlan_pd": lower.count("wlan_pd"),
        "wlfw": lower.count("wlfw"),
        "bdf": lower.count("bdf"),
        "wlan0": lower.count("wlan0"),
        "warning": lower.count("warning:"),
    }


def analyze(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    sysfs_text = payload(steps, "mdm3-sysfs")
    access_text = payload(steps, "access-matrix")
    gpio_text = payload(steps, "gpio-surface")
    dt_text = payload(steps, "devicetree-mdm3")
    dev_text = payload(steps, "device-nodes")
    dmesg_text = payload(steps, "dmesg-focus")
    all_text = "\n".join([sysfs_text, access_text, gpio_text, dt_text, dev_text, dmesg_text])
    access_rows = parse_access(access_text)
    writable_existing = [row["path"] for row in access_rows if row["exists"] and row["writable"]]
    return {
        "version_ok": args.expect_version in payload(steps, "version"),
        "bootstatus_ok": "BOOT OK" in payload(steps, "bootstatus"),
        "selftest_ok": "selftest: pass=" in payload(steps, "selftest") and "fail=0" in payload(steps, "selftest"),
        "post_bootstatus_ok": "BOOT OK" in payload(steps, "post-bootstatus"),
        "post_selftest_ok": "selftest: pass=" in payload(steps, "post-selftest") and "fail=0" in payload(steps, "post-selftest"),
        "all_steps_ok": all(bool(step.get("ok")) for step in steps),
        "step_status": {str(step.get("name")): bool(step.get("ok")) for step in steps},
        "mdm3_sysfs_present": bool_from_text(sysfs_text, "== PATH /sys/devices/platform/soc/soc:qcom,mdm3 =="),
        "esoc_bus_present": bool_from_text(sysfs_text, "== PATH /sys/bus/esoc/devices =="),
        "esoc0_sysfs_present": bool_from_text(sysfs_text, "== PATH /sys/bus/esoc/devices/esoc0 =="),
        "subsys_esoc0_present": bool_from_text(sysfs_text, "== PATH /sys/class/subsys/subsys_esoc0 =="),
        "mdm3_state": first_state(sysfs_text, ("mdm3", "subsys9", "subsys_esoc0", "esoc0")),
        "mss_state": first_state(sysfs_text, ("subsys_modem", "subsys0")),
        "access_rows": access_rows,
        "writable_existing_control_candidates": writable_existing,
        "gpio_debug_readable": "GPIO_DEBUG readable=1" in gpio_text,
        "gpio_class_present": "== gpio_class ==" in gpio_text and "No such file or directory" not in gpio_text[:240],
        "gpio135_exported": "== GPIO /sys/class/gpio/gpio135 ==" in gpio_text and "No such file or directory" not in gpio_text[gpio_text.find("== GPIO /sys/class/gpio/gpio135 =="):gpio_text.find("== GPIO /sys/class/gpio/gpio135 ==") + 180],
        "gpio142_exported": "== GPIO /sys/class/gpio/gpio142 ==" in gpio_text and "No such file or directory" not in gpio_text[gpio_text.find("== GPIO /sys/class/gpio/gpio142 =="):gpio_text.find("== GPIO /sys/class/gpio/gpio142 ==") + 180],
        "dt_mdm3_present": "== DTNODE " in dt_text,
        "dt_ext_sdx50m_present": "71 63 6f 6d 2c 65 78 74 2d 73 64 78 35 30 6d" in dt_text or "ext-sdx50m" in dt_text,
        "dt_ap2mdm_gpio_present": "qcom,ap2mdm-status-gpio" in dt_text,
        "dt_mdm2ap_gpio_present": "qcom,mdm2ap-status-gpio" in dt_text,
        "dev_esoc_node_present": "== DEV /dev/esoc" in dev_text and "No such file or directory" not in dev_text[dev_text.find("== DEV /dev/esoc"):dev_text.find("== DEV /dev/esoc") + 180],
        "dev_subsys_node_present": "== DEV /dev/subsys" in dev_text and "No such file or directory" not in dev_text[dev_text.find("== DEV /dev/subsys"):dev_text.find("== DEV /dev/subsys") + 180],
        "runtime_counts": count_patterns(dmesg_text),
        "surface_counts": count_patterns(all_text),
    }


def build_checks(command: str,
                 args: argparse.Namespace,
                 v844: dict[str, Any],
                 steps: list[dict[str, Any]],
                 analysis: dict[str, Any],
                 missing_flags: list[str]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "read-only mdm3/ext-sdx50m surface plan; no device command executed",
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
            "name": "v844-route-ready",
            "status": "pass" if v844.get("pass") is True and v844.get("decision") == EXPECTED_V844 else "blocked",
            "detail": {"decision": v844.get("decision"), "pass": v844.get("pass")},
            "next_step": "refresh V844 classifier evidence before V845 live snapshot",
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
            "next_step": "restore healthy native v724 before interpreting mdm3/eSoC surface",
        },
        {
            "name": "read-only-command-success",
            "status": "pass" if analysis.get("all_steps_ok") else "blocked",
            "detail": analysis.get("step_status"),
            "next_step": "fix bridge/runtime read failures before selecting a state-changing gate",
        },
        {
            "name": "mdm3-esoc-surface",
            "status": "pass" if analysis.get("mdm3_sysfs_present") and analysis.get("esoc0_sysfs_present") and analysis.get("subsys_esoc0_present") else "blocked",
            "detail": {
                "mdm3_sysfs_present": analysis.get("mdm3_sysfs_present"),
                "esoc_bus_present": analysis.get("esoc_bus_present"),
                "esoc0_sysfs_present": analysis.get("esoc0_sysfs_present"),
                "subsys_esoc0_present": analysis.get("subsys_esoc0_present"),
                "mdm3_state": analysis.get("mdm3_state"),
                "mss_state": analysis.get("mss_state"),
            },
            "next_step": "if absent, classify why mdm3/eSoC sysfs is unavailable before any live trigger",
        },
        {
            "name": "gpio-dt-surface",
            "status": "finding",
            "detail": {
                "gpio_debug_readable": analysis.get("gpio_debug_readable"),
                "gpio135_exported": analysis.get("gpio135_exported"),
                "gpio142_exported": analysis.get("gpio142_exported"),
                "dt_mdm3_present": analysis.get("dt_mdm3_present"),
                "dt_ext_sdx50m_present": analysis.get("dt_ext_sdx50m_present"),
                "dt_ap2mdm_gpio_present": analysis.get("dt_ap2mdm_gpio_present"),
                "dt_mdm2ap_gpio_present": analysis.get("dt_mdm2ap_gpio_present"),
            },
            "next_step": "use only for source-backed control-contract classification; do not write GPIOs",
        },
        {
            "name": "raw-device-node-boundary",
            "status": "pass" if not analysis.get("dev_esoc_node_present") else "finding",
            "detail": {
                "dev_esoc_node_present": analysis.get("dev_esoc_node_present"),
                "dev_subsys_node_present": analysis.get("dev_subsys_node_present"),
            },
            "next_step": "keep raw esoc0 open blocked regardless of device-node presence",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v845-mdm3-ext-sdx50m-surface-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V845 read-only live mdm3/ext-sdx50m surface snapshot",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v845-mdm3-ext-sdx50m-surface-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "restore required evidence or live read-only health before any mdm3/eSoC action",
        )
    if analysis.get("mdm3_state") == "ONLINE":
        return (
            "v845-mdm3-already-online-surface-captured",
            True,
            "read-only snapshot found mdm3 already ONLINE; route next gate to WLFW/service69 readiness",
            "V846 should capture WLFW/service69/BDF readiness before HAL/connect",
        )
    return (
        "v845-mdm3-ext-sdx50m-surface-captured",
        True,
        "read-only snapshot captured mdm3/ext-sdx50m sysfs, access, GPIO, devicetree, and device-node boundaries without opening esoc0 or writing controls",
        "V846 should classify the source-backed mdm3/eSoC state-control contract before any bounded write or GPIO action",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v844 = load_json(args.v844_manifest)
    missing_flags = required_flags(args) if args.command == "run" else []
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    if args.command == "run" and not missing_flags:
        steps = collect_steps(args, store)
        analysis = analyze(args, steps)
    checks = build_checks(args.command, args, v844, steps, analysis, missing_flags)
    decision, pass_ok, reason, next_step = decide(args.command, checks, analysis)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v845",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v844_manifest": str(resolve(args.v844_manifest)),
            "v844_decision": v844.get("decision"),
            "v844_pass": v844.get("pass"),
            "expect_version": args.expect_version,
        },
        "steps": steps,
        "analysis": analysis,
        "checks": checks,
        "device_commands_executed": args.command == "run" and not missing_flags,
        "device_mutations": False,
        "menu_hide_executed": any("hide_on_busy" in step for step in steps),
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
        "esoc0_open_executed": False,
        "gpio_write_executed": False,
        "sysfs_write_executed": False,
        "bind_unbind_executed": False,
        "module_load_unload_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    analysis = manifest.get("analysis", {})
    analysis_rows = [
        [key, json.dumps(value, ensure_ascii=False, sort_keys=True)]
        for key, value in analysis.items()
        if key not in {"step_status", "access_rows"}
    ]
    step_rows = [
        [str(step.get("name")), str(step.get("ok")), str(step.get("status")), str(step.get("file"))]
        for step in manifest.get("steps", [])
    ]
    access_rows = [
        [row.get("path"), row.get("exists"), row.get("readable"), row.get("writable"), row.get("executable")]
        for row in analysis.get("access_rows", [])
    ]
    return "\n".join([
        "# V845 mdm3/ext-sdx50m Surface Snapshot",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- esoc0_open_executed: `{manifest['esoc0_open_executed']}`",
        f"- gpio_write_executed: `{manifest['gpio_write_executed']}`",
        f"- sysfs_write_executed: `{manifest['sysfs_write_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Analysis",
        "",
        markdown_table(["signal", "value"], analysis_rows),
        "",
        "## Access Matrix",
        "",
        markdown_table(["path", "exists", "readable", "writable", "executable"], access_rows),
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
    print(f"esoc0_open_executed: {manifest['esoc0_open_executed']}")
    print(f"gpio_write_executed: {manifest['gpio_write_executed']}")
    print(f"sysfs_write_executed: {manifest['sysfs_write_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
