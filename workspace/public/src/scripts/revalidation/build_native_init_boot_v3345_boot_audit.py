#!/usr/bin/env python3
"""Build V3345 native-init read-only boot-audit candidate.

Adds the §7.1 read-only boot-target auditor command (`boot-audit`, a90_boot_audit.c) on top of the
V3344 SoftAP S4 image. No write path: opens the boot block O_RDONLY, reads the first 4096 bytes, and
reports fd-derived identity as `A90BOOTAUDIT key=value` lines. Inherits the full V3344 surface
unchanged; only the init version and this command are added. Rollback baseline stays v2321.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3344_softap_s4_transfer_server as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3344_text
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3344_ramdisk
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3344_adapter_source

CYCLE = "V3345"
INIT_VERSION = "0.11.109"
INIT_BUILD = "v3345-boot-audit"
BUILD_TAG = INIT_BUILD
DECISION = "v3345-boot-audit-readonly-source-build-pass"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3345_BOOT_AUDIT_READONLY_SOURCE_BUILD_2026-07-02.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3345_boot_audit.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3345_boot_audit"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3345_boot_audit.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v626_boot_audit"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3345"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3345.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3345.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3345"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3345-boot-audit"

FRAME_PATH = "/tmp/a90-doomgeneric-v3345-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3345-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3345-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3345-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3345-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3345-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3345-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3345.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG

# Boot-audit adds no new SoftAP commands; keep the inherited surface unchanged.
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3345_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.108", INIT_VERSION),
        ("v3344", "v3345"),
        ("V3344", "V3345"),
        ("a90-doomgeneric-v3344", "a90-doomgeneric-v3345"),
        ("a90.doomgeneric.v3344", "a90.doomgeneric.v3345"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3345_bytes(item: bytes) -> bytes:
    return _rewrite_v3345_text(item.decode("utf-8")).encode("utf-8")


# Inherited doom/frame/sfx markers: keep the V3344 semantic names, apply only the version bump so
# they stay byte-consistent with the rewritten REQUIRED_STRINGS the deeper build layers verify.
FRAME_SCALE = _rewrite_v3345_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3345_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3345_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3345_text(previous.SOUND_MODE)


REQUIRED_STRINGS = tuple(_rewrite_v3345_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    b"0.11.109",
    b"v3345-boot-audit",
    b"boot-audit [target-path]",
    b"A90BOOTAUDIT begin",
)


def _boot_audit_manifest() -> dict[str, Any]:
    return {
        "rung": "boot-audit-readonly",
        "scope": "readonly-boot-target-auditor-self-dd-tool-7.1",
        "commands": ["boot-audit", "boot-audit /dev/block/by-name/boot"],
        "expected_current_decisions": [DECISION],
        "audit_contract": {
            "open_mode": "O_RDONLY|O_CLOEXEC|O_NONBLOCK",
            "read_probe_bytes": 4096,
            "write_path": "forbidden",
            "authoritative_target": "/dev/block/by-name/boot",
            "identity_source": "fd-derived (fstat st_rdev, BLKGETSIZE64, sysfs by rdev)",
            "canonical": "realpath-absolute-only",
        },
        "pass_requirements": [
            "version-0.11.109",
            "post-flash-selftest-fail-0",
            "boot-audit-open-ok",
            "boot-audit-read-ok",
            "boot-audit-authoritative-1",
            "boot-audit-partname-boot",
            "boot-audit-size-67108864",
            "no-write-primitive-in-source",
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
        "# Native Init V3345 Boot-Audit Read-Only Source Build",
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
        "- Adds the read-only `boot-audit [target-path]` native-init command (`a90_boot_audit.c`): "
        "opens the boot block `O_RDONLY|O_NONBLOCK`, reads the first 4096 bytes, and reports "
        "fd-derived identity (rdev, canonical via `realpath`, size, sector, PARTNAME, diskseq) as "
        "`A90BOOTAUDIT key=value` lines.",
        "- No write path: this is the §7.1 read-only auditor for the fast self-dd boot-flash tool "
        "(`docs/plans/FAST_SELF_DD_BOOT_FLASH_TOOL_DESIGN_2026-07-02.md`). It answers §0.1 (can "
        "native-init read `sda24` under RKP) and produces the host-confirmed `BootTargetPin`.",
        "- Non-default targets are flagged `authoritative=0` so the host wrapper never promotes them "
        "to a write-authorizing pin.",
        "- Inherits the full V3344 SoftAP S4 transfer-server surface unchanged; only the init "
        "version and this command are added.",
        "",
        "## Validation Contract",
        "",
        "- PASS requires post-flash `selftest fail=0`, `version` reporting 0.11.109, and `boot-audit` "
        "emitting `open=ok`, `read=ok`, `authoritative=1`, `partname=boot`, `size_bytes=67108864` "
        "for the default target.",
        "- Read-only: the command MUST NOT contain any write/dd/O_WRONLY path (verified in source). "
        "Rollback baseline is `v2321`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `boot-audit-readonly-candidate`.",
    ]) + "\n"


def v3345_adapter_source() -> str:
    return _rewrite_v3345_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "boot-audit-readonly-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "boot-audit-readonly-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "live_validation_focus": manifest["boot_audit"]["pass_requirements"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-boot-audit-readonly-live-validation",
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
        "candidate_type": "boot-audit-readonly-candidate",
        "adoption_state": "pending-boot-audit-readonly-live-validation",
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
        "candidate_type": "boot-audit-readonly-candidate",
        "adoption_state": "pending-boot-audit-readonly-live-validation",
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


def _overlay_preserved_v3345_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3345-init-helper-engine"
    return overlay


def _patch_v3344_module_for_v3345() -> None:
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
        "v3344_adapter_source": v3345_adapter_source,
        "_rewrite_v3344_text": _rewrite_v3345_text,
        "_rewrite_v3344_bytes": _rewrite_v3345_bytes,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3344_ramdisk": _overlay_preserved_v3345_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3344_module_for_v3345()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
