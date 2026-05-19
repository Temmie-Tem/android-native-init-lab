#!/usr/bin/env python3
"""Build the final host-only V317 live handoff packet."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v340-v317-final-handoff-packet")
DEFAULT_V331 = Path("tmp/wifi/v331-v317-live-readiness-packet/manifest.json")
DEFAULT_V336 = Path("tmp/wifi/v336-v317-prelive-gate-audit/manifest.json")
DEFAULT_V339 = Path("tmp/wifi/v339-v317-live-surface-linter/manifest.json")
PREFLIGHT_OUT_DIR = "tmp/wifi/v317-private-property-namespace-proof-preflight"

APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"


@dataclass(frozen=True)
class InputSpec:
    name: str
    path: Path
    expected_decision: str
    expected_pass: bool
    critical_paths: tuple[str, ...]
    require_current_head: bool = False


@dataclass
class HandoffCheck:
    name: str
    status: str
    detail: str
    evidence: str


INPUTS = (
    InputSpec(
        "v331-readiness-packet",
        DEFAULT_V331,
        "v317-live-readiness-packet-ready",
        True,
        (
            "scripts/revalidation/wifi_v317_live_readiness_packet.py",
            "scripts/revalidation/wifi_private_property_namespace_proof.py",
            "scripts/revalidation/wifi_v317_prelive_gate_audit.py",
        ),
    ),
    InputSpec(
        "v336-prelive-gate",
        DEFAULT_V336,
        "v317-prelive-gate-awaiting-approval",
        True,
        (
            "scripts/revalidation/wifi_v317_prelive_gate_audit.py",
            "scripts/revalidation/wifi_private_property_namespace_proof.py",
        ),
        True,
    ),
    InputSpec(
        "v339-live-surface-linter",
        DEFAULT_V339,
        "v317-live-surface-lint-pass",
        True,
        (
            "scripts/revalidation/wifi_v317_live_surface_linter.py",
            "scripts/revalidation/wifi_private_property_namespace_proof.py",
            "scripts/revalidation/wifi_v317_live_readiness_packet.py",
            "scripts/revalidation/wifi_v317_prelive_gate_audit.py",
        ),
    ),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v331-manifest", type=Path, default=DEFAULT_V331)
    parser.add_argument("--v336-manifest", type=Path, default=DEFAULT_V336)
    parser.add_argument("--v339-manifest", type=Path, default=DEFAULT_V339)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("packet")
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


def manifest_head(manifest: dict[str, Any]) -> str:
    host = manifest.get("host") if isinstance(manifest.get("host"), dict) else {}
    return str(host.get("git_head") or "")


def manifest_dirty(manifest: dict[str, Any]) -> bool | None:
    host = manifest.get("host") if isinstance(manifest.get("host"), dict) else {}
    value = host.get("git_dirty")
    return bool(value) if value is not None else None


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


def is_affected(path: str, critical_paths: tuple[str, ...]) -> bool:
    return any(path == critical or path.startswith(f"{critical}/") for critical in critical_paths)


def input_spec_with_args(args: argparse.Namespace) -> tuple[InputSpec, ...]:
    return (
        InputSpec(INPUTS[0].name, args.v331_manifest, INPUTS[0].expected_decision, INPUTS[0].expected_pass, INPUTS[0].critical_paths),
        InputSpec(INPUTS[1].name, args.v336_manifest, INPUTS[1].expected_decision, INPUTS[1].expected_pass, INPUTS[1].critical_paths, INPUTS[1].require_current_head),
        InputSpec(INPUTS[2].name, args.v339_manifest, INPUTS[2].expected_decision, INPUTS[2].expected_pass, INPUTS[2].critical_paths),
    )


def check_input(spec: InputSpec, manifest: dict[str, Any], current_head: str) -> HandoffCheck:
    head = manifest_head(manifest)
    changed = changed_paths_since(head, current_head)
    affected = [path for path in changed if is_affected(path, spec.critical_paths)]
    freshness = "current" if head == current_head else "stale-unaffected"
    if affected:
        freshness = "stale-affected"
    ok = (
        bool(manifest.get("present"))
        and manifest.get("decision") == spec.expected_decision
        and pass_value(manifest) is spec.expected_pass
        and manifest_dirty(manifest) is False
        and (not spec.require_current_head or head == current_head)
        and freshness != "stale-affected"
        and not bool(manifest.get("device_commands_executed"))
        and not bool(manifest.get("device_mutations"))
        and not bool(manifest.get("live_execution_approved"))
    )
    return HandoffCheck(
        spec.name,
        "pass" if ok else "blocked",
        (
            f"decision={manifest.get('decision')} pass={pass_value(manifest)} "
            f"head={head} current_head={current_head} freshness={freshness} "
            f"require_current_head={spec.require_current_head} "
            f"affected={affected}"
        ),
        str(manifest.get("path", repo_path(spec.path))),
    )


def contract_checks(v331: dict[str, Any], v336: dict[str, Any], v339: dict[str, Any]) -> list[HandoffCheck]:
    live_command = str(v331.get("live_command") or "")
    cleanup_command = str(v331.get("cleanup_command") or "")
    preflight_command = command_variant(live_command, "preflight", PREFLIGHT_OUT_DIR)
    live_out_dir = command_arg(live_command, "--out-dir")
    preflight_out_dir = command_arg(preflight_command, "--out-dir")
    return [
        HandoffCheck(
            "approval-phrase",
            "pass" if v331.get("approval_phrase") == APPROVAL_PHRASE and v336.get("required_approval_phrase") == APPROVAL_PHRASE else "blocked",
            "approval phrase matches V317 exact phrase",
            str(v331.get("path", "")),
        ),
        HandoffCheck(
            "live-command-contract",
            "pass" if APPROVAL_PHRASE in live_command and "--prelive-gate-manifest" in live_command else "blocked",
            "live command contains exact phrase and prelive gate manifest argument",
            str(v331.get("path", "")),
        ),
        HandoffCheck(
            "cleanup-command-contract",
            "pass" if APPROVAL_PHRASE in cleanup_command and "--prelive-gate-manifest" in cleanup_command else "blocked",
            "cleanup command contains exact phrase and prelive gate manifest argument",
            str(v331.get("path", "")),
        ),
        HandoffCheck(
            "preflight-command-contract",
            "pass" if APPROVAL_PHRASE in preflight_command and "--prelive-gate-manifest" in preflight_command and preflight_command.endswith(" preflight") and preflight_out_dir == PREFLIGHT_OUT_DIR else "blocked",
            f"preflight command contains exact phrase, prelive gate manifest argument, preflight subcommand, and out_dir={preflight_out_dir}",
            str(v331.get("path", "")),
        ),
        HandoffCheck(
            "preflight-output-isolated",
            "pass" if live_out_dir and preflight_out_dir and live_out_dir != preflight_out_dir else "blocked",
            f"live_out_dir={live_out_dir} preflight_out_dir={preflight_out_dir}",
            str(v331.get("path", "")),
        ),
        HandoffCheck(
            "remaining-blocker",
            "pass" if v336.get("remaining_blockers") == ["exact-v317-approval-phrase"] else "blocked",
            f"remaining_blockers={v336.get('remaining_blockers')}",
            str(v336.get("path", "")),
        ),
        HandoffCheck(
            "surface-lint-contract",
            "pass" if all(item.get("status") == "pass" for item in v339.get("device_calls", [])) else "blocked",
            f"device_call_count={len(v339.get('device_calls', []))}",
            str(v339.get("path", "")),
        ),
    ]


def command_arg(command: str, name: str) -> str | None:
    argv = shlex.split(command)
    for index, item in enumerate(argv[:-1]):
        if item == name:
            return argv[index + 1]
    return None


def command_variant(command: str, subcommand: str, out_dir: str | None = None) -> str:
    argv = shlex.split(command)
    if out_dir is not None:
        for index, item in enumerate(argv[:-1]):
            if item == "--out-dir":
                argv[index + 1] = out_dir
                break
        else:
            argv[1:1] = ["--out-dir", out_dir]
    if argv and argv[-1] in {"run", "cleanup", "preflight"}:
        argv[-1] = subcommand
    else:
        argv.append(subcommand)
    return " ".join(shlex.quote(item) for item in argv)


def decide(checks: list[HandoffCheck]) -> tuple[str, bool, str, str, list[str]]:
    blocked = [item.name for item in checks if item.status != "pass"]
    if blocked:
        return (
            "v317-handoff-blocked",
            False,
            "blocked checks: " + ", ".join(blocked),
            "refresh or repair blocked evidence before requesting live approval",
            blocked,
        )
    return (
        "v317-handoff-awaiting-approval",
        True,
        "all host-side gates pass; live execution remains blocked by exact operator phrase",
        "provide exact V317 phrase only if you accept the approved scope",
        ["exact-v317-approval-phrase"],
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    host = collect_host_metadata()
    current_head = str(host.get("git_head") or "")
    specs = input_spec_with_args(args)
    manifests = [load_json(spec.path) for spec in specs]
    input_checks = [check_input(spec, manifest, current_head) for spec, manifest in zip(specs, manifests)]
    v331, v336, v339 = manifests
    checks = [
        HandoffCheck(
            "current-tree-clean",
            "pass" if host.get("git_dirty") is False else "blocked",
            f"git_head={current_head} git_dirty={host.get('git_dirty')}",
            str(repo_path(Path("."))),
        ),
        *input_checks,
        *contract_checks(v331, v336, v339),
    ]
    decision, pass_ok, reason, next_step, blockers = decide(checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": host,
        "checks": [asdict(item) for item in checks],
        "remaining_blockers": blockers,
        "approval_phrase": APPROVAL_PHRASE,
        "preflight_command": command_variant(str(v331.get("live_command") or ""), "preflight", PREFLIGHT_OUT_DIR),
        "preflight_out_dir": PREFLIGHT_OUT_DIR,
        "live_command": v331.get("live_command"),
        "cleanup_command": v331.get("cleanup_command"),
        "approved_scope": v331.get("approved_scope", []),
        "explicitly_not_approved": v331.get("explicitly_not_approved", []),
        "live_execution_approved": False,
        "device_commands_executed": False,
        "device_mutations": False,
    }


def render_packet(manifest: dict[str, Any]) -> str:
    rows = [[item["name"], item["status"], item["detail"], item["evidence"]] for item in manifest["checks"]]
    lines = [
        "# v340 V317 Final Handoff Packet",
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
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "evidence"], rows),
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['approval_phrase']}`",
        "",
        "## Live Command",
        "",
        "Run this preflight command first; it is designed to execute no device commands and writes to a separate preflight evidence directory:",
        "",
        "```bash",
        str(manifest["preflight_command"]),
        "```",
        "",
        "Then run the live command only if the preflight result is `private-property-namespace-proof-preflight-ready`:",
        "",
        "```bash",
        str(manifest["live_command"]),
        "```",
        "",
        "## Cleanup Command",
        "",
        "```bash",
        str(manifest["cleanup_command"]),
        "```",
        "",
        "## Approved Scope",
        "",
        "\n".join(f"- {item}" for item in manifest["approved_scope"]),
        "",
        "## Explicitly Not Approved",
        "",
        "\n".join(f"- {item}" for item in manifest["explicitly_not_approved"]),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("handoff.md", render_packet(manifest))
    store.write_text("summary.md", render_packet(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
