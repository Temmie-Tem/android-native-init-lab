#!/usr/bin/env python3
"""V364 no-scan/no-connect Wi-Fi HAL/service-manager readiness gate.

This collector is intentionally read-only on the active Wi-Fi path.  It may
perform native cmdv1 status/stat/ls/cat commands and ``mountsystem ro`` for
visibility, but it must not start HALs, service managers, supplicant, hostapd,
or change rfkill/link state.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v364-hal-service-readiness-gate")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_TOYBOX = "/cache/bin/toybox"

DEFAULT_V292 = Path("tmp/wifi/v292-binder-open-smoke-live-20260519-141358/manifest.json")
DEFAULT_V320 = Path("tmp/wifi/v320-private-property-lookup-proof-live-v11-mounted/manifest.json")
DEFAULT_V362 = Path("tmp/wifi/v362-cnss-start-only-live-20260520/manifest.json")
DEFAULT_V363 = Path("tmp/wifi/v363-bringup-preflight-20260520-001255/manifest.json")

LIVE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("wifiinv-full", ["wifiinv", "full"], 20.0),
    ("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
    ("sys-class-net", ["ls", "/sys/class/net"], 10.0),
    ("sys-class-rfkill", ["ls", "/sys/class/rfkill"], 10.0),
    ("ps", ["run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
    ("stat-dev-binder", ["stat", "/dev/binder"], 10.0),
    ("stat-dev-hwbinder", ["stat", "/dev/hwbinder"], 10.0),
    ("stat-dev-vndbinder", ["stat", "/dev/vndbinder"], 10.0),
    ("stat-property-socket", ["stat", "/dev/socket/property_service"], 10.0),
    ("stat-properties-area", ["stat", "/dev/__properties__"], 10.0),
    ("stat-selinux", ["stat", "/sys/fs/selinux"], 10.0),
    ("stat-linkerconfig", ["stat", "/linkerconfig/ld.config.txt"], 10.0),
    ("stat-system-linkerconfig", ["stat", "/mnt/system/linkerconfig/ld.config.txt"], 10.0),
    ("stat-apex", ["stat", "/mnt/system/apex"], 10.0),
    ("stat-system-servicemanager", ["stat", "/mnt/system/system/bin/servicemanager"], 10.0),
    ("stat-system-hwservicemanager", ["stat", "/mnt/system/system/bin/hwservicemanager"], 10.0),
    ("stat-vendor-vndservicemanager", ["stat", "/mnt/system/vendor/bin/vndservicemanager"], 10.0),
    ("stat-wificond", ["stat", "/mnt/system/system/bin/wificond"], 10.0),
    ("stat-wifi-hal-legacy", ["stat", "/mnt/system/vendor/bin/hw/android.hardware.wifi@1.0-service"], 10.0),
    ("stat-wifi-hal-ext", ["stat", "/mnt/system/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service"], 10.0),
    ("stat-wpa-supplicant", ["stat", "/mnt/system/vendor/bin/hw/wpa_supplicant"], 10.0),
    ("stat-hostapd", ["stat", "/mnt/system/vendor/bin/hw/hostapd"], 10.0),
    ("find-wifi-vintf", ["run", DEFAULT_TOYBOX, "find", "/mnt/system", "-maxdepth", "6", "-path", "*vintf*", "-o", "-name", "*manifest*"], 20.0),
    ("grep-wifi-vintf", ["run", DEFAULT_TOYBOX, "grep", "-RHiE", "wifi|supplicant|hostapd", "/mnt/system/system/etc/vintf", "/mnt/system/vendor/etc/vintf"], 20.0),
)

WLAN_NETDEV_RE = re.compile(r"(^|\s)(wlan\S*|swlan\S*|p2p\S*|wifi-aware\S*|wiphy\S*|phy\d+)(\s|:|$)", re.IGNORECASE)
CNSS_PROCESS_RE = re.compile(r"\b(cnss-daemon|cnss_diag)\b", re.IGNORECASE)
MANAGER_PROCESS_RE = re.compile(r"\b(servicemanager|hwservicemanager|vndservicemanager)\b")


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
class GateCheck:
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
    parser.add_argument("--v292-manifest", type=Path, default=DEFAULT_V292)
    parser.add_argument("--v320-manifest", type=Path, default=DEFAULT_V320)
    parser.add_argument("--v362-manifest", type=Path, default=DEFAULT_V362)
    parser.add_argument("--v363-manifest", type=Path, default=DEFAULT_V363)
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
        return {"present": False, "path": str(resolved), "decision": "missing", "pass": False}
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
        if capture.name == name:
            path = store.path(capture.file)
            return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return ""


def add_check(checks: list[GateCheck],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(GateCheck(name, status, severity, detail, evidence or [], next_step))


def source_checks(args: argparse.Namespace,
                  v292: dict[str, Any],
                  v320: dict[str, Any],
                  v362: dict[str, Any],
                  v363: dict[str, Any]) -> list[GateCheck]:
    checks: list[GateCheck] = []
    add_check(
        checks,
        "binder-open-primitive",
        "pass" if v292.get("decision") == "binder-open-only-smoke-pass" and v292.get("pass") else "missing",
        "info" if v292.get("decision") == "binder-open-only-smoke-pass" and v292.get("pass") else "blocker",
        f"decision={v292.get('decision', 'missing')}",
        [str(repo_path(args.v292_manifest))],
        "temporary Binder devnode/open primitive is useful but not a running service-manager model",
    )
    add_check(
        checks,
        "private-property-lookup",
        "pass" if v320.get("decision") == "private-property-lookup-getprop-pass" and v320.get("pass") else "missing",
        "info" if v320.get("decision") == "private-property-lookup-getprop-pass" and v320.get("pass") else "blocker",
        f"decision={v320.get('decision', 'missing')}",
        [str(repo_path(args.v320_manifest))],
        "read-only getprop works in private namespace, but mutable property_service is not proven",
    )
    add_check(
        checks,
        "cnss-start-only",
        "pass" if v362.get("decision") == "start-only-pass" and v362.get("pass") else "missing",
        "info" if v362.get("decision") == "start-only-pass" and v362.get("pass") else "blocker",
        f"decision={v362.get('decision', 'missing')}",
        [str(repo_path(args.v362_manifest))],
        "CNSS start-only is proven; do not infer wlan link readiness from it",
    )
    add_check(
        checks,
        "phase0-baseline",
        "pass" if v363.get("decision") == "wifi-bringup-phase0-live-baseline-ready" and v363.get("pass") else "missing",
        "info" if v363.get("decision") == "wifi-bringup-phase0-live-baseline-ready" and v363.get("pass") else "blocker",
        f"decision={v363.get('decision', 'missing')}",
        [str(repo_path(args.v363_manifest))],
        "Phase 0 must be current before service/HAL start-only planning",
    )
    return checks


def live_checks(store: EvidenceStore, captures: list[CaptureSummary], expect_version: str) -> list[GateCheck]:
    checks: list[GateCheck] = []
    version_text = capture_text(store, captures, "version")
    ps_text = capture_text(store, captures, "ps")
    proc_net = capture_text(store, captures, "proc-net-dev")
    sys_net = capture_text(store, captures, "sys-class-net")
    wifiinv = capture_text(store, captures, "wifiinv-full")
    rfkill = capture_text(store, captures, "sys-class-rfkill")
    manager_lines = [line.strip() for line in ps_text.splitlines() if MANAGER_PROCESS_RE.search(line)]
    cnss_lines = [line.strip() for line in ps_text.splitlines() if CNSS_PROCESS_RE.search(line)]
    wlan_surface = WLAN_NETDEV_RE.search(proc_net) or WLAN_NETDEV_RE.search(sys_net)
    wifi_rfkill = "wifi_like=yes" in wifiinv or re.search(r"\bwifi\b", rfkill, re.IGNORECASE)

    add_check(
        checks,
        "native-version",
        "pass" if expect_version in version_text else "warn",
        "info" if expect_version in version_text else "warning",
        f"expect_version={expect_version}",
        [line for line in version_text.splitlines() if "A90 Linux init" in line][:3],
        "refresh gate defaults when native boot image changes",
    )
    add_check(
        checks,
        "current-wlan-surface",
        "absent" if not wlan_surface else "present",
        "info" if not wlan_surface else "warning",
        "no wlan/wiphy surface" if not wlan_surface else "wlan/wiphy surface appeared",
        [],
        "HAL start-only planning should not assume link surface exists",
    )
    add_check(
        checks,
        "current-wifi-rfkill",
        "absent" if not wifi_rfkill else "present",
        "info" if not wifi_rfkill else "warning",
        "no Wi-Fi rfkill surface" if not wifi_rfkill else "Wi-Fi rfkill-like surface appeared",
        [],
        "rfkill writes remain out of scope",
    )
    add_check(
        checks,
        "current-cnss-process",
        "clean" if not cnss_lines else "present",
        "info" if not cnss_lines else "blocker",
        f"cnss_process_lines={len(cnss_lines)}",
        cnss_lines[:8],
        "postflight process table must be clean before another live probe",
    )
    binder_present = all(capture_ok(captures, name) for name in ("stat-dev-binder", "stat-dev-hwbinder", "stat-dev-vndbinder"))
    add_check(
        checks,
        "current-binder-devnodes",
        "present" if binder_present else "absent",
        "info" if binder_present else "blocker",
        "binder/hwbinder/vndbinder currently visible" if binder_present else "binder/hwbinder/vndbinder are not currently present",
        [],
        "either create a bounded temporary Binder namespace again or keep service-manager/HAL blocked",
    )
    add_check(
        checks,
        "current-service-manager-processes",
        "present" if manager_lines else "absent",
        "info" if manager_lines else "blocker",
        f"manager_process_lines={len(manager_lines)}",
        manager_lines[:8],
        "service-manager start-only must have its own supervisor/cleanup gate before HAL",
    )
    property_runtime = capture_ok(captures, "stat-property-socket") or capture_ok(captures, "stat-properties-area")
    add_check(
        checks,
        "current-property-runtime",
        "present" if property_runtime else "absent",
        "info" if property_runtime else "blocker",
        "property socket or area currently visible" if property_runtime else "no property socket or global property area currently visible",
        [],
        "read-only private getprop is not a mutable property_service runtime",
    )
    service_binary_names = (
        "stat-system-servicemanager",
        "stat-system-hwservicemanager",
        "stat-vendor-vndservicemanager",
        "stat-wificond",
        "stat-wifi-hal-legacy",
        "stat-wifi-hal-ext",
    )
    visible = [name for name in service_binary_names if capture_ok(captures, name)]
    add_check(
        checks,
        "service-binary-visibility",
        "partial" if visible else "absent",
        "warning" if visible else "blocker",
        f"visible={len(visible)}/{len(service_binary_names)}",
        visible,
        "binary visibility is prerequisite evidence, not execution readiness",
    )
    linkerconfig_ready = capture_ok(captures, "stat-linkerconfig") or capture_ok(captures, "stat-system-linkerconfig")
    add_check(
        checks,
        "linkerconfig-visibility",
        "present" if linkerconfig_ready else "missing",
        "warning" if linkerconfig_ready else "blocker",
        "linkerconfig visible in mounted/live path" if linkerconfig_ready else "linkerconfig not visible",
        [],
        "HAL/service-manager child needs explicit private namespace linker roots",
    )
    vintf_text = capture_text(store, captures, "grep-wifi-vintf")
    add_check(
        checks,
        "wifi-vintf-metadata",
        "present" if vintf_text.strip() else "missing",
        "warning" if vintf_text.strip() else "blocker",
        f"wifi_vintf_lines={len(vintf_text.splitlines())}",
        vintf_text.splitlines()[:12],
        "service publication needs VINTF/fqname mapping before HAL",
    )
    return checks


def check_blocks_start_only(check: GateCheck) -> bool:
    """Return whether a check blocks the next start-only approval packet.

    Most readiness checks block when a required prerequisite is absent/missing.
    The CNSS process cleanliness check is inverted: it blocks only when a
    leftover process is present after a previous bounded probe.
    """

    if check.severity != "blocker":
        return False
    if check.name == "current-cnss-process":
        return check.status == "present"
    return check.status in {"missing", "absent"}


def decide(command: str, checks: list[GateCheck]) -> tuple[bool, str, str, bool]:
    if command == "plan":
        return True, "hal-service-readiness-gate-plan-ready", "plan-only gate; no live device commands", False
    hard_blockers = [check.name for check in checks if check_blocks_start_only(check)]
    if hard_blockers:
        return True, "hal-service-readiness-blocked", "blocked by " + ", ".join(hard_blockers), False
    return True, "hal-service-start-only-candidate-ready", "no hard blocker found; requires separate start-only approval packet", True


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
        for check in manifest["checks"]
    ]
    return "\n".join([
        "# V364 Wi-Fi HAL/Service-Manager Readiness Gate",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- mode: `{manifest['mode']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- start_only_candidate: `{manifest['start_only_candidate']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "severity", "detail", "next"], rows),
        "",
        "## Guardrails",
        "",
        "- no service-manager execution",
        "- no Wi-Fi HAL, wificond, supplicant, hostapd, cnss-daemon, or cnss_diag execution",
        "- no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        "- no rfkill unblock, ICNSS bind/unbind, module load/unload, or firmware mutation",
        "- no Android partition write",
        "",
        "## Recommendation",
        "",
        "- If blocked, implement the smallest missing runtime primitive before any HAL start-only attempt.",
        "- If candidate-ready, create a separate approval packet before running any service process.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v292 = load_manifest(args.v292_manifest)
    v320 = load_manifest(args.v320_manifest)
    v362 = load_manifest(args.v362_manifest)
    v363 = load_manifest(args.v363_manifest)
    captures: list[CaptureSummary] = []
    checks = source_checks(args, v292, v320, v362, v363)
    if args.command == "run":
        captures = live_collect(args, store)
        checks.extend(live_checks(store, captures, args.expect_version))
    pass_ok, decision, reason, candidate = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "mode": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "start_only_candidate": candidate,
        "expect_version": args.expect_version,
        "inputs": {
            "v292_manifest": str(repo_path(args.v292_manifest)),
            "v320_manifest": str(repo_path(args.v320_manifest)),
            "v362_manifest": str(repo_path(args.v362_manifest)),
            "v363_manifest": str(repo_path(args.v363_manifest)),
        },
        "source_decisions": {
            "v292": v292.get("decision"),
            "v320": v320.get("decision"),
            "v362": v362.get("decision"),
            "v363": v363.get("decision"),
        },
        "captures": [asdict(capture) for capture in captures],
        "checks": [asdict(check) for check in checks],
        "host": collect_host_metadata(),
        "guardrails": [
            "no service-manager execution",
            "no Wi-Fi HAL, wificond, supplicant, hostapd, cnss-daemon, or cnss_diag execution",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill unblock, ICNSS bind/unbind, module load/unload, or firmware mutation",
            "no Android partition write",
        ],
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_json("checks.json", {"checks": manifest["checks"]})
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"start_only_candidate: {manifest['start_only_candidate']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
