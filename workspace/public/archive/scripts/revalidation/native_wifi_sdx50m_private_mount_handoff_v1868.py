#!/usr/bin/env python3
"""V1868 rollbackable handoff for V1867 private SDX50M argvfix boot."""

from __future__ import annotations

from pathlib import Path

import native_wifi_sdx50m_private_mount_handoff_v1864 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
V1867_OUT = REPO_ROOT / "tmp" / "wifi" / "v1867-sdx50m-private-mount-argvfix-test-boot"


def configure_constants() -> None:
    base.CYCLE = "V1868"
    base.V1863_OUT = V1867_OUT
    base.REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1867/dev/__properties__"
    base.DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1868-sdx50m-private-mount-argvfix-handoff"
    base.DEFAULT_REPORT_PATH = (
        REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1868_SDX50M_PRIVATE_MOUNT_ARGVFIX_HANDOFF_2026-06-03.md"
    )
    base.TEST_EXPECT_VERSION = "A90 Linux init 0.9.168 (v1867-sdx50m-private-mount-argvfix)"
    base.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1867.log"
    base.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1867.summary"
    base.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1867-helper.result"
    base.TEST_IMAGE = V1867_OUT / "boot_linux_v1867_sdx50m_private_mount_argvfix.img"
    base.DMESG_PATTERN = base.DMESG_PATTERN.replace("A90v1863", "A90v1867")


def main(argv: list[str] | None = None) -> int:
    configure_constants()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
