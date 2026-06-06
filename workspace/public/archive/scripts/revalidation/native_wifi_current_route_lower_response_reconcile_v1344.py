#!/usr/bin/env python3
"""V1344 host-only lower-response reconciliation classifier.

Compares the current V1343 SDX50M route result against prior lower-response
classifiers. No device command is executed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1344-current-route-lower-response-reconcile")
LATEST_POINTER = Path("tmp/wifi/latest-v1344-current-route-lower-response-reconcile.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1344_CURRENT_ROUTE_LOWER_RESPONSE_RECONCILIATION_2026-06-01.md")
DEFAULT_V1343 = Path("tmp/wifi/v1343-provider-ready-sdx50m-route-live/manifest.json")
DEFAULT_V1222 = Path("tmp/wifi/v1222-post-esoc-power-boundary-live/manifest.json")
DEFAULT_V1318 = Path("tmp/wifi/v1318-critical-lower-trace-collector-live/manifest.json")
DEFAULT_V1324 = Path("tmp/wifi/v1324-provider-response-delta-classifier/manifest.json")
DEFAULT_V1222_REPORT = Path("docs/reports/NATIVE_INIT_V1222_POST_ESOC_POWER_BOUNDARY_2026-05-31.md")
DEFAULT_V1318_REPORT = Path("docs/reports/NATIVE_INIT_V1318_CRITICAL_LOWER_TRACE_COLLECTOR_2026-05-31.md")
DEFAULT_V1324_REPORT = Path("docs/reports/NATIVE_INIT_V1324_PROVIDER_RESPONSE_DELTA_CLASSIFIER_2026-05-31.md")
DEFAULT_V1343_REPORT = Path("docs/reports/NATIVE_INIT_V1343_PROVIDER_READY_SDX50M_ROUTE_LIVE_2026-06-01.md")

FORBIDDEN_FLAGS = (
    "wifi_hal_start_executed",
    "scan_connect_executed",
    "credential_use_executed",
    "dhcp_route_executed",
    "external_ping_executed",
    "wifi_bringup_executed",
    "flash_executed",
    "partition_write_executed",
    "pmic_write_executed",
    "gpio_line_request_executed",
    "direct_esoc_ioctl_executed",
    "live_esoc_ioctl_executed",
    "live_esoc_notify_executed",
    "boot_image_write_executed",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1343-manifest", type=Path, default=DEFAULT_V1343)
    parser.add_argument("--v1222-manifest", type=Path, default=DEFAULT_V1222)
    parser.add_argument("--v1318-manifest", type=Path, default=DEFAULT_V1318)
    parser.add_argument("--v1324-manifest", type=Path, default=DEFAULT_V1324)
    parser.add_argument("--v1343-report", type=Path, default=DEFAULT_V1343_REPORT)
    parser.add_argument("--v1222-report", type=Path, default=DEFAULT_V1222_REPORT)
    parser.add_argument("--v1318-report", type=Path, default=DEFAULT_V1318_REPORT)
    parser.add_argument("--v1324-report", type=Path, default=DEFAULT_V1324_REPORT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"_exists": False, "_path": str(path)}
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"_exists": True, "_path": str(path), "_json_error": str(exc)}
    if not isinstance(value, dict):
        return {"_exists": True, "_path": str(path), "_json_error": "top-level JSON is not object"}
    value["_exists"] = True
    value["_path"] = str(path)
    return value


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "pass"}
    return False


def int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def float_value(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return fallback


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def forbidden_hits(*manifests: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    for index, manifest in enumerate(manifests):
        route = ((manifest.get("analysis") or {}).get("v1221_route") or {})
        for flag in FORBIDDEN_FLAGS:
            if bool_value(manifest.get(flag)) or bool_value(route.get(flag)):
                hits.append(f"input{index}.{flag}")
    return hits


def summarize_v1343(manifest: dict[str, Any], report_text: str) -> dict[str, Any]:
    route = ((manifest.get("analysis") or {}).get("v1221_route") or {})
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": str(manifest.get("decision", "")),
        "pass": bool_value(manifest.get("pass")),
        "route_decision": str(route.get("decision", "")),
        "sdx50m_registered": bool_value(route.get("sdx50m_registered")),
        "per_mgr_esoc0_any": bool_value(route.get("per_mgr_esoc0_any")),
        "wlfw_or_wlan_dmesg_seen": bool_value(route.get("wlfw_or_wlan_dmesg_seen")),
        "wlan0_up": bool_value(route.get("wlan0_up")),
        "report_mentions_current_gap": (
            "per_mgr_esoc0_any | True" in report_text
            and "wlfw_or_wlan_dmesg_seen | False" in report_text
            and "wlan0_up | False" in report_text
        ),
    }


def summarize_v1222(manifest: dict[str, Any], report_text: str) -> dict[str, Any]:
    boundary = manifest.get("post_esoc_boundary") or {}
    states = boundary.get("mdm3_state_transitions") or []
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": str(manifest.get("decision", "")),
        "pass": bool_value(manifest.get("pass")),
        "esoc_open_seen": bool_value(boundary.get("esoc_open_seen")),
        "esoc_syscall_seen": bool_value(boundary.get("esoc_syscall_seen")),
        "max_dmesg_esoc_open_count": int_value(boundary.get("max_dmesg_esoc_open_count")),
        "max_dmesg_wlfw_count": int_value(boundary.get("max_dmesg_wlfw_count")),
        "max_dmesg_modem_down_count": int_value(boundary.get("max_dmesg_modem_down_count")),
        "mdm3_state_transitions": [str(item) for item in states],
        "report_mentions_boundary": (
            "subsys_esoc0" in report_text
            and "WLFW/BDF/`wlan0` marker count: max `0`" in report_text
        ),
    }


def summarize_v1318(manifest: dict[str, Any], report_text: str) -> dict[str, Any]:
    critical = manifest.get("critical_line_classification") or {}
    response = manifest.get("response_sampler") or {}
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": str(manifest.get("decision", "")),
        "pass": bool_value(manifest.get("pass")),
        "gpio1270_line_count": int_value(critical.get("gpio1270_line_count")),
        "gpio135_high_count": int_value(critical.get("gpio135_high_count")),
        "gpio135_line_count": int_value(critical.get("gpio135_line_count")),
        "gpio142_line_count": int_value(critical.get("gpio142_line_count")),
        "post_gpio135_sample_span_sec": float_value(critical.get("post_gpio135_sample_span_sec")),
        "esoc_pil_notif_count": int_value(critical.get("esoc_pil_notif_count")),
        "mhi_pipe_seen": bool_value(response.get("mhi_pipe_seen")),
        "max_kmsg_pcie_count": int_value(response.get("max_kmsg_pcie_count")),
        "max_kmsg_mhi_count": int_value(response.get("max_kmsg_mhi_count")),
        "max_kmsg_wlfw_count": int_value(response.get("max_kmsg_wlfw_count")),
        "wlan0_seen": bool_value(response.get("wlan0_seen")),
        "report_mentions_gpio_gap": "GPIO1270 / GPIO135 / GPIO142 lines | 5 / 2 / 0" in report_text,
    }


def summarize_v1324(manifest: dict[str, Any], report_text: str) -> dict[str, Any]:
    checks = {str(item.get("name")): bool_value(item.get("pass")) for item in manifest.get("checks", []) if isinstance(item, dict)}
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": str(manifest.get("decision", "")),
        "pass": bool_value(manifest.get("pass")),
        "native_trigger_reaches_ap_side": checks.get("native-trigger-reaches-ap-side", False),
        "native_mdm_side_silent": checks.get("native-mdm-side-silent", False),
        "android_downstream_response_present": checks.get("android-downstream-response-present", False),
        "guardrails_clear": checks.get("guardrails-clear", False),
        "report_mentions_gap": "post-AP2MDM MDM2AP/PCIe response gap" in report_text,
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1343_manifest = load_json(args.v1343_manifest)
    v1222_manifest = load_json(args.v1222_manifest)
    v1318_manifest = load_json(args.v1318_manifest)
    v1324_manifest = load_json(args.v1324_manifest)
    v1343 = summarize_v1343(v1343_manifest, read_text(args.v1343_report))
    v1222 = summarize_v1222(v1222_manifest, read_text(args.v1222_report))
    v1318 = summarize_v1318(v1318_manifest, read_text(args.v1318_report))
    v1324 = summarize_v1324(v1324_manifest, read_text(args.v1324_report))

    forbidden = forbidden_hits(v1343_manifest, v1222_manifest, v1318_manifest, v1324_manifest)
    current_route_ok = (
        v1343["exists"]
        and v1343["pass"]
        and v1343["decision"] == "v1343-sdx50m-route-esoc-powerup-observed"
        and v1343["route_decision"] == "v1221-sdx50m-per-mgr-esoc0"
        and v1343["sdx50m_registered"]
        and v1343["per_mgr_esoc0_any"]
        and not v1343["wlfw_or_wlan_dmesg_seen"]
        and not v1343["wlan0_up"]
        and v1343["report_mentions_current_gap"]
    )
    v1222_boundary_ok = (
        v1222["exists"]
        and v1222["pass"]
        and v1222["decision"] == "v1222-esoc-powerup-crash-before-wlfw"
        and v1222["esoc_open_seen"]
        and v1222["esoc_syscall_seen"]
        and v1222["max_dmesg_esoc_open_count"] > 0
        and v1222["max_dmesg_wlfw_count"] == 0
        and "OFFLINING" in v1222["mdm3_state_transitions"]
        and v1222["report_mentions_boundary"]
    )
    v1318_ap_side_ok = (
        v1318["exists"]
        and v1318["pass"]
        and v1318["decision"] == "v1318-target-critical-lines-captured"
        and v1318["gpio1270_line_count"] > 0
        and v1318["gpio135_high_count"] > 0
        and v1318["gpio142_line_count"] == 0
        and v1318["post_gpio135_sample_span_sec"] >= 10.0
        and not v1318["mhi_pipe_seen"]
        and v1318["max_kmsg_pcie_count"] == 0
        and v1318["max_kmsg_mhi_count"] == 0
        and v1318["max_kmsg_wlfw_count"] == 0
        and not v1318["wlan0_seen"]
    )
    v1324_delta_ok = (
        v1324["exists"]
        and v1324["pass"]
        and v1324["decision"] == "v1324-delta-is-post-ap2mdm-mdm2ap-response-gap"
        and v1324["native_trigger_reaches_ap_side"]
        and v1324["native_mdm_side_silent"]
        and v1324["android_downstream_response_present"]
        and v1324["guardrails_clear"]
        and v1324["report_mentions_gap"]
    )

    checks = [
        check(
            "v1343-current-route-reaches-esoc-without-wlfw",
            current_route_ok,
            (
                f"decision={v1343['decision']} route={v1343['route_decision']} "
                f"sdx50m={v1343['sdx50m_registered']} esoc={v1343['per_mgr_esoc0_any']} "
                f"wlfw={v1343['wlfw_or_wlan_dmesg_seen']} wlan0={v1343['wlan0_up']}"
            ),
        ),
        check(
            "v1222-post-esoc-boundary-matches",
            v1222_boundary_ok,
            (
                f"decision={v1222['decision']} esoc_open={v1222['esoc_open_seen']} "
                f"wlfw_count={v1222['max_dmesg_wlfw_count']} states={v1222['mdm3_state_transitions']}"
            ),
        ),
        check(
            "v1318-ap-side-without-mdm-response",
            v1318_ap_side_ok,
            (
                f"gpio1270={v1318['gpio1270_line_count']} gpio135_high={v1318['gpio135_high_count']} "
                f"gpio142={v1318['gpio142_line_count']} pcie={v1318['max_kmsg_pcie_count']} "
                f"mhi={v1318['max_kmsg_mhi_count']} wlan0={v1318['wlan0_seen']}"
            ),
        ),
        check(
            "v1324-delta-still-authoritative",
            v1324_delta_ok,
            (
                f"decision={v1324['decision']} ap={v1324['native_trigger_reaches_ap_side']} "
                f"silent={v1324['native_mdm_side_silent']} android={v1324['android_downstream_response_present']}"
            ),
        ),
        check(
            "no-forbidden-actions-in-reconciled-inputs",
            not forbidden,
            ", ".join(forbidden) if forbidden else "no Wi-Fi/network/flash/PMIC/GPIO/eSoC mutation flags observed",
        ),
    ]

    if forbidden:
        decision = "v1344-forbidden-action-detected"
        passed = False
        reason = f"forbidden action flags present: {', '.join(forbidden)}"
        next_step = "stop and audit the evidence chain before any additional live gate"
    elif v1343["wlfw_or_wlan_dmesg_seen"] or v1343["wlan0_up"]:
        decision = "v1344-unexpected-wlfw-or-wlan0"
        passed = True
        reason = "V1343 already observed WLFW/BDF or wlan0 readiness"
        next_step = "classify readiness before Wi-Fi HAL, scan/connect, DHCP, or external ping"
    elif not current_route_ok and v1343["exists"]:
        decision = "v1344-route-regressed-before-esoc"
        passed = False
        reason = "V1343 no longer proves SDX50M registration and eSoC reachability"
        next_step = "repair provider/CNSS route before lower-response work"
    elif current_route_ok and v1222_boundary_ok and v1318_ap_side_ok and v1324_delta_ok:
        decision = "v1344-current-route-matches-post-ap2mdm-response-gap"
        passed = True
        reason = (
            "V1343 reproduces the SDX50M/eSoC route and still stops before WLFW/wlan0; "
            "V1222/V1318/V1324 classify the same blocker as AP-side eSoC activity without MDM2AP/PCIe/MHI response."
        )
        next_step = (
            "V1345 should be a bounded live lower-response sampler using the current V1343 route, "
            "focused on GPIO142, PCIe RC1/LTSSM, MHI/ks, WLFW/BDF, wlan0, and mdm3 state; "
            "keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, "
            "manual eSoC open, and flash blocked."
        )
    else:
        decision = "v1344-insufficient-evidence"
        passed = False
        reason = "Required current-route or prior lower-response evidence is missing or inconsistent"
        next_step = "refresh only the missing host report or bounded live evidence before choosing V1345"

    return {
        "cycle": "v1344",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1343_manifest": str(repo_path(args.v1343_manifest)),
            "v1222_manifest": str(repo_path(args.v1222_manifest)),
            "v1318_manifest": str(repo_path(args.v1318_manifest)),
            "v1324_manifest": str(repo_path(args.v1324_manifest)),
        },
        "v1343": v1343,
        "v1222": v1222,
        "v1318": v1318,
        "v1324": v1324,
        "checks": checks,
        "forbidden_hits": forbidden,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "policy_load_executed": False,
        "daemon_start_executed": False,
        "pm_actor_executed": False,
        "mdm_helper_executed": False,
        "cnss_daemon_start_executed": False,
        "tracefs_write_executed": False,
        "live_esoc_ioctl_executed": False,
        "live_esoc_notify_executed": False,
        "manual_esoc_open_executed": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "direct_esoc_ioctl_executed": False,
        "gdsc_write_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
        "partition_write_executed": False,
    }


def safety_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    return [[key, manifest.get(key)] for key in (
        "device_commands_executed",
        "device_mutations",
        "policy_load_executed",
        "daemon_start_executed",
        "pm_actor_executed",
        "mdm_helper_executed",
        "cnss_daemon_start_executed",
        "tracefs_write_executed",
        "live_esoc_ioctl_executed",
        "live_esoc_notify_executed",
        "manual_esoc_open_executed",
        "pmic_write_executed",
        "gpio_line_request_executed",
        "direct_esoc_ioctl_executed",
        "gdsc_write_executed",
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
        "wifi_bringup_executed",
        "flash_executed",
        "partition_write_executed",
    )]


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[row["name"], row["pass"], row["detail"]] for row in manifest["checks"]]
    return "\n".join([
        "# V1344 Current Route Lower Response Reconciliation",
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
        "## Evidence Delta",
        "",
        markdown_table(["surface", "V1343 current route", "Prior lower-response record"], [
            [
                "SDX50M/eSoC",
                f"sdx50m={manifest['v1343']['sdx50m_registered']} esoc={manifest['v1343']['per_mgr_esoc0_any']}",
                f"V1222 esoc_open={manifest['v1222']['esoc_open_seen']}",
            ],
            [
                "AP-side response",
                "not directly sampled in V1343 wrapper",
                f"V1318 gpio135_high={manifest['v1318']['gpio135_high_count']} gpio142={manifest['v1318']['gpio142_line_count']}",
            ],
            [
                "Downstream response",
                f"wlfw={manifest['v1343']['wlfw_or_wlan_dmesg_seen']} wlan0={manifest['v1343']['wlan0_up']}",
                f"V1324={manifest['v1324']['decision']}",
            ],
        ]),
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], safety_rows(manifest)),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    check_rows = [[row["name"], row["pass"], row["detail"]] for row in manifest["checks"]]
    return "\n".join([
        "# Native Init V1344 Current Route Lower Response Reconciliation",
        "",
        "## Summary",
        "",
        "- Cycle: `V1344`",
        "- Type: host-only lower-response reconciliation classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1344-current-route-lower-response-reconcile/manifest.json`",
        "  - `tmp/wifi/v1344-current-route-lower-response-reconcile/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_current_route_lower_response_reconcile_v1344.py`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "pass", "detail"], check_rows),
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "V1344 keeps the Wi-Fi objective blocked at the lower SDX50M response",
        "boundary. The current route is actionable enough to reach PM/eSoC, but the",
        "reconciled record still has no MDM2AP/GPIO142, PCIe RC1/LTSSM, MHI/ks,",
        "WLFW/BDF, or `wlan0` evidence on native init.",
        "",
        "## Guardrails",
        "",
        "V1344 is host-only. It executed no device command, helper deploy, policy",
        "load, daemon start, PM actor, `mdm_helper`, CNSS daemon, tracefs write,",
        "eSoC ioctl/notify, manual eSoC open, PMIC/GPIO/GDSC write, Wi-Fi HAL,",
        "scan/connect, credential use, DHCP/routes, external ping, flash, boot",
        "image write, or partition write.",
        "",
        "## Next",
        "",
        manifest["next_step"],
        "",
    ])


def print_result(manifest: dict[str, Any]) -> None:
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {manifest.get('_run_dir')}/manifest.json")


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    manifest["_run_dir"] = str(store.run_dir)
    if args.command == "plan":
        manifest["decision"] = "v1344-current-route-reconciliation-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only; no device command or live action executed"
        manifest["next_step"] = "run V1344 host-only reconciliation against V1343/V1222/V1318/V1324 evidence"
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print_result(manifest)
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
