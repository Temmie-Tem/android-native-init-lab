#!/usr/bin/env python3
"""One-shot attended removal of fixed obsolete A90 SD images from healthy H5.

The selected set is closed in source: twelve superseded V3406 rootfs images,
five older rootfs/clean images, and three WSTA snapshots.  The installed H5
run-12 source is a separate exact protected identity.  Inventory is D0; live
execution writes one durable intent and one capability-wide dispatch receipt,
sends one nonrecursive unlink frame, and never retransmits it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import socket
import stat
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SERVER_DIR = Path(__file__).resolve().parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import a90_h5_h4_source_reclaim_v1 as h5  # noqa: E402
import a90_obsolete_rootfs_cleanup_v1 as gc  # noqa: E402
import a90_v3405_retained_work_cleanup as legacy  # noqa: E402


RUNNER = Path(__file__).resolve()
PRIVATE_BASE = (
    REPO_ROOT / "workspace/private/runs/server-distro"
).resolve()
PRIVATE_ROOT = (REPO_ROOT / "workspace/private").resolve()
COMMON_CONTRACT = (REPO_ROOT / "AGENTS.md").resolve()
TARGET_CONTRACT = (
    REPO_ROOT / "docs/operations/targets/A90_TARGET_CONTRACT.md"
).resolve()
RISK_TIERS = (
    REPO_ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md"
).resolve()

SCHEMA = "a90_h5_historical_image_gc_manifest_v1"
INVENTORY_SCHEMA = "a90_h5_historical_image_gc_inventory_v1"
RESULT_SCHEMA = "a90_h5_historical_image_gc_result_v1"
INTENT_SCHEMA = "a90_h5_historical_image_gc_intent_v1"
DISPATCH_SCHEMA = "a90_h5_historical_image_gc_dispatch_v1"
EFFECT_NOT_STARTED_SCHEMA = "a90_h5_historical_image_gc_effect_not_started_v1"
CAPABILITY = "A90_ATTENDED_H5_HISTORICAL_IMAGE_GC_V1"
HAZARD = "SD_CAPACITY_EXHAUSTION_FROM_SUPERSEDED_EXPERIMENT_IMAGES"
RUN_ID_RE = re.compile(r"^a90-h5-historical-image-gc-[0-9]{8}-[0-9]{2}$")
CAPABILITY_STATE_DIR = "a90-h5-historical-image-gc-capability-v1"
CAPABILITY_EXPIRES_UTC = "2026-08-08T00:00:00Z"
MAX_INVENTORY_AGE_SEC = 3600
READ_TIMEOUT_SEC = 30.0
HASH_TIMEOUT_SEC = 300.0
EFFECT_TIMEOUT_SEC = 300.0
FREE_GAIN_TOLERANCE_KIB = 131072
HOST_NCM_ADDRESS = "192.168.7.1"
DEVICE_NCM_ADDRESS = "192.168.7.2"
PRESERVE_TIMEOUT_SEC = 240.0
RUNTIME_DIR = "/mnt/sdext/a90/runtime"
WORK_PATH = f"{RUNTIME_DIR}/d3-handoff-work.img"
PROTECTED_PATH = (
    f"{RUNTIME_DIR}/"
    "debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-12.img"
)
PROTECTED_SIZE = 2147483648
PROTECTED_MODE = "600"
PROTECTED_SHA256 = h5.PROTECTED_SHA256
PASS_OUTCOME = "PASS_HISTORICAL_IMAGES_AND_SNAPSHOTS_RECLAIMED_H5_HEALTHY"
PASS_AMBIGUOUS_OUTCOME = (
    "PASS_HISTORICAL_IMAGE_GC_PROVEN_AFTER_AMBIGUOUS_RESPONSE"
)


@dataclass(frozen=True)
class FixedArtifact:
    token: str
    name: str
    size: int
    mode: str

    @property
    def path(self) -> str:
        return f"{RUNTIME_DIR}/{self.name}"


@dataclass(frozen=True)
class ArtifactRecord:
    token: str
    path: str
    size: int
    blocks: int
    mode: str
    nlink: int
    st_dev: int
    st_ino: int
    sha256: str


@dataclass(frozen=True)
class Spec:
    manifest_path: Path
    manifest_sha256: str
    run_id: str
    inventory: legacy.BoundFile
    bridge_realpath: str
    bridge_process: dict[str, Any]
    selected: tuple[ArtifactRecord, ...]
    protected: ArtifactRecord
    host_preservation: dict[str, legacy.BoundFile]
    host_preservation_receipt: legacy.BoundFile
    source_closure: dict[str, legacy.BoundFile]
    evidence: dict[str, legacy.BoundFile]
    rollback: legacy.BoundFile
    capability_dispatch_path: Path


GIB2 = 2147483648
GIB15 = 1610612736
SELECTED_FIXED = (
    FixedArtifact("01", "a90-wsta98-packet-filter-rootfs.img", GIB2, "755"),
    FixedArtifact("02", "a90-wsta98-packet-filter-rootfs.img.clean", GIB2, "755"),
    FixedArtifact("03", "debian-bookworm-arm64-20260701-024412.img", GIB2, "755"),
    FixedArtifact("04", "debian-bookworm-arm64-20260701-024412.img.clean", GIB2, "755"),
    FixedArtifact("05", "debian-bookworm-arm64-d3-sysvinit-keyed.img", GIB2, "755"),
    FixedArtifact("06", "debian-bookworm-arm64-phase2-display-v3406-keyed-20260801-03.img", GIB2, "600"),
    FixedArtifact("07", "debian-bookworm-arm64-phase2-display-v3406-keyed-20260801-06.img", GIB2, "600"),
    FixedArtifact("08", "debian-bookworm-arm64-phase2-display-v3406-keyed-20260801-09.img", GIB2, "600"),
    FixedArtifact("09", "debian-bookworm-arm64-phase2-display-v3406-keyed-20260801-10.img", GIB2, "600"),
    FixedArtifact("10", "debian-bookworm-arm64-phase2-display-v3406-keyed-20260802-01.img", GIB2, "600"),
    FixedArtifact("11", "debian-bookworm-arm64-phase2-display-v3406-keyed-20260803-02.img", GIB2, "600"),
    FixedArtifact("12", "debian-bookworm-arm64-phase2-display-v3406-keyed-20260803-03.img", GIB2, "600"),
    FixedArtifact("13", "debian-bookworm-arm64-phase2-display-v3406-keyed-20260803-04.img", GIB2, "600"),
    FixedArtifact("14", "debian-bookworm-arm64-phase2-display-v3406-keyed-20260804-02.img", GIB2, "600"),
    FixedArtifact("15", "debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-02.img", GIB2, "600"),
    FixedArtifact("16", "debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-03.img", GIB2, "600"),
    FixedArtifact("17", "debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-09.img", GIB2, "600"),
    FixedArtifact("18", "wsta16-immediate-snapshot.img", GIB15, "755"),
    FixedArtifact("19", "wsta17-handoff-materialization.img", GIB15, "755"),
    FixedArtifact("20", "wsta18-control-plane.img", GIB15, "755"),
)

STAGED_HOST_RUNS = {
    "06": ("a90-v3406-debian-display-f1-20260801-03", "phase2-display-v1-keyed.img"),
    "07": ("a90-v3406-debian-display-f1-20260801-06", "phase2-display-v1-keyed.img"),
    "08": ("a90-v3406-debian-display-f1-20260801-09", "phase2-display-v1-keyed.img"),
    "09": ("a90-v3406-debian-display-f1-20260801-10", "phase2-display-v1-keyed.img"),
    "10": ("a90-v3406-debian-display-f1-20260802-01", "phase2-display-v1-keyed.img"),
    "11": ("a90-v3406-debian-display-f1-20260803-02", "phase3-network-ssh-v1-keyed.img"),
    "12": ("a90-v3406-debian-display-f1-20260803-03", "phase3-network-ssh-v1-keyed.img"),
    "13": ("a90-v3406-debian-display-f1-20260803-04", "phase3-network-ssh-v1-keyed.img"),
    "14": ("a90-v3406-debian-display-f1-20260804-02", "phase3-network-ssh-v1-keyed.img"),
    "15": ("a90-v3406-debian-display-f1-20260805-02", "phase3-network-ssh-v1-keyed.img"),
    "16": ("a90-v3406-debian-display-f1-20260805-03", "phase3-network-ssh-v1-keyed.img"),
    "17": ("a90-v3406-debian-display-f1-20260805-09", "phase3-network-ssh-v1-keyed.img"),
}
MISSING_HOST_TOKENS = frozenset({"01", "02", "03", "04", "05", "18", "19", "20"})


class ContractError(RuntimeError):
    """The fixed historical-image cleanup contract is not satisfied."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bound(path: Path, *, private: bool) -> legacy.BoundFile:
    resolved = path.resolve(strict=True)
    state = path.lstat()
    if not stat.S_ISREG(state.st_mode) or state.st_nlink != 1:
        raise ContractError(f"bound file is not one regular file: {path}")
    if private and (
        not resolved.is_relative_to(PRIVATE_ROOT)
        or stat.S_IMODE(state.st_mode) != 0o600
    ):
        raise ContractError(f"private bound file is outside mode-0600 private scope: {path}")
    return legacy.BoundFile(resolved, state.st_size, _sha256_file(resolved))


def _bound_value(bound: legacy.BoundFile) -> dict[str, Any]:
    return {"path": str(bound.path), "size": bound.size, "sha256": bound.sha256}


def _load_bound(value: Any, label: str, *, private: bool) -> legacy.BoundFile:
    if not isinstance(value, dict) or set(value) != {"path", "size", "sha256"}:
        raise ContractError(f"{label} binding shape changed")
    bound = _bound(Path(str(value["path"])), private=private)
    if _bound_value(bound) != value:
        raise ContractError(f"{label} binding changed")
    return bound


def _source_paths() -> dict[str, Path]:
    paths = {f"h5_{role}": path for role, path in h5._source_paths().items()}  # noqa: SLF001
    paths.update(
        {
            "runner": RUNNER,
            "common_contract": COMMON_CONTRACT,
            "target_contract": TARGET_CONTRACT,
            "risk_tiers": RISK_TIERS,
            "host_ncm_rebind": Path(h5.auto.base.__file__).resolve(),
            "host_ncm_identity": Path(h5.auto.base.staging.__file__).resolve(),
        }
    )
    return {role: path.resolve() for role, path in paths.items()}


def execution_closure() -> dict[str, Any]:
    files = {
        role: _bound_value(_bound(path, private=False))
        for role, path in sorted(_source_paths().items())
    }
    return {"sha256": legacy.json_sha256(files), "files": files}


def capability_dispatch_path() -> Path:
    return (
        PRIVATE_BASE / CAPABILITY_STATE_DIR / "dispatch-started.json"
    ).resolve()


def _require_unconsumed() -> None:
    state_dir = capability_dispatch_path().parent
    if state_dir.exists() or capability_dispatch_path().exists():
        raise ContractError("historical-image GC capability is already consumed")


def _require_not_expired() -> None:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if now >= CAPABILITY_EXPIRES_UTC:
        raise ContractError("historical-image GC capability expired")


def _target() -> tuple[str, dict[str, Any]]:
    realpath, serial_sha = gc._find_target()  # noqa: SLF001
    if serial_sha != gc.USB_SERIAL_SHA256:
        raise ContractError("A90 USB identity changed")
    bridge = h5.engine._require_bridge(realpath)  # noqa: SLF001
    return realpath, bridge


def _artifact_script(*, hash_bytes: bool) -> str:
    lines = [
        "set -eu",
        "P=$1; Z=$2; M=$3; T=$4",
        '[ ! -L "$P" ]; [ -f "$P" ]',
        'X=$(/bin/busybox stat -c "%s|%b|%a|%h|%d|%i" "$P")',
        '[ "${X%%|*}" = "$Z" ]',
    ]
    if hash_bytes:
        lines.extend(
            [
                'S=$(/bin/busybox sha256sum "$P")',
                'S=${S%% *}',
                'echo "A90HIST_ART|$T|$P|$X|$S"',
            ]
        )
    else:
        lines.append('echo "A90HIST_META|$T|$P|$X"')
    return "\n".join(lines)


ART_RE = re.compile(
    r"^A90HIST_ART\|(?P<token>[0-9]{2}|P)\|(?P<path>/mnt/sdext/a90/runtime/[A-Za-z0-9._-]+)"
    r"\|(?P<size>[0-9]+)\|(?P<blocks>[0-9]+)\|(?P<mode>[0-9]+)"
    r"\|(?P<nlink>[0-9]+)\|(?P<dev>[0-9]+)\|(?P<ino>[0-9]+)"
    r"\|(?P<sha>[0-9a-f]{64})\r?$",
    re.MULTILINE,
)
META_RE = re.compile(
    r"^A90HIST_META\|(?P<token>[0-9]{2}|P)\|(?P<path>/mnt/sdext/a90/runtime/[A-Za-z0-9._-]+)"
    r"\|(?P<size>[0-9]+)\|(?P<blocks>[0-9]+)\|(?P<mode>[0-9]+)"
    r"\|(?P<nlink>[0-9]+)\|(?P<dev>[0-9]+)\|(?P<ino>[0-9]+)\r?$",
    re.MULTILINE,
)


def _read_artifact(
    fixed: FixedArtifact,
    *,
    hash_bytes: bool,
    expected: ArtifactRecord | None = None,
) -> ArtifactRecord:
    text = gc._run_script(  # noqa: SLF001
        _artifact_script(hash_bytes=hash_bytes),
        HASH_TIMEOUT_SEC if hash_bytes else READ_TIMEOUT_SEC,
        f"historical image {fixed.token} {'hash' if hash_bytes else 'metadata'}",
        args=(fixed.path, str(fixed.size), fixed.mode, fixed.token),
    )
    match = (ART_RE if hash_bytes else META_RE).search(text)
    if match is None or len((ART_RE if hash_bytes else META_RE).findall(text)) != 1:
        raise ContractError(f"historical image {fixed.token} receipt is not exact")
    item = match.groupdict()
    sha = item.get("sha") or (expected.sha256 if expected is not None else "")
    record = ArtifactRecord(
        token=fixed.token,
        path=fixed.path,
        size=int(item["size"]),
        blocks=int(item["blocks"]),
        mode=item["mode"],
        nlink=int(item["nlink"]),
        st_dev=int(item["dev"]),
        st_ino=int(item["ino"]),
        sha256=sha,
    )
    if (
        record.path != fixed.path
        or record.size != fixed.size
        or record.mode != fixed.mode
        or record.nlink != 1
        or record.blocks <= 0
        or record.st_dev <= 0
        or record.st_ino <= 0
        or re.fullmatch(r"[0-9a-f]{64}", record.sha256) is None
        or (expected is not None and record != expected)
    ):
        raise ContractError(f"historical image {fixed.token} identity changed")
    return record


def _protected_fixed() -> FixedArtifact:
    return FixedArtifact("P", Path(PROTECTED_PATH).name, PROTECTED_SIZE, PROTECTED_MODE)


def _stage_and_work_absent() -> dict[str, int]:
    script = "\n".join(
        (
            "set -eu",
            f"W={shlex.quote(WORK_PATH)}",
            '[ ! -e "$W" ] && [ ! -L "$W" ]',
            "for X in /mnt/sdext/a90/runtime/.a90-stage-* "
            "/mnt/sdext/a90/runtime/.a90-d1-stage-* "
            "/mnt/sdext/a90/runtime/.a90-cleanup-restore-*; do "
            '[ ! -e "$X" ] && [ ! -L "$X" ] || exit 60; done',
            "set -- $(/bin/busybox df -k /mnt/sdext | /bin/busybox tail -n 1)",
            'echo "A90HIST_DF|$2|$3|$4"',
        )
    )
    text = gc._run_script(script, READ_TIMEOUT_SEC, "historical GC filesystem state")  # noqa: SLF001
    matches = re.findall(r"^A90HIST_DF\|([0-9]+)\|([0-9]+)\|([0-9]+)\r?$", text, re.MULTILINE)
    if len(matches) != 1:
        raise ContractError("historical GC filesystem receipt is not exact")
    blocks, used, available = (int(value) for value in matches[0])
    return {"blocks": blocks, "used": used, "available": available}


def _record_value(item: ArtifactRecord) -> dict[str, Any]:
    return {
        "token": item.token,
        "path": item.path,
        "size": item.size,
        "blocks": item.blocks,
        "mode": item.mode,
        "nlink": item.nlink,
        "st_dev": item.st_dev,
        "st_ino": item.st_ino,
        "sha256": item.sha256,
    }


def _preserved_path(run_id: str, fixed: FixedArtifact) -> Path:
    return (
        PRIVATE_BASE
        / run_id
        / "host-preserved"
        / f"{fixed.token}-{fixed.name}"
    ).resolve()


def _staged_host_preservation(
    fixed: FixedArtifact,
    record: ArtifactRecord,
) -> legacy.BoundFile:
    binding = STAGED_HOST_RUNS.get(fixed.token)
    if binding is None:
        raise ContractError(f"artifact {fixed.token} has no staged host binding")
    run_id, filename = binding
    run_dir = (PRIVATE_BASE / run_id).resolve()
    prepared = _bound(run_dir / "prepared-manifest.json", private=True)
    result = _bound(run_dir / "staging-live/result.json", private=True)
    prepared_value = json.loads(prepared.path.read_text(encoding="utf-8"))
    result_value = json.loads(result.path.read_text(encoding="utf-8"))
    keyed = prepared_value.get("debian_rootfs", {}).get("keyed_source", {})
    rootfs = result_value.get("rootfs", {})
    host_path = (run_dir / filename).resolve()
    host = _bound(host_path, private=True)
    if (
        prepared_value.get("run_id") != run_id
        or result_value.get("schema")
        != "a90_v3403_absent_only_staging_adapter_v1"
        or result_value.get("status") != "PASS_ABSENT_ONLY_ROOTFS_STAGED"
        or result_value.get("run_id") != run_id
        or result_value.get("manifest_sha256") != prepared.sha256
        or keyed.get("local_path") != str(host_path)
        or keyed.get("device_path") != fixed.path
        or keyed.get("size") != fixed.size
        or keyed.get("sha256") != record.sha256
        or rootfs
        != {
            "device_path": fixed.path,
            "size": fixed.size,
            "sha256": record.sha256,
        }
        or host.size != fixed.size
        or host.sha256 != record.sha256
    ):
        raise ContractError(f"artifact {fixed.token} staged host copy changed")
    return host


def _all_host_preservation(
    run_id: str,
    records: tuple[ArtifactRecord, ...],
) -> dict[str, legacy.BoundFile]:
    preserved: dict[str, legacy.BoundFile] = {}
    for fixed, record in zip(SELECTED_FIXED, records, strict=True):
        host = (
            _bound(_preserved_path(run_id, fixed), private=True)
            if fixed.token in MISSING_HOST_TOKENS
            else _staged_host_preservation(fixed, record)
        )
        if host.size != record.size or host.sha256 != record.sha256:
            raise ContractError(f"artifact {fixed.token} host bytes are not exact")
        preserved[fixed.token] = host
    if set(preserved) != {item.token for item in SELECTED_FIXED}:
        raise ContractError("host-preserved recovery set is not complete")
    return preserved


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _receive_sparse_preservation(
    fixed: FixedArtifact,
    record: ArtifactRecord,
    destination: Path,
) -> dict[str, Any]:
    partial = destination.with_name(destination.name + ".partial")
    if destination.exists() or destination.is_symlink() or partial.exists() or partial.is_symlink():
        raise ContractError(f"artifact {fixed.token} preservation destination is not fresh")
    errors: list[BaseException] = []
    received: dict[str, Any] = {"size": 0, "peer": None, "sha256": None}
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((HOST_NCM_ADDRESS, 0))
    listener.listen(1)
    listener.settimeout(60.0)
    port = listener.getsockname()[1]

    def receive() -> None:
        digest = hashlib.sha256()
        zero = bytes(1024 * 1024)
        try:
            connection, peer = listener.accept()
            with connection:
                connection.settimeout(PRESERVE_TIMEOUT_SEC)
                received["peer"] = peer[0]
                if peer[0] != DEVICE_NCM_ADDRESS:
                    raise ContractError("preservation peer is not exact A90 NCM")
                descriptor = os.open(
                    partial,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
                with os.fdopen(descriptor, "wb") as stream:
                    while True:
                        chunk = connection.recv(1024 * 1024)
                        if not chunk:
                            break
                        if received["size"] + len(chunk) > record.size:
                            raise ContractError("preservation stream exceeded exact size")
                        digest.update(chunk)
                        if chunk == zero[: len(chunk)]:
                            stream.seek(len(chunk), os.SEEK_CUR)
                        else:
                            stream.write(chunk)
                        received["size"] += len(chunk)
                    stream.truncate(record.size)
                    stream.flush()
                    os.fsync(stream.fileno())
                received["sha256"] = digest.hexdigest()
        except BaseException as exc:  # delivered after the bounded join
            errors.append(exc)
        finally:
            listener.close()

    thread = threading.Thread(target=receive, daemon=True)
    thread.start()
    try:
        receipt_text = gc._run_script(  # noqa: SLF001
            'exec /bin/busybox nc -n -w 180 "$1" "$2" < "$3"',
            PRESERVE_TIMEOUT_SEC,
            f"historical image {fixed.token} host preservation",
            args=(HOST_NCM_ADDRESS, str(port), fixed.path),
        )
    except Exception:
        listener.close()
        thread.join(timeout=2.0)
        if partial.exists() and not partial.is_symlink():
            partial.unlink()
        raise
    thread.join(timeout=PRESERVE_TIMEOUT_SEC)
    if thread.is_alive() or errors:
        if partial.exists() and not partial.is_symlink():
            partial.unlink()
        raise ContractError(f"artifact {fixed.token} preservation receiver failed: {errors!r}")
    if (
        received["peer"] != DEVICE_NCM_ADDRESS
        or received["size"] != record.size
        or received["sha256"] != record.sha256
    ):
        if partial.exists() and not partial.is_symlink():
            partial.unlink()
        raise ContractError(f"artifact {fixed.token} preservation identity changed")
    os.link(partial, destination, follow_symlinks=False)
    _fsync_directory(destination.parent)
    partial.unlink()
    _fsync_directory(destination.parent)
    host = _bound(destination, private=True)
    if host.size != record.size or host.sha256 != record.sha256:
        raise ContractError(f"artifact {fixed.token} published host copy changed")
    return {
        "token": fixed.token,
        "device_path": fixed.path,
        "device_sha256": record.sha256,
        "host_preservation": _bound_value(host),
        "peer": DEVICE_NCM_ADDRESS,
        "sparse_raw_regular_file": True,
        "receipt_marker_present": "status=ok" in receipt_text or "[exit 0]" in receipt_text,
    }


def _rebind_host_ncm() -> dict[str, Any]:
    d1_manifest = PRIVATE_BASE / h5.D1_RUN_ID / "manifest.json"
    d1_spec = h5.resident.load_spec(d1_manifest, h5.D1_MANIFEST_SHA256)
    f1_spec = h5.auto._f1_spec(d1_spec)  # noqa: SLF001 - exact H5 projection
    args = h5.auto._effect_args()  # noqa: SLF001 - reviewed host adapter
    result = h5.auto.base.rebind_host_ncm_after_reenumeration(f1_spec, args)
    ready = result.get("ready")
    if (
        result.get("same_current_acm_usb_parent") is not True
        or result.get("exact_interface_count") != 1
        or result.get("profile_bound") is not True
        or not isinstance(ready, dict)
        or ready.get("verified_a90_ncm") is not True
        or ready.get("direct_route") is not True
        or ready.get("host_cidr_present") is not True
        or ready.get("device_ping") is not True
    ):
        raise ContractError("exact A90 NCM host preservation route is unavailable")
    return result


def preserve_missing(
    run_id: str,
    inventory_path: Path,
    inventory_sha256: str,
) -> dict[str, Any]:
    _require_not_expired()
    _require_unconsumed()
    inventory, value = _load_inventory(inventory_path, inventory_sha256)
    if value.get("run_id") != run_id:
        raise ContractError("preservation and inventory run IDs differ")
    age = int(time.time()) - value["captured_epoch_sec"]
    if age < -5 or age > MAX_INVENTORY_AGE_SEC:
        raise ContractError("preservation inventory is stale")
    realpath, bridge = _target()
    if (
        realpath != value["target"]["bridge_realpath"]
        or bridge != value["target"]["bridge_process"]
    ):
        raise ContractError("preservation target or bridge changed")
    h5._health()  # noqa: SLF001
    host_ncm_rebind = _rebind_host_ncm()
    records = tuple(
        _parse_record(item, fixed)
        for item, fixed in zip(value["selected"], SELECTED_FIXED, strict=True)
    )
    parent = (PRIVATE_BASE / run_id / "host-preserved").resolve()
    if parent.exists() and (parent.is_symlink() or not parent.is_dir()):
        raise ContractError("host preservation parent is not one directory")
    parent.mkdir(mode=0o700, exist_ok=True)
    os.chmod(parent, 0o700)
    receipts: list[dict[str, Any]] = []
    for fixed, record in zip(SELECTED_FIXED, records, strict=True):
        if fixed.token not in MISSING_HOST_TOKENS:
            continue
        destination = _preserved_path(run_id, fixed)
        if destination.exists() and not destination.is_symlink():
            host = _bound(destination, private=True)
            if host.size != record.size or host.sha256 != record.sha256:
                raise ContractError(f"artifact {fixed.token} existing preservation changed")
            receipts.append(
                {
                    "token": fixed.token,
                    "device_path": fixed.path,
                    "device_sha256": record.sha256,
                    "host_preservation": _bound_value(host),
                    "peer": DEVICE_NCM_ADDRESS,
                    "sparse_raw_regular_file": True,
                    "receipt_marker_present": True,
                }
            )
            continue
        print(f"preserve {fixed.token}/20", file=sys.stderr, flush=True)
        receipts.append(
            _receive_sparse_preservation(fixed, record, destination)
        )
    h5._health()  # noqa: SLF001
    _require_not_expired()
    _require_unconsumed()
    all_preserved = _all_host_preservation(run_id, records)
    _require_not_expired()
    _require_unconsumed()
    output = (PRIVATE_BASE / run_id / "host-preservation.json").resolve()
    if output.exists():
        raise ContractError("host preservation receipt already exists")
    result = {
        "schema": "a90_h5_historical_image_host_preservation_v1",
        "created_utc": legacy.utc_now(),
        "run_id": run_id,
        "inventory": _bound_value(inventory),
        "preserved_count": len(all_preserved),
        "newly_required_count": len(MISSING_HOST_TOKENS),
        "receipts": receipts,
        "all_host_preservation": {
            token: _bound_value(bound)
            for token, bound in sorted(all_preserved.items())
        },
        "host_ncm_rebind": host_ncm_rebind,
        "device_read_only": True,
        "device_write": False,
        "other_target_commands": 0,
    }
    legacy.write_private_json_exclusive(output, result)
    return result


def _load_host_preservation_receipt(
    run_id: str,
    inventory: legacy.BoundFile,
    preserved: dict[str, legacy.BoundFile],
) -> legacy.BoundFile:
    bound = _bound(
        PRIVATE_BASE / run_id / "host-preservation.json",
        private=True,
    )
    value = json.loads(bound.path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != {
        "schema", "created_utc", "run_id", "inventory", "preserved_count",
        "newly_required_count", "receipts", "all_host_preservation",
        "host_ncm_rebind",
        "device_read_only", "device_write", "other_target_commands",
    }:
        raise ContractError("host preservation receipt shape changed")
    receipts = value.get("receipts")
    expected_all = {
        token: _bound_value(item) for token, item in sorted(preserved.items())
    }
    if (
        value.get("schema")
        != "a90_h5_historical_image_host_preservation_v1"
        or value.get("run_id") != run_id
        or value.get("inventory") != _bound_value(inventory)
        or type(value.get("preserved_count")) is not int
        or value.get("preserved_count") != len(SELECTED_FIXED)
        or type(value.get("newly_required_count")) is not int
        or value.get("newly_required_count") != len(MISSING_HOST_TOKENS)
        or not isinstance(receipts, list)
        or len(receipts) != len(MISSING_HOST_TOKENS)
        or value.get("all_host_preservation") != expected_all
        or not isinstance(value.get("host_ncm_rebind"), dict)
        or value["host_ncm_rebind"].get("same_current_acm_usb_parent") is not True
        or value["host_ncm_rebind"].get("exact_interface_count") != 1
        or value["host_ncm_rebind"].get("profile_bound") is not True
        or not isinstance(value["host_ncm_rebind"].get("ready"), dict)
        or value["host_ncm_rebind"]["ready"].get("verified_a90_ncm") is not True
        or value["host_ncm_rebind"]["ready"].get("direct_route") is not True
        or value["host_ncm_rebind"]["ready"].get("host_cidr_present") is not True
        or value["host_ncm_rebind"]["ready"].get("device_ping") is not True
        or value.get("device_read_only") is not True
        or value.get("device_write") is not False
        or type(value.get("other_target_commands")) is not int
        or value.get("other_target_commands") != 0
    ):
        raise ContractError("host preservation receipt binding changed")
    seen: set[str] = set()
    for receipt in receipts:
        if not isinstance(receipt, dict) or set(receipt) != {
            "token", "device_path", "device_sha256", "host_preservation",
            "peer", "sparse_raw_regular_file", "receipt_marker_present",
        }:
            raise ContractError("host preservation item shape changed")
        token = receipt.get("token")
        fixed = next((item for item in SELECTED_FIXED if item.token == token), None)
        if (
            fixed is None
            or token not in MISSING_HOST_TOKENS
            or token in seen
            or receipt.get("device_path") != fixed.path
            or receipt.get("device_sha256") != preserved[token].sha256
            or receipt.get("host_preservation") != _bound_value(preserved[token])
            or receipt.get("peer") != DEVICE_NCM_ADDRESS
            or receipt.get("sparse_raw_regular_file") is not True
            or receipt.get("receipt_marker_present") is not True
        ):
            raise ContractError("host preservation item binding changed")
        seen.add(token)
    if seen != set(MISSING_HOST_TOKENS):
        raise ContractError("host preservation item set changed")
    return bound


def capture_inventory(run_id: str, output: Path) -> dict[str, Any]:
    _require_not_expired()
    _require_unconsumed()
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise ContractError("historical GC run_id is not exact")
    expected = (PRIVATE_BASE / run_id / "inventory.json").resolve()
    if output.resolve() != expected or output.exists() or output.parent.exists():
        raise ContractError("inventory output is not a new exact private run path")
    h5._historical_evidence()  # noqa: SLF001 - exact H5 recovery provenance
    realpath, bridge = _target()
    health = h5._health()  # noqa: SLF001 - exact H5 plus latched state
    selected: list[ArtifactRecord] = []
    for fixed in SELECTED_FIXED:
        print(f"inventory {fixed.token}/20", file=sys.stderr, flush=True)
        selected.append(_read_artifact(fixed, hash_bytes=True))
    protected = _read_artifact(_protected_fixed(), hash_bytes=True)
    if protected.sha256 != PROTECTED_SHA256:
        raise ContractError("installed H5 source SHA256 changed")
    identities = {(item.st_dev, item.st_ino) for item in (*selected, protected)}
    if len(identities) != len(selected) + 1:
        raise ContractError("selected/protected inode identities overlap")
    filesystem = _stage_and_work_absent()
    _require_not_expired()
    _require_unconsumed()
    output.parent.mkdir(mode=0o700, parents=False, exist_ok=False)
    value = {
        "schema": INVENTORY_SCHEMA,
        "created_utc": legacy.utc_now(),
        "captured_epoch_sec": int(time.time()),
        "run_id": run_id,
        "target": {
            "bridge_realpath": realpath,
            "usb_serial_sha256": gc.USB_SERIAL_SHA256,
            "bridge_process": bridge,
        },
        "health": health,
        "selected": [_record_value(item) for item in selected],
        "protected": _record_value(protected),
        "work_absent": True,
        "stage_absent": True,
        "filesystem_kib": filesystem,
        "device_contact": True,
        "device_write": False,
        "other_target_commands": 0,
    }
    legacy.write_private_json_exclusive(output, value)
    return value


def _parse_record(value: Any, fixed: FixedArtifact) -> ArtifactRecord:
    if not isinstance(value, dict) or set(value) != set(_record_value(ArtifactRecord("", "", 0, 0, "", 0, 0, 0, ""))):
        raise ContractError(f"artifact {fixed.token} record shape changed")
    record = ArtifactRecord(
        token=value.get("token"), path=value.get("path"), size=value.get("size"),
        blocks=value.get("blocks"), mode=value.get("mode"), nlink=value.get("nlink"),
        st_dev=value.get("st_dev"), st_ino=value.get("st_ino"), sha256=value.get("sha256"),
    )
    if (
        record.token != fixed.token or record.path != fixed.path
        or record.size != fixed.size or record.mode != fixed.mode or record.nlink != 1
        or type(record.blocks) is not int or record.blocks <= 0
        or type(record.st_dev) is not int or record.st_dev <= 0
        or type(record.st_ino) is not int or record.st_ino <= 0
        or not isinstance(record.sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", record.sha256) is None
    ):
        raise ContractError(f"artifact {fixed.token} record identity changed")
    return record


def _load_inventory(path: Path, expected_sha256: str) -> tuple[legacy.BoundFile, dict[str, Any]]:
    bound = _bound(path, private=True)
    if bound.sha256 != expected_sha256:
        raise ContractError("inventory SHA256 changed")
    value = json.loads(bound.path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != {
        "schema", "created_utc", "captured_epoch_sec", "run_id", "target", "health",
        "selected", "protected", "work_absent", "stage_absent", "filesystem_kib",
        "device_contact", "device_write", "other_target_commands",
    }:
        raise ContractError("inventory shape changed")
    if (
        value.get("schema") != INVENTORY_SCHEMA
        or RUN_ID_RE.fullmatch(str(value.get("run_id") or "")) is None
        or type(value.get("captured_epoch_sec")) is not int
        or value["captured_epoch_sec"] <= 0
        or value.get("work_absent") is not True
        or value.get("stage_absent") is not True
        or value.get("device_contact") is not True
        or value.get("device_write") is not False
        or value.get("other_target_commands") != 0
    ):
        raise ContractError("inventory authority or state changed")
    selected = value.get("selected")
    if not isinstance(selected, list) or len(selected) != len(SELECTED_FIXED):
        raise ContractError("inventory selected set changed")
    records = tuple(_parse_record(item, fixed) for item, fixed in zip(selected, SELECTED_FIXED, strict=True))
    protected = _parse_record(value.get("protected"), _protected_fixed())
    if protected.sha256 != PROTECTED_SHA256:
        raise ContractError("inventory protected H5 SHA256 changed")
    if len({(item.st_dev, item.st_ino) for item in (*records, protected)}) != len(records) + 1:
        raise ContractError("inventory inode identities overlap")
    target = value.get("target")
    filesystem = value.get("filesystem_kib")
    if (
        not isinstance(target, dict)
        or set(target) != {"bridge_realpath", "usb_serial_sha256", "bridge_process"}
        or target.get("usb_serial_sha256") != gc.USB_SERIAL_SHA256
        or not isinstance(target.get("bridge_realpath"), str)
        or not isinstance(filesystem, dict)
        or set(filesystem) != {"blocks", "used", "available"}
        or any(type(filesystem.get(key)) is not int or filesystem[key] < 0 for key in filesystem)
        or filesystem.get("blocks", 0) <= 0
        or filesystem.get("used", 0) > filesystem.get("blocks", 0)
        or filesystem.get("available", 0) > filesystem.get("blocks", 0)
        or filesystem.get("used", 0) + filesystem.get("available", 0)
        > filesystem.get("blocks", 0)
    ):
        raise ContractError("inventory target or filesystem changed")
    h5._validate_inventory_health(value.get("health"))  # noqa: SLF001
    h5.engine._validated_bridge_process(target.get("bridge_process"))  # noqa: SLF001
    h5._validate_inventory_target_health(value["health"], target)  # noqa: SLF001
    return bound, value


def build_manifest(run_id: str, inventory_path: Path, inventory_sha256: str, output: Path) -> dict[str, Any]:
    _require_not_expired()
    _require_unconsumed()
    inventory, value = _load_inventory(inventory_path, inventory_sha256)
    if value.get("run_id") != run_id:
        raise ContractError("manifest and inventory run IDs differ")
    expected = (PRIVATE_BASE / run_id / "manifest.json").resolve()
    if output.resolve() != expected or output.exists():
        raise ContractError("manifest output path changed")
    evidence, rollback = h5._historical_evidence()  # noqa: SLF001
    closure = {role: _bound(path, private=False) for role, path in _source_paths().items()}
    records = tuple(
        _parse_record(item, fixed)
        for item, fixed in zip(value["selected"], SELECTED_FIXED, strict=True)
    )
    host_preservation = _all_host_preservation(run_id, records)
    host_preservation_receipt = _load_host_preservation_receipt(
        run_id,
        inventory,
        host_preservation,
    )
    selected = [
        {
            **item,
            "host_preservation": _bound_value(host_preservation[item["token"]]),
        }
        for item in value["selected"]
    ]
    manifest = {
        "schema": SCHEMA,
        "status": "ready-for-attended-h5-historical-image-gc",
        "created_utc": legacy.utc_now(),
        "run_id": run_id,
        "capability": CAPABILITY,
        "hazard": HAZARD,
        "inventory": _bound_value(inventory),
        "target": value["target"],
        "health": value["health"],
        "selected": selected,
        "protected": value["protected"],
        "host_preservation_receipt": _bound_value(host_preservation_receipt),
        "source_closure": {role: _bound_value(item) for role, item in sorted(closure.items())},
        "historical_evidence": {role: _bound_value(item) for role, item in sorted(evidence.items())},
        "rollback_boot": _bound_value(rollback),
        "recovery_profile": h5.RECOVERY_PROFILE,
        "capability_lifetime": {
            "dispatch_path": str(capability_dispatch_path()),
            "expires_utc": CAPABILITY_EXPIRES_UTC,
            "consumed_by_first_durable_dispatch": True,
        },
        "authority": {
            "risk_tier": "TIER_D1_ATTENDED_EXACT_STORAGE_ARTIFACT_CLEANUP",
            "operator_attended_required": True,
            "selected_count": len(SELECTED_FIXED),
            "host_preserved_count": len(host_preservation),
            "single_unlink_dispatch": True,
            "unlink_retry_forbidden": True,
            "restore_authority": False,
            "payload_transfer": False,
            "partition_write": False,
            "flash": False,
        },
    }
    _require_not_expired()
    _require_unconsumed()
    legacy.write_private_json_exclusive(output, manifest)
    return manifest


def load_spec(path: Path, expected_sha256: str) -> Spec:
    manifest = _bound(path, private=True)
    if manifest.sha256 != expected_sha256:
        raise ContractError("manifest SHA256 changed")
    value = json.loads(manifest.path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != {
        "schema", "status", "created_utc", "run_id", "capability", "hazard", "inventory",
        "target", "health", "selected", "protected", "source_closure",
        "host_preservation_receipt",
        "historical_evidence", "rollback_boot", "recovery_profile",
        "capability_lifetime", "authority",
    }:
        raise ContractError("manifest shape changed")
    run_id = value.get("run_id")
    if (
        value.get("schema") != SCHEMA
        or value.get("status") != "ready-for-attended-h5-historical-image-gc"
        or value.get("capability") != CAPABILITY
        or value.get("hazard") != HAZARD
        or value.get("recovery_profile") != h5.RECOVERY_PROFILE
        or not isinstance(run_id, str) or RUN_ID_RE.fullmatch(run_id) is None
        or manifest.path != (PRIVATE_BASE / run_id / "manifest.json").resolve()
    ):
        raise ContractError("manifest header changed")
    inventory_value = value.get("inventory")
    inventory = _load_bound(inventory_value, "inventory", private=True)
    inventory, loaded = _load_inventory(inventory.path, inventory.sha256)
    if loaded.get("run_id") != run_id or value.get("target") != loaded.get("target") or value.get("health") != loaded.get("health"):
        raise ContractError("manifest inventory projection changed")
    selected_values = value.get("selected")
    if not isinstance(selected_values, list) or len(selected_values) != len(SELECTED_FIXED):
        raise ContractError("manifest selected set changed")
    selected_projection = [
        {key: item[key] for key in item if key != "host_preservation"}
        if isinstance(item, dict)
        else item
        for item in selected_values
    ]
    if selected_projection != loaded.get("selected") or value.get("protected") != loaded.get("protected"):
        raise ContractError("manifest selected/protected set changed")
    selected = tuple(
        _parse_record(item, fixed)
        for item, fixed in zip(selected_projection, SELECTED_FIXED, strict=True)
    )
    protected = _parse_record(value["protected"], _protected_fixed())
    current_host_preservation = _all_host_preservation(run_id, selected)
    host_preservation: dict[str, legacy.BoundFile] = {}
    for item, record in zip(selected_values, selected, strict=True):
        if not isinstance(item, dict) or set(item) != set(_record_value(record)) | {"host_preservation"}:
            raise ContractError(f"artifact {record.token} host binding shape changed")
        host = _load_bound(
            item["host_preservation"],
            f"artifact {record.token} host preservation",
            private=True,
        )
        if host != current_host_preservation[record.token]:
            raise ContractError(f"artifact {record.token} host preservation changed")
        host_preservation[record.token] = host
    host_preservation_receipt = _load_host_preservation_receipt(
        run_id,
        inventory,
        host_preservation,
    )
    if value.get("host_preservation_receipt") != _bound_value(host_preservation_receipt):
        raise ContractError("manifest host preservation receipt changed")
    source_values = value.get("source_closure")
    source_paths = _source_paths()
    if not isinstance(source_values, dict) or set(source_values) != set(source_paths):
        raise ContractError("manifest source closure roles changed")
    closure = {role: _load_bound(source_values[role], role, private=False) for role in source_paths}
    if any(closure[role].path != source_paths[role] for role in source_paths):
        raise ContractError("manifest source closure paths changed")
    evidence, rollback = h5._historical_evidence()  # noqa: SLF001
    if value.get("historical_evidence") != {role: _bound_value(item) for role, item in sorted(evidence.items())}:
        raise ContractError("manifest H5 historical evidence changed")
    if value.get("rollback_boot") != _bound_value(rollback):
        raise ContractError("manifest rollback binding changed")
    lifetime = value.get("capability_lifetime")
    authority = value.get("authority")
    if lifetime != {
        "dispatch_path": str(capability_dispatch_path()),
        "expires_utc": CAPABILITY_EXPIRES_UTC,
        "consumed_by_first_durable_dispatch": True,
    } or authority != {
        "risk_tier": "TIER_D1_ATTENDED_EXACT_STORAGE_ARTIFACT_CLEANUP",
        "operator_attended_required": True,
        "selected_count": len(SELECTED_FIXED),
        "host_preserved_count": len(SELECTED_FIXED),
        "single_unlink_dispatch": True,
        "unlink_retry_forbidden": True,
        "restore_authority": False,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
    }:
        raise ContractError("manifest lifetime or authority changed")
    target = value["target"]
    return Spec(
        manifest_path=manifest.path,
        manifest_sha256=manifest.sha256,
        run_id=run_id,
        inventory=inventory,
        bridge_realpath=target["bridge_realpath"],
        bridge_process=h5.engine._validated_bridge_process(target["bridge_process"]),  # noqa: SLF001
        selected=selected,
        protected=protected,
        host_preservation=host_preservation,
        host_preservation_receipt=host_preservation_receipt,
        source_closure=closure,
        evidence=evidence,
        rollback=rollback,
        capability_dispatch_path=capability_dispatch_path(),
    )


def _revalidate_host(spec: Spec) -> None:
    for role, path in _source_paths().items():
        if _bound(path, private=False) != spec.source_closure[role]:
            raise ContractError(f"execution-critical closure changed: {role}")
    evidence, rollback = h5._historical_evidence()  # noqa: SLF001
    if evidence != spec.evidence or rollback != spec.rollback:
        raise ContractError("H5 evidence or rollback changed")
    for token, preserved in spec.host_preservation.items():
        if _bound(preserved.path, private=True) != preserved:
            raise ContractError(f"artifact {token} host preservation changed")
    if _bound(spec.host_preservation_receipt.path, private=True) != spec.host_preservation_receipt:
        raise ContractError("host preservation receipt changed")


def _inventory_age(spec: Spec) -> None:
    value = json.loads(spec.inventory.path.read_text(encoding="utf-8"))
    age = int(time.time()) - value["captured_epoch_sec"]
    if age < -5 or age > MAX_INVENTORY_AGE_SEC:
        raise ContractError("historical GC inventory is stale")


def _live_target(spec: Spec, *, allow_new_bridge: bool = False) -> dict[str, Any]:
    realpath, bridge = _target()
    if realpath != spec.bridge_realpath:
        raise ContractError("live A90 realpath changed")
    if bridge != spec.bridge_process and not allow_new_bridge:
        raise ContractError("live A90 bridge generation changed")
    return bridge


def _validate_health_for_target(health: Any, spec: Spec) -> dict[str, Any]:
    try:
        value = h5._validate_inventory_health(health)  # noqa: SLF001
        h5._validate_inventory_target_health(  # noqa: SLF001
            value,
            {"bridge_realpath": spec.bridge_realpath},
        )
    except Exception as exc:
        raise ContractError("H5 target-bound health changed") from exc
    return value


def _health_for_target(spec: Spec) -> dict[str, Any]:
    return _validate_health_for_target(h5._health(), spec)  # noqa: SLF001


def _as_gc_record(item: ArtifactRecord) -> gc.ImageRecord:
    return gc.ImageRecord(
        role=f"historical-{item.token}", device_path=item.path, size=item.size,
        blocks=item.blocks, mode=item.mode, nlink=item.nlink, st_dev=item.st_dev,
        st_ino=item.st_ino, sha256=item.sha256, host_preservation=None,
    )


def _preflight(spec: Spec) -> dict[str, int]:
    before = _stage_and_work_absent()
    for fixed, item in zip(SELECTED_FIXED, spec.selected, strict=True):
        _read_artifact(fixed, hash_bytes=True, expected=item)
    protected = _read_artifact(_protected_fixed(), hash_bytes=True)
    if protected != spec.protected:
        raise ContractError("protected H5 source changed before dispatch")
    for index, item in enumerate(spec.selected):
        tag = f"selected-{index}"
        for kind, script in zip(
            ("MOUNT", "FD", "LOOP", "ROOT"),
            gc._selected_use_guard_scripts(_as_gc_record(item), tag),  # noqa: SLF001
            strict=True,
        ):
            text = gc._run_script(script, READ_TIMEOUT_SEC, f"{tag} {kind.lower()} guard")  # noqa: SLF001
            if text.count(f"A90CLEAN_USE_{kind} tag={tag} exact=1") != 1:
                raise ContractError(f"{tag} {kind.lower()} guard is not exact")
    return before


def _selector_path(token: str) -> str:
    matches = [item.path for item in SELECTED_FIXED if item.token == token]
    if len(matches) != 1:
        raise ContractError("historical GC selector is not exact")
    return matches[0]


def _effect_script() -> str:
    return "\n".join(
        (
            "set -eu",
            "D=$1; X=$2; shift 2",
            '[ ! -e "' + WORK_PATH + '" ] && [ ! -L "' + WORK_PATH + '" ]',
            'while [ -n "$X" ]; do case "$X" in *,*) R=${X%%,*};X=${X#*,};;*) R=$X;X=;;esac',
            'K=${R%%:*};I=${R#*:}; case "$K" in '
            '01|02)B=a90-wsta98-packet-filter-rootfs.img;[ "$K" = 01 ]||B=$B.clean;Z=2147483648;M=755;;'
            '03|04)B=debian-bookworm-arm64-20260701-024412.img;[ "$K" = 03 ]||B=$B.clean;Z=2147483648;M=755;;'
            '05)B=debian-bookworm-arm64-d3-sysvinit-keyed.img;Z=2147483648;M=755;;'
            '18)B=wsta16-immediate-snapshot.img;Z=1610612736;M=755;;'
            '19)B=wsta17-handoff-materialization.img;Z=1610612736;M=755;;'
            '20)B=wsta18-control-plane.img;Z=1610612736;M=755;;'
            '*)case "$K" in 06)S=20260801-03;;07)S=20260801-06;;08)S=20260801-09;;'
            '09)S=20260801-10;;10)S=20260802-01;;11)S=20260803-02;;12)S=20260803-03;;'
            '13)S=20260803-04;;14)S=20260804-02;;15)S=20260805-02;;16)S=20260805-03;;'
            '17)S=20260805-09;;*)exit 66;;esac;'
            'B=debian-bookworm-arm64-phase2-display-v3406-keyed-$S.img;Z=2147483648;M=600;;esac',
            'P="' + RUNTIME_DIR + '/$B"; [ ! -L "$P" ]; [ -f "$P" ]',
            '[ "$(/bin/busybox stat -c "%s|%a|%h|%d|%i" "$P")" = "$Z|$M|1|$D|$I" ]',
            'set -- "$@" "$P"; done',
            f'[ "$#" -eq {len(SELECTED_FIXED)} ]',
            '/bin/busybox rm -- "$@"',
            '/bin/busybox sync',
            'for P do [ ! -e "$P" ] && [ ! -L "$P" ]; done',
            'echo "A90HIST_UNLINKED exact=1 selected_absent=$#"',
        )
    )


def _effect_args(spec: Spec) -> tuple[str, str]:
    devices = {item.st_dev for item in spec.selected}
    if len(devices) != 1:
        raise ContractError("selected historical images span filesystems")
    selectors = ",".join(f"{item.token}:{item.st_ino}" for item in spec.selected)
    if any(_selector_path(item.token) != item.path for item in spec.selected):
        raise ContractError("historical GC selector round-trip changed")
    return str(next(iter(devices))), selectors


def effect_command(spec: Spec) -> list[str]:
    command = gc._script_command(_effect_script(), _effect_args(spec))  # noqa: SLF001
    gc._require_bounded_command(command, "historical image GC effect")  # noqa: SLF001
    return command


def _reconcile(spec: Spec) -> dict[str, Any]:
    script = "\n".join(
        (
            "set -eu",
            "P=$1; T=$2",
            '[ ! -e "$P" ] && [ ! -L "$P" ]',
            'echo "A90HIST_ABSENT|$T"',
        )
    )
    for item in spec.selected:
        text = gc._run_script(  # noqa: SLF001
            script,
            READ_TIMEOUT_SEC,
            f"historical GC absence reconciliation {item.token}",
            args=(item.path, item.token),
        )
        if text.count(f"A90HIST_ABSENT|{item.token}") != 1:
            raise ContractError(
                f"selected absence reconciliation {item.token} is not exact"
            )
    protected = _read_artifact(_protected_fixed(), hash_bytes=True)
    if protected != spec.protected:
        raise ContractError("protected H5 source changed after dispatch")
    filesystem = _stage_and_work_absent()
    return {
        "selected_absent_count": len(spec.selected),
        "protected_exact": True,
        "work_absent": True,
        "stage_absent": True,
        "filesystem_kib": filesystem,
    }


def _free_gain_bounds(spec: Spec) -> tuple[int, int]:
    allocated_kib = sum(item.blocks for item in spec.selected) // 2
    return max(1, allocated_kib - FREE_GAIN_TOLERANCE_KIB), allocated_kib + FREE_GAIN_TOLERANCE_KIB


def _validate_filesystem(value: Any, label: str) -> dict[str, int]:
    if (
        not isinstance(value, dict)
        or set(value) != {"blocks", "used", "available"}
        or any(type(value.get(key)) is not int for key in value)
        or value["blocks"] <= 0
        or value["used"] < 0
        or value["available"] < 0
        or value["used"] > value["blocks"]
        or value["available"] > value["blocks"]
        or value["used"] + value["available"] > value["blocks"]
    ):
        raise ContractError(f"{label} filesystem state changed")
    return value


def _validate_intent(value: Any, spec: Spec) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "schema", "created_utc", "run_id", "manifest_sha256", "target",
        "before_health", "before_filesystem_kib", "selected", "protected",
        "rollback_sha256", "unlink_dispatch_count_max", "unlink_retry_forbidden",
    }:
        raise ContractError("historical GC intent shape changed")
    expected_target = {
        "bridge_realpath": spec.bridge_realpath,
        "bridge_process": spec.bridge_process,
    }
    if (
        value.get("schema") != INTENT_SCHEMA
        or value.get("run_id") != spec.run_id
        or value.get("manifest_sha256") != spec.manifest_sha256
        or value.get("target") != expected_target
        or value.get("selected") != [_record_value(item) for item in spec.selected]
        or value.get("protected") != _record_value(spec.protected)
        or value.get("rollback_sha256") != spec.rollback.sha256
        or type(value.get("unlink_dispatch_count_max")) is not int
        or value.get("unlink_dispatch_count_max") != 1
        or value.get("unlink_retry_forbidden") is not True
        or not isinstance(value.get("created_utc"), str)
    ):
        raise ContractError("historical GC intent binding changed")
    _validate_health_for_target(value.get("before_health"), spec)
    _validate_filesystem(value.get("before_filesystem_kib"), "intent opening")
    return value


def _validate_dispatch(
    value: Any,
    spec: Spec,
    intent_sha256: str,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "schema", "created_utc", "run_id", "manifest_sha256", "intent_sha256",
        "selected_tokens", "protected_sha256", "cleanup_command_sha256",
        "dispatch_authorization_count", "unlink_dispatch_count_max",
        "retry_forbidden", "capability_consumed",
    }:
        raise ContractError("historical GC dispatch shape changed")
    if (
        value.get("schema") != DISPATCH_SCHEMA
        or value.get("run_id") != spec.run_id
        or value.get("manifest_sha256") != spec.manifest_sha256
        or value.get("intent_sha256") != intent_sha256
        or value.get("selected_tokens") != [item.token for item in spec.selected]
        or value.get("protected_sha256") != spec.protected.sha256
        or value.get("cleanup_command_sha256")
        != legacy.json_sha256({"argv": effect_command(spec)})
        or type(value.get("dispatch_authorization_count")) is not int
        or value.get("dispatch_authorization_count") != 1
        or type(value.get("unlink_dispatch_count_max")) is not int
        or value.get("unlink_dispatch_count_max") != 1
        or value.get("retry_forbidden") is not True
        or value.get("capability_consumed") is not True
        or not isinstance(value.get("created_utc"), str)
    ):
        raise ContractError("historical GC dispatch binding changed")
    return value


def _validate_effect_not_started(
    value: Any,
    spec: Spec,
    dispatch_sha256: str,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "schema", "created_utc", "run_id", "manifest_sha256",
        "dispatch_sha256", "reason", "dispatch_count", "device_write",
        "capability_consumed",
    }:
        raise ContractError("effect-not-started shape changed")
    if (
        value.get("schema") != EFFECT_NOT_STARTED_SCHEMA
        or value.get("run_id") != spec.run_id
        or value.get("manifest_sha256") != spec.manifest_sha256
        or value.get("dispatch_sha256") != dispatch_sha256
        or value.get("reason") != "capability-expired-before-unlink"
        or type(value.get("dispatch_count")) is not int
        or value.get("dispatch_count") != 0
        or value.get("device_write") is not False
        or value.get("capability_consumed") is not True
        or not isinstance(value.get("created_utc"), str)
    ):
        raise ContractError("effect-not-started binding changed")
    return value


RESULT_KEYS = {
    "schema", "created_utc", "run_id", "manifest_sha256", "intent_sha256",
    "dispatch_sha256", "outcome", "dispatch_count", "cleanup_retransmitted",
    "response_proven", "dispatch_error", "reconciliation",
    "reconciliation_error", "final_health", "final_health_error",
    "before_filesystem_kib", "free_gain_kib", "free_gain_bounds_kib",
    "resumed_from_durable_dispatch", "device_write", "payload_transfer",
    "partition_write", "flash", "rollback_transfer_count",
    "other_target_commands",
}


def _result(
    spec: Spec,
    before: dict[str, int],
    response_proven: bool,
    dispatch_error: dict[str, str] | None,
    intent_sha256: str,
    dispatch_sha256: str,
    *,
    resumed: bool,
) -> dict[str, Any]:
    reconciliation_error = None
    try:
        reconciliation = _reconcile(spec)
    except Exception as exc:  # noqa: BLE001 - read-only after durable dispatch
        reconciliation = {"selected_absent_count": None, "protected_exact": False}
        reconciliation_error = {"type": type(exc).__name__, "message": str(exc)}
    health_error = None
    try:
        health = _health_for_target(spec)
    except Exception as exc:  # noqa: BLE001 - never causes another unlink
        health = {"proven": False}
        health_error = {"type": type(exc).__name__, "message": str(exc)}
    after = reconciliation.get("filesystem_kib")
    gain = after["available"] - before["available"] if isinstance(after, dict) else None
    bounds = _free_gain_bounds(spec)
    complete = (
        reconciliation.get("selected_absent_count") == len(spec.selected)
        and reconciliation.get("protected_exact") is True
        and reconciliation.get("work_absent") is True
        and reconciliation.get("stage_absent") is True
        and health.get("proven") is True
        and gain is not None and bounds[0] <= gain <= bounds[1]
    )
    outcome = (PASS_OUTCOME if response_proven else PASS_AMBIGUOUS_OUTCOME) if complete else "RECOVERY_PENDING_PARKED_NO_RETRY"
    return {
        "schema": RESULT_SCHEMA,
        "created_utc": legacy.utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "intent_sha256": intent_sha256,
        "dispatch_sha256": dispatch_sha256,
        "outcome": outcome,
        "dispatch_count": 1,
        "cleanup_retransmitted": False,
        "response_proven": response_proven,
        "dispatch_error": dispatch_error,
        "reconciliation": reconciliation,
        "reconciliation_error": reconciliation_error,
        "final_health": health,
        "final_health_error": health_error,
        "before_filesystem_kib": before,
        "free_gain_kib": gain,
        "free_gain_bounds_kib": list(bounds),
        "resumed_from_durable_dispatch": resumed,
        "device_write": True,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
        "rollback_transfer_count": 0,
        "other_target_commands": 0,
    }


def _expired_result(
    spec: Spec,
    before: dict[str, int],
    intent_sha256: str,
    dispatch_sha256: str,
    error: dict[str, str],
    *,
    resumed: bool,
) -> dict[str, Any]:
    health_error = None
    try:
        health = _health_for_target(spec)
    except Exception as exc:  # noqa: BLE001 - read-only terminal observation
        health = {"proven": False}
        health_error = {"type": type(exc).__name__, "message": str(exc)}
    return {
        "schema": RESULT_SCHEMA,
        "created_utc": legacy.utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "intent_sha256": intent_sha256,
        "dispatch_sha256": dispatch_sha256,
        "outcome": "CAPABILITY_CONSUMED_EXPIRED_BEFORE_UNLINK",
        "dispatch_count": 0,
        "cleanup_retransmitted": False,
        "response_proven": False,
        "dispatch_error": error,
        "reconciliation": None,
        "reconciliation_error": None,
        "final_health": health,
        "final_health_error": health_error,
        "before_filesystem_kib": before,
        "free_gain_kib": None,
        "free_gain_bounds_kib": [0, 0],
        "resumed_from_durable_dispatch": resumed,
        "device_write": False,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
        "rollback_transfer_count": 0,
        "other_target_commands": 0,
    }


def _validate_result(
    value: Any,
    spec: Spec,
    intent_sha256: str,
    dispatch_sha256: str,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != RESULT_KEYS:
        raise ContractError("historical GC result shape changed")
    common = (
        value.get("schema") == RESULT_SCHEMA
        and value.get("run_id") == spec.run_id
        and value.get("manifest_sha256") == spec.manifest_sha256
        and value.get("intent_sha256") == intent_sha256
        and value.get("dispatch_sha256") == dispatch_sha256
        and value.get("cleanup_retransmitted") is False
        and value.get("payload_transfer") is False
        and value.get("partition_write") is False
        and value.get("flash") is False
        and type(value.get("rollback_transfer_count")) is int
        and value.get("rollback_transfer_count") == 0
        and type(value.get("other_target_commands")) is int
        and value.get("other_target_commands") == 0
        and isinstance(value.get("created_utc"), str)
        and type(value.get("resumed_from_durable_dispatch")) is bool
    )
    if not common:
        raise ContractError("historical GC result common binding changed")
    before = _validate_filesystem(value.get("before_filesystem_kib"), "result opening")
    outcome = value.get("outcome")
    final_health = value.get("final_health")
    if isinstance(final_health, dict) and final_health.get("proven") is True:
        _validate_health_for_target(final_health, spec)
    if outcome == "CAPABILITY_CONSUMED_EXPIRED_BEFORE_UNLINK":
        if (
            type(value.get("dispatch_count")) is not int
            or value.get("dispatch_count") != 0
            or value.get("device_write") is not False
            or value.get("response_proven") is not False
            or value.get("reconciliation") is not None
            or value.get("free_gain_kib") is not None
            or value.get("free_gain_bounds_kib") != [0, 0]
        ):
            raise ContractError("expired-before-unlink result changed")
        return value
    if outcome not in {
        PASS_OUTCOME,
        PASS_AMBIGUOUS_OUTCOME,
        "RECOVERY_PENDING_PARKED_NO_RETRY",
    }:
        raise ContractError("historical GC result outcome changed")
    if (
        type(value.get("dispatch_count")) is not int
        or value.get("dispatch_count") != 1
        or value.get("device_write") is not True
        or type(value.get("response_proven")) is not bool
        or not isinstance(value.get("reconciliation"), dict)
        or not isinstance(value.get("free_gain_bounds_kib"), list)
        or value.get("free_gain_bounds_kib") != list(_free_gain_bounds(spec))
    ):
        raise ContractError("historical GC live result binding changed")
    reconciliation = value["reconciliation"]
    after = reconciliation.get("filesystem_kib")
    gain = (
        _validate_filesystem(after, "result final")["available"] - before["available"]
        if isinstance(after, dict)
        else None
    )
    if value.get("free_gain_kib") != gain:
        raise ContractError("historical GC result free gain changed")
    complete = (
        reconciliation.get("selected_absent_count") == len(spec.selected)
        and reconciliation.get("protected_exact") is True
        and reconciliation.get("work_absent") is True
        and reconciliation.get("stage_absent") is True
        and isinstance(final_health, dict)
        and final_health.get("proven") is True
        and value.get("reconciliation_error") is None
        and value.get("final_health_error") is None
        and gain is not None
        and _free_gain_bounds(spec)[0] <= gain <= _free_gain_bounds(spec)[1]
    )
    if outcome == PASS_OUTCOME and (not complete or value.get("response_proven") is not True):
        raise ContractError("exact-response PASS result changed")
    if outcome == PASS_OUTCOME and value.get("dispatch_error") is not None:
        raise ContractError("exact-response PASS retains a dispatch error")
    if outcome == PASS_AMBIGUOUS_OUTCOME and (not complete or value.get("response_proven") is not False):
        raise ContractError("ambiguous-response PASS result changed")
    if outcome == "RECOVERY_PENDING_PARKED_NO_RETRY" and complete:
        raise ContractError("parked result falsely contains complete PASS facts")
    return value


def execute(spec: Spec, transaction_dir: Path, operator_attended: bool) -> dict[str, Any]:
    if operator_attended is not True:
        raise ContractError("historical image GC is attended-only")
    _require_not_expired()
    _require_unconsumed()
    expected = (PRIVATE_BASE / spec.run_id / "live").resolve()
    if transaction_dir.resolve() != expected or transaction_dir.exists():
        raise ContractError("historical GC live directory is not new and exact")
    _revalidate_host(spec)
    _inventory_age(spec)
    _live_target(spec)
    _health_for_target(spec)
    before = _preflight(spec)
    _require_not_expired()
    bridge = _live_target(spec)
    before_health = _health_for_target(spec)
    command = effect_command(spec)
    _require_not_expired()
    transaction_dir.mkdir(mode=0o700)
    intent_path = transaction_dir / "intent.json"
    legacy.write_private_json_exclusive(
        intent_path,
        {
            "schema": INTENT_SCHEMA,
            "created_utc": legacy.utc_now(),
            "run_id": spec.run_id,
            "manifest_sha256": spec.manifest_sha256,
            "target": {"bridge_realpath": spec.bridge_realpath, "bridge_process": bridge},
            "before_health": before_health,
            "before_filesystem_kib": before,
            "selected": [_record_value(item) for item in spec.selected],
            "protected": _record_value(spec.protected),
            "rollback_sha256": spec.rollback.sha256,
            "unlink_dispatch_count_max": 1,
            "unlink_retry_forbidden": True,
        },
    )
    intent = _bound(intent_path, private=True)
    _require_not_expired()
    _require_unconsumed()
    dispatch = {
        "schema": DISPATCH_SCHEMA,
        "created_utc": legacy.utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "intent_sha256": intent.sha256,
        "selected_tokens": [item.token for item in spec.selected],
        "protected_sha256": spec.protected.sha256,
        "cleanup_command_sha256": legacy.json_sha256({"argv": command}),
        "dispatch_authorization_count": 1,
        "unlink_dispatch_count_max": 1,
        "retry_forbidden": True,
        "capability_consumed": True,
    }
    spec.capability_dispatch_path.parent.mkdir(mode=0o700, parents=False, exist_ok=False)
    legacy.write_private_json_exclusive(spec.capability_dispatch_path, dispatch)
    dispatch_path = transaction_dir / "dispatch-started.json"
    legacy.write_private_json_exclusive(dispatch_path, dispatch)
    capability_dispatch = _bound(spec.capability_dispatch_path, private=True)
    local_dispatch = _bound(dispatch_path, private=True)
    if (
        capability_dispatch.size != local_dispatch.size
        or capability_dispatch.sha256 != local_dispatch.sha256
    ):
        raise ContractError("capability and local dispatch receipts differ")
    try:
        _require_not_expired()
    except ContractError as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        legacy.write_private_json_exclusive(
            transaction_dir / "effect-not-started.json",
            {
                "schema": EFFECT_NOT_STARTED_SCHEMA,
                "created_utc": legacy.utc_now(),
                "run_id": spec.run_id,
                "manifest_sha256": spec.manifest_sha256,
                "dispatch_sha256": local_dispatch.sha256,
                "reason": "capability-expired-before-unlink",
                "dispatch_count": 0,
                "device_write": False,
                "capability_consumed": True,
            },
        )
        result = _expired_result(
            spec,
            before,
            intent.sha256,
            local_dispatch.sha256,
            error,
            resumed=False,
        )
        legacy.write_private_json_exclusive(transaction_dir / "result.json", result)
        return result
    response_proven = False
    dispatch_error = None
    try:
        text = gc._run_script(  # noqa: SLF001
            _effect_script(), EFFECT_TIMEOUT_SEC, "H5 historical image GC unlink",
            args=_effect_args(spec),
        )
        response_proven = text.count(
            f"A90HIST_UNLINKED exact=1 selected_absent={len(spec.selected)}"
        ) == 1
        if not response_proven:
            dispatch_error = {"type": "ContractError", "message": "unlink marker is not exact"}
    except Exception as exc:  # noqa: BLE001 - unlink is never retransmitted
        dispatch_error = {"type": type(exc).__name__, "message": str(exc)}
    result = _result(
        spec,
        before,
        response_proven,
        dispatch_error,
        intent.sha256,
        local_dispatch.sha256,
        resumed=False,
    )
    legacy.write_private_json_exclusive(transaction_dir / "result.json", result)
    return result


def resume(spec: Spec, transaction_dir: Path) -> dict[str, Any]:
    expected = (PRIVATE_BASE / spec.run_id / "live").resolve()
    if transaction_dir.resolve() != expected or not transaction_dir.is_dir():
        raise ContractError("historical GC resume path changed")
    intent_bound = _bound(transaction_dir / "intent.json", private=True)
    dispatch_bound = _bound(transaction_dir / "dispatch-started.json", private=True)
    capability_bound = _bound(spec.capability_dispatch_path, private=True)
    intent = _validate_intent(
        json.loads(intent_bound.path.read_text(encoding="utf-8")), spec
    )
    dispatch = _validate_dispatch(
        json.loads(dispatch_bound.path.read_text(encoding="utf-8")),
        spec,
        intent_bound.sha256,
    )
    capability = _validate_dispatch(
        json.loads(capability_bound.path.read_text(encoding="utf-8")),
        spec,
        intent_bound.sha256,
    )
    if (
        dispatch != capability
        or dispatch_bound.sha256 != capability_bound.sha256
    ):
        raise ContractError("durable historical GC dispatch receipts differ")
    result_path = transaction_dir / "result.json"
    existing_result = (
        json.loads(_bound(result_path, private=True).path.read_text(encoding="utf-8"))
        if result_path.exists()
        else None
    )
    effect_not_started_path = transaction_dir / "effect-not-started.json"
    if effect_not_started_path.exists():
        marker_bound = _bound(effect_not_started_path, private=True)
        _validate_effect_not_started(
            json.loads(marker_bound.path.read_text(encoding="utf-8")),
            spec,
            dispatch_bound.sha256,
        )
        if existing_result is not None:
            value = _validate_result(
                existing_result,
                spec,
                intent_bound.sha256,
                dispatch_bound.sha256,
            )
            if value.get("outcome") != "CAPABILITY_CONSUMED_EXPIRED_BEFORE_UNLINK":
                raise ContractError("effect-not-started result outcome changed")
            return value
        result = _expired_result(
            spec,
            intent["before_filesystem_kib"],
            intent_bound.sha256,
            dispatch_bound.sha256,
            {"type": "ContractError", "message": "capability expired before unlink"},
            resumed=True,
        )
        legacy.write_private_json_exclusive(result_path, result)
        return result
    if existing_result is not None:
        value = _validate_result(
            existing_result,
            spec,
            intent_bound.sha256,
            dispatch_bound.sha256,
        )
        if value.get("outcome") == "CAPABILITY_CONSUMED_EXPIRED_BEFORE_UNLINK":
            raise ContractError("expired result lacks effect-not-started marker")
        return value
    _revalidate_host(spec)
    _live_target(spec, allow_new_bridge=True)
    result = _result(
        spec, intent["before_filesystem_kib"], False,
        {"type": "Interrupted", "message": "read-only resume after durable dispatch"},
        intent_bound.sha256,
        dispatch_bound.sha256,
        resumed=True,
    )
    legacy.write_private_json_exclusive(result_path, result)
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    modes = value.add_mutually_exclusive_group(required=True)
    modes.add_argument("--print-execution-closure", action="store_true")
    modes.add_argument("--capture-inventory", action="store_true")
    modes.add_argument("--preserve-missing", action="store_true")
    modes.add_argument("--build-manifest", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--resume", action="store_true")
    value.add_argument("--run-id")
    value.add_argument("--output", type=Path)
    value.add_argument("--inventory", type=Path)
    value.add_argument("--inventory-sha256")
    value.add_argument("--manifest", type=Path)
    value.add_argument("--manifest-sha256")
    value.add_argument("--transaction-dir", type=Path)
    value.add_argument("--operator-attended", action="store_true")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.print_execution_closure:
        print(json.dumps(execution_closure(), indent=2, sort_keys=True))
        return 0
    if args.capture_inventory:
        if not args.run_id or args.output is None:
            raise ContractError("capture requires run-id and output")
        value = capture_inventory(args.run_id, args.output)
    elif args.preserve_missing:
        if not all((args.run_id, args.inventory, args.inventory_sha256)):
            raise ContractError("preservation arguments are incomplete")
        value = preserve_missing(
            args.run_id,
            args.inventory,
            args.inventory_sha256,
        )
    elif args.build_manifest:
        if not all((args.run_id, args.inventory, args.inventory_sha256, args.output)):
            raise ContractError("manifest build arguments are incomplete")
        value = build_manifest(args.run_id, args.inventory, args.inventory_sha256, args.output)
    else:
        if args.manifest is None or args.manifest_sha256 is None or args.transaction_dir is None:
            raise ContractError("live historical GC arguments are incomplete")
        spec = load_spec(args.manifest, args.manifest_sha256)
        value = execute(spec, args.transaction_dir, args.operator_attended) if args.execute else resume(spec, args.transaction_dir)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, h5.engine.ContractError, gc.ContractError) as exc:
        print(f"a90-h5-historical-image-gc-v1: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
