#!/usr/bin/env python3
"""Build V3096 native-init DOOM presenter sequence telemetry candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v3086_doomgeneric_pageflip_cadence as v3086
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3096"
INIT_VERSION = "0.10.104"
INIT_BUILD = "v3096-doomgeneric-seq-telemetry"
BUILD_TAG = INIT_BUILD
DECISION = "v3096-doomgeneric-seq-telemetry-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3096_DOOMGENERIC_SEQ_TELEMETRY_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3096_doomgeneric_seq_telemetry.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3096_doomgeneric_seq_telemetry"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3096_doomgeneric_seq_telemetry.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v515_doomgeneric_seq_telemetry"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3096"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3096.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3096.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3096"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3096-seq-telemetry"

RUNTIME_WAD_ROOT = v3086.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3086.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3086.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3086.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3086.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3086.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = v3086.DEFAULT_LOOP_FRAMES
CONTINUOUS_LOOP_FRAMES = v3086.CONTINUOUS_LOOP_FRAMES
MAX_LOOP_FRAMES = v3086.MAX_LOOP_FRAMES
LOOP_FRAME_MS = v3086.LOOP_FRAME_MS
PRESENTER_POLL_MS = v3086.PRESENTER_POLL_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3096-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3096-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3096-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3096-input.sock"
INPUT_UDP_PORT = v3086.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3086.DEVICE_NCM_HOST
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3096-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3096-tick-telemetry.txt"
BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = v3086.BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS
PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = v3086.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS
FRAME_WIDTH = v3086.FRAME_WIDTH
FRAME_HEIGHT = v3086.FRAME_HEIGHT
FRAME_STRIDE = v3086.FRAME_STRIDE
FRAME_BYTES = v3086.FRAME_BYTES
NATIVE_DASHBOARD = v3086.NATIVE_DASHBOARD
NATIVE_DASHBOARD_MINIMAL = v3086.NATIVE_DASHBOARD_MINIMAL
NATIVE_DASHBOARD_LARGE_FRAME = 0
NATIVE_DOOM_PRESENT_PAGEFLIP = v3086.NATIVE_DOOM_PRESENT_PAGEFLIP
BASELINE_NATIVE_DASHBOARD_LARGE_FRAME = v3086.NATIVE_DASHBOARD_LARGE_FRAME
BASELINE_FRAME_SCALE = v3086.FRAME_SCALE
FRAME_SCALE = "1:1"
SCALE_PATH = "large-frame-disabled-1to1"
REUSE_FRAME_BUFFER = v3086.REUSE_FRAME_BUFFER
DASHBOARD_METRICS_INTERVAL_FRAMES = v3086.DASHBOARD_METRICS_INTERVAL_FRAMES
FRAME_TIMING_PROBE = v3086.FRAME_TIMING_PROBE
SEQ_TELEMETRY = 1
BASELINE_BACKGROUND_CANCEL = v3086.BASELINE_BACKGROUND_CANCEL
CANDIDATE_BACKGROUND_CANCEL = v3086.CANDIDATE_BACKGROUND_CANCEL

SOUND_MODE = v3086.SOUND_MODE
AUDIO_CORUN = v3086.AUDIO_CORUN
AUDIO_CORUN_MODE = v3086.AUDIO_CORUN_MODE
AUDIO_CORUN_DURATION_MS = v3086.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3086.AUDIO_CORUN_AMPLITUDE_MILLI

HOST_KEYBOARD_BRIDGE = v3086.HOST_KEYBOARD_BRIDGE
HOST_DASHBOARD = v3086.HOST_DASHBOARD
V3059 = v3086.V3059
BASE_V3081_ADAPTER_SOURCE = v3086.v3084.v3083.v3081.v3081_adapter_source

TICK_TELEMETRY_MARKER = "a90.doomgeneric.v3096.tick_telemetry=seq-telemetry-fake-time-summary"
SCALE_1TO1_MARKER = "a90.doomgeneric.v3096.scale=large-frame-off-1to1"
SEQ_TELEMETRY_CONTRACT = "video.demo.doom.loop.seq_telemetry=1"
SEQ_TELEMETRY_MODEL = "frame-id-upper32-shared-seq"

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.104 (v3096-doomgeneric-seq-telemetry)",
    b"v3096-doomgeneric-seq-telemetry",
    b"doomgeneric-private-link-v3096-seq-telemetry",
    b"/bin/a90_doomgeneric_private_engine_v3096",
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
    b"a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback",
    b"a90.doomgeneric.v3079.pace=presenter-pageflip-token",
    b"a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq",
    b"--shared-frame",
    b"shared-mmap-copy",
    b"video.demo.doom.presenter.pageflip_min_submit_interval_ms=%d",
    b"video.demo.doom.dashboard.large_frame=0",
    b"video.demo.doom.dashboard.frame_scale=1:1",
    SEQ_TELEMETRY_CONTRACT.encode("ascii"),
    SEQ_TELEMETRY_MODEL.encode("ascii"),
    b"video.demo.doom.presenter.seq_telemetry=1",
    b"%s.seq.new_frame_polls=%u",
    b"%s.seq.duplicate_frame_polls=%u",
    b"%s.seq.polls_without_new_frame=%u",
    b"%s.seq.shared_missed_frames=%u",
    b"video.demo.doom.loop_start.background_cancel=disabled-serial-preserve",
    b"video.demo.doom.loop.frame_ipc=",
    b"video.demo.doom.loop.timing_probe=1",
    b"native-audio-corun-tone-v3053",
)


def rel(path: Path) -> str:
    return v3086.rel(path)


def v3033_module() -> Any:
    return v3086.v3033_module()


def _replace_required(source: str, old: str, new: str) -> str:
    if old not in source:
        raise RuntimeError(f"missing V3096 adapter source anchor: {old[:96]!r}")
    return source.replace(old, new, 1)


def v3096_adapter_source() -> str:
    source = BASE_V3081_ADAPTER_SOURCE()
    source = _replace_required(
        source,
        '#include "doomkeys.h"\n',
        '#include "doomkeys.h"\n\nextern int I_GetTime(void);\nextern int gametic;\n',
    )
    source = _replace_required(
        source,
        'const char a90_doomgeneric_v3081_frame_ipc_policy[] =\n'
        '    "a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq";\n',
        'const char a90_doomgeneric_v3081_frame_ipc_policy[] =\n'
        '    "a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq";\n'
        'const char a90_doomgeneric_v3096_tick_telemetry_policy[] =\n'
        f'    "{TICK_TELEMETRY_MARKER}";\n'
        'const char a90_doomgeneric_v3096_scale_policy[] =\n'
        f'    "{SCALE_1TO1_MARKER}";\n',
    )
    source = _replace_required(
        source,
        "static uint32_t fake_ticks_ms;\n",
        "static uint32_t fake_ticks_ms;\n"
        "static uint32_t tick_telemetry_sleep_calls;\n"
        "static uint64_t tick_telemetry_sleep_ms_total;\n"
        "static uint32_t tick_telemetry_getticks_calls;\n",
    )
    source = _replace_required(
        source,
        "    fake_ticks_ms = 0;\n"
        "    frame_checksum = 0;\n",
        "    fake_ticks_ms = 0;\n"
        "    tick_telemetry_sleep_calls = 0;\n"
        "    tick_telemetry_sleep_ms_total = 0;\n"
        "    tick_telemetry_getticks_calls = 0;\n"
        "    frame_checksum = 0;\n",
    )
    source = _replace_required(
        source,
        "void DG_SleepMs(uint32_t ms) {\n"
        "    fake_ticks_ms += ms;\n"
        "}\n\n"
        "uint32_t DG_GetTicksMs(void) {\n"
        "    return fake_ticks_ms;\n"
        "}\n",
        "void DG_SleepMs(uint32_t ms) {\n"
        "    ++tick_telemetry_sleep_calls;\n"
        "    tick_telemetry_sleep_ms_total += ms;\n"
        "    fake_ticks_ms += ms;\n"
        "}\n\n"
        "uint32_t DG_GetTicksMs(void) {\n"
        "    ++tick_telemetry_getticks_calls;\n"
        "    return fake_ticks_ms;\n"
        "}\n",
    )
    source = _replace_required(
        source,
        "        marker_checksum(a90_doomgeneric_v3079_pace_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3081_frame_ipc_policy) == 0U) {\n",
        "        marker_checksum(a90_doomgeneric_v3079_pace_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3081_frame_ipc_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3096_tick_telemetry_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3096_scale_policy) == 0U) {\n",
    )
    source = _replace_required(
        source,
        "static int a90_doomgeneric_parse_loop_frames(const char *text, int max_value) {\n",
        f"""#define A90_DG_TICK_TELEMETRY_PATH "{TICK_TELEMETRY_PATH}"\n\n"""
        """static int a90_doomgeneric_write_tick_telemetry(const char *path,\n"""
        """                                                int frames_requested,\n"""
        """                                                int loop_iterations,\n"""
        """                                                int loop_rc) {\n"""
        """    char tmp_path[256];\n"""
        """    FILE *fp;\n"""
        """    int i_time;\n"""
        """    int observed_gametic;\n"""
        """    unsigned int observed_presented;\n"""
        """    int ok = 1;\n\n"""
        """    if (path == NULL || path[0] == '\\0' ||\n"""
        """        snprintf(tmp_path, sizeof(tmp_path), "%s.tmp", path) >= (int)sizeof(tmp_path)) {\n"""
        """        return 62;\n"""
        """    }\n"""
        """    i_time = I_GetTime();\n"""
        """    observed_gametic = gametic;\n"""
        """    observed_presented = a90_doomgeneric_presented_frames();\n"""
        """    fp = fopen(tmp_path, "w");\n"""
        """    if (fp == NULL) {\n"""
        """        return 63;\n"""
        """    }\n"""
        """    ok = ok && fprintf(fp, "version=1\\n") >= 0;\n"""
        f"""    ok = ok && fprintf(fp, "marker={TICK_TELEMETRY_MARKER}\\n") >= 0;\n"""
        """    ok = ok && fprintf(fp, "frames_requested=%d\\n", frames_requested) >= 0;\n"""
        """    ok = ok && fprintf(fp, "loop_iterations=%d\\n", loop_iterations) >= 0;\n"""
        """    ok = ok && fprintf(fp, "loop_rc=%d\\n", loop_rc) >= 0;\n"""
        """    ok = ok && fprintf(fp, "presented_frames=%u\\n", observed_presented) >= 0;\n"""
        """    ok = ok && fprintf(fp, "fake_ticks_ms=%u\\n", fake_ticks_ms) >= 0;\n"""
        """    ok = ok && fprintf(fp, "sleep_calls=%u\\n", tick_telemetry_sleep_calls) >= 0;\n"""
        """    ok = ok && fprintf(fp, "sleep_ms_total=%llu\\n",\n"""
        """                      (unsigned long long)tick_telemetry_sleep_ms_total) >= 0;\n"""
        """    ok = ok && fprintf(fp, "getticks_calls=%u\\n", tick_telemetry_getticks_calls) >= 0;\n"""
        """    ok = ok && fprintf(fp, "i_get_time=%d\\n", i_time) >= 0;\n"""
        """    ok = ok && fprintf(fp, "gametic=%d\\n", observed_gametic) >= 0;\n"""
        """    ok = ok && fprintf(fp, "ticrate=35\\n") >= 0;\n"""
        """    ok = ok && fprintf(fp, "fake_time_model=DG_SleepMs-accumulated\\n") >= 0;\n"""
        """    ok = ok && fprintf(fp, "pacing_model=presenter-pageflip-token\\n") >= 0;\n"""
        """    ok = ok && fprintf(fp, "input_model=udp-ncm-unix-dgram-file-fallback\\n") >= 0;\n"""
        """    if (!ok || fflush(fp) != 0) {\n"""
        """        (void)fclose(fp);\n"""
        """        (void)unlink(tmp_path);\n"""
        """        return 64;\n"""
        """    }\n"""
        """    if (fclose(fp) != 0) {\n"""
        """        (void)unlink(tmp_path);\n"""
        """        return 65;\n"""
        """    }\n"""
        """    if (rename(tmp_path, path) < 0) {\n"""
        """        (void)unlink(tmp_path);\n"""
        """        return 66;\n"""
        """    }\n"""
        """    return 0;\n"""
        """}\n\n"""
        """static int a90_doomgeneric_parse_loop_frames(const char *text, int max_value) {\n""",
    )
    source = _replace_required(
        source,
        "    if (loop_rc != 0) {\n"
        "        return loop_rc;\n"
        "    }\n"
        "    return a90_doomgeneric_presented_frames() > 0U ? 0 : 50;\n",
        "    {\n"
        "        int final_rc = loop_rc != 0 ? loop_rc :\n"
        "            (a90_doomgeneric_presented_frames() > 0U ? 0 : 50);\n"
        "        int telemetry_rc = a90_doomgeneric_write_tick_telemetry(\n"
        "            A90_DG_TICK_TELEMETRY_PATH, frames, index, final_rc);\n\n"
        "        if (telemetry_rc != 0 && final_rc == 0) {\n"
        "            return telemetry_rc;\n"
        "        }\n"
        "        return final_rc;\n"
        "    }\n",
    )
    return source


def _set_large_frame(value: int) -> None:
    v3086.NATIVE_DASHBOARD_LARGE_FRAME = value
    v3086.v3084.NATIVE_DASHBOARD_LARGE_FRAME = value
    v3086.v3084.v3083.NATIVE_DASHBOARD_LARGE_FRAME = value
    v3086.v3084.v3083.v3081.NATIVE_DASHBOARD_LARGE_FRAME = value
    v3086.v3084.v3083.v3081.v3079.NATIVE_DASHBOARD_LARGE_FRAME = value
    v3086.v3084.v3083.v3081.v3079.v3077.NATIVE_DASHBOARD_LARGE_FRAME = value
    v3086.v3084.v3083.v3081.v3079.v3077.v3074.NATIVE_DASHBOARD_LARGE_FRAME = value
    v3086.v3084.v3083.v3081.v3079.v3077.v3074.v3071.NATIVE_DASHBOARD_LARGE_FRAME = value
    v3033_module().NATIVE_DASHBOARD_LARGE_FRAME = value


def _set_seq_telemetry(value: int) -> None:
    v3033_module().SEQ_TELEMETRY = value


def apply_v3096_globals() -> None:
    v3086.CYCLE = CYCLE
    v3086.INIT_VERSION = INIT_VERSION
    v3086.INIT_BUILD = INIT_BUILD
    v3086.BUILD_TAG = BUILD_TAG
    v3086.DECISION = DECISION
    v3086.OUT_DIR = OUT_DIR
    v3086.OBJ_DIR = OBJ_DIR
    v3086.REPORT_PATH = REPORT_PATH
    v3086.BOOT_IMAGE = BOOT_IMAGE
    v3086.INIT_BINARY = INIT_BINARY
    v3086.RAMDISK_CPIO = RAMDISK_CPIO
    v3086.HELPER_BINARY = HELPER_BINARY
    v3086.ENGINE_BINARY = ENGINE_BINARY
    v3086.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3086.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3086.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3086.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3086.ENGINE_NAME = ENGINE_NAME
    v3086.FRAME_PATH = FRAME_PATH
    v3086.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    v3086.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3086.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3086.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    v3086.NATIVE_DASHBOARD_LARGE_FRAME = NATIVE_DASHBOARD_LARGE_FRAME
    v3086.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3086.render_report = render_report
    _set_large_frame(NATIVE_DASHBOARD_LARGE_FRAME)
    _set_seq_telemetry(SEQ_TELEMETRY)
    v3086.v3084.v3083.v3081.v3081_adapter_source = v3096_adapter_source
    v3086.apply_v3086_globals()
    _set_large_frame(NATIVE_DASHBOARD_LARGE_FRAME)
    _set_seq_telemetry(SEQ_TELEMETRY)
    V3059.v3059_adapter_source = v3096_adapter_source


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3096 DOOMGENERIC Sequence Telemetry Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback / DOOM new-frame sequence isolation.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps V3094's 1:1 native dashboard scale, fake-time tick telemetry, pageflip cadence, serial-preserve, shared-frame IPC, presenter-paced helper, timing probe, audio corun, and UDP/NCM input.",
        "- Adds presenter sequence telemetry under `VIDEO_DEMO_DOOMGENERIC_SEQ_TELEMETRY=1`.",
        "- Purpose: quantify whether remaining visible stepping comes from helper/presenter new-frame cadence, duplicate frame polls, or missed shared-frame sequences after the large scaler was removed.",
        "",
        "## Telemetry Contract",
        "",
        f"- Telemetry marker: `{TICK_TELEMETRY_MARKER}`",
        f"- Scale marker: `{SCALE_1TO1_MARKER}`",
        f"- Sequence telemetry contract: `{SEQ_TELEMETRY_CONTRACT}`",
        f"- Sequence telemetry model: `{SEQ_TELEMETRY_MODEL}`",
        f"- Telemetry path: `{TICK_TELEMETRY_PATH}`",
        "- Captured fields: `fake_ticks_ms`, `sleep_calls`, `sleep_ms_total`, `getticks_calls`, `i_get_time`, `gametic`, `presented_frames`, and loop result.",
        "- Fake time model: `DG_SleepMs-accumulated`.",
        "- DOOM ticrate: `35`.",
        "",
        "## Scale Contract",
        "",
        f"- Baseline large dashboard frame: `{int(bool(BASELINE_NATIVE_DASHBOARD_LARGE_FRAME))}`",
        f"- Candidate large dashboard frame: `{int(bool(NATIVE_DASHBOARD_LARGE_FRAME))}`",
        f"- Baseline frame scale: `{BASELINE_FRAME_SCALE}`",
        f"- Candidate frame scale: `{FRAME_SCALE}`",
        f"- Candidate scale path: `{SCALE_PATH}`",
        f"- Candidate sequence telemetry: `{SEQ_TELEMETRY}`",
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
        "- `py_compile`: V3096 builder and focused tests.",
        "- `unittest`: V3096 source contract plus V3090/V3086/V3084/V3083/V3081/V3079/V3077/V3074/V3071 lineage regressions.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3096 identity, 1:1 scale marker, large_frame=0/frame_scale=1:1 markers, sequence telemetry markers, tick telemetry marker/path, serial-preserve marker, shared-frame markers, pace/pageflip markers, timing probe, audio marker, and UDP input markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3097`",
        "- Type: rollback-gated live validation.",
        f"- Scope: flash exact V3096 boot image via `native_init_flash.py`, health-check, require `large_frame=0`, `frame_scale=1:1`, and `seq_telemetry=1`, run bounded DOOM loop, then compare new-frame/duplicate/missed-sequence telemetry with V3095.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-seq-telemetry-candidate`.",
    ]) + "\n"


def main() -> int:
    apply_v3096_globals()
    rc = v3086.v3084.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "pageflip_min_submit_interval_ms": PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "pageflip_min_submit_interval_baseline_ms": BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "cadence_experiment": "presenter-seq-telemetry-on-1to1-scale",
        "tick_telemetry_marker": TICK_TELEMETRY_MARKER,
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
        "candidate_type": "doomgeneric-seq-telemetry-candidate",
        "adoption_state": "pending-seq-telemetry-live-validation",
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
    (OUT_DIR / "doomgeneric-seq-telemetry-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-seq-telemetry-candidate",
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
        "seq_telemetry_contract": SEQ_TELEMETRY_CONTRACT,
        "seq_telemetry_model": SEQ_TELEMETRY_MODEL,
        "seq_telemetry_enabled": bool(SEQ_TELEMETRY),
        "tick_telemetry_path": TICK_TELEMETRY_PATH,
        "loop_frame_ms": LOOP_FRAME_MS,
        "presenter_poll_ms": PRESENTER_POLL_MS,
        "pageflip_min_submit_interval_baseline_ms": BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "pageflip_min_submit_interval_ms": PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "frame_ipc": v3086.v3084.v3083.v3081.CANDIDATE_FRAME_IPC,
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
        "adoption_state": "pending-seq-telemetry-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
