#!/usr/bin/env python3
"""Build V3371 native-init boot image for the server-distro D3B switch_root handoff."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3368_hot_reload_autohud as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3368_text
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3368_adapter_source
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3368_ramdisk
ORIG_PREVIOUS_FINALIZE = previous._finalize_manifest_after_overlay
ORIG_PREVIOUS_POSTPROCESS = previous._postprocess_manifest

CYCLE = "V3371"
INIT_VERSION = "0.11.132"
INIT_BUILD = "v3371-server-distro-switchroot-devprep"
BUILD_TAG = INIT_BUILD
DECISION = "v3371-server-distro-d3b-switchroot-devprep-source-build"
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
    / "NATIVE_INIT_V3371_SERVER_DISTRO_D3B_SWITCHROOT_DEVPREP_SOURCE_BUILD_2026-07-03.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3371_server_distro_switchroot_devprep.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3371_server_distro_switchroot_devprep"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3371_server_distro_switchroot_devprep.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v629_server_distro_switchroot"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3371"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3371.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3371.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3371"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3371-server-distro-switchroot-devprep"

FRAME_PATH = "/tmp/a90-doomgeneric-v3371-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3371-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3371-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3371-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3371-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3371-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3371-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3371.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3371_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.129", INIT_VERSION),
        ("v3368-hot-reload-autohud", INIT_BUILD),
        ("hot-reload-autohud", "server-distro-switchroot-devprep"),
        ("v3368", "v3371"),
        ("V3368", "V3371"),
        ("a90-doomgeneric-v3368", "a90-doomgeneric-v3371"),
        ("a90.doomgeneric.v3368", "a90.doomgeneric.v3371"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3371_bytes(item: bytes) -> bytes:
    return _rewrite_v3371_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3371_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3371_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3371_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3371_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(_rewrite_v3371_bytes(marker) for marker in previous.REQUIRED_STRINGS)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.132",
    b"v3371-server-distro-switchroot-devprep",
    b"switch-root-to-distro",
    b"SERVER-DISTRO-D3B-SWITCHROOT",
    b"A90D3B",
    b"/mnt/sdext/a90/runtime/",
    b"/mnt/sdext/a90/runtime/distro-root",
    b"loop_node_created=1",
    b"dev_mountpoint=0",
    b"dev_nodes=prepared",
    b"rootfs=unmounted-after-fail",
    b"exec_switch_root_now",
    b"expected_sha_match=1",
)


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "server-distro-d3b-switchroot"
    manifest["scope"] = "D3B-PID1-switch-root-to-SD-backed-Debian-sysvinit"
    manifest["server_distro_contract"] = {
        "command": "switch-root-to-distro SERVER-DISTRO-D3B-SWITCHROOT <image> <sha256>",
        "image_policy": "image path must live under /mnt/sdext/a90/runtime and match caller-pinned SHA-256",
        "handoff": "PID1 loop-mounts the ext4 image, moves /proc and /sys, prepares /dev nodes when /dev is not a mountpoint, then execve()s busybox switch_root",
        "proof": "D3A firstboot writes A90D3_MARKER and serves key-only dropbear over NCM; /proc/1/comm must be init",
        "recovery": "D3A rootfs mandatory bounded auto-reboot returns to this flashed candidate; live runner then rollback-flashes v2321",
        "guardrails": "boot partition only through native_init_flash.py; no userdata, no forbidden partition, no public tunnel",
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
        "# Native Init V3371 Server-Distro D3B Switchroot Devprep Source Build",
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
        "- Adds the gated PID1 command `switch-root-to-distro SERVER-DISTRO-D3B-SWITCHROOT <image> <sha256>`.",
        "- The command accepts only images under `/mnt/sdext/a90/runtime/`, rejects unpinned or mismatched SHA-256, loop-mounts the ext4 rootfs at `/mnt/sdext/a90/runtime/distro-root`, verifies `/sbin/init`, moves `/proc` and `/sys`, prepares `/dev` nodes when host `/dev` is not a mountpoint, then execs BusyBox `switch_root` so Debian sysvinit becomes PID1.",
        "- Keeps the V3370 loop-major parser fix and adds V3371 `/dev` preparation for the A90 native rootfs, where `/dev` is a plain rootfs directory rather than a movable mount.",
        "- Adds failure cleanup that unmounts the D3 rootfs before detaching the loop device on pre-handoff failures.",
        "- The command is registered as `CMD_DANGEROUS | CMD_NO_DONE`; a successful handoff intentionally has no normal serial END marker.",
        "- This is a D3B source-build/static gate only. Live D3B still requires the amended one checked boot flash, D3 image/key staging, SSH marker observation, mandatory auto-reboot, and rollback to v2321.",
        "",
        "## Static Validation Contract",
        "",
        "- Boot image strings must contain the V3371 identity, `switch-root-to-distro`, `SERVER-DISTRO-D3B-SWITCHROOT`, `A90D3B`, the approved SD runtime prefix, and the `exec_switch_root_now` marker.",
        "- Source contract must show the command table registration with `CMD_DANGEROUS | CMD_NO_DONE` and no `/data`/`userdata` write path in the D3 handoff module.",
        "- Live contract remains: exactly one D3 candidate flash via `native_init_flash.py`, Debian `A90D3_MARKER` over NCM SSH with `/proc/1/comm=init`, mandatory auto-reboot back to the candidate, then rollback flash to v2321 with `selftest fail=0`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `server-distro-d3b-switchroot`.",
    ]) + "\n"


def v3371_adapter_source() -> str:
    return _rewrite_v3371_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "server-distro-switchroot-devprep.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "server-distro-d3b-switchroot",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "switch_root_command": "switch-root-to-distro SERVER-DISTRO-D3B-SWITCHROOT <image> <sha256>",
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "source-built-live-gated",
        "d3_image_remote_prefix": "/mnt/sdext/a90/runtime/",
        "d3_root_mountpoint": "/mnt/sdext/a90/runtime/distro-root",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3371(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "server-distro-d3b-switchroot",
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
    manifest = _normalize_manifest_for_v3371(json.loads(manifest_path.read_text(encoding="utf-8")))
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
    manifest = _normalize_manifest_for_v3371(ORIG_PREVIOUS_POSTPROCESS())
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


def _overlay_preserved_v3371_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3371-init-helper-engine"
    return overlay


def _patch_v3368_module_for_v3371() -> None:
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
        "v3368_adapter_source": v3371_adapter_source,
        "_rewrite_v3368_text": _rewrite_v3371_text,
        "_rewrite_v3368_bytes": _rewrite_v3371_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3368_ramdisk": _overlay_preserved_v3371_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3368_module_for_v3371()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
