#!/usr/bin/env python3
"""Check two independent FYG8 R4W1-B Full-LTO reproductions host-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import s22plus_fyg8_r4w1b_build as r4w1b_build  # noqa: E402
import s22plus_fyg8_r4w1b_patch_check as patch_check  # noqa: E402
import s22plus_fyg8_r4w1b_static_audit as static_audit  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1b_repro_check_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
VERDICT = "PASS_R4W1B_CLEAN_REPRODUCIBILITY"
BUILD_SCHEMA = r4w1b_build.SCHEMA
STATIC_SCHEMA = static_audit.SCHEMA
PATCH_SHA256 = patch_check.PATCH_SHA256
MARKER = patch_check.MARKER.encode("ascii")
IMAGE_SIZE = r4w1b_build.STOCK_IMAGE_SIZE
ALIGNED_SIZE = r4w1b_build.FIXED_KERNEL_SLOT_CAPACITY
PATH_CONFIG = "CONFIG_UNUSED_KSYMS_WHITELIST"
REQUIRED_BUILD_ARTIFACTS = (
    "Image",
    ".config",
    "vmlinux.symvers",
    "abi.xml",
    "vmlinux",
    "System.map",
)


class CheckError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise CheckError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CheckError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CheckError(f"JSON root is not an object: {path}")
    return value


def check_build(path: Path) -> dict[str, Any]:
    value = load_json(path)
    source_delta = value.get("source_delta", {})
    kmi_path = value.get("kmi_path_control_runtime", {})
    kernel_debug = value.get("kernel_debug_control_runtime", {})
    vdso_debug = value.get("vdso_debug_control_runtime", {})
    effective_tools = value.get("provenance", {}).get("effective_tools", {})
    outputs = value.get("outputs", [])
    artifact_rows: dict[str, dict[str, Any]] = {}
    duplicate_artifacts: list[str] = []
    if isinstance(outputs, list):
        for row in outputs:
            if not isinstance(row, dict) or row.get("name") not in REQUIRED_BUILD_ARTIFACTS:
                continue
            name = row["name"]
            if name in artifact_rows:
                duplicate_artifacts.append(name)
            artifact_rows[name] = row
    artifacts_verified = (
        not duplicate_artifacts
        and set(artifact_rows) == set(REQUIRED_BUILD_ARTIFACTS)
        and all(
            isinstance(row.get("path"), str)
            and bool(row["path"])
            and isinstance(row.get("sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None
            and isinstance(row.get("size"), int)
            and row["size"] >= 0
            for row in artifact_rows.values()
        )
    )
    gate = {
        "path": str(path),
        "sha256": sha256_file(path),
        "schema": value.get("schema"),
        "target": value.get("target"),
        "work_tree": value.get("work_tree"),
        "returncode": value.get("returncode"),
        "r4w1b_build_pass": value.get("r4w1b_build_pass"),
        "source_overlay_verified": value.get("provenance", {})
        .get("source_overlay", {})
        .get("verified"),
        "patch_sha256": source_delta.get("patch_sha256"),
        "source_delta_verified": source_delta.get("verified"),
        "patched_files": source_delta.get("after"),
        "witness_output_verified": value.get("witness_output_gate", {}).get(
            "verified"
        ),
        "kmi_path_control_verified": (
            kmi_path.get("applied") is True
            and kmi_path.get("restored") is True
            and kmi_path.get("patched_content_unchanged") is True
            and kmi_path.get("restored_sha256") == kmi_path.get("original_sha256")
        ),
        "kernel_debug_control_verified": (
            kernel_debug.get("applied") is True
            and kernel_debug.get("restored") is True
            and kernel_debug.get("patched_content_unchanged") is True
            and kernel_debug.get("restored_sha256")
            == kernel_debug.get("original_sha256")
            and kernel_debug.get("object_map") == "/kernel-out"
        ),
        "vdso_debug_control_verified": (
            vdso_debug.get("applied") is True
            and vdso_debug.get("restored") is True
            and vdso_debug.get("patched_content_unchanged") is True
            and vdso_debug.get("verified") is True
        ),
        "effective_tools_verified": (
            effective_tools.get("verified") is True
            and isinstance(effective_tools.get("tools"), list)
            and bool(effective_tools["tools"])
            and all(row.get("verified") is True for row in effective_tools["tools"])
        ),
        "effective_tool_fingerprint": {
            row.get("name"): {
                "sha256": row.get("sha256"),
                "size": row.get("size"),
            }
            for row in effective_tools.get("tools", [])
            if isinstance(row, dict) and isinstance(row.get("name"), str)
        },
        "artifacts": artifact_rows,
        "duplicate_artifacts": sorted(duplicate_artifacts),
        "artifact_manifest_verified": artifacts_verified,
    }
    gate["verified"] = (
        gate["schema"] == BUILD_SCHEMA
        and gate["target"] == TARGET
        and gate["returncode"] == 0
        and gate["r4w1b_build_pass"] is True
        and gate["source_overlay_verified"] is True
        and gate["patch_sha256"] == PATCH_SHA256
        and gate["source_delta_verified"] is True
        and gate["witness_output_verified"] is True
        and gate["kmi_path_control_verified"] is True
        and gate["kernel_debug_control_verified"] is True
        and gate["vdso_debug_control_verified"] is True
        and gate["effective_tools_verified"] is True
        and gate["artifact_manifest_verified"] is True
        and isinstance(gate["work_tree"], str)
        and bool(gate["work_tree"])
    )
    return gate


def check_artifact_binding(
    build: dict[str, Any], name: str, path: Path
) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CheckError(f"{name} input missing or indirect: {path}")
    row = build.get("artifacts", {}).get(name)
    if not isinstance(row, dict):
        raise CheckError(f"build result has no {name} artifact identity")
    recorded_path = Path(row["path"])
    result = {
        "name": name,
        "input_path": str(path),
        "recorded_path": str(recorded_path),
        "path_match": path.resolve() == recorded_path.resolve(),
        "input_sha256": sha256_file(path),
        "recorded_sha256": row["sha256"],
        "input_size": path.stat().st_size,
        "recorded_size": row["size"],
    }
    result["verified"] = (
        result["path_match"]
        and result["input_sha256"] == result["recorded_sha256"]
        and result["input_size"] == result["recorded_size"]
    )
    return result


def check_distinct_artifact_paths(
    supplied: dict[str, list[Path]],
) -> dict[str, bool]:
    return {
        name: len(paths) == 2 and paths[0].resolve() != paths[1].resolve()
        for name, paths in supplied.items()
    }


def check_static(path: Path) -> dict[str, Any]:
    value = load_json(path)
    final_binary = value.get("gates", {}).get("final_binary", {})
    fips = final_binary.get("elf", {}).get("fips", {})
    gate = {
        "path": str(path),
        "sha256": sha256_file(path),
        "schema": value.get("schema"),
        "target": value.get("target"),
        "verdict": value.get("verdict"),
        "pass": value.get("r4w1b_static_pass"),
        "blockers": value.get("blockers"),
        "final_binary_verified": final_binary.get("verified"),
        "fips_hmac_hex": fips.get("hmac_hex"),
        "fips_hmac_sha256": fips.get("hmac_sha256"),
    }
    gate["verified"] = (
        gate["schema"] == STATIC_SCHEMA
        and gate["target"] == TARGET
        and gate["verdict"] == static_audit.VERDICT
        and gate["pass"] is True
        and gate["blockers"] == []
        and gate["final_binary_verified"] is True
        and isinstance(gate["fips_hmac_hex"], str)
        and re.fullmatch(r"[0-9a-f]{64}", gate["fips_hmac_hex"]) is not None
        and gate["fips_hmac_sha256"]
        == hashlib.sha256(bytes.fromhex(gate["fips_hmac_hex"])).hexdigest()
    )
    return gate


def check_image(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CheckError(f"Image missing or indirect: {path}")
    data = path.read_bytes()
    gate = {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "aligned_size": (len(data) + 4095) & ~4095,
        "marker_count": data.count(MARKER),
        "family_count": data.count(r4w1b_build.R4W1B_MARKER_FAMILY),
        "historical_family_count": data.count(
            r4w1b_build.HISTORICAL_R4W1_MARKER_FAMILY
        ),
    }
    gate["verified"] = (
        gate["size"] == IMAGE_SIZE
        and gate["aligned_size"] == ALIGNED_SIZE
        and gate["marker_count"] == 1
        and gate["family_count"] == 1
        and gate["historical_family_count"] == 0
    )
    return gate


def normalized_config(path: Path) -> tuple[dict[str, str], str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("CONFIG_") and "=" in raw:
            key, value = raw.split("=", 1)
        else:
            match = re.fullmatch(r"# (CONFIG_[A-Za-z0-9_]+) is not set", raw)
            if not match:
                continue
            key, value = match.group(1), "n"
        if key in values:
            raise CheckError(f"duplicate config key: {key}")
        values[key] = "<ABSOLUTE_PATH>" if key == PATH_CONFIG else value
    encoded = json.dumps(values, sort_keys=True, separators=(",", ":")).encode("ascii")
    return values, hashlib.sha256(encoded).hexdigest()


def identity_gate(path_a: Path, path_b: Path) -> dict[str, Any]:
    result = {
        "sha256_a": sha256_file(path_a),
        "sha256_b": sha256_file(path_b),
        "size_a": path_a.stat().st_size,
        "size_b": path_b.stat().st_size,
    }
    result["verified"] = (
        result["sha256_a"] == result["sha256_b"]
        and result["size_a"] == result["size_b"]
    )
    return result


def run_check(
    *,
    build_a: Path,
    build_b: Path,
    static_a: Path,
    static_b: Path,
    image_a: Path,
    image_b: Path,
    config_a: Path,
    config_b: Path,
    symvers_a: Path,
    symvers_b: Path,
    abi_a: Path,
    abi_b: Path,
    vmlinux_a: Path,
    vmlinux_b: Path,
    system_map_a: Path,
    system_map_b: Path,
) -> dict[str, Any]:
    builds = [check_build(build_a), check_build(build_b)]
    statics = [check_static(static_a), check_static(static_b)]
    images = [check_image(image_a), check_image(image_b)]
    if builds[0]["work_tree"] == builds[1]["work_tree"]:
        raise CheckError("A/B build results use the same work tree")
    if builds[0]["patched_files"] != builds[1]["patched_files"]:
        raise CheckError("A/B patched source identities differ")
    toolchain_equal = (
        builds[0]["effective_tool_fingerprint"]
        == builds[1]["effective_tool_fingerprint"]
    )
    supplied = {
        "Image": [image_a, image_b],
        ".config": [config_a, config_b],
        "vmlinux.symvers": [symvers_a, symvers_b],
        "abi.xml": [abi_a, abi_b],
        "vmlinux": [vmlinux_a, vmlinux_b],
        "System.map": [system_map_a, system_map_b],
    }
    artifact_bindings = {
        name: [
            check_artifact_binding(builds[index], name, paths[index])
            for index in range(2)
        ]
        for name, paths in supplied.items()
    }
    distinct_artifact_paths = check_distinct_artifact_paths(supplied)
    configs = [normalized_config(config_a), normalized_config(config_b)]
    config_gate = {
        "normalized_sha256_a": configs[0][1],
        "normalized_sha256_b": configs[1][1],
        "raw_sha256_a": sha256_file(config_a),
        "raw_sha256_b": sha256_file(config_b),
        "witness_a": configs[0][0].get("CONFIG_S22PLUS_FYG8_RETAINED_WITNESS"),
        "witness_b": configs[1][0].get("CONFIG_S22PLUS_FYG8_RETAINED_WITNESS"),
        "fips_a": configs[0][0].get("CONFIG_CRYPTO_FIPS"),
        "fips_b": configs[1][0].get("CONFIG_CRYPTO_FIPS"),
    }
    config_gate["verified"] = (
        configs[0][0] == configs[1][0]
        and config_gate["raw_sha256_a"] == config_gate["raw_sha256_b"]
        and config_gate["witness_a"] == "y"
        and config_gate["witness_b"] == "y"
        and config_gate["fips_a"] == "y"
        and config_gate["fips_b"] == "y"
    )
    symvers_gate = identity_gate(symvers_a, symvers_b)
    abi_gate = identity_gate(abi_a, abi_b)
    vmlinux_gate = identity_gate(vmlinux_a, vmlinux_b)
    system_map_gate = identity_gate(system_map_a, system_map_b)
    fips_gate = {
        "hmac_a": statics[0]["fips_hmac_hex"],
        "hmac_b": statics[1]["fips_hmac_hex"],
        "sha256_a": statics[0]["fips_hmac_sha256"],
        "sha256_b": statics[1]["fips_hmac_sha256"],
    }
    fips_gate["verified"] = (
        fips_gate["hmac_a"] == fips_gate["hmac_b"]
        and fips_gate["sha256_a"] == fips_gate["sha256_b"]
    )
    image_equal = images[0]["sha256"] == images[1]["sha256"]
    blockers: list[str] = []
    if not all(item["verified"] for item in builds):
        blockers.append("one or more build gates failed")
    if not toolchain_equal:
        blockers.append("A/B effective host tool fingerprints differ")
    if not all(
        item["verified"]
        for bindings in artifact_bindings.values()
        for item in bindings
    ):
        blockers.append("one or more artifacts are not bound to their build result")
    if not all(distinct_artifact_paths.values()):
        blockers.append("A/B artifact inputs reuse the same path")
    if not all(item["verified"] for item in statics):
        blockers.append("one or more static audits failed")
    if not all(item["verified"] for item in images) or not image_equal:
        blockers.append("A/B Image identity failed")
    if not config_gate["verified"]:
        blockers.append("normalized A/B config identity failed")
    if not symvers_gate["verified"]:
        blockers.append("A/B vmlinux.symvers identity failed")
    if not abi_gate["verified"]:
        blockers.append("A/B abi.xml identity failed")
    if not vmlinux_gate["verified"]:
        blockers.append("A/B vmlinux identity failed")
    if not system_map_gate["verified"]:
        blockers.append("A/B System.map identity failed")
    if not fips_gate["verified"]:
        blockers.append("A/B regenerated FIPS HMAC identity failed")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT if not blockers else "BLOCKED_R4W1B_REPRODUCIBILITY",
        "builds": builds,
        "effective_tool_fingerprints_equal": toolchain_equal,
        "artifact_bindings": artifact_bindings,
        "distinct_artifact_paths": distinct_artifact_paths,
        "static_audits": statics,
        "images": images,
        "image_byte_identical": image_equal,
        "config": config_gate,
        "symvers": symvers_gate,
        "abi_definition": abi_gate,
        "vmlinux": vmlinux_gate,
        "system_map": system_map_gate,
        "fips_hmac": fips_gate,
        "blockers": blockers,
        "reproducible": not blockers,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "image_packaging": False,
            "flash": False,
            "live_authorized": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "build-a",
        "build-b",
        "static-a",
        "static-b",
        "image-a",
        "image-b",
        "config-a",
        "config-b",
        "symvers-a",
        "symvers-b",
        "abi-a",
        "abi-b",
        "vmlinux-a",
        "vmlinux-b",
        "system-map-a",
        "system-map-b",
        "out",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    result = run_check(
        **{
            name: resolve(root, getattr(args, name))
            for name in (
                "build_a",
                "build_b",
                "static_a",
                "static_b",
                "image_a",
                "image_b",
                "config_a",
                "config_b",
                "symvers_a",
                "symvers_b",
                "abi_a",
                "abi_b",
                "vmlinux_a",
                "vmlinux_b",
                "system_map_a",
                "system_map_b",
            )
        }
    )
    out = resolve(root, args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(
        json.dumps(
            {
                "result": "pass" if result["reproducible"] else "blocked",
                "image_sha256": result["images"][0]["sha256"],
                "blocker_count": len(result["blockers"]),
                "out": str(out),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["reproducible"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CheckError, OSError, KeyError) as exc:
        raise SystemExit(str(exc)) from exc
