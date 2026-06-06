#!/usr/bin/env python3
"""Read-only Android property snapshot model from mounted property inputs."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v295-property-snapshot")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_V294 = Path("tmp/wifi/v294-property-runtime-live-20260519-142338/manifest.json")
DEFAULT_TOYBOX = "/cache/bin/toybox"
MAX_CAPTURE_FILES = 16

DISCOVERY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("find-property-inputs", ["run", DEFAULT_TOYBOX, "find", "/mnt/system", "-maxdepth", "6", "-name", "*build.prop", "-o", "-name", "default.prop", "-o", "-name", "prop.default"], 20.0),
    ("find-property-contexts", ["run", DEFAULT_TOYBOX, "find", "/mnt/system", "-maxdepth", "7", "-name", "*property_contexts"], 20.0),
)

REQUIRED_KEYS = (
    "ro.build.version.sdk",
    "ro.product.name",
    "ro.hardware",
    "ro.vendor.build.version.sdk",
)

WIFI_TOKENS = ("wifi", "wlan", "cnss", "qcom", "qca", "wcnss")


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
    parser.add_argument("--v294-manifest", type=Path, default=DEFAULT_V294)
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


def capture_command(args: argparse.Namespace,
                    store: EvidenceStore,
                    name: str,
                    command: list[str],
                    timeout: float | None = None) -> CaptureSummary:
    record = run_capture(args, name, command, timeout=timeout if timeout is not None else args.timeout)
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


def capture_text(store: EvidenceStore, captures: list[CaptureSummary], name: str) -> str:
    for capture in captures:
        if capture.name != name:
            continue
        path = store.path(capture.file)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def discover_paths(text: str) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("/mnt/system/") or line in seen:
            continue
        seen.add(line)
        paths.append(line)
    return paths[:MAX_CAPTURE_FILES]


def live_collect(args: argparse.Namespace, store: EvidenceStore) -> list[CaptureSummary]:
    captures: list[CaptureSummary] = []
    store.mkdir("native")
    for name, command, timeout in DISCOVERY_COMMANDS:
        captures.append(capture_command(args, store, name, command, timeout=timeout))
    property_paths = discover_paths(capture_text(store, captures, "find-property-inputs"))
    context_paths = discover_paths(capture_text(store, captures, "find-property-contexts"))
    for path in property_paths:
        captures.append(capture_command(args, store, "cat-prop-" + safe_name(path), ["run", DEFAULT_TOYBOX, "cat", path], timeout=20.0))
    for path in context_paths:
        captures.append(capture_command(args, store, "cat-context-" + safe_name(path), ["run", DEFAULT_TOYBOX, "cat", path], timeout=20.0))
    return captures


def parse_properties(text: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            props[key] = value.strip()
    return props


def parse_context_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def build_snapshot(store: EvidenceStore, captures: list[CaptureSummary]) -> dict[str, Any]:
    props: dict[str, str] = {}
    context_lines: list[str] = []
    property_files: list[str] = []
    context_files: list[str] = []
    for capture in captures:
        text = capture_text(store, captures, capture.name)
        if capture.name.startswith("cat-prop-") and capture.ok:
            property_files.append(capture.command.rsplit(" ", 1)[-1])
            props.update(parse_properties(text))
        if capture.name.startswith("cat-context-") and capture.ok:
            context_files.append(capture.command.rsplit(" ", 1)[-1])
            context_lines.extend(parse_context_lines(text))
    wifi_props = {
        key: value
        for key, value in props.items()
        if any(token in key.lower() or token in value.lower() for token in WIFI_TOKENS)
    }
    required = {key: props.get(key) for key in REQUIRED_KEYS}
    return {
        "property_files": property_files,
        "context_files": context_files,
        "property_count": len(props),
        "context_line_count": len(context_lines),
        "ro_count": sum(1 for key in props if key.startswith("ro.")),
        "ro_vendor_count": sum(1 for key in props if key.startswith("ro.vendor.")),
        "wifi_property_count": len(wifi_props),
        "required": required,
        "required_present_count": sum(1 for value in required.values() if value not in (None, "")),
        "wifi_properties_sample": dict(list(sorted(wifi_props.items()))[:40]),
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(expect_version: str,
                 v294_manifest: dict[str, Any],
                 snapshot: dict[str, Any],
                 version_text: str) -> list[Check]:
    checks: list[Check] = []
    add_check(
        checks,
        "v294-property-runtime",
        "expected" if v294_manifest.get("decision") == "property-runtime-inputs-visible-runtime-absent" else "unexpected",
        "info" if v294_manifest.get("decision") == "property-runtime-inputs-visible-runtime-absent" else "warning",
        f"decision={v294_manifest.get('decision', 'missing')}",
        [str(v294_manifest.get("path", ""))],
        "refresh v294 if property runtime changed",
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
    prop_count = int(snapshot["property_count"])
    add_check(
        checks,
        "property-snapshot",
        "present" if prop_count >= 20 else "partial",
        "info" if prop_count >= 20 else "warning",
        f"property_count={prop_count} files={len(snapshot['property_files'])}",
        snapshot["property_files"][:12],
        "static properties can seed read-only lookup model",
    )
    context_count = int(snapshot["context_line_count"])
    add_check(
        checks,
        "property-context-snapshot",
        "present" if context_count >= 20 else "partial",
        "info" if context_count >= 20 else "warning",
        f"context_lines={context_count} files={len(snapshot['context_files'])}",
        snapshot["context_files"][:12],
        "contexts map property labels, not live property values",
    )
    required_present = int(snapshot["required_present_count"])
    add_check(
        checks,
        "required-property-baseline",
        "present" if required_present >= 2 else "partial",
        "info" if required_present >= 2 else "warning",
        f"present={required_present}/{len(REQUIRED_KEYS)}",
        [f"{key}={value}" for key, value in snapshot["required"].items() if value],
        "missing keys may need Android-boot capture or property defaults",
    )
    add_check(
        checks,
        "wifi-property-surface",
        "present" if int(snapshot["wifi_property_count"]) > 0 else "absent",
        "info" if int(snapshot["wifi_property_count"]) > 0 else "warning",
        f"wifi_property_count={snapshot['wifi_property_count']}",
        [f"{key}={value}" for key, value in snapshot["wifi_properties_sample"].items()][:20],
        "Wi-Fi properties are hints, not link-up readiness",
    )
    return checks


def choose_decision(mode: str, captures: list[CaptureSummary], checks: list[Check]) -> tuple[str, bool, str]:
    if mode == "plan":
        return "property-snapshot-model-ready", True, "plan-only mode"
    if not captures or not any(capture.ok for capture in captures):
        return "property-snapshot-native-capture-failed", False, "no successful native captures"
    by_name = {check.name: check for check in checks}
    if by_name.get("property-snapshot", Check("", "", "", "", [], "")).status == "present" and by_name.get("property-context-snapshot", Check("", "", "", "", [], "")).status == "present":
        return "property-snapshot-model-ready", True, "static property and context inputs parsed"
    if by_name.get("property-snapshot", Check("", "", "", "", [], "")).status in {"present", "partial"}:
        return "property-snapshot-inputs-partial", True, "partial property snapshot parsed"
    return "property-snapshot-input-missing", False, "no usable property snapshot inputs"


def render_summary(manifest: dict[str, Any], checks: list[Check], snapshot: dict[str, Any]) -> str:
    rows = [[check.name, check.status, check.severity, check.detail, check.next_step] for check in checks]
    return "\n".join(
        [
            "# v295 Read-Only Property Snapshot Model",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- mode: `{manifest['mode']}`",
            f"- pass: `{manifest['pass']}`",
            f"- decision: `{manifest['decision']}`",
            f"- reason: {manifest['reason']}",
            "",
            "## Snapshot",
            "",
            f"- property files: `{len(snapshot['property_files'])}`",
            f"- property count: `{snapshot['property_count']}`",
            f"- context files: `{len(snapshot['context_files'])}`",
            f"- context line count: `{snapshot['context_line_count']}`",
            f"- Wi-Fi property count: `{snapshot['wifi_property_count']}`",
            f"- required present: `{snapshot['required_present_count']}/{len(REQUIRED_KEYS)}`",
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
            "- Next candidate is property shim design, still without service-manager execution.",
            "- Do not treat static properties as live Android property runtime.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v294_manifest = load_manifest(args.v294_manifest)
    captures: list[CaptureSummary] = []
    if args.command == "run":
        captures = live_collect(args, store)
    else:
        store.mkdir("native")
    snapshot = build_snapshot(store, captures)
    version_text = capture_text(store, captures, "version")
    checks = build_checks(args.expect_version, v294_manifest, snapshot, version_text)
    decision, pass_ok, reason = choose_decision(args.command, captures, checks)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "mode": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "expect_version": args.expect_version,
        "v294_manifest": {
            "path": str(repo_path(args.v294_manifest)),
            "present": bool(v294_manifest.get("present")),
            "decision": v294_manifest.get("decision"),
        },
        "host": collect_host_metadata(),
        "captures": [asdict(capture) for capture in captures],
        "snapshot": snapshot,
        "checks": [asdict(check) for check in checks],
    }
    store.write_json("manifest.json", manifest)
    store.write_json("snapshot.json", snapshot)
    store.write_json("checks.json", {"checks": [asdict(check) for check in checks]})
    store.write_text("summary.md", render_summary(manifest, checks, snapshot))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
