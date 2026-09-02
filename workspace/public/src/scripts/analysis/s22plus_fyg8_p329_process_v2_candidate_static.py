#!/usr/bin/env python3
"""P3.29 candidate-static wrapper over the exact P3.28 checker."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import s22plus_fyg8_p329_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p329_auth_acm_observer as observer_adapter  # noqa: E402
import s22plus_fyg8_p329_auth_exec_runtime as framed_runtime  # noqa: E402
import s22plus_fyg8_p329_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p329_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P328_STATIC_SOURCE = ANALYSIS / "s22plus_fyg8_p328_process_v2_candidate_static.py"
P328_STATIC_IDENTITY = {
    "size": 27_442,
    "sha256": "df2ea043b331bedc73e4acbdced5c9ab040a04532cc4078fcb8fcdc50a89df85",
}
BUILDER_OUTPUT = candidate_build.DEFAULT_OUTPUT_ROOT
BUILDER_RESULT = BUILDER_OUTPUT / "result.json"
BUILDER_RESULT_IDENTITY = {
    "size": 45_150,
    "sha256": "d8475c76d7fe31fa52fc78ed6f770eae73bd24520bf3ff4ab8b696a981503973",
}
BUILDER_SOURCE_IDENTITY = {
    "size": 12_112,
    "sha256": "67d27540675dd594ae22f0c4d6a7e1cb508926f6d43b662abc0b2850a6b25691",
}
RUNTIME_SOURCE_IDENTITY = {
    "size": 3_738,
    "sha256": "6b3bcb98bf02358cbeb3faff24604d0f2168fe843147797a6f3acdc618edea2e",
}
OBSERVER_SOURCE_IDENTITY = {
    "size": 3_579,
    "sha256": "ddcc7ab2cc8e6fd70f096b4b19606d9e9fde8355eaa9cb65534b43eb917bbe76",
}
ADAPTER_SOURCE_IDENTITY = {
    "size": 8_843,
    "sha256": "c6894dbbcc8eaf2369a288f16d8379bf59e936517edc2c68d727cfd13b1ac16c",
}
ARTIFACT_SOURCE_IDENTITY = {
    "size": 6_077,
    "sha256": "4251bafc22db87846ddac24558d5c84a12eced56cc10cb70ee32e238cb1cf437",
}
P329_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "7a83b7c32e52f13fb88ec3cc6d81671baf70f13c343f2e02b03a6d712ab494bf",
}
P329_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "6fc2e5c0b299c740b21c66ff0185b6e8ef4764e88e4821d0e3cd18ee37c5361a",
}
P329_INIT_IDENTITY = {
    "size": 82_032,
    "sha256": "245a65095da1a615a727ee92edfd3906b7d20096c4a21cc25c73e683c6f7a1fd",
}
P329_KEY_IDENTITY = {
    "size": 32,
    "sha256": "7eb6a32ca96daa9cd125b2798834f45515265a76d653ae719091d98f0a1f515b",
}
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p329/"
    "process-v2-candidate-static-20260903-01.json"
)
SCHEMA = "s22plus_fyg8_p329_process_v2_candidate_static_v1"
VERDICT = "PASS_P329_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
RUN_ID = adapter.P329_RUN_ID_HEX
PREDECESSOR_RUN_ID = adapter.P328_PREDECESSOR_RUN_ID_HEX
OVERLAY = adapter.P329_OVERLAY_CONTRACT_ID


class StaticContractError(ValueError):
    """The exact P3.28 checker or P3.29 static closure differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _inode(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _load() -> types.ModuleType:
    direct = P328_STATIC_SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(P328_STATIC_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise StaticContractError("P3.28 static checker is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or identity(payload) != P328_STATIC_IDENTITY
    ):
        raise StaticContractError("P3.28 static checker identity differs")
    module = types.ModuleType("s22plus_fyg8_p328_static_bound_for_p329")
    module.__file__ = str(P328_STATIC_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P328_STATIC_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise StaticContractError("P3.28 static checker failed to load") from exc
    return module


class _BuilderProxy:
    def __getattr__(self, name: str) -> Any:
        if hasattr(candidate_build, name):
            return getattr(candidate_build, name)
        return getattr(candidate_build._P328, name)  # noqa: SLF001


_P328 = _load()
_P328.artifact = artifact
_P328.observer_adapter = observer_adapter
_P328.framed_runtime = framed_runtime
_P328.candidate_build = _BuilderProxy()
_P328.adapter = adapter
_P328.SELF_SOURCE = SELF_SOURCE
_P328.BUILDER_OUTPUT = BUILDER_OUTPUT
_P328.BUILDER_RESULT = BUILDER_RESULT
_P328.BUILDER_RESULT_IDENTITY = BUILDER_RESULT_IDENTITY
_P328.BUILDER_SOURCE_IDENTITY = BUILDER_SOURCE_IDENTITY
_P328.RUNTIME_SOURCE_IDENTITY = RUNTIME_SOURCE_IDENTITY
_P328.OBSERVER_SOURCE_IDENTITY = OBSERVER_SOURCE_IDENTITY
_P328.ADAPTER_SOURCE_IDENTITY = ADAPTER_SOURCE_IDENTITY
_P328.ARTIFACT_SOURCE_IDENTITY = ARTIFACT_SOURCE_IDENTITY
_P328.P328_AP_IDENTITY = P329_AP_IDENTITY
_P328.P328_IMAGE_IDENTITY = P329_IMAGE_IDENTITY
_P328.P328_INIT_IDENTITY = P329_INIT_IDENTITY
_P328.P328_KEY_IDENTITY = P329_KEY_IDENTITY
_P328.DEFAULT_OUTPUT = DEFAULT_OUTPUT
_P328.SCHEMA = SCHEMA
_P328.VERDICT = VERDICT
_P328.RUN_ID = RUN_ID
_P328.PREDECESSOR_RUN_ID = PREDECESSOR_RUN_ID
_P328.OVERLAY = OVERLAY
_P328.AUTH_KEY_SCHEMA = artifact.AUTH_KEY_SCHEMA
_P328.AUTH_KEY_SIZE = artifact.AUTH_KEY_SIZE
_P328.DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH

canonical = _P328.canonical
receipt = _P328.receipt
build_result = _P328.build_result
validate_result = _P328.validate_result
validate_bound_result = _P328.validate_bound_result
publish = _P328.publish
main = _P328.main
ROLLBACK_AP = _P328.ROLLBACK_AP
ROLLBACK_IDENTITY = dict(_P328.ROLLBACK_IDENTITY)
TARGET = dict(_P328.TARGET)


if __name__ == "__main__":
    raise SystemExit(main())
