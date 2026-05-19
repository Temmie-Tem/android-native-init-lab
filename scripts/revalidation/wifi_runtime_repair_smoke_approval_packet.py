#!/usr/bin/env python3
"""Generate a V366 runtime repair smoke approval packet.

The packet runs only safe gates: V366 preflight, V366 no-approval run refusal,
V366 no-approval cleanup refusal, and V367/V368 host-only regression.  It then
emits the exact approved command as an artifact.  It does not execute the
approved runtime repair smoke.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from wifi_runtime_repair_smoke import APPROVAL_PHRASE, DEFAULT_EXPECT_VERSION, DEFAULT_V365


DEFAULT_OUT_DIR = Path("tmp/wifi/v369-runtime-repair-smoke-approval-packet")
SMOKE_SCRIPT = Path("scripts/revalidation/wifi_runtime_repair_smoke.py")
REGRESSION_SCRIPT = Path("scripts/revalidation/wifi_runtime_repair_smoke_regression.py")
DEFAULT_LIVE_OUT_DIR = Path("tmp/wifi/v366-runtime-repair-smoke-live-approved")
DEFAULT_CLEANUP_OUT_DIR = Path("tmp/wifi/v366-runtime-repair-smoke-cleanup-approved")


@dataclass
class PacketCheck:
    name: str
    status: str
    detail: str
    evidence: str
    next_step: str


@dataclass
class ToolRun:
    name: str
    argv: list[str]
    rc: int
    stdout_path: str
    manifest_path: str
    decision: str
    pass_value: bool | None


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v365-manifest", type=Path, default=DEFAULT_V365)
    parser.add_argument("--live-out-dir", default=str(DEFAULT_LIVE_OUT_DIR))
    parser.add_argument("--cleanup-out-dir", default=str(DEFAULT_CLEANUP_OUT_DIR))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def script_argv(script: Path, out_dir: Path, *extra: str) -> list[str]:
    return [sys.executable, str(repo_path(script)), "--out-dir", str(repo_path(out_dir)), *extra]


def run_tool(store: EvidenceStore, name: str, argv: list[str]) -> ToolRun:
    result = subprocess.run(
        argv,
        cwd=repo_path(Path(".")),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
    )
    stdout_path = store.write_text(f"commands/{name}.txt", result.stdout)
    out_dir = Path(argv[argv.index("--out-dir") + 1])
    manifest_path = out_dir / "manifest.json"
    manifest = load_json(manifest_path)
    return ToolRun(
        name=name,
        argv=argv,
        rc=result.returncode,
        stdout_path=str(stdout_path),
        manifest_path=str(repo_path(manifest_path)),
        decision=str(manifest.get("decision") or "missing"),
        pass_value=bool(manifest.get("pass")) if manifest.get("pass") is not None else None,
    )


def check_status(condition: bool, pass_status: str = "pass", fail_status: str = "blocked") -> str:
    return pass_status if condition else fail_status


def manifest_steps(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    steps = manifest.get("steps")
    return steps if isinstance(steps, list) else []


def manifest_checks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    checks = manifest.get("checks")
    return checks if isinstance(checks, list) else []


def check_named(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    for check in manifest_checks(manifest):
        if check.get("name") == name:
            return check
    return {}


def command_text(parts: list[str]) -> str:
    return " ".join(shlex.quote(item) for item in parts)


def approved_run_command(args: argparse.Namespace) -> str:
    parts = [
        "python3",
        str(SMOKE_SCRIPT),
        "--out-dir",
        args.live_out_dir,
        "--approval-phrase",
        APPROVAL_PHRASE,
        "--apply",
        "--assume-yes",
        "run",
    ]
    return command_text(parts) + "\n"


def approved_cleanup_command(args: argparse.Namespace) -> str:
    parts = [
        "python3",
        str(SMOKE_SCRIPT),
        "--out-dir",
        args.cleanup_out_dir,
        "--approval-phrase",
        APPROVAL_PHRASE,
        "--apply",
        "--assume-yes",
        "cleanup",
    ]
    return command_text(parts) + "\n"


def render_rollback_checklist() -> str:
    return """# V366 Runtime Repair Smoke Rollback Checklist

## Before Approved Run

- Confirm bridge/NCM control is available.
- Confirm TWRP/recovery path is available.
- Confirm no `/dev/block/sda29`, `/dev/binder`, `/dev/hwbinder`, or `/dev/vndbinder` exists before the run.
- Confirm service-manager/CNSS processes are absent.
- Confirm no `wlan*` link surface exists.

## Approved Run Boundary

- Temporary node creation is limited to `/dev/block/sda29`, `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder`.
- The only probe is private property lookup through `/cache/bin/a90_android_execns_probe`.
- Cleanup and postflight must run in the same invocation.

## Not Approved

- service-manager, hwservicemanager, vndservicemanager start.
- Wi-Fi HAL, wificond, supplicant, hostapd, cnss-daemon, cnss_diag start.
- Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- rfkill unblock, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition writes.

## If The Run Fails Or Control Is Lost

- Preserve the evidence directory.
- Do not improvise daemon starts or rfkill/ICNSS writes.
- Reconnect ACM/NCM and run `version`, `status`, `selftest verbose`, and V366 cleanup only with exact cleanup approval.
"""


def build_checks(args: argparse.Namespace,
                 v365: dict[str, Any],
                 runs: list[ToolRun],
                 manifests: dict[str, dict[str, Any]],
                 approval_command: str,
                 cleanup_command: str) -> list[PacketCheck]:
    checks: list[PacketCheck] = []
    v365_ok = v365.get("decision") == "service-runtime-repair-packet-ready" and bool(v365.get("pass"))
    checks.append(PacketCheck(
        "v365-packet",
        check_status(v365_ok),
        f"decision={v365.get('decision')} pass={v365.get('pass')}",
        str(v365.get("path", "")),
        "V365 ready packet is required",
    ))
    run_by_name = {run.name: run for run in runs}
    expected = {
        "preflight": "runtime-repair-smoke-preflight-ready",
        "run-refusal": "runtime-repair-smoke-approval-required",
        "cleanup-refusal": "runtime-repair-smoke-cleanup-approval-required",
        "regression": "runtime-repair-smoke-regression-pass",
    }
    for name, decision in expected.items():
        item = run_by_name.get(name)
        ok = item is not None and item.rc == 0 and item.decision == decision and item.pass_value is True
        checks.append(PacketCheck(
            name,
            check_status(ok),
            f"rc={getattr(item, 'rc', None)} decision={getattr(item, 'decision', None)} pass={getattr(item, 'pass_value', None)}",
            getattr(item, "manifest_path", ""),
            f"expected {decision}",
        ))
    cleanup_steps = manifest_steps(manifests.get("cleanup-refusal", {}))
    checks.append(PacketCheck(
        "cleanup-refusal-no-steps",
        check_status(len(cleanup_steps) == 0),
        f"steps={len(cleanup_steps)}",
        run_by_name.get("cleanup-refusal").manifest_path if run_by_name.get("cleanup-refusal") else "",
        "cleanup refusal must not send device commands",
    ))
    preflight_manifest = manifests.get("preflight", {})
    preexisting = check_named(preflight_manifest, "preexisting-temp-nodes")
    checks.append(PacketCheck(
        "preexisting-temp-nodes-clean",
        check_status(preexisting.get("status") == "clean"),
        str(preexisting.get("detail")),
        run_by_name.get("preflight").manifest_path if run_by_name.get("preflight") else "",
        "target nodes must be absent before approval",
    ))
    service_clean = check_named(preflight_manifest, "post-service-process-clean")
    wifi_clean = check_named(preflight_manifest, "post-wifi-link-clean")
    checks.append(PacketCheck(
        "service-and-wifi-surface-clean",
        check_status(service_clean.get("status") == "clean" and wifi_clean.get("status") == "clean"),
        f"service={service_clean.get('detail')} wifi={wifi_clean.get('detail')}",
        run_by_name.get("preflight").manifest_path if run_by_name.get("preflight") else "",
        "no service-manager/CNSS process or Wi-Fi link before approval",
    ))
    approval_ok = APPROVAL_PHRASE in approval_command and "--apply" in approval_command and "--assume-yes" in approval_command and approval_command.rstrip().endswith("run")
    cleanup_ok = APPROVAL_PHRASE in cleanup_command and "--apply" in cleanup_command and "--assume-yes" in cleanup_command and cleanup_command.rstrip().endswith("cleanup")
    checks.append(PacketCheck(
        "approval-command-contract",
        check_status(approval_ok),
        approval_command.strip(),
        "approval-command.sh",
        "approved command must include exact phrase and mutation flags",
    ))
    checks.append(PacketCheck(
        "cleanup-command-contract",
        check_status(cleanup_ok),
        cleanup_command.strip(),
        "cleanup-command.sh",
        "cleanup command must include exact phrase and mutation flags",
    ))
    return checks


def decide(checks: list[PacketCheck]) -> tuple[str, bool, str, str]:
    blocked = [check.name for check in checks if check.status != "pass"]
    if blocked:
        return (
            "runtime-repair-smoke-approval-packet-blocked",
            False,
            "blocked checks: " + ", ".join(blocked),
            "repair approval packet blockers before live smoke",
        )
    return (
        "runtime-repair-smoke-approval-packet-ready",
        True,
        "approval packet ready; live execution is still not approved by this packet",
        "operator may provide exact phrase if they accept the listed V366 boundary",
    )


def render_packet(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["detail"], item["evidence"], item["next_step"]] for item in manifest["checks"]]
    run_rows = [[item["name"], item["rc"], item["decision"], item["pass_value"], item["manifest_path"]] for item in manifest["runs"]]
    return "\n".join([
        "# V366 Runtime Repair Smoke Approval Packet",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "evidence", "next"], check_rows),
        "",
        "## Gate Runs",
        "",
        markdown_table(["name", "rc", "decision", "pass", "manifest"], run_rows),
        "",
        "## Approved Live Command",
        "",
        "```bash",
        manifest["approval_command"].rstrip(),
        "```",
        "",
        "## Approved Cleanup Command",
        "",
        "```bash",
        manifest["cleanup_command"].rstrip(),
        "```",
        "",
        "## Required Exact Approval Phrase",
        "",
        f"`{manifest['approval_phrase']}`",
        "",
        "## Explicitly Not Approved",
        "",
        "\n".join(f"- {item}" for item in manifest["explicitly_not_approved"]),
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    store.mkdir("commands")
    packet_root = store.run_dir / "gates"
    v365 = load_json(args.v365_manifest)
    runs = [
        run_tool(store, "preflight", script_argv(SMOKE_SCRIPT, packet_root / "preflight", "preflight")),
        run_tool(store, "run-refusal", script_argv(SMOKE_SCRIPT, packet_root / "run-refusal", "run")),
        run_tool(store, "cleanup-refusal", script_argv(SMOKE_SCRIPT, packet_root / "cleanup-refusal", "cleanup")),
        run_tool(store, "regression", script_argv(REGRESSION_SCRIPT, packet_root / "regression", "run")),
    ]
    manifests = {run.name: load_json(Path(run.manifest_path)) for run in runs}
    approval_command = approved_run_command(args)
    cleanup_command = approved_cleanup_command(args)
    store.write_text("approval-command.sh", "#!/usr/bin/env bash\nset -euo pipefail\n" + approval_command)
    store.write_text("cleanup-command.sh", "#!/usr/bin/env bash\nset -euo pipefail\n" + cleanup_command)
    store.write_text("rollback-checklist.md", render_rollback_checklist())
    checks = build_checks(args, v365, runs, manifests, approval_command, cleanup_command)
    decision, pass_ok, reason, next_step = decide(checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "expect_version": args.expect_version,
        "v365_manifest": {"path": str(repo_path(args.v365_manifest)), "decision": v365.get("decision"), "pass": v365.get("pass")},
        "runs": [asdict(run) for run in runs],
        "checks": [asdict(check) for check in checks],
        "approval_phrase": APPROVAL_PHRASE,
        "approval_command": approval_command,
        "cleanup_command": cleanup_command,
        "live_execution_approved": False,
        "device_commands_executed": True,
        "device_mutations": False,
        "approved_scope_after_phrase": [
            "create temporary /dev/block/sda29, /dev/binder, /dev/hwbinder, /dev/vndbinder only when absent",
            "run private property lookup through /cache/bin/a90_android_execns_probe",
            "cleanup created temporary nodes in the same invocation",
            "verify no service-manager/CNSS process and no Wi-Fi link surface remains",
        ],
        "explicitly_not_approved": [
            "service-manager, hwservicemanager, or vndservicemanager start",
            "Wi-Fi HAL, wificond, supplicant, hostapd, cnss-daemon, or cnss_diag start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
            "cleanup without the exact approval phrase and mutation flags",
        ],
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("approval-packet.md", render_packet(manifest))
    store.write_text("summary.md", render_packet(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"live_execution_approved: {manifest['live_execution_approved']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"approval_phrase: {manifest['approval_phrase']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
