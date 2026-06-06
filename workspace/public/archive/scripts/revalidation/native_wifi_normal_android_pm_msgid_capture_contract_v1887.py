#!/usr/bin/env python3
"""V1887 host-only contract for the normal-Android PM msg-id trigger capture."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1887-normal-android-pm-msgid-capture-contract"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1887_NORMAL_ANDROID_PM_MSGID_CAPTURE_CONTRACT_2026-06-03.md"
)
DEFAULT_PM_SERVICE = REPO_ROOT / "tmp" / "wifi" / "v1073-host-only" / "vendor-extract" / "files" / "pm-service"
DEFAULT_V1886_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1886-internal-servloc-msg22-stateup-classifier" / "manifest.json"
)
DEFAULT_V1885_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1885-internal-pm-qmi-servreg-trigger-source-diff" / "manifest.json"
)
DEFAULT_V1703_REPORT = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1703_CNSS_WLFW_DOWNSTREAM_STATIC_2026-06-02.md"
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


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def command_text(command: list[str]) -> str:
    proc = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc.stdout


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def extract_pm_strings(pm_service: Path) -> dict[str, Any]:
    strings_text = command_text(["strings", "-a", "-tx", str(pm_service)])
    interesting = {}
    for line in strings_text.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue
        address, value = parts
        if value in {
            "PerMgrSrv",
            "QMI service system restart request from %s",
            "QMI service system shutdown request from %s",
            "QMI service peripheral restart request from %s",
            "QMI service peripheral restart response error %d",
            "%s going on-line because restart request",
            "%s going off-line because restart request",
            "%s voting for %s",
            "%s state: %s, add client %s",
            "modem",
        }:
            interesting[value] = address
    return {
        "pm_service": rel(pm_service),
        "tag": "PerMgrSrv",
        "addresses": interesting,
        "msg20_string": interesting.get("QMI service system restart request from %s", ""),
        "msg21_string": interesting.get("QMI service system shutdown request from %s", ""),
        "msg22_string": interesting.get("QMI service peripheral restart request from %s", ""),
        "vote_string": interesting.get("%s voting for %s", ""),
        "register_string": interesting.get("%s state: %s, add client %s", ""),
    }


def source_trace_points(v1885: dict[str, Any]) -> dict[str, Any]:
    source = v1885.get("source") or {}
    return {
        "pm_service_msgid_handlers": [
            {
                "name": "pm_msg20_system_restart_request",
                "offset": "0x6ebc",
                "expected_msg_id": "0x20",
                "meaning": "system restart request path; must not be used for WLAN bring-up",
            },
            {
                "name": "pm_msg21_system_shutdown_request",
                "offset": "0x7014",
                "expected_msg_id": "0x21",
                "meaning": "system shutdown request path; must not be used for WLAN bring-up",
            },
            {
                "name": "pm_msg22_peripheral_restart_request",
                "offset": "0x716c",
                "expected_msg_id": "0x22",
                "meaning": "peripheral restart request handler; candidate WLAN-PD state-up edge",
            },
            {
                "name": "pm_msg22_response_call",
                "offset": "0x725c",
                "expected_msg_id": "0x22",
                "meaning": "QMI response call for msg22 request handler",
            },
            {
                "name": "pm_msg22_post_ack_indication_call",
                "offset": "0x8a4c",
                "expected_msg_id": "0x22",
                "meaning": "post-ack indication call using the pending restart client slot",
            },
        ],
        "source_checks": {
            "pm_msgid_0x22_dispatch": bool(source.get("pm_msgid_0x22_dispatch")),
            "pm_msg22_request_string": bool(source.get("pm_msg22_request_string")),
            "pm_msg22_response_call": bool(source.get("pm_msg22_response_call")),
            "pm_post_ack_msg22_indication": bool(source.get("pm_post_ack_msg22_indication")),
            "pm_post_ack_pending_restart_client_slot": bool(source.get("pm_post_ack_pending_restart_client_slot")),
            "libperipheral_qmi_imports": bool(source.get("libperipheral_qmi_imports")),
        },
    }


def cnss_trace_points(v1703_report: Path) -> dict[str, Any]:
    text = read_text(v1703_report)
    qmi_rows: dict[str, dict[str, str]] = {}
    row_re = re.compile(
        r"^\|\s*`(?P<function>[^`]+)`\s*\|\s*`(?P<site>0x[0-9a-f]+)`\s*\|\s*`(?P<message>0x[0-9a-f]+)`\s*"
        r"\|\s*`(?P<req>0x[0-9a-f]+)`\s*\|\s*`(?P<resp>0x[0-9a-f]+)`\s*\|\s*`(?P<timeout>[^`]+)`",
        re.IGNORECASE,
    )
    for line in text.splitlines():
        match = row_re.search(line)
        if not match:
            continue
        qmi_rows[match.group("function")] = match.groupdict()
    return {
        "source_report": rel(v1703_report),
        "qmi_sync_calls": qmi_rows,
        "required_native_stop_boundary": "before wlfw_send_ind_register_req@0xf32c in failed native; at or after it only when WLFW service 69 is present",
    }


def capture_contract() -> dict[str, Any]:
    return {
        "capture_window": {
            "boot_class": "normal Android boot only",
            "start": "before vendor.per_mgr PM vote for modem",
            "stop": "after first wlanmdsp.mbn tftp request or wlan0 event",
            "reject_if": [
                "wlan0 appears near 257s degraded path",
                "esoc0_boot_failed appears before wlan0",
                "PCIe/MHI events appear before wlan0",
            ],
        },
        "required_artifacts": {
            "logcat_threadtime": [
                "PerMgrSrv",
                "PerMgrLib",
                "cnss-daemon",
                "tftp_server",
                "vendor.rmt_storage",
                "service-notifier",
                "servloc",
                "sysmon-qmi",
            ],
            "dmesg_markers": [
                "sysmon-qmi SSCTL",
                "service-notifier 180",
                "service-notifier 74",
                "msm/modem/wlan_pd state indication",
                "icnss_qmi QMI Server Connected",
                "wlanmdsp.mbn request",
                "wlan0 event",
                "PCIe/MHI contamination check",
            ],
            "process_observation_targets": [
                "pm-service",
                "per_mgr",
                "cnss-daemon",
                "tftp_server",
                "rmt_storage",
            ],
            "pm_service_msgid_signals": [
                "msg 0x20 request/response/indication count",
                "msg 0x21 request/response/indication count",
                "msg 0x22 request/response/indication count",
                "pending restart client slot nonzero before post-ack msg22 indication",
            ],
        },
        "fixed_labels": [
            "android-msg22-stateup-observed-native-absent",
            "android-stateup-without-msg22-log-observability-gap",
            "android-normal-capture-contaminated",
            "native-post-open-msg22-still-absent",
            "capture-incomplete",
        ],
        "hard_stops": [
            "no GDSC PMIC GPIO regulator writes",
            "no forced RC1 or case writes",
            "no subsys_esoc0 open",
            "no fake ONLINE",
            "no eSoC notify or BOOT_DONE",
            "no PCI rescan",
            "no platform bind or unbind",
            "no Wi-Fi HAL scan connect credential DHCP route or external ping",
        ],
    }


def classify(v1886: dict[str, Any], v1885: dict[str, Any], traces: dict[str, Any]) -> tuple[str, bool, str, str]:
    checks = traces["pm_service"]["source_checks"]
    source_ready = (
        checks["pm_msgid_0x22_dispatch"]
        and checks["pm_msg22_request_string"]
        and checks["pm_msg22_response_call"]
        and checks["pm_post_ack_msg22_indication"]
        and checks["pm_post_ack_pending_restart_client_slot"]
        and not checks["libperipheral_qmi_imports"]
    )
    prior_ready = (
        boolish(v1886.get("pass"))
        and v1886.get("label") == "servloc-domain-present-msg22-stateup-missing"
        and boolish(v1885.get("pass"))
        and v1885.get("label") == "pm-msg22-servreg-trigger-trace-gap"
    )
    cnss_qmi_ready = {"wlfw_send_ind_register_req", "wlfw_send_cap_req"}.issubset(
        set((traces["cnss_daemon"].get("qmi_sync_calls") or {}).keys())
    )
    if not prior_ready:
        return (
            "v1887-prior-trigger-gap-not-ready",
            False,
            "V1885/V1886 did not preserve the internal msg22/servloc state-up gap",
            "prior-trigger-gap-not-ready",
        )
    if not source_ready:
        return (
            "v1887-pm-msgid-source-targets-incomplete",
            False,
            "pm-service msg22 source trace targets are incomplete",
            "pm-msgid-source-targets-incomplete",
        )
    if not cnss_qmi_ready:
        return (
            "v1887-cnss-wlfw-qmi-targets-incomplete",
            False,
            "CNSS WLFW QMI target map is incomplete",
            "cnss-wlfw-qmi-targets-incomplete",
        )
    return (
        "v1887-normal-android-pm-msgid-capture-contract-host-pass",
        True,
        "normal-Android read-only capture contract is ready for the PM msg-id/servreg/SSCTL diff; no live capture ran because Android ADB is absent in the current state",
        "normal-android-pm-msgid-capture-contract-ready",
    )


def render_report(result: dict[str, Any]) -> str:
    pm_strings = result["pm_service_strings"]
    pm_trace = result["trace_targets"]["pm_service"]
    cnss_trace = result["trace_targets"]["cnss_daemon"]
    contract = result["capture_contract"]
    return "\n".join(
        [
            "# Native Init V1887 Normal Android PM Msg-id Capture Contract",
            "",
            "## Summary",
            "",
            "- Cycle: `V1887`",
            "- Type: host-only capture contract for the normal-Android PM msg-id/servreg/SSCTL trigger diff",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Source Anchors",
            "",
            f"- pm-service binary/tag: `{pm_strings['pm_service']}` / `{pm_strings['tag']}`",
            f"- PM register/vote string offsets: `{pm_strings['register_string']}` / `{pm_strings['vote_string']}`",
            f"- msg20/msg21/msg22 string offsets: `{pm_strings['msg20_string']}` / `{pm_strings['msg21_string']}` / `{pm_strings['msg22_string']}`",
            f"- pm-service source checks: `{json.dumps(pm_trace['source_checks'], sort_keys=True)}`",
            f"- pm-service trace points: `{json.dumps(pm_trace['pm_service_msgid_handlers'], sort_keys=True)}`",
            f"- CNSS QMI sync calls: `{json.dumps(cnss_trace['qmi_sync_calls'], sort_keys=True)}`",
            "",
            "## Capture Contract",
            "",
            f"- boot class/start/stop: `{contract['capture_window']['boot_class']}` / `{contract['capture_window']['start']}` / `{contract['capture_window']['stop']}`",
            f"- reject-if: `{json.dumps(contract['capture_window']['reject_if'])}`",
            f"- logcat tags: `{json.dumps(contract['required_artifacts']['logcat_threadtime'])}`",
            f"- dmesg markers: `{json.dumps(contract['required_artifacts']['dmesg_markers'])}`",
            f"- process targets: `{json.dumps(contract['required_artifacts']['process_observation_targets'])}`",
            f"- PM msg-id signals: `{json.dumps(contract['required_artifacts']['pm_service_msgid_signals'])}`",
            f"- fixed labels: `{json.dumps(contract['fixed_labels'])}`",
            "",
            "## Selected Diff",
            "",
            f"- Label: `{result['label']}`.",
            "- The next live unit is not another SDX50M/eSoC/PCIe/GDSC probe; it is the normal-Android PM msg-id/servreg/SSCTL capture across PM vote to first `wlanmdsp.mbn`.",
            "- The required discriminator is whether Android emits pm-service msg `0x22` and a service-notifier state-up path before `wlanmdsp.mbn`, and whether native post-open still lacks that edge.",
            "- If Android reaches WLAN-PD state-up but msg-id evidence is still absent, the correct label is an observability gap, not proof that msg22 is false.",
            "",
            "## Safety Scope",
            "",
            "V1887 is host-only. It reads retained manifests/reports and local binaries, then writes local contract artifacts only. It performs no device command, flash, reboot, property staging, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or device partition write.",
            "",
            "## Next",
            "",
            "- Run the contract only when normal Android ADB/root capture is available; current state has no ADB device attached.",
            "- Use the normal ~14s boot path only; reject degraded 257s captures and any pre-wlan0 PCIe/MHI path.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--pm-service", type=Path, default=DEFAULT_PM_SERVICE)
    parser.add_argument("--v1886-manifest", type=Path, default=DEFAULT_V1886_MANIFEST)
    parser.add_argument("--v1885-manifest", type=Path, default=DEFAULT_V1885_MANIFEST)
    parser.add_argument("--v1703-report", type=Path, default=DEFAULT_V1703_REPORT)
    args = parser.parse_args()

    store = EvidenceStore(args.out_dir)
    v1886 = read_json(args.v1886_manifest)
    v1885 = read_json(args.v1885_manifest)
    traces = {
        "pm_service": source_trace_points(v1885),
        "cnss_daemon": cnss_trace_points(args.v1703_report),
    }
    decision, passed, reason, label = classify(v1886, v1885, traces)
    result = {
        "cycle": "V1887",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
        "inputs": {
            "v1886_manifest": rel(args.v1886_manifest),
            "v1885_manifest": rel(args.v1885_manifest),
            "v1703_report": rel(args.v1703_report),
        },
        "pm_service_strings": extract_pm_strings(args.pm_service),
        "trace_targets": traces,
        "capture_contract": capture_contract(),
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
            "pci_rescan": False,
            "platform_bind_unbind": False,
        },
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    store.write_text(
        "host/normal-android-capture-contract.json",
        json.dumps(result["capture_contract"], indent=2, sort_keys=True) + "\n",
    )
    store.write_text(
        "host/pm-service-msgid-trace-targets.json",
        json.dumps(result["trace_targets"]["pm_service"], indent=2, sort_keys=True) + "\n",
    )
    store.write_text(
        "host/cnss-wlfw-qmi-trace-targets.json",
        json.dumps(result["trace_targets"]["cnss_daemon"], indent=2, sort_keys=True) + "\n",
    )
    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "summary.md", render_report(result))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(args.report, render_report(result))
    print(json.dumps({key: result[key] for key in ("decision", "pass", "label", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
