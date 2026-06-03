#!/usr/bin/env python3
"""Build V1867 unconditional-argv private SDX50M mount test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1865 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1867-sdx50m-private-mount-argvfix-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1867/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1867_SDX50M_PRIVATE_MOUNT_ARGVFIX_SOURCE_BUILD_2026-06-03.md"
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
        "# Native Init V1867 SDX50M Private Mount Argvfix Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1867`",
        "- Type: source/build-only rollbackable v356 lower-state observer with private SDX50M cnss-daemon bind mount appended unconditionally when the private-mount macro is enabled",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V1864 and V1866 both rolled back safely but emitted no `private_cnss_daemon.*` fields; V1867 keeps the active branch patches and also appends the private mount arguments at the common helper argv tail.",
        "- Manifest: `tmp/wifi/v1867-sdx50m-private-mount-argvfix-test-boot/manifest.json`",
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
        "- PID1 now carries the private mount arguments in the common helper argv tail for this macro-enabled build, avoiding branch-selection ambiguity.",
        "- The private mount remains namespace-local; it does not write `/vendor` and depends on the remote cache artifact already verified by V1862.",
        f"- PM-service open-context labels retained: {labels}.",
        "- Lower-state observer guardrails remain: no direct `/dev/subsys_esoc0` open, no fake ONLINE, no eSoC notify/BOOT_DONE, no forced RC1, no PCI rescan/bind, no PMIC/GPIO/GDSC writes, no Wi-Fi HAL, no scan/connect, no credentials, no DHCP/routes, and no external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- `private-mount-bind-failed`: active argv still failed to materialize the namespace-local bind mount; stop before live bridge interpretation.",
        "- `private-mount-sdx50m-selected`: SDX50M private daemon path executed and changed PM selection; inspect lower publication before connect.",
        "- `private-mount-lower-publication-progress`: WLFW service 69, BDF, MHI, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.",
        "- `private-mount-pre-wifi-gap`: private mount works but WLFW service 69 and `wlan0` still remain absent.",
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
        arg.replace("V1865", "V1867")
        .replace("v1865", "v1867")
        .replace("0.9.167", "0.9.168")
        .replace("sdx50m-private-mount-routefix", "sdx50m-private-mount-argvfix")
        .replace("sdx50m_private_mount_routefix", "sdx50m_private_mount_argvfix")
        for arg in builder.DEFAULT_ARGS
    ]
    builder.DEFAULT_ARGS = [
        arg.replace(str(base.OUT_DIR), str(OUT_DIR)).replace(base.REMOTE_PROPERTY_ROOT, REMOTE_PROPERTY_ROOT)
        for arg in builder.DEFAULT_ARGS
    ]
    builder.render_report = render_report
    return builder.main()


if __name__ == "__main__":
    raise SystemExit(main())
