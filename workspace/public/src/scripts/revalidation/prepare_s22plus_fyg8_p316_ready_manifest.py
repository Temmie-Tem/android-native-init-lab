#!/usr/bin/env python3
"""Create or rehearse one verified Process-v2 ready manifest for P3.16."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import prepare_s22plus_fyg8_p292_ready_manifest as base
import s22plus_fyg8_p316_overlay_contract as overlay


SCHEMA = "s22plus_fyg8_p316_ready_manifest_builder_v1"
VERDICT = "PASS_P316_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P316_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
SOURCE_CONTRACT_ID = overlay.PARENT_SOURCE_CONTRACT_ID
USERSPACE_OVERLAY_CONTRACT_ID = overlay.CONTRACT_ID
DEFAULT_CANDIDATE_STATIC = Path(
    "workspace/private/device-action/s22plus_fyg8_p316_ready_1/"
    "evidence/candidate-static.json"
)
DEFAULT_RUN_MANIFEST = Path(
    "workspace/private/device-action/s22plus_fyg8_p316_ready_1/"
    "evidence/run-manifest.json"
)
DEFAULT_STATIC_CHECK = Path(
    "workspace/private/device-action/s22plus_fyg8_p316_ready_1/"
    "evidence/static-check-result.json"
)
DEFAULT_CANDIDATE_AP = Path(
    "workspace/private/device-action/s22plus_fyg8_p316_ready_1/"
    "candidate/AP.tar.md5"
)
DEFAULT_ROLLBACK_AP = base.DEFAULT_ROLLBACK_AP
DEFAULT_OUT = Path(
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p316_process_v2_ready_1.json"
)
DEFAULT_TARGET_PROFILE = base.DEFAULT_TARGET_PROFILE
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p316-process-v2-ready-1"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p316-live-1"
DEFAULT_TIMEOUT_SEC = base.DEFAULT_TIMEOUT_SEC
ManifestError = base.ManifestError
_CONFIGURATION_FIELDS = (
    "__doc__", "SCHEMA", "VERDICT", "REHEARSAL_VERDICT",
    "SOURCE_CONTRACT_ID", "USERSPACE_OVERLAY_CONTRACT_ID",
    "DEFAULT_CANDIDATE_STATIC", "DEFAULT_RUN_MANIFEST", "DEFAULT_STATIC_CHECK",
    "DEFAULT_CANDIDATE_AP", "DEFAULT_ROLLBACK_AP", "DEFAULT_OUT",
    "DEFAULT_TARGET_PROFILE", "DEFAULT_MANIFEST_ID", "DEFAULT_LIVE_RUN_ID",
    "DEFAULT_TIMEOUT_SEC",
)


def _apply_configuration() -> None:
    for name in _CONFIGURATION_FIELDS:
        setattr(base, name, __doc__ if name == "__doc__" else globals()[name])


@contextmanager
def _configuration_context() -> Iterator[None]:
    previous = {name: getattr(base, name) for name in _CONFIGURATION_FIELDS}
    _apply_configuration()
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


def __getattr__(name: str):
    return getattr(base, name)


def parse_args(argv: list[str] | None = None):
    with _configuration_context():
        return base.parse_args(argv)


def derive_manifest(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    with _configuration_context():
        return base.derive_manifest(*args, **kwargs)


def main(argv: list[str] | None = None) -> int:
    with _configuration_context():
        return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
