#!/usr/bin/env python3
"""Route V366 runtime repair smoke results to the next safe Wi-Fi action.

This is host-only: it reads manifests, emits a decision and recommended next
commands, and never opens the serial bridge or mutates the device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from wifi_runtime_repair_smoke import APPROVAL_PHRASE


DEFAULT_OUT_DIR = Path("tmp/wifi/v370-runtime-repair-smoke-result-router")
DEFAULT_SMOKE_MANIFEST = Path("tmp/wifi/v366-runtime-repair-smoke-live-approved/manifest.json")
DEFAULT_CLEANUP_MANIFEST = Path("tmp/wifi/v366-runtime-repair-smoke-cleanup-approved/manifest.json")
PACKET_GLOB = "v369-runtime-repair-smoke-approval-packet*/manifest.json"


@dataclass(frozen=True)
class RouteResult:
    decision: str
    pass_value: bool
    reason: str
    next_step: str
    recommended_commands: list[str]
    remaining_blockers: list[str]


@dataclass
class RouterCaseResult:
    name: str
    status: str
    decision: str
    expected_decision: str
    pass_value: bool
    expected_pass: bool
    command_count: int
    expected_command_count: int
    missing_fragments: list[str]
    detail: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--packet-manifest", type=Path, default=None)
    parser.add_argument("--smoke-manifest", type=Path, default=DEFAULT_SMOKE_MANIFEST)
    parser.add_argument("--cleanup-manifest", type=Path, default=DEFAULT_CLEANUP_MANIFEST)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("route")
    subparsers.add_parser("regression")
    return parser.parse_args()


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"present": False, "path": ""}
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def latest_packet_manifest() -> Path | None:
    root = repo_path(Path("tmp/wifi"))
    if not root.exists():
        return None
    matches = sorted(root.glob(PACKET_GLOB), key=lambda path: path.stat().st_mtime)
    return matches[-1] if matches else None


def manifest_checks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    checks = manifest.get("checks")
    return checks if isinstance(checks, list) else []


def check_named(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    for check in manifest_checks(manifest):
        if check.get("name") == name:
            return check
    return {}


def check_status(manifest: dict[str, Any], name: str) -> str:
    return str(check_named(manifest, name).get("status") or "missing")


def check_detail(manifest: dict[str, Any], name: str) -> str:
    return str(check_named(manifest, name).get("detail") or "")


def packet_ready(packet: dict[str, Any]) -> bool:
    return packet.get("decision") == "runtime-repair-smoke-approval-packet-ready" and bool(packet.get("pass"))


def packet_command(packet: dict[str, Any], key: str) -> str:
    value = packet.get(key)
    return value if isinstance(value, str) else ""


def blockers_from_checks(manifest: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for check in manifest_checks(manifest):
        if check.get("severity") == "blocker" and check.get("status") not in {"pass", "clean"}:
            blockers.append(str(check.get("name")))
    return blockers


def route_result(packet: dict[str, Any], smoke: dict[str, Any], cleanup: dict[str, Any]) -> RouteResult:
    approval_command = packet_command(packet, "approval_command")
    cleanup_command = packet_command(packet, "cleanup_command")

    if not packet_ready(packet):
        return RouteResult(
            "runtime-repair-smoke-router-packet-blocked",
            False,
            f"approval packet missing or not ready: decision={packet.get('decision')} pass={packet.get('pass')}",
            "regenerate V369 approval packet before live smoke",
            [],
            ["v369-approval-packet"],
        )

    if not smoke.get("present"):
        return RouteResult(
            "runtime-repair-smoke-router-awaiting-approval",
            True,
            "approval packet is ready but live smoke manifest is absent",
            "run approved V366 live smoke only after exact operator approval",
            [approval_command] if approval_command else [],
            ["exact-v366-approval-phrase"],
        )

    decision = str(smoke.get("decision") or "missing")
    pass_value = bool(smoke.get("pass"))

    if decision == "runtime-repair-smoke-approval-required":
        return RouteResult(
            "runtime-repair-smoke-router-awaiting-approval",
            True,
            "live smoke run was invoked without exact approval",
            "run approved V366 live smoke only after exact operator approval",
            [approval_command] if approval_command else [],
            ["exact-v366-approval-phrase"],
        )

    if decision == "runtime-repair-smoke-cleanup-approval-required":
        return RouteResult(
            "runtime-repair-smoke-router-awaiting-cleanup-approval",
            True,
            "cleanup was invoked without exact approval",
            "run approved cleanup only if temporary nodes need cleanup",
            [cleanup_command] if cleanup_command else [],
            ["exact-v366-cleanup-approval-phrase"],
        )

    if decision == "runtime-repair-smoke-blocked":
        blockers = blockers_from_checks(smoke) or [str(smoke.get("reason") or "unknown-blocker")]
        commands = [cleanup_command] if "preexisting-temp-nodes" in blockers and cleanup_command else []
        return RouteResult(
            "runtime-repair-smoke-router-blocked",
            False,
            "live smoke blocked: " + ", ".join(blockers),
            "resolve blocker before service-manager/HAL work",
            commands,
            blockers,
        )

    if decision == "runtime-repair-smoke-cleanup-done":
        cleanup_ok = check_status(smoke, "post-node-cleanup") in {"clean", "missing"}
        return RouteResult(
            "runtime-repair-smoke-router-cleanup-done" if cleanup_ok else "runtime-repair-smoke-router-cleanup-review",
            cleanup_ok,
            "cleanup manifest routed",
            "rerun V366 preflight before any next live step",
            [],
            [] if cleanup_ok else ["cleanup-postflight"],
        )

    if decision != "runtime-repair-smoke-pass" or not pass_value:
        return RouteResult(
            "runtime-repair-smoke-router-manual-review",
            False,
            f"unexpected smoke decision={decision} pass={pass_value}",
            "inspect smoke manifest before continuing",
            [cleanup_command] if cleanup_command else [],
            ["manual-review"],
        )

    property_ok = check_status(smoke, "property-lookup-smoke") == "pass"
    cleanup_ok = check_status(smoke, "post-node-cleanup") == "clean"
    service_clean = check_status(smoke, "post-service-process-clean") == "clean"
    wifi_clean = check_status(smoke, "post-wifi-link-clean") == "clean"
    failed = []
    if not property_ok:
        failed.append("property-lookup-smoke")
    if not cleanup_ok:
        failed.append("post-node-cleanup")
    if not service_clean:
        failed.append("post-service-process-clean")
    if not wifi_clean:
        failed.append("post-wifi-link-clean")

    if failed:
        commands = [cleanup_command] if "post-node-cleanup" in failed and cleanup_command else []
        return RouteResult(
            "runtime-repair-smoke-router-postflight-blocked",
            False,
            "postflight failed: " + ", ".join(failed),
            "run approved cleanup if needed, then inspect manifest",
            commands,
            failed,
        )

    return RouteResult(
        "runtime-repair-smoke-router-service-runtime-next-ready",
        True,
        "runtime repair smoke passed and cleaned up",
        "create separate service-manager start-only readiness/approval packet; still no HAL/scan/connect",
        [],
        ["service-manager-start-only-approval-packet"],
    )


def build_manifest(args: argparse.Namespace, packet: dict[str, Any], smoke: dict[str, Any], cleanup: dict[str, Any]) -> dict[str, Any]:
    routed = route_result(packet, smoke, cleanup)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": routed.decision,
        "pass": routed.pass_value,
        "reason": routed.reason,
        "next_step": routed.next_step,
        "host": collect_host_metadata(),
        "packet_manifest": {"path": packet.get("path"), "present": packet.get("present"), "decision": packet.get("decision"), "pass": packet.get("pass")},
        "smoke_manifest": {"path": smoke.get("path"), "present": smoke.get("present"), "decision": smoke.get("decision"), "pass": smoke.get("pass")},
        "cleanup_manifest": {"path": cleanup.get("path"), "present": cleanup.get("present"), "decision": cleanup.get("decision"), "pass": cleanup.get("pass")},
        "recommended_commands": routed.recommended_commands,
        "remaining_blockers": routed.remaining_blockers,
        "required_approval_phrase": APPROVAL_PHRASE,
        "device_commands_executed": False,
        "device_mutations": False,
        "explicitly_not_approved": [
            "service-manager/HAL start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
        ],
    }


def synthetic_packet() -> dict[str, Any]:
    return {
        "present": True,
        "path": "synthetic-packet",
        "decision": "runtime-repair-smoke-approval-packet-ready",
        "pass": True,
        "approval_command": "python3 scripts/revalidation/wifi_runtime_repair_smoke.py --approval-phrase 'approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up' --apply --assume-yes run\n",
        "cleanup_command": "python3 scripts/revalidation/wifi_runtime_repair_smoke.py --approval-phrase 'approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up' --apply --assume-yes cleanup\n",
    }


def check(name: str, status: str, severity: str = "info", detail: str = "") -> dict[str, Any]:
    return {"name": name, "status": status, "severity": severity, "detail": detail, "evidence": [], "next_step": ""}


def synthetic_cases() -> list[tuple[str, dict[str, Any], str, bool, int, tuple[str, ...]]]:
    return [
        ("awaiting-approval", {"present": False, "path": "missing"}, "runtime-repair-smoke-router-awaiting-approval", True, 1, ("exact-v366-approval-phrase",)),
        ("run-refusal", {"present": True, "decision": "runtime-repair-smoke-approval-required", "pass": True}, "runtime-repair-smoke-router-awaiting-approval", True, 1, ("exact-v366-approval-phrase",)),
        (
            "blocked-preexisting",
            {"present": True, "decision": "runtime-repair-smoke-blocked", "pass": False, "checks": [check("preexisting-temp-nodes", "present", "blocker", "present=['/dev/binder']")]},
            "runtime-repair-smoke-router-blocked",
            False,
            1,
            ("preexisting-temp-nodes",),
        ),
        (
            "pass-next-ready",
            {"present": True, "decision": "runtime-repair-smoke-pass", "pass": True, "checks": [check("property-lookup-smoke", "pass"), check("post-node-cleanup", "clean"), check("post-service-process-clean", "clean"), check("post-wifi-link-clean", "clean")]},
            "runtime-repair-smoke-router-service-runtime-next-ready",
            True,
            0,
            ("service-manager-start-only-approval-packet",),
        ),
        (
            "pass-cleanup-failed",
            {"present": True, "decision": "runtime-repair-smoke-pass", "pass": True, "checks": [check("property-lookup-smoke", "pass"), check("post-node-cleanup", "present", "blocker"), check("post-service-process-clean", "clean"), check("post-wifi-link-clean", "clean")]},
            "runtime-repair-smoke-router-postflight-blocked",
            False,
            1,
            ("post-node-cleanup",),
        ),
        ("unexpected", {"present": True, "decision": "unexpected", "pass": False}, "runtime-repair-smoke-router-manual-review", False, 1, ("manual-review",)),
    ]


def run_regression(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    packet = synthetic_packet()
    cleanup = {"present": False, "path": "missing"}
    results: list[RouterCaseResult] = []
    for name, smoke, expected_decision, expected_pass, expected_command_count, expected_blockers in synthetic_cases():
        manifest = build_manifest(args, packet, smoke, cleanup)
        path = store.write_json(f"cases/{name}.json", manifest)
        blockers = tuple(str(item) for item in manifest.get("remaining_blockers", []))
        missing = [item for item in expected_blockers if item not in blockers]
        commands = manifest.get("recommended_commands") if isinstance(manifest.get("recommended_commands"), list) else []
        ok = (
            manifest.get("decision") == expected_decision
            and bool(manifest.get("pass")) is expected_pass
            and len(commands) == expected_command_count
            and not missing
            and not bool(manifest.get("device_commands_executed"))
            and not bool(manifest.get("device_mutations"))
        )
        results.append(RouterCaseResult(
            name=name,
            status="pass" if ok else "blocked",
            decision=str(manifest.get("decision")),
            expected_decision=expected_decision,
            pass_value=bool(manifest.get("pass")),
            expected_pass=expected_pass,
            command_count=len(commands),
            expected_command_count=expected_command_count,
            missing_fragments=missing,
            detail=f"case_manifest={path}",
        ))
    failed = [item.name for item in results if item.status != "pass"]
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "runtime-repair-smoke-router-regression-pass" if not failed else "runtime-repair-smoke-router-regression-failed",
        "pass": not failed,
        "reason": "all router cases passed" if not failed else "failed cases: " + ", ".join(failed),
        "next_step": "V366 live smoke remains blocked by exact approval phrase",
        "host": collect_host_metadata(),
        "results": [asdict(item) for item in results],
        "device_commands_executed": False,
        "device_mutations": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    if "results" in manifest:
        rows = [[item["name"], item["status"], item["decision"], str(item["pass_value"]), str(item["command_count"]), item["detail"]] for item in manifest["results"]]
        body = markdown_table(["case", "status", "decision", "pass", "commands", "detail"], rows)
    else:
        body = markdown_table(
            ["field", "value"],
            [
                ["packet", json.dumps(manifest["packet_manifest"], ensure_ascii=False, sort_keys=True)],
                ["smoke", json.dumps(manifest["smoke_manifest"], ensure_ascii=False, sort_keys=True)],
                ["cleanup", json.dumps(manifest["cleanup_manifest"], ensure_ascii=False, sort_keys=True)],
                ["recommended_commands", "\\n".join(manifest["recommended_commands"]) or "none"],
                ["remaining_blockers", ", ".join(manifest["remaining_blockers"]) or "none"],
            ],
        )
    return "\n".join([
        "# V370 Runtime Repair Smoke Result Router",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Details",
        "",
        body,
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "regression":
        manifest = run_regression(args, store)
    else:
        packet_path = args.packet_manifest if args.packet_manifest is not None else latest_packet_manifest()
        packet = load_json(packet_path)
        smoke = load_json(args.smoke_manifest)
        cleanup = load_json(args.cleanup_manifest)
        manifest = build_manifest(args, packet, smoke, cleanup)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
