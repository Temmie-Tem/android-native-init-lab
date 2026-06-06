#!/usr/bin/env python3
"""Host-only V317 pre-live gate audit.

This does not execute the V317 live proof. It consolidates the current
host-only/read-only Wi-Fi gate evidence and checks whether older evidence is
stale in a way that affects the V317 private-property live boundary.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v336-v317-prelive-gate-audit")
V317_APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"


@dataclass(frozen=True)
class GateSpec:
    name: str
    path: Path
    expected_decisions: set[str]
    expected_pass: bool | None
    critical_paths: tuple[str, ...]
    notes: str
    require_device_command_false: bool = True


@dataclass
class GateResult:
    name: str
    status: str
    decision: str
    pass_value: bool | None
    evidence_head: str
    current_head: str
    freshness: str
    affected_paths: list[str]
    device_commands_executed: bool | None
    device_mutations: bool | None
    path: str
    notes: str


GATES = (
    GateSpec(
        "v325-helper-preflight",
        Path("tmp/wifi/v325-execns-helper-deploy-preflight/manifest.json"),
        {"execns-helper-deploy-preflight-ready"},
        True,
        (
            "scripts/revalidation/wifi_execns_helper_deploy_preflight.py",
            "stage3/linux_init/helpers/a90_android_execns_probe.c",
        ),
        "fresh helper build/deploy preflight",
    ),
    GateSpec(
        "v326-chain-audit",
        Path("tmp/wifi/v326-private-property-chain-audit/manifest.json"),
        {"private-property-chain-blocked-v317-missing"},
        True,
        (
            "scripts/revalidation/wifi_private_property_chain_audit.py",
            "scripts/revalidation/wifi_private_property_namespace_proof.py",
            "scripts/revalidation/wifi_private_property_lookup_proof.py",
        ),
        "private-property chain blocks V320 until V317 PASS",
    ),
    GateSpec(
        "v327-approval-refresh",
        Path("tmp/wifi/v327-private-property-approval-refresh/manifest.json"),
        {"private-property-approval-refresh-ready"},
        True,
        (
            "scripts/revalidation/wifi_private_property_approval_refresh.py",
            "scripts/revalidation/wifi_private_property_namespace_proof.py",
        ),
        "current V317 approval packet refresh",
    ),
    GateSpec(
        "v328-runner-plan",
        Path("tmp/wifi/v328-v317-runner-plan/manifest.json"),
        {"private-property-namespace-proof-plan-ready"},
        True,
        ("scripts/revalidation/wifi_private_property_namespace_proof.py",),
        "V317 runner plan without live execution",
    ),
    GateSpec(
        "v328-runner-refusal",
        Path("tmp/wifi/v328-v317-runner-refuse/manifest.json"),
        {"private-property-namespace-proof-approval-required"},
        False,
        ("scripts/revalidation/wifi_private_property_namespace_proof.py",),
        "V317 runner refuses without exact approval",
    ),
    GateSpec(
        "v329-readiness-dashboard",
        Path("tmp/wifi/v329-wifi-readiness-dashboard/manifest.json"),
        {"wifi-readiness-dashboard-ready-blocked-by-v317"},
        True,
        ("scripts/revalidation/wifi_readiness_dashboard.py",),
        "readiness aggregation still blocked by V317",
    ),
    GateSpec(
        "v332-readonly-live-preflight",
        Path("tmp/wifi/v332-current-readonly-live-preflight/manifest.json"),
        {"private-property-live-preflight-ready"},
        True,
        (
            "scripts/revalidation/wifi_private_property_live_preflight.py",
            "scripts/revalidation/a90ctl.py",
        ),
        "read-only current-device preflight",
        False,
    ),
    GateSpec(
        "v334-freshness-audit",
        Path("tmp/wifi/v334-evidence-freshness-audit/manifest.json"),
        {"wifi-evidence-freshness-clean"},
        True,
        ("scripts/revalidation/wifi_evidence_freshness_audit.py",),
        "V325-V333 freshness audit",
    ),
    GateSpec(
        "v335-approval-gate-regression",
        Path("tmp/wifi/v335-approval-gate-regression/manifest.json"),
        {"wifi-approval-gate-regression-pass"},
        True,
        (
            "scripts/revalidation/wifi_approval_gate_regression.py",
            "scripts/revalidation/wifi_private_property_namespace_proof.py",
            "scripts/revalidation/wifi_private_property_lookup_proof.py",
        ),
        "partial approval combinations fail closed",
    ),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("audit")
    return parser.parse_args()


def run_git(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_path(Path(".")),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
    )
    return result.returncode, result.stdout


def changed_paths_since(old_head: str, current_head: str) -> list[str]:
    if not old_head or old_head == "unknown" or old_head == current_head:
        return []
    rc, output = run_git(["diff", "--name-only", f"{old_head}..{current_head}"])
    if rc != 0:
        return [f"git-diff-failed: {output.strip()}"]
    return [line.strip() for line in output.splitlines() if line.strip()]


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


def manifest_head(manifest: dict[str, Any]) -> str:
    host = manifest.get("host") if isinstance(manifest.get("host"), dict) else {}
    if not host and isinstance(manifest.get("host_metadata"), dict):
        host = manifest["host_metadata"]
    return str(host.get("git_head") or "")


def manifest_dirty(manifest: dict[str, Any]) -> bool | None:
    host = manifest.get("host") if isinstance(manifest.get("host"), dict) else {}
    if not host and isinstance(manifest.get("host_metadata"), dict):
        host = manifest["host_metadata"]
    value = host.get("git_dirty")
    return bool(value) if value is not None else None


def is_affected(path: str, critical_paths: tuple[str, ...]) -> bool:
    return any(path == critical or path.startswith(f"{critical}/") for critical in critical_paths)


def evaluate_gate(spec: GateSpec, current_head: str) -> GateResult:
    manifest = load_json(spec.path)
    decision = str(manifest.get("decision") or "")
    actual_pass = pass_value(manifest)
    evidence_head = manifest_head(manifest)
    dirty = manifest_dirty(manifest)
    changed = changed_paths_since(evidence_head, current_head)
    affected = [path for path in changed if is_affected(path, spec.critical_paths)]
    device_commands = manifest.get("device_commands_executed")
    device_mutations = manifest.get("device_mutations")
    if device_commands is None and "commands" in manifest:
        device_commands = bool(manifest.get("commands"))
    freshness = "current" if evidence_head == current_head else "stale-unaffected"
    if affected:
        freshness = "stale-affected"
    present = bool(manifest.get("present"))
    ok = (
        present
        and decision in spec.expected_decisions
        and (spec.expected_pass is None or actual_pass is spec.expected_pass)
        and dirty is False
        and freshness != "stale-affected"
        and (not spec.require_device_command_false or device_commands in {False, None})
        and device_mutations is False
    )
    if not present:
        status = "missing"
        freshness = "missing"
    elif not ok:
        status = "blocked"
    else:
        status = "pass"
    return GateResult(
        name=spec.name,
        status=status,
        decision=decision or "missing",
        pass_value=actual_pass,
        evidence_head=evidence_head or "missing",
        current_head=current_head,
        freshness=freshness,
        affected_paths=affected,
        device_commands_executed=device_commands,
        device_mutations=device_mutations,
        path=str(manifest.get("path", repo_path(spec.path))),
        notes=spec.notes,
    )


def decide(results: list[GateResult]) -> tuple[str, bool, str, str, list[str]]:
    blocked = [item.name for item in results if item.status != "pass"]
    if blocked:
        return (
            "v317-prelive-gate-blocked",
            False,
            "blocked gates: " + ", ".join(blocked),
            "refresh or repair blocked evidence before requesting live approval",
            blocked,
        )
    return (
        "v317-prelive-gate-awaiting-approval",
        True,
        "all host-only/read-only gates pass; live proof remains blocked only by exact operator approval",
        "run V317 only after the exact approval phrase is provided",
        ["exact-v317-approval-phrase"],
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    host = collect_host_metadata()
    current_head = str(host.get("git_head") or "")
    results = [evaluate_gate(spec, current_head) for spec in GATES]
    decision, pass_ok, reason, next_step, blockers = decide(results)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": host,
        "gates": [asdict(item) for item in results],
        "remaining_blockers": blockers,
        "required_approval_phrase": V317_APPROVAL_PHRASE,
        "live_execution_approved": False,
        "device_commands_executed": False,
        "device_mutations": False,
        "notes": [
            "This audit is host-only and does not run V317.",
            "stale-unaffected evidence is accepted only when changed files do not touch that gate's critical paths.",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [
            item["name"],
            item["status"],
            item["decision"],
            str(item["pass_value"]),
            item["freshness"],
            ",".join(item["affected_paths"]) or "-",
        ]
        for item in manifest["gates"]
    ]
    return "\n".join([
        "# v336 V317 Pre-live Gate Audit",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Remaining Blockers",
        "",
        "\n".join(f"- `{item}`" for item in manifest["remaining_blockers"]) or "- none",
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
        "## Gates",
        "",
        markdown_table(["gate", "status", "decision", "pass", "freshness", "affected_paths"], rows),
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
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
