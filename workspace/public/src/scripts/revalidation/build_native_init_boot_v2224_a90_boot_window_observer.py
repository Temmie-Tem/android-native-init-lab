#!/usr/bin/env python3
"""Build V2224 a90 boot-window observer test boot.

This is a host-only source/build wrapper. It keeps the V2189 security/transport
baseline and changes the supervised Wi-Fi helper route to the a90 CNSS/WLFW
output-visibility trace_uprobe observer needed by V2223.
"""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2189_security_p0_stage_fix as v2189
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2224-a90-boot-window-observer")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2224_A90_BOOT_WINDOW_OBSERVER_SOURCE_BUILD_2026-06-12.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2224_a90_boot_window_observer.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2224_a90_boot_window_observer"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2224_a90_boot_window_observer.cpio"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2224/dev/__properties__"
EXPECTED_HELPER_MARKER = v2189.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = v2189.EXPECTED_HELPER_SHA256
EXTRA_INIT_FLAGS = v2189.EXTRA_INIT_FLAGS
HELPER_MODE = "wlan-pd-cnss-output-visibility"
HELPER_RUNTIME_MODE = "wifi-companion-wlan-pd-cnss-output-visibility-start-only"


def base_module():
    return v2189.base_module()


def configure_base() -> None:
    v2189.OUT_DIR = OUT_DIR
    v2189.REPORT_PATH = REPORT_PATH
    v2189.BOOT_IMAGE = BOOT_IMAGE
    v2189.INIT_BINARY = INIT_BINARY
    v2189.RAMDISK_CPIO = RAMDISK_CPIO
    v2189.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    v2189.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2224",
        "--decision": "v2224-a90-boot-window-observer-source-build-pass",
        "--cycle-label": "v2224",
        "--init-version": "0.9.262",
        "--init-build": "v2224-a90-boot-window-observer",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v427_a90_boot_window_observer"),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2224",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2224.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2224.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2224.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2224-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2224.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2224-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode": HELPER_MODE,
        "--wifi-test-watch-sec": "70",
        "--wifi-test-supervisor-timeout-sec": "95",
    }
    for key, value in replacements.items():
        v2189.v2188.v2187.v2182.v2178.v2176.v2174.v2169.v726.set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V2224 A90 Boot-Window Observer Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2224`",
        "- Type: source/build-only rollbackable observer test boot.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V2224 keeps the V2189 security P0 baseline and changes the supervised early helper route to the V2223 a90 CNSS/WLFW trace_uprobe boot-window observer.",
        "- Manifest: `workspace/private/builds/native-init/v2224-a90-boot-window-observer/manifest.json`",
        f"- Base boot: `{manifest['base_boot']}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Observer Route",
        "",
        f"- Helper mode: `{wifi['helper_mode']}`",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Supervisor timeout: `{wifi['supervisor_timeout_sec']}`",
        f"- Watch window: `{wifi['watch_sec']}` seconds",
        f"- Helper result: `{wifi['helper_result']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Expected parsed sequence: `wlfw_start -> wlfw_service_request -> wlfw_cap_qmi -> wlfw_bdf_entry`.",
        "",
        "## Safety Scope",
        "",
        "- This build script is host-only and does not flash, reboot, scan/connect Wi-Fi, use credentials, configure DHCP/routes, ping, attach BPF, execute `probe_write_user`, or write device partitions.",
        "- The eventual live run still requires explicit approval and should immediately postprocess the helper result with `a90_kernel_v2220_helper_summary_trace_parser.py`.",
        "- Keep the V2222/V2223 blocks: no dynamic `a90*` BPF attach, no PMIC/GPIO/GDSC/eSoC/PCI path, no platform bind/unbind, and no `sda29` writes.",
        "",
    ])


def normalize_manifest_axes() -> None:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["candidate_tag"] = "v2224-a90-boot-window-observer"
    manifest["parent_baseline"] = "v2189-security-p0-stage-fix"
    manifest["rollback_baseline"] = "v2189-security-p0-stage-fix"
    manifest["promoted_baseline"] = False
    manifest["version_axes"] = {
        "candidate_tag": "v2224-a90-boot-window-observer",
        "parent_baseline": "v2189-security-p0-stage-fix",
        "rollback_baseline": "v2189-security-p0-stage-fix",
        "helper_version": "helper-v427",
        "run_id": "V2224",
        "note": "V2224 is a rollbackable observer test boot for approved V2225 boot-window a90 trace capture.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def main() -> int:
    configure_base()
    base = base_module()
    helper_builder = (
        v2189.v2188.v2187.v2182.v2178.v2176.v2174.v2169.v726.v2168.prev2137.prev2135.prev2133.prev2131
        .prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102
        .prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038
    )
    helper_builder.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    helper_builder.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    helper_builder.patch_helper_builder(base)
    base.render_report = render_report
    created_legacy_link = v2189.v2188.v2187.v2182.v2178.v2176.v2174.v2169.ensure_legacy_mkbootimg_link()
    try:
        rc = base.main()
        if rc == 0:
            normalize_manifest_axes()
            REPORT_PATH.chmod(0o644)
        return rc
    finally:
        if created_legacy_link and v2189.v2188.v2187.v2182.v2178.v2176.v2174.v2169.LEGACY_MKBOOTIMG_DIR.is_symlink():
            v2189.v2188.v2187.v2182.v2178.v2176.v2174.v2169.LEGACY_MKBOOTIMG_DIR.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
