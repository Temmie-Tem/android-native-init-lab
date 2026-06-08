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
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "REVALIDATION_SCRIPT_INVENTORY_2026-06-08.md"
JSON_PATH = REPO_ROOT / "docs" / "reports" / "REVALIDATION_SCRIPT_INVENTORY_2026-06-08.json"

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
    if "native_init_flash.py" in text or "a90ctl.py" in text:
        return "active", "scripted live-device workflow"
    return "delete-review", "unclassified top-level script"


def requires_live_device(path: Path, text: str) -> bool:
    name = path.name
    tokens = (
        "native_init_flash.py",
        "a90ctl.py",
        "run_cmdv1_command",
        "wifi",
        "netservice",
        "reboot",
        "adb",
        "fastboot",
        "tcpctl",
        "serial_tcp_bridge",
    )
    return name in {"a90ctl.py", "a90_bridge.py", "serial_tcp_bridge.py"} or any(token in text for token in tokens)


def imports_module(text: str, module: str) -> bool:
    pattern = rf"^\s*(?:import\s+{re.escape(module)}\b|from\s+{re.escape(module)}\s+import\b)"
    return re.search(pattern, text, flags=re.MULTILINE) is not None


def inventory(root: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.iterdir(), key=lambda item: item.name):
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
            "has_phase_timer": "phase_timer" in text or "PhaseTimer" in text or "transport.phase(" in text,
            "has_secret_redaction": "redact" in text.lower() or "secret_values_logged" in text,
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
        "entries": entries,
    }


def render_markdown(data: dict[str, Any]) -> str:
    entries = data["entries"]
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
    rows = [
        "| Label | Count |",
        "| --- | ---: |",
    ]
    for label, count in sorted(data["summary"].items()):
        rows.append(f"| `{label}` | {count} |")

    table = [
        "| Script | Label | Transport | Refs | Reason |",
        "| --- | --- | --- | ---: | --- |",
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
            f"`{','.join(transport_bits)}` | {entry['repo_reference_count']} | {entry['reason']} |"
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
