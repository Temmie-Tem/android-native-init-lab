#!/usr/bin/env python3
"""V689 host-only classifier for PeripheralManager property shim requests."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v689-peripheral-property-shim-classifier")
DEFAULT_V688_MANIFEST = Path("tmp/wifi/v688-peripheral-manager-cnss-retry-orchestrated-live/manifest.json")
DEFAULT_V685_MANIFEST = Path("tmp/wifi/v685-peripheral-manager-provider-plan-check/manifest.json")
DEFAULT_V676_MANIFEST = Path("tmp/wifi/v676-v535-property-android-order-orchestrated-live/manifest.json")

EXPECTED_PRIVATE_ACKS = {
    ("vendor.peripheral.SDX50M.state", "OFFLINE"),
    ("vendor.peripheral.modem.state", "OFFLINE"),
}
PROPERTY_PREFIX = "wifi_hal_composite_start.property_service_shim."
FORBIDDEN_ACTIONS = (
    "device command",
    "helper deploy",
    "daemon or service start",
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "scan/connect/link-up",
    "credential, DHCP, route change, or external ping",
    "boot image or partition write",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v688-manifest", type=Path, default=DEFAULT_V688_MANIFEST)
    parser.add_argument("--v685-manifest", type=Path, default=DEFAULT_V685_MANIFEST)
    parser.add_argument("--v676-manifest", type=Path, default=DEFAULT_V676_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {"present": False, "path": str(repo_path(path))}
    data = json.loads(text)
    data["present"] = True
    data["path"] = str(repo_path(path))
    return data


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)=(.*)$", line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def arm_manifest_from_v688(v688: dict[str, Any]) -> dict[str, Any]:
    arm_path = ((v688.get("arm_v688") or {}).get("manifest") or "")
    if not arm_path:
        return {}
    return load_json(Path(str(arm_path)))


def evidence_dir(manifest: dict[str, Any], fallback_manifest_path: Path) -> Path:
    evidence = manifest.get("evidence") or manifest.get("out_dir")
    if evidence:
        return repo_path(Path(str(evidence)))
    return repo_path(fallback_manifest_path).parent


def companion_text(v688_path: Path, v688: dict[str, Any], arm: dict[str, Any]) -> str:
    arm_evidence = evidence_dir(arm, Path(str((v688.get("arm_v688") or {}).get("manifest") or v688_path)))
    return read_text(arm_evidence / "native" / "companion-start-only-with-holder.txt")


def property_requests(keys: dict[str, str]) -> list[dict[str, str]]:
    request_count = int(keys.get(PROPERTY_PREFIX + "request_count") or "0")
    requests: list[dict[str, str]] = []
    for idx in range(1, request_count + 1):
        requests.append({
            "index": str(idx),
            "cmd": keys.get(f"{PROPERTY_PREFIX}request.{idx}.cmd", ""),
            "name": keys.get(f"{PROPERTY_PREFIX}request.{idx}.name", ""),
            "value": keys.get(f"{PROPERTY_PREFIX}request.{idx}.value", ""),
            "allowed": keys.get(f"{PROPERTY_PREFIX}request.{idx}.allowed", ""),
            "result": keys.get(f"{PROPERTY_PREFIX}request.{idx}.result", ""),
        })
    return requests


def child_status(keys: dict[str, str], name: str) -> dict[str, str]:
    child_prefix = f"wifi_companion_start.child.{name}."
    preexec_prefix = f"wifi_hal_composite_child.{name}."
    return {
        "start_order": keys.get(child_prefix + "start_order", ""),
        "observable": keys.get(child_prefix + "observable", ""),
        "exited": keys.get(child_prefix + "exited", ""),
        "exit_code": keys.get(child_prefix + "exit_code", ""),
        "signal": keys.get(child_prefix + "signal", ""),
        "postflight_safe": keys.get(child_prefix + "postflight_safe", ""),
        "selinux_exec_skipped": keys.get(preexec_prefix + "selinux_exec.skipped", ""),
        "selinux_exec_reason": keys.get(preexec_prefix + "selinux_exec.reason", ""),
        "selinux_exec_errno": keys.get(preexec_prefix + "selinux_exec.errno", ""),
        "selinux_exec_target_context": keys.get(preexec_prefix + "selinux_exec.target_context", ""),
    }


def denied_vendor_peripheral_requests(requests: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        request
        for request in requests
        if request["name"].startswith("vendor.peripheral.")
        and request["result"].lower() == "0x00000018"
    ]


def request_counter(requests: list[dict[str, str]]) -> list[list[Any]]:
    counter = collections.Counter((request["name"], request["value"], request["allowed"], request["result"]) for request in requests)
    return [[name, value, allowed, result, count] for (name, value, allowed, result), count in counter.most_common()]


def v685_contract(v685: dict[str, Any]) -> dict[str, Any]:
    host_surface = v685.get("host_surface") or {}
    if isinstance(host_surface.get("vendor_init"), dict):
        return host_surface["vendor_init"]
    host = v685.get("host") or {}
    return host.get("vendor_init") or {}


def v676_property_surface(v676: dict[str, Any]) -> dict[str, Any]:
    reason = str(v676.get("reason") or "")
    return {
        "decision": v676.get("decision"),
        "pass": v676.get("pass"),
        "mentions_permgrlib": "PerMgrLib" in reason,
        "property_denial_summary": reason[reason.find("property_surface="): reason.find("}; counts=") + 1] if "property_surface=" in reason else "",
    }


def decide(command: str,
           v688: dict[str, Any],
           arm: dict[str, Any],
           requests: list[dict[str, str]],
           children: dict[str, dict[str, str]],
           contract: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v689-peripheral-property-shim-classifier-plan-ready",
            True,
            "plan-only; no evidence parsed",
            "run host-only V689 classifier against V688/V685/V676 evidence",
        )
    if not v688.get("present") or not arm.get("present"):
        return "v689-missing-v688-evidence", False, "V688 manifest or arm manifest missing", "restore V688 evidence before V689"
    if v688.get("decision") != "v688-provider-start-gap-classified":
        return "v689-v688-state-mismatch", False, f"v688_decision={v688.get('decision')}", "refresh V688 live proof before property shim classification"
    if arm.get("context_repair_regressed"):
        return "v689-context-repair-regressed", False, "V688 arm still shows invalid SELinux context regression", "repair context before property shim classification"
    denied = denied_vendor_peripheral_requests(requests)
    denied_pairs = {(request["name"], request["value"]) for request in denied}
    unexpected = sorted(denied_pairs - EXPECTED_PRIVATE_ACKS)
    missing = sorted(EXPECTED_PRIVATE_ACKS - denied_pairs)
    provider_seen = all((children.get(name) or {}).get("observable") == "1" for name in ("per_mgr", "per_proxy"))
    provider_exited = all((children.get(name) or {}).get("exited") == "1" for name in ("per_mgr", "per_proxy"))
    init_contract_ready = all(bool(contract.get(key)) for key in (
        "has_per_mgr_service",
        "has_per_proxy_service",
        "per_mgr_user_system",
        "per_mgr_group_system",
        "per_proxy_disabled",
        "per_proxy_started_by_per_mgr",
    ))
    if unexpected:
        return (
            "v689-peripheral-property-shim-broader-than-expected",
            True,
            f"unexpected denied vendor peripheral requests={unexpected}",
            "do not broaden shim; capture Android property contract first",
        )
    if missing:
        return (
            "v689-peripheral-property-shim-incomplete-evidence",
            True,
            f"missing expected denied pairs={missing}",
            "repeat V688 or inspect provider output before helper changes",
        )
    if denied and provider_seen and provider_exited and init_contract_ready:
        return (
            "v689-peripheral-property-shim-candidate",
            True,
            f"only exact denied peripheral state writes are {sorted(denied_pairs)}; provider exits after those denials",
            "V690 should acknowledge only those exact private shim writes, then rerun bounded provider/CNSS retry",
        )
    return (
        "v689-peripheral-property-shim-manual-review",
        True,
        f"denied={denied} provider_seen={provider_seen} provider_exited={provider_exited} init_contract_ready={init_contract_ready}",
        "inspect evidence before changing shim allowlist",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v688 = load_json(args.v688_manifest)
    arm = arm_manifest_from_v688(v688)
    v685 = load_json(args.v685_manifest)
    v676 = load_json(args.v676_manifest)
    text = "" if args.command == "plan" else companion_text(args.v688_manifest, v688, arm)
    keys = parse_keys(text)
    requests = property_requests(keys)
    children = {name: child_status(keys, name) for name in ("per_mgr", "per_proxy", "cnss_daemon_retry")}
    contract = v685_contract(v685)
    decision, pass_ok, reason, next_step = decide(args.command, v688, arm, requests, children, contract)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v689",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v688": {"path": v688.get("path"), "present": bool(v688.get("present")), "decision": v688.get("decision"), "pass": v688.get("pass")},
            "v688_arm": {"path": arm.get("path"), "present": bool(arm.get("present")), "decision": arm.get("decision"), "pass": arm.get("pass")},
            "v685": {"path": v685.get("path"), "present": bool(v685.get("present")), "decision": v685.get("decision"), "pass": v685.get("pass")},
            "v676": {"path": v676.get("path"), "present": bool(v676.get("present")), "decision": v676.get("decision"), "pass": v676.get("pass")},
        },
        "property_service_shim": {
            "started": keys.get(PROPERTY_PREFIX + "started", ""),
            "allowlist": keys.get(PROPERTY_PREFIX + "allowlist", ""),
            "request_count": keys.get(PROPERTY_PREFIX + "request_count", ""),
            "requests": requests,
            "request_counts": request_counter(requests),
            "denied_vendor_peripheral_requests": denied_vendor_peripheral_requests(requests),
            "expected_private_acks": sorted([list(item) for item in EXPECTED_PRIVATE_ACKS]),
        },
        "provider_children": children,
        "v685_contract": contract,
        "v676_property_surface": v676_property_surface(v676),
        "recommended_v690_exact_acks": sorted([list(item) for item in EXPECTED_PRIVATE_ACKS]),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    request_rows = [
        [str(name), str(value), str(allowed), str(result), str(count)]
        for name, value, allowed, result, count in manifest["property_service_shim"]["request_counts"]
    ]
    child_rows = [
        [name, data["observable"], data["exited"], data["exit_code"], data["signal"], data["selinux_exec_reason"]]
        for name, data in manifest["provider_children"].items()
    ]
    input_rows = [
        [name, str(data["present"]), str(data.get("decision")), str(data.get("path"))]
        for name, data in manifest["inputs"].items()
    ]
    return "\n".join([
        "# V689 Peripheral Property Shim Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "present", "decision", "path"], input_rows),
        "",
        "## Property Requests",
        "",
        markdown_table(["name", "value", "allowed", "result", "count"], request_rows),
        "",
        "## Provider Children",
        "",
        markdown_table(["child", "observable", "exited", "exit_code", "signal", "selinux_reason"], child_rows),
        "",
        "## Recommended V690 Exact Acks",
        "",
        *[f"- `{name}={value}`" for name, value in manifest["recommended_v690_exact_acks"]],
        "",
        "## Guardrails",
        "",
        *[f"- {item}" for item in manifest["forbidden_actions"]],
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
