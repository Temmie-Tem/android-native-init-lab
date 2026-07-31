#!/usr/bin/env python3
"""Deterministic boot-only packaging primitive for P2.94."""

from __future__ import annotations

from pathlib import Path

import s22plus_fyg8_p286_boot_only_packager as base


SCHEMA = "s22plus_fyg8_p294_boot_only_package_v1"
VERDICT = "PASS_P294_DETERMINISTIC_BOOT_ONLY_PACKAGE_HOST_ONLY"
PackageError = base.PackageError


def _configure() -> None:
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT


def package(*, boot_path: Path, lz4_path: Path, output_dir: Path, audit_dir: Path):
    _configure()
    return base.package(
        boot_path=boot_path,
        lz4_path=lz4_path,
        output_dir=output_dir,
        audit_dir=audit_dir,
    )
