#!/usr/bin/env python3
"""V1063 host-only PM service trigger/input classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v1063-pm-service-trigger-classifier")
DEFAULT_V1024_MANIFEST = Path("tmp/wifi/v1024-fast-fd-contract-classifier/manifest.json")
DEFAULT_V1046_MANIFEST = Path("tmp/wifi/v1046-android-vendor-init-rc-handoff/manifest.json")
DEFAULT_V1061_MANIFEST = Path("tmp/wifi/v1061-global-firmware-pm-full-contract/manifest.json")
DEFAULT_V1061_HELPER = Path("tmp/wifi/v1061-global-firmware-pm-full-contract/native/pm-full-contract-with-global-firmware.txt")
DEFAULT_V1062_MANIFEST = Path("tmp/wifi/v1062-pm-contract-gap-classifier/manifest.json")
DEFAULT_V860_MANIFEST = Path("tmp/wifi/v860-pm-service-property-superset-replay-live/manifest.json")
DEFAULT_V861_MANIFEST = Path("tmp/wifi/v861-pm-service-domain-parity-live-r2/manifest.json")
DEFAULT_V692_REPORT = Path("docs/reports/NATIVE_INIT_V692_PERIPHERAL_REGISTRY_SNAPSHOT_LIVE_2026-05-24.md")
DEFAULT_V694_REPORT = Path("docs/reports/NATIVE_INIT_V694_PERIPHERAL_VNDSERVICE_QUERY_LIVE_2026-05-24.md")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
LATEST_POINTER = Path("tmp/wifi/latest-v1063-pm-service-trigger-classifier.txt")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1024-manifest", type=Path, default=DEFAULT_V1024_MANIFEST)
    parser.add_argument("--v1046-manifest", type=Path, default=DEFAULT_V1046_MANIFEST)
    parser.add_argument("--v1061-manifest", type=Path, default=DEFAULT_V1061_MANIFEST)
    parser.add_argument("--v1061-helper", type=Path, default=DEFAULT_V1061_HELPER)
    parser.add_argument("--v1062-manifest", type=Path, default=DEFAULT_V1062_MANIFEST)
    parser.add_argument("--v860-manifest", type=Path, default=DEFAULT_V860_MANIFEST)
    parser.add_argument("--v861-manifest", type=Path, default=DEFAULT_V861_MANIFEST)
    parser.add_argument("--v692-report", type=Path, default=DEFAULT_V692_REPORT)
    parser.add_argument("--v694-report", type=Path, default=DEFAULT_V694_REPORT)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    parser.add_argument("command", choices=("run",), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path, limit: int = 3_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"exists": False, "path": str(repo_path(path)), "invalid": True}
    data.setdefault("exists", True)
    data.setdefault("path", str(repo_path(path)))
    return data


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "pass"}
    return False


def intish(value: Any, default: int = -1) -> int:
    try:
        text = str(value).strip()
        if not text:
            return default
        return int(text)
    except (TypeError, ValueError):
        return default


def key_values(text: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for raw in text.splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        if key:
            pairs[key] = value.strip()
    return pairs


def first_line(text: str, pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for raw in text.splitlines():
        line = raw.strip()
        if line and regex.search(line):
            return line
    return ""


def count_lines(text: str, pattern: str) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    return sum(1 for line in text.splitlines() if regex.search(line))


def contains_ordered(source: str, snippets: list[str]) -> bool:
    offset = 0
    for snippet in snippets:
        index = source.find(snippet, offset)
        if index < 0:
            return False
        offset = index + len(snippet)
    return True


def nested(mapping: dict[str, Any], *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def android_contract(v1024: dict[str, Any], v1046: dict[str, Any]) -> dict[str, Any]:
    early_fd = nested(v1024, "classification", "early", "fd") or {}
    late_chain = nested(v1024, "classification", "late", "chain") or {}
    rc_results = nested(v1046, "context", "rc_results") or {}
    return {
        "pm_proxy_helper_subsys_modem_fd": boolish(early_fd.get("pm_proxy_helper_subsys_modem_fd")),
        "pm_service_subsys_modem_fd": boolish(early_fd.get("pm_service_subsys_modem_fd")),
        "mdm_helper_esoc0_fd": boolish(early_fd.get("mdm_helper_esoc0_fd")),
        "wlfw_chain": boolish(late_chain.get("wlfw_chain")),
        "per_proxy_helper_start_s": late_chain.get("per_proxy_helper_start"),
        "per_mgr_start_s": late_chain.get("per_mgr_start"),
        "per_proxy_start_s": late_chain.get("per_proxy_start"),
        "mdm_helper_start_s": late_chain.get("mdm_helper_start"),
        "wlfw_start_s": late_chain.get("wlfw_start"),
        "subsys_esoc0_get_s": late_chain.get("subsys_esoc0_get"),
        "rc_per_proxy_helper_present": "pm_proxy_helper" in str(rc_results.get("pm_proxy_helper-rc", "")),
        "rc_init_mdm_gate_present": "ro.baseband" in str(rc_results.get("init-mdm-sh", "")),
    }


def native_contract(v1061: dict[str, Any], v1061_helper_text: str, v1062: dict[str, Any]) -> dict[str, Any]:
    keys = key_values(v1061_helper_text)
    live_contract = nested(v1061, "live", "contract") or {}
    native1062 = v1062.get("native") or {}
    process1062 = v1062.get("native_process") or {}
    return {
        "decision_v1061": v1061.get("decision", ""),
        "decision_v1062": v1062.get("decision", ""),
        "order": keys.get("cnss_before_esoc.order", nested(v1061, "checks", "4", "detail", "order") or ""),
        "modem_pre_holder_confirmed": boolish(live_contract.get("modem_pre_holder_confirmed")),
        "pm_proxy_helper_subsys_modem_fd_count": intish(
            live_contract.get("pm_proxy_helper_subsys_modem_fd_count")
            or native1062.get("pm_proxy_helper_subsys_modem_fd_count")
        ),
        "per_mgr_subsys_modem_fd_count": intish(
            live_contract.get("per_mgr_subsys_modem_fd_count")
            or native1062.get("per_mgr_subsys_modem_fd_count")
        ),
        "pm_full_contract_seen": boolish(live_contract.get("pm_full_contract_seen"))
        or boolish(native1062.get("pm_full_contract_seen")),
        "pm_proxy_started": boolish(live_contract.get("pm_proxy_started")) or boolish(native1062.get("pm_proxy_started")),
        "pm_service_process_count": process1062.get("pm_service_process_count", ""),
        "pm_proxy_count": process1062.get("pm_proxy_count", ""),
        "pm_proxy_helper_count": process1062.get("pm_proxy_helper_count", ""),
        "per_mgr_attr": process1062.get("per_mgr_attr", ""),
        "per_mgr_binder_count": process1062.get("per_mgr_binder_count", ""),
        "per_mgr_hwbinder_count": process1062.get("per_mgr_hwbinder_count", ""),
        "per_mgr_vndbinder_count": process1062.get("per_mgr_vndbinder_count", ""),
        "per_mgr_wchan": first_line(v1061_helper_text, r"cnss_before_esoc_pm_full_gap_per_mgr_wchan_BEGIN[\s\S]*|SyS_nanosleep"),
        "per_mgr_stack_nanosleep": "SyS_nanosleep" in v1061_helper_text,
        "per_mgr_fd_vndbinder": "/dev/vndbinder" in v1061_helper_text,
        "per_mgr_fd_subsys_modem": "cnss_before_esoc.per_mgr_subsys_modem_fd_count=1" in v1061_helper_text,
        "property_sdx50m_offline_requests": count_lines(v1061_helper_text, r"vendor\.peripheral\.SDX50M\.state=.*OFFLINE"),
        "property_modem_offline_requests": count_lines(v1061_helper_text, r"vendor\.peripheral\.modem\.state=.*OFFLINE"),
        "service_manager_start_executed": boolish(native1062.get("service_manager_start_executed")),
        "subsys_esoc0_open_attempted": boolish(native1062.get("subsys_esoc0_open_attempted")),
        "kernel_warning_count": intish(native1062.get("kernel_warning_count"), 0),
    }


def previous_closures(v860: dict[str, Any], v861: dict[str, Any], v692_report: str, v694_report: str) -> dict[str, Any]:
    v860_helper = nested(v860, "analysis", "helper") or {}
    v861_helper = nested(v861, "analysis", "helper") or {}
    return {
        "property_denials_clean_v860": intish(nested(v860, "analysis", "property_denials", "total"), 999) == 0
        or intish(nested(v860_helper, "property_denials", "total"), 999) == 0,
        "v860_pm_service_observable": boolish(nested(v860_helper, "keys", "per_mgr_observable")),
        "v860_pm_service_subsys_modem": boolish(v860_helper.get("per_mgr_holds_subsys_modem")),
        "v861_exec_target_accepted": boolish(nested(v861_helper, "children", "per_mgr", "observable")),
        "v861_pm_service_subsys_modem": boolish(v861_helper.get("per_mgr_holds_subsys_modem")),
        "v692_provider_snapshot_captured": "v692-provider-registration-snapshot-captured" in v692_report,
        "v694_vndservice_registration_confirmed": "v694-peripheral-vndservice-registration-confirmed" in v694_report,
    }


def source_surface(helper_source: str) -> dict[str, Any]:
    return {
        "direct_execv_child_target": "execv(child->target, child_argv)" in helper_source,
        "pm_service_default_argv": '"/vendor/bin/pm-service"' in helper_source
        and "child_argv = default_argv" in helper_source
        and '(char *)child->target' in helper_source,
        "pm_full_contract_order_present": "after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder" in helper_source,
        "v1061_order_pm_proxy_helper_before_per_mgr": contains_ordered(
            helper_source,
            [
                'composite_spawn_child(cfg, paths, pm_proxy_helper, stdout_buf)',
                'composite_spawn_child(cfg, paths, per_mgr, stdout_buf)',
            ],
        ),
        "v1061_service_manager_after_pm_contract_gate": contains_ordered(
            helper_source,
            [
                "pm_full_contract_seen =",
                "start_cnss_before_esoc_service_manager_trio",
            ],
        ),
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1024 = load_json(args.v1024_manifest)
    v1046 = load_json(args.v1046_manifest)
    v1061 = load_json(args.v1061_manifest)
    v1062 = load_json(args.v1062_manifest)
    v860 = load_json(args.v860_manifest)
    v861 = load_json(args.v861_manifest)
    helper_text = read_text(args.v1061_helper)
    helper_source = read_text(args.helper_source)
    v692_report = read_text(args.v692_report)
    v694_report = read_text(args.v694_report)

    android = android_contract(v1024, v1046)
    native = native_contract(v1061, helper_text, v1062)
    closures = previous_closures(v860, v861, v692_report, v694_report)
    source = source_surface(helper_source)

    android_positive = (
        android["pm_proxy_helper_subsys_modem_fd"]
        and android["pm_service_subsys_modem_fd"]
        and android["mdm_helper_esoc0_fd"]
        and android["wlfw_chain"]
    )
    native_idle_gap = (
        native["pm_proxy_helper_subsys_modem_fd_count"] > 0
        and native["per_mgr_subsys_modem_fd_count"] == 0
        and native["per_mgr_vndbinder_count"] == "1"
        and native["per_mgr_stack_nanosleep"]
        and not native["pm_full_contract_seen"]
    )
    older_routes_closed = (
        closures["property_denials_clean_v860"]
        and closures["v860_pm_service_observable"]
        and not closures["v860_pm_service_subsys_modem"]
        and closures["v694_vndservice_registration_confirmed"]
    )
    source_direct_exec_gap = (
        source["direct_execv_child_target"]
        and source["pm_service_default_argv"]
        and source["v1061_order_pm_proxy_helper_before_per_mgr"]
    )
    warning_blocker = native["kernel_warning_count"] > 0

    if android_positive and native_idle_gap and older_routes_closed and source_direct_exec_gap:
        decision = "v1063-pm-service-idle-input-gap-classified"
        reason = (
            "Android proves pm-service should hold /dev/subsys_modem, but native V1061 leaves "
            "pm-service alive, vndbinder-only, and sleeping in nanosleep with no subsystem fd; "
            "property coverage and provider registration were already proven insufficient."
        )
        next_step = (
            "add source/build support for a PM service trigger observer that models Android init "
            "service state and captures the exact vndbinder/property request before another PM live retry"
        )
    elif android_positive and native_idle_gap:
        decision = "v1063-pm-service-idle-gap-partial"
        reason = "Android/native fd delta is present, but older closure evidence or helper source surface is incomplete."
        next_step = "refresh V860/V694/source evidence before choosing a live retry"
    else:
        decision = "v1063-pm-service-trigger-classifier-incomplete"
        reason = "available evidence does not isolate the PM service trigger/input gap."
        next_step = "refresh V1024/V1061/V1062 inputs"

    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": True,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v1024_manifest": str(repo_path(args.v1024_manifest)),
            "v1046_manifest": str(repo_path(args.v1046_manifest)),
            "v1061_manifest": str(repo_path(args.v1061_manifest)),
            "v1061_helper": str(repo_path(args.v1061_helper)),
            "v1062_manifest": str(repo_path(args.v1062_manifest)),
            "v860_manifest": str(repo_path(args.v860_manifest)),
            "v861_manifest": str(repo_path(args.v861_manifest)),
            "v692_report": str(repo_path(args.v692_report)),
            "v694_report": str(repo_path(args.v694_report)),
            "helper_source": str(repo_path(args.helper_source)),
        },
        "android": android,
        "native": native,
        "previous_closures": closures,
        "helper_source": source,
        "classification": {
            "android_positive": android_positive,
            "native_idle_gap": native_idle_gap,
            "older_routes_closed": older_routes_closed,
            "source_direct_exec_gap": source_direct_exec_gap,
            "warning_blocker": warning_blocker,
        },
        "device_commands_executed": False,
        "device_mutations": False,
        "live_retry_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
    }


def rows(mapping: dict[str, Any]) -> list[list[str]]:
    return [[key, str(value)] for key, value in mapping.items()]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V1063 PM Service Trigger Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            "",
            "## Classification",
            "",
            markdown_table(["item", "value"], rows(manifest["classification"])),
            "",
            "## Android Contract",
            "",
            markdown_table(["item", "value"], rows(manifest["android"])),
            "",
            "## Native V1061",
            "",
            markdown_table(["item", "value"], rows(manifest["native"])),
            "",
            "## Previous Closures",
            "",
            markdown_table(["item", "value"], rows(manifest["previous_closures"])),
            "",
            "## Helper Source Surface",
            "",
            markdown_table(["item", "value"], rows(manifest["helper_source"])),
        ]
    ) + "\n"


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = classify(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    repo_path(LATEST_POINTER).write_text(
        str(store.run_dir.relative_to(repo_path("."))) + "\n",
        encoding="utf-8",
    )
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
