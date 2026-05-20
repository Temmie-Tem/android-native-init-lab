#!/usr/bin/env python3
"""V409 bounded Wi-Fi HAL registration query runner.

V409 is the next gate after the V408 service-surface packet.  It requires
helper v25 and uses the helper-owned private namespace to start only:

* servicemanager
* hwservicemanager
* first Wi-Fi HAL candidate
* a bounded `/system/bin/lshal` query child

It is fail-closed.  Plan and no-approval run execute no device command.  A live
query requires the exact approval phrase and still excludes scan/connect/link-up,
credentials, DHCP, routing, persistence, and Wi-Fi bring-up.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import wifi_composite_hal_start_only_v405_runner as base


base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v409-hal-registration-query-runner")
base.DEFAULT_HELPER_SHA256 = "e90639d55dacc5486c998c4d1470235a6c72e4759cc63ebd1f07cf90c5852b37"
base.DEFAULT_V404 = Path("tmp/wifi/v408-hal-registration-surface-packet-20260520-102249/manifest.json")
base.HELPER_LABEL = "v25"
base.APPROVAL_PHRASE = (
    "approve v409 bounded lshal registration query only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)
base.READ_ONLY_COMMANDS = base.READ_ONLY_COMMANDS + (
    ("stat-lshal", ["stat", "/mnt/system/system/bin/lshal"], 10.0),
    ("stat-system-ext-vndk-v30", ["stat", "/mnt/system/system/system_ext/apex/com.android.vndk.v30"], 10.0),
    ("stat-system-ext-wifi-1-0", ["stat", "/mnt/system/system/system_ext/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.0.so"], 10.0),
)


SERVICE_QUERY_KEY_RE = base.re.compile(r"^wifi_hal_service_query\.([A-Za-z0-9_.]+)=(.*)$")


def build_helper_argv(args: base.argparse.Namespace, *, include_data_wifi: bool = True) -> list[str]:
    argv = [
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "wifi-hal-composite-lshal-list",
        "--target-profile",
        args.target_profile,
        "--null-device-mode",
        "dev-null-selinux",
    ]
    if include_data_wifi:
        argv.extend(["--data-wifi-mode", "private-empty"])
    argv.extend([
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
    ])
    if base.approved(args):
        argv.extend([
            "--allow-service-manager-start-only",
            "--allow-wifi-hal-start-only",
            "--allow-hal-service-query",
        ])
    return argv


def build_checks(args: base.argparse.Namespace, store: base.EvidenceStore, steps: list[base.Step],
                 v408: dict[str, Any]) -> list[base.Check]:
    checks: list[base.Check] = []
    if args.command == "plan":
        base.add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight after helper v25 deploy")
        return checks

    version = base.step_text(store, steps, "version")
    status = base.step_text(store, steps, "status")
    selftest = base.step_text(store, steps, "selftest")
    helper_sha = base.step_text(store, steps, "sha-helper")
    helper_usage = base.step_text(store, steps, "helper-usage")
    ps = base.step_text(store, steps, "ps")
    netdev = base.step_text(store, steps, "proc-net-dev")
    processes = [line.strip() for line in ps.splitlines() if base.SERVICE_PROCESS_RE.search(line)]
    wifi_links = [line.strip() for line in netdev.splitlines() if base.WIFI_RE.search(line)]
    helper_ready = (
        args.helper_sha256 in helper_sha
        and "a90_android_execns_probe v25" in helper_usage
        and "wifi-hal-composite-lshal-list" in helper_usage
        and "--allow-hal-service-query" in helper_usage
    )

    base.add_check(
        checks,
        "v408-registration-surface-pass",
        "pass" if v408.get("decision") == "v408-hal-registration-service-surface-evidence-ready" and v408.get("pass") else "blocked",
        "blocker",
        f"decision={v408.get('decision')} pass={v408.get('pass')}",
        [str(v408.get("path", ""))],
        "V408 evidence packet must pass before V409 registration query",
    )
    base.add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning", f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3], "refresh baseline if native version intentionally changed")
    base.add_check(checks, "native-clean", "pass" if base.step_ok(steps, "status") and base.step_ok(steps, "selftest") and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker", "status/selftest rc=0 fail=0 expected", [], "fix native health before live run")
    base.add_check(checks, "helper-v25", "pass" if helper_ready else "blocked", "blocker", "remote helper must be v25 with lshal query mode", [line for line in helper_sha.splitlines() if args.helper in line][:2], "deploy helper v25 before V409 live query")
    base.add_check(checks, "lshal-binary", "pass" if base.step_ok(steps, "stat-lshal") else "blocked", "blocker", "/mnt/system/system/bin/lshal must exist for direct registration listing", [], "if absent, route to V410 micro HIDL client or Android-side lshal extraction")
    base.add_check(checks, "runtime-materials", "pass" if base.step_ok(steps, "stat-real-ld-config") and base.step_ok(steps, "stat-real-apex-libraries") and base.step_ok(steps, "stat-property-root") else "blocked", "blocker", f"ld={base.step_ok(steps, 'stat-real-ld-config')} apex={base.step_ok(steps, 'stat-real-apex-libraries')} property={base.step_ok(steps, 'stat-property-root')}", [], "restore private runtime materialization inputs")
    base.add_check(checks, "system-ext-vndk-v30", "pass" if base.step_ok(steps, "stat-system-ext-vndk-v30") and base.step_ok(steps, "stat-system-ext-wifi-1-0") else "blocked", "blocker", "system_ext VNDK v30 and android.hardware.wifi@1.0.so must exist", [], "restore system_ext VNDK v30 source")
    base.add_check(checks, "service-manager-binaries", "pass" if base.step_ok(steps, "stat-servicemanager") and base.step_ok(steps, "stat-hwservicemanager") else "blocked", "blocker", f"servicemanager={base.step_ok(steps, 'stat-servicemanager')} hwservicemanager={base.step_ok(steps, 'stat-hwservicemanager')}", [], "core managers must be visible")
    base.add_check(checks, "process-surface-clean", "pass" if not processes else "blocked", "blocker", f"process_count={len(processes)}", processes[:8], "do not run over existing manager/HAL processes")
    base.add_check(checks, "wifi-link-clean", "pass" if not wifi_links else "blocked", "blocker", f"wifi_link_count={len(wifi_links)}", wifi_links[:8], "do not run while Wi-Fi link is active")
    base.add_check(checks, "approval-gate", "pass" if base.approved(args) else "needs-operator", "approval", f"phrase_match={args.approval_phrase == base.APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}", [base.APPROVAL_PHRASE], "exact phrase and flags required before V409 live query")
    return checks


def parse_service_query_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = SERVICE_QUERY_KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    command = base.build_native_run_command(args)
    record = base.run_capture(args, "run-registration-query", command, timeout=args.timeout + args.max_runtime_sec + 45.0)
    rel = "native/run-registration-query.txt"
    store.write_text(rel, base.strip_cmdv1_text(record.text) if record.text else record.error + "\n")
    text = store.path(rel).read_text(encoding="utf-8", errors="replace")
    keys = base.parse_composite_keys(text)
    query_keys = parse_service_query_keys(text)
    return {
        "capture": base.capture_to_manifest(record),
        "file": rel,
        "keys": keys,
        "service_query_keys": query_keys,
        "helper_result": keys.get("result", "missing"),
        "helper_reason": keys.get("reason", ""),
        "service_query_result": query_keys.get("result", "missing"),
        "service_query_reason": query_keys.get("reason", ""),
        "timed_out": keys.get("timed_out") == "1",
        "all_postflight_safe": keys.get("all_postflight_safe") == "1",
        "all_observable_at_timeout": keys.get("all_observable_at_timeout") == "1",
    }


def decide(args: base.argparse.Namespace, checks: list[base.Check], live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return "v409-hal-registration-query-plan-ready", True, "plan-only; no device command executed", "run preflight after helper v25 deploy", False
    blocked = base.blockers(checks)
    if blocked:
        return "v409-hal-registration-query-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before approval", False
    if args.command == "preflight":
        return "v409-hal-registration-query-preflight-ready", True, "read-only preflight is ready; live query still needs approval", "operator may approve exact V409 phrase", False
    if not base.approved(args):
        return "v409-hal-registration-query-approval-required", True, "exact approval phrase required; no device command executed", "rerun with exact approval if intended", False
    if not live_result or not post or not post["clean"]:
        return "v409-hal-registration-query-review-required", False, "live result or postflight cleanliness missing", "inspect evidence and consider recovery reboot", True
    helper_result = live_result.get("helper_result")
    query_result = live_result.get("service_query_result")
    if helper_result == "service-query-pass" and query_result == "service-query-pass" and live_result.get("all_postflight_safe") and post.get("clean"):
        return "v409-hal-registration-query-pass", True, "lshal query completed while composite HAL trio stayed bounded and cleaned", "classify listed Wi-Fi HAL service and plan next gate", True
    if helper_result == "service-query-tool-missing":
        return "v409-hal-registration-query-tool-missing", True, "lshal is unavailable in this system image", "route to V410 micro HIDL client or Android-side lshal extraction", True
    if helper_result == "service-query-runtime-gap":
        return "v409-hal-registration-query-runtime-gap", True, f"service query failed: {live_result.get('service_query_reason')}", "classify lshal/HIDL query failure before wider Wi-Fi work", True
    return "v409-hal-registration-query-review-required", False, f"helper_result={helper_result} query_result={query_result}", "inspect helper output before widening scope", True


def refusal_manifest(args: base.argparse.Namespace, v408: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": "v409-hal-registration-query-approval-required",
        "pass": True,
        "reason": "exact approval phrase required; no device command executed",
        "next_step": "rerun with exact approval only after helper v25 deploy and preflight",
        "host": base.collect_host_metadata(),
        "v408": {"path": v408.get("path"), "decision": v408.get("decision"), "pass": v408.get("pass")},
        "plan": base.build_plan(args),
        "steps": [],
        "checks": [asdict(base.Check("approval-gate", "needs-operator", "approval", base.APPROVAL_PHRASE, [base.APPROVAL_PHRASE], "approve before live registration query"))],
        "live_result": None,
        "postflight": None,
        "required_approval_phrase": base.APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == base.APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
    }


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    v408 = base.load_json(args.v404_manifest)
    if args.command == "run" and not base.approved(args):
        return refusal_manifest(args, v408)
    steps: list[base.Step] = []
    live_result: dict[str, Any] | None = None
    post: dict[str, Any] | None = None
    if args.command != "plan":
        steps = base.run_preflight(args, store)
    checks = build_checks(args, store, steps, v408)
    if args.command == "run" and base.approved(args) and not base.blockers(checks):
        live_result = run_live(args, store)
        post = base.postflight(args, store)
    decision, pass_ok, reason, next_step, daemon_started = decide(args, checks, live_result, post)
    return {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": base.collect_host_metadata(),
        "v408": {"path": v408.get("path"), "decision": v408.get("decision"), "pass": v408.get("pass")},
        "plan": base.build_plan(args),
        "steps": [asdict(step) for step in steps],
        "checks": [asdict(check) for check in checks],
        "live_result": live_result,
        "postflight": post,
        "required_approval_phrase": base.APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == base.APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan" and (args.command != "run" or base.approved(args)),
        "device_mutations": daemon_started,
        "daemon_start_executed": daemon_started,
        "wifi_hal_start_executed": daemon_started,
        "wifi_bringup_executed": False,
        "explicitly_not_approved": [
            "wificond, supplicant, hostapd, cnss-daemon, or cnss_diag start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
            "unbounded daemon persistence or boot autostart",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], "<br>".join(c["evidence"]), c["next_step"]] for c in manifest["checks"]]
    step_rows = [[s["name"], "PASS" if s["ok"] else "FAIL", s["rc"], s["status"], s["file"]] for s in manifest["steps"]]
    return "\n".join([
        "# V409 Wi-Fi HAL Registration Query Runner",
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
        "",
        "## Checks",
        "",
        base.markdown_table(["name", "status", "severity", "detail", "evidence", "next"], check_rows),
        "",
        "## Native Steps",
        "",
        base.markdown_table(["step", "ok", "rc", "status", "file"], step_rows) if step_rows else "- none",
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
        "## Command",
        "",
        "`" + " ".join(manifest["plan"]["command"]) + "`",
        "",
    ]) + "\n"


base.build_helper_argv = build_helper_argv
base.build_checks = build_checks
base.run_live = run_live
base.decide = decide
base.refusal_manifest = refusal_manifest
base.build_manifest = build_manifest
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
