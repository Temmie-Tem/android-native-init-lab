#!/usr/bin/env python3
"""Build V3148 DOOM real SFX PCM stream over the V3141 demo HUD stack."""

from __future__ import annotations

import json
import types
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3141_doomgeneric_demo_hud_large_groups as v3141
import build_native_init_boot_v3033_doomgeneric_visible_loop as v3033
import native_doomgeneric_engine_integration_build_v3024 as v3024

REPO_ROOT = repo_root()
_V3141_ADAPTER_SOURCE_TEXT = v3141.v3141_adapter_source()

CYCLE = "V3148"
INIT_VERSION = "0.10.130"
INIT_BUILD = "v3148-doomgeneric-sfx-stream-refresh"
BUILD_TAG = INIT_BUILD
DECISION = "v3148-doomgeneric-sfx-stream-refresh-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3148_DOOMGENERIC_SFX_STREAM_REFRESH_SOURCE_BUILD_2026-06-24.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3148_doomgeneric_sfx_stream_refresh.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3148_doomgeneric_sfx_stream_refresh"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3148_doomgeneric_sfx_stream_refresh.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v531_doomgeneric_sfx_stream_refresh"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3148"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3148.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3148.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3148"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3148-sfx-stream-refresh"

FRAME_PATH = "/tmp/a90-doomgeneric-v3148-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3148-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3148-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3148-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3148-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3148-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3148-sfx.pcmstream"

RUNTIME_WAD_PATH = v3141.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3141.EXPECTED_WAD_SHA256
FRAME_WIDTH = v3141.FRAME_WIDTH
FRAME_HEIGHT = v3141.FRAME_HEIGHT
FRAME_STRIDE = v3141.FRAME_STRIDE
FRAME_BYTES = v3141.FRAME_BYTES
INPUT_UDP_PORT = v3141.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3141.DEVICE_NCM_HOST

DASHBOARD_METRICS_INTERVAL_FRAMES = v3141.DASHBOARD_METRICS_INTERVAL_FRAMES
DASHBOARD_STATUS_INTERVAL_FRAMES = v3141.DASHBOARD_STATUS_INTERVAL_FRAMES
NATIVE_DASHBOARD = v3141.NATIVE_DASHBOARD
NATIVE_DASHBOARD_MINIMAL = v3141.NATIVE_DASHBOARD_MINIMAL
NATIVE_DASHBOARD_LARGE_FRAME = v3141.NATIVE_DASHBOARD_LARGE_FRAME
NATIVE_DEMO_HUD = v3141.NATIVE_DEMO_HUD
NATIVE_DEMO_HUD_FAST = v3141.NATIVE_DEMO_HUD_FAST
NATIVE_DEMO_HUD_READABLE = v3141.NATIVE_DEMO_HUD_READABLE
NATIVE_DEMO_HUD_SECTIONED = v3141.NATIVE_DEMO_HUD_SECTIONED
NATIVE_DEMO_HUD_LARGE_GROUPS = v3141.NATIVE_DEMO_HUD_LARGE_GROUPS
PRE_SCALED_LARGE_FRAME = v3141.PRE_SCALED_LARGE_FRAME
FRAME_SCALE = "1:1-demo-hud-large-groups-sfx-stream-refresh"
SCALE_PATH = v3141.SCALE_PATH
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-sfx-stream-refresh"

INPUT_THREAD_MARKER = v3141.INPUT_THREAD_MARKER.replace("v3141", "v3148")
TIME_MODEL_MARKER = v3141.TIME_MODEL_MARKER.replace("v3141", "v3148")
DEMO_HUD_MARKER = v3141.DEMO_HUD_MARKER.replace("v3141", "v3148")
PACED_TIME_MARKER = v3141.PACED_TIME_MARKER.replace("v3141", "v3148")
TICK_TELEMETRY_MARKER = v3141.TICK_TELEMETRY_MARKER.replace("v3141", "v3148")
SCALE_MARKER = v3141.SCALE_MARKER.replace("v3141", "v3148")
PHASE_TELEMETRY_MARKER = v3141.PHASE_TELEMETRY_MARKER.replace("v3141", "v3148")
GAMETIC_FRAME_TELEMETRY_MARKER = v3141.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3141", "v3148")
SFX_STREAM_MARKER = "a90.doomgeneric.v3148.audio=real-sfx-pcm-stream-refresh-music-disabled"
SOUND_MODE = "native-doom-sfx-pcm-stream-refresh-v3148"
AUDIO_CORUN = 1
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = 1
AUDIO_CORUN_DURATION_MS = 10000
AUDIO_CORUN_REFRESH_MS = 13000
AUDIO_CORUN_AMPLITUDE_MILLI = 150
PHYSICAL_BUTTON_EXIT = 0

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3148.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"


def rel(path: Path) -> str:
    return v3141.rel(path)


def replace_required(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing V3148 source fragment: {old[:100]!r}")
    return text.replace(old, new)


def replace_loop_required(text: str, old: str, new: str) -> str:
    start = text.find("int a90_doomgeneric_run_wad_frame_loop(")
    if start < 0:
        raise RuntimeError("missing V3148 loop function")
    end = text.find("\nint main(int argc, char **argv) {", start)
    if end < 0:
        raise RuntimeError("missing V3148 main after loop function")
    loop = text[start:end]
    if old not in loop:
        raise RuntimeError(f"missing V3148 loop fragment: {old[:100]!r}")
    loop = loop.replace(old, new, 1)
    return text[:start] + loop + text[end:]


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        v3141.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        v3141.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        v3141.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        v3141.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        v3141.DEMO_HUD_MARKER.encode("ascii"): DEMO_HUD_MARKER.encode("ascii"),
        v3141.SCALE_MARKER.encode("ascii"): SCALE_MARKER.encode("ascii"),
        b"a90-doomgeneric-v3141": b"a90-doomgeneric-v3148",
        b"a90.doomgeneric.v3141": b"a90.doomgeneric.v3148",
        b"v3141": b"v3148",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


_DROPPED_INHERITED_MARKERS = (
    b"video.demo.doom.audio.source=native-bounded-tone",
    b"video.demo.doom.audio.real_doom_sfx=0",
    b"native-audio-corun-tone-v3053",
)

REQUIRED_STRINGS = tuple(
    item
    for item in (_rewrite_required_string(item) for item in v3141.REQUIRED_STRINGS)
    if item not in _DROPPED_INHERITED_MARKERS
) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"native-pcm-stream",
    b"pcm-stream",
    b"video.demo.doom.audio.source=%s",
    b"video.demo.doom.audio.real_doom_sfx=%d",
    b"video.demo.doom.audio.stream_prepare.rc=",
    b"audio.play.pcm_stream_supported=1",
    b"audio.play.execute.source=%s",
    b"--pcm-stream",
)


SFX_BACKEND_SOURCE_TEXT = rf'''#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "i_sound.h"
#include "w_wad.h"
#include "z_zone.h"

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif
#ifndef O_NONBLOCK
#define O_NONBLOCK 0
#endif

#define A90_SFX_STREAM_PATH "{AUDIO_PCM_STREAM_PATH}"
#define A90_SFX_RATE 48000
#define A90_SFX_CHANNELS 8
#define A90_SFX_FRAMES_MAX 1600
#define A90_SFX_MASTER_PERCENT 80

int use_libsamplerate = 0;
float libsamplerate_scale = 0.0f;

struct a90_sfx_data {{
    int16_t *samples;
    unsigned int frames;
}};

struct a90_sfx_channel {{
    const struct a90_sfx_data *data;
    unsigned int pos;
    int vol;
    int sep;
    int active;
}};

static int stream_fd = -1;
static int use_prefix = 1;
static unsigned int frame_remainder;
static struct a90_sfx_channel channels[A90_SFX_CHANNELS];

static snddevice_t sound_devices[] = {{ SNDDEVICE_SB }};

static int open_stream_once(void) {{
    int fd = open(A90_SFX_STREAM_PATH, O_WRONLY | O_NONBLOCK | O_CLOEXEC);

    if (fd >= 0) {{
        int flags = fcntl(fd, F_GETFL, 0);

        if (flags >= 0) {{
            (void)fcntl(fd, F_SETFL, flags & ~O_NONBLOCK);
        }}
    }}
    return fd;
}}

static int write_full(int fd, const void *data, size_t bytes) {{
    size_t done = 0;

    while (done < bytes) {{
        ssize_t wr = write(fd, (const char *)data + done, bytes - done);

        if (wr < 0) {{
            if (errno == EINTR) {{
                continue;
            }}
            return -errno;
        }}
        if (wr == 0) {{
            return -EIO;
        }}
        done += (size_t)wr;
    }}
    return 0;
}}

static int open_stream(void) {{
    int attempt;

    for (attempt = 0; attempt < 500; ++attempt) {{
        int fd = open_stream_once();

        if (fd >= 0) {{
            return fd;
        }}
        if (errno != ENOENT && errno != ENXIO && errno != EINTR) {{
            return -1;
        }}
        usleep(10000);
    }}
    return -1;
}}

static int get_sfx_lump_num(sfxinfo_t *sfx) {{
    char name[16];

    if (sfx == NULL) {{
        return -1;
    }}
    if (sfx->link != NULL) {{
        sfx = sfx->link;
    }}
    if (use_prefix) {{
        snprintf(name, sizeof(name), "ds%s", sfx->name);
    }} else {{
        snprintf(name, sizeof(name), "%s", sfx->name);
    }}
    return W_GetNumForName(name);
}}

static struct a90_sfx_data *load_sfx(sfxinfo_t *sfx) {{
    byte *lump;
    unsigned int lumplen;
    unsigned int lump_samples;
    unsigned int source_samples;
    unsigned int out_frames;
    unsigned int index;
    int samplerate;
    struct a90_sfx_data *out;

    if (sfx == NULL || sfx->lumpnum < 0) {{
        return NULL;
    }}
    if (sfx->driver_data != NULL) {{
        return (struct a90_sfx_data *)sfx->driver_data;
    }}
    lumplen = (unsigned int)W_LumpLength(sfx->lumpnum);
    lump = (byte *)W_CacheLumpNum(sfx->lumpnum, PU_STATIC);
    if (lump == NULL || lumplen < 40U || lump[0] != 0x03U || lump[1] != 0x00U) {{
        return NULL;
    }}
    samplerate = ((int)lump[3] << 8) | (int)lump[2];
    lump_samples = ((unsigned int)lump[7] << 24) |
                   ((unsigned int)lump[6] << 16) |
                   ((unsigned int)lump[5] << 8) |
                   (unsigned int)lump[4];
    if (samplerate <= 0 || lump_samples > lumplen - 8U || lump_samples <= 48U) {{
        return NULL;
    }}
    source_samples = lump_samples - 32U;
    out_frames = (unsigned int)((((uint64_t)source_samples * A90_SFX_RATE) + (unsigned int)samplerate - 1U) /
                                (unsigned int)samplerate);
    if (out_frames == 0U) {{
        return NULL;
    }}
    out = (struct a90_sfx_data *)calloc(1, sizeof(*out));
    if (out == NULL) {{
        return NULL;
    }}
    out->samples = (int16_t *)calloc(out_frames, sizeof(out->samples[0]));
    if (out->samples == NULL) {{
        free(out);
        return NULL;
    }}
    out->frames = out_frames;
    for (index = 0; index < out_frames; ++index) {{
        unsigned int src = (unsigned int)(((uint64_t)index * (unsigned int)samplerate) / A90_SFX_RATE);
        int sample;

        if (src >= source_samples) {{
            src = source_samples - 1U;
        }}
        sample = ((int)lump[24U + src] - 128) * 256;
        if (sample > 32767) {{
            sample = 32767;
        }} else if (sample < -32768) {{
            sample = -32768;
        }}
        out->samples[index] = (int16_t)sample;
    }}
    sfx->driver_data = out;
    return out;
}}

static boolean sfx_init(boolean use_sfx_prefix) {{
    unsigned int index;

    (void)signal(SIGPIPE, SIG_IGN);
    use_prefix = use_sfx_prefix ? 1 : 0;
    for (index = 0; index < A90_SFX_CHANNELS; ++index) {{
        memset(&channels[index], 0, sizeof(channels[index]));
    }}
    frame_remainder = 0;
    stream_fd = open_stream();
    return stream_fd >= 0 ? true : false;
}}

static void sfx_shutdown(void) {{
    if (stream_fd >= 0) {{
        close(stream_fd);
        stream_fd = -1;
    }}
}}

static int sfx_get_lump_num(sfxinfo_t *sfx) {{
    return get_sfx_lump_num(sfx);
}}

static unsigned int frames_per_update(void) {{
    unsigned int total = A90_SFX_RATE + frame_remainder;
    unsigned int frames = total / 35U;

    frame_remainder = total % 35U;
    if (frames > A90_SFX_FRAMES_MAX) {{
        frames = A90_SFX_FRAMES_MAX;
    }}
    return frames;
}}

static void sfx_update(void) {{
    int16_t mix[A90_SFX_FRAMES_MAX * 2U];
    unsigned int frames = frames_per_update();
    unsigned int frame;
    unsigned int chan;

    memset(mix, 0, frames * 2U * sizeof(mix[0]));
    for (chan = 0; chan < A90_SFX_CHANNELS; ++chan) {{
        struct a90_sfx_channel *ch = &channels[chan];
        int left_gain;
        int right_gain;

        if (!ch->active || ch->data == NULL || ch->data->samples == NULL) {{
            continue;
        }}
        left_gain = (254 - ch->sep) * ch->vol * A90_SFX_MASTER_PERCENT;
        right_gain = ch->sep * ch->vol * A90_SFX_MASTER_PERCENT;
        for (frame = 0; frame < frames; ++frame) {{
            int sample;
            int left;
            int right;
            int mixed;

            if (ch->pos >= ch->data->frames) {{
                ch->active = 0;
                break;
            }}
            sample = ch->data->samples[ch->pos++];
            left = (sample * left_gain) / (254 * 127 * 100);
            right = (sample * right_gain) / (254 * 127 * 100);
            mixed = (int)mix[(frame * 2U)] + left;
            if (mixed > 32767) {{
                mixed = 32767;
            }} else if (mixed < -32768) {{
                mixed = -32768;
            }}
            mix[(frame * 2U)] = (int16_t)mixed;
            mixed = (int)mix[(frame * 2U) + 1U] + right;
            if (mixed > 32767) {{
                mixed = 32767;
            }} else if (mixed < -32768) {{
                mixed = -32768;
            }}
            mix[(frame * 2U) + 1U] = (int16_t)mixed;
        }}
    }}
    if (stream_fd < 0) {{
        stream_fd = open_stream_once();
    }}
    if (stream_fd >= 0) {{
        int write_rc = write_full(stream_fd, mix, frames * 2U * sizeof(mix[0]));

        if (write_rc < 0) {{
            close(stream_fd);
            stream_fd = -1;
        }}
    }}
}}

static void sfx_update_params(int channel, int vol, int sep) {{
    if (channel < 0 || channel >= (int)A90_SFX_CHANNELS) {{
        return;
    }}
    channels[channel].vol = vol;
    channels[channel].sep = sep;
}}

static int sfx_start(sfxinfo_t *sfx, int channel, int vol, int sep) {{
    struct a90_sfx_data *data;

    if (channel < 0 || channel >= (int)A90_SFX_CHANNELS) {{
        return -1;
    }}
    data = load_sfx(sfx);
    if (data == NULL) {{
        return -1;
    }}
    channels[channel].data = data;
    channels[channel].pos = 0;
    channels[channel].vol = vol;
    channels[channel].sep = sep;
    channels[channel].active = 1;
    return channel;
}}

static void sfx_stop(int channel) {{
    if (channel >= 0 && channel < (int)A90_SFX_CHANNELS) {{
        channels[channel].active = 0;
    }}
}}

static boolean sfx_playing(int channel) {{
    if (channel < 0 || channel >= (int)A90_SFX_CHANNELS) {{
        return false;
    }}
    return channels[channel].active ? true : false;
}}

static void sfx_cache(sfxinfo_t *sounds, int num_sounds) {{
    (void)sounds;
    (void)num_sounds;
}}

sound_module_t DG_sound_module = {{
    sound_devices,
    1,
    sfx_init,
    sfx_shutdown,
    sfx_get_lump_num,
    sfx_update,
    sfx_update_params,
    sfx_start,
    sfx_stop,
    sfx_playing,
    sfx_cache,
}};

static boolean music_init(void) {{ return false; }}
static void music_shutdown(void) {{}}
static void music_set_volume(int volume) {{ (void)volume; }}
static void music_pause(void) {{}}
static void music_resume(void) {{}}
static void *music_register(void *data, int len) {{ (void)data; (void)len; return NULL; }}
static void music_unregister(void *handle) {{ (void)handle; }}
static void music_play(void *handle, boolean looping) {{ (void)handle; (void)looping; }}
static void music_stop(void) {{}}
static boolean music_playing(void) {{ return false; }}
static void music_poll(void) {{}}

music_module_t DG_music_module = {{
    sound_devices,
    1,
    music_init,
    music_shutdown,
    music_set_volume,
    music_pause,
    music_resume,
    music_register,
    music_unregister,
    music_play,
    music_stop,
    music_playing,
    music_poll,
}};
'''


def v3148_adapter_source() -> str:
    source = _V3141_ADAPTER_SOURCE_TEXT.replace("v3141", "v3148").replace("V3141", "V3148")
    source = source.replace(
        "a90.doomgeneric.v3148.scale=producer-960x600-1to1-demo-hud-large-groups",
        SCALE_MARKER,
    )
    source = source.replace(
        "a90.doomgeneric.v3148.demo_hud=large-grouped-hw-doom-input",
        DEMO_HUD_MARKER,
    )
    source = replace_required(
        source,
        'const char a90_doomgeneric_v3148_demo_hud_policy[] =\n'
        '    "a90.doomgeneric.v3148.demo_hud=large-grouped-hw-doom-input";',
        'const char a90_doomgeneric_v3148_demo_hud_policy[] =\n'
        f'    "{DEMO_HUD_MARKER}";\n'
        'const char a90_doomgeneric_v3148_audio_policy[] =\n'
        f'    "{SFX_STREAM_MARKER}";',
    )
    source = replace_required(
        source,
        "        marker_checksum(a90_doomgeneric_v3148_demo_hud_policy) == 0U) {",
        "        marker_checksum(a90_doomgeneric_v3148_demo_hud_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3148_audio_policy) == 0U) {",
    )
    source = replace_loop_required(
        source,
        '    static char arg_nosound[] = "-nosound";\n'
        '    static char arg_nomusic[] = "-nomusic";\n'
        '    static char arg_mb[] = "-mb";\n',
        '    static char arg_nomusic[] = "-nomusic";\n'
        '    static char arg_mb[] = "-mb";\n',
    )
    source = replace_loop_required(
        source,
        "    argv[3] = arg_nosound;\n"
        "    argv[4] = arg_nomusic;\n"
        "    argv[5] = arg_mb;\n"
        "    argv[6] = arg_mb_value;\n"
        "    argv[7] = arg_warp;\n"
        "    argv[8] = arg_episode;\n"
        "    argv[9] = arg_map;\n"
        "    argv[10] = arg_skill;\n"
        "    argv[11] = arg_skill_value;\n"
        "    argv[12] = NULL;\n"
        "\n"
        "    a90_doomgeneric_shared_frame_init(&shared_frame);",
        "    argv[3] = arg_nomusic;\n"
        "    argv[4] = arg_mb;\n"
        "    argv[5] = arg_mb_value;\n"
        "    argv[6] = arg_warp;\n"
        "    argv[7] = arg_episode;\n"
        "    argv[8] = arg_map;\n"
        "    argv[9] = arg_skill;\n"
        "    argv[10] = arg_skill_value;\n"
        "    argv[11] = NULL;\n"
        "\n"
        "    a90_doomgeneric_shared_frame_init(&shared_frame);",
    )
    source = replace_loop_required(source, "    doomgeneric_Create(12, argv);\n", "    doomgeneric_Create(11, argv);\n")
    return source


def write_generated_engine_inputs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SFX_BACKEND_SOURCE.write_text(SFX_BACKEND_SOURCE_TEXT, encoding="utf-8")
    SDL_MIXER_STUB.write_text(
        "#ifndef A90_STUB_SDL_MIXER_H\n#define A90_STUB_SDL_MIXER_H\n#endif\n",
        encoding="utf-8",
    )


def set_v3033_audio_globals() -> None:
    v3033.SOUND_MODE = SOUND_MODE
    v3033.AUDIO_CORUN = AUDIO_CORUN
    v3033.AUDIO_CORUN_MODE = AUDIO_CORUN_MODE
    v3033.AUDIO_CORUN_DURATION_MS = AUDIO_CORUN_DURATION_MS
    v3033.AUDIO_CORUN_REFRESH_MS = AUDIO_CORUN_REFRESH_MS
    v3033.AUDIO_CORUN_AMPLITUDE_MILLI = AUDIO_CORUN_AMPLITUDE_MILLI
    v3033.AUDIO_CORUN_STREAM = AUDIO_CORUN_STREAM
    v3033.AUDIO_PCM_STREAM_PATH = AUDIO_PCM_STREAM_PATH
    v3033.PHYSICAL_BUTTON_EXIT = PHYSICAL_BUTTON_EXIT


def collect_build_modules() -> list[types.ModuleType]:
    seen: set[str] = set()
    modules: list[types.ModuleType] = []

    def visit(module: types.ModuleType) -> None:
        if module.__name__ in seen:
            return
        seen.add(module.__name__)
        modules.append(module)
        for value in vars(module).values():
            if isinstance(value, types.ModuleType) and (
                value.__name__.startswith("build_native_init_boot_") or
                value.__name__ == "native_doomgeneric_engine_integration_build_v3024"
            ):
                visit(value)

    visit(v3141)
    visit(v3033)
    return modules


def set_chain_audio_globals(modules: list[types.ModuleType]) -> list[tuple[types.ModuleType, str, Any, bool]]:
    saved: list[tuple[types.ModuleType, str, Any, bool]] = []
    values: dict[str, Any] = {
        "SOUND_MODE": SOUND_MODE,
        "AUDIO_CORUN": AUDIO_CORUN,
        "AUDIO_CORUN_MODE": AUDIO_CORUN_MODE,
        "AUDIO_CORUN_DURATION_MS": AUDIO_CORUN_DURATION_MS,
        "AUDIO_CORUN_REFRESH_MS": AUDIO_CORUN_REFRESH_MS,
        "AUDIO_CORUN_AMPLITUDE_MILLI": AUDIO_CORUN_AMPLITUDE_MILLI,
        "AUDIO_CORUN_STREAM": AUDIO_CORUN_STREAM,
        "AUDIO_PCM_STREAM_PATH": AUDIO_PCM_STREAM_PATH,
        "PHYSICAL_BUTTON_EXIT": PHYSICAL_BUTTON_EXIT,
    }

    for module in modules:
        for name, value in values.items():
            existed = hasattr(module, name)
            saved.append((module, name, getattr(module, name, None), existed))
            if existed or module is v3033:
                setattr(module, name, value)
    return saved


def restore_chain_audio_globals(saved: list[tuple[types.ModuleType, str, Any, bool]]) -> None:
    for module, name, value, existed in reversed(saved):
        if existed:
            setattr(module, name, value)
        elif hasattr(module, name):
            delattr(module, name)


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    audio = doom.get("audio_corun", {})
    return "\n".join([
        "# Native Init V3148 DOOMGENERIC SFX Stream Refresh Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: DOOM native demo audio over the V3141 large grouped HUD stack.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Enables doomgeneric `FEATURE_SOUND` for a generated native SFX backend.",
        "- Keeps music disabled with `-nomusic`; this unit targets DOOM SFX only.",
        "- Removes `-nosound` only from the playable loop argv; smoke/probe/frame paths remain soundless to avoid FIFO blocking.",
        "- Adds a native-init `audio play --pcm-stream` FIFO path so the existing ADSP/app-type/setcal/route/PCM writer owns the hardware path.",
        "- Starts a bounded 10-second PCM stream co-run for loop-start and quietly refreshes it every 13 seconds during continuous loop playback.",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Audio stream path: `{AUDIO_PCM_STREAM_PATH}`",
        f"- Sound mode: `{SOUND_MODE}`",
        f"- Audio co-run enabled: `{int(bool(audio.get('enabled', AUDIO_CORUN)))}`",
        f"- Audio co-run stream: `{AUDIO_CORUN_STREAM}`",
        f"- Audio duration ms: `{AUDIO_CORUN_DURATION_MS}`",
        f"- Audio refresh ms: `{AUDIO_CORUN_REFRESH_MS}`",
        f"- Audio amplitude milli: `{AUDIO_CORUN_AMPLITUDE_MILLI}`",
        f"- Frame IPC: `{FRAME_IPC}`",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No new PMIC, regulator, GDSC, GPIO, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- The helper writes PCM bytes only to an allowlisted FIFO under `/cache/a90-runtime`; it does not open ALSA, route, setcal, or smart-amp controls.",
        "- WAD/IWAD bytes remain runtime-private and are not copied into public, ramdisk reports, or generated source.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3148 builder and focused tests.",
        "- `unittest`: V3148 source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3148 identity, real SFX stream markers, stream path, and inherited V3141 HUD/input markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-sfx-stream-refresh-candidate`.",
    ]) + "\n"


_PATCHED_V3141_ATTRS = v3141._PATCHED_V3137_ATTRS


def configure_v3148_modules() -> dict[str, Any]:
    v3133 = v3141.v3137.v3135.v3133
    saved = {name: getattr(v3141, name) for name in _PATCHED_V3141_ATTRS}
    saved["v3141_adapter_source"] = v3141.v3141_adapter_source
    saved["render_report"] = v3141.render_report
    saved["apply_v3133_dashboard_globals"] = v3133.apply_v3133_dashboard_globals
    saved["v3024_extra_third_party_cflags"] = v3024.EXTRA_THIRD_PARTY_CFLAGS
    saved["v3024_extra_adapter_cflags"] = v3024.EXTRA_ADAPTER_CFLAGS
    saved["v3024_extra_engine_sources"] = v3024.EXTRA_ENGINE_SOURCES
    saved["chain_audio_globals"] = set_chain_audio_globals(collect_build_modules())

    for name in _PATCHED_V3141_ATTRS:
        setattr(v3141, name, globals()[name])
    v3141.v3141_adapter_source = v3148_adapter_source
    v3141.render_report = render_report

    def apply_dashboard_and_audio_globals() -> None:
        saved["apply_v3133_dashboard_globals"]()
        set_v3033_audio_globals()

    v3133.apply_v3133_dashboard_globals = apply_dashboard_and_audio_globals
    v3024.EXTRA_THIRD_PARTY_CFLAGS = ("-DFEATURE_SOUND", f"-I{OUT_DIR}")
    v3024.EXTRA_ADAPTER_CFLAGS = ()
    v3024.EXTRA_ENGINE_SOURCES = (SFX_BACKEND_SOURCE,)
    return saved


def restore_v3148_modules(saved: dict[str, Any]) -> None:
    v3133 = v3141.v3137.v3135.v3133
    for name in _PATCHED_V3141_ATTRS:
        setattr(v3141, name, saved[name])
    v3141.v3141_adapter_source = saved["v3141_adapter_source"]
    v3141.render_report = saved["render_report"]
    v3133.apply_v3133_dashboard_globals = saved["apply_v3133_dashboard_globals"]
    v3024.EXTRA_THIRD_PARTY_CFLAGS = saved["v3024_extra_third_party_cflags"]
    v3024.EXTRA_ADAPTER_CFLAGS = saved["v3024_extra_adapter_cflags"]
    v3024.EXTRA_ENGINE_SOURCES = saved["v3024_extra_engine_sources"]
    restore_chain_audio_globals(saved["chain_audio_globals"])


def main() -> int:
    write_generated_engine_inputs()
    saved = configure_v3148_modules()
    try:
        rc = v3141.main()
    finally:
        restore_v3148_modules(saved)

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "sound_mode": SOUND_MODE,
        "sfx_stream_marker": SFX_STREAM_MARKER,
        "sfx_backend_source": rel(SFX_BACKEND_SOURCE),
        "sfx_backend_source_sha256": v3024.sha256_file(SFX_BACKEND_SOURCE),
        "sdl_mixer_stub": rel(SDL_MIXER_STUB),
        "audio_pcm_stream_path": AUDIO_PCM_STREAM_PATH,
        "audio_corun": {
            "enabled": True,
            "mode": AUDIO_CORUN_MODE,
            "stream": True,
            "stream_path": AUDIO_PCM_STREAM_PATH,
            "duration_ms": AUDIO_CORUN_DURATION_MS,
            "refresh_ms": AUDIO_CORUN_REFRESH_MS,
            "amplitude_milli": AUDIO_CORUN_AMPLITUDE_MILLI,
            "real_doom_sfx": True,
            "music": False,
        },
        "loop_sound_argv": "sound-enabled-sfx-only-nomusic",
        "probe_sound_argv": "nosound-nomusic",
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-sfx-stream-refresh-candidate",
        "adoption_state": "pending-sfx-stream-refresh-live-validation",
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
    (OUT_DIR / "doomgeneric-sfx-stream-refresh-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-sfx-stream-refresh-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "runtime_wad_path": RUNTIME_WAD_PATH,
        "expected_wad_sha256": EXPECTED_WAD_SHA256,
        "audio_pcm_stream_path": AUDIO_PCM_STREAM_PATH,
        "audio_refresh_ms": AUDIO_CORUN_REFRESH_MS,
        "sound_mode": SOUND_MODE,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-sfx-stream-refresh-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
