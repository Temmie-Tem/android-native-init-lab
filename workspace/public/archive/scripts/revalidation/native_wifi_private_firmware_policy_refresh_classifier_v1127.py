#!/usr/bin/env python3
"""V1127 host-only classifier for SELinux policy refresh addService repair."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1127-private-firmware-policy-refresh-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1127-private-firmware-policy-refresh-classifier.txt")
DEFAULT_BASELINE = Path("tmp/wifi/v1126-private-firmware-addservice-status-trace/manifest.json")
DEFAULT_SELINUXFS = Path("tmp/wifi/v1127-v401-selinuxfs-mount/manifest.json")
DEFAULT_POLICY_LOAD = Path("tmp/wifi/v1127-v490-policy-load-v212-r2/manifest.json")
DEFAULT_POST_POLICY = Path("tmp/wifi/v1127-post-policy-private-firmware-addservice-status-trace/manifest.json")
DEFAULT_POST_REBOOT_PS = Path("tmp/wifi/v1127-current-post-reboot-ps.txt")

EXPECTED_BASELINE_DECISION = "v1126-private-firmware-addservice-status-permission-denied--1"
EXPECTED_SELINUXFS_DECISION = "toybox-selinuxfs-mount-live-executor-run-pass"
EXPECTED_POLICY_LOAD_DECISION = "v490-selinux-policy-load-proof-pass"
ACTOR_RE = re.compile(
    r"\b(pm-service|pm_proxy_helper|per_proxy|servicemanager|hwservicemanager|"
    r"vndservicemanager|cnss-daemon|cnss_diag|android\.hardware\.wifi|wificond|wpa_supplicant)\b"
)


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


def nested_get(data: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    cur: Any = data
    for item in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(item)
    return default if cur is None else cur


def tracefs(data: dict[str, Any]) -> dict[str, Any]:
    value = nested_get(data, ("analysis", "tracefs_uprobe"), {})
    return value if isinstance(value, dict) else {}


def counts(data: dict[str, Any]) -> dict[str, int]:
    value = tracefs(data).get("counts") or {}
    return {str(key): int(item) for key, item in value.items()} if isinstance(value, dict) else {}


def contract(data: dict[str, Any]) -> dict[str, str]:
    value = tracefs(data).get("pm_contract") or {}
    return {str(key): str(item) for key, item in value.items()} if isinstance(value, dict) else {}


def addservice_status(data: dict[str, Any]) -> dict[str, Any]:
    statuses = tracefs(data).get("addservice_statuses") or {}
    values = statuses.get("status") if isinstance(statuses, dict) else None
    if isinstance(values, list) and values:
        first = values[0]
        return first if isinstance(first, dict) else {}
    return {}


def bool_false(value: Any) -> bool:
    return value in (False, 0, "0", "false", "False", None)


def contract_false(data: dict[str, Any], key: str) -> bool:
    return contract(data).get(key, "0") == "0"


def contract_one(data: dict[str, Any], key: str) -> bool:
    return contract(data).get(key) == "1"


def forbidden_clear(data: dict[str, Any]) -> bool:
    return all(
        [
            bool_false(data.get("cnss_daemon_start_executed")),
            bool_false(data.get("wifi_hal_start_executed")),
            bool_false(data.get("scan_connect_executed")),
            bool_false(data.get("external_ping_executed")),
            contract_false(data, "cnss_daemon_start_executed"),
            contract_false(data, "wifi_hal_start_executed"),
            contract_false(data, "scan_connect_linkup"),
            contract_false(data, "external_ping"),
            contract_false(data, "subsys_esoc0_open_attempted"),
        ]
    )


def ps_clean(path: Path) -> dict[str, Any]:
    text = read_text(path)
    matches = ACTOR_RE.findall(text)
    busy = "status=busy" in text or "[busy]" in text
    return {
        "path": str(repo_path(path)),
        "exists": bool(text),
        "busy": busy,
        "matches": matches,
        "clean": bool(text) and not busy and not matches,
    }


def summarize_gate(data: dict[str, Any]) -> dict[str, Any]:
    c = contract(data)
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
        "status": addservice_status(data),
        "counts": counts(data),
        "provider_seen": c.get("vndservice_provider_seen", ""),
        "vndservicemanager_ready": c.get("vndservicemanager_readiness.ready", ""),
        "private_firmware_mounts_requested": c.get("private_firmware_mounts_requested", ""),
        "private_firmware_mnt_mounted": c.get("private_firmware_mnt_mounted", ""),
        "private_firmware_modem_mounted": c.get("private_firmware_modem_mounted", ""),
        "forbidden_clear": forbidden_clear(data),
    }


def classify(
    baseline: dict[str, Any],
    selinuxfs: dict[str, Any],
    policy_load: dict[str, Any],
    post_policy: dict[str, Any],
    post_reboot_ps: Path,
) -> dict[str, Any]:
    baseline_status = addservice_status(baseline)
    post_status = addservice_status(post_policy)
    post_counts = counts(post_policy)
    policy_result = nested_get(policy_load, ("load", "result"), "")
    policy_executed = bool(policy_load.get("policy_load_executed")) or bool(
        nested_get(policy_load, ("load", "policy_load_executed"), 0)
    )
    comparison = {
        "baseline": summarize_gate(baseline),
        "selinuxfs": {
            "decision": selinuxfs.get("decision", ""),
            "pass": bool(selinuxfs.get("pass")),
            "reason": selinuxfs.get("reason", ""),
        },
        "policy_load": {
            "decision": policy_load.get("decision", ""),
            "pass": bool(policy_load.get("pass")),
            "result": policy_result,
            "policy_load_executed": policy_executed,
            "reason": policy_load.get("reason", ""),
        },
        "post_policy": summarize_gate(post_policy),
        "post_reboot_ps": ps_clean(post_reboot_ps),
    }
    flags = {
        "baseline_expected": comparison["baseline"]["decision"] == EXPECTED_BASELINE_DECISION,
        "baseline_addservice_permission_denied": baseline_status.get("signed32") == -1
        and baseline_status.get("name") == "PERMISSION_DENIED",
        "baseline_provider_absent": comparison["baseline"]["provider_seen"] == "0",
        "baseline_failure_log_seen": comparison["baseline"]["counts"].get("pm_add_service_fail_log") == 1,
        "selinuxfs_ready": comparison["selinuxfs"]["decision"] == EXPECTED_SELINUXFS_DECISION
        and comparison["selinuxfs"]["pass"],
        "policy_load_ready": comparison["policy_load"]["decision"] == EXPECTED_POLICY_LOAD_DECISION
        and comparison["policy_load"]["pass"]
        and comparison["policy_load"]["result"] == "policy-load-pass"
        and comparison["policy_load"]["policy_load_executed"],
        "post_policy_addservice_ok": post_status.get("signed32") == 0 and post_status.get("name") == "OK",
        "post_policy_failure_log_absent": post_counts.get("pm_add_service_fail_log") == 0,
        "post_policy_provider_seen": comparison["post_policy"]["provider_seen"] == "1",
        "post_policy_vndservicemanager_ready": comparison["post_policy"]["vndservicemanager_ready"] == "1",
        "post_policy_private_firmware_mounts": all(
            comparison["post_policy"][key] == "1"
            for key in (
                "private_firmware_mounts_requested",
                "private_firmware_mnt_mounted",
                "private_firmware_modem_mounted",
            )
        ),
        "post_policy_forbidden_clear": comparison["post_policy"]["forbidden_clear"],
        "post_reboot_clean": comparison["post_reboot_ps"]["clean"],
    }
    return {
        "comparison": comparison,
        "flags": flags,
        "interpretation": {
            "closed": [
                "V1126 baseline addService failure is SELinux/service-manager PERMISSION_DENIED",
                "V401 made selinuxfs visible for policy load",
                "V490 loaded the compiled Android split policy in the current boot without init reexec",
                "after V490, pm-service addService returned OK and the provider became visible",
            ],
            "active_delta": (
                "private firmware provider registration requires current-boot Android SELinux policy load; "
                "without it, vndservicemanager rejects vendor.qcom.PeripheralManager"
            ),
            "next_gate": (
                "V1128 should integrate the V490 policy-load precondition and replay the private-firmware "
                "CNSS PM path to see whether the blocker advances to PM register/connect or mdm3/eSoC"
            ),
        },
    }


def decide(analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    flags = analysis["flags"]
    required = (
        "baseline_expected",
        "baseline_addservice_permission_denied",
        "baseline_provider_absent",
        "baseline_failure_log_seen",
        "selinuxfs_ready",
        "policy_load_ready",
        "post_policy_addservice_ok",
        "post_policy_failure_log_absent",
        "post_policy_provider_seen",
        "post_policy_vndservicemanager_ready",
        "post_policy_private_firmware_mounts",
        "post_policy_forbidden_clear",
        "post_reboot_clean",
    )
    missing = [key for key in required if not flags[key]]
    if not missing:
        return (
            "v1127-policy-load-repairs-private-firmware-addservice",
            True,
            "V490 current-boot policy load changes pm-service addService from PERMISSION_DENIED to OK and restores provider visibility",
            "run V1128 with V490 policy-load as an explicit precondition before replaying the private-firmware CNSS PM path",
        )
    return (
        "v1127-policy-refresh-classifier-incomplete",
        False,
        f"missing={missing}",
        "refresh V1127 evidence or inspect post-policy trace manually before advancing",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    flag_rows = [[key, value] for key, value in analysis["flags"].items()]
    comparison_rows = [
        ["baseline", json.dumps(analysis["comparison"]["baseline"], sort_keys=True)],
        ["selinuxfs", json.dumps(analysis["comparison"]["selinuxfs"], sort_keys=True)],
        ["policy_load", json.dumps(analysis["comparison"]["policy_load"], sort_keys=True)],
        ["post_policy", json.dumps(analysis["comparison"]["post_policy"], sort_keys=True)],
        ["post_reboot_ps", json.dumps(analysis["comparison"]["post_reboot_ps"], sort_keys=True)],
    ]
    return "\n".join(
        [
            "# V1127 Private Firmware Policy Refresh Classifier",
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
            markdown_table(["flag", "value"], flag_rows),
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
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--baseline-manifest", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--selinuxfs-manifest", type=Path, default=DEFAULT_SELINUXFS)
    parser.add_argument("--policy-load-manifest", type=Path, default=DEFAULT_POLICY_LOAD)
    parser.add_argument("--post-policy-manifest", type=Path, default=DEFAULT_POST_POLICY)
    parser.add_argument("--post-reboot-ps", type=Path, default=DEFAULT_POST_REBOOT_PS)
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
                "next_gate": "run V1127 host-only classifier",
            },
        }
        decision, passed, reason, next_step = (
            "v1127-policy-refresh-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V1127 host-only classifier against V1126 and post-policy V1127 evidence",
        )
    else:
        analysis = classify(
            load_json(args.baseline_manifest),
            load_json(args.selinuxfs_manifest),
            load_json(args.policy_load_manifest),
            load_json(args.post_policy_manifest),
            args.post_reboot_ps,
        )
        decision, passed, reason, next_step = decide(analysis)

    manifest = {
        "cycle": "v1127",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "inputs": {
            "baseline_manifest": str(repo_path(args.baseline_manifest)),
            "selinuxfs_manifest": str(repo_path(args.selinuxfs_manifest)),
            "policy_load_manifest": str(repo_path(args.policy_load_manifest)),
            "post_policy_manifest": str(repo_path(args.post_policy_manifest)),
            "post_reboot_ps": str(repo_path(args.post_reboot_ps)),
        },
        "analysis": analysis,
        "device_commands_executed": False,
        "firmware_mounts_executed": False,
        "global_modem_holder_opened": False,
        "tracefs_write_executed": False,
        "policy_load_executed": False,
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
