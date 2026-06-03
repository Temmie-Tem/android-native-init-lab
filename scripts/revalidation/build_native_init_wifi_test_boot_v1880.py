#!/usr/bin/env python3
"""Build V1880 delayed lower-response read-only sampler test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1865 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1880-delayed-lower-readonly-sampler-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1880/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v358"
EXPECTED_HELPER_SHA256 = "1d6cb4bb16e1b35b86eb0a76381f1651a72d87d760756f33562efe2aeef5d7cc"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1880_DELAYED_LOWER_READONLY_SAMPLER_SOURCE_BUILD_2026-06-03.md"
)


def replace_option(args: list[str], option: str, value: str) -> None:
    for index, arg in enumerate(args):
        if arg == option and index + 1 < len(args):
            args[index + 1] = value
            return
    raise RuntimeError(f"missing option: {option}")


def configure_constants() -> None:
    base.OUT_DIR = OUT_DIR
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.REPORT_PATH = REPORT_PATH


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    labels = ", ".join(f"`{label}`" for label in base.prev1846.OPEN_CONTEXT_LABELS)
    return "\n".join([
        "# Native Init V1880 Delayed Lower Read-only Sampler Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1880`",
        "- Type: source/build-only rollbackable v358 delayed lower-response sampler on the private SDX50M post-PM route",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V1879 selected a delayed read-only window because Android-good lower publication appears around 205-216 seconds after `wlfw_start`, while V1876 only sampled 0-1000 ms after private SDX50M PM powerup.",
        "- Manifest: `tmp/wifi/v1880-delayed-lower-readonly-sampler-test-boot/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        f"- Private CNSS mount: `{wifi['private_cnss_daemon_sdx50m']}` path `{wifi['private_cnss_daemon_path']}`",
        "- New helper marker: `a90_android_execns_probe v358`.",
        "- New output namespace: `wlan_pd_lower_response_input_contract.post_powerup_delayed.*`.",
        "- Dense offsets retained: `0,1,2,5,10,20,50,100,150,250,500,1000 ms`.",
        "- Delayed offsets added: `0,1,2,5,10,20,30,60,90,120,150,180,210,240,250,260,300 s`.",
        f"- PID1 watch/supervisor seconds: `{wifi['watch_sec']}` / `{wifi['supervisor_timeout_sec']}`.",
        "- Each delayed sample reuses existing read-only lower-state and PM/eSoC/GPIO/GDSC/PCIe/MHI/ks surfaces; it does not write rc_sel/case, rescan PCI, bind/unbind, or directly open `/dev/subsys_esoc0`.",
        f"- PM-service open-context labels retained: {labels}.",
        "",
        "## Expected Live Discriminator",
        "",
        "- `delayed-lower-wifi-prereq-present-readonly-stop`: WLFW service 69 and `wlan0` both exist; run a separate connect prerequisite check before credentials.",
        "- `delayed-lower-mhi-or-wlfw-progress-readonly-stop`: MHI, WLFW service 69, BDF, firmware-ready, or `wlan0` appears; stop before connect.",
        "- `delayed-lower-pcie-l0-no-wlfw-readonly-stop`: PCIe/MHI moves but WLFW/`wlan0` remain absent.",
        "- `delayed-lower-still-power-clock-gap`: no lower progress appears across the Android-good 300 second delayed window.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_constants()
    base.configure_base()
    builder = base.prev1846.prev1792.prev1790.prev1783.prev
    builder.DEFAULT_ARGS = [
        arg.replace("V1865", "V1880")
        .replace("v1865", "v1880")
        .replace("0.9.167", "0.9.171")
        .replace("sdx50m-private-mount-routefix", "delayed-lower-readonly-sampler")
        .replace("sdx50m_private_mount_routefix", "delayed_lower_readonly_sampler")
        .replace("a90_android_execns_probe_v356", "a90_android_execns_probe_v358")
        for arg in builder.DEFAULT_ARGS
    ]
    replace_option(builder.DEFAULT_ARGS, "--wifi-test-watch-sec", "330")
    replace_option(builder.DEFAULT_ARGS, "--wifi-test-supervisor-timeout-sec", "360")
    builder.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    builder.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    builder.render_report = render_report
    return builder.main()


if __name__ == "__main__":
    raise SystemExit(main())
