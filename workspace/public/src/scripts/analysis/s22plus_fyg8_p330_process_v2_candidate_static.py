#!/usr/bin/env python3
"""P3.30 candidate-static receipt over the exact P3.29 checker.

The checker reopens the final P3.30 host build, both boot-only APs, the exact
stock rollback, and the materialized diagnostic runtime.  P3.30 diagnostics
are explicitly metadata only; they do not create a ready manifest, approval,
device contact, or live authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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

import s22plus_fyg8_p330_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p330_auth_acm_observer as observer_adapter  # noqa: E402
import s22plus_fyg8_p330_auth_exec_runtime as framed_runtime  # noqa: E402
import s22plus_fyg8_p330_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p330_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P329_STATIC_SOURCE = ANALYSIS / "s22plus_fyg8_p329_process_v2_candidate_static.py"
P329_STATIC_IDENTITY = {
    "size": 6_501,
    "sha256": "c9fda4da9d66c490104078fb596869847d9a76d1170663b22e7e10c7e84e852e",
}
BUILDER_OUTPUT = candidate_build.DEFAULT_OUTPUT_ROOT
BUILDER_RESULT = BUILDER_OUTPUT / "result.json"
BUILDER_RESULT_IDENTITY = {
    "size": 45_820,
    "sha256": "d2186404aaab0c1472d41d93a241c0ab32119561fe0a07ca231eb0b0ca3bacf1",
}
BUILDER_SOURCE_IDENTITY = {
    "size": 16_862,
    "sha256": "a1f56c5983d078df149be29937b343a63cf91a451fc1a71e5dfa977dacf68ce5",
}
RUNTIME_SOURCE_IDENTITY = {
    "size": 8_818,
    "sha256": "c281a19568569195640fa73de72ae62fafca8481e17037934e595e8da6a77e6a",
}
OBSERVER_SOURCE_IDENTITY = {
    "size": 15_035,
    "sha256": "a00589310609cbab776dd99a23325644406d4d52cc0038ab34ab11ae726b3240",
}
ADAPTER_SOURCE_IDENTITY = {
    "size": 9_731,
    "sha256": "1e72d5d5acffbb98c65c7e61ad3fbb42252398644b78fa9b7558fe532cef63d8",
}
ARTIFACT_SOURCE_IDENTITY = {
    "size": 7_846,
    "sha256": "bc85e7e88c85a9b2678586a0897e14246e1a09976b15921d5f1b414d10118a36",
}
P330_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "f458498c1b33961a9a7049a3ad8e74d4ab67ab64e672ba20af21d074f418175b",
}
P330_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "7a730473a60cf454ba5a3df9dd992444196299b0397369531f3e171982ee8456",
}
P330_INIT_IDENTITY = {
    "size": 82_032,
    "sha256": "4d744d3def07a000d0d31f5abfa323372709d4cac0d6493d8696cb0a0e70a7a7",
}
P330_KEY_IDENTITY = {
    "size": 32,
    "sha256": "7eb6a32ca96daa9cd125b2798834f45515265a76d653ae719091d98f0a1f515b",
}
ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p330/"
    "process-v2-candidate-static-20260903-01.json"
)
SCHEMA = "s22plus_fyg8_p330_process_v2_candidate_static_v1"
VERDICT = "PASS_P330_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
RUN_ID = adapter.P330_RUN_ID_HEX
PREDECESSOR_RUN_ID = adapter.P329_PREDECESSOR_RUN_ID_HEX
OVERLAY = adapter.P330_OVERLAY_CONTRACT_ID
PARENT_SOURCE = adapter.PARENT_SOURCE_CONTRACT_ID
AUTH_KEY_SCHEMA = artifact.AUTH_KEY_SCHEMA
AUTH_KEY_SIZE = artifact.AUTH_KEY_SIZE
DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


class StaticContractError(ValueError):
    """The exact P3.30 static closure is incomplete or changed."""


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


def _stable(path: Path, label: str, maximum: int, expected: dict[str, Any] | None = None, *, mode: int | None = None) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise StaticContractError(f"{label} is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or len(payload) > maximum
        or (expected is not None and identity(payload) != expected)
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
    ):
        raise StaticContractError(f"{label} identity differs")
    return payload


def _load_p329_static() -> types.ModuleType:
    payload = _stable(P329_STATIC_SOURCE, "P3.29 static checker", 2 << 20, P329_STATIC_IDENTITY)
    module = types.ModuleType("s22plus_fyg8_p329_static_bound_for_p330")
    module.__file__ = str(P329_STATIC_SOURCE)
    module.__package__ = ""
    previous = sys.modules.get(module.__name__)
    sys.modules[module.__name__] = module
    try:
        exec(compile(payload, str(P329_STATIC_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise StaticContractError("P3.29 static checker failed to load") from exc
    finally:
        if previous is None:
            sys.modules.pop(module.__name__, None)
        else:
            sys.modules[module.__name__] = previous
    return module


class _BuilderProxy:
    def __getattr__(self, name: str) -> Any:
        if hasattr(candidate_build, name):
            return getattr(candidate_build, name)
        return getattr(candidate_build._P328, name)  # noqa: SLF001


_P329 = _load_p329_static()
_P328 = _P329._P328
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
_P328.P328_AP_IDENTITY = P330_AP_IDENTITY
_P328.P328_IMAGE_IDENTITY = P330_IMAGE_IDENTITY
_P328.P328_INIT_IDENTITY = P330_INIT_IDENTITY
_P328.P328_KEY_IDENTITY = P330_KEY_IDENTITY
_P328.ROLLBACK_AP = ROLLBACK_AP
_P328.ROLLBACK_IDENTITY = ROLLBACK_IDENTITY
_P328.DEFAULT_OUTPUT = DEFAULT_OUTPUT
_P328.SCHEMA = SCHEMA
_P328.VERDICT = VERDICT
_P328.TARGET = TARGET
_P328.RUN_ID = RUN_ID
_P328.PREDECESSOR_RUN_ID = PREDECESSOR_RUN_ID
_P328.OVERLAY = OVERLAY
_P328.PARENT_SOURCE = PARENT_SOURCE
_P328.AUTH_KEY_SCHEMA = AUTH_KEY_SCHEMA
_P328.AUTH_KEY_SIZE = AUTH_KEY_SIZE
_P328.DEFAULT_AUTH_KEY_PATH = DEFAULT_AUTH_KEY_PATH


def _validate_p330(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise StaticContractError("P3.30 static result is not an object")
    if (
        value.get("schema") != SCHEMA
        or value.get("verdict") != VERDICT
        or value.get("target") != TARGET
        or value.get("run_id") != RUN_ID
        or value.get("predecessor_run_id") != PREDECESSOR_RUN_ID
        or value.get("userspace_overlay_contract_id") != OVERLAY
        or value.get("source_contract_id") != PARENT_SOURCE
    ):
        raise StaticContractError("P3.30 static header differs")
    candidate = value.get("candidate")
    if not isinstance(candidate, dict) or candidate.get("a") != candidate.get("b"):
        raise StaticContractError("P3.30 A/B candidate differs")
    if (
        candidate.get("byte_identical") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("run_id_join", {}).get("joined") is not True
        or candidate.get("run_id_join", {}).get("run_id_hex") != RUN_ID
        or candidate.get("a", {}).get("ap_tar_md5") != P330_AP_IDENTITY
        or candidate.get("image") != P330_IMAGE_IDENTITY
        or candidate.get("init") != P330_INIT_IDENTITY
    ):
        raise StaticContractError("P3.30 candidate identity differs")
    if candidate.get("a", {}).get("package", {}).get("members") != ["boot.img.lz4"]:
        raise StaticContractError("P3.30 package is not boot-only")
    observer = value.get("observer_adapter")
    if (
        not isinstance(observer, dict)
        or observer.get("schema") != observer_adapter.SCHEMA
        or observer.get("contract_id") != observer_adapter.CONTRACT_ID
        or observer.get("raw_rx_forwarded_before_classification") is not True
        or observer.get("host_only") is not True
        or observer.get("device_contact") is not False
    ):
        raise StaticContractError("P3.30 observer binding differs")
    framed = value.get("runtime_repair")
    if (
        not isinstance(framed, dict)
        or framed.get("contract_id") != framed_runtime.CONTRACT_ID
        or framed.get("run_id_hex") != RUN_ID
        or framed.get("preauth_diagnostic_frame") != framed_runtime.DIAGNOSTIC_FRAME_TYPE
        or framed.get("rng_eagain_retry_limit") != framed_runtime.RNG_EAGAIN_RETRY_LIMIT
        or framed.get("diagnostics_non_authoritative") is not True
    ):
        raise StaticContractError("P3.30 runtime diagnostic binding differs")
    safety = value.get("safety")
    if (
        not isinstance(safety, dict)
        or safety.get("host_only") is not True
        or any(safety.get(name) is not False for name in (
            "device_contact", "device_write", "odin_invoked", "odin_transfer",
            "flash", "partition_write", "live_authorized", "d0_authorized",
            "d1_authorized", "f1_authorized", "replay_authorized",
            "causal_result_allowed", "candidate_success",
        ))
    ):
        raise StaticContractError("P3.30 static authority projection differs")
    return value


def _augment_p330(value: dict[str, Any]) -> dict[str, Any]:
    """Add the bounded diagnostic projection absent from the P329 checker."""

    observer = value.get("observer_adapter")
    if isinstance(observer, dict):
        observer["preauth_diagnostic_frame"] = framed_runtime.DIAGNOSTIC_FRAME_TYPE
        observer["diagnostic_stages"] = [
            framed_runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
            framed_runtime.DIAGNOSTIC_STAGE_RNG,
        ]
        observer["rng_eagain_retry_limit"] = framed_runtime.RNG_EAGAIN_RETRY_LIMIT
        observer["eagain_only_retry"] = True
        observer["diagnostics_non_authoritative"] = True
    repair = value.get("runtime_repair")
    if isinstance(repair, dict):
        repair["preauth_diagnostic_frame"] = framed_runtime.DIAGNOSTIC_FRAME_TYPE
        repair["rng_eagain_retry_limit"] = framed_runtime.RNG_EAGAIN_RETRY_LIMIT
        repair["diagnostics_non_authoritative"] = True
    return value


def build_result() -> dict[str, Any]:
    try:
        return _validate_p330(_augment_p330(_P328.build_result()))
    except StaticContractError:
        raise
    except Exception as exc:
        raise StaticContractError(f"P3.30 static result did not regenerate: {exc}") from exc


def build_bound_result() -> dict[str, Any]:
    try:
        return _validate_p330(_augment_p330(_P328.build_result(runtime_bound=True)))
    except StaticContractError:
        raise
    except Exception as exc:
        raise StaticContractError(f"P3.30 bound static result differs: {exc}") from exc


def validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or value != build_result():
        raise StaticContractError("P3.30 static result does not regenerate")
    return value


def validate_bound_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or value != build_bound_result():
        raise StaticContractError("P3.30 bound static result does not regenerate")
    return value


def canonical(value: Any) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise StaticContractError("P3.30 value is not canonical JSON") from exc


def publish(path: Path, payload: bytes) -> None:
    direct = path.absolute()
    if direct.exists() or direct.is_symlink():
        raise StaticContractError("P3.30 static output already exists")
    direct.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    direct.parent.chmod(0o700)
    descriptor = os.open(direct, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o400)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise StaticContractError("P3.30 static publication was short")
            offset += written
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(direct.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    output = args.out if args.out.is_absolute() else ROOT / args.out
    try:
        value = build_result()
        payload = canonical(value)
        if not args.audit_only:
            publish(output, payload)
    except (OSError, RuntimeError, StaticContractError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({
        "schema": SCHEMA,
        "verdict": VERDICT,
        "output": str(output),
        "identity": identity(payload),
        "created": not args.audit_only,
        "device_contact": False,
        "live_authorized": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
