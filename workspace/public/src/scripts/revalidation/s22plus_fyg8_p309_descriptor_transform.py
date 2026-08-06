#!/usr/bin/env python3
"""Correct the P3.08 QSCRATCH tracefs register spelling in a successor source."""

from __future__ import annotations

from typing import Mapping


class TransformError(ValueError):
    pass


ARTIFACT_KEY = "trace_descriptor_header"
_OLD = (
    b'{"p307_qscratch", "p:p282/p307_qscratch '
    b'dwc3_msm:dwc3_otg_start_peripheral+0x4cc rc=%w21:s32\\n", '
    b'"common_pid >= 0"}'
)
_NEW = _OLD.replace(b"rc=%w21:s32", b"rc=%x21:s32")


def transform_descriptor(data: bytes) -> bytes:
    if data.count(_OLD) != 1 or _NEW in data:
        raise TransformError("P3.09 inherited QSCRATCH descriptor differs")
    value = data.replace(_OLD, _NEW, 1)
    if value.count(b"rc=%x21:s32") != 1 or b"rc=%w21:s32" in value:
        raise TransformError("P3.09 corrected QSCRATCH descriptor differs")
    return value


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    if ARTIFACT_KEY not in source:
        raise TransformError("P3.09 trace descriptor artifact is absent")
    result = dict(source)
    result[ARTIFACT_KEY] = transform_descriptor(source[ARTIFACT_KEY])
    changed = {key for key in result if result[key] != source[key]}
    if changed != {ARTIFACT_KEY}:
        raise TransformError(f"P3.09 artifact delta differs: {sorted(changed)}")
    return result
