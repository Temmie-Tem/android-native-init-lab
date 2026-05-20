#!/usr/bin/env python3
"""V421 host-only plan packet for a micro hwservicemanager query.

This consumes the V420 post-live gate plus the V414 primary target classifier
and emits a concrete no-scan/no-link micro-query contract.  It executes no
bridge/device command, deploys no helper, starts no daemon/HAL, and never
attempts Wi-Fi bring-up.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_V420_GATE = Path("tmp/wifi/v420-current-gate-packet-post-live-20260520-124014/manifest.json")
DEFAULT_V414 = Path("tmp/wifi/v414-static-runtime-target-classifier-20260520-121416/manifest.json")
DEFAULT_V411_QUERY = Path("tmp/wifi/v419-v411-binderized-lshal-query-live-20260520-123721/query/manifest.json")
DEFAULT_OUT_DIR = Path("tmp/wifi/v421-micro-hwservice-query-plan")
APPROVAL_PHRASE = (
    "approve v421 micro hwservicemanager listByInterface proof only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    evidence: list[str]
    next_step: str


@dataclass(frozen=True)
class QueryTarget:
    fqinstance: str
    fqname: str
    instance: str
    method: str
    expected_result: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v420-gate", type=Path, default=DEFAULT_V420_GATE)
    parser.add_argument("--v414-manifest", type=Path, default=DEFAULT_V414)
    parser.add_argument("--v411-query", type=Path, default=DEFAULT_V411_QUERY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    with resolved.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} is not a JSON object")
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def add_check(checks: list[Check], name: str, status: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, detail, evidence or [], next_step))


def primary_target(v414: dict[str, Any]) -> dict[str, Any]:
    primary = v414.get("primary_target")
    return primary if isinstance(primary, dict) else {}


def runtime_patterns(v414: dict[str, Any]) -> list[str]:
    primary = primary_target(v414)
    patterns = primary.get("runtime_match_patterns")
    if not isinstance(patterns, list):
        return []
    return [str(pattern) for pattern in patterns if "::" in str(pattern) and "/" in str(pattern)]


def split_fqinstance(value: str) -> tuple[str, str]:
    fqname, instance = value.split("/", 1)
    return fqname, instance


def query_targets(patterns: list[str]) -> list[QueryTarget]:
    targets = []
    for pattern in patterns:
        fqname, instance = split_fqinstance(pattern)
        targets.append(QueryTarget(
            fqinstance=pattern,
            fqname=fqname,
            instance=instance,
            method="android.hidl.manager@1.0::IServiceManager.listByInterface",
            expected_result=f"instance list contains {instance!r}",
        ))
    return targets


def checks_for(v420: dict[str, Any], v414: dict[str, Any],
               v411_query: dict[str, Any], targets: list[QueryTarget]) -> list[Check]:
    checks: list[Check] = []
    add_check(
        checks,
        "v420-micro-gate",
        "pass" if v420.get("present") and v420.get("decision") == "v416-current-gate-micro-query-needed" and v420.get("pass") else "blocked",
        f"decision={v420.get('decision')} pass={v420.get('pass')}",
        [str(v420.get("path", ""))],
        "rerun V420 gate after V419/V415 evidence if stale",
    )
    add_check(
        checks,
        "v411-lshal-runtime-gap",
        "pass" if v411_query.get("present") and v411_query.get("decision") == "v411-hal-registration-query-runtime-gap" and v411_query.get("pass") else "blocked",
        f"decision={v411_query.get('decision')} reason={v411_query.get('reason')}",
        [str(v411_query.get("path", ""))],
        "V421 is only needed after bounded lshal times out or cannot provide registrations",
    )
    add_check(
        checks,
        "v414-primary-target",
        "pass" if v414.get("present") and v414.get("decision") == "v414-static-runtime-targets-ready" and bool(targets) else "blocked",
        f"decision={v414.get('decision')} target_count={len(targets)}",
        [str(v414.get("path", ""))],
        "rerun V414 static classifier before designing a micro query",
    )
    add_check(
        checks,
        "query-scope",
        "pass" if targets else "blocked",
        "single-interface listByInterface probes only; no getService in V421",
        [target.fqinstance for target in targets],
        "do not widen to scan/connect/link-up or generic lshal",
    )
    add_check(
        checks,
        "no-live-execution",
        "pass",
        "plan packet executes no bridge/device command and starts no daemon/HAL",
        [],
        "future helper execution requires a separate exact approval gate",
    )
    return checks


def decide(checks: list[Check]) -> tuple[str, bool, str, str]:
    blocked = [check.name for check in checks if check.status == "blocked"]
    if blocked:
        return (
            "v421-micro-hwservice-query-plan-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh V411/V414/V420 evidence before helper implementation",
        )
    return (
        "v421-micro-hwservice-query-plan-ready",
        True,
        "V420 requires a narrower hwservicemanager query and V414 target patterns are available",
        "implement helper v28 micro listByInterface mode and fail-closed runner",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v420 = load_json(args.v420_gate)
    v414 = load_json(args.v414_manifest)
    v411_query = load_json(args.v411_query)
    targets = query_targets(runtime_patterns(v414))
    checks = checks_for(v420, v414, v411_query, targets)
    decision, pass_ok, reason, next_step = decide(checks)
    primary = primary_target(v414)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "source_v420_gate": v420.get("path"),
        "source_v414_manifest": v414.get("path"),
        "source_v411_query": v411_query.get("path"),
        "primary_target": primary,
        "query_targets": [asdict(target) for target in targets],
        "checks": [asdict(check) for check in checks],
        "required_future_approval_phrase": APPROVAL_PHRASE,
        "proposed_helper_version": "a90_android_execns_probe v28",
        "proposed_helper_mode": "wifi-hal-composite-hwservice-listbyinterface",
        "proposed_runner": "scripts/revalidation/wifi_hal_micro_hwservice_query_v421_runner.py",
        "implementation_contract": [
            "start bounded servicemanager, hwservicemanager, and first Wi-Fi HAL candidate in the existing private namespace",
            "query only android.hidl.manager@1.0::IServiceManager.listByInterface(fqName)",
            "try the V414 primary runtime match patterns in ranked order",
            "return service-query-pass only when a returned instance equals the target instance",
            "do not call getService/get in the first micro gate",
            "do not scan, connect, link up, configure credentials, run DHCP, change routing, or bring up Wi-Fi",
            "always terminate/reap bounded children and prove postflight clean",
        ],
        "source_references": [
            {
                "label": "AOSP IServiceManager.hal listByInterface contract",
                "url": "https://android.googlesource.com/platform/system/libhidl/+/refs/heads/android12L-tests-dev/transport/manager/1.0/IServiceManager.hal",
            },
            {
                "label": "AOSP hwservicemanager listByInterface implementation",
                "url": "https://android.googlesource.com/platform/system/hwservicemanager/+/refs/heads/master/ServiceManager.cpp",
            },
            {
                "label": "AOSP lshal implementation context",
                "url": "https://android.googlesource.com/platform/frameworks/native/+/013be5f/cmds/lshal/ListCommand.cpp",
            },
        ],
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "explicitly_not_approved": [
            "helper deploy",
            "servicemanager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, driver bind/unbind, firmware mutation, Android partition write",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# V421 Micro Hwservice Query Plan",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- proposed_helper_version: `{manifest['proposed_helper_version']}`",
        f"- proposed_helper_mode: `{manifest['proposed_helper_mode']}`",
        f"- proposed_runner: `{manifest['proposed_runner']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Query Targets",
        "",
    ]
    for target in manifest["query_targets"]:
        lines.append(f"- `{target['method']}` fqName=`{target['fqname']}` expect `{target['instance']}`")
    lines.extend(["", "## Checks", ""])
    for check in manifest["checks"]:
        lines.append(f"- {check['status']} `{check['name']}`: {check['detail']}")
    lines.extend([
        "",
        "## Future Approval Phrase",
        "",
        f"`{manifest['required_future_approval_phrase']}`",
        "",
        "## Implementation Contract",
        "",
    ])
    for item in manifest["implementation_contract"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Source References", ""])
    for source in manifest["source_references"]:
        lines.append(f"- {source['label']}: {source['url']}")
    return "\n".join(lines) + "\n"


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
    print(f"proposed_helper_version: {manifest['proposed_helper_version']}")
    print(f"proposed_helper_mode: {manifest['proposed_helper_mode']}")
    print(f"query_target_count: {len(manifest['query_targets'])}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
