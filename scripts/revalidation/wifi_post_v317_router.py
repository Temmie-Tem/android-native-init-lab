#!/usr/bin/env python3
"""Route the next Wi-Fi step from the V317 live proof result."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v333-post-v317-router")
DEFAULT_V317 = Path("tmp/wifi/v317-private-property-namespace-proof/manifest.json")
DEFAULT_V331 = Path("tmp/wifi/v331-v317-live-readiness-packet/manifest.json")
DEFAULT_V332 = Path("tmp/wifi/v332-current-readonly-live-preflight/manifest.json")
V317_APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"
V320_APPROVAL_PHRASE = "approve v320 private property lookup proof only; no daemon start and no Wi-Fi bring-up"


@dataclass
class RouteCheck:
    name: str
    status: str
    detail: str
    evidence: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v317-manifest", type=Path, default=DEFAULT_V317)
    parser.add_argument("--v331-manifest", type=Path, default=DEFAULT_V331)
    parser.add_argument("--v332-manifest", type=Path, default=DEFAULT_V332)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("route")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def shell_command(argv: list[str]) -> str:
    return " ".join(shlex.quote(item) for item in argv)


def v317_live_command() -> str:
    return shell_command([
        "python3",
        "scripts/revalidation/wifi_private_property_namespace_proof.py",
        "--out-dir",
        "tmp/wifi/v317-private-property-namespace-proof",
        "--host",
        "127.0.0.1",
        "--port",
        "54321",
        "--timeout",
        "20.0",
        "--approval-phrase",
        V317_APPROVAL_PHRASE,
        "--allow-device-mutation",
        "--assume-yes",
        "run",
    ])


def v317_cleanup_command() -> str:
    return shell_command([
        "python3",
        "scripts/revalidation/wifi_private_property_namespace_proof.py",
        "--out-dir",
        "tmp/wifi/v317-private-property-namespace-proof-cleanup",
        "--host",
        "127.0.0.1",
        "--port",
        "54321",
        "--timeout",
        "20.0",
        "--approval-phrase",
        V317_APPROVAL_PHRASE,
        "--allow-device-mutation",
        "--assume-yes",
        "cleanup",
    ])


def v320_plan_command() -> str:
    return shell_command([
        "python3",
        "scripts/revalidation/wifi_private_property_lookup_proof.py",
        "--out-dir",
        "tmp/wifi/v320-private-property-lookup-proof-plan-after-v317",
        "plan",
    ])


def v320_run_command() -> str:
    return shell_command([
        "python3",
        "scripts/revalidation/wifi_private_property_lookup_proof.py",
        "--out-dir",
        "tmp/wifi/v320-private-property-lookup-proof-live",
        "--approval-phrase",
        V320_APPROVAL_PHRASE,
        "--allow-device-mutation",
        "--assume-yes",
        "run",
    ])


def build_checks(v331: dict[str, Any], v332: dict[str, Any], v317: dict[str, Any]) -> list[RouteCheck]:
    v331_ok = (
        v331.get("present")
        and v331.get("decision") == "v317-live-readiness-packet-ready"
        and bool(v331.get("pass"))
        and not bool(v331.get("live_execution_approved"))
        and not bool(v331.get("device_commands_executed"))
        and not bool(v331.get("device_mutations"))
    )
    v332_ok = (
        v332.get("present")
        and v332.get("decision") == "private-property-live-preflight-ready"
        and bool(v332.get("pass"))
        and not bool(v332.get("device_mutations"))
    )
    v317_present = bool(v317.get("present"))
    return [
        RouteCheck(
            "v331-readiness-packet",
            "pass" if v331_ok else "blocked",
            f"decision={v331.get('decision')} pass={v331.get('pass')} live_execution_approved={v331.get('live_execution_approved')}",
            str(v331.get("path", "")),
        ),
        RouteCheck(
            "v332-readonly-preflight",
            "pass" if v332_ok else "blocked",
            f"decision={v332.get('decision')} pass={v332.get('pass')} device_mutations={v332.get('device_mutations')}",
            str(v332.get("path", "")),
        ),
        RouteCheck(
            "v317-live-result",
            "present" if v317_present else "missing",
            f"decision={v317.get('decision')} pass={v317.get('pass')} present={v317_present}",
            str(v317.get("path", "")),
        ),
    ]


def decide(v317: dict[str, Any], checks: list[RouteCheck]) -> tuple[str, bool, str, str, list[str]]:
    blockers = [check.name for check in checks if check.name != "v317-live-result" and check.status != "pass"]
    if blockers:
        return (
            "post-v317-router-prereq-blocked",
            False,
            "readiness prerequisites failed: " + ", ".join(blockers),
            "refresh readiness/preflight evidence before V317",
            [],
        )
    if not v317.get("present"):
        return (
            "post-v317-router-awaiting-v317",
            True,
            "V317 live proof evidence is absent",
            "run V317 only after exact approval phrase",
            [v317_live_command()],
        )
    decision = str(v317.get("decision") or "")
    pass_ok = bool(v317.get("pass"))
    live_error = str(v317.get("live_error") or "")
    if decision == "private-property-namespace-proof-pass" and pass_ok:
        return (
            "post-v317-router-v320-ready",
            True,
            "V317 live proof passed; V320 property lookup planning may proceed",
            "run V320 plan first, then V320 live lookup only after its exact approval phrase",
            [v320_plan_command(), v320_run_command()],
        )
    if decision == "private-property-namespace-proof-cleaned" and pass_ok:
        return (
            "post-v317-router-cleaned",
            True,
            "V317 workspace cleanup evidence exists",
            "rerun V317 proof after exact approval if proceeding",
            [v317_live_command()],
        )
    if decision in {"private-property-namespace-proof-failed", "private-property-namespace-proof-cleanup-failed"} or live_error:
        return (
            "post-v317-router-cleanup-required",
            False,
            f"V317 failed or cleanup state is uncertain: decision={decision} live_error={live_error}",
            "run scoped V317 cleanup after exact V317 approval, then rerun read-only preflight",
            [v317_cleanup_command()],
        )
    return (
        "post-v317-router-manual-review",
        False,
        f"unexpected V317 decision={decision} pass={pass_ok}",
        "inspect V317 manifest before any V320 lookup",
        [],
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v317 = load_json(args.v317_manifest)
    v331 = load_json(args.v331_manifest)
    v332 = load_json(args.v332_manifest)
    checks = build_checks(v331, v332, v317)
    decision, pass_ok, reason, next_step, commands = decide(v317, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "checks": [asdict(check) for check in checks],
        "recommended_commands": commands,
        "approval_phrases": {
            "v317": V317_APPROVAL_PHRASE,
            "v320": V320_APPROVAL_PHRASE,
        },
        "device_commands_executed": False,
        "device_mutations": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[item["name"], item["status"], item["detail"], item["evidence"]] for item in manifest["checks"]]
    lines = [
        "# v333 Post-V317 Router",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "evidence"], rows),
        "",
        "## Recommended Commands",
        "",
    ]
    if manifest["recommended_commands"]:
        lines.extend(["```bash", *manifest["recommended_commands"], "```", ""])
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Approval Phrases",
        "",
        f"- v317: `{manifest['approval_phrases']['v317']}`",
        f"- v320: `{manifest['approval_phrases']['v320']}`",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    store = EvidenceStore(repo_path(args.out_dir))
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
