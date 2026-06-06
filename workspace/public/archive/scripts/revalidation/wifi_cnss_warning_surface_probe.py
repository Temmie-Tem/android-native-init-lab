#!/usr/bin/env python3
"""Classify CNSS warning surfaces without starting Wi-Fi daemons."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, repo_path, run_capture  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v259-cnss-warning-surface")
DEFAULT_V258_MANIFEST = Path("tmp/wifi/v258-cnss-live-evidence-analysis/manifest.json")
HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")

READ_ONLY_COMMANDS: tuple[tuple[str, tuple[str, ...], float], ...] = (
    ("pidof-cnss-daemon", ("run", "/cache/bin/toybox", "pidof", "cnss-daemon"), 10.0),
    ("stat-dev-kmsg", ("stat", "/dev/kmsg"), 10.0),
    ("stat-property-socket", ("stat", "/dev/socket/property_service"), 10.0),
    ("stat-property-area", ("stat", "/dev/__properties__"), 10.0),
    ("stat-perfd-socket", ("stat", "/dev/socket/perfd"), 10.0),
    ("stat-vendor-perfd", ("stat", "/mnt/system/vendor/bin/perfd"), 10.0),
    ("stat-system-vendor-perfd", ("stat", "/mnt/system/system/vendor/bin/perfd"), 10.0),
    (
        "find-perfd-paths",
        ("run", "/cache/bin/toybox", "find", "/mnt/system", "-maxdepth", "8", "-name", "*perfd*"),
        30.0,
    ),
    (
        "grep-warning-refs",
        (
            "run",
            "/cache/bin/toybox",
            "grep",
            "-R",
            "-n",
            "-i",
            "-m",
            "160",
            "-E",
            "perfd|dev/kmsg|cnss-daemon|msm_performance|vendor.perf",
            "/mnt/system/vendor/etc",
            "/mnt/system/system/etc",
            "/mnt/system/odm/etc",
            "/mnt/system/product/etc",
        ),
        45.0,
    ),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def capture_rc(captures: dict[str, dict[str, Any]], name: str) -> int | None:
    value = captures.get(name, {}).get("rc")
    return value if isinstance(value, int) else None


def capture_text(captures: dict[str, dict[str, Any]], name: str) -> str:
    return str(captures.get(name, {}).get("text") or "")


def capture_ok(captures: dict[str, dict[str, Any]], name: str) -> bool:
    item = captures.get(name, {})
    return item.get("rc") == 0 and item.get("status") == "ok"


def stat_mode(text: str) -> str | None:
    match = re.search(r"mode=([0-7]{3,4})", text)
    return match.group(1) if match else None


def stat_uid_gid(text: str) -> tuple[str | None, str | None]:
    uid = re.search(r"uid=([0-9]+)", text)
    gid = re.search(r"gid=([0-9]+)", text)
    return (uid.group(1) if uid else None, gid.group(1) if gid else None)


def helper_has_kmsg_shell(source_path: Path) -> bool:
    path = repo_path(source_path)
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return "/dev/kmsg" in text or "kmsg" in text.lower()


def add_check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str, *, severity: str = "critical") -> None:
    checks.append({"name": name, "pass": passed, "severity": severity, "detail": detail})


def classify(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    v258_manifest = load_json(repo_path(args.v258_manifest))
    captures_list: list[dict[str, Any]] = []
    captures_by_name: dict[str, dict[str, Any]] = {}

    for name, command, timeout in READ_ONLY_COMMANDS:
        capture = run_capture(args, name, list(command), timeout=timeout)
        store.write_text(f"commands/{name}.txt", capture.text if capture.text else capture.error + "\n")
        data = capture_to_manifest(capture)
        captures_list.append(data)
        captures_by_name[name] = data

    helper_kmsg = helper_has_kmsg_shell(args.helper_source)
    pidof_absent = capture_rc(captures_by_name, "pidof-cnss-daemon") == 1
    dev_kmsg_text = capture_text(captures_by_name, "stat-dev-kmsg")
    dev_kmsg_mode = stat_mode(dev_kmsg_text)
    dev_kmsg_uid, dev_kmsg_gid = stat_uid_gid(dev_kmsg_text)
    property_socket_present = capture_ok(captures_by_name, "stat-property-socket")
    property_area_present = capture_ok(captures_by_name, "stat-property-area")
    perfd_socket_present = capture_ok(captures_by_name, "stat-perfd-socket")
    perfd_binary_present = capture_ok(captures_by_name, "stat-vendor-perfd") or capture_ok(captures_by_name, "stat-system-vendor-perfd")
    perfd_paths_text = capture_text(captures_by_name, "find-perfd-paths")
    perfd_paths_lines = [
        line.strip()
        for line in perfd_paths_text.splitlines()
        if line.strip().startswith("/mnt/system/")
    ]
    grep_text = capture_text(captures_by_name, "grep-warning-refs")

    checks: list[dict[str, Any]] = []
    add_check(checks, "v258-prerequisite", v258_manifest.get("decision") == "cnss-start-only-evidence-classified" and v258_manifest.get("pass") is True, f"decision={v258_manifest.get('decision')} pass={v258_manifest.get('pass')}")
    add_check(checks, "cnss-daemon-absent", pidof_absent, f"pidof rc={capture_rc(captures_by_name, 'pidof-cnss-daemon')}")
    add_check(checks, "dev-kmsg-observed", capture_ok(captures_by_name, "stat-dev-kmsg"), f"mode={dev_kmsg_mode} uid={dev_kmsg_uid} gid={dev_kmsg_gid}", severity="warning")
    add_check(checks, "property-surface-observed", property_socket_present or property_area_present, f"socket={property_socket_present} area={property_area_present}", severity="warning")
    add_check(checks, "perfd-surface-classified", True, f"binary={perfd_binary_present} socket={perfd_socket_present}", severity="warning")
    add_check(checks, "helper-kmsg-source-clean", not helper_kmsg, f"helper_source_contains_kmsg={helper_kmsg}", severity="warning")

    findings: list[dict[str, str]] = []
    if (perfd_binary_present or perfd_paths_lines) and not perfd_socket_present:
        findings.append({"code": "perfd-client-surface-present-socket-absent", "classification": "android-service-gap-warning", "detail": "perfd client references or binary exist but runtime socket is absent in native init"})
    elif not perfd_binary_present and not perfd_paths_lines:
        findings.append({"code": "perfd-surface-not-visible", "classification": "warning-context", "detail": "no perfd binary or client path found in checked mounted paths"})
    else:
        findings.append({"code": "perfd-runtime-present", "classification": "available", "detail": "perfd binary and socket are visible"})

    if not property_socket_present:
        findings.append({"code": "property-service-socket-absent", "classification": "android-service-gap-warning", "detail": "/dev/socket/property_service is absent in native init"})
    if property_area_present and not property_socket_present:
        findings.append({"code": "property-area-without-service", "classification": "read-only-area-only", "detail": "property area is visible but property service socket is not"})
    elif not property_area_present:
        findings.append({"code": "property-area-absent", "classification": "android-runtime-gap-warning", "detail": "/dev/__properties__ is absent"})

    if dev_kmsg_mode:
        findings.append({"code": "kmsg-mode", "classification": "permission-warning", "detail": f"/dev/kmsg mode={dev_kmsg_mode} uid={dev_kmsg_uid} gid={dev_kmsg_gid}; uid 1000 write denial is expected unless permissions are relaxed"})
    if not helper_kmsg:
        findings.append({"code": "shell-quote-noise-not-helper-source", "classification": "daemon-or-library-stderr", "detail": "helper source does not construct a /dev/kmsg shell command; quote noise is likely emitted by daemon/library logging path"})

    critical_pass = all(item["pass"] for item in checks if item["severity"] == "critical")
    manifest = {
        "created": now_iso(),
        "mode": "cnss-warning-surface-probe",
        "decision": "cnss-warning-surface-classified" if critical_pass else "cnss-warning-surface-incomplete",
        "pass": critical_pass,
        "reason": "warning surfaces classified without daemon execution" if critical_pass else "critical prerequisite failed",
        "out_dir": str(out_dir),
        "v258_manifest": str(repo_path(args.v258_manifest)),
        "host_metadata": collect_host_metadata(),
        "captures": captures_list,
        "checks": checks,
        "findings": findings,
        "surface": {
            "perfd_binary_present": perfd_binary_present,
            "perfd_socket_present": perfd_socket_present,
            "perfd_paths_lines": perfd_paths_lines[:80],
            "property_socket_present": property_socket_present,
            "property_area_present": property_area_present,
            "dev_kmsg": {"mode": dev_kmsg_mode, "uid": dev_kmsg_uid, "gid": dev_kmsg_gid},
            "helper_source_contains_kmsg": helper_kmsg,
            "grep_warning_refs_lines": [line for line in grep_text.splitlines() if line.strip()][:160],
        },
        "next_candidates": [
            "If perfd is needed, design a no-start perfd/property shim model before another broader live action.",
            "Run QRTR/QMI endpoint interaction probe without scan/connect/link-up.",
            "Patch helper instrumentation only if later evidence proves shell quote noise comes from helper-generated commands.",
        ],
        "guardrails": [
            "no cnss-daemon execution",
            "no cnss_diag execution",
            "no rfkill unblock or ICNSS bind/unbind",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# CNSS Warning Surface Probe\n\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- reason: `{manifest['reason']}`\n\n",
        "## Checks\n\n",
    ]
    for item in manifest["checks"]:
        lines.append(f"- {'PASS' if item['pass'] else 'FAIL'} `{item['name']}` ({item['severity']}): {item['detail']}\n")
    lines.append("\n## Findings\n\n")
    for item in manifest["findings"]:
        lines.append(f"- `{item['code']}` / `{item['classification']}`: {item['detail']}\n")
    lines.append("\n## Next Candidates\n\n")
    for item in manifest["next_candidates"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v258-manifest", type=Path, default=DEFAULT_V258_MANIFEST)
    parser.add_argument("--helper-source", type=Path, default=HELPER_SOURCE)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser.parse_args()


def main() -> int:
    manifest = classify(parse_args())
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {manifest['out_dir']}")
    for item in manifest["findings"]:
        print(f"finding: {item['code']} {item['classification']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
