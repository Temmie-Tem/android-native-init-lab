#!/usr/bin/env python3
"""Build V3401 native-init boot image with shared D-public HUD run-dir bind."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3400_dpublic_hud_presenter_service_dedupe as previous

base = previous.base
ORIG_V3400_REQUIRED_STRINGS = previous.REQUIRED_STRINGS
ORIG_V3400_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_V3400_NORMALIZE_MANIFEST = previous._normalize_manifest_for_v3400
ORIG_V3400_REWRITE_TEXT = previous._rewrite_v3400_text

CYCLE = "V3401"
INIT_VERSION = "0.11.157"
INIT_BUILD = "v3401-dpublic-hud-shared-run-bind"
BUILD_TAG = INIT_BUILD
DECISION = "v3401-dpublic-hud-shared-run-bind-source-build"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3401_DPUBLIC_HUD_SHARED_RUN_BIND_SOURCE_BUILD_2026-07-05.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3401_dpublic_hud_shared_run_bind.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3401_dpublic_hud_shared_run_bind"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3401_dpublic_hud_shared_run_bind.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v638_dpublic_hud_shared_run_bind"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3401"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3401.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3401.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3401"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3401-dpublic-hud-shared-run-bind"

FRAME_PATH = "/tmp/a90-doomgeneric-v3401-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3401-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3401-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3401-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3401-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3401-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3401-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3401.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3401_text(text: str) -> str:
    text = ORIG_V3400_REWRITE_TEXT(text)
    replacements = (
        ("v3400-dpublic-hud-presenter-service-dedupe", INIT_BUILD),
        ("0.11.156", INIT_VERSION),
        ("V3400", CYCLE),
        ("v3400", "v3401"),
        ("a90-doomgeneric-v3400", "a90-doomgeneric-v3401"),
        ("a90.doomgeneric.v3400", "a90.doomgeneric.v3401"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3401_bytes(item: bytes) -> bytes:
    return _rewrite_v3401_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3401_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3401_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3401_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3401_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(
    _rewrite_v3401_bytes(marker) for marker in ORIG_V3400_REQUIRED_STRINGS
)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.157",
    b"v3401-dpublic-hud-shared-run-bind",
    b"A90WSTA144",
    b"shared-run-dir-bind-before-switch-root",
    b"shared_run_bind=ok",
    b"stop=dpublic-hud-shared-run-bind",
)

OBSOLETE_RAMDISK_ENGINES = tuple(dict.fromkeys([
    *previous.OBSOLETE_RAMDISK_ENGINES,
    "a90_doomgeneric_private_engine_v3400",
]))


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_V3400_BOOT_AUDIT_MANIFEST()
    service = manifest["dpublic_hud_presenter_service"]
    service["shared_run_dir"] = "tmpfs-root-a90hud-1770"
    service["shared_run_dir_mount"] = True
    service["handoff_shared_run_bind"] = True
    service["handoff_shared_run_mode"] = "shared-run-dir-bind-before-switch-root"
    manifest["rung"] = "dpublic-hud-shared-run-bind"
    manifest["scope"] = "native-root-owned-dpublic-hud-presenter-shared-intent-run-dir"
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
        "# Native Init V3401 D-public HUD Shared Run Bind Source Build",
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
        "- Keeps the durable native HUD presenter service and stale-intent dedupe from V3400.",
        "- Mounts `/run/a90-dpublic` as a small tmpfs owned `root:a90hud` mode `1770`.",
        "- Binds that same run directory into the userdata Debian root before `switch_root`.",
        "- Fails closed before handoff if the shared run-dir bind cannot be established.",
        "- Adds live-visible marker `A90WSTA144 shared_run_dir=shared-run-dir-bind-before-switch-root`.",
        "",
        "## Validation",
        "",
        "- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.",
        "- Static source checks: WSTA144 source/build tests.",
        "- No association, DHCP, ping, public exposure, userdata format/populate, switch-root, or live display action was performed by this source build.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `dpublic-hud-shared-run-bind`.",
    ]) + "\n"


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "dpublic-hud-shared-run-bind.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "dpublic-hud-shared-run-bind",
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


def _normalize_manifest_for_v3401(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = ORIG_V3400_NORMALIZE_MANIFEST(manifest)
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "dpublic-hud-shared-run-bind",
        "adoption_state": "source-built-awaiting-live-gate",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_audit": _boot_audit_manifest(),
    })
    return manifest


def _patch_v3400_module_for_v3401() -> None:
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
        "_rewrite_v3400_text": _rewrite_v3401_text,
        "_rewrite_v3400_bytes": _rewrite_v3401_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_normalize_manifest_for_v3400": _normalize_manifest_for_v3401,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3400_module_for_v3401()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
