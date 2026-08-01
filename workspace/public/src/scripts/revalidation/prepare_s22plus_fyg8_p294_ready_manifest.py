#!/usr/bin/env python3
"""Create one verified Process-v2 ready manifest for P2.94."""

from __future__ import annotations

from pathlib import Path

import prepare_s22plus_fyg8_p292_ready_manifest as base


SCHEMA = "s22plus_fyg8_p294_ready_manifest_builder_v1"
VERDICT = "PASS_P294_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P294_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
SOURCE_CONTRACT_ID = base.evidence.P294_SOURCE_CONTRACT_ID
DEFAULT_CANDIDATE_STATIC = Path(
    "workspace/private/device-action/s22plus_fyg8_p294_ready_1/"
    "evidence/candidate-static.json"
)
DEFAULT_RUN_MANIFEST = Path(
    "workspace/private/device-action/s22plus_fyg8_p294_ready_1/"
    "evidence/run-manifest.json"
)
DEFAULT_STATIC_CHECK = Path(
    "workspace/private/device-action/s22plus_fyg8_p294_ready_1/"
    "evidence/static-check-result.json"
)
DEFAULT_CANDIDATE_AP = Path(
    "workspace/private/device-action/s22plus_fyg8_p294_ready_1/"
    "candidate/AP.tar.md5"
)
DEFAULT_ROLLBACK_AP = base.DEFAULT_ROLLBACK_AP
DEFAULT_OUT = Path(
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p294_process_v2_ready_1.json"
)
DEFAULT_TARGET_PROFILE = base.DEFAULT_TARGET_PROFILE
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p294-process-v2-ready-1"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p294-live-1"
DEFAULT_TIMEOUT_SEC = base.DEFAULT_TIMEOUT_SEC


def _configure() -> None:
    base.__doc__ = __doc__
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.REHEARSAL_VERDICT = REHEARSAL_VERDICT
    base.SOURCE_CONTRACT_ID = SOURCE_CONTRACT_ID
    base.DEFAULT_CANDIDATE_STATIC = DEFAULT_CANDIDATE_STATIC
    base.DEFAULT_RUN_MANIFEST = DEFAULT_RUN_MANIFEST
    base.DEFAULT_STATIC_CHECK = DEFAULT_STATIC_CHECK
    base.DEFAULT_CANDIDATE_AP = DEFAULT_CANDIDATE_AP
    base.DEFAULT_ROLLBACK_AP = DEFAULT_ROLLBACK_AP
    base.DEFAULT_OUT = DEFAULT_OUT
    base.DEFAULT_TARGET_PROFILE = DEFAULT_TARGET_PROFILE
    base.DEFAULT_MANIFEST_ID = DEFAULT_MANIFEST_ID
    base.DEFAULT_LIVE_RUN_ID = DEFAULT_LIVE_RUN_ID
    base.DEFAULT_TIMEOUT_SEC = DEFAULT_TIMEOUT_SEC


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def parse_args(argv: list[str] | None = None):
    _configure()
    return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
