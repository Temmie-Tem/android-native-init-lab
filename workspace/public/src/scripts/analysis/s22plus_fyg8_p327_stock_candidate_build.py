#!/usr/bin/env python3
"""Build the P3.27 boot-only framed fixed-command ACM candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import s22plus_fyg8_p327_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p327_framed_acm_observer as framed_observer  # noqa: E402
import s22plus_fyg8_p327_framed_exec_runtime as framed_runtime  # noqa: E402
import s22plus_fyg8_p327_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P326_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p326_stock_candidate_build.py"
P326_BUILDER_IDENTITY = {
    "size": 24_494,
    "sha256": "ee8f3c72f9857c9e6efb219dc03a43ad363cd27f2641a5bdd46dd4f1bc8ae84d",
}
P326_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p326/"
    "stock-candidate-build-v1-20260902-08"
)
P326_RESULT_IDENTITY = {
    "size": 42_384,
    "sha256": "58142bf3b5121d616987f920232ddfe9fdd9b1f1307da5a1ee63480851341436",
}
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p327/"
    "stock-candidate-build-v1-20260902-04"
)
BUSYBOX = ROOT / (
    "workspace/private/inputs/s22plus_fyg8_p326/busybox/bin/"
    "busybox-aarch64-static-1.36.1"
)
BUSYBOX_IDENTITY = {
    "size": 2_237_056,
    "sha256": "d4e1ca8235fd5c47a7dfca5c9c60ad2243f5d17d3c43d58a7c42355f10fa2cba",
}
BUSYBOX_SOURCE_ARCHIVE_IDENTITY = {
    "size": 2_525_473,
    "sha256": "b8cc24c9574d809e7279c3be349795c5d5ceb6fdf19ca709f80cde50e47de314",
}
BUSYBOX_CONFIG_IDENTITY = {
    "size": 29_588,
    "sha256": "aae4e7cb22845d0eb46ab912f830558c0fb0655fd1964fdda6c745c43fa3b601",
}
BUSYBOX_SOURCE_ARCHIVE = BUSYBOX.parents[1] / "downloads/busybox-1.36.1.tar.bz2"
BUSYBOX_CONFIG = BUSYBOX.parents[1] / "pkg/busybox-1.36.1-config"

P327_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p327_artifact_identity.py"
P327_RUNTIME_SOURCE = REVALIDATION / "s22plus_fyg8_p327_framed_exec_runtime.py"
P327_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p327_stock_process_v2_adapter.py"
P327_OBSERVER_SOURCE = REVALIDATION / "s22plus_fyg8_p327_framed_acm_observer.py"

SCHEMA = "s22plus-fyg8-p327-stock-candidate-build-v1"
VERDICT = "PASS_P327_STOCK_CANDIDATE_BUILD_H0_FRAMED_FIXED_COMMANDS"
STATUS = "IMPLEMENTED_H0_FRAMED_FIXED_COMMANDS_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P327_RUN_ID = artifact.P327_RUN_ID
P327_RUN_ID_HEX = artifact.P327_RUN_ID_HEX


class AuditError(RuntimeError):
    pass


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("ascii")


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def unique(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise AuditError(f"{label} has duplicate key {key}")
            result[key] = value
        return result

    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} is not an object")
    return value


def _stable(
    path: Path,
    label: str,
    maximum: int,
    expected: Mapping[str, Any] | None = None,
    *,
    mode: int | None = None,
    nlink: int | None = None,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    inode = lambda value: (  # noqa: E731
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
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or inode(before) != inode(inside)
        or inode(before) != inode(after)
        or len(payload) != before.st_size
        or len(payload) > maximum
        or (expected is not None and identity(payload) != dict(expected))
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or (nlink is not None and before.st_nlink != nlink)
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def _load_p326() -> types.ModuleType:
    payload = _stable(
        P326_BUILDER_SOURCE, "P326 builder", 2 << 20, P326_BUILDER_IDENTITY, nlink=1
    )
    module = types.ModuleType("s22plus_fyg8_p326_builder_bound_for_p327")
    module.__file__ = str(P326_BUILDER_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P326_BUILDER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("P326 builder failed to load") from exc
    if getattr(module, "P326_RUN_ID_HEX", None) != artifact.P326_RUN_ID_HEX:
        raise AuditError("P326 builder run identity differs")
    return module


_P326 = _load_p326()
try:
    _P326_PREDECESSOR = _P326.audit_existing(P326_OUTPUT)
    _P326_PREDECESSOR_PAYLOAD = _stable(
        P326_OUTPUT / "result.json",
        "P326 result",
        4 << 20,
        P326_RESULT_IDENTITY,
        mode=0o400,
        nlink=1,
    )
except Exception as exc:
    raise AuditError("P326 predecessor audit failed") from exc

_ENGINE = _P326._ENGINE
_ORIGINAL_BUILD_ONCE = _P326._ORIGINAL_BUILD_ONCE
_ORIGINAL_AUDIT_EXISTING = _P326._ORIGINAL_AUDIT_EXISTING
_P326_NORMALIZE = _P326._normalize_result


def _predecessor() -> tuple[dict[str, Any], bytes, bytes]:
    payload = _stable(
        P326_OUTPUT / "result.json", "P326 result", 4 << 20,
        P326_RESULT_IDENTITY, mode=0o400, nlink=1,
    )
    if payload != _P326_PREDECESSOR_PAYLOAD:
        raise AuditError("P326 result changed")
    source = _stable(
        P326_BUILDER_SOURCE, "P326 builder", 2 << 20,
        P326_BUILDER_IDENTITY, nlink=1,
    )
    return dict(_P326_PREDECESSOR), payload, source


def _current_sources() -> dict[str, bytes]:
    paths = {
        "p327_stock_candidate_build.py": SELF_SOURCE,
        "p327_artifact_identity.py": P327_ARTIFACT_SOURCE,
        "p327_framed_exec_runtime.py": P327_RUNTIME_SOURCE,
        "p327_stock_process_v2_adapter.py": P327_ADAPTER_SOURCE,
        "p327_framed_acm_observer.py": P327_OBSERVER_SOURCE,
    }
    return {
        name: _stable(path, f"P327 source {name}", 2 << 20, nlink=1)
        for name, path in paths.items()
    }


def _copy_source_closure(
    output_root: Path, predecessor: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    source_root = output_root / "stock-sources"
    _ENGINE.p321._mkdir(source_root)
    expected = predecessor.get("source_closure")
    if not isinstance(expected, dict) or len(expected) != 12:
        raise AuditError("P326 source closure differs")
    receipts: dict[str, dict[str, Any]] = {}
    runtime_receipt: dict[str, Any] | None = None
    for name, expected_identity in sorted(expected.items()):
        before = _stable(
            P326_OUTPUT / "stock-sources" / name,
            f"P326 source {name}",
            2 << 20,
            expected_identity,
            mode=0o400,
            nlink=1,
        )
        after = before
        if name == "s22plus_fyg8_p290_e3_runtime.inc.c":
            after = framed_runtime.transform_runtime_include(before)
            runtime_receipt = framed_runtime.validate_transform(before, after) | {
                "before_identity": identity(before),
                "after_identity": identity(after),
            }
        _ENGINE.p321._write_exclusive(source_root / name, after)
        receipts[name] = identity(after)
    if runtime_receipt is None:
        raise AuditError("P327 runtime source is absent")
    _ENGINE.p321._fsync_directory(source_root)
    return receipts, runtime_receipt



def _load_packager() -> tuple[Any, Any, bytes]:
    helper, packager, source = _P326._load_packager()
    packager.RUN_ID = P327_RUN_ID
    packager._ACTIVE_TOOLS = None
    packager._bind_tools()
    return helper, packager, source


class _RuntimeCompat:
    RuntimeRepairError = framed_runtime.FramedRuntimeError

    @staticmethod
    def transform_runtime_include(value: bytes) -> bytes:
        return framed_runtime.transform_runtime_include(value)

    @staticmethod
    def validate_repair(before: bytes, after: bytes) -> dict[str, Any]:
        return framed_runtime.validate_transform(before, after)


_ENGINE._current_sources = _current_sources
_ENGINE._predecessor = _predecessor
_ENGINE._copy_source_closure = _copy_source_closure
_ENGINE._load_packager = _load_packager
_ENGINE.artifact = artifact
_ENGINE.adapter = adapter
_ENGINE.repair = _RuntimeCompat
_ENGINE.P321_OUTPUT = P326_OUTPUT
_ENGINE.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
_ENGINE.P322_ARTIFACT_SOURCE = P327_ARTIFACT_SOURCE
_ENGINE.P322_REPAIR_SOURCE = P327_RUNTIME_SOURCE
_ENGINE.P322_ADAPTER_SOURCE = P327_ADAPTER_SOURCE
_ENGINE.P322_RUN_ID = P327_RUN_ID
_ENGINE.P322_RUN_ID_HEX = P327_RUN_ID_HEX
_ENGINE.SCHEMA = SCHEMA
_ENGINE.VERDICT = VERDICT
_ENGINE.STATUS = STATUS
_ENGINE.TARGET = TARGET

class _P326ConsoleCompat:
    CONTRACT_ID = framed_runtime.CONTRACT_ID
    HOST_TRANSCRIPT = b""
    DEVICE_TRANSCRIPT = b""


for _module in (_P326, _P326._P325, _P326._P325._P324):
    for _name, _value in {
        "artifact": artifact,
        "adapter": adapter,
        "SCHEMA": SCHEMA,
        "VERDICT": VERDICT,
        "STATUS": STATUS,
        "TARGET": TARGET,
    }.items():
        setattr(_module, _name, _value)

for _name, _value in {
    "P326_RUN_ID": P327_RUN_ID,
    "P326_RUN_ID_HEX": P327_RUN_ID_HEX,
    "P324_PREDECESSOR_RUN_ID_HEX": artifact.P326_PREDECESSOR_RUN_ID_HEX,
    "console": _P326ConsoleCompat,
    "bidirectional_observer": framed_observer,
}.items():
    setattr(_P326, _name, _value)

for _name, _value in {
    "P325_RUN_ID": P327_RUN_ID,
    "P325_RUN_ID_HEX": P327_RUN_ID_HEX,
    "P324_PREDECESSOR_RUN_ID_HEX": artifact.P326_PREDECESSOR_RUN_ID_HEX,
}.items():
    setattr(_P326._P325, _name, _value)

_P326._P325._P324.P324_RUN_ID = P327_RUN_ID
_P326._P325._P324.P324_RUN_ID_HEX = P327_RUN_ID_HEX


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    result = _P326_NORMALIZE(value)
    if (
        result.get("schema") != SCHEMA
        or result.get("run_id_hex") != P327_RUN_ID_HEX
        or result.get("lineage", {}).get("predecessor_run_id")
        != artifact.P326_PREDECESSOR_RUN_ID_HEX
    ):
        raise AuditError("P327 result header differs")
    candidate = result.get("phase2", {}).get("candidate")
    if not isinstance(candidate, dict):
        raise AuditError("P327 candidate projection is absent")
    candidate["differs_from_consumed_p326"] = candidate.pop(
        "differs_from_consumed_p325",
        candidate.get("differs_from_consumed_p324", False),
    )
    if candidate["differs_from_consumed_p326"] is not True:
        raise AuditError("P327 repeats consumed P326 AP")
    for label in ("a", "b"):
        if candidate.get(label, {}).get("busybox") != BUSYBOX_IDENTITY:
            raise AuditError("P327 candidate lacks exact BusyBox")
        package = candidate[label].get("package")
        inherited_pair = (
            "s22plus_fyg8_p326_boot_only_package_v1",
            "PASS_P326_DETERMINISTIC_BOOT_ONLY_BUSYBOX_PACKAGE_H0",
        )
        normalized_pair = (
            "s22plus_fyg8_p327_boot_only_package_v1",
            "PASS_P327_DETERMINISTIC_BOOT_ONLY_FRAMED_EXEC_PACKAGE_H0",
        )
        if not isinstance(package, dict) or (
            package.get("schema"), package.get("verdict")
        ) not in (inherited_pair, normalized_pair):
            raise AuditError("P327 inherited package projection differs")
        package["schema"] = "s22plus_fyg8_p327_boot_only_package_v1"
        package["verdict"] = (
            "PASS_P327_DETERMINISTIC_BOOT_ONLY_FRAMED_EXEC_PACKAGE_H0"
        )
    preservation = result.get("preservation")
    if not isinstance(preservation, dict):
        raise AuditError("P327 preservation projection is absent")
    for stale in (
        "p325_consumed_candidate_unchanged",
        "p325_source_closure_reopened",
        "p325_exact_lane_and_guard_reused",
        "runtime_byte_equivalent_to_p323",
        "runtime_byte_equivalent_to_p324",
        "runtime_delta_console_only",
        "runtime_delta_one_function",
    ):
        preservation.pop(stale, None)
    preservation["p326_consumed_candidate_unchanged"] = True
    preservation["p326_source_closure_reopened"] = True
    preservation["runtime_delta_framed_exec_only"] = True
    preservation["p326_exact_lane_and_guard_reused"] = True
    result["busybox"] = {
        "binary": BUSYBOX_IDENTITY,
        "source_archive": BUSYBOX_SOURCE_ARCHIVE_IDENTITY,
        "config": BUSYBOX_CONFIG_IDENTITY,
        "path": "bin/busybox",
        "static_aarch64": True,
        "ash_enabled": True,
        "su_getty_disabled": True,
    }
    result.pop("bidirectional_console", None)
    result["framed_exec"] = {
        "runtime_contract": framed_runtime.CONTRACT_ID,
        "observer_contract": framed_observer.CONTRACT_ID,
        "wire_magic": framed_runtime.FRAME_MAGIC.decode("ascii"),
        "frame_header_size": framed_runtime.FRAME_HEADER_SIZE,
        "commands": [identity(item) for item in framed_runtime.DEFAULT_COMMANDS],
        "command_count": framed_runtime.MAX_COMMANDS,
        "caller_selected_command": False,
        "command_timeout_sec": framed_runtime.COMMAND_TIMEOUT_SEC,
        "max_output_bytes": framed_runtime.MAX_OUTPUT_BYTES,
        "busybox_ash_child": True,
        "child_kill_and_reap": True,
        "interactive_pty": False,
    }
    result["limitations"] = [
        "P327 packages only the fixed three-command framed proof over the P326 ACM path.",
        "P327 accepts no caller-selected command and proves no general interactive shell or PTY.",
        "No partition other than boot is transferred and rollback remains mandatory.",
        "Carrier remains supplemental and makes no Max77705 causal claim.",
        "No device contact, approval, D0, D1, F1, recovery, replay, or live authority is created by this host build.",
    ]
    result["compatibility_labels"] = {
        "inherited_input_names": ["p321-result.json", "p321-stock-candidate-build.py"],
        "actual_predecessor": "P326",
        "presentation_only": True,
    }
    return result


_ENGINE._json_bytes = lambda value: _json_bytes(_normalize_result(value))


def _validate_busybox_inputs() -> None:
    _stable(BUSYBOX, "P327 BusyBox", 4 << 20, BUSYBOX_IDENTITY, mode=0o555, nlink=1)
    config = _stable(BUSYBOX_CONFIG, "P327 BusyBox config", 128 << 10, BUSYBOX_CONFIG_IDENTITY, nlink=1)
    _stable(BUSYBOX_SOURCE_ARCHIVE, "P327 BusyBox source", 4 << 20, BUSYBOX_SOURCE_ARCHIVE_IDENTITY, nlink=1)
    required = (b"CONFIG_STATIC=y\n", b"CONFIG_ASH=y\n", b"CONFIG_SH_IS_ASH=y\n")
    forbidden = (b"CONFIG_SU=y\n", b"CONFIG_SULOGIN=y\n", b"CONFIG_GETTY=y\n")
    if any(token not in config for token in required) or any(token in config for token in forbidden):
        raise AuditError("P327 BusyBox config differs")


def build_result(
    output_root: Path = DEFAULT_OUTPUT_ROOT, *, audit_only: bool = False
) -> dict[str, Any]:
    output_root = output_root.absolute()
    _validate_busybox_inputs()
    if audit_only:
        return audit_existing(output_root)
    if output_root.exists() or output_root.is_symlink():
        raise AuditError("P327 output already exists")
    output_root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    output_root.parent.chmod(0o700)
    _ORIGINAL_BUILD_ONCE(output_root)
    return _strict_json(
        _stable(output_root / "result.json", "P327 result", 4 << 20, mode=0o400, nlink=1),
        "P327 result",
    )


def audit_existing(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.absolute()
    _validate_busybox_inputs()
    raw = _stable(output_root / "result.json", "P327 result", 4 << 20, mode=0o400, nlink=1)
    stored = _strict_json(raw, "P327 result")
    try:
        audited = _ORIGINAL_AUDIT_EXISTING(output_root)
    except Exception as exc:
        raise AuditError("P327 output did not reopen") from exc
    if stored != _normalize_result(audited):
        raise AuditError("P327 stored result differs from audit")
    return stored


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    output = args.out if args.out.is_absolute() else ROOT / args.out
    try:
        result = build_result(output, audit_only=args.audit_only)
    except (AuditError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({
        "schema": SCHEMA,
        "verdict": result["verdict"],
        "output": str(output),
        "result": identity((output / "result.json").read_bytes()),
        "created": not args.audit_only,
        "device_contact": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
