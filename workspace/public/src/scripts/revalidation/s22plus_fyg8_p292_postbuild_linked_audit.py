#!/usr/bin/env python3
"""P2.92 post-build proof with accept-to-resume closure."""

from __future__ import annotations

import json
import subprocess
import sys

import s22plus_fyg8_p290_postbuild_linked_audit as inherited
import s22plus_fyg8_p292_accept_to_resume as closure
import s22plus_fyg8_p292_build_repro_check as repro
import s22plus_fyg8_p292_linked_audit as linked
import s22plus_fyg8_p292_source_contract as p292


SCHEMA = repro.SCHEMA
VERDICT = repro.VERDICT
TARGET = repro.TARGET
ADAPTER_ID = linked.ADAPTER_ID
IMPLEMENTATION_ID = (
    "s22plus-fyg8-p292-linked-data-and-accept-to-resume-v1"
)
EXPECTED_SOURCE_CONTRACT_ID = p292.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p292_postbuild_linked_audit"
LINKED_VALIDATOR_SYMBOLS = linked.LINKED_VALIDATOR_SYMBOLS
LINKED_DATA_SYMBOLS = inherited.LINKED_DATA_SYMBOLS
HOST_GENERATIONS = len(p292.spec.POSITIONS) + 1
PAIR_DOMAIN_SIZE = inherited.PAIR_DOMAIN_SIZE
HOST_CASE_COUNT = HOST_GENERATIONS * PAIR_DOMAIN_SIZE
HOST_ACCEPT_COUNT = len(p292.spec.POSITIONS)
HOST_OUTPUT = (
    f"checked={HOST_CASE_COUNT} accepted={HOST_ACCEPT_COUNT}\n"
).encode("ascii")
AuditError = linked.AuditError
SourceContractError = AuditError
require_gnu_aarch64_tools = linked.require_gnu_aarch64_tools
linked_table_storage_bytes = linked.linked_table_storage_bytes
normalize_linked_table_storage = linked.normalize_linked_table_storage


def _configure() -> None:
    repro._configure()
    inherited.repro = repro
    inherited.linked = linked
    inherited.p290 = p292
    inherited.SCHEMA = SCHEMA
    inherited.VERDICT = VERDICT
    inherited.TARGET = TARGET
    inherited.ADAPTER_ID = ADAPTER_ID
    inherited.IMPLEMENTATION_ID = IMPLEMENTATION_ID
    inherited.EXPECTED_SOURCE_CONTRACT_ID = EXPECTED_SOURCE_CONTRACT_ID
    inherited.ADAPTER_MODULE = ADAPTER_MODULE
    inherited.LINKED_VALIDATOR_SYMBOLS = LINKED_VALIDATOR_SYMBOLS
    inherited.LINKED_DATA_SYMBOLS = LINKED_DATA_SYMBOLS
    inherited.HOST_GENERATIONS = HOST_GENERATIONS
    inherited.HOST_CASE_COUNT = HOST_CASE_COUNT
    inherited.HOST_ACCEPT_COUNT = HOST_ACCEPT_COUNT
    inherited.HOST_OUTPUT = HOST_OUTPUT


def check(args):  # noqa: ANN001, ANN201
    _configure()
    result = inherited.check(args)
    root = repro.candidate_contract.intent.repo_root()
    proof = closure.run_closure(root)
    if (
        proof.get("verdict") != closure.VERDICT
        or proof.get("accept_to_resume_closure", {}).get(
            "closure_case_count"
        )
        != 171
        or proof.get("accept_to_resume_sequence_walk", {}).get(
            "snapshot_count"
        )
        != 214
        or proof.get("checkpoint_errno_observability", {}).get("verified")
        is not True
    ):
        raise AuditError("P2.92 accept-to-resume postbuild closure differs")
    linked_result = result["linked_audit"]
    linked_result["postbuild_audit"]["accept_to_resume"] = {
        "closure_case_count": 171,
        "sequence_walk_snapshots": 214,
        "exact_old_generation_88_resumed": True,
        "errno_observable": True,
        "verified": True,
    }
    linked_result["source_contract_validator"][
        "accept_to_resume_pending_postbuild"
    ] = False
    return result


def main(argv: list[str] | None = None) -> int:
    _configure()
    try:
        result = check(repro.parse_args(argv))
    except (
        AuditError,
        repro.CheckError,
        repro.candidate_contract.ContractError,
        repro.candidate_contract.intent.IntentError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.modules.setdefault(ADAPTER_MODULE, sys.modules[__name__])
    raise SystemExit(main())
