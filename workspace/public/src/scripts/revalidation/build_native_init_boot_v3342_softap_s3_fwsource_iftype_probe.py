#!/usr/bin/env python3
"""Build V3342 native-init SoftAP S3 firmware-source iftype probe candidate."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3341_softap_s3_iftype_probe as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3341_text
ORIG_PREVIOUS_SOFTAP_MANIFEST = previous._softap_manifest

CYCLE = "V3342"
INIT_VERSION = "0.11.106"
INIT_BUILD = "v3342-softap-s3-fwsource-iftype-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3342-softap-s3-fwsource-iftype-probe-source-build-pass"
HELPER_SOURCE_POLICY = "qcacld-fwsource-mounted-vendor-first"
EXPECTED_HELPER_MARKER = previous.wifi_route.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = "fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3342_SOFTAP_S3_FWSOURCE_IFTYPE_PROBE_SOURCE_BUILD_2026-06-28.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3342_softap_s3_fwsource_iftype_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3342_softap_s3_fwsource_iftype_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3342_softap_s3_fwsource_iftype_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v625_softap_s3_fwsource_iftype_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3342"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3342.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3342.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3342"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3342-softap-s3-fwsource-iftype-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3342-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3342-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3342-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3342-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3342-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3342-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3342-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-softap-s3-fwsource-iftype-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-softap-s3-fwsource-iftype-probe"

SFX_STREAM_MARKER = "a90.doomgeneric.v3342.audio=real-sfx-pcm-stream-softap-s3-fwsource-iftype-probe"
SOUND_MODE = "native-doom-sfx-softap-s3-fwsource-iftype-probe-v3342"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3342.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = previous.SOFTAP_COMMANDS


def _rewrite_v3342_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        ("softap-s3-iftype-probe", "softap-s3-fwsource-iftype-probe"),
        ("SOFTAP_S3_IFTYPE_PROBE", "SOFTAP_S3_FWSOURCE_IFTYPE_PROBE"),
        ("SoftAP S3 IfType Probe", "SoftAP S3 Firmware Source IfType Probe"),
        ("v3341", "v3342"),
        ("V3341", "V3342"),
        ("0.11.105", INIT_VERSION),
        ("a90-doomgeneric-v3341", "a90-doomgeneric-v3342"),
        ("a90.doomgeneric.v3341", "a90.doomgeneric.v3342"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3342_bytes(item: bytes) -> bytes:
    return _rewrite_v3342_text(item.decode("utf-8")).encode("utf-8")


REQUIRED_STRINGS = tuple(_rewrite_v3342_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    HELPER_SOURCE_POLICY.encode("utf-8"),
    b"source_policy=qcacld-fwsource-mounted-vendor-first",
)


def _softap_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_SOFTAP_MANIFEST()
    manifest["scope"] = "softap-fwsource-mounted-vendor-iftype-probe-no-ap-start"
    manifest["helper_route"]["source_policy"] = HELPER_SOURCE_POLICY
    manifest["helper_route"]["source_fix"] = "mounted-vendor-firmware-first-static-fallback"
    manifest["pass_requirements"] = list(dict.fromkeys([
        *manifest["pass_requirements"],
        "qcacld-fwsource-mounted-vendor-first",
        "qcacld-fwclass-feed-source-rc-0",
    ]))
    manifest["pass_requirements"] = [
        f"version-{INIT_VERSION}" if item == "version-0.11.105" else item
        for item in manifest["pass_requirements"]
    ]
    return manifest


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    boot_image = manifest.get("boot_image", base.rel(BOOT_IMAGE))
    boot_sha = manifest.get("boot_sha256", "")
    helper_sha = manifest.get("helper_sha256", "")
    return "\n".join([
        "# Native Init V3342 SoftAP S3 Firmware Source IfType Probe Source Build",
        "",
        f"- Cycle: `{CYCLE}`",
        f"- Decision: `{DECISION}`",
        f"- Init: `A90 Linux init {INIT_VERSION} ({INIT_BUILD})`",
        f"- Boot image: `{boot_image}`",
        f"- Boot SHA256: `{boot_sha}`",
        f"- Helper SHA256: `{helper_sha}`",
        f"- Base boot: `{base.rel(BASE_BOOT)}`",
        "",
        "## Change",
        "",
        "- Keeps the V3341 `wifi softap iftype-probe [timeout_ms]` AP-iftype add/delete proof.",
        "- Fixes the pre-iftype `wlan0` blocker by letting the QCACLD firmware_class feeder read from the helper's already mounted read-only vendor firmware tree before falling back to global `/vendor/firmware` paths.",
        f"- Adds helper source policy marker `{HELPER_SOURCE_POLICY}`.",
        "- Keeps AP service below start: no generated SSID/PSK config, no `wpa_supplicant mode=2`, no `udhcpd`, no listener, no AP address, no route/NAT.",
        "",
        "## Validation Contract",
        "",
        "- PASS requires post-flash `selftest fail=0`, helper-window `wlan0_present=1`, firmware_class feed `source_rc=0`, `decision=softap-iftype-probe-pass`, `ap_iftype_add_rc=0`, `ap_iftype_iface_created=1`, and `ap_iftype_cleanup_ok=1`.",
        "- Public output remains metadata-only and must not contain SSID, PSK, BSSID, MAC, client identifiers, concrete peer addresses, DHCP leases, or transfer payloads.",
        "",
        "## Static Validation",
        "",
        "- `py_compile`: V3342 builder and focused source tests.",
        "- Unit tests: V3342 firmware-source feeder source/build contract plus retained V3341 SoftAP iftype contract.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3342 identity, SoftAP v2, no-start fields, and the mounted-vendor-first firmware source policy marker.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `softap-s3-fwsource-iftype-probe-candidate`.",
    ]) + "\n"


def v3342_adapter_source() -> str:
    return _rewrite_v3342_text(previous.ORIG_PREVIOUS_ADAPTER_SOURCE())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "softap-s3-fwsource-iftype-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "softap-s3-fwsource-iftype-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "live_validation_focus": manifest["softap_s3"]["pass_requirements"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-softap-s3-fwsource-iftype-probe-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _finalize_manifest_after_overlay(
    overlay: dict[str, Any],
    *,
    base_main_completed: bool,
    base_main_error: str | None = None,
) -> None:
    manifest_path = OUT_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {
            "helper_sha256": base.sha256_file(HELPER_BINARY),
            "helper_flags": [SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG],
            "init_extra_flags": [],
        }
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "softap-s3-fwsource-iftype-probe-candidate",
        "adoption_state": "pending-softap-s3-fwsource-iftype-probe-live-validation",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_sha256": overlay["boot_sha256"],
        "ramdisk_sha256": overlay["ramdisk_sha256"],
        "ramdisk_overlay": overlay,
        "base_main_completed": base_main_completed,
        "helper_flags": list(dict.fromkeys([
            *manifest.get("helper_flags", []),
            SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG,
        ])),
        "softap_s3": _softap_manifest(),
    })
    if base_main_error:
        manifest["base_main_error"] = base_main_error
    else:
        manifest.pop("base_main_error", None)
    for key in ("gpu_d3", "gpu_h1", "gpu_m0", "gpu_m1", "gpu_m2", "gpu_m3", "gpu_z2", "gpu_z3", "softap_s2"):
        manifest.pop(key, None)
    manifest["softap_s3"]["ramdisk_overlay"] = overlay
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(
        render_report(
            manifest,
            tuple(manifest.get("helper_flags", ())),
            tuple(manifest.get("init_extra_flags", ())),
        ),
        encoding="utf-8",
    )
    _write_candidate_manifest(manifest)


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("base_main_error", None)
    for key in ("gpu_d3", "gpu_h1", "gpu_m0", "gpu_m1", "gpu_m2", "gpu_m3", "gpu_z2", "gpu_z3", "softap_s2"):
        manifest.pop(key, None)
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "softap-s3-fwsource-iftype-probe-candidate",
        "adoption_state": "pending-softap-s3-fwsource-iftype-probe-live-validation",
        "helper_flags": list(dict.fromkeys([
            *manifest.get("helper_flags", []),
            SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG,
        ])),
        "softap_s3": _softap_manifest(),
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
    _write_candidate_manifest(manifest)
    return manifest


def _overlay_preserved_v3342_ramdisk() -> dict[str, Any]:
    overlay = previous.ORIG_PREVIOUS_OVERLAY()
    overlay["mode"] = "preserve-v3335-ramdisk-overlay-v3342-init-helper-engine"
    return overlay


def _patch_v3341_module_for_v3342() -> None:
    replacements = {
        "CYCLE": CYCLE,
        "INIT_VERSION": INIT_VERSION,
        "INIT_BUILD": INIT_BUILD,
        "BUILD_TAG": BUILD_TAG,
        "DECISION": DECISION,
        "OUT_DIR": OUT_DIR,
        "OBJ_DIR": OBJ_DIR,
        "REPORT_PATH": REPORT_PATH,
        "BOOT_IMAGE": BOOT_IMAGE,
        "BASE_BOOT": BASE_BOOT,
        "INIT_BINARY": INIT_BINARY,
        "RAMDISK_CPIO": RAMDISK_CPIO,
        "HELPER_BINARY": HELPER_BINARY,
        "ENGINE_BINARY": ENGINE_BINARY,
        "ENGINE_ADAPTER_SOURCE": ENGINE_ADAPTER_SOURCE,
        "ENGINE_ADAPTER_OBJECT": ENGINE_ADAPTER_OBJECT,
        "ENGINE_RAMDISK_PATH": ENGINE_RAMDISK_PATH,
        "ENGINE_REMOTE_PATH": ENGINE_REMOTE_PATH,
        "ENGINE_NAME": ENGINE_NAME,
        "FRAME_PATH": FRAME_PATH,
        "SHARED_FRAME_PATH": SHARED_FRAME_PATH,
        "INPUT_STATE_PATH": INPUT_STATE_PATH,
        "INPUT_SOCKET_PATH": INPUT_SOCKET_PATH,
        "PACE_SOCKET_PATH": PACE_SOCKET_PATH,
        "TICK_TELEMETRY_PATH": TICK_TELEMETRY_PATH,
        "AUDIO_PCM_STREAM_PATH": AUDIO_PCM_STREAM_PATH,
        "FRAME_SCALE": FRAME_SCALE,
        "FRAME_IPC": FRAME_IPC,
        "SFX_STREAM_MARKER": SFX_STREAM_MARKER,
        "SOUND_MODE": SOUND_MODE,
        "SFX_BACKEND_SOURCE": SFX_BACKEND_SOURCE,
        "SDL_MIXER_STUB": SDL_MIXER_STUB,
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3341_adapter_source": v3342_adapter_source,
        "_rewrite_v3341_text": _rewrite_v3342_text,
        "_rewrite_v3341_bytes": _rewrite_v3342_bytes,
        "_softap_manifest": _softap_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_overlay_preserved_v3341_ramdisk": _overlay_preserved_v3342_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def _patch_expected_helper_sha() -> None:
    helper_builder = previous.wifi_route.helper_builder_module()
    previous.wifi_route.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    previous.wifi_route.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    helper_builder.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    helper_builder.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    helper_builder.patch_helper_builder = _patch_helper_builder_constant
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    archive_wrapper = helper_builder.prev2008.prev2006.build_base_module()
    archive_wrapper.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    archive_wrapper.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256


def _patch_helper_builder_constant(base_wrapper: Any) -> None:
    helper_builder = previous.wifi_route.helper_builder_module()
    helper_flags = tuple(helper_builder.HELPER_FLAGS)
    build_base = base_wrapper.base
    expected_marker = EXPECTED_HELPER_MARKER
    expected_sha = EXPECTED_HELPER_SHA256

    def build_helper(args: Any) -> None:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        command: list[object] = [
            "env",
            "A90_EXECNS_PROBE_CFLAGS=" + " ".join(helper_flags),
            "bash",
            build_base.HELPER_BUILD_SCRIPT,
            args.helper_binary,
        ]
        build_base.run(command)
        args.helper_binary.chmod(0o600)
        helper_sha = build_base.sha256(args.helper_binary)
        if helper_sha != expected_sha:
            raise RuntimeError(
                f"helper sha mismatch: got {helper_sha}, expected {expected_sha}"
            )
        strings = build_base.run(["strings", args.helper_binary], capture=True).stdout
        if expected_marker not in strings:
            raise RuntimeError(f"missing helper marker: {expected_marker}")

    build_base.build_helper = build_helper


def main() -> int:
    _patch_v3341_module_for_v3342()
    _patch_expected_helper_sha()
    previous._apply_v3341_overrides()
    _patch_expected_helper_sha()
    helper_builder = previous.wifi_route.helper_builder_module()
    archive_wrapper = helper_builder.prev2008.prev2006.build_base_module()
    _patch_helper_builder_constant(base)
    _patch_helper_builder_constant(archive_wrapper)
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
