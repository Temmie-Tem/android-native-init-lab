#!/usr/bin/env python3
"""Build V3354 native-init §0.2 E4 boot-header sector identity rung."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3353_boot_write_e3b_1mib as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3353_text
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3353_adapter_source
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3353_ramdisk
ORIG_PREVIOUS_FINALIZE = previous._finalize_manifest_after_overlay
ORIG_PREVIOUS_POSTPROCESS = previous._postprocess_manifest

CYCLE = "V3354"
INIT_VERSION = "0.11.118"
INIT_BUILD = "v3354-boot-write-e4-header"
BUILD_TAG = INIT_BUILD
DECISION = "v3354-boot-write-e4-header-source-build-pass"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3354_BOOT_WRITE_E4_HEADER_SOURCE_BUILD_2026-07-02.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3354_boot_write_e4_header.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3354_boot_write_e4_header"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3354_boot_write_e4_header.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v626_boot_write_e4_header"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3354"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3354.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3354.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3354"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3354-boot-write-e4-header"

FRAME_PATH = "/tmp/a90-doomgeneric-v3354-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3354-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3354-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3354-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3354-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3354-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3354-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3354.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3354_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.117", INIT_VERSION),
        ("v3353", "v3354"),
        ("V3353", "V3354"),
        ("a90-doomgeneric-v3353", "a90-doomgeneric-v3354"),
        ("a90.doomgeneric.v3353", "a90.doomgeneric.v3354"),
        ("boot_write_e3b_1mib", "boot_write_e4_header"),
        ("boot-write-e3b-1mib", "boot-write-e4-header"),
        ("BOOT_WRITE_E3B_1MIB", "BOOT_WRITE_E4_HEADER"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3354_bytes(item: bytes) -> bytes:
    return _rewrite_v3354_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3354_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3354_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3354_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3354_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(_rewrite_v3354_bytes(item) for item in previous.REQUIRED_STRINGS)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.118",
    b"v3354-boot-write-e4-header",
    b"A90BWE4",
    b"boot-write-e4 <token>",
    b"BOOT-WRITE-PROBE-E4-HEADER-SECTOR",
    b"header-sector-4096-identity",
    b"target_off=%llu len=%u header_magic=%s source_sha=%s",
    b"pwrite_count=1 pwrite=ok fsync=ok",
    b"readback_rc=%ld region_match=%d readback_sha=%s",
    b"sector_sha_match=%d",
)


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "boot-write-probe-E4-header-sector"
    manifest["scope"] = "0.2-write-probe-E4-offset-0-4096-header-sector-identity"
    manifest["commands"] = ["boot-write-e4 BOOT-WRITE-PROBE-E4-HEADER-SECTOR"]
    manifest["probe_contract"] = {
        "rung": "E4",
        "token": "BOOT-WRITE-PROBE-E4-HEADER-SECTOR",
        "cmd_flags": "CMD_DANGEROUS (menu-settle required)",
        "write_syscall": "one pwrite call of 4096 bytes to offset 0",
        "target": "Android boot header sector at boot partition offset 0",
        "safety_gates": "fail-closed Android magic/header parse, identity on every fd, O_NOFOLLOW",
        "verify": "O_DIRECT 4096B readback memcmp + sector SHA + O_DIRECT full-partition SHA before/after",
        "risk": "late high-consequence identity rung: UFS-tear residual can corrupt boot header; externally recoverable boot-only",
    }
    manifest["pass_requirements"] = [
        "version-0.11.118",
        "post-flash-selftest-fail-0",
        "boot-write-e4-token-and-menu-gated",
        "boot-write-e4-target-offset-0-len-4096",
        "boot-write-e4-android-header-magic-ok",
        "boot-write-e4-pwrite-count-1",
        "boot-write-e4-sector-sha-match-1",
        "boot-write-e4-region-match-all-1",
        "boot-write-e4-full-match-1",
        "rollback-v2321-selftest-fail-0",
    ]
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
        "# Native Init V3354 §0.2 Write-Probe E4 Header Source Build",
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
        "- Adds `boot-write-e4 <token>` after the V3353 E3b live pass. E4 writes one 4096B "
        "identity block at boot partition offset 0, the Android boot-header sector.",
        "- The command reads the sector first, requires `ANDROID!` magic and a valid boot-header "
        "parse, writes exactly the bytes it just read, fsyncs, checks an O_DIRECT sector readback "
        "and sector SHA, then compares O_DIRECT full-partition SHA before/after.",
        "- This is the first non-slack write rung. The residual tear risk is boot-header corruption, "
        "still boot-only and externally recoverable through the existing v2321 rollback path.",
        "",
        "## Validation Contract",
        "",
        "- PASS requires post-flash `selftest fail=0`, `version` 0.11.118, and after `hide`, "
        "`boot-write-e4 BOOT-WRITE-PROBE-E4-HEADER-SECTOR` emitting `target_off=0`, `len=4096`, "
        "`header_magic=ANDROID`, `pwrite_count=1`, `sector_sha_match=1`, `region_match_all=1`, "
        "`full_match=1`, then rollback to `v2321` with `selftest fail=0`.",
        "- This is a source-build preparation only; no live V3354 write is claimed here.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `boot-write-e4-header-candidate`.",
    ]) + "\n"


def v3354_adapter_source() -> str:
    return _rewrite_v3354_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "boot-write-e4-header-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "boot-write-e4-header-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "live_validation_focus": manifest["boot_audit"]["pass_requirements"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-boot-write-e4-header-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3354(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "boot-write-e4-header-candidate",
        "adoption_state": "pending-boot-write-e4-header-live-validation",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_audit": _boot_audit_manifest(),
    })
    manifest["helper_flags"] = list(dict.fromkeys([
        *manifest.get("helper_flags", []),
        SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG,
    ]))
    for key in previous._STALE_MANIFEST_KEYS:
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
    manifest = _normalize_manifest_for_v3354(json.loads(manifest_path.read_text(encoding="utf-8")))
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
    manifest = _normalize_manifest_for_v3354(ORIG_PREVIOUS_POSTPROCESS())
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


def _overlay_preserved_v3354_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3354-init-helper-engine"
    return overlay


def _patch_v3353_module_for_v3354() -> None:
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
        "v3353_adapter_source": v3354_adapter_source,
        "_rewrite_v3353_text": _rewrite_v3354_text,
        "_rewrite_v3353_bytes": _rewrite_v3354_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3353_ramdisk": _overlay_preserved_v3354_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3353_module_for_v3354()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
