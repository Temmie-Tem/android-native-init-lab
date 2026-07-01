#!/usr/bin/env python3
"""Build V3351 native-init §0.2 E2 zero-population tail-slack identity rung.

V3350's fixed quarter-band selector refused cleanly when band 0 had no all-zero sector. V3351 keeps
the same E2 safety envelope but scans the whole tail-slack window, records the all-zero sector
population, and picks four spread indices from that population.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3350_boot_write_e2_multi as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3350_text
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3350_ramdisk
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3350_adapter_source
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest

CYCLE = "V3351"
INIT_VERSION = "0.11.115"
INIT_BUILD = "v3351-boot-write-e2-zero-population"
BUILD_TAG = INIT_BUILD
DECISION = "v3351-boot-write-e2-zero-population-source-build-pass"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3351_BOOT_WRITE_E2_ZERO_POPULATION_SOURCE_BUILD_2026-07-02.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3351_boot_write_e2_zero_population.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3351_boot_write_e2_zero_population"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3351_boot_write_e2_zero_population.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v626_boot_write_e2_zero_population"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3351"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3351.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3351.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3351"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3351-boot-write-e2-zero-population"

FRAME_PATH = "/tmp/a90-doomgeneric-v3351-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3351-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3351-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3351-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3351-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3351-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3351-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3351.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG

SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3351_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.114", INIT_VERSION),
        ("v3350", "v3351"),
        ("V3350", "V3351"),
        ("a90-doomgeneric-v3350", "a90-doomgeneric-v3351"),
        ("a90.doomgeneric.v3350", "a90.doomgeneric.v3351"),
        ("boot_write_e2_multi", "boot_write_e2_zero_population"),
        ("boot-write-e2-multi", "boot-write-e2-zero-population"),
        ("BOOT_WRITE_E2_MULTI", "BOOT_WRITE_E2_ZERO_POPULATION"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3351_bytes(item: bytes) -> bytes:
    return _rewrite_v3351_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3351_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3351_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3351_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3351_text(previous.SOUND_MODE)


PREVIOUS_REQUIRED_STRINGS = tuple(
    item for item in (_rewrite_v3351_bytes(item) for item in previous.REQUIRED_STRINGS)
    if item != b"tail-slack-4x4096-spread"
)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.115",
    b"v3351-boot-write-e2-zero-population",
    b"tail-slack-4x4096-zero-population",
    b"zero_candidates=%llu zero_stored=%u target_count=%u",
    b"selected%u_index=%u selected%u_off=%llu",
)


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "boot-write-probe-E2-zero-population"
    manifest["scope"] = "0.2-write-probe-E2-four-spread-all-zero-tail-slack-population"
    manifest["commands"] = ["boot-write-e2 BOOT-WRITE-PROBE-E2-MULTI-TAILSLACK"]
    manifest["probe_contract"] = {
        "rung": "E2",
        "token": "BOOT-WRITE-PROBE-E2-MULTI-TAILSLACK",
        "cmd_flags": "CMD_DANGEROUS (menu-settle required)",
        "write_syscall": "four pwrite calls of confirmed-zero 4096B tail-slack sectors",
        "target": "four spread indices from the all-zero sector population in [roundup(used_len), size-1MiB)",
        "safety_gates": "fail-closed header, every selected target>=used_len, every selected target all-zero, identity on every fd, O_NOFOLLOW",
        "verify": "O_DIRECT per-target readback memcmp + O_DIRECT full-partition SHA before/after",
        "risk": "UFS-tear residual is externally-recoverable (boot-only); operator must drill recovery first",
    }
    manifest["pass_requirements"] = [
        "version-0.11.115",
        "post-flash-selftest-fail-0",
        "boot-write-e2-token-and-menu-gated",
        "boot-write-e2-zero-candidates-at-least-4",
        "boot-write-e2-target-count-4",
        "boot-write-e2-all-selected-targets-slack-zero-1",
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
        "# Native Init V3351 §0.2 Write-Probe E2 Zero-Population Source Build",
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
        "- Revises `boot-write-e2 <token>` after the V3350 clean refusal. V3350 required one all-zero "
        "sector in each fixed quarter-band; live evidence showed band 0 had no zero sector, so the "
        "probe stopped before any write.",
        "- V3351 scans the whole tail-slack window, records all all-zero 4096B sector offsets, then "
        "selects four spread indices from that zero population. Each selected sector is re-read and "
        "rechecked as all-zero before any write fd is opened.",
        "- The rest of the safety envelope is unchanged: `CMD_DANGEROUS`, no auto-menu execution, "
        "O_NOFOLLOW + identity on every fd, one fsync after the four identity pwrite calls, O_DIRECT "
        "per-target readback, and O_DIRECT full-partition SHA before/after.",
        "",
        "## Validation Contract",
        "",
        "- PASS requires post-flash `selftest fail=0`, `version` 0.11.115, and after `hide`, "
        "`boot-write-e2 BOOT-WRITE-PROBE-E2-MULTI-TAILSLACK` emitting `zero_candidates>=4`, "
        "four `selectedN_off`/`targetN_off` lines, `pwrite_count=4` (or a clean refusal), "
        "`region_match_all=1`, `full_match=1`, then rollback to `v2321` with `selftest fail=0`.",
        "- This is a source-build preparation only; no live V3351 write is claimed here.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `boot-write-e2-zero-population-candidate`.",
    ]) + "\n"


def v3351_adapter_source() -> str:
    return _rewrite_v3351_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "boot-write-e2-zero-population-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "boot-write-e2-zero-population-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "live_validation_focus": manifest["boot_audit"]["pass_requirements"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-boot-write-e2-zero-population-live-validation",
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
        "candidate_type": "boot-write-e2-zero-population-candidate",
        "adoption_state": "pending-boot-write-e2-zero-population-live-validation",
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
        "candidate_type": "boot-write-e2-zero-population-candidate",
        "adoption_state": "pending-boot-write-e2-zero-population-live-validation",
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


def _overlay_preserved_v3351_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3351-init-helper-engine"
    return overlay


def _patch_v3350_module_for_v3351() -> None:
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
        "v3350_adapter_source": v3351_adapter_source,
        "_rewrite_v3350_text": _rewrite_v3351_text,
        "_rewrite_v3350_bytes": _rewrite_v3351_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3350_ramdisk": _overlay_preserved_v3351_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3350_module_for_v3351()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
