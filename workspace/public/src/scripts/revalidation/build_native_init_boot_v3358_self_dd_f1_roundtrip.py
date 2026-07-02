#!/usr/bin/env python3
"""Build V3358 native-init self-dd F1 paired roundtrip source candidate."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3357_self_dd_f0_plan as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3357_text
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3357_adapter_source
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3357_ramdisk
ORIG_PREVIOUS_FINALIZE = previous._finalize_manifest_after_overlay
ORIG_PREVIOUS_POSTPROCESS = previous._postprocess_manifest

CYCLE = "V3358"
INIT_VERSION = "0.11.121"
INIT_BUILD = "v3358-self-dd-f1-roundtrip"
BUILD_TAG = INIT_BUILD
DECISION = "v3358-self-dd-f1-roundtrip-source-build-pass-live-policy-blocked"
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
    / "NATIVE_INIT_V3358_SELF_DD_F1_ROUNDTRIP_SOURCE_BUILD_2026-07-02.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3358_self_dd_f1_roundtrip.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3358_self_dd_f1_roundtrip"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3358_self_dd_f1_roundtrip.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v627_self_dd_f1_roundtrip"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3358"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3358.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3358.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3358"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3358-self-dd-f1-roundtrip"

FRAME_PATH = "/tmp/a90-doomgeneric-v3358-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3358-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3358-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3358-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3358-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3358-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3358-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3358.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3358_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.120", INIT_VERSION),
        ("v3357", "v3358"),
        ("V3357", "V3358"),
        ("a90-doomgeneric-v3357", "a90-doomgeneric-v3358"),
        ("a90.doomgeneric.v3357", "a90.doomgeneric.v3358"),
        ("self_dd_f0_plan", "self_dd_f1_roundtrip"),
        ("self-dd-f0-plan", "self-dd-f1-roundtrip"),
        ("SELF_DD_F0_PLAN", "SELF_DD_F1_ROUNDTRIP"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3358_bytes(item: bytes) -> bytes:
    return _rewrite_v3358_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3358_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3358_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3358_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3358_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(_rewrite_v3358_bytes(item) for item in previous.REQUIRED_STRINGS)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.121",
    b"v3358-self-dd-f1-roundtrip",
    b"A90BWF1",
    b"boot-flash-f1 <token> <candidate-path> <expected-sha256> <expected-version>",
    b"BOOT-FLASH-F1-PAIRED-ROUNDTRIP",
    b"paired-content-roundtrip",
    b"snapshot_path=%s snapshot_ready=1",
    b"snapshot_existing=%s refused=preserve-retained-snapshot",
    b"target_full_sha_after=%s target_full_match=%d",
    b"restore_full_sha_after=%s restore_full_match=%d",
    b"result=ok paired-roundtrip-restored",
)


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "self-dd-F1-paired-content-roundtrip"
    manifest["scope"] = "post-F0-content-changing-target-write-then-restore"
    manifest["commands"] = [
        "boot-flash-plan <candidate-path> <expected-sha256> <expected-version>",
        "boot-flash-f1 BOOT-FLASH-F1-PAIRED-ROUNDTRIP <candidate-path> <expected-sha256> <expected-version>",
    ]
    manifest["probe_contract"] = {
        "rung": "F1",
        "cmd_flags": "CMD_DANGEROUS plus explicit token",
        "write_syscall": "boot pwrite through existing guarded self-dd pwrite wrapper",
        "target": "guarded boot partition, source candidate from approved SD/cache staging root",
        "safety_gates": "F0-equivalent candidate SHA/version/header checks, before.full SD snapshot, target SHA verify, immediate restore SHA verify",
        "verify": "target_full_sha_after == target_full_sha, then restore_full_sha_after == before_full_sha",
        "risk": "content-changing source build only; live execution remains blocked until AGENTS.md policy gate is deliberately amended",
    }
    manifest["pass_requirements"] = [
        "version-0.11.121",
        "post-flash-selftest-fail-0",
        "boot-flash-plan-F0-pass-before-F1",
        "boot-flash-f1-token-accepted",
        "snapshot_match_before-1",
        "target_full_match-1",
        "restore_full_match-1",
        "result-ok-paired-roundtrip-restored",
        "post-probe-pstore-entries-0",
        "rollback-v2321-selftest-fail-0",
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
        "# Native Init V3358 Self-dd F1 Roundtrip Source Build",
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
        "- Adds `boot-flash-f1 BOOT-FLASH-F1-PAIRED-ROUNDTRIP <candidate-path> "
        "<expected-sha256> <expected-version>` as the first content-changing self-dd rung.",
        "- F1 repeats the F0 source-plan checks, captures `before.full` to the approved SD staging "
        "root, writes the planned full 64 MiB target image, verifies the target full SHA, then "
        "immediately restores `before.full` and verifies the restored full SHA before any reboot.",
        "- If a retained `before.full` snapshot already exists from a failed run, F1 refuses to "
        "overwrite it and stops before any target pwrite.",
        "- The command is `CMD_DANGEROUS` and token-gated. It is source-built only in this unit; live "
        "execution remains blocked by the policy gate in `AGENTS.md` and design section 12.1.",
        "",
        "## Validation Contract",
        "",
        "- Static PASS requires the V3358 strings, command registration, and token-gated F1 contract "
        "to be present, while preserving the existing F0 read-only source-plan command.",
        "- Live F1 PASS, when separately authorized, will require `target_full_match=1`, "
        "`restore_full_match=1`, `result=ok paired-roundtrip-restored`, pstore entries `0`, "
        "post-probe `selftest fail=0`, and clean v2321 rollback.",
        "- No live F1 content-changing write is claimed by this source-build report.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `self-dd-f1-roundtrip-candidate`.",
    ]) + "\n"


def v3358_adapter_source() -> str:
    return _rewrite_v3358_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "self-dd-f1-roundtrip-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "self-dd-f1-roundtrip-candidate",
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


def _normalize_manifest_for_v3358(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "self-dd-f1-roundtrip-candidate",
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
    manifest = _normalize_manifest_for_v3358(json.loads(manifest_path.read_text(encoding="utf-8")))
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
    manifest = _normalize_manifest_for_v3358(ORIG_PREVIOUS_POSTPROCESS())
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


def _overlay_preserved_v3358_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3358-init-helper-engine"
    return overlay


def _patch_v3357_module_for_v3358() -> None:
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
        "v3357_adapter_source": v3358_adapter_source,
        "_rewrite_v3357_text": _rewrite_v3358_text,
        "_rewrite_v3357_bytes": _rewrite_v3358_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3357_ramdisk": _overlay_preserved_v3358_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3357_module_for_v3358()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
