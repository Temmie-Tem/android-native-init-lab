#!/usr/bin/env python3
"""V1122 host-only classifier for V1108 vs V1121 provider lifetime delta."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1122-provider-namespace-delta-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1122-provider-namespace-delta-classifier.txt")
DEFAULT_V1108 = Path("tmp/wifi/v1108-pm-ordering-no-pre-cnss-per-proxy-live/manifest.json")
DEFAULT_V1121 = Path("tmp/wifi/v1121-firmware-mount-only-provider-live/manifest.json")
EXPECTED_V1108_DECISION = "v1108-no-pre-cnss-per-proxy-cnss-connect-path-reached"
EXPECTED_V1121_DECISION = "v1121-firmware-mount-only-provider-still-missing"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path, limit: int = 8_000_000) -> str:
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


def step_file(manifest: dict[str, Any], name: str) -> Path | None:
    run_dir = Path(str(manifest.get("out_dir") or ""))
    if not run_dir:
        return None
    for step in manifest.get("steps") or []:
        if step.get("name") == name and step.get("file"):
            return repo_path(run_dir / str(step["file"]))
    return None


def step_text(manifest: dict[str, Any], name: str) -> str:
    path = step_file(manifest, name)
    if path is None:
        return ""
    return read_text(path)


def mount_targets(text: str) -> dict[str, list[str]]:
    mounts: dict[str, list[str]] = {}
    for raw in text.splitlines():
        parts = raw.split()
        if len(parts) >= 3:
            mounts.setdefault(parts[1], []).append(raw)
    return mounts


def nested_get(data: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    cur: Any = data
    for item in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(item)
    return default if cur is None else cur


def cnss_returns(manifest: dict[str, Any], label: str) -> list[str]:
    tracefs = nested_get(manifest, ("analysis", "tracefs_uprobe"), {})
    values: list[str] = []
    for comm, labels in (tracefs.get("return_values_by_comm") or {}).items():
        if "cnss" in str(comm):
            values.extend(str(item) for item in (labels or {}).get(label, []))
    return values


def contract(manifest: dict[str, Any]) -> dict[str, str]:
    value = nested_get(manifest, ("analysis", "tracefs_uprobe", "pm_contract"), {})
    return {str(key): str(item) for key, item in value.items()} if isinstance(value, dict) else {}


def classify(v1108: dict[str, Any], v1121: dict[str, Any]) -> dict[str, Any]:
    c1108 = contract(v1108)
    c1121 = contract(v1121)
    mounts1108 = mount_targets(step_text(v1108, "proc-mounts-before"))
    mounts1121 = mount_targets(step_text(v1121, "proc-mounts-before"))
    mounted1121 = mount_targets(step_text(v1121, "mount-only-proc-mounts-mounted"))
    firmware_mounts1121 = nested_get(v1121, ("analysis", "firmware_mount_only", "mounted_hits"), {})
    comparison = {
        "v1108": {
            "decision": v1108.get("decision", ""),
            "pass": bool(v1108.get("pass")),
            "provider_seen": c1108.get("vndservice_provider_seen", ""),
            "per_mgr_post_start_observable": c1108.get("child.per_mgr.post_start_observable", ""),
            "per_mgr_exited": c1108.get("child.per_mgr.exited", ""),
            "per_mgr_exit_code": c1108.get("child.per_mgr.exit_code", ""),
            "per_proxy_start_executed": c1108.get("per_proxy_start_executed", ""),
            "per_proxy_start_skipped": c1108.get("child.per_proxy.start_skipped", ""),
            "register_ret": cnss_returns(v1108, "pm_client_register_ret"),
            "connect_ret": cnss_returns(v1108, "pm_client_connect_ret"),
            "observer_mounts": {
                "/vendor": mounts1108.get("/vendor", []),
                "/vendor/firmware_mnt": mounts1108.get("/vendor/firmware_mnt", []),
                "/vendor/firmware-modem": mounts1108.get("/vendor/firmware-modem", []),
            },
        },
        "v1121": {
            "decision": v1121.get("decision", ""),
            "pass": bool(v1121.get("pass")),
            "provider_seen": c1121.get("vndservice_provider_seen", ""),
            "per_mgr_post_start_observable": c1121.get("child.per_mgr.post_start_observable", ""),
            "per_mgr_exited": c1121.get("child.per_mgr.exited", ""),
            "per_mgr_exit_code": c1121.get("child.per_mgr.exit_code", ""),
            "per_proxy_start_executed": c1121.get("per_proxy_start_executed", ""),
            "per_proxy_start_skipped": c1121.get("child.per_proxy.start_skipped", ""),
            "register_ret": cnss_returns(v1121, "pm_client_register_ret"),
            "connect_ret": cnss_returns(v1121, "pm_client_connect_ret"),
            "observer_mounts": {
                "/vendor": mounts1121.get("/vendor", []),
                "/vendor/firmware_mnt": mounts1121.get("/vendor/firmware_mnt", []),
                "/vendor/firmware-modem": mounts1121.get("/vendor/firmware-modem", []),
            },
            "mounted_firmware_hits": firmware_mounts1121,
            "mounted_lines": {
                "/vendor": mounted1121.get("/vendor", []),
                "/vendor/firmware_mnt": mounted1121.get("/vendor/firmware_mnt", []),
                "/vendor/firmware-modem": mounted1121.get("/vendor/firmware-modem", []),
            },
            "global_modem_holder_opened": bool(v1121.get("global_modem_holder_opened")),
        },
    }
    flags = {
        "v1108_expected": comparison["v1108"]["decision"] == EXPECTED_V1108_DECISION,
        "v1121_expected": comparison["v1121"]["decision"] == EXPECTED_V1121_DECISION,
        "v1108_provider_positive": comparison["v1108"]["provider_seen"] == "1",
        "v1121_provider_missing": comparison["v1121"]["provider_seen"] == "0",
        "same_no_pre_cnss_per_proxy_contract": (
            comparison["v1108"]["per_proxy_start_executed"] == "0"
            and comparison["v1108"]["per_proxy_start_skipped"] == "1"
            and comparison["v1121"]["per_proxy_start_executed"] == "0"
            and comparison["v1121"]["per_proxy_start_skipped"] == "1"
        ),
        "v1108_cnss_pm_success": "0x0" in comparison["v1108"]["register_ret"]
        and "0x0" in comparison["v1108"]["connect_ret"],
        "v1121_cnss_pm_not_reached": not comparison["v1121"]["register_ret"]
        and not comparison["v1121"]["connect_ret"],
        "v1121_firmware_mounts_present": all(bool(value) for value in firmware_mounts1121.values()),
        "v1121_no_global_holder": not comparison["v1121"]["global_modem_holder_opened"],
        "per_mgr_lifetime_delta": (
            comparison["v1108"]["per_mgr_post_start_observable"] == "1"
            and comparison["v1121"]["per_mgr_post_start_observable"] == "0"
            and comparison["v1121"]["per_mgr_exit_code"] == "0"
        ),
    }
    return {
        "comparison": comparison,
        "flags": flags,
        "interpretation": {
            "closed": [
                "global /dev/subsys_modem holder alone is not required for the provider regression",
                "pre-CNSS per_proxy ordering is not the differentiator because both gates skip it",
                "CNSS does not fail inside PM register in V1121; it never reaches PM register because provider is absent",
            ],
            "active_delta": (
                "V1121 creates global /vendor firmware mount surface before the PM observer. "
                "Under that surface, pm-service exits cleanly before provider registration; "
                "V1108 without that surface keeps the provider visible long enough for CNSS PM register/connect."
            ),
            "next_gate": (
                "V1123 should avoid global /vendor mutation and test firmware mounts inside the private runtime namespace, "
                "or trace pm-service early exit under V1121 to identify the exact path affected by global /vendor."
            ),
        },
    }


def decide(analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    flags = analysis["flags"]
    if not flags["v1108_expected"] or not flags["v1121_expected"]:
        return (
            "v1122-input-decision-mismatch",
            False,
            f"v1108_expected={flags['v1108_expected']} v1121_expected={flags['v1121_expected']}",
            "refresh V1108/V1121 evidence before comparing provider namespace delta",
        )
    if (
        flags["v1108_provider_positive"]
        and flags["v1121_provider_missing"]
        and flags["same_no_pre_cnss_per_proxy_contract"]
        and flags["v1108_cnss_pm_success"]
        and flags["v1121_cnss_pm_not_reached"]
        and flags["v1121_firmware_mounts_present"]
        and flags["v1121_no_global_holder"]
        and flags["per_mgr_lifetime_delta"]
    ):
        return (
            "v1122-provider-regression-is-global-firmware-vendor-surface",
            True,
            "V1108 succeeds and V1121 fails under the same no-pre-CNSS-per_proxy order; the differentiator is global firmware /vendor mount surface",
            "V1123 should test private-namespace firmware mounts or trace pm-service early clean exit under the global vendor surface",
        )
    return (
        "v1122-provider-namespace-delta-inconclusive",
        True,
        f"flags={flags}",
        "inspect V1108/V1121 evidence manually before choosing V1123",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rows = [[key, value] for key, value in analysis["flags"].items()]
    comparison_rows = [
        ["V1108", json.dumps(analysis["comparison"]["v1108"], sort_keys=True)],
        ["V1121", json.dumps(analysis["comparison"]["v1121"], sort_keys=True)],
    ]
    return "\n".join([
        "# V1122 Provider Namespace Delta Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Flags",
        "",
        markdown_table(["flag", "value"], rows),
        "",
        "## Comparison",
        "",
        markdown_table(["gate", "value"], comparison_rows),
        "",
        "## Interpretation",
        "",
        "- closed:",
        *[f"  - {item}" for item in analysis["interpretation"]["closed"]],
        f"- active_delta: {analysis['interpretation']['active_delta']}",
        f"- next_gate: {analysis['interpretation']['next_gate']}",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1108-manifest", type=Path, default=DEFAULT_V1108)
    parser.add_argument("--v1121-manifest", type=Path, default=DEFAULT_V1121)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        analysis: dict[str, Any] = {
            "comparison": {},
            "flags": {},
            "interpretation": {
                "closed": [],
                "active_delta": "plan-only",
                "next_gate": "run V1122 host-only classifier",
            },
        }
        decision, passed, reason, next_step = (
            "v1122-provider-namespace-delta-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V1122 host-only classifier against V1108 and V1121 evidence",
        )
    else:
        analysis = classify(load_json(args.v1108_manifest), load_json(args.v1121_manifest))
        decision, passed, reason, next_step = decide(analysis)

    manifest = {
        "cycle": "v1122",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "inputs": {
            "v1108_manifest": str(repo_path(args.v1108_manifest)),
            "v1121_manifest": str(repo_path(args.v1121_manifest)),
        },
        "analysis": analysis,
        "device_commands_executed": False,
        "firmware_mounts_executed": False,
        "global_modem_holder_opened": False,
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
        "reboot_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
