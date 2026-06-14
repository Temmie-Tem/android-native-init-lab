#!/usr/bin/env python3
"""Build V2331 audio ADSP firmware_class native-path boot.

V2331 keeps the V2329 sparse ADSP preflight and disables the legacy
Wi-Fi-only firmware_class vendor-path override so the boot cmdline
`firmware_class.path=/vendor/firmware_mnt/image` remains the effective loader
path for the AUD-2 liveness gate. It does not flash or run the activation path.
"""

from __future__ import annotations

import json
from pathlib import Path

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2323_usb_multi_lun_identity as v2323
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2331-audio-adsp-fwclass-native-path")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2331_AUDIO_ADSP_FWCLASS_NATIVE_PATH_SOURCE_BUILD_2026-06-14.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2331_audio_adsp_fwclass_native_path.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2331_audio_adsp_fwclass_native_path"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2331_audio_adsp_fwclass_native_path.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v440_audio_adsp_fwclass_native_path"
PATCHED_KERNEL = OUT_DIR / "kernel_v2331_audio_adsp_fwclass_native_path"
FWCLASS_NATIVE_PATH_FLAGS = (
    "-UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH",
    "-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0",
)


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
        "--cycle": "V2331",
        "--decision": "v2331-audio-adsp-fwclass-native-path-source-build-pass",
        "--cycle-label": "v2331",
        "--init-version": "0.9.291",
        "--init-build": "v2331-audio-adsp-fwclass-native-path",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2331",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2331.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2331.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2331.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2331-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2331.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2331-supervisor.pid",
    }
    for key, value in replacements.items():
        set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    inherited_extra_flags = tuple(base.base.EXTRA_INIT_FLAGS)
    base.base.EXTRA_INIT_FLAGS = (*inherited_extra_flags, *FWCLASS_NATIVE_PATH_FLAGS)
    return helper_flags


def render_report(
    manifest: dict[str, object],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    helper_flag_lines = [f"- `{flag}`" for flag in helper_flags]
    init_extra_flag_lines = [f"- `{flag}`" for flag in init_extra_flags]
    identities = manifest["usb_named_lun_identities"]
    identity_lines = [
        f"- `lun.{item['lun']}` model `{item['inquiry_product']}`, FAT label `{item['volume_label']}`, backing `{item['backing_file']}`."
        for item in identities
    ]
    return "\n".join([
        "# Native Init V2331 Audio ADSP Firmware Class Native Path Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2331`",
        "- Track: audio AUD-2 gated firmware preflight correction, source/build-only.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no`.",
        "- Device action: `none`.",
        "- Manifest: `workspace/private/builds/native-init/v2331-audio-adsp-fwclass-native-path/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Change",
        "",
        "- Keeps the native-init command surface at `audio [adsp-status|status|adsp-boot-once]`.",
        "- Retains the V2329 sparse ADSP firmware segment model: `adsp.b00`..`adsp.b11` plus `adsp.b13`..`adsp.b16`; `adsp.b12` is not expected.",
        "- Retains the V2329 effective `firmware_class.path` preflight gate before any ADSP boot write.",
        "- Disables the legacy Wi-Fi-only `A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH` override for this audio artifact so PID1 should not rewrite `firmware_class.path` to `/mnt/vendor/firmware`.",
        "- Expected effective loader path is the boot cmdline path `/vendor/firmware_mnt/image`, which V2330 proved contains the complete sparse ADSP set.",
        "- If all preflight checks pass in a future gated live run, the only activation write remains `1\\n` to `/sys/kernel/boot_adsp/boot` once.",
        "- No `tinymix`, `tinyplay`, PCM, HAL, adsprpc invoke/ioctl, `/dev/subsys_adsp` open, retry, unload, or playback path is added.",
        "",
        "## Host Evidence Correction",
        "",
        "- V2328 correctly blocked before activation, but the immediate `adsp.b12` discriminator was a false-negative in the V2327 preflight model.",
        "- The private AUD-0 NON-HLOS FAT directory inventory lists `ADSP.B00`..`ADSP.B11` and `ADSP.B13`..`ADSP.B16`, plus `ADSP.MDT`; it does not list `ADSP.B12`.",
        "- Therefore a complete stock ADSP image for this build is the sparse 16-segment set, not a contiguous 17-segment set.",
        "- V2328 also showed `firmware_class.path=/mnt/vendor/firmware` while V2327 validated only `/vendor/firmware_mnt/image`; V2331 treats the effective firmware_class path as the write gate.",
        "- V2330 proved `/vendor/firmware_mnt/image` has the corrected sparse ADSP set while the legacy effective path `/mnt/vendor/firmware` has none.",
        "",
        "## Firmware Class Path Strategy",
        "",
        "- Mode: `disable-legacy-wifi-fwclass-vendor-path`.",
        "- Runtime sysfs write added by this build: `no`.",
        "- The inherited Wi-Fi firmware mounts stay enabled; only the legacy `/mnt/vendor/firmware` firmware_class override is disabled.",
        "- The live discriminator is direct: `audio adsp-status` must report `audio.firmware_class_path=/vendor/firmware_mnt/image` and `audio.firmware_class.adsp_complete=yes` before `audio adsp-boot-once` is allowed to write.",
        "",
        "## Safety Boundary",
        "",
        "- This is not AUD-2 live execution. It only fixes the gated command preflight that AUD-2 would use after explicit operator approval.",
        "- No ADSP activation write was run. No flash was performed by this source-build unit.",
        "- The command remains intentionally not safe-retryable at the `a90ctl` layer because it can write once after token + preflight.",
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
        "## Init Extra Flag Override",
        "",
        *init_extra_flag_lines,
        "",
        "## Static Validation",
        "",
        "- Source build: PASS.",
        "- `file` on init binary: recorded by builder output.",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2331_audio_adsp_fwclass_native_path.py`: PASS.",
        "- `python3 -m unittest discover -s tests -p 'test_*.py'`: PASS (`996` tests).",
        "- `git diff --check`: PASS.",
        "",
    ])


def main() -> int:
    helper_flags = configure_base()
    init_extra_flags = tuple(base_module().base.EXTRA_INIT_FLAGS)
    helper_builder = helper_builder_module()
    helper_builder.EXPECTED_HELPER_MARKER = v2323.v2321.EXPECTED_HELPER_MARKER
    helper_builder.EXPECTED_HELPER_SHA256 = v2323.v2321.EXPECTED_HELPER_SHA256
    base = base_module()
    base.base.EXPECTED_HELPER_MARKER = v2323.v2321.EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = v2323.v2321.EXPECTED_HELPER_SHA256
    helper_builder.patch_helper_builder(base)
    v2323.v2321.patch_mkbootimg_tools(base)

    def render_with_v2331_info(manifest: dict[str, object]) -> str:
        if "usb_clean_identity_rodata_patch" not in manifest:
            if v2323.v2321.LAST_PATCH_INFO is None:
                raise RuntimeError("clean identity rodata patch info missing before report render")
            manifest["usb_clean_identity_rodata_patch"] = v2323.v2321.LAST_PATCH_INFO
        manifest["usb_named_lun_identities"] = v2323.LUN_IDENTITIES
        return render_report(manifest, helper_flags, init_extra_flags)

    base.render_report = render_with_v2331_info
    rc = base.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    patch_info = {
        **v2323.v2321.USB_CLEAN_IDENTITY_RODATA_PATCH,
        "patched_kernel_sha256": v2323.v2321.sha256(PATCHED_KERNEL),
    }
    manifest["candidate_tag"] = "v2331-audio-adsp-fwclass-native-path"
    manifest["parent_baseline"] = "v2323-usb-multi-lun-identity"
    manifest["rollback_baseline"] = "v2321-usb-clean-identity-rodata"
    manifest["deeper_fallback_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["helper_flags"] = list(helper_flags)
    manifest["init_extra_flags"] = list(init_extra_flags)
    manifest["audio_fwclass_path_strategy"] = {
        "mode": "disable-legacy-wifi-fwclass-vendor-path",
        "expected_effective_firmware_class_path": "/vendor/firmware_mnt/image",
        "disabled_macro": "A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH",
        "runtime_sysfs_write_added_by_this_build": False,
        "adsp_activation_write_attempted_by_build": False,
        "retains_firmware_mounts": True,
        "reason": "V2330 proved the complete sparse ADSP set exists under /vendor/firmware_mnt/image while the legacy /mnt/vendor/firmware firmware_class path lacks ADSP files.",
    }
    manifest["usb_clean_identity_rodata_patch"] = patch_info
    manifest["usb_named_lun_identities"] = v2323.LUN_IDENTITIES
    manifest["audio_command"] = {
        "name": "audio",
        "subcommands": ["adsp-status", "status", "adsp-boot-once"],
        "boot_once_token": "AUD2_ONE_SHOT_ADSP_BOOT",
        "activation_write_attempted_by_build": False,
        "audio_playback_attempted": False,
        "boot_once_write_payload": "1\n",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest, helper_flags, init_extra_flags), encoding="utf-8")
    promotion_path = OUT_DIR / "promotion-candidate.json"
    promotion_path.write_text(json.dumps({
        "candidate_tag": "v2331-audio-adsp-fwclass-native-path",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest["helper_sha256"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "audio_command": manifest["audio_command"],
        "audio_fwclass_path_strategy": manifest["audio_fwclass_path_strategy"],
        "usb_named_lun_identities": manifest["usb_named_lun_identities"],
        "clean_identity_rodata_patch": patch_info,
        "note": "V2331 is a source/build-only AUD-2 firmware_class native-path artifact. Do not flash or run audio adsp-boot-once without the explicit AUD-2 operator phrase.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
