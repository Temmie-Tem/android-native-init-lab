#!/usr/bin/env python3
"""V1891 host-only handoff from Android PM msg-id capture runner to parser."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1891-android-capture-parser-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1891_ANDROID_CAPTURE_PARSER_HANDOFF_2026-06-03.md"
)
DEFAULT_V1887_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1887-normal-android-pm-msgid-capture-contract" / "manifest.json"
)
DEFAULT_V1888_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1888-pm-msgid-capture-diff-classifier" / "manifest.json"
DEFAULT_V1890_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1890-android-pm-msgid-log-capture-runner" / "manifest.json"
)
DEFAULT_CAPTURE_SCRIPT = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1890-android-pm-msgid-log-capture-runner"
    / "host"
    / "android-pm-msgid-log-capture.sh"
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
DEFAULT_PARSER = REPO_ROOT / "scripts" / "revalidation" / "native_wifi_pm_msgid_capture_diff_classifier_v1888.py"
FUTURE_CAPTURE_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1891-normal-android-capture-run"
FUTURE_DIFF_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1891-normal-android-capture-diff"
REQUIRED_ANDROID_OUTPUTS = (
    "android/logcat-filtered.txt",
    "android/dmesg-filtered.txt",
    "android/request-lines.txt",
)
EXPECTED_COMMAND_OUTPUTS = (
    "android/identity-props.txt",
    "android/process-targets.txt",
    "android/init-service-props.txt",
    "android/proc-net-qrtr.txt",
    "android/dmesg-filtered.txt",
    "android/logcat-filtered.txt",
    "android/request-lines.txt",
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


def command_texts(commands: Any) -> list[str]:
    if not isinstance(commands, list):
        return []
    texts: list[str] = []
    for item in commands:
        if not isinstance(item, dict):
            continue
        command = item.get("command") or []
        if isinstance(command, list):
            texts.append(" ".join(str(part) for part in command))
        elif isinstance(command, str):
            texts.append(command)
    return texts


def handoff_commands(capture_out_dir: Path, diff_out_dir: Path) -> list[str]:
    android_dir = capture_out_dir / "android"
    return [
        (
            "python3 scripts/revalidation/native_wifi_android_pm_msgid_log_capture_runner_v1890.py "
            f"--execute --out-dir {rel(capture_out_dir)}"
        ),
        (
            "python3 scripts/revalidation/native_wifi_pm_msgid_capture_diff_classifier_v1888.py "
            f"--android-dir {rel(android_dir)} --out-dir {rel(diff_out_dir)}"
        ),
    ]


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    v1887 = read_json(args.v1887_manifest)
    v1888 = read_json(args.v1888_manifest)
    v1890 = read_json(args.v1890_manifest)
    commands = read_json(args.commands_json)
    outputs = command_outputs(commands)
    texts = command_texts(commands)
    missing_required_outputs = [name for name in REQUIRED_ANDROID_OUTPUTS if name not in outputs]
    missing_expected_outputs = [name for name in EXPECTED_COMMAND_OUTPUTS if name not in outputs]
    forbidden_hits = [text for text in texts if FORBIDDEN_COMMAND_RE.search(text)]
    capture_script_ok = args.capture_script.exists() and args.capture_script.stat().st_mode & 0o111 != 0
    runner_ok = args.runner.exists()
    parser_ok = args.parser.exists()
    contract_ok = (
        boolish(v1887.get("pass"))
        and v1887.get("label") == "normal-android-pm-msgid-capture-contract-ready"
    )
    prior_diff_ok = (
        boolish(v1888.get("pass"))
        and v1888.get("label") == "android-stateup-without-msg22-log-observability-gap"
    )
    runner_manifest_ok = (
        boolish(v1890.get("pass"))
        and v1890.get("label") == "android-pm-msgid-log-capture-runner-ready"
        and v1890.get("parser") == rel(args.parser)
        and boolish(v1890.get("contract_pass"))
        and v1890.get("contract_label") == "normal-android-pm-msgid-capture-contract-ready"
    )
    safety = {
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
    }
    checks = {
        "v1887_contract_ready": contract_ok,
        "v1888_observability_gap_ready": prior_diff_ok,
        "v1890_runner_manifest_ready": runner_manifest_ok,
        "capture_script_exists_executable": capture_script_ok,
        "runner_script_exists": runner_ok,
        "parser_script_exists": parser_ok,
        "required_parser_inputs_declared": not missing_required_outputs,
        "all_expected_outputs_declared": not missing_expected_outputs,
        "forbidden_command_surface_absent": not forbidden_hits,
    }
    if all(checks.values()):
        decision = "v1891-android-capture-parser-handoff-host-pass"
        label = "android-capture-parser-handoff-ready"
        reason = "V1890 runner outputs satisfy the V1888 parser input contract; future normal-Android capture and parser commands are fixed"
        passed = True
    else:
        decision = "v1891-android-capture-parser-handoff-blocked"
        label = "android-capture-parser-handoff-incomplete"
        reason = "runner, contract, parser, or required output declarations are incomplete"
        passed = False
    commands_to_run = handoff_commands(args.future_capture_out_dir, args.future_diff_out_dir)
    return {
        "cycle": "V1891",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
        "inputs": {
            "v1887_manifest": rel(args.v1887_manifest),
            "v1888_manifest": rel(args.v1888_manifest),
            "v1890_manifest": rel(args.v1890_manifest),
            "capture_script": rel(args.capture_script),
            "commands_json": rel(args.commands_json),
            "runner": rel(args.runner),
            "parser": rel(args.parser),
        },
        "checks": checks,
        "command_outputs": outputs,
        "required_parser_inputs": list(REQUIRED_ANDROID_OUTPUTS),
        "missing_required_outputs": missing_required_outputs,
        "missing_expected_outputs": missing_expected_outputs,
        "forbidden_command_hits": forbidden_hits,
        "future_commands": commands_to_run,
        "future_capture_out_dir": rel(args.future_capture_out_dir),
        "future_diff_out_dir": rel(args.future_diff_out_dir),
        "safety": safety,
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    inputs = result["inputs"]
    safety = result["safety"]
    future_commands = result["future_commands"]
    return "\n".join(
        [
            "# Native Init V1891 Android Capture Parser Handoff",
            "",
            "## Summary",
            "",
            "- Cycle: `V1891`",
            "- Type: host-only handoff gate from normal-Android PM msg-id capture runner to parser",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Inputs",
            "",
            f"- V1887 contract: `{inputs['v1887_manifest']}`",
            f"- V1888 parser baseline: `{inputs['v1888_manifest']}`",
            f"- V1890 runner manifest: `{inputs['v1890_manifest']}`",
            f"- V1890 generated shell: `{inputs['capture_script']}`",
            f"- V1890 command manifest: `{inputs['commands_json']}`",
            f"- Parser script: `{inputs['parser']}`",
            "",
            "## Handoff Checks",
            "",
            f"- contract/diff/runner ready: `{checks['v1887_contract_ready']}` / `{checks['v1888_observability_gap_ready']}` / `{checks['v1890_runner_manifest_ready']}`",
            f"- shell/runner/parser present: `{checks['capture_script_exists_executable']}` / `{checks['runner_script_exists']}` / `{checks['parser_script_exists']}`",
            f"- required parser inputs declared: `{checks['required_parser_inputs_declared']}`",
            f"- expected outputs declared: `{checks['all_expected_outputs_declared']}`",
            f"- forbidden command surface absent: `{checks['forbidden_command_surface_absent']}`",
            f"- required parser inputs: `{json.dumps(result['required_parser_inputs'])}`",
            f"- missing required/expected outputs: `{json.dumps(result['missing_required_outputs'])}` / `{json.dumps(result['missing_expected_outputs'])}`",
            "",
            "## Future Handoff",
            "",
            f"- Capture output dir: `{result['future_capture_out_dir']}`",
            f"- Diff output dir: `{result['future_diff_out_dir']}`",
            f"- Capture command: `{future_commands[0]}`",
            f"- Parser command: `{future_commands[1]}`",
            "",
            "## Selected Diff",
            "",
            f"- Label: `{result['label']}`.",
            "- The unresolved comparison remains internal-modem PM post-vote to WLAN guest-PD load, not SDX50M/eSoC/PCIe/GDSC.",
            "- V1890 declares the exact Android files consumed by V1888: `logcat-filtered.txt`, `dmesg-filtered.txt`, and `request-lines.txt` under the captured `android/` directory.",
            "- The next useful live evidence is a normal Android ADB/root capture across per_mgr vote to first `wlanmdsp.mbn`, then immediate V1888 parsing of that captured `android/` directory.",
            "",
            "## Safety Scope",
            "",
            f"- host-only/device-contact/live-capture: `{safety['host_only']}` / `{safety['device_contact']}` / `{safety['live_capture_executed']}`",
            f"- Wi-Fi HAL/scan-connect/credential/DHCP/routes/ping: `{safety['wifi_hal']}` / `{safety['scan_connect']}` / `{safety['credential_use']}` / `{safety['dhcp_routes']}` / `{safety['external_ping']}`",
            f"- PMIC-GPIO-GDSC/forced-RC1/subsys-esoc0/eSoC notify/PCI rescan/platform bind: `{safety['pmic_gpio_gdsc_write']}` / `{safety['forced_rc1_case']}` / `{safety['subsys_esoc0_open']}` / `{safety['esoc_notify_boot_done']}` / `{safety['pci_rescan']}` / `{safety['platform_bind_unbind']}`",
            "",
            "## Next",
            "",
            "- Run the capture command only on a normal Android boot with ADB/root available; reject degraded 257s captures or any pre-wlan0 PCIe/MHI path.",
            "- Promote only if V1888 sees Android msg `0x22` before `wlanmdsp.mbn` while native post-open still lacks msg22/WLFW69/wlanmdsp/wlan0.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1887-manifest", type=Path, default=DEFAULT_V1887_MANIFEST)
    parser.add_argument("--v1888-manifest", type=Path, default=DEFAULT_V1888_MANIFEST)
    parser.add_argument("--v1890-manifest", type=Path, default=DEFAULT_V1890_MANIFEST)
    parser.add_argument("--capture-script", type=Path, default=DEFAULT_CAPTURE_SCRIPT)
    parser.add_argument("--commands-json", type=Path, default=DEFAULT_COMMANDS_JSON)
    parser.add_argument("--runner", type=Path, default=DEFAULT_RUNNER)
    parser.add_argument("--parser", type=Path, default=DEFAULT_PARSER)
    parser.add_argument("--future-capture-out-dir", type=Path, default=FUTURE_CAPTURE_OUT_DIR)
    parser.add_argument("--future-diff-out-dir", type=Path, default=FUTURE_DIFF_OUT_DIR)
    args = parser.parse_args()

    result = analyze(args)
    store = EvidenceStore(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    store.write_text("host/handoff-checks.json", json.dumps(result["checks"], indent=2, sort_keys=True) + "\n")
    store.write_text("host/command-outputs.json", json.dumps(result["command_outputs"], indent=2, sort_keys=True) + "\n")
    store.write_text("host/handoff-commands.txt", "\n".join(result["future_commands"]) + "\n")
    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "summary.md", render_report(result))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(args.report, render_report(result))
    print(json.dumps({key: result[key] for key in ("decision", "pass", "label", "out_dir", "report")}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
