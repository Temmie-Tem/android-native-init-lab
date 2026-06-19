#!/usr/bin/env python3
"""Build V2812 native-init audio core 0.10.0 promotion candidate.

V2812 intentionally reuses the V2807 late-manifest-wait audio command source
that V2811 validated on-device, but rolls the device-visible init version to
0.10.0 for the audio-core promotion candidate. This build unit does not itself
promote the rollback baseline; a follow-up live unit must flash and validate
the generated image before adoption.
"""

from __future__ import annotations

import json

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2807_audio_late_manifest_wait as v2807
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2812"
INIT_VERSION = "0.10.0"
INIT_BUILD = "v2812-audio-core-promotion-candidate"
BUILD_TAG = INIT_BUILD
DECISION = "v2812-audio-core-promotion-candidate-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2812_AUDIO_CORE_PROMOTION_CANDIDATE_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2812_audio_core_promotion_candidate.img", legacy_fallback=False
)
BASE_BOOT = v2807.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v2812_audio_core_promotion_candidate"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2812_audio_core_promotion_candidate.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v445_audio_core_promotion_candidate"


def configure_v2807_for_v2812() -> None:
    v2807.CYCLE = CYCLE
    v2807.INIT_VERSION = INIT_VERSION
    v2807.INIT_BUILD = INIT_BUILD
    v2807.BUILD_TAG = BUILD_TAG
    v2807.DECISION = DECISION
    v2807.OUT_DIR = OUT_DIR
    v2807.REPORT_PATH = REPORT_PATH
    v2807.BOOT_IMAGE = BOOT_IMAGE
    v2807.BASE_BOOT = BASE_BOOT
    v2807.INIT_BINARY = INIT_BINARY
    v2807.RAMDISK_CPIO = RAMDISK_CPIO
    v2807.HELPER_BINARY = HELPER_BINARY


def render_report(manifest: dict[str, object],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    return "\n".join([
        "# Native Init V2812 Audio Core 0.10.0 Promotion Candidate Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: audio core promotion candidate.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Base boot: `{str(BASE_BOOT.relative_to(REPO_ROOT))}`",
        "",
        "## Promotion Context",
        "",
        "- V2811 proved the native `audio play --mode listen --execute` integrated path mechanically on device: worker start, ADSP/card/control, late manifest deploy, SET-cal, route, PCM write/drain, cleanup, and rollback all passed.",
        "- GOAL.md and `docs/operations/VERSIONING_POLICY.md` require an epic-level MINOR roll when audio becomes the adopted promoted baseline, so this candidate resets the init version from `0.9.x` to `0.10.0`.",
        "- This unit only builds the candidate. Adoption still requires a follow-up live validation of this exact boot image and an explicit docs/status promotion update.",
        "",
        "## Included Audio Core",
        "",
        "- Keeps the V2807 late-manifest wait source: `audio play` can start before private SET-cal artifacts are staged, then waits up to 90 s for the default runtime manifest.",
        "- Keeps the V2804 no-wait foreground ADSP kick, native-width `/dev/msm_audio_cal` ioctl constants, `/dev/ion` and `/dev/msm_audio_cal` materialization, dmabuf `msync(EINVAL)` nonfatal handling, observed App-Type Config, corrected SET-cal order, route apply/reset, and bounded PCM playback.",
        "- Safety profile remains `internal-speaker-safe`, listen amplitude 0.15, hard cap 0.2, no WSA smart-amp gain/boost writes.",
        "",
        "## Scope Boundary",
        "",
        "- No device action was performed by this builder.",
        "- No audio ioctl, mixer write, route apply, PCM open, or playback occurs during build.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata` until this candidate is live-validated and explicitly adopted.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `promotion-candidate`, not yet the rollback baseline.",
        "",
    ])


def rewrite_candidate_metadata() -> None:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-core-promotion-candidate",
        "parent_test_artifact": "v2807-audio-late-manifest-wait",
        "validated_by_prior_live_run": "V2811",
        "promotion_version_roll": "0.9.x-to-0.10.0",
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "promotion-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-core-promotion-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "validated_by_prior_live_run": "V2811",
        "adoption_state": "pending-live-validation",
        "note": "V2812 rolls the proven audio core to 0.10.0 as a promotion candidate; it is not adopted until a follow-up live validation passes.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    configure_v2807_for_v2812()
    v2807.render_report = render_report
    rc = v2807.main()
    rewrite_candidate_metadata()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
