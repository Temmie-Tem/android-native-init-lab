#!/usr/bin/env python3
"""Immutable host-only R4W1-E0 build artifact identities."""

from __future__ import annotations


SCHEMA = "s22plus_fyg8_r4w1e0_build_artifact_contract_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

IMAGE_SIZE = 41_490_944
IMAGE_SHA256 = "54d637f9ee018e9daac017847c1a233dfa8913c20830a357ea597baf3f9232f9"

KERNEL_BUILD_RESULT_SIZE = 692_896
KERNEL_BUILD_RESULT_SHA256 = (
    "3303a528229d2b6e79e8b4393e7b7d1fd80a9e8ba489991b214bd554e8035857"
)


def matches(*, size: int, sha256: str, expected_size: int, expected_sha256: str) -> bool:
    return size == expected_size and sha256 == expected_sha256
