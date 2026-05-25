#!/usr/bin/env python3
"""V821 in-helper QRTR nameservice matrix.

V820 proved that AF_QIPCRTR readback works while procfs/debugfs QRTR visibility
is absent.  V821 deploys/uses helper v125 and widens only the nameservice
lookup matrix inside the already-established V817 lower window.  It does not
send QMI payloads and does not start service-manager, Wi-Fi HAL, scan/connect,
DHCP, routes, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import native_wifi_in_window_sysmon_sampler_v817 as v817
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v821-qrtr-nameservice-matrix")
LATEST_POINTER = Path("tmp/wifi/latest-v821-qrtr-nameservice-matrix.txt")
DEFAULT_V820_MANIFEST = Path("tmp/wifi/v820-qrtr-namespace-classifier/manifest.json")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v821-execns-helper-v125-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "49194d47fc251d3201f6af65ff78909087f4734584383f1d600a5daab29d30da"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v125"
DEFAULT_MATRIX = "servloc:64:1;servnotif:66:74,180;wlfw:69:0,1"
DEPLOY_APPROVAL = "approve v821 deploy execns helper v125 only; no daemon start and no Wi-Fi bring-up"
PROOF_PREFIX = "/tmp/a90-v821-"

FORBIDDEN_ACTIONS = (
    "custom kernel flash, boot image write, or partition write",
    "bootloader handoff",
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
    parser.add_argument("--v820-manifest", type=Path, default=DEFAULT_V820_MANIFEST)
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
    info: dict[str, Any] = {"path": str(path), "exists": path.exists(), "sha256": "", "marker": False, "matrix_option": False}
    if not path.exists():
        return info
    info["sha256"] = sha256_file(path)
    result = subprocess.run(["strings", str(path)], cwd=repo_path("."), text=True, capture_output=True, check=False)
    strings_output = result.stdout if result.returncode == 0 else ""
    info["marker"] = args.helper_marker in strings_output
    info["matrix_option"] = "--qrtr-readback-matrix" in strings_output
    return info


def v820_input(args: argparse.Namespace) -> dict[str, Any]:
    loaded = load_json(args.v820_manifest)
    data = loaded["data"]
    return {
        "file": loaded["file"],
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
        "next_step": data.get("next_step", ""),
    }


def deploy_helper(args: argparse.Namespace, store: EvidenceStore, command: str) -> dict[str, Any]:
    deploy_dir = store.path(f"deploy-v125-{command}")
    cmd = [
        "python3",
        "scripts/revalidation/wifi_execns_helper_v125_deploy_preflight.py",
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
    result = run_host(store, f"v821-deploy-{command}", cmd, timeout)
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


def parse_key_values(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    key_re = re.compile(r"^([A-Za-z0-9_.:-]+)=(.*)$")
    for line in text.splitlines():
        match = key_re.match(line.strip())
        if match:
            keys[match.group(1)] = match.group(2)
    return keys


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def matrix_rows(keys: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    index = 0
    while True:
        prefix = f"wifi_companion_qrtr_readback.case_{index}"
        if f"{prefix}.begin" not in keys and f"{prefix}.service" not in keys:
            break
        rows.append({
            "case": index,
            "label": keys.get(f"{prefix}.label", ""),
            "service": int_value(keys.get(f"{prefix}.service")),
            "instance": int_value(keys.get(f"{prefix}.instance")),
            "socket_rc": int_value(keys.get(f"{prefix}.socket.rc")),
            "socket_family": int_value(keys.get(f"{prefix}.socket_name.family")),
            "new_lookup_rc": int_value(keys.get(f"{prefix}.new_lookup_send.rc")),
            "del_lookup_rc": int_value(keys.get(f"{prefix}.del_lookup_send.rc")),
            "events": int_value(keys.get(f"{prefix}.readback.events")),
            "service_events": int_value(keys.get(f"{prefix}.readback.service_events")),
            "end_of_list": int_value(keys.get(f"{prefix}.readback.end_of_list")),
            "timeout": int_value(keys.get(f"{prefix}.readback.timeout")),
            "qmi_attempted": int_value(keys.get(f"{prefix}.qmi_attempted")),
            "status": keys.get(f"{prefix}.status", ""),
        })
        index += 1
    return rows


def summarize_matrix(helper_payload: str) -> dict[str, Any]:
    keys = parse_key_values(helper_payload)
    rows = matrix_rows(keys)
    by_label: dict[str, Any] = {}
    for row in rows:
        label = str(row["label"] or "unknown")
        item = by_label.setdefault(label, {"cases": 0, "service_events": 0, "timeouts": 0, "end_of_list": 0})
        item["cases"] += 1
        item["service_events"] += int_value(row["service_events"])
        item["timeouts"] += int_value(row["timeout"])
        item["end_of_list"] += int_value(row["end_of_list"])
    return {
        "allowed": int_value(keys.get("wifi_companion_qrtr_readback.allowed")),
        "matrix": keys.get("wifi_companion_qrtr_readback.matrix", ""),
        "case_count": int_value(keys.get("wifi_companion_qrtr_readback.case_count")),
        "send_attempted": int_value(keys.get("wifi_companion_qrtr_readback.send_attempted")),
        "result": keys.get("wifi_companion_qrtr_readback.result", ""),
        "qmi_payload": int_value(keys.get("wifi_companion_qrtr_readback.qmi_payload")),
        "rows": rows,
        "by_label": by_label,
        "total_service_events": sum(int_value(row["service_events"]) for row in rows),
        "total_timeouts": sum(int_value(row["timeout"]) for row in rows),
        "total_qmi_attempted": sum(int_value(row["qmi_attempted"]) for row in rows),
        "lookup_ok": bool(rows) and all(int_value(row["new_lookup_rc"]) == 0 and int_value(row["del_lookup_rc"]) == 0 for row in rows),
        "socket_ok": bool(rows) and all(int_value(row["socket_rc"]) == 0 and int_value(row["socket_family"]) == 42 for row in rows),
    }


def configure_v821(args: argparse.Namespace) -> tuple[Any, Any]:
    v817.configure_base()
    v817.PROOF_PREFIX = PROOF_PREFIX
    original_v735_helper = v817.v735.helper_command
    original_base_helper = v817.base.helper_command

    def helper_command_with_matrix(inner_args: argparse.Namespace) -> list[str]:
        return original_v735_helper(inner_args) + ["--qrtr-readback-matrix", args.qrtr_matrix]

    v817.v735.helper_command = helper_command_with_matrix
    v817.base.helper_command = helper_command_with_matrix
    return original_v735_helper, original_base_helper


def restore_helpers(original_v735_helper: Any, original_base_helper: Any) -> None:
    v817.v735.helper_command = original_v735_helper
    v817.base.helper_command = original_base_helper


def run_live(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    live_store = EvidenceStore(store.path("live-v817-v125-matrix"))
    live_store.mkdir("native")
    live_store.mkdir("host")
    original_v735_helper, original_base_helper = configure_v821(args)
    try:
        live_manifest = v817.build_manifest(args, live_store)
    finally:
        restore_helpers(original_v735_helper, original_base_helper)
    live_store.write_json("manifest.json", live_manifest)
    live_store.write_text("summary.md", v817.render_summary(live_manifest))
    helper_payload = ""
    for step in live_manifest.get("steps", []):
        if step.get("name") == "lower-companion-start-only":
            helper_payload = str(step.get("payload") or "")
            break
    live_manifest["v821_matrix"] = summarize_matrix(helper_payload)
    live_store.write_json("manifest-v821-annotated.json", live_manifest)
    return {
        "manifest": str(live_store.run_dir / "manifest-v821-annotated.json"),
        "decision": live_manifest.get("decision"),
        "pass": live_manifest.get("pass"),
        "live": live_manifest.get("live", {}),
        "matrix": live_manifest["v821_matrix"],
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
                 v820: dict[str, Any],
                 local: dict[str, Any],
                 deploy: dict[str, Any] | None,
                 live: dict[str, Any] | None) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = [
        {
            "name": "v820-route-ready",
            "status": "pass" if v820["pass"] and v820["decision"] == "v820-procfs-absent-af-qrtr-readback-working" else "blocked",
            "detail": v820,
            "next_step": "restore V820 evidence before V821",
        },
        {
            "name": "local-helper-v125",
            "status": "pass" if local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["matrix_option"] else "blocked",
            "detail": local,
            "next_step": "rebuild helper v125 before live matrix",
        },
        {
            "name": "host-only-plan-boundary" if args.command == "plan" else "preflight-live-boundary",
            "status": "pass",
            "detail": "plan has no device command; preflight/run keep HAL/connect/networking blocked",
            "next_step": "continue only inside V821 guardrails",
        },
    ]
    if args.command == "plan":
        return checks
    checks.append({
        "name": "helper-deploy-preflight" if args.command == "preflight" else "helper-deploy-run",
        "status": "pass" if deploy and deploy.get("pass") else "blocked",
        "detail": deploy or {},
        "next_step": "fix helper deploy/preflight before nameservice matrix",
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
        and matrix.get("case_count") == 5
        and matrix.get("qmi_payload") == 0
        and matrix.get("total_qmi_attempted") == 0
        and matrix.get("total_timeouts") == 0
        and matrix.get("socket_ok")
        and matrix.get("lookup_ok")
    )
    checks.extend([
        {
            "name": "v817-window-with-v125",
            "status": "pass" if live and live.get("pass") else "blocked",
            "detail": {"decision": (live or {}).get("decision"), "pass": (live or {}).get("pass"), "manifest": (live or {}).get("manifest")},
            "next_step": "restore V817 lower window before interpreting matrix",
        },
        {
            "name": "guardrails-preserved",
            "status": "pass" if forbidden_ok and matrix.get("qmi_payload") == 0 and matrix.get("total_qmi_attempted") == 0 else "blocked",
            "detail": {"forbidden": forbidden, "matrix": matrix},
            "next_step": "discard run if QMI payload/HAL/connect/network action occurred",
        },
        {
            "name": "nameservice-matrix-complete",
            "status": "pass" if matrix_ok else "blocked",
            "detail": matrix,
            "next_step": "fix helper matrix readback before selecting next blocker",
        },
        {
            "name": "nameservice-publication-result",
            "status": "finding",
            "detail": matrix,
            "next_step": "if any service is visible, route to exact service continuation; otherwise classify why sysmon exists without nameservice publication",
        },
    ])
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], live: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v821-qrtr-nameservice-matrix-plan-ready",
            True,
            "plan-only; helper v125 matrix gate defined without live action",
            "run V821 preflight, then deploy/live matrix if clean",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v821-qrtr-nameservice-matrix-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "resolve blocker before continuing toward Wi-Fi bring-up",
        )
    if args.command == "preflight":
        return (
            "v821-qrtr-nameservice-matrix-preflight-ready",
            True,
            "preflight passed; helper v125 deploy/live matrix remains gated",
            "run V821 live matrix",
        )
    matrix = (live or {}).get("matrix", {})
    service_events = int_value(matrix.get("total_service_events"))
    if service_events:
        return (
            "v821-qrtr-nameservice-publication-visible",
            True,
            f"nameservice matrix observed service_events={service_events} below HAL/connect",
            "classify visible QRTR services before any QMI payload, HAL, scan/connect, or credential step",
        )
    return (
        "v821-qrtr-nameservice-matrix-empty-below-hal",
        True,
        "matrix completed for service-locator, service-notifier, and WLFW candidates, but all service publications stayed empty below HAL/connect",
        "V822 should classify why kernel sysmon/service-locator dmesg appears while AF_QIPCRTR nameservice publication stays empty",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    store.mkdir("host")
    v820 = v820_input(args)
    local = local_helper(args)
    deploy: dict[str, Any] | None = None
    live: dict[str, Any] | None = None
    if args.command == "preflight":
        deploy = deploy_helper(args, store, "preflight")
    elif args.command == "run":
        deploy = deploy_helper(args, store, "run")
        if deploy.get("pass"):
            live = run_live(args, store)
    checks = build_checks(args, v820, local, deploy, live)
    decision, pass_ok, reason, next_step = decide(args, checks, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v821",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v820": v820,
        "local_helper": local,
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "qrtr_matrix": args.qrtr_matrix,
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
        "# V821 QRTR Nameservice Matrix",
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
