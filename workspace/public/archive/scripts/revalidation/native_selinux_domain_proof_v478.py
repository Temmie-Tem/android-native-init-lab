#!/usr/bin/env python3
"""V478 native-init SELinux domain handoff proof.

This runner uses the execns helper's child-only `selinux-domain-proof` mode to
test whether native init can set a future exec context such as
`u:r:hal_wifi_default:s0`. It does not start service-manager, hwservicemanager,
Wi-Fi HAL, CNSS, scan/connect, DHCP, routing, or external ping.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import ProtocolResult, run_cmdv1_command  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402
from a90_kernel_tools import collect_host_metadata, markdown_table  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v478-native-selinux-domain-proof")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_HELPER_SHA256 = "0a0c01c6978fb602e0716b4cd0960272a4257f608844d80b547c519cb6e93224"
DEFAULT_SELINUX_CONTEXT = "u:r:hal_wifi_default:s0"
APPROVAL_PHRASE = (
    "approve v478 native SELinux domain proof only; "
    "no daemon start and no Wi-Fi bring-up"
)


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
    parser.add_argument("--selinux-context", default=DEFAULT_SELINUX_CONTEXT)
    parser.add_argument("--selinux-attr-mode", choices=("current", "exec", "both"), default="exec")
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
    except Exception as exc:  # noqa: BLE001 - evidence should preserve transport failures
        ok = False
        error = str(exc)
        text = error + "\n"
    duration = time.monotonic() - started
    path = store.write_text(f"commands/{name}.txt", text)
    return Step(name, command, ok, rc, status, duration, str(path), error)


def capture_text(step: Step | None) -> str:
    if step is None:
        return ""
    try:
        return Path(step.file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def parse_key_values(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.-]+", key):
            keys[key] = value
    return keys


def postflight_surfaces(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    ps = run_capture(args, store, "post-ps", ["run", args.toybox, "ps", "-A"], timeout=args.timeout)
    netdev = run_capture(args, store, "post-proc-net-dev", ["run", args.toybox, "cat", "/proc/net/dev"], timeout=args.timeout)
    ps_text = capture_text(ps)
    netdev_text = capture_text(netdev)
    managers = [
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
    wifi_links = [
        line.strip()
        for line in netdev_text.splitlines()
        if re.search(r"\b(wlan|wifi|p2p)", line)
    ]
    return {
        "clean": not managers and not wifi_links,
        "processes": managers,
        "wifi_links": wifi_links,
        "steps": [asdict(ps), asdict(netdev)],
    }


def build_helper_argv(args: argparse.Namespace) -> list[str]:
    return [
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
        args.selinux_context,
        "--selinux-attr-mode",
        args.selinux_attr_mode,
        "--timeout-sec",
        "5",
    ]


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "version": "V478",
        "goal": "prove whether native init can hand off to the Android SELinux domain needed by Wi-Fi HAL",
        "helper": args.helper,
        "helper_version": "a90_android_execns_probe v41",
        "helper_mode": "selinux-domain-proof",
        "target_context": args.selinux_context,
        "attr_mode": args.selinux_attr_mode,
        "executes": [
            "private helper namespace setup",
            "child-only write to /proc/self/attr/<mode>",
            "postflight process/link cleanup check",
        ],
        "blocked_actions": [
            "service-manager start",
            "hwservicemanager start",
            "Wi-Fi HAL start",
            "CNSS start",
            "scan/connect",
            "credential read",
            "DHCP/routing/external ping",
        ],
    }


def add_check(checks: list[Check], name: str, status: str, severity: str,
              detail: str, evidence: list[str], next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, evidence, next_step))


def build_checks(args: argparse.Namespace, steps: dict[str, Step],
                 run_keys: dict[str, str] | None, postflight: dict[str, Any] | None) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight")
        return checks

    version = capture_text(steps.get("version"))
    status = capture_text(steps.get("status"))
    helper_sha = capture_text(steps.get("helper-sha"))
    helper_usage = capture_text(steps.get("helper-usage"))
    ps = capture_text(steps.get("ps"))
    netdev = capture_text(steps.get("proc-net-dev"))

    process_hits = [
        line.strip()
        for line in ps.splitlines()
        if any(token in line for token in ("servicemanager", "hwservicemanager", "wifi@", "cnss-daemon"))
    ]
    wifi_links = [line.strip() for line in netdev.splitlines() if re.search(r"\b(wlan|wifi|p2p)", line)]

    add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning",
              f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3],
              "refresh expected version if native image intentionally changed")
    add_check(checks, "native-clean", "pass" if "fail=0" in status else "blocked", "blocker",
              "status/selftest should report fail=0", [line for line in status.splitlines() if "selftest:" in line][:2],
              "fix native health before SELinux proof")
    helper_ready = (
        args.helper_sha256 in helper_sha
        and "a90_android_execns_probe v41" in helper_usage
        and "selinux-domain-proof" in helper_usage
    )
    add_check(checks, "helper-v41", "pass" if helper_ready else "blocked", "blocker",
              f"sha_match={args.helper_sha256 in helper_sha} marker={'a90_android_execns_probe v41' in helper_usage} mode={'selinux-domain-proof' in helper_usage}",
              [line for line in helper_sha.splitlines() if args.helper in line][:2],
              "deploy helper v41 before V478 run")
    add_check(checks, "service-surface-clean", "pass" if not process_hits else "blocked", "blocker",
              f"process_count={len(process_hits)}", process_hits[:8],
              "do not run proof over active manager/HAL/CNSS process")
    add_check(checks, "wifi-link-clean", "pass" if not wifi_links else "blocked", "blocker",
              f"wifi_link_count={len(wifi_links)}", wifi_links[:8],
              "do not run proof while Wi-Fi link is active")
    add_check(checks, "approval-gate", "pass" if approved(args) else "needs-operator", "approval",
              f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
              [APPROVAL_PHRASE],
              "exact phrase required before child-only SELinux attr write")

    if args.command == "run" and run_keys is not None:
        result = run_keys.get("selinux_domain_proof.result", "")
        write_exec_ok = run_keys.get("selinux_domain_proof.write_exec.ok", "")
        write_current_ok = run_keys.get("selinux_domain_proof.write_current.ok", "")
        requested_ok = write_exec_ok == "1" or write_current_ok == "1"
        add_check(checks, "selinux-domain-write", "pass" if result.endswith("-pass") and requested_ok else "blocked", "blocker",
                  f"result={result} write_exec={write_exec_ok or '-'} write_current={write_current_ok or '-'}",
                  [],
                  "if blocked, native init cannot directly hand off into Android Wi-Fi SELinux domain")
    if postflight is not None:
        add_check(checks, "postflight-clean", "pass" if postflight.get("clean") else "blocked", "blocker",
                  f"processes={len(postflight.get('processes', []))} wifi_links={len(postflight.get('wifi_links', []))}",
                  list(postflight.get("processes", []))[:6] + list(postflight.get("wifi_links", []))[:6],
                  "cleanup residual processes/links before next Wi-Fi gate")
    return checks


def blockers(checks: list[Check], *, ignore_approval: bool = False) -> list[str]:
    result: list[str] = []
    for check in checks:
        if check.severity == "blocker" and check.status != "pass":
            result.append(check.name)
        if check.severity == "approval" and check.status != "pass" and not ignore_approval:
            result.append(check.name)
    return result


def decide(args: argparse.Namespace, checks: list[Check], run_keys: dict[str, str] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v478-native-selinux-domain-proof-plan-ready", True, "plan-only; no live command executed", "run preflight"
    pre_run_blockers = blockers(checks, ignore_approval=args.command == "run" and approved(args))
    if args.command == "preflight":
        if pre_run_blockers:
            return "v478-native-selinux-domain-proof-blocked", False, "blocked before run by " + ", ".join(pre_run_blockers), "resolve blockers before V478 run"
        return "v478-native-selinux-domain-proof-preflight-ready", True, "preflight passed; child-only SELinux proof still requires exact approval", "run approved V478 proof"
    if not approved(args):
        return "v478-native-selinux-domain-proof-approval-required", False, "missing exact approval phrase or apply flags", "rerun with exact V478 approval"
    if pre_run_blockers:
        return "v478-native-selinux-domain-proof-blocked", False, "blocked before run by " + ", ".join(pre_run_blockers), "resolve blockers before retry"
    if run_keys and run_keys.get("selinux_domain_proof.result") == "selinux-domain-setcon-proof-pass":
        return "v478-native-selinux-domain-proof-pass", True, "native child accepted requested SELinux exec/current context handoff", "rerun Samsung HAL registration with helper context handoff"
    return "v478-native-selinux-domain-proof-blocked", True, "native child could not set requested SELinux domain", "treat SELinux domain handoff as current Wi-Fi HAL registration blocker"


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [
        [check["name"], check["status"], check["severity"], check["detail"]]
        for check in manifest["checks"]
    ]
    return "\n".join([
        "# V478 Native SELinux Domain Proof",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Scope",
        "",
        "- Starts no daemon and performs no Wi-Fi scan/connect/link-up.",
        "- Writes only child-local `/proc/self/attr/<mode>` in the proof child.",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail"], checks),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    steps: dict[str, Step] = {}
    live_step: Step | None = None
    live_keys: dict[str, str] | None = None
    postflight: dict[str, Any] | None = None

    if args.command != "plan":
        for name, command, timeout in (
            ("version", ["version"], args.timeout),
            ("status", ["status"], args.timeout),
            ("helper-sha", ["run", args.toybox, "sha256sum", args.helper], args.timeout),
            ("helper-usage", ["run", args.helper, "--help"], args.timeout),
            ("ps", ["run", args.toybox, "ps", "-A"], args.timeout),
            ("proc-net-dev", ["run", args.toybox, "cat", "/proc/net/dev"], args.timeout),
        ):
            steps[name] = run_capture(args, store, name, command, timeout=timeout)

    initial_checks = build_checks(args, steps, None, None)
    if args.command == "run" and approved(args) and not blockers(initial_checks, ignore_approval=True):
        helper_argv = build_helper_argv(args)
        live_step = run_capture(args, store, "selinux-domain-proof", ["run", *helper_argv], timeout=args.timeout)
        live_keys = parse_key_values(capture_text(live_step))
        postflight = postflight_surfaces(args, store)

    checks = build_checks(args, steps, live_keys, postflight)
    decision, pass_ok, reason, next_step = decide(args, checks, live_keys)
    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "host": collect_host_metadata(),
        "plan": build_plan(args),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credentials_read": False,
        "external_ping_executed": False,
        "steps": {name: asdict(step) for name, step in steps.items()},
        "live_step": asdict(live_step) if live_step else None,
        "live_keys": live_keys or {},
        "postflight": postflight,
        "checks": [asdict(check) for check in checks],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(json.dumps({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "manifest": str(store.path("manifest.json")),
    }, ensure_ascii=False, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
