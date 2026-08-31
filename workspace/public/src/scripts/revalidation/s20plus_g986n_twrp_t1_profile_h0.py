#!/usr/bin/env python3
"""Exact host closure and recovery observer profile for S20+ TWRP T1.

This module has no connected entrypoint.  It pins the IYC2-stock-substrate,
AstroForge-ramdisk T1 candidate and exact-stock rollback, validates their
recovery-only Odin archives, and freezes the first-boot ADB observation.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[5]

import s20plus_g986n_recovery_canary_t0_runner_h0 as base


VERSION = "s20plus-g986n-twrp-t1-profile-h0-v1"
HOST_RESULT_SCHEMA = "s20plus_g986n_twrp_t1_host_validation_v1"
HOST_PASS_VERDICT = "PASS_S20PLUS_G986N_TWRP_T1_HOST_CLOSURE"

EXPECTED_TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "incremental": "G986NKSS8IYC2",
}

ODIN = base.ODIN
ODIN_SIZE = base.ODIN_SIZE
ODIN_SHA256 = base.ODIN_SHA256
USBFS_RE = base.USBFS_RE
AP_MEMBER_NAME = base.AP_MEMBER_NAME
pin_regular_file = base.pin_regular_file
validate_recovery_only_ap = base.validate_recovery_only_ap
_identity = base._identity

BASE_SOURCE = HERE / "s20plus_g986n_recovery_canary_t0_runner_h0.py"
BASE_SOURCE_SIZE = 30_909
BASE_SOURCE_SHA256 = (
    "3eb7cd148477c4e28d8bf1102a22f4eeb2f7a92bc99199fdd084af1dde5cd7df"
)
_BOUND_BASE_APIS = {
    "pin_regular_file": base.pin_regular_file,
    "validate_recovery_only_ap": base.validate_recovery_only_ap,
    "identity": base._identity,
}

OUTPUT_ROOT = ROOT / "workspace/private/outputs/s20plus_g986n/twrp_port_t1_v1"
CANDIDATE_AP = OUTPUT_ROOT / "candidate/AP.tar.md5"
CANDIDATE_AP_SIZE = 52_111_401
CANDIDATE_AP_SHA256 = (
    "3ed8498243ff09399ffd93fa3b0e90044a3cfe1709b7204dac53fe190647260f"
)
CANDIDATE_MEMBER_SIZE = 52_100_173
CANDIDATE_MEMBER_SHA256 = (
    "f4ccd3fbcd683b5597cf20b028b1230cfb0dd8f4f3c93d3db27c5314834ace7a"
)
CANDIDATE_RECOVERY_SIZE = 82_694_144
CANDIDATE_RECOVERY_SHA256 = (
    "48406883b1f631c4dfa1b157708f2e320e70b744967024bad6cb50b08cd06cb2"
)
CANDIDATE_TAR_MD5 = "8f2b4ad3ca9dee13860cea8faca4a170"

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
MANIFEST_SIZE = 9_703
MANIFEST_SHA256 = (
    "c5901e75a81997c9ab7b7b964710c166c7a9650dfee8fcf92de637269ac19019"
)
BUILDER = HERE / "build_s20plus_g986n_twrp_port_t1_h0.py"
BUILDER_SIZE = 25_415
BUILDER_SHA256 = (
    "300bd7f136dcb952db6ce7b1da2d4ce7ae382734b9f566f92e9ab6397f2aa3e7"
)

MARKER_PATH = "/init.s20plus_g986n_twrp_port_t1"
MARKER_SIZE = 355
MARKER_SHA256 = "9e772d73d58740e09abe7f75f30e99c66cda04547287189d859ed457b9c2c6c5"
TWRP_VERSION = "3.7.1_12-AstroForge_v2"
TWRP_INCREMENTAL = "eng.codeby.20260803.123008"

RECOVERY_OUTPUT_KEYS = (
    "boot_id",
    "uid",
    "twrp_version",
    "incremental",
    "ro_secure",
    "ro_debuggable",
    "usb_config",
    "adbd_state",
    "marker_sha256",
)
EXPECTED_RECOVERY_FIXED_OUTPUT = {
    "uid": "0",
    "twrp_version": TWRP_VERSION,
    "incremental": TWRP_INCREMENTAL,
    "ro_secure": "0",
    "ro_debuggable": "1",
    "usb_config": "adb",
    "adbd_state": "running",
    "marker_sha256": MARKER_SHA256,
}
MAX_RECOVERY_OBSERVER_BYTES = 4 * 1024
PROPOSED_RECOVERY_OBSERVER_TIMEOUT_SECONDS = 30.0
BOOT_ID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)

RECOVERY_SHELL_ARGUMENT = rf"""set -eu
boot_id=$(/system/bin/cat /proc/sys/kernel/random/boot_id)
uid=$(/system/bin/id -u)
twrp_version=$(/system/bin/getprop ro.twrp.version)
incremental=$(/system/bin/getprop ro.build.version.incremental)
ro_secure=$(/system/bin/getprop ro.secure)
ro_debuggable=$(/system/bin/getprop ro.debuggable)
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
    "boot_id=$boot_id" \
    "uid=$uid" \
    "twrp_version=$twrp_version" \
    "incremental=$incremental" \
    "ro_secure=$ro_secure" \
    "ro_debuggable=$ro_debuggable" \
    "usb_config=$usb_config" \
    "adbd_state=$adbd_state" \
    "marker_sha256=$marker_sha256"
"""


class TWRPT1ProfileError(RuntimeError):
    """The exact T1 host or observer closure changed."""


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise TWRPT1ProfileError(f"{label} has a duplicate key")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8", "strict"), object_pairs_hook=unique,
            parse_constant=lambda token: (_ for _ in ()).throw(
                TWRPT1ProfileError(f"{label} has a non-finite number")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise TWRPT1ProfileError(f"{label} is malformed") from exc
    if type(value) is not dict:
        raise TWRPT1ProfileError(f"{label} root differs")
    return value


def _read_exact(descriptor: int, size: int) -> bytes:
    payload = bytearray()
    offset = 0
    while offset < size:
        block = os.pread(descriptor, min(1024 * 1024, size - offset), offset)
        if not block:
            raise TWRPT1ProfileError("short manifest read")
        payload.extend(block)
        offset += len(block)
    if os.pread(descriptor, 1, size):
        raise TWRPT1ProfileError("manifest grew while read")
    return bytes(payload)


def validate_manifest() -> dict[str, Any]:
    with pin_regular_file(
        MANIFEST,
        label="T1 manifest",
        expected_size=MANIFEST_SIZE,
        expected_sha256=MANIFEST_SHA256,
    ) as (descriptor, receipt):
        value = _strict_json(_read_exact(descriptor, MANIFEST_SIZE), "T1 manifest")
    safety = value.get("safety")
    candidate = value.get("candidate")
    rollback = value.get("rollback")
    entries = value.get("ramdisk", {}).get("critical_port_entries", {})
    marker = entries.get(MARKER_PATH.removeprefix("/")) if type(entries) is dict else None
    if (
        value.get("schema") != "s20plus_g986n_twrp_port_t1_build_v1"
        or value.get("verdict")
        != "PASS_S20PLUS_G986N_TWRP_PORT_T1_HOST_BUILT_REVIEW_PENDING"
        or value.get("target") != EXPECTED_TARGET
        or value.get("tier") != "H0"
        or value.get("review_state") != "REVIEW_PENDING"
        or value.get("live_authority") is not False
        or value.get("twrp_version") != TWRP_VERSION
        or value.get("source_claim")
        != "BINARY_DONOR_PINNED_SOURCE_REPRODUCTION_UNPROVED"
        or type(safety) is not dict
        or safety.get("device_contact") is not False
        or safety.get("live_flash_authorized") is not False
        or safety.get("partition_transfers") != 0
        or type(safety.get("partition_transfers")) is not int
        or safety.get("vbmeta_payload") is not False
        or safety.get("data_write") is not False
        or safety.get("efs_write") is not False
        or safety.get("persist_write") is not False
        or type(candidate) is not dict
        or candidate.get("ap_tar_md5", {}).get("sha256") != CANDIDATE_AP_SHA256
        or candidate.get("ap_tar_md5", {}).get("members") != [AP_MEMBER_NAME]
        or candidate.get("recovery_img_lz4", {}).get("sha256")
        != CANDIDATE_MEMBER_SHA256
        or candidate.get("recovery_img")
        != {"size": CANDIDATE_RECOVERY_SIZE, "sha256": CANDIDATE_RECOVERY_SHA256}
        or type(rollback) is not dict
        or rollback.get("ap_tar_md5", {}).get("sha256") != ROLLBACK_AP_SHA256
        or rollback.get("ap_tar_md5", {}).get("members") != [AP_MEMBER_NAME]
        or rollback.get("recovery_img_lz4", {}).get("sha256")
        != ROLLBACK_MEMBER_SHA256
        or rollback.get("recovery_img")
        != {"size": ROLLBACK_RECOVERY_SIZE, "sha256": ROLLBACK_RECOVERY_SHA256}
        or rollback.get("exact_stock_bytes") is not True
        or marker
        != {"size": MARKER_SIZE, "sha256": MARKER_SHA256}
    ):
        raise TWRPT1ProfileError("T1 manifest semantics changed")
    return {**receipt, "semantic_validation": True}


def validate_host_closure() -> dict[str, Any]:
    current = {
        "pin_regular_file": base.pin_regular_file,
        "validate_recovery_only_ap": base.validate_recovery_only_ap,
        "identity": base._identity,
    }
    if any(current[name] is not value for name, value in _BOUND_BASE_APIS.items()):
        raise TWRPT1ProfileError("T0 H0 base API was rebound")
    with pin_regular_file(
        BASE_SOURCE,
        label="T0 H0 base source",
        expected_size=BASE_SOURCE_SIZE,
        expected_sha256=BASE_SOURCE_SHA256,
        require_nonwritable=False,
    ) as (_descriptor, base_source):
        base_receipt = dict(base_source)
    with pin_regular_file(
        ODIN, label="Odin4", expected_size=ODIN_SIZE,
        expected_sha256=ODIN_SHA256,
    ) as (_descriptor, odin):
        odin_receipt = dict(odin)
    with pin_regular_file(
        BUILDER, label="T1 builder", expected_size=BUILDER_SIZE,
        expected_sha256=BUILDER_SHA256, require_nonwritable=False,
    ) as (_descriptor, builder):
        builder_receipt = dict(builder)
    candidate = validate_recovery_only_ap(
        CANDIDATE_AP,
        label="T1 candidate",
        expected_size=CANDIDATE_AP_SIZE,
        expected_sha256=CANDIDATE_AP_SHA256,
        expected_member_size=CANDIDATE_MEMBER_SIZE,
        expected_member_sha256=CANDIDATE_MEMBER_SHA256,
        expected_tar_md5=CANDIDATE_TAR_MD5,
    )
    rollback = validate_recovery_only_ap(
        ROLLBACK_AP,
        label="T1 rollback",
        expected_size=ROLLBACK_AP_SIZE,
        expected_sha256=ROLLBACK_AP_SHA256,
        expected_member_size=ROLLBACK_MEMBER_SIZE,
        expected_member_sha256=ROLLBACK_MEMBER_SHA256,
        expected_tar_md5=ROLLBACK_TAR_MD5,
    )
    return {
        "schema": HOST_RESULT_SCHEMA,
        "version": VERSION,
        "verdict": HOST_PASS_VERDICT,
        "tier": "H0",
        "live_authorized": False,
        "target": dict(EXPECTED_TARGET),
        "closure": {
            "t0_h0_base": base_receipt,
            "odin": odin_receipt,
            "builder": builder_receipt,
            "candidate": candidate,
            "rollback": rollback,
            "manifest": validate_manifest(),
        },
    }


def parse_recovery_observation(
    result: tuple[int, bytes, bytes],
) -> dict[str, str]:
    if type(result) is not tuple or len(result) != 3:
        raise TWRPT1ProfileError("T1 observer envelope differs")
    returncode, stdout, stderr = result
    if (
        type(returncode) is not int
        or type(stdout) is not bytes
        or type(stderr) is not bytes
        or len(stdout) > MAX_RECOVERY_OBSERVER_BYTES
        or len(stderr) > MAX_RECOVERY_OBSERVER_BYTES
        or returncode != 0
        or stderr
    ):
        raise TWRPT1ProfileError("T1 observer command failed or exceeded bounds")
    try:
        text = stdout.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise TWRPT1ProfileError("T1 observer output is not UTF-8") from exc
    if "\r" in text or "\x00" in text or not text.endswith("\n"):
        raise TWRPT1ProfileError("T1 observer framing differs")
    lines = text.splitlines()
    if len(lines) != len(RECOVERY_OUTPUT_KEYS):
        raise TWRPT1ProfileError("T1 observer field count differs")
    values: dict[str, str] = {}
    for expected, line in zip(RECOVERY_OUTPUT_KEYS, lines, strict=True):
        key, separator, value = line.partition("=")
        if separator != "=" or key != expected or key in values or not value:
            raise TWRPT1ProfileError("T1 observer grammar differs")
        values[key] = value
    if any(values.get(key) != value for key, value in EXPECTED_RECOVERY_FIXED_OUTPUT.items()):
        raise TWRPT1ProfileError("T1 observer fixed values differ")
    if BOOT_ID_RE.fullmatch(values["boot_id"]) is None:
        raise TWRPT1ProfileError("T1 recovery boot ID differs")
    return values
