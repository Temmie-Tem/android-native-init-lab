#!/usr/bin/env python3
"""Dormant policy owner for a bounded autonomous S20+ research session."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SCHEMA = "s20plus_g986n_autonomous_research_h0_v1"
RESEARCH_ACTIVE = False
STATUS = "H0_AUTONOMOUS_RESEARCH_POLICY_PASS_GO_NOT_ACTIVE"

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "build": "G986NKSS8IYC2",
}

LIMITS = {
    "session_duration_sec": 4 * 60 * 60,
    "read_operations_max": 64,
    "private_evidence_bytes_max": 32 * 1024 * 1024,
    "single_command_output_bytes_max": 1024 * 1024,
    "control_transactions_max": 16,
    "component_effects_max": 24,
    "normal_reboots_max": 8,
    "download_roundtrips_max": 8,
}

CAMPAIGN_LIMITS = {
    "fresh_attended_opening_required": True,
    "campaign_duration_sec": 24 * 60 * 60,
    "read_operations_max": 256,
    "private_evidence_bytes_max": 128 * 1024 * 1024,
    "control_transactions_max": 64,
    "component_effects_max": 96,
    "normal_reboots_max": 32,
    "download_roundtrips_max": 32,
    "automatic_renewal": False,
    "terminal_resets_counters": False,
}

SOURCE_SPECS = {
    "inventory": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/s20plus_g986n_d0_inventory.py",
        "size": 21_474,
        "sha256": "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81",
    },
    "routine_d0": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/s20plus_g986n_routine_d0.py",
        "size": 12_649,
        "sha256": "2377e463e1ec4869fd9ba7a5155aeb6c792bdb5b5b969c902a2b0e5a00fda77c",
    },
    "routine_actions": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/s20plus_g986n_routine_actions.py",
        "size": 41_739,
        "sha256": "7b1d8989db5ffbf012cbf356e4e1411d5e487e965361b4ea61307a508b17bc72",
    },
    "download_exit": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/s20plus_g986n_download_exit_d1.py",
        "size": 34_025,
        "sha256": "72411a9e7983849dca0cbb3775f4f070c9642b9c8efb929fd519826e954b336a",
    },
}

READ_ACTIONS = (
    "public-health",
)
CONTROL_ACTIONS = (
    "reboot-system",
    "download-roundtrip",
)
ACTIONS = READ_ACTIONS + CONTROL_ACTIONS + ("prepare-f1-readiness",)

DEFERRED_ROOT_PROFILES = {
    "root-pid1-status": {
        "paths": {"/proc/1/status": "direct-regular-proc"},
        "status": "DEFERRED_NOT_AN_ACTION",
    },
    "root-pid1-mountinfo": {
        "paths": {"/proc/1/mountinfo": "direct-regular-proc"},
        "status": "DEFERRED_NOT_AN_ACTION",
    },
    "root-namespace-links": {
        "paths": {
            "/proc/1/ns/mnt": "direct-proc-symlink",
            "/proc/1/ns/pid": "direct-proc-symlink",
            "/proc/1/ns/uts": "direct-proc-symlink",
        },
        "status": "DEFERRED_NOT_AN_ACTION",
    },
    "root-selinux-enforce": {
        "paths": {"/sys/fs/selinux/enforce": "direct-regular-sysfs"},
        "status": "DEFERRED_NOT_AN_ACTION",
    },
    "root-magisk-metadata": {
        "paths": {
            "/data/adb/magisk/magisk": "direct-regular",
            "/data/adb/magisk/busybox": "direct-regular",
            "/data/adb/magisk/util_functions.sh": "direct-regular",
            "/data/adb/modules": "direct-directory",
            "/data/adb/modules_update": "direct-directory",
        },
        "status": "DEFERRED_NOT_AN_ACTION",
    },
}

ROOT_PROFILE_ACTIVATION_REQUIREMENTS = {
    "exact_root_launcher_and_transport_receipts": True,
    "fixed_command_timeout": True,
    "per_input_size_ceiling_before_read": True,
    "stable_no_follow_metadata_before_and_after": True,
    "directory_entry_count_and_name_grammar": True,
    "exact_parser_source_receipts": True,
    "hostile_cut_and_replacement_tests": True,
}

HASH_RE = re.compile(r"[0-9a-f]{64}\Z")


class ResearchPolicyError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def read_exact_source(spec: dict[str, Any], label: str) -> dict[str, Any]:
    path = spec["path"]
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise ResearchPolicyError(f"{label} source is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size != spec["size"]
        ):
            raise ResearchPolicyError(f"{label} source identity changed")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(descriptor, min(1024 * 1024, before.st_size - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != before.st_size or os.read(descriptor, 1):
            raise ResearchPolicyError(f"{label} source length changed")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity = lambda value: (
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
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if identity(before) != identity(after) or actual_sha256 != spec["sha256"]:
        raise ResearchPolicyError(f"{label} source bytes changed")
    return {
        "path": str(path),
        "size": before.st_size,
        "sha256": actual_sha256,
    }


def source_receipts() -> dict[str, Any]:
    return {
        label: read_exact_source(spec, label)
        for label, spec in sorted(SOURCE_SPECS.items())
    }


def validate_named_request(value: Any) -> str:
    if not isinstance(value, dict) or set(value) != {"action"}:
        raise ResearchPolicyError("research request must contain only action")
    action = value.get("action")
    if not isinstance(action, str) or action not in ACTIONS:
        raise ResearchPolicyError("research action is not allowlisted")
    return action


def validate_exact_identity(value: Any) -> dict[str, Any]:
    keys = {
        "target",
        "serial_sha256",
        "topology_sha256",
        "boot_id_sha256",
        "healthy_android",
        "foreign_guard_present",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise ResearchPolicyError("session identity schema differs")
    if value.get("target") != TARGET:
        raise ResearchPolicyError("session target differs")
    for key in ("serial_sha256", "topology_sha256", "boot_id_sha256"):
        field = value.get(key)
        if not isinstance(field, str) or HASH_RE.fullmatch(field) is None:
            raise ResearchPolicyError(f"{key} is invalid")
    if value.get("healthy_android") is not True:
        raise ResearchPolicyError("Android is not healthy")
    if value.get("foreign_guard_present") is not False:
        raise ResearchPolicyError("a foreign guard blocks the session")
    return value


COUNTER_KEYS = {
    "control_transactions",
    "component_effects_consumed",
    "component_effects_reserved",
    "normal_reboots",
    "download_roundtrips",
    "roundtrip_entries",
    "roundtrip_returns",
}


def validate_control_counters(
    counters: Any, limits: dict[str, Any]
) -> dict[str, int]:
    if (
        not isinstance(counters, dict)
        or set(counters) != COUNTER_KEYS
        or any(type(value) is not int or value < 0 for value in counters.values())
    ):
        raise ResearchPolicyError("control counters are malformed")
    value = dict(counters)
    unresolved = value["roundtrip_entries"] - value["roundtrip_returns"]
    if (
        value["download_roundtrips"] != value["roundtrip_entries"]
        or unresolved not in (0, 1)
        or value["component_effects_reserved"] != unresolved
        or value["control_transactions"]
        != value["normal_reboots"] + value["download_roundtrips"]
        or value["component_effects_consumed"]
        != value["normal_reboots"]
        + value["roundtrip_entries"]
        + value["roundtrip_returns"]
    ):
        raise ResearchPolicyError("control counter relationships are invalid")
    checks = {
        "control_transactions": "control_transactions_max",
        "normal_reboots": "normal_reboots_max",
        "download_roundtrips": "download_roundtrips_max",
    }
    total_effects = (
        value["component_effects_consumed"]
        + value["component_effects_reserved"]
    )
    if (
        total_effects > limits["component_effects_max"]
        or any(value[counter] > limits[maximum] for counter, maximum in checks.items())
    ):
        raise ResearchPolicyError("control budget is exhausted")
    return value


def debit_before_intent(
    counters: Any, action: str, component: str, limits: dict[str, Any]
) -> dict[str, int]:
    value = validate_control_counters(counters, limits)
    if action == "reboot-system" and component == "reboot":
        if value["roundtrip_entries"] != value["roundtrip_returns"]:
            raise ResearchPolicyError("a Download roundtrip is unresolved")
        value["control_transactions"] += 1
        value["component_effects_consumed"] += 1
        value["normal_reboots"] += 1
    elif action == "download-roundtrip" and component == "entry":
        if value["roundtrip_entries"] != value["roundtrip_returns"]:
            raise ResearchPolicyError("a Download roundtrip is already unresolved")
        value["control_transactions"] += 1
        value["component_effects_consumed"] += 1
        value["component_effects_reserved"] += 1
        value["download_roundtrips"] += 1
        value["roundtrip_entries"] += 1
    elif action == "download-roundtrip" and component == "return":
        if (
            value["roundtrip_entries"] != value["roundtrip_returns"] + 1
            or value["component_effects_reserved"] < 1
        ):
            raise ResearchPolicyError("no unmatched Download entry exists")
        value["component_effects_reserved"] -= 1
        value["component_effects_consumed"] += 1
        value["roundtrip_returns"] += 1
    else:
        raise ResearchPolicyError("control component is not allowlisted")
    return validate_control_counters(value, limits)


LIVE_COORDINATOR_REQUIREMENTS = {
    "fixed_private_campaign_guard_path": True,
    "bounded_no_follow_canonical_duplicate_safe_reads": True,
    "derive_campaign_session_policy_source_and_ordinal_from_current_guard": True,
    "derive_endpoint_from_current_validated_arrival": True,
    "hash_actual_validated_predecessor_bytes": True,
    "validate_full_opening_entry_arrival_return_chain": True,
    "ordinal_equals_current_campaign_roundtrip_count": True,
    "exact_child_membership_in_current_campaign": True,
    "atomic_both_scope_counters_and_intent": True,
    "debit_only_or_partial_scope_has_zero_authority": True,
    "expiry_recovery_only_from_current_guard_chain": True,
    "hostile_old_foreign_duplicate_noncanonical_and_cut_fixtures": True,
}


def binding_value() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "target": TARGET,
        "sources": source_receipts(),
        "actions": {
            "read_only": list(READ_ACTIONS),
            "control": list(CONTROL_ACTIONS),
            "pre_f1_terminal": "prepare-f1-readiness",
        },
        "deferred_root_profiles": DEFERRED_ROOT_PROFILES,
        "root_profile_activation_requirements": ROOT_PROFILE_ACTIVATION_REQUIREMENTS,
        "live_coordinator_requirements": LIVE_COORDINATOR_REQUIREMENTS,
        "limits": LIMITS,
        "campaign_limits": CAMPAIGN_LIMITS,
        "campaign_accounting": {
            "one_durable_allocation": True,
            "child_sessions_debit_monotonically": True,
            "expiry_or_terminal_never_resets": True,
            "new_campaign_requires_fresh_attended_opening": True,
            "roundtrip_debits_one_transaction_and_two_component_effects": True,
            "entry_debits_entry_and_reserves_return_before_entry_intent": True,
            "return_intent_converts_reservation_without_new_capacity": True,
            "reserved_return_survives_expiry_for_recovery_only": True,
            "expiry_never_allows_new_baseline_entry_or_transaction": True,
            "child_campaign_counters_and_intent_publish_as_one_atomic_node": True,
            "recovery_binds_campaign_session_ordinal_source_endpoint_predecessor": True,
        },
        "privacy": {
            "raw_output": "workspace/private/session-only",
            "public_output": "sanitized-hashes-and-conclusions-only",
            "caller_path": False,
            "caller_shell": False,
        },
        "stop_conditions": [
            "disconnect",
            "unowned-boot-change",
            "target-build-topology-or-source-drift",
            "unhealthy-android",
            "foreign-or-unresolved-guard",
            "ambiguous-endpoint",
            "budget-exhaustion",
            "uncertain-mode-transition",
        ],
        "pre_f1_boundary": {
            "healthy_normal_android": True,
            "f1_intent": False,
            "download_entry_for_f1": False,
            "approval_consumed": False,
            "partition_transfer": False,
        },
    }


def render_plan() -> dict[str, Any]:
    binding = binding_value()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "active": RESEARCH_ACTIVE,
        "policy_owner_permanently_render_only": True,
        "live_authority": False,
        "binding_sha256": digest(binding),
        "binding": binding,
        "cli": ["--render-plan"],
        "device_commands": [],
        "root_commands": [],
        "device_effects": [],
        "partition_transfers": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-plan", action="store_true")
    args = parser.parse_args()
    if not args.render_plan:
        parser.error("only --render-plan exists while the session owner is dormant")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
