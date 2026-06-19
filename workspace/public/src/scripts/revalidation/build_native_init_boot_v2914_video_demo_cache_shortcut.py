#!/usr/bin/env python3
"""Build V2914 native-init candidate with the cached video demo shortcut."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2914"
INIT_VERSION = "0.10.37"
INIT_BUILD = "v2914-video-demo-cache-shortcut"
BUILD_TAG = INIT_BUILD
DECISION = "v2914-video-demo-cache-shortcut-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2914_VIDEO_DEMO_CACHE_SHORTCUT_SOURCE_BUILD_2026-06-20.md"
BOOT_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v2914_video_demo_cache_shortcut.img", legacy_fallback=False)
INIT_BINARY = OUT_DIR / "init_v2914_video_demo_cache_shortcut"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2914_video_demo_cache_shortcut.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v465_video_demo_cache_shortcut"

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.37 (v2914-video-demo-cache-shortcut)",
    b"video.status.next_demo=video demo badapple-scale [status|verify|play] [--trust-cache]",
    b"video demo badapple-scale",
    b"video.demo.preset=%s",
    b"video.demo.asset_id=%s",
    b"video.demo.storage=sd-sha-cache",
    b"video.demo.boot_asset_policy=boot-image-carries-player-not-frames",
    b"badapple-scale",
    b"v2874-synthetic-mono1-checker-6501f",
    b"878dd867d63141eb6c9ce45a936d0454778ac91031e929b8da1c873c1c901890",
    b"video.cache.preset=%s",
    b"video.cache.preset.asset_id=%s",
    b"video.cache.preset.sha256=%s",
    b"video.cache.version=1",
    b"/mnt/sdext/a90/runtime/video/cache",
    b"video.cache.play.trust_cache=1",
    b"video.cache.verify.actual_sha256=trust-cache-not-checked",
    b"video.cache.verify.sha256_checked=0",
    b"kms-dumb-buffer-pageflip",
    b"mono1",
    b"video.stream.frames_total=",
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
        raise RuntimeError(f"missing V2914 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any], helper_flags: tuple[str, ...], init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    markers = manifest.get("v2914_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V2914 Video Demo Cache Shortcut Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback pipeline on existing KMS display.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "- Parent code unit: V2913 added `video demo badapple-scale` over the SD SHA-addressed cache preset.",
        "",
        "## Included Delta",
        "",
        "- Packages the V2913 cached-demo shortcut into a flashable test image.",
        "- Keeps multi-GB video frame data out of the boot image; the boot artifact carries only the player and command surface.",
        "- Keeps `--trust-cache` explicit; default cache playback still uses the existing full-SHA path.",
        "- Playback still uses the existing KMS dumb-buffer stream/page-flip path; no Venus, GPU, raw DSI, backlight, PMIC, PWM, regulator, GPIO, or GDSC path is added.",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Validation",
        "",
        "- `py_compile`: V2914 builder.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains the V2914 init identity, demo shortcut, SD-cache policy markers, and retained pageflip/mono1 stream markers.",
        "- Device validation is deferred to V2915: flash this exact image, run `video demo badapple-scale status|verify|play --trust-cache` against the existing SD cache, then rollback to `v2321`.",
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
        "- Generated frames, raw streams, boot images, and private caches remain private/untracked.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `video-demo-cache-shortcut-candidate`.",
        "",
    ])


def main() -> int:
    configure_base()
    v2859.render_report = render_report
    rc = v2859.main()
    marker_strings = require_strings(BOOT_IMAGE)
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "video-demo-cache-shortcut-candidate",
        "parent_test_artifact": "v2913-video-demo-cache-shortcut-host-only",
        "video_demo_cache_shortcut": {
            "version": 1,
            "source_unit": "V2914",
            "parent_unit": "V2913",
            "cache_root": "/mnt/sdext/a90/runtime/video/cache",
            "commands": [
                "video demo badapple-scale",
                "video demo badapple-scale status",
                "video demo badapple-scale verify",
                "video demo badapple-scale play --trust-cache [--frames N] [--present pageflip]",
            ],
            "large_asset_policy": "pre-rendered streams stay in the SHA-addressed SD-card cache, not inside the boot image",
            "live_validation": "pending",
        },
        "v2914_marker_strings": marker_strings,
        "adoption_state": "pending-live-validation",
        "trust_cache_contract": "requires a prior video cache verify in the validation plan; runtime path emits sha256_checked=0",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest, tuple(manifest.get("helper_flags", ())), tuple(manifest.get("init_extra_flags", ()))), encoding="utf-8")
    (OUT_DIR / "video-demo-cache-shortcut-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "video-demo-cache-shortcut-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": "V2914",
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
