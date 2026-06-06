#!/usr/bin/env python3
"""V861 pm-service domain-parity lifetime proof.

V860 removed the current private-property denials, but `pm-service` still did
not hold `/dev/subsys_esoc0` or `/dev/subsys_modem`.  V861 deploys helper v133,
which adds Android default SELinux exec contexts for `/vendor/bin/pm-service`
and `/vendor/bin/pm-proxy`, then reruns only the bounded
`pm-service`/`pm-proxy` start-only path under Android node parity.

It does not start `mdm_helper`/`ks`, start Wi-Fi HAL, scan/connect, use
credentials, run DHCP/routes, or ping externally.
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

import native_wifi_pm_service_property_contract_start_only_v857 as v857
import native_wifi_pm_service_property_superset_replay_v860 as v860
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v861-pm-service-domain-parity-live")
LATEST_POINTER = Path("tmp/wifi/latest-v861-pm-service-domain-parity.txt")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v861-execns-helper-v133-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "ff7039d41f7d4b0c17c480297a58b33cac49aeceaba33a865a347d300fc2fb15"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v133"
DEFAULT_V860_REPLAY = Path("tmp/wifi/v860-pm-service-property-superset-replay-live/manifest.json")
DEPLOY_APPROVAL = (
    "approve v861 deploy execns helper v133 only; "
    "no mdm_helper, no Wi-Fi HAL start and no Wi-Fi bring-up"
)
EXPECTED_DOMAIN = "u:r:vendor_per_mgr:s0"
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")


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
    parser.add_argument("--helper", default=v857.DEFAULT_HELPER)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--device-ip", default=v857.DEFAULT_DEVICE_IP)
    parser.add_argument("--runtime-sec", type=int, default=v857.DEFAULT_RUNTIME_SEC)
    parser.add_argument("--marker", default="/tmp/a90-v861-pm-domain-parity.created")
    parser.add_argument("--v855-manifest", type=Path, default=v857.DEFAULT_V855_MANIFEST)
    parser.add_argument("--v860-replay-manifest", type=Path, default=DEFAULT_V860_REPLAY)
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


def load_json(path: Path) -> dict[str, Any]:
    return v857.load_json(path)


def safe_name(value: str) -> str:
    return v857.safe_name(value)


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
        if index + 1 >= len(lines):
            continue
        attrs[pid] = lines[index + 1].replace("\\0", "").strip()
    return attrs


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
    output = v857.redact(result.stdout)
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
    info["mode"] = v857.MODE in strings
    info["vendor_per_mgr_mapping"] = EXPECTED_DOMAIN in strings
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
    deploy_dir = store.path("deploy-v133")
    command = [
        sys.executable,
        str(repo_path("scripts/revalidation/wifi_execns_helper_v133_deploy_preflight.py")),
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
    result = run_host(store, "deploy-helper-v133", command, timeout=420.0)
    manifest_path = deploy_dir / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}
    return {
        "result": result,
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": bool(manifest.get("pass")),
        "device_mutations": bool(manifest.get("device_mutations")),
    }


def helper_command(args: argparse.Namespace) -> list[str]:
    command = v857.helper_command(args)
    return command


def surface_from_payload(text: str) -> dict[str, Any]:
    base = v857.helper_surface(text)
    keys = parse_keys(text)
    actual_attrs = actual_attr_current_by_pid(text)
    children: dict[str, dict[str, Any]] = {}
    for name in ("vndservicemanager", "per_mgr", "per_proxy"):
        child_prefix = f"wifi_companion_start.child.{name}."
        exec_prefix = f"wifi_hal_composite_child.{name}."
        fd_prefix = f"capture.wifi_hal_composite_{name}.fd_links."
        pid = keys.get(f"wifi_hal_composite_start.child.{name}.pid", "")
        children[name] = {
            "pid": pid,
            "observable": keys.get(child_prefix + "observable", ""),
            "exited": keys.get(child_prefix + "exited", ""),
            "exit_code": keys.get(child_prefix + "exit_code", ""),
            "signal": keys.get(child_prefix + "signal", ""),
            "postflight_safe": keys.get(child_prefix + "postflight_safe", ""),
            "selinux_target": keys.get(exec_prefix + "selinux_exec.target_context", ""),
            "selinux_ok": keys.get(exec_prefix + "selinux_exec.ok", ""),
            "selinux_skipped": keys.get(exec_prefix + "selinux_exec.skipped", ""),
            "selinux_skip_reason": keys.get(exec_prefix + "selinux_exec.reason", ""),
            "selinux_current": keys.get(exec_prefix + "selinux.current", ""),
            "selinux_exec": keys.get(exec_prefix + "selinux.exec", ""),
            "actual_attr_current": actual_attrs.get(pid, ""),
            "fd_count": keys.get(fd_prefix + "count", ""),
            "fd_socket_count": keys.get(fd_prefix + "socket_count", ""),
        }
    base["children"] = children
    base["property_denials"] = v860.v859.parse_denials(text)
    base["per_mgr_exec_target_match"] = children["per_mgr"]["selinux_target"] == EXPECTED_DOMAIN and children["per_mgr"]["selinux_ok"] == "1"
    base["per_proxy_exec_target_match"] = children["per_proxy"]["selinux_target"] == EXPECTED_DOMAIN and children["per_proxy"]["selinux_ok"] == "1"
    base["per_mgr_actual_domain_match"] = children["per_mgr"]["actual_attr_current"] == EXPECTED_DOMAIN
    base["per_proxy_actual_domain_match"] = children["per_proxy"]["actual_attr_current"] == EXPECTED_DOMAIN
    return base


def execute(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    v857.run_device(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    if args.allow_netservice_start:
        v857.maybe_start_netservice(args, store, steps)
    v857.run_device(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    selinuxfs = v857.ensure_selinuxfs(args, store)
    deploy = deploy_helper(args, store)
    v857.run_device(args, store, steps, "helper-usage-after-deploy", ["run", args.helper], timeout=12.0)
    v857.run_device(args, store, steps, "node-preflight", v857.v855.shell_cmd(args, v857.v855.preflight_script(args)), timeout=20.0)
    try:
        v857.run_device(args, store, steps, "materialize-android-node-parity", v857.v855.shell_cmd(args, v857.v855.materialize_script(args)), timeout=20.0)
        helper = v857.run_device(args, store, steps, "pm-service-domain-parity-start-only", helper_command(args), timeout=args.runtime_sec + 45.0)
        helper_payload = str(helper.get("payload") or "")
        helper_file = store.run_dir / str(helper.get("file") or "")
        if helper_file.exists():
            helper_payload = helper_file.read_text(encoding="utf-8", errors="replace")
        analysis["helper"] = surface_from_payload(helper_payload)
    finally:
        v857.run_device(args, store, steps, "cleanup-created-nodes", v857.v855.shell_cmd(args, v857.v855.cleanup_script(args)), timeout=20.0)
    v857.run_device(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)
    analysis["selinuxfs"] = selinuxfs
    analysis["deploy"] = deploy
    analysis["node"] = v857.v855.analyze(steps)
    return steps, analysis


def decide(args: argparse.Namespace,
           v855_manifest: dict[str, Any],
           v860_replay: dict[str, Any],
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if v855_manifest.get("decision") != "v855-esoc-node-parity-clean":
            return "v861-plan-v855-missing", False, "V855 clean node-parity evidence is missing", "rerun V855 before V861"
        if v860_replay.get("decision") != "v860-property-clean-no-subsys-hold":
            return "v861-plan-v860-missing", False, "V860 property-clean replay evidence is missing", "rerun V860 before V861"
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v861-plan-helper-v133-missing", False, f"local_helper={local}", "build helper v133 before live"
        return "v861-pm-service-domain-parity-plan-ready", True, "plan-only; no device command executed", "run bounded V861 live proof"
    missing = required_flags(args)
    if missing:
        return "v861-pm-service-domain-parity-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun V861 with explicit bounded live flags"
    if v855_manifest.get("decision") != "v855-esoc-node-parity-clean":
        return "v861-v855-node-parity-missing", False, "V855 clean node-parity evidence is missing or stale", "rerun V855 before V861"
    if v860_replay.get("decision") != "v860-property-clean-no-subsys-hold":
        return "v861-v860-property-clean-missing", False, "V860 property-clean replay evidence is missing", "rerun V860 before V861"
    if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
        return "v861-helper-v133-local-missing", False, f"local_helper={local}", "rebuild helper v133 before deploy"
    failed_steps = [
        step["name"]
        for step in steps
        if not step.get("ok")
        and not (step.get("name") == "helper-usage-after-deploy" and args.helper_marker in str(step.get("payload") or ""))
        and not step.get("name", "").startswith("netservice")
    ]
    if failed_steps:
        return "v861-step-failed", False, f"failed_steps={failed_steps}", "inspect V861 evidence before retry"
    deploy = analysis.get("deploy") or {}
    if not deploy.get("pass"):
        return "v861-helper-deploy-failed", False, f"deploy={deploy}", "repair helper deployment before V861 replay"
    helper = analysis.get("helper") or {}
    denials = helper.get("property_denials") or {}
    if int(denials.get("total") or 0) > 0:
        return "v861-property-regression", False, f"property_denials={denials}", "repair V860 property root before domain-parity interpretation"
    if helper.get("forbidden_hits"):
        return "v861-forbidden-surface-detected", False, f"forbidden={helper.get('forbidden_hits')}", "stop and audit helper mode before retry"
    keys = helper.get("keys") or {}
    if keys.get("mode") != v857.MODE or keys.get("allowed") != "1":
        return "v861-helper-mode-not-executed", False, f"keys={keys}", "fix helper mode/allow flags before retry"
    if not helper.get("per_mgr_exec_target_match") or not helper.get("per_proxy_exec_target_match"):
        return "v861-domain-target-not-applied", True, f"children={helper.get('children')}", "repair helper SELinux target mapping before actor escalation"
    if not helper.get("per_mgr_actual_domain_match") or not helper.get("per_proxy_actual_domain_match"):
        return (
            "v861-exec-target-accepted-current-kernel-no-subsys-hold",
            True,
            f"vendor_per_mgr exec target was accepted but runtime attr/current stayed non-Android; children={helper.get('children')}",
            "classify native SELinux transition semantics or init-service launch context before mdm_helper",
        )
    if helper.get("per_mgr_holds_subsys_modem") and helper.get("per_mgr_holds_subsys_esoc0"):
        return (
            "v861-pm-service-domain-parity-subsys-hold-confirmed",
            True,
            "vendor_per_mgr domain parity made pm-service hold both Android-equivalent subsystem nodes",
            "plan mdm_helper/ks eSoC contract replay below HAL/connect",
        )
    children = helper.get("children") or {}
    return (
        "v861-domain-parity-clean-no-subsys-hold",
        True,
        f"vendor_per_mgr domain parity applied and property denials stayed zero, but no subsystem fd hold; children={children}",
        "classify missing init/service/provider trigger or mdm_helper ordering before starting mdm_helper",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V861 pm-service Domain Parity",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{manifest['helper_marker']}`",
        f"- helper_sha256: `{manifest['helper_sha256']}`",
        f"- helper_deploy_executed: `{manifest['helper_deploy_executed']}`",
        f"- pm_service_start_only_executed: `{manifest['pm_service_start_only_executed']}`",
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
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
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
    device_commands = args.command == "run" and bool(steps)
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
        "v860_replay_manifest": {
            "path": str(repo_path(args.v860_replay_manifest)),
            "decision": v860_replay.get("decision"),
            "pass": bool(v860_replay.get("pass")),
        },
        "local_helper": local,
        "helper": args.helper,
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "steps": steps,
        "analysis": analysis,
        "required_flags_missing": required_flags(args),
        "device_commands_executed": device_commands,
        "device_mutations": device_commands,
        "helper_deploy_executed": device_commands,
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
    print(f"helper_deploy_executed: {manifest['helper_deploy_executed']}")
    print(f"pm_service_start_only_executed: {manifest['pm_service_start_only_executed']}")
    print(f"mdm_helper_start_executed: {manifest['mdm_helper_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
