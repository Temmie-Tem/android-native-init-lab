#!/usr/bin/env python3
"""Audit Wi-Fi host-only evidence freshness against the current git head."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v330-evidence-freshness-audit")


@dataclass
class EvidenceCheck:
    name: str
    path: str
    present: bool
    decision: str
    status: str
    detail: str


EXPECTED = (
    ("v325-helper-preflight", Path("tmp/wifi/v325-execns-helper-deploy-preflight/manifest.json"), {"execns-helper-deploy-preflight-ready"}, True),
    ("v326-chain-audit", Path("tmp/wifi/v326-private-property-chain-audit/manifest.json"), {"private-property-chain-blocked-v317-missing"}, True),
    ("v327-approval-refresh", Path("tmp/wifi/v327-private-property-approval-refresh/manifest.json"), {"private-property-approval-refresh-ready"}, True),
    ("v328-runner-plan", Path("tmp/wifi/v328-v317-runner-plan/manifest.json"), {"private-property-namespace-proof-plan-ready"}, True),
    ("v328-runner-refusal", Path("tmp/wifi/v328-v317-runner-refuse/manifest.json"), {"private-property-namespace-proof-approval-required"}, False),
    ("v329-readiness-dashboard", Path("tmp/wifi/v329-wifi-readiness-dashboard/manifest.json"), {"wifi-readiness-dashboard-ready-blocked-by-v317"}, True),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("audit")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def pass_value(manifest: dict[str, Any]) -> bool | None:
    if "pass" in manifest:
        return bool(manifest.get("pass"))
    if "audit_pass" in manifest:
        return bool(manifest.get("audit_pass"))
    return None


def build_checks(current_head: str) -> list[EvidenceCheck]:
    checks: list[EvidenceCheck] = []
    for name, path, expected_decisions, expected_pass in EXPECTED:
        manifest = load_json(path)
        host = manifest.get("host") if isinstance(manifest.get("host"), dict) else {}
        if not host and isinstance(manifest.get("host_metadata"), dict):
            host = manifest["host_metadata"]
        decision = str(manifest.get("decision") or "")
        actual_pass = pass_value(manifest)
        head = str(host.get("git_head") or "")
        dirty = host.get("git_dirty")
        present = bool(manifest.get("present"))
        ok = (
            present
            and decision in expected_decisions
            and actual_pass is expected_pass
            and head == current_head
            and dirty is False
        )
        if not present:
            detail = "missing"
        else:
            detail = (
                f"decision={decision} pass={actual_pass} "
                f"git_head={head} current_head={current_head} git_dirty={dirty}"
            )
        checks.append(EvidenceCheck(
            name=name,
            path=str(manifest.get("path", repo_path(path))),
            present=present,
            decision=decision or "missing",
            status="pass" if ok else "blocked",
            detail=detail,
        ))
    return checks


def decide(checks: list[EvidenceCheck]) -> tuple[str, bool, str, str]:
    blocked = [check.name for check in checks if check.status != "pass"]
    if blocked:
        return (
            "wifi-evidence-freshness-blocked",
            False,
            "stale or missing evidence: " + ", ".join(blocked),
            "rerun the affected host-only evidence steps on a clean tree",
        )
    return (
        "wifi-evidence-freshness-clean",
        True,
        "all V325-V329 host-only evidence was regenerated on the current clean git head",
        "V317 live proof remains the next approval-gated step",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    host = collect_host_metadata()
    current_head = str(host.get("git_head") or "")
    checks = build_checks(current_head)
    decision, pass_ok, reason, next_step = decide(checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": host,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[item["name"], item["status"], item["decision"], item["detail"], item["path"]] for item in manifest["checks"]]
    return "\n".join([
        "# v330 Wi-Fi Evidence Freshness Audit",
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
        markdown_table(["name", "status", "decision", "detail", "path"], rows),
        "",
    ])


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
