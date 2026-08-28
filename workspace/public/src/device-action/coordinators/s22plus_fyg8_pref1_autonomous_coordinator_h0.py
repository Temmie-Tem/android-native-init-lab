#!/usr/bin/env python3
"""Inactive host-only state core for the S22+ pre-F1 catalog.

This module models activation, aggregate debit, healthy return, and uncertain
park semantics.  It has no device transport, durable journal, action executor,
or activation entry point.  The only CLI operation renders the dormant plan.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
POLICY_PATH = (
    ROOT
    / "docs/operations/targets/"
    "S22PLUS_FYG8_PREF1_AUTONOMOUS_RESEARCH_POLICY_V1.md"
)

SCHEMA = "s22plus_fyg8_pref1_autonomous_coordinator_h0_v1"
ACTIVATION_SCHEMA = "s22plus_fyg8_pref1_activation_manifest_v1"
CAMPAIGN_SCHEMA = "s22plus_fyg8_pref1_campaign_state_v1"
INTENT_SCHEMA = "s22plus_fyg8_pref1_effect_intent_v1"
RESULT_SCHEMA = "s22plus_fyg8_pref1_effect_result_v1"
STATUS = "H0_PREF1_AUTONOMOUS_COORDINATOR_NOT_ACTIVE"

COORDINATOR_ACTIVE = False
LIVE_AUTHORITY = False
DEVICE_ACTION_INTEGRATION = False
DURABLE_JOURNAL_INTEGRATION = False

TARGET = {
    "model": "SM-S906N",
    "device": "g0q",
    "build": "S906NKSS7FYG8",
}
ACTION_TIERS = {
    "bounded_raw_first_read": "D0",
    "normal_android_reboot_health": "D1",
    "payload_free_download_roundtrip": "D1",
    "fixed_privileged_usb_role_or_udc_transient": "D1",
}
PROOF_MODES = {
    "bounded_raw_first_read": frozenset({"same_boot_observation"}),
    "normal_android_reboot_health": frozenset({"new_boot_health"}),
    "payload_free_download_roundtrip": frozenset({"new_boot_health"}),
    "fixed_privileged_usb_role_or_udc_transient": frozenset(
        {"same_boot_restore", "reboot_restore_health"}
    ),
}
DEFAULT_PROOF_MODES = {
    class_id: sorted(modes)[0] for class_id, modes in PROOF_MODES.items()
}
SAME_BOOT_PROOF_MODES = frozenset({"same_boot_observation", "same_boot_restore"})
NEW_BOOT_PROOF_MODES = frozenset({"new_boot_health", "reboot_restore_health"})
PARK_REASONS = frozenset(
    {"host_cut", "identity_ambiguous", "health_missing", "result_uncertain"}
)
PRE_INTENT_FAILURES = frozenset(
    {"host_input_invalid", "host_resource_unavailable", "preflight_rejected"}
)

CAMPAIGN_DURATION_SECONDS = 43_200
D1_EFFECT_MAX = 8
D0_COMMAND_GROUP_MAX = 256
MAX_MANIFEST_BYTES = 32 * 1024
HEX32 = re.compile(r"[0-9a-f]{32}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class CoordinatorModelError(RuntimeError):
    """A malformed or disallowed model transition fails closed."""


def canonical_bytes(value: Any) -> bytes:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CoordinatorModelError("value is not canonical JSON") from exc
    return (encoded + "\n").encode("utf-8")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CoordinatorModelError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def strict_json_bytes(raw: bytes, *, maximum: int = MAX_MANIFEST_BYTES) -> Any:
    if type(raw) is not bytes or not 0 < len(raw) <= maximum:
        raise CoordinatorModelError("JSON byte extent is invalid")
    try:
        text = raw.decode("utf-8", "strict")
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                CoordinatorModelError(f"non-finite JSON value: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CoordinatorModelError("JSON is not strict UTF-8") from exc
    if canonical_bytes(value) != raw:
        raise CoordinatorModelError("JSON is not canonical")
    return value


def _exact_mapping(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise CoordinatorModelError(f"{label} shape differs")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise CoordinatorModelError(f"{label} is not a canonical integer")
    return value


def _hex(value: Any, pattern: re.Pattern[str], label: str) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise CoordinatorModelError(f"{label} is not canonical lowercase hex")
    return value


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _decode_policy(text: str) -> dict[str, Any]:
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if len(blocks) != 1:
        raise CoordinatorModelError("policy must contain one JSON declaration")
    try:
        policy = json.loads(blocks[0], object_pairs_hook=_pairs)
    except json.JSONDecodeError as exc:
        raise CoordinatorModelError("policy declaration is invalid") from exc
    _exact_mapping(
        policy,
        {
            "schema",
            "status",
            "target",
            "activation",
            "campaign",
            "catalog",
            "effect_accounting",
            "repair",
            "evidence",
            "forbidden",
        },
        "policy",
    )
    if policy["schema"] != "s22plus_fyg8_pre_f1_autonomous_action_catalog_v1":
        raise CoordinatorModelError("policy schema differs")
    if policy["status"] != "DEFINED_NOT_ACTIVE":
        raise CoordinatorModelError("policy is not dormant")
    if policy["target"] != {**TARGET, "other_target_commands": 0}:
        raise CoordinatorModelError("policy target differs")
    campaign = policy["campaign"]
    expected_limits = {
        "d1_effect_max": D1_EFFECT_MAX,
        "d1_effect_max_scope": "aggregate_per_campaign",
        "d0_command_group_max": D0_COMMAND_GROUP_MAX,
        "d0_command_group_max_scope": "aggregate_per_campaign",
        "duration_seconds": CAMPAIGN_DURATION_SECONDS,
        "exclusive_campaign_guard": "required_single_coordinator",
        "intent_publication": "atomic_no_replace",
    }
    for key, expected in expected_limits.items():
        if campaign.get(key) != expected:
            raise CoordinatorModelError(f"policy campaign field differs: {key}")
    classes = policy["catalog"].get("classes")
    if type(classes) is not list or len(classes) != len(ACTION_TIERS):
        raise CoordinatorModelError("policy class count differs")
    observed = {item.get("id"): item.get("tier") for item in classes if type(item) is dict}
    if observed != ACTION_TIERS:
        raise CoordinatorModelError("policy action classes differ")
    if policy["catalog"].get("android_recovery_entry") != (
        "not_in_catalog_ordinary_attended_d1"
    ):
        raise CoordinatorModelError("policy Recovery boundary differs")
    return policy


def current_binding() -> dict[str, Any]:
    policy_raw = POLICY_PATH.read_bytes()
    try:
        policy_text = policy_raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise CoordinatorModelError("policy is not UTF-8") from exc
    policy = _decode_policy(policy_text)
    source_raw = Path(__file__).resolve().read_bytes()
    return {
        "policy": {"size": len(policy_raw), "sha256": _sha256(policy_raw)},
        "coordinator": {"size": len(source_raw), "sha256": _sha256(source_raw)},
        "catalog_sha256": _sha256(canonical_bytes(policy["catalog"])),
    }


ACTIVATION_KEYS = {
    "schema",
    "campaign_id",
    "target",
    "policy_sha256",
    "coordinator_sha256",
    "catalog_sha256",
    "effect_core_sha256",
    "topology_sha256",
    "boot_id_sha256",
    "opened_at_epoch",
    "expires_at_epoch",
    "d1_effect_max",
    "d0_command_group_max",
    "independent_pass_go_sha256",
    "live_session_approval_sha256",
    "operator_attended_opening",
}


def parse_activation_manifest(raw: bytes, *, now: int) -> dict[str, Any]:
    manifest = _exact_mapping(strict_json_bytes(raw), ACTIVATION_KEYS, "activation")
    _integer(now, "now")
    if manifest["schema"] != ACTIVATION_SCHEMA or manifest["target"] != TARGET:
        raise CoordinatorModelError("activation identity differs")
    _hex(manifest["campaign_id"], HEX32, "campaign_id")
    for key in (
        "policy_sha256",
        "coordinator_sha256",
        "catalog_sha256",
        "effect_core_sha256",
        "topology_sha256",
        "boot_id_sha256",
        "independent_pass_go_sha256",
        "live_session_approval_sha256",
    ):
        _hex(manifest[key], HEX64, key)
    opened = _integer(manifest["opened_at_epoch"], "opened_at_epoch")
    expires = _integer(manifest["expires_at_epoch"], "expires_at_epoch")
    if expires - opened != CAMPAIGN_DURATION_SECONDS or not opened <= now < expires:
        raise CoordinatorModelError("activation time window differs")
    if type(manifest["operator_attended_opening"]) is not bool or not manifest[
        "operator_attended_opening"
    ]:
        raise CoordinatorModelError("opening is not attended")
    if manifest["d1_effect_max"] != D1_EFFECT_MAX:
        raise CoordinatorModelError("D1 budget differs")
    if manifest["d0_command_group_max"] != D0_COMMAND_GROUP_MAX:
        raise CoordinatorModelError("D0 budget differs")
    binding = current_binding()
    if manifest["policy_sha256"] != binding["policy"]["sha256"]:
        raise CoordinatorModelError("policy identity differs")
    if manifest["coordinator_sha256"] != binding["coordinator"]["sha256"]:
        raise CoordinatorModelError("coordinator identity differs")
    if manifest["catalog_sha256"] != binding["catalog_sha256"]:
        raise CoordinatorModelError("catalog identity differs")
    return manifest


def model_campaign_open(raw: bytes, *, now: int) -> dict[str, Any]:
    manifest = parse_activation_manifest(raw, now=now)
    return {
        "schema": CAMPAIGN_SCHEMA,
        "campaign_id": manifest["campaign_id"],
        "target": deepcopy(TARGET),
        "phase": "OPEN_HEALTHY",
        "opened_at_epoch": manifest["opened_at_epoch"],
        "expires_at_epoch": manifest["expires_at_epoch"],
        "activation_sha256": _sha256(raw),
        "policy_sha256": manifest["policy_sha256"],
        "coordinator_sha256": manifest["coordinator_sha256"],
        "catalog_sha256": manifest["catalog_sha256"],
        "effect_core_sha256": manifest["effect_core_sha256"],
        "topology_sha256": manifest["topology_sha256"],
        "boot_id_sha256": manifest["boot_id_sha256"],
        "d1_effect_max": D1_EFFECT_MAX,
        "d0_command_group_max": D0_COMMAND_GROUP_MAX,
        "d1_effects_used": 0,
        "d0_command_groups_used": 0,
        "next_ordinal": 1,
        "active_intent": None,
    }


STATE_KEYS = {
    "schema",
    "campaign_id",
    "target",
    "phase",
    "opened_at_epoch",
    "expires_at_epoch",
    "activation_sha256",
    "policy_sha256",
    "coordinator_sha256",
    "catalog_sha256",
    "effect_core_sha256",
    "topology_sha256",
    "boot_id_sha256",
    "d1_effect_max",
    "d0_command_group_max",
    "d1_effects_used",
    "d0_command_groups_used",
    "next_ordinal",
    "active_intent",
}

INTENT_KEYS = {
    "schema",
    "campaign_id",
    "ordinal",
    "class_id",
    "tier",
    "proof_mode",
    "source_boot_id_sha256",
    "effect_core_sha256",
    "d1_effects_used_after",
    "d0_command_groups_used_after",
    "status",
    "intent_at_epoch",
}


def _validate_intent(intent: Any, state: Mapping[str, Any]) -> dict[str, Any]:
    value = _exact_mapping(intent, INTENT_KEYS, "effect intent")
    if value["schema"] != INTENT_SCHEMA:
        raise CoordinatorModelError("effect intent schema differs")
    if value["campaign_id"] != state["campaign_id"]:
        raise CoordinatorModelError("effect intent campaign differs")
    ordinal = _integer(value["ordinal"], "effect intent ordinal", minimum=1)
    if ordinal != state["next_ordinal"] - 1:
        raise CoordinatorModelError("effect intent ordinal differs")
    class_id = value["class_id"]
    if type(class_id) is not str or ACTION_TIERS.get(class_id) != value["tier"]:
        raise CoordinatorModelError("effect intent class differs")
    if value["proof_mode"] not in PROOF_MODES[class_id]:
        raise CoordinatorModelError("effect intent proof mode differs")
    if value["source_boot_id_sha256"] != state["boot_id_sha256"]:
        raise CoordinatorModelError("effect intent source boot differs")
    if value["effect_core_sha256"] != state["effect_core_sha256"]:
        raise CoordinatorModelError("effect intent core differs")
    intent_at = _integer(value["intent_at_epoch"], "effect intent time")
    if not state["opened_at_epoch"] <= intent_at < state["expires_at_epoch"]:
        raise CoordinatorModelError("effect intent time differs")
    if value["d1_effects_used_after"] != state["d1_effects_used"]:
        raise CoordinatorModelError("effect intent D1 debit differs")
    if value["d0_command_groups_used_after"] != state["d0_command_groups_used"]:
        raise CoordinatorModelError("effect intent D0 debit differs")
    if value["status"] != "CONSUMED_UNDISPATCHED":
        raise CoordinatorModelError("effect intent status differs")
    return value


def _validate_state(state: Any) -> dict[str, Any]:
    value = _exact_mapping(state, STATE_KEYS, "campaign state")
    if value["schema"] != CAMPAIGN_SCHEMA or value["target"] != TARGET:
        raise CoordinatorModelError("campaign state identity differs")
    _hex(value["campaign_id"], HEX32, "campaign_id")
    for key in (
        "activation_sha256",
        "policy_sha256",
        "coordinator_sha256",
        "catalog_sha256",
        "effect_core_sha256",
        "topology_sha256",
        "boot_id_sha256",
    ):
        _hex(value[key], HEX64, key)
    for key in (
        "opened_at_epoch",
        "expires_at_epoch",
        "d1_effect_max",
        "d0_command_group_max",
        "d1_effects_used",
        "d0_command_groups_used",
        "next_ordinal",
    ):
        _integer(value[key], key, minimum=1 if key == "next_ordinal" else 0)
    if value["d1_effect_max"] != D1_EFFECT_MAX:
        raise CoordinatorModelError("campaign D1 budget differs")
    if value["d0_command_group_max"] != D0_COMMAND_GROUP_MAX:
        raise CoordinatorModelError("campaign D0 budget differs")
    if value["expires_at_epoch"] - value["opened_at_epoch"] != CAMPAIGN_DURATION_SECONDS:
        raise CoordinatorModelError("campaign expiry differs")
    if not 0 <= value["d1_effects_used"] <= D1_EFFECT_MAX:
        raise CoordinatorModelError("campaign D1 counter differs")
    if not 0 <= value["d0_command_groups_used"] <= D0_COMMAND_GROUP_MAX:
        raise CoordinatorModelError("campaign D0 counter differs")
    if value["next_ordinal"] != (
        value["d1_effects_used"] + value["d0_command_groups_used"] + 1
    ):
        raise CoordinatorModelError("campaign ordinal counter differs")
    binding = current_binding()
    if value["policy_sha256"] != binding["policy"]["sha256"]:
        raise CoordinatorModelError("campaign policy identity differs")
    if value["coordinator_sha256"] != binding["coordinator"]["sha256"]:
        raise CoordinatorModelError("campaign coordinator identity differs")
    if value["catalog_sha256"] != binding["catalog_sha256"]:
        raise CoordinatorModelError("campaign catalog identity differs")
    if value["phase"] not in {"OPEN_HEALTHY", "EFFECT_INTENT_DURABLE", "PARKED", "CLOSED"}:
        raise CoordinatorModelError("campaign phase differs")
    if value["phase"] in {"OPEN_HEALTHY", "CLOSED"}:
        if value["active_intent"] is not None:
            raise CoordinatorModelError("campaign active intent differs")
    elif value["active_intent"] is None:
        raise CoordinatorModelError("campaign active intent is absent")
    else:
        _validate_intent(value["active_intent"], value)
    return value


OBSERVED_KEYS = {"target", "topology_sha256", "boot_id_sha256", "healthy_android"}


def _validate_observed(observed: Any, state: Mapping[str, Any]) -> dict[str, Any]:
    value = _exact_mapping(observed, OBSERVED_KEYS, "observed identity")
    if value["target"] != TARGET or value["topology_sha256"] != state["topology_sha256"]:
        raise CoordinatorModelError("observed target or topology differs")
    _hex(value["boot_id_sha256"], HEX64, "observed boot_id_sha256")
    if type(value["healthy_android"]) is not bool or not value["healthy_android"]:
        raise CoordinatorModelError("observed Android is not healthy")
    return value


def model_pre_intent_failure(
    state: Mapping[str, Any], *, reason: str
) -> dict[str, Any]:
    value = _validate_state(state)
    if (
        value["phase"] != "OPEN_HEALTHY"
        or type(reason) is not str
        or reason not in PRE_INTENT_FAILURES
    ):
        raise CoordinatorModelError("pre-intent failure is unavailable")
    return deepcopy(value)


def model_effect_intent(
    state: Mapping[str, Any],
    *,
    class_id: str,
    proof_mode: str,
    observed: Mapping[str, Any],
    now: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    value = _validate_state(state)
    _integer(now, "now")
    if value["phase"] != "OPEN_HEALTHY" or value["active_intent"] is not None:
        raise CoordinatorModelError("another effect is open")
    if not value["opened_at_epoch"] <= now < value["expires_at_epoch"]:
        raise CoordinatorModelError("campaign is expired")
    if type(class_id) is not str or class_id not in ACTION_TIERS:
        raise CoordinatorModelError("action class is not in the catalog")
    if type(proof_mode) is not str or proof_mode not in PROOF_MODES[class_id]:
        raise CoordinatorModelError("proof mode is not allowed for the class")
    current = _validate_observed(observed, value)
    if current["boot_id_sha256"] != value["boot_id_sha256"]:
        raise CoordinatorModelError("pre-intent boot identity differs")
    next_state = deepcopy(value)
    tier = ACTION_TIERS[class_id]
    if tier == "D0":
        if next_state["d0_command_groups_used"] >= D0_COMMAND_GROUP_MAX:
            raise CoordinatorModelError("aggregate D0 budget is exhausted")
        next_state["d0_command_groups_used"] += 1
    else:
        if next_state["d1_effects_used"] >= D1_EFFECT_MAX:
            raise CoordinatorModelError("aggregate D1 budget is exhausted")
        next_state["d1_effects_used"] += 1
    intent = {
        "schema": INTENT_SCHEMA,
        "campaign_id": value["campaign_id"],
        "ordinal": value["next_ordinal"],
        "class_id": class_id,
        "tier": tier,
        "proof_mode": proof_mode,
        "source_boot_id_sha256": value["boot_id_sha256"],
        "effect_core_sha256": value["effect_core_sha256"],
        "intent_at_epoch": now,
        "d1_effects_used_after": next_state["d1_effects_used"],
        "d0_command_groups_used_after": next_state["d0_command_groups_used"],
        "status": "CONSUMED_UNDISPATCHED",
    }
    next_state["phase"] = "EFFECT_INTENT_DURABLE"
    next_state["active_intent"] = deepcopy(intent)
    next_state["next_ordinal"] += 1
    return next_state, intent


def _match_active_intent(state: Mapping[str, Any], intent: Mapping[str, Any]) -> None:
    if state["phase"] != "EFFECT_INTENT_DURABLE":
        raise CoordinatorModelError("effect result is unavailable")
    candidate = _validate_intent(intent, state)
    if canonical_bytes(state["active_intent"]) != canonical_bytes(candidate):
        raise CoordinatorModelError("intent does not match the active ordinal")


def model_healthy_return(
    state: Mapping[str, Any],
    *,
    intent: Mapping[str, Any],
    observed: Mapping[str, Any],
    now: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    value = _validate_state(state)
    _integer(now, "now")
    if now < value["opened_at_epoch"]:
        raise CoordinatorModelError("effect result predates the campaign")
    _match_active_intent(value, intent)
    if now < intent["intent_at_epoch"]:
        raise CoordinatorModelError("effect result predates intent")
    current = _validate_observed(observed, value)
    class_id = intent.get("class_id")
    changed = current["boot_id_sha256"] != value["boot_id_sha256"]
    proof_mode = intent["proof_mode"]
    if proof_mode in NEW_BOOT_PROOF_MODES and not changed:
        raise CoordinatorModelError("new-boot proof reused its source boot")
    if proof_mode in SAME_BOOT_PROOF_MODES and changed:
        raise CoordinatorModelError("same-boot proof changed boot identity")
    result = {
        "schema": RESULT_SCHEMA,
        "campaign_id": value["campaign_id"],
        "ordinal": intent["ordinal"],
        "class_id": class_id,
        "proof_mode": proof_mode,
        "status": "HEALTHY_RETURN",
        "boot_id_sha256": current["boot_id_sha256"],
    }
    next_state = deepcopy(value)
    next_state["phase"] = "OPEN_HEALTHY"
    next_state["active_intent"] = None
    next_state["boot_id_sha256"] = current["boot_id_sha256"]
    return next_state, result


def model_uncertain_cut(
    state: Mapping[str, Any],
    *,
    intent: Mapping[str, Any],
    reason: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    value = _validate_state(state)
    _match_active_intent(value, intent)
    if type(reason) is not str or reason not in PARK_REASONS:
        raise CoordinatorModelError("park reason is not closed")
    next_state = deepcopy(value)
    next_state["phase"] = "PARKED"
    result = {
        "schema": RESULT_SCHEMA,
        "campaign_id": value["campaign_id"],
        "ordinal": intent["ordinal"],
        "class_id": intent["class_id"],
        "proof_mode": intent["proof_mode"],
        "status": "UNCERTAIN_CONSUMED_NO_REPLAY",
        "reason": reason,
    }
    return next_state, result


def model_close(state: Mapping[str, Any]) -> dict[str, Any]:
    value = _validate_state(state)
    if value["phase"] != "OPEN_HEALTHY" or value["active_intent"] is not None:
        raise CoordinatorModelError("campaign cannot close with an open effect")
    next_state = deepcopy(value)
    next_state["phase"] = "CLOSED"
    return next_state


def render_plan() -> dict[str, Any]:
    policy = _decode_policy(POLICY_PATH.read_text(encoding="utf-8"))
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "active": COORDINATOR_ACTIVE,
        "live_authority": LIVE_AUTHORITY,
        "device_action_integration": DEVICE_ACTION_INTEGRATION,
        "durable_journal_integration": DURABLE_JOURNAL_INTEGRATION,
        "target": deepcopy(TARGET),
        "action_tiers": deepcopy(ACTION_TIERS),
        "limits": {
            "d1_effect_max": D1_EFFECT_MAX,
            "d0_command_group_max": D0_COMMAND_GROUP_MAX,
            "duration_seconds": CAMPAIGN_DURATION_SECONDS,
        },
        "binding": current_binding(),
        "policy_status": policy["status"],
        "cli": ["--render-plan"],
        "activation_manifest_present": False,
        "live_session_approval_present": False,
        "device_commands": [],
        "device_effects": [],
        "partition_transfers": [],
        "next_required_unit": "durable_journal_and_fixed_descriptor_runner_integration",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-plan", action="store_true")
    args = parser.parse_args(argv)
    if not args.render_plan:
        parser.error("only --render-plan is available")
    print(canonical_bytes(render_plan()).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
