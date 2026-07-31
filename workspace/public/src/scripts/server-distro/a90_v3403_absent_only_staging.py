#!/usr/bin/env python3
"""Absent-only SD rootfs staging adapter for A90 V3403-V3406 F1 transactions.

The default mode is host-only inspection.  The write-capable mode is usable
only with a final prepared manifest and explicit exact manifest/adapter
bindings.  It stages into an exclusive directory on the ext4 SD filesystem,
then publishes with ``link(2)`` through BusyBox ``ln``.  The final path is
never passed to a command that can overwrite it.

This adapter does not flash, reboot, mount the rootfs, invoke switch_root, or
touch userdata.  A successful staging result is only an input to a separately
approved F1 candidate/rollback transaction.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import ipaddress
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_d1_chroot_mvp as d1  # noqa: E402


ADAPTER_SCHEMA = "a90_v3403_absent_only_staging_adapter_v1"
FINAL_MANIFEST_SCHEMA = "a90_native_init_f1_prepared_v2"
PHASE2_DISPLAY_MANIFEST_SCHEMA = "a90_native_init_f1_prepared_v3"
FINAL_MANIFEST_STATUS = "ready-for-f1-approval"
TARGET_PROFILE = "galaxy-a90-5g-native-init"
EXPECTED_BASELINE_VERSION = "0.9.285"
EXPECTED_BASELINE_BUILD = "v2321-usb-clean-identity-rodata"
REMOTE_ROOT = PurePosixPath("/mnt/sdext/a90/runtime")
REMOTE_MOUNT = PurePosixPath("/mnt/sdext")
REMOTE_WORK = REMOTE_ROOT / "d3-handoff-work.img"
REMOTE_FINAL_PREFIX_BY_CYCLE = {
    "v3403": "debian-bookworm-arm64-d3-sysvinit-v3403-keyed-",
    "v3404": "debian-bookworm-arm64-d3-sysvinit-v3404-keyed-",
    "v3405": "debian-bookworm-arm64-d3-sysvinit-v3405-keyed-",
    "v3406": "debian-bookworm-arm64-phase2-display-v3406-keyed-",
}
STAGE_PREFIX = ".a90-stage-"
STAGE_PAYLOAD_NAME = "payload.img"
REQUIRED_FS_TYPE = "ext4"
PRIVATE_ROOT = REPO_ROOT / "workspace" / "private"
PRIVATE_RUN_BASE = PRIVATE_ROOT / "runs" / "server-distro"
PUBLIC_ROOT = REPO_ROOT / "workspace" / "public"
REQUIRED_SUPPORT_FILES = (
    SCRIPT_DIR / "run_d1_chroot_mvp.py",
    REVAL_DIR / "_workspace_bootstrap.py",
    REVAL_DIR / "a90_bridge.py",
    REVAL_DIR / "a90_serial_lock.py",
    REVAL_DIR / "a90ctl.py",
    REVAL_DIR / "serial_tcp_bridge.py",
    SCRIPT_DIR / "a90_phase2d_keyed_rootfs.py",
    SCRIPT_DIR / "a90_phase2d_display_observer.py",
    REPO_ROOT / "workspace" / "public" / "src" / "harness" / "a90harness" / "evidence.py",
)
PHASE2_KEYER_PATH = SCRIPT_DIR / "a90_phase2d_keyed_rootfs.py"
PHASE2_CONNECTED_PREFLIGHT_PATH = (
    SCRIPT_DIR / "a90_phase2d_connected_preflight.py"
)
PHASE2_CLEAN_IMAGE = (
    PRIVATE_ROOT
    / "outputs"
    / "a90-phase2-display-v1-ab-06"
    / "A"
    / "phase2-display-v1.img"
)
PHASE2_CLEAN_RECEIPT = (
    PRIVATE_ROOT
    / "outputs"
    / "a90-phase2-display-v1-ab-06"
    / "ab-receipt.json"
)
PHASE2_CLEAN_IMAGE_SHA256 = (
    "cf2cf17d5c706123f85b21d4f2479fc348329cdc09e48fe6406874328e3977c8"
)
PHASE2_CLEAN_RECEIPT_SHA256 = (
    "34b0c83ae612762287ee3ad1c7217c0031a259cb8fa745a55a1cc40964f279d2"
)
PHASE2_IMAGE_BYTES = 2 * 1024 * 1024 * 1024
PHASE2_FILESYSTEM_LABEL = "PHASE2DISPLAYV1"
PHASE2_AUTHORIZED_KEYS = "/root/.ssh/authorized_keys"
PHASE2_ABSENT_RUNTIME_PATHS = (
    "/etc/dropbear/dropbear_ed25519_host_key",
    "/run/a90-native-display-release",
    "/run/a90-display/ready",
    "/run/a90-display/failure",
)
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_RE = re.compile(
    r"^a90-(?P<cycle>v3403|v3404|v3405|v3406)-"
    r"(?P<kind>debian|debian-display)-f1-"
    r"(?P<suffix>[0-9]{8}-[0-9]{2})$"
)
PSTORE_ZERO_RE = re.compile(r"^pstore=[^\r\n]*\bentries=0\b", re.MULTILINE)
D0_RESULT_SCHEMA = "a90-v3403-connected-d0-v1"
D0_RESULT_OUTCOME = (
    "PASS_A90_V3403_CONNECTED_READ_ONLY_AWAITING_STAGING_CONTRACT_AND_F1_MANIFEST"
)
PATH_PREFLIGHT_SCHEMA = "a90_v3403_d3_path_preflight_v1"
APPROVAL_PREPARED_SCHEMA = "a90_v3403_f1_approval_prepared_v1"
APPROVAL_PREFIX = "A90-F1-V2-APPROVE:"
UNATTENDED_OBSERVATION_MODE = "unattended-single-shot-v1"
ATTENDED_OBSERVATION_MODE = "operator-attended-v1"
ATTENDED_WINDOW_SEC = 900
ATTENDED_PRE_HANDOFF_ATTEMPT_LIMIT = 3
ATTENDED_HANDOFF_ATTEMPT_LIMIT = 1
HOST_NCM_PREFIX = 24
HOST_NCM_DRIVER = "cdc_ncm"
HOST_NCM_VENDOR_ID = "04e8"
HOST_NCM_PRODUCT_ID = "6861"
HOST_IFACE_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
BRIDGE_REALPATH_RE = re.compile(r"^/dev/ttyACM[0-9]+$")
SYS_CLASS_NET = Path("/sys/class/net")
SYS_CLASS_TTY = Path("/sys/class/tty")
STAGE_STEPS = (
    "validate_local",
    "connected_preflight",
    "reserve_stage_dir",
    "transfer_payload",
    "verify_payload",
    "recheck_final_absent",
    "publish_link",
    "verify_link_identity",
    "verify_final",
    "remove_payload_link",
    "remove_stage_dir",
    "complete",
)


class ContractError(RuntimeError):
    """Raised when an immutable staging contract does not validate."""


def _private_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise ContractError("short private JSON write")
        offset += written


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_private_json_exclusive(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{time.time_ns()}"
    )
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        _write_all(descriptor, _private_json_bytes(payload))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, path, follow_symlinks=False)
        _fsync_directory(path.parent)
    except FileExistsError as exc:
        raise ContractError(f"private JSON already exists: {path}") from exc
    finally:
        temporary.unlink(missing_ok=True)


@dataclass(frozen=True)
class BoundFile:
    label: str
    path: Path
    size: int
    sha256: str


@dataclass(frozen=True)
class StageSpec:
    run_id: str
    manifest_path: Path
    manifest_sha256: str
    local_image: Path
    local_size: int
    local_sha256: str
    remote_final: str
    remote_work: str
    remote_stage_dir: str
    remote_payload: str
    bridge_device: str
    bridge_realpath: str
    observer_device: str
    adapter_size: int
    adapter_sha256: str
    tcpctl_host: Path
    tcpctl_host_size: int
    tcpctl_host_sha256: str
    bound_files: tuple[BoundFile, ...]


@dataclass
class StageModel:
    history: list[str] = field(default_factory=list)
    stage_dir_exists: bool = False
    payload_exists: bool = False
    payload_verified: bool = False
    final_exists: bool = False
    final_is_foreign: bool = False
    final_verified: bool = False
    completed: bool = False
    candidate_allowed: bool = False
    error: str | None = None


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for block in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_regular_file(path: Path, *, expected_size: int, expected_sha256: str) -> None:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise ContractError(f"not a non-symlink regular file: {path}")
    if info.st_mode & 0o022:
        raise ContractError(f"group/world-writable input refused: {path}")
    if info.st_size != expected_size:
        raise ContractError(
            f"size mismatch for {path}: actual={info.st_size} expected={expected_size}"
        )
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise ContractError(
            f"sha256 mismatch for {path}: actual={actual} expected={expected_sha256}"
        )


def validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise ContractError(f"{label} must be lowercase sha256")
    return value


def exact_run_id_parts(run_id: str) -> tuple[str, str]:
    match = RUN_ID_RE.fullmatch(run_id)
    if match is None:
        raise ContractError(
            "run_id must be an exact supported A90 V3403-V3406 form"
        )
    cycle = match.group("cycle")
    kind = match.group("kind")
    if (cycle == "v3406") != (kind == "debian-display"):
        raise ContractError("run_id cycle and Debian profile kind do not match")
    return cycle, match.group("suffix")


def expected_manifest_schema(run_id: str) -> str:
    cycle, _ = exact_run_id_parts(run_id)
    if cycle == "v3406":
        return PHASE2_DISPLAY_MANIFEST_SCHEMA
    return FINAL_MANIFEST_SCHEMA


def derive_remote_final(run_id: str) -> PurePosixPath:
    cycle, suffix = exact_run_id_parts(run_id)
    prefix = REMOTE_FINAL_PREFIX_BY_CYCLE[cycle]
    return REMOTE_ROOT / f"{prefix}{suffix}.img"


def validate_remote_final(value: Any, run_id: str) -> str:
    if not isinstance(value, str):
        raise ContractError("remote final path must be a string")
    path = PurePosixPath(value)
    expected = derive_remote_final(run_id)
    if (
        value != str(expected)
        or path != expected
        or path.parent != REMOTE_ROOT
        or path == REMOTE_WORK
    ):
        raise ContractError(
            f"remote final path is not exact for run_id {run_id}: {value}"
        )
    return str(path)


def validate_observer_device(value: Any) -> str:
    if not isinstance(value, str):
        raise ContractError("observer device address must be a string")
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as exc:
        raise ContractError("observer device address must be canonical IPv4") from exc
    if str(address) != value or address.is_unspecified or address.is_multicast:
        raise ContractError("observer device address must be canonical unicast IPv4")
    network = ipaddress.IPv4Network(f"{address}/{HOST_NCM_PREFIX}", strict=False)
    if address in (network.network_address, network.broadcast_address):
        raise ContractError("observer device address is not a usable host address")
    return value


def derive_stage_dir(run_id: str) -> PurePosixPath:
    exact_run_id_parts(run_id)
    return REMOTE_ROOT / f"{STAGE_PREFIX}{run_id}"


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def _bound_file(
    value: Any,
    label: str,
    *,
    path_key: str = "path",
    size_key: str = "size",
    sha_key: str = "sha256",
) -> BoundFile:
    item = _dict(value, label)
    path_value = item.get(path_key)
    size_value = item.get(size_key)
    sha_value = item.get(sha_key)
    if not isinstance(path_value, str):
        raise ContractError(f"{label}.{path_key} is missing")
    if not isinstance(size_value, int) or size_value <= 0:
        raise ContractError(f"{label}.{size_key} must be positive")
    lexical_path = Path(path_value)
    if lexical_path.is_symlink():
        raise ContractError(f"{label}.{path_key} must not be a symbolic link")
    return BoundFile(
        label=label,
        path=lexical_path.resolve(strict=True),
        size=size_value,
        sha256=validate_sha256(sha_value, f"{label}.{sha_key}"),
    )


def load_bound_json(bound: BoundFile) -> dict[str, Any]:
    require_regular_file(
        bound.path,
        expected_size=bound.size,
        expected_sha256=bound.sha256,
    )
    try:
        value = json.loads(bound.path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{bound.label} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{bound.label} root must be an object")
    return value


def _debugfs_stat(image: Path, target: str) -> dict[str, int] | None:
    result = subprocess.run(
        ["debugfs", "-R", f"stat {target}", str(image)],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60.0,
        check=False,
    )
    text = (result.stdout + result.stderr).decode(
        "utf-8",
        errors="replace",
    )
    if "Inode:" not in text:
        return None
    mode = re.search(r"\bMode:\s+0([0-7]{3,4})\b", text)
    owner = re.search(r"\bUser:\s+(\d+)\s+Group:\s+(\d+)\b", text)
    size = re.search(r"\bSize:\s+(\d+)\b", text)
    if mode is None or owner is None or size is None:
        raise ContractError(f"cannot parse debugfs stat for {target}")
    return {
        "mode": int(mode.group(1), 8),
        "uid": int(owner.group(1)),
        "gid": int(owner.group(2)),
        "size": int(size.group(1)),
    }


def _debugfs_cat(image: Path, target: str) -> bytes:
    result = subprocess.run(
        ["debugfs", "-R", f"cat {target}", str(image)],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60.0,
        check=False,
    )
    if b"File not found" in result.stdout + result.stderr:
        raise ContractError(f"ext4 path is absent: {target}")
    return result.stdout


def _ext4_label(image: Path) -> str:
    with image.open("rb") as stream:
        stream.seek(1024 + 0x38)
        if stream.read(2) != b"\x53\xef":
            raise ContractError("keyed Phase 2 image is not ext4")
        stream.seek(1024 + 0x78)
        raw = stream.read(16)
    try:
        return raw.split(b"\0", 1)[0].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ContractError("keyed Phase 2 label is not ASCII") from exc


def validate_phase2_key_material_pair(
    private_key: Path,
    public_key: Path,
) -> None:
    private_info = private_key.lstat()
    public_info = public_key.lstat()
    if (
        private_key.is_symlink()
        or not stat.S_ISREG(private_info.st_mode)
        or stat.S_IMODE(private_info.st_mode) != 0o600
        or public_key.is_symlink()
        or not stat.S_ISREG(public_info.st_mode)
        or public_info.st_mode & 0o022
    ):
        raise ContractError("Phase 2 observer key modes are not exact")
    result = subprocess.run(
        ["ssh-keygen", "-y", "-f", str(private_key)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=60.0,
        check=False,
        env={**os.environ, "LC_ALL": "C", "LANG": "C"},
    )
    public_fields = public_key.read_text(encoding="utf-8").strip().split()
    derived_fields = result.stdout.strip().split()
    if (
        result.returncode != 0
        or len(public_fields) < 2
        or len(derived_fields) != 2
        or public_fields[:2] != derived_fields
        or public_fields[0] != "ssh-ed25519"
    ):
        raise ContractError("Phase 2 observer private/public key pair mismatch")


def validate_phase2_keyed_materialization(
    *,
    run_id: str,
    run_root: Path,
    keyed_value: dict[str, Any],
    local_image: Path,
    local_size: int,
    local_sha256: str,
    observer: dict[str, Any],
) -> BoundFile:
    materialization = _bound_file(
        keyed_value.get("materialization"),
        "debian_rootfs.keyed_source.materialization",
    )
    require_below(
        materialization.path,
        PRIVATE_ROOT,
        materialization.label,
    )
    if materialization.path.parent != run_root:
        raise ContractError(
            "Phase 2 materialization receipt must be inside the run directory"
        )
    summary = load_bound_json(materialization)
    source = _dict(summary.get("source"), "keyed summary source")
    materializer = _dict(
        summary.get("materializer"),
        "keyed summary materializer",
    )
    keyed = _dict(summary.get("keyed_image"), "keyed summary image")
    authorized = _dict(
        keyed.get("authorized_keys"),
        "keyed summary authorized_keys",
    )
    summary_observer = _dict(
        summary.get("observer"),
        "keyed summary observer",
    )
    expected_materializer = PHASE2_KEYER_PATH.resolve(strict=True)
    clean_image = PHASE2_CLEAN_IMAGE.resolve(strict=True)
    clean_receipt = PHASE2_CLEAN_RECEIPT.resolve(strict=True)
    local_info = local_image.lstat()
    clean_info = clean_image.lstat()
    private_key_input = Path(observer.get("private_key_path", ""))
    if private_key_input.is_symlink():
        raise ContractError("Phase 2 observer private key must not be a symbolic link")
    private_key = private_key_input.resolve(strict=True)
    public_key = private_key.with_suffix(private_key.suffix + ".pub")
    if (
        summary.get("schema") != "a90-phase2d-keyed-rootfs-v1"
        or summary.get("decision") != "A90_PHASE2D_KEYED_ROOTFS_HOST_PASS"
        or summary.get("run_id") != run_id
        or materializer.get("path") != str(expected_materializer)
        or materializer.get("size") != expected_materializer.stat().st_size
        or materializer.get("sha256") != sha256_file(expected_materializer)
        or source.get("path") != str(clean_image)
        or source.get("size") != PHASE2_IMAGE_BYTES
        or source.get("sha256") != PHASE2_CLEAN_IMAGE_SHA256
        or source.get("inode") != clean_info.st_ino
        or source.get("device") != clean_info.st_dev
        or source.get("receipt_path") != str(clean_receipt)
        or source.get("receipt_sha256") != PHASE2_CLEAN_RECEIPT_SHA256
        or source.get("unchanged") is not True
        or keyed.get("path") != str(local_image)
        or keyed.get("size") != PHASE2_IMAGE_BYTES
        or keyed.get("size") != local_size
        or keyed.get("sha256") != local_sha256
        or keyed.get("inode") != local_info.st_ino
        or keyed.get("device") != local_info.st_dev
        or keyed.get("new_inode") is not True
        or (local_info.st_dev, local_info.st_ino)
        == (clean_info.st_dev, clean_info.st_ino)
        or keyed.get("filesystem") != "ext4"
        or keyed.get("filesystem_label") != PHASE2_FILESYSTEM_LABEL
        or keyed.get("e2fsck_read_only_rc") != 0
        or keyed.get("runtime_paths_absent")
        != list(PHASE2_ABSENT_RUNTIME_PATHS)
        or authorized.get("target") != PHASE2_AUTHORIZED_KEYS
        or authorized.get("mode") != 0o600
        or authorized.get("uid") != 0
        or authorized.get("gid") != 0
        or authorized.get("size") != public_key.stat().st_size
        or authorized.get("root_owned_mode_0600") is not True
        or authorized.get("sha256")
        != observer.get("public_key_sha256")
        or summary_observer.get("private_key_path") != str(private_key)
        or summary_observer.get("private_key_sha256")
        != sha256_file(private_key)
        or summary_observer.get("public_key_path") != str(public_key)
        or summary_observer.get("public_key_sha256")
        != observer.get("public_key_sha256")
        or summary_observer.get("algorithm") != "ssh-ed25519"
        or summary_observer.get("single_run") is not True
        or any(
            summary.get(name) is not False
            for name in (
                "candidate_authority",
                "f1_authorized",
                "live_authority",
                "device_contact",
                "device_write",
                "rootfs_staged",
                "flash",
                "reboot",
            )
        )
    ):
        raise ContractError("Phase 2 keyed-rootfs summary is not exact")
    require_regular_file(
        clean_image,
        expected_size=PHASE2_IMAGE_BYTES,
        expected_sha256=PHASE2_CLEAN_IMAGE_SHA256,
    )
    require_regular_file(
        clean_receipt,
        expected_size=clean_receipt.stat().st_size,
        expected_sha256=PHASE2_CLEAN_RECEIPT_SHA256,
    )
    validate_phase2_key_material_pair(private_key, public_key)
    public_bytes = public_key.read_bytes()
    if (
        public_bytes.count(b"\n") != 1
        or _debugfs_cat(local_image, PHASE2_AUTHORIZED_KEYS)
        != public_bytes
        or _debugfs_stat(local_image, PHASE2_AUTHORIZED_KEYS)
        != {
            "mode": 0o600,
            "uid": 0,
            "gid": 0,
            "size": len(public_bytes),
        }
        or _ext4_label(local_image) != PHASE2_FILESYSTEM_LABEL
        or any(
            _debugfs_stat(local_image, path) is not None
            for path in PHASE2_ABSENT_RUNTIME_PATHS
        )
    ):
        raise ContractError(
            "Phase 2 keyed image content does not match its observer key"
        )
    return materialization


def json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_f1_approval_binding(
    *,
    run_id: str,
    manifest_sha256: str,
    orchestrator_sha256: str,
    staging_adapter_sha256: str,
    flash_runner_sha256: str,
    candidate_boot_sha256: str,
    rollback_boot_sha256: str,
    rootfs_sha256: str,
    connected_d0_sha256: str,
    connected_path_preflight_sha256: str,
    recovery_adb_serial_sha256: str,
    observation_mode: str,
    attended_window_sec: int,
    pre_handoff_attempt_limit: int,
    handoff_attempt_limit: int,
) -> dict[str, Any]:
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise ContractError("approval binding run_id is not exact")
    hashes = {
        "manifest_sha256": manifest_sha256,
        "orchestrator_sha256": orchestrator_sha256,
        "staging_adapter_sha256": staging_adapter_sha256,
        "flash_runner_sha256": flash_runner_sha256,
        "candidate_boot_sha256": candidate_boot_sha256,
        "rollback_boot_sha256": rollback_boot_sha256,
        "rootfs_sha256": rootfs_sha256,
        "connected_d0_sha256": connected_d0_sha256,
        "connected_path_preflight_sha256": connected_path_preflight_sha256,
        "recovery_adb_serial_sha256": recovery_adb_serial_sha256,
    }
    for label, value in hashes.items():
        validate_sha256(value, f"approval binding {label}")
    if observation_mode == ATTENDED_OBSERVATION_MODE:
        expected_policy = (
            ATTENDED_WINDOW_SEC,
            ATTENDED_PRE_HANDOFF_ATTEMPT_LIMIT,
            ATTENDED_HANDOFF_ATTEMPT_LIMIT,
        )
    elif observation_mode == UNATTENDED_OBSERVATION_MODE:
        expected_policy = (0, 1, 1)
    else:
        raise ContractError("approval binding observation mode is not exact")
    policy = (
        attended_window_sec,
        pre_handoff_attempt_limit,
        handoff_attempt_limit,
    )
    if (
        any(type(value) is not int for value in policy)
        or policy != expected_policy
    ):
        raise ContractError("approval binding observation policy is not exact")
    return {
        "schema": "a90_v3403_f1_approval_binding_v1",
        "run_id": run_id,
        **hashes,
        "observation_mode": observation_mode,
        "attended_window_sec": attended_window_sec,
        "pre_handoff_attempt_limit": pre_handoff_attempt_limit,
        "handoff_attempt_limit": handoff_attempt_limit,
        "candidate_attempt_limit": 1,
        "mandatory_rollback_preapproved_after_candidate_start": True,
        "candidate_replay": False,
        "only_partition_payload": "boot",
    }


def validate_parent_approval(
    spec: StageSpec,
    manifest: dict[str, Any],
    approval: str | None,
) -> dict[str, Any]:
    path = (
        PRIVATE_RUN_BASE / spec.run_id / "approval-prepared.json"
    ).resolve()
    require_below(path, PRIVATE_RUN_BASE, "approval-prepared")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink() or info.st_mode & 0o077:
        raise ContractError("approval-prepared is not an exact private regular file")
    value = json.loads(path.read_text(encoding="utf-8"))
    binding = value.get("approval_binding") if isinstance(value, dict) else None
    if not isinstance(binding, dict):
        raise ContractError("approval-prepared binding is missing")
    target = _dict(manifest.get("target"), "target")
    connected_d0 = _dict(target.get("connected_d0_result"), "connected_d0_result")
    connected_paths = _dict(
        target.get("connected_path_preflight"),
        "connected_path_preflight",
    )
    binding_sha256 = json_sha256(binding)
    candidate = _dict(manifest.get("candidate_boot"), "candidate_boot")
    rollback = _dict(manifest.get("rollback_boot"), "rollback_boot")
    orchestrator = _dict(manifest.get("f1_orchestrator"), "f1_orchestrator")
    transport = _dict(manifest.get("transport"), "transport")
    observation = _dict(manifest.get("observation"), "observation")
    expected_binding = canonical_f1_approval_binding(
        run_id=spec.run_id,
        manifest_sha256=spec.manifest_sha256,
        orchestrator_sha256=orchestrator.get("sha256"),
        staging_adapter_sha256=spec.adapter_sha256,
        flash_runner_sha256=transport.get("runner_sha256"),
        candidate_boot_sha256=candidate.get("sha256"),
        rollback_boot_sha256=rollback.get("sha256"),
        rootfs_sha256=spec.local_sha256,
        connected_d0_sha256=connected_d0.get("sha256"),
        connected_path_preflight_sha256=connected_paths.get("sha256"),
        recovery_adb_serial_sha256=target.get("recovery_adb_serial_sha256"),
        observation_mode=observation.get("mode"),
        attended_window_sec=observation.get("attended_window_sec"),
        pre_handoff_attempt_limit=observation.get(
            "pre_handoff_attempt_limit"
        ),
        handoff_attempt_limit=observation.get("handoff_attempt_limit"),
    )
    expected_keys = {
        "schema",
        "created_utc",
        "run_id",
        "manifest_sha256",
        "approval_binding",
        "approval_binding_sha256",
        "approval_token",
        "device_contact",
        "device_write",
        "f1_authorized",
        "live_authorized",
    }
    if (
        set(value) != expected_keys
        or value.get("schema") != APPROVAL_PREPARED_SCHEMA
        or value.get("run_id") != spec.run_id
        or value.get("manifest_sha256") != spec.manifest_sha256
        or value.get("approval_binding_sha256") != binding_sha256
        or value.get("approval_token") != APPROVAL_PREFIX + binding_sha256
        or approval != value.get("approval_token")
        or binding != expected_binding
        or any(
            value.get(name) is not False
            for name in (
                "device_contact",
                "device_write",
                "f1_authorized",
                "live_authorized",
            )
        )
    ):
        raise ContractError("parent approval does not match exact staging closure")
    return value


def validate_connected_d0_evidence(
    value: dict[str, Any],
    *,
    expected_realpath: str,
    candidate: BoundFile,
    rollback: BoundFile,
    flash_runner: BoundFile,
    require_phase2_preflight: bool = False,
) -> None:
    target = _dict(value.get("target"), "connected D0 target")
    health = _dict(value.get("health"), "connected D0 health")
    selftest = _dict(health.get("selftest"), "connected D0 selftest")
    safety = _dict(value.get("safety"), "connected D0 safety")
    artifacts = _dict(value.get("artifacts"), "connected D0 artifacts")
    repository = _dict(value.get("repository"), "connected D0 repository")
    candidate_value = _dict(
        artifacts.get("candidate_boot"),
        "connected D0 candidate_boot",
    )
    rollback_value = _dict(
        artifacts.get("rollback_boot"),
        "connected D0 rollback_boot",
    )
    if value.get("schema") != D0_RESULT_SCHEMA:
        raise ContractError("connected D0 schema mismatch")
    if value.get("outcome") != D0_RESULT_OUTCOME:
        raise ContractError("connected D0 outcome mismatch")
    if (
        target.get("profile") != TARGET_PROFILE
        or target.get("matching_a90_usb_devices") != 1
        or target.get("bridge_selected_realpath") != expected_realpath
    ):
        raise ContractError("connected D0 exact target binding mismatch")
    if (
        health.get("bridge_exact") is not True
        or health.get("bridge_running") is not True
        or health.get("version") != EXPECTED_BASELINE_VERSION
        or health.get("version_build") != EXPECTED_BASELINE_BUILD
        or health.get("pstore_entries") != 0
        or selftest.get("fail") != 0
    ):
        raise ContractError("connected D0 baseline health mismatch")
    for name in (
        "device_write",
        "flash",
        "payload_sent",
        "reboot_requested",
        "rootfs_staged",
        "userdata_touched",
    ):
        if safety.get(name) is not False:
            raise ContractError(f"connected D0 safety.{name} is not false")
    for label, item, bound in (
        ("candidate", candidate_value, candidate),
        ("rollback", rollback_value, rollback),
    ):
        if item.get("size") != bound.size or item.get("sha256") != bound.sha256:
            raise ContractError(f"connected D0 {label} artifact mismatch")
    if repository.get("runner_sha256") != flash_runner.sha256:
        raise ContractError("connected D0 flash runner mismatch")
    if require_phase2_preflight:
        source = PHASE2_CONNECTED_PREFLIGHT_PATH.resolve(strict=True)
        source_info = source.lstat()
        source_sha256 = sha256_file(source)
        if (
            repository.get("connected_preflight") != str(source)
            or repository.get("connected_preflight_size") != source_info.st_size
            or repository.get("connected_preflight_sha256") != source_sha256
        ):
            raise ContractError(
                "connected D0 Phase 2 preflight helper binding mismatch"
            )


def validate_path_preflight_evidence(
    value: dict[str, Any],
    *,
    run_id: str,
    connected_d0: BoundFile,
    remote_final: str,
    remote_work: str,
    remote_stage_dir: str,
) -> None:
    target = _dict(value.get("target_binding"), "path preflight target_binding")
    read = _dict(value.get("read"), "path preflight read")
    paths = _dict(read.get("paths"), "path preflight paths")
    safety = _dict(value.get("safety"), "path preflight safety")
    if value.get("schema") != PATH_PREFLIGHT_SCHEMA:
        raise ContractError("connected path preflight schema mismatch")
    if value.get("run_id") != run_id:
        raise ContractError("connected path preflight run_id mismatch")
    if (
        target.get("connected_d0_result") != str(connected_d0.path)
        or target.get("connected_d0_result_sha256") != connected_d0.sha256
        or target.get("target_profile") != TARGET_PROFILE
        or target.get("exact_a90_bridge") is not True
    ):
        raise ContractError("connected path preflight target binding mismatch")
    if (
        read.get("kind") != "bounded-connected-read-only"
        or read.get("framed_command") != "run"
        or read.get("framed_rc") != 0
        or read.get("framed_status") != "ok"
    ):
        raise ContractError("connected path preflight read result mismatch")
    expected_paths = {
        remote_final: "absent",
        remote_work: "absent",
        remote_stage_dir: "absent",
    }
    if paths != expected_paths:
        raise ContractError("connected path preflight does not prove all exact paths absent")
    for name in (
        "device_write",
        "payload_sent",
        "reboot_requested",
        "flash",
        "userdata_touched",
    ):
        if safety.get(name) is not False:
            raise ContractError(f"connected path preflight safety.{name} is not false")


def require_below(path: Path, root: Path, label: str) -> None:
    try:
        path.relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise ContractError(f"{label} escapes {root}") from exc


def load_manifest(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    resolved = path.resolve(strict=True)
    validate_sha256(expected_sha256, "expected manifest sha256")
    info = resolved.lstat()
    if not stat.S_ISREG(info.st_mode) or resolved.is_symlink():
        raise ContractError("manifest must be a non-symlink regular file")
    if info.st_mode & 0o022:
        raise ContractError("group/world-writable manifest refused")
    actual = sha256_file(resolved)
    if actual != expected_sha256:
        raise ContractError(
            f"manifest sha256 mismatch: actual={actual} expected={expected_sha256}"
        )
    try:
        manifest = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"manifest is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ContractError("manifest root must be an object")
    return manifest, actual


def stage_spec_from_manifest(
    manifest_path: Path,
    expected_manifest_sha256: str,
    *,
    allow_draft: bool,
) -> tuple[StageSpec, dict[str, Any], list[str]]:
    manifest, actual_manifest_sha = load_manifest(
        manifest_path,
        expected_manifest_sha256,
    )
    issues: list[str] = []
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or RUN_ID_RE.fullmatch(run_id) is None:
        raise ContractError("run_id is not an exact supported A90 F1 form")
    cycle, _ = exact_run_id_parts(run_id)
    schema = manifest.get("schema")
    status_value = manifest.get("status")
    required_schema = expected_manifest_schema(run_id)
    if schema != required_schema:
        issues.append(
            f"manifest schema is {schema!r}, live requires {required_schema!r}"
        )
    if status_value != FINAL_MANIFEST_STATUS:
        issues.append(
            f"manifest status is {status_value!r}, live requires {FINAL_MANIFEST_STATUS!r}"
        )
    if not allow_draft and issues:
        raise ContractError("; ".join(issues))
    run_root = (PRIVATE_RUN_BASE / run_id).resolve()
    if manifest_path.resolve().parent != run_root:
        raise ContractError("manifest must be directly inside its exact private run directory")

    target = _dict(manifest.get("target"), "target")
    if target.get("profile") != TARGET_PROFILE:
        raise ContractError("target profile mismatch")
    bridge_device = target.get("bridge_device")
    bridge_realpath = target.get("bridge_selected_realpath")
    if not isinstance(bridge_device, str) or not bridge_device.startswith(
        "/dev/serial/by-id/"
    ):
        issues.append("final manifest lacks an exact /dev/serial/by-id bridge device")
        bridge_device = ""
    if not isinstance(bridge_realpath, str) or not bridge_realpath.startswith(
        "/dev/ttyACM"
    ):
        issues.append("final manifest lacks an exact bridge realpath")
        bridge_realpath = ""

    rootfs = _dict(manifest.get("debian_rootfs"), "debian_rootfs")
    keyed = _dict(rootfs.get("keyed_source"), "debian_rootfs.keyed_source")
    observer = _dict(rootfs.get("observer"), "debian_rootfs.observer")
    observer_device = validate_observer_device(observer.get("device_ip"))
    local_path_value = keyed.get("local_path")
    if not isinstance(local_path_value, str):
        raise ContractError("keyed rootfs local_path is missing")
    local_path_input = Path(local_path_value)
    if local_path_input.is_symlink():
        raise ContractError("keyed rootfs local_path must not be a symbolic link")
    local_path = local_path_input.resolve(strict=True)
    if local_path.parent != run_root:
        raise ContractError("keyed rootfs must be directly inside its exact private run directory")
    local_size = keyed.get("size")
    if not isinstance(local_size, int) or local_size <= 0:
        raise ContractError("keyed rootfs size must be positive")
    local_sha = validate_sha256(keyed.get("sha256"), "keyed rootfs sha256")
    remote_final = validate_remote_final(keyed.get("device_path"), run_id)
    keyed_materialization: BoundFile | None = None
    if cycle == "v3406":
        if local_size != PHASE2_IMAGE_BYTES:
            raise ContractError("V3406 keyed rootfs must be exactly 2 GiB")
        try:
            keyed_materialization = validate_phase2_keyed_materialization(
                run_id=run_id,
                run_root=run_root,
                keyed_value=keyed,
                local_image=local_path,
                local_size=local_size,
                local_sha256=local_sha,
                observer=observer,
            )
        except (ContractError, FileNotFoundError, json.JSONDecodeError) as exc:
            if not allow_draft:
                raise
            issues.append(
                f"Phase 2 keyed materialization is not final: {exc}"
            )
    elif keyed.get("materialization") is not None:
        raise ContractError(
            "legacy rootfs contract must not add Phase 2 materialization"
        )

    work = _dict(rootfs.get("work_copy"), "debian_rootfs.work_copy")
    if work.get("device_path") != str(REMOTE_WORK):
        raise ContractError("fixed D3 work-copy path mismatch")
    if work.get("must_be_absent_before_handoff") is not True:
        raise ContractError("work-copy absence requirement missing")

    staging = _dict(manifest.get("rootfs_staging"), "rootfs_staging")
    adapter = _dict(staging.get("adapter"), "rootfs_staging.adapter")
    adapter_path_value = adapter.get("path")
    adapter_size_value = adapter.get("size")
    adapter_sha_value = adapter.get("sha256")
    if not isinstance(adapter_path_value, str):
        issues.append("staging adapter path is not bound")
    else:
        try:
            adapter_path = Path(adapter_path_value).resolve(strict=True)
        except FileNotFoundError:
            issues.append("staging adapter path is absent")
        else:
            if adapter_path != Path(__file__).resolve():
                issues.append("staging adapter path does not select this source")
    if not isinstance(adapter_size_value, int) or adapter_size_value <= 0:
        issues.append("staging adapter size is not bound")
    if not isinstance(adapter_sha_value, str) or HEX64_RE.fullmatch(adapter_sha_value) is None:
        issues.append("staging adapter sha256 is not bound")
    elif adapter_sha_value != sha256_file(Path(__file__).resolve()):
        issues.append("staging adapter sha256 does not match this source")

    transport = _dict(staging.get("transport"), "rootfs_staging.transport")
    tcpctl_path_value = transport.get("path")
    tcpctl_size_value = transport.get("size")
    tcpctl_sha_value = transport.get("sha256")
    if not isinstance(tcpctl_path_value, str):
        raise ContractError("tcpctl transport path is missing")
    tcpctl_path = Path(tcpctl_path_value).resolve(strict=True)
    if tcpctl_path != (REVAL_DIR / "tcpctl_host.py").resolve(strict=True):
        raise ContractError("tcpctl transport path mismatch")
    if not isinstance(tcpctl_size_value, int) or tcpctl_size_value <= 0:
        raise ContractError("tcpctl transport size must be positive")
    tcpctl_sha = validate_sha256(tcpctl_sha_value, "tcpctl transport sha256")

    support_value = staging.get("support_files")
    if not isinstance(support_value, list):
        raise ContractError("rootfs_staging.support_files must be an array")
    support_files = tuple(
        _bound_file(item, f"rootfs_staging.support_files[{index}]")
        for index, item in enumerate(support_value)
    )
    expected_support_paths = {
        path.resolve(strict=True) for path in REQUIRED_SUPPORT_FILES
    }
    actual_support_paths = {item.path for item in support_files}
    if actual_support_paths != expected_support_paths:
        missing = sorted(str(path) for path in expected_support_paths - actual_support_paths)
        extra = sorted(str(path) for path in actual_support_paths - expected_support_paths)
        raise ContractError(f"support-file closure mismatch missing={missing} extra={extra}")
    if len(actual_support_paths) != len(support_files):
        raise ContractError("support-file closure contains duplicate paths")
    for item in support_files:
        require_below(item.path, PUBLIC_ROOT, item.label)

    candidate = _bound_file(manifest.get("candidate_boot"), "candidate_boot")
    rollback = _bound_file(manifest.get("rollback_boot"), "rollback_boot")
    if _dict(manifest.get("candidate_boot"), "candidate_boot").get("partition") != "boot":
        raise ContractError("candidate partition must be boot")
    if _dict(manifest.get("rollback_boot"), "rollback_boot").get("partition") != "boot":
        raise ContractError("rollback partition must be boot")
    flash_runner = _bound_file(
        manifest.get("transport"),
        "transport",
        path_key="candidate_and_rollback_runner",
        size_key="runner_size",
        sha_key="runner_sha256",
    )
    if flash_runner.path != (REVAL_DIR / "native_init_flash.py").resolve(strict=True):
        raise ContractError("candidate/rollback runner is not native_init_flash.py")
    connected_d0 = _bound_file(
        target.get("connected_d0_result"),
        "target.connected_d0_result",
    )
    connected_paths = _bound_file(
        target.get("connected_path_preflight"),
        "target.connected_path_preflight",
    )
    host_preparation = _bound_file(
        manifest.get("host_preparation"),
        "host_preparation",
    )
    connected_preflight_source: BoundFile | None = None
    if cycle == "v3406":
        source = PHASE2_CONNECTED_PREFLIGHT_PATH.resolve(strict=True)
        source_info = source.lstat()
        connected_preflight_source = BoundFile(
            "phase2_connected_preflight",
            source,
            source_info.st_size,
            sha256_file(source),
        )
    for item in (
        connected_d0,
        connected_paths,
        candidate,
        rollback,
        host_preparation,
    ):
        require_below(item.path, PRIVATE_ROOT, item.label)

    stage_dir = derive_stage_dir(run_id)
    evidence_checks = (
        (
            "connected D0 evidence",
            lambda: validate_connected_d0_evidence(
                load_bound_json(connected_d0),
                expected_realpath=bridge_realpath,
                candidate=candidate,
                rollback=rollback,
                flash_runner=flash_runner,
                require_phase2_preflight=cycle == "v3406",
            ),
        ),
        (
            "connected path preflight evidence",
            lambda: validate_path_preflight_evidence(
                load_bound_json(connected_paths),
                run_id=run_id,
                connected_d0=connected_d0,
                remote_final=remote_final,
                remote_work=str(REMOTE_WORK),
                remote_stage_dir=str(stage_dir),
            ),
        ),
    )
    for label, check in evidence_checks:
        try:
            check()
        except ContractError as exc:
            if not allow_draft:
                raise
            issues.append(f"{label} is not final: {exc}")

    if not allow_draft and issues:
        raise ContractError("; ".join(issues))

    spec = StageSpec(
        run_id=run_id,
        manifest_path=manifest_path.resolve(),
        manifest_sha256=actual_manifest_sha,
        local_image=local_path,
        local_size=local_size,
        local_sha256=local_sha,
        remote_final=remote_final,
        remote_work=str(REMOTE_WORK),
        remote_stage_dir=str(stage_dir),
        remote_payload=str(stage_dir / STAGE_PAYLOAD_NAME),
        bridge_device=bridge_device,
        bridge_realpath=bridge_realpath,
        observer_device=observer_device,
        adapter_size=adapter_size_value if isinstance(adapter_size_value, int) else 0,
        adapter_sha256=adapter_sha_value if isinstance(adapter_sha_value, str) else "",
        tcpctl_host=tcpctl_path,
        tcpctl_host_size=tcpctl_size_value,
        tcpctl_host_sha256=tcpctl_sha,
        bound_files=(
            connected_d0,
            connected_paths,
            candidate,
            rollback,
            flash_runner,
            host_preparation,
            *((keyed_materialization,) if keyed_materialization else ()),
            *(
                (connected_preflight_source,)
                if connected_preflight_source
                else ()
            ),
            *support_files,
        ),
    )
    return spec, manifest, issues


def verify_local_closure(spec: StageSpec) -> None:
    require_regular_file(
        Path(__file__).resolve(),
        expected_size=spec.adapter_size,
        expected_sha256=spec.adapter_sha256,
    )
    require_regular_file(
        spec.local_image,
        expected_size=spec.local_size,
        expected_sha256=spec.local_sha256,
    )
    require_regular_file(
        spec.tcpctl_host,
        expected_size=spec.tcpctl_host_size,
        expected_sha256=spec.tcpctl_host_sha256,
    )
    for item in spec.bound_files:
        require_regular_file(
            item.path,
            expected_size=item.size,
            expected_sha256=item.sha256,
        )


def _shell_vars(spec: StageSpec) -> str:
    pairs = (
        ("ROOT", str(REMOTE_ROOT)),
        ("MOUNT", str(REMOTE_MOUNT)),
        ("FINAL", spec.remote_final),
        ("WORK", spec.remote_work),
        ("STAGE", spec.remote_stage_dir),
        ("PAYLOAD", spec.remote_payload),
        ("EXPECTED_SIZE", str(spec.local_size)),
        ("EXPECTED_SHA", spec.local_sha256),
    )
    return "\n".join(f"{name}={shlex.quote(value)}" for name, value in pairs)


def remote_readonly_preflight_script(spec: StageSpec) -> str:
    return f"""set -eu
{_shell_vars(spec)}
FS=
OPTS=
while read SRC TARGET FSTYPE MOUNTOPTS REST; do
  if [ "$TARGET" = "$MOUNT" ]; then
    FS=$FSTYPE
    OPTS=$MOUNTOPTS
    break
  fi
done < /proc/mounts
[ "$FS" = "{REQUIRED_FS_TYPE}" ]
case ",$OPTS," in
  *,rw,*) ;;
  *) exit 31 ;;
esac
[ -d "$ROOT" ]
[ ! -L "$ROOT" ]
APPLETS=$(/bin/busybox --list)
for APPLET in chmod ln mkdir rm rmdir sha256sum stat sync; do
  echo "$APPLETS" | /bin/busybox grep -qx "$APPLET"
done
for PATH_ITEM in "$FINAL" "$WORK" "$STAGE"; do
  if [ -e "$PATH_ITEM" ] || [ -L "$PATH_ITEM" ]; then
    echo "A90STAGE_PRECHECK present=$PATH_ITEM"
    exit 32
  fi
done
echo "A90STAGE_PRECHECK fs=$FS rw=1 final_absent=1 work_absent=1 stage_absent=1"
""".strip()


def remote_reserve_script(spec: StageSpec) -> str:
    return f"""set -eu
{_shell_vars(spec)}
umask 077
for PATH_ITEM in "$FINAL" "$WORK" "$STAGE"; do
  if [ -e "$PATH_ITEM" ] || [ -L "$PATH_ITEM" ]; then
    echo "A90STAGE_RESERVE refused_present=$PATH_ITEM"
    exit 41
  fi
done
/bin/busybox mkdir "$STAGE"
[ -d "$STAGE" ]
[ ! -L "$STAGE" ]
/bin/busybox chmod 700 "$STAGE"
ROOT_DEV=$(/bin/busybox stat -c %d "$ROOT")
STAGE_DEV=$(/bin/busybox stat -c %d "$STAGE")
[ "$ROOT_DEV" = "$STAGE_DEV" ]
echo "A90STAGE_RESERVE ready=1"
""".strip()


def remote_verify_payload_script(spec: StageSpec) -> str:
    return f"""set -eu
{_shell_vars(spec)}
[ -d "$STAGE" ]
[ ! -L "$STAGE" ]
[ -f "$PAYLOAD" ]
[ ! -L "$PAYLOAD" ]
[ ! -e "$FINAL" ]
[ ! -L "$FINAL" ]
[ ! -e "$WORK" ]
[ ! -L "$WORK" ]
ACTUAL_SIZE=$(/bin/busybox stat -c %s "$PAYLOAD")
[ "$ACTUAL_SIZE" = "$EXPECTED_SIZE" ]
ACTUAL_SHA=$(/bin/busybox sha256sum "$PAYLOAD")
ACTUAL_SHA=${{ACTUAL_SHA%% *}}
[ "$ACTUAL_SHA" = "$EXPECTED_SHA" ]
echo "A90STAGE_PAYLOAD verified=1 size=$ACTUAL_SIZE sha256=$ACTUAL_SHA"
""".strip()


def remote_publish_script(spec: StageSpec) -> str:
    return f"""set -eu
{_shell_vars(spec)}
[ -d "$STAGE" ]
[ ! -L "$STAGE" ]
[ -f "$PAYLOAD" ]
[ ! -L "$PAYLOAD" ]
[ ! -e "$FINAL" ]
[ ! -L "$FINAL" ]
[ ! -e "$WORK" ]
[ ! -L "$WORK" ]
ACTUAL_SIZE=$(/bin/busybox stat -c %s "$PAYLOAD")
[ "$ACTUAL_SIZE" = "$EXPECTED_SIZE" ]
ACTUAL_SHA=$(/bin/busybox sha256sum "$PAYLOAD")
ACTUAL_SHA=${{ACTUAL_SHA%% *}}
[ "$ACTUAL_SHA" = "$EXPECTED_SHA" ]
PAYLOAD_ID=$(/bin/busybox stat -c %d:%i "$PAYLOAD")
ROOT_DEV=$(/bin/busybox stat -c %d "$ROOT")
PAYLOAD_DEV=$(/bin/busybox stat -c %d "$PAYLOAD")
[ "$ROOT_DEV" = "$PAYLOAD_DEV" ]
/bin/busybox ln "$PAYLOAD" "$FINAL"
[ -f "$FINAL" ]
[ ! -L "$FINAL" ]
FINAL_ID=$(/bin/busybox stat -c %d:%i "$FINAL")
[ "$PAYLOAD_ID" = "$FINAL_ID" ]
/bin/busybox chmod 600 "$FINAL"
/bin/busybox sync
FINAL_SIZE=$(/bin/busybox stat -c %s "$FINAL")
[ "$FINAL_SIZE" = "$EXPECTED_SIZE" ]
FINAL_SHA=$(/bin/busybox sha256sum "$FINAL")
FINAL_SHA=${{FINAL_SHA%% *}}
[ "$FINAL_SHA" = "$EXPECTED_SHA" ]
/bin/busybox rm "$PAYLOAD"
/bin/busybox rmdir "$STAGE"
/bin/busybox sync
FINAL_SIZE=$(/bin/busybox stat -c %s "$FINAL")
FINAL_SHA=$(/bin/busybox sha256sum "$FINAL")
FINAL_SHA=${{FINAL_SHA%% *}}
[ "$FINAL_SIZE" = "$EXPECTED_SIZE" ]
[ "$FINAL_SHA" = "$EXPECTED_SHA" ]
echo "A90STAGE_PUBLISH complete=1 no_clobber=hardlink size=$FINAL_SIZE sha256=$FINAL_SHA"
""".strip()


def remote_cleanup_script(spec: StageSpec) -> str:
    return f"""set -eu
{_shell_vars(spec)}
if [ -e "$FINAL" ] || [ -L "$FINAL" ]; then
  echo "A90STAGE_CLEANUP final_preserved=1 stage_untouched=1"
  exit 0
fi
if [ -d "$STAGE" ] && [ ! -L "$STAGE" ]; then
  if [ -f "$PAYLOAD" ] && [ ! -L "$PAYLOAD" ]; then
    /bin/busybox rm "$PAYLOAD"
  fi
  if /bin/busybox rmdir "$STAGE" 2>/dev/null; then
    echo "A90STAGE_CLEANUP owned_stage_removed=1"
  else
    echo "A90STAGE_CLEANUP owned_stage_retained=1 reason=unexpected-entry"
  fi
else
  echo "A90STAGE_CLEANUP owned_stage_absent=1"
fi
""".strip()


def transfer_command(spec: StageSpec, args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(spec.tcpctl_host),
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--device-ip",
        args.device_ip,
        "--bridge-timeout",
        str(args.bridge_timeout),
        "--connect-timeout",
        str(args.connect_timeout),
        "--tcp-timeout",
        str(args.tcp_timeout),
        "--toybox",
        args.toybox,
        "--device-binary",
        spec.remote_payload,
        "install",
        "--local-binary",
        str(spec.local_image),
        "--transfer-timeout",
        str(args.transfer_timeout),
        "--transfer-delay",
        str(args.transfer_delay),
        "--install-control-channel",
        "bridge",
    ]


def simulate_stage(
    *,
    fail_step: str | None = None,
    preexisting_final: bool = False,
    preexisting_work: bool = False,
    preexisting_stage: bool = False,
    final_race_before_publish: bool = False,
) -> StageModel:
    if fail_step is not None and fail_step not in STAGE_STEPS:
        raise ValueError(f"unknown fail step: {fail_step}")
    state = StageModel(
        stage_dir_exists=preexisting_stage,
        final_exists=preexisting_final,
        final_is_foreign=preexisting_final,
    )

    def enter(step: str) -> bool:
        state.history.append(step)
        if fail_step == step:
            state.error = step
            return False
        return True

    if not enter("validate_local"):
        return state
    if not enter("connected_preflight"):
        return state
    if preexisting_final or preexisting_work or preexisting_stage:
        state.error = "preexisting-path"
        return state
    if not enter("reserve_stage_dir"):
        return state
    state.stage_dir_exists = True
    if not enter("transfer_payload"):
        state.stage_dir_exists = False
        return state
    state.payload_exists = True
    if not enter("verify_payload"):
        state.payload_exists = False
        state.stage_dir_exists = False
        return state
    state.payload_verified = True
    if not enter("recheck_final_absent"):
        state.payload_exists = False
        state.stage_dir_exists = False
        return state
    if final_race_before_publish:
        state.final_exists = True
        state.final_is_foreign = True
    if not enter("publish_link") or state.final_exists:
        state.error = state.error or "publish-no-clobber"
        state.payload_exists = False
        state.stage_dir_exists = False
        return state
    state.final_exists = True
    if not enter("verify_link_identity"):
        return state
    if not enter("verify_final"):
        return state
    state.final_verified = True
    if not enter("remove_payload_link"):
        return state
    state.payload_exists = False
    if not enter("remove_stage_dir"):
        return state
    state.stage_dir_exists = False
    if not enter("complete"):
        return state
    state.completed = True
    state.candidate_allowed = True
    return state


def source_contract_issues(source: str) -> tuple[str, ...]:
    issues: list[str] = []
    identity_start = source.find("REMOTE_FINAL_PREFIX_BY_CYCLE = {")
    identity_end = source.find("PSTORE_ZERO_RE =", identity_start + 1)
    if identity_start < 0 or identity_end < 0:
        issues.append("versioned run identity constant boundary is missing")
    else:
        identity = source[identity_start:identity_end]
        for token in (
            '"v3403": "debian-bookworm-arm64-d3-sysvinit-v3403-keyed-"',
            '"v3404": "debian-bookworm-arm64-d3-sysvinit-v3404-keyed-"',
            '"v3405": "debian-bookworm-arm64-d3-sysvinit-v3405-keyed-"',
            '"v3406": "debian-bookworm-arm64-phase2-display-v3406-keyed-"',
            'r"^a90-(?P<cycle>v3403|v3404|v3405|v3406)-"',
            'r"(?P<kind>debian|debian-display)-f1-"',
            'r"(?P<suffix>[0-9]{8}-[0-9]{2})$"',
        ):
            if identity.count(token) != 1:
                issues.append(f"versioned run identity is not exact: {token}")
    functions = {
        "private JSON": "def write_private_json_exclusive(",
        "run identity": "def exact_run_id_parts(",
        "approval binding": "def canonical_f1_approval_binding(",
        "connected D0 evidence": "def validate_connected_d0_evidence(",
        "path preflight evidence": "def validate_path_preflight_evidence(",
        "phase2 materialization": "def validate_phase2_keyed_materialization(",
        "parent approval": "def validate_parent_approval(",
        "host NCM": "def require_host_ncm_ready(",
        "preflight": "def remote_readonly_preflight_script(",
        "reserve": "def remote_reserve_script(",
        "verify": "def remote_verify_payload_script(",
        "publish": "def remote_publish_script(",
        "cleanup": "def remote_cleanup_script(",
    }
    positions: dict[str, int] = {}
    for label, marker in functions.items():
        pos = source.find(marker)
        if pos < 0:
            issues.append(f"missing {label} function")
        positions[label] = pos
    if not issues:
        run_identity = source[
            positions["run identity"]:source.find(
                "\ndef derive_remote_final(",
                positions["run identity"] + 1,
            )
        ]
        for token in (
            "match = RUN_ID_RE.fullmatch(run_id)",
            "if match is None:",
            'kind = match.group("kind")',
            'if (cycle == "v3406") != (kind == "debian-display"):',
            'return cycle, match.group("suffix")',
            'def expected_manifest_schema(run_id: str) -> str:',
            'if cycle == "v3406":',
            "return PHASE2_DISPLAY_MANIFEST_SCHEMA",
        ):
            if token not in run_identity:
                issues.append(f"run identity contract missing: {token}")
        parent_approval = source[
            positions["parent approval"]:positions["connected D0 evidence"]
        ]
        for token in (
            "expected_binding = canonical_f1_approval_binding(",
            'observation_mode=observation.get("mode")',
            'attended_window_sec=observation.get("attended_window_sec")',
            '"pre_handoff_attempt_limit"',
            'handoff_attempt_limit=observation.get("handoff_attempt_limit")',
            "binding != expected_binding",
        ):
            if token not in parent_approval:
                issues.append(
                    f"parent approval lacks canonical observation binding: {token}"
                )
        publish = source[positions["publish"]:positions["cleanup"]]
        for token in (
            '/bin/busybox ln "$PAYLOAD" "$FINAL"',
            '[ ! -e "$FINAL" ]',
            '[ ! -L "$FINAL" ]',
            'PAYLOAD_ID=$(/bin/busybox stat -c %d:%i "$PAYLOAD")',
            'FINAL_ID=$(/bin/busybox stat -c %d:%i "$FINAL")',
            '[ "$PAYLOAD_ID" = "$FINAL_ID" ]',
            'FINAL_SHA=$(/bin/busybox sha256sum "$FINAL")',
        ):
            if token not in publish:
                issues.append(f"publish contract missing: {token}")
        for forbidden in (
            'mv -f "$PAYLOAD" "$FINAL"',
            'cp "$PAYLOAD" "$FINAL"',
            'rm -rf',
            "/dev/block/",
            "userdata",
        ):
            if forbidden in publish:
                issues.append(f"publish contract contains forbidden token: {forbidden}")
    derivation_start = source.find("\ndef derive_remote_final(")
    derivation_end = source.find("\ndef validate_remote_final(", derivation_start + 1)
    if derivation_start < 0 or derivation_end < 0:
        issues.append("missing remote final derivation source boundary")
    else:
        derivation = source[derivation_start:derivation_end]
        for token in (
            "cycle, suffix = exact_run_id_parts(run_id)",
            "prefix = REMOTE_FINAL_PREFIX_BY_CYCLE[cycle]",
            'return REMOTE_ROOT / f"{prefix}{suffix}.img"',
        ):
            if token not in derivation:
                issues.append(f"remote final derivation contract missing: {token}")
    validator_start = source.find("\ndef validate_remote_final(")
    validator_end = source.find("\ndef validate_observer_device(", validator_start + 1)
    if validator_start < 0 or validator_end < 0:
        issues.append("missing remote final validator source boundary")
    else:
        validator = source[validator_start:validator_end]
        for token in (
            "expected = derive_remote_final(run_id)",
            "value != str(expected)",
            "path != expected",
            "path.parent != REMOTE_ROOT",
            "path == REMOTE_WORK",
        ):
            if token not in validator:
                issues.append(f"remote final validator contract missing: {token}")
    manifest_start = source.find("\ndef stage_spec_from_manifest(")
    manifest_end = source.find("\ndef verify_local_closure(", manifest_start + 1)
    if manifest_start < 0 or manifest_end < 0:
        issues.append("missing manifest loader source boundary")
    else:
        manifest_loader = source[manifest_start:manifest_end]
        if (
            'remote_final = validate_remote_final(keyed.get("device_path"), run_id)'
            not in manifest_loader
        ):
            issues.append("manifest remote final is not bound to its exact run_id")
        if "stage_dir = derive_stage_dir(run_id)" not in manifest_loader:
            issues.append("stage path is not derived from the stable run_id")
        for token in (
            'if cycle == "v3406":',
            "local_size != PHASE2_IMAGE_BYTES",
            "validate_phase2_keyed_materialization(",
            "elif keyed.get(\"materialization\") is not None:",
            "*((keyed_materialization,) if keyed_materialization else ())",
        ):
            if token not in manifest_loader:
                issues.append(
                    f"V3406 keyed materialization gate missing: {token}"
                )
    execute_start = source.find("\ndef execute_approved_stage(")
    inspect_start = source.find("\ndef inspect_manifest(", execute_start + 1)
    if execute_start < 0 or inspect_start < 0:
        issues.append("missing execute-stage source boundary")
    else:
        execute = source[execute_start:inspect_start]
        ordered = (
            "validate_parent_approval(",
            "verify_local_closure(spec)",
            "host_ncm = require_host_ncm_ready(",
            "require_exact_bridge(spec, args)",
            "require_baseline(args)",
            "remote_readonly_preflight_script(spec)",
            '"stage-reserve-start"',
            "remote_reserve_script(spec)",
            "transfer_command(spec, args)",
            '"payload-transfer-start"',
            "completed = subprocess.run(",
            "remote_verify_payload_script(spec)",
            '"publish-start"',
            "publish_attempted = True",
            "remote_publish_script(spec)",
            "published = True",
            '"candidate_allowed": True',
            'write_private_json_exclusive(run_dir / "result.json", result)',
        )
        cursor = -1
        for token in ordered:
            position = execute.find(token, cursor + 1)
            if position < 0:
                issues.append(f"execute contract missing or out of order: {token}")
                continue
            cursor = position
    append_start = source.find("\ndef append_record(")
    exact_dir_start = source.find("\ndef exact_live_run_dir(", append_start + 1)
    if append_start < 0 or exact_dir_start < 0:
        issues.append("missing append-record source boundary")
    elif "write_private_json_exclusive(path, body)" not in source[
        append_start:exact_dir_start
    ]:
        issues.append("staging journal does not use atomic exclusive publication")
    return tuple(issues)


def append_record(
    journal_dir: Path,
    state_name: str,
    payload: dict[str, Any],
    *,
    manifest_sha256: str,
    run_id: str,
) -> Path:
    journal_dir.mkdir(parents=True, exist_ok=True)
    sequence = len(list(journal_dir.glob("*.json")))
    path = journal_dir / f"{sequence:04d}-{state_name}.json"
    body = {
        **payload,
        "schema": "a90_v3403_absent_only_stage_journal_v1",
        "sequence": sequence,
        "timestamp_utc": utc_now(),
        "state": state_name,
        "manifest_sha256": manifest_sha256,
        "run_id": run_id,
    }
    write_private_json_exclusive(path, body)
    return path


def exact_live_run_dir(spec: StageSpec, requested: Path) -> Path:
    expected = (PRIVATE_RUN_BASE / spec.run_id / "staging-live").resolve()
    actual = requested.resolve()
    if actual != expected:
        raise ContractError(f"run_dir must be the exact private staging path: {expected}")
    require_below(actual, PRIVATE_RUN_BASE, "run_dir")
    return actual


def run_remote(args: argparse.Namespace, script: str, *, allow_error: bool = False) -> dict[str, Any]:
    return d1.run_shell(
        args.bridge_host,
        args.bridge_port,
        args.remote_timeout,
        script,
        allow_error=allow_error,
    )


def require_baseline(
    args: argparse.Namespace,
    *,
    input_mode: str | None = None,
    input_char_delay_sec: float | None = None,
) -> dict[str, Any]:
    version = d1.run_cmd(
        args.bridge_host,
        args.bridge_port,
        args.remote_timeout,
        ["version"],
        input_mode=input_mode,
        input_char_delay_sec=input_char_delay_sec,
    )
    status_result = d1.run_cmd(
        args.bridge_host,
        args.bridge_port,
        args.remote_timeout,
        ["status"],
        input_mode=input_mode,
        input_char_delay_sec=input_char_delay_sec,
    )
    selftest = d1.run_cmd(
        args.bridge_host,
        args.bridge_port,
        args.remote_timeout,
        ["selftest"],
        input_mode=input_mode,
        input_char_delay_sec=input_char_delay_sec,
    )
    version_text = str(version.get("text") or "")
    status_text = str(status_result.get("text") or "")
    selftest_text = str(selftest.get("text") or "")
    if EXPECTED_BASELINE_VERSION not in version_text or EXPECTED_BASELINE_BUILD not in version_text:
        raise ContractError("resident A90 is not the exact V2321 baseline")
    if "fail=0" not in selftest_text:
        raise ContractError("resident A90 selftest is not fail=0")
    if PSTORE_ZERO_RE.search(status_text) is None:
        raise ContractError("resident A90 pstore health is not exact zero")
    return {"version": version, "status": status_result, "selftest": selftest}


def require_exact_bridge(spec: StageSpec, args: argparse.Namespace) -> dict[str, Any]:
    command = [
        sys.executable,
        str(REVAL_DIR / "a90_bridge.py"),
        "preflight",
        "--host",
        args.bridge_host,
        "--port",
        str(args.bridge_port),
        "--device",
        spec.bridge_device,
        "--expect-realpath",
        spec.bridge_realpath,
        "--json",
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30.0,
        check=False,
    )
    if result.returncode != 0:
        raise ContractError(
            f"exact bridge preflight failed rc={result.returncode}: {result.stderr}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ContractError(f"exact bridge preflight returned invalid JSON: {exc}") from exc
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    if (
        payload.get("ok") is not True
        or payload.get("selected_device") != spec.bridge_device
        or payload.get("selected_realpath") != spec.bridge_realpath
        or metadata.get("effective_expect_realpath") != spec.bridge_realpath
        or payload.get("bridge_process") != "running"
        or payload.get("port_listening") is not True
    ):
        raise ContractError("exact bridge continuity did not validate")
    return payload


def _read_sysfs_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="strict").strip()
    except OSError:
        return ""


def _usb_device_parent(path: Path) -> Path | None:
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return None
    for parent in (resolved, *resolved.parents):
        vendor = _read_sysfs_text(parent / "idVendor").lower()
        product = _read_sysfs_text(parent / "idProduct").lower()
        if vendor and product:
            return parent
    return None


def exact_a90_ncm_interfaces(bridge_realpath: str) -> tuple[str, ...]:
    if BRIDGE_REALPATH_RE.fullmatch(bridge_realpath) is None:
        return ()
    bridge_parent = _usb_device_parent(
        SYS_CLASS_TTY / Path(bridge_realpath).name
    )
    if bridge_parent is None:
        return ()
    if (
        _read_sysfs_text(bridge_parent / "idVendor").lower()
        != HOST_NCM_VENDOR_ID
        or _read_sysfs_text(bridge_parent / "idProduct").lower()
        != HOST_NCM_PRODUCT_ID
    ):
        return ()
    try:
        netdevs = tuple(SYS_CLASS_NET.iterdir())
    except OSError:
        return ()
    matches: list[str] = []
    for netdev in netdevs:
        if HOST_IFACE_RE.fullmatch(netdev.name) is None:
            continue
        try:
            driver = (netdev / "device" / "driver").resolve(strict=True).name
        except OSError:
            continue
        if (
            driver == HOST_NCM_DRIVER
            and _usb_device_parent(netdev) == bridge_parent
        ):
            matches.append(netdev.name)
    return tuple(sorted(matches))


def host_interface_is_exact_a90_ncm(
    interface: str,
    bridge_realpath: str,
) -> bool:
    if HOST_IFACE_RE.fullmatch(interface) is None or interface in {".", ".."}:
        return False
    return exact_a90_ncm_interfaces(bridge_realpath) == (interface,)


def _route_token(tokens: list[str], name: str) -> str:
    if tokens.count(name) != 1:
        raise ContractError(f"host NCM route lacks one exact {name} field")
    index = tokens.index(name)
    if index + 1 >= len(tokens):
        raise ContractError(f"host NCM route has an incomplete {name} field")
    return tokens[index + 1]


def require_host_ncm_ready(
    device_ip: str,
    bridge_realpath: str,
) -> dict[str, bool]:
    device = ipaddress.IPv4Address(validate_observer_device(device_ip))
    network = ipaddress.IPv4Network(f"{device}/{HOST_NCM_PREFIX}", strict=False)
    host = ipaddress.IPv4Address(int(device) - 1)
    if host not in network or host == network.network_address:
        raise ContractError("observer device address has no expected host peer")
    host_cidr = f"{host}/{HOST_NCM_PREFIX}"

    try:
        route = subprocess.run(
            ["ip", "-4", "route", "get", str(device)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=5.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ContractError("host NCM direct-route check failed") from exc
    route_lines = [line for line in route.stdout.splitlines() if line.strip()]
    if (
        route.returncode != 0
        or not route_lines
        or any(line.strip() != "cache" for line in route_lines[1:])
    ):
        raise ContractError("host NCM direct route is unavailable")
    tokens = route_lines[0].split()
    if not tokens or tokens[0] != str(device) or "via" in tokens:
        raise ContractError("observer route is not direct USB-local")
    interface = _route_token(tokens, "dev")
    source = _route_token(tokens, "src")
    if source != str(host):
        raise ContractError("observer route does not use the expected host peer")
    if not host_interface_is_exact_a90_ncm(interface, bridge_realpath):
        raise ContractError("observer route is not on the exact A90 NCM interface")

    try:
        address = subprocess.run(
            ["ip", "-4", "-o", "addr", "show", "dev", interface],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=5.0,
            check=False,
        )
        ping = subprocess.run(
            ["ping", "-n", "-c", "1", "-W", "2", str(device)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=5.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ContractError("host NCM address or reachability check failed") from exc
    if address.returncode != 0 or host_cidr not in address.stdout.split():
        raise ContractError("exact A90 NCM interface lacks the expected host CIDR")
    if ping.returncode != 0:
        raise ContractError("observer device is not reachable on USB-local NCM")
    return {
        "verified_a90_ncm": True,
        "direct_route": True,
        "host_cidr_present": True,
        "device_ping": True,
    }


def execute_approved_stage(
    spec: StageSpec,
    manifest: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    if manifest.get("schema") != expected_manifest_schema(spec.run_id):
        raise ContractError("live staging refuses a non-final manifest schema")
    if manifest.get("status") != FINAL_MANIFEST_STATUS:
        raise ContractError("live staging refuses a non-ready manifest status")
    if args.approved_manifest_sha256 != spec.manifest_sha256:
        raise ContractError("approved manifest sha256 does not match")
    adapter_sha = sha256_file(Path(__file__).resolve())
    if args.approved_adapter_sha256 != adapter_sha:
        raise ContractError("approved adapter sha256 does not match")
    if args.approved_run_id != spec.run_id:
        raise ContractError("approved run_id does not match")
    if args.device_ip != spec.observer_device:
        raise ContractError("staging device address does not match the manifest observer")
    approval_prepared = validate_parent_approval(
        spec,
        manifest,
        args.approval,
    )

    verify_local_closure(spec)
    run_dir = exact_live_run_dir(spec, args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    journal_dir = run_dir / "journal"
    def record(state_name: str, payload: dict[str, Any]) -> Path:
        return append_record(
            journal_dir,
            state_name,
            payload,
            manifest_sha256=spec.manifest_sha256,
            run_id=spec.run_id,
        )

    record(
        "approval-binding-reopened",
        {
            "run_id": spec.run_id,
            "manifest_sha256": spec.manifest_sha256,
            "adapter_sha256": adapter_sha,
            "rootfs_sha256": spec.local_sha256,
            "approval_binding_sha256": approval_prepared[
                "approval_binding_sha256"
            ],
            "device_write": False,
        },
    )

    host_ncm = require_host_ncm_ready(
        spec.observer_device,
        spec.bridge_realpath,
    )
    exact_bridge = require_exact_bridge(spec, args)
    baseline = require_baseline(args)
    readonly = run_remote(args, remote_readonly_preflight_script(spec))
    record(
        "connected-preflight",
        {
            "exact_bridge": True,
            "bridge_selected_realpath": exact_bridge.get("selected_realpath"),
            "baseline_version": EXPECTED_BASELINE_VERSION,
            "baseline_build": EXPECTED_BASELINE_BUILD,
            "selftest_fail_zero": True,
            "host_ncm": host_ncm,
            "remote_preflight": readonly,
            "device_write": False,
        },
    )

    stage_reserved = False
    published = False
    publish_attempted = False
    transfer_result: dict[str, Any] | None = None
    try:
        record(
            "stage-reserve-start",
            {"device_write_may_follow": True},
        )
        reserve = run_remote(args, remote_reserve_script(spec))
        stage_reserved = True
        record("stage-reserved", {"record": reserve})

        command = transfer_command(spec, args)
        record(
            "payload-transfer-start",
            {
                "device_path": spec.remote_payload,
                "size": spec.local_size,
                "sha256": spec.local_sha256,
            },
        )
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=args.transfer_timeout + args.bridge_timeout + 120.0,
            check=False,
        )
        transfer_result = {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        if completed.returncode != 0:
            raise RuntimeError(f"payload transfer failed rc={completed.returncode}")
        record("payload-transfer-complete", transfer_result)

        payload = run_remote(args, remote_verify_payload_script(spec))
        record("payload-verified", {"record": payload})
        record(
            "publish-start",
            {"primitive": "hardlink-no-clobber", "final": spec.remote_final},
        )
        publish_attempted = True
        publish = run_remote(args, remote_publish_script(spec))
        published = True
        record("published", {"record": publish})
        require_baseline(args)
        result = {
            "schema": ADAPTER_SCHEMA,
            "run_id": spec.run_id,
            "status": "PASS_ABSENT_ONLY_ROOTFS_STAGED",
            "manifest_sha256": spec.manifest_sha256,
            "adapter_sha256": adapter_sha,
            "rootfs": {
                "device_path": spec.remote_final,
                "size": spec.local_size,
                "sha256": spec.local_sha256,
            },
            "publication": {
                "primitive": "hardlink-no-clobber",
                "stage_dir_removed": True,
                "candidate_allowed": True,
            },
            "safety": {
                "flash": False,
                "reboot": False,
                "mount": False,
                "switch_root": False,
                "userdata_touched": False,
            },
            "final_health": {
                "version": EXPECTED_BASELINE_VERSION,
                "build": EXPECTED_BASELINE_BUILD,
                "selftest_fail_zero": True,
            },
        }
        write_private_json_exclusive(run_dir / "result.json", result)
        record("closed", {"result": result})
        return result
    except Exception as exc:
        cleanup: dict[str, Any] | None = None
        if stage_reserved:
            try:
                cleanup = run_remote(
                    args,
                    remote_cleanup_script(spec),
                    allow_error=True,
                )
            except Exception as cleanup_exc:  # noqa: BLE001 - preserve primary failure
                cleanup = {
                    "error": type(cleanup_exc).__name__,
                    "message": str(cleanup_exc),
                }
        record(
            "aborted",
            {
                "error": type(exc).__name__,
                "message": str(exc),
                "published_may_exist": publish_attempted,
                "publish_completed": published,
                "candidate_allowed": False,
                "cleanup": cleanup,
                "transfer": transfer_result,
            },
        )
        raise


def inspect_manifest(spec: StageSpec, issues: list[str]) -> dict[str, Any]:
    verify_local_closure(spec)
    source = Path(__file__).read_text(encoding="utf-8")
    source_issues = source_contract_issues(source)
    all_issues = [*issues, *source_issues]
    return {
        "schema": ADAPTER_SCHEMA,
        "mode": "host-only-inspection",
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "adapter_sha256": sha256_file(Path(__file__).resolve()),
        "tcpctl_host_sha256": spec.tcpctl_host_sha256,
        "local_rootfs": {
            "path": str(spec.local_image),
            "size": spec.local_size,
            "sha256": spec.local_sha256,
        },
        "remote": {
            "mount": str(REMOTE_MOUNT),
            "required_fstype": REQUIRED_FS_TYPE,
            "final": spec.remote_final,
            "work": spec.remote_work,
            "stage_dir": spec.remote_stage_dir,
            "payload": spec.remote_payload,
            "publication": "hardlink-no-clobber",
        },
        "contract_issues": all_issues,
        "ready_for_parent_approval": not all_issues,
        "ready_for_live_staging": False,
        "fresh_parent_approval_required": True,
        "device_contact": False,
        "device_write": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expect-manifest-sha256", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--execute-approved-stage", action="store_true")
    parser.add_argument("--approved-manifest-sha256", default="")
    parser.add_argument("--approved-adapter-sha256", default="")
    parser.add_argument("--approved-run-id", default="")
    parser.add_argument("--approval")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--bridge-host", default="localhost")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--device-ip")
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--remote-timeout", type=float, default=180.0)
    parser.add_argument("--bridge-timeout", type=float, default=120.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--tcp-timeout", type=float, default=60.0)
    parser.add_argument("--transfer-timeout", type=float, default=1200.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    spec, manifest, issues = stage_spec_from_manifest(
        args.manifest,
        args.expect_manifest_sha256,
        allow_draft=not args.execute_approved_stage,
    )
    if not args.execute_approved_stage:
        result = inspect_manifest(spec, issues)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if not result["contract_issues"] else 2

    if args.run_dir is None:
        raise ContractError("--run-dir is required for approved staging")
    if not args.device_ip:
        raise ContractError("--device-ip is required for approved staging")
    if not args.approval:
        raise ContractError("--approval is required for approved staging")
    result = execute_approved_stage(spec, manifest, args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
