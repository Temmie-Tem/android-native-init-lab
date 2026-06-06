#!/usr/bin/env python3
"""V415 host-only comparator for V411 runtime registrations and V414 targets.

This reads existing V411 and V414 evidence.  It executes no bridge/device
command, deploys no helper, starts no daemon/HAL, and never attempts Wi-Fi
bring-up.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_V411_MANIFEST = Path("tmp/wifi/v411-current-query-preflight-20260520-114943/manifest.json")
DEFAULT_V414_MANIFEST = Path("tmp/wifi/v414-static-runtime-target-classifier-20260520-121416/manifest.json")
DEFAULT_OUT_DIR = Path("tmp/wifi/v415-runtime-static-comparator")

FQINSTANCE_RE = re.compile(
    r"(?P<fqinstance>(?:android|vendor|com)\.[A-Za-z0-9_.-]+@\d+\.\d+::[A-Za-z0-9_]+/[A-Za-z0-9_.:-]+)"
)


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
    parser.add_argument("--v411-manifest", type=Path, default=DEFAULT_V411_MANIFEST)
    parser.add_argument("--v414-manifest", type=Path, default=DEFAULT_V414_MANIFEST)
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


def live_result_file(manifest: dict[str, Any]) -> Path | None:
    live_result = manifest.get("live_result")
    if not isinstance(live_result, dict):
        return None
    file_name = live_result.get("file")
    manifest_path = manifest.get("path")
    if not isinstance(file_name, str) or not isinstance(manifest_path, str):
        return None
    return Path(manifest_path).parent / file_name


def live_text(manifest: dict[str, Any]) -> tuple[str, str]:
    path = live_result_file(manifest)
    if path is None:
        return "", ""
    if not path.exists():
        return str(path), ""
    return str(path), path.read_text(encoding="utf-8", errors="replace")


def extract_fqinstances(text: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for match in FQINSTANCE_RE.finditer(text):
        value = match.group("fqinstance").rstrip(",;")
        if value not in seen:
            values.append(value)
            seen.add(value)
    return values


def target_patterns(v414: dict[str, Any]) -> list[str]:
    primary = v414.get("primary_target")
    if isinstance(primary, dict):
        patterns = primary.get("runtime_match_patterns")
        if isinstance(patterns, list):
            return [str(item) for item in patterns if item]
    return []


def top_patterns(v414: dict[str, Any]) -> list[str]:
    patterns: list[str] = []
    seen: set[str] = set()
    records = v414.get("top_records")
    if not isinstance(records, list):
        return patterns
    for record in records:
        if not isinstance(record, dict):
            continue
        for item in record.get("runtime_match_patterns", []):
            value = str(item)
            if value and value not in seen:
                patterns.append(value)
                seen.add(value)
    return patterns


def primary_target(v414: dict[str, Any]) -> str:
    primary = v414.get("primary_target")
    if isinstance(primary, dict):
        return str(primary.get("fqinstance") or "")
    return ""


def service_query_keys(v411: dict[str, Any]) -> dict[str, str]:
    live_result = v411.get("live_result")
    if not isinstance(live_result, dict):
        return {}
    keys = live_result.get("service_query_keys")
    if not isinstance(keys, dict):
        return {}
    return {str(key): str(value) for key, value in keys.items()}


def add_check(checks: list[Check], name: str, status: str, detail: str,
              evidence: list[str], next_step: str) -> None:
    checks.append(Check(name, status, detail, evidence, next_step))


def compare(v411: dict[str, Any], v414: dict[str, Any]) -> tuple[dict[str, Any], list[Check]]:
    checks: list[Check] = []
    v411_decision = str(v411.get("decision") or "")
    v414_decision = str(v414.get("decision") or "")
    text_path, text = live_text(v411)
    runtime = extract_fqinstances(text)
    primary_patterns = target_patterns(v414)
    secondary_patterns = top_patterns(v414)
    primary_matches = [item for item in runtime if item in set(primary_patterns)]
    secondary_matches = [item for item in runtime if item in set(secondary_patterns)]

    add_check(
        checks,
        "v411-source",
        "pass" if v411.get("present") else "blocked",
        f"decision={v411_decision} pass={v411.get('pass')}",
        [str(v411.get("path", ""))],
        "run V411 deploy/query sequence before comparison",
    )
    add_check(
        checks,
        "v414-source",
        "pass" if v414.get("decision") == "v414-static-runtime-targets-ready" and v414.get("pass") else "blocked",
        f"decision={v414_decision} pass={v414.get('pass')}",
        [str(v414.get("path", ""))],
        "rerun V414 target classifier if stale or missing",
    )
    add_check(
        checks,
        "primary-target-patterns",
        "pass" if primary_patterns else "blocked",
        f"primary={primary_target(v414)} pattern_count={len(primary_patterns)}",
        primary_patterns,
        "V414 must provide runtime match patterns",
    )

    result = {
        "v411_decision": v411_decision,
        "v411_pass": bool(v411.get("pass")),
        "v414_decision": v414_decision,
        "v414_pass": bool(v414.get("pass")),
        "primary_target": primary_target(v414),
        "primary_patterns": primary_patterns,
        "secondary_pattern_count": len(secondary_patterns),
        "live_text_path": text_path,
        "live_text_present": bool(text),
        "runtime_registrations": runtime,
        "primary_matches": primary_matches,
        "secondary_matches": secondary_matches,
        "service_query_keys": service_query_keys(v411),
    }
    if not v411.get("present"):
        add_check(checks, "comparison-state", "blocked", "V411 manifest missing", [], "run V411 preflight first")
        result.update({
            "decision": "v415-runtime-static-comparator-missing-v411",
            "pass": False,
            "reason": "V411 manifest missing",
            "next_step": "run V411 deploy/preflight sequence before comparing runtime/static targets",
        })
        return result, checks
    if not v414.get("present") or not primary_patterns:
        add_check(checks, "comparison-state", "blocked", "V414 target data missing", [], "run V414 classifier")
        result.update({
            "decision": "v415-runtime-static-comparator-missing-v414",
            "pass": False,
            "reason": "V414 target patterns missing",
            "next_step": "run V414 target classifier before comparing runtime/static targets",
        })
        return result, checks
    if v411_decision == "v411-hal-registration-query-blocked":
        add_check(checks, "comparison-state", "waiting", "V411 runtime query has not run; helper v27 still required", [], "deploy helper v27, rerun V411 preflight, then live query")
        result.update({
            "decision": "v415-runtime-static-comparator-waiting-for-v411-deploy",
            "pass": True,
            "reason": "V411 is blocked before runtime registration query",
            "next_step": "execute exact-approved V411 helper v27 deploy before runtime/static comparison",
        })
        return result, checks
    if v411_decision == "v411-hal-registration-query-preflight-ready":
        add_check(checks, "comparison-state", "waiting", "V411 preflight is ready but live query is absent", [], "run exact-approved V411 binderized live query")
        result.update({
            "decision": "v415-runtime-static-comparator-waiting-for-v411-live-query",
            "pass": True,
            "reason": "V411 live registration query has not run",
            "next_step": "run exact-approved V411 binderized lshal query before comparing targets",
        })
        return result, checks
    if v411_decision in {"v411-hal-registration-query-runtime-gap", "v411-hal-registration-query-tool-missing"}:
        add_check(checks, "comparison-state", "runtime-gap", f"V411 decision={v411_decision}", [text_path] if text_path else [], "use V414 targets for a narrower micro registration query")
        result.update({
            "decision": "v415-runtime-static-comparator-micro-query-needed",
            "pass": True,
            "reason": f"V411 runtime query did not provide comparable registrations: {v411_decision}",
            "next_step": "design micro hwservicemanager query using V414 primary target patterns",
        })
        return result, checks
    if v411_decision == "v411-hal-registration-query-pass":
        add_check(checks, "runtime-registrations", "pass" if runtime else "blocked", f"runtime_count={len(runtime)}", runtime[:16], "inspect V411 output if runtime registrations are missing")
        add_check(checks, "primary-runtime-match", "pass" if primary_matches else "review", f"match_count={len(primary_matches)}", primary_matches, "if matched, plan no-scan/no-link HIDL client proof")
        if primary_matches:
            result.update({
                "decision": "v415-runtime-static-primary-match",
                "pass": True,
                "reason": "V411 runtime registrations match V414 primary Samsung Wi-Fi target",
                "next_step": "plan no-scan/no-link HIDL client proof for matched Samsung Wi-Fi HAL service",
            })
        elif secondary_matches:
            result.update({
                "decision": "v415-runtime-static-secondary-match",
                "pass": True,
                "reason": "V411 runtime registrations match V414 secondary Wi-Fi target but not primary",
                "next_step": "review secondary runtime match before choosing no-scan client proof target",
            })
        else:
            result.update({
                "decision": "v415-runtime-static-no-match",
                "pass": True,
                "reason": "V411 runtime registrations did not match V414 ranked static Wi-Fi targets",
                "next_step": "inspect V411 output and consider micro target query before client proof",
            })
        return result, checks
    add_check(checks, "comparison-state", "review", f"unclassified V411 decision={v411_decision}", [], "inspect V411 evidence")
    result.update({
        "decision": "v415-runtime-static-comparator-review-required",
        "pass": False,
        "reason": f"unclassified V411 decision: {v411_decision}",
        "next_step": "inspect V411 and V414 evidence before widening scope",
    })
    return result, checks


def render_summary(manifest: dict[str, Any]) -> str:
    comparison = manifest["comparison"]
    lines = [
        "# V415 Runtime Static Comparator",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- primary_target: `{comparison['primary_target']}`",
        f"- runtime_registration_count: `{len(comparison['runtime_registrations'])}`",
        f"- primary_match_count: `{len(comparison['primary_matches'])}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Primary Patterns",
        "",
    ]
    for pattern in comparison["primary_patterns"]:
        lines.append(f"- `{pattern}`")
    if comparison["runtime_registrations"]:
        lines.extend(["", "## Runtime Registrations", ""])
        for item in comparison["runtime_registrations"]:
            lines.append(f"- `{item}`")
    lines.extend(["", "## Checks", ""])
    for check in manifest["checks"]:
        lines.append(f"- {check['status']} `{check['name']}`: {check['detail']}")
    return "\n".join(lines) + "\n"


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v411_source = repo_path(args.v411_manifest)
    v414_source = repo_path(args.v414_manifest)
    v411 = load_json(args.v411_manifest)
    v414 = load_json(args.v414_manifest)
    comparison, checks = compare(v411, v414)
    return {
        "generated_at": now_iso(),
        "decision": comparison["decision"],
        "pass": comparison["pass"],
        "reason": comparison["reason"],
        "next_step": comparison["next_step"],
        "host": collect_host_metadata(),
        "source_v411_manifest": str(v411_source),
        "source_v414_manifest": str(v414_source),
        "comparison": comparison,
        "checks": [asdict(check) for check in checks],
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
    print(f"primary_target: {manifest['comparison']['primary_target']}")
    print(f"runtime_registration_count: {len(manifest['comparison']['runtime_registrations'])}")
    print(f"primary_match_count: {len(manifest['comparison']['primary_matches'])}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
