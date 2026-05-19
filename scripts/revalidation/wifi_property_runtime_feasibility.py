#!/usr/bin/env python3
"""Read-only Android property runtime feasibility inventory."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v294-property-runtime")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_V293 = Path("tmp/wifi/v293-service-manager-prereq-live-20260519-141752/manifest.json")
DEFAULT_TOYBOX = "/cache/bin/toybox"

PROPERTY_CONTEXT_PATHS = (
    "/mnt/system/system/etc/selinux/plat_property_contexts",
    "/mnt/system/system_ext/etc/selinux/system_ext_property_contexts",
    "/mnt/system/vendor/etc/selinux/vendor_property_contexts",
    "/mnt/system/product/etc/selinux/product_property_contexts",
    "/mnt/system/odm/etc/selinux/odm_property_contexts",
)

BUILD_PROP_PATHS = (
    "/mnt/system/system/build.prop",
    "/mnt/system/vendor/build.prop",
    "/mnt/system/product/build.prop",
    "/mnt/system/odm/build.prop",
    "/mnt/system/system_ext/build.prop",
    "/mnt/system/system/etc/prop.default",
    "/mnt/system/vendor/default.prop",
)

LIVE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("stat-dev-socket", ["stat", "/dev/socket"], 10.0),
    ("stat-property-socket", ["stat", "/dev/socket/property_service"], 10.0),
    ("stat-properties-dir", ["stat", "/dev/__properties__"], 10.0),
    ("find-dev-properties", ["run", DEFAULT_TOYBOX, "find", "/dev", "-maxdepth", "4", "-name", "*propert*"], 15.0),
    ("find-mounted-property-contexts", ["run", DEFAULT_TOYBOX, "find", "/mnt/system", "-maxdepth", "6", "-name", "*property_contexts"], 20.0),
    ("find-mounted-build-props", ["run", DEFAULT_TOYBOX, "find", "/mnt/system", "-maxdepth", "5", "-name", "*build.prop", "-o", "-name", "default.prop", "-o", "-name", "prop.default"], 20.0),
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
    parser.add_argument("--v293-manifest", type=Path, default=DEFAULT_V293)
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
    for path in PROPERTY_CONTEXT_PATHS:
        name = "stat-" + safe_name(path)
        captures.append(capture_one(args, store, name, ["stat", path], timeout=10.0))
    for path in BUILD_PROP_PATHS:
        name = "stat-" + safe_name(path)
        captures.append(capture_one(args, store, name, ["stat", path], timeout=10.0))
    return captures


def capture_one(args: argparse.Namespace,
                store: EvidenceStore,
                name: str,
                command: list[str],
                timeout: float) -> CaptureSummary:
    record = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text)
    return CaptureSummary(
        name=name,
        command=record.command,
        ok=record.ok,
        rc=record.rc,
        status=record.status,
        duration_sec=record.duration_sec,
        file=rel,
        error=record.error,
    )


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


def stat_name(path: str) -> str:
    return "stat-" + safe_name(path)


def manifest_check_status(manifest: dict[str, Any], name: str) -> str:
    for check in manifest.get("checks", []):
        if check.get("name") == name:
            return str(check.get("status", "missing"))
    return "missing"


def build_checks(store: EvidenceStore,
                 captures: list[CaptureSummary],
                 expect_version: str,
                 v293_manifest: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    version_text = capture_text(store, captures, "version")
    dev_property_hits = capture_text(store, captures, "find-dev-properties")
    context_hits = capture_text(store, captures, "find-mounted-property-contexts")
    build_prop_hits = capture_text(store, captures, "find-mounted-build-props")
    v293_property_status = manifest_check_status(v293_manifest, "property-runtime")

    add_check(
        checks,
        "v293-property-blocker",
        "expected" if v293_property_status == "absent" else "unexpected",
        "info" if v293_property_status == "absent" else "warning",
        f"v293_property_runtime={v293_property_status}",
        [str(v293_manifest.get("path", ""))],
        "refresh v293 if service-manager blocker changed",
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
    socket_present = capture_ok(captures, "stat-property-socket")
    area_present = capture_ok(captures, "stat-properties-dir")
    add_check(
        checks,
        "live-property-runtime",
        "present" if socket_present or area_present else "absent",
        "info" if socket_present or area_present else "blocker",
        f"property_socket={socket_present} properties_dir={area_present}",
        dev_property_hits.splitlines()[:12],
        "service-manager execution remains blocked if runtime is absent",
    )
    context_lines = [line for line in context_hits.splitlines() if line.strip()]
    context_present_count = sum(1 for path in PROPERTY_CONTEXT_PATHS if capture_ok(captures, stat_name(path)))
    context_present = context_present_count >= 2 or len(context_lines) >= 2
    add_check(
        checks,
        "mounted-property-contexts",
        "present" if context_present else "incomplete",
        "info" if context_present else "warning",
        f"stat_present={context_present_count}/{len(PROPERTY_CONTEXT_PATHS)} find_lines={len(context_lines)}",
        context_lines[:20],
        "property contexts are inputs, not runtime state",
    )
    build_prop_lines = [line for line in build_prop_hits.splitlines() if line.strip()]
    build_prop_count = sum(1 for path in BUILD_PROP_PATHS if capture_ok(captures, stat_name(path)))
    build_prop_present = build_prop_count >= 2 or len(build_prop_lines) >= 2
    add_check(
        checks,
        "mounted-build-props",
        "present" if build_prop_present else "incomplete",
        "info" if build_prop_present else "warning",
        f"stat_present={build_prop_count}/{len(BUILD_PROP_PATHS)} find_lines={len(build_prop_lines)}",
        build_prop_lines[:20],
        "build props can seed a future read-only property model",
    )
    add_check(
        checks,
        "dev-socket-dir",
        "present" if capture_ok(captures, "stat-dev-socket") else "absent",
        "warning",
        "/dev/socket directory visible" if capture_ok(captures, "stat-dev-socket") else "/dev/socket absent",
        [],
        "creating property service socket is out of v294 scope",
    )
    return checks


def choose_decision(mode: str, captures: list[CaptureSummary], checks: list[Check]) -> tuple[str, bool, str]:
    if mode == "plan":
        return "property-runtime-feasibility-ready", True, "plan-only mode"
    if not captures or not any(capture.ok for capture in captures):
        return "property-runtime-native-capture-failed", False, "no successful native captures"
    by_name = {check.name: check for check in checks}
    runtime_status = by_name.get("live-property-runtime", Check("", "", "", "", [], "")).status
    context_status = by_name.get("mounted-property-contexts", Check("", "", "", "", [], "")).status
    build_prop_status = by_name.get("mounted-build-props", Check("", "", "", "", [], "")).status
    if runtime_status == "present":
        return "property-runtime-native-present", True, "native property runtime paths are visible"
    if context_status == "present" and build_prop_status == "present":
        return "property-runtime-inputs-visible-runtime-absent", True, "property inputs visible but runtime paths absent"
    return "property-runtime-inputs-incomplete", False, "property runtime absent and mounted inputs incomplete"


def render_summary(manifest: dict[str, Any], checks: list[Check]) -> str:
    rows = [[check.name, check.status, check.severity, check.detail, check.next_step] for check in checks]
    return "\n".join(
        [
            "# v294 Android Property Runtime Feasibility",
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
            "- no property service creation",
            "- no /dev/socket or /dev/__properties__ writes",
            "- no property value mutation",
            "- no service-manager execution",
            "- no Binder ioctl or Binder devnode creation",
            "- no Wi-Fi daemon execution",
            "- no QMI/QRTR packet",
            "- no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "- no Android partition write",
            "",
            "## Recommendation",
            "",
            "- Do not start service managers from this result alone.",
            "- Next candidate is a read-only property snapshot/shim model.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v293_manifest = load_manifest(args.v293_manifest)
    captures: list[CaptureSummary] = []
    if args.command == "run":
        captures = live_collect(args, store)
    else:
        store.mkdir("native")
    checks = build_checks(store, captures, args.expect_version, v293_manifest)
    decision, pass_ok, reason = choose_decision(args.command, captures, checks)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "mode": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "expect_version": args.expect_version,
        "v293_manifest": {
            "path": str(repo_path(args.v293_manifest)),
            "present": bool(v293_manifest.get("present")),
            "decision": v293_manifest.get("decision"),
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
