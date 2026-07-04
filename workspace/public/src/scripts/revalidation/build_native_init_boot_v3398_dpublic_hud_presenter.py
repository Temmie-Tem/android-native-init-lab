#!/usr/bin/env python3
"""Build V3398 native-init boot image with the D-public HUD presenter command."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3397_wsta_execute_gate_screen as previous

base = previous.base
ORIG_V3397_REQUIRED_STRINGS = previous.REQUIRED_STRINGS
ORIG_V3397_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_V3397_NORMALIZE_MANIFEST = previous._normalize_manifest_for_v3397
ORIG_V3397_REWRITE_TEXT = previous._rewrite_v3397_text

CYCLE = "V3398"
INIT_VERSION = "0.11.154"
INIT_BUILD = "v3398-dpublic-hud-presenter"
BUILD_TAG = INIT_BUILD
DECISION = "v3398-dpublic-hud-presenter-source-build"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3398_DPUBLIC_HUD_PRESENTER_SOURCE_BUILD_2026-07-05.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3398_dpublic_hud_presenter.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3398_dpublic_hud_presenter"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3398_dpublic_hud_presenter.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v638_dpublic_hud_presenter"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3398"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3398.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3398.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3398"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3398-dpublic-hud-presenter"

FRAME_PATH = "/tmp/a90-doomgeneric-v3398-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3398-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3398-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3398-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3398-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3398-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3398-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3398.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3398_text(text: str) -> str:
    text = ORIG_V3397_REWRITE_TEXT(text)
    replacements = (
        ("v3397-wsta-execute-gate-screen", INIT_BUILD),
        ("0.11.153", INIT_VERSION),
        ("V3397", CYCLE),
        ("v3397", "v3398"),
        ("a90-doomgeneric-v3397", "a90-doomgeneric-v3398"),
        ("a90.doomgeneric.v3397", "a90.doomgeneric.v3398"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3398_bytes(item: bytes) -> bytes:
    return _rewrite_v3398_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3398_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3398_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3398_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3398_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(
    _rewrite_v3398_bytes(marker) for marker in ORIG_V3397_REQUIRED_STRINGS
)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.154",
    b"v3398-dpublic-hud-presenter",
    b"dpublic-hud-presenter",
    b"A90WSTA136",
    b"a90-dpublic-hud-intent-v1",
    b"NATIVE ROOT PRESENTER OWNS KMS",
    b"presenter.debian_direct_kms=0",
    b"policy.forbidden_fields=reject",
    b"policy.unknown_fields=reject",
)

OBSOLETE_RAMDISK_ENGINES = tuple(dict.fromkeys([
    *previous.OBSOLETE_RAMDISK_ENGINES,
    "a90_doomgeneric_private_engine_v3397",
]))


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_V3397_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "dpublic-hud-presenter"
    manifest["scope"] = "native-root-owned-dpublic-hud-presenter"
    manifest["dpublic_hud_presenter"] = {
        "command": "dpublic-hud-presenter [validate|present] [intent-path]",
        "default_intent": "/run/a90-dpublic/hud-intent.json",
        "schema": "a90-dpublic-hud-intent-v1",
        "max_intent_bytes": 4096,
        "stale_after_ms": 2000,
        "owner": "native-init-root",
        "debian_direct_kms": False,
        "forbidden_fields": "reject",
        "unknown_fields": "reject",
        "presenter": "minimal native KMS HUD",
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
        "# Native Init V3398 D-public HUD Presenter Source Build",
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
        "- Adds native-init command `dpublic-hud-presenter [validate|present] [intent-path]`.",
        "- Reads a bounded `a90-dpublic-hud-intent-v1` JSON intent file.",
        "- Rejects stale intent, forbidden fields, and unknown top-level fields.",
        "- Presents a minimal native/root-owned KMS HUD; Debian remains an intent producer and does not own direct KMS.",
        "- Does not add Wi-Fi connect, DHCP, public tunnel, native reboot, flash behavior, or Debian direct DRM ownership.",
        "",
        "## Validation",
        "",
        "- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.",
        "- Static source checks: `tests.test_dpublic_smoke_helpers` and WSTA136 source proof.",
        "- No association, DHCP, ping, public exposure, userdata mutation, switch-root, or live display action was performed by this source build.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `dpublic-hud-presenter`.",
    ]) + "\n"


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "dpublic-hud-presenter.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "dpublic-hud-presenter",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "source_report": base.rel(REPORT_PATH),
        "base_boot": base.rel(BASE_BOOT),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "dpublic_hud_presenter": manifest["boot_audit"]["dpublic_hud_presenter"],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3398(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = ORIG_V3397_NORMALIZE_MANIFEST(manifest)
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "dpublic-hud-presenter",
        "adoption_state": "source-built-live-gated",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_audit": _boot_audit_manifest(),
    })
    return manifest


def _patch_v3397_module_for_v3398() -> None:
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
        "_rewrite_v3397_text": _rewrite_v3398_text,
        "_rewrite_v3397_bytes": _rewrite_v3398_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_normalize_manifest_for_v3397": _normalize_manifest_for_v3398,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3397_module_for_v3398()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
