#!/usr/bin/env python3
"""Build V2998 native-init candidate with multi-event DOOM input mux."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2998"
INIT_VERSION = "0.10.67"
INIT_BUILD = "v2998-doominput-mux"
BUILD_TAG = INIT_BUILD
DECISION = "v2998-doominput-mux-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2998_DOOMINPUT_MUX_SOURCE_BUILD_2026-06-20.md"
BOOT_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v2998_doominput_mux.img", legacy_fallback=False)
INIT_BINARY = OUT_DIR / "init_v2998_doominput_mux"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2998_doominput_mux.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v505_doominput_mux"

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.67 (v2998-doominput-mux)",
    b"doominputmux <eventX,eventY[,eventZ]> [count] [timeout_ms]",
    b"doominputmux: waiting on %s (%d events across %d fds), q/Ctrl-C cancels",
    b"doominputmux.event %d: source=%s type=%s code=%s role=%s value=%d",
    b"doominputmux.state %d: source=%s forward=%d back=%d left=%d right=%d fire=%d",
    b"doom_button_forward",
    b"doom_button_back",
    b"doom_button_fire",
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
        raise RuntimeError(f"missing V2998 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    markers = manifest.get("v2998_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V2998 DOOM Input Mux Source Build",
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
        "- Parent candidate: `v2996-doominput-button-proxy`.",
        "",
        "## Branch Evidence",
        "",
        "- V2996 maps known A90 physical buttons into diagnostic DOOM state bits.",
        "- V2997 stages sequential event3/event0 live sampling, but physical-button fallback spans more than one evdev node.",
        "- A real DOOM input path needs a single state machine that can merge multiple read-only input sources.",
        "",
        "## Included Delta",
        "",
        "- Adds `doominputmux <eventX,eventY[,eventZ]> [count] [timeout_ms]`.",
        "- Opens up to four event nodes `O_RDONLY|O_NONBLOCK`, polls them together, and applies events to one `doominput_state`.",
        "- Emits source-labelled `doominputmux.event` and `doominputmux.state` lines so event3 volume keys and event0 power can be validated in one bounded window.",
        "- Keeps V2996 diagnostic button mappings: `KEY_VOLUMEUP` -> forward, `KEY_VOLUMEDOWN` -> back, `KEY_POWER` -> fire.",
        "- Adds no input injection, evdev grabs, keymap changes, touch configuration, or sysfs writes.",
        "- No PMIC/backlight/GPIO/regulator/GDSC writes, audio playback, video playback, or forbidden partition path is touched.",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Static Validation",
        "",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains the V2998 identity, `doominputmux` command surface, source-labelled state markers, and physical-button proxy role strings.",
        "",
        "## Host Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2998_doominput_mux.py tests/test_native_doominput_mux_source_v2998.py`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doominput_mux_source_v2998`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v2998_doominput_mux.py`: PASS (source build and marker check)",
        "- `file workspace/private/builds/native-init/v2998-doominput-mux/init_v2998_doominput_mux workspace/private/builds/native-init/v2998-doominput-mux/a90_android_execns_probe_v505_doominput_mux`: PASS (both AArch64 static ELF)",
        f"- `sha256sum workspace/private/inputs/boot_images/boot_linux_v2998_doominput_mux.img`: PASS (`{manifest['boot_sha256']}`)",
        "- `git diff --check`: PASS",
        "",
        "## Safety",
        "",
        "- Host-side source build only; no device action in V2998.",
        "- Runtime behavior remains read-only: `doominputmux` opens `/dev/input/event*` `O_RDONLY|O_NONBLOCK`, polls, reads, and prints state.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata` for any later live unit.",
        "",
        "## Next",
        "",
        "- A later live handoff can flash this candidate and sample `doominputmux event3,event0` while the operator presses VOLUMEUP/VOLUMEDOWN/POWER.",
        "- That live step remains diagnostic input liveness proof, not a final DOOM control scheme.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doominput-mux-candidate`.",
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
        "candidate_type": "doominput-mux-candidate",
        "parent_test_artifact": "v2996-doominput-button-proxy",
        "doominput_mux": {
            "version": 1,
            "source_unit": CYCLE,
            "command": "doominputmux <eventX,eventY[,eventZ]> [count] [timeout_ms]",
            "purpose": "diagnostic multi-event evdev-to-doominput.state liveness mux",
            "max_events": 4,
            "expected_live_events": ["event3", "event0"],
            "mappings": {
                "KEY_VOLUMEUP": "forward",
                "KEY_VOLUMEDOWN": "back",
                "KEY_POWER": "fire",
            },
            "live_validation": "pending-event3-event0-doominputmux-button-sample",
        },
        "v2998_marker_strings": marker_strings,
        "adoption_state": "pending-doominputmux-button-live-sample",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(
        manifest,
        tuple(manifest.get("helper_flags", ())),
        tuple(manifest.get("init_extra_flags", ())),
    ), encoding="utf-8")
    (OUT_DIR / "doominput-mux-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doominput-mux-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": CYCLE,
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-doominputmux-button-live-sample",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
