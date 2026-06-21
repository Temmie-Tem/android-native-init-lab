#!/usr/bin/env python3
"""Build V3031 native-init doomgeneric visible-frame candidate.

V3031 adds the first WAD-backed visible frame path: the private helper can dump
a bounded doomgeneric frame from the SD-staged WAD, and native-init can blit
that raw frame into the existing KMS/menu presentation flow. It still performs
no device action and does not copy WAD/IWAD bytes into public, ramdisk, or boot.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
import build_native_init_boot_v3029_doomgeneric_sd_wad_command as v3029
import native_doomgeneric_engine_integration_build_v3024 as v3024
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3031"
INIT_VERSION = "0.10.75"
INIT_BUILD = "v3031-doomgeneric-visible-frame"
BUILD_TAG = INIT_BUILD
DECISION = "v3031-doomgeneric-visible-frame-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3031_DOOMGENERIC_VISIBLE_FRAME_SOURCE_BUILD_2026-06-22.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3031_doomgeneric_visible_frame.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3031_doomgeneric_visible_frame"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3031_doomgeneric_visible_frame.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v511_doomgeneric_visible_frame"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3031"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3031.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3031.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3031"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3031-visible-frame"

RUNTIME_WAD_ROOT = v3029.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3029.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3029.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3029.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = 8
DEFAULT_SMOKE_FRAMES = v3029.DEFAULT_SMOKE_FRAMES
MAX_FRAME_TICKS = v3029.MAX_SMOKE_FRAMES
FRAME_PATH = "/tmp/a90-doomgeneric-v3031-frame.xbgr8888"
FRAME_WIDTH = 640
FRAME_HEIGHT = 400
FRAME_STRIDE = FRAME_WIDTH * 4
FRAME_BYTES = FRAME_STRIDE * FRAME_HEIGHT

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.75 (v3031-doomgeneric-visible-frame)",
    b"v3031-doomgeneric-visible-frame",
    b"doomgeneric-private-link-v3031-visible-frame",
    b"/bin/a90_doomgeneric_private_engine_v3031",
    RUNTIME_WAD_PATH.encode("ascii"),
    EXPECTED_WAD_SHA256.encode("ascii"),
    FRAME_PATH.encode("ascii"),
    b"--wad-smoke",
    b"--wad-frame-dump",
    b"--output",
    b"a90.doomgeneric.v3031.visible_frame=frame-dump-xbgr8888",
    b"video demo doom frame [frames] --wad runtime-private --sha256",
    b"video.demo.doom.frame=doomgeneric-sd-wad-visible-frame",
    b"video.demo.doom.frame.display.presented=1",
    b"menu.demo.doom.action=visible-frame-preview",
    b"video.status.doomgeneric.visible_frame=1",
    b"video.demo.asset.wad.embedded_in_boot=%d",
    b"video.demo.input.otg_required=0",
)


def rel(path: Path) -> str:
    return v3029.rel(path)


def shell_define(name: str, value: str) -> str:
    return v3029.shell_define(name, value)


def numeric_define(name: str, value: int) -> str:
    return v3029.numeric_define(name, value)


def v3031_adapter_source() -> str:
    text = v3029.v3029_adapter_source()
    text = text.replace(
        "#include <stdint.h>\n#include <stdlib.h>\n#include <string.h>",
        "#include <errno.h>\n"
        "#include <fcntl.h>\n"
        "#include <stdint.h>\n"
        "#include <stdlib.h>\n"
        "#include <string.h>\n"
        "#include <unistd.h>\n\n"
        "#ifndef O_CLOEXEC\n"
        "#define O_CLOEXEC 0\n"
        "#endif\n"
        "#ifndef O_NOFOLLOW\n"
        "#define O_NOFOLLOW 0\n"
        "#endif",
    )
    text = text.replace(
        '"a90.doomgeneric.v3029.sd_wad_command=1";',
        '"a90.doomgeneric.v3031.visible_frame=frame-dump-xbgr8888";',
    )
    text = text.replace(
        '"a90.doomgeneric.v3029.wad_smoke=bounded";',
        '"a90.doomgeneric.v3031.wad_smoke=bounded";\n'
        'const char a90_doomgeneric_v3031_frame_dump_policy[] =\n'
        '    "a90.doomgeneric.v3031.frame_dump=raw-xbgr8888-file";',
    )
    frame_dump = r'''
static int a90_doomgeneric_write_full(int fd, const void *data, size_t bytes) {
    size_t done = 0;

    while (done < bytes) {
        ssize_t wr = write(fd, (const char *)data + done, bytes - done);

        if (wr < 0) {
            if (errno == EINTR) {
                continue;
            }
            return 40;
        }
        if (wr == 0) {
            return 41;
        }
        done += (size_t)wr;
    }
    return 0;
}

int a90_doomgeneric_dump_frame_xbgr8888(const char *output_path) {
    const size_t bytes = (size_t)DOOMGENERIC_RESX * (size_t)DOOMGENERIC_RESY * sizeof(frame_sink[0]);
    int fd;
    int rc;

    if (output_path == NULL || output_path[0] == '\0' || sizeof(frame_sink[0]) != 4U) {
        return 42;
    }
    fd = open(output_path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        return 43;
    }
    rc = a90_doomgeneric_write_full(fd, frame_sink, bytes);
    if (close(fd) < 0 && rc == 0) {
        rc = 44;
    }
    return rc;
}

int a90_doomgeneric_run_wad_frame_dump(const char *wad_path, int frames, const char *output_path) {
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
        frames <= 0 || frames > 300) {
        return 45;
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
        doomgeneric_Tick();
    }
    if (a90_doomgeneric_presented_frames() == 0U) {
        return 46;
    }
    return a90_doomgeneric_dump_frame_xbgr8888(output_path);
}

'''
    text = text.replace("int main(int argc, char **argv) {", frame_dump + "int main(int argc, char **argv) {")
    text = text.replace(
        "marker_checksum(a90_doomgeneric_v3029_wad_smoke_policy) == 0U) {",
        "marker_checksum(a90_doomgeneric_v3029_wad_smoke_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3031_frame_dump_policy) == 0U) {",
    )
    text = text.replace(
        r'''int main(int argc, char **argv) {
    int frames;

    if (argc == 1) {
        return a90_doomgeneric_native_probe_entry();
    }
    if (argc == 5 &&
        strcmp(argv[1], "--wad-smoke") == 0 &&
        argv[2] != NULL &&
        strcmp(argv[3], "--frames") == 0) {
        frames = a90_doomgeneric_parse_positive_int(argv[4], 300);
        if (frames <= 0) {
            return 32;
        }
        return a90_doomgeneric_run_wad_smoke(argv[2], frames);
    }
    return 33;
}
''',
        r'''int main(int argc, char **argv) {
    int frames;

    if (argc == 1) {
        return a90_doomgeneric_native_probe_entry();
    }
    if (argc == 5 &&
        strcmp(argv[1], "--wad-smoke") == 0 &&
        argv[2] != NULL &&
        strcmp(argv[3], "--frames") == 0) {
        frames = a90_doomgeneric_parse_positive_int(argv[4], 300);
        if (frames <= 0) {
            return 32;
        }
        return a90_doomgeneric_run_wad_smoke(argv[2], frames);
    }
    if (argc == 7 &&
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
    )
    return text


def build_v3031_engine() -> dict[str, Any]:
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
        v3024.ADAPTER_SOURCE_TEXT = v3031_adapter_source()
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
            numeric_define("A90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES", RUNTIME_WAD_MAX_BYTES),
            numeric_define("A90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES", MAX_FRAME_TICKS),
            numeric_define("A90_DOOMGENERIC_BRIDGE_FRAME_WIDTH", FRAME_WIDTH),
            numeric_define("A90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT", FRAME_HEIGHT),
            numeric_define("A90_DOOMGENERIC_BRIDGE_FRAME_STRIDE", FRAME_STRIDE),
            numeric_define("A90_DOOMGENERIC_BRIDGE_FRAME_BYTES", FRAME_BYTES),
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
        raise RuntimeError(f"missing V3031 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_frame", {})
    markers = manifest.get("v3031_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3031 DOOMGENERIC Visible Frame Source Build",
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
        "- Extends the private doomgeneric helper with `--wad-frame-dump <path> --frames N --output <frame>`.",
        "- Adds native-init `video demo doom frame [frames] --wad runtime-private --sha256 EXPECTED`.",
        "- The command verifies the SD WAD path/hash first, asks the helper for one bounded raw frame, then blits that frame through the existing KMS dumb-buffer path.",
        "- The DEMO > DOOM menu item now launches an 8-frame WAD-backed visible-frame preview and restores the menu.",
        "- Existing `verify`, `play`, and `engine-probe` command surfaces remain bounded.",
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
        "## Frame Contract",
        "",
        f"- Helper frame command: `{doom.get('helper_frame_command')}`",
        f"- Native command: `{doom.get('frame_command')}`",
        f"- Frame path: `{doom.get('frame_path')}`",
        f"- Frame format: `{doom.get('frame_format')}`",
        f"- Frame geometry: `{doom.get('frame_width')}x{doom.get('frame_height')}` stride `{doom.get('frame_stride')}` bytes `{doom.get('frame_bytes')}`",
        f"- KMS path: `{doom.get('kms_path')}`",
        "",
        "## Private Engine Helper",
        "",
        f"- Bundled helper path: `{doom.get('engine_ramdisk_path')}`",
        f"- V3031 engine binary: `{doom.get('engine_binary')}`",
        f"- V3031 engine SHA256: `{doom.get('engine_binary_sha256')}`",
        f"- V3031 engine bytes: `{doom.get('engine_binary_bytes')}`",
        f"- Helper bundled in ramdisk: `{int(bool(doom.get('helper_bundled_in_ramdisk')))}`",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- No flash, serial command, Wi-Fi action, sysfs write, evdev injection, uinput, PMIC, regulator, backlight, GPIO, GDSC, or forbidden partition path is touched.",
        "- WAD/IWAD bytes remain only on the runtime SD path and are not copied into public, ramdisk, boot image, reports, or generated source.",
        "- The frame dump is a bounded temporary raw-frame artifact path, not a WAD copy.",
        "- The generated boot image and helper are private/untracked. Public output is limited to source, tests, and this metadata-only report.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata` for the next live unit.",
        "",
        "## Host Validation",
        "",
        "- `py_compile`: builder, selector, and focused tests.",
        "- `unittest`: V3031 visible-frame tests, V3029 SD-WAD command tests, and selector tests.",
        "- Build: AArch64 static private doomgeneric helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3031 visible-frame command, frame path, SD WAD path/hash, and bounded helper markers.",
        "- Ramdisk inventory: helper path present and WAD file count is zero.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3032`",
        "- Type: rollback-gated live validation of V3031 visible-frame candidate.",
        "- Scope: flash only the exact V3031 boot image through `native_init_flash.py`, health-check, run `video demo doom frame 8 --wad runtime-private --sha256 EXPECTED`, confirm KMS presentation markers, then rollback to V2321.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-visible-frame-candidate`.",
    ]) + "\n"


def main() -> int:
    source = v3024.collect_source_state()
    if not source["source_exists"] or not source["git_head_matches_pin"] or not source["git_status_clean"]:
        raise RuntimeError("private doomgeneric source is not pinned and clean")
    engine = build_v3031_engine()
    configure_base()
    patch_ramdisk_with_doomgeneric_helper()
    v2859.render_report = render_report
    rc = v2859.main()
    marker_strings = require_strings(BOOT_IMAGE)
    ramdisk_entries = v3029.list_cpio_entries(RAMDISK_CPIO)
    helper_entry_present = ENGINE_RAMDISK_PATH in ramdisk_entries
    wad_count = v3029.count_wad_entries(ramdisk_entries)
    if not helper_entry_present:
        raise RuntimeError(f"missing V3031 helper entry in ramdisk: {ENGINE_RAMDISK_PATH}")
    if wad_count != 0:
        raise RuntimeError(f"unexpected WAD files in V3031 ramdisk: {wad_count}")

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-visible-frame-candidate",
        "parent_test_artifact": "v3030-doomgeneric-sd-wad-command-live",
        "doomgeneric_visible_frame": {
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
            "max_frame_ticks": MAX_FRAME_TICKS,
            "frame_path": FRAME_PATH,
            "frame_format": "xbgr8888-raw",
            "frame_width": FRAME_WIDTH,
            "frame_height": FRAME_HEIGHT,
            "frame_stride": FRAME_STRIDE,
            "frame_bytes": FRAME_BYTES,
            "helper_frame_command": (
                f"{ENGINE_REMOTE_PATH} --wad-frame-dump {RUNTIME_WAD_PATH} "
                f"--frames {DEFAULT_FRAME_TICKS} --output {FRAME_PATH}"
            ),
            "helper_smoke_command": f"{ENGINE_REMOTE_PATH} --wad-smoke {RUNTIME_WAD_PATH} --frames {DEFAULT_SMOKE_FRAMES}",
            "helper_bundled_in_ramdisk": helper_entry_present,
            "ramdisk_wad_file_count": wad_count,
            "public_wad_file_count": v3024.count_files(v3024.PUBLIC_WAD_ROOT, ".wad")["count"],
            "wad_embedded_in_boot": 0,
            "input_path": "serial-doompad-to-DG_GetKey",
            "otg_required": False,
            "evdev_injection": False,
            "uinput": False,
            "sound_mode": "disabled-nosound-nomusic",
            "kms_path": "existing-kms-dumb-buffer-blit-present",
            "verify_command": f"video demo doom verify --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
            "play_command": f"video demo doom play {DEFAULT_SMOKE_FRAMES} --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
            "frame_command": f"video demo doom frame {DEFAULT_FRAME_TICKS} --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
            "menu_action": "DEMO > DOOM visible-frame-preview",
            "live_validation": "pending-v3032",
        },
        "v3031_engine_build": engine,
        "v3031_marker_strings": marker_strings,
        "adoption_state": "pending-visible-frame-live-validation",
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
    (OUT_DIR / "doomgeneric-visible-frame-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-visible-frame-candidate",
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
        "frame_format": "xbgr8888-raw",
        "frame_command": f"video demo doom frame {DEFAULT_FRAME_TICKS} --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "ramdisk_wad_file_count": wad_count,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-visible-frame-live-validation",
        "note": "V3031 bundles only the private helper and visible-frame command metadata; WAD/IWAD bytes remain runtime-private and are not copied into public, ramdisk, or boot image.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
