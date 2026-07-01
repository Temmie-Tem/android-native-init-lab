#!/usr/bin/env python3
"""Build V3349 native-init §0.2 write-probe E1 with tail-slack zero-sector SCAN.

Same E1 command as V3348, but a90_boot_write_e1.c now scans the tail-slack window for the FIRST
all-zero 4096B sector (instead of a single fixed offset) and targets that — keeping both safety
layers (past parsed content AND confirmed-zero padding) while finding a real zero sector to probe.
Rollback baseline stays v2321.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3348_boot_write_e1 as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3348_text
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3348_ramdisk
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3348_adapter_source
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest

CYCLE = "V3349"
INIT_VERSION = "0.11.113"
INIT_BUILD = "v3349-boot-write-e1-scan"
BUILD_TAG = INIT_BUILD
DECISION = "v3349-boot-write-e1-scan-source-build-pass"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3349_BOOT_WRITE_E1_SCAN_SOURCE_BUILD_2026-07-02.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3349_boot_write_e1_scan.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3349_boot_write_e1_scan"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3349_boot_write_e1_scan.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v626_boot_write_e1_scan"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3349"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3349.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3349.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3349"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3349-boot-write-e1-scan"

FRAME_PATH = "/tmp/a90-doomgeneric-v3349-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3349-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3349-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3349-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3349-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3349-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3349-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3349.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG

SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3349_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.112", INIT_VERSION),
        ("v3348", "v3349"),
        ("V3348", "V3349"),
        ("a90-doomgeneric-v3348", "a90-doomgeneric-v3349"),
        ("a90.doomgeneric.v3348", "a90.doomgeneric.v3349"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3349_bytes(item: bytes) -> bytes:
    return _rewrite_v3349_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3349_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3349_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3349_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3349_text(previous.SOUND_MODE)


REQUIRED_STRINGS = tuple(_rewrite_v3349_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    b"0.11.113",
    b"v3349-boot-write-e1-scan",
    b"slack_scanned=%llu have_zero_sector=%d",
    b"stop=no-zero-slack",
)


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "boot-write-probe-E1-scan"
    manifest["scope"] = "0.2-write-probe-E1-tail-slack-zero-sector-scan-read-then-write-identical"
    manifest["probe_contract"]["target"] = "first all-zero 4096B sector in [roundup(used_len), size-1MiB)"
    reqs = list(manifest.get("pass_requirements", []))
    reqs = ["version-0.11.113" if r == "version-0.11.112" else r for r in reqs]
    manifest["pass_requirements"] = reqs
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
        "# Native Init V3349 §0.2 Write-Probe E1 Tail-Slack Zero-Sector Scan Source Build",
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
        "- `boot-write-e1` now SCANS the tail-slack window `[roundup(used_len), size - 1 MiB)` for the "
        "FIRST all-zero 4096B sector and targets it, instead of a single fixed offset. V3348 live "
        "showed the fixed tail offset held stale non-zero data, so the all-zero gate correctly "
        "refused (no write). The scan keeps both safety layers (past parsed content AND "
        "confirmed-zero) while finding a genuine zero sector to probe the first pwrite.",
        "- All other E1 safety properties are unchanged (CMD_DANGEROUS, token, fail-closed header, "
        "O_NOFOLLOW + identity on every fd, O_DIRECT region readback + full-partition SHA "
        "before/after, single pwrite of the confirmed-zero bytes it read).",
        "",
        "## Validation Contract",
        "",
        "- PASS requires post-flash `selftest fail=0`, `version` 0.11.113, and after a recovery drill "
        "+ `hide`, `boot-write-e1 BOOT-WRITE-PROBE-E1-TAILSLACK` emitting `have_zero_sector=1`, "
        "`slack_zero=1`, `pwrite_rc=4096` (or a clean refusal), `region_match=1`, `full_match=1`, "
        "then rollback to `v2321` with `selftest fail=0`. If `have_zero_sector=0` the probe stops "
        "with `no-zero-slack` and no write occurs.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `boot-write-e1-scan-candidate`.",
    ]) + "\n"


def v3349_adapter_source() -> str:
    return _rewrite_v3349_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "boot-write-e1-scan-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "boot-write-e1-scan-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "live_validation_focus": manifest["boot_audit"]["pass_requirements"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-boot-write-e1-scan-live-validation",
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
        "candidate_type": "boot-write-e1-scan-candidate",
        "adoption_state": "pending-boot-write-e1-scan-live-validation",
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
        "candidate_type": "boot-write-e1-scan-candidate",
        "adoption_state": "pending-boot-write-e1-scan-live-validation",
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


def _overlay_preserved_v3349_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3349-init-helper-engine"
    return overlay


def _patch_v3348_module_for_v3349() -> None:
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
        "v3348_adapter_source": v3349_adapter_source,
        "_rewrite_v3348_text": _rewrite_v3349_text,
        "_rewrite_v3348_bytes": _rewrite_v3349_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3348_ramdisk": _overlay_preserved_v3349_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3348_module_for_v3349()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
