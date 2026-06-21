#!/usr/bin/env python3
"""Build V3025 native-init doomgeneric command/boot bridge candidate.

V3025 wires the V3024 private doomgeneric engine link into a native-init
command surface and boot candidate. It bundles the private engine helper in the
private ramdisk, but WAD/IWAD bytes remain runtime-private and are not copied
into public, ramdisk, or boot image.
"""

from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
import native_doomgeneric_engine_integration_build_v3024 as v3024
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3025"
INIT_VERSION = "0.10.73"
INIT_BUILD = "v3025-doomgeneric-command-bridge"
BUILD_TAG = INIT_BUILD
DECISION = "v3025-doomgeneric-command-bridge-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3025_DOOMGENERIC_COMMAND_BRIDGE_SOURCE_BUILD_2026-06-21.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3025_doomgeneric_command_bridge.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3025_doomgeneric_command_bridge"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3025_doomgeneric_command_bridge.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v510_doomgeneric_command_bridge"

ENGINE_BINARY = v3024.ENGINE_BINARY
ENGINE_EXPECTED_SHA256 = "8b6630498b7ff217e6ad9b27593f89644ba73eb7cbbf11361838972f15581735"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3024"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
RUNTIME_WAD_ROOT = v3024.RUNTIME_WAD_ROOT

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.73 (v3025-doomgeneric-command-bridge)",
    b"v3025-doomgeneric-command-bridge",
    b"doomgeneric-private-link-v3025",
    b"/bin/a90_doomgeneric_private_engine_v3024",
    b"/cache/a90-runtime/pkg/doom/v3024/",
    b"serial-doompad-to-DG_GetKey",
    b"disabled-nosound-nomusic",
    b"video demo doom engine-probe",
    b"video.demo.engine.helper.present=%d",
    b"video.demo.asset.wad.embedded_in_boot=%d",
    b"video.demo.input.otg_required=0",
    b"a90.doomgeneric.v3024.private_source_integration=1",
    b"a90.doomgeneric.v3024.wad_policy=runtime-private-not-boot",
    b"a90.doomgeneric.v3024.input=serial-doompad-to-DG_GetKey",
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def run(argv: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd) if cwd is not None else str(REPO_ROOT),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def require_success(result: subprocess.CompletedProcess[str], description: str) -> str:
    if result.returncode != 0:
        raise RuntimeError(f"{description} failed rc={result.returncode}\n{result.stdout}")
    return result.stdout


def shell_define(name: str, value: str) -> str:
    return f'-D{name}="{value}"'


def ensure_v3024_engine_artifact() -> dict[str, Any]:
    if not ENGINE_BINARY.exists() or v3024.sha256_file(ENGINE_BINARY) != ENGINE_EXPECTED_SHA256:
        state = v3024.collect_state(build=True)
        if not state.get("safe_to_continue_host_only"):
            raise RuntimeError("V3024 private engine build did not pass safety gates")
    engine_sha = v3024.sha256_file(ENGINE_BINARY)
    if engine_sha != ENGINE_EXPECTED_SHA256:
        raise RuntimeError(
            f"unexpected V3024 private engine SHA256: {engine_sha}; expected {ENGINE_EXPECTED_SHA256}"
        )
    return {
        "engine_binary": rel(ENGINE_BINARY),
        "engine_binary_sha256": engine_sha,
        "engine_binary_bytes": ENGINE_BINARY.stat().st_size,
        "engine_ramdisk_path": ENGINE_REMOTE_PATH,
    }


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
            shell_define("A90_DOOMGENERIC_BRIDGE_HELPER_PATH", ENGINE_REMOTE_PATH),
            shell_define("A90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT", RUNTIME_WAD_ROOT),
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
        raise RuntimeError(f"missing V3025 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def list_cpio_entries(path: Path) -> list[str]:
    command = "cpio -it < " + shlex.quote(str(path))
    output = require_success(run(["bash", "-lc", command]), "list V3025 ramdisk cpio")
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
    doom = manifest.get("doomgeneric_command_bridge", {})
    markers = manifest.get("v3025_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3025 DOOMGENERIC Command Bridge Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback / DOOM capstone.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Adds the `a90_doomgeneric_bridge` native-init module and `video demo doom engine-probe` command surface.",
        "- Bundles the V3024 private doomgeneric engine probe helper into the private ramdisk as a boot candidate helper.",
        "- Keeps serial control as the primary input path: `serial-doompad-to-DG_GetKey`.",
        "- Keeps sound disabled for the first bridge candidate: `-nosound -nomusic`.",
        "- Keeps WAD/IWAD bytes out of public, ramdisk, and boot image; the command surface records only the runtime-private WAD root.",
        "",
        "## Private Engine Helper",
        "",
        f"- Bundled helper path: `{doom.get('engine_ramdisk_path')}`",
        f"- V3024 engine binary: `{doom.get('engine_binary')}`",
        f"- V3024 engine SHA256: `{doom.get('engine_binary_sha256')}`",
        f"- V3024 engine bytes: `{doom.get('engine_binary_bytes')}`",
        f"- Helper bundled in ramdisk: `{int(bool(doom.get('helper_bundled_in_ramdisk')))}`",
        f"- WAD files in ramdisk: `{doom.get('ramdisk_wad_file_count')}`",
        f"- Runtime WAD root: `{doom.get('runtime_wad_root')}`",
        "",
        "## Command Surface",
        "",
        "- `video status`: reports `video.status.doomgeneric.*` helper, input, and WAD embedding markers.",
        "- `video demo doom status`: retains legacy doompad-loop markers and adds `video.demo.engine.active` / helper state.",
        "- `video demo doom engine-probe`: runs the V3024 helper with a bounded 3000 ms timeout and reports `video.demo.doom.engine_probe.rc`.",
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
        "- The generated boot image is private/untracked. Public output is limited to source, tests, and this metadata-only report.",
        "- WAD/IWAD bytes are not copied; full gameplay remains blocked on a later runtime-private WAD staging/live-validation unit.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Host Validation",
        "",
        "- `py_compile`: builder, selector, and focused tests.",
        "- `unittest`: V3025 command bridge tests and selector tests.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack with V3024 private engine helper, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3025 command bridge markers plus V3024 private engine bridge markers.",
        "- Ramdisk inventory: helper path present and WAD file count is zero.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3026`",
        "- Type: rollback-gated live validation of V3025 command bridge.",
        "- Scope: flash only the exact V3025 boot image through `native_init_flash.py`, health-check, run `video demo doom status` and `video demo doom engine-probe`, then rollback to V2321.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-command-bridge-candidate`.",
    ]) + "\n"


def main() -> int:
    engine = ensure_v3024_engine_artifact()
    configure_base()
    patch_ramdisk_with_doomgeneric_helper()
    v2859.render_report = render_report
    rc = v2859.main()
    marker_strings = require_strings(BOOT_IMAGE)
    ramdisk_entries = list_cpio_entries(RAMDISK_CPIO)
    helper_entry_present = ENGINE_RAMDISK_PATH in ramdisk_entries
    wad_count = count_wad_entries(ramdisk_entries)
    if not helper_entry_present:
        raise RuntimeError(f"missing V3025 helper entry in ramdisk: {ENGINE_RAMDISK_PATH}")
    if wad_count != 0:
        raise RuntimeError(f"unexpected WAD files in V3025 ramdisk: {wad_count}")

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-command-bridge-candidate",
        "parent_test_artifact": "v3024-doomgeneric-private-integration",
        "doomgeneric_command_bridge": {
            "version": 1,
            **engine,
            "runtime_wad_root": RUNTIME_WAD_ROOT,
            "helper_bundled_in_ramdisk": helper_entry_present,
            "ramdisk_wad_file_count": wad_count,
            "public_wad_file_count": v3024.count_files(v3024.PUBLIC_WAD_ROOT, ".wad")["count"],
            "input_path": "serial-doompad-to-DG_GetKey",
            "otg_required": False,
            "evdev_injection": False,
            "uinput": False,
            "sound_mode": "disabled-nosound-nomusic",
            "engine_probe_command": "video demo doom engine-probe",
            "live_validation": "pending-v3026",
        },
        "v3025_marker_strings": marker_strings,
        "adoption_state": "pending-command-bridge-live-validation",
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
    (OUT_DIR / "doomgeneric-command-bridge-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-command-bridge-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "engine_binary": engine["engine_binary"],
        "engine_binary_sha256": engine["engine_binary_sha256"],
        "engine_ramdisk_path": ENGINE_REMOTE_PATH,
        "runtime_wad_root": RUNTIME_WAD_ROOT,
        "ramdisk_wad_file_count": wad_count,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-command-bridge-live-validation",
        "note": "V3025 bundles only the private V3024 engine probe helper; WAD/IWAD bytes remain runtime-private and must not be copied into public, ramdisk, or boot image.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
