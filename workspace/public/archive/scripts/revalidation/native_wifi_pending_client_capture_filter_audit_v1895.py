#!/usr/bin/env python3
"""V1895 host-only audit for the pending-client capture filter repair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1895-pending-client-capture-filter-audit"
DEFAULT_REPORT_PATH = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1895_PENDING_CLIENT_CAPTURE_FILTER_AUDIT_2026-06-03.md"
)
DEFAULT_V1890_COMMANDS = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1890-android-pm-msgid-log-capture-runner"
    / "host"
    / "android-pm-msgid-log-capture-commands.json"
)
DEFAULT_V1890_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1890-android-pm-msgid-log-capture-runner" / "manifest.json"
)
DEFAULT_V1894_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1894-android-pending-client-msg22-parser" / "manifest.json"
)
DEFAULT_V1894_COVERAGE = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1894-android-pending-client-msg22-parser"
    / "host"
    / "capture-filter-coverage.json"
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


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    v1890 = read_json(args.v1890_manifest)
    v1894 = read_json(args.v1894_manifest)
    coverage = read_json(args.v1894_coverage)
    commands = read_json(args.v1890_commands)
    text = command_text(commands)
    checks = {
        "v1890_runner_ready": (
            boolish(v1890.get("pass")) and v1890.get("label") == "android-pm-msgid-log-capture-runner-ready"
        ),
        "v1894_parser_ready": (
            boolish(v1894.get("pass"))
            and v1894.get("label") == "android-stateup-pending-client-observability-gap"
        ),
        "v1890_filter_has_qmi_client": "QMI client" in text,
        "v1890_request_lines_has_qmi_client": "QMI client|peripheral restart" in text
        or "QMI service|QMI client|peripheral restart" in text,
        "v1894_requires_qmi_client": boolish(coverage.get("covers_qmi_client")),
        "core_filter_terms_present": all(
            term in text
            for term in (
                "PerMgrSrv",
                "QMI client",
                "QMI service",
                "peripheral restart",
                "wlanmdsp",
                "wlan_pd",
                "wlfw_service_request",
            )
        ),
    }
    if all(checks.values()):
        decision = "v1895-pending-client-capture-filter-audit-host-pass"
        label = "pending-client-capture-filter-qmi-client-covered"
        reason = "V1890 and V1894 now both cover QMI client pending-slot logs for the V1893 msg22 gate"
        passed = True
    else:
        decision = "v1895-pending-client-capture-filter-audit-incomplete"
        label = "pending-client-capture-filter-incomplete"
        reason = "QMI client pending-slot coverage is still missing from the capture runner or parser gate"
        passed = False
    return {
        "cycle": "V1895",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
        "inputs": {
            "v1890_manifest": rel(args.v1890_manifest),
            "v1890_commands": rel(args.v1890_commands),
            "v1894_manifest": rel(args.v1894_manifest),
            "v1894_coverage": rel(args.v1894_coverage),
        },
        "checks": checks,
        "coverage": coverage,
        "safety": {
            "host_only": True,
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
    coverage = result["coverage"]
    safety = result["safety"]
    return "\n".join(
        [
            "# Native Init V1895 Pending Client Capture Filter Audit",
            "",
            "## Summary",
            "",
            "- Cycle: `V1895`",
            "- Type: host-only audit for V1890/V1894 pending-client capture-filter coverage",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Checks",
            "",
            f"- V1890/V1894 ready: `{checks['v1890_runner_ready']}` / `{checks['v1894_parser_ready']}`",
            f"- V1890 filter/request-lines QMI client: `{checks['v1890_filter_has_qmi_client']}` / `{checks['v1890_request_lines_has_qmi_client']}`",
            f"- V1894 requires QMI client: `{checks['v1894_requires_qmi_client']}`",
            f"- core filter terms present: `{checks['core_filter_terms_present']}`",
            "",
            "## Coverage",
            "",
            f"- coverage file: `{result['inputs']['v1894_coverage']}`",
            f"- PerMgrSrv/QMI-client/QMI-service/peripheral-restart: `{coverage.get('covers_per_mgr_srv')}` / `{coverage.get('covers_qmi_client')}` / `{coverage.get('covers_qmi_service')}` / `{coverage.get('covers_peripheral_restart')}`",
            f"- wlanmdsp/wlan_pd/WLFW/service-notifier: `{coverage.get('covers_wlanmdsp')}` / `{coverage.get('covers_wlan_pd')}` / `{coverage.get('covers_wlfw_service_request')}` / `{coverage.get('covers_service_notifier')}`",
            "",
            "## Selected Diff",
            "",
            f"- Label: `{result['label']}`.",
            "- V1893 narrowed the missing edge to pm-service pending QMI client creation and msg22 indication.",
            "- V1890 previously covered `QMI service` and `peripheral restart`, but not the standalone `QMI client` connected/disconnected log string.",
            "- The future normal-Android capture now includes `QMI client`, so V1894 can promote if pending-client/msg22 appears before `wlanmdsp.mbn`.",
            "",
            "## Safety Scope",
            "",
            f"- host-only/device-contact: `{safety['host_only']}` / `{safety['device_contact']}`",
            f"- Wi-Fi HAL/scan-connect/credential/DHCP/routes/ping: `{safety['wifi_hal']}` / `{safety['scan_connect']}` / `{safety['credential_use']}` / `{safety['dhcp_routes']}` / `{safety['external_ping']}`",
            f"- PMIC-GPIO-GDSC/forced-RC1/subsys-esoc0/eSoC notify/PCI rescan/platform bind: `{safety['pmic_gpio_gdsc_write']}` / `{safety['forced_rc1_case']}` / `{safety['subsys_esoc0_open']}` / `{safety['esoc_notify_boot_done']}` / `{safety['pci_rescan']}` / `{safety['platform_bind_unbind']}`",
            "",
            "## Next",
            "",
            "- Run the normal Android capture only when ADB/root is available; reject degraded 257s captures and any pre-wlan0 PCIe/MHI path.",
            "- Parse that capture with V1894 and V1888 before any native trigger replay or Wi-Fi connect attempt.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1890-manifest", type=Path, default=DEFAULT_V1890_MANIFEST)
    parser.add_argument("--v1890-commands", type=Path, default=DEFAULT_V1890_COMMANDS)
    parser.add_argument("--v1894-manifest", type=Path, default=DEFAULT_V1894_MANIFEST)
    parser.add_argument("--v1894-coverage", type=Path, default=DEFAULT_V1894_COVERAGE)
    args = parser.parse_args()

    result = analyze(args)
    store = EvidenceStore(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    store.write_text("host/filter-audit-checks.json", json.dumps(result["checks"], indent=2, sort_keys=True) + "\n")
    store.write_text("host/filter-coverage.json", json.dumps(result["coverage"], indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "summary.md", render_report(result))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(args.report, render_report(result))
    print(json.dumps({key: result[key] for key in ("decision", "pass", "label", "out_dir", "report")}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
