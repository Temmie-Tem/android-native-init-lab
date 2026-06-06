#!/usr/bin/env python3
"""V508 bounded boot_wlan materialization proof.

This runner uses the fixed-target `/cache/bin/a90_wlanbootctl` helper to write
`1` to `/sys/kernel/boot_wlan/boot_wlan` and observe whether the stock WLAN
driver materializes `wlan0`, wiphy, qcwlanstate, or `/dev/wlan` surfaces.

It does not start Wi-Fi HAL/CNSS/wificond/supplicant/hostapd, scan, connect,
read credentials, run DHCP, change routes, ping externally, or persist an
Android service.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v508-wlan-boot-materialize")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_HELPER = "/cache/bin/a90_wlanbootctl"
DEFAULT_HELPER_SHA256 = "2c97fe349c0a4543de93a88ca9fbd3704005573be4a9ff75c33a02f5d1f10f6d"
DEFAULT_TOYBOX = "/cache/bin/toybox"
APPROVAL_PHRASE = (
    "approve v508 boot_wlan materialization proof only; "
    "no scan/connect/link-up and no external ping"
)
PROCESS_RE = re.compile(
    r"\b(servicemanager|hwservicemanager|vndservicemanager|wificond|supplicant|hostapd|"
    r"cnss-daemon|cnss_diag|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b",
    re.IGNORECASE,
)
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wifi-aware\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
DMESG_FOCUS_RE = re.compile(
    r"(boot_wlan|qcwlanstate|wlan|wifi|wiphy|cnss|icnss|qca|qcacld|firmware|bdf|bdwlan|"
    r"regdb|nl80211|cfg80211|wlfw|qmi|pdr|ssr)",
    re.IGNORECASE,
)


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
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--observe-sec", type=int, default=20)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"))
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
        run_step(args, store, "status", ["status"], 25.0),
        run_step(args, store, "selftest", ["selftest"], 25.0),
        run_step(args, store, "sha-helper", ["run", args.toybox, "sha256sum", args.helper], 20.0),
        run_step(args, store, "helper-usage", ["run", args.helper], 20.0),
        run_step(args, store, "helper-status", ["run", args.helper, "status"], 25.0),
        run_step(args, store, "ps", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
        run_step(args, store, "proc-devices", ["run", args.toybox, "cat", "/proc/devices"], 20.0),
        run_step(args, store, "proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
        run_step(args, store, "sys-class-net", ["ls", "/sys/class/net"], 10.0),
        run_step(args, store, "sys-class-ieee80211", ["ls", "/sys/class/ieee80211"], 10.0),
        run_step(args, store, "qcwlanstate", ["cat", "/sys/wifi/qcwlanstate"], 10.0),
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
    helper_status = step_payload(steps, "helper-status")
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
        and "a90_wlanbootctl v1" in helper_usage
        and "wlanboot.status.begin=1" in helper_status
        and "wlanboot.status.boot_wlan.exists=1" in helper_status
    )

    add_check(checks, "native-clean", "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker",
              f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3], "restore native health before V508")
    add_check(checks, "helper-wlanbootctl", "pass" if helper_ready else "blocked", "blocker",
              f"sha_match={args.helper_sha256 in helper_sha} usage={'a90_wlanbootctl v1' in helper_usage} boot_node={'wlanboot.status.boot_wlan.exists=1' in helper_status}",
              [line for line in helper_sha.splitlines() if args.helper in line][:2], "deploy /cache/bin/a90_wlanbootctl before V508 run")
    add_check(checks, "process-surface-clean", "pass" if not process_hits else "blocked", "blocker",
              f"process_count={len(process_hits)}", process_hits[:8], "do not run boot_wlan proof over active Android Wi-Fi service processes")
    add_check(checks, "wifi-link-clean", "pass" if not wifi_hits else "blocked", "blocker",
              f"wifi_hit_count={len(wifi_hits)}", wifi_hits[:8], "do not run V508 if Wi-Fi link is already active")
    add_check(checks, "approval-gate", "pass" if approved(args) else "needs-operator", "approval",
              f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
              [APPROVAL_PHRASE], "exact phrase required before fixed boot_wlan write")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def int_value(value: str | None) -> int:
    try:
        return int(value or "0")
    except ValueError:
        return 0


def dmesg_focus(text: str, limit: int = 160) -> list[str]:
    lines = []
    for line in text.splitlines():
        if DMESG_FOCUS_RE.search(line):
            lines.append(line.strip())
    return lines[-limit:]


def run_live(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    dmesg_before = run_step(args, store, "dmesg-before", ["run", args.toybox, "dmesg"], timeout=45.0)
    record = run_step(
        args,
        store,
        "run-wlanboot-boot-observe",
        ["run", args.helper, "boot-observe", str(args.observe_sec)],
        timeout=args.timeout + args.observe_sec + 30.0,
    )
    dmesg_after = run_step(args, store, "dmesg-after", ["run", args.toybox, "dmesg"], timeout=60.0)
    post_status = run_step(args, store, "post-status", ["status"], timeout=25.0)
    post_selftest = run_step(args, store, "post-selftest", ["selftest"], timeout=25.0)
    text = str(record.get("payload") or "")
    keys = parse_keys(text)
    surface_keys = {
        "wlan0": keys.get("wlanboot.after.sys_class_net_wlan0.exists") == "1" or keys.get("wlanboot.after.proc_net_dev.wlan_present") == "1",
        "swlan0": keys.get("wlanboot.after.sys_class_net_swlan0.exists") == "1",
        "dev_wlan": keys.get("wlanboot.after.dev_wlan.exists") == "1",
        "qcwlanstate_char": keys.get("wlanboot.after.proc_devices.qcwlanstate_present") == "1",
        "wiphy": int_value(keys.get("wlanboot.after.sys_class_ieee80211.count")) > 0,
        "wifi_dir": int_value(keys.get("wlanboot.after.sys_class_net_wifi.count")) > 0,
        "qcwlanstate_on": "ON" in keys.get("wlanboot.after.qcwlanstate.value", ""),
    }
    return {
        "capture": record,
        "keys": keys,
        "boot_write_rc": keys.get("wlanboot.boot_wlan.write_rc", ""),
        "boot_write_errno": keys.get("wlanboot.boot_wlan.write_errno", ""),
        "helper_result": keys.get("wlanboot.result", "missing"),
        "surface": surface_keys,
        "materialized": any(surface_keys.values()),
        "dmesg_before_file": dmesg_before["file"],
        "dmesg_after_file": dmesg_after["file"],
        "dmesg_focus_after": dmesg_focus(str(dmesg_after.get("payload") or "")),
        "post_status_ok": bool(post_status.get("ok")),
        "post_selftest_ok": bool(post_selftest.get("ok")),
        "post_selftest_text": str(post_selftest.get("payload") or "").strip()[:400],
    }


def classify(command: str,
             checks: list[Check],
             live_result: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if command == "plan":
        return "v508-wlan-boot-materialize-plan-ready", True, "plan-only; no device command executed", "deploy helper, preflight, then run approved V508 proof", False
    blocked = blockers(checks)
    if blocked:
        return "v508-wlan-boot-materialize-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before fixed boot_wlan write", False
    if command == "preflight":
        return "v508-wlan-boot-materialize-preflight-ready", True, "read-only preflight ready; live run still needs exact approval", "run approved V508 proof", False
    if not live_result:
        return "v508-wlan-boot-materialize-review-required", False, "missing live result", "inspect runner failure", True
    if live_result.get("boot_write_rc") != "0":
        return "v508-wlan-boot-materialize-write-failed", False, f"boot_wlan write failed errno={live_result.get('boot_write_errno')}", "inspect helper transcript and kernel logs", True
    if not live_result.get("post_status_ok") or not live_result.get("post_selftest_ok"):
        return "v508-wlan-boot-materialize-postflight-review", False, "native postflight status/selftest did not pass", "inspect device state before proceeding", True
    if live_result.get("materialized"):
        return "v508-wlan-boot-materialized", True, "fixed boot_wlan write produced a WLAN readiness surface", "advance to no-scan HAL/CNSS registration with driver already materialized", True
    return "v508-wlan-boot-no-surface-captured", True, "fixed boot_wlan write completed but no WLAN readiness surface appeared", "compare dmesg focus lines and decide whether shutdown/retry or service-order expansion is required", True


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    live = manifest.get("live_result") or {}
    surface = live.get("surface") or {}
    live_rows = [
        ["helper_result", live.get("helper_result", "")],
        ["boot_write_rc", live.get("boot_write_rc", "")],
        ["boot_write_errno", live.get("boot_write_errno", "")],
        ["materialized", str(live.get("materialized", ""))],
        ["surface", json.dumps(surface, ensure_ascii=False, sort_keys=True)],
        ["post_status_ok", str(live.get("post_status_ok", ""))],
        ["post_selftest_ok", str(live.get("post_selftest_ok", ""))],
    ]
    dmesg_lines = live.get("dmesg_focus_after") or []
    return "\n".join([
        "# V508 WLAN boot_wlan Materialization Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- wlan_driver_boot_executed: `{manifest['wlan_driver_boot_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Live Result",
        "",
        markdown_table(["key", "value"], live_rows) if live else "- none",
        "",
        "## Dmesg Focus Tail",
        "",
        "\n".join(f"- `{line[:220]}`" for line in dmesg_lines[-24:]) if dmesg_lines else "- none",
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
    if args.command == "run" and approved(args) and not blockers(checks):
        live_result = run_live(args, store)
    decision, pass_ok, reason, next_step, live_executed = classify(args.command, checks, live_result)
    return {
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
        "device_mutations": live_executed,
        "wlan_driver_boot_executed": live_executed,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    if args.observe_sec < 0 or args.observe_sec > 120:
        raise SystemExit("--observe-sec must be between 0 and 120")
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
    print(f"wlan_driver_boot_executed: {manifest['wlan_driver_boot_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
