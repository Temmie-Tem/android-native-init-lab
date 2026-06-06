#!/usr/bin/env python3
"""Export minimal vendor Wi-Fi/CNSS files from a live read-only native mount."""

from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from collections import deque
from dataclasses import dataclass
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v226-vendor-root-live-export")
DEFAULT_V221_MANIFEST = Path("tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json")
PROBE_PREFIX = "/tmp/a90-v226-"
BLOCK_NAME = "sda29"
TARGET_RELS = ("bin/cnss-daemon", "bin/cnss_diag")
LIBRARY_DIRS = (
    "lib64",
    "lib",
    "lib64/hw",
    "lib/hw",
    "lib64/vndk-sp",
    "lib/vndk-sp",
    "lib64/egl",
    "lib/egl",
)
ANDROID_CORE_LIBS = {
    "ld-android.so",
    "libbase.so",
    "libbinder.so",
    "libc++.so",
    "libc.so",
    "libcrypto.so",
    "libdl.so",
    "libhardware.so",
    "libhidlbase.so",
    "libhidltransport.so",
    "liblog.so",
    "libm.so",
    "libprotobuf-cpp-lite.so",
    "libselinux.so",
    "libssl.so",
    "libstdc++.so",
    "libutils.so",
    "libz.so",
}
FORBIDDEN_OUTPUT_PARTS = {"data", "misc", "wifi", "wpa_supplicant.conf"}
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


@dataclass(frozen=True)
class ProbePaths:
    run_id: str
    base: str
    node: str
    mountpoint: str
    major: str
    minor: str


@dataclass
class PulledFile:
    relative_path: str
    size: int
    sha256: str
    source: str
    reason: str


def default_out_dir() -> Path:
    return REPO_ROOT / DEFAULT_OUT_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--max-file-bytes", type=int, default=64 * 1024 * 1024)
    parser.add_argument("--max-total-bytes", type=int, default=256 * 1024 * 1024)
    parser.add_argument("--max-elf-objects", type=int, default=200)
    parser.add_argument("--v221-manifest", type=Path, default=DEFAULT_V221_MANIFEST)
    parser.add_argument("--skip-libs", action="store_true", help="pull only required service binaries")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "_", value).strip("_") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def is_safe_rel(rel: str) -> bool:
    path = Path(rel)
    parts = path.parts
    lowered = rel.lower()
    if not rel or path.is_absolute() or ".." in parts:
        return False
    return not any(part.lower() in FORBIDDEN_OUTPUT_PARTS for part in parts) and "wpa_supplicant.conf" not in lowered


def remote_path(probe: ProbePaths, rel: str) -> str:
    if not is_safe_rel(rel):
        raise RuntimeError(f"unsafe vendor relative path: {rel}")
    return f"{probe.mountpoint}/{rel}"


def make_probe_paths(run_id: str, major: str, minor: str) -> ProbePaths:
    base = f"{PROBE_PREFIX}{safe_name(run_id)}"
    return ProbePaths(
        run_id=run_id,
        base=base,
        node=f"{base}/{BLOCK_NAME}",
        mountpoint=f"{base}/vendor",
        major=major,
        minor=minor,
    )


def validate_command(command: list[str], probe: ProbePaths | None = None) -> None:
    name = command[0] if command else ""
    joined = " ".join(command)
    if name in {"version", "status", "bootstatus"}:
        if len(command) != 1:
            raise RuntimeError(f"unexpected {name} command: {joined}")
        return
    if name in {"cat", "ls", "stat"}:
        if len(command) != 2:
            raise RuntimeError(f"unexpected {name} arity: {joined}")
        path = command[1]
        if path.startswith("/sys/class/block/sda29/") or path == "/proc/mounts":
            return
        if probe and path.startswith(probe.mountpoint + "/"):
            return
        if probe and path == probe.node:
            return
        raise RuntimeError(f"{name} outside allowed paths: {joined}")
    if name == "mkdir":
        if not probe or len(command) != 2 or not command[1].startswith(probe.base):
            raise RuntimeError(f"mkdir outside probe path: {joined}")
        return
    if name == "mknodb":
        if not probe or command != ["mknodb", probe.node, probe.major, probe.minor]:
            raise RuntimeError(f"unexpected mknodb command: {joined}")
        return
    if name == "umount":
        if not probe or command != ["umount", probe.mountpoint]:
            raise RuntimeError(f"unexpected umount command: {joined}")
        return
    if name == "run":
        if not probe:
            raise RuntimeError(f"run command requires probe context: {joined}")
        mount_command = [
            "run",
            "/cache/bin/toybox",
            "mount",
            "-t",
            "ext4",
            "-o",
            "ro,noload",
            probe.node,
            probe.mountpoint,
        ]
        if command == mount_command:
            return
        if len(command) >= 5 and command[1:4] == ["/cache/bin/toybox", "base64", "-w"]:
            if command[4] != "0" or len(command) != 6 or not command[5].startswith(probe.mountpoint + "/"):
                raise RuntimeError(f"unexpected base64 pull command: {joined}")
            return
        raise RuntimeError(f"unexpected run command: {joined}")
    raise RuntimeError(f"unexpected command: {joined}")


def validate_command_guard() -> None:
    probe = make_probe_paths("guard", "259", "22")
    commands = [
        ["version"],
        ["status"],
        ["bootstatus"],
        ["cat", "/sys/class/block/sda29/dev"],
        ["mkdir", probe.base],
        ["mkdir", probe.mountpoint],
        ["mknodb", probe.node, probe.major, probe.minor],
        ["run", "/cache/bin/toybox", "mount", "-t", "ext4", "-o", "ro,noload", probe.node, probe.mountpoint],
        ["stat", remote_path(probe, "bin/cnss-daemon")],
        ["run", "/cache/bin/toybox", "base64", "-w", "0", remote_path(probe, "bin/cnss-daemon")],
        ["umount", probe.mountpoint],
    ]
    for command in commands:
        validate_command(command, probe)


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    path = store.write_text(f"native/commands/{safe_name(name)}.txt", text.rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def capture_device(store: EvidenceStore,
                   args: argparse.Namespace,
                   probe: ProbePaths | None,
                   name: str,
                   command: list[str],
                   timeout: float | None = None) -> dict[str, Any]:
    validate_command(command, probe)
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


def parse_block_dev(text: str) -> tuple[str, str]:
    payload = strip_cmdv1_text(text).strip()
    match = re.search(r"\b(\d+):(\d+)\b", payload)
    if not match:
        raise RuntimeError(f"could not parse sda29 major/minor from: {payload!r}")
    return match.group(1), match.group(2)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_vendor_file(vendor_root: Path, rel: str, data: bytes) -> None:
    if not is_safe_rel(rel):
        raise RuntimeError(f"unsafe vendor output path: {rel}")
    dest = vendor_root / rel
    resolved_parent = dest.parent.resolve() if dest.parent.exists() else dest.parent
    try:
        resolved_parent.relative_to(vendor_root.resolve())
    except ValueError as exc:
        raise RuntimeError(f"destination escapes vendor root: {dest}") from exc
    write_private_bytes(dest, data)


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


def pull_remote_file(store: EvidenceStore,
                     args: argparse.Namespace,
                     probe: ProbePaths,
                     vendor_root: Path,
                     rel: str,
                     reason: str,
                     total_bytes: int) -> tuple[PulledFile | None, int, dict[str, Any]]:
    stat_record = capture_device(store, args, probe, f"stat-{rel}", ["stat", remote_path(probe, rel)], timeout=25.0)
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
        probe,
        f"base64-{rel}",
        ["run", "/cache/bin/toybox", "base64", "-w", "0", remote_path(probe, rel)],
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

    write_vendor_file(vendor_root, rel, data)
    digest = sha256_bytes(data)
    pulled = PulledFile(rel, len(data), digest, remote_path(probe, rel), reason)
    return pulled, total_bytes + len(data), {"path": rel, "reason": "copied", "record": record["file"]}


def run_readelf_needed(path: Path) -> tuple[str, list[str]]:
    try:
        result = subprocess.run(
            ["readelf", "-W", "-d", str(path)],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=15,
        )
    except FileNotFoundError:
        return "readelf-unavailable", []
    except subprocess.TimeoutExpired:
        return "readelf-timeout", []
    if result.returncode != 0:
        return f"readelf-rc-{result.returncode}", []
    needed = sorted(set(re.findall(r"Shared library:\s*\[([^\]]+)\]", result.stdout)))
    return "ok", needed


def dependency_candidates(lib_name: str) -> list[str]:
    return [f"{directory}/{lib_name}" for directory in LIBRARY_DIRS]


def queue_needed_libraries(vendor_root: Path,
                           rel: str,
                           queue: deque[tuple[str, str]],
                           seen_requested: set[str],
                           dependency_records: list[dict[str, Any]]) -> None:
    status, needed = run_readelf_needed(vendor_root / rel)
    dependency_records.append({"path": rel, "readelf_status": status, "needed": needed})
    if status != "ok":
        return
    for lib_name in needed:
        if lib_name in ANDROID_CORE_LIBS:
            dependency_records.append({"path": rel, "library": lib_name, "classification": "android-core-runtime-required"})
            continue
        for candidate in dependency_candidates(lib_name):
            if candidate not in seen_requested:
                queue.append((candidate, f"needed-by:{rel}:{lib_name}"))
                seen_requested.add(candidate)


def build_summary(manifest: dict[str, Any]) -> str:
    pulled_rows = [
        [item["relative_path"], str(item["size"]), item["sha256"][:16], item["reason"]]
        for item in manifest["pulled_files"]
    ]
    missing_rows = [
        [item["path"], item["reason"]]
        for item in manifest["missing_or_skipped_files"]
    ]
    lines = [
        "# v226 Native Vendor Root Live Export",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        f"- output_vendor_source: `{manifest['output_vendor_source']}`",
        f"- pulled_files: `{manifest['pulled_file_count']}`",
        f"- pulled_total_bytes: `{manifest['pulled_total_bytes']}`",
        "",
        "## Pulled Files",
        "",
        markdown_table(["path", "size", "sha256 prefix", "reason"], pulled_rows or [["none", "0", "", ""]]),
        "",
        "## Missing / Skipped",
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


def next_commands(vendor_source: Path) -> list[list[str]]:
    rel_source = str(vendor_source.relative_to(REPO_ROOT) if vendor_source.is_relative_to(REPO_ROOT) else vendor_source)
    return [
        [
            "python3",
            "scripts/revalidation/wifi_vendor_root_evidence_export.py",
            "--source-vendor-root",
            rel_source,
            "--out-dir",
            "tmp/wifi/v222-vendor-root-evidence-export",
        ],
        [
            "python3",
            "scripts/revalidation/wifi_vendor_elf_library_closure.py",
            "--vendor-root",
            "tmp/wifi/v222-vendor-root-evidence-export/vendor-root",
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


def decide(pulled: list[PulledFile], missing: list[dict[str, Any]], cleanup_ok: bool) -> tuple[str, str, bool]:
    pulled_rels = {item.relative_path for item in pulled}
    missing_required = [rel for rel in TARGET_RELS if rel not in pulled_rels]
    if missing_required:
        return "live-export-blocked", f"required vendor binaries missing: {', '.join(missing_required)}", False
    if not cleanup_ok:
        return "manual-review-required", "vendor files were exported but cleanup did not fully pass", False
    if any(item["path"] in TARGET_RELS and item["reason"] != "copied" for item in missing):
        return "live-export-blocked", "required vendor binary copy had skipped evidence", False
    return "vendor-source-exported", "live read-only vendor source is ready for v222 rerun", True


def main() -> int:
    args = parse_args()
    validate_command_guard()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    vendor_source = out_dir / "vendor-source"
    reset_private_dir(vendor_source)

    created = dt.datetime.now(dt.timezone.utc).isoformat()
    run_id = args.run_id or "live-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    captures: list[dict[str, Any]] = []
    missing_or_skipped: list[dict[str, Any]] = []
    pulled_files: list[PulledFile] = []
    dependencies: list[dict[str, Any]] = []
    total_bytes = 0
    cleanup_ok = True
    probe: ProbePaths | None = None

    captures.append(capture_device(store, args, None, "version", ["version"], timeout=15.0))
    version_text = captures[-1]["text"]
    version_matches = args.expect_version in version_text
    captures.append(capture_device(store, args, None, "status", ["status"], timeout=25.0))
    captures.append(capture_device(store, args, None, "bootstatus", ["bootstatus"], timeout=25.0))
    block_dev = capture_device(store, args, None, "sys-sda29-dev", ["cat", "/sys/class/block/sda29/dev"], timeout=20.0)
    captures.append(block_dev)
    major, minor = parse_block_dev(block_dev["text"])
    probe = make_probe_paths(run_id, major, minor)

    try:
        for name, command, timeout in (
            ("mkdir-base", ["mkdir", probe.base], 20.0),
            ("mkdir-mountpoint", ["mkdir", probe.mountpoint], 20.0),
            ("mknodb-sda29", ["mknodb", probe.node, probe.major, probe.minor], 20.0),
            ("safe-ro-noload-mount", ["run", "/cache/bin/toybox", "mount", "-t", "ext4", "-o", "ro,noload", probe.node, probe.mountpoint], 45.0),
            ("mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0),
        ):
            record = capture_device(store, args, probe, name, command, timeout=timeout)
            captures.append(record)
            if not record["ok"]:
                raise RuntimeError(f"{name} failed; see {record['file']}")

        queue: deque[tuple[str, str]] = deque((rel, "target-binary") for rel in TARGET_RELS)
        requested = set(TARGET_RELS)
        while queue and len(pulled_files) < args.max_elf_objects:
            rel, reason = queue.popleft()
            if any(item.relative_path == rel for item in pulled_files):
                continue
            pulled, total_bytes, evidence = pull_remote_file(store, args, probe, vendor_source, rel, reason, total_bytes)
            if pulled is None:
                missing_or_skipped.append(evidence)
                continue
            pulled_files.append(pulled)
            if not args.skip_libs:
                queue_needed_libraries(vendor_source, rel, queue, requested, dependencies)
        if queue:
            missing_or_skipped.append({"path": "dependency-queue", "reason": f"truncated-after-{args.max_elf_objects}-objects"})
    except Exception as exc:  # noqa: BLE001 - manifest records partial evidence
        missing_or_skipped.append({"path": "live-export", "reason": str(exc)})
    finally:
        if probe is not None:
            cleanup_record = capture_device(store, args, probe, "cleanup-umount", ["umount", probe.mountpoint], timeout=25.0)
            captures.append(cleanup_record)
            cleanup_ok = cleanup_record["ok"]
            post_record = capture_device(store, args, probe, "post-proc-mounts", ["cat", "/proc/mounts"], timeout=20.0)
            captures.append(post_record)
            if probe.mountpoint in post_record["text"]:
                cleanup_ok = False
                missing_or_skipped.append({"path": probe.mountpoint, "reason": "still-mounted-after-cleanup"})

    decision, reason, pass_ok = decide(pulled_files, missing_or_skipped, cleanup_ok)
    manifest = {
        "created": created,
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "mode": "native-vendor-root-live-export",
        "run_id": run_id,
        "expect_version": args.expect_version,
        "version_matches": version_matches,
        "probe": {
            "block": BLOCK_NAME,
            "major": probe.major if probe else None,
            "minor": probe.minor if probe else None,
            "base": probe.base if probe else None,
            "node": probe.node if probe else None,
            "mountpoint": probe.mountpoint if probe else None,
            "cleanup_ok": cleanup_ok,
        },
        "output_dir": str(out_dir),
        "output_vendor_source": str(vendor_source if pulled_files else ""),
        "pulled_file_count": len(pulled_files),
        "pulled_total_bytes": total_bytes,
        "pulled_files": [item.__dict__ for item in pulled_files],
        "missing_or_skipped_files": missing_or_skipped,
        "dependencies": dependencies,
        "captures": [
            {k: v for k, v in record.items() if k != "text"}
            for record in captures
        ],
        "inputs": {
            "v221_manifest": str(repo_path(args.v221_manifest)),
            "v221_decision": load_json(args.v221_manifest).get("decision"),
        },
        "limits": {
            "max_file_bytes": args.max_file_bytes,
            "max_total_bytes": args.max_total_bytes,
            "max_elf_objects": args.max_elf_objects,
            "skip_libs": args.skip_libs,
        },
        "next_commands": next_commands(vendor_source),
        "guardrails": [
            "temporary vendor mount only",
            "mount command is exact ext4 ro,noload",
            "no persistent /dev/block/sda29 node",
            "no device writes",
            "no daemon execution",
            "no rfkill/link-up/scan/connect",
            "no credential collection",
            "private no-follow host evidence output",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
