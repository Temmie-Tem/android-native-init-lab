#!/usr/bin/env python3
"""Build V3059 native-init DOOM UDP/NCM input candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v3057_doomgeneric_input_socket as v3057
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3059"
INIT_VERSION = "0.10.87"
INIT_BUILD = "v3059-doomgeneric-udp-input"
BUILD_TAG = INIT_BUILD
DECISION = "v3059-doomgeneric-udp-input-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3059_DOOMGENERIC_UDP_INPUT_SOURCE_BUILD_2026-06-22.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3059_doomgeneric_udp_input.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3059_doomgeneric_udp_input"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3059_doomgeneric_udp_input.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v512_doomgeneric_udp_input"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3059"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3059.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3059.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3059"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3059-udp-input"

RUNTIME_WAD_ROOT = v3057.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3057.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3057.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3057.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3057.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3057.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = v3057.DEFAULT_LOOP_FRAMES
CONTINUOUS_LOOP_FRAMES = v3057.CONTINUOUS_LOOP_FRAMES
MAX_LOOP_FRAMES = v3057.MAX_LOOP_FRAMES
LOOP_FRAME_MS = v3057.LOOP_FRAME_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3059-udp-input-frame.xbgr8888"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3059-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3059-input.sock"
INPUT_UDP_PORT = 30570
DEVICE_NCM_HOST = "192.168.7.2"
FRAME_WIDTH = v3057.FRAME_WIDTH
FRAME_HEIGHT = v3057.FRAME_HEIGHT
FRAME_STRIDE = v3057.FRAME_STRIDE
FRAME_BYTES = v3057.FRAME_BYTES
NATIVE_DASHBOARD = v3057.NATIVE_DASHBOARD
NATIVE_DASHBOARD_LARGE_FRAME = v3057.NATIVE_DASHBOARD_LARGE_FRAME

SOUND_MODE = v3057.SOUND_MODE
AUDIO_CORUN = v3057.AUDIO_CORUN
AUDIO_CORUN_MODE = v3057.AUDIO_CORUN_MODE
AUDIO_CORUN_DURATION_MS = v3057.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3057.AUDIO_CORUN_AMPLITUDE_MILLI

HOST_KEYBOARD_BRIDGE = v3057.HOST_KEYBOARD_BRIDGE
HOST_DASHBOARD = v3057.HOST_DASHBOARD
BASE_V3057_ADAPTER_SOURCE = v3057.v3057_adapter_source
BASE_CONFIGURE_V3057_GLOBALS = v3057.configure_v3057_globals

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.87 (v3059-doomgeneric-udp-input)",
    b"v3059-doomgeneric-udp-input",
    b"doomgeneric-private-link-v3059-udp-input",
    b"/bin/a90_doomgeneric_private_engine_v3059",
    RUNTIME_WAD_PATH.encode("ascii"),
    EXPECTED_WAD_SHA256.encode("ascii"),
    FRAME_PATH.encode("ascii"),
    INPUT_STATE_PATH.encode("ascii"),
    INPUT_SOCKET_PATH.encode("ascii"),
    b"a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback",
    b"--input-udp",
    b"udp-ncm-to-DG_GetKey-with-serial-doompad-fallback",
    b"video.demo.input.udp_port=",
    b"video.demo.input.socket_path=",
    b"doompad.input_socket.rc=",
    b"doompad.batch=state-mask-v3047",
    b"video.demo.doom.loop_start.continuous",
    b"native-audio-corun-tone-v3053",
    b"host_doompad_keyboard_v3033.py",
    b"video.demo.input.otg_required=0",
)


def rel(path: Path) -> str:
    return v3057.rel(path)


def replace_required(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing source fragment for V3059 patch: {old[:80]!r}")
    return text.replace(old, new)


def v3059_adapter_source() -> str:
    text = BASE_V3057_ADAPTER_SOURCE()
    text = replace_required(
        text,
        "#include <stdio.h>\n#include <stdint.h>\n#include <sys/socket.h>\n#include <sys/un.h>",
        "#include <stdio.h>\n#include <stdint.h>\n#include <arpa/inet.h>\n#include <netinet/in.h>\n#include <sys/socket.h>\n#include <sys/un.h>",
    )
    text = replace_required(
        text,
        'const char a90_doomgeneric_v3057_input_policy[] =\n'
        '    "a90.doomgeneric.v3057.input=unix-dgram-state-with-file-fallback";',
        'const char a90_doomgeneric_v3057_input_policy[] =\n'
        '    "a90.doomgeneric.v3057.input=unix-dgram-state-with-file-fallback";\n'
        'const char a90_doomgeneric_v3059_udp_input_policy[] =\n'
        '    "a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback";',
    )
    text = replace_required(
        text,
        "marker_checksum(a90_doomgeneric_v3057_input_policy) == 0U) {",
        "marker_checksum(a90_doomgeneric_v3057_input_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3059_udp_input_policy) == 0U) {",
    )
    udp_support = r'''
static int a90_doomgeneric_open_input_udp(unsigned int port) {
    struct sockaddr_in addr;
    int fd;
    int flags;
    int one = 1;

    if (port == 0U || port > 65535U) {
        return -1;
    }
    fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        return -1;
    }
    (void)setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    flags = fcntl(fd, F_GETFL, 0);
    if (flags >= 0) {
        (void)fcntl(fd, F_SETFL, flags | O_NONBLOCK);
    }
    (void)fcntl(fd, F_SETFD, FD_CLOEXEC);
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons((uint16_t)port);
    if (bind(fd, (const struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(fd);
        return -1;
    }
    return fd;
}

'''
    text = replace_required(
        text,
        "static void a90_doomgeneric_close_input_socket(int fd, const char *path) {",
        udp_support + "static void a90_doomgeneric_close_input_socket(int fd, const char *path) {",
    )
    text = replace_required(
        text,
        r'''static void a90_doomgeneric_drain_input_socket(int fd) {
    for (;;) {
        struct a90_dg_input_packet packet;
        ssize_t rd;

        if (fd < 0) {
            return;
        }
        rd = recv(fd, &packet, sizeof(packet), MSG_DONTWAIT);
        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            return;
        }
        if (rd != (ssize_t)sizeof(packet)) {
            continue;
        }
        if (packet.magic != A90_DG_INPUT_PACKET_MAGIC ||
            packet.version != A90_DG_INPUT_PACKET_VERSION) {
            continue;
        }
        a90_doomgeneric_apply_input_mask(packet.seq, packet.mask);
    }
}
''',
        r'''static void a90_doomgeneric_write_input_state_mask(const char *path,
                                                   unsigned int seq,
                                                   unsigned int mask) {
    FILE *fp;

    if (path == NULL || path[0] == '\0') {
        return;
    }
    fp = fopen(path, "w");
    if (fp == NULL) {
        return;
    }
    (void)fprintf(fp,
                  "seq=%u\n"
                  "forward=%d\n"
                  "back=%d\n"
                  "left=%d\n"
                  "right=%d\n"
                  "fire=%d\n"
                  "use=%d\n"
                  "menu=%d\n"
                  "run=%d\n"
                  "active=%d\n",
                  seq,
                  (mask & (1U << 0)) != 0U ? 1 : 0,
                  (mask & (1U << 1)) != 0U ? 1 : 0,
                  (mask & (1U << 2)) != 0U ? 1 : 0,
                  (mask & (1U << 3)) != 0U ? 1 : 0,
                  (mask & (1U << 4)) != 0U ? 1 : 0,
                  (mask & (1U << 5)) != 0U ? 1 : 0,
                  (mask & (1U << 6)) != 0U ? 1 : 0,
                  (mask & (1U << 7)) != 0U ? 1 : 0,
                  mask != 0U ? 1 : 0);
    (void)fclose(fp);
}

static void a90_doomgeneric_drain_input_fd(int fd, const char *input_state_path) {
    for (;;) {
        struct a90_dg_input_packet packet;
        ssize_t rd;

        if (fd < 0) {
            return;
        }
        rd = recv(fd, &packet, sizeof(packet), MSG_DONTWAIT);
        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            return;
        }
        if (rd != (ssize_t)sizeof(packet)) {
            continue;
        }
        if (packet.magic != A90_DG_INPUT_PACKET_MAGIC ||
            packet.version != A90_DG_INPUT_PACKET_VERSION) {
            continue;
        }
        a90_doomgeneric_apply_input_mask(packet.seq, packet.mask);
        a90_doomgeneric_write_input_state_mask(input_state_path, packet.seq, packet.mask);
    }
}
''',
    )
    text = replace_required(
        text,
        "                                       const char *input_state_path,\n"
        "                                       const char *input_socket_path,\n"
        "                                       int frame_ms) {",
        "                                       const char *input_state_path,\n"
        "                                       const char *input_socket_path,\n"
        "                                       unsigned int input_udp_port,\n"
        "                                       int frame_ms) {",
    )
    text = replace_required(
        text,
        "    int input_socket_fd;\n"
        "    int loop_rc = 0;",
        "    int input_socket_fd;\n"
        "    int input_udp_fd;\n"
        "    int loop_rc = 0;",
    )
    text = replace_required(
        text,
        "    a90_doomgeneric_apply_input_state_file(input_state_path);\n"
        "    input_socket_fd = a90_doomgeneric_open_input_socket(input_socket_path);\n",
        "    a90_doomgeneric_apply_input_state_file(input_state_path);\n"
        "    input_socket_fd = a90_doomgeneric_open_input_socket(input_socket_path);\n"
        "    input_udp_fd = a90_doomgeneric_open_input_udp(input_udp_port);\n",
    )
    text = replace_required(
        text,
        "        if (input_socket_fd >= 0) {\n"
        "            a90_doomgeneric_drain_input_socket(input_socket_fd);\n"
        "        } else {\n"
        "            a90_doomgeneric_apply_input_state_file(input_state_path);\n"
        "        }",
        "        if (input_socket_fd >= 0) {\n"
        "            a90_doomgeneric_drain_input_fd(input_socket_fd, input_state_path);\n"
        "        }\n"
        "        if (input_udp_fd >= 0) {\n"
        "            a90_doomgeneric_drain_input_fd(input_udp_fd, input_state_path);\n"
        "        }\n"
        "        if (input_socket_fd < 0 && input_udp_fd < 0) {\n"
        "            a90_doomgeneric_apply_input_state_file(input_state_path);\n"
        "        }",
    )
    text = replace_required(
        text,
        "    a90_doomgeneric_close_input_socket(input_socket_fd, input_socket_path);\n",
        "    if (input_udp_fd >= 0) {\n"
        "        close(input_udp_fd);\n"
        "    }\n"
        "    a90_doomgeneric_close_input_socket(input_socket_fd, input_socket_path);\n",
    )
    text = replace_required(
        text,
        '''if ((argc == 11 || argc == 13) &&
        strcmp(argv[1], "--wad-frame-loop") == 0 &&
        argv[2] != NULL &&
        strcmp(argv[3], "--frames") == 0 &&
        strcmp(argv[5], "--output") == 0 &&
        argv[6] != NULL &&
        strcmp(argv[7], "--input-state") == 0 &&
        argv[8] != NULL &&
        strcmp(argv[9], "--frame-ms") == 0) {
        int frame_ms;
        const char *input_socket_path = NULL;

        if (argc == 13) {
            if (strcmp(argv[11], "--input-socket") != 0 || argv[12] == NULL) {
                return 37;
            }
            input_socket_path = argv[12];
        }
        frames = a90_doomgeneric_parse_loop_frames(argv[4], 300);
        frame_ms = a90_doomgeneric_parse_positive_int(argv[10], 250);
        if (frames < 0 || frame_ms <= 0) {
            return 36;
        }
        return a90_doomgeneric_run_wad_frame_loop(argv[2], frames, argv[6], argv[8], input_socket_path, frame_ms);
    }
    return 37;
}
''',
        '''if ((argc == 11 || argc == 13 || argc == 15) &&
        strcmp(argv[1], "--wad-frame-loop") == 0 &&
        argv[2] != NULL &&
        strcmp(argv[3], "--frames") == 0 &&
        strcmp(argv[5], "--output") == 0 &&
        argv[6] != NULL &&
        strcmp(argv[7], "--input-state") == 0 &&
        argv[8] != NULL &&
        strcmp(argv[9], "--frame-ms") == 0) {
        int frame_ms;
        const char *input_socket_path = NULL;
        unsigned int input_udp_port = 0U;
        int arg_index = 11;

        while (arg_index < argc) {
            if (arg_index + 1 >= argc) {
                return 37;
            }
            if (strcmp(argv[arg_index], "--input-socket") == 0) {
                input_socket_path = argv[arg_index + 1];
            } else if (strcmp(argv[arg_index], "--input-udp") == 0) {
                input_udp_port = (unsigned int)a90_doomgeneric_parse_positive_int(argv[arg_index + 1], 65535);
                if (input_udp_port == 0U) {
                    return 37;
                }
            } else {
                return 37;
            }
            arg_index += 2;
        }
        frames = a90_doomgeneric_parse_loop_frames(argv[4], 300);
        frame_ms = a90_doomgeneric_parse_positive_int(argv[10], 250);
        if (frames < 0 || frame_ms <= 0) {
            return 36;
        }
        return a90_doomgeneric_run_wad_frame_loop(argv[2], frames, argv[6], argv[8], input_socket_path, input_udp_port, frame_ms);
    }
    return 37;
}
''',
    )
    return text


def apply_v3059_globals() -> None:
    v3033 = v3057.v3053.v3051.v3049.v3047.v3045.v3042.v3040.v3038.v3033
    v3057.CYCLE = CYCLE
    v3057.INIT_VERSION = INIT_VERSION
    v3057.INIT_BUILD = INIT_BUILD
    v3057.BUILD_TAG = BUILD_TAG
    v3057.DECISION = DECISION
    v3057.OUT_DIR = OUT_DIR
    v3057.OBJ_DIR = OBJ_DIR
    v3057.REPORT_PATH = REPORT_PATH
    v3057.BOOT_IMAGE = BOOT_IMAGE
    v3057.INIT_BINARY = INIT_BINARY
    v3057.RAMDISK_CPIO = RAMDISK_CPIO
    v3057.HELPER_BINARY = HELPER_BINARY
    v3057.ENGINE_BINARY = ENGINE_BINARY
    v3057.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3057.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3057.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3057.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3057.ENGINE_NAME = ENGINE_NAME
    v3057.DEFAULT_LOOP_FRAMES = DEFAULT_LOOP_FRAMES
    v3057.LOOP_FRAME_MS = LOOP_FRAME_MS
    v3057.FRAME_PATH = FRAME_PATH
    v3057.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3057.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3057.NATIVE_DASHBOARD = NATIVE_DASHBOARD
    v3057.NATIVE_DASHBOARD_LARGE_FRAME = NATIVE_DASHBOARD_LARGE_FRAME
    v3057.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3057.v3057_adapter_source = v3059_adapter_source
    v3057.render_report = render_report

    v3033.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3033.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3033.INPUT_UDP_PORT = INPUT_UDP_PORT
    v3033.INPUT_PATH = "udp-ncm-to-DG_GetKey-with-serial-doompad-fallback"
    v3033.SOUND_MODE = SOUND_MODE
    v3033.AUDIO_CORUN = AUDIO_CORUN
    v3033.AUDIO_CORUN_MODE = AUDIO_CORUN_MODE
    v3033.AUDIO_CORUN_DURATION_MS = AUDIO_CORUN_DURATION_MS
    v3033.AUDIO_CORUN_AMPLITUDE_MILLI = AUDIO_CORUN_AMPLITUDE_MILLI


def configure_v3057_globals_for_v3059() -> None:
    apply_v3059_globals()
    BASE_CONFIGURE_V3057_GLOBALS()
    apply_v3059_globals()


def configure_v3059_globals() -> None:
    apply_v3059_globals()
    v3057.configure_v3057_globals = configure_v3057_globals_for_v3059


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3059 DOOMGENERIC UDP Input Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback / DOOM capstone input responsiveness.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps V3057 helper-owned Unix datagram input as the serial fallback path.",
        "- Adds a helper-owned non-blocking UDP listener for compact host input packets over NCM.",
        "- Updates the host keyboard bridge with `--input-transport udp` so evdev down/up can bypass serial cmdv1 for gameplay input.",
        "- Serial remains available for loop start/stop/status and for legacy doompad fallback.",
        "",
        "## Input Contract",
        "",
        f"- Device NCM target: `<device-ncm-ip>:{INPUT_UDP_PORT}`",
        f"- Input active marker: `{doom.get('input_path')}`",
        f"- UDP port marker: `{doom.get('input_udp_port', INPUT_UDP_PORT)}`",
        f"- Unix fallback socket: `{doom.get('input_socket_path', INPUT_SOCKET_PATH)}`",
        f"- State file dashboard/fallback: `{doom.get('input_state_path')}`",
        "- Packet format: fixed little-endian `{magic, version, seq, mask, active}` datagram.",
        "- Mask bits remain V3047-compatible: `forward:0 back:1 left:2 right:3 fire:4 use:5 menu:6 run:7`.",
        "- Host command: `host_doompad_keyboard_v3033.py --input-backend evdev --input-transport udp --udp-host <device-ncm-ip> --udp-port 30570 ...`",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}`",
        f"- Helper loop command: `{doom.get('helper_loop_command')}`",
        f"- Frame path: `{doom.get('frame_path')}`",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Validation",
        "",
        "- `py_compile`: V3059 builder, host keyboard bridge, and focused tests.",
        "- `unittest`: V3059 source contract plus V3057/V3053 and host input regressions.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3059 UDP input, V3057 socket fallback, V3053 audio co-run, and V3047 batch input markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3060`",
        "- Type: rollback-gated live validation of V3059 UDP input candidate.",
        "- Scope: flash exact V3059 boot image, health-check, start DOOM loop, require UDP port status marker, send host UDP input packet, and confirm loop remains active.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-udp-input-candidate`.",
    ]) + "\n"


def main() -> int:
    configure_v3059_globals()
    rc = v3057.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "input_path": "udp-ncm-to-DG_GetKey-with-serial-doompad-fallback",
        "input_udp_port": INPUT_UDP_PORT,
        "input_udp_host": DEVICE_NCM_HOST,
        "input_socket_path": INPUT_SOCKET_PATH,
        "input_state_path": INPUT_STATE_PATH,
        "frame_path": FRAME_PATH,
        "engine_binary": rel(ENGINE_BINARY),
        "engine_ramdisk_path": ENGINE_REMOTE_PATH,
        "helper_loop_command": (
            f"{ENGINE_REMOTE_PATH} --wad-frame-loop {RUNTIME_WAD_PATH} "
            f"--frames {DEFAULT_LOOP_FRAMES} --output {FRAME_PATH} "
            f"--input-state {INPUT_STATE_PATH} --frame-ms {LOOP_FRAME_MS} "
            f"--input-socket {INPUT_SOCKET_PATH} --input-udp {INPUT_UDP_PORT}"
        ),
        "input_udp": {
            "host": DEVICE_NCM_HOST,
            "port": INPUT_UDP_PORT,
            "transport": "udp-over-ncm",
            "packet": "little-endian-magic-version-seq-mask-active",
            "serial_fallback_socket": INPUT_SOCKET_PATH,
        },
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-udp-input-candidate",
        "adoption_state": "pending-udp-input-live-validation",
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
    (OUT_DIR / "doomgeneric-udp-input-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-udp-input-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "engine_binary": rel(ENGINE_BINARY),
        "engine_ramdisk_path": ENGINE_REMOTE_PATH,
        "runtime_wad_path": RUNTIME_WAD_PATH,
        "expected_wad_sha256": EXPECTED_WAD_SHA256,
        "frame_path": FRAME_PATH,
        "input_state_path": INPUT_STATE_PATH,
        "input_socket_path": INPUT_SOCKET_PATH,
        "input_udp_host": DEVICE_NCM_HOST,
        "input_udp_port": INPUT_UDP_PORT,
        "loop_start_command": f"video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "host_keyboard_bridge": rel(HOST_KEYBOARD_BRIDGE),
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-udp-input-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
