#!/usr/bin/env python3
"""V490 native SELinux policy-load proof.

This runner uses `a90_android_execns_probe v48` in `sepolicy-load-proof` mode
to compile Android split policy and write the resulting binary policy to
`/sys/fs/selinux/load`. This is a global SELinux policy mutation, so `run`
requires the exact approval phrase and the helper also requires
`--allow-policy-load-proof`.

It does not reexec init, start service-manager, start Wi-Fi HAL/CNSS,
scan/connect, DHCP, route, or ping externally.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import native_selinux_policy_inventory_v488 as base


base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v490-native-selinux-policy-load-proof")
base.DEFAULT_HELPER_SHA256 = "5bc491c7ed0c4da498c6ee16568004dd886df577edd5f8cbebd50fb0740db10c"
base.APPROVAL_PHRASE = (
    "approve v490 native SELinux policy-load proof only; "
    "no init reexec, no daemon start and no Wi-Fi bring-up"
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
        "sepolicy-load-proof",
        "--target-profile",
        "system-toybox",
        "--allow-policy-load-proof",
        "--timeout-sec",
        "10",
    ]


def summarize_load(step: base.Step | None) -> dict[str, Any]:
    text = base.read_step(step)
    keys = base.parse_keys(text)
    return {
        "file": step.file if step else "",
        "ok": bool(step and step.ok),
        "keys": keys,
        "result": keys.get("sepolicy_load.result", ""),
        "reason": keys.get("sepolicy_load.reason", ""),
        "policy_load_attempted": keys.get("sepolicy_load.policy_load_attempted", ""),
        "policy_load_executed": keys.get("sepolicy_load.policy_load_executed", ""),
        "init_reexec_executed": keys.get("sepolicy_load.init_reexec_executed", ""),
        "daemon_start_executed": keys.get("sepolicy_load.daemon_start_executed", ""),
        "wifi_hal_start_executed": keys.get("sepolicy_load.wifi_hal_start_executed", ""),
        "wifi_bringup_executed": keys.get("sepolicy_load.wifi_bringup_executed", ""),
        "bytes": keys.get("sepolicy_load.bytes", ""),
        "hash": keys.get("sepolicy_load.hash", ""),
        "compiled_policy_version": keys.get("sepolicy_load.compiled_policy.version", ""),
        "kernel_policy_version": keys.get("sepolicy_load.kernel_policy_version", ""),
        "vendor_mapping_version": keys.get("sepolicy_load.vendor_mapping_version", ""),
        "pre_current": keys.get("sepolicy_load.pre.current", ""),
        "post_current": keys.get("sepolicy_load.post.current", ""),
        "pre_enforce": keys.get("sepolicy_load.pre.enforce", ""),
        "post_enforce": keys.get("sepolicy_load.post.enforce", ""),
        "attempt_31_result": keys.get("sepolicy_compile.attempt_31.result", ""),
        "attempt_31_exit_code": keys.get("sepolicy_compile.attempt_31.exit_code", ""),
        "attempt_30_result": keys.get("sepolicy_compile.attempt_30.result", ""),
        "attempt_30_exit_code": keys.get("sepolicy_compile.attempt_30.exit_code", ""),
    }


def build_checks(args: base.argparse.Namespace,
                 steps: dict[str, base.Step],
                 load_result: dict[str, Any] | None = None) -> list[base.Check]:
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
                   "fix native runtime before SELinux policy-load proof")
    helper_marker_ready = any(
        marker in helper_usage
        for marker in ("a90_android_execns_probe v48", "a90_android_execns_probe v52", "a90_android_execns_probe v53")
    )
    helper_ready = (
        args.helper_sha256 in helper_sha
        and helper_marker_ready
        and "sepolicy-load-proof" in helper_usage
        and "--allow-policy-load-proof" in helper_usage
    )
    base.add_check(checks, "helper-v48", "pass" if helper_ready else "blocked", "blocker",
                   f"sha_match={args.helper_sha256 in helper_sha} marker={helper_marker_ready} mode={'sepolicy-load-proof' in helper_usage} allow_flag={'--allow-policy-load-proof' in helper_usage}",
                   [line for line in helper_sha.splitlines() if args.helper in line][:2],
                   "deploy helper v48 before V490 run")
    base.add_check(checks, "selinuxfs-mounted", "pass" if "/sys/fs/selinux" in mounts and " selinuxfs " in mounts else "blocked", "blocker",
                   "global SELinuxfs must be mounted for policy load", [line for line in mounts.splitlines() if "/sys/fs/selinux" in line][:3],
                   "mount SELinuxfs before policy-load proof")
    base.add_check(checks, "process-surface-clean", "pass" if not process_hits else "blocked", "blocker",
                   f"process_count={len(process_hits)}", process_hits[:8],
                   "do not load policy over existing manager/HAL/CNSS process")
    base.add_check(checks, "wifi-link-clean", "pass" if not wifi_links else "blocked", "blocker",
                   f"wifi_link_count={len(wifi_links)}", wifi_links[:8],
                   "do not run policy-load proof while Wi-Fi link is active")
    base.add_check(checks, "approval-gate", "pass" if base.approved(args) else "needs-operator", "approval",
                   f"phrase_match={args.approval_phrase == base.APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
                   [base.APPROVAL_PHRASE], "exact approval required before SELinux policy load")

    if load_result is not None:
        keys = load_result["keys"]
        no_reexec_or_daemons = all(keys.get(key) == "0" for key in (
            "sepolicy_load.init_reexec_executed",
            "sepolicy_load.daemon_start_executed",
            "sepolicy_load.wifi_hal_start_executed",
            "sepolicy_load.wifi_bringup_executed",
        ))
        base.add_check(checks, "policy-load-result", "pass" if load_result["result"] == "policy-load-pass" else "gap", "finding",
                       f"result={load_result['result']} reason={load_result['reason']} attempted={load_result['policy_load_attempted']} executed={load_result['policy_load_executed']}",
                       [load_result["file"]],
                       "inspect load errno and compile transcript if policy load failed")
        base.add_check(checks, "compile-before-load", "pass" if load_result["attempt_31_result"] == "compile-pass" or load_result["attempt_30_result"] == "compile-pass" else "gap", "finding",
                       f"v31={load_result['attempt_31_result']}/{load_result['attempt_31_exit_code']} v30={load_result['attempt_30_result']}/{load_result['attempt_30_exit_code']}",
                       [f"kernel_policy_version={load_result['kernel_policy_version']}", f"vendor_mapping_version={load_result['vendor_mapping_version']}"],
                       "compile must pass before any policy load is accepted")
        base.add_check(checks, "load-safety", "pass" if no_reexec_or_daemons else "blocked", "blocker",
                       f"init_reexec={load_result['init_reexec_executed']} daemon={load_result['daemon_start_executed']} hal={load_result['wifi_hal_start_executed']} wifi={load_result['wifi_bringup_executed']}",
                       [load_result["file"]],
                       "stop and inspect helper before any daemon/HAL retry")
    return checks


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           load_result: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v490-selinux-policy-load-proof-plan-ready", True, "plan-only; no device command executed", "deploy v48, preflight, then explicitly approve policy-load proof"
    pre_run_blockers = base.blockers(checks, ignore_approval=args.command == "preflight" or (args.command == "run" and base.approved(args)))
    if args.command == "preflight":
        if pre_run_blockers:
            return "v490-selinux-policy-load-proof-blocked", False, "blocked before run by " + ", ".join(pre_run_blockers), "resolve blockers before V490 run"
        return "v490-selinux-policy-load-proof-preflight-ready", True, "preflight passed; run still needs exact approval", "run approved policy-load proof only"
    if not base.approved(args):
        return "v490-selinux-policy-load-proof-approval-required", False, "missing exact approval phrase or apply flags", "rerun with exact V490 approval"
    if pre_run_blockers:
        return "v490-selinux-policy-load-proof-blocked", False, "blocked before run by " + ", ".join(pre_run_blockers), "resolve blockers before retry"
    if load_result is None or not load_result.get("ok"):
        return "v490-selinux-policy-load-proof-run-failed", False, "policy-load helper did not complete", "inspect helper transcript and device state"
    if load_result["result"] == "policy-load-pass":
        return "v490-selinux-policy-load-proof-pass", True, "compiled Android split policy was written to /sys/fs/selinux/load without init reexec or daemon start", "run a separate post-load domain-transition proof before any HAL start"
    return "v490-selinux-policy-load-proof-gap", False, f"load result={load_result['result']} reason={load_result['reason']}", "inspect load errno and compile transcript before retry"


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[check["name"], check["status"], check["severity"], check["detail"]] for check in manifest["checks"]]
    load_result = manifest.get("load") or {}
    rows = [
        ["result", load_result.get("result", "")],
        ["reason", load_result.get("reason", "")],
        ["attempted", load_result.get("policy_load_attempted", "")],
        ["executed", load_result.get("policy_load_executed", "")],
        ["bytes", load_result.get("bytes", "")],
        ["hash", load_result.get("hash", "")],
        ["compiled_policy_version", load_result.get("compiled_policy_version", "")],
        ["pre_current", load_result.get("pre_current", "")],
        ["post_current", load_result.get("post_current", "")],
        ["pre_enforce", load_result.get("pre_enforce", "")],
        ["post_enforce", load_result.get("post_enforce", "")],
    ]
    return "\n".join([
        "# V490 Native SELinux Policy Load Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        "",
        "## Load",
        "",
        base.markdown_table(["item", "value"], rows),
        "",
        "## Checks",
        "",
        base.markdown_table(["name", "status", "severity", "detail"], checks),
        "",
        "## Safety",
        "",
        "- `run` is blocked unless the exact V490 approval phrase is provided.",
        "- The helper is also blocked unless `--allow-policy-load-proof` is present.",
        "- Does not reexec PID1.",
        "- Does not start service-manager, Wi-Fi HAL, CNSS, supplicant, or wificond.",
        "- Does not scan/connect/link-up, run DHCP, route, or ping externally.",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    steps: dict[str, base.Step] = {}
    load_result: dict[str, Any] | None = None
    if args.command != "plan":
        steps = base.preflight(args, store)
    checks = build_checks(args, steps)
    if args.command == "run" and base.approved(args) and not base.blockers(checks, ignore_approval=True):
        load_step = base.run_capture(args, store, "sepolicy-load-proof", helper_command(args), timeout=args.timeout + 30.0)
        load_result = summarize_load(load_step)
        checks = build_checks(args, steps, load_result)
    decision, pass_ok, reason, next_step = decide(args, checks, load_result)
    policy_loaded = bool(load_result and load_result.get("policy_load_executed") == "1")
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
            "helper_version": "a90_android_execns_probe v48",
            "helper_sha256": args.helper_sha256,
            "helper_mode": "sepolicy-load-proof",
            "system_root": "/mnt/system/system",
            "vendor_block": "/dev/block/sda29",
            "vendor_fstype": "ext4",
            "policy_load": True,
            "init_reexec": False,
        },
        "steps": {name: asdict(step) for name, step in steps.items()},
        "load": load_result,
        "checks": [asdict(check) for check in checks],
        "required_approval_phrase": base.APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == base.APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan",
        "device_mutations": args.command == "run" and base.approved(args),
        "policy_load_executed": policy_loaded,
        "init_reexec_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


base.helper_command = helper_command
base.summarize_inventory = summarize_load
base.build_checks = build_checks
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
