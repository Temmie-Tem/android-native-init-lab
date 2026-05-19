#!/usr/bin/env python3
"""Audit private-property Wi-Fi lookup chain gates without touching the device."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v323-private-property-chain-audit")
DEFAULT_V312 = Path("tmp/wifi/v312-private-property-runtime-layout/manifest.json")
DEFAULT_V315 = Path("tmp/wifi/v315-private-property-live-preflight/manifest.json")
DEFAULT_V316 = Path("tmp/wifi/v316-private-property-live-approval/manifest.json")
DEFAULT_V317_PLAN = Path("tmp/wifi/v317-private-property-namespace-proof-current-plan/manifest.json")
DEFAULT_V317_AUDIT = Path("tmp/wifi/v317-private-property-namespace-proof-audit/manifest.json")
DEFAULT_V317_LIVE = Path("tmp/wifi/v317-private-property-namespace-proof/manifest.json")
DEFAULT_V319_REPORT = Path("docs/reports/NATIVE_INIT_V319_SERIAL_TRANSFER_APPEND_2026-05-19.md")
DEFAULT_V321_REPORT = Path("docs/reports/NATIVE_INIT_V321_EXECNS_PROPERTY_LOOKUP_HELPER_2026-05-19.md")
DEFAULT_V322_REPORT = Path("docs/reports/NATIVE_INIT_V322_PRIVATE_PROPERTY_LOOKUP_RUNNER_2026-05-19.md")
DEFAULT_V322_BLOCKED = Path("tmp/wifi/v322-postcommit-run-blocked/manifest.json")
V317_APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"
V320_APPROVAL_PHRASE = "approve v320 private property lookup proof only; no daemon start and no Wi-Fi bring-up"


@dataclass
class Gate:
    name: str
    status: str
    required: bool
    detail: str
    evidence: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v312-manifest", type=Path, default=DEFAULT_V312)
    parser.add_argument("--v315-manifest", type=Path, default=DEFAULT_V315)
    parser.add_argument("--v316-manifest", type=Path, default=DEFAULT_V316)
    parser.add_argument("--v317-plan-manifest", type=Path, default=DEFAULT_V317_PLAN)
    parser.add_argument("--v317-audit-manifest", type=Path, default=DEFAULT_V317_AUDIT)
    parser.add_argument("--v317-live-manifest", type=Path, default=DEFAULT_V317_LIVE)
    parser.add_argument("--v319-report", type=Path, default=DEFAULT_V319_REPORT)
    parser.add_argument("--v321-report", type=Path, default=DEFAULT_V321_REPORT)
    parser.add_argument("--v322-report", type=Path, default=DEFAULT_V322_REPORT)
    parser.add_argument("--v322-blocked-manifest", type=Path, default=DEFAULT_V322_BLOCKED)
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


def text_present(path: Path, needle: str | None = None) -> tuple[bool, str, str]:
    resolved = repo_path(path)
    if not resolved.exists():
        return False, str(resolved), "missing"
    if needle is None:
        return True, str(resolved), "present"
    text = resolved.read_text(encoding="utf-8", errors="replace")
    return needle in text, str(resolved), f"needle={needle!r}"


def gate_from_manifest(name: str,
                       manifest: dict[str, Any],
                       expected_decisions: set[str],
                       *,
                       required: bool = True) -> Gate:
    present = bool(manifest.get("present"))
    decision = str(manifest.get("decision") or "")
    pass_ok = bool(manifest.get("pass"))
    status = "pass" if present and pass_ok and decision in expected_decisions else "blocked"
    if not present:
        detail = "missing"
    else:
        detail = f"decision={decision} pass={pass_ok}"
    return Gate(name, status, required, detail, str(manifest.get("path", "")))


def build_gates(args: argparse.Namespace) -> list[Gate]:
    v312 = load_json(args.v312_manifest)
    v315 = load_json(args.v315_manifest)
    v316 = load_json(args.v316_manifest)
    v317_plan = load_json(args.v317_plan_manifest)
    v317_audit = load_json(args.v317_audit_manifest)
    v317_live = load_json(args.v317_live_manifest)
    v322_blocked = load_json(args.v322_blocked_manifest)
    v319_ok, v319_path, v319_detail = text_present(args.v319_report, "A90 Linux init 0.9.61 (v319)")
    v321_ok, v321_path, v321_detail = text_present(args.v321_report, "execns-property-lookup-helper-static-pass")
    v322_ok, v322_path, v322_detail = text_present(args.v322_report, "private-property-lookup-runner-integrated-blocked-v317")
    v322_blocked_safe = (
        bool(v322_blocked.get("present")) and
        v322_blocked.get("decision") == "private-property-lookup-blocked-v317-missing" and
        not bool(v322_blocked.get("device_commands_executed")) and
        not bool(v322_blocked.get("device_mutations"))
    )
    if not v322_blocked.get("present"):
        v322_blocked_detail = "missing"
    else:
        v322_blocked_detail = (
            f"decision={v322_blocked.get('decision')} "
            f"device_commands_executed={v322_blocked.get('device_commands_executed')} "
            f"device_mutations={v322_blocked.get('device_mutations')}"
        )

    return [
        gate_from_manifest("v312-property-layout", v312, {"private-property-layout-dryrun-ready"}),
        gate_from_manifest("v315-live-preflight", v315, {"private-property-live-preflight-ready"}),
        gate_from_manifest("v316-live-approval-packet", v316, {"private-property-live-approval-ready"}),
        gate_from_manifest("v317-plan", v317_plan, {"private-property-namespace-proof-plan-ready"}),
        gate_from_manifest("v317-audit", v317_audit, {"private-property-namespace-proof-audit-pass"}),
        gate_from_manifest("v317-live-pass", v317_live, {"private-property-namespace-proof-pass"}),
        Gate("v319-native-transfer-support", "pass" if v319_ok else "blocked", True, v319_detail, v319_path),
        Gate("v321-helper-support", "pass" if v321_ok else "blocked", True, v321_detail, v321_path),
        Gate("v322-runner-integration", "pass" if v322_ok else "blocked", True, v322_detail, v322_path),
        Gate(
            "v322-current-run-blocked-safely",
            "pass" if v322_blocked_safe else "blocked",
            False,
            v322_blocked_detail,
            str(v322_blocked.get("path", "")),
        ),
    ]


def decide(gates: list[Gate]) -> tuple[str, bool, bool, str, str]:
    missing_required = [gate.name for gate in gates if gate.required and gate.status != "pass"]
    live_gate = next((gate for gate in gates if gate.name == "v317-live-pass"), None)
    if missing_required == ["v317-live-pass"] or (live_gate is not None and live_gate.status != "pass" and all(g.status == "pass" for g in gates if g.required and g.name != "v317-live-pass")):
        return (
            "private-property-chain-blocked-v317-missing",
            True,
            False,
            "all local/static prerequisites pass, but v317 live namespace proof PASS evidence is absent",
            f"provide exact v317 approval phrase if you want to run the live proof: {V317_APPROVAL_PHRASE}",
        )
    if missing_required:
        return (
            "private-property-chain-evidence-incomplete",
            True,
            False,
            "missing or failed required gates: " + ", ".join(missing_required),
            "repair prerequisite evidence before any live private property lookup",
        )
    return (
        "private-property-chain-ready-for-v320-approval",
        True,
        True,
        "all prerequisite gates pass; v320 still requires exact live approval before helper execution",
        f"review and provide exact v320 phrase only if proceeding: {V320_APPROVAL_PHRASE}",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    gates = build_gates(args)
    decision, audit_pass, chain_ready, reason, next_step = decide(gates)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "audit_pass": audit_pass,
        "chain_ready": chain_ready,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "gates": [asdict(gate) for gate in gates],
        "approval_phrases": {
            "v317": V317_APPROVAL_PHRASE,
            "v320": V320_APPROVAL_PHRASE,
        },
        "device_commands_executed": False,
        "device_mutations": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [item["name"], item["status"], str(item["required"]), item["detail"], item["evidence"]]
        for item in manifest["gates"]
    ]
    return "\n".join([
        "# v323 Private Property Chain Gate Audit",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- audit_pass: `{manifest['audit_pass']}`",
        f"- chain_ready: `{manifest['chain_ready']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Gates",
        "",
        markdown_table(["name", "status", "required", "detail", "evidence"], rows),
        "",
        "## Approval Phrases",
        "",
        f"- v317: `{manifest['approval_phrases']['v317']}`",
        f"- v320: `{manifest['approval_phrases']['v320']}`",
        "",
    ])


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    store = EvidenceStore(repo_path(args.out_dir))
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"audit_pass: {manifest['audit_pass']}")
    print(f"chain_ready: {manifest['chain_ready']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["audit_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
