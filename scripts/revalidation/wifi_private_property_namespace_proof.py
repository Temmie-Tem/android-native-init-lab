#!/usr/bin/env python3
"""Minimal private property namespace proof runner.

The live path is approval-gated. Without the exact v317 approval phrase and
explicit mutation flags this tool only produces plans/refusal evidence.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, repo_path
from a90ctl import ProtocolResult, run_cmdv1_command
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v317-private-property-namespace-proof")
DEFAULT_V312 = Path("tmp/wifi/v312-private-property-runtime-layout/manifest.json")
DEFAULT_V315 = Path("tmp/wifi/v315-private-property-live-preflight/manifest.json")
DEFAULT_V316 = Path("tmp/wifi/v316-private-property-live-approval/manifest.json")
DEFAULT_APPROVAL_REFRESH = Path("tmp/wifi/v327-private-property-approval-refresh/manifest.json")
DEFAULT_PRELIVE_GATE = Path("tmp/wifi/v336-v317-prelive-gate-audit/manifest.json")
APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"
REMOTE_WORKDIR = "/mnt/sdext/a90/private-property-v317"
REMOTE_PROP_PREFIX = REMOTE_WORKDIR + "/dev/__properties__"
TOYBOX = "/cache/bin/toybox"
CHUNK_SIZE = 1536
SAFE_DEVICE_PATH_RE = re.compile(r"^[A-Za-z0-9_./:+-]+$")
SHA256_RE = re.compile(r"\b([0-9a-fA-F]{64})\b")


@dataclass
class ProofCheck:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]


@dataclass
class LayoutFile:
    role: str
    relative_path: str
    local_path: str
    remote_path: str
    bytes: int
    sha256: str
    status: str


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
class TransferEstimate:
    files: int
    bytes: int
    chunk_size: int
    chunks: int
    estimated_commands: int
    max_script_chars: int
    status: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v312-manifest", type=Path, default=DEFAULT_V312)
    parser.add_argument("--v315-manifest", type=Path, default=DEFAULT_V315)
    parser.add_argument("--v316-manifest", type=Path, default=DEFAULT_V316)
    parser.add_argument("--approval-refresh-manifest", type=Path, default=DEFAULT_APPROVAL_REFRESH)
    parser.add_argument("--prelive-gate-manifest", type=Path, default=DEFAULT_PRELIVE_GATE)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--allow-device-mutation", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    subparsers.add_parser("cleanup")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_relative_path(path: str) -> bool:
    if not path or "\x00" in path:
        return False
    value = Path(path)
    return not value.is_absolute() and ".." not in value.parts and path.startswith("layout/dev/__properties__/")


def validate_device_path(path: str) -> bool:
    return (
        bool(path)
        and "\x00" not in path
        and "'" not in path
        and path.startswith(REMOTE_WORKDIR + "/")
        and ".." not in Path(path).parts
        and bool(SAFE_DEVICE_PATH_RE.match(path))
    )


def file_entries(v312: dict[str, Any]) -> list[LayoutFile]:
    base_dir = Path(str(v312.get("path") or "")).parent
    entries: list[LayoutFile] = []
    for item in v312.get("files", []):
        if not isinstance(item, dict):
            continue
        relative_path = str(item.get("relative_path") or "")
        expected_sha = str(item.get("sha256") or "")
        expected_size = int(item.get("bytes") or 0)
        local_path = base_dir / relative_path
        remote_suffix = relative_path.removeprefix("layout/")
        remote_path = f"{REMOTE_WORKDIR}/{remote_suffix}"
        status = "pass"
        if not validate_relative_path(relative_path) or not validate_device_path(remote_path):
            status = "unsafe-path"
        elif not local_path.exists():
            status = "missing-local"
        else:
            data = local_path.read_bytes()
            actual_sha = sha256_bytes(data)
            if actual_sha != expected_sha or len(data) != expected_size:
                status = "hash-or-size-mismatch"
        entries.append(LayoutFile(
            role=str(item.get("role") or ""),
            relative_path=relative_path,
            local_path=str(local_path),
            remote_path=remote_path,
            bytes=expected_size,
            sha256=expected_sha,
            status=status,
        ))
    return entries


def build_checks(args: argparse.Namespace,
                 v312: dict[str, Any],
                 v315: dict[str, Any],
                 v316: dict[str, Any],
                 approval_refresh: dict[str, Any],
                 prelive_gate: dict[str, Any],
                 files: list[LayoutFile],
                 transfer: TransferEstimate,
                 current_head: str,
                 current_dirty: bool | None) -> list[ProofCheck]:
    phrase = str(v316.get("operator_approval_phrase") or APPROVAL_PHRASE)
    approval_ok = args.approval_phrase == phrase and args.allow_device_mutation and args.assume_yes
    bad_files = [item.relative_path for item in files if item.status != "pass"]
    approval_refresh_ok = (
        bool(approval_refresh.get("present")) and
        approval_refresh.get("decision") == "private-property-approval-refresh-ready" and
        bool(approval_refresh.get("pass")) and
        approval_refresh.get("approval_phrase") == phrase and
        not bool(approval_refresh.get("live_execution_approved")) and
        not bool(approval_refresh.get("device_commands_executed")) and
        not bool(approval_refresh.get("device_mutations"))
    )
    prelive_host = prelive_gate.get("host") if isinstance(prelive_gate.get("host"), dict) else {}
    prelive_ok = (
        bool(prelive_gate.get("present")) and
        prelive_gate.get("decision") == "v317-prelive-gate-awaiting-approval" and
        bool(prelive_gate.get("pass")) and
        prelive_gate.get("required_approval_phrase") == phrase and
        prelive_gate.get("remaining_blockers") == ["exact-v317-approval-phrase"] and
        not bool(prelive_gate.get("live_execution_approved")) and
        not bool(prelive_gate.get("device_commands_executed")) and
        not bool(prelive_gate.get("device_mutations")) and
        prelive_host.get("git_head") == current_head and
        prelive_host.get("git_dirty") is False and
        current_dirty is False
    )
    prelive_not_required_yet = not approval_ok
    return [
        ProofCheck(
            "v312-layout",
            "pass" if v312.get("decision") == "private-property-layout-dryrun-ready" and bool(v312.get("pass")) else "blocked",
            "blocker",
            f"decision={v312.get('decision')} pass={v312.get('pass')}",
            [str(v312.get("path", ""))],
        ),
        ProofCheck(
            "v315-preflight",
            "pass" if v315.get("decision") == "private-property-live-preflight-ready" and bool(v315.get("pass")) else "blocked",
            "blocker",
            f"decision={v315.get('decision')} pass={v315.get('pass')}",
            [str(v315.get("path", ""))],
        ),
        ProofCheck(
            "v316-approval",
            "pass" if v316.get("decision") == "private-property-live-approval-ready" and bool(v316.get("pass")) else "blocked",
            "blocker",
            f"decision={v316.get('decision')} pass={v316.get('pass')}",
            [str(v316.get("path", ""))],
        ),
        ProofCheck(
            "approval-refresh",
            "pass" if approval_refresh_ok else "blocked",
            "blocker",
            (
                f"decision={approval_refresh.get('decision')} pass={approval_refresh.get('pass')} "
                f"live_execution_approved={approval_refresh.get('live_execution_approved')}"
            ),
            [str(approval_refresh.get("path", ""))],
        ),
        ProofCheck(
            "layout-files",
            "pass" if files and not bad_files else "blocked",
            "blocker",
            f"files={len(files)} bad={len(bad_files)}",
            bad_files[:8],
        ),
        ProofCheck(
            "transfer-plan",
            "pass" if transfer.status == "pass" else "blocked",
            "blocker",
            f"chunks={transfer.chunks} estimated_commands={transfer.estimated_commands} max_script_chars={transfer.max_script_chars}",
            [f"chunk_size={transfer.chunk_size}", f"bytes={transfer.bytes}"],
        ),
        ProofCheck(
            "approval-gate",
            "pass" if approval_ok else "needs-operator",
            "approval",
            f"phrase_match={args.approval_phrase == phrase} allow_device_mutation={args.allow_device_mutation} assume_yes={args.assume_yes}",
            [phrase],
        ),
        ProofCheck(
            "v336-prelive-gate",
            "pass" if prelive_not_required_yet or prelive_ok else "blocked",
            "blocker",
            (
                "not required until exact live approval"
                if prelive_not_required_yet
                else (
                    f"decision={prelive_gate.get('decision')} pass={prelive_gate.get('pass')} "
                    f"head={prelive_host.get('git_head')} current_head={current_head} "
                    f"current_dirty={current_dirty} "
                    f"remaining_blockers={prelive_gate.get('remaining_blockers')}"
                )
            ),
            [str(prelive_gate.get("path", ""))],
        ),
    ]




def uuencode_base64_payload(data: bytes, name: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9_.+-]", "_", name) or "payload"
    encoded = base64.b64encode(data).decode("ascii")
    lines = ["begin-base64 600 " + safe_name]
    lines.extend(encoded[index:index + 76] for index in range(0, len(encoded), 76))
    lines.append("====")
    return "\n".join(lines) + "\n"


def estimate_cmdv1x_line_chars(argv: list[str]) -> int:
    total = len("cmdv1x")
    for arg in argv:
        data_len = len(arg.encode("utf-8"))
        total += 1 + len(str(data_len)) + 1 + data_len * 2
    return total


def estimate_transfer(files: list[LayoutFile], chunk_size: int) -> TransferEstimate:
    total_bytes = 0
    total_chunks = 0
    max_script_chars = 0
    if chunk_size < 256 or chunk_size > 1800:
        return TransferEstimate(len(files), 0, chunk_size, 0, 0, 0, "bad-chunk-size")
    for entry in files:
        if entry.status != "pass":
            continue
        data = Path(entry.local_path).read_bytes()
        encoded_text = uuencode_base64_payload(data, Path(entry.remote_path).name)
        chunks = (len(encoded_text) + chunk_size - 1) // chunk_size
        script_chars = estimate_cmdv1x_line_chars([
            "appendfile",
            entry.remote_path + ".uue",
            "X" * min(chunk_size, len(encoded_text)),
        ])
        total_bytes += len(data)
        total_chunks += chunks
        max_script_chars = max(max_script_chars, script_chars)
    manifest_estimate_text = uuencode_base64_payload(b"X" * (4096 + len(files) * 512), "manifest.json")
    manifest_chunks = (len(manifest_estimate_text) + chunk_size - 1) // chunk_size
    manifest_script_chars = estimate_cmdv1x_line_chars([
        "appendfile",
        REMOTE_WORKDIR + "/manifest.json.uue",
        "X" * min(chunk_size, len(manifest_estimate_text)),
    ])
    max_script_chars = max(max_script_chars, manifest_script_chars)
    total_chunks += manifest_chunks
    estimated_commands = 1 + 3 + manifest_chunks + 5
    for entry in files:
        if entry.status != "pass":
            continue
        encoded_len = len(uuencode_base64_payload(Path(entry.local_path).read_bytes(), Path(entry.remote_path).name))
        estimated_commands += ((encoded_len + chunk_size - 1) // chunk_size) + 5
    status = "pass" if total_chunks > 0 and estimated_commands < 1000 and max_script_chars < 3900 else "too-large"
    return TransferEstimate(len(files), total_bytes, chunk_size, total_chunks, estimated_commands, max_script_chars, status)


def command_line(argv: list[str]) -> str:
    return " ".join(argv)


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
    return CommandRecord(
        name=name,
        command=command_line(argv),
        ok=ok,
        rc=result.rc if result is not None else None,
        status=result.status if result is not None else "missing",
        duration_sec=duration,
        file=str(path.relative_to(store.run_dir)),
        error=error,
    )


def device_cmd(args: argparse.Namespace,
               store: EvidenceStore,
               records: list[CommandRecord],
               name: str,
               argv: list[str]) -> ProtocolResult:
    started = time.monotonic()
    try:
        result = run_cmdv1_command(args.host, args.port, args.timeout, argv, retry_unsafe=False)
    except Exception as exc:  # noqa: BLE001 - preserve live failure evidence
        records.append(write_command_record(store, name, argv, None, started, str(exc)))
        raise
    records.append(write_command_record(store, name, argv, result, started))
    if result.rc != 0 or result.status != "ok":
        raise RuntimeError(f"device command failed: {name} rc={result.rc} status={result.status}")
    return result


def mkdir_sequence(args: argparse.Namespace, store: EvidenceStore, records: list[CommandRecord]) -> None:
    for index, path in enumerate([
        REMOTE_WORKDIR,
        REMOTE_WORKDIR + "/dev",
        REMOTE_PROP_PREFIX,
    ], start=1):
        device_cmd(args, store, records, f"mkdir-{index}", ["mkdir", path])


def cleanup_sequence(args: argparse.Namespace, store: EvidenceStore, records: list[CommandRecord]) -> None:
    device_cmd(args, store, records, "cleanup-workdir", ["run", TOYBOX, "rm", "-rf", REMOTE_WORKDIR])


def upload_bytes(args: argparse.Namespace,
                 store: EvidenceStore,
                 records: list[CommandRecord],
                 remote_path: str,
                 data: bytes,
                 expected_sha: str,
                 label: str) -> None:
    if args.chunk_size < 256 or args.chunk_size > 1800:
        raise RuntimeError("chunk size must be between 256 and 1800")
    if not validate_device_path(remote_path):
        raise RuntimeError(f"unsafe remote path: {remote_path}")
    tmp_uue = remote_path + ".uue"
    tmp_file = remote_path + ".tmp"
    for path in [tmp_uue, tmp_file, remote_path]:
        if not validate_device_path(path):
            raise RuntimeError(f"unsafe temp path: {path}")

    device_cmd(args, store, records, f"{label}-rm-old", ["run", TOYBOX, "rm", "-f", tmp_uue, tmp_file, remote_path])
    encoded_text = uuencode_base64_payload(data, Path(remote_path).name)
    for index in range(0, len(encoded_text), args.chunk_size):
        chunk = encoded_text[index:index + args.chunk_size]
        device_cmd(args, store, records, f"{label}-chunk-{index // args.chunk_size:04d}", ["appendfile", tmp_uue, chunk])
    device_cmd(args, store, records, f"{label}-decode", ["run", TOYBOX, "uudecode", "-o", tmp_file, tmp_uue])
    sha_result = device_cmd(args, store, records, f"{label}-sha256", ["run", TOYBOX, "sha256sum", tmp_file])
    match = SHA256_RE.search(sha_result.text)
    actual_sha = match.group(1).lower() if match else ""
    if actual_sha != expected_sha:
        raise RuntimeError(f"sha256 mismatch for {remote_path}: expected={expected_sha} actual={actual_sha}")
    device_cmd(args, store, records, f"{label}-mv", ["run", TOYBOX, "mv", "-f", tmp_file, remote_path])
    device_cmd(args, store, records, f"{label}-rm-uue", ["run", TOYBOX, "rm", "-f", tmp_uue])


def live_run(args: argparse.Namespace, store: EvidenceStore, files: list[LayoutFile]) -> tuple[list[CommandRecord], str]:
    records: list[CommandRecord] = []
    try:
        cleanup_sequence(args, store, records)
        mkdir_sequence(args, store, records)
        for index, entry in enumerate(files, start=1):
            data = Path(entry.local_path).read_bytes()
            upload_bytes(args, store, records, entry.remote_path, data, entry.sha256, f"file-{index:02d}")
        remote_manifest = REMOTE_WORKDIR + "/manifest.json"
        manifest_payload = {
            "generated_at": now_iso(),
            "remote_workdir": REMOTE_WORKDIR,
            "files": [asdict(entry) for entry in files],
            "blocked_actions": [
                "global /dev/__properties__ replacement",
                "property service socket",
                "daemon start",
                "Wi-Fi bring-up",
            ],
        }
        upload_bytes(
            args,
            store,
            records,
            remote_manifest,
            (json.dumps(manifest_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            sha256_bytes((json.dumps(manifest_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")),
            "manifest",
        )
    except Exception as exc:  # noqa: BLE001 - cleanup and report failure evidence
        try:
            cleanup_sequence(args, store, records)
        except Exception:
            pass
        return records, str(exc)
    return records, ""


def approval_ok(args: argparse.Namespace, v316: dict[str, Any]) -> bool:
    return (
        args.approval_phrase == str(v316.get("operator_approval_phrase") or APPROVAL_PHRASE)
        and args.allow_device_mutation
        and args.assume_yes
    )


def decide(args: argparse.Namespace,
           checks: list[ProofCheck],
           live_error: str) -> tuple[str, bool, str]:
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    approvals = [check.name for check in checks if check.severity == "approval" and check.status != "pass"]
    if blockers:
        return "private-property-namespace-proof-blocked", False, "blocked checks: " + ", ".join(blockers)
    if args.command == "plan":
        return "private-property-namespace-proof-plan-ready", True, "plan generated without device mutation"
    if approvals:
        return "private-property-namespace-proof-approval-required", False, "missing approval gates: " + ", ".join(approvals)
    if args.command == "preflight":
        return "private-property-namespace-proof-preflight-ready", True, "all gates passed without device command execution"
    if live_error:
        if args.command == "cleanup":
            return "private-property-namespace-proof-cleanup-failed", False, live_error
        return "private-property-namespace-proof-failed", False, live_error
    if args.command == "cleanup":
        return "private-property-namespace-proof-cleaned", True, "private v317 workdir cleanup completed"
    return "private-property-namespace-proof-pass", True, "private property files copied and verified under the v317 workdir"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    host = collect_host_metadata()
    v312 = load_json(args.v312_manifest)
    v315 = load_json(args.v315_manifest)
    v316 = load_json(args.v316_manifest)
    approval_refresh = load_json(args.approval_refresh_manifest)
    prelive_gate = load_json(args.prelive_gate_manifest)
    files = file_entries(v312)
    transfer = estimate_transfer(files, args.chunk_size)
    checks = build_checks(
        args,
        v312,
        v315,
        v316,
        approval_refresh,
        prelive_gate,
        files,
        transfer,
        str(host.get("git_head") or ""),
        host.get("git_dirty") if isinstance(host.get("git_dirty"), bool) else None,
    )
    records: list[CommandRecord] = []
    live_error = ""
    if args.command == "run" and approval_ok(args, v316) and not any(
        check.severity == "blocker" and check.status != "pass" for check in checks
    ):
        records, live_error = live_run(args, store, files)
    elif args.command == "cleanup" and approval_ok(args, v316):
        try:
            cleanup_sequence(args, store, records)
        except Exception as exc:  # noqa: BLE001 - preserve cleanup failure evidence
            live_error = str(exc)
    decision, pass_ok, reason = decide(args, checks, live_error)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": (
            "v320 private property lookup proof planning"
            if decision == "private-property-namespace-proof-pass"
            else (
                "live run is ready but still requires explicitly choosing the run command"
                if decision == "private-property-namespace-proof-preflight-ready"
                else "provide exact v317 approval before live proof execution"
            )
        ),
        "host": host,
        "remote_workdir": REMOTE_WORKDIR,
        "inputs": {
            "v312": {"path": v312.get("path"), "present": bool(v312.get("present")), "decision": v312.get("decision"), "pass": v312.get("pass")},
            "v315": {"path": v315.get("path"), "present": bool(v315.get("present")), "decision": v315.get("decision"), "pass": v315.get("pass")},
            "v316": {"path": v316.get("path"), "present": bool(v316.get("present")), "decision": v316.get("decision"), "pass": v316.get("pass")},
            "approval_refresh": {"path": approval_refresh.get("path"), "present": bool(approval_refresh.get("present")), "decision": approval_refresh.get("decision"), "pass": approval_refresh.get("pass")},
            "prelive_gate": {"path": prelive_gate.get("path"), "present": bool(prelive_gate.get("present")), "decision": prelive_gate.get("decision"), "pass": prelive_gate.get("pass")},
        },
        "checks": [asdict(check) for check in checks],
        "files": [asdict(entry) for entry in files],
        "transfer_estimate": asdict(transfer),
        "commands": [asdict(record) for record in records],
        "live_error": live_error,
        "preflight_only": args.command == "preflight",
        "device_commands_executed": bool(records),
        "device_mutations": bool(records),
        "blocked_actions": [
            "global /dev/__properties__ replacement",
            "global bind mount over /dev/__properties__",
            "global /dev/socket/property_service creation",
            "property mutation or setprop-like writes",
            "service-manager or hwservicemanager start",
            "Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "NCM/tcpctl start for transfer",
        ],
        "operator_approval_phrase": str(v316.get("operator_approval_phrase") or APPROVAL_PHRASE),
    }


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# v317 Minimal Private Property Namespace Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- remote_workdir: `{manifest['remote_workdir']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Checks",
        "",
        "| name | status | severity | detail |",
        "| --- | --- | --- | --- |",
    ]
    for check in manifest["checks"]:
        lines.append(f"| `{check['name']}` | `{check['status']}` | `{check['severity']}` | {check['detail']} |")
    lines.extend(["", "## Files", "", "| role | relative_path | bytes | status |", "| --- | --- | --- | --- |"])
    for entry in manifest["files"]:
        lines.append(f"| `{entry['role']}` | `{entry['relative_path']}` | `{entry['bytes']}` | `{entry['status']}` |")
    transfer = manifest["transfer_estimate"]
    lines.extend([
        "",
        "## Transfer Estimate",
        "",
        f"- files: `{transfer['files']}`",
        f"- bytes: `{transfer['bytes']}`",
        f"- chunk_size: `{transfer['chunk_size']}`",
        f"- chunks: `{transfer['chunks']}`",
        f"- estimated_commands: `{transfer['estimated_commands']}`",
        f"- max_script_chars: `{transfer['max_script_chars']}`",
        f"- status: `{transfer['status']}`",
    ])
    lines.extend(["", "## Commands", "", "| name | ok | rc | status | file |", "| --- | --- | --- | --- | --- |"])
    for record in manifest["commands"]:
        lines.append(f"| `{record['name']}` | `{record['ok']}` | `{record['rc']}` | `{record['status']}` | `{record['file']}` |")
    lines.extend(["", "## Blocked Actions", ""])
    lines.extend(f"- `{item}`" for item in manifest["blocked_actions"])
    lines.extend(["", "## Approval Phrase", "", f"`{manifest['operator_approval_phrase']}`", ""])
    return "\n".join(lines)


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
