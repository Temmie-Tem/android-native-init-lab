#!/usr/bin/env python3
"""V428 explicit lshal status-column Wi-Fi HAL query runner.

V428 is the next gate after V427. It collects two bounded service-surface
views with helper v29:

* a no-daemon-start VINTF-only lshal control;
* a bounded composite servicemanager + hwservicemanager + Wi-Fi HAL start-only
  query using `/system/bin/lshal list --types=binderized,vintf --neat -V -S -i -p -e -c`.

It never starts wificond, supplicant, hostapd, CNSS/diag, scan, connect,
link-up, credentials, DHCP, routing, persistence, or Wi-Fi bring-up.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import wifi_composite_hal_start_only_v405_runner as base


base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v428-lshal-status-column-query-runner")
base.DEFAULT_HELPER_SHA256 = "fcb1a7440995d018a73d52e74fbdd826102cc3fa93ba5f46d50bdca585f2d1bb"
base.DEFAULT_V404 = Path("tmp/wifi/v427-query-improvement-run-statusfix-20260520-140148/manifest.json")
base.HELPER_LABEL = "v29"
base.APPROVAL_PHRASE = (
    "approve v428 explicit lshal status-column query only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)
base.READ_ONLY_COMMANDS = base.READ_ONLY_COMMANDS + (
    ("proc-mounts", ["cat", "/proc/mounts"], 10.0),
    ("stat-selinux-status", ["stat", "/sys/fs/selinux/status"], 10.0),
    ("stat-lshal", ["stat", "/mnt/system/system/bin/lshal"], 10.0),
    ("stat-system-ext-vndk-v30", ["stat", "/mnt/system/system/system_ext/apex/com.android.vndk.v30"], 10.0),
    ("stat-system-ext-wifi-1-0", ["stat", "/mnt/system/system/system_ext/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.0.so"], 10.0),
)


TARGETS = (
    "vendor.samsung.hardware.wifi@2.0::ISehWifi/default",
    "vendor.samsung.hardware.wifi@2.1::ISehWifi/default",
    "vendor.samsung.hardware.wifi@2.2::ISehWifi/default",
)
SERVICE_QUERY_KEY_RE = re.compile(r"^wifi_hal_service_query\.([A-Za-z0-9_.]+)=(.*)$")
_BASE_BUILD_PLAN = base.build_plan


def build_helper_argv(args: base.argparse.Namespace, *, include_data_wifi: bool = True) -> list[str]:
    del include_data_wifi
    argv = [
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "wifi-hal-composite-lshal-status-list",
        "--target-profile",
        args.target_profile,
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
    if base.approved(args):
        argv.extend([
            "--allow-service-manager-start-only",
            "--allow-wifi-hal-start-only",
            "--allow-hal-service-query",
        ])
    return argv


def build_vintf_control_argv(args: base.argparse.Namespace) -> list[str]:
    return [
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "wifi-hal-lshal-vintf-status-list",
        "--target-profile",
        "system-toybox",
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


def build_vintf_control_command(args: base.argparse.Namespace) -> list[str]:
    command = ["run", *build_vintf_control_argv(args)]
    if len(command) <= base.NATIVE_SHELL_MAX_COMMAND_ARGS:
        return command
    raise RuntimeError(f"VINTF control helper command has {len(command)} args; limit is {base.NATIVE_SHELL_MAX_COMMAND_ARGS}")


def build_plan(args: base.argparse.Namespace) -> dict[str, Any]:
    plan = _BASE_BUILD_PLAN(args)
    plan["helper_implicit_data_wifi_mode"] = "private-empty"
    plan["vintf_control_command"] = build_vintf_control_command(args)
    plan["status_query_command"] = base.build_native_run_command(args)
    plan["query_argv"] = "/system/bin/lshal list --types=binderized,vintf --neat -V -S -i -p -e -c"
    plan["vintf_control_argv"] = "/system/bin/lshal list --types=vintf --neat -V -S -i"
    plan["arg_budget_note"] = (
        "helper v29 keeps data-wifi private-empty implicit for status-query modes "
        "so both native shell commands stay within the 30-arg limit"
    )
    return plan


def build_checks(args: base.argparse.Namespace, store: base.EvidenceStore, steps: list[base.Step],
                 v427: dict[str, Any]) -> list[base.Check]:
    checks: list[base.Check] = []
    if args.command == "plan":
        base.add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight after helper v29 deploy")
        return checks

    version = base.step_text(store, steps, "version")
    status = base.step_text(store, steps, "status")
    selftest = base.step_text(store, steps, "selftest")
    helper_sha = base.step_text(store, steps, "sha-helper")
    helper_usage = base.step_text(store, steps, "helper-usage")
    ps = base.step_text(store, steps, "ps")
    netdev = base.step_text(store, steps, "proc-net-dev")
    mounts = base.step_text(store, steps, "proc-mounts")
    processes = [line.strip() for line in ps.splitlines() if base.SERVICE_PROCESS_RE.search(line)]
    wifi_links = [line.strip() for line in netdev.splitlines() if base.WIFI_RE.search(line)]
    selinuxfs_mounted = "/sys/fs/selinux" in mounts and " selinuxfs " in mounts
    helper_ready = (
        args.helper_sha256 in helper_sha
        and "a90_android_execns_probe v29" in helper_usage
        and "wifi-hal-composite-lshal-status-list" in helper_usage
        and "wifi-hal-lshal-vintf-status-list" in helper_usage
        and "--allow-hal-service-query" in helper_usage
        and "--types=binderized,vintf" in helper_usage
        and "--types=vintf" in helper_usage
        and "-V" in helper_usage
        and "-S" in helper_usage
    )

    base.add_check(
        checks,
        "v427-query-improvement-pass",
        "pass" if v427.get("decision") == "v427-explicit-status-query-needed" and v427.get("pass") else "blocked",
        "blocker",
        f"decision={v427.get('decision')} pass={v427.get('pass')}",
        [str(v427.get("path", ""))],
        "V427 must recommend explicit lshal status columns before V428",
    )
    base.add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning", f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3], "refresh baseline if native version intentionally changed")
    base.add_check(checks, "native-clean", "pass" if base.step_ok(steps, "status") and base.step_ok(steps, "selftest") and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker", "status/selftest rc=0 fail=0 expected", [], "fix native health before live run")
    base.add_check(checks, "helper-v29", "pass" if helper_ready else "blocked", "blocker", "remote helper must be v29 with status-column and VINTF-control lshal modes", [line for line in helper_sha.splitlines() if args.helper in line][:2], "deploy helper v29 before V428 live query")
    base.add_check(checks, "selinuxfs-runtime-surface", "pass" if base.step_ok(steps, "stat-selinux-status") and selinuxfs_mounted else "blocked", "blocker", f"mounted={selinuxfs_mounted} status={base.step_ok(steps, 'stat-selinux-status')}", [line for line in mounts.splitlines() if "/sys/fs/selinux" in line][:3], "run the bounded V401 toybox selinuxfs mount before V428 status-column query")
    base.add_check(checks, "lshal-binary", "pass" if base.step_ok(steps, "stat-lshal") else "blocked", "blocker", "/mnt/system/system/bin/lshal must exist for status-column listing", [], "if absent, route to Android-side lshal extraction")
    base.add_check(checks, "runtime-materials", "pass" if base.step_ok(steps, "stat-real-ld-config") and base.step_ok(steps, "stat-real-apex-libraries") and base.step_ok(steps, "stat-property-root") else "blocked", "blocker", f"ld={base.step_ok(steps, 'stat-real-ld-config')} apex={base.step_ok(steps, 'stat-real-apex-libraries')} property={base.step_ok(steps, 'stat-property-root')}", [], "restore private runtime materialization inputs")
    base.add_check(checks, "system-ext-vndk-v30", "pass" if base.step_ok(steps, "stat-system-ext-vndk-v30") and base.step_ok(steps, "stat-system-ext-wifi-1-0") else "blocked", "blocker", "system_ext VNDK v30 and android.hardware.wifi@1.0.so must exist", [], "restore system_ext VNDK v30 source")
    base.add_check(checks, "service-manager-binaries", "pass" if base.step_ok(steps, "stat-servicemanager") and base.step_ok(steps, "stat-hwservicemanager") else "blocked", "blocker", f"servicemanager={base.step_ok(steps, 'stat-servicemanager')} hwservicemanager={base.step_ok(steps, 'stat-hwservicemanager')}", [], "core managers must be visible")
    base.add_check(checks, "process-surface-clean", "pass" if not processes else "blocked", "blocker", f"process_count={len(processes)}", processes[:8], "do not run over existing manager/HAL processes")
    base.add_check(checks, "wifi-link-clean", "pass" if not wifi_links else "blocked", "blocker", f"wifi_link_count={len(wifi_links)}", wifi_links[:8], "do not run while Wi-Fi link is active")
    base.add_check(checks, "approval-gate", "pass" if base.approved(args) else "needs-operator", "approval", f"phrase_match={args.approval_phrase == base.APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}", [base.APPROVAL_PHRASE], "exact phrase and flags required before V428 status-column live query")
    return checks


def parse_service_query_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = SERVICE_QUERY_KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def parse_target_statuses(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for target in TARGETS:
        target_lines = [line.strip() for line in text.splitlines() if target in line]
        warnings = [line for line in target_lines if "cannot be fetched from service manager" in line]
        data_lines = [line for line in target_lines if "cannot be fetched from service manager" not in line]
        status_token = ""
        for line in data_lines:
            fields = line.split()
            if len(fields) >= 2:
                status_token = fields[1]
                break
        if warnings:
            interpretation = "get-null-warning"
        elif data_lines and status_token:
            interpretation = "status-row-present"
        else:
            interpretation = "absent"
        rows.append({
            "target": target,
            "line_present": bool(target_lines),
            "warning_present": bool(warnings),
            "status_token": status_token,
            "interpretation": interpretation,
            "evidence": target_lines[:6],
        })
    return rows


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    control_command = build_vintf_control_command(args)
    control_record = base.run_capture(args, "run-vintf-status-control", control_command, timeout=args.timeout + args.max_runtime_sec + 30.0)
    control_rel = "native/run-vintf-status-control.txt"
    store.write_text(control_rel, base.strip_cmdv1_text(control_record.text) if control_record.text else control_record.error + "\n")
    control_text = store.path(control_rel).read_text(encoding="utf-8", errors="replace")
    control_query_keys = parse_service_query_keys(control_text)

    status_command = base.build_native_run_command(args)
    status_record = base.run_capture(args, "run-lshal-status-query", status_command, timeout=args.timeout + args.max_runtime_sec + 45.0)
    status_rel = "native/run-lshal-status-query.txt"
    store.write_text(status_rel, base.strip_cmdv1_text(status_record.text) if status_record.text else status_record.error + "\n")
    status_text = store.path(status_rel).read_text(encoding="utf-8", errors="replace")
    composite_keys = base.parse_composite_keys(status_text)
    status_query_keys = parse_service_query_keys(status_text)
    return {
        "control_capture": base.capture_to_manifest(control_record),
        "control_file": control_rel,
        "control_service_query_keys": control_query_keys,
        "control_service_query_result": control_query_keys.get("result", "missing"),
        "control_target_statuses": parse_target_statuses(control_text),
        "status_capture": base.capture_to_manifest(status_record),
        "status_file": status_rel,
        "keys": composite_keys,
        "service_query_keys": status_query_keys,
        "helper_result": composite_keys.get("result", "missing"),
        "helper_reason": composite_keys.get("reason", ""),
        "service_query_result": status_query_keys.get("result", "missing"),
        "service_query_reason": status_query_keys.get("reason", ""),
        "target_statuses": parse_target_statuses(status_text),
        "timed_out": composite_keys.get("timed_out") == "1",
        "all_postflight_safe": composite_keys.get("all_postflight_safe") == "1",
        "all_observable_at_timeout": composite_keys.get("all_observable_at_timeout") == "1",
    }


def decide(args: base.argparse.Namespace, checks: list[base.Check], live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return "v428-lshal-status-query-plan-ready", True, "plan-only; no device command executed", "run preflight after helper v29 deploy", False
    blocked = base.blockers(checks)
    if blocked:
        return "v428-lshal-status-query-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before approval", False
    if args.command == "preflight":
        return "v428-lshal-status-query-preflight-ready", True, "read-only preflight is ready; live query still needs approval", "operator may approve exact V428 phrase", False
    if not base.approved(args):
        return "v428-lshal-status-query-approval-required", True, "exact approval phrase required; no device command executed", "rerun with exact approval if intended", False
    if not live_result or not post or not post["clean"]:
        return "v428-lshal-status-query-review-required", False, "live result or postflight cleanliness missing", "inspect evidence and consider recovery reboot", True
    control_result = live_result.get("control_service_query_result")
    control_has_rows = any(row.get("line_present") for row in live_result.get("control_target_statuses", []))
    helper_result = live_result.get("helper_result")
    query_result = live_result.get("service_query_result")
    if control_result == "service-query-pass" and helper_result == "service-query-pass" and query_result == "service-query-pass" and live_result.get("all_postflight_safe") and post.get("clean"):
        return "v428-lshal-status-query-pass", True, "VINTF control and explicit status-column query completed while composite HAL trio stayed bounded and cleaned", "classify status rows before any Wi-Fi bring-up", True
    if helper_result == "service-query-tool-missing":
        return "v428-lshal-status-query-tool-missing", True, "lshal is unavailable in this system image", "route to Android-side lshal extraction", True
    if control_result != "service-query-pass" and not control_has_rows:
        return "v428-lshal-status-query-control-gap", True, f"VINTF control result={control_result}", "inspect VINTF-only command evidence before retrying composite query", True
    if helper_result == "service-query-runtime-gap":
        return "v428-lshal-status-query-runtime-gap", True, f"status query failed: {live_result.get('service_query_reason')}; VINTF rows present={control_has_rows}", "compare target rows and decide Android-managed pivot versus native retry", True
    return "v428-lshal-status-query-review-required", False, f"helper_result={helper_result} query_result={query_result}", "inspect helper output before widening scope", True


def refusal_manifest(args: base.argparse.Namespace, v427: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": "v428-lshal-status-query-approval-required",
        "pass": True,
        "reason": "exact approval phrase required; no device command executed",
        "next_step": "rerun with exact approval only after helper v29 deploy and preflight",
        "host": base.collect_host_metadata(),
        "v427": {"path": v427.get("path"), "decision": v427.get("decision"), "pass": v427.get("pass")},
        "plan": base.build_plan(args),
        "steps": [],
        "checks": [asdict(base.Check("approval-gate", "needs-operator", "approval", base.APPROVAL_PHRASE, [base.APPROVAL_PHRASE], "approve before live status-column query"))],
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
    v427 = base.load_json(args.v404_manifest)
    if args.command == "run" and not base.approved(args):
        return refusal_manifest(args, v427)
    steps: list[base.Step] = []
    live_result: dict[str, Any] | None = None
    post: dict[str, Any] | None = None
    if args.command != "plan":
        steps = base.run_preflight(args, store)
    checks = build_checks(args, store, steps, v427)
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
        "v427": {"path": v427.get("path"), "decision": v427.get("decision"), "pass": v427.get("pass")},
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
        "# V428 Explicit lshal Status-Column Query Runner",
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
        "## Commands",
        "",
        "`" + " ".join(manifest["plan"]["vintf_control_command"]) + "`",
        "",
        "`" + " ".join(manifest["plan"]["status_query_command"]) + "`",
        "",
    ]) + "\n"


base.build_helper_argv = build_helper_argv
base.build_plan = build_plan
base.build_checks = build_checks
base.run_live = run_live
base.decide = decide
base.refusal_manifest = refusal_manifest
base.build_manifest = build_manifest
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
