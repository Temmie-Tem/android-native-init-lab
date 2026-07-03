#!/usr/bin/env python3
"""Build V3377 native-init boot image for the server-distro D4C formatter fix surface."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3368_hot_reload_autohud as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3368_text
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3368_adapter_source
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3368_ramdisk
ORIG_PREVIOUS_FINALIZE = previous._finalize_manifest_after_overlay
ORIG_PREVIOUS_POSTPROCESS = previous._postprocess_manifest

CYCLE = "V3377"
INIT_VERSION = "0.11.136"
INIT_BUILD = "v3377-server-distro-userdata-formatter-fix"
BUILD_TAG = INIT_BUILD
DECISION = "v3377-server-distro-d4c-userdata-formatter-fix-source-build"
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
    / "NATIVE_INIT_V3377_SERVER_DISTRO_D4C_FORMATTER_FIX_SOURCE_BUILD_2026-07-03.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3377_server_distro_userdata_formatter_fix.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3377_server_distro_userdata_formatter_fix"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3377_server_distro_userdata_formatter_fix.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v629_server_distro_switchroot"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3377"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3377.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3377.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3377"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3377-server-distro-userdata-formatter-fix"

FRAME_PATH = "/tmp/a90-doomgeneric-v3377-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3377-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3377-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3377-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3377-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3377-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3377-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3377.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3377_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.129", INIT_VERSION),
        ("v3368-hot-reload-autohud", INIT_BUILD),
        ("hot-reload-autohud", "server-distro-userdata-formatter-fix"),
        ("v3368", "v3377"),
        ("V3368", "V3377"),
        ("a90-doomgeneric-v3368", "a90-doomgeneric-v3377"),
        ("a90.doomgeneric.v3368", "a90.doomgeneric.v3377"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3377_bytes(item: bytes) -> bytes:
    return _rewrite_v3377_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3377_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3377_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3377_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3377_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(_rewrite_v3377_bytes(marker) for marker in previous.REQUIRED_STRINGS)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.136",
    b"v3377-server-distro-userdata-formatter-fix",
    b"switch-root-to-distro",
    b"SERVER-DISTRO-D3B-SWITCHROOT",
    b"A90D3B",
    b"userdata-appliance-preflight",
    b"userdata-appliance-formatter-probe",
    b"userdata-appliance-format",
    b"userdata-appliance-populate",
    b"switch-root-to-userdata",
    b"SERVER-DISTRO-D4-USERDATA-APPLIANCE",
    b"A90D4",
    b"/sys/class/block",
    b"PARTNAME=",
    b"/dev/block/a90-userdata",
    b"/mnt/a90-userdata-root",
    b"busybox-mke2fs",
    b"kbytes=",
    b"A90D4PROBE",
    b"formatter-probe=done",
    b"ext4-magic-ok",
    b"userdata_touched=0",
    b"userdata=appliance-root",
    b"target.source=partname-scan",
    b"format=done",
    b"populate=done",
    b"/mnt/sdext/a90/runtime/",
    b"/mnt/sdext/a90/runtime/distro-root",
    b"loop_node_created=1",
    b"dev_mountpoint=0",
    b"dev_nodes=prepared",
    b"rootfs=unmounted-after-fail",
    b"exec_switch_root_now",
    b"console=reuse-stdio",
    b"expected_sha_match=1",
)


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "server-distro-d4c-formatter-fix"
    manifest["scope"] = "D4C-entry-formatter-syntax-fix-surface"
    manifest["server_distro_contract"] = {
        "commands": [
            "userdata-appliance-preflight SERVER-DISTRO-D4-USERDATA-APPLIANCE",
            "userdata-appliance-formatter-probe SERVER-DISTRO-D4-USERDATA-APPLIANCE <probe-image> <size-bytes>",
            "userdata-appliance-format SERVER-DISTRO-D4-USERDATA-APPLIANCE <expected-devname> <expected-dev> <expected-sectors>",
            "userdata-appliance-populate SERVER-DISTRO-D4-USERDATA-APPLIANCE <source-tar> <sha256>",
            "switch-root-to-userdata SERVER-DISTRO-D4-USERDATA-APPLIANCE <expected-marker>",
        ],
        "target_policy": "derive exactly one PARTNAME=userdata from /sys/class/block, compare caller-pinned identity, materialize /dev/block/a90-userdata from verified MAJOR:MINOR only",
        "formatter_policy": "non-destructive probe formats an approved SD runtime regular file with the device-proven BusyBox mke2fs syntax, passes KBYTES for regular-file sizing, verifies ext magic, unlinks the probe, and never materializes userdata",
        "populate_policy": "source tar must live under /mnt/sdext/a90/runtime and match caller-pinned SHA-256",
        "handoff": "PID1 mounts the userdata root, verifies /etc/a90-appliance-stage and /sbin/init, moves /proc /sys /dev, then execve()s busybox switch_root",
        "guardrails": "boot partition flash only through native_init_flash.py; userdata is the only destructive D4 target; no forbidden partitions; no public tunnel",
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
        "# Native Init V3377 Server-Distro D4C Formatter Fix Source Build",
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
        "- Fixes `userdata-appliance-formatter-probe` to use the device-supported BusyBox syntax: `mke2fs -F -L A90D4PROBE <probe-image> <KBYTES>`.",
        "- Keeps the probe non-destructive: it writes only an approved SD-runtime regular file, checks the ext superblock magic, unlinks the probe file, and reports `userdata_touched=0`.",
        "- Keeps the D4B command surface: `userdata-appliance-preflight`, `userdata-appliance-format`, `userdata-appliance-populate`, and `switch-root-to-userdata`.",
        "- All D4 commands require `SERVER-DISTRO-D4-USERDATA-APPLIANCE`; mutating commands re-derive sysfs `PARTNAME=userdata` and compare host-pinned `devname`, `dev`, and `sectors` before touching storage.",
        "- The surface does not rely on `/dev/block/by-name/userdata`; it materializes `/dev/block/a90-userdata` from verified `MAJOR:MINOR` only after target identity passes.",
        "- Fixes the destructive format path to remove unsupported BusyBox `-t ext4`: `busybox mke2fs -F -L A90D4ROOT /dev/block/a90-userdata`.",
        "- Populate accepts only SHA-pinned source tarballs under `/mnt/sdext/a90/runtime/`, mounts userdata at `/mnt/a90-userdata-root`, extracts the rootfs, verifies `/sbin/init`, and writes `userdata=appliance-root`.",
        "- `switch-root-to-userdata` verifies the appliance marker, prepares/moves `/proc`, `/sys`, and `/dev`, then execs BusyBox `switch_root` so userdata Debian init becomes PID1.",
        "- This is a D4C entry-prep source-build/static gate. D4C format/populate still requires live formatter-probe pass, rootfs tarball staging, fresh same-session preflight, and rollback readiness.",
        "",
        "## Static Validation Contract",
        "",
        "- Boot image strings must contain the V3377 identity, all five D4 command names, `SERVER-DISTRO-D4-USERDATA-APPLIANCE`, `A90D4`, `/sys/class/block`, `PARTNAME=`, `userdata`, `/dev/block/a90-userdata`, `/mnt/a90-userdata-root`, and the formatter-probe/format/populate/switch markers.",
        "- Source contract must show command table registration with `CMD_DANGEROUS` on mutating D4 commands and `CMD_DANGEROUS | CMD_NO_DONE` on `switch-root-to-userdata`.",
        "- Live contract before destructive D4C: flash only through `native_init_flash.py`, prove candidate health, run device-side `userdata-appliance-preflight` plus `userdata-appliance-formatter-probe`, and roll back to v2321 unless the destructive D4C unit starts immediately under the same controlled plan.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `server-distro-d4c-formatter-fix`.",
    ]) + "\n"


def v3377_adapter_source() -> str:
    return _rewrite_v3377_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "server-distro-userdata-formatter-fix.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "server-distro-d4c-formatter-fix",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "d4_commands": [
            "userdata-appliance-preflight SERVER-DISTRO-D4-USERDATA-APPLIANCE",
            "userdata-appliance-formatter-probe SERVER-DISTRO-D4-USERDATA-APPLIANCE <probe-image> <size-bytes>",
            "userdata-appliance-format SERVER-DISTRO-D4-USERDATA-APPLIANCE <expected-devname> <expected-dev> <expected-sectors>",
            "userdata-appliance-populate SERVER-DISTRO-D4-USERDATA-APPLIANCE <source-tar> <sha256>",
            "switch-root-to-userdata SERVER-DISTRO-D4-USERDATA-APPLIANCE <expected-marker>",
        ],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "source-built-live-gated",
        "d4_source_remote_prefix": "/mnt/sdext/a90/runtime/",
        "d4_userdata_node": "/dev/block/a90-userdata",
        "d4_root_mountpoint": "/mnt/a90-userdata-root",
        "d4_marker": "userdata=appliance-root",
        "d4_formatter_probe": "/mnt/sdext/a90/runtime/<probe-image>",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3377(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "server-distro-d4c-formatter-fix",
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
    manifest = _normalize_manifest_for_v3377(json.loads(manifest_path.read_text(encoding="utf-8")))
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
    manifest = _normalize_manifest_for_v3377(ORIG_PREVIOUS_POSTPROCESS())
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


def _overlay_preserved_v3377_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3377-init-helper-engine"
    return overlay


def _patch_v3368_module_for_v3377() -> None:
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
        "v3368_adapter_source": v3377_adapter_source,
        "_rewrite_v3368_text": _rewrite_v3377_text,
        "_rewrite_v3368_bytes": _rewrite_v3377_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3368_ramdisk": _overlay_preserved_v3377_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3368_module_for_v3377()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
