#!/usr/bin/env python3
"""V1896 host-only chain for normal-Android trigger capture parsing."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1896-normal-android-trigger-capture-chain"
DEFAULT_REPORT_PATH = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1896_NORMAL_ANDROID_TRIGGER_CAPTURE_CHAIN_2026-06-03.md"
)
DEFAULT_V1890_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1890-android-pm-msgid-log-capture-runner" / "manifest.json"
)
DEFAULT_V1894_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1894-android-pending-client-msg22-parser" / "manifest.json"
)
DEFAULT_V1888_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1888-pm-msgid-capture-diff-classifier" / "manifest.json"
DEFAULT_V1895_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1895-pending-client-capture-filter-audit" / "manifest.json"
)
DEFAULT_COMMANDS_JSON = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1890-android-pm-msgid-log-capture-runner"
    / "host"
    / "android-pm-msgid-log-capture-commands.json"
)
DEFAULT_RUNNER = REPO_ROOT / "scripts" / "revalidation" / "native_wifi_android_pm_msgid_log_capture_runner_v1890.py"
DEFAULT_PENDING_PARSER = (
    REPO_ROOT / "scripts" / "revalidation" / "native_wifi_android_pending_client_msg22_parser_v1894.py"
)
DEFAULT_MSGID_PARSER = REPO_ROOT / "scripts" / "revalidation" / "native_wifi_pm_msgid_capture_diff_classifier_v1888.py"
FUTURE_CAPTURE_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1896-normal-android-trigger-capture"
FUTURE_PENDING_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1896-normal-android-pending-client-diff"
FUTURE_MSGID_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1896-normal-android-msgid-diff"
REQUIRED_ANDROID_OUTPUTS = (
    "android/logcat-filtered.txt",
    "android/dmesg-filtered.txt",
    "android/request-lines.txt",
)
REQUIRED_FILTER_TERMS = (
    "PerMgrSrv",
    "QMI client",
    "QMI service",
    "peripheral restart",
    "wlanmdsp",
    "wlan_pd",
    "wlfw_service_request",
)
FORBIDDEN_COMMAND_RE = re.compile(
    r"svc wifi|cmd wifi|wpa_cli|iw\b|iwpriv|ifconfig wlan0|ip link set|dhcp|ping|"
    r"/dev/subsys_esoc0|\brescan\b|/bind\b|/unbind\b|BOOT_DONE|notify.*boot|"
    r"gdsc|pmic|gpio|regulator",
    re.IGNORECASE,
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def command_outputs(commands: Any) -> list[str]:
    if not isinstance(commands, list):
        return []
    outputs: list[str] = []
    for item in commands:
        if not isinstance(item, dict):
            continue
        outfile = item.get("outfile")
        if isinstance(outfile, str) and outfile:
            outputs.append(outfile)
    return outputs


def command_text(commands: Any) -> str:
    if not isinstance(commands, list):
        return ""
    rendered: list[str] = []
    for item in commands:
        if not isinstance(item, dict):
            continue
        command = item.get("command") or []
        if isinstance(command, list):
            rendered.append(" ".join(str(part) for part in command))
        elif isinstance(command, str):
            rendered.append(command)
    return "\n".join(rendered)


def chain_commands(capture_out_dir: Path, pending_out_dir: Path, msgid_out_dir: Path) -> list[str]:
    android_dir = capture_out_dir / "android"
    return [
        (
            "python3 scripts/revalidation/native_wifi_android_pm_msgid_log_capture_runner_v1890.py "
            f"--execute --out-dir {rel(capture_out_dir)}"
        ),
        (
            "python3 scripts/revalidation/native_wifi_android_pending_client_msg22_parser_v1894.py "
            f"--android-dir {rel(android_dir)} --out-dir {rel(pending_out_dir)}"
        ),
        (
            "python3 scripts/revalidation/native_wifi_pm_msgid_capture_diff_classifier_v1888.py "
            f"--android-dir {rel(android_dir)} --out-dir {rel(msgid_out_dir)}"
        ),
    ]


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    v1890 = read_json(args.v1890_manifest)
    v1894 = read_json(args.v1894_manifest)
    v1888 = read_json(args.v1888_manifest)
    v1895 = read_json(args.v1895_manifest)
    commands = read_json(args.commands_json)
    outputs = command_outputs(commands)
    text = command_text(commands)
    future_commands = chain_commands(args.future_capture_out_dir, args.future_pending_out_dir, args.future_msgid_out_dir)
    checks = {
        "v1890_runner_ready": (
            boolish(v1890.get("pass")) and v1890.get("label") == "android-pm-msgid-log-capture-runner-ready"
        ),
        "v1894_pending_parser_ready": (
            boolish(v1894.get("pass"))
            and v1894.get("label") == "android-stateup-pending-client-observability-gap"
        ),
        "v1888_msgid_parser_ready": (
            boolish(v1888.get("pass"))
            and v1888.get("label") == "android-stateup-without-msg22-log-observability-gap"
        ),
        "v1895_qmi_client_filter_ready": (
            boolish(v1895.get("pass"))
            and v1895.get("label") == "pending-client-capture-filter-qmi-client-covered"
        ),
        "scripts_present": args.runner.exists() and args.pending_parser.exists() and args.msgid_parser.exists(),
        "required_outputs_declared": all(output in outputs for output in REQUIRED_ANDROID_OUTPUTS),
        "required_filter_terms_present": all(term in text for term in REQUIRED_FILTER_TERMS),
        "forbidden_command_surface_absent": not FORBIDDEN_COMMAND_RE.search(text),
    }
    if all(checks.values()):
        decision = "v1896-normal-android-trigger-capture-chain-host-pass"
        label = "normal-android-trigger-capture-chain-ready"
        reason = "fresh normal-Android capture handoff is ready for V1894 pending-client parsing and V1888 msg-id diffing"
        passed = True
    else:
        decision = "v1896-normal-android-trigger-capture-chain-incomplete"
        label = "normal-android-trigger-capture-chain-incomplete"
        reason = "runner, parsers, filter terms, or required output declarations are incomplete"
        passed = False
    return {
        "cycle": "V1896",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
        "inputs": {
            "v1890_manifest": rel(args.v1890_manifest),
            "v1894_manifest": rel(args.v1894_manifest),
            "v1888_manifest": rel(args.v1888_manifest),
            "v1895_manifest": rel(args.v1895_manifest),
            "commands_json": rel(args.commands_json),
            "runner": rel(args.runner),
            "pending_parser": rel(args.pending_parser),
            "msgid_parser": rel(args.msgid_parser),
        },
        "checks": checks,
        "required_android_outputs": list(REQUIRED_ANDROID_OUTPUTS),
        "required_filter_terms": list(REQUIRED_FILTER_TERMS),
        "command_outputs": outputs,
        "future_capture_out_dir": rel(args.future_capture_out_dir),
        "future_pending_out_dir": rel(args.future_pending_out_dir),
        "future_msgid_out_dir": rel(args.future_msgid_out_dir),
        "future_commands": future_commands,
        "safety": {
            "host_only": True,
            "live_capture_executed": False,
            "device_contact": False,
            "flash": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credential_use": False,
            "dhcp_routes": False,
            "external_ping": False,
            "pmic_gpio_gdsc_write": False,
            "forced_rc1_case": False,
            "subsys_esoc0_open": False,
            "esoc_notify_boot_done": False,
            "pci_rescan": False,
            "platform_bind_unbind": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    safety = result["safety"]
    future_commands = result["future_commands"]
    return "\n".join(
        [
            "# Native Init V1896 Normal Android Trigger Capture Chain",
            "",
            "## Summary",
            "",
            "- Cycle: `V1896`",
            "- Type: host-only chain gate for normal-Android trigger capture parsing",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Chain Checks",
            "",
            f"- V1890/V1894/V1888 ready: `{checks['v1890_runner_ready']}` / `{checks['v1894_pending_parser_ready']}` / `{checks['v1888_msgid_parser_ready']}`",
            f"- V1895 QMI-client filter ready: `{checks['v1895_qmi_client_filter_ready']}`",
            f"- scripts present: `{checks['scripts_present']}`",
            f"- required outputs/filter terms: `{checks['required_outputs_declared']}` / `{checks['required_filter_terms_present']}`",
            f"- forbidden command surface absent: `{checks['forbidden_command_surface_absent']}`",
            f"- required Android outputs: `{json.dumps(result['required_android_outputs'])}`",
            f"- required filter terms: `{json.dumps(result['required_filter_terms'])}`",
            "",
            "## Future Chain",
            "",
            f"- Capture output dir: `{result['future_capture_out_dir']}`",
            f"- Pending-client diff dir: `{result['future_pending_out_dir']}`",
            f"- Msg-id diff dir: `{result['future_msgid_out_dir']}`",
            f"- Capture command: `{future_commands[0]}`",
            f"- Pending-client parser: `{future_commands[1]}`",
            f"- Msg-id parser: `{future_commands[2]}`",
            "",
            "## Selected Diff",
            "",
            f"- Label: `{result['label']}`.",
            "- The next useful live evidence is a normal Android ADB/root capture across PM vote to first `wlanmdsp.mbn`.",
            "- V1894 now tests the narrowed V1893 pending-client/msg22 edge; V1888 tests the broader pm-service msg-id/servreg transition.",
            "- A capture promotes only if pending-client/msg22, servreg, or SSCTL evidence appears before `wlanmdsp.mbn` on a normal non-PCIe/MHI boot.",
            "",
            "## Safety Scope",
            "",
            f"- host-only/device-contact/live-capture: `{safety['host_only']}` / `{safety['device_contact']}` / `{safety['live_capture_executed']}`",
            f"- Wi-Fi HAL/scan-connect/credential/DHCP/routes/ping: `{safety['wifi_hal']}` / `{safety['scan_connect']}` / `{safety['credential_use']}` / `{safety['dhcp_routes']}` / `{safety['external_ping']}`",
            f"- PMIC-GPIO-GDSC/forced-RC1/subsys-esoc0/eSoC notify/PCI rescan/platform bind: `{safety['pmic_gpio_gdsc_write']}` / `{safety['forced_rc1_case']}` / `{safety['subsys_esoc0_open']}` / `{safety['esoc_notify_boot_done']}` / `{safety['pci_rescan']}` / `{safety['platform_bind_unbind']}`",
            "",
            "## Next",
            "",
            "- Run the capture command only on normal Android with ADB/root available; reject degraded 257s captures and any pre-wlan0 PCIe/MHI path.",
            "- Parse the captured `android/` directory with both listed parsers before any native trigger replay.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1890-manifest", type=Path, default=DEFAULT_V1890_MANIFEST)
    parser.add_argument("--v1894-manifest", type=Path, default=DEFAULT_V1894_MANIFEST)
    parser.add_argument("--v1888-manifest", type=Path, default=DEFAULT_V1888_MANIFEST)
    parser.add_argument("--v1895-manifest", type=Path, default=DEFAULT_V1895_MANIFEST)
    parser.add_argument("--commands-json", type=Path, default=DEFAULT_COMMANDS_JSON)
    parser.add_argument("--runner", type=Path, default=DEFAULT_RUNNER)
    parser.add_argument("--pending-parser", type=Path, default=DEFAULT_PENDING_PARSER)
    parser.add_argument("--msgid-parser", type=Path, default=DEFAULT_MSGID_PARSER)
    parser.add_argument("--future-capture-out-dir", type=Path, default=FUTURE_CAPTURE_OUT_DIR)
    parser.add_argument("--future-pending-out-dir", type=Path, default=FUTURE_PENDING_OUT_DIR)
    parser.add_argument("--future-msgid-out-dir", type=Path, default=FUTURE_MSGID_OUT_DIR)
    args = parser.parse_args()

    result = analyze(args)
    store = EvidenceStore(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    store.write_text("host/chain-checks.json", json.dumps(result["checks"], indent=2, sort_keys=True) + "\n")
    store.write_text("host/chain-commands.txt", "\n".join(result["future_commands"]) + "\n")
    store.write_text("host/command-outputs.json", json.dumps(result["command_outputs"], indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "summary.md", render_report(result))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(args.report, render_report(result))
    print(json.dumps({key: result[key] for key in ("decision", "pass", "label", "out_dir", "report")}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
