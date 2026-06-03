#!/usr/bin/env python3
"""V1890 dry-run/read-only Android PM msg-id log capture runner."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1890-android-pm-msgid-log-capture-runner"
DEFAULT_REPORT_PATH = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1890_ANDROID_PM_MSGID_LOG_CAPTURE_RUNNER_2026-06-03.md"
)
DEFAULT_CONTRACT_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1887-normal-android-pm-msgid-capture-contract" / "manifest.json"
)
DEFAULT_PARSER = REPO_ROOT / "scripts" / "revalidation" / "native_wifi_pm_msgid_capture_diff_classifier_v1888.py"

FILTER = (
    "PerMgrSrv|PerMgrLib|QMI service|QMI client|peripheral restart|system restart|system shutdown|"
    "cnss-daemon|wlfw_service_request|WLFW service connected|wlanmdsp|tftp_server|"
    "service-notifier|servloc|sysmon-qmi|icnss_qmi|icnss|wlan_pd|wlan0|PCIe|MHI|"
    "esoc0.*boot.*fail|boot_failed"
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def redact(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(serialno|ap_serial|androidboot\.serialno)=([^\s]+)", r"\1=<redacted>", text)
    text = re.sub(r"(?i)(ssid|bssid|psk|passphrase)=([^\s]+)", r"\1=<redacted>", text)
    return text


def quote(command: str) -> str:
    return shlex.quote(command)


def adb_base(adb: str, serial: str | None) -> list[str]:
    command = [adb]
    if serial:
        command.extend(["-s", serial])
    return command


def adb_shell(adb: str, serial: str | None, shell_command: str, use_su: bool) -> list[str]:
    base = [*adb_base(adb, serial), "shell"]
    if use_su:
        return [*base, "su", "-c", quote(shell_command)]
    return [*base, shell_command]


def run_command(command: list[str], timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        return {
            "command": command,
            "rc": proc.returncode,
            "ok": proc.returncode == 0,
            "timeout": False,
            "duration_s": round(time.monotonic() - started, 3),
            "text": redact(proc.stdout),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "rc": None,
            "ok": False,
            "timeout": True,
            "duration_s": round(time.monotonic() - started, 3),
            "text": redact((exc.stdout or "") if isinstance(exc.stdout, str) else ""),
        }


def capture_commands(adb: str, serial: str | None, use_su: bool) -> list[dict[str, Any]]:
    grep_filter = quote(FILTER)
    return [
        {
            "name": "identity-props",
            "kind": "shell",
            "timeout_s": 15,
            "outfile": "android/identity-props.txt",
            "command": adb_shell(
                adb,
                serial,
                "for p in sys.boot_completed dev.bootcomplete ro.product.name ro.hardware ro.boot.verifiedbootstate ro.boot.vbmeta.device_state; do echo \"$p=$(getprop $p 2>/dev/null)\"; done",
                use_su,
            ),
        },
        {
            "name": "process-targets",
            "kind": "shell",
            "timeout_s": 20,
            "outfile": "android/process-targets.txt",
            "command": adb_shell(
                adb,
                serial,
                "ps -A -o USER,PID,PPID,STAT,COMM,ARGS 2>/dev/null | grep -Ei 'pm-service|per_mgr|cnss-daemon|tftp_server|rmt_storage|service-notifier|servloc|sysmon-qmi' || true",
                use_su,
            ),
        },
        {
            "name": "init-service-props",
            "kind": "shell",
            "timeout_s": 20,
            "outfile": "android/init-service-props.txt",
            "command": adb_shell(
                adb,
                serial,
                "getprop | grep -Ei 'init\\.svc\\..*(pm-service|per_mgr|cnss|tftp|rmt|service-notifier|servloc|sysmon)|ro\\.boottime\\..*(pm-service|per_mgr|cnss|tftp|rmt|service-notifier|servloc|sysmon)' || true",
                use_su,
            ),
        },
        {
            "name": "proc-net-qrtr",
            "kind": "shell",
            "timeout_s": 15,
            "outfile": "android/proc-net-qrtr.txt",
            "command": adb_shell(adb, serial, "cat /proc/net/qrtr 2>/dev/null || true", use_su),
        },
        {
            "name": "dmesg-filtered",
            "kind": "shell",
            "timeout_s": 60,
            "outfile": "android/dmesg-filtered.txt",
            "command": adb_shell(adb, serial, f"dmesg 2>/dev/null | grep -Ei {grep_filter} | tail -n 2000 || true", use_su),
        },
        {
            "name": "logcat-filtered",
            "kind": "shell",
            "timeout_s": 90,
            "outfile": "android/logcat-filtered.txt",
            "command": adb_shell(
                adb,
                serial,
                f"logcat -b all -d -v threadtime 2>/dev/null | grep -Ei {grep_filter} | tail -n 3000 || true",
                use_su,
            ),
        },
        {
            "name": "request-lines",
            "kind": "host-compose",
            "timeout_s": 0,
            "outfile": "android/request-lines.txt",
            "command": [],
        },
    ]


def write_shell_script(path: Path, commands: list[dict[str, Any]]) -> None:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "OUT=${1:?output directory}",
        "mkdir -p \"$OUT/android\"",
    ]
    for item in commands:
        if item["kind"] != "shell":
            continue
        cmdline = " ".join(shlex.quote(part) for part in item["command"])
        lines.append(f"{cmdline} > \"$OUT/{item['outfile']}\" 2>&1 || true")
    lines.append("cat \"$OUT/android/dmesg-filtered.txt\" \"$OUT/android/logcat-filtered.txt\" 2>/dev/null | grep -Ei 'QMI service|QMI client|peripheral restart|wlanmdsp|wlan_pd|service-notifier|wlan0|PerMgr|wlfw' > \"$OUT/android/request-lines.txt\" || true")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)


def execute_capture(store: EvidenceStore, commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    executed: list[dict[str, Any]] = []
    captured: dict[str, str] = {}
    for item in commands:
        if item["kind"] == "shell":
            result = run_command(item["command"], float(item["timeout_s"]))
            text = result.pop("text")
            store.write_text(item["outfile"], text)
            captured[item["outfile"]] = text
            result["outfile"] = item["outfile"]
            result["name"] = item["name"]
            executed.append(result)
        elif item["kind"] == "host-compose":
            text = "\n".join(
                line
                for source in ("android/dmesg-filtered.txt", "android/logcat-filtered.txt")
                for line in captured.get(source, "").splitlines()
                if re.search(r"QMI service|QMI client|peripheral restart|wlanmdsp|wlan_pd|service-notifier|wlan0|PerMgr|wlfw", line, re.IGNORECASE)
            )
            store.write_text(item["outfile"], text + ("\n" if text else ""))
            executed.append({"name": item["name"], "kind": item["kind"], "ok": True, "rc": 0, "outfile": item["outfile"]})
    return executed


def classify(contract: dict[str, Any], execute: bool, adb_state: dict[str, Any] | None, executed: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if contract.get("label") != "normal-android-pm-msgid-capture-contract-ready":
        return (
            "v1890-contract-not-ready",
            False,
            "V1887 capture contract is not ready",
            "android-pm-msgid-log-capture-contract-missing",
        )
    if not execute:
        return (
            "v1890-android-pm-msgid-log-capture-runner-dry-run-pass",
            True,
            "dry-run generated a read-only normal-Android PM msg-id capture runner without contacting the device",
            "android-pm-msgid-log-capture-runner-ready",
        )
    device_count = 0 if adb_state is None else len(adb_state.get("devices") or [])
    if device_count == 0:
        return (
            "v1890-adb-device-absent-no-capture-host-pass",
            True,
            "execute mode requested but no Android ADB device is attached",
            "adb-device-absent-no-capture",
        )
    if not all(item.get("ok") for item in executed):
        return (
            "v1890-android-log-capture-command-failed-host-pass",
            True,
            "one or more read-only Android capture commands failed",
            "android-log-capture-command-failed",
        )
    return (
        "v1890-android-pm-msgid-log-capture-collected-host-pass",
        True,
        "read-only Android PM msg-id log capture was collected",
        "android-pm-msgid-log-capture-collected",
    )


def adb_devices(adb: str, serial: str | None) -> dict[str, Any]:
    result = run_command([*adb_base(adb, serial), "devices", "-l"], 10)
    devices: list[str] = []
    for raw in result["text"].splitlines()[1:]:
        fields = raw.split()
        if len(fields) >= 2 and fields[1] == "device":
            devices.append(fields[0])
    result["devices"] = devices
    return result


def render_report(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Native Init V1890 Android PM Msg-id Log Capture Runner",
            "",
            "## Summary",
            "",
            "- Cycle: `V1890`",
            "- Type: dry-run/read-only Android normal-boot PM msg-id log capture runner",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Runner",
            "",
            f"- execute mode: `{result['execute']}`",
            f"- use su: `{result['use_su']}`",
            f"- command count: `{len(result['commands'])}`",
            f"- generated shell script: `{result['shell_script']}`",
            f"- parser: `{result['parser']}`",
            f"- contract decision/label/pass: `{result['contract_decision']}` / `{result['contract_label']}` / `{result['contract_pass']}`",
            "",
            "## Command Targets",
            "",
            "- Captures read-only identity props, target processes, init service props, `/proc/net/qrtr`, filtered `dmesg`, filtered `logcat -b all`, and a composed `request-lines.txt`.",
            "- Filters include `PerMgrSrv`, `PerMgrLib`, `QMI service`, `QMI client`, `peripheral restart`, `cnss-daemon`, `service-notifier`, `servloc`, `sysmon-qmi`, `wlanmdsp`, `wlan_pd`, `wlan0`, PCIe/MHI contamination terms, and degraded-boot terms.",
            "- Output names match V1888 parser inputs: `android/logcat-filtered.txt`, `android/dmesg-filtered.txt`, and `android/request-lines.txt`.",
            "",
            "## Selected Diff",
            "",
            f"- Label: `{result['label']}`.",
            "- Current state still lacks Android ADB, so no live Android capture was attempted.",
            "- The runner is ready to collect a fresh normal Android boot log surface with broader pm-service msg-id visibility than the retained V1753 filtered sample.",
            "- V1888 should be run against the collected `android/` directory; promote only if msg `0x22` appears before `wlanmdsp.mbn` on a normal non-PCIe/MHI boot.",
            "",
            "## Safety Scope",
            "",
            "V1890 dry-run is host-only. In execute mode it runs only read-only Android ADB shell commands and writes host evidence files. It performs no flash, reboot, property staging, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or device partition write.",
            "",
            "## Next",
            "",
            "- Use execute mode only after booting normal Android with ADB/root available; reject degraded 257s or pre-wlan0 PCIe/MHI captures.",
            "- Keep native init at v724/selftest fail=0 until a bounded rollbackable internal-modem gate is justified.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--contract-manifest", type=Path, default=DEFAULT_CONTRACT_MANIFEST)
    parser.add_argument("--parser", type=Path, default=DEFAULT_PARSER)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial")
    parser.add_argument("--no-su", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    store = EvidenceStore(args.out_dir)
    contract = read_json(args.contract_manifest)
    use_su = not args.no_su
    commands = capture_commands(args.adb, args.serial, use_su)
    host_dir = args.out_dir / "host"
    host_dir.mkdir(parents=True, exist_ok=True)
    shell_script = host_dir / "android-pm-msgid-log-capture.sh"
    write_shell_script(shell_script, commands)
    store.write_text("host/android-pm-msgid-log-capture-commands.json", json.dumps(commands, indent=2, sort_keys=True) + "\n")

    adb_state: dict[str, Any] | None = None
    executed: list[dict[str, Any]] = []
    if args.execute:
        adb_state = adb_devices(args.adb, args.serial)
        store.write_text("host/adb-devices.json", json.dumps(adb_state, indent=2, sort_keys=True) + "\n")
        if adb_state.get("devices"):
            executed = execute_capture(store, commands)
            store.write_text("host/executed-commands.json", json.dumps(executed, indent=2, sort_keys=True) + "\n")

    decision, passed, reason, label = classify(contract, args.execute, adb_state, executed)
    result = {
        "cycle": "V1890",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
        "execute": args.execute,
        "use_su": use_su,
        "commands": commands,
        "shell_script": rel(shell_script),
        "parser": rel(args.parser),
        "contract_manifest": rel(args.contract_manifest),
        "contract_decision": contract.get("decision", ""),
        "contract_label": contract.get("label", ""),
        "contract_pass": bool(contract.get("pass")),
        "adb_state": adb_state,
        "executed": executed,
        "safety": {
            "dry_run_host_only": not args.execute,
            "device_contact": bool(args.execute),
            "flash": False,
            "reboot": False,
            "tracefs_write": False,
            "service_start": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credential_use": False,
            "dhcp_routes": False,
            "external_ping": False,
            "pmic_gpio_gdsc_write": False,
            "forced_rc1_case": False,
            "subsys_esoc0_open": False,
            "pci_rescan": False,
            "platform_bind_unbind": False,
        },
    }
    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "summary.md", render_report(result))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(args.report, render_report(result))
    print(json.dumps({key: result[key] for key in ("decision", "pass", "label", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
