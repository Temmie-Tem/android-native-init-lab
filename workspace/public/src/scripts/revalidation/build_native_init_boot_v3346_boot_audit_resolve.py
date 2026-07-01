#!/usr/bin/env python3
"""Build V3346 native-init boot-audit auditor with sysfs PARTNAME=boot resolution.

Extends the V3345 read-only auditor: with no explicit target and no /dev/block/by-name/boot symlink
(native-init), `boot-audit` now scans /sys/class/block for the SINGLE partition with PARTNAME=boot,
materializes /dev/block/<X> via mknod, audits it O_RDONLY, cross-checks the fd rdev against the
sysfs-resolved major:minor, and unlinks the node — emitting authoritative=1 so the host wrapper can
propose a confirmed BootTargetPin. A duplicate PARTNAME=boot is refused (ambiguous). Still no
partition write. Rollback baseline stays v2321.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3345_boot_audit as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3345_text
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3345_ramdisk
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3345_adapter_source

CYCLE = "V3346"
INIT_VERSION = "0.11.110"
INIT_BUILD = "v3346-boot-audit-resolve"
BUILD_TAG = INIT_BUILD
DECISION = "v3346-boot-audit-resolve-source-build-pass"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3346_BOOT_AUDIT_RESOLVE_SOURCE_BUILD_2026-07-02.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3346_boot_audit_resolve.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3346_boot_audit_resolve"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3346_boot_audit_resolve.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v626_boot_audit_resolve"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3346"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3346.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3346.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3346"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3346-boot-audit-resolve"

FRAME_PATH = "/tmp/a90-doomgeneric-v3346-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3346-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3346-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3346-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3346-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3346-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3346-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3346.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG

SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3346_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.109", INIT_VERSION),
        ("v3345", "v3346"),
        ("V3345", "V3346"),
        ("a90-doomgeneric-v3345", "a90-doomgeneric-v3346"),
        ("a90.doomgeneric.v3345", "a90.doomgeneric.v3346"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3346_bytes(item: bytes) -> bytes:
    return _rewrite_v3346_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3346_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3346_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3346_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3346_text(previous.SOUND_MODE)


REQUIRED_STRINGS = tuple(_rewrite_v3346_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    b"0.11.110",
    b"v3346-boot-audit-resolve",
    b"sysfs-partname",
    b"A90BOOTAUDIT resolve=%s",
)


def _boot_audit_manifest() -> dict[str, Any]:
    return {
        "rung": "boot-audit-readonly-resolve",
        "scope": "readonly-boot-target-auditor-sysfs-partname-resolve-materialize-7.1",
        "commands": ["boot-audit", "boot-audit /dev/block/by-name/boot"],
        "expected_current_decisions": [DECISION],
        "audit_contract": {
            "open_mode": "O_RDONLY|O_CLOEXEC|O_NONBLOCK",
            "read_probe_bytes": 4096,
            "write_path": "forbidden",
            "resolution": "sysfs PARTNAME=boot (single match) -> mknod materialize -> audit -> unlink",
            "ambiguous_partname": "refused-fail-closed",
            "identity_source": "fd-derived (fstat st_rdev, BLKGETSIZE64) cross-checked vs sysfs rdev",
            "canonical": "realpath-absolute-only",
        },
        "pass_requirements": [
            "version-0.11.110",
            "post-flash-selftest-fail-0",
            "boot-audit-resolve-sysfs-partname",
            "boot-audit-materialized-1",
            "boot-audit-open-ok",
            "boot-audit-read-ok",
            "boot-audit-authoritative-1",
            "boot-audit-partname-boot",
            "boot-audit-size-67108864",
            "boot-audit-cleaned-1",
            "no-partition-write-primitive-in-source",
            "rollback-v2321-selftest-fail-0",
        ],
    }


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    boot_image = manifest.get("boot_image", base.rel(BOOT_IMAGE))
    boot_sha = manifest.get("boot_sha256", "")
    helper_sha = manifest.get("helper_sha256", "")
    return "\n".join([
        "# Native Init V3346 Boot-Audit sysfs-PARTNAME Resolve Source Build",
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
        "- `boot-audit` with no explicit target now resolves the boot partition from sysfs: it scans "
        "`/sys/class/block/<X>/uevent` for the SINGLE partition with `PARTNAME=boot`, materializes "
        "`/dev/block/<X>` via `mknod` (device node in /dev tmpfs, NOT a partition write), audits it "
        "`O_RDONLY`, cross-checks the fd `st_rdev` against the sysfs major:minor, and `unlink`s the "
        "node. Only a unique authoritative resolution emits `authoritative=1`.",
        "- A duplicate `PARTNAME=boot` (>1 match) is refused fail-closed (`resolve=ambiguous`). An "
        "rdev mismatch on a pre-existing node downgrades to `authoritative=0`.",
        "- This closes the last read-only precondition: the host wrapper can now propose a confirmed "
        "`BootTargetPin` from a real native-init `boot-audit` run. Still NO partition write.",
        "",
        "## Validation Contract",
        "",
        "- PASS requires post-flash `selftest fail=0`, `version` 0.11.110, and no-arg `boot-audit` "
        "emitting `resolve=sysfs-partname`, `materialized=1`, `open=ok`, `read=ok`, "
        "`authoritative=1`, `partname=boot`, `size_bytes=67108864`, `cleaned=1`.",
        "- Read-only: NO write/dd/O_WRONLY on the partition (verified in source). Rollback is `v2321`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `boot-audit-resolve-readonly-candidate`.",
    ]) + "\n"


def v3346_adapter_source() -> str:
    return _rewrite_v3346_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "boot-audit-resolve-readonly-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "boot-audit-resolve-readonly-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "live_validation_focus": manifest["boot_audit"]["pass_requirements"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-boot-audit-resolve-readonly-live-validation",
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
        "candidate_type": "boot-audit-resolve-readonly-candidate",
        "adoption_state": "pending-boot-audit-resolve-readonly-live-validation",
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
        "candidate_type": "boot-audit-resolve-readonly-candidate",
        "adoption_state": "pending-boot-audit-resolve-readonly-live-validation",
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


def _overlay_preserved_v3346_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3346-init-helper-engine"
    return overlay


def _patch_v3345_module_for_v3346() -> None:
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
        "v3345_adapter_source": v3346_adapter_source,
        "_rewrite_v3345_text": _rewrite_v3346_text,
        "_rewrite_v3345_bytes": _rewrite_v3346_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3345_ramdisk": _overlay_preserved_v3346_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3345_module_for_v3346()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
