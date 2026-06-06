#!/usr/bin/env python3
"""Route V411 binderized lshal evidence to the next Wi-Fi gate.

This is host-only.  It reads a V411 manifest, optionally reads the captured
``native/run-registration-query.txt`` file referenced by that manifest, and
emits a private evidence packet describing the next safe branch.

It executes no bridge/device command, performs no helper deploy, starts no
daemon, starts no Wi-Fi HAL, and never attempts Wi-Fi bring-up.
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
DEFAULT_OUT_DIR = Path("tmp/wifi/v412-registration-result-router")

WIFI_SERVICE_RE = re.compile(
    r"(?P<name>(?:android|vendor|com)\.[A-Za-z0-9_.-]*wifi[A-Za-z0-9_.@:/-]*)",
    re.IGNORECASE,
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


def check_status(manifest: dict[str, Any], name: str) -> str:
    checks = manifest.get("checks") if isinstance(manifest.get("checks"), list) else []
    for check in checks:
        if isinstance(check, dict) and check.get("name") == name:
            return str(check.get("status") or "")
    return ""


def live_result_file(manifest: dict[str, Any]) -> Path | None:
    live_result = manifest.get("live_result")
    if not isinstance(live_result, dict):
        return None
    file_name = live_result.get("file")
    manifest_path = manifest.get("path")
    if not isinstance(file_name, str) or not isinstance(manifest_path, str):
        return None
    return Path(manifest_path).parent / file_name


def read_live_text(manifest: dict[str, Any]) -> tuple[str, str]:
    path = live_result_file(manifest)
    if path is None:
        return "", ""
    if not path.exists():
        return str(path), ""
    return str(path), path.read_text(encoding="utf-8", errors="replace")


def service_query_keys(manifest: dict[str, Any]) -> dict[str, str]:
    live_result = manifest.get("live_result")
    if not isinstance(live_result, dict):
        return {}
    keys = live_result.get("service_query_keys")
    if not isinstance(keys, dict):
        return {}
    return {str(key): str(value) for key, value in keys.items()}


def wifi_service_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if "wifi" not in line.lower():
            continue
        for match in WIFI_SERVICE_RE.finditer(line):
            value = match.group("name").rstrip(",;")
            if value not in seen:
                candidates.append(value)
                seen.add(value)
    return candidates


def add_check(checks: list[Check], name: str, status: str, detail: str,
              evidence: list[str], next_step: str) -> None:
    checks.append(Check(name, status, detail, evidence, next_step))


def classify(manifest: dict[str, Any], live_text_path: str, live_text: str) -> tuple[str, bool, str, str, list[Check], list[str]]:
    checks: list[Check] = []
    candidates = wifi_service_candidates(live_text)
    decision = str(manifest.get("decision") or "missing")
    pass_ok = bool(manifest.get("pass"))
    query = service_query_keys(manifest)
    service_result = query.get("result", "")
    service_reason = query.get("reason", "")
    helper_status = check_status(manifest, "helper-v27")
    approval_status = check_status(manifest, "approval-gate")

    if not manifest.get("present"):
        add_check(checks, "v411-manifest", "blocked", "V411 manifest is missing", [str(manifest.get("path"))], "run V411 preflight first")
        return (
            "v412-registration-router-missing-v411",
            False,
            "V411 manifest missing",
            "run V411 deploy/preflight sequence before routing",
            checks,
            candidates,
        )

    add_check(checks, "v411-manifest", "pass", f"decision={decision} pass={pass_ok}", [str(manifest.get("path"))], "classify V411 decision")

    if decision == "v411-hal-registration-query-blocked":
        add_check(checks, "helper-v27", helper_status or "unknown", "remote helper v27 is required before live query", [], "deploy helper v27 with exact approval")
        add_check(checks, "approval-gate", approval_status or "unknown", "live query approval remains separate from deploy", [], "rerun preflight after deploy")
        return (
            "v412-registration-router-waiting-for-v411-deploy",
            True,
            "V411 query is still blocked before live run",
            "execute exact-approved V411 helper v27 deploy, then rerun V411 query preflight",
            checks,
            candidates,
        )

    if decision == "v411-hal-registration-query-preflight-ready":
        add_check(checks, "v411-live-query", "needs-operator", "V411 preflight is ready but live query has not run", [], "approve bounded V411 binderized lshal query if intended")
        return (
            "v412-registration-router-waiting-for-v411-live-query",
            True,
            "V411 live query has not run yet",
            "run exact-approved V411 binderized lshal query before selecting V412",
            checks,
            candidates,
        )

    if decision == "v411-hal-registration-query-tool-missing":
        add_check(checks, "lshal-tool", "blocked", "system lshal is unavailable", [live_text_path] if live_text_path else [], "use Android-side lshal extraction or a smaller native service-manager client")
        return (
            "v412-registration-router-tool-missing",
            True,
            "V411 could not use /system/bin/lshal",
            "plan Android-side lshal extraction or a micro HIDL registration client",
            checks,
            candidates,
        )

    if decision == "v411-hal-registration-query-runtime-gap":
        add_check(checks, "lshal-runtime", "blocked", f"service_result={service_result} reason={service_reason}", [live_text_path] if live_text_path else [], "avoid broader lshal; use a narrower registration query")
        return (
            "v412-registration-router-micro-query-needed",
            True,
            "V411 lshal query did not complete cleanly",
            "implement V412 micro hwservicemanager/HIDL service-list or targeted getService proof",
            checks,
            candidates,
        )

    if decision == "v411-hal-registration-query-pass":
        add_check(checks, "lshal-live-output", "pass" if live_text else "warn", f"captured={bool(live_text)}", [live_text_path] if live_text_path else [], "parse registered Wi-Fi HAL candidates")
        add_check(checks, "wifi-service-candidates", "pass" if candidates else "blocked", f"count={len(candidates)}", candidates[:16], "choose targeted no-scan Wi-Fi HAL client proof")
        if candidates:
            return (
                "v412-registration-router-wifi-service-candidates-ready",
                True,
                "V411 binderized query found Wi-Fi-looking service candidates",
                "plan targeted no-scan/no-link Wi-Fi HAL client proof using captured service name",
                checks,
                candidates,
            )
        return (
            "v412-registration-router-no-wifi-service",
            True,
            "V411 binderized query passed but no Wi-Fi service candidate was parsed",
            "inspect lshal output and vendor manifests before daemon bring-up work",
            checks,
            candidates,
        )

    add_check(checks, "v411-decision", "review", f"unclassified decision={decision}", [str(manifest.get("path"))], "inspect V411 evidence before choosing V412")
    return (
        "v412-registration-router-review-required",
        False,
        f"unclassified V411 decision: {decision}",
        "inspect V411 manifest and live output before widening scope",
        checks,
        candidates,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# V412 Registration Result Router",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- source_v411_manifest: `{manifest['source_v411_manifest']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
    ]
    for check in manifest["checks"]:
        lines.append(f"- {check['status']} `{check['name']}`: {check['detail']}")
    if manifest["wifi_service_candidates"]:
        lines.extend(["", "## Wi-Fi Service Candidates", ""])
        for candidate in manifest["wifi_service_candidates"]:
            lines.append(f"- `{candidate}`")
    return "\n".join(lines) + "\n"


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    source = repo_path(args.v411_manifest)
    v411 = load_json(args.v411_manifest)
    live_text_path, live_text = read_live_text(v411)
    decision, pass_ok, reason, next_step, checks, candidates = classify(v411, live_text_path, live_text)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "source_v411_manifest": str(source),
        "source_v411_decision": str(v411.get("decision") or ""),
        "source_v411_pass": bool(v411.get("pass")),
        "live_text_path": live_text_path,
        "live_text_present": bool(live_text),
        "service_query_keys": service_query_keys(v411),
        "wifi_service_candidates": candidates,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "explicitly_not_approved": [
            "helper deploy",
            "service-manager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd start",
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
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
