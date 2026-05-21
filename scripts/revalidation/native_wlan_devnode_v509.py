#!/usr/bin/env python3
"""V509 bounded /dev/wlan devnode materialization proof.

This runner uses `/cache/bin/a90_wlanbootctl` v2 to create only the fixed
`/dev/wlan` character device from `/sys/class/wlan/wlan/dev` after V508 has
materialized the qcwlanstate class device.

It does not write `ON` to `/dev/wlan`, call IWifi.start(), read credentials,
scan, connect, request DHCP, change routes, ping externally, or persist an
Android service.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

import native_wlan_boot_materialize_v508 as v508


v508.__doc__ = __doc__
v508.DEFAULT_OUT_DIR = v508.Path("tmp/wifi/v509-wlan-devnode")
v508.DEFAULT_HELPER_SHA256 = "5f66cc97afb92ce6af45c2584d7fa04e0d0aa23f0442b54a047fb710ed5648c0"
v508.APPROVAL_PHRASE = (
    "approve v509 /dev/wlan devnode proof only; "
    "no driver-state ON, no scan/connect/link-up and no external ping"
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
        and "devnode-observe" in helper_usage
        and "wlanboot.status.begin=1" in helper_status
        and "wlanboot.status.sys_class_wlan_dev.exists=1" in helper_status
    )
    qcwlanstate_ready = (
        "qcwlanstate" in proc_devices
        and "wlanboot.status.sys_class_wlan_dev.exists=1" in helper_status
        and "wlanboot.status.sys_class_wlan_dev.value=" in helper_status
    )

    v508.add_check(checks, "native-clean", "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker",
                   f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3], "restore native health before V509")
    v508.add_check(checks, "helper-wlanbootctl-v2", "pass" if helper_ready else "blocked", "blocker",
                   f"sha_match={args.helper_sha256 in helper_sha} usage={'a90_wlanbootctl v2' in helper_usage} devnode_mode={'devnode-observe' in helper_usage}",
                   [line for line in helper_sha.splitlines() if args.helper in line][:2], "deploy /cache/bin/a90_wlanbootctl v2 before V509 run")
    v508.add_check(checks, "qcwlanstate-class-ready", "pass" if qcwlanstate_ready else "blocked", "blocker",
                   "requires V508-created /sys/class/wlan/wlan/dev and /proc/devices qcwlanstate",
                   [line for line in helper_status.splitlines() if "sys_class_wlan_dev" in line][:4], "run V508 boot_wlan materialization before V509")
    v508.add_check(checks, "process-surface-clean", "pass" if not process_hits else "blocked", "blocker",
                   f"process_count={len(process_hits)}", process_hits[:8], "do not create devnode over active Android Wi-Fi service processes")
    v508.add_check(checks, "wifi-link-clean", "pass" if not wifi_hits else "blocked", "blocker",
                   f"wifi_hit_count={len(wifi_hits)}", wifi_hits[:8], "do not run V509 if Wi-Fi link is already active")
    v508.add_check(checks, "approval-gate", "pass" if v508.approved(args) else "needs-operator", "approval",
                   f"phrase_match={args.approval_phrase == v508.APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
                   [v508.APPROVAL_PHRASE], "exact phrase required before fixed /dev/wlan mknod/chown/chmod")
    return checks


def run_live(args: v508.argparse.Namespace, store: v508.EvidenceStore) -> dict[str, Any]:
    dmesg_before = v508.run_step(args, store, "dmesg-before", ["run", args.toybox, "dmesg"], timeout=45.0)
    record = v508.run_step(
        args,
        store,
        "run-wlanboot-devnode-observe",
        ["run", args.helper, "devnode-observe", str(args.observe_sec)],
        timeout=args.timeout + args.observe_sec + 30.0,
    )
    dmesg_after = v508.run_step(args, store, "dmesg-after", ["run", args.toybox, "dmesg"], timeout=60.0)
    post_status = v508.run_step(args, store, "post-status", ["status"], timeout=25.0)
    post_selftest = v508.run_step(args, store, "post-selftest", ["selftest"], timeout=25.0)
    text = str(record.get("payload") or "")
    keys = v508.parse_keys(text)
    surface_keys = {
        "dev_wlan": keys.get("wlanboot.after.dev_wlan.exists") == "1",
        "dev_wlan_char": keys.get("wlanboot.after.dev_wlan.type") == "char",
        "dev_wlan_major": keys.get("wlanboot.after.dev_wlan.major", ""),
        "dev_wlan_minor": keys.get("wlanboot.after.dev_wlan.minor", ""),
        "wlan0": keys.get("wlanboot.after.sys_class_net_wlan0.exists") == "1" or keys.get("wlanboot.after.proc_net_dev.wlan_present") == "1",
        "wiphy": v508.int_value(keys.get("wlanboot.after.sys_class_ieee80211.count")) > 0,
        "qcwlanstate_char": keys.get("wlanboot.after.proc_devices.qcwlanstate_present") == "1",
    }
    return {
        "capture": record,
        "keys": keys,
        "helper_result": keys.get("wlanboot.result", "missing"),
        "devnode_source_major": keys.get("wlanboot.dev_wlan_node.source_major", ""),
        "devnode_source_minor": keys.get("wlanboot.dev_wlan_node.source_minor", ""),
        "devnode_created": keys.get("wlanboot.dev_wlan_node.created", ""),
        "devnode_match_after": keys.get("wlanboot.dev_wlan_node.match_after", ""),
        "driver_state_on_executed": keys.get("wlanboot.driver_state_on_executed", ""),
        "surface": surface_keys,
        "devnode_ready": surface_keys["dev_wlan"] and surface_keys["dev_wlan_char"] and keys.get("wlanboot.dev_wlan_node.match_after") == "1",
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
        return "v509-wlan-devnode-plan-ready", True, "plan-only; no device command executed", "deploy v2 helper, preflight, then run approved V509 proof", False
    blocked = v508.blockers(checks)
    if blocked:
        return "v509-wlan-devnode-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before fixed /dev/wlan creation", False
    if command == "preflight":
        return "v509-wlan-devnode-preflight-ready", True, "read-only preflight ready; live run still needs exact approval", "run approved V509 proof", False
    if not live_result:
        return "v509-wlan-devnode-review-required", False, "missing live result", "inspect runner failure", True
    if live_result.get("driver_state_on_executed") != "0":
        return "v509-wlan-devnode-scope-violation", False, "helper executed driver-state ON unexpectedly", "inspect helper transcript before proceeding", True
    if not live_result.get("post_status_ok") or not live_result.get("post_selftest_ok"):
        return "v509-wlan-devnode-postflight-review", False, "native postflight status/selftest did not pass", "inspect device state before proceeding", True
    if live_result.get("devnode_ready"):
        return "v509-wlan-devnode-ready", True, "fixed /dev/wlan node now matches qcwlanstate char device", "rerun no-scan HAL/CNSS registration proof with /dev/wlan present", True
    return "v509-wlan-devnode-not-ready", False, f"helper_result={live_result.get('helper_result')}", "inspect helper transcript and /sys/class/wlan/wlan/dev", True


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    live = manifest.get("live_result") or {}
    surface = live.get("surface") or {}
    live_rows = [
        ["helper_result", live.get("helper_result", "")],
        ["devnode_source", f"{live.get('devnode_source_major', '')}:{live.get('devnode_source_minor', '')}"],
        ["devnode_created", live.get("devnode_created", "")],
        ["devnode_match_after", live.get("devnode_match_after", "")],
        ["driver_state_on_executed", live.get("driver_state_on_executed", "")],
        ["devnode_ready", str(live.get("devnode_ready", ""))],
        ["surface", json.dumps(surface, ensure_ascii=False, sort_keys=True)],
        ["post_status_ok", str(live.get("post_status_ok", ""))],
        ["post_selftest_ok", str(live.get("post_selftest_ok", ""))],
    ]
    dmesg_lines = live.get("dmesg_focus_after") or []
    return "\n".join([
        "# V509 /dev/wlan Devnode Materialization Proof",
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
        "\n".join(f"- `{line[:220]}`" for line in dmesg_lines[-24:]) if dmesg_lines else "- none",
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
