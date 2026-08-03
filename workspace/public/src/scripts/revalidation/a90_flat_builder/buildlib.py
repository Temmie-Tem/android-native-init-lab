"""Read-only configuration and command construction for the A90 flat builder."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tomllib
from typing import Any, Iterable


SCHEMA = "a90-flat-builder-v1"
HEX_DIGITS = frozenset("0123456789abcdef")
NEWC_HEX_BYTES = frozenset(b"0123456789abcdefABCDEF")
MAX_EXTENDS_DEPTH = 1
VERSION_NAME = re.compile(r"[a-z0-9][a-z0-9._-]*")
TOP_LEVEL_KEYS = frozenset({
    "schema",
    "extends",
    "profile",
    "cycle",
    "decision",
    "candidate_authority",
    "reproducible_mtime",
    "random_seed",
    "boot_partition_max_bytes",
    "inputs",
    "toolchain",
    "init",
    "helper",
    "engine",
    "ramdisk",
    "validation",
    "legacy_bridge",
})


class ManifestError(RuntimeError):
    """The flat manifest or one of its pinned inputs is invalid."""


@dataclass(frozen=True)
class ManifestResolution:
    """Resolved data plus the source file that supplied each leaf value."""

    data: dict[str, Any]
    requested_path: Path
    lineage: tuple[Path, ...]
    lineage_sha256: tuple[str, ...]
    origins: dict[tuple[str, ...], Path]
    effective_sha256: str

    def origin_for(self, *keys: str) -> Path:
        try:
            return self.origins[tuple(keys)]
        except KeyError as exc:
            joined = ".".join(keys)
            raise ManifestError(f"manifest value has no source origin: {joined}") from exc


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


def _effective_sha256(manifest: dict[str, Any]) -> str:
    encoded = json.dumps(
        manifest,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_manifest(path: Path) -> tuple[dict[str, Any], str]:
    require_regular(path, "manifest")
    try:
        raw = path.read_bytes()
        manifest = tomllib.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ManifestError(f"cannot parse manifest {path}: {exc}") from exc
    if manifest.get("schema") != SCHEMA:
        raise ManifestError(f"unsupported schema: {manifest.get('schema')!r}")
    unknown = sorted(set(manifest) - TOP_LEVEL_KEYS)
    if unknown:
        raise ManifestError(f"unknown top-level manifest keys: {unknown}")
    return manifest, hashlib.sha256(raw).hexdigest()


def _leaf_origins(
    value: object,
    source: Path,
    prefix: tuple[str, ...] = (),
) -> dict[tuple[str, ...], Path]:
    if isinstance(value, dict):
        result: dict[tuple[str, ...], Path] = {}
        for key, child in value.items():
            result.update(_leaf_origins(child, source, (*prefix, key)))
        return result
    return {prefix: source}


def _merge_known(
    parent: object,
    overlay: object,
    *,
    path: tuple[str, ...],
    source: Path,
    origins: dict[tuple[str, ...], Path],
) -> object:
    label = ".".join(path)
    if isinstance(parent, dict):
        if not isinstance(overlay, dict):
            raise ManifestError(f"{label} must remain a table")
        unknown = sorted(set(overlay) - set(parent))
        if unknown:
            raise ManifestError(f"{label} contains unknown keys: {unknown}")
        merged = copy.deepcopy(parent)
        for key, value in overlay.items():
            merged[key] = _merge_known(
                parent[key],
                value,
                path=(*path, key),
                source=source,
                origins=origins,
            )
        return merged
    if type(overlay) is not type(parent):
        raise ManifestError(
            f"{label} changes type from {type(parent).__name__} "
            f"to {type(overlay).__name__}"
        )
    origins[path] = source
    return copy.deepcopy(overlay)


def _resolve_manifest(
    path: Path,
    *,
    versions_root: Path,
    stack: tuple[Path, ...],
) -> ManifestResolution:
    if path.is_symlink() or path.parent.is_symlink():
        raise ManifestError(f"manifest path must not use symlinks: {path}")
    resolved_path = path.resolve()
    if resolved_path in stack:
        cycle = " -> ".join(item.parent.name for item in (*stack, resolved_path))
        raise ManifestError(f"manifest extends cycle: {cycle}")
    manifest, manifest_sha256 = _read_manifest(resolved_path)
    extends = manifest.get("extends")
    if extends is None:
        if manifest.get("candidate_authority") is not False:
            raise ManifestError(
                "flat-builder profile must grant no candidate authority"
            )
        data = copy.deepcopy(manifest)
        return ManifestResolution(
            data=data,
            requested_path=resolved_path,
            lineage=(resolved_path,),
            lineage_sha256=(manifest_sha256,),
            origins=_leaf_origins(data, resolved_path),
            effective_sha256=_effective_sha256(data),
        )
    if not isinstance(extends, str) or VERSION_NAME.fullmatch(extends) is None:
        raise ManifestError(f"invalid extends version name: {extends!r}")
    parent_candidate = versions_root / extends / "manifest.toml"
    if parent_candidate.is_symlink() or parent_candidate.parent.is_symlink():
        raise ManifestError(
            f"parent manifest path must not use symlinks: {parent_candidate}"
        )
    parent_path = parent_candidate.resolve()
    current_stack = (*stack, resolved_path)
    if parent_path in current_stack:
        cycle = " -> ".join(
            item.parent.name for item in (*current_stack, parent_path)
        )
        raise ManifestError(f"manifest extends cycle: {cycle}")
    if len(stack) >= MAX_EXTENDS_DEPTH:
        raise ManifestError(
            f"manifest extends depth exceeds {MAX_EXTENDS_DEPTH}"
        )
    try:
        parent_path.relative_to(versions_root.resolve())
    except ValueError as exc:
        raise ManifestError(f"extends escapes versions root: {extends!r}") from exc
    parent = _resolve_manifest(
        parent_candidate,
        versions_root=versions_root,
        stack=current_stack,
    )
    overlay = {
        key: value
        for key, value in manifest.items()
        if key not in {"schema", "extends"}
    }
    unknown = sorted(set(overlay) - set(parent.data))
    if unknown:
        raise ManifestError(f"child manifest contains unknown keys: {unknown}")
    origins = dict(parent.origins)
    data = copy.deepcopy(parent.data)
    for key, value in overlay.items():
        data[key] = _merge_known(
            parent.data[key],
            value,
            path=(key,),
            source=resolved_path,
            origins=origins,
        )
    if data.get("candidate_authority") is not False:
        raise ManifestError("child manifest must grant no candidate authority")
    return ManifestResolution(
        data=data,
        requested_path=resolved_path,
        lineage=(resolved_path, *parent.lineage),
        lineage_sha256=(manifest_sha256, *parent.lineage_sha256),
        origins=origins,
        effective_sha256=_effective_sha256(data),
    )


def resolve_manifest(path: Path) -> ManifestResolution:
    """Resolve one child over one flat sibling manifest directory."""

    requested = path.absolute()
    versions_root = requested.parent.parent.resolve()
    return _resolve_manifest(
        requested,
        versions_root=versions_root,
        stack=(),
    )


def load_manifest(path: Path) -> dict[str, Any]:
    """Compatibility wrapper returning only resolved manifest data."""

    return resolve_manifest(path).data


def revalidate_manifest_lineage(resolution: ManifestResolution) -> None:
    """Fail if any raw manifest changed after the effective snapshot was made."""

    if len(resolution.lineage) != len(resolution.lineage_sha256):
        raise ManifestError("manifest lineage path/hash cardinality mismatch")
    for path, expected in zip(
        resolution.lineage,
        resolution.lineage_sha256,
        strict=True,
    ):
        if path.is_symlink() or path.parent.is_symlink():
            raise ManifestError(f"manifest lineage gained a symlink: {path}")
        require_regular(path, "manifest lineage member")
        actual = sha256_file(path)
        if actual != expected:
            raise ManifestError(
                f"manifest lineage changed: {path}: "
                f"got {actual}, expected {expected}"
            )


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


def validate_component_selection(manifest: dict[str, Any]) -> None:
    """Validate optional build components without inspecting private inputs."""

    engine = manifest.get("engine")
    ramdisk = manifest.get("ramdisk")
    validation = manifest.get("validation")
    if not isinstance(engine, dict) or type(engine.get("enabled")) is not bool:
        raise ManifestError("engine.enabled must be one boolean")
    if not isinstance(ramdisk, dict) or not isinstance(validation, dict):
        raise ManifestError("ramdisk or validation table is absent")
    ramdisk_path = engine.get("ramdisk_path")
    obsolete = ramdisk.get("obsolete_engines")
    required = ramdisk.get("required_entries")
    engine_strings = validation.get("engine_strings")
    if (
        not isinstance(ramdisk_path, str)
        or not ramdisk_path
        or not isinstance(obsolete, list)
        or any(not isinstance(item, str) or not item for item in obsolete)
        or not isinstance(required, list)
        or any(not isinstance(item, str) or not item for item in required)
        or not isinstance(engine_strings, list)
        or any(not isinstance(item, str) or not item for item in engine_strings)
    ):
        raise ManifestError("engine ramdisk selection is malformed")
    if engine["enabled"]:
        if ramdisk_path not in required or not engine_strings:
            raise ManifestError("enabled engine is not required and validated")
        return
    if (
        ramdisk_path not in obsolete
        or ramdisk_path in required
        or engine_strings
    ):
        raise ManifestError("disabled engine is not removed from the ramdisk")


def validate_ramdisk_component_listing(
    manifest: dict[str, Any],
    listing: set[str],
) -> None:
    """Require the packed ramdisk to contain exactly the selected engine set."""

    validate_component_selection(manifest)
    engine_path = manifest["engine"]["ramdisk_path"]
    engine_prefix = "bin/a90_doomgeneric_private_engine_"
    present = sorted(item for item in listing if item.startswith(engine_prefix))
    expected = [engine_path] if manifest["engine"]["enabled"] else []
    if present != expected:
        raise ManifestError(
            "packed ramdisk engine selection mismatch: "
            f"expected={expected!r} present={present!r}"
        )


def newc_archive_listing(data: bytes) -> set[str]:
    """Parse one GNU newc archive without trusting the external cpio tool."""

    header_bytes = 110
    offset = 0
    listing: set[str] = set()
    while True:
        if offset + header_bytes > len(data):
            raise ManifestError("packed ramdisk is truncated before its header")
        header = data[offset:offset + header_bytes]
        if header[:6] != b"070701":
            raise ManifestError("packed ramdisk is not one newc archive")
        encoded_fields = [
            header[index:index + 8]
            for index in range(6, header_bytes, 8)
        ]
        if any(
            len(field) != 8
            or any(byte not in NEWC_HEX_BYTES for byte in field)
            for field in encoded_fields
        ):
            raise ManifestError("packed ramdisk has a malformed newc header")
        fields = [int(field, 16) for field in encoded_fields]
        file_size = fields[6]
        name_size = fields[11]
        if name_size < 2:
            raise ManifestError("packed ramdisk has an invalid member name size")
        offset += header_bytes
        name_end = offset + name_size
        if name_end > len(data):
            raise ManifestError("packed ramdisk is truncated in a member name")
        encoded_name = data[offset:name_end]
        if encoded_name[-1:] != b"\0" or b"\0" in encoded_name[:-1]:
            raise ManifestError("packed ramdisk has a malformed member name")
        try:
            name = encoded_name[:-1].decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ManifestError("packed ramdisk member name is not UTF-8") from exc
        aligned_name_end = (name_end + 3) & ~3
        if (
            aligned_name_end > len(data)
            or any(data[name_end:aligned_name_end])
        ):
            raise ManifestError("packed ramdisk has invalid member-name padding")
        offset = aligned_name_end
        data_end = offset + file_size
        if data_end > len(data):
            raise ManifestError("packed ramdisk is truncated in member data")
        aligned_data_end = (data_end + 3) & ~3
        if (
            aligned_data_end > len(data)
            or any(data[data_end:aligned_data_end])
        ):
            raise ManifestError("packed ramdisk has invalid member-data padding")
        offset = aligned_data_end

        if name == "TRAILER!!!":
            if file_size != 0 or any(data[offset:]):
                raise ManifestError("packed ramdisk has an invalid newc trailer")
            return listing

        normalized = name
        member = PurePosixPath(name)
        canonical = member.as_posix()
        if (
            not normalized
            or member.is_absolute()
            or ".." in member.parts
            or canonical != normalized
            or normalized in listing
        ):
            raise ManifestError(
                f"packed ramdisk has a noncanonical or duplicate member: {name!r}"
            )
        listing.add(normalized)


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
    manifest_source: Path | ManifestResolution,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    if isinstance(manifest_source, ManifestResolution):
        resolution = manifest_source
        manifest_path = resolution.requested_path
    else:
        resolution = resolve_manifest(manifest_source)
        manifest_path = resolution.requested_path
        if resolution.data != manifest:
            raise ManifestError("manifest data does not match its resolved source")
    validate_component_selection(manifest)
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

    result = {
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
        "engine_enabled": manifest["engine"]["enabled"],
    }
    if not manifest["engine"]["enabled"]:
        return result

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
        [*doom_sources, "Makefile.soso"],
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

    materialized: dict[str, Path] = {}
    materialized_sha: dict[str, str] = {}
    source_pins = engine["materialized_sources"]
    for name in ("adapter", "sfx", "sdl_mixer_stub"):
        entry = source_pins[name]
        version_root = (
            resolution.origin_for(
                "engine",
                "materialized_sources",
                name,
                "path",
            ).parent
        )
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
    result.update(
        {
            "doom_root": doom_root,
            "doom_sources": [doom_root / relative for relative in doom_sources],
            "doom_closure_sha256": doom_closure_sha,
            "materialized": materialized,
            "materialized_sha256": materialized_sha,
        }
    )
    return result


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
