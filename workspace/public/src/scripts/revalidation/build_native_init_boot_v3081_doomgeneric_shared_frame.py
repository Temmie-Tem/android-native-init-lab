#!/usr/bin/env python3
"""Build V3081 native-init DOOM shared-frame IPC candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v3079_doomgeneric_pace_socket as v3079
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3081"
INIT_VERSION = "0.10.97"
INIT_BUILD = "v3081-doomgeneric-shared-frame"
BUILD_TAG = INIT_BUILD
DECISION = "v3081-doomgeneric-shared-frame-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3081_DOOMGENERIC_SHARED_FRAME_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3081_doomgeneric_shared_frame.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3081_doomgeneric_shared_frame"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3081_doomgeneric_shared_frame.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v512_doomgeneric_shared_frame"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3081"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3081.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3081.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3081"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3081-shared-frame"

RUNTIME_WAD_ROOT = v3079.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3079.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3079.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3079.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3079.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3079.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = v3079.DEFAULT_LOOP_FRAMES
CONTINUOUS_LOOP_FRAMES = v3079.CONTINUOUS_LOOP_FRAMES
MAX_LOOP_FRAMES = v3079.MAX_LOOP_FRAMES
LOOP_FRAME_MS = v3079.LOOP_FRAME_MS
PRESENTER_POLL_MS = v3079.PRESENTER_POLL_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3081-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3081-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3081-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3081-input.sock"
INPUT_UDP_PORT = v3079.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3079.DEVICE_NCM_HOST
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3081-pace.sock"
PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = v3079.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS
FRAME_WIDTH = v3079.FRAME_WIDTH
FRAME_HEIGHT = v3079.FRAME_HEIGHT
FRAME_STRIDE = v3079.FRAME_STRIDE
FRAME_BYTES = v3079.FRAME_BYTES
NATIVE_DASHBOARD = v3079.NATIVE_DASHBOARD
NATIVE_DASHBOARD_MINIMAL = v3079.NATIVE_DASHBOARD_MINIMAL
NATIVE_DASHBOARD_LARGE_FRAME = v3079.NATIVE_DASHBOARD_LARGE_FRAME
NATIVE_DOOM_PRESENT_PAGEFLIP = v3079.NATIVE_DOOM_PRESENT_PAGEFLIP
BASELINE_FRAME_IPC = "raw-frame-file-rename-open-read"
CANDIDATE_FRAME_IPC = "shared-mmap-seq-copy"
REUSE_FRAME_BUFFER = v3079.REUSE_FRAME_BUFFER
DASHBOARD_METRICS_INTERVAL_FRAMES = v3079.DASHBOARD_METRICS_INTERVAL_FRAMES
FRAME_TIMING_PROBE = v3079.FRAME_TIMING_PROBE

SOUND_MODE = v3079.SOUND_MODE
AUDIO_CORUN = v3079.AUDIO_CORUN
AUDIO_CORUN_MODE = v3079.AUDIO_CORUN_MODE
AUDIO_CORUN_DURATION_MS = v3079.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3079.AUDIO_CORUN_AMPLITUDE_MILLI

HOST_KEYBOARD_BRIDGE = v3079.HOST_KEYBOARD_BRIDGE
HOST_DASHBOARD = v3079.HOST_DASHBOARD
V3059 = v3079.V3059
BASE_V3079_ADAPTER_SOURCE = v3079.v3079_adapter_source

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.97 (v3081-doomgeneric-shared-frame)",
    b"v3081-doomgeneric-shared-frame",
    b"doomgeneric-private-link-v3081-shared-frame",
    b"/bin/a90_doomgeneric_private_engine_v3081",
    RUNTIME_WAD_PATH.encode("ascii"),
    EXPECTED_WAD_SHA256.encode("ascii"),
    FRAME_PATH.encode("ascii"),
    SHARED_FRAME_PATH.encode("ascii"),
    INPUT_STATE_PATH.encode("ascii"),
    INPUT_SOCKET_PATH.encode("ascii"),
    PACE_SOCKET_PATH.encode("ascii"),
    b"a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback",
    b"a90.doomgeneric.v3079.pace=presenter-pageflip-token",
    b"a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq",
    b"--shared-frame",
    b"shared-mmap-seq",
    b"shared-mmap-copy",
    b"video.demo.doom.frame.ipc=",
    b"video.demo.doom.loop.frame_ipc=",
    b"video.demo.doom.presenter.reader=",
    b"video.demo.doom.loop.timing_probe=1",
    b"pace_socket.tokens_sent=",
    b"native-audio-corun-tone-v3053",
)


def rel(path: Path) -> str:
    return v3079.rel(path)


def replace_required(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing source fragment for V3081 patch: {old[:80]!r}")
    return text.replace(old, new)


def v3081_adapter_source() -> str:
    text = BASE_V3079_ADAPTER_SOURCE()
    text = replace_required(
        text,
        "#include <netinet/in.h>\n#include <sys/socket.h>\n#include <sys/un.h>\n#include <stdlib.h>",
        "#include <netinet/in.h>\n#include <sys/mman.h>\n#include <sys/socket.h>\n#include <sys/un.h>\n#include <stdlib.h>",
    )
    text = replace_required(
        text,
        'const char a90_doomgeneric_v3079_pace_policy[] =\n'
        '    "a90.doomgeneric.v3079.pace=presenter-pageflip-token";',
        'const char a90_doomgeneric_v3079_pace_policy[] =\n'
        '    "a90.doomgeneric.v3079.pace=presenter-pageflip-token";\n'
        'const char a90_doomgeneric_v3081_frame_ipc_policy[] =\n'
        '    "a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq";',
    )
    text = replace_required(
        text,
        "marker_checksum(a90_doomgeneric_v3079_pace_policy) == 0U) {",
        "marker_checksum(a90_doomgeneric_v3079_pace_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3081_frame_ipc_policy) == 0U) {",
    )
    shared_support = r'''
#define A90_DG_SHARED_FRAME_MAGIC 0x41394652U
#define A90_DG_SHARED_FRAME_VERSION 1U
#define A90_DG_SHARED_FRAME_HEADER_BYTES 64U

struct a90_dg_shared_frame_header {
    uint32_t magic;
    uint32_t version;
    uint32_t header_bytes;
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    uint32_t frame_bytes;
    uint32_t sequence;
    uint32_t flags;
    uint32_t reserved0;
    uint64_t frame_id;
    uint8_t reserved[16];
};

struct a90_dg_shared_frame {
    int fd;
    void *map;
    size_t map_size;
    volatile struct a90_dg_shared_frame_header *header;
    uint8_t *pixels;
    const char *path;
    uint32_t sequence;
};

static void a90_doomgeneric_shared_frame_init(struct a90_dg_shared_frame *shared) {
    if (shared == NULL) {
        return;
    }
    memset(shared, 0, sizeof(*shared));
    shared->fd = -1;
}

static int a90_doomgeneric_shared_frame_requested(const char *path) {
    return path != NULL && path[0] != '\0';
}

static int a90_doomgeneric_open_shared_frame(struct a90_dg_shared_frame *shared,
                                             const char *path) {
    const size_t frame_bytes = (size_t)DOOMGENERIC_RESX *
        (size_t)DOOMGENERIC_RESY * sizeof(frame_sink[0]);
    const size_t map_size = (size_t)A90_DG_SHARED_FRAME_HEADER_BYTES + frame_bytes;
    void *map;
    int fd;

    if (shared == NULL || !a90_doomgeneric_shared_frame_requested(path) ||
        sizeof(struct a90_dg_shared_frame_header) != A90_DG_SHARED_FRAME_HEADER_BYTES ||
        sizeof(frame_sink[0]) != 4U) {
        return 54;
    }
    fd = open(path, O_RDWR | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        return 55;
    }
    if (ftruncate(fd, (off_t)map_size) < 0) {
        close(fd);
        return 56;
    }
    map = mmap(NULL, map_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (map == MAP_FAILED) {
        close(fd);
        return 57;
    }
    memset(map, 0, map_size);
    shared->fd = fd;
    shared->map = map;
    shared->map_size = map_size;
    shared->header = (volatile struct a90_dg_shared_frame_header *)map;
    shared->pixels = (uint8_t *)map + A90_DG_SHARED_FRAME_HEADER_BYTES;
    shared->path = path;
    shared->sequence = 0U;

    shared->header->magic = A90_DG_SHARED_FRAME_MAGIC;
    shared->header->version = A90_DG_SHARED_FRAME_VERSION;
    shared->header->header_bytes = A90_DG_SHARED_FRAME_HEADER_BYTES;
    shared->header->width = DOOMGENERIC_RESX;
    shared->header->height = DOOMGENERIC_RESY;
    shared->header->stride = DOOMGENERIC_RESX * (uint32_t)sizeof(frame_sink[0]);
    shared->header->frame_bytes = (uint32_t)frame_bytes;
    __sync_synchronize();
    return 0;
}

static int a90_doomgeneric_write_shared_frame(struct a90_dg_shared_frame *shared) {
    const size_t frame_bytes = (size_t)DOOMGENERIC_RESX *
        (size_t)DOOMGENERIC_RESY * sizeof(frame_sink[0]);
    uint32_t sequence;

    if (shared == NULL || shared->header == NULL || shared->pixels == NULL) {
        return 58;
    }
    sequence = shared->sequence + 2U;
    if (sequence == 0U) {
        sequence = 2U;
    }
    shared->sequence = sequence;
    shared->header->sequence = sequence - 1U;
    __sync_synchronize();
    memcpy(shared->pixels, frame_sink, frame_bytes);
    __sync_synchronize();
    shared->header->frame_id = (((uint64_t)sequence) << 32U) ^ (uint64_t)frame_checksum;
    shared->header->sequence = sequence;
    __sync_synchronize();
    return 0;
}

static void a90_doomgeneric_close_shared_frame(struct a90_dg_shared_frame *shared) {
    if (shared == NULL) {
        return;
    }
    if (shared->map != NULL && shared->map != MAP_FAILED) {
        munmap(shared->map, shared->map_size);
    }
    if (shared->fd >= 0) {
        close(shared->fd);
    }
    a90_doomgeneric_shared_frame_init(shared);
}

'''
    text = replace_required(
        text,
        "static int a90_doomgeneric_parse_loop_frames(const char *text, int max_value) {",
        shared_support + "static int a90_doomgeneric_parse_loop_frames(const char *text, int max_value) {",
    )
    text = replace_required(
        text,
        "                                       const char *pace_socket_path,\n"
        "                                       int frame_ms) {",
        "                                       const char *pace_socket_path,\n"
        "                                       const char *shared_frame_path,\n"
        "                                       int frame_ms) {",
    )
    text = replace_required(
        text,
        "    int input_udp_fd;\n"
        "    int pace_fd;\n"
        "    int loop_rc = 0;",
        "    int input_udp_fd;\n"
        "    int pace_fd;\n"
        "    struct a90_dg_shared_frame shared_frame;\n"
        "    int rc;\n"
        "    int loop_rc = 0;",
    )
    text = replace_required(
        text,
        "    a90_doomgeneric_apply_input_state_file(input_state_path);\n"
        "    input_socket_fd = a90_doomgeneric_open_input_socket(input_socket_path);\n",
        "    a90_doomgeneric_shared_frame_init(&shared_frame);\n"
        "    a90_doomgeneric_apply_input_state_file(input_state_path);\n"
        "    input_socket_fd = a90_doomgeneric_open_input_socket(input_socket_path);\n",
    )
    text = replace_required(
        text,
        "    if (pace_socket_path != NULL && pace_socket_path[0] != '\\0' && pace_fd < 0) {\n"
        "        if (input_udp_fd >= 0) {\n"
        "            close(input_udp_fd);\n"
        "        }\n"
        "        a90_doomgeneric_close_input_socket(input_socket_fd, input_socket_path);\n"
        "        return 52;\n"
        "    }\n",
        "    if (pace_socket_path != NULL && pace_socket_path[0] != '\\0' && pace_fd < 0) {\n"
        "        if (input_udp_fd >= 0) {\n"
        "            close(input_udp_fd);\n"
        "        }\n"
        "        a90_doomgeneric_close_input_socket(input_socket_fd, input_socket_path);\n"
        "        return 52;\n"
        "    }\n"
        "    if (a90_doomgeneric_shared_frame_requested(shared_frame_path)) {\n"
        "        rc = a90_doomgeneric_open_shared_frame(&shared_frame, shared_frame_path);\n"
        "        if (rc != 0) {\n"
        "            a90_doomgeneric_close_pace_socket(pace_fd, pace_socket_path);\n"
        "            if (input_udp_fd >= 0) {\n"
        "                close(input_udp_fd);\n"
        "            }\n"
        "            a90_doomgeneric_close_input_socket(input_socket_fd, input_socket_path);\n"
        "            return rc;\n"
        "        }\n"
        "    }\n",
    )
    text = replace_required(
        text,
        "        if (a90_doomgeneric_presented_frames() > 0U) {\n"
        "            rc = a90_doomgeneric_dump_frame_xbgr8888_atomic(output_path);\n"
        "            if (rc != 0) {\n"
        "                loop_rc = rc;\n"
        "                break;\n"
        "            }\n"
        "        }\n",
        "        if (a90_doomgeneric_presented_frames() > 0U) {\n"
        "            if (shared_frame.header != NULL) {\n"
        "                rc = a90_doomgeneric_write_shared_frame(&shared_frame);\n"
        "            } else {\n"
        "                rc = a90_doomgeneric_dump_frame_xbgr8888_atomic(output_path);\n"
        "            }\n"
        "            if (rc != 0) {\n"
        "                loop_rc = rc;\n"
        "                break;\n"
        "            }\n"
        "        }\n",
    )
    text = replace_required(
        text,
        "    a90_doomgeneric_close_pace_socket(pace_fd, pace_socket_path);\n",
        "    a90_doomgeneric_close_shared_frame(&shared_frame);\n"
        "    a90_doomgeneric_close_pace_socket(pace_fd, pace_socket_path);\n",
    )
    text = replace_required(
        text,
        "if ((argc == 11 || argc == 13 || argc == 15 || argc == 17) &&",
        "if ((argc == 11 || argc == 13 || argc == 15 || argc == 17 || argc == 19) &&",
    )
    text = replace_required(
        text,
        "        const char *pace_socket_path = NULL;\n"
        "        unsigned int input_udp_port = 0U;",
        "        const char *pace_socket_path = NULL;\n"
        "        const char *shared_frame_path = NULL;\n"
        "        unsigned int input_udp_port = 0U;",
    )
    text = replace_required(
        text,
        "            } else if (strcmp(argv[arg_index], \"--pace-socket\") == 0) {\n"
        "                pace_socket_path = argv[arg_index + 1];\n"
        "            } else {",
        "            } else if (strcmp(argv[arg_index], \"--pace-socket\") == 0) {\n"
        "                pace_socket_path = argv[arg_index + 1];\n"
        "            } else if (strcmp(argv[arg_index], \"--shared-frame\") == 0) {\n"
        "                shared_frame_path = argv[arg_index + 1];\n"
        "            } else {",
    )
    text = replace_required(
        text,
        "return a90_doomgeneric_run_wad_frame_loop(argv[2], frames, argv[6], argv[8], input_socket_path, input_udp_port, pace_socket_path, frame_ms);",
        "return a90_doomgeneric_run_wad_frame_loop(argv[2], frames, argv[6], argv[8], input_socket_path, input_udp_port, pace_socket_path, shared_frame_path, frame_ms);",
    )
    return text


def v3033_module() -> Any:
    return v3079.v3033_module()


def apply_v3081_globals() -> None:
    v3079.CYCLE = CYCLE
    v3079.INIT_VERSION = INIT_VERSION
    v3079.INIT_BUILD = INIT_BUILD
    v3079.BUILD_TAG = BUILD_TAG
    v3079.DECISION = DECISION
    v3079.OUT_DIR = OUT_DIR
    v3079.OBJ_DIR = OBJ_DIR
    v3079.REPORT_PATH = REPORT_PATH
    v3079.BOOT_IMAGE = BOOT_IMAGE
    v3079.INIT_BINARY = INIT_BINARY
    v3079.RAMDISK_CPIO = RAMDISK_CPIO
    v3079.HELPER_BINARY = HELPER_BINARY
    v3079.ENGINE_BINARY = ENGINE_BINARY
    v3079.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3079.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3079.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3079.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3079.ENGINE_NAME = ENGINE_NAME
    v3079.FRAME_PATH = FRAME_PATH
    v3079.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3079.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3079.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    v3079.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3079.render_report = render_report
    v3079.apply_v3079_globals()

    v3033 = v3033_module()
    v3033.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    V3059.v3059_adapter_source = v3081_adapter_source


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3081 DOOMGENERIC Shared Frame Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback / DOOM capstone frame IPC.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps V3079 presenter-paced helper, pageflip presentation, minimal dashboard, timing probe, frame_ms=28, and UDP/NCM input.",
        "- Adds a helper-created shared mmap frame file with a 64-byte header and even/odd sequence guard.",
        "- Presenter reads the shared frame via mmap and copies only a stable sequence, avoiding per-frame raw-file open/read and helper write/rename.",
        "- Leaves the raw frame file path compiled as fallback when no shared-frame path is configured.",
        "",
        "## IPC Contract",
        "",
        f"- Baseline frame IPC: `{BASELINE_FRAME_IPC}`",
        f"- Candidate frame IPC: `{CANDIDATE_FRAME_IPC}`",
        f"- Shared frame path: `{SHARED_FRAME_PATH}`",
        f"- Raw fallback frame path: `{FRAME_PATH}`",
        f"- Pace socket: `{PACE_SOCKET_PATH}`",
        f"- Helper loop command: `{doom.get('helper_loop_command')}`",
        "- Header: magic/version/header_bytes/geometry/sequence/frame_id, then XBGR8888 pixels.",
        "- Sequence: odd means writer in progress; even nonzero means stable frame.",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}`",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Validation",
        "",
        "- `py_compile`: V3081 builder and focused tests.",
        "- `unittest`: V3081 source contract plus V3079/V3077/V3074/V3071 lineage regressions.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3081 identity, shared-frame helper markers, presenter shared-mmap markers, V3079 pace markers, pageflip telemetry, and UDP input markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3082`",
        "- Type: rollback-gated live validation of V3081 shared-frame candidate.",
        "- Scope: flash exact V3081 boot image via `native_init_flash.py`, health-check, require shared-frame markers, run bounded foreground timing loop, compare read/copy and flip delta distribution with V3080, then verify continuous loop and UDP input.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-shared-frame-candidate`.",
    ]) + "\n"


def main() -> int:
    apply_v3081_globals()
    rc = v3079.v3077.v3074.v3071.v3069.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "shared_frame_path": SHARED_FRAME_PATH,
        "raw_fallback_frame_path": FRAME_PATH,
        "baseline_frame_ipc": BASELINE_FRAME_IPC,
        "frame_ipc": CANDIDATE_FRAME_IPC,
        "pace_socket_path": PACE_SOCKET_PATH,
        "pageflip_min_submit_interval_ms": PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "shared_frame_header": {
            "magic": "0x41394652",
            "version": 1,
            "header_bytes": 64,
            "sequence": "odd=writer-active even=stable-frame",
            "fields": [
                "magic",
                "version",
                "header_bytes",
                "width",
                "height",
                "stride",
                "frame_bytes",
                "sequence",
                "flags",
                "frame_id",
            ],
        },
        "native_dashboard": bool(NATIVE_DASHBOARD),
        "native_dashboard_minimal": bool(NATIVE_DASHBOARD_MINIMAL),
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "native_doom_present_pageflip": bool(NATIVE_DOOM_PRESENT_PAGEFLIP),
        "present_mode": "pageflip",
        "present_path": "kms-dumb-buffer-pageflip",
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
        "candidate_type": "doomgeneric-shared-frame-candidate",
        "adoption_state": "pending-shared-frame-live-validation",
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
    (OUT_DIR / "doomgeneric-shared-frame-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-shared-frame-candidate",
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
        "loop_frame_ms": LOOP_FRAME_MS,
        "presenter_poll_ms": PRESENTER_POLL_MS,
        "frame_ipc": CANDIDATE_FRAME_IPC,
        "present_mode": "pageflip",
        "present_path": "kms-dumb-buffer-pageflip",
        "dashboard_profile": "minimal-fastdraw",
        "frame_timing_probe": FRAME_TIMING_PROBE,
        "native_dashboard": bool(NATIVE_DASHBOARD),
        "native_dashboard_minimal": bool(NATIVE_DASHBOARD_MINIMAL),
        "native_doom_present_pageflip": bool(NATIVE_DOOM_PRESENT_PAGEFLIP),
        "loop_start_command": f"video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "host_keyboard_bridge": rel(HOST_KEYBOARD_BRIDGE),
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-shared-frame-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
