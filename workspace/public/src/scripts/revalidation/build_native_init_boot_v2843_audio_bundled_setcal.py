#!/usr/bin/env python3
"""Build V2843 native-init audio bundled SET-cal candidate.

V2843 keeps the V2840/V2842 audio chime productization path, but packages the
private SET-cal replay bundle into the boot ramdisk under `/a90/audio` and
changes the default native manifest path to that bundled location. This is the
source/build half of removing the host late-deploy dependency; live validation
is a separate unit.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2807_audio_late_manifest_wait as v2807
import native_audio_adsp_kick_no_wait_live_handoff_v2804 as live_base
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2843"
INIT_VERSION = "0.10.12"
INIT_BUILD = "v2843-audio-bundled-setcal"
BUILD_TAG = INIT_BUILD
DECISION = "v2843-audio-bundled-setcal-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2843_AUDIO_BUNDLED_SETCAL_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2843_audio_bundled_setcal.img", legacy_fallback=False
)
BASE_BOOT = v2807.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v2843_audio_bundled_setcal"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2843_audio_bundled_setcal.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v453_audio_bundled_setcal"

OLD_REMOTE_ROOT = "/cache/a90-acdb-setcal-replay-v2725"
BUNDLED_PREFIX = "/a90/audio"
BUNDLED_REMOTE_ROOT = BUNDLED_PREFIX + "/setcal/internal-speaker-safe"
BUNDLED_REMOTE_MANIFEST = BUNDLED_PREFIX + "/manifests/audio-setcal-internal-speaker-safe.manifest"


def shell_define(name: str, value: str) -> str:
    return f'-D{name}="{value}"'


def configure_v2807_for_v2843() -> None:
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


def remap_remote_path(path: str | None) -> str | None:
    if not path:
        return path
    if path.startswith(OLD_REMOTE_ROOT + "/"):
        return BUNDLED_REMOTE_ROOT + path[len(OLD_REMOTE_ROOT):]
    return path


def remap_deploy_plan_to_bundled(deploy_plan: dict[str, Any]) -> dict[str, Any]:
    remapped = copy.deepcopy(deploy_plan)
    for item in remapped.get("files") or []:
        item["remote_path"] = remap_remote_path(str(item.get("remote_path") or ""))
    for item in remapped.get("replay_entries") or []:
        item["arg_remote"] = remap_remote_path(str(item.get("arg_remote") or ""))
        payload_remote = item.get("payload_remote")
        if payload_remote:
            item["payload_remote"] = remap_remote_path(str(payload_remote))
    remapped["remote_dir"] = BUNDLED_REMOTE_ROOT
    remapped["remote_native_manifest"] = BUNDLED_REMOTE_MANIFEST
    remapped["v2843_remote_remap"] = {
        "old_remote_root": OLD_REMOTE_ROOT,
        "bundled_prefix": BUNDLED_PREFIX,
        "bundled_remote_root": BUNDLED_REMOTE_ROOT,
        "bundled_remote_manifest": BUNDLED_REMOTE_MANIFEST,
    }
    return remapped


def bundled_relative_path(remote_path: str) -> str:
    if not remote_path.startswith(BUNDLED_PREFIX + "/"):
        raise ValueError(f"not a bundled path: {remote_path}")
    return remote_path.lstrip("/")


def prepare_bundled_assets() -> tuple[dict[str, Any], Path, dict[str, Path]]:
    deploy_plan = remap_deploy_plan_to_bundled(live_base.read_json(live_base.DEPLOY_PLAN))
    errors = live_base.validate_deploy_plan(deploy_plan)
    if errors:
        raise RuntimeError("bundled deploy plan invalid: " + "; ".join(errors))
    manifest_path = live_base.materialize_native_manifest(OUT_DIR, deploy_plan)
    ramdisk_files: dict[str, Path] = {}
    for entry in live_base.deploy_artifacts_for_native_manifest(deploy_plan):
        remote = str(entry.get("remote_path") or "")
        ramdisk_files[bundled_relative_path(remote)] = live_base.local_private_path(entry)
    ramdisk_files[bundled_relative_path(BUNDLED_REMOTE_MANIFEST)] = manifest_path
    return deploy_plan, manifest_path, ramdisk_files


def patch_ramdisk_and_flags(ramdisk_files: dict[str, Path]) -> None:
    base = v2807.v2799.v2789.v2334.base_module().base
    original_ramdisk_helpers = base.ramdisk_helpers
    inherited_flags = tuple(base.EXTRA_INIT_FLAGS)
    bundled_flags = (
        shell_define("AUDIO_SETCAL_BUNDLED_PREFIX", BUNDLED_PREFIX),
        shell_define("AUDIO_SETCAL_DEFAULT_MANIFEST_PATH", BUNDLED_REMOTE_MANIFEST),
    )
    base.EXTRA_INIT_FLAGS = (*inherited_flags, *bundled_flags)

    def ramdisk_helpers_with_bundled_setcal(args: Any) -> dict[str, Path]:
        helpers = dict(original_ramdisk_helpers(args))
        helpers.update(ramdisk_files)
        return helpers

    base.ramdisk_helpers = ramdisk_helpers_with_bundled_setcal


def configure() -> tuple[str, ...]:
    helper_flags = v2807.configure()
    _deploy_plan, _manifest_path, ramdisk_files = prepare_bundled_assets()
    patch_ramdisk_and_flags(ramdisk_files)
    return helper_flags


def render_report(manifest: dict[str, object], helper_flags: tuple[str, ...], init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    return "\n".join([
        "# Native Init V2843 Audio Bundled SET-cal Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: post-promotion audio productization / standalone runtime packaging.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Base boot: `{str(BASE_BOOT.relative_to(REPO_ROOT))}`",
        "",
        "## Included Delta",
        "",
        f"- Adds an allowlisted bundled SET-cal prefix: `{BUNDLED_PREFIX}`.",
        f"- Overrides default native manifest path to `{BUNDLED_REMOTE_MANIFEST}` for this build only.",
        "- Packages the private SET-cal arg/payload files plus generated native manifest into the boot ramdisk under `/a90/audio`.",
        "- Keeps boot autoplay disabled; this unit only removes the host late-deploy dependency for manual playback validation.",
        "",
        "## Bundled Runtime Metadata",
        "",
        f"- Bundled artifact count: `{bundled.get('artifact_count')}`",
        f"- Replay entry count: `{bundled.get('replay_entry_count')}`",
        f"- Native manifest SHA256: `{bundled.get('native_manifest_sha256')}`",
        f"- Bundled remote root: `{BUNDLED_REMOTE_ROOT}`",
        "- Raw SET-cal bytes remain private; this report records only counts and hashes.",
        "",
        "## Validation",
        "",
        "- `py_compile`: builder and focused tests.",
        "- `unittest`: bundled SET-cal source/build tests.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.",
        "- Next live unit should flash this exact image and run `audio chime --execute` without host artifact deployment.",
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- No audio ioctl, mixer write, route apply, PCM open, or playback occurs during build.",
        "- Private raw payloads are not committed; they are only copied into the private generated boot image.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `audio-productization-bundled-setcal-candidate`.",
        "",
    ])


def main() -> int:
    configure_v2807_for_v2843()
    v2807.configure_v2789_base()
    v2807.v2799.v2789.configure = configure
    v2807.v2799.v2789.render_report = render_report
    rc = v2807.v2799.v2789.main()

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    deploy_plan = remap_deploy_plan_to_bundled(live_base.read_json(live_base.DEPLOY_PLAN))
    native_manifest_path = OUT_DIR / "runtime" / "audio-setcal-internal-speaker-safe.manifest"
    artifact_count = len(live_base.deploy_artifacts_for_native_manifest(deploy_plan))
    replay_entry_count = len(deploy_plan.get("replay_entries") or [])
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-productization-bundled-setcal-candidate",
        "parent_test_artifact": "v2840-audio-chime-screen",
        "promoted_audio_core": "0.10.0",
        "audio_bundled_setcal": {
            "bundled_prefix": BUNDLED_PREFIX,
            "bundled_remote_root": BUNDLED_REMOTE_ROOT,
            "bundled_remote_manifest": BUNDLED_REMOTE_MANIFEST,
            "artifact_count": artifact_count,
            "replay_entry_count": replay_entry_count,
            "native_manifest_sha256": live_base.sha256_file(native_manifest_path),
            "raw_payloads_private": True,
            "host_late_deploy_dependency_removed_for_candidate": True,
        },
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
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
    (OUT_DIR / "audio-bundled-setcal-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-productization-bundled-setcal-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "bundled_prefix": BUNDLED_PREFIX,
        "bundled_remote_manifest": BUNDLED_REMOTE_MANIFEST,
        "artifact_count": artifact_count,
        "replay_entry_count": replay_entry_count,
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
        "note": "V2843 packages the private SET-cal bundle into the boot ramdisk for a follow-up standalone playback validation; raw payloads stay private and untracked.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
