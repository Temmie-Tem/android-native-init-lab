#!/usr/bin/env python3
"""V825 encoded-instance QRTR nameservice matrix.

V824 showed that kernel QMI clients encode the QRTR nameservice instance as
`version | instance << 8`.  V825 reuses helper v125 and the V817 lower window,
but replaces the raw V823 matrix with encoded instance values while keeping QMI
payload, HAL, scan/connect, credentials, DHCP, routing, external ping, and
custom kernel flashing blocked.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_qrtr_nameservice_matrix_v821 as v821
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v825-qrtr-encoded-matrix")
LATEST_POINTER = Path("tmp/wifi/latest-v825-qrtr-encoded-matrix.txt")
DEFAULT_V824_MANIFEST = Path("tmp/wifi/v824-qrtr-encoded-instance-classifier/manifest.json")
DEFAULT_MATRIX = "servloc:64:257;ssctl:43:4098;servnotif:66:18945,46081;wlfw:69:1"
PROOF_PREFIX = "/tmp/a90-v825-"

FORBIDDEN_ACTIONS = (
    "custom kernel flash, boot image write, partition write, or bootloader handoff",
    "esoc0 open, qcwlanstate on/off, bind/unbind, driver override, or module load/unload",
    "QMI payload transmission",
    "service-manager, Wi-Fi HAL, wificond, supplicant, scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v821.v817.base.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v821.v817.base.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=v821.v817.base.DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=v821.v817.base.DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=v821.v817.base.DEFAULT_BUSYBOX_PATH)
    parser.add_argument("--helper", default=v821.v817.base.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=v821.DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=v821.DEFAULT_HELPER_MARKER)
    parser.add_argument("--local-helper", type=Path, default=v821.DEFAULT_LOCAL_HELPER)
    parser.add_argument("--expect-version", default=v821.v817.base.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--hold-sec", type=int, default=v821.v817.base.DEFAULT_HOLD_SEC)
    parser.add_argument("--companion-runtime-sec", type=int, default=v821.v817.DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=v821.v817.base.DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=v821.v817.base.DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--v731-manifest", type=Path, default=v821.v817.base.DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=v821.v817.base.DEFAULT_V732_MANIFEST)
    parser.add_argument("--v734-manifest", type=Path, default=v821.v817.v735.DEFAULT_V734_MANIFEST)
    parser.add_argument("--v816-manifest", type=Path, default=v821.v817.DEFAULT_V816_MANIFEST)
    parser.add_argument("--v824-manifest", type=Path, default=DEFAULT_V824_MANIFEST)
    parser.add_argument("--qrtr-matrix", default=DEFAULT_MATRIX)
    parser.add_argument("--transfer-method", choices=("auto", "ncm", "serial"), default="auto")
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
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


def expected_case_count(matrix: str) -> int:
    count = 0
    for group in matrix.split(";"):
        parts = [part.strip() for part in group.split(":")]
        if len(parts) != 3 or not parts[2]:
            continue
        count += len([item for item in parts[2].split(",") if item.strip()])
    return count


def expected_rows(matrix: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    case = 0
    for group in matrix.split(";"):
        parts = [part.strip() for part in group.split(":")]
        if len(parts) != 3:
            continue
        label, service_text, instances_text = parts
        try:
            service = int(service_text, 0)
        except ValueError:
            continue
        for instance_text in instances_text.split(","):
            instance_text = instance_text.strip()
            if not instance_text:
                continue
            try:
                instance = int(instance_text, 0)
            except ValueError:
                continue
            rows.append({"case": case, "label": label, "service": service, "instance": instance})
            case += 1
    return rows


def live_rows_for(matrix: dict[str, Any], service: int, instance: int) -> list[dict[str, Any]]:
    return [
        row for row in matrix.get("rows", [])
        if v821.int_value(row.get("service")) == service and v821.int_value(row.get("instance")) == instance
    ]


def encoded_rows_present(matrix: dict[str, Any], expected: list[dict[str, Any]]) -> bool:
    return all(live_rows_for(matrix, row["service"], row["instance"]) for row in expected)


def v824_input(args: argparse.Namespace) -> dict[str, Any]:
    loaded = load_json(args.v824_manifest)
    data = loaded["data"]
    return {
        "file": loaded["file"],
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
        "next_step": data.get("next_step", ""),
        "next_encoded_matrix": data.get("next_encoded_matrix", ""),
    }


def run_live(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    previous_prefix = v821.PROOF_PREFIX
    v821.PROOF_PREFIX = PROOF_PREFIX
    try:
        return v821.run_live(args, store)
    finally:
        v821.PROOF_PREFIX = previous_prefix


def build_checks(args: argparse.Namespace,
                 v824: dict[str, Any],
                 local: dict[str, Any],
                 deploy: dict[str, Any] | None,
                 live: dict[str, Any] | None) -> list[dict[str, Any]]:
    expected = expected_rows(args.qrtr_matrix)
    expected_cases = len(expected)
    checks: list[dict[str, Any]] = [
        {
            "name": "v824-route-ready",
            "status": "pass" if (
                v824["pass"]
                and v824["decision"] == "v824-qmi-encoded-instance-gap-classified"
                and v824["next_encoded_matrix"] == args.qrtr_matrix
            ) else "blocked",
            "detail": v824,
            "next_step": "complete V824 before V825",
        },
        {
            "name": "local-helper-v125",
            "status": "pass" if local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["matrix_option"] else "blocked",
            "detail": local,
            "next_step": "rebuild helper v125 before live encoded matrix",
        },
        {
            "name": "host-only-plan-boundary" if args.command == "plan" else "preflight-live-boundary",
            "status": "pass",
            "detail": "plan has no device command; preflight/run keep QMI payload, HAL/connect, credentials, and networking blocked",
            "next_step": "continue only inside V825 guardrails",
        },
    ]
    if args.command == "plan":
        return checks
    checks.append({
        "name": "helper-v125-ready" if args.command == "preflight" else "helper-v125-deploy-run",
        "status": "pass" if deploy and deploy.get("pass") else "blocked",
        "detail": deploy or {},
        "next_step": "fix helper v125 readiness before encoded nameservice matrix",
    })
    if args.command == "preflight":
        return checks
    matrix = (live or {}).get("matrix", {})
    forbidden = (live or {}).get("forbidden", {})
    forbidden_ok = all(value in {False, None, 0} for value in forbidden.values())
    matrix_ok = (
        matrix.get("allowed") == 1
        and matrix.get("send_attempted") == 1
        and matrix.get("result") == "complete"
        and matrix.get("case_count") == expected_cases
        and matrix.get("qmi_payload") == 0
        and matrix.get("total_qmi_attempted") == 0
        and matrix.get("total_timeouts") == 0
        and matrix.get("socket_ok")
        and matrix.get("lookup_ok")
        and encoded_rows_present(matrix, expected)
    )
    checks.extend([
        {
            "name": "v817-window-with-v125",
            "status": "pass" if live and live.get("pass") else "blocked",
            "detail": {"decision": (live or {}).get("decision"), "pass": (live or {}).get("pass"), "manifest": (live or {}).get("manifest")},
            "next_step": "restore V817 lower window before interpreting encoded matrix",
        },
        {
            "name": "guardrails-preserved",
            "status": "pass" if forbidden_ok and matrix.get("qmi_payload") == 0 and matrix.get("total_qmi_attempted") == 0 else "blocked",
            "detail": {"forbidden": forbidden, "matrix": matrix},
            "next_step": "discard run if QMI payload/HAL/connect/network action occurred",
        },
        {
            "name": "encoded-matrix-complete",
            "status": "pass" if matrix_ok else "blocked",
            "detail": {"expected_cases": expected_cases, "expected_rows": expected, "matrix": matrix},
            "next_step": "fix encoded matrix readback before selecting next blocker",
        },
        {
            "name": "encoded-publication-result",
            "status": "finding",
            "detail": {"expected_rows": expected, "matrix": matrix},
            "next_step": "if encoded services publish, classify continuation; otherwise close raw-vs-encoded explanation",
        },
    ])
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], live: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v825-encoded-instance-matrix-plan-ready",
            True,
            "plan-only; encoded-instance helper v125 matrix gate defined without live action",
            "run V825 preflight, then live encoded-instance matrix if clean",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v825-encoded-instance-matrix-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "resolve blocker before continuing toward Wi-Fi bring-up",
        )
    if args.command == "preflight":
        return (
            "v825-encoded-instance-matrix-preflight-ready",
            True,
            "preflight passed; live encoded-instance matrix remains gated",
            "run V825 live encoded-instance nameservice matrix",
        )
    matrix = (live or {}).get("matrix", {})
    service_events = sum(v821.int_value(row.get("service_events")) for row in matrix.get("rows", []))
    if service_events:
        return (
            "v825-encoded-publication-visible",
            True,
            f"encoded nameservice publication observed with service_events={service_events} below QMI payload/HAL/connect",
            "classify published services and continuation before any QMI payload, HAL, scan/connect, credential, DHCP, route, or external ping",
        )
    return (
        "v825-encoded-nameservice-clean-empty-below-hal",
        True,
        "encoded nameservice matrix completed but returned only end-of-list below QMI payload/HAL/connect",
        "classify kernel QMI-client progress versus userspace AF_QIPCRTR lookup visibility; raw-vs-encoded explanation is closed",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    store.mkdir("host")
    v824 = v824_input(args)
    local = v821.local_helper(args)
    deploy: dict[str, Any] | None = None
    live: dict[str, Any] | None = None
    if args.command == "preflight":
        deploy = v821.deploy_helper(args, store, "preflight")
    elif args.command == "run":
        deploy = v821.deploy_helper(args, store, "run")
        if deploy.get("pass"):
            live = run_live(args, store)
    checks = build_checks(args, v824, local, deploy, live)
    decision, pass_ok, reason, next_step = decide(args, checks, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v825",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v824": v824,
        "local_helper": local,
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "qrtr_matrix": args.qrtr_matrix,
        "expected_rows": expected_rows(args.qrtr_matrix),
        "expected_case_count": expected_case_count(args.qrtr_matrix),
        "deploy": deploy,
        "live": live,
        "checks": checks,
        "device_commands_executed": bool(live),
        "device_mutations": bool(live) or bool((deploy or {}).get("device_mutations")),
        "helper_deploy_executed": bool((deploy or {}).get("device_mutations")),
        "reboot_cleanup_executed": bool((live or {}).get("reboot_cleanup_executed")),
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "esoc0_open_executed": False,
        "module_load_unload_executed": False,
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
    matrix = ((manifest.get("live") or {}).get("matrix") or {})
    row_rows = [
        [
            str(row.get("case")),
            str(row.get("label")),
            str(row.get("service")),
            str(row.get("instance")),
            str(row.get("service_events")),
            str(row.get("end_of_list")),
            str(row.get("timeout")),
            str(row.get("qmi_attempted")),
        ]
        for row in matrix.get("rows", [])
    ]
    return "\n".join([
        "# V825 Encoded QRTR Nameservice Matrix",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- qrtr_matrix: `{manifest['qrtr_matrix']}`",
        f"- expected_case_count: `{manifest['expected_case_count']}`",
        f"- helper_deploy_executed: `{manifest['helper_deploy_executed']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- qmi_payload_executed: `{manifest['qmi_payload_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Matrix Rows",
        "",
        markdown_table(["case", "label", "service", "instance", "service_events", "eol", "timeout", "qmi_attempted"], row_rows) if row_rows else "- none",
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"helper_deploy_executed: {manifest['helper_deploy_executed']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"qmi_payload_executed: {manifest['qmi_payload_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
