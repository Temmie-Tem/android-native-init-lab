#!/usr/bin/env python3
"""V476 incremental observed-property runtime deploy.

This uploads only the minimum V476 files needed to remove observed property
context warnings from the repaired V471 private root: `property_info` plus newly
introduced context prop_area files. Existing context prop_area files are left in
place, so missing values remain empty instead of becoming context lookup
failures. It does not replace global /dev/__properties__, start daemons, or
bring Wi-Fi up.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore

import native_property_runtime_live_v472 as live


DEFAULT_OUT_DIR = Path("tmp/wifi/v476-observed-property-context-incremental-deploy")
DEFAULT_V471 = Path("tmp/wifi/v471-extended-private-property-runtime/manifest.json")
APPROVAL_PHRASE = (
    "approve v476 observed property context incremental deploy only; "
    "no daemon start and no Wi-Fi bring-up"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--chunk-size", type=int, default=live.CHUNK_SIZE)
    parser.add_argument("--helper", default=live.DEFAULT_HELPER)
    parser.add_argument("--v471-manifest", type=Path, default=DEFAULT_V471)
    parser.add_argument("--v476-manifest", type=Path, required=True)
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


def relative_file_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("relative_path") or ""): item
        for item in manifest.get("files", [])
        if isinstance(item, dict) and str(item.get("relative_path") or "").startswith("layout/dev/__properties__/")
    }


def selected_files(v471: dict[str, Any], v476: dict[str, Any]) -> tuple[list[live.LayoutFile], list[str]]:
    old = relative_file_map(v471)
    new = relative_file_map(v476)
    selected: list[live.LayoutFile] = []
    skipped_changed: list[str] = []
    base_dir = Path(str(v476.get("path") or "")).parent
    for relative_path, item in sorted(new.items()):
        old_item = old.get(relative_path)
        is_property_info = relative_path.endswith("/property_info")
        is_new_context = old_item is None
        is_changed_existing = old_item is not None and (
            old_item.get("sha256") != item.get("sha256") or old_item.get("bytes") != item.get("bytes")
        )
        if not is_property_info and not is_new_context:
            if is_changed_existing:
                skipped_changed.append(relative_path)
            continue
        local_path = base_dir / relative_path
        remote_path = live.REMOTE_WORKDIR + "/" + relative_path.removeprefix("layout/")
        status = "pass"
        if not live.validate_device_path(remote_path) or not live.validate_relative_path(relative_path):
            status = "unsafe-path"
        elif not local_path.exists():
            status = "missing-local"
        selected.append(live.LayoutFile(
            role=str(item.get("role") or ""),
            relative_path=relative_path,
            local_path=str(local_path),
            remote_path=remote_path,
            bytes=int(item.get("bytes") or 0),
            sha256=str(item.get("sha256") or ""),
            status=status,
        ))
    return selected, skipped_changed


def run_preflight(args: argparse.Namespace, store: EvidenceStore, records: list[live.CommandRecord]) -> None:
    live.device_cmd(args, store, records, "version", ["version"])
    live.device_cmd(args, store, records, "status", ["status"])
    live.device_cmd(args, store, records, "stat-remote-root", ["stat", live.REMOTE_PROP_ROOT])
    live.device_cmd(args, store, records, "stat-property-info", ["stat", live.REMOTE_PROP_ROOT + "/property_info"])


def run_upload(args: argparse.Namespace,
               store: EvidenceStore,
               records: list[live.CommandRecord],
               files: list[live.LayoutFile]) -> None:
    for index, entry in enumerate(files, start=1):
        if entry.status != "pass":
            raise RuntimeError(f"selected file is not uploadable: {entry.relative_path} status={entry.status}")
        live.upload_bytes(
            args,
            store,
            records,
            entry.remote_path,
            Path(entry.local_path).read_bytes(),
            entry.sha256,
            f"file-{index:02d}",
            live.REMOTE_PROP_FILE_MODE,
        )
    live.device_cmd(args, store, records, "stat-after-property-info", ["stat", live.REMOTE_PROP_ROOT + "/property_info"])


def decide(args: argparse.Namespace,
           bad_files: list[str],
           records: list[live.CommandRecord],
           live_error: str) -> tuple[str, bool, str, str]:
    failed = [record.name for record in records if not record.ok]
    if args.command == "plan":
        return "v476-observed-property-context-incremental-plan-ready", True, "plan generated without device commands", "run preflight"
    if bad_files:
        return "v476-observed-property-context-incremental-blocked", False, "bad files: " + ", ".join(bad_files), "fix V476 layout"
    if failed or live_error:
        return "v476-observed-property-context-incremental-failed", False, live_error or "failed commands: " + ", ".join(failed), "inspect deploy evidence"
    if args.command == "preflight":
        return "v476-observed-property-context-incremental-preflight-ready", True, "remote root is present; upload still requires approval", "run approved incremental deploy"
    if not approved(args):
        return "v476-observed-property-context-incremental-approval-required", False, "exact approval phrase required", "provide exact approval phrase"
    return "v476-observed-property-context-incremental-deployed", True, "minimal V476 property_info/context files deployed", "rerun Samsung registration proof and check context warnings"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    store.mkdir("commands")
    v471 = load_json(args.v471_manifest)
    v476 = load_json(args.v476_manifest)
    files, skipped_changed = selected_files(v471, v476)
    records: list[live.CommandRecord] = []
    live_error = ""
    if args.command in ("preflight", "run"):
        try:
            run_preflight(args, store, records)
            if args.command == "run" and approved(args):
                run_upload(args, store, records, files)
        except Exception as exc:  # noqa: BLE001 - preserve evidence
            live_error = str(exc)
    bad_files = [entry.relative_path for entry in files if entry.status != "pass"]
    decision, pass_ok, reason, next_step = decide(args, bad_files, records, live_error)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "remote_property_root": live.REMOTE_PROP_ROOT,
        "inputs": {
            "v471": {"path": v471.get("path"), "decision": v471.get("decision"), "pass": v471.get("pass")},
            "v476": {"path": v476.get("path"), "decision": v476.get("decision"), "pass": v476.get("pass")},
        },
        "selected_files": [asdict(entry) for entry in files],
        "skipped_changed_existing_context_files": skipped_changed,
        "commands": [asdict(record) for record in records],
        "live_error": live_error,
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": bool(records),
        "device_mutations": args.command == "run" and approved(args) and not live_error,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "blocked_actions": [
            "global /dev/__properties__ replacement",
            "property mutation or setprop-like writes",
            "service-manager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
            "persistent boot/autostart changes",
            "Android partition writes",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    file_rows = [[item["relative_path"], str(item["bytes"]), item["status"]] for item in manifest["selected_files"]]
    command_rows = [[item["name"], "PASS" if item["ok"] else "FAIL", item["status"], item["file"]] for item in manifest["commands"]]
    return "\n".join([
        "# V476 Observed Property Context Incremental Deploy",
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
        "## Selected Files",
        "",
        markdown_table(["path", "bytes", "status"], file_rows),
        "",
        "## Commands",
        "",
        markdown_table(["name", "ok", "status", "file"], command_rows) if command_rows else "- none",
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
