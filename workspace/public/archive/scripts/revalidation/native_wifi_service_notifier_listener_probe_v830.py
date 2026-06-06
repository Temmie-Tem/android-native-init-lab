#!/usr/bin/env python3
"""V830 bounded service-notifier REGISTER_LISTENER probe.

V829 proved that service-locator maps `wlan/fw` to `msm/modem/wlan_pd`
instance 180.  V830 sends only the corresponding service-notifier
REGISTER_LISTENER request to service 66 / encoded instance 46081, then parses
the response and any immediate STATE_UPDATED indication.  It does not start
service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external
ping, partition writes, boot image writes, or custom kernel flashing.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v830-service-notifier-listener-probe")
LATEST_POINTER = Path("tmp/wifi/latest-v830-service-notifier-listener-probe.txt")
DEFAULT_V829_MANIFEST = Path("tmp/wifi/latest-v829-servloc-domain-list-probe.txt")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v830-execns-helper-v127-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "e2ba21fc7f00afc433fa23358d05780dcc0e5288bfc7db7d015e87c61d3e36d7"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v127"
DEFAULT_MATRIX = "servnotif:66:46081;wlfw:69:1"
REGISTER_REQUEST_HEX = "00010020001800010100010211006d736d2f6d6f64656d2f776c616e5f7064"
DEPLOY_APPROVAL = "approve v830 deploy execns helper v127 only; no daemon start and no Wi-Fi bring-up"
PROOF_PREFIX = "/tmp/a90-v830-"

FORBIDDEN_ACTIONS = (
    "custom kernel flash, boot image write, partition write, or bootloader handoff",
    "esoc0 open, qcwlanstate on/off, bind/unbind, driver override, or module load/unload",
    "service-manager, Wi-Fi HAL, wificond, supplicant, scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "only the bounded service-notifier REGISTER_LISTENER and optional ACK QMI requests are allowed",
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
    parser.add_argument("--v829-manifest", type=Path, default=DEFAULT_V829_MANIFEST)
    parser.add_argument("--qrtr-matrix", default=DEFAULT_MATRIX)
    parser.add_argument("--transfer-method", choices=("auto", "ncm", "serial"), default="auto")
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


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


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def resolve_manifest_path(path: Path) -> Path:
    resolved = path if path.is_absolute() else repo_path(path)
    if resolved.is_dir():
        return resolved / "manifest.json"
    if resolved.exists():
        text = resolved.read_text(encoding="utf-8", errors="replace").strip()
        if text and not text.startswith("{"):
            pointed = Path(text)
            if not pointed.is_absolute():
                pointed = repo_path(pointed)
            if pointed.is_dir():
                return pointed / "manifest.json"
            return pointed
    return resolved


def load_manifest(path: Path) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(path)
    if not manifest_path.exists():
        return {"file": {"path": str(manifest_path), "exists": False}, "data": {}}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"file": {"path": str(manifest_path), "exists": True}, "data": {}, "error": str(exc)}
    return {
        "file": {"path": str(manifest_path), "exists": True, "size": manifest_path.stat().st_size},
        "data": data if isinstance(data, dict) else {},
    }


def local_helper(args: argparse.Namespace) -> dict[str, Any]:
    path = repo_path(args.local_helper)
    info: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "sha256": "",
        "marker": False,
        "listener_option": False,
        "matrix_option": False,
    }
    if not path.exists():
        return info
    info["sha256"] = sha256_file(path)
    result = subprocess.run(["strings", str(path)], cwd=repo_path("."), text=True, capture_output=True, check=False)
    strings_output = result.stdout if result.returncode == 0 else ""
    info["marker"] = args.helper_marker in strings_output
    info["listener_option"] = "--allow-service-notifier-listener-probe" in strings_output
    info["matrix_option"] = "--qrtr-readback-matrix" in strings_output
    return info


def v829_input(args: argparse.Namespace) -> dict[str, Any]:
    loaded = load_manifest(args.v829_manifest)
    data = loaded["data"]
    live = data.get("live") if isinstance(data.get("live"), dict) else {}
    servloc = live.get("servloc") if isinstance(live.get("servloc"), dict) else data.get("v829_servloc", {})
    domains = servloc.get("domains") if isinstance(servloc, dict) else []
    wlan_domain = None
    if isinstance(domains, list):
        for domain in domains:
            if isinstance(domain, dict) and domain.get("name") == "msm/modem/wlan_pd":
                wlan_domain = domain
                break
    return {
        "file": loaded["file"],
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
        "next_step": data.get("next_step", ""),
        "servloc": servloc if isinstance(servloc, dict) else {},
        "wlan_domain": wlan_domain or {},
    }


def deploy_helper(args: argparse.Namespace, store: EvidenceStore, command: str) -> dict[str, Any]:
    deploy_dir = store.path(f"deploy-v127-{command}")
    cmd = [
        "python3",
        "scripts/revalidation/wifi_execns_helper_v127_deploy_preflight.py",
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
    result = run_host(store, f"v830-deploy-{command}", cmd, timeout)
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


def summarize_service_notifier(helper_payload: str) -> dict[str, Any]:
    keys = v821.parse_key_values(helper_payload)
    prefix = "wifi_companion_service_notifier_listener"
    packets = []
    index = 0
    while f"{prefix}.packet.{index}.bytes" in keys:
        packet_prefix = f"{prefix}.packet.{index}"
        packets.append({
            "index": index,
            "bytes": int_value(keys.get(f"{packet_prefix}.bytes")),
            "from_node": int_value(keys.get(f"{packet_prefix}.from.node")),
            "from_port": int_value(keys.get(f"{packet_prefix}.from.port")),
            "type": int_value(keys.get(f"{packet_prefix}.type")),
            "txn_id": int_value(keys.get(f"{packet_prefix}.txn_id")),
            "msg_id": int_value(keys.get(f"{packet_prefix}.msg_id")),
        })
        index += 1
    return {
        "allowed": int_value(keys.get(f"{prefix}.allowed")),
        "service": int_value(keys.get(f"{prefix}.service")),
        "instance": int_value(keys.get(f"{prefix}.instance")),
        "service_name": keys.get(f"{prefix}.service_name", ""),
        "qmi_payload": int_value(keys.get(f"{prefix}.qmi_payload")),
        "request_hex": keys.get(f"{prefix}.register_request_hex", ""),
        "result": keys.get(f"{prefix}.result", ""),
        "endpoint_found": int_value(keys.get(f"{prefix}.endpoint.found")),
        "endpoint_node": int_value(keys.get(f"{prefix}.endpoint.node")),
        "endpoint_port": int_value(keys.get(f"{prefix}.endpoint.port")),
        "send_attempted": int_value(keys.get(f"{prefix}.send_attempted")),
        "register_send_rc": int_value(keys.get(f"{prefix}.register_send.rc")),
        "register_send_bytes": int_value(keys.get(f"{prefix}.register_send.bytes")),
        "register_response_parse": keys.get(f"{prefix}.register_response_parse", ""),
        "register_response_qmi_result_valid": int_value(keys.get(f"{prefix}.register_response.qmi_result_valid")),
        "register_response_qmi_result": int_value(keys.get(f"{prefix}.register_response.qmi_result")),
        "register_response_qmi_error": int_value(keys.get(f"{prefix}.register_response.qmi_error")),
        "response_seen": int_value(keys.get(f"{prefix}.response_seen")),
        "response_success": int_value(keys.get(f"{prefix}.response_success")),
        "response_curr_state_valid": int_value(keys.get(f"{prefix}.response_curr_state_valid")),
        "response_curr_state": keys.get(f"{prefix}.response_curr_state", ""),
        "response_curr_state_name": keys.get(f"{prefix}.response_curr_state_name", ""),
        "indication_seen": int_value(keys.get(f"{prefix}.indication_seen")),
        "indication_valid": int_value(keys.get(f"{prefix}.indication_valid")),
        "indication_curr_state": keys.get(f"{prefix}.indication_curr_state", ""),
        "indication_curr_state_name": keys.get(f"{prefix}.indication_curr_state_name", ""),
        "ack_sent": int_value(keys.get(f"{prefix}.ack_sent")),
        "ack_success": int_value(keys.get(f"{prefix}.ack_success")),
        "packets": packets,
    }


def configure_v830(args: argparse.Namespace) -> tuple[Any, Any]:
    v817.configure_base()
    v817.PROOF_PREFIX = PROOF_PREFIX
    original_v735_helper = v817.v735.helper_command
    original_base_helper = v817.base.helper_command

    def helper_command_with_listener_probe(inner_args: argparse.Namespace) -> list[str]:
        return original_v735_helper(inner_args) + [
            "--qrtr-readback-matrix",
            args.qrtr_matrix,
            "--allow-service-notifier-listener-probe",
        ]

    v817.v735.helper_command = helper_command_with_listener_probe
    v817.base.helper_command = helper_command_with_listener_probe
    return original_v735_helper, original_base_helper


def restore_helpers(original_v735_helper: Any, original_base_helper: Any) -> None:
    v817.v735.helper_command = original_v735_helper
    v817.base.helper_command = original_base_helper


def run_live(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    live_store = EvidenceStore(store.path("live-v817-v127-service-notifier-listener"))
    live_store.mkdir("native")
    live_store.mkdir("host")
    original_v735_helper, original_base_helper = configure_v830(args)
    try:
        live_manifest = v817.build_manifest(args, live_store)
    finally:
        restore_helpers(original_v735_helper, original_base_helper)
    helper_payload = ""
    for step in live_manifest.get("steps", []):
        if step.get("name") == "lower-companion-start-only":
            helper_payload = str(step.get("payload") or "")
            break
    live_manifest["v830_matrix"] = v821.summarize_matrix(helper_payload)
    live_manifest["v830_service_notifier"] = summarize_service_notifier(helper_payload)
    live_store.write_json("manifest-v830-annotated.json", live_manifest)
    live_store.write_text("summary-v830.md", v817.render_summary(live_manifest))
    return {
        "manifest": str(live_store.run_dir / "manifest-v830-annotated.json"),
        "decision": live_manifest.get("decision"),
        "pass": live_manifest.get("pass"),
        "live": live_manifest.get("live", {}),
        "matrix": live_manifest["v830_matrix"],
        "service_notifier": live_manifest["v830_service_notifier"],
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
                 v829: dict[str, Any],
                 local: dict[str, Any],
                 deploy: dict[str, Any] | None,
                 live: dict[str, Any] | None) -> list[dict[str, Any]]:
    wlan_domain = v829.get("wlan_domain", {})
    checks: list[dict[str, Any]] = [
        {
            "name": "v829-domain-ready",
            "status": "pass" if (
                v829["pass"]
                and v829["decision"] == "v829-servloc-domain-list-response-success"
                and wlan_domain.get("name") == "msm/modem/wlan_pd"
                and int_value(wlan_domain.get("instance_id")) == 180
            ) else "blocked",
            "detail": v829,
            "next_step": "complete V829 domain-list proof before V830",
        },
        {
            "name": "local-helper-v127",
            "status": "pass" if (
                local["exists"]
                and local["sha256"] == args.helper_sha256
                and local["marker"]
                and local["listener_option"]
                and local["matrix_option"]
            ) else "blocked",
            "detail": local,
            "next_step": "rebuild helper v127 before live service-notifier probe",
        },
        {
            "name": "host-only-plan-boundary" if args.command == "plan" else "preflight-live-boundary",
            "status": "pass",
            "detail": "plan has no device command; live sends only bounded service-notifier listener QMI below HAL/connect",
            "next_step": "continue only inside V830 guardrails",
        },
    ]
    if args.command == "plan":
        return checks
    checks.append({
        "name": "helper-v127-ready" if args.command == "preflight" else "helper-v127-deploy-run",
        "status": "pass" if deploy and deploy.get("pass") else "blocked",
        "detail": deploy or {},
        "next_step": "fix helper v127 readiness before service-notifier probe",
    })
    if args.command == "preflight":
        return checks
    matrix = (live or {}).get("matrix", {})
    servnotif = (live or {}).get("service_notifier", {})
    forbidden = (live or {}).get("forbidden", {})
    forbidden_ok = all(value in {False, None, 0} for value in forbidden.values())
    listener_attempt_ok = (
        servnotif.get("allowed") == 1
        and servnotif.get("qmi_payload") == 1
        and servnotif.get("request_hex") == REGISTER_REQUEST_HEX
        and servnotif.get("endpoint_found") == 1
        and servnotif.get("send_attempted") == 1
        and servnotif.get("register_send_rc") == 0
        and servnotif.get("register_send_bytes") == 31
    )
    checks.extend([
        {
            "name": "v817-window-with-v127",
            "status": "pass" if live and live.get("pass") else "blocked",
            "detail": {"decision": (live or {}).get("decision"), "pass": (live or {}).get("pass"), "manifest": (live or {}).get("manifest")},
            "next_step": "restore V817 lower window before interpreting service-notifier probe",
        },
        {
            "name": "guardrails-preserved",
            "status": "pass" if forbidden_ok else "blocked",
            "detail": {"forbidden": forbidden, "matrix": matrix, "service_notifier": servnotif},
            "next_step": "discard run if HAL/connect/credential/network/flash action occurred",
        },
        {
            "name": "service-notifier-listener-attempt",
            "status": "pass" if listener_attempt_ok else "blocked",
            "detail": servnotif,
            "next_step": "fix endpoint discovery or request send before interpreting listener response",
        },
        {
            "name": "service-notifier-state-result",
            "status": "finding",
            "detail": servnotif,
            "next_step": "if state is up, watch WLFW service 69; otherwise classify modem/WLAN-PD online trigger gap",
        },
    ])
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], live: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v830-service-notifier-listener-plan-ready",
            True,
            "plan-only; helper v127 bounded service-notifier listener gate defined without live action",
            "run V830 preflight, then live listener probe if clean",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v830-service-notifier-listener-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "resolve blocker before continuing toward Wi-Fi bring-up",
        )
    if args.command == "preflight":
        return (
            "v830-service-notifier-listener-preflight-ready",
            True,
            "preflight passed; helper v127 deploy/live listener probe remains gated",
            "run V830 live bounded service-notifier listener probe",
        )
    servnotif = (live or {}).get("service_notifier", {})
    up_seen = (
        servnotif.get("response_curr_state_name") == "up"
        or servnotif.get("indication_curr_state_name") == "up"
    )
    if servnotif.get("response_success") == 1 and up_seen:
        return (
            "v830-service-notifier-listener-state-up",
            True,
            "service-notifier listener response or indication reports wlan_pd UP",
            "watch WLFW service 69 and ICNSS firmware-ready path before HAL/connect",
        )
    if servnotif.get("response_success") == 1:
        return (
            "v830-service-notifier-listener-state-not-up",
            True,
            f"listener registered but state is response={servnotif.get('response_curr_state_name')} indication={servnotif.get('indication_curr_state_name')}",
            "classify modem/WLAN-PD online trigger gap before HAL/connect",
        )
    if servnotif.get("response_seen") == 1:
        return (
            "v830-service-notifier-listener-response-error",
            True,
            "service-notifier endpoint responded but listener registration was not successful",
            "classify QMI response before retrying wider Wi-Fi stack",
        )
    return (
        "v830-service-notifier-listener-no-response",
        True,
        "REGISTER_LISTENER was sent but no matching response was observed in the bounded window",
        "classify service-notifier endpoint lifetime or QMI transaction routing before HAL/connect",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    store.mkdir("host")
    v829 = v829_input(args)
    local = local_helper(args)
    deploy: dict[str, Any] | None = None
    live: dict[str, Any] | None = None
    if args.command == "preflight":
        deploy = deploy_helper(args, store, "preflight")
    elif args.command == "run":
        deploy = deploy_helper(args, store, "run")
        if deploy.get("pass"):
            live = run_live(args, store)
    checks = build_checks(args, v829, local, deploy, live)
    decision, pass_ok, reason, next_step = decide(args, checks, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v830",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v829": v829,
        "local_helper": local,
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "qrtr_matrix": args.qrtr_matrix,
        "register_request_hex": REGISTER_REQUEST_HEX,
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
    servnotif = ((manifest.get("live") or {}).get("service_notifier") or {})
    packet_rows = [
        [
            str(row.get("index")),
            str(row.get("bytes")),
            str(row.get("from_node")),
            str(row.get("from_port")),
            str(row.get("type")),
            str(row.get("txn_id")),
            str(row.get("msg_id")),
        ]
        for row in servnotif.get("packets", [])
    ]
    return "\n".join([
        "# V830 Service-notifier Listener Probe",
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
        "## Service-notifier Result",
        "",
        f"- endpoint_found: `{servnotif.get('endpoint_found', '')}`",
        f"- send_attempted: `{servnotif.get('send_attempted', '')}`",
        f"- response_seen: `{servnotif.get('response_seen', '')}`",
        f"- response_success: `{servnotif.get('response_success', '')}`",
        f"- register_response_qmi_result: `{servnotif.get('register_response_qmi_result', '')}`",
        f"- register_response_qmi_error: `{servnotif.get('register_response_qmi_error', '')}`",
        f"- response_curr_state_name: `{servnotif.get('response_curr_state_name', '')}`",
        f"- indication_seen: `{servnotif.get('indication_seen', '')}`",
        f"- indication_curr_state_name: `{servnotif.get('indication_curr_state_name', '')}`",
        f"- ack_sent: `{servnotif.get('ack_sent', '')}`",
        f"- ack_success: `{servnotif.get('ack_success', '')}`",
        f"- result: `{servnotif.get('result', '')}`",
        "",
        "## Packets",
        "",
        markdown_table(["idx", "bytes", "from_node", "from_port", "type", "txn_id", "msg_id"], packet_rows) if packet_rows else "- none",
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
