#!/usr/bin/env python3
"""Export minimal Android system/core libraries needed by CNSS ELF evidence."""

from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import hashlib
import json
import re
import shutil
import stat
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    DEFAULT_EXPECT_VERSION,
    REPO_ROOT,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore, ensure_private_dir, write_private_bytes


DEFAULT_OUT_DIR = Path("tmp/wifi/v227-android-core-system-library-evidence")
DEFAULT_V221_MANIFEST = Path("tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json")
DEFAULT_UNRESOLVED_NAMES = ("libcutils.so", "libnl.so", "libhardware_legacy.so")
SYSTEM_LIBRARY_DIRS = ("system/lib64", "system/lib")
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=]*$")
STAT_SIZE_RE = re.compile(r"\bsize=(\d+)\b")
RUN_PID_INLINE_RE = re.compile(r"run:\s*pid=\d+,\s*q/Ctrl-C cancels")
CMDV1_NOISE_PREFIXES = (
    "a90:/#",
    "A90P1 BEGIN ",
    "A90P1 END ",
    "[done] ",
    "[exit ",
    "run: pid=",
)


def default_out_dir() -> Path:
    return REPO_ROOT / DEFAULT_OUT_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v221-manifest", type=Path, default=DEFAULT_V221_MANIFEST)
    parser.add_argument("--max-file-bytes", type=int, default=16 * 1024 * 1024)
    parser.add_argument("--max-total-bytes", type=int, default=96 * 1024 * 1024)
    parser.add_argument("--library", action="append", default=None, help="Library name to export; defaults to v221 unresolved names")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "_", value).strip("_") or "capture"


def is_safe_library_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.+@-]+\.so", name))


def is_safe_rel(rel: str) -> bool:
    path = Path(rel)
    return bool(rel) and not path.is_absolute() and ".." not in path.parts and rel.startswith(("system/lib/", "system/lib64/"))


def remote_path(rel: str) -> str:
    if not is_safe_rel(rel):
        raise RuntimeError(f"unsafe system relative path: {rel}")
    return f"/mnt/system/{rel}"


def load_json(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def unresolved_library_names(v221: dict[str, Any], requested: list[str] | None) -> list[str]:
    names: set[str] = set(DEFAULT_UNRESOLVED_NAMES)
    if requested:
        names.update(requested)
    for daemon in v221.get("daemons", []):
        if not isinstance(daemon, dict):
            continue
        for item in daemon.get("unresolved_libraries", []):
            if isinstance(item, dict) and item.get("name"):
                names.add(str(item["name"]))
    invalid = sorted(name for name in names if not is_safe_library_name(name))
    if invalid:
        raise RuntimeError(f"unsafe library names in request: {', '.join(invalid)}")
    return sorted(names)


def target_rels(names: list[str]) -> list[str]:
    return [f"{directory}/{name}" for name in names for directory in SYSTEM_LIBRARY_DIRS]


def validate_command(command: list[str]) -> None:
    name = command[0] if command else ""
    joined = " ".join(command)
    if name in {"version", "status", "bootstatus"}:
        if len(command) != 1:
            raise RuntimeError(f"unexpected {name} command: {joined}")
        return
    if command == ["mountsystem", "ro"]:
        return
    if command == ["cat", "/proc/mounts"]:
        return
    if name == "stat" and len(command) == 2 and command[1].startswith("/mnt/system/system/lib"):
        return
    if len(command) == 6 and command[:5] == ["run", "/cache/bin/toybox", "base64", "-w", "0"] and command[5].startswith("/mnt/system/system/lib"):
        return
    raise RuntimeError(f"unexpected command: {joined}")


def validate_command_guard() -> None:
    commands = [
        ["version"],
        ["status"],
        ["bootstatus"],
        ["mountsystem", "ro"],
        ["cat", "/proc/mounts"],
        ["stat", "/mnt/system/system/lib64/libcutils.so"],
        ["run", "/cache/bin/toybox", "base64", "-w", "0", "/mnt/system/system/lib64/libcutils.so"],
    ]
    for command in commands:
        validate_command(command)


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    path = store.write_text(f"native/commands/{safe_name(name)}.txt", text.rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def capture_device(store: EvidenceStore,
                   args: argparse.Namespace,
                   name: str,
                   command: list[str],
                   timeout: float | None = None) -> dict[str, Any]:
    validate_command(command)
    capture = run_capture(args, name, command, timeout=timeout)
    file_path = write_capture(store, name, capture.text or capture.error)
    return {
        "name": name,
        "command": capture.command,
        "ok": capture.ok,
        "rc": capture.rc,
        "status": capture.status,
        "duration_sec": capture.duration_sec,
        "file": file_path,
        "text": capture.text,
        "error": capture.error,
    }


def cleaned_payload_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in strip_cmdv1_text(text).splitlines():
        line = raw_line.strip()
        line = RUN_PID_INLINE_RE.sub("", line)
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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reset_private_dir(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        ensure_private_dir(path)
        return
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"refusing non-directory output path: {path}")
    shutil.rmtree(path)
    ensure_private_dir(path)


def write_system_file(system_root: Path, rel: str, data: bytes) -> None:
    if not is_safe_rel(rel):
        raise RuntimeError(f"unsafe system output path: {rel}")
    dest = system_root / rel
    resolved_root = system_root.resolve()
    resolved_parent = dest.parent.resolve() if dest.parent.exists() else dest.parent
    try:
        resolved_parent.relative_to(resolved_root)
    except ValueError as exc:
        raise RuntimeError(f"destination escapes system root: {dest}") from exc
    write_private_bytes(dest, data)


def pull_remote_file(store: EvidenceStore,
                     args: argparse.Namespace,
                     system_root: Path,
                     rel: str,
                     total_bytes: int) -> tuple[dict[str, Any] | None, int, dict[str, Any]]:
    stat_record = capture_device(store, args, f"stat-{rel}", ["stat", remote_path(rel)], timeout=25.0)
    if not stat_record["ok"]:
        return None, total_bytes, {"path": rel, "reason": "stat-failed", "record": stat_record["file"]}
    expected_size = parse_stat_size(stat_record["text"])
    if expected_size is None:
        return None, total_bytes, {"path": rel, "reason": "stat-size-missing", "record": stat_record["file"]}
    if expected_size > args.max_file_bytes:
        return None, total_bytes, {"path": rel, "reason": f"file-too-large:{expected_size}", "record": stat_record["file"]}
    if total_bytes + expected_size > args.max_total_bytes:
        return None, total_bytes, {"path": rel, "reason": f"total-size-limit:{total_bytes + expected_size}", "record": stat_record["file"]}
    record = capture_device(
        store,
        args,
        f"base64-{rel}",
        ["run", "/cache/bin/toybox", "base64", "-w", "0", remote_path(rel)],
        timeout=max(args.timeout, 120.0),
    )
    if not record["ok"]:
        return None, total_bytes, {"path": rel, "reason": "base64-failed", "record": record["file"]}
    try:
        data = base64.b64decode(extract_base64_payload(record["text"]), validate=True)
    except (binascii.Error, RuntimeError) as exc:
        return None, total_bytes, {"path": rel, "reason": f"base64-decode-failed:{exc}", "record": record["file"]}
    if len(data) != expected_size:
        return None, total_bytes, {"path": rel, "reason": f"size-mismatch:{len(data)}!={expected_size}", "record": record["file"]}
    write_system_file(system_root, rel, data)
    copied = {
        "relative_path": rel,
        "library": Path(rel).name,
        "size": len(data),
        "sha256": sha256_bytes(data),
        "source": remote_path(rel),
    }
    return copied, total_bytes + len(data), {"path": rel, "reason": "copied", "record": record["file"]}


def decide(requested_names: list[str], copied: list[dict[str, Any]], version_matches: bool) -> tuple[str, str, bool]:
    copied_names = {item["library"] for item in copied}
    missing_names = [name for name in requested_names if name not in copied_names]
    if missing_names:
        return "system-export-blocked", f"requested libraries missing from system root: {', '.join(missing_names)}", False
    if not version_matches:
        return "manual-review-required", "device version did not match expected native init", False
    return "system-root-ready", "Android core/system library evidence is ready for v221 rerun", True


def next_commands(system_root: Path) -> list[list[str]]:
    rel_root = str(system_root.relative_to(REPO_ROOT) if system_root.is_relative_to(REPO_ROOT) else system_root)
    return [
        [
            "python3",
            "scripts/revalidation/wifi_vendor_elf_library_closure.py",
            "--vendor-root",
            "tmp/wifi/v222-vendor-root-evidence-export/vendor-root",
            "--system-root",
            rel_root,
            "--out-dir",
            "tmp/wifi/v221-host-vendor-elf-library-evidence",
        ],
        [
            "python3",
            "scripts/revalidation/wifi_android_env_shim_materialize.py",
            "--vendor-root",
            "tmp/wifi/v222-vendor-root-evidence-export/vendor-root",
            "--out-dir",
            "tmp/wifi/v224-android-env-shim-materialize",
        ],
        [
            "python3",
            "scripts/revalidation/wifi_exposure_security_gate_v3.py",
            "--out-dir",
            "tmp/wifi/v225-exposure-security-gate-v3",
        ],
    ]


def build_summary(manifest: dict[str, Any]) -> str:
    copied_rows = [
        [item["relative_path"], str(item["size"]), item["sha256"][:16]]
        for item in manifest["copied_files"]
    ]
    missing_rows = [[item["path"], item["reason"]] for item in manifest["missing_or_skipped_files"]]
    lines = [
        "# v227 Android Core/System Library Evidence Export",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        f"- output_system_root: `{manifest['output_system_root']}`",
        f"- requested_libraries: `{', '.join(manifest['requested_libraries'])}`",
        "",
        "## Copied Files",
        "",
        markdown_table(["path", "size", "sha256 prefix"], copied_rows or [["none", "0", ""]]),
        "",
        "## Missing / Skipped Candidates",
        "",
        markdown_table(["path", "reason"], missing_rows or [["none", "none"]]),
        "",
        "## Next Commands",
        "",
        "```bash",
        "\n".join(" ".join(command) for command in manifest["next_commands"]),
        "```",
        "",
        "## Guardrails",
        "",
    ]
    for guardrail in manifest["guardrails"]:
        lines.append(f"- {guardrail}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    validate_command_guard()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    system_root = out_dir / "system-root"
    reset_private_dir(system_root)

    v221 = load_json(args.v221_manifest)
    requested_names = unresolved_library_names(v221, args.library)
    rels = target_rels(requested_names)
    captures: list[dict[str, Any]] = []
    copied_files: list[dict[str, Any]] = []
    missing_or_skipped: list[dict[str, Any]] = []
    total_bytes = 0

    captures.append(capture_device(store, args, "version", ["version"], timeout=15.0))
    version_matches = args.expect_version in captures[-1]["text"]
    captures.append(capture_device(store, args, "status", ["status"], timeout=25.0))
    captures.append(capture_device(store, args, "bootstatus", ["bootstatus"], timeout=25.0))
    mount_record = capture_device(store, args, "mountsystem-ro", ["mountsystem", "ro"], timeout=35.0)
    captures.append(mount_record)
    captures.append(capture_device(store, args, "proc-mounts", ["cat", "/proc/mounts"], timeout=20.0))

    if not mount_record["ok"]:
        decision, reason, pass_ok = "system-export-blocked", "mountsystem ro failed", False
    else:
        for rel in rels:
            copied, total_bytes, evidence = pull_remote_file(store, args, system_root, rel, total_bytes)
            if copied is None:
                missing_or_skipped.append(evidence)
                continue
            copied_files.append(copied)
            missing_or_skipped.append(evidence)
        decision, reason, pass_ok = decide(requested_names, copied_files, version_matches)

    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "mode": "android-core-system-library-evidence-export",
        "output_system_root": str(system_root),
        "requested_libraries": requested_names,
        "target_relative_paths": rels,
        "copied_file_count": len(copied_files),
        "copied_total_bytes": total_bytes,
        "copied_files": copied_files,
        "missing_or_skipped_files": missing_or_skipped,
        "version_matches": version_matches,
        "captures": captures,
        "source_decisions": {
            "v221": v221.get("decision"),
        },
        "inputs": {
            "v221_manifest": str(repo_path(args.v221_manifest)),
        },
        "next_commands": next_commands(system_root),
        "guardrails": [
            "read-only system mount through mountsystem ro only",
            "no Android daemon execution",
            "no Android service start",
            "no rfkill write",
            "no Wi-Fi scan/connect",
            "no credential collection",
            "no system or vendor write",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
