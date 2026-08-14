#!/usr/bin/env python3
"""Bind the P3.18 timing/topology successor to frozen P3.17 and P3.10 Image."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import s22plus_fyg8_p308_overlay_contract as helpers
import s22plus_fyg8_p317_generator as p317_generator
import s22plus_fyg8_p317_overlay_contract as predecessor
import s22plus_fyg8_p318_dwc3_event_latch_build as latch_build
import s22plus_fyg8_p318_generator as generator
import s22plus_fyg8_p318_max77705_diag_build as diag_build
import s22plus_fyg8_p318_max77705_envelope_qualification as envelope_qualification
import s22plus_fyg8_p318_max77705_preimage_fixture as preimage_fixture
import s22plus_fyg8_p318_max77705_runtime_parser_fixture as runtime_parser
import s22plus_fyg8_p318_max77705_telemetry as telemetry
import s22plus_fyg8_p318_max77705_telemetry_decoder as decoder
import s22plus_fyg8_p318_process_v2_adapter_fixture as adapter_fixture
import s22plus_fyg8_p318_runtime_qualification as runtime_qualification
import s22plus_fyg8_p318_topology_receipt as topology_receipt


SCHEMA = "s22plus_fyg8_p318_userspace_overlay_contract_v1"
CONTRACT_ID = decoder.OVERLAY_CONTRACT_ID
INTENT_SCHEMA = "s22plus_fyg8_p318_userspace_overlay_intent_v1"
INTENT_VERDICT = "PASS_P318_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
CONTRACT_VERDICT = "PASS_P318_USERSPACE_OVERLAY_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P318_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
TARGET = predecessor.TARGET
PROFILE = predecessor.PROFILE
PARENT_SOURCE_CONTRACT_ID = predecessor.PARENT_SOURCE_CONTRACT_ID
PARENT_SOURCE = predecessor.PARENT_SOURCE
PARENT_PATCH = predecessor.PARENT_PATCH
PARENT_IMAGE = predecessor.PARENT_IMAGE
PARENT_REPRO_RESULT = predecessor.PARENT_REPRO_RESULT
EXPECTED_IMAGE = predecessor.EXPECTED_IMAGE
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p318/intent")
DEFAULT_INTENT = DEFAULT_OUT / "overlay-intent.json"
DEFAULT_MATERIALIZED = DEFAULT_OUT / "materialized-sources"
P317_INTENT = predecessor.DEFAULT_INTENT

PREFIX = Path("workspace/public/src/scripts/revalidation")
NATIVE = Path("workspace/public/src/native-init")
LATCH_MODULE = Path("workspace/public/src/kernel-modules/s22plus_dwc3_event_latch")
DIAG_MODULE = Path("workspace/public/src/kernel-modules/s22plus_max77705_mux_diag_p318")
SOURCE_PATHS = {
    "p318_latch_source": LATCH_MODULE / "s22plus_dwc3_event_latch.c",
    "p318_latch_decoder": LATCH_MODULE / "s22plus_dwc3_event_decode.h",
    "p318_latch_makefile": LATCH_MODULE / "Makefile",
    "p318_diag_source": DIAG_MODULE / "s22plus_max77705_mux_diag_p318.c",
    "p318_diag_makefile": DIAG_MODULE / "Makefile",
    "p318_runtime": NATIVE / "s22plus_fyg8_p318_max77705_runtime.inc.c",
    "p318_result_parser": NATIVE / "s22plus_fyg8_p318_max77705_result_parser.inc.c",
    "p318_latch_parser": NATIVE / "s22plus_fyg8_p318_dwc3_latch_parser.inc.c",
    "p318_banner_writer": NATIVE / "s22plus_fyg8_p318_banner_writer.inc.c",
    "p318_envelope": NATIVE / "s22plus_fyg8_p318_max77705_envelope.inc.c",
    "p318_generator": PREFIX / "s22plus_fyg8_p318_generator.py",
    "p318_latch_build": PREFIX / "s22plus_fyg8_p318_dwc3_event_latch_build.py",
    "p318_diag_build": PREFIX / "s22plus_fyg8_p318_max77705_diag_build.py",
    "p318_runtime_qualification": PREFIX / "s22plus_fyg8_p318_runtime_qualification.py",
    "p318_envelope_qualification": PREFIX / "s22plus_fyg8_p318_max77705_envelope_qualification.py",
    "p318_preimage_fixture": PREFIX / "s22plus_fyg8_p318_max77705_preimage_fixture.py",
    "p318_runtime_parser": PREFIX / "s22plus_fyg8_p318_max77705_runtime_parser_fixture.py",
    "p318_telemetry": PREFIX / "s22plus_fyg8_p318_max77705_telemetry.py",
    "p318_decoder": PREFIX / "s22plus_fyg8_p318_max77705_telemetry_decoder.py",
    "p318_endpoint_transition": PREFIX / "s22plus_fyg8_p318_cdc_acm_endpoint_transition.py",
    "p318_adapter_fixture": PREFIX / "s22plus_fyg8_p318_process_v2_adapter_fixture.py",
    "p318_topology_receipt": PREFIX / "s22plus_fyg8_p318_topology_receipt.py",
    "p318_stock_closure": PREFIX / "s22plus_fyg8_p318_e2_stock_closure.py",
    "p318_overlay_contract": PREFIX / "s22plus_fyg8_p318_overlay_contract.py",
    "p318_overlay_intent": PREFIX / "s22plus_fyg8_p318_overlay_intent.py",
    "p318_candidate_contract": PREFIX / "s22plus_fyg8_p318_candidate_contract.py",
    "p318_userspace_build": PREFIX / "s22plus_fyg8_p318_userspace_build.py",
    "p318_candidate_builder": PREFIX / "build_s22plus_fyg8_p318_candidate.py",
    "p318_qualification": PREFIX / "s22plus_fyg8_p318_qualification_closure.py",
    "p318_static_checker": PREFIX / "s22plus_fyg8_p318_candidate_static_checker.py",
    "p318_process_promotion": PREFIX / "prepare_s22plus_fyg8_p318_process_v2.py",
    "p318_ready_manifest": PREFIX / "prepare_s22plus_fyg8_p318_ready_manifest.py",
    "process_v2_live": PREFIX / "device_action_f1_live_v2.py",
    "process_v2_evidence": PREFIX / "device_action_f1_evidence_v2.py",
    "process_v2_runner": PREFIX / "device_action_f1_v2.py",
    "target_contract": Path("docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md"),
    "process_v2_contract": Path("docs/operations/DEVICE_ACTION_PROCESS_V2.md"),
    "p318_live_tests": Path("tests/test_s22plus_fyg8_p318_live_integration.py"),
    "p318_topology_tests": Path("tests/test_s22plus_fyg8_p318_topology_receipt.py"),
    "p318_process_adapter_tests": Path("tests/test_s22plus_fyg8_p318_process_v2_adapter_fixture.py"),
    "p318_runtime_tests": Path("tests/test_s22plus_fyg8_p318_runtime_qualification.py"),
    "p318_packaging_tests": Path("tests/test_s22plus_fyg8_p318_packaging.py"),
}
SOURCE_KEYS = frozenset(SOURCE_PATHS)
OverlayContractError = helpers.OverlayContractError
_receipt = helpers._receipt  # noqa: SLF001
_canonical = helpers._canonical  # noqa: SLF001
_read_regular = helpers._read_regular  # noqa: SLF001


def _json_regular(path: Path, label: str, maximum: int = 64 * 1024 * 1024):
    payload = _read_regular(path, label, maximum)
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OverlayContractError(f"{label} is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise OverlayContractError(f"{label} is not an object")
    return payload, value


def source_receipts(root: Path) -> dict[str, dict[str, Any]]:
    rows = {
        key: _receipt(_read_regular(root / path, f"P3.18 SOURCE_KEY {key}"))
        for key, path in sorted(SOURCE_PATHS.items())
    }
    if set(rows) != SOURCE_KEYS:
        raise OverlayContractError("P3.18 SOURCE_KEYS differ")
    return rows


def verify_parent(root: Path) -> dict[str, Any]:
    payload, value = _json_regular(root / P317_INTENT, "frozen P3.17 overlay intent")
    if (
        value.get("schema") != predecessor.INTENT_SCHEMA
        or value.get("contract_id") != predecessor.CONTRACT_ID
        or value.get("target") != TARGET
        or value.get("profile") != PROFILE
        or value.get("parent_source_contract_id") != PARENT_SOURCE_CONTRACT_ID
    ):
        raise OverlayContractError("P3.18 frozen P3.17 parent differs")
    generated = p317_generator.generate_bytes(
        root,
        run_id=bytes.fromhex(str(value["run_id"])),
        unsat_tag=bytes.fromhex(str(value["unsat_tag_hex"])),
        profile=str(value["profile"]),
    )
    for key, relative in p317_generator.artifact_paths().items():
        frozen = _read_regular(
            (root / P317_INTENT).parent / relative,
            f"frozen P3.17 materialized {key}",
        )
        if frozen != generated[key]:
            raise OverlayContractError(f"frozen P3.17 materialized source differs: {key}")
    fixed_image = value.get("fixed_image", {})
    if {
        key: fixed_image.get(key) for key in ("size", "sha256")
    } != EXPECTED_IMAGE:
        raise OverlayContractError("P3.18 frozen P3.17 Image identity differs")
    return {
        "schema": predecessor.SCHEMA,
        "contract_id": predecessor.CONTRACT_ID,
        "target": TARGET,
        "profile": PROFILE,
        "run_id": value["run_id"],
        "unsat_tag_hex": value["unsat_tag_hex"],
        "parent_source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "fixed_image": value["fixed_image"],
        "frozen_overlay_intent": _receipt(payload),
        "frozen_generated_artifacts": {
            key: _receipt(data) for key, data in sorted(generated.items())
        },
        "parent_candidate_contract": value["parent_contract"]["parent_contract"][
            "parent_candidate_contract"
        ],
        "verified": True,
    }


def generated_bytes(root: Path, parent_contract: Mapping[str, Any]) -> dict[str, bytes]:
    return generator.generate_bytes(
        root,
        run_id=bytes.fromhex(str(parent_contract["run_id"])),
        unsat_tag=bytes.fromhex(str(parent_contract["unsat_tag_hex"])),
        profile=str(parent_contract["profile"]),
    )


def _module_builds(root: Path) -> dict[str, Any]:
    latch = latch_build.audit_build(root, root / latch_build.DEFAULT_OUTPUT_DIR)
    diag = diag_build.audit_build(root, root / diag_build.DEFAULT_OUTPUT)
    for label, value, schema, verdict in (
        ("latch", latch, latch_build.SCHEMA, latch_build.VERDICT),
        ("diagnostic", diag, diag_build.SCHEMA, diag_build.VERDICT),
    ):
        if (
            value.get("schema") != schema
            or value.get("verdict") != verdict
            or value.get("a_b_byte_identical") is not True
            or any(
                value.get("modules", {}).get("a", {}).get(key)
                != value.get("modules", {}).get("b", {}).get(key)
                for key in ("size", "sha256")
            )
        ):
            raise OverlayContractError(f"P3.18 {label} A/B module build differs")
    return {"early_latch": latch, "late_diagnostic": diag, "verified": True}


def create_intent_value(root: Path) -> dict[str, Any]:
    parent_contract = verify_parent(root)
    generated = generated_bytes(root, parent_contract)
    modules = _module_builds(root)
    runtime = runtime_qualification.audit(root)
    envelope = envelope_qualification.audit(root)
    preimages = preimage_fixture.audit(root)
    adapter = adapter_fixture.audit()
    parser = runtime_parser.audit(root)
    topology = topology_receipt.validate()
    telemetry_value = {
        **decoder.validate(),
        "decoder_id": decoder.DECODER_ID,
        "decoder_policy_id": decoder.POLICY_ID,
    }
    if (
        runtime.get("verdict") != runtime_qualification.VERDICT
        or runtime.get("process_v2_integration") is not False
        or envelope.get("verdict") != envelope_qualification.VERDICT
        or preimages.get("verdict") != preimage_fixture.VERDICT
        or preimages.get("row_count") != 121
        or adapter.get("verdict") != adapter_fixture.VERDICT
        or adapter.get("retained_vector_preimages") != 126
        or parser.get("verdict") != runtime_parser.VERDICT
        or topology.get("verified") is not True
    ):
        raise OverlayContractError("P3.18 qualification input differs")
    module_identities = {
        "early_latch": {
            "name": "s22plus_dwc3_event_latch.ko",
            "boot_ramdisk_path": "lib/modules/s22plus_dwc3_event_latch.ko",
            "early_plan_membership": True,
            "late_load_only": False,
            **{
                key: modules["early_latch"]["modules"]["a"][key]
                for key in ("size", "sha256")
            },
        },
        "late_diagnostic": {
            "name": "s22plus_max77705_mux_diag_p318.ko",
            "boot_ramdisk_path": "lib/modules/s22plus_max77705_mux_diag_p318.ko",
            "early_plan_membership": False,
            "late_load_only": True,
            **{
                key: modules["late_diagnostic"]["modules"]["a"][key]
                for key in ("size", "sha256")
            },
        },
    }
    value = {
        "schema": INTENT_SCHEMA,
        "verdict": INTENT_VERDICT,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "profile": PROFILE,
        "run_id": parent_contract["run_id"],
        "unsat_tag_hex": parent_contract["unsat_tag_hex"],
        "parent_source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "parent_contract": parent_contract,
        "fixed_image": parent_contract["fixed_image"],
        "source_keys": sorted(SOURCE_KEYS),
        "source_receipts": source_receipts(root),
        "generated_artifacts": {
            key: _receipt(data) for key, data in sorted(generated.items())
        },
        "module_builds": modules,
        "module_identities": module_identities,
        "runtime_qualification": runtime,
        "envelope_qualification": envelope,
        "native_preimages": preimages,
        "process_v2_adapter_fixture": adapter,
        "runtime_parser": parser,
        "topology_receipt": topology,
        "telemetry": telemetry_value,
        "observer": {
            "candidate_window_sec": 300,
            "guard_lifetime_sec": 1200,
            "topology_phase_receipts_required": True,
            "host_observer_window_receipt_required": True,
            "rollback_drift_parks_before_transfer": True,
            "verified": True,
        },
        "packaging_requirements": {
            "stock_early_module_count": 69,
            "custom_early_module_count": 1,
            "effective_early_module_count": 70,
            "late_diagnostic_payload_count": 1,
            "total_effective_module_count": 71,
            "latch_staged_exactly_once_in_boot_ramdisk": True,
            "diagnostic_staged_exactly_once_in_boot_ramdisk": True,
            "diagnostic_absent_from_early_plan": True,
            "old_p317_diagnostic_absent": True,
            "two_userspace_builds_and_two_packages_byte_identical": True,
            "independent_boot_ramdisk_reconstruction_required": True,
            "blocks_packaging_until_validated": True,
        },
        "safety": {
            "host_only": True,
            "fixed_kernel_image": True,
            "kernel_rebuild": False,
            "full_lto_ab": False,
            "custom_module_binaries_injected": 2,
            "boot_only": True,
            "device_contact": False,
            "live_authorized": False,
        },
    }
    value["intent_sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    return value


def verify_intent(root: Path, intent_path: Path) -> dict[str, Any]:
    payload, value = _json_regular(intent_path, "P3.18 overlay intent")
    if value != create_intent_value(root):
        raise OverlayContractError("P3.18 overlay intent content differs")
    generated = generated_bytes(root, value["parent_contract"])
    for key, relative in generator.artifact_paths().items():
        actual = _read_regular(intent_path.parent / relative, f"P3.18 materialized {key}")
        if actual != generated[key]:
            raise OverlayContractError(f"P3.18 materialized source differs: {key}")
    return {
        "schema": SCHEMA,
        "verdict": CONTRACT_VERDICT,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "profile": PROFILE,
        "profile_number": 3,
        "run_id": value["run_id"],
        "unsat_tag_hex": value["unsat_tag_hex"],
        "source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": CONTRACT_ID,
        "parent_contract": value["parent_contract"],
        "parent_candidate_contract": value["parent_contract"]["parent_candidate_contract"],
        "overlay_intent": _receipt(payload),
        "overlay_intent_sha256": value["intent_sha256"],
        **{
            key: value[key]
            for key in (
                "source_receipts", "generated_artifacts", "fixed_image",
                "module_builds", "module_identities", "runtime_qualification",
                "envelope_qualification", "native_preimages",
                "process_v2_adapter_fixture", "runtime_parser",
                "topology_receipt", "telemetry", "observer",
                "packaging_requirements", "safety",
            )
        },
        "verified": True,
    }
