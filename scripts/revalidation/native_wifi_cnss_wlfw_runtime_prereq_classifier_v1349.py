#!/usr/bin/env python3
"""V1349 host-only CNSS/WLFW runtime prerequisite classifier.

Reads specific prior reports and selects the next CNSS/WLFW prerequisite branch.
No device command, helper deploy, daemon start, or network action is performed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1349-cnss-wlfw-runtime-prereq-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1349-cnss-wlfw-runtime-prereq-classifier.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1349_CNSS_WLFW_RUNTIME_PREREQ_CLASSIFIER_2026-06-01.md")

DEFAULT_REPORTS = {
    "v924": Path("docs/reports/NATIVE_INIT_V924_CNSS_WLFW_PRECONDITION_GAP_2026-05-26.md"),
    "v966": Path("docs/reports/NATIVE_INIT_V966_ANDROID_WLFW_START_ATTRIBUTION_2026-05-26.md"),
    "v1100": Path("docs/reports/NATIVE_INIT_V1100_CNSS_PM_REGISTER_RETURN_TRACEFS_2026-05-27.md"),
    "v1101": Path("docs/reports/NATIVE_INIT_V1101_PM_SERVER_REGISTER_PATH_TRACEFS_2026-05-27.md"),
    "v1102": Path("docs/reports/NATIVE_INIT_V1102_PM_SERVER_EARLY_REGISTER_TRACEFS_2026-05-27.md"),
    "v1171": Path("docs/reports/NATIVE_INIT_V1171_PM_RECEIVER_CALLBACK_LIVE_2026-05-27.md"),
    "v1172": Path("docs/reports/NATIVE_INIT_V1172_CNSS_CALLBACK_BODY_LIVE_2026-05-27.md"),
    "v1348": Path("docs/reports/NATIVE_INIT_V1348_ANDROID_WLFW_REQUEST_PATH_CLASSIFIER_2026-06-01.md"),
}

FORBIDDEN_PATTERNS = (
    re.compile(r"\b(?:wifi_hal_start|scan_connect|credential_use|dhcp_route|external_ping)_executed\b\s*[:=]\s*(?:true|1)", re.I),
    re.compile(r"\b(?:wifi_hal_start|scan_connect|credential_use|dhcp_route|external_ping)\b[^\n]{0,80}\|\s*`?(?:true|1)`?", re.I),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def read_text(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(path), "text": ""}
    return {
        "exists": True,
        "path": str(path),
        "text": resolved.read_text(encoding="utf-8", errors="replace"),
    }


def has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.I | re.S) is not None


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def report_paths_from_args(args: argparse.Namespace) -> dict[str, Path]:
    return {
        "v924": args.v924_report,
        "v966": args.v966_report,
        "v1100": args.v1100_report,
        "v1101": args.v1101_report,
        "v1102": args.v1102_report,
        "v1171": args.v1171_report,
        "v1172": args.v1172_report,
        "v1348": args.v1348_report,
    }


def forbidden_hits(reports: dict[str, dict[str, Any]]) -> list[str]:
    hits: list[str] = []
    for name, report in reports.items():
        text = str(report.get("text", ""))
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(text):
                hits.append(f"{name}:{pattern.pattern}")
    return hits


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    paths = report_paths_from_args(args)
    reports = {name: read_text(path) for name, path in paths.items()}
    missing = [name for name, report in reports.items() if not report["exists"]]
    forbidden = forbidden_hits(reports)

    v924 = reports["v924"]["text"]
    v966 = reports["v966"]["text"]
    v1100 = reports["v1100"]["text"]
    v1101 = reports["v1101"]["text"]
    v1102 = reports["v1102"]["text"]
    v1171 = reports["v1171"]["text"]
    v1172 = reports["v1172"]["text"]
    v1348 = reports["v1348"]["text"]

    cnss_netlink_no_wlfw = (
        has(v924, r"reach(?:es)? the kernel `cld80211` netlink surface")
        and has(v924, r"native `wlfw_start` count \| `0`")
        and has(v924, r"native BDF count \| `0`")
        and has(v924, r"native `wlan0` positive count \| `0`")
    )
    android_wlfw_attributed = (
        has(v966, r"`cnss-daemon wlfw_start` \| `8\.")
        and has(v966, r"wlfw_start` is not caused by the direct `/dev/subsys_esoc0` open")
        and has(v966, r"native already reaches a CNSS netlink-visible state")
    )
    pm_register_blocks = (
        has(v1100, r"cnss-daemon.*pm_client_register.*does not return")
        and has(v1100, r"never calls `?pm_client_connect`?")
        and has(v1101, r"pm-service server register entry hit")
        and has(v1101, r"no pm-service register match")
        and has(v1102, r"helper at `0x9538`.*second/modem")
        and has(v1102, r"helper does not return")
    )
    callback_ack_only = (
        has(v1171, r"receiver-side callback.*inside `cnss-daemon`")
        and has(v1172, r"ack-only path")
        and has(v1172, r"does not open\s+`/dev/subsys_esoc0`")
    )
    v1348_branch_selected = has(v1348, r"v1348-cnss-wlfw-request-path-before-lower-mutation")
    lower_mutation_blocked = has(v1348, r"Do not add PMIC/GPIO/GDSC/eSoC mutation")

    checks = [
        check("required-reports-present", not missing, "missing=" + ",".join(missing) if missing else "all required reports present"),
        check("v924-cnss-netlink-no-wlfw", cnss_netlink_no_wlfw, "native reaches cld80211 but no wlfw/BDF/wlan0"),
        check("v966-android-wlfw-attributed", android_wlfw_attributed, "Android wlfw_start attributed before captured eSoC open"),
        check("v1100-v1102-pm-register-blocks", pm_register_blocks, "CNSS PM register does not return/connect; blocker at pm-service helper 0x9538"),
        check("v1171-v1172-callback-ack-only", callback_ack_only, "PM state callback reaches cnss-daemon but is ack-only"),
        check("v1348-branch-selected", v1348_branch_selected and lower_mutation_blocked, "V1348 selected CNSS/WLFW runtime path before lower mutation"),
        check("guardrails-clear", not forbidden, "no active Wi-Fi/network/credential execution claim in classifier inputs"),
    ]

    if forbidden:
        decision = "v1349-forbidden-action-detected"
        passed = False
        reason = "forbidden active action wording found in inputs: " + ", ".join(forbidden)
        next_step = "audit input reports before another classifier or live gate"
    elif missing or not all(item["pass"] for item in checks[1:6]):
        decision = "v1349-evidence-incomplete"
        passed = False
        reason = "one or more required CNSS/WLFW prerequisite facts are missing or inconsistent"
        next_step = "refresh the failed host-only evidence before live work"
    elif pm_register_blocks and callback_ack_only and v1348_branch_selected:
        decision = "v1349-cnss-pm-register-blocker-is-next-prereq"
        passed = True
        reason = (
            "existing evidence converges on CNSS PM register/connect/vote as the missing prerequisite: "
            "native CNSS reaches netlink but not wlfw_start, Android wlfw_start belongs to the service window, "
            "CNSS PM register blocks in pm-service before connect, and the PM callback body is ack-only"
        )
        next_step = "V1350 should define a compact PM register helper/mutex observer before any lower eSoC mutation"
    else:
        decision = "v1349-cnss-runtime-namespace-still-primary"
        passed = True
        reason = "CNSS runtime path remains selected, but PM register evidence is not strong enough to be the sole next prerequisite"
        next_step = "inspect runtime namespace/property/linker surfaces before tracefs/live work"

    if args.command == "plan":
        decision = "v1349-cnss-wlfw-runtime-prereq-plan-ready"
        passed = True
        reason = "plan-only; no device command or live action executed"
        next_step = "run the V1349 host-only classifier against specific prior reports"

    return {
        "cycle": "v1349",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {name: str(repo_path(path)) for name, path in paths.items()},
        "checks": checks,
        "missing_reports": missing,
        "forbidden_hits": forbidden,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "helper_deploy_executed": False,
        "daemon_start_executed": False,
        "pm_actor_executed": False,
        "tracefs_write_executed": False,
        "sysfs_write_executed": False,
        "debugfs_write_executed": False,
        "direct_esoc_ioctl_executed": False,
        "live_esoc_ioctl_executed": False,
        "live_esoc_notify_executed": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "gdsc_write_executed": False,
        "wifi_hal_start_executed": False,
        "wificond_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["pass"], item["detail"]] for item in manifest["checks"]]
    basis_rows = [
        ["CNSS upper path", "native reaches cld80211 but not wlfw_start/BDF/wlan0; Android reaches wlfw_start/QMI/BDF/wlan0"],
        ["PM register path", "CNSS register enters pm-service but blocks before return/connect at the second/modem helper boundary"],
        ["PM callback path", "state=2 callback reaches cnss-daemon but is ack-only and does not open eSoC"],
        ["next safe branch", manifest["next_step"]],
    ]
    return "\n".join([
        "# V1349 CNSS/WLFW Runtime Prerequisite Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "pass", "detail"], check_rows),
        "",
        "## Decision Basis",
        "",
        markdown_table(["surface", "value"], basis_rows),
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, helper deploy, daemon start, PM actor, tracefs/sysfs/debugfs write, eSoC ioctl/notify, PMIC/GPIO/GDSC write, Wi-Fi HAL, scan/connect, credential, DHCP/route, external ping, flash, boot image write, or partition write was executed.",
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1349 CNSS/WLFW Runtime Prerequisite Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1349`",
        "- Type: host-only evidence classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1349-cnss-wlfw-runtime-prereq-classifier/manifest.json`",
        "  - `tmp/wifi/v1349-cnss-wlfw-runtime-prereq-classifier/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_cnss_wlfw_runtime_prereq_classifier_v1349.py`",
        "",
        "## Key Facts",
        "",
        markdown_table(["fact", "value"], [
            ["CNSS upper path", "V924/V966: native reaches `cld80211` but not `wlfw_start`; Android reaches `wlfw_start`, QMI, BDF, FW-ready, and `wlan0`"],
            ["PM register path", "V1100-V1102: CNSS PM register enters `pm-service`, blocks before return/connect, and stops at the second/modem helper `0x9538` boundary"],
            ["PM callback path", "V1171-V1172: PM `state=2` callback reaches `cnss-daemon`, but the callback body only acknowledges and returns"],
            ["Current branch", "V1348 blocks lower PMIC/GPIO/GDSC/eSoC mutation and selects CNSS/WLFW runtime prerequisites"],
        ]),
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "The next unit should not chase another blind lower eSoC trigger. The highest-signal prerequisite is the CNSS PM register/connect/vote path: native `cnss-daemon` never gets past register, so it cannot issue the same PM continuation that Android's service window reaches before WLFW/QMI/BDF progress.",
        "",
        "## Next",
        "",
        manifest["next_step"],
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, helper deploy, daemon start, PM actor, tracefs/sysfs/debugfs write, eSoC ioctl/notify, PMIC/GPIO/GDSC write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    for name, path in DEFAULT_REPORTS.items():
        parser.add_argument(f"--{name}-report", type=Path, default=path)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def print_result(manifest: dict[str, Any]) -> None:
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"next:     {manifest['next_step']}")
    print(f"evidence: {manifest.get('_run_dir')}")


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    manifest["_run_dir"] = str(store.run_dir)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
