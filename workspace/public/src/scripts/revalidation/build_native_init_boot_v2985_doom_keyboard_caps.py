#!/usr/bin/env python3
"""Build V2985 native-init candidate with DOOM keyboard fallback keycaps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2985"
INIT_VERSION = "0.10.63"
INIT_BUILD = "v2985-doom-keyboard-caps"
BUILD_TAG = INIT_BUILD
DECISION = "v2985-doom-keyboard-caps-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2985_DOOM_KEYBOARD_CAPS_SOURCE_BUILD_2026-06-20.md"
BOOT_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v2985_doom_keyboard_caps.img", legacy_fallback=False)
INIT_BINARY = OUT_DIR / "init_v2985_doom_keyboard_caps"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2985_doom_keyboard_caps.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v501_doom_keyboard_caps"

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.63 (v2985-doom-keyboard-caps)",
    b"inputscan [eventX]",
    b"inputcaps <eventX>",
    b"readinput <eventX> [count] [timeout_ms]",
    b"inputcaps.decode key_w=",
    b"key_a=",
    b"key_s=",
    b"key_d=",
    b"key_up=",
    b"key_down=",
    b"key_left=",
    b"key_right=",
    b"key_enter=",
    b"key_space=",
    b"key_esc=",
    b"key_leftctrl=",
    b"key_rightctrl=",
    b"key_leftshift=",
    b"key_rightshift=",
    b"inputcaps.decode abs_x=",
    b"power.runtime_status",
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
        raise RuntimeError(f"missing V2985 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    markers = manifest.get("v2985_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V2985 DOOM Keyboard Caps Source Build",
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
        "- Parent candidate: `v2983-inputcaps-touch-diag`.",
        "",
        "## Branch Evidence",
        "",
        "- V2984 live diagnostics proved `event6` and `event8` expose touch/MT capability bits and report `power.runtime_status=unsupported`, not `suspended`.",
        "- Repeated V2982 live runs against `event6` reached the native `readinput` timeout with `0` captured events and clean rollback.",
        "- Therefore the touch branch is not explained by missing capability or sysfs runtime-PM suspended state; the next recoverable path is the USB-keyboard fallback surface for DOOM input.",
        "",
        "## Included Delta",
        "",
        "- Extends `inputcaps <eventX>` decode output with DOOM-relevant keyboard capability bits: WASD, arrow keys, Enter, Space, Esc, Ctrl, and Shift.",
        "- Keeps `inputscan` keyboard candidate classification and bounded `readinput` sampling unchanged.",
        "- Adds no event injection, keymap changes, evdev grabs, touch configuration, or sysfs writes.",
        "- Live validation is deferred: attach a USB keyboard/OTG path, flash this exact image, run `inputscan` and `inputcaps <keyboard-event>`, then bounded `readinput <keyboard-event> ...`.",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Static Validation",
        "",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains the V2985 identity plus expanded keyboard capability strings.",
        "",
        "## Safety",
        "",
        "- Host-side source build only; no device action in V2985.",
        "- The changed command is read-only capability inventory from `/sys/class/input/<event>/device/capabilities/*`.",
        "- No PMIC/backlight/GPIO/regulator/GDSC, Wi-Fi, audio route, video playback, or forbidden partition path is touched.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata` for the later live unit.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doom-keyboard-fallback-caps-candidate`.",
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
        "candidate_type": "doom-keyboard-fallback-caps-candidate",
        "parent_test_artifact": "v2983-inputcaps-touch-diag",
        "doom_keyboard_caps": {
            "version": 1,
            "source_unit": CYCLE,
            "commands": ["inputscan", "inputcaps <keyboard-event>", "readinput <keyboard-event> <count> <timeout_ms>"],
            "live_validation": "pending-usb-keyboard-candidate",
            "intent": "DOOM input prerequisite: pivot from non-emitting touch event to USB-keyboard fallback capability validation",
            "keys": [
                "KEY_W",
                "KEY_A",
                "KEY_S",
                "KEY_D",
                "KEY_UP",
                "KEY_DOWN",
                "KEY_LEFT",
                "KEY_RIGHT",
                "KEY_ENTER",
                "KEY_SPACE",
                "KEY_ESC",
                "KEY_LEFTCTRL",
                "KEY_RIGHTCTRL",
                "KEY_LEFTSHIFT",
                "KEY_RIGHTSHIFT",
            ],
        },
        "v2985_marker_strings": marker_strings,
        "adoption_state": "pending-usb-keyboard-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(
        manifest,
        tuple(manifest.get("helper_flags", ())),
        tuple(manifest.get("init_extra_flags", ())),
    ), encoding="utf-8")
    (OUT_DIR / "doom-keyboard-fallback-caps-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doom-keyboard-fallback-caps-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": CYCLE,
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-usb-keyboard-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
