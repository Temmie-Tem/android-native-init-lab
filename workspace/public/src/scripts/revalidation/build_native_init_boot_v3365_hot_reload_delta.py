#!/usr/bin/env python3
"""Build V3365 native-init boot image for H2 hot-reload delta validation.

Chains off V3364 (hot-reload fast path). This source unit intentionally changes only
the native-init version/build identity while preserving the reload command and the
A90_RELOADED fast path. Live H2 then stages the V3365 init ELF onto a V3364 resident
and proves the new code identity takes effect via reload without a reboot.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3364_hot_reload_fastpath as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3364_text
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3364_adapter_source
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3364_ramdisk
ORIG_PREVIOUS_FINALIZE = previous._finalize_manifest_after_overlay
ORIG_PREVIOUS_POSTPROCESS = previous._postprocess_manifest

CYCLE = "V3365"
INIT_VERSION = "0.11.126"
INIT_BUILD = "v3365-hot-reload-delta"
BUILD_TAG = INIT_BUILD
DECISION = "v3365-hot-reload-delta-source-build"
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
    / "NATIVE_INIT_V3365_HOT_RELOAD_DELTA_SOURCE_BUILD_2026-07-03.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3365_hot_reload_delta.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3365_hot_reload_delta"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3365_hot_reload_delta.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v629_hot_reload_delta"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3365"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3365.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3365.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3365"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3365-hot-reload-delta"

FRAME_PATH = "/tmp/a90-doomgeneric-v3365-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3365-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3365-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3365-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3365-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3365-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3365-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3365.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3365_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.125", INIT_VERSION),
        ("v3364-hot-reload-fastpath", INIT_BUILD),
        ("hot-reload-fastpath", "hot-reload-delta"),
        ("v3364", "v3365"),
        ("V3364", "V3365"),
        ("a90-doomgeneric-v3364", "a90-doomgeneric-v3365"),
        ("a90.doomgeneric.v3364", "a90.doomgeneric.v3365"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3365_bytes(item: bytes) -> bytes:
    return _rewrite_v3365_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3365_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3365_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3365_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3365_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(_rewrite_v3365_bytes(item) for item in previous.REQUIRED_STRINGS)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.126",
    b"v3365-hot-reload-delta",
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
    manifest["rung"] = "hot-reload-delta"
    manifest["scope"] = "H2-reload-genuinely-changed-init-version-marker"
    manifest["reload_contract"] = {
        "command": "reload INIT-RELOAD-EXECVE <staged-init-path> <expected-sha256>",
        "cmd_flags": "CMD_DANGEROUS | CMD_NO_DONE plus explicit token",
        "mechanism": "V3364 resident validates approved-staging path + ELF magic + SHA256, "
                     "then execve()s the V3365 init ELF in PID1",
        "h2_success": "post-reload version/build changes from V3364 to V3365 with no reboot, "
                      "no USB re-enumeration, and selftest fail=0",
        "safety": "no boot-partition write by this H2 candidate; failed execve leaves the old "
                  "resident running; a broken new init is recovered by reboot/TWRP rollback",
        "risk": "source build only; live H2 reload is a separately gated step",
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
        "# Native Init V3365 Hot-Reload Delta Source Build",
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
        "- H2 delta candidate: preserve V3364's `reload INIT-RELOAD-EXECVE` command and "
        "`A90_RELOADED` fast path, but bump the init identity to `0.11.126` / "
        "`v3365-hot-reload-delta`.",
        "- Live H2 will flash V3364 as the resident once, stage this V3365 init ELF under the "
        "approved SD staging root, then reload it to prove a genuinely changed native-init binary "
        "takes effect without rebooting or re-enumerating USB.",
        "- This candidate does not add a new boot-write primitive and does not require flashing "
        "V3365 for the proof; only the V3365 init ELF is staged as reload input.",
        "- Existing self-dd F0/F1/F2/F3 commands and the V3364 fast-path guards are preserved.",
        "",
        "## Validation Contract",
        "",
        "- Static PASS requires the V3365 version strings plus the reload markers (`A90RELOAD`, "
        "`INIT-RELOAD-EXECVE`, usage) and the fast-path marker to be present.",
        "- Live H2 PASS, separately gated, requires: V3364 resident boot health clean; staged V3365 "
        "init SHA matches the caller-pinned SHA; `reload` returns through the new init shell; "
        "`version` reports `0.11.126` / `v3365-hot-reload-delta`; `selftest fail=0`; then rollback "
        "to v2321 and health-check clean.",
        "- No live H2 reload result is claimed by this source-build report.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `hot-reload-delta`.",
    ]) + "\n"


def v3365_adapter_source() -> str:
    return _rewrite_v3365_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "hot-reload-delta.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "hot-reload-delta",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "reload_candidate_init_binary": base.rel(INIT_BINARY),
        "source_report": base.rel(REPORT_PATH),
        "resident_required_for_h2": "v3364-hot-reload-fastpath",
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "source-built-live-gated",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3365(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "hot-reload-delta",
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
    manifest = _normalize_manifest_for_v3365(json.loads(manifest_path.read_text(encoding="utf-8")))
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
    manifest = _normalize_manifest_for_v3365(ORIG_PREVIOUS_POSTPROCESS())
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


def _overlay_preserved_v3365_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3365-init-helper-engine"
    return overlay


def _patch_v3364_module_for_v3365() -> None:
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
        "v3364_adapter_source": v3365_adapter_source,
        "_rewrite_v3364_text": _rewrite_v3365_text,
        "_rewrite_v3364_bytes": _rewrite_v3365_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3364_ramdisk": _overlay_preserved_v3365_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3364_module_for_v3365()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
