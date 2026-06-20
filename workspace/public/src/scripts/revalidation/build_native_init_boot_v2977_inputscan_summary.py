#!/usr/bin/env python3
"""Build V2977 native-init candidate with read-only inputscan inventory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2977"
INIT_VERSION = "0.10.60"
INIT_BUILD = "v2977-inputscan-summary"
BUILD_TAG = INIT_BUILD
DECISION = "v2977-inputscan-summary-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2977_INPUTSCAN_SUMMARY_SOURCE_BUILD_2026-06-20.md"
BOOT_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v2977_inputscan_summary.img", legacy_fallback=False)
INIT_BINARY = OUT_DIR / "init_v2977_inputscan_summary"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2977_inputscan_summary.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v499_inputscan_summary"

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.60 (v2977-inputscan-summary)",
    b"inputscan [eventX]",
    b"inputscan.summary events=",
    b"touch_candidates=",
    b"keyboard_candidates=",
    b"button_candidates=",
    b"btn_touch=",
    b"mt_xy=",
    b"key_wasd=",
    b"key_enter_space_esc=",
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
        raise RuntimeError(f"missing V2977 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    markers = manifest.get("v2977_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V2977 Inputscan Summary Source Build",
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
        "",
        "## Included Delta",
        "",
        "- Adds `inputscan [eventX]`, a read-only evdev inventory command for the DOOM input prerequisite.",
        "- Enumerates `/sys/class/input/event*`, materializes existing `/dev/input/event*` char nodes through the existing helper path, and prints each event name/dev/node.",
        "- Classifies touch candidates from `EV_ABS` plus `BTN_TOUCH`, `ABS_X/Y`, or `ABS_MT_POSITION_X/Y`.",
        "- Classifies keyboard fallback candidates from `EV_KEY` plus WASD/Enter/Space/Esc capability bits.",
        "- Classifies physical-button candidates from power/volume key capability bits.",
        "- Does not read event streams, block for input, inject input, alter keymaps, or touch display/audio/network state.",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Static Validation",
        "",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains the V2977 identity and `inputscan` summary/classification strings.",
        "- Live validation is deferred to V2978: flash this exact image, run `inputscan`, and if a touch candidate appears run a bounded `readinput <event> 1` human-touch sample.",
        "",
        "## Safety",
        "",
        "- Host-side source build only; no device action in V2977.",
        "- The command is read-only sysfs/capability inventory. The only runtime node action is the existing `/dev/input/event*` char-node materialization from `/sys/class/input/*/dev`.",
        "- No PMIC/backlight/GPIO/regulator/GDSC, Wi-Fi, audio route, or forbidden partition path is touched.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata` for the later live unit.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `inputscan-summary-candidate`.",
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
        "candidate_type": "inputscan-summary-candidate",
        "parent_test_artifact": "v2974-nyan-real-preset",
        "inputscan_summary": {
            "version": 1,
            "source_unit": CYCLE,
            "command": "inputscan [eventX]",
            "live_validation": "pending-v2978",
            "intent": "DOOM input prerequisite: identify touch or keyboard candidates from evdev capabilities",
        },
        "v2977_marker_strings": marker_strings,
        "adoption_state": "pending-inputscan-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(
        manifest,
        tuple(manifest.get("helper_flags", ())),
        tuple(manifest.get("init_extra_flags", ())),
    ), encoding="utf-8")
    (OUT_DIR / "inputscan-summary-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "inputscan-summary-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": CYCLE,
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-inputscan-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
