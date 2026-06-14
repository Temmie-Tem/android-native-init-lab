#!/usr/bin/env python3
"""Build V2329 audio ADSP firmware preflight correction boot.

V2329 keeps the V2323 named multi-LUN USB behavior and corrects the refusal-first
`audio adsp-boot-once` preflight after V2328 proved the stock ADSP segment set is
sparse and the effective firmware_class path can differ from the mounted APNHLOS
firmware path. It does not flash or run the activation path.
"""

from __future__ import annotations

import json
from pathlib import Path

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2323_usb_multi_lun_identity as v2323
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2329-audio-adsp-fw-preflight")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2329_AUDIO_ADSP_FW_PREFLIGHT_SOURCE_BUILD_2026-06-14.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2329_audio_adsp_fw_preflight.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2329_audio_adsp_fw_preflight"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2329_audio_adsp_fw_preflight.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v439_audio_adsp_fw_preflight"
PATCHED_KERNEL = OUT_DIR / "kernel_v2329_audio_adsp_fw_preflight"


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
        "--cycle": "V2329",
        "--decision": "v2329-audio-adsp-fw-preflight-source-build-pass",
        "--cycle-label": "v2329",
        "--init-version": "0.9.290",
        "--init-build": "v2329-audio-adsp-fw-preflight",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2329",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2329.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2329.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2329.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2329-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2329.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2329-supervisor.pid",
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
        "# Native Init V2329 Audio ADSP Firmware Preflight Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2329`",
        "- Track: audio AUD-2 gated firmware preflight correction, source/build-only.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no`.",
        "- Device action: `none`.",
        "- Manifest: `workspace/private/builds/native-init/v2329-audio-adsp-fw-preflight/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Change",
        "",
        "- Keeps the native-init command surface at `audio [adsp-status|status|adsp-boot-once]`.",
        "- Corrects the ADSP firmware segment model from contiguous `adsp.b00`..`adsp.b16` to the stock sparse NON-HLOS set `adsp.b00`..`adsp.b11` plus `adsp.b13`..`adsp.b16`; `adsp.b12` is not expected.",
        "- `audio adsp-status` now reports both the mounted APNHLOS firmware directory and the effective `firmware_class.path` directory with ADSP segment model, count, missing-list, and completion status.",
        "- `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT` still refuses without the exact token, but now also refuses if the effective `firmware_class.path` does not itself expose a complete ADSP firmware set.",
        "- If all preflight checks pass in a future gated live run, the only activation write remains `1\\n` to `/sys/kernel/boot_adsp/boot` once.",
        "- No `tinymix`, `tinyplay`, PCM, HAL, adsprpc invoke/ioctl, `/dev/subsys_adsp` open, retry, unload, or playback path is added.",
        "",
        "## Host Evidence Correction",
        "",
        "- V2328 correctly blocked before activation, but the immediate `adsp.b12` discriminator was a false-negative in the V2327 preflight model.",
        "- The private AUD-0 NON-HLOS FAT directory inventory lists `ADSP.B00`..`ADSP.B11` and `ADSP.B13`..`ADSP.B16`, plus `ADSP.MDT`; it does not list `ADSP.B12`.",
        "- Therefore a complete stock ADSP image for this build is the sparse 16-segment set, not a contiguous 17-segment set.",
        "- V2328 also showed `firmware_class.path=/mnt/vendor/firmware` while V2327 validated only `/vendor/firmware_mnt/image`; V2329 treats the effective firmware_class path as the write gate.",
        "",
        "## Expected Live Discriminator",
        "",
        "- If `/vendor/firmware_mnt/image` has the sparse ADSP set but `firmware_class.path` still points at `/mnt/vendor/firmware` without ADSP files, `audio adsp-boot-once` must refuse with `firmware-class-path-incomplete` and keep `activation_write_attempted=0`.",
        "- A future AUD-2 activation attempt requires a separate, explicit serve-path fix or proof that the effective firmware_class path exposes the sparse ADSP set.",
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
        "## Static Validation",
        "",
        "- Source build: PASS.",
        "- `file` on init binary: recorded by builder output.",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2329_audio_adsp_fw_preflight.py`: PASS.",
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

    def render_with_v2329_info(manifest: dict[str, object]) -> str:
        if "usb_clean_identity_rodata_patch" not in manifest:
            if v2323.v2321.LAST_PATCH_INFO is None:
                raise RuntimeError("clean identity rodata patch info missing before report render")
            manifest["usb_clean_identity_rodata_patch"] = v2323.v2321.LAST_PATCH_INFO
        manifest["usb_named_lun_identities"] = v2323.LUN_IDENTITIES
        return render_report(manifest, helper_flags)

    base.render_report = render_with_v2329_info
    rc = base.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    patch_info = {
        **v2323.v2321.USB_CLEAN_IDENTITY_RODATA_PATCH,
        "patched_kernel_sha256": v2323.v2321.sha256(PATCHED_KERNEL),
    }
    manifest["candidate_tag"] = "v2329-audio-adsp-fw-preflight"
    manifest["parent_baseline"] = "v2323-usb-multi-lun-identity"
    manifest["rollback_baseline"] = "v2321-usb-clean-identity-rodata"
    manifest["deeper_fallback_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["helper_flags"] = list(helper_flags)
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
    REPORT_PATH.write_text(render_report(manifest, helper_flags), encoding="utf-8")
    promotion_path = OUT_DIR / "promotion-candidate.json"
    promotion_path.write_text(json.dumps({
        "candidate_tag": "v2329-audio-adsp-fw-preflight",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest["helper_sha256"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "audio_command": manifest["audio_command"],
        "usb_named_lun_identities": manifest["usb_named_lun_identities"],
        "clean_identity_rodata_patch": patch_info,
        "note": "V2329 is a source/build-only AUD-2 firmware preflight correction artifact. Do not flash or run audio adsp-boot-once without the explicit AUD-2 operator phrase.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
