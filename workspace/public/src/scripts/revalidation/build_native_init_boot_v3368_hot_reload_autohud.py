#!/usr/bin/env python3
"""Build V3368 native-init boot image for H5 hot-reload autohud refresh.

Chains off V3367 (hot-reload tcpctl). This unit keeps the already-running HUD process
alive across PID1 execve, preserves /tmp so its pidfile/controller IPC remain visible,
adopts that HUD in the reloaded PID1, and refreshes rshell on the existing NCM.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3367_hot_reload_tcpctl as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3367_text
ORIG_PREVIOUS_ADAPTER_SOURCE = previous.v3367_adapter_source
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_PREVIOUS_OVERLAY = previous._overlay_preserved_v3367_ramdisk
ORIG_PREVIOUS_FINALIZE = previous._finalize_manifest_after_overlay
ORIG_PREVIOUS_POSTPROCESS = previous._postprocess_manifest

CYCLE = "V3368"
INIT_VERSION = "0.11.129"
INIT_BUILD = "v3368-hot-reload-autohud"
BUILD_TAG = INIT_BUILD
DECISION = "v3368-hot-reload-autohud-source-build"
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
    / "NATIVE_INIT_V3368_HOT_RELOAD_AUTOHUD_SOURCE_BUILD_2026-07-03.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3368_hot_reload_autohud.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3368_hot_reload_autohud"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3368_hot_reload_autohud.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v629_hot_reload_autohud"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3368"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3368.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3368.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3368"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3368-hot-reload-autohud"

FRAME_PATH = "/tmp/a90-doomgeneric-v3368-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3368-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3368-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3368-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3368-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3368-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3368-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3368.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3368_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("0.11.128", INIT_VERSION),
        ("v3367-hot-reload-tcpctl", INIT_BUILD),
        ("hot-reload-tcpctl", "hot-reload-autohud"),
        ("v3367", "v3368"),
        ("V3367", "V3368"),
        ("a90-doomgeneric-v3367", "a90-doomgeneric-v3368"),
        ("a90.doomgeneric.v3367", "a90.doomgeneric.v3368"),
        (
            '    mount("tmpfs", "/tmp", "tmpfs", 0, "mode=1777");',
            '    if (getenv("A90_RELOADED") == NULL) {\n'
            '        mount("tmpfs", "/tmp", "tmpfs", 0, "mode=1777");\n'
            '    }',
        ),
        (
            "static void boot_auto_frame(void) {\n"
            "    if (a90_kms_begin_frame(0x000000) == 0) {",
            "static void boot_auto_frame(void) {\n"
            "    if (getenv(\"A90_RELOADED\") != NULL) {\n"
            "        return;\n"
            "    }\n"
            "    if (a90_kms_begin_frame(0x000000) == 0) {",
        ),
        (
            "static int handle_init_reload(char **argv, int argc) {\n"
            "    /* Hot-reload replaces PID1 via execve without a reboot. Stop the auto-hud drawing thread first\n"
            "       so it is not mid-frame when the image is replaced; a90_init_reload_cmd validates the staged\n"
            "       candidate (approved path + SHA + ELF) and only then execve()s. A failed validation returns an\n"
            "       error and the current init keeps running. */\n"
            "    stop_auto_hud(false);\n"
            "    return a90_init_reload_cmd(argv, argc);\n"
            "}",
            "static int handle_init_reload(char **argv, int argc) {\n"
            "    /* H5 preserves the already-running auto-hud child so its existing DRM master/fb state survives\n"
            "       PID1 execve. The reloaded init adopts the pidfile instead of re-running SETCRTC. */\n"
            "    a90_console_printf(\"reload: preserving autohud for DRM-master handoff\\r\\n\");\n"
            "    return a90_init_reload_cmd(argv, argc);\n"
            "}",
        ),
        (
            '        if (a90_reloaded) {\n'
            '            a90_console_printf("# Hot-reload: skipping autohud/rshell re-init; refreshing tcpctl only.\\r\\n");\n'
            '            a90_logf("boot", "reloaded fast-path: skip autohud/rshell re-init; refresh tcpctl only");\n'
            '            if (a90_netservice_enabled()) {',
            '        if (a90_reloaded) {\n'
            '            pid_t hud_pid;\n'
            '\n'
            '            a90_console_printf("# Hot-reload: adopting autohud, refreshing tcpctl, restarting rshell.\\r\\n");\n'
            '            a90_logf("boot", "reloaded fast-path: adopt autohud; refresh tcpctl; restart rshell");\n'
            '            hud_pid = auto_hud_adopt_pidfile();\n'
            '            if (hud_pid > 0) {\n'
            '                a90_controller_set_menu_active(true);\n'
            '                a90_console_printf("# Hot-reload: autohud adopted pid=%ld.\\r\\n", (long)hud_pid);\n'
            '                a90_timeline_record(0, 0, "hotreload-autohud", "adopted pid=%ld", (long)hud_pid);\n'
            '                a90_logf("boot", "hot-reload autohud adopted pid=%ld", (long)hud_pid);\n'
            '            } else {\n'
            '                a90_controller_set_menu_active(false);\n'
            '                a90_console_printf("# Hot-reload: autohud adopt missing; SETCRTC retry blocked by H5 guard.\\r\\n");\n'
            '                a90_timeline_record(-ENODEV, ENODEV, "hotreload-autohud", "adopt missing; setcrtc retry blocked");\n'
            '                a90_logf("boot", "hot-reload autohud adopt missing; setcrtc retry blocked");\n'
            '            }\n'
            '            if (a90_netservice_enabled()) {',
        ),
        (
            '            } else {\n'
            '                a90_console_printf("# Hot-reload: netservice disabled; tcpctl refresh skipped.\\r\\n");\n'
            '                a90_logf("boot", "hot-reload tcpctl skipped: netservice disabled");\n'
            '            }\n'
            '        } else {',
            '            } else {\n'
            '                a90_console_printf("# Hot-reload: netservice disabled; tcpctl refresh skipped.\\r\\n");\n'
            '                a90_logf("boot", "hot-reload tcpctl skipped: netservice disabled");\n'
            '            }\n'
            '            if (rshell_enabled()) {\n'
            '                int rshell_rc;\n'
            '\n'
            '                a90_console_printf("# Hot-reload: rshell enabled; starting token TCP shell.\\r\\n");\n'
            '                rshell_rc = rshell_start_service(false);\n'
            '                if (rshell_rc == 0) {\n'
            '                    a90_console_printf("# Hot-reload: rshell ready on %s:%s.\\r\\n",\n'
            '                            A90_RSHELL_BIND_ADDR,\n'
            '                            A90_RSHELL_PORT);\n'
            '                    a90_timeline_record(0, 0, "hotreload-rshell", "ready %s:%s",\n'
            '                                    A90_RSHELL_BIND_ADDR,\n'
            '                                    A90_RSHELL_PORT);\n'
            '                    a90_logf("boot", "hot-reload rshell ready %s:%s",\n'
            '                                A90_RSHELL_BIND_ADDR,\n'
            '                                A90_RSHELL_PORT);\n'
            '                } else {\n'
            '                    int rshell_errno = -rshell_rc;\n'
            '\n'
            '                    if (rshell_errno <= 0) {\n'
            '                        rshell_errno = EIO;\n'
            '                    }\n'
            '                    a90_console_printf("# Hot-reload: rshell refresh failed rc=%d errno=%d (%s).\\r\\n",\n'
            '                            rshell_rc,\n'
            '                            rshell_errno,\n'
            '                            strerror(rshell_errno));\n'
            '                    a90_timeline_record(rshell_rc,\n'
            '                                    rshell_errno,\n'
            '                                    "hotreload-rshell",\n'
            '                                    "refresh failed: %s",\n'
            '                                    strerror(rshell_errno));\n'
            '                    a90_logf("boot", "hot-reload rshell refresh failed rc=%d errno=%d error=%s",\n'
            '                                rshell_rc, rshell_errno, strerror(rshell_errno));\n'
            '                }\n'
            '            } else {\n'
            '                a90_console_printf("# Hot-reload: rshell disabled; refresh skipped.\\r\\n");\n'
            '                a90_logf("boot", "hot-reload rshell skipped: disabled");\n'
            '            }\n'
            '        } else {',
        ),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3368_bytes(item: bytes) -> bytes:
    return _rewrite_v3368_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3368_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3368_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3368_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3368_text(previous.SOUND_MODE)

OBSOLETE_H4_SKIP_MARKERS = (
    b"reloaded fast-path: skip autohud/rshell re-init; refresh tcpctl only",
    b"Hot-reload: skipping autohud/rshell re-init; refreshing tcpctl only.",
)

PREVIOUS_REQUIRED_STRINGS = tuple(
    item
    for item in (_rewrite_v3368_bytes(marker) for marker in previous.REQUIRED_STRINGS)
    if item not in OBSOLETE_H4_SKIP_MARKERS
)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.129",
    b"v3368-hot-reload-autohud",
    b"A90RELOAD",
    b"INIT-RELOAD-EXECVE",
    b"hot-reload fast-path (A90_RELOADED set)",
    b"storage-adopt",
    b"sd already mounted rw",
    b"/cache already mounted rw",
    b"tcpctl-adopt",
    b"Hot-reload: tcpctl ready",
    b"refreshing tcpctl on existing NCM",
    b"reload: preserving autohud for DRM-master handoff",
    b"Hot-reload: autohud adopted",
    b"hotreload-autohud",
    b"SETCRTC retry blocked by H5 guard",
    b"Hot-reload: rshell ready",
    b"hotreload-rshell",
)


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "hot-reload-autohud"
    manifest["scope"] = "H5-reload-preserves-and-adopts-autohud-refreshes-rshell"
    manifest["reload_contract"] = {
        "command": "reload INIT-RELOAD-EXECVE <staged-init-path> <expected-sha256>",
        "h5_success": "post-reload version/build changes to V3368, boot summary is BOOT OK, "
                      "storage backend remains sd, runtime backend remains sd, tcpctl is ready, "
                      "autohud is adopted/running without SETCRTC retry, rshell is running when enabled, "
                      "and selftest fail=0",
        "storage_fix_preserved": "already-mounted rw /cache and /mnt/sdext are still adopted instead of remounted",
        "tmp_preserved": "reload path preserves /tmp so existing autohud pidfile and controller IPC remain visible",
        "autohud_fix": "reload preserves the existing HUD child and reloaded PID1 adopts its pidfile instead of re-running SETCRTC",
        "tcpctl_fix": "hot-reload still refreshes tcpctl on the existing NCM",
        "rshell_fix": "hot-reload starts rshell after tcpctl refresh when the rshell opt-in flag is enabled",
        "bright_line": "no panel re-init, no backlight/PMIC/regulator/GDSC/GPIO writes, no SETCRTC retry in reload branch",
        "safety": "no new boot-write primitive; live H5 stages only an init ELF under the approved SD root",
        "risk": "source build only; live H5 reload is separately gated",
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
        "# Native Init V3368 Hot-Reload Autohud Source Build",
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
        "- H5 candidate after V3367 H4: keep the reload command, storage adoption, and tcpctl refresh, "
        "but make the display side a DRM-master handoff.",
        "- `reload` no longer stops the existing autohud child. The reload path also preserves `/tmp` and "
        "skips boot splash KMS presents, so the old HUD process keeps its existing DRM fd/master/fb state.",
        "- The reloaded PID1 calls `auto_hud_adopt_pidfile()` and records `hotreload-autohud` instead of "
        "running a new modeset or SETCRTC retry.",
        "- After tcpctl refresh, rshell is started when its opt-in flag is enabled.",
        "- Bright line retained: no panel re-init, no backlight/PMIC/regulator/GDSC/GPIO writes, no reload "
        "SETCRTC retry.",
        "",
        "## Validation Contract",
        "",
        "- Static PASS requires the V3368 version strings, reload markers, retained storage/tcpctl markers, "
        "and H5 markers (`reload: preserving autohud`, `Hot-reload: autohud adopted`, "
        "`hotreload-autohud`, `Hot-reload: rshell ready`, `hotreload-rshell`).",
        "- Live H5 PASS, separately gated, requires: staged V3368 init SHA matches; `reload` returns "
        "through the new V3368 shell; `status` reports `BOOT OK`, `storage backend=sd`, runtime SD "
        "root, `autohud=running`, `tcpctl=running`, `transport.tcpctl=ready`, `rshell=running` when "
        "enabled, and `selftest fail=0`; host tcpctl `ping` works; operator confirms HUD remains visible; "
        "then rollback to v2321 and health-check clean.",
        "- If autohud cannot be adopted without a SETCRTC/panel re-init, H5 clean-closes the hot-reload "
        "epic at H4 by design.",
        "- No live H5 reload result is claimed by this source-build report.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `hot-reload-autohud`.",
    ]) + "\n"


def v3368_adapter_source() -> str:
    return _rewrite_v3368_text(ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "hot-reload-autohud.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "hot-reload-autohud",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "reload_candidate_init_binary": base.rel(INIT_BINARY),
        "source_report": base.rel(REPORT_PATH),
        "resident_required_for_h5": "v3367-hot-reload-tcpctl-or-later",
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "source-built-live-gated",
        "autohud_contract": "preserve-existing-hud-child-and-adopt-pidfile-no-setcrtc-retry",
        "rshell_contract": "restart-after-hot-reload-on-existing-ncm",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3368(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "hot-reload-autohud",
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
    manifest = _normalize_manifest_for_v3368(json.loads(manifest_path.read_text(encoding="utf-8")))
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
    manifest = _normalize_manifest_for_v3368(ORIG_PREVIOUS_POSTPROCESS())
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


def _overlay_preserved_v3368_ramdisk() -> dict[str, Any]:
    overlay = ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3368-init-helper-engine"
    return overlay


def _patch_v3367_module_for_v3368() -> None:
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
        "v3367_adapter_source": v3368_adapter_source,
        "_rewrite_v3367_text": _rewrite_v3368_text,
        "_rewrite_v3367_bytes": _rewrite_v3368_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3367_ramdisk": _overlay_preserved_v3368_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3367_module_for_v3368()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
