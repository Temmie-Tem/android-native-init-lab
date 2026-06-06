#!/usr/bin/env python3
"""V1032 bounded PM runtime-domain guard live classifier.

Runs deployed helper v175 with the V1027 PM full-contract order plus
`--require-android-selinux-exec-match`. The proof is intentionally fail-closed:
if a PM actor's requested Android SELinux exec context is not observable in
`/proc/self/attr/exec` before `execv`, the helper must stop that child before
the actor can run.

This does not start Wi-Fi HAL, scan/connect, use credentials, configure routes,
or ping externally.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import native_wifi_pm_full_contract_live_v1027 as v1027
from a90_kernel_tools import markdown_table


base = v1027.base
v923 = v1027.v923

ORIGINAL_V923_HELPER_SURFACE = v923.helper_surface

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1032-pm-runtime-domain-guard-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1032-pm-runtime-domain-guard-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1030-execns-helper-v175-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "9036bb15ced9fb1098c4375c15c2c729502c841574ae14798fb331fc29c89e42"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v175"

DEFAULT_SERVICE_MANAGER_ORDER = v1027.DEFAULT_SERVICE_MANAGER_ORDER
DEFAULT_SUBSYS_TRIGGER_GATE = v1027.DEFAULT_SUBSYS_TRIGGER_GATE
DEFAULT_PROPERTY_ROOT = v1027.DEFAULT_PROPERTY_ROOT

GUARDED_CHILDREN = (
    "pm_proxy_helper",
    "per_mgr_light",
    "pm_proxy",
    "mdm_helper",
)


def parse_args() -> argparse.Namespace:
    return v1027.parse_args()


def required_flags(args: argparse.Namespace) -> list[str]:
    return v1027.required_flags(args)


def helper_command(args: argparse.Namespace) -> list[str]:
    command = v1027.helper_command(args)
    insert_at = command.index("--timeout-sec") if "--timeout-sec" in command else len(command)
    command.insert(insert_at, "--require-android-selinux-exec-match")
    return command


def _child_guard(keys: dict[str, str], child: str) -> dict[str, str]:
    prefix = f"wifi_hal_composite_child.{child}.selinux_exec."
    return {
        "target_context": keys.get(prefix + "target_context", ""),
        "ok": keys.get(prefix + "ok", ""),
        "match_required": keys.get(prefix + "match_required", ""),
        "attr_exec_observed": keys.get(prefix + "attr_exec_observed", ""),
        "attr_exec_expected": keys.get(prefix + "attr_exec_expected", ""),
        "attr_exec_match": keys.get(prefix + "attr_exec_match", ""),
        "attr_exec_error": keys.get(prefix + "attr_exec_error", ""),
    }


def helper_surface(text: str) -> dict[str, Any]:
    surface = ORIGINAL_V923_HELPER_SURFACE(text)
    keys = base.parse_keys(text)
    children = {child: _child_guard(keys, child) for child in GUARDED_CHILDREN}
    blocked = {
        child: data
        for child, data in children.items()
        if data.get("match_required") == "1" and data.get("attr_exec_match") == "0"
    }
    matched = {
        child: data
        for child, data in children.items()
        if data.get("match_required") == "1" and data.get("attr_exec_match") == "1"
    }
    contract = surface.get("contract") or {}
    contract["runtime_domain_guard_enabled"] = "1"
    contract["runtime_domain_guard_blocked"] = "1" if blocked else "0"
    contract["runtime_domain_guard_matched_count"] = str(len(matched))
    contract["runtime_domain_guard_blocked_count"] = str(len(blocked))
    surface["contract"] = contract
    surface["runtime_domain_guard"] = {
        "children": children,
        "blocked": blocked,
        "matched": matched,
    }
    return surface


def _domain_guard_blocked(helper: dict[str, Any]) -> bool:
    return bool((helper.get("runtime_domain_guard") or {}).get("blocked"))


def decide(
    args: argparse.Namespace,
    local: dict[str, Any],
    steps: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v1032-plan-helper-v175-missing", False, f"local={local}", "build/deploy helper v175 before V1032"
        return "v1032-pm-runtime-domain-guard-plan-ready", True, "plan-only; no device command executed", "run bounded V1032 PM runtime-domain guard proof"

    missing = required_flags(args)
    if missing:
        return "v1032-pm-runtime-domain-guard-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V1032 flags"

    helper = analysis.get("helper") or {}
    failed_steps = v923.step_failures(steps, helper)
    if failed_steps:
        return "v1032-step-failed", False, f"failed_steps={failed_steps}", "inspect V1032 evidence before retry"

    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v1032-helper-v175-remote-mismatch", False, f"remote={remote}", "redeploy helper v175 before V1032"

    if helper.get("forbidden_true"):
        return "v1032-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"

    contract = helper.get("contract") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v1032-helper-mode-not-executed", False, f"contract={contract}", "fix V1032 helper command before retry"

    if contract.get("runtime_domain_guard_enabled") != "1":
        return "v1032-runtime-domain-guard-not-enabled", False, f"contract={contract}", "fix V1032 helper command before retry"

    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v1032-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify or rerun recovery reboot before continuing"

    if _domain_guard_blocked(helper):
        return (
            "v1032-pm-runtime-domain-guard-blocked-clean",
            True,
            f"guard={(helper.get('runtime_domain_guard') or {}).get('blocked')}",
            "classify why current native SELinux exec attr remains outside requested Android PM domains",
        )

    if contract.get("matrix_mode") != "1" or contract.get("service_manager_order") != args.service_manager_order:
        return "v1032-matrix-order-mismatch", False, f"contract={contract}", "fix V1032 helper order command before retry"
    if contract.get("subsys_trigger_gate") != args.subsys_trigger_gate:
        return "v1032-subsys-gate-mismatch", False, f"contract={contract}", "fix V1032 helper gate command before retry"
    if contract.get("pm_full_contract_matrix") != "1":
        return "v1032-pm-full-contract-matrix-missing", False, f"contract={contract}", "repair helper matrix selection"

    decision, pass_ok, reason, next_step = v1027.decide(args, local, steps, analysis)
    return (
        decision.replace("v1027", "v1032").replace("v174", "v175"),
        pass_ok,
        reason.replace("v1027", "v1032").replace("v174", "v175"),
        next_step.replace("V1027", "V1032").replace("v174", "v175"),
    )


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V1032 PM Runtime-Domain Guard Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- service_manager_order: `{manifest['service_manager_order']}`",
        f"- subsys_trigger_gate: `{manifest['subsys_trigger_gate']}`",
        f"- require_android_selinux_exec_match: `{manifest['require_android_selinux_exec_match']}`",
        f"- runtime_domain_guard_blocked: `{manifest['runtime_domain_guard_blocked']}`",
        f"- runtime_domain_guard_blocked_children: `{manifest['runtime_domain_guard_blocked_children']}`",
        f"- pm_actor_execv_allowed_by_guard: `{manifest['pm_actor_execv_allowed_by_guard']}`",
        f"- pm_proxy_helper_start_executed: `{manifest['pm_proxy_helper_start_executed']}`",
        f"- pm_proxy_start_executed: `{manifest['pm_proxy_start_executed']}`",
        f"- pm_full_contract_seen: `{manifest['pm_full_contract_seen']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- mdm_helper_start_executed: `{manifest['mdm_helper_start_executed']}`",
        f"- cnss_diag_start_executed: `{manifest['cnss_diag_start_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- wlfw_precondition_observed: `{manifest['wlfw_precondition_observed']}`",
        f"- subsys_esoc0_open_attempted: `{manifest['subsys_esoc0_open_attempted']}`",
        f"- cleanup_reboot_executed: `{manifest['cleanup_reboot_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Analysis",
        "",
        markdown_table(["section", "value"], analysis_rows),
        "",
        "## Steps",
        "",
        markdown_table(["name", "status", "rc", "duration_sec", "file"], step_rows),
        "",
        "## Guardrails",
        "",
        "- Permits current-boot selinuxfs mount/cleanup, private property shim, Android PM actors, `mdm_helper`, service-manager trio, `cnss_diag`, and `cnss-daemon -n -l` only if the helper observes the requested Android SELinux exec context before `execv`.",
        "- Wi-Fi HAL, `wificond`, `IWifi.start`, `qcwlanstate`, scan/connect, credentials, DHCP/routes, external ping, controller eSoC notify, and controller BOOT_DONE are forbidden.",
        "- No module load/unload, boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write, or Wi-Fi link-up.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = v1027.build_manifest(args, store)
    helper = (manifest.get("analysis") or {}).get("helper") or {}
    guard = helper.get("runtime_domain_guard") or {}
    contract = helper.get("contract") or {}
    decision, pass_ok, reason, next_step = decide(
        args,
        manifest.get("local_helper") or {},
        manifest.get("steps") or [],
        manifest.get("analysis") or {},
    )
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "require_android_selinux_exec_match": True,
        "runtime_domain_guard": guard,
        "runtime_domain_guard_blocked": bool(guard.get("blocked")),
        "runtime_domain_guard_blocked_children": sorted((guard.get("blocked") or {}).keys()),
        "pm_actor_execv_allowed_by_guard": not bool(guard.get("blocked")),
        "runtime_domain_guard_blocked_count": int(str(contract.get("runtime_domain_guard_blocked_count") or "0")),
        "runtime_domain_guard_matched_count": int(str(contract.get("runtime_domain_guard_matched_count") or "0")),
    })
    return manifest


base.parse_args = parse_args
base.required_flags = required_flags
base.helper_command = helper_command
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest
v923.required_flags = required_flags
v923.helper_command = helper_command
v923.helper_surface = helper_surface
v923.decide = decide
v923.render_summary = render_summary
v923.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
