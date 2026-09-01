#!/usr/bin/env python3
"""Host-only evidence parser and journal-prefix model for S20+ Q0.

This module cannot contact or control a device.  It strictly parses the fixed
backend capture and validates canonical intent-before-effect journal prefixes
so that a durable write intent consumes the sole backend attempt even when no
backend result exists.  Durable publication and every live/physical/recovery
owner remain separate, absent gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from typing import Any


SCHEMA = "s20plus_g986n_twrp_identical_resident_q0_evidence_h0_v1"
VERSION = "s20plus-g986n-twrp-identical-resident-q0-v1"
STATUS = "H0_PASS_GO_NOT_ACTIVE"
TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "incremental": "G986NKSS8IYC2",
}
BACKEND_H0_OWNER_BINDING_SHA256 = (
    "7b4aad4df0102da4c5119a83a9d50b246c788a9df3fec40e287c0a5b618b6e74"
)
BACKEND_SHA256 = "16271fee5c31ddb34e426b29ae5032e0fe366623eb3114862aac1ea1cc1022b5"
RESIDENT_SHA256 = "d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc"
TARGET_PATH = "/dev/block/sda23"
TARGET_RDEV = "259:7"
TARGET_PARTITION = 23
TARGET_SIZE = 67_108_864
STAGE_DIR = "/tmp/s20plus-g986n-identical-resident-q0"
BACKEND_NAME = "s20plus_twrp_boot_write_q0"
SOURCE_NAME = "resident-boot.img"
BACKEND_SIZE = 597_720
MAX_CAPTURE_BYTES = 4096
RUN_ID_RE = re.compile(r"run-[0-9]{19}")
HEX64_RE = re.compile(r"[0-9a-f]{64}")
DECIMAL_RE = re.compile(r"0|[1-9][0-9]*")
ZERO_HASH = "0" * 64

SUCCESS_KEYS = (
    "schema",
    "verdict",
    "target",
    "rdev",
    "partname",
    "partition",
    "size_bytes",
    "source_sha256",
    "preimage_sha256",
    "write_bytes",
    "fsync_succeeded",
    "readback_sha256",
    "write_attempts",
    "reboot_count",
    "other_partition_writes",
)
FAILURE_KEYS = (
    "schema",
    "verdict",
    "stage",
    "errno",
    "write_started",
    "write_bytes",
    "fsync_attempted",
    "fsync_succeeded",
    "reboot_count",
    "other_partition_writes",
)
PRE_WRITE_FAILURE_STAGES = {
    "arguments",
    "stage",
    "preimage-target-guard",
    "buffer",
    "source-hash",
    "preimage-hash",
    "preimage-close",
    "source-drift-before-write",
    "write-target-guard",
}
POST_FULL_WRITE_FAILURE_STAGES = {
    "write-fsync",
    "write-close",
    "source-drift-after-write",
    "readback-target-guard",
    "readback-hash",
}
FAILURE_STAGES = PRE_WRITE_FAILURE_STAGES | {"write"} | POST_FULL_WRITE_FAILURE_STAGES
JOURNAL_KINDS = (
    "prepared",
    "stage-intent",
    "stage-result",
    "write-intent",
    "backend-result",
)
NODE_KEYS = (
    "schema",
    "version",
    "run_id",
    "ordinal",
    "kind",
    "predecessor_sha256",
    "payload",
)


class EvidenceError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def digest(value: Any) -> str:
    return digest_bytes(canonical(value))


def exact_int(value: Any, minimum: int, maximum: int, label: str) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise EvidenceError(f"{label} differs")
    return value


def exact_bool(value: Any, expected: bool, label: str) -> None:
    if type(value) is not bool or value is not expected:
        raise EvidenceError(f"{label} differs")


def exact_hex(value: Any, label: str) -> str:
    if type(value) is not str or HEX64_RE.fullmatch(value) is None:
        raise EvidenceError(f"{label} differs")
    return value


def parse_decimal(value: str, maximum: int, label: str) -> int:
    if DECIMAL_RE.fullmatch(value) is None:
        raise EvidenceError(f"{label} is not canonical decimal")
    parsed = int(value, 10)
    if parsed > maximum:
        raise EvidenceError(f"{label} exceeds bound")
    return parsed


def ordered_fields(payload: bytes, keys: tuple[str, ...], label: str) -> dict[str, str]:
    if type(payload) is not bytes or not payload or len(payload) > MAX_CAPTURE_BYTES:
        raise EvidenceError(f"{label} byte bound differs")
    if b"\x00" in payload or b"\r" in payload or not payload.endswith(b"\n"):
        raise EvidenceError(f"{label} framing differs")
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as exc:
        raise EvidenceError(f"{label} is not ASCII") from exc
    lines = text[:-1].split("\n")
    if len(lines) != len(keys) or any(not line for line in lines):
        raise EvidenceError(f"{label} line count differs")
    result: dict[str, str] = {}
    for expected_key, line in zip(keys, lines, strict=True):
        key, separator, value = line.partition("=")
        if separator != "=" or key != expected_key or not value or key in result:
            raise EvidenceError(f"{label} ordered key differs")
        result[key] = value
    return result


def parse_success(stdout: bytes) -> dict[str, Any]:
    fields = ordered_fields(stdout, SUCCESS_KEYS, "Q0 success stdout")
    expected = {
        "schema": "s20plus_g986n_twrp_identical_resident_write_backend_v1",
        "verdict": "PROVED_IDENTICAL_RESIDENT_WRITE_READBACK",
        "target": TARGET_PATH,
        "rdev": TARGET_RDEV,
        "partname": "boot",
        "partition": str(TARGET_PARTITION),
        "size_bytes": str(TARGET_SIZE),
        "source_sha256": RESIDENT_SHA256,
        "preimage_sha256": RESIDENT_SHA256,
        "write_bytes": str(TARGET_SIZE),
        "fsync_succeeded": "1",
        "readback_sha256": RESIDENT_SHA256,
        "write_attempts": "1",
        "reboot_count": "0",
        "other_partition_writes": "0",
    }
    if fields != expected:
        raise EvidenceError("Q0 success semantics differ")
    return {
        "backend_verdict": fields["verdict"],
        "classification": "PROVED_IDENTICAL_RESIDENT_WRITE_READBACK",
        "write_started": True,
        "write_bytes": TARGET_SIZE,
        "fsync_attempted": True,
        "fsync_succeeded": True,
        "readback_proved": True,
        "boot_partition_effect_proved": True,
        "backend_replay_permitted": False,
    }


def parse_failure(stdout: bytes) -> dict[str, Any]:
    fields = ordered_fields(stdout, FAILURE_KEYS, "Q0 failure stdout")
    if (
        fields["schema"]
        != "s20plus_g986n_twrp_identical_resident_write_backend_v1"
        or fields["verdict"] != "STOP_IDENTICAL_RESIDENT_WRITE_QUALIFICATION"
        or fields["stage"] not in FAILURE_STAGES
        or fields["reboot_count"] != "0"
        or fields["other_partition_writes"] != "0"
    ):
        raise EvidenceError("Q0 failure semantics differ")
    error = parse_decimal(fields["errno"], 4095, "Q0 errno")
    if error == 0:
        raise EvidenceError("Q0 errno must be nonzero")
    write_started = parse_decimal(fields["write_started"], 1, "Q0 write_started")
    write_bytes = parse_decimal(fields["write_bytes"], TARGET_SIZE, "Q0 write_bytes")
    fsync_attempted = parse_decimal(
        fields["fsync_attempted"], 1, "Q0 fsync_attempted"
    )
    fsync_succeeded = parse_decimal(
        fields["fsync_succeeded"], 1, "Q0 fsync_succeeded"
    )
    if fsync_succeeded > fsync_attempted:
        raise EvidenceError("Q0 fsync success without attempt")
    if write_started == 0 and (write_bytes != 0 or fsync_attempted != 0):
        raise EvidenceError("Q0 zero-write failure counters differ")
    if write_started == 1 and fsync_attempted != 1:
        raise EvidenceError("Q0 started write lacks fsync attempt")
    stage = fields["stage"]
    if stage in PRE_WRITE_FAILURE_STAGES and (
        write_started != 0
        or write_bytes != 0
        or fsync_attempted != 0
        or fsync_succeeded != 0
    ):
        raise EvidenceError("Q0 pre-write stage reports a write")
    if stage in POST_FULL_WRITE_FAILURE_STAGES and (
        write_started != 1
        or write_bytes != TARGET_SIZE
        or fsync_attempted != 1
        or (stage != "write-fsync" and fsync_succeeded != 1)
    ):
        raise EvidenceError("Q0 post-write stage counters differ")
    classification = (
        "PRE_WRITE_REJECTED_ZERO_BOOT_EFFECT"
        if write_started == 0
        else "WRITE_EFFECT_OUTCOME_UNPROVED"
    )
    return {
        "backend_verdict": fields["verdict"],
        "classification": classification,
        "failure_stage": stage,
        "errno": error,
        "write_started": bool(write_started),
        "write_bytes": write_bytes,
        "fsync_attempted": bool(fsync_attempted),
        "fsync_succeeded": bool(fsync_succeeded),
        "readback_proved": False,
        "boot_partition_effect_proved": False,
        "backend_replay_permitted": False,
    }


def parse_backend_capture(returncode: int, stdout: bytes, stderr: bytes) -> dict[str, Any]:
    if type(returncode) is not int or type(stdout) is not bytes or type(stderr) is not bytes:
        raise EvidenceError("Q0 command capture types differ")
    if stderr != b"":
        raise EvidenceError("Q0 backend stderr is nonempty")
    if returncode == 0:
        parsed = parse_success(stdout)
    elif returncode == 70:
        parsed = parse_failure(stdout)
    else:
        raise EvidenceError("Q0 backend return code differs")
    return {
        "schema": SCHEMA,
        "command_returncode": returncode,
        "stdout_size": len(stdout),
        "stdout_sha256": digest_bytes(stdout),
        "stderr_size": 0,
        **parsed,
    }


def strict_node(payload: bytes) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise EvidenceError("Q0 journal node has duplicate key")
            result[key] = value
        return result

    def reject_constant(_value: str) -> Any:
        raise EvidenceError("Q0 journal node has non-finite number")

    if type(payload) is not bytes or not payload or len(payload) > 32 * 1024:
        raise EvidenceError("Q0 journal node byte bound differs")
    try:
        value = json.loads(
            payload,
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("Q0 journal node is malformed") from exc
    if type(value) is not dict or tuple(sorted(value)) != tuple(sorted(NODE_KEYS)):
        raise EvidenceError("Q0 journal node keys differ")
    if canonical(value) != payload:
        raise EvidenceError("Q0 journal node is not canonical bytes")
    return value


def make_node(
    run_id: str,
    ordinal: int,
    kind: str,
    predecessor_sha256: str,
    payload: dict[str, Any],
) -> bytes:
    return canonical(
        {
            "schema": SCHEMA,
            "version": VERSION,
            "run_id": run_id,
            "ordinal": ordinal,
            "kind": kind,
            "predecessor_sha256": predecessor_sha256,
            "payload": payload,
        }
    )


def exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise EvidenceError(f"{label} keys differ")
    return value


def validate_prepared(payload: Any) -> str:
    value = exact_keys(
        payload,
        {
            "target",
            "backend_h0_owner_binding_sha256",
            "serial_sha256",
            "topology_sha256",
            "recovery_boot_id_sha256",
            "prepared_at_ns",
            "expires_at_ns",
        },
        "Q0 prepared payload",
    )
    if (
        value["target"] != TARGET
        or value["backend_h0_owner_binding_sha256"]
        != BACKEND_H0_OWNER_BINDING_SHA256
    ):
        raise EvidenceError("Q0 prepared binding differs")
    for key in ("serial_sha256", "topology_sha256", "recovery_boot_id_sha256"):
        exact_hex(value[key], f"Q0 prepared {key}")
    prepared = exact_int(value["prepared_at_ns"], 1, 2**63 - 1, "Q0 prepared time")
    expires = exact_int(value["expires_at_ns"], 1, 2**63 - 1, "Q0 expiry")
    if expires <= prepared or expires - prepared > 15 * 60 * 1_000_000_000:
        raise EvidenceError("Q0 preparation lifetime differs")
    return value["recovery_boot_id_sha256"]


def validate_stage_intent(payload: Any) -> None:
    value = exact_keys(
        payload,
        {"attempt", "stage_dir", "backend_sha256", "resident_sha256"},
        "Q0 stage intent",
    )
    exact_int(value["attempt"], 1, 1, "Q0 stage attempt")
    if (
        value["stage_dir"] != STAGE_DIR
        or value["backend_sha256"] != BACKEND_SHA256
        or value["resident_sha256"] != RESIDENT_SHA256
    ):
        raise EvidenceError("Q0 stage intent binding differs")


def validate_stage_result(payload: Any) -> None:
    value = exact_keys(
        payload,
        {
            "attempt",
            "stage_dir",
            "child_names",
            "backend_size",
            "backend_sha256",
            "backend_mode",
            "resident_size",
            "resident_sha256",
            "resident_mode",
            "partition_effects",
        },
        "Q0 stage result",
    )
    exact_int(value["attempt"], 1, 1, "Q0 stage result attempt")
    exact_int(value["backend_size"], BACKEND_SIZE, BACKEND_SIZE, "Q0 backend size")
    exact_int(value["resident_size"], TARGET_SIZE, TARGET_SIZE, "Q0 resident size")
    exact_int(value["partition_effects"], 0, 0, "Q0 stage partition effects")
    if (
        value["stage_dir"] != STAGE_DIR
        or value["child_names"] != [BACKEND_NAME, SOURCE_NAME]
        or value["backend_sha256"] != BACKEND_SHA256
        or value["backend_mode"] != "0500"
        or value["resident_sha256"] != RESIDENT_SHA256
        or value["resident_mode"] != "0400"
    ):
        raise EvidenceError("Q0 stage result differs")


def validate_write_intent(payload: Any, prepared_boot_id_sha256: str) -> None:
    value = exact_keys(
        payload,
        {
            "attempt",
            "source_boot_id_sha256",
            "target_path",
            "rdev",
            "partname",
            "partition_number",
            "size_bytes",
            "preimage_sha256",
            "source_sha256",
            "backend_sha256",
            "backend_invocations_max",
            "replay_permitted",
        },
        "Q0 write intent",
    )
    exact_int(value["attempt"], 1, 1, "Q0 write attempt")
    exact_int(value["partition_number"], TARGET_PARTITION, TARGET_PARTITION, "Q0 partition")
    exact_int(value["size_bytes"], TARGET_SIZE, TARGET_SIZE, "Q0 target size")
    exact_int(value["backend_invocations_max"], 1, 1, "Q0 invocation maximum")
    exact_bool(value["replay_permitted"], False, "Q0 replay")
    source_boot_id_sha256 = exact_hex(
        value["source_boot_id_sha256"], "Q0 source boot"
    )
    if (
        source_boot_id_sha256 != prepared_boot_id_sha256
        or value["target_path"] != TARGET_PATH
        or value["rdev"] != TARGET_RDEV
        or value["partname"] != "boot"
        or value["preimage_sha256"] != RESIDENT_SHA256
        or value["source_sha256"] != RESIDENT_SHA256
        or value["backend_sha256"] != BACKEND_SHA256
    ):
        raise EvidenceError("Q0 write intent binding differs")


def validate_backend_result(
    payload: Any,
    capture: tuple[int, bytes, bytes] | None,
) -> dict[str, Any]:
    value = exact_keys(
        payload,
        {"attempt", "capture", "parsed"},
        "Q0 backend result",
    )
    exact_int(value["attempt"], 1, 1, "Q0 backend result attempt")
    if capture is None:
        raise EvidenceError("Q0 backend result lacks exact capture")
    parsed = parse_backend_capture(*capture)
    capture_value = exact_keys(
        value["capture"],
        {"returncode", "stdout_size", "stdout_sha256", "stderr_size"},
        "Q0 backend capture receipt",
    )
    expected_capture = {
        "returncode": parsed["command_returncode"],
        "stdout_size": parsed["stdout_size"],
        "stdout_sha256": parsed["stdout_sha256"],
        "stderr_size": 0,
    }
    if (
        canonical(capture_value) != canonical(expected_capture)
        or canonical(value["parsed"]) != canonical(parsed)
    ):
        raise EvidenceError("Q0 backend result capture or parse differs")
    return parsed


def validate_journal_prefix(
    nodes: list[bytes],
    *,
    backend_capture: tuple[int, bytes, bytes] | None = None,
) -> dict[str, Any]:
    if type(nodes) is not list or len(nodes) > len(JOURNAL_KINDS):
        raise EvidenceError("Q0 journal prefix length differs")
    if not nodes:
        if backend_capture is not None:
            raise EvidenceError("Q0 orphan backend capture")
        return {
            "state": "EMPTY_NO_AUTHORITY",
            "write_attempt_consumed": False,
            "backend_replay_permitted": False,
            "boot_partition_effect_proved": False,
            "system_boot_authorized_by_prefix": False,
        }
    previous_hash = ZERO_HASH
    run_id: str | None = None
    parsed_backend: dict[str, Any] | None = None
    prepared_boot_id_sha256: str | None = None
    for index, node_bytes in enumerate(nodes):
        node = strict_node(node_bytes)
        expected_kind = JOURNAL_KINDS[index]
        if (
            node["schema"] != SCHEMA
            or node["version"] != VERSION
            or type(node["run_id"]) is not str
            or RUN_ID_RE.fullmatch(node["run_id"]) is None
            or type(node["ordinal"]) is not int
            or node["ordinal"] != index + 1
            or node["kind"] != expected_kind
            or node["predecessor_sha256"] != previous_hash
        ):
            raise EvidenceError("Q0 journal chain differs")
        if run_id is None:
            run_id = node["run_id"]
        elif node["run_id"] != run_id:
            raise EvidenceError("Q0 journal run id changed")
        if index == 0:
            prepared_boot_id_sha256 = validate_prepared(node["payload"])
        elif index == 1:
            validate_stage_intent(node["payload"])
        elif index == 2:
            validate_stage_result(node["payload"])
        elif index == 3:
            if prepared_boot_id_sha256 is None:
                raise EvidenceError("Q0 prepared boot context is absent")
            validate_write_intent(node["payload"], prepared_boot_id_sha256)
        else:
            parsed_backend = validate_backend_result(node["payload"], backend_capture)
        previous_hash = digest_bytes(node_bytes)
    if len(nodes) < len(JOURNAL_KINDS) and backend_capture is not None:
        raise EvidenceError("Q0 capture exists without backend result node")
    if len(nodes) <= 3:
        state = "BEFORE_WRITE_INTENT_NO_BOOT_EFFECT"
        consumed = False
        proved = False
    elif len(nodes) == 4:
        state = "WRITE_OUTCOME_UNPROVED_ATTEMPT_CONSUMED_NO_REPLAY"
        consumed = True
        proved = False
    elif parsed_backend is not None and parsed_backend["boot_partition_effect_proved"]:
        state = "PROVED_BACKEND_WRITE_READBACK_PENDING_PHYSICAL_HEALTH"
        consumed = True
        proved = True
    elif parsed_backend is not None and not parsed_backend["write_started"]:
        state = "PRE_WRITE_REJECTION_AFTER_CONSUMED_INTENT_NO_REPLAY"
        consumed = True
        proved = False
    else:
        state = "WRITE_EFFECT_OUTCOME_UNPROVED_NO_REPLAY"
        consumed = True
        proved = False
    return {
        "state": state,
        "run_id": run_id,
        "node_count": len(nodes),
        "head_sha256": previous_hash,
        "write_attempt_consumed": consumed,
        "backend_replay_permitted": False,
        "boot_partition_effect_proved": proved,
        "system_boot_authorized_by_prefix": False,
    }


def render_plan() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "active": False,
        "live_authority": False,
        "target": TARGET,
        "backend_h0_owner_binding_sha256": BACKEND_H0_OWNER_BINDING_SHA256,
        "backend_sha256": BACKEND_SHA256,
        "parses": [
            "exact success capture",
            "exact bounded failure capture",
        ],
        "journal_prefix_kinds": list(JOURNAL_KINDS),
        "write_intent_consumes_attempt_without_result": True,
        "backend_replay_permitted": False,
        "system_boot_authorized": False,
        "durable_publisher_implemented": False,
        "connected_owner_implemented": False,
        "device_commands": [],
        "device_writes": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-plan", action="store_true")
    args = parser.parse_args()
    if not args.render_plan:
        parser.error("only --render-plan exists in H0 evidence model")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
