#!/usr/bin/env python3
"""V1350 host-only PM register supersession classifier.

Reconciles the V1349 PM-register prerequisite decision with later/current
evidence that already bypassed the old PM mutex blocker and reached lower
subsystem power-up. No device command or live action is performed.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1350-pm-register-supersession-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1350-pm-register-supersession-classifier.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1350_PM_REGISTER_SUPERSESSION_CLASSIFIER_2026-06-01.md")

DEFAULT_REPORTS = {
    "v1103": Path("docs/reports/NATIVE_INIT_V1103_PM_SERVER_NAME_HELPER_TRACEFS_2026-05-27.md"),
    "v1107": Path("docs/reports/NATIVE_INIT_V1107_PM_SERVER_MUTEX_OWNER_CLASSIFIER_2026-05-27.md"),
    "v1108": Path("docs/reports/NATIVE_INIT_V1108_PM_ORDERING_NO_PRE_CNSS_PER_PROXY_2026-05-27.md"),
    "v1109": Path("docs/reports/NATIVE_INIT_V1109_PM_CONNECT_SUBSYSTEM_GET_CLASSIFIER_2026-05-27.md"),
    "v1345": Path("docs/reports/NATIVE_INIT_V1345_CURRENT_ROUTE_MDM2AP_TIMING_SAMPLER_LIVE_2026-06-01.md"),
    "v1347": Path("docs/reports/NATIVE_INIT_V1347_ANDROID_EARLIEST_RESPONSE_RECAPTURE_LIVE_2026-06-01.md"),
    "v1348": Path("docs/reports/NATIVE_INIT_V1348_ANDROID_WLFW_REQUEST_PATH_CLASSIFIER_2026-06-01.md"),
    "v1349": Path("docs/reports/NATIVE_INIT_V1349_CNSS_WLFW_RUNTIME_PREREQ_CLASSIFIER_2026-06-01.md"),
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
        "v1103": args.v1103_report,
        "v1107": args.v1107_report,
        "v1108": args.v1108_report,
        "v1109": args.v1109_report,
        "v1345": args.v1345_report,
        "v1347": args.v1347_report,
        "v1348": args.v1348_report,
        "v1349": args.v1349_report,
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

    v1103 = reports["v1103"]["text"]
    v1107 = reports["v1107"]["text"]
    v1108 = reports["v1108"]["text"]
    v1109 = reports["v1109"]["text"]
    v1345 = reports["v1345"]["text"]
    v1347 = reports["v1347"]["text"]
    v1348 = reports["v1348"]["text"]
    v1349 = reports["v1349"]["text"]

    old_register_mutex_blocker_real = (
        has(v1103, r"v1103-cnss-server-register-no-return-at-pm_server_name_helper_lock_call")
        and has(v1103, r"pthread_mutex_lock\(entry \+ 0x18\)")
        and has(v1107, r"v1107-modem-mutex-owner-blocked-in-subsystem-get")
        and has(v1107, r"pre-CNSS `per_proxy` connect")
    )
    no_pre_cnss_per_proxy_solves_register = (
        has(v1108, r"per_proxy_start_executed=0")
        and has(v1108, r"pm_client_register_ret=\['0x0'\]")
        and has(v1108, r"pm_client_connect_ret=\['0x0'\]")
        and has(v1108, r"removes the V1106/V1107 CNSS mutex wait blocker")
    )
    pm_connect_moves_downward = (
        has(v1109, r"v1109-cnss-pm-connect-triggers-subsystem-get-blocker")
        and has(v1109, r"pm_client_connect_ret=\['0x0'\]")
        and has(v1109, r"__subsystem_get")
        and has(v1109, r"_request_firmware")
    )
    current_route_reaches_lower_powerup = (
        has(v1345, r"v1345-current-route-mdm2ap-full-window-no-transition")
        and has(v1345, r"timing_pm_service_powerup_seen\s+\|\s+True")
        and has(v1345, r"timing_gpio142_irq_delta\s+\|\s+0")
        and has(v1345, r"timing_wlfw_kmsg_max\s+\|\s+0")
        and has(v1345, r"timing_wlan0_seen\s+\|\s+False")
    )
    android_positive_wlfw_chain = (
        has(v1347, r"cnss-daemon wlfw_start")
        and has(v1347, r"icnss_qmi")
        and has(v1347, r"BDF")
        and has(v1347, r"WLAN FW ready")
        and has(v1347, r"`wlan0`")
    )
    current_branch_cnss_wlfw = (
        has(v1348, r"v1348-cnss-wlfw-request-path-before-lower-mutation")
        and has(v1348, r"Do not add PMIC/GPIO/GDSC/eSoC mutation")
    )
    v1349_selected_pm_register = has(v1349, r"v1349-cnss-pm-register-blocker-is-next-prereq")

    checks = [
        check("required-reports-present", not missing, "missing=" + ",".join(missing) if missing else "all required reports present"),
        check("old-register-mutex-blocker-real", old_register_mutex_blocker_real, "V1103/V1107 prove the old CNSS register mutex wait"),
        check("no-pre-cnss-per-proxy-solves-register", no_pre_cnss_per_proxy_solves_register, "V1108 proves CNSS PM register/connect return 0x0 when old ordering is removed"),
        check("pm-connect-moves-downward", pm_connect_moves_downward, "V1109 moves the blocker below PM connect into subsystem_get/request_firmware"),
        check("current-route-reaches-lower-powerup", current_route_reaches_lower_powerup, "V1345 reaches mdm_subsys_powerup and sees no lower response"),
        check("android-positive-wlfw-chain", android_positive_wlfw_chain, "V1347 has Android wlfw/QMI/BDF/FW-ready/wlan0 anchors"),
        check("current-branch-cnss-wlfw", current_branch_cnss_wlfw, "V1348 selects CNSS/WLFW runtime path before lower mutation"),
        check("v1349-local-pm-register-selection-present", v1349_selected_pm_register, "V1349 selected PM register blocker before supersession reconciliation"),
        check("guardrails-clear", not forbidden, "no active Wi-Fi/network/credential execution claim in classifier inputs"),
    ]

    if forbidden:
        decision = "v1350-forbidden-action-detected"
        passed = False
        reason = "forbidden active action wording found in inputs: " + ", ".join(forbidden)
        next_step = "audit input reports before another classifier or live gate"
    elif missing or not all(item["pass"] for item in checks[1:7]):
        decision = "v1350-evidence-incomplete"
        passed = False
        reason = "one or more supersession facts are missing or inconsistent"
        next_step = "refresh missing host-only evidence before changing direction"
    elif no_pre_cnss_per_proxy_solves_register and pm_connect_moves_downward and current_route_reaches_lower_powerup:
        decision = "v1350-pm-register-blocker-superseded-by-current-route"
        passed = True
        reason = (
            "the old PM register mutex blocker is real but superseded: V1108 removes it and reaches CNSS PM connect, "
            "V1109 moves the blocker downward, and V1345's current route already reaches mdm_subsys_powerup with no lower response"
        )
        next_step = (
            "V1351 should define a compact current-route CNSS/WLFW precondition observer before any lower PMIC/GPIO/GDSC/eSoC mutation"
        )
    else:
        decision = "v1350-pm-register-blocker-still-current"
        passed = True
        reason = "later supersession evidence is not strong enough; V1349 PM register branch remains current"
        next_step = "define compact PM register helper/mutex observer"

    if args.command == "plan":
        decision = "v1350-pm-register-supersession-plan-ready"
        passed = True
        reason = "plan-only; no device command or live action executed"
        next_step = "run the V1350 host-only supersession classifier"

    return {
        "cycle": "v1350",
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
    rows = [[item["name"], item["pass"], item["detail"]] for item in manifest["checks"]]
    basis = [
        ["old PM register blocker", "V1103/V1107: real mutex wait caused by pre-CNSS `per_proxy` ordering"],
        ["supersession", "V1108: CNSS PM register/connect return 0x0 when that ordering is removed"],
        ["downstream blocker", "V1109/V1345: blocker is now lower subsystem/powerup/no-response"],
        ["next safe branch", manifest["next_step"]],
    ]
    return "\n".join([
        "# V1350 PM Register Supersession Classifier",
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
        markdown_table(["check", "pass", "detail"], rows),
        "",
        "## Decision Basis",
        "",
        markdown_table(["surface", "value"], basis),
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, helper deploy, daemon start, PM actor, tracefs/sysfs/debugfs write, eSoC ioctl/notify, PMIC/GPIO/GDSC write, Wi-Fi HAL, scan/connect, credential, DHCP/route, external ping, flash, boot image write, or partition write was executed.",
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1350 PM Register Supersession Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1350`",
        "- Type: host-only corrective evidence classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1350-pm-register-supersession-classifier/manifest.json`",
        "  - `tmp/wifi/v1350-pm-register-supersession-classifier/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_pm_register_supersession_classifier_v1350.py`",
        "",
        "## Key Facts",
        "",
        markdown_table(["fact", "value"], [
            ["old blocker", "V1103/V1107 prove the CNSS PM register mutex wait existed"],
            ["superseded by ordering", "V1108 removes the pre-CNSS `per_proxy` ordering and CNSS PM register/connect both return `0x0`"],
            ["moved downward", "V1109 moves the blocker below PM connect into `__subsystem_get` / `_request_firmware`"],
            ["current route", "V1345 reaches `mdm_subsys_powerup` but still sees no GPIO142/PCIe/MHI/WLFW/`wlan0` response"],
            ["Android positive", "V1347 reaches `wlfw_start`, ICNSS QMI, BDF, FW-ready, and `wlan0`"],
        ]),
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "V1349's PM-register conclusion is superseded as the immediate next branch. Repeating the old PM register/mutex observer would not move the current route forward, because the project already has evidence that CNSS PM connect can succeed and that the active blocker is now lower response plus Android-only WLFW request-path parity.",
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
