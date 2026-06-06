#!/usr/bin/env python3
"""V829 bounded service-locator GET_DOMAIN_LIST probe.

V828 derived the exact QMI request for `GET_DOMAIN_LIST wlan/fw`.  V829 deploys
helper v126 and sends only that request to the live service-locator endpoint
inside the established V817 lower window.  It still blocks service-manager,
Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, partition
writes, boot image writes, and custom kernel flashing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import native_wifi_in_window_sysmon_sampler_v817 as v817
import native_wifi_qrtr_nameservice_matrix_v821 as v821
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v829-servloc-domain-list-probe")
LATEST_POINTER = Path("tmp/wifi/latest-v829-servloc-domain-list-probe.txt")
DEFAULT_V828_MANIFEST = Path("tmp/wifi/v828-servloc-domain-list-payload/manifest.json")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v829-execns-helper-v126-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "106d408acf6d48c6a38350756cd921e8ffb8fcc518708855036fd858e79236e2"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v126"
DEFAULT_MATRIX = "servloc:64:257;servnotif:66:46081;wlfw:69:1"
REQUEST_HEX = "00010021001100010700776c616e2f667710040000000000"
DEPLOY_APPROVAL = "approve v829 deploy execns helper v126 only; no daemon start and no Wi-Fi bring-up"
PROOF_PREFIX = "/tmp/a90-v829-"

FORBIDDEN_ACTIONS = (
    "custom kernel flash, boot image write, partition write, or bootloader handoff",
    "esoc0 open, qcwlanstate on/off, bind/unbind, driver override, or module load/unload",
    "service-manager, Wi-Fi HAL, wificond, supplicant, scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "only the bounded service-locator GET_DOMAIN_LIST wlan/fw QMI request is allowed",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v817.base.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v817.base.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=v817.base.DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=v817.base.DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=v817.base.DEFAULT_BUSYBOX_PATH)
    parser.add_argument("--helper", default=v817.base.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--expect-version", default=v817.base.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--hold-sec", type=int, default=v817.base.DEFAULT_HOLD_SEC)
    parser.add_argument("--companion-runtime-sec", type=int, default=v817.DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=v817.base.DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=v817.base.DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--v731-manifest", type=Path, default=v817.base.DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=v817.base.DEFAULT_V732_MANIFEST)
    parser.add_argument("--v734-manifest", type=Path, default=v817.v735.DEFAULT_V734_MANIFEST)
    parser.add_argument("--v816-manifest", type=Path, default=v817.DEFAULT_V816_MANIFEST)
    parser.add_argument("--v828-manifest", type=Path, default=DEFAULT_V828_MANIFEST)
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_host(store: EvidenceStore, name: str, command: list[str], timeout: float) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        rc = result.returncode
        output = result.stdout + result.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        rc = None
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", errors="replace")
        output = stdout + stderr
        timed_out = True
    rel = f"host/{name}.txt"
    store.write_text(rel, "$ " + " ".join(command) + "\n" + output)
    return {"name": name, "command": command, "rc": rc, "ok": rc == 0 and not timed_out, "timed_out": timed_out, "file": rel}


def local_helper(args: argparse.Namespace) -> dict[str, Any]:
    path = repo_path(args.local_helper)
    info: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "sha256": "",
        "marker": False,
        "servloc_option": False,
        "matrix_option": False,
    }
    if not path.exists():
        return info
    info["sha256"] = sha256_file(path)
    result = subprocess.run(["strings", str(path)], cwd=repo_path("."), text=True, capture_output=True, check=False)
    strings_output = result.stdout if result.returncode == 0 else ""
    info["marker"] = args.helper_marker in strings_output
    info["servloc_option"] = "--allow-servloc-domain-list-probe" in strings_output
    info["matrix_option"] = "--qrtr-readback-matrix" in strings_output
    return info


def v828_input(args: argparse.Namespace) -> dict[str, Any]:
    loaded = load_json(args.v828_manifest)
    data = loaded["data"]
    request = data.get("request") if isinstance(data.get("request"), dict) else {}
    return {
        "file": loaded["file"],
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
        "next_step": data.get("next_step", ""),
        "request_hex": request.get("request_hex", ""),
        "destination_service": request.get("destination_service"),
        "destination_encoded_instance": request.get("destination_encoded_instance"),
    }


def deploy_helper(args: argparse.Namespace, store: EvidenceStore, command: str) -> dict[str, Any]:
    deploy_dir = store.path(f"deploy-v126-{command}")
    cmd = [
        "python3",
        "scripts/revalidation/wifi_execns_helper_v126_deploy_preflight.py",
        "--out-dir",
        str(deploy_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--expect-version",
        args.expect_version,
        "--local-helper",
        str(args.local_helper),
        "--remote-helper",
        args.helper,
        "--helper-sha256",
        args.helper_sha256,
        "--transfer-method",
        args.transfer_method,
    ]
    if command == "run":
        cmd.extend(["--approval-phrase", DEPLOY_APPROVAL, "--apply", "--assume-yes", "run"])
        timeout = 2400.0 if args.transfer_method in {"auto", "serial"} else 300.0
    else:
        cmd.append("preflight")
        timeout = 240.0
    result = run_host(store, f"v829-deploy-{command}", cmd, timeout)
    manifest_path = deploy_dir / "manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result.update({
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
        "device_mutations": manifest.get("device_mutations", False),
        "deploy_result": manifest.get("deploy_result"),
    })
    return result


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def summarize_servloc(helper_payload: str) -> dict[str, Any]:
    keys = v821.parse_key_values(helper_payload)
    domains: list[dict[str, Any]] = []
    index = 0
    while f"wifi_companion_servloc_domain_list.domain.{index}.status" in keys:
        prefix = f"wifi_companion_servloc_domain_list.domain.{index}"
        domains.append({
            "index": index,
            "name": keys.get(f"{prefix}.name", ""),
            "instance_id": int_value(keys.get(f"{prefix}.instance_id")),
            "service_data_valid": int_value(keys.get(f"{prefix}.service_data_valid")),
            "service_data": int_value(keys.get(f"{prefix}.service_data")),
            "contains_wlan": int_value(keys.get(f"{prefix}.contains_wlan")),
            "status": keys.get(f"{prefix}.status", ""),
        })
        index += 1
    return {
        "allowed": int_value(keys.get("wifi_companion_servloc_domain_list.allowed")),
        "qmi_payload": int_value(keys.get("wifi_companion_servloc_domain_list.qmi_payload")),
        "request_hex": keys.get("wifi_companion_servloc_domain_list.request_hex", ""),
        "send_attempted": int_value(keys.get("wifi_companion_servloc_domain_list.send_attempted")),
        "result": keys.get("wifi_companion_servloc_domain_list.result", ""),
        "endpoint_found": int_value(keys.get("wifi_companion_servloc_domain_list.endpoint.found")),
        "endpoint_node": int_value(keys.get("wifi_companion_servloc_domain_list.endpoint.node")),
        "endpoint_port": int_value(keys.get("wifi_companion_servloc_domain_list.endpoint.port")),
        "send_rc": int_value(keys.get("wifi_companion_servloc_domain_list.send.rc")),
        "send_bytes": int_value(keys.get("wifi_companion_servloc_domain_list.send.bytes")),
        "response_seen": int_value(keys.get("wifi_companion_servloc_domain_list.response_seen")),
        "response_success": int_value(keys.get("wifi_companion_servloc_domain_list.response_success")),
        "response_type": int_value(keys.get("wifi_companion_servloc_domain_list.response.type")),
        "response_txn_id": int_value(keys.get("wifi_companion_servloc_domain_list.response.txn_id")),
        "response_msg_id": int_value(keys.get("wifi_companion_servloc_domain_list.response.msg_id")),
        "response_parse": keys.get("wifi_companion_servloc_domain_list.response_parse", ""),
        "qmi_result_valid": int_value(keys.get("wifi_companion_servloc_domain_list.qmi_result_valid")),
        "qmi_result": int_value(keys.get("wifi_companion_servloc_domain_list.qmi_result")),
        "qmi_error": int_value(keys.get("wifi_companion_servloc_domain_list.qmi_error")),
        "total_domains": int_value(keys.get("wifi_companion_servloc_domain_list.total_domains")),
        "domain_count": int_value(keys.get("wifi_companion_servloc_domain_list.domain_count")),
        "wlan_like_domains": int_value(keys.get("wifi_companion_servloc_domain_list.wlan_like_domains")),
        "domains": domains,
    }


def configure_v829(args: argparse.Namespace) -> tuple[Any, Any]:
    v817.configure_base()
    v817.PROOF_PREFIX = PROOF_PREFIX
    original_v735_helper = v817.v735.helper_command
    original_base_helper = v817.base.helper_command

    def helper_command_with_servloc_probe(inner_args: argparse.Namespace) -> list[str]:
        return original_v735_helper(inner_args) + [
            "--qrtr-readback-matrix",
            args.qrtr_matrix,
            "--allow-servloc-domain-list-probe",
        ]

    v817.v735.helper_command = helper_command_with_servloc_probe
    v817.base.helper_command = helper_command_with_servloc_probe
    return original_v735_helper, original_base_helper


def restore_helpers(original_v735_helper: Any, original_base_helper: Any) -> None:
    v817.v735.helper_command = original_v735_helper
    v817.base.helper_command = original_base_helper


def run_live(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    live_store = EvidenceStore(store.path("live-v817-v126-servloc-domain-list"))
    live_store.mkdir("native")
    live_store.mkdir("host")
    original_v735_helper, original_base_helper = configure_v829(args)
    try:
        live_manifest = v817.build_manifest(args, live_store)
    finally:
        restore_helpers(original_v735_helper, original_base_helper)
    helper_payload = ""
    for step in live_manifest.get("steps", []):
        if step.get("name") == "lower-companion-start-only":
            helper_payload = str(step.get("payload") or "")
            break
    live_manifest["v829_matrix"] = v821.summarize_matrix(helper_payload)
    live_manifest["v829_servloc"] = summarize_servloc(helper_payload)
    live_store.write_json("manifest-v829-annotated.json", live_manifest)
    live_store.write_text("summary-v829.md", v817.render_summary(live_manifest))
    return {
        "manifest": str(live_store.run_dir / "manifest-v829-annotated.json"),
        "decision": live_manifest.get("decision"),
        "pass": live_manifest.get("pass"),
        "live": live_manifest.get("live", {}),
        "matrix": live_manifest["v829_matrix"],
        "servloc": live_manifest["v829_servloc"],
        "device_commands_executed": live_manifest.get("device_commands_executed", False),
        "device_mutations": live_manifest.get("device_mutations", False),
        "reboot_cleanup_executed": live_manifest.get("reboot_cleanup_executed", False),
        "forbidden": {
            "service_manager": live_manifest.get("service_manager_start_executed"),
            "wifi_hal": live_manifest.get("wifi_hal_start_executed"),
            "scan_connect": live_manifest.get("scan_connect_executed"),
            "credential": live_manifest.get("credential_use_executed"),
            "dhcp_route": live_manifest.get("dhcp_route_executed"),
            "external_ping": live_manifest.get("external_ping_executed"),
            "esoc0_open": live_manifest.get("esoc0_open_executed"),
            "module_load_unload": live_manifest.get("module_load_unload_executed"),
            "custom_kernel_flash": live_manifest.get("custom_kernel_flash_executed"),
            "boot_image_write": live_manifest.get("boot_image_write_executed"),
            "partition_write": live_manifest.get("partition_write_executed"),
        },
    }


def build_checks(args: argparse.Namespace,
                 v828: dict[str, Any],
                 local: dict[str, Any],
                 deploy: dict[str, Any] | None,
                 live: dict[str, Any] | None) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = [
        {
            "name": "v828-route-ready",
            "status": "pass" if (
                v828["pass"]
                and v828["decision"] == "v828-servloc-domain-list-payload-derived"
                and v828["request_hex"] == REQUEST_HEX
                and int_value(v828["destination_service"]) == 64
                and int_value(v828["destination_encoded_instance"]) == 257
            ) else "blocked",
            "detail": v828,
            "next_step": "complete V828 before V829",
        },
        {
            "name": "local-helper-v126",
            "status": "pass" if (
                local["exists"]
                and local["sha256"] == args.helper_sha256
                and local["marker"]
                and local["servloc_option"]
                and local["matrix_option"]
            ) else "blocked",
            "detail": local,
            "next_step": "rebuild helper v126 before live service-locator probe",
        },
        {
            "name": "host-only-plan-boundary" if args.command == "plan" else "preflight-live-boundary",
            "status": "pass",
            "detail": "plan has no device command; live sends exactly one bounded service-locator QMI request below HAL/connect",
            "next_step": "continue only inside V829 guardrails",
        },
    ]
    if args.command == "plan":
        return checks
    checks.append({
        "name": "helper-v126-ready" if args.command == "preflight" else "helper-v126-deploy-run",
        "status": "pass" if deploy and deploy.get("pass") else "blocked",
        "detail": deploy or {},
        "next_step": "fix helper v126 readiness before service-locator probe",
    })
    if args.command == "preflight":
        return checks
    matrix = (live or {}).get("matrix", {})
    servloc = (live or {}).get("servloc", {})
    forbidden = (live or {}).get("forbidden", {})
    forbidden_ok = all(value in {False, None, 0} for value in forbidden.values())
    servloc_attempt_ok = (
        servloc.get("allowed") == 1
        and servloc.get("qmi_payload") == 1
        and servloc.get("request_hex") == REQUEST_HEX
        and servloc.get("endpoint_found") == 1
        and servloc.get("send_attempted") == 1
        and servloc.get("send_rc") == 0
        and servloc.get("send_bytes") == 24
    )
    checks.extend([
        {
            "name": "v817-window-with-v126",
            "status": "pass" if live and live.get("pass") else "blocked",
            "detail": {"decision": (live or {}).get("decision"), "pass": (live or {}).get("pass"), "manifest": (live or {}).get("manifest")},
            "next_step": "restore V817 lower window before interpreting service-locator probe",
        },
        {
            "name": "guardrails-preserved",
            "status": "pass" if forbidden_ok else "blocked",
            "detail": {"forbidden": forbidden, "matrix": matrix, "servloc": servloc},
            "next_step": "discard run if HAL/connect/credential/network/flash action occurred",
        },
        {
            "name": "servloc-request-attempt",
            "status": "pass" if servloc_attempt_ok else "blocked",
            "detail": servloc,
            "next_step": "fix endpoint discovery or request send before interpreting response",
        },
        {
            "name": "servloc-response-result",
            "status": "finding",
            "detail": servloc,
            "next_step": "if response has WLAN domains, register matching service-notifier listener; otherwise classify no-response or QMI error",
        },
    ])
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], live: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v829-servloc-domain-list-probe-plan-ready",
            True,
            "plan-only; helper v126 bounded service-locator probe gate defined without live action",
            "run V829 preflight, then live service-locator probe if clean",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v829-servloc-domain-list-probe-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "resolve blocker before continuing toward Wi-Fi bring-up",
        )
    if args.command == "preflight":
        return (
            "v829-servloc-domain-list-probe-preflight-ready",
            True,
            "preflight passed; helper v126 deploy/live QMI probe remains gated",
            "run V829 live bounded service-locator probe",
        )
    servloc = (live or {}).get("servloc", {})
    if servloc.get("response_success") == 1 and int_value(servloc.get("domain_count")) > 0:
        return (
            "v829-servloc-domain-list-response-success",
            True,
            f"service-locator returned domain_count={servloc.get('domain_count')} wlan_like={servloc.get('wlan_like_domains')}",
            "derive and send bounded service-notifier REGISTER_LISTENER for returned WLAN domain",
        )
    if servloc.get("response_seen") == 1:
        return (
            "v829-servloc-domain-list-response-error",
            True,
            f"service-locator responded with result={servloc.get('qmi_result')} error={servloc.get('qmi_error')}",
            "classify service-locator response error before retrying wider Wi-Fi stack",
        )
    return (
        "v829-servloc-domain-list-no-response",
        True,
        "request was sent to service-locator endpoint but no matching response was observed in the bounded window",
        "classify service-locator endpoint lifetime or QMI transaction routing before HAL/connect",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    store.mkdir("host")
    v828 = v828_input(args)
    local = local_helper(args)
    deploy: dict[str, Any] | None = None
    live: dict[str, Any] | None = None
    if args.command == "preflight":
        deploy = deploy_helper(args, store, "preflight")
    elif args.command == "run":
        deploy = deploy_helper(args, store, "run")
        if deploy.get("pass"):
            live = run_live(args, store)
    checks = build_checks(args, v828, local, deploy, live)
    decision, pass_ok, reason, next_step = decide(args, checks, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v829",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v828": v828,
        "local_helper": local,
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "qrtr_matrix": args.qrtr_matrix,
        "request_hex": REQUEST_HEX,
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
        "qmi_payload_executed": args.command == "run" and bool(live),
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
    servloc = ((manifest.get("live") or {}).get("servloc") or {})
    domain_rows = [
        [
            str(row.get("index")),
            str(row.get("name")),
            str(row.get("instance_id")),
            str(row.get("service_data_valid")),
            str(row.get("service_data")),
            str(row.get("contains_wlan")),
            str(row.get("status")),
        ]
        for row in servloc.get("domains", [])
    ]
    return "\n".join([
        "# V829 Service-locator Domain-list Probe",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
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
        "## Service-locator Result",
        "",
        f"- endpoint_found: `{servloc.get('endpoint_found', '')}`",
        f"- send_attempted: `{servloc.get('send_attempted', '')}`",
        f"- response_seen: `{servloc.get('response_seen', '')}`",
        f"- response_success: `{servloc.get('response_success', '')}`",
        f"- result: `{servloc.get('result', '')}`",
        f"- total_domains: `{servloc.get('total_domains', '')}`",
        f"- domain_count: `{servloc.get('domain_count', '')}`",
        f"- wlan_like_domains: `{servloc.get('wlan_like_domains', '')}`",
        "",
        "## Domain Rows",
        "",
        markdown_table(["idx", "name", "instance", "data_valid", "data", "wlan", "status"], domain_rows) if domain_rows else "- none",
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
