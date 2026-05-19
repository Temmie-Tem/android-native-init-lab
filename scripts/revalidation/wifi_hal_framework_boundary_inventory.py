#!/usr/bin/env python3
"""Inventory HAL/framework boundaries before Wi-Fi HAL execution.

The v288 collector is read-only.  It may issue native cmdv1 status/stat/ls/cat
commands and a safe ``mountsystem ro`` visibility step, but it never starts Wi-Fi
services, sends QRTR/QMI packets, toggles rfkill, or brings up interfaces.
"""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v288-hal-framework-boundary")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_V206 = Path("tmp/wifi/v206-android-icnss-cnss-map/manifest.json")
DEFAULT_V210 = Path("tmp/wifi/v210-vendor-asset-classifier/manifest.json")
DEFAULT_V287 = Path("tmp/wifi/v287-wifi-service-order-replay-model/manifest.json")
DEFAULT_TOYBOX = "/cache/bin/toybox"

ANDROID_WIFI_TERMS = re.compile(
    r"(wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|qca|qmi|hwbinder|binder|vintf)",
    re.IGNORECASE,
)

LIVE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("ls-dev", ["ls", "/dev"], 10.0),
    ("stat-dev-binder", ["stat", "/dev/binder"], 10.0),
    ("stat-dev-hwbinder", ["stat", "/dev/hwbinder"], 10.0),
    ("stat-dev-vndbinder", ["stat", "/dev/vndbinder"], 10.0),
    ("stat-dev-socket", ["stat", "/dev/socket"], 10.0),
    ("ls-dev-socket", ["run", DEFAULT_TOYBOX, "ls", "-la", "/dev/socket"], 10.0),
    ("stat-property-socket", ["stat", "/dev/socket/property_service"], 10.0),
    ("stat-properties-area", ["stat", "/dev/__properties__"], 10.0),
    ("stat-selinux", ["stat", "/sys/fs/selinux"], 10.0),
    ("stat-selinux-enforce", ["stat", "/sys/fs/selinux/enforce"], 10.0),
    ("ps", ["run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm"], 20.0),
    ("find-system-vintf", ["run", DEFAULT_TOYBOX, "find", "/mnt/system", "-maxdepth", "6", "-name", "*vintf*"], 20.0),
    ("grep-system-wifi-vintf", ["run", DEFAULT_TOYBOX, "grep", "-RHiE", "wifi|supplicant|hostapd", "/mnt/system/system/etc/vintf", "/mnt/system/vendor/etc/vintf"], 20.0),
    ("stat-system-hwservicemanager", ["stat", "/mnt/system/system/bin/hwservicemanager"], 10.0),
    ("stat-system-servicemanager", ["stat", "/mnt/system/system/bin/servicemanager"], 10.0),
    ("stat-system-vndservicemanager", ["stat", "/mnt/system/vendor/bin/vndservicemanager"], 10.0),
    ("stat-system-wificond", ["stat", "/mnt/system/system/bin/wificond"], 10.0),
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
class BoundaryCheck:
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
    parser.add_argument("--v206-manifest", type=Path, default=DEFAULT_V206)
    parser.add_argument("--v210-manifest", type=Path, default=DEFAULT_V210)
    parser.add_argument("--v287-manifest", type=Path, default=DEFAULT_V287)
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


def manifest_dir(manifest: dict[str, Any]) -> Path | None:
    path = manifest.get("path")
    if not isinstance(path, str):
        return None
    return Path(path).parent


def capture_text(manifest: dict[str, Any], name: str) -> str:
    base = manifest_dir(manifest)
    if base is None:
        return ""
    for capture in manifest.get("captures", []):
        if not isinstance(capture, dict) or capture.get("name") != name:
            continue
        rel = capture.get("file")
        if isinstance(rel, str):
            path = Path(rel)
            if not path.is_absolute():
                path = base / path
            if path.exists():
                return path.read_text(encoding="utf-8", errors="replace")
        text = capture.get("text")
        if isinstance(text, str):
            return text
    return ""


def focus_lines(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.startswith("$") and ANDROID_WIFI_TERMS.search(line)
    ]


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


def read_capture(store: EvidenceStore, captures: list[CaptureSummary], name: str) -> str:
    for capture in captures:
        if capture.name != name:
            continue
        path = store.path(capture.file)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def add_check(checks: list[BoundaryCheck],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(
        BoundaryCheck(
            name=name,
            status=status,
            severity=severity,
            detail=detail,
            evidence=evidence or [],
            next_step=next_step,
        )
    )


def android_boundary_checks(v206: dict[str, Any], v210: dict[str, Any], v287: dict[str, Any]) -> list[BoundaryCheck]:
    checks: list[BoundaryCheck] = []
    service_order = v287.get("service_order", []) if isinstance(v287.get("service_order"), list) else []
    hal_services = [item for item in service_order if isinstance(item, dict) and str(item.get("name", "")).startswith("vendor.wifi_hal")]
    wificond = [item for item in service_order if isinstance(item, dict) and item.get("name") == "wificond"]
    vintf_lines = focus_lines(capture_text(v206, "vintf-wifi-hal"))
    process_lines = focus_lines(capture_text(v206, "processes-wifi"))
    socket_lines = focus_lines(capture_text(v206, "devnodes-sockets-wifi"))
    vintf_hits = v210.get("classification", {}).get("vintf_hits", [])

    add_check(
        checks,
        "android-hal-service-metadata",
        "present" if hal_services else "missing",
        "info" if hal_services else "blocker",
        f"hal_service_count={len(hal_services)} wificond_count={len(wificond)}",
        [str(item.get("name")) for item in hal_services + wificond],
        "keep service execution blocked until native runtime boundaries are known",
    )
    add_check(
        checks,
        "android-vintf-wifi-hal",
        "present" if vintf_lines or vintf_hits else "missing",
        "info" if vintf_lines or vintf_hits else "blocker",
        f"v206_vintf_lines={len(vintf_lines)} v210_vintf_hits={len(vintf_hits) if isinstance(vintf_hits, list) else 0}",
        (vintf_lines[:8] + [str(item) for item in (vintf_hits[:4] if isinstance(vintf_hits, list) else [])]),
        "map HAL fqnames to native VINTF visibility before HAL execution",
    )
    add_check(
        checks,
        "android-hal-process-domains",
        "present" if process_lines else "missing",
        "info" if process_lines else "warning",
        f"process_evidence_lines={len(process_lines)}",
        process_lines[:10],
        "preserve as Android reference; native init does not recreate these SELinux domains",
    )
    add_check(
        checks,
        "android-wifi-socket-surface",
        "present" if socket_lines else "missing",
        "info" if socket_lines else "warning",
        f"socket_evidence_lines={len(socket_lines)}",
        socket_lines[:8],
        "compare against native /dev/socket visibility",
    )
    return checks


def native_boundary_checks(store: EvidenceStore, captures: list[CaptureSummary], expect_version: str) -> list[BoundaryCheck]:
    checks: list[BoundaryCheck] = []
    version_text = read_capture(store, captures, "version")
    ps_text = read_capture(store, captures, "ps")
    socket_text = read_capture(store, captures, "ls-dev-socket")
    vintf_text = read_capture(store, captures, "grep-system-wifi-vintf")

    add_check(
        checks,
        "native-version",
        "present" if expect_version in version_text else "mismatch",
        "info" if expect_version in version_text else "warning",
        f"expect_version={expect_version}",
        [line for line in version_text.splitlines() if "A90 Linux init" in line][:3],
        "refresh baseline if device build changed",
    )
    for node in ("binder", "hwbinder", "vndbinder"):
        capture_name = f"stat-dev-{node}"
        add_check(
            checks,
            f"native-dev-{node}",
            "present" if capture_ok(captures, capture_name) else "absent",
            "warning" if capture_ok(captures, capture_name) else "blocker",
            f"/dev/{node} {'visible' if capture_ok(captures, capture_name) else 'not visible'}",
            read_capture(store, captures, capture_name).splitlines()[:4],
            "inventory binder driver feasibility before HAL execution",
        )
    manager_hits = [
        line.strip()
        for line in ps_text.splitlines()
        if any(term in line for term in ("servicemanager", "hwservicemanager", "vndservicemanager"))
    ]
    manager_binaries = [
        name
        for name in ("stat-system-hwservicemanager", "stat-system-servicemanager", "stat-system-vndservicemanager")
        if capture_ok(captures, name)
    ]
    add_check(
        checks,
        "native-service-manager-binaries",
        "present" if manager_binaries else "absent",
        "warning" if manager_binaries else "blocker",
        f"visible_manager_binaries={len(manager_binaries)}",
        manager_binaries,
        "binary visibility is not enough; live service manager process/model is still required",
    )
    add_check(
        checks,
        "native-service-manager-processes",
        "present" if manager_hits else "absent",
        "warning" if manager_hits else "blocker",
        f"manager_process_count={len(manager_hits)}",
        manager_hits[:8],
        "model or provide service manager boundary before HAL/wificond execution",
    )
    property_present = capture_ok(captures, "stat-property-socket") or capture_ok(captures, "stat-properties-area")
    add_check(
        checks,
        "native-property-runtime",
        "present" if property_present else "absent",
        "warning" if property_present else "blocker",
        "property socket or serialized property area visibility",
        (
            read_capture(store, captures, "stat-property-socket").splitlines()[:3]
            + read_capture(store, captures, "stat-properties-area").splitlines()[:3]
        ),
        "do not emulate mutable property service in Wi-Fi path without a separate plan",
    )
    wifi_socket_hits = [
        line.strip()
        for line in socket_text.splitlines()
        if any(term in line.lower() for term in ("wifi", "wlan", "wpa", "hostapd", "supplicant"))
    ]
    add_check(
        checks,
        "native-wifi-socket-surface",
        "present" if wifi_socket_hits else "absent",
        "warning" if wifi_socket_hits else "info",
        f"wifi_socket_count={len(wifi_socket_hits)}",
        wifi_socket_hits[:8],
        "socket creation remains service-owned; do not pre-create active sockets yet",
    )
    selinux_present = capture_ok(captures, "stat-selinux")
    add_check(
        checks,
        "native-selinux-surface",
        "present" if selinux_present else "absent",
        "warning" if selinux_present else "blocker",
        "/sys/fs/selinux visibility",
        read_capture(store, captures, "stat-selinux").splitlines()[:4],
        "HAL domain assumptions remain unresolved in native init",
    )
    add_check(
        checks,
        "native-system-vintf-wifi",
        "present" if capture_ok(captures, "grep-system-wifi-vintf") and vintf_text.strip() else ("partial-present" if focus_lines(vintf_text) else "absent"),
        "warning",
        f"wifi_vintf_lines={len(focus_lines(vintf_text))}",
        focus_lines(vintf_text)[:8],
        "vendor VINTF visibility still needs namespace/root mapping before HAL execution",
    )
    add_check(
        checks,
        "native-wificond-binary",
        "present" if capture_ok(captures, "stat-system-wificond") else "absent",
        "warning" if capture_ok(captures, "stat-system-wificond") else "blocker",
        "/system/bin/wificond visibility after read-only system mount",
        read_capture(store, captures, "stat-system-wificond").splitlines()[:4],
        "binary visibility is not execution readiness without framework/property/binder boundaries",
    )
    return checks


def classify(input_errors: list[str], checks: list[BoundaryCheck], mode: str) -> tuple[bool, str, str]:
    if input_errors:
        return False, "hal-framework-boundary-input-missing", "; ".join(input_errors)
    unsafe = [
        check.name
        for check in checks
        if check.name.startswith("unsafe-") and check.status != "absent"
    ]
    if unsafe:
        return False, "hal-framework-boundary-unsafe-policy", ", ".join(unsafe)
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status in {"absent", "missing", "mismatch"}]
    if mode == "run" and blockers:
        return True, "hal-framework-boundary-native-blocked", "native HAL/framework blockers: " + ", ".join(blockers)
    return True, "hal-framework-boundary-inventory-ready", "HAL/framework boundary inventory completed"


def render_summary(manifest: dict[str, Any]) -> str:
    rows = []
    for check in manifest["checks"]:
        rows.append([
            check["name"],
            check["status"],
            check["severity"],
            check["detail"],
            check["next_step"],
        ])
    lines = [
        "# v288 HAL / Framework Boundary Inventory\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- mode: `{manifest['mode']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: {manifest['reason']}\n\n",
        "## Boundary Checks\n\n",
        markdown_table(["check", "status", "severity", "detail", "next"], rows),
        "\n\n## Guardrails\n\n",
    ]
    lines.extend(f"- {item}\n" for item in manifest["guardrails"])
    lines.extend([
        "\n## Recommendation\n\n",
        "- Do not execute Wi-Fi HAL or `wificond` until binder, service manager, property, VINTF, SELinux, and namespace blockers are resolved.\n",
        "- If the native run is blocked, v289 should narrow the largest missing boundary rather than start a daemon.\n",
    ])
    return "".join(lines)


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v206 = load_manifest(args.v206_manifest)
    v210 = load_manifest(args.v210_manifest)
    v287 = load_manifest(args.v287_manifest)
    input_errors: list[str] = []
    for name, manifest, expected in (
        ("v206", v206, "ready-for-native-preflight-plan"),
        ("v210", v210, "firmware-path-policy-needed"),
        ("v287", v287, "wifi-service-order-replay-model-ready"),
    ):
        if not manifest.get("present"):
            input_errors.append(f"{name} missing: {manifest.get('path')}")
        elif manifest.get("decision") != expected:
            input_errors.append(f"{name} decision expected {expected}, got {manifest.get('decision')}")
        elif manifest.get("pass") is not True:
            input_errors.append(f"{name} pass expected true")

    captures: list[CaptureSummary] = []
    checks = android_boundary_checks(v206, v210, v287) if not input_errors else []
    if args.command == "run" and not input_errors:
        captures = live_collect(args, store)
        checks.extend(native_boundary_checks(store, captures, args.expect_version))
    pass_ok, decision, reason = classify(input_errors, checks, args.command)
    manifest: dict[str, Any] = {
        "created": now_iso(),
        "mode": args.command,
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "inputs": {
            "v206_manifest": str(repo_path(args.v206_manifest)),
            "v210_manifest": str(repo_path(args.v210_manifest)),
            "v287_manifest": str(repo_path(args.v287_manifest)),
        },
        "source_decisions": {
            "v206": v206.get("decision"),
            "v210": v210.get("decision"),
            "v287": v287.get("decision"),
        },
        "input_errors": input_errors,
        "checks": [asdict(check) for check in checks],
        "captures": [asdict(capture) for capture in captures],
        "execution_ready": False,
        "next_recommendation": "v289 narrow missing binder/service-manager/property boundary before HAL or wificond execution",
        "guardrails": [
            "no service execution",
            "no cnss-daemon/cnss_diag/Wi-Fi HAL/wificond/supplicant/hostapd start",
            "no QMI payload",
            "no QRTR packet",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill write",
            "no ICNSS bind/unbind or driver_override",
            "no firmware path mutation",
            "no reboot/recovery/poweroff",
            "no Android partition write",
            "mountsystem ro allowed only for read-only visibility",
        ],
        "host_metadata": collect_host_metadata(),
    }
    return manifest


def main() -> int:
    args = parse_args()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_json("boundary-checks.json", {"checks": manifest["checks"]})
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {out_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
