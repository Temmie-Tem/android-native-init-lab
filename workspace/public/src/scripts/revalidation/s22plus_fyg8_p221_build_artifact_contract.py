#!/usr/bin/env python3
"""Immutable identities for the completed FYG8 P2.21 kernel build."""

from __future__ import annotations

import hashlib
import json
from typing import Any


SCHEMA = "s22plus_fyg8_p221_build_artifact_contract_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
BUILD_SCHEMA = "s22plus_fyg8_p221_build_v1"
BUILD_VERDICT = "PASS_P219_SAME_RING_IMPLEMENTATION_HOST_ONLY"
PATCH_SHA256 = "6bf03ca0d3448e0a707b03815e94d8ef5c059e9aaa14f3612a0bb953f3758c44"
CONFIG_SYMBOL = "CONFIG_S22PLUS_FYG8_PID1_SAME_RING_DISCRIMINATOR=y"

IMAGE_SIZE = 41_490_944
IMAGE_SHA256 = "3afa1c8121c6040e09329abae4d0a8a61ff0f9ee7fe37ed311e1b2e56ab24ce5"
VMLINUX_SIZE = 476_932_816
VMLINUX_SHA256 = "83e5cdc23143f69f2be22038f39cbb5c427999fe3ffc63a32319ee0aab77e06e"
CONFIG_SIZE = 185_347
CONFIG_SHA256 = "cf6f6c91bc572daa7d6d44cf6ac7a693698443ed32dc1a0748b769bf99329684"
BUILD_RESULT_SIZE = 679_932
BUILD_RESULT_SHA256 = "5d9bca09726c1dca27ce6b74e1da7401575cd79ce57249bc6abaa147fc0d6c19"


class ArtifactError(ValueError):
    """An input does not match the immutable P2.21 build closure."""


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _require_identity(data: bytes, size: int, digest: str, label: str) -> dict[str, Any]:
    if (
        size <= 0
        or len(digest) != 64
        or any(value not in "0123456789abcdef" for value in digest)
    ):
        raise ArtifactError("P2.21 artifact contract is not populated")
    actual = receipt(data)
    if actual != {"size": size, "sha256": digest}:
        raise ArtifactError(f"P2.21 {label} identity mismatch")
    return actual


def verify(
    *, image: bytes, vmlinux: bytes, config: bytes, build_result: bytes
) -> dict[str, Any]:
    identities = {
        "Image": _require_identity(image, IMAGE_SIZE, IMAGE_SHA256, "Image"),
        "vmlinux": _require_identity(
            vmlinux, VMLINUX_SIZE, VMLINUX_SHA256, "vmlinux"
        ),
        ".config": _require_identity(config, CONFIG_SIZE, CONFIG_SHA256, ".config"),
        "build_result": _require_identity(
            build_result, BUILD_RESULT_SIZE, BUILD_RESULT_SHA256, "build result"
        ),
    }
    try:
        result = json.loads(build_result.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ArtifactError("P2.21 build result is not valid JSON") from exc
    if not isinstance(result, dict):
        raise ArtifactError("P2.21 build result is not an object")
    required = {
        "schema": BUILD_SCHEMA,
        "target": TARGET,
        "mode": "build",
        "returncode": 0,
        "p221_build_pass": True,
    }
    for name, expected in required.items():
        if result.get(name) != expected:
            raise ArtifactError(f"P2.21 build result {name} mismatch")
    contract = result.get("p219_same_ring_contract")
    if not isinstance(contract, dict) or contract.get("verdict") != BUILD_VERDICT:
        raise ArtifactError("P2.19 same-ring contract is not bound")
    source_delta = result.get("source_delta")
    if (
        not isinstance(source_delta, dict)
        or source_delta.get("patch_sha256") != PATCH_SHA256
        or source_delta.get("restored") is not True
    ):
        raise ArtifactError("P2.21 source patch/restoration mismatch")
    for name in (
        "source_symlink_control_runtime",
        "output_gate",
        "module_gate",
        "kernel_banner_gate",
        "witness_output_gate",
        "sec_log_buf_timing_gate",
        "exclusive_output_root",
    ):
        gate = result.get(name)
        if not isinstance(gate, dict) or gate.get("verified") is not True:
            raise ArtifactError(f"P2.21 build gate not verified: {name}")
    outputs = result.get("outputs")
    if not isinstance(outputs, list):
        raise ArtifactError("P2.21 output inventory is malformed")
    for name in ("Image", "vmlinux", ".config"):
        matches = [
            row
            for row in outputs
            if isinstance(row, dict) and row.get("name") == name
        ]
        if len(matches) != 1:
            raise ArtifactError(f"P2.21 build output cardinality mismatch: {name}")
        row = matches[0]
        expected = identities[name]
        if any(row.get(key) != expected[key] for key in expected):
            raise ArtifactError(f"P2.21 build output receipt mismatch: {name}")
    try:
        config_lines = config.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise ArtifactError("P2.21 compiled config is not UTF-8") from exc
    if config_lines.count(CONFIG_SYMBOL) != 1:
        raise ArtifactError("P2.21 compiled config symbol mismatch")
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
        raise ArtifactError("P2.21 build safety contract mismatch")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "artifacts": identities,
        "compiled_config_symbol_count": 1,
        "verified": True,
    }
