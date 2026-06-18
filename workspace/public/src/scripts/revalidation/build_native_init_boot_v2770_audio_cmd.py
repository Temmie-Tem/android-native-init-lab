#!/usr/bin/env python3
"""Build V2770 native-init audio command validation boot image.

V2770 is the anti-churn device milestone for the audio command surface: it
rebuilds the current native-init source, including the accumulated `audio`
subcommands, into a flashable test image.  The image itself does not run audio;
live validation is handled by `native_audio_cmd_device_validation_handoff_v2770.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2334_audio_snd_nodes_preflight as v2334
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

CYCLE = "V2770"
INIT_VERSION = "0.9.293"
INIT_BUILD = "v2770-audio-cmd"
BUILD_TAG = "v2770-audio-cmd-device-validation"
DECISION = "v2770-audio-cmd-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2770_AUDIO_CMD_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2770_audio_cmd.img", legacy_fallback=False
)
BASE_BOOT = workspace_private_input_path(
    "boot_images", "boot_linux_v2334_audio_snd_nodes_preflight.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2770_audio_cmd"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2770_audio_cmd.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v441_audio_cmd"


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
        "--cycle-label": "v2770",
        "--init-version": INIT_VERSION,
        "--init-build": INIT_BUILD,
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--base-boot": str(BASE_BOOT),
        "--wifi-test-klog-prefix": "A90v2770",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2770.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2770.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2770.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2770-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2770.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2770-supervisor.pid",
    }
    for key, value in replacements.items():
        _set_or_append_arg(args, key, value)
    base.DEFAULT_ARGS = args
    return helper_flags


def render_report(manifest: dict[str, object], helper_flags: tuple[str, ...], init_extra_flags: tuple[str, ...]) -> str:
    return "\n".join([
        "# Native Init V2770 Audio Command Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: audio command device-validation image.",
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
        "- This is the anti-churn checkpoint required by `GOAL.md`: compile the current `a90_audio.c` command surface into a real boot image before adding more host-only APIs.",
        "- Expected live validation: `version` / `status` / `selftest`, then `audio status`, `audio profiles`, `audio stages`, `audio play internal-speaker-safe --mode probe --dry-run`, and `audio play ... --execute` to confirm the current implementation boundary.",
        "- Current source intentionally reports `audio.play.execute_supported=0`; live sound is therefore not expected from this image unless the source changed before build.",
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
        "parent_baseline": "v2334-audio-snd-nodes-preflight",
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "deeper_fallback_baseline": "v2237-supplicant-terminate-poll",
        "helper_flags": list(helper_flags),
        "init_extra_flags": list(init_extra_flags),
        "audio_command_device_validation": {
            "anti_churn_device_milestone": True,
            "commands_to_probe_live": [
                "audio status",
                "audio profiles",
                "audio stages internal-speaker-safe",
                "audio play internal-speaker-safe --mode probe --dry-run",
                "audio play internal-speaker-safe --mode probe --execute",
            ],
            "known_source_boundary": "audio.play.execute_supported=0 / execute-not-implemented-native-pcm",
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
        "note": "V2770 is a test image for on-device audio command validation, not a promoted rollback baseline.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
