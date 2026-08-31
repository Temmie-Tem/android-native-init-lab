#!/usr/bin/env python3
"""Dormant H0 profile for one fixed S20+ stock-recovery digest read.

This module deliberately has no ADB backend or subprocess execution path.  It
freezes the exact privileged shell bytes and a strict parser so they can be
reviewed before any common-boundary, target-contract, or live-runner change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shlex
from typing import Any, Sequence


VERSION = "s20plus-g986n-recovery-digest-profile-h0-v1"
PLAN_SCHEMA = "s20plus_g986n_recovery_digest_profile_h0_plan_v1"
DORMANT_VERDICT = "STOP_S20PLUS_G986N_RECOVERY_DIGEST_PROFILE_NOT_ACTIVE"

# This is a review artifact, not a live feature switch.  A future change may
# not activate it in place: the connected owner must be reviewed separately.
RECOVERY_DIGEST_PROFILE_ACTIVE = False

EXPECTED_TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "incremental": "G986NKSS8IYC2",
}
FIXED_RECOVERY_LINK = "/dev/block/by-name/recovery"
EXPECTED_RECOVERY_NODE = "/dev/block/sda24"
EXPECTED_RECOVERY_SIZE = 82_694_144
EXPECTED_RECOVERY_SHA256 = (
    "dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e"
)
PIT_NAME = "Y2Q_USA_SINGLE.pit"
PIT_SIZE = 12_156
PIT_SHA256 = "06f87a8aba5ac95c4784f034816d2744c246af6067452b0a3acd2b63c5763b99"
PIT_RECOVERY_ENTRY_INDEX = 23
PIT_RECOVERY_IDENTIFIER = 24
PIT_RECOVERY_BLOCK_OFFSET = 171_027
PIT_RECOVERY_BLOCK_COUNT = 20_189
PIT_BLOCK_BYTES = 4_096
MAX_ROOT_STDOUT_BYTES = 4 * 1024
MAX_ROOT_STDERR_BYTES = 4 * 1024
PROPOSED_ROOT_TIMEOUT_SECONDS = 180.0

ROOT_OUTPUT_KEYS = (
    "uid",
    "gid",
    "context",
    "magisk_version",
    "magisk_version_code",
    "selinux",
    "pid1_exe",
    "pid1_context",
    "recovery_size",
    "recovery_sha256",
)

EXPECTED_ROOT_OUTPUT = {
    "uid": "0",
    "gid": "0",
    "context": "u:r:magisk:s0",
    "magisk_version": "30.7:MAGISK:R",
    "magisk_version_code": "30700",
    "selinux": "Enforcing",
    "pid1_exe": "/system/bin/init",
    "pid1_context": "u:r:init:s0",
    "recovery_size": str(EXPECTED_RECOVERY_SIZE),
    "recovery_sha256": EXPECTED_RECOVERY_SHA256,
}

# No value in this script is caller supplied.  The symlink target must be one
# direct Samsung UFS block node, the node must be a block device, and both size
# and content digest must match the exact retained IYC2 stock recovery.
ROOT_READ_SCRIPT = rf"""set -eu
uid=$(/system/bin/id -u)
gid=$(/system/bin/id -g)
context=$(/system/bin/cat /proc/self/attr/current)
magisk_version=$(/data/adb/magisk/magisk -v)
magisk_version_code=$(/data/adb/magisk/magisk -V)
selinux=$(/system/bin/getenforce)
pid1_exe=$(/system/bin/readlink /proc/1/exe)
pid1_context=$(/system/bin/cat /proc/1/attr/current)
recovery_link={FIXED_RECOVERY_LINK}
recovery_node=$(/system/bin/readlink -f "$recovery_link")
[ "$recovery_node" = "{EXPECTED_RECOVERY_NODE}" ] || exit 91
[ -b "$recovery_node" ] || exit 92
recovery_size=$(/system/bin/blockdev --getsize64 "$recovery_node")
[ "$recovery_size" = "{EXPECTED_RECOVERY_SIZE}" ] || exit 93
recovery_line=$(/system/bin/sha256sum "$recovery_node")
set -- $recovery_line
[ "$#" -eq 2 ] || exit 94
[ "$2" = "$recovery_node" ] || exit 95
recovery_sha256=$1
[ "$recovery_sha256" = "{EXPECTED_RECOVERY_SHA256}" ] || exit 96
printf '%s\n' \
    "uid=$uid" \
    "gid=$gid" \
    "context=$context" \
    "magisk_version=$magisk_version" \
    "magisk_version_code=$magisk_version_code" \
    "selinux=$selinux" \
    "pid1_exe=$pid1_exe" \
    "pid1_context=$pid1_context" \
    "recovery_size=$recovery_size" \
    "recovery_sha256=$recovery_sha256"
"""

ROOT_SHELL_ARGUMENT = shlex.quote(ROOT_READ_SCRIPT)
EXPECTED_ROOT_STDOUT = "".join(
    f"{key}={EXPECTED_ROOT_OUTPUT[key]}\n" for key in ROOT_OUTPUT_KEYS
).encode("utf-8")


class RecoveryDigestProfileError(RuntimeError):
    """The frozen read profile or its result violated a closed invariant."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def source_receipt() -> dict[str, Any]:
    path = Path(__file__).resolve()
    payload = path.read_bytes()
    return {
        "path": str(path),
        "size": len(payload),
        "sha256": sha256_bytes(payload),
    }


def parse_root_result(
    result: tuple[int, bytes, bytes],
) -> dict[str, str]:
    """Accept only the exact canonical stock-recovery result transcript."""

    if type(result) is not tuple or len(result) != 3:
        raise RecoveryDigestProfileError("root result envelope is malformed")
    returncode, stdout, stderr = result
    if type(returncode) is not int or type(stdout) is not bytes or type(stderr) is not bytes:
        raise RecoveryDigestProfileError("root result envelope types are invalid")
    if len(stdout) > MAX_ROOT_STDOUT_BYTES or len(stderr) > MAX_ROOT_STDERR_BYTES:
        raise RecoveryDigestProfileError("root result exceeds the fixed transcript bound")
    if returncode != 0:
        raise RecoveryDigestProfileError("fixed recovery digest command failed")
    if stderr != b"":
        raise RecoveryDigestProfileError("fixed recovery digest command wrote stderr")
    if stdout != EXPECTED_ROOT_STDOUT:
        raise RecoveryDigestProfileError("root result is not the exact stock transcript")
    return dict(EXPECTED_ROOT_OUTPUT)


def render_plan() -> dict[str, Any]:
    script_bytes = ROOT_READ_SCRIPT.encode("utf-8")
    argument_bytes = ROOT_SHELL_ARGUMENT.encode("utf-8")
    return {
        "schema": PLAN_SCHEMA,
        "version": VERSION,
        "status": "DORMANT_H0_REVIEW_PROFILE_NOT_ACTIVE",
        "verdict": DORMANT_VERDICT,
        "tier": "H0",
        "live_authorized": False,
        "profile_active": RECOVERY_DIGEST_PROFILE_ACTIVE,
        "current_contract_status": (
            "FORBIDDEN_UNTIL_COMMON_BOUNDARY_AND_S20PLUS_TARGET_ACTIVATION"
        ),
        "target": dict(EXPECTED_TARGET),
        "fixed_surface": {
            "recovery_link": FIXED_RECOVERY_LINK,
            "required_resolved_node": EXPECTED_RECOVERY_NODE,
            "required_node_type": "block",
            "expected_size": EXPECTED_RECOVERY_SIZE,
            "expected_sha256": EXPECTED_RECOVERY_SHA256,
            "caller_supplied_path": False,
            "returned_block_path": False,
            "node_live_confirmed": False,
            "node_h0_derivation": {
                "pit_name": PIT_NAME,
                "pit_size": PIT_SIZE,
                "pit_sha256": PIT_SHA256,
                "entry_index": PIT_RECOVERY_ENTRY_INDEX,
                "partition_name": "RECOVERY",
                "identifier": PIT_RECOVERY_IDENTIFIER,
                "block_offset": PIT_RECOVERY_BLOCK_OFFSET,
                "block_count": PIT_RECOVERY_BLOCK_COUNT,
                "block_bytes": PIT_BLOCK_BYTES,
                "block_count_times_block_bytes": (
                    PIT_RECOVERY_BLOCK_COUNT * PIT_BLOCK_BYTES
                ),
            },
        },
        "root_command": {
            "script_size": len(script_bytes),
            "script_sha256": sha256_bytes(script_bytes),
            "shell_argument_size": len(argument_bytes),
            "shell_argument_sha256": sha256_bytes(argument_bytes),
            "proposed_timeout_seconds": PROPOSED_ROOT_TIMEOUT_SECONDS,
            "stdout_maximum_bytes": MAX_ROOT_STDOUT_BYTES,
            "stderr_maximum_bytes": MAX_ROOT_STDERR_BYTES,
            "output_keys": list(ROOT_OUTPUT_KEYS),
            "expected_output": dict(EXPECTED_ROOT_OUTPUT),
            "expected_stdout_size": len(EXPECTED_ROOT_STDOUT),
            "expected_stdout_sha256": sha256_bytes(EXPECTED_ROOT_STDOUT),
        },
        "future_transport_shape": [
            "<PINNED_ADB>",
            "-s",
            "<EXACT_SELECTED_SERIAL>",
            "shell",
            "su",
            "-c",
            "<EXACT_ROOT_SHELL_ARGUMENT>",
        ],
        "planned_counts": {
            "root_command_count": 1,
            "partition_read_count": 1,
            "partition_write_count": 0,
            "partition_transfer_count": 0,
            "device_effect_count": 0,
            "reboot_count": 0,
            "adb_command_count_in_this_h0_module": 0,
            "su_command_count_in_this_h0_module": 0,
        },
        "required_future_owner_guards": [
            "fresh global ADB inventory and exactly one exact target",
            "serial topology current-boot and exact-build binding",
            "healthy rooted Android before and after the read",
            "pinned ADB and connected-runner source receipts",
            "bounded private no-clobber raw transcript publication",
            "no command to any other target",
            "independent review and mechanical activation",
        ],
        "source": source_receipt(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render or reject the dormant S20+ recovery digest profile"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--render-plan", action="store_true")
    mode.add_argument("--connected", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.render_plan:
        print(json.dumps(render_plan(), sort_keys=True, indent=2))
        return 0
    print(DORMANT_VERDICT)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
