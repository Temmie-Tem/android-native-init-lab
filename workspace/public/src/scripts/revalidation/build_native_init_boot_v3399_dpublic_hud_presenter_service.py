#!/usr/bin/env python3
"""Build V3399 native-init boot image with durable D-public HUD presenter service."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3398_dpublic_hud_presenter as previous

base = previous.base
ORIG_V3398_REQUIRED_STRINGS = previous.REQUIRED_STRINGS
ORIG_V3398_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_V3398_NORMALIZE_MANIFEST = previous._normalize_manifest_for_v3398
ORIG_V3398_REWRITE_TEXT = previous._rewrite_v3398_text

CYCLE = "V3399"
INIT_VERSION = "0.11.155"
INIT_BUILD = "v3399-dpublic-hud-presenter-service"
BUILD_TAG = INIT_BUILD
DECISION = "v3399-dpublic-hud-presenter-service-source-build"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3399_DPUBLIC_HUD_PRESENTER_SERVICE_SOURCE_BUILD_2026-07-05.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3399_dpublic_hud_presenter_service.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3399_dpublic_hud_presenter_service"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3399_dpublic_hud_presenter_service.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v638_dpublic_hud_presenter_service"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3399"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3399.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3399.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3399"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3399-dpublic-hud-presenter-service"

FRAME_PATH = "/tmp/a90-doomgeneric-v3399-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3399-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3399-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3399-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3399-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3399-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3399-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3399.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3399_text(text: str) -> str:
    text = ORIG_V3398_REWRITE_TEXT(text)
    replacements = (
        ("v3398-dpublic-hud-presenter", INIT_BUILD),
        ("0.11.154", INIT_VERSION),
        ("V3398", CYCLE),
        ("v3398", "v3399"),
        ("a90-doomgeneric-v3398", "a90-doomgeneric-v3399"),
        ("a90.doomgeneric.v3398", "a90.doomgeneric.v3399"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3399_bytes(item: bytes) -> bytes:
    return _rewrite_v3399_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3399_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3399_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3399_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3399_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(
    _rewrite_v3399_bytes(marker) for marker in ORIG_V3398_REQUIRED_STRINGS
)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.155",
    b"v3399-dpublic-hud-presenter-service",
    b"dpublic-hud-presenter-service",
    b"A90WSTA140",
    b"forked-native-child-survives-switch-root",
    b"preserve-dpublic-hud-presenter",
    b"start.done=1",
    b"stop.done=1",
    b"status.debian_direct_kms=0",
    b"survives_handoff=1",
)

OBSOLETE_RAMDISK_ENGINES = tuple(dict.fromkeys([
    *previous.OBSOLETE_RAMDISK_ENGINES,
    "a90_doomgeneric_private_engine_v3398",
]))


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_V3398_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "dpublic-hud-presenter-service"
    manifest["scope"] = "native-root-owned-dpublic-hud-presenter-service"
    manifest["dpublic_hud_presenter"]["command"] = (
        "dpublic-hud-presenter [validate|present] [intent-path]"
    )
    manifest["dpublic_hud_presenter_service"] = {
        "command": "dpublic-hud-presenter-service [start|status|stop] [options]",
        "service": "native-dpublic-hud-presenter",
        "process_model": "forked-native-child-survives-switch-root",
        "pid_file": "/run/a90-dpublic/hud-presenter.pid",
        "status_file": "/run/a90-dpublic/hud-presenter.status",
        "intent": "/run/a90-dpublic/hud-intent.json",
        "runtime_dir": "/run/a90-dpublic",
        "runtime_dir_owner": "root:a90hud",
        "runtime_dir_mode": "1770",
        "intent_file_mode": "0640",
        "poll_ms": 100,
        "stale_after_ms": 2000,
        "debian_direct_kms": False,
        "handoff_cleanup": "preserve-dpublic-hud-presenter-when-armed",
        "stop_releases_drm": True,
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
        "# Native Init V3399 D-public HUD Presenter Service Source Build",
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
        "- Adds native-init command `dpublic-hud-presenter-service [start|status|stop] [options]`.",
        "- `start` forks a native/root child presenter that watches the bounded HUD intent file.",
        "- `status` reports pid, intent path, status path, and whether the presenter owns a DRM fd.",
        "- `stop` terminates the presenter, removes the pidfile, and releases DRM by process exit.",
        "- Handoff cleanup preserves the armed durable presenter while still killing legacy unexpected native DRM holders.",
        "- Debian remains an intent producer and does not own direct KMS.",
        "",
        "## Validation",
        "",
        "- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.",
        "- Static source checks: WSTA140 source/build tests.",
        "- No association, DHCP, ping, public exposure, userdata mutation, switch-root, or live display action was performed by this source build.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `dpublic-hud-presenter-service`.",
    ]) + "\n"


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "dpublic-hud-presenter-service.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "dpublic-hud-presenter-service",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "source_report": base.rel(REPORT_PATH),
        "base_boot": base.rel(BASE_BOOT),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "dpublic_hud_presenter": manifest["boot_audit"]["dpublic_hud_presenter"],
        "dpublic_hud_presenter_service": manifest["boot_audit"]["dpublic_hud_presenter_service"],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3399(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = ORIG_V3398_NORMALIZE_MANIFEST(manifest)
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "dpublic-hud-presenter-service",
        "adoption_state": "source-built-awaiting-live-gate",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_audit": _boot_audit_manifest(),
    })
    return manifest


def _patch_v3398_module_for_v3399() -> None:
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
        "_rewrite_v3398_text": _rewrite_v3399_text,
        "_rewrite_v3398_bytes": _rewrite_v3399_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_normalize_manifest_for_v3398": _normalize_manifest_for_v3399,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3398_module_for_v3399()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
