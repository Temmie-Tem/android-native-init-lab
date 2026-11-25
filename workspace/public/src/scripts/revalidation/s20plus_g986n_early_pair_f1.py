#!/usr/bin/env python3
"""Attended y2q early-pair transaction with one operator grant."""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
from functools import partial
from types import SimpleNamespace

import s20plus_g986n_twrp_observe_source_view_v1 as view
import s20plus_g986n_mainline_stage_f1 as stage

ACTIVE = True
SCRIPT = Path(__file__).resolve()
OWNER = stage.owner
require = OWNER.require
ROOT = view.ROOT
PROFILE = "s20plus-g986n-early-pair-f1"
RUN_ROOT = view.PRIVATE / "runs" / PROFILE
EXP = view.PRIVATE / "analysis/s20plus-y2q-early-pair-20261126"
PAIR = EXP / "packaged/pair.json"
PAIR_SHA = "b7525b676b07e6e55d06422fd0c2315cdbef0665f9e490bc8679ad012294963e"
CANDIDATE = "5841af93a66fe64ed6ad5d7d744a32e24b61d72887978498d9a9f28564c22c43"
ORIGINAL = "1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2"
REVIEWED_STAGE = "0221e45351c305b00b15e66476d2296754dd675a03a45596fbf2dd2bdd58dce7"
CAL_RUN = (
    view.PRIVATE / "runs/s20plus-g986n-stock-seclog-physical-v1/run-1795633906382643926"
)
HEADING = "## S20+ y2q early handoff pair under one attended approval\n"
PREFIX = "S20PLUS-G986N-EARLY-PAIR-F1-APPROVE:"
READER = EXP / "retained-reader/return_stage.py"
PACKAGER = READER.with_name("package_stage.py")
READER_SHA = "f91b8b437fae3b7a6d97aae3d72dad17bf8ae81254f5bdccb69bd9ea20b600f6"
PACKAGER_SHA = "728e0417d2f99a1a82b73e6169a0f05a57fa4773358f66559d509d12c21e2098"
CAL_SOURCE = SCRIPT.with_name("s20plus_g986n_pmsg_download_calibration_f1.py")
CAL_SHA = "a55c2bee4c9edfb126d4106695bc86b7c78079c1e0a7488f3dca0b8dc781fdb1"
cal = stage.load(CAL_SOURCE, "_early_pair_fixed_health", CAL_SHA)
reader = stage.load(READER, "_early_pair_retained_reader", READER_SHA)
old_configure = stage._configure_runtime
old_scope = stage.scope
old_stage_review = stage.review_identity
old_preflight = stage.preflight
old_make_intent = stage.make_intent
retained_source = stage.runtime_source
CHECK = ROOT / "tests/test_s20plus_g986n_early_pair_f1.py"


def pinned(path, digest):
    raw = view.read_file(path)
    require(hashlib.sha256(raw).hexdigest() == digest, "changed " + path.name)
    return raw


def pair():
    data = json.loads(pinned(PAIR, PAIR_SHA))
    require(
        data["target"] == "SM-G986N/y2q/G986NKSS8IYC2"
        and data["kind"] == "HOST_ONLY_S20PLUS_Y2Q_EARLY_AP_PAIR"
        and data["device_commands"] == 0
        and data["clear_frames_absent_from_both_boots"] is True
        and data["raw"]
        == "8cbb81d0a1d9c4e419f07d4e69bccca64db4e70d8287ff0e73a0c252a6379317",
        "candidate package mismatch",
    )
    for role, digest in (("candidate", CANDIDATE), ("rollback", ORIGINAL)):
        a = data["archives"][role]
        require(
            a["ap"]["sha256"] == digest
            and a["only_member"]["name"] == "boot.img.lz4"
            and a["decoded_boot"]["size"] == 67108864,
            "wrong AP role",
        )
    require(
        Path(data["archives"]["candidate"]["ap"]["path"])
        == PAIR.with_name("AP.tar.md5")
        and hashlib.sha256(
            reader.shell(data["nonce"], "0" * 64, reader.EARLY_STAGES).encode()
        ).hexdigest()
        == data["return_template"],
        "candidate reader or path mismatch",
    )
    pinned(
        reader.FILTER,
        "58c44217e5d523d74c2aa2ec15b1ff3673ec7892daf2c4e14d19e4f7affcdfc8",
    )
    return dict(**data["archives"], nonce=data["nonce"])


def calibrated_identity():
    record = json.loads(
        pinned(
            CAL_RUN / "terminal.json",
            "587d02131ad157beef11bb155525f04f071ba2121861e9ae084923e8c1d50990",
        )
    )
    health = json.loads(
        pinned(
            CAL_RUN / "post-comparison-health.json",
            "fa8d121ff4e6bad2e9af1ceaf6b1755b23ee2ee546bce481ff2378571a9411d9",
        )
    )
    require(
        record["verdict"] == "PROVED_STOCK_SECLOG_RETENTION"
        and record["original_ap_transfers"] == 1
        and record["comparison"]["matches"] == 1
        and health["target"] == OWNER.TARGET,
        "physical control identity differs",
    )
    return {k: health[k] for k in stage.IDENTITY}


def scope():
    return {
        **old_scope(),
        "sites": list(reader.EARLY_STAGES),
        "grant_origin": "healthy-original-Android",
        "one_attended_grant": True,
        "rebind": False,
        "calibrated_source": calibrated_identity(),
    }


def review():
    value = old_stage_review()
    pinned(Path(stage.__file__), REVIEWED_STAGE)
    pinned(PACKAGER, PACKAGER_SHA)
    pinned(
        EXP / "evidence.json",
        "c16d113b5a726f84a68d79141393161f5ec1f23921661b1b898d729b9aa6596b",
    )
    pinned(
        EXP / "qualification/exact-run-2/results.json",
        "29226a32978da0cd9e93b0d8da8fa5020426a4cd457e48cc7d5fa6e970c6aeb0",
    )
    value.update(
        stage_owner_sha256=REVIEWED_STAGE,
        calibrated_health_owner=CAL_SHA,
        schema="s20plus_early_pair_f1_v1",
    )
    return value


def ticket_dir(run):
    require(
        isinstance(run, Path)
        and run.parent == RUN_ROOT
        and re.fullmatch(r"run-[0-9]{19}", run.name)
        and run.absolute() == run,
        "invalid early-pair run",
    )
    ticket = RUN_ROOT / ("ticket-" + run.name[4:])
    require(
        ticket.resolve(strict=True) == ticket and ticket.is_dir(), "indirect admission"
    )
    return ticket


def put(ticket, name, value):
    cal.engine.durable_json(ticket / (name + ".json"), value)


def get(ticket, name):
    return cal.engine.read_json(ticket / (name + ".json"), name)


def source_fields(health):
    return {k: health[k] for k in stage.IDENTITY}


def subject(run):
    ticket = ticket_dir(run)
    v = get(ticket, "prepared")
    cal.RUN = ticket
    cal.validate_health(v["health"], "grant-root")
    require(
        v["profile"] == PROFILE
        and v["run"] == str(run)
        and v["candidate"] == CANDIDATE
        and v["original"] == ORIGINAL
        and v["review"] == cal.engine.digest(review())
        and source_fields(v["health"]) == calibrated_identity()
        and re.fullmatch("[0-9a-f]{32}", v["nonce"])
        and type(v["issued"]) is int
        and v["expires"] == v["issued"] + 900,
        "invalid stock admission",
    )
    return v, cal.engine.digest(v)


def accepted(run, *, fresh=False):
    v, key = subject(run)
    receipt = get(ticket_dir(run), "accepted")
    require(
        receipt
        == {
            "grant_sha256": key,
            "approved_at": receipt["approved_at"],
            "approval_sha256": hashlib.sha256((PREFIX + key).encode()).hexdigest(),
        }
        and type(receipt["approved_at"]) is int
        and v["issued"] <= receipt["approved_at"] < v["expires"],
        "incorrect saved approval",
    )
    if fresh:
        require(
            receipt["approved_at"] <= time.time() < v["expires"],
            "original candidate approval expired",
        )
    return v, key


def prepare():
    with cal.registry.target_session_lease(ROOT):
        cal.registry.require_no_f1_owner(ROOT)
        require(
            not os.path.lexists(OWNER.GUARD)
            and not os.path.lexists(view.CAMPAIGN_GUARD)
            and not (RUN_ROOT / "consumed-candidates" / (CANDIDATE + ".json")).exists(),
            "unresolved owner or consumed candidate",
        )
        identity = OWNER.runtime._registry_identity("early-pair-preflight", "0" * 64)
        require(
            cal.registry.active_claim(ROOT, identity["candidate_key"]) is None,
            "candidate already consumed in global registry",
        )
        OWNER.validate_host_closure()
        physical = OWNER.retained_physical_recovery()
        ordinal = str(time.time_ns())
        run = RUN_ROOT / ("run-" + ordinal)
        ticket = RUN_ROOT / ("ticket-" + ordinal)
        ticket.mkdir(mode=0o700)
        cal.RUN = ticket
        h, _ = cal.engine.resident_health_once(ticket, "grant-root")
        cal.validate_health(h, "grant-root")
        require(
            source_fields(h) == calibrated_identity()
            and all(h[k] == physical[k] for k in stage.IDENTITY[:2]),
            "current Android does not match the calibrated original",
        )
        issued = int(time.time())
        v = dict(
            profile=PROFILE,
            run=str(run),
            review=cal.engine.digest(review()),
            health=h,
            candidate=CANDIDATE,
            original=ORIGINAL,
            nonce=secrets.token_hex(16),
            issued=issued,
            expires=issued + 900,
        )
        put(ticket, "prepared", v)
        _, key = subject(run)
        return {"approval": PREFIX + key, "run_dir": str(run), "expires": v["expires"]}


def health(run, name, expected_serial=None):
    if name == "preflight-root":
        v, _ = accepted(run, fresh=True)
        answer = old_preflight(run, name, expected_serial)
        require(
            source_fields(answer[0]) == source_fields(v["health"]),
            "source boot changed before Download",
        )
        accepted(run, fresh=True)
        return answer
    if name == "final-root" and stage.fresh_return_run == run:
        v, key = accepted(run)
        ticket = ticket_dir(run)
        source = v["health"]
        cal.RUN = ticket
        pin = cal.wait_first_return(
            {
                "serial_sha256": source["serial_sha256"],
                "topology_sha256": source["topology_sha256"],
                "source_boot_sha256": source["boot_id_sha256"],
            },
            key,
        )
        answer = old_preflight(run, name, expected_serial)
        require(
            answer[0]["boot_id_sha256"] == pin["boot_sha256"],
            "first identified return changed",
        )
        return answer
    return old_preflight(run, name, expected_serial)


def scan_intent(run, phase, h):
    out = old_make_intent(run, phase, h)
    v, key = accepted(run)
    out["grant_sha256"] = key
    if phase == "return":
        pin = get(ticket_dir(run), "first-observed-return")
        require(
            pin == {"binding_sha256": key, "boot_sha256": h["boot_id_sha256"]}
            and h["boot_id_sha256"] != v["health"]["boot_id_sha256"],
            "return scan escaped first identified boot",
        )
        out["first_observed_return"] = pin
    return out


def verdict(classification, claim, rollback):
    run = stage.CURRENT_RUN.get() or Path(
        OWNER.runtime._require_live_transaction()["run_dir"]
    )
    prepared = OWNER.engine.read_json(run / "prepared.json", "prepared")
    final = OWNER.engine.read_json(run / "final-health.json", "final original health")
    evidence = stage.first_return(run, prepared, final)
    require(
        evidence
        == OWNER.engine.read_json(run / stage.paths("return")[2], "return evidence"),
        "return classification changed",
    )
    if rollback and classification == "odin_transfer_completed" and claim == "NO_PROOF":
        labels = {
            "paired": "PREBRANCH_AND_PRIMARY_ENTRY",
            "prebranch_only": "PREBRANCH",
            "primary_entry_only": "PRIMARY_ENTRY",
        }
        if evidence["state"] in labels:
            return "PROVED_Y2Q_" + labels[
                evidence["state"]
            ] + "_ORIGINAL_MAGISK_RETURNED", True
    return "NO_PROOF_Y2Q_EARLY_PAIR_RESIDENT_HEALTH_OBSERVED", False


def initial_proof(run, v):
    ticket = ticket_dir(run)
    h = get(ticket, "before-adb-health")
    cal.RUN = ticket
    cal.validate_health(h, "before-adb-root")
    require(
        source_fields(h) == source_fields(v["health"]), "initial control source differs"
    )
    record = OWNER.engine.read_json(
        run / "initial-download-result.json", "initial Download result"
    )
    capture = cal.engine.raw_capture
    handle = capture.load_handle(run / "initial-reboot.capture.json")
    err = capture.read_stderr(handle, maximum=cal.engine.MAX_ADB_BYTES)
    out = capture.read_stdout(handle, maximum=cal.engine.MAX_ADB_BYTES)
    require(
        handle.name == "initial-reboot"
        and handle.stdout_path == run / "initial-reboot.stdout"
        and handle.stderr_path == run / "initial-reboot.stderr"
        and record["capture_receipt"]
        == dict(path=str(handle.receipt_path), **OWNER.receipt(handle.receipt_path))
        and cal.engine.raw_dispatch_proved(handle, err)
        and record["returncode"] == handle.returncode
        and record["stdout_sha256"] == hashlib.sha256(out).hexdigest()
        and record["stderr_sha256"] == hashlib.sha256(err).hexdigest()
        and record["outcome"] == "dispatched"
        and record["replay_permitted"] is False,
        "initial Download dispatch is unproved",
    )


def runtime_source():
    raw = retained_source()
    call = b"                result = original(argv, capture_dir, name, **kwargs)"
    require(raw.count(call) == 1, "reviewed raw dispatch boundary differs")
    return raw.replace(
        call,
        b'                if name in ("initial-reboot", "candidate-transfer"):\n                    _early_effect_deadline(Path(capture_dir))\n'
        + call,
    )


def raw_deadline(run):
    accepted(run, fresh=True)


def _configure_runtime(module):
    old_configure(module)
    module._early_effect_deadline = raw_deadline
    engine = module.engine
    original_binding = engine.prepared_binding

    def bound(run, preflight, endpoint, closure):
        v, _ = accepted(run, fresh=True)
        require(
            source_fields(preflight) == source_fields(v["health"]),
            "prepared source is outside the grant",
        )
        initial_proof(run, v)
        binding = original_binding(run, preflight, endpoint, closure)
        binding["expires_unix"] = min(binding["expires_unix"], v["expires"])
        return binding

    engine.prepared_binding = bound
    # Install inside the retained profile's normal guarded entrypoints.
    # This variant only admits empty-baseline physical entry, including
    # the original one-read recovery from a cut. No endpoint substitution.
    module._arm_physical_rollback_with_rebind = module._ENGINE_ARM_PHYSICAL_ROLLBACK
    module._confirm_physical_rollback_with_rebind = (
        module._ENGINE_CONFIRM_PHYSICAL_ROLLBACK
    )
    enumerate_download = engine.enumerate_download

    def inventory():
        devices, digest = enumerate_download()
        if module._require_live_transaction()["entrypoint"] == "arm_physical_rollback":
            require(not devices, "Download already present before physical cue")
        return devices, digest

    engine.enumerate_download = inventory
    initial = engine.adb_reboot_download_capture

    def initial_entry(run_dir, serial, name):
        v, _ = accepted(run_dir, fresh=True)
        ticket = ticket_dir(run_dir)
        h, current = cal.engine.resident_health_once(
            ticket, "before-adb-root", v["health"]["serial_sha256"]
        )
        cal.RUN = ticket
        cal.validate_health(h, "before-adb-root")
        require(
            source_fields(h) == source_fields(v["health"]) and current == serial,
            "source changed at initial control",
        )
        put(ticket, "before-adb-health", h)
        accepted(run_dir, fresh=True)
        return initial(run_dir, serial, name)

    engine.adb_reboot_download_capture = initial_entry
    dispatch = engine.execute_odin_exact

    def guarded_dispatch(run_dir, kind, *args, **kwargs):
        v, _ = accepted(run_dir, fresh=kind == "candidate")
        if kind == "candidate":
            initial_proof(run_dir, v)
        return dispatch(run_dir, kind, *args, **kwargs)

    engine.execute_odin_exact = guarded_dispatch


def parser():
    p = argparse.ArgumentParser(allow_abbrev=False)
    modes = p.add_mutually_exclusive_group(required=True)
    for n in (
        "review-input",
        "validate-host",
        "validate-active",
        "prepare",
        "execute",
        "recover",
        "abort-pre-candidate",
    ):
        modes.add_argument("--" + n, action="store_true")
    p.add_argument("--run-dir", type=Path)
    p.add_argument("--approval")
    return p


def bind():
    stage.ACTIVE = OWNER.ACTIVE = ACTIVE
    stage.SCRIPT = OWNER.SCRIPT = SCRIPT
    stage.RUN_ROOT = OWNER.RUN_ROOT = RUN_ROOT
    stage.PROFILE = OWNER.PROFILE = PROFILE
    stage.HEADING = OWNER.HEADING = HEADING
    stage.PAIR = OWNER.PAIR = PAIR
    stage.PAIR_SHA = OWNER.PAIR_SHA = PAIR_SHA
    OWNER.PAIR_SIZE = PAIR.stat().st_size
    stage.READER, stage.FILTER, stage.PACKAGER = READER, reader.FILTER, PACKAGER
    stage.reader = SimpleNamespace(
        shell=partial(reader.shell, stages=reader.EARLY_STAGES),
        parse=partial(reader.parse, stages=reader.EARLY_STAGES),
    )
    stage.APPROVAL = "S20PLUS-G986N-EARLY-PAIR-BOUND:"
    stage.CONFIRM = "S20PLUS-G986N-EARLY-PAIR-ARRIVAL:"
    OWNER.ACTIVATION = RUN_ROOT / "activation.json"
    OWNER.BUILDER, OWNER.BUILDER_SHA = PACKAGER, PACKAGER_SHA
    OWNER.TEST_SOURCE = CHECK
    OWNER.PHASES = {}
    stage.read_pair = OWNER.read_pair = pair
    OWNER.effect_profile, OWNER.retained_runtime_source, OWNER.review_identity = (
        scope,
        stage.runtime_source,
        review,
    )
    stage._configure_runtime = _configure_runtime
    stage.runtime_source = runtime_source
    OWNER.retained_runtime_source = runtime_source
    OWNER.enter_runtime = stage.enter_runtime
    OWNER.resident_health, OWNER.allow_marker = health, stage.allowed
    OWNER.observe_candidate, OWNER.validate_candidate_observation = (
        stage.observe,
        stage.validate_observation,
    )
    OWNER.terminal_verdict, OWNER.validate_namespace, OWNER.checked_terminal = (
        verdict,
        stage.validate_namespace,
        stage.publish,
    )
    stage.make_intent = scan_intent
    OWNER.parser = parser


def restore(run):
    accepted(run)
    e = OWNER.engine
    if (run / "terminal.json").exists() or (run / "rollback-intent.json").exists():
        stage.fresh_return_run = None
        return e.finalize_resident(run)
    require(
        (run / "candidate-intent.json").exists()
        or (run / "candidate-claim-intent.json").exists(),
        "no candidate effect to recover",
    )
    if not (run / "candidate-observation.json").exists():
        e.resume_run(run)
    require(
        not (run / "physical-observation-miss.json").exists(),
        "consumed physical observation",
    )
    arm_path = run / "physical-rollback-intent.json"
    if not arm_path.exists():
        e.arm_physical_rollback(run)
    arm = e.read_json(arm_path, "physical arrival authorization")
    require(
        arm["branch"] == "attended-entry-required"
        and arm["baseline"]["endpoint_count"] == 0,
        "forced-entry requires a recorded empty Download inventory",
    )
    t = ticket_dir(run)
    cued = (t / "physical-cue.json").exists()
    confirmed = (run / "physical-confirmation-intent.json").exists()
    arrived = (run / "physical-rollback-arrival.json").exists()
    require(
        arrived or time.time() < arm["expires_unix"], "physical arrival window expired"
    )
    cue = {"run": str(run), "arm_sha256": e.digest(arm), "expires": arm["expires_unix"]}
    if cued:
        require(get(t, "physical-cue") == cue, "saved physical cue differs")
    else:
        require(not confirmed and not arrived, "uncued physical observation")
        put(t, "physical-cue", cue)
        print(
            json.dumps(
                {
                    "status": "ENTER_PHYSICAL_DOWNLOAD_NOW",
                    "expires": arm["expires_unix"],
                }
            ),
            flush=True,
        )
    stage.fresh_return_run = run if not (cued or confirmed or arrived) else None
    return e.confirm_physical_rollback(run, arm["confirmation_token"])


def execute(run, approval):
    v, key = subject(run)
    now = int(time.time())
    require(
        approval == PREFIX + key and v["issued"] <= now < v["expires"],
        "fresh exact attended approval required",
    )
    require(not os.path.lexists(run), "run is not fresh")
    put(
        ticket_dir(run),
        "accepted",
        {
            "grant_sha256": key,
            "approved_at": now,
            "approval_sha256": hashlib.sha256(approval.encode()).hexdigest(),
        },
    )
    e = OWNER.engine
    e.prepare(run)
    prepared = OWNER.runtime._read_prepared_for_output(run)
    accepted(run, fresh=True)
    require(
        prepared["binding"]["expires_unix"] <= v["expires"]
        and source_fields(prepared["binding"]["preflight"])
        == source_fields(v["health"]),
        "post-Download admission exceeds original grant",
    )
    print(json.dumps({"status": "CANDIDATE_ADMISSION_BOUND"}), flush=True)
    e.execute(run, prepared["approval_token"])
    return restore(run)


@contextmanager
def exclusive(run):
    descriptor = os.open(
        ticket_dir(run), os.O_DIRECTORY | os.O_NOFOLLOW | os.O_RDONLY | os.O_CLOEXEC
    )
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def main(argv):
    bind()
    inner = argv[:1] == ["--in-source-view"]
    if inner:
        argv = argv[1:]
    a = parser().parse_args(argv)
    if a.review_input:
        print(json.dumps(review(), sort_keys=True))
        return
    if not inner:
        connected = not (a.validate_host or a.validate_active)
        ns = OWNER.namespace(argv, connected=connected)
        raise SystemExit(subprocess.run(ns, env=view.clean_environment()).returncode)
    cal.runtime()
    OWNER.enter_runtime()
    if a.validate_host:
        OWNER.validate_host_closure()
        OWNER.retained_physical_recovery()
        print(json.dumps({"status": "PASS_EARLY_PAIR_HOST", "device_commands": 0}))
        return
    OWNER.require_active()
    if a.validate_active:
        print(json.dumps({"status": "PASS_EARLY_PAIR_ACTIVE", "device_commands": 0}))
        return
    if a.prepare:
        result = prepare()
    else:
        run = a.run_dir
        ticket_dir(run)
        with exclusive(run):
            if a.execute:
                result = execute(run, a.approval)
            elif a.recover:
                result = restore(run)
            else:
                accepted(run)
                require(
                    not (run / "candidate-intent.json").exists()
                    and not (run / "candidate-claim-intent.json").exists(),
                    "candidate already owns rollback",
                )
                result = OWNER.engine.abort_pre_candidate(run)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "run_dir",
                    "approval",
                    "expires",
                    "verdict",
                    "experiment_pass",
                )
                if k in result
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as e:
        if "--validate-host" in sys.argv:
            import traceback

            traceback.print_exc()
        print(
            json.dumps(
                {
                    "status": "STOP_EARLY_PAIR",
                    "failure": type(e).__name__,
                    "reason": str(e)[:230]
                    if isinstance(e, (OWNER.Stop, ValueError))
                    else "",
                }
            )
        )
        raise SystemExit(2)
