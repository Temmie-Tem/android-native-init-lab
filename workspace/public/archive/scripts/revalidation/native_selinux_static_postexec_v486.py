#!/usr/bin/env python3
"""V486 native SELinux static post-exec handoff matrix.

This runner uses `a90_android_execns_probe v44` in `selinux-domain-proof` mode.
Unlike V478's dynamic toybox post-exec check, v44 re-execs the static helper via
`/proc/self/exe --selinux-print-current`, so the result isolates SELinux exec
handoff without depending on Android linker/toybox startup.

No service-manager, hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, DHCP,
routing, credential read, or external ping is executed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import ProtocolResult, run_cmdv1_command  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402
from a90_kernel_tools import collect_host_metadata, markdown_table  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v486-native-selinux-static-postexec")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_HELPER_SHA256 = "150630c088dda1e53173021575420a996cf395ded049bfdf0ab26e71dd4c38c9"
APPROVAL_PHRASE = (
    "approve v486 native SELinux static postexec proof only; "
    "no daemon start and no Wi-Fi bring-up"
)
CONTEXTS = (
    "u:r:hal_wifi_default:s0",
    "u:r:servicemanager:s0",
    "u:r:hwservicemanager:s0",
)
ATTR_MODES = ("exec", "both")


@dataclass
class Step:
    name: str
    command: list[str]
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str = ""


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


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
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"))
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def run_capture(args: argparse.Namespace, store: EvidenceStore, name: str,
                command: list[str], timeout: float | None = None) -> Step:
    started = time.monotonic()
    text = ""
    error = ""
    rc: int | None = None
    status = "missing"
    try:
        result: ProtocolResult = run_cmdv1_command(
            args.host,
            args.port,
            timeout if timeout is not None else args.timeout,
            command,
            retry_unsafe=False,
        )
        text = result.text
        rc = result.rc
        status = result.status
        ok = result.rc == 0 and result.status == "ok"
    except Exception as exc:  # noqa: BLE001 - preserve transport evidence
        ok = False
        error = str(exc)
        text = error + "\n"
    duration = time.monotonic() - started
    path = store.write_text(f"commands/{name}.txt", text)
    return Step(name, command, ok, rc, status, duration, str(path), error)


def read_step(step: Step | None) -> str:
    if step is None:
        return ""
    return Path(step.file).read_text(encoding="utf-8", errors="replace")


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.-]+", key):
            keys[key] = value
    return keys


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


def add_check(checks: list[Check], name: str, status: str, severity: str,
              detail: str, evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def preflight(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Step]:
    return {
        "version": run_capture(args, store, "version", ["version"], args.timeout),
        "status": run_capture(args, store, "status", ["status"], args.timeout),
        "ps": run_capture(args, store, "ps", ["run", args.toybox, "ps", "-A"], args.timeout),
        "netdev": run_capture(args, store, "proc-net-dev", ["run", args.toybox, "cat", "/proc/net/dev"], args.timeout),
        "helper-sha": run_capture(args, store, "helper-sha", ["run", args.toybox, "sha256sum", args.helper], args.timeout),
        "helper-usage": run_capture(args, store, "helper-usage", ["run", args.helper], args.timeout),
    }


def build_checks(args: argparse.Namespace, steps: dict[str, Step],
                 cases: list[dict[str, Any]] | None = None,
                 postflight: dict[str, Any] | None = None) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed")
        return checks
    version = read_step(steps.get("version"))
    status = read_step(steps.get("status"))
    ps = read_step(steps.get("ps"))
    netdev = read_step(steps.get("netdev"))
    helper_sha = read_step(steps.get("helper-sha"))
    helper_usage = read_step(steps.get("helper-usage"))
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

    add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning",
              f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3])
    add_check(checks, "native-clean", "pass" if "fail=0" in status else "blocked", "blocker",
              "status/selftest fail=0 expected", [line for line in status.splitlines() if "selftest:" in line][:2],
              "fix native runtime before SELinux proof")
    helper_ready = (
        args.helper_sha256 in helper_sha
        and "a90_android_execns_probe v44" in helper_usage
        and "selinux-domain-proof" in helper_usage
        and "--selinux-print-current" in helper_usage
    )
    add_check(checks, "helper-v44", "pass" if helper_ready else "blocked", "blocker",
              f"sha_match={args.helper_sha256 in helper_sha} marker={'a90_android_execns_probe v44' in helper_usage} static_probe={'--selinux-print-current' in helper_usage}",
              [line for line in helper_sha.splitlines() if args.helper in line][:2],
              "deploy helper v44 before V486 run")
    add_check(checks, "process-surface-clean", "pass" if not process_hits else "blocked", "blocker",
              f"process_count={len(process_hits)}", process_hits[:8],
              "do not run proof over existing manager/HAL/CNSS process")
    add_check(checks, "wifi-link-clean", "pass" if not wifi_links else "blocked", "blocker",
              f"wifi_link_count={len(wifi_links)}", wifi_links[:8],
              "do not run proof while Wi-Fi link is active")
    add_check(checks, "approval-gate", "pass" if approved(args) else "needs-operator", "approval",
              f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
              [APPROVAL_PHRASE], "exact approval required before child-local SELinux attr writes")
    if cases is not None:
        any_match = any(case["postexec_match"] for case in cases)
        add_check(checks, "static-postexec-match", "pass" if any_match else "gap", "finding",
                  f"matching_cases={sum(1 for case in cases if case['postexec_match'])}/{len(cases)}",
                  [f"{case['context']} {case['attr_mode']} match={case['postexec_match']} current={case['postexec_current']}" for case in cases],
                  "if all cases remain kernel, SELinux domain handoff is blocked before HAL registration")
        hal_exec = next((case for case in cases if case["context"] == "u:r:hal_wifi_default:s0" and case["attr_mode"] == "exec"), None)
        if hal_exec is not None:
            add_check(checks, "hal-wifi-exec-postexec", "pass" if hal_exec["postexec_match"] else "gap", "finding",
                      f"postexec_current={hal_exec['postexec_current']} signal={hal_exec['child_signal']} exit={hal_exec['child_exit_code']}",
                      [hal_exec["file"]], "fix or route around SELinux domain handoff before HAL connect work")
    if postflight is not None:
        add_check(checks, "postflight-clean", "pass" if postflight["clean"] else "blocked", "blocker",
                  f"processes={len(postflight['processes'])} wifi_links={len(postflight['wifi_links'])}",
                  postflight["processes"][:6] + postflight["wifi_links"][:6],
                  "cleanup/reboot before further Wi-Fi work")
    return checks


def blockers(checks: list[Check], ignore_approval: bool = False) -> list[str]:
    blocked: list[str] = []
    for check in checks:
        if check.severity == "blocker" and check.status != "pass":
            blocked.append(check.name)
        if check.severity == "approval" and check.status != "pass" and not ignore_approval:
            blocked.append(check.name)
    return blocked


def run_case(args: argparse.Namespace, store: EvidenceStore, context: str, attr_mode: str) -> dict[str, Any]:
    name = f"run-{context.replace(':', '_')}-{attr_mode}"
    step = run_capture(args, store, name, helper_command(args, context, attr_mode), timeout=args.timeout + 20.0)
    text = read_step(step)
    keys = parse_keys(text)
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


def postflight(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    ps = run_capture(args, store, "post-ps", ["run", args.toybox, "ps", "-A"], args.timeout)
    netdev = run_capture(args, store, "post-proc-net-dev", ["run", args.toybox, "cat", "/proc/net/dev"], args.timeout)
    ps_text = read_step(ps)
    netdev_text = read_step(netdev)
    processes = [
        line.strip()
        for line in ps_text.splitlines()
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
    wifi_links = [line.strip() for line in netdev_text.splitlines() if re.search(r"\b(wlan|wifi|p2p)", line)]
    return {
        "clean": not processes and not wifi_links,
        "processes": processes,
        "wifi_links": wifi_links,
        "steps": [asdict(ps), asdict(netdev)],
    }


def decide(args: argparse.Namespace, checks: list[Check], cases: list[dict[str, Any]] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v486-selinux-static-postexec-plan-ready", True, "plan-only; no device command executed", "deploy v44 and run preflight"
    pre_run_blockers = blockers(
        checks,
        ignore_approval=args.command == "preflight" or (args.command == "run" and approved(args)),
    )
    if args.command == "preflight":
        if pre_run_blockers:
            return "v486-selinux-static-postexec-blocked", False, "blocked before run by " + ", ".join(pre_run_blockers), "resolve blockers before V486 run"
        return "v486-selinux-static-postexec-preflight-ready", True, "preflight passed; run still needs exact approval", "run approved static postexec matrix"
    if not approved(args):
        return "v486-selinux-static-postexec-approval-required", False, "missing exact approval phrase or apply flags", "rerun with exact V486 approval"
    if pre_run_blockers:
        return "v486-selinux-static-postexec-blocked", False, "blocked before run by " + ", ".join(pre_run_blockers), "resolve blockers before retry"
    if cases and any(case["postexec_match"] for case in cases):
        return "v486-selinux-static-postexec-handoff-present", True, "at least one requested domain survived static re-exec", "try HAL registration with the passing domain path only"
    return "v486-selinux-static-postexec-kernel-stuck", True, "static re-exec still reports kernel for requested Android domains", "treat SELinux domain handoff as the primary Wi-Fi HAL registration blocker"


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
    return "\n".join(
        [
            "# V486 Native SELinux Static Postexec Matrix",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            "## Cases",
            "",
            markdown_table(["context", "attr_mode", "result", "postexec_match", "postexec_current", "exit_or_signal"], rows),
            "",
            "## Checks",
            "",
            markdown_table(["name", "status", "severity", "detail"], checks),
            "",
            "## Safety",
            "",
            "- No daemon/HAL/CNSS process is started.",
            "- No Wi-Fi scan/connect/link-up or external ping is attempted.",
        ]
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: dict[str, Step] = {}
    cases: list[dict[str, Any]] | None = None
    post: dict[str, Any] | None = None
    if args.command != "plan":
        steps = preflight(args, store)
    checks = build_checks(args, steps)
    if args.command == "run" and approved(args) and not blockers(checks, ignore_approval=True):
        cases = [
            run_case(args, store, context, attr_mode)
            for context in CONTEXTS
            for attr_mode in ATTR_MODES
        ]
        post = postflight(args, store)
        checks = build_checks(args, steps, cases, post)
    decision, pass_ok, reason, next_step = decide(args, checks, cases)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "plan": {
            "helper": args.helper,
            "helper_version": "a90_android_execns_probe v44",
            "helper_sha256": args.helper_sha256,
            "contexts": list(CONTEXTS),
            "attr_modes": list(ATTR_MODES),
            "static_postexec_probe": "/proc/self/exe --selinux-print-current",
        },
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
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    manifest = build_manifest(args, store)
    store.write_text("manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {args.out_dir.resolve()}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
