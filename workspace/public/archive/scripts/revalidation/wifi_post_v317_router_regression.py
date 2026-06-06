#!/usr/bin/env python3
"""Host-only regression tests for the post-V317 Wi-Fi router."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v345-post-v317-router-regression")
ROUTER_SCRIPT = Path("scripts/revalidation/wifi_post_v317_router.py")


@dataclass(frozen=True)
class RouterCase:
    name: str
    v331: dict[str, Any] | None
    v332: dict[str, Any] | None
    v317: dict[str, Any] | None
    expected_rc: int
    expected_decision: str
    expected_pass: bool
    expected_command_count: int
    required_command_fragments: tuple[str, ...]


@dataclass
class RouterCaseResult:
    name: str
    status: str
    rc: int
    expected_rc: int
    decision: str
    expected_decision: str
    pass_value: bool | None
    expected_pass: bool
    command_count: int
    expected_command_count: int
    missing_fragments: list[str]
    device_commands_executed: bool | None
    device_mutations: bool | None
    stdout_path: str
    manifest_path: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def ok_v331() -> dict[str, Any]:
    return {
        "decision": "v317-live-readiness-packet-ready",
        "pass": True,
        "live_execution_approved": False,
        "device_commands_executed": False,
        "device_mutations": False,
    }


def ok_v332() -> dict[str, Any]:
    return {
        "decision": "private-property-live-preflight-ready",
        "pass": True,
        "device_commands_executed": False,
        "device_mutations": False,
    }


def cases() -> list[RouterCase]:
    return [
        RouterCase(
            "awaiting-v317",
            ok_v331(),
            ok_v332(),
            None,
            0,
            "post-v317-router-awaiting-v317",
            True,
            1,
            ("wifi_private_property_namespace_proof.py", " run"),
        ),
        RouterCase(
            "v317-pass-v320-ready",
            ok_v331(),
            ok_v332(),
            {"decision": "private-property-namespace-proof-pass", "pass": True},
            0,
            "post-v317-router-v320-ready",
            True,
            2,
            ("wifi_private_property_lookup_proof.py", " plan", " run"),
        ),
        RouterCase(
            "v317-cleaned-rerun-ready",
            ok_v331(),
            ok_v332(),
            {"decision": "private-property-namespace-proof-cleaned", "pass": True},
            0,
            "post-v317-router-cleaned",
            True,
            1,
            ("wifi_private_property_namespace_proof.py", " run"),
        ),
        RouterCase(
            "v317-failed-cleanup-required",
            ok_v331(),
            ok_v332(),
            {"decision": "private-property-namespace-proof-failed", "pass": False},
            1,
            "post-v317-router-cleanup-required",
            False,
            1,
            ("wifi_private_property_namespace_proof.py", " cleanup"),
        ),
        RouterCase(
            "v317-live-error-cleanup-required",
            ok_v331(),
            ok_v332(),
            {"decision": "private-property-namespace-proof-manual-review", "pass": False, "live_error": "boom"},
            1,
            "post-v317-router-cleanup-required",
            False,
            1,
            ("wifi_private_property_namespace_proof.py", " cleanup"),
        ),
        RouterCase(
            "v317-unexpected-manual-review",
            ok_v331(),
            ok_v332(),
            {"decision": "unexpected", "pass": False},
            1,
            "post-v317-router-manual-review",
            False,
            0,
            (),
        ),
        RouterCase(
            "blocked-readiness-prereq",
            {**ok_v331(), "decision": "wrong", "pass": False},
            ok_v332(),
            None,
            1,
            "post-v317-router-prereq-blocked",
            False,
            0,
            (),
        ),
        RouterCase(
            "blocked-readonly-preflight-prereq",
            ok_v331(),
            {**ok_v332(), "pass": False},
            None,
            1,
            "post-v317-router-prereq-blocked",
            False,
            0,
            (),
        ),
    ]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_case(case: RouterCase, case_dir: Path) -> RouterCaseResult:
    input_dir = case_dir / "inputs"
    output_dir = case_dir / "router-output"
    stdout_path = case_dir / "router-stdout.txt"
    v331_path = input_dir / "v331.json"
    v332_path = input_dir / "v332.json"
    v317_path = input_dir / "v317.json"
    if case.v331 is not None:
        write_json(v331_path, case.v331)
    if case.v332 is not None:
        write_json(v332_path, case.v332)
    if case.v317 is not None:
        write_json(v317_path, case.v317)

    argv = [
        sys.executable,
        str(repo_path(ROUTER_SCRIPT)),
        "--out-dir",
        str(output_dir),
        "--v331-manifest",
        str(v331_path),
        "--v332-manifest",
        str(v332_path),
        "--v317-manifest",
        str(v317_path),
        "route",
    ]
    result = subprocess.run(
        argv,
        cwd=repo_path(Path(".")),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
    )
    stdout_path.write_text(result.stdout, encoding="utf-8")
    manifest_path = output_dir / "manifest.json"
    manifest = load_json(manifest_path)
    commands = manifest.get("recommended_commands") or []
    joined_commands = "\n".join(str(item) for item in commands)
    missing_fragments = [fragment for fragment in case.required_command_fragments if fragment not in joined_commands]
    ok = (
        result.returncode == case.expected_rc
        and manifest.get("decision") == case.expected_decision
        and bool(manifest.get("pass")) is case.expected_pass
        and len(commands) == case.expected_command_count
        and not missing_fragments
        and not bool(manifest.get("device_commands_executed"))
        and not bool(manifest.get("device_mutations"))
    )
    return RouterCaseResult(
        name=case.name,
        status="pass" if ok else "blocked",
        rc=result.returncode,
        expected_rc=case.expected_rc,
        decision=str(manifest.get("decision") or "missing"),
        expected_decision=case.expected_decision,
        pass_value=manifest.get("pass"),
        expected_pass=case.expected_pass,
        command_count=len(commands),
        expected_command_count=case.expected_command_count,
        missing_fragments=missing_fragments,
        device_commands_executed=manifest.get("device_commands_executed"),
        device_mutations=manifest.get("device_mutations"),
        stdout_path=str(stdout_path),
        manifest_path=str(manifest_path),
    )


def decide(results: list[RouterCaseResult]) -> tuple[str, bool, str, str, list[str]]:
    blocked = [item.name for item in results if item.status != "pass"]
    if blocked:
        return (
            "post-v317-router-regression-blocked",
            False,
            "blocked cases: " + ", ".join(blocked),
            "fix router behavior before running V317 live proof",
            blocked,
        )
    return (
        "post-v317-router-regression-pass",
        True,
        "all synthetic post-V317 router branches behave as expected",
        "V317 live proof remains blocked by exact approval phrase",
        ["exact-v317-approval-phrase"],
    )


def build_manifest(args: argparse.Namespace, results: list[RouterCaseResult]) -> dict[str, Any]:
    decision, pass_ok, reason, next_step, blockers = decide(results)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "cases": [asdict(item) for item in results],
        "remaining_blockers": blockers,
        "device_commands_executed": False,
        "device_mutations": False,
        "notes": [
            "Synthetic manifests are used; no device or bridge access is performed.",
            "Recommended commands are inspected as strings but never executed.",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [
            item["name"],
            item["status"],
            str(item["rc"]),
            item["decision"],
            str(item["pass_value"]),
            f"{item['command_count']}/{item['expected_command_count']}",
            ",".join(item["missing_fragments"]) or "-",
        ]
        for item in manifest["cases"]
    ]
    return "\n".join([
        "# v345 Post-V317 Router Regression",
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
        "## Cases",
        "",
        markdown_table(["case", "status", "rc", "decision", "pass", "commands", "missing_fragments"], rows),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    case_root = store.run_dir / "cases"
    case_root.mkdir(mode=0o700, exist_ok=True)
    results = [run_case(case, case_root / case.name) for case in cases()]
    manifest = build_manifest(args, results)
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
