#!/usr/bin/env python3
"""Host-only safety audit for v317 private property namespace proof manifests."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v317-private-property-namespace-proof-audit")
DEFAULT_PLAN = Path("tmp/wifi/v317-private-property-namespace-proof-plan/manifest.json")
DEFAULT_RUN_REFUSE = Path("tmp/wifi/v317-private-property-namespace-proof-refuse/manifest.json")
DEFAULT_CLEANUP_REFUSE = Path("tmp/wifi/v317-private-property-namespace-proof-cleanup-refuse/manifest.json")
REMOTE_WORKDIR = "/mnt/sdext/a90/private-property-v317"
APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"


@dataclass
class AuditCheck:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--plan-manifest", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--run-refuse-manifest", type=Path, default=DEFAULT_RUN_REFUSE)
    parser.add_argument("--cleanup-refuse-manifest", type=Path, default=DEFAULT_CLEANUP_REFUSE)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    subparsers.add_parser("selftest")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def decision_check(name: str, manifest: dict[str, Any], expected_decision: str, expected_pass: bool) -> AuditCheck:
    ok = (
        manifest.get("present")
        and manifest.get("decision") == expected_decision
        and bool(manifest.get("pass")) is expected_pass
    )
    return AuditCheck(
        name,
        "pass" if ok else "blocked",
        "blocker",
        f"decision={manifest.get('decision')} pass={manifest.get('pass')}",
        [str(manifest.get("path", ""))],
    )


def mutation_check(name: str, manifest: dict[str, Any]) -> AuditCheck:
    commands = manifest.get("commands", [])
    no_mutation = bool(manifest.get("present")) and not bool(manifest.get("device_mutations")) and commands == []
    return AuditCheck(
        name,
        "pass" if no_mutation else "blocked",
        "blocker",
        f"device_mutations={manifest.get('device_mutations')} commands={len(commands) if isinstance(commands, list) else 'invalid'}",
        [str(manifest.get("path", ""))],
    )


def transfer_check(manifest: dict[str, Any]) -> AuditCheck:
    transfer = manifest.get("transfer_estimate", {})
    ok = (
        isinstance(transfer, dict)
        and transfer.get("status") == "pass"
        and int(transfer.get("files") or 0) == 5
        and int(transfer.get("bytes") or 0) == 524988
        and 0 < int(transfer.get("estimated_commands") or 0) < 5000
        and int(transfer.get("max_script_chars") or 0) < 4096
    )
    return AuditCheck(
        "transfer-estimate",
        "pass" if ok else "blocked",
        "blocker",
        json.dumps(transfer, ensure_ascii=False, sort_keys=True),
        [str(manifest.get("path", ""))],
    )


def path_scope_check(manifest: dict[str, Any]) -> AuditCheck:
    files = manifest.get("files", [])
    bad: list[str] = []
    if not isinstance(files, list) or not files:
        bad.append("missing-files")
    else:
        for item in files:
            if not isinstance(item, dict):
                bad.append("invalid-item")
                continue
            remote_path = str(item.get("remote_path") or "")
            if not remote_path.startswith(REMOTE_WORKDIR + "/") or ".." in Path(remote_path).parts:
                bad.append(remote_path or "<empty>")
    return AuditCheck(
        "remote-path-scope",
        "pass" if not bad else "blocked",
        "blocker",
        f"remote_workdir={REMOTE_WORKDIR} bad={len(bad)}",
        bad[:8],
    )


def blocked_actions_check(manifest: dict[str, Any]) -> AuditCheck:
    actions = "\n".join(str(item) for item in manifest.get("blocked_actions", []))
    required = [
        "global /dev/__properties__ replacement",
        "global bind mount over /dev/__properties__",
        "global /dev/socket/property_service creation",
        "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        "NCM/tcpctl start for transfer",
    ]
    missing = [item for item in required if item not in actions]
    return AuditCheck(
        "blocked-actions",
        "pass" if not missing else "blocked",
        "blocker",
        "all required blocked actions present" if not missing else "missing: " + ", ".join(missing),
        required,
    )


def approval_phrase_check(manifest: dict[str, Any]) -> AuditCheck:
    phrase = str(manifest.get("operator_approval_phrase") or "")
    ok = phrase == APPROVAL_PHRASE
    return AuditCheck(
        "approval-phrase",
        "pass" if ok else "blocked",
        "blocker",
        "exact phrase matches" if ok else f"unexpected phrase={phrase!r}",
        [APPROVAL_PHRASE],
    )


def decide(checks: list[AuditCheck]) -> tuple[str, bool, str]:
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return "private-property-namespace-proof-audit-blocked", False, "blocked checks: " + ", ".join(blockers)
    return "private-property-namespace-proof-audit-pass", True, "pre-live v317 manifests are fail-closed and scope-bounded"


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[item["name"], item["status"], item["severity"], item["detail"]] for item in manifest["checks"]]
    return "\n".join([
        "# v317 Private Property Namespace Proof Audit",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail"], rows),
        "",
    ])


def selftest_result(name: str, expected_pass: bool, checks: list[AuditCheck]) -> dict[str, Any]:
    decision, pass_ok, reason = decide(checks)
    return {
        "name": name,
        "expected_pass": expected_pass,
        "actual_pass": pass_ok,
        "ok": pass_ok is expected_pass,
        "decision": decision,
        "reason": reason,
        "checks": [asdict(check) for check in checks],
    }


def run_selftest(args: argparse.Namespace) -> int:
    plan = load_json(args.plan_manifest)
    run_refuse = load_json(args.run_refuse_manifest)
    cleanup_refuse = load_json(args.cleanup_refuse_manifest)
    base_checks = [
        decision_check("plan-decision", plan, "private-property-namespace-proof-plan-ready", True),
        decision_check("run-refusal-decision", run_refuse, "private-property-namespace-proof-approval-required", False),
        decision_check("cleanup-refusal-decision", cleanup_refuse, "private-property-namespace-proof-approval-required", False),
        mutation_check("plan-no-mutation", plan),
        mutation_check("run-refusal-no-mutation", run_refuse),
        mutation_check("cleanup-refusal-no-mutation", cleanup_refuse),
        transfer_check(plan),
        path_scope_check(plan),
        blocked_actions_check(plan),
        approval_phrase_check(plan),
    ]
    bad_path = json.loads(json.dumps(plan))
    bad_path["files"][0]["remote_path"] = "/tmp/outside"
    bad_actions = json.loads(json.dumps(plan))
    bad_actions["blocked_actions"] = []
    bad_transfer = json.loads(json.dumps(plan))
    bad_transfer["transfer_estimate"]["estimated_commands"] = 999999
    bad_mutation = json.loads(json.dumps(plan))
    bad_mutation["device_mutations"] = True
    bad_mutation["commands"] = [{"name": "unexpected"}]
    results = [
        selftest_result("base-pass", True, base_checks),
        selftest_result("bad-path-blocked", False, [path_scope_check(bad_path)]),
        selftest_result("bad-actions-blocked", False, [blocked_actions_check(bad_actions)]),
        selftest_result("bad-transfer-blocked", False, [transfer_check(bad_transfer)]),
        selftest_result("bad-mutation-blocked", False, [mutation_check("bad-mutation", bad_mutation)]),
    ]
    pass_ok = all(item["ok"] for item in results)
    manifest = {
        "generated_at": now_iso(),
        "decision": "private-property-namespace-proof-audit-selftest-pass" if pass_ok else "private-property-namespace-proof-audit-selftest-failed",
        "pass": pass_ok,
        "reason": "audit selftest cases behaved as expected" if pass_ok else "one or more audit selftest cases failed",
        "host": collect_host_metadata(),
        "results": results,
        "device_commands_executed": False,
    }
    store = EvidenceStore(repo_path(args.out_dir))
    store.write_json("selftest-manifest.json", manifest)
    store.write_text(
        "selftest-summary.md",
        "\n".join([
            "# v317 Audit Selftest",
            "",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            "",
            "| case | expected | actual | ok | decision |",
            "| --- | --- | --- | --- | --- |",
            *[
                f"| `{item['name']}` | `{item['expected_pass']}` | `{item['actual_pass']}` | `{item['ok']}` | `{item['decision']}` |"
                for item in results
            ],
            "",
        ]),
    )
    print(f"decision: {manifest['decision']}")
    print(f"pass: {pass_ok}")
    print(f"evidence: {store.run_dir}")
    return 0 if pass_ok else 1


def main() -> int:
    args = parse_args()
    if args.command == "selftest":
        return run_selftest(args)
    plan = load_json(args.plan_manifest)
    run_refuse = load_json(args.run_refuse_manifest)
    cleanup_refuse = load_json(args.cleanup_refuse_manifest)
    checks = [
        decision_check("plan-decision", plan, "private-property-namespace-proof-plan-ready", True),
        decision_check("run-refusal-decision", run_refuse, "private-property-namespace-proof-approval-required", False),
        decision_check("cleanup-refusal-decision", cleanup_refuse, "private-property-namespace-proof-approval-required", False),
        mutation_check("plan-no-mutation", plan),
        mutation_check("run-refusal-no-mutation", run_refuse),
        mutation_check("cleanup-refusal-no-mutation", cleanup_refuse),
        transfer_check(plan),
        path_scope_check(plan),
        blocked_actions_check(plan),
        approval_phrase_check(plan),
    ]
    decision, pass_ok, reason = decide(checks)
    manifest = {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "inputs": {
            "plan": {"path": plan.get("path"), "present": bool(plan.get("present")), "decision": plan.get("decision"), "pass": plan.get("pass")},
            "run_refuse": {"path": run_refuse.get("path"), "present": bool(run_refuse.get("present")), "decision": run_refuse.get("decision"), "pass": run_refuse.get("pass")},
            "cleanup_refuse": {"path": cleanup_refuse.get("path"), "present": bool(cleanup_refuse.get("present")), "decision": cleanup_refuse.get("decision"), "pass": cleanup_refuse.get("pass")},
        },
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
    }
    store = EvidenceStore(repo_path(args.out_dir))
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"evidence: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
