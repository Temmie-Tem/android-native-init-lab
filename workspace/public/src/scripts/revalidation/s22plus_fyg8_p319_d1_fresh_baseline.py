#!/usr/bin/env python3
"""Bounded P3.19 D1 fresh-baseline producer.

Default execution is a host-only rehearsal. The live branch accepts only the
approval derived from the exact reviewed execution-binding manifest. While
that manifest remains review-pending it stops before publishing the one-shot
arm, constructing a device transport, or issuing a command.

The reviewed P2.96 one-reboot state machine remains the execution owner. This
adapter byte-pins and loads it through the reviewed P3.18 wrapper; it does not
copy or widen that state machine. There is no payload, Odin, Download, F1,
retry, or caller-selected path.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve(strict=True)
SCRIPT_DIR = SCRIPT.parent
BINDING_MANIFEST = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d1_fresh_baseline_v1.json"
)
REDUCER = SCRIPT_DIR / "s22plus_fyg8_p319_fresh_baseline_capability.py"
INTENT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "candidate-qualification-v1-20260821-10/intent.json"
)
QUALIFICATION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "candidate-qualification-v1-20260821-10/qualification.json"
)
P318_WRAPPER = SCRIPT_DIR / "s22plus_fyg8_p318_baseline_rotation_d1.py"
P318_WRAPPER_SIZE = 30_648
P318_WRAPPER_SHA256 = "2b798b4ab73ee0ac9cc5c40c007e470f54083e460171852e844276413a95a706"
P296_PRIMITIVE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p296/d1-baseline-rotation/"
    "s22plus_fyg8_p296_baseline_rotation_d1.py"
)
P296_PRIMITIVE_SIZE = 18_578
P296_PRIMITIVE_SHA256 = "bfec4bc9c947e098b6a18134a805524aa8fe8103edd5ddc4bc3b398895cad8ea"
D0_RUNTIME = SCRIPT_DIR / "device_action_d0_v2.py"
D0_RUNTIME_SIZE = 44_582
D0_RUNTIME_SHA256 = "e71894396ca0c9ba0657a1c83d45883b99f53887c1fb87076ea0a38bbee5c37a"
REFERENCE_D0 = ROOT / (
    "workspace/private/runs/s22plus-fyg8-max77705-sysfs-d0/"
    "d0-20260823T160942Z-1787501382211543634/result.json"
)
REFERENCE_D0_SIZE = 16_825
REFERENCE_D0_SHA256 = "6bac2ea6a77ec3bc19c20e61df7c62efa6a471728e0421e7532f0e3731ed3e28"
PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
ADB = Path("/usr/lib/android-sdk/platform-tools/adb")
ADB_SIZE = 716_968
ADB_SHA256 = "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
ADB_SNAPSHOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/d1-fresh-baseline-v1/adb-"
    + ADB_SHA256
)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-d1-p319-fresh-baseline/"
    "p319-fresh-baseline-1"
)
RUN_ARM = Path(str(RUN_DIR) + ".arm.json")
RUN_STOP = RUN_DIR / "stop.json"
AUTHORITY_PREFIX = "DEVICE-ACTION-D1-P319-FRESH-BASELINE-V1-APPROVE:"
BINDING_SCHEMA = "s22plus_fyg8_p319_d1_fresh_baseline_execution_binding_v1"
BINDING_ID = "s22plus-fyg8-p319-d1-fresh-baseline-v1"
RESULT_SCHEMA = "s22plus_fyg8_p319_d1_fresh_baseline_v1_result"
RESULT_VERSION = "device-action-d1-p319-v1"
RESULT_VERDICT = "PASS_P319_D1_EXACT_NORMAL_REBOOT_RETURN_HEALTH"
STOP_SCHEMA = "s22plus_fyg8_p319_d1_fresh_baseline_v1_stop"
STOP_VERDICT = "STOP_P319_D1_FRESH_BASELINE_CONSUMED_NO_REPLAY"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


class D1FreshBaselineError(RuntimeError):
    """The bounded P3.19 D1 action cannot proceed."""


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False,
        ).encode("ascii") + b"\n"
    except (TypeError, ValueError) as exc:
        raise D1FreshBaselineError("value is not canonical JSON") from exc


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


def _identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _stable_read(
    path: Path, label: str, *, expected_size: int | None = None,
    expected_sha256: str | None = None, mode: int | None = None,
    maximum: int = 4 * 1024 * 1024,
) -> bytes:
    direct = path.absolute()
    try:
        if direct != path or direct.resolve(strict=True) != direct:
            raise D1FreshBaselineError(f"{label} path is indirect")
        flags = os.O_RDONLY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(direct, flags)
    except OSError as exc:
        raise D1FreshBaselineError(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise D1FreshBaselineError(f"{label} is not a single-link regular file")
        if mode is not None and stat.S_IMODE(before.st_mode) != mode:
            raise D1FreshBaselineError(f"{label} mode differs")
        if before.st_size > maximum:
            raise D1FreshBaselineError(f"{label} exceeds its bounded read")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, key) != getattr(after, key) for key in fields):
        raise D1FreshBaselineError(f"{label} changed while open")
    payload = b"".join(chunks)
    if expected_size is not None and len(payload) != expected_size:
        raise D1FreshBaselineError(f"{label} size differs")
    if expected_sha256 is not None and hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise D1FreshBaselineError(f"{label} hash differs")
    return payload


def _source_receipt(path: Path, payload: bytes) -> dict[str, Any]:
    return {"path": _relative(path), **_identity(payload)}


def _strict_object(payload: bytes, label: str) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise D1FreshBaselineError(f"{label} contains a duplicate key")
            out[key] = value
        return out

    try:
        value = json.loads(
            payload.decode("utf-8"), object_pairs_hook=unique,
            parse_constant=lambda item: (_ for _ in ()).throw(
                D1FreshBaselineError(f"{label} contains non-finite JSON: {item}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D1FreshBaselineError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise D1FreshBaselineError(f"{label} is not an object")
    return value


def _load_reducer() -> Any:
    before = _stable_read(
        REDUCER, "P3.19 fresh-baseline reducer", maximum=512 * 1024
    )
    spec = importlib.util.spec_from_file_location("p319_d1_bound_reducer", REDUCER)
    if spec is None or spec.loader is None:
        raise D1FreshBaselineError("P3.19 reducer cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise D1FreshBaselineError(f"P3.19 reducer failed to load: {type(exc).__name__}") from exc
    after = _stable_read(
        REDUCER, "post-import P3.19 fresh-baseline reducer", maximum=512 * 1024
    )
    if after != before:
        raise D1FreshBaselineError("P3.19 reducer changed while importing")
    return module


def _candidate_binding(reducer: Any) -> dict[str, Any]:
    candidate = reducer._current_candidate_identity()
    return {
        "target": candidate["target"],
        "intent": candidate["intent"],
        "qualification": candidate["qualification"],
        "closure": candidate["closure"],
    }


def _expected_manifest(
    *, script_payload: bytes, reducer_payload: bytes, p318_payload: bytes,
    p296_payload: bytes, d0_payload: bytes, reference_payload: bytes,
    profile_payload: bytes, adb_payload: bytes,
    current_candidate: Mapping[str, Any],
    review: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": BINDING_SCHEMA,
        "binding_id": BINDING_ID,
        "action": "one exact attended normal Android reboot",
        "authority_prefix": AUTHORITY_PREFIX,
        "target": TARGET,
        "target_profile": _source_receipt(PROFILE, profile_payload),
        "current_candidate": dict(current_candidate),
        "inputs": {
            "d1_source": _source_receipt(SCRIPT, script_payload),
            "fresh_baseline_reducer": _source_receipt(REDUCER, reducer_payload),
            "p318_reviewed_wrapper": _source_receipt(P318_WRAPPER, p318_payload),
            "p296_reboot_primitive": _source_receipt(P296_PRIMITIVE, p296_payload),
            "current_d0_runtime": _source_receipt(D0_RUNTIME, d0_payload),
            "reference_d0_identity_health": _source_receipt(REFERENCE_D0, reference_payload),
            "host_adb": _source_receipt(ADB, adb_payload),
        },
        "reference_d0": {
            "purpose": "exact-target serial and healthy-partition reference only",
            "historical_topology_is_current_authority": False,
        },
        "host_adb_execution_snapshot": {
            "path": _relative(ADB_SNAPSHOT), "size": ADB_SIZE,
            "sha256": ADB_SHA256, "mode": "0500",
            "publication": "file-fsync-link-no-replace-directory-fsync",
        },
        "run_directory": {
            "path": _relative(RUN_DIR),
            "publication": "directory-no-replace-then-durable-start-no-replace",
        },
        "run_approval_arm": {
            "path": _relative(RUN_ARM),
            "publication": "file-no-replace-fsync-then-directory-fsync",
        },
        "run_stop": {
            "path": _relative(RUN_STOP),
            "publication": "file-no-replace-fsync-then-directory-fsync",
        },
        "independent_review": dict(review),
        "command_count": 1,
        "initiation_bound_sec": 60,
        "return_bound_sec": 240,
        "live_exact_serial_identity_required": True,
        "live_topology_continuity_required": True,
        "transport_id_drift_allowed": True,
        "candidate_transfer": False,
        "partition_payload": False,
        "odin": False,
        "download_transition": False,
        "f1_authorized": False,
        "failure_rule": "consumed stop without replay or a second reboot command",
    }


def _validated_inputs() -> dict[str, Any]:
    script_payload = _stable_read(SCRIPT, "P3.19 D1 source", maximum=512 * 1024)
    reducer_payload = _stable_read(REDUCER, "P3.19 fresh-baseline reducer", maximum=512 * 1024)
    p318_payload = _stable_read(P318_WRAPPER, "reviewed P3.18 D1 wrapper", expected_size=P318_WRAPPER_SIZE, expected_sha256=P318_WRAPPER_SHA256, maximum=P318_WRAPPER_SIZE)
    p296_payload = _stable_read(P296_PRIMITIVE, "reviewed P2.96 reboot primitive", expected_size=P296_PRIMITIVE_SIZE, expected_sha256=P296_PRIMITIVE_SHA256, maximum=P296_PRIMITIVE_SIZE)
    d0_payload = _stable_read(D0_RUNTIME, "current D0 runtime", expected_size=D0_RUNTIME_SIZE, expected_sha256=D0_RUNTIME_SHA256, maximum=D0_RUNTIME_SIZE)
    reference_payload = _stable_read(REFERENCE_D0, "reference healthy D0", expected_size=REFERENCE_D0_SIZE, expected_sha256=REFERENCE_D0_SHA256, mode=0o400, maximum=REFERENCE_D0_SIZE)
    intent_payload = _stable_read(
        INTENT, "current P3.19 intent", mode=0o400, maximum=256 * 1024
    )
    qualification_payload = _stable_read(
        QUALIFICATION, "current P3.19 qualification", mode=0o400,
        maximum=256 * 1024,
    )
    profile_payload = _stable_read(PROFILE, "S22+ target profile", maximum=16 * 1024)
    adb_payload = _stable_read(ADB, "host ADB executable", expected_size=ADB_SIZE, expected_sha256=ADB_SHA256, maximum=ADB_SIZE)
    binding_payload = _stable_read(BINDING_MANIFEST, "P3.19 D1 execution binding", maximum=64 * 1024)
    binding = _strict_object(binding_payload, "P3.19 D1 execution binding")
    if binding_payload != canonical(binding):
        raise D1FreshBaselineError("P3.19 D1 execution binding is not canonical JSON")
    review = binding.get("independent_review")
    allowed_reviews = (
        {"status": "review-pending", "verdict": None},
        {"status": "pass-go", "verdict": "PASS_GO_P319_D1_FRESH_BASELINE_H0_CAPABILITY_V1"},
    )
    if not any(_typed_equal(review, item) for item in allowed_reviews):
        raise D1FreshBaselineError("independent D1 review shape differs")
    current_candidate = {
        "target": TARGET,
        "intent": _source_receipt(INTENT, intent_payload),
        "qualification": _source_receipt(QUALIFICATION, qualification_payload),
        "closure": {
            "source_keys": {
                "count": 437,
                "sha256": "f41bfd2d1a4cf62aa62500a636a22e2035f3d56f9151e806e80da86f6c9cdded",
            },
            "module_plan": {
                "count": 73, "eud_index": 38,
                "overlay_delta": ["s22plus_dwc3_event_latch.ko"],
            },
        },
    }
    expected = _expected_manifest(
        script_payload=script_payload, reducer_payload=reducer_payload,
        p318_payload=p318_payload, p296_payload=p296_payload,
        d0_payload=d0_payload, reference_payload=reference_payload,
        profile_payload=profile_payload, adb_payload=adb_payload,
        current_candidate=current_candidate, review=review,
    )
    if not _typed_equal(binding, expected):
        raise D1FreshBaselineError("P3.19 D1 execution binding differs")
    # Only now may the reducer execute: its exact path/size/hash and every
    # other manifest field have already matched the canonical binding.
    reducer = _load_reducer()
    if not _typed_equal(_candidate_binding(reducer), current_candidate):
        raise D1FreshBaselineError("P3.19 reducer candidate derivation differs")
    reference = _strict_object(reference_payload, "reference healthy D0")
    profile = _strict_object(profile_payload, "S22+ target profile")
    try:
        target_evidence = reference["target_evidence"]
        health = reference["health"]
        profile_target = profile["target"]
    except (KeyError, TypeError) as exc:
        raise D1FreshBaselineError("reference D0/profile shape differs") from exc
    if (
        reference.get("schema") != "s22plus_fyg8_max77705_sysfs_d0_v1"
        or reference.get("verdict") != "PASS_S22PLUS_FYG8_MAX77705_SYSFS_D0_READ_ONLY"
        or target_evidence.get("identity") != {"model": TARGET["model"], "device": TARGET["codename"], "incremental": TARGET["build"]}
        or target_evidence.get("inventory_row_count") != 1
        or target_evidence.get("other_target_command_count") != 0
        or not isinstance(target_evidence.get("adb_serial_sha256"), str)
        or len(target_evidence["adb_serial_sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in target_evidence["adb_serial_sha256"])
        or profile_target.get("model") != TARGET["model"]
        or profile_target.get("device") != TARGET["codename"]
        or profile_target.get("firmware_incremental") != TARGET["build"]
        or health.get("android_boot_completed") is not True
        or health.get("boot_animation_stopped") is not True
        or health.get("root_verified") is not True
        or health.get("odin_endpoint_absent") is not True
        or not isinstance(health.get("kernel_release"), str)
        or not health["kernel_release"]
        or health.get("verified_boot_state")
        != profile.get("start_health", {}).get("verified_boot_state")
        or health.get("boot_sha256")
        != profile.get("start_health", {}).get("boot_sha256")
        or health.get("supporting_partition_sha256")
        != profile.get("start_health", {}).get("supporting_partition_sha256")
        or reference.get("device_contact") is not True
        or reference.get("device_writes") is not False
        or reference.get("reboot_requested") is not False
        or reference.get("partition_transfer") is not False
        or reference.get("f1_authorized") is not False
    ):
        raise D1FreshBaselineError("reference D0/profile semantics differ")
    manifest_receipt = _source_receipt(BINDING_MANIFEST, binding_payload)
    authority = AUTHORITY_PREFIX + manifest_receipt["sha256"]
    return {
        "manifest": binding,
        "manifest_receipt": manifest_receipt,
        "authority": authority,
        "approval_sha256": hashlib.sha256(authority.encode("ascii")).hexdigest(),
        "candidate": reducer._current_candidate_identity(),
        "baseline_design": reducer._baseline_design_identity(),
        "reducer": reducer,
        "profile": profile,
        "prior_binding": {
            "target": {"model": TARGET["model"], "device": TARGET["codename"], "firmware_incremental": TARGET["build"], "adb_serial_sha256": target_evidence["adb_serial_sha256"]},
            "health": json.loads(json.dumps(health)),
        },
        "p296_payload": p296_payload,
        "p318_payload": p318_payload,
        "d0_payload": d0_payload,
        "adb_payload": adb_payload,
    }


def _load_p318(payload: bytes) -> Any:
    if (
        len(payload) != P318_WRAPPER_SIZE
        or hashlib.sha256(payload).hexdigest() != P318_WRAPPER_SHA256
    ):
        raise D1FreshBaselineError("reviewed P3.18 wrapper payload differs")
    name = "p319_bound_p318_wrapper"
    spec = importlib.util.spec_from_loader(
        name, loader=None, origin=str(P318_WRAPPER)
    )
    if spec is None:
        raise D1FreshBaselineError("reviewed P3.18 wrapper cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(P318_WRAPPER)
    module.__package__ = None
    sys.modules[name] = module
    try:
        code = compile(
            payload, str(P318_WRAPPER), "exec", dont_inherit=True
        )
        exec(code, module.__dict__)
    except BaseException as exc:
        if sys.modules.get(name) is module:
            del sys.modules[name]
        raise D1FreshBaselineError(f"reviewed P3.18 wrapper failed to load: {type(exc).__name__}") from exc
    try:
        current = _stable_read(
            P318_WRAPPER, "post-import reviewed P3.18 D1 wrapper",
            expected_size=P318_WRAPPER_SIZE,
            expected_sha256=P318_WRAPPER_SHA256,
            maximum=P318_WRAPPER_SIZE,
        )
    except BaseException:
        if sys.modules.get(name) is module:
            del sys.modules[name]
        raise
    if current != payload:
        if sys.modules.get(name) is module:
            del sys.modules[name]
        raise D1FreshBaselineError("reviewed P3.18 wrapper changed while importing")
    return module


def _validate_p318_post(inputs: Mapping[str, Any]) -> None:
    payload = _stable_read(
        P318_WRAPPER, "post-run reviewed P3.18 D1 wrapper",
        expected_size=P318_WRAPPER_SIZE,
        expected_sha256=P318_WRAPPER_SHA256,
        maximum=P318_WRAPPER_SIZE,
    )
    if (
        payload != inputs["p318_payload"]
        or _source_receipt(P318_WRAPPER, payload)
        != inputs["manifest"]["inputs"]["p318_reviewed_wrapper"]
    ):
        raise D1FreshBaselineError("reviewed P3.18 wrapper changed during D1")


def _durable_create(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical(dict(value))
    parent = path.parent.absolute()
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if parent.resolve(strict=True) != parent:
        raise D1FreshBaselineError("D1 journal parent is indirect")
    metadata = parent.stat(follow_symlinks=False)
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise D1FreshBaselineError("D1 journal parent metadata differs")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o400)
    except FileExistsError as exc:
        raise D1FreshBaselineError(f"D1 journal already exists: {path.name}") from exc
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise D1FreshBaselineError("short D1 journal write")
            offset += written
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _journal_receipt(path: Path) -> dict[str, Any]:
    payload = _stable_read(path, f"D1 {path.name}", mode=0o400, maximum=256 * 1024)
    metadata = path.stat(follow_symlinks=False)
    return {"path": _relative(path), "size": len(payload), "sha256": hashlib.sha256(payload).hexdigest(), "mode": "0400", "nlink": metadata.st_nlink}


def _validate_adb_snapshot(inputs: Mapping[str, Any]) -> dict[str, Any]:
    expected = inputs["manifest"]["host_adb_execution_snapshot"]
    payload = _stable_read(
        ADB_SNAPSHOT, "post-run host ADB snapshot", expected_size=ADB_SIZE,
        expected_sha256=ADB_SHA256, mode=0o500, maximum=ADB_SIZE,
    )
    actual = {
        "path": _relative(ADB_SNAPSHOT), "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(), "mode": "0500",
        "publication": "file-fsync-link-no-replace-directory-fsync",
    }
    if not _typed_equal(actual, expected):
        raise D1FreshBaselineError("post-run host ADB snapshot binding differs")
    return actual


def _validate_profile_post(inputs: Mapping[str, Any]) -> None:
    payload = _stable_read(
        PROFILE, "post-run S22+ target profile", maximum=16 * 1024
    )
    if _source_receipt(PROFILE, payload) != inputs["manifest"]["target_profile"]:
        raise D1FreshBaselineError("S22+ target profile changed during D1")


def _validate_reducer_post(inputs: Mapping[str, Any]) -> None:
    payload = _stable_read(
        REDUCER, "post-run P3.19 fresh-baseline reducer", maximum=512 * 1024
    )
    if (
        _source_receipt(REDUCER, payload)
        != inputs["manifest"]["inputs"]["fresh_baseline_reducer"]
    ):
        raise D1FreshBaselineError("P3.19 reducer changed during D1")


def _pinned_profile_loader(module: Any, profile: Mapping[str, Any]) -> Any:
    def load(path: Path, label: str) -> dict[str, Any]:
        if path != module.PROFILE or label != "S22+ target profile":
            raise module.RotationError("P3.19 D1 attempted an unbound JSON reopen")
        return json.loads(json.dumps(profile))

    return load


def _health_from_snapshot(module: Any, original: Any, snapshot: dict[str, Any], binding: dict[str, Any], *, initial: bool) -> dict[str, Any]:
    base = original(snapshot, binding, initial=initial)
    properties = snapshot.get("properties")
    if not isinstance(properties, dict) or not isinstance(properties.get("kernel_release"), str) or not properties["kernel_release"]:
        raise module.RotationError("kernel release is unavailable")
    return {
        "android_boot_completed": base["android_boot_completed"],
        "boot_animation_stopped": base["boot_animation_stopped"],
        "verified_boot_state": properties["verified_boot_state"],
        "root_verified": base["root_verified"],
        "boot_sha256": base["boot_sha256"],
        "supporting_partition_sha256": base["supporting_partition_sha256"],
        "odin_endpoint_absent": base["odin_endpoint_absent"],
        "kernel_release": properties["kernel_release"],
        "boot_id_sha256": base["boot_id_sha256"],
    }


def _selection(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {"inventory_count", "inventory_models", "inventory_sha256", "selected_serial_sha256", "selected_topology_sha256", "other_targets_commanded"}
    if set(value) != expected or type(value["inventory_count"]) is not int or value["inventory_count"] < 1:
        raise D1FreshBaselineError("D1 primitive selection shape differs")
    return {
        "inventory_count": value["inventory_count"],
        "inventory_digest": value["inventory_sha256"],
        "selected_serial_sha256": value["selected_serial_sha256"],
        "selected_topology_sha256": value["selected_topology_sha256"],
        "other_targets_commanded": value["other_targets_commanded"],
    }


def _result_binding(inputs: Mapping[str, Any], journal: Mapping[str, Any]) -> dict[str, Any]:
    manifest = inputs["manifest"]
    return {
        "schema": "s22plus_fyg8_p319_d1_fresh_baseline_binding_v1",
        "action": manifest["action"],
        "adapter": {
            **_source_receipt(
                SCRIPT, _stable_read(SCRIPT, "P3.19 D1 source", maximum=512 * 1024)
            ),
            "schema": "s22plus_fyg8_p319_d1_fresh_baseline_binding_v1",
        },
        "baseline_design": inputs["baseline_design"],
        "candidate": inputs["candidate"],
        "execution_manifest": inputs["manifest_receipt"],
        "approval_sha256": inputs["approval_sha256"],
        "run_directory": manifest["run_directory"],
        "run_approval_arm": manifest["run_approval_arm"],
        "journal": dict(journal),
        "candidate_transfer": False,
        "partition_payload": False,
        "odin": False,
        "download_transition": False,
        "f1_authorized": False,
    }


def _pinned_base(inputs: Mapping[str, Any], p318: Any) -> Any:
    prior = list(sys.path)
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        return p318._load_base(
            inputs["p296_payload"], inputs["d0_payload"], inputs["authority"]
        )
    finally:
        sys.path[:] = prior


def _execute_primitive(
    inputs: Mapping[str, Any], p318: Any, *,
    transport_factory: Any | None = None, clock_factory: Any | None = None,
) -> dict[str, Any]:
    module = _pinned_base(inputs, p318)
    module.SCHEMA = "s22plus_fyg8_p319_d1_fresh_baseline_v1"
    module.VERDICT = RESULT_VERDICT
    module.RUN_ROOT = RUN_DIR.parent
    module.INITIATION_BOUND_SEC = 60.0
    module.RETURN_BOUND_SEC = 240.0
    module.prior_binding = lambda: json.loads(json.dumps(inputs["prior_binding"]))
    original_validate = module.validate_snapshot
    original_create = module.d0.durable_create
    original_load_json = module.load_json

    def validate(snapshot: dict[str, Any], binding: dict[str, Any], *, initial: bool) -> dict[str, Any]:
        return _health_from_snapshot(module, original_validate, snapshot, binding, initial=initial)

    start_holder: dict[str, Any] = {}

    def create(path: Path, value: dict[str, Any]) -> None:
        if path == RUN_DIR / "start.json":
            transformed = {
                "schema": "s22plus_fyg8_p319_d1_fresh_baseline_start_v1",
                "execution_manifest": inputs["manifest_receipt"],
                "approval_sha256": inputs["approval_sha256"],
                "before": value.get("before"),
                "selection": _selection(value.get("selection", {})),
                "reboot_count": 1,
                "reboot_requested": True,
                "device_writes": False,
                "candidate_transfer": False,
                "partition_transfer": False,
                "odin_invoked": False,
                "download_transition_requested": False,
                "f1_authorized": False,
            }
            _durable_create(path, transformed)
            start_holder.update(transformed)
            return
        if path == RUN_DIR / "result.json":
            before = value.get("before")
            after = value.get("after")
            selection = _selection(value.get("selection", {}))
            if start_holder.get("before") != before or start_holder.get("selection") != selection:
                raise module.RotationError("D1 result differs from its durable start")
            journal = {"arm": _journal_receipt(RUN_ARM), "start": _journal_receipt(RUN_DIR / "start.json"), "result": {"path": _relative(RUN_DIR / "result.json")}}
            binding = _result_binding(inputs, journal)
            result = {
                "schema": RESULT_SCHEMA,
                "version": RESULT_VERSION,
                "mode": "attended-normal-reboot",
                "baseline_design_id": inputs["baseline_design"]["design_id"],
                "target": TARGET,
                "binding": binding,
                "before": before,
                "after": after,
                "selection": selection,
                "journal": journal,
                "reboot_count": 1,
                "candidate_transfer": False,
                "device_writes": False,
                "download_transition_requested": False,
                "odin_invoked": False,
                "partition_transfer": False,
                "f1_authorized": False,
                "live_authorized": False,
                "other_targets_commanded": False,
                "verdict": RESULT_VERDICT,
            }
            _durable_create(path, result)
            return
        raise module.RotationError("D1 primitive attempted an unbound journal path")

    module.validate_snapshot = validate
    module.d0.durable_create = create
    module.load_json = _pinned_profile_loader(module, inputs["profile"])
    try:
        transport = (
            module.RealTransport(ADB_SNAPSHOT, inputs["prior_binding"])
            if transport_factory is None
            else transport_factory(module, inputs["prior_binding"])
        )
        clock = module.RealClock() if clock_factory is None else clock_factory(module)
        return module.perform_rotation(
            transport, inputs["prior_binding"], clock, RUN_DIR
        )
    finally:
        module.validate_snapshot = original_validate
        module.d0.durable_create = original_create
        module.load_json = original_load_json


def _run_fixture(inputs: Mapping[str, Any]) -> dict[str, Any]:
    p318 = _load_p318(inputs["p318_payload"])
    module = _pinned_base(inputs, p318)
    original = module.validate_snapshot

    def validate(snapshot: dict[str, Any], binding: dict[str, Any], *, initial: bool) -> dict[str, Any]:
        snapshot = json.loads(json.dumps(snapshot))
        snapshot["properties"]["kernel_release"] = "5.10.226-fixture"
        return _health_from_snapshot(module, original, snapshot, binding, initial=initial)

    module.validate_snapshot = validate
    binding = module.fixture_binding()
    transport = module.FixtureTransport(binding)
    with tempfile.TemporaryDirectory(prefix="p319-d1-fixture-") as temporary:
        result = module.perform_rotation(transport, binding, module.FakeClock(), Path(temporary) / "run")
    if transport.reboot_count != 1 or transport.other_target_commands != 0:
        raise D1FreshBaselineError("P3.19 D1 fixture action count differs")
    return {
        "schema": "s22plus_fyg8_p319_d1_fresh_baseline_fixture_v1",
        "verdict": "PASS_P319_D1_FRESH_BASELINE_FIXTURE_H0",
        "primitive_verdict": result["verdict"],
        "reboot_count": transport.reboot_count,
        "other_target_commands": transport.other_target_commands,
        "device_contact": False,
        "live_authorized": False,
        "review_status": inputs["manifest"]["independent_review"]["status"],
    }


def _direct_regular(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return stat.S_ISREG(metadata.st_mode) and metadata.st_uid == os.getuid()


def _arm_bytes_complete(inputs: Mapping[str, Any]) -> bool:
    try:
        payload = _stable_read(
            RUN_ARM, "P3.19 D1 arm after cut", mode=0o400,
            maximum=64 * 1024,
        )
        return _typed_equal(
            _strict_object(payload, "P3.19 D1 arm after cut"),
            _arm_value(inputs),
        )
    except (D1FreshBaselineError, OSError):
        return False


def _optional_journal_payload(path: Path, label: str) -> bytes | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise D1FreshBaselineError(f"{label} cannot be inspected") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o400
    ):
        raise D1FreshBaselineError(f"{label} node identity differs")
    return _stable_read(path, label, mode=0o400, maximum=512 * 1024)


def _start_bytes_complete(payload: bytes, inputs: Mapping[str, Any]) -> bool:
    try:
        value = _strict_object(payload, "P3.19 D1 start after cut")
    except D1FreshBaselineError:
        return False
    if payload != canonical(value):
        raise D1FreshBaselineError("P3.19 D1 start is not canonical JSON")
    required = {
        "schema", "execution_manifest", "approval_sha256", "before",
        "selection", "reboot_count", "reboot_requested", "device_writes",
        "candidate_transfer", "partition_transfer", "odin_invoked",
        "download_transition_requested", "f1_authorized",
    }
    if (
        set(value) != required
        or value["schema"]
        != "s22plus_fyg8_p319_d1_fresh_baseline_start_v1"
        or value["execution_manifest"] != inputs["manifest_receipt"]
        or value["approval_sha256"] != inputs["approval_sha256"]
        or value["reboot_count"] != 1
        or value["reboot_requested"] is not True
        or not isinstance(value["before"], dict)
        or not isinstance(value["selection"], dict)
    ):
        raise D1FreshBaselineError("P3.19 D1 start binding differs")
    for key in (
        "device_writes", "candidate_transfer", "partition_transfer",
        "odin_invoked", "download_transition_requested", "f1_authorized",
    ):
        if value[key] is not False:
            raise D1FreshBaselineError("P3.19 D1 start safety claim differs")
    return True


def _result_bytes_complete(payload: bytes, inputs: Mapping[str, Any]) -> bool:
    try:
        value = _strict_object(payload, "P3.19 D1 result after cut")
    except D1FreshBaselineError:
        return False
    if payload != canonical(value):
        raise D1FreshBaselineError("P3.19 D1 result is not canonical JSON")
    binding = value.get("binding")
    required = {
        "schema", "version", "mode", "baseline_design_id", "target",
        "binding", "before", "after", "selection", "journal",
        "reboot_count", "candidate_transfer", "device_writes",
        "download_transition_requested", "odin_invoked", "partition_transfer",
        "f1_authorized", "live_authorized", "other_targets_commanded", "verdict",
    }
    if (
        set(value) != required
        or value.get("schema") != RESULT_SCHEMA
        or value.get("version") != RESULT_VERSION
        or value.get("mode") != "attended-normal-reboot"
        or value.get("verdict") != RESULT_VERDICT
        or value.get("baseline_design_id")
        != inputs["baseline_design"]["design_id"]
        or value.get("target") != TARGET
        or value.get("reboot_count") != 1
        or not isinstance(binding, dict)
        or binding.get("execution_manifest") != inputs["manifest_receipt"]
        or binding.get("approval_sha256") != inputs["approval_sha256"]
        or binding.get("baseline_design") != inputs["baseline_design"]
        or binding.get("candidate") != inputs["candidate"]
        or value.get("journal") != binding.get("journal")
        or not isinstance(value.get("before"), dict)
        or not isinstance(value.get("after"), dict)
        or not isinstance(value.get("selection"), dict)
    ):
        raise D1FreshBaselineError("P3.19 D1 result binding differs")
    for key in (
        "candidate_transfer", "device_writes", "download_transition_requested",
        "odin_invoked", "partition_transfer", "f1_authorized",
        "live_authorized", "other_targets_commanded",
    ):
        if value[key] is not False:
            raise D1FreshBaselineError("P3.19 D1 result safety claim differs")
    return True


def _validate_stop_namespace(
    value: Mapping[str, Any], inputs: Mapping[str, Any], *, publishing: bool
) -> None:
    arm_payload = _optional_journal_payload(RUN_ARM, "P3.19 D1 stop arm")
    start_payload = _optional_journal_payload(
        RUN_DIR / "start.json", "P3.19 D1 stop start"
    )
    result_payload = _optional_journal_payload(
        RUN_DIR / "result.json", "P3.19 D1 stop result"
    )
    actual = {
        "arm_present": arm_payload is not None,
        "arm_bytes_complete": (
            _arm_bytes_complete(inputs) if arm_payload is not None else False
        ),
        "start_present": start_payload is not None,
        "start_bytes_complete": (
            _start_bytes_complete(start_payload, inputs)
            if start_payload is not None else False
        ),
        "result_present": result_payload is not None,
        "result_bytes_complete": (
            _result_bytes_complete(result_payload, inputs)
            if result_payload is not None else False
        ),
    }
    if any(value[key] is not state for key, state in actual.items()):
        raise D1FreshBaselineError("D1 stop cut-state does not match fixed files")
    try:
        run_metadata = RUN_DIR.lstat()
    except FileNotFoundError:
        if not publishing or actual["start_present"] or actual["result_present"]:
            raise D1FreshBaselineError("D1 stop run directory is absent")
        return
    except OSError as exc:
        raise D1FreshBaselineError("D1 stop run directory cannot be inspected") from exc
    if (
        not stat.S_ISDIR(run_metadata.st_mode)
        or run_metadata.st_uid != os.getuid()
        or stat.S_IMODE(run_metadata.st_mode) != 0o700
    ):
        raise D1FreshBaselineError("D1 stop run directory identity differs")
    expected_children = {
        name for name, present in (
            ("start.json", actual["start_present"]),
            ("result.json", actual["result_present"]),
            ("stop.json", not publishing),
        ) if present
    }
    if {child.name for child in RUN_DIR.iterdir()} != expected_children:
        raise D1FreshBaselineError("D1 stop fixed namespace differs")


def validate_stop(
    value: Any, path: Path | None = None,
    inputs: Mapping[str, Any] | None = None,
    *, publishing: bool = False,
) -> dict[str, Any]:
    required = {"schema", "verdict", "execution_manifest", "approval_sha256", "run_directory", "stage", "error_type", "arm_present", "arm_bytes_complete", "start_present", "start_bytes_complete", "result_present", "result_bytes_complete", "reboot_dispatch_possible", "candidate_transfer", "partition_payload", "odin", "download_transition", "f1_authorized", "result_reusable", "replay_authorized", "device_contact_unknown"}
    if not isinstance(value, dict) or set(value) != required:
        raise D1FreshBaselineError("D1 stop key set differs")
    if value["schema"] != STOP_SCHEMA or value["verdict"] != STOP_VERDICT:
        raise D1FreshBaselineError("D1 stop header differs")
    if value["run_directory"] != _relative(RUN_DIR) or not isinstance(value["error_type"], str) or not value["error_type"]:
        raise D1FreshBaselineError("D1 stop run/error identity differs")
    if value["stage"] not in {
        "after-arm-before-start", "after-start-before-result",
        "after-result-validation-failure",
    }:
        raise D1FreshBaselineError("D1 stop stage differs")
    booleans = ("arm_present", "arm_bytes_complete", "start_present", "start_bytes_complete", "result_present", "result_bytes_complete", "reboot_dispatch_possible", "candidate_transfer", "partition_payload", "odin", "download_transition", "f1_authorized", "result_reusable", "replay_authorized", "device_contact_unknown")
    if any(type(value[key]) is not bool for key in booleans):
        raise D1FreshBaselineError("D1 stop contains an untyped boolean")
    if value["arm_present"] is not True or value["reboot_dispatch_possible"] is not value["start_present"] or any(value[key] is not False for key in ("candidate_transfer", "partition_payload", "odin", "download_transition", "f1_authorized", "result_reusable", "replay_authorized")) or value["device_contact_unknown"] is not True:
        raise D1FreshBaselineError("D1 stop safety accounting differs")
    expected_stage = (
        "after-result-validation-failure" if value["result_present"] else
        "after-start-before-result" if value["start_present"] else
        "after-arm-before-start"
    )
    if value["stage"] != expected_stage or value["result_present"] and not value["start_present"]:
        raise D1FreshBaselineError("D1 stop stage/start evidence differs")
    if (RUN_STOP if path is None else path) != RUN_STOP:
        raise D1FreshBaselineError("D1 stop path differs")
    bound = _validated_inputs() if inputs is None else inputs
    if (
        value["execution_manifest"] != bound["manifest_receipt"]
        or value["approval_sha256"] != bound["approval_sha256"]
    ):
        raise D1FreshBaselineError("D1 stop execution authority differs")
    if not publishing:
        stop_payload = _optional_journal_payload(
            RUN_STOP, "P3.19 D1 fixed stop"
        )
        if stop_payload is None:
            raise D1FreshBaselineError("P3.19 D1 fixed stop is absent")
        stop_value = _strict_object(stop_payload, "P3.19 D1 fixed stop")
        if stop_payload != canonical(stop_value) or not _typed_equal(stop_value, value):
            raise D1FreshBaselineError("P3.19 D1 fixed stop bytes differ")
    _validate_stop_namespace(value, bound, publishing=publishing)
    return dict(value)


def validate_stop_file(path: Path | None = None) -> dict[str, Any]:
    path = RUN_STOP if path is None else path
    payload = _stable_read(path, "P3.19 D1 stop", mode=0o400, maximum=64 * 1024)
    value = _strict_object(payload, "P3.19 D1 stop")
    if payload != canonical(value):
        raise D1FreshBaselineError("P3.19 D1 stop is not canonical JSON")
    result = validate_stop(value, path)
    if _stable_read(
        path, "final P3.19 D1 stop", mode=0o400, maximum=64 * 1024
    ) != payload:
        raise D1FreshBaselineError("P3.19 D1 stop changed during validation")
    return result


def _publish_stop(inputs: Mapping[str, Any], error: BaseException) -> None:
    start_present = (RUN_DIR / "start.json").is_file()
    result_present = (RUN_DIR / "result.json").is_file()
    value = {
        "schema": STOP_SCHEMA,
        "verdict": STOP_VERDICT,
        "execution_manifest": inputs["manifest_receipt"],
        "approval_sha256": inputs["approval_sha256"],
        "run_directory": _relative(RUN_DIR),
        "stage": (
            "after-result-validation-failure" if result_present else
            "after-start-before-result" if start_present else
            "after-arm-before-start"
        ),
        "error_type": type(error).__name__,
        "arm_present": _direct_regular(RUN_ARM),
        "arm_bytes_complete": _arm_bytes_complete(inputs),
        "start_present": start_present,
        "start_bytes_complete": (
            _start_bytes_complete(
                _optional_journal_payload(
                    RUN_DIR / "start.json", "P3.19 D1 stop start"
                ),
                inputs,
            ) if start_present else False
        ),
        "result_present": result_present,
        "result_bytes_complete": (
            _result_bytes_complete(
                _optional_journal_payload(
                    RUN_DIR / "result.json", "P3.19 D1 stop result"
                ),
                inputs,
            ) if result_present else False
        ),
        "reboot_dispatch_possible": start_present,
        "candidate_transfer": False,
        "partition_payload": False,
        "odin": False,
        "download_transition": False,
        "f1_authorized": False,
        "result_reusable": False,
        "replay_authorized": False,
        "device_contact_unknown": True,
    }
    validate_stop(value, inputs=inputs, publishing=True)
    _durable_create(RUN_STOP, value)


def _arm_value(inputs: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "s22plus_fyg8_p319_d1_fresh_baseline_arm_v1",
        "execution_manifest": inputs["manifest_receipt"],
        "approval_sha256": inputs["approval_sha256"],
        "run_directory": inputs["manifest"]["run_directory"],
        "action": inputs["manifest"]["action"],
        "attempt": 1,
        "consumed": True,
        "device_contact_before_arm": False,
    }


def run_live(approval: str) -> dict[str, Any]:
    inputs = _validated_inputs()
    review = inputs["manifest"]["independent_review"]
    if review != {"status": "pass-go", "verdict": "PASS_GO_P319_D1_FRESH_BASELINE_H0_CAPABILITY_V1"}:
        raise D1FreshBaselineError("independent D1 capability review is absent")
    if approval != inputs["authority"]:
        raise D1FreshBaselineError("exact D1 approval is absent")
    p318 = _load_p318(inputs["p318_payload"])
    arm_completed = False
    try:
        p318._durable_arm(RUN_ARM, _arm_value(inputs))
        arm_completed = True
        p318._prepare_executable_snapshot(inputs["adb_payload"], ADB_SNAPSHOT)
        _execute_primitive(inputs, p318)
        _validate_p318_post(inputs)
        _validate_adb_snapshot(inputs)
        _validate_profile_post(inputs)
        _validate_reducer_post(inputs)
        result_payload = _stable_read(RUN_DIR / "result.json", "P3.19 D1 result", mode=0o400, maximum=512 * 1024)
        result = _strict_object(result_payload, "P3.19 D1 result")
        reducer = inputs["reducer"]
        reducer._validate_d1(result, inputs["baseline_design"], inputs["candidate"], reducer._profile(), RUN_DIR / "result.json")
        return result
    except BaseException as exc:
        duplicate_arm = (
            not arm_completed
            and isinstance(exc, p318.AdapterError)
            and str(exc) == "D1 approval arm already exists"
        )
        if duplicate_arm:
            raise D1FreshBaselineError(
                "D1 approval arm already exists; replay is forbidden"
            ) from exc
        if not arm_completed and not _direct_regular(RUN_ARM):
            raise D1FreshBaselineError(
                f"D1 stopped before durable arm: {type(exc).__name__}"
            ) from exc
        try:
            _publish_stop(inputs, exc)
        except BaseException as stop_exc:
            raise D1FreshBaselineError(f"D1 stopped after durable arm; stop publication also failed: {type(stop_exc).__name__}") from exc
        raise D1FreshBaselineError(f"D1 stopped after durable arm: {type(exc).__name__}") from exc


def self_test() -> dict[str, Any]:
    return _run_fixture(_validated_inputs())


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        if arguments in ([], ["--self-test"]):
            result = self_test()
        elif len(arguments) == 3 and arguments[:2] == ["--live", "--approval"]:
            result = run_live(arguments[2])
        else:
            raise D1FreshBaselineError("accepted argv is empty/--self-test or exact --live --approval TOKEN")
        print(json.dumps(result, sort_keys=True))
        return 0
    except (D1FreshBaselineError, OSError, KeyError, TypeError) as exc:
        print(f"P3.19 D1 fresh-baseline blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
