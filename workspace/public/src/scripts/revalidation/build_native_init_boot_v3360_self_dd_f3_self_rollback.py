#!/usr/bin/env python3
"""Build V3360 native-init self-dd F3 self-rollback source candidate."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3359_self_dd_f2_boot_candidate as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3359_text
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3359_adapter_source
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3359_ramdisk
ORIG_PREVIOUS_FINALIZE = previous._finalize_manifest_after_overlay
ORIG_PREVIOUS_POSTPROCESS = previous._postprocess_manifest

CYCLE = "V3360"
INIT_VERSION = "0.11.123"
INIT_BUILD = "v3360-self-dd-f3-self-rollback"
BUILD_TAG = INIT_BUILD
DECISION = "v3360-self-dd-f3-self-rollback-source-build-pass-live-policy-blocked"
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
    / "NATIVE_INIT_V3360_SELF_DD_F3_SELF_ROLLBACK_SOURCE_BUILD_2026-07-02.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3360_self_dd_f3_self_rollback.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3360_self_dd_f3_self_rollback"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3360_self_dd_f3_self_rollback.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v629_self_dd_f3_self_rollback"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3360"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3360.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3360.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3360"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3360-self-dd-f3-self-rollback"

FRAME_PATH = "/tmp/a90-doomgeneric-v3360-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3360-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3360-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3360-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3360-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3360-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3360-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3360.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3360_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.122", INIT_VERSION),
        ("v3359", "v3360"),
        ("V3359", "V3360"),
        ("a90-doomgeneric-v3359", "a90-doomgeneric-v3360"),
        ("a90.doomgeneric.v3359", "a90.doomgeneric.v3360"),
        ("self_dd_f2_boot_candidate", "self_dd_f3_self_rollback"),
        ("self-dd-f2-boot-candidate", "self-dd-f3-self-rollback"),
        ("SELF_DD_F2_BOOT_CANDIDATE", "SELF_DD_F3_SELF_ROLLBACK"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3360_bytes(item: bytes) -> bytes:
    return _rewrite_v3360_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3360_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3360_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3360_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3360_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(_rewrite_v3360_bytes(item) for item in previous.REQUIRED_STRINGS)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.123",
    b"v3360-self-dd-f3-self-rollback",
    b"A90BWF3",
    b"boot-flash-f3 <token> <candidate-path> <expected-sha256> <expected-version>",
    b"BOOT-FLASH-F3-SELF-ROLLBACK",
    b"self-rollback-write",
    b"snapshot_path=%s snapshot_ready=1",
    b"snapshot_retained=%s",
    b"target_full_sha_after=%s target_full_match=%d",
    b"restore_skipped=rollback-verified-host-reboot-required",
    b"reboot_required=1 host_must_reboot_now=1",
    b"result=ok rollback-written-ready-to-reboot",
)


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "self-dd-F3-self-rollback"
    manifest["scope"] = "post-F2-self-written-candidate-writes-v2321-target-then-host-reboot"
    manifest["commands"] = [
        "boot-flash-plan <candidate-path> <expected-sha256> <expected-version>",
        "boot-flash-f2 BOOT-FLASH-F2-BOOT-CANDIDATE <candidate-path> <expected-sha256> <expected-version>",
        "boot-flash-f3 BOOT-FLASH-F3-SELF-ROLLBACK <candidate-path> <expected-sha256> <expected-version>",
    ]
    manifest["probe_contract"] = {
        "rung": "F3",
        "cmd_flags": "CMD_DANGEROUS plus explicit token",
        "write_syscall": "boot pwrite through existing guarded self-dd pwrite wrapper",
        "target": "guarded boot partition, rollback image from approved SD/cache staging root",
        "safety_gates": "F0-equivalent rollback-image SHA/version/header checks, before.full SD snapshot, target SHA verify, host-controlled reboot only after rc=0",
        "verify": "target_full_sha_after == target_full_sha, then host reboots and verifies v2321",
        "failure_recovery": "if target write/readback fails after any target pwrite, attempt before.full restore before returning failure",
        "risk": "source build only; live execution remains blocked until AGENTS.md policy gate is deliberately amended",
    }
    manifest["pass_requirements"] = [
        "v3359-or-later-F2-boots-v3360-self-written-candidate",
        "version-0.11.123",
        "candidate-selftest-fail-0",
        "boot-flash-f3-token-accepted",
        "snapshot_match_before-1",
        "target_full_match-1",
        "result-ok-rollback-written-ready-to-reboot",
        "host-reboot-into-v2321",
        "v2321-version-marker-matches-target",
        "v2321-selftest-fail-0",
        "v2321-pstore-entries-0",
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
        "# Native Init V3360 Self-dd F3 Self-Rollback Source Build",
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
        "- Adds `boot-flash-f3 BOOT-FLASH-F3-SELF-ROLLBACK <candidate-path> "
        "<expected-sha256> <expected-version>` for the self-rollback rung.",
        "- F3 uses the same guarded leave-target primitive as F2, but it is intended to run from a "
        "candidate that was itself booted through F2. Its staged target is the v2321 rollback image.",
        "- On success, F3 returns a clean command END with `reboot_required=1` and retains the "
        "`before.full` snapshot. The host must immediately reboot and verify v2321.",
        "- On target-write or target-readback failure after any target pwrite, F3 attempts an "
        "immediate before.full restore before returning failure. It never reboots itself.",
        "- The command is `CMD_DANGEROUS` and token-gated. It is source-built only in this unit; "
        "live execution remains blocked by the F3 policy gate in `AGENTS.md` and design section 12.1.",
        "",
        "## Validation Contract",
        "",
        "- Static PASS requires the V3360 strings, command registration, and token-gated F3 contract "
        "to be present, while preserving the existing F0/F1/F2 commands.",
        "- Live F3 PASS, when separately authorized, will require F2 boot into V3360, F3 "
        "`target_full_match=1`, `result=ok rollback-written-ready-to-reboot`, reboot into v2321, "
        "v2321 `selftest fail=0`, pstore entries `0`, and retained-snapshot cleanup.",
        "- No live F3 self-rollback write or reboot into v2321 is claimed by this source-build report.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `self-dd-f3-self-rollback`.",
    ]) + "\n"


def v3360_adapter_source() -> str:
    return _rewrite_v3360_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "self-dd-f3-self-rollback.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "self-dd-f3-self-rollback",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "live_validation_focus": manifest["boot_audit"]["pass_requirements"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "source-built-live-policy-blocked",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3360(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "self-dd-f3-self-rollback",
        "adoption_state": "source-built-live-policy-blocked",
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
    manifest = _normalize_manifest_for_v3360(json.loads(manifest_path.read_text(encoding="utf-8")))
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
    manifest = _normalize_manifest_for_v3360(ORIG_PREVIOUS_POSTPROCESS())
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


def _overlay_preserved_v3360_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3360-init-helper-engine"
    return overlay


def _patch_v3359_module_for_v3360() -> None:
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
        "v3359_adapter_source": v3360_adapter_source,
        "_rewrite_v3359_text": _rewrite_v3360_text,
        "_rewrite_v3359_bytes": _rewrite_v3360_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3359_ramdisk": _overlay_preserved_v3360_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3359_module_for_v3360()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
