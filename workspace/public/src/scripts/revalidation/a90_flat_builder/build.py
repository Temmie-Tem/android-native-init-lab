#!/usr/bin/env python3
"""Build the portable V3404 effective profile without importing legacy builders."""

from __future__ import annotations

import argparse
import base64
import binascii
import filecmp
import hashlib
import json
import os
from pathlib import Path
import re
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
BUILDER_SOURCES = {
    "flat_builder": HERE / "build.py",
    "flat_builder_library": HERE / "buildlib.py",
}

AUTO_HANDOFF_COMMON_VALUE_MACROS = (
    "INIT_VERSION",
    "INIT_BUILD",
    "A90_AUTO_HANDOFF_ENABLE_PATH",
    "A90_AUTO_HANDOFF_LATCH_PATH",
)
AUTO_HANDOFF_IMAGE_VALUE_MACROS = (
    "A90_AUTO_HANDOFF_IMAGE",
    "A90_AUTO_HANDOFF_IMAGE_SHA256",
)
AUTO_HANDOFF_USERDATA_ENABLE = "A90_AUTO_HANDOFF_USERDATA_ROOT_V1"
AUTO_HANDOFF_USERDATA_DYNAMIC_DEVT_ENABLE = (
    "A90_AUTO_HANDOFF_USERDATA_DYNAMIC_DEVT"
)
AUTO_HANDOFF_USERDATA_STABLE_VALUE_MACROS = (
    "A90_AUTO_HANDOFF_USERDATA_DEVNAME",
    "A90_AUTO_HANDOFF_USERDATA_SECTORS",
    "A90_AUTO_HANDOFF_USERDATA_LABEL",
    "A90_AUTO_HANDOFF_USERDATA_MARKER",
    "A90_AUTO_HANDOFF_USERDATA_UUID",
    "A90_AUTO_HANDOFF_USERDATA_CONTENT_MANIFEST_SHA256",
    "A90_AUTO_HANDOFF_USERDATA_CONTENT_MANIFEST_PATH",
    "A90_AUTO_HANDOFF_USERDATA_CONTENT_MANIFEST_FILE_SHA256",
)
AUTO_HANDOFF_USERDATA_LEGACY_DEVT_MACRO = "A90_AUTO_HANDOFF_USERDATA_DEV"
AUTO_HANDOFF_USERDATA_DYNAMIC_DEVT_POLICY_MACRO = (
    "A90_AUTO_HANDOFF_USERDATA_DEVT_POLICY"
)
AUTO_HANDOFF_USERDATA_VALUE_MACROS = (
    *AUTO_HANDOFF_USERDATA_STABLE_VALUE_MACROS,
    AUTO_HANDOFF_USERDATA_LEGACY_DEVT_MACRO,
    AUTO_HANDOFF_USERDATA_DYNAMIC_DEVT_POLICY_MACRO,
)
AUTO_HANDOFF_RECEIPT_MACRO = "A90_D3_SOURCE_RECEIPT_PATH"
H17_OBSERVER_AUTH_ENABLE = "A90_UFS_OBSERVER_AUTH_OVERLAY_V1"
H17_FIRSTBOOT_OVERLAY_ENABLE = "A90_UFS_FIRSTBOOT_OVERLAY_V1"
H17_PERSISTENT_HUD_ENABLE = "A90_UFS_PERSISTENT_NATIVE_HUD_V1"
H21_DELAYED_HUD_DRM_ENABLE = "A90_UFS_PERSISTENT_NATIVE_HUD_DELAYED_DRM_V1"
H22_PRESERVED_DEV_DIR_ENABLE = (
    "A90_UFS_PERSISTENT_NATIVE_HUD_PRESERVED_DEV_DIR_V1"
)
H23_PRIVATE_CARD_ROOT_ENABLE = (
    "A90_UFS_PERSISTENT_NATIVE_HUD_PRIVATE_CARD_ROOT_V1"
)
H17_OBSERVER_AUTH_RAMDISK_PATH = "a90/h17/authorized_keys"
H17_FIRSTBOOT_RAMDISK_PATH = "a90/h17/firstboot"
H17_FIRSTBOOT_SOURCE = Path(
    "workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh"
)
USERDATA_RUNTIME_SOURCE = Path("workspace/public/src/native-init/a90_server_distro.c")


def h17_runtime_features(manifest: dict[str, Any]) -> tuple[bool, bool, bool]:
    """Return observer-auth, firstboot-overlay, and persistent-HUD modes."""

    cflags = manifest["init"]["cflags"]
    auth = _macro_directives(cflags, H17_OBSERVER_AUTH_ENABLE)
    firstboot = _macro_directives(cflags, H17_FIRSTBOOT_OVERLAY_ENABLE)
    hud = _macro_directives(cflags, H17_PERSISTENT_HUD_ENABLE)
    valid_auth = [f"-D{H17_OBSERVER_AUTH_ENABLE}=1"]
    valid_firstboot = [
        f"-D{H17_FIRSTBOOT_OVERLAY_ENABLE}=0",
        f"-D{H17_FIRSTBOOT_OVERLAY_ENABLE}=1",
    ]
    valid_hud = [f"-D{H17_PERSISTENT_HUD_ENABLE}=1"]
    if (
        auth not in ([], valid_auth)
        or firstboot not in ([], [valid_firstboot[0]], [valid_firstboot[1]])
        or hud not in ([], valid_hud)
    ):
        raise RuntimeError("H17 runtime feature macro is duplicated or conflicting")
    auth_enabled = bool(auth)
    hud_enabled = bool(hud)
    firstboot_enabled = (
        hud_enabled
        if not firstboot
        else firstboot == [f"-D{H17_FIRSTBOOT_OVERLAY_ENABLE}=1"]
    )
    if (firstboot_enabled or hud_enabled) and not auth_enabled:
        raise RuntimeError("H17 firstboot/native HUD requires observer-auth")
    if firstboot_enabled and not hud_enabled:
        raise RuntimeError("H17 firstboot overlay requires persistent native HUD")
    return auth_enabled, firstboot_enabled, hud_enabled


def h17_private_runtime_mode(manifest: dict[str, Any]) -> bool:
    """Return whether the private observer-auth overlay is enabled."""

    auth, _, _ = h17_runtime_features(manifest)
    return auth


def h17_firstboot_overlay_mode(manifest: dict[str, Any]) -> bool:
    """Return whether the boot firstboot file bind is enabled."""

    _, firstboot, _ = h17_runtime_features(manifest)
    return firstboot


def h17_persistent_hud_mode(manifest: dict[str, Any]) -> bool:
    """Return whether the boot firstboot overlay and native HUD are enabled."""

    _, _, hud = h17_runtime_features(manifest)
    return hud


def h21_delayed_hud_drm_mode(manifest: dict[str, Any]) -> bool:
    """Return whether HUD DRM acquisition is deferred until the UFS intent."""

    cflags = manifest["init"]["cflags"]
    directives = _macro_directives(cflags, H21_DELAYED_HUD_DRM_ENABLE)
    if directives not in ([], [f"-D{H21_DELAYED_HUD_DRM_ENABLE}=1"]):
        raise RuntimeError("H21 delayed HUD DRM macro is duplicated or conflicting")
    enabled = bool(directives)
    if enabled:
        auth, firstboot, hud = h17_runtime_features(manifest)
        if not auth or firstboot or not hud:
            raise RuntimeError(
                "H21 delayed HUD DRM requires auth and HUD without firstboot overlay"
            )
    return enabled


def h22_preserved_dev_dir_mode(manifest: dict[str, Any]) -> bool:
    """Return whether the delayed HUD keeps an exact pre-handoff /dev dir FD."""

    cflags = manifest["init"]["cflags"]
    directives = _macro_directives(cflags, H22_PRESERVED_DEV_DIR_ENABLE)
    if directives not in ([], [f"-D{H22_PRESERVED_DEV_DIR_ENABLE}=1"]):
        raise RuntimeError("H22 preserved /dev directory macro is duplicated or conflicting")
    enabled = bool(directives)
    if enabled and not h21_delayed_hud_drm_mode(manifest):
        raise RuntimeError("H22 preserved /dev directory requires delayed HUD DRM")
    return enabled


def h23_private_card_root_mode(manifest: dict[str, Any]) -> bool:
    """Return whether the HUD pivots into the exact card0-only private root."""

    cflags = manifest["init"]["cflags"]
    directives = _macro_directives(cflags, H23_PRIVATE_CARD_ROOT_ENABLE)
    if directives not in ([], [f"-D{H23_PRIVATE_CARD_ROOT_ENABLE}=1"]):
        raise RuntimeError("H23 private card root macro is duplicated or conflicting")
    enabled = bool(directives)
    if enabled and (
        not h21_delayed_hud_drm_mode(manifest) or
        h22_preserved_dev_dir_mode(manifest)
    ):
        raise RuntimeError(
            "H23 private card root requires delayed HUD DRM without preserved dev FD"
        )
    return enabled


def validate_observer_authorized_key(
    repo: Path,
    manifest: dict[str, Any],
    requested: Path | None,
) -> dict[str, object] | None:
    """Bind one private Ed25519 public key without exposing its bytes."""

    enabled = h17_private_runtime_mode(manifest)
    if not enabled:
        if requested is not None:
            raise RuntimeError("observer authorized key supplied to a non-H17 profile")
        return None
    if requested is None:
        raise RuntimeError("H17 profile requires --observer-authorized-key")
    private_root = (repo / "workspace/private").resolve()
    path = requested.resolve(strict=True)
    try:
        path.relative_to(private_root)
    except ValueError as exc:
        raise RuntimeError("observer authorized key must stay under workspace/private") from exc
    if requested.is_symlink() or path.is_symlink() or not path.is_file():
        raise RuntimeError("observer authorized key must be one regular non-symlink file")
    stat_result = path.stat()
    if stat_result.st_nlink != 1 or not 64 <= stat_result.st_size <= 512:
        raise RuntimeError("observer authorized key metadata is outside the fixed bounds")
    data = path.read_bytes()
    if data.count(b"\n") != 1 or not data.endswith(b"\n") or b"\r" in data:
        raise RuntimeError("observer authorized key must be exactly one LF-terminated line")
    match = re.fullmatch(
        rb"ssh-ed25519 ([A-Za-z0-9+/]+={0,2})(?: ([ -~]{0,128}))?\n",
        data,
    )
    if match is None:
        raise RuntimeError("observer authorized key is not one bounded ssh-ed25519 key")
    try:
        blob = base64.b64decode(match.group(1), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RuntimeError("observer authorized key base64 is invalid") from exc
    if (
        len(blob) != 51
        or blob[:4] != b"\x00\x00\x00\x0b"
        or blob[4:15] != b"ssh-ed25519"
        or blob[15:19] != b"\x00\x00\x00\x20"
    ):
        raise RuntimeError("observer authorized key blob is not canonical Ed25519")
    return {
        "path": path,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _userdata_runtime_records(repo: Path) -> list[dict[str, object]]:
    """Parse the compiled H14 table so its semantic hash is not a mere tag."""

    source_path = (repo / USERDATA_RUNTIME_SOURCE).resolve(strict=True)
    source = source_path.read_text(encoding="utf-8")
    start_marker = (
        "static const struct d4_ro_content_identity d4_h14_content[] = {"
    )
    try:
        start = source.index(start_marker) + len(start_marker)
        end = source.index("\n};", start)
    except ValueError as exc:
        raise RuntimeError("H14 compiled userdata table is absent") from exc
    body = source[start:end]
    entry = re.compile(
        r'''\{\s*"(?P<leaf>[^"\\\r\n]+)",\s*
            (?P<kind>D4_RO_CONTENT_(?:REGULAR|SYMLINK)),\s*
            (?P<mode>0[0-7]{3}),\s*(?P<uid>[0-9]+),\s*
            (?P<gid>[0-9]+),\s*(?P<size>[0-9]+),\s*
            "(?P<sha>[0-9a-f]{64})",\s*
            (?P<link>NULL|"[^"\\\r\n]+")\s*\}''',
        re.VERBOSE,
    )
    records: list[dict[str, object]] = []
    cursor = 0
    for match in entry.finditer(body):
        if body[cursor:match.start()].strip(" \t\r\n,"):
            raise RuntimeError("H14 compiled userdata table has unparsed content")
        link_token = match.group("link")
        record: dict[str, object] = {
            "path": "/" + match.group("leaf"),
            "kind": (
                "file"
                if match.group("kind") == "D4_RO_CONTENT_REGULAR"
                else "symlink"
            ),
            "mode": match.group("mode"),
            "uid": int(match.group("uid"), 10),
            "gid": int(match.group("gid"), 10),
            "size": int(match.group("size"), 10),
            "sha256": match.group("sha"),
        }
        if link_token != "NULL":
            record["link_target"] = link_token[1:-1]
        records.append(record)
        cursor = match.end()
    if body[cursor:].strip(" \t\r\n,") or len(records) != 19:
        raise RuntimeError("H14 compiled userdata table is not exactly 19 records")
    return records


def _macro_directives(cflags: list[str], macro: str) -> list[str]:
    """Return every compiler directive that can define or undefine macro."""

    pattern = re.compile(rf"^(?:-D{re.escape(macro)}(?:=.*)?|-U{re.escape(macro)})$")
    return [flag for flag in cflags if pattern.fullmatch(flag)]


def _quoted_macro_value(cflags: list[str], macro: str) -> str:
    directives = _macro_directives(cflags, macro)
    pattern = re.compile(rf'^-D{re.escape(macro)}="([^"\r\n]+)"$')
    matches = [
        match.group(1)
        for flag in directives
        if (match := pattern.fullmatch(flag))
    ]
    if len(directives) != 1 or len(matches) != 1:
        raise RuntimeError(
            f"auto-handoff macro is missing, duplicated, or conflicting: {macro}"
        )
    return matches[0]


def _userdata_content_binding(values: dict[str, str]) -> dict[str, str]:
    relative = values["A90_AUTO_HANDOFF_USERDATA_CONTENT_MANIFEST_PATH"]
    file_sha256 = values[
        "A90_AUTO_HANDOFF_USERDATA_CONTENT_MANIFEST_FILE_SHA256"
    ]
    content_sha256 = values["A90_AUTO_HANDOFF_USERDATA_CONTENT_MANIFEST_SHA256"]
    filesystem_uuid = values["A90_AUTO_HANDOFF_USERDATA_UUID"]
    if (
        not isinstance(relative, str)
        or not relative.startswith("workspace/public/")
        or ".." in Path(relative).parts
        or not isinstance(file_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", file_sha256) is None
        or not isinstance(content_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", content_sha256) is None
        or not isinstance(filesystem_uuid, str)
        or re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            filesystem_uuid,
        )
        is None
    ):
        raise RuntimeError("auto-handoff userdata content tuple is malformed")
    repo = repo_root().resolve()
    path = (repo / relative).resolve()
    try:
        path.relative_to(repo)
    except ValueError as exc:
        raise RuntimeError("auto-handoff userdata content manifest escapes repo") from exc
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("auto-handoff userdata content manifest is not regular")
    if buildlib.sha256_file(path) != file_sha256:
        raise RuntimeError("auto-handoff userdata content manifest file changed")
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("auto-handoff userdata content manifest is invalid") from exc
    encoded = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    filesystem = content.get("filesystem") if isinstance(content, dict) else None
    if (
        hashlib.sha256(encoded).hexdigest() != content_sha256
        or not isinstance(filesystem, dict)
        or filesystem
        != {
            "type": "ext4",
            "uuid": filesystem_uuid,
            "label": "A90D4ROOT",
            "marker": "userdata=appliance-root",
        }
        or content.get("schema") != "a90-h14-ufs-content-manifest-v1"
        or not isinstance(content.get("files"), list)
        or len(content["files"]) != 19
        or content["files"] != _userdata_runtime_records(repo)
    ):
        raise RuntimeError("auto-handoff userdata content manifest semantics changed")
    return {
        "userdata_uuid": filesystem_uuid,
        "userdata_content_manifest": relative,
        "userdata_content_manifest_file_sha256": file_sha256,
        "userdata_content_manifest_sha256": content_sha256,
    }


def normalized_auto_handoff_binding(
    manifest: dict[str, Any],
) -> dict[str, str] | None:
    """Return the exact compiled auto-handoff tuple or reject ambiguity."""

    cflags = manifest["init"]["cflags"]
    enabled = _macro_directives(cflags, "A90_AUTO_HANDOFF_BENCHMARK_V1")
    if not enabled:
        return None
    if enabled != ["-DA90_AUTO_HANDOFF_BENCHMARK_V1=1"]:
        raise RuntimeError("auto-handoff enable macro is duplicated or conflicting")
    userdata_flags = _macro_directives(cflags, AUTO_HANDOFF_USERDATA_ENABLE)
    if userdata_flags not in ([], [f"-D{AUTO_HANDOFF_USERDATA_ENABLE}=1"]):
        raise RuntimeError(
            "auto-handoff userdata enable macro is duplicated or conflicting"
        )
    userdata_root = bool(userdata_flags)
    dynamic_devt_flags = _macro_directives(
        cflags,
        AUTO_HANDOFF_USERDATA_DYNAMIC_DEVT_ENABLE,
    )
    if dynamic_devt_flags not in (
        [],
        [f"-D{AUTO_HANDOFF_USERDATA_DYNAMIC_DEVT_ENABLE}=1"],
    ):
        raise RuntimeError(
            "auto-handoff dynamic dev_t macro is duplicated or conflicting"
        )
    dynamic_devt = bool(dynamic_devt_flags)
    if dynamic_devt and not userdata_root:
        raise RuntimeError("auto-handoff dynamic dev_t requires userdata root")
    values: dict[str, str] = {}
    selected_value_macros = (
        *AUTO_HANDOFF_COMMON_VALUE_MACROS,
        *(
            (
                *AUTO_HANDOFF_USERDATA_STABLE_VALUE_MACROS,
                AUTO_HANDOFF_USERDATA_DYNAMIC_DEVT_POLICY_MACRO
                if dynamic_devt
                else AUTO_HANDOFF_USERDATA_LEGACY_DEVT_MACRO,
            )
            if userdata_root
            else AUTO_HANDOFF_IMAGE_VALUE_MACROS
        ),
    )
    for macro in selected_value_macros:
        values[macro] = _quoted_macro_value(cflags, macro)
    enable_path = values["A90_AUTO_HANDOFF_ENABLE_PATH"]
    latch_path = values["A90_AUTO_HANDOFF_LATCH_PATH"]
    receipt_pattern = re.compile(
        rf'^-D{re.escape(AUTO_HANDOFF_RECEIPT_MACRO)}="([^"\r\n]+)"$'
    )
    receipt_directives = _macro_directives(cflags, AUTO_HANDOFF_RECEIPT_MACRO)
    receipt_matches = [
        match.group(1)
        for flag in receipt_directives
        if (match := receipt_pattern.fullmatch(flag))
    ]
    if len(receipt_directives) != len(receipt_matches) or len(receipt_matches) > 1:
        raise RuntimeError(
            "auto-handoff source receipt macro is duplicated or conflicting"
        )
    receipt_path = receipt_matches[0] if receipt_matches else ""
    if (
        not enable_path.startswith("/cache/a90-auto-handoff-")
        or not latch_path.startswith("/cache/a90-auto-handoff-")
        or enable_path == latch_path
    ):
        raise RuntimeError("auto-handoff compiled tuple is not canonical")
    normalized: dict[str, str] = {
        "candidate_version": values["INIT_VERSION"],
        "candidate_build": values["INIT_BUILD"],
        "enable_path": enable_path,
        "latch_path": latch_path,
    }
    if userdata_root:
        forbidden_image_flags = [
            flag
            for macro in AUTO_HANDOFF_IMAGE_VALUE_MACROS
            for flag in _macro_directives(cflags, macro)
        ]
        userdata = {
            "userdata_devname": values["A90_AUTO_HANDOFF_USERDATA_DEVNAME"],
            "userdata_sectors": values["A90_AUTO_HANDOFF_USERDATA_SECTORS"],
            "userdata_label": values["A90_AUTO_HANDOFF_USERDATA_LABEL"],
            "userdata_marker": values["A90_AUTO_HANDOFF_USERDATA_MARKER"],
            "userdata_uuid": values["A90_AUTO_HANDOFF_USERDATA_UUID"],
            "userdata_content_manifest_sha256": values[
                "A90_AUTO_HANDOFF_USERDATA_CONTENT_MANIFEST_SHA256"
            ],
        }
        if dynamic_devt:
            if _macro_directives(
                cflags,
                AUTO_HANDOFF_USERDATA_LEGACY_DEVT_MACRO,
            ):
                raise RuntimeError(
                    "auto-handoff userdata dev_t policy is conflicting"
                )
            userdata["userdata_devt_policy"] = values[
                AUTO_HANDOFF_USERDATA_DYNAMIC_DEVT_POLICY_MACRO
            ]
        else:
            if _macro_directives(
                cflags,
                AUTO_HANDOFF_USERDATA_DYNAMIC_DEVT_POLICY_MACRO,
            ):
                raise RuntimeError(
                    "auto-handoff userdata dev_t policy is conflicting"
                )
            userdata["userdata_dev"] = values[
                AUTO_HANDOFF_USERDATA_LEGACY_DEVT_MACRO
            ]
        content_binding = _userdata_content_binding(values)
        expected_userdata = {
            "userdata_devname": "sda33",
            "userdata_sectors": "231577432",
            "userdata_label": "A90D4ROOT",
            "userdata_marker": "userdata=appliance-root",
            "userdata_uuid": content_binding["userdata_uuid"],
            "userdata_content_manifest_sha256": content_binding[
                "userdata_content_manifest_sha256"
            ],
        }
        expected_userdata[
            "userdata_devt_policy" if dynamic_devt else "userdata_dev"
        ] = (
            "runtime-resolved-same-session" if dynamic_devt else "259:17"
        )
        if forbidden_image_flags or receipt_path or userdata != expected_userdata:
            raise RuntimeError("auto-handoff userdata tuple is not canonical")
        normalized.update(
            {
                "schema": (
                    "a90-compiled-auto-handoff-binding-v4"
                    if dynamic_devt
                    else "a90-compiled-auto-handoff-binding-v3"
                ),
                "root_kind": "userdata-ext4-ro-noload",
                **userdata,
                "userdata_content_manifest": content_binding[
                    "userdata_content_manifest"
                ],
                "userdata_content_manifest_file_sha256": content_binding[
                    "userdata_content_manifest_file_sha256"
                ],
            }
        )
    else:
        forbidden_userdata_flags = [
            flag
            for macro in AUTO_HANDOFF_USERDATA_VALUE_MACROS
            for flag in _macro_directives(cflags, macro)
        ]
        forbidden_userdata_flags.extend(dynamic_devt_flags)
        image = values["A90_AUTO_HANDOFF_IMAGE"]
        image_sha256 = values["A90_AUTO_HANDOFF_IMAGE_SHA256"]
        if (
            forbidden_userdata_flags
            or not image.startswith("/mnt/sdext/a90/runtime/")
            or re.fullmatch(r"[0-9a-f]{64}", image_sha256) is None
            or (
                receipt_path
                and (
                    not receipt_path.startswith("/cache/a90-source-receipt-")
                    or receipt_path in {enable_path, latch_path}
                )
            )
        ):
            raise RuntimeError("auto-handoff compiled tuple is not canonical")
        normalized.update(
            {
                "schema": (
                    "a90-compiled-auto-handoff-binding-v2"
                    if receipt_path
                    else "a90-compiled-auto-handoff-binding-v1"
                ),
                "image_path": image,
                "image_sha256": image_sha256,
            }
        )
        if receipt_path:
            normalized["receipt_path"] = receipt_path
    auth_enabled, firstboot_enabled, hud_enabled = h17_runtime_features(manifest)
    delayed_hud_drm = h21_delayed_hud_drm_mode(manifest)
    preserved_dev_dir = h22_preserved_dev_dir_mode(manifest)
    private_card_root = h23_private_card_root_mode(manifest)
    if auth_enabled:
        if not userdata_root or not dynamic_devt:
            raise RuntimeError("H17 private runtime requires dynamic read-only userdata")
        normalized.update(
            {
                "schema": (
                    "a90-compiled-auto-handoff-binding-v5"
                    if firstboot_enabled and hud_enabled
                    else "a90-compiled-auto-handoff-binding-v6"
                ),
                "observer_auth": "boot-private-tmpfs-v1",
                "display_owner": (
                    "native-handoff-hud-v1"
                    if hud_enabled
                    else "debian-existing-firstboot-v1"
                ),
            }
        )
        if (hud_enabled and not firstboot_enabled and delayed_hud_drm and
                private_card_root):
            normalized.update(
                {
                    "schema": "a90-compiled-auto-handoff-binding-v11",
                    "firstboot_source": "ufs-existing-immutable-v1",
                    "firstboot_overlay": "disabled",
                    "persistent_native_hud": "enabled",
                    "hud_drm_acquisition": "deferred-until-ufs-intent-v3",
                    "hud_drm_device_access": (
                        "private-pivot-root-card0-bind-v1"
                    ),
                    "hud_mount_namespace": "private-minimal-card-root-v1",
                    "hud_device_exposure": "card0-only-no-userdata-v1",
                    "debian_dev_tree_exposure": (
                        "minimal-core-char-no-drm-no-userdata-v1"
                    ),
                    "debian_proc_hud_root_exposure": (
                        "card0-and-shared-public-run-no-block-no-userdata-v1"
                    ),
                    "ufs_firstboot_cleanup_compatibility": (
                        "zero-pre-intent-drm-fd-v3"
                    ),
                }
            )
        elif (hud_enabled and not firstboot_enabled and delayed_hud_drm and
                preserved_dev_dir):
            normalized.update(
                {
                    "schema": "a90-compiled-auto-handoff-binding-v9",
                    "firstboot_source": "ufs-existing-immutable-v1",
                    "firstboot_overlay": "disabled",
                    "persistent_native_hud": "enabled",
                    "hud_drm_acquisition": "deferred-until-ufs-intent-v2",
                    "hud_drm_device_access": (
                        "preopened-dev-dir-fd-openat-card0-v1"
                    ),
                    "ufs_firstboot_cleanup_compatibility": (
                        "no-pre-intent-drm-card-fd-v2"
                    ),
                }
            )
        elif hud_enabled and not firstboot_enabled and delayed_hud_drm:
            normalized.update(
                {
                    "schema": "a90-compiled-auto-handoff-binding-v8",
                    "firstboot_source": "ufs-existing-immutable-v1",
                    "firstboot_overlay": "disabled",
                    "persistent_native_hud": "enabled",
                    "hud_drm_acquisition": "deferred-until-ufs-intent-v1",
                    "ufs_firstboot_cleanup_compatibility": (
                        "no-pre-intent-drm-fd-v1"
                    ),
                }
            )
        elif hud_enabled and not firstboot_enabled:
            normalized.update(
                {
                    "schema": "a90-compiled-auto-handoff-binding-v7",
                    "firstboot_source": "ufs-existing-immutable-v1",
                    "firstboot_overlay": "disabled",
                    "persistent_native_hud": "enabled",
                }
            )
        elif not hud_enabled:
            normalized.update(
                {
                    "firstboot_source": "ufs-existing-immutable-v1",
                    "persistent_native_hud": "disabled",
                }
            )
    encoded = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        **normalized,
        "binding_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def artifact_names(manifest: dict[str, Any]) -> dict[str, str]:
    names = dict(ARTIFACT_NAMES)
    if manifest["engine"]["enabled"] is False:
        del names["engine"]
    return names


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL_A90.md").is_file():
            return parent
    raise RuntimeError("could not locate repository root")


def builder_source_keys(repo: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for role, requested in BUILDER_SOURCES.items():
        if requested.is_symlink() or not requested.is_file():
            raise RuntimeError(f"builder source is not one regular file: {requested}")
        path = requested.resolve()
        try:
            relative = path.relative_to(repo.resolve())
        except ValueError as exc:
            raise RuntimeError(f"builder source escapes repository: {path}") from exc
        result[role] = {
            "path": relative.as_posix(),
            "size": path.stat().st_size,
            "sha256": buildlib.sha256_file(path),
        }
    return result


def revalidate_execution_closure(
    repo: Path,
    resolution: buildlib.ManifestResolution,
    manifest: dict[str, Any],
    expected_inputs: dict[str, Any],
    expected_source_keys: dict[str, dict[str, object]],
) -> None:
    buildlib.revalidate_manifest_lineage(resolution)
    if builder_source_keys(repo) != expected_source_keys:
        raise RuntimeError("flat-builder source closure changed during execution")
    current_inputs = buildlib.validate_inputs(repo, resolution, manifest)
    observer_path = expected_inputs.get("observer_authorized_key")
    if observer_path is not None:
        observer = validate_observer_authorized_key(
            repo,
            manifest,
            Path(observer_path),
        )
        assert observer is not None
        current_inputs.update(
            {
                "observer_authorized_key": observer["path"],
                "observer_authorized_key_bytes": observer["bytes"],
                "observer_authorized_key_sha256": observer["sha256"],
            }
        )
    if h17_firstboot_overlay_mode(manifest):
        firstboot = (repo / H17_FIRSTBOOT_SOURCE).resolve(strict=True)
        current_inputs.update(
            {
                "h17_firstboot": firstboot,
                "h17_firstboot_sha256": buildlib.sha256_file(firstboot),
            }
        )
    expected_pins = {
        key: value
        for key, value in expected_inputs.items()
        if key.endswith("_sha256")
    }
    current_pins = {
        key: value
        for key, value in current_inputs.items()
        if key.endswith("_sha256")
    }
    if current_pins != expected_pins:
        raise RuntimeError("flat-builder input pins changed during execution")
    normalized_auto_handoff_binding(manifest)


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


def selected_manifest(requested: Path) -> Path:
    versions = (HERE / "versions").resolve()
    if requested.is_symlink() or requested.parent.is_symlink():
        raise RuntimeError(
            f"manifest/profile must not be a symlink: {requested}"
        )
    resolved = requested.resolve()
    try:
        relative = resolved.relative_to(versions)
    except ValueError as exc:
        raise RuntimeError(f"manifest must stay below {versions}: {resolved}") from exc
    if len(relative.parts) != 2 or relative.name != "manifest.toml":
        raise RuntimeError(
            "manifest must be versions/<host-profile>/manifest.toml"
        )
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


def validate_packed_ramdisk(
    manifest: dict[str, Any],
    archive: Path,
) -> set[str]:
    listing = buildlib.newc_archive_listing(archive.read_bytes())
    missing = sorted(set(manifest["ramdisk"]["required_entries"]) - listing)
    if missing:
        raise RuntimeError(f"ramdisk required entries missing: {missing}")
    buildlib.validate_ramdisk_component_listing(manifest, listing)
    auth_enabled, firstboot_enabled, _ = h17_runtime_features(manifest)
    h17_entries = {H17_OBSERVER_AUTH_RAMDISK_PATH, H17_FIRSTBOOT_RAMDISK_PATH}
    expected_h17_entries: set[str] = set()
    if auth_enabled:
        expected_h17_entries.add(H17_OBSERVER_AUTH_RAMDISK_PATH)
    if firstboot_enabled:
        expected_h17_entries.add(H17_FIRSTBOOT_RAMDISK_PATH)
    if listing & h17_entries != expected_h17_entries:
        raise RuntimeError("packed ramdisk H17 runtime entries mismatch")
    return listing


def overlay_ramdisk(
    repo: Path,
    manifest: dict[str, Any],
    inputs: dict[str, Any],
    output_dir: Path,
    init: Path,
    helper: Path,
    engine: Path | None,
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
        for relative in manifest["ramdisk"].get("remove_entries", []):
            removed = safe_ramdisk_path(ramdisk, relative, "removed entry")
            removed.unlink(missing_ok=True)
        if manifest["engine"]["enabled"]:
            if engine is None:
                raise RuntimeError("enabled engine output is absent")
            engine_path = safe_ramdisk_path(
                ramdisk,
                manifest["engine"]["ramdisk_path"],
                "engine",
            )
            engine_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(engine, engine_path)
            engine_path.chmod(0o755)
        elif engine is not None:
            raise RuntimeError("disabled engine unexpectedly has output")

        observer_key = inputs.get("observer_authorized_key")
        if observer_key is not None:
            observer_path = safe_ramdisk_path(
                ramdisk,
                H17_OBSERVER_AUTH_RAMDISK_PATH,
                "H17 observer authorized key",
            )
            if observer_path.exists() or observer_path.is_symlink():
                raise RuntimeError("base ramdisk already contains the H17 observer key path")
            observer_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(observer_key), observer_path)
            observer_path.chmod(0o400)
            if h17_firstboot_overlay_mode(manifest):
                firstboot_path = safe_ramdisk_path(
                    ramdisk,
                    H17_FIRSTBOOT_RAMDISK_PATH,
                    "H17 firstboot overlay",
                )
                if firstboot_path.exists() or firstboot_path.is_symlink():
                    raise RuntimeError(
                        "base ramdisk already contains the H17 firstboot path"
                    )
                shutil.copyfile(Path(inputs["h17_firstboot"]), firstboot_path)
                firstboot_path.chmod(0o500)

        set_reproducible_mtime(ramdisk, int(manifest["reproducible_mtime"]))
        pack_ramdisk(manifest, ramdisk, ramdisk_cpio)
        validate_packed_ramdisk(manifest, ramdisk_cpio)

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


def artifact_info(
    root: Path,
    names: dict[str, str],
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for name, relative in names.items():
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
    resolution: buildlib.ManifestResolution,
    manifest: dict[str, Any],
    inputs: dict[str, Any],
    versions: dict[str, str],
    source_keys: dict[str, dict[str, object]],
    root: Path,
) -> dict[str, Any]:
    if root.exists() or root.is_symlink():
        raise RuntimeError(f"single build output must be absent: {root}")
    revalidate_execution_closure(
        repo,
        resolution,
        manifest,
        inputs,
        source_keys,
    )
    build_dir = root / "build"
    build_dir.mkdir(parents=True, mode=0o700)
    init = build_dir / "init"
    helper = build_dir / "helper"
    engine = build_dir / "engine" if manifest["engine"]["enabled"] else None
    build_init(manifest, inputs, init, build_dir / "obj/init")
    build_helper(manifest, inputs, helper)
    if engine is not None:
        build_engine(manifest, inputs, engine, build_dir / "obj/engine")
    overlay_ramdisk(repo, manifest, inputs, build_dir, init, helper, engine)

    validation = manifest["validation"]
    require_markers(init, validation["init_strings"], "init")
    require_markers(helper, validation["helper_strings"], "helper")
    if engine is not None:
        require_markers(engine, validation["engine_strings"], "engine")
    artifacts = artifact_info(root, artifact_names(manifest))
    revalidate_execution_closure(
        repo,
        resolution,
        manifest,
        inputs,
        source_keys,
    )
    receipt = {
        "schema": "a90-flat-builder-v1-build-receipt",
        "profile": manifest["profile"],
        "candidate_authority": False,
        "manifest": str(manifest_path.relative_to(repo)),
        "manifest_sha256": resolution.lineage_sha256[0],
        "effective_manifest_sha256": resolution.effective_sha256,
        "manifest_lineage": [
            {
                "path": str(path.relative_to(repo)),
                "sha256": digest,
            }
            for path, digest in zip(
                resolution.lineage,
                resolution.lineage_sha256,
                strict=True,
            )
        ],
        "inputs": {
            key: value
            for key, value in inputs.items()
            if key.endswith("_sha256")
        },
        "toolchain": versions,
        "source_keys": source_keys,
        "artifacts": artifacts,
        "legacy_bridge_reference": manifest["legacy_bridge"],
    }
    write_json(root / "receipt.json", receipt)
    return receipt


def audit(
    repo: Path,
    manifest_path: Path,
    observer_authorized_key: Path | None = None,
) -> tuple[
    buildlib.ManifestResolution,
    dict[str, Any],
    dict[str, Any],
    dict[str, str],
    dict[str, dict[str, object]],
]:
    resolution = buildlib.resolve_manifest(manifest_path)
    manifest = resolution.data
    inputs = buildlib.validate_inputs(repo, resolution, manifest)
    observer = validate_observer_authorized_key(
        repo,
        manifest,
        observer_authorized_key,
    )
    if observer is not None:
        inputs.update(
            {
                "observer_authorized_key": observer["path"],
                "observer_authorized_key_bytes": observer["bytes"],
                "observer_authorized_key_sha256": observer["sha256"],
            }
        )
        if h17_firstboot_overlay_mode(manifest):
            firstboot = (repo / H17_FIRSTBOOT_SOURCE).resolve(strict=True)
            if firstboot.is_symlink() or not firstboot.is_file():
                raise RuntimeError("H17 firstboot source is not one regular file")
            inputs.update(
                {
                    "h17_firstboot": firstboot,
                    "h17_firstboot_sha256": buildlib.sha256_file(firstboot),
                }
            )
    versions = validate_toolchain(manifest)
    source_keys = builder_source_keys(repo)
    return resolution, manifest, inputs, versions, source_keys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    outputs = parser.add_mutually_exclusive_group()
    outputs.add_argument("--out-dir", type=Path)
    outputs.add_argument("--ab-root", type=Path)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--observer-authorized-key", type=Path)
    args = parser.parse_args()
    os.environ.update({"LC_ALL": "C", "LANG": "C", "TZ": "UTC"})
    repo = repo_root()
    manifest_path = selected_manifest(args.manifest)
    resolution, manifest, inputs, versions, source_keys = audit(
        repo,
        manifest_path,
        args.observer_authorized_key,
    )
    auto_handoff_binding = normalized_auto_handoff_binding(manifest)
    audit_result = {
        "schema": buildlib.SCHEMA,
        "profile": manifest["profile"],
        "candidate_authority": False,
        "manifest_sha256": resolution.lineage_sha256[0],
        "effective_manifest_sha256": resolution.effective_sha256,
        "manifest_lineage": [
            {
                "path": str(path.relative_to(repo)),
                "sha256": digest,
            }
            for path, digest in zip(
                resolution.lineage,
                resolution.lineage_sha256,
                strict=True,
            )
        ],
        "input_pins": {
            key: value
            for key, value in inputs.items()
            if key.endswith("_sha256")
        },
        "toolchain": versions,
        "source_keys": source_keys,
    }
    if auto_handoff_binding is not None:
        audit_result["auto_handoff_binding"] = auto_handoff_binding
    if args.audit_only:
        revalidate_execution_closure(
            repo,
            resolution,
            manifest,
            inputs,
            source_keys,
        )
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
            resolution,
            manifest,
            inputs,
            versions,
            source_keys,
            root,
        )
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        root.mkdir(parents=True, mode=0o700)
        a_receipt = build_one(
            repo,
            manifest_path,
            resolution,
            manifest,
            inputs,
            versions,
            source_keys,
            root / "A",
        )
        b_receipt = build_one(
            repo,
            manifest_path,
            resolution,
            manifest,
            inputs,
            versions,
            source_keys,
            root / "B",
        )
        byte_identical = all(
            filecmp.cmp(
                root / "A" / relative,
                root / "B" / relative,
                shallow=False,
            )
            for relative in artifact_names(manifest).values()
        )
        if a_receipt["artifacts"] != b_receipt["artifacts"]:
            byte_identical = False
        revalidate_execution_closure(
            repo,
            resolution,
            manifest,
            inputs,
            source_keys,
        )
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
    revalidate_execution_closure(
        repo,
        resolution,
        manifest,
        inputs,
        source_keys,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
