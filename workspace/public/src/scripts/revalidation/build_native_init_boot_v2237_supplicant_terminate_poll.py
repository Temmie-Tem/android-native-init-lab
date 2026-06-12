#!/usr/bin/env python3
"""Build V2237 supplicant terminate-poll validation boot.

This source/build wrapper keeps the V2230 service-object-visible route that
reached WLFW cap/BDF QMI, then enables the previously verified V2137
post-FW_READY boot_wlan + firmware_class feeder tail for this route only.
"""

from __future__ import annotations

import json
import shlex
import tempfile
from pathlib import Path

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2230_service_object_visible_post_bdf_hold as v2230
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2237-supplicant-terminate-poll")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2237_SUPPLICANT_TERMINATE_POLL_SOURCE_BUILD_2026-06-12.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2237_supplicant_terminate_poll.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2237_supplicant_terminate_poll"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2237_supplicant_terminate_poll.cpio"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v726/dev/__properties__"
EXPECTED_HELPER_MARKER = v2230.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = "062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910"
EXTRA_INIT_FLAGS = v2230.EXTRA_INIT_FLAGS
HELPER_MODE = v2230.HELPER_MODE
HELPER_RUNTIME_MODE = v2230.HELPER_RUNTIME_MODE
SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = (
    "-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1"
)
THIRD_PARTY_MKBOOTIMG = REPO_ROOT / "workspace" / "public" / "src" / "third_party" / "mkbootimg"


def base_module():
    return v2230.base_module()


def helper_chain():
    return (
        v2230.v2189.v2188.v2187.v2182.v2178.v2176.v2174.v2169.v726
        .v2168.prev2137
    )


def helper_builder_module():
    prev2137 = helper_chain()
    return (
        prev2137.prev2135.prev2133.prev2131.prev2129.prev2127.prev2120
        .prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095
        .prev2082.prev2080.prev2058.prev2038
    )


def with_bridge_flag(flags: tuple[str, ...]) -> tuple[str, ...]:
    return (*tuple(flag for flag in flags if flag != SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG),
            SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG)


def configure_helper_flags() -> tuple[str, ...]:
    prev2137 = helper_chain()
    helper_flags = with_bridge_flag(prev2137.HELPER_FLAGS)
    prev2137.HELPER_FLAGS = helper_flags
    prev2137.prev2135.HELPER_FLAGS = helper_flags
    prev2137.prev2135.prev2133.prev2131.HELPER_FLAGS = helper_flags
    helper_builder_module().HELPER_FLAGS = helper_flags
    return helper_flags


def configure_base() -> tuple[str, ...]:
    helper_flags = configure_helper_flags()
    v2230.OUT_DIR = OUT_DIR
    v2230.REPORT_PATH = REPORT_PATH
    v2230.BOOT_IMAGE = BOOT_IMAGE
    v2230.INIT_BINARY = INIT_BINARY
    v2230.RAMDISK_CPIO = RAMDISK_CPIO
    v2230.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    v2230.configure_base()
    helper_flags = configure_helper_flags()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2237",
        "--decision": "v2237-supplicant-terminate-poll-source-build-pass",
        "--cycle-label": "v2237",
        "--init-version": "0.9.268",
        "--init-build": "v2237-supplicant-terminate-poll",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v430_supplicant_terminate_poll"),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2237",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2237.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2237.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2237.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2237-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2237.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2237-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode": HELPER_MODE,
        "--wifi-test-watch-sec": "180",
        "--wifi-test-supervisor-timeout-sec": "215",
    }
    for key, value in replacements.items():
        v2230.v2189.v2188.v2187.v2182.v2178.v2176.v2174.v2169.v726.set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    return helper_flags


def patch_mkbootimg_tools(base_wrapper) -> None:
    build_base = base_wrapper.base

    def build_boot_image(args) -> None:
        with tempfile.TemporaryDirectory(prefix="a90-v2237-unpack-") as temp_name:
            temp_dir = Path(temp_name)
            unpack_args = build_base.run(
                [
                    "python3",
                    THIRD_PARTY_MKBOOTIMG / "unpack_bootimg.py",
                    "--boot_img",
                    args.base_boot,
                    "--out",
                    temp_dir,
                    "--format=mkbootimg",
                ],
                capture=True,
            ).stdout
            mkboot_args = shlex.split(unpack_args)

            for index, item in enumerate(mkboot_args):
                if item == "--ramdisk":
                    mkboot_args[index + 1] = str(args.ramdisk_cpio)
                    break
            else:
                raise RuntimeError("base boot image mkbootimg args did not include --ramdisk")

            if args.boot_image.exists():
                args.boot_image.unlink()
            build_base.run([
                "python3",
                THIRD_PARTY_MKBOOTIMG / "mkbootimg.py",
                *mkboot_args,
                "--output",
                args.boot_image,
            ])
        args.boot_image.chmod(0o600)

    build_base.build_boot_image = build_boot_image


def render_report(manifest: dict[str, object], helper_flags: tuple[str, ...]) -> str:
    wifi = manifest["wifi_test"]
    helper_flag_lines = [f"- `{flag}`" for flag in helper_flags]
    return "\n".join([
        "# Native Init V2237 Supplicant Terminate Poll Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2237`",
        "- Type: source/build-only rollbackable Wi-Fi profile-switch hardening test boot.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: GOAL.md names the V2236 strict-connect terminate race as the next bounded frontier: replace the blind 500 ms post-`TERMINATE` delay with a bounded wait for the old supplicant to exit plus SIGKILL escalation before the next profile starts.",
        "- Manifest: `workspace/private/builds/native-init/v2237-supplicant-terminate-poll/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Kept from V2230: service-object-visible service-manager/PM route, provider-visible startup, internal modem holder, WLFW cap/BDF focused uprobes, long post-BDF hold.",
        "- Kept from V2232: `A90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`, allowing service-object mode to run the already compile-gated V2137 post-FW_READY `boot_wlan` trigger and QCACLD firmware_class feeder.",
        "- Kept from V2236: stale `wpa_supplicant` is not reused across `wifi connect`, and connect success still requires carrier plus `ctrl.status_confirm.field.wpa_state=COMPLETED`.",
        "- Added for this build: existing supplicant shutdown now emits `supplicant.existing_terminate_wait_*` fields, polls up to 3000 ms for clean exit, escalates with SIGKILL when needed, emits `supplicant.existing_kill_*` fields, and refuses to start the new profile with `wifi-connect-supplicant-terminate-timeout` if the old process remains.",
        "",
        "## Helper Flags",
        "",
        *helper_flag_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. The live validation is rollbackable. It permits explicit bounded native Wi-Fi scan/connect/DHCP/ping only under stored private profiles, keeps secret redaction, and still excludes Wi-Fi HAL/framework control, credential logging, eSoC/PCIe/GDSC/PMIC/GPIO writes, platform bind/unbind, module load/unload, `/dev/subsys_esoc0`, and sda29 writes.",
        "",
    ])


def main() -> int:
    helper_flags = configure_base()
    helper_builder = helper_builder_module()
    helper_builder.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    helper_builder.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    base = base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    helper_builder.patch_helper_builder(base)
    patch_mkbootimg_tools(base)
    base.render_report = lambda manifest: render_report(manifest, helper_flags)
    rc = base.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["candidate_tag"] = "v2237-supplicant-terminate-poll"
    manifest["helper_flags"] = list(helper_flags)
    manifest["service_object_fwclass_bridge_flag"] = SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
    manifest["wifi_connect_change"] = "bounded-supplicant-terminate-poll-plus-sigkill"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    BOOT_IMAGE.parent.mkdir(parents=True, exist_ok=True)
    promotion_path = OUT_DIR / "promotion-candidate.json"
    promotion_path.write_text(json.dumps({
        "candidate_tag": "v2237-supplicant-terminate-poll",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest["helper_sha256"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "note": "V2237 keeps the V2236 WLAN route and replaces blind supplicant terminate sleep with bounded poll plus SIGKILL escalation.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
