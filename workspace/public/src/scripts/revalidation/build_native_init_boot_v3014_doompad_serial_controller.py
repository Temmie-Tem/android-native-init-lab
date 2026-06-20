#!/usr/bin/env python3
"""Build V3014 native-init candidate with serial-controlled DOOM input state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3014"
INIT_VERSION = "0.10.70"
INIT_BUILD = "v3014-doompad-serial-controller"
BUILD_TAG = INIT_BUILD
DECISION = "v3014-doompad-serial-controller-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V3014_DOOMPAD_SERIAL_CONTROLLER_SOURCE_BUILD_2026-06-21.md"
BOOT_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v3014_doompad_serial_controller.img", legacy_fallback=False)
INIT_BINARY = OUT_DIR / "init_v3014_doompad_serial_controller"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3014_doompad_serial_controller.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v508_doompad_serial_controller"

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.70 (v3014-doompad-serial-controller)",
    b"video.status.doom_stub=1",
    b"video.status.doom_input=serial-doompad-staged",
    b"doompad [status|reset|key <role> <0|1>|tap <role>]",
    b"doompad.version=1",
    b"doompad.source=serial-control",
    b"doompad.event seq=",
    b"doompad.state seq=",
    b"video.demo.status=blocked-gameplay-loop",
    b"video.demo.input=serial-doompad-staged",
    b"video.demo.input.virtual_controller=doompad-serial-v3014",
    b"video.demo.input.hardware_gate=none-serial-control",
    b"video.demo.input.command=doompad key <role> <0|1>",
    b"menu.demo.doom.status=blocked-gameplay-loop",
    b"menu.demo.doom.input.virtual_controller=doompad-serial-v3014",
    b"menu.demo.doom.input.command=doompad key <role> <0|1>",
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
        raise RuntimeError(f"missing V3014 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    markers = manifest.get("v3014_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3014 DOOMPAD Serial Controller Source Build",
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
        "- Parent gate: `v3013-doom-precondition-stop`.",
        "",
        "## Branch Evidence",
        "",
        "- Touch-class input and physical-button mux samples previously produced zero DOOM state events.",
        "- The USB keyboard/OTG fallback was operationally awkward because it requires host/device role changes and manual keyboard re-plugging.",
        "- V3014 stages a host-serial virtual controller surface so validation can drive DOOM intent through the existing command channel without OTG hardware.",
        "",
        "## Included Delta",
        "",
        "- Adds `doompad [status|reset|key <role> <0|1>|tap <role>]` as a native-init command.",
        "- Keeps a persistent native-init-memory-only DOOM button state for `forward`, `back`, `left`, `right`, `fire`, `use`, `menu`, and `run`.",
        "- Emits stable `doompad.version`, `doompad.source`, `doompad.event`, and `doompad.state` lines for scripted validation.",
        "- Updates `video status`, `video demo doom status`, and the DOOM menu entry to point at the serial `doompad` path.",
        "- Leaves `doominput` and `doominputmux` intact as read-only evdev diagnostics and keeps USB keyboard/OTG only as a fallback note.",
        "- Adds no DOOM WAD, gameplay loop, evdev injection, uinput, sysfs write, PMIC/backlight/GPIO/regulator/GDSC path, Wi-Fi action, or forbidden partition path.",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Static Validation",
        "",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains the V3014 identity plus serial `doompad` command/status strings.",
        "",
        "## Host Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v3014_doompad_serial_controller.py tests/test_native_doompad_serial_controller_source_v3014.py tests/test_native_doom_status_stub_source_v3000.py tests/test_native_doom_keyboard_gate_status_source_v3005.py`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doompad_serial_controller_source_v3014 tests.test_native_doom_status_stub_source_v3000 tests.test_native_doom_keyboard_gate_status_source_v3005`: PASS (`16` tests)",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v3014_doompad_serial_controller.py`: PASS (source build and marker check)",
        "- `file workspace/private/builds/native-init/v3014-doompad-serial-controller/init_v3014_doompad_serial_controller workspace/private/builds/native-init/v3014-doompad-serial-controller/a90_android_execns_probe_v508_doompad_serial_controller`: PASS (both AArch64 static ELF)",
        f"- `sha256sum workspace/private/inputs/boot_images/boot_linux_v3014_doompad_serial_controller.img`: PASS (`{manifest['boot_sha256']}`)",
        "- `git diff --check`: PASS",
        "",
        "## Safety",
        "",
        "- Host-side source build only; no device action in V3014.",
        "- `doompad` mutates only native-init memory reachable through the serial shell; it does not open `/dev/input`, write sysfs, inject events, or touch storage/partition state.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata` for any later live unit.",
        "",
        "## Next",
        "",
        "- Flash this exact candidate only after rollback image and recovery gates are re-confirmed.",
        "- Live validation should run `doompad status`, a bounded key down/up sequence, `doompad reset`, `version`, `status`, and `selftest`, then rollback to V2321.",
        "- A later unit can wire the actual DOOM gameplay loop to consume this state surface.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doompad-serial-controller-candidate`.",
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
        "candidate_type": "doompad-serial-controller-candidate",
        "parent_test_artifact": "v3013-doom-precondition-stop",
        "doompad_serial_controller": {
            "version": 1,
            "source_unit": CYCLE,
            "command": "doompad [status|reset|key <role> <0|1>|tap <role>]",
            "source": "serial-control",
            "roles": ["forward", "back", "left", "right", "fire", "use", "menu", "run"],
            "mutates": "native-init-memory-only",
            "evdev_open": False,
            "input_injection": False,
            "uinput": False,
            "sysfs_write": False,
            "hardware_gate": "none-serial-control",
            "keyboard_fallback": "usb-keyboard-otg",
            "next_live_commands": [
                "doompad status",
                "doompad key forward 1",
                "doompad key fire 1",
                "doompad key fire 0",
                "doompad key forward 0",
                "doompad reset",
            ],
        },
        "v3014_marker_strings": marker_strings,
        "adoption_state": "pending-doompad-serial-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(
        manifest,
        tuple(manifest.get("helper_flags", ())),
        tuple(manifest.get("init_extra_flags", ())),
    ), encoding="utf-8")
    (OUT_DIR / "doompad-serial-controller-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doompad-serial-controller-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": CYCLE,
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-doompad-serial-live-validation",
        "note": "V3014 stages a serial-controlled in-memory DOOM input state surface; live validation must still flash and rollback through the checked helper.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
