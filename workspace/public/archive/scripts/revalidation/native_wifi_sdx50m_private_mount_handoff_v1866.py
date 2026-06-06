#!/usr/bin/env python3
"""V1866 rollbackable handoff for V1865 private SDX50M routefix boot."""

from __future__ import annotations

from pathlib import Path

import native_wifi_sdx50m_private_mount_handoff_v1864 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
V1865_OUT = REPO_ROOT / "tmp" / "wifi" / "v1865-sdx50m-private-mount-routefix-test-boot"


def configure_constants() -> None:
    base.CYCLE = "V1866"
    base.V1863_OUT = V1865_OUT
    base.REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1865/dev/__properties__"
    base.DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1866-sdx50m-private-mount-routefix-handoff"
    base.DEFAULT_REPORT_PATH = (
        REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1866_SDX50M_PRIVATE_MOUNT_ROUTEFIX_HANDOFF_2026-06-03.md"
    )
    base.TEST_EXPECT_VERSION = "A90 Linux init 0.9.167 (v1865-sdx50m-private-mount-routefix)"
    base.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1865.log"
    base.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1865.summary"
    base.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1865-helper.result"
    base.TEST_IMAGE = V1865_OUT / "boot_linux_v1865_sdx50m_private_mount_routefix.img"
    base.DMESG_PATTERN = base.DMESG_PATTERN.replace("A90v1863", "A90v1865")


def main(argv: list[str] | None = None) -> int:
    configure_constants()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
