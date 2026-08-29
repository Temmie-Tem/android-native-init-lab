#!/usr/bin/env python3
"""H0-qualified P3.19 D1 fresh-baseline successor with raw-first pre-start evidence.

Default execution is a no-device fixture.  Live execution remains mechanically
blocked while the V3 binding is review-pending and later requires the exact
binding-derived approval.  The consumed V1 arm/run is evidence only and can
never be selected by this successor.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve(strict=True)
SCRIPT_DIR = SCRIPT.parent
BINDING_MANIFEST = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d1_fresh_baseline_v3.json"
)
V1_SOURCE = SCRIPT_DIR / "s22plus_fyg8_p319_d1_fresh_baseline.py"
V1_BINDING = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d1_fresh_baseline_v1.json"
)
V2_SOURCE = SCRIPT_DIR / "s22plus_fyg8_p319_d1_fresh_baseline_v2.py"
V2_BINDING = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d1_fresh_baseline_v2.json"
)
D0_RUNTIME = SCRIPT_DIR / "device_action_d0_v2.py"
RAW_CAPTURE = SCRIPT_DIR / "device_action_raw_capture_v1.py"
P318_WRAPPER = SCRIPT_DIR / "s22plus_fyg8_p318_baseline_rotation_d1.py"
P296_PRIMITIVE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p296/d1-baseline-rotation/"
    "s22plus_fyg8_p296_baseline_rotation_d1.py"
)
PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
HOST_ADB = Path("/usr/lib/android-sdk/platform-tools/adb")
V1_ARM = ROOT / (
    "workspace/private/runs/device-action-d1-p319-fresh-baseline/"
    "p319-fresh-baseline-1.arm.json"
)
V1_STOP = ROOT / (
    "workspace/private/runs/device-action-d1-p319-fresh-baseline/"
    "p319-fresh-baseline-1/stop.json"
)
V2_ARM = ROOT / (
    "workspace/private/runs/device-action-d1-p319-fresh-baseline-v2/"
    "p319-fresh-baseline-2.arm.json"
)
V2_STOP = ROOT / (
    "workspace/private/runs/device-action-d1-p319-fresh-baseline-v2/"
    "p319-fresh-baseline-2/stop.json"
)

RUN_PARENT = ROOT / "workspace/private/runs/device-action-d1-p319-fresh-baseline-v3"
RUN_DIR = RUN_PARENT / "p319-fresh-baseline-3"
RUN_ARM = RUN_PARENT / "p319-fresh-baseline-3.arm.json"
RUN_STOP = RUN_DIR / "stop.json"
RAW_ROOT = RUN_PARENT / "p319-fresh-baseline-3-raw"
RAW_ADB_DIR = RAW_ROOT / "raw-adb"
ADB_SNAPSHOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/d1-fresh-baseline-v3/adb-"
    "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
)

TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
BINDING_SCHEMA = "s22plus_fyg8_p319_d1_fresh_baseline_execution_binding_v3"
BINDING_ID = "s22plus-fyg8-p319-d1-fresh-baseline-v3"
AUTHORITY_PREFIX = "DEVICE-ACTION-D1-P319-FRESH-BASELINE-V3-APPROVE:"
REVIEW_VERDICT = "PASS_GO_P319_D1_FRESH_BASELINE_CANONICAL_ARM_V3_H0_CAPABILITY_V1"
ARM_SCHEMA = "s22plus_fyg8_p319_d1_fresh_baseline_arm_v3"
START_SCHEMA = "s22plus_fyg8_p319_d1_fresh_baseline_start_v3"
RESULT_SCHEMA = "s22plus_fyg8_p319_d1_fresh_baseline_v3_result"
RESULT_VERDICT = "PASS_P319_D1_FRESH_BASELINE_V3_EXACT_NORMAL_REBOOT_RETURN_HEALTH"
STOP_SCHEMA = "s22plus_fyg8_p319_d1_fresh_baseline_v3_stop"
STOP_VERDICT = "STOP_P319_D1_FRESH_BASELINE_V3_CONSUMED_NO_REPLAY"
RAW_INVENTORY_SCHEMA = "s22plus_fyg8_p319_d1_fresh_baseline_v3_raw_inventory"
RAW_HANDLE_LABELS = frozenset(
    {
        "adb-inventory",
        "adb-get-devpath",
        "adb-read-only-shell",
        "adb-normal-reboot",
    }
)
MAX_TEXT = 4 * 1024 * 1024
HEX64_RE = re.compile(r"[0-9a-f]{64}")
SERIAL_RE = re.compile(r"[A-Za-z0-9._:-]{1,128}")
DEVPATH_RE = re.compile(r"usb:[0-9]+(?:-[0-9]+(?:\.[0-9]+)*)?")

EXPECTED = {
    "v1_source": (48_354, "e0fa9d40e58e2ab372fa3f89005b51a33e17aeb47c21c2b42cdb0bbe35edad55"),
    "v1_binding": (4_128, "0a91beec8cad13622bb29c2f7865a08d37fd4531da984b9423024f6f7b9dd63b"),
    "d0_runtime": (44_582, "e71894396ca0c9ba0657a1c83d45883b99f53887c1fb87076ea0a38bbee5c37a"),
    "raw_capture": (25_006, "410e260129c0c50dca29b008dc7cf1051ee007816ab18bea76aeae62505ca0e4"),
    "p318_wrapper": (30_648, "2b798b4ab73ee0ac9cc5c40c007e470f54083e460171852e844276413a95a706"),
    "p296_primitive": (18_578, "bfec4bc9c947e098b6a18134a805524aa8fe8103edd5ddc4bc3b398895cad8ea"),
    "profile": (2_285, "7afa7b690b71eabca14c99e83efc55bdb453256bcd40f7ccdf5d41bed78d6c28"),
    "host_adb": (716_968, "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"),
    "v1_arm": (708, "1d64712e342968ae6a3574104248ea93f485cd8247db6c646bc47f57275d8aa7"),
    "v1_stop": (943, "ad0cae49fd88cadbcb6f7be54afca6448b3fa4cd2cb2b02a1c0bfab2ab6bc326"),
    "v2_source": (66_357, "9443c81cd51e23a24f48a0f43573e1449cfa188b3cd1c69e6f6f11644d15d478"),
    "v2_binding": (5_351, "65e2953ecdcb55a0b5b21614e181c7ed8fe4daafaadda5e7319ae142ad9fbae9"),
    "v2_arm": (773, "86dfc3ef18c42e210f0b72f943da1de3ab4a09e559359a63e7d093e81846ee84"),
    "v2_stop": (1_989, "bc43872717fc988be3f587ccc280cb7cfdf5272a28b04f290b1bdc0b97f95acc"),
}

FAILURES = frozenset(
    {
        ("raw-capture-bind", "RAW_CAPTURE_NAMESPACE"),
        ("inventory-read", "INVENTORY_READ"),
        ("inventory-parse", "INVENTORY_FORMAT"),
        ("inventory-select", "INVENTORY_CARDINALITY"),
        ("inventory-select", "INVENTORY_STATE"),
        ("serial-identity", "SERIAL_IDENTITY"),
        ("topology-read", "TOPOLOGY_READ"),
        ("topology-identity", "TOPOLOGY_IDENTITY"),
        ("properties-read", "HEALTH_PROPERTIES_READ"),
        ("root-health-read", "HEALTH_ROOT_READ"),
        ("usb-snapshot", "USB_SNAPSHOT"),
        ("health-validation", "HEALTH_INVALID"),
        ("start-publication", "START_PUBLICATION"),
        ("reboot-dispatch", "REBOOT_COMMAND"),
        ("poll-inventory", "POLL_INVENTORY"),
        ("returned-health", "RETURN_HEALTH"),
        ("namespace-publication", "NAMESPACE_PUBLICATION"),
        ("internal", "UNCLASSIFIED"),
    }
)


class SuccessorError(RuntimeError):
    """The V3 successor failed closed."""


class CanonicalArmAlreadyExists(SuccessorError):
    """The V3 arm namespace is already owned; replay is forbidden."""


class ClassifiedFailure(SuccessorError):
    def __init__(self, failure_site: str, failure_code: str):
        if (failure_site, failure_code) not in FAILURES:
            raise SuccessorError("unallowlisted failure classification")
        super().__init__(failure_code)
        self.failure_site = failure_site
        self.failure_code = failure_code


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
        raise SuccessorError("value is not canonical JSON") from exc


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise SuccessorError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _strict(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload, object_pairs_hook=_unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SuccessorError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict) or canonical(value) != payload:
        raise SuccessorError(f"{label} is not a canonical object")
    return value


def _identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _stable(
    path: Path,
    label: str,
    *,
    maximum: int,
    expected: tuple[int, str] | None = None,
    mode: int | None = None,
    nlink: int = 1,
    owner: int | None = os.getuid(),
) -> bytes:
    direct = path.absolute()
    if direct != path or path.resolve(strict=True) != direct:
        raise SuccessorError(f"{label} path is indirect")
    before = path.stat(follow_symlinks=False)
    if (
        not stat.S_ISREG(before.st_mode)
        or (owner is not None and before.st_uid != owner)
        or before.st_nlink != nlink
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or before.st_size > maximum
    ):
        raise SuccessorError(f"{label} identity differs")
    payload = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    if _identity(before) != _identity(after) or len(payload) != before.st_size:
        raise SuccessorError(f"{label} changed while reading")
    digest = hashlib.sha256(payload).hexdigest()
    if expected is not None and (len(payload), digest) != expected:
        raise SuccessorError(f"{label} bytes differ")
    return payload


def _relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _receipt(path: Path, payload: bytes, *, mode: str | None = None) -> dict[str, Any]:
    value = {
        "path": _relative(path),
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    if mode is not None:
        value.update({"mode": mode, "nlink": 1})
    return value


def _typed_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            _typed_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _typed_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def _compile(name: str, path: Path, payload: bytes) -> Any:
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    prior = sys.modules.get(name)
    sys.modules[name] = module
    try:
        exec(compile(payload, str(path), "exec", dont_inherit=True), module.__dict__)
    except BaseException as exc:
        raise SuccessorError(f"pinned module failed to load: {name}") from exc
    finally:
        if prior is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
    return module


def _input_payloads() -> dict[str, bytes]:
    return {
        "successor_source": _stable(SCRIPT, "V3 successor source", maximum=1024 * 1024),
        "v1_source": _stable(V1_SOURCE, "V1 source", maximum=512 * 1024, expected=EXPECTED["v1_source"]),
        "v1_binding": _stable(V1_BINDING, "V1 binding", maximum=64 * 1024, expected=EXPECTED["v1_binding"]),
        "v2_source": _stable(V2_SOURCE, "V2 source", maximum=512 * 1024, expected=EXPECTED["v2_source"]),
        "v2_binding": _stable(V2_BINDING, "V2 binding", maximum=64 * 1024, expected=EXPECTED["v2_binding"]),
        "d0_runtime": _stable(D0_RUNTIME, "D0 runtime", maximum=128 * 1024, expected=EXPECTED["d0_runtime"]),
        "raw_capture": _stable(RAW_CAPTURE, "raw capture", maximum=128 * 1024, expected=EXPECTED["raw_capture"]),
        "p318_wrapper": _stable(P318_WRAPPER, "P3.18 wrapper", maximum=128 * 1024, expected=EXPECTED["p318_wrapper"]),
        "p296_primitive": _stable(P296_PRIMITIVE, "P2.96 primitive", maximum=128 * 1024, expected=EXPECTED["p296_primitive"]),
        "profile": _stable(PROFILE, "target profile", maximum=64 * 1024, expected=EXPECTED["profile"]),
        "host_adb": _stable(
            HOST_ADB,
            "host ADB",
            maximum=EXPECTED["host_adb"][0],
            expected=EXPECTED["host_adb"],
            owner=None,
        ),
        "v1_arm": _stable(V1_ARM, "consumed V1 arm", maximum=64 * 1024, expected=EXPECTED["v1_arm"], mode=0o400),
        "v1_stop": _stable(V1_STOP, "consumed V1 stop", maximum=64 * 1024, expected=EXPECTED["v1_stop"], mode=0o400),
        "v2_arm": _stable(V2_ARM, "consumed V2 arm", maximum=64 * 1024, expected=EXPECTED["v2_arm"], mode=0o400),
        "v2_stop": _stable(V2_STOP, "consumed V2 stop", maximum=64 * 1024, expected=EXPECTED["v2_stop"], mode=0o400),
    }


def _expected_manifest(payloads: Mapping[str, bytes], review: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": BINDING_SCHEMA,
        "binding_id": BINDING_ID,
        "action": "one exact attended normal Android reboot with raw-first D1 evidence",
        "authority_prefix": AUTHORITY_PREFIX,
        "target": TARGET,
        "successor": _receipt(SCRIPT, payloads["successor_source"]),
        "inputs": {
            "v1_source": _receipt(V1_SOURCE, payloads["v1_source"]),
            "v1_binding": _receipt(V1_BINDING, payloads["v1_binding"]),
            "v2_source": _receipt(V2_SOURCE, payloads["v2_source"]),
            "v2_binding": _receipt(V2_BINDING, payloads["v2_binding"]),
            "d0_runtime": _receipt(D0_RUNTIME, payloads["d0_runtime"]),
            "raw_capture": _receipt(RAW_CAPTURE, payloads["raw_capture"]),
            "p318_wrapper": _receipt(P318_WRAPPER, payloads["p318_wrapper"]),
            "p296_primitive": _receipt(P296_PRIMITIVE, payloads["p296_primitive"]),
            "profile": _receipt(PROFILE, payloads["profile"]),
            "host_adb": _receipt(HOST_ADB, payloads["host_adb"]),
        },
        "consumed_v1": {
            "ordinal": "d1-fresh-baseline-1",
            "binding": _receipt(V1_BINDING, payloads["v1_binding"]),
            "arm": _receipt(V1_ARM, payloads["v1_arm"], mode="0400"),
            "stop": _receipt(V1_STOP, payloads["v1_stop"], mode="0400"),
            "verdict": "STOP_P319_D1_FRESH_BASELINE_CONSUMED_NO_REPLAY",
            "replay_authorized": False,
        },
        "consumed_v2": {
            "ordinal": "d1-fresh-baseline-2",
            "binding": _receipt(V2_BINDING, payloads["v2_binding"]),
            "arm": _receipt(V2_ARM, payloads["v2_arm"], mode="0400"),
            "stop": _receipt(V2_STOP, payloads["v2_stop"], mode="0400"),
            "verdict": "STOP_P319_D1_FRESH_BASELINE_V2_CONSUMED_NO_REPLAY",
            "failure_site": "namespace-publication",
            "failure_code": "NAMESPACE_PUBLICATION",
            "reboot_dispatch_possible": False,
            "private_raw_evidence_preserved": False,
            "result_reusable": False,
            "replay_authorized": False,
        },
        "run": {
            "ordinal": "d1-fresh-baseline-3",
            "parent": _relative(RUN_PARENT),
            "directory": _relative(RUN_DIR),
            "arm": _relative(RUN_ARM),
            "stop": _relative(RUN_STOP),
            "raw_root": _relative(RAW_ROOT),
            "raw_adb": _relative(RAW_ADB_DIR),
            "adb_snapshot": _relative(ADB_SNAPSHOT),
        },
        "bounds": {
            "reboot_count": 1,
            "other_target_commands": 0,
            "inventory_timeout_sec": 10,
            "read_timeout_sec": 180,
            "initiation_bound_sec": 60,
            "return_bound_sec": 240,
            "raw_text_maximum": MAX_TEXT,
        },
        "failure_taxonomy": [
            {"failure_site": site, "failure_code": code}
            for site, code in sorted(FAILURES)
        ],
        "safety": {
            "partition_payload": False,
            "odin": False,
            "download_transition": False,
            "f1_authorized": False,
            "candidate_transfer": False,
            "replay_authorized": False,
            "other_targets_commanded": False,
        },
        "independent_review": dict(review),
    }


def _validated_static_inputs() -> dict[str, Any]:
    payloads = _input_payloads()
    binding_payload = _stable(BINDING_MANIFEST, "V3 binding", maximum=256 * 1024)
    binding = _strict(binding_payload, "V3 binding")
    review = binding.get("independent_review")
    if review not in (
        {"status": "review-pending", "verdict": None},
        {"status": "pass-go", "verdict": REVIEW_VERDICT},
    ):
        raise SuccessorError("V3 review state differs")
    if not _typed_equal(binding, _expected_manifest(payloads, review)):
        raise SuccessorError("V3 binding does not match exact inputs")
    receipt = _receipt(BINDING_MANIFEST, binding_payload)
    authority = AUTHORITY_PREFIX + receipt["sha256"]
    return {
        "manifest": binding,
        "manifest_payload": binding_payload,
        "manifest_receipt": receipt,
        "authority": authority,
        "approval_sha256": hashlib.sha256(authority.encode("ascii")).hexdigest(),
        "payloads": payloads,
    }


def _validate_consumed_v2(payloads: Mapping[str, bytes]) -> None:
    binding = _strict(payloads["v2_binding"], "consumed V2 binding")
    if (
        binding.get("independent_review")
        != {
            "status": "pass-go",
            "verdict": "PASS_GO_P319_D1_FRESH_BASELINE_RAW_FIRST_V2_H0_CAPABILITY_V1",
        }
        or binding.get("successor") != _receipt(V2_SOURCE, payloads["v2_source"])
    ):
        raise SuccessorError("consumed V2 binding authority differs")
    try:
        arm = json.loads(payloads["v2_arm"], object_pairs_hook=_unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SuccessorError("consumed V2 arm is not strict JSON") from exc
    stop = _strict(payloads["v2_stop"], "consumed V2 stop")
    expected_binding = _receipt(V2_BINDING, payloads["v2_binding"])
    expected_arm = _receipt(V2_ARM, payloads["v2_arm"], mode="0400")
    if (
        arm.get("schema") != "s22plus_fyg8_p319_d1_fresh_baseline_arm_v2"
        or arm.get("ordinal") != "d1-fresh-baseline-2"
        or arm.get("execution_manifest") != expected_binding
        or arm.get("consumed") is not True
        or arm.get("device_contact_before_arm") is not False
    ):
        raise SuccessorError("consumed V2 arm semantics differ")
    required_stop = {
        "schema": "s22plus_fyg8_p319_d1_fresh_baseline_v2_stop",
        "verdict": "STOP_P319_D1_FRESH_BASELINE_V2_CONSUMED_NO_REPLAY",
        "ordinal": "d1-fresh-baseline-2",
        "execution_manifest": expected_binding,
        "arm_receipt": expected_arm,
        "failure_site": "namespace-publication",
        "failure_code": "NAMESPACE_PUBLICATION",
        "stage": "during-arm-publication",
        "reboot_dispatch_possible": False,
        "private_raw_evidence_preserved": False,
        "result_reusable": False,
        "replay_authorized": False,
    }
    if any(stop.get(key) != value for key, value in required_stop.items()):
        raise SuccessorError("consumed V2 stop semantics differ")
    if (
        stop.get("start_present") is not False
        or stop.get("result_present") is not False
        or stop.get("raw_evidence", {}).get("complete") is not False
    ):
        raise SuccessorError("consumed V2 stop device boundary differs")


def _validated_execution_inputs(static: Mapping[str, Any]) -> dict[str, Any]:
    _validate_consumed_v2(static["payloads"])
    v1 = _compile("p319_d1_v3_bound_v1", V1_SOURCE, static["payloads"]["v1_source"])
    raw = _compile("p319_d1_v3_bound_raw", RAW_CAPTURE, static["payloads"]["raw_capture"])
    v1_inputs = v1._validated_inputs()
    if (
        v1_inputs["manifest_receipt"]
        != static["manifest"]["consumed_v1"]["binding"]
        or v1_inputs["manifest"]["independent_review"]
        != {
            "status": "pass-go",
            "verdict": "PASS_GO_P319_D1_FRESH_BASELINE_H0_CAPABILITY_V1",
        }
    ):
        raise SuccessorError("reviewed V1 transitive binding differs")
    for name, path in (
        ("v1_source", V1_SOURCE),
        ("v1_binding", V1_BINDING),
        ("v2_source", V2_SOURCE),
        ("v2_binding", V2_BINDING),
        ("v2_source", V2_SOURCE),
        ("v2_binding", V2_BINDING),
        ("raw_capture", RAW_CAPTURE),
        ("v1_arm", V1_ARM),
        ("v1_stop", V1_STOP),
        ("v2_arm", V2_ARM),
        ("v2_stop", V2_STOP),
        ("v2_arm", V2_ARM),
        ("v2_stop", V2_STOP),
    ):
        if _stable(
            path,
            f"post-load {name}",
            maximum=max(len(static["payloads"][name]), 1),
            expected=(
                len(static["payloads"][name]),
                hashlib.sha256(static["payloads"][name]).hexdigest(),
            ),
            mode=0o400 if name in {"v1_arm", "v1_stop", "v2_arm", "v2_stop"} else None,
        ) != static["payloads"][name]:
            raise SuccessorError(f"post-load {name} differs")
    return {**dict(static), "v1": v1, "raw": raw, "v1_inputs": v1_inputs}


def _pinned_base(inputs: Mapping[str, Any]) -> tuple[Any, Any]:
    v1 = inputs["v1"]
    p318 = v1._load_p318(inputs["v1_inputs"]["p318_payload"])
    prior = sys.modules.get("device_action_raw_capture_v1")
    sys.modules["device_action_raw_capture_v1"] = inputs["raw"]
    try:
        module = v1._pinned_base(inputs["v1_inputs"], p318)
    finally:
        if prior is None:
            sys.modules.pop("device_action_raw_capture_v1", None)
        else:
            sys.modules["device_action_raw_capture_v1"] = prior
    if module.d0.raw_capture is not inputs["raw"]:
        raise SuccessorError("D0 runtime did not retain pinned raw helper")
    return module, p318


def reproduce_v1_missing_bind(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Prove the consumed V1 source order without running a command."""

    module, _p318 = _pinned_base(inputs)
    transport = object.__new__(module.RealTransport)
    serial = "FIXTURE_S22"
    topology = "usb:1-1"
    transport.binding = {
        "target": {
            "adb_serial_sha256": hashlib.sha256(serial.encode()).hexdigest(),
            "usb_topology_sha256": hashlib.sha256(topology.encode()).hexdigest(),
        }
    }
    transport.selected = None
    transport.current_topology_sha256 = None
    transport.client = module.d0.AdbReadOnlyClient(HOST_ADB)
    transport._inventory = lambda: [
        (
            serial,
            "device",
            {"model:SM_S906N", "device:g0q", "transport_id:1"},
        )
    ]
    calls = {"bounded_command": 0}

    inventory_transport = object.__new__(module.RealTransport)
    inventory_transport.adb = Path("/fixture/nonexistent-adb")

    def fixture_inventory(*_args: Any, **_kwargs: Any) -> Any:
        calls["bounded_command"] += 1
        return types.SimpleNamespace(
            returncode=0,
            stderr=b"",
            stdout=(
                b"List of devices attached\n"
                b"FIXTURE_S22 device model:SM_S906N device:g0q transport_id:1\n"
            ),
        )

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        calls["bounded_command"] += 1
        raise AssertionError("fixture attempted device acquisition")

    original = module.d0.bounded_command
    try:
        module.d0.bounded_command = fixture_inventory
        inherited_rows = module.RealTransport._inventory(inventory_transport)
        if len(inherited_rows) != 1 or calls["bounded_command"] != 1:
            raise SuccessorError("V1 inherited inventory bypass fixture differs")
        module.d0.bounded_command = forbidden
        try:
            transport.select_exact()
        except module.d0.D0Error as exc:
            failure = str(exc)
        else:
            raise SuccessorError("V1 missing-bind fixture did not fail")
    finally:
        module.d0.bounded_command = original
    if failure != "ADB raw-first capture is not bound" or calls["bounded_command"] != 1:
        raise SuccessorError("V1 missing-bind cause fixture differs")
    p296_source = inputs["payloads"]["p296_primitive"].decode("utf-8")
    if "d0.bounded_command(" not in p296_source or "def _inventory(self)" not in p296_source:
        raise SuccessorError("V1 inherited inventory bypass source differs")
    return {
        "classification": "V1_RAW_CAPTURE_UNBOUND_BEFORE_TOPOLOGY",
        "error_type": "D0Error",
        "error_code": "RAW_CAPTURE_UNBOUND",
        "topology_path_bounded_command_calls": 0,
        "inherited_inventory_bounded_command_calls": 1,
        "inherited_inventory_raw_handles": 0,
        "device_contact": False,
        "retroactive_run_reclassification": False,
    }


def _inventory_rows(text: str) -> list[tuple[str, str, set[str]]]:
    rows: list[tuple[str, str, set[str]]] = []
    for line in text.splitlines():
        if not line or line.startswith("List of devices attached"):
            continue
        fields = line.split()
        if len(fields) < 2:
            raise ClassifiedFailure("inventory-parse", "INVENTORY_FORMAT")
        rows.append((fields[0], fields[1], set(fields[2:])))
    return rows


def _stable_inventory_metadata(metadata: set[str]) -> list[str]:
    transport = sorted(
        token for token in metadata if token.startswith("transport_id:")
    )
    if len(transport) != 1:
        raise ClassifiedFailure("inventory-parse", "INVENTORY_FORMAT")
    value = transport[0].removeprefix("transport_id:")
    if not value.isascii() or not value.isdigit():
        raise ClassifiedFailure("inventory-parse", "INVENTORY_FORMAT")
    return sorted(metadata - {transport[0]})


def _inventory_digest(rows: list[tuple[str, str, set[str]]]) -> str:
    value = [
        {
            "serial_sha256": hashlib.sha256(serial.encode("utf-8")).hexdigest(),
            "state": state,
            "stable_metadata": _stable_inventory_metadata(metadata),
        }
        for serial, state, metadata in sorted(rows, key=lambda row: row[0])
    ]
    return hashlib.sha256(canonical(value).rstrip(b"\n")).hexdigest()


def _make_transport(
    module: Any,
    raw: Any,
    binding: Mapping[str, Any],
    profile: Mapping[str, Any],
    raw_root: Path,
    *,
    client_factory: Any | None = None,
) -> Any:
    class RawFirstTransport:
        def __init__(self) -> None:
            self.binding = binding
            self.selected: str | None = None
            self.current_topology_sha256: str | None = None
            self.reboot_count = 0
            self.other_target_commands = 0
            self.current_site = "raw-capture-bind"
            self.client = (
                module.d0.AdbReadOnlyClient(ADB_SNAPSHOT)
                if client_factory is None
                else client_factory(module.d0, raw)
            )
            self.adb = self.client.adb
            try:
                self.client.bind_raw_capture_dir(raw_root)
            except BaseException as exc:
                raise ClassifiedFailure(
                    "raw-capture-bind", "RAW_CAPTURE_NAMESPACE"
                ) from exc
            try:
                capture_dir = raw_root / "raw-adb"
                metadata = capture_dir.lstat()
                if (
                    not stat.S_ISDIR(metadata.st_mode)
                    or stat.S_IMODE(metadata.st_mode) != 0o700
                    or metadata.st_uid != os.getuid()
                    or capture_dir.resolve(strict=True) != capture_dir.absolute()
                    or any(capture_dir.iterdir())
                ):
                    raise SuccessorError("raw capture directory is not fresh")
            except BaseException as exc:
                raise ClassifiedFailure(
                    "raw-capture-bind", "RAW_CAPTURE_NAMESPACE"
                ) from exc
            self.download = profile["target"]["download"]

        def _inventory(self, *, poll: bool = False) -> list[tuple[str, str, set[str]]]:
            self.current_site = "poll-inventory" if poll else "inventory-read"
            try:
                text = self.client._run(["devices", "-l"], "adb inventory", 10)
            except BaseException as exc:
                raise ClassifiedFailure(
                    "poll-inventory" if poll else "inventory-read",
                    "POLL_INVENTORY" if poll else "INVENTORY_READ",
                ) from exc
            return _inventory_rows(text)

        def select_exact(self) -> tuple[str, dict[str, Any]]:
            rows = self._inventory()
            matching_metadata = [
                row
                for row in rows
                if {"model:SM_S906N", "device:g0q"} <= row[2]
            ]
            matches = [row[0] for row in matching_metadata if row[1] == "device"]
            if len(matches) != 1:
                code = (
                    "INVENTORY_STATE"
                    if len(matching_metadata) == 1 and not matches
                    else "INVENTORY_CARDINALITY"
                )
                raise ClassifiedFailure("inventory-select", code)
            serial = matches[0]
            target = binding["target"]
            if (
                SERIAL_RE.fullmatch(serial) is None
                or hashlib.sha256(serial.encode()).hexdigest()
                != target["adb_serial_sha256"]
            ):
                raise ClassifiedFailure("serial-identity", "SERIAL_IDENTITY")
            self.current_site = "topology-read"
            try:
                topology = self.client.topology(serial)
            except BaseException as exc:
                raise ClassifiedFailure("topology-read", "TOPOLOGY_READ") from exc
            topology_sha = hashlib.sha256(topology.encode()).hexdigest()
            if DEVPATH_RE.fullmatch(topology) is None or (
                self.current_topology_sha256 is not None
                and topology_sha != self.current_topology_sha256
            ):
                raise ClassifiedFailure("topology-identity", "TOPOLOGY_IDENTITY")
            if self.selected is not None and self.selected != serial:
                raise ClassifiedFailure("serial-identity", "SERIAL_IDENTITY")
            self.selected = serial
            self.current_topology_sha256 = topology_sha
            models = sorted(
                token.split(":", 1)[1]
                for _serial, _state, metadata in rows
                for token in metadata
                if token.startswith("model:")
            )
            return serial, {
                "inventory_count": len(rows),
                "inventory_models": models,
                "inventory_sha256": _inventory_digest(rows),
                "selected_serial_sha256": hashlib.sha256(serial.encode()).hexdigest(),
                "selected_topology_sha256": topology_sha,
                "other_targets_commanded": False,
            }

        def snapshot(self, serial: str) -> dict[str, Any]:
            if serial != self.selected:
                raise ClassifiedFailure("serial-identity", "SERIAL_IDENTITY")
            self.current_site = "properties-read"
            try:
                properties = self.client.properties(serial)
            except BaseException as exc:
                raise ClassifiedFailure(
                    "properties-read", "HEALTH_PROPERTIES_READ"
                ) from exc
            self.current_site = "root-health-read"
            try:
                root_health = self.client.root_health(serial)
            except BaseException as exc:
                raise ClassifiedFailure(
                    "root-health-read", "HEALTH_ROOT_READ"
                ) from exc
            self.current_site = "topology-read"
            try:
                topology = self.client.topology(serial)
            except BaseException as exc:
                raise ClassifiedFailure("topology-read", "TOPOLOGY_READ") from exc
            if (
                self.current_topology_sha256 is None
                or hashlib.sha256(topology.encode()).hexdigest()
                != self.current_topology_sha256
            ):
                raise ClassifiedFailure("topology-identity", "TOPOLOGY_IDENTITY")
            self.current_site = "usb-snapshot"
            try:
                usb = module.d0.usb_snapshot(module.d0.DEFAULT_USB_ROOT, self.download)
            except BaseException as exc:
                raise ClassifiedFailure("usb-snapshot", "USB_SNAPSHOT") from exc
            if usb.get("download_endpoint_count") != 0:
                raise ClassifiedFailure("usb-snapshot", "USB_SNAPSHOT")
            self.current_site = "health-validation"
            return {
                "properties": properties,
                "root_health": root_health,
                "topology": topology,
                "no_odin": True,
            }

        def reboot_once(self, serial: str) -> None:
            if serial != self.selected or self.reboot_count:
                raise ClassifiedFailure("reboot-dispatch", "REBOOT_COMMAND")
            self.current_site = "reboot-dispatch"
            self.reboot_count += 1
            try:
                handle = self.client.capture_command(
                    ["-s", serial, "reboot"],
                    "adb normal reboot",
                    timeout=20,
                    maximum=MAX_TEXT,
                )
                reopened = raw.load_handle(handle.receipt_path)
                raw.require_success(reopened)
                if raw.read_stdout(reopened, maximum=MAX_TEXT) or raw.read_stderr(
                    reopened, maximum=MAX_TEXT
                ):
                    raise SuccessorError("reboot command emitted output")
            except BaseException as exc:
                if isinstance(exc, ClassifiedFailure):
                    raise
                raise ClassifiedFailure("reboot-dispatch", "REBOOT_COMMAND") from exc

        def poll(self, serial: str) -> dict[str, Any]:
            rows = self._inventory(poll=True)
            row = next((item for item in rows if item[0] == serial), None)
            if row is None or row[1] != "device":
                return {"connected": False}
            if serial != self.selected:
                self.other_target_commands += 1
                raise ClassifiedFailure("serial-identity", "SERIAL_IDENTITY")
            try:
                properties = self.client.properties(serial)
            except (module.d0.D0Error, OSError):
                # Preserve P2.96: an early post-reboot shell failure is
                # connected-but-not-ready. The failed immutable raw handle is
                # retained, and the bounded poll continues without replay.
                return {"connected": True, "ready": False}
            return {
                "connected": True,
                "ready": (
                    properties["boot_completed"] == "1"
                    and properties["bootanim"] == "stopped"
                ),
                "boot_id": properties["boot_id"],
            }

    return RawFirstTransport()


def _node_type(mode: int) -> str:
    if stat.S_ISREG(mode):
        return "regular"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "special"


def _raw_inventory(raw: Any) -> dict[str, Any]:
    try:
        root_stat = RAW_ROOT.lstat()
    except FileNotFoundError:
        base = {
            "schema": RAW_INVENTORY_SCHEMA,
            "root": _relative(RAW_ROOT),
            "directory": _relative(RAW_ADB_DIR),
            "root_present": False,
            "directory_present": False,
            "complete": False,
            "children": [],
            "handles": [],
            "invalid_receipts": [],
            "unclaimed_children": [],
        }
        return {**base, "aggregate_sha256": hashlib.sha256(canonical(base)).hexdigest()}
    if (
        not stat.S_ISDIR(root_stat.st_mode)
        or stat.S_IMODE(root_stat.st_mode) != 0o700
        or root_stat.st_uid != os.getuid()
        or RAW_ROOT.resolve(strict=True) != RAW_ROOT.absolute()
    ):
        raise SuccessorError("raw root identity differs")
    root_children = {item.name for item in RAW_ROOT.iterdir()}
    if not root_children:
        base = {
            "schema": RAW_INVENTORY_SCHEMA,
            "root": _relative(RAW_ROOT),
            "directory": _relative(RAW_ADB_DIR),
            "root_present": True,
            "directory_present": False,
            "complete": False,
            "children": [],
            "handles": [],
            "invalid_receipts": [],
            "unclaimed_children": [],
        }
        return {
            **base,
            "aggregate_sha256": hashlib.sha256(canonical(base)).hexdigest(),
        }
    if root_children != {"raw-adb"}:
        raise SuccessorError("raw root child set differs")
    directory_stat = RAW_ADB_DIR.lstat()
    if (
        not stat.S_ISDIR(directory_stat.st_mode)
        or stat.S_IMODE(directory_stat.st_mode) != 0o700
        or directory_stat.st_uid != os.getuid()
        or RAW_ADB_DIR.resolve(strict=True) != RAW_ADB_DIR.absolute()
    ):
        raise SuccessorError("raw ADB directory identity differs")
    children: list[dict[str, Any]] = []
    child_map: dict[str, dict[str, Any]] = {}
    for child in sorted(RAW_ADB_DIR.iterdir(), key=lambda item: item.name):
        metadata = child.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_nlink != 1
            or metadata.st_uid != os.getuid()
        ):
            raise SuccessorError("raw ADB child identity differs")
        payload = _stable(
            child,
            f"raw child {child.name}",
            maximum=MAX_TEXT,
            mode=0o400,
        )
        entry = {
            "name": child.name,
            "node_type": _node_type(metadata.st_mode),
            "mode": "0400",
            "nlink": 1,
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        children.append(entry)
        child_map[child.name] = entry
    handles: list[dict[str, Any]] = []
    claimed: set[str] = set()
    invalid_receipts: list[str] = []
    for receipt_name in sorted(name for name in child_map if name.endswith(".capture.json")):
        try:
            handle = raw.load_handle(RAW_ADB_DIR / receipt_name)
        except BaseException:
            invalid_receipts.append(receipt_name)
            continue
        names = {handle.receipt_path.name, handle.stdout_path.name, handle.stderr_path.name}
        if len(names) != 3 or not names <= set(child_map) or claimed & names:
            invalid_receipts.append(receipt_name)
            continue
        claimed.update(names)
        handles.append(
            {
                "name": handle.name,
                "receipt": child_map[handle.receipt_path.name],
                "stdout": child_map[handle.stdout_path.name],
                "stderr": child_map[handle.stderr_path.name],
                "returncode": handle.returncode,
                "timed_out": handle.timed_out,
                "output_exceeded": handle.output_exceeded,
                "producer_error_type": handle.producer_error_type,
            }
        )
    unclaimed = sorted(set(child_map) - claimed)
    for sequence, handle in enumerate(handles):
        prefix = f"{sequence:04d}-"
        if (
            not handle["name"].startswith(prefix)
            or handle["name"].removeprefix(prefix) not in RAW_HANDLE_LABELS
        ):
            invalid_receipts.append(handle["receipt"]["name"])
    complete = (
        bool(handles)
        and not invalid_receipts
        and not unclaimed
        and len(claimed) == len(children)
    )
    base = {
        "schema": RAW_INVENTORY_SCHEMA,
        "root": _relative(RAW_ROOT),
        "directory": _relative(RAW_ADB_DIR),
        "root_present": True,
        "directory_present": True,
        "complete": complete,
        "children": children,
        "handles": handles,
        "invalid_receipts": invalid_receipts,
        "unclaimed_children": unclaimed,
    }
    return {**base, "aggregate_sha256": hashlib.sha256(canonical(base)).hexdigest()}


def _arm_value(inputs: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": ARM_SCHEMA,
        "execution_manifest": inputs["manifest_receipt"],
        "approval_sha256": inputs["approval_sha256"],
        "run_directory": inputs["manifest"]["run"]["directory"],
        "raw_root": inputs["manifest"]["run"]["raw_root"],
        "action": inputs["manifest"]["action"],
        "ordinal": "d1-fresh-baseline-3",
        "consumed": True,
        "device_contact_before_arm": False,
    }


def reproduce_canonical_arm_writer_validator(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Run the production V1 arm writer into V3's production validator."""

    value = _arm_value(inputs)
    with tempfile.TemporaryDirectory(prefix="p319-d1-v3-arm-") as temporary:
        arm = Path(temporary) / "run-parent" / "p319-fresh-baseline-3.arm.json"
        original = inputs["v1"]._durable_create
        try:
            inputs["v1"]._durable_create = lambda _path, item: original(arm, item)
            _durable_arm_canonical(inputs)
        finally:
            inputs["v1"]._durable_create = original
        payload = _stable(arm, "V3 canonical arm seam", maximum=64 * 1024, mode=0o400)
        parsed = _strict(payload, "V3 canonical arm seam")
        if not _arm_complete(parsed, inputs):
            raise SuccessorError("V3 canonical arm seam did not reach validator")
        return {
            "writer": "pinned_v1._durable_create",
            "validator": "_arm_complete",
            "canonical": payload == canonical(value),
            "pre_acquisition_boundary": True,
            "device_contact": False,
        }


def _direct_receipt(path: Path, label: str, maximum: int = 512 * 1024) -> dict[str, Any]:
    payload = _stable(path, label, maximum=maximum, mode=0o400)
    return _receipt(path, payload, mode="0400")


def _adb_snapshot_state() -> dict[str, Any]:
    try:
        payload = _stable(
            ADB_SNAPSHOT,
            "V3 ADB snapshot",
            maximum=EXPECTED["host_adb"][0],
            expected=EXPECTED["host_adb"],
            mode=0o500,
        )
    except FileNotFoundError:
        return {"present": False, "receipt": None}
    return {"present": True, "receipt": _receipt(ADB_SNAPSHOT, payload, mode="0500")}


def _failure(error: BaseException) -> tuple[str, str]:
    if isinstance(error, ClassifiedFailure) and (
        error.failure_site,
        error.failure_code,
    ) in FAILURES:
        return error.failure_site, error.failure_code
    return "internal", "UNCLASSIFIED"


def _health_complete(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "android_boot_completed",
        "boot_animation_stopped",
        "boot_id_sha256",
        "boot_sha256",
        "kernel_release",
        "odin_endpoint_absent",
        "root_verified",
        "supporting_partition_sha256",
        "verified_boot_state",
    }:
        return False
    support = value["supporting_partition_sha256"]
    return (
        all(
            value[key] is True
            for key in (
                "android_boot_completed",
                "boot_animation_stopped",
                "odin_endpoint_absent",
                "root_verified",
            )
        )
        and all(
            isinstance(value[key], str) and HEX64_RE.fullmatch(value[key])
            for key in ("boot_id_sha256", "boot_sha256")
        )
        and isinstance(value["kernel_release"], str)
        and bool(value["kernel_release"])
        and isinstance(value["verified_boot_state"], str)
        and bool(value["verified_boot_state"])
        and isinstance(support, dict)
        and set(support) == {"dtbo", "recovery", "vendor_boot"}
        and all(
            isinstance(item, str) and HEX64_RE.fullmatch(item)
            for item in support.values()
        )
    )


def _selection_complete(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value)
        == {
            "inventory_count",
            "inventory_models",
            "inventory_sha256",
            "selected_serial_sha256",
            "selected_topology_sha256",
            "other_targets_commanded",
        }
        and type(value["inventory_count"]) is int
        and value["inventory_count"] >= 1
        and isinstance(value["inventory_models"], list)
        and all(isinstance(item, str) for item in value["inventory_models"])
        and all(
            isinstance(value[key], str) and HEX64_RE.fullmatch(value[key])
            for key in (
                "inventory_sha256",
                "selected_serial_sha256",
                "selected_topology_sha256",
            )
        )
        and value["other_targets_commanded"] is False
    )


def _start_complete(value: Mapping[str, Any], inputs: Mapping[str, Any]) -> bool:
    return (
        set(value)
        == {
            "schema",
            "execution_manifest",
            "approval_sha256",
            "before",
            "selection",
            "reboot_count",
            "reboot_requested",
            "device_writes",
            "candidate_transfer",
            "partition_transfer",
            "odin_invoked",
            "download_transition_requested",
            "f1_authorized",
        }
        and value["schema"] == START_SCHEMA
        and value["execution_manifest"] == inputs["manifest_receipt"]
        and value["approval_sha256"] == inputs["approval_sha256"]
        and _health_complete(value["before"])
        and _selection_complete(value["selection"])
        and value["reboot_count"] == 1
        and value["reboot_requested"] is True
        and all(
            value[key] is False
            for key in (
                "device_writes",
                "candidate_transfer",
                "partition_transfer",
                "odin_invoked",
                "download_transition_requested",
                "f1_authorized",
            )
        )
    )


def _result_complete(value: Mapping[str, Any], inputs: Mapping[str, Any]) -> bool:
    return (
        set(value)
        == {
            "schema",
            "verdict",
            "execution_manifest",
            "approval_sha256",
            "ordinal",
            "run_directory",
            "arm",
            "start",
            "adb_snapshot",
            "raw_evidence",
            "reboot_count",
            "candidate_transfer",
            "partition_payload",
            "odin",
            "download_transition",
            "f1_authorized",
            "replay_authorized",
            "before",
            "after",
            "selection",
            "other_targets_commanded",
            "device_writes",
            "live_authorized",
        }
        and value.get("schema") == RESULT_SCHEMA
        and value.get("verdict") == RESULT_VERDICT
        and value.get("execution_manifest") == inputs["manifest_receipt"]
        and value.get("approval_sha256") == inputs["approval_sha256"]
        and value.get("ordinal") == "d1-fresh-baseline-3"
        and value.get("run_directory") == _relative(RUN_DIR)
        and value.get("arm")
        == _direct_receipt(RUN_ARM, "V3 result arm", maximum=64 * 1024)
        and value.get("start")
        == _direct_receipt(RUN_DIR / "start.json", "V3 result start")
        and value.get("adb_snapshot") == _adb_snapshot_state()
        and value["adb_snapshot"]["present"] is True
        and value.get("reboot_count") == 1
        and value.get("raw_evidence", {}).get("complete") is True
        and _health_complete(value.get("before"))
        and _health_complete(value.get("after"))
        and value["before"]["boot_id_sha256"]
        != value["after"]["boot_id_sha256"]
        and _selection_complete(value.get("selection"))
        and all(
            value.get(key) is False
            for key in (
                "candidate_transfer",
                "partition_payload",
                "odin",
                "download_transition",
                "f1_authorized",
                "replay_authorized",
                "other_targets_commanded",
                "device_writes",
                "live_authorized",
            )
        )
    )


def _arm_complete(value: Mapping[str, Any], inputs: Mapping[str, Any]) -> bool:
    return _typed_equal(value, _arm_value(inputs))


def _journal_state(
    path: Path,
    label: str,
    inputs: Mapping[str, Any],
    complete: Any,
) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return {
            "present": False,
            "node_valid": False,
            "bytes_complete": False,
            "receipt": None,
        }
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o400
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or path.resolve(strict=True) != path.absolute()
    ):
        raise SuccessorError(f"{label} node identity differs")
    payload = _stable(path, label, maximum=512 * 1024, mode=0o400)
    receipt = _receipt(path, payload, mode="0400")
    try:
        value = _strict(payload, label)
        bytes_complete = bool(complete(value, inputs))
    except SuccessorError:
        bytes_complete = False
    return {
        "present": True,
        "node_valid": True,
        "bytes_complete": bytes_complete,
        "receipt": receipt,
    }


def _cut_state(inputs: Mapping[str, Any]) -> dict[str, Any]:
    arm = _journal_state(RUN_ARM, "V3 arm", inputs, _arm_complete)
    start = _journal_state(
        RUN_DIR / "start.json", "V3 start", inputs, _start_complete
    )
    result = _journal_state(
        RUN_DIR / "result.json", "V3 result", inputs, _result_complete
    )
    return {
        **{f"arm_{key}": item for key, item in arm.items()},
        **{f"start_{key}": item for key, item in start.items()},
        **{f"result_{key}": item for key, item in result.items()},
    }


def _stop_value(inputs: Mapping[str, Any], error: BaseException) -> dict[str, Any]:
    site, code = _failure(error)
    cut = _cut_state(inputs)
    raw_evidence = _raw_inventory(inputs["raw"])
    if cut["result_present"]:
        stage = "after-result-publication"
    elif cut["start_bytes_complete"]:
        stage = "after-start-before-result"
    elif cut["start_present"]:
        stage = "during-start-publication"
    elif cut["arm_bytes_complete"]:
        stage = "after-arm-before-start"
    else:
        stage = "during-arm-publication"
    return {
        "schema": STOP_SCHEMA,
        "verdict": STOP_VERDICT,
        "execution_manifest": inputs["manifest_receipt"],
        "approval_sha256": inputs["approval_sha256"],
        "ordinal": "d1-fresh-baseline-3",
        "run_directory": _relative(RUN_DIR),
        "stage": stage,
        "failure_site": site,
        "failure_code": code,
        "adb_snapshot": _adb_snapshot_state(),
        "raw_evidence": raw_evidence,
        **cut,
        "reboot_dispatch_possible": cut["start_bytes_complete"],
        "candidate_transfer": False,
        "partition_payload": False,
        "odin": False,
        "download_transition": False,
        "f1_authorized": False,
        "result_reusable": False,
        "replay_authorized": False,
        "private_raw_evidence_preserved": raw_evidence["root_present"],
        "tracked_private_identifiers": False,
    }


def _validate_parent_namespace(value: Mapping[str, Any], *, include_stop: bool) -> None:
    parent = RUN_PARENT.lstat()
    if (
        not stat.S_ISDIR(parent.st_mode)
        or stat.S_IMODE(parent.st_mode) != 0o700
        or parent.st_uid != os.getuid()
        or RUN_PARENT.resolve(strict=True) != RUN_PARENT.absolute()
    ):
        raise SuccessorError("V3 parent namespace differs")
    expected_parent = {RUN_ARM.name, RUN_DIR.name}
    if value["raw_evidence"]["root_present"]:
        expected_parent.add(RAW_ROOT.name)
    if {path.name for path in RUN_PARENT.iterdir()} != expected_parent:
        raise SuccessorError("V3 parent child set differs")
    run = RUN_DIR.lstat()
    if (
        not stat.S_ISDIR(run.st_mode)
        or stat.S_IMODE(run.st_mode) != 0o700
        or run.st_uid != os.getuid()
        or RUN_DIR.resolve(strict=True) != RUN_DIR.absolute()
    ):
        raise SuccessorError("V3 run namespace differs")
    expected_run = set()
    if value["start_present"]:
        expected_run.add("start.json")
    if value["result_present"]:
        expected_run.add("result.json")
    if include_stop:
        expected_run.add("stop.json")
    if {path.name for path in RUN_DIR.iterdir()} != expected_run:
        raise SuccessorError("V3 run child set differs")


def validate_stop(
    value: Any,
    *,
    inputs: Mapping[str, Any] | None = None,
    path: Path | None = None,
    publishing: bool = False,
) -> dict[str, Any]:
    bound = _validated_execution_inputs(_validated_static_inputs()) if inputs is None else inputs
    required = {
        "schema",
        "verdict",
        "execution_manifest",
        "approval_sha256",
        "ordinal",
        "run_directory",
        "stage",
        "failure_site",
        "failure_code",
        "adb_snapshot",
        "raw_evidence",
        "arm_present",
        "arm_node_valid",
        "arm_bytes_complete",
        "arm_receipt",
        "start_present",
        "start_node_valid",
        "start_bytes_complete",
        "start_receipt",
        "result_present",
        "result_node_valid",
        "result_bytes_complete",
        "result_receipt",
        "reboot_dispatch_possible",
        "candidate_transfer",
        "partition_payload",
        "odin",
        "download_transition",
        "f1_authorized",
        "result_reusable",
        "replay_authorized",
        "private_raw_evidence_preserved",
        "tracked_private_identifiers",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise SuccessorError("V3 stop key set differs")
    if (
        value["schema"] != STOP_SCHEMA
        or value["verdict"] != STOP_VERDICT
        or value["execution_manifest"] != bound["manifest_receipt"]
        or value["approval_sha256"] != bound["approval_sha256"]
        or value["ordinal"] != "d1-fresh-baseline-3"
        or value["run_directory"] != _relative(RUN_DIR)
        or (value["failure_site"], value["failure_code"]) not in FAILURES
    ):
        raise SuccessorError("V3 stop binding differs")
    for key in (
        "arm_present",
        "arm_node_valid",
        "arm_bytes_complete",
        "start_present",
        "start_node_valid",
        "start_bytes_complete",
        "result_present",
        "result_node_valid",
        "result_bytes_complete",
        "reboot_dispatch_possible",
        "candidate_transfer",
        "partition_payload",
        "odin",
        "download_transition",
        "f1_authorized",
        "result_reusable",
        "replay_authorized",
        "private_raw_evidence_preserved",
        "tracked_private_identifiers",
    ):
        if type(value[key]) is not bool:
            raise SuccessorError("V3 stop boolean is untyped")
    if (
        value["arm_present"] is not True
        or value["arm_node_valid"] is not True
        or value["reboot_dispatch_possible"] is not value["start_bytes_complete"]
        or value["private_raw_evidence_preserved"]
        is not value["raw_evidence"]["root_present"]
        or any(
            value[key]
            for key in (
                "candidate_transfer",
                "partition_payload",
                "odin",
                "download_transition",
                "f1_authorized",
                "result_reusable",
                "replay_authorized",
                "tracked_private_identifiers",
            )
        )
    ):
        raise SuccessorError("V3 stop safety state differs")
    expected_stage = (
        "after-result-publication"
        if value["result_present"]
        else "after-start-before-result"
        if value["start_bytes_complete"]
        else "during-start-publication"
        if value["start_present"]
        else "after-arm-before-start"
        if value["arm_bytes_complete"]
        else "during-arm-publication"
    )
    if value["stage"] != expected_stage:
        raise SuccessorError("V3 stop stage differs")
    if value["adb_snapshot"] != _adb_snapshot_state():
        raise SuccessorError("V3 stop ADB snapshot differs")
    if value["raw_evidence"] != _raw_inventory(bound["raw"]):
        raise SuccessorError("V3 stop raw evidence differs")
    cut = _cut_state(bound)
    if {key: value[key] for key in cut} != cut:
        raise SuccessorError("V3 stop cut state differs")
    if not publishing:
        stop_path = RUN_STOP if path is None else path
        if stop_path != RUN_STOP:
            raise SuccessorError("V3 stop path differs")
        payload = _stable(stop_path, "V3 fixed stop", maximum=512 * 1024, mode=0o400)
        if _strict(payload, "V3 fixed stop") != value:
            raise SuccessorError("V3 fixed stop bytes differ")
    _validate_parent_namespace(value, include_stop=not publishing)
    return dict(value)


def validate_stop_file(path: Path | None = None) -> dict[str, Any]:
    selected = RUN_STOP if path is None else path
    payload = _stable(selected, "V3 stop", maximum=512 * 1024, mode=0o400)
    value = _strict(payload, "V3 stop")
    result = validate_stop(value, path=selected)
    if _stable(selected, "final V3 stop", maximum=512 * 1024, mode=0o400) != payload:
        raise SuccessorError("V3 stop changed during validation")
    return result


def _publish_stop(inputs: Mapping[str, Any], error: BaseException) -> None:
    value = _stop_value(inputs, error)
    if RUN_DIR.exists() or RUN_DIR.is_symlink():
        metadata = RUN_DIR.lstat()
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or metadata.st_uid != os.getuid()
        ):
            raise SuccessorError("V3 stop run directory differs")
    else:
        RUN_DIR.mkdir(mode=0o700)
    _validate_parent_namespace(value, include_stop=False)
    inputs["v1"]._durable_create(RUN_STOP, value)
    validate_stop(value, inputs=inputs, path=RUN_STOP)


def _result_binding(inputs: Mapping[str, Any], raw_evidence: Mapping[str, Any]) -> dict[str, Any]:
    adb_snapshot = _adb_snapshot_state()
    if adb_snapshot["present"] is not True:
        raise ClassifiedFailure("namespace-publication", "NAMESPACE_PUBLICATION")
    return {
        "schema": RESULT_SCHEMA,
        "verdict": RESULT_VERDICT,
        "execution_manifest": inputs["manifest_receipt"],
        "approval_sha256": inputs["approval_sha256"],
        "ordinal": "d1-fresh-baseline-3",
        "run_directory": _relative(RUN_DIR),
        "arm": _direct_receipt(RUN_ARM, "V3 result arm", maximum=64 * 1024),
        "start": _direct_receipt(RUN_DIR / "start.json", "V3 result start"),
        "adb_snapshot": adb_snapshot,
        "raw_evidence": dict(raw_evidence),
        "reboot_count": 1,
        "candidate_transfer": False,
        "partition_payload": False,
        "odin": False,
        "download_transition": False,
        "f1_authorized": False,
        "replay_authorized": False,
    }


def _execute_primitive(
    inputs: Mapping[str, Any], *, client_factory: Any | None = None, clock: Any | None = None
) -> dict[str, Any]:
    module, _p318 = _pinned_base(inputs)
    v1 = inputs["v1"]
    v1_inputs = inputs["v1_inputs"]
    module.SCHEMA = "s22plus_fyg8_p319_d1_fresh_baseline_v3"
    module.VERDICT = RESULT_VERDICT
    module.APPROVAL = inputs["authority"]
    module.RUN_ROOT = RUN_PARENT
    module.INITIATION_BOUND_SEC = 60.0
    module.RETURN_BOUND_SEC = 240.0
    module.prior_binding = lambda: json.loads(json.dumps(v1_inputs["prior_binding"]))
    original_validate = module.validate_snapshot
    original_create = module.d0.durable_create
    original_load_json = module.load_json
    start_holder: dict[str, Any] = {}

    def validate(snapshot: dict[str, Any], binding: dict[str, Any], *, initial: bool) -> dict[str, Any]:
        try:
            return v1._health_from_snapshot(
                module, original_validate, snapshot, binding, initial=initial
            )
        except BaseException as exc:
            raise ClassifiedFailure("health-validation", "HEALTH_INVALID") from exc

    def create(path: Path, value: dict[str, Any]) -> None:
        if path == RUN_DIR / "start.json":
            transformed = {
                "schema": START_SCHEMA,
                "execution_manifest": inputs["manifest_receipt"],
                "approval_sha256": inputs["approval_sha256"],
                "before": value.get("before"),
                "selection": value.get("selection"),
                "reboot_count": 1,
                "reboot_requested": True,
                "device_writes": False,
                "candidate_transfer": False,
                "partition_transfer": False,
                "odin_invoked": False,
                "download_transition_requested": False,
                "f1_authorized": False,
            }
            try:
                v1._durable_create(path, transformed)
            except BaseException as exc:
                raise ClassifiedFailure("start-publication", "START_PUBLICATION") from exc
            start_holder.update(transformed)
            return
        if path == RUN_DIR / "result.json":
            try:
                raw_evidence = _raw_inventory(inputs["raw"])
            except BaseException as exc:
                raise ClassifiedFailure(
                    "namespace-publication", "NAMESPACE_PUBLICATION"
                ) from exc
            if raw_evidence["complete"] is not True:
                raise ClassifiedFailure("namespace-publication", "NAMESPACE_PUBLICATION")
            result = {
                **_result_binding(inputs, raw_evidence),
                "before": value.get("before"),
                "after": value.get("after"),
                "selection": value.get("selection"),
                "other_targets_commanded": False,
                "device_writes": False,
                "live_authorized": False,
            }
            if (
                start_holder.get("before") != result["before"]
                or start_holder.get("selection") != result["selection"]
            ):
                raise ClassifiedFailure("returned-health", "RETURN_HEALTH")
            v1._durable_create(path, result)
            return
        raise ClassifiedFailure("namespace-publication", "NAMESPACE_PUBLICATION")

    module.validate_snapshot = validate
    module.d0.durable_create = create
    module.load_json = v1._pinned_profile_loader(module, v1_inputs["profile"])
    try:
        transport = _make_transport(
            module,
            inputs["raw"],
            v1_inputs["prior_binding"],
            v1_inputs["profile"],
            RAW_ROOT,
            client_factory=client_factory,
        )
        try:
            result = module.perform_rotation(
                transport,
                v1_inputs["prior_binding"],
                module.RealClock() if clock is None else clock,
                RUN_DIR,
            )
        except module.RotationError as exc:
            if transport.reboot_count == 1 and (RUN_DIR / "start.json").is_file():
                raise ClassifiedFailure(
                    "returned-health", "RETURN_HEALTH"
                ) from exc
            raise
        if transport.reboot_count != 1 or transport.other_target_commands != 0:
            raise ClassifiedFailure("returned-health", "RETURN_HEALTH")
        return result
    finally:
        module.validate_snapshot = original_validate
        module.d0.durable_create = original_create
        module.load_json = original_load_json


def _post_validate(inputs: Mapping[str, Any]) -> dict[str, Any]:
    binding_payload = _stable(
        BINDING_MANIFEST, "post-run V3 binding", maximum=256 * 1024
    )
    if binding_payload != inputs["manifest_payload"]:
        raise SuccessorError("post-run V3 binding differs")
    for key, path in (
        ("successor_source", SCRIPT),
        ("v1_source", V1_SOURCE),
        ("v1_binding", V1_BINDING),
        ("d0_runtime", D0_RUNTIME),
        ("raw_capture", RAW_CAPTURE),
        ("p318_wrapper", P318_WRAPPER),
        ("p296_primitive", P296_PRIMITIVE),
        ("profile", PROFILE),
        ("host_adb", HOST_ADB),
        ("v1_arm", V1_ARM),
        ("v1_stop", V1_STOP),
    ):
        payload = inputs["payloads"][key]
        if _stable(
            path,
            f"post-run {key}",
            maximum=max(len(payload), 1),
            expected=(len(payload), hashlib.sha256(payload).hexdigest()),
            mode=0o400 if key in {"v1_arm", "v1_stop", "v2_arm", "v2_stop"} else None,
            owner=None if key == "host_adb" else os.getuid(),
        ) != payload:
            raise SuccessorError(f"post-run {key} differs")
    result_payload = _stable(
        RUN_DIR / "result.json", "V3 result", maximum=512 * 1024, mode=0o400
    )
    result = _strict(result_payload, "V3 result")
    if not _result_complete(result, inputs):
        raise SuccessorError("V3 result validation differs")
    if result["raw_evidence"] != _raw_inventory(inputs["raw"]):
        raise SuccessorError("V3 result raw evidence changed")
    _validate_parent_namespace(
        {
            "raw_evidence": result["raw_evidence"],
            "start_present": True,
            "result_present": True,
        },
        include_stop=False,
    )
    return result


def _validate_post_arm_pre_acquisition(inputs: Mapping[str, Any]) -> None:
    parent = RUN_PARENT.lstat()
    if (
        not stat.S_ISDIR(parent.st_mode)
        or stat.S_IMODE(parent.st_mode) != 0o700
        or parent.st_uid != os.getuid()
        or RUN_PARENT.resolve(strict=True) != RUN_PARENT.absolute()
        or {child.name for child in RUN_PARENT.iterdir()} != {RUN_ARM.name}
    ):
        raise ClassifiedFailure("namespace-publication", "NAMESPACE_PUBLICATION")
    arm = _journal_state(RUN_ARM, "post-arm V3 arm", inputs, _arm_complete)
    if arm != {
        "present": True,
        "node_valid": True,
        "bytes_complete": True,
        "receipt": arm["receipt"],
    }:
        raise ClassifiedFailure("namespace-publication", "NAMESPACE_PUBLICATION")
    if RAW_ROOT.exists() or RAW_ROOT.is_symlink():
        raise ClassifiedFailure("namespace-publication", "NAMESPACE_PUBLICATION")


def _preflight_new_run_namespace() -> None:
    for path in (RUN_ARM, RUN_DIR, RAW_ROOT, ADB_SNAPSHOT):
        try:
            path.lstat()
        except FileNotFoundError:
            continue
        raise SuccessorError(
            f"V3 fixed namespace already exists: {path.name}; replay is forbidden"
        )
    try:
        parent = RUN_PARENT.lstat()
    except FileNotFoundError:
        return
    if (
        not stat.S_ISDIR(parent.st_mode)
        or stat.S_IMODE(parent.st_mode) != 0o700
        or parent.st_uid != os.getuid()
        or RUN_PARENT.resolve(strict=True) != RUN_PARENT.absolute()
        or any(RUN_PARENT.iterdir())
    ):
        raise SuccessorError(
            "V3 run parent is not a fresh direct namespace; replay is forbidden"
        )


def _durable_arm_canonical(inputs: Mapping[str, Any]) -> None:
    """Use the already-qualified V1 canonical writer for the V3 arm."""

    try:
        inputs["v1"]._durable_create(RUN_ARM, _arm_value(inputs))
    except inputs["v1"].D1FreshBaselineError as exc:
        if str(exc) == f"D1 journal already exists: {RUN_ARM.name}":
            raise CanonicalArmAlreadyExists("V3 approval arm already exists") from exc
        raise


def _duplicate_arm_error(error: BaseException, p318: Any) -> bool:
    return (
        isinstance(error, CanonicalArmAlreadyExists)
        or (
            isinstance(error, p318.AdapterError)
            and str(error) == "D1 approval arm already exists"
        )
    )


def run_live(approval: str) -> dict[str, Any]:
    static = _validated_static_inputs()
    if static["manifest"]["independent_review"] != {
        "status": "pass-go",
        "verdict": REVIEW_VERDICT,
    }:
        raise SuccessorError("independent V3 review is absent")
    if approval != static["authority"]:
        raise SuccessorError("exact V3 approval is absent")
    inputs = _validated_execution_inputs(static)
    _preflight_new_run_namespace()
    p318 = inputs["v1"]._load_p318(inputs["v1_inputs"]["p318_payload"])
    arm_creation_attempted = False
    arm_completed = False
    try:
        arm_creation_attempted = True
        _durable_arm_canonical(inputs)
        arm_completed = True
        _validate_post_arm_pre_acquisition(inputs)
        p318._prepare_executable_snapshot(
            inputs["payloads"]["host_adb"], ADB_SNAPSHOT
        )
        inputs["raw"].prepare_capture_dir(RUN_PARENT, RAW_ROOT.name)
        _execute_primitive(inputs)
        return _post_validate(inputs)
    except BaseException as exc:
        if not arm_completed and _duplicate_arm_error(exc, p318):
            raise SuccessorError(
                "V3 approval arm already exists; replay is forbidden"
            ) from exc
        try:
            arm_present = RUN_ARM.lstat() is not None
        except FileNotFoundError:
            arm_present = False
        if not arm_completed and not (arm_creation_attempted and arm_present):
            raise SuccessorError("V3 stopped before durable arm") from exc
        try:
            _publish_stop(inputs, exc)
        except BaseException as stop_exc:
            raise SuccessorError(
                f"V3 stopped after arm; stop publication failed: {type(stop_exc).__name__}"
            ) from exc
        raise SuccessorError("V3 stopped after arm; consumed without replay") from exc


def _source_contract() -> dict[str, Any]:
    text = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(SCRIPT))
    direct_bounded = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "bounded_command"
    ]
    if direct_bounded:
        raise SuccessorError("V3 source retains direct bounded_command bypass")
    required = (
        "bind_raw_capture_dir(raw_root)",
        "self.client._run([\"devices\", \"-l\"]",
        "raw.load_handle(handle.receipt_path)",
        "raw.require_success(reopened)",
        "_raw_inventory(inputs[\"raw\"])",
        "_durable_arm_canonical(inputs)",
        "inputs[\"v1\"]._durable_create(RUN_ARM, _arm_value(inputs))",
        "_validate_consumed_v2(static[\"payloads\"])",
    )
    if any(token not in text for token in required):
        raise SuccessorError("V3 raw-first source seam differs")
    bind_before_inventory = text.index(
        "self.client.bind_raw_capture_dir(raw_root)"
    ) < text.index("        def _inventory(self")
    if not bind_before_inventory:
        raise SuccessorError("V3 raw capture is not bound before inventory")
    return {
        "direct_bounded_command_calls": 0,
        "bind_before_inventory": bind_before_inventory,
        "raw_handle_reopen_present": True,
    }


def self_test() -> dict[str, Any]:
    static = _validated_static_inputs()
    inputs = _validated_execution_inputs(static)
    cause = reproduce_v1_missing_bind(inputs)
    contract = _source_contract()
    arm_seam = reproduce_canonical_arm_writer_validator(inputs)
    return {
        "schema": "s22plus_fyg8_p319_d1_fresh_baseline_v3_fixture_h0",
        "verdict": "PASS_P319_D1_FRESH_BASELINE_V3_CANONICAL_ARM_FIXTURE_H0",
        "review_status": static["manifest"]["independent_review"]["status"],
        "v1_cause": cause,
        "successor_contract": contract,
        "canonical_arm_seam": arm_seam,
        "consumed_v2_bound": True,
        "device_contact": False,
        "approval_created": False,
        "live_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        if arguments in ([], ["--self-test"]):
            value = self_test()
        elif len(arguments) == 3 and arguments[:2] == ["--live", "--approval"]:
            value = run_live(arguments[2])
        else:
            raise SuccessorError(
                "accepted argv is empty/--self-test or exact --live --approval TOKEN"
            )
    except SuccessorError as exc:
        print(f"P3.19 D1 V3 blocked: {exc}", file=sys.stderr)
        return 2
    except (OSError, KeyError, TypeError) as exc:
        print(
            "P3.19 D1 V3 blocked: host input validation failed ("
            + type(exc).__name__
            + ")",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
