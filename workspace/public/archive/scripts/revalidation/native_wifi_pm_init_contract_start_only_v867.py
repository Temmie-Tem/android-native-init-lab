#!/usr/bin/env python3
"""V867 bounded PeripheralManager init-contract start-only proof.

This runs only helper v134's PeripheralManager init-contract mode:
`pm_proxy_helper` oneshot, `pm-service` (`per_mgr`), and property-gated
`pm-proxy` under Android node parity. It does not start mdm_helper, ks, CNSS,
Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import native_wifi_esoc_node_parity_preflight_v855 as v855
import native_wifi_pm_service_property_contract_start_only_v857 as v857
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v867-pm-init-contract-start-only")
LATEST_POINTER = Path("tmp/wifi/latest-v867-pm-init-contract-start-only.txt")
DEFAULT_V855_MANIFEST = Path("tmp/wifi/v855-esoc-node-parity-preflight/manifest.json")
DEFAULT_V860_REPLAY = Path("tmp/wifi/v860-pm-service-property-superset-replay-live/manifest.json")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v865-execns-helper-v134-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "92792fb954de42825d328c047498c5291be803185d9897d22dd734fd9bd77582"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v134"
DEFAULT_RUNTIME_SEC = 10
DEFAULT_MARKER = "/tmp/a90-v867-pm-init-contract.created"
MODE = "wifi-companion-peripheral-manager-init-contract-start-only"
EXPECTED_PER_MGR_DOMAIN = "u:r:vendor_per_mgr:s0"
EXPECTED_PER_PROXY_HELPER_DOMAIN = "u:r:per_proxy_helper:s0"
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
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
    parser.add_argument("--host", "--bridge-host", dest="host", default=v857.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v857.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=v857.DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=v857.DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=v857.DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--runtime-sec", type=int, default=DEFAULT_RUNTIME_SEC)
    parser.add_argument("--marker", default=DEFAULT_MARKER)
    parser.add_argument("--v855-manifest", type=Path, default=DEFAULT_V855_MANIFEST)
    parser.add_argument("--v860-replay-manifest", type=Path, default=DEFAULT_V860_REPLAY)
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-node-materialization", action="store_true")
    parser.add_argument("--allow-node-cleanup", action="store_true")
    parser.add_argument("--allow-pm-init-contract-start-only", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--no-hide-on-busy", dest="hide_on_busy", action="store_false")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def actual_attr_current_by_pid(text: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    lines = text.replace("\0", "\\0").splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("A90_EXECNS_CNSS_PROC_attr_current_BEGIN path=/proc/"):
            continue
        try:
            pid = line.split("path=/proc/", 1)[1].split("/", 1)[0]
        except IndexError:
            continue
        if index + 1 < len(lines):
            attrs[pid] = lines[index + 1].replace("\\0", "").strip()
    return attrs


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
        ("--allow-mountsystem-ro", args.allow_mountsystem_ro),
        ("--allow-selinuxfs-mount", args.allow_selinuxfs_mount),
        ("--allow-node-materialization", args.allow_node_materialization),
        ("--allow-node-cleanup", args.allow_node_cleanup),
        ("--allow-pm-init-contract-start-only", args.allow_pm_init_contract_start_only),
        ("--assume-yes", args.assume_yes),
    ):
        if not enabled:
            missing.append(flag)
    return missing


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
        v857.PROPERTY_ROOT,
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        v857.REAL_LD_CONFIG,
        "--apex-libraries-source",
        v857.REAL_APEX_LIBRARIES,
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


def child_surface(keys: dict[str, str], actual_attrs: dict[str, str], text: str, name: str) -> dict[str, Any]:
    child_prefix = f"wifi_companion_start.child.{name}."
    exec_prefix = f"wifi_hal_composite_child.{name}."
    fd_prefix = f"capture.wifi_hal_composite_{name}.fd_links."
    pid = keys.get(f"wifi_hal_composite_start.child.{name}.pid", "")
    fd_targets = [
        line.strip()
        for line in text.splitlines()
        if fd_prefix in line and ".target=" in line
    ]
    return {
        "pid": pid,
        "observable": keys.get(child_prefix + "observable", ""),
        "exited": keys.get(child_prefix + "exited", ""),
        "exit_code": keys.get(child_prefix + "exit_code", ""),
        "signal": keys.get(child_prefix + "signal", ""),
        "postflight_safe": keys.get(child_prefix + "postflight_safe", ""),
        "selinux_target": keys.get(exec_prefix + "selinux_exec.target_context", ""),
        "selinux_ok": keys.get(exec_prefix + "selinux_exec.ok", ""),
        "selinux_current": keys.get(exec_prefix + "selinux.current", ""),
        "selinux_exec": keys.get(exec_prefix + "selinux.exec", ""),
        "actual_attr_current": actual_attrs.get(pid, ""),
        "ioprio_ok": keys.get(exec_prefix + "ioprio.ok", ""),
        "ioprio_errno": keys.get(exec_prefix + "ioprio.errno", ""),
        "fd_count": keys.get(fd_prefix + "count", ""),
        "fd_socket_count": keys.get(fd_prefix + "socket_count", ""),
        "fd_targets": fd_targets[:64],
    }


def helper_surface(text: str) -> dict[str, Any]:
    keys = parse_keys(text)
    actual_attrs = actual_attr_current_by_pid(text)
    children = {
        name: child_surface(keys, actual_attrs, text, name)
        for name in ("per_proxy_helper", "per_mgr", "per_proxy")
    }
    return {
        "keys": {
            "mode": keys.get("mode", ""),
            "allowed": keys.get("wifi_companion_start.allowed", ""),
            "order": keys.get("wifi_companion_start.order", ""),
            "child_started": keys.get("wifi_companion_start.child_started", ""),
            "result": keys.get("wifi_companion_start.result", ""),
            "reason": keys.get("wifi_companion_start.reason", ""),
            "timed_out": keys.get("wifi_companion_start.timed_out", ""),
            "all_postflight_safe": keys.get("wifi_companion_start.all_postflight_safe", ""),
            "init_contract": keys.get("wifi_companion_start.peripheral_manager.init_contract", ""),
            "property_contract": keys.get("wifi_companion_start.peripheral_manager.property_contract", ""),
            "per_mgr_ioprio_rt4": keys.get("wifi_companion_start.peripheral_manager.per_mgr_ioprio_rt4", ""),
            "per_proxy_property_lifecycle": keys.get("wifi_companion_start.peripheral_manager.per_proxy_property_lifecycle", ""),
            "shutdown_stop_model": keys.get("wifi_companion_start.peripheral_manager.shutdown_stop_model", ""),
            "per_proxy_helper_oneshot": keys.get("wifi_companion_start.peripheral_manager.per_proxy_helper.oneshot", ""),
            "per_mgr_ready": keys.get("wifi_companion_start.peripheral_manager.per_mgr.ready", ""),
            "per_mgr_observable": keys.get("wifi_companion_start.peripheral_manager.per_mgr.observable", ""),
            "per_proxy_start_gate": keys.get("wifi_companion_start.peripheral_manager.per_proxy_start_gate", ""),
            "per_proxy_start_gate_open": keys.get("wifi_companion_start.peripheral_manager.per_proxy_start_gate.open", ""),
            "init_svc_vendor_per_mgr": keys.get("wifi_companion_start.peripheral_manager.init.svc.vendor.per_mgr", ""),
            "per_proxy_ready": keys.get("wifi_companion_start.peripheral_manager.per_proxy.ready", ""),
            "shutdown_stop_vendor_per_proxy": keys.get("wifi_companion_start.peripheral_manager.shutdown_stop.vendor_per_proxy", ""),
            "private_subsys_modem": keys.get("wifi_companion_start.private_node.subsys_modem.exists", ""),
            "private_subsys_esoc0": keys.get("wifi_companion_start.private_node.subsys_esoc0.exists", ""),
            "private_esoc_0": keys.get("wifi_companion_start.private_node.esoc_0.exists", ""),
        },
        "children": children,
        "per_mgr_holds_subsys_modem": any("subsys_modem" in line for line in children["per_mgr"]["fd_targets"]),
        "per_mgr_holds_subsys_esoc0": any("subsys_esoc0" in line for line in children["per_mgr"]["fd_targets"]),
        "per_proxy_helper_holds_subsys": any("subsys_" in line for line in children["per_proxy_helper"]["fd_targets"]),
        "per_proxy_holds_subsys": any("subsys_" in line for line in children["per_proxy"]["fd_targets"]),
        "forbidden_hits": [term for term in FORBIDDEN_HELPER_TERMS if term in text],
        "contains_wifi_hal_start": "wifi_companion_start.wifi_hal=2" in text,
        "contains_scan_connect": "wifi_companion_start.scan_connect_linkup=1" in text,
        "contains_external_ping": "wifi_companion_start.external_ping=1" in text,
    }


def remote_helper_state(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    sha = v857.run_device(args, store, steps, "remote-helper-sha", ["run", args.toybox, "sha256sum", args.helper], timeout=12.0)
    usage = v857.run_device(args, store, steps, "remote-helper-usage", ["run", args.helper], timeout=12.0)
    sha_payload = str(sha.get("payload") or "")
    usage_payload = str(usage.get("payload") or "")
    return {
        "sha_ok": args.helper_sha256 in sha_payload,
        "marker_ok": args.helper_marker in usage_payload,
        "mode_ok": MODE in usage_payload,
        "sha_file": sha.get("file"),
        "usage_file": usage.get("file"),
    }


def post_actor_surface(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    ps = v857.run_device(args, store, steps, "post-ps", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], timeout=20.0)
    net = v857.run_device(args, store, steps, "post-proc-net-dev", ["cat", "/proc/net/dev"], timeout=12.0)
    actor_re = re.compile(r"\b(servicemanager|hwservicemanager|vndservicemanager|pm-service|pm-proxy|pm_proxy_helper|mdm_helper|ks|cnss-daemon|cnss_diag|wificond|supplicant|hostapd)\b")
    wifi_re = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)
    ps_text = str(ps.get("payload") or "")
    net_text = str(net.get("payload") or "")
    ps_file = store.run_dir / str(ps.get("file") or "")
    net_file = store.run_dir / str(net.get("file") or "")
    if ps_file.exists():
        ps_text = ps_file.read_text(encoding="utf-8", errors="replace")
    if net_file.exists():
        net_text = net_file.read_text(encoding="utf-8", errors="replace")
    actors = [line.strip() for line in ps_text.splitlines() if actor_re.search(line)]
    links = [line.strip() for line in net_text.splitlines() if wifi_re.search(line)]
    actor_pids = []
    for line in actors:
        fields = line.split()
        if fields and fields[0].isdigit():
            actor_pids.append(fields[0])
    return {
        "actor_processes": actors[:16],
        "actor_process_count": len(actors),
        "actor_pids": actor_pids[:16],
        "wifi_links": links[:16],
        "wifi_link_count": len(links),
    }


def cleanup_residual_actors(args: argparse.Namespace,
                            store: EvidenceStore,
                            steps: list[dict[str, Any]],
                            surface: dict[str, Any]) -> dict[str, Any]:
    pids = [str(pid) for pid in surface.get("actor_pids", []) if str(pid).isdigit()]
    kill_steps = []
    for pid in pids:
        kill_steps.append(v857.run_device(args, store, steps, f"cleanup-residual-actor-{pid}", ["run", args.toybox, "kill", "-9", pid], timeout=12.0))
    if pids:
        time.sleep(1.0)
    return {
        "attempted": bool(pids),
        "pids": pids,
        "kill_steps": [{"name": step.get("name"), "ok": step.get("ok"), "rc": step.get("rc"), "status": step.get("status"), "file": step.get("file")} for step in kill_steps],
    }


def execute(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    v857.run_device(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    v857.run_device(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    analysis["selinuxfs"] = v857.ensure_selinuxfs(args, store)
    analysis["remote_helper"] = remote_helper_state(args, store, steps)
    v857.run_device(args, store, steps, "node-preflight", v855.shell_cmd(args, v855.preflight_script(args)), timeout=20.0)
    try:
        v857.run_device(args, store, steps, "materialize-android-node-parity", v855.shell_cmd(args, v855.materialize_script(args)), timeout=20.0)
        helper = v857.run_device(args, store, steps, "pm-init-contract-start-only", helper_command(args), timeout=args.runtime_sec + 50.0)
        helper_payload = str(helper.get("payload") or "")
        helper_file = store.run_dir / str(helper.get("file") or "")
        if helper_file.exists():
            helper_payload = helper_file.read_text(encoding="utf-8", errors="replace")
        analysis["helper"] = helper_surface(helper_payload)
    finally:
        v857.run_device(args, store, steps, "cleanup-created-nodes", v855.shell_cmd(args, v855.cleanup_script(args)), timeout=20.0)
    v857.run_device(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    analysis["post_actor_surface_initial"] = post_actor_surface(args, store, steps)
    if int((analysis["post_actor_surface_initial"] or {}).get("actor_process_count") or 0) > 0:
        analysis["residual_actor_cleanup"] = cleanup_residual_actors(args, store, steps, analysis["post_actor_surface_initial"])
        analysis["post_actor_surface"] = post_actor_surface(args, store, steps)
    else:
        analysis["residual_actor_cleanup"] = {"attempted": False, "pids": [], "kill_steps": []}
        analysis["post_actor_surface"] = analysis["post_actor_surface_initial"]
    v857.run_device(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)
    analysis["node"] = v855.analyze(steps)
    return steps, analysis


def decide(args: argparse.Namespace,
           v855_manifest: dict[str, Any],
           v860_replay: dict[str, Any],
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if v855_manifest.get("decision") != "v855-esoc-node-parity-clean":
            return "v867-plan-v855-missing", False, "V855 clean node-parity evidence is missing", "rerun V855 before V867"
        if v860_replay.get("decision") != "v860-property-clean-no-subsys-hold":
            return "v867-plan-v860-missing", False, "V860 property-clean replay evidence is missing", "rerun V860 before V867"
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v867-plan-helper-v134-missing", False, f"local_helper={local}", "build helper v134 before live"
        return "v867-pm-init-contract-plan-ready", True, "plan-only; no device command executed", "run bounded V867 live proof"
    missing = required_flags(args)
    if missing:
        return "v867-pm-init-contract-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun V867 with explicit bounded live flags"
    if v855_manifest.get("decision") != "v855-esoc-node-parity-clean":
        return "v867-v855-node-parity-missing", False, "V855 clean node-parity evidence is missing or stale", "rerun V855 before V867"
    if v860_replay.get("decision") != "v860-property-clean-no-subsys-hold":
        return "v867-v860-property-clean-missing", False, "V860 property-clean replay evidence is missing", "rerun V860 before V867"
    if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
        return "v867-helper-v134-local-missing", False, f"local_helper={local}", "rebuild helper v134 before live"
    failed_steps = []
    for step in steps:
        if step.get("ok"):
            continue
        if step.get("name") == "remote-helper-usage" and args.helper_marker in str(step.get("payload") or ""):
            continue
        if str(step.get("name") or "").startswith("cleanup-residual-actor-"):
            continue
        failed_steps.append(step["name"])
    if failed_steps:
        return "v867-step-failed", False, f"failed_steps={failed_steps}", "inspect V867 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v867-helper-v134-remote-mismatch", False, f"remote={remote}", "redeploy helper v134 before live proof"
    selinuxfs = analysis.get("selinuxfs") or {}
    if not selinuxfs.get("pass"):
        return "v867-selinuxfs-mount-missing", False, f"selinuxfs={selinuxfs}", "mount SELinuxfs before PM init-contract proof"
    node = analysis.get("node") or {}
    if not ((node.get("materialize") or {}).get("all_target_nodes_accounted")):
        return "v867-node-materialization-failed", False, f"node={node}", "repair node materialization before retry"
    if not ((node.get("cleanup") or {}).get("removed_all_created")):
        return "v867-node-cleanup-review", False, f"node={node}", "cleanup V867 nodes manually before continuing"
    post_surface = analysis.get("post_actor_surface") or {}
    if int(post_surface.get("actor_process_count") or 0) > 0:
        return "v867-residual-actor-cleanup-required", False, f"post_actor_surface={post_surface}", "stop and clean residual PM actors before retry"
    helper = analysis.get("helper") or {}
    if helper.get("forbidden_hits"):
        return "v867-forbidden-surface-detected", False, f"forbidden={helper.get('forbidden_hits')}", "stop and audit helper mode before retry"
    keys = helper.get("keys") or {}
    if keys.get("mode") != MODE or keys.get("allowed") != "1":
        return "v867-helper-mode-not-executed", False, f"keys={keys}", "fix helper v134 mode/allow flags before retry"
    required_key_values = {
        "init_contract": "1",
        "per_mgr_ioprio_rt4": "1",
        "per_proxy_property_lifecycle": "1",
        "shutdown_stop_model": "1",
        "per_proxy_helper_oneshot": "1",
    }
    missing_contract = {key: value for key, value in required_key_values.items() if keys.get(key) != value}
    if missing_contract:
        return "v867-init-contract-marker-gap", False, f"missing_contract={missing_contract} keys={keys}", "repair helper v134 init-contract markers"
    children = helper.get("children") or {}
    per_mgr = children.get("per_mgr") or {}
    per_proxy_helper = children.get("per_proxy_helper") or {}
    cleanup = analysis.get("residual_actor_cleanup") or {}
    cleanup_suffix = " cleanup rescue was used;" if cleanup.get("attempted") else ""
    if per_proxy_helper.get("selinux_target") != EXPECTED_PER_PROXY_HELPER_DOMAIN:
        return "v867-per-proxy-helper-target-gap", True, f"children={children}", "classify per_proxy_helper SELinux file-context/domain before retry"
    if per_mgr.get("ioprio_ok") != "1":
        return "v867-per-mgr-ioprio-gap", True, f"per_mgr={per_mgr}", "classify whether native privilege can apply Android ioprio rt 4"
    if keys.get("per_mgr_observable") != "1":
        return "v867-per-mgr-not-observable", True, f"keys={keys} children={children}", "classify pm-service startup/runtime exit before mdm_helper"
    if per_mgr.get("actual_attr_current") != EXPECTED_PER_MGR_DOMAIN:
        return (
            "v867-init-contract-current-kernel-no-subsys-hold",
            True,
            f"init-contract markers passed;{cleanup_suffix} per_mgr runtime domain still differs; children={children}",
            "classify SELinux transition semantics and helper cleanup timing before mdm_helper/ks",
        )
    if helper.get("per_mgr_holds_subsys_modem") and helper.get("per_mgr_holds_subsys_esoc0"):
        return (
            "v867-pm-init-contract-subsys-hold-confirmed",
            True,
            "PM init-contract produced both target subsystem fd holds",
            "classify mdm3 movement and consider PM-gated mdm_helper/ks start-only",
        )
    return (
        "v867-pm-init-contract-no-subsys-hold",
        True,
        f"PM init-contract executed and cleaned up, but target subsystem fd hold not proven; helper={helper}",
        "classify remaining PeripheralManager input/lifetime gap before mdm_helper/ks",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V867 PeripheralManager Init Contract Start-Only",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{manifest['helper_marker']}`",
        f"- helper_sha256: `{manifest['helper_sha256']}`",
        f"- pm_init_contract_start_only_executed: `{manifest['pm_init_contract_start_only_executed']}`",
        f"- mdm_helper_start_executed: `{manifest['mdm_helper_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Analysis",
        "",
        markdown_table(["section", "value"], analysis_rows) if analysis_rows else "- none",
        "",
        "## Steps",
        "",
        markdown_table(["name", "status", "rc", "duration_sec", "file"], step_rows) if step_rows else "- none",
        "",
        "## Guardrails",
        "",
        "- No `mdm_helper` or `ks` start.",
        "- No CNSS, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "- No raw eSoC ioctl, GPIO/sysfs/debugfs write, subsystem state write, module load/unload, boot image write, or partition write.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v855_manifest = load_json(args.v855_manifest)
    v860_replay = load_json(args.v860_replay_manifest)
    local = local_helper_info(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    if args.command == "run" and not required_flags(args):
        steps, analysis = execute(args, store)
    decision, pass_ok, reason, next_step = decide(args, v855_manifest, v860_replay, local, steps, analysis)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "v855_manifest": {"path": str(repo_path(args.v855_manifest)), "decision": v855_manifest.get("decision"), "pass": bool(v855_manifest.get("pass"))},
        "v860_replay_manifest": {"path": str(repo_path(args.v860_replay_manifest)), "decision": v860_replay.get("decision"), "pass": bool(v860_replay.get("pass"))},
        "local_helper": local,
        "helper": args.helper,
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "mode": MODE,
        "runtime_sec": args.runtime_sec,
        "steps": steps,
        "analysis": analysis,
        "pm_init_contract_start_only_executed": args.command == "run" and bool(analysis.get("helper")),
        "mdm_helper_start_executed": False,
        "ks_start_executed": False,
        "cnss_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_or_partition_write_executed": False,
        "module_load_unload_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    LATEST_POINTER.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"pm_init_contract_start_only_executed: {manifest['pm_init_contract_start_only_executed']}")
    print(f"mdm_helper_start_executed: {manifest['mdm_helper_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    print(f"summary: {store.run_dir / 'summary.md'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
