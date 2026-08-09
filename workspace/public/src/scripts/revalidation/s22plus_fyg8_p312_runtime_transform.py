#!/usr/bin/env python3
"""Repair only the P3.11 early profile/record relation for P3.12."""

from __future__ import annotations

from typing import Mapping


class TransformError(ValueError):
    pass


_OLD = b"        if (control->profile_hits[index] != record_hits[index]) {\n"
_NEW = b"        if (control->profile_hits[index] < record_hits[index]) {\n"


def transform_runtime_include(data: bytes) -> bytes:
    if data.count(_OLD) != 1 or _NEW in data:
        raise TransformError("P3.12 profile relation anchor differs")
    return data.replace(_OLD, _NEW, 1)


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    result = dict(source)
    result["p290_e3_runtime_include"] = transform_runtime_include(
        source["p290_e3_runtime_include"]
    )
    changed = {key for key in result if result[key] != source[key]}
    if changed != {"p290_e3_runtime_include"}:
        raise TransformError(f"P3.12 delta differs: {sorted(changed)}")
    return result
