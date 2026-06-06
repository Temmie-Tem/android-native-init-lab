#!/usr/bin/env python3
"""V416 host-only Wi-Fi gate status packet.

This aggregates V411-V415 evidence into one current gate decision.  The packet
itself executes no bridge/device command and performs no mutation or Wi-Fi
bring-up; the input evidence can include earlier bounded deploy/query steps.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v416-current-gate-packet")
DEFAULT_V411_DEPLOY = Path("tmp/wifi/v411-current-deploy-preflight-20260520-114943/manifest.json")
DEFAULT_V411_QUERY = Path("tmp/wifi/v411-current-query-preflight-20260520-114943/manifest.json")
DEFAULT_V412 = Path("tmp/wifi/v412-registration-router-current-20260520-115708/manifest.json")
DEFAULT_V413 = Path("tmp/wifi/v413-vintf-live-20260520-120842/manifest.json")
DEFAULT_V414 = Path("tmp/wifi/v414-static-runtime-target-classifier-20260520-121416/manifest.json")
DEFAULT_V415 = Path("tmp/wifi/v415-runtime-static-comparator-20260520-121831/manifest.json")

V411_DEPLOY_PHRASE = "approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up"
V411_QUERY_PHRASE = "approve v411 bounded binderized lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up"
V411_DEPLOY_DECISIONS = {
    "execns-helper-v27-deploy-preflight-ready-needs-deploy",
    "execns-helper-v27-deploy-pass",
}
V411_QUERY_DECISIONS = {
    "v411-hal-registration-query-blocked",
    "v411-hal-registration-query-preflight-ready",
    "v411-hal-registration-query-pass",
    "v411-hal-registration-query-runtime-gap",
    "v411-hal-registration-query-tool-missing",
}
V412_DECISIONS = {
    "v412-registration-router-waiting-for-v411-deploy",
    "v412-registration-router-waiting-for-v411-live-query",
    "v412-registration-router-wifi-service-candidates-ready",
    "v412-registration-router-no-wifi-service",
    "v412-registration-router-micro-query-needed",
    "v412-registration-router-tool-missing",
}
V415_DECISIONS = {
    "v415-runtime-static-comparator-waiting-for-v411-deploy",
    "v415-runtime-static-primary-match",
    "v415-runtime-static-review-required",
    "v415-runtime-static-comparator-micro-query-needed",
}


@dataclass(frozen=True)
class EvidenceInput:
    name: str
    path: str
    present: bool
    decision: str
    pass_ok: bool
    reason: str
    next_step: str
    device_commands_executed: bool
    device_mutations: bool
    daemon_start_executed: bool
    wifi_hal_start_executed: bool
    wifi_bringup_executed: bool


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v411-deploy", type=Path, default=DEFAULT_V411_DEPLOY)
    parser.add_argument("--v411-query", type=Path, default=DEFAULT_V411_QUERY)
    parser.add_argument("--v412", type=Path, default=DEFAULT_V412)
    parser.add_argument("--v413", type=Path, default=DEFAULT_V413)
    parser.add_argument("--v414", type=Path, default=DEFAULT_V414)
    parser.add_argument("--v415", type=Path, default=DEFAULT_V415)
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


def summarize(name: str, payload: dict[str, Any]) -> EvidenceInput:
    return EvidenceInput(
        name=name,
        path=str(payload.get("path", "")),
        present=bool(payload.get("present")),
        decision=str(payload.get("decision") or ""),
        pass_ok=bool(payload.get("pass")),
        reason=str(payload.get("reason") or ""),
        next_step=str(payload.get("next_step") or ""),
        device_commands_executed=bool(payload.get("device_commands_executed")),
        device_mutations=bool(payload.get("device_mutations")),
        daemon_start_executed=bool(payload.get("daemon_start_executed")),
        wifi_hal_start_executed=bool(payload.get("wifi_hal_start_executed")),
        wifi_bringup_executed=bool(payload.get("wifi_bringup_executed")),
    )


def add_check(checks: list[Check], name: str, status: str, detail: str,
              evidence: list[str], next_step: str) -> None:
    checks.append(Check(name, status, detail, evidence, next_step))


def primary_target(v414: dict[str, Any]) -> str:
    primary = v414.get("primary_target")
    if isinstance(primary, dict):
        return str(primary.get("fqinstance") or "")
    return ""


def primary_patterns(v414: dict[str, Any]) -> list[str]:
    primary = v414.get("primary_target")
    if not isinstance(primary, dict):
        return []
    patterns = primary.get("runtime_match_patterns")
    if not isinstance(patterns, list):
        return []
    return [str(pattern) for pattern in patterns if pattern]


def input_map(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    return {
        "v411_deploy": load_json(args.v411_deploy),
        "v411_query": load_json(args.v411_query),
        "v412": load_json(args.v412),
        "v413": load_json(args.v413),
        "v414": load_json(args.v414),
        "v415": load_json(args.v415),
    }


def decision_ok(payload: dict[str, Any], allowed: set[str], *, allow_blocked: set[str] | None = None) -> bool:
    decision = str(payload.get("decision") or "")
    if decision not in allowed:
        return False
    if allow_blocked and decision in allow_blocked:
        return True
    return bool(payload.get("pass"))


def mutation_boundary(inputs: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    wifi_bringup = [
        name
        for name, payload in inputs.items()
        if payload.get("wifi_bringup_executed")
    ]
    unexpected: list[str] = []
    for name, payload in inputs.items():
        decision = str(payload.get("decision") or "")
        device_mutation = bool(payload.get("device_mutations"))
        daemon_start = bool(payload.get("daemon_start_executed"))
        wifi_hal_start = bool(payload.get("wifi_hal_start_executed"))
        if name == "v411_deploy":
            if decision == "execns-helper-v27-deploy-pass":
                if daemon_start or wifi_hal_start:
                    unexpected.append(name)
            elif device_mutation or daemon_start or wifi_hal_start:
                unexpected.append(name)
            continue
        if name == "v411_query":
            if decision in {
                "v411-hal-registration-query-pass",
                "v411-hal-registration-query-runtime-gap",
                "v411-hal-registration-query-tool-missing",
            }:
                continue
            if device_mutation or daemon_start or wifi_hal_start:
                unexpected.append(name)
            continue
        if device_mutation or daemon_start or wifi_hal_start:
            unexpected.append(name)
    return wifi_bringup, unexpected


def build_checks(inputs: dict[str, dict[str, Any]]) -> list[Check]:
    checks: list[Check] = []
    for name, payload in inputs.items():
        add_check(
            checks,
            f"{name}-present",
            "pass" if payload.get("present") else "blocked",
            f"decision={payload.get('decision')} pass={payload.get('pass')}",
            [str(payload.get("path", ""))],
            f"refresh {name} evidence if missing",
        )
    v411_deploy = inputs["v411_deploy"]
    v411_query = inputs["v411_query"]
    v412 = inputs["v412"]
    v413 = inputs["v413"]
    v414 = inputs["v414"]
    v415 = inputs["v415"]
    add_check(
        checks,
        "v411-deploy-state",
        "pass" if decision_ok(v411_deploy, V411_DEPLOY_DECISIONS) else "blocked",
        str(v411_deploy.get("reason") or ""),
        [str(v411_deploy.get("path", ""))],
        "use deploy-wait or deploy-pass evidence",
    )
    add_check(
        checks,
        "v411-query-state",
        "pass" if decision_ok(v411_query, V411_QUERY_DECISIONS, allow_blocked={"v411-hal-registration-query-blocked"}) else "blocked",
        str(v411_query.get("reason") or ""),
        [str(v411_query.get("path", ""))],
        "use blocked, preflight-ready, pass, runtime-gap, or tool-missing evidence",
    )
    add_check(
        checks,
        "branch-router-state",
        "pass" if decision_ok(v412, V412_DECISIONS) else "blocked",
        str(v412.get("reason") or ""),
        [str(v412.get("path", ""))],
        "rerun router after V411 state changes",
    )
    add_check(
        checks,
        "static-target-context-ready",
        "pass" if v413.get("decision") == "v413-vintf-wifi-declarations-ready" and v414.get("decision") == "v414-static-runtime-targets-ready" else "blocked",
        f"primary={primary_target(v414)} patterns={len(primary_patterns(v414))}",
        primary_patterns(v414),
        "compare with V411 runtime output after live query",
    )
    add_check(
        checks,
        "runtime-static-comparator-state",
        "pass" if decision_ok(v415, V415_DECISIONS) else "blocked",
        str(v415.get("reason") or ""),
        [str(v415.get("path", ""))],
        "rerun V415 after V411 state changes",
    )
    wifi_bringup, unexpected_mutations = mutation_boundary(inputs)
    add_check(
        checks,
        "no-wifi-bringup-boundary",
        "pass" if not wifi_bringup else "blocked",
        "no input evidence executed Wi-Fi bring-up" if not wifi_bringup else "Wi-Fi bring-up flags in " + ", ".join(wifi_bringup),
        wifi_bringup,
        "do not proceed if any Wi-Fi bring-up appears in gate evidence",
    )
    add_check(
        checks,
        "bounded-mutation-boundary",
        "pass" if not unexpected_mutations else "blocked",
        "only V411 deploy/query bounded mutations are present" if not unexpected_mutations else "unexpected mutation flags in " + ", ".join(unexpected_mutations),
        unexpected_mutations,
        "review evidence before widening scope",
    )
    return checks


def decide(inputs: dict[str, dict[str, Any]], checks: list[Check]) -> tuple[str, bool, str, str, str, list[str]]:
    blocked = [check.name for check in checks if check.status == "blocked"]
    if blocked:
        return (
            "v416-current-gate-packet-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh or repair missing/blocked evidence before live gate",
            "review",
            [],
        )
    v411_query_decision = str(inputs["v411_query"].get("decision") or "")
    v415_decision = str(inputs["v415"].get("decision") or "")
    if v411_query_decision == "v411-hal-registration-query-blocked" and v415_decision == "v415-runtime-static-comparator-waiting-for-v411-deploy":
        return (
            "v416-current-gate-waiting-for-v411-deploy",
            True,
            "all host-side follow-up tools are ready; live path is blocked only by helper v27 deploy gate",
            "execute exact-approved V411 helper v27 deploy only, then rerun V411 query preflight",
            "v411-helper-v27-deploy-only",
            [V411_DEPLOY_PHRASE],
        )
    if v411_query_decision == "v411-hal-registration-query-preflight-ready":
        return (
            "v416-current-gate-waiting-for-v411-live-query",
            True,
            "helper v27 appears deployed and query preflight is ready",
            "execute exact-approved V411 binderized live query only",
            "v411-binderized-live-query",
            [V411_QUERY_PHRASE],
        )
    if v415_decision == "v415-runtime-static-primary-match":
        return (
            "v416-current-gate-primary-runtime-match-ready",
            True,
            "runtime registration matches primary static target",
            "plan no-scan/no-link HIDL client proof for the matched Samsung Wi-Fi HAL",
            "no-scan-hidl-client-proof-plan",
            [],
        )
    if v415_decision == "v415-runtime-static-comparator-micro-query-needed":
        return (
            "v416-current-gate-micro-query-needed",
            True,
            "runtime query did not provide comparable registrations",
            "design micro hwservicemanager query using V414 primary target patterns",
            "micro-hwservicemanager-query-plan",
            [],
        )
    return (
        "v416-current-gate-review-required",
        False,
        f"unclassified state: v411_query={v411_query_decision} v415={v415_decision}",
        "inspect V411-V415 manifests before widening scope",
        "review",
        [],
    )


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# V416 Current Wi-Fi Gate Packet",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- next_gate: `{manifest['next_gate']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Required Approval Phrases",
        "",
    ]
    for phrase in manifest["required_approval_phrases"]:
        lines.append(f"- `{phrase}`")
    lines.extend(["", "## Inputs", ""])
    for item in manifest["inputs"]:
        lines.append(f"- `{item['name']}`: `{item['decision']}` pass={item['pass_ok']} path=`{item['path']}`")
    lines.extend(["", "## Checks", ""])
    for check in manifest["checks"]:
        lines.append(f"- {check['status']} `{check['name']}`: {check['detail']}")
    lines.extend(["", "## Primary Target", ""])
    lines.append(f"- `{manifest['primary_target']}`")
    for pattern in manifest["primary_patterns"]:
        lines.append(f"- match `{pattern}`")
    return "\n".join(lines) + "\n"


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    inputs = input_map(args)
    summaries = [summarize(name, payload) for name, payload in inputs.items()]
    checks = build_checks(inputs)
    decision, pass_ok, reason, next_step, next_gate, phrases = decide(inputs, checks)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "next_gate": next_gate,
        "host": collect_host_metadata(),
        "inputs": [asdict(summary) for summary in summaries],
        "checks": [asdict(check) for check in checks],
        "primary_target": primary_target(inputs["v414"]),
        "primary_patterns": primary_patterns(inputs["v414"]),
        "required_approval_phrases": phrases,
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
    print(f"next_gate: {manifest['next_gate']}")
    for phrase in manifest["required_approval_phrases"]:
        print(f"required_approval_phrase: {phrase}")
    print(f"primary_target: {manifest['primary_target']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
