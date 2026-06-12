#!/usr/bin/env python3
"""Inventory current revalidation scripts without moving or deleting them."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import stat
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root


REPO_ROOT = repo_root()
SCRIPT_ROOT = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "REVALIDATION_SCRIPT_INVENTORY_2026-06-10.md"
JSON_PATH = REPO_ROOT / "docs" / "reports" / "REVALIDATION_SCRIPT_INVENTORY_2026-06-10.json"

ACTIVE = {
    "a90ctl.py": "cmdv1 operator/client entrypoint",
    "a90_bridge.py": "bridge lifecycle wrapper",
    "serial_tcp_bridge.py": "bridge implementation",
    "a90_ncm_transport_smoke.py": "active NCM transport smoke",
    "a90_wifi_profile_stage.py": "active Wi-Fi profile staging helper",
    "native_init_flash.py": "active flash/rollback helper",
    "native_wifi_connect_carrier_handoff_v2174.py": "active Wi-Fi carrier validation",
    "native_wifi_dhcp_ping_handoff_v2176.py": "active Wi-Fi DHCP/ping validation",
    "native_wifi_hold_reconnect_handoff_v2177.py": "active Wi-Fi hold/reconnect validation",
    "native_wifi_v2178_autoconnect_phase_validation.py": "active V2178 Wi-Fi autoconnect phase validation",
    "native_wifi_supplicant_dependency_probe.py": "current Wi-Fi dependency probe",
    "a90_v725_fasttransport_baseline_validation.py": "fast transport baseline validator",
    "build_native_init_boot_v724.py": "baseline/emergency boot builder",
    "build_native_init_boot_v725_fasttransport.py": "fast transport boot builder",
    "build_native_init_boot_v726_wifi_lifecycle.py": "Wi-Fi lifecycle source builder",
    "build_native_init_boot_v2169_transport_contract.py": "transport contract boot builder",
    "build_native_init_wifi_test_boot_v2168.py": "Wi-Fi test boot builder dependency",
    "build_native_init_boot_v2170_wifi_config_prepare.py": "Wi-Fi config prepare boot builder",
    "build_native_init_boot_v2172_wifi_status_scan.py": "Wi-Fi status/scan boot builder",
    "build_native_init_boot_v2174_wifi_urandom_connect.py": "Wi-Fi carrier boot builder",
    "build_native_init_boot_v2176_wifi_dhcp.py": "Wi-Fi DHCP boot builder",
    "build_native_init_boot_v2178_wifi_profile_autoconnect.py": "Wi-Fi profile/autoconnect boot builder",
    "build_native_init_boot_v2182_hud_menu_cleanup.py": "HUD/menu cleanup baseline boot builder",
    "build_native_init_boot_v2184_network_ui_p0_p1.py": "network UI P0/P1 boot builder",
    "build_native_init_boot_v2185_network_ping_test.py": "network ping test boot builder",
    "build_native_init_boot_v2186_wifi_ui_polish.py": "Wi-Fi UI polish boot builder",
    "build_native_init_boot_v2187_screenapp_ui_validation.py": "screenapp UI validation boot builder",
    "native_ui_screenapp_validation_v2187.py": "active V2187 screenapp UI validation",
    "native_init_frontier_select.py": "native-init frontier selector/audit utility",
    "native_kernel_workqueue_fwclass_oracle_plan_v2272.py": "T1 workqueue firmware_class oracle plan utility",
}
MODULES = {
    "_workspace_bootstrap.py": "workspace path bootstrap",
    "a90_kernel_tools.py": "kernel inspection helper module",
    "a90_ncm_transport.py": "NCM host/device helper module",
    "a90_serial_lock.py": "serial bridge lock helper",
    "a90_transport.py": "shared bridge/transport selector",
    "tcpctl_host.py": "tcpctl host protocol helper",
}
ARCHIVED_ENTRYPOINTS = {
    "native_wifi_connect_dhcp_google_ping_handoff_v2167.py": (
        "superseded by V2174/V2176 split lifecycle runners"
    ),
}
UTILITY_PREFIXES = (
    "cleanup_",
    "inventory_",
)
UTILITY_NAMES = {
    "a90_ncm_host_preflight.py",
    "ncm_host_setup.py",
    "netservice_reconnect_soak.py",
    "cpu_mem_thermal_stability.py",
    "kselftest_feasibility.py",
    "storage_iotest.py",
    "usb_recovery_validate.py",
}
ACTIVE_PATTERN_REASONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"^build_native_init_boot_v\d+_.*\.py$"),
        "native-init boot artifact builder",
    ),
    (
        re.compile(r"^build_native_init_wifi_test_boot_v\d+.*\.py$"),
        "native-init Wi-Fi test boot builder",
    ),
    (
        re.compile(r"^native_kernel_.*\.py$"),
        "kernel-observation runner or postprocessor",
    ),
    (
        re.compile(r"^a90_kernel_v\d+_.*\.py$"),
        "host-side kernel-observation analyzer",
    ),
    (
        re.compile(r"^security_.*_regression\.py$"),
        "local security regression utility",
    ),
)
ACTIVE_UTILITY_NAMES = {
    "a90_kernel_stack_symbolize.py": "kernel stack symbolization utility",
    "a90_stock_kallsyms_extract.py": "stock kernel kallsyms extraction utility",
}
HOST_ONLY_PATTERNS = (
    re.compile(r"^a90_kernel_v\d+_.*\.py$"),
    re.compile(r"^security_.*_regression\.py$"),
)
HOST_ONLY_NAMES = set(ACTIVE_UTILITY_NAMES)
PHASE_TIMER_EXEMPT = {
    "ncm_host_setup.py": "interactive host NCM setup utility; no manifest contract",
    "netservice_reconnect_soak.py": "interactive netservice lifecycle utility; no manifest contract",
}
RESIDUAL_STATE_EXEMPT = {
    **PHASE_TIMER_EXEMPT,
    "native_init_flash.py": "flash helper; caller runner records rollback/residual state",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write markdown and JSON reports")
    parser.add_argument("--json", action="store_true", help="print JSON to stdout")
    parser.add_argument("--root", type=Path, default=SCRIPT_ROOT)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--json-out", type=Path, default=JSON_PATH)
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except UnicodeDecodeError:
        return ""


def repo_reference_count(name: str) -> int:
    count = 0
    for root in (REPO_ROOT / "docs", REPO_ROOT / "workspace" / "public"):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".py", ".sh", ".json"}:
                continue
            if path.name == name:
                continue
            if name in read_text(path):
                count += 1
    return count


def classify(path: Path, text: str) -> tuple[str, str]:
    name = path.name
    if name in ACTIVE:
        return "active", ACTIVE[name]
    if name in ACTIVE_UTILITY_NAMES:
        return "active", ACTIVE_UTILITY_NAMES[name]
    if name in MODULES:
        return "module", MODULES[name]
    if name == "README.md":
        return "active", "current entrypoint index"
    if path.is_dir() and name == "__pycache__":
        return "delete-review", "generated Python bytecode cache"
    if name in UTILITY_NAMES or name.startswith(UTILITY_PREFIXES):
        return "active", "operator utility or inventory/cleanup utility"
    if path.suffix == ".sh" and name.startswith("build_"):
        return "active", "build utility shell entrypoint"
    if not path.is_file():
        return "delete-review", "non-file entry in script root"
    if "TODO" in text or "deprecated" in text.lower():
        return "delete-review", "requires manual review before keeping"
    for pattern, reason in ACTIVE_PATTERN_REASONS:
        if pattern.match(name):
            return "active", reason
    if "native_init_flash.py" in text or "a90ctl.py" in text:
        return "active", "scripted live-device workflow"
    return "delete-review", "unclassified top-level script"


def requires_live_device(path: Path, text: str) -> bool:
    name = path.name
    if name in HOST_ONLY_NAMES or any(pattern.match(name) for pattern in HOST_ONLY_PATTERNS):
        return False
    if name == "README.md" or name.startswith("build_") or name.startswith("inventory_") or name.startswith("cleanup_"):
        return False
    tokens = (
        "native_init_flash.py",
        "a90ctl.py",
        "run_cmdv1_command",
        "netservice",
        "reboot",
        "adb",
        "fastboot",
        "tcpctl",
        "serial_tcp_bridge",
        "run_serial_step",
        "run_serial_command_recovered",
        "FastTransferSession",
    )
    return name in {"a90ctl.py", "a90_bridge.py", "serial_tcp_bridge.py"} or any(token in text for token in tokens)


def imports_module(text: str, module: str) -> bool:
    pattern = rf"^\s*(?:import\s+{re.escape(module)}\b|from\s+{re.escape(module)}\s+import\b)"
    return re.search(pattern, text, flags=re.MULTILINE) is not None


def direct_a90ctl_group(name: str) -> dict[str, Any]:
    if name == "native_wifi_detail_surface_handoff_v2255.py":
        return {
            "group": "current_baseline_wifi_surface",
            "impact_score": 90,
            "actionable_now": True,
            "migration_gate": "changed-current-baseline-runner",
            "reason": "current V2254 baseline live-surface validator",
            "recommended_action": "migrate direct a90ctl command lists if this current-baseline runner is changed again",
        }
    if name in {
        "native_kernel_a90_boot_window_handoff_v2225.py",
        "native_kernel_a90_boot_window_handoff_v2227.py",
        "native_kernel_a90_post_bdf_hold_handoff_v2231.py",
        "native_kernel_a90_service_object_fwclass_bridge_handoff_v2233.py",
        "native_kernel_a90_service_object_visible_handoff_v2229.py",
        "native_kernel_fwclass_boundary_stack_handoff_v2253.py",
    }:
        return {
            "group": "flash_capable_kernel_handoff_runners",
            "impact_score": 80,
            "actionable_now": False,
            "migration_gate": "revive-for-bounded-live-run",
            "reason": "rollbackable flash-capable historical kernel/WLAN observer",
            "recommended_action": "migrate only if reviving or modifying this flash-capable observer family",
        }
    if name in {
        "native_kernel_a90_boot_window_preflight_v2222.py",
        "native_kernel_a90_uprobe_trace_buffer_collector_v2219.py",
        "native_kernel_static_tracepoint_object_chain_audit_v2238.py",
        "native_kernel_wlan_tracepoint_catalog_v2218.py",
    }:
        return {
            "group": "live_readonly_kernel_catalog_runners",
            "impact_score": 60,
            "actionable_now": False,
            "migration_gate": "revive-or-modify-observer",
            "reason": "read-only live observer/catalog runner with direct a90ctl subprocess helper",
            "recommended_action": "prefer shared transport serial helpers when next changing this observer",
        }
    if name in {
        "native_kernel_file_ops_anchor_v2204.py",
        "native_kernel_timer_object_context_v2201.py",
        "native_kernel_timer_object_histogram_v2202.py",
        "native_kernel_timer_start_context_v2200.py",
    }:
        return {
            "group": "legacy_bpf_anchor_runners",
            "impact_score": 40,
            "actionable_now": False,
            "migration_gate": "reactivate-legacy-anchor",
            "reason": "older BPF/perf anchor runner retained for provenance",
            "recommended_action": "review-only unless the old anchor runner is reactivated",
        }
    return {
        "group": "ungrouped_direct_a90ctl_reference",
        "impact_score": 10,
        "actionable_now": False,
        "migration_gate": "manual-review",
        "reason": "direct a90ctl reference not matched by current grouping rules",
        "recommended_action": "inspect manually before migration",
    }


def direct_a90ctl_candidate_groups(names: list[str]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for name in names:
        detail = direct_a90ctl_group(name)
        group = groups.setdefault(detail["group"], {
            "group": detail["group"],
            "impact_score": detail["impact_score"],
            "actionable_now": detail["actionable_now"],
            "migration_gate": detail["migration_gate"],
            "reason": detail["reason"],
            "recommended_action": detail["recommended_action"],
            "count": 0,
            "names": [],
        })
        group["impact_score"] = max(group["impact_score"], detail["impact_score"])
        group["actionable_now"] = bool(group["actionable_now"] or detail["actionable_now"])
        group["count"] += 1
        group["names"].append(name)
    return sorted(
        groups.values(),
        key=lambda item: (-int(item["impact_score"]), str(item["group"])),
    )


def consolidation_signals(entries: list[dict[str, Any]]) -> dict[str, Any]:
    direct_a90ctl = [
        entry["name"] for entry in entries
        if entry["mentions_a90ctl_subprocess"] and entry["name"] not in {"README.md", "a90ctl.py"}
    ]
    live_without_phase = [
        entry["name"] for entry in entries
        if entry["live_device_required"]
        and entry["label"] == "active"
        and not entry["has_phase_timer"]
        and entry["name"] not in {"a90ctl.py", "a90_bridge.py", "serial_tcp_bridge.py"}
        and entry["name"] not in PHASE_TIMER_EXEMPT
        and not entry["name"].startswith("build_")
    ]
    live_phase_exempt = [
        entry["name"] for entry in entries
        if entry["live_device_required"]
        and entry["label"] == "active"
        and not entry["has_phase_timer"]
        and entry["name"] in PHASE_TIMER_EXEMPT
    ]
    live_without_residual = [
        entry["name"] for entry in entries
        if entry["live_device_required"]
        and entry["label"] == "active"
        and not entry["has_residual_state"]
        and entry["name"] not in {"a90ctl.py", "a90_bridge.py", "serial_tcp_bridge.py"}
        and entry["name"] not in RESIDUAL_STATE_EXEMPT
        and not entry["name"].startswith("build_")
    ]
    live_residual_exempt = [
        entry["name"] for entry in entries
        if entry["live_device_required"]
        and entry["label"] == "active"
        and not entry["has_residual_state"]
        and entry["name"] in RESIDUAL_STATE_EXEMPT
    ]
    secret_related = [
        entry["name"] for entry in entries
        if entry["has_secret_redaction"]
    ]
    source_delete_review = [
        entry["name"] for entry in entries
        if entry["label"] == "delete-review"
    ]
    candidate_groups = direct_a90ctl_candidate_groups(direct_a90ctl)
    actionable_groups = [group for group in candidate_groups if group["actionable_now"]]
    review_only_groups = [group for group in candidate_groups if not group["actionable_now"]]
    actionable_names = [
        name
        for group in actionable_groups
        for name in group["names"]
    ]
    review_only_names = [
        name
        for group in review_only_groups
        for name in group["names"]
    ]
    return {
        "direct_a90ctl_reference_count": len(direct_a90ctl),
        "direct_a90ctl_reference_names": direct_a90ctl,
        "direct_a90ctl_candidate_groups": candidate_groups,
        "direct_a90ctl_top_group": candidate_groups[0] if candidate_groups else {},
        "direct_a90ctl_actionable_now_count": len(actionable_names),
        "direct_a90ctl_actionable_now_names": actionable_names,
        "direct_a90ctl_review_only_count": len(review_only_names),
        "direct_a90ctl_review_only_names": review_only_names,
        "direct_a90ctl_next_actionable_group": actionable_groups[0] if actionable_groups else {},
        "live_without_phase_timer_count": len(live_without_phase),
        "live_without_phase_timer_names": live_without_phase,
        "live_phase_timer_exempt_count": len(live_phase_exempt),
        "live_phase_timer_exempt_names": live_phase_exempt,
        "live_without_residual_state_count": len(live_without_residual),
        "live_without_residual_state_names": live_without_residual,
        "live_residual_state_exempt_count": len(live_residual_exempt),
        "live_residual_state_exempt_names": live_residual_exempt,
        "secret_handling_count": len(secret_related),
        "secret_handling_names": secret_related,
        "source_delete_review_count": len(source_delete_review),
        "source_delete_review_names": source_delete_review,
        "active_live_phase_residual_backlog_closed": not live_without_phase and not live_without_residual,
    }


def inventory(root: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        if path.name == "__pycache__" or path.suffix == ".pyc":
            continue
        text = read_text(path) if path.is_file() else ""
        label, reason = classify(path, text)
        mode = path.stat().st_mode
        self_inventory = path.name == Path(__file__).name
        entries.append({
            "path": rel(path),
            "name": path.name,
            "type": "dir" if path.is_dir() else "file" if path.is_file() else "other",
            "label": label,
            "reason": reason,
            "executable": bool(mode & stat.S_IXUSR),
            "imports_a90_transport": imports_module(text, "a90_transport"),
            "mentions_a90_bridge": False if self_inventory else "a90_bridge.py" in text,
            "mentions_serial_tcp_bridge": False if self_inventory else "serial_tcp_bridge.py" in text,
            "mentions_a90ctl_subprocess": False if self_inventory else "a90ctl.py" in text,
            "has_phase_timer": False if self_inventory else (
                "phase_timer" in text
                or "PhaseTimer" in text
                or "transport.phase(" in text
                or "add_total_phase(" in text
            ),
            "has_residual_state": False if self_inventory else (
                "residual_state_contract" in text or "residual_state" in text
            ),
            "has_secret_redaction": False if self_inventory else (
                "redact" in text.lower() or "secret_values_logged" in text
            ),
            "live_device_required": requires_live_device(path, text),
            "repo_reference_count": repo_reference_count(path.name),
        })
    summary: dict[str, int] = {}
    for entry in entries:
        summary[entry["label"]] = summary.get(entry["label"], 0) + 1
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "root": rel(root),
        "summary": summary,
        "consolidation_signals": consolidation_signals(entries),
        "entries": entries,
    }


def render_markdown(data: dict[str, Any]) -> str:
    entries = data["entries"]
    signals = data["consolidation_signals"]

    def flag(value: bool) -> str:
        return "yes" if value else "no"

    archived_lines = []
    for name, reason in ARCHIVED_ENTRYPOINTS.items():
        archive_path = REPO_ROOT / "workspace" / "public" / "archive" / "scripts" / "revalidation" / name
        if archive_path.exists():
            archived_lines.append(f"- `{rel(archive_path)}`: {reason}.")

    cleanup_lines = []
    if data["summary"].get("archive", 0):
        cleanup_lines.append("- `archive`: review docs references before moving to `workspace/public/archive/scripts/revalidation/`.")
    else:
        cleanup_lines.append("- No current source-root archive candidates remain.")
    if data["summary"].get("delete-review", 0):
        cleanup_lines.append("- `delete-review`: inspect manually before deletion; generated caches can be removed immediately.")
    else:
        cleanup_lines.append("- No current source-root delete-review candidates remain.")
    cleanup_lines.append("- Active live workflow scripts should use `a90_transport.py`; `a90ctl.py` itself remains the cmdv1 client.")

    direct_a90ctl = signals["direct_a90ctl_reference_names"]
    direct_a90ctl_actionable = signals["direct_a90ctl_actionable_now_names"]
    direct_a90ctl_review_only = signals["direct_a90ctl_review_only_names"]
    live_without_phase = signals["live_without_phase_timer_names"]
    live_phase_exempt = signals["live_phase_timer_exempt_names"]
    live_residual_exempt = signals["live_residual_state_exempt_names"]
    live_without_residual = signals["live_without_residual_state_names"]
    secret_related = signals["secret_handling_names"]
    consolidation_lines = [
        "- Machine-readable copy: JSON field `consolidation_signals`.",
        "- Direct `a90ctl.py` subprocess references outside the client are review-only candidates; migrate only when changing the script for another reason.",
        f"- Direct `a90ctl.py` reference count: `{len(direct_a90ctl)}`"
        + (f" (`{', '.join(direct_a90ctl[:8])}`{'...' if len(direct_a90ctl) > 8 else ''})." if direct_a90ctl else "."),
        f"- Direct `a90ctl.py` actionable-now count: `{len(direct_a90ctl_actionable)}`"
        + (f" (`{', '.join(direct_a90ctl_actionable[:8])}`{'...' if len(direct_a90ctl_actionable) > 8 else ''})." if direct_a90ctl_actionable else "."),
        f"- Direct `a90ctl.py` review-only count: `{len(direct_a90ctl_review_only)}`"
        + (f" (`{', '.join(direct_a90ctl_review_only[:8])}`{'...' if len(direct_a90ctl_review_only) > 8 else ''})." if direct_a90ctl_review_only else "."),
        "- Direct `a90ctl.py` candidate groups: "
        + ", ".join(
            f"`{group['group']}`={group['count']}/"
            f"{'actionable' if group['actionable_now'] else 'review-only'}"
            f"/gate:{group['migration_gate']}"
            for group in signals["direct_a90ctl_candidate_groups"]
        )
        + ".",
        f"- Active live scripts without explicit phase timer markers: `{len(live_without_phase)}`"
        + (f" (`{', '.join(live_without_phase[:8])}`{'...' if len(live_without_phase) > 8 else ''})." if live_without_phase else "."),
        f"- Phase-timer-exempt live utilities: `{len(live_phase_exempt)}`"
        + (f" (`{', '.join(live_phase_exempt[:8])}`{'...' if len(live_phase_exempt) > 8 else ''})." if live_phase_exempt else "."),
        f"- Active live scripts without residual-state metadata: `{len(live_without_residual)}`"
        + (f" (`{', '.join(live_without_residual[:8])}`{'...' if len(live_without_residual) > 8 else ''})." if live_without_residual else "."),
        f"- Residual-state-exempt live utilities/helpers: `{len(live_residual_exempt)}`"
        + (f" (`{', '.join(live_residual_exempt[:8])}`{'...' if len(live_residual_exempt) > 8 else ''})." if live_residual_exempt else "."),
        f"- Scripts with explicit redaction/secret handling: `{len(secret_related)}`"
        + (f" (`{', '.join(secret_related[:8])}`{'...' if len(secret_related) > 8 else ''})." if secret_related else "."),
    ]
    rows = [
        "| Label | Count |",
        "| --- | ---: |",
    ]
    for label, count in sorted(data["summary"].items()):
        rows.append(f"| `{label}` | {count} |")

    table = [
        "| Script | Label | Transport | Live | Phase | Residual | Secret | Refs | Reason |",
        "| --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for entry in entries:
        transport_bits = []
        if entry["imports_a90_transport"]:
            transport_bits.append("shared")
        if entry["mentions_a90ctl_subprocess"]:
            transport_bits.append("a90ctl-subprocess")
        if entry["mentions_a90_bridge"]:
            transport_bits.append("bridge-wrapper")
        if entry["mentions_serial_tcp_bridge"]:
            transport_bits.append("bridge-impl")
        if not transport_bits:
            transport_bits.append("none")
        table.append(
            f"| `{entry['name']}` | `{entry['label']}` | "
            f"`{','.join(transport_bits)}` | "
            f"{flag(entry['live_device_required'])} | "
            f"{flag(entry['has_phase_timer'])} | "
            f"{flag(entry['has_residual_state'])} | "
            f"{flag(entry['has_secret_redaction'])} | "
            f"{entry['repo_reference_count']} | {entry['reason']} |"
        )

    return "\n".join([
        "# Revalidation Script Inventory",
        "",
        f"- Generated at: `{data['generated_at']}`",
        f"- Root: `{data['root']}`",
        "- Scope: public metadata only; no private run logs, credentials, boot images, or raw captures.",
        "- Action: inventory only. No scripts were moved or deleted by this report.",
        "",
        "## Summary",
        "",
        *rows,
        "",
        "## Entries",
        "",
        *table,
        "",
        "## Archived Entrypoints",
        "",
        *(archived_lines if archived_lines else ["- None recorded."]),
        "",
        "## Immediate Cleanup Candidates",
        "",
        *cleanup_lines,
        "",
        "## Consolidation Signals",
        "",
        *consolidation_lines,
        "",
    ])


def main() -> int:
    args = parse_args()
    data = inventory(args.root)
    if args.write:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_markdown(data), encoding="utf-8")
        args.json_out.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.write:
        print(render_markdown(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
