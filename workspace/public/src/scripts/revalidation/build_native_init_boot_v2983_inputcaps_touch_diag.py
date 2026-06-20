#!/usr/bin/env python3
"""Build V2983 native-init candidate with expanded touch inputcaps diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2983"
INIT_VERSION = "0.10.62"
INIT_BUILD = "v2983-inputcaps-touch-diag"
BUILD_TAG = INIT_BUILD
DECISION = "v2983-inputcaps-touch-diag-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2983_INPUTCAPS_TOUCH_DIAG_SOURCE_BUILD_2026-06-20.md"
BOOT_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v2983_inputcaps_touch_diag.img", legacy_fallback=False)
INIT_BINARY = OUT_DIR / "init_v2983_inputcaps_touch_diag"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2983_inputcaps_touch_diag.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v500_inputcaps_touch_diag"

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.62 (v2983-inputcaps-touch-diag)",
    b"inputscan [eventX]",
    b"inputcaps <eventX>",
    b"readinput <eventX> [count] [timeout_ms]",
    b"inputcaps.event=",
    b"inputcaps.cap.%s=%s",
    b"inputcaps.cap.%s=<missing errno=%d>",
    b"inputcaps.decode ev_syn=",
    b"inputcaps.decode abs_x=",
    b"mt_slot=",
    b"mt_x=",
    b"mt_y=",
    b"mt_tracking_id=",
    b"power.runtime_status",
    b"power/runtime_status",
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
        raise RuntimeError(f"missing V2983 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    markers = manifest.get("v2983_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V2983 Inputcaps Touch Diagnostics Source Build",
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
        "- Expands `inputcaps <eventX>` from key-only output to read-only touch diagnostics for EV/KEY/ABS/PROP/SW capability bitmaps and runtime-PM state.",
        "- Keeps V2981 bounded `readinput <eventX> [count] [timeout_ms]` support for later event sampling.",
        "- Decodes the key touch bits needed for multitouch protocol B: `ABS_MT_SLOT`, `ABS_MT_TRACKING_ID`, `ABS_MT_POSITION_X`, `ABS_MT_POSITION_Y`, pressure/major, and `BTN_TOUCH`.",
        "- Prints read-only `/sys/class/input/<event>/device/power/*` runtime PM attributes to distinguish capability presence from a suspended/non-emitting device.",
        "- Does not open the event stream, inject input, alter keymaps, or write touch/sysfs state in this build unit.",
        "",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Static Validation",
        "",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains the V2983 identity plus expanded `inputcaps` capability/runtime-PM diagnostics strings.",
        "- Live validation is deferred to V2984: flash this exact image and run `inputcaps event6` / `inputcaps event8` plus full `inputscan`, then rollback to V2321.",
        "",
        "## Safety",
        "",
        "- Host-side source build only; no device action in V2983.",
        "- The command is read-only sysfs/capability inventory. The only runtime node action is the existing `/dev/input/event*` char-node materialization from `/sys/class/input/*/dev`.",
        "- No PMIC/backlight/GPIO/regulator/GDSC, Wi-Fi, audio route, or forbidden partition path is touched.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata` for the later live unit.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `inputcaps-touch-diagnostics-candidate`.",
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
        "candidate_type": "inputcaps-touch-diagnostics-candidate",
        "parent_test_artifact": "v2981-readinput-timeout",
        "inputcaps_touch_diagnostics": {
            "version": 1,
            "source_unit": CYCLE,
            "commands": ["inputscan", "inputcaps event6", "inputcaps event8"],
            "live_validation": "pending-v2984",
            "intent": "DOOM input prerequisite: explain touch candidate capabilities and runtime-PM state after zero-event readinput",
        },
        "v2983_marker_strings": marker_strings,
        "adoption_state": "pending-inputcaps-touch-diagnostics-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(
        manifest,
        tuple(manifest.get("helper_flags", ())),
        tuple(manifest.get("init_extra_flags", ())),
    ), encoding="utf-8")
    (OUT_DIR / "inputcaps-touch-diagnostics-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "inputcaps-touch-diagnostics-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": CYCLE,
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-inputcaps-touch-diagnostics-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
