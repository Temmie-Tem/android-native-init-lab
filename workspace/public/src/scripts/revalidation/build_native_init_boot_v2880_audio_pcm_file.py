#!/usr/bin/env python3
"""Build V2880 native-init candidate with bounded audio PCM-file playback.

V2880 keeps the V2878 page-flip video stream path and adds an optional
`audio play --pcm-file PATH` source for future A/V bundles. The default tone/chime
path remains unchanged. The PCM-file source is restricted to /cache/a90-runtime,
opened with O_NOFOLLOW, size-checked for the requested duration, and scanned for
peak amplitude before any ALSA write.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2880"
INIT_VERSION = "0.10.26"
INIT_BUILD = "v2880-audio-pcm-file"
BUILD_TAG = INIT_BUILD
DECISION = "v2880-audio-pcm-file-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2880_AUDIO_PCM_FILE_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2880_audio_pcm_file.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2880_audio_pcm_file"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2880_audio_pcm_file.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v456_audio_pcm_file"

REQUIRED_STRINGS = (
    b"audio.play.pcm_file_supported=1",
    b"audio.play.pcm_file.path_allowed=",
    b"audio.play.pcm_file.validated=1",
    b"audio.play.pcm_file.amplitude_within_cap=",
    b"audio.play.execute.source=",
    b"audio.play.execute.plan.source=",
    b"audio.play.execute.plan.pcm_file=",
    b"--pcm-file PATH",
    b"kms-dumb-buffer-pageflip",
)


def configure_base_for_v2880() -> None:
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
        raise RuntimeError(f"missing V2880 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    video = manifest.get("video_command_surface", {}) if isinstance(manifest.get("video_command_surface"), dict) else {}
    marker_strings = manifest.get("v2880_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in marker_strings] if isinstance(marker_strings, list) else []
    return "\n".join([
        "# Native Init V2880 Audio PCM-File Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback pipeline; this unit adds the missing PCM-file audio source needed for A/V bundles.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "- Parent validated state: V2879 live-proved raw-stride frame streaming with DRM page-flip events.",
        "",
        "## Included Delta",
        "",
        "- Adds optional `audio play ... --pcm-file PATH` while keeping the default generated-tone/chime path unchanged.",
        "- Restricts PCM-file sources to `/cache/a90-runtime`, rejects `..`, and opens the file with `O_NOFOLLOW`.",
        "- Before any ALSA write, checks that the file is regular, large enough for the requested duration, seekable, and peak amplitude is within the profile cap.",
        "- Streams bounded S16LE stereo chunks from the validated file through the existing integrated ADSP/snd/app-type/SET-cal/route/PCM path.",
        "- Keeps the V2878/V2879 KMS page-flip video stream command surface intact for the next A/V sync unit.",
        "",
        "## Audio PCM-File Contract",
        "",
        "- Command shape: `audio play internal-speaker-safe --mode listen --duration-ms N --amplitude-milli M --pcm-file /cache/a90-runtime/pkg/.../audio.s16le --execute`.",
        "- File format: raw interleaved S16LE matching the active speaker profile: 48 kHz, stereo, 16-bit.",
        "- Duration remains bounded by the existing profile duration cap; amplitude remains bounded by a pre-write peak scan.",
        "- Raw PCM files are private runtime artifacts and are not committed.",
        "",
        "## Retained Video Metadata",
        "",
        f"- Version: `{video.get('version')}`",
        f"- Commands: `{', '.join(video.get('commands', [])) if isinstance(video.get('commands'), list) else video.get('commands')}`",
        f"- Safety boundary: `{video.get('safety_boundary')}`",
        "- Page-flip stream path marker retained: `kms-dumb-buffer-pageflip`.",
        "",
        "## Bundled Runtime Metadata",
        "",
        f"- Bundled audio artifact count: `{bundled.get('artifact_count')}`",
        f"- Replay entry count: `{bundled.get('replay_entry_count')}`",
        f"- Native manifest SHA256: `{bundled.get('native_manifest_sha256')}`",
        "- Raw SET-cal bytes remain private; this report records only counts and hashes.",
        "",
        "## Static Validation",
        "",
        "- `py_compile`: V2880 builder.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V2880 PCM-file and retained page-flip markers.",
        *marker_lines,
        "- `file`: native-init and helper are AArch64 statically linked executables.",
        "- Device validation is deferred to the next V-iteration: flash this exact image, install a bounded private PCM fixture, run dry-run/execute, then rollback to `v2321`.",
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- This unit adds no Venus, GPU/KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path.",
        "- PCM-file execution remains bounded by existing audio caps and pre-write amplitude scanning.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `audio-pcm-file-candidate`.",
        "",
    ])


def main() -> int:
    configure_base_for_v2880()
    v2859.render_report = render_report
    rc = v2859.main()

    marker_strings = require_strings(BOOT_IMAGE)
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-pcm-file-candidate",
        "parent_test_artifact": "v2878-video-stream-pageflip",
        "audio_pcm_file_source": {
            "version": 1,
            "source_unit": "V2880",
            "allowed_prefix": "/cache/a90-runtime",
            "format": "s16le-stereo-48000",
            "path_policy": "absolute-no-dotdot-runtime-prefix-open-nofollow",
            "safety": "regular-file-size-check-peak-amplitude-scan-before-alsa-write",
            "live_validation": "pending",
        },
        "video_command_surface": {
            "version": 6,
            "source_unit": "V2880",
            "inventory_unit": "V2864",
            "plan_unit": "V2870",
            "commands": [
                "video",
                "video status",
                "video frame",
                "video demo",
                "video anim",
                "video blitbench",
                "video flipprobe",
                "video stream",
            ],
            "stream_format": "A90VSTR1 xbgr8888-raw-stride",
            "stream_present_modes": ["setcrtc", "pageflip"],
            "default_stream_present_mode": "setcrtc",
            "pageflip_stream_status": "live-validated-v2879",
            "render_path": "kms-dumb-buffer",
            "flip_path": "kms-dumb-buffer-pageflip",
            "pixel_format": "xbgr8888",
            "safety_boundary": "no-venus-no-kgsl-no-raw-dsi-no-power-writes",
        },
        "v2880_marker_strings": marker_strings,
        "adoption_state": "pending-live-validation",
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
    (OUT_DIR / "audio-pcm-file-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-pcm-file-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": "V2880",
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
        "note": "V2880 packages bounded raw S16LE PCM-file input for the native audio play path.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
