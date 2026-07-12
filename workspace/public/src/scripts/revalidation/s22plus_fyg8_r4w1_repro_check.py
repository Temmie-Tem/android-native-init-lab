#!/usr/bin/env python3
"""Check two independent FYG8 R4W1 Full-LTO reproductions host-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_r4w1_repro_check_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
VERDICT = "PASS_R4W1_CLEAN_REPRODUCIBILITY"
BUILD_SCHEMA = "s22plus_fyg8_r4w1_build_v1"
STATIC_SCHEMA = "s22plus_fyg8_r4w1_static_audit_v1"
PATCH_SHA256 = "e66962c9e8cc503f9c5e94265816fdc2e96f4920a2d47387c6f1a4d9bbc6b787"
MARKER = (
    b"\n[[S22R4W1|id=9ed5923b08c5eedbbdb0aaa6f6a5200c|"
    b"phase=RAMDISK_EXEC_ACCEPTED|pid=1|path=/init]]\n"
)
IMAGE_SIZE = 41_490_944
ALIGNED_SIZE = 41_492_480
PATH_CONFIG = "CONFIG_UNUSED_KSYMS_WHITELIST"
REQUIRED_BUILD_ARTIFACTS = ("Image", ".config", "vmlinux.symvers")


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
        "r4w1_build_pass": value.get("r4w1_build_pass"),
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
        "artifacts": artifact_rows,
        "duplicate_artifacts": sorted(duplicate_artifacts),
        "artifact_manifest_verified": artifacts_verified,
    }
    gate["verified"] = (
        gate["schema"] == BUILD_SCHEMA
        and gate["target"] == TARGET
        and gate["returncode"] == 0
        and gate["r4w1_build_pass"] is True
        and gate["source_overlay_verified"] is True
        and gate["patch_sha256"] == PATCH_SHA256
        and gate["source_delta_verified"] is True
        and gate["witness_output_verified"] is True
        and gate["kmi_path_control_verified"] is True
        and gate["kernel_debug_control_verified"] is True
        and gate["vdso_debug_control_verified"] is True
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
    gate = {
        "path": str(path),
        "sha256": sha256_file(path),
        "schema": value.get("schema"),
        "target": value.get("target"),
        "verdict": value.get("verdict"),
        "pass": value.get("r4w1_static_pass"),
        "blockers": value.get("blockers"),
    }
    gate["verified"] = (
        gate["schema"] == STATIC_SCHEMA
        and gate["target"] == TARGET
        and gate["verdict"] == "PASS_R4W1_STATIC_COMPATIBILITY"
        and gate["pass"] is True
        and gate["blockers"] == []
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
    }
    gate["verified"] = (
        gate["size"] == IMAGE_SIZE
        and gate["aligned_size"] == ALIGNED_SIZE
        and gate["marker_count"] == 1
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
) -> dict[str, Any]:
    builds = [check_build(build_a), check_build(build_b)]
    statics = [check_static(static_a), check_static(static_b)]
    images = [check_image(image_a), check_image(image_b)]
    if builds[0]["work_tree"] == builds[1]["work_tree"]:
        raise CheckError("A/B build results use the same work tree")
    if builds[0]["patched_files"] != builds[1]["patched_files"]:
        raise CheckError("A/B patched source identities differ")
    supplied = {
        "Image": [image_a, image_b],
        ".config": [config_a, config_b],
        "vmlinux.symvers": [symvers_a, symvers_b],
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
        "witness_a": configs[0][0].get("CONFIG_S22PLUS_FYG8_RETAINED_WITNESS"),
        "witness_b": configs[1][0].get("CONFIG_S22PLUS_FYG8_RETAINED_WITNESS"),
    }
    config_gate["verified"] = (
        configs[0][0] == configs[1][0]
        and config_gate["witness_a"] == "y"
        and config_gate["witness_b"] == "y"
    )
    symvers_gate = {
        "sha256_a": sha256_file(symvers_a),
        "sha256_b": sha256_file(symvers_b),
    }
    symvers_gate["verified"] = symvers_gate["sha256_a"] == symvers_gate["sha256_b"]
    image_equal = images[0]["sha256"] == images[1]["sha256"]
    blockers: list[str] = []
    if not all(item["verified"] for item in builds):
        blockers.append("one or more build gates failed")
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
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT if not blockers else "BLOCKED_R4W1_REPRODUCIBILITY",
        "builds": builds,
        "artifact_bindings": artifact_bindings,
        "distinct_artifact_paths": distinct_artifact_paths,
        "static_audits": statics,
        "images": images,
        "image_byte_identical": image_equal,
        "config": config_gate,
        "symvers": symvers_gate,
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
