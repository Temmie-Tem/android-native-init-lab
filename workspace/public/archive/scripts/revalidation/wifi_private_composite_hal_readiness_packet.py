#!/usr/bin/env python3
"""V404 private-composite Wi-Fi HAL readiness packet.

This packet is non-mutating. It refreshes read-only native evidence after V403
proved service-manager and hwservicemanager can run in the helper-owned private
namespace. It decides whether the next useful work is a composite helper/runner
that supervises service-manager + hwservicemanager while later testing a Wi-Fi
HAL start-only candidate.

It does not start Wi-Fi HAL, wificond, supplicant, hostapd, CNSS/diag, scan,
connect, DHCP, routing, or link-up flows.
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
from wifi_service_manager_start_only_approval_packet import DEFAULT_EXPECT_VERSION


DEFAULT_OUT_DIR = Path("tmp/wifi/v404-private-composite-hal-readiness-packet")
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "55f83cfa43ebc69ab37b3181262fbdf0e3ed6b5b11f0e41e63d3b56e7ea080e6"
DEFAULT_V402_PROOF = Path("tmp/wifi/v402-private-selinux-surface-live-20260520-084832/manifest.json")
DEFAULT_V403_LIVE = Path("tmp/wifi/v403-service-manager-start-only-retry-live-20260520-085702/manifest.json")
DEFAULT_V403_POST = Path("tmp/wifi/v403-service-manager-start-only-postflight-20260520-085747/manifest.json")
DEFAULT_V210 = Path("tmp/wifi/v210-vendor-asset-classifier/manifest.json")
DEFAULT_V216 = Path("tmp/wifi/v216-service-replay-model/manifest.json")
DEFAULT_V287 = Path("tmp/wifi/v287-wifi-service-order-replay-model/manifest.json")
DEFAULT_V364_REFRESH = Path("tmp/wifi/v403-post-service-manager-hal-readiness-refresh-20260520-085835/manifest.json")

WIFI_LINK_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wiphy\d+|phy\d+)\b", re.IGNORECASE)
MANAGER_RE = re.compile(r"\b(servicemanager|hwservicemanager|vndservicemanager)\b")
WIFI_PROCESS_RE = re.compile(
    r"\b(android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi|wificond|wpa_supplicant|hostapd|cnss-daemon|cnss_diag)\b",
    re.IGNORECASE,
)

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("selftest", ["selftest"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("wifiinv-full", ["wifiinv", "full"], 20.0),
    ("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
    ("ps", ["run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
    ("stat-helper", ["stat", DEFAULT_HELPER], 10.0),
    ("sha-helper", ["run", DEFAULT_TOYBOX, "sha256sum", DEFAULT_HELPER], 10.0),
    ("helper-usage", ["run", DEFAULT_HELPER], 10.0),
    ("stat-servicemanager", ["stat", "/mnt/system/system/bin/servicemanager"], 10.0),
    ("stat-hwservicemanager", ["stat", "/mnt/system/system/bin/hwservicemanager"], 10.0),
    ("stat-vndservicemanager", ["stat", "/mnt/system/vendor/bin/vndservicemanager"], 10.0),
    ("stat-wifi-hal-ext", ["stat", "/mnt/system/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service"], 10.0),
    ("stat-wifi-hal-legacy", ["stat", "/mnt/system/vendor/bin/hw/android.hardware.wifi@1.0-service"], 10.0),
    ("stat-wifi-hal-ext-rc", ["stat", "/mnt/system/vendor/etc/init/vendor.samsung.hardware.wifi@2.0-service.rc"], 10.0),
    ("stat-wifi-hal-legacy-rc", ["stat", "/mnt/system/vendor/etc/init/android.hardware.wifi@1.0-service.rc"], 10.0),
    ("stat-wifi-hal-ext-vintf", ["stat", "/mnt/system/vendor/etc/vintf/manifest/vendor.samsung.hardware.wifi@2.0-service.xml"], 10.0),
    ("stat-wifi-hal-legacy-vintf", ["stat", "/mnt/system/vendor/etc/vintf/manifest/android.hardware.wifi@1.0-service.xml"], 10.0),
    ("stat-wificond", ["stat", "/mnt/system/system/bin/wificond"], 10.0),
    ("grep-wifi-vintf", ["run", DEFAULT_TOYBOX, "grep", "-RHiE", "android.hardware.wifi|vendor.samsung.hardware.wifi|supplicant|hostapd", "/mnt/system/system/etc/vintf", "/mnt/system/vendor/etc/vintf"], 20.0),
)


@dataclass
class Step:
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


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--v402-proof-manifest", type=Path, default=DEFAULT_V402_PROOF)
    parser.add_argument("--v403-live-manifest", type=Path, default=DEFAULT_V403_LIVE)
    parser.add_argument("--v403-postflight-manifest", type=Path, default=DEFAULT_V403_POST)
    parser.add_argument("--v210-manifest", type=Path, default=DEFAULT_V210)
    parser.add_argument("--v216-manifest", type=Path, default=DEFAULT_V216)
    parser.add_argument("--v287-manifest", type=Path, default=DEFAULT_V287)
    parser.add_argument("--v364-refresh-manifest", type=Path, default=DEFAULT_V364_REFRESH)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved), "decision": "missing", "pass": False}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def run_read_only(args: argparse.Namespace, store: EvidenceStore) -> list[Step]:
    store.mkdir("native")
    steps: list[Step] = []
    for name, command, timeout in READ_ONLY_COMMANDS:
        command = [args.helper if item == DEFAULT_HELPER else item for item in command]
        record = run_capture(args, name, command, timeout=timeout)
        text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
        rel = f"native/{safe_name(name)}.txt"
        store.write_text(rel, text)
        steps.append(Step(name, record.command, record.ok, record.rc, record.status, record.duration_sec, rel, record.error))
    return steps


def step_text(store: EvidenceStore, steps: list[Step], name: str) -> str:
    for step in steps:
        if step.name == name:
            path = store.path(step.file)
            return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return ""


def step_ok(steps: list[Step], name: str) -> bool:
    return any(step.name == name and step.ok for step in steps)


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def input_checks(v402: dict[str, Any], v403: dict[str, Any], v403_post: dict[str, Any],
                 v210: dict[str, Any], v216: dict[str, Any], v287: dict[str, Any],
                 v364: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    observations = v403.get("observations", []) if isinstance(v403.get("observations"), list) else []
    results = {str(item.get("target_profile")): item for item in observations if isinstance(item, dict)}
    classification = v210.get("classification", {}) if isinstance(v210.get("classification"), dict) else {}
    service_blocks = classification.get("service_blocks", []) if isinstance(classification.get("service_blocks"), list) else []
    service_names = {str(item.get("name")) for item in service_blocks if isinstance(item, dict)}
    vintf_hits = classification.get("vintf_hits", []) if isinstance(classification.get("vintf_hits"), list) else []
    add_check(checks, "v402-private-runtime-proof", "pass" if v402.get("decision") == "private-selinux-surface-proof-pass" and v402.get("pass") else "blocked", "blocker", f"decision={v402.get('decision')} pass={v402.get('pass')}", [str(v402.get("path", ""))], "V402 private runtime proof must pass")
    add_check(checks, "v403-service-manager-pass", "pass" if v403.get("decision") == "service-manager-start-only-live-pass" and v403.get("pass") else "blocked", "blocker", f"decision={v403.get('decision')} pass={v403.get('pass')}", [str(v403.get("path", ""))], "V403 service-manager pair must pass before HAL work")
    add_check(checks, "v403-target-results", "pass" if all(results.get(name, {}).get("helper_result") == "start-only-pass" for name in ("system-servicemanager", "system-hwservicemanager")) else "blocked", "blocker", f"targets={sorted(results)}", [], "both core managers must have start-only-pass")
    add_check(checks, "v403-no-wifi-bringup", "pass" if not v403.get("wifi_bringup_executed") else "blocked", "blocker", f"wifi_bringup_executed={v403.get('wifi_bringup_executed')}", [], "do not widen from a Wi-Fi-mutating baseline")
    post_clean = v403.get("postflight", {}).get("clean") if isinstance(v403.get("postflight"), dict) else False
    add_check(checks, "v403-postflight-clean", "pass" if post_clean and v403_post.get("pass") else "blocked", "blocker", f"live_postflight={post_clean} post_decision={v403_post.get('decision')}", [str(v403_post.get("path", ""))], "postflight must be clean before HAL packet")
    add_check(checks, "v210-vendor-assets", "pass" if v210.get("pass") else "blocked", "blocker", f"decision={v210.get('decision')} pass={v210.get('pass')}", [str(v210.get("path", ""))], "vendor HAL assets must be classified")
    add_check(
        checks,
        "v210-hal-service-assets",
        "pass" if {"vendor.wifi_hal_ext", "vendor.wifi_hal_legacy"} <= service_names and len(vintf_hits) > 0 else "blocked",
        "blocker",
        f"services={sorted(service_names)} vintf_hits={len(vintf_hits)}",
        [str(v210.get("path", ""))],
        "V210 must prove HAL binaries/init rc/VINTF exist in vendor-root evidence",
    )
    add_check(checks, "v216-service-model", "pass" if v216.get("decision") == "replay-model-ready" and v216.get("pass") else "blocked", "blocker", f"decision={v216.get('decision')} pass={v216.get('pass')}", [str(v216.get("path", ""))], "Android Wi-Fi service model must be available")
    add_check(checks, "v287-service-order", "pass" if v287.get("decision") == "wifi-service-order-replay-model-ready" and v287.get("pass") else "blocked", "blocker", f"decision={v287.get('decision')} pass={v287.get('pass')}", [str(v287.get("path", ""))], "service order model must be available")
    add_check(checks, "v364-global-gate-context", "pass" if v364.get("decision") == "hal-service-readiness-blocked" and v364.get("pass") else "warn", "info", f"decision={v364.get('decision')} reason={v364.get('reason')}", [str(v364.get("path", ""))], "old global gate is context only; V404 uses private runtime model")
    return checks


def live_checks(args: argparse.Namespace, store: EvidenceStore, steps: list[Step],
                v210: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    version = step_text(store, steps, "version")
    status = step_text(store, steps, "status")
    selftest = step_text(store, steps, "selftest")
    helper_sha = step_text(store, steps, "sha-helper")
    helper_usage = step_text(store, steps, "helper-usage")
    ps = step_text(store, steps, "ps")
    netdev = step_text(store, steps, "proc-net-dev")
    wifiinv = step_text(store, steps, "wifiinv-full")
    vintf = step_text(store, steps, "grep-wifi-vintf")
    managers = [line.strip() for line in ps.splitlines() if MANAGER_RE.search(line)]
    wifi_processes = [line.strip() for line in ps.splitlines() if WIFI_PROCESS_RE.search(line)]
    wifi_links = [line.strip() for line in (netdev + "\n" + wifiinv).splitlines() if WIFI_LINK_RE.search(line)]
    classification = v210.get("classification", {}) if isinstance(v210.get("classification"), dict) else {}
    missing_binaries = classification.get("missing_required_binaries", []) if isinstance(classification.get("missing_required_binaries"), list) else []
    missing_init_rc = classification.get("missing_required_init_rc", []) if isinstance(classification.get("missing_required_init_rc"), list) else []
    service_blocks = classification.get("service_blocks", []) if isinstance(classification.get("service_blocks"), list) else []
    service_by_name = {str(item.get("name")): item for item in service_blocks if isinstance(item, dict)}
    vintf_hits = classification.get("vintf_hits", []) if isinstance(classification.get("vintf_hits"), list) else []
    has_ext_vintf = any("vendor.samsung.hardware.wifi" in str(item) for item in vintf_hits)
    has_legacy_vintf = any("android.hardware.wifi" in str(item) for item in vintf_hits)

    add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning", f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3], "refresh baseline if native version changed")
    add_check(checks, "native-health", "pass" if step_ok(steps, "status") and step_ok(steps, "selftest") and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker", "status/selftest fail=0 expected", [], "fix native health before HAL packet")
    add_check(checks, "helper-v22", "pass" if args.helper_sha256 in helper_sha and "service-manager-start-only" in helper_usage else "blocked", "blocker", "helper v22 with service-manager mode expected", [line for line in helper_sha.splitlines() if args.helper in line][:2], "deploy v22 before V404")
    add_check(checks, "current-process-clean", "pass" if not managers and not wifi_processes else "blocked", "blocker", f"managers={len(managers)} wifi_processes={len(wifi_processes)}", (managers + wifi_processes)[:8], "do not plan HAL over active leftover processes")
    add_check(checks, "wifi-link-clean", "pass" if not wifi_links else "blocked", "blocker", f"wifi_link_lines={len(wifi_links)}", wifi_links[:8], "do not plan HAL over active Wi-Fi link")
    add_check(checks, "core-manager-binaries", "pass" if step_ok(steps, "stat-servicemanager") and step_ok(steps, "stat-hwservicemanager") else "blocked", "blocker", f"servicemanager={step_ok(steps, 'stat-servicemanager')} hwservicemanager={step_ok(steps, 'stat-hwservicemanager')}", [], "core service-manager binaries must be visible")
    ext_visible = step_ok(steps, "stat-wifi-hal-ext")
    legacy_visible = step_ok(steps, "stat-wifi-hal-legacy")
    add_check(
        checks,
        "wifi-hal-binaries",
        "pass" if not missing_binaries and {"vendor.wifi_hal_ext", "vendor.wifi_hal_legacy"} <= set(service_by_name) else "blocked",
        "blocker",
        f"v210_missing={len(missing_binaries)} current_ext={ext_visible} current_legacy={legacy_visible}",
        [str(service_by_name.get("vendor.wifi_hal_ext", {})), str(service_by_name.get("vendor.wifi_hal_legacy", {}))],
        "HAL binaries are expected via helper private vendor mount, not global /mnt/system/vendor",
    )
    add_check(
        checks,
        "wifi-hal-init-rc",
        "pass" if not missing_init_rc and {"vendor.wifi_hal_ext", "vendor.wifi_hal_legacy"} <= set(service_by_name) else "warn",
        "warning",
        f"v210_missing_init_rc={len(missing_init_rc)} current_ext_rc={step_ok(steps, 'stat-wifi-hal-ext-rc')} current_legacy_rc={step_ok(steps, 'stat-wifi-hal-legacy-rc')}",
        [],
        "init rc is available in vendor-root evidence; current global path may remain absent",
    )
    add_check(
        checks,
        "wifi-hal-vintf",
        "pass" if has_ext_vintf and has_legacy_vintf else "blocked",
        "blocker",
        f"v210_ext={has_ext_vintf} v210_legacy={has_legacy_vintf} current_ext_vintf={step_ok(steps, 'stat-wifi-hal-ext-vintf')} current_legacy_vintf={step_ok(steps, 'stat-wifi-hal-legacy-vintf')} grep_lines={len(vintf.splitlines())}",
        [str(item) for item in vintf_hits[:12]] + vintf.splitlines()[:12],
        "HAL fqname/VINTF evidence must be available from vendor-root or mounted system evidence",
    )
    add_check(checks, "wificond-binary", "pass" if step_ok(steps, "stat-wificond") else "warn", "warning", f"wificond={step_ok(steps, 'stat-wificond')}", [], "wificond remains later than first HAL candidate")
    add_check(checks, "first-hal-candidate", "pass", "info", "vendor.wifi_hal_ext is first candidate per V287 service-order model; legacy HAL remains sibling fallback", [], "V405 should target ext first unless new evidence changes service order")
    add_check(checks, "composite-helper-needed", "needed", "action", "current helper starts one target per invocation; HAL start-only needs one helper-owned namespace supervising service-manager + hwservicemanager + one HAL candidate", [], "implement V405 composite helper/runner before any HAL start")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status not in {"pass", "warn"}]


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v402 = load_json(args.v402_proof_manifest)
    v403 = load_json(args.v403_live_manifest)
    v403_post = load_json(args.v403_postflight_manifest)
    v210 = load_json(args.v210_manifest)
    v216 = load_json(args.v216_manifest)
    v287 = load_json(args.v287_manifest)
    v364 = load_json(args.v364_refresh_manifest)
    steps: list[Step] = []
    checks = input_checks(v402, v403, v403_post, v210, v216, v287, v364)
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "plan mode performs no live device commands", [], "run packet to refresh current read-only native evidence")
    else:
        steps = run_read_only(args, store)
        checks.extend(live_checks(args, store, steps, v210))
    blocking = blockers(checks)
    pass_ok = not blocking
    if args.command == "plan":
        decision = "v404-private-composite-hal-readiness-packet-plan-ready"
    elif pass_ok:
        decision = "v404-private-composite-hal-readiness-packet-ready"
    else:
        decision = "v404-private-composite-hal-readiness-packet-blocked"
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": "private-composite HAL readiness packet ready; HAL start still requires V405 implementation and separate approval" if pass_ok else "blocked by " + ", ".join(blocking),
        "next_step": "implement V405 composite helper/runner approval packet" if pass_ok and args.command == "run" else "run packet before V405 design",
        "host": collect_host_metadata(),
        "inputs": {
            "v402_proof": {"path": v402.get("path"), "decision": v402.get("decision"), "pass": v402.get("pass")},
            "v403_live": {"path": v403.get("path"), "decision": v403.get("decision"), "pass": v403.get("pass")},
            "v403_postflight": {"path": v403_post.get("path"), "decision": v403_post.get("decision"), "pass": v403_post.get("pass")},
            "v210": {"path": v210.get("path"), "decision": v210.get("decision"), "pass": v210.get("pass")},
            "v216": {"path": v216.get("path"), "decision": v216.get("decision"), "pass": v216.get("pass")},
            "v287": {"path": v287.get("path"), "decision": v287.get("decision"), "pass": v287.get("pass")},
            "v364_refresh": {"path": v364.get("path"), "decision": v364.get("decision"), "pass": v364.get("pass"), "reason": v364.get("reason")},
        },
        "steps": [asdict(step) for step in steps],
        "checks": [asdict(check) for check in checks],
        "first_hal_candidate": "vendor.wifi_hal_ext",
        "first_hal_binary": "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service",
        "sibling_hal_candidate": "vendor.wifi_hal_legacy",
        "sibling_hal_binary": "/vendor/bin/hw/android.hardware.wifi@1.0-service",
        "live_execution_approved": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "explicitly_not_approved": [
            "Wi-Fi HAL service start",
            "wificond, supplicant, hostapd, cnss-daemon, or cnss_diag start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
            "unbounded service-manager, hwservicemanager, or HAL persistence",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"], "<br>".join(item["evidence"]), item["next_step"]] for item in manifest["checks"]]
    step_rows = [[item["name"], "PASS" if item["ok"] else "FAIL", item["rc"], item["status"], item["file"]] for item in manifest["steps"]]
    return "\n".join([
        "# V404 Private-Composite Wi-Fi HAL Readiness Packet",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- first_hal_candidate: `{manifest['first_hal_candidate']}`",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence", "next"], check_rows),
        "",
        "## Native Steps",
        "",
        markdown_table(["step", "ok", "rc", "status", "file"], step_rows) if step_rows else "- none",
        "",
        "## Explicitly Not Approved",
        "",
        "\n".join(f"- `{item}`" for item in manifest["explicitly_not_approved"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"first_hal_candidate: {manifest['first_hal_candidate']}")
    print(f"live_execution_approved: {manifest['live_execution_approved']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
