#!/usr/bin/env python3
"""Typed observation contracts for Device Action Process v2."""

from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any

import s22plus_fyg8_r4w1e_checkpoint_contract as checkpoint
import s22plus_fyg8_p219_same_ring_decoder as same_ring
import s22plus_fyg8_p230_same_ring_multiboot_decoder as same_ring_multiboot
import s22plus_fyg8_p233_e1_decoder as e1_latest_stage
import s22plus_fyg8_p242_e2_stock_closure as e2_closure
import s22plus_fyg8_p253_e2_stock_closure as e2_closure_selector
import s22plus_fyg8_p286_e2_stock_closure as p286_e2_closure
import s22plus_fyg8_p286_source_contracts as source_contracts
import s22plus_fyg8_p288_e2_stock_closure as p288_e2_closure
import s22plus_fyg8_p290_e2_stock_closure as p290_e2_closure
import s22plus_fyg8_p292_e2_stock_closure as p292_e2_closure
import s22plus_fyg8_p294_e2_stock_closure as p294_e2_closure
import s22plus_fyg8_p296_e2_stock_closure as p296_e2_closure
import s22plus_fyg8_p298_e2_stock_closure as p298_e2_closure
import s22plus_fyg8_p298_identity_tiers as p298_identity
import s22plus_fyg8_p300_e2_stock_closure as p300_e2_closure
import s22plus_fyg8_p300_source_contract as p300_source_contract
import s22plus_fyg8_p301_overlay_contract as p301_overlay
import s22plus_fyg8_p301_telemetry_decoder as p301_decoder
import s22plus_fyg8_p302_overlay_contract as p302_overlay
import s22plus_fyg8_p303_overlay_contract as p303_overlay
import s22plus_fyg8_p303_stock_log_baseline_binding as p303_stock_binding
import s22plus_fyg8_p303_telemetry_decoder as p303_decoder
import s22plus_fyg8_p304_e2_stock_closure as p304_e2_closure
import s22plus_fyg8_p304_overlay_contract as p304_overlay
import s22plus_fyg8_p305_overlay_contract as p305_overlay
import s22plus_fyg8_p306_overlay_contract as p306_overlay
import s22plus_fyg8_p306_telemetry_decoder as p306_decoder
import s22plus_fyg8_p307_overlay_contract as p307_overlay
import s22plus_fyg8_p307_telemetry_decoder as p307_decoder
import s22plus_fyg8_p307_telemetry_spec as p307_spec
import s22plus_fyg8_p308_overlay_contract as p308_overlay
import s22plus_fyg8_p308_telemetry_decoder as p308_decoder
import s22plus_fyg8_p308_telemetry_spec as p308_spec
import s22plus_fyg8_p310_e2_stock_closure as p310_e2_closure
import s22plus_fyg8_p310_source_contract as p310_source_contract
import s22plus_fyg8_p310_telemetry_decoder as p310_decoder
import s22plus_fyg8_p311_overlay_contract as p311_overlay
import s22plus_fyg8_p311_e2_stock_closure as p311_e2_closure
import s22plus_fyg8_p311_telemetry_decoder as p311_decoder
import s22plus_fyg8_p311_telemetry_spec as p311_spec
import s22plus_fyg8_p312_overlay_contract as p312_overlay
import s22plus_fyg8_p312_e2_stock_closure as p312_e2_closure
import s22plus_fyg8_p312_telemetry_decoder as p312_decoder
import s22plus_fyg8_p312_telemetry_spec as p312_spec


MARKER_KIND = "retained_marker_after_rollback"
CHECKPOINT_KIND = "retained_checkpoint_after_rollback"
PID1_USERSPACE_KIND = "retained_pid1_userspace_after_rollback"
SAME_RING_KIND = "retained_pid1_same_ring_discriminator_after_rollback"
SAME_RING_MULTIBOOT_KIND = (
    "retained_pid1_same_ring_multiboot_discriminator_after_rollback"
)
E1_LATEST_STAGE_KIND = "retained_e1_latest_stage_multiboot_after_rollback"
CHECKPOINT_DECODER = "s22plus_fyg8_r4w1e_checkpoint_v1"
PID1_USERSPACE_DECODER = "s22plus_fyg8_r4w1e0_pid1_userspace_v1"
SAME_RING_DECODER = "s22plus_fyg8_p219_same_ring_v1"
SAME_RING_MULTIBOOT_DECODER = "s22plus_fyg8_p230_same_ring_multiboot_v1"
E1_LATEST_STAGE_DECODER = e1_latest_stage.DECODER_ID
E1_LATEST_STAGE_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p234_run_manifest_v1"
E1_LATEST_STAGE_STATIC_SCHEMA = "s22plus_fyg8_p234_process_v2_static_result_v1"
E1_LATEST_STAGE_STATIC_VERDICT = "PASS_P234_PROCESS_V2_OFFLINE_EVIDENCE_PROMOTION"
E1_LATEST_STAGE_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p234_candidate_static_checker_v1"
)
E1_LATEST_STAGE_CANDIDATE_STATIC_VERDICT = (
    "PASS_P234_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P286_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p286_candidate_static_checker_v1"
)
P286_CANDIDATE_STATIC_VERDICT = (
    "PASS_P286_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P286_SOURCE_CONTRACT_ID = p286_e2_closure.source_contract.CONTRACT_ID
P288_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p288_candidate_static_checker_v1"
)
P288_CANDIDATE_STATIC_VERDICT = (
    "PASS_P288_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P288_SOURCE_CONTRACT_ID = p288_e2_closure.source_contract.CONTRACT_ID
P290_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p290_candidate_static_checker_v1"
)
P290_CANDIDATE_STATIC_VERDICT = (
    "PASS_P290_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P290_SOURCE_CONTRACT_ID = p290_e2_closure.source_contract.CONTRACT_ID
P292_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p292_candidate_static_checker_v1"
)
P292_CANDIDATE_STATIC_VERDICT = (
    "PASS_P292_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P292_SOURCE_CONTRACT_ID = p292_e2_closure.source_contract.CONTRACT_ID
P294_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p294_candidate_static_checker_v1"
)
P294_CANDIDATE_STATIC_VERDICT = (
    "PASS_P294_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P294_SOURCE_CONTRACT_ID = p294_e2_closure.source_contract.CONTRACT_ID
P296_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p296_candidate_static_checker_v1"
)
P296_CANDIDATE_STATIC_VERDICT = (
    "PASS_P296_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P296_SOURCE_CONTRACT_ID = p296_e2_closure.source_contract.CONTRACT_ID
P298_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p298_candidate_static_checker_v1"
)
P298_CANDIDATE_STATIC_VERDICT = (
    "PASS_P298_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P298_SOURCE_CONTRACT_ID = p298_e2_closure.source_contract.CONTRACT_ID
P300_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p300_candidate_static_checker_v1"
)
P300_CANDIDATE_STATIC_VERDICT = (
    "PASS_P300_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P300_SOURCE_CONTRACT_ID = p300_e2_closure.source_contract.CONTRACT_ID
P310_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p310_candidate_static_checker_v1"
)
P310_CANDIDATE_STATIC_VERDICT = (
    "PASS_P310_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P310_SOURCE_CONTRACT_ID = p310_source_contract.CONTRACT_ID
P301_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p301_candidate_static_checker_v1"
)
P301_CANDIDATE_STATIC_VERDICT = (
    "PASS_P301_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P301_OVERLAY_CONTRACT_ID = p301_overlay.CONTRACT_ID
P302_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p302_candidate_static_checker_v1"
)
P302_CANDIDATE_STATIC_VERDICT = (
    "PASS_P302_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P302_OVERLAY_CONTRACT_ID = p302_overlay.CONTRACT_ID
P303_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p303_candidate_static_checker_v1"
)
P303_CANDIDATE_STATIC_VERDICT = (
    "PASS_P303_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P303_OVERLAY_CONTRACT_ID = p303_overlay.CONTRACT_ID
P304_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p304_candidate_static_checker_v1"
)
P304_CANDIDATE_STATIC_VERDICT = (
    "PASS_P304_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P304_OVERLAY_CONTRACT_ID = p304_overlay.CONTRACT_ID
P305_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p305_candidate_static_checker_v1"
)
P305_CANDIDATE_STATIC_VERDICT = (
    "PASS_P305_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P305_OVERLAY_CONTRACT_ID = p305_overlay.CONTRACT_ID
P306_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p306_candidate_static_checker_v1"
)
P306_CANDIDATE_STATIC_VERDICT = (
    "PASS_P306_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P306_OVERLAY_CONTRACT_ID = p306_overlay.CONTRACT_ID
P307_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p307_candidate_static_checker_v1"
)
P307_CANDIDATE_STATIC_VERDICT = (
    "PASS_P307_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P307_OVERLAY_CONTRACT_ID = p307_overlay.CONTRACT_ID
P308_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p308_candidate_static_checker_v1"
)
P308_CANDIDATE_STATIC_VERDICT = (
    "PASS_P308_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P308_OVERLAY_CONTRACT_ID = p308_overlay.CONTRACT_ID
P311_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p311_candidate_static_checker_v1"
)
P311_CANDIDATE_STATIC_VERDICT = (
    "PASS_P311_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P311_OVERLAY_CONTRACT_ID = p311_overlay.CONTRACT_ID
P312_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p312_candidate_static_checker_v1"
)
P312_CANDIDATE_STATIC_VERDICT = (
    "PASS_P312_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P312_OVERLAY_CONTRACT_ID = p312_overlay.CONTRACT_ID
P301_TELEMETRY_OVERLAY_IDS = frozenset(
    {
        P301_OVERLAY_CONTRACT_ID,
        P302_OVERLAY_CONTRACT_ID,
        P303_OVERLAY_CONTRACT_ID,
        P304_OVERLAY_CONTRACT_ID,
        P305_OVERLAY_CONTRACT_ID,
        P306_OVERLAY_CONTRACT_ID,
        P307_OVERLAY_CONTRACT_ID,
        P308_OVERLAY_CONTRACT_ID,
        P311_OVERLAY_CONTRACT_ID,
        P312_OVERLAY_CONTRACT_ID,
    }
)
P298_HISTORICAL_POSTBUILD_RESULT = {
    "sha256": "a7bfff7bdc82683999ef0d91349f20560b659ea703cb0542eeb37ca36a3ff997",
    "size": 71342,
}
P298_HISTORICAL_QUALIFICATION = {
    "sha256": "f3533d20ef3edc5c4feaf410296492820138dcd2c56861ee81be02fca78b89eb",
    "size": 115141,
}
P298_REPAIR_TIER2_KEYS = frozenset(
    {
        "p298_e2_stock_closure",
        "p298_candidate_static_checker",
        "p298_contract_test",
    }
)
P298_BUILD_ARTIFACTS = frozenset(
    {
        ".config",
        "Image",
        "System.map",
        "abi.xml",
        "build-result.json",
        "vmlinux",
        "vmlinux.symvers",
    }
)
E1_LATEST_STAGE_CANDIDATE_CONTRACT_SCHEMA = (
    "s22plus_fyg8_p234_candidate_contract_v1"
)
E1_LATEST_STAGE_CANDIDATE_CONTRACT_VERDICT = (
    "PASS_P234_CANDIDATE_CONTRACT_HOST_ONLY"
)
E1_LATEST_STAGE_PREIMAGE_SCHEMA = (
    "s22plus_fyg8_p234_candidate_identity_preimage_v1"
)
E1_LATEST_STAGE_RUN_ID_DOMAINS = {
    "E1A": b"S22PLUS-FYG8-P234-E1A-RUN-ID-V1\0",
    "E1B": b"S22PLUS-FYG8-P239-E1B-RUN-ID-V1\0",
    "E2": b"S22PLUS-FYG8-P242-E2-RUN-ID-V1\0",
}
E1_LATEST_STAGE_SOURCE_KEYS = {
    "E1A": {
        "base_patch",
        "checkpoint_client",
        "runtime_wrapper",
        "legacy_runtime",
        "legacy_header",
        "child",
        "decoder",
        "design_model",
        "source_checker",
    },
    "E1B": {
        "base_patch",
        "checkpoint_client",
        "runtime_wrapper",
        "legacy_runtime",
        "legacy_header",
        "child",
        "decoder",
        "design_model",
        "source_checker",
    },
    "E2": {
        "base_patch",
        "checkpoint_client",
        "runtime_wrapper",
        "plan_header",
        "loader_core",
        "legacy_runtime",
        "legacy_header",
        "child",
        "decoder",
        "design_model",
        "source_checker",
        "planner",
        "dtbo_contract",
        "stock_closure",
    },
}
E1_LATEST_STAGE_KERNEL_INTERVAL = (4096, 41495040)
CHECKPOINT_SOURCE = "/proc/last_kmsg"
PID1_USERSPACE_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
PID1_USERSPACE_ENTRY = b"\n[[S22P1U|ba234c7de4105b2a23222436284605f2]]\n"
PID1_USERSPACE_PROOF = b"\n[[S22P1U|ec8d029b05288644bbe7b5f7c7af190c]]\n"
PID1_USERSPACE_FAMILY = b"[[S22P1U|"
PID1_USERSPACE_PROBE_ID = "64554e8469385878c5bf8d57c44edeea"
SAME_RING_CONTRACT_ID = same_ring.CONTRACT_ID.hex()
SAME_RING_MULTIBOOT_POLICY_ID = same_ring_multiboot.POLICY_ID.hex()
SAME_RING_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p219_run_manifest_v1"
SAME_RING_STATIC_SCHEMA = "s22plus_fyg8_p219_candidate_static_checker_v1"
SAME_RING_STATIC_VERDICT = "PASS_P219_OFFLINE_CANDIDATE_STATIC_CONTRACT"
OUTCOME_NAMES = {
    checkpoint.OUTCOME_PROGRESS: "progress",
    checkpoint.OUTCOME_SUCCESS: "success",
    checkpoint.OUTCOME_FAILURE: "failure",
}
HEX32_RE = re.compile(r"[0-9a-f]{32}")
HASH_RE = re.compile(r"[0-9a-f]{64}")
E1_LATEST_STAGE_BASE_FILES = {
    "kernel_platform/common/arch/arm64/configs/gki_defconfig": (
        "12661b7d249fb8f80135c3fdcd331733b86d5215f2f4e88e356d1516831ab493"
    ),
    "kernel_platform/common/init/Kconfig": (
        "8273d233a441c21df2fcb1d5d17a590321d758205fd5babd8b8dcb4e6a334019"
    ),
    "kernel_platform/common/init/main.c": (
        "7d281c86ca63646083b9f489eed28281c7d2518f397f34ceccf34c223eaa663a"
    ),
}


def _candidate_base_files(
    source_contract_id: str | None,
    profile: str,
) -> dict[str, str]:
    expected = dict(E1_LATEST_STAGE_BASE_FILES)
    if source_contract_id not in {
        P294_SOURCE_CONTRACT_ID,
        P296_SOURCE_CONTRACT_ID,
        P298_SOURCE_CONTRACT_ID,
        P300_SOURCE_CONTRACT_ID,
        P310_SOURCE_CONTRACT_ID,
    }:
        return expected
    driver_sources = getattr(
        _selected_contract(source_contract_id, profile).module,
        "DRIVER_SOURCE_RECEIPTS",
        None,
    )
    if (
        not isinstance(driver_sources, dict)
        or not driver_sources
        or any(
            not isinstance(path, str)
            or not isinstance(digest, str)
            or HASH_RE.fullmatch(digest) is None
            for path, digest in driver_sources.items()
        )
        or set(expected) & set(driver_sources)
    ):
        raise EvidenceError("versioned driver source receipts are invalid")
    expected.update(driver_sources)
    return expected
E1B_MODULE_SPECS = [
    {
        "file": "smem.ko",
        "runtime": "smem",
        "size": 28_704,
        "sha256": "27a80d5598329d6a526384d09806de63983204988748ea4e7d3fccfafc24a524",
    },
    {
        "file": "minidump.ko",
        "runtime": "minidump",
        "size": 37_312,
        "sha256": "e5e6f4dfe1ddac2cd4f8d15c11a50d4d32b6e9de278fedbed44747630a5c554d",
    },
    {
        "file": "qcom-scm.ko",
        "runtime": "qcom_scm",
        "size": 218_384,
        "sha256": "e12ba8661808c2c47acf42c9939157e509fcdb5b98f6e650f79b92dba18a1af3",
    },
    {
        "file": "qcom_wdt_core.ko",
        "runtime": "qcom_wdt_core",
        "size": 48_640,
        "sha256": "ef484fb4f1f17586ff63852e0ea9579d07f275f7966ad117d20039055c2d7599",
    },
    {
        "file": "gh_virt_wdt.ko",
        "runtime": "gh_virt_wdt",
        "size": 18_944,
        "sha256": "f030c5486a41b1fbe4b0ea3aa85a401dd16daa1f1a551a626f6ea424ee90dd39",
    },
]
E1B_MODULE_FILES = [row["file"] for row in E1B_MODULE_SPECS]
E1B_MODULE_RUNTIME_NAMES = [row["runtime"] for row in E1B_MODULE_SPECS]
E1B_MODULE_ORDER_MODEL = (
    "modules.dep topological order with stock modules.load.recovery tie-breaks"
)
E1B_STOCK_RECOVERY_POSITIONS = {
    "gh_virt_wdt.ko": 5,
    "minidump.ko": 51,
    "qcom-scm.ko": 83,
    "qcom_wdt_core.ko": 6,
    "smem.ko": 124,
}
E1B_VENDOR_METADATA_HASHES = {
    "modules.alias": "5679e647fcdcb6a13bd4f20d24a901f158e641fbd0a813274c99006ec8fa2c20",
    "modules.dep": "21eae389f1d8b0a9fc93cec0b12d36e736cfac656d91ae55055c793f2ed67b27",
    "modules.load": "8491b842e6e05cfba42694ad003301a6598e8d152ec10cc8f0cc6fb17f10e232",
    "modules.load.recovery": "616bdb71f2b68d76eca23f72883aea25d5202d4e14f5c99dd934720df863ac10",
    "modules.softdep": "21d6a678d186356c2fb0349a8a9a5190e6e225dab0feb5012e495a100c33afb0",
}
E1B_COMPOSITION_ORDER = ["generic", "vendor[0]/"]
E1B_EFFECTIVE_ENTRY_COUNT = 474
E1B_EFFECTIVE_MODULE_ROWS = [
    {"file": name, "runtime": runtime, "layer": "vendor[0]/"}
    for name, runtime in zip(E1B_MODULE_FILES, E1B_MODULE_RUNTIME_NAMES)
]
E1B_ELF_ENTRYPOINTS = {"init": 4_198_200, "child": 4_194_508}
E1B_STOCK_VENDOR_BOOT = {
    "size": 100_663_296,
    "sha256": "096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7",
}


def _e1_reachable_slot_variant_count(
    profile: str, source_contract_id: str | None = None
) -> int:
    if source_contract_id is not None:
        return _selected_contract(
            source_contract_id, profile
        ).contract.reachable_variants
    model = e1_latest_stage.model
    sequence = model.PROFILE_STAGE_SEQUENCES.get(profile)
    terminal = model.PROFILE_TERMINALS.get(profile)
    if not sequence or sequence[-1] != terminal or sequence.count(terminal) != 1:
        raise EvidenceError("E1 profile stage sequence is not terminal-bound")
    return sum(1 if stage == terminal else 1 + 4095 for stage in sequence)


class EvidenceError(ValueError):
    pass


def _selected_contract(
    source_contract_id: str | None, profile: str
) -> source_contracts.SelectedSourceContract:
    if source_contract_id == P310_SOURCE_CONTRACT_ID:
        try:
            contract = p310_source_contract.require(source_contract_id, profile)
        except p310_source_contract.SourceContractError as exc:
            raise EvidenceError(str(exc)) from exc
        return source_contracts.SelectedSourceContract(
            module=p310_source_contract,
            contract=contract,
            implementation_verdict=p310_source_contract.IMPLEMENTATION_VERDICT,
            source_check_run_id=p310_source_contract.SOURCE_CHECK_RUN_ID,
            userspace_verdict=p310_source_contract.USERSPACE_VERDICT,
        )
    if source_contract_id == P300_SOURCE_CONTRACT_ID:
        try:
            contract = p300_source_contract.require(source_contract_id, profile)
        except p300_source_contract.SourceContractError as exc:
            raise EvidenceError(str(exc)) from exc
        return source_contracts.SelectedSourceContract(
            module=p300_source_contract,
            contract=contract,
            implementation_verdict=p300_source_contract.IMPLEMENTATION_VERDICT,
            source_check_run_id=p300_source_contract.SOURCE_CHECK_RUN_ID,
            userspace_verdict=p300_source_contract.USERSPACE_VERDICT,
        )
    try:
        return source_contracts.select(source_contract_id, profile)
    except source_contracts.SourceContractSelectionError as exc:
        raise EvidenceError(str(exc)) from exc


def _latest_stage_decoder(
    source_contract_id: str | None, profile: str
):
    if source_contract_id is None:
        return e1_latest_stage
    return _selected_contract(source_contract_id, profile).decoder


def _latest_stage_observation_decoder(
    source_contract_id: str | None,
    profile: str,
    userspace_overlay_contract_id: str | None = None,
):
    if userspace_overlay_contract_id is None:
        return _latest_stage_decoder(source_contract_id, profile)
    if userspace_overlay_contract_id == P311_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != P310_SOURCE_CONTRACT_ID
            or profile != p311_overlay.PROFILE
        ):
            raise EvidenceError("P3.11 userspace observation overlay is unsupported")
        selected = p311_decoder
    elif userspace_overlay_contract_id == P312_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != P310_SOURCE_CONTRACT_ID
            or profile != p312_overlay.PROFILE
        ):
            raise EvidenceError("P3.12 userspace observation overlay is unsupported")
        selected = p312_decoder
    else:
        if (
            userspace_overlay_contract_id not in P301_TELEMETRY_OVERLAY_IDS
            or source_contract_id != P300_SOURCE_CONTRACT_ID
            or profile != p301_overlay.PROFILE
        ):
            raise EvidenceError("userspace observation overlay is unsupported")
        if userspace_overlay_contract_id == P307_OVERLAY_CONTRACT_ID:
            selected = p307_decoder
        elif userspace_overlay_contract_id == P308_OVERLAY_CONTRACT_ID:
            selected = p308_decoder
        elif userspace_overlay_contract_id == P306_OVERLAY_CONTRACT_ID:
            selected = p306_decoder
        elif userspace_overlay_contract_id in {
            P303_OVERLAY_CONTRACT_ID,
            P304_OVERLAY_CONTRACT_ID,
            P305_OVERLAY_CONTRACT_ID,
        }:
            selected = p303_decoder
        else:
            selected = p301_decoder
    return _validate_decoder_carrier_authority(
        selected, source_contract_id=source_contract_id, profile=profile
    )


def _validate_decoder_carrier_authority(
    selected_decoder: Any,
    *,
    source_contract_id: str | None,
    profile: str,
):
    """Bind overlay semantics to the source contract's retained-record ABI."""

    source_decoder = _latest_stage_decoder(source_contract_id, profile)
    attributes = (
        "LONG_FAMILY",
        "UNSAT_FAMILY",
        "LONG_RECORD_SIZE",
        "FORMAT_VERSION",
    )
    if any(
        getattr(selected_decoder.model, name, None)
        != getattr(source_decoder.model, name, None)
        for name in attributes
    ):
        raise EvidenceError(
            "userspace observation decoder carrier differs from source contract"
        )
    try:
        run_id = bytes.fromhex("00112233445566778899aabbccddeeff")
        record = source_decoder.model.initialize_record(profile, run_id)
        decoded = selected_decoder.decode_record(
            record,
            expected_profile=profile,
            expected_run_id=run_id,
        )
        json.dumps(decoded, sort_keys=True, allow_nan=False)
    except (AttributeError, TypeError, ValueError, selected_decoder.DecodeError) as exc:
        raise EvidenceError(
            "userspace observation decoder is not JSON-safe for its carrier"
        ) from exc
    return selected_decoder


def _validate_p301_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p301_overlay.verify_intent(
            root,
            root / p301_overlay.DEFAULT_INTENT,
        )
    except (p301_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.01 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.01 overlay contract differs from current intent")
    return current


def _validate_p302_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p302_overlay.verify_intent(
            root,
            root / p302_overlay.DEFAULT_INTENT,
        )
    except (p302_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.02 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.02 overlay contract differs from current intent")
    return current


def _validate_p303_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p303_overlay.verify_intent(
            root,
            root / p303_overlay.DEFAULT_INTENT,
        )
    except (p303_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.03 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.03 overlay contract differs from current intent")
    return current


def _validate_p304_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p304_overlay.verify_intent(root, root / p304_overlay.DEFAULT_INTENT)
    except (p304_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.04 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.04 overlay contract differs from current intent")
    return current


def _validate_p305_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p305_overlay.verify_intent(root, root / p305_overlay.DEFAULT_INTENT)
    except (p305_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.05 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.05 overlay contract differs from current intent")
    return current


def _validate_p306_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p306_overlay.verify_intent(root, root / p306_overlay.DEFAULT_INTENT)
    except (p306_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.06 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.06 overlay contract differs from current intent")
    return current


def _validate_p307_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p307_overlay.verify_intent(root, root / p307_overlay.DEFAULT_INTENT)
    except (p307_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.07 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.07 overlay contract differs from current intent")
    return current


def _validate_p308_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p308_overlay.verify_intent(root, root / p308_overlay.DEFAULT_INTENT)
    except (p308_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.08 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.08 overlay contract differs from current intent")
    return current


def _validate_p311_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p311_overlay.verify_intent(root, root / p311_overlay.DEFAULT_INTENT)
    except (p311_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.11 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.11 overlay contract differs from current intent")
    return current


def _validate_p312_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p312_overlay.verify_intent(root, root / p312_overlay.DEFAULT_INTENT)
    except (p312_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.12 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.12 overlay contract differs from current intent")
    return current


def _validate_userspace_overlay_contract(
    value: Any, userspace_overlay_contract_id: str
) -> dict[str, Any]:
    if userspace_overlay_contract_id == P301_OVERLAY_CONTRACT_ID:
        return _validate_p301_overlay_contract(value)
    if userspace_overlay_contract_id == P302_OVERLAY_CONTRACT_ID:
        return _validate_p302_overlay_contract(value)
    if userspace_overlay_contract_id == P303_OVERLAY_CONTRACT_ID:
        return _validate_p303_overlay_contract(value)
    if userspace_overlay_contract_id == P304_OVERLAY_CONTRACT_ID:
        return _validate_p304_overlay_contract(value)
    if userspace_overlay_contract_id == P305_OVERLAY_CONTRACT_ID:
        return _validate_p305_overlay_contract(value)
    if userspace_overlay_contract_id == P306_OVERLAY_CONTRACT_ID:
        return _validate_p306_overlay_contract(value)
    if userspace_overlay_contract_id == P307_OVERLAY_CONTRACT_ID:
        return _validate_p307_overlay_contract(value)
    if userspace_overlay_contract_id == P308_OVERLAY_CONTRACT_ID:
        return _validate_p308_overlay_contract(value)
    if userspace_overlay_contract_id == P311_OVERLAY_CONTRACT_ID:
        return _validate_p311_overlay_contract(value)
    if userspace_overlay_contract_id == P312_OVERLAY_CONTRACT_ID:
        return _validate_p312_overlay_contract(value)
    raise EvidenceError("userspace observation overlay is unsupported")


def _select_e2_closure(
    source_contract_id: str | None,
    userspace_overlay_contract_id: str | None = None,
):
    if userspace_overlay_contract_id in {
        P304_OVERLAY_CONTRACT_ID,
        P305_OVERLAY_CONTRACT_ID,
        P306_OVERLAY_CONTRACT_ID,
        P307_OVERLAY_CONTRACT_ID,
        P308_OVERLAY_CONTRACT_ID,
    }:
        if source_contract_id != P300_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.04 parent source contract differs")
        return p304_e2_closure
    if userspace_overlay_contract_id == P311_OVERLAY_CONTRACT_ID:
        if source_contract_id != P310_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.11 parent source contract differs")
        return p311_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P312_OVERLAY_CONTRACT_ID:
        if source_contract_id != P310_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.12 parent source contract differs")
        return p312_e2_closure.select(source_contract_id)
    if source_contract_id == P300_SOURCE_CONTRACT_ID:
        return p300_e2_closure.select(source_contract_id)
    if source_contract_id == P310_SOURCE_CONTRACT_ID:
        return p310_e2_closure.select(source_contract_id)
    if source_contract_id == P298_SOURCE_CONTRACT_ID:
        return p298_e2_closure.select(source_contract_id)
    if source_contract_id == P296_SOURCE_CONTRACT_ID:
        return p296_e2_closure.select(source_contract_id)
    if source_contract_id == P294_SOURCE_CONTRACT_ID:
        return p294_e2_closure.select(source_contract_id)
    if source_contract_id == P292_SOURCE_CONTRACT_ID:
        return p292_e2_closure.select(source_contract_id)
    if source_contract_id == P290_SOURCE_CONTRACT_ID:
        return p290_e2_closure.select(source_contract_id)
    if source_contract_id == P288_SOURCE_CONTRACT_ID:
        return p288_e2_closure.select(source_contract_id)
    if source_contract_id == P286_SOURCE_CONTRACT_ID:
        return p286_e2_closure.select(source_contract_id)
    return e2_closure_selector.select(source_contract_id)


def _e2_authority_context(source_contract_id: str | None, closure_api: Any):
    if source_contract_id not in {
        P286_SOURCE_CONTRACT_ID,
        P288_SOURCE_CONTRACT_ID,
        P290_SOURCE_CONTRACT_ID,
        P292_SOURCE_CONTRACT_ID,
        P294_SOURCE_CONTRACT_ID,
        P296_SOURCE_CONTRACT_ID,
        P298_SOURCE_CONTRACT_ID,
        P300_SOURCE_CONTRACT_ID,
        P310_SOURCE_CONTRACT_ID,
    }:
        return nullcontext()
    authority_context = getattr(closure_api, "_p286_authority_paths", None)
    if not callable(authority_context):
        raise EvidenceError(
            "versioned stock-closure authority adapter is unavailable"
        )
    return authority_context()


def _p310_e2_authority_context(
    closure_api: Any,
    entries: list[Any],
    expected_init: dict[str, Any],
):
    if closure_api is not p310_e2_closure.select(P310_SOURCE_CONTRACT_ID):
        raise EvidenceError("P3.10 stock-closure authority adapter differs")
    matching = [
        entry
        for entry in entries
        if entry.name == "init" and entry.file_type == "regular"
    ]
    if (
        len(matching) != 1
        or e2_closure.receipt(matching[0].data) != expected_init
    ):
        raise EvidenceError("P3.10 exact init authority is unavailable")
    return closure_api.exact_init_authority(matching[0].data)


def _p311_e2_authority_context(
    closure_api: Any,
    entries: list[Any],
    expected_init: dict[str, Any],
):
    if closure_api is not p311_e2_closure.select(P310_SOURCE_CONTRACT_ID):
        raise EvidenceError("P3.11 stock-closure authority adapter differs")
    matching = [
        entry
        for entry in entries
        if entry.name == "init" and entry.file_type == "regular"
    ]
    if (
        len(matching) != 1
        or e2_closure.receipt(matching[0].data) != expected_init
    ):
        raise EvidenceError("P3.11 exact init authority is unavailable")
    return closure_api.exact_init_authority(matching[0].data)


def _p312_e2_authority_context(
    closure_api: Any,
    entries: list[Any],
    expected_init: dict[str, Any],
):
    if closure_api is not p312_e2_closure.select(P310_SOURCE_CONTRACT_ID):
        raise EvidenceError("P3.12 stock-closure authority adapter differs")
    matching = [
        entry
        for entry in entries
        if entry.name == "init" and entry.file_type == "regular"
    ]
    if (
        len(matching) != 1
        or e2_closure.receipt(matching[0].data) != expected_init
    ):
        raise EvidenceError("P3.12 exact init authority is unavailable")
    return closure_api.exact_init_authority(matching[0].data)


@contextmanager
def _p301_e2_authority_context(
    closure_api: Any, expected_init: dict[str, Any]
):
    if closure_api is not p300_e2_closure.select(P300_SOURCE_CONTRACT_ID):
        raise EvidenceError("P3.01 parent stock-closure adapter differs")
    previous = p300_e2_closure.p286.p282._validate_p282_authority_strings  # noqa: SLF001

    def validate(data: bytes) -> None:
        if e2_closure.receipt(data) != expected_init:
            raise p300_e2_closure.ClosureError(
                "P3.01 effective init differs from bound identity"
            )
        printable = p300_e2_closure.p286.p282.p280.isolated_p260._printable_strings(  # noqa: SLF001
            data
        )
        paths = p300_e2_closure.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
        incidental = paths - p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS
        if (
            p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS - paths
            or incidental != {'/E9"', "/R9@"}
            or any(data.count(value.encode("ascii")) != 1 for value in incidental)
        ):
            raise p300_e2_closure.ClosureError(
                "P3.01 effective init authority path set differs"
            )
        scrubbed = data
        for value in sorted(incidental):
            encoded = value.encode("ascii")
            scrubbed = scrubbed.replace(encoded, b"\0" * len(encoded))
        with p300_e2_closure._p300_authority_globals():  # noqa: SLF001
            p300_e2_closure._P282_VALIDATE_AUTHORITY_STRINGS(scrubbed)  # noqa: SLF001

    p300_e2_closure.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
    try:
        yield
    finally:
        p300_e2_closure.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001


@contextmanager
def _p303_e2_authority_context(
    closure_api: Any, expected_init: dict[str, Any]
):
    if closure_api not in {
        p300_e2_closure.select(P300_SOURCE_CONTRACT_ID),
        p304_e2_closure,
    }:
        raise EvidenceError("P3.03 parent stock-closure adapter differs")
    previous = p300_e2_closure.p286.p282._validate_p282_authority_strings  # noqa: SLF001

    def validate(data: bytes) -> None:
        if e2_closure.receipt(data) != expected_init:
            raise p300_e2_closure.ClosureError(
                "P3.03 effective init differs from bound identity"
            )
        required = frozenset(
            {*p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS, "/dev/kmsg"}
        )
        allowed = frozenset(
            {*p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS, "/dev/kmsg"}
        )
        printable = p300_e2_closure.p286.p282.p280.isolated_p260._printable_strings(  # noqa: SLF001
            data
        )
        paths = p300_e2_closure.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
        incidental = paths - allowed
        if (
            required - paths
            or incidental != {'/E9"'}
            or data.count(b"/dev/kmsg") != 1
            or any(data.count(value.encode("ascii")) != 1 for value in incidental)
        ):
            raise p300_e2_closure.ClosureError(
                "P3.03 effective init authority path set differs"
            )
        scrubbed = data
        for value in sorted(incidental):
            encoded = value.encode("ascii")
            scrubbed = scrubbed.replace(encoded, b"\0" * len(encoded))
        old_required = p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS
        old_allowed = p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS
        p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS = required
        p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS = allowed
        try:
            with p300_e2_closure._p300_authority_globals():  # noqa: SLF001
                p300_e2_closure._P282_VALIDATE_AUTHORITY_STRINGS(scrubbed)  # noqa: SLF001
        finally:
            p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS = old_required
            p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS = old_allowed

    p300_e2_closure.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
    try:
        yield
    finally:
        p300_e2_closure.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001


@contextmanager
def _p306_e2_authority_context(
    closure_api: Any, expected_init: dict[str, Any]
):
    if closure_api is not p304_e2_closure:
        raise EvidenceError("P3.06 parent stock-closure adapter differs")
    previous = p300_e2_closure.p286.p282._validate_p282_authority_strings  # noqa: SLF001

    def validate(data: bytes) -> None:
        if e2_closure.receipt(data) != expected_init:
            raise p300_e2_closure.ClosureError(
                "P3.06 effective init differs from bound identity"
            )
        additions = {
            "/dev/kmsg",
            "/sys/kernel/debug",
            "/sys/kernel/debug/ipc_logging/a600000_ssusb/log",
        }
        required = frozenset(
            {*p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS, *additions}
        )
        allowed = frozenset(
            {*p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS, *additions}
        )
        printable = p300_e2_closure.p286.p282.p280.isolated_p260._printable_strings(  # noqa: SLF001
            data
        )
        paths = p300_e2_closure.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
        incidental = paths - allowed
        if (
            required - paths
            or incidental != {'/E9"'}
            or data.count(b"/dev/kmsg") != 1
            or data.count(b"/sys/kernel/debug/ipc_logging/a600000_ssusb/log") != 1
            or any(data.count(value.encode("ascii")) != 1 for value in incidental)
        ):
            raise p300_e2_closure.ClosureError(
                "P3.06 effective init authority path set differs"
            )
        scrubbed = data
        for value in sorted(incidental):
            encoded = value.encode("ascii")
            scrubbed = scrubbed.replace(encoded, b"\0" * len(encoded))
        old_required = p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS
        old_allowed = p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS
        p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS = required
        p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS = allowed
        try:
            with p300_e2_closure._p300_authority_globals():  # noqa: SLF001
                p300_e2_closure._P282_VALIDATE_AUTHORITY_STRINGS(scrubbed)  # noqa: SLF001
        finally:
            p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS = old_required
            p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS = old_allowed

    p300_e2_closure.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
    try:
        yield
    finally:
        p300_e2_closure.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001


@contextmanager
def _p307_e2_authority_context(
    closure_api: Any, expected_init: dict[str, Any]
):
    if closure_api is not p304_e2_closure:
        raise EvidenceError("P3.07 parent stock-closure adapter differs")
    previous = p300_e2_closure.p286.p282._validate_p282_authority_strings  # noqa: SLF001

    def validate(data: bytes) -> None:
        if e2_closure.receipt(data) != expected_init:
            raise p300_e2_closure.ClosureError(
                "P3.07 effective init differs from bound identity"
            )
        additions = {"/dev/kmsg", p307_spec.EUD_CACHE_PATH}
        required = frozenset(
            {*p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS, *additions}
        )
        allowed = frozenset(
            {*p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS, *additions}
        )
        printable = p300_e2_closure.p286.p282.p280.isolated_p260._printable_strings(  # noqa: SLF001
            data
        )
        paths = p300_e2_closure.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
        incidental = paths - allowed
        if (
            required - paths
            or incidental != {'/E9"'}
            or data.count(b"/dev/kmsg") != 1
            or data.count(p307_spec.EUD_CACHE_PATH.encode("ascii")) != 1
            or any(data.count(value.encode("ascii")) != 1 for value in incidental)
        ):
            raise p300_e2_closure.ClosureError(
                "P3.07 effective init authority path set differs"
            )
        scrubbed = data
        for value in sorted(incidental):
            encoded = value.encode("ascii")
            scrubbed = scrubbed.replace(encoded, b"\0" * len(encoded))
        old_required = p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS
        old_allowed = p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS
        p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS = required
        p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS = allowed
        try:
            with p300_e2_closure._p300_authority_globals():  # noqa: SLF001
                p300_e2_closure._P282_VALIDATE_AUTHORITY_STRINGS(scrubbed)  # noqa: SLF001
        finally:
            p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS = old_required
            p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS = old_allowed

    p300_e2_closure.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
    try:
        yield
    finally:
        p300_e2_closure.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001


def _latest_stage_terminal(selected_decoder, profile: str) -> int:
    terminal = getattr(selected_decoder, "TERMINAL_STAGE", None)
    if terminal is None:
        position = getattr(selected_decoder, "TERMINAL_POSITION", None)
        inherited = selected_decoder
        seen: set[int] = set()
        while position is None:
            inherited = getattr(inherited, "inherited", None)
            if inherited is None or id(inherited) in seen:
                break
            seen.add(id(inherited))
            position = getattr(inherited, "TERMINAL_POSITION", None)
        if (
            isinstance(position, tuple)
            and len(position) == 2
            and type(position[0]) is int
        ):
            terminal = position[0]
    if terminal is None:
        terminal = selected_decoder.model.PROFILE_TERMINALS.get(profile)
    if (
        isinstance(terminal, bool)
        or not isinstance(terminal, int)
        or not 0 <= terminal <= 0xFF
    ):
        raise EvidenceError("selected decoder terminal stage is invalid")
    return terminal


def _expected_reachable_record_contract(
    profile: str,
    source_contract_id: str | None,
    run_id_hex: str,
) -> dict[str, Any]:
    if source_contract_id is None:
        return {
            "reachable_slot_variants": _e1_reachable_slot_variant_count(
                profile
            ),
            "profiles": [profile],
            "checked_run_ids": {profile: run_id_hex},
            "adjacent_slot_combinations_verified": True,
            "zero_crc_count": 0,
            "family_collision_count": 0,
            "decoder_policy_id": e1_latest_stage.POLICY_ID,
            "verified": True,
        }
    try:
        result = _selected_contract(
            source_contract_id, profile
        ).validate_reachable_records(bytes.fromhex(run_id_hex))
    except (TypeError, ValueError) as exc:
        raise EvidenceError(
            "versioned reachable-record contract validation failed"
        ) from exc
    if not isinstance(result, dict):
        raise EvidenceError(
            "versioned reachable-record contract is not structured"
        )
    return dict(result)


def _validate_reachable_record_contract(
    value: Any,
    profile: str,
    source_contract_id: str | None,
    run_id_hex: str,
) -> dict[str, Any]:
    expected = _expected_reachable_record_contract(
        profile, source_contract_id, run_id_hex
    )
    actual = _exact(
        value,
        set(expected),
        "versioned reachable-record contract",
    )
    if any(
        type(actual[name]) is not type(expected_value)
        for name, expected_value in expected.items()
    ) or actual != expected:
        raise EvidenceError(
            "candidate static source contract is not E1A-bound, "
            "E1B-bound, or E2-bound: reachable-record contract "
            "differs from its source"
        )
    return actual


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise EvidenceError(f"{label} keys do not match the evidence schema")
    return value


def _artifact(value: Any, label: str) -> dict[str, Any]:
    item = _exact(value, {"path", "size", "sha256"}, label)
    if (
        not isinstance(item["path"], str)
        or not item["path"]
        or isinstance(item["size"], bool)
        or not isinstance(item["size"], int)
        or not 1 <= item["size"] <= 1024 * 1024
        or not isinstance(item["sha256"], str)
        or HASH_RE.fullmatch(item["sha256"]) is None
    ):
        raise EvidenceError(f"{label} identity is invalid")
    return item


def _artifact_matches(value: Any, expected: dict[str, Any]) -> bool:
    return (
        isinstance(value, dict)
        and value.get("size") == expected.get("size")
        and value.get("sha256") == expected.get("sha256")
    )


def _binary_identity(value: Any, label: str) -> dict[str, Any]:
    item = _exact(value, {"size", "sha256"}, label)
    if (
        isinstance(item["size"], bool)
        or not isinstance(item["size"], int)
        or not 1 <= item["size"] <= 2**40
        or not isinstance(item["sha256"], str)
        or HASH_RE.fullmatch(item["sha256"]) is None
    ):
        raise EvidenceError(f"{label} identity is invalid")
    return item


def _validate_p298_historical_build_repair(
    source_build: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    repair = source_build.get("tier2_repair")
    expected_repair_keys = {
        "schema",
        "historical_postbuild_result",
        "historical_pre_lto_qualification",
        "a_b_artifacts_reopened",
        "a_b_artifact_inodes_distinct",
        "byte_identical_artifacts_reverified",
        "tier1_candidate_identity_changed",
        "tier2_repair_files",
        "fresh_full_lto_claimed",
        "verified",
    }
    expected_equal = sorted(P298_BUILD_ARTIFACTS - {"build-result.json"})
    if (
        source_build.get("fresh_reverification") is not False
        or source_build.get("immutable_build_time_proof_revalidated") is not True
        or source_build.get("result") != P298_HISTORICAL_POSTBUILD_RESULT
        or not isinstance(repair, dict)
        or set(repair) != expected_repair_keys
        or repair.get("schema")
        != "s22plus_fyg8_p298_postbuild_tier2_repair_v1"
        or repair.get("historical_postbuild_result")
        != P298_HISTORICAL_POSTBUILD_RESULT
        or repair.get("historical_pre_lto_qualification")
        != P298_HISTORICAL_QUALIFICATION
        or repair.get("a_b_artifact_inodes_distinct") is not True
        or repair.get("byte_identical_artifacts_reverified") != expected_equal
        or repair.get("tier1_candidate_identity_changed") is not False
        or repair.get("fresh_full_lto_claimed") is not False
        or repair.get("verified") is not True
    ):
        raise EvidenceError("P2.98 historical build repair contract differs")

    reopened = repair.get("a_b_artifacts_reopened")
    if not isinstance(reopened, dict) or set(reopened) != {"build_a", "build_b"}:
        raise EvidenceError("P2.98 historical A/B artifact proof is incomplete")
    normalized: dict[str, dict[str, dict[str, Any]]] = {}
    for build_name in ("build_a", "build_b"):
        artifacts = reopened.get(build_name)
        if not isinstance(artifacts, dict) or set(artifacts) != P298_BUILD_ARTIFACTS:
            raise EvidenceError(
                f"P2.98 historical {build_name} artifact inventory differs"
            )
        normalized[build_name] = {
            name: _binary_identity(value, f"P2.98 {build_name} {name}")
            for name, value in artifacts.items()
        }
    for name in expected_equal:
        if normalized["build_a"][name] != normalized["build_b"][name]:
            raise EvidenceError(f"P2.98 historical A/B {name} receipt differs")
    image = _binary_identity(source_build.get("image"), "P2.98 kernel Image")
    if (
        normalized["build_a"]["Image"] != image
        or normalized["build_b"]["Image"] != image
    ):
        raise EvidenceError("P2.98 historical A/B Image identity differs")

    expected_repair_paths = {
        p298_identity.TIER2_DIRECT_PATHS[name].as_posix()
        for name in P298_REPAIR_TIER2_KEYS
    }
    repair_files = repair.get("tier2_repair_files")
    if not isinstance(repair_files, dict) or set(repair_files) != expected_repair_paths:
        raise EvidenceError("P2.98 Tier-2 repair file inventory differs")
    return {
        path: _binary_identity(value, f"P2.98 Tier-2 repair {path}")
        for path, value in repair_files.items()
    }


def validate_candidate_source_preimage(
    contract: dict[str, Any], profile: str, run_id: str
) -> dict[str, dict[str, Any]]:
    source_contract_id = contract.get("source_contract_id")
    selected_decoder = _latest_stage_decoder(source_contract_id, profile)
    preimage_keys = {
        "schema",
        "target",
        "profile",
        "profile_number",
        "nonce",
        "decoder_id",
        "decoder_policy_id",
        "record_layout",
        "sources",
    }
    if source_contract_id is not None:
        _selected_contract(source_contract_id, profile)
        preimage_keys.add("source_contract_id")
    preimage = _exact(
        contract.get("identity_preimage"),
        preimage_keys,
        "candidate identity preimage",
    )
    source_keys = (
        _selected_contract(source_contract_id, profile).source_keys
        if source_contract_id is not None
        else E1_LATEST_STAGE_SOURCE_KEYS.get(profile)
    )
    sources = preimage.get("sources")
    if source_keys is None or not isinstance(sources, dict) or set(sources) != source_keys:
        raise EvidenceError("candidate identity source set is invalid")
    normalized_sources = {
        name: _binary_identity(value, f"candidate source {name}")
        for name, value in sources.items()
    }
    preimage_sha256 = hashlib.sha256(_canonical(preimage)).hexdigest()
    nonce = preimage.get("nonce")
    expected_schema = (
        _selected_contract(source_contract_id, profile).preimage_schema
        if source_contract_id is not None
        else E1_LATEST_STAGE_PREIMAGE_SCHEMA
    )
    run_id_domain = (
        _selected_contract(source_contract_id, profile).run_id_domain
        if source_contract_id is not None
        else E1_LATEST_STAGE_RUN_ID_DOMAINS[profile]
    )
    if (
        preimage.get("schema") != expected_schema
        or preimage.get("source_contract_id") != source_contract_id
        or preimage.get("target") != PID1_USERSPACE_TARGET
        or preimage.get("profile") != profile
        or type(preimage.get("profile_number")) is not int
        or preimage.get("profile_number")
        != selected_decoder.model.PROFILE_NUMBERS[profile]
        or not isinstance(nonce, str)
        or HEX32_RE.fullmatch(nonce) is None
        or nonce == "0" * 32
        or preimage.get("decoder_id") != selected_decoder.DECODER_ID
        or preimage.get("decoder_policy_id") != selected_decoder.POLICY_ID
        or preimage.get("record_layout")
        != (
            "S22E1L2-192-ab-header-slot-crc-payload64"
            if source_contract_id == P310_SOURCE_CONTRACT_ID
            else "S22E1L1-45-ab-crc32"
        )
        or contract.get("identity_preimage_sha256") != preimage_sha256
        or hashlib.sha256(
            run_id_domain + _canonical(preimage)
        ).digest()[:16].hex()
        != run_id
    ):
        raise EvidenceError("candidate source preimage or run ID derivation is invalid")
    return normalized_sources


def _generic_rootfs_module_closure(
    source_contract_id: str | None,
    closure_api: Any,
    module_closure: dict[str, Any],
) -> dict[str, Any]:
    if closure_api is p304_e2_closure:
        return module_closure
    if source_contract_id == P310_SOURCE_CONTRACT_ID:
        if closure_api not in {
            p310_e2_closure.select(P310_SOURCE_CONTRACT_ID),
            p311_e2_closure.select(P310_SOURCE_CONTRACT_ID),
            p312_e2_closure.select(P310_SOURCE_CONTRACT_ID),
        }:
            raise EvidenceError("P3.10 generic-rootfs closure adapter differs")
        return module_closure
    if source_contract_id not in {
        e2_closure_selector.P280_CONTRACT_ID,
        e2_closure_selector.P282_CONTRACT_ID,
        e2_closure_selector.P284_CONTRACT_ID,
        P286_SOURCE_CONTRACT_ID,
        P288_SOURCE_CONTRACT_ID,
        P290_SOURCE_CONTRACT_ID,
        P292_SOURCE_CONTRACT_ID,
        P294_SOURCE_CONTRACT_ID,
        P296_SOURCE_CONTRACT_ID,
        P298_SOURCE_CONTRACT_ID,
        P300_SOURCE_CONTRACT_ID,
        P310_SOURCE_CONTRACT_ID,
    }:
        return module_closure
    adapter_api = closure_api
    label = "P2.80"
    if source_contract_id in {
        e2_closure_selector.P284_CONTRACT_ID,
        P286_SOURCE_CONTRACT_ID,
        P288_SOURCE_CONTRACT_ID,
        P290_SOURCE_CONTRACT_ID,
        P292_SOURCE_CONTRACT_ID,
        P294_SOURCE_CONTRACT_ID,
        P296_SOURCE_CONTRACT_ID,
        P298_SOURCE_CONTRACT_ID,
        P300_SOURCE_CONTRACT_ID,
        P310_SOURCE_CONTRACT_ID,
    }:
        inherited_p282 = getattr(closure_api, "p282", None)
        adapter_api = getattr(inherited_p282, "p280", None)
        label = {
            P286_SOURCE_CONTRACT_ID: "P2.86",
            P288_SOURCE_CONTRACT_ID: "P2.88",
            P290_SOURCE_CONTRACT_ID: "P2.90",
            P292_SOURCE_CONTRACT_ID: "P2.92",
            P294_SOURCE_CONTRACT_ID: "P2.94",
            P296_SOURCE_CONTRACT_ID: "P2.96",
            P298_SOURCE_CONTRACT_ID: "P2.98",
            P300_SOURCE_CONTRACT_ID: "P3.00",
            P310_SOURCE_CONTRACT_ID: "P3.10",
            e2_closure_selector.P284_CONTRACT_ID: "P2.84",
        }[source_contract_id]
    elif source_contract_id == e2_closure_selector.P282_CONTRACT_ID:
        adapter_api = getattr(closure_api, "p280", None)
        label = "P2.82"
    try:
        if (
            getattr(
                getattr(adapter_api, "source_contract", None),
                "CONTRACT_ID",
                None,
            )
            != e2_closure_selector.P280_CONTRACT_ID
        ):
            raise AttributeError
        p257_adapter = adapter_api.isolated_p260.p257
        p253_adapter = adapter_api.isolated_p260.p253
        full_count = module_closure.get("count")
        if (
            isinstance(full_count, bool)
            or not isinstance(full_count, int)
            or full_count != closure_api.EXPECTED_MODULE_COUNT
        ):
            raise EvidenceError(
                f"{label} full module closure count is invalid"
            )
        expected_count = full_count - 1
        adapted = p253_adapter._legacy_view(
            p257_adapter._legacy_view(module_closure)
        )
    except (AttributeError, e2_closure.ClosureError) as exc:
        raise EvidenceError(
            f"{label} generic-rootfs module adapter is unavailable"
        ) from exc
    adapted_modules = adapted.get("modules") if isinstance(adapted, dict) else None
    if (
        not isinstance(adapted, dict)
        or adapted is module_closure
        or adapted.get("count") != expected_count
        or not isinstance(adapted_modules, list)
        or len(adapted_modules) != expected_count
    ):
        raise EvidenceError(
            f"{label} generic-rootfs module adapter result is invalid"
        )
    return adapted


def _latest_stage_accepted_identity(
    profile: str,
    source_contract_id: str | None,
    userspace_overlay_contract_id: str | None,
) -> str:
    if (
        userspace_overlay_contract_id in P301_TELEMETRY_OVERLAY_IDS
        or source_contract_id == P310_SOURCE_CONTRACT_ID
    ):
        return "P301_TELEMETRY_RETAINED"
    return f"{profile}_TERMINAL_SUCCESS_REACHED"


def validate_e2_ap_payload(
    frame: bytes, closure: Any
) -> dict[str, Any]:
    source_contract_id = (
        closure.get("source_contract_id") if isinstance(closure, dict) else None
    )
    userspace_overlay_contract_id = (
        closure.get("userspace_overlay_contract_id")
        if isinstance(closure, dict)
        else None
    )
    expected_keys = {
        "boot_img_lz4",
        "boot_image",
        "image",
        "init",
        "child",
        "run_id",
        "module_closure",
        "effective_rootfs",
    }
    if source_contract_id is not None:
        _selected_contract(source_contract_id, "E2")
        expected_keys.add("source_contract_id")
    if userspace_overlay_contract_id is not None:
        _latest_stage_observation_decoder(
            source_contract_id,
            "E2",
            userspace_overlay_contract_id,
        )
        expected_keys.add("userspace_overlay_contract_id")
    closure_api = _select_e2_closure(
        source_contract_id, userspace_overlay_contract_id
    )
    expected = _exact(
        closure,
        expected_keys,
        "E2 AP payload closure",
    )
    identities = {
        name: _binary_identity(value, f"E2 AP {name}")
        for name, value in expected.items()
        if name in {"boot_img_lz4", "boot_image", "image", "init", "child"}
    }
    run_id = expected.get("run_id")
    if not isinstance(run_id, str) or HEX32_RE.fullmatch(run_id) is None:
        raise EvidenceError("E2 AP run ID is invalid")
    try:
        module_closure = closure_api.validate_module_closure(
            expected.get("module_closure")
        )
        effective_rootfs = closure_api.validate_effective_rootfs(
            expected.get("effective_rootfs"),
            expected_init=identities["init"],
            expected_child=identities["child"],
            module_closure=module_closure,
        )
    except e2_closure.ClosureError as exc:
        raise EvidenceError("E2 AP semantic closure is invalid") from exc
    if e2_closure.receipt(frame) != identities["boot_img_lz4"]:
        raise EvidenceError("E2 AP boot member identity mismatch")
    try:
        boot_payload = e2_closure.boot_verify.decompress_lz4_frame_python(
            frame,
            expected_size=identities["boot_image"]["size"],
        )
        if e2_closure.receipt(boot_payload) != identities["boot_image"]:
            raise EvidenceError("E2 AP decoded boot identity mismatch")
        boot = e2_closure.boot_verify.parse_boot_v4(boot_payload)
        if e2_closure.receipt(boot.kernel) != identities["image"]:
            raise EvidenceError("E2 AP kernel identity mismatch")
        ramdisk = e2_closure.boot_verify.decompress_lz4_stream_python(
            boot.ramdisk, maximum=128 * 1024 * 1024
        )
        entries = e2_closure.boot_verify.parse_newc(ramdisk)
        generic_module_closure = _generic_rootfs_module_closure(
            source_contract_id, closure_api, module_closure
        )
        if userspace_overlay_contract_id == P312_OVERLAY_CONTRACT_ID:
            authority_context = _p312_e2_authority_context(
                closure_api, entries, identities["init"]
            )
        elif userspace_overlay_contract_id == P311_OVERLAY_CONTRACT_ID:
            authority_context = _p311_e2_authority_context(
                closure_api, entries, identities["init"]
            )
        elif source_contract_id == P310_SOURCE_CONTRACT_ID:
            authority_context = _p310_e2_authority_context(
                closure_api, entries, identities["init"]
            )
        elif userspace_overlay_contract_id in {
            P307_OVERLAY_CONTRACT_ID,
            P308_OVERLAY_CONTRACT_ID,
        }:
            authority_context = _p307_e2_authority_context(
                closure_api, identities["init"]
            )
        elif userspace_overlay_contract_id == P306_OVERLAY_CONTRACT_ID:
            authority_context = _p306_e2_authority_context(
                closure_api, identities["init"]
            )
        elif userspace_overlay_contract_id in {
            P303_OVERLAY_CONTRACT_ID,
            P304_OVERLAY_CONTRACT_ID,
            P305_OVERLAY_CONTRACT_ID,
        }:
            authority_context = _p303_e2_authority_context(
                closure_api, identities["init"]
            )
        elif userspace_overlay_contract_id in P301_TELEMETRY_OVERLAY_IDS:
            authority_context = _p301_e2_authority_context(
                closure_api, identities["init"]
            )
        else:
            authority_context = _e2_authority_context(
                source_contract_id, closure_api
            )
        with authority_context:
            generic_rootfs = closure_api.audit_candidate_generic_rootfs(
                boot,
                entries,
                expected_init=identities["init"],
                expected_child=identities["child"],
                run_id=bytes.fromhex(run_id),
                module_closure=generic_module_closure,
            )
    except e2_closure.boot_verify.BootVerifyError as exc:
        raise EvidenceError("E2 AP payload cannot be independently decoded") from exc
    except e2_closure.ClosureError as exc:
        raise EvidenceError("E2 AP executable semantics mismatch") from exc
    if _canonical(generic_rootfs) != _canonical(effective_rootfs["generic_rootfs"]):
        raise EvidenceError("E2 AP generic rootfs differs from static closure")
    return {"verified": True, **identities, "generic_rootfs": generic_rootfs}


def validate_e1b_stock_closure(
    *,
    module_closure: Any,
    effective_rootfs: Any,
    stock_vendor_boot: Any,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
) -> None:
    closure = _exact(
        module_closure,
        {
            "files",
            "runtime_names",
            "count",
            "modules",
            "order_model",
            "stock_recovery_positions",
            "vendor_metadata_hashes",
        },
        "E1B module closure",
    )
    expected_closure = {
        "files": E1B_MODULE_FILES,
        "runtime_names": E1B_MODULE_RUNTIME_NAMES,
        "count": len(E1B_MODULE_FILES),
        "modules": E1B_MODULE_SPECS,
        "order_model": E1B_MODULE_ORDER_MODEL,
        "stock_recovery_positions": E1B_STOCK_RECOVERY_POSITIONS,
        "vendor_metadata_hashes": E1B_VENDOR_METADATA_HASHES,
    }
    if closure != expected_closure:
        raise EvidenceError("E1B stock module derivation differs from the pinned closure")

    rootfs = _exact(
        effective_rootfs,
        {
            "composition_order",
            "entry_count",
            "no_duplicate_override_or_alias",
            "init",
            "child",
            "modules",
            "module_count",
            "rdinit_override_absent",
            "verified",
        },
        "E1B effective rootfs",
    )
    init = _exact(
        rootfs["init"],
        {"size", "sha256", "elf", "run_id_count"},
        "E1B effective init",
    )
    child = _exact(
        rootfs["child"], {"size", "sha256", "elf"}, "E1B effective child"
    )
    init_elf = _exact(
        init["elf"],
        {
            "machine",
            "entrypoint",
            "interpreter",
            "dynamic",
            "executable_stack",
            "entrypoint_mapped",
            "verified",
        },
        "E1B effective init ELF",
    )
    child_elf = _exact(
        child["elf"],
        {
            "machine",
            "entrypoint",
            "interpreter",
            "dynamic",
            "executable_stack",
            "entrypoint_mapped",
            "verified",
        },
        "E1B effective child ELF",
    )
    expected_elf = {
        "machine": "AArch64",
        "interpreter": False,
        "dynamic": False,
        "executable_stack": False,
        "entrypoint_mapped": True,
        "verified": True,
    }
    if (
        _binary_identity(
            {name: init[name] for name in ("size", "sha256")},
            "E1B effective init",
        )
        != expected_init
        or _binary_identity(
            {name: child[name] for name in ("size", "sha256")},
            "E1B effective child",
        )
        != expected_child
        or init.get("run_id_count") != 1
        or init_elf
        != {**expected_elf, "entrypoint": E1B_ELF_ENTRYPOINTS["init"]}
        or child_elf
        != {**expected_elf, "entrypoint": E1B_ELF_ENTRYPOINTS["child"]}
        or rootfs.get("composition_order") != E1B_COMPOSITION_ORDER
        or rootfs.get("entry_count") != E1B_EFFECTIVE_ENTRY_COUNT
        or rootfs.get("no_duplicate_override_or_alias") is not True
        or rootfs.get("modules") != E1B_EFFECTIVE_MODULE_ROWS
        or rootfs.get("module_count") != len(E1B_EFFECTIVE_MODULE_ROWS)
        or rootfs.get("rdinit_override_absent") is not True
        or rootfs.get("verified") is not True
    ):
        raise EvidenceError("E1B effective stock rootfs differs from the pinned closure")

    if _binary_identity(stock_vendor_boot, "E1B stock vendor_boot") != E1B_STOCK_VENDOR_BOOT:
        raise EvidenceError("E1B stock vendor_boot identity changed")


def _record_blob_claim(
    value: Any, label: str, artifact: dict[str, Any]
) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "label",
            "size",
            "sha256",
            "entry_count",
            "userspace_count",
            "unsat_count",
            "long_family_count",
            "unsat_family_count",
            "old_e0_entry_count",
            "old_e0_userspace_count",
            "verified",
        },
        label,
    )
    expected_counts = {
        "entry_count": 1,
        "userspace_count": 1,
        "unsat_count": 1,
        "long_family_count": 2,
        "unsat_family_count": 1,
        "old_e0_entry_count": 0,
        "old_e0_userspace_count": 0,
    }
    if (
        item["label"] != label
        or not _artifact_matches(item, artifact)
        or any(item[key] != count for key, count in expected_counts.items())
        or item["verified"] is not True
    ):
        raise EvidenceError(f"{label} record claim is invalid")
    return item


def _bounded_text(value: Any, label: str, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum
        or "\x00" in value
    ):
        raise EvidenceError(f"{label} must be a bounded string")
    return value


def validate_acceptance(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("acceptance must be an object")
    kind = value.get("kind")
    if kind == MARKER_KIND:
        item = _exact(
            value,
            {"kind", "source", "marker", "family", "exact_count"},
            "marker acceptance",
        )
        if item["source"] != CHECKPOINT_SOURCE or item["exact_count"] != 1:
            raise EvidenceError("marker acceptance source or count is invalid")
        _bounded_text(item["marker"], "acceptance.marker", 512)
        _bounded_text(item["family"], "acceptance.family", 128)
        return item
    if kind == SAME_RING_KIND:
        item = _exact(
            value,
            {
                "kind",
                "source",
                "decoder",
                "contract_id",
                "records",
                "families",
                "accepted_identity",
                "exact_count",
                "contract",
            },
            "same-ring acceptance",
        )
        expected_records = {
            "entry_hex": same_ring.ENTRY_PROOF.hex(),
            "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
            "unsat_hex": same_ring.UNSAT_PROOF.hex(),
        }
        expected_families = {
            "long_hex": same_ring.ENTRY_FAMILY.hex(),
            "unsat_hex": same_ring.UNSAT_FAMILY.hex(),
        }
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["decoder"] != SAME_RING_DECODER
            or item["contract_id"] != SAME_RING_CONTRACT_ID
            or item["records"] != expected_records
            or item["families"] != expected_families
            or item["accepted_identity"] != "USERSPACE_CALLBACK_REACHED"
            or item["exact_count"] != 1
        ):
            raise EvidenceError("same-ring acceptance identity is invalid")
        contract = _exact(
            item["contract"],
            {"run_manifest", "static_check"},
            "same-ring contract",
        )
        _artifact(contract["run_manifest"], "same-ring contract run_manifest")
        _artifact(contract["static_check"], "same-ring contract static_check")
        return item
    if kind == SAME_RING_MULTIBOOT_KIND:
        item = _exact(
            value,
            {
                "kind",
                "source",
                "decoder",
                "contract_id",
                "policy_id",
                "records",
                "families",
                "accepted_identity",
                "minimum_exact_count",
                "contract",
            },
            "same-ring multiboot acceptance",
        )
        expected_records = {
            "entry_hex": same_ring.ENTRY_PROOF.hex(),
            "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
            "unsat_hex": same_ring.UNSAT_PROOF.hex(),
        }
        expected_families = {
            "long_hex": same_ring.ENTRY_FAMILY.hex(),
            "unsat_hex": same_ring.UNSAT_FAMILY.hex(),
        }
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["decoder"] != SAME_RING_MULTIBOOT_DECODER
            or item["contract_id"] != SAME_RING_CONTRACT_ID
            or item["policy_id"] != SAME_RING_MULTIBOOT_POLICY_ID
            or item["records"] != expected_records
            or item["families"] != expected_families
            or item["accepted_identity"]
            != "USERSPACE_CALLBACK_REACHED_ONE_OR_MORE_BOOTS"
            or item["minimum_exact_count"] != 1
        ):
            raise EvidenceError("same-ring multiboot acceptance identity is invalid")
        contract = _exact(
            item["contract"],
            {"run_manifest", "static_check"},
            "same-ring multiboot contract",
        )
        _artifact(
            contract["run_manifest"],
            "same-ring multiboot contract run_manifest",
        )
        _artifact(
            contract["static_check"],
            "same-ring multiboot contract static_check",
        )
        return item
    if kind == E1_LATEST_STAGE_KIND:
        source_contract_id = value.get("source_contract_id")
        userspace_overlay_contract_id = value.get(
            "userspace_overlay_contract_id"
        )
        expected_keys = {
            "kind",
            "source",
            "decoder",
            "policy_id",
            "profile",
            "run_id",
            "long_family_hex",
            "unsat_family_hex",
            "terminal_stage",
            "minimum_success_count",
            "clean_baseline_required",
            "contract",
        }
        if source_contract_id is not None:
            expected_keys.add("source_contract_id")
        if userspace_overlay_contract_id is not None:
            expected_keys.add("userspace_overlay_contract_id")
        item = _exact(
            value,
            expected_keys,
            "E1 latest-stage acceptance",
        )
        profile = item["profile"]
        selected_decoder = _latest_stage_observation_decoder(
            source_contract_id,
            profile,
            userspace_overlay_contract_id,
        )
        model = selected_decoder.model
        terminal_stage = _latest_stage_terminal(selected_decoder, profile)
        model_ids = {model.model_run_id(name).hex() for name in model.PROFILE_NUMBERS}
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["decoder"] != selected_decoder.DECODER_ID
            or item["policy_id"] != selected_decoder.POLICY_ID
            or profile not in model.PROFILE_NUMBERS
            or not isinstance(item["run_id"], str)
            or HEX32_RE.fullmatch(item["run_id"]) is None
            or item["run_id"] == "0" * 32
            or item["run_id"] in model_ids
            or item["long_family_hex"] != model.LONG_FAMILY.hex()
            or item["unsat_family_hex"] != model.UNSAT_FAMILY.hex()
            or item["terminal_stage"] != terminal_stage
            or item["minimum_success_count"] != 1
            or item["clean_baseline_required"] is not True
        ):
            raise EvidenceError("E1 latest-stage acceptance identity is invalid")
        contract_keys = {"candidate_static", "run_manifest", "static_check"}
        stock_keys = {"stock_baseline_raw", "stock_baseline_result"}
        if userspace_overlay_contract_id in {
            P303_OVERLAY_CONTRACT_ID,
            P304_OVERLAY_CONTRACT_ID,
            P305_OVERLAY_CONTRACT_ID,
        }:
            supplied = stock_keys & set(item["contract"])
            if supplied not in (set(), stock_keys):
                raise EvidenceError(
                    "P3.03 stock baseline contract must be absent or an exact pair"
                )
            contract_keys.update(supplied)
        contract = _exact(
            item["contract"],
            contract_keys,
            "E1 latest-stage contract",
        )
        _artifact(contract["candidate_static"], "E1 latest-stage candidate_static")
        _artifact(contract["run_manifest"], "E1 latest-stage run_manifest")
        _artifact(contract["static_check"], "E1 latest-stage static_check")
        if stock_keys <= set(contract):
            _artifact(
                contract["stock_baseline_raw"],
                "P3.03 stock baseline raw",
            )
            _artifact(
                contract["stock_baseline_result"],
                "P3.03 stock baseline result",
            )
        return item
    if kind == PID1_USERSPACE_KIND:
        item = _exact(
            value,
            {
                "kind",
                "source",
                "marker",
                "family",
                "exact_count",
                "decoder",
                "probe_id",
                "entry_marker",
                "contract",
            },
            "PID1 userspace acceptance",
        )
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["marker"] != PID1_USERSPACE_PROOF.decode("ascii")
            or item["entry_marker"] != PID1_USERSPACE_ENTRY.decode("ascii")
            or item["family"] != PID1_USERSPACE_FAMILY.decode("ascii")
            or item["exact_count"] != 1
            or item["decoder"] != PID1_USERSPACE_DECODER
            or item["probe_id"] != PID1_USERSPACE_PROBE_ID
        ):
            raise EvidenceError("PID1 userspace acceptance identity is invalid")
        contract = _exact(
            item["contract"],
            {"run_manifest", "static_check"},
            "PID1 userspace contract",
        )
        _artifact(contract["run_manifest"], "PID1 userspace contract run_manifest")
        _artifact(contract["static_check"], "PID1 userspace contract static_check")
        return item
    if kind != CHECKPOINT_KIND:
        raise EvidenceError("acceptance kind is not allowlisted")

    item = _exact(
        value,
        {
            "kind",
            "source",
            "marker",
            "family",
            "exact_count",
            "decoder",
            "profile",
            "run_id",
            "terminal_stage",
            "terminal_outcome",
            "require_two_valid_slots",
            "contract",
        },
        "checkpoint acceptance",
    )
    if (
        item["source"] != CHECKPOINT_SOURCE
        or item["marker"] != checkpoint.ENTRY_PROOF.decode("ascii")
        or item["family"] != checkpoint.ENTRY_FAMILY.decode("ascii")
        or item["exact_count"] != 1
        or item["decoder"] != CHECKPOINT_DECODER
        or item["profile"] != "E1"
        or item["terminal_stage"] != checkpoint.PROFILE_TERMINAL_STAGE["E1"]
        or item["terminal_outcome"] != "success"
        or item["require_two_valid_slots"] is not True
        or not isinstance(item["run_id"], str)
        or HEX32_RE.fullmatch(item["run_id"]) is None
        or item["run_id"] == "0" * 32
        or item["run_id"]
        == checkpoint.MODEL_RUN_IDS["E1"].hex()
    ):
        raise EvidenceError("checkpoint acceptance identity is invalid")
    contract = _exact(
        item["contract"], {"run_manifest", "static_check"}, "checkpoint contract"
    )
    _artifact(contract["run_manifest"], "checkpoint contract run_manifest")
    _artifact(contract["static_check"], "checkpoint contract static_check")
    return item


def contract_artifacts(acceptance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    item = validate_acceptance(acceptance)
    if item["kind"] not in {
        CHECKPOINT_KIND,
        PID1_USERSPACE_KIND,
        SAME_RING_KIND,
        SAME_RING_MULTIBOOT_KIND,
        E1_LATEST_STAGE_KIND,
    }:
        return {}
    return {
        name: dict(value)
        for name, value in item["contract"].items()
    }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise EvidenceError(f"duplicate evidence JSON key: {key}")
        value[key] = item
    return value


def _json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{label} is not canonical JSON") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} is not an object")
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise EvidenceError("run manifest is not canonical ASCII JSON") from exc


def _verify_checkpoint_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != CHECKPOINT_KIND:
        raise EvidenceError("offline checkpoint contract is not applicable")
    if set(payloads) != {"run_manifest", "static_check"} or set(receipts) != set(
        payloads
    ):
        raise EvidenceError("offline checkpoint contract artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        receipt = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipt.get("size") != pin["size"]
            or receipt.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline checkpoint contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "run manifest")
    static_result = _json(payloads["static_check"], "static checker result")
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    run_id = canonical_sha256[:32]
    if (
        run_manifest.get("schema")
        != "s22plus_fyg8_r4w1e_e1_run_manifest_v1"
        or run_manifest.get("target") != checkpoint.TARGET
        or run_manifest.get("profile") != item["profile"]
        or run_manifest.get("checkpoint_carrier_sha256")
        != checkpoint.CARRIER_SHA256
        or run_manifest.get("checkpoint_patch_sha256") != checkpoint.PATCH_SHA256
        or run_id != item["run_id"]
    ):
        raise EvidenceError("run manifest does not bind the checkpoint acceptance")

    binding = static_result.get("run_binding")
    candidate = static_result.get("candidate")
    artifacts = candidate.get("artifacts") if isinstance(candidate, dict) else None
    blockers = static_result.get("blockers")
    safety = static_result.get("safety")
    if (
        static_result.get("schema")
        != "s22plus_fyg8_r4w1e_e1_candidate_static_checker_v1"
        or static_result.get("target") != checkpoint.TARGET
        or static_result.get("verdict")
        != "PASS_R4W1E_E1_OFFLINE_CANDIDATE_STATIC_CONTRACT"
        or blockers != []
        or not isinstance(binding, dict)
        or binding.get("run_id") != item["run_id"]
        or binding.get("canonical_manifest_size") != len(canonical)
        or binding.get("canonical_manifest_sha256") != canonical_sha256
        or binding.get("fresh_non_model_id") is not True
        or binding.get("verified") is not True
        or not isinstance(artifacts, dict)
        or not _artifact_matches(artifacts.get("ap"), candidate_ap)
        or not _artifact_matches(
            artifacts.get("run_manifest"), receipts["run_manifest"]
        )
        or candidate.get("boot_only_ap") is not True
        or not isinstance(safety, dict)
        or safety.get("host_only") is not True
        or any(
            safety.get(key) is not False
            for key in (
                "device_contact",
                "device_write",
                "odin_invoked",
                "odin_transfer",
                "flash",
                "partition_write",
                "live_authorized",
            )
        )
    ):
        raise EvidenceError("static checker result does not bind the candidate")
    return {
        "schema": "device_action_f1_checkpoint_offline_contract_v2",
        "decoder": item["decoder"],
        "profile": item["profile"],
        "run_id": item["run_id"],
        "terminal_stage": item["terminal_stage"],
        "candidate_ap_sha256": candidate_ap["sha256"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "verified": True,
    }
def _verify_pid1_userspace_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != PID1_USERSPACE_KIND:
        raise EvidenceError("offline PID1 userspace contract is not applicable")
    if set(payloads) != {"run_manifest", "static_check"} or set(receipts) != set(
        payloads
    ):
        raise EvidenceError("offline PID1 userspace artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        receipt = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipt.get("size") != pin["size"]
            or receipt.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline PID1 userspace contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "run manifest")
    static_result = _json(payloads["static_check"], "static checker result")
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    observation = run_manifest.get("observation_contract")
    if (
        run_manifest.get("schema") != "s22plus_fyg8_r4w1e0_run_manifest_v1"
        or run_manifest.get("target") != PID1_USERSPACE_TARGET
        or run_manifest.get("profile") != "E0"
        or run_manifest.get("probe_id") != item["probe_id"]
        or run_manifest.get("entry_proof")
        != PID1_USERSPACE_ENTRY.decode("ascii").strip()
        or run_manifest.get("userspace_proof")
        != PID1_USERSPACE_PROOF.decode("ascii").strip()
        or observation
        != {
            "accepted_identity": "USERSPACE_CALLBACK_REACHED",
            "baseline_family_count": 0,
            "post_family_count": 1,
        }
    ):
        raise EvidenceError("run manifest does not bind PID1 userspace acceptance")

    binding = static_result.get("run_binding")
    candidate = static_result.get("candidate")
    artifacts = candidate.get("artifacts") if isinstance(candidate, dict) else None
    blockers = static_result.get("blockers")
    safety = static_result.get("safety")
    if (
        static_result.get("schema")
        != "s22plus_fyg8_r4w1e0_candidate_static_checker_v1"
        or static_result.get("target") != PID1_USERSPACE_TARGET
        or static_result.get("verdict")
        != "PASS_R4W1E0_OFFLINE_CANDIDATE_STATIC_CONTRACT"
        or blockers != []
        or not isinstance(binding, dict)
        or binding.get("run_id") != item["probe_id"]
        or binding.get("canonical_manifest_size") != len(canonical)
        or binding.get("canonical_manifest_sha256") != canonical_sha256
        or binding.get("fixed_probe_id") is not True
        or binding.get("clean_baseline_required") is not True
        or binding.get("verified") is not True
        or not isinstance(artifacts, dict)
        or not _artifact_matches(artifacts.get("ap"), candidate_ap)
        or not _artifact_matches(
            artifacts.get("run_manifest"), receipts["run_manifest"]
        )
        or candidate.get("boot_only_ap") is not True
        or not isinstance(safety, dict)
        or safety.get("host_only") is not True
        or any(
            safety.get(key) is not False
            for key in (
                "device_contact",
                "device_write",
                "odin_invoked",
                "odin_transfer",
                "flash",
                "partition_write",
                "live_authorized",
            )
        )
    ):
        raise EvidenceError("static checker result does not bind E0 candidate")
    return {
        "schema": "device_action_f1_pid1_userspace_offline_contract_v2",
        "decoder": item["decoder"],
        "probe_id": item["probe_id"],
        "candidate_ap_sha256": candidate_ap["sha256"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "verified": True,
    }


def _same_ring_records() -> dict[str, str]:
    return {
        "entry_hex": same_ring.ENTRY_PROOF.hex(),
        "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
        "unsat_hex": same_ring.UNSAT_PROOF.hex(),
    }


def _verify_same_ring_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] not in {SAME_RING_KIND, SAME_RING_MULTIBOOT_KIND}:
        raise EvidenceError("offline same-ring contract is not applicable")
    if set(payloads) != {"run_manifest", "static_check"} or set(receipts) != set(
        payloads
    ):
        raise EvidenceError("offline same-ring artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        receipt = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipt.get("size") != pin["size"]
            or receipt.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline same-ring contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "same-ring run manifest")
    static_result = _json(payloads["static_check"], "same-ring static result")
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    records = _same_ring_records()
    expected_observation = {
        "accepted_identity": "USERSPACE_CALLBACK_REACHED",
        "zero_classification": "ZERO_AMBIGUOUS",
        "entry_threshold": same_ring.ENTRY_SIZE,
        "unsat_threshold": same_ring.UNSAT_SIZE,
        "clean_baseline_required": True,
    }
    if (
        set(run_manifest)
        != {
            "schema",
            "target",
            "profile",
            "contract_id",
            "contract_sha256",
            "records",
            "observation_contract",
            "candidate_ap",
        }
        or run_manifest.get("schema") != SAME_RING_RUN_MANIFEST_SCHEMA
        or run_manifest.get("target") != same_ring.TARGET
        or run_manifest.get("profile") != "P219"
        or run_manifest.get("contract_id") != SAME_RING_CONTRACT_ID
        or run_manifest.get("contract_sha256") != same_ring.CONTRACT_SHA256
        or run_manifest.get("records") != records
        or run_manifest.get("observation_contract") != expected_observation
        or not _artifact_matches(run_manifest.get("candidate_ap"), candidate_ap)
        or payloads["run_manifest"] != canonical
    ):
        raise EvidenceError("run manifest does not bind the same-ring candidate")

    if (
        set(static_result)
        != {
            "schema",
            "target",
            "verdict",
            "contract_id",
            "contract_sha256",
            "records",
            "run_binding",
            "candidate",
            "safety",
        }
        or static_result.get("schema") != SAME_RING_STATIC_SCHEMA
        or static_result.get("target") != same_ring.TARGET
        or static_result.get("verdict") != SAME_RING_STATIC_VERDICT
        or static_result.get("contract_id") != SAME_RING_CONTRACT_ID
        or static_result.get("contract_sha256") != same_ring.CONTRACT_SHA256
        or static_result.get("records") != records
        or static_result.get("run_binding")
        != {
            "canonical_manifest_size": len(canonical),
            "canonical_manifest_sha256": canonical_sha256,
            "verified": True,
        }
    ):
        raise EvidenceError("static checker header does not bind P2.19 candidate")

    candidate = _exact(
        static_result["candidate"],
        {"artifacts", "record_verification"},
        "same-ring candidate",
    )
    artifacts = _exact(
        candidate["artifacts"],
        {"ap", "run_manifest", "image", "vmlinux", "boot_image"},
        "same-ring candidate artifacts",
    )
    identities = {
        name: _binary_identity(value, f"same-ring {name}")
        for name, value in artifacts.items()
    }
    verification = _exact(
        candidate["record_verification"],
        {
            "image",
            "vmlinux",
            "boot_image",
            "boot_kernel",
            "ap_members",
            "boot_only_ap",
            "verified",
        },
        "same-ring record verification",
    )
    image_claim = _record_blob_claim(
        verification["image"], "Image", identities["image"]
    )
    _record_blob_claim(
        verification["vmlinux"], "vmlinux", identities["vmlinux"]
    )
    boot_image_claim = _binary_identity(
        verification["boot_image"], "verified boot image"
    )
    boot_kernel_claim = _exact(
        verification["boot_kernel"],
        {"size", "sha256", "equals_image"},
        "verified boot kernel",
    )
    if (
        not _artifact_matches(identities["ap"], candidate_ap)
        or not _artifact_matches(
            identities["run_manifest"], receipts["run_manifest"]
        )
        or boot_image_claim != identities["boot_image"]
        or boot_kernel_claim
        != {
            "size": image_claim["size"],
            "sha256": image_claim["sha256"],
            "equals_image": True,
        }
        or verification["ap_members"]
        != [{"name": "boot.img.lz4", "type": "regular"}]
        or verification["boot_only_ap"] is not True
        or verification["verified"] is not True
        or static_result.get("safety")
        != {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
        }
    ):
        raise EvidenceError("static checker result does not bind P2.19 candidate")
    multiboot = item["kind"] == SAME_RING_MULTIBOOT_KIND
    result = {
        "schema": (
            "device_action_f1_same_ring_multiboot_offline_contract_v1"
            if multiboot
            else "device_action_f1_same_ring_offline_contract_v2"
        ),
        "decoder": (
            SAME_RING_MULTIBOOT_DECODER if multiboot else SAME_RING_DECODER
        ),
        "contract_id": SAME_RING_CONTRACT_ID,
        "candidate_ap_sha256": candidate_ap["sha256"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "zero_is_ambiguous": True,
        "verified": True,
    }
    if multiboot:
        result["policy_id"] = SAME_RING_MULTIBOOT_POLICY_ID
        result["minimum_exact_count"] = 1
    return result


def _verify_e1_latest_stage_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != E1_LATEST_STAGE_KIND:
        raise EvidenceError("offline E1 latest-stage contract is not applicable")
    profile = item["profile"]
    source_contract_id = item.get("source_contract_id")
    userspace_overlay_contract_id = item.get("userspace_overlay_contract_id")
    source_decoder = _latest_stage_decoder(source_contract_id, profile)
    selected_decoder = _latest_stage_observation_decoder(
        source_contract_id,
        profile,
        userspace_overlay_contract_id,
    )
    expected_payloads = {
        "candidate_static",
        "run_manifest",
        "static_check",
    }
    stock_keys = {"stock_baseline_raw", "stock_baseline_result"}
    if (
        userspace_overlay_contract_id
        in {
            P303_OVERLAY_CONTRACT_ID,
            P304_OVERLAY_CONTRACT_ID,
            P305_OVERLAY_CONTRACT_ID,
        }
        and stock_keys <= set(item["contract"])
    ):
        expected_payloads.update(
            stock_keys
        )
    if set(payloads) != expected_payloads or set(receipts) != set(payloads):
        raise EvidenceError(
            "P2.34 E1 latest-stage evidence has no candidate-bound offline contract"
        )
    for name, payload in payloads.items():
        pin = item["contract"][name]
        value = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or value.get("size") != pin["size"]
            or value.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline E1 latest-stage contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "E1 latest-stage run manifest")
    static_result = _json(payloads["static_check"], "E1 latest-stage static result")
    p303_stock_baseline = None
    if stock_keys <= set(payloads):
        try:
            p303_stock_baseline = p303_stock_binding.verify_payloads(
                Path(__file__).resolve().parents[5],
                payloads["stock_baseline_raw"],
                payloads["stock_baseline_result"],
                expected_raw_path=item["contract"]["stock_baseline_raw"]["path"],
            )
        except (p303_stock_binding.BindingError, OSError) as exc:
            raise EvidenceError("P3.03 stock baseline binding is invalid") from exc
    if (
        run_manifest.get("schema") != E1_LATEST_STAGE_RUN_MANIFEST_SCHEMA
        or static_result.get("schema") != E1_LATEST_STAGE_STATIC_SCHEMA
    ):
        raise EvidenceError(
            "P2.34 E1 latest-stage evidence has no candidate-bound offline contract"
        )
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    expected_records = {
        "long_family_hex": selected_decoder.model.LONG_FAMILY.hex(),
        "unsat_family_hex": selected_decoder.model.UNSAT_FAMILY.hex(),
        "terminal_stage": item["terminal_stage"],
    }
    expected_observation = {
        "accepted_identity": _latest_stage_accepted_identity(
            profile,
            source_contract_id,
            userspace_overlay_contract_id,
        ),
        "minimum_success_count": 1,
        "clean_baseline_required": True,
    }
    run_manifest_keys = {
        "schema",
        "target",
        "profile",
        "run_id",
        "decoder",
        "policy_id",
        "records",
        "observation_contract",
        "candidate_ap",
        "candidate_static",
    }
    if source_contract_id is not None:
        run_manifest_keys.add("source_contract_id")
    if userspace_overlay_contract_id is not None:
        run_manifest_keys.add("userspace_overlay_contract_id")
    if (
        set(run_manifest) != run_manifest_keys
        or run_manifest.get("schema") != E1_LATEST_STAGE_RUN_MANIFEST_SCHEMA
        or run_manifest.get("target") != PID1_USERSPACE_TARGET
        or run_manifest.get("profile") != item["profile"]
        or run_manifest.get("source_contract_id") != source_contract_id
        or run_manifest.get("userspace_overlay_contract_id")
        != userspace_overlay_contract_id
        or run_manifest.get("run_id") != item["run_id"]
        or run_manifest.get("decoder") != selected_decoder.DECODER_ID
        or run_manifest.get("policy_id") != selected_decoder.POLICY_ID
        or run_manifest.get("records") != expected_records
        or run_manifest.get("observation_contract") != expected_observation
        or not _artifact_matches(run_manifest.get("candidate_ap"), candidate_ap)
        or payloads["run_manifest"] != canonical
    ):
        raise EvidenceError("run manifest does not bind the E1 candidate")
    candidate_static = _binary_identity(
        run_manifest.get("candidate_static"), "E1A candidate static result"
    )
    if not _artifact_matches(receipts["candidate_static"], candidate_static):
        raise EvidenceError("run manifest does not bind the candidate static payload")

    candidate_static_result = _json(
        payloads["candidate_static"], "E1A candidate static result"
    )
    overlay_static_contracts = {
        P301_OVERLAY_CONTRACT_ID: (
            P301_CANDIDATE_STATIC_SCHEMA, P301_CANDIDATE_STATIC_VERDICT
        ),
        P302_OVERLAY_CONTRACT_ID: (
            P302_CANDIDATE_STATIC_SCHEMA, P302_CANDIDATE_STATIC_VERDICT
        ),
        P303_OVERLAY_CONTRACT_ID: (
            P303_CANDIDATE_STATIC_SCHEMA, P303_CANDIDATE_STATIC_VERDICT
        ),
        P304_OVERLAY_CONTRACT_ID: (
            P304_CANDIDATE_STATIC_SCHEMA, P304_CANDIDATE_STATIC_VERDICT
        ),
        P305_OVERLAY_CONTRACT_ID: (
            P305_CANDIDATE_STATIC_SCHEMA, P305_CANDIDATE_STATIC_VERDICT
        ),
        P306_OVERLAY_CONTRACT_ID: (
            P306_CANDIDATE_STATIC_SCHEMA, P306_CANDIDATE_STATIC_VERDICT
        ),
        P307_OVERLAY_CONTRACT_ID: (
            P307_CANDIDATE_STATIC_SCHEMA, P307_CANDIDATE_STATIC_VERDICT
        ),
        P308_OVERLAY_CONTRACT_ID: (
            P308_CANDIDATE_STATIC_SCHEMA, P308_CANDIDATE_STATIC_VERDICT
        ),
        P311_OVERLAY_CONTRACT_ID: (
            P311_CANDIDATE_STATIC_SCHEMA, P311_CANDIDATE_STATIC_VERDICT
        ),
        P312_OVERLAY_CONTRACT_ID: (
            P312_CANDIDATE_STATIC_SCHEMA, P312_CANDIDATE_STATIC_VERDICT
        ),
    }
    source_static_contracts = {
        P286_SOURCE_CONTRACT_ID: (
            P286_CANDIDATE_STATIC_SCHEMA, P286_CANDIDATE_STATIC_VERDICT
        ),
        P288_SOURCE_CONTRACT_ID: (
            P288_CANDIDATE_STATIC_SCHEMA, P288_CANDIDATE_STATIC_VERDICT
        ),
        P290_SOURCE_CONTRACT_ID: (
            P290_CANDIDATE_STATIC_SCHEMA, P290_CANDIDATE_STATIC_VERDICT
        ),
        P292_SOURCE_CONTRACT_ID: (
            P292_CANDIDATE_STATIC_SCHEMA, P292_CANDIDATE_STATIC_VERDICT
        ),
        P294_SOURCE_CONTRACT_ID: (
            P294_CANDIDATE_STATIC_SCHEMA, P294_CANDIDATE_STATIC_VERDICT
        ),
        P296_SOURCE_CONTRACT_ID: (
            P296_CANDIDATE_STATIC_SCHEMA, P296_CANDIDATE_STATIC_VERDICT
        ),
        P298_SOURCE_CONTRACT_ID: (
            P298_CANDIDATE_STATIC_SCHEMA, P298_CANDIDATE_STATIC_VERDICT
        ),
        P300_SOURCE_CONTRACT_ID: (
            P300_CANDIDATE_STATIC_SCHEMA, P300_CANDIDATE_STATIC_VERDICT
        ),
        P310_SOURCE_CONTRACT_ID: (
            P310_CANDIDATE_STATIC_SCHEMA, P310_CANDIDATE_STATIC_VERDICT
        ),
    }
    expected_candidate_static_schema, expected_candidate_static_verdict = (
        overlay_static_contracts.get(userspace_overlay_contract_id)
        or source_static_contracts.get(source_contract_id)
        or (
            E1_LATEST_STAGE_CANDIDATE_STATIC_SCHEMA,
            E1_LATEST_STAGE_CANDIDATE_STATIC_VERDICT,
        )
    )
    expected_candidate_static_keys = {
        "schema",
        "target",
        "verdict",
        "candidate_contract",
        "build_repro",
        "candidate",
        "tools",
        "limits",
        "safety",
    }
    if userspace_overlay_contract_id == P302_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.add("carrier_identity")
    if userspace_overlay_contract_id == P312_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {
                "p312_callsite_audit",
                "p312_delayed_arm_qemu",
                "p312_tracefs_abi",
                "p312_cross_gate_audit",
                "p312_carrier_decoder_authority",
                "p312_runtime_fixture",
                "p312_telemetry",
                "p312_observer",
            }
        )
    elif userspace_overlay_contract_id == P311_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {
                "p311_callsite_audit",
                "p311_delayed_arm_qemu",
                "p311_tracefs_abi",
                "p311_cross_gate_audit",
                "p311_runtime_fixture",
                "p311_telemetry",
                "p311_observer",
            }
        )
    elif userspace_overlay_contract_id == P308_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {
                "p303_callsite_audit",
                "p307_qscratch_audit",
                "p308_telemetry",
                "p308_observer",
                "p308_cross_gate_audit",
            }
        )
    elif userspace_overlay_contract_id == P307_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {
                "p303_callsite_audit",
                "p307_qscratch_audit",
                "p307_telemetry",
                "p307_observer",
            }
        )
    elif userspace_overlay_contract_id == P306_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {"p303_callsite_audit", "p306_ipc_telemetry", "p306_observer"}
        )
    elif userspace_overlay_contract_id in {
        P303_OVERLAY_CONTRACT_ID,
        P304_OVERLAY_CONTRACT_ID,
        P305_OVERLAY_CONTRACT_ID,
    }:
        expected_candidate_static_keys.update(
            {"p303_callsite_audit", "p303_offset_probe_rule"}
        )
    if userspace_overlay_contract_id == P305_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.add("p305_folded_tail")
    if (
        set(candidate_static_result) != expected_candidate_static_keys
        or candidate_static_result.get("schema")
        != expected_candidate_static_schema
        or candidate_static_result.get("target") != PID1_USERSPACE_TARGET
        or candidate_static_result.get("verdict")
        != expected_candidate_static_verdict
    ):
        raise EvidenceError("candidate static result header is not accepted")
    source_contract_keys = {
        "schema",
        "target",
        "verdict",
        "profile",
        "profile_number",
        "run_id",
        "unsat_record_hex",
        "unsat_tag_hex",
        "decoder_id",
        "decoder_policy_id",
        "identity_preimage",
        "identity_preimage_sha256",
        "intent",
        "patch",
        "base_files",
        "patched_files",
        "config_lines",
        "reachable_record_contract",
        "verified",
        "safety",
    }
    if source_contract_id is not None:
        source_contract_keys.update(
            {"source_contract_id", "materialized_sources"}
        )
    candidate_contract_value = candidate_static_result.get("candidate_contract")
    p301_overlay_source_receipts = None
    p302_overlay_source_receipts = None
    p303_overlay_source_receipts = None
    p304_overlay_source_receipts = None
    p305_overlay_source_receipts = None
    p306_overlay_source_receipts = None
    p307_overlay_source_receipts = None
    p308_overlay_source_receipts = None
    p311_overlay_source_receipts = None
    p312_overlay_source_receipts = None
    p302_contract = None
    p303_contract = None
    if userspace_overlay_contract_id == P301_OVERLAY_CONTRACT_ID:
        p301_contract = _validate_p301_overlay_contract(candidate_contract_value)
        if (
            p301_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p301_contract.get("source_contract_id") != source_contract_id
            or p301_contract.get("profile") != profile
            or p301_contract.get("run_id") != item["run_id"]
            or p301_contract.get("telemetry", {}).get("decoder_id")
            != selected_decoder.DECODER_ID
            or p301_contract.get("telemetry", {}).get("decoder_policy_id")
            != selected_decoder.POLICY_ID
            or p301_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.01 overlay candidate contract is invalid")
        candidate_contract_value = p301_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = p301_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P312_OVERLAY_CONTRACT_ID:
        p312_contract = _validate_p312_overlay_contract(candidate_contract_value)
        telemetry = p312_contract.get("telemetry")
        cross_gate = p312_contract.get("cross_gate_audit")
        carrier_authority = p312_contract.get("carrier_decoder_authority")
        callsites = p312_contract.get("callsite_audit", {}).get("result", {})
        delayed = p312_contract.get("delayed_arm_qemu", {}).get("result", {})
        abi = p312_contract.get("tracefs_abi")
        observer = p312_contract.get("observer")
        fixture = candidate_static_result.get("p312_runtime_fixture")
        if (
            p312_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p312_contract.get("source_contract_id") != source_contract_id
            or p312_contract.get("profile") != profile
            or p312_contract.get("run_id") != item["run_id"]
            or selected_decoder is not p312_decoder
            or not isinstance(telemetry, dict)
            or telemetry.get("schema") != "s22plus_fyg8_p312_telemetry_spec_v1"
            or telemetry.get("early_event_count") != 30
            or telemetry.get("callsite_count") != 24
            or telemetry.get("first_detail_range") != [0xD00, 0xD51]
            or telemetry.get("summary_detail_range") != [0x4001, 0x4640]
            or telemetry.get("profile_hits_may_exceed_records_outside_recording_window")
            is not True
            or telemetry.get("decoder_id") != selected_decoder.DECODER_ID
            or telemetry.get("decoder_policy_id") != selected_decoder.POLICY_ID
            or telemetry.get("verified") is not True
            or not isinstance(cross_gate, dict)
            or cross_gate.get("verified") is not True
            or cross_gate.get("retained_pair_round_trip") is not True
            or cross_gate.get("foreign_count_zero") is not True
            or not isinstance(carrier_authority, dict)
            or carrier_authority.get("verdict")
            != "PASS_P312_CARRIER_DECODER_CROSS_AUTHORITY_HOST_ONLY"
            or carrier_authority.get("p311_historical_mismatch_rejected") is not True
            or carrier_authority.get("p312_carrier_v2_json_safe") is not True
            or carrier_authority.get("records_generated_by_source_carrier") is not True
            or carrier_authority.get("verified") is not True
            or callsites.get("verdict")
            != "PASS_P311_24_EXACT_POST_BL_CALLSITES_HOST_ONLY"
            or callsites.get("callsite_count") != 24
            or delayed.get("verdict")
            != "PASS_P311_DELAYED_MODULE_KPROBE_QEMU_HOST_ONLY"
            or not isinstance(abi, dict)
            or abi.get("verified") is not True
            or not isinstance(observer, dict)
            or observer.get("pending_module_local_probes") is not True
            or observer.get("global_clock_probe") is not False
            or observer.get("event_count") != 30
            or observer.get("profile_hits_lower_bound_records") is not True
            or observer.get("profile_missed_must_be_zero") is not True
            or observer.get("semantic_call_pairs_complete") is not True
            or observer.get("ring_loss_must_be_zero") is not True
            or observer.get("carrier_v2_family") != "S22E1L2|"
            or observer.get("verified") is not True
            or candidate_static_result.get("p312_callsite_audit")
            != p312_contract.get("callsite_audit")
            or candidate_static_result.get("p312_delayed_arm_qemu")
            != p312_contract.get("delayed_arm_qemu")
            or candidate_static_result.get("p312_tracefs_abi") != abi
            or candidate_static_result.get("p312_cross_gate_audit") != cross_gate
            or candidate_static_result.get("p312_carrier_decoder_authority")
            != carrier_authority
            or candidate_static_result.get("p312_telemetry") != telemetry
            or candidate_static_result.get("p312_observer") != observer
            or not isinstance(fixture, dict)
            or fixture.get("verdict")
            != "PASS_P312_MATERIALIZED_RUNTIME_FIXTURES_HOST_ONLY"
            or fixture.get("fixture_count") != 9
            or fixture.get("profile_excess_accepted") is not True
            or fixture.get("profile_below_records_rejected") is not True
            or fixture.get("verified") is not True
            or p312_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.12 overlay candidate contract is invalid")
        candidate_contract_value = p312_contract.get("parent_candidate_contract")
        p312_overlay_source_receipts = p312_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P311_OVERLAY_CONTRACT_ID:
        p311_contract = _validate_p311_overlay_contract(candidate_contract_value)
        telemetry = p311_contract.get("telemetry")
        cross_gate = p311_contract.get("cross_gate_audit")
        callsites = p311_contract.get("callsite_audit", {}).get("result", {})
        delayed = p311_contract.get("delayed_arm_qemu", {}).get("result", {})
        abi = p311_contract.get("tracefs_abi")
        observer = p311_contract.get("observer")
        fixture = candidate_static_result.get("p311_runtime_fixture")
        if (
            p311_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p311_contract.get("source_contract_id") != source_contract_id
            or p311_contract.get("profile") != profile
            or p311_contract.get("run_id") != item["run_id"]
            or selected_decoder is not p311_decoder
            or not isinstance(telemetry, dict)
            or telemetry.get("schema") != "s22plus_fyg8_p311_telemetry_spec_v1"
            or telemetry.get("early_event_count") != 30
            or telemetry.get("callsite_count") != 24
            or telemetry.get("first_detail_range") != [0xD00, 0xD51]
            or telemetry.get("summary_detail_range") != [0x4001, 0x4640]
            or telemetry.get("decoder_id") != selected_decoder.DECODER_ID
            or telemetry.get("decoder_policy_id") != selected_decoder.POLICY_ID
            or telemetry.get("verified") is not True
            or not isinstance(cross_gate, dict)
            or cross_gate.get("verified") is not True
            or callsites.get("verdict")
            != "PASS_P311_24_EXACT_POST_BL_CALLSITES_HOST_ONLY"
            or callsites.get("callsite_count") != 24
            or delayed.get("verdict")
            != "PASS_P311_DELAYED_MODULE_KPROBE_QEMU_HOST_ONLY"
            or not isinstance(abi, dict)
            or abi.get("verified") is not True
            or not isinstance(observer, dict)
            or observer.get("pending_module_local_probes") is not True
            or observer.get("global_clock_probe") is not False
            or observer.get("event_count") != 30
            or observer.get("verified") is not True
            or candidate_static_result.get("p311_callsite_audit")
            != p311_contract.get("callsite_audit")
            or candidate_static_result.get("p311_delayed_arm_qemu")
            != p311_contract.get("delayed_arm_qemu")
            or candidate_static_result.get("p311_tracefs_abi") != abi
            or candidate_static_result.get("p311_cross_gate_audit") != cross_gate
            or candidate_static_result.get("p311_telemetry") != telemetry
            or candidate_static_result.get("p311_observer") != observer
            or not isinstance(fixture, dict)
            or fixture.get("verdict")
            != "PASS_P311_MATERIALIZED_RUNTIME_FIXTURES_HOST_ONLY"
            or fixture.get("fixture_count") != 8
            or fixture.get("verified") is not True
            or p311_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.11 overlay candidate contract is invalid")
        candidate_contract_value = p311_contract.get("parent_candidate_contract")
        p311_overlay_source_receipts = p311_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P308_OVERLAY_CONTRACT_ID:
        p308_contract = _validate_p308_overlay_contract(candidate_contract_value)
        p307_contract = _validate_p307_overlay_contract(
            p308_contract.get("parent_overlay_contract")
        )
        p305_contract = _validate_p305_overlay_contract(
            p307_contract.get("parent_overlay_contract")
        )
        p304_contract = _validate_p304_overlay_contract(
            p305_contract.get("parent_overlay_contract")
        )
        p303_contract = _validate_p303_overlay_contract(
            p304_contract.get("parent_overlay_contract")
        )
        parent_overlay = p303_contract.get("parent_overlay_contract")
        expected_observer = {
            "kmsg_opened_before_modules": True,
            "eud_cache_path": p307_spec.EUD_CACHE_PATH,
            "eud_cache_read_after_module_index": p307_spec.EUD_MODULE_INDEX,
            "eud_cache_read_count": 1,
            "message_body_ends_at_first_literal_lf": True,
            "dictionary_suffix_excluded": True,
            "local_parser_failure_latched": True,
            "local_parser_failure_drain_continues": True,
            "parent_kmsg_integrity_errors_remain_immediate": True,
            "degraded_pair_preserves_clock_qscratch_site_prefix_mask": True,
            "raw_excerpt_retained": False,
            "kernel_changed": False,
            "module_plan_changed": False,
            "carrier_changed": False,
            "log_level_changed": False,
            "read_only": True,
            "verified": True,
        }
        telemetry = p308_contract.get("telemetry")
        cross_gate = p308_contract.get("cross_gate_audit")
        qscratch = p308_contract.get("qscratch_audit")
        if (
            p308_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p308_contract.get("parent_overlay_contract_id")
            != P307_OVERLAY_CONTRACT_ID
            or p308_contract.get("source_contract_id") != source_contract_id
            or p308_contract.get("profile") != profile
            or p308_contract.get("run_id") != item["run_id"]
            or selected_decoder is not p308_decoder
            or not isinstance(telemetry, dict)
            or telemetry.get("schema") != p308_spec.SCHEMA
            or telemetry.get("enumerated_family_value_count") != 5988
            or telemetry.get("summary_detail_range") != [0x4001, 0x4FEB]
            or telemetry.get("degraded_detail_range") != [0x6100, 0x673F]
            or telemetry.get("verified") is not True
            or not isinstance(cross_gate, dict)
            or cross_gate.get("verified") is not True
            or cross_gate.get("telemetry") != telemetry
            or p308_contract.get("observer") != expected_observer
            or p308_contract.get("callsite_audit", {}).get("verified") is not True
            or p308_contract.get("callsite_audit", {}).get("callsite_count") != 12
            or not isinstance(qscratch, dict)
            or qscratch.get("verified") is not True
            or qscratch.get("probe", {}).get("offset")
            != p307_spec.QSCRATCH_PROBE_OFFSET
            or p308_contract.get("module_delta", {}).get("verified") is not True
            or p308_contract.get("module_delta", {}).get("plan_count_after") != 61
            or p308_contract.get("folded_tail", {}).get("verified") is not True
            or p307_contract.get("userspace_overlay_contract_id")
            != P307_OVERLAY_CONTRACT_ID
            or p305_contract.get("userspace_overlay_contract_id")
            != P305_OVERLAY_CONTRACT_ID
            or p304_contract.get("userspace_overlay_contract_id")
            != P304_OVERLAY_CONTRACT_ID
            or p303_contract.get("userspace_overlay_contract_id")
            != P303_OVERLAY_CONTRACT_ID
            or not isinstance(parent_overlay, dict)
            or parent_overlay.get("userspace_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p308_contract.get("carrier_v2_design_input", {}).get(
                "raw_excerpt_must_not_create_foreign_family_count"
            ) is not True
            or p308_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.08 loss-resistant overlay candidate contract is invalid")
        if (
            candidate_static_result.get("p303_callsite_audit")
            != p308_contract.get("callsite_audit")
            or candidate_static_result.get("p307_qscratch_audit") != qscratch
            or candidate_static_result.get("p308_telemetry") != telemetry
            or candidate_static_result.get("p308_observer") != expected_observer
            or candidate_static_result.get("p308_cross_gate_audit") != cross_gate
        ):
            raise EvidenceError("P3.08 observer proof is invalid")
        candidate_contract_value = p308_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = parent_overlay.get("source_receipts")
        p303_overlay_source_receipts = p303_contract.get("source_receipts")
        p304_overlay_source_receipts = p304_contract.get("source_receipts")
        p305_overlay_source_receipts = p305_contract.get("source_receipts")
        p307_overlay_source_receipts = p307_contract.get("source_receipts")
        p308_overlay_source_receipts = p308_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P307_OVERLAY_CONTRACT_ID:
        p307_contract = _validate_p307_overlay_contract(candidate_contract_value)
        p305_contract = _validate_p305_overlay_contract(
            p307_contract.get("parent_overlay_contract")
        )
        p304_contract = _validate_p304_overlay_contract(
            p305_contract.get("parent_overlay_contract")
        )
        p303_contract = _validate_p303_overlay_contract(
            p304_contract.get("parent_overlay_contract")
        )
        parent_overlay = p303_contract.get("parent_overlay_contract")
        expected_observer = {
            "kmsg_opened_before_modules": True,
            "eud_cache_path": p307_spec.EUD_CACHE_PATH,
            "eud_cache_read_after_module_index": p307_spec.EUD_MODULE_INDEX,
            "eud_cache_read_count": 1,
            "ordered_first_init_attribution": True,
            "qscratch_module": p307_spec.DWC3_MODULE_RUNTIME_NAME,
            "qscratch_symbol": p307_spec.QSCRATCH_SYMBOL,
            "qscratch_offset": p307_spec.QSCRATCH_PROBE_OFFSET,
            "qscratch_register": "w21",
            "kernel_changed": False,
            "module_plan_changed": False,
            "log_level_changed": False,
            "read_only": True,
            "verified": True,
        }
        telemetry = p307_contract.get("telemetry")
        qscratch = p307_contract.get("qscratch_audit")
        if (
            p307_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p307_contract.get("parent_overlay_contract_id")
            != P305_OVERLAY_CONTRACT_ID
            or p307_contract.get("source_contract_id") != source_contract_id
            or p307_contract.get("profile") != profile
            or p307_contract.get("run_id") != item["run_id"]
            or selected_decoder is not p307_decoder
            or not isinstance(telemetry, dict)
            or telemetry.get("schema") != p307_spec.SCHEMA
            or telemetry.get("attribution_detail_range") != [0xD00, 0xD95]
            or telemetry.get("summary_detail_range") != [0x4001, 0x4FEB]
            or telemetry.get("qscratch_state_count") != 25
            or telemetry.get("verified") is not True
            or p307_contract.get("observer") != expected_observer
            or p307_contract.get("callsite_audit", {}).get("verified") is not True
            or p307_contract.get("callsite_audit", {}).get("callsite_count") != 12
            or not isinstance(qscratch, dict)
            or qscratch.get("verified") is not True
            or qscratch.get("probe", {}).get("offset")
            != p307_spec.QSCRATCH_PROBE_OFFSET
            or p307_contract.get("module_delta", {}).get("verified") is not True
            or p307_contract.get("module_delta", {}).get("plan_count_after") != 61
            or p307_contract.get("folded_tail", {}).get("verified") is not True
            or p305_contract.get("userspace_overlay_contract_id")
            != P305_OVERLAY_CONTRACT_ID
            or p304_contract.get("userspace_overlay_contract_id")
            != P304_OVERLAY_CONTRACT_ID
            or p303_contract.get("userspace_overlay_contract_id")
            != P303_OVERLAY_CONTRACT_ID
            or not isinstance(parent_overlay, dict)
            or parent_overlay.get("userspace_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p307_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.07 EUD/QSCRATCH overlay candidate contract is invalid")
        if (
            candidate_static_result.get("p303_callsite_audit")
            != p307_contract.get("callsite_audit")
            or candidate_static_result.get("p307_qscratch_audit") != qscratch
            or candidate_static_result.get("p307_telemetry") != telemetry
            or candidate_static_result.get("p307_observer") != expected_observer
        ):
            raise EvidenceError("P3.07 EUD/QSCRATCH observer proof is invalid")
        candidate_contract_value = p307_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = parent_overlay.get("source_receipts")
        p303_overlay_source_receipts = p303_contract.get("source_receipts")
        p304_overlay_source_receipts = p304_contract.get("source_receipts")
        p305_overlay_source_receipts = p305_contract.get("source_receipts")
        p307_overlay_source_receipts = p307_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P306_OVERLAY_CONTRACT_ID:
        p306_contract = _validate_p306_overlay_contract(candidate_contract_value)
        p305_contract = _validate_p305_overlay_contract(
            p306_contract.get("parent_overlay_contract")
        )
        p304_contract = _validate_p304_overlay_contract(
            p305_contract.get("parent_overlay_contract")
        )
        p303_contract = _validate_p303_overlay_contract(
            p304_contract.get("parent_overlay_contract")
        )
        parent_overlay = p303_contract.get("parent_overlay_contract")
        expected_observer = {
            "path": "/sys/kernel/debug/ipc_logging/a600000_ssusb/log",
            "armed_after_module_index": 58,
            "armed_before_module_index": 59,
            "kernel_changed": False,
            "module_plan_changed": False,
            "log_level_changed": False,
            "passive_read_only": True,
            "verified": True,
        }
        ipc_telemetry = p306_contract.get("ipc_telemetry")
        if (
            p306_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p306_contract.get("parent_overlay_contract_id")
            != P305_OVERLAY_CONTRACT_ID
            or p306_contract.get("source_contract_id") != source_contract_id
            or p306_contract.get("profile") != profile
            or p306_contract.get("run_id") != item["run_id"]
            or not isinstance(ipc_telemetry, dict)
            or ipc_telemetry.get("schema")
            != "s22plus_fyg8_p306_ipc_state_telemetry_spec_v1"
            or ipc_telemetry.get("chain_detail_range") != [0xD01, 0xD80]
            or ipc_telemetry.get("summary_detail_range") != [0x4001, 0x4800]
            or ipc_telemetry.get("verified") is not True
            or p306_contract.get("observer") != expected_observer
            or p306_contract.get("callsite_audit", {}).get("verified") is not True
            or p306_contract.get("callsite_audit", {}).get("callsite_count") != 12
            or p306_contract.get("module_delta", {}).get("verified") is not True
            or p306_contract.get("module_delta", {}).get("plan_count_after") != 61
            or p306_contract.get("folded_tail", {}).get("verified") is not True
            or p305_contract.get("userspace_overlay_contract_id")
            != P305_OVERLAY_CONTRACT_ID
            or p304_contract.get("userspace_overlay_contract_id")
            != P304_OVERLAY_CONTRACT_ID
            or p303_contract.get("userspace_overlay_contract_id")
            != P303_OVERLAY_CONTRACT_ID
            or not isinstance(parent_overlay, dict)
            or parent_overlay.get("userspace_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p306_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.06 IPC overlay candidate contract is invalid")
        if (
            candidate_static_result.get("p303_callsite_audit")
            != p306_contract.get("callsite_audit")
            or candidate_static_result.get("p306_ipc_telemetry") != ipc_telemetry
            or candidate_static_result.get("p306_observer") != expected_observer
        ):
            raise EvidenceError("P3.06 IPC observer proof is invalid")
        candidate_contract_value = p306_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = parent_overlay.get("source_receipts")
        p303_overlay_source_receipts = p303_contract.get("source_receipts")
        p304_overlay_source_receipts = p304_contract.get("source_receipts")
        p305_overlay_source_receipts = p305_contract.get("source_receipts")
        p306_overlay_source_receipts = p306_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P305_OVERLAY_CONTRACT_ID:
        p305_contract = _validate_p305_overlay_contract(candidate_contract_value)
        p304_contract = _validate_p304_overlay_contract(
            p305_contract.get("parent_overlay_contract")
        )
        p303_contract = _validate_p303_overlay_contract(
            p304_contract.get("parent_overlay_contract")
        )
        parent_overlay = p303_contract.get("parent_overlay_contract")
        if (
            p305_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p305_contract.get("parent_overlay_contract_id")
            != P304_OVERLAY_CONTRACT_ID
            or p305_contract.get("source_contract_id") != source_contract_id
            or p305_contract.get("profile") != profile
            or p305_contract.get("run_id") != item["run_id"]
            or p305_contract.get("telemetry", {}).get("decoder_id")
            != selected_decoder.DECODER_ID
            or p305_contract.get("telemetry", {}).get("decoder_policy_id")
            != selected_decoder.POLICY_ID
            or p305_contract.get("callsite_audit", {}).get("verified") is not True
            or p305_contract.get("callsite_audit", {}).get("callsite_count") != 12
            or p305_contract.get("module_delta", {}).get("verified") is not True
            or p305_contract.get("module_delta", {}).get("plan_count_after") != 61
            or p305_contract.get("folded_tail", {}).get("verified") is not True
            or p305_contract.get("folded_tail", {}).get("later_ordinals_unchanged")
            is not True
            or p305_contract.get("folded_tail", {}).get("success_stage") != 0x7B
            or p305_contract.get("folded_tail", {}).get("first_gate_stage") != 0x7C
            or p304_contract.get("userspace_overlay_contract_id")
            != P304_OVERLAY_CONTRACT_ID
            or p304_contract.get("parent_overlay_contract_id")
            != P303_OVERLAY_CONTRACT_ID
            or p303_contract.get("parent_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or not isinstance(parent_overlay, dict)
            or parent_overlay.get("userspace_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p305_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.05 overlay candidate contract is invalid")
        callsites = candidate_static_result.get("p303_callsite_audit")
        offset_rule = _exact(
            candidate_static_result.get("p303_offset_probe_rule"),
            {
                "p300_epilogue_rejection_preserved",
                "immediate_post_bl_only",
                "w0_immediately_consumed",
                "fixed_module_receipt_shared_by_candidate_a_b",
                "hit_zero_distinct_from_rc_zero",
                "verified",
            },
            "P3.05 inherited post-BL offset probe rule",
        )
        if (
            callsites != p305_contract.get("callsite_audit")
            or candidate_static_result.get("p305_folded_tail")
            != p305_contract.get("folded_tail")
            or any(value is not True for value in offset_rule.values())
        ):
            raise EvidenceError("P3.05 folded-tail or callsite proof is invalid")
        candidate_contract_value = p305_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = parent_overlay.get("source_receipts")
        p303_overlay_source_receipts = p303_contract.get("source_receipts")
        p304_overlay_source_receipts = p304_contract.get("source_receipts")
        p305_overlay_source_receipts = p305_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P304_OVERLAY_CONTRACT_ID:
        p304_contract = _validate_p304_overlay_contract(candidate_contract_value)
        p303_contract = _validate_p303_overlay_contract(
            p304_contract.get("parent_overlay_contract")
        )
        parent_overlay = p303_contract.get("parent_overlay_contract")
        if (
            p304_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p304_contract.get("parent_overlay_contract_id")
            != P303_OVERLAY_CONTRACT_ID
            or p304_contract.get("source_contract_id") != source_contract_id
            or p304_contract.get("profile") != profile
            or p304_contract.get("run_id") != item["run_id"]
            or p304_contract.get("telemetry", {}).get("decoder_id")
            != selected_decoder.DECODER_ID
            or p304_contract.get("telemetry", {}).get("decoder_policy_id")
            != selected_decoder.POLICY_ID
            or p304_contract.get("callsite_audit", {}).get("verified") is not True
            or p304_contract.get("callsite_audit", {}).get("callsite_count") != 12
            or p304_contract.get("module_delta", {}).get("verified") is not True
            or p304_contract.get("module_delta", {}).get("plan_count_after") != 61
            or p304_contract.get("module_delta", {}).get("module", {}).get("sha256")
            != p304_overlay.MODULE_SHA256
            or not isinstance(parent_overlay, dict)
            or parent_overlay.get("userspace_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p304_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.04 overlay candidate contract is invalid")
        callsites = candidate_static_result.get("p303_callsite_audit")
        offset_rule = _exact(
            candidate_static_result.get("p303_offset_probe_rule"),
            {
                "p300_epilogue_rejection_preserved",
                "immediate_post_bl_only",
                "w0_immediately_consumed",
                "fixed_module_receipt_shared_by_candidate_a_b",
                "hit_zero_distinct_from_rc_zero",
                "verified",
            },
            "P3.04 inherited post-BL offset probe rule",
        )
        if (
            callsites != p304_contract.get("callsite_audit")
            or any(value is not True for value in offset_rule.values())
        ):
            raise EvidenceError("P3.04 inherited callsite proof is invalid")
        candidate_contract_value = p304_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = parent_overlay.get("source_receipts")
        p303_overlay_source_receipts = p303_contract.get("source_receipts")
        p304_overlay_source_receipts = p304_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P303_OVERLAY_CONTRACT_ID:
        p303_contract = _validate_p303_overlay_contract(candidate_contract_value)
        parent_overlay = p303_contract.get("parent_overlay_contract")
        if (
            p303_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p303_contract.get("parent_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p303_contract.get("source_contract_id") != source_contract_id
            or p303_contract.get("profile") != profile
            or p303_contract.get("run_id") != item["run_id"]
            or p303_contract.get("telemetry", {}).get("decoder_id")
            != selected_decoder.DECODER_ID
            or p303_contract.get("telemetry", {}).get("decoder_policy_id")
            != selected_decoder.POLICY_ID
            or p303_contract.get("callsite_audit", {}).get("verified") is not True
            or p303_contract.get("callsite_audit", {}).get("callsite_count") != 12
            or not isinstance(parent_overlay, dict)
            or parent_overlay.get("userspace_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p303_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.03 overlay candidate contract is invalid")
        callsites = candidate_static_result.get("p303_callsite_audit")
        offset_rule = _exact(
            candidate_static_result.get("p303_offset_probe_rule"),
            {
                "p300_epilogue_rejection_preserved",
                "immediate_post_bl_only",
                "w0_immediately_consumed",
                "fixed_module_receipt_shared_by_candidate_a_b",
                "hit_zero_distinct_from_rc_zero",
                "verified",
            },
            "P3.03 post-BL offset probe rule",
        )
        if (
            callsites != p303_contract.get("callsite_audit")
            or any(value is not True for value in offset_rule.values())
        ):
            raise EvidenceError("P3.03 post-BL callsite proof is invalid")
        candidate_contract_value = p303_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = parent_overlay.get("source_receipts")
        p303_overlay_source_receipts = p303_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P302_OVERLAY_CONTRACT_ID:
        p302_contract = _validate_p302_overlay_contract(candidate_contract_value)
        parent_overlay = p302_contract.get("parent_overlay_contract")
        if (
            p302_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p302_contract.get("parent_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p302_contract.get("source_contract_id") != source_contract_id
            or p302_contract.get("profile") != profile
            or p302_contract.get("run_id") != item["run_id"]
            or p302_contract.get("telemetry", {}).get("decoder_id")
            != selected_decoder.DECODER_ID
            or p302_contract.get("telemetry", {}).get("decoder_policy_id")
            != selected_decoder.POLICY_ID
            or p302_contract.get("carrier", {}).get("id")
            != "P302_ELECTRICAL_CARRIER_V1"
            or p302_contract.get("carrier", {}).get("execution_delta")
            != "nonalloc_elf_identity_section_only"
            or not isinstance(parent_overlay, dict)
            or parent_overlay.get("userspace_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p302_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.02 overlay candidate contract is invalid")
        candidate_contract_value = p302_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = parent_overlay.get("source_receipts")
        p302_overlay_source_receipts = p302_contract.get("source_receipts")
        carrier_identity = _exact(
            candidate_static_result.get("carrier_identity"),
            {
                "carrier_id",
                "section",
                "section_allocatable",
                "alloc_sections_byte_identical",
                "elf_header_execution_fields_identical",
                "program_headers_byte_identical",
                "program_segment_bytes_identical_except_section_table_fields",
                "file_prefix_and_padding_identical_except_section_table_fields",
                "identity_section_exact",
                "identity_in_program_segment",
                "baseline_size",
                "carried_size",
                "parent_init",
                "parent_child",
                "child_byte_identical",
                "fixed_image_sha256",
                "kernel_rebuilt",
                "module_binaries_injected",
                "verified",
            },
            "P3.02 carrier identity",
        )
        _binary_identity(carrier_identity["parent_init"], "P3.02 parent init")
        _binary_identity(carrier_identity["parent_child"], "P3.02 parent child")
        if (
            carrier_identity.get("carrier_id")
            != p302_contract.get("carrier", {}).get("id")
            or carrier_identity.get("section")
            != p302_contract.get("carrier", {}).get("section")
            or carrier_identity.get("section_allocatable") is not False
            or carrier_identity.get("alloc_sections_byte_identical")
            != [".text", ".rodata", ".data.rel.ro", ".data", ".bss"]
            or carrier_identity.get("elf_header_execution_fields_identical")
            is not True
            or carrier_identity.get("program_headers_byte_identical") is not True
            or carrier_identity.get(
                "program_segment_bytes_identical_except_section_table_fields"
            )
            is not True
            or carrier_identity.get(
                "file_prefix_and_padding_identical_except_section_table_fields"
            )
            is not True
            or carrier_identity.get("identity_section_exact") is not True
            or carrier_identity.get("identity_in_program_segment") is not False
            or type(carrier_identity.get("baseline_size")) is not int
            or type(carrier_identity.get("carried_size")) is not int
            or carrier_identity["baseline_size"] <= 0
            or carrier_identity["carried_size"] <= carrier_identity["baseline_size"]
            or carrier_identity.get("child_byte_identical") is not True
            or carrier_identity.get("fixed_image_sha256")
            != p302_contract.get("fixed_image", {}).get("sha256")
            or carrier_identity.get("kernel_rebuilt") is not False
            or carrier_identity.get("module_binaries_injected") != 0
            or carrier_identity.get("verified") is not True
        ):
            raise EvidenceError("P3.02 carrier identity is invalid")
    source_contract = _exact(
        candidate_contract_value,
        source_contract_keys,
        "E1A candidate source contract",
    )
    if source_contract.get("source_contract_id") != source_contract_id:
        raise EvidenceError("candidate source contract selector mismatch")
    run_id = bytes.fromhex(item["run_id"])
    candidate_source_receipts = validate_candidate_source_preimage(
        source_contract, profile, item["run_id"]
    )
    if source_contract_id is not None:
        selected_contract = _selected_contract(source_contract_id, profile)
        materialized = _exact(
            source_contract.get("materialized_sources"),
            set(selected_contract.materialized_filenames),
            "versioned materialized source contract",
        )
        for name, filename in selected_contract.materialized_filenames.items():
            row = _exact(
                materialized.get(name),
                {"path", "size", "sha256"},
                f"versioned materialized source {name}",
            )
            if (
                row.get("path") != f"materialized-sources/{filename}"
                or {
                    key: row.get(key) for key in ("size", "sha256")
                }
                != candidate_source_receipts[name]
            ):
                raise EvidenceError(
                    f"versioned materialized source identity mismatch: {name}"
                )
    unsat_record = source_decoder.model.unsat_record(profile, run_id)
    unsat_tag = unsat_record[len(source_decoder.model.UNSAT_FAMILY) :]
    expected_config_lines = [
        "CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE=y",
        f"CONFIG_S22PLUS_FYG8_E1_PROFILE={source_decoder.model.PROFILE_NUMBERS[profile]}",
        f'CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="{item["run_id"]}"',
        f'CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX="{unsat_tag.hex()}"',
    ]
    source_intent = _binary_identity(
        source_contract["intent"], "E1A candidate intent"
    )
    expected_base_files = _candidate_base_files(source_contract_id, profile)
    source_base_files = _exact(
        source_contract["base_files"],
        set(expected_base_files),
        "E1A candidate base files",
    )
    source_patched_files = _exact(
        source_contract["patched_files"],
        set(expected_base_files),
        "E1A candidate patched files",
    )
    source_patch = _exact(
        source_contract["patch"],
        {
            "size",
            "sha256",
            "targets",
            "base_files",
            "patched_files",
            "config_lines",
            "clean_apply",
            "verified",
        },
        "E1A candidate patch",
    )
    _binary_identity(
        {name: source_patch[name] for name in ("size", "sha256")},
        "E1A candidate patch",
    )
    _validate_reachable_record_contract(
        source_contract["reachable_record_contract"],
        profile,
        source_contract_id,
        item["run_id"],
    )
    source_contract_safety = _exact(
        source_contract["safety"],
        {
            "host_only",
            "device_contact",
            "device_write",
            "odin_invoked",
            "live_authorized",
        },
        "E1A candidate contract safety",
    )
    expected_contract_schema = (
        _selected_contract(
            source_contract_id, profile
        ).contract_schema
        if source_contract_id is not None
        else E1_LATEST_STAGE_CANDIDATE_CONTRACT_SCHEMA
    )
    expected_contract_verdict = (
        _selected_contract(
            source_contract_id, profile
        ).contract_verdict
        if source_contract_id is not None
        else E1_LATEST_STAGE_CANDIDATE_CONTRACT_VERDICT
    )
    if (
        source_contract.get("schema") != expected_contract_schema
        or source_contract.get("target") != PID1_USERSPACE_TARGET
        or source_contract.get("verdict") != expected_contract_verdict
        or source_contract.get("profile") != item["profile"]
        or type(source_contract.get("profile_number")) is not int
        or source_contract.get("profile_number")
        != source_decoder.model.PROFILE_NUMBERS[profile]
        or source_contract.get("run_id") != item["run_id"]
        or source_contract.get("unsat_record_hex") != unsat_record.hex()
        or source_contract.get("unsat_tag_hex") != unsat_tag.hex()
        or source_contract.get("decoder_id") != source_decoder.DECODER_ID
        or source_contract.get("decoder_policy_id")
        != source_decoder.POLICY_ID
        or source_base_files != expected_base_files
        or any(
            not isinstance(value, str) or HASH_RE.fullmatch(value) is None
            for value in source_patched_files.values()
        )
        or source_patch["targets"] != sorted(expected_base_files)
        or source_patch["base_files"] != source_base_files
        or source_patch["patched_files"] != source_patched_files
        or source_patch["config_lines"] != expected_config_lines
        or source_patch["clean_apply"] is not True
        or source_patch["verified"] is not True
        or source_contract["config_lines"] != expected_config_lines
        or any(type(value) is not bool for value in source_contract_safety.values())
        or source_contract_safety
        != {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        }
        or source_contract.get("verified") is not True
    ):
        raise EvidenceError(
            "candidate static source contract is not E1A-bound, E1B-bound, or E2-bound"
        )
    source_build_keys = {
        "result",
        "image",
        "fresh_reverification",
        "two_clean_builds_byte_identical",
        "linked_audit_verified",
    }
    if source_contract_id == P298_SOURCE_CONTRACT_ID:
        source_build_keys.update(
            {"immutable_build_time_proof_revalidated", "tier2_repair"}
        )
    source_build = _exact(
        candidate_static_result.get("build_repro"),
        source_build_keys,
        "E1A candidate static build closure",
    )
    p298_repair_files = None
    if source_contract_id == P298_SOURCE_CONTRACT_ID:
        p298_repair_files = _validate_p298_historical_build_repair(source_build)
    if (
        not isinstance(source_build, dict)
        or (
            source_contract_id != P298_SOURCE_CONTRACT_ID
            and source_build.get("fresh_reverification") is not True
        )
        or source_build.get("two_clean_builds_byte_identical") is not True
        or source_build.get("linked_audit_verified") is not True
    ):
        raise EvidenceError("candidate static build closure is incomplete")
    source_result_identity = _binary_identity(
        source_build.get("result"), "E1A build reproducibility result"
    )
    source_image_identity = _binary_identity(
        source_build.get("image"), "E1A kernel Image"
    )
    candidate_keys = {
        "artifacts",
        "candidate_b_artifacts",
        "base_boot",
        "ap",
        "fixed_interval",
        "userspace",
        "independent_reconstruction",
        "independent_lz4_roundtrip",
        "independent_magiskboot_unpack",
        "writer_exclusion_verified",
        "two_package_builds_byte_identical",
        "manifest_absent",
        "boot_only_ap",
        "verified",
    }
    if profile in {"E1B", "E2"}:
        candidate_keys.update(
            {"module_closure", "effective_rootfs", "stock_vendor_boot"}
        )
    source_candidate = _exact(
        candidate_static_result.get("candidate"),
        candidate_keys,
        "E1A candidate static artifact closure",
    )
    source_artifacts = _exact(
        source_candidate["artifacts"],
        {"artifact_result", "boot_img", "boot_img_lz4", "ap_tar_md5"},
        "E1A source artifacts",
    )
    source_b_artifacts = _exact(
        source_candidate["candidate_b_artifacts"],
        set(source_artifacts),
        "E1A source candidate-B artifacts",
    )
    normalized_source_artifacts = {
        name: _binary_identity(value, f"E1A source {name}")
        for name, value in source_artifacts.items()
    }
    normalized_source_b_artifacts = {
        name: _binary_identity(value, f"E1A source candidate-B {name}")
        for name, value in source_b_artifacts.items()
    }
    source_userspace = _exact(
        source_candidate["userspace"],
        {"result", "init", "child", "two_build_byte_identical", "verified"},
        "E1A source userspace",
    )
    normalized_source_userspace = {
        name: _binary_identity(source_userspace[name], f"E1A userspace {name}")
        for name in ("result", "init", "child")
    }
    source_base_boot = _binary_identity(
        source_candidate["base_boot"], "E1A source base boot"
    )
    source_ap = _exact(
        source_candidate["ap"], {"tar_md5", "member"}, "E1A source AP"
    )
    source_member = _exact(
        source_ap["member"],
        {"name", "size", "mode", "uid", "gid", "mtime", "uname", "gname"},
        "E1A source AP member",
    )
    source_fixed_interval = _exact(
        source_candidate["fixed_interval"],
        {
            "kernel_start",
            "kernel_end_exclusive",
            "header_preserved",
            "ramdisk_preserved",
            "outside_interval_changed_byte_count",
            "verified",
        },
        "E1A source fixed interval",
    )
    if profile == "E1B":
        validate_e1b_stock_closure(
            module_closure=source_candidate.get("module_closure"),
            effective_rootfs=source_candidate.get("effective_rootfs"),
            stock_vendor_boot=source_candidate.get("stock_vendor_boot"),
            expected_init=normalized_source_userspace["init"],
            expected_child=normalized_source_userspace["child"],
        )
    elif profile == "E2":
        closure_api = _select_e2_closure(
            source_contract_id, userspace_overlay_contract_id
        )
        try:
            closure = closure_api.validate_module_closure(
                source_candidate.get("module_closure")
            )
            closure_api.validate_effective_rootfs(
                source_candidate.get("effective_rootfs"),
                expected_init=normalized_source_userspace["init"],
                expected_child=normalized_source_userspace["child"],
                module_closure=closure,
            )
        except e2_closure.ClosureError as exc:
            raise EvidenceError("E2 stock rootfs closure is invalid") from exc
        if (
            _binary_identity(
                source_candidate.get("stock_vendor_boot"),
                "E2 stock vendor_boot",
            )
            != E1B_STOCK_VENDOR_BOOT
        ):
            raise EvidenceError("E2 stock vendor_boot identity mismatch")
    source_tools = _exact(
        candidate_static_result["tools"],
        {"lz4", "magiskboot", "qemu_aarch64"},
        "E1A candidate static tools",
    )
    for name, value in source_tools.items():
        _binary_identity(value, f"E1A source tool {name}")
    expected_limits = [
        "host-only artifact qualification grants no D0, D1, F1, or live authority",
        "candidate execution and retained observation remain unproved",
    ]
    if (
        normalized_source_b_artifacts != normalized_source_artifacts
        or not _artifact_matches(source_artifacts["ap_tar_md5"], candidate_ap)
        or (
            profile == "E2"
            and candidate_ap.get("member")
            != {
                "name": "boot.img.lz4",
                **normalized_source_artifacts["boot_img_lz4"],
            }
        )
        or source_member
        != {
            "name": "boot.img.lz4",
            "size": normalized_source_artifacts["boot_img_lz4"]["size"],
            "mode": 0o644,
            "uid": 0,
            "gid": 0,
            "mtime": 0,
            "uname": "",
            "gname": "",
        }
        or not isinstance(source_ap["tar_md5"], str)
        or HEX32_RE.fullmatch(source_ap["tar_md5"]) is None
        or source_fixed_interval
        != {
            "kernel_start": E1_LATEST_STAGE_KERNEL_INTERVAL[0],
            "kernel_end_exclusive": E1_LATEST_STAGE_KERNEL_INTERVAL[1],
            "header_preserved": True,
            "ramdisk_preserved": True,
            "outside_interval_changed_byte_count": 0,
            "verified": True,
        }
        or source_userspace.get("two_build_byte_identical") is not True
        or source_userspace.get("verified") is not True
        or source_candidate.get("boot_only_ap") is not True
        or source_candidate.get("independent_reconstruction") is not True
        or source_candidate.get("independent_lz4_roundtrip") is not True
        or source_candidate.get("independent_magiskboot_unpack") is not True
        or source_candidate.get("writer_exclusion_verified") is not True
        or source_candidate.get("two_package_builds_byte_identical") is not True
        or source_candidate.get("manifest_absent") is not True
        or source_candidate.get("verified") is not True
        or candidate_static_result.get("limits") != expected_limits
    ):
        raise EvidenceError("candidate static artifact closure is not accepted")
    source_safety = candidate_static_result.get("safety")
    expected_source_safety = {
        "host_only": True,
        "device_contact": False,
        "device_write": False,
        "odin_invoked": False,
        "flash": False,
        "partition_write": False,
        "manifest_created": False,
        "live_authorized": False,
    }
    if source_safety != expected_source_safety:
        raise EvidenceError("candidate static safety contract changed")

    static_result_keys = {
        "schema",
        "target",
        "verdict",
        "profile",
        "run_id",
        "decoder",
        "policy_id",
        "run_binding",
        "candidate",
        "safety",
    }
    if source_contract_id is not None:
        static_result_keys.add("source_contract_id")
    if userspace_overlay_contract_id is not None:
        static_result_keys.add("userspace_overlay_contract_id")
    if (
        set(static_result) != static_result_keys
        or static_result.get("schema") != E1_LATEST_STAGE_STATIC_SCHEMA
        or static_result.get("target") != PID1_USERSPACE_TARGET
        or static_result.get("verdict") != E1_LATEST_STAGE_STATIC_VERDICT
        or static_result.get("profile") != item["profile"]
        or static_result.get("source_contract_id") != source_contract_id
        or static_result.get("userspace_overlay_contract_id")
        != userspace_overlay_contract_id
        or static_result.get("run_id") != item["run_id"]
        or static_result.get("decoder") != selected_decoder.DECODER_ID
        or static_result.get("policy_id") != selected_decoder.POLICY_ID
        or static_result.get("run_binding")
        != {
            "canonical_manifest_size": len(canonical),
            "canonical_manifest_sha256": canonical_sha256,
            "verified": True,
        }
    ):
        raise EvidenceError("static checker header does not bind the E1A candidate")
    candidate_result = _exact(
        static_result["candidate"],
        {
            "artifacts",
            "boot_only_ap",
            "two_clean_builds_byte_identical",
            "two_package_builds_byte_identical",
            "linked_audit_verified",
            "independent_reconstruction",
            "writer_exclusion_verified",
            "verified",
        },
        "E1A candidate result",
    )
    artifacts = _exact(
        candidate_result["artifacts"],
        {
            "ap",
            "candidate_static",
            "image",
            "boot_image",
            "boot_img_lz4",
            "init",
            "child",
        },
        "E1A candidate artifacts",
    )
    for name, value in artifacts.items():
        artifacts[name] = _binary_identity(value, f"E1A {name}")
    expected_artifacts = {
        "ap": normalized_source_artifacts["ap_tar_md5"],
        "candidate_static": candidate_static,
        "image": source_image_identity,
        "boot_image": normalized_source_artifacts["boot_img"],
        "boot_img_lz4": normalized_source_artifacts["boot_img_lz4"],
        "init": normalized_source_userspace["init"],
        "child": normalized_source_userspace["child"],
    }
    safety = _exact(
        static_result["safety"],
        {
            "host_only",
            "device_contact",
            "device_write",
            "odin_invoked",
            "odin_transfer",
            "flash",
            "partition_write",
            "live_authorized",
        },
        "E1A static safety",
    )
    if (
        artifacts != expected_artifacts
        or source_result_identity["size"] <= 0
        or source_base_boot["size"] <= 0
        or candidate_result["boot_only_ap"] is not True
        or candidate_result["two_clean_builds_byte_identical"] is not True
        or candidate_result["two_package_builds_byte_identical"] is not True
        or candidate_result["linked_audit_verified"] is not True
        or candidate_result["independent_reconstruction"] is not True
        or candidate_result["writer_exclusion_verified"] is not True
        or candidate_result["verified"] is not True
        or safety["host_only"] is not True
        or any(value is not False for name, value in safety.items() if name != "host_only")
    ):
        raise EvidenceError("static checker result does not bind the E1A candidate")
    result = {
        "schema": "device_action_f1_e1_latest_stage_offline_contract_v1",
        "decoder": item["decoder"],
        "policy_id": item["policy_id"],
        "profile": item["profile"],
        "run_id": item["run_id"],
        "terminal_stage": item["terminal_stage"],
        "candidate_ap_sha256": candidate_ap["sha256"],
        "candidate_static_sha256": candidate_static["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_source_receipts": candidate_source_receipts,
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "verified": True,
    }
    if source_contract_id is not None:
        result["source_contract_id"] = source_contract_id
    if userspace_overlay_contract_id is not None:
        result["userspace_overlay_contract_id"] = userspace_overlay_contract_id
        result["p301_overlay_source_receipts"] = p301_overlay_source_receipts
        if userspace_overlay_contract_id == P302_OVERLAY_CONTRACT_ID:
            result["p302_overlay_source_receipts"] = (
                p302_overlay_source_receipts
            )
        if userspace_overlay_contract_id in {
            P303_OVERLAY_CONTRACT_ID,
            P304_OVERLAY_CONTRACT_ID,
            P305_OVERLAY_CONTRACT_ID,
        }:
            result["p303_overlay_source_receipts"] = (
                p303_overlay_source_receipts
            )
            result["p303_stock_baseline"] = p303_stock_baseline
        if userspace_overlay_contract_id in {
            P306_OVERLAY_CONTRACT_ID,
            P307_OVERLAY_CONTRACT_ID,
            P308_OVERLAY_CONTRACT_ID,
        }:
            result["p303_overlay_source_receipts"] = (
                p303_overlay_source_receipts
            )
        if userspace_overlay_contract_id in {
            P304_OVERLAY_CONTRACT_ID,
            P305_OVERLAY_CONTRACT_ID,
            P306_OVERLAY_CONTRACT_ID,
            P307_OVERLAY_CONTRACT_ID,
            P308_OVERLAY_CONTRACT_ID,
        }:
            result["p304_overlay_source_receipts"] = (
                p304_overlay_source_receipts
            )
        if userspace_overlay_contract_id in {
            P305_OVERLAY_CONTRACT_ID,
            P306_OVERLAY_CONTRACT_ID,
            P307_OVERLAY_CONTRACT_ID,
            P308_OVERLAY_CONTRACT_ID,
        }:
            result["p305_overlay_source_receipts"] = (
                p305_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P306_OVERLAY_CONTRACT_ID:
            result["p306_overlay_source_receipts"] = (
                p306_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P307_OVERLAY_CONTRACT_ID:
            result["p307_overlay_source_receipts"] = (
                p307_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P308_OVERLAY_CONTRACT_ID:
            result["p307_overlay_source_receipts"] = (
                p307_overlay_source_receipts
            )
            result["p308_overlay_source_receipts"] = (
                p308_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P311_OVERLAY_CONTRACT_ID:
            result["p311_overlay_source_receipts"] = (
                p311_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P312_OVERLAY_CONTRACT_ID:
            result["p312_overlay_source_receipts"] = (
                p312_overlay_source_receipts
            )
    if p298_repair_files is not None:
        result["tier2_repair_files"] = p298_repair_files
    if profile == "E2":
        result["ap_payload_closure"] = {
            "boot_img_lz4": normalized_source_artifacts["boot_img_lz4"],
            "boot_image": normalized_source_artifacts["boot_img"],
            "image": source_image_identity,
            "init": normalized_source_userspace["init"],
            "child": normalized_source_userspace["child"],
            "run_id": item["run_id"],
            "module_closure": source_candidate["module_closure"],
            "effective_rootfs": source_candidate["effective_rootfs"],
        }
        if source_contract_id is not None:
            result["ap_payload_closure"][
                "source_contract_id"
            ] = source_contract_id
        if userspace_overlay_contract_id is not None:
            result["ap_payload_closure"][
                "userspace_overlay_contract_id"
            ] = userspace_overlay_contract_id
    return result


def verify_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    if acceptance.get("kind") == E1_LATEST_STAGE_KIND:
        return _verify_e1_latest_stage_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
        )
    if acceptance.get("kind") in {SAME_RING_KIND, SAME_RING_MULTIBOOT_KIND}:
        return _verify_same_ring_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
        )
    if acceptance.get("kind") == PID1_USERSPACE_KIND:
        return _verify_pid1_userspace_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
        )
    return _verify_checkpoint_offline_contract(
        acceptance,
        payloads=payloads,
        receipts=receipts,
        candidate_ap=candidate_ap,
    )


def _base_classification(
    *,
    classification: str,
    exact_count: int,
    family_count: int,
    integrity_issue: bool,
) -> dict[str, Any]:
    return {
        "classification": classification,
        "exact_count": exact_count,
        "exact_record_count": exact_count,
        "family_count": family_count,
        "foreign_count": max(0, family_count - exact_count),
        "foreign_records_hex": [],
        "unterminated_offsets": [],
        "delimiter_mismatch_count": 0,
        "partial_at_head": False,
        "partial_at_tail": False,
        "historical_family_count": 0,
        "integrity_issue": integrity_issue,
        "baseline_absent": family_count == 0 and exact_count == 0,
        "acceptance_present": False,
        "accepted": False,
        "checkpoint": None,
    }


def classify_checkpoint(payload: bytes, acceptance: dict[str, Any]) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != CHECKPOINT_KIND:
        raise EvidenceError("checkpoint classifier received another evidence kind")
    marker = checkpoint.ENTRY_PROOF
    family = checkpoint.ENTRY_FAMILY
    exact_count = payload.count(marker)
    family_count = payload.count(family)
    prefix_counts = [payload.count(prefix) for prefix in checkpoint.ENTRY_PREFIXES]
    partial_head = any(
        payload.startswith(marker[-length:])
        for length in range(len(b"[[S22P1"), len(marker))
    )
    partial_tail = any(
        payload.endswith(marker[:length])
        for length in range(len(b"[[S22P1"), len(marker))
    )
    if not any(prefix_counts) and exact_count == 0 and not partial_head and not partial_tail:
        return _base_classification(
            classification="CHECKPOINT_ABSENT",
            exact_count=0,
            family_count=0,
            integrity_issue=False,
        )
    if (
        exact_count != item["exact_count"]
        or family_count != item["exact_count"]
        or any(count != item["exact_count"] for count in prefix_counts)
        or partial_head
        or partial_tail
    ):
        result = _base_classification(
            classification="CHECKPOINT_FAMILY_INTEGRITY_FAILURE",
            exact_count=exact_count,
            family_count=family_count,
            integrity_issue=True,
        )
        result["partial_at_head"] = partial_head
        result["partial_at_tail"] = partial_tail
        return result

    position = payload.index(marker)
    region = payload[position : position + checkpoint.REGION_SIZE]
    try:
        decoded = checkpoint.decode_region(
            region,
            item["profile"],
            expected_run_id=bytes.fromhex(item["run_id"]),
        )
    except checkpoint.CheckError as exc:
        result = _base_classification(
            classification="CHECKPOINT_DECODE_FAILURE",
            exact_count=exact_count,
            family_count=family_count,
            integrity_issue=True,
        )
        result["checkpoint"] = {"error": str(exc), "observer_offset": position}
        return result

    active = decoded["active"]
    outcome_name = OUTCOME_NAMES.get(active["outcome"], "unknown")
    two_slots = len(decoded["valid_slots"]) == 2
    accepted = (
        decoded["terminal"] is True
        and active["stage"] == item["terminal_stage"]
        and outcome_name == item["terminal_outcome"]
        and (two_slots or item["require_two_valid_slots"] is not True)
    )
    if accepted:
        classification = "CHECKPOINT_TERMINAL_SUCCESS"
    elif decoded["terminal"] and outcome_name == "failure":
        classification = "CHECKPOINT_TERMINAL_FAILURE"
    elif decoded["terminal"]:
        classification = "CHECKPOINT_TERMINAL_MISMATCH"
    else:
        classification = "CHECKPOINT_PROGRESS_ONLY"
    result = _base_classification(
        classification=classification,
        exact_count=exact_count,
        family_count=family_count,
        integrity_issue=False,
    )
    result["acceptance_present"] = accepted
    result["accepted"] = accepted
    result["checkpoint"] = {
        **decoded,
        "observer_offset": position,
        "outcome_name": outcome_name,
        "two_valid_slots": two_slots,
        "boot_identity_self_consistent": two_slots,
    }
    return result


def classify_pid1_userspace(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != PID1_USERSPACE_KIND:
        raise EvidenceError("PID1 userspace classifier received another evidence kind")
    entry_count = payload.count(PID1_USERSPACE_ENTRY)
    userspace_count = payload.count(PID1_USERSPACE_PROOF)
    family_count = payload.count(PID1_USERSPACE_FAMILY)
    markers = (PID1_USERSPACE_ENTRY, PID1_USERSPACE_PROOF)
    partial_head = any(
        payload.startswith(marker[-length:])
        for marker in markers
        for length in range(len(b"[[S22P1"), len(marker))
    )
    partial_tail = any(
        payload.endswith(marker[:length])
        for marker in markers
        for length in range(len(b"[[S22P1"), len(marker))
    )
    if family_count == 0 and not partial_head and not partial_tail:
        result = _base_classification(
            classification="PID1_USERSPACE_ABSENT",
            exact_count=0,
            family_count=0,
            integrity_issue=False,
        )
    elif (
        family_count != 1
        or entry_count + userspace_count != 1
        or partial_head
        or partial_tail
    ):
        result = _base_classification(
            classification="PID1_USERSPACE_FAMILY_INTEGRITY_FAILURE",
            exact_count=userspace_count,
            family_count=family_count,
            integrity_issue=True,
        )
        result["partial_at_head"] = partial_head
        result["partial_at_tail"] = partial_tail
    elif userspace_count == 1:
        result = _base_classification(
            classification="PID1_USERSPACE_CALLBACK_REACHED",
            exact_count=1,
            family_count=1,
            integrity_issue=False,
        )
        result["acceptance_present"] = True
        result["accepted"] = True
    else:
        result = _base_classification(
            classification="PID1_ENTRY_ONLY",
            exact_count=0,
            family_count=1,
            integrity_issue=False,
        )
    result["entry_count"] = entry_count
    result["userspace_count"] = userspace_count
    result["probe_id"] = item["probe_id"]
    return result


def classify_same_ring(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != SAME_RING_KIND:
        raise EvidenceError("same-ring classifier received another evidence kind")
    try:
        decoded = same_ring.classify_observation(payload)
    except same_ring.DecodeError as exc:
        raise EvidenceError(str(exc)) from exc

    exact_record_count = (
        decoded["entry_count"]
        + decoded["userspace_count"]
        + decoded["unsat_count"]
    )
    family_count = decoded["long_family_count"] + decoded["unsat_family_count"]
    result = _base_classification(
        classification=decoded["classification"],
        exact_count=decoded["userspace_count"],
        family_count=family_count,
        integrity_issue=decoded["integrity_issue"],
    )
    result["exact_record_count"] = exact_record_count
    result["foreign_count"] = max(0, family_count - exact_record_count)
    result["partial_at_head"] = decoded["partial_at_snapshot_edge"]
    result["partial_at_tail"] = decoded["partial_at_snapshot_edge"]
    result["baseline_absent"] = decoded["classification"] == "ZERO_AMBIGUOUS"
    result["acceptance_present"] = decoded["accepted"]
    result["accepted"] = decoded["accepted"]
    result["entry_count"] = decoded["entry_count"]
    result["userspace_count"] = decoded["userspace_count"]
    result["unsat_count"] = decoded["unsat_count"]
    result["long_family_count"] = decoded["long_family_count"]
    result["unsat_family_count"] = decoded["unsat_family_count"]
    result["contract_id"] = item["contract_id"]
    result["residual_zero_meanings"] = decoded["residual_zero_meanings"]
    return result


def classify_same_ring_multiboot(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != SAME_RING_MULTIBOOT_KIND:
        raise EvidenceError("same-ring multiboot classifier received another kind")
    try:
        decoded = same_ring_multiboot.classify_observation(payload)
    except same_ring_multiboot.DecodeError as exc:
        raise EvidenceError(str(exc)) from exc

    family_count = decoded["long_family_count"] + decoded["unsat_family_count"]
    result = _base_classification(
        classification=decoded["classification"],
        exact_count=decoded["userspace_count"],
        family_count=family_count,
        integrity_issue=decoded["integrity_issue"],
    )
    result["exact_record_count"] = decoded["exact_record_count"]
    result["foreign_count"] = max(0, family_count - decoded["exact_record_count"])
    result["partial_at_head"] = decoded["partial_at_snapshot_edge"]
    result["partial_at_tail"] = decoded["partial_at_snapshot_edge"]
    result["baseline_absent"] = decoded["classification"] == "ZERO_AMBIGUOUS"
    result["acceptance_present"] = decoded["accepted"]
    result["accepted"] = decoded["accepted"]
    result["entry_count"] = decoded["entry_count"]
    result["userspace_count"] = decoded["userspace_count"]
    result["unsat_count"] = decoded["unsat_count"]
    result["long_family_count"] = decoded["long_family_count"]
    result["unsat_family_count"] = decoded["unsat_family_count"]
    result["minimum_candidate_boots"] = decoded["minimum_candidate_boots"]
    result["contract_id"] = item["contract_id"]
    result["policy_id"] = item["policy_id"]
    result["residual_zero_meanings"] = decoded["residual_zero_meanings"]
    return result


def _p303_bound_stock_baseline(item: dict[str, Any]) -> dict[str, Any] | None:
    root = Path(__file__).resolve().parents[5]
    contract = item["contract"]
    stock_keys = {"stock_baseline_raw", "stock_baseline_result"}
    supplied = stock_keys & set(contract)
    if not supplied:
        return None
    if supplied != stock_keys:
        raise EvidenceError(
            "P3.03 stock baseline contract must be absent or an exact pair"
        )
    payloads: dict[str, bytes] = {}
    for name in ("stock_baseline_raw", "stock_baseline_result"):
        pin = contract[name]
        path = (root / pin["path"]).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise EvidenceError("P3.03 stock baseline escaped the repository") from exc
        try:
            before = path.stat()
            if path.is_symlink() or not path.is_file():
                raise EvidenceError("P3.03 stock baseline artifact is indirect")
            payload = path.read_bytes()
            after = path.stat()
        except OSError as exc:
            raise EvidenceError("P3.03 stock baseline artifact is unavailable") from exc
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        ):
            raise EvidenceError("P3.03 stock baseline artifact changed")
        payloads[name] = payload
    try:
        return p303_stock_binding.verify_payloads(
            root,
            payloads["stock_baseline_raw"],
            payloads["stock_baseline_result"],
            expected_raw_path=contract["stock_baseline_raw"]["path"],
        )
    except (p303_stock_binding.BindingError, OSError) as exc:
        raise EvidenceError("P3.03 stock baseline comparison input is invalid") from exc


def classify_e1_latest_stage(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != E1_LATEST_STAGE_KIND:
        raise EvidenceError("E1 latest-stage classifier received another kind")
    selected_decoder = _latest_stage_observation_decoder(
        item.get("source_contract_id"),
        item["profile"],
        item.get("userspace_overlay_contract_id"),
    )
    try:
        decoded = selected_decoder.classify_observation(
            payload,
            expected_profile=item["profile"],
            expected_run_id=bytes.fromhex(item["run_id"]),
        )
    except selected_decoder.DecodeError as exc:
        raise EvidenceError(str(exc)) from exc

    model = selected_decoder.model
    long_family_count = payload.count(model.LONG_FAMILY)
    unsat_family_count = payload.count(model.UNSAT_FAMILY)
    carrier_v2 = item.get("source_contract_id") == P310_SOURCE_CONTRACT_ID
    family_count = (
        decoded["family_count"]
        if carrier_v2
        else long_family_count + unsat_family_count
    )
    exact_record_count = decoded["long_record_count"] + decoded["unsat_count"]
    accepted_count = (
        decoded.get("telemetry_count", 0)
        if (
            item.get("userspace_overlay_contract_id")
            in P301_TELEMETRY_OVERLAY_IDS
            or carrier_v2
        )
        else decoded["success_count"]
    )
    result = _base_classification(
        classification=decoded["classification"],
        exact_count=accepted_count,
        family_count=family_count,
        integrity_issue=decoded["integrity_issue"],
    )
    result["exact_record_count"] = exact_record_count
    result["foreign_count"] = (
        decoded["foreign_count"]
        if carrier_v2
        else max(0, family_count - exact_record_count)
    )
    result["baseline_absent"] = decoded["classification"] == "ZERO_AMBIGUOUS"
    result["acceptance_present"] = decoded["accepted"]
    result["accepted"] = decoded["accepted"]
    result["long_record_count"] = decoded["long_record_count"]
    result["unsat_count"] = decoded["unsat_count"]
    result["entry_count"] = decoded["entry_count"]
    result["progress_count"] = decoded["progress_count"]
    result["failure_count"] = decoded["failure_count"]
    result["success_count"] = decoded["success_count"]
    if (
        item.get("userspace_overlay_contract_id") in P301_TELEMETRY_OVERLAY_IDS
        or carrier_v2
    ):
        result["telemetry_count"] = decoded["telemetry_count"]
        result["contradiction_count"] = decoded["contradiction_count"]
        if "degraded_count" in decoded:
            result["degraded_count"] = decoded["degraded_count"]
    result["fallback_record_count"] = decoded["fallback_record_count"]
    result["minimum_candidate_boots"] = decoded["minimum_candidate_boots"]
    result["records"] = decoded["records"]
    result["integrity_issues"] = decoded["integrity_issues"]
    result["policy_id"] = item["policy_id"]
    result["profile"] = item["profile"]
    result["run_id"] = item["run_id"]
    result["residual_zero_meanings"] = decoded["residual_zero_meanings"]
    if item.get("userspace_overlay_contract_id") in {
        P303_OVERLAY_CONTRACT_ID,
        P304_OVERLAY_CONTRACT_ID,
        P305_OVERLAY_CONTRACT_ID,
    }:
        stock = _p303_bound_stock_baseline(item)
        comparisons = []
        if stock is not None:
            for record in decoded["records"]:
                pair = record.get("p303_pair")
                if pair is None:
                    continue
                try:
                    comparisons.append(
                        p303_decoder.compare_stock_baseline(
                            int(pair["b"]["detail"]), stock["baseline"]
                        )
                    )
                except p303_decoder.DecodeError as exc:
                    raise EvidenceError(str(exc)) from exc
            result["p303_stock_baseline"] = {
                "available": True,
                "causal_attribution_permitted": True,
                "raw": stock["raw"],
                "boot_window_complete": stock["boot_window_complete"],
                "comparisons": comparisons,
                "comparison_count": len(comparisons),
            }
        else:
            result["p303_stock_baseline"] = {
                "available": False,
                "causal_attribution_permitted": False,
                "comparisons": [],
                "comparison_count": 0,
            }
    return result


def classify_clean_baseline(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] == E1_LATEST_STAGE_KIND:
        selected_decoder = _latest_stage_observation_decoder(
            item.get("source_contract_id"),
            item["profile"],
            item.get("userspace_overlay_contract_id"),
        )
        baseline = selected_decoder.classify_clean_baseline(
            payload,
            expected_profile=item["profile"],
            expected_run_id=bytes.fromhex(item["run_id"]),
        )
        return {
            "classification": baseline["classification"],
            "exact_record_count": 0,
            "family_count": 0 if baseline["baseline_clean"] else 1,
            "integrity_issue": baseline["integrity_issue"],
            "baseline_clean": baseline["baseline_clean"],
        }
    if item["kind"] in {SAME_RING_KIND, SAME_RING_MULTIBOOT_KIND}:
        result = (
            classify_same_ring_multiboot(payload, item)
            if item["kind"] == SAME_RING_MULTIBOOT_KIND
            else classify_same_ring(payload, item)
        )
        exact_count = result["exact_record_count"]
        family_count = result["family_count"]
        clean = (
            result["classification"] == "ZERO_AMBIGUOUS"
            and result["integrity_issue"] is False
            and exact_count == 0
            and family_count == 0
        )
        return {
            "classification": result["classification"],
            "exact_record_count": exact_count,
            "family_count": family_count,
            "integrity_issue": result["integrity_issue"],
            "baseline_clean": clean,
        }

    marker = item["marker"].encode("ascii")
    family = item["family"].encode("ascii")
    exact_count = payload.count(marker)
    family_count = payload.count(family)
    return {
        "classification": (
            "BASELINE_CLEAN"
            if exact_count == 0 and family_count == 0
            else "BASELINE_FAMILY_PRESENT"
        ),
        "exact_record_count": exact_count,
        "family_count": family_count,
        "integrity_issue": False,
        "baseline_clean": exact_count == 0 and family_count == 0,
    }
