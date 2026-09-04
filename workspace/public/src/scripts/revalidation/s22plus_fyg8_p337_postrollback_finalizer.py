#!/usr/bin/env python3
"""Close the exact consumed P3.37 run from retained evidence only.

Candidate and rollback transfers already completed exactly once and the live
runner retained final Android/root health plus two identical rollback reads.
It stopped before HEALTH_VERIFIED because the P337 stock projection was absent.
This finalizer has no device/USB/transfer backend.  It reopens only the fixed
consumed run, rederives its original binding without relaxing the common
loader, repairs the retained P337 receipt projection, and closes the journal.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import stat
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent
BASE_SOURCE = REVALIDATION / "s22plus_fyg8_p336_postrollback_finalizer.py"
MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p337_process_v2_ready_7.json"
)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "p337-ready7-prepared-20260904-2"
)
STATE_PATH = RUN_DIR / "live-state.json"
RESULT_PATH = RUN_DIR / "live-result.json"
TRANSACTION = RUN_DIR / "transaction"

SCHEMA = "s22plus_fyg8_p337_postrollback_finalizer_v1"
AUDIT_VERDICT = "PASS_P337_POSTROLLBACK_FINALIZER_AUDIT_HOST_ONLY"
FINALIZE_VERDICT = "PASS_P337_POSTROLLBACK_FINALIZED_HOST_ONLY"
EXPECTED_BINDING = (
    "2858d03fb967d591854d2c4a98f41057970c0942629b1526b44e2706855f6323"
)
EXPECTED_OLD_BUNDLE = (
    "99ee24fdee53b7f728a3e8ea1faabbe6a92fae9cbb855aced4aee0154f5bdb5b"
)
EXPECTED_CURRENT_BUNDLE = (
    "fe739dcd00f49fe90bde282ce01cd81add7a48b983372d693b5ea02a869d5a21"
)
EXPECTED_OLD_CLOSURE = (
    "c59d829cc3577ab07c20f96b3ec9ffd5a5bcdcb002348aaa01ddb9ffe9e36c06"
)
EXPECTED_CURRENT_CLOSURE = (
    "1441b739160d05a280280bc21d084a5028b78d04a06dfad2c6827763f6f1b5de"
)
EXPECTED_PRE_STATE = (
    6_507,
    "cbe01b95d4b54dfdef64be72a0f52dd8b34cc41a6bd6215221912c22f1c8957f",
)
EXPECTED_PRE_HEAD = (
    276,
    "e37fb809cd66fad840f014875fc3ce97603d7c99877b48b0b1610cfca98d68b1",
)
EXPECTED_NO_PROOF_OUTCOME = (
    "p337_authenticated_resident_open_read_diagnostic_unproved_rollback_verified"
)
OLD_ADAPTER = {
    "path": str(REVALIDATION / "device_action_f1_live_v2.py"),
    "size": 596_753,
    "sha256": "463ef1d1d89ff72426cb29bce69a9d2fefb9bfcb8f30a0d1b0cd2570f0765d77",
}
OLD_EVIDENCE = {
    "path": str(REVALIDATION / "device_action_f1_evidence_v2.py"),
    "size": 728_161,
    "sha256": "3638864e60c90a0c7a2667756a7dd491e5317168b50018249dc4d80d37dc0167",
}

EXACT_FILES = {
    "base_finalizer": (
        BASE_SOURCE,
        23_965,
        "d669dca0e919e72d6c55a026a5a9f3ddd59f2aa585a71294b244337354e4cdb6",
    ),
    "manifest": (
        MANIFEST,
        9_464,
        "444322eca68598a8875a1facd61bc1b2ed449dbda0210c8ae40d74bdd1f0619d",
    ),
    "live_source": (
        REVALIDATION / "device_action_f1_live_v2.py",
        597_112,
        "9c3e27860e6cf398da8a13e7a0cf8891274c4b075f7cb2152dce18eff297599b",
    ),
    "core_source": (
        REVALIDATION / "device_action_f1_v2.py",
        149_413,
        "5c301612ecf6af13954971cad6c6f6a1f9c419a1d658bc602ac67eaf6c3472eb",
    ),
    "evidence_source": (
        REVALIDATION / "device_action_f1_evidence_v2.py",
        729_792,
        "b416f23a5f450272b3228d1430a50c241104342a519425797dcaa218dde8693e",
    ),
    "prepared": (
        RUN_DIR / "prepared.json",
        24_298,
        "5ec9c27a40c697246b63eb84e528cb5800cb4a690ee979355bb212f0a05232ab",
    ),
    "preflight": (
        RUN_DIR / "preflight/result.json",
        3_261,
        "abdff4575cf2235f7c6111d5dd2f52302cf07099276021dccace3acf04284ae0",
    ),
    "target": (
        RUN_DIR / "target-private.json",
        107,
        "94a7c1e84513f2b6e59fc2a2cc6bff0de390c42d56f155f0a34c05e3dbfd3aab",
    ),
    "lane": (
        RUN_DIR / "p324-typec-lane-binding.json",
        1_829,
        "3f80a810d55f39fd899a536be3b5e1fdcb5760918d7dfaf21b2bfb1422a9fa69",
    ),
    "trace_binding": (
        RUN_DIR / "p300-usb-trace-binding.json",
        1_733,
        "228670c35a34341c665e5366ef2db4df9c90b2546e2093dbde85831c836dd975",
    ),
    "candidate_result": (
        RUN_DIR / "candidate-attempt-01.result.json",
        2_079,
        "c3b80dfae2c08882064152f04e6600b36d31b0e34da300f5a91f6365eae8e1aa",
    ),
    "rollback_result": (
        RUN_DIR / "rollback-attempt-01.result.json",
        2_030,
        "beeacf4762ee2d44cd33d134f404a052168c3375f7d9ab97b398bd4ccb8f174f",
    ),
    "candidate_capture": (
        RUN_DIR / "candidate-observer.capture.json",
        517,
        "ffcfff4d373d9b096e44e960c06a22ee734b1b81ccb3af40f00b260091029623",
    ),
    "candidate_receipt": (
        RUN_DIR / "candidate-observer.json",
        7_406,
        "8a938155c4d66067debfbf1895f9df78eefe03d624b8ac1694672aab94c7ca8c",
    ),
    "candidate_raw": (
        RUN_DIR / "candidate-observer.raw",
        97,
        "066a47804aa425c50497032549e8938dff413cf25969b10d55e15729293bc943",
    ),
    "guard_arm": (
        RUN_DIR / "candidate-observer-guard.json",
        836,
        "dc43f0b67cdf0e5e69ccdefcff709a62700d2ab1529452d1f8bfd162b262be37",
    ),
    "guard_release": (
        RUN_DIR / "candidate-observer-guard-release.json",
        206,
        "bd4853f0879f9cf88d51b1494f6a6e6979fad0a2d5ccbdfb3d8736b5e24546ad",
    ),
    "endpoint_journal": (
        RUN_DIR / "odin-endpoints/transaction.jsonl",
        11_188,
        "a2e50fd632c255584b447f877f4568432437319403f922dd2e0dfb9752d529e6",
    ),
    "rollback_capture_1": (
        RUN_DIR / "0027-observer-eof.capture.json",
        510,
        "88728d2499317234bfe99e787d422c70dfc287b785d1c73ac2a9beaf9e189df3",
    ),
    "rollback_capture_2": (
        RUN_DIR / "0028-observer-eof.capture.json",
        510,
        "534a069fcadf35890e459e791609d3bbff6e245b08fc7b0cc39cb13d9dac9536",
    ),
    "rollback_raw_1": (
        RUN_DIR / "rollback-observer-1.bin",
        2_097_136,
        "64ac7a5b6666c4a21ce23effce2ec13015cdbdb985555300202ad46d8fe26a11",
    ),
    "rollback_raw_2": (
        RUN_DIR / "rollback-observer-2.bin",
        2_097_136,
        "64ac7a5b6666c4a21ce23effce2ec13015cdbdb985555300202ad46d8fe26a11",
    ),
    "final_properties_capture": (
        RUN_DIR / "raw-adb/0025-adb-read-only-shell.capture.json",
        530,
        "88a895450f0dbb20d106bd0338f9f6cc50302583bd6103a357be7e34486f390e",
    ),
    "final_root_capture": (
        RUN_DIR / "raw-adb/0026-adb-read-only-shell.capture.json",
        531,
        "c714c0714dd3118bfd44d4b7e15ecd784346178c28f1e3c25656997c74ac446e",
    ),
    "final_inventory_capture": (
        RUN_DIR / "raw-adb/0029-adb-devices.capture.json",
        505,
        "b8555ecba5fa9c548b9dc72ad408e9136b6716942facb54107b2e2449d45decf",
    ),
    "final_topology_capture": (
        RUN_DIR / "raw-adb/0030-adb-get-devpath.capture.json",
        516,
        "48d3834e35bc0a578b381d4be8e9ff8ba0be4a87805a4825d6ec75e37b13435e",
    ),
}


def _load_base() -> Any:
    before = BASE_SOURCE.lstat()
    payload = BASE_SOURCE.read_bytes()
    after = BASE_SOURCE.lstat()
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
        not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or before.st_nlink != 1
        or identity(before) != identity(after)
        or (len(payload), hashlib.sha256(payload).hexdigest())
        != EXACT_FILES["base_finalizer"][1:]
    ):
        raise RuntimeError("P3.36 base finalizer identity differs")
    module = types.ModuleType("p337_exact_p336_finalizer_base")
    module.__file__ = str(BASE_SOURCE)
    exec(compile(payload, str(BASE_SOURCE), "exec", dont_inherit=True), module.__dict__)
    return module


BASE = _load_base()
FinalizerError = BASE.FinalizerError


def _load_runtime() -> tuple[Any, Any]:
    BASE.EXACT_FILES = EXACT_FILES
    BASE._verify_exact_files()  # noqa: SLF001
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


def _load_prepared(live: Any, core: Any) -> Any:
    current = core.verify_bundle(ROOT, MANIFEST, runtime_bound=True)
    stored = live._read_json(RUN_DIR / "prepared.json", "prepared F1 record")  # noqa: SLF001
    if (
        current.sha256 != EXPECTED_CURRENT_BUNDLE
        or core.json_sha256(current.receipt) != EXPECTED_CURRENT_BUNDLE
        or stored.get("bundle_sha256") != EXPECTED_OLD_BUNDLE
        or stored.get("approval_binding_sha256") != EXPECTED_BINDING
        or stored.get("manifest_id") != current.manifest["manifest_id"]
        or stored.get("approval_token") != live.APPROVAL_PREFIX + EXPECTED_BINDING
    ):
        raise FinalizerError("P3.37 prepared header differs")

    stored_closure = stored.get("execution_closure")
    if not isinstance(stored_closure, dict):
        raise FinalizerError("P3.37 stored closure is absent")
    if (
        stored_closure.get("sources", {}).get("adapter") != OLD_ADAPTER
        or stored_closure.get("sources", {}).get("typed_evidence") != OLD_EVIDENCE
        or stored_closure.get("sha256") != EXPECTED_OLD_CLOSURE
    ):
        raise FinalizerError("P3.37 old source receipts differ")

    old_receipt = copy.deepcopy(current.receipt)
    sources = old_receipt.get("execution_critical_sources")
    if not isinstance(sources, dict):
        raise FinalizerError("P3.37 current bundle source receipts are absent")
    sources["typed_evidence"] = dict(OLD_EVIDENCE)
    sources["p300_tier3_direct_process_v2_evidence"] = {
        "size": OLD_EVIDENCE["size"],
        "sha256": OLD_EVIDENCE["sha256"],
    }
    if core.json_sha256(old_receipt) != EXPECTED_OLD_BUNDLE:
        raise FinalizerError("P3.37 old bundle receipt cannot be rederived")
    compat = core.Bundle(
        current.profile, current.manifest, old_receipt, EXPECTED_OLD_BUNDLE
    )

    current_closure = live._closure(ROOT, current)  # noqa: SLF001
    if current_closure.get("sha256") != EXPECTED_CURRENT_CLOSURE:
        raise FinalizerError("P3.37 current execution closure differs")
    old_closure = copy.deepcopy(current_closure)
    old_closure["sources"]["adapter"] = dict(OLD_ADAPTER)
    old_closure["sources"]["typed_evidence"] = dict(OLD_EVIDENCE)
    old_closure["sha256"] = core.json_sha256(
        {key: value for key, value in old_closure.items() if key != "sha256"}
    )
    if old_closure != stored_closure:
        raise FinalizerError("P3.37 old execution closure cannot be rederived")

    d0_path = RUN_DIR / "preflight/result.json"
    target_path = RUN_DIR / "target-private.json"
    d0_receipt = live._receipt(d0_path, "prepared D0 result")  # noqa: SLF001
    target_receipt = live._receipt(target_path, "private target")  # noqa: SLF001
    if stored.get("d0_result") != d0_receipt or stored.get(
        "private_target"
    ) != target_receipt:
        raise FinalizerError("P3.37 prepared input receipt differs")
    d0_result = live._read_json(d0_path, "prepared D0 result")  # noqa: SLF001
    private_target = live._read_json(target_path, "private target")  # noqa: SLF001
    live.d0.validate_result(d0_result, compat, RUN_DIR / "preflight")
    if set(private_target) != {"schema", "serial", "topology"} or private_target[
        "schema"
    ] != live.PRIVATE_TARGET_SCHEMA:
        raise FinalizerError("P3.37 private target shape differs")
    target = d0_result["target_evidence"]["targets"][0]
    if (
        hashlib.sha256(private_target["serial"].encode()).hexdigest()
        != target["adb_serial_sha256"]
        or hashlib.sha256(private_target["topology"].encode()).hexdigest()
        != target["usb_topology_sha256"]
    ):
        raise FinalizerError("P3.37 retained target continuity differs")

    prepared = live.PreparedRun(ROOT, RUN_DIR, compat, stored, private_target)
    live._validate_prepared_auth_key_identity(compat, stored)  # noqa: SLF001
    live._candidate_arrival_proof_role(compat)  # noqa: SLF001
    _lane, lane_receipt = live._p324_typec_lane_value(  # noqa: SLF001
        prepared, revalidate=False
    )
    binding, binding_sha256 = live._binding(  # noqa: SLF001
        compat,
        d0_result,
        d0_receipt,
        target_receipt,
        old_closure,
        lane_receipt,
    )
    if (
        binding != stored.get("approval_binding")
        or binding_sha256 != EXPECTED_BINDING
    ):
        raise FinalizerError("P3.37 original approval binding cannot be rederived")
    expected_trace = live._p300_usb_binding_value(  # noqa: SLF001
        ROOT, compat, RUN_DIR, EXPECTED_BINDING
    )
    trace_path = RUN_DIR / "p300-usb-trace-binding.json"
    if (
        expected_trace is None
        or stored.get("p300_usb_trace_binding")
        != live._receipt(trace_path, "P3.00 USB trace binding")  # noqa: SLF001
        or live._read_json(trace_path, "P3.00 USB trace binding")  # noqa: SLF001
        != expected_trace
    ):
        raise FinalizerError("P3.37 trace binding differs")
    live.p300_usb_trace.verify_binding(expected_trace)
    return prepared


def _final_health(live: Any, prepared: Any) -> dict[str, Any]:
    raw = RUN_DIR / "raw-adb"
    properties_raw, _ = BASE._raw_handle(  # noqa: SLF001
        live, raw / "0025-adb-read-only-shell.capture.json", 64 * 1024
    )
    root_raw, _ = BASE._raw_handle(  # noqa: SLF001
        live, raw / "0026-adb-read-only-shell.capture.json", 64 * 1024
    )
    inventory_raw, _ = BASE._raw_handle(  # noqa: SLF001
        live, raw / "0029-adb-devices.capture.json", 64 * 1024
    )
    topology_raw, _ = BASE._raw_handle(  # noqa: SLF001
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
    rows = [
        json.loads(line)
        for line in BASE._stable(  # noqa: SLF001
            EXACT_FILES["endpoint_journal"][0], "endpoint journal", 64 * 1024
        ).splitlines()
        if line
    ]
    if (
        len(rows) != 22
        or [row.get("sequence") for row in rows] != list(range(22))
        or rows[-1].get("record") != "odin_snapshot"
        or rows[-1].get("live_devices") != []
        or rows[-1].get("stale_devices") != []
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
        payload, capture = BASE._raw_handle(  # noqa: SLF001
            live, receipt_path, live.MAX_OBSERVER_BYTES
        )
        destination = RUN_DIR / f"rollback-observer-{index}.bin"
        if payload != BASE._stable(destination, destination.name):  # noqa: SLF001
            raise FinalizerError("retained rollback observer bytes differ")
        elapsed = capture["elapsed_msec"] / 1000
        if not 0 < elapsed <= 185:
            raise FinalizerError("retained rollback observer duration differs")
        capture_payload = BASE._stable(  # noqa: SLF001
            receipt_path, receipt_path.name, 64 * 1024
        )
        receipts.append(
            {
                "path": str(destination),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "raw_capture": {
                    "path": str(receipt_path),
                    "size": len(capture_payload),
                    "sha256": hashlib.sha256(capture_payload).hexdigest(),
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
        raise FinalizerError("retained P3.37 stock evidence cannot be classified") from exc
    if (
        classified.get("overlay_contract_id")
        != live.typed_evidence.P337_STOCK_OVERLAY_CONTRACT_ID
        or classified.get("classification") != "AMBIGUOUS_INTEGRITY_FAILURE"
        or classified.get("proof_class") != "NO_PROOF_OBSERVER"
        or classified.get("accepted") is not False
        or classified.get("p337_stock") != []
        or projection.get("proof_class") != "NO_PROOF_OBSERVER"
        or projection.get("candidate_success") is not False
    ):
        raise FinalizerError("retained P3.37 stock projection differs")
    return {
        "reads": receipts,
        "byte_identical": True,
        "bytes": len(payloads[0]),
        "sha256": hashlib.sha256(payloads[0]).hexdigest(),
        "exact_marker_count": classified["exact_count"],
        "marker_family_count": classified["family_count"],
        "classification": classified,
        "accepted": False,
        "p337_stock": projection,
    }


def _reconstruct_final(live: Any, core: Any, prepared: Any) -> dict[str, Any]:
    return {
        "health": _final_health(live, prepared),
        "target_evidence_sha256": core.json_sha256(
            {
                "serial": hashlib.sha256(
                    prepared.private_target["serial"].encode()
                ).hexdigest(),
                "topology": hashlib.sha256(
                    prepared.private_target["topology"].encode()
                ).hexdigest(),
            }
        ),
        "observer": _final_observer(live, prepared),
        "rollback_verified": True,
    }


def _repair_state_projection(
    live: Any, prepared: Any, state: dict[str, Any], final: dict[str, Any]
) -> dict[str, Any]:
    durable = live._reopen_candidate_observation(prepared)  # noqa: SLF001
    guard = live._reopen_candidate_guard_release(prepared)  # noqa: SLF001
    repaired = dict(state)
    repaired.update(
        {
            "download_endpoint_absent": durable["download_endpoint_absent"],
            "candidate_observer_classification": durable["classification"],
            "candidate_observer_accepted": durable["accepted"],
            "candidate_observer_receipt_sha256": durable["receipt_sha256"],
            "candidate_observer_guard_release_status": guard["status"],
            "candidate_observer_guard_released": guard["released"],
            "candidate_observer_guard_warning": guard["warning"],
            "candidate_observer_guard_release_receipt_sha256": guard[
                "receipt_sha256"
            ],
        }
    )
    repaired.update(live._p337_proof_state(durable))  # noqa: SLF001
    repaired.update(
        {
            "preauth_diagnostics": durable["preauth_diagnostics"],
            "rng_eagain_retries": durable["rng_eagain_retries"],
            "partial_sessions": durable["partial_sessions"],
            "p337_authenticated_attended_resident": durable[
                "p337_authenticated_attended_resident"
            ],
            "final_verified": True,
            "marker_accepted": False,
            "final_evidence": final,
            "p337_proof_class": "NO_PROOF_OBSERVER",
            "p337_stock": final["observer"]["p337_stock"],
        }
    )
    live._save_candidate_arrival_proof(prepared, repaired)  # noqa: SLF001
    live._validate_candidate_observer_state(prepared, repaired)  # noqa: SLF001
    live._validate_final_observer(prepared, repaired)  # noqa: SLF001
    return repaired


def _context() -> tuple[Any, Any, Any, Any, dict[str, Any], dict[str, Any]]:
    if RUN_DIR.is_symlink() or RUN_DIR.resolve(strict=True) != RUN_DIR.absolute():
        raise FinalizerError("exact P3.37 run directory is indirect")
    live, core = _load_runtime()
    prepared = _load_prepared(live, core)
    journal = core.Journal(TRANSACTION, EXPECTED_BINDING)
    if journal.state() not in {"ROLLBACK_FLASHED", "HEALTH_VERIFIED", "CLOSED"}:
        raise FinalizerError("P3.37 journal is not at a post-rollback cut")
    records = journal.records()
    if len(records) < 15 or records[13].get("state") != "ROLLBACK_FLASHED":
        raise FinalizerError("P3.37 rollback transition differs")
    for kind in ("candidate", "rollback"):
        result = live._validate_transfer_result(prepared, kind, 1)  # noqa: SLF001
        if result is None or result.get("classification") != "odin_transfer_completed":
            raise FinalizerError(f"P3.37 {kind} transfer differs")
        if any(RUN_DIR.glob(f"{kind}-attempt-02.*")):
            raise FinalizerError("a second transfer attempt exists")
    state = live._state(prepared)  # noqa: SLF001
    final = _reconstruct_final(live, core, prepared)
    if state.get("final_verified") is not True:
        state_payload = BASE._stable(  # noqa: SLF001
            STATE_PATH, "P3.37 pre-final state", 64 * 1024
        )
        head_payload = BASE._stable(  # noqa: SLF001
            TRANSACTION / "journal-head.json", "P3.37 pre-final journal head"
        )
        if (
            journal.state() != "ROLLBACK_FLASHED"
            or (len(state_payload), hashlib.sha256(state_payload).hexdigest())
            != EXPECTED_PRE_STATE
            or (len(head_payload), hashlib.sha256(head_payload).hexdigest())
            != EXPECTED_PRE_HEAD
            or state.get("rollback_completed") is not True
            or state.get("candidate_completed") is not True
        ):
            raise FinalizerError("P3.37 pre-final cut differs")
        repaired = _repair_state_projection(live, prepared, state, final)
    else:
        repaired = state
        if (
            state.get("final_evidence") != final
            or state.get("p337_stock") != final["observer"]["p337_stock"]
            or state.get("p337_proof_class") != "NO_PROOF_OBSERVER"
        ):
            raise FinalizerError("P3.37 finalized evidence differs")
        live._validate_candidate_observer_state(prepared, repaired)  # noqa: SLF001
        live._validate_final_observer(prepared, repaired)  # noqa: SLF001
    return live, core, prepared, journal, repaired, final


def _terminal_result(live: Any, prepared: Any, journal: Any) -> dict[str, Any]:
    verdict, outcome = live._closed_terminal_classification(prepared)  # noqa: SLF001
    if (
        verdict != "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
        or outcome != EXPECTED_NO_PROOF_OUTCOME
    ):
        raise FinalizerError("P3.37 terminal classification differs")
    if RESULT_PATH.exists():
        value = json.loads(BASE._stable(RESULT_PATH, "P3.37 terminal result"))  # noqa: SLF001
        live.validate_live_result(value, prepared)
        return value
    return live._result(prepared, journal, verdict, outcome, False)  # noqa: SLF001


def _close(
    live: Any, prepared: Any, journal: Any, repaired: dict[str, Any]
) -> dict[str, Any]:
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
        raise FinalizerError("P3.37 journal did not close")
    return _terminal_result(live, prepared, journal)


def finalize(*, audit_only: bool) -> dict[str, Any]:
    if audit_only:
        _live, _core, _prepared, journal, _repaired, final = _context()
        result_present = RESULT_PATH.exists()
        if journal.state() == "CLOSED":
            _terminal_result(_live, _prepared, journal)
        elif result_present:
            raise FinalizerError("P3.37 result precedes CLOSED")
        return {
            "schema": SCHEMA,
            "verdict": AUDIT_VERDICT,
            "journal_state": journal.state(),
            "candidate_transfer_count": 1,
            "rollback_transfer_count": 1,
            "candidate_open_read_errno": -71,
            "rollback_verified_from_retained_evidence": final["rollback_verified"],
            "stock_proof_class": final["observer"]["p337_stock"]["proof_class"],
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
    with _load_runtime()[0].odin_core.transaction_session(RUN_DIR / "f1-session"):
        live, _core, prepared, journal, repaired, _final = _context()
        result = _close(live, prepared, journal, repaired)
    if (
        result.get("current_state") != "CLOSED"
        or result.get("verdict") != "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
        or result.get("outcome_class") != EXPECTED_NO_PROOF_OUTCOME
        or result.get("recovery_required") is not False
    ):
        raise FinalizerError("P3.37 final terminal differs")
    result_payload = BASE._stable(RESULT_PATH, "P3.37 terminal result")  # noqa: SLF001
    state_payload = BASE._stable(STATE_PATH, "P3.37 terminal state")  # noqa: SLF001
    return {
        "schema": SCHEMA,
        "verdict": FINALIZE_VERDICT,
        "journal_state": "CLOSED",
        "result_verdict": result["verdict"],
        "outcome_class": result["outcome_class"],
        "candidate_transfer_count": 1,
        "rollback_transfer_count": 1,
        "candidate_open_read_errno": -71,
        "rollback_verified_from_retained_evidence": True,
        "result": {
            "path": str(RESULT_PATH),
            "size": len(result_payload),
            "sha256": hashlib.sha256(result_payload).hexdigest(),
        },
        "state": {
            "path": str(STATE_PATH),
            "size": len(state_payload),
            "sha256": hashlib.sha256(state_payload).hexdigest(),
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
