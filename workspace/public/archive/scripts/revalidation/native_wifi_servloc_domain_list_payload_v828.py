#!/usr/bin/env python3
"""V828 host-only service-locator GET_DOMAIN_LIST payload derivation.

V827 selected service-locator domain-list as the next proof.  This script
derives the exact bounded QMI request bytes for `wlan/fw` from OSRC source and
V826/V827 endpoint evidence, without opening QRTR or sending QMI.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v828-servloc-domain-list-payload")
LATEST_POINTER = Path("tmp/wifi/latest-v828-servloc-domain-list-payload.txt")
DEFAULT_V827_MANIFEST = Path("tmp/wifi/v827-service-notifier-continuation-classifier/manifest.json")
OSRC_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel')
SERVICE_LOCATOR_PRIVATE = OSRC_ROOT / "drivers/soc/qcom/service-locator-private.h"
SERVICE_LOCATOR = OSRC_ROOT / "drivers/soc/qcom/service-locator.c"
QMI_H = OSRC_ROOT / "include/linux/soc/qcom/qmi.h"
QMI_ENCDEC = OSRC_ROOT / "drivers/soc/qcom/qmi_encdec.c"

SERVICE_NAME = "wlan/fw"
TXN_ID = 1
QMI_REQUEST = 0
GET_DOMAIN_LIST_MSG_ID = 0x0021
SERVICE_LOCATOR_SERVICE = 64
SERVICE_LOCATOR_ENCODED_INSTANCE = 257

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
    parser.add_argument("--v827-manifest", type=Path, default=DEFAULT_V827_MANIFEST)
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


def read_text(path: Path) -> dict[str, Any]:
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


def source_model() -> dict[str, Any]:
    sources = {
        "service_locator_private": read_text(SERVICE_LOCATOR_PRIVATE),
        "service_locator": read_text(SERVICE_LOCATOR),
        "qmi_h": read_text(QMI_H),
        "qmi_encdec": read_text(QMI_ENCDEC),
    }
    anchors = {
        "service_locator_private": [
            "struct qmi_servreg_loc_get_domain_list_req_msg_v01",
            "QMI_SERVREG_LOC_GET_DOMAIN_LIST_REQ_MSG_V01_MAX_MSG_LEN 74",
            "tlv_type       = 0x01",
            "tlv_type       = 0x10",
            "struct qmi_servreg_loc_get_domain_list_resp_msg_v01",
        ],
        "service_locator": [
            "strlcpy(req->service_name, pd->service_name",
            "req->domain_offset_valid = true",
            "req->domain_offset = 0",
            "QMI_SERVREG_LOC_GET_DOMAIN_LIST_REQ_V01",
            "service_locator_send_msg",
        ],
        "qmi_h": [
            "struct qmi_header",
            "#define QMI_REQUEST",
            "#define QMI_RESPONSE",
        ],
        "qmi_encdec": [
            "qmi_encode_message",
            "QMI_ENCDEC_ENCODE_TLV",
            "qmi_encode_string_elem",
        ],
    }
    model: dict[str, Any] = {}
    for name, source in sources.items():
        text = source["text"]
        model[name] = {
            "source": {key: value for key, value in source.items() if key != "text"},
            "anchors": {anchor: anchor in text for anchor in anchors[name]},
            "anchor_lines": {anchor: line_number(text, anchor) for anchor in anchors[name]},
        }
    return model


def int_value(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(str(value), 0)
    except ValueError:
        return default


def v827_input(args: argparse.Namespace) -> dict[str, Any]:
    loaded = load_json(args.v827_manifest)
    data = loaded["data"]
    observed = (((data.get("flow") or {}).get("observed")) or {})
    return {
        "file": loaded["file"],
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
        "next_step": data.get("next_step", ""),
        "service_locator_endpoint": observed.get("service_locator_64_257") or {},
        "service_notifier_endpoint": observed.get("service_notifier_66_46081") or {},
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


def qmi_header(message_type: int, txn_id: int, msg_id: int, msg_len: int) -> bytes:
    return bytes([message_type]) + txn_id.to_bytes(2, "little") + msg_id.to_bytes(2, "little") + msg_len.to_bytes(2, "little")


def tlv(tlv_type: int, payload: bytes) -> bytes:
    return bytes([tlv_type]) + len(payload).to_bytes(2, "little") + payload


def derive_request() -> dict[str, Any]:
    service_name = SERVICE_NAME.encode("ascii")
    payload = tlv(0x01, service_name) + tlv(0x10, (0).to_bytes(4, "little"))
    request = qmi_header(QMI_REQUEST, TXN_ID, GET_DOMAIN_LIST_MSG_ID, len(payload)) + payload
    return {
        "service_name": SERVICE_NAME,
        "domain_offset": 0,
        "destination_service": SERVICE_LOCATOR_SERVICE,
        "destination_encoded_instance": SERVICE_LOCATOR_ENCODED_INSTANCE,
        "message_type": QMI_REQUEST,
        "transaction_id": TXN_ID,
        "message_id": GET_DOMAIN_LIST_MSG_ID,
        "payload_length": len(payload),
        "total_length": len(request),
        "tlvs": [
            {"type": "0x01", "name": "service_name", "length": len(service_name), "value_ascii": SERVICE_NAME, "value_hex": service_name.hex()},
            {"type": "0x10", "name": "domain_offset", "length": 4, "value": 0, "value_hex": (0).to_bytes(4, "little").hex()},
        ],
        "request_hex": request.hex(),
        "request_hex_spaced": " ".join(f"{byte:02x}" for byte in request),
        "request_bytes": list(request),
    }


def expected_response_model() -> dict[str, Any]:
    return {
        "message_type": 2,
        "message_id": GET_DOMAIN_LIST_MSG_ID,
        "required_tlv": {"type": "0x02", "name": "resp", "fields": ["result", "error"]},
        "optional_tlvs": [
            {"type": "0x10", "name": "total_domains", "field_type": "uint16"},
            {"type": "0x11", "name": "db_rev_count", "field_type": "uint16"},
            {"type": "0x12", "name": "domain_list", "fields": ["len", "name", "instance_id", "service_data_valid", "service_data"]},
        ],
        "success_condition": "resp.result == QMI_RESULT_SUCCESS and total_domains > 0 and domain_list contains wlan domain entries",
    }


def build_checks(v827: dict[str, Any], sources: dict[str, Any], request: dict[str, Any]) -> list[dict[str, Any]]:
    guardrails = v827["guardrails"]
    endpoint = v827["service_locator_endpoint"]
    source_anchor_pass = all(all(group["anchors"].values()) for group in sources.values())
    endpoint_ok = (
        int_value(endpoint.get("service")) == SERVICE_LOCATOR_SERVICE
        and int_value(endpoint.get("instance")) == SERVICE_LOCATOR_ENCODED_INSTANCE
        and int_value(endpoint.get("node")) > 0
        and int_value(endpoint.get("port")) > 0
    )
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
    request_ok = (
        request["payload_length"] == 17
        and request["total_length"] == 24
        and request["request_hex"].startswith("00010021001100")
        and "010700776c616e2f6677" in request["request_hex"]
        and "10040000000000" in request["request_hex"]
    )
    return [
        {
            "name": "host-only-boundary",
            "status": "pass",
            "detail": "V828 derives bytes only; no live socket or device command",
            "next_step": "keep V828 host-only",
        },
        {
            "name": "v827-input-ready",
            "status": "pass" if v827["pass"] and v827["decision"] == "v827-service-notifier-continuation-requires-domain-list-qmi-classified" else "blocked",
            "detail": {"decision": v827["decision"], "pass": v827["pass"], "file": v827["file"]},
            "next_step": "complete V827 before V828",
        },
        {
            "name": "service-locator-endpoint-ready",
            "status": "pass" if endpoint_ok else "blocked",
            "detail": endpoint,
            "next_step": "restore V826/V827 service-locator endpoint evidence",
        },
        {
            "name": "source-abi-ready",
            "status": "pass" if source_anchor_pass else "blocked",
            "detail": sources,
            "next_step": "restore OSRC service-locator/QMI encoding anchors",
        },
        {
            "name": "request-bytes-derived",
            "status": "pass" if request_ok else "blocked",
            "detail": request,
            "next_step": "fix QMI payload derivation before any live probe",
        },
        {
            "name": "guardrails-preserved",
            "status": "pass" if guardrails_ok else "blocked",
            "detail": guardrails,
            "next_step": "discard if previous gate exceeded guardrails",
        },
    ]


def decide(checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    if blockers:
        return (
            "v828-servloc-domain-list-payload-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "resolve host-only derivation blockers before live QMI work",
        )
    return (
        "v828-servloc-domain-list-payload-derived",
        True,
        "bounded service-locator GET_DOMAIN_LIST request for wlan/fw derived from OSRC QMI ABI",
        "V829 should implement a bounded no-HAL live probe that sends only this request to service-locator and parses the response",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v827 = v827_input(args)
    sources = source_model()
    request = derive_request()
    response = expected_response_model()
    checks = build_checks(v827, sources, request)
    decision, pass_ok, reason, next_step = decide(checks)
    if args.command == "plan":
        decision = "v828-servloc-domain-list-payload-plan-ready"
        reason = "plan-only; service-locator QMI payload derivation defined"
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v828",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v827": v827,
        "sources": sources,
        "request": request,
        "expected_response": response,
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "qrtr_socket_open_executed": False,
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
    tlv_rows = [
        [item["type"], item["name"], str(item["length"]), str(item.get("value", item.get("value_ascii"))), item["value_hex"]]
        for item in manifest["request"]["tlvs"]
    ]
    source_rows = [
        [
            name,
            str(group["source"].get("exists")),
            ", ".join(f"{anchor}:{line}" for anchor, line in group["anchor_lines"].items()),
        ]
        for name, group in manifest["sources"].items()
    ]
    return "\n".join([
        "# V828 Service-Locator Domain-List Payload",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- request_hex: `{manifest['request']['request_hex_spaced']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- qrtr_socket_open_executed: `{manifest['qrtr_socket_open_executed']}`",
        f"- qmi_payload_executed: `{manifest['qmi_payload_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Request TLVs",
        "",
        markdown_table(["tlv", "name", "length", "value", "hex"], tlv_rows),
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
    print(f"request_hex: {manifest['request']['request_hex_spaced']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"qrtr_socket_open_executed: {manifest['qrtr_socket_open_executed']}")
    print(f"qmi_payload_executed: {manifest['qmi_payload_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
