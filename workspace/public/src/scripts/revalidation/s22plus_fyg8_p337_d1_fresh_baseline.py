#!/usr/bin/env python3
"""P3.37 one-shot attended D1 baseline rotation.

The reviewed P3.36 wrapper is loaded as an isolated source graph.  Only the
P3.37 binding, run identity, and no-replay namespace are new; the P2.96
one-reboot primitive remains the exact execution engine.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve(strict=True)
SCRIPT_DIR = SCRIPT.parent
P336_SOURCE = SCRIPT_DIR / "s22plus_fyg8_p336_d1_fresh_baseline.py"
P320_SOURCE = SCRIPT_DIR / "s22plus_fyg8_p320_d1_fresh_baseline.py"
P296_PRIMITIVE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p296/d1-baseline-rotation/"
    "s22plus_fyg8_p296_baseline_rotation_d1.py"
)
D0_RUNTIME = SCRIPT_DIR / "device_action_d0_v2.py"
RAW_CAPTURE = SCRIPT_DIR / "device_action_raw_capture_v1.py"
PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
HOST_ADB = Path("/usr/lib/android-sdk/platform-tools/adb")
BINDING_MANIFEST = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p337_d1_fresh_baseline.json"
)

RUN_PARENT = ROOT / "workspace/private/runs/device-action-d1-p337-fresh-baseline"
RUN_DIR = RUN_PARENT / "p337-d1-fresh-baseline-1"
RUN_ARM = RUN_PARENT / "p337-d1-fresh-baseline-1.arm.json"
RUN_STOP = RUN_DIR / "stop.json"
RAW_ROOT = RUN_PARENT / "p337-d1-fresh-baseline-1-raw"
RAW_ADB_DIR = RAW_ROOT / "raw-adb"
ADB_SNAPSHOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p337/d1-fresh-baseline-1/"
    "adb-05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
)

TARGET = {
    "model": "SM-S906N",
    "codename": "g0q",
    "build": "S906NKSS7FYG8",
    "adb_serial_sha256": (
        "c5302ccc08374d408ca3ec4df0ef23770d5ecd35ce173b7d150c4316e9a0757b"
    ),
}
P337_RUN_ID = "c337f1e0a90b5e6d7c8a9b0c1d2e3f3b"
ORDINAL = "p337-d1-fresh-baseline-1"
BINDING_SCHEMA = "s22plus_fyg8_p337_d1_fresh_baseline_execution_binding_v1"
BINDING_ID = "s22plus-fyg8-p337-d1-fresh-baseline-v1"
AUTHORITY_PREFIX = "DEVICE-ACTION-D1-P337-FRESH-BASELINE-1-APPROVE:"
REVIEW_VERDICT = "PASS_GO_P337_D1_FRESH_BASELINE_H0_CAPABILITY_V1"
RESULT_SCHEMA = "s22plus_fyg8_p337_d1_fresh_baseline_result_v1"
RESULT_VERDICT = "PASS_P337_D1_FRESH_BASELINE_EXACT_NORMAL_REBOOT_RETURN_HEALTH"
STOP_SCHEMA = "s22plus_fyg8_p337_d1_fresh_baseline_stop_v1"
STOP_VERDICT = "STOP_P337_D1_FRESH_BASELINE_CONSUMED_NO_REPLAY"
HOST_ADB_SIZE = 716_968
HOST_ADB_SHA256 = "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"


class D1Error(RuntimeError):
    """The P3.37 D1 action failed closed."""


def canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise D1Error("value is not canonical JSON") from exc


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _relative(path: Path) -> str:
    try:
        return path.absolute().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.absolute())


def _receipt(path: Path, payload: bytes) -> dict[str, Any]:
    return {"path": _relative(path), "size": len(payload), "sha256": sha256_bytes(payload)}


def _stable(path: Path, label: str, *, maximum: int, expected: Mapping[str, Any] | None = None) -> bytes:
    direct = path.absolute()
    try:
        if direct != path or direct.resolve(strict=True) != direct:
            raise D1Error(f"{label} path is indirect")
        descriptor = os.open(direct, os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise D1Error(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise D1Error(f"{label} identity differs")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, item) != getattr(after, item) for item in fields):
        raise D1Error(f"{label} changed while reading")
    payload = b"".join(chunks)
    if len(payload) != before.st_size or len(payload) > maximum:
        raise D1Error(f"{label} size differs")
    if expected is not None and (_receipt(path, payload)["size"], _receipt(path, payload)["sha256"]) != (expected.get("size"), expected.get("sha256")):
        raise D1Error(f"{label} bytes differ")
    return payload


def _load_p336() -> types.ModuleType:
    payload = _stable(P336_SOURCE, "P3.36 D1 source", maximum=2 * 1024 * 1024)
    module = types.ModuleType("s22plus_fyg8_p336_d1_bound_for_p337")
    module.__file__ = str(P336_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P336_SOURCE), "exec", dont_inherit=True), module.__dict__)
    except BaseException as exc:
        raise D1Error(f"P3.36 D1 source failed to load: {type(exc).__name__}") from exc
    replacements = {
        "ROOT": ROOT,
        "SCRIPT": SCRIPT,
        "SCRIPT_DIR": SCRIPT_DIR,
        "P320_SOURCE": P320_SOURCE,
        "P296_PRIMITIVE": P296_PRIMITIVE,
        "D0_RUNTIME": D0_RUNTIME,
        "RAW_CAPTURE": RAW_CAPTURE,
        "PROFILE": PROFILE,
        "HOST_ADB": HOST_ADB,
        "BINDING_MANIFEST": BINDING_MANIFEST,
        "RUN_PARENT": RUN_PARENT,
        "RUN_DIR": RUN_DIR,
        "RUN_ARM": RUN_ARM,
        "RUN_STOP": RUN_STOP,
        "RAW_ROOT": RAW_ROOT,
        "RAW_ADB_DIR": RAW_ADB_DIR,
        "ADB_SNAPSHOT": ADB_SNAPSHOT,
        "TARGET": TARGET,
        "P336_RUN_ID": P337_RUN_ID,
        "ORDINAL": ORDINAL,
        "BINDING_SCHEMA": BINDING_SCHEMA,
        "BINDING_ID": BINDING_ID,
        "AUTHORITY_PREFIX": AUTHORITY_PREFIX,
        "REVIEW_VERDICT": REVIEW_VERDICT,
        "RESULT_SCHEMA": RESULT_SCHEMA,
        "RESULT_VERDICT": RESULT_VERDICT,
        "STOP_SCHEMA": STOP_SCHEMA,
        "STOP_VERDICT": STOP_VERDICT,
        "HOST_ADB_SIZE": HOST_ADB_SIZE,
        "HOST_ADB_SHA256": HOST_ADB_SHA256,
    }
    module.__dict__.update(replacements)
    original_receipts = module._source_receipts

    def source_receipts() -> dict[str, dict[str, Any]]:
        value = original_receipts()
        value["p336_source"] = _receipt(
            P336_SOURCE,
            _stable(P336_SOURCE, "P3.36 D1 source", maximum=2 * 1024 * 1024),
        )
        return value

    module._source_receipts = source_receipts
    original_load_p335 = module._load_p335

    def validated_static_inputs() -> dict[str, Any]:
        inputs = source_receipts()
        payload = _stable(
            BINDING_MANIFEST, "P3.37 D1 binding", maximum=256 * 1024
        )
        try:
            binding = json.loads(payload.decode("ascii"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise D1Error("P3.37 D1 binding is not JSON") from exc
        review = binding.get("independent_review")
        if review not in (
            {"status": "review-pending", "verdict": None},
            {"status": "pass-go", "verdict": REVIEW_VERDICT},
        ) or binding != module._expected_binding(inputs, review):
            raise D1Error("P3.37 D1 binding does not match exact inputs")
        authority = AUTHORITY_PREFIX + sha256_bytes(payload)
        return {
            "manifest": binding,
            "manifest_payload": payload,
            "manifest_receipt": _receipt(BINDING_MANIFEST, payload),
            "authority": authority,
            "approval_sha256": sha256_bytes(authority.encode("ascii")),
            "payloads": inputs,
        }

    def load_p335() -> types.ModuleType:
        bound = original_load_p335()
        bound._validated_static_inputs = validated_static_inputs
        return bound

    module._validated_static_inputs = validated_static_inputs
    module._load_p335 = load_p335
    return module


def _source_receipts() -> dict[str, dict[str, Any]]:
    return _load_p336()._source_receipts()


def _expected_binding(inputs: Mapping[str, Any], review: Mapping[str, Any]) -> dict[str, Any]:
    return _load_p336()._expected_binding(inputs, review)


def _validated_static_inputs() -> dict[str, Any]:
    return _load_p336()._validated_static_inputs()


def self_test() -> dict[str, Any]:
    bound = _load_p336()
    value = bound.self_test()
    if value.get("reboot_count") != 1 or value.get("other_target_commands") != 0 or value.get("device_contact") is not False:
        raise D1Error("P3.37 D1 fixture result differs")
    return {
        "schema": "s22plus_fyg8_p337_d1_fresh_baseline_fixture_h0",
        "verdict": "PASS_P337_D1_FRESH_BASELINE_FIXTURE_H0",
        "ordinal": ORDINAL,
        "run_id": P337_RUN_ID,
        "reboot_count": 1,
        "other_target_commands": 0,
        "device_contact": False,
        "approval_created": False,
        "live_authorized": False,
        "p336_run_id_rejected": True,
    }


def run_live(approval: str) -> dict[str, Any]:
    if not isinstance(approval, str) or not approval:
        raise D1Error("P3.37 D1 approval is absent")
    bound = _load_p336()
    try:
        value = bound.run_live(approval)
    except Exception as exc:
        if isinstance(exc, bound.D1Error):
            raise D1Error(str(exc)) from exc
        raise
    result = dict(value)
    result.update({
        "schema": RESULT_SCHEMA,
        "version": "device-action-d1-p337-v1",
        "verdict": RESULT_VERDICT,
        "ordinal": ORDINAL,
        "run_id": P337_RUN_ID,
    })
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        if arguments in ([], ["--self-test"]):
            value = self_test()
        elif len(arguments) == 3 and arguments[:2] == ["--live", "--approval"]:
            value = run_live(arguments[2])
        else:
            raise D1Error("accepted argv is empty/--self-test or exact --live --approval TOKEN")
    except (D1Error, OSError, KeyError, TypeError) as exc:
        print(f"P3.37 D1 blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
