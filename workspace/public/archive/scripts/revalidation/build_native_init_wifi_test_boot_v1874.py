#!/usr/bin/env python3
"""Build V1874 lower-response read-only sampler test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1865 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1874-lower-response-readonly-sampler-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1874/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v357"
EXPECTED_HELPER_SHA256 = "8ec9d4153e5dcc966888170bfef0c3428f2261b30c0e58836697c91442386d87"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1874_LOWER_RESPONSE_READONLY_SAMPLER_SOURCE_BUILD_2026-06-03.md"
)


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
        "# Native Init V1874 Lower Response Read-only Sampler Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1874`",
        "- Type: source/build-only rollbackable v357 lower-response input sampler on the private SDX50M post-PM route",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V1873 selected the next source/build-only contract: extend the private SDX50M post-PM lower observer with a dense read-only lower-response input window before any new mutation or Wi-Fi connect attempt.",
        "- Manifest: `tmp/wifi/v1874-lower-response-readonly-sampler-test-boot/manifest.json`",
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
        "- New helper marker: `a90_android_execns_probe v357`.",
        "- New output namespace: `wlan_pd_lower_response_input_contract.post_powerup_dense.*`.",
        "- Dense offsets: `0,1,2,5,10,20,50,100,150,250,500,1000 ms`.",
        "- Each sample reuses existing read-only lower-state and PM/eSoC/GPIO/GDSC/PCIe/MHI/ks surfaces; it does not write rc_sel/case, rescan PCI, bind/unbind, or directly open `/dev/subsys_esoc0`.",
        f"- PM-service open-context labels retained: {labels}.",
        "",
        "## Expected Live Discriminator",
        "",
        "- `lower-input-mdm2ap-silent`: private SDX50M path selected, but GPIO142/MDM2AP and PCIe/MHI/WLFW stay silent.",
        "- `lower-input-rc1-natural-attempt-no-l0`: natural PCIe/RC1 state changes appear but no L0/MHI/WLFW publication follows.",
        "- `lower-input-power-clock-snapshot-gap`: pcie1 GDSC/clock/regulator read-only samples stay different from Android-good evidence.",
        "- `lower-input-mhi-or-wlfw-progress-readonly-stop`: MHI, WLFW service 69, BDF, firmware-ready, or `wlan0` appears; stop before connect.",
        "- `lower-input-wifi-prereq-present-readonly-stop`: WLFW service 69 and `wlan0` both exist; only then plan Wi-Fi HAL/connect.",
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
        arg.replace("V1865", "V1874")
        .replace("v1865", "v1874")
        .replace("0.9.167", "0.9.170")
        .replace("sdx50m-private-mount-routefix", "lower-response-readonly-sampler")
        .replace("sdx50m_private_mount_routefix", "lower_response_readonly_sampler")
        .replace("a90_android_execns_probe_v356", "a90_android_execns_probe_v357")
        for arg in builder.DEFAULT_ARGS
    ]
    builder.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    builder.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    builder.render_report = render_report
    return builder.main()


if __name__ == "__main__":
    raise SystemExit(main())
