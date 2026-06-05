#!/usr/bin/env python3
"""V1942 read-only export of bounded QCRIL/radio vendor artifacts."""

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

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, ensure_private_dir, write_private_bytes


CYCLE = "V1942"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_OUT_DIR = repo_path("tmp/wifi/v1942-qcril-radio-vendor-artifact-export")
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1942_QCRIL_RADIO_VENDOR_ARTIFACT_EXPORT_2026-06-04.md")
PROBE_PREFIX = "/tmp/a90-v1942-"
BLOCK_NAME = "sda29"
SCAN_DIRS = (
    "bin",
    "bin/hw",
    "lib64",
    "lib64/hw",
    "lib",
    "lib/hw",
    "etc/init",
    "etc/vintf",
    "etc/permissions",
)
DIRECT_TARGETS = (
    "bin/hw/vendor.qti.hardware.radio@1.0-service",
    "bin/hw/vendor.qti.hardware.radio@1.1-service",
    "bin/hw/vendor.qti.hardware.radio@1.2-service",
    "bin/hw/vendor.qti.hardware.radio@1.3-service",
    "bin/hw/vendor.qti.hardware.radio@1.4-service",
    "bin/hw/vendor.qti.hardware.radio@1.5-service",
    "bin/hw/vendor.qti.hardware.radio@1.6-service",
    "bin/hw/vendor.samsung.hardware.radio@1.2-service",
    "bin/qcrild",
    "bin/rild",
    "bin/pm-service",
    "lib64/libqcrilNr.so",
    "lib64/libqcrilFramework.so",
    "lib64/libqcrilDataModule.so",
    "lib64/libril-qc-hal-qmi.so",
    "lib64/libril-qcril-hook-oem.so",
    "lib64/libperipheral_client.so",
    "lib64/libperipheral_client_qcci.so",
    "lib/libqcrilNr.so",
    "lib/libqcrilFramework.so",
    "lib/libril-qc-hal-qmi.so",
    "lib/libril-qcril-hook-oem.so",
    "lib/libperipheral_client.so",
    "lib/libperipheral_client_qcci.so",
)
LIBRARY_DIRS = (
    "lib64",
    "lib",
    "lib64/hw",
    "lib/hw",
    "lib64/vndk-sp",
    "lib/vndk-sp",
)
ANDROID_CORE_LIBS = {
    "ld-android.so",
    "libbase.so",
    "libbinder.so",
    "libc++.so",
    "libc.so",
    "libcutils.so",
    "libdl.so",
    "libhidlbase.so",
    "libhidltransport.so",
    "liblog.so",
    "libm.so",
    "libutils.so",
    "libz.so",
}
FORBIDDEN_OUTPUT_PARTS = {"data", "misc", "wifi", "wpa_supplicant.conf"}
ARTIFACT_RE = re.compile(
    r"(?:qcril|qcrild|rild|libril|radio|vendor\.qti\.hardware\.radio|"
    r"vendor\.samsung\.hardware\.radio|peripheral|per_mgr|pm-service)",
    re.IGNORECASE,
)
BROADCAST_RADIO_RE = re.compile(r"broadcastradio", re.IGNORECASE)
INTERESTING_STRING_RE = re.compile(
    r"(QCRIL|PM-PROXY|PerMgr|peripheral|voting for modem|voting for SDX50M|"
    r"subsys_modem|/dev/subsys_modem|wlan_pd|wlanmdsp|SSCTL|servreg|wlfw)",
    re.IGNORECASE,
)
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


@dataclass(frozen=True)
class PulledFile:
    relative_path: str
    size: int
    sha256: str
    source: str
    reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--max-file-bytes", type=int, default=96 * 1024 * 1024)
    parser.add_argument("--max-total-bytes", type=int, default=384 * 1024 * 1024)
    parser.add_argument("--max-targets", type=int, default=120)
    parser.add_argument("--max-elf-objects", type=int, default=180)
    parser.add_argument("--skip-libs", action="store_true")
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "_", value).strip("_") or "capture"


def is_safe_rel(relative_path: str) -> bool:
    path = Path(relative_path)
    lowered = relative_path.lower()
    if not relative_path or path.is_absolute() or ".." in path.parts:
        return False
    return not any(part.lower() in FORBIDDEN_OUTPUT_PARTS for part in path.parts) and "wpa_supplicant.conf" not in lowered


def remote_path(probe: ProbePaths, relative_path: str) -> str:
    if not is_safe_rel(relative_path):
        raise RuntimeError(f"unsafe vendor relative path: {relative_path}")
    return f"{probe.mountpoint}/{relative_path}"


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


def validate_remote_vendor_path(probe: ProbePaths, path: str) -> None:
    if not path.startswith(probe.mountpoint + "/"):
        raise RuntimeError(f"path outside vendor mount: {path}")
    relative_path = path.removeprefix(probe.mountpoint + "/")
    if not is_safe_rel(relative_path):
        raise RuntimeError(f"unsafe remote vendor path: {path}")


def validate_command(command: list[str], probe: ProbePaths | None = None) -> None:
    name = command[0] if command else ""
    joined = " ".join(command)
    if name in {"version", "status", "bootstatus", "selftest"}:
        if len(command) != 1:
            raise RuntimeError(f"unexpected {name} command: {joined}")
        return
    if name == "cat":
        if len(command) == 2 and command[1] in {"/sys/class/block/sda29/dev", "/proc/mounts"}:
            return
        raise RuntimeError(f"cat outside allowed paths: {joined}")
    if name == "mkdir":
        if not probe or len(command) != 2 or command[1] not in {probe.base, probe.mountpoint}:
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
    if name in {"ls", "stat"}:
        if not probe or len(command) != 2:
            raise RuntimeError(f"unexpected {name} command: {joined}")
        validate_remote_vendor_path(probe, command[1])
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
        if len(command) == 6 and command[1:5] == ["/cache/bin/toybox", "base64", "-w", "0"]:
            validate_remote_vendor_path(probe, command[5])
            return
        raise RuntimeError(f"unexpected run command: {joined}")
    raise RuntimeError(f"unexpected command: {joined}")


def validate_command_guard() -> None:
    probe = make_probe_paths("guard", "259", "29")
    commands = [
        ["version"],
        ["status"],
        ["bootstatus"],
        ["selftest"],
        ["cat", "/sys/class/block/sda29/dev"],
        ["mkdir", probe.base],
        ["mkdir", probe.mountpoint],
        ["mknodb", probe.node, probe.major, probe.minor],
        ["run", "/cache/bin/toybox", "mount", "-t", "ext4", "-o", "ro,noload", probe.node, probe.mountpoint],
        ["ls", remote_path(probe, "bin/hw")],
        ["stat", remote_path(probe, "bin/hw/vendor.qti.hardware.radio@1.0-service")],
        ["run", "/cache/bin/toybox", "base64", "-w", "0", remote_path(probe, "bin/hw/vendor.qti.hardware.radio@1.0-service")],
        ["cat", "/proc/mounts"],
        ["umount", probe.mountpoint],
    ]
    for command in commands:
        validate_command(command, probe)


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    path = store.write_text(f"native/commands/{safe_name(name)}.txt", text.rstrip() + "\n")
    return rel(path)


def capture_device(
    store: EvidenceStore,
    args: argparse.Namespace,
    probe: ProbePaths | None,
    name: str,
    command: list[str],
    timeout: float | None = None,
) -> dict[str, Any]:
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
        if not line or line.startswith(("cmdv1 ", "cmdv1x ")):
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


def parse_ls_names(text: str) -> list[str]:
    names: list[str] = []
    for line in cleaned_payload_lines(text):
        if "No such file" in line or line.startswith("ls:"):
            continue
        for token in line.split():
            if token in {".", ".."} or "/" in token:
                continue
            names.append(token)
    return sorted(set(names))


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


def write_vendor_file(vendor_root: Path, relative_path: str, data: bytes) -> None:
    if not is_safe_rel(relative_path):
        raise RuntimeError(f"unsafe vendor output path: {relative_path}")
    destination = vendor_root / relative_path
    destination_parent = destination.parent
    if destination_parent.exists():
        resolved_parent = destination_parent.resolve()
        try:
            resolved_parent.relative_to(vendor_root.resolve())
        except ValueError as exc:
            raise RuntimeError(f"destination escapes vendor root: {destination}") from exc
    write_private_bytes(destination, data)


def run_readelf_needed(path: Path) -> tuple[str, list[str]]:
    try:
        result = subprocess.run(
            ["readelf", "-W", "-d", str(path)],
            cwd=repo_path("."),
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


def run_strings_hits(path: Path, limit: int = 40) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["strings", "-a", str(path)],
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
        )
    except FileNotFoundError:
        return {"status": "strings-unavailable", "count": 0, "samples": []}
    except subprocess.TimeoutExpired:
        return {"status": "strings-timeout", "count": 0, "samples": []}
    if result.returncode != 0:
        return {"status": f"strings-rc-{result.returncode}", "count": 0, "samples": []}
    hits: list[str] = []
    count = 0
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if INTERESTING_STRING_RE.search(line):
            count += 1
            if len(hits) < limit:
                hits.append(line[:240])
    return {"status": "ok", "count": count, "samples": hits}


def dependency_candidates(library_name: str) -> list[str]:
    return [f"{directory}/{library_name}" for directory in LIBRARY_DIRS]


def is_artifact_path(relative_path: str) -> bool:
    return bool(ARTIFACT_RE.search(relative_path)) and not BROADCAST_RADIO_RE.search(relative_path)


def queue_needed_libraries(
    vendor_root: Path,
    relative_path: str,
    queue: deque[tuple[str, str]],
    seen_requested: set[str],
    dependency_records: list[dict[str, Any]],
) -> None:
    status, needed = run_readelf_needed(vendor_root / relative_path)
    dependency_records.append({"path": relative_path, "readelf_status": status, "needed": needed})
    if status != "ok":
        return
    for library_name in needed:
        if library_name in ANDROID_CORE_LIBS:
            dependency_records.append({"path": relative_path, "library": library_name, "classification": "android-core-runtime-required"})
            continue
        for candidate in dependency_candidates(library_name):
            if candidate not in seen_requested:
                queue.append((candidate, f"needed-by:{relative_path}:{library_name}"))
                seen_requested.add(candidate)


def pull_remote_file(
    store: EvidenceStore,
    args: argparse.Namespace,
    probe: ProbePaths,
    vendor_root: Path,
    relative_path: str,
    reason: str,
    total_bytes: int,
) -> tuple[PulledFile | None, int, dict[str, Any]]:
    stat_record = capture_device(store, args, probe, f"stat-{relative_path}", ["stat", remote_path(probe, relative_path)], timeout=25.0)
    if not stat_record["ok"]:
        return None, total_bytes, {"path": relative_path, "reason": "stat-failed", "record": stat_record["file"]}
    expected_size = parse_stat_size(stat_record["text"])
    if expected_size is None:
        return None, total_bytes, {"path": relative_path, "reason": "stat-size-missing", "record": stat_record["file"]}
    if expected_size > args.max_file_bytes:
        return None, total_bytes, {"path": relative_path, "reason": f"file-too-large:{expected_size}", "record": stat_record["file"]}
    if total_bytes + expected_size > args.max_total_bytes:
        return None, total_bytes, {"path": relative_path, "reason": f"total-size-limit:{total_bytes + expected_size}", "record": stat_record["file"]}

    record = capture_device(
        store,
        args,
        probe,
        f"base64-{relative_path}",
        ["run", "/cache/bin/toybox", "base64", "-w", "0", remote_path(probe, relative_path)],
        timeout=max(args.timeout, 120.0),
    )
    if not record["ok"]:
        return None, total_bytes, {"path": relative_path, "reason": "base64-failed", "record": record["file"]}
    try:
        data = base64.b64decode(extract_base64_payload(record["text"]), validate=True)
    except (binascii.Error, RuntimeError) as exc:
        return None, total_bytes, {"path": relative_path, "reason": f"base64-decode-failed:{exc}", "record": record["file"]}
    if len(data) != expected_size:
        return None, total_bytes, {"path": relative_path, "reason": f"size-mismatch:{len(data)}!={expected_size}", "record": record["file"]}

    write_vendor_file(vendor_root, relative_path, data)
    return (
        PulledFile(relative_path, len(data), sha256_bytes(data), remote_path(probe, relative_path), reason),
        total_bytes + len(data),
        {"path": relative_path, "reason": "copied", "record": record["file"]},
    )


def discover_targets(listings: dict[str, list[str]], max_targets: int) -> tuple[list[tuple[str, str]], list[dict[str, Any]]]:
    discovered: list[tuple[str, str]] = []
    notes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for relative_path in DIRECT_TARGETS:
        if relative_path not in seen:
            discovered.append((relative_path, "direct-target"))
            seen.add(relative_path)
    for directory, names in listings.items():
        for name in names:
            relative_path = f"{directory}/{name}"
            if relative_path in seen:
                continue
            if is_artifact_path(relative_path):
                discovered.append((relative_path, "directory-match"))
                seen.add(relative_path)
    if len(discovered) > max_targets:
        notes.append({"path": "target-discovery", "reason": f"truncated:{len(discovered)}>{max_targets}"})
        discovered = discovered[:max_targets]
    return discovered, notes


def decide(
    pulled_files: list[PulledFile],
    missing_or_skipped: list[dict[str, Any]],
    cleanup_ok: bool,
    version_matches: bool,
    post_selftest_fail0: bool,
) -> tuple[str, str, bool]:
    pulled_paths = {item.relative_path for item in pulled_files}
    qcril_paths = [path for path in pulled_paths if is_artifact_path(path)]
    if not cleanup_ok:
        return "qcril-radio-artifact-export-cleanup-review", "temporary vendor mount cleanup did not fully pass", False
    if not version_matches or not post_selftest_fail0:
        return "qcril-radio-artifact-export-baseline-review", "native version or post selftest baseline did not verify", False
    if qcril_paths:
        return "qcril-radio-artifacts-exported-readonly", "bounded QCRIL/radio/peripheral vendor artifacts were exported read-only for host/source comparison", True
    if missing_or_skipped:
        return "qcril-radio-artifacts-not-copied-review", "candidate discovery produced paths but none copied; review skipped records", False
    return "qcril-radio-artifacts-absent-from-sda29", "bounded vendor scan found no QCRIL/radio/peripheral artifacts on sda29", True


def build_report(manifest: dict[str, Any]) -> str:
    pulled_rows = [
        [item["relative_path"], str(item["size"]), item["sha256"][:16], item["reason"]]
        for item in manifest["pulled_files"]
        if is_artifact_path(item["relative_path"])
    ][:40]
    dependency_rows = [
        [item["path"], item["readelf_status"], ", ".join(item.get("needed", [])[:8])]
        for item in manifest["dependencies"]
        if "needed" in item
    ][:30]
    string_rows = [
        [path, str(summary["count"]), summary["status"], " | ".join(summary["samples"][:3])]
        for path, summary in manifest["string_hits"].items()
        if summary["count"] > 0
    ][:30]
    missing_rows = [[item["path"], item["reason"]] for item in manifest["missing_or_skipped_files"][:40]]
    lines = [
        "# Native Init V1942 QCRIL/Radio Vendor Artifact Export",
        "",
        "## Summary",
        "",
        f"- Cycle: `{manifest['cycle']}`",
        "- Type: live read-only bounded vendor artifact export from `sda29`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["version matches", manifest["version_matches"], manifest["expect_version"]],
                ["post selftest fail=0", manifest["post_selftest_fail0"], manifest["post_selftest_file"]],
                ["cleanup ok", manifest["probe"]["cleanup_ok"], manifest["probe"]["mountpoint"]],
                ["target count", manifest["target_count"], "direct targets plus bounded directory matches"],
                ["pulled files", manifest["pulled_file_count"], f"{manifest['pulled_total_bytes']} bytes"],
                ["skip libs", manifest["limits"]["skip_libs"], "direct artifacts only when true"],
                ["interesting string files", len(string_rows), "host strings over copied artifacts only"],
            ],
        ),
        "",
        "## Pulled QCRIL/Radio/Peripheral Artifacts",
        "",
        markdown_table(["path", "size", "sha256 prefix", "reason"], pulled_rows or [["none", "0", "", ""]]),
        "",
        "## Host String Hits",
        "",
        markdown_table(["path", "hit count", "status", "sample"], string_rows or [["none", "0", "", ""]]),
        "",
        "## ELF Dependency Samples",
        "",
        markdown_table(["path", "readelf", "needed sample"], dependency_rows or [["none", "", ""]]),
        "",
        "## Missing / Skipped Sample",
        "",
        markdown_table(["path", "reason"], missing_rows or [["none", "none"]]),
        "",
        "## Interpretation",
        "",
        "- This is source/diff evidence only; no QCRIL/radio daemon was executed on native.",
        "- The export keeps QCRIL as a read-only comparison lead because Android's QCRIL vote remains SDX50M-coupled in V1941.",
        "- Next host-only step: disassemble/string-diff the exported QCRIL/peripheral artifacts against the Android PM voter window and isolate any internal-modem WLAN-PD servreg/SSCTL producer action that is not SDX50M/eSoC/PCIe coupled.",
        "",
        "## Safety Scope",
        "",
        "- Temporary `sda29` mount only, exact `ext4 ro,noload`.",
        "- No vendor/firmware/partition write, no remount-write, no daemon execution.",
        "- No `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, restart-PD, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
    ]
    return "\n".join(str(line) for line in lines)


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
    listings: dict[str, list[str]] = {}
    string_hits: dict[str, dict[str, Any]] = {}
    total_bytes = 0
    cleanup_ok = True
    version_matches = False
    post_selftest_fail0 = False
    post_selftest_file = ""
    probe: ProbePaths | None = None

    captures.append(capture_device(store, args, None, "version", ["version"], timeout=15.0))
    version_matches = args.expect_version in captures[-1]["text"]
    captures.append(capture_device(store, args, None, "pre-selftest", ["selftest"], timeout=15.0))
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

        for directory in SCAN_DIRS:
            record = capture_device(store, args, probe, f"ls-{directory}", ["ls", remote_path(probe, directory)], timeout=25.0)
            captures.append(record)
            if record["ok"]:
                listings[directory] = parse_ls_names(record["text"])
            else:
                missing_or_skipped.append({"path": directory, "reason": "ls-failed", "record": record["file"]})

        targets, discovery_notes = discover_targets(listings, args.max_targets)
        missing_or_skipped.extend(discovery_notes)
        queue: deque[tuple[str, str]] = deque(targets)
        requested = {path for path, _reason in targets}
        while queue and len(pulled_files) < args.max_elf_objects:
            relative_path, reason = queue.popleft()
            if any(item.relative_path == relative_path for item in pulled_files):
                continue
            pulled, total_bytes, evidence = pull_remote_file(store, args, probe, vendor_source, relative_path, reason, total_bytes)
            if pulled is None:
                missing_or_skipped.append(evidence)
                continue
            pulled_files.append(pulled)
            string_hits[relative_path] = run_strings_hits(vendor_source / relative_path)
            if not args.skip_libs:
                queue_needed_libraries(vendor_source, relative_path, queue, requested, dependencies)
        if queue:
            missing_or_skipped.append({"path": "dependency-queue", "reason": f"truncated-after-{args.max_elf_objects}-objects"})
    except Exception as exc:
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
        post_selftest = capture_device(store, args, None, "post-selftest", ["selftest"], timeout=15.0)
        captures.append(post_selftest)
        post_selftest_fail0 = "fail=0" in post_selftest["text"]
        post_selftest_file = post_selftest["file"]

    label, reason, pass_ok = decide(pulled_files, missing_or_skipped, cleanup_ok, version_matches, post_selftest_fail0)
    manifest = {
        "created": created,
        "cycle": CYCLE,
        "pass": pass_ok,
        "decision": f"v1942-{label}-{'pass' if pass_ok else 'review'}",
        "label": label,
        "reason": reason,
        "mode": "native-qcril-radio-vendor-artifact-readonly-export",
        "run_id": run_id,
        "expect_version": args.expect_version,
        "version_matches": version_matches,
        "post_selftest_fail0": post_selftest_fail0,
        "post_selftest_file": post_selftest_file,
        "out_dir": rel(out_dir),
        "output_vendor_source": rel(vendor_source if pulled_files else out_dir),
        "target_count": len(discover_targets(listings, args.max_targets)[0]),
        "pulled_file_count": len(pulled_files),
        "pulled_total_bytes": total_bytes,
        "pulled_files": [item.__dict__ for item in pulled_files],
        "missing_or_skipped_files": missing_or_skipped,
        "dependencies": dependencies,
        "listings": listings,
        "string_hits": string_hits,
        "probe": {
            "block": BLOCK_NAME,
            "major": probe.major if probe else None,
            "minor": probe.minor if probe else None,
            "base": probe.base if probe else None,
            "node": probe.node if probe else None,
            "mountpoint": probe.mountpoint if probe else None,
            "cleanup_ok": cleanup_ok,
        },
        "captures": [{key: value for key, value in record.items() if key != "text"} for record in captures],
        "limits": {
            "max_file_bytes": args.max_file_bytes,
            "max_total_bytes": args.max_total_bytes,
            "max_targets": args.max_targets,
            "max_elf_objects": args.max_elf_objects,
            "skip_libs": args.skip_libs,
        },
        "guardrails": [
            "temporary vendor mount only",
            "mount command is exact ext4 ro,noload",
            "no persistent /dev/block/sda29 node",
            "no vendor or firmware writes",
            "no daemon execution",
            "no /dev/subsys_esoc0, eSoC, PCIe, GDSC, PMIC, GPIO, regulator action",
            "no Wi-Fi HAL, scan, connect, credentials, DHCP, routes, external ping",
            "private no-follow host evidence output",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    REPORT_PATH.write_text(build_report(manifest), encoding="utf-8")
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={manifest['decision']} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
