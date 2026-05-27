#!/usr/bin/env python3
"""V1136 host-only planner for the post-PM eSoC/MDM2AP gate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1136-post-pm-esoc-gate-planner")
LATEST_POINTER = Path("tmp/wifi/latest-v1136-post-pm-esoc-gate-planner.txt")
DEFAULT_V1135 = Path("tmp/wifi/v1135-lower-publication-gap-classifier/manifest.json")
DEFAULT_V1134 = Path("tmp/wifi/v1134-outer-holder-post-policy-cnss-live-run/manifest.json")
DEFAULT_V1024 = Path("tmp/wifi/v1024-fast-fd-contract-classifier/manifest.json")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path, limit: int = 16_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def nested_get(data: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    cur: Any = data
    for item in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(item)
    return default if cur is None else cur


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass", "online"}


def summarize_v1135(data: dict[str, Any]) -> dict[str, Any]:
    flags = nested_get(data, ("analysis", "classification", "flags"), {})
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "upper_pm_success": boolish(flags.get("v1134_upper_pm_success")) if isinstance(flags, dict) else False,
        "lower_wlfw_absent": boolish(flags.get("v1134_lower_wlfw_absent")) if isinstance(flags, dict) else False,
        "android_publication_path": boolish(flags.get("android_has_complete_publication_path")) if isinstance(flags, dict) else False,
        "esoc_history_known": boolish(flags.get("esoc_state_machine_partially_known")) if isinstance(flags, dict) else False,
    }


def summarize_v1134(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "pm_actor_executed": boolish(data.get("pm_actor_executed")),
        "cnss_daemon_start_executed": boolish(data.get("cnss_daemon_start_executed")),
        "wifi_hal_start_executed": boolish(data.get("wifi_hal_start_executed")),
        "wifi_bringup_executed": boolish(data.get("wifi_bringup_executed")),
        "external_ping_executed": boolish(data.get("external_ping_executed")),
        "mdm3_after_observer": nested_get(data, ("analysis", "global_firmware", "mdm3_after_observer"), ""),
        "service69": nested_get(data, ("analysis", "global_firmware", "qrtr_services_after_observer", "69"), 0),
        "wlan0": nested_get(data, ("analysis", "global_firmware", "markers", "counts", "wlan0"), 0),
    }


def summarize_v1024(data: dict[str, Any]) -> dict[str, Any]:
    fd = nested_get(data, ("classification", "early", "fd"), {})
    late = nested_get(data, ("classification", "late", "chain"), {})
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "android_pm_service_subsys_modem": boolish(fd.get("pm_service_subsys_modem_fd")) if isinstance(fd, dict) else False,
        "android_pm_proxy_helper_subsys_modem": boolish(fd.get("pm_proxy_helper_subsys_modem_fd")) if isinstance(fd, dict) else False,
        "android_mdm_helper_esoc0": boolish(fd.get("mdm_helper_esoc0_fd")) if isinstance(fd, dict) else False,
        "android_wlfw_time": late.get("cnss_daemon_wlfw_start") if isinstance(late, dict) else None,
        "android_wlan0_time": late.get("wlan0") if isinstance(late, dict) else None,
    }


def summarize_helper_source(text: str) -> dict[str, Any]:
    return {
        "source_present": bool(text),
        "helper_marker_v213": "a90_android_execns_probe v213" in text,
        "pm_observer_mode": "wifi-companion-pm-service-trigger-observer" in text,
        "mdm_helper_runtime_mode": "wifi-companion-mdm-helper-runtime-contract-capture" in text,
        "mdm_helper_subsys_trigger_mode": "wifi-companion-mdm-helper-runtime-subsys-trigger-capture" in text,
        "pm_observer_forces_mdm_helper_zero": "pm_service_trigger_observer.mdm_helper_start_executed=0" in text,
        "pm_observer_has_cnss_before_per_proxy": "--pm-observer-start-cnss-before-per-proxy" in text,
        "has_post_pm_mdm_helper_composite": (
            "post-pm-mdm-helper" in text
            or "pm-observer-mdm-helper" in text
            or "post_pm_mdm_helper" in text
        ),
    }


def classify(analysis: dict[str, Any]) -> dict[str, Any]:
    v1135 = analysis["v1135"]
    v1134 = analysis["v1134"]
    v1024 = analysis["v1024_android"]
    helper = analysis["helper"]
    flags = {
        "v1135_ready": (
            v1135["pass"]
            and v1135["upper_pm_success"]
            and v1135["lower_wlfw_absent"]
            and v1135["android_publication_path"]
            and v1135["esoc_history_known"]
        ),
        "v1134_clean_upper_reference": (
            v1134["pass"]
            and v1134["pm_actor_executed"]
            and v1134["cnss_daemon_start_executed"]
            and not v1134["wifi_hal_start_executed"]
            and not v1134["wifi_bringup_executed"]
            and not v1134["external_ping_executed"]
            and v1134["mdm3_after_observer"] == "OFFLINING"
        ),
        "android_contract_requires_mdm_helper_esoc": (
            v1024["pass"]
            and v1024["android_pm_service_subsys_modem"]
            and v1024["android_pm_proxy_helper_subsys_modem"]
            and v1024["android_mdm_helper_esoc0"]
        ),
        "helper_has_separate_building_blocks": (
            helper["source_present"]
            and helper["helper_marker_v213"]
            and helper["pm_observer_mode"]
            and helper["mdm_helper_runtime_mode"]
            and helper["pm_observer_has_cnss_before_per_proxy"]
        ),
        "current_helper_lacks_composite": (
            helper["pm_observer_forces_mdm_helper_zero"]
            and not helper["has_post_pm_mdm_helper_composite"]
        ),
    }
    missing = [name for name, ok in flags.items() if not ok]
    if not missing:
        return {
            "decision": "v1136-post-pm-mdm-helper-composite-support-required",
            "pass": True,
            "reason": (
                "V1134/V1135 make the next live target post-PM mdm_helper/eSoC observation, "
                "but helper v213 only has separate PM-observer and mdm_helper runtime modes; "
                "the PM observer explicitly records mdm_helper_start_executed=0"
            ),
            "next_step": (
                "V1137 should be source/build-only: add a guarded post-PM mdm_helper/eSoC "
                "observer mode that reuses the V1134 PM/CNSS path, then starts/observes "
                "mdm_helper without Wi-Fi HAL, scan/connect, credentials, DHCP, route, or ping"
            ),
            "flags": flags,
            "missing": [],
        }
    return {
        "decision": "v1136-post-pm-esoc-planner-incomplete",
        "pass": False,
        "reason": "missing=" + ",".join(missing),
        "next_step": "refresh missing evidence before adding helper support",
        "flags": flags,
        "missing": missing,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    cls = analysis["classification"]
    rows = [
        ["V1135 ready", str(cls["flags"]["v1135_ready"]), analysis["v1135"]["decision"]],
        ["V1134 upper reference", str(cls["flags"]["v1134_clean_upper_reference"]), analysis["v1134"]["decision"]],
        ["Android mdm_helper/eSoC contract", str(cls["flags"]["android_contract_requires_mdm_helper_esoc"]), analysis["v1024_android"]["decision"]],
        ["helper building blocks", str(cls["flags"]["helper_has_separate_building_blocks"]), "source"],
        ["composite missing", str(cls["flags"]["current_helper_lacks_composite"]), "source"],
    ]
    support_rows = [
        ["pm_observer_mode", str(analysis["helper"]["pm_observer_mode"])],
        ["mdm_helper_runtime_mode", str(analysis["helper"]["mdm_helper_runtime_mode"])],
        ["pm_observer_forces_mdm_helper_zero", str(analysis["helper"]["pm_observer_forces_mdm_helper_zero"])],
        ["has_post_pm_mdm_helper_composite", str(analysis["helper"]["has_post_pm_mdm_helper_composite"])],
        ["android_mdm_helper_esoc0", str(analysis["v1024_android"]["android_mdm_helper_esoc0"])],
    ]
    return "\n".join([
        "# V1136 Post-PM eSoC Gate Planner",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Classification Evidence",
        "",
        markdown_table(["evidence", "ok", "detail"], rows),
        "",
        "## Helper Support",
        "",
        markdown_table(["key", "value"], support_rows),
        "",
        "## Missing",
        "",
        json.dumps(cls["missing"], indent=2, sort_keys=True),
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1135", type=Path, default=DEFAULT_V1135)
    parser.add_argument("--v1134", type=Path, default=DEFAULT_V1134)
    parser.add_argument("--v1024", type=Path, default=DEFAULT_V1024)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = {
        "v1135": summarize_v1135(load_json(args.v1135)),
        "v1134": summarize_v1134(load_json(args.v1134)),
        "v1024_android": summarize_v1024(load_json(args.v1024)),
        "helper": summarize_helper_source(read_text(args.helper_source)),
    }
    classification = classify(analysis)
    analysis["classification"] = classification
    manifest = {
        "cycle": "v1136",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1135": str(repo_path(args.v1135)),
            "v1134": str(repo_path(args.v1134)),
            "v1024": str(repo_path(args.v1024)),
            "helper_source": str(repo_path(args.helper_source)),
        },
        "analysis": analysis,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "device_commands_executed": False,
        "device_mutations": False,
        "tracefs_write_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
