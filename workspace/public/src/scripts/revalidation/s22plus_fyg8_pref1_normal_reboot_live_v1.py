#!/usr/bin/env python3
"""Single-session S22+ pre-F1 normal-reboot live integration.

The tracked binding is review-pending by default, so every connected entry
fails before loading execution inputs.  Once independently reviewed, the fixed
CLI can prepare one read-only activation proposal, activate it with one exact
attended session approval, execute the sole reviewed normal-reboot descriptor,
or reconcile a post-intent cut without replay.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import time
import types
from typing import Any, Callable, Iterator, Mapping


ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve()
BINDING_PATH = (
    ROOT
    / "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_pref1_normal_reboot_live_v1.json"
)
POLICY_PATH = (
    ROOT
    / "docs/operations/targets/"
    "S22PLUS_FYG8_PREF1_AUTONOMOUS_RESEARCH_POLICY_V1.md"
)
COORDINATOR_PATH = (
    ROOT
    / "workspace/public/src/device-action/coordinators/"
    "s22plus_fyg8_pref1_autonomous_coordinator_h0.py"
)
JOURNAL_PATH = (
    ROOT
    / "workspace/public/src/device-action/coordinators/"
    "s22plus_fyg8_pref1_normal_reboot_journal_h0.py"
)
V3_SOURCE = SCRIPT.parent / "s22plus_fyg8_p319_d1_fresh_baseline_v3.py"
RAW_CAPTURE_MODULE = "device_action_raw_capture_v1.py"
V3_BINDING = (
    ROOT
    / "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d1_fresh_baseline_v3.json"
)

SESSION_ROOT = (
    ROOT
    / "workspace/private/runs/"
    "s22plus-pref1-autonomous-research/normal-reboot-session-v1"
)
SESSION_LOCK = SESSION_ROOT / "coordinator.lock"
PREPARE_ADB = SESSION_ROOT / "prepare-adb"
PREPARE_RAW = SESSION_ROOT / "prepare-raw"
PROPOSAL_PATH = SESSION_ROOT / "activation-proposal.json"
PREPARE_STOP = SESSION_ROOT / "prepare-stop.json"
ACTIVATE_ADB = SESSION_ROOT / "activate-adb"
ACTIVATE_RAW = SESSION_ROOT / "activate-raw"
ACTIVATION_PATH = SESSION_ROOT / "activation.json"
JOURNAL_ROOT = SESSION_ROOT / "journal-owner"
RUN_STOP = SESSION_ROOT / "run-stop.json"
PRE_INTENT_PREFIX = "pre-intent-observation"
MAX_PRE_INTENT_OBSERVATIONS = 32

BINDING_SCHEMA = "s22plus_fyg8_pref1_normal_reboot_live_binding_v1"
PROPOSAL_SCHEMA = "s22plus_fyg8_pref1_activation_proposal_v1"
ACTIVATION_ENVELOPE_SCHEMA = "s22plus_fyg8_pref1_activation_envelope_v1"
STOP_SCHEMA = "s22plus_fyg8_pref1_normal_reboot_live_stop_v1"
SELF_TEST_SCHEMA = "s22plus_fyg8_pref1_normal_reboot_live_fixture_v1"
REVIEW_VERDICT = "PASS_GO_S22PLUS_FYG8_PREF1_NORMAL_REBOOT_LIVE_V1"
AUTHORITY_PREFIX = "DEVICE-ACTION-S22PLUS-PREF1-SESSION-V1-APPROVE:"

TARGET = {"model": "SM-S906N", "device": "g0q", "build": "S906NKSS7FYG8"}
CLASS_ID = "normal_android_reboot_health"
PROOF_MODE = "new_boot_health"
PROPOSAL_VALID_SECONDS = 600
SESSION_DURATION_SECONDS = 43_200
MAX_JSON = 512 * 1024
HEX32 = re.compile(r"[0-9a-f]{32}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")

EXPECTED = {
    "policy": (9_587, "b08681059bc0ba1752a93aa908515b8552e0b70423876809b96e032676867c9e"),
    "coordinator": (23_764, "c0d56417c070c5958a356110f4b1996f9c903af993d118e0f812cccdd8aea65e"),
    "journal": (32_123, "0d13c6216c1c6a11795911daefe53ea35ee803f3e5b718b26e839a99599fedf6"),
    "v3_source": (73_125, "cb13236e1fb10bf25ac47f7706df050abe15b2ab5a7e423bbdc7b5b31c2c491d"),
    "v3_binding": (6_705, "dcb869aeeebf877d669da0a1f45b8c1d56a65777c13c9d518c0ad2dace93fc10"),
}


class LiveRunnerError(RuntimeError):
    """Every malformed, stale, uncertain, or unavailable state fails closed."""


def canonical(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise LiveRunnerError("value is not canonical JSON") from exc
    return (text + "\n").encode("utf-8")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise LiveRunnerError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def strict(raw: bytes, label: str, *, maximum: int = MAX_JSON) -> Any:
    if type(raw) is not bytes or not 0 < len(raw) <= maximum:
        raise LiveRunnerError(f"{label} byte extent differs")
    try:
        value = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                LiveRunnerError(f"{label} has non-finite value {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LiveRunnerError(f"{label} is not strict JSON") from exc
    if canonical(value) != raw:
        raise LiveRunnerError(f"{label} is not canonical JSON")
    return value


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise LiveRunnerError("path is outside the repository root") from exc


def _read_regular(
    path: Path,
    label: str,
    *,
    maximum: int,
    expected: tuple[int, str] | None = None,
    mode: int | None = None,
) -> bytes:
    try:
        initial = path.lstat()
        if not stat.S_ISREG(initial.st_mode) or stat.S_ISLNK(initial.st_mode):
            raise LiveRunnerError(f"{label} metadata differs")
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        )
    except LiveRunnerError:
        raise
    except OSError as exc:
        raise LiveRunnerError(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or (before.st_dev, before.st_ino) != (initial.st_dev, initial.st_ino)
            or not 0 < before.st_size <= maximum
            or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        ):
            raise LiveRunnerError(f"{label} metadata differs")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 64 * 1024))
            if not chunk:
                raise LiveRunnerError(f"{label} read was short")
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_nlink,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_nlink,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise LiveRunnerError(f"{label} changed while open")
        payload = b"".join(chunks)
    finally:
        os.close(descriptor)
    if expected is not None and (len(payload), _sha(payload)) != expected:
        raise LiveRunnerError(f"{label} identity differs")
    return payload


def _receipt(path: Path, payload: bytes, *, mode: str | None = None) -> dict[str, Any]:
    value = {"path": _relative(path), "size": len(payload), "sha256": _sha(payload)}
    if mode is not None:
        value.update({"mode": mode, "nlink": 1})
    return value


def _compile(name: str, path: Path, payload: bytes) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = str(path)
    prior = sys.modules.get(name)
    sys.modules[name] = module
    try:
        exec(compile(payload, str(path), "exec", dont_inherit=True), module.__dict__)
    except BaseException as exc:
        raise LiveRunnerError(f"bound module failed to load: {name}") from exc
    finally:
        if prior is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
    return module


def _input_payloads() -> dict[str, bytes]:
    return {
        "source": _read_regular(SCRIPT, "live runner source", maximum=1024 * 1024),
        "policy": _read_regular(POLICY_PATH, "pre-F1 policy", maximum=64 * 1024, expected=EXPECTED["policy"]),
        "coordinator": _read_regular(COORDINATOR_PATH, "coordinator", maximum=128 * 1024, expected=EXPECTED["coordinator"]),
        "journal": _read_regular(JOURNAL_PATH, "journal", maximum=128 * 1024, expected=EXPECTED["journal"]),
        "v3_source": _read_regular(V3_SOURCE, "D1 V3 source", maximum=1024 * 1024, expected=EXPECTED["v3_source"]),
        "v3_binding": _read_regular(V3_BINDING, "D1 V3 binding", maximum=64 * 1024, expected=EXPECTED["v3_binding"]),
    }


def _descriptor(payloads: Mapping[str, bytes]) -> dict[str, Any]:
    journal = _compile("pref1_live_bound_journal_descriptor", JOURNAL_PATH, payloads["journal"])
    descriptor = journal.fixed_descriptor()
    if (
        descriptor.get("class_id") != CLASS_ID
        or descriptor.get("proof_mode") != PROOF_MODE
        or descriptor.get("executor", {}).get("binding", {}).get("sha256")
        != EXPECTED["v3_binding"][1]
        or descriptor.get("live_integration") is not False
    ):
        raise LiveRunnerError("fixed normal-reboot descriptor differs")
    return descriptor


def _expected_binding(
    payloads: Mapping[str, bytes], review: Mapping[str, Any]
) -> dict[str, Any]:
    descriptor = _descriptor(payloads)
    return {
        "schema": BINDING_SCHEMA,
        "binding_id": "s22plus-fyg8-pref1-normal-reboot-live-v1",
        "target": deepcopy(TARGET),
        "source": _receipt(SCRIPT, payloads["source"]),
        "inputs": {
            "policy": _receipt(POLICY_PATH, payloads["policy"]),
            "coordinator": _receipt(COORDINATOR_PATH, payloads["coordinator"]),
            "journal": _receipt(JOURNAL_PATH, payloads["journal"]),
            "v3_source": _receipt(V3_SOURCE, payloads["v3_source"]),
            "v3_binding": _receipt(V3_BINDING, payloads["v3_binding"]),
        },
        "descriptor": {
            "sha256": _sha(canonical(descriptor)),
            "class_id": CLASS_ID,
            "proof_mode": PROOF_MODE,
            "executor_ordinal": "d1-fresh-baseline-3",
            "maximum_invocations": 1,
        },
        "session": {
            "root": _relative(SESSION_ROOT),
            "proposal": _relative(PROPOSAL_PATH),
            "activation": _relative(ACTIVATION_PATH),
            "journal_root": _relative(JOURNAL_ROOT),
            "proposal_valid_seconds": PROPOSAL_VALID_SECONDS,
            "session_duration_seconds": SESSION_DURATION_SECONDS,
            "approval_prefix": AUTHORITY_PREFIX,
        },
        "cli": [
            "--self-test",
            "--prepare-activation",
            "--activate",
            "--run-normal-reboot",
            "--reconcile",
        ],
        "safety": {
            "candidate_transfer": False,
            "partition_payload": False,
            "download_transition": False,
            "odin": False,
            "f1": False,
            "other_target_commands": 0,
            "replay": False,
        },
        "independent_review": dict(review),
    }


def _static() -> dict[str, Any]:
    payloads = _input_payloads()
    raw = _read_regular(BINDING_PATH, "live runner binding", maximum=256 * 1024)
    binding = strict(raw, "live runner binding")
    review = binding.get("independent_review")
    if review not in (
        {"status": "review-pending", "verdict": None},
        {"status": "pass-go", "verdict": REVIEW_VERDICT},
    ):
        raise LiveRunnerError("live runner review state differs")
    if binding != _expected_binding(payloads, review):
        raise LiveRunnerError("live runner binding differs")
    return {
        "payloads": payloads,
        "binding": binding,
        "binding_raw": raw,
        "binding_receipt": _receipt(BINDING_PATH, raw),
        "descriptor": _descriptor(payloads),
    }


def _require_live_review(static: Mapping[str, Any]) -> None:
    if static["binding"]["independent_review"] != {
        "status": "pass-go",
        "verdict": REVIEW_VERDICT,
    }:
        raise LiveRunnerError("independent live-runner review is absent")


def _modules(static: Mapping[str, Any]) -> tuple[types.ModuleType, types.ModuleType]:
    journal = _compile("pref1_live_bound_journal", JOURNAL_PATH, static["payloads"]["journal"])
    v3 = _compile("pref1_live_bound_d1_v3", V3_SOURCE, static["payloads"]["v3_source"])
    if journal.fixed_descriptor() != static["descriptor"]:
        raise LiveRunnerError("post-load descriptor differs")
    return journal, v3


def _direct_directory(path: Path, label: str, *, create: bool) -> None:
    if create:
        try:
            path.mkdir(mode=0o700)
            parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            try:
                os.fsync(parent)
            finally:
                os.close(parent)
        except FileExistsError:
            pass
        except OSError as exc:
            raise LiveRunnerError(f"cannot create {label}") from exc
    try:
        info = path.lstat()
    except OSError as exc:
        raise LiveRunnerError(f"{label} is unavailable") from exc
    if (
        not stat.S_ISDIR(info.st_mode)
        or stat.S_ISLNK(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
        or info.st_uid != os.getuid()
        or path.resolve(strict=True) != path.absolute()
    ):
        raise LiveRunnerError(f"{label} identity differs")


def _initialize_root() -> None:
    _direct_directory(SESSION_ROOT.parent, "pre-F1 run parent", create=False)
    _direct_directory(SESSION_ROOT, "normal-reboot session root", create=True)


@contextmanager
def _lease() -> Iterator[None]:
    _direct_directory(SESSION_ROOT, "normal-reboot session root", create=False)
    descriptor = -1
    try:
        descriptor = os.open(
            SESSION_LOCK,
            os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
        )
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except BlockingIOError as exc:
        raise LiveRunnerError("normal-reboot session is already owned") from exc
    finally:
        if descriptor >= 0:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)


def _publish(journal: types.ModuleType, path: Path, value: Mapping[str, Any]) -> None:
    try:
        journal._atomic_publish(path, journal.canonical_bytes(dict(value)))
    except BaseException as exc:
        raise LiveRunnerError(f"cannot publish {path.name}") from exc


def _publish_stop(
    journal: types.ModuleType,
    *,
    path: Path,
    stage: str,
    error: BaseException,
    intent_durable: bool,
) -> None:
    if path.exists() or path.is_symlink():
        return
    value = {
        "schema": STOP_SCHEMA,
        "stage": stage,
        "error_type": type(error).__name__,
        "intent_durable": intent_durable,
        "replay_authorized": False if intent_durable else None,
        "device_effect_possible": intent_durable,
    }
    _publish(journal, path, value)


def _observation_paths(raw_root: Path, adb_snapshot: Path) -> None:
    if (
        raw_root.exists()
        or raw_root.is_symlink()
        or adb_snapshot.exists()
        or adb_snapshot.is_symlink()
    ):
        raise LiveRunnerError("observation namespace is not fresh")


def _observe_v3(
    v3: types.ModuleType,
    *,
    raw_root: Path,
    adb_snapshot: Path,
    client_factory: Callable[[Any, Any], Any] | None = None,
    usb_snapshot: Callable[..., Any] | None = None,
    binding_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    _observation_paths(raw_root, adb_snapshot)
    static = v3._validated_static_inputs()
    inputs = v3._validated_execution_inputs(static)
    if Path(inputs["raw"].__file__).name != RAW_CAPTURE_MODULE:
        raise LiveRunnerError("D1 V3 raw-capture provider differs")
    p318 = inputs["v1"]._load_p318(inputs["v1_inputs"]["p318_payload"])
    p318._prepare_executable_snapshot(inputs["payloads"]["host_adb"], adb_snapshot)
    inputs["raw"].prepare_capture_dir(raw_root.parent, raw_root.name)
    old_root, old_dir, old_adb = v3.RAW_ROOT, v3.RAW_ADB_DIR, v3.ADB_SNAPSHOT
    v3.RAW_ROOT, v3.RAW_ADB_DIR, v3.ADB_SNAPSHOT = raw_root, raw_root / "raw-adb", adb_snapshot
    try:
        module, _ = v3._pinned_base(inputs)
        original_usb = module.d0.usb_snapshot
        if usb_snapshot is not None:
            module.d0.usb_snapshot = usb_snapshot
        binding = deepcopy(
            inputs["v1_inputs"]["prior_binding"]
            if binding_override is None
            else binding_override
        )
        factory = (
            (lambda d0, _raw: d0.AdbReadOnlyClient(adb_snapshot))
            if client_factory is None
            else client_factory
        )
        try:
            transport = v3._make_transport(
                module,
                inputs["raw"],
                binding,
                inputs["v1_inputs"]["profile"],
                raw_root,
                client_factory=factory,
            )
            serial, selection = transport.select_exact()
            snapshot = transport.snapshot(serial)
            health = inputs["v1"]._health_from_snapshot(
                module,
                module.validate_snapshot,
                snapshot,
                binding,
                initial=True,
            )
        finally:
            module.d0.usb_snapshot = original_usb
        raw_evidence = v3._raw_inventory(inputs["raw"])
        if raw_evidence.get("complete") is not True:
            raise LiveRunnerError("activation observation raw evidence is incomplete")
        required_health = (
            "android_boot_completed",
            "boot_animation_stopped",
            "root_verified",
            "odin_endpoint_absent",
        )
        if any(health.get(key) is not True for key in required_health):
            raise LiveRunnerError("activation observation is not healthy")
        return {
            "target": deepcopy(TARGET),
            "topology_sha256": selection["selected_topology_sha256"],
            "boot_id_sha256": health["boot_id_sha256"],
            "healthy_android": True,
            "selection": selection,
            "health": health,
            "raw_evidence": raw_evidence,
            "adb_snapshot": _receipt(
                adb_snapshot,
                _read_regular(adb_snapshot, "activation ADB snapshot", maximum=2 * 1024 * 1024, mode=0o500),
                mode="0500",
            ),
        }
    finally:
        v3.RAW_ROOT, v3.RAW_ADB_DIR, v3.ADB_SNAPSHOT = old_root, old_dir, old_adb


def _coordinator_observed(observation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "target": deepcopy(TARGET),
        "topology_sha256": observation["topology_sha256"],
        "boot_id_sha256": observation["boot_id_sha256"],
        "healthy_android": observation["healthy_android"],
    }


def _selected_serial(observation: Mapping[str, Any]) -> str:
    selection = observation.get("selection")
    value = (
        selection.get("selected_serial_sha256")
        if type(selection) is dict
        else None
    )
    if type(value) is not str or HEX64.fullmatch(value) is None:
        raise LiveRunnerError("observation selected serial differs")
    return value


def _next_pre_intent_paths() -> tuple[Path, Path]:
    for index in range(MAX_PRE_INTENT_OBSERVATIONS):
        stem = f"{PRE_INTENT_PREFIX}-{index:02d}"
        raw_root = SESSION_ROOT / f"{stem}-raw"
        adb_snapshot = SESSION_ROOT / f"{stem}-adb"
        if not (
            raw_root.exists()
            or raw_root.is_symlink()
            or adb_snapshot.exists()
            or adb_snapshot.is_symlink()
        ):
            return raw_root, adb_snapshot
    raise LiveRunnerError("pre-intent observation slots are exhausted")


def _proposal_value(
    static: Mapping[str, Any],
    observation: Mapping[str, Any],
    *,
    now: int,
    campaign_id: str,
) -> dict[str, Any]:
    if type(now) is not int or now < 0 or HEX32.fullmatch(campaign_id) is None:
        raise LiveRunnerError("proposal clock or campaign id differs")
    return {
        "schema": PROPOSAL_SCHEMA,
        "campaign_id": campaign_id,
        "target": deepcopy(TARGET),
        "runner_binding": static["binding_receipt"],
        "descriptor_sha256": static["binding"]["descriptor"]["sha256"],
        "created_at_epoch": now,
        "expires_at_epoch": now + PROPOSAL_VALID_SECONDS,
        "session_duration_seconds": SESSION_DURATION_SECONDS,
        "d1_effect_max": 8,
        "d0_command_group_max": 256,
        "normal_reboot_invocations_max": 1,
        "observation": deepcopy(dict(observation)),
    }


def _validate_proposal(
    static: Mapping[str, Any],
    raw: bytes,
    *,
    now: int | None,
) -> dict[str, Any]:
    value = strict(raw, "activation proposal")
    if (
        type(value) is not dict
        or value.get("schema") != PROPOSAL_SCHEMA
        or value.get("target") != TARGET
        or value.get("runner_binding") != static["binding_receipt"]
        or value.get("descriptor_sha256") != static["binding"]["descriptor"]["sha256"]
        or type(value.get("campaign_id")) is not str
        or HEX32.fullmatch(value["campaign_id"]) is None
        or type(value.get("created_at_epoch")) is not int
        or type(value.get("expires_at_epoch")) is not int
        or value["expires_at_epoch"] - value["created_at_epoch"] != PROPOSAL_VALID_SECONDS
        or value.get("session_duration_seconds") != SESSION_DURATION_SECONDS
        or value.get("d1_effect_max") != 8
        or value.get("d0_command_group_max") != 256
        or value.get("normal_reboot_invocations_max") != 1
    ):
        raise LiveRunnerError("activation proposal differs")
    if now is not None and not value["created_at_epoch"] <= now < value["expires_at_epoch"]:
        raise LiveRunnerError("activation proposal expired")
    observation = value.get("observation")
    if (
        type(observation) is not dict
        or observation.get("target") != TARGET
        or observation.get("healthy_android") is not True
        or HEX64.fullmatch(str(observation.get("topology_sha256"))) is None
        or HEX64.fullmatch(str(observation.get("boot_id_sha256"))) is None
    ):
        raise LiveRunnerError("activation proposal observation differs")
    _selected_serial(observation)
    return value


def _read_proposal(
    static: Mapping[str, Any], *, now: int | None
) -> tuple[dict[str, Any], bytes]:
    raw = _read_regular(
        PROPOSAL_PATH,
        "activation proposal",
        maximum=MAX_JSON,
        mode=0o400,
    )
    return _validate_proposal(static, raw, now=now), raw


def _approval(proposal_raw: bytes) -> str:
    return AUTHORITY_PREFIX + _sha(proposal_raw)


def prepare_activation(
    *,
    observer: Callable[..., dict[str, Any]] | None = None,
    now: int | None = None,
    campaign_id: str | None = None,
    client_factory: Callable[[Any, Any], Any] | None = None,
    usb_snapshot: Callable[..., Any] | None = None,
    binding_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    static = _static()
    _require_live_review(static)
    journal, v3 = _modules(static)
    if SESSION_ROOT.exists() or SESSION_ROOT.is_symlink():
        raise LiveRunnerError("normal-reboot session namespace already exists")
    _initialize_root()
    with _lease():
        try:
            selected = _observe_v3 if observer is None else observer
            observation = selected(
                v3,
                raw_root=PREPARE_RAW,
                adb_snapshot=PREPARE_ADB,
                client_factory=client_factory,
                usb_snapshot=usb_snapshot,
                binding_override=binding_override,
            )
            current = int(time.time()) if now is None else now
            identifier = secrets.token_hex(16) if campaign_id is None else campaign_id
            proposal = _proposal_value(
                static, observation, now=current, campaign_id=identifier
            )
            _publish(journal, PROPOSAL_PATH, proposal)
        except BaseException as exc:
            _publish_stop(
                journal,
                path=PREPARE_STOP,
                stage="prepare-activation",
                error=exc,
                intent_durable=False,
            )
            raise
    raw = _read_regular(
        PROPOSAL_PATH,
        "published activation proposal",
        maximum=MAX_JSON,
        mode=0o400,
    )
    return {
        "schema": PROPOSAL_SCHEMA,
        "proposal": _receipt(PROPOSAL_PATH, raw, mode="0400"),
        "session_approval": _approval(raw),
        "device_effect": False,
        "d1_consumed": False,
    }


def _activation_value(
    static: Mapping[str, Any],
    journal: types.ModuleType,
    proposal: Mapping[str, Any],
    proposal_raw: bytes,
    approval: str,
    observation: Mapping[str, Any],
    *,
    now: int,
) -> dict[str, Any]:
    coordinator = journal.load_coordinator()
    binding = coordinator.current_binding()
    activation = {
        "schema": coordinator.ACTIVATION_SCHEMA,
        "campaign_id": proposal["campaign_id"],
        "target": deepcopy(TARGET),
        "policy_sha256": binding["policy"]["sha256"],
        "coordinator_sha256": binding["coordinator"]["sha256"],
        "catalog_sha256": binding["catalog_sha256"],
        "effect_core_sha256": static["binding"]["descriptor"]["sha256"],
        "topology_sha256": observation["topology_sha256"],
        "boot_id_sha256": observation["boot_id_sha256"],
        "opened_at_epoch": now,
        "expires_at_epoch": now + SESSION_DURATION_SECONDS,
        "d1_effect_max": coordinator.D1_EFFECT_MAX,
        "d0_command_group_max": coordinator.D0_COMMAND_GROUP_MAX,
        "independent_pass_go_sha256": _sha(REVIEW_VERDICT.encode("ascii")),
        "live_session_approval_sha256": _sha(approval.encode("ascii")),
        "operator_attended_opening": True,
    }
    coordinator.parse_activation_manifest(coordinator.canonical_bytes(activation), now=now)
    return {
        "schema": ACTIVATION_ENVELOPE_SCHEMA,
        "proposal": _receipt(PROPOSAL_PATH, proposal_raw, mode="0400"),
        "session_approval_sha256": _sha(approval.encode("ascii")),
        "selected_serial_sha256": _selected_serial(observation),
        "activation": activation,
    }


def _finish_activation_journal(
    journal: types.ModuleType,
    envelope: Mapping[str, Any],
    *,
    now: int,
) -> str:
    activation_raw = journal.canonical_bytes(envelope["activation"])
    if not (JOURNAL_ROOT.exists() or JOURNAL_ROOT.is_symlink()):
        journal.Journal.create(JOURNAL_ROOT)
    with journal.Journal(JOURNAL_ROOT) as store:
        history = store.history()
        if not history:
            store.record_open(activation_raw, now=now)
            return "ACTIVATED_NO_EFFECT"
        state, intent = store._tail()
        if (
            len(history) != 1
            or history[0]["record"]["kind"] != "CAMPAIGN_OPEN"
            or state is None
            or intent is not None
            or state["phase"] != "OPEN_HEALTHY"
            or state["d1_effects_used"] != 0
            or state["d0_command_groups_used"] != 0
            or state["activation_sha256"] != _sha(activation_raw)
        ):
            raise LiveRunnerError("activation journal is not an empty open campaign")
    return "ACTIVATED_NO_EFFECT_ALREADY_OPEN"


def activate_session(
    approval: str,
    *,
    observer: Callable[..., dict[str, Any]] | None = None,
    now: int | None = None,
    client_factory: Callable[[Any, Any], Any] | None = None,
    usb_snapshot: Callable[..., Any] | None = None,
    binding_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    static = _static()
    _require_live_review(static)
    journal, v3 = _modules(static)
    current = int(time.time()) if now is None else now
    with _lease():
        activation_present = ACTIVATION_PATH.exists() or ACTIVATION_PATH.is_symlink()
        proposal, proposal_raw = _read_proposal(
            static,
            now=None if activation_present else current,
        )
        if approval != _approval(proposal_raw):
            raise LiveRunnerError("exact attended session approval is absent")
        if activation_present:
            envelope, _raw = _read_activation(
                static,
                journal,
                now=current,
                require_current=True,
            )
            status = _finish_activation_journal(journal, envelope, now=current)
            return {
                "schema": ACTIVATION_ENVELOPE_SCHEMA,
                "status": status,
                "campaign_id": proposal["campaign_id"],
                "device_effect": False,
                "d1_consumed": False,
                "expires_at_epoch": envelope["activation"]["expires_at_epoch"],
            }
        if JOURNAL_ROOT.exists() or JOURNAL_ROOT.is_symlink():
            raise LiveRunnerError("journal exists without its activation")
        selected = _observe_v3 if observer is None else observer
        observation = selected(
            v3,
            raw_root=ACTIVATE_RAW,
            adb_snapshot=ACTIVATE_ADB,
            client_factory=client_factory,
            usb_snapshot=usb_snapshot,
            binding_override=binding_override,
        )
        commit_now = int(time.time()) if now is None else now
        current_proposal, current_raw = _read_proposal(static, now=commit_now)
        if current_raw != proposal_raw or current_proposal != proposal:
            raise LiveRunnerError("activation proposal changed during observation")
        prior = proposal["observation"]
        if any(
            observation.get(key) != prior.get(key)
            for key in ("target", "topology_sha256", "boot_id_sha256", "healthy_android")
        ):
            raise LiveRunnerError("activation target, topology, boot, or health changed")
        envelope = _activation_value(
            static,
            journal,
            proposal,
            proposal_raw,
            approval,
            observation,
            now=commit_now,
        )
        _publish(journal, ACTIVATION_PATH, envelope)
        status = _finish_activation_journal(journal, envelope, now=commit_now)
    return {
        "schema": ACTIVATION_ENVELOPE_SCHEMA,
        "status": status,
        "campaign_id": proposal["campaign_id"],
        "device_effect": False,
        "d1_consumed": False,
        "expires_at_epoch": envelope["activation"]["expires_at_epoch"],
    }


def _read_activation(
    static: Mapping[str, Any],
    journal: types.ModuleType,
    *,
    now: int,
    require_current: bool,
) -> tuple[dict[str, Any], bytes]:
    raw = _read_regular(ACTIVATION_PATH, "session activation", maximum=MAX_JSON, mode=0o400)
    value = strict(raw, "session activation")
    if type(value) is not dict or set(value) != {
        "schema",
        "proposal",
        "session_approval_sha256",
        "selected_serial_sha256",
        "activation",
    }:
        raise LiveRunnerError("session activation shape differs")
    if value["schema"] != ACTIVATION_ENVELOPE_SCHEMA:
        raise LiveRunnerError("session activation schema differs")
    proposal, proposal_raw = _read_proposal(static, now=None)
    if value["proposal"] != _receipt(PROPOSAL_PATH, proposal_raw, mode="0400"):
        raise LiveRunnerError("session activation proposal differs")
    activation = value["activation"]
    coordinator = journal.load_coordinator()
    try:
        validation_now = (
            now
            if require_current
            else min(
                max(now, activation.get("opened_at_epoch", -1)),
                activation.get("expires_at_epoch", 0) - 1,
            )
        )
        coordinator.parse_activation_manifest(
            coordinator.canonical_bytes(activation),
            now=validation_now,
        )
    except Exception as exc:
        raise LiveRunnerError("session activation is invalid or expired") from exc
    if (
        activation.get("campaign_id") != proposal["campaign_id"]
        or activation.get("effect_core_sha256") != static["binding"]["descriptor"]["sha256"]
        or not proposal["created_at_epoch"]
        <= activation.get("opened_at_epoch", -1)
        < proposal["expires_at_epoch"]
        or value["session_approval_sha256"]
        != activation.get("live_session_approval_sha256")
        or value["session_approval_sha256"]
        != _sha(_approval(proposal_raw).encode("ascii"))
        or value["selected_serial_sha256"]
        != _selected_serial(proposal["observation"])
    ):
        raise LiveRunnerError("session activation binding differs")
    return value, raw


def _result_observed(
    v3: types.ModuleType,
    result: Mapping[str, Any],
    state: Mapping[str, Any],
    *,
    selected_serial_sha256: str,
) -> dict[str, Any]:
    if (
        type(result) is not dict
        or result.get("schema")
        != "s22plus_fyg8_p319_d1_fresh_baseline_v3_result"
        or result.get("verdict")
        != "PASS_P319_D1_FRESH_BASELINE_V3_EXACT_NORMAL_REBOOT_RETURN_HEALTH"
        or result.get("ordinal") != "d1-fresh-baseline-3"
        or result.get("reboot_count") != 1
        or result.get("other_targets_commanded") is not False
        or not v3._health_complete(result.get("before"))
        or not v3._health_complete(result.get("after"))
        or not v3._selection_complete(result.get("selection"))
        or result["selection"]["selected_serial_sha256"]
        != selected_serial_sha256
        or result.get("before", {}).get("boot_id_sha256") != state["boot_id_sha256"]
        or result.get("selection", {}).get("selected_topology_sha256")
        != state["topology_sha256"]
        or type(result.get("after", {}).get("boot_id_sha256")) is not str
        or HEX64.fullmatch(result["after"]["boot_id_sha256"]) is None
        or result["after"]["boot_id_sha256"] == state["boot_id_sha256"]
        or result.get("raw_evidence", {}).get("complete") is not True
        or any(
            result.get(key) is not False
            for key in (
                "candidate_transfer",
                "partition_payload",
                "odin",
                "download_transition",
                "f1_authorized",
                "replay_authorized",
                "device_writes",
                "live_authorized",
            )
        )
    ):
        raise LiveRunnerError("D1 V3 result does not satisfy the session intent")
    return {
        "target": deepcopy(TARGET),
        "topology_sha256": state["topology_sha256"],
        "boot_id_sha256": result["after"]["boot_id_sha256"],
        "healthy_android": True,
    }


def _default_executor(v3: types.ModuleType) -> dict[str, Any]:
    return v3.run_live(v3._validated_static_inputs()["authority"])


def _default_result_loader(v3: types.ModuleType) -> dict[str, Any]:
    inputs = v3._validated_execution_inputs(v3._validated_static_inputs())
    return v3._post_validate(inputs)


def _reconcile_intent(
    journal: types.ModuleType,
    v3: types.ModuleType,
    store: Any,
    *,
    now: int,
    selected_serial_sha256: str,
    result_loader: Callable[[types.ModuleType], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    state, intent = store._tail()
    if state is None or intent is None:
        raise LiveRunnerError("there is no durable intent to reconcile")
    if state["phase"] == "PARKED":
        return {"status": "PARKED_UNCERTAIN_CONSUMED_NO_REPLAY", "replay": False}
    if state["phase"] != "EFFECT_INTENT_DURABLE":
        raise LiveRunnerError("durable intent state differs")
    try:
        selected_loader = _default_result_loader if result_loader is None else result_loader
        result = selected_loader(v3)
        observed = _result_observed(
            v3,
            result,
            state,
            selected_serial_sha256=selected_serial_sha256,
        )
        store.record_healthy_return(observed, now=now)
    except BaseException:
        store.record_uncertain(reason="result_uncertain", now=now)
        return {"status": "PARKED_UNCERTAIN_CONSUMED_NO_REPLAY", "replay": False}
    store.record_close(now=now)
    return {"status": "RECONCILED_HEALTHY_RETURN", "replay": False}


def _close_completed_effect(store: Any, *, now: int) -> dict[str, Any]:
    state, intent = store._tail()
    if (
        state is None
        or intent is not None
        or state["phase"] != "OPEN_HEALTHY"
        or state["d1_effects_used"] != 1
    ):
        raise LiveRunnerError("completed normal reboot state differs")
    store.record_close(now=now)
    return {"status": "FINALIZED_EXISTING_HEALTHY_RETURN", "replay": False}


def run_normal_reboot(
    *,
    observer: Callable[..., dict[str, Any]] | None = None,
    executor: Callable[[types.ModuleType], dict[str, Any]] | None = None,
    now: int | None = None,
    client_factory: Callable[[Any, Any], Any] | None = None,
    usb_snapshot: Callable[..., Any] | None = None,
    binding_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    static = _static()
    _require_live_review(static)
    journal, v3 = _modules(static)
    current = int(time.time()) if now is None else now
    with _lease():
        activation, activation_raw = _read_activation(
            static,
            journal,
            now=current,
            require_current=False,
        )
        with journal.Journal(JOURNAL_ROOT) as store:
            state, intent = store._tail()
            if state is None:
                raise LiveRunnerError("session journal is empty")
            if state["phase"] == "EFFECT_INTENT_DURABLE" and intent is not None:
                return _reconcile_intent(
                    journal,
                    v3,
                    store,
                    now=current,
                    selected_serial_sha256=activation["selected_serial_sha256"],
                )
            if (
                state["phase"] == "OPEN_HEALTHY"
                and intent is None
                and state["d1_effects_used"] == 1
            ):
                return _close_completed_effect(store, now=current)
            if state["phase"] != "OPEN_HEALTHY" or intent is not None:
                raise LiveRunnerError("session is not eligible for a new effect")
            if state["d1_effects_used"] != 0:
                raise LiveRunnerError("normal reboot was already consumed")
            active_activation, active_raw = _read_activation(
                static,
                journal,
                now=current,
                require_current=True,
            )
            if active_activation != activation or active_raw != activation_raw:
                raise LiveRunnerError("session activation changed before observation")
            selected = _observe_v3 if observer is None else observer
            pre_intent_raw, pre_intent_adb = _next_pre_intent_paths()
            observation = selected(
                v3,
                raw_root=pre_intent_raw,
                adb_snapshot=pre_intent_adb,
                client_factory=client_factory,
                usb_snapshot=usb_snapshot,
                binding_override=binding_override,
            )
            if _coordinator_observed(observation) != {
                "target": deepcopy(TARGET),
                "topology_sha256": state["topology_sha256"],
                "boot_id_sha256": state["boot_id_sha256"],
                "healthy_android": True,
            }:
                raise LiveRunnerError("fresh pre-intent target or health differs")
            if _selected_serial(observation) != activation["selected_serial_sha256"]:
                raise LiveRunnerError("fresh pre-intent selected serial differs")
            intent_now = int(time.time()) if now is None else now
            current_activation, current_activation_raw = _read_activation(
                static,
                journal,
                now=intent_now,
                require_current=True,
            )
            if (
                current_activation != activation
                or current_activation_raw != activation_raw
            ):
                raise LiveRunnerError("session activation changed during observation")
            store.record_intent(_coordinator_observed(observation), now=intent_now)
            intent_durable = True
            try:
                selected_executor = _default_executor if executor is None else executor
                result = selected_executor(v3)
                intended_state, _ = store._tail()
                observed = _result_observed(
                    v3,
                    result,
                    intended_state,
                    selected_serial_sha256=activation["selected_serial_sha256"],
                )
                store.record_healthy_return(observed, now=intent_now)
            except BaseException as exc:
                try:
                    store.record_uncertain(reason="result_uncertain", now=intent_now)
                finally:
                    _publish_stop(
                        journal,
                        path=RUN_STOP,
                        stage="after-effect-intent",
                        error=exc,
                        intent_durable=intent_durable,
                    )
                raise LiveRunnerError("normal reboot is uncertain-consumed and parked") from exc
            try:
                store.record_close(now=intent_now)
            except BaseException as exc:
                _publish_stop(
                    journal,
                    path=RUN_STOP,
                    stage="after-healthy-return",
                    error=exc,
                    intent_durable=True,
                )
                raise LiveRunnerError(
                    "healthy return is durable; close remains pending without replay"
                ) from exc
            return {
                "status": "HEALTHY_RETURN_CLOSED",
                "replay": False,
                "result_sha256": _sha(canonical(result)),
            }


def reconcile(
    *,
    now: int | None = None,
    result_loader: Callable[[types.ModuleType], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    static = _static()
    _require_live_review(static)
    journal, v3 = _modules(static)
    current = int(time.time()) if now is None else now
    with _lease():
        activation, _raw = _read_activation(
            static,
            journal,
            now=current,
            require_current=False,
        )
        with journal.Journal(JOURNAL_ROOT) as store:
            state, intent = store._tail()
            if (
                state is not None
                and state["phase"] == "OPEN_HEALTHY"
                and intent is None
                and state["d1_effects_used"] == 1
            ):
                return _close_completed_effect(store, now=current)
            return _reconcile_intent(
                journal,
                v3,
                store,
                now=current,
                selected_serial_sha256=activation["selected_serial_sha256"],
                result_loader=result_loader,
            )


def self_test() -> dict[str, Any]:
    static = _static()
    return {
        "schema": SELF_TEST_SCHEMA,
        "review_status": static["binding"]["independent_review"]["status"],
        "target": deepcopy(TARGET),
        "descriptor": deepcopy(static["binding"]["descriptor"]),
        "session_root": static["binding"]["session"]["root"],
        "cli": deepcopy(static["binding"]["cli"]),
        "connected_entries_blocked_until_review": (
            static["binding"]["independent_review"]["status"] != "pass-go"
        ),
        "device_contact": False,
        "activation_created": False,
        "approval_created": False,
        "live_authority": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--prepare-activation", action="store_true")
    group.add_argument("--activate", metavar="APPROVAL")
    group.add_argument("--run-normal-reboot", action="store_true")
    group.add_argument("--reconcile", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            value = self_test()
        elif args.prepare_activation:
            value = prepare_activation()
        elif args.activate is not None:
            value = activate_session(args.activate)
        elif args.run_normal_reboot:
            value = run_normal_reboot()
        else:
            value = reconcile()
    except LiveRunnerError as exc:
        print(f"S22+ pre-F1 normal-reboot runner blocked: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(
            "S22+ pre-F1 normal-reboot runner blocked: host input failure ("
            + type(exc).__name__
            + ")",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
