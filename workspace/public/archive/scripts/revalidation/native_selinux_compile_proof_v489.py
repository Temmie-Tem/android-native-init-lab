#!/usr/bin/env python3
"""V489 native SELinux split-policy compile proof.

This runner uses `a90_android_execns_probe v47` in `sepolicy-compile-proof`
mode to run `/system/bin/secilc` inside the helper private namespace. It only
compiles into the helper temp root and proves the policy assembly path. It does
not write `/sys/fs/selinux/load`, reexec init, start service-manager, start
Wi-Fi HAL/CNSS, scan/connect, DHCP, route, or ping externally.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import native_selinux_policy_inventory_v488 as base


base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v489-native-selinux-compile-proof")
base.DEFAULT_HELPER_SHA256 = "ee49f2b762081c3d617cf84f957080846c8c003ef1ea08836772ae21d7149efb"
base.APPROVAL_PHRASE = (
    "approve v489 native SELinux compile proof only; "
    "no policy load, no daemon start and no Wi-Fi bring-up"
)


def helper_command(args: base.argparse.Namespace) -> list[str]:
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
        "sepolicy-compile-proof",
        "--target-profile",
        "system-toybox",
        "--timeout-sec",
        "10",
    ]


def summarize_compile(step: base.Step | None) -> dict[str, Any]:
    text = base.read_step(step)
    keys = base.parse_keys(text)
    return {
        "file": step.file if step else "",
        "ok": bool(step and step.ok),
        "keys": keys,
        "result": keys.get("sepolicy_compile.result", ""),
        "reason": keys.get("sepolicy_compile.reason", ""),
        "attempts": keys.get("sepolicy_compile.attempts", ""),
        "pass_version": keys.get("sepolicy_compile.pass_version", ""),
        "kernel_policy_version": keys.get("sepolicy_compile.kernel_policy_version", ""),
        "vendor_mapping_version": keys.get("sepolicy_compile.vendor_mapping_version", ""),
        "attempt_31_result": keys.get("sepolicy_compile.attempt_31.result", ""),
        "attempt_31_exit_code": keys.get("sepolicy_compile.attempt_31.exit_code", ""),
        "attempt_31_output_hash": keys.get("sepolicy_compile.attempt_31.output.hash", ""),
        "attempt_30_result": keys.get("sepolicy_compile.attempt_30.result", ""),
        "attempt_30_exit_code": keys.get("sepolicy_compile.attempt_30.exit_code", ""),
        "attempt_30_output_hash": keys.get("sepolicy_compile.attempt_30.output.hash", ""),
        "policy_load_executed": keys.get("sepolicy_compile.policy_load_executed", ""),
        "init_reexec_executed": keys.get("sepolicy_compile.init_reexec_executed", ""),
        "daemon_start_executed": keys.get("sepolicy_compile.daemon_start_executed", ""),
        "wifi_hal_start_executed": keys.get("sepolicy_compile.wifi_hal_start_executed", ""),
        "wifi_bringup_executed": keys.get("sepolicy_compile.wifi_bringup_executed", ""),
    }


def build_checks(args: base.argparse.Namespace,
                 steps: dict[str, base.Step],
                 compile_result: dict[str, Any] | None = None) -> list[base.Check]:
    checks: list[base.Check] = []
    if args.command == "plan":
        base.add_check(checks, "plan-only", "pass", "info", "no device command executed")
        return checks

    version = base.read_step(steps.get("version"))
    status = base.read_step(steps.get("status"))
    ps = base.read_step(steps.get("ps"))
    netdev = base.read_step(steps.get("netdev"))
    mounts = base.read_step(steps.get("mounts"))
    helper_sha = base.read_step(steps.get("helper-sha"))
    helper_usage = base.read_step(steps.get("helper-usage"))
    process_hits = [
        line.strip()
        for line in ps.splitlines()
        if any(token in line for token in (
            "servicemanager",
            "hwservicemanager",
            "vendor.samsung.hardware.wifi",
            "android.hardware.wifi",
            "cnss-daemon",
            "wpa_supplicant",
            "wificond",
        ))
    ]
    wifi_links = [line.strip() for line in netdev.splitlines() if base.re.search(r"\b(wlan|wifi|p2p)", line)]

    base.add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning",
                   f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3])
    base.add_check(checks, "native-clean", "pass" if "fail=0" in status else "blocked", "blocker",
                   "status/selftest fail=0 expected", [line for line in status.splitlines() if "selftest:" in line][:2],
                   "fix native runtime before SELinux compile proof")
    helper_ready = (
        args.helper_sha256 in helper_sha
        and "a90_android_execns_probe v47" in helper_usage
        and "sepolicy-compile-proof" in helper_usage
    )
    base.add_check(checks, "helper-v47", "pass" if helper_ready else "blocked", "blocker",
                   f"sha_match={args.helper_sha256 in helper_sha} marker={'a90_android_execns_probe v47' in helper_usage} mode={'sepolicy-compile-proof' in helper_usage}",
                   [line for line in helper_sha.splitlines() if args.helper in line][:2],
                   "deploy helper v47 before V489 run")
    base.add_check(checks, "selinuxfs-mounted", "pass" if "/sys/fs/selinux" in mounts and " selinuxfs " in mounts else "blocked", "blocker",
                   "global SELinuxfs must be mounted for private compile null sink", [line for line in mounts.splitlines() if "/sys/fs/selinux" in line][:3],
                   "mount SELinuxfs before policy compile proof")
    base.add_check(checks, "process-surface-clean", "pass" if not process_hits else "blocked", "blocker",
                   f"process_count={len(process_hits)}", process_hits[:8],
                   "do not compile proof over existing manager/HAL/CNSS process")
    base.add_check(checks, "wifi-link-clean", "pass" if not wifi_links else "blocked", "blocker",
                   f"wifi_link_count={len(wifi_links)}", wifi_links[:8],
                   "do not run compile proof while Wi-Fi link is active")
    base.add_check(checks, "approval-gate", "pass" if base.approved(args) else "needs-operator", "approval",
                   f"phrase_match={args.approval_phrase == base.APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
                   [base.APPROVAL_PHRASE], "exact approval required before namespace compile proof")

    if compile_result is not None:
        keys = compile_result["keys"]
        safety_ok = all(keys.get(key) == "0" for key in (
            "sepolicy_compile.policy_load_executed",
            "sepolicy_compile.init_reexec_executed",
            "sepolicy_compile.daemon_start_executed",
            "sepolicy_compile.wifi_hal_start_executed",
            "sepolicy_compile.wifi_bringup_executed",
        ))
        base.add_check(checks, "compile-result", "pass" if compile_result["result"] == "compile-pass" else "gap", "finding",
                       f"result={compile_result['result']} reason={compile_result['reason']} pass_version={compile_result['pass_version']}",
                       [compile_result["file"]],
                       "inspect secilc stderr and exact argv if compile failed")
        base.add_check(checks, "compile-attempts", "pass" if compile_result["attempts"] else "gap", "finding",
                       f"attempts={compile_result['attempts']} v31={compile_result['attempt_31_result']}/{compile_result['attempt_31_exit_code']} v30={compile_result['attempt_30_result']}/{compile_result['attempt_30_exit_code']}",
                       [f"kernel_policy_version={compile_result['kernel_policy_version']}", f"vendor_mapping_version={compile_result['vendor_mapping_version']}"],
                       "use passing policy version for any later load-only proof")
        base.add_check(checks, "compile-safety", "pass" if safety_ok else "blocked", "blocker",
                       f"policy_load={compile_result['policy_load_executed']} init_reexec={compile_result['init_reexec_executed']} daemon={compile_result['daemon_start_executed']} hal={compile_result['wifi_hal_start_executed']} wifi={compile_result['wifi_bringup_executed']}",
                       [compile_result["file"]],
                       "stop and inspect helper before any further live SELinux work")
    return checks


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           compile_result: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v489-selinux-compile-proof-plan-ready", True, "plan-only; no device command executed", "deploy v47 and run preflight"
    pre_run_blockers = base.blockers(checks, ignore_approval=args.command == "preflight" or (args.command == "run" and base.approved(args)))
    if args.command == "preflight":
        if pre_run_blockers:
            return "v489-selinux-compile-proof-blocked", False, "blocked before run by " + ", ".join(pre_run_blockers), "resolve blockers before V489 run"
        return "v489-selinux-compile-proof-preflight-ready", True, "preflight passed; run still needs exact approval", "run approved secilc compile proof"
    if not base.approved(args):
        return "v489-selinux-compile-proof-approval-required", False, "missing exact approval phrase or apply flags", "rerun with exact V489 approval"
    if pre_run_blockers:
        return "v489-selinux-compile-proof-blocked", False, "blocked before run by " + ", ".join(pre_run_blockers), "resolve blockers before retry"
    if compile_result is None or not compile_result.get("ok"):
        return "v489-selinux-compile-proof-run-failed", False, "compile helper did not complete", "inspect helper transcript"
    if compile_result["result"] == "compile-pass":
        return "v489-selinux-compile-proof-pass", True, f"secilc compiled split policy with policy version {compile_result['pass_version']} in private namespace", "plan a separate explicit policy-load proof; do not start HAL yet"
    return "v489-selinux-compile-proof-gap", False, f"compile result={compile_result['result']} reason={compile_result['reason']}", "inspect secilc stderr and argv before any policy load attempt"


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[check["name"], check["status"], check["severity"], check["detail"]] for check in manifest["checks"]]
    compile_result = manifest.get("compile") or {}
    rows = [
        ["result", compile_result.get("result", "")],
        ["reason", compile_result.get("reason", "")],
        ["attempts", compile_result.get("attempts", "")],
        ["pass_version", compile_result.get("pass_version", "")],
        ["kernel_policy_version", compile_result.get("kernel_policy_version", "")],
        ["vendor_mapping_version", compile_result.get("vendor_mapping_version", "")],
        ["attempt_31", f"{compile_result.get('attempt_31_result', '')}/{compile_result.get('attempt_31_exit_code', '')}"],
        ["attempt_30", f"{compile_result.get('attempt_30_result', '')}/{compile_result.get('attempt_30_exit_code', '')}"],
    ]
    return "\n".join([
        "# V489 Native SELinux Compile Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        "",
        "## Compile",
        "",
        base.markdown_table(["item", "value"], rows),
        "",
        "## Checks",
        "",
        base.markdown_table(["name", "status", "severity", "detail"], checks),
        "",
        "## Safety",
        "",
        "- Runs `/system/bin/secilc` only inside the helper private namespace.",
        "- Writes compiled policy only to the helper temp root and removes it before cleanup.",
        "- Does not write `/sys/fs/selinux/load` or reexec PID1.",
        "- No daemon/HAL/CNSS process is started.",
        "- No Wi-Fi scan/connect/link-up or external ping is attempted.",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    steps: dict[str, base.Step] = {}
    compile_result: dict[str, Any] | None = None
    if args.command != "plan":
        steps = base.preflight(args, store)
    checks = build_checks(args, steps)
    if args.command == "run" and base.approved(args) and not base.blockers(checks, ignore_approval=True):
        compile_step = base.run_capture(args, store, "sepolicy-compile-proof", helper_command(args), timeout=args.timeout + 30.0)
        compile_result = summarize_compile(compile_step)
        checks = build_checks(args, steps, compile_result)
    decision, pass_ok, reason, next_step = decide(args, checks, compile_result)
    return {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": base.collect_host_metadata(),
        "plan": {
            "helper": args.helper,
            "helper_version": "a90_android_execns_probe v47",
            "helper_sha256": args.helper_sha256,
            "helper_mode": "sepolicy-compile-proof",
            "system_root": "/mnt/system/system",
            "vendor_block": "/dev/block/sda29",
            "vendor_fstype": "ext4",
            "policy_load": False,
            "init_reexec": False,
        },
        "steps": {name: asdict(step) for name, step in steps.items()},
        "compile": compile_result,
        "checks": [asdict(check) for check in checks],
        "required_approval_phrase": base.APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == base.APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan",
        "device_mutations": False,
        "policy_load_executed": False,
        "init_reexec_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


base.helper_command = helper_command
base.summarize_inventory = summarize_compile
base.build_checks = build_checks
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
