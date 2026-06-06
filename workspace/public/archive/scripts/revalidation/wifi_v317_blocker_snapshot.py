#!/usr/bin/env python3
"""Host-only V317 live blocker snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v359-v317-blocker-snapshot")
DEFAULT_V357_OUT_DIR = Path("tmp/wifi/v357-v317-preapproval-audit")
DEFAULT_V350_MANIFEST = Path("tmp/wifi/v350-v317-operator-checklist/manifest.json")
APPROVAL_BLOCKER = "exact-v317-approval-phrase"
APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"
EXECUTOR_SCRIPT = "scripts/revalidation/wifi_v317_live_executor.py"


@dataclass
class SnapshotCheck:
    name: str
    status: str
    detail: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v357-out-dir", type=Path, default=DEFAULT_V357_OUT_DIR)
    parser.add_argument("--v350-manifest", type=Path, default=DEFAULT_V350_MANIFEST)
    parser.add_argument("--timeout", type=int, default=600)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("snapshot")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def run_v357(args: argparse.Namespace, store: EvidenceStore) -> tuple[int, str]:
    command = [
        sys.executable,
        str(repo_path(Path("scripts/revalidation/wifi_v317_preapproval_audit.py"))),
        "--out-dir",
        str(args.v357_out_dir),
        "check",
    ]
    result = subprocess.run(
        command,
        cwd=repo_path(Path(".")),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=args.timeout,
    )
    store.write_text("v357-audit.txt", result.stdout)
    return result.returncode, result.stdout


def host_head(payload: dict[str, Any]) -> str:
    host = payload.get("host") if isinstance(payload.get("host"), dict) else {}
    return str(host.get("git_head") or "")


def host_dirty(payload: dict[str, Any]) -> bool | None:
    host = payload.get("host") if isinstance(payload.get("host"), dict) else {}
    value = host.get("git_dirty")
    return bool(value) if value is not None else None


def blockers(payload: dict[str, Any]) -> list[str]:
    value = payload.get("remaining_blockers")
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def check(name: str, ok: bool, detail: str) -> SnapshotCheck:
    return SnapshotCheck(name, "pass" if ok else "blocked", detail)


def build_checks(v357_rc: int, v357: dict[str, Any], v350: dict[str, Any], current_head: str) -> list[SnapshotCheck]:
    return [
        check(
            "v357-audit-rc",
            v357_rc == 0,
            f"rc={v357_rc}",
        ),
        check(
            "v357-awaiting-approval",
            v357.get("decision") == "v317-preapproval-audit-awaiting-approval" and bool(v357.get("pass")),
            f"decision={v357.get('decision')} pass={v357.get('pass')}",
        ),
        check(
            "v357-current-clean-head",
            host_head(v357) == current_head and host_dirty(v357) is False,
            f"head={host_head(v357)} current={current_head} dirty={host_dirty(v357)}",
        ),
        check(
            "v357-approval-blocker-only",
            blockers(v357) == [APPROVAL_BLOCKER],
            f"remaining_blockers={blockers(v357)}",
        ),
        check(
            "v357-no-device-action",
            bool(v357.get("device_commands_executed")) is False and bool(v357.get("device_mutations")) is False,
            f"device_commands_executed={v357.get('device_commands_executed')} device_mutations={v357.get('device_mutations')}",
        ),
        check(
            "v350-checklist-ready",
            v350.get("decision") == "v317-operator-checklist-ready" and bool(v350.get("pass")),
            f"decision={v350.get('decision')} pass={v350.get('pass')}",
        ),
        check(
            "v350-executor-run-command",
            EXECUTOR_SCRIPT in str(v350.get("executor_run_command") or ""),
            str(v350.get("executor_run_command") or ""),
        ),
        check(
            "v350-exact-approval-phrase",
            APPROVAL_PHRASE in str(v350.get("executor_run_command") or ""),
            "approval phrase present in executor run command",
        ),
    ]


def decide(checks: list[SnapshotCheck]) -> tuple[str, bool, str, str, list[str]]:
    blocked = [item.name for item in checks if item.status != "pass"]
    if blocked:
        return (
            "v317-live-blocker-snapshot-blocked",
            False,
            "blocked snapshot checks: " + ", ".join(blocked),
            "repair V357/V350 evidence before live approval handoff",
            blocked,
        )
    return (
        "v317-live-blocked-awaiting-exact-approval",
        True,
        "V317 live proof is ready to request approval and blocked only by the exact phrase",
        "wait for exact V317 approval phrase before running V351 executor run",
        [APPROVAL_BLOCKER],
    )


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[item["name"], item["status"], item["detail"]] for item in manifest["checks"]]
    return "\n".join([
        "# v359 V317 Live Blocker Snapshot",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Remaining Blockers",
        "",
        "\n".join(f"- `{item}`" for item in manifest["remaining_blockers"]) or "- none",
        "",
        "## Approval Phrase",
        "",
        f"`{manifest['approval_phrase']}`",
        "",
        "## Preferred Live Command",
        "",
        "```bash",
        manifest["executor_run_command"],
        "```",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail"], rows),
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v357_rc, _ = run_v357(args, store)
    v357 = load_json(args.v357_out_dir / "manifest.json")
    v350 = load_json(args.v350_manifest)
    host = collect_host_metadata()
    current_head = str(host.get("git_head") or "")
    checks = build_checks(v357_rc, v357, v350, current_head)
    decision, pass_ok, reason, next_step, remaining = decide(checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": host,
        "checks": [asdict(item) for item in checks],
        "v357_manifest": str(repo_path(args.v357_out_dir / "manifest.json")),
        "v350_manifest": str(repo_path(args.v350_manifest)),
        "approval_phrase": APPROVAL_PHRASE,
        "executor_plan_command": str(v350.get("executor_plan_command") or ""),
        "executor_run_command": str(v350.get("executor_run_command") or ""),
        "executor_cleanup_command": str(v350.get("executor_cleanup_command") or ""),
        "remaining_blockers": remaining,
        "live_execution_approved": False,
        "device_commands_executed": False,
        "device_mutations": False,
        "notes": [
            "This snapshot executes only the host-only V357 audit.",
            "It does not run V351 executor run or cleanup.",
            "It does not start Wi-Fi daemon, scan, connect, or bring links up.",
        ],
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
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
