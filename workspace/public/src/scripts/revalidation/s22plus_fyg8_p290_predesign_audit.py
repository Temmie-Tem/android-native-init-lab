#!/usr/bin/env python3
"""Close the two P2.88 gaps required before the P2.90 park repair."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import s22plus_fyg8_p288_contract_spec as spec
import s22plus_fyg8_p288_e1_decoder as decoder
import s22plus_fyg8_p288_postlive_no_silent_park_audit as p288_audit
import s22plus_fyg8_p288_source_contract as source_contract


SCHEMA = "s22plus_fyg8_p290_predesign_audit_v1"
VERDICT = "PASS_P290_PARK_REPAIR_PREDESIGN_H0"
RUN_ID = "20bb4d70842fe7ae1a6bd0aec261d722"
RETAINED_SHA256 = (
    "34f5df7414b0c1f992372abe1c68e3d026da92d30e8a636e12ad3403998a4a34"
)
RESTART_HELPER_DISPATCH_ORDINAL = 88
RESTART_HELPER_DISPATCH_PAIR = (0x90, 0)

DEFAULT_INTENT = Path(
    "workspace/private/outputs/s22plus_fyg8_p288/intent/"
    "candidate-intent.json"
)
DEFAULT_CANDIDATE_STATIC = Path(
    "workspace/private/outputs/s22plus_fyg8_p288/process-v2/"
    "candidate-static.json"
)
DEFAULT_RETAINED_A = Path(
    "workspace/private/worktrees/p288-postbuild-linked-audit-v2/"
    "workspace/private/runs/device-action-f1-live-v2/"
    "f1-p288-ready1-1/rollback-observer-1.bin"
)
DEFAULT_RETAINED_B = Path(
    "workspace/private/worktrees/p288-postbuild-linked-audit-v2/"
    "workspace/private/runs/device-action-f1-live-v2/"
    "f1-p288-ready1-1/rollback-observer-2.bin"
)


class AuditError(ValueError):
    pass


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        value = json.loads(payload)
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is unavailable or invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} root is not an object")
    return value, payload


def repo_root() -> Path:
    return Path(
        subprocess.run(
            ("git", "rev-parse", "--show-toplevel"),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.strip()
    ).resolve()


def shared_root(root: Path) -> Path:
    common_dir = Path(
        subprocess.run(
            (
                "git",
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
            ),
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.strip()
    ).resolve()
    return common_dir.parent


def resolve_shared(root: Path, requested: Path) -> Path:
    if requested.is_absolute():
        return requested
    local = root / requested
    if local.is_file():
        return local
    shared = shared_root(root) / requested
    if not shared.is_file():
        raise AuditError(f"required shared input is absent: {requested}")
    return shared


def verify_receipt(path: Path, expected: dict[str, Any], label: str) -> bytes:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable: {exc}") from exc
    actual = receipt(payload)
    wanted = {"size": expected.get("size"), "sha256": expected.get("sha256")}
    if actual != wanted:
        raise AuditError(
            f"{label} receipt differs: expected={wanted} actual={actual}"
        )
    return payload


def frozen_sources(
    root: Path, intent_path: Path
) -> tuple[dict[str, Any], dict[str, bytes]]:
    intent_value, intent_payload = read_json(intent_path, "P2.88 intent")
    if (
        intent_value.get("run_id") != RUN_ID
        or intent_value.get("source_contract_id")
        != source_contract.CONTRACT_ID
    ):
        raise AuditError("P2.88 frozen identity differs")
    expected = intent_value.get("identity_preimage", {}).get("sources")
    if not isinstance(expected, dict) or len(expected) != 83:
        raise AuditError("P2.88 source receipt set is not exact 83")

    actual_sources = source_contract.source_bytes(shared_root(root))
    if set(actual_sources) != set(expected):
        raise AuditError("P2.88 source-key set differs")
    changed = tuple(
        key
        for key in sorted(expected)
        if receipt(actual_sources[key]) != expected[key]
    )
    if changed:
        raise AuditError(f"P2.88 frozen SOURCE_KEYS changed: {changed}")

    materialized: dict[str, bytes] = {}
    intent_dir = intent_path.parent
    entries = intent_value.get("materialized_sources")
    if not isinstance(entries, dict):
        raise AuditError("P2.88 materialized source map is absent")
    for key, entry in entries.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise AuditError(f"invalid materialized source entry: {key}")
        materialized[key] = verify_receipt(
            intent_dir / entry["path"], entry, f"materialized source {key}"
        )
    return {
        "intent": receipt(intent_payload),
        "source_key_count": len(expected),
        "source_keys_changed": list(changed),
        "materialized_source_count": len(materialized),
        "verified": True,
    }, materialized


def checkpoint_rows(checkpoint: bytes) -> tuple[tuple[int, int], ...]:
    start = checkpoint.index(
        b"static const struct s22_p248_step k_p248_e2_steps[] = {"
    )
    end = checkpoint.index(b"\n};", start)
    rows = tuple(
        (int(stage, 16), int(item, 10))
        for stage, item in re.findall(
            rb"\{0x([0-9a-fA-F]+)U, ([0-9]+)U, "
            rb"S22_P248_STEP_[A-Z]+\},",
            checkpoint[start:end],
        )
    )
    if rows != spec.POSITION_SEQUENCE:
        raise AuditError("materialized checkpoint position table differs")
    return rows


def audit_runtime_request(
    materialized: dict[str, bytes],
    root: Path,
    candidate_static_path: Path,
) -> dict[str, Any]:
    position = spec.POSITIONS[RESTART_HELPER_DISPATCH_ORDINAL]
    if (
        position.name != "restart_helper_dispatch"
        or position.pair != RESTART_HELPER_DISPATCH_PAIR
    ):
        raise AuditError("P2.88 restart-helper position spec differs")

    positions = materialized["p288_position_header"]
    match = re.search(
        rb"#define S22_P288_POSITION_RESTART_HELPER_DISPATCH ([0-9]+)U",
        positions,
    )
    if match is None or int(match.group(1)) != RESTART_HELPER_DISPATCH_ORDINAL:
        raise AuditError("restart-helper symbolic ordinal differs")

    runtime = materialized["p288_e3_runtime_include"]
    call = (
        b"p288_progress_position(\n"
        b"        S22_P288_POSITION_RESTART_HELPER_DISPATCH, 0U);"
    )
    if runtime.count(call) != 1:
        raise AuditError("restart-helper symbolic runtime call is not exact")

    checkpoint = materialized["checkpoint_client"]
    rows = checkpoint_rows(checkpoint)
    publish = source_contract._c_function_body(  # noqa: SLF001
        checkpoint, "p288_publish_next"
    )
    required_order = (
        b"size_t ordinal = client->generation;",
        b"(check_position && position_ordinal != ordinal)",
        b"const struct s22_p248_step *step = &k_p248_e2_steps[ordinal];",
        b"request.stage = step->stage;",
        b"request.item_index = step->item_index;",
        b"long written = sys_write(",
        b"client->generation = (uint8_t)(ordinal + 1U);",
    )
    offsets = tuple(publish.index(token) for token in required_order)
    if offsets != tuple(sorted(offsets)):
        raise AuditError("runtime request-construction order differs")

    formal = p288_audit.audit_postbuild_proof(
        root, candidate_static_path
    )
    if (
        formal["host_native_replay"]["checked_pairs"] != 6_815_744
        or formal["host_native_replay"]["accepted_pairs"] != 103
        or formal["linked_elf_table_proof_transitively_accepted"] is not True
    ):
        raise AuditError("formal linked validator proof differs")

    pair = rows[RESTART_HELPER_DISPATCH_ORDINAL]
    if pair != RESTART_HELPER_DISPATCH_PAIR:
        raise AuditError("runtime ordinal 88 does not select (0x90,0)")
    return {
        "symbolic_ordinal": RESTART_HELPER_DISPATCH_ORDINAL,
        "runtime_client_generation_required": 88,
        "linked_table_pair": list(pair),
        "request_stage": pair[0],
        "request_item_index": pair[1],
        "caller_encodes_wire_pair_directly": False,
        "request_pair_derived_from_generation_indexed_linked_table": True,
        "runtime_correct_request_construction_proved": True,
        "formal_validator_proof": formal,
        "verified": True,
    }


def decode_retained(path: Path) -> tuple[dict[str, Any], bytes]:
    payload = path.read_bytes()
    if receipt(payload)["sha256"] != RETAINED_SHA256:
        raise AuditError(f"retained read hash differs: {path}")
    decoded = decoder.classify_observation(
        payload,
        expected_profile=spec.PROFILE,
        expected_run_id=bytes.fromhex(RUN_ID),
    )
    if (
        decoded.get("classification") != "E2_PROGRESS_OBSERVED"
        or len(decoded.get("records", ())) != 1
    ):
        raise AuditError("retained read classification differs")
    return decoded["records"][0], payload


def audit_retained_slot_protocol(
    patch: bytes, retained_a: Path, retained_b: Path
) -> dict[str, Any]:
    record_a, payload_a = decode_retained(retained_a)
    record_b, payload_b = decode_retained(retained_b)
    if payload_a != payload_b or record_a != record_b:
        raise AuditError("the two retained reads differ")

    expected_slots = (
        {
            "slot_id": 1,
            "generation": 87,
            "stage": 0x8E,
            "outcome": 0,
            "item_index": 0,
            "detail": 0,
        },
        {
            "slot_id": 0,
            "generation": 88,
            "stage": 0x8F,
            "outcome": 0,
            "item_index": 0,
            "detail": 0xC18,
        },
    )
    if tuple(record_a["valid_slots"]) != expected_slots:
        raise AuditError("retained slot generations differ")
    if record_a["active"] != expected_slots[1]:
        raise AuditError("retained active slot differs")

    observer_offset = record_a["observer_offset"]
    raw_record = payload_a[observer_offset : observer_offset + 45]
    if len(raw_record) != 45:
        raise AuditError("retained record is truncated")
    slot1 = raw_record[35:45]
    slot1_commit_crc = slot1[6:10]
    if slot1_commit_crc == b"\0\0\0\0":
        raise AuditError("retained generation-87 slot CRC is clear")

    protocol = (
        b"next_slot = s22_fyg8_e1_state.active_slot ^ 1U;",
        b"memset(&record->slots[next_slot].commit_crc, 0,",
        b"memcpy(&record->slots[next_slot], &next,",
        b"memcpy(&record->slots[next_slot].commit_crc, &next.commit_crc,",
        b"memcmp(&record->slots[next_slot], &next, sizeof(next))",
        b"s22_fyg8_e1_state.active_slot = next_slot;",
    )
    offsets = tuple(patch.index(token) for token in protocol)
    if offsets != tuple(sorted(offsets)):
        raise AuditError("retained writer mutation order differs")

    writer_start = patch.rfind(
        b"+static ssize_t s22_fyg8_e1_write", 0, offsets[0]
    )
    writer_end = patch.find(b"\n+}", offsets[-1])
    writer = patch[writer_start:writer_end]
    if (
        writer_start < 0
        or writer_end < 0
        or writer.count(b"&head->buf[s22_fyg8_e1_state.proof_pos]") != 1
        or b"struct s22_fyg8_e1_record prospective;" not in writer
        or b"memcpy(&prospective, record, sizeof(prospective));" not in writer
        or b"__flush_dcache_area(&prospective" in writer
    ):
        raise AuditError("writer staging/storage shape differs")

    active_slot = record_a["active"]["slot_id"]
    gen89_target_slot = active_slot ^ 1
    if active_slot != 0 or gen89_target_slot != (89 & 1) or gen89_target_slot != 1:
        raise AuditError("generation-89 target slot derivation differs")
    return {
        "retained_read": receipt(payload_a),
        "reads_byte_identical": True,
        "observer_offset": observer_offset,
        "record_size": len(raw_record),
        "active_generation": 88,
        "active_slot": active_slot,
        "preserved_other_generation": 87,
        "preserved_other_slot": 1,
        "preserved_slot_commit_crc_nonzero": True,
        "generation_89_target_slot": gen89_target_slot,
        "separate_persistent_staging_region": False,
        "prospective_copy_is_stack_only": True,
        "first_persistent_target_mutation": "target-slot commit CRC clear",
        "generation_89_reached_target_crc_clear": False,
        "generation_89_postcommit_estale_rejected": True,
        "generation_88_postcommit_estale_rejected": False,
        "remaining_classes": [
            "publication nonreturn or returned error before generation-89 "
            "target mutation",
            "generation-88 primary publication error followed by fallback "
            "failure or nonreturn",
        ],
        "verified": True,
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    intent_path = resolve_shared(root, args.intent)
    candidate_static = resolve_shared(root, args.candidate_static)
    retained_a = resolve_shared(root, args.retained_a)
    retained_b = resolve_shared(root, args.retained_b)

    identity, materialized = frozen_sources(root, intent_path)
    intent_value, _ = read_json(intent_path, "P2.88 intent")
    patch_path = intent_path.parent / "candidate.patch"
    patch = verify_receipt(patch_path, intent_value["patch"], "P2.88 patch")

    runtime_request = audit_runtime_request(
        materialized, root, candidate_static
    )
    retained = audit_retained_slot_protocol(
        patch, retained_a, retained_b
    )
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "tier": "H0",
        "run_id": RUN_ID,
        "identity": identity,
        "runtime_request": runtime_request,
        "retained_slot_protocol": retained,
        "design_consequence": {
            "next_unit": "P2.90 publication park repair",
            "f1_authorized": False,
            "p288_rebuild_allowed": False,
            "p288_source_mutation_allowed": False,
            "persistent_single_channel_can_prove_its_own_total_failure": False,
            "repair_target": (
                "collapse fourteen attempt-only park routes into one "
                "explicit persistent-checkpoint-channel-failure sink"
            ),
        },
        "verified": True,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument(
        "--candidate-static", type=Path, default=DEFAULT_CANDIDATE_STATIC
    )
    parser.add_argument(
        "--retained-a", type=Path, default=DEFAULT_RETAINED_A
    )
    parser.add_argument(
        "--retained-b", type=Path, default=DEFAULT_RETAINED_B
    )
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        result = audit(args)
    except (AuditError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"FAIL_P290_PREDESIGN_AUDIT: {exc}", file=sys.stderr)
        return 1
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
