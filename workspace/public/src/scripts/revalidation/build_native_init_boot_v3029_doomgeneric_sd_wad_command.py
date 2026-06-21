#!/usr/bin/env python3
"""Build V3029 native-init doomgeneric SD-WAD command candidate.

V3029 wires bounded `video demo doom verify/play --wad runtime-private` command
handling around the SD-staged private WAD path and hash. It builds a new private
doomgeneric helper that can smoke-run the engine against the SD WAD, but it does
not copy WAD/IWAD bytes into public, ramdisk, or boot image.
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
import native_doomgeneric_engine_integration_build_v3024 as v3024
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3029"
INIT_VERSION = "0.10.74"
INIT_BUILD = "v3029-doomgeneric-sd-wad-command"
BUILD_TAG = INIT_BUILD
DECISION = "v3029-doomgeneric-sd-wad-command-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3029_DOOMGENERIC_SD_WAD_COMMAND_SOURCE_BUILD_2026-06-22.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3029_doomgeneric_sd_wad_command.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3029_doomgeneric_sd_wad_command"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3029_doomgeneric_sd_wad_command.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v510_doomgeneric_sd_wad_command"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3029"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3029.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3029.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3029"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3029-sd-wad-smoke"

RUNTIME_WAD_ROOT = "/mnt/sdext/a90/runtime/doom/v3028/"
RUNTIME_WAD_PATH = RUNTIME_WAD_ROOT + "DOOM1.WAD"
EXPECTED_WAD_SHA256 = "1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771"
RUNTIME_WAD_MAX_BYTES = 67_108_864
DEFAULT_SMOKE_FRAMES = 16
MAX_SMOKE_FRAMES = 300

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.74 (v3029-doomgeneric-sd-wad-command)",
    b"v3029-doomgeneric-sd-wad-command",
    b"doomgeneric-private-link-v3029-sd-wad-smoke",
    b"/bin/a90_doomgeneric_private_engine_v3029",
    b"/mnt/sdext/a90/runtime/doom/v3028/",
    b"/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD",
    EXPECTED_WAD_SHA256.encode("ascii"),
    b"--wad-smoke",
    b"a90.doomgeneric.v3029.wad_smoke=bounded",
    b"video demo doom verify --wad runtime-private --sha256",
    b"video demo doom play [frames] --wad runtime-private --sha256",
    b"video.demo.doom.verify=doomgeneric-sd-wad",
    b"video.demo.doom.play=doomgeneric-sd-wad-smoke",
    b"video.demo.doom.play.verify.sha256_match=%d",
    b"video.demo.asset.wad.embedded_in_boot=%d",
    b"video.demo.input.otg_required=0",
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def run(argv: list[str], *, cwd: Path | None = None) -> v3024.subprocess.CompletedProcess[str]:
    return v3024.run(argv, cwd=cwd)


def require_success(result: v3024.subprocess.CompletedProcess[str], description: str) -> str:
    return v3024.require_success(result, description)


def shell_define(name: str, value: str) -> str:
    return f'-D{name}="{value}"'


def numeric_define(name: str, value: int) -> str:
    return f"-D{name}={value}"


def v3029_adapter_source() -> str:
    text = v3024.ADAPTER_SOURCE_TEXT
    text = text.replace(
        "#include <stdint.h>\n#include <string.h>",
        "#include <stdint.h>\n#include <stdlib.h>\n#include <string.h>",
    )
    text = text.replace(
        '#define A90_DG_RUNTIME_WAD_PATH "/cache/a90-runtime/pkg/doom/v3024/DOOM1.WAD"',
        f'#define A90_DG_RUNTIME_WAD_PATH "{RUNTIME_WAD_PATH}"',
    )
    text = text.replace(
        'const char a90_doomgeneric_v3024_input_policy[] =\n'
        '    "a90.doomgeneric.v3024.input=serial-doompad-to-DG_GetKey";\n',
        'const char a90_doomgeneric_v3024_input_policy[] =\n'
        '    "a90.doomgeneric.v3024.input=serial-doompad-to-DG_GetKey";\n'
        'const char a90_doomgeneric_v3029_marker[] =\n'
        '    "a90.doomgeneric.v3029.sd_wad_command=1";\n'
        'const char a90_doomgeneric_v3029_wad_smoke_policy[] =\n'
        '    "a90.doomgeneric.v3029.wad_smoke=bounded";\n',
    )
    smoke = r'''
static int a90_doomgeneric_parse_positive_int(const char *text, int max_value) {
    char *end = NULL;
    long value;

    if (text == NULL || text[0] == '\0') {
        return -1;
    }
    value = strtol(text, &end, 10);
    if (end == NULL || *end != '\0' || value <= 0 || value > max_value) {
        return -1;
    }
    return (int)value;
}

int a90_doomgeneric_run_wad_smoke(const char *wad_path, int frames) {
    static char arg0[] = "doomgeneric";
    static char arg_iwad[] = "-iwad";
    static char arg_nosound[] = "-nosound";
    static char arg_nomusic[] = "-nomusic";
    static char arg_mb[] = "-mb";
    static char arg_mb_value[] = "6";
    char *argv[8];
    int index;

    if (wad_path == NULL || wad_path[0] == '\0' || frames <= 0 || frames > 300) {
        return 30;
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
    return a90_doomgeneric_presented_frames() > 0U ? 0 : 31;
}

'''
    text = text.replace("int a90_doomgeneric_native_probe_entry(void) {", smoke + "int a90_doomgeneric_native_probe_entry(void) {")
    text = text.replace(
        "marker_checksum(a90_doomgeneric_v3024_input_policy) == 0U) {",
        "marker_checksum(a90_doomgeneric_v3024_input_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3029_marker) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3029_wad_smoke_policy) == 0U) {",
    )
    text = text.replace(
        "int main(void) {\n    return a90_doomgeneric_native_probe_entry();\n}\n",
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
    )
    return text


def build_v3029_engine() -> dict[str, Any]:
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
        v3024.ADAPTER_SOURCE_TEXT = v3029_adapter_source()
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
            numeric_define("A90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES", RUNTIME_WAD_MAX_BYTES),
            numeric_define("A90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES", MAX_SMOKE_FRAMES),
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
        raise RuntimeError(f"missing V3029 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def list_cpio_entries(path: Path) -> list[str]:
    command = "cpio -it < " + shlex.quote(str(path))
    output = require_success(run(["bash", "-lc", command]), "list V3029 ramdisk cpio")
    entries = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.endswith(" blocks"):
            continue
        entries.append(stripped.lstrip("./"))
    return entries


def count_wad_entries(entries: list[str]) -> int:
    return sum(1 for entry in entries if entry.lower().endswith(".wad"))


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_sd_wad_command", {})
    markers = manifest.get("v3029_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3029 DOOMGENERIC SD WAD Command Source Build",
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
        "- Extends `a90_doomgeneric_bridge` with native `stat` + magic + SHA256 WAD verification.",
        "- Adds bounded SD-WAD command handling for `video demo doom verify --wad runtime-private --sha256 EXPECTED`.",
        "- Adds bounded SD-WAD smoke command handling for `video demo doom play [frames] --wad runtime-private --sha256 EXPECTED`.",
        "- Builds and bundles a V3029 private doomgeneric helper that accepts `--wad-smoke <path> --frames N` and runs the engine against the SD WAD.",
        "- Keeps serial control as the primary input path: `serial-doompad-to-DG_GetKey`.",
        "- Keeps sound disabled: `-nosound -nomusic`.",
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
        "## Private Engine Helper",
        "",
        f"- Bundled helper path: `{doom.get('engine_ramdisk_path')}`",
        f"- V3029 engine binary: `{doom.get('engine_binary')}`",
        f"- V3029 engine SHA256: `{doom.get('engine_binary_sha256')}`",
        f"- V3029 engine bytes: `{doom.get('engine_binary_bytes')}`",
        f"- Helper bundled in ramdisk: `{int(bool(doom.get('helper_bundled_in_ramdisk')))}`",
        f"- Helper command: `{doom.get('helper_smoke_command')}`",
        "",
        "## Command Surface",
        "",
        f"- `video demo doom verify --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}`",
        f"- `video demo doom play [frames] --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}`",
        "- `video demo doom status` remains status-only and reports SD-WAD path/hash/readiness markers.",
        "- `video demo doom engine-probe` remains a bounded no-WAD helper probe.",
        "- Menu status remains status-only; it does not launch WAD-backed gameplay.",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- No flash, serial command, Wi-Fi action, sysfs write, evdev injection, uinput, PMIC, regulator, backlight, GPIO, GDSC, or forbidden partition path is touched.",
        "- WAD/IWAD bytes are not copied into public, ramdisk, boot image, reports, or generated source.",
        "- The generated boot image and helper are private/untracked. Public output is limited to source, tests, and this metadata-only report.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata` for the next live unit.",
        "",
        "## Host Validation",
        "",
        "- `py_compile`: builder, selector, and focused tests.",
        "- `unittest`: V3029 SD-WAD command tests and selector tests.",
        "- Build: AArch64 static private doomgeneric helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3029 command, SD WAD path/hash, and bounded helper markers.",
        "- Ramdisk inventory: helper path present and WAD file count is zero.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3030`",
        "- Type: rollback-gated live validation of V3029 SD-WAD command candidate.",
        "- Scope: flash only the exact V3029 boot image through `native_init_flash.py`, health-check, run `video demo doom verify --wad runtime-private --sha256 EXPECTED` and a short bounded `video demo doom play ...`, then rollback to V2321.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-sd-wad-command-candidate`.",
    ]) + "\n"


def main() -> int:
    source = v3024.collect_source_state()
    if not source["source_exists"] or not source["git_head_matches_pin"] or not source["git_status_clean"]:
        raise RuntimeError("private doomgeneric source is not pinned and clean")
    engine = build_v3029_engine()
    configure_base()
    patch_ramdisk_with_doomgeneric_helper()
    v2859.render_report = render_report
    rc = v2859.main()
    marker_strings = require_strings(BOOT_IMAGE)
    ramdisk_entries = list_cpio_entries(RAMDISK_CPIO)
    helper_entry_present = ENGINE_RAMDISK_PATH in ramdisk_entries
    wad_count = count_wad_entries(ramdisk_entries)
    if not helper_entry_present:
        raise RuntimeError(f"missing V3029 helper entry in ramdisk: {ENGINE_RAMDISK_PATH}")
    if wad_count != 0:
        raise RuntimeError(f"unexpected WAD files in V3029 ramdisk: {wad_count}")

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-sd-wad-command-candidate",
        "parent_test_artifact": "v3028-doomgeneric-sd-wad-stage-live",
        "doomgeneric_sd_wad_command": {
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
            "default_smoke_frames": DEFAULT_SMOKE_FRAMES,
            "max_smoke_frames": MAX_SMOKE_FRAMES,
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
            "verify_command": f"video demo doom verify --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
            "play_command": f"video demo doom play {DEFAULT_SMOKE_FRAMES} --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
            "live_validation": "pending-v3030",
        },
        "v3029_engine_build": engine,
        "v3029_marker_strings": marker_strings,
        "adoption_state": "pending-sd-wad-command-live-validation",
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
    (OUT_DIR / "doomgeneric-sd-wad-command-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-sd-wad-command-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "engine_binary": rel(ENGINE_BINARY),
        "engine_binary_sha256": v3024.sha256_file(ENGINE_BINARY),
        "engine_ramdisk_path": ENGINE_REMOTE_PATH,
        "runtime_wad_path": RUNTIME_WAD_PATH,
        "expected_wad_sha256": EXPECTED_WAD_SHA256,
        "ramdisk_wad_file_count": wad_count,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-sd-wad-command-live-validation",
        "note": "V3029 bundles only the private helper and SD-WAD command metadata; WAD/IWAD bytes remain runtime-private and are not copied into public, ramdisk, or boot image.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
