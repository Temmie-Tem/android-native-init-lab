#!/usr/bin/env python3
"""Refresh host-only V317 gate evidence in dependency order.

This tool never runs the V317 live proof. It regenerates host-only/read-only
manifests used by the V317 handoff chain and can optionally run the no-device
`preflight` subcommand with the exact approval phrase as data.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v344-v317-gate-refresh")
V317_APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"


@dataclass(frozen=True)
class RefreshStep:
    name: str
    argv: list[str]
    manifest_path: Path
    expected_rc: int
    expected_decision: str
    expected_pass: bool | None


@dataclass
class RefreshResult:
    name: str
    status: str
    rc: int
    expected_rc: int
    decision: str
    expected_decision: str
    pass_value: bool | None
    expected_pass: bool | None
    device_commands_executed: bool | None
    device_mutations: bool | None
    stdout_path: str
    manifest_path: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--run-approved-preflight",
        action="store_true",
        help="also run the V317 runner's no-device preflight path with the exact approval phrase",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("refresh")
    return parser.parse_args()


def py_script(path: str) -> str:
    return str(repo_path(Path(path)))


def base_steps() -> list[RefreshStep]:
    return [
        RefreshStep(
            "v317-plan",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_private_property_namespace_proof.py"),
                "--out-dir",
                "tmp/wifi/v317-private-property-namespace-proof-current-plan",
                "plan",
            ],
            Path("tmp/wifi/v317-private-property-namespace-proof-current-plan/manifest.json"),
            0,
            "private-property-namespace-proof-plan-ready",
            True,
        ),
        RefreshStep(
            "v326-chain-audit",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_private_property_chain_audit.py"),
                "--out-dir",
                "tmp/wifi/v326-private-property-chain-audit",
                "audit",
            ],
            Path("tmp/wifi/v326-private-property-chain-audit/manifest.json"),
            0,
            "private-property-chain-blocked-v317-missing",
            True,
        ),
        RefreshStep(
            "v327-approval-refresh",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_private_property_approval_refresh.py"),
                "--out-dir",
                "tmp/wifi/v327-private-property-approval-refresh",
                "run",
            ],
            Path("tmp/wifi/v327-private-property-approval-refresh/manifest.json"),
            0,
            "private-property-approval-refresh-ready",
            True,
        ),
        RefreshStep(
            "v328-runner-plan",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_private_property_namespace_proof.py"),
                "--out-dir",
                "tmp/wifi/v328-v317-runner-plan",
                "plan",
            ],
            Path("tmp/wifi/v328-v317-runner-plan/manifest.json"),
            0,
            "private-property-namespace-proof-plan-ready",
            True,
        ),
        RefreshStep(
            "v328-runner-refuse",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_private_property_namespace_proof.py"),
                "--out-dir",
                "tmp/wifi/v328-v317-runner-refuse",
                "run",
            ],
            Path("tmp/wifi/v328-v317-runner-refuse/manifest.json"),
            1,
            "private-property-namespace-proof-approval-required",
            False,
        ),
        RefreshStep(
            "v335-approval-gate-regression",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_approval_gate_regression.py"),
                "--out-dir",
                "tmp/wifi/v335-approval-gate-regression",
                "run",
            ],
            Path("tmp/wifi/v335-approval-gate-regression/manifest.json"),
            0,
            "wifi-approval-gate-regression-pass",
            True,
        ),
        RefreshStep(
            "v336-prelive-gate",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_v317_prelive_gate_audit.py"),
                "--out-dir",
                "tmp/wifi/v336-v317-prelive-gate-audit",
                "audit",
            ],
            Path("tmp/wifi/v336-v317-prelive-gate-audit/manifest.json"),
            0,
            "v317-prelive-gate-awaiting-approval",
            True,
        ),
        RefreshStep(
            "v331-readiness-packet",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_v317_live_readiness_packet.py"),
                "--out-dir",
                "tmp/wifi/v331-v317-live-readiness-packet",
                "packet",
            ],
            Path("tmp/wifi/v331-v317-live-readiness-packet/manifest.json"),
            0,
            "v317-live-readiness-packet-ready",
            True,
        ),
        RefreshStep(
            "v339-live-surface-linter",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_v317_live_surface_linter.py"),
                "--out-dir",
                "tmp/wifi/v339-v317-live-surface-linter",
                "lint",
            ],
            Path("tmp/wifi/v339-v317-live-surface-linter/manifest.json"),
            0,
            "v317-live-surface-lint-pass",
            True,
        ),
        RefreshStep(
            "v340-final-handoff-packet",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_v317_handoff_packet.py"),
                "--out-dir",
                "tmp/wifi/v340-v317-final-handoff-packet",
                "packet",
            ],
            Path("tmp/wifi/v340-v317-final-handoff-packet/manifest.json"),
            0,
            "v317-handoff-awaiting-approval",
            True,
        ),
        RefreshStep(
            "v333-post-v317-router",
            [
                sys.executable,
                py_script("scripts/revalidation/wifi_post_v317_router.py"),
                "--out-dir",
                "tmp/wifi/v333-post-v317-router",
                "route",
            ],
            Path("tmp/wifi/v333-post-v317-router/manifest.json"),
            0,
            "post-v317-router-awaiting-v317",
            True,
        ),
    ]


def approved_preflight_step() -> RefreshStep:
    return RefreshStep(
        "v342-approved-preflight",
        [
            sys.executable,
            py_script("scripts/revalidation/wifi_private_property_namespace_proof.py"),
            "--out-dir",
            "tmp/wifi/v342-v317-approved-preflight",
            "--prelive-gate-manifest",
            "tmp/wifi/v336-v317-prelive-gate-audit/manifest.json",
            "--approval-phrase",
            V317_APPROVAL_PHRASE,
            "--allow-device-mutation",
            "--assume-yes",
            "preflight",
        ],
        Path("tmp/wifi/v342-v317-approved-preflight/manifest.json"),
        0,
        "private-property-namespace-proof-preflight-ready",
        True,
    )


def command_arg(argv: list[str], name: str) -> str | None:
    for index, item in enumerate(argv[:-1]):
        if item == name:
            return argv[index + 1]
    return None


def generated_handoff_preflight_step() -> RefreshStep:
    handoff_manifest = load_manifest(Path("tmp/wifi/v340-v317-final-handoff-packet/manifest.json"))
    command = str(handoff_manifest.get("preflight_command") or "")
    if not command:
        return RefreshStep(
            "v340-generated-preflight",
            [sys.executable, "-c", "raise SystemExit('missing V340 preflight command')"],
            Path("tmp/wifi/v317-private-property-namespace-proof-preflight/manifest.json"),
            0,
            "private-property-namespace-proof-preflight-ready",
            True,
        )
    argv = shlex.split(command)
    out_dir = command_arg(argv, "--out-dir") or "tmp/wifi/v317-private-property-namespace-proof-preflight"
    return RefreshStep(
        "v340-generated-preflight",
        argv,
        Path(out_dir) / "manifest.json",
        0,
        "private-property-namespace-proof-preflight-ready",
        True,
    )


def load_manifest(path: Path) -> dict[str, Any]:
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


def no_device_execution(manifest: dict[str, Any]) -> bool:
    device_commands = manifest.get("device_commands_executed")
    if device_commands is None and "commands" in manifest:
        device_commands = bool(manifest.get("commands"))
    return not bool(device_commands) and not bool(manifest.get("device_mutations"))


def step_status(step: RefreshStep, rc: int, manifest: dict[str, Any]) -> str:
    ok = (
        rc == step.expected_rc
        and bool(manifest.get("present"))
        and manifest.get("decision") == step.expected_decision
        and (step.expected_pass is None or pass_value(manifest) is step.expected_pass)
        and no_device_execution(manifest)
    )
    return "pass" if ok else "blocked"


def run_step(step: RefreshStep, transcript_dir: Path) -> RefreshResult:
    transcript_path = transcript_dir / f"{step.name}.txt"
    result = subprocess.run(
        step.argv,
        cwd=repo_path(Path(".")),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
    )
    transcript_path.write_text(result.stdout, encoding="utf-8")
    manifest = load_manifest(step.manifest_path)
    status = step_status(step, result.returncode, manifest)
    return RefreshResult(
        name=step.name,
        status=status,
        rc=result.returncode,
        expected_rc=step.expected_rc,
        decision=str(manifest.get("decision") or "missing"),
        expected_decision=step.expected_decision,
        pass_value=pass_value(manifest),
        expected_pass=step.expected_pass,
        device_commands_executed=manifest.get("device_commands_executed"),
        device_mutations=manifest.get("device_mutations"),
        stdout_path=str(transcript_path),
        manifest_path=str(repo_path(step.manifest_path)),
    )


def decide(results: list[RefreshResult]) -> tuple[str, bool, str, str, list[str]]:
    blocked = [item.name for item in results if item.status != "pass"]
    if blocked:
        return (
            "v317-gate-refresh-blocked",
            False,
            "blocked refresh steps: " + ", ".join(blocked),
            "repair blocked step evidence before requesting V317 approval",
            blocked,
        )
    return (
        "v317-gate-refresh-ready",
        True,
        "all host-only V317 gate evidence refreshed without device commands",
        "V317 live proof still requires the exact operator approval phrase",
        ["exact-v317-approval-phrase"],
    )


def build_manifest(args: argparse.Namespace, results: list[RefreshResult]) -> dict[str, Any]:
    decision, pass_ok, reason, next_step, blockers = decide(results)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "steps": [asdict(item) for item in results],
        "remaining_blockers": blockers,
        "approved_preflight_requested": bool(args.run_approved_preflight),
        "required_approval_phrase": V317_APPROVAL_PHRASE,
        "live_execution_approved": False,
        "device_commands_executed": False,
        "device_mutations": False,
        "notes": [
            "This refresh is host-only and does not run V317 live proof.",
            "The approved preflight option executes both the direct runner preflight and the generated V340 preflight command, and expects commands=[].",
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
            str(item["device_commands_executed"]),
            str(item["device_mutations"]),
        ]
        for item in manifest["steps"]
    ]
    return "\n".join([
        "# v344 V317 Gate Refresh",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- approved_preflight_requested: `{manifest['approved_preflight_requested']}`",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Remaining Blockers",
        "",
        "\n".join(f"- `{item}`" for item in manifest["remaining_blockers"]) or "- none",
        "",
        "## Steps",
        "",
        markdown_table(
            ["step", "status", "rc", "decision", "pass", "device_commands", "device_mutations"],
            rows,
        ),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    transcript_dir = store.run_dir / "transcripts"
    transcript_dir.mkdir(mode=0o700, exist_ok=True)
    results = [run_step(step, transcript_dir) for step in base_steps()]
    if args.run_approved_preflight:
        results.append(run_step(approved_preflight_step(), transcript_dir))
        results.append(run_step(generated_handoff_preflight_step(), transcript_dir))
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
