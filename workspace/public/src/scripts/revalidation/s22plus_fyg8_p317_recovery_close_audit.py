#!/usr/bin/env python3
"""Host-only audit of the closed P3.17 recovery transaction.

The approved recovery adapter intentionally remains byte-frozen.  Its
pre-recovery ``--validate`` audit expected snapshot 17 to be the tail, so it
cannot describe the three normal receipts added by the successful recovery.
This audit reopens the closed durable result and treats snapshot 17 as the
exact historical barrier while requiring every later snapshot to remain
unambiguous.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(REVALIDATION))

import device_action_f1_live_v2 as live  # noqa: E402
import s22plus_fyg8_p317_recovery_only as recovery  # noqa: E402
import s22plus_odin_transition_core as odin_core  # noqa: E402


class CloseAuditError(RuntimeError):
    """The closed recovery evidence does not satisfy its exact contract."""


EXPECTED_JOURNAL_RECORD_COUNT = 19
EXPECTED_POST_BARRIER_CLOSURE = (
    {
        "sequence": 18,
        "receipt_sha256": "ec5be5fa82f904cb412655b86bbf8b6e60345e6fa32354a83316403815b36b97",
        "identity_count": 1,
        "identity_vector_sha256": "c53a14f990f5d98f65d28af2b2106adcb7cfe9d36631f3dc15adcbcbbf7b08a9",
    },
    {
        "sequence": 19,
        "receipt_sha256": "8d844389932ba2e960cf3634e586dafceb4b26ba8dcebd6d052e740664988990",
        "identity_count": 1,
        "identity_vector_sha256": "c53a14f990f5d98f65d28af2b2106adcb7cfe9d36631f3dc15adcbcbbf7b08a9",
    },
    {
        "sequence": 20,
        "receipt_sha256": "42f5f346560ed5fa3f862a70c7bc36399a4857d00cf34270cafec725c57e5e4c",
        "identity_count": 0,
        "identity_vector_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    },
)


def _post_barrier_closure(
    receipts: list[dict[str, Any]], sequence: int
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "sequence": record["sequence"],
            "receipt_sha256": record["sha256"],
            "identity_count": len(record["live_device_identities"]),
            "identity_vector_sha256": live.core.json_sha256(
                record["live_device_identities"]
            ),
        }
        for record in receipts[sequence + 1 :]
    )


def audit_receipt_history(
    authority: dict[str, Any],
    receipts: list[dict[str, Any]],
    *,
    endpoint_dir: Path | None = None,
    expected_post_barrier: tuple[dict[str, Any], ...] = EXPECTED_POST_BARRIER_CLOSURE,
) -> dict[str, Any]:
    incident = authority["binding"]["incident"]
    sequence = incident["historical_ambiguity_sequence"]
    expected_sha256 = authority["binding"]["immutable_inputs"][
        "historical_ambiguity_receipt"
    ]["sha256"]
    if (
        len(receipts) <= sequence
        or [record.get("sequence") for record in receipts]
        != list(range(len(receipts)))
    ):
        raise CloseAuditError("snapshot receipt sequence is incomplete")
    historical = receipts[sequence]
    if (
        historical.get("sha256") != expected_sha256
        or len(historical.get("live_device_identities", []))
        != incident["historical_ambiguity_identity_count"]
    ):
        raise CloseAuditError("historical ambiguity receipt changed")
    tail = receipts[sequence + 1 :]
    if any(len(record.get("live_device_identities", [])) > 1 for record in tail):
        raise CloseAuditError("post-barrier snapshot is ambiguous")

    if endpoint_dir is None:
        endpoint_dir = recovery._resolve_relative(  # noqa: SLF001
            incident["run_dir"], "incident run"
        ) / "odin-endpoints"
    patch = recovery.HistoricalAmbiguityPatch(
        endpoint_dir, sequence, expected_sha256
    )

    original = odin_core.EndpointGenerationTracker()
    original_failure = False
    try:
        for record in receipts:
            original.observe(
                tuple(tuple(value) for value in record["live_device_identities"])
            )
    except odin_core.OdinTransitionError as exc:
        original_failure = "ambiguous live Odin endpoints" in str(exc)
    if not original_failure:
        raise CloseAuditError("original historical replay failure was not reproduced")

    historical_tracker = patch._replay(receipts[: sequence + 1])  # noqa: SLF001
    current_tracker = patch._replay(receipts)  # noqa: SLF001
    historical_generation = historical_tracker.generation
    current_generation = current_tracker.generation
    fixture_generation = current_tracker.observe(
        (("/dev/bus/usb/999/999", "post-close-host-only-single"),)
    )
    fresh_multi_rejected = False
    try:
        current_tracker.observe(
            (
                ("/dev/bus/usb/999/998", "post-close-host-only-multi-a"),
                ("/dev/bus/usb/999/999", "post-close-host-only-multi-b"),
            )
        )
    except odin_core.OdinTransitionError as exc:
        fresh_multi_rejected = "ambiguous live Odin endpoints" in str(exc)
    if (
        historical_generation != 1
        or current_generation != historical_generation + 1
        or fixture_generation != current_generation + 1
        or not fresh_multi_rejected
    ):
        raise CloseAuditError("post-close endpoint generation semantics differ")
    closure = _post_barrier_closure(receipts, sequence)
    if closure != expected_post_barrier:
        raise CloseAuditError("post-barrier receipt closure differs")
    return {
        "snapshot_receipt_count": len(receipts),
        "historical_ambiguity_sequence": sequence,
        "historical_ambiguity_sha256": historical["sha256"],
        "post_barrier_receipt_count": len(tail),
        "post_barrier_identity_counts": [row["identity_count"] for row in closure],
        "post_barrier_closure": list(closure),
        "historical_generation": historical_generation,
        "closed_generation": current_generation,
        "fresh_single_fixture_generation": fixture_generation,
        "fresh_multi_fixture_rejected": True,
        "original_failure_reproduced": True,
    }


def audit_closed_recovery() -> dict[str, Any]:
    authority = recovery.load_authority()
    prepared, journal = recovery.verify_incident(authority)
    if journal.state() != "CLOSED":
        raise CloseAuditError("P3.17 recovery transaction is not closed")
    arm_path = prepared.run_dir / recovery.ARM_FILENAME
    arm = recovery._load_json(arm_path, "P3.17 recovery arm", 256 * 1024)  # noqa: SLF001
    if arm != recovery._expected_arm(authority):  # noqa: SLF001
        raise CloseAuditError("P3.17 recovery arm changed")
    recovery._verify_attempt_files(prepared.run_dir)  # noqa: SLF001
    if any(prepared.run_dir.glob("rollback-attempt-02*")):
        raise CloseAuditError("forbidden rollback attempt 2 exists")

    result = recovery._load_json(  # noqa: SLF001
        prepared.run_dir / "live-result.json", "closed live result"
    )
    live.validate_live_result(result, prepared)
    if (
        result.get("current_state") != "CLOSED"
        or result.get("verdict") != "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
        or result.get("outcome_class")
        != "candidate_not_proven_rollback_verified"
        or result.get("recovery_required") is not False
        or result.get("journal", {}).get("record_count")
        != EXPECTED_JOURNAL_RECORD_COUNT
    ):
        raise CloseAuditError("closed live result semantics differ")
    state = result["live_state"]
    health = state.get("final_evidence", {}).get("health", {})
    if (
        state.get("rollback_classification") != "odin_transfer_completed"
        or state.get("rollback_completed") is not True
        or state.get("final_verified") is not True
        or health.get("android_boot_completed") is not True
        or health.get("boot_animation_stopped") is not True
        or health.get("root_verified") is not True
        or health.get("odin_endpoint_absent") is not True
    ):
        raise CloseAuditError("closed rollback health differs")

    receipts = odin_core.list_snapshot_receipts(
        prepared.run_dir / "odin-endpoints"
    )
    history = audit_receipt_history(
        authority, receipts, endpoint_dir=prepared.run_dir / "odin-endpoints"
    )
    return {
        "schema": "s22plus_fyg8_p317_recovery_close_audit_v1",
        "verdict": "PASS_P317_RECOVERY_CLOSED_HEALTHY_HOST_AUDIT",
        "incident_binding_sha256": prepared.binding_sha256,
        "recovery_approval_binding_sha256": authority[
            "approval_binding_sha256"
        ],
        "journal_state": journal.state(),
        "journal_record_count": result["journal"]["record_count"],
        "candidate_transfer_count": 1,
        "rollback_transfer_count": 1,
        "rollback_classification": state["rollback_classification"],
        "final_verified": state["final_verified"],
        "recovery_required": result["recovery_required"],
        "live_verdict": result["verdict"],
        "live_outcome_class": result["outcome_class"],
        "history": history,
        "device_contact": False,
        "device_commands": 0,
        "partition_transfer": False,
    }


def main() -> int:
    try:
        result = audit_closed_recovery()
    except (
        CloseAuditError,
        recovery.RecoveryOnlyError,
        live.F1LiveError,
        live.core.F1V2Error,
        odin_core.OdinTransitionError,
        OSError,
    ) as exc:
        print(f"P3.17 close-audit error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
