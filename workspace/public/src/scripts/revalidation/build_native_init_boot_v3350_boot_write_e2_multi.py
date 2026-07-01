#!/usr/bin/env python3
"""Build V3350 native-init §0.2 write-probe E2 multi-offset tail-slack identity rung.

Extends the V3349 E1 scan command set with `boot-write-e2`: four spread 4096B targets in confirmed
zero tail slack, all read-then-write-identical, one fsync, O_DIRECT per-region readback, and
O_DIRECT full-partition SHA before/after. Rollback baseline stays v2321.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3349_boot_write_e1_scan as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3349_text
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3349_ramdisk
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3349_adapter_source
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest

CYCLE = "V3350"
INIT_VERSION = "0.11.114"
INIT_BUILD = "v3350-boot-write-e2-multi"
BUILD_TAG = INIT_BUILD
DECISION = "v3350-boot-write-e2-multi-source-build-pass"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3350_BOOT_WRITE_E2_MULTI_SOURCE_BUILD_2026-07-02.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3350_boot_write_e2_multi.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3350_boot_write_e2_multi"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3350_boot_write_e2_multi.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v626_boot_write_e2_multi"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3350"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3350.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3350.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3350"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3350-boot-write-e2-multi"

FRAME_PATH = "/tmp/a90-doomgeneric-v3350-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3350-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3350-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3350-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3350-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3350-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3350-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3350.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG

SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3350_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.113", INIT_VERSION),
        ("v3349", "v3350"),
        ("V3349", "V3350"),
        ("a90-doomgeneric-v3349", "a90-doomgeneric-v3350"),
        ("a90.doomgeneric.v3349", "a90.doomgeneric.v3350"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3350_bytes(item: bytes) -> bytes:
    return _rewrite_v3350_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3350_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3350_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3350_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3350_text(previous.SOUND_MODE)


PREVIOUS_REQUIRED_STRINGS = tuple(
    item for item in (_rewrite_v3350_bytes(item) for item in previous.REQUIRED_STRINGS)
    if item != b"A90BWE1 begin"
)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.114",
    b"v3350-boot-write-e2-multi",
    b"A90BWE1",
    b"A90BWE2",
    b"boot-write-e2 <token>",
    b"BOOT-WRITE-PROBE-E2-MULTI-TAILSLACK",
    b"tail-slack-4x4096-spread",
    b"pwrite_count=%u pwrite=ok fsync=ok",
    b"region_match_all=%d",
)


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "boot-write-probe-E2-multi-offset"
    manifest["scope"] = "0.2-write-probe-E2-four-spread-tail-slack-sectors-read-then-write-identical"
    manifest["commands"] = ["boot-write-e2 BOOT-WRITE-PROBE-E2-MULTI-TAILSLACK"]
    manifest["probe_contract"] = {
        "rung": "E2",
        "token": "BOOT-WRITE-PROBE-E2-MULTI-TAILSLACK",
        "cmd_flags": "CMD_DANGEROUS (menu-settle required)",
        "write_syscall": "four pwrite calls of confirmed-zero 4096B tail-slack sectors",
        "target": "one all-zero sector from each quarter of [roundup(used_len), size-1MiB)",
        "safety_gates": "fail-closed header, every target>=used_len, all targets all-zero, identity on every fd, O_NOFOLLOW",
        "verify": "O_DIRECT per-target readback memcmp + O_DIRECT full-partition SHA before/after",
        "risk": "UFS-tear residual is externally-recoverable (boot-only); operator must drill recovery first",
    }
    manifest["pass_requirements"] = [
        "version-0.11.114",
        "post-flash-selftest-fail-0",
        "boot-write-e2-token-and-menu-gated",
        "boot-write-e2-target-count-4",
        "boot-write-e2-all-targets-slack-zero-1",
        "boot-write-e2-pwrite-count-4-or-clean-refusal",
        "boot-write-e2-region-match-all-1-if-written",
        "boot-write-e2-full-match-1",
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
        "# Native Init V3350 §0.2 Write-Probe E2 Multi-Offset Source Build",
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
        "- Adds the token-gated `boot-write-e2 <token>` command for the E2 rung. It reuses the E1 "
        "guarded write path but selects four spread 4096B targets in confirmed-zero tail slack, one "
        "from each quarter of `[roundup(used_len), size - 1 MiB)`.",
        "- Every selected sector is read first and must be all-zero. The command writes only those "
        "same bytes back to the same offsets, fsyncs once, verifies each target with O_DIRECT "
        "readback, and compares O_DIRECT full-partition SHA before/after.",
        "- `boot-write-e2` is `CMD_DANGEROUS`, not menu-allowed, and requires explicit hide/menu-settle "
        "before dispatch. This is a source-build preparation only; no live write is claimed here.",
        "",
        "## Validation Contract",
        "",
        "- PASS requires post-flash `selftest fail=0`, `version` 0.11.114, and after a recovery drill "
        "+ `hide`, `boot-write-e2 BOOT-WRITE-PROBE-E2-MULTI-TAILSLACK` emitting `target_count=4`, "
        "four `targetN_off` lines with `slack_zero=1`, `pwrite_count=4` (or a clean refusal), "
        "`region_match_all=1`, `full_match=1`, then rollback to `v2321` with `selftest fail=0`.",
        "- The AGENTS checked-helper flash path remains the only path used to install this candidate; "
        "the E2 live command itself remains separately operator-gated because it performs boot-block "
        "identity writes under the self-dd experiment.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `boot-write-e2-multi-candidate`.",
    ]) + "\n"


def v3350_adapter_source() -> str:
    return _rewrite_v3350_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "boot-write-e2-multi-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "boot-write-e2-multi-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "live_validation_focus": manifest["boot_audit"]["pass_requirements"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-boot-write-e2-multi-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


_STALE_MANIFEST_KEYS = (
    "gpu_d3", "gpu_h1", "gpu_m0", "gpu_m1", "gpu_m2", "gpu_m3", "gpu_z2", "gpu_z3",
    "softap_s2", "softap_s4",
)


def _finalize_manifest_after_overlay(
    overlay: dict[str, Any],
    *,
    base_main_completed: bool,
    base_main_error: str | None = None,
) -> None:
    manifest_path = OUT_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {
            "helper_sha256": base.sha256_file(HELPER_BINARY),
            "helper_flags": [SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG],
            "init_extra_flags": [],
        }
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "boot-write-e2-multi-candidate",
        "adoption_state": "pending-boot-write-e2-multi-live-validation",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_sha256": overlay["boot_sha256"],
        "ramdisk_sha256": overlay["ramdisk_sha256"],
        "ramdisk_overlay": overlay,
        "base_main_completed": base_main_completed,
        "helper_flags": list(dict.fromkeys([
            *manifest.get("helper_flags", []),
            SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG,
        ])),
        "boot_audit": _boot_audit_manifest(),
    })
    if base_main_error:
        manifest["base_main_error"] = base_main_error
    else:
        manifest.pop("base_main_error", None)
    for key in _STALE_MANIFEST_KEYS:
        manifest.pop(key, None)
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
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("base_main_error", None)
    for key in _STALE_MANIFEST_KEYS:
        manifest.pop(key, None)
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "boot-write-e2-multi-candidate",
        "adoption_state": "pending-boot-write-e2-multi-live-validation",
        "helper_flags": list(dict.fromkeys([
            *manifest.get("helper_flags", []),
            SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG,
        ])),
        "boot_audit": _boot_audit_manifest(),
    })
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


def _overlay_preserved_v3350_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3350-init-helper-engine"
    return overlay


def _patch_v3349_module_for_v3350() -> None:
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
        "v3349_adapter_source": v3350_adapter_source,
        "_rewrite_v3349_text": _rewrite_v3350_text,
        "_rewrite_v3349_bytes": _rewrite_v3350_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3349_ramdisk": _overlay_preserved_v3350_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3349_module_for_v3350()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
