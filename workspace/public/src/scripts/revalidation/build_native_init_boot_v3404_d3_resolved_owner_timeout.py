#!/usr/bin/env python3
"""Build V3404 native-init boot image with bounded DRM-timeout resolution."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3403_d3_immutable_handoff as previous

base = previous.base
ORIG_V3403_REQUIRED_STRINGS = previous.REQUIRED_STRINGS
ORIG_V3403_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_V3403_NORMALIZE_MANIFEST = previous._normalize_manifest_for_v3403
ORIG_V3403_REWRITE_TEXT = previous._rewrite_v3403_text

CYCLE = "V3404"
INIT_VERSION = "0.11.160"
INIT_BUILD = "v3404-d3-resolved-owner-timeout"
BUILD_TAG = INIT_BUILD
DECISION = "v3404-d3-resolved-owner-timeout-source-build"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3404_D3_RESOLVED_OWNER_TIMEOUT_SOURCE_BUILD_2026-07-31.md"
)
SOURCE_CONTRACT_PATH = (
    REPO_ROOT
    / "workspace"
    / "public"
    / "src"
    / "scripts"
    / "revalidation"
    / "a90_d3_resolved_owner_timeout_v3404.py"
)
PRIVATE_DOOM_SOURCE_ROOT = previous.PRIVATE_DOOM_SOURCE_ROOT
PRIVATE_DOOM_SOURCE_DIR = previous.PRIVATE_DOOM_SOURCE_DIR
RECOVERED_V535_MANIFEST = previous.RECOVERED_V535_MANIFEST
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3404_d3_resolved_owner_timeout.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3404_d3_resolved_owner_timeout"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3404_d3_resolved_owner_timeout.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v641_d3_resolved_owner_timeout"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3404"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3404.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3404.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3404"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3404-d3-resolved-owner-timeout"

FRAME_PATH = "/tmp/a90-doomgeneric-v3404-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3404-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3404-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3404-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3404-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3404-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3404-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3404.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3404_text(text: str) -> str:
    text = ORIG_V3403_REWRITE_TEXT(text)
    replacements = (
        ("v3403-d3-immutable-handoff", INIT_BUILD),
        ("0.11.159", INIT_VERSION),
        ("V3403", CYCLE),
        ("v3403", "v3404"),
        ("a90-doomgeneric-v3403", "a90-doomgeneric-v3404"),
        ("a90.doomgeneric.v3403", "a90.doomgeneric.v3404"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3404_bytes(item: bytes) -> bytes:
    return _rewrite_v3404_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3404_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3404_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3404_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3404_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(
    _rewrite_v3404_bytes(marker) for marker in ORIG_V3403_REQUIRED_STRINGS
)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.160",
    b"v3404-d3-resolved-owner-timeout",
    b"owner_timeouts=%u resolved_by_zero_owner_scan=1",
)

OBSOLETE_RAMDISK_ENGINES = tuple(dict.fromkeys([
    *previous.OBSOLETE_RAMDISK_ENGINES,
    "a90_doomgeneric_private_engine_v3403",
]))


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_V3403_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "d3-resolved-owner-timeout"
    manifest["scope"] = "final-zero-owner-authoritative-for-owner-timeout-only"
    handoff = manifest["d3_immutable_handoff"]
    handoff["source_contract"] = base.rel(SOURCE_CONTRACT_PATH)
    handoff["owner_timeout_resolution"] = (
        "only strict D3 per-owner -EBUSY is deferred to the final DRM-owner rescan"
    )
    handoff["final_zero_owner_scan_resolves_owner_timeout"] = True
    handoff["service_scan_and_signal_errors_remain_fatal"] = True
    handoff["nonzero_final_owner_count_remains_fatal"] = True
    handoff["private_doom_source_pin"] = previous.doom_source.PINNED_COMMIT
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
        "# Native Init V3404 D3 Resolved Owner Timeout Source Build",
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
        "- Keeps V3403's immutable-source ordering, work-copy policy, and failure cleanup.",
        "- Defers only a strict-D3 per-owner `-EBUSY` to the existing authoritative final DRM-owner rescan.",
        "- Continues only when that scan succeeds with zero remaining non-preserved owners.",
        "- Preserves service failures, scan failures, non-timeout owner errors, and any nonzero final owner count.",
        "- Emits a bounded resolution marker without process identifiers.",
        "",
        "## Validation",
        "",
        "- Host-only error model covers resolved timeout, remaining owner, service, scan, and non-timeout owner failures.",
        "- Static source gate binds the narrow timeout branch before the final zero-owner decision.",
        "- Build performs the inherited AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot pack, and SHA256 capture.",
        "- No device, flash, mount, switch-root, network, userdata, or public-exposure action was performed by this H0 build.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `d3-resolved-owner-timeout`.",
        "- Rollback baseline remains `v2321-usb-clean-identity-rodata`; no live authority is created by this build.",
    ]) + "\n"


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "d3-resolved-owner-timeout.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "d3-resolved-owner-timeout",
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


def _normalize_manifest_for_v3404(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = ORIG_V3403_NORMALIZE_MANIFEST(manifest)
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "d3-resolved-owner-timeout",
        "adoption_state": "source-built-awaiting-fresh-rootfs-and-live-gate",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_audit": _boot_audit_manifest(),
    })
    return manifest


def _patch_v3403_module_for_v3404() -> None:
    replacements = {
        "CYCLE": CYCLE,
        "INIT_VERSION": INIT_VERSION,
        "INIT_BUILD": INIT_BUILD,
        "BUILD_TAG": BUILD_TAG,
        "DECISION": DECISION,
        "OUT_DIR": OUT_DIR,
        "OBJ_DIR": OBJ_DIR,
        "REPORT_PATH": REPORT_PATH,
        "SOURCE_CONTRACT_PATH": SOURCE_CONTRACT_PATH,
        "PRIVATE_DOOM_SOURCE_ROOT": PRIVATE_DOOM_SOURCE_ROOT,
        "PRIVATE_DOOM_SOURCE_DIR": PRIVATE_DOOM_SOURCE_DIR,
        "RECOVERED_V535_MANIFEST": RECOVERED_V535_MANIFEST,
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
        "_rewrite_v3403_text": _rewrite_v3404_text,
        "_rewrite_v3403_bytes": _rewrite_v3404_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_normalize_manifest_for_v3403": _normalize_manifest_for_v3404,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3403_module_for_v3404()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
