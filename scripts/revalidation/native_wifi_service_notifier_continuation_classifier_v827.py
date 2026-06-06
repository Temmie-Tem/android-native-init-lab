#!/usr/bin/env python3
"""V827 host-only service-notifier continuation classifier.

V826 showed that encoded service-locator and service-notifier instance 180 are
visible through AF_QIPCRTR.  This classifier maps that evidence onto the
Samsung OSRC ICNSS/service-locator/service-notifier source path to decide what
must be proven next before WLFW or wlan0 can appear.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v827-service-notifier-continuation-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v827-service-notifier-continuation-classifier.txt")
DEFAULT_V826_MANIFEST = Path("tmp/wifi/v826-qrtr-event-detail-classifier/manifest.json")
OSRC_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel')

SOURCE_FILES = {
    "icnss": OSRC_ROOT / "drivers/soc/qcom/icnss.c",
    "icnss_qmi": OSRC_ROOT / "drivers/soc/qcom/icnss_qmi.c",
    "service_locator": OSRC_ROOT / "drivers/soc/qcom/service-locator.c",
    "service_notifier": OSRC_ROOT / "drivers/soc/qcom/service-notifier.c",
    "service_notifier_private": OSRC_ROOT / "drivers/soc/qcom/service-notifier-private.h",
    "sysmon_qmi": OSRC_ROOT / "drivers/soc/qcom/sysmon-qmi.c",
    "wlfw": OSRC_ROOT / "drivers/soc/qcom/wlan_firmware_service_v01.h",
}

REQUIRED_ANCHORS = {
    "icnss": [
        "ICNSS_SERVICE_LOCATION_CLIENT_NAME",
        "ICNSS_WLAN_SERVICE_NAME",
        "get_service_location(ICNSS_SERVICE_LOCATION_CLIENT_NAME",
        "service_notif_register_notifier(pd->domain_list[i].name",
    ],
    "service_locator": [
        "qmi_add_lookup(&service_locator.clnt_handle",
        "SERVREG_LOC_SERVICE_ID_V01",
        "service_locator_send_msg",
        "QMI_SERVREG_LOC_GET_DOMAIN_LIST_REQ_V01",
    ],
    "service_notifier": [
        "qmi_add_lookup(&qmi_data->clnt_handle",
        "SERVREG_NOTIF_SERVICE_ID",
        "send_notif_listener_msg_req",
        "SERVREG_NOTIF_REGISTER_LISTENER_REQ",
        "root_service_service_ind_cb",
    ],
    "sysmon_qmi": [
        "SSCTL_SERVICE_ID",
        "SSCTL_VER_2",
        "qmi_add_lookup(&data->clnt_handle, SSCTL_SERVICE_ID",
        "ssctl_new_server",
    ],
    "icnss_qmi": [
        "WLFW_SERVICE_ID_V01",
        "WLFW_SERVICE_VERS_V01",
        "qmi_add_lookup(&priv->qmi, WLFW_SERVICE_ID_V01",
    ],
    "wlfw": [
        "#define WLFW_SERVICE_ID_V01 0x45",
        "#define WLFW_SERVICE_VERS_V01 0x01",
    ],
}

FORBIDDEN_ACTIONS = (
    "host-only; no bridge command",
    "no device command, reboot, bootloader handoff, boot image write, or partition write",
    "no QRTR socket open or QRTR/QMI packet transmission",
    "no service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP, route, or external ping",
    "custom OSRC kernel flashing remains paused",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v826-manifest", type=Path, default=DEFAULT_V826_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else repo_path(path)
    if not resolved.exists():
        return {"file": {"path": str(resolved), "exists": False}, "data": {}}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"file": {"path": str(resolved), "exists": True}, "data": {}, "error": str(exc)}
    return {
        "file": {"path": str(resolved), "exists": True, "size": resolved.stat().st_size},
        "data": data if isinstance(data, dict) else {},
    }


def read_source(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"path": str(resolved), "exists": False, "text": ""}
    return {
        "path": str(resolved),
        "exists": True,
        "size": resolved.stat().st_size,
        "text": resolved.read_text(encoding="utf-8", errors="replace"),
    }


def line_number(text: str, pattern: str) -> int | None:
    for idx, line in enumerate(text.splitlines(), start=1):
        if pattern in line:
            return idx
    return None


def evidence_lines(text: str, patterns: list[str], limit: int = 24) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        if any(pattern in line for pattern in patterns):
            lines.append(line.strip())
            if len(lines) >= limit:
                break
    return lines


def source_model() -> dict[str, Any]:
    model: dict[str, Any] = {}
    for name, path in SOURCE_FILES.items():
        source = read_source(path)
        text = source["text"]
        anchors = REQUIRED_ANCHORS.get(name, [])
        model[name] = {
            "source": {key: value for key, value in source.items() if key != "text"},
            "anchors": {anchor: anchor in text for anchor in anchors},
            "anchor_lines": {anchor: line_number(text, anchor) for anchor in anchors},
            "evidence_lines": evidence_lines(text, anchors),
        }
    return model


def int_value(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(str(value), 0)
    except ValueError:
        return default


def v826_input(args: argparse.Namespace) -> dict[str, Any]:
    loaded = load_json(args.v826_manifest)
    data = loaded["data"]
    service_events = data.get("service_events") or []
    empty_events = data.get("empty_events") or []
    return {
        "file": loaded["file"],
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
        "next_step": data.get("next_step", ""),
        "service_events": service_events if isinstance(service_events, list) else [],
        "empty_events": empty_events if isinstance(empty_events, list) else [],
        "guardrails": {
            "device_commands_executed": data.get("device_commands_executed"),
            "qmi_payload_executed": data.get("qmi_payload_executed"),
            "wifi_hal_start_executed": data.get("wifi_hal_start_executed"),
            "scan_connect_executed": data.get("scan_connect_executed"),
            "external_ping_executed": data.get("external_ping_executed"),
            "custom_kernel_flash_executed": data.get("custom_kernel_flash_executed"),
            "boot_image_write_executed": data.get("boot_image_write_executed"),
            "partition_write_executed": data.get("partition_write_executed"),
        },
    }


def has_event(events: list[dict[str, Any]], service: int, instance: int) -> bool:
    return any(int_value(event.get("service")) == service and int_value(event.get("instance")) == instance for event in events)


def event_for(events: list[dict[str, Any]], service: int, instance: int) -> dict[str, Any]:
    for event in events:
        if int_value(event.get("service")) == service and int_value(event.get("instance")) == instance:
            return event
    return {}


def build_flow(v826: dict[str, Any], sources: dict[str, Any]) -> dict[str, Any]:
    service_events = v826["service_events"]
    empty_events = v826["empty_events"]
    return {
        "observed": {
            "service_locator_64_257": event_for(service_events, 64, 257),
            "service_notifier_66_46081": event_for(service_events, 66, 46081),
            "ssctl_43_4098_visible": has_event(service_events, 43, 4098),
            "service_notifier_66_18945_visible": has_event(service_events, 66, 18945),
            "wlfw_69_1_visible": has_event(service_events, 69, 1),
            "empty_events": empty_events,
        },
        "source_path": [
            "icnss_pd_restart_enable calls get_service_location(ICNSS-WLAN, wlan/fw)",
            "service-locator uses QMI GET_DOMAIN_LIST against service 64/257",
            "icnss_get_service_location_notify registers service_notif for returned domain names/instances",
            "service-notifier service 66/46081 visibility only exposes the root notifier endpoint",
            "service-notifier continuation requires QMI REGISTER_LISTENER and later state indication",
            "WLFW requires service 69/1 publication through icnss_register_fw_service",
        ],
        "source_anchor_pass": all(
            all(result for result in group["anchors"].values())
            for group in sources.values()
            if group["anchors"]
        ),
    }


def build_checks(args: argparse.Namespace,
                 v826: dict[str, Any],
                 sources: dict[str, Any],
                 flow: dict[str, Any]) -> list[dict[str, Any]]:
    guardrails = v826["guardrails"]
    guardrails_ok = (
        guardrails.get("device_commands_executed") is False
        and guardrails.get("qmi_payload_executed") is False
        and guardrails.get("wifi_hal_start_executed") is False
        and guardrails.get("scan_connect_executed") is False
        and guardrails.get("external_ping_executed") is False
        and guardrails.get("custom_kernel_flash_executed") is False
        and guardrails.get("boot_image_write_executed") is False
        and guardrails.get("partition_write_executed") is False
    )
    observed = flow["observed"]
    return [
        {
            "name": "host-only-boundary",
            "status": "pass",
            "detail": "V827 reads only V826 evidence and OSRC source",
            "next_step": "keep V827 host-only",
        },
        {
            "name": "v826-input-ready",
            "status": "pass" if v826["pass"] and v826["decision"] == "v826-qrtr-event-details-classified" else "blocked",
            "detail": {"decision": v826["decision"], "pass": v826["pass"], "file": v826["file"]},
            "next_step": "complete V826 before V827",
        },
        {
            "name": "visible-control-endpoints-ready",
            "status": "pass" if observed["service_locator_64_257"] and observed["service_notifier_66_46081"] else "blocked",
            "detail": observed,
            "next_step": "restore V826 visible service event evidence",
        },
        {
            "name": "absence-still-below-wlfw",
            "status": "pass" if (
                not observed["ssctl_43_4098_visible"]
                and not observed["service_notifier_66_18945_visible"]
                and not observed["wlfw_69_1_visible"]
            ) else "blocked",
            "detail": observed,
            "next_step": "do not classify continuation if SSCTL/WLFW is already visible",
        },
        {
            "name": "source-anchors-ready",
            "status": "pass" if flow["source_anchor_pass"] else "blocked",
            "detail": sources,
            "next_step": "restore OSRC source anchors before selecting next gate",
        },
        {
            "name": "guardrails-preserved",
            "status": "pass" if guardrails_ok else "blocked",
            "detail": guardrails,
            "next_step": "discard interpretation if previous evidence exceeded guardrails",
        },
        {
            "name": "continuation-requires-qmi-domain-list",
            "status": "finding",
            "detail": flow["source_path"],
            "next_step": "next gate should prove service-locator domain-list/registration path before HAL/connect",
        },
    ]


def decide(checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    if blockers:
        return (
            "v827-service-notifier-continuation-classifier-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "resolve host-only evidence/source blockers before live work",
        )
    return (
        "v827-service-notifier-continuation-requires-domain-list-qmi-classified",
        True,
        "visible service-notifier 180 is a control endpoint; ICNSS continuation still requires service-locator domain-list and notifier registration/state indication",
        "V828 should derive a bounded service-locator GET_DOMAIN_LIST probe for wlan/fw before any HAL/connect or Wi-Fi credential use",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v826 = v826_input(args)
    sources = source_model()
    flow = build_flow(v826, sources)
    checks = build_checks(args, v826, sources, flow)
    decision, pass_ok, reason, next_step = decide(checks)
    if args.command == "plan":
        decision = "v827-service-notifier-continuation-classifier-plan-ready"
        reason = "plan-only; service-notifier continuation source/evidence classifier defined"
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v827",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v826": v826,
        "sources": sources,
        "flow": flow,
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "qmi_payload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    observed = manifest["flow"]["observed"]
    source_rows = [
        [
            name,
            str(group["source"].get("exists")),
            ", ".join(f"{anchor}:{line}" for anchor, line in group["anchor_lines"].items()),
        ]
        for name, group in manifest["sources"].items()
    ]
    return "\n".join([
        "# V827 Service-Notifier Continuation Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- qmi_payload_executed: `{manifest['qmi_payload_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Observed Control Endpoints",
        "",
        f"- service-locator 64/257: `{json.dumps(observed['service_locator_64_257'], ensure_ascii=False, sort_keys=True)}`",
        f"- service-notifier 66/46081: `{json.dumps(observed['service_notifier_66_46081'], ensure_ascii=False, sort_keys=True)}`",
        f"- ssctl 43/4098 visible: `{observed['ssctl_43_4098_visible']}`",
        f"- service-notifier 66/18945 visible: `{observed['service_notifier_66_18945_visible']}`",
        f"- wlfw 69/1 visible: `{observed['wlfw_69_1_visible']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Source Anchors",
        "",
        markdown_table(["source", "exists", "anchor_lines"], source_rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"qmi_payload_executed: {manifest['qmi_payload_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
