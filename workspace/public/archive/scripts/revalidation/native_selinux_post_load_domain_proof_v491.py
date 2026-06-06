#!/usr/bin/env python3
"""V491 post-load SELinux domain-transition proof.

This runner uses `a90_android_execns_probe v48` in `selinux-domain-proof` mode
after a successful V490 policy-load proof. It reuses the static
`/proc/self/exe --selinux-print-current` post-exec probe to determine whether
requested Android domains survive exec after the compiled Android policy has
been loaded.

It does not load SELinux policy, reexec PID1, start service-manager, start
Wi-Fi HAL/CNSS, scan/connect, DHCP, route, or ping externally.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import native_selinux_init_handoff_v487 as base


DEFAULT_OUT_DIR = Path("tmp/wifi/v491-native-selinux-post-load-domain-proof")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_HELPER_SHA256 = "5bc491c7ed0c4da498c6ee16568004dd886df577edd5f8cbebd50fb0740db10c"
APPROVAL_PHRASE = (
    "approve v491 post-load SELinux domain proof only; "
    "no policy load, no daemon start and no Wi-Fi bring-up"
)
CONTEXTS = (
    "u:r:init:s0",
    "u:r:hal_wifi_default:s0",
    "u:r:servicemanager:s0",
    "u:r:hwservicemanager:s0",
)
ATTR_MODES = ("current", "exec", "both")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--v490-manifest", type=Path)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"))
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def helper_command(args: argparse.Namespace, context: str, attr_mode: str) -> list[str]:
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
        "selinux-domain-proof",
        "--target-profile",
        "system-toybox",
        "--selinux-context",
        context,
        "--selinux-attr-mode",
        attr_mode,
        "--timeout-sec",
        "5",
    ]


def load_v490_manifest(args: argparse.Namespace) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(args.v490_manifest) if args.v490_manifest else "",
        "present": False,
        "valid": False,
        "decision": "",
        "policy_load_executed": False,
        "init_reexec_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "reason": "missing-v490-manifest",
    }
    if args.v490_manifest is None:
        return result
    if not args.v490_manifest.exists():
        result["reason"] = "v490-manifest-not-found"
        return result
    result["present"] = True
    try:
        manifest = json.loads(args.v490_manifest.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report evidence parser issue
        result["reason"] = f"v490-manifest-read-failed-{exc}"
        return result
    result["decision"] = str(manifest.get("decision", ""))
    result["policy_load_executed"] = bool(manifest.get("policy_load_executed"))
    result["init_reexec_executed"] = bool(manifest.get("init_reexec_executed"))
    result["daemon_start_executed"] = bool(manifest.get("daemon_start_executed"))
    result["wifi_hal_start_executed"] = bool(manifest.get("wifi_hal_start_executed"))
    result["wifi_bringup_executed"] = bool(manifest.get("wifi_bringup_executed"))
    result["valid"] = (
        manifest.get("decision") == "v490-selinux-policy-load-proof-pass"
        and manifest.get("pass") is True
        and manifest.get("policy_load_executed") is True
        and manifest.get("init_reexec_executed") is False
        and manifest.get("daemon_start_executed") is False
        and manifest.get("wifi_hal_start_executed") is False
        and manifest.get("wifi_bringup_executed") is False
    )
    result["reason"] = "v490-policy-load-pass" if result["valid"] else "v490-policy-load-pass-required"
    return result


def preflight(args: argparse.Namespace, store: base.EvidenceStore) -> dict[str, base.Step]:
    steps = base.preflight(args, store)
    steps["selinux-current"] = base.run_capture(
        args,
        store,
        "selinux-current",
        ["run", args.toybox, "cat", "/proc/self/attr/current"],
        args.timeout,
    )
    steps["selinux-enforce"] = base.run_capture(
        args,
        store,
        "selinux-enforce",
        ["run", args.toybox, "cat", "/sys/fs/selinux/enforce"],
        args.timeout,
    )
    steps["selinux-policyvers"] = base.run_capture(
        args,
        store,
        "selinux-policyvers",
        ["run", args.toybox, "cat", "/sys/fs/selinux/policyvers"],
        args.timeout,
    )
    return steps


def build_checks(args: argparse.Namespace,
                 steps: dict[str, base.Step],
                 v490: dict[str, Any],
                 cases: list[dict[str, Any]] | None = None,
                 postflight: dict[str, Any] | None = None) -> list[base.Check]:
    checks: list[base.Check] = []
    if args.command == "plan":
        base.add_check(checks, "plan-only", "pass", "info", "no device command executed")
        return checks

    version = base.read_step(steps.get("version"))
    status = base.read_step(steps.get("status"))
    ps = base.read_step(steps.get("ps"))
    netdev = base.read_step(steps.get("netdev"))
    helper_sha = base.read_step(steps.get("helper-sha"))
    helper_usage = base.read_step(steps.get("helper-usage"))
    current = base.read_step(steps.get("selinux-current")).strip().replace("\x00", "")
    enforce = base.read_step(steps.get("selinux-enforce")).strip().replace("\x00", "")
    policyvers = base.read_step(steps.get("selinux-policyvers")).strip().replace("\x00", "")
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
    wifi_links = [line.strip() for line in netdev.splitlines() if re.search(r"\b(wlan|wifi|p2p)", line)]

    base.add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning",
                   f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3])
    base.add_check(checks, "native-clean", "pass" if "fail=0" in status else "blocked", "blocker",
                   "status/selftest fail=0 expected", [line for line in status.splitlines() if "selftest:" in line][:2],
                   "fix native runtime before post-load domain proof")
    helper_marker_match = re.search(r"a90_android_execns_probe v([0-9]+)", helper_usage)
    helper_marker_version = int(helper_marker_match.group(1)) if helper_marker_match else 0
    helper_marker_ready = helper_marker_version >= 48
    helper_ready = (
        args.helper_sha256 in helper_sha
        and helper_marker_ready
        and "selinux-domain-proof" in helper_usage
        and "--selinux-print-current" in helper_usage
    )
    base.add_check(checks, "helper-v48-domain-proof", "pass" if helper_ready else "blocked", "blocker",
                   f"sha_match={args.helper_sha256 in helper_sha} marker={helper_marker_ready} static_probe={'--selinux-print-current' in helper_usage}",
                   [line for line in helper_sha.splitlines() if args.helper in line][:2],
                   "deploy helper v48 before V491 run")
    base.add_check(checks, "v490-policy-load-evidence", "pass" if v490["valid"] else "blocked", "blocker",
                   f"path={v490['path']} present={v490['present']} decision={v490['decision']} policy_load={v490['policy_load_executed']} reason={v490['reason']}",
                   [v490["path"]] if v490["path"] else [],
                   "run V490 policy-load proof and pass its manifest to --v490-manifest")
    base.add_check(checks, "selinux-runtime-visible", "pass" if current and enforce and policyvers else "blocked", "blocker",
                   f"current={current[:80]} enforce={enforce} policyvers={policyvers}",
                   [current[:160], enforce, policyvers],
                   "inspect SELinuxfs and proc attr visibility before V491")
    base.add_check(checks, "process-surface-clean", "pass" if not process_hits else "blocked", "blocker",
                   f"process_count={len(process_hits)}", process_hits[:8],
                   "do not run domain proof over existing manager/HAL/CNSS process")
    base.add_check(checks, "wifi-link-clean", "pass" if not wifi_links else "blocked", "blocker",
                   f"wifi_link_count={len(wifi_links)}", wifi_links[:8],
                   "do not run domain proof while Wi-Fi link is active")
    base.add_check(checks, "approval-gate", "pass" if approved(args) else "needs-operator", "approval",
                   f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
                   [APPROVAL_PHRASE], "exact approval required before child-local SELinux attr writes")

    if cases is not None:
        any_match = any(case["postexec_match"] for case in cases)
        base.add_check(checks, "static-postexec-match", "pass" if any_match else "gap", "finding",
                       f"matching_cases={sum(1 for case in cases if case['postexec_match'])}/{len(cases)}",
                       [f"{case['context']} {case['attr_mode']} match={case['postexec_match']} current={case['postexec_current']}" for case in cases],
                       "if all cases remain kernel, policy load did not enable the needed domain handoff path")
        hal_exec = next((case for case in cases if case["context"] == "u:r:hal_wifi_default:s0" and case["attr_mode"] == "exec"), None)
        if hal_exec is not None:
            base.add_check(checks, "hal-wifi-exec-postexec", "pass" if hal_exec["postexec_match"] else "gap", "finding",
                           f"postexec_current={hal_exec['postexec_current']} signal={hal_exec['child_signal']} exit={hal_exec['child_exit_code']}",
                           [hal_exec["file"]], "HAL registration should wait until the Wi-Fi HAL domain handoff path is proven")
    if postflight is not None:
        base.add_check(checks, "postflight-clean", "pass" if postflight["clean"] else "blocked", "blocker",
                       f"processes={len(postflight['processes'])} wifi_links={len(postflight['wifi_links'])}",
                       postflight["processes"][:6] + postflight["wifi_links"][:6],
                       "cleanup/reboot before further Wi-Fi work")
    return checks


def blockers(checks: list[base.Check], ignore_approval: bool = False) -> list[str]:
    blocked: list[str] = []
    for check in checks:
        if check.severity == "blocker" and check.status != "pass":
            blocked.append(check.name)
        if check.severity == "approval" and check.status != "pass" and not ignore_approval:
            blocked.append(check.name)
    return blocked


def run_case(args: argparse.Namespace,
             store: base.EvidenceStore,
             context: str,
             attr_mode: str) -> dict[str, Any]:
    name = f"run-{context.replace(':', '_')}-{attr_mode}"
    step = base.run_capture(args, store, name, helper_command(args, context, attr_mode), timeout=args.timeout + 20.0)
    text = base.read_step(step)
    keys = base.parse_keys(text)
    return {
        "context": context,
        "attr_mode": attr_mode,
        "step": asdict(step),
        "file": step.file,
        "result": keys.get("selinux_domain_proof.result", ""),
        "reason": keys.get("selinux_domain_proof.reason", ""),
        "write_current_ok": keys.get("selinux_domain_proof.write_current.ok", ""),
        "verify_current_match": keys.get("selinux_domain_proof.verify_current.match", ""),
        "write_exec_ok": keys.get("selinux_domain_proof.write_exec.ok", ""),
        "verify_exec_match": keys.get("selinux_domain_proof.verify_exec.match", ""),
        "postexec_current": keys.get("selinux_domain_proof.postexec.current", ""),
        "postexec_exit_code": keys.get("selinux_domain_proof.postexec.exit_code", ""),
        "postexec_signal": keys.get("selinux_domain_proof.postexec.signal", ""),
        "postexec_match": keys.get("selinux_domain_proof.postexec.match") == "1",
        "child_exit_code": keys.get("child_exit_code", ""),
        "child_signal": keys.get("child_signal", ""),
        "keys": keys,
    }


def decide(args: argparse.Namespace,
           checks: list[base.Check],
           cases: list[dict[str, Any]] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v491-post-load-domain-proof-plan-ready", True, "plan-only; no device command executed", "run V490 first, then preflight V491 with the V490 pass manifest"
    pre_run_blockers = blockers(
        checks,
        ignore_approval=args.command == "preflight" or (args.command == "run" and approved(args)),
    )
    if args.command == "preflight":
        if pre_run_blockers:
            return "v491-post-load-domain-proof-blocked", False, "blocked before run by " + ", ".join(pre_run_blockers), "resolve blockers before V491 run"
        return "v491-post-load-domain-proof-preflight-ready", True, "preflight passed; run still needs exact approval", "run approved post-load domain proof matrix"
    if not approved(args):
        return "v491-post-load-domain-proof-approval-required", False, "missing exact approval phrase or apply flags", "rerun with exact V491 approval"
    if pre_run_blockers:
        return "v491-post-load-domain-proof-blocked", False, "blocked before run by " + ", ".join(pre_run_blockers), "resolve blockers before retry"
    if cases and any(case["postexec_match"] for case in cases):
        return "v491-post-load-domain-handoff-present", True, "at least one requested domain survived static re-exec after policy load", "try service-manager/HAL registration with the passing domain path only"
    return "v491-post-load-domain-kernel-stuck", True, "post-load static re-exec/current proof still reports kernel for requested Android domains", "policy-load alone did not solve the native-init domain handoff blocker"


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [
            case["context"],
            case["attr_mode"],
            case["result"],
            str(case["postexec_match"]),
            case["postexec_current"],
            case["postexec_exit_code"] or case["postexec_signal"],
        ]
        for case in manifest.get("cases", [])
    ]
    checks = [[check["name"], check["status"], check["severity"], check["detail"]] for check in manifest["checks"]]
    return "\n".join([
        "# V491 Post-Load SELinux Domain Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        "",
        "## V490 Precondition",
        "",
        base.markdown_table(["item", "value"], [
            ["manifest", manifest["v490"]["path"]],
            ["valid", str(manifest["v490"]["valid"])],
            ["decision", manifest["v490"]["decision"]],
            ["policy_load_executed", str(manifest["v490"]["policy_load_executed"])],
        ]),
        "",
        "## Cases",
        "",
        base.markdown_table(["context", "attr_mode", "result", "postexec_match", "postexec_current", "exit_or_signal"], rows),
        "",
        "## Checks",
        "",
        base.markdown_table(["name", "status", "severity", "detail"], checks),
        "",
        "## Safety",
        "",
        "- No policy load is performed by V491.",
        "- No PID1 reexec is performed.",
        "- No daemon/HAL/CNSS process is started.",
        "- No Wi-Fi scan/connect/link-up or external ping is attempted.",
    ])


def build_manifest(args: argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    steps: dict[str, base.Step] = {}
    cases: list[dict[str, Any]] | None = None
    post: dict[str, Any] | None = None
    v490 = load_v490_manifest(args)
    if args.command != "plan":
        steps = preflight(args, store)
    checks = build_checks(args, steps, v490)
    if args.command == "run" and approved(args) and not blockers(checks, ignore_approval=True):
        cases = [
            run_case(args, store, context, attr_mode)
            for context in CONTEXTS
            for attr_mode in ATTR_MODES
        ]
        post = base.postflight(args, store)
        checks = build_checks(args, steps, v490, cases, post)
    decision, pass_ok, reason, next_step = decide(args, checks, cases)
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
            "contexts": list(CONTEXTS),
            "attr_modes": list(ATTR_MODES),
            "static_postexec_probe": "/proc/self/exe --selinux-print-current",
            "requires_v490_policy_load_pass": True,
        },
        "v490": v490,
        "steps": {name: asdict(step) for name, step in steps.items()},
        "cases": cases or [],
        "postflight": post,
        "checks": [asdict(check) for check in checks],
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan",
        "device_mutations": args.command == "run" and approved(args),
        "policy_load_executed": False,
        "init_reexec_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = base.EvidenceStore(args.out_dir)
    manifest = build_manifest(args, store)
    store.write_text("manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"policy_load_executed: {manifest['policy_load_executed']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {args.out_dir.resolve()}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
