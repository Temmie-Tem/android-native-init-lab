#!/usr/bin/env python3
"""Bind P3.17 executability witnesses and the 69+1 package to fixed P3.10."""

from __future__ import annotations

import hashlib
from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Mapping

import s22plus_fyg8_max77705_custom_surface_contract as surface
import s22plus_fyg8_p308_overlay_contract as helpers
import s22plus_fyg8_p316_overlay_contract as predecessor
import s22plus_fyg8_p316_sidecar_positive_control as sidecar_control
import s22plus_fyg8_p317_executability_fixed_point as fixed_point
import s22plus_fyg8_p317_fw_devlink_contract as fw_devlink
import s22plus_fyg8_p317_generator as generator
import s22plus_fyg8_p317_lifecycle_audit as lifecycle_audit
import s22plus_fyg8_p317_max77705_envelope_fixture as envelope_fixture
import s22plus_fyg8_p317_max77705_telemetry as telemetry
import s22plus_fyg8_p317_max77705_telemetry_decoder as decoder
import s22plus_fyg8_p317_must_bind_claim_contract as must_bind
import s22plus_fyg8_p317_process_v2_adapter_fixture as adapter_fixture
import s22plus_fyg8_p317_runtime_fixture as runtime_fixture


SCHEMA = "s22plus_fyg8_p317_userspace_overlay_contract_v1"
CONTRACT_ID = decoder.OVERLAY_CONTRACT_ID
INTENT_SCHEMA = "s22plus_fyg8_p317_userspace_overlay_intent_v1"
INTENT_VERDICT = "PASS_P317_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
CONTRACT_VERDICT = "PASS_P317_USERSPACE_OVERLAY_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P317_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
TARGET = predecessor.TARGET
PROFILE = predecessor.PROFILE
PARENT_SOURCE_CONTRACT_ID = predecessor.PARENT_SOURCE_CONTRACT_ID
PARENT_SOURCE = predecessor.PARENT_SOURCE
PARENT_PATCH = predecessor.PARENT_PATCH
PARENT_IMAGE = predecessor.PARENT_IMAGE
PARENT_REPRO_RESULT = predecessor.PARENT_REPRO_RESULT
EXPECTED_IMAGE = predecessor.EXPECTED_IMAGE
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p317/intent")
DEFAULT_INTENT = DEFAULT_OUT / "overlay-intent.json"
DEFAULT_MATERIALIZED = DEFAULT_OUT / "materialized-sources"

PREFIX = Path("workspace/public/src/scripts/revalidation")
NATIVE = Path("workspace/public/src/native-init")
KERNEL_MODULE = Path("workspace/public/src/kernel-modules/s22plus_max77705_mux_diag")
SOURCE_PATHS = {
    "max77705_diag_source": KERNEL_MODULE / "s22plus_max77705_mux_diag.c",
    "p317_envelope": NATIVE / "s22plus_fyg8_p317_max77705_envelope.inc.c",
    "p317_runtime": NATIVE / "s22plus_fyg8_p317_max77705_runtime.inc.c",
    "p317_envelope_fixture_c": NATIVE / "s22plus_fyg8_p317_max77705_envelope_fixture.c",
    "p316_result_parser": NATIVE / "s22plus_fyg8_max77705_result_parser.inc.c",
    "p316_runtime_core": NATIVE / "s22plus_fyg8_max77705_runtime_core.inc.c",
    "p317_generator": PREFIX / "s22plus_fyg8_p317_generator.py",
    "p317_runtime_fixture": PREFIX / "s22plus_fyg8_p317_runtime_fixture.py",
    "p317_lifecycle_audit": PREFIX / "s22plus_fyg8_p317_lifecycle_audit.py",
    "p317_envelope_fixture": PREFIX / "s22plus_fyg8_p317_max77705_envelope_fixture.py",
    "p317_telemetry": PREFIX / "s22plus_fyg8_p317_max77705_telemetry.py",
    "p317_decoder": PREFIX / "s22plus_fyg8_p317_max77705_telemetry_decoder.py",
    "p317_adapter_fixture": PREFIX / "s22plus_fyg8_p317_process_v2_adapter_fixture.py",
    "p317_must_bind": PREFIX / "s22plus_fyg8_p317_must_bind_claim_contract.py",
    "p317_fw_devlink": PREFIX / "s22plus_fyg8_p317_fw_devlink_contract.py",
    "p317_fixed_point": PREFIX / "s22plus_fyg8_p317_executability_fixed_point.py",
    "p317_overlay_contract": PREFIX / "s22plus_fyg8_p317_overlay_contract.py",
    "p317_overlay_intent": PREFIX / "s22plus_fyg8_p317_overlay_intent.py",
    "p317_candidate_contract": PREFIX / "s22plus_fyg8_p317_candidate_contract.py",
    "p317_e2_stock_closure": PREFIX / "s22plus_fyg8_p317_e2_stock_closure.py",
    "p317_userspace_build": PREFIX / "s22plus_fyg8_p317_userspace_build.py",
    "p317_candidate_builder": PREFIX / "build_s22plus_fyg8_p317_candidate.py",
    "p317_static_checker": PREFIX / "s22plus_fyg8_p317_candidate_static_checker.py",
    "p317_qualification": PREFIX / "s22plus_fyg8_p317_qualification_closure.py",
    "p317_process_promotion": PREFIX / "prepare_s22plus_fyg8_p317_process_v2.py",
    "p317_ready_manifest": PREFIX / "prepare_s22plus_fyg8_p317_ready_manifest.py",
    "p316_generator": PREFIX / "s22plus_fyg8_p316_generator.py",
    "p316_lifecycle_audit": PREFIX / "s22plus_fyg8_p316_lifecycle_audit.py",
    "p316_e2_stock_closure": PREFIX / "s22plus_fyg8_p316_e2_stock_closure.py",
    "p316_sidecar_control": PREFIX / "s22plus_fyg8_p316_sidecar_positive_control.py",
    "process_v2_live_adapter": PREFIX / "device_action_f1_live_v2.py",
    "process_v2_evidence_adapter": PREFIX / "device_action_f1_evidence_v2.py",
    "process_v2_runner": PREFIX / "device_action_f1_v2.py",
    "p317_process_v2_tests": Path("tests/test_s22plus_fyg8_p317_process_v2.py"),
    "p317_fixed_point_tests": Path("tests/test_s22plus_fyg8_p317_executability_fixed_point.py"),
    "p317_fw_devlink_tests": Path("tests/test_s22plus_fyg8_p317_fw_devlink_contract.py"),
    "p317_must_bind_tests": Path("tests/test_s22plus_fyg8_p317_must_bind_claim_contract.py"),
}
SOURCE_KEYS = frozenset(SOURCE_PATHS)
OverlayContractError = helpers.OverlayContractError
_receipt = helpers._receipt  # noqa: SLF001
_canonical = helpers._canonical  # noqa: SLF001
_read_regular = helpers._read_regular  # noqa: SLF001

MUST_BIND_RECEIPT = Path(
    "workspace/private/outputs/s22plus_fyg8_p317/"
    "must-bind-claim-contract-20260812-01.json"
)
FW_DEVLINK_RECEIPT = Path(
    "workspace/private/outputs/s22plus_fyg8_p317/"
    "fw-devlink-contract-20260812-01.json"
)
FIXED_POINT_RECEIPT = Path(
    "workspace/private/outputs/s22plus_fyg8_p317/"
    "executability-fixed-point-20260812-01.json"
)


def source_receipts(root: Path) -> dict[str, dict[str, Any]]:
    rows = {
        key: _receipt(_read_regular(root / path, f"P3.17 SOURCE_KEY {key}"))
        for key, path in sorted(SOURCE_PATHS.items())
    }
    if set(rows) != SOURCE_KEYS:
        raise OverlayContractError("P3.17 SOURCE_KEYS differ")
    return rows


def _json_regular(path: Path, label: str, maximum: int = 8 * 1024 * 1024):
    payload = _read_regular(path, label, maximum)
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OverlayContractError(f"{label} is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise OverlayContractError(f"{label} is not an object")
    return payload, value


def _reviewed_gate(root: Path, relative: Path, *, schema: str, verdict: str):
    payload, value = _json_regular(root / relative, f"P3.17 reviewed {schema}")
    if value.get("schema") != schema or value.get("verdict") != verdict:
        raise OverlayContractError(f"P3.17 reviewed gate differs: {schema}")
    return {"artifact": _receipt(payload), "value": value, "verified": True}


def _exact_must_bind(root: Path) -> dict[str, Any]:
    read = must_bind.stable_read
    return must_bind.build_contract(
        extractor_data=read(Path(must_bind.__file__).resolve(), "claim extractor", 2**21),
        runtime_data=read(root / must_bind.DEFAULT_RUNTIME_SOURCE, "P3.16 runtime", 2**21),
        diagnostic_data=read(root / must_bind.DEFAULT_DIAGNOSTIC_SOURCE, "diagnostic", 2**21),
        surface_data=read(root / must_bind.DEFAULT_SURFACE_SOURCE, "surface", 2**22),
        live_data=read(root / must_bind.DEFAULT_LIVE_SOURCE, "live", 2**22),
        qup_data=read(root / must_bind.DEFAULT_QUP_SOURCE, "QUP", 2**22),
        i2c_driver_data=read(root / must_bind.DEFAULT_I2C_DRIVER_SOURCE, "I2C driver", 2**22),
        i2c_core_data=read(root / must_bind.DEFAULT_I2C_CORE_SOURCE, "I2C core", 2**22),
        i2c_of_data=read(root / must_bind.DEFAULT_I2C_OF_SOURCE, "I2C OF", 2**21),
        of_platform_data=read(root / must_bind.DEFAULT_OF_PLATFORM_SOURCE, "OF platform", 2**21),
        qup_dts_data=read(root / must_bind.DEFAULT_QUP_DTS_SOURCE, "QUP DT", 2**22),
        spmi_arb_data=read(root / must_bind.DEFAULT_SPMI_ARB_SOURCE, "SPMI arb", 2**22),
        spmi_core_data=read(root / must_bind.DEFAULT_SPMI_CORE_SOURCE, "SPMI core", 2**22),
        spmi_pmic_data=read(root / must_bind.DEFAULT_SPMI_PMIC_SOURCE, "SPMI PMIC", 2**22),
        pm8350c_dts_data=read(root / must_bind.DEFAULT_PM8350C_DTS_SOURCE, "PM8350C DT", 2**22),
    )


def _exact_fw_devlink(root: Path) -> dict[str, Any]:
    read = fw_devlink.stable_read
    return fw_devlink.build_contract(
        extractor_data=read(Path(fw_devlink.__file__).resolve(), "fw extractor", 2**21),
        property_data=read(root / fw_devlink.DEFAULT_PROPERTY_SOURCE, "OF property", 2**19),
        core_data=read(root / fw_devlink.DEFAULT_CORE_SOURCE, "driver core", 2**20),
        of_base_data=read(root / fw_devlink.DEFAULT_OF_BASE_SOURCE, "OF base", 2**19),
        dts_data=read(root / fw_devlink.DEFAULT_DTS, "exact g0q DTS", 2**23),
    )


def _exact_fixed_point(root: Path) -> dict[str, Any]:
    read = fixed_point.stable_read
    metadata = fixed_point.module_plan.load_metadata(root / fixed_point.DEFAULT_METADATA)
    return fixed_point.build_contract(
        extractor_data=read(Path(fixed_point.__file__).resolve(), "fixed-point extractor", 2**21),
        dtbo_data=read(root / fixed_point.DEFAULT_DTBO, "stock DTBO", 2**26),
        vendor_dtb_data=read(root / fixed_point.DEFAULT_VENDOR_DTB, "stock vendor DTB", 2**26),
        property_data=read(root / fixed_point.DEFAULT_PROPERTY_SOURCE, "OF property", 2**19),
        core_data=read(root / fixed_point.DEFAULT_CORE_SOURCE, "driver core", 2**20),
        of_base_data=read(root / fixed_point.DEFAULT_OF_BASE_SOURCE, "OF base", 2**19),
        irq_data=read(root / fixed_point.DEFAULT_IRQ_SOURCE, "OF IRQ", 2**19),
        rpmh_data=read(root / fixed_point.DEFAULT_RPMH_SOURCE, "RPMh", 2**19),
        rpmh_regulator_data=read(root / fixed_point.DEFAULT_RPMH_REGULATOR_SOURCE, "RPMh regulator", 2**19),
        config_data=read(root / fixed_point.DEFAULT_CONFIG, "fixed Image config", 2**19),
        predecessor_data=read(root / fixed_point.DEFAULT_PREDECESSOR, "P3.16 predecessor", 2**23),
        must_bind_data=read(root / fixed_point.DEFAULT_MUST_BIND_RECEIPT, "must-bind receipt", 2**19),
        metadata=metadata,
        fdtoverlay=root / fixed_point.DEFAULT_FDTOVERLAY,
        libfdt=root / fixed_point.DEFAULT_LIBFDT,
    )


@lru_cache(maxsize=1)
def _executability_gates(root: Path) -> dict[str, Any]:
    claims = _reviewed_gate(
        root, MUST_BIND_RECEIPT, schema=must_bind.SCHEMA, verdict=must_bind.VERDICT
    )
    fw = _reviewed_gate(
        root, FW_DEVLINK_RECEIPT, schema=fw_devlink.SCHEMA,
        verdict=fw_devlink.VERDICT,
    )
    fixed = _reviewed_gate(
        root, FIXED_POINT_RECEIPT, schema=fixed_point.SCHEMA,
        verdict=fixed_point.VERDICT,
    )
    claim_value = claims["value"]
    fw_value = fw["value"]
    fixed_value = fixed["value"]
    if (
        _read_regular(root / MUST_BIND_RECEIPT, "P3.17 must-bind receipt")
        != must_bind.encode_contract(_exact_must_bind(root))
        or _read_regular(root / FW_DEVLINK_RECEIPT, "P3.17 fw_devlink receipt")
        != fw_devlink.encode_contract(_exact_fw_devlink(root))
        or _read_regular(root / FIXED_POINT_RECEIPT, "P3.17 fixed-point receipt")
        != fixed_point.encode_contract(_exact_fixed_point(root))
    ):
        raise OverlayContractError("P3.17 reviewed gate is stale")
    if (
        claim_value.get("human_causal_review") != "SATISFIED_2026_08_12"
        or fixed_value.get("must_bind", {}).get("human_causal_review")
        != "SATISFIED_2026_08_12"
        or fixed_value.get("module_delta", {}).get("added_early_module_count") != 5
        or fixed_value.get("module_delta", {}).get("successor_early_count") != 69
        or fixed_value.get("module_delta", {}).get("successor_effective_total_count") != 70
        or fixed_value.get("applicable_bases_static_closure_identical") is not True
        or fixed_value.get("status") != "CANDIDATE_NOT_READY"
        or fw_value.get("max77705_regression", {}).get(
            "deduplicated_consumer_supplier_edge_count"
        ) != 1
    ):
        raise OverlayContractError("P3.17 reviewed executability facts differ")
    return {"must_bind": claims, "fw_devlink": fw, "fixed_point": fixed}


def verify_parent(root: Path) -> dict[str, Any]:
    value = predecessor.create_intent_value(root)
    if (
        value.get("contract_id") != predecessor.CONTRACT_ID
        or value.get("target") != TARGET
        or value.get("profile") != PROFILE
        or value.get("parent_source_contract_id") != PARENT_SOURCE_CONTRACT_ID
    ):
        raise OverlayContractError("P3.17 P3.16 predecessor differs")
    return value


def generated_bytes(root: Path, parent_contract: Mapping[str, Any]) -> dict[str, bytes]:
    return generator.generate_bytes(
        root,
        run_id=bytes.fromhex(str(parent_contract["run_id"])),
        unsat_tag=bytes.fromhex(str(parent_contract["unsat_tag_hex"])),
        profile=str(parent_contract["profile"]),
    )


def create_intent_value(root: Path) -> dict[str, Any]:
    parent_contract = verify_parent(root)
    generated = generated_bytes(root, parent_contract)
    runtime = runtime_fixture.audit(root)
    lifecycle = lifecycle_audit.audit(root)
    envelope = envelope_fixture.audit(root)
    adapter = adapter_fixture.audit()
    sidecar = sidecar_control.audit(root)
    gates = _executability_gates(root)
    telemetry_value = {
        **telemetry.validate(),
        "decoder_id": decoder.DECODER_ID,
        "decoder_policy_id": decoder.POLICY_ID,
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
        "max77705_surface_gate": predecessor._surface_gate(root),  # noqa: SLF001
        "executability_gates": gates,
        "runtime_fixture": runtime,
        "late_loader_lifecycle": lifecycle,
        "envelope_fixture": envelope,
        "process_v2_adapter_fixture": adapter,
        "sidecar_positive_control": sidecar,
        "telemetry": telemetry_value,
        "observer": {
            "candidate_window_sec": 300,
            "guard_lifetime_sec": 1200,
            "final_pair_before_banner": True,
            "usb_sidecar_required": True,
            "usb_sidecar_positive_control": sidecar["verdict"],
            "fixed_image": True,
            "verified": True,
        },
        "packaging_requirements": {
            "early_stock_module_count": 69,
            "late_diagnostic_payload_count": 1,
            "total_effective_module_count": 70,
            "derived_early_module_delta": 5,
            "predecessor_order_preserved_as_subsequence": True,
            "diagnostic_absent_from_early_plan": True,
            "diagnostic_staged_exactly_once_in_boot_ramdisk": True,
            "diagnostic_module_identity": list(surface.DIAG_MODULE_IDENTITY),
            "runtime_executability_fixture_required": runtime["verdict"],
            "real_process_v2_round_trip_required": adapter["verdict"],
            "late_loader_lifecycle_required": lifecycle["verdict"],
            "sidecar_positive_control_required": sidecar["verdict"],
            "two_userspace_builds_and_two_packages_byte_identical": True,
            "independent_boot_ramdisk_reconstruction_required": True,
            "blocks_packaging_until_validated": True,
        },
        "safety": {
            "host_only": True,
            "fixed_kernel_image": True,
            "kernel_rebuild": False,
            "full_lto_ab": False,
            "early_stock_modules_added": 5,
            "custom_module_binaries_injected": 1,
            "boot_only": True,
            "device_contact": False,
            "live_authorized": False,
        },
    }
    value["intent_sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    return value


def verify_intent(root: Path, intent_path: Path) -> dict[str, Any]:
    payload, value = _json_regular(intent_path, "P3.17 overlay intent")
    if value != create_intent_value(root):
        raise OverlayContractError("P3.17 overlay intent content differs")
    generated = generated_bytes(root, value["parent_contract"])
    for key, relative in generator.artifact_paths().items():
        actual = _read_regular(intent_path.parent / relative, f"P3.17 materialized {key}")
        if actual != generated[key]:
            raise OverlayContractError(f"P3.17 materialized source differs: {key}")
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
        "parent_candidate_contract": value["parent_contract"]["parent_contract"]["parent_candidate_contract"],
        "overlay_intent": _receipt(payload),
        "overlay_intent_sha256": value["intent_sha256"],
        **{
            key: value[key]
            for key in (
                "source_receipts", "generated_artifacts", "fixed_image",
                "max77705_surface_gate", "executability_gates",
                "runtime_fixture", "late_loader_lifecycle", "envelope_fixture",
                "process_v2_adapter_fixture", "sidecar_positive_control",
                "telemetry", "observer", "packaging_requirements", "safety",
            )
        },
        "verified": True,
    }
