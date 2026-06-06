#!/usr/bin/env python3
"""Build the V726 Wi-Fi lifecycle native init image.

V726 promotes the verified V2168 QCACLD firmware_class feeder route and the
V31/V32 modem-holder finding into one fasttransport-based boot candidate.
"""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_wifi_test_boot_v2168 as v2168
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v726-wifi-lifecycle-test-boot")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V726_WIFI_LIFECYCLE_SOURCE_BUILD_2026-06-07.md"
)
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v726/dev/__properties__"
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v726_wifi_lifecycle.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v726_wifi_lifecycle"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v726_wifi_lifecycle.cpio"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v427"
EXPECTED_HELPER_SHA256 = "99bdd67f0cd2fcaf6557478a97f85d405a0de3d6b0858ea17b4d46d7ce162ca1"
EXTRA_INIT_FLAGS = (
    *v2168.EXTRA_INIT_FLAGS,
    "-DA90_WIFI_LIFECYCLE_MODEM_OWNER=1",
)


def base_module():
    return v2168.base_module()


def set_arg(args: list[str], key: str, value: str) -> None:
    setter = (
        v2168.prev2137.prev2135.prev2133.prev2131.prev2129.prev2127.prev2120
        .prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095
        .prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg
    )
    setter(args, key, value)


def configure_base() -> None:
    v2168.OUT_DIR = OUT_DIR
    v2168.REPORT_PATH = REPORT_PATH
    v2168.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    v2168.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    v2168.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    v2168.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    v2168.prev2137.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    v2168.prev2137.prev2135.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    v2168.prev2137.prev2135.prev2133.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    v2168.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V726",
        "--decision": "v726-wifi-lifecycle-source-build-pass",
        "--cycle-label": "v726",
        "--init-version": "0.9.246",
        "--init-build": "v726-wifi-lifecycle",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v427_wifi_lifecycle"),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v726",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v726.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v726.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v726.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v726-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v726.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v726-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V726 Wi-Fi Lifecycle Source Build",
        "",
        "## Summary",
        "",
        "- Baseline tag: `v726-wifi-lifecycle`",
        "- Type: source/build-only baseline candidate.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: the V726 boot/init baseline incorporates the validation-route V2168 QCACLD firmware_class feeder path with a PID1-owned `/dev/subsys_modem` lifecycle holder, while preserving the V725 fasttransport ramdisk contract.",
        "- Manifest: `workspace/private/builds/native-init/v726-wifi-lifecycle-test-boot/manifest.json`",
        f"- Base boot: `{manifest['base_boot']}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        "- Boot SHA verification: source/build output; flash/readback/selftest verification is recorded in the V726 baseline promotion report.",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "- Version axes: `v726-wifi-lifecycle` is the boot/init baseline tag; `helper-v427` is the helper binary marker; `V2167`/`V2168` are validation-route/report identifiers, not newer boot baselines.",
        "",
        "## Included Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Kept from validation route V2168: firmware mounts, `firmware_class.path` vendor path, RFS bridges, post-FW_READY `boot_wlan`, and bounded QCACLD firmware_class feeder.",
        "- Added: PID1 starts a persistent internal-modem lifecycle owner that opens only `/dev/subsys_modem` and records `/cache/native-init-wifi-lifecycle-modem-owner.*`.",
        "- Added: PID1 starts a lightweight Wi-Fi runtime summary sampler at `/cache/native-init-wifi-runtime.summary`; the HUD consumes it for Wi-Fi MAC/IP/RX/TX state and optional SSID/RSSI/link-speed labels.",
        "",
        "## Safety Scope",
        "",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.",
        "- The live validation remains credential-redacted and rollbackable to `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`.",
        "",
    ])


def normalize_manifest_axes() -> None:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("cycle") == "V726":
        manifest["legacy_cycle_field"] = "V726"
        manifest["cycle"] = None
    manifest["baseline_tag"] = "v726-wifi-lifecycle"
    manifest["version_axes"] = {
        "baseline_tag": "v726-wifi-lifecycle",
        "helper_version": "helper-v427",
        "supporting_run_ids": ["V2167", "V2168"],
        "note": "V726 is a boot/init baseline tag, not a global run ID.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def main() -> int:
    configure_base()
    base = base_module()
    helper_builder = (
        v2168.prev2137.prev2135.prev2133.prev2131.prev2129.prev2127.prev2120
        .prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095
        .prev2082.prev2080.prev2058.prev2038
    )
    helper_builder.patch_helper_builder(base)
    base.render_report = render_report
    rc = base.main()
    if rc == 0:
        normalize_manifest_axes()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
