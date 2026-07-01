#!/usr/bin/env python3
"""Build V3347 native-init §0.2 write-probe rung E-open (open-only, NO write).

Adds the token-gated `boot-write-open-probe` command (a90_boot_write_probe.c): resolves the boot
partition from sysfs PARTNAME=boot, materializes the node, calls open(O_WRONLY) then close() with NO
write()/pwrite()/dd, confirms the fd identity, and unlinks the node. This answers half of §0.2 —
whether RKP permits a writable open of the boot block from normal-boot PID1 — with ZERO write risk.
Rollback baseline stays v2321.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3346_boot_audit_resolve as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3346_text
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3346_ramdisk
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3346_adapter_source

CYCLE = "V3347"
INIT_VERSION = "0.11.111"
INIT_BUILD = "v3347-boot-write-open-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3347-boot-write-open-probe-source-build-pass"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3347_BOOT_WRITE_OPEN_PROBE_SOURCE_BUILD_2026-07-02.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3347_boot_write_open_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3347_boot_write_open_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3347_boot_write_open_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v626_boot_write_open_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3347"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3347.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3347.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3347"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3347-boot-write-open-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3347-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3347-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3347-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3347-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3347-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3347-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3347-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3347.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG

SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3347_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.110", INIT_VERSION),
        ("v3346", "v3347"),
        ("V3346", "V3347"),
        ("a90-doomgeneric-v3346", "a90-doomgeneric-v3347"),
        ("a90.doomgeneric.v3346", "a90.doomgeneric.v3347"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3347_bytes(item: bytes) -> bytes:
    return _rewrite_v3347_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3347_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3347_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3347_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3347_text(previous.SOUND_MODE)


REQUIRED_STRINGS = tuple(_rewrite_v3347_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    b"0.11.111",
    b"v3347-boot-write-open-probe",
    b"A90BWOPEN begin",
    b"boot-write-open-probe <token>",
    b"BOOT-WRITE-OPEN-PROBE-E-OPEN",
    b"no_write_primitive=1",
)


def _boot_audit_manifest() -> dict[str, Any]:
    return {
        "rung": "boot-write-probe-E-open",
        "scope": "0.2-write-probe-open-only-no-write-boot-block-O_WRONLY-open-close",
        "commands": ["boot-audit", "boot-write-open-probe BOOT-WRITE-OPEN-PROBE-E-OPEN"],
        "expected_current_decisions": [DECISION],
        "probe_contract": {
            "rung": "E-open",
            "open_mode": "O_WRONLY|O_CLOEXEC|O_NONBLOCK",
            "write_syscalls": "none (no write/pwrite/dd/O_TRUNC/O_CREAT)",
            "token": "BOOT-WRITE-OPEN-PROBE-E-OPEN",
            "resolution": "sysfs PARTNAME=boot (single match) -> mknod -> open O_WRONLY -> close -> unlink",
            "identity_confirm": "block + rdev==sysfs + PARTNAME=boot + size==64MiB",
            "answers": "does RKP permit a writable open of the boot block from normal-boot PID1",
        },
        "pass_requirements": [
            "version-0.11.111",
            "post-flash-selftest-fail-0",
            "boot-write-open-probe-token-gated",
            "boot-write-open-probe-resolve-sysfs-partname",
            "boot-write-open-probe-open-wronly-result-recorded",
            "boot-write-open-probe-no-write-performed",
            "boot-write-open-probe-cleaned-1",
            "no-write-primitive-in-probe-source",
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
        "# Native Init V3347 §0.2 Write-Probe Rung E-open (open-only) Source Build",
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
        "- Adds the token-gated `boot-write-open-probe <token>` command (`a90_boot_write_probe.c`), "
        "the first rung (E-open) of the §0.2 write-probe ladder. It resolves the boot partition from "
        "sysfs `PARTNAME=boot`, materializes the node, calls `open(O_WRONLY)` then `close()` with "
        "**NO** `write`/`pwrite`/`dd`/`O_TRUNC`/`O_CREAT`, confirms the fd identity "
        "(block + rdev==sysfs + PARTNAME=boot + size==64MiB), and unlinks the node.",
        "- Answers half of §0.2 — whether RKP/the kernel permits a writable open of the boot block "
        "from normal-boot PID1 — with **zero bytes written**. `open_wronly=fail EROFS/EPERM` means "
        "blocked (keep TWRP); `open_wronly=ok` means writable open is permitted (advance the ladder).",
        "- The probe file contains no write primitive; verified in source.",
        "",
        "## Validation Contract",
        "",
        "- PASS requires post-flash `selftest fail=0`, `version` 0.11.111, and "
        "`boot-write-open-probe BOOT-WRITE-OPEN-PROBE-E-OPEN` emitting `rung=E-open`, "
        "`resolve=sysfs-partname`, a recorded `open_wronly=ok|fail`, `no_write_performed=1`, "
        "`cleaned=1`, then rollback to `v2321` with `selftest fail=0`.",
        "- No write to any partition. No vbmeta/AVB/PIT/bootloader/forbidden-partition access.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `boot-write-open-probe-candidate`.",
    ]) + "\n"


def v3347_adapter_source() -> str:
    return _rewrite_v3347_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "boot-write-open-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "boot-write-open-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "live_validation_focus": manifest["boot_audit"]["pass_requirements"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-boot-write-open-probe-live-validation",
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
        "candidate_type": "boot-write-open-probe-candidate",
        "adoption_state": "pending-boot-write-open-probe-live-validation",
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
        "candidate_type": "boot-write-open-probe-candidate",
        "adoption_state": "pending-boot-write-open-probe-live-validation",
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


def _overlay_preserved_v3347_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3347-init-helper-engine"
    return overlay


def _patch_v3346_module_for_v3347() -> None:
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
        "v3346_adapter_source": v3347_adapter_source,
        "_rewrite_v3346_text": _rewrite_v3347_text,
        "_rewrite_v3346_bytes": _rewrite_v3347_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3346_ramdisk": _overlay_preserved_v3347_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3346_module_for_v3347()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
