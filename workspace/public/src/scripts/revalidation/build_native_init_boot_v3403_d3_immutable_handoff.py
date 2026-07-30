#!/usr/bin/env python3
"""Build V3403 native-init boot image with an immutable D3 handoff input."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3402_dpublic_hud_presenter_restart_policy as previous
import build_native_init_wifi_test_boot_v1693 as legacy_v1693
import native_doomgeneric_engine_integration_build_v3024 as doom_source

base = previous.base
ORIG_V3402_REQUIRED_STRINGS = previous.REQUIRED_STRINGS
ORIG_V3402_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_V3402_NORMALIZE_MANIFEST = previous._normalize_manifest_for_v3402
ORIG_V3402_REWRITE_TEXT = previous._rewrite_v3402_text

CYCLE = "V3403"
INIT_VERSION = "0.11.159"
INIT_BUILD = "v3403-d3-immutable-handoff"
BUILD_TAG = INIT_BUILD
DECISION = "v3403-d3-immutable-handoff-source-build"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3403_D3_IMMUTABLE_HANDOFF_SOURCE_BUILD_2026-07-30.md"
)
SOURCE_CONTRACT_PATH = (
    REPO_ROOT
    / "workspace"
    / "public"
    / "src"
    / "scripts"
    / "revalidation"
    / "a90_d3_immutable_handoff_v3403.py"
)
PRIVATE_DOOM_SOURCE_ROOT = (
    REPO_ROOT / "workspace" / "private" / "demo-assets" / "doom" / "doomgeneric-v3403"
)
PRIVATE_DOOM_SOURCE_DIR = PRIVATE_DOOM_SOURCE_ROOT / "doomgeneric"
RECOVERED_V535_MANIFEST = (
    REPO_ROOT
    / "workspace"
    / "private"
    / "runs"
    / "server-distro"
    / "a90-debian-reactivation-prep-20260730"
    / "rebuild-audit"
    / "source-v2321-commit"
    / "tmp"
    / "wifi"
    / "v535-rmt-storage-private-property-runtime"
    / "manifest.json"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3403_d3_immutable_handoff.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3403_d3_immutable_handoff"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3403_d3_immutable_handoff.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v640_d3_immutable_handoff"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3403"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3403.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3403.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3403"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3403-d3-immutable-handoff"

FRAME_PATH = "/tmp/a90-doomgeneric-v3403-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3403-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3403-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3403-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3403-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3403-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3403-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3403.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3403_text(text: str) -> str:
    text = ORIG_V3402_REWRITE_TEXT(text)
    replacements = (
        ("v3402-dpublic-hud-presenter-restart-policy", INIT_BUILD),
        ("0.11.158", INIT_VERSION),
        ("V3402", CYCLE),
        ("v3402", "v3403"),
        ("a90-doomgeneric-v3402", "a90-doomgeneric-v3403"),
        ("a90.doomgeneric.v3402", "a90.doomgeneric.v3403"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3403_bytes(item: bytes) -> bytes:
    return _rewrite_v3403_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3403_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3403_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3403_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3403_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(
    _rewrite_v3403_bytes(marker) for marker in ORIG_V3402_REQUIRED_STRINGS
)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.159",
    b"v3403-d3-immutable-handoff",
    b"A90D3H0",
    b"handoff_display strict=1 preserve_dpublic=0",
    b"required_nonpreserved_owner_count=0 observed=%u",
    b"source_sha phase=%s sha=%s expected_sha_match=1",
    b"work_copy=ready source=%s work=%s",
    b"d3-handoff-work.img",
    b"source_unchanged_after_failure=1",
)

OBSOLETE_RAMDISK_ENGINES = tuple(dict.fromkeys([
    *previous.OBSOLETE_RAMDISK_ENGINES,
    "a90_doomgeneric_private_engine_v3402",
]))


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_V3402_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "d3-immutable-handoff"
    manifest["scope"] = "sd-rootfs-source-immutable-through-pre-switch-root-failures"
    manifest["d3_immutable_handoff"] = {
        "source_policy": "manifest-bound source image is never loop-attached or mounted rw",
        "display_cleanup": "stop autohud and dpublic presenter, terminate every native DRM owner, require zero",
        "display_cleanup_before_storage": True,
        "source_recheck_after_display_cleanup": True,
        "work_copy": "/mnt/sdext/a90/runtime/d3-handoff-work.img",
        "work_copy_mounted_rw": True,
        "preexisting_work_copy_refused": True,
        "failure_cleanup": ["restore mounts", "unmount work root", "detach loop", "remove owned work copy"],
        "source_sha_recheck_after_failure": True,
        "source_contract": base.rel(SOURCE_CONTRACT_PATH),
        "private_doom_source_pin": doom_source.PINNED_COMMIT,
        "legacy_v535_manifest_sha256": (
            "e848fafcfe3070a3a37ea389542c4ececdb7db60a8fe511821b847c29c6f647c"
        ),
    }
    manifest["wifi_uplink_service_boundary"]["obsolete_ramdisk_engines"] = [
        "bin/" + name for name in OBSOLETE_RAMDISK_ENGINES
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
        "# Native Init V3403 D3 Immutable Handoff Source Build",
        "",
        f"- Cycle: `{CYCLE}`",
        f"- Decision: `{DECISION}`",
        f"- Init: `A90 Linux init {INIT_VERSION} ({INIT_BUILD})`",
        f"- Boot image: `{boot_image}`",
        f"- Boot SHA256: `{boot_sha}`",
        f"- Helper SHA256: `{helper_sha}`",
        f"- Base boot: `{base.rel(BASE_BOOT)}`",
        f"- Source contract: `{base.rel(SOURCE_CONTRACT_PATH)}`",
        "",
        "## Change",
        "",
        "- Keeps V3402's native services and restart policy while replacing the D3 handoff ordering.",
        "- Stops autohud and the D-public presenter, terminates all native-init DRM owners, and requires zero remaining owners before any loop attachment or rw mount.",
        "- Rechecks the manifest-bound source SHA after display cleanup, copies it to a fixed absent-only work image, and loop-mounts only that work image rw.",
        "- On every pre-`switch_root` failure, restores moved mounts, unmounts the work root, detaches the loop, removes the owned work image, and rechecks the original source SHA.",
        "- Refuses a preexisting work image rather than overwriting or deleting an unowned path.",
        "",
        "## Validation",
        "",
        "- Host-only model injects every pre-switch failure and a multi-owner `-EBUSY` fault.",
        "- Static source-order gate binds cleanup, source recheck, work-copy, loop, mount, init validation, mount moves, exec, and failure cleanup.",
        "- Build performs the inherited AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot pack, and SHA256 capture.",
        "- No device, flash, mount, switch-root, network, userdata, or public-exposure action was performed by this H0 build.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `d3-immutable-handoff`.",
        "- Rollback baseline remains `v2321-usb-clean-identity-rodata`; no live authority is created by this build.",
    ]) + "\n"


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "d3-immutable-handoff.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "d3-immutable-handoff",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "source_report": base.rel(REPORT_PATH),
        "source_contract": base.rel(SOURCE_CONTRACT_PATH),
        "base_boot": base.rel(BASE_BOOT),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "d3_immutable_handoff": manifest["boot_audit"]["d3_immutable_handoff"],
        "adoption_state": "source-built-awaiting-fresh-rootfs-and-live-gate",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3403(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = ORIG_V3402_NORMALIZE_MANIFEST(manifest)
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "d3-immutable-handoff",
        "adoption_state": "source-built-awaiting-fresh-rootfs-and-live-gate",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_audit": _boot_audit_manifest(),
    })
    return manifest


def _patch_v3402_module_for_v3403() -> None:
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
        "OBSOLETE_RAMDISK_ENGINES": OBSOLETE_RAMDISK_ENGINES,
        "SOFTAP_COMMANDS": SOFTAP_COMMANDS,
        "render_report": render_report,
        "_rewrite_v3402_text": _rewrite_v3403_text,
        "_rewrite_v3402_bytes": _rewrite_v3403_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_normalize_manifest_for_v3402": _normalize_manifest_for_v3403,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def _patch_private_doom_source_for_v3403() -> None:
    doom_source.SOURCE_ROOT = PRIVATE_DOOM_SOURCE_ROOT
    doom_source.SOURCE_DIR = PRIVATE_DOOM_SOURCE_DIR
    doom_source.SOURCE_MAKEFILE = PRIVATE_DOOM_SOURCE_DIR / "Makefile.soso"


def _patch_recovered_legacy_inputs_for_v3403() -> None:
    legacy_v1693.V535_MANIFEST = RECOVERED_V535_MANIFEST


def main() -> int:
    _patch_private_doom_source_for_v3403()
    _patch_recovered_legacy_inputs_for_v3403()
    _patch_v3402_module_for_v3403()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
