#!/usr/bin/env python3
"""V859 pm-service property-delta replay proof.

V858 deployed the pm-service/pm-proxy property context delta into the existing
private V535 property root.  This bounded live proof reuses the already deployed
helper and reruns only the `pm-service`/`pm-proxy` start-only path under Android
node parity to check whether property denials are gone and whether subsystem fd
holds appear.

It does not deploy a helper, start `mdm_helper`/`ks`, start Wi-Fi HAL, scan,
connect, use credentials, run DHCP/routes, or ping externally.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_pm_service_property_contract_start_only_v857 as v857
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v859-pm-service-property-delta-replay")
LATEST_POINTER = Path("tmp/wifi/latest-v859-pm-service-property-delta-replay.txt")
DEFAULT_V858_DEPLOY = Path("tmp/wifi/v858-pm-service-property-incremental-live/manifest.json")
DEFAULT_V858_LAYOUT = Path("tmp/wifi/v858-pm-service-private-property-runtime/manifest.json")
PROPERTY_DENIAL_RE = re.compile(
    r'(?:Could not find context for property|Access denied finding property) "([^"]+)"',
    re.I,
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
    parser.add_argument("--helper", default=v857.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=v857.DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=v857.DEFAULT_HELPER_MARKER)
    parser.add_argument("--runtime-sec", type=int, default=v857.DEFAULT_RUNTIME_SEC)
    parser.add_argument("--marker", default="/tmp/a90-v859-pm-property-delta.created")
    parser.add_argument("--v855-manifest", type=Path, default=v857.DEFAULT_V855_MANIFEST)
    parser.add_argument("--v858-deploy-manifest", type=Path, default=DEFAULT_V858_DEPLOY)
    parser.add_argument("--v858-layout-manifest", type=Path, default=DEFAULT_V858_LAYOUT)
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


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    for flag, enabled in (
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


def parse_denials(text: str) -> dict[str, Any]:
    counts = collections.Counter(PROPERTY_DENIAL_RE.findall(text.replace("\0", "\n")))
    return {
        "total": sum(counts.values()),
        "unique": len(counts),
        "counts": dict(sorted(counts.items())),
        "top": [[key, count] for key, count in counts.most_common(16)],
    }


def annotate_denials(analysis: dict[str, Any], v858_layout: dict[str, Any]) -> None:
    denials = analysis.get("property_denials") or {}
    counts = denials.get("counts") or {}
    target_keys = [str(key) for key in v858_layout.get("v857_residual_keys", [])]
    remaining = [key for key in target_keys if key in counts]
    new_keys = [key for key in counts if key not in set(target_keys)]
    denials["v858_target_keys"] = target_keys
    denials["v858_target_remaining"] = remaining
    denials["new_after_v858"] = new_keys


def plan_steps() -> list[dict[str, Any]]:
    return [
        {"name": "v855-manifest-check", "mutates": False},
        {"name": "v858-deploy-check", "mutates": False},
        {"name": "remote-helper-sha-check", "mutates": False},
        {"name": "mountsystem-ro", "mutates": True},
        {"name": "selinuxfs-mount", "mutates": True},
        {"name": "global-node-materialization", "mutates": True},
        {"name": "pm-service-property-delta-replay", "mutates": True},
        {"name": "node-cleanup", "mutates": True},
        {"name": "postflight-health", "mutates": False},
    ]


def execute(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    helper_live: dict[str, Any] = {}
    denials: dict[str, Any] = {}
    node_cleanup_done = False

    v857.run_device(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    v857.run_device(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    selinuxfs = v857.ensure_selinuxfs(args, store)
    v857.run_device(args, store, steps, "sha-helper", ["run", args.toybox, "sha256sum", args.helper], timeout=12.0)
    v857.run_device(args, store, steps, "helper-usage", ["run", args.helper], timeout=12.0)
    v857.run_device(args, store, steps, "node-preflight", v857.v855.shell_cmd(args, v857.v855.preflight_script(args)), timeout=20.0)
    try:
        v857.run_device(args, store, steps, "materialize-android-node-parity", v857.v855.shell_cmd(args, v857.v855.materialize_script(args)), timeout=20.0)
        helper = v857.run_device(args, store, steps, "pm-service-property-delta-replay", v857.helper_command(args), timeout=args.runtime_sec + 45.0)
        helper_payload = str(helper.get("payload") or "")
        helper_file = store.run_dir / str(helper.get("file") or "")
        if helper_file.exists():
            helper_payload = helper_file.read_text(encoding="utf-8", errors="replace")
        helper_live = v857.helper_surface(helper_payload)
        denials = parse_denials(helper_payload)
    finally:
        v857.run_device(args, store, steps, "cleanup-created-nodes", v857.v855.shell_cmd(args, v857.v855.cleanup_script(args)), timeout=20.0)
        node_cleanup_done = True
    v857.run_device(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)

    return steps, {
        "selinuxfs": selinuxfs,
        "node": v857.v855.analyze(steps),
        "helper": helper_live,
        "property_denials": denials,
        "node_cleanup_done": node_cleanup_done,
    }


def decide(args: argparse.Namespace,
           v855_manifest: dict[str, Any],
           v858_deploy: dict[str, Any],
           v858_layout: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if v855_manifest.get("decision") != "v855-esoc-node-parity-clean":
            return "v859-plan-v855-missing", False, "V855 clean node-parity evidence is missing", "rerun V855 before V859"
        if v858_deploy.get("decision") != "v858-pm-service-property-incremental-deploy-pass":
            return "v859-plan-v858-deploy-missing", False, "V858 property delta deploy evidence is missing", "run V858 deploy before V859"
        return "v859-pm-service-property-delta-replay-plan-ready", True, "plan-only; no device command executed", "run bounded V859 live replay"
    missing = required_flags(args)
    if missing:
        return "v859-pm-service-property-delta-replay-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun V859 with explicit bounded live flags"
    if v855_manifest.get("decision") != "v855-esoc-node-parity-clean":
        return "v859-v855-node-parity-missing", False, "V855 clean node-parity evidence is missing or stale", "rerun V855 before V859"
    if v858_deploy.get("decision") != "v858-pm-service-property-incremental-deploy-pass":
        return "v859-v858-property-delta-missing", False, "V858 deploy did not pass", "deploy V858 property delta before replay"
    failed_steps = [
        step["name"]
        for step in steps
        if not step.get("ok")
        and not (step.get("name") == "helper-usage" and args.helper_marker in str(step.get("payload") or ""))
    ]
    if failed_steps:
        return "v859-step-failed", False, f"failed_steps={failed_steps}", "inspect V859 evidence before retry"
    helper_sha_text = "\n".join(str(step.get("payload") or "") for step in steps if step.get("name") == "sha-helper")
    if args.helper_sha256 not in helper_sha_text:
        return "v859-helper-sha-mismatch", False, "remote helper sha did not match v132", "redeploy helper v132 before replay"
    selinuxfs = analysis.get("selinuxfs") or {}
    if not selinuxfs.get("pass"):
        return "v859-selinuxfs-mount-missing", False, f"selinuxfs={selinuxfs}", "mount SELinuxfs before replay"
    node = analysis.get("node") or {}
    if not (node.get("materialize") or {}).get("all_target_nodes_accounted"):
        return "v859-node-materialization-failed", False, f"node={node}", "repair node materialization before replay"
    if not (node.get("cleanup") or {}).get("removed_all_created"):
        return "v859-node-cleanup-review", False, f"node={node}", "cleanup created nodes before continuing"
    helper = analysis.get("helper") or {}
    keys = helper.get("keys") or {}
    if helper.get("forbidden_hits"):
        return "v859-forbidden-surface-detected", False, f"forbidden={helper.get('forbidden_hits')}", "stop and audit helper mode before retry"
    if keys.get("mode") != v857.MODE or keys.get("allowed") != "1":
        return "v859-helper-mode-not-executed", False, f"keys={keys}", "fix helper mode/allow flags before retry"
    denials = analysis.get("property_denials") or {}
    if int(denials.get("total") or 0) > 0:
        if not denials.get("v858_target_remaining") and denials.get("new_after_v858"):
            return (
                "v859-v858-target-denials-removed-new-property-gap",
                True,
                f"V858 target denials were removed; new property denials remain: {denials}",
                "extend property layout for vndservicemanager/ServiceManager/PerMgrLib keys before mdm_helper or ks replay",
            )
        return (
            "v859-property-denials-persist",
            True,
            f"V858 property root was used but denials remain: {denials}",
            "classify whether helper used stale property_info or needs new allow/context coverage",
        )
    if helper.get("per_mgr_holds_subsys_modem") and helper.get("per_mgr_holds_subsys_esoc0"):
        return (
            "v859-pm-service-subsys-hold-confirmed",
            True,
            "V858 removed property denials and pm-service held both Android-equivalent subsystem nodes",
            "plan mdm_helper/ks eSoC contract replay under the same lower gates",
        )
    return (
        "v859-property-clean-no-subsys-hold",
        True,
        "V858 removed pm-service/pm-proxy property denials, but subsystem fd hold is still not proven",
        "classify the next pm-service lifetime/input gap before mdm_helper or ks replay",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V859 pm-service Property Delta Replay",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- property_root: `{v857.PROPERTY_ROOT}`",
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
        markdown_table(["section", "value"], analysis_rows) if analysis_rows else "- none",
        "",
        "## Steps",
        "",
        markdown_table(["name", "status", "rc", "duration_sec", "file"], step_rows) if step_rows else "- none",
        "",
        "## Guardrails",
        "",
        "- No helper deployment.",
        "- No `mdm_helper` or `ks` start.",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "- No raw eSoC ioctl, GPIO/sysfs/debugfs write, subsystem state write, module load/unload, boot image write, or partition write.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v855_manifest = load_json(args.v855_manifest)
    v858_deploy = load_json(args.v858_deploy_manifest)
    v858_layout = load_json(args.v858_layout_manifest)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    if args.command == "run" and not required_flags(args):
        steps, analysis = execute(args, store)
        annotate_denials(analysis, v858_layout)
    decision, pass_ok, reason, next_step = decide(args, v855_manifest, v858_deploy, v858_layout, steps, analysis)
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
        "v858_deploy_manifest": {
            "path": str(repo_path(args.v858_deploy_manifest)),
            "decision": v858_deploy.get("decision"),
            "pass": bool(v858_deploy.get("pass")),
        },
        "v858_layout_manifest": {
            "path": str(repo_path(args.v858_layout_manifest)),
            "decision": v858_layout.get("decision"),
            "pass": bool(v858_layout.get("pass")),
        },
        "property_root": v857.PROPERTY_ROOT,
        "helper": args.helper,
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "plan_steps": plan_steps(),
        "steps": steps,
        "analysis": analysis,
        "required_flags_missing": required_flags(args),
        "device_commands_executed": device_commands,
        "device_mutations": device_commands,
        "helper_deploy_executed": False,
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
