#!/usr/bin/env python3
"""Read-only Binder devnode feasibility planner for Wi-Fi HAL work."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v290-binder-devnode")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_V289 = Path("tmp/wifi/v289-binder-service-manager-live-20260519-135726/manifest.json")
DEFAULT_TOYBOX = "/cache/bin/toybox"
BINDER_NAMES = ("binder", "hwbinder", "vndbinder")
MISC_MAJOR = 10

LIVE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("proc-misc", ["run", DEFAULT_TOYBOX, "cat", "/proc/misc"], 10.0),
    ("proc-mounts", ["run", DEFAULT_TOYBOX, "cat", "/proc/mounts"], 10.0),
    ("ls-dev", ["ls", "/dev"], 10.0),
    ("stat-dev-binder", ["stat", "/dev/binder"], 10.0),
    ("stat-dev-hwbinder", ["stat", "/dev/hwbinder"], 10.0),
    ("stat-dev-vndbinder", ["stat", "/dev/vndbinder"], 10.0),
    ("stat-sys-class-misc-binder", ["stat", "/sys/class/misc/binder"], 10.0),
    ("stat-sys-class-misc-hwbinder", ["stat", "/sys/class/misc/hwbinder"], 10.0),
    ("stat-sys-class-misc-vndbinder", ["stat", "/sys/class/misc/vndbinder"], 10.0),
    ("cat-sys-class-misc-binder-dev", ["run", DEFAULT_TOYBOX, "cat", "/sys/class/misc/binder/dev"], 10.0),
    ("cat-sys-class-misc-hwbinder-dev", ["run", DEFAULT_TOYBOX, "cat", "/sys/class/misc/hwbinder/dev"], 10.0),
    ("cat-sys-class-misc-vndbinder-dev", ["run", DEFAULT_TOYBOX, "cat", "/sys/class/misc/vndbinder/dev"], 10.0),
)


@dataclass
class CaptureSummary:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


@dataclass
class DevnodeCandidate:
    name: str
    path: str
    sysfs_major: int | None
    sysfs_minor: int | None
    proc_misc_minor: int | None
    devnode_present: bool
    status: str
    proposed_command: str | None
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v289-manifest", type=Path, default=DEFAULT_V289)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
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


def live_collect(args: argparse.Namespace, store: EvidenceStore) -> list[CaptureSummary]:
    captures: list[CaptureSummary] = []
    store.mkdir("native")
    for name, command, timeout in LIVE_COMMANDS:
        record = run_capture(args, name, command, timeout=timeout)
        text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
        rel = f"native/{safe_name(name)}.txt"
        store.write_text(rel, text)
        captures.append(
            CaptureSummary(
                name=name,
                command=record.command,
                ok=record.ok,
                rc=record.rc,
                status=record.status,
                duration_sec=record.duration_sec,
                file=rel,
                error=record.error,
            )
        )
    return captures


def capture_ok(captures: list[CaptureSummary], name: str) -> bool:
    return any(capture.name == name and capture.ok for capture in captures)


def capture_text(store: EvidenceStore, captures: list[CaptureSummary], name: str) -> str:
    for capture in captures:
        if capture.name != name:
            continue
        path = store.path(capture.file)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def parse_proc_misc(text: str) -> dict[str, int]:
    minors: dict[str, int] = {}
    for raw_line in text.splitlines():
        parts = raw_line.strip().split()
        if len(parts) != 2:
            continue
        try:
            minor = int(parts[0], 10)
        except ValueError:
            continue
        minors[parts[1]] = minor
    return minors


def parse_sysfs_dev(text: str) -> tuple[int | None, int | None]:
    match = re.search(r"\b([0-9]+):([0-9]+)\b", text)
    if not match:
        return None, None
    return int(match.group(1), 10), int(match.group(2), 10)


def build_candidates(store: EvidenceStore, captures: list[CaptureSummary]) -> list[DevnodeCandidate]:
    proc_misc = parse_proc_misc(capture_text(store, captures, "proc-misc"))
    candidates: list[DevnodeCandidate] = []
    for name in BINDER_NAMES:
        sysfs_name = f"cat-sys-class-misc-{name}-dev"
        stat_name = f"stat-dev-{name}"
        major, minor = parse_sysfs_dev(capture_text(store, captures, sysfs_name))
        proc_minor = proc_misc.get(name)
        devnode_present = capture_ok(captures, stat_name)
        command = None
        if major is None or minor is None:
            status = "missing-sysfs-dev"
            detail = "sysfs dev attribute missing or unparsable"
        elif major != MISC_MAJOR:
            status = "unexpected-major"
            detail = f"expected misc major {MISC_MAJOR}, got {major}"
        elif proc_minor is None:
            status = "missing-proc-misc"
            detail = "device absent from /proc/misc"
        elif proc_minor != minor:
            status = "minor-mismatch"
            detail = f"sysfs minor {minor} != /proc/misc minor {proc_minor}"
        elif devnode_present:
            status = "existing"
            detail = "devnode already visible"
        else:
            status = "ready"
            detail = "metadata consistent and devnode absent"
            command = f"mknod -m 0600 /dev/{name} c {major} {minor}"
        candidates.append(
            DevnodeCandidate(
                name=name,
                path=f"/dev/{name}",
                sysfs_major=major,
                sysfs_minor=minor,
                proc_misc_minor=proc_minor,
                devnode_present=devnode_present,
                status=status,
                proposed_command=command,
                detail=detail,
            )
        )
    return candidates


def build_checks(store: EvidenceStore,
                 captures: list[CaptureSummary],
                 expect_version: str,
                 v289_manifest: dict[str, Any],
                 candidates: list[DevnodeCandidate]) -> list[Check]:
    checks: list[Check] = []
    version_text = capture_text(store, captures, "version")
    proc_misc = capture_text(store, captures, "proc-misc")

    v289_decision = v289_manifest.get("decision", "missing") if v289_manifest.get("present") else "missing"
    add_check(
        checks,
        "v289-decision",
        "expected" if v289_decision == "binder-kernel-present-devnodes-missing" else "unexpected",
        "info" if v289_decision == "binder-kernel-present-devnodes-missing" else "warning",
        f"decision={v289_decision}",
        [str(v289_manifest.get("path", ""))],
        "refresh v289 evidence if the baseline changed",
    )
    add_check(
        checks,
        "native-version",
        "present" if expect_version in version_text else "mismatch",
        "info" if expect_version in version_text else "warning",
        f"expect_version={expect_version}",
        [line for line in version_text.splitlines() if "A90 Linux init" in line][:3],
        "refresh baseline if device build changed",
    )
    add_check(
        checks,
        "proc-misc-binder-lines",
        "present" if all(name in parse_proc_misc(proc_misc) for name in BINDER_NAMES) else "incomplete",
        "info" if all(name in parse_proc_misc(proc_misc) for name in BINDER_NAMES) else "blocker",
        "Binder misc minors visible" if proc_misc else "/proc/misc capture missing",
        [line.strip() for line in proc_misc.splitlines() if "binder" in line],
        "do not create devnodes without registered misc devices",
    )

    for candidate in candidates:
        severity = "info" if candidate.status in {"ready", "existing"} else "blocker"
        add_check(
            checks,
            f"candidate-{candidate.name}",
            candidate.status,
            severity,
            (
                f"path={candidate.path} sysfs={candidate.sysfs_major}:{candidate.sysfs_minor} "
                f"proc_misc_minor={candidate.proc_misc_minor} present={candidate.devnode_present}"
            ),
            [candidate.proposed_command or candidate.detail],
            "requires explicit approval before any mknod/open smoke",
        )
    return checks


def choose_decision(mode: str, captures: list[CaptureSummary], candidates: list[DevnodeCandidate]) -> tuple[str, bool, str]:
    if mode == "plan":
        return "binder-devnode-feasibility-ready", True, "plan-only mode"
    if not captures or not any(capture.ok for capture in captures):
        return "binder-devnode-native-capture-failed", False, "no successful native captures"
    statuses = {candidate.status for candidate in candidates}
    if statuses == {"existing"}:
        return "binder-devnodes-already-present", True, "all Binder devnodes already visible"
    if statuses <= {"ready", "existing"} and any(candidate.status == "ready" for candidate in candidates):
        return "binder-devnode-plan-ready", True, "metadata consistent; devnode creation candidate produced"
    if any(status.endswith("mismatch") or status == "unexpected-major" for status in statuses):
        return "binder-devnode-metadata-mismatch", False, f"metadata mismatch statuses={sorted(statuses)}"
    return "binder-devnode-input-missing", False, f"missing or incomplete metadata statuses={sorted(statuses)}"


def render_summary(manifest: dict[str, Any], checks: list[Check], candidates: list[DevnodeCandidate]) -> str:
    rows = [
        [check.name, check.status, check.severity, check.detail, check.next_step]
        for check in checks
    ]
    candidate_rows = [
        [
            candidate.name,
            candidate.path,
            f"{candidate.sysfs_major}:{candidate.sysfs_minor}",
            str(candidate.proc_misc_minor),
            candidate.status,
            candidate.proposed_command or "",
        ]
        for candidate in candidates
    ]
    return "\n".join(
        [
            "# v290 Binder Devnode Feasibility",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- mode: `{manifest['mode']}`",
            f"- pass: `{manifest['pass']}`",
            f"- decision: `{manifest['decision']}`",
            f"- reason: {manifest['reason']}",
            "",
            "## Candidates",
            "",
            markdown_table(
                ["name", "path", "sysfs major:minor", "proc misc minor", "status", "non-executed candidate"],
                candidate_rows,
            ),
            "",
            "## Checks",
            "",
            markdown_table(["check", "status", "severity", "detail", "next"], rows),
            "",
            "## Guardrails",
            "",
            "- no mknod",
            "- no binderfs mount",
            "- no Binder ioctl or open smoke",
            "- no service-manager execution",
            "- no Wi-Fi daemon execution",
            "- no QMI/QRTR packet",
            "- no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "- no rfkill/ICNSS writes",
            "- no Android partition write",
            "",
            "## Recommendation",
            "",
            "- Treat the proposed commands as review evidence only.",
            "- A later v291 must explicitly approve temporary node creation and define cleanup.",
            "- HAL, `wificond`, supplicant, hostapd, and Wi-Fi link-up remain blocked.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v289_manifest = load_manifest(args.v289_manifest)
    captures: list[CaptureSummary] = []
    if args.command == "run":
        captures = live_collect(args, store)
    else:
        store.mkdir("native")
    candidates = build_candidates(store, captures)
    checks = build_checks(store, captures, args.expect_version, v289_manifest, candidates)
    decision, pass_ok, reason = choose_decision(args.command, captures, candidates)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "mode": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "expect_version": args.expect_version,
        "v289_manifest": {
            "path": str(repo_path(args.v289_manifest)),
            "present": bool(v289_manifest.get("present")),
            "decision": v289_manifest.get("decision"),
        },
        "host": collect_host_metadata(),
        "captures": [asdict(capture) for capture in captures],
        "candidates": [asdict(candidate) for candidate in candidates],
        "checks": [asdict(check) for check in checks],
    }
    store.write_json("manifest.json", manifest)
    store.write_json("checks.json", {"checks": [asdict(check) for check in checks]})
    store.write_text("summary.md", render_summary(manifest, checks, candidates))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
