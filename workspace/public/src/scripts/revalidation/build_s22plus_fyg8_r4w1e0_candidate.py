#!/usr/bin/env python3
"""Build one host-only FYG8 R4W1-E0 fixed-probe candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_s22plus_fyg8_r4w1e_e1_candidate as engine  # noqa: E402
import s22plus_fyg8_r4w1e0_build_artifact_contract as artifact  # noqa: E402
import s22plus_fyg8_r4w1e0_pid1_userspace_proof as proof  # noqa: E402


BASE_E1 = engine.e1
SCHEMA = "s22plus_fyg8_r4w1e0_candidate_build_v1"
RUN_MANIFEST_SCHEMA = "s22plus_fyg8_r4w1e0_run_manifest_v1"
VERDICT = "PASS_R4W1E0_CANDIDATE_BUILT_HOST_ONLY"
RUNTIME_SCHEMA = "s22plus_fyg8_r4w1e0_candidate_runtime_contract_v1"
RUNTIME_VERDICT = "PASS_R4W1E0_EXACT_RUNTIME_BOUND"
RUNG = "R4W1-E0"
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e0_candidate/reproduction-a"
)
DEFAULT_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e0_candidate_inputs/Image"
)
DEFAULT_KERNEL_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e0_candidate_inputs/"
    "kernel-build-result.json"
)
DEFAULT_CHILD = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e0_runtime/s22-e1-child"
)


class _CheckpointContract:
    TARGET = proof.TARGET
    PATCH_SHA256 = proof.PATCH_SHA256
    CARRIER_SHA256 = proof.RUNTIME_RECEIPT_SHA256
    ENTRY_PROOF = proof.ENTRY_PROOF
    ENTRY_FAMILY = proof.PROOF_FAMILY
    MODEL_RUN_IDS = {"E1": bytes.fromhex("80a64813040630db026bba06f21f8d17")}


checkpoint = _CheckpointContract()


def _proof_call(function: Any, *args: Any) -> Any:
    try:
        return function(*args)
    except proof.CheckError as exc:
        raise BASE_E1.CheckError(str(exc)) from exc


class _RuntimeContract:
    SCHEMA = RUNTIME_SCHEMA
    VERDICT = RUNTIME_VERDICT
    CheckError = BASE_E1.CheckError

    def __getattr__(self, name: str) -> Any:
        return getattr(BASE_E1, name)

    def run_check(self, *args: Any) -> dict[str, Any]:
        base = BASE_E1.run_check(*args)
        root = proof.shared.repo_root()
        sources = _proof_call(proof.check_runtime_sources, root)
        runtime = _proof_call(
            proof.check_runtime_artifact,
            root / proof.DEFAULT_INIT, root / proof.DEFAULT_RUNTIME_RECEIPT
        )
        child = BASE_E1.read_direct(root / DEFAULT_CHILD, "R4W1-E0 child artifact")
        if hashlib.sha256(child).hexdigest() != (
            "9a57b30aa3fb08ee0aab4d045d2805dd36875bb80bcba7b0b6606f619df71639"
        ):
            raise BASE_E1.CheckError("R4W1-E0 child artifact identity mismatch")
        return {
            "schema": self.SCHEMA,
            "verdict": self.VERDICT,
            "base_e1_contract": {
                "schema": base["schema"],
                "verdict": base["verdict"],
            },
            "sources": sources,
            "runtime": runtime,
        }

    def compile_one(self, *args: Any) -> dict[str, Any]:
        run_id = args[5]
        if run_id != proof.PROBE_ID:
            raise BASE_E1.CheckError("R4W1-E0 compile requested a non-probe run ID")
        compiled = BASE_E1.compile_one(*args)
        root = proof.shared.repo_root()
        expected_init = BASE_E1.read_direct(root / proof.DEFAULT_INIT, "exact E0 init")
        expected_child = BASE_E1.read_direct(root / DEFAULT_CHILD, "exact E0 child")
        if (
            compiled["init"]["data"] != expected_init
            or compiled["child"]["data"] != expected_child
        ):
            raise BASE_E1.CheckError("compiled R4W1-E0 runtime differs from receipt")
        _proof_call(
            proof.check_runtime_artifact,
            root / proof.DEFAULT_INIT, root / proof.DEFAULT_RUNTIME_RECEIPT
        )
        return compiled


runtime = _RuntimeContract()


def _receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _require_receipt(
    value: Any, expected: dict[str, Any], label: str, error: type[ValueError]
) -> None:
    if not isinstance(value, dict) or any(
        value.get(name) != expected[name] for name in ("size", "sha256")
    ):
        raise error(f"{label} receipt mismatch")


def verify_kernel_result_common(
    data: bytes,
    image_receipt: dict[str, Any],
    error: type[ValueError],
) -> dict[str, Any]:
    result_receipt = _receipt(data)
    if not artifact.matches(
        size=image_receipt.get("size", -1),
        sha256=image_receipt.get("sha256", ""),
        expected_size=artifact.IMAGE_SIZE,
        expected_sha256=artifact.IMAGE_SHA256,
    ):
        raise error("R4W1-E0 Image does not match the immutable build artifact")
    if not artifact.matches(
        size=result_receipt["size"],
        sha256=result_receipt["sha256"],
        expected_size=artifact.KERNEL_BUILD_RESULT_SIZE,
        expected_sha256=artifact.KERNEL_BUILD_RESULT_SHA256,
    ):
        raise error("R4W1-E0 kernel result does not match the immutable artifact")
    try:
        result = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise error("invalid R4W1-E0 kernel result") from exc
    if not isinstance(result, dict):
        raise error("R4W1-E0 kernel result is not an object")
    required = {
        "schema": "s22plus_fyg8_r4w1e0_build_v1",
        "target": proof.TARGET,
        "mode": "build",
        "returncode": 0,
        "r4w1e0_build_pass": True,
    }
    for name, expected in required.items():
        if result.get(name) != expected:
            raise error(f"R4W1-E0 kernel result {name} mismatch")
    for name in (
        "source_delta",
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
            raise error(f"R4W1-E0 kernel gate not verified: {name}")
    source_delta = result["source_delta"]
    if (
        source_delta.get("patch_sha256") != proof.PATCH_SHA256
        or source_delta.get("restored") is not True
    ):
        raise error("R4W1-E0 kernel patch/restoration mismatch")
    contract = result.get("r4w1e0_pid1_userspace_proof_contract")
    if not isinstance(contract, dict) or contract.get("verdict") != proof.VERDICT:
        raise error("R4W1-E0 kernel proof contract mismatch")
    witness = result["witness_output_gate"]
    expected_witness = {
        "image_size": engine.KERNEL_SIZE,
        "image_proof_count": 1,
        "vmlinux_proof_count": 1,
        "image_userspace_proof_count": 1,
        "vmlinux_userspace_proof_count": 1,
        "image_shared_family_count": 2,
        "vmlinux_shared_family_count": 2,
        "config_enable_count": 1,
        "fips_enable_count": 1,
    }
    for name, expected in expected_witness.items():
        if witness.get(name) != expected:
            raise error(f"R4W1-E0 kernel witness mismatch: {name}")
    if any(witness.get("historical_config_enable_counts", {}).values()) or any(
        row.get("image") or row.get("vmlinux")
        for row in witness.get("historical_family_counts", {}).values()
        if isinstance(row, dict)
    ):
        raise error("historical R4W1 kernel proof remains enabled")
    outputs = result.get("outputs")
    if not isinstance(outputs, list):
        raise error("R4W1-E0 kernel outputs malformed")
    image_rows = [row for row in outputs if isinstance(row, dict) and row.get("name") == "Image"]
    if len(image_rows) != 1:
        raise error("R4W1-E0 kernel Image cardinality mismatch")
    _require_receipt(image_rows[0], image_receipt, "kernel result Image", error)
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
        raise error("R4W1-E0 kernel safety mismatch")
    return {
        "schema": result["schema"],
        "patch_sha256": source_delta["patch_sha256"],
        "image": image_receipt,
        "build_result": result_receipt,
        "artifact_contract_schema": artifact.SCHEMA,
        "clean_full_lto_build": True,
        "source_restored": True,
        "verified": True,
    }


def verify_kernel_build(data: bytes, image: bytes) -> dict[str, Any]:
    return verify_kernel_result_common(data, _receipt(image), engine.BuildError)


def classify_image(image: bytes) -> dict[str, Any]:
    if len(image) != engine.KERNEL_SIZE:
        raise engine.BuildError(f"R4W1-E0 Image size mismatch: {len(image)}")
    engine.boot_verify.parse_arm64_header(image)
    counts = {
        "entry_proof_count": image.count(proof.ENTRY_PROOF),
        "userspace_proof_count": image.count(proof.USERSPACE_PROOF),
        "shared_family_count": image.count(proof.PROOF_FAMILY),
    }
    historical = {
        value.decode("ascii"): image.count(value)
        for value in (b"[[S22P1E|", b"[[S22P1D|", b"[[S22R4W1B|", b"[[S22R4W1|")
    }
    if counts != {
        "entry_proof_count": 1,
        "userspace_proof_count": 1,
        "shared_family_count": 2,
    } or any(historical.values()):
        raise engine.BuildError("R4W1-E0 Image marker cardinality mismatch")
    return {
        "size": len(image),
        "sha256": hashlib.sha256(image).hexdigest(),
        **counts,
        "historical_family_counts": historical,
        "verified": True,
    }


def derive_run_manifest(
    *,
    nonce: bytes,
    image: dict[str, Any],
    kernel_result: dict[str, Any],
    base_boot: dict[str, Any],
    vendor_ramdisk: dict[str, Any],
    lz4: dict[str, Any],
    magiskboot: dict[str, Any],
    sources: dict[str, Any],
    tools: dict[str, Any],
) -> tuple[dict[str, Any], bytes, bytes]:
    if nonce != proof.PROBE_ID:
        raise engine.BuildError("R4W1-E0 manifest received a non-probe ID")
    manifest = {
        "schema": RUN_MANIFEST_SCHEMA,
        "target": proof.TARGET,
        "profile": "E0",
        "probe_id": proof.PROBE_ID.hex(),
        "probe_id_preimage": proof.PROBE_ID_PREIMAGE,
        "proof_patch_sha256": proof.PATCH_SHA256,
        "runtime_receipt_sha256": proof.RUNTIME_RECEIPT_SHA256,
        "request_hex": proof.REQUEST.hex(),
        "entry_proof": proof.ENTRY_PROOF.decode("ascii").strip(),
        "userspace_proof": proof.USERSPACE_PROOF.decode("ascii").strip(),
        "observation_contract": {
            "baseline_family_count": 0,
            "post_family_count": 1,
            "accepted_identity": "USERSPACE_CALLBACK_REACHED",
        },
        "inputs": {
            "image": image,
            "kernel_build_result": kernel_result,
            "base_boot": base_boot,
            "vendor_ramdisk": vendor_ramdisk,
            "lz4": lz4,
            "magiskboot": magiskboot,
            "sources": sources,
            "host_tools": tools,
            "runtime_contract": {
                "schema": runtime.SCHEMA,
                "base_schema": BASE_E1.SCHEMA,
                "compile_flags": list(BASE_E1.COMPILE_FLAGS),
                "init": {"size": 66_056, "sha256": proof.E1_INIT_SHA256},
                "child": {
                    "size": 720,
                    "sha256": "9a57b30aa3fb08ee0aab4d045d2805dd36875bb80bcba7b0b6606f619df71639",
                },
            },
            "modules": [
                {"file": name, "runtime": name_runtime, "size": size, "sha256": digest}
                for name, name_runtime, size, digest in BASE_E1.MODULE_SPECS
            ],
        },
    }
    encoded = engine.canonical_json(manifest)
    return manifest, encoded, proof.PROBE_ID


def verify_run_manifest_common(
    data: bytes,
    *,
    image_receipt: dict[str, Any],
    kernel_result_receipt: dict[str, Any],
    fixed_receipts: dict[str, Any],
    source_receipts: dict[str, Any],
    actual_tool_receipts: dict[str, Any],
    error: type[ValueError],
) -> tuple[dict[str, Any], bytes, bytes]:
    try:
        manifest = json.loads(data.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise error("invalid R4W1-E0 run manifest") from exc
    if not isinstance(manifest, dict):
        raise error("R4W1-E0 run manifest is not an object")
    expected_fixed = {
        "base_boot": {
            "size": engine.BOOT_SIZE,
            "sha256": engine.carrier_engine.EXPECTED_BASE_BOOT_SHA256,
        },
        "vendor_ramdisk": {
            "size": engine.carrier_engine.VENDOR_RAMDISK_SIZE,
            "sha256": engine.carrier_engine.VENDOR_RAMDISK_SHA256,
        },
        "lz4": {
            "size": engine.slice_engine.LZ4_SIZE,
            "sha256": engine.slice_engine.LZ4_SHA256,
        },
        "magiskboot": {
            "size": engine.carrier_engine.MAGISKBOOT_SIZE,
            "sha256": engine.carrier_engine.MAGISKBOOT_SHA256,
        },
    }
    for name, expected in expected_fixed.items():
        _require_receipt(fixed_receipts.get(name), expected, f"actual {name}", error)
    if set(source_receipts) != set(BASE_E1.EXPECTED_SOURCE_SHA256):
        raise error("R4W1-E0 source receipt inventory mismatch")
    for name, digest in BASE_E1.EXPECTED_SOURCE_SHA256.items():
        value = source_receipts[name]
        if not isinstance(value, dict) or value.get("sha256") != digest:
            raise error(f"R4W1-E0 source receipt mismatch: {name}")
    expected_tool_names = {
        "aarch64-linux-gnu-gcc",
        "aarch64-linux-gnu-strip",
        "aarch64-linux-gnu-readelf",
        "aarch64-linux-gnu-nm",
        "aarch64-linux-gnu-objdump",
        "gcc",
        "file",
        "qemu-aarch64",
    }
    if set(actual_tool_receipts) != expected_tool_names:
        raise error("R4W1-E0 host-tool receipt inventory mismatch")
    for name, value in actual_tool_receipts.items():
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("resolved_name"), str)
            or not isinstance(value.get("size"), int)
            or value["size"] <= 0
            or not isinstance(value.get("sha256"), str)
            or len(value["sha256"]) != 64
        ):
            raise error(f"R4W1-E0 host-tool receipt malformed: {name}")
    image_pin = {name: image_receipt[name] for name in ("size", "sha256")}
    kernel_result_pin = {
        name: kernel_result_receipt[name] for name in ("size", "sha256")
    }
    image_info = {
        **image_pin,
        "entry_proof_count": 1,
        "userspace_proof_count": 1,
        "shared_family_count": 2,
        "historical_family_counts": {
            "[[S22P1E|": 0,
            "[[S22P1D|": 0,
            "[[S22R4W1B|": 0,
            "[[S22R4W1|": 0,
        },
        "verified": True,
    }
    kernel_info = {
        **kernel_result_pin,
        "schema": "s22plus_fyg8_r4w1e0_build_v1",
        "patch_sha256": proof.PATCH_SHA256,
        "image": image_pin,
        "build_result": kernel_result_pin,
        "artifact_contract_schema": artifact.SCHEMA,
        "clean_full_lto_build": True,
        "source_restored": True,
        "verified": True,
    }
    expected, encoded, run_id = derive_run_manifest(
        nonce=proof.PROBE_ID,
        image=image_info,
        kernel_result=kernel_info,
        base_boot=expected_fixed["base_boot"],
        vendor_ramdisk=expected_fixed["vendor_ramdisk"],
        lz4=expected_fixed["lz4"],
        magiskboot=expected_fixed["magiskboot"],
        sources=source_receipts,
        tools=actual_tool_receipts,
    )
    actual_encoded = engine.canonical_json(manifest)
    if manifest != expected or actual_encoded != encoded:
        raise error("R4W1-E0 run manifest differs from exact reconstruction")
    return manifest, encoded, run_id


def fixed_probe(value: str | None) -> bytes:
    if value is not None:
        raise engine.BuildError("R4W1-E0 does not accept a caller-selected nonce")
    return proof.PROBE_ID


def candidate_run_binding(run_manifest: bytes, run_id: bytes) -> dict[str, Any]:
    if run_id != proof.PROBE_ID:
        raise engine.BuildError("R4W1-E0 candidate run binding changed")
    return {
        "run_id": run_id.hex(),
        "canonical_manifest_size": len(run_manifest),
        "canonical_manifest_sha256": hashlib.sha256(run_manifest).hexdigest(),
        "derivation": "fixed-probe-id-from-r4w1e0-contract",
        "p2_7_model_id_reused": False,
        "clean_baseline_required": True,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--kernel-result", type=Path, default=DEFAULT_KERNEL_RESULT)
    parser.add_argument("--base-boot", type=Path, default=engine.DEFAULT_BASE_BOOT)
    parser.add_argument("--vendor-ramdisk", type=Path, default=engine.DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--lz4", type=Path, default=engine.DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=engine.DEFAULT_MAGISKBOOT)
    args = parser.parse_args(argv)
    args.nonce_hex = None
    return args


@contextmanager
def bind_engine() -> Iterator[None]:
    replacements = {
        "SCHEMA": SCHEMA,
        "RUN_MANIFEST_SCHEMA": RUN_MANIFEST_SCHEMA,
        "VERDICT": VERDICT,
        "RUNG": RUNG,
        "DEFAULT_OUT": DEFAULT_OUT,
        "DEFAULT_IMAGE": DEFAULT_IMAGE,
        "DEFAULT_KERNEL_RESULT": DEFAULT_KERNEL_RESULT,
        "build_artifact": artifact,
        "checkpoint": checkpoint,
        "e1": runtime,
        "verify_kernel_build": verify_kernel_build,
        "classify_image": classify_image,
        "derive_run_manifest": derive_run_manifest,
        "parse_nonce": fixed_probe,
        "candidate_run_binding": candidate_run_binding,
        "parse_args": parse_args,
    }
    previous = {name: getattr(engine, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(engine, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(engine, name, value)


def main(argv: list[str] | None = None) -> int:
    with bind_engine():
        return engine.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
