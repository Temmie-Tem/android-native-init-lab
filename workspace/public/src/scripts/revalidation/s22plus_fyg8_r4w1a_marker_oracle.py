#!/usr/bin/env python3
"""Audit and parse the FYG8 R4W1-A dumpstate marker oracle host-only.

The ``audit`` command pins the effective FYG8 SELinux policy, system binaries,
init service definition, file contexts, and Samsung log-buffer sources. The
``parse`` command validates a complete streamed bugreport ZIP and classifies
the exact R4W1 marker only inside its ``LAST KMSG (/proc/last_kmsg)`` section.

Neither command contains a device transport, creates a boot artifact, or
authorizes a live run.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import stat
import sys
import tempfile
import zipfile
import zlib
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCHEMA = "s22plus_fyg8_r4w1a_marker_oracle_v1"
ROOT = Path(__file__).resolve().parents[5]
ORACLE_ROOT = ROOT / "workspace/private/work/s22plus_fyg8_r4w1a_oracle"
KERNEL_ROOT = (
    ROOT
    / "workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/msm-kernel"
)
DEFAULT_SETOOLS_PATH = (
    ROOT / "workspace/private/tools/selinux-analysis-debian/root/usr/lib/python3/dist-packages"
)

EXPECTED_MARKER = (
    b"[[S22R4W1|id=9ed5923b08c5eedbbdb0aaa6f6a5200c|"
    b"phase=RAMDISK_EXEC_ACCEPTED|pid=1|path=/init]]"
)
MARKER_FAMILY_PREFIX = b"[[S22R4W"
LAST_KMSG_HEADER = b"------ LAST KMSG (/proc/last_kmsg) ------"
MAX_ARCHIVE_SIZE = 2 * 1024 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 100_000
MAX_TOTAL_UNCOMPRESSED = 4 * 1024 * 1024 * 1024
MAX_MAIN_ENTRY_SIZE = 512 * 1024 * 1024
MAX_METADATA_ENTRY_SIZE = 4096
SCAN_CHUNK_SIZE = 1024 * 1024

PINS = {
    "policy": "9f3060ccc428a4fdd11183d7206c253dfc6735489208dbd0e3e5fe1b34667880",
    "vendor_policy_version": "4e90c4d01f877a1b658aec3119b36985333375a2e554f6d03c6732e2064d9cb4",
    "dumpstate": "b5de4fb2c0339c04dc6b9cc0c8063cb189d736b4a429f23417c9c09a20bfbe96",
    "bugreportz": "e10c143f8909bd8f79cf7528c1c1d12c81acbbd1e4e4e57e226652be508feaaa",
    "dumpstate_rc": "14ea29bf7ec4a37dadae5a68d0c494d86292b8bc1df8831eb36c566b31094c8b",
    "plat_file_contexts": "30a0b3a5317968e0fc82291dfdd75506d6355c478cbab830a1d34a7bd3d09214",
    "sec_log_buf_main": "296f4fc175d958feb35b92c8736faf6361ade2e7c447d9a9af5a93f59bdb97b8",
    "sec_log_buf_last_kmsg": "ba9e0f9f0832cbf666e55b51804515fc8298203fd37958ccdfb6bfbbe3524443",
}


class OracleError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_stream(stream: Any) -> str:
    digest = hashlib.sha256()
    while chunk := stream.read(SCAN_CHUNK_SIZE):
        digest.update(chunk)
    return digest.hexdigest()


def direct_regular_file(path: Path, maximum_size: int | None = None) -> Path:
    if path.is_symlink():
        raise OracleError(f"symlink input refused: {path}")
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise OracleError(f"input missing: {path}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise OracleError(f"input is not a regular file: {path}")
    if maximum_size is not None and info.st_size > maximum_size:
        raise OracleError(f"input exceeds size bound: {info.st_size} > {maximum_size}")
    return path.resolve()


def read_pinned(path: Path, expected_sha256: str, maximum_size: int) -> tuple[Path, bytes]:
    resolved = direct_regular_file(path, maximum_size)
    data = resolved.read_bytes()
    actual = sha256_bytes(data)
    if actual != expected_sha256:
        raise OracleError(f"SHA256 mismatch for {path}: {actual} != {expected_sha256}")
    return resolved, data


@contextmanager
def staged_exact_policy(data: bytes) -> Any:
    fd, raw_path = tempfile.mkstemp(prefix="s22plus-fyg8-policy-", suffix=".bin")
    path = Path(raw_path)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, 0o400)
        if sha256_bytes(path.read_bytes()) != sha256_bytes(data):
            raise OracleError("staged policy bytes changed before analysis")
        yield path
    finally:
        path.unlink(missing_ok=True)


def require_substrings(data: bytes, required: Iterable[bytes], label: str) -> None:
    missing = [value.decode("ascii", "backslashreplace") for value in required if value not in data]
    if missing:
        raise OracleError(f"{label} is missing required strings: {missing}")


def normalize_source(data: bytes) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OracleError("source input is not UTF-8") from exc
    return " ".join(text.split())


def check_text_contract(
    dumpstate: bytes,
    bugreportz: bytes,
    dumpstate_rc: bytes,
    file_contexts: bytes,
    sec_log_buf_main: bytes,
    sec_log_buf_last_kmsg: bytes,
) -> dict[str, Any]:
    require_substrings(
        dumpstate,
        (
            b"/proc/last_kmsg\0",
            b"/sys/fs/pstore/console-ramoops\0",
            b"/sys/fs/pstore/console-ramoops-0\0",
            b"LAST KMSG\0",
            b"main_entry.txt\0",
            b"version.txt\0",
            b"/bugreports\0",
            b"-s: write zipped file to control socket (for init)",
        ),
        "dumpstate",
    )
    require_substrings(
        bugreportz,
        (
            b"ctl.start\0",
            b"dumpstate\0",
            b"-s: stream content to standard output",
            b"Failed to write data to stdout",
            b"dumpstate.is_running\0",
        ),
        "bugreportz",
    )

    rc = normalize_source(dumpstate_rc)
    service = (
        "service dumpstate /system/bin/dumpstate -s class main "
        "socket dumpstate stream 0660 shell log disabled oneshot user root"
    )
    if service not in rc:
        raise OracleError("dumpstate init service contract mismatch")

    contexts = normalize_source(file_contexts)
    if "/system/bin/dumpstate u:object_r:dumpstate_exec:s0" not in contexts:
        raise OracleError("dumpstate_exec file-context mapping missing")

    main = normalize_source(sec_log_buf_main)
    ordered = (
        "DEVICE_BUILDER(__log_buf_prepare_buffer, NULL)",
        "DEVICE_BUILDER(__last_kmsg_alloc_buffer, __last_kmsg_free_buffer)",
        "DEVICE_BUILDER(__last_kmsg_pull_last_log, NULL)",
        "DEVICE_BUILDER(__last_kmsg_procfs_create, __last_kmsg_procfs_remove)",
        "DEVICE_BUILDER(__log_buf_pull_early_buffer, NULL)",
        "DEVICE_BUILDER(__log_buf_logger_init, __log_buf_logger_exit)",
        "DEVICE_BUILDER(__ap_klog_proc_init, __ap_klog_proc_exit)",
    )
    positions = [main.find(item) for item in ordered]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise OracleError("sec_log_buf probe order contract mismatch")

    last = normalize_source(sec_log_buf_last_kmsg)
    required_source = (
        "last_kmsg->size = __log_buf_copy_to_buffer(buf);",
        "count = min(len, (size_t)(last_kmsg->size - pos));",
        "copy_to_user(buf, last_kmsg->buf + pos, count)",
        "proc_create_data(LAST_LOG_BUF_NODE, 0444, NULL, &last_kmsg_buf_pops, last_kmsg)",
    )
    missing = [item for item in required_source if item not in last]
    if missing:
        raise OracleError(f"last_kmsg immutable-snapshot contract mismatch: {missing}")

    return {
        "dumpstate_exact_strings": True,
        "bugreportz_exact_strings": True,
        "init_root_stream_service": True,
        "dumpstate_exec_file_context": True,
        "snapshot_before_current_logger": True,
        "snapshot_proc_mode_octal": "0444",
        "snapshot_read_from_private_buffer": True,
    }


def load_setools(extra_path: Path | None) -> Any:
    if extra_path is not None:
        resolved = extra_path.resolve()
        if not resolved.is_dir():
            raise OracleError(f"setools Python path is not a directory: {extra_path}")
        sys.path.insert(0, str(resolved))
    try:
        return importlib.import_module("setools")
    except ImportError as exc:
        raise OracleError("setools Python module is unavailable") from exc


def rule_strings(query: Any) -> list[str]:
    return sorted(str(rule) for rule in query.results())


def one_rule(setools: Any, policy: Any, **kwargs: Any) -> list[str]:
    rules = rule_strings(setools.TERuleQuery(policy, **kwargs))
    if len(rules) != 1:
        raise OracleError(f"expected exactly one SELinux rule for {kwargs}, got {rules}")
    return rules


def check_policy_contract(setools: Any, policy_path: Path) -> dict[str, Any]:
    policy = setools.SELinuxPolicy(str(policy_path))
    shell_read = rule_strings(
        setools.TERuleQuery(
            policy,
            ruletype={"allow"},
            source="shell",
            target="proc_last_kmsg",
            tclass={"file"},
            perms={"read"},
        )
    )
    if shell_read:
        raise OracleError(f"shell unexpectedly reads proc_last_kmsg: {shell_read}")

    readers = rule_strings(
        setools.TERuleQuery(
            policy,
            ruletype={"allow"},
            target="proc_last_kmsg",
            tclass={"file"},
            perms={"read"},
        )
    )
    sources = {re.match(r"allow ([^ ]+) ", rule).group(1) for rule in readers}
    expected_sources = {"bootchecker", "dumpstate", "incidentd", "system_server", "vendor_init"}
    if sources != expected_sources:
        raise OracleError(f"proc_last_kmsg reader set mismatch: {sorted(sources)}")

    dumpstate_read = one_rule(
        setools,
        policy,
        ruletype={"allow"},
        source="dumpstate",
        target="proc_last_kmsg",
        tclass={"file"},
        perms={"read", "open"},
    )
    shell_ctl = one_rule(
        setools,
        policy,
        ruletype={"allow"},
        source="shell",
        target="ctl_dumpstate_prop",
        tclass={"property_service"},
        perms={"set"},
    )
    shell_socket = one_rule(
        setools,
        policy,
        ruletype={"allow"},
        source="shell",
        target="dumpstate_socket",
        tclass={"sock_file"},
        perms={"write"},
    )
    shell_connect = one_rule(
        setools,
        policy,
        ruletype={"allow"},
        source="shell",
        target="dumpstate",
        tclass={"unix_stream_socket"},
        perms={"connectto"},
    )
    transition = one_rule(
        setools,
        policy,
        ruletype={"type_transition"},
        source="init",
        target="dumpstate_exec",
        tclass={"process"},
    )
    genfs = sorted(
        str(rule)
        for rule in setools.GenfsconQuery(policy, fs="proc", path="/last_kmsg").results()
    )
    if genfs != ["genfscon proc /last_kmsg  u:object_r:proc_last_kmsg:s0"]:
        raise OracleError(f"last_kmsg genfscon mismatch: {genfs}")

    return {
        "setools_version": getattr(setools, "__version__", "unknown"),
        "shell_direct_read_rules": shell_read,
        "authorized_reader_sources": sorted(sources),
        "dumpstate_read_rule": dumpstate_read,
        "shell_ctl_start_rule": shell_ctl,
        "shell_socket_rule": shell_socket,
        "shell_connect_rule": shell_connect,
        "init_transition_rule": transition,
        "last_kmsg_genfscon": genfs,
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    inputs: dict[str, dict[str, Any]] = {}

    def pinned(name: str, path: Path, maximum_size: int) -> tuple[Path, bytes]:
        resolved, data = read_pinned(path, PINS[name], maximum_size)
        inputs[name] = {"path": str(resolved), "size": len(data), "sha256": PINS[name]}
        return resolved, data

    _, policy_bytes = pinned("policy", args.policy, 8 * 1024 * 1024)
    _, version = pinned("vendor_policy_version", args.vendor_policy_version, 64 * 1024)
    _, dumpstate = pinned("dumpstate", args.dumpstate, 8 * 1024 * 1024)
    _, bugreportz = pinned("bugreportz", args.bugreportz, 1024 * 1024)
    _, dumpstate_rc = pinned("dumpstate_rc", args.dumpstate_rc, 1024 * 1024)
    _, file_contexts = pinned("plat_file_contexts", args.file_contexts, 16 * 1024 * 1024)
    _, main = pinned("sec_log_buf_main", args.sec_log_buf_main, 4 * 1024 * 1024)
    _, last = pinned("sec_log_buf_last_kmsg", args.sec_log_buf_last_kmsg, 4 * 1024 * 1024)

    if f"HS={PINS['policy']}".encode("ascii") not in version:
        raise OracleError("vendor policy-version HS pin does not name the exact policy binary")
    text_contract = check_text_contract(
        dumpstate, bugreportz, dumpstate_rc, file_contexts, main, last
    )
    setools = load_setools(args.setools_python_path)
    with staged_exact_policy(policy_bytes) as staged_policy:
        policy_contract = check_policy_contract(setools, staged_policy)
    policy_contract["parsed_from_staged_pinned_bytes"] = True

    return {
        "schema": SCHEMA,
        "verdict": "PASS_R4W1A_PRIMARY_ORACLE_SELECTED_HOST_ONLY",
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "inputs": inputs,
        "policy_contract": policy_contract,
        "text_and_source_contract": text_contract,
        "decision": {
            "direct_nonroot_shell_last_kmsg": "DENIED_BY_EXACT_FYG8_SELINUX",
            "selected_primary_oracle": "BUGREPORTZ_STREAM_DUMPSTATE_LAST_KMSG",
            "candidate_snapshot_is_immutable_after_module_probe": True,
            "candidate_snapshot_overwrite_risk": False,
            "requires_both_pstore_console_paths_absent": True,
            "exact_stream_parser_implemented": True,
            "exact_fyg8_live_zip_shape_verified": False,
            "userdata_write_side_effect": True,
            "future_policy_must_authorize_inventory_and_exact_cleanup": True,
            "a1_implementation_ready": True,
            "a1_live_ready": False,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "artifact_build": False,
            "flash": False,
            "live_authorized": False,
        },
    }


def checked_zip_name(name: str) -> None:
    if not name or "\\" in name or name.startswith("/"):
        raise OracleError(f"unsafe ZIP entry name: {name!r}")
    path = PurePosixPath(name)
    if any(part in ("", ".", "..") for part in path.parts):
        raise OracleError(f"unsafe ZIP entry name: {name!r}")


def read_zip_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int) -> bytes:
    if info.file_size > limit:
        raise OracleError(f"ZIP member exceeds size bound: {info.filename}")
    try:
        data = archive.read(info)
    except (OSError, RuntimeError, zipfile.BadZipFile, zlib.error) as exc:
        raise OracleError(f"failed CRC-checked read of {info.filename}: {exc}") from exc
    if len(data) != info.file_size:
        raise OracleError(f"ZIP member size mismatch: {info.filename}")
    return data


def count_streamed_member(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo, needles: tuple[bytes, ...]
) -> tuple[int, ...]:
    overlap = max(len(needle) for needle in needles) - 1
    counts = [0] * len(needles)
    tail = b""
    total = 0

    def count_before(data: bytes, needle: bytes, start_limit: int) -> int:
        count = 0
        start = 0
        while True:
            position = data.find(needle, start)
            if position < 0 or position >= start_limit:
                return count
            count += 1
            start = position + len(needle)

    try:
        with archive.open(info) as stream:
            while True:
                chunk = stream.read(SCAN_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                combined = tail + chunk
                cutoff = max(0, len(combined) - overlap)
                for index, needle in enumerate(needles):
                    counts[index] += count_before(combined, needle, cutoff)
                tail = combined[cutoff:]
            for index, needle in enumerate(needles):
                counts[index] += tail.count(needle)
    except (OSError, RuntimeError, zipfile.BadZipFile, zlib.error) as exc:
        raise OracleError(f"failed CRC-checked scan of {info.filename}: {exc}") from exc
    if total != info.file_size:
        raise OracleError(f"ZIP streamed size mismatch: {info.filename}")
    return tuple(counts)


def parse_main_entry_name(data: bytes, names: set[str]) -> str:
    if not data or len(data) > MAX_METADATA_ENTRY_SIZE or b"\0" in data:
        raise OracleError("invalid main_entry.txt payload")
    if data.endswith(b"\n"):
        data = data[:-1]
    if b"\n" in data or b"\r" in data:
        raise OracleError("main_entry.txt is not a single clean line")
    try:
        name = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise OracleError("main_entry.txt is not ASCII") from exc
    checked_zip_name(name)
    if len(PurePosixPath(name).parts) != 1 or not name.endswith(".txt"):
        raise OracleError(f"main entry is not a direct text member: {name!r}")
    if name in {"main_entry.txt", "version.txt"}:
        raise OracleError(f"main entry aliases a metadata member: {name!r}")
    if name not in names:
        raise OracleError(f"declared main entry is missing: {name!r}")
    return name


def extract_last_kmsg_section(main: bytes) -> bytes:
    prefix = b"------ LAST KMSG ("
    if main.count(prefix) != 1:
        raise OracleError("main report must contain exactly one LAST KMSG section")
    start = main.find(prefix)
    header_end = main.find(b"\n", start)
    if header_end < 0 or main[start:header_end] != LAST_KMSG_HEADER:
        raise OracleError("LAST KMSG did not come from exact /proc/last_kmsg fallback")
    body_start = header_end + 1
    next_header = main.find(b"\n------ ", body_start)
    if next_header < 0:
        raise OracleError("LAST KMSG section has no complete following section boundary")
    body = main[body_start:next_header]
    errors = (
        b"*** Error dumping /proc/last_kmsg",
        b"*** /proc/last_kmsg:",
        b"/proc/last_kmsg: skipped on dry run",
    )
    if any(error in body for error in errors):
        raise OracleError("LAST KMSG section contains a dumpstate read error")
    if not body:
        raise OracleError("LAST KMSG section is empty")
    minimum_partial = len(MARKER_FAMILY_PREFIX)
    if any(
        body.endswith(EXPECTED_MARKER[:length])
        for length in range(minimum_partial, len(EXPECTED_MARKER))
    ) or any(
        body.startswith(EXPECTED_MARKER[-length:])
        for length in range(minimum_partial, len(EXPECTED_MARKER))
    ):
        raise OracleError("LAST KMSG section has a partial R4W1 marker at a boundary")
    return body


def parse_bugreport(path: Path, expect_marker: str) -> dict[str, Any]:
    resolved = direct_regular_file(path, MAX_ARCHIVE_SIZE)
    with resolved.open("rb") as raw_archive:
        initial_stat = os.fstat(raw_archive.fileno())
        archive_sha256 = sha256_stream(raw_archive)
        raw_archive.seek(0)
        try:
            archive = zipfile.ZipFile(raw_archive)
        except (OSError, zipfile.BadZipFile) as exc:
            raise OracleError(f"invalid bugreport ZIP: {exc}") from exc
        with archive:
            infos = archive.infolist()
            if not infos or len(infos) > MAX_ARCHIVE_ENTRIES:
                raise OracleError(f"invalid ZIP entry count: {len(infos)}")
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise OracleError("duplicate ZIP entry names refused")
            for name in names:
                checked_zip_name(name)
            total_uncompressed = sum(info.file_size for info in infos)
            if total_uncompressed > MAX_TOTAL_UNCOMPRESSED:
                raise OracleError("ZIP total uncompressed size exceeds bound")
            by_name = {info.filename: info for info in infos}
            if "main_entry.txt" not in by_name or "version.txt" not in by_name:
                raise OracleError("bugreport metadata entries are incomplete")
            main_name = parse_main_entry_name(
                read_zip_member(archive, by_name["main_entry.txt"], MAX_METADATA_ENTRY_SIZE),
                set(names),
            )
            version_data = read_zip_member(
                archive, by_name["version.txt"], MAX_METADATA_ENTRY_SIZE
            )
            if not version_data or b"\0" in version_data:
                raise OracleError("invalid version.txt payload")
            try:
                version = version_data.decode("ascii").strip()
            except UnicodeDecodeError as exc:
                raise OracleError("version.txt is not ASCII") from exc
            if not version:
                raise OracleError("empty bugreport version")
            main = read_zip_member(archive, by_name[main_name], MAX_MAIN_ENTRY_SIZE)
            section = extract_last_kmsg_section(main)

            archive_family_count = 0
            archive_exact_count = 0
            for info in infos:
                if info.filename in {"main_entry.txt", "version.txt", main_name}:
                    data = {
                        "main_entry.txt": main_name.encode("ascii"),
                        "version.txt": version_data,
                        main_name: main,
                    }[info.filename]
                    family_count = data.count(MARKER_FAMILY_PREFIX)
                    exact_count = data.count(EXPECTED_MARKER)
                else:
                    family_count, exact_count = count_streamed_member(
                        archive, info, (MARKER_FAMILY_PREFIX, EXPECTED_MARKER)
                    )
                archive_family_count += family_count
                archive_exact_count += exact_count
        raw_archive.seek(0)
        if sha256_stream(raw_archive) != archive_sha256:
            raise OracleError("bugreport ZIP changed while it was being parsed")
        final_stat = os.fstat(raw_archive.fileno())
        if final_stat.st_size != initial_stat.st_size:
            raise OracleError("bugreport ZIP size changed while it was being parsed")

    section_family_count = section.count(MARKER_FAMILY_PREFIX)
    section_exact_count = section.count(EXPECTED_MARKER)
    if expect_marker == "exact":
        if (
            archive_family_count != 1
            or archive_exact_count != 1
            or section_family_count != 1
            or section_exact_count != 1
        ):
            raise OracleError(
                "exact R4W1 marker cardinality mismatch: "
                f"archive={archive_family_count}/{archive_exact_count}, "
                f"section={section_family_count}/{section_exact_count}"
            )
        marker_verdict = "EXACT_MARKER_ONCE_IN_LAST_KMSG"
    elif expect_marker == "absent":
        if archive_family_count or archive_exact_count or section_family_count or section_exact_count:
            raise OracleError("R4W1 marker family unexpectedly present in baseline bugreport")
        marker_verdict = "MARKER_FAMILY_ABSENT"
    else:
        raise OracleError(f"unsupported marker expectation: {expect_marker}")

    return {
        "schema": SCHEMA,
        "verdict": "PASS_R4W1A_BUGREPORT_ORACLE_PARSED_HOST_ONLY",
        "input": {
            "path": str(resolved),
            "size": initial_stat.st_size,
            "sha256": archive_sha256,
            "same_fd_pre_post_sha256": True,
        },
        "zip": {
            "entry_count": len(infos),
            "total_uncompressed_size": total_uncompressed,
            "all_entries_crc_checked": True,
            "main_entry": main_name,
            "main_entry_size": len(main),
            "version": version,
        },
        "last_kmsg": {
            "header": LAST_KMSG_HEADER.decode("ascii"),
            "source": "/proc/last_kmsg",
            "section_size": len(section),
            "complete_following_boundary": True,
            "read_error": False,
        },
        "marker": {
            "expectation": expect_marker,
            "classification": marker_verdict,
            "archive_family_count": archive_family_count,
            "archive_exact_count": archive_exact_count,
            "section_family_count": section_family_count,
            "section_exact_count": section_exact_count,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "flash": False,
            "live_authorized": False,
        },
    }


def write_new(path: Path, payload: str) -> None:
    if path.is_symlink():
        raise OracleError(f"symlink output refused: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="ascii") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def add_common_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--out", type=Path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument(
        "--policy", type=Path, default=ORACLE_ROOT / "policy/odm/precompiled_sepolicy"
    )
    audit_parser.add_argument(
        "--vendor-policy-version",
        type=Path,
        default=ORACLE_ROOT / "policy/vendor/vendor_sepolicy_version",
    )
    audit_parser.add_argument(
        "--dumpstate", type=Path, default=ORACLE_ROOT / "binaries/system/dumpstate"
    )
    audit_parser.add_argument(
        "--bugreportz", type=Path, default=ORACLE_ROOT / "binaries/system/bugreportz"
    )
    audit_parser.add_argument(
        "--dumpstate-rc", type=Path, default=ORACLE_ROOT / "init/dumpstate.rc"
    )
    audit_parser.add_argument(
        "--file-contexts",
        type=Path,
        default=ORACLE_ROOT / "policy/system/plat_file_contexts",
    )
    audit_parser.add_argument(
        "--sec-log-buf-main",
        type=Path,
        default=KERNEL_ROOT / "drivers/samsung/debug/log_buf/sec_log_buf_main.c",
    )
    audit_parser.add_argument(
        "--sec-log-buf-last-kmsg",
        type=Path,
        default=KERNEL_ROOT / "drivers/samsung/debug/log_buf/sec_log_buf_last_kmsg.c",
    )
    audit_parser.add_argument(
        "--setools-python-path", type=Path, default=DEFAULT_SETOOLS_PATH
    )
    add_common_output(audit_parser)

    parse_parser = subparsers.add_parser("parse")
    parse_parser.add_argument("bugreport_zip", type=Path)
    parse_parser.add_argument("--expect-marker", choices=("exact", "absent"), required=True)
    add_common_output(parse_parser)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "audit":
            result = audit(args)
        else:
            result = parse_bugreport(args.bugreport_zip, args.expect_marker)
        encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.out is not None:
            write_new(args.out, encoded)
        print(encoded, end="")
        return 0
    except (OracleError, OSError, zipfile.BadZipFile, zlib.error) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
