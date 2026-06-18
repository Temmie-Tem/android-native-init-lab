#!/usr/bin/env python3
"""Build V2771 native-init audio PCM writer boot image.

V2771 promotes `audio play --execute` from a source refusal to a bounded native PCM writer.
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

CYCLE = "V2771"
INIT_VERSION = "0.9.294"
INIT_BUILD = "v2771-audio-pcm-writer"
BUILD_TAG = "v2771-audio-pcm-writer"
DECISION = "v2771-audio-pcm-writer-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2771_AUDIO_PCM_WRITER_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2771_audio_pcm_writer.img", legacy_fallback=False
)
BASE_BOOT = workspace_private_input_path(
    "boot_images", "boot_linux_v2334_audio_snd_nodes_preflight.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2771_audio_pcm_writer"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2771_audio_pcm_writer.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v441_audio_pcm_writer"


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
        "--cycle-label": "v2771",
        "--init-version": INIT_VERSION,
        "--init-build": INIT_BUILD,
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--base-boot": str(BASE_BOOT),
        "--wifi-test-klog-prefix": "A90v2771",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2771.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2771.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2771.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2771-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2771.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2771-supervisor.pid",
    }
    for key, value in replacements.items():
        _set_or_append_arg(args, key, value)
    base.DEFAULT_ARGS = args
    return helper_flags


def render_report(manifest: dict[str, object], helper_flags: tuple[str, ...], init_extra_flags: tuple[str, ...]) -> str:
    return "\n".join([
        "# Native Init V2771 Audio PCM Writer Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: audio command PCM writer image.",
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
        "- This compiles the V2771 source change that makes `audio play --execute` attempt bounded native PCM playback instead of returning `execute-not-implemented-native-pcm`.",
        "- Expected live validation: `version` / `status` / `selftest`, then `audio play internal-speaker-safe --mode probe --dry-run` and a single bounded `audio play ... --execute` after the required app-type / SET / route prerequisites are staged by the chosen runner.",
        "- Current source reports `audio.play.execute_supported=1`; live success still depends on app-type, ACDB SET replay, route, and `/dev/snd` prerequisites.",
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
        "parent_baseline": "v2770-audio-cmd",
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "deeper_fallback_baseline": "v2237-supplicant-terminate-poll",
        "helper_flags": list(helper_flags),
        "init_extra_flags": list(init_extra_flags),
        "audio_pcm_writer_device_validation": {
            "native_pcm_writer_compiled": True,
            "commands_to_probe_live": [
                "audio status",
                "audio profiles",
                "audio stages internal-speaker-safe",
                "audio play internal-speaker-safe --mode probe --dry-run",
                "audio play internal-speaker-safe --mode probe --execute",
            ],
            "known_source_boundary": "audio.play.execute_supported=1 / native PCM writer attempts ALSA open+HW_PARAMS+WRITEI+DRAIN",
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
        "note": "V2771 is a test image for on-device audio PCM writer validation, not a promoted rollback baseline.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
