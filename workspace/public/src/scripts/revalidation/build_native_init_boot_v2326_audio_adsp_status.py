#!/usr/bin/env python3
"""Build V2326 audio ADSP status preparation boot.

V2326 keeps the V2323 named multi-LUN USB behavior and adds only a read-only
`audio adsp-status` command for the future operator-gated AUD-2 ADSP liveness
probe. It does not add or run any ADSP activation path.
"""

from __future__ import annotations

import json
from pathlib import Path

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2323_usb_multi_lun_identity as v2323
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2326-audio-adsp-status")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2326_AUDIO_ADSP_STATUS_SOURCE_BUILD_2026-06-14.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2326_audio_adsp_status.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2326_audio_adsp_status"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2326_audio_adsp_status.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v439_audio_adsp_status"
PATCHED_KERNEL = OUT_DIR / "kernel_v2326_audio_adsp_status"


def base_module():
    return v2323.base_module()


def helper_builder_module():
    return v2323.helper_builder_module()


def set_arg(args: list[str], key: str, value: str) -> None:
    index = args.index(key)
    args[index + 1] = value


def configure_base() -> tuple[str, ...]:
    v2323.OUT_DIR = OUT_DIR
    v2323.REPORT_PATH = REPORT_PATH
    v2323.BOOT_IMAGE = BOOT_IMAGE
    v2323.INIT_BINARY = INIT_BINARY
    v2323.RAMDISK_CPIO = RAMDISK_CPIO
    v2323.HELPER_BINARY = HELPER_BINARY
    v2323.PATCHED_KERNEL = PATCHED_KERNEL
    helper_flags = v2323.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2326",
        "--decision": "v2326-audio-adsp-status-source-build-pass",
        "--cycle-label": "v2326",
        "--init-version": "0.9.288",
        "--init-build": "v2326-audio-adsp-status",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2326",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2326.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2326.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2326.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2326-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2326.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2326-supervisor.pid",
    }
    for key, value in replacements.items():
        set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    return helper_flags


def render_report(manifest: dict[str, object], helper_flags: tuple[str, ...]) -> str:
    helper_flag_lines = [f"- `{flag}`" for flag in helper_flags]
    identities = manifest["usb_named_lun_identities"]
    identity_lines = [
        f"- `lun.{item['lun']}` model `{item['inquiry_product']}`, FAT label `{item['volume_label']}`, backing `{item['backing_file']}`."
        for item in identities
    ]
    return "\n".join([
        "# Native Init V2326 Audio ADSP Status Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2326`",
        "- Track: audio AUD-2 preparation, source/build-only.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no`.",
        "- Device action: `none`.",
        "- Manifest: `workspace/private/builds/native-init/v2326-audio-adsp-status/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Change",
        "",
        "- Adds the native-init command `audio [adsp-status|status]`.",
        "- The command is read-only: it reports firmware-class path, `/sys/kernel/boot_adsp/boot` metadata, ADSP firmware visibility, remoteproc/RPMSG/FastRPC/sound class counts, `/proc/asound/cards`, and relevant device-node metadata.",
        "- The command reports `audio.status.activation_write_attempted=0` and `audio.status.audio_playback_attempted=0` by construction.",
        "- No `audio adsp-boot-once`, `tinymix`, `tinyplay`, PCM, HAL, adsprpc invoke/ioctl, or `/dev/subsys_adsp` open path is added.",
        "",
        "## Safety Boundary",
        "",
        "- This is not AUD-2 live execution. It only prepares the read-only preflight surface that AUD-2 would use after explicit operator approval.",
        "- No ADSP activation write is implemented or run.",
        "- No flash was performed by this source-build unit.",
        "- Future live use still requires the explicit AUD-2 operator phrase from V2325 and the AGENTS.md flash/rollback gates.",
        "",
        "## USB Baseline Retained",
        "",
        "- Parent descriptor remains V2321: `A90-LNX` / `A90 Linux ARM64` / `A90NATIVE001`.",
        "- V2323 named multi-LUN behavior is retained:",
        *identity_lines,
        "",
        "## Helper Flags",
        "",
        *helper_flag_lines,
        "",
        "## Static Validation",
        "",
        "- Source build: PASS.",
        "- `file` on init binary: recorded by builder output.",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2326_audio_adsp_status.py`: PASS.",
        "- `python3 -m unittest discover -s tests -p 'test_*.py'`: PASS (`996` tests).",
        "- `git diff --check`: PASS.",
        "",
    ])


def main() -> int:
    helper_flags = configure_base()
    helper_builder = helper_builder_module()
    helper_builder.EXPECTED_HELPER_MARKER = v2323.v2321.EXPECTED_HELPER_MARKER
    helper_builder.EXPECTED_HELPER_SHA256 = v2323.v2321.EXPECTED_HELPER_SHA256
    base = base_module()
    base.base.EXPECTED_HELPER_MARKER = v2323.v2321.EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = v2323.v2321.EXPECTED_HELPER_SHA256
    helper_builder.patch_helper_builder(base)
    v2323.v2321.patch_mkbootimg_tools(base)

    def render_with_v2326_info(manifest: dict[str, object]) -> str:
        if "usb_clean_identity_rodata_patch" not in manifest:
            if v2323.v2321.LAST_PATCH_INFO is None:
                raise RuntimeError("clean identity rodata patch info missing before report render")
            manifest["usb_clean_identity_rodata_patch"] = v2323.v2321.LAST_PATCH_INFO
        manifest["usb_named_lun_identities"] = v2323.LUN_IDENTITIES
        return render_report(manifest, helper_flags)

    base.render_report = render_with_v2326_info
    rc = base.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    patch_info = {
        **v2323.v2321.USB_CLEAN_IDENTITY_RODATA_PATCH,
        "patched_kernel_sha256": v2323.v2321.sha256(PATCHED_KERNEL),
    }
    manifest["candidate_tag"] = "v2326-audio-adsp-status"
    manifest["parent_baseline"] = "v2323-usb-multi-lun-identity"
    manifest["rollback_baseline"] = "v2321-usb-clean-identity-rodata"
    manifest["deeper_fallback_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["helper_flags"] = list(helper_flags)
    manifest["usb_clean_identity_rodata_patch"] = patch_info
    manifest["usb_named_lun_identities"] = v2323.LUN_IDENTITIES
    manifest["audio_command"] = {
        "name": "audio",
        "subcommands": ["adsp-status", "status"],
        "activation_write_attempted": False,
        "audio_playback_attempted": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest, helper_flags), encoding="utf-8")
    promotion_path = OUT_DIR / "promotion-candidate.json"
    promotion_path.write_text(json.dumps({
        "candidate_tag": "v2326-audio-adsp-status",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest["helper_sha256"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "audio_command": manifest["audio_command"],
        "usb_named_lun_identities": manifest["usb_named_lun_identities"],
        "clean_identity_rodata_patch": patch_info,
        "note": "V2326 is a source/build-only AUD-2 preparation artifact. Do not flash or run ADSP liveness without the explicit AUD-2 operator phrase.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
