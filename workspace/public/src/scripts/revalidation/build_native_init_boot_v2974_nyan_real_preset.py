#!/usr/bin/env python3
"""Build V2974 native-init candidate with real Nyan cache preset/menu preview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2974"
INIT_VERSION = "0.10.59"
INIT_BUILD = "v2974-nyan-real-preset"
BUILD_TAG = INIT_BUILD
DECISION = "v2974-nyan-real-preset-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2974_NYAN_REAL_PRESET_SOURCE_BUILD_2026-06-20.md"
BOOT_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v2974_nyan_real_preset.img", legacy_fallback=False)
INIT_BINARY = OUT_DIR / "init_v2974_nyan_real_preset"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2974_nyan_real_preset.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v498_nyan_real_preset"

NYAN_STREAM_SHA256 = "9a8d91956218acf674b7d99d421467effec442fdde1dbbea8635b8f47085c573"
NYAN_AUDIO_SHA256 = "4c3774553195c04166a3a83de793253696a5bee60afe83a04219419fc28e43de"
NYAN_ASSET_ID = "nyancat-v2973-pal8-rle-preview"
NYAN_AUDIO_PATH = "/cache/a90-runtime/pkg/av/v2973/audio/nyancat.s16le"

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.59 (v2974-nyan-real-preset)",
    b"video.status.version=9",
    b"video.status.nyan_pal8_rle=1",
    b"video cache preset [badapple|badapple-scale|nyan]",
    b"video demo [badapple|badapple-scale|nyan]",
    b"nyancat-v2973-pal8-rle-preview",
    b"9a8d91956218acf674b7d99d421467effec442fdde1dbbea8635b8f47085c573",
    b"DEMO / NYAN CAT",
    b"NYAN CAT",
    b"menu.demo.nyan.action=play-av-preview",
    b"menu.demo.nyan.frames=300",
    b"menu.demo.nyan.audio_duration_ms=10000",
    b"menu.demo.nyan.audio_pcm=/cache/a90-runtime/pkg/av/v2973/audio/nyancat.s16le",
    b"menu.demo.nyan.audio_pcm_gain_milli=780",
    b"menu.demo.nyan.video_present=setcrtc",
    b"pal8-rle",
    b"A90VSTR2",
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
        raise RuntimeError(f"missing V2974 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    markers = manifest.get("v2974_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    return "\n".join([
        "# Native Init V2974 Nyan Real Preset Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback pipeline / Nyan Cat compact color demo.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Bumps `video.status.version` to `9` for the expanded Nyan command/menu surface.",
        "- Adds the content-addressed `video cache preset nyan` mapping to the V2973 private `A90VSTR2 pal8-rle` preview stream.",
        "- Adds `video demo nyan` by reusing the existing SHA-addressed cache preset wrapper and Player HUD layout.",
        "- Adds `DEMO > NYAN CAT` as a bounded 300-frame / 10 s A/V preview entry with low-amplitude PCM playback.",
        "- Keeps Bad Apple presets and the existing `A90VSTR2 pal8-rle` decoder path intact.",
        "- Does not add GPU, Venus, raw DSI, backlight, PMIC, PWM, regulator, GPIO, GDSC, or telemetry write paths.",
        "",
        "## Asset Contract",
        "",
        f"- Nyan asset ID: `{NYAN_ASSET_ID}`",
        f"- Nyan stream SHA256: `{NYAN_STREAM_SHA256}`",
        f"- Nyan audio SHA256: `{NYAN_AUDIO_SHA256}`",
        f"- Nyan audio runtime path: `{NYAN_AUDIO_PATH}`",
        "- Media bytes remain private/untracked; this image carries only the player and SHA/path contract.",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Static Validation",
        "",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V2974 identity, Nyan preset SHA/asset ID, menu action markers, `A90VSTR2`, and `pal8-rle` strings.",
        "- Device validation is deferred to V2975: flash this exact image, seed the V2973 private stream+PCM to SD/runtime cache, run `video demo nyan status|verify|play`, then health-check/rollback.",
        "",
        "## Bundled Runtime Metadata",
        "",
        f"- Bundled audio artifact count: `{bundled.get('artifact_count')}`",
        f"- Replay entry count: `{bundled.get('replay_entry_count')}`",
        f"- Native manifest SHA256: `{bundled.get('native_manifest_sha256')}`",
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- Generated streams, PCM, boot images, and private caches remain private/untracked.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `nyan-real-preset-candidate`.",
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
        "candidate_type": "nyan-real-preset-candidate",
        "parent_test_artifact": "v2972-nyan-pal8-rle-synthetic",
        "nyan_real_preset": {
            "version": 1,
            "source_unit": "V2974",
            "asset_id": NYAN_ASSET_ID,
            "stream_sha256": NYAN_STREAM_SHA256,
            "audio_sha256": NYAN_AUDIO_SHA256,
            "audio_runtime_path": NYAN_AUDIO_PATH,
            "frame_count": 300,
            "duration_ms": 10000,
            "live_validation": "pending-v2975",
        },
        "v2974_marker_strings": marker_strings,
        "adoption_state": "pending-real-nyan-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest, tuple(manifest.get("helper_flags", ())), tuple(manifest.get("init_extra_flags", ()))), encoding="utf-8")
    (OUT_DIR / "nyan-real-preset-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "nyan-real-preset-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": "V2974",
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "asset_id": NYAN_ASSET_ID,
        "stream_sha256": NYAN_STREAM_SHA256,
        "audio_sha256": NYAN_AUDIO_SHA256,
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-real-nyan-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
