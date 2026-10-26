#!/usr/bin/env python3
"""Dormant S20+ P1 PID1 witness profile of the complete P0 F1 runtime.

A fixed pre-install hook specializes the isolated P0 shell before its final
maps and leased entrypoints are built. Its global consumed-candidate registry,
cage journals, guarded dependency graph and recovery state machine are reused,
not replaced with a bare B0 engine. Ordinary P0 imports are unaffected.

No device capability is active. A fresh independent review and mechanical
activation remain necessary. Recovery uses the owner gate, never the kmsg
observation flag, and evidence failure cannot authorize candidate replay.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
from types import FunctionType
from typing import Any

VERSION = "s20plus-g986n-p1-pid1-witness-f1-v1"
PLAN_SCHEMA = "s20plus_g986n_p1_pid1_witness_f1_plan_v1"
JOURNAL_SCHEMA = "s20plus_g986n_p1_pid1_witness_f1_journal_v1"
OBSERVATION_SCHEMA = "s20plus_g986n_b0_candidate_observation_v1"

# No live authority. Rotating this is an activation with its own review record.
P1_F1_ACTIVE = False
EXPECTED_REVIEWED_NORMALIZED_SHA256 = "f591ebe9bbfcf3391def053ce9c1f49174cf15902207227542593c8da69a0536"

ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve()
RUN_ROOT = ROOT / "workspace/private/runs/s20plus-g986n-p1-pid1-witness-f1"
CLAIM_ROOT = RUN_ROOT / "consumed-candidates"
SHARED_GUARD = (
    ROOT / "workspace/private/runs/s20plus-g986n-routine-actions/active-action.json"
)

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "incremental": "G986NKSS8IYC2",
}

APPROVAL_PREFIX = "S20PLUS-G986N-P1-PID1-WITNESS-F1-APPROVE:"
PHYSICAL_CONFIRM_PREFIX = "S20PLUS-G986N-P1-PHYSICAL-ROLLBACK-CONFIRM:"

CAPTURE_NAME = "p1-kmsg-capture.raw"
ATTESTATION_NAME = "p1-kmsg-attestation.json"
OBSERVATION_NAME = "candidate-observation.json"

REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"

ENGINE_PATH = REVALIDATION / "s20plus_g986n_boot_recovery_canary_b0_f1.py"
ENGINE_SIZE = 224_559
ENGINE_SHA256 = "82ec4cee48c3a39aa8dc4de6136e8fda3fbefe88d4821a71bdb0df55d2a17c2a"

SOURCE_PATH = ROOT / "workspace/public/src/native-init/s20plus_p1_pid1_witness_init.c"
SOURCE_SIZE = 23145
SOURCE_SHA256 = "94c1f0d7843758544c0ae268cc36963794c57e3cfff1a42b3a2d8444adab8311"
BUILDER_PATH = REVALIDATION / "build_s20plus_g986n_p1_pid1_witness_h0.py"
BUILDER_SIZE = 26686
BUILDER_SHA256 = "92ba861e5316580903cf26accd259998e68c89925db2ca94b133a9520a402c16"
CONSUMER_PATH = REVALIDATION / "s20plus_g986n_p1_pid1_witness_evidence.py"
CONSUMER_SIZE = 30982
CONSUMER_SHA256 = "c99f33f99ccc502793f382c74566f8b25bf662c2b76ba2b7b6d0e08d34498308"
OBSERVER_PATH = REVALIDATION / "s20plus_g986n_p1_pid1_kmsg_observer.py"
OBSERVER_SIZE = 20959
OBSERVER_SHA256 = "75b0961a09f92f797c0870e149434fb4944a1e274f24a94f47da5bc2d12d7904"

OUTPUT_ROOT = ROOT / "workspace/private/outputs/s20plus_g986n/p1_pid1_witness_v1"
CANDIDATE_AP = OUTPUT_ROOT / "AP.tar.md5"
CANDIDATE_AP_SIZE = 25_845_801
CANDIDATE_AP_SHA256 = "2d80698a6cbcf2690cc4ae9a9ee70934df0f671102645e60f040d525b184e70b"
CANDIDATE_MEMBER_SIZE = 25_834_402
CANDIDATE_MEMBER_SHA256 = "836c6a89b798d6f7f7509446e1bc176f85d5b571fda2b2f971242ae51805bea9"
CANDIDATE_BOOT_SIZE = 67_108_864
CANDIDATE_BOOT_SHA256 = "9e6ce6689d8f36693c83b9a7137bb6df39754b63699c634a8dc1cb71baa3a2cf"
CANDIDATE_INIT_NAME = "s20plus_p1_pid1_witness_init"
CANDIDATE_INIT_SIZE = 1_800
CANDIDATE_INIT_SHA256 = "20c49e008a93f7ff0455384c54b2675c05d2d859a3b497f49dd153ce9edb7c3c"
MANIFEST = OUTPUT_ROOT / "manifest.json"
CANDIDATE_BUILD_SCHEMA = "s20plus_g986n_p1_pid1_witness_build_v1"

# The resident Magisk boot the B0 and P0 owners already use, unchanged. The
# rollback artifact is the one already proved to restore this device; this
# candidate introduces no new recovery path.
ROLLBACK_ROOT = (
    ROOT / "workspace/private/outputs/s20plus_g986n/boot_recovery_canary_b0_v1/rollback"
)
ROLLBACK_AP = ROLLBACK_ROOT / "AP.tar.md5"
ROLLBACK_AP_SIZE = 25_835_561
ROLLBACK_AP_SHA256 = "1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2"
ROLLBACK_MEMBER_SIZE = 25_833_304
ROLLBACK_MEMBER_SHA256 = "2003a3db44c35e0a32b6b485ca0260c7feeab4d9c3031b8cf3ec64f87a8b19b5"
ROLLBACK_BOOT_SIZE = 67_108_864
ROLLBACK_BOOT_SHA256 = "d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc"

EVIDENCE_VERDICTS = ("PROVED", "OBSERVED", "NO_PROOF")
RETURN_STATES = ("android-returned", "android-not-returned", "unknown")
ROLLBACK_STATES = ("completed", "outstanding", "failed")
HEALTH_STATES = ("healthy", "degraded", "unknown")


RUNTIME_PATH = REVALIDATION / "s20plus_g986n_p0_pid1_odin_f1.py"
RUNTIME_SIZE = 236870
RUNTIME_SHA256 = "c9486ec43ad5f0ed6acc2b34436a9d1be7007e9be9d81bbdcd17c2e0d423d6ef"
MANIFEST_SIZE = 8377
MANIFEST_SHA256 = "a218350b04d7075698f2ec124857095303fce18f118f0f7af12473352f3e9032"

REPORT = ROOT / "docs/reports/S20PLUS_G986N_P1_PID1_WITNESS_H0_2026-09-08.md"
CONTRACT_HEADING = "## S20+ P1 PID1 exec-handoff witness F1 candidate"
GOAL_HEADING = "## Current P1 PID1 exec-handoff witness state"
DORMANT_STATUS = "Status: **DEFINED - H0 ONLY - NOT ACTIVE - REVIEW REQUIRED**"
ACTIVE_STATUS = "Status: **ACTIVE - ATTENDED F1 ONLY**"
REMAINING_CLOSURE = [
    "independent review of the exact P1 profile, inherited shell delta, observer, consumer and tests",
    "reviewed mechanical activation and the three P1-specific activation records",
    "fresh exact-target attended prepare and its emitted candidate/rollback approval",
]
P1_NODES = frozenset({
    "p1-kmsg-capture.raw", "p1-kmsg.stderr", "p1-kmsg.capture.json",
    "p1-kmsg-attestation.json", "p1-kmsg-binding.json",
})


class P1F1Error(RuntimeError):
    pass


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_direct(path: Path, maximum: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or not 0 <= before.st_size <= maximum or path.resolve(strict=True) != path.absolute()):
            raise P1F1Error("P1 direct input identity differs")
        data = bytearray()
        while len(data) <= maximum:
            part = os.read(fd, min(65536, maximum + 1 - len(data)))
            if not part:
                break
            data.extend(part)
        after = os.fstat(fd)
        if (len(data) != before.st_size
                or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise P1F1Error("P1 input changed while reading")
        return bytes(data)
    finally:
        os.close(fd)


def _direct_receipt(path: Path, size: int, sha256: str, label: str) -> dict[str, Any]:
    payload = _read_direct(path, size)
    if len(payload) != size or sha256_hex(payload) != sha256:
        raise P1F1Error(f"{label} identity differs")
    return {"path": str(path), "size": size, "sha256": sha256}


def normalized_self_sha256() -> str:
    source = _read_direct(SCRIPT, 128 * 1024)
    for pattern, replacement in (
        (rb"^P1_F1_ACTIVE = (?:False|True)$", b"P1_F1_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>"),
        (rb'^EXPECTED_REVIEWED_NORMALIZED_SHA256 = "[0-9a-f]{64}"$',
         b'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"'),
    ):
        source, count = re.subn(pattern, replacement, source, flags=re.M)
        if count != 1:
            raise P1F1Error("P1 normalization grammar differs")
    return sha256_hex(source)


def self_receipt() -> dict[str, Any]:
    normalized = normalized_self_sha256()
    if normalized != EXPECTED_REVIEWED_NORMALIZED_SHA256:
        raise P1F1Error("P1 owner is outside its bound normalized identity")
    payload = _read_direct(SCRIPT, 128 * 1024)
    return {"path": str(SCRIPT), "size": len(payload), "sha256": sha256_hex(payload),
            "normalized_sha256": normalized}


def _reader_receipt() -> dict[str, Any]:
    """Only the declared Boolean transition is normalized, not arbitrary edits."""
    payload = _read_direct(OBSERVER_PATH, OBSERVER_SIZE)
    dormant, count = re.subn(rb"^OBSERVER_ACTIVE = (?:False|True)$",
                            b"OBSERVER_ACTIVE = False", payload, flags=re.M)
    if count != 1 or len(dormant) != OBSERVER_SIZE or sha256_hex(dormant) != OBSERVER_SHA256:
        raise P1F1Error("P1 reader is outside its bound activation pair")
    return {"path": str(OBSERVER_PATH), "size": len(payload), "sha256": sha256_hex(payload)}


def _reader_normalized_sha256() -> str:
    _reader_receipt()
    source = _read_direct(OBSERVER_PATH, OBSERVER_SIZE)
    source = re.sub(rb"^OBSERVER_ACTIVE = (?:False|True)$",
                    b"OBSERVER_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>", source, flags=re.M)
    return sha256_hex(source)


def _load_source(name: str, path: Path, payload: bytes):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    # Execute the bytes already checked instead of a second path/pycache read.
    exec(compile(payload, str(path), "exec"), module.__dict__)
    return module


_reader = None
_consumer = None
_reader_apis = None
_consumer_apis = None


def _function_identities(module):
    return {name: value for name, value in vars(module).items()
            if isinstance(value, FunctionType) and value.__module__ == module.__name__}


def _assert_apis(module, expected):
    if _function_identities(module) != expected:
        raise P1F1Error("P1 evidence execution API was rebound")


def _load_reader():
    global _reader, _reader_apis
    receipt = _reader_receipt()
    if _reader is None:
        payload = _read_direct(OBSERVER_PATH, OBSERVER_SIZE)
        if sha256_hex(payload) != receipt["sha256"]:
            raise P1F1Error("P1 reader changed during load")
        _reader = _load_source("_s20plus_g986n_p1_kmsg", OBSERVER_PATH, payload)
        _reader_apis = _function_identities(_reader)
    _assert_apis(_reader, _reader_apis)
    return _reader


def _load_consumer():
    global _consumer, _consumer_apis
    _direct_receipt(CONSUMER_PATH, CONSUMER_SIZE, CONSUMER_SHA256, "P1 consumer")
    if _consumer is None:
        _consumer = _load_source("_s20plus_g986n_p1_evidence", CONSUMER_PATH,
                                 _read_direct(CONSUMER_PATH, CONSUMER_SIZE))
        _consumer_apis = _function_identities(_consumer)
    _assert_apis(_consumer, _consumer_apis)
    return _consumer


def _profile_receipts(include_candidate: bool = True) -> dict[str, Any]:
    result = {
        "p1_owner": self_receipt(),
        "p0_runtime": _direct_receipt(RUNTIME_PATH, RUNTIME_SIZE, RUNTIME_SHA256, "P0 runtime"),
        "p0_usb_baseline": _runtime._activation_normalized_observer_receipt()[0],
    }
    if include_candidate:
        result.update({
            "p1_reader": _reader_receipt(),
            "p1_consumer": _direct_receipt(CONSUMER_PATH, CONSUMER_SIZE, CONSUMER_SHA256, "P1 consumer"),
            "p1_source": _direct_receipt(SOURCE_PATH, SOURCE_SIZE, SOURCE_SHA256, "P1 source"),
            "global_registry": _runtime._registry_authority(),
        })
    return result


def _strict_manifest() -> dict[str, Any]:
    _direct_receipt(MANIFEST, MANIFEST_SIZE, MANIFEST_SHA256, "P1 manifest")
    value = json.loads(_read_direct(MANIFEST, MANIFEST_SIZE),
                       object_pairs_hook=engine._unique_pairs, parse_constant=engine._reject_constant)
    outputs = {
        "AP.tar.md5": {"size": CANDIDATE_AP_SIZE, "sha256": CANDIDATE_AP_SHA256},
        "boot.img": {"size": CANDIDATE_BOOT_SIZE, "sha256": CANDIDATE_BOOT_SHA256},
        "boot.img.lz4": {"size": CANDIDATE_MEMBER_SIZE, "sha256": CANDIDATE_MEMBER_SHA256},
        CANDIDATE_INIT_NAME: {"size": CANDIDATE_INIT_SIZE, "sha256": CANDIDATE_INIT_SHA256},
    }
    if (type(value) is not dict or value.get("schema") != CANDIDATE_BUILD_SCHEMA
            or value.get("outputs") != outputs or value.get("target") != TARGET
            or value.get("tier") != "H0" or value.get("live_authority") is not False):
        raise P1F1Error("P1 manifest closure differs")
    # The entire manifest is pinned, including its producer grammar, two-entry
    # ramdisk delta and no-change repack receipt. This is not label-only binding.
    return value


def validate_manifest() -> dict[str, Any]:
    _strict_manifest()
    return _direct_receipt(MANIFEST, MANIFEST_SIZE, MANIFEST_SHA256, "P1 manifest")


def validate_host_closure(*, include_candidate: bool = True, include_rollback: bool = True):
    _runtime._assert_profile_installed()
    closure = _runtime._ENGINE_HOST_VALIDATION_CALL(
        include_candidate=include_candidate, include_rollback=include_rollback)
    closure["p1_profile"] = _profile_receipts(include_candidate)
    if P1_F1_ACTIVE:
        closure["p1_activation"] = _runtime._validate_live_activation()
    return closure


def validate_rollback_closure():
    _runtime._assert_profile_installed()
    closure = _runtime._ENGINE_VALIDATE_ROLLBACK_CLOSURE()
    closure["p1_profile"] = _profile_receipts(False)
    return closure


def validate_health_closure():
    _runtime._assert_profile_installed()
    closure = _runtime._ENGINE_VALIDATE_HEALTH_CLOSURE()
    closure["p1_profile"] = _profile_receipts(False)
    return closure


def require_active() -> None:
    self_receipt()
    _direct_receipt(RUNTIME_PATH, RUNTIME_SIZE, RUNTIME_SHA256, "P0 runtime")
    if P1_F1_ACTIVE is not True:
        raise P1F1Error("STOP_S20PLUS_G986N_P1_PID1_WITNESS_F1_NOT_ACTIVE")
    _runtime._assert_profile_installed()
    if _runtime._profile_read_command_allowed is not _allow_kmsg_read:
        raise P1F1Error("P1 read dispatch was rebound")
    _runtime._validate_live_activation()


def _candidate_require_active() -> None:
    require_active()
    if _load_reader().OBSERVER_ACTIVE is not True:
        raise P1F1Error("STOP_S20PLUS_G986N_P1_PID1_KMSG_OBSERVER_NOT_ACTIVE")
    _load_consumer()


def _candidate_transfer(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    result = engine.read_json(run_dir / "candidate-result.json", "P1 candidate transfer")
    engine._validate_transfer_outcome(run_dir, result, "candidate", prepared["binding_sha256"])
    if result["classification"] != "odin_transfer_completed":
        raise P1F1Error("P1 proof requires a completed candidate transfer")
    closure = prepared["binding"]["closure"]
    if (closure["candidate"]["ap"]["sha256"] != CANDIDATE_AP_SHA256
            or closure["candidate"]["decoded_boot"]["sha256"] != CANDIDATE_BOOT_SHA256):
        raise P1F1Error("P1 transferred candidate differs")
    return {"candidate_result_sha256": engine.digest(result),
            "binding_sha256": prepared["binding_sha256"],
            "candidate_ap_sha256": CANDIDATE_AP_SHA256,
            "candidate_boot_sha256": CANDIDATE_BOOT_SHA256}


def _allow_kmsg_read(command, capture_dir, name, kwargs) -> bool:
    if name != "p1-kmsg":
        return False
    _candidate_require_active()
    transaction = _runtime._require_live_transaction()
    if transaction["run_dir"] != str(capture_dir):
        raise P1F1Error("P1 capture escaped its leased run")
    reader = _load_reader()
    if command[3:] != ["shell", "su", "-c", engine.shlex.quote(reader.READ_SCRIPT)] or kwargs != reader.CAPTURE_KWARGS:
        raise P1F1Error("P1 capture differs from its fixed read and limits")
    prepared = engine.read_json(capture_dir / "prepared.json", "P1 prepared")
    _candidate_transfer(capture_dir, prepared)
    intent = engine.read_json(capture_dir / "candidate-observation-intent.json", "P1 observation intent")
    if intent.get("binding_sha256") != prepared["binding_sha256"]:
        raise P1F1Error("P1 capture lacks its bound observation intent")
    return True


def _failed_observation(reason: str) -> dict[str, Any]:
    return {"environment": "observer-reporting-cut", "transport_authorized": False,
            "claim_verdict": "NO_PROOF", "reason": reason, "at": engine.utc_now()}


def _evidence_receipt(run_dir: Path, prepared: dict[str, Any], health: dict[str, Any]):
    reader, consumer = _load_reader(), _load_consumer()
    transferred = _candidate_transfer(run_dir, prepared)
    binding = engine.read_json(run_dir / reader.BINDING_NAME, "P1 acquisition binding")
    if (set(binding) != {"schema", "serial_sha256", "topology_sha256", "boot_id_sha256",
                         "snapshot_sha256", "pre_post_identical", "candidate_boot_sha256", "candidate_ap_sha256"}
            or binding["schema"] != "s20plus_g986n_p1_kmsg_binding_v1"
            or binding["pre_post_identical"] is not True
            or re.fullmatch(r"[0-9a-f]{64}", str(binding["snapshot_sha256"])) is None
            or any(binding[key] != health[key] for key in ("serial_sha256", "topology_sha256", "boot_id_sha256"))
            or binding["boot_id_sha256"] == prepared["binding"]["preflight"]["boot_id_sha256"]
            or binding["candidate_ap_sha256"] != CANDIDATE_AP_SHA256
            or binding["candidate_boot_sha256"] != CANDIDATE_BOOT_SHA256):
        raise P1F1Error("P1 acquisition binding is not the observed candidate boot")
    acquisition = reader.read_acquisition(engine, run_dir)
    attestation_path = run_dir / reader.ATTESTATION_NAME
    attestation = consumer.parse_attestation(_read_direct(attestation_path, 16384))
    if (attestation["acquisition_status"] != acquisition["status"]
            or sha256_hex(attestation["boot_id"].encode()) != binding["boot_id_sha256"]):
        raise P1F1Error("P1 attestation differs from acquired evidence")
    result = consumer.validate(run_dir / reader.CAPTURE_NAME, attestation_path)
    receipt = {**transferred,
        "binding_receipt_sha256": engine.digest(binding),
        "acquisition_receipt_sha256": sha256_hex(_read_direct(run_dir / (reader.CAPTURE_LABEL + ".capture.json"), 16384)),
        "attestation_sha256": sha256_hex(_read_direct(attestation_path, 16384)),
        "raw_sha256": sha256_hex(acquisition["raw"]), "raw_size": len(acquisition["raw"]),
        "consumer_verdict": result["verdict"], "consumer_result_sha256": engine.digest(result),
    }
    return result, receipt


def observe_candidate(run_dir: Path, prepared: dict[str, Any]):
    require_active()
    _runtime._require_live_transaction()
    try:
        # Reuse exact Android/recovery/Download arrival and root-health handling.
        # This preserves a qualified serial for the engine's mandatory rollback.
        observation, serial = _runtime._ENGINE_OBSERVE_CANDIDATE(run_dir, prepared)
    except Exception as error:
        return _failed_observation("arrival-failed-" + type(error).__name__), None
    if observation.get("environment") == "recovery-adb":
        # Recovery's B0 canary verdict belongs to that different producer. Do
        # not relabel it as P1 evidence: retain its raw probes, require physical
        # recovery, and use the existing recovery-only reporting-cut grammar.
        return _failed_observation("unexpected-recovery-adb"), None
    observation["claim_verdict"] = "NO_PROOF"
    if observation.get("environment") != "resident-android" or serial is None:
        return observation, serial
    try:
        _candidate_require_active()
        _candidate_transfer(run_dir, prepared)
        reader, consumer = _load_reader(), _load_consumer()
        acquired = reader.observe(
            engine, out_dir=run_dir, expected=prepared["binding"]["preflight"],
            candidate_id=consumer.CANDIDATE_ID,
            candidate_boot_sha256=CANDIDATE_BOOT_SHA256,
            candidate_ap_sha256=CANDIDATE_AP_SHA256,
            candidate_boot_id_sha256=observation["resident_health"]["boot_id_sha256"],
        )
        if acquired["serial"] != serial:
            raise P1F1Error("P1 capture selected another serial")
        result, receipt = _evidence_receipt(run_dir, prepared, observation["resident_health"])
        # An acquisition error is an unexplained session outcome, even when a
        # prefix happened to contain a witness. Only attended recovery follows.
        if acquired["acquisition"]["status"] == reader.STATUS_FAILED:
            return _failed_observation("capture-acquisition-failed"), None
        observation["p1_evidence"] = receipt
        observation["claim_verdict"] = "PROVED" if result["verdict"] == "PROVED" else "NO_PROOF"
        return observation, serial
    except Exception as error:
        # Raw files and journals remain untouched. No acquisition is retried;
        # the inherited resume path handles an observation/reporting cut.
        return _failed_observation("capture-failed-" + type(error).__name__), None


def validate_candidate_observation(run_dir, value, binding_sha256, initial_boot_id_sha256):
    _runtime._ENGINE_VALIDATE_CANDIDATE_OBSERVATION(
        run_dir, value, binding_sha256, initial_boot_id_sha256)
    if "p1_evidence" not in value:
        if value.get("claim_verdict") != "NO_PROOF":
            raise P1F1Error("only a rederived P1 witness may prove PID1")
        return
    if value.get("environment") != "resident-android":
        raise P1F1Error("P1 proof requires qualified same-boot Android")
    prepared = engine.read_json(run_dir / "prepared.json", "P1 prepared")
    result, receipt = _evidence_receipt(run_dir, prepared, value["resident_health"])
    expected = "PROVED" if result["verdict"] == "PROVED" else "NO_PROOF"
    if value["p1_evidence"] != receipt or value.get("claim_verdict") != expected:
        raise P1F1Error("P1 observation is not raw-derived")


def validate_namespace(run_dir: Path) -> None:
    _inherited_namespace(run_dir)
    names = {entry.name for entry in os.scandir(run_dir)}
    present = names & P1_NODES
    if present and "candidate-observation-intent.json" not in names:
        raise P1F1Error("P1 capture lacks its observation intent")
    # Stream-only/reporting cuts must remain recoverable. Full attestation and
    # raw re-derivation are mandatory only when a result makes a positive claim.
    if "p1-kmsg-attestation.json" in names and not {
        "p1-kmsg.capture.json", "p1-kmsg-capture.raw", "p1-kmsg.stderr", "p1-kmsg-binding.json"
    } <= names:
        raise P1F1Error("P1 attestation lacks its raw acquisition chain")


def derive_terminal_verdict(candidate_classification, claim_verdict, rollback_completed):
    passed = (candidate_classification == "odin_transfer_completed"
              and claim_verdict == "PROVED" and rollback_completed is True)
    return ("PROVED_P1_PID1_WITNESS_RETURNED_RESIDENT_HEALTHY" if passed
            else "NO_PROOF_P1_PID1_WITNESS_RETURNED_RESIDENT_HEALTHY", passed)


def _declared_profile_sources():
    # Candidate inputs are checked by validate_host_closure before prepare and
    # transfer. Frozen expected receipts keep rollback independent of discarded
    # candidate payloads/build inputs after consumption.
    return {
        label: {"path": str(path), "size": size, "sha256": digest}
        for label, path, size, digest in (
            ("runtime", RUNTIME_PATH, RUNTIME_SIZE, RUNTIME_SHA256),
            ("producer", SOURCE_PATH, SOURCE_SIZE, SOURCE_SHA256),
            ("builder", BUILDER_PATH, BUILDER_SIZE, BUILDER_SHA256),
            ("consumer", CONSUMER_PATH, CONSUMER_SIZE, CONSUMER_SHA256),
            ("manifest", MANIFEST, MANIFEST_SIZE, MANIFEST_SHA256),
        )
    }


def _document_semantics(documents=None):
    r = _runtime
    if documents is None:
        documents = {name: r.P0_POLICY_FILES[name].read_text("utf-8")
                     for name in r.P0_DORMANT_DOCUMENT_SEMANTICS}
    return {
        "repository_contract": r._registry_process_cell(documents["repository_contract"]),
        "target_contract": r._section_status(documents["target_contract"], CONTRACT_HEADING, "P1 contract"),
        "current_goal": r._section_status(documents["current_goal"], GOAL_HEADING, "P1 goal"),
        "qualification_report": _report_status(documents["qualification_report"]),
    }


def _report_status(text):
    lines = _runtime._semantic_markdown_lines(text, "P1 report")
    end = next((i for i, line in enumerate(lines) if line.startswith("## ")), len(lines))
    fields = [line for line in lines[:end] if line]
    if (len(fields) != 3
            or fields[0] != "# S20+ P1 PID1 witness: H0 acquisition and F1 integration"
            or fields[1] != "Tier: H0 only" or not fields[2].startswith("Status: ")):
        raise P1F1Error("P1 report preamble differs")
    return fields[2]


def _activation_marker(name, status):
    r = _runtime
    if name == "repository_contract":
        marker = f"| {r.P0_REGISTRY_TARGET_CELL} | {r.P0_REGISTRY_GOAL_CELL} | {r.P0_REGISTRY_CONTRACT_CELL} | {status} |"
    elif name == "target_contract":
        marker = f"\n{CONTRACT_HEADING}\n\n{status}\n"
    elif name == "current_goal":
        marker = f"\n{GOAL_HEADING}\n\n{status}\n"
    elif name == "qualification_report":
        marker = f"\nTier: H0 only\n\n{status}\n\n## Outcome\n"
    else:
        raise P1F1Error("P1 activation document is not declared")
    return marker, marker.replace(status, "<P1_REVIEWED_ACTIVATION_STATUS>")


def _reviewed_closure_current():
    r = _runtime
    return {
        "owner": self_receipt(), "owner_normalized_sha256": normalized_self_sha256(),
        "observer": _reader_receipt(), "observer_normalized_sha256": _reader_normalized_sha256(),
        "engine": r._direct_receipt(ENGINE_PATH, ENGINE_SIZE, ENGINE_SHA256, "P1 B0 engine"),
        "registry_source": r._direct_receipt(r.REGISTRY_PATH, r.REGISTRY_SIZE, r.REGISTRY_SHA256, "registry"),
        "registry_activation": r._direct_receipt(r.REGISTRY_ACTIVATION, r.REGISTRY_ACTIVATION_SIZE,
                                                  r.REGISTRY_ACTIVATION_SHA256, "registry activation"),
        "policy": {name: r._current_file_receipt(path, name) for name, path in sorted(r.P0_POLICY_FILES.items())},
        "tests": {name: r._current_file_receipt(path, name) for name, path in sorted(r.P0_TEST_FILES.items())},
        "activation_document_semantics": _document_semantics(),
        "activation_documents_normalized": r._activation_document_normalized_receipts(),
        "profile_sources": _declared_profile_sources(),
    }


def _validate_zero_review():
    value, receipt = _inherited_zero_review()
    if value["reviewed_closure"].get("profile_sources") != _declared_profile_sources():
        raise P1F1Error("P1 reviewed profile source closure drifted")
    return value, receipt


def _live_activation_expected():
    expected = _inherited_live_expected()
    # The baseline-only USB reader stays dormant. The mechanical observation
    # activation belongs to the kmsg reader and does not activate the old ACM.
    expected["closure"]["observer"] = _reader_receipt()
    expected["closure"]["profile_sources"] = _declared_profile_sources()
    expected["closure_sha256"] = engine.digest(expected["closure"])
    return expected


def _configure_review_metadata(r):
    r.P0_LIVE_ACTIVATION = RUN_ROOT / "live-activation-v1.json"
    r.P0_ZERO_FINDING_REVIEW = RUN_ROOT / "zero-finding-review-v1.json"
    r.P0_MECHANICAL_ACTIVATION = RUN_ROOT / "mechanical-activation-v1.json"
    r.P0_REVIEW_TEST_LOG_ROOT = RUN_ROOT / "review-tests-v1"
    r.P0_ACTIVE_REVIEW_TEST_LOG_ROOT = RUN_ROOT / "active-review-tests-v1"
    for name in ("P0_LIVE_ACTIVATION_SCHEMA", "P0_ZERO_FINDING_REVIEW_SCHEMA",
                 "P0_MECHANICAL_ACTIVATION_SCHEMA", "P0_REVIEW_TEST_RESULTS_SCHEMA"):
        setattr(r, name, getattr(r, name).replace("p0_pid1_odin", "p1_pid1_witness"))
    r.P0_POLICY_FILES = {
        "repository_contract": ROOT / "AGENTS.md",
        "target_contract": ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md",
        "risk_tiers": ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md",
        "process_v2": ROOT / "docs/operations/DEVICE_ACTION_PROCESS_V2.md",
        "current_goal": ROOT / "GOAL_S20PLUS.md", "qualification_report": REPORT,
    }
    r.P0_TEST_FILES = {
        "p1_witness": ROOT / "tests/test_s20plus_g986n_p1_pid1_witness_v1.py",
        "p1_integration": ROOT / "tests/test_s20plus_g986n_p1_pid1_integration.py",
        "p0_owner": ROOT / "tests/test_s20plus_g986n_p0_pid1_odin_f1.py",
        "p0_observer": ROOT / "tests/test_s20plus_g986n_p0_pid1_usb_observer.py",
    }
    r.P0_REVIEW_TEST_REQUIREMENTS = {
        "focused_observer": {"modules": ["tests.test_s20plus_g986n_p1_pid1_witness_v1"],
                             "tests": 88, "skipped": 0, "log_name": "focused-observer.log"},
        "focused_owner": {"modules": ["tests.test_s20plus_g986n_p1_pid1_integration"],
                          "tests": 28, "skipped": 0, "log_name": "focused-owner.log"},
        "wider": {"modules": ["tests.test_s20plus_g986n_p0_pid1_odin_f1",
                              "tests.test_s20plus_g986n_p0_pid1_usb_observer"],
                  "tests": 95, "skipped": 0, "log_name": "wider.log"},
    }
    r.P0_ACTIVE_REGISTRY_MARKER = "reviewed attended P1 PID1 witness F1 active"
    r.P0_ACTIVE_REGISTRY_PROCESS_CELL = r.P0_DORMANT_REGISTRY_PROCESS_CELL + "; " + r.P0_ACTIVE_REGISTRY_MARKER
    r.P0_DORMANT_CONTRACT_MARKER = DORMANT_STATUS
    r.P0_ACTIVE_CONTRACT_MARKER = ACTIVE_STATUS
    r.P0_DORMANT_GOAL_MARKER = "Status: `P1_PID1_WITNESS_H0_CORRECTED_NOT_ACTIVE_REVIEW_REQUIRED`"
    r.P0_ACTIVE_GOAL_MARKER = "Status: `P1_PID1_WITNESS_ACTIVE_ATTENDED`"
    r.P0_DORMANT_DOCUMENT_SEMANTICS = {
        "repository_contract": r.P0_DORMANT_REGISTRY_PROCESS_CELL,
        "target_contract": DORMANT_STATUS, "current_goal": r.P0_DORMANT_GOAL_MARKER,
        "qualification_report": r.P0_DORMANT_REPORT_MARKER,
    }
    r.P0_ACTIVE_DOCUMENT_SEMANTICS = {
        "repository_contract": r.P0_ACTIVE_REGISTRY_PROCESS_CELL,
        "target_contract": ACTIVE_STATUS, "current_goal": r.P0_ACTIVE_GOAL_MARKER,
        "qualification_report": r.P0_ACTIVE_REPORT_MARKER,
    }
    r.P0_ACTIVATION_CHANGE_FILES = {
        "owner": SCRIPT, "observer": OBSERVER_PATH,
        **{name: r.P0_POLICY_FILES[name] for name in r.P0_DORMANT_DOCUMENT_SEMANTICS},
    }
    r.P0_ACTIVATION_CHANGE_RULES = {
        "owner": {"before": "P1_F1_ACTIVE = False", "after": "P1_F1_ACTIVE = True"},
        "observer": {"before": "OBSERVER_ACTIVE = False", "after": "OBSERVER_ACTIVE = True"},
        **{name: {"before": value, "after": r.P0_ACTIVE_DOCUMENT_SEMANTICS[name]}
           for name, value in r.P0_DORMANT_DOCUMENT_SEMANTICS.items()},
    }


def _configure_runtime(r):
    """Fixed P1-only hook, called before the inherited final maps are built."""
    global _runtime, engine, _inherited_namespace, _inherited_zero_review, _inherited_live_expected
    _runtime, engine = r, r.engine
    _inherited_namespace = r.validate_namespace
    _inherited_zero_review = r._validate_zero_finding_review
    _inherited_live_expected = r._live_activation_expected
    for name in (
        "VERSION", "PLAN_SCHEMA", "RUN_ROOT", "CLAIM_ROOT", "SHARED_GUARD", "OUTPUT_ROOT",
        "CANDIDATE_AP", "CANDIDATE_AP_SIZE", "CANDIDATE_AP_SHA256", "CANDIDATE_MEMBER_SIZE",
        "CANDIDATE_MEMBER_SHA256", "CANDIDATE_BOOT_SIZE", "CANDIDATE_BOOT_SHA256",
        "CANDIDATE_INIT_NAME", "CANDIDATE_INIT_SIZE", "CANDIDATE_INIT_SHA256", "CANDIDATE_BUILD_SCHEMA",
        "MANIFEST", "MANIFEST_SIZE", "MANIFEST_SHA256", "BUILDER_PATH", "BUILDER_SIZE", "BUILDER_SHA256",
        "APPROVAL_PREFIX", "PHYSICAL_CONFIRM_PREFIX",
    ):
        setattr(r, name, globals()[name])
    r.PHYSICAL_REBIND_CONFIRM_PREFIX = "S20PLUS-G986N-P1-PHYSICAL-ROLLBACK-REENUM-CONFIRM:"
    r.REGISTRY_MANIFEST_ID = "s20plus-g986n-p1-pid1-witness-v1"
    r.P0_F1_ACTIVE = P1_F1_ACTIVE
    r.INIT_SOURCE_PATH, r.INIT_SOURCE_SIZE, r.INIT_SOURCE_SHA256 = SOURCE_PATH, SOURCE_SIZE, SOURCE_SHA256
    r.P0_RUN_NODE_NAMES = r.P0_RUN_NODE_NAMES | P1_NODES
    for name, function in {
        "self_receipt": self_receipt, "normalized_self_sha256": normalized_self_sha256,
        "_strict_manifest": _strict_manifest, "validate_manifest": validate_manifest,
        "validate_host_closure": validate_host_closure, "validate_rollback_closure": validate_rollback_closure,
        "validate_health_closure": validate_health_closure, "require_active": require_active,
        "_profile_read_command_allowed": _allow_kmsg_read, "observe_candidate": observe_candidate,
        "validate_candidate_observation": validate_candidate_observation, "validate_namespace": validate_namespace,
        "derive_terminal_verdict": derive_terminal_verdict, "render_plan": render_plan,
        "_current_document_semantics": _document_semantics, "_activation_marker": _activation_marker,
        "_reviewed_closure_current": _reviewed_closure_current, "_validate_zero_finding_review": _validate_zero_review,
        "_normalized_observer_sha256": _reader_normalized_sha256, "_live_activation_expected": _live_activation_expected,
    }.items():
        setattr(r, name, function)
    _configure_review_metadata(r)


def render_plan():
    return {
        "schema": PLAN_SCHEMA, "version": VERSION, "target": TARGET, "tier": "F1",
        "p1_f1_active": P1_F1_ACTIVE, "live_authority": False,
        "profile_installed": bool(_runtime.PROFILE_INSTALLED), "device_commands": 0,
        "candidate": {"ap_sha256": CANDIDATE_AP_SHA256, "boot_sha256": CANDIDATE_BOOT_SHA256},
        "rollback": {"ap_sha256": ROLLBACK_AP_SHA256, "mandatory": True},
        "global_registry_reused": True, "session_lease_reused": True, "process_cage_reused": True,
        "remaining_closure": list(REMAINING_CLOSURE),
    }


def _load_runtime():
    _direct_receipt(RUNTIME_PATH, RUNTIME_SIZE, RUNTIME_SHA256, "P0 runtime")
    name = "_s20plus_g986n_p1_pid1_runtime"
    spec = importlib.util.spec_from_file_location(name, RUNTIME_PATH)
    module = importlib.util.module_from_spec(spec)
    module._p1_configure = _configure_runtime
    sys.modules[name] = module
    exec(compile(_read_direct(RUNTIME_PATH, RUNTIME_SIZE), str(RUNTIME_PATH), "exec"), module.__dict__)
    module._assert_profile_installed()
    return module


if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))
_runtime = _load_runtime()
engine = _runtime.engine


def main(argv=None) -> int:
    args = _runtime.build_parser().parse_args(argv)
    try:
        if args.render_plan:
            print(json.dumps(render_plan(), sort_keys=True))
            return 0
        if args.validate_host:
            closure = validate_host_closure()
            print(json.dumps({"schema": PLAN_SCHEMA, "verdict": "PASS_P1_HOST_CLOSURE_ONLY",
                              "closure_sha256": engine.digest(closure), "live_authority": False}, sort_keys=True))
            return 0
        require_active()
        if args.prepare or args.execute:
            _candidate_require_active()
        if args.prepare:
            run_dir = engine.prepare(args.run_dir)
            prepared = _runtime._read_prepared_for_output(run_dir)
            print(f"run_dir={run_dir}")
            print(f"approval={prepared['approval_token']}")
            return 0
        if args.run_dir is None:
            raise P1F1Error("--run-dir is required")
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
        else:
            result = engine.abort_pre_candidate(run_dir)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"schema": PLAN_SCHEMA, "verdict": "STOP_P1_F1",
                          "failure_class": type(error).__name__, "live_authority": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
