#!/usr/bin/env python3
"""Build V2798 native-init audio msm_audio_cal devnode boot image.

V2798 keeps the V2796 `/dev/ion` materialization and V2797 dmabuf
`msync(EINVAL)` nonfatal handling, then materializes `/dev/msm_audio_cal` from
sysfs or `/proc/misc` before the SET-cal executor opens it. V2797 prepared all
SET entries and allocated ION, then stopped at `/dev/msm_audio_cal` errno=2.
"""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2789_audio_query_module as v2789
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

CYCLE = "V2798"
INIT_VERSION = "0.9.311"
INIT_BUILD = "v2798-audio-msm-audio-cal-devnode"
BUILD_TAG = "v2798-audio-msm-audio-cal-devnode"
DECISION = "v2798-audio-msm-audio-cal-devnode-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2798_AUDIO_MSM_AUDIO_CAL_DEVNODE_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2798_audio_msm_audio_cal_devnode.img", legacy_fallback=False
)
BASE_BOOT = workspace_private_input_path(
    "boot_images", "boot_linux_v2334_audio_snd_nodes_preflight.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2798_audio_msm_audio_cal_devnode"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2798_audio_msm_audio_cal_devnode.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v445_audio_msm_audio_cal_devnode"


def _set_or_append_arg(args: list[str], key: str, value: str) -> None:
    if key in args:
        args[args.index(key) + 1] = value
    else:
        args.extend([key, value])


def configure_v2789_base() -> None:
    v2789.CYCLE = CYCLE
    v2789.INIT_VERSION = INIT_VERSION
    v2789.INIT_BUILD = INIT_BUILD
    v2789.BUILD_TAG = BUILD_TAG
    v2789.DECISION = DECISION
    v2789.OUT_DIR = OUT_DIR
    v2789.REPORT_PATH = REPORT_PATH
    v2789.BOOT_IMAGE = BOOT_IMAGE
    v2789.BASE_BOOT = BASE_BOOT
    v2789.INIT_BINARY = INIT_BINARY
    v2789.RAMDISK_CPIO = RAMDISK_CPIO
    v2789.HELPER_BINARY = HELPER_BINARY


def configure() -> tuple[str, ...]:
    v2789.v2334.OUT_DIR = OUT_DIR
    v2789.v2334.REPORT_PATH = REPORT_PATH
    v2789.v2334.BOOT_IMAGE = BOOT_IMAGE
    v2789.v2334.BASE_BOOT = BASE_BOOT
    v2789.v2334.INIT_BINARY = INIT_BINARY
    v2789.v2334.RAMDISK_CPIO = RAMDISK_CPIO
    v2789.v2334.HELPER_BINARY = HELPER_BINARY
    helper_flags = v2789.v2334.configure_base()

    base = v2789.v2334.base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": CYCLE,
        "--decision": DECISION,
        "--cycle-label": "v2798",
        "--init-version": INIT_VERSION,
        "--init-build": INIT_BUILD,
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--base-boot": str(BASE_BOOT),
        "--wifi-test-klog-prefix": "A90v2798",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2798.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2798.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2798.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2798-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2798.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2798-supervisor.pid",
    }
    for key, value in replacements.items():
        _set_or_append_arg(args, key, value)
    base.DEFAULT_ARGS = args
    return helper_flags


def render_report(manifest: dict[str, object], helper_flags: tuple[str, ...], init_extra_flags: tuple[str, ...]) -> str:
    return "\n".join([
        "# Native Init V2798 Audio MSM Audio Cal Devnode Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: audio command-surface integrated playback closure gate.",
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
        "- Compiles the V2798 source change that materializes `/dev/msm_audio_cal` from `/sys/class/misc/msm_audio_cal/dev` or `/proc/misc` before the SET-cal executor opens it.",
        "- Keeps the V2796 `/dev/ion` materialization, the V2797 dmabuf `msync(EINVAL)` nonfatal behavior, and the V2795 direct execute behavior: integrated play verifies the SET-cal manifest without the extra preload pass, then the execute stage owns payload loading, ION allocation, `/dev/msm_audio_cal` ioctl progress, route apply, bounded PCM, route reset, and SET deallocate.",
        "- The SET-cal executor is held active across the PCM write and then reverse-deallocated during integrated cleanup.",
        "- The live command to validate is `audio play internal-speaker-safe --mode listen --execute` with the private V2725 SET-cal manifest bundle staged under `/cache/a90-acdb-setcal-replay-v2725`.",
        "",
        "## Scope Boundary",
        "",
        "- No device action was performed by this builder.",
        "- No audio ioctl, mixer write, route apply, PCM open, or playback occurs during build.",
        "- The next live unit must flash this image, deploy the private SET-cal manifest bundle at `/cache/a90-acdb-setcal-replay-v2725`, run `audio play --execute`, confirm `audio.msm_audio_cal_materialize.*` plus `audio.setcal.execute.open.msm_audio_cal.open_ok=1`, poll `audio play-status`, confirm audible sound if playback completes, and rollback to `v2321`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Rollback target: `v2321-usb-clean-identity-rodata`.",
        "",
    ])


def main() -> int:
    configure_v2789_base()
    v2789.configure = configure
    v2789.render_report = render_report
    rc = v2789.main()

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "parent_baseline": "v2797-audio-dmabuf-msync-nonfatal",
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "deeper_fallback_baseline": "v2237-supplicant-terminate-poll",
        "audio_msm_audio_cal_devnode_source_validation": {
            "play_execute_supported": True,
            "play_worker_executor_compiled": True,
            "legacy_replay_manifest_prefix_allowed": True,
            "integrated_setcal_verify_load_files": False,
            "execute_stage_owns_payload_load": True,
            "ion_devnode_materialization_compiled": True,
            "msm_audio_cal_devnode_compiled": True,
            "msm_audio_cal_sysfs_dev_path": "/sys/class/misc/msm_audio_cal/dev",
            "msm_audio_cal_proc_misc_fallback": True,
            "msm_audio_cal_runtime_devnode": "/dev/msm_audio_cal",
            "ion_sysfs_dev_path": "/sys/class/misc/ion/dev",
            "ion_runtime_devnode": "/dev/ion",
            "dmabuf_msync_nonfatal_compiled": True,
            "v2797_blocker": "audio.setcal.execute.open.msm_audio_cal.open_ok=0 errno=2",
            "default_manifest_path": "/cache/a90-runtime/pkg/manifests/audio-setcal-internal-speaker-safe.manifest",
            "setcal_held_across_pcm": True,
            "listen_markers": True,
            "sound_control_wait_timeout_ms": 70000,
            "set_sequence_order": [39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21],
            "worker_sequence": ["adsp", "snd", "app_type", "setcal_hold", "route_core", "pcm", "route_core_reset", "setcal_deallocate"],
            "commands_to_probe_live_after_flash": [
                "audio prereq internal-speaker-safe",
                "audio play internal-speaker-safe --mode listen --execute",
            ],
        },
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
    (OUT_DIR / "promotion-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "note": "V2798 is a test image for integrated native audio playback, not a promoted rollback baseline.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
