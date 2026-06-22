#!/usr/bin/env python3
"""Build V3100 native-init DOOM tick/draw/dump phase telemetry candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v3098_doomgeneric_gametic_frame_telemetry as v3098
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3100"
INIT_VERSION = "0.10.106"
INIT_BUILD = "v3100-doomgeneric-phase-telemetry"
BUILD_TAG = INIT_BUILD
DECISION = "v3100-doomgeneric-phase-telemetry-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3100_DOOMGENERIC_PHASE_TELEMETRY_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3100_doomgeneric_phase_telemetry.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3100_doomgeneric_phase_telemetry"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3100_doomgeneric_phase_telemetry.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v517_doomgeneric_phase_telemetry"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3100"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3100.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3100.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3100"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3100-phase-telemetry"

RUNTIME_WAD_ROOT = v3098.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3098.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3098.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3098.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3098.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3098.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = v3098.DEFAULT_LOOP_FRAMES
CONTINUOUS_LOOP_FRAMES = v3098.CONTINUOUS_LOOP_FRAMES
MAX_LOOP_FRAMES = v3098.MAX_LOOP_FRAMES
LOOP_FRAME_MS = v3098.LOOP_FRAME_MS
PRESENTER_POLL_MS = v3098.PRESENTER_POLL_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3100-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3100-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3100-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3100-input.sock"
INPUT_UDP_PORT = v3098.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3098.DEVICE_NCM_HOST
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3100-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3100-tick-telemetry.txt"
PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = v3098.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS
BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = v3098.BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS
FRAME_WIDTH = v3098.FRAME_WIDTH
FRAME_HEIGHT = v3098.FRAME_HEIGHT
FRAME_STRIDE = v3098.FRAME_STRIDE
FRAME_BYTES = v3098.FRAME_BYTES
NATIVE_DASHBOARD = v3098.NATIVE_DASHBOARD
NATIVE_DASHBOARD_MINIMAL = v3098.NATIVE_DASHBOARD_MINIMAL
NATIVE_DASHBOARD_LARGE_FRAME = v3098.NATIVE_DASHBOARD_LARGE_FRAME
BASELINE_NATIVE_DASHBOARD_LARGE_FRAME = v3098.BASELINE_NATIVE_DASHBOARD_LARGE_FRAME
NATIVE_DOOM_PRESENT_PAGEFLIP = v3098.NATIVE_DOOM_PRESENT_PAGEFLIP
BASELINE_FRAME_SCALE = v3098.BASELINE_FRAME_SCALE
FRAME_SCALE = v3098.FRAME_SCALE
SCALE_PATH = v3098.SCALE_PATH
REUSE_FRAME_BUFFER = v3098.REUSE_FRAME_BUFFER
DASHBOARD_METRICS_INTERVAL_FRAMES = v3098.DASHBOARD_METRICS_INTERVAL_FRAMES
FRAME_TIMING_PROBE = v3098.FRAME_TIMING_PROBE
SEQ_TELEMETRY = v3098.SEQ_TELEMETRY
BASELINE_BACKGROUND_CANCEL = v3098.BASELINE_BACKGROUND_CANCEL
CANDIDATE_BACKGROUND_CANCEL = v3098.CANDIDATE_BACKGROUND_CANCEL

SOUND_MODE = v3098.SOUND_MODE
AUDIO_CORUN = v3098.AUDIO_CORUN
AUDIO_CORUN_MODE = v3098.AUDIO_CORUN_MODE
AUDIO_CORUN_DURATION_MS = v3098.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3098.AUDIO_CORUN_AMPLITUDE_MILLI

HOST_KEYBOARD_BRIDGE = v3098.HOST_KEYBOARD_BRIDGE
HOST_DASHBOARD = v3098.HOST_DASHBOARD
V3059 = v3098.V3059

TICK_TELEMETRY_MARKER = "a90.doomgeneric.v3100.tick_telemetry=tick-draw-dump-phase-summary"
SCALE_1TO1_MARKER = "a90.doomgeneric.v3100.scale=large-frame-off-1to1"
GAMETIC_FRAME_TELEMETRY_MARKER = (
    "a90.doomgeneric.v3100.gametic_frame_telemetry=loop-dump-gametic-summary"
)
PHASE_TELEMETRY_MARKER = "a90.doomgeneric.v3100.phase_telemetry=tick-draw-dump-split"
SEQ_TELEMETRY_CONTRACT = v3098.SEQ_TELEMETRY_CONTRACT
SEQ_TELEMETRY_MODEL = v3098.SEQ_TELEMETRY_MODEL

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.106 (v3100-doomgeneric-phase-telemetry)",
    b"v3100-doomgeneric-phase-telemetry",
    b"doomgeneric-private-link-v3100-phase-telemetry",
    b"/bin/a90_doomgeneric_private_engine_v3100",
    RUNTIME_WAD_PATH.encode("ascii"),
    EXPECTED_WAD_SHA256.encode("ascii"),
    FRAME_PATH.encode("ascii"),
    SHARED_FRAME_PATH.encode("ascii"),
    INPUT_STATE_PATH.encode("ascii"),
    INPUT_SOCKET_PATH.encode("ascii"),
    PACE_SOCKET_PATH.encode("ascii"),
    TICK_TELEMETRY_PATH.encode("ascii"),
    TICK_TELEMETRY_MARKER.encode("ascii"),
    SCALE_1TO1_MARKER.encode("ascii"),
    GAMETIC_FRAME_TELEMETRY_MARKER.encode("ascii"),
    PHASE_TELEMETRY_MARKER.encode("ascii"),
    b"a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback",
    b"a90.doomgeneric.v3079.pace=presenter-pageflip-token",
    b"a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq",
    b"--shared-frame",
    b"shared-mmap-copy",
    b"video.demo.doom.dashboard.large_frame=0",
    b"video.demo.doom.dashboard.frame_scale=1:1",
    SEQ_TELEMETRY_CONTRACT.encode("ascii"),
    SEQ_TELEMETRY_MODEL.encode("ascii"),
    b"loop_tick.samples=%u",
    b"loop_tick.gametic_changed=%u",
    b"loop_tick.draw_changed_iterations=%u",
    b"draw_gametic.samples=%u",
    b"draw_gametic.changed_transitions=%u",
    b"dump_gametic.samples=%u",
    b"dump_gametic.repeated_transitions=%u",
    b"video.demo.doom.loop_start.background_cancel=disabled-serial-preserve",
    b"video.demo.doom.loop.frame_ipc=",
    b"video.demo.doom.loop.timing_probe=1",
    b"native-audio-corun-tone-v3053",
)


def rel(path: Path) -> str:
    return v3098.rel(path)


def v3033_module() -> Any:
    return v3098.v3033_module()


def _replace_required(source: str, old: str, new: str) -> str:
    if old not in source:
        raise RuntimeError(f"missing V3100 adapter source anchor: {old[:96]!r}")
    return source.replace(old, new, 1)


def _phase_struct(prefix: str) -> str:
    return (
        f"static uint32_t {prefix}_samples;\n"
        f"static uint32_t {prefix}_changed_transitions;\n"
        f"static uint32_t {prefix}_repeated_transitions;\n"
        f"static uint32_t {prefix}_positive_delta_total;\n"
        f"static uint32_t {prefix}_max_delta;\n"
        f"static uint32_t {prefix}_reset_transitions;\n"
        f"static uint32_t {prefix}_same_run_current;\n"
        f"static uint32_t {prefix}_max_same_run;\n"
        f"static int {prefix}_first;\n"
        f"static int {prefix}_last;\n"
        f"static int {prefix}_previous;\n"
    )


def _phase_reset(prefix: str) -> str:
    return (
        f"    {prefix}_samples = 0;\n"
        f"    {prefix}_changed_transitions = 0;\n"
        f"    {prefix}_repeated_transitions = 0;\n"
        f"    {prefix}_positive_delta_total = 0;\n"
        f"    {prefix}_max_delta = 0;\n"
        f"    {prefix}_reset_transitions = 0;\n"
        f"    {prefix}_same_run_current = 0;\n"
        f"    {prefix}_max_same_run = 0;\n"
        f"    {prefix}_first = -1;\n"
        f"    {prefix}_last = -1;\n"
        f"    {prefix}_previous = -1;\n"
    )


def v3100_adapter_source() -> str:
    source = v3098.v3098_adapter_source()
    source = source.replace(v3098.TICK_TELEMETRY_MARKER, TICK_TELEMETRY_MARKER)
    source = source.replace(v3098.SCALE_1TO1_MARKER, SCALE_1TO1_MARKER)
    source = source.replace(v3098.GAMETIC_FRAME_TELEMETRY_MARKER, GAMETIC_FRAME_TELEMETRY_MARKER)
    source = source.replace(v3098.TICK_TELEMETRY_PATH, TICK_TELEMETRY_PATH)
    source = _replace_required(
        source,
        'const char a90_doomgeneric_v3098_gametic_frame_policy[] =\n'
        f'    "{GAMETIC_FRAME_TELEMETRY_MARKER}";\n',
        'const char a90_doomgeneric_v3098_gametic_frame_policy[] =\n'
        f'    "{GAMETIC_FRAME_TELEMETRY_MARKER}";\n'
        'const char a90_doomgeneric_v3100_phase_policy[] =\n'
        f'    "{PHASE_TELEMETRY_MARKER}";\n',
    )
    source = _replace_required(
        source,
        "static int frame_gametic_previous;\n",
        "static int frame_gametic_previous;\n"
        + _phase_struct("draw_gametic")
        + "static uint32_t loop_tick_samples;\n"
        + "static uint32_t loop_tick_gametic_changed;\n"
        + "static uint32_t loop_tick_gametic_repeated;\n"
        + "static uint32_t loop_tick_gametic_positive_delta_total;\n"
        + "static uint32_t loop_tick_gametic_max_delta;\n"
        + "static uint32_t loop_tick_gametic_reset;\n"
        + "static uint32_t loop_tick_draw_changed_iterations;\n"
        + "static uint32_t loop_tick_draw_unchanged_iterations;\n"
        + "static uint32_t loop_tick_draw_delta_total;\n"
        + "static uint32_t loop_tick_draw_max_delta;\n",
    )
    source = _replace_required(
        source,
        "void DG_DrawFrame(void) {\n",
        "static void a90_doomgeneric_record_phase_gametic(\n"
        "        const char *label,\n"
        "        uint32_t *samples,\n"
        "        uint32_t *changed_transitions,\n"
        "        uint32_t *repeated_transitions,\n"
        "        uint32_t *positive_delta_total,\n"
        "        uint32_t *max_delta,\n"
        "        uint32_t *reset_transitions,\n"
        "        uint32_t *same_run_current,\n"
        "        uint32_t *max_same_run,\n"
        "        int *first,\n"
        "        int *last,\n"
        "        int *previous,\n"
        "        int current);\n\n"
        "void DG_DrawFrame(void) {\n",
    )
    source = _replace_required(
        source,
        "    frame_gametic_previous = -1;\n"
        "    frame_checksum = 0;\n",
        "    frame_gametic_previous = -1;\n"
        + _phase_reset("draw_gametic")
        + "    loop_tick_samples = 0;\n"
        + "    loop_tick_gametic_changed = 0;\n"
        + "    loop_tick_gametic_repeated = 0;\n"
        + "    loop_tick_gametic_positive_delta_total = 0;\n"
        + "    loop_tick_gametic_max_delta = 0;\n"
        + "    loop_tick_gametic_reset = 0;\n"
        + "    loop_tick_draw_changed_iterations = 0;\n"
        + "    loop_tick_draw_unchanged_iterations = 0;\n"
        + "    loop_tick_draw_delta_total = 0;\n"
        + "    loop_tick_draw_max_delta = 0;\n"
        + "    frame_checksum = 0;\n",
    )
    source = _replace_required(
        source,
        "static void a90_doomgeneric_record_frame_gametic(void) {\n",
        "static void a90_doomgeneric_record_phase_gametic(\n"
        "        const char *label,\n"
        "        uint32_t *samples,\n"
        "        uint32_t *changed_transitions,\n"
        "        uint32_t *repeated_transitions,\n"
        "        uint32_t *positive_delta_total,\n"
        "        uint32_t *max_delta,\n"
        "        uint32_t *reset_transitions,\n"
        "        uint32_t *same_run_current,\n"
        "        uint32_t *max_same_run,\n"
        "        int *first,\n"
        "        int *last,\n"
        "        int *previous,\n"
        "        int current) {\n"
        "    (void)label;\n"
        "    if (samples == NULL || changed_transitions == NULL || repeated_transitions == NULL ||\n"
        "        positive_delta_total == NULL || max_delta == NULL || reset_transitions == NULL ||\n"
        "        same_run_current == NULL || max_same_run == NULL || first == NULL ||\n"
        "        last == NULL || previous == NULL) {\n"
        "        return;\n"
        "    }\n"
        "    ++*samples;\n"
        "    if (*samples == 1U) {\n"
        "        *first = current;\n"
        "        *last = current;\n"
        "        *previous = current;\n"
        "        *same_run_current = 1U;\n"
        "        *max_same_run = 1U;\n"
        "        return;\n"
        "    }\n"
        "    if (current == *previous) {\n"
        "        ++*repeated_transitions;\n"
        "        ++*same_run_current;\n"
        "    } else {\n"
        "        ++*changed_transitions;\n"
        "        if (current > *previous) {\n"
        "            uint32_t delta = (uint32_t)(current - *previous);\n\n"
        "            *positive_delta_total += delta;\n"
        "            if (delta > *max_delta) {\n"
        "                *max_delta = delta;\n"
        "            }\n"
        "        } else {\n"
        "            ++*reset_transitions;\n"
        "        }\n"
        "        *same_run_current = 1U;\n"
        "        *previous = current;\n"
        "    }\n"
        "    if (*same_run_current > *max_same_run) {\n"
        "        *max_same_run = *same_run_current;\n"
        "    }\n"
        "    *last = current;\n"
        "}\n\n"
        "static void a90_doomgeneric_record_frame_gametic(void) {\n",
    )
    source = _replace_required(
        source,
        "    int current = gametic;\n\n"
        "    ++frame_gametic_samples;\n",
        "    int current = gametic;\n\n"
        "    a90_doomgeneric_record_phase_gametic(\n"
        "        \"dump_gametic\",\n"
        "        &frame_gametic_samples,\n"
        "        &frame_gametic_changed_transitions,\n"
        "        &frame_gametic_repeated_transitions,\n"
        "        &frame_gametic_positive_delta_total,\n"
        "        &frame_gametic_max_delta,\n"
        "        &frame_gametic_reset_transitions,\n"
        "        &frame_gametic_same_run_current,\n"
        "        &frame_gametic_max_same_run,\n"
        "        &frame_gametic_first,\n"
        "        &frame_gametic_last,\n"
        "        &frame_gametic_previous,\n"
        "        current);\n"
        "    return;\n\n"
        "    ++frame_gametic_samples;\n",
    )
    source = _replace_required(
        source,
        "    ++presented_frames;\n"
        "}\n\n"
        "void DG_SleepMs",
        "    ++presented_frames;\n"
        "    a90_doomgeneric_record_phase_gametic(\n"
        "        \"draw_gametic\",\n"
        "        &draw_gametic_samples,\n"
        "        &draw_gametic_changed_transitions,\n"
        "        &draw_gametic_repeated_transitions,\n"
        "        &draw_gametic_positive_delta_total,\n"
        "        &draw_gametic_max_delta,\n"
        "        &draw_gametic_reset_transitions,\n"
        "        &draw_gametic_same_run_current,\n"
        "        &draw_gametic_max_same_run,\n"
        "        &draw_gametic_first,\n"
        "        &draw_gametic_last,\n"
        "        &draw_gametic_previous,\n"
        "        gametic);\n"
        "}\n\n"
        "void DG_SleepMs",
    )
    source = _replace_required(
        source,
        "static int a90_doomgeneric_write_tick_telemetry(const char *path,",
        "static void a90_doomgeneric_record_loop_tick_phase(\n"
        "        int before_gametic,\n"
        "        int after_gametic,\n"
        "        unsigned int before_draws,\n"
        "        unsigned int after_draws) {\n"
        "    ++loop_tick_samples;\n"
        "    if (after_gametic == before_gametic) {\n"
        "        ++loop_tick_gametic_repeated;\n"
        "    } else {\n"
        "        ++loop_tick_gametic_changed;\n"
        "        if (after_gametic > before_gametic) {\n"
        "            uint32_t delta = (uint32_t)(after_gametic - before_gametic);\n\n"
        "            loop_tick_gametic_positive_delta_total += delta;\n"
        "            if (delta > loop_tick_gametic_max_delta) {\n"
        "                loop_tick_gametic_max_delta = delta;\n"
        "            }\n"
        "        } else {\n"
        "            ++loop_tick_gametic_reset;\n"
        "        }\n"
        "    }\n"
        "    if (after_draws > before_draws) {\n"
        "        uint32_t delta = after_draws - before_draws;\n\n"
        "        ++loop_tick_draw_changed_iterations;\n"
        "        loop_tick_draw_delta_total += delta;\n"
        "        if (delta > loop_tick_draw_max_delta) {\n"
        "            loop_tick_draw_max_delta = delta;\n"
        "        }\n"
        "    } else {\n"
        "        ++loop_tick_draw_unchanged_iterations;\n"
        "    }\n"
        "}\n\n"
        "static int a90_doomgeneric_write_tick_telemetry(const char *path,",
    )
    source = _replace_required(
        source,
        """    ok = ok && fprintf(fp, "frame_gametic.samples=%u\\n", frame_gametic_samples) >= 0;\n""",
        f"""    ok = ok && fprintf(fp, "phase_marker={PHASE_TELEMETRY_MARKER}\\n") >= 0;\n"""
        """    ok = ok && fprintf(fp, "loop_tick.samples=%u\\n", loop_tick_samples) >= 0;\n"""
        """    ok = ok && fprintf(fp, "loop_tick.gametic_changed=%u\\n", loop_tick_gametic_changed) >= 0;\n"""
        """    ok = ok && fprintf(fp, "loop_tick.gametic_repeated=%u\\n", loop_tick_gametic_repeated) >= 0;\n"""
        """    ok = ok && fprintf(fp, "loop_tick.gametic_positive_delta_total=%u\\n", loop_tick_gametic_positive_delta_total) >= 0;\n"""
        """    ok = ok && fprintf(fp, "loop_tick.gametic_max_delta=%u\\n", loop_tick_gametic_max_delta) >= 0;\n"""
        """    ok = ok && fprintf(fp, "loop_tick.gametic_reset=%u\\n", loop_tick_gametic_reset) >= 0;\n"""
        """    ok = ok && fprintf(fp, "loop_tick.draw_changed_iterations=%u\\n", loop_tick_draw_changed_iterations) >= 0;\n"""
        """    ok = ok && fprintf(fp, "loop_tick.draw_unchanged_iterations=%u\\n", loop_tick_draw_unchanged_iterations) >= 0;\n"""
        """    ok = ok && fprintf(fp, "loop_tick.draw_delta_total=%u\\n", loop_tick_draw_delta_total) >= 0;\n"""
        """    ok = ok && fprintf(fp, "loop_tick.draw_max_delta=%u\\n", loop_tick_draw_max_delta) >= 0;\n"""
        """    ok = ok && fprintf(fp, "draw_gametic.samples=%u\\n", draw_gametic_samples) >= 0;\n"""
        """    ok = ok && fprintf(fp, "draw_gametic.first=%d\\n", draw_gametic_first) >= 0;\n"""
        """    ok = ok && fprintf(fp, "draw_gametic.last=%d\\n", draw_gametic_last) >= 0;\n"""
        """    ok = ok && fprintf(fp, "draw_gametic.changed_transitions=%u\\n", draw_gametic_changed_transitions) >= 0;\n"""
        """    ok = ok && fprintf(fp, "draw_gametic.repeated_transitions=%u\\n", draw_gametic_repeated_transitions) >= 0;\n"""
        """    ok = ok && fprintf(fp, "draw_gametic.positive_delta_total=%u\\n", draw_gametic_positive_delta_total) >= 0;\n"""
        """    ok = ok && fprintf(fp, "draw_gametic.max_delta=%u\\n", draw_gametic_max_delta) >= 0;\n"""
        """    ok = ok && fprintf(fp, "draw_gametic.reset_transitions=%u\\n", draw_gametic_reset_transitions) >= 0;\n"""
        """    ok = ok && fprintf(fp, "draw_gametic.max_same_run=%u\\n", draw_gametic_max_same_run) >= 0;\n"""
        """    ok = ok && fprintf(fp, "draw_gametic.transition_samples=%u\\n",\n"""
        """                      draw_gametic_changed_transitions +\n"""
        """                      draw_gametic_repeated_transitions) >= 0;\n"""
        """    ok = ok && fprintf(fp, "dump_gametic.samples=%u\\n", frame_gametic_samples) >= 0;\n"""
        """    ok = ok && fprintf(fp, "frame_gametic.samples=%u\\n", frame_gametic_samples) >= 0;\n""",
    )
    source = source.replace("frame_gametic.", "dump_gametic.")
    source = _replace_required(
        source,
        "        marker_checksum(a90_doomgeneric_v3098_gametic_frame_policy) == 0U) {\n",
        "        marker_checksum(a90_doomgeneric_v3098_gametic_frame_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3100_phase_policy) == 0U) {\n",
    )
    source = _replace_required(
        source,
        "        if (input_socket_fd < 0 && input_udp_fd < 0) {\n"
        "            a90_doomgeneric_apply_input_state_file(input_state_path);\n"
        "        }\n"
        "        doomgeneric_Tick();\n"
        "        if (a90_doomgeneric_presented_frames() > 0U) {\n",
        "        {\n"
        "            int before_gametic = gametic;\n"
        "            unsigned int before_draws = a90_doomgeneric_presented_frames();\n\n"
        "            if (input_socket_fd < 0 && input_udp_fd < 0) {\n"
        "                a90_doomgeneric_apply_input_state_file(input_state_path);\n"
        "            }\n"
        "            doomgeneric_Tick();\n"
        "            a90_doomgeneric_record_loop_tick_phase(\n"
        "                before_gametic,\n"
        "                gametic,\n"
        "                before_draws,\n"
        "                a90_doomgeneric_presented_frames());\n"
        "        }\n"
        "        if (a90_doomgeneric_presented_frames() > 0U) {\n",
    )
    return source


def apply_v3100_globals() -> None:
    v3098.apply_v3098_globals()
    v3098.v3096.v3086.CYCLE = CYCLE
    v3098.v3096.v3086.INIT_VERSION = INIT_VERSION
    v3098.v3096.v3086.INIT_BUILD = INIT_BUILD
    v3098.v3096.v3086.BUILD_TAG = BUILD_TAG
    v3098.v3096.v3086.DECISION = DECISION
    v3098.v3096.v3086.OUT_DIR = OUT_DIR
    v3098.v3096.v3086.OBJ_DIR = OBJ_DIR
    v3098.v3096.v3086.REPORT_PATH = REPORT_PATH
    v3098.v3096.v3086.BOOT_IMAGE = BOOT_IMAGE
    v3098.v3096.v3086.INIT_BINARY = INIT_BINARY
    v3098.v3096.v3086.RAMDISK_CPIO = RAMDISK_CPIO
    v3098.v3096.v3086.HELPER_BINARY = HELPER_BINARY
    v3098.v3096.v3086.ENGINE_BINARY = ENGINE_BINARY
    v3098.v3096.v3086.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3098.v3096.v3086.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3098.v3096.v3086.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3098.v3096.v3086.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3098.v3096.v3086.ENGINE_NAME = ENGINE_NAME
    v3098.v3096.v3086.FRAME_PATH = FRAME_PATH
    v3098.v3096.v3086.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    v3098.v3096.v3086.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3098.v3096.v3086.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3098.v3096.v3086.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    v3098.v3096.v3086.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3098.v3096.v3086.render_report = render_report
    v3098.v3096.v3086.v3084.v3083.v3081.v3081_adapter_source = v3100_adapter_source
    v3098.v3096._set_large_frame(NATIVE_DASHBOARD_LARGE_FRAME)
    v3098.v3096._set_seq_telemetry(SEQ_TELEMETRY)
    v3098.v3096.v3086.apply_v3086_globals()
    v3098.v3096._set_large_frame(NATIVE_DASHBOARD_LARGE_FRAME)
    v3098.v3096._set_seq_telemetry(SEQ_TELEMETRY)
    V3059.v3059_adapter_source = v3100_adapter_source


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3100 DOOMGENERIC Phase Telemetry Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback / DOOM tick-vs-draw cadence isolation.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps V3098's 1:1 dashboard scale, pageflip cadence, shared-frame sequence telemetry, timing probe, audio corun, and UDP/NCM input.",
        "- Splits helper telemetry into `loop_tick.*`, `draw_gametic.*`, and `dump_gametic.*` so frame writes can be separated from real `DG_DrawFrame()` calls.",
        "- Purpose: correct the V3099 ambiguity where `frame_gametic.*` sampled dump/write loop iterations, not necessarily actual engine draw calls.",
        "",
        "## Telemetry Contract",
        "",
        f"- Tick telemetry marker: `{TICK_TELEMETRY_MARKER}`",
        f"- Phase telemetry marker: `{PHASE_TELEMETRY_MARKER}`",
        f"- Dump gametic marker: `{GAMETIC_FRAME_TELEMETRY_MARKER}`",
        f"- Telemetry path: `{TICK_TELEMETRY_PATH}`",
        "- Captured fields: `loop_tick.*`, `draw_gametic.*`, and `dump_gametic.*`.",
        "- Fake time model remains `DG_SleepMs-accumulated`.",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Helper loop command: `{doom.get('helper_loop_command')}`",
        f"- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}`",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Validation",
        "",
        "- `py_compile`: V3100 builder and focused tests.",
        "- `unittest`: V3100 source contract plus current DOOM cadence lineage regressions.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3100 identity, phase telemetry marker/fields, 1:1 scale marker, sequence telemetry markers, shared-frame markers, pace/pageflip markers, timing probe, audio marker, and UDP input markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3101`",
        "- Type: rollback-gated live validation.",
        "- Scope: flash exact V3100 boot image via `native_init_flash.py`, health-check, run bounded DOOM loops, then compare `loop_tick.*`, `draw_gametic.*`, and `dump_gametic.*`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-phase-telemetry-candidate`.",
    ]) + "\n"


def main() -> int:
    apply_v3100_globals()
    rc = v3098.v3096.v3086.v3084.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "pageflip_min_submit_interval_ms": PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "pageflip_min_submit_interval_baseline_ms": BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "cadence_experiment": "tick-draw-dump-phase-telemetry",
        "tick_telemetry_marker": TICK_TELEMETRY_MARKER,
        "phase_telemetry_marker": PHASE_TELEMETRY_MARKER,
        "gametic_frame_telemetry_marker": GAMETIC_FRAME_TELEMETRY_MARKER,
        "seq_telemetry_contract": SEQ_TELEMETRY_CONTRACT,
        "seq_telemetry_model": SEQ_TELEMETRY_MODEL,
        "seq_telemetry_enabled": bool(SEQ_TELEMETRY),
        "tick_telemetry_path": TICK_TELEMETRY_PATH,
        "fake_time_model": "DG_SleepMs-accumulated",
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "baseline_native_dashboard_large_frame": bool(BASELINE_NATIVE_DASHBOARD_LARGE_FRAME),
        "baseline_frame_scale": BASELINE_FRAME_SCALE,
        "frame_scale": FRAME_SCALE,
        "scale_path": SCALE_PATH,
        "helper_loop_command": (
            f"{ENGINE_REMOTE_PATH} --wad-frame-loop {RUNTIME_WAD_PATH} "
            f"--frames {DEFAULT_LOOP_FRAMES} --output {FRAME_PATH} "
            f"--input-state {INPUT_STATE_PATH} --frame-ms {LOOP_FRAME_MS} "
            f"--input-socket {INPUT_SOCKET_PATH} --pace-socket {PACE_SOCKET_PATH} "
            f"--shared-frame {SHARED_FRAME_PATH} --input-udp {INPUT_UDP_PORT}"
        ),
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-phase-telemetry-candidate",
        "adoption_state": "pending-phase-telemetry-live-validation",
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
    (OUT_DIR / "doomgeneric-phase-telemetry-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-phase-telemetry-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "engine_binary": rel(ENGINE_BINARY),
        "engine_ramdisk_path": ENGINE_REMOTE_PATH,
        "runtime_wad_path": RUNTIME_WAD_PATH,
        "expected_wad_sha256": EXPECTED_WAD_SHA256,
        "frame_path": FRAME_PATH,
        "shared_frame_path": SHARED_FRAME_PATH,
        "input_state_path": INPUT_STATE_PATH,
        "input_socket_path": INPUT_SOCKET_PATH,
        "input_udp_host": DEVICE_NCM_HOST,
        "input_udp_port": INPUT_UDP_PORT,
        "pace_socket_path": PACE_SOCKET_PATH,
        "tick_telemetry_marker": TICK_TELEMETRY_MARKER,
        "phase_telemetry_marker": PHASE_TELEMETRY_MARKER,
        "gametic_frame_telemetry_marker": GAMETIC_FRAME_TELEMETRY_MARKER,
        "seq_telemetry_contract": SEQ_TELEMETRY_CONTRACT,
        "seq_telemetry_model": SEQ_TELEMETRY_MODEL,
        "seq_telemetry_enabled": bool(SEQ_TELEMETRY),
        "tick_telemetry_path": TICK_TELEMETRY_PATH,
        "loop_frame_ms": LOOP_FRAME_MS,
        "presenter_poll_ms": PRESENTER_POLL_MS,
        "pageflip_min_submit_interval_baseline_ms": BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "pageflip_min_submit_interval_ms": PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "frame_ipc": v3098.v3096.v3086.v3084.v3083.v3081.CANDIDATE_FRAME_IPC,
        "frame_scale": FRAME_SCALE,
        "scale_path": SCALE_PATH,
        "baseline_frame_scale": BASELINE_FRAME_SCALE,
        "baseline_native_dashboard_large_frame": bool(BASELINE_NATIVE_DASHBOARD_LARGE_FRAME),
        "background_cancel": CANDIDATE_BACKGROUND_CANCEL,
        "present_mode": "pageflip",
        "present_path": "kms-dumb-buffer-pageflip",
        "frame_timing_probe": FRAME_TIMING_PROBE,
        "fake_time_model": "DG_SleepMs-accumulated",
        "native_dashboard": bool(NATIVE_DASHBOARD),
        "native_dashboard_minimal": bool(NATIVE_DASHBOARD_MINIMAL),
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "native_doom_present_pageflip": bool(NATIVE_DOOM_PRESENT_PAGEFLIP),
        "loop_start_command": f"video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "host_keyboard_bridge": rel(HOST_KEYBOARD_BRIDGE),
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-phase-telemetry-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
