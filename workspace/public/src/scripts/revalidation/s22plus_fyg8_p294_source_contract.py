#!/usr/bin/env python3
"""P2.94 source contract for two-slot DWC3 value telemetry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import s22plus_fyg8_p292_source_contract as inherited
import s22plus_fyg8_p294_identity_tiers as identity
import s22plus_fyg8_p294_telemetry_closure as closure
import s22plus_fyg8_p294_telemetry_generator as generator
import s22plus_fyg8_p294_telemetry_spec as spec


CONTRACT_ID = "s22plus-fyg8-p294-dwc3-value-telemetry-v1"
PROFILE = spec.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P294-DWC3-TELEMETRY-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p294_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p294_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P294_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p294_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P294_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P294_E3_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = "PASS_P294_DWC3_VALUE_TELEMETRY_IMPLEMENTATION_HOST_ONLY"
SOURCE_CHECK_RUN_ID = identity.SOURCE_CHECK_RUN_ID
SOURCE_CHECK_UNSAT_TAG = identity.SOURCE_CHECK_UNSAT_TAG
MODULE_PLAN_COUNT = inherited.MODULE_PLAN_COUNT
SOURCE_KEYS = identity.TIER1_SOURCE_KEYS
STAGE_SEQUENCE = tuple(position.stage for position in spec.POSITIONS)
MATERIALIZED_FILENAMES = {
    key: path.name
    for key, path in generator.artifact_paths().items()
    if key != "candidate_patch"
}
REACHABLE_VARIANTS = inherited.REACHABLE_VARIANTS + 165
LINKED_VALIDATOR_SYMBOLS = (
    *inherited.LINKED_VALIDATOR_SYMBOLS,
    "s22_p294_dwc3_state_snapshot",
    "s22_p294_wrapper_vbus_snapshot",
)
DRIVER_SOURCE_REFERENCE = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae"
)
DRIVER_SOURCE_RECEIPTS = {
    "kernel_platform/common/drivers/usb/dwc3/gadget.c": (
        "c121003d37f4fc9ab951f5d8811fe32736b21dadab985214996606578160c730"
    ),
    "kernel_platform/msm-kernel/drivers/usb/dwc3/dwc3-msm-core.c": (
        "1c8a3cea43337eebaf0601e01fe3a17e1260f2f768298b16f723534eee433021"
    ),
}


class SourceContractError(ValueError):
    pass


SourceContract = inherited.SourceContract
P294 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=spec.TERMINAL_STAGE,
    reachable_variants=REACHABLE_VARIANTS,
    source_keys=SOURCE_KEYS,
)


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def require(contract_id: str | None, profile: str) -> SourceContract:
    if contract_id != CONTRACT_ID or profile != PROFILE:
        raise SourceContractError(
            f"unsupported source contract/profile: {contract_id!r}/{profile}"
        )
    return P294


def candidate_observer(run_id: bytes) -> dict[str, str]:
    return inherited.candidate_observer(run_id)


def source_bytes(root: Path) -> dict[str, bytes]:
    result = identity.tier1_materials(root)
    if set(result) != SOURCE_KEYS:
        raise SourceContractError("P2.94 source inventory changed")
    expected_patch = generator.generate_bytes(
        root,
        run_id=SOURCE_CHECK_RUN_ID,
        unsat_tag=SOURCE_CHECK_UNSAT_TAG,
        profile=PROFILE,
    )["candidate_patch"]
    if result["base_patch"] != expected_patch:
        raise SourceContractError(
            "P2.94 base patch is not the telemetry generator output"
        )
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {
        name: receipt(value) for name, value in sorted(data.items())
    }


def generate(root: Path | None = None) -> dict[str, bytes]:
    repository = inherited.p290.p288.p243.repo_root() if root is None else root
    source = source_bytes(repository)
    return {
        "plan": source["plan_header"],
        "runtime": source["runtime_wrapper"],
        "checkpoint": source["checkpoint_client"],
        "patch": source["base_patch"],
    }


def _driver_patch(patch: bytes) -> tuple[bytes, bytes]:
    marker = (
        b"diff --git a/kernel_platform/common/drivers/usb/dwc3/gadget.c "
    )
    if patch.count(marker) != 1:
        raise SourceContractError("P2.94 driver patch boundary differs")
    offset = patch.index(marker)
    return patch[:offset], patch[offset:]


def _audit_patch(root: Path, patch: bytes, directory: Path) -> dict[str, Any]:
    inherited_patch, driver_patch = _driver_patch(patch)
    inherited_result = inherited._audit_patch(  # noqa: SLF001
        root, inherited_patch, directory
    )
    reference = root / DRIVER_SOURCE_REFERENCE
    for relative, expected in DRIVER_SOURCE_RECEIPTS.items():
        path = reference / relative
        if (
            not path.is_file()
            or path.is_symlink()
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise SourceContractError(
                f"P2.94 driver reference differs: {relative}"
            )
    checked = subprocess.run(
        ["git", "apply", "--check", "--unsafe-paths", "-"],
        cwd=reference,
        input=driver_patch,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if checked.returncode != 0:
        raise SourceContractError(
            "P2.94 driver patch does not cleanly apply: "
            + checked.stderr.decode("utf-8", "replace")[-2000:]
        )
    required = (
        b"s22_p294_dwc3_state_snapshot",
        b"DWC3_DSTS_USBLNKST(dsts)",
        b"s22_p294_wrapper_vbus_snapshot",
        b"UTMI_OTG_VBUS_VALID",
    )
    if any(driver_patch.count(token) < 1 for token in required):
        raise SourceContractError("P2.94 driver telemetry source is incomplete")
    return {
        **receipt(patch),
        "inherited_checkpoint_patch": inherited_result,
        "driver_reference_receipts": dict(DRIVER_SOURCE_RECEIPTS),
        "driver_clean_apply": True,
        "verified": True,
    }


def _audit_userspace(
    root: Path,
    generated: dict[str, bytes],
    source: dict[str, bytes],
    directory: Path,
) -> dict[str, Any]:
    for key, filename in MATERIALIZED_FILENAMES.items():
        if key in {"checkpoint_client", "runtime_wrapper", "plan_header"}:
            continue
        (directory / filename).write_bytes(source[key])
    try:
        return inherited.p290.p288.p252._audit_userspace(  # noqa: SLF001
            inherited.p290.shared_input_root(root),
            generated,
            directory,
            materialized_filenames=MATERIALIZED_FILENAMES,
            source_check_run_id=SOURCE_CHECK_RUN_ID,
        )
    except inherited.p290.p288.p252.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc


def implementation_result(root: Path) -> dict[str, Any]:
    first = generate(root)
    second = generate(root)
    if first != second:
        raise SourceContractError("P2.94 generation is not deterministic")
    source = source_bytes(root)
    identity_result = identity.validate()
    telemetry = closure.run_closure(root)
    if telemetry.get("verdict") != closure.VERDICT:
        raise SourceContractError("P2.94 telemetry closure differs")
    with tempfile.TemporaryDirectory(prefix="s22-p294-") as temporary:
        directory = Path(temporary)
        patch = _audit_patch(root, first["patch"], directory)
        userspace = _audit_userspace(root, first, source, directory)
    return {
        "schema": "s22plus_fyg8_p294_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "source_key_count": len(SOURCE_KEYS),
        "generated": {
            name: receipt(data) for name, data in sorted(first.items())
        },
        "patch": patch,
        "linked_userspace": userspace,
        "telemetry_closure": telemetry,
        "identity": identity_result,
        "descriptor": {
            "position_count": len(spec.POSITIONS),
            "terminal_generation": spec.TERMINAL_GENERATION,
            "record_size": 45,
            "slot_count": 2,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "boot_image_packaging": False,
            "live_authorized": False,
        },
        "verified": True,
    }


def linked_table_bytes() -> dict[str, bytes]:
    result = dict(inherited.linked_table_bytes())
    rules = bytearray()
    for ordinal, outcome, detail in spec.exact_detail_rules():
        rules.append(ordinal)
        rules.append(outcome)
        rules.extend(detail.to_bytes(2, "little"))
    result["s22_fyg8_p290_detail_rules"] = bytes(rules)
    return result


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    expected = linked_table_bytes()
    if actual != expected:
        raise SourceContractError("P2.94 linked descriptor tables differ")
    return {
        name: receipt(data) for name, data in sorted(actual.items())
    } | {
        "descriptor_bytes_verified": True,
        "position_pairs_verified": True,
        "exact_detail_whitelist_verified": True,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(implementation_result(Path.cwd()), indent=2, sort_keys=True))
