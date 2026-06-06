#!/usr/bin/env python3
"""V503 dual-HAL IWifi.start surface proof.

This bounded proof starts the private Android service-manager surface, both
legacy and Samsung Wi-Fi HAL daemons, and CNSS in the same helper-owned
namespace before querying `android.hardware.wifi@1.0::IWifi/default` and
calling `IWifi.start()` only if the service handle is non-null.

It does not read credentials, scan, connect, request DHCP, change routes, ping
externally, start supplicant/wificond/hostapd, or persist any Android service.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v503-dual-hal-iwifi-surface")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "434dd15f47eabdb2a418f79cdcfb03765de6e6e8d3af18cff7cf1f5ba47126cf"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v53"
DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
APPROVAL_PHRASE = (
    "approve v503 dual-HAL IWifi.start surface proof only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)
HELPER_MODE = "wifi-dual-hal-iwifi-start-surface"
KEY_RE = re.compile(r"^(wifi_hal_composite_start|iwifi_start|wifi_surface_composite)\.([A-Za-z0-9_.-]+)=(.*)$")
PROCESS_RE = re.compile(r"\b(servicemanager|hwservicemanager|vndservicemanager|wificond|supplicant|hostapd|cnss-daemon|cnss_diag|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b", re.IGNORECASE)
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wifi-aware\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--property-root", default=DEFAULT_PROPERTY_ROOT)
    parser.add_argument("--max-runtime-sec", type=int, default=8)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    return item


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def preflight_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    return [
        run_step(args, store, "version", ["version"], 15.0),
        run_step(args, store, "status", ["status"], 20.0),
        run_step(args, store, "selftest", ["selftest"], 20.0),
        run_step(args, store, "sha-helper", ["run", "/cache/bin/toybox", "sha256sum", args.helper], 20.0),
        run_step(args, store, "helper-usage", ["run", args.helper, "--help"], 20.0),
        run_step(args, store, "ps", ["run", "/cache/bin/toybox", "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
        run_step(args, store, "proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
        run_step(args, store, "sys-class-net", ["ls", "/sys/class/net"], 10.0),
        run_step(args, store, "sys-class-ieee80211", ["ls", "/sys/class/ieee80211"], 10.0),
    ]


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace, steps: list[dict[str, Any]]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight")
        return checks

    version = step_payload(steps, "version")
    status = step_payload(steps, "status")
    selftest = step_payload(steps, "selftest")
    helper_sha = step_payload(steps, "sha-helper")
    helper_usage = step_payload(steps, "helper-usage")
    ps = step_payload(steps, "ps")
    netdev = step_payload(steps, "proc-net-dev")
    sys_net = step_payload(steps, "sys-class-net")
    sys_ieee = step_payload(steps, "sys-class-ieee80211")
    process_hits = [line.strip() for line in ps.splitlines() if PROCESS_RE.search(line)]
    wifi_hits = [
        line.strip()
        for line in (netdev + "\n" + sys_net + "\n" + sys_ieee).splitlines()
        if WIFI_RE.search(line)
    ]
    helper_ready = (
        args.helper_sha256 in helper_sha
        and args.helper_marker in helper_usage
        and HELPER_MODE in helper_usage
    )

    add_check(checks, "native-clean", "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker", f"expect_version={args.expect_version}", [], "restore native health before V503")
    add_check(checks, "helper-dual-hal", "pass" if helper_ready else "blocked", "blocker", f"marker={args.helper_marker} sha_match={args.helper_sha256 in helper_sha} dual_mode={HELPER_MODE in helper_usage}", [line for line in helper_sha.splitlines() if args.helper in line][:2], "deploy expected helper before this proof")
    add_check(checks, "process-surface-clean", "pass" if not process_hits else "blocked", "blocker", f"process_count={len(process_hits)}", process_hits[:8], "do not run dual-HAL proof over active manager/HAL/CNSS processes")
    add_check(checks, "wifi-link-clean", "pass" if not wifi_hits else "blocked", "blocker", f"wifi_hit_count={len(wifi_hits)}", wifi_hits[:8], "do not run dual-HAL proof while Wi-Fi link is active")
    add_check(checks, "approval-gate", "pass" if approved(args) else "needs-operator", "approval", f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}", [APPROVAL_PHRASE], "exact phrase required for bounded dual-HAL run")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def helper_command(args: argparse.Namespace) -> list[str]:
    command = [
        "run",
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        HELPER_MODE,
        "--target-profile",
        "vendor-wifi-hal-legacy",
        "--null-device-mode",
        "dev-null-selinux",
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        "/cache/bin/a90_real_ld.config.txt",
        "--apex-libraries-source",
        "/cache/bin/a90_real_apex.libraries.config.txt",
        "--property-root",
        args.property_root,
        "--timeout-sec",
        str(args.max_runtime_sec),
    ]
    if approved(args):
        command.extend([
            "--allow-service-manager-start-only",
            "--allow-wifi-hal-start-only",
            "--allow-cnss-start-only",
            "--allow-iwifi-start-only",
        ])
    return command


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            keys[f"{match.group(1)}.{match.group(2)}"] = match.group(3).strip()
    return keys


def run_live(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    record = run_capture(args, "run-dual-hal-iwifi-surface", helper_command(args), timeout=args.timeout + args.max_runtime_sec + 70.0)
    text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
    rel = write_capture(store, "run-dual-hal-iwifi-surface", text)
    keys = parse_keys(text)
    return {
        "capture": capture_to_manifest(record),
        "file": rel,
        "keys": keys,
        "helper_result": keys.get("wifi_hal_composite_start.result", "missing"),
        "helper_reason": keys.get("wifi_hal_composite_start.reason", ""),
        "iwifi_result": keys.get("iwifi_start.result", "missing"),
        "iwifi_start_transaction_ok": keys.get("iwifi_start.start_transaction_ok") == "1",
        "service_handle_found": keys.get("iwifi_start.service_handle_found") == "1",
        "service_null": keys.get("iwifi_start.service_null") == "1" or keys.get("iwifi_start.result") == "service-null",
        "dual_hal": keys.get("wifi_hal_composite_start.dual_hal") == "1",
        "legacy_observable": keys.get("wifi_hal_composite_start.child.wifi_hal_legacy.observable") == "1",
        "ext_observable": keys.get("wifi_hal_composite_start.child.wifi_hal_ext.observable") == "1",
        "cnss_observable": keys.get("wifi_hal_composite_start.child.cnss_daemon.observable") == "1",
        "wlan_during_count": keys.get("wifi_surface_composite.during.wlan_count", "0"),
        "phy_during_count": keys.get("wifi_surface_composite.during.phy_count", "0"),
        "wlan_after_cleanup_count": keys.get("wifi_surface_composite.after_cleanup.wlan_count", "0"),
        "phy_after_cleanup_count": keys.get("wifi_surface_composite.after_cleanup.phy_count", "0"),
        "all_postflight_safe": keys.get("wifi_hal_composite_start.all_postflight_safe") == "1",
    }


def classify(command: str,
             checks: list[Check],
             live_result: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if command == "plan":
        return "v503-dual-hal-iwifi-surface-plan-ready", True, "plan-only; no device command executed", "run preflight", False
    blocked = blockers(checks)
    if blocked:
        return "v503-dual-hal-iwifi-surface-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before V503 live proof", False
    if command == "preflight":
        return "v503-dual-hal-iwifi-surface-preflight-ready", True, "read-only preflight ready; live run still needs exact approval", "run approved V503 dual-HAL proof", False
    if not approved(args):
        return "v503-dual-hal-iwifi-surface-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V503 approval", False
    if not live_result:
        return "v503-dual-hal-iwifi-surface-review-required", False, "missing live result", "inspect runner failure", True
    if not live_result["all_postflight_safe"]:
        return "v503-dual-hal-iwifi-surface-cleanup-review", False, "helper-owned children were not proven cleaned", "inspect evidence and consider recovery reboot", True
    if live_result["iwifi_start_transaction_ok"]:
        return "v503-dual-hal-iwifi-start-transaction-pass", True, "dual-HAL namespace returned IWifi/default and IWifi.start completed", "advance to scan-only proof with dual-HAL mode", True
    if live_result["service_null"]:
        return "v503-dual-hal-iwifi-service-null", True, "dual-HAL namespace still did not return IWifi/default", "triage Android runtime prerequisites beyond dual HAL daemons", True
    return "v503-dual-hal-iwifi-review-required", False, f"helper_result={live_result['helper_result']} iwifi={live_result['iwifi_result']}", "inspect dual-HAL transcript before widening scope", True


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    live_rows = [[key, str(value)] for key, value in sorted((manifest.get("live_result") or {}).items()) if key != "capture"]
    return "\n".join([
        "# V503 Dual-HAL IWifi.start Surface Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Live Result",
        "",
        markdown_table(["key", "value"], live_rows) if live_rows else "- none",
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps = [] if args.command == "plan" else preflight_steps(args, store)
    checks = build_checks(args, steps)
    live_result = None
    device_mutations = False
    if args.command == "run" and approved(args) and not blockers(checks):
        live_result = run_live(args, store)
        device_mutations = True
    decision, pass_ok, reason, next_step, live_executed = classify(args.command, checks, live_result)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "steps": steps,
        "checks": [asdict(check) for check in checks],
        "live_result": live_result,
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan" or live_executed,
        "device_mutations": device_mutations,
        "daemon_start_executed": live_executed,
        "wifi_hal_start_executed": live_executed,
        "credentials_read": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    return manifest


def main() -> int:
    global args
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
