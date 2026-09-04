"""Retain first-OPEN failure diagnostics through the real session reader.

Install only on an isolated, already source-bound initial observer module.
The original reader, writer, deadline and failure parser remain the owners.
After stage 3 / code 1 or 4, read at most four existing 24-byte diagnostic
frames before returning that original rejected frame to the failure parser.
No transmission, reconnection, new deadline or successful proof is added.
"""

from __future__ import annotations

import types
from typing import Any


def install(initial: types.ModuleType) -> None:
    """Give one private initial observer a bounded failure-suffix reader."""
    codec = initial._CODEC
    runtime = initial.runtime
    header = initial.HEADER
    diagnostic = initial.DIAGNOSTIC
    if header.size != 16 or diagnostic.size != 8:
        raise ValueError("OPEN diagnostic capture requires the existing 16/8 ABI")
    if getattr(codec, "_open_failure_capture_installed", False):
        raise ValueError("OPEN diagnostic capture is already installed")

    def read_frame(
        descriptor: int, deadline: float, audit: Any, writer: Any
    ) -> Any:
        frame = codec._read_frame(descriptor, deadline, audit, writer)
        if (
            audit.current_stage != "open-diagnostic-read"
            or frame.frame_type != runtime.DIAGNOSTIC_FRAME_TYPE
            or frame.sequence != 0
            or len(frame.payload) != diagnostic.size
        ):
            return frame
        stage, code = diagnostic.unpack(frame.payload)
        if stage != 3 or code not in (1, 4):
            return frame

        # Failure is already established. Keep any partial suffix through the
        # same raw sink; the original stage-1 parser still rejects stage 3.
        for expected_stage in (4, 5, 6, 7):
            try:
                raw_header = codec._read_exact(
                    descriptor, header.size, deadline, audit, writer
                )
                magic, version, kind, size, sequence, _crc = header.unpack(raw_header)
                if (
                    magic != runtime.FRAME_MAGIC
                    or version != runtime.FRAME_VERSION
                    or kind != runtime.DIAGNOSTIC_FRAME_TYPE
                    or size != diagnostic.size
                    or sequence != 0
                ):
                    break
                payload = codec._read_exact(
                    descriptor, diagnostic.size, deadline, audit, writer
                )
                suffix = codec.decode_frame(raw_header + payload)
                if diagnostic.unpack(suffix.payload)[0] != expected_stage:
                    break
            except (TimeoutError, OSError, codec.AuthObserverError):
                # Timeout, EOF or an invalid suffix does not erase the
                # original failure frame or bytes already retained.
                break
        return frame

    # Never mutate the shared predecessor codec used by other campaigns.
    private_codec = types.ModuleType(f"{initial.__name__}_failure_capture_codec")
    private_codec.__dict__.update(vars(codec))
    private_codec._read_frame = read_frame
    private_codec._open_failure_capture_installed = True
    initial._CODEC = private_codec
