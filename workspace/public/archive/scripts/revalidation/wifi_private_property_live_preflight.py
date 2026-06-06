#!/usr/bin/env python3
"""Read-only live preflight before private property namespace materialization."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v315-private-property-live-preflight")
DEFAULT_V314 = Path("tmp/wifi/v314-private-property-materialization-executor/manifest.json")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"


@dataclass
class PreflightCheck:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v314-manifest", type=Path, default=DEFAULT_V314)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
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


def has_all(text: str, needles: list[str]) -> bool:
    return all(needle in text for needle in needles)


def build_checks(args: argparse.Namespace,
                 v314: dict[str, Any],
                 captures: dict[str, Any]) -> list[PreflightCheck]:
    version = captures["version"]
    status = captures["status"]
    storage = captures["storage"]
    mountsd = captures["mountsd-status"]
    logpath = captures["logpath"]
    selftest = captures["selftest"]
    return [
        PreflightCheck(
            "v314-plan",
            "pass" if v314.get("decision") == "private-property-materialization-executor-plan-ready" and bool(v314.get("pass")) else "blocked",
            "blocker",
            f"decision={v314.get('decision')} pass={v314.get('pass')}",
            [str(v314.get("path", ""))],
        ),
        PreflightCheck(
            "native-version",
            "pass" if version.ok and args.expect_version in version.text else "blocked",
            "blocker",
            f"expected={args.expect_version} ok={version.ok}",
            ["version"],
        ),
        PreflightCheck(
            "native-status",
            "pass" if status.ok and has_all(status.text, ["storage: backend=sd", "writable=yes", "netservice: disabled", "selftest: pass="]) else "blocked",
            "blocker",
            "requires SD writable storage, disabled netservice, and selftest summary",
            ["status"],
        ),
        PreflightCheck(
            "selftest-no-fail",
            "pass" if selftest.ok and "fail=0" in selftest.text else "blocked",
            "blocker",
            "selftest must report fail=0 before any materialization work",
            ["selftest"],
        ),
        PreflightCheck(
            "storage-command",
            "pass" if storage.ok and has_all(storage.text, ["backend=sd", "rw=yes"]) else "blocked",
            "blocker",
            "storage command must confirm writable SD backend",
            ["storage"],
        ),
        PreflightCheck(
            "mountsd-command",
            "pass" if mountsd.ok and has_all(mountsd.text, ["match=yes", "state=mounted", "workspace=/mnt/sdext/a90"]) else "blocked",
            "blocker",
            "mountsd status must confirm expected mounted SD workspace",
            ["mountsd status"],
        ),
        PreflightCheck(
            "logpath-command",
            "pass" if logpath.ok and "/mnt/sdext/a90/logs/native-init.log" in logpath.text else "warn",
            "warning",
            "preferred log path should be on SD workspace",
            ["logpath"],
        ),
        PreflightCheck(
            "read-only-scope",
            "pass",
            "info",
            "v315 uses observation commands only; no run/cat redirection/write/mount/push/reboot",
            ["version", "status", "selftest", "storage", "mountsd status", "logpath"],
        ),
    ]


def decide(checks: list[PreflightCheck]) -> tuple[str, bool, str]:
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return "private-property-live-preflight-blocked", False, "blocked checks: " + ", ".join(blockers)
    return "private-property-live-preflight-ready", True, "read-only live preflight passed; materialization still requires a separate approved implementation"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v314 = load_json(args.v314_manifest)
    command_list = {
        "version": ["version"],
        "status": ["status"],
        "selftest": ["selftest"],
        "storage": ["storage"],
        "mountsd-status": ["mountsd", "status"],
        "logpath": ["logpath"],
    }
    captures = {name: run_capture(args, name, command, args.timeout) for name, command in command_list.items()}
    for name, capture in captures.items():
        store.write_text(f"commands/{name}.txt", capture.text if capture.text else capture.error + "\n")
    checks = build_checks(args, v314, captures)
    decision, pass_ok, reason = decide(checks)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": "v316 approved minimal private namespace copy/materialization proof" if pass_ok else "fix preflight blockers before any live materialization",
        "host": collect_host_metadata(),
        "inputs": {
            "v314": {"path": v314.get("path"), "present": bool(v314.get("present")), "decision": v314.get("decision"), "pass": v314.get("pass")},
        },
        "checks": [asdict(check) for check in checks],
        "captures": {name: capture_to_manifest(capture) for name, capture in captures.items()},
        "blocked_actions": [
            "write generated property files to device",
            "bind mount generated layout",
            "create /dev/socket/property_service",
            "start service-manager/hwservicemanager or Wi-Fi daemons",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
        "device_mutations": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"], "<br>".join(item["evidence"])] for item in manifest["checks"]]
    capture_rows = [[name, "ok" if item["ok"] else "fail", str(item["rc"]), item["status"], f"{item['duration_sec']:.3f}s"] for name, item in manifest["captures"].items()]
    return "\n".join([
        "# v315 Private Property Live Preflight",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence"], check_rows),
        "",
        "## Captures",
        "",
        markdown_table(["name", "ok", "rc", "status", "duration"], capture_rows),
        "",
        "## Blocked Actions",
        "",
        "\n".join(f"- `{item}`" for item in manifest["blocked_actions"]),
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
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
