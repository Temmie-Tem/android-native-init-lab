#!/usr/bin/env python3
"""Build the P3.26 boot-only bidirectional ACM and BusyBox-console candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import s22plus_fyg8_p326_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p326_bidirectional_acm_observer as bidirectional_observer  # noqa: E402
import s22plus_fyg8_p326_bidirectional_console_runtime as console  # noqa: E402
import s22plus_fyg8_p326_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P325_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p325_stock_candidate_build.py"
P325_BUILDER_IDENTITY = {
    "size": 18_815,
    "sha256": "994a437a62809c9884d81a0fdc5bc1bbacdc8e245c2bc2983390fa1abed35c69",
}
P325_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p325/"
    "stock-candidate-build-v1-20260901-02"
)
P325_RESULT_IDENTITY = {
    "size": 40_980,
    "sha256": "49b408fbf3f3095e1c3f4887a29c8d47e6f209e471962ed5c5e823661bd95240",
}
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p326/"
    "stock-candidate-build-v1-20260902-07"
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

P326_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p326_artifact_identity.py"
P326_RUNTIME_SOURCE = REVALIDATION / "s22plus_fyg8_p326_bidirectional_console_runtime.py"
P326_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p326_stock_process_v2_adapter.py"
P326_OBSERVER_SOURCE = REVALIDATION / "s22plus_fyg8_p326_bidirectional_acm_observer.py"

SCHEMA = "s22plus-fyg8-p326-stock-candidate-build-v1"
VERDICT = "PASS_P326_STOCK_CANDIDATE_BUILD_H0_BIDIRECTIONAL_CONSOLE"
STATUS = "IMPLEMENTED_H0_BIDIRECTIONAL_CONSOLE_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P326_RUN_ID = artifact.P326_RUN_ID
P326_RUN_ID_HEX = artifact.P326_RUN_ID_HEX


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


def _load_p325() -> types.ModuleType:
    payload = _stable(
        P325_BUILDER_SOURCE, "P325 builder", 2 << 20, P325_BUILDER_IDENTITY, nlink=1
    )
    module = types.ModuleType("s22plus_fyg8_p325_builder_bound_for_p326")
    module.__file__ = str(P325_BUILDER_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P325_BUILDER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("P325 builder failed to load") from exc
    if getattr(module, "P325_RUN_ID_HEX", None) != artifact.P325_RUN_ID_HEX:
        raise AuditError("P325 builder run identity differs")
    return module


_P325 = _load_p325()
try:
    _P325_PREDECESSOR = _P325.audit_existing(P325_OUTPUT)
    _P325_PREDECESSOR_PAYLOAD = _stable(
        P325_OUTPUT / "result.json",
        "P325 result",
        4 << 20,
        P325_RESULT_IDENTITY,
        mode=0o400,
        nlink=1,
    )
except Exception as exc:
    raise AuditError("P325 predecessor audit failed") from exc

_ENGINE = _P325._ENGINE
_ORIGINAL_BUILD_ONCE = _P325._ORIGINAL_BUILD_ONCE
_ORIGINAL_AUDIT_EXISTING = _P325._ORIGINAL_AUDIT_EXISTING
_P325_NORMALIZE = _P325._normalize_result


def _predecessor() -> tuple[dict[str, Any], bytes, bytes]:
    payload = _stable(
        P325_OUTPUT / "result.json", "P325 result", 4 << 20,
        P325_RESULT_IDENTITY, mode=0o400, nlink=1,
    )
    if payload != _P325_PREDECESSOR_PAYLOAD:
        raise AuditError("P325 result changed")
    source = _stable(
        P325_BUILDER_SOURCE, "P325 builder", 2 << 20,
        P325_BUILDER_IDENTITY, nlink=1,
    )
    return dict(_P325_PREDECESSOR), payload, source


def _current_sources() -> dict[str, bytes]:
    paths = {
        "p326_stock_candidate_build.py": SELF_SOURCE,
        "p326_artifact_identity.py": P326_ARTIFACT_SOURCE,
        "p326_bidirectional_console_runtime.py": P326_RUNTIME_SOURCE,
        "p326_stock_process_v2_adapter.py": P326_ADAPTER_SOURCE,
        "p326_bidirectional_acm_observer.py": P326_OBSERVER_SOURCE,
    }
    return {
        name: _stable(path, f"P326 source {name}", 2 << 20, nlink=1)
        for name, path in paths.items()
    }


def _copy_source_closure(
    output_root: Path, predecessor: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    source_root = output_root / "stock-sources"
    _ENGINE.p321._mkdir(source_root)
    expected = predecessor.get("source_closure")
    if not isinstance(expected, dict) or len(expected) != 12:
        raise AuditError("P325 source closure differs")
    receipts: dict[str, dict[str, Any]] = {}
    runtime_receipt: dict[str, Any] | None = None
    for name, expected_identity in sorted(expected.items()):
        before = _stable(
            P325_OUTPUT / "stock-sources" / name,
            f"P325 source {name}",
            2 << 20,
            expected_identity,
            mode=0o400,
            nlink=1,
        )
        after = before
        if name == "s22plus_fyg8_p290_e3_runtime.inc.c":
            after = console.transform_runtime_include(before)
            runtime_receipt = console.validate_transform(before, after) | {
                "before_identity": identity(before),
                "after_identity": identity(after),
            }
        _ENGINE.p321._write_exclusive(source_root / name, after)
        receipts[name] = identity(after)
    if runtime_receipt is None:
        raise AuditError("P326 runtime source is absent")
    _ENGINE.p321._fsync_directory(source_root)
    return receipts, runtime_receipt


def _copy_to_output(source: Path, destination: Path) -> None:
    _ENGINE.p321._write_exclusive(destination, source.read_bytes())


def _install_busybox_packager(packager: Any) -> None:
    original_package = packager._package_candidate
    original_verify = packager._verify_packaged_candidate

    def package_candidate(
        base_boot: bytes,
        init_bytes: bytes,
        child_bytes: bytes,
        module_payloads: dict[str, bytes],
        overlay_names: tuple[str, ...],
        output: Path,
        label: str,
    ) -> dict[str, Any]:
        busybox = _stable(
            BUSYBOX, "P326 BusyBox", 4 << 20,
            BUSYBOX_IDENTITY, mode=0o555, nlink=1,
        )
        with tempfile.TemporaryDirectory(prefix=f"p326-package-{label}-") as name:
            work = Path(name)
            inherited = work / "inherited"
            original = original_package(
                base_boot, init_bytes, child_bytes, module_payloads,
                overlay_names, inherited, label + "-p325",
            )
            unpack = work / "unpack"
            final = work / "final"
            tools = work / "tools"
            for directory in (unpack, final, tools):
                directory.mkdir()
            magiskboot = tools / "magiskboot"
            lz4 = tools / "lz4"
            magiskboot.write_bytes(
                packager.stable_bytes(packager._tools()["magiskboot"], "magiskboot", 4 << 20)
            )
            lz4.write_bytes(packager.stable_bytes(packager._tools()["lz4"], "lz4", 4 << 20))
            magiskboot.chmod(0o700)
            lz4.chmod(0o700)
            inherited_boot = inherited / "boot.img"
            packager._run_tool([magiskboot, "unpack", "-h", inherited_boot], unpack, "P326 inherited unpack")
            ramdisk = unpack / "ramdisk.cpio"
            entries = packager._cpio_entries(magiskboot, ramdisk, unpack, "P326 inherited")
            if "bin" in entries or "bin/busybox" in entries:
                raise AuditError("P326 predecessor unexpectedly contains BusyBox")
            busybox_stage = work / "busybox"
            busybox_stage.write_bytes(busybox)
            packager._run_tool(
                [
                    magiskboot,
                    "cpio",
                    str(ramdisk),
                    "mkdir 755 bin",
                    f"add 755 bin/busybox {busybox_stage}",
                ],
                unpack,
                "P326 BusyBox ramdisk overlay",
            )
            boot = work / "boot.img"
            packager._run_tool([magiskboot, "repack", inherited_boot, boot], unpack, "P326 boot repack")
            candidate = boot.read_bytes()
            packager._run_tool([magiskboot, "unpack", "-h", boot], final, "P326 final unpack")
            final_ramdisk = final / "ramdisk.cpio"
            extracted = final / "busybox"
            packager._run_tool(
                [magiskboot, "cpio", str(final_ramdisk), f"extract bin/busybox {extracted}"],
                final,
                "P326 BusyBox extract",
            )
            if extracted.read_bytes() != busybox:
                raise AuditError("P326 packaged BusyBox differs")
            frame = work / "boot.img.lz4"
            packager._run_tool(
                [lz4, "--content-size", "-B6", "-f", "-q", boot, frame],
                work,
                "P326 LZ4 compression",
            )
            roundtrip = work / "roundtrip.boot.img"
            packager._run_tool([lz4, "-d", "-f", "-q", frame, roundtrip], work, "P326 LZ4 roundtrip")
            if roundtrip.read_bytes() != candidate:
                raise AuditError("P326 LZ4 roundtrip differs")
            ap_path = work / "odin4/AP.tar.md5"
            ap_structure = packager._write_deterministic_boot_ap(frame.read_bytes(), ap_path)
            output.mkdir(mode=0o700)
            (output / "odin4").mkdir(mode=0o700)
            for source, destination in (
                (boot, output / "boot.img"),
                (frame, output / "boot.img.lz4"),
                (ap_path, output / "odin4/AP.tar.md5"),
            ):
                _copy_to_output(source, destination)
            packager._fsync_directory(output / "odin4")
            packager._fsync_directory(output)
            result = dict(original)
            result.update(
                {
                    "boot_img": identity(candidate),
                    "boot_img_lz4": identity(frame.read_bytes()),
                    "ap_tar_md5": identity(ap_path.read_bytes()),
                    "busybox": BUSYBOX_IDENTITY,
                    "busybox_path": "bin/busybox",
                    "busybox_mode": "0755",
                    "busybox_static_aarch64": True,
                }
            )
            result["package"] = {
                "schema": "s22plus_fyg8_p326_boot_only_package_v1",
                "verdict": "PASS_P326_DETERMINISTIC_BOOT_ONLY_BUSYBOX_PACKAGE_H0",
                "boot_img": result["boot_img"],
                "boot_img_lz4": result["boot_img_lz4"],
                "ap_tar_md5": result["ap_tar_md5"],
                "ap_structure": ap_structure,
                "members": ["boot.img.lz4"],
                "busybox": BUSYBOX_IDENTITY,
                "host_only": True,
                "device_contact": False,
                "odin_invoked": False,
            }
            return result

    def verify_candidate(
        candidate_root: Path,
        expected: dict[str, Any],
        init_bytes: bytes,
        child_bytes: bytes,
        module_payloads: dict[str, bytes],
        image_bytes: bytes,
        overlay_names: tuple[str, ...],
        label: str,
    ) -> dict[str, Any]:
        base = original_verify(
            candidate_root, expected, init_bytes, child_bytes,
            module_payloads, image_bytes, overlay_names, label,
        )
        busybox = _stable(
            BUSYBOX, "P326 BusyBox", 4 << 20,
            BUSYBOX_IDENTITY, mode=0o555, nlink=1,
        )
        with tempfile.TemporaryDirectory(prefix=f"p326-verify-{label}-") as name:
            work = Path(name)
            unpack = work / "unpack"
            unpack.mkdir()
            magiskboot = work / "magiskboot"
            magiskboot.write_bytes(
                packager.stable_bytes(packager._tools()["magiskboot"], "magiskboot", 4 << 20)
            )
            magiskboot.chmod(0o700)
            packager._run_tool(
                [magiskboot, "unpack", "-h", candidate_root / "boot.img"],
                unpack,
                "P326 verify unpack",
            )
            entries = packager._cpio_entries(
                magiskboot, unpack / "ramdisk.cpio", unpack, "P326 verify"
            )
            if entries.count("bin/busybox") != 1:
                raise AuditError("P326 BusyBox cpio member differs")
            extracted = work / "busybox"
            packager._run_tool(
                [magiskboot, "cpio", str(unpack / "ramdisk.cpio"), f"extract bin/busybox {extracted}"],
                unpack,
                "P326 verify BusyBox extract",
            )
            if extracted.read_bytes() != busybox:
                raise AuditError("P326 verified BusyBox differs")
        return dict(base) | {
            "busybox": BUSYBOX_IDENTITY,
            "busybox_path": "bin/busybox",
            "busybox_static_aarch64": True,
        }

    packager._package_candidate = package_candidate
    packager._verify_packaged_candidate = verify_candidate


def _load_packager() -> tuple[Any, Any, bytes]:
    helper, packager, source = _P325._load_packager()
    packager.RUN_ID = P326_RUN_ID
    packager._ACTIVE_TOOLS = None
    packager._bind_tools()
    _install_busybox_packager(packager)
    return helper, packager, source


class _RuntimeCompat:
    RuntimeRepairError = console.ConsoleRuntimeError

    @staticmethod
    def transform_runtime_include(value: bytes) -> bytes:
        return console.transform_runtime_include(value)

    @staticmethod
    def validate_repair(before: bytes, after: bytes) -> dict[str, Any]:
        return console.validate_transform(before, after)


_ENGINE._current_sources = _current_sources
_ENGINE._predecessor = _predecessor
_ENGINE._copy_source_closure = _copy_source_closure
_ENGINE._load_packager = _load_packager
_ENGINE.artifact = artifact
_ENGINE.adapter = adapter
_ENGINE.repair = _RuntimeCompat
_ENGINE.P321_OUTPUT = P325_OUTPUT
_ENGINE.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
_ENGINE.P322_ARTIFACT_SOURCE = P326_ARTIFACT_SOURCE
_ENGINE.P322_REPAIR_SOURCE = P326_RUNTIME_SOURCE
_ENGINE.P322_ADAPTER_SOURCE = P326_ADAPTER_SOURCE
_ENGINE.P322_RUN_ID = P326_RUN_ID
_ENGINE.P322_RUN_ID_HEX = P326_RUN_ID_HEX
_ENGINE.SCHEMA = SCHEMA
_ENGINE.VERDICT = VERDICT
_ENGINE.STATUS = STATUS
_ENGINE.TARGET = TARGET

for _module, _values in (
    (
        _P325,
        {
            "artifact": artifact,
            "adapter": adapter,
            "P325_RUN_ID": P326_RUN_ID,
            "P325_RUN_ID_HEX": P326_RUN_ID_HEX,
            "P324_PREDECESSOR_RUN_ID_HEX": artifact.P325_PREDECESSOR_RUN_ID_HEX,
            "SCHEMA": SCHEMA,
            "VERDICT": VERDICT,
            "STATUS": STATUS,
            "TARGET": TARGET,
        },
    ),
    (
        _P325._P324,
        {
            "artifact": artifact,
            "adapter": adapter,
            "P324_RUN_ID": P326_RUN_ID,
            "P324_RUN_ID_HEX": P326_RUN_ID_HEX,
            "SCHEMA": SCHEMA,
            "VERDICT": VERDICT,
            "STATUS": STATUS,
            "TARGET": TARGET,
        },
    ),
):
    for _name, _value in _values.items():
        setattr(_module, _name, _value)


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    result = _P325_NORMALIZE(value)
    if (
        result.get("schema") != SCHEMA
        or result.get("run_id_hex") != P326_RUN_ID_HEX
        or result.get("lineage", {}).get("predecessor_run_id")
        != artifact.P325_PREDECESSOR_RUN_ID_HEX
    ):
        raise AuditError("P326 result header differs")
    candidate = result.get("phase2", {}).get("candidate")
    if not isinstance(candidate, dict):
        raise AuditError("P326 candidate projection is absent")
    candidate["differs_from_consumed_p325"] = candidate.pop(
        "differs_from_consumed_p324", candidate.get("differs_from_consumed_p323", False)
    )
    if candidate["differs_from_consumed_p325"] is not True:
        raise AuditError("P326 repeats consumed P325 AP")
    for label in ("a", "b"):
        if candidate.get(label, {}).get("busybox") != BUSYBOX_IDENTITY:
            raise AuditError("P326 candidate lacks exact BusyBox")
    preservation = result.get("preservation")
    if not isinstance(preservation, dict):
        raise AuditError("P326 preservation projection is absent")
    preservation.pop("p324_consumed_candidate_unchanged", None)
    preservation.pop("p324_source_closure_reopened", None)
    preservation["p325_consumed_candidate_unchanged"] = True
    preservation["p325_source_closure_reopened"] = True
    preservation["runtime_delta_console_only"] = True
    preservation["p325_exact_lane_and_guard_reused"] = True
    result["busybox"] = {
        "binary": BUSYBOX_IDENTITY,
        "source_archive": BUSYBOX_SOURCE_ARCHIVE_IDENTITY,
        "config": BUSYBOX_CONFIG_IDENTITY,
        "path": "bin/busybox",
        "static_aarch64": True,
        "ash_enabled": True,
        "su_getty_disabled": True,
    }
    result["bidirectional_console"] = {
        "runtime_contract": console.CONTRACT_ID,
        "observer_contract": bidirectional_observer.CONTRACT_ID,
        "host_tx": identity(console.HOST_TRANSCRIPT),
        "device_rx": identity(console.DEVICE_TRANSCRIPT),
        "pid1_ping_pong": True,
        "busybox_ash_child": True,
        "busybox_ash_exits_after_proof": True,
        "trailing_bytes_policy": "reject-and-retain",
        "fixed_lines": 2,
    }
    result["limitations"] = [
        "P326 proves only the fixed PID1 PING/PONG and BusyBox ash round trip over the P325 ACM path.",
        "The BusyBox ash child exits after its fixed reply; no general interactive command is accepted by P326.",
        "No partition other than boot is transferred and rollback remains mandatory.",
        "Carrier remains supplemental and makes no Max77705 causal claim.",
        "No device contact, approval, D0, D1, F1, recovery, replay, or live authority is created by this host build.",
    ]
    result["compatibility_labels"] = {
        "inherited_input_names": ["p321-result.json", "p321-stock-candidate-build.py"],
        "actual_predecessor": "P325",
        "presentation_only": True,
    }
    return result


_ENGINE._json_bytes = lambda value: _json_bytes(_normalize_result(value))


def _validate_busybox_inputs() -> None:
    _stable(BUSYBOX, "P326 BusyBox", 4 << 20, BUSYBOX_IDENTITY, mode=0o555, nlink=1)
    config = _stable(BUSYBOX_CONFIG, "P326 BusyBox config", 128 << 10, BUSYBOX_CONFIG_IDENTITY, nlink=1)
    _stable(BUSYBOX_SOURCE_ARCHIVE, "P326 BusyBox source", 4 << 20, BUSYBOX_SOURCE_ARCHIVE_IDENTITY, nlink=1)
    required = (b"CONFIG_STATIC=y\n", b"CONFIG_ASH=y\n", b"CONFIG_SH_IS_ASH=y\n")
    forbidden = (b"CONFIG_SU=y\n", b"CONFIG_SULOGIN=y\n", b"CONFIG_GETTY=y\n")
    if any(token not in config for token in required) or any(token in config for token in forbidden):
        raise AuditError("P326 BusyBox config differs")


def build_result(
    output_root: Path = DEFAULT_OUTPUT_ROOT, *, audit_only: bool = False
) -> dict[str, Any]:
    output_root = output_root.absolute()
    _validate_busybox_inputs()
    if audit_only:
        return audit_existing(output_root)
    if output_root.exists() or output_root.is_symlink():
        raise AuditError("P326 output already exists")
    output_root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    output_root.parent.chmod(0o700)
    _ORIGINAL_BUILD_ONCE(output_root)
    return _strict_json(
        _stable(output_root / "result.json", "P326 result", 4 << 20, mode=0o400, nlink=1),
        "P326 result",
    )


def audit_existing(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.absolute()
    _validate_busybox_inputs()
    raw = _stable(output_root / "result.json", "P326 result", 4 << 20, mode=0o400, nlink=1)
    stored = _strict_json(raw, "P326 result")
    try:
        audited = _ORIGINAL_AUDIT_EXISTING(output_root)
    except Exception as exc:
        raise AuditError("P326 output did not reopen") from exc
    if stored != _normalize_result(audited):
        raise AuditError("P326 stored result differs from audit")
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
