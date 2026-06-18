#!/usr/bin/env python3
"""Build V2793 native-init audio play worker boot image.

V2793 compiles the asynchronous native `audio play --execute` worker path.
The image is the test artifact for the device playback closure run.
"""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2789_audio_query_module as v2789
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

CYCLE = "V2793"
INIT_VERSION = "0.9.306"
INIT_BUILD = "v2793-audio-play-worker"
BUILD_TAG = "v2793-audio-play-worker"
DECISION = "v2793-audio-play-worker-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2793_AUDIO_PLAY_WORKER_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2793_audio_play_worker.img", legacy_fallback=False
)
BASE_BOOT = workspace_private_input_path(
    "boot_images", "boot_linux_v2334_audio_snd_nodes_preflight.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2793_audio_play_worker"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2793_audio_play_worker.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v445_audio_play_worker"


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
        "--cycle-label": "v2793",
        "--init-version": INIT_VERSION,
        "--init-build": INIT_BUILD,
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--base-boot": str(BASE_BOOT),
        "--wifi-test-klog-prefix": "A90v2793",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2793.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2793.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2793.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2793-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2793.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2793-supervisor.pid",
    }
    for key, value in replacements.items():
        _set_or_append_arg(args, key, value)
    base.DEFAULT_ARGS = args
    return helper_flags


def render_report(manifest: dict[str, object], helper_flags: tuple[str, ...], init_extra_flags: tuple[str, ...]) -> str:
    return "\n".join([
        "# Native Init V2793 Audio Play Worker Source Build",
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
        "- Compiles the V2793 source change that turns `audio play --execute` into the asynchronous worker path: parent returns after spawning a child; the child performs ADSP boot, 70s sound-control settle wait, `/dev/snd` materialization, App Type Config, ACDB SET hold, route apply, bounded PCM, route reset, and SET deallocate.",
        "- The SET-cal executor is held active across the PCM write and then reverse-deallocated during integrated cleanup.",
        "- The live command to validate is `audio play internal-speaker-safe --mode listen --execute` with the default private manifest path under `/cache/a90-runtime/pkg/manifests/`.",
        "",
        "## Scope Boundary",
        "",
        "- No device action was performed by this builder.",
        "- No audio ioctl, mixer write, route apply, PCM open, or playback occurs during build.",
        "- The next live unit must flash this image, deploy the private SET-cal manifest bundle, run `audio play --execute`, poll `audio play-status`, confirm audible sound, and rollback to `v2321`.",
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
        "parent_baseline": "v2791-audio-integrated-play",
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "deeper_fallback_baseline": "v2237-supplicant-terminate-poll",
        "audio_play_worker_source_validation": {
            "play_execute_supported": True,
            "play_worker_executor_compiled": True,
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
        "note": "V2793 is a test image for integrated native audio playback, not a promoted rollback baseline.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
