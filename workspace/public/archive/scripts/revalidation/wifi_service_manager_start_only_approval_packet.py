#!/usr/bin/env python3
"""Generate a service-manager start-only approval packet after V371.

This packet is intentionally non-mutating.  It verifies that the V371 bounded
runtime repair smoke passed, refreshes read-only native state, and records the
exact boundary for a future V373 service-manager start-only runner.  It does not
start servicemanager, hwservicemanager, vndservicemanager, Wi-Fi HAL, wificond,
supplicant, hostapd, CNSS, or any Wi-Fi link operation.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v372-service-manager-start-only-approval-packet")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_V371 = Path("tmp/wifi/v371-runtime-repair-smoke-live-executor-run-20260520-012422/manifest.json")
DEFAULT_V366 = Path("tmp/wifi/v366-runtime-repair-smoke-live-approved/manifest.json")
DEFAULT_TOYBOX = "/cache/bin/toybox"
APPROVAL_PHRASE = (
    "approve v373 service-manager start-only smoke only; "
    "no Wi-Fi HAL start and no Wi-Fi bring-up"
)
FUTURE_RUNNER = "scripts/revalidation/wifi_service_manager_start_only_smoke.py"

LIVE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("selftest", ["selftest"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("ps", ["run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
    ("stat-servicemanager", ["stat", "/mnt/system/system/bin/servicemanager"], 10.0),
    ("stat-hwservicemanager", ["stat", "/mnt/system/system/bin/hwservicemanager"], 10.0),
    ("stat-vndservicemanager", ["stat", "/mnt/system/vendor/bin/vndservicemanager"], 10.0),
    ("stat-binder", ["stat", "/dev/binder"], 10.0),
    ("stat-hwbinder", ["stat", "/dev/hwbinder"], 10.0),
    ("stat-vndbinder", ["stat", "/dev/vndbinder"], 10.0),
    ("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
)

MANAGER_NAMES = ("servicemanager", "hwservicemanager", "vndservicemanager")
WIFI_LINK_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*)\b", re.IGNORECASE)


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
class ApprovalCheck:
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
    parser.add_argument("--v371-manifest", type=Path, default=DEFAULT_V371)
    parser.add_argument("--v366-manifest", type=Path, default=DEFAULT_V366)
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
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def collect_live(args: argparse.Namespace, store: EvidenceStore) -> list[CaptureSummary]:
    captures: list[CaptureSummary] = []
    store.mkdir("native")
    for name, command, timeout in LIVE_COMMANDS:
        capture = run_capture(args, name, command, timeout=timeout)
        text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
        rel = f"native/{safe_name(name)}.txt"
        store.write_text(rel, text)
        captures.append(CaptureSummary(
            name=name,
            command=capture.command,
            ok=capture.ok,
            rc=capture.rc,
            status=capture.status,
            duration_sec=capture.duration_sec,
            file=rel,
            error=capture.error,
        ))
    return captures


def capture_text(store: EvidenceStore, captures: list[CaptureSummary], name: str) -> str:
    for capture in captures:
        if capture.name != name:
            continue
        path = store.path(capture.file)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def capture_ok(captures: list[CaptureSummary], name: str) -> bool:
    return any(capture.name == name and capture.ok for capture in captures)


def manager_process_lines(ps_text: str) -> list[str]:
    lines: list[str] = []
    for line in ps_text.splitlines():
        if any(name in line for name in MANAGER_NAMES):
            lines.append(line.strip())
    return lines


def wifi_link_lines(netdev_text: str) -> list[str]:
    return [line.strip() for line in netdev_text.splitlines() if WIFI_LINK_RE.search(line)]


def add_check(checks: list[ApprovalCheck],
              name: str,
              ok: bool,
              detail: str,
              evidence: list[str] | None = None,
              severity: str = "blocker",
              next_step: str = "") -> None:
    checks.append(ApprovalCheck(
        name=name,
        status="pass" if ok else "blocked",
        severity=severity,
        detail=detail,
        evidence=evidence or [],
        next_step=next_step,
    ))


def build_checks(args: argparse.Namespace,
                 store: EvidenceStore,
                 captures: list[CaptureSummary],
                 v371: dict[str, Any],
                 v366: dict[str, Any]) -> list[ApprovalCheck]:
    checks: list[ApprovalCheck] = []
    version_text = capture_text(store, captures, "version")
    status_text = capture_text(store, captures, "status")
    selftest_text = capture_text(store, captures, "selftest")
    ps_text = capture_text(store, captures, "ps")
    netdev_text = capture_text(store, captures, "proc-net-dev")
    managers = manager_process_lines(ps_text)
    wifi_links = wifi_link_lines(netdev_text)

    add_check(
        checks,
        "v371-live-executor-pass",
        v371.get("decision") == "runtime-repair-smoke-live-executor-run-pass" and bool(v371.get("pass")),
        f"decision={v371.get('decision')} pass={v371.get('pass')}",
        [str(v371.get("path", ""))],
        next_step="V371 must prove temporary repair smoke and cleanup before service-manager start-only packet",
    )
    add_check(
        checks,
        "v371-router-next-ready",
        v371.get("router_decision") == "runtime-repair-smoke-router-service-runtime-next-ready",
        f"router_decision={v371.get('router_decision')}",
        [str(v371.get("path", ""))],
        next_step="router must target service-manager start-only approval packet",
    )
    add_check(
        checks,
        "v366-smoke-pass",
        v366.get("decision") == "runtime-repair-smoke-pass" and bool(v366.get("pass")),
        f"decision={v366.get('decision')} pass={v366.get('pass')}",
        [str(v366.get("path", ""))],
        next_step="V366 smoke must pass before widening to service-manager start-only",
    )
    add_check(
        checks,
        "native-version",
        args.expect_version in version_text,
        f"expect_version={args.expect_version}",
        [line for line in version_text.splitlines() if "A90 Linux init" in line][:3],
        severity="warning",
        next_step="refresh baseline if native boot image changed",
    )
    add_check(
        checks,
        "status-selftest-clean",
        capture_ok(captures, "status") and capture_ok(captures, "selftest") and "fail=0" in status_text and "fail=0" in selftest_text,
        "status/selftest rc=0 and fail=0 expected",
        [line.strip() for line in (status_text + "\n" + selftest_text).splitlines() if line.strip().startswith("selftest:")][:4],
        next_step="device must be healthy after V371 cleanup",
    )
    binary_ok = capture_ok(captures, "stat-servicemanager") and capture_ok(captures, "stat-hwservicemanager")
    add_check(
        checks,
        "core-service-manager-binaries-visible",
        binary_ok,
        f"servicemanager={capture_ok(captures, 'stat-servicemanager')} hwservicemanager={capture_ok(captures, 'stat-hwservicemanager')} vndservicemanager={capture_ok(captures, 'stat-vndservicemanager')}",
        [capture_text(store, captures, "stat-servicemanager").strip(), capture_text(store, captures, "stat-hwservicemanager").strip(), capture_text(store, captures, "stat-vndservicemanager").strip()][:3],
        next_step="future start-only runner must still resolve exact binaries before execution",
    )
    add_check(
        checks,
        "service-manager-processes-clean",
        not managers,
        f"process_count={len(managers)}",
        managers[:8],
        next_step="packet must start from a clean process surface",
    )
    add_check(
        checks,
        "wifi-link-surface-clean",
        not wifi_links,
        f"wifi_link_count={len(wifi_links)}",
        wifi_links[:8],
        next_step="start-only packet must not create wlan/p2p link surfaces",
    )
    binder_absent_ok = not capture_ok(captures, "stat-binder") and not capture_ok(captures, "stat-hwbinder") and not capture_ok(captures, "stat-vndbinder")
    add_check(
        checks,
        "temporary-binder-nodes-cleaned",
        binder_absent_ok,
        f"binder={capture_ok(captures, 'stat-binder')} hwbinder={capture_ok(captures, 'stat-hwbinder')} vndbinder={capture_ok(captures, 'stat-vndbinder')}",
        [capture_text(store, captures, "stat-binder").strip(), capture_text(store, captures, "stat-hwbinder").strip(), capture_text(store, captures, "stat-vndbinder").strip()],
        next_step="V373 runner must recreate temporary nodes only inside its bounded cleanup window",
    )
    return checks


def blockers(checks: list[ApprovalCheck]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v371 = load_json(args.v371_manifest)
    v366 = load_json(args.v366_manifest)
    captures = [] if args.command == "plan" else collect_live(args, store)
    checks = build_checks(args, store, captures, v371, v366) if captures else [
        ApprovalCheck(
            "plan-only",
            "pass",
            "info",
            "run mode performs read-only native captures and builds the approval packet",
            [],
            "run this script with command `run` before seeking operator approval",
        )
    ]
    blocking = blockers(checks)
    pass_ok = not blocking
    decision = "service-manager-start-only-approval-packet-ready" if pass_ok and args.command == "run" else (
        "service-manager-start-only-approval-packet-plan-ready" if args.command == "plan" else "service-manager-start-only-approval-packet-blocked"
    )
    reason = "approval packet ready; live start-only still requires separate exact approval" if decision.endswith("ready") else "blocked checks: " + ", ".join(blocking)
    future_command = (
        "python3 " + FUTURE_RUNNER + " "
        "--approval-phrase '" + APPROVAL_PHRASE + "' --apply --assume-yes run"
    )
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": "implement V373 service-manager start-only smoke runner" if args.command == "run" and pass_ok else "run V372 packet in live read-only mode",
        "host": collect_host_metadata(),
        "inputs": {
            "v371": {"path": v371.get("path"), "present": bool(v371.get("present")), "decision": v371.get("decision"), "pass": v371.get("pass"), "router_decision": v371.get("router_decision")},
            "v366": {"path": v366.get("path"), "present": bool(v366.get("present")), "decision": v366.get("decision"), "pass": v366.get("pass")},
        },
        "captures": [asdict(capture) for capture in captures],
        "checks": [asdict(check) for check in checks],
        "required_approval_phrase": APPROVAL_PHRASE,
        "future_runner": FUTURE_RUNNER,
        "future_command_template": future_command,
        "approved_scope_after_phrase": [
            "temporary recreate only the runtime nodes needed for service-manager start-only smoke",
            "start only servicemanager and hwservicemanager candidates needed by the runner contract",
            "start vndservicemanager only if a later preflight proves the binary exists and the runner contract requires it",
            "observe for a bounded timeout, then terminate/reap started processes",
            "cleanup temporary nodes and confirm service-manager/Wi-Fi surfaces are clean afterward",
        ],
        "explicitly_not_approved": [
            "Wi-Fi HAL service start",
            "wificond, supplicant, hostapd, cnss-daemon, or cnss_diag start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
            "unbounded daemon persistence or boot autostart flag changes",
        ],
        "live_execution_approved": False,
        "device_commands_executed": bool(captures),
        "device_mutations": False,
    }


def render_packet(manifest: dict[str, Any]) -> str:
    rows = [[item["name"], item["status"], item["severity"], item["detail"], "<br>".join(item["evidence"]), item["next_step"]] for item in manifest["checks"]]
    return "\n".join([
        "# v372 Service-Manager Start-Only Approval Packet",
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
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence", "next_step"], rows),
        "",
        "## Future Runner",
        "",
        f"- runner: `{manifest['future_runner']}`",
        "- command template:",
        "",
        "```bash",
        manifest["future_command_template"],
        "```",
        "",
        "## Approved Scope After Phrase",
        "",
        "\n".join(f"- {item}" for item in manifest["approved_scope_after_phrase"]),
        "",
        "## Explicitly Not Approved",
        "",
        "\n".join(f"- `{item}`" for item in manifest["explicitly_not_approved"]),
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("approval-packet.md", render_packet(manifest))
    store.write_text("summary.md", render_packet(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"approval_phrase: {manifest['required_approval_phrase']}")
    print(f"live_execution_approved: {manifest['live_execution_approved']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
