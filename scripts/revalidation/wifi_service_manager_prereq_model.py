#!/usr/bin/env python3
"""Read-only service-manager prerequisite model after Binder open smoke."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v293-service-manager-prereq")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_V288 = Path("tmp/wifi/v288-hal-framework-boundary-live-20260519-135154/manifest.json")
DEFAULT_V292 = Path("tmp/wifi/v292-binder-open-smoke-live-20260519-141358/manifest.json")
DEFAULT_TOYBOX = "/cache/bin/toybox"

LIVE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("ps", ["run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
    ("stat-system-servicemanager", ["stat", "/mnt/system/system/bin/servicemanager"], 10.0),
    ("stat-system-hwservicemanager", ["stat", "/mnt/system/system/bin/hwservicemanager"], 10.0),
    ("stat-vendor-vndservicemanager", ["stat", "/mnt/system/vendor/bin/vndservicemanager"], 10.0),
    ("find-service-manager-binaries", ["run", DEFAULT_TOYBOX, "find", "/mnt/system", "-maxdepth", "5", "-name", "*servicemanager*"], 20.0),
    ("stat-property-socket", ["stat", "/dev/socket/property_service"], 10.0),
    ("stat-properties-dir", ["stat", "/dev/__properties__"], 10.0),
    ("find-properties", ["run", DEFAULT_TOYBOX, "find", "/dev", "-maxdepth", "3", "-name", "*propert*"], 10.0),
    ("stat-selinux", ["stat", "/sys/fs/selinux"], 10.0),
    ("cat-selinux-enforce", ["run", DEFAULT_TOYBOX, "cat", "/sys/fs/selinux/enforce"], 10.0),
    ("stat-linker64", ["stat", "/mnt/system/system/bin/linker64"], 10.0),
    ("stat-mounted-linkerconfig", ["stat", "/mnt/system/linkerconfig/ld.config.txt"], 10.0),
    ("stat-live-linkerconfig", ["stat", "/linkerconfig/ld.config.txt"], 10.0),
    ("stat-apex", ["stat", "/mnt/system/apex"], 10.0),
    ("stat-system-lib64", ["stat", "/mnt/system/system/lib64"], 10.0),
    ("stat-vendor-lib64", ["stat", "/mnt/system/vendor/lib64"], 10.0),
    ("find-vintf-wifi", ["run", DEFAULT_TOYBOX, "find", "/mnt/system", "-maxdepth", "6", "-path", "*vintf*", "-name", "*wifi*"], 20.0),
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v288-manifest", type=Path, default=DEFAULT_V288)
    parser.add_argument("--v292-manifest", type=Path, default=DEFAULT_V292)
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


def manager_process_lines(ps_text: str) -> list[str]:
    managers = ("servicemanager", "hwservicemanager", "vndservicemanager")
    return [line.strip() for line in ps_text.splitlines() if any(name in line for name in managers)]


def manifest_check_status(manifest: dict[str, Any], name: str) -> str:
    for check in manifest.get("checks", []):
        if check.get("name") == name:
            return str(check.get("status", "missing"))
    return "missing"


def build_checks(store: EvidenceStore,
                 captures: list[CaptureSummary],
                 expect_version: str,
                 v288_manifest: dict[str, Any],
                 v292_manifest: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    version_text = capture_text(store, captures, "version")
    ps_text = capture_text(store, captures, "ps")
    property_hits = capture_text(store, captures, "find-properties")
    vintf_hits = capture_text(store, captures, "find-vintf-wifi")
    manager_lines = manager_process_lines(ps_text)

    add_check(
        checks,
        "v292-binder-open",
        "pass" if v292_manifest.get("decision") == "binder-open-only-smoke-pass" else "missing",
        "info" if v292_manifest.get("decision") == "binder-open-only-smoke-pass" else "blocker",
        f"decision={v292_manifest.get('decision', 'missing')}",
        [str(v292_manifest.get("path", ""))],
        "Binder open-only must pass before service-manager planning",
    )
    add_check(
        checks,
        "v288-boundary",
        "known-blocked" if v288_manifest.get("decision") == "hal-framework-boundary-native-blocked" else "missing",
        "info" if v288_manifest.get("decision") == "hal-framework-boundary-native-blocked" else "warning",
        f"decision={v288_manifest.get('decision', 'missing')}",
        [str(v288_manifest.get("path", ""))],
        "v288 captures baseline framework blockers",
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
    binary_names = ("stat-system-servicemanager", "stat-system-hwservicemanager", "stat-vendor-vndservicemanager")
    present_binary_count = sum(1 for name in binary_names if capture_ok(captures, name))
    add_check(
        checks,
        "service-manager-binaries",
        "present" if present_binary_count >= 2 else "incomplete",
        "info" if present_binary_count >= 2 else "warning",
        f"present={present_binary_count}/3",
        [capture_text(store, captures, "find-service-manager-binaries").strip()[:1000]],
        "binary visibility is not execution readiness",
    )
    add_check(
        checks,
        "service-manager-processes",
        "present" if manager_lines else "absent",
        "warning" if manager_lines else "blocker",
        f"process_count={len(manager_lines)}",
        manager_lines[:10],
        "a future dry-run must define who supervises and cleans up managers",
    )
    property_present = capture_ok(captures, "stat-property-socket") or capture_ok(captures, "stat-properties-dir")
    add_check(
        checks,
        "property-runtime",
        "present" if property_present else "absent",
        "info" if property_present else "blocker",
        "property socket or serialized property area visible" if property_present else "property runtime paths absent",
        property_hits.splitlines()[:12],
        "model or provide Android property runtime before service-manager execution",
    )
    selinux_present = capture_ok(captures, "stat-selinux")
    enforce_text = capture_text(store, captures, "cat-selinux-enforce").strip()
    add_check(
        checks,
        "selinux-surface",
        "present" if selinux_present else "absent",
        "warning" if selinux_present else "warning",
        f"selinux_present={selinux_present} enforce={enforce_text or 'unknown'}",
        [enforce_text] if enforce_text else [],
        "service-manager domains/permissions need a separate model",
    )
    linker_ready = capture_ok(captures, "stat-linker64")
    mounted_linkerconfig = capture_ok(captures, "stat-mounted-linkerconfig")
    live_linkerconfig = capture_ok(captures, "stat-live-linkerconfig")
    add_check(
        checks,
        "linker-runtime",
        "partial" if linker_ready else "missing",
        "warning",
        (
            f"linker64={linker_ready} mounted_linkerconfig={mounted_linkerconfig} "
            f"live_linkerconfig={live_linkerconfig}"
        ),
        [],
        "service-manager dry-run needs explicit linker namespace/root model",
    )
    apex_ready = capture_ok(captures, "stat-apex")
    system_lib_ready = capture_ok(captures, "stat-system-lib64")
    vendor_lib_ready = capture_ok(captures, "stat-vendor-lib64")
    add_check(
        checks,
        "runtime-library-roots",
        "partial" if system_lib_ready and vendor_lib_ready else "incomplete",
        "warning",
        f"apex={apex_ready} system_lib64={system_lib_ready} vendor_lib64={vendor_lib_ready}",
        [],
        "APEX and library roots must match Android linker expectations",
    )
    v288_vintf = manifest_check_status(v288_manifest, "android-vintf-wifi-hal")
    add_check(
        checks,
        "vintf-wifi-metadata",
        "present" if v288_vintf == "present" or vintf_hits.strip() else "missing",
        "info" if v288_vintf == "present" or vintf_hits.strip() else "warning",
        f"v288_status={v288_vintf} live_lines={len(vintf_hits.splitlines())}",
        vintf_hits.splitlines()[:12],
        "VINTF is later service publication input, not an execution pass",
    )
    return checks


def choose_decision(mode: str, captures: list[CaptureSummary], checks: list[Check]) -> tuple[str, bool, str]:
    if mode == "plan":
        return "service-manager-prereq-model-ready", True, "plan-only mode"
    if not captures or not any(capture.ok for capture in captures):
        return "service-manager-prereq-native-capture-failed", False, "no successful native captures"
    blockers = [check for check in checks if check.severity == "blocker"]
    if blockers:
        return (
            "service-manager-prereq-blockers-mapped",
            True,
            "blocked by " + ", ".join(check.name for check in blockers),
        )
    return "service-manager-prereq-model-ready", True, "no hard blocker found; still requires separate dry-run plan"


def render_summary(manifest: dict[str, Any], checks: list[Check]) -> str:
    rows = [[check.name, check.status, check.severity, check.detail, check.next_step] for check in checks]
    return "\n".join(
        [
            "# v293 Service-Manager Prerequisite Model",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- mode: `{manifest['mode']}`",
            f"- pass: `{manifest['pass']}`",
            f"- decision: `{manifest['decision']}`",
            f"- reason: {manifest['reason']}",
            "",
            "## Checks",
            "",
            markdown_table(["check", "status", "severity", "detail", "next"], rows),
            "",
            "## Guardrails",
            "",
            "- no service-manager execution",
            "- no Binder ioctl",
            "- no Binder devnode creation",
            "- no Wi-Fi daemon execution",
            "- no QMI/QRTR packet",
            "- no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "- no rfkill/ICNSS writes",
            "- no Android partition write",
            "",
            "## Recommendation",
            "",
            "- Do not start service managers from this result alone.",
            "- Next candidate is property-runtime feasibility or a service-manager dry-run namespace model.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v288_manifest = load_manifest(args.v288_manifest)
    v292_manifest = load_manifest(args.v292_manifest)
    captures: list[CaptureSummary] = []
    if args.command == "run":
        captures = live_collect(args, store)
    else:
        store.mkdir("native")
    checks = build_checks(store, captures, args.expect_version, v288_manifest, v292_manifest)
    decision, pass_ok, reason = choose_decision(args.command, captures, checks)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "mode": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "expect_version": args.expect_version,
        "v288_manifest": {
            "path": str(repo_path(args.v288_manifest)),
            "present": bool(v288_manifest.get("present")),
            "decision": v288_manifest.get("decision"),
        },
        "v292_manifest": {
            "path": str(repo_path(args.v292_manifest)),
            "present": bool(v292_manifest.get("present")),
            "decision": v292_manifest.get("decision"),
        },
        "host": collect_host_metadata(),
        "captures": [asdict(capture) for capture in captures],
        "checks": [asdict(check) for check in checks],
    }
    store.write_json("manifest.json", manifest)
    store.write_json("checks.json", {"checks": [asdict(check) for check in checks]})
    store.write_text("summary.md", render_summary(manifest, checks))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
