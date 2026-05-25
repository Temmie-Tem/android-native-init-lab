#!/usr/bin/env python3
"""V824 host-only QRTR encoded-instance classifier.

V823 queried the correct service IDs, but OSRC `qmi_interface.c` shows kernel
QMI clients encode the QRTR nameservice instance as `version | instance << 8`.
This host-only classifier compares V823's raw matrix with the encoded values
that kernel `qmi_add_lookup()` would transmit.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v824-qrtr-encoded-instance-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v824-qrtr-encoded-instance-classifier.txt")
DEFAULT_V823_MANIFEST = Path("tmp/wifi/v823-ssctl-nameservice-matrix/manifest.json")
OSRC_ROOT = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel")
QMI_INTERFACE = OSRC_ROOT / "drivers/soc/qcom/qmi_interface.c"

SOURCE_SERVICES = [
    {"label": "servloc", "service": 64, "version": 1, "instance": 1},
    {"label": "ssctl", "service": 43, "version": 2, "instance": 16},
    {"label": "servnotif", "service": 66, "version": 1, "instance": 74},
    {"label": "servnotif", "service": 66, "version": 1, "instance": 180},
    {"label": "wlfw", "service": 69, "version": 1, "instance": 0},
]

FORBIDDEN_ACTIONS = (
    "host-only; no bridge command",
    "no device command, reboot, bootloader handoff, boot image write, or partition write",
    "no custom kernel flash",
    "no QRTR socket open or QRTR/QMI packet transmission",
    "no service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP, route, or external ping",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v823-manifest", type=Path, default=DEFAULT_V823_MANIFEST)
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


def encoded_instance(version: int, instance: int) -> int:
    return version | (instance << 8)


def matrix_rows(v823: dict[str, Any]) -> list[dict[str, Any]]:
    rows = (((v823.get("live") or {}).get("matrix") or {}).get("rows") or [])
    return rows if isinstance(rows, list) else []


def rows_for_service(rows: list[dict[str, Any]], service: int) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("service") == service]


def matrix_has(rows: list[dict[str, Any]], service: int, instance: int) -> bool:
    return any(row.get("service") == service and row.get("instance") == instance for row in rows)


def qmi_source_model() -> dict[str, Any]:
    source = read_source(QMI_INTERFACE)
    text = source["text"]
    encode_pattern = "svc->version | svc->instance << 8"
    return {
        "source": {key: value for key, value in source.items() if key != "text"},
        "has_encode_expression": encode_pattern in text,
        "has_qmi_add_lookup": "int qmi_add_lookup(" in text,
        "has_new_lookup": "QRTR_TYPE_NEW_LOOKUP" in text,
        "encode_expression": encode_pattern,
        "evidence_lines": [
            line.strip()
            for line in text.splitlines()
            if "QRTR_TYPE_NEW_LOOKUP" in line or "svc->version | svc->instance << 8" in line or "pkt.server.instance" in line
        ][:12],
        "qmi_add_lookup_line": next((idx for idx, line in enumerate(text.splitlines(), start=1) if "int qmi_add_lookup(" in line), None),
        "encode_line": next((idx for idx, line in enumerate(text.splitlines(), start=1) if "svc->version | svc->instance << 8" in line), None),
    }


def build_expected(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expected: list[dict[str, Any]] = []
    for item in SOURCE_SERVICES:
        encoded = encoded_instance(item["version"], item["instance"])
        expected.append({
            **item,
            "encoded_instance": encoded,
            "raw_in_v823": matrix_has(rows, item["service"], item["instance"]),
            "encoded_in_v823": matrix_has(rows, item["service"], encoded),
            "v823_rows_for_service": rows_for_service(rows, item["service"]),
        })
    return expected


def next_matrix(expected: list[dict[str, Any]]) -> str:
    groups: dict[str, dict[str, Any]] = {}
    for item in expected:
        group = groups.setdefault(item["label"], {"service": item["service"], "instances": []})
        group["instances"].append(str(item["encoded_instance"]))
    return ";".join(
        f"{label}:{group['service']}:{','.join(group['instances'])}"
        for label, group in groups.items()
    )


def build_checks(args: argparse.Namespace,
                 loaded: dict[str, Any],
                 source: dict[str, Any],
                 expected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    v823 = loaded["data"]
    all_raw_or_equivalent = all(item["raw_in_v823"] or item["encoded_in_v823"] for item in expected)
    missing_encoded = [item for item in expected if not item["encoded_in_v823"]]
    return [
        {
            "name": "host-only-boundary",
            "status": "pass",
            "detail": "no bridge/device command; source and V823 evidence only",
            "next_step": "keep V824 host-only",
        },
        {
            "name": "v823-input-ready",
            "status": "pass" if loaded["file"].get("exists") and v823.get("pass") and v823.get("decision") == "v823-ssctl-nameservice-clean-empty-below-hal" else "blocked",
            "detail": {"file": loaded["file"], "decision": v823.get("decision"), "pass": v823.get("pass")},
            "next_step": "complete V823 before V824",
        },
        {
            "name": "qmi-source-encoding-ready",
            "status": "pass" if source["source"].get("exists") and source["has_qmi_add_lookup"] and source["has_new_lookup"] and source["has_encode_expression"] else "blocked",
            "detail": source,
            "next_step": "restore staged qmi_interface.c before classification",
        },
        {
            "name": "v823-used-unencoded-or-partial-instances",
            "status": "finding" if all_raw_or_equivalent and missing_encoded else "blocked",
            "detail": {"expected": expected, "missing_encoded": missing_encoded},
            "next_step": "run encoded-instance matrix before interpreting clean-empty as service absence",
        },
    ]


def decide(checks: list[dict[str, Any]], expected: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    if blockers:
        return (
            "v824-qrtr-encoded-instance-classifier-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "resolve host-only evidence/source blockers before selecting next live gate",
        )
    return (
        "v824-qmi-encoded-instance-gap-classified",
        True,
        "kernel qmi_add_lookup encodes QRTR instance as version | instance << 8, while V823 mostly queried raw instances",
        f"V825 should run no-QMI encoded matrix {next_matrix(expected)} before any wider trigger",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    loaded = load_json(args.v823_manifest)
    v823 = loaded["data"]
    source = qmi_source_model()
    rows = matrix_rows(v823)
    expected = build_expected(rows)
    checks = build_checks(args, loaded, source, expected)
    decision, pass_ok, reason, next_step = decide(checks, expected)
    if args.command == "plan":
        decision = "v824-qrtr-encoded-instance-classifier-plan-ready"
        reason = "plan-only; host-only encoded-instance classifier defined"
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v824",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v823": {
            "file": loaded["file"],
            "decision": v823.get("decision"),
            "pass": v823.get("pass"),
            "matrix": ((v823.get("live") or {}).get("matrix") or {}),
        },
        "qmi_source_model": source,
        "expected_encoded_services": expected,
        "next_encoded_matrix": next_matrix(expected),
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
    expected_rows = [
        [
            item["label"],
            str(item["service"]),
            str(item["version"]),
            str(item["instance"]),
            str(item["encoded_instance"]),
            str(item["raw_in_v823"]),
            str(item["encoded_in_v823"]),
        ]
        for item in manifest["expected_encoded_services"]
    ]
    return "\n".join([
        "# V824 QRTR Encoded Instance Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- next_encoded_matrix: `{manifest['next_encoded_matrix']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Encoded Instances",
        "",
        markdown_table(["label", "service", "version", "raw_instance", "encoded_instance", "raw_in_v823", "encoded_in_v823"], expected_rows),
        "",
        "## Source Evidence",
        "",
        f"- source: `{manifest['qmi_source_model']['source']['path']}`",
        f"- qmi_add_lookup_line: `{manifest['qmi_source_model']['qmi_add_lookup_line']}`",
        f"- encode_line: `{manifest['qmi_source_model']['encode_line']}`",
        f"- encode_expression: `{manifest['qmi_source_model']['encode_expression']}`",
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
    print(f"next_encoded_matrix: {manifest['next_encoded_matrix']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"qmi_payload_executed: {manifest['qmi_payload_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
