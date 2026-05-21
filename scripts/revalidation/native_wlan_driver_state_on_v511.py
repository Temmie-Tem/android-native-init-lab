#!/usr/bin/env python3
"""V511 bounded qcwlanstate driver-state ON proof.

This runner uses `/cache/bin/a90_wlanbootctl` v2 to ensure the fixed
`/dev/wlan` node exists, write `ON` to that qcwlanstate device, and observe
whether `wlan0`, wiphy, or qcwlanstate state changes materialize.

It does not start Wi-Fi HAL/CNSS/wificond/supplicant/hostapd, scan, connect,
read credentials, run DHCP, change routes, ping externally, or persist an
Android service.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

import native_wlan_devnode_v509 as v509


v508 = v509.v508
v508.__doc__ = __doc__
v508.DEFAULT_OUT_DIR = v508.Path("tmp/wifi/v511-wlan-driver-state-on")
v508.DEFAULT_HELPER_SHA256 = "5f66cc97afb92ce6af45c2584d7fa04e0d0aa23f0442b54a047fb710ed5648c0"
v508.APPROVAL_PHRASE = (
    "approve v511 /dev/wlan driver-state ON proof only; "
    "no scan/connect/link-up and no external ping"
)


def build_checks(args: v508.argparse.Namespace, steps: list[dict[str, Any]]) -> list[v508.Check]:
    checks: list[v508.Check] = []
    if args.command == "plan":
        v508.add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight")
        return checks

    version = v508.step_payload(steps, "version")
    status = v508.step_payload(steps, "status")
    selftest = v508.step_payload(steps, "selftest")
    helper_sha = v508.step_payload(steps, "sha-helper")
    helper_usage = v508.step_payload(steps, "helper-usage")
    helper_status = v508.step_payload(steps, "helper-status")
    ps = v508.step_payload(steps, "ps")
    netdev = v508.step_payload(steps, "proc-net-dev")
    sys_net = v508.step_payload(steps, "sys-class-net")
    sys_ieee = v508.step_payload(steps, "sys-class-ieee80211")
    proc_devices = v508.step_payload(steps, "proc-devices")
    process_hits = [line.strip() for line in ps.splitlines() if v508.PROCESS_RE.search(line)]
    wifi_hits = [
        line.strip()
        for line in (netdev + "\n" + sys_net + "\n" + sys_ieee).splitlines()
        if v508.WIFI_RE.search(line)
    ]
    helper_ready = (
        args.helper_sha256 in helper_sha
        and "a90_wlanbootctl v2" in helper_usage
        and "devnode-on-observe" in helper_usage
        and "wlanboot.status.begin=1" in helper_status
        and "wlanboot.status.dev_wlan.exists=1" in helper_status
        and "wlanboot.status.dev_wlan.type=char" in helper_status
    )
    qcwlanstate_ready = (
        "qcwlanstate" in proc_devices
        and "wlanboot.status.sys_class_wlan_dev.exists=1" in helper_status
        and "wlanboot.status.sys_class_wlan_dev.value=" in helper_status
    )

    v508.add_check(checks, "native-clean", "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker",
                   f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3], "restore native health before V511")
    v508.add_check(checks, "helper-wlanbootctl-v2", "pass" if helper_ready else "blocked", "blocker",
                   f"sha_match={args.helper_sha256 in helper_sha} usage={'a90_wlanbootctl v2' in helper_usage} on_mode={'devnode-on-observe' in helper_usage}",
                   [line for line in helper_sha.splitlines() if args.helper in line][:2], "deploy /cache/bin/a90_wlanbootctl v2 and create /dev/wlan before V511")
    v508.add_check(checks, "qcwlanstate-class-ready", "pass" if qcwlanstate_ready else "blocked", "blocker",
                   "requires V508/V509-created qcwlanstate class and fixed /dev/wlan char device",
                   [line for line in helper_status.splitlines() if "sys_class_wlan_dev" in line or "dev_wlan" in line][:8], "run V508/V509 before V511")
    v508.add_check(checks, "process-surface-clean", "pass" if not process_hits else "blocked", "blocker",
                   f"process_count={len(process_hits)}", process_hits[:8], "do not write ON over active Android Wi-Fi service processes")
    v508.add_check(checks, "wifi-link-clean", "pass" if not wifi_hits else "blocked", "blocker",
                   f"wifi_hit_count={len(wifi_hits)}", wifi_hits[:8], "do not run V511 if Wi-Fi link is already active")
    v508.add_check(checks, "approval-gate", "pass" if v508.approved(args) else "needs-operator", "approval",
                   f"phrase_match={args.approval_phrase == v508.APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
                   [v508.APPROVAL_PHRASE], "exact phrase required before fixed /dev/wlan ON write")
    return checks


def run_live(args: v508.argparse.Namespace, store: v508.EvidenceStore) -> dict[str, Any]:
    dmesg_before = v508.run_step(args, store, "dmesg-before", ["run", args.toybox, "dmesg"], timeout=45.0)
    record = v508.run_step(
        args,
        store,
        "run-wlanboot-driver-state-on-observe",
        ["run", args.helper, "devnode-on-observe", str(args.observe_sec)],
        timeout=args.timeout + args.observe_sec + 45.0,
    )
    dmesg_after = v508.run_step(args, store, "dmesg-after", ["run", args.toybox, "dmesg"], timeout=60.0)
    post_status = v508.run_step(args, store, "post-status", ["status"], timeout=25.0)
    post_selftest = v508.run_step(args, store, "post-selftest", ["selftest"], timeout=25.0)
    text = str(record.get("payload") or "")
    keys = v508.parse_keys(text)
    surface_keys = {
        "dev_wlan": keys.get("wlanboot.after.dev_wlan.exists") == "1",
        "dev_wlan_char": keys.get("wlanboot.after.dev_wlan.type") == "char",
        "qcwlanstate_on": "ON" in keys.get("wlanboot.after.qcwlanstate.value", ""),
        "wlan0": keys.get("wlanboot.after.sys_class_net_wlan0.exists") == "1" or keys.get("wlanboot.after.proc_net_dev.wlan_present") == "1",
        "wiphy": v508.int_value(keys.get("wlanboot.after.sys_class_ieee80211.count")) > 0,
        "qcwlanstate_char": keys.get("wlanboot.after.proc_devices.qcwlanstate_present") == "1",
    }
    return {
        "capture": record,
        "keys": keys,
        "helper_result": keys.get("wlanboot.result", "missing"),
        "driver_state_on_executed": keys.get("wlanboot.driver_state_on_executed", ""),
        "driver_state_write_rc": keys.get("wlanboot.dev_wlan_on.write_rc", ""),
        "driver_state_write_errno": keys.get("wlanboot.dev_wlan_on.write_errno", ""),
        "surface": surface_keys,
        "driver_state_on_written": keys.get("wlanboot.result") == "driver-state-on-written",
        "dmesg_before_file": dmesg_before["file"],
        "dmesg_after_file": dmesg_after["file"],
        "dmesg_focus_after": v508.dmesg_focus(str(dmesg_after.get("payload") or "")),
        "post_status_ok": bool(post_status.get("ok")),
        "post_selftest_ok": bool(post_selftest.get("ok")),
        "post_selftest_text": str(post_selftest.get("payload") or "").strip()[:400],
    }


def classify(command: str,
             checks: list[v508.Check],
             live_result: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if command == "plan":
        return "v511-wlan-driver-state-on-plan-ready", True, "plan-only; no device command executed", "preflight, then run approved V511 proof", False
    blocked = v508.blockers(checks)
    if blocked:
        return "v511-wlan-driver-state-on-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before /dev/wlan ON write", False
    if command == "preflight":
        return "v511-wlan-driver-state-on-preflight-ready", True, "read-only preflight ready; live run still needs exact approval", "run approved V511 proof", False
    if not live_result:
        return "v511-wlan-driver-state-on-review-required", False, "missing live result", "inspect runner failure", True
    if live_result.get("driver_state_on_executed") != "1":
        return "v511-wlan-driver-state-on-scope-review", False, "helper did not execute driver-state ON write", "inspect helper transcript", True
    if not live_result.get("post_status_ok") or not live_result.get("post_selftest_ok"):
        return "v511-wlan-driver-state-on-postflight-review", False, "native postflight status/selftest did not pass", "inspect device state before proceeding", True
    surface = live_result.get("surface") or {}
    if live_result.get("driver_state_on_written") and (surface.get("wlan0") or surface.get("wiphy")):
        return "v511-wlan-driver-state-on-materialized", True, "driver-state ON write succeeded and kernel exposed wlan/wiphy surface", "rerun V510 dual-HAL proof, then proceed to scan-only if IWifi registers", True
    if live_result.get("driver_state_on_written"):
        return "v511-wlan-driver-state-on-written", True, "driver-state ON write succeeded but wlan0/wiphy did not materialize in observe window", "rerun V510 dual-HAL proof and inspect dmesg for firmware/CNSS blockers", True
    return "v511-wlan-driver-state-on-write-failed", False, f"helper_result={live_result.get('helper_result')} write_rc={live_result.get('driver_state_write_rc')} errno={live_result.get('driver_state_write_errno')}", "inspect qcwlanstate write failure and dmesg", True


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    live = manifest.get("live_result") or {}
    surface = live.get("surface") or {}
    live_rows = [
        ["helper_result", live.get("helper_result", "")],
        ["driver_state_on_executed", live.get("driver_state_on_executed", "")],
        ["driver_state_write_rc", live.get("driver_state_write_rc", "")],
        ["driver_state_write_errno", live.get("driver_state_write_errno", "")],
        ["driver_state_on_written", str(live.get("driver_state_on_written", ""))],
        ["surface", json.dumps(surface, ensure_ascii=False, sort_keys=True)],
        ["post_status_ok", str(live.get("post_status_ok", ""))],
        ["post_selftest_ok", str(live.get("post_selftest_ok", ""))],
    ]
    dmesg_lines = live.get("dmesg_focus_after") or []
    return "\n".join([
        "# V511 /dev/wlan Driver-State ON Proof",
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
        f"- driver_state_on_executed: `{manifest['driver_state_on_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        v508.markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Live Result",
        "",
        v508.markdown_table(["key", "value"], live_rows) if live else "- none",
        "",
        "## Dmesg Focus Tail",
        "",
        "\n".join(f"- `{line[:220]}`" for line in dmesg_lines[-36:]) if dmesg_lines else "- none",
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
    ])


def build_manifest(args: v508.argparse.Namespace, store: v508.EvidenceStore) -> dict[str, Any]:
    steps = [] if args.command == "plan" else v508.preflight_steps(args, store)
    checks = build_checks(args, steps)
    live_result = None
    if args.command == "run" and v508.approved(args) and not v508.blockers(checks):
        live_result = run_live(args, store)
    decision, pass_ok, reason, next_step, live_executed = classify(args.command, checks, live_result)
    return {
        "generated_at": v508.now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": v508.collect_host_metadata(),
        "steps": steps,
        "checks": [asdict(check) for check in checks],
        "live_result": live_result,
        "required_approval_phrase": v508.APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == v508.APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan" or live_executed,
        "device_mutations": live_executed,
        "wlan_driver_boot_executed": False,
        "driver_state_on_executed": live_result.get("driver_state_on_executed") == "1" if live_result else False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


v508.build_checks = build_checks
v508.run_live = run_live
v508.classify = classify
v508.render_summary = render_summary
v508.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(v508.main())
