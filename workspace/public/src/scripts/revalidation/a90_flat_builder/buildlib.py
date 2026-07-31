"""Read-only configuration and command construction for the A90 flat builder."""

from __future__ import annotations

import hashlib
from pathlib import Path
import tomllib
from typing import Any, Iterable


SCHEMA = "a90-flat-builder-v1"
HEX_DIGITS = frozenset("0123456789abcdef")


class ManifestError(RuntimeError):
    """The flat manifest or one of its pinned inputs is invalid."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(
        char not in HEX_DIGITS for char in value
    ):
        raise ManifestError(f"{label} is not a lowercase SHA256")
    return value


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        manifest = tomllib.load(stream)
    if manifest.get("schema") != SCHEMA:
        raise ManifestError(f"unsupported schema: {manifest.get('schema')!r}")
    if "extends" in manifest:
        raise ManifestError("v3404-effective must be a fully flattened manifest")
    if manifest.get("candidate_authority") is not False:
        raise ManifestError("flat-builder profile must grant no candidate authority")
    return manifest


def resolve_repo_path(repo_root: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ManifestError(f"{label} path is empty")
    candidate = (repo_root / relative).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ManifestError(f"{label} escapes repository: {relative}") from exc
    return candidate


def require_regular(path: Path, label: str) -> Path:
    if not path.is_file() or path.is_symlink():
        raise ManifestError(f"{label} is not one regular file: {path}")
    return path


def require_directory(path: Path, label: str) -> Path:
    if not path.is_dir() or path.is_symlink():
        raise ManifestError(f"{label} is not one directory: {path}")
    return path


def closure_sha256(root: Path, relative_paths: Iterable[str]) -> str:
    digest = hashlib.sha256()
    seen: set[str] = set()
    for relative in sorted(relative_paths):
        if relative in seen:
            raise ManifestError(f"duplicate closure member: {relative}")
        seen.add(relative)
        path = require_regular(root / relative, f"closure member {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _string_list(table: dict[str, Any], key: str) -> list[str]:
    value = table.get(key)
    if not isinstance(value, list) or not value or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise ManifestError(f"{key} must be a nonempty string list")
    if len(value) != len(set(value)):
        raise ManifestError(f"{key} contains duplicates")
    return list(value)


def expanded_closure(
    root: Path,
    explicit: Iterable[str],
    globs: Iterable[str],
) -> list[str]:
    members = set(explicit)
    for pattern in globs:
        if not pattern or Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise ManifestError(f"invalid closure glob: {pattern!r}")
        for path in root.glob(pattern):
            if path.is_file() and not path.is_symlink():
                members.add(path.relative_to(root).as_posix())
    return sorted(members)


def _pin_file(
    repo_root: Path,
    table: dict[str, Any],
    path_key: str,
    sha_key: str,
    label: str,
) -> tuple[Path, str]:
    path = require_regular(
        resolve_repo_path(repo_root, table[path_key], label),
        label,
    )
    expected = _require_sha256(table[sha_key], f"{label} pin")
    actual = sha256_file(path)
    if actual != expected:
        raise ManifestError(f"{label} changed: got {actual}, expected {expected}")
    return path, actual


def validate_inputs(
    repo_root: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    inputs = manifest["inputs"]
    base_boot, base_boot_sha = _pin_file(
        repo_root, inputs, "base_boot", "base_boot_sha256", "base boot"
    )
    accepted_boot, accepted_boot_sha = _pin_file(
        repo_root,
        inputs,
        "accepted_boot",
        "accepted_boot_sha256",
        "accepted historical boot",
    )
    mkbootimg, mkbootimg_sha = _pin_file(
        repo_root, inputs, "mkbootimg", "mkbootimg_sha256", "mkbootimg"
    )
    unpack_bootimg, unpack_bootimg_sha = _pin_file(
        repo_root,
        inputs,
        "unpack_bootimg",
        "unpack_bootimg_sha256",
        "unpack_bootimg",
    )

    init = manifest["init"]
    init_root = require_directory(
        resolve_repo_path(repo_root, init["source_root"], "native-init root"),
        "native-init root",
    )
    init_sources = _string_list(init, "sources")
    for relative in init_sources:
        require_regular(init_root / relative, f"native-init source {relative}")
    init_closure = expanded_closure(
        init_root,
        init_sources,
        _string_list(init, "closure_globs"),
    )
    init_closure_sha = closure_sha256(init_root, init_closure)
    expected_init_closure = _require_sha256(
        init["closure_sha256"], "native-init closure pin"
    )
    if init_closure_sha != expected_init_closure:
        raise ManifestError(
            "native-init closure changed: "
            f"got {init_closure_sha}, expected {expected_init_closure}"
        )

    helper = manifest["helper"]
    helper_source = require_regular(
        init_root / helper["source"], "helper source"
    )
    helper_sha = sha256_file(helper_source)
    expected_helper_sha = _require_sha256(
        helper["source_sha256"], "helper source pin"
    )
    if helper_sha != expected_helper_sha:
        raise ManifestError(
            f"helper source changed: got {helper_sha}, expected {expected_helper_sha}"
        )

    engine = manifest["engine"]
    doom_root = require_directory(
        resolve_repo_path(repo_root, engine["doom_source_root"], "Doom source root"),
        "Doom source root",
    )
    doom_sources = _string_list(engine, "doom_sources")
    for relative in doom_sources:
        require_regular(doom_root / relative, f"Doom source {relative}")
    doom_closure = expanded_closure(
        doom_root,
        [*_string_list(engine, "doom_sources"), "Makefile.soso"],
        _string_list(engine, "doom_closure_globs"),
    )
    doom_closure_sha = closure_sha256(doom_root, doom_closure)
    expected_doom_closure = _require_sha256(
        engine["doom_closure_sha256"], "Doom closure pin"
    )
    if doom_closure_sha != expected_doom_closure:
        raise ManifestError(
            "Doom closure changed: "
            f"got {doom_closure_sha}, expected {expected_doom_closure}"
        )

    version_root = manifest_path.parent
    materialized: dict[str, Path] = {}
    materialized_sha: dict[str, str] = {}
    source_pins = engine["materialized_sources"]
    for name in ("adapter", "sfx", "sdl_mixer_stub"):
        entry = source_pins[name]
        path = require_regular(
            (version_root / entry["path"]).resolve(),
            f"materialized {name}",
        )
        try:
            path.relative_to(version_root.resolve())
        except ValueError as exc:
            raise ManifestError(f"materialized {name} escapes version root") from exc
        expected = _require_sha256(entry["sha256"], f"materialized {name} pin")
        actual = sha256_file(path)
        if actual != expected:
            raise ManifestError(
                f"materialized {name} changed: got {actual}, expected {expected}"
            )
        materialized[name] = path
        materialized_sha[name] = actual

    return {
        "base_boot": base_boot,
        "base_boot_sha256": base_boot_sha,
        "accepted_boot": accepted_boot,
        "accepted_boot_sha256": accepted_boot_sha,
        "mkbootimg": mkbootimg,
        "mkbootimg_sha256": mkbootimg_sha,
        "unpack_bootimg": unpack_bootimg,
        "unpack_bootimg_sha256": unpack_bootimg_sha,
        "init_root": init_root,
        "init_sources": [init_root / relative for relative in init_sources],
        "init_closure_sha256": init_closure_sha,
        "helper_source": helper_source,
        "helper_source_sha256": helper_sha,
        "doom_root": doom_root,
        "doom_sources": [doom_root / relative for relative in doom_sources],
        "doom_closure_sha256": doom_closure_sha,
        "materialized": materialized,
        "materialized_sha256": materialized_sha,
    }


def prefix_map_flags(actual: Path, virtual: str) -> list[str]:
    if not virtual.startswith("/") or ".." in Path(virtual).parts:
        raise ManifestError(f"invalid virtual source prefix: {virtual}")
    return [
        f"-ffile-prefix-map={actual.resolve()}={virtual}",
        f"-fmacro-prefix-map={actual.resolve()}={virtual}",
        f"-fdebug-prefix-map={actual.resolve()}={virtual}",
    ]


def init_flags(manifest: dict[str, Any], inputs: dict[str, Any]) -> list[str]:
    table = manifest["init"]
    flags = _string_list(table, "cflags")
    flags.extend(
        prefix_map_flags(inputs["init_root"], table["virtual_source_root"])
    )
    return flags


def helper_flags(manifest: dict[str, Any], inputs: dict[str, Any]) -> list[str]:
    table = manifest["helper"]
    flags = _string_list(table, "cflags")
    flags.extend(
        prefix_map_flags(inputs["init_root"], table["virtual_source_root"])
    )
    return flags


def engine_flags(
    manifest: dict[str, Any],
    inputs: dict[str, Any],
) -> tuple[list[str], list[str]]:
    table = manifest["engine"]
    common = _string_list(table, "common_cflags")
    doom = common + _string_list(table, "doom_extra_cflags")
    adapter = common + _string_list(table, "adapter_extra_cflags")
    maps = prefix_map_flags(inputs["doom_root"], table["virtual_doom_root"])
    materialized_root = inputs["materialized"]["adapter"].parent
    maps.extend(
        prefix_map_flags(
            materialized_root,
            table["virtual_materialized_root"],
        )
    )
    return doom + maps, adapter + maps
