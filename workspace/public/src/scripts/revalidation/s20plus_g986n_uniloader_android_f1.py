#!/usr/bin/env python3
"""An exact S20+ UniLoader Android compatibility transaction."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import s20plus_g986n_twrp_observe_source_view_v1 as source_view


ACTIVE = True
SCRIPT = Path(__file__).resolve()
ROOT = source_view.ROOT
PRIVATE = source_view.PRIVATE
RUNS = PRIVATE / "runs"
RUN_ROOT = RUNS / "s20plus-g986n-uniloader-android-f1"
REGISTRY_ROOT = PRIVATE / "consumed-candidate-registry-v1"
GUARD = source_view.RUN_ROOT / "active-action.json"
CAGE_ROOT = Path("/sys/fs/cgroup")
ACTIVATION = RUN_ROOT / "activation-v2.json"
P2_RUN = RUNS / "s20plus-g986n-p2-ram-snapshot-f1/run-1790103602144341728"
P2_CLOSE = PRIVATE / "outputs/s20plus_g986n/p2_live_close_2026-09-23/close.json"
P2_CLOSE_SHA = "073d52b8eb3bcd7597ccfb905523a1c5362d1d9f6a1b694217a208c1284a4b6d"
TWRP_BASELINE = source_view.RUN_ROOT / "twrp-baseline-1795353624525085969/baseline.json"
TWRP_BASELINE_SHA = "6755cdf623b398334ac3c9218df3192b61beeb742a442d7d5e9ca234c714f4fd"
SCRIPTS = SCRIPT.parent
P0 = SCRIPTS / "s20plus_g986n_p0_pid1_odin_f1.py"
P0_SHA = "c9486ec43ad5f0ed6acc2b34436a9d1be7007e9be9d81bbdcd17c2e0d423d6ef"
P0_ENGINE_SHA = "82ec4cee48c3a39aa8dc4de6136e8fda3fbefe88d4821a71bdb0df55d2a17c2a"
PROFILE = "s20plus-g986n-uniloader-android-v1"
PAIR = PRIVATE / "outputs/s20plus-y2q-uniloader-h0-20261122.sgJEum/physical-prep-2/artifact-pair.json"
PAIR_SHA = "48ce3ac3e5a574859088e9bd904c6f23c22e2c9f7a79470fa0749447e10b5559"
MARKER_SOURCE = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0/uniloader_android_observation.py"
MARKER_SHA = "750a2a87abbfd153e7aa2fa3859efc2e665bf64d129b2d7cb7984e76fdd6452a"
BUILDER = MARKER_SOURCE.with_name("build_uniloader_android.py")
BUILDER_SHA = "ef1c86f60864a4a58bf9b180e461653c43fc165a96b69224b53b81a311b9926e"
EXIT_SOURCE = SCRIPTS / "s20plus_g986n_download_exit_d1.py"
EXIT_SOURCE_SHA = "72411a9e7983849dca0cbb3775f4f070c9642b9c8efb929fd519826e954b336a"
TARGET = {"model": "SM-G986N", "device": "y2q", "product": "y2qksx", "incremental": "G986NKSS8IYC2"}
CONTRACT = ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
TEST_SOURCE = ROOT / "tests/test_s20plus_g986n_uniloader_android_f1.py"
HEADING = "## S20+ UniLoader Android compatibility attended F1\n"
REVIEW_PASS = {"verdict": "PASS_GO", "high": 0, "medium": 0, "low": 0}
PHASES = {
    "preflight": ("preflight-root", "ABSENT"),
    "candidate": ("candidate-android-root", "MATCH"),
    "final": ("final-root", "ABSENT"),
}


class Stop(RuntimeError):
    pass


def require(condition, reason):
    if not condition:
        raise Stop(reason)


def receipt(path):
    return source_view.file_receipt(source_view.read_file(path))


def strict_private(path, *, compact=False):
    raw = source_view.read_file(path, mode=0o400)
    value = json.loads(raw)
    formatting = {"separators": (",", ":")} if compact else {"indent": 2}
    canonical = (json.dumps(value, sort_keys=True, allow_nan=False, **formatting) + "\n").encode()
    require(type(value) is dict and canonical == raw, "private record is not canonical")
    return value


def retained_runtime_source():
    raw = source_view.read_file(P0)
    require(source_view.file_receipt(raw)["sha256"] == P0_SHA, "retained runtime differs")
    replacements = (
        (b'"_s20plus_g986n_p1_pid1_runtime"', b'"_s20plus_g986n_uniloader_runtime"'),
        (b'"_p1_configure"', b'"_uniloader_configure"'),
        (b'"workspace/public/src/scripts/revalidation/s20plus_g986n_p1_pid1_witness_f1.py"',
         b'"workspace/public/src/scripts/revalidation/s20plus_g986n_uniloader_android_f1.py"'),
        (b"REGISTRY_SIZE = 54_571", b"REGISTRY_SIZE = 60_232"),
        (b"c87b7d81c343221742f3577735c09d9da5ffbff44d1ad1d1683b2d81061f0a8b",
         b"e67d75137469f0435c3b9e8780c1b81d8bd5fda2d8142e03499d09784443cead"),
    )
    for (before, after), count in zip(replacements, (1, 2, 1, 1, 1), strict=True):
        require(raw.count(before) == count, "retained profile hook differs")
        raw = raw.replace(before, after)
    return raw


def effect_profile():
    return {
        "partition": "boot", "candidate_attempt_maximum": 1, "rollback_attempt_maximum": 1,
        "candidate_marker": "MATCH", "original_marker": "ABSENT",
        "preflight_and_terminal": "exact-rooted-Magisk-Android",
        "attendance_required": True, "approval_seconds": 900,
        "candidate_and_rollback_replay": False,
    }


def common_authority(data):
    lines = data.decode().splitlines()
    for index, line in enumerate(lines):
        if line.startswith("| Samsung Galaxy"):
            cells = line.strip("|").split("|")
            require(len(cells) == 4, "target registry shape differs")
            lines[index] = "|" + "|".join(cells[:3]) + "| <LIVE_STATUS> |"
    return source_view.file_receipt("\n".join(lines).encode())


def review_identity():
    view = source_view.view_receipt()
    data = source_view.read_file(SCRIPT)
    dormant, count = re.subn(rb"^ACTIVE = (True|False)$", b"ACTIVE = False", data, flags=re.M)
    require(count == 1, "activation literal differs")
    active = dormant.replace(b"\nACTIVE = False\n", b"\nACTIVE = True\n", 1)
    authority = source_view.read_file(CONTRACT).decode()
    require(authority.count(HEADING) == 1, "target authority section differs")
    section = authority.split(HEADING, 1)[1].split("\n## ", 1)[0]
    common = ROOT / "AGENTS.md"
    details = ROOT / "docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md"
    common_bytes = source_view.read_file(common)
    pin = re.findall(rb"The incorporated details have SHA-256:\s*`([a-f0-9]{64})`", common_bytes)
    require(pin == [receipt(details)["sha256"].encode()], "common details pin differs")
    docs = (details, ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md",
            ROOT / "docs/operations/DEVICE_ACTION_PROCESS_V2.md")
    return {
        "schema": "s20plus_g986n_uniloader_android_f1_review_v1", "target": TARGET,
        "owner_dormant": source_view.file_receipt(dormant),
        "owner_active": source_view.file_receipt(active),
        "runtime": source_view.file_receipt(retained_runtime_source()),
        "engine": P0_ENGINE_SHA, "source_view": view, "marker_source": receipt(MARKER_SOURCE),
        "builder": receipt(BUILDER),
        "tests": receipt(TEST_SOURCE),
        "physical_exit_source": receipt(EXIT_SOURCE),
        "twrp_identity_baseline": TWRP_BASELINE_SHA,
        "retained_physical_download_proof": P2_CLOSE_SHA,
        "pair_sha256": PAIR_SHA, "scope": effect_profile(), "authority": {
            "section": source_view.file_receipt(section.encode()),
            "common": common_authority(common_bytes),
            "documents": {str(path.relative_to(ROOT)): receipt(path) for path in docs},
        },
    }


def require_active():
    require(ACTIVE is True, "STOP_UNILOADER_F1_NOT_ACTIVE")
    expected = review_identity()
    record = strict_private(ACTIVATION)
    require(record == {"identity": expected, "review": REVIEW_PASS},
            "reviewed activation differs")
    require(receipt(SCRIPT) == expected["owner_active"], "active owner bytes differ")
    runtime._assert_profile_installed()


def load_exact(path, name, raw):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def read_pair():
    data = source_view.read_file(PAIR)
    require(source_view.file_receipt(data)["sha256"] == PAIR_SHA, "AP pair receipt differs")
    value = json.loads(data)
    require(value["target"] == TARGET and value["device_commands"] == 0
            and value["live_prepared"] is False, "AP pair is not exact H0 evidence")
    for role in ("candidate", "rollback"):
        require(value[role]["only_member"]["name"] == "boot.img.lz4", "non-boot AP member")
    return value


def retained_physical_recovery():
    close_data = source_view.read_file(P2_CLOSE, mode=0o400)
    close_pin = source_view.file_receipt(close_data)
    require(close_pin["sha256"] == P2_CLOSE_SHA, "retained physical close differs")
    close = json.loads(close_data)
    require(close["schema"] == "s20plus_g986n_p2_live_close_v1"
            and close["run"] == str(P2_RUN.relative_to(ROOT)) and close["guard_absent"] is True
            and close["physical_download_and_twrp_return_completed"] is True,
            "retained physical run was not closed")

    def historical(name):
        path = P2_RUN / name
        raw = source_view.read_file(path, mode=0o400)
        expected = close["run_files"][name]
        require(expected == {"mode": "0o400", "path": str(path.relative_to(ROOT)), **source_view.file_receipt(raw)},
                "retained physical journal input differs")
        return json.loads(raw)

    def historical_capture(label, maximum):
        path = P2_RUN / (label + ".capture.json")
        historical(path.name)
        handle = engine.raw_capture.load_handle(path)
        stdout = engine.raw_capture.read_stdout(handle, maximum=maximum)
        stderr = engine.raw_capture.read_stderr(handle, maximum=maximum)
        for name, data in ((handle.stdout_path.name, stdout), (handle.stderr_path.name, stderr)):
            expected = close["run_files"][name]
            require(expected == {"mode": "0o400", "path": str((P2_RUN / name).relative_to(ROOT)),
                                 **source_view.file_receipt(data)}, "retained capture stream differs")
        return handle, stdout, stderr

    prepared = historical("prepared.json")
    baseline = historical("physical-rollback-baseline.json")
    arm = historical("physical-rollback-intent.json")
    confirmation = historical("physical-confirmation-intent.json")
    observation = historical("physical-observation-intent.json")
    arrival = historical("physical-rollback-arrival.json")
    intent = historical("rollback-intent.json")
    result = historical("rollback-result.json")
    cage = historical("rollback-cage-quiescent.json")
    final = historical("final-health.json")
    terminal = historical("terminal.json")
    binding = prepared["binding"]
    key = engine.digest(binding)
    require(all(record["binding_sha256"] == key for record in
                (prepared, arm, confirmation, observation, arrival, intent, result, final, terminal))
            and baseline["endpoint_count"] == 0 and arm["baseline"] == baseline
            and arm["baseline_sha256"] == observation["baseline_sha256"] == arrival["baseline_sha256"]
            == engine.digest(baseline)
            and confirmation["arm_sha256"] == engine.digest(arm)
            and confirmation["no_replay"] is True and observation["no_replay"] is True
            and arm["branch"] == "attended-entry-required" and arrival["branch"] == "attended-entry"
            and intent["no_replay"] is True and intent["attempt"] == 1
            and result["replay_permitted"] is False and result["host_process_quiescence_proved"] is True
            and cage["empty_and_removed"] is True and cage["cage_binding_sha256"]
            == engine.digest(intent["process_cage"]),
            "retained physical entry/rollback effect chain differs")

    arrival_endpoint = exit_d1.validate_endpoint(arrival["endpoint"])
    transfer_endpoint = exit_d1.validate_endpoint(intent["endpoint"])
    for label, expected_listing, listing_sha in (
            ("p0-odin-listing-0091", [], baseline["listing_sha256"]),
            ("p0-odin-listing-0099", [arrival_endpoint["device"]], arrival["arrival_listing_sha256"])):
        handle, stdout, stderr = historical_capture(label, engine.MAX_ADB_BYTES)
        prefix = engine.ODIN_CAGE_ENTRY_MARKER
        listing = stdout[len(prefix):]
        require(engine.raw_dispatch_proved(handle, stderr) and stdout.startswith(prefix)
                and hashlib.sha256(listing).hexdigest() == listing_sha
                and engine.parse_download_listing(listing.decode("utf-8", "strict")) == expected_listing,
                "retained raw physical Download listing differs")
    twrp = source_view.read_file(TWRP_BASELINE, mode=0o400)
    require(source_view.file_receipt(twrp)["sha256"] == TWRP_BASELINE_SHA,
            "retained TWRP baseline bytes differ")
    known = json.loads(twrp)["recovery_health"]["recovery"]
    before, after = binding["preflight"], final["health"]
    require(engine.same_download_session(arrival_endpoint, transfer_endpoint)
            and before["target"] == after["target"] == binding["target"] == TARGET
            and before["serial_sha256"] == after["serial_sha256"] == known["serial_sha256"]
            and before["topology_sha256"] == after["topology_sha256"] == arrival_endpoint["topology_sha256"]
            and before["boot_id_sha256"] != after["boot_id_sha256"]
            and final["rollback_outcome_proved"] is True and final["rollback_transfer_completed"] is True
            and final["twrp_recovery_healthy"] is True and terminal == close["terminal"]
            and terminal["rollback_transfer_completed"] is True and terminal["rollback_attempts"] == 1
            and terminal["rollback_replay_permitted"] is False
            and terminal["verdict"] == "NO_PROOF_NATIVE_PID1_RETURNED_TWRP_HEALTHY",
            "retained physical target or terminal differs")

    prior_rollback = binding["closure"]["rollback"]
    expected_ap = pair["rollback"]["ap"]
    transport = result["receipt"]
    require(prior_rollback["ap"] == transport["ap"] == expected_ap
            and intent["ap_sha256"] == expected_ap["sha256"]
            and transport["endpoint_path_sha256"] == transfer_endpoint["endpoint_sha256"]
            and transport["endpoint_pre_identity"] == transfer_endpoint["endpoint_identity"]
            and transport["command_shape"] == ["odin4", "-a", "AP.tar.md5", "-d", "USBFS"]
            and prior_rollback["decoded_boot"] == {
                **pair["rollback"]["decoded_boot"], "binding": "exact-member-plus-reviewed-manifest"},
            "retained physical recovery used a different rollback")
    capture_path = P2_RUN / "rollback-transfer.capture.json"
    require(transport["raw_capture_receipt"] == {"path": str(capture_path), **receipt(capture_path)},
            "retained physical rollback capture differs")
    handle, stdout, stderr = historical_capture("rollback-transfer", engine.MAX_RAW_BYTES)
    for stream, data in (("stdout", stdout), ("stderr", stderr)):
        require(result[stream + "_sha256"] == hashlib.sha256(data).hexdigest(),
                "retained rollback stream differs")
    require(result["classification"] == engine.classify_odin_capture(handle, stdout, stderr)
            == "odin_transfer_completed", "retained physical rollback transfer is unproved")
    return {"source": "closed_P2_physical_download", "close": close_pin, "terminal": receipt(P2_RUN / "terminal.json"),
            "original_ap_sha256": expected_ap["sha256"], "target": TARGET,
            "serial_sha256": after["serial_sha256"], "topology_sha256": after["topology_sha256"]}


def check_recovery_identity(health, recovery):
    require(health["target"] == recovery["target"]
            and all(health[key] == recovery[key] for key in marker.IDENTITY[:2]),
            "current rooted Android does not match the proved physical recovery path")


def wait_bound_download(baseline, timeout=None):
    arrival = original_wait(baseline, engine.DOWNLOAD_ARRIVAL_SECONDS if timeout is None else timeout)
    lease = runtime._require_live_transaction()
    if arrival is not None and lease["entrypoint"] == "prepare":
        run = Path(lease["run_dir"])
        preflight = engine.read_json(run / "preflight.json", "current Android preflight")
        require(arrival["endpoint"]["topology_sha256"] == preflight["topology_sha256"],
                "current Download arrival differs from the proved physical recovery topology")
    return arrival

def validate_manifest():
    read_pair()
    return {"path": str(PAIR), **receipt(PAIR)}


def validate_host_closure(*, include_candidate=True, include_rollback=True):
    try:
        transaction = runtime._require_live_transaction()
    except runtime.P0F1Error:
        transaction = None
    if transaction is not None:
        require_new_effect_owner_clear()
    value = runtime._ENGINE_HOST_VALIDATION_CALL(
        include_candidate=include_candidate, include_rollback=include_rollback)
    value["uniloader"] = {"capability": review_identity(),
                        "registry": runtime._registry_authority()}
    if ACTIVE:
        require_active()
        value["uniloader"]["physical_recovery"] = retained_physical_recovery()
    return value


def transfer_receipt(run, phase, binding_sha256):
    kind = "candidate" if phase == "candidate" else "rollback"
    result = engine.read_json(run / f"{kind}-result.json", f"UniLoader {kind} transfer")
    engine._validate_transfer_outcome(run, result, kind, binding_sha256)
    require(result["classification"] == "odin_transfer_completed", f"{kind} transfer is unproved")
    return engine.digest(result)


def phase_files(phase):
    prefix = f"uniloader-{phase}"
    return (prefix + "-marker", prefix + "-after-root",
            prefix + "-marker-intent.json", prefix + "-marker-evidence.json")


def capture_options(name):
    return {"timeout": marker.READ_SECONDS, "stdout_maximum": marker.STDOUT_MAXIMUM,
            "stderr_maximum": marker.STDERR_MAXIMUM, "stdout_name": name + ".stdout",
            "stderr_name": name + ".stderr"}


def require_marker_capture_order(phase, nodes):
    marker_name, after, intent, evidence = phase_files(phase)
    raw = {marker_name + suffix for suffix in (".capture.json", ".stdout", ".stderr")}
    post = {after + suffix for suffix in (".capture.json", ".stdout", ".stderr")}
    prerequisite = {"candidate": "candidate-observation-intent.json", "final": "final-health.json"}
    if intent in nodes and phase in prerequisite:
        require(prerequisite[phase] in nodes, "marker intent escaped its phase")
    if nodes & (raw | post | {evidence}):
        require(intent in nodes, "marker capture lacks its durable intent")
    if evidence in nodes:
        require(raw | post <= nodes, "marker evidence lacks its raw inputs")


def phase_intent(run, phase, before, prepared):
    value = {"schema": "s20plus_g986n_uniloader_marker_intent_v1",
             "phase": phase, "before": before,
             "binding_sha256": None, "transfer_sha256": None}
    if prepared is not None:
        value["binding_sha256"] = prepared["binding_sha256"]
        value["transfer_sha256"] = transfer_receipt(run, phase, prepared["binding_sha256"])
    return value


def marker_raw(run, name):
    capture = engine.raw_capture
    handle = capture.load_handle(run / (name + ".capture.json"))
    clean = not handle.timed_out and not handle.output_exceeded and not handle.producer_error_type
    raw = (handle.returncode if clean else None,
           capture.read_stdout(handle, maximum=marker.STDOUT_MAXIMUM),
           capture.read_stderr(handle, maximum=marker.STDERR_MAXIMUM))
    return raw, engine.digest({"receipt": receipt(handle.receipt_path),
                               "stdout": dict(handle.stdout), "stderr": dict(handle.stderr)})


def validate_root(run, health, prefix):
    engine._validate_resident_health_receipt(run, health, "UniLoader Magisk root", prefix)
    handle = engine.raw_capture.load_handle(Path(health["root_capture"]["path"]))
    require(handle.returncode == 0 and not handle.timed_out and not handle.output_exceeded
            and handle.producer_error_type is None, "root capture producer failed")


def marker_result(run, phase, before, after, prepared):
    name, after_root, intent_name, _ = phase_files(phase)
    before_root, _ = PHASES[phase]
    validate_root(run, before, before_root)
    validate_root(run, after, after_root)
    if phase == "preflight":
        check_recovery_identity(before, retained_physical_recovery())
        start = {key: before[key] for key in marker.IDENTITY[:2]}
        prior = ()
    else:
        start = prepared["binding"]["preflight"]
        prior = ()
        if phase == "final":
            observation = engine.read_json(run / "candidate-observation.json", "candidate observation")
            checked = observation.get("resident_health", {})
            prior = (checked.get("boot_id_sha256"), observation.get("boot_id_sha256"),
                     before_candidate_boot(run))
    intent = phase_intent(run, phase, before, prepared)
    require(engine.read_json(run / intent_name, "UniLoader marker intent") == intent,
            "marker intent differs")
    raw, raw_sha = marker_raw(run, name)
    status = marker.observe_marker(before, after, raw, expected_marker_sha256=pair["marker"]["sha256_with_nul"],
                                   preflight=start, prior_boots=prior)
    return {"intent_sha256": engine.digest(intent), "raw_sha256": raw_sha,
            "after": after, "marker_status": status}


def before_candidate_boot(run):
    path = run / phase_files("candidate")[2]
    if not path.exists():
        return None
    before = engine.read_json(path, "candidate marker intent")["before"]
    validate_root(run, before, PHASES["candidate"][0])
    return before["boot_id_sha256"]


def acquire_marker(run, phase, before, serial, prepared):
    name, after_root, intent_name, evidence_name = phase_files(phase)
    intent_path, evidence_path = run / intent_name, run / evidence_name
    if evidence_path.exists():
        evidence = engine.read_json(evidence_path, "UniLoader marker evidence")
        require(evidence == marker_result(run, phase, before, evidence["after"], prepared),
                "marker claim is not raw-derived")
        return evidence
    require(not os.path.lexists(intent_path), "one-shot marker observation was interrupted")
    validate_root(run, before, PHASES[phase][0])
    engine.durable_json(intent_path, phase_intent(run, phase, before, prepared))
    engine.raw_capture.acquire_command(marker.marker_argv(serial), run, name, **capture_options(name))
    after, selected = original_health(run, after_root, before["serial_sha256"])
    require(selected == serial, "marker health selected another endpoint")
    value = marker_result(run, phase, before, after, prepared)
    engine.durable_json(evidence_path, value)
    return value


def allow_marker(command, run, name, kwargs):
    phases = {phase_files(phase)[0]: phase for phase in PHASES}
    if name not in phases:
        return False
    phase = phases[name]
    _, _, intent_name, evidence_name = phase_files(phase)
    require_active()
    lease = runtime._require_live_transaction()
    require(lease["run_dir"] == str(run) and command == marker.marker_argv(command[2])
            and kwargs == capture_options(name) and not os.path.lexists(run / evidence_name),
            "marker capture escaped the fixed read")
    intent = engine.read_json(run / intent_name, "UniLoader marker intent")
    require(intent["phase"] == phase, "marker phase differs")
    if phase != "preflight":
        prepared = engine.read_json(run / "prepared.json", "prepared binding")
        require(intent["binding_sha256"] == prepared["binding_sha256"]
                and intent["transfer_sha256"] == transfer_receipt(run, phase, prepared["binding_sha256"]),
                "marker read lacks its proved transfer")
        required = "candidate-observation-intent.json" if phase == "candidate" else "final-health.json"
        require((run / required).exists(), "marker read escaped its observation stage")
    else:
        require(not os.path.lexists(run / "initial-download-intent.json"),
                "original marker read after Download intent")
    return True


def resident_health(run, name, expected_serial=None):
    if name == "preflight-root":
        require_new_effect_owner_clear()
    health, serial = original_health(run, name, expected_serial)
    if name == "preflight-root":
        check_recovery_identity(health, retained_physical_recovery())
        result = acquire_marker(run, "preflight", health, serial, None)
        require(result["marker_status"] == "ABSENT", "original FDT baseline is unproved")
    return health, serial


def require_new_effect_owner_clear():
    runtime._require_live_transaction()
    runtime.registry.require_no_f1_owner(ROOT)
    require(not os.path.lexists(ROOT / runtime.registry.RESEARCH_PENDING)
            and not os.path.lexists(source_view.CAMPAIGN_GUARD),
            "another owner has unresolved device control")


def observe_candidate(run, prepared):
    try:
        transfer_receipt(run, "candidate", prepared["binding_sha256"])
        health, serial = candidate_health(run, prepared["binding"]["preflight"])
    except Exception as error:
        return failed_observation(error), None
    try:
        result = acquire_marker(run, "candidate", health, serial, prepared)
        require(result["marker_status"] in {"MATCH", "ABSENT", "DIFFERENT"},
                "candidate marker channel failed")
        return {"environment": "resident-android", "transport_authorized": True,
                "resident_health": health, "claim_verdict": ("PROVED" if result["marker_status"] == "MATCH"
                                                              else "NO_PROOF"),
                "uniloader_marker_sha256": engine.digest(result), "at": engine.utc_now()}, serial
    except Exception as error:
        failure = failed_observation(error)
        failure["boot_id_sha256"] = health["boot_id_sha256"]
        return failure, None


def failed_observation(error):
    return {"environment": "observer-reporting-cut", "transport_authorized": False,
            "claim_verdict": "NO_PROOF", "reason": type(error).__name__, "at": engine.utc_now()}


def candidate_health(run, start):
    deadline = time.monotonic() + engine.RECOVERY_ARRIVAL_SECONDS
    while time.monotonic() < deadline:
        rows = engine.adb_inventory()
        matches = engine.target_adb_rows(rows)
        source_rows = [r for r in rows if hashlib.sha256(r["serial"].encode()).hexdigest()
                       == start["serial_sha256"]]
        if not matches and not source_rows:
            time.sleep(2)
            continue
        require(len(matches) == len(source_rows) == 1 and matches[0] == source_rows[0],
                "candidate ADB identity is ambiguous or changed")
        row = matches[0]
        if row["state"] == "offline":
            time.sleep(2)
            continue
        row = engine.exact_adb_row(rows, start["serial_sha256"], "device")
        serial = row["serial"]
        require(hashlib.sha256(engine.adb_devpath(serial).encode()).hexdigest()
                == start["topology_sha256"], "candidate topology differs")
        argv = [str(engine.ADB), "-s", serial, "exec-out", "sh", "-c", engine.PUBLIC_SNAPSHOT_SCRIPT]
        values = engine._ordered_output(
            engine.base.bounded_command(argv, 20, engine.MAX_ADB_BYTES),
            engine.PUBLIC_SNAPSHOT_KEYS, "UniLoader candidate readiness")
        require(all(values[key] == TARGET[field] for key, field in (
                ("model", "model"), ("device", "device"), ("product_name", "product"),
                ("incremental", "incremental"))) and values["selinux"] == "Enforcing"
                and engine.BOOT_ID_RE.fullmatch(values["boot_id"]) is not None
                and hashlib.sha256(values["boot_id"].encode()).hexdigest() != start["boot_id_sha256"],
                "candidate Android properties changed")
        require(values["boot_completed"] in {"", "0", "1"} and values["bootanim"] in {
                "", "running", "stopped"}, "candidate readiness fields malformed")
        if (values["boot_completed"], values["bootanim"]) != ("1", "stopped"):
            time.sleep(2)
            continue
        health, selected = engine.resident_health_once(run, "candidate-android-root", start["serial_sha256"])
        require(health["boot_id_sha256"] != start["boot_id_sha256"], "candidate boot id is stale")
        return health, selected
    raise Stop("candidate Android timed out")


def validate_candidate_observation(run, value, binding_sha256, initial_boot):
    runtime._ENGINE_VALIDATE_CANDIDATE_OBSERVATION(run, value, binding_sha256, initial_boot)
    if value["environment"] == "resident-android":
        prepared = engine.read_json(run / "prepared.json", "prepared binding")
        evidence = verified_marker(run, "candidate", value["resident_health"], prepared)
        expected = "PROVED" if evidence["marker_status"] == "MATCH" else "NO_PROOF"
        require(value["claim_verdict"] == expected
                and value.get("uniloader_marker_sha256") == engine.digest(evidence),
                "candidate marker claim differs")
    else:
        require(value["environment"] == "observer-reporting-cut" and value["claim_verdict"] == "NO_PROOF"
                and value["transport_authorized"] is False, "unsupported candidate observation")


def verified_marker(run, phase, before, prepared):
    evidence = engine.read_json(run / phase_files(phase)[3], "UniLoader marker evidence")
    require(evidence == marker_result(run, phase, before, evidence["after"], prepared),
            "saved marker is not raw-derived")
    return evidence


def checked_terminal(run, prepared, final):
    require(final["rollback_transfer_completed"] is True, "original rollback transfer unproved")
    transfer_receipt(run, "final", prepared["binding_sha256"])
    health = final["health"]
    if not os.path.lexists(run / phase_files("final")[3]):
        serial = validated_current_serial(prepared["binding"]["preflight"], health)
        acquire_marker(run, "final", health, serial, prepared)
    require(verified_marker(run, "final", health, prepared)["marker_status"] == "ABSENT",
            "restored Magisk boot did not prove marker absence")
    return original_publish(run, prepared, final)


def validated_current_serial(start, before):
    require(all(before[key] == start[key] for key in marker.IDENTITY[:2])
            and before["boot_id_sha256"] != start["boot_id_sha256"], "original return identity differs")
    row = engine.exact_adb_row(engine.adb_inventory(), start["serial_sha256"], "device")
    require(hashlib.sha256(engine.adb_devpath(row["serial"]).encode()).hexdigest()
            == start["topology_sha256"], "original return topology differs")
    return row["serial"]


def validate_namespace(run):
    inherited_namespace(run)
    nodes = {entry.name for entry in run.iterdir()}
    for phase in PHASES:
        require_marker_capture_order(phase, nodes)
    if "initial-download-intent.json" in nodes:
        preflight = engine.read_json(run / "preflight.json", "UniLoader preflight")
        health = {k: v for k, v in preflight.items() if k not in {"schema", "version"}}
        require(verified_marker(run, "preflight", health, None)["marker_status"] == "ABSENT",
                "Download intent lacks absent original FDT marker")
    if "terminal.json" in nodes and "candidate-intent.json" in nodes:
        prepared = engine.read_json(run / "prepared.json", "prepared binding")
        final = engine.read_json(run / "final-health.json", "original final health")
        require(final["rollback_transfer_completed"] is True
                and verified_marker(run, "final", final["health"], prepared)["marker_status"] == "ABSENT",
                "terminal lacks proved original Magisk and absent FDT marker")


def terminal_verdict(classification, claim, rollback):
    passed = classification == "odin_transfer_completed" and claim == "PROVED" and rollback is True
    return ("PROVED_UNILOADER_MAGISK_FDT_AND_ORIGINAL_ROOT_RETURN" if passed
            else "NO_PROOF_UNILOADER_ORIGINAL_ROOT_RETURNED", passed)


def _configure_runtime(module):
    global runtime, engine, original_health, original_publish, original_wait, inherited_namespace
    runtime, engine, inherited_namespace = module, module.engine, module.validate_namespace
    original_health, original_publish = engine.resident_health_once, engine.publish_terminal_from_final
    original_wait = engine.wait_download
    candidate = pair["candidate"]
    values = {"VERSION": PROFILE, "RUN_ROOT": RUN_ROOT, "CLAIM_ROOT": RUN_ROOT / "consumed-candidates",
              "OUTPUT_ROOT": PAIR.parent, "MANIFEST": PAIR, "MANIFEST_SIZE": 1818,
              "MANIFEST_SHA256": PAIR_SHA, "REGISTRY_MANIFEST_ID": PROFILE, "P0_F1_ACTIVE": ACTIVE,
              "BUILDER_PATH": BUILDER, "BUILDER_SIZE": BUILDER.stat().st_size,
              "BUILDER_SHA256": BUILDER_SHA,
              "APPROVAL_PREFIX": "S20PLUS-G986N-UNILOADER-ANDROID-F1-APPROVE:",
              "PHYSICAL_CONFIRM_PREFIX": "S20PLUS-G986N-UNILOADER-PHYSICAL-ROLLBACK:",
              "PHYSICAL_REBIND_CONFIRM_PREFIX": "S20PLUS-G986N-UNILOADER-PHYSICAL-REENUM:"}
    for stem, item in (("AP", candidate["ap"]), ("MEMBER", candidate["only_member"]),
                       ("BOOT", candidate["decoded_boot"])):
        values[f"CANDIDATE_{stem}_SIZE"] = item["size"]
        values[f"CANDIDATE_{stem}_SHA256"] = item["sha256"]
    values["CANDIDATE_AP"] = Path(candidate["ap"]["path"])
    for key, value in values.items():
        setattr(module, key, value)
    for phase in PHASES:
        name, after, intent, evidence = phase_files(phase)
        module.P0_RUN_NODE_NAMES |= {intent, evidence, *(stem + suffix for stem in (name, after)
                                                         for suffix in (".capture.json", ".stdout", ".stderr"))}
    module.validate_manifest = validate_manifest
    module.validate_host_closure = validate_host_closure
    module.require_active = require_active
    module._profile_read_command_allowed = allow_marker
    module.observe_candidate = observe_candidate
    module.validate_candidate_observation = validate_candidate_observation
    module.validate_namespace = validate_namespace
    module.derive_terminal_verdict = terminal_verdict
    module._BOUND_REGISTRY_APIS["require_no_f1_owner"] = module.registry.require_no_f1_owner
    engine.resident_health_once = resident_health
    engine.wait_download = wait_bound_download
    engine.publish_terminal_from_final = checked_terminal


def enter_runtime():
    global pair, marker, marker_source_pin, exit_d1
    pair = read_pair()
    marker_raw_source = source_view.read_file(MARKER_SOURCE)
    marker_source_pin = source_view.file_receipt(marker_raw_source)
    require(marker_source_pin["sha256"] == MARKER_SHA, "marker implementation differs")
    marker = load_exact(MARKER_SOURCE, "_s20plus_uniloader_marker", marker_raw_source)
    exit_raw = source_view.read_file(EXIT_SOURCE)
    require(source_view.file_receipt(exit_raw)["sha256"] == EXIT_SOURCE_SHA, "Download exit implementation differs")
    exit_d1 = load_exact(EXIT_SOURCE, "_s20plus_uniloader_download_exit", exit_raw)
    require(marker.ADB == "/usr/lib/android-sdk/platform-tools/adb"
            and marker.MARKER_PATH == pair["marker"]["path"]
            and hashlib.sha256(marker.READ_SCRIPT.encode()).hexdigest() == pair["marker"]["read_script_sha256"],
            "fixed marker producer differs")
    name = "_s20plus_g986n_uniloader_runtime"
    module = importlib.util.module_from_spec(importlib.util.spec_from_file_location(name, P0))
    module._uniloader_configure = _configure_runtime
    sys.modules[name] = module
    exec(compile(retained_runtime_source(), str(P0), "exec"), module.__dict__)
    module.install_profile()
    require(module._assert_profile_installed() is None, "retained leased profile differs")
    require(engine.APPROVAL_LIFETIME_SECONDS == 900, "approval lifetime differs")
    return module


def namespace(argv, *, connected):
    view = source_view.command(observe=False)
    prefix = view[:view.index("--chdir")]
    path = Path("/proc/self/cgroup").read_text().strip().removeprefix("0::")
    cgroup = CAGE_ROOT / path.lstrip("/")
    require(path.startswith("/") and cgroup_identity(cgroup), "host has no direct owned cgroup")
    for direct in (RUN_ROOT, REGISTRY_ROOT, source_view.RUN_ROOT, cgroup):
        require(direct.resolve(strict=True) == direct and direct.is_dir(), "namespace input not direct")
        prefix += ["--bind", str(direct), str(direct)]
    if connected:
        prefix += ["--dev-bind", "/dev/bus/usb", "/dev/bus/usb"]
        args = parser().parse_args(argv)
        for retained in recovery_cgroup_mounts(args.run_dir) - {cgroup}:
            prefix += ["--bind", str(retained), str(retained)]
    return [*prefix, "--chdir", str(SCRIPTS), "--", str(source_view.PYTHON), "-E", "-s", "-B",
            "-X", "pycache_prefix=/dev/null", str(SCRIPT), "--in-source-view", *argv]


def cgroup_identity(path):
    require(path != CAGE_ROOT and path.is_relative_to(CAGE_ROOT)
            and path.resolve(strict=True) == path and path.is_dir(), "indirect cgroup")
    info = path.stat()
    require(info.st_uid == os.getuid(), "cgroup owner differs")
    return [info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid]


def recovery_cgroup_mounts(run):
    if run is None or not os.path.lexists(GUARD):
        return set()
    guard = strict_private(GUARD, compact=True)
    run = run.absolute()
    if guard.get("version") != PROFILE or guard.get("run_dir") != str(run):
        return set()
    require(guard == {"schema": "s20plus_g986n_boot_recovery_canary_b0_guard_v1",
                      "version": PROFILE, "run_dir": str(run),
                      "candidate_sha256": read_pair()["candidate"]["ap"]["sha256"],
                      "unresolved": True}, "guarded cgroup owner differs")
    require(run.parent == RUN_ROOT and re.fullmatch(r"run-[0-9]{19}", run.name) is not None
            and run.resolve(strict=True) == run, "invalid guarded cgroup run")
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    boot_sha = hashlib.sha256(boot.encode()).hexdigest()
    mounts = set()
    for node in run.glob("p0-*-cage-*-prepare.json"):
        value = strict_private(node, compact=True)
        kind, generation = value["kind"], value["generation"]
        require(kind in {"candidate", "rollback", "abort-return", "odin-listing"}
                and type(generation) is int and 1 <= generation <= 512
                and node.name == f"p0-{kind}-cage-{generation:04d}-prepare.json"
                and value["schema"] == "s20plus_g986n_p0_process_cage_prepare_v1"
                and value["version"] == PROFILE, "invalid guarded cgroup intent")
        if value["host_boot_id_sha256"] != boot_sha:
            continue  # The existing engine handles previous-host-boot records.
        parent = Path(value["parent"])
        if not os.path.lexists(parent):
            continue  # The inherited core checks whether retained quiescence is sufficient.
        require(cgroup_identity(parent) == value["parent_identity"], "retained cgroup parent changed")
        mounts.add(parent)
    return mounts


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    modes = result.add_mutually_exclusive_group(required=True)
    for mode in ("review-input", "validate-host", "validate-active", "prepare", "execute", "resume",
                 "arm-physical-rollback", "confirm-physical-rollback", "finalize-resident",
                 "abort-pre-candidate"):
        modes.add_argument("--" + mode, action="store_true")
    result.add_argument("--run-dir", type=Path)
    result.add_argument("--approval")
    result.add_argument("--confirmation")
    return result


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    inner = argv[:1] == ["--in-source-view"]
    if inner:
        argv.pop(0)
    args = parser().parse_args(argv)
    if args.review_input:
        print(json.dumps(review_identity(), sort_keys=True))
        return 0
    if not inner:
        source_view.view_receipt()
        return subprocess.run(namespace(argv, connected=not (args.validate_host or args.validate_active)),
                              env=source_view.clean_environment()).returncode
    module = enter_runtime()  # Retained bytes mandatory even on direct inner invocation.
    if args.validate_host:
        closure = validate_host_closure()
        recovery = retained_physical_recovery()
        print(json.dumps({"status": "PASS_UNILOADER_F1_HOST", "closure_sha256": engine.digest(closure),
                          "physical_recovery_source": recovery["source"],
                          "device_commands": 0, "f1_approval": False}, sort_keys=True))
        return 0
    require_active()
    if args.validate_active:
        print(json.dumps({"status": "UNILOADER_ATTENDED_CAPABILITY_ACTIVE",
                          "device_commands": 0, "f1_approval": False}))
        return 0
    if args.prepare:
        require(not os.path.lexists(source_view.CAMPAIGN_GUARD), "S20+ campaign already owns the device")
        run = engine.prepare(args.run_dir)
        prepared = module._read_prepared_for_output(run)
        print(json.dumps({"run_dir": str(run), "approval": prepared["approval_token"]}))
        return 0
    require(args.run_dir is not None, "run-dir required")
    run = args.run_dir.absolute()
    if args.execute:
        result = engine.execute(run, args.approval or "")
    elif args.resume:
        result = engine.resume_run(run)
    elif args.arm_physical_rollback:
        result = engine.arm_physical_rollback(run)
    elif args.confirm_physical_rollback:
        result = engine.confirm_physical_rollback(run, args.confirmation or "")
    elif args.finalize_resident:
        result = engine.finalize_resident(run)
    else:
        result = engine.abort_pre_candidate(run)
    print(json.dumps({key: result[key] for key in
                      ("run_dir", "verdict", "confirmation", "experiment_pass") if key in result},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"verdict": "STOP_UNILOADER_ANDROID_F1", "failure_class": type(exc).__name__,
                          **({"reason": str(exc)} if type(exc) is Stop else {})}))
        raise SystemExit(2)
