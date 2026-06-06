#!/usr/bin/env python3
"""V815 read-only stock-v724 subsystem/sysmon/service-locator snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v815-subsystem-sysmon-snapshot")
LATEST_POINTER = Path("tmp/wifi/latest-v815-subsystem-sysmon-snapshot.txt")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 60.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_V814_MANIFEST = Path("tmp/wifi/v814-sibling-sysmon-source-classifier/manifest.json")

SECRET_RE = re.compile(r"(made by|creator: made by) [^\r\n]+", re.IGNORECASE)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
BLOCK_RE = re.compile(r"^== (?P<label>[^=].*?) ==$", re.MULTILINE)

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
)

FORBIDDEN_ACTIONS = (
    "custom kernel flash, boot image write, or partition write",
    "reboot or bootloader handoff",
    "daemon start, service-manager start, or Wi-Fi HAL start",
    "Wi-Fi scan/connect/link-up or credential use",
    "DHCP, route change, or external ping",
    "boot_wlan, qcwlanstate, esoc0 open, bind/unbind, driver override, or module load/unload",
    "sysfs/debugfs/control write",
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
    parser.add_argument("--v814-manifest", type=Path, default=DEFAULT_V814_MANIFEST)
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
            raise RuntimeError(f"forbidden V815 command term {term!r}: {' '.join(command)}")


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


def subsys_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== msm_subsys_devices ==\\n'; $BB ls -la /sys/bus/msm_subsys/devices 2>&1 || true; "
        "for d in /sys/bus/msm_subsys/devices/*; do "
        "[ -e \"$d\" ] || continue; "
        "printf '== SUBSYS %s ==\\n' \"$d\"; "
        "$BB ls -ld \"$d\" 2>&1 || true; "
        "$BB readlink \"$d\" 2>&1 || true; "
        "for f in name state crash_count restart_level fw_name edge; do "
        "printf '%s=' \"$f\"; if [ -r \"$d/$f\" ]; then $BB cat \"$d/$f\" 2>&1 | $BB head -c 400; else printf 'unreadable'; fi; printf '\\n'; "
        "done; "
        "printf 'files='; $BB ls -1 \"$d\" 2>&1 | $BB tr '\\n' ','; printf '\\n'; "
        "done; "
        "true"
    )


def esoc_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "for p in /sys/bus/esoc/devices /sys/bus/esoc/devices/* /sys/class/subsys /sys/class/subsys/* /dev/subsys* /dev/esoc*; do "
        "printf '== %s ==\\n' \"$p\"; "
        "$BB ls -ld \"$p\" 2>&1 || true; "
        "if [ -d \"$p\" ]; then $BB ls -la \"$p\" 2>&1 | $BB head -80; fi; "
        "for f in name state link modem type uevent power/runtime_status power/control; do "
        "if [ -r \"$p/$f\" ]; then printf 'FILE %s/%s\\n' \"$p\" \"$f\"; $BB cat \"$p/$f\" 2>&1 | $BB head -c 500; printf '\\n'; fi; "
        "done; "
        "done; "
        "true"
    )


def sysmon_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== platform_sysmon_paths ==\\n'; "
        "for p in /sys/bus/platform/devices/*sysmon* /sys/bus/platform/drivers/*sysmon* /sys/bus/platform/devices/*serv* /sys/bus/platform/drivers/*serv*; do "
        "[ -e \"$p\" ] || continue; $BB ls -ld \"$p\" 2>&1 || true; "
        "if [ -d \"$p\" ]; then $BB ls -1 \"$p\" 2>&1 | $BB head -80; fi; "
        "done; "
        "printf '\\n== devicetree_sysmon_id_paths ==\\n'; "
        "$BB find /sys/firmware/devicetree/base -name 'qcom,sysmon-id' -print 2>&1 | $BB head -80; "
        "printf '\\n== devicetree_sysmon_names ==\\n'; "
        "$BB find /sys/firmware/devicetree/base -name '*sysmon*' -print 2>&1 | $BB head -120; "
        "printf '\\n== devicetree_wlan_pd_names ==\\n'; "
        "$BB find /sys/firmware/devicetree/base -name '*wlan*' -o -name '*mdm*' -o -name '*modem*' 2>&1 | $BB head -160; "
        "true"
    )


def proc_net_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== proc_net_qrtr ==\\n'; $BB cat /proc/net/qrtr 2>&1 || true; "
        "printf '\\n== proc_net_netlink_focus ==\\n'; $BB cat /proc/net/netlink 2>&1 | $BB head -120; "
        "printf '\\n== proc_net_protocols_focus ==\\n'; $BB cat /proc/net/protocols 2>&1 | $BB grep -Ei 'qrtr|netlink|qmi|diag' || true; "
        "true"
    )


def icnss_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "for p in /sys/bus/platform/drivers/icnss /sys/bus/platform/devices/18800000.qcom,icnss /sys/bus/platform/devices/18800000.qcom,icnss/driver /sys/module/wlan /sys/module/wlan/parameters /sys/class/net/wlan0 /dev/wlan /dev/qcwlanstate; do "
        "printf '== %s ==\\n' \"$p\"; "
        "$BB ls -ld \"$p\" 2>&1 || true; "
        "if [ -d \"$p\" ]; then $BB ls -la \"$p\" 2>&1 | $BB head -80; fi; "
        "done; "
        "true"
    )


def process_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== ps_focus ==\\n'; "
        "$BB ps 2>&1 | $BB grep -Ei 'qrtr|rmt|tftp|pd-mapper|cnss|mdm|qmi|diag|wifi' || true; "
        "true"
    )


def dmesg_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "$BB dmesg 2>&1 | $BB grep -Ei 'sysmon-qmi|sysmon|service-notifier|servreg|service.loc|servloc|qrtr: Modem QMI Readiness|subsys|ssr|pil|modem|mdm3|esoc|wlan_pd|icnss_qmi|WLAN FW|BDF file|wlan0|icnss: Modules not initialized|wlan: Loading driver|qcwlanstate' | $BB tail -n 360 || true; "
        "true"
    )


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    steps: list[dict[str, Any]] = []
    run_step(args, store, steps, "version", ["version"], timeout=20.0)
    run_step(args, store, steps, "selftest", ["selftest"], timeout=20.0)
    run_step(args, store, steps, "subsys-snapshot", shell_cmd(args, subsys_script(args)))
    run_step(args, store, steps, "esoc-metadata", shell_cmd(args, esoc_script(args)))
    run_step(args, store, steps, "sysmon-service-dt", shell_cmd(args, sysmon_script(args)))
    run_step(args, store, steps, "proc-net-snapshot", shell_cmd(args, proc_net_script(args)))
    run_step(args, store, steps, "icnss-snapshot", shell_cmd(args, icnss_script(args)))
    run_step(args, store, steps, "process-focus", shell_cmd(args, process_script(args)))
    run_step(args, store, steps, "dmesg-focus", shell_cmd(args, dmesg_script(args)))
    return steps


def payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def parse_subsys_blocks(text: str) -> dict[str, dict[str, str]]:
    blocks: dict[str, dict[str, str]] = {}
    current = ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("== SUBSYS ") and line.endswith(" =="):
            current = line[len("== SUBSYS "):-len(" ==")]
            blocks[current] = {"_label": current}
            continue
        if current and "=" in line:
            key, value = line.split("=", 1)
            blocks[current][key.strip()] = value.strip()
    return blocks


def find_state(blocks: dict[str, dict[str, str]], wanted: tuple[str, ...]) -> str:
    for attrs in blocks.values():
        name = attrs.get("name", "").lower()
        path = " ".join(attrs.values()).lower()
        if any(item in name or item in path for item in wanted):
            return attrs.get("state", "")
    return ""


def count_patterns(text: str) -> dict[str, int]:
    lower = text.lower()
    return {
        "sysmon_qmi": lower.count("sysmon-qmi"),
        "sysmon_any": lower.count("sysmon"),
        "service_notifier": lower.count("service-notifier"),
        "service_notifier_180": len(re.findall(r"service-notifier.*\\b180\\b", lower)),
        "service_notifier_74": len(re.findall(r"service-notifier.*\\b74\\b", lower)),
        "service_locator": lower.count("service.loc") + lower.count("servloc"),
        "qrtr_modem_readiness": lower.count("qrtr: modem qmi readiness"),
        "wlan_pd": lower.count("wlan_pd"),
        "wlfw": lower.count("wlfw"),
        "bdf": lower.count("bdf"),
        "wlan0": lower.count("wlan0"),
        "kernel_warning": lower.count("warning:") + lower.count("kernel panic"),
    }


def analyze(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    subsys_text = payload(steps, "subsys-snapshot")
    dmesg_text = payload(steps, "dmesg-focus")
    sysmon_text = payload(steps, "sysmon-service-dt")
    esoc_text = payload(steps, "esoc-metadata")
    proc_text = payload(steps, "proc-net-snapshot")
    icnss_text = payload(steps, "icnss-snapshot")
    blocks = parse_subsys_blocks(subsys_text)
    runtime_counts = count_patterns("\n".join([dmesg_text, proc_text]))
    surface_counts = count_patterns("\n".join([sysmon_text, esoc_text, icnss_text]))
    return {
        "version_ok": args.expect_version in payload(steps, "version"),
        "selftest_ok": "selftest: pass=" in payload(steps, "selftest") and "fail=0" in payload(steps, "selftest"),
        "all_steps_ok": all(bool(step.get("ok")) for step in steps),
        "step_status": {str(step.get("name")): bool(step.get("ok")) for step in steps},
        "subsys_count": len(blocks),
        "mss_or_modem_state": find_state(blocks, ("mss", "modem")),
        "mdm3_state": find_state(blocks, ("mdm3", "esoc0")),
        "esoc_surface_present": "== /sys/bus/esoc/devices ==" in esoc_text and "esoc0" in esoc_text,
        "icnss_platform_present": "18800000.qcom,icnss" in icnss_text,
        "wlan0_present": "/sys/class/net/wlan0" in icnss_text and "No such file" not in icnss_text,
        "dev_qcwlanstate_present": "/dev/qcwlanstate" in icnss_text and "No such file" not in icnss_text,
        "runtime_counts": runtime_counts,
        "surface_counts": surface_counts,
        "counts": runtime_counts,
    }


def build_checks(command: str,
                 args: argparse.Namespace,
                 v814: dict[str, Any],
                 steps: list[dict[str, Any]],
                 analysis: dict[str, Any],
                 missing_flags: list[str]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "read-only snapshot plan; no device command executed",
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
            "name": "v814-route-ready",
            "status": "pass"
            if v814.get("pass") is True
            and v814.get("decision") == "v814-source-routes-to-subsystem-sysmon-registration-snapshot"
            else "blocked",
            "detail": {"decision": v814.get("decision"), "pass": v814.get("pass")},
            "next_step": "complete V814 before live snapshot",
        },
        {
            "name": "runtime-health",
            "status": "pass" if analysis.get("version_ok") and analysis.get("selftest_ok") else "blocked",
            "detail": {"version_ok": analysis.get("version_ok"), "selftest_ok": analysis.get("selftest_ok")},
            "next_step": "restore healthy stock v724 before interpreting snapshot",
        },
        {
            "name": "read-only-command-success",
            "status": "pass" if analysis.get("all_steps_ok") else "blocked",
            "detail": analysis.get("step_status"),
            "next_step": "fix bridge/runtime command failures before using snapshot",
        },
        {
            "name": "subsystem-surface",
            "status": "pass" if analysis.get("subsys_count", 0) > 0 else "blocked",
            "detail": {
                "subsys_count": analysis.get("subsys_count"),
                "mss_or_modem_state": analysis.get("mss_or_modem_state"),
                "mdm3_state": analysis.get("mdm3_state"),
            },
            "next_step": "if absent, classify why msm_subsys sysfs is unavailable",
        },
        {
            "name": "read-only-wifi-surface",
            "status": "pass",
            "detail": {
                "icnss_platform_present": analysis.get("icnss_platform_present"),
                "wlan0_present": analysis.get("wlan0_present"),
                "dev_qcwlanstate_present": analysis.get("dev_qcwlanstate_present"),
                "esoc_surface_present": analysis.get("esoc_surface_present"),
            },
            "next_step": "use only as read-only state; do not bind/unbind or open esoc0",
        },
    ]


def decide(command: str,
           checks: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v815-subsystem-sysmon-snapshot-plan-ready",
            True,
            "plan-only; no device command executed",
            "run read-only stock-v724 snapshot",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v815-subsystem-sysmon-snapshot-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "clear read-only snapshot blocker before routing next gate",
        )
    counts = analysis.get("runtime_counts", analysis.get("counts", {}))
    if counts.get("service_notifier_74", 0) > 0 or counts.get("wlan_pd", 0) > 0 or counts.get("wlfw", 0) > 0:
        return (
            "v815-service-publication-visible-at-idle",
            True,
            "read-only snapshot saw service-publication/WLAN-PD/WLFW markers without a new trigger",
            "capture WLFW/service69/BDF readiness before any HAL or connect attempt",
        )
    return (
        "v815-idle-registration-snapshot-captured",
        True,
        "read-only stock-v724 snapshot captured subsystem/sysmon/service-locator surfaces; no idle service74/WLAN-PD/WLFW publication is visible",
        "V816 should collect the same read-only surfaces around the bounded lower trigger window and compare idle-vs-trigger deltas",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v814 = load_json(args.v814_manifest)
    missing_flags = required_flags(args) if args.command == "run" else []
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    if args.command == "run" and not missing_flags:
        steps = collect_steps(args, store)
        analysis = analyze(args, steps)
    checks = build_checks(args.command, args, v814, steps, analysis, missing_flags)
    decision, pass_ok, reason, next_step = decide(args.command, checks, analysis)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v815",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v814_manifest": str(resolve(args.v814_manifest)),
            "v814_decision": v814.get("decision"),
            "v814_pass": v814.get("pass"),
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
        "esoc0_open_executed": False,
        "bind_unbind_executed": False,
        "module_load_unload_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    analysis_rows = [
        [key, json.dumps(value, sort_keys=True)]
        for key, value in manifest.get("analysis", {}).items()
        if key != "step_status"
    ]
    step_rows = [
        [str(step.get("name")), str(step.get("ok")), str(step.get("status")), str(step.get("file"))]
        for step in manifest.get("steps", [])
    ]
    return "\n".join([
        "# V815 Subsystem/Sysmon Snapshot",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Analysis",
        "",
        markdown_table(["signal", "value"], analysis_rows),
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
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
