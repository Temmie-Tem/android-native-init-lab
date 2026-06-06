#!/usr/bin/env python3
"""V536 incremental rmt_storage private property deploy.

Uploads only the V535 files changed by the rmt_storage property-surface patch:
`property_info`, `u:object_r:debug_prop:s0`, and
`u:object_r:log_tag_prop:s0`. It then runs the V535 read-only lookup proof.
It does not replace global `/dev/__properties__`, start daemons,
scan/connect, or bring Wi-Fi up.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore

import native_property_runtime_live_v535 as v535


DEFAULT_OUT_DIR = Path("tmp/wifi/v536-rmt-property-incremental-live")
DEFAULT_V535 = Path("tmp/wifi/v535-rmt-storage-private-property-runtime/manifest.json")
TCPCTL_SCRIPT = Path("scripts/revalidation/tcpctl_host.py")
DEFAULT_DEVICE_IP = "192.168.7.2"
DEFAULT_TRANSFER_PORT = 18085
DEFAULT_NCM_STAGING_DIR = "/cache/a90-runtime/bin"
SELECTED_RELATIVE_PATHS = (
    "layout/dev/__properties__/property_info",
    "layout/dev/__properties__/u:object_r:debug_prop:s0",
    "layout/dev/__properties__/u:object_r:log_tag_prop:s0",
)
APPROVAL_PHRASE = (
    "approve v536 rmt-storage private property delta deploy only; "
    "no daemon start and no Wi-Fi bring-up"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v535-manifest", type=Path, default=DEFAULT_V535)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--chunk-size", type=int, default=v535.live.CHUNK_SIZE)
    parser.add_argument("--helper", default=v535.live.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=v535.live.DEFAULT_HELPER_SHA256)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--transfer-port", type=int, default=DEFAULT_TRANSFER_PORT)
    parser.add_argument("--transfer-method", choices=("ncm", "serial"), default="ncm")
    parser.add_argument("--ncm-staging-dir", default=DEFAULT_NCM_STAGING_DIR)
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
    data = json.loads(resolved.read_text(encoding="utf-8"))
    data["present"] = True
    data["path"] = str(resolved)
    return data


def run_host(command: list[str], *, timeout: float = 180.0) -> tuple[int, str, float]:
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout, time.monotonic() - started


def validate_ncm_staging_path(path: str) -> bool:
    return (
        bool(path)
        and "\x00" not in path
        and "'" not in path
        and path.startswith(DEFAULT_NCM_STAGING_DIR + "/")
        and ".." not in Path(path).parts
        and bool(v535.live.SAFE_DEVICE_PATH_RE.match(path))
    )


def selected_files(layout: dict[str, Any]) -> list[v535.live.LayoutFile]:
    files_by_path = {
        item.relative_path: item
        for item in v535.live.layout_files(layout)
    }
    selected_paths = set(SELECTED_RELATIVE_PATHS)
    observed_keys = set(layout.get("rmt_storage_observed_keys") or [])
    for mapping in layout.get("mappings", []):
        if mapping.get("key") not in observed_keys:
            continue
        context = mapping.get("context")
        if not context:
            continue
        selected_paths.add(f"layout/dev/__properties__/{context}")
    return [files_by_path[path] for path in sorted(selected_paths) if path in files_by_path]


def preflight(args: argparse.Namespace,
              store: EvidenceStore,
              records: list[v535.live.CommandRecord]) -> None:
    v535.live.device_cmd(args, store, records, "version", ["version"])
    v535.live.device_cmd(args, store, records, "status", ["status"])
    v535.live.device_cmd(args, store, records, "sha-helper", ["run", v535.live.TOYBOX, "sha256sum", args.helper])
    v535.live.device_cmd(args, store, records, "stat-v535-root", ["stat", v535.live.REMOTE_PROP_ROOT])


def deploy_delta(args: argparse.Namespace,
                 store: EvidenceStore,
                 records: list[v535.live.CommandRecord],
                 files: list[v535.live.LayoutFile]) -> None:
    for index, item in enumerate(files, start=1):
        label = f"file-{index:02d}"
        data = Path(item.local_path).read_bytes()
        if args.transfer_method == "ncm":
            upload_bytes_ncm(args, store, records, item.remote_path, data, item.sha256, label, v535.live.REMOTE_PROP_FILE_MODE, index)
        else:
            v535.live.upload_bytes(
                args,
                store,
                records,
                item.remote_path,
                data,
                item.sha256,
                label,
                v535.live.REMOTE_PROP_FILE_MODE,
            )


def upload_bytes_ncm(args: argparse.Namespace,
                     store: EvidenceStore,
                     records: list[v535.live.CommandRecord],
                     remote_path: str,
                     data: bytes,
                     expected_sha: str,
                     label: str,
                     mode: str,
                     index: int) -> None:
    staging_dir = args.ncm_staging_dir.rstrip("/")
    staging = f"{staging_dir}/.v536-{label}-{os.getpid()}-{int(time.time())}"
    if not v535.live.validate_device_path(remote_path):
        raise RuntimeError(f"unsafe remote path: {remote_path}")
    if not validate_ncm_staging_path(staging):
        raise RuntimeError(f"unsafe NCM staging path: {staging}")

    store.mkdir("host")
    payload = store.path("host", f"{label}-payload.bin")
    payload.write_bytes(data)
    os.chmod(payload, 0o600)

    v535.live.device_cmd(args, store, records, f"{label}-ncm-mkdir-staging", ["run", v535.live.TOYBOX, "mkdir", "-p", staging_dir])
    v535.live.device_cmd(args, store, records, f"{label}-ncm-rm-staging", ["run", v535.live.TOYBOX, "rm", "-f", staging])

    command = [
        sys.executable,
        str(repo_path(TCPCTL_SCRIPT)),
        "--bridge-host",
        args.host,
        "--bridge-port",
        str(args.port),
        "--device-ip",
        args.device_ip,
        "--device-binary",
        staging,
        "--toybox",
        v535.live.TOYBOX,
        "install",
        "--local-binary",
        str(payload),
        "--transfer-port",
        str(args.transfer_port + index),
    ]
    rc, output, duration = run_host(command, timeout=max(180.0, args.timeout * 6.0))
    rel = f"host/{label}-ncm-install.txt"
    store.write_text(rel, output)
    records.append(v535.live.CommandRecord(
        name=f"{label}-ncm-install",
        command=" ".join(command),
        ok=rc == 0,
        rc=rc,
        status="host",
        duration_sec=duration,
        file=rel,
        error="" if rc == 0 else output[-1000:],
    ))
    if rc != 0:
        raise RuntimeError(f"NCM install failed for {remote_path}: rc={rc}")

    sha_result = v535.live.device_cmd(args, store, records, f"{label}-ncm-sha-staging", ["run", v535.live.TOYBOX, "sha256sum", staging])
    match = v535.live.SHA256_RE.search(sha_result.text)
    actual_sha = match.group(1).lower() if match else ""
    if actual_sha != expected_sha:
        raise RuntimeError(f"sha256 mismatch for {staging}: expected={expected_sha} actual={actual_sha}")
    v535.live.device_cmd(args, store, records, f"{label}-ncm-mv", ["run", v535.live.TOYBOX, "mv", "-f", staging, remote_path])
    v535.live.device_cmd(args, store, records, f"{label}-ncm-chmod", ["run", v535.live.TOYBOX, "chmod", mode, remote_path])
    v535.live.device_cmd(args, store, records, f"{label}-ncm-sha-final", ["run", v535.live.TOYBOX, "sha256sum", remote_path])


def decide(args: argparse.Namespace,
           layout: dict[str, Any],
           files: list[v535.live.LayoutFile],
           records: list[v535.live.CommandRecord],
           lookups: list[v535.live.LookupResult],
           live_error: str) -> tuple[str, bool, str, str]:
    failed_commands = [record.name for record in records if not record.ok]
    bad_files = [item.relative_path for item in files if item.status != "pass"]
    lookup_failures = [item.key for item in lookups if not item.ok]
    if args.command == "plan":
        return "v536-rmt-property-incremental-plan-ready", True, "plan generated without device commands", "run preflight"
    if layout.get("decision") != "v535-rmt-storage-private-property-runtime-ready" or not layout.get("pass"):
        return "v536-rmt-property-incremental-blocked", False, "V535 layout is not ready", "regenerate V535 layout"
    if bad_files:
        return "v536-rmt-property-incremental-blocked", False, "bad files: " + ", ".join(bad_files), "fix V535 selected files"
    if failed_commands or live_error:
        return "v536-rmt-property-incremental-failed", False, live_error or "failed commands: " + ", ".join(failed_commands), "inspect live evidence"
    if args.command == "preflight":
        return "v536-rmt-property-incremental-preflight-ready", True, "preflight passed; delta upload still needs approval", "run approved V536 delta deploy"
    if not approved(args):
        return "v536-rmt-property-incremental-approval-required", False, "exact approval phrase required", "provide exact approval phrase"
    if lookup_failures:
        return "v536-rmt-property-incremental-lookup-blocked", False, "lookup failures: " + ", ".join(lookup_failures), "fix property layout or helper allowlist"
    return "v536-rmt-property-incremental-lookup-pass", True, "property delta deployed and selected rmt lookups passed", "rerun rmt_storage start-only proof"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    store.mkdir("commands")
    layout = load_json(args.v535_manifest)
    files = selected_files(layout)
    records: list[v535.live.CommandRecord] = []
    lookups: list[v535.live.LookupResult] = []
    live_error = ""
    if args.command != "plan":
        try:
            preflight(args, store, records)
            if args.command == "run" and approved(args):
                deploy_delta(args, store, records, files)
                expected = v535.live.expected_values(layout)
                lookups = v535.live.run_lookup(args, store, records, expected)
        except Exception as exc:  # noqa: BLE001
            live_error = str(exc)
    decision, pass_ok, reason, next_step = decide(args, layout, files, records, lookups, live_error)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v535": {"path": layout.get("path"), "decision": layout.get("decision"), "pass": layout.get("pass")},
        },
        "remote_property_root": v535.live.REMOTE_PROP_ROOT,
        "selected_files": [asdict(item) for item in files],
        "commands": [asdict(record) for record in records],
        "lookups": [asdict(item) for item in lookups],
        "live_error": live_error,
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan",
        "device_mutations": args.command == "run" and approved(args) and not live_error,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    file_rows = [[item["relative_path"], str(item["bytes"]), item["status"]] for item in manifest["selected_files"]]
    lookup_rows = [[item["key"], item["expected"], item["actual"], str(item["context_warning_count"]), str(item["access_denied_count"]), str(item["ok"])] for item in manifest["lookups"]]
    command_rows = [[item["name"], "PASS" if item["ok"] else "FAIL", item["status"], item["file"]] for item in manifest["commands"]]
    return "\n".join([
        "# V536 rmt_storage Property Incremental Deploy",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- remote_property_root: `{manifest['remote_property_root']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Selected Files",
        "",
        markdown_table(["path", "bytes", "status"], file_rows),
        "",
        "## Lookups",
        "",
        markdown_table(["key", "expected", "actual", "context_warnings", "access_denied", "ok"], lookup_rows) if lookup_rows else "- none",
        "",
        "## Commands",
        "",
        markdown_table(["name", "ok", "status", "file"], command_rows) if command_rows else "- none",
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
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
