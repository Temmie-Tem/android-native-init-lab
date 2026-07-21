#!/usr/bin/env python3
"""Immutable host-only R4W1-E build artifact identities for P2.9."""

from __future__ import annotations


SCHEMA = "s22plus_fyg8_r4w1e_build_artifact_contract_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

IMAGE_SIZE = 41_490_944
IMAGE_SHA256 = "b45b87beab49b65a8212468178ff440004a20e76ff2e5564a271f47ff6dd80c8"

KERNEL_BUILD_RESULT_SIZE = 703_813
KERNEL_BUILD_RESULT_SHA256 = (
    "0ac93b9adb9e7b02c04f5f7c2109bcfb8b7088b7ed6b98baf81e8e5fd2f4eee3"
)


def matches(*, size: int, sha256: str, expected_size: int, expected_sha256: str) -> bool:
    return size == expected_size and sha256 == expected_sha256
