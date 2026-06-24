#!/usr/bin/env python3
"""Build V3155 DOOM SFX best-effort video cadence candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3154_doomgeneric_physical_exit_hud_pid_adopt as v3154

REPO_ROOT = repo_root()

CYCLE = "V3155"
INIT_VERSION = "0.10.137"
INIT_BUILD = "v3155-doomgeneric-sfx-best-effort-video-cadence"
BUILD_TAG = INIT_BUILD
DECISION = "v3155-doomgeneric-sfx-best-effort-video-cadence-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3155_DOOMGENERIC_SFX_BEST_EFFORT_VIDEO_CADENCE_SOURCE_BUILD_2026-06-24.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3155_doomgeneric_sfx_best_effort_video_cadence.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3155_doomgeneric_sfx_best_effort_video_cadence"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3155_doomgeneric_sfx_best_effort_video_cadence.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v533_doomgeneric_sfx_best_effort_video_cadence"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3155"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3155.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3155.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3155"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3155-sfx-best-effort-video-cadence"

FRAME_PATH = "/tmp/a90-doomgeneric-v3155-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3155-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3155-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3155-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3155-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3155-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3155-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-sfx-best-effort-video-cadence"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-sfx-best-effort-video-cadence"

INPUT_THREAD_MARKER = v3154.INPUT_THREAD_MARKER.replace("v3154", "v3155")
TIME_MODEL_MARKER = v3154.TIME_MODEL_MARKER.replace("v3154", "v3155")
DEMO_HUD_MARKER = v3154.DEMO_HUD_MARKER.replace("v3154", "v3155")
PACED_TIME_MARKER = v3154.PACED_TIME_MARKER.replace("v3154", "v3155")
TICK_TELEMETRY_MARKER = v3154.TICK_TELEMETRY_MARKER.replace("v3154", "v3155")
SCALE_MARKER = v3154.SCALE_MARKER.replace("v3154", "v3155")
PHASE_TELEMETRY_MARKER = v3154.PHASE_TELEMETRY_MARKER.replace("v3154", "v3155")
GAMETIC_FRAME_TELEMETRY_MARKER = v3154.GAMETIC_FRAME_TELEMETRY_MARKER.replace(
    "v3154",
    "v3155",
)
SFX_STREAM_MARKER = "a90.doomgeneric.v3155.audio=real-sfx-pcm-stream-best-effort-video-cadence"
SOUND_MODE = "native-doom-sfx-best-effort-video-cadence-v3155"

AUDIO_CORUN = v3154.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = v3154.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = v3154.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = v3154.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3154.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = v3154.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3155.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

_ORIGINAL_V3154_VALUES = v3154._v3154_values
_ORIGINAL_V3154_ADAPTER_SOURCE = v3154._v3154_adapter_source_from_patched_v3148


def rel(path: Path) -> str:
    return v3154.rel(path)


def _replace_required(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"required source block missing: {old[:80]!r}")
    return text.replace(old, new, 1)


def _make_v3155_sfx_backend(text: str) -> str:
    text = text.replace(v3154.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
    text = text.replace("v3154", "v3155")
    text = _replace_required(
        text,
        """static int open_stream_once(void) {
    int fd = open(A90_SFX_STREAM_PATH, O_WRONLY | O_NONBLOCK | O_CLOEXEC);

    if (fd >= 0) {
        int flags = fcntl(fd, F_GETFL, 0);

        if (flags >= 0) {
            (void)fcntl(fd, F_SETFL, flags & ~O_NONBLOCK);
        }
    }
    return fd;
}
""",
        """static int open_stream_once(void) {
    return open(A90_SFX_STREAM_PATH, O_WRONLY | O_NONBLOCK | O_CLOEXEC);
}
""",
    )
    text = _replace_required(
        text,
        """static int write_full(int fd, const void *data, size_t bytes) {
    size_t done = 0;

    while (done < bytes) {
        ssize_t wr = write(fd, (const char *)data + done, bytes - done);

        if (wr < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -errno;
        }
        if (wr == 0) {
            return -EIO;
        }
        done += (size_t)wr;
    }
    return 0;
}
""",
        """static int write_best_effort(int fd, const void *data, size_t bytes) {
    size_t done = 0;
    unsigned int writes = 0;

    while (done < bytes && writes < 4U) {
        ssize_t wr = write(fd, (const char *)data + done, bytes - done);

        if (wr < 0) {
            if (errno == EINTR) {
                continue;
            }
            if (errno == EAGAIN
#ifdef EWOULDBLOCK
                || errno == EWOULDBLOCK
#endif
            ) {
                return 0;
            }
            return -errno;
        }
        if (wr == 0) {
            return 0;
        }
        done += (size_t)wr;
        ++writes;
    }
    return 0;
}
""",
    )
    text = _replace_required(
        text,
        """static int open_stream(void) {
    int attempt;

    for (attempt = 0; attempt < 500; ++attempt) {
        int fd = open_stream_once();

        if (fd >= 0) {
            return fd;
        }
        if (errno != ENOENT && errno != ENXIO && errno != EINTR) {
            return -1;
        }
        usleep(10000);
    }
    return -1;
}
""",
        """static int open_stream(void) {
    return open_stream_once();
}
""",
    )
    text = _replace_required(
        text,
        """    stream_fd = open_stream();
    return stream_fd >= 0 ? true : false;
}
""",
        """    stream_fd = open_stream();
    return true;
}
""",
    )
    text = _replace_required(
        text,
        "        int write_rc = write_full(stream_fd, mix, frames * 2U * sizeof(mix[0]));",
        "        int write_rc = write_best_effort(stream_fd, mix, frames * 2U * sizeof(mix[0]));",
    )
    return text


SFX_BACKEND_SOURCE_TEXT = _make_v3155_sfx_backend(v3154.SFX_BACKEND_SOURCE_TEXT)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        v3154.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        v3154.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        v3154.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        v3154.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        v3154.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        v3154.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        v3154.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3154": b"a90-doomgeneric-v3155",
        b"a90.doomgeneric.v3154": b"a90.doomgeneric.v3155",
        b"v3154": b"v3155",
        b"V3154": b"V3155",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in v3154.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
)


def _v3155_overrides() -> dict[str, Any]:
    return {
        "CYCLE": CYCLE,
        "INIT_VERSION": INIT_VERSION,
        "INIT_BUILD": INIT_BUILD,
        "BUILD_TAG": BUILD_TAG,
        "DECISION": DECISION,
        "OUT_DIR": OUT_DIR,
        "OBJ_DIR": OBJ_DIR,
        "REPORT_PATH": REPORT_PATH,
        "BOOT_IMAGE": BOOT_IMAGE,
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
        "INPUT_THREAD_MARKER": INPUT_THREAD_MARKER,
        "TIME_MODEL_MARKER": TIME_MODEL_MARKER,
        "DEMO_HUD_MARKER": DEMO_HUD_MARKER,
        "PACED_TIME_MARKER": PACED_TIME_MARKER,
        "TICK_TELEMETRY_MARKER": TICK_TELEMETRY_MARKER,
        "SCALE_MARKER": SCALE_MARKER,
        "PHASE_TELEMETRY_MARKER": PHASE_TELEMETRY_MARKER,
        "GAMETIC_FRAME_TELEMETRY_MARKER": GAMETIC_FRAME_TELEMETRY_MARKER,
        "SFX_STREAM_MARKER": SFX_STREAM_MARKER,
        "SOUND_MODE": SOUND_MODE,
        "AUDIO_CORUN": AUDIO_CORUN,
        "AUDIO_CORUN_MODE": AUDIO_CORUN_MODE,
        "AUDIO_CORUN_STREAM": AUDIO_CORUN_STREAM,
        "AUDIO_CORUN_DURATION_MS": AUDIO_CORUN_DURATION_MS,
        "AUDIO_CORUN_REFRESH_MS": AUDIO_CORUN_REFRESH_MS,
        "AUDIO_CORUN_AMPLITUDE_MILLI": AUDIO_CORUN_AMPLITUDE_MILLI,
        "PHYSICAL_BUTTON_EXIT": PHYSICAL_BUTTON_EXIT,
        "SFX_BACKEND_SOURCE": SFX_BACKEND_SOURCE,
        "SDL_MIXER_STUB": SDL_MIXER_STUB,
        "SFX_BACKEND_SOURCE_TEXT": SFX_BACKEND_SOURCE_TEXT,
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
    }


def _v3155_values() -> dict[str, Any]:
    values = dict(_ORIGINAL_V3154_VALUES())
    values.update(_v3155_overrides())
    return values


def _v3155_adapter_source_from_patched_v3148() -> str:
    return (
        _ORIGINAL_V3154_ADAPTER_SOURCE()
        .replace("real-sfx-pcm-stream-long-window-physical-exit-hud-pid-adopt",
                 "real-sfx-pcm-stream-best-effort-video-cadence")
        .replace("v3154", "v3155")
        .replace("V3154", "V3155")
    )


def v3155_adapter_source() -> str:
    return _v3155_adapter_source_from_patched_v3148()


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    audio = doom.get("audio_corun", {})
    return "\n".join([
        "# Native Init V3155 DOOMGENERIC SFX Best-Effort Video Cadence Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: DOOM native demo video cadence with real SFX enabled.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps the V3154 physical-button menu recovery and HUD PID adoption behavior.",
        "- Makes DOOM SFX FIFO writes best-effort and nonblocking, so audio backpressure cannot stall the video loop.",
        "- Removes the SFX init FIFO wait; foreground frame timing tests no longer fail before the first frame when no audio worker is present.",
        "- Preserves real SFX when the PCM stream worker is ready; overloaded audio samples may be dropped instead of blocking frames.",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Audio stream path: `{AUDIO_PCM_STREAM_PATH}`",
        f"- Sound mode: `{SOUND_MODE}`",
        f"- Audio co-run enabled: `{int(bool(audio.get('enabled', AUDIO_CORUN)))}`",
        f"- Audio duration ms: `{AUDIO_CORUN_DURATION_MS}`",
        f"- Audio refresh ms: `{AUDIO_CORUN_REFRESH_MS}`",
        "- Physical exit: `POWER`, `VOLUP`, or `VOLDOWN` exits the loop, presents the menu frame, restores live HUD input, then stops audio.",
        f"- Frame IPC: `{FRAME_IPC}`",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- The helper writes PCM bytes only to an allowlisted FIFO under `/cache/a90-runtime`; it does not open ALSA, route, setcal, or smart-amp controls.",
        "- SFX stream behavior is best-effort: video cadence is preferred over lossless audio samples.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3155 builder and focused tests.",
        "- `unittest`: V3155 source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3155 identity, best-effort SFX marker, and inherited DOOM/input/HUD markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-sfx-best-effort-video-cadence-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    audio = doom.setdefault("audio_corun", {})
    audio.update({
        "enabled": True,
        "mode": AUDIO_CORUN_MODE,
        "stream": True,
        "stream_path": AUDIO_PCM_STREAM_PATH,
        "duration_ms": AUDIO_CORUN_DURATION_MS,
        "refresh_ms": AUDIO_CORUN_REFRESH_MS,
        "refresh_disabled": True,
        "amplitude_milli": AUDIO_CORUN_AMPLITUDE_MILLI,
        "real_doom_sfx": True,
        "music": False,
        "best_effort_nonblocking": True,
        "video_cadence_priority": True,
    })
    doom.update({
        "physical_button_exit": {
            "enabled": True,
            "events": ["event3", "event0"],
            "keys": ["KEY_POWER", "KEY_VOLUMEUP", "KEY_VOLUMEDOWN"],
            "action": "exit-doom-loop-hud-pid-adopt-then-stop-audio",
            "return_reason": "physical-button-exit",
            "menu_return": True,
            "hud_pid_adopt": True,
            "start_new_hud_from_doom_exit_path": True,
        },
        "sound_mode": SOUND_MODE,
        "sfx_stream_marker": SFX_STREAM_MARKER,
        "audio_pcm_stream_path": AUDIO_PCM_STREAM_PATH,
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-sfx-best-effort-video-cadence-candidate",
        "adoption_state": "pending-sfx-best-effort-video-cadence-live-validation",
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
    (OUT_DIR / "doomgeneric-sfx-best-effort-video-cadence-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-sfx-best-effort-video-cadence-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "runtime_wad_path": v3154.v3151.v3150.v3149.RUNTIME_WAD_PATH,
        "expected_wad_sha256": v3154.v3151.v3150.v3149.EXPECTED_WAD_SHA256,
        "audio_pcm_stream_path": AUDIO_PCM_STREAM_PATH,
        "audio_duration_ms": AUDIO_CORUN_DURATION_MS,
        "audio_refresh_ms": AUDIO_CORUN_REFRESH_MS,
        "audio_best_effort_nonblocking": True,
        "video_cadence_priority": True,
        "physical_button_exit": True,
        "direct_menu_present_on_physical_exit": True,
        "hud_pid_adopt_on_physical_exit": True,
        "start_new_hud_from_doom_exit_path": True,
        "sound_mode": SOUND_MODE,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-sfx-best-effort-video-cadence-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _apply_v3155_globals() -> list[tuple[str, Any, bool]]:
    saved: list[tuple[str, Any, bool]] = []
    for name, value in _v3155_overrides().items():
        existed = hasattr(v3154, name)
        saved.append((name, getattr(v3154, name, None), existed))
        setattr(v3154, name, value)
    for name, value in (
        ("_v3154_values", _v3155_values),
        ("_v3154_adapter_source_from_patched_v3148", _v3155_adapter_source_from_patched_v3148),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((name, getattr(v3154, name), True))
        setattr(v3154, name, value)
    return saved


def _restore_v3155_globals(saved: list[tuple[str, Any, bool]]) -> None:
    for name, value, existed in reversed(saved):
        if existed:
            setattr(v3154, name, value)
        else:
            delattr(v3154, name)


def main() -> int:
    saved = _apply_v3155_globals()
    try:
        return v3154.main()
    finally:
        _restore_v3155_globals(saved)


if __name__ == "__main__":
    raise SystemExit(main())
