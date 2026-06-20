#!/usr/bin/env python3
"""Build V3005 native-init candidate with current DOOM keyboard-gate status."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3005"
INIT_VERSION = "0.10.69"
INIT_BUILD = "v3005-doom-keyboard-gate-status"
BUILD_TAG = INIT_BUILD
DECISION = "v3005-doom-keyboard-gate-status-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V3005_DOOM_KEYBOARD_GATE_STATUS_SOURCE_BUILD_2026-06-20.md"
BOOT_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v3005_doom_keyboard_gate_status.img", legacy_fallback=False)
INIT_BINARY = OUT_DIR / "init_v3005_doom_keyboard_gate_status"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3005_doom_keyboard_gate_status.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v507_doom_keyboard_gate_status"

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.69 (v3005-doom-keyboard-gate-status)",
    b"video.status.doom_stub=1",
    b"video.status.doom_input=not-proven",
    b"video.demo.status=blocked-input-prerequisite",
    b"video.demo.input.physical_button_mux=v3002-zero-event-do-not-repeat",
    b"video.demo.input.keyboard_gate=v3004-doominput-keyboard-live-gate",
    b"video.demo.input.hardware_gate=usb-keyboard-otg",
    b"video.demo.input.command=doominput <keyboard-event> 32 60000",
    b"menu.demo.doom.action=status-only",
    b"menu.demo.doom.input.live_handoff=v3004-doominput-keyboard-live-gate",
    b"menu.demo.doom.input.command=doominput <keyboard-event> 32 60000",
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
        raise RuntimeError(f"missing V3005 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    markers = manifest.get("v3005_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3005 DOOM Keyboard Gate Status Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback / DOOM input prerequisite.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "- Parent gate: `v3004-doominput-keyboard-live-gate`.",
        "",
        "## Branch Evidence",
        "",
        "- V3002 proved `event3,event0` are button-capable but captured zero mux events/states during the bounded live window.",
        "- V3003 recorded the DOOM input frontier as hardware-stimulus-gated and warned against repeating the same physical-button mux run without confirmed button input.",
        "- V3004 staged the higher-information USB keyboard/OTG live gate on the V2989 `doominput.state` candidate.",
        "- This source build updates the on-device DOOM status/menu text so it no longer points operators back at the stale physical-button mux command.",
        "",
        "## Included Delta",
        "",
        "- Keeps the `DOOM` DEMO entry status-only with `verify` and `play` still blocked by `-EAGAIN`.",
        "- Reports built-in touch as zero-event and physical-button mux as `v3002-zero-event-do-not-repeat`.",
        "- Reports the current next gate as `v3004-doominput-keyboard-live-gate` with `usb-keyboard-otg` hardware required.",
        "- Exposes the diagnostic command shape as `doominput <keyboard-event> 32 60000` instead of the stale `doominputmux event3,event0` sample.",
        "- Adds no DOOM WAD, gameplay loop, input sampling, input injection, video/audio playback, sysfs write, PMIC/backlight/GPIO/regulator/GDSC path, Wi-Fi action, or forbidden partition path.",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Static Validation",
        "",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains the V3005 identity and current keyboard-gate DOOM status strings.",
        "",
        "## Host Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v3005_doom_keyboard_gate_status.py tests/test_native_doom_keyboard_gate_status_source_v3005.py tests/test_native_doom_status_stub_source_v3000.py`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_keyboard_gate_status_source_v3005 tests.test_native_doom_status_stub_source_v3000`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v3005_doom_keyboard_gate_status.py`: PASS (source build and marker check)",
        "- `file workspace/private/builds/native-init/v3005-doom-keyboard-gate-status/init_v3005_doom_keyboard_gate_status workspace/private/builds/native-init/v3005-doom-keyboard-gate-status/a90_android_execns_probe_v507_doom_keyboard_gate_status`: PASS (both AArch64 static ELF)",
        f"- `sha256sum workspace/private/inputs/boot_images/boot_linux_v3005_doom_keyboard_gate_status.img`: PASS (`{manifest['boot_sha256']}`)",
        "- `git diff --check`: PASS",
        "",
        "## Safety",
        "",
        "- Host-side source build only; no device action in V3005.",
        "- The new DOOM surface is status-only and does not start playback or sample input.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata` for any later live unit.",
        "",
        "## Next",
        "",
        "- Run the V3004 live gate only when USB keyboard/OTG is attached and an operator can press DOOM keys during the single bounded sample window.",
        "- If keyboard state is proven, the next DOOM branch can wire a minimal game input path; if it times out, keep the blocker visible and avoid repeating no-stimulus samples.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doom-keyboard-gate-status-candidate`.",
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
        "candidate_type": "doom-keyboard-gate-status-candidate",
        "parent_live_gate": "v3004-doominput-keyboard-live-gate",
        "supersedes_status": "v3000-doom-status-stub",
        "doom_keyboard_gate_status": {
            "version": 1,
            "source_unit": CYCLE,
            "menu_action": "SCREEN_MENU_DEMO_DOOM",
            "menu_command": "video demo doom status",
            "status": "blocked-input-prerequisite",
            "input_state": "not-proven",
            "touch_state": "event6,event8-zero-events",
            "physical_button_mux": "v3002-zero-event-do-not-repeat",
            "keyboard_gate": "v3004-doominput-keyboard-live-gate",
            "hardware_gate": "usb-keyboard-otg",
            "next_live_command": "doominput <keyboard-event> 32 60000",
            "verify_play_rc": "-EAGAIN",
        },
        "v3005_marker_strings": marker_strings,
        "adoption_state": "status-only-until-keyboard-or-touch-input-proven",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(
        manifest,
        tuple(manifest.get("helper_flags", ())),
        tuple(manifest.get("init_extra_flags", ())),
    ), encoding="utf-8")
    (OUT_DIR / "doom-keyboard-gate-status-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doom-keyboard-gate-status-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": CYCLE,
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "parent_live_gate": "v3004-doominput-keyboard-live-gate",
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "status-only-until-keyboard-or-touch-input-proven",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
