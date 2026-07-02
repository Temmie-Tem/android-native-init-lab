#!/usr/bin/env python3
"""Build V3364 native-init boot image adding the hot-reload (`reload`) command.

Chains off V3360 (self-dd F3). This unit adds a90_init_reload.c: a token+SHA+ELF-gated
`reload` command that replaces PID1 in place via execve() without a reboot. Source-build
only; live re-exec is a separately gated step.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3363_init_hot_reload as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3363_text
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3363_adapter_source
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3363_ramdisk
ORIG_PREVIOUS_FINALIZE = previous._finalize_manifest_after_overlay
ORIG_PREVIOUS_POSTPROCESS = previous._postprocess_manifest

CYCLE = "V3364"
INIT_VERSION = "0.11.125"
INIT_BUILD = "v3364-hot-reload-fastpath"
BUILD_TAG = INIT_BUILD
DECISION = "v3364-hot-reload-fastpath-source-build"
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
    / "NATIVE_INIT_V3364_HOT_RELOAD_FASTPATH_SOURCE_BUILD_2026-07-02.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3364_init_hot_reload.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3364_init_hot_reload"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3364_init_hot_reload.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v629_init_hot_reload"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3364"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3364.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3364.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3364"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3364-hot-reload-fastpath"

FRAME_PATH = "/tmp/a90-doomgeneric-v3364-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3364-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3364-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3364-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3364-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3364-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3364-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3364.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3364_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.124", INIT_VERSION),
        ("v3363", "v3364"),
        ("V3360", "V3364"),
        ("a90-doomgeneric-v3363", "a90-doomgeneric-v3364"),
        ("a90.doomgeneric.v3363", "a90.doomgeneric.v3364"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3364_bytes(item: bytes) -> bytes:
    return _rewrite_v3364_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3364_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3364_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3364_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3364_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(_rewrite_v3364_bytes(item) for item in previous.REQUIRED_STRINGS)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.125",
    b"v3364-hot-reload-fastpath",
    b"A90RELOAD",
    b"INIT-RELOAD-EXECVE",
    b"reload <token> <staged-init-path> <expected-sha256>",
    b"host_note=serial-persists-no-reboot",
    b"hot-reload fast-path (A90_RELOADED set)",
    b"reloaded fast-path: skip autohud/netservice/rshell re-init",
    b"Hot-reload: skipping autohud/netservice/rshell re-init (already live).",
)


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "hot-reload-fastpath"
    manifest["scope"] = "add-reload-command-execve-pid1-in-place-no-reboot"
    manifest["reload_contract"] = {
        "command": "reload INIT-RELOAD-EXECVE <staged-init-path> <expected-sha256>",
        "cmd_flags": "CMD_DANGEROUS | CMD_NO_DONE plus explicit token",
        "mechanism": "validate approved-staging path + ELF magic + SHA256, then execve() PID1 in place",
        "safety": "no reboot; USB gadget/configfs persists (idempotent setup, no UDC unbind); "
                  "failed execve leaves the old init running; broken new init that crashes early "
                  "panics PID1 and is recovered via reboot/TWRP",
        "risk": "source build only; live re-exec is a separately gated step",
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
        "# Native Init V3364 Hot-Reload Fast-Path Source Build",
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
        "- Adds `reload INIT-RELOAD-EXECVE <staged-init-path> <expected-sha256>` "
        "(a90_init_reload.c): replaces PID1 in place via execve() with NO reboot, to shorten the "
        "research flash cycle for init-only changes.",
        "- The USB gadget/configfs kernel state persists across execve (native-init gadget setup is "
        "idempotent and never unbinds the UDC), so the host serial link stays up and the new init "
        "comes straight back to a shell without a reboot or USB re-enumeration.",
        "- Token-gated, requires the candidate in the approved SD staging root, validates a "
        "caller-pinned SHA-256 and ELF magic before execve. A failed execve leaves the old init "
        "running. Registered `CMD_DANGEROUS | CMD_NO_DONE`.",
        "- Existing self-dd F0/F1/F2/F3 commands are preserved.",
        "",
        "## Validation Contract",
        "",
        "- Static PASS requires the V3364 version strings plus the reload markers (`A90RELOAD`, "
        "`INIT-RELOAD-EXECVE`, usage) to be present while preserving the prior command surface.",
        "- Live H0 PASS, separately gated, will require: flash V3364, stage its own init ELF, "
        "`reload` it, prove the serial device never re-enumerates (no reboot), native-init uptime "
        "resets (init restarted), `selftest fail=0`, and the reload completes far under a reboot.",
        "- No live re-exec is claimed by this source-build report.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `hot-reload-fastpath`.",
    ]) + "\n"


def v3364_adapter_source() -> str:
    return _rewrite_v3364_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "hot-reload-fastpath.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "hot-reload-fastpath",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "source-built-live-gated",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3364(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "hot-reload-fastpath",
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
    manifest = _normalize_manifest_for_v3364(json.loads(manifest_path.read_text(encoding="utf-8")))
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
    manifest = _normalize_manifest_for_v3364(ORIG_PREVIOUS_POSTPROCESS())
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


def _overlay_preserved_v3364_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3364-init-helper-engine"
    return overlay


def _patch_v3363_module_for_v3364() -> None:
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
        "v3363_adapter_source": v3364_adapter_source,
        "_rewrite_v3363_text": _rewrite_v3364_text,
        "_rewrite_v3363_bytes": _rewrite_v3364_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3363_ramdisk": _overlay_preserved_v3364_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3363_module_for_v3364()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
