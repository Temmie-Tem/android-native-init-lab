#!/usr/bin/env python3
"""V1870 rollbackable handoff for V1869 private SDX50M summary boot."""

from __future__ import annotations

from pathlib import Path

import native_wifi_sdx50m_private_mount_handoff_v1864 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
V1869_OUT = REPO_ROOT / "tmp" / "wifi" / "v1869-sdx50m-private-mount-summary-test-boot"


def configure_constants() -> None:
    base.CYCLE = "V1870"
    base.V1863_OUT = V1869_OUT
    base.REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1869/dev/__properties__"
    base.DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1870-sdx50m-private-mount-summary-handoff"
    base.DEFAULT_REPORT_PATH = (
        REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1870_SDX50M_PRIVATE_MOUNT_SUMMARY_HANDOFF_2026-06-03.md"
    )
    base.TEST_EXPECT_VERSION = "A90 Linux init 0.9.169 (v1869-sdx50m-private-mount-summary)"
    base.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1869.log"
    base.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1869.summary"
    base.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1869-helper.result"
    base.TEST_IMAGE = V1869_OUT / "boot_linux_v1869_sdx50m_private_mount_summary.img"
    base.DMESG_PATTERN = base.DMESG_PATTERN.replace("A90v1863", "A90v1869")


def main(argv: list[str] | None = None) -> int:
    configure_constants()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
