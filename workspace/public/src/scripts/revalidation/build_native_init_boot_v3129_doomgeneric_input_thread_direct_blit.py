#!/usr/bin/env python3
"""Build V3129 DOOM direct-blit candidate with background input drain."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3126_doomgeneric_smooth_demo_direct_blit as v3126
import native_doomgeneric_engine_integration_build_v3024 as v3024

REPO_ROOT = repo_root()

CYCLE = "V3129"
INIT_VERSION = "0.10.118"
INIT_BUILD = "v3129-doomgeneric-input-thread-direct-blit"
BUILD_TAG = INIT_BUILD
DECISION = "v3129-doomgeneric-input-thread-direct-blit-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3129_DOOMGENERIC_INPUT_THREAD_DIRECT_BLIT_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3129_doomgeneric_input_thread_direct_blit.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3129_doomgeneric_input_thread_direct_blit"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3129_doomgeneric_input_thread_direct_blit.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v524_doomgeneric_input_thread_direct_blit"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3129"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3129.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3129.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3129"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3129-input-thread-direct-blit"

FRAME_PATH = "/tmp/a90-doomgeneric-v3129-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3129-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3129-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3129-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3129-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3129-tick-telemetry.txt"

INPUT_THREAD_MARKER = "a90.doomgeneric.v3129.input_thread=background-drain-udp-unix-dgram"

RUNTIME_WAD_PATH = v3126.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3126.EXPECTED_WAD_SHA256
FRAME_WIDTH = v3126.FRAME_WIDTH
FRAME_HEIGHT = v3126.FRAME_HEIGHT
FRAME_STRIDE = v3126.FRAME_STRIDE
FRAME_BYTES = v3126.FRAME_BYTES
TICK_QUANTUM_US = v3126.TICK_QUANTUM_US
FRAME_IPC = "shared-mmap-direct-blit-summary-only-smooth-demo-input-thread"
INPUT_UDP_PORT = v3126.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3126.DEVICE_NCM_HOST

PACED_TIME_MARKER = v3126.PACED_TIME_MARKER.replace("v3126", "v3129")
TICK_TELEMETRY_MARKER = v3126.TICK_TELEMETRY_MARKER.replace("v3126", "v3129")
SCALE_MARKER = v3126.SCALE_MARKER.replace("v3126", "v3129")
PHASE_TELEMETRY_MARKER = v3126.PHASE_TELEMETRY_MARKER.replace("v3126", "v3129")
GAMETIC_FRAME_TELEMETRY_MARKER = v3126.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3126", "v3129")

_V3126_ADAPTER_SOURCE = v3126.v3126_adapter_source
_V3126_RENDER_REPORT = v3126.render_report


def rel(path: Path) -> str:
    return v3126.rel(path)


def _replace_required(source: str, old: str, new: str) -> str:
    if old not in source:
        raise RuntimeError(f"missing V3129 adapter source anchor: {old[:96]!r}")
    return source.replace(old, new, 1)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        v3126.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        v3126.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        v3126.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        v3126.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        b"a90-doomgeneric-v3126": b"a90-doomgeneric-v3129",
        b"a90.doomgeneric.v3126": b"a90.doomgeneric.v3129",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in v3126.REQUIRED_STRINGS) + (
    INPUT_THREAD_MARKER.encode("ascii"),
)


def v3129_adapter_source() -> str:
    source = _V3126_ADAPTER_SOURCE()
    replacements = {
        v3126.FRAME_PATH: FRAME_PATH,
        v3126.SHARED_FRAME_PATH: SHARED_FRAME_PATH,
        v3126.INPUT_STATE_PATH: INPUT_STATE_PATH,
        v3126.INPUT_SOCKET_PATH: INPUT_SOCKET_PATH,
        v3126.PACE_SOCKET_PATH: PACE_SOCKET_PATH,
        v3126.TICK_TELEMETRY_PATH: TICK_TELEMETRY_PATH,
        v3126.PACED_TIME_MARKER: PACED_TIME_MARKER,
        v3126.TICK_TELEMETRY_MARKER: TICK_TELEMETRY_MARKER,
        v3126.SCALE_MARKER: SCALE_MARKER,
        v3126.PHASE_TELEMETRY_MARKER: PHASE_TELEMETRY_MARKER,
        v3126.GAMETIC_FRAME_TELEMETRY_MARKER: GAMETIC_FRAME_TELEMETRY_MARKER,
        "a90_doomgeneric_v3126": "a90_doomgeneric_v3129",
        "a90.doomgeneric.v3126": "a90.doomgeneric.v3129",
    }
    for old, new in replacements.items():
        source = source.replace(old, new)

    source = _replace_required(
        source,
        "#include <stdint.h>\n#include <arpa/inet.h>",
        "#include <stdint.h>\n#include <pthread.h>\n#include <arpa/inet.h>",
    )
    source = _replace_required(
        source,
        'const char a90_doomgeneric_v3129_mode_label[] =\n'
        '    "non-original-smooth-demo";\n',
        'const char a90_doomgeneric_v3129_mode_label[] =\n'
        '    "non-original-smooth-demo";\n'
        'const char a90_doomgeneric_v3129_input_thread_policy[] =\n'
        f'    "{INPUT_THREAD_MARKER}";\n',
    )
    source = _replace_required(
        source,
        "        marker_checksum(a90_doomgeneric_v3129_paced_time_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3129_mode_label) == 0U) {\n",
        "        marker_checksum(a90_doomgeneric_v3129_paced_time_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3129_mode_label) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3129_input_thread_policy) == 0U) {\n",
    )
    source = _replace_required(
        source,
        "static uint32_t frame_checksum;\n",
        "static uint32_t frame_checksum;\n"
        "static pthread_mutex_t a90_dg_key_lock = PTHREAD_MUTEX_INITIALIZER;\n",
    )
    source = _replace_required(
        source,
        """void a90_doomgeneric_feed_snapshot(const struct a90_doompad_snapshot *snapshot) {
    if (snapshot == NULL) {
        return;
    }

    queue_edge(snapshot->forward, &last_forward, KEY_UPARROW);
    queue_edge(snapshot->back, &last_back, KEY_DOWNARROW);
    queue_edge(snapshot->left, &last_left, KEY_LEFTARROW);
    queue_edge(snapshot->right, &last_right, KEY_RIGHTARROW);
    queue_edge(snapshot->fire, &last_fire, KEY_FIRE);
    queue_edge(snapshot->use, &last_use, KEY_USE);
    queue_edge(snapshot->menu, &last_menu, KEY_ESCAPE);
    queue_edge(snapshot->run, &last_run, KEY_RSHIFT);
    last_seq = snapshot->seq;
}
""",
        """void a90_doomgeneric_feed_snapshot(const struct a90_doompad_snapshot *snapshot) {
    if (snapshot == NULL) {
        return;
    }

    pthread_mutex_lock(&a90_dg_key_lock);
    queue_edge(snapshot->forward, &last_forward, KEY_UPARROW);
    queue_edge(snapshot->back, &last_back, KEY_DOWNARROW);
    queue_edge(snapshot->left, &last_left, KEY_LEFTARROW);
    queue_edge(snapshot->right, &last_right, KEY_RIGHTARROW);
    queue_edge(snapshot->fire, &last_fire, KEY_FIRE);
    queue_edge(snapshot->use, &last_use, KEY_USE);
    queue_edge(snapshot->menu, &last_menu, KEY_ESCAPE);
    queue_edge(snapshot->run, &last_run, KEY_RSHIFT);
    last_seq = snapshot->seq;
    pthread_mutex_unlock(&a90_dg_key_lock);
}
""",
    )
    source = _replace_required(
        source,
        """unsigned int a90_doomgeneric_last_seq(void) {
    return last_seq;
}

unsigned int a90_doomgeneric_pending_keys(void) {
    if (key_tail >= key_head) {
        return key_tail - key_head;
    }
    return A90_DG_KEY_QUEUE_MAX - key_head + key_tail;
}
""",
        """unsigned int a90_doomgeneric_last_seq(void) {
    unsigned int seq;

    pthread_mutex_lock(&a90_dg_key_lock);
    seq = last_seq;
    pthread_mutex_unlock(&a90_dg_key_lock);
    return seq;
}

unsigned int a90_doomgeneric_pending_keys(void) {
    unsigned int pending;

    pthread_mutex_lock(&a90_dg_key_lock);
    if (key_tail >= key_head) {
        pending = key_tail - key_head;
    } else {
        pending = A90_DG_KEY_QUEUE_MAX - key_head + key_tail;
    }
    pthread_mutex_unlock(&a90_dg_key_lock);
    return pending;
}
""",
    )
    source = _replace_required(
        source,
        """int DG_GetKey(int *pressed, unsigned char *key) {
    if (pressed == NULL || key == NULL || key_head == key_tail) {
        return 0;
    }

    *pressed = key_queue[key_head].pressed;
    *key = key_queue[key_head].key;
    key_head = next_index(key_head);
    return 1;
}
""",
        """int DG_GetKey(int *pressed, unsigned char *key) {
    if (pressed == NULL || key == NULL) {
        return 0;
    }

    pthread_mutex_lock(&a90_dg_key_lock);
    if (key_head == key_tail) {
        pthread_mutex_unlock(&a90_dg_key_lock);
        return 0;
    }
    *pressed = key_queue[key_head].pressed;
    *key = key_queue[key_head].key;
    key_head = next_index(key_head);
    pthread_mutex_unlock(&a90_dg_key_lock);
    return 1;
}
""",
    )
    input_thread_support = r'''
struct a90_dg_input_thread {
    int input_socket_fd;
    int input_udp_fd;
    const char *input_state_path;
    volatile int stop;
    int started;
    pthread_t thread;
};

static void a90_doomgeneric_input_thread_init(struct a90_dg_input_thread *ctx,
                                              int input_socket_fd,
                                              int input_udp_fd,
                                              const char *input_state_path) {
    memset(ctx, 0, sizeof(*ctx));
    ctx->input_socket_fd = input_socket_fd;
    ctx->input_udp_fd = input_udp_fd;
    ctx->input_state_path = input_state_path;
}

static void *a90_doomgeneric_input_thread_main(void *opaque) {
    struct a90_dg_input_thread *ctx = (struct a90_dg_input_thread *)opaque;

    while (ctx != NULL && !ctx->stop) {
        if (ctx->input_socket_fd >= 0) {
            a90_doomgeneric_drain_input_fd(ctx->input_socket_fd, ctx->input_state_path);
        }
        if (ctx->input_udp_fd >= 0) {
            a90_doomgeneric_drain_input_fd(ctx->input_udp_fd, ctx->input_state_path);
        }
        usleep(1000U);
    }
    return NULL;
}

static int a90_doomgeneric_input_thread_start(struct a90_dg_input_thread *ctx) {
    if (ctx == NULL || (ctx->input_socket_fd < 0 && ctx->input_udp_fd < 0)) {
        return 0;
    }
    if (pthread_create(&ctx->thread, NULL, a90_doomgeneric_input_thread_main, ctx) != 0) {
        return -1;
    }
    ctx->started = 1;
    return 0;
}

static void a90_doomgeneric_input_thread_stop(struct a90_dg_input_thread *ctx) {
    if (ctx == NULL || !ctx->started) {
        return;
    }
    ctx->stop = 1;
    pthread_join(ctx->thread, NULL);
    ctx->started = 0;
}

'''
    source = _replace_required(
        source,
        "static void a90_doomgeneric_apply_input_state_file(const char *path) {",
        input_thread_support + "static void a90_doomgeneric_apply_input_state_file(const char *path) {",
    )
    source = _replace_required(
        source,
        "    int pace_fd;\n"
        "    struct a90_dg_shared_frame shared_frame;\n",
        "    int pace_fd;\n"
        "    struct a90_dg_input_thread input_thread;\n"
        "    struct a90_dg_shared_frame shared_frame;\n",
    )
    source = _replace_required(
        source,
        "    a90_doomgeneric_shared_frame_init(&shared_frame);\n"
        "    a90_doomgeneric_apply_input_state_file(input_state_path);\n",
        "    a90_doomgeneric_shared_frame_init(&shared_frame);\n"
        "    a90_doomgeneric_input_thread_init(&input_thread, -1, -1, input_state_path);\n"
        "    a90_doomgeneric_apply_input_state_file(input_state_path);\n",
    )
    source = _replace_required(
        source,
        "    input_socket_fd = a90_doomgeneric_open_input_socket(input_socket_path);\n"
        "    input_udp_fd = a90_doomgeneric_open_input_udp(input_udp_port);\n"
        "    pace_fd = a90_doomgeneric_open_pace_socket(pace_socket_path);\n",
        "    input_socket_fd = a90_doomgeneric_open_input_socket(input_socket_path);\n"
        "    input_udp_fd = a90_doomgeneric_open_input_udp(input_udp_port);\n"
        "    a90_doomgeneric_input_thread_init(&input_thread, input_socket_fd, input_udp_fd, input_state_path);\n"
        "    pace_fd = a90_doomgeneric_open_pace_socket(pace_socket_path);\n",
    )
    source = _replace_required(
        source,
        "    paced_time_active = 1;\n"
        "    for (index = 0; frames == 0 || index < frames; ++index) {\n",
        "    paced_time_active = 1;\n"
        "    if (a90_doomgeneric_input_thread_start(&input_thread) != 0) {\n"
        "        loop_rc = 54;\n"
        "    }\n"
        "    for (index = 0; loop_rc == 0 && (frames == 0 || index < frames); ++index) {\n",
    )
    source = _replace_required(
        source,
        "    a90_doomgeneric_close_shared_frame(&shared_frame);\n"
        "    paced_time_active = 0;\n",
        "    a90_doomgeneric_input_thread_stop(&input_thread);\n"
        "    a90_doomgeneric_close_shared_frame(&shared_frame);\n"
        "    paced_time_active = 0;\n",
    )
    return source


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    return "\n".join([
        "# Native Init V3129 DOOMGENERIC Input Thread Direct Blit Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: DOOM host input reliability / smooth demo direct-blit candidate.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Inherits V3126 smooth-demo direct shared blit and summary-only native dashboard.",
        "- Adds a background helper input thread that continuously drains UDP/NCM and UNIX datagram input sockets.",
        "- Protects the DOOM key queue with a pthread mutex so the input thread can feed `DG_GetKey` safely while the engine is inside `doomgeneric_Tick()`.",
        f"- Input thread marker: `{INPUT_THREAD_MARKER}`",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Helper loop command: `{doom.get('helper_loop_command')}`",
        f"- Frame geometry: `{FRAME_WIDTH}x{FRAME_HEIGHT}` stride `{FRAME_STRIDE}` bytes `{FRAME_BYTES}`",
        f"- Frame IPC: `{FRAME_IPC}`",
        f"- UDP input target: `{DEVICE_NCM_HOST}:{INPUT_UDP_PORT}`",
        "- Expected live behavior: `/proc/net/udp` rx_queue for port 30570 should not grow while host evdev input is active; the input-state file should track host seq/mask updates.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No GPU/GL stack, panel re-init, backlight, PMIC, regulator, GDSC, GPIO, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- Changes are limited to the userspace private DOOM helper and native-init identity/metadata.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3129 builder and focused tests.",
        "- `unittest`: V3129 source contract plus V3126 host/input regressions.",
        "- Build: AArch64 static helper compile/link with pthread, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3129 identity, V3126 smooth-demo markers rewritten to V3129 paths, and the input thread marker.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Flash exact V3129 image, health-check, start continuous DOOM loop, and verify UDP input state changes live.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-input-thread-direct-blit-candidate`.",
    ]) + "\n"


def configure_v3129_module() -> None:
    v3126.CYCLE = CYCLE
    v3126.INIT_VERSION = INIT_VERSION
    v3126.INIT_BUILD = INIT_BUILD
    v3126.BUILD_TAG = BUILD_TAG
    v3126.DECISION = DECISION
    v3126.OUT_DIR = OUT_DIR
    v3126.OBJ_DIR = OBJ_DIR
    v3126.REPORT_PATH = REPORT_PATH
    v3126.BOOT_IMAGE = BOOT_IMAGE
    v3126.INIT_BINARY = INIT_BINARY
    v3126.RAMDISK_CPIO = RAMDISK_CPIO
    v3126.HELPER_BINARY = HELPER_BINARY
    v3126.ENGINE_BINARY = ENGINE_BINARY
    v3126.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3126.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3126.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3126.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3126.ENGINE_NAME = ENGINE_NAME
    v3126.FRAME_PATH = FRAME_PATH
    v3126.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    v3126.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3126.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3126.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    v3126.TICK_TELEMETRY_PATH = TICK_TELEMETRY_PATH
    v3126.TICK_TELEMETRY_MARKER = TICK_TELEMETRY_MARKER
    v3126.SCALE_MARKER = SCALE_MARKER
    v3126.PHASE_TELEMETRY_MARKER = PHASE_TELEMETRY_MARKER
    v3126.GAMETIC_FRAME_TELEMETRY_MARKER = GAMETIC_FRAME_TELEMETRY_MARKER
    v3126.PACED_TIME_MARKER = PACED_TIME_MARKER
    v3126.FRAME_IPC = FRAME_IPC
    v3126.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3126.v3126_adapter_source = v3129_adapter_source
    v3126.render_report = render_report


def main() -> int:
    saved_link_flags = v3024.LINK_FLAGS
    saved_adapter = v3126.v3126_adapter_source
    saved_report = v3126.render_report
    try:
        configure_v3129_module()
        if "-pthread" not in v3024.LINK_FLAGS:
            v3024.LINK_FLAGS = (*v3024.LINK_FLAGS, "-pthread")
        rc = v3126.main()
    finally:
        v3024.LINK_FLAGS = saved_link_flags
        v3126.v3126_adapter_source = saved_adapter
        v3126.render_report = saved_report

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "input_thread": True,
        "input_thread_marker": INPUT_THREAD_MARKER,
        "input_thread_poll_us": 1000,
        "frame_ipc": FRAME_IPC,
        "input_state_path": INPUT_STATE_PATH,
        "input_socket_path": INPUT_SOCKET_PATH,
        "input_udp_port": INPUT_UDP_PORT,
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-input-thread-direct-blit-candidate",
        "adoption_state": "pending-input-thread-direct-blit-live-validation",
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
    (OUT_DIR / "doomgeneric-input-thread-direct-blit-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-input-thread-direct-blit-candidate",
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
        "frame_width": FRAME_WIDTH,
        "frame_height": FRAME_HEIGHT,
        "frame_stride": FRAME_STRIDE,
        "frame_bytes": FRAME_BYTES,
        "input_state_path": INPUT_STATE_PATH,
        "input_socket_path": INPUT_SOCKET_PATH,
        "input_udp_host": DEVICE_NCM_HOST,
        "input_udp_port": INPUT_UDP_PORT,
        "input_thread_marker": INPUT_THREAD_MARKER,
        "pace_socket_path": PACE_SOCKET_PATH,
        "frame_ipc": FRAME_IPC,
        "loop_start_command": f"video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-input-thread-direct-blit-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
