#!/usr/bin/env python3
"""Canonical Linux banner extraction for pinned S22+ FYG8 kernel evidence."""

from __future__ import annotations

import re


CANONICAL_LINUX_BANNER_RE = re.compile(rb"Linux version [^\x00\n]+")
LINUX_RELEASE_RE = re.compile(r"^Linux version ([^\s]+)")


def extract_linux_banner(data: bytes) -> str | None:
    """Return the exact banner bytes before LF/NUL without normalization."""
    match = CANONICAL_LINUX_BANNER_RE.search(data)
    if match is None:
        return None
    try:
        return match.group(0).decode("ascii")
    except UnicodeDecodeError:
        return None


def extract_linux_release(banner: str) -> str | None:
    match = LINUX_RELEASE_RE.match(banner)
    return match.group(1) if match else None
