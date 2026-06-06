#!/usr/bin/env python3
"""Read-only pull of service-manager frame ELFs and framechain re-analysis."""

from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_bytes


DEFAULT_OUT_DIR = Path("tmp/wifi/v396-service-manager-frame-elf-pull")
DEFAULT_RUN_LOG = Path("tmp/wifi/v392-approved-full-20260520-072551/live/native/run-system-servicemanager.txt")
REMOTE_FILES = (
    "/mnt/system/system/bin/servicemanager",
    "/mnt/system/system/lib64/libbase.so",
    "/mnt/system/system/lib64/liblog.so",
)
MAX_FILE_BYTES = 8 * 1024 * 1024
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=]*$")
STAT_SIZE_RE = re.compile(r"\bsize=(\d+)\b")
CMDV1_NOISE_PREFIXES = (
    "a90:/#",
    "A90P1 BEGIN ",
    "A90P1 END ",
    "[done] ",
    "[exit ",
    "run: pid=",
)


@dataclass
class PulledElf:
    remote_path: str
    local_path: str
    size: int
    sha256: str
    stat_ok: bool
    pull_ok: bool
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run-log", type=Path, default=DEFAULT_RUN_LOG)
    parser.add_argument("--max-file-bytes", type=int, default=MAX_FILE_BYTES)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("pull")
    return parser.parse_args()


def validate_remote_path(path: str) -> None:
    if path not in REMOTE_FILES:
        raise RuntimeError(f"remote path is not allowlisted: {path}")


def validate_device_command(command: list[str]) -> None:
    if command in (["version"], ["status"], ["mountsystem", "ro"]):
        return
    if len(command) == 2 and command[0] == "stat":
        validate_remote_path(command[1])
        return
    if len(command) == 6 and command[:5] == ["run", "/cache/bin/toybox", "base64", "-w", "0"]:
        validate_remote_path(command[5])
        return
    raise RuntimeError(f"unexpected device command: {' '.join(command)}")


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    path = store.write_text(f"native/commands/{name}.txt", text.rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def capture_device(store: EvidenceStore,
                   args: argparse.Namespace,
                   name: str,
                   command: list[str],
                   timeout: float | None = None) -> dict[str, Any]:
    validate_device_command(command)
    capture = run_capture(args, name, command, timeout=timeout)
    file_path = write_capture(store, name, capture.text or capture.error)
    data = capture_to_manifest(capture)
    data["file"] = file_path
    return data


def cleaned_payload_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in strip_cmdv1_text(text).splitlines():
        line = raw_line.strip()
        for marker in ("[exit ", "[done] ", "A90P1 END "):
            marker_index = line.find(marker)
            if marker_index >= 0:
                line = line[:marker_index].strip()
        if not line:
            continue
        if line.startswith("cmdv1 ") or line.startswith("cmdv1x "):
            continue
        if any(line.startswith(prefix) for prefix in CMDV1_NOISE_PREFIXES):
            continue
        lines.append(line)
    return lines


def extract_base64_payload(text: str) -> str:
    payload = "".join(cleaned_payload_lines(text))
    payload = re.sub(r"\s+", "", payload)
    if not payload:
        raise RuntimeError("empty base64 payload")
    if not BASE64_RE.fullmatch(payload):
        raise RuntimeError("base64 payload contains unexpected characters")
    return payload


def parse_stat_size(text: str) -> int | None:
    match = STAT_SIZE_RE.search(strip_cmdv1_text(text))
    return int(match.group(1)) if match else None


def local_path_for(remote_path: str) -> Path:
    suffix = remote_path.removeprefix("/mnt/system/system/")
    if suffix == remote_path:
        raise RuntimeError(f"unexpected remote prefix: {remote_path}")
    return Path("system-root") / "system" / suffix


def sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def pull_one(store: EvidenceStore, args: argparse.Namespace, remote_path: str, captures: list[dict[str, Any]]) -> PulledElf:
    validate_remote_path(remote_path)
    safe_name = remote_path.removeprefix("/mnt/system/system/").replace("/", "-")
    stat_record = capture_device(store, args, f"stat-{safe_name}", ["stat", remote_path], timeout=30.0)
    captures.append(stat_record)
    if not stat_record["ok"]:
        return PulledElf(remote_path, "", 0, "", False, False, "stat failed")
    expected_size = parse_stat_size(stat_record["text"])
    if expected_size is None:
        return PulledElf(remote_path, "", 0, "", True, False, "stat size missing")
    if expected_size > args.max_file_bytes:
        return PulledElf(remote_path, "", expected_size, "", True, False, f"file too large: {expected_size}")
    base64_record = capture_device(
        store,
        args,
        f"base64-{safe_name}",
        ["run", "/cache/bin/toybox", "base64", "-w", "0", remote_path],
        timeout=max(args.timeout, 180.0),
    )
    captures.append(base64_record)
    if not base64_record["ok"]:
        return PulledElf(remote_path, "", expected_size, "", True, False, "base64 failed")
    try:
        encoded = store.path(base64_record["file"]).read_text(encoding="utf-8", errors="replace")
        data = base64.b64decode(extract_base64_payload(encoded), validate=True)
    except (binascii.Error, RuntimeError) as exc:
        return PulledElf(remote_path, "", expected_size, "", True, False, f"base64 decode failed: {exc}")
    if len(data) != expected_size:
        return PulledElf(remote_path, "", expected_size, "", True, False, f"size mismatch {len(data)}!={expected_size}")
    local_path = store.path(str(local_path_for(remote_path)))
    write_private_bytes(local_path, data)
    return PulledElf(
        remote_path,
        str(local_path.relative_to(store.run_dir)),
        expected_size,
        sha256_bytes(data),
        True,
        True,
        "",
    )


def run_host_command(command: list[str], timeout: int = 120) -> tuple[int | None, str, str]:
    try:
        result = subprocess.run(
            command,
            cwd=repo_path(Path(".")),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return result.returncode, result.stdout, ""
    except Exception as exc:  # noqa: BLE001 - preserve host failures in evidence
        return None, "", str(exc)


def run_framechain_analyzer(store: EvidenceStore, args: argparse.Namespace) -> dict[str, Any]:
    out_dir = store.run_dir / "framechain"
    command = [
        "python3",
        "scripts/revalidation/wifi_service_manager_framechain_analyze.py",
        "--out-dir",
        str(out_dir),
        "--run-log",
        str(repo_path(args.run_log)),
        "--elf-root",
        str(store.run_dir / "system-root"),
        "analyze",
    ]
    rc, text, error = run_host_command(command)
    store.write_text("host/framechain-analyzer.txt", "$ " + " ".join(command) + "\n" + (text or error) + f"\nrc={rc}\n")
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        return {"present": False, "path": str(manifest_path), "rc": rc, "error": error or "manifest missing"}
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(manifest_path)
    payload["rc"] = rc
    return payload


def build_plan_manifest(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "service-manager-frame-elf-pull-plan-ready",
        "pass": True,
        "reason": "plan-only; no device commands executed",
        "next_step": "run pull to read-only mirror frame ELFs and rerun framechain analyzer",
        "host": collect_host_metadata(),
        "remote_files": list(REMOTE_FILES),
        "run_log": str(repo_path(args.run_log)),
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
    }


def build_pull_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures: list[dict[str, Any]] = []
    captures.append(capture_device(store, args, "version", ["version"], timeout=15.0))
    captures.append(capture_device(store, args, "status", ["status"], timeout=25.0))
    mount_record = capture_device(store, args, "mountsystem-ro", ["mountsystem", "ro"], timeout=35.0)
    captures.append(mount_record)
    pulled: list[PulledElf] = []
    if mount_record["ok"]:
        for remote_path in REMOTE_FILES:
            pulled.append(pull_one(store, args, remote_path, captures))
    analyzer = run_framechain_analyzer(store, args) if all(item.pull_ok for item in pulled) else {"present": False}
    all_pulled = bool(pulled) and all(item.pull_ok for item in pulled)
    symbolized = analyzer.get("decision") == "service-manager-framechain-symbolization-pass" and bool(analyzer.get("symbols_present"))
    if all_pulled and symbolized:
        decision = "service-manager-frame-elf-symbolization-pass"
        pass_ok = True
        next_step = "inspect newly symbolized service-manager/libbase/liblog frame callers"
        blockers: list[str] = []
    elif all_pulled:
        decision = "service-manager-frame-elf-pulled-analysis-review"
        pass_ok = bool(analyzer.get("pass"))
        next_step = "inspect framechain analyzer output"
        blockers = ["framechain-analysis-review"]
    else:
        decision = "service-manager-frame-elf-pull-failed"
        pass_ok = False
        next_step = "inspect failed read-only ELF pull evidence"
        blockers = [item.remote_path for item in pulled if not item.pull_ok] or ["frame-elf-pull"]
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": "read-only frame ELF pull and framechain analyzer completed" if pass_ok else "frame ELF pull/analyze did not complete cleanly",
        "next_step": next_step,
        "host": collect_host_metadata(),
        "run_log": str(repo_path(args.run_log)),
        "device_captures": captures,
        "pulled": [asdict(item) for item in pulled],
        "framechain_manifest": {
            "present": analyzer.get("present"),
            "path": analyzer.get("path"),
            "decision": analyzer.get("decision"),
            "pass": analyzer.get("pass"),
            "symbols_present": analyzer.get("symbols_present"),
            "remaining_blockers": analyzer.get("remaining_blockers"),
        },
        "remaining_blockers": blockers,
        "device_commands_executed": True,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "guardrails": [
            "allowlisted /mnt/system/system frame ELF paths only",
            "mountsystem ro only",
            "toybox base64 read-only transfer",
            "no helper deploy",
            "no daemon start",
            "no Wi-Fi HAL/start/scan/connect",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    pulled_rows = [
        [item["remote_path"], item["pull_ok"], item["size"], item["sha256"], item["local_path"], item["error"]]
        for item in manifest.get("pulled", [])
    ]
    lines = [
        "# Service-Manager Frame ELF Pull",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Pulled ELFs",
        "",
    ]
    if pulled_rows:
        from a90_kernel_tools import markdown_table

        lines.append(markdown_table(["remote", "ok", "size", "sha256", "local", "error"], pulled_rows))
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        manifest = build_plan_manifest(args)
    else:
        manifest = build_pull_manifest(args, store)
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
