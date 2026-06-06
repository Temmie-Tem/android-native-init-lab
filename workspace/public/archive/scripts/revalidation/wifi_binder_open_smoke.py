#!/usr/bin/env python3
"""Temporary Binder open/close-only smoke using toybox dd count=0."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v292-binder-open-smoke")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_V290 = Path("tmp/wifi/v290-binder-devnode-live-20260519-140441/manifest.json")
DEFAULT_V291 = Path("tmp/wifi/v291-binder-devnode-smoke-live-20260519-140937/manifest.json")
DEFAULT_TOYBOX = "/cache/bin/toybox"
BINDER_ORDER = ("binder", "hwbinder", "vndbinder")


@dataclass
class StepResult:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


@dataclass
class Candidate:
    name: str
    path: str
    major: int
    minor: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v290-manifest", type=Path, default=DEFAULT_V290)
    parser.add_argument("--v291-manifest", type=Path, default=DEFAULT_V291)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--apply", action="store_true", help="create temporary nodes and perform open-only checks")
    return parser.parse_args()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def load_candidates(v290_manifest: dict[str, Any]) -> list[Candidate]:
    by_name: dict[str, Candidate] = {}
    for item in v290_manifest.get("candidates", []):
        name = item.get("name")
        path = item.get("path")
        major = item.get("sysfs_major")
        minor = item.get("sysfs_minor")
        if name in BINDER_ORDER and path == f"/dev/{name}" and isinstance(major, int) and isinstance(minor, int):
            by_name[name] = Candidate(name=name, path=path, major=major, minor=minor)
    return [by_name[name] for name in BINDER_ORDER if name in by_name]


def capture_command(args: argparse.Namespace,
                    store: EvidenceStore,
                    name: str,
                    command: list[str],
                    timeout: float | None = None) -> StepResult:
    record = run_capture(args, name, command, timeout=timeout if timeout is not None else args.timeout)
    text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text)
    return StepResult(
        name=name,
        command=record.command,
        ok=record.ok,
        rc=record.rc,
        status=record.status,
        duration_sec=record.duration_sec,
        file=rel,
        error=record.error,
    )


def capture_state(args: argparse.Namespace,
                  store: EvidenceStore,
                  prefix: str,
                  candidates: list[Candidate]) -> list[StepResult]:
    results = [capture_command(args, store, f"{prefix}-version", ["version"], timeout=10.0)]
    for candidate in candidates:
        results.append(capture_command(args, store, f"{prefix}-stat-{candidate.name}", ["stat", candidate.path], timeout=10.0))
    return results


def create_nodes(args: argparse.Namespace,
                 store: EvidenceStore,
                 candidates: list[Candidate]) -> list[StepResult]:
    return [
        capture_command(
            args,
            store,
            f"create-{candidate.name}",
            ["mknodc", candidate.path, str(candidate.major), str(candidate.minor)],
            timeout=10.0,
        )
        for candidate in candidates
    ]


def open_only(args: argparse.Namespace,
              store: EvidenceStore,
              candidates: list[Candidate]) -> list[StepResult]:
    return [
        capture_command(
            args,
            store,
            f"open-only-{candidate.name}",
            ["run", DEFAULT_TOYBOX, "dd", f"if={candidate.path}", "of=/dev/null", "bs=1", "count=0"],
            timeout=10.0,
        )
        for candidate in candidates
    ]


def cleanup_nodes(args: argparse.Namespace,
                  store: EvidenceStore,
                  candidates: list[Candidate]) -> list[StepResult]:
    paths = [candidate.path for candidate in candidates]
    if not paths:
        return []
    return [
        capture_command(
            args,
            store,
            "cleanup-rm-binder-devnodes",
            ["run", DEFAULT_TOYBOX, "rm", "-f", *paths],
            timeout=10.0,
        )
    ]


def all_step_prefix_ok(steps: list[StepResult], prefix: str) -> bool:
    selected = [step for step in steps if step.name.startswith(prefix)]
    return bool(selected) and all(step.ok for step in selected)


def stat_presence(steps: list[StepResult], prefix: str, expect_present: bool) -> bool:
    stats = [step for step in steps if step.name.startswith(f"{prefix}-stat-")]
    return bool(stats) and all(step.ok == expect_present for step in stats)


def choose_decision(mode: str,
                    apply: bool,
                    v291_manifest: dict[str, Any],
                    candidates: list[Candidate],
                    steps: list[StepResult]) -> tuple[str, bool, str]:
    if mode == "plan":
        if v291_manifest.get("decision") == "binder-devnode-create-cleanup-pass" and len(candidates) == 3:
            return "binder-open-smoke-plan-ready", True, "v291 input ready; run mode requires --apply"
        return "binder-open-smoke-input-missing", False, "v291 manifest or candidates missing"
    if not apply:
        return "binder-open-smoke-input-missing", False, "run mode requires --apply"
    if v291_manifest.get("decision") != "binder-devnode-create-cleanup-pass" or len(candidates) != 3:
        return "binder-open-smoke-input-missing", False, "v291 manifest did not provide prerequisite"
    if not all_step_prefix_ok(steps, "create-"):
        return "binder-open-smoke-create-failed", False, "one or more mknodc commands failed"
    if not stat_presence(steps, "created", expect_present=True):
        return "binder-open-smoke-create-failed", False, "created nodes were not all visible"
    if not all_step_prefix_ok(steps, "open-only-"):
        return "binder-open-smoke-open-failed", False, "one or more open-only dd commands failed"
    cleanup_ok = any(step.name == "cleanup-rm-binder-devnodes" and step.ok for step in steps)
    if not cleanup_ok or not stat_presence(steps, "post", expect_present=False):
        return "binder-open-smoke-cleanup-failed", False, "cleanup failed or nodes remained visible"
    return "binder-open-only-smoke-pass", True, "temporary Binder devnodes opened with count=0 and cleaned up"


def render_summary(manifest: dict[str, Any], candidates: list[Candidate], steps: list[StepResult]) -> str:
    candidate_rows = [[candidate.name, candidate.path, str(candidate.major), str(candidate.minor)] for candidate in candidates]
    step_rows = [[step.name, "PASS" if step.ok else "FAIL", str(step.rc), step.status, step.command, step.file] for step in steps]
    return "\n".join(
        [
            "# v292 Binder Open-Only Smoke",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- mode: `{manifest['mode']}`",
            f"- apply: `{manifest['apply']}`",
            f"- pass: `{manifest['pass']}`",
            f"- decision: `{manifest['decision']}`",
            f"- reason: {manifest['reason']}",
            "",
            "## Candidates",
            "",
            markdown_table(["name", "path", "major", "minor"], candidate_rows),
            "",
            "## Steps",
            "",
            markdown_table(["step", "ok", "rc", "status", "command", "file"], step_rows),
            "",
            "## Guardrails",
            "",
            "- no Binder ioctl",
            "- no binderfs mount",
            "- no service-manager execution",
            "- no Wi-Fi daemon execution",
            "- no QMI/QRTR packet",
            "- no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "- no rfkill/ICNSS writes",
            "- no Android partition write",
            "- cleanup attempted in a finally block",
            "",
            "## Recommendation",
            "",
            "- If PASS, the next step is service-manager prerequisite modeling.",
            "- Do not start service managers, HALs, or `wificond` from this result alone.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    v290_manifest = load_manifest(args.v290_manifest)
    v291_manifest = load_manifest(args.v291_manifest)
    candidates = load_candidates(v290_manifest)
    apply = bool(getattr(args, "apply", False))
    steps: list[StepResult] = []
    if args.command == "run" and apply:
        try:
            steps.extend(capture_state(args, store, "pre", candidates))
            steps.extend(create_nodes(args, store, candidates))
            steps.extend(capture_state(args, store, "created", candidates))
            steps.extend(open_only(args, store, candidates))
        finally:
            steps.extend(cleanup_nodes(args, store, candidates))
            steps.extend(capture_state(args, store, "post", candidates))
    elif args.command == "run":
        steps.extend(capture_state(args, store, "pre", candidates))
    decision, pass_ok, reason = choose_decision(args.command, apply, v291_manifest, candidates, steps)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "mode": args.command,
        "apply": apply,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "expect_version": args.expect_version,
        "v290_manifest": {
            "path": str(repo_path(args.v290_manifest)),
            "present": bool(v290_manifest.get("present")),
            "decision": v290_manifest.get("decision"),
        },
        "v291_manifest": {
            "path": str(repo_path(args.v291_manifest)),
            "present": bool(v291_manifest.get("present")),
            "decision": v291_manifest.get("decision"),
        },
        "host": collect_host_metadata(),
        "candidates": [asdict(candidate) for candidate in candidates],
        "steps": [asdict(step) for step in steps],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest, candidates, steps))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
