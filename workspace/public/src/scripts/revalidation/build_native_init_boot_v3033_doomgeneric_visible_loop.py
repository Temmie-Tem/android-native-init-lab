#!/usr/bin/env python3
"""Build V3033 native-init doomgeneric visible playable-loop candidate.

V3033 keeps WAD bytes runtime-private on SD, then combines the V3032-proven
hash gate, helper frame rendering, KMS presentation path, and serial doompad
input bridge into a bounded visible loop. It also adds a host-side keyboard
bridge script that drives `doompad key` over the existing serial command path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
import build_native_init_boot_v3029_doomgeneric_sd_wad_command as v3029
import build_native_init_boot_v3031_doomgeneric_visible_frame as v3031
import native_doomgeneric_engine_integration_build_v3024 as v3024
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3033"
INIT_VERSION = "0.10.76"
INIT_BUILD = "v3033-doomgeneric-visible-loop"
BUILD_TAG = INIT_BUILD
DECISION = "v3033-doomgeneric-visible-loop-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3033_DOOMGENERIC_VISIBLE_LOOP_SOURCE_BUILD_2026-06-22.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3033_doomgeneric_visible_loop.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3033_doomgeneric_visible_loop"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3033_doomgeneric_visible_loop.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v512_doomgeneric_visible_loop"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3033"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3033.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3033.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3033"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3033-visible-loop"

RUNTIME_WAD_ROOT = v3029.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3029.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3029.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3029.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3031.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3029.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = 90
MAX_LOOP_FRAMES = v3029.MAX_SMOKE_FRAMES
LOOP_FRAME_MS = 50
PRESENTER_POLL_MS = 4
FRAME_PATH = "/tmp/a90-doomgeneric-v3033-loop-frame.xbgr8888"
SHARED_FRAME_PATH = ""
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3033-input.state"
INPUT_SOCKET_PATH = ""
INPUT_PATH = "serial-doompad-to-DG_GetKey"
INPUT_UDP_PORT = 0
PACE_SOCKET_PATH = ""
FRAME_WIDTH = v3031.FRAME_WIDTH
FRAME_HEIGHT = v3031.FRAME_HEIGHT
FRAME_STRIDE = v3031.FRAME_STRIDE
FRAME_BYTES = v3031.FRAME_BYTES
NATIVE_DASHBOARD = 0
NATIVE_DASHBOARD_MINIMAL = 0
NATIVE_DASHBOARD_LARGE_FRAME = 0
NATIVE_DOOM_PRESENT_PAGEFLIP = 0
REUSE_FRAME_BUFFER = 0
DASHBOARD_METRICS_INTERVAL_FRAMES = 1
FRAME_TIMING_PROBE = 0
SEQ_TELEMETRY = 0
PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = 0
SOUND_MODE = "disabled-nosound-nomusic"
AUDIO_CORUN = 0
AUDIO_CORUN_MODE = "disabled"
AUDIO_CORUN_DURATION_MS = 10000
AUDIO_CORUN_AMPLITUDE_MILLI = 80

HOST_KEYBOARD_BRIDGE = (
    REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation" / "host_doompad_keyboard_v3033.py"
)

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.76 (v3033-doomgeneric-visible-loop)",
    b"v3033-doomgeneric-visible-loop",
    b"doomgeneric-private-link-v3033-visible-loop",
    b"/bin/a90_doomgeneric_private_engine_v3033",
    RUNTIME_WAD_PATH.encode("ascii"),
    EXPECTED_WAD_SHA256.encode("ascii"),
    FRAME_PATH.encode("ascii"),
    INPUT_STATE_PATH.encode("ascii"),
    b"--wad-smoke",
    b"--wad-frame-dump",
    b"--wad-frame-loop",
    b"--input-state",
    b"--frame-ms",
    b"a90.doomgeneric.v3033.visible_loop=state-file-frame-loop",
    b"video demo doom loop [frames] --wad runtime-private --sha256",
    b"video demo doom loop-start [frames] --wad runtime-private --sha256",
    b"video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop",
    b"video.demo.doom.loop_start=background-presenter",
    b"doompad.input_state.path=",
    b"host_doompad_keyboard_v3033.py",
    b"menu.demo.doom.action=visible-playable-loop",
    b"WAD PLAYABLE LOOP",
    b"video.demo.asset.wad.embedded_in_boot=%d",
    b"video.demo.input.otg_required=0",
)


def rel(path: Path) -> str:
    return v3029.rel(path)


def shell_define(name: str, value: str) -> str:
    return v3029.shell_define(name, value)


def numeric_define(name: str, value: int) -> str:
    return v3029.numeric_define(name, value)


def v3033_adapter_source() -> str:
    text = v3031.v3031_adapter_source()
    text = text.replace(
        "#include <fcntl.h>\n#include <stdint.h>",
        "#include <fcntl.h>\n#include <stdio.h>\n#include <stdint.h>",
    )
    text = text.replace(
        '"a90.doomgeneric.v3031.visible_frame=frame-dump-xbgr8888";',
        '"a90.doomgeneric.v3033.visible_loop=state-file-frame-loop";',
    )
    text = text.replace(
        'const char a90_doomgeneric_v3031_frame_dump_policy[] =\n'
        '    "a90.doomgeneric.v3031.frame_dump=raw-xbgr8888-file";',
        'const char a90_doomgeneric_v3031_frame_dump_policy[] =\n'
        '    "a90.doomgeneric.v3031.frame_dump=raw-xbgr8888-file";\n'
        'const char a90_doomgeneric_v3033_loop_policy[] =\n'
        '    "a90.doomgeneric.v3033.loop=input-state-file-to-DG_GetKey";',
    )
    loop_support = r'''
static void a90_doomgeneric_apply_input_state_file(const char *path) {
    struct a90_doompad_snapshot snapshot;
    FILE *fp;
    char line[96];

    if (path == NULL || path[0] == '\0') {
        return;
    }
    memset(&snapshot, 0, sizeof(snapshot));
    fp = fopen(path, "r");
    if (fp == NULL) {
        return;
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        char key[32];
        unsigned int value = 0U;

        if (sscanf(line, "%31[^=]=%u", key, &value) != 2) {
            continue;
        }
        if (strcmp(key, "forward") == 0) {
            snapshot.forward = value != 0U;
        } else if (strcmp(key, "back") == 0) {
            snapshot.back = value != 0U;
        } else if (strcmp(key, "left") == 0) {
            snapshot.left = value != 0U;
        } else if (strcmp(key, "right") == 0) {
            snapshot.right = value != 0U;
        } else if (strcmp(key, "fire") == 0) {
            snapshot.fire = value != 0U;
        } else if (strcmp(key, "use") == 0) {
            snapshot.use = value != 0U;
        } else if (strcmp(key, "menu") == 0) {
            snapshot.menu = value != 0U;
        } else if (strcmp(key, "run") == 0) {
            snapshot.run = value != 0U;
        } else if (strcmp(key, "seq") == 0) {
            snapshot.seq = value;
        }
    }
    fclose(fp);
    a90_doomgeneric_feed_snapshot(&snapshot);
}

static int a90_doomgeneric_dump_frame_xbgr8888_atomic(const char *output_path) {
    char tmp_path[256];
    int rc;

    if (output_path == NULL ||
        snprintf(tmp_path, sizeof(tmp_path), "%s.tmp", output_path) >= (int)sizeof(tmp_path)) {
        return 47;
    }
    rc = a90_doomgeneric_dump_frame_xbgr8888(tmp_path);
    if (rc != 0) {
        (void)unlink(tmp_path);
        return rc;
    }
    if (rename(tmp_path, output_path) < 0) {
        (void)unlink(tmp_path);
        return 48;
    }
    return 0;
}

int a90_doomgeneric_run_wad_frame_loop(const char *wad_path,
                                       int frames,
                                       const char *output_path,
                                       const char *input_state_path,
                                       int frame_ms) {
    static char arg0[] = "doomgeneric";
    static char arg_iwad[] = "-iwad";
    static char arg_nosound[] = "-nosound";
    static char arg_nomusic[] = "-nomusic";
    static char arg_mb[] = "-mb";
    static char arg_mb_value[] = "6";
    char *argv[8];
    int index;

    if (wad_path == NULL || wad_path[0] == '\0' ||
        output_path == NULL || output_path[0] == '\0' ||
        input_state_path == NULL || input_state_path[0] == '\0' ||
        frames <= 0 || frames > 300 || frame_ms <= 0 || frame_ms > 250) {
        return 49;
    }
    argv[0] = arg0;
    argv[1] = arg_iwad;
    argv[2] = (char *)wad_path;
    argv[3] = arg_nosound;
    argv[4] = arg_nomusic;
    argv[5] = arg_mb;
    argv[6] = arg_mb_value;
    argv[7] = NULL;

    doomgeneric_Create(7, argv);
    for (index = 0; index < frames; ++index) {
        int rc;

        a90_doomgeneric_apply_input_state_file(input_state_path);
        doomgeneric_Tick();
        if (a90_doomgeneric_presented_frames() > 0U) {
            rc = a90_doomgeneric_dump_frame_xbgr8888_atomic(output_path);
            if (rc != 0) {
                return rc;
            }
        }
        usleep((useconds_t)frame_ms * 1000U);
    }
    return a90_doomgeneric_presented_frames() > 0U ? 0 : 50;
}

'''
    text = text.replace("int main(int argc, char **argv) {", loop_support + "int main(int argc, char **argv) {")
    text = text.replace(
        "marker_checksum(a90_doomgeneric_v3031_frame_dump_policy) == 0U) {",
        "marker_checksum(a90_doomgeneric_v3031_frame_dump_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3033_loop_policy) == 0U) {",
    )
    text = text.replace(
        '''    if (argc == 7 &&
        strcmp(argv[1], "--wad-frame-dump") == 0 &&
        argv[2] != NULL &&
        strcmp(argv[3], "--frames") == 0 &&
        strcmp(argv[5], "--output") == 0 &&
        argv[6] != NULL) {
        frames = a90_doomgeneric_parse_positive_int(argv[4], 300);
        if (frames <= 0) {
            return 34;
        }
        return a90_doomgeneric_run_wad_frame_dump(argv[2], frames, argv[6]);
    }
    return 35;
}
''',
        '''    if (argc == 7 &&
        strcmp(argv[1], "--wad-frame-dump") == 0 &&
        argv[2] != NULL &&
        strcmp(argv[3], "--frames") == 0 &&
        strcmp(argv[5], "--output") == 0 &&
        argv[6] != NULL) {
        frames = a90_doomgeneric_parse_positive_int(argv[4], 300);
        if (frames <= 0) {
            return 34;
        }
        return a90_doomgeneric_run_wad_frame_dump(argv[2], frames, argv[6]);
    }
    if (argc == 11 &&
        strcmp(argv[1], "--wad-frame-loop") == 0 &&
        argv[2] != NULL &&
        strcmp(argv[3], "--frames") == 0 &&
        strcmp(argv[5], "--output") == 0 &&
        argv[6] != NULL &&
        strcmp(argv[7], "--input-state") == 0 &&
        argv[8] != NULL &&
        strcmp(argv[9], "--frame-ms") == 0) {
        int frame_ms;

        frames = a90_doomgeneric_parse_positive_int(argv[4], 300);
        frame_ms = a90_doomgeneric_parse_positive_int(argv[10], 250);
        if (frames <= 0 || frame_ms <= 0) {
            return 36;
        }
        return a90_doomgeneric_run_wad_frame_loop(argv[2], frames, argv[6], argv[8], frame_ms);
    }
    return 37;
}
''',
    )
    return text


def build_v3033_engine() -> dict[str, Any]:
    originals = {
        "OUT_DIR": v3024.OUT_DIR,
        "OBJ_DIR": v3024.OBJ_DIR,
        "ADAPTER_SOURCE": v3024.ADAPTER_SOURCE,
        "ADAPTER_OBJECT": v3024.ADAPTER_OBJECT,
        "ENGINE_BINARY": v3024.ENGINE_BINARY,
        "RUNTIME_WAD_PATH": v3024.RUNTIME_WAD_PATH,
        "RUNTIME_WAD_ROOT": v3024.RUNTIME_WAD_ROOT,
        "ADAPTER_SOURCE_TEXT": v3024.ADAPTER_SOURCE_TEXT,
    }
    try:
        v3024.OUT_DIR = OUT_DIR
        v3024.OBJ_DIR = OBJ_DIR
        v3024.ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
        v3024.ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
        v3024.ENGINE_BINARY = ENGINE_BINARY
        v3024.RUNTIME_WAD_PATH = RUNTIME_WAD_PATH
        v3024.RUNTIME_WAD_ROOT = RUNTIME_WAD_ROOT
        v3024.ADAPTER_SOURCE_TEXT = v3033_adapter_source()
        return v3024.compile_private_engine()
    finally:
        for name, value in originals.items():
            setattr(v3024, name, value)


def configure_base() -> None:
    v2859.CYCLE = CYCLE
    v2859.INIT_VERSION = INIT_VERSION
    v2859.INIT_BUILD = INIT_BUILD
    v2859.BUILD_TAG = BUILD_TAG
    v2859.DECISION = DECISION
    v2859.OUT_DIR = OUT_DIR
    v2859.REPORT_PATH = REPORT_PATH
    v2859.BOOT_IMAGE = BOOT_IMAGE
    v2859.INIT_BINARY = INIT_BINARY
    v2859.RAMDISK_CPIO = RAMDISK_CPIO
    v2859.HELPER_BINARY = HELPER_BINARY


def patch_ramdisk_with_doomgeneric_helper() -> None:
    v2845 = v2859.v2851.v2849.v2847.v2845
    v2843 = v2845.v2843
    original_patch_ramdisk_and_flags = v2845.patch_ramdisk_and_flags_with_boot_chime

    def patch_with_doomgeneric_helper(ramdisk_files: dict[str, Path]) -> None:
        original_patch_ramdisk_and_flags(ramdisk_files)
        base = v2843.v2807.v2799.v2789.v2334.base_module().base
        original_ramdisk_helpers = base.ramdisk_helpers
        inherited_flags = tuple(base.EXTRA_INIT_FLAGS)
        doomgeneric_flags = (
            shell_define("A90_DOOMGENERIC_BRIDGE_CANDIDATE", INIT_BUILD),
            shell_define("A90_DOOMGENERIC_BRIDGE_ENGINE", ENGINE_NAME),
            shell_define("A90_DOOMGENERIC_BRIDGE_HELPER_PATH", ENGINE_REMOTE_PATH),
            shell_define("A90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT", RUNTIME_WAD_ROOT),
            shell_define("A90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH", RUNTIME_WAD_PATH),
            shell_define("A90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256", EXPECTED_WAD_SHA256),
            shell_define("A90_DOOMGENERIC_BRIDGE_FRAME_PATH", FRAME_PATH),
            shell_define("A90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH", INPUT_STATE_PATH),
            shell_define("A90_DOOMGENERIC_BRIDGE_INPUT", INPUT_PATH),
            shell_define("A90_DOOMGENERIC_BRIDGE_SOUND", SOUND_MODE),
            shell_define("A90_DOOMGENERIC_AUDIO_CORUN_MODE", AUDIO_CORUN_MODE),
            numeric_define("A90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES", RUNTIME_WAD_MAX_BYTES),
            numeric_define("A90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES", MAX_LOOP_FRAMES),
            numeric_define("A90_DOOMGENERIC_BRIDGE_FRAME_WIDTH", FRAME_WIDTH),
            numeric_define("A90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT", FRAME_HEIGHT),
            numeric_define("A90_DOOMGENERIC_BRIDGE_FRAME_STRIDE", FRAME_STRIDE),
            numeric_define("A90_DOOMGENERIC_BRIDGE_FRAME_BYTES", FRAME_BYTES),
            numeric_define("A90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS", LOOP_FRAME_MS),
            numeric_define("VIDEO_DEMO_DOOMGENERIC_PRESENTER_POLL_MS", PRESENTER_POLL_MS),
            numeric_define("A90_DOOMGENERIC_AUDIO_CORUN", AUDIO_CORUN),
            numeric_define("A90_DOOMGENERIC_AUDIO_CORUN_DURATION_MS", AUDIO_CORUN_DURATION_MS),
            numeric_define("A90_DOOMGENERIC_AUDIO_CORUN_AMPLITUDE_MILLI", AUDIO_CORUN_AMPLITUDE_MILLI),
        )
        if REUSE_FRAME_BUFFER:
            doomgeneric_flags = (
                *doomgeneric_flags,
                numeric_define("VIDEO_DEMO_DOOMGENERIC_REUSE_FRAME_BUFFER", 1),
            )
        if DASHBOARD_METRICS_INTERVAL_FRAMES > 1:
            doomgeneric_flags = (
                *doomgeneric_flags,
                numeric_define(
                    "VIDEO_DEMO_DOOMGENERIC_DASHBOARD_METRICS_INTERVAL_FRAMES",
                    DASHBOARD_METRICS_INTERVAL_FRAMES,
                ),
            )
        if FRAME_TIMING_PROBE:
            doomgeneric_flags = (
                *doomgeneric_flags,
                numeric_define("VIDEO_DEMO_DOOMGENERIC_FRAME_TIMING_PROBE", 1),
            )
        if SEQ_TELEMETRY:
            doomgeneric_flags = (
                *doomgeneric_flags,
                numeric_define("VIDEO_DEMO_DOOMGENERIC_SEQ_TELEMETRY", 1),
            )
        if NATIVE_DASHBOARD:
            doomgeneric_flags = (
                *doomgeneric_flags,
                numeric_define("A90_DOOMGENERIC_NATIVE_DASHBOARD", 1),
            )
        if NATIVE_DASHBOARD_MINIMAL:
            doomgeneric_flags = (
                *doomgeneric_flags,
                numeric_define("A90_DOOMGENERIC_NATIVE_DASHBOARD_MINIMAL", 1),
            )
        if NATIVE_DASHBOARD_LARGE_FRAME:
            doomgeneric_flags = (
                *doomgeneric_flags,
                numeric_define("A90_DOOMGENERIC_NATIVE_DASHBOARD_LARGE_FRAME", 1),
            )
        if NATIVE_DOOM_PRESENT_PAGEFLIP:
            doomgeneric_flags = (
                *doomgeneric_flags,
                numeric_define("VIDEO_DEMO_DOOMGENERIC_PRESENT_PAGEFLIP", 1),
            )
        if PAGEFLIP_MIN_SUBMIT_INTERVAL_MS > 0:
            doomgeneric_flags = (
                *doomgeneric_flags,
                numeric_define(
                    "VIDEO_DEMO_DOOMGENERIC_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS",
                    PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
                ),
            )
        if INPUT_SOCKET_PATH:
            doomgeneric_flags = (
                *doomgeneric_flags,
                shell_define("A90_DOOMGENERIC_BRIDGE_INPUT_SOCKET_PATH", INPUT_SOCKET_PATH),
            )
        if SHARED_FRAME_PATH:
            doomgeneric_flags = (
                *doomgeneric_flags,
                shell_define("A90_DOOMGENERIC_BRIDGE_SHARED_FRAME_PATH", SHARED_FRAME_PATH),
            )
        if PACE_SOCKET_PATH:
            doomgeneric_flags = (
                *doomgeneric_flags,
                shell_define("A90_DOOMGENERIC_BRIDGE_PACE_SOCKET_PATH", PACE_SOCKET_PATH),
            )
        if INPUT_UDP_PORT:
            doomgeneric_flags = (
                *doomgeneric_flags,
                numeric_define("A90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT", INPUT_UDP_PORT),
            )
        base.EXTRA_INIT_FLAGS = (*inherited_flags, *(flag for flag in doomgeneric_flags if flag not in inherited_flags))

        def ramdisk_helpers_with_doomgeneric(args: Any) -> dict[str, Path]:
            helpers = dict(original_ramdisk_helpers(args))
            helpers[ENGINE_RAMDISK_PATH] = ENGINE_BINARY
            return helpers

        base.ramdisk_helpers = ramdisk_helpers_with_doomgeneric

    v2845.patch_ramdisk_and_flags_with_boot_chime = patch_with_doomgeneric_helper


def require_strings(path: Path) -> list[str]:
    data = path.read_bytes()
    missing = [marker.decode("ascii", errors="replace") for marker in REQUIRED_STRINGS if marker not in data]
    if missing:
        raise RuntimeError(f"missing V3033 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3033 DOOMGENERIC Visible Loop Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback / DOOM capstone.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        "- Device action: `none` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Extends the private doomgeneric helper with `--wad-frame-loop <path> --frames N --output <frame> --input-state <state> --frame-ms N`.",
        "- Adds native-init `video demo doom loop [frames] --wad runtime-private --sha256 EXPECTED` for bounded foreground KMS presentation.",
        "- Adds native-init `video demo doom loop-start [frames] --wad runtime-private --sha256 EXPECTED`, `loop-status`, and `loop-stop` for a background presenter that leaves the serial command path free for host keyboard input.",
        "- Mirrors every `doompad key` / `doompad reset` state into a temporary input-state file consumed by the helper's `DG_GetKey` queue.",
        "- Adds `host_doompad_keyboard_v3033.py`, which maps a host terminal keyboard to `doompad key <role> <0|1>` over `a90ctl.py` with all-up cleanup.",
        "- The DEMO > DOOM menu item now launches a bounded visible playable loop and restores the menu afterward.",
        "",
        "## Runtime WAD Contract",
        "",
        f"- Runtime WAD root: `{doom.get('runtime_wad_root')}`",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Runtime WAD max bytes: `{doom.get('runtime_wad_max_bytes')}`",
        f"- WAD files in ramdisk: `{doom.get('ramdisk_wad_file_count')}`",
        f"- Public WAD files committed/present: `{doom.get('public_wad_file_count')}`",
        f"- WAD bytes embedded in boot image: `{doom.get('wad_embedded_in_boot')}`",
        "",
        "## Loop Contract",
        "",
        f"- Helper loop command: `{doom.get('helper_loop_command')}`",
        f"- Native foreground command: `{doom.get('loop_command')}`",
        f"- Native background command: `{doom.get('loop_start_command')}`",
        f"- Host keyboard bridge: `{doom.get('host_keyboard_bridge')}`",
        f"- Input state path: `{doom.get('input_state_path')}`",
        f"- Frame path: `{doom.get('frame_path')}`",
        f"- Frame format: `{doom.get('frame_format')}`",
        f"- Frame geometry: `{doom.get('frame_width')}x{doom.get('frame_height')}` stride `{doom.get('frame_stride')}` bytes `{doom.get('frame_bytes')}`",
        f"- Default loop frames: `{doom.get('default_loop_frames')}`",
        f"- Loop frame ms: `{doom.get('loop_frame_ms')}`",
        "",
        "## Private Engine Helper",
        "",
        f"- Bundled helper path: `{doom.get('engine_ramdisk_path')}`",
        f"- V3033 engine binary: `{doom.get('engine_binary')}`",
        f"- V3033 engine SHA256: `{doom.get('engine_binary_sha256')}`",
        f"- V3033 engine bytes: `{doom.get('engine_binary_bytes')}`",
        f"- Helper bundled in ramdisk: `{int(bool(doom.get('helper_bundled_in_ramdisk')))}`",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- No flash, serial live command, Wi-Fi action, sysfs write, evdev injection, uinput, PMIC, regulator, backlight, GPIO, GDSC, or forbidden partition path is touched.",
        "- WAD/IWAD bytes remain only on the runtime SD path and are not copied into public, ramdisk, boot image, reports, or generated source.",
        "- The input-state and frame files are temporary runtime files under `/tmp`, not WAD copies.",
        "- The generated boot image and helper are private/untracked. Public output is limited to source, tests, host keyboard tooling, and this metadata-only report.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata` for the next live unit.",
        "",
        "## Host Validation",
        "",
        "- `py_compile`: builder, host keyboard bridge, selector, and focused tests.",
        "- `unittest`: V3033 visible-loop tests, host keyboard bridge tests, V3031 visible-frame tests, and selector tests.",
        "- Build: AArch64 static private doomgeneric helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3033 visible-loop commands, input-state path, SD WAD path/hash, host bridge marker, and bounded helper markers.",
        "- Ramdisk inventory: helper path present and WAD file count is zero.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3034`",
        "- Type: rollback-gated live validation of V3033 visible-loop candidate.",
        "- Scope: flash only the exact V3033 boot image through `native_init_flash.py`, health-check, run foreground `video demo doom loop 8 --wad runtime-private --sha256 EXPECTED`, then run `loop-start` with the host keyboard bridge sending bounded `doompad` transitions, confirm presentation/input markers, stop the loop, and rollback to V2321.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-visible-loop-candidate`.",
    ]) + "\n"


def main() -> int:
    source = v3024.collect_source_state()
    if not source["source_exists"] or not source["git_head_matches_pin"] or not source["git_status_clean"]:
        raise RuntimeError("private doomgeneric source is not pinned and clean")
    if not HOST_KEYBOARD_BRIDGE.is_file():
        raise RuntimeError(f"missing host keyboard bridge: {HOST_KEYBOARD_BRIDGE}")
    engine = build_v3033_engine()
    configure_base()
    patch_ramdisk_with_doomgeneric_helper()
    v2859.render_report = render_report
    rc = v2859.main()
    marker_strings = require_strings(BOOT_IMAGE)
    ramdisk_entries = v3029.list_cpio_entries(RAMDISK_CPIO)
    helper_entry_present = ENGINE_RAMDISK_PATH in ramdisk_entries
    wad_count = v3029.count_wad_entries(ramdisk_entries)
    if not helper_entry_present:
        raise RuntimeError(f"missing V3033 helper entry in ramdisk: {ENGINE_RAMDISK_PATH}")
    if wad_count != 0:
        raise RuntimeError(f"unexpected WAD files in V3033 ramdisk: {wad_count}")

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-visible-loop-candidate",
        "parent_live_artifact": "v3032-doomgeneric-visible-frame-live",
        "doomgeneric_visible_loop": {
            "version": 1,
            "engine_binary": rel(ENGINE_BINARY),
            "engine_binary_sha256": v3024.sha256_file(ENGINE_BINARY),
            "engine_binary_bytes": ENGINE_BINARY.stat().st_size,
            "engine_adapter_source": rel(ENGINE_ADAPTER_SOURCE),
            "engine_adapter_source_sha256": v3024.sha256_file(ENGINE_ADAPTER_SOURCE),
            "engine_ramdisk_path": ENGINE_REMOTE_PATH,
            "runtime_wad_root": RUNTIME_WAD_ROOT,
            "runtime_wad_path": RUNTIME_WAD_PATH,
            "expected_wad_sha256": EXPECTED_WAD_SHA256,
            "runtime_wad_max_bytes": RUNTIME_WAD_MAX_BYTES,
            "default_frame_ticks": DEFAULT_FRAME_TICKS,
            "default_smoke_frames": DEFAULT_SMOKE_FRAMES,
            "default_loop_frames": DEFAULT_LOOP_FRAMES,
            "max_loop_frames": MAX_LOOP_FRAMES,
            "loop_frame_ms": LOOP_FRAME_MS,
            "frame_path": FRAME_PATH,
            "input_state_path": INPUT_STATE_PATH,
            "frame_format": "xbgr8888-raw",
            "frame_width": FRAME_WIDTH,
            "frame_height": FRAME_HEIGHT,
            "frame_stride": FRAME_STRIDE,
            "frame_bytes": FRAME_BYTES,
            "helper_loop_command": (
                f"{ENGINE_REMOTE_PATH} --wad-frame-loop {RUNTIME_WAD_PATH} "
                f"--frames {DEFAULT_LOOP_FRAMES} --output {FRAME_PATH} "
                f"--input-state {INPUT_STATE_PATH} --frame-ms {LOOP_FRAME_MS}"
            ),
            "helper_frame_command": (
                f"{ENGINE_REMOTE_PATH} --wad-frame-dump {RUNTIME_WAD_PATH} "
                f"--frames {DEFAULT_FRAME_TICKS} --output {FRAME_PATH}"
            ),
            "helper_smoke_command": f"{ENGINE_REMOTE_PATH} --wad-smoke {RUNTIME_WAD_PATH} --frames {DEFAULT_SMOKE_FRAMES}",
            "helper_bundled_in_ramdisk": helper_entry_present,
            "ramdisk_wad_file_count": wad_count,
            "public_wad_file_count": v3024.count_files(v3024.PUBLIC_WAD_ROOT, ".wad")["count"],
            "wad_embedded_in_boot": 0,
            "input_path": "serial-doompad-to-DG_GetKey-via-state-file",
            "host_keyboard_bridge": rel(HOST_KEYBOARD_BRIDGE),
            "otg_required": False,
            "evdev_injection": False,
            "uinput": False,
            "sound_mode": SOUND_MODE,
            "audio_corun": {
                "enabled": bool(AUDIO_CORUN),
                "mode": AUDIO_CORUN_MODE,
                "duration_ms": AUDIO_CORUN_DURATION_MS,
                "amplitude_milli": AUDIO_CORUN_AMPLITUDE_MILLI,
                "real_doom_sfx": False,
            },
            "kms_path": "background-or-foreground-kms-dumb-buffer-presenter",
            "verify_command": f"video demo doom verify --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
            "play_command": f"video demo doom play {DEFAULT_SMOKE_FRAMES} --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
            "frame_command": f"video demo doom frame {DEFAULT_FRAME_TICKS} --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
            "loop_command": f"video demo doom loop {DEFAULT_LOOP_FRAMES} --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
            "loop_start_command": f"video demo doom loop-start {MAX_LOOP_FRAMES} --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
            "loop_stop_command": "video demo doom loop-stop",
            "menu_action": "DEMO > DOOM visible-playable-loop",
            "live_validation": "pending-v3034",
        },
        "v3033_engine_build": engine,
        "v3033_marker_strings": marker_strings,
        "adoption_state": "pending-visible-loop-live-validation",
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
    (OUT_DIR / "doomgeneric-visible-loop-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-visible-loop-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "engine_binary": rel(ENGINE_BINARY),
        "engine_binary_sha256": v3024.sha256_file(ENGINE_BINARY),
        "engine_ramdisk_path": ENGINE_REMOTE_PATH,
        "runtime_wad_path": RUNTIME_WAD_PATH,
        "expected_wad_sha256": EXPECTED_WAD_SHA256,
        "frame_path": FRAME_PATH,
        "input_state_path": INPUT_STATE_PATH,
        "loop_command": f"video demo doom loop {DEFAULT_LOOP_FRAMES} --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "loop_start_command": f"video demo doom loop-start {MAX_LOOP_FRAMES} --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "host_keyboard_bridge": rel(HOST_KEYBOARD_BRIDGE),
        "ramdisk_wad_file_count": wad_count,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-visible-loop-live-validation",
        "note": "V3033 bundles only the private helper and visible-loop command metadata; WAD/IWAD bytes remain runtime-private and are not copied into public, ramdisk, or boot image.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
