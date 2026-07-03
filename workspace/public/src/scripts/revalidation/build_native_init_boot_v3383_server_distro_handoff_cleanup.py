#!/usr/bin/env python3
"""Build V3383 native-init boot image for server-distro native handoff cleanup."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3381_server_distro_journaled_formatter as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3381_text
ORIG_PREVIOUS_REWRITE_BYTES = previous._rewrite_v3381_bytes
ORIG_PREVIOUS_REQUIRED_STRINGS = previous.REQUIRED_STRINGS
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_PREVIOUS_NORMALIZE_MANIFEST = previous._normalize_manifest_for_v3381

CYCLE = "V3383"
INIT_VERSION = "0.11.139"
INIT_BUILD = "v3383-server-distro-handoff-cleanup"
BUILD_TAG = INIT_BUILD
DECISION = "v3383-server-distro-native-handoff-cleanup-source-build"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3383_SERVER_DISTRO_HANDOFF_CLEANUP_SOURCE_BUILD_2026-07-04.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3383_server_distro_handoff_cleanup.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3383_server_distro_handoff_cleanup"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3383_server_distro_handoff_cleanup.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v631_server_distro_handoff_cleanup"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3383"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3383.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3383.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3383"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3383-server-distro-handoff-cleanup"

FRAME_PATH = "/tmp/a90-doomgeneric-v3383-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3383-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3383-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3383-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3383-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3383-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3383-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3383.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3383_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        ("v3381-server-distro-journaled-formatter", INIT_BUILD),
        ("server-distro-journaled-formatter", "server-distro-handoff-cleanup"),
        ("server-distro-d4c-journaled-formatter", "server-distro-d4d-handoff-cleanup"),
        ("d4c-journaled-formatter", "d4d-handoff-cleanup"),
        ("journaled-formatter", "handoff-cleanup"),
        ("0.11.138", INIT_VERSION),
        ("V3381", CYCLE),
        ("v3381", "v3383"),
        ("a90-doomgeneric-v3381", "a90-doomgeneric-v3383"),
        ("a90.doomgeneric.v3381", "a90.doomgeneric.v3383"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3383_bytes(item: bytes) -> bytes:
    return _rewrite_v3383_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3383_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3383_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3383_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3383_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(_rewrite_v3383_bytes(marker) for marker in ORIG_PREVIOUS_REQUIRED_STRINGS)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.139",
    b"v3383-server-distro-handoff-cleanup",
    b"handoff_display service=autohud stop_rc=%d",
    b"handoff_display drm_owner_pid=%ld action=term",
    b"handoff_display drm_owner_pid=%ld action=kill",
    b"handoff_display=done killed=%u rc=%d",
    b"stop=handoff-display-owner",
)


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "server-distro-d4d-handoff-cleanup"
    manifest["scope"] = "native-display-owner-cleanup-before-switch-root"
    manifest["server_distro_handoff_cleanup"] = {
        "tracked_service_stop": "a90_service_stop(A90_SERVICE_HUD, 3000)",
        "orphan_scan": "scan /proc for non-self /init processes holding DRM fds",
        "drm_fd_match": ["/dri/", "card0", "drm"],
        "signals": ["SIGTERM", "SIGKILL"],
        "fail_closed_marker": "stop=handoff-display-owner",
        "placement": "after root/init validation and before moving /proc /sys /dev",
        "paths": ["switch-root-to-distro", "switch-root-to-userdata"],
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
        "# Native Init V3383 Server-Distro Handoff Cleanup Source Build",
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
        "- Carries forward the V3381 D4 journaled formatter/userdata appliance surface.",
        "- Adds native server-distro display-owner cleanup before both D3 and D4 `switch_root` handoffs.",
        "- The cleanup stops the tracked `A90_SERVICE_HUD` service, scans `/proc` for non-self `/init` processes holding DRM fds, terminates those owners with bounded `SIGTERM` then `SIGKILL`, and fails closed with `stop=handoff-display-owner` if cleanup cannot complete.",
        "- Cleanup runs after the new root and init have already been validated, but before `/proc`, `/sys`, and `/dev` are moved into the new root.",
        "- Intended live proof: `switch-root-to-userdata` should emit `handoff_display` markers and Debian firstboot should no longer need to kill a native `/init` DRM holder.",
        "",
        "## Validation",
        "",
        "- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.",
        "- Static source checks: `tests.test_server_distro_native_handoff_cleanup`.",
        "- Builder regression: `tests.test_build_native_init_boot_v3383_server_distro_handoff_cleanup`.",
        "- Live validation is a separate gate; this report is the source/build artifact record.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `server-distro-d4d-handoff-cleanup`.",
    ]) + "\n"


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "server-distro-handoff-cleanup.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "server-distro-d4d-handoff-cleanup",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "source_report": base.rel(REPORT_PATH),
        "base_boot": base.rel(BASE_BOOT),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "handoff_cleanup": {
            "tracked_service_stop": "A90_SERVICE_HUD",
            "orphan_scan": "non-self /init DRM fd holders",
            "fail_closed_marker": "stop=handoff-display-owner",
        },
        "live_gate": "flash checked helper, run switch-root-to-userdata, verify handoff_display markers and Debian HUD",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3383(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_NORMALIZE_MANIFEST(manifest)
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "server-distro-d4d-handoff-cleanup",
        "adoption_state": "source-built-live-gated",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_audit": _boot_audit_manifest(),
    })
    return manifest


def _patch_v3381_module_for_v3383() -> None:
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
        "_rewrite_v3381_text": _rewrite_v3383_text,
        "_rewrite_v3381_bytes": _rewrite_v3383_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_normalize_manifest_for_v3381": _normalize_manifest_for_v3383,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3381_module_for_v3383()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
