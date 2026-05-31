#!/usr/bin/env python3
"""V1342 host-only classifier for the PM actionability gap.

Compares the current V1341 provider-positive evidence against the V1221
SDX50M-client positive control. No device command is executed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1342-pm-actionability-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1342-pm-actionability-gap-classifier.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1342_PM_ACTIONABILITY_GAP_CLASSIFIER_2026-06-01.md")
DEFAULT_V1341 = Path("tmp/wifi/v1341-android-pre-cnss-provider-policy-ready-live/manifest.json")
DEFAULT_V1341_REPORT = Path("docs/reports/NATIVE_INIT_V1341_ANDROID_PRE_CNSS_PROVIDER_POLICY_READY_2026-06-01.md")
DEFAULT_V1221 = Path("tmp/wifi/v1221-private-cnss-daemon-sdx50m-live/manifest.json")
DEFAULT_V1221_REPORT = Path("docs/reports/NATIVE_INIT_V1221_PRIVATE_CNSS_DAEMON_SDX50M_LIVE_2026-05-31.md")

EXPECTED_PER_MGR_DOMAIN = "u:r:vendor_per_mgr:s0"
EXPECTED_PER_PROXY_DOMAIN = "u:r:vendor_per_proxy:s0"
EXPECTED_V1341_ORDER = (
    "servicemanager,hwservicemanager,vndservicemanager,vndservice_ready_query,"
    "per_proxy_helper,qrtr_ns,rmt_storage,tftp_server,pd_mapper,per_mgr,"
    "vndservice_query,per_proxy,vndservice_query,mdm_helper,cnss_diag,cnss_daemon"
)
WIFI_FORBIDDEN_FLAGS = (
    "wifi_hal_start_executed",
    "scan_connect_executed",
    "credential_use_executed",
    "dhcp_route_executed",
    "external_ping_executed",
    "wifi_bringup_executed",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1341-manifest", type=Path, default=DEFAULT_V1341)
    parser.add_argument("--v1341-report", type=Path, default=DEFAULT_V1341_REPORT)
    parser.add_argument("--v1221-manifest", type=Path, default=DEFAULT_V1221)
    parser.add_argument("--v1221-report", type=Path, default=DEFAULT_V1221_REPORT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"_exists": False, "_path": str(path)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"_exists": True, "_path": str(path), "_json_error": str(exc)}
    if not isinstance(data, dict):
        return {"_exists": True, "_path": str(path), "_json_error": "top-level JSON is not object"}
    data["_exists"] = True
    data["_path"] = str(path)
    return data


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


def str_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def helper_keys(manifest: dict[str, Any]) -> dict[str, str]:
    helper = ((manifest.get("analysis") or {}).get("helper") or {})
    keys = helper.get("keys") or {}
    return {str(key): str(value) for key, value in keys.items()}


def helper_contract(manifest: dict[str, Any]) -> dict[str, str]:
    helper = ((manifest.get("analysis") or {}).get("helper") or {})
    contract = helper.get("contract") or {}
    return {str(key): str(value) for key, value in contract.items()}


def walk_scalars(value: Any) -> list[str]:
    if isinstance(value, dict):
        out: list[str] = []
        for child in value.values():
            out.extend(walk_scalars(child))
        return out
    if isinstance(value, list):
        out = []
        for child in value:
            out.extend(walk_scalars(child))
        return out
    return [str(value)]


def cnss_client_peripherals(v1221: dict[str, Any]) -> list[str]:
    trace = ((v1221.get("analysis") or {}).get("tracefs_uprobe") or {})
    clients = ((trace.get("client_register_args_by_comm") or {}).get("cnss-daemon") or [])
    peripherals: list[str] = []
    if isinstance(clients, list):
        for item in clients:
            if isinstance(item, dict) and item.get("peripheral"):
                peripherals.append(str(item["peripheral"]))
    return peripherals


def contains_all(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return all(needle.lower() in lowered for needle in needles)


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def summarize_v1341(manifest: dict[str, Any], report_text: str) -> dict[str, Any]:
    keys = helper_keys(manifest)
    contract = helper_contract(manifest)
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "policy_load_executed": bool_value(manifest.get("policy_load_executed")),
        "v490_decision": (((manifest.get("analysis") or {}).get("v490_policy_load") or {}).get("decision", "")),
        "provider_after_per_mgr": keys.get("wifi_companion_start.android_pre_cnss_provider.per_mgr.provider_seen", ""),
        "provider_after_per_proxy": keys.get("wifi_companion_start.android_pre_cnss_provider.per_proxy.provider_seen", ""),
        "per_mgr_domain": keys.get("wifi_hal_composite_child.per_mgr.selinux_current.after", ""),
        "per_proxy_domain": keys.get("wifi_hal_composite_child.per_proxy.selinux_current.after", ""),
        "contract_order": contract.get("order", ""),
        "helper_result": contract.get("result", ""),
        "helper_reason": contract.get("reason", ""),
        "all_observable": contract.get("all_observable", ""),
        "all_postflight_safe": contract.get("all_postflight_safe", ""),
        "per_mgr_subsys_esoc0_window": contract.get("per_mgr_subsys_esoc0_window", ""),
        "mdm_helper_esoc0_window": contract.get("mdm_helper_esoc0_window", ""),
        "mdm_helper_subsys_esoc0_window": contract.get("mdm_helper_subsys_esoc0_window", ""),
        "ks_window": contract.get("ks_window", ""),
        "mhi_cmdline_window": contract.get("mhi_cmdline_window", ""),
        "manual_subsys_esoc0_open": contract.get("manual_subsys_esoc0_open", ""),
        "wifi_hal": contract.get("wifi_hal", ""),
        "scan_connect_linkup": contract.get("scan_connect_linkup", ""),
        "external_ping": contract.get("external_ping", ""),
        "wlan0_exists": keys.get("wifi_icnss_edge.window.wlan0_netdev.exists", ""),
        "report_mentions_provider_positive": contains_all(
            report_text,
            ("provider registration side is working", "next blocker is", "PM request/actionability"),
        ),
        "forbidden_wifi_flags_clear": all(not bool_value(manifest.get(flag)) for flag in WIFI_FORBIDDEN_FLAGS),
        "manual_esoc_open_executed": bool_value(manifest.get("manual_esoc_open_executed")),
    }


def summarize_v1221(manifest: dict[str, Any], report_text: str) -> dict[str, Any]:
    private_cnss = manifest.get("private_cnss_daemon") or {}
    peripherals = cnss_client_peripherals(manifest)
    scalars = walk_scalars((manifest.get("analysis") or {}).get("tracefs_uprobe") or {})
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "cnss_daemon_start_executed": bool_value(manifest.get("cnss_daemon_start_executed")),
        "private_cnss_bind_rc": str_value(private_cnss.get("bind_rc")),
        "private_cnss_expected_c_string": str_value(private_cnss.get("expected_c_string")),
        "private_cnss_path": str_value(manifest.get("private_cnss_daemon_path")),
        "cnss_client_peripherals": peripherals,
        "cnss_registered_modem": "modem" in peripherals,
        "cnss_registered_sdx50m": "SDX50M" in peripherals,
        "per_mgr_esoc0_any": bool_value(manifest.get("per_mgr_esoc0_any")),
        "mdm_subsys_powerup_seen": any("mdm_subsys_powerup" in item for item in scalars) or "mdm_subsys_powerup" in report_text,
        "pm_service_esoc_open_seen": bool_value(manifest.get("per_mgr_esoc0_any")) or "__subsystem_get(): esoc0 count:0" in report_text,
        "wlan0_up": bool_value(manifest.get("wlan0_up")),
        "forbidden_wifi_flags_clear": all(not bool_value(manifest.get(flag)) for flag in WIFI_FORBIDDEN_FLAGS),
        "flash_clear": not bool_value(manifest.get("flash_executed")) and not bool_value(manifest.get("partition_write_executed")),
        "report_mentions_sdx50m_route": contains_all(
            report_text,
            ("registered `SDX50M`", "subsys_esoc0", "mdm_subsys_powerup"),
        ),
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1341 = summarize_v1341(read_json(args.v1341_manifest), read_text(args.v1341_report))
    v1221 = summarize_v1221(read_json(args.v1221_manifest), read_text(args.v1221_report))

    v1341_provider_gate_positive = (
        v1341["exists"]
        and v1341["pass"]
        and v1341["decision"] == "v1341-provider-positive-no-lower-transition"
        and v1341["policy_load_executed"]
        and v1341["v490_decision"] == "v490-selinux-policy-load-proof-pass"
        and v1341["provider_after_per_mgr"] == "1"
        and v1341["provider_after_per_proxy"] == "1"
        and v1341["per_mgr_domain"] == EXPECTED_PER_MGR_DOMAIN
        and v1341["per_proxy_domain"] == EXPECTED_PER_PROXY_DOMAIN
        and v1341["contract_order"] == EXPECTED_V1341_ORDER
        and v1341["report_mentions_provider_positive"]
    )
    v1341_lower_transition_absent = (
        v1341["helper_result"] == "start-only-runtime-gap"
        and v1341["per_mgr_subsys_esoc0_window"] == "0"
        and v1341["mdm_helper_esoc0_window"] == "0"
        and v1341["mdm_helper_subsys_esoc0_window"] == "0"
        and v1341["ks_window"] == "0"
        and v1341["mhi_cmdline_window"] == "0"
        and v1341["wlan0_exists"] == "0"
    )
    v1221_positive_control_present = (
        v1221["exists"]
        and v1221["pass"]
        and v1221["decision"] == "v1221-sdx50m-per-mgr-esoc0"
        and v1221["cnss_daemon_start_executed"]
        and v1221["private_cnss_bind_rc"] == "0"
        and v1221["private_cnss_expected_c_string"] == "SDX50M"
        and v1221["cnss_registered_sdx50m"]
        and v1221["per_mgr_esoc0_any"]
        and v1221["pm_service_esoc_open_seen"]
        and v1221["mdm_subsys_powerup_seen"]
        and v1221["report_mentions_sdx50m_route"]
    )
    no_wifi_dependency = (
        v1341["forbidden_wifi_flags_clear"]
        and v1221["forbidden_wifi_flags_clear"]
        and v1221["flash_clear"]
        and v1341["manual_subsys_esoc0_open"] == "0"
        and not v1341["manual_esoc_open_executed"]
    )
    next_gate_implication = (
        v1341_provider_gate_positive
        and v1341_lower_transition_absent
        and v1221_positive_control_present
        and no_wifi_dependency
    )

    checks = [
        check(
            "v1341-provider-gate-positive",
            v1341_provider_gate_positive,
            f"decision={v1341['decision']} providers={v1341['provider_after_per_mgr']}/{v1341['provider_after_per_proxy']} domains={v1341['per_mgr_domain']}/{v1341['per_proxy_domain']}",
        ),
        check(
            "v1341-lower-transition-absent",
            v1341_lower_transition_absent,
            f"esoc={v1341['per_mgr_subsys_esoc0_window']} mdm_esoc={v1341['mdm_helper_esoc0_window']} ks={v1341['ks_window']} mhi={v1341['mhi_cmdline_window']} wlan0={v1341['wlan0_exists']}",
        ),
        check(
            "v1221-sdx50m-positive-control-present",
            v1221_positive_control_present,
            f"decision={v1221['decision']} cnss_clients={','.join(v1221['cnss_client_peripherals'])} per_mgr_esoc0={v1221['per_mgr_esoc0_any']} powerup={v1221['mdm_subsys_powerup_seen']}",
        ),
        check(
            "no-wifi-hal-or-network-dependency",
            no_wifi_dependency,
            f"v1341_wifi_clear={v1341['forbidden_wifi_flags_clear']} v1221_wifi_clear={v1221['forbidden_wifi_flags_clear']} flash_clear={v1221['flash_clear']}",
        ),
        check(
            "next-gate-implication",
            next_gate_implication,
            "provider-positive alone is not actionable; SDX50M CNSS client registration is the proven lower transition trigger",
        ),
    ]

    if next_gate_implication:
        decision = "v1342-sdx50m-client-registration-is-required"
        passed = True
        reason = (
            "V1341 proves PM provider registration and vendor domains are repaired, but lower eSoC/ks/MHI/WLFW surfaces stay absent. "
            "V1221 proves the SDX50M CNSS client registration route moves pm-service to /dev/subsys_esoc0 and mdm_subsys_powerup."
        )
        next_step = (
            "V1343 should combine V1341 provider prerequisites with the V1221-proven SDX50M CNSS client route and compact lower observation; "
            "keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, manual eSoC open, PMIC/GPIO writes, flash, and boot image writes blocked."
        )
    elif v1341_provider_gate_positive and v1341_lower_transition_absent:
        decision = "v1342-pm-provider-actionability-still-unproven"
        passed = True
        reason = "V1341 provider-positive state is proven, but the comparable SDX50M positive-control evidence is incomplete."
        next_step = "Add a narrower observer around PM client registration/Binder request handling before another lower retry."
    else:
        decision = "v1342-evidence-incomplete"
        passed = False
        reason = "Required V1341 provider-positive or lower-absence evidence is missing or inconsistent."
        next_step = "Refresh host evidence before any live gate."

    return {
        "cycle": "v1342",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1341_manifest": str(repo_path(args.v1341_manifest)),
            "v1341_report": str(repo_path(args.v1341_report)),
            "v1221_manifest": str(repo_path(args.v1221_manifest)),
            "v1221_report": str(repo_path(args.v1221_report)),
        },
        "v1341": v1341,
        "v1221": v1221,
        "checks": checks,
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


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[row["name"], row["pass"], row["detail"]] for row in manifest["checks"]]
    v1341 = manifest["v1341"]
    v1221 = manifest["v1221"]
    safety_rows = [[key, manifest.get(key)] for key in (
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
    return "\n".join([
        "# V1342 PM Actionability Gap Classifier",
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
        "## Delta",
        "",
        markdown_table(["surface", "V1341 provider-ready gate", "V1221 SDX50M positive control"], [
            ["Provider", f"mgr={v1341['provider_after_per_mgr']} proxy={v1341['provider_after_per_proxy']} domains={v1341['per_mgr_domain']}/{v1341['per_proxy_domain']}", "already positive in V1341"],
            ["SDX50M client", "not proven in V1341", f"clients={','.join(v1221['cnss_client_peripherals'])}"],
            ["eSoC lower path", f"per_mgr_esoc0={v1341['per_mgr_subsys_esoc0_window']} mdm_esoc={v1341['mdm_helper_esoc0_window']}", f"per_mgr_esoc0={v1221['per_mgr_esoc0_any']} powerup={v1221['mdm_subsys_powerup_seen']}"],
            ["Network/Wi-Fi actions", f"wifi_clear={v1341['forbidden_wifi_flags_clear']}", f"wifi_clear={v1221['forbidden_wifi_flags_clear']}"],
        ]),
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1342 PM Actionability Gap Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1342`",
        "- Type: host/source-only PM actionability classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1342-pm-actionability-gap-classifier/manifest.json`",
        "  - `tmp/wifi/v1342-pm-actionability-gap-classifier/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_pm_actionability_gap_classifier_v1342.py`",
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "The current provider side is no longer the blocker. V1341 proves the",
        "`vendor.qcom.PeripheralManager` provider appears under the repaired",
        "V490 policy-load and `vndservicemanager` readiness contract. It also proves",
        "that provider-positive alone does not move the lower path: no",
        "`/dev/subsys_esoc0`, `mdm_helper` `/dev/esoc-0`, `ks`, MHI, WLFW service 69,",
        "or `wlan0` surface appears in the bounded window.",
        "",
        "V1221 is the positive control for what is missing: when private patched",
        "`cnss-daemon` registers the real `SDX50M` CNSS PM client, `pm-service` reaches",
        "`/dev/subsys_esoc0` and `mdm_subsys_powerup`. Therefore the next unit should",
        "preserve the V1341 provider prerequisites and add only the already-proven",
        "SDX50M CNSS client route plus compact lower observation.",
        "",
        "## Guardrails",
        "",
        "V1342 is host/source-only. It executed no device command, helper deploy,",
        "policy load, daemon start, PM actor, `mdm_helper`, CNSS daemon, tracefs write,",
        "eSoC ioctl/notify, PMIC/GPIO/GDSC write, Wi-Fi HAL, scan/connect, credential",
        "use, DHCP/routes, external ping, flash, boot image write, or partition write.",
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
        manifest["decision"] = "v1342-pm-actionability-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only; no device command or live action executed"
        manifest["next_step"] = "run V1342 host/source-only classifier against V1341 and V1221 evidence"
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print_result(manifest)
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
