#!/usr/bin/env python3
"""V475 Android-readable private property mode repair.

This repairs an already-deployed V471 private property runtime root in place by
setting only Android-compatible read modes: 0755 directories and 0444 property
files. It does not replace global /dev/__properties__, create a property
service socket, start daemons, or bring Wi-Fi up.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90ctl import ProtocolResult, run_cmdv1_command
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v475-android-readable-property-mode-repair")
DEFAULT_V471 = Path("tmp/wifi/v471-extended-private-property-runtime/manifest.json")
DEFAULT_V472 = Path("tmp/wifi/v472-extended-property-runtime-live-fixed-20260521-021526/manifest.json")
REMOTE_WORKDIR = "/mnt/sdext/a90/private-property-v317/v471"
REMOTE_PROP_ROOT = REMOTE_WORKDIR + "/dev/__properties__"
TOYBOX = "/cache/bin/toybox"
DIR_MODE = "755"
FILE_MODE = "444"
APPROVAL_PHRASE = (
    "approve v475 Android-readable private property mode repair only; "
    "no daemon start and no Wi-Fi bring-up"
)
SAFE_REMOTE_RE = re.compile(r"^/[A-Za-z0-9_./:+-]+$")


@dataclass
class CommandRecord:
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
    parser.add_argument("--v471-manifest", type=Path, default=DEFAULT_V471)
    parser.add_argument("--v472-manifest", type=Path, default=DEFAULT_V472)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def validate_remote(path: str) -> bool:
    return (
        bool(path)
        and "\x00" not in path
        and "'" not in path
        and ".." not in Path(path).parts
        and path.startswith(REMOTE_PROP_ROOT + "/")
        and bool(SAFE_REMOTE_RE.match(path))
    )


def property_files(v471: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for item in v471.get("files", []):
        if not isinstance(item, dict):
            continue
        relative_path = str(item.get("relative_path") or "")
        if not relative_path.startswith("layout/dev/__properties__/"):
            continue
        remote_path = REMOTE_WORKDIR + "/" + relative_path.removeprefix("layout/")
        if validate_remote(remote_path):
            paths.append(remote_path)
    return paths


def write_command_record(store: EvidenceStore,
                         name: str,
                         argv: list[str],
                         result: ProtocolResult | None,
                         started: float,
                         error: str = "") -> CommandRecord:
    duration = time.monotonic() - started
    text = result.text if result is not None else error + "\n"
    path = store.write_text(f"commands/{name}.txt", text)
    ok = bool(result is not None and result.rc == 0 and result.status == "ok")
    return CommandRecord(name, " ".join(argv), ok, result.rc if result else None, result.status if result else "missing", duration, str(path.relative_to(store.run_dir)), error)


def device_cmd(args: argparse.Namespace,
               store: EvidenceStore,
               records: list[CommandRecord],
               name: str,
               argv: list[str]) -> ProtocolResult:
    started = time.monotonic()
    try:
        result = run_cmdv1_command(args.host, args.port, args.timeout, argv, retry_unsafe=False)
    except Exception as exc:  # noqa: BLE001 - preserve live evidence
        records.append(write_command_record(store, name, argv, None, started, str(exc)))
        raise
    records.append(write_command_record(store, name, argv, result, started))
    if result.rc != 0 or result.status != "ok":
        raise RuntimeError(f"device command failed: {name} rc={result.rc} status={result.status}")
    return result


def run_preflight(args: argparse.Namespace, store: EvidenceStore, records: list[CommandRecord]) -> None:
    device_cmd(args, store, records, "version", ["version"])
    device_cmd(args, store, records, "status", ["status"])
    device_cmd(args, store, records, "stat-remote-root", ["stat", REMOTE_PROP_ROOT])
    device_cmd(args, store, records, "stat-property-info", ["stat", REMOTE_PROP_ROOT + "/property_info"])


def run_repair(args: argparse.Namespace, store: EvidenceStore, records: list[CommandRecord], files: list[str]) -> None:
    for index, path in enumerate((REMOTE_WORKDIR, REMOTE_WORKDIR + "/dev", REMOTE_PROP_ROOT), start=1):
        device_cmd(args, store, records, f"chmod-dir-{index}", ["run", TOYBOX, "chmod", DIR_MODE, path])
    for index, path in enumerate(files, start=1):
        device_cmd(args, store, records, f"chmod-file-{index:02d}", ["run", TOYBOX, "chmod", FILE_MODE, path])
    device_cmd(args, store, records, "stat-after-property-info", ["stat", REMOTE_PROP_ROOT + "/property_info"])
    device_cmd(args, store, records, "stat-after-version-prop", ["stat", REMOTE_PROP_ROOT + "/u:object_r:property_service_version_prop:s0"])


def build_checks(args: argparse.Namespace,
                 v471: dict[str, Any],
                 v472: dict[str, Any],
                 files: list[str],
                 records: list[CommandRecord],
                 live_error: str) -> list[Check]:
    failed = [record.name for record in records if not record.ok]
    return [
        Check(
            "v471-layout",
            "pass" if v471.get("decision") == "v471-extended-private-property-runtime-ready" and bool(v471.get("pass")) else "blocked",
            "blocker",
            f"decision={v471.get('decision')} pass={v471.get('pass')}",
            [str(v471.get("path", ""))],
            "regenerate V471 layout",
        ),
        Check(
            "v472-deploy",
            "pass" if v472.get("decision") == "v472-extended-property-runtime-lookup-pass" and bool(v472.get("pass")) else "warn",
            "warning",
            f"decision={v472.get('decision')} pass={v472.get('pass')}",
            [str(v472.get("path", ""))],
            "refresh V472 deploy if remote root was removed",
        ),
        Check(
            "property-file-list",
            "pass" if files else "blocked",
            "blocker",
            f"files={len(files)}",
            files[:4],
            "V471 manifest must contain layout files",
        ),
        Check(
            "approval-gate",
            "pass" if approved(args) else "needs-operator",
            "approval",
            f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
            [APPROVAL_PHRASE],
            "provide exact approval phrase before chmod repair",
        ),
        Check(
            "device-commands",
            "pass" if not failed and not live_error else "blocked",
            "blocker",
            f"failed={len(failed)} error={live_error[:120]}",
            failed[:8],
            "inspect evidence and retry from clean native control",
        ),
    ]


def decide(args: argparse.Namespace, checks: list[Check], live_error: str) -> tuple[str, bool, str, str]:
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    approvals = [check.name for check in checks if check.severity == "approval" and check.status != "pass"]
    if args.command == "plan":
        return "v475-android-readable-property-mode-plan-ready", True, "plan generated without device command execution", "run preflight"
    if blockers:
        return "v475-android-readable-property-mode-blocked", False, "blocked checks: " + ", ".join(blockers), "resolve blockers before repair"
    if args.command == "preflight":
        return "v475-android-readable-property-mode-preflight-ready", True, "remote V471 root exists; repair still requires approval", "run approved mode repair"
    if approvals:
        return "v475-android-readable-property-mode-approval-required", False, "missing approval gates: " + ", ".join(approvals), "provide exact approval phrase"
    if live_error:
        return "v475-android-readable-property-mode-failed", False, live_error, "inspect chmod evidence"
    return "v475-android-readable-property-mode-repaired", True, "remote V471 private property root now uses Android-readable modes", "rerun Samsung registration proof against repaired V471 root"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    store.mkdir("commands")
    v471 = load_json(args.v471_manifest)
    v472 = load_json(args.v472_manifest)
    files = property_files(v471)
    records: list[CommandRecord] = []
    live_error = ""
    if args.command in ("preflight", "run"):
        try:
            run_preflight(args, store, records)
            if args.command == "run" and approved(args):
                run_repair(args, store, records, files)
        except Exception as exc:  # noqa: BLE001 - evidence carries details
            live_error = str(exc)
    checks = build_checks(args, v471, v472, files, records, live_error)
    decision, pass_ok, reason, next_step = decide(args, checks, live_error)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "remote_workdir": REMOTE_WORKDIR,
        "remote_property_root": REMOTE_PROP_ROOT,
        "remote_modes": {"directories": DIR_MODE, "property_files": FILE_MODE},
        "inputs": {
            "v471": {"path": v471.get("path"), "decision": v471.get("decision"), "pass": v471.get("pass")},
            "v472": {"path": v472.get("path"), "decision": v472.get("decision"), "pass": v472.get("pass")},
        },
        "checks": [asdict(check) for check in checks],
        "commands": [asdict(record) for record in records],
        "files": files,
        "live_error": live_error,
        "device_commands_executed": bool(records),
        "device_mutations": args.command == "run" and approved(args) and not live_error,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "blocked_actions": [
            "global /dev/__properties__ replacement",
            "global bind mount over /dev/__properties__",
            "property mutation or setprop-like writes",
            "service-manager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
            "persistent boot/autostart changes",
            "Android partition writes",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"]] for item in manifest["checks"]]
    command_rows = [[item["name"], "PASS" if item["ok"] else "FAIL", item["status"], item["file"]] for item in manifest["commands"]]
    return "\n".join([
        "# V475 Android-Readable Private Property Mode Repair",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail"], check_rows),
        "",
        "## Commands",
        "",
        markdown_table(["name", "ok", "status", "file"], command_rows) if command_rows else "- none",
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
    ]) + "\n"


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
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
