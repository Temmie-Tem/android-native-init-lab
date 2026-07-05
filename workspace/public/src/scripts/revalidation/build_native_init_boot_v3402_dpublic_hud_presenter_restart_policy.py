#!/usr/bin/env python3
"""Build V3402 native-init boot image with D-public HUD restart policy."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3401_dpublic_hud_shared_run_bind as previous

base = previous.base
ORIG_V3401_REQUIRED_STRINGS = previous.REQUIRED_STRINGS
ORIG_V3401_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_V3401_NORMALIZE_MANIFEST = previous._normalize_manifest_for_v3401
ORIG_V3401_REWRITE_TEXT = previous._rewrite_v3401_text

CYCLE = "V3402"
INIT_VERSION = "0.11.158"
INIT_BUILD = "v3402-dpublic-hud-presenter-restart-policy"
BUILD_TAG = INIT_BUILD
DECISION = "v3402-dpublic-hud-presenter-restart-policy-source-build"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3402_DPUBLIC_HUD_PRESENTER_RESTART_POLICY_SOURCE_BUILD_2026-07-05.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3402_dpublic_hud_presenter_restart_policy.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3402_dpublic_hud_presenter_restart_policy"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3402_dpublic_hud_presenter_restart_policy.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v639_dpublic_hud_presenter_restart_policy"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3402"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3402.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3402.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3402"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3402-dpublic-hud-presenter-restart-policy"

FRAME_PATH = "/tmp/a90-doomgeneric-v3402-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3402-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3402-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3402-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3402-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3402-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3402-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3402.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3402_text(text: str) -> str:
    text = ORIG_V3401_REWRITE_TEXT(text)
    replacements = (
        ("v3401-dpublic-hud-shared-run-bind", INIT_BUILD),
        ("0.11.157", INIT_VERSION),
        ("V3401", CYCLE),
        ("v3401", "v3402"),
        ("a90-doomgeneric-v3401", "a90-doomgeneric-v3402"),
        ("a90.doomgeneric.v3401", "a90.doomgeneric.v3402"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3402_bytes(item: bytes) -> bytes:
    return _rewrite_v3402_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3402_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3402_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3402_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3402_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(
    _rewrite_v3402_bytes(marker) for marker in ORIG_V3401_REQUIRED_STRINGS
)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.158",
    b"v3402-dpublic-hud-presenter-restart-policy",
    b"A90WSTA146",
    b"restart-stop-start-stale-pid-cleanup",
    b"dpublic-hud-presenter-service [start|status|stop|restart]",
    b"start.stale_pid",
    b"status.restart_policy",
    b"restart.policy",
    b"restart.stop_rc",
    b"restart.start_rc",
    b"restart.done",
)

OBSOLETE_RAMDISK_ENGINES = tuple(dict.fromkeys([
    *previous.OBSOLETE_RAMDISK_ENGINES,
    "a90_doomgeneric_private_engine_v3401",
]))


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_V3401_BOOT_AUDIT_MANIFEST()
    service = manifest["dpublic_hud_presenter_service"]
    service["restart_policy"] = "restart-stop-start-stale-pid-cleanup"
    service["restart_command"] = True
    service["restart_releases_drm_before_start"] = True
    service["stale_pid_cleanup"] = True
    service["long_running_appliance_restart_policy"] = True
    manifest["rung"] = "dpublic-hud-presenter-restart-policy"
    manifest["scope"] = "native-root-owned-dpublic-hud-presenter-restart-policy"
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
        "# Native Init V3402 D-public HUD Presenter Restart Policy Source Build",
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
        "- Keeps the V3401 shared run-dir bind and stale-intent dedupe.",
        "- Adds `dpublic-hud-presenter-service restart` as stop-then-start.",
        "- Fails closed if the stop phase cannot release the old DRM owner.",
        "- Cleans stale pidfiles before a new start and records `stale-cleaned` status.",
        "- Adds live-visible marker `A90WSTA146 restart-stop-start-stale-pid-cleanup`.",
        "",
        "## Validation",
        "",
        "- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.",
        "- Static source checks: WSTA146 source/build tests.",
        "- No association, DHCP, ping, public exposure, userdata format/populate, switch-root, or live display action was performed by this source build.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `dpublic-hud-presenter-restart-policy`.",
    ]) + "\n"


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "dpublic-hud-presenter-restart-policy.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "dpublic-hud-presenter-restart-policy",
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


def _normalize_manifest_for_v3402(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = ORIG_V3401_NORMALIZE_MANIFEST(manifest)
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "dpublic-hud-presenter-restart-policy",
        "adoption_state": "source-built-awaiting-live-gate",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_audit": _boot_audit_manifest(),
    })
    return manifest


def _patch_v3401_module_for_v3402() -> None:
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
        "_rewrite_v3401_text": _rewrite_v3402_text,
        "_rewrite_v3401_bytes": _rewrite_v3402_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_normalize_manifest_for_v3401": _normalize_manifest_for_v3402,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3401_module_for_v3402()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
