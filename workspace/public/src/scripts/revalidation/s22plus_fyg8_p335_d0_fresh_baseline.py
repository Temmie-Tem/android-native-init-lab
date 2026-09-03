#!/usr/bin/env python3
"""P3.35 exact-target D0 fresh-baseline consumer.

The implementation exact-loads the reviewed P3.20 D0 state machine, but owns
a new P3.35 binding and run namespace.  It reopens only the new D1 result,
captures ``/proc/last_kmsg`` once through the raw-first helper, then invokes
the P3.35 clean-baseline classifier before the final exact-target readback.
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
P320_SOURCE = SCRIPT_DIR / "s22plus_fyg8_p320_d0_fresh_baseline.py"
ADAPTER = SCRIPT_DIR / "s22plus_fyg8_p335_stock_process_v2_adapter.py"
D1_SOURCE = SCRIPT_DIR / "s22plus_fyg8_p335_d1_fresh_baseline.py"
D1_BINDING = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p335_d1_fresh_baseline.json"
)
D1_RESULT = ROOT / (
    "workspace/private/runs/device-action-d1-p335-fresh-baseline/"
    "p335-d1-fresh-baseline-1/result.json"
)
D0_RUNTIME = SCRIPT_DIR / "device_action_d0_v2.py"
RAW_CAPTURE = SCRIPT_DIR / "device_action_raw_capture_v1.py"
PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
HOST_ADB = Path("/usr/lib/android-sdk/platform-tools/adb")
BINDING_MANIFEST = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p335_d0_fresh_baseline.json"
)

RUN_PARENT = ROOT / "workspace/private/runs/device-action-d0-p335-fresh-baseline"
RUN_DIR = RUN_PARENT / "p335-d0-fresh-baseline-1"
RUN_ARM = RUN_PARENT / "p335-d0-fresh-baseline-1.arm.json"
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
P335_RUN_ID = "c335f1e0a90b5e6d7c8a9b0c1d2e3f5b"
ORDINAL = "p335-d0-fresh-baseline-1"
BINDING_SCHEMA = "s22plus_fyg8_p335_d0_fresh_baseline_execution_binding_v1"
BINDING_ID = "s22plus-fyg8-p335-d0-fresh-baseline-v1"
AUTHORITY_PREFIX = "DEVICE-ACTION-D0-P335-FRESH-BASELINE-1-APPROVE:"
REVIEW_VERDICT = "PASS_GO_P335_D0_FRESH_BASELINE_H0_CAPABILITY_V1"
D1_REVIEW_VERDICT = "PASS_GO_P335_D1_FRESH_BASELINE_H0_CAPABILITY_V1"
D1_BINDING_SCHEMA = "s22plus_fyg8_p335_d1_fresh_baseline_execution_binding_v1"
D1_BINDING_ID = "s22plus-fyg8-p335-d1-fresh-baseline-v1"
D1_RESULT_SCHEMA = "s22plus_fyg8_p335_d1_fresh_baseline_result_v1"
D1_RESULT_VERDICT = "PASS_P335_D1_FRESH_BASELINE_EXACT_NORMAL_REBOOT_RETURN_HEALTH"
RESULT_SCHEMA = "s22plus_fyg8_p335_d0_fresh_baseline_result_v1"
RESULT_VERDICT = "PASS_P335_D0_FRESH_BASELINE_RAW_FIRST_V1"
STOP_SCHEMA = "s22plus_fyg8_p335_d0_fresh_baseline_stop_v1"
STOP_VERDICT = "STOP_P335_D0_FRESH_BASELINE_CONSUMED_NO_REPLAY"
HOST_ADB_SIZE = 716_968
HOST_ADB_SHA256 = "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
RAW_SIZE = 2_097_136


class D0Error(RuntimeError):
    """The P3.35 D0 action failed closed."""


def canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise D0Error("value is not canonical JSON") from exc


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _typed_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _typed_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _typed_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def _relative(path: Path) -> str:
    try:
        return path.absolute().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.absolute())


def _receipt(path: Path, payload: bytes, *, mode: str | None = None) -> dict[str, Any]:
    value = {"path": _relative(path), "size": len(payload), "sha256": sha256_bytes(payload)}
    if mode is not None:
        value.update({"mode": mode, "nlink": 1})
    return value


def _stable(
    path: Path,
    label: str,
    *,
    maximum: int,
    expected: Mapping[str, Any] | None = None,
    mode: int | None = None,
    owner: int | None = os.getuid(),
) -> bytes:
    direct = path.absolute()
    try:
        if direct != path or direct.resolve(strict=True) != direct:
            raise D0Error(f"{label} path is indirect")
        descriptor = os.open(
            direct,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as exc:
        raise D0Error(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or (owner is not None and before.st_uid != owner)
            or before.st_nlink != 1
            or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
            or before.st_size > maximum
        ):
            raise D0Error(f"{label} identity differs")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if any(getattr(before, item) != getattr(after, item) for item in fields):
        raise D0Error(f"{label} changed while reading")
    payload = b"".join(chunks)
    if len(payload) != before.st_size or len(payload) > maximum:
        raise D0Error(f"{label} size differs")
    if expected is not None:
        actual = _receipt(path, payload)
        if actual.get("size") != expected.get("size") or actual.get("sha256") != expected.get("sha256"):
            raise D0Error(f"{label} bytes differ")
    return payload


def _strict(payload: bytes, label: str) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise D0Error(f"{label} contains duplicate key")
            value[key] = item
        return value

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=unique,
            parse_constant=lambda item: (_ for _ in ()).throw(
                D0Error(f"{label} contains non-finite JSON: {item}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D0Error(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict) or canonical(value) != payload:
        raise D0Error(f"{label} is not a canonical object")
    return value


def _source_receipts() -> dict[str, dict[str, Any]]:
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
    return {
        name: _receipt(
            path,
            _stable(
                path,
                name,
                maximum=HOST_ADB_SIZE if name == "host_adb" else 2 * 1024 * 1024,
                owner=None if name == "host_adb" else os.getuid(),
            ),
        )
        for name, path in paths.items()
    }


def _expected_binding(
    inputs: Mapping[str, Any], review: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema": BINDING_SCHEMA,
        "binding_id": BINDING_ID,
        "action": "one exact connected read-only P3.35 fresh-baseline acquisition",
        "authority_prefix": AUTHORITY_PREFIX,
        "target": TARGET,
        "ordinal": ORDINAL,
        "inputs": dict(inputs),
        "d1_dependency": {
            "binding": _relative(D1_BINDING),
            "binding_review_verdict": D1_REVIEW_VERDICT,
            "result": _relative(D1_RESULT),
            "result_replay_authorized": False,
            "result_schema": D1_RESULT_SCHEMA,
            "result_verdict": D1_RESULT_VERDICT,
        },
        "run": {
            "parent": _relative(RUN_PARENT),
            "directory": _relative(RUN_DIR),
            "arm": _relative(RUN_ARM),
            "stop": _relative(RUN_STOP),
            "result": _relative(RESULT_PATH),
            "observer": _relative(OBSERVER_PATH),
            "raw_adb": _relative(RAW_ADB_DIR),
            "adb_snapshot": _relative(ADB_SNAPSHOT),
        },
        "bounds": {
            "observer_source": "/proc/last_kmsg",
            "observer_bytes": RAW_SIZE,
            "observer_read_count": 1,
            "observer_timeout_sec": 180,
            "read_timeout_sec": 180,
            "raw_text_maximum": 64 * 1024,
        },
        "safety": {
            "device_writes": False,
            "reboot": False,
            "partition_transfer": False,
            "download_transition": False,
            "odin": False,
            "f1_authorized": False,
            "replay_authorized": False,
            "other_targets_commanded": False,
        },
        "independent_review": dict(review),
    }


def _validated_static_inputs() -> dict[str, Any]:
    inputs = _source_receipts()
    payload = _stable(BINDING_MANIFEST, "P3.35 D0 binding", maximum=256 * 1024)
    binding = _strict(payload, "P3.35 D0 binding")
    review = binding.get("independent_review")
    if review not in (
        {"status": "review-pending", "verdict": None},
        {"status": "pass-go", "verdict": REVIEW_VERDICT},
    ):
        raise D0Error("P3.35 D0 review state differs")
    if not _typed_equal(binding, _expected_binding(inputs, review)):
        raise D0Error("P3.35 D0 binding does not match exact inputs")
    d1_payload = _stable(D1_BINDING, "P3.35 D1 binding", maximum=256 * 1024)
    d1 = _strict(d1_payload, "P3.35 D1 binding")
    if (
        d1.get("schema") != D1_BINDING_SCHEMA
        or d1.get("binding_id") != D1_BINDING_ID
        or d1.get("target") != TARGET
        or d1.get("ordinal") != "p335-d1-fresh-baseline-1"
    ):
        raise D0Error("P3.35 D1 predecessor identity differs")
    return {
        "manifest": binding,
        "manifest_payload": payload,
        "manifest_receipt": _receipt(BINDING_MANIFEST, payload),
        "authority": AUTHORITY_PREFIX + sha256_bytes(payload),
        "approval_sha256": sha256_bytes(
            (AUTHORITY_PREFIX + sha256_bytes(payload)).encode("ascii")
        ),
        "payloads": inputs,
        "d1_binding": d1,
    }


def _load_d1_result(static: Mapping[str, Any]) -> dict[str, Any]:
    payload = _stable(D1_RESULT, "P3.35 D1 result", maximum=512 * 1024, mode=0o400)
    value = _strict(payload, "P3.35 D1 result")
    d1_binding_payload = _stable(
        D1_BINDING,
        "P3.35 D1 binding",
        maximum=256 * 1024,
        expected=static["payloads"]["d1_binding"],
    )
    expected_manifest = _receipt(D1_BINDING, d1_binding_payload)
    if (
        value.get("schema") != D1_RESULT_SCHEMA
        or value.get("verdict") != D1_RESULT_VERDICT
        or value.get("execution_manifest") != expected_manifest
        or value.get("ordinal") != static["d1_binding"].get("ordinal")
        or value.get("run_id") != P335_RUN_ID
        or type(value.get("reboot_count")) is not int
        or value.get("reboot_count") != 1
    ):
        raise D0Error("P3.35 D1 result identity differs")
    expected_flags = {
        "device_contact": True,
        "live_authorized": True,
        "device_writes": False,
        "candidate_transfer": False,
        "partition_transfer": False,
        "odin_invoked": False,
        "download_transition_requested": False,
        "f1_authorized": False,
        "other_targets_commanded": False,
    }
    if any(
        type(value.get(key)) is not bool or value.get(key) != expected
        for key, expected in expected_flags.items()
    ):
        raise D0Error("P3.35 D1 result safety flags differ")
    selection = value.get("selection")
    if not isinstance(selection, dict) or set(selection) != {
        "inventory_count",
        "inventory_models",
        "inventory_sha256",
        "selected_serial_sha256",
        "selected_topology_sha256",
        "other_targets_commanded",
    }:
        raise D0Error("P3.35 D1 result selection shape differs")
    if (
        type(selection["inventory_count"]) is not int
        or selection["inventory_count"] < 1
        or not isinstance(selection["inventory_models"], list)
        or "SM_S906N" not in selection["inventory_models"]
        or selection["other_targets_commanded"] is not False
        or selection["selected_serial_sha256"] != TARGET["adb_serial_sha256"]
        or not isinstance(selection["selected_topology_sha256"], str)
        or len(selection["selected_topology_sha256"]) != 64
        or any(char not in "0123456789abcdef" for char in selection["selected_topology_sha256"])
    ):
        raise D0Error("P3.35 D1 result target selection differs")
    before = value.get("before")
    after = value.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise D0Error("P3.35 D1 result health shape differs")
    for health in (before, after):
        boot_id = health.get("boot_id_sha256")
        if (
            not isinstance(boot_id, str)
            or len(boot_id) != 64
            or any(char not in "0123456789abcdef" for char in boot_id)
        ):
            raise D0Error("P3.35 D1 result boot identity differs")
    if before["boot_id_sha256"] == after["boot_id_sha256"]:
        raise D0Error("P3.35 D1 result did not prove a changed boot")
    return {"value": value, "receipt": _receipt(D1_RESULT, payload), "path": D1_RESULT}


def _classify_clean_baseline(adapter: Any, payload: bytes) -> dict[str, Any]:
    expected = bytes.fromhex(P335_RUN_ID)
    if getattr(adapter, "STOCK_RUN_ID", None) != expected:
        raise D0Error("P3.35 adapter run ID is not bound")
    result = adapter.classify_clean_baseline(payload, expected_run_id=expected)
    if result.get("classification") != "ZERO_AMBIGUOUS" or result.get("baseline_clean") is not True:
        raise D0Error("P3.35 clean baseline classification differs")
    return result


def _load_p320() -> types.ModuleType:
    static = _validated_static_inputs()
    payload = _stable(
        P320_SOURCE,
        "P3.20 D0 source",
        maximum=2 * 1024 * 1024,
        expected=static["payloads"]["p320_source"],
    )
    module = types.ModuleType("s22plus_fyg8_p320_d0_bound_for_p335")
    module.__file__ = str(P320_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P320_SOURCE), "exec", dont_inherit=True), module.__dict__)
    except BaseException as exc:
        raise D0Error(f"P3.20 D0 source failed to load: {type(exc).__name__}") from exc
    replacements = {
        "ROOT": ROOT,
        "SCRIPT": SCRIPT,
        "SCRIPT_DIR": SCRIPT_DIR,
        "ADAPTER": ADAPTER,
        "D1_SOURCE": D1_SOURCE,
        "D1_BINDING": D1_BINDING,
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
        "P320_RUN_ID": P335_RUN_ID,
        "ORDINAL": ORDINAL,
        "BINDING_SCHEMA": BINDING_SCHEMA,
        "BINDING_ID": BINDING_ID,
        "AUTHORITY_PREFIX": AUTHORITY_PREFIX,
        "REVIEW_VERDICT": REVIEW_VERDICT,
        "D1_REVIEW_VERDICT": D1_REVIEW_VERDICT,
        "RESULT_SCHEMA": RESULT_SCHEMA,
        "RESULT_VERDICT": RESULT_VERDICT,
        "STOP_SCHEMA": STOP_SCHEMA,
        "STOP_VERDICT": STOP_VERDICT,
        "HOST_ADB_SIZE": HOST_ADB_SIZE,
        "HOST_ADB_SHA256": HOST_ADB_SHA256,
        "RAW_SIZE": RAW_SIZE,
    }
    module.__dict__.update(replacements)
    module._validated_static_inputs = _validated_static_inputs
    module._load_d1_result = _load_d1_result
    module._classify_clean_baseline = _classify_clean_baseline
    original_durable_create = module._durable_create

    def durable_create(path: Path, value: Mapping[str, Any]) -> None:
        # Keep the inherited no-replace journal mechanics while projecting the
        # durable terminal to the new P3.35 identity before publication.
        if path.name == "result.json":
            value = {
                **dict(value),
                "schema": RESULT_SCHEMA,
                "version": "device-action-d0-p335-v1",
                "verdict": RESULT_VERDICT,
            }
        original_durable_create(path, value)

    module._durable_create = durable_create
    return module


def self_test() -> dict[str, Any]:
    _validated_static_inputs()
    bound = _load_p320()
    value = bound.self_test()
    if value.get("clean_baseline") is not True or value.get("device_contact") is not False:
        raise D0Error("P3.35 D0 fixture result differs")
    return {
        "schema": "s22plus_fyg8_p335_d0_fresh_baseline_fixture_h0",
        "verdict": "PASS_P335_D0_FRESH_BASELINE_FIXTURE_H0",
        "ordinal": ORDINAL,
        "run_id": P335_RUN_ID,
        "raw_first": True,
        "clean_baseline": True,
        "p335_d1_dependency": True,
        "device_contact": False,
        "approval_created": False,
        "live_authorized": False,
    }


def run_live(approval: str) -> dict[str, Any]:
    if not isinstance(approval, str) or not approval:
        raise D0Error("P3.35 D0 approval is absent")
    bound = _load_p320()
    try:
        value = bound.run_live(approval)
    except Exception as exc:
        if isinstance(exc, bound.D0Error):
            raise D0Error(str(exc)) from exc
        raise
    result = dict(value)
    result.update(
        {
            "schema": RESULT_SCHEMA,
            "version": "device-action-d0-p335-v1",
            "verdict": RESULT_VERDICT,
            "ordinal": ORDINAL,
            "run_id": P335_RUN_ID,
        }
    )
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
        print(f"P3.35 D0 blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
