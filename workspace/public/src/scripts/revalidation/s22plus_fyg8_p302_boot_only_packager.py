#!/usr/bin/env python3
"""Deterministic boot-only packaging primitive for P3.02-M0."""

from __future__ import annotations

from pathlib import Path

import s22plus_fyg8_p286_boot_only_packager as base


SCHEMA = "s22plus_fyg8_p302_boot_only_package_v1"
VERDICT = "PASS_P302_DETERMINISTIC_BOOT_ONLY_PACKAGE_HOST_ONLY"
PackageError = base.PackageError


def package(*, boot_path: Path, lz4_path: Path, output_dir: Path, audit_dir: Path):
    previous = (base.SCHEMA, base.VERDICT)
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    try:
        return base.package(
            boot_path=boot_path,
            lz4_path=lz4_path,
            output_dir=output_dir,
            audit_dir=audit_dir,
        )
    finally:
        base.SCHEMA, base.VERDICT = previous
