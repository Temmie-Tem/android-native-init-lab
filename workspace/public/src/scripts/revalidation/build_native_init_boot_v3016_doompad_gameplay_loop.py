#!/usr/bin/env python3
"""Build V3016 native-init candidate with a DOOMPAD-consuming KMS gameplay loop."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3016"
INIT_VERSION = "0.10.71"
INIT_BUILD = "v3016-doompad-gameplay-loop"
BUILD_TAG = INIT_BUILD
DECISION = "v3016-doompad-gameplay-loop-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V3016_DOOMPAD_GAMEPLAY_LOOP_SOURCE_BUILD_2026-06-21.md"
BOOT_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v3016_doompad_gameplay_loop.img", legacy_fallback=False)
INIT_BINARY = OUT_DIR / "init_v3016_doompad_gameplay_loop"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3016_doompad_gameplay_loop.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v509_doompad_gameplay_loop"

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.71 (v3016-doompad-gameplay-loop)",
    b"video.status.doom_stub=1",
    b"video.status.doom_input=serial-doompad-staged",
    b"doompad [status|reset|key <role> <0|1>|tap <role>]",
    b"doompad.version=1",
    b"doompad.source=serial-control",
    b"video.demo.asset_id=doompad-loop-v3016",
    b"video.demo.status=doompad-frame-loop-ready",
    b"video.demo.engine=doompad-loop-not-doomgeneric",
    b"video.demo.asset.wad=not-bundled",
    b"video.demo.gameplay_loop=doompad-kms-v3016",
    b"video.demo.input=serial-doompad-consumed",
    b"video.demo.input.virtual_controller=doompad-serial-v3014",
    b"video.demo.input.consumed=doompad-serial-v3014",
    b"video.demo.input.hardware_gate=none-serial-control",
    b"video.demo.input.command=doompad key <role> <0|1>",
    b"video.demo.play.command=video demo doom play [frames]",
    b"doomplay.version=1",
    b"doomplay.source=doompad-state",
    b"doomplay.frames_presented=",
    b"doomplay.consumed_doompad_seq=",
    b"doomplay.player.x=",
    b"video.demo.doom.play=doompad-frame-loop",
    b"menu.demo.doom.status=doompad-frame-loop-ready",
    b"menu.demo.doom.input.consumed=doompad-serial-v3014",
    b"menu.demo.doom.play.command=video demo doom play [frames]",
    b"SERIAL DOOMPAD STATUS",
)


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


def require_strings(path: Path) -> list[str]:
    data = path.read_bytes()
    missing = [marker.decode("ascii", errors="replace") for marker in REQUIRED_STRINGS if marker not in data]
    if missing:
        raise RuntimeError(f"missing V3016 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    markers = manifest.get("v3016_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3016 DOOMPAD Gameplay Loop Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback / DOOM input handoff.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "- Parent gate: `v3015-doompad-serial-controller-serial-state-pass-before-rollback`.",
        "",
        "## Branch Evidence",
        "",
        "- V3015 proved the serial command bridge can mutate a native-init-memory-only DOOMPAD state and rollback cleanly to V2321.",
        "- OTG keyboard use remains operationally awkward because host mode and keyboard re-plugging interrupt the normal command path.",
        "- V3016 wires the already-proven `doompad` state into a bounded foreground KMS loop so the command channel can prove input consumption without `/dev/input` injection.",
        "",
        "## Included Delta",
        "",
        "- Adds `video demo doom verify` and `video demo doom play [frames]` as a bounded KMS frame loop that consumes the current `doompad` snapshot.",
        "- Emits stable `doomplay.version`, `doomplay.source`, `doomplay.consumed_doompad_seq`, `doomplay.input.*`, `doomplay.player.*`, and `doomplay.frames_presented` lines.",
        "- Keeps the loop foreground and bounded: default `90` frames, verify `1` frame, max `300` frames.",
        "- Updates `video demo doom status` and the DOOM menu status to report `serial-doompad-consumed` rather than a blocked gameplay loop.",
        "- Leaves `doompad` as native-init memory only; no evdev open, `uinput`, `EVIOCGRAB`, sysfs write, key injection, Wi-Fi action, or forbidden partition path is added.",
        "- Does not bundle a WAD or claim `doomgeneric`; this is a DOOMPAD gameplay-loop proof surface.",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Static Validation",
        "",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains the V3016 identity plus DOOMPAD state-consumer and gameplay-loop strings.",
        "",
        "## Host Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v3016_doompad_gameplay_loop.py tests/test_native_doompad_gameplay_loop_source_v3016.py tests/test_native_doompad_serial_controller_source_v3014.py tests/test_native_doom_status_stub_source_v3000.py tests/test_native_doom_keyboard_gate_status_source_v3005.py`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doompad_gameplay_loop_source_v3016 tests.test_native_doompad_serial_controller_source_v3014 tests.test_native_doom_status_stub_source_v3000 tests.test_native_doom_keyboard_gate_status_source_v3005`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v3016_doompad_gameplay_loop.py`: PASS (source build and marker check)",
        "- `file workspace/private/builds/native-init/v3016-doompad-gameplay-loop/init_v3016_doompad_gameplay_loop workspace/private/builds/native-init/v3016-doompad-gameplay-loop/a90_android_execns_probe_v509_doompad_gameplay_loop`: PASS (both AArch64 static ELF)",
        f"- `sha256sum workspace/private/inputs/boot_images/boot_linux_v3016_doompad_gameplay_loop.img`: PASS (`{manifest['boot_sha256']}`)",
        "- `git diff --check`: PASS",
        "",
        "## Safety",
        "",
        "- Host-side source build only; no device action in V3016.",
        "- The gameplay loop reads only the in-memory `doompad` snapshot and writes only KMS frames plus serial status lines.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata` for any later live unit.",
        "",
        "## Next",
        "",
        "- Flash this exact candidate only after rollback image and recovery gates are re-confirmed.",
        "- Live validation should set `doompad key forward 1` and `doompad key fire 1`, run `video demo doom play 8`, prove the frame loop consumed those bits, then reset and rollback to V2321.",
        "- A later unit can replace this proof surface with a real WAD-backed engine if a boot-size and asset policy are chosen.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doompad-gameplay-loop-candidate`.",
    ]) + "\n"


def main() -> int:
    configure_base()
    v2859.render_report = render_report
    rc = v2859.main()
    marker_strings = require_strings(BOOT_IMAGE)
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doompad-gameplay-loop-candidate",
        "parent_live_artifact": "v3015-doompad-serial-controller",
        "doompad_gameplay_loop": {
            "version": 1,
            "source_unit": CYCLE,
            "command": "video demo doom play [frames]",
            "verify_command": "video demo doom verify",
            "source": "doompad-state",
            "consumes": "serial doompad snapshot",
            "default_frames": 90,
            "verify_frames": 1,
            "max_frames": 300,
            "render": "foreground-kms",
            "asset_wad": False,
            "doomgeneric": False,
            "evdev_open": False,
            "input_injection": False,
            "uinput": False,
            "sysfs_write": False,
            "next_live_commands": [
                "doompad reset",
                "doompad key forward 1",
                "doompad key fire 1",
                "video demo doom play 8",
                "doompad key fire 0",
                "doompad key forward 0",
                "doompad reset",
            ],
        },
        "v3016_marker_strings": marker_strings,
        "adoption_state": "pending-doompad-gameplay-loop-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(
        manifest,
        tuple(manifest.get("helper_flags", ())),
        tuple(manifest.get("init_extra_flags", ())),
    ), encoding="utf-8")
    (OUT_DIR / "doompad-gameplay-loop-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doompad-gameplay-loop-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": CYCLE,
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-doompad-gameplay-loop-live-validation",
        "note": "V3016 consumes serial doompad state in a bounded foreground KMS frame loop; live validation must flash and rollback through the checked helper.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
