#!/usr/bin/env python3
"""Publish the exact P3.34 result from its already-CLOSED retained run.

The device action already completed one candidate transfer, one exact Magisk
rollback, final Android/root health collection, and two stable rollback
observer reads.  The live process stopped after those reads because the P3.34
adapter's missing-return-receipt exception escaped the existing supplemental
parser-failure branch.  A reviewed first host-only invocation reconstructed
that evidence and appended HEALTH_VERIFIED, the two closing events, and CLOSED;
the same validator exception then stopped before ``live-result.json`` was
published.  This resumed exact-run finalizer performs no device I/O, cannot
transfer either artifact, does not change the CLOSED journal or state, and
publishes only the missing canonical result through the pinned result writer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent
MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p334_process_v2_ready_1.json"
)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "p334-ready1-prepared-20260904-1"
)
STATE_PATH = RUN_DIR / "live-state.json"
RESULT_PATH = RUN_DIR / "live-result.json"

SCHEMA = "s22plus_fyg8_p334_postrollback_finalizer_v1"
AUDIT_VERDICT = "PASS_P334_POSTROLLBACK_FINALIZER_AUDIT_HOST_ONLY"
PUBLISH_VERDICT = "PASS_P334_POSTROLLBACK_FINALIZED_HOST_ONLY"
EXPECTED_BINDING = (
    "2a22b00c4bd5d17dc1c464275d3f59bda430d2f79de0e3ac61743c95359952eb"
)
EXPECTED_BUNDLE = (
    "b9d1df221d953a22ef745beeea99ede945fc3f8fe2fa5321946f04360510c583"
)
EXPECTED_CLOSED_STATE = (
    13_105,
    "ebfc0e3a908ddd8b0966ded809a711d76d37e88bff916e95c348773321250ff5",
)
EXPECTED_CLOSED_HEAD = (
    276,
    "60f4262dd704ca7f400708f98cbb59184d88b2bffeb00a52b8b7cae1a573eba3",
)
EXPECTED_TERMINAL_RECORD_SHA256 = (
    "bbb939241a54f9b9c343cf0c4c3c50e89b5fe2bb9a95bc126280752b8d7f04ca"
)
EXPECTED_RESULT_VERDICT = (
    "PASS_F1_V2_P334_AUTHENTICATED_LOGICAL_RESIDENT_"
    "FIRST_CONSOLE_RETURN_AND_ROLLED_BACK"
)
EXPECTED_OUTCOME = (
    "p334_authenticated_logical_resident_first_console_return_"
    "rollback_verified"
)
EXPECTED_RESULT = (
    15_807,
    "91ba8a7e0642155c0a2bf5a111beff32854fabe673866e434413c486b9bb63ed",
)
EXPECTED_PARSER_ERROR = "P3.34 first-console return record is not exact"

EXACT_FILES = {
    "manifest": (
        MANIFEST,
        7_580,
        "a662083e264c1784cf8782153eb918816207e4ad42135bfe9cf57480c93225c5",
    ),
    "live_source": (
        REVALIDATION / "device_action_f1_live_v2.py",
        502_612,
        "a4b0a8fe7434a7b5a4330c94b26c09693b7ec6b49521b45f2ade69c3075207c8",
    ),
    "core_source": (
        REVALIDATION / "device_action_f1_v2.py",
        136_809,
        "3902e1a887530e590e0a8f10f3d6fda1c1affea2283873b40682b0f1576a3a33",
    ),
    "evidence_source": (
        REVALIDATION / "device_action_f1_evidence_v2.py",
        639_038,
        "8b771a2bd5b3f1c60db04dc9d91d4f4bb4318c47a050b7630c97a768da7a1706",
    ),
    "prepared": (
        RUN_DIR / "prepared.json",
        21_499,
        "16096c7490a2d918ea330c76dec2950cfa2a7c156f9e3102ed7439cc5568db05",
    ),
    "target": (
        RUN_DIR / "target-private.json",
        107,
        "94a7c1e84513f2b6e59fc2a2cc6bff0de390c42d56f155f0a34c05e3dbfd3aab",
    ),
    "candidate_result": (
        RUN_DIR / "candidate-attempt-01.result.json",
        2_079,
        "f24853bf05ec7403d6f64793a26739c4b3ab8c31a42944d65354b4daf0fe8302",
    ),
    "rollback_result": (
        RUN_DIR / "rollback-attempt-01.result.json",
        2_030,
        "d5e284c9331beac7917145e203521787fc4b73032576602e138412025b0b4df2",
    ),
    "candidate_observer": (
        RUN_DIR / "candidate-observer.json",
        15_385,
        "811d8c0340b4058c7e5f5ecaa0fb5ef629dd96179c2f12a5bf10a61c5e25d28d",
    ),
    "candidate_raw": (
        RUN_DIR / "candidate-observer.raw",
        1_162,
        "06a1cdcfd547d652bc6cb76745599e61ad280933c82c8ad8f340e4f28eae80a8",
    ),
    "odin_snapshots": (
        RUN_DIR / "odin-endpoints/transaction.jsonl",
        24_768,
        "543c6fc0d250005c0c8e294e498436f5195bc240b0f29f388a3f4a4cc0e69f50",
    ),
    "rollback_capture_1": (
        RUN_DIR / "0023-observer-eof.capture.json",
        510,
        "395a275a9ebbf1cc19aa68548d176962978c236853fa0959b8955088bd4566bc",
    ),
    "rollback_capture_2": (
        RUN_DIR / "0024-observer-eof.capture.json",
        510,
        "0e7122148a02476f12e2681531b16a9c26aca241f23897c68746bb48747c472e",
    ),
    "rollback_raw_1": (
        RUN_DIR / "rollback-observer-1.bin",
        2_097_136,
        "3492285992bacda0d82494093433dcfa42c56142191d97389fdab9dfa0eebc3e",
    ),
    "rollback_raw_2": (
        RUN_DIR / "rollback-observer-2.bin",
        2_097_136,
        "3492285992bacda0d82494093433dcfa42c56142191d97389fdab9dfa0eebc3e",
    ),
    "final_properties_capture": (
        RUN_DIR / "raw-adb/0021-adb-read-only-shell.capture.json",
        530,
        "33adb678659cd7f54b5457cf1d0335ad03c869fb48ccbeb809ccbd7e2e18f70d",
    ),
    "final_properties": (
        RUN_DIR / "raw-adb/0021-adb-read-only-shell.stdout.bin",
        244,
        "359dfb1d649bbcc43a0823f595a3cff8e7a3987166cda8b45838ce779686864d",
    ),
    "final_root_capture": (
        RUN_DIR / "raw-adb/0022-adb-read-only-shell.capture.json",
        531,
        "6ef338aaf317411cd95fac70389bde6327047300bb7c66afac84cae9ec0b2eb8",
    ),
    "final_root": (
        RUN_DIR / "raw-adb/0022-adb-read-only-shell.stdout.bin",
        357,
        "4fe0ce0251960752c8617d0244391fabf87f1bd3aeea472c9f90464bc9e81a2a",
    ),
    "final_inventory_capture": (
        RUN_DIR / "raw-adb/0025-adb-devices.capture.json",
        505,
        "57a32a767838f950c5cc335f0d3606af72a7a4503123ece5633d14a0c961bf0e",
    ),
    "final_inventory": (
        RUN_DIR / "raw-adb/0025-adb-devices.stdout.bin",
        216,
        "02ce835c508f19a787f93b62e00ffe825696ac7a1d77a74a6cbc1c1ab4874452",
    ),
    "final_topology_capture": (
        RUN_DIR / "raw-adb/0026-adb-get-devpath.capture.json",
        516,
        "3e7547974f26a03a90f852f3496c7a062e4cfea56a59a43e583281bc76a0ff5c",
    ),
    "final_topology": (
        RUN_DIR / "raw-adb/0026-adb-get-devpath.stdout.bin",
        10,
        "f3612060719188ec47f87d280accf80e8ef2237272c78aa7c79bacb9606751cc",
    ),
}


class FinalizerError(RuntimeError):
    """The exact consumed P3.34 run cannot be closed from retained evidence."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"


def _stable(path: Path, label: str, maximum: int = 4 * 1024 * 1024) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        descriptor = os.open(direct, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            inside = os.fstat(descriptor)
            payload = bytearray()
            while chunk := os.read(descriptor, 1024 * 1024):
                payload.extend(chunk)
                if len(payload) > maximum:
                    raise FinalizerError(f"{label} exceeds its bound")
            after_fd = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        after = direct.lstat()
    except OSError as exc:
        raise FinalizerError(f"{label} is unavailable") from exc
    identity = lambda item: (
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_nlink,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or identity(before) != identity(inside)
        or identity(before) != identity(after_fd)
        or identity(before) != identity(after)
        or len(payload) != before.st_size
    ):
        raise FinalizerError(f"{label} is not one stable direct file")
    return bytes(payload)


def _verify_exact_files() -> None:
    for label, (path, size, digest) in EXACT_FILES.items():
        payload = _stable(path, label)
        if (len(payload), _sha256(payload)) != (size, digest):
            raise FinalizerError(f"{label} identity differs")


def _load_runtime() -> tuple[Any, Any]:
    _verify_exact_files()
    if str(REVALIDATION) not in sys.path:
        sys.path.insert(0, str(REVALIDATION))
    import device_action_f1_live_v2 as live  # noqa: PLC0415
    import device_action_f1_v2 as core  # noqa: PLC0415

    if (
        Path(live.__file__).resolve(strict=True) != EXACT_FILES["live_source"][0]
        or Path(core.__file__).resolve(strict=True) != EXACT_FILES["core_source"][0]
        or live.core is not core
    ):
        raise FinalizerError("loaded Process-v2 runtime identity differs")
    return live, core


def _load_prepared_stored_lane(live: Any) -> Any:
    original = live._p324_typec_lane_value  # noqa: SLF001

    def stored(prepared: Any, **_kwargs: Any) -> Any:
        return original(prepared, revalidate=False)

    live._p324_typec_lane_value = stored  # noqa: SLF001
    try:
        return live.load_prepared(ROOT, MANIFEST, RUN_DIR)
    finally:
        live._p324_typec_lane_value = original  # noqa: SLF001


def _raw_handle(live: Any, path: Path, maximum: int) -> tuple[bytes, dict[str, Any]]:
    try:
        handle = live.raw_capture.load_handle(path)
        stdout = live.raw_capture.read_stdout(handle, maximum=maximum)
        stderr = live.raw_capture.read_stderr(handle, maximum=64 * 1024)
        value = json.loads(_stable(path, path.name, 64 * 1024))
    except (OSError, ValueError, live.raw_capture.RawCaptureError) as exc:
        raise FinalizerError(f"retained raw handle differs: {path.name}") from exc
    if (
        handle.returncode != 0
        or handle.timed_out
        or handle.output_exceeded
        or handle.producer_error_type is not None
        or stderr
        or not isinstance(value, dict)
        or value.get("elapsed_msec") is None
    ):
        raise FinalizerError(f"retained raw command failed: {path.name}")
    return stdout, value


def _final_health(live: Any, prepared: Any) -> dict[str, Any]:
    raw = RUN_DIR / "raw-adb"
    properties_raw, _ = _raw_handle(
        live, raw / "0021-adb-read-only-shell.capture.json", 64 * 1024
    )
    root_raw, _ = _raw_handle(
        live, raw / "0022-adb-read-only-shell.capture.json", 64 * 1024
    )
    inventory_raw, _ = _raw_handle(
        live, raw / "0025-adb-devices.capture.json", 64 * 1024
    )
    topology_raw, _ = _raw_handle(
        live, raw / "0026-adb-get-devpath.capture.json", 64 * 1024
    )
    try:
        properties = live.d0._parse_key_values(  # noqa: SLF001
            properties_raw.decode("utf-8", "strict"),
            live.d0.AdbReadOnlyClient.PROPERTY_FIELDS,
            "retained final Android properties",
        )
        root_health = live.d0._parse_key_values(  # noqa: SLF001
            root_raw.decode("utf-8", "strict"),
            {"root", "boot", "vendor_boot", "dtbo", "recovery"},
            "retained final root health",
        )
        inventory = inventory_raw.decode("utf-8", "strict").splitlines()
        topology = topology_raw.decode("utf-8", "strict").strip()
    except (UnicodeError, live.d0.D0Error) as exc:
        raise FinalizerError("retained final health cannot be decoded") from exc
    serial = prepared.private_target["serial"]
    matches = []
    for line in inventory:
        fields = line.split()
        if len(fields) >= 2 and fields[0] == serial and fields[1] == "device":
            matches.append(set(fields[2:]))
    expected_metadata = {
        "model:SM_S906N",
        "device:g0q",
    }
    if (
        len(matches) != 1
        or not expected_metadata <= matches[0]
        or topology != prepared.private_target["topology"]
    ):
        raise FinalizerError("retained final target continuity differs")
    snapshots = [
        json.loads(line)
        for line in _stable(
            EXACT_FILES["odin_snapshots"][0], "Odin endpoint snapshots"
        ).splitlines()
        if line
    ]
    if (
        len(snapshots) != 50
        or snapshots[-1].get("sequence") != 49
        or snapshots[-1].get("record") != "odin_snapshot"
        or snapshots[-1].get("live_devices") != []
        or snapshots[-1].get("stale_devices") != []
    ):
        raise FinalizerError("retained final Download absence differs")
    try:
        return live.d0.validate_health(
            prepared.bundle,
            properties,
            root_health,
            True,
            "final_health",
        )
    except live.d0.D0Error as exc:
        raise FinalizerError("retained final health differs") from exc


def _final_observer(live: Any, prepared: Any) -> dict[str, Any]:
    payloads: list[bytes] = []
    receipts: list[dict[str, Any]] = []
    for index, sequence in ((1, "0023"), (2, "0024")):
        receipt_path = RUN_DIR / f"{sequence}-observer-eof.capture.json"
        payload, raw_value = _raw_handle(
            live, receipt_path, live.MAX_OBSERVER_BYTES
        )
        destination = RUN_DIR / f"rollback-observer-{index}.bin"
        if payload != _stable(destination, destination.name):
            raise FinalizerError("retained rollback observer bytes differ")
        elapsed = raw_value["elapsed_msec"] / 1000
        if not 0 < elapsed <= 185:
            raise FinalizerError("retained rollback observer duration differs")
        receipt_payload = _stable(receipt_path, receipt_path.name, 64 * 1024)
        receipts.append(
            {
                "path": str(destination),
                "bytes": len(payload),
                "sha256": _sha256(payload),
                "raw_capture": {
                    "path": str(receipt_path),
                    "size": len(receipt_payload),
                    "sha256": _sha256(receipt_payload),
                },
                "read_to_eof": True,
                "stderr_bytes": 0,
                "elapsed_sec": elapsed,
            }
        )
        payloads.append(payload)
    if not payloads[0] or payloads[0] != payloads[1]:
        raise FinalizerError("retained rollback observer reads differ")
    acceptance = prepared.bundle.manifest["observation"]["acceptance"]
    try:
        live.classify_acceptance(payloads[0], acceptance)
    except Exception as exc:  # the exact escaped adapter exception is the incident
        if type(exc).__name__ != "AdapterIdentityError" or str(exc) != EXPECTED_PARSER_ERROR:
            raise FinalizerError("P3.34 parser incident differs") from exc
        wrapped = live.F1LiveError(str(exc))
    else:
        raise FinalizerError("P3.34 missing-return parser unexpectedly accepted")
    marker = live._p334_parser_failure_classification(  # noqa: SLF001
        payloads[0], wrapped
    )
    stock_error = live._p334_stock_error(payloads[0], wrapped)  # noqa: SLF001
    if (
        marker.get("classification") != "P334_STOCK_PARSER_EXCEPTION"
        or marker.get("accepted") is not False
        or marker.get("p334_stock_error") != stock_error
    ):
        raise FinalizerError("P3.34 supplemental failure projection differs")
    return {
        "reads": receipts,
        "byte_identical": True,
        "bytes": len(payloads[0]),
        "sha256": _sha256(payloads[0]),
        "exact_marker_count": 0,
        "marker_family_count": 0,
        "classification": marker,
        "accepted": False,
        "p334_stock_error": stock_error,
    }


def _audit_context() -> tuple[Any, Any, Any, Any, dict[str, Any]]:
    if RUN_DIR.is_symlink() or RUN_DIR.absolute() != RUN_DIR.resolve(strict=True):
        raise FinalizerError("exact P3.34 run directory is indirect")
    if RESULT_PATH.is_symlink():
        raise FinalizerError("P3.34 result is indirect")
    state_payload = _stable(STATE_PATH, "P3.34 CLOSED state", 64 * 1024)
    if (len(state_payload), _sha256(state_payload)) != EXPECTED_CLOSED_STATE:
        raise FinalizerError("P3.34 CLOSED state identity differs")
    head_payload = _stable(
        RUN_DIR / "transaction/journal-head.json", "P3.34 journal head"
    )
    if (len(head_payload), _sha256(head_payload)) != EXPECTED_CLOSED_HEAD:
        raise FinalizerError("P3.34 CLOSED journal head differs")
    live, core = _load_runtime()
    prepared = _load_prepared_stored_lane(live)
    if (
        prepared.binding_sha256 != EXPECTED_BINDING
        or prepared.bundle.sha256 != EXPECTED_BUNDLE
        or prepared.run_dir != RUN_DIR
    ):
        raise FinalizerError("P3.34 prepared binding differs")
    journal = core.Journal(RUN_DIR / "transaction", EXPECTED_BINDING)
    records = journal.records()
    if (
        journal.state() != "CLOSED"
        or len(records) != 19
        or records[-1].get("sequence") != 18
        or records[-1].get("state") != "CLOSED"
        or records[-1].get("record_sha256") != EXPECTED_TERMINAL_RECORD_SHA256
    ):
        raise FinalizerError("P3.34 journal is not the exact CLOSED cut")
    for name in ("candidate", "rollback"):
        for suffix in ("start", "result"):
            extra = RUN_DIR / f"{name}-attempt-02.{suffix}.json"
            if extra.exists() or extra.is_symlink():
                raise FinalizerError("a second transfer attempt exists")
        result = live._validate_transfer_result(prepared, name, 1)  # noqa: SLF001
        if result.get("classification") != "odin_transfer_completed":
            raise FinalizerError(f"P3.34 {name} transfer differs")
    state = live._state(prepared)  # noqa: SLF001
    expected_state = {
        "candidate_classification": "odin_transfer_completed",
        "candidate_completed": True,
        "candidate_observer_classification": "accepted",
        "candidate_observer_accepted": True,
        "candidate_observer_guard_released": True,
        "candidate_observer_guard_release_status": "released",
        "download_endpoint_absent": True,
        "rollback_classification": "odin_transfer_completed",
        "rollback_completed": True,
        "final_verified": True,
        "marker_accepted": False,
        "hmac_authenticated": True,
        "logical_resident_proof": True,
        "same_tty_fd": True,
        "physical_reopen_count": 0,
        "session_count": 2,
        "successful_sessions": 2,
        "reconnect_count": 0,
        "command_count": 6,
        "busybox_ash_command_proof": True,
        "framed_session_closed": True,
    }
    if (
        _canonical(state) != state_payload
        or any(state.get(key) != value for key, value in expected_state.items())
    ):
        raise FinalizerError("P3.34 successful CLOSED state differs")
    reopened = live._reopen_candidate_observation(prepared)  # noqa: SLF001
    if (
        reopened.get("accepted") is not True
        or reopened.get("successful_sessions") != 2
        or reopened.get("command_count") != 6
        or reopened.get("logical_resident_proof") is not True
    ):
        raise FinalizerError("P3.34 candidate proof cannot be reopened")
    final = {
        "health": _final_health(live, prepared),
        "target_evidence_sha256": core.json_sha256(
            {
                "serial": _sha256(prepared.private_target["serial"].encode()),
                "topology": _sha256(prepared.private_target["topology"].encode()),
            }
        ),
        "observer": _final_observer(live, prepared),
        "rollback_verified": True,
    }
    projection = state.get(live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY)
    if (
        not isinstance(projection, dict)
        or projection.get("proof") is not True
        or projection.get("final_healthy_return") is not True
        or projection.get("successful_sessions") != 2
        or projection.get("command_count") != 6
        or state.get("final_evidence") != final
        or state.get("p334_stock_error")
        != final["observer"]["p334_stock_error"]
    ):
        raise FinalizerError("P3.34 CLOSED final evidence differs")
    return live, core, prepared, journal, final


def _publish_closed_result(
    live: Any, prepared: Any, journal: Any, *, allow_create: bool
) -> tuple[dict[str, Any], bool]:
    """Use the intended supplemental-error branch during result validation."""
    original = live.classify_acceptance

    def classify(payload: bytes, acceptance: dict[str, Any]) -> dict[str, Any]:
        try:
            return original(payload, acceptance)
        except Exception as exc:
            if (
                type(exc).__name__ != "AdapterIdentityError"
                or str(exc) != EXPECTED_PARSER_ERROR
            ):
                raise
            raise live.F1LiveError(str(exc)) from exc

    live.classify_acceptance = classify
    try:
        verdict, outcome = live._closed_terminal_classification(prepared)  # noqa: SLF001
        if (verdict, outcome) != (EXPECTED_RESULT_VERDICT, EXPECTED_OUTCOME):
            raise FinalizerError("P3.34 CLOSED terminal classification differs")
        if RESULT_PATH.exists():
            payload = _stable(RESULT_PATH, "P3.34 terminal result", 64 * 1024)
            if (len(payload), _sha256(payload)) != EXPECTED_RESULT:
                raise FinalizerError("P3.34 terminal result identity differs")
            try:
                value = json.loads(payload, object_pairs_hook=live.core._unique_object)  # noqa: SLF001
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise FinalizerError("P3.34 terminal result cannot be decoded") from exc
            if not isinstance(value, dict) or _canonical(value) != payload:
                raise FinalizerError("P3.34 terminal result is not canonical")
            live.validate_live_result(value, prepared)
            return value, False
        if not allow_create:
            raise FinalizerError("P3.34 terminal result is absent")
        return (
            live._result(  # noqa: SLF001
                prepared, journal, verdict, outcome, False
            ),
            True,
        )
    finally:
        live.classify_acceptance = original


def finalize(*, audit_only: bool) -> dict[str, Any]:
    if audit_only:
        live, _core, prepared, journal, final = _audit_context()
        _result, _created = _publish_closed_result(
            live, prepared, journal, allow_create=False
        )
        if _created:
            raise FinalizerError("P3.34 audit created a terminal result")
        return {
            "schema": SCHEMA,
            "verdict": AUDIT_VERDICT,
            "journal_state": "CLOSED",
            "result_present": True,
            "candidate_observation_proved": True,
            "rollback_verified_from_retained_evidence": final["rollback_verified"],
            "created": False,
            "device_contact": False,
            "adb_invoked": False,
            "usb_revalidated": False,
            "odin_invoked": False,
            "candidate_transfer": False,
            "rollback_transfer": False,
            "live_authorized": False,
        }
    live, _core = _load_runtime()
    with live.odin_core.transaction_session(RUN_DIR / "f1-session"):
        live, _core, prepared, journal, _final = _audit_context()
        result, created = _publish_closed_result(
            live, prepared, journal, allow_create=True
        )
    if (
        result.get("current_state") != "CLOSED"
        or result.get("verdict") != EXPECTED_RESULT_VERDICT
        or result.get("outcome_class") != EXPECTED_OUTCOME
        or result.get("recovery_required") is not False
    ):
        raise FinalizerError("P3.34 final terminal differs")
    records = _core.Journal(RUN_DIR / "transaction", EXPECTED_BINDING).records()
    if len(records) != 19 or records[-1].get("state") != "CLOSED":
        raise FinalizerError("P3.34 final journal differs")
    if (
        (STATE_PATH.stat().st_size, _sha256(STATE_PATH.read_bytes()))
        != EXPECTED_CLOSED_STATE
        or (
            (RUN_DIR / "transaction/journal-head.json").stat().st_size,
            _sha256((RUN_DIR / "transaction/journal-head.json").read_bytes()),
        )
        != EXPECTED_CLOSED_HEAD
    ):
        raise FinalizerError("result publication changed CLOSED state or journal")
    for name in ("candidate", "rollback"):
        if any(RUN_DIR.glob(f"{name}-attempt-02.*")):
            raise FinalizerError("P3.34 finalization created another transfer attempt")
    return {
        "schema": SCHEMA,
        "verdict": PUBLISH_VERDICT,
        "journal_state": "CLOSED",
        "result_verdict": result["verdict"],
        "outcome_class": result["outcome_class"],
        "candidate_arrival_proved": True,
        "rollback_verified_from_retained_evidence": True,
        "result": {
            "path": str(RESULT_PATH),
            "size": RESULT_PATH.stat().st_size,
            "sha256": _sha256(RESULT_PATH.read_bytes()),
        },
        "state": {
            "path": str(STATE_PATH),
            "size": STATE_PATH.stat().st_size,
            "sha256": _sha256(STATE_PATH.read_bytes()),
        },
        "created": created,
        "device_contact": False,
        "adb_invoked": False,
        "usb_revalidated": False,
        "odin_invoked": False,
        "candidate_transfer": False,
        "rollback_transfer": False,
        "live_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--audit-only", action="store_true")
    group.add_argument("--finalize", action="store_true")
    args = parser.parse_args(argv)
    try:
        value = finalize(audit_only=args.audit_only)
    except FinalizerError as exc:
        parser.error(str(exc))
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
