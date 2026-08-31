#!/usr/bin/env python3
"""Dormant H0 execution closure for the S20+ recovery ADB canary T0.

The module validates the exact host artifacts, freezes the proposed recovery
observer and Odin command shapes, and models the one-shot journal.  It has no
device backend.  ``--connected`` always stops before reading an artifact.
Activation must be implemented as a separately reviewed connected owner after
the common and target contracts explicitly permit the recovery-only lane.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tarfile
from typing import Any, Iterator, Sequence


VERSION = "s20plus-g986n-recovery-canary-t0-runner-h0-v1"
PLAN_SCHEMA = "s20plus_g986n_recovery_canary_t0_runner_h0_plan_v1"
HOST_RESULT_SCHEMA = "s20plus_g986n_recovery_canary_t0_host_validation_v1"
HOST_PASS_VERDICT = "PASS_S20PLUS_G986N_RECOVERY_CANARY_T0_HOST_CLOSURE"
DORMANT_VERDICT = "STOP_S20PLUS_G986N_RECOVERY_CANARY_T0_NOT_ACTIVE"

# Never flip this constant to activate the profile.  A connected owner is a
# separate execution-critical file and requires the reviews named above.
RECOVERY_CANARY_T0_ACTIVE = False

ROOT = Path(__file__).resolve().parents[5]
EXPECTED_TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "incremental": "G986NKSS8IYC2",
}

ODIN = Path("/usr/bin/odin4")
ODIN_SIZE = 3_746_744
ODIN_SHA256 = "6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b"

OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s20plus_g986n/recovery_adb_canary_t0_v1"
)
CANDIDATE_AP = OUTPUT_ROOT / "candidate/AP.tar.md5"
CANDIDATE_AP_SIZE = 36_556_841
CANDIDATE_AP_SHA256 = (
    "30227458889f1fa99eca192c9b7f8747f168d9e33cc1f407b52ae2b4d298559a"
)
CANDIDATE_MEMBER_SIZE = 36_547_618
CANDIDATE_MEMBER_SHA256 = (
    "7f0e6b53a1036904fd02c5e8c2c014d3112ffb58fc33f9aa9a26c0962af45928"
)
CANDIDATE_RECOVERY_SIZE = 82_694_144
CANDIDATE_RECOVERY_SHA256 = (
    "e1297613df576d25cc9391df97dac7cf316fee545f56111e6bc5340cb8ce659b"
)
CANDIDATE_TAR_MD5 = "134a6bb8cb76efd575bf88dc1d668533"

ROLLBACK_AP = OUTPUT_ROOT / "rollback/AP.tar.md5"
ROLLBACK_AP_SIZE = 36_608_041
ROLLBACK_AP_SHA256 = (
    "ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157"
)
ROLLBACK_MEMBER_SIZE = 36_600_544
ROLLBACK_MEMBER_SHA256 = (
    "6b962af2fc4fcc424d16ecdcee1793bdd6d4c8dba2e80d35cb21961fcb865923"
)
ROLLBACK_RECOVERY_SIZE = 82_694_144
ROLLBACK_RECOVERY_SHA256 = (
    "dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e"
)
ROLLBACK_TAR_MD5 = "ae65d25904f3af850e47e2bf896263e5"

MANIFEST = OUTPUT_ROOT / "manifest.json"
MANIFEST_SIZE = 5_459
MANIFEST_SHA256 = (
    "7c693b4e2e13efa912b5de00a95bbd41bb1651913427461e756225243381e1e3"
)
BUILDER = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "build_s20plus_g986n_recovery_adb_canary_h0.py"
)
BUILDER_SIZE = 25_007
BUILDER_SHA256 = (
    "811b2f80db822689d716c0de400cea22440af3069d7ea20945ddf0b36908c118"
)
RECOVERY_DIGEST_PROFILE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_recovery_digest_profile_h0.py"
)
RECOVERY_DIGEST_PROFILE_SIZE = 9_509
RECOVERY_DIGEST_PROFILE_SHA256 = (
    "9377e58d3717e0fa96826210815b09df20bf2ba62a70c85c896f5a6fdf68fded"
)

AP_MEMBER_NAME = "recovery.img.lz4"
MD5_TRAILER_SIZE = len(b"0" * 32 + b"  AP.tar\n")
USBFS_RE = re.compile(r"/dev/bus/usb/[0-9]{3}/[0-9]{3}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
BOOT_ID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)

MARKER_PATH = "/init.s20plus_g986n_recovery_adb_canary"
MARKER_SIZE = 159
MARKER_SHA256 = "5aafd7ca6918bf82aef0b7de62346d8de1b17bb0c9ececafa15978cfae2c87b0"
RECOVERY_OUTPUT_KEYS = (
    "model",
    "device",
    "product_name",
    "incremental",
    "boot_id",
    "service_adb_root",
    "usb_config",
    "adbd_state",
    "marker_sha256",
)
EXPECTED_RECOVERY_FIXED_OUTPUT = {
    "model": "SM-G986N",
    "device": "y2q",
    "product_name": "y2qksx",
    "incremental": "G986NKSS8IYC2",
    "service_adb_root": "1",
    "usb_config": "adb",
    "adbd_state": "running",
    "marker_sha256": MARKER_SHA256,
}
MAX_RECOVERY_OBSERVER_BYTES = 4 * 1024
PROPOSED_RECOVERY_OBSERVER_TIMEOUT_SECONDS = 30.0

RECOVERY_OBSERVER_SCRIPT = rf"""set -eu
model=$(/system/bin/getprop ro.product.model)
device=$(/system/bin/getprop ro.product.device)
product_name=$(/system/bin/getprop ro.product.name)
incremental=$(/system/bin/getprop ro.build.version.incremental)
boot_id=$(/system/bin/cat /proc/sys/kernel/random/boot_id)
service_adb_root=$(/system/bin/getprop service.adb.root)
usb_config=$(/system/bin/getprop sys.usb.config)
adbd_state=$(/system/bin/getprop init.svc.adbd)
marker_path={MARKER_PATH}
[ -f "$marker_path" ] || exit 81
[ ! -L "$marker_path" ] || exit 82
marker_line=$(/system/bin/sha256sum "$marker_path")
set -- $marker_line
[ "$#" -eq 2 ] || exit 83
[ "$2" = "$marker_path" ] || exit 84
marker_sha256=$1
[ "$marker_sha256" = "{MARKER_SHA256}" ] || exit 85
printf '%s\n' \
    "model=$model" \
    "device=$device" \
    "product_name=$product_name" \
    "incremental=$incremental" \
    "boot_id=$boot_id" \
    "service_adb_root=$service_adb_root" \
    "usb_config=$usb_config" \
    "adbd_state=$adbd_state" \
    "marker_sha256=$marker_sha256"
"""
RECOVERY_SHELL_ARGUMENT = RECOVERY_OBSERVER_SCRIPT

# The successful path is a prefix of this list; recovery_boot_intent is the
# only optional node.  An uncertain candidate result skips that physical boot
# and publishes candidate-observation as NO_PROOF before stock rollback.
JOURNAL_ORDER = (
    "prepared.json",
    "approval.json",
    "candidate-download-intent.json",
    "candidate-download-arrival.json",
    "candidate-intent.json",
    "candidate-result.json",
    "recovery-boot-intent.json",
    "candidate-observation.json",
    "rollback-download-intent.json",
    "rollback-download-arrival.json",
    "rollback-intent.json",
    "rollback-result.json",
    "final-health.json",
    "terminal.json",
)
OPTIONAL_JOURNAL_NODES = frozenset({"recovery-boot-intent.json"})
REQUIRED_JOURNAL_ORDER = tuple(
    name for name in JOURNAL_ORDER if name not in OPTIONAL_JOURNAL_NODES
)


class RecoveryCanaryT0Error(RuntimeError):
    """A frozen host closure or proposed one-shot invariant failed."""


def _identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _sha256_fd(descriptor: int, size: int) -> str:
    digest = hashlib.sha256()
    offset = 0
    while offset < size:
        block = os.pread(descriptor, min(8 * 1024 * 1024, size - offset), offset)
        if not block:
            raise RecoveryCanaryT0Error("short read while hashing a pinned file")
        digest.update(block)
        offset += len(block)
    if os.pread(descriptor, 1, size):
        raise RecoveryCanaryT0Error("pinned file grew while hashing")
    return digest.hexdigest()


@contextmanager
def pin_regular_file(
    path: Path,
    *,
    label: str,
    expected_size: int,
    expected_sha256: str,
    require_nonwritable: bool = True,
) -> Iterator[tuple[int, dict[str, Any]]]:
    if type(expected_size) is not int or expected_size <= 0 or SHA256_RE.fullmatch(expected_sha256) is None:
        raise RecoveryCanaryT0Error(f"{label} expected receipt is malformed")
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        opened = os.fstat(descriptor)
        named = os.lstat(path)
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_ISLNK(named.st_mode)
            or _identity(opened) != _identity(named)
            or opened.st_nlink != 1
            or opened.st_size != expected_size
            or (require_nonwritable and opened.st_mode & 0o022)
            or path.resolve(strict=True) != path.absolute()
        ):
            raise RecoveryCanaryT0Error(f"{label} is not the exact direct immutable file")
        digest = _sha256_fd(descriptor, expected_size)
        if digest != expected_sha256:
            raise RecoveryCanaryT0Error(f"{label} SHA-256 changed")
        if _identity(os.fstat(descriptor)) != _identity(opened) or _identity(os.lstat(path)) != _identity(named):
            raise RecoveryCanaryT0Error(f"{label} changed while pinned")
        yield descriptor, {
            "path": str(path),
            "size": expected_size,
            "sha256": digest,
            "mode": f"{stat.S_IMODE(opened.st_mode):04o}",
            "direct_regular": True,
            "single_link": True,
            "group_or_world_writable": bool(opened.st_mode & 0o022),
        }
        if _identity(os.fstat(descriptor)) != _identity(opened) or _identity(os.lstat(path)) != _identity(named):
            raise RecoveryCanaryT0Error(f"{label} changed before unpin")
    except (FileNotFoundError, OSError) as exc:
        if isinstance(exc, RecoveryCanaryT0Error):
            raise
        raise RecoveryCanaryT0Error(f"{label} cannot be pinned") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _read_fd(descriptor: int, size: int) -> bytes:
    payload = bytearray()
    offset = 0
    while offset < size:
        block = os.pread(descriptor, min(1024 * 1024, size - offset), offset)
        if not block:
            raise RecoveryCanaryT0Error("short pinned-file read")
        payload.extend(block)
        offset += len(block)
    return bytes(payload)


def _validate_tar_md5(
    descriptor: int,
    *,
    file_size: int,
    expected_md5: str,
) -> None:
    if re.fullmatch(r"[0-9a-f]{32}", expected_md5) is None:
        raise RecoveryCanaryT0Error("expected Odin MD5 is malformed")
    tar_size = file_size - MD5_TRAILER_SIZE
    if tar_size <= 0:
        raise RecoveryCanaryT0Error("Odin archive is shorter than its trailer")
    digest = hashlib.md5()
    offset = 0
    while offset < tar_size:
        block = os.pread(descriptor, min(8 * 1024 * 1024, tar_size - offset), offset)
        if not block:
            raise RecoveryCanaryT0Error("short Odin tar read")
        digest.update(block)
        offset += len(block)
    trailer = os.pread(descriptor, MD5_TRAILER_SIZE, tar_size)
    expected_trailer = f"{expected_md5}  AP.tar\n".encode("ascii")
    if len(trailer) != MD5_TRAILER_SIZE or trailer != expected_trailer:
        raise RecoveryCanaryT0Error("Odin MD5 trailer changed")
    if digest.hexdigest() != expected_md5:
        raise RecoveryCanaryT0Error("Odin tar MD5 does not match its trailer")


def validate_recovery_only_ap(
    path: Path,
    *,
    label: str,
    expected_size: int,
    expected_sha256: str,
    expected_member_size: int,
    expected_member_sha256: str,
    expected_tar_md5: str,
) -> dict[str, Any]:
    with pin_regular_file(
        path,
        label=label,
        expected_size=expected_size,
        expected_sha256=expected_sha256,
    ) as (descriptor, receipt):
        _validate_tar_md5(
            descriptor, file_size=expected_size, expected_md5=expected_tar_md5
        )
        duplicate = os.dup(descriptor)
        try:
            os.lseek(duplicate, 0, os.SEEK_SET)
            with os.fdopen(duplicate, "rb", closefd=True) as stream:
                duplicate = -1
                with tarfile.open(fileobj=stream, mode="r:") as archive:
                    members = archive.getmembers()
                    if len(members) != 1:
                        raise RecoveryCanaryT0Error(
                            f"{label} does not have exactly one member"
                        )
                    member = members[0]
                    if (
                        member.name != AP_MEMBER_NAME
                        or not member.isfile()
                        or member.size != expected_member_size
                        or member.mode != 0o644
                        or member.uid != 0
                        or member.gid != 0
                        or member.mtime != 0
                    ):
                        raise RecoveryCanaryT0Error(
                            f"{label} recovery member metadata changed"
                        )
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        raise RecoveryCanaryT0Error(
                            f"{label} recovery member is unreadable"
                        )
                    member_digest = hashlib.sha256()
                    member_bytes = 0
                    while True:
                        block = extracted.read(8 * 1024 * 1024)
                        if not block:
                            break
                        member_bytes += len(block)
                        if member_bytes > expected_member_size:
                            raise RecoveryCanaryT0Error(
                                f"{label} recovery member exceeded its bound"
                            )
                        member_digest.update(block)
        except (tarfile.TarError, OSError) as exc:
            raise RecoveryCanaryT0Error(f"{label} tar structure is invalid") from exc
        finally:
            if duplicate >= 0:
                os.close(duplicate)
        if member_bytes != expected_member_size or member_digest.hexdigest() != expected_member_sha256:
            raise RecoveryCanaryT0Error(f"{label} recovery member identity changed")
        return {
            **receipt,
            "tar_md5": expected_tar_md5,
            "members": [
                {
                    "name": AP_MEMBER_NAME,
                    "type": "regular",
                    "size": expected_member_size,
                    "sha256": expected_member_sha256,
                    "mode": "0644",
                    "uid": 0,
                    "gid": 0,
                    "mtime": 0,
                }
            ],
            "recovery_only": True,
            "vbmeta_member": False,
        }


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise RecoveryCanaryT0Error(f"{label} has a duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(payload.decode("utf-8", "strict"), object_pairs_hook=object_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RecoveryCanaryT0Error(f"{label} is malformed JSON") from exc
    if type(value) is not dict:
        raise RecoveryCanaryT0Error(f"{label} root is not an object")
    return value


def validate_manifest() -> dict[str, Any]:
    with pin_regular_file(
        MANIFEST,
        label="T0 build manifest",
        expected_size=MANIFEST_SIZE,
        expected_sha256=MANIFEST_SHA256,
    ) as (descriptor, receipt):
        value = _strict_json(_read_fd(descriptor, MANIFEST_SIZE), "T0 build manifest")
    safety = value.get("safety")
    candidate = value.get("candidate")
    rollback = value.get("rollback")
    marker = value.get("ramdisk", {}).get("marker") if type(value.get("ramdisk")) is dict else None
    if (
        value.get("schema") != "s20plus_g986n_recovery_adb_canary_t0_build_v1"
        or value.get("verdict")
        != "PASS_S20PLUS_G986N_RECOVERY_ADB_CANARY_T0_HOST_BUILT_REVIEW_PENDING"
        or value.get("target") != EXPECTED_TARGET
        or value.get("tier") != "H0"
        or value.get("review_state") != "REVIEW_PENDING"
        or value.get("live_authority") is not False
        or type(safety) is not dict
        or any(
            safety.get(key) is not False
            for key in (
                "device_contact",
                "live_flash_authorized",
                "policy_amendment_complete",
                "independent_review_complete",
                "vbmeta_payload",
                "vendor_mutation",
                "misc_write",
                "data_format",
            )
        )
        or type(candidate) is not dict
        or candidate.get("ap_tar_md5", {}).get("sha256") != CANDIDATE_AP_SHA256
        or candidate.get("ap_tar_md5", {}).get("members") != [AP_MEMBER_NAME]
        or candidate.get("recovery_img_lz4", {}).get("sha256")
        != CANDIDATE_MEMBER_SHA256
        or candidate.get("recovery_img", {})
        != {"size": CANDIDATE_RECOVERY_SIZE, "sha256": CANDIDATE_RECOVERY_SHA256}
        or type(rollback) is not dict
        or rollback.get("ap_tar_md5", {}).get("sha256") != ROLLBACK_AP_SHA256
        or rollback.get("ap_tar_md5", {}).get("members") != [AP_MEMBER_NAME]
        or rollback.get("recovery_img_lz4", {}).get("sha256")
        != ROLLBACK_MEMBER_SHA256
        or rollback.get("recovery_img", {})
        != {"size": ROLLBACK_RECOVERY_SIZE, "sha256": ROLLBACK_RECOVERY_SHA256}
        or rollback.get("exact_stock_bytes") is not True
        or rollback.get("demonstrated_live_path") is not False
        or marker
        != {"path": MARKER_PATH, "size": MARKER_SIZE, "sha256": MARKER_SHA256, "mode": "0444"}
    ):
        raise RecoveryCanaryT0Error("T0 build manifest semantics changed")
    return {**receipt, "semantic_validation": True}


def validate_host_closure() -> dict[str, Any]:
    with pin_regular_file(
        ODIN,
        label="Odin4",
        expected_size=ODIN_SIZE,
        expected_sha256=ODIN_SHA256,
    ) as (_odin_descriptor, odin):
        odin_receipt = dict(odin)
    with pin_regular_file(
        BUILDER,
        label="T0 builder",
        expected_size=BUILDER_SIZE,
        expected_sha256=BUILDER_SHA256,
        require_nonwritable=False,
    ) as (_builder_descriptor, builder):
        builder_receipt = dict(builder)
    with pin_regular_file(
        RECOVERY_DIGEST_PROFILE,
        label="stock recovery digest profile",
        expected_size=RECOVERY_DIGEST_PROFILE_SIZE,
        expected_sha256=RECOVERY_DIGEST_PROFILE_SHA256,
        require_nonwritable=False,
    ) as (_profile_descriptor, profile):
        profile_receipt = dict(profile)
    candidate = validate_recovery_only_ap(
        CANDIDATE_AP,
        label="candidate recovery-only AP",
        expected_size=CANDIDATE_AP_SIZE,
        expected_sha256=CANDIDATE_AP_SHA256,
        expected_member_size=CANDIDATE_MEMBER_SIZE,
        expected_member_sha256=CANDIDATE_MEMBER_SHA256,
        expected_tar_md5=CANDIDATE_TAR_MD5,
    )
    rollback = validate_recovery_only_ap(
        ROLLBACK_AP,
        label="rollback recovery-only AP",
        expected_size=ROLLBACK_AP_SIZE,
        expected_sha256=ROLLBACK_AP_SHA256,
        expected_member_size=ROLLBACK_MEMBER_SIZE,
        expected_member_sha256=ROLLBACK_MEMBER_SHA256,
        expected_tar_md5=ROLLBACK_TAR_MD5,
    )
    manifest = validate_manifest()
    return {
        "schema": HOST_RESULT_SCHEMA,
        "version": VERSION,
        "verdict": HOST_PASS_VERDICT,
        "tier": "H0",
        "live_authorized": False,
        "target": dict(EXPECTED_TARGET),
        "closure": {
            "odin": odin_receipt,
            "builder": builder_receipt,
            "stock_recovery_digest_profile": profile_receipt,
            "candidate": candidate,
            "rollback": rollback,
            "manifest": manifest,
        },
    }


def parse_recovery_observation(result: tuple[int, bytes, bytes]) -> dict[str, str]:
    if type(result) is not tuple or len(result) != 3:
        raise RecoveryCanaryT0Error("recovery observer envelope is malformed")
    returncode, stdout, stderr = result
    if type(returncode) is not int or type(stdout) is not bytes or type(stderr) is not bytes:
        raise RecoveryCanaryT0Error("recovery observer envelope types are invalid")
    if len(stdout) > MAX_RECOVERY_OBSERVER_BYTES or len(stderr) > MAX_RECOVERY_OBSERVER_BYTES:
        raise RecoveryCanaryT0Error("recovery observer transcript exceeded its bound")
    if returncode != 0 or stderr:
        raise RecoveryCanaryT0Error("recovery observer command did not close cleanly")
    try:
        text = stdout.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise RecoveryCanaryT0Error("recovery observer output is not UTF-8") from exc
    if "\r" in text or "\x00" in text or not text.endswith("\n"):
        raise RecoveryCanaryT0Error("recovery observer output framing changed")
    lines = text.splitlines()
    if len(lines) != len(RECOVERY_OUTPUT_KEYS):
        raise RecoveryCanaryT0Error("recovery observer field count changed")
    values: dict[str, str] = {}
    for expected_key, line in zip(RECOVERY_OUTPUT_KEYS, lines, strict=True):
        key, separator, value = line.partition("=")
        if separator != "=" or key != expected_key or key in values or not value:
            raise RecoveryCanaryT0Error("recovery observer field grammar changed")
        values[key] = value
    if any(values.get(key) != value for key, value in EXPECTED_RECOVERY_FIXED_OUTPUT.items()):
        raise RecoveryCanaryT0Error("recovery observer exact target or marker changed")
    if BOOT_ID_RE.fullmatch(values["boot_id"]) is None:
        raise RecoveryCanaryT0Error("recovery boot ID is malformed")
    return values


def candidate_transfer_argv(endpoint: str) -> list[str]:
    if type(endpoint) is not str or USBFS_RE.fullmatch(endpoint) is None:
        raise RecoveryCanaryT0Error("candidate Download endpoint grammar is invalid")
    return [str(ODIN), "-a", str(CANDIDATE_AP), "-d", endpoint]


def rollback_transfer_argv(endpoint: str) -> list[str]:
    if type(endpoint) is not str or USBFS_RE.fullmatch(endpoint) is None:
        raise RecoveryCanaryT0Error("rollback Download endpoint grammar is invalid")
    return [str(ODIN), "--reboot", "-a", str(ROLLBACK_AP), "-d", endpoint]


def validate_journal_nodes(nodes: set[str] | frozenset[str]) -> frozenset[str]:
    if type(nodes) not in (set, frozenset) or any(type(name) is not str for name in nodes):
        raise RecoveryCanaryT0Error("journal node inventory is malformed")
    present = frozenset(nodes)
    unknown = present - frozenset(JOURNAL_ORDER)
    if unknown:
        raise RecoveryCanaryT0Error("journal contains an unknown node")
    required_present = [name for name in REQUIRED_JOURNAL_ORDER if name in present]
    if required_present != list(REQUIRED_JOURNAL_ORDER[: len(required_present)]):
        raise RecoveryCanaryT0Error("journal has a gap or reordered required node")
    if "recovery-boot-intent.json" in present:
        if "candidate-result.json" not in present or "candidate-observation.json" in present and "candidate-result.json" not in present:
            raise RecoveryCanaryT0Error("recovery boot intent has no candidate result")
        if "rollback-download-intent.json" in present and "candidate-observation.json" not in present:
            raise RecoveryCanaryT0Error("rollback path bypassed candidate observation")
    if "terminal.json" in present and "final-health.json" not in present:
        raise RecoveryCanaryT0Error("terminal has no final health")
    return present


def replay_policy(nodes: set[str] | frozenset[str]) -> dict[str, Any]:
    present = validate_journal_nodes(nodes)
    candidate_intent = "candidate-intent.json" in present
    rollback_intent = "rollback-intent.json" in present
    candidate_ready = (
        "candidate-download-arrival.json" in present and not candidate_intent
    )
    rollback_ready = "rollback-download-arrival.json" in present and not rollback_intent
    return {
        "candidate_transfer_permitted": candidate_ready,
        "candidate_replay_permitted": False if candidate_intent else None,
        "rollback_transfer_permitted": rollback_ready,
        "rollback_replay_permitted": False if rollback_intent else None,
        "candidate_attempt_maximum": 1,
        "rollback_attempt_maximum": 1,
    }


def next_reviewed_action(nodes: set[str] | frozenset[str]) -> str:
    present = validate_journal_nodes(nodes)
    if not present:
        return "host-prepare"
    for name, action in (
        ("approval.json", "await-fresh-attended-approval"),
        ("candidate-download-intent.json", "publish-candidate-download-intent"),
        ("candidate-download-arrival.json", "observe-bound-candidate-download-arrival"),
        ("candidate-intent.json", "publish-candidate-transfer-intent"),
        ("candidate-result.json", "finalize-candidate-result-without-replay"),
    ):
        if name not in present:
            return action
    if "candidate-observation.json" not in present:
        if "recovery-boot-intent.json" not in present:
            return "classify-candidate-then-boot-recovery-once-or-record-no-proof"
        return "observe-fixed-recovery-canary-without-transfer-replay"
    for name, action in (
        ("rollback-download-intent.json", "publish-stock-rollback-download-intent"),
        ("rollback-download-arrival.json", "observe-bound-stock-rollback-download-arrival"),
        ("rollback-intent.json", "publish-stock-rollback-transfer-intent"),
        ("rollback-result.json", "finalize-stock-rollback-result-without-replay"),
        ("final-health.json", "observe-android-health-and-stock-recovery-digest"),
        ("terminal.json", "publish-terminal-if-and-only-if-final-health-passes"),
    ):
        if name not in present:
            return action
    return "closed-no-more-device-action"


def source_receipt() -> dict[str, Any]:
    path = Path(__file__).resolve()
    payload = path.read_bytes()
    return {"path": str(path), "size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def render_plan() -> dict[str, Any]:
    observer = RECOVERY_OBSERVER_SCRIPT.encode("utf-8")
    return {
        "schema": PLAN_SCHEMA,
        "version": VERSION,
        "status": "DORMANT_H0_EXECUTION_CLOSURE_REVIEW_PENDING",
        "verdict": DORMANT_VERDICT,
        "tier": "H0",
        "active": RECOVERY_CANARY_T0_ACTIVE,
        "live_authorized": False,
        "current_contract_status": "RECOVERY_PARTITION_READ_AND_WRITE_FORBIDDEN",
        "target": dict(EXPECTED_TARGET),
        "experiment": "T0_RECOVERY_ADB_CANARY_ONLY",
        "t1_authorized": False,
        "artifacts": {
            "candidate": {
                "path": str(CANDIDATE_AP),
                "size": CANDIDATE_AP_SIZE,
                "sha256": CANDIDATE_AP_SHA256,
                "members": [AP_MEMBER_NAME],
                "candidate_recovery_sha256": CANDIDATE_RECOVERY_SHA256,
            },
            "rollback": {
                "path": str(ROLLBACK_AP),
                "size": ROLLBACK_AP_SIZE,
                "sha256": ROLLBACK_AP_SHA256,
                "members": [AP_MEMBER_NAME],
                "stock_recovery_sha256": ROLLBACK_RECOVERY_SHA256,
                "mandatory": True,
                "demonstrated_live_path": False,
            },
            "odin": {"path": str(ODIN), "size": ODIN_SIZE, "sha256": ODIN_SHA256},
        },
        "proposed_command_shapes": {
            "candidate": ["odin4", "-a", "CANDIDATE_AP.tar.md5", "-d", "BOUND_USBFS"],
            "candidate_auto_reboot": False,
            "rollback": [
                "odin4",
                "--reboot",
                "-a",
                "ROLLBACK_AP.tar.md5",
                "-d",
                "BOUND_USBFS",
            ],
            "caller_supplied_artifact": False,
            "caller_supplied_partition": False,
        },
        "recovery_observer": {
            "script_size": len(observer),
            "script_sha256": hashlib.sha256(observer).hexdigest(),
            "shell_argument_size": len(RECOVERY_SHELL_ARGUMENT.encode("utf-8")),
            "timeout_seconds": PROPOSED_RECOVERY_OBSERVER_TIMEOUT_SECONDS,
            "maximum_bytes": MAX_RECOVERY_OBSERVER_BYTES,
            "marker_path": MARKER_PATH,
            "marker_size": MARKER_SIZE,
            "marker_sha256": MARKER_SHA256,
            "output_keys": list(RECOVERY_OUTPUT_KEYS),
        },
        "journal": {
            "ordered_nodes": list(JOURNAL_ORDER),
            "optional_nodes": sorted(OPTIONAL_JOURNAL_NODES),
            "intent_before_effect": True,
            "candidate_attempt_maximum": 1,
            "rollback_attempt_maximum": 1,
            "candidate_replay_after_intent": False,
            "rollback_replay_after_intent": False,
            "observer_timeout_causes_replay": False,
        },
        "maximum_effects": {
            "candidate_recovery_partition_transfer": 1,
            "candidate_direct_recovery_boot": 1,
            "stock_rollback_download_entry": 1,
            "stock_recovery_partition_transfer": 1,
            "all_other_partition_transfers": 0,
            "vbmeta_transfers": 0,
            "data_formats": 0,
            "misc_writes": 0,
        },
        "preconditions": [
            "exact healthy rooted Android and current boot binding",
            "exact stock recovery digest from the separately reviewed fixed profile",
            "exact candidate rollback Odin and source closure host receipts",
            "empty Download baseline and one exact bound endpoint",
            "demonstrated physical Download access and attended direct-recovery chord",
            "fresh approval for one exact prepared binding",
            "common boundary target contract process runner and hostile-test review",
        ],
        "success_requires": [
            "completed candidate transfer classification",
            "new recovery boot ID and exact T0 marker observation",
            "one completed exact-stock rollback transfer",
            "healthy exact rooted Android on a later boot",
            "exact stock recovery size and SHA-256 after rollback",
        ],
        "source": source_receipt(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect the dormant S20+ recovery canary T0 closure"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--render-plan", action="store_true")
    mode.add_argument("--validate-host", action="store_true")
    mode.add_argument("--connected", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.connected:
        print(DORMANT_VERDICT)
        return 2
    if arguments.validate_host:
        print(json.dumps(validate_host_closure(), sort_keys=True, indent=2))
        return 0
    print(json.dumps(render_plan(), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
