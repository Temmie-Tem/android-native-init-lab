#!/usr/bin/env python3
"""Exact P2 profile on the complete shared TWRP F1 runtime.

H0 installs the actual candidate observer and recovery-source validator into an
isolated engine before its lease/cage/entrypoint maps are frozen. This file has
one reviewed capability record. Fresh prepared approval remains separate from
capability activation; every effect retains the shared one-shot machinery.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any

import s20plus_g986n_p2_ram_snapshot as codec
import s20plus_g986n_p2_snapshot_observer as observation

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
RUNTIME_PATH = HERE / "s20plus_g986n_twrp_f1_runtime_v2.py"
ENGINE_NORMALIZED_SHA256 = "a65a92fe5612de906a8d2fe5e293987bf578bc80a91d93502276b57958924cf8"
OUTPUT_ROOT = ROOT / "workspace/private/outputs/s20plus_g986n/p2_ram_snapshot_v1"
MANIFEST = OUTPUT_ROOT / "manifest.json"
VERSION = "s20plus-g986n-p2-ram-snapshot-f1-v1"
PLAN_SCHEMA = "s20plus_g986n_p2_ram_snapshot_plan_v1"
P2_F1_ACTIVE = True
RUN_ROOT = ROOT / "workspace/private/runs/s20plus-g986n-p2-ram-snapshot-f1"
CLAIM_ROOT = RUN_ROOT / "consumed-candidates"
ACTIVATION = RUN_ROOT / "activation-v2.json"
ACTIVATION_SCHEMA = "s20plus_g986n_p2_ram_snapshot_activation_v1"
TARGET_CONTRACT = ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
TARGET_SECTION = "## S20+ P2 RAM snapshot attended F1"
PROFILE_ID = "s20plus-g986n-p2-ram-snapshot-v1"
INIT_NAME = "s20plus_p2_pid1_ram_snapshot"
BUILDER_PATH = HERE / "build_s20plus_g986n_p2_ram_snapshot_h0.py"
SOURCE_PATH = ROOT / "workspace/public/src/native-init/s20plus_p2_pid1_ram_snapshot.c"
TARGET = {"model": "SM-G986N", "device": "y2q", "product": "y2qksx", "incremental": "G986NKSS8IYC2"}
EVIDENCE_NAME = "p2-evidence.json"
FAILURE_NAME = "p2-observation-failure.json"
ROLLBACK_IDENTITY_NAME = "p2-rollback-identity.json"
P2_NODES = observation.node_names() | {EVIDENCE_NAME, FAILURE_NAME, ROLLBACK_IDENTITY_NAME}

# Filled from the validated H0 artifacts/source closure. No caller or CLI may
# supply a replacement path/hash. Rebuilds never rewrite consumed artifacts.
SOURCE_PINS = {'workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_f1_runtime_v2.py': {'size': 236445, 'sha256': '366bce9ae70cefb4c3dcdd51aad59ee9bd5ac8cc3fae6524b2994171aed4e4aa'}, 'workspace/public/src/scripts/revalidation/s20plus_g986n_p2_snapshot_observer.py': {'size': 12203, 'sha256': '3e8d5b72ccd502e2e9a25018ded5ff3abd8fa873a4578df2dbff582605f15674'}, 'workspace/public/src/scripts/revalidation/s20plus_g986n_p2_ram_snapshot.py': {'size': 9206, 'sha256': '884fb4072f091b360027c969150800204a4be2399677301f43444e98eecef50c'}, 'workspace/public/src/scripts/revalidation/build_s20plus_g986n_p2_ram_snapshot_h0.py': {'size': 11411, 'sha256': '5aacad83835d630830384a74ff92b6c1ac2f3d7188e661b485923b1ef9b9d08a'}, 'workspace/public/src/native-init/s20plus_p2_pid1_ram_snapshot.c': {'size': 26158, 'sha256': '6e78c6f9971c812c7c19c5de5df8027c46d6b126d0209e9d5cc6ebbbed7dfa67'}, 'workspace/public/src/native-init/s20plus_p2_ram_snapshot_contract.h': {'size': 1353, 'sha256': '35a38b15b03c3b38d7a32917eac4c6b919019abf5b66759a18a6387ae9738002'}, 'workspace/public/src/scripts/revalidation/s20plus_g986n_p1_pid1_witness_evidence.py': {'size': 30982, 'sha256': 'c99f33f99ccc502793f382c74566f8b25bf662c2b76ba2b7b6d0e08d34498308'}}
OUTPUTS = {'AP.tar.md5': {'sha256': '8a3e1d95d9b4d01c4637b3d20f89547f2042122a5cecceba81a8f5d0a7d5d650', 'size': 25845801}, 'boot.img': {'sha256': '0e6198b0fc02e5c726ff6b7a5bfab82f83d49d85302dfd273a1f2e9918e3d629', 'size': 67108864}, 'boot.img.lz4': {'sha256': 'a7d67772981307b2898e57a7249361cec5b6663087024ab78bd27d5c323dd10e', 'size': 25838065}, 's20plus_p2_pid1_ram_snapshot': {'sha256': '549be09f9231cacfde6d2cc5a2e2ac66e21c72edc130ac7b5609674fe6af239b', 'size': 4296}, 's20plus_p2_snapshot_reader': {'sha256': '183dd1600b5f4ecb00899f398011f0e1722a97cd40db70d3772ea1205e45ec79', 'size': 3184}}
MANIFEST_PIN = {'size': 9287, 'sha256': 'b81bb5656ba649d93e472a41d8c8e5602a1b34f4f55e66e04f8fa800dd132ff9'}


class P2F1Error(ValueError):
    pass


_KMSG = codec.kmsg
_MODULE_APIS = tuple((module, name, value) for module in (codec, observation, _KMSG)
                     for name, value in vars(module).items()
                     if inspect.isfunction(value) and value.__module__ == module.__name__)
_COLLECTOR_APIS = tuple((name, value) for name, value in vars(observation.Collector).items()
                        if inspect.isfunction(value))
_COLLECTOR_CLASS = observation.Collector


def _require_module_bindings():
    if (codec.kmsg is not _KMSG or observation.codec is not codec
            or observation.Collector is not _COLLECTOR_CLASS
            or any(getattr(module, name, None) is not value for module, name, value in _MODULE_APIS)
            or any(getattr(_COLLECTOR_CLASS, name, None) is not value for name, value in _COLLECTOR_APIS)):
        raise P2F1Error("P2 observation or parser API was rebound")


def _input_bytes(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 2 * 1024 * 1024:
            raise P2F1Error("indirect or oversized P2 input")
        chunks = []
        left = before.st_size
        while left:
            chunk = os.read(fd, min(left, 65536))
            if not chunk:
                raise P2F1Error("short P2 input")
            chunks.append(chunk); left -= len(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise P2F1Error("P2 input changed during read")
        data = b"".join(chunks)
    finally:
        os.close(fd)
    return data


def _bytes_receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _receipt(path: Path) -> dict[str, Any]:
    return _bytes_receipt(_input_bytes(path))


def _check(path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    value = _receipt(path)
    if value != expected:
        raise P2F1Error("P2 source/artifact identity differs: " + path.name)
    return value


def self_receipt():
    _check(RUNTIME_PATH, SOURCE_PINS[str(RUNTIME_PATH.relative_to(ROOT))])
    data = _input_bytes(Path(__file__))
    normalized, count = re.subn(rb"^P2_F1_ACTIVE = (?:False|True)$",
        b"P2_F1_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>", data, flags=re.M)
    if count != 1:
        raise P2F1Error("P2 activation declaration differs")
    return {"path": str(Path(__file__).resolve()), **_bytes_receipt(data), "normalized_sha256": codec.sha256(normalized)}


def _engine_receipt():
    value = _runtime._direct_receipt(_runtime.ENGINE_PATH, _runtime.ENGINE_SIZE,
                                     _runtime.ENGINE_SHA256, "P2 shared engine")
    if engine.normalized_self_sha256() != ENGINE_NORMALIZED_SHA256:
        raise P2F1Error("P2 shared engine normalized identity differs")
    return {"path": str(_runtime.ENGINE_PATH), **value,
            "normalized_sha256": ENGINE_NORMALIZED_SHA256}


def source_receipts(*, candidate: bool = True):
    _require_module_bindings()
    build_only = {str(BUILDER_PATH.relative_to(ROOT)), str(SOURCE_PATH.relative_to(ROOT))}
    result = {name: _check(ROOT / name, pin) for name, pin in SOURCE_PINS.items()
              if candidate or name not in build_only}
    result["owner"] = self_receipt()
    return result


def declared_source_receipts():
    # The owner pins the original build provenance. Recovery validates current
    # execution code, including the header read by the Python codec, without
    # reopening build-only development inputs or the candidate image.
    source_receipts(candidate=False)
    return {**SOURCE_PINS, "owner": self_receipt()}


def _strict_manifest():
    _check(MANIFEST, MANIFEST_PIN)
    value = json.loads(MANIFEST.read_text(), object_pairs_hook=engine._unique_pairs,
                       parse_constant=engine._reject_constant)
    if (value.get("schema") != "s20plus_g986n_p2_ram_snapshot_build_v1"
            or value.get("profile") != PROFILE_ID or value.get("target") != TARGET
            or value.get("tier") != "H0" or value.get("live_authority") is not False
            or value.get("outputs") != OUTPUTS
            or value.get("evidence_contract", {}).get("declaration") != codec.CONSTANTS):
        raise P2F1Error("P2 manifest contract differs")
    return value


def validate_manifest():
    _strict_manifest()
    return _check(MANIFEST, MANIFEST_PIN)


def _authority_identity():
    common = _input_bytes(ROOT / "AGENTS.md")
    pins = re.findall(rb"The incorporated details have SHA-256:\s*`([0-9a-f]{64})`", common)
    details = _receipt(ROOT / "docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md")
    if len(pins) != 1 or details["sha256"] != pins[0].decode("ascii"):
        raise P2F1Error("common details pin differs")
    target = _input_bytes(TARGET_CONTRACT).decode("utf-8")
    marker = TARGET_SECTION + "\n"
    if target.count(marker) != 1:
        raise P2F1Error("P2 target authority section differs")
    start = target.index(marker)
    end = target.find("\n## ", start + len(marker))
    section = target[start:end if end >= 0 else None].encode()
    return {"common_and_twrp": engine.twrp_baseline.authority_identity(),
            "details": details, "p2_target_section": _bytes_receipt(section),
            "risk_tiers": _receipt(ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md"),
            "process_v2": _receipt(ROOT / "docs/operations/DEVICE_ACTION_PROCESS_V2.md")}


def activation_identity():
    """H0 identity of the capability and its sole allowed activation edit."""
    data = _input_bytes(Path(__file__))
    dormant, count = re.subn(rb"^P2_F1_ACTIVE = (?:False|True)$", b"P2_F1_ACTIVE = False", data, flags=re.M)
    if count != 1:
        raise P2F1Error("P2 activation edit is not unique")
    active = dormant.replace(b"\nP2_F1_ACTIVE = False\n", b"\nP2_F1_ACTIVE = True\n", 1)
    if active == dormant:
        raise P2F1Error("P2 activation edit is absent")
    critical = source_receipts(candidate=False)
    critical.pop("owner")
    return {"schema": ACTIVATION_SCHEMA, "version": VERSION, "target": TARGET,
            "owner_dormant": _bytes_receipt(dormant), "owner_active": _bytes_receipt(active),
            "owner_normalized_sha256": self_receipt()["normalized_sha256"],
            "critical_sources": critical, "declared_candidate_sources": SOURCE_PINS,
            "shared_engine": _engine_receipt(),
            "twrp_baseline": {"checker": _receipt(Path(engine.twrp_baseline.__file__)),
                              "qualification": _receipt(engine.twrp_baseline.REVIEW)},
            "registry_source": _runtime._direct_receipt(_runtime.REGISTRY_PATH,
                _runtime.REGISTRY_SIZE, _runtime.REGISTRY_SHA256, "P2 registry source"),
            "registry_activation": _runtime._direct_receipt(_runtime.REGISTRY_ACTIVATION,
                _runtime.REGISTRY_ACTIVATION_SIZE, _runtime.REGISTRY_ACTIVATION_SHA256, "P2 registry activation"),
            "authority": _authority_identity(), "candidate": OUTPUTS, "manifest": MANIFEST_PIN,
            "rollback": {"ap_sha256": engine.ROLLBACK_AP_SHA256, "boot_sha256": engine.ROLLBACK_BOOT_SHA256},
            "scope": {"candidate_attempt_maximum": 1, "rollback_attempt_maximum": 1,
                "fresh_prepare_required": True, "fresh_exact_approval_required": True,
                "attendance_required": True, "approval_seconds": engine.APPROVAL_LIFETIME_SECONDS,
                "starting_and_terminal_health": "retained_t2_recovery",
                "boot_rollback_required": True, "replay_permitted": False}}


def _require_reviewed_activation():
    value, _ = _runtime._read_private_activation_record(ACTIVATION, ACTIVATION_SCHEMA, "P2 activation")
    expected = activation_identity()
    if (set(value) != {"schema", "version", "target", "identity", "identity_sha256", "review", "at"}
            or value.get("target") != TARGET
            or engine.canonical_bytes(value.get("identity")) != engine.canonical_bytes(expected)
            or value.get("identity_sha256") != engine.digest(expected)
            or engine.canonical_bytes(value.get("review")) != engine.canonical_bytes(
                {"verdict": "PASS_GO", "high": 0, "medium": 0, "low": 0})
            or not isinstance(value.get("at"), str) or not value["at"]
            or _receipt(Path(__file__)) != expected["owner_active"]):
        raise P2F1Error("P2 reviewed activation identity differs")
    return value


def require_active():
    self_receipt()
    _require_module_bindings()
    if P2_F1_ACTIVE is not True:
        raise P2F1Error("STOP_P2_H0_PROFILE_NOT_ACTIVE")
    _runtime._assert_profile_installed()
    if _runtime._profile_read_command_allowed is not _allow_read:
        raise P2F1Error("P2 read fence was rebound")
    _require_reviewed_activation()


def validate_host_closure(*, include_candidate=True, include_rollback=True):
    _runtime._assert_profile_installed()
    closure = _runtime._ENGINE_HOST_VALIDATION_CALL(include_candidate=include_candidate,
                                                   include_rollback=include_rollback)
    closure["p2_profile"] = source_receipts(candidate=include_candidate)
    if P2_F1_ACTIVE:
        closure["p2_activation"] = {"record": _receipt(ACTIVATION),
                                    "identity_sha256": _require_reviewed_activation()["identity_sha256"]}
    return closure


def validate_rollback_closure():
    _runtime._assert_profile_installed()
    value = _runtime._ENGINE_VALIDATE_ROLLBACK_CLOSURE()
    value["p2_profile"] = source_receipts(candidate=False)
    return value


def validate_health_closure():
    _runtime._assert_profile_installed()
    value = _runtime._ENGINE_VALIDATE_HEALTH_CLOSURE()
    value["p2_profile"] = source_receipts(candidate=False)
    return value


def _candidate_transfer(run_dir: Path, prepared: dict[str, Any]):
    result = engine.read_json(run_dir / "candidate-result.json", "P2 transfer")
    engine._validate_transfer_outcome(run_dir, result, "candidate", prepared["binding_sha256"])
    if result.get("classification") != "odin_transfer_completed":
        raise P2F1Error("P2 acquisition requires a proved candidate transfer")
    candidate = prepared["binding"]["closure"]["candidate"]
    if (any(candidate["ap"].get(k) != v for k, v in OUTPUTS["AP.tar.md5"].items())
            or any(candidate["decoded_boot"].get(k) != v for k, v in OUTPUTS["boot.img"].items())):
        raise P2F1Error("P2 prepared candidate differs")
    return {"candidate_result_sha256": engine.digest(result),
            "binding_sha256": prepared["binding_sha256"], "candidate_ap": OUTPUTS["AP.tar.md5"],
            "candidate_boot": OUTPUTS["boot.img"]}


def _allow_read(command, capture_dir, name, kwargs):
    if name not in observation.capture_names():
        return False
    require_active()
    transaction = _runtime._require_live_transaction()
    if transaction["run_dir"] != str(capture_dir):
        raise P2F1Error("P2 read escaped the leased run")
    if not observation.allowed(engine, command, name, kwargs):
        raise P2F1Error("P2 read command or bound differs")
    prepared = engine.read_json(capture_dir / "prepared.json", "P2 prepared")
    intent = engine.read_json(capture_dir / "candidate-observation-intent.json", "P2 observation intent")
    if intent.get("binding_sha256") != prepared["binding_sha256"]:
        raise P2F1Error("P2 read lacks observation ownership")
    if name.startswith("p2-rollback-"):
        source_receipts(candidate=False)
        saved = engine.read_json(capture_dir / "candidate-observation.json", "P2 observation")
        if saved.get("environment") != "resident-android" or saved.get("transport_authorized") is not True:
            raise P2F1Error("P2 rollback source was not qualified")
    else:
        source_receipts()
        _candidate_transfer(capture_dir, prepared)
        if os.path.lexists(capture_dir / "candidate-observation.json"):
            raise P2F1Error("P2 candidate observation is already consumed")
    return True


def _collector(run_dir, prepared, *, replay=None):
    _require_module_bindings()
    return observation.Collector(engine, run_dir, prepared["binding"]["preflight"],
                                 OUTPUTS[codec.READER_NAME]["sha256"], replay=replay)


def _rederive_evidence(run_dir: Path, prepared: dict[str, Any]):
    stored = engine.read_json(run_dir / EVIDENCE_NAME, "P2 evidence")
    if (stored.get("schema") != "s20plus_g986n_p2_evidence_v1"
            or stored.get("sources") != declared_source_receipts()
            or stored.get("sources") != prepared["binding"]["closure"]["p2_profile"]
            or stored.get("transfer") != _candidate_transfer(run_dir, prepared)):
        raise P2F1Error("P2 saved evidence closure differs")
    derived, _ = _collector(run_dir, prepared, replay=stored["collection"]["reads"]).collect()
    if derived != stored["collection"]:
        raise P2F1Error("P2 evidence is not raw-derived")
    return stored, derived


def observe_candidate(run_dir: Path, prepared: dict[str, Any]):
    require_active()
    _runtime._require_live_transaction()
    collector = _collector(run_dir, prepared)
    try:
        sources, transfer = source_receipts(), _candidate_transfer(run_dir, prepared)
        collected, serial = collector.collect()
        value = {"schema": "s20plus_g986n_p2_evidence_v1", "sources": sources,
                 "transfer": transfer, "collection": collected}
        engine.durable_json(run_dir / EVIDENCE_NAME, value)
        saved, derived = _rederive_evidence(run_dir, prepared)
        passed = derived["analysis"]["structural_verdict"] == "MATCH"
        return {"environment": "resident-android", "transport_authorized": True,
            "claim_verdict": "PROVED" if passed else "NO_PROOF",
            "boot_id_sha256": derived["after"]["boot_id_sha256"],
            "p2_evidence_sha256": engine.digest(saved), "at": engine.utc_now()}, serial
    except Exception as error:
        failure = {"schema": "s20plus_g986n_p2_failure_v1", "binding_sha256": prepared["binding_sha256"],
                   "error_type": type(error).__name__, "reason_sha256": codec.sha256(str(error).encode()),
                   "reads": collector.reads, "candidate_replay_permitted": False}
        engine.durable_json(run_dir / FAILURE_NAME, failure)
        return {"environment": "observer-reporting-cut", "transport_authorized": False,
                "claim_verdict": "NO_PROOF", "reason_sha256": engine.digest(failure),
                "at": engine.utc_now()}, None


def validate_candidate_observation(run_dir, value, binding_sha256, initial_boot_id_sha256):
    common = {"schema", "version", "binding_sha256", "candidate_replay_permitted", "environment",
              "transport_authorized", "claim_verdict", "at"}
    if (value.get("schema") != "s20plus_g986n_twrp_v2_candidate_observation_v1"
            or value.get("version") != VERSION or value.get("binding_sha256") != binding_sha256
            or value.get("candidate_replay_permitted") is not False
            or not isinstance(value.get("at"), str) or not value["at"]):
        raise P2F1Error("P2 observation header differs")
    if value.get("environment") == "observer-reporting-cut":
        if value.get("transport_authorized") is not False or value.get("claim_verdict") != "NO_PROOF":
            raise P2F1Error("P2 failed observation grants transport/proof")
        if set(value) == common | {"reason"} and value["reason"] == "observation-intent-consumed-result-absent":
            return
        failure = engine.read_json(run_dir / FAILURE_NAME, "P2 failure")
        if set(value) != common | {"reason_sha256"} or value["reason_sha256"] != engine.digest(failure):
            raise P2F1Error("P2 failed observation differs")
        return
    if set(value) != common | {"boot_id_sha256", "p2_evidence_sha256"} or value.get("environment") != "resident-android":
        raise P2F1Error("P2 observation shape differs")
    prepared = engine.read_json(run_dir / "prepared.json", "P2 prepared")
    stored, collected = _rederive_evidence(run_dir, prepared)
    passed = collected["analysis"]["structural_verdict"] == "MATCH"
    if (value["transport_authorized"] is not True or value["claim_verdict"] != ("PROVED" if passed else "NO_PROOF")
            or value["boot_id_sha256"] != collected["after"]["boot_id_sha256"]
            or value["boot_id_sha256"] == initial_boot_id_sha256
            or value["p2_evidence_sha256"] != engine.digest(stored)):
        raise P2F1Error("P2 observation is not raw-derived")


def revalidate_rollback_source(run_dir, prepared, observed, serial):
    require_active()
    _runtime._require_live_transaction()
    collector = _collector(run_dir, prepared)
    identity, confirmed = collector.identity_once("p2-rollback", require_reader=False)
    if (identity is None or confirmed != serial or identity["boot_id_sha256"] != observed.get("boot_id_sha256")
            or identity["serial_sha256"] != prepared["binding"]["preflight"]["serial_sha256"]):
        raise engine.B0F1Error("P2 rollback source changed")
    value = {"schema": "s20plus_g986n_p2_rollback_identity_v1", "identity": identity,
             "reads": collector.reads, "sources": source_receipts(candidate=False)}
    engine.durable_json(run_dir / ROLLBACK_IDENTITY_NAME, value)
    return {"environment": "resident-android", "serial_sha256": identity["serial_sha256"],
            "topology_sha256": identity["topology_sha256"], "boot_id_sha256": identity["boot_id_sha256"],
            "p2_identity_sha256": engine.digest(value)}


def validate_namespace(run_dir):
    _inherited_namespace(run_dir)
    names = {p.name for p in run_dir.iterdir()}
    if any(n.startswith("p2-") for n in names) and "candidate-observation-intent.json" not in names:
        raise P2F1Error("P2 evidence lacks its observation intent")
    if ROLLBACK_IDENTITY_NAME in names:
        value = engine.read_json(run_dir / ROLLBACK_IDENTITY_NAME, "P2 rollback identity")
        prepared = engine.read_json(run_dir / "prepared.json", "P2 prepared")
        collector = _collector(run_dir, prepared, replay=value["reads"])
        identity, _ = collector.identity_once("p2-rollback", require_reader=False)
        if (value.get("schema") != "s20plus_g986n_p2_rollback_identity_v1" or identity != value.get("identity")
                or value.get("sources") != source_receipts(candidate=False) or collector.reads != value["reads"]):
            raise P2F1Error("P2 rollback identity is not raw-derived")
        if "rollback-download-intent.json" in names:
            intent = engine.read_json(run_dir / "rollback-download-intent.json", "P2 rollback intent")
            expected = {"environment": "resident-android", "serial_sha256": identity["serial_sha256"],
                        "topology_sha256": identity["topology_sha256"], "boot_id_sha256": identity["boot_id_sha256"],
                        "p2_identity_sha256": engine.digest(value)}
            if intent.get("source_receipt") != expected or intent.get("source_boot_id_sha256") != identity["boot_id_sha256"]:
                raise P2F1Error("P2 rollback source receipt differs")


def render_plan():
    return {"schema": PLAN_SCHEMA, "version": VERSION, "target": TARGET,
            "status": "P2_CAPABILITY_ACTIVE" if P2_F1_ACTIVE else "H0_P2_CONFIGURED_NOT_ACTIVATED", "live_authority": False,
            "candidate": OUTPUTS, "candidate_configured": True, "mechanical_activation_defined": True,
            "fresh_prepared_approval_required": True,
            "capture_source": codec.CAPTURE_SOURCE, "starting_and_terminal_health": "retained_t2_recovery",
            "rollback": "proved-boot-restore-then-attended-physical-TWRP-entry", "device_commands": 0}


def _configure_runtime(r):
    global _runtime, engine, _inherited_namespace
    _runtime, engine, _inherited_namespace = r, r.engine, r.validate_namespace
    inherited_values = r._profile_value_replacements
    def profile_values():
        return {**inherited_values(), "EXPECTED_REVIEWED_NORMALIZED_SHA256": ENGINE_NORMALIZED_SHA256}
    r._profile_value_replacements = profile_values
    values = {"VERSION": VERSION, "PLAN_SCHEMA": PLAN_SCHEMA, "RUN_ROOT": RUN_ROOT, "CLAIM_ROOT": CLAIM_ROOT,
        "OUTPUT_ROOT": OUTPUT_ROOT, "CANDIDATE_AP": OUTPUT_ROOT / "AP.tar.md5",
        "CANDIDATE_AP_SIZE": OUTPUTS["AP.tar.md5"]["size"], "CANDIDATE_AP_SHA256": OUTPUTS["AP.tar.md5"]["sha256"],
        "CANDIDATE_MEMBER_SIZE": OUTPUTS["boot.img.lz4"]["size"], "CANDIDATE_MEMBER_SHA256": OUTPUTS["boot.img.lz4"]["sha256"],
        "CANDIDATE_BOOT_SIZE": OUTPUTS["boot.img"]["size"], "CANDIDATE_BOOT_SHA256": OUTPUTS["boot.img"]["sha256"],
        "CANDIDATE_INIT_NAME": INIT_NAME, "CANDIDATE_INIT_SIZE": OUTPUTS[INIT_NAME]["size"],
        "CANDIDATE_INIT_SHA256": OUTPUTS[INIT_NAME]["sha256"], "CANDIDATE_BUILD_SCHEMA": "s20plus_g986n_p2_ram_snapshot_build_v1",
        "MANIFEST": MANIFEST, "MANIFEST_SIZE": MANIFEST_PIN["size"], "MANIFEST_SHA256": MANIFEST_PIN["sha256"],
        "BUILDER_PATH": BUILDER_PATH, "BUILDER_SIZE": SOURCE_PINS[str(BUILDER_PATH.relative_to(ROOT))]["size"],
        "BUILDER_SHA256": SOURCE_PINS[str(BUILDER_PATH.relative_to(ROOT))]["sha256"],
        "INIT_SOURCE_PATH": SOURCE_PATH, "INIT_SOURCE_SIZE": SOURCE_PINS[str(SOURCE_PATH.relative_to(ROOT))]["size"],
        "INIT_SOURCE_SHA256": SOURCE_PINS[str(SOURCE_PATH.relative_to(ROOT))]["sha256"],
        "REGISTRY_MANIFEST_ID": PROFILE_ID, "P0_F1_ACTIVE": False, "TWRP_RUNTIME_CONFIGURED": True,
        "P0_LIVE_ACTIVATION": ACTIVATION,
        "APPROVAL_PREFIX": "S20PLUS-G986N-P2-RAM-SNAPSHOT-F1-APPROVE:",
        "PHYSICAL_CONFIRM_PREFIX": "S20PLUS-G986N-P2-PHYSICAL-ROLLBACK-CONFIRM:",
        "PHYSICAL_REBIND_CONFIRM_PREFIX": "S20PLUS-G986N-P2-PHYSICAL-ROLLBACK-REENUM-CONFIRM:"}
    for name, value in values.items():
        setattr(r, name, value)
    r.P0_RUN_NODE_NAMES |= P2_NODES
    for name, function in {"self_receipt": self_receipt, "_strict_manifest": _strict_manifest,
        "validate_manifest": validate_manifest, "validate_host_closure": validate_host_closure,
        "validate_rollback_closure": validate_rollback_closure, "validate_health_closure": validate_health_closure,
        "require_active": require_active, "_profile_read_command_allowed": _allow_read,
        "observe_candidate": observe_candidate, "validate_candidate_observation": validate_candidate_observation,
        "validate_namespace": validate_namespace, "render_plan": render_plan}.items():
        setattr(r, name, function)
    # Captured by the shared runtime's guarded live map after this hook.
    engine.revalidate_rollback_source = revalidate_rollback_source
    engine.self_receipt = _engine_receipt


def _load_runtime():
    _check(RUNTIME_PATH, SOURCE_PINS[str(RUNTIME_PATH.relative_to(ROOT))])
    name = "_s20plus_g986n_p2_ram_runtime"
    spec = importlib.util.spec_from_file_location(name, RUNTIME_PATH)
    module = importlib.util.module_from_spec(spec)
    module._p2_configure = _configure_runtime
    sys.modules[name] = module
    exec(compile(RUNTIME_PATH.read_bytes(), str(RUNTIME_PATH), "exec"), module.__dict__)
    module._assert_profile_installed()
    return module


_runtime = _load_runtime()
engine = _runtime.engine


def main(argv=None):
    parser = _runtime.build_parser()
    args = parser.parse_args(argv)
    if args.render_plan:
        print(json.dumps(render_plan(), sort_keys=True)); return 0
    if args.validate_host:
        value = validate_host_closure()
        print(json.dumps({"status": "H0_P2_HOST_CLOSURE_PASS", "closure_sha256": engine.digest(value),
                          "live_authority": False, "device_commands": 0}, sort_keys=True)); return 0
    if args.validate_runtime:
        require_active()
        print(json.dumps({"status": "P2_REVIEWED_CAPABILITY_ACTIVE", "live_authority": False,
                          "fresh_prepared_approval_required": True, "device_commands": 0}, sort_keys=True)); return 0
    # A capability activation never substitutes for the prepared approval.
    require_active()
    if args.prepare:
        run_dir = engine.prepare(args.run_dir)
        prepared = _runtime._read_prepared_for_output(run_dir)
        print(json.dumps({"run_dir": str(run_dir), "approval": prepared["approval_token"]})); return 0
    if args.run_dir is None:
        raise P2F1Error("--run-dir is required")
    run_dir = args.run_dir.absolute()
    if args.execute:
        result = engine.execute(run_dir, args.approval or "")
    elif args.resume:
        result = engine.resume_run(run_dir)
    elif args.arm_physical_rollback:
        result = engine.arm_physical_rollback(run_dir)
    elif args.confirm_physical_rollback:
        result = engine.confirm_physical_rollback(run_dir, args.confirmation or "")
    elif args.finalize_resident:
        result = engine.finalize_resident(run_dir)
    elif args.abort_pre_candidate:
        result = engine.abort_pre_candidate(run_dir)
    else:
        raise P2F1Error("no supported P2 operation selected")
    print(json.dumps(result, sort_keys=True)); return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (P2F1Error, engine.B0F1Error, _runtime.P0F1Error) as error:
        print(json.dumps({"status": "STOP_P2_F1", "reason": str(error)}, sort_keys=True))
        raise SystemExit(2)
