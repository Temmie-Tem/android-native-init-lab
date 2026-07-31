#!/usr/bin/env python3
"""Build the portable V3404 effective profile without importing legacy builders."""

from __future__ import annotations

import argparse
import filecmp
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from a90_flat_builder import buildlib
else:
    from . import buildlib


HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE / "versions/v3404-effective/manifest.toml"
ARTIFACT_NAMES = {
    "boot": "boot.img",
    "ramdisk": "build/ramdisk.cpio",
    "init": "build/init",
    "helper": "build/helper",
    "engine": "build/engine",
}


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL_A90.md").is_file():
            return parent
    raise RuntimeError("could not locate repository root")


def run_checked(
    command: list[object],
    *,
    cwd: Path | None = None,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    argv = [str(item) for item in command]
    print("+ " + shlex.join(argv), flush=True)
    result = subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"command failed rc={result.returncode}: {shlex.join(argv)}\n"
            f"stdout:\n{stdout}\nstderr:\n{stderr}"
        )
    return result


def first_version_line(command: str) -> str:
    result = run_checked([command, "--version"])
    return result.stdout.decode("utf-8", errors="replace").splitlines()[0]


def validate_toolchain(manifest: dict[str, Any]) -> dict[str, str]:
    toolchain = manifest["toolchain"]
    versions = {
        "gcc": first_version_line(toolchain["cc"]),
        "strip": first_version_line(toolchain["strip"]),
        "cpio": first_version_line(toolchain["cpio"]),
        "python": sys.version.splitlines()[0],
    }
    expected = {
        "gcc": toolchain["gcc_version"],
        "strip": toolchain["strip_version"],
        "cpio": toolchain["cpio_version"],
    }
    for name, value in expected.items():
        if versions[name] != value:
            raise RuntimeError(
                f"{name} version changed: got {versions[name]!r}, expected {value!r}"
            )
    return versions


def output_root(repo: Path, requested: Path) -> Path:
    resolved = requested.resolve()
    private_outputs = (repo / "workspace/private/outputs").resolve()
    try:
        relative = resolved.relative_to(private_outputs)
    except ValueError as exc:
        raise RuntimeError(
            f"output must stay below {private_outputs}: {resolved}"
        ) from exc
    if not relative.parts:
        raise RuntimeError("output cannot be the private outputs root")
    if resolved.exists() or resolved.is_symlink():
        raise RuntimeError(f"output must be absent: {resolved}")
    return resolved


def compile_objects(
    *,
    cc: str,
    sources: list[Path],
    object_dir: Path,
    common_flags: list[str],
    include_dirs: list[Path],
    seed: str,
) -> list[Path]:
    object_dir.mkdir(parents=True, mode=0o700)
    objects: list[Path] = []
    for index, source in enumerate(sources):
        output = object_dir / f"{index:03d}_{source.stem}.o"
        command: list[object] = [
            cc,
            *common_flags,
            f"-frandom-seed={seed}-{index:03d}-{source.stem}",
            *(f"-I{path}" for path in include_dirs),
            "-c",
            source,
            "-o",
            output,
        ]
        run_checked(command)
        objects.append(output)
    return objects


def strip_binary(strip: str, path: Path) -> None:
    run_checked([strip, path])
    path.chmod(0o600)


def verify_static(readelf: str, path: Path) -> None:
    dynamic = run_checked([readelf, "-d", path])
    dynamic_text = (
        dynamic.stdout + dynamic.stderr
    ).decode("utf-8", errors="replace")
    if "There is no dynamic section" not in dynamic_text:
        raise RuntimeError(f"dynamic section found in {path}")
    program_headers = run_checked([readelf, "-l", path])
    if b"INTERP" in program_headers.stdout:
        raise RuntimeError(f"INTERP segment found in {path}")


def build_init(
    manifest: dict[str, Any],
    inputs: dict[str, Any],
    output: Path,
    object_dir: Path,
) -> None:
    toolchain = manifest["toolchain"]
    flags = buildlib.init_flags(manifest, inputs)
    objects = compile_objects(
        cc=toolchain["cc"],
        sources=inputs["init_sources"],
        object_dir=object_dir,
        common_flags=flags,
        include_dirs=[],
        seed=manifest["random_seed"] + "-init",
    )
    run_checked([
        toolchain["cc"],
        *flags,
        f"-frandom-seed={manifest['random_seed']}-init-link",
        "-o",
        output,
        *objects,
    ])
    strip_binary(toolchain["strip"], output)
    verify_static(toolchain["readelf"], output)


def build_helper(
    manifest: dict[str, Any],
    inputs: dict[str, Any],
    output: Path,
) -> None:
    toolchain = manifest["toolchain"]
    flags = buildlib.helper_flags(manifest, inputs)
    run_checked([
        toolchain["cc"],
        *flags,
        f"-frandom-seed={manifest['random_seed']}-helper",
        "-o",
        output,
        inputs["helper_source"],
    ])
    strip_binary(toolchain["strip"], output)
    verify_static(toolchain["readelf"], output)


def build_engine(
    manifest: dict[str, Any],
    inputs: dict[str, Any],
    output: Path,
    object_dir: Path,
) -> None:
    toolchain = manifest["toolchain"]
    doom_flags, adapter_flags = buildlib.engine_flags(manifest, inputs)
    materialized_root = inputs["materialized"]["adapter"].parent
    objects = compile_objects(
        cc=toolchain["cc"],
        sources=[
            *inputs["doom_sources"],
            inputs["materialized"]["sfx"],
        ],
        object_dir=object_dir,
        common_flags=doom_flags,
        include_dirs=[materialized_root, inputs["doom_root"]],
        seed=manifest["random_seed"] + "-engine",
    )
    adapter_objects = compile_objects(
        cc=toolchain["cc"],
        sources=[inputs["materialized"]["adapter"]],
        object_dir=object_dir / "adapter",
        common_flags=adapter_flags,
        include_dirs=[inputs["doom_root"]],
        seed=manifest["random_seed"] + "-adapter",
    )
    run_checked([
        toolchain["cc"],
        *manifest["engine"]["link_flags"],
        *objects,
        *adapter_objects,
        "-lm",
        "-o",
        output,
    ])
    strip_binary(toolchain["strip"], output)
    verify_static(toolchain["readelf"], output)


def set_reproducible_mtime(root: Path, timestamp: int) -> None:
    paths = sorted(root.rglob("*"), key=lambda item: item.as_posix(), reverse=True)
    for path in paths:
        os.utime(path, (timestamp, timestamp), follow_symlinks=False)
    os.utime(root, (timestamp, timestamp), follow_symlinks=False)


def cpio_listing(root: Path) -> list[str]:
    return [
        ".",
        *sorted(
            "./" + path.relative_to(root).as_posix()
            for path in root.rglob("*")
        ),
    ]


def safe_ramdisk_path(root: Path, relative: str, label: str) -> Path:
    requested = Path(relative)
    if requested.is_absolute() or ".." in requested.parts or not requested.parts:
        raise RuntimeError(f"unsafe {label} path: {relative!r}")
    path = root / requested
    path.relative_to(root)
    return path


def pack_ramdisk(manifest: dict[str, Any], root: Path, output: Path) -> None:
    listing = cpio_listing(root)
    input_bytes = ("\n".join(listing) + "\n").encode("utf-8")
    result = run_checked(
        [
            manifest["toolchain"]["cpio"],
            "--reproducible",
            "-o",
            "-H",
            "newc",
        ],
        cwd=root,
        input_bytes=input_bytes,
    )
    output.write_bytes(result.stdout)
    output.chmod(0o600)


def overlay_ramdisk(
    repo: Path,
    manifest: dict[str, Any],
    inputs: dict[str, Any],
    output_dir: Path,
    init: Path,
    helper: Path,
    engine: Path,
) -> tuple[Path, Path]:
    ramdisk_cpio = output_dir / "ramdisk.cpio"
    boot_image = output_dir.parent / "boot.img"
    with tempfile.TemporaryDirectory(
        prefix="a90-flat-overlay-",
        dir=output_dir,
    ) as temp_name:
        temp = Path(temp_name)
        unpack = temp / "unpack"
        ramdisk = temp / "ramdisk"
        unpack.mkdir()
        ramdisk.mkdir()
        unpacked = run_checked([
            sys.executable,
            inputs["unpack_bootimg"],
            "--boot_img",
            inputs["base_boot"],
            "--out",
            unpack,
            "--format=mkbootimg",
        ])
        mkboot_args = shlex.split(
            unpacked.stdout.decode("utf-8", errors="strict")
        )
        with (unpack / "ramdisk").open("rb") as stream:
            result = subprocess.run(
                [
                    manifest["toolchain"]["cpio"],
                    "-idm",
                    "--no-absolute-filenames",
                ],
                cwd=ramdisk,
                stdin=stream,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        if result.returncode:
            raise RuntimeError(
                "ramdisk extraction failed: "
                + result.stderr.decode("utf-8", errors="replace")
            )

        shutil.copy2(init, ramdisk / "init")
        (ramdisk / "init").chmod(0o755)
        helper_path = safe_ramdisk_path(
            ramdisk,
            manifest["ramdisk"]["helper_path"],
            "helper",
        )
        helper_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(helper, helper_path)
        helper_path.chmod(0o755)
        for relative in manifest["ramdisk"]["obsolete_engines"]:
            obsolete = safe_ramdisk_path(ramdisk, relative, "obsolete engine")
            obsolete.unlink(missing_ok=True)
        engine_path = safe_ramdisk_path(
            ramdisk,
            manifest["engine"]["ramdisk_path"],
            "engine",
        )
        engine_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(engine, engine_path)
        engine_path.chmod(0o755)

        set_reproducible_mtime(ramdisk, int(manifest["reproducible_mtime"]))
        pack_ramdisk(manifest, ramdisk, ramdisk_cpio)
        listing = {
            item.removeprefix("./") for item in cpio_listing(ramdisk)
        }
        missing = sorted(set(manifest["ramdisk"]["required_entries"]) - listing)
        if missing:
            raise RuntimeError(f"ramdisk required entries missing: {missing}")

        for index, item in enumerate(mkboot_args):
            if item == "--ramdisk" and index + 1 < len(mkboot_args):
                mkboot_args[index + 1] = str(ramdisk_cpio)
                break
        else:
            raise RuntimeError("base boot mkbootimg args omitted --ramdisk")
        run_checked([
            sys.executable,
            inputs["mkbootimg"],
            *mkboot_args,
            "--output",
            boot_image,
        ])
        boot_image.chmod(0o600)

    if boot_image.stat().st_size > int(manifest["boot_partition_max_bytes"]):
        raise RuntimeError(
            f"boot exceeds declared maximum: {boot_image.stat().st_size}"
        )
    return ramdisk_cpio, boot_image


def require_markers(path: Path, markers: list[str], label: str) -> None:
    data = path.read_bytes()
    missing = [marker for marker in markers if marker.encode("utf-8") not in data]
    if missing:
        raise RuntimeError(f"{label} markers missing: {missing}")


def artifact_info(root: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for name, relative in ARTIFACT_NAMES.items():
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"missing {name}: {path}")
        result[name] = {
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": buildlib.sha256_file(path),
        }
    return result


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def build_one(
    repo: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    inputs: dict[str, Any],
    versions: dict[str, str],
    root: Path,
) -> dict[str, Any]:
    if root.exists() or root.is_symlink():
        raise RuntimeError(f"single build output must be absent: {root}")
    build_dir = root / "build"
    build_dir.mkdir(parents=True, mode=0o700)
    init = build_dir / "init"
    helper = build_dir / "helper"
    engine = build_dir / "engine"
    build_init(manifest, inputs, init, build_dir / "obj/init")
    build_helper(manifest, inputs, helper)
    build_engine(manifest, inputs, engine, build_dir / "obj/engine")
    overlay_ramdisk(repo, manifest, inputs, build_dir, init, helper, engine)

    validation = manifest["validation"]
    require_markers(init, validation["init_strings"], "init")
    require_markers(helper, validation["helper_strings"], "helper")
    require_markers(engine, validation["engine_strings"], "engine")
    artifacts = artifact_info(root)
    receipt = {
        "schema": "a90-flat-builder-v1-build-receipt",
        "profile": manifest["profile"],
        "candidate_authority": False,
        "manifest": str(manifest_path.relative_to(repo)),
        "manifest_sha256": buildlib.sha256_file(manifest_path),
        "inputs": {
            key: value
            for key, value in inputs.items()
            if key.endswith("_sha256")
        },
        "toolchain": versions,
        "artifacts": artifacts,
        "legacy_bridge_reference": manifest["legacy_bridge"],
    }
    write_json(root / "receipt.json", receipt)
    return receipt


def audit(
    repo: Path,
    manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    manifest = buildlib.load_manifest(manifest_path)
    inputs = buildlib.validate_inputs(repo, manifest_path, manifest)
    versions = validate_toolchain(manifest)
    return manifest, inputs, versions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    outputs = parser.add_mutually_exclusive_group()
    outputs.add_argument("--out-dir", type=Path)
    outputs.add_argument("--ab-root", type=Path)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    os.environ.update({"LC_ALL": "C", "LANG": "C", "TZ": "UTC"})
    repo = repo_root()
    manifest_path = args.manifest.resolve()
    manifest, inputs, versions = audit(repo, manifest_path)
    audit_result = {
        "schema": buildlib.SCHEMA,
        "profile": manifest["profile"],
        "candidate_authority": False,
        "manifest_sha256": buildlib.sha256_file(manifest_path),
        "input_pins": {
            key: value
            for key, value in inputs.items()
            if key.endswith("_sha256")
        },
        "toolchain": versions,
    }
    if args.audit_only:
        print(json.dumps(audit_result, indent=2, sort_keys=True))
        return 0
    if args.out_dir is None and args.ab_root is None:
        parser.error("one of --out-dir, --ab-root, or --audit-only is required")

    requested = args.out_dir or args.ab_root
    assert requested is not None
    root = output_root(repo, requested)
    accepted_before = buildlib.sha256_file(inputs["accepted_boot"])
    if args.out_dir is not None:
        receipt = build_one(
            repo,
            manifest_path,
            manifest,
            inputs,
            versions,
            root,
        )
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        root.mkdir(parents=True, mode=0o700)
        a_receipt = build_one(
            repo,
            manifest_path,
            manifest,
            inputs,
            versions,
            root / "A",
        )
        b_receipt = build_one(
            repo,
            manifest_path,
            manifest,
            inputs,
            versions,
            root / "B",
        )
        byte_identical = all(
            filecmp.cmp(
                root / "A" / relative,
                root / "B" / relative,
                shallow=False,
            )
            for relative in ARTIFACT_NAMES.values()
        )
        if a_receipt["artifacts"] != b_receipt["artifacts"]:
            byte_identical = False
        ab_receipt = {
            **audit_result,
            "schema": "a90-flat-builder-v1-ab-receipt",
            "artifacts": a_receipt["artifacts"],
            "byte_identical": byte_identical,
            "accepted_boot_unchanged": (
                buildlib.sha256_file(inputs["accepted_boot"]) == accepted_before
            ),
            "legacy_bridge_reference": manifest["legacy_bridge"],
        }
        write_json(root / "ab-receipt.json", ab_receipt)
        print(json.dumps(ab_receipt, indent=2, sort_keys=True))
        if not byte_identical or not ab_receipt["accepted_boot_unchanged"]:
            return 1
    if buildlib.sha256_file(inputs["accepted_boot"]) != accepted_before:
        raise RuntimeError("accepted historical boot changed during flat build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
