#!/usr/bin/env python3
"""P3.36 exact-target D0 fresh-baseline consumer.

This wrapper reuses the finalized P3.35/P3.20 raw-first state machine while
owning a new P3.36 D1 dependency and no-replay namespace.  The P3.36 stock
adapter is deliberately a final-repin dependency; until it exists, this
module can only perform a host-side pending self-test and cannot arm D0.
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
P335_SOURCE = SCRIPT_DIR / "s22plus_fyg8_p335_d0_fresh_baseline.py"
P320_SOURCE = SCRIPT_DIR / "s22plus_fyg8_p320_d0_fresh_baseline.py"
ADAPTER = SCRIPT_DIR / "s22plus_fyg8_p336_stock_process_v2_adapter.py"
D1_SOURCE = SCRIPT_DIR / "s22plus_fyg8_p336_d1_fresh_baseline.py"
D1_BINDING = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p336_d1_fresh_baseline.json"
)
D1_RESULT = ROOT / (
    "workspace/private/runs/device-action-d1-p336-fresh-baseline/"
    "p336-d1-fresh-baseline-1/result.json"
)
D0_RUNTIME = SCRIPT_DIR / "device_action_d0_v2.py"
RAW_CAPTURE = SCRIPT_DIR / "device_action_raw_capture_v1.py"
PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
HOST_ADB = Path("/usr/lib/android-sdk/platform-tools/adb")
BINDING_MANIFEST = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p336_d0_fresh_baseline.json"
)

RUN_PARENT = ROOT / "workspace/private/runs/device-action-d0-p336-fresh-baseline"
RUN_DIR = RUN_PARENT / "p336-d0-fresh-baseline-1"
RUN_ARM = RUN_PARENT / "p336-d0-fresh-baseline-1.arm.json"
RUN_STOP = RUN_DIR / "stop.json"
RESULT_PATH = RUN_DIR / "result.json"
OBSERVER_PATH = RUN_DIR / "baseline-observer.bin"
RAW_ADB_DIR = RUN_DIR / "raw-adb"
ADB_SNAPSHOT = RUN_DIR / "adb-05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"

TARGET = {
    "model": "SM-S906N",
    "codename": "g0q",
    "build": "S906NKSS7FYG8",
    "adb_serial_sha256": (
        "c5302ccc08374d408ca3ec4df0ef23770d5ecd35ce173b7d150c4316e9a0757b"
    ),
}
P336_RUN_ID = "c336f1e0a90b5e6d7c8a9b0c1d2e3f4b"
ORDINAL = "p336-d0-fresh-baseline-1"
BINDING_SCHEMA = "s22plus_fyg8_p336_d0_fresh_baseline_execution_binding_v1"
BINDING_ID = "s22plus-fyg8-p336-d0-fresh-baseline-v1"
AUTHORITY_PREFIX = "DEVICE-ACTION-D0-P336-FRESH-BASELINE-1-APPROVE:"
REVIEW_VERDICT = "PASS_GO_P336_D0_FRESH_BASELINE_H0_CAPABILITY_V1"
D1_REVIEW_VERDICT = "PASS_GO_P336_D1_FRESH_BASELINE_H0_CAPABILITY_V1"
D1_BINDING_SCHEMA = "s22plus_fyg8_p336_d1_fresh_baseline_execution_binding_v1"
D1_BINDING_ID = "s22plus-fyg8-p336-d1-fresh-baseline-v1"
D1_RESULT_SCHEMA = "s22plus_fyg8_p336_d1_fresh_baseline_result_v1"
D1_RESULT_VERDICT = "PASS_P336_D1_FRESH_BASELINE_EXACT_NORMAL_REBOOT_RETURN_HEALTH"
RESULT_SCHEMA = "s22plus_fyg8_p336_d0_fresh_baseline_result_v1"
RESULT_VERDICT = "PASS_P336_D0_FRESH_BASELINE_RAW_FIRST_V1"
STOP_SCHEMA = "s22plus_fyg8_p336_d0_fresh_baseline_stop_v1"
STOP_VERDICT = "STOP_P336_D0_FRESH_BASELINE_CONSUMED_NO_REPLAY"
HOST_ADB_SIZE = 716_968
HOST_ADB_SHA256 = "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
RAW_SIZE = 2_097_136
ADAPTER_PLACEHOLDER = {
    "status": "P336_ADAPTER_FINAL_REPIN_REQUIRED",
    "path": "workspace/public/src/scripts/revalidation/s22plus_fyg8_p336_stock_process_v2_adapter.py",
    "size": 0,
    "sha256": "0" * 64,
}


class D0Error(RuntimeError):
    """The P3.36 D0 action failed closed."""


def canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise D0Error("value is not canonical JSON") from exc


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
            raise D0Error(f"{label} path is indirect")
        descriptor = os.open(direct, os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise D0Error(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise D0Error(f"{label} identity differs")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, item) != getattr(after, item) for item in fields):
        raise D0Error(f"{label} changed while reading")
    payload = b"".join(chunks)
    if len(payload) != before.st_size or len(payload) > maximum:
        raise D0Error(f"{label} size differs")
    if expected is not None and (_receipt(path, payload)["size"], _receipt(path, payload)["sha256"]) != (expected.get("size"), expected.get("sha256")):
        raise D0Error(f"{label} bytes differ")
    return payload


def _load_p335() -> types.ModuleType:
    payload = _stable(P335_SOURCE, "P3.35 D0 source", maximum=2 * 1024 * 1024)
    module = types.ModuleType("s22plus_fyg8_p335_d0_bound_for_p336")
    module.__file__ = str(P335_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P335_SOURCE), "exec", dont_inherit=True), module.__dict__)
    except BaseException as exc:
        raise D0Error(f"P3.35 D0 source failed to load: {type(exc).__name__}") from exc
    replacements = {
        "ROOT": ROOT,
        "SCRIPT": SCRIPT,
        "SCRIPT_DIR": SCRIPT_DIR,
        "P320_SOURCE": P320_SOURCE,
        "ADAPTER": ADAPTER,
        "D1_SOURCE": D1_SOURCE,
        "D1_BINDING": D1_BINDING,
        "D1_RESULT": D1_RESULT,
        "D0_RUNTIME": D0_RUNTIME,
        "RAW_CAPTURE": RAW_CAPTURE,
        "PROFILE": PROFILE,
        "HOST_ADB": HOST_ADB,
        "BINDING_MANIFEST": BINDING_MANIFEST,
        "RUN_PARENT": RUN_PARENT,
        "RUN_DIR": RUN_DIR,
        "RUN_ARM": RUN_ARM,
        "RUN_STOP": RUN_STOP,
        "RESULT_PATH": RESULT_PATH,
        "OBSERVER_PATH": OBSERVER_PATH,
        "RAW_ADB_DIR": RAW_ADB_DIR,
        "ADB_SNAPSHOT": ADB_SNAPSHOT,
        "TARGET": TARGET,
        "P335_RUN_ID": P336_RUN_ID,
        "ORDINAL": ORDINAL,
        "BINDING_SCHEMA": BINDING_SCHEMA,
        "BINDING_ID": BINDING_ID,
        "AUTHORITY_PREFIX": AUTHORITY_PREFIX,
        "REVIEW_VERDICT": REVIEW_VERDICT,
        "D1_REVIEW_VERDICT": D1_REVIEW_VERDICT,
        "D1_BINDING_SCHEMA": D1_BINDING_SCHEMA,
        "D1_BINDING_ID": D1_BINDING_ID,
        "D1_RESULT_SCHEMA": D1_RESULT_SCHEMA,
        "D1_RESULT_VERDICT": D1_RESULT_VERDICT,
        "RESULT_SCHEMA": RESULT_SCHEMA,
        "RESULT_VERDICT": RESULT_VERDICT,
        "STOP_SCHEMA": STOP_SCHEMA,
        "STOP_VERDICT": STOP_VERDICT,
        "HOST_ADB_SIZE": HOST_ADB_SIZE,
        "HOST_ADB_SHA256": HOST_ADB_SHA256,
        "RAW_SIZE": RAW_SIZE,
    }
    module.__dict__.update(replacements)
    def source_receipts() -> dict[str, dict[str, Any]]:
        paths = {
            "d0_source": SCRIPT,
            "p320_source": P320_SOURCE,
            "adapter": ADAPTER,
            "d1_source": D1_SOURCE,
            "d1_binding": D1_BINDING,
            "d0_runtime": D0_RUNTIME,
            "raw_capture": RAW_CAPTURE,
            "profile": PROFILE,
            "host_adb": HOST_ADB,
        }
        value: dict[str, dict[str, Any]] = {}
        for name, path in paths.items():
            if name == "adapter" and not path.exists():
                value[name] = dict(ADAPTER_PLACEHOLDER)
                value[name].pop("status", None)
                continue
            value[name] = _receipt(
                path,
                module._stable(
                    path,
                    name,
                    maximum=HOST_ADB_SIZE if name == "host_adb" else 2 * 1024 * 1024,
                    owner=None if name == "host_adb" else os.getuid(),
                ),
            )
        return value

    original_expected = module._expected_binding

    def expected_binding(inputs: Mapping[str, Any], review: Mapping[str, Any]) -> dict[str, Any]:
        value = original_expected(inputs, review)
        value["action"] = "one exact connected read-only P3.36 fresh-baseline acquisition"
        adapter_receipt = inputs.get("adapter")
        if (
            not isinstance(adapter_receipt, dict)
            or adapter_receipt.get("size") == 0
            or adapter_receipt.get("sha256") == "0" * 64
        ):
            value["adapter_repin"] = dict(ADAPTER_PLACEHOLDER)
        else:
            value["adapter_repin"] = dict(adapter_receipt)
        return value

    module._source_receipts = source_receipts
    module._expected_binding = expected_binding

    def validated_static_inputs() -> dict[str, Any]:
        inputs = module._source_receipts()
        payload = module._stable(BINDING_MANIFEST, "P3.36 D0 binding", maximum=256 * 1024)
        binding = module._strict(payload, "P3.36 D0 binding")
        review = binding.get("independent_review")
        if review not in (
            {"status": "review-pending", "verdict": None},
            {"status": "pass-go", "verdict": REVIEW_VERDICT},
        ):
            raise module.D0Error("P3.36 D0 review state differs")
        expected = module._expected_binding(inputs, review)
        if binding != expected:
            # A review-pending D0 binding may deliberately retain the
            # placeholder while the final adapter/common closure is being
            # repinned.  It remains non-armable; once the binding carries the
            # exact adapter receipt, the strict path below is used.
            pending_inputs = dict(inputs)
            pending_adapter = dict(ADAPTER_PLACEHOLDER)
            pending_adapter.pop("status", None)
            pending_inputs["adapter"] = pending_adapter
            if binding != module._expected_binding(pending_inputs, review):
                raise module.D0Error("P3.36 D0 binding does not match exact inputs")
            inputs = pending_inputs
        d1_payload = module._stable(D1_BINDING, "P3.36 D1 binding", maximum=256 * 1024)
        d1 = module._strict(d1_payload, "P3.36 D1 binding")
        if (
            d1.get("schema") != D1_BINDING_SCHEMA
            or d1.get("binding_id") != D1_BINDING_ID
            or d1.get("target") != TARGET
            or d1.get("ordinal") != "p336-d1-fresh-baseline-1"
        ):
            raise module.D0Error("P3.36 D1 predecessor identity differs")
        return {
            "manifest": binding,
            "manifest_payload": payload,
            "manifest_receipt": module._receipt(BINDING_MANIFEST, payload),
            "authority": AUTHORITY_PREFIX + sha256_bytes(payload),
            "approval_sha256": sha256_bytes(
                (AUTHORITY_PREFIX + sha256_bytes(payload)).encode("ascii")
            ),
            "payloads": inputs,
            "d1_binding": d1,
        }

    original_load_p320 = module._load_p320

    def load_p320() -> types.ModuleType:
        bound = original_load_p320()
        original_load_adapter = bound._load_adapter

        def load_adapter(adapter_payload: bytes) -> Any:
            loaded = original_load_adapter(adapter_payload)
            parent = getattr(loaded, "_P335", None)
            parser = getattr(parent, "_P334", None)
            if parent is not None and parser is not None:
                for name in (
                    "_ORIGINAL_CLASSIFY_OBSERVATION",
                    "_ORIGINAL_CLASSIFY_CLEAN_BASELINE",
                ):
                    if not callable(getattr(parent, name, None)):
                        value = getattr(parser, name, None)
                        if callable(value):
                            setattr(parent, name, value)
            return loaded

        bound._load_adapter = load_adapter
        return bound

    module._load_p320 = load_p320
    module._validated_static_inputs = validated_static_inputs
    return module


def _source_receipts() -> dict[str, dict[str, Any]]:
    return _load_p335()._source_receipts()


def _expected_binding(inputs: Mapping[str, Any], review: Mapping[str, Any]) -> dict[str, Any]:
    return _load_p335()._expected_binding(inputs, review)


def _validated_static_inputs() -> dict[str, Any]:
    bound = _load_p335()
    try:
        return bound._validated_static_inputs()
    except Exception as exc:
        if isinstance(exc, bound.D0Error):
            raise D0Error(str(exc)) from exc
        raise


def _adapter_ready(static: Mapping[str, Any]) -> bool:
    item = static["payloads"].get("adapter")
    return (
        ADAPTER.is_file()
        and item != ADAPTER_PLACEHOLDER
        and item.get("size", 0) > 0
        and isinstance(item.get("sha256"), str)
        and len(item["sha256"]) == 64
        and set(item["sha256"]) <= set("0123456789abcdef")
    )


def self_test() -> dict[str, Any]:
    static = _validated_static_inputs()
    if not _adapter_ready(static):
        return {
            "schema": "s22plus_fyg8_p336_d0_fresh_baseline_fixture_h0",
            "verdict": "PENDING_P336_D0_ADAPTER_FINAL_REPIN_REQUIRED",
            "ordinal": ORDINAL,
            "run_id": P336_RUN_ID,
            "raw_first": True,
            "clean_baseline": None,
            "adapter_repin_required": True,
            "device_contact": False,
            "approval_created": False,
            "live_authorized": False,
        }
    bound = _load_p335()
    value = bound.self_test()
    if value.get("clean_baseline") is not True or value.get("device_contact") is not False:
        raise D0Error("P3.36 D0 fixture result differs")
    return {
        "schema": "s22plus_fyg8_p336_d0_fresh_baseline_fixture_h0",
        "verdict": "PASS_P336_D0_FRESH_BASELINE_FIXTURE_H0",
        "ordinal": ORDINAL,
        "run_id": P336_RUN_ID,
        "raw_first": True,
        "clean_baseline": True,
        "adapter_repin_required": False,
        "device_contact": False,
        "approval_created": False,
        "live_authorized": False,
    }


def run_live(approval: str) -> dict[str, Any]:
    if not isinstance(approval, str) or not approval:
        raise D0Error("P3.36 D0 approval is absent")
    static = _validated_static_inputs()
    if not _adapter_ready(static):
        raise D0Error("P3.36 adapter final repin is required before D0 arm")
    bound = _load_p335()
    try:
        value = bound.run_live(approval)
    except Exception as exc:
        if isinstance(exc, bound.D0Error):
            raise D0Error(str(exc)) from exc
        raise
    result = dict(value)
    result.update({
        "schema": RESULT_SCHEMA,
        "version": "device-action-d0-p336-v1",
        "verdict": RESULT_VERDICT,
        "ordinal": ORDINAL,
        "run_id": P336_RUN_ID,
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
            raise D0Error("accepted argv is empty/--self-test or exact --live --approval TOKEN")
    except (D0Error, OSError, KeyError, TypeError) as exc:
        print(f"P3.36 D0 blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
