#!/usr/bin/env python3
"""Bind the exact FYG8 P2.25 build to its supplemental linked audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p225_build as p225  # noqa: E402


SCHEMA = "s22plus_fyg8_p225_build_artifact_contract_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
BUILD_SCHEMA = "s22plus_fyg8_p225_build_v1"
LEGACY_CONTRACT_KEY = "p225_guard_durability_contract"
PATCH_SHA256 = "fbbbcc43685f4899fdceb95d4b8b9e92d111fad07bfaf582752aa8c36ccf9254"
CONFIG_SYMBOL = "CONFIG_S22PLUS_FYG8_PID1_SAME_RING_DISCRIMINATOR=y"

IMAGE_SIZE = 41_490_944
IMAGE_SHA256 = p225.EXPECTED_IMAGE_SHA256
VMLINUX_SIZE = 476_936_664
VMLINUX_SHA256 = p225.EXPECTED_VMLINUX_SHA256
CONFIG_SIZE = 185_347
CONFIG_SHA256 = "cf6f6c91bc572daa7d6d44cf6ac7a693698443ed32dc1a0748b769bf99329684"
BUILD_RESULT_SIZE = 683_315
BUILD_RESULT_SHA256 = (
    "39f54cbc2349b127ea56083044640c00e6c061167ad4cadb48603296eec4f0a5"
)


class ArtifactError(ValueError):
    """An input does not match the immutable P2.25 build closure."""


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _require_identity(
    data: bytes, size: int, digest: str, label: str
) -> dict[str, Any]:
    actual = receipt(data)
    if actual != {"size": size, "sha256": digest}:
        raise ArtifactError(f"P2.25 {label} identity mismatch")
    return actual


def _require_verified_gate(result: dict[str, Any], name: str) -> None:
    gate = result.get(name)
    if not isinstance(gate, dict) or gate.get("verified") is not True:
        raise ArtifactError(f"P2.25 build gate not verified: {name}")


def verify(
    *,
    image: bytes,
    vmlinux: bytes,
    config: bytes,
    build_result: bytes,
    vmlinux_path: Path | None = None,
) -> dict[str, Any]:
    identities = {
        "Image": _require_identity(image, IMAGE_SIZE, IMAGE_SHA256, "Image"),
        "vmlinux": _require_identity(
            vmlinux, VMLINUX_SIZE, VMLINUX_SHA256, "vmlinux"
        ),
        ".config": _require_identity(
            config, CONFIG_SIZE, CONFIG_SHA256, ".config"
        ),
        "build_result": _require_identity(
            build_result,
            BUILD_RESULT_SIZE,
            BUILD_RESULT_SHA256,
            "build result",
        ),
    }
    if vmlinux_path is None:
        raise ArtifactError("P2.25 linked audit requires the stable vmlinux path")
    try:
        result = json.loads(build_result.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ArtifactError("P2.25 build result is not valid JSON") from exc
    if not isinstance(result, dict):
        raise ArtifactError("P2.25 build result is not an object")
    required = {
        "schema": BUILD_SCHEMA,
        "target": TARGET,
        "mode": "build",
        "returncode": 7,
        "build_command_returncode": 0,
        "p225_build_pass": False,
    }
    for name, expected in required.items():
        if result.get(name) != expected:
            raise ArtifactError(f"P2.25 build result {name} mismatch")
    source_delta = result.get("source_delta")
    if (
        not isinstance(source_delta, dict)
        or source_delta.get("patch_sha256") != PATCH_SHA256
        or source_delta.get("restored") is not True
        or source_delta.get("verified") is not True
    ):
        raise ArtifactError("P2.25 source patch/restoration mismatch")
    legacy = result.get(LEGACY_CONTRACT_KEY)
    if (
        not isinstance(legacy, dict)
        or legacy.get("patch", {}).get("sha256") != PATCH_SHA256
        or legacy.get("patch", {}).get("verified") is not True
        or legacy.get("source", {}).get("current_node_reg_parser") is not True
        or legacy.get("source", {}).get("generic_resource_helper_absent")
        is not True
        or legacy.get("stock_dtb", {}).get("generic_parser_regression_proven")
        is not True
    ):
        raise ArtifactError("P2.25 embedded source/DT contract mismatch")
    for name in (
        "source_symlink_control_runtime",
        "output_gate",
        "module_gate",
        "kernel_banner_gate",
        "sec_log_buf_timing_gate",
        "exclusive_output_root",
    ):
        _require_verified_gate(result, name)
    witness = result.get("witness_output_gate")
    if (
        not isinstance(witness, dict)
        or witness.get("verified") is not False
        or witness.get("p225_linked_audit", {}).get("error")
        != "objdump missing or indirect: /usr/bin/aarch64-linux-gnu-objdump"
    ):
        raise ArtifactError("P2.25 original post-build audit failure changed")
    outputs = result.get("outputs")
    if not isinstance(outputs, list):
        raise ArtifactError("P2.25 output inventory is malformed")
    for name in ("Image", "vmlinux", ".config"):
        matches = [
            row
            for row in outputs
            if isinstance(row, dict) and row.get("name") == name
        ]
        if len(matches) != 1:
            raise ArtifactError(f"P2.25 output cardinality mismatch: {name}")
        if any(
            matches[0].get(key) != identities[name][key]
            for key in ("size", "sha256")
        ):
            raise ArtifactError(f"P2.25 output receipt mismatch: {name}")
    try:
        config_lines = config.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise ArtifactError("P2.25 compiled config is not UTF-8") from exc
    if config_lines.count(CONFIG_SYMBOL) != 1:
        raise ArtifactError("P2.25 compiled config symbol mismatch")
    safety = result.get("safety")
    if not isinstance(safety, dict) or any(
        safety.get(name) is not expected
        for name, expected in {
            "host_only": True,
            "device_contact": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "packaging_outputs_promoted": False,
        }.items()
    ):
        raise ArtifactError("P2.25 build safety contract mismatch")
    try:
        linked = p225.audit_linked_vmlinux(vmlinux_path)
    except p225.BuildAuditError as exc:
        raise ArtifactError(f"P2.25 supplemental linked audit failed: {exc}") from exc
    if linked.get("verified") is not True or linked.get("reset_retention_proven") is not False:
        raise ArtifactError("P2.25 supplemental linked audit result mismatch")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "artifacts": identities,
        "compiled_config_symbol_count": 1,
        "original_build_command_passed": True,
        "original_post_build_tool_path_failure_reconciled": True,
        "supplemental_linked_audit": linked,
        "reset_retention_proven": False,
        "verified": True,
    }
