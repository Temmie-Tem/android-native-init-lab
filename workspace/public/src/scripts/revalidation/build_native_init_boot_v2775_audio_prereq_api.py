#!/usr/bin/env python3
"""Build V2775 native-init audio prerequisite API boot image.

V2775 adds the read-only `audio prereq` API for callable speaker preparation stages.
The image is built for the next rollbackable live validation unit; this builder performs host-side build work only.
"""

from __future__ import annotations

import json
from pathlib import Path

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2334_audio_snd_nodes_preflight as v2334
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

CYCLE = "V2775"
INIT_VERSION = "0.9.296"
INIT_BUILD = "v2775-audio-prereq-api"
BUILD_TAG = "v2775-audio-prereq-api"
DECISION = "v2775-audio-prereq-api-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2775_AUDIO_PREREQ_API_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2775_audio_prereq_api.img", legacy_fallback=False
)
BASE_BOOT = workspace_private_input_path(
    "boot_images", "boot_linux_v2334_audio_snd_nodes_preflight.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2775_audio_prereq_api"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2775_audio_prereq_api.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v442_audio_prereq_api"


def _set_or_append_arg(args: list[str], key: str, value: str) -> None:
    if key in args:
        args[args.index(key) + 1] = value
    else:
        args.extend([key, value])


def configure() -> tuple[str, ...]:
    v2334.OUT_DIR = OUT_DIR
    v2334.REPORT_PATH = REPORT_PATH
    v2334.BOOT_IMAGE = BOOT_IMAGE
    v2334.BASE_BOOT = BASE_BOOT
    v2334.INIT_BINARY = INIT_BINARY
    v2334.RAMDISK_CPIO = RAMDISK_CPIO
    v2334.HELPER_BINARY = HELPER_BINARY
    helper_flags = v2334.configure_base()

    base = v2334.base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": CYCLE,
        "--decision": DECISION,
        "--cycle-label": "v2775",
        "--init-version": INIT_VERSION,
        "--init-build": INIT_BUILD,
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--base-boot": str(BASE_BOOT),
        "--wifi-test-klog-prefix": "A90v2775",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2775.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2775.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2775.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2775-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2775.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2775-supervisor.pid",
    }
    for key, value in replacements.items():
        _set_or_append_arg(args, key, value)
    base.DEFAULT_ARGS = args
    return helper_flags


def render_report(manifest: dict[str, object], helper_flags: tuple[str, ...], init_extra_flags: tuple[str, ...]) -> str:
    return "\n".join([
        "# Native Init V2775 Audio Prerequisite API Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: audio command prerequisite API image.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Base boot: `{str(BASE_BOOT.relative_to(REPO_ROOT))}`",
        "",
        "## Purpose",
        "",
        "- This compiles the V2775 source change that adds `audio prereq [profile]`, a read-only callable contract for ADSP, `/dev/snd`, app-type, SET replay, route, and PCM stages.",
        "- Expected future live validation: `version` / `status` / `selftest`, then `audio prereq internal-speaker-safe` to confirm the read-only prerequisite surface before any playback attempt.",
        "- Current source reports `audio.prereq.*` stage commands and `audio.prereq.snd.*` PCM node readiness without opening ALSA, issuing calibration ioctls, or writing mixer controls.",
        "",
        "## Scope Boundary",
        "",
        "- No device action was performed by this builder.",
        "- No audio ioctl, mixer write, ACDB SET, route apply, PCM open, or playback occurs during build.",
        "- The paired live runner must rollback to V2321 after validation.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Rollback target: `v2321-usb-clean-identity-rodata`.",
        "",
    ])


def main() -> int:
    helper_flags = configure()
    init_extra_flags = tuple(v2334.base_module().base.EXTRA_INIT_FLAGS)
    helper_builder = v2334.helper_builder_module()
    helper_builder.EXPECTED_HELPER_MARKER = v2334.v2323.v2321.EXPECTED_HELPER_MARKER
    helper_builder.EXPECTED_HELPER_SHA256 = v2334.v2323.v2321.EXPECTED_HELPER_SHA256
    base = v2334.base_module()
    base.base.EXPECTED_HELPER_MARKER = v2334.v2323.v2321.EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = v2334.v2323.v2321.EXPECTED_HELPER_SHA256
    helper_builder.patch_helper_builder(base)
    v2334.patch_mkbootimg_tool_paths(base)

    def render(manifest: dict[str, object]) -> str:
        if "usb_clean_identity_rodata_patch" not in manifest:
            manifest["usb_clean_identity_rodata_patch"] = v2334.inherited_clean_identity_patch_info()
        manifest["usb_named_lun_identities"] = v2334.v2323.LUN_IDENTITIES
        return render_report(manifest, helper_flags, init_extra_flags)

    base.render_report = render
    rc = base.main()

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "parent_baseline": "v2773-audio-play-prereq",
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "deeper_fallback_baseline": "v2237-supplicant-terminate-poll",
        "helper_flags": list(helper_flags),
        "init_extra_flags": list(init_extra_flags),
        "audio_prereq_api_source_validation": {
            "native_prereq_api_compiled": True,
            "commands_to_probe_live": [
                "audio status",
                "audio profiles",
                "audio stages internal-speaker-safe",
                "audio prereq internal-speaker-safe",
                "audio play internal-speaker-safe --mode probe --dry-run",
            ],
            "known_source_boundary": "audio.prereq is read-only and exposes callable stage commands before playback",
        },
        "usb_clean_identity_rodata_patch": v2334.inherited_clean_identity_patch_info(),
        "usb_named_lun_identities": v2334.v2323.LUN_IDENTITIES,
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest, helper_flags, init_extra_flags), encoding="utf-8")
    (OUT_DIR / "promotion-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "note": "V2775 is a test image for the read-only audio prerequisite API, not a promoted rollback baseline.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
