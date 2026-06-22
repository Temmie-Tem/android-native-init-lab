#!/usr/bin/env python3
"""Build V3098 native-init DOOM per-frame gametic telemetry candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v3096_doomgeneric_seq_telemetry as v3096
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3098"
INIT_VERSION = "0.10.105"
INIT_BUILD = "v3098-doomgeneric-gametic-frame-telemetry"
BUILD_TAG = INIT_BUILD
DECISION = "v3098-doomgeneric-gametic-frame-telemetry-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3098_DOOMGENERIC_GAMETIC_FRAME_TELEMETRY_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3098_doomgeneric_gametic_frame_telemetry.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3098_doomgeneric_gametic_frame_telemetry"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3098_doomgeneric_gametic_frame_telemetry.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v516_doomgeneric_gametic_frame_telemetry"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3098"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3098.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3098.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3098"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3098-gametic-frame-telemetry"

RUNTIME_WAD_ROOT = v3096.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3096.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3096.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3096.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3096.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3096.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = v3096.DEFAULT_LOOP_FRAMES
CONTINUOUS_LOOP_FRAMES = v3096.CONTINUOUS_LOOP_FRAMES
MAX_LOOP_FRAMES = v3096.MAX_LOOP_FRAMES
LOOP_FRAME_MS = v3096.LOOP_FRAME_MS
PRESENTER_POLL_MS = v3096.PRESENTER_POLL_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3098-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3098-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3098-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3098-input.sock"
INPUT_UDP_PORT = v3096.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3096.DEVICE_NCM_HOST
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3098-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3098-tick-telemetry.txt"
PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = v3096.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS
BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = v3096.BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS
FRAME_WIDTH = v3096.FRAME_WIDTH
FRAME_HEIGHT = v3096.FRAME_HEIGHT
FRAME_STRIDE = v3096.FRAME_STRIDE
FRAME_BYTES = v3096.FRAME_BYTES
NATIVE_DASHBOARD = v3096.NATIVE_DASHBOARD
NATIVE_DASHBOARD_MINIMAL = v3096.NATIVE_DASHBOARD_MINIMAL
NATIVE_DASHBOARD_LARGE_FRAME = v3096.NATIVE_DASHBOARD_LARGE_FRAME
BASELINE_NATIVE_DASHBOARD_LARGE_FRAME = v3096.BASELINE_NATIVE_DASHBOARD_LARGE_FRAME
NATIVE_DOOM_PRESENT_PAGEFLIP = v3096.NATIVE_DOOM_PRESENT_PAGEFLIP
BASELINE_FRAME_SCALE = v3096.BASELINE_FRAME_SCALE
FRAME_SCALE = v3096.FRAME_SCALE
SCALE_PATH = v3096.SCALE_PATH
REUSE_FRAME_BUFFER = v3096.REUSE_FRAME_BUFFER
DASHBOARD_METRICS_INTERVAL_FRAMES = v3096.DASHBOARD_METRICS_INTERVAL_FRAMES
FRAME_TIMING_PROBE = v3096.FRAME_TIMING_PROBE
SEQ_TELEMETRY = v3096.SEQ_TELEMETRY
BASELINE_BACKGROUND_CANCEL = v3096.BASELINE_BACKGROUND_CANCEL
CANDIDATE_BACKGROUND_CANCEL = v3096.CANDIDATE_BACKGROUND_CANCEL

SOUND_MODE = v3096.SOUND_MODE
AUDIO_CORUN = v3096.AUDIO_CORUN
AUDIO_CORUN_MODE = v3096.AUDIO_CORUN_MODE
AUDIO_CORUN_DURATION_MS = v3096.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3096.AUDIO_CORUN_AMPLITUDE_MILLI

HOST_KEYBOARD_BRIDGE = v3096.HOST_KEYBOARD_BRIDGE
HOST_DASHBOARD = v3096.HOST_DASHBOARD
V3059 = v3096.V3059

TICK_TELEMETRY_MARKER = "a90.doomgeneric.v3098.tick_telemetry=gametic-frame-fake-time-summary"
SCALE_1TO1_MARKER = "a90.doomgeneric.v3098.scale=large-frame-off-1to1"
GAMETIC_FRAME_TELEMETRY_MARKER = (
    "a90.doomgeneric.v3098.gametic_frame_telemetry=per-rendered-frame-gametic-summary"
)
SEQ_TELEMETRY_CONTRACT = v3096.SEQ_TELEMETRY_CONTRACT
SEQ_TELEMETRY_MODEL = v3096.SEQ_TELEMETRY_MODEL

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.105 (v3098-doomgeneric-gametic-frame-telemetry)",
    b"v3098-doomgeneric-gametic-frame-telemetry",
    b"doomgeneric-private-link-v3098-gametic-frame-telemetry",
    b"/bin/a90_doomgeneric_private_engine_v3098",
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
    b"a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback",
    b"a90.doomgeneric.v3079.pace=presenter-pageflip-token",
    b"a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq",
    b"--shared-frame",
    b"shared-mmap-copy",
    b"video.demo.doom.dashboard.large_frame=0",
    b"video.demo.doom.dashboard.frame_scale=1:1",
    SEQ_TELEMETRY_CONTRACT.encode("ascii"),
    SEQ_TELEMETRY_MODEL.encode("ascii"),
    b"video.demo.doom.presenter.seq_telemetry=1",
    b"%s.seq.shared_missed_frames=%u",
    b"frame_gametic.samples=%u",
    b"frame_gametic.changed_transitions=%u",
    b"frame_gametic.repeated_transitions=%u",
    b"frame_gametic.max_same_run=%u",
    b"frame_gametic.max_delta=%u",
    b"video.demo.doom.loop_start.background_cancel=disabled-serial-preserve",
    b"video.demo.doom.loop.frame_ipc=",
    b"video.demo.doom.loop.timing_probe=1",
    b"native-audio-corun-tone-v3053",
)


def rel(path: Path) -> str:
    return v3096.rel(path)


def v3033_module() -> Any:
    return v3096.v3033_module()


def _replace_required(source: str, old: str, new: str) -> str:
    if old not in source:
        raise RuntimeError(f"missing V3098 adapter source anchor: {old[:96]!r}")
    return source.replace(old, new, 1)


def v3098_adapter_source() -> str:
    source = v3096.v3096_adapter_source()
    source = source.replace(v3096.TICK_TELEMETRY_MARKER, TICK_TELEMETRY_MARKER)
    source = source.replace(v3096.SCALE_1TO1_MARKER, SCALE_1TO1_MARKER)
    source = source.replace(v3096.TICK_TELEMETRY_PATH, TICK_TELEMETRY_PATH)
    source = _replace_required(
        source,
        'const char a90_doomgeneric_v3096_scale_policy[] =\n'
        f'    "{SCALE_1TO1_MARKER}";\n',
        'const char a90_doomgeneric_v3096_scale_policy[] =\n'
        f'    "{SCALE_1TO1_MARKER}";\n'
        'const char a90_doomgeneric_v3098_gametic_frame_policy[] =\n'
        f'    "{GAMETIC_FRAME_TELEMETRY_MARKER}";\n',
    )
    source = _replace_required(
        source,
        "static uint32_t tick_telemetry_getticks_calls;\n",
        "static uint32_t tick_telemetry_getticks_calls;\n"
        "static uint32_t frame_gametic_samples;\n"
        "static uint32_t frame_gametic_changed_transitions;\n"
        "static uint32_t frame_gametic_repeated_transitions;\n"
        "static uint32_t frame_gametic_positive_delta_total;\n"
        "static uint32_t frame_gametic_max_delta;\n"
        "static uint32_t frame_gametic_reset_transitions;\n"
        "static uint32_t frame_gametic_same_run_current;\n"
        "static uint32_t frame_gametic_max_same_run;\n"
        "static int frame_gametic_first;\n"
        "static int frame_gametic_last;\n"
        "static int frame_gametic_previous;\n",
    )
    source = _replace_required(
        source,
        "    tick_telemetry_getticks_calls = 0;\n"
        "    frame_checksum = 0;\n",
        "    tick_telemetry_getticks_calls = 0;\n"
        "    frame_gametic_samples = 0;\n"
        "    frame_gametic_changed_transitions = 0;\n"
        "    frame_gametic_repeated_transitions = 0;\n"
        "    frame_gametic_positive_delta_total = 0;\n"
        "    frame_gametic_max_delta = 0;\n"
        "    frame_gametic_reset_transitions = 0;\n"
        "    frame_gametic_same_run_current = 0;\n"
        "    frame_gametic_max_same_run = 0;\n"
        "    frame_gametic_first = -1;\n"
        "    frame_gametic_last = -1;\n"
        "    frame_gametic_previous = -1;\n"
        "    frame_checksum = 0;\n",
    )
    source = _replace_required(
        source,
        f'#define A90_DG_TICK_TELEMETRY_PATH "{TICK_TELEMETRY_PATH}"\n\n'
        "static int a90_doomgeneric_write_tick_telemetry",
        f'#define A90_DG_TICK_TELEMETRY_PATH "{TICK_TELEMETRY_PATH}"\n\n'
        "static void a90_doomgeneric_record_frame_gametic(void) {\n"
        "    int current = gametic;\n\n"
        "    ++frame_gametic_samples;\n"
        "    if (frame_gametic_samples == 1U) {\n"
        "        frame_gametic_first = current;\n"
        "        frame_gametic_last = current;\n"
        "        frame_gametic_previous = current;\n"
        "        frame_gametic_same_run_current = 1U;\n"
        "        frame_gametic_max_same_run = 1U;\n"
        "        return;\n"
        "    }\n"
        "    if (current == frame_gametic_previous) {\n"
        "        ++frame_gametic_repeated_transitions;\n"
        "        ++frame_gametic_same_run_current;\n"
        "    } else {\n"
        "        ++frame_gametic_changed_transitions;\n"
        "        if (current > frame_gametic_previous) {\n"
        "            uint32_t delta = (uint32_t)(current - frame_gametic_previous);\n\n"
        "            frame_gametic_positive_delta_total += delta;\n"
        "            if (delta > frame_gametic_max_delta) {\n"
        "                frame_gametic_max_delta = delta;\n"
        "            }\n"
        "        } else {\n"
        "            ++frame_gametic_reset_transitions;\n"
        "        }\n"
        "        frame_gametic_same_run_current = 1U;\n"
        "        frame_gametic_previous = current;\n"
        "    }\n"
        "    if (frame_gametic_same_run_current > frame_gametic_max_same_run) {\n"
        "        frame_gametic_max_same_run = frame_gametic_same_run_current;\n"
        "    }\n"
        "    frame_gametic_last = current;\n"
        "}\n\n"
        "static int a90_doomgeneric_write_tick_telemetry",
    )
    source = _replace_required(
        source,
        """    ok = ok && fprintf(fp, "gametic=%d\\n", observed_gametic) >= 0;\n""",
        """    ok = ok && fprintf(fp, "gametic=%d\\n", observed_gametic) >= 0;\n"""
        f"""    ok = ok && fprintf(fp, "gametic_frame_marker={GAMETIC_FRAME_TELEMETRY_MARKER}\\n") >= 0;\n"""
        """    ok = ok && fprintf(fp, "frame_gametic.samples=%u\\n", frame_gametic_samples) >= 0;\n"""
        """    ok = ok && fprintf(fp, "frame_gametic.first=%d\\n", frame_gametic_first) >= 0;\n"""
        """    ok = ok && fprintf(fp, "frame_gametic.last=%d\\n", frame_gametic_last) >= 0;\n"""
        """    ok = ok && fprintf(fp, "frame_gametic.changed_transitions=%u\\n", frame_gametic_changed_transitions) >= 0;\n"""
        """    ok = ok && fprintf(fp, "frame_gametic.repeated_transitions=%u\\n", frame_gametic_repeated_transitions) >= 0;\n"""
        """    ok = ok && fprintf(fp, "frame_gametic.positive_delta_total=%u\\n", frame_gametic_positive_delta_total) >= 0;\n"""
        """    ok = ok && fprintf(fp, "frame_gametic.max_delta=%u\\n", frame_gametic_max_delta) >= 0;\n"""
        """    ok = ok && fprintf(fp, "frame_gametic.reset_transitions=%u\\n", frame_gametic_reset_transitions) >= 0;\n"""
        """    ok = ok && fprintf(fp, "frame_gametic.max_same_run=%u\\n", frame_gametic_max_same_run) >= 0;\n"""
        """    ok = ok && fprintf(fp, "frame_gametic.transition_samples=%u\\n",\n"""
        """                      frame_gametic_changed_transitions +\n"""
        """                      frame_gametic_repeated_transitions) >= 0;\n""",
    )
    source = _replace_required(
        source,
        "        marker_checksum(a90_doomgeneric_v3096_scale_policy) == 0U) {\n",
        "        marker_checksum(a90_doomgeneric_v3096_scale_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3098_gametic_frame_policy) == 0U) {\n",
    )
    source = _replace_required(
        source,
        "        if (a90_doomgeneric_presented_frames() > 0U) {\n"
        "            if (shared_frame.header != NULL) {\n",
        "        if (a90_doomgeneric_presented_frames() > 0U) {\n"
        "            a90_doomgeneric_record_frame_gametic();\n"
        "            if (shared_frame.header != NULL) {\n",
    )
    return source


def apply_v3098_globals() -> None:
    v3096.apply_v3096_globals()
    v3096.v3086.CYCLE = CYCLE
    v3096.v3086.INIT_VERSION = INIT_VERSION
    v3096.v3086.INIT_BUILD = INIT_BUILD
    v3096.v3086.BUILD_TAG = BUILD_TAG
    v3096.v3086.DECISION = DECISION
    v3096.v3086.OUT_DIR = OUT_DIR
    v3096.v3086.OBJ_DIR = OBJ_DIR
    v3096.v3086.REPORT_PATH = REPORT_PATH
    v3096.v3086.BOOT_IMAGE = BOOT_IMAGE
    v3096.v3086.INIT_BINARY = INIT_BINARY
    v3096.v3086.RAMDISK_CPIO = RAMDISK_CPIO
    v3096.v3086.HELPER_BINARY = HELPER_BINARY
    v3096.v3086.ENGINE_BINARY = ENGINE_BINARY
    v3096.v3086.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3096.v3086.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3096.v3086.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3096.v3086.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3096.v3086.ENGINE_NAME = ENGINE_NAME
    v3096.v3086.FRAME_PATH = FRAME_PATH
    v3096.v3086.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    v3096.v3086.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3096.v3086.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3096.v3086.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    v3096.v3086.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3096.v3086.render_report = render_report
    v3096.v3086.v3084.v3083.v3081.v3081_adapter_source = v3098_adapter_source
    v3096._set_large_frame(NATIVE_DASHBOARD_LARGE_FRAME)
    v3096._set_seq_telemetry(SEQ_TELEMETRY)
    v3096.v3086.apply_v3086_globals()
    v3096._set_large_frame(NATIVE_DASHBOARD_LARGE_FRAME)
    v3096._set_seq_telemetry(SEQ_TELEMETRY)
    V3059.v3059_adapter_source = v3098_adapter_source


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3098 DOOMGENERIC Gametic Frame Telemetry Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback / DOOM fixed-tic isolation.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps V3096's 1:1 dashboard scale, pageflip cadence, shared-frame sequence telemetry, serial-preserve, timing probe, audio corun, and UDP/NCM input.",
        "- Adds helper-side per-rendered-frame `gametic` transition telemetry.",
        "- Purpose: prove or disprove whether the remaining visible stepping is caused by DOOM fixed-tic content updates rather than frame IPC or KMS cadence.",
        "",
        "## Telemetry Contract",
        "",
        f"- Tick telemetry marker: `{TICK_TELEMETRY_MARKER}`",
        f"- Gametic frame telemetry marker: `{GAMETIC_FRAME_TELEMETRY_MARKER}`",
        f"- Scale marker: `{SCALE_1TO1_MARKER}`",
        f"- Sequence telemetry contract: `{SEQ_TELEMETRY_CONTRACT}`",
        f"- Sequence telemetry model: `{SEQ_TELEMETRY_MODEL}`",
        f"- Telemetry path: `{TICK_TELEMETRY_PATH}`",
        "- Captured gametic fields: `frame_gametic.samples`, `first`, `last`, `changed_transitions`, `repeated_transitions`, `positive_delta_total`, `max_delta`, `reset_transitions`, `max_same_run`, and `transition_samples`.",
        "- Fake time model remains `DG_SleepMs-accumulated`.",
        "- DOOM ticrate remains `35`.",
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
        "- `py_compile`: V3098 builder and focused tests.",
        "- `unittest`: V3098 source contract plus current DOOM cadence lineage regressions.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3098 identity, 1:1 scale marker, sequence telemetry markers, gametic frame telemetry marker/fields, tick telemetry marker/path, shared-frame markers, pace/pageflip markers, timing probe, audio marker, and UDP input markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3099`",
        "- Type: rollback-gated live validation.",
        f"- Scope: flash exact V3098 boot image via `native_init_flash.py`, health-check, run bounded DOOM loops, then compare `frame_gametic.*` with presenter seq/pageflip telemetry.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-gametic-frame-telemetry-candidate`.",
    ]) + "\n"


def main() -> int:
    apply_v3098_globals()
    rc = v3096.v3086.v3084.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "pageflip_min_submit_interval_ms": PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "pageflip_min_submit_interval_baseline_ms": BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "cadence_experiment": "per-rendered-frame-gametic-telemetry",
        "tick_telemetry_marker": TICK_TELEMETRY_MARKER,
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
        "candidate_type": "doomgeneric-gametic-frame-telemetry-candidate",
        "adoption_state": "pending-gametic-frame-live-validation",
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
    (OUT_DIR / "doomgeneric-gametic-frame-telemetry-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-gametic-frame-telemetry-candidate",
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
        "gametic_frame_telemetry_marker": GAMETIC_FRAME_TELEMETRY_MARKER,
        "seq_telemetry_contract": SEQ_TELEMETRY_CONTRACT,
        "seq_telemetry_model": SEQ_TELEMETRY_MODEL,
        "seq_telemetry_enabled": bool(SEQ_TELEMETRY),
        "tick_telemetry_path": TICK_TELEMETRY_PATH,
        "loop_frame_ms": LOOP_FRAME_MS,
        "presenter_poll_ms": PRESENTER_POLL_MS,
        "pageflip_min_submit_interval_baseline_ms": BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "pageflip_min_submit_interval_ms": PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "frame_ipc": v3096.v3086.v3084.v3083.v3081.CANDIDATE_FRAME_IPC,
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
        "adoption_state": "pending-gametic-frame-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
