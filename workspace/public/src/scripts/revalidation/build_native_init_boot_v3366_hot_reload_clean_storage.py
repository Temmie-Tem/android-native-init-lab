#!/usr/bin/env python3
"""Build V3366 native-init boot image for H3 hot-reload storage cleanliness.

Chains off V3365 (hot-reload delta). This unit preserves the reload proof surface and
adds the storage adoption fix: an already-mounted `/cache` or `/mnt/sdext` rw mount is
accepted as a clean boot resource during PID1 hot-reload instead of being treated as an
EBUSY remount failure.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3365_hot_reload_delta as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3365_text
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3365_adapter_source
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3365_ramdisk
ORIG_PREVIOUS_FINALIZE = previous._finalize_manifest_after_overlay
ORIG_PREVIOUS_POSTPROCESS = previous._postprocess_manifest

CYCLE = "V3366"
INIT_VERSION = "0.11.127"
INIT_BUILD = "v3366-hot-reload-clean-storage"
BUILD_TAG = INIT_BUILD
DECISION = "v3366-hot-reload-clean-storage-source-build"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

_STALE_MANIFEST_KEYS = tuple(
    getattr(previous, "_STALE_MANIFEST_KEYS", None)
    or getattr(previous.previous, "_STALE_MANIFEST_KEYS", None)
    or getattr(previous.previous.previous, "_STALE_MANIFEST_KEYS", ())
)

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3366_HOT_RELOAD_CLEAN_STORAGE_SOURCE_BUILD_2026-07-03.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3366_hot_reload_clean_storage.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3366_hot_reload_clean_storage"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3366_hot_reload_clean_storage.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v629_hot_reload_clean_storage"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3366"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3366.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3366.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3366"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3366-hot-reload-clean-storage"

FRAME_PATH = "/tmp/a90-doomgeneric-v3366-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3366-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3366-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3366-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3366-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3366-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3366-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3366.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3366_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.126", INIT_VERSION),
        ("v3365-hot-reload-delta", INIT_BUILD),
        ("hot-reload-delta", "hot-reload-clean-storage"),
        ("v3365", "v3366"),
        ("V3365", "V3366"),
        ("a90-doomgeneric-v3365", "a90-doomgeneric-v3366"),
        ("a90.doomgeneric.v3365", "a90.doomgeneric.v3366"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3366_bytes(item: bytes) -> bytes:
    return _rewrite_v3366_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3366_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3366_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3366_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3366_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(_rewrite_v3366_bytes(item) for item in previous.REQUIRED_STRINGS)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.127",
    b"v3366-hot-reload-clean-storage",
    b"A90RELOAD",
    b"INIT-RELOAD-EXECVE",
    b"hot-reload fast-path (A90_RELOADED set)",
    b"storage-adopt",
    b"sd already mounted rw",
    b"/cache already mounted rw",
)


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "hot-reload-clean-storage"
    manifest["scope"] = "H3-reload-storage-adopts-existing-rw-mounts"
    manifest["reload_contract"] = {
        "command": "reload INIT-RELOAD-EXECVE <staged-init-path> <expected-sha256>",
        "h3_success": "post-reload version/build changes to V3366, boot summary is BOOT OK, "
                      "storage backend remains sd, runtime backend remains sd, and selftest fail=0",
        "storage_fix": "already-mounted rw /cache and /mnt/sdext are adopted instead of remounted",
        "safety": "no new boot-write primitive; live H3 stages only an init ELF under the approved SD root",
        "risk": "source build only; live H3 reload is separately gated",
    }
    return manifest


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    boot_image = manifest.get("boot_image", base.rel(BOOT_IMAGE))
    boot_sha = manifest.get("boot_sha256", "")
    helper_sha = manifest.get("helper_sha256", "")
    return "\n".join([
        "# Native Init V3366 Hot-Reload Clean Storage Source Build",
        "",
        f"- Cycle: `{CYCLE}`",
        f"- Decision: `{DECISION}`",
        f"- Init: `A90 Linux init {INIT_VERSION} ({INIT_BUILD})`",
        f"- Boot image: `{boot_image}`",
        f"- Boot SHA256: `{boot_sha}`",
        f"- Helper SHA256: `{helper_sha}`",
        f"- Base boot: `{base.rel(BASE_BOOT)}`",
        "",
        "## Change",
        "",
        "- H3 cleanup candidate after V3365 H2: keep the reload command and V3365 proof surface, "
        "but fix reload storage cleanliness.",
        "- `/cache` mount setup now treats `EBUSY` plus an already-mounted rw `/cache` as ready.",
        "- SD boot probing now adopts an already-mounted rw `/mnt/sdext` after UUID validation, then "
        "runs the same workspace, identity-marker, and rw probes before selecting SD storage.",
        "- Normal boot behavior remains the same when those mounts are not already present.",
        "",
        "## Validation Contract",
        "",
        "- Static PASS requires the V3366 version strings, reload markers, and the storage adoption "
        "markers (`storage-adopt`, `sd already mounted rw`, `/cache already mounted rw`).",
        "- Live H3 PASS, separately gated, requires: staged V3366 init SHA matches; `reload` returns "
        "through the new V3366 shell; `status` reports `BOOT OK`, `storage backend=sd`, runtime SD "
        "root, and `selftest fail=0`; then rollback to v2321 and health-check clean.",
        "- No live H3 reload result is claimed by this source-build report.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `hot-reload-clean-storage`.",
    ]) + "\n"


def v3366_adapter_source() -> str:
    return _rewrite_v3366_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "hot-reload-clean-storage.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "hot-reload-clean-storage",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "reload_candidate_init_binary": base.rel(INIT_BINARY),
        "source_report": base.rel(REPORT_PATH),
        "resident_required_for_h3": "v3364-or-later-hot-reload-fastpath",
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "source-built-live-gated",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3366(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "hot-reload-clean-storage",
        "adoption_state": "source-built-live-gated",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_audit": _boot_audit_manifest(),
    })
    manifest["helper_flags"] = list(dict.fromkeys([
        *manifest.get("helper_flags", []),
        SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG,
    ]))
    for key in _STALE_MANIFEST_KEYS:
        manifest.pop(key, None)
    return manifest


def _finalize_manifest_after_overlay(
    overlay: dict[str, Any],
    *,
    base_main_completed: bool,
    base_main_error: str | None = None,
) -> None:
    ORIG_PREVIOUS_FINALIZE(
        overlay,
        base_main_completed=base_main_completed,
        base_main_error=base_main_error,
    )
    manifest_path = OUT_DIR / "manifest.json"
    manifest = _normalize_manifest_for_v3366(json.loads(manifest_path.read_text(encoding="utf-8")))
    if base_main_error:
        manifest["base_main_error"] = base_main_error
    else:
        manifest.pop("base_main_error", None)
    manifest["boot_audit"]["ramdisk_overlay"] = overlay
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(
        render_report(
            manifest,
            tuple(manifest.get("helper_flags", ())),
            tuple(manifest.get("init_extra_flags", ())),
        ),
        encoding="utf-8",
    )
    _write_candidate_manifest(manifest)


def _postprocess_manifest() -> dict[str, Any]:
    manifest = _normalize_manifest_for_v3366(ORIG_PREVIOUS_POSTPROCESS())
    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(
        render_report(
            manifest,
            tuple(manifest.get("helper_flags", ())),
            tuple(manifest.get("init_extra_flags", ())),
        ),
        encoding="utf-8",
    )
    _write_candidate_manifest(manifest)
    return manifest


def _overlay_preserved_v3366_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3366-init-helper-engine"
    return overlay


def _patch_v3365_module_for_v3366() -> None:
    replacements = {
        "CYCLE": CYCLE,
        "INIT_VERSION": INIT_VERSION,
        "INIT_BUILD": INIT_BUILD,
        "BUILD_TAG": BUILD_TAG,
        "DECISION": DECISION,
        "OUT_DIR": OUT_DIR,
        "OBJ_DIR": OBJ_DIR,
        "REPORT_PATH": REPORT_PATH,
        "BOOT_IMAGE": BOOT_IMAGE,
        "BASE_BOOT": BASE_BOOT,
        "INIT_BINARY": INIT_BINARY,
        "RAMDISK_CPIO": RAMDISK_CPIO,
        "HELPER_BINARY": HELPER_BINARY,
        "ENGINE_BINARY": ENGINE_BINARY,
        "ENGINE_ADAPTER_SOURCE": ENGINE_ADAPTER_SOURCE,
        "ENGINE_ADAPTER_OBJECT": ENGINE_ADAPTER_OBJECT,
        "ENGINE_RAMDISK_PATH": ENGINE_RAMDISK_PATH,
        "ENGINE_REMOTE_PATH": ENGINE_REMOTE_PATH,
        "ENGINE_NAME": ENGINE_NAME,
        "FRAME_PATH": FRAME_PATH,
        "SHARED_FRAME_PATH": SHARED_FRAME_PATH,
        "INPUT_STATE_PATH": INPUT_STATE_PATH,
        "INPUT_SOCKET_PATH": INPUT_SOCKET_PATH,
        "PACE_SOCKET_PATH": PACE_SOCKET_PATH,
        "TICK_TELEMETRY_PATH": TICK_TELEMETRY_PATH,
        "AUDIO_PCM_STREAM_PATH": AUDIO_PCM_STREAM_PATH,
        "FRAME_SCALE": FRAME_SCALE,
        "FRAME_IPC": FRAME_IPC,
        "SFX_STREAM_MARKER": SFX_STREAM_MARKER,
        "SOUND_MODE": SOUND_MODE,
        "SFX_BACKEND_SOURCE": SFX_BACKEND_SOURCE,
        "SDL_MIXER_STUB": SDL_MIXER_STUB,
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "SOFTAP_COMMANDS": SOFTAP_COMMANDS,
        "render_report": render_report,
        "v3365_adapter_source": v3366_adapter_source,
        "_rewrite_v3365_text": _rewrite_v3366_text,
        "_rewrite_v3365_bytes": _rewrite_v3366_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3365_ramdisk": _overlay_preserved_v3366_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3365_module_for_v3366()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
