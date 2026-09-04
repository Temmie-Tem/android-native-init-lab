#!/usr/bin/env python3
"""Close the exact P3.36 run from retained post-rollback evidence only.

The candidate and exact Magisk rollback were each transferred once.  The live
runner then collected healthy Android/root evidence and two identical rollback
observer reads, but stopped before HEALTH_VERIFIED because its final observer
publisher omitted the new P336 stock key.  This finalizer opens no device or
USB backend and performs no transfer.  It reconstructs only the already
captured final evidence, repairs the interrupted P336 proof projection from
the runner's own durable fallback, and resumes the journal tail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent
MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p336_process_v2_ready_1.json"
)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "p336-ready1-prepared-20260904-2"
)
STATE_PATH = RUN_DIR / "live-state.json"
RESULT_PATH = RUN_DIR / "live-result.json"
TRANSACTION = RUN_DIR / "transaction"

SCHEMA = "s22plus_fyg8_p336_postrollback_finalizer_v1"
AUDIT_VERDICT = "PASS_P336_POSTROLLBACK_FINALIZER_AUDIT_HOST_ONLY"
FINALIZE_VERDICT = "PASS_P336_POSTROLLBACK_FINALIZED_HOST_ONLY"
EXPECTED_BINDING = (
    "fb5d8f5298f8e187a3fba9f477cf192fa161a4ed3d11322f59ab0b5894ba8a87"
)
EXPECTED_BUNDLE = (
    "c2a1e71b3cdf51495f4ec59a9d414e92680a1bac400d353bd4e0531dcc96e6af"
)
EXPECTED_PRE_STATE = (
    2_244,
    "d9049cd48eaf2815258ebb8ac6d2317010053fa5cd032d2d17fecee6bb3f9a4a",
)
EXPECTED_PRE_HEAD = (
    276,
    "b2e6deb41340c0e0b36f35c113a1f684e46ffb4932943c484d363f6c97217fdb",
)
EXPECTED_NO_PROOF_OUTCOME = (
    "p336_authenticated_long_idle_resident_unproved_rollback_verified"
)

EXACT_FILES = {
    "manifest": (
        MANIFEST,
        8_911,
        "752ec97a2f79e31775e8f6361d0cd260da51727c4ac1cfbfe38ffc00be96372a",
    ),
    "live_source": (
        REVALIDATION / "device_action_f1_live_v2.py",
        567_567,
        "aa466742444767020d5cc4181f21d2657ca5d8922b1ef91259fd31f8e91e6749",
    ),
    "core_source": (
        REVALIDATION / "device_action_f1_v2.py",
        145_859,
        "fdb21354b1acec1982748a88e63b7b6e8e43186e5499ae500b6a3866ed1113fe",
    ),
    "evidence_source": (
        REVALIDATION / "device_action_f1_evidence_v2.py",
        697_621,
        "594d8c40e56a938a26c7bb9adeff7a7d4a6c45f5a55edec49d174cdb83936ade",
    ),
    "prepared": (
        RUN_DIR / "prepared.json",
        24_241,
        "019d69bbf4958fbf701493a0e35b1eec267dfd430beb1b134042bde0b0b3cb0b",
    ),
    "target": (
        RUN_DIR / "target-private.json",
        107,
        "94a7c1e84513f2b6e59fc2a2cc6bff0de390c42d56f155f0a34c05e3dbfd3aab",
    ),
    "candidate_result": (
        RUN_DIR / "candidate-attempt-01.result.json",
        2_079,
        "cf250ff7d4f8acefb68dc931943684cd689b94300c8f99fdcf06738d81721cf5",
    ),
    "rollback_result": (
        RUN_DIR / "rollback-attempt-01.result.json",
        2_030,
        "ef989d7ef97b69a9677946b17f8792a84edcbdf8e565b404a65bd1f7da78ca79",
    ),
    "candidate_capture": (
        RUN_DIR / "candidate-observer.capture.json",
        519,
        "d4313c95973e07b6ca26dac8909e43e321e0e30acdbf92af2c1c0566a9b8bd30",
    ),
    "candidate_raw": (
        RUN_DIR / "candidate-observer.raw",
        73,
        "19955936676751fff5e9d8643b0b5d4f8a89e27d94da57c80771ef5c1b39b5b6",
    ),
    "endpoint_journal": (
        RUN_DIR / "odin-endpoints/transaction.jsonl",
        53_878,
        "60269ab178c9d8aeeeb786bd3b08a00892d1198b7010738979cf569c64147fdd",
    ),
    "rollback_capture_1": (
        RUN_DIR / "0027-observer-eof.capture.json",
        510,
        "c4e5d423c66acf470ff267afa1a50d7d3e1dd995972050a11178065885ecee89",
    ),
    "rollback_capture_2": (
        RUN_DIR / "0028-observer-eof.capture.json",
        510,
        "a26526faed525bce539d7144935e7ef56e42abb6371dc81902574109d6e25330",
    ),
    "rollback_raw_1": (
        RUN_DIR / "rollback-observer-1.bin",
        2_097_136,
        "c8f8c4fd67a354beee120fd473502d1d296f5aeb98410293d41f9d38114b7efe",
    ),
    "rollback_raw_2": (
        RUN_DIR / "rollback-observer-2.bin",
        2_097_136,
        "c8f8c4fd67a354beee120fd473502d1d296f5aeb98410293d41f9d38114b7efe",
    ),
    "final_properties_capture": (
        RUN_DIR / "raw-adb/0025-adb-read-only-shell.capture.json",
        530,
        "d9eebda26ce451fd3445f43c57f1006253108c675270033a17d65a45c9dee5ab",
    ),
    "final_root_capture": (
        RUN_DIR / "raw-adb/0026-adb-read-only-shell.capture.json",
        531,
        "f686869f40aa2df1879cb14decd80cc420879afeb3d15533916d0da9f074f0cd",
    ),
    "final_inventory_capture": (
        RUN_DIR / "raw-adb/0029-adb-devices.capture.json",
        505,
        "14ba45016be67243956eefb231e9c70494455e21609df4a2babe89ce5059eaa9",
    ),
    "final_topology_capture": (
        RUN_DIR / "raw-adb/0030-adb-get-devpath.capture.json",
        516,
        "48d3834e35bc0a578b381d4be8e9ff8ba0be4a87805a4825d6ec75e37b13435e",
    ),
}


class FinalizerError(RuntimeError):
    """The exact consumed P3.36 rollback cut cannot be finalized."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _stable(path: Path, label: str, maximum: int = 4 * 1024 * 1024) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        descriptor = os.open(
            direct, os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
        )
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
    identity = lambda value: (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )
    if (
        direct != resolved
        or not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
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


def _load_prepared(live: Any) -> Any:
    original = live._p324_typec_lane_value  # noqa: SLF001

    def stored(prepared: Any, **_kwargs: Any) -> Any:
        return original(prepared, revalidate=False)

    live._p324_typec_lane_value = stored  # noqa: SLF001
    try:
        prepared = live.load_prepared(ROOT, MANIFEST, RUN_DIR)
    finally:
        live._p324_typec_lane_value = original  # noqa: SLF001
    if (
        prepared.binding_sha256 != EXPECTED_BINDING
        or prepared.bundle.sha256 != EXPECTED_BUNDLE
        or prepared.run_dir != RUN_DIR
    ):
        raise FinalizerError("P3.36 prepared binding differs")
    return prepared


def _raw_handle(live: Any, path: Path, maximum: int) -> tuple[bytes, Mapping[str, Any]]:
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
        or type(value.get("elapsed_msec")) is not int
    ):
        raise FinalizerError(f"retained raw command failed: {path.name}")
    return stdout, value


def _final_health(live: Any, prepared: Any) -> dict[str, Any]:
    raw = RUN_DIR / "raw-adb"
    properties_raw, _ = _raw_handle(
        live, raw / "0025-adb-read-only-shell.capture.json", 64 * 1024
    )
    root_raw, _ = _raw_handle(
        live, raw / "0026-adb-read-only-shell.capture.json", 64 * 1024
    )
    inventory_raw, _ = _raw_handle(
        live, raw / "0029-adb-devices.capture.json", 64 * 1024
    )
    topology_raw, _ = _raw_handle(
        live, raw / "0030-adb-get-devpath.capture.json", 64 * 1024
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
    if (
        len(matches) != 1
        or not {"model:SM_S906N", "device:g0q"} <= matches[0]
        or topology != prepared.private_target["topology"]
    ):
        raise FinalizerError("retained final target continuity differs")
    endpoint_rows = [
        json.loads(line)
        for line in _stable(
            EXACT_FILES["endpoint_journal"][0], "endpoint journal", 128 * 1024
        ).splitlines()
        if line
    ]
    if (
        len(endpoint_rows) != 110
        or [row.get("sequence") for row in endpoint_rows] != list(range(110))
        or endpoint_rows[-1].get("record") != "odin_snapshot"
        or endpoint_rows[-1].get("live_devices") != []
        or endpoint_rows[-1].get("stale_devices") != []
    ):
        raise FinalizerError("retained final Download absence differs")
    try:
        return live.d0.validate_health(
            prepared.bundle, properties, root_health, True, "final_health"
        )
    except live.d0.D0Error as exc:
        raise FinalizerError("retained final health differs") from exc


def _final_observer(live: Any, prepared: Any) -> dict[str, Any]:
    payloads: list[bytes] = []
    receipts: list[dict[str, Any]] = []
    for index, sequence in ((1, "0027"), (2, "0028")):
        receipt_path = RUN_DIR / f"{sequence}-observer-eof.capture.json"
        payload, capture = _raw_handle(live, receipt_path, live.MAX_OBSERVER_BYTES)
        destination = RUN_DIR / f"rollback-observer-{index}.bin"
        if payload != _stable(destination, destination.name):
            raise FinalizerError("retained rollback observer bytes differ")
        elapsed = capture["elapsed_msec"] / 1000
        if not 0 < elapsed <= 185:
            raise FinalizerError("retained rollback observer duration differs")
        capture_payload = _stable(receipt_path, receipt_path.name, 64 * 1024)
        receipts.append(
            {
                "path": str(destination),
                "bytes": len(payload),
                "sha256": _sha256(payload),
                "raw_capture": {
                    "path": str(receipt_path),
                    "size": len(capture_payload),
                    "sha256": _sha256(capture_payload),
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
        classified = live.classify_acceptance(payloads[0], acceptance)
        projection = live._p320_terminal_projection(classified)  # noqa: SLF001
    except live.F1LiveError as exc:
        raise FinalizerError("retained P3.36 stock evidence cannot be classified") from exc
    if (
        classified.get("overlay_contract_id")
        != live.typed_evidence.P336_STOCK_OVERLAY_CONTRACT_ID
        or classified.get("classification") != "AMBIGUOUS_INTEGRITY_FAILURE"
        or classified.get("proof_class") != "NO_PROOF_OBSERVER"
        or classified.get("accepted") is not False
        or projection.get("proof_class") != "NO_PROOF_OBSERVER"
        or projection.get("candidate_success") is not False
    ):
        raise FinalizerError("retained P3.36 stock projection differs")
    return {
        "reads": receipts,
        "byte_identical": True,
        "bytes": len(payloads[0]),
        "sha256": _sha256(payloads[0]),
        "exact_marker_count": classified["exact_count"],
        "marker_family_count": classified["family_count"],
        "classification": classified,
        "accepted": False,
        "p336_stock": projection,
    }


def _reconstruct_final(live: Any, core: Any, prepared: Any) -> dict[str, Any]:
    return {
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


def _repair_state_projection(
    live: Any, prepared: Any, state: dict[str, Any], final: dict[str, Any]
) -> dict[str, Any]:
    durable = live._reopen_candidate_observation(prepared)  # noqa: SLF001
    repaired = dict(state)
    for key in dict.fromkeys(
        (
            *live.P332_PROOF_FIELDS,
            *live.P336_PROOF_FIELDS,
            "p336_authenticated_attended_resident",
        )
    ):
        repaired[key] = durable.get(key)
    repaired.update(
        {
            "final_verified": True,
            "marker_accepted": False,
            "final_evidence": final,
            "p336_proof_class": "NO_PROOF_OBSERVER",
            "p336_stock": final["observer"]["p336_stock"],
        }
    )
    live._save_candidate_arrival_proof(prepared, repaired)  # noqa: SLF001
    live._validate_candidate_observer_state(prepared, repaired)  # noqa: SLF001
    live._validate_final_observer(prepared, repaired)  # noqa: SLF001
    return repaired


def _context() -> tuple[Any, Any, Any, Any, dict[str, Any], dict[str, Any]]:
    if RUN_DIR.is_symlink() or RUN_DIR.resolve(strict=True) != RUN_DIR.absolute():
        raise FinalizerError("exact P3.36 run directory is indirect")
    live, core = _load_runtime()
    prepared = _load_prepared(live)
    journal = core.Journal(TRANSACTION, EXPECTED_BINDING)
    if journal.state() not in {"ROLLBACK_FLASHED", "HEALTH_VERIFIED", "CLOSED"}:
        raise FinalizerError("P3.36 journal is not at a post-rollback cut")
    records = journal.records()
    if len(records) < 15 or records[13].get("state") != "ROLLBACK_FLASHED":
        raise FinalizerError("P3.36 rollback transition differs")
    for kind in ("candidate", "rollback"):
        result = live._validate_transfer_result(prepared, kind, 1)  # noqa: SLF001
        if result is None or result.get("classification") != "odin_transfer_completed":
            raise FinalizerError(f"P3.36 {kind} transfer differs")
        if any(RUN_DIR.glob(f"{kind}-attempt-02.*")):
            raise FinalizerError("a second transfer attempt exists")
    state = live._state(prepared)  # noqa: SLF001
    final = _reconstruct_final(live, core, prepared)
    if state.get("final_verified") is not True:
        state_payload = _stable(STATE_PATH, "P3.36 pre-final state", 64 * 1024)
        head_payload = _stable(
            TRANSACTION / "journal-head.json", "P3.36 pre-final journal head"
        )
        if (
            journal.state() != "ROLLBACK_FLASHED"
            or (len(state_payload), _sha256(state_payload)) != EXPECTED_PRE_STATE
            or (len(head_payload), _sha256(head_payload)) != EXPECTED_PRE_HEAD
            or state.get("rollback_completed") is not True
            or state.get("candidate_completed") is not True
        ):
            raise FinalizerError("P3.36 pre-final cut differs")
        repaired = _repair_state_projection(live, prepared, state, final)
    else:
        repaired = state
        if (
            state.get("final_evidence") != final
            or state.get("p336_stock") != final["observer"]["p336_stock"]
            or state.get("p336_proof_class") != "NO_PROOF_OBSERVER"
        ):
            raise FinalizerError("P3.36 finalized evidence differs")
        live._validate_candidate_observer_state(prepared, repaired)  # noqa: SLF001
        live._validate_final_observer(prepared, repaired)  # noqa: SLF001
    return live, core, prepared, journal, repaired, final


def _terminal_result(live: Any, prepared: Any, journal: Any) -> dict[str, Any]:
    verdict, outcome = live._closed_terminal_classification(prepared)  # noqa: SLF001
    if (
        verdict != "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
        or outcome != EXPECTED_NO_PROOF_OUTCOME
    ):
        raise FinalizerError("P3.36 terminal classification differs")
    if RESULT_PATH.exists():
        value = json.loads(_stable(RESULT_PATH, "P3.36 terminal result", 128 * 1024))
        live.validate_live_result(value, prepared)
        return value
    return live._result(prepared, journal, verdict, outcome, False)  # noqa: SLF001


def _close(live: Any, prepared: Any, journal: Any, repaired: dict[str, Any]) -> dict[str, Any]:
    if journal.state() == "ROLLBACK_FLASHED":
        if live._state(prepared) != repaired:  # noqa: SLF001
            live._save_state(prepared, repaired)  # noqa: SLF001
        journal.transition(
            "HEALTH_VERIFIED",
            "final_health_and_rollback_verified",
            {"marker_accepted": False},
        )
    if journal.state() == "HEALTH_VERIFIED":
        events = live._events(journal)  # noqa: SLF001
        if "rollback_boot_ready" not in events:
            journal.event("rollback_boot_ready", {"healthy": True, "resumed": True})
            events = live._events(journal)  # noqa: SLF001
        if "live_session_end" not in events:
            journal.event(
                "live_session_end", {"rollback_verified": True, "resumed": True}
            )
        current = live._state(prepared)  # noqa: SLF001
        journal.transition(
            "CLOSED",
            "run_complete",
            {
                "marker_accepted": False,
                "candidate_observer_accepted": False,
                "candidate_observer_guard_released": current.get(
                    "candidate_observer_guard_released"
                )
                is True,
                "candidate_observer_guard_warning": current.get(
                    "candidate_observer_guard_warning"
                ),
            },
        )
    if journal.state() != "CLOSED":
        raise FinalizerError("P3.36 journal did not close")
    return _terminal_result(live, prepared, journal)


def finalize(*, audit_only: bool) -> dict[str, Any]:
    live, core, prepared, journal, repaired, final = _context()
    if audit_only:
        result_present = RESULT_PATH.exists()
        if journal.state() == "CLOSED":
            _terminal_result(live, prepared, journal)
        elif result_present:
            raise FinalizerError("P3.36 result precedes CLOSED")
        return {
            "schema": SCHEMA,
            "verdict": AUDIT_VERDICT,
            "journal_state": journal.state(),
            "candidate_transfer_count": 1,
            "rollback_transfer_count": 1,
            "rollback_verified_from_retained_evidence": final["rollback_verified"],
            "stock_proof_class": final["observer"]["p336_stock"]["proof_class"],
            "ready_to_finalize": journal.state() != "CLOSED",
            "result_present": result_present,
            "created": False,
            "device_contact": False,
            "adb_invoked": False,
            "usb_revalidated": False,
            "odin_invoked": False,
            "candidate_transfer": False,
            "rollback_transfer": False,
            "live_authorized": False,
        }
    with live.odin_core.transaction_session(RUN_DIR / "f1-session"):
        live, core, prepared, journal, repaired, final = _context()
        result = _close(live, prepared, journal, repaired)
    if (
        result.get("current_state") != "CLOSED"
        or result.get("verdict") != "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
        or result.get("outcome_class") != EXPECTED_NO_PROOF_OUTCOME
        or result.get("recovery_required") is not False
    ):
        raise FinalizerError("P3.36 final terminal differs")
    return {
        "schema": SCHEMA,
        "verdict": FINALIZE_VERDICT,
        "journal_state": "CLOSED",
        "result_verdict": result["verdict"],
        "outcome_class": result["outcome_class"],
        "candidate_transfer_count": 1,
        "rollback_transfer_count": 1,
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
        "created": True,
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
