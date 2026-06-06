#!/usr/bin/env python3
"""V857 bounded pm-service property-contract start-only proof.

V856 proved that native can start PeripheralManager under Android node parity
but does not reproduce Android subsystem fd holds. V857 permits only the
observed PeripheralManager shutdown-critical-list property contract below
`mdm_helper`, `ks`, Wi-Fi HAL, scan/connect, DHCP/routes, and external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import native_wifi_esoc_node_parity_preflight_v855 as v855
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v857-pm-service-property-contract-start-only")
LATEST_POINTER = Path("tmp/wifi/latest-v857-pm-service-property-contract-start-only.txt")
DEFAULT_V855_MANIFEST = Path("tmp/wifi/v855-esoc-node-parity-preflight/manifest.json")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 90.0
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v857-execns-helper-v132-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "a167500bd43f56a99da7e3644a8b240360de571aea5edc76b8afaa5215b1f5c7"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v132"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_DEVICE_IP = "192.168.7.2"
DEFAULT_RUNTIME_SEC = 8
DEFAULT_MARKER = "/tmp/a90-v857-pm-property-contract.created"
PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v535/dev/__properties__"
REAL_LD_CONFIG = "/cache/bin/a90_real_ld.config.txt"
REAL_APEX_LIBRARIES = "/cache/bin/a90_real_apex.libraries.config.txt"
MODE = "wifi-companion-peripheral-manager-property-contract-start-only"
DEPLOY_APPROVAL = (
    "approve v857 deploy execns helper v132 only; "
    "no mdm_helper, no Wi-Fi HAL start and no Wi-Fi bring-up"
)
SELINUXFS_APPROVAL = "approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up"

KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
PROP_REQ_RE = re.compile(
    r"^wifi_hal_composite_start\.property_service_shim\.request\.(\d+)\.(cmd|name|value|allowed|result)=(.*)$"
)
SECRET_RE = re.compile(r"(made by|creator: made by) [^\r\n]+", re.IGNORECASE)
FORBIDDEN_HELPER_TERMS = (
    "wifi_companion_start.mdm_helper=1",
    "wifi_hal_composite_start.child.mdm_helper",
    "wifi_hal_composite_child.mdm_helper",
    "wifi_hal_composite_start.child.wifi_hal",
    "wifi_hal_composite_start.child.wificond",
    "scan_connect_linkup=1",
    "external_ping=1",
    "qcwlanstate_write=1",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--runtime-sec", type=int, default=DEFAULT_RUNTIME_SEC)
    parser.add_argument("--marker", default=DEFAULT_MARKER)
    parser.add_argument("--v855-manifest", type=Path, default=DEFAULT_V855_MANIFEST)
    parser.add_argument("--transfer-method", choices=("auto", "ncm", "serial"), default="auto")
    parser.add_argument("--allow-helper-deploy", action="store_true")
    parser.add_argument("--allow-netservice-start", action="store_true")
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-node-materialization", action="store_true")
    parser.add_argument("--allow-node-cleanup", action="store_true")
    parser.add_argument("--allow-pm-service-start-only", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--no-hide-on-busy", dest="hide_on_busy", action="store_false")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def redact(text: str) -> str:
    return SECRET_RE.sub(r"\1 [redacted]", v855.ANSI_RE.sub("", text))


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def run_host(store: EvidenceStore, name: str, command: list[str], timeout: float) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    output = redact(result.stdout)
    rel = f"host/{safe_name(name)}.txt"
    store.write_text(rel, output.rstrip() + "\n")
    return {
        "name": name,
        "command": " ".join(command),
        "rc": result.returncode,
        "ok": result.returncode == 0,
        "file": rel,
        "output": output[:4096] + ("\n[truncated]\n" if len(output) > 4096 else ""),
    }


def run_device(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    command: list[str],
    timeout: float | None = None,
) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    if args.hide_on_busy and (capture.status == "busy" or "[busy]" in payload):
        run_capture(args, f"{name}-hide-on-busy", ["hide"], timeout=min(args.timeout, 8.0))
        capture = run_capture(args, name, command, timeout=timeout or args.timeout)
        payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    payload = redact(payload)
    item = {
        "name": name,
        "command": " ".join(command[:4]) + (" ..." if len(command) > 4 else ""),
        "ok": capture.ok,
        "rc": capture.rc,
        "status": capture.status,
        "duration_sec": round(capture.duration_sec, 3),
        "error": redact(capture.error),
        "payload": payload[:8192] + ("\n[truncated]\n" if len(payload) > 8192 else ""),
        "file": f"native/{safe_name(name)}.txt",
    }
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def local_helper_info(args: argparse.Namespace) -> dict[str, Any]:
    path = repo_path(args.local_helper)
    info: dict[str, Any] = {"path": str(path), "exists": path.exists(), "sha256": "", "marker": False, "mode": False}
    if not path.exists():
        return info
    info["sha256"] = sha256_file(path)
    strings = subprocess.run(
        ["strings", str(path)],
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=30,
    ).stdout
    info["marker"] = args.helper_marker in strings
    info["mode"] = MODE in strings
    return info


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    for flag, enabled in (
        ("--allow-helper-deploy", args.allow_helper_deploy),
        ("--allow-mountsystem-ro", args.allow_mountsystem_ro),
        ("--allow-selinuxfs-mount", args.allow_selinuxfs_mount),
        ("--allow-node-materialization", args.allow_node_materialization),
        ("--allow-node-cleanup", args.allow_node_cleanup),
        ("--allow-pm-service-start-only", args.allow_pm_service_start_only),
        ("--assume-yes", args.assume_yes),
    ):
        if not enabled:
            missing.append(flag)
    return missing


def deploy_helper(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    deploy_dir = store.path("deploy-v132")
    command = [
        sys.executable,
        str(repo_path("scripts/revalidation/wifi_execns_helper_v132_deploy_preflight.py")),
        "--out-dir",
        str(deploy_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--local-helper",
        str(args.local_helper),
        "--remote-helper",
        args.helper,
        "--helper-sha256",
        args.helper_sha256,
        "--toybox",
        args.toybox,
        "--device-ip",
        args.device_ip,
        "--transfer-method",
        args.transfer_method,
        "--approval-phrase",
        DEPLOY_APPROVAL,
        "--apply",
        "--assume-yes",
        "run",
    ]
    result = run_host(store, "deploy-helper-v132", command, timeout=420.0)
    manifest_path = deploy_dir / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}
    return {
        "result": result,
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": bool(manifest.get("pass")),
        "device_mutations": bool(manifest.get("device_mutations")),
    }


def ensure_selinuxfs(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    selinux_dir = store.path("v401-selinuxfs-mount")
    command = [
        sys.executable,
        str(repo_path("scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py")),
        "--out-dir",
        str(selinux_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--approval-phrase",
        SELINUXFS_APPROVAL,
        "--apply",
        "--assume-yes",
        "run",
    ]
    result = run_host(store, "v401-selinuxfs-mount", command, timeout=120.0)
    manifest_path = selinux_dir / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}
    return {
        "result": result,
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": bool(manifest.get("pass")),
        "device_mutations": bool(manifest.get("device_mutations")),
    }


def maybe_start_netservice(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    status = run_device(args, store, steps, "netservice-status-before-deploy", ["netservice", "status"], timeout=10.0)
    if "ncm0=absent" not in status.get("payload", ""):
        return {"started": False, "reason": "already-present"}
    if not args.allow_netservice_start:
        return {"started": False, "reason": "flag-not-set"}
    start = run_device(args, store, steps, "netservice-start-for-deploy", ["netservice", "start"], timeout=20.0)
    ping_results: list[dict[str, Any]] = []
    for index in range(8):
        result = run_host(
            store,
            f"ncm-ping-after-start-{index + 1}",
            ["ping", "-c", "1", "-W", "1", args.device_ip],
            timeout=3,
        )
        ping_results.append({"ok": result["ok"], "file": result["file"]})
        if result["ok"]:
            break
    return {"started": bool(start.get("ok")), "reason": "start-attempted", "step": start["file"], "ping_results": ping_results}


def helper_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        MODE,
        "--property-root",
        PROPERTY_ROOT,
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        REAL_LD_CONFIG,
        "--apex-libraries-source",
        REAL_APEX_LIBRARIES,
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--null-device-mode",
        "dev-null",
        "--data-wifi-mode",
        "private-empty",
        "--android-selinux-context-mode",
        "service-defaults",
        "--timeout-sec",
        str(args.runtime_sec),
        "--allow-wifi-companion-start-only",
        "--allow-service-manager-start-only",
    ]


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def helper_surface(text: str) -> dict[str, Any]:
    keys = parse_keys(text)
    property_requests: dict[str, dict[str, str]] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = PROP_REQ_RE.match(raw_line.strip())
        if match:
            property_requests.setdefault(match.group(1), {})[match.group(2)] = match.group(3)
    property_request_list = [
        {"index": index, **value}
        for index, value in sorted(property_requests.items(), key=lambda item: int(item[0]))
    ]
    shutdown_critical_requests = [
        item
        for item in property_request_list
        if item.get("name") == "vendor.peripheral.shutdown_critical_list"
    ]
    per_mgr_fd_targets = [
        line.strip()
        for line in text.splitlines()
        if "capture.wifi_hal_composite_per_mgr.fd_links." in line and ".target=" in line
    ]
    per_proxy_fd_targets = [
        line.strip()
        for line in text.splitlines()
        if "capture.wifi_hal_composite_per_proxy.fd_links." in line and ".target=" in line
    ]
    forbidden_hits = [term for term in FORBIDDEN_HELPER_TERMS if term in text and term not in {MODE}]
    return {
        "keys": {
            "mode": keys.get("mode", ""),
            "allowed": keys.get("wifi_companion_start.allowed", ""),
            "order": keys.get("wifi_companion_start.order", ""),
            "peripheral_manager_enabled": keys.get("wifi_companion_start.peripheral_manager.enabled", ""),
            "property_contract": keys.get("wifi_companion_start.peripheral_manager.property_contract", ""),
            "service_manager_started": keys.get("wifi_companion_start.service_manager_started", ""),
            "property_allow_peripheral_shutdown_list": keys.get(
                "wifi_hal_composite_start.property_service_shim.allow_peripheral_shutdown_list",
                "",
            ),
            "child_started": keys.get("wifi_companion_start.child_started", ""),
            "result": keys.get("wifi_companion_start.result", ""),
            "reason": keys.get("wifi_companion_start.reason", ""),
            "timed_out": keys.get("wifi_companion_start.timed_out", ""),
            "all_postflight_safe": keys.get("wifi_companion_start.all_postflight_safe", ""),
            "private_subsys_modem": keys.get("wifi_companion_start.private_node.subsys_modem.exists", ""),
            "private_subsys_esoc0": keys.get("wifi_companion_start.private_node.subsys_esoc0.exists", ""),
            "private_esoc_0": keys.get("wifi_companion_start.private_node.esoc_0.exists", ""),
            "per_mgr_ready": keys.get("wifi_companion_start.peripheral_manager.per_mgr.ready", ""),
            "per_mgr_observable": keys.get("wifi_companion_start.peripheral_manager.per_mgr.observable", ""),
            "per_mgr_fd_summary": keys.get("wifi_companion_start.peripheral_manager.per_mgr.fd_summary_captured", ""),
            "per_proxy_ready": keys.get("wifi_companion_start.peripheral_manager.per_proxy.ready", ""),
            "per_proxy_observable": keys.get("wifi_companion_start.peripheral_manager.per_proxy.observable", ""),
            "per_proxy_fd_summary": keys.get("wifi_companion_start.peripheral_manager.per_proxy.fd_summary_captured", ""),
        },
        "per_mgr_fd_targets": per_mgr_fd_targets[:64],
        "per_proxy_fd_targets": per_proxy_fd_targets[:64],
        "per_mgr_holds_subsys_modem": any("subsys_modem" in line for line in per_mgr_fd_targets),
        "per_mgr_holds_subsys_esoc0": any("subsys_esoc0" in line for line in per_mgr_fd_targets),
        "per_proxy_holds_subsys": any("subsys_" in line for line in per_proxy_fd_targets),
        "property_requests": property_request_list[:32],
        "shutdown_critical_requests": shutdown_critical_requests[:16],
        "shutdown_critical_allowed": any(item.get("allowed") == "1" for item in shutdown_critical_requests),
        "forbidden_hits": forbidden_hits,
        "contains_wifi_hal_start": "wifi_companion_start.wifi_hal=2" in text,
        "contains_scan_connect": "wifi_companion_start.scan_connect_linkup=1" in text,
        "contains_external_ping": "wifi_companion_start.external_ping=1" in text,
    }


def plan_steps() -> list[dict[str, Any]]:
    return [
        {"name": "v855-manifest-check", "mutates": False},
        {"name": "mountsystem-ro", "mutates": True},
        {"name": "selinuxfs-mount", "mutates": True},
        {"name": "helper-v132-deploy", "mutates": True},
        {"name": "global-node-materialization", "mutates": True},
        {"name": "pm-service-property-contract-start-only", "mutates": True},
        {"name": "node-cleanup", "mutates": True},
        {"name": "postflight-health", "mutates": False},
    ]


def execute(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    deploy: dict[str, Any] = {}
    selinuxfs: dict[str, Any] = {}
    helper_live: dict[str, Any] = {}
    node_cleanup_done = False

    run_device(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    run_device(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    maybe_start_netservice(args, store, steps)
    run_device(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    selinuxfs = ensure_selinuxfs(args, store)
    deploy = deploy_helper(args, store)
    run_device(args, store, steps, "helper-usage-after-deploy", ["run", args.helper], timeout=12.0)
    run_device(args, store, steps, "node-preflight", v855.shell_cmd(args, v855.preflight_script(args)), timeout=20.0)
    try:
        run_device(args, store, steps, "materialize-android-node-parity", v855.shell_cmd(args, v855.materialize_script(args)), timeout=20.0)
        helper = run_device(args, store, steps, "pm-service-property-contract-start-only", helper_command(args), timeout=args.runtime_sec + 45.0)
        helper_payload = str(helper.get("payload") or "")
        helper_file = store.run_dir / str(helper.get("file") or "")
        if helper_file.exists():
            helper_payload = helper_file.read_text(encoding="utf-8", errors="replace")
        helper_live = helper_surface(helper_payload)
    finally:
        run_device(args, store, steps, "cleanup-created-nodes", v855.shell_cmd(args, v855.cleanup_script(args)), timeout=20.0)
        node_cleanup_done = True
    run_device(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    run_device(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)

    analysis = {
        "selinuxfs": selinuxfs,
        "deploy": deploy,
        "node": v855.analyze(steps),
        "helper": helper_live,
        "node_cleanup_done": node_cleanup_done,
    }
    return steps, analysis, deploy


def decide(args: argparse.Namespace,
           v855_manifest: dict[str, Any],
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if v855_manifest.get("decision") != "v855-esoc-node-parity-clean":
            return "v857-plan-v855-missing", False, "V855 clean node-parity evidence is missing", "rerun V855 before V857"
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v857-plan-helper-v132-missing", False, f"local_helper={local}", "build helper v132 before V857 live"
        return "v857-pm-service-property-contract-plan-ready", True, "plan-only; no device command executed", "run bounded V857 live proof"
    missing = required_flags(args)
    if missing:
        return "v857-pm-service-property-contract-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun V857 with explicit bounded live flags"
    if v855_manifest.get("decision") != "v855-esoc-node-parity-clean":
        return "v857-v855-node-parity-missing", False, "V855 clean node-parity evidence is missing or stale", "rerun V855 before V857"
    if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
        return "v857-helper-v132-local-missing", False, f"local_helper={local}", "rebuild helper v132 before deploy"
    failed_steps = []
    for step in steps:
        if step.get("ok"):
            continue
        if step.get("name") == "netservice-start-for-deploy":
            continue
        if step.get("name") == "helper-usage-after-deploy" and args.helper_marker in str(step.get("payload") or ""):
            continue
        failed_steps.append(step["name"])
    if failed_steps:
        return "v857-step-failed", False, f"failed_steps={failed_steps}", "inspect V857 evidence before retry"
    deploy = analysis.get("deploy") or {}
    if not deploy.get("pass"):
        return "v857-helper-deploy-failed", False, f"deploy={deploy}", "repair helper deployment before pm-service proof"
    selinuxfs = analysis.get("selinuxfs") or {}
    if not selinuxfs.get("pass"):
        return "v857-selinuxfs-mount-missing", False, f"selinuxfs={selinuxfs}", "mount SELinuxfs before pm-service proof"
    node = analysis.get("node") or {}
    materialize = node.get("materialize") or {}
    cleanup = node.get("cleanup") or {}
    if not materialize.get("all_target_nodes_accounted"):
        return "v857-node-materialization-failed", False, f"materialize={materialize}", "repair node materialization before pm-service proof"
    if not cleanup.get("removed_all_created"):
        return "v857-node-cleanup-review", False, f"cleanup={cleanup}", "cleanup V857 nodes manually before continuing"
    helper = analysis.get("helper") or {}
    keys = helper.get("keys") or {}
    if helper.get("forbidden_hits"):
        return "v857-forbidden-surface-detected", False, f"forbidden={helper.get('forbidden_hits')}", "stop and audit helper mode before retry"
    if keys.get("mode") != MODE or keys.get("allowed") != "1":
        return "v857-helper-mode-not-executed", False, f"keys={keys}", "fix helper v132 mode/allow flags before retry"
    if keys.get("order") != "servicemanager,hwservicemanager,vndservicemanager,per_mgr,per_proxy":
        return "v857-helper-order-gap", False, f"keys={keys}", "fix helper v132 pm-service-only order"
    if not (keys.get("private_subsys_modem") == "1" and keys.get("private_subsys_esoc0") == "1"):
        return "v857-private-node-parity-gap", False, f"keys={keys}", "fix helper private /dev node materialization"
    if keys.get("property_contract") != "1" or keys.get("property_allow_peripheral_shutdown_list") != "1":
        return "v857-property-contract-not-enabled", False, f"keys={keys}", "fix helper v132 property contract mode"
    if not helper.get("shutdown_critical_allowed"):
        return (
            "v857-shutdown-critical-list-not-observed",
            True,
            f"helper={helper}",
            "classify whether pm-service avoided the shutdown-critical property path before mdm_helper",
        )
    if keys.get("per_mgr_observable") != "1" or keys.get("per_mgr_fd_summary") != "1":
        return "v857-pm-service-not-observable", True, f"keys={keys}", "classify pm-service startup/runtime exit before mdm_helper"
    if helper.get("per_mgr_holds_subsys_modem") and helper.get("per_mgr_holds_subsys_esoc0"):
        return (
            "v857-pm-service-subsys-hold-confirmed",
            True,
            "pm-service was observable and held both Android-equivalent subsystem nodes under private property contract",
            "plan V858 mdm_helper + ks eSoC contract replay after pm-service property contract",
        )
    return (
        "v857-pm-property-contract-no-subsys-hold",
        True,
        f"shutdown-critical-list property contract replayed, but target subsystem fd hold not proven; helper={helper}",
        "classify remaining pm-service init/property/service inputs before mdm_helper replay",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    check_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V857 pm-service Property Contract Start-Only",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{manifest['helper_marker']}`",
        f"- helper_sha256: `{manifest['helper_sha256']}`",
        f"- mode: `{MODE}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- helper_deploy_executed: `{manifest['helper_deploy_executed']}`",
        f"- pm_service_start_only_executed: `{manifest['pm_service_start_only_executed']}`",
        f"- mdm_helper_start_executed: `{manifest['mdm_helper_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Plan",
        "",
        markdown_table(["name", "mutates"], [[step["name"], step["mutates"]] for step in manifest.get("plan_steps", [])]),
        "",
        "## Analysis",
        "",
        markdown_table(["section", "value"], check_rows) if check_rows else "- none",
        "",
        "## Steps",
        "",
        markdown_table(["name", "status", "rc", "duration_sec", "file"], step_rows) if step_rows else "- none",
        "",
        "## Guardrails",
        "",
        "- No `mdm_helper` or `ks` start.",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "- No raw eSoC ioctl, GPIO/sysfs/debugfs write, subsystem state write, module load/unload, boot image write, or partition write.",
        "- Only V855-equivalent node materialization/cleanup plus helper deploy and bounded `pm-service`/`pm-proxy` start-only are in scope.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v855_manifest = load_json(args.v855_manifest)
    local = local_helper_info(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    deploy: dict[str, Any] = {}

    if args.command == "run" and not required_flags(args):
        steps, analysis, deploy = execute(args, store)
    decision, pass_ok, reason, next_step = decide(args, v855_manifest, local, steps, analysis)
    device_commands = args.command == "run" and bool(steps)
    device_mutations = device_commands
    deploy_executed = bool((deploy.get("result") or {}).get("ok") or deploy.get("device_mutations"))
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "v855_manifest": {
            "path": str(repo_path(args.v855_manifest)),
            "decision": v855_manifest.get("decision"),
            "pass": bool(v855_manifest.get("pass")),
        },
        "local_helper": local,
        "helper": args.helper,
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "plan_steps": plan_steps(),
        "steps": steps,
        "analysis": analysis,
        "required_flags_missing": required_flags(args),
        "device_commands_executed": device_commands,
        "device_mutations": device_mutations,
        "helper_deploy_executed": deploy_executed,
        "mountsystem_ro_executed": device_commands,
        "selinuxfs_mount_executed": bool((analysis.get("selinuxfs") or {}).get("device_mutations")),
        "node_materialization_executed": device_commands,
        "node_cleanup_executed": device_commands,
        "pm_service_start_only_executed": device_commands,
        "pm_proxy_start_only_executed": device_commands,
        "mdm_helper_start_executed": False,
        "ks_start_executed": False,
        "raw_esoc_ioctl_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "sysfs_write_executed": False,
        "debugfs_write_executed": False,
        "gpio_write_executed": False,
        "boot_or_partition_write_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"pm_service_start_only_executed: {manifest['pm_service_start_only_executed']}")
    print(f"mdm_helper_start_executed: {manifest['mdm_helper_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
