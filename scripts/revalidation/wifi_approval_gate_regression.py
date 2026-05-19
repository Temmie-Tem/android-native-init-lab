#!/usr/bin/env python3
"""Host-only regression checks for Wi-Fi approval gates."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v335-approval-gate-regression")
V317_APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"
V320_APPROVAL_PHRASE = "approve v320 private property lookup proof only; no daemon start and no Wi-Fi bring-up"


@dataclass
class RegressionCase:
    name: str
    argv: list[str]
    expected_decision: str
    expected_pass: bool
    expect_no_device_command: bool
    expect_no_device_mutation: bool
    expected_rc: int


@dataclass
class RegressionResult:
    name: str
    status: str
    rc: int
    expected_rc: int
    decision: str
    expected_decision: str
    pass_value: bool | None
    expected_pass: bool
    device_commands_executed: bool | None
    device_mutations: bool | None
    manifest_path: str
    stdout_path: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def case_out(base: Path, name: str) -> Path:
    return base / name


def cases(base_out: Path) -> list[RegressionCase]:
    return [
        RegressionCase(
            "v317-run-no-approval",
            [
                "python3",
                "scripts/revalidation/wifi_private_property_namespace_proof.py",
                "--out-dir",
                str(case_out(base_out, "v317-run-no-approval")),
                "run",
            ],
            "private-property-namespace-proof-approval-required",
            False,
            True,
            True,
            1,
        ),
        RegressionCase(
            "v317-run-phrase-only",
            [
                "python3",
                "scripts/revalidation/wifi_private_property_namespace_proof.py",
                "--out-dir",
                str(case_out(base_out, "v317-run-phrase-only")),
                "--approval-phrase",
                V317_APPROVAL_PHRASE,
                "run",
            ],
            "private-property-namespace-proof-approval-required",
            False,
            True,
            True,
            1,
        ),
        RegressionCase(
            "v317-run-flags-only",
            [
                "python3",
                "scripts/revalidation/wifi_private_property_namespace_proof.py",
                "--out-dir",
                str(case_out(base_out, "v317-run-flags-only")),
                "--allow-device-mutation",
                "--assume-yes",
                "run",
            ],
            "private-property-namespace-proof-approval-required",
            False,
            True,
            True,
            1,
        ),
        RegressionCase(
            "v317-cleanup-no-approval",
            [
                "python3",
                "scripts/revalidation/wifi_private_property_namespace_proof.py",
                "--out-dir",
                str(case_out(base_out, "v317-cleanup-no-approval")),
                "cleanup",
            ],
            "private-property-namespace-proof-approval-required",
            False,
            True,
            True,
            1,
        ),
        RegressionCase(
            "v320-run-no-approval",
            [
                "python3",
                "scripts/revalidation/wifi_private_property_lookup_proof.py",
                "--out-dir",
                str(case_out(base_out, "v320-run-no-approval")),
                "run",
            ],
            "private-property-lookup-blocked-v317-missing",
            False,
            True,
            True,
            1,
        ),
        RegressionCase(
            "v320-run-full-approval-still-blocked-v317",
            [
                "python3",
                "scripts/revalidation/wifi_private_property_lookup_proof.py",
                "--out-dir",
                str(case_out(base_out, "v320-run-full-approval-still-blocked-v317")),
                "--approval-phrase",
                V320_APPROVAL_PHRASE,
                "--allow-device-mutation",
                "--assume-yes",
                "run",
            ],
            "private-property-lookup-blocked-v317-missing",
            False,
            True,
            True,
            1,
        ),
    ]


def is_dangerous_v317_full_approval(case: RegressionCase) -> bool:
    argv = case.argv
    return (
        "scripts/revalidation/wifi_private_property_namespace_proof.py" in argv
        and "run" in argv
        and "--allow-device-mutation" in argv
        and "--assume-yes" in argv
        and "--approval-phrase" in argv
        and argv[argv.index("--approval-phrase") + 1] == V317_APPROVAL_PHRASE
    )


def assert_safe_case(case: RegressionCase) -> None:
    if is_dangerous_v317_full_approval(case):
        raise RuntimeError(
            f"{case.name}: refusing dangerous V317 full-approval live case"
        )


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_case(store: EvidenceStore, case: RegressionCase) -> RegressionResult:
    assert_safe_case(case)
    result = subprocess.run(
        case.argv,
        cwd=repo_path(Path(".")),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
    )
    stdout_path = store.write_text(f"{case.name}.txt", result.stdout)
    manifest_path = repo_path(Path(case.argv[case.argv.index("--out-dir") + 1]) / "manifest.json")
    manifest = load_manifest(manifest_path)
    decision = str(manifest.get("decision") or "")
    pass_value = manifest.get("pass")
    if pass_value is not None:
        pass_value = bool(pass_value)
    device_commands = manifest.get("device_commands_executed")
    device_mutations = manifest.get("device_mutations")
    if device_commands is None and "commands" in manifest:
        device_commands = bool(manifest.get("commands"))
    ok = (
        result.returncode == case.expected_rc
        and decision == case.expected_decision
        and pass_value is case.expected_pass
        and (not case.expect_no_device_command or device_commands is False)
        and (not case.expect_no_device_mutation or device_mutations is False)
    )
    return RegressionResult(
        name=case.name,
        status="pass" if ok else "fail",
        rc=result.returncode,
        expected_rc=case.expected_rc,
        decision=decision,
        expected_decision=case.expected_decision,
        pass_value=pass_value,
        expected_pass=case.expected_pass,
        device_commands_executed=device_commands,
        device_mutations=device_mutations,
        manifest_path=str(manifest_path),
        stdout_path=str(stdout_path),
    )


def decide(results: list[RegressionResult]) -> tuple[str, bool, str, str]:
    failed = [item.name for item in results if item.status != "pass"]
    if failed:
        return (
            "wifi-approval-gate-regression-failed",
            False,
            "failed cases: " + ", ".join(failed),
            "fix gate behavior before any live Wi-Fi/private-property proof",
        )
    return (
        "wifi-approval-gate-regression-pass",
        True,
        "all partial/blocked approval cases refused without device commands",
        "V317 exact approval remains required for the next live proof",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    base_out = repo_path(args.out_dir / "cases")
    results = [run_case(store, case) for case in cases(base_out)]
    decision, pass_ok, reason, next_step = decide(results)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "results": [asdict(item) for item in results],
        "dangerous_case_not_run": "v317 exact phrase + --allow-device-mutation + --assume-yes",
        "device_commands_executed": any(item.device_commands_executed is True for item in results),
        "device_mutations": any(item.device_mutations is True for item in results),
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [
            item["name"],
            item["status"],
            str(item["rc"]),
            item["decision"],
            str(item["device_commands_executed"]),
            str(item["device_mutations"]),
        ]
        for item in manifest["results"]
    ]
    return "\n".join([
        "# v335 Wi-Fi Approval Gate Regression",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- dangerous_case_not_run: `{manifest['dangerous_case_not_run']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Results",
        "",
        markdown_table(["case", "status", "rc", "decision", "device_commands", "device_mutations"], rows),
        "",
    ])


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
