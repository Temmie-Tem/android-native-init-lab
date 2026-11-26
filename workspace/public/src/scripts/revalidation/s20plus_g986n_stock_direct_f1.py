#!/usr/bin/env python3
"""Single attended y2q stock-kernel direct-marker control."""

import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import s20plus_g986n_early_pair_f1 as base

ACTIVE = True
SCRIPT = Path(__file__).resolve()
ROOT, stage, owner, cal = base.ROOT, base.stage, base.OWNER, base.cal
require, pinned = base.require, base.pinned
VERSION = "s20plus-g986n-stock-direct-f1"
HEADING = "## S20+ stock Magisk direct loader marker under one attended approval\n"
PREFIX = "S20PLUS-G986N-STOCK-DIRECT-F1-APPROVE:"
EXP = base.view.PRIVATE / "analysis/s20plus-y2q-stock-direct-20261126"
PAIR = EXP / "packaged3/pair.json"
PAIR_SHA = "0029519deca70ba480df681661be3bc86f4394bbafb2cb2d67a6ed9c1505393b"
CANDIDATE = "ad9caa48da7c58854b177d29e6552abc81eb7487b32d944a4df7c4f9baa7e696"
LAST = base.view.PRIVATE / "runs/s20plus-g986n-early-pair-f1/run-1795640333141198698"
SRC = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0/stock-direct"
BUILD = SRC / "build_control.py"
BUILD_SHA = "2ad5cc9ebfd5fdeecb74e0699c3c69f3096c18347c42a86486b4ee0371b462b5"
PARENT_SHA = "65921607a5ec5442d9542c3f616642dd6931fb58bba5efb876be4297e86f3676"
PROP = "/sys/firmware/devicetree/base/chosen/codex,y2q-stock-direct-v1"
old_bind = base.bind
old_configure = base._configure_runtime
old_health = base.health
old_restore = base.restore
old_execute = base.execute
from contextvars import ContextVar

initial_process = ContextVar("stock_direct_initial_process", default=False)


def pair():
    data = json.loads(pinned(PAIR, PAIR_SHA))
    require(
        data["kind"] == "HOST_ONLY_S20PLUS_STOCK_DIRECT_AP_PAIR"
        and data["target"] == "SM-G986N/y2q/G986NKSS8IYC2"
        and data["raw"]
        == "e3559ea3419b443da6f0f8a57ddb8d8a59d835bee4fdca95bf4010f478b77a8c"
        and data["clear_frames_absent_from_both_boots"] is True
        and data["device_commands"] == 0,
        "wrong control package",
    )
    for role, pin in (("candidate", CANDIDATE), ("rollback", base.ORIGINAL)):
        a = data["archives"][role]
        require(
            a["ap"]["sha256"] == pin
            and a["decoded_boot"]["size"] == 67108864
            and a["only_member"]["name"] == "boot.img.lz4",
            "wrong boot role",
        )
    require(
        Path(data["archives"]["candidate"]["ap"]["path"])
        == PAIR.with_name("AP.tar.md5")
        and hashlib.sha256(
            base.reader.shell(
                data["nonce"], "0" * 64, base.reader.EARLY_STAGES
            ).encode()
        ).hexdigest()
        == data["return_template"],
        "reader or candidate path differs",
    )
    return dict(**data["archives"], nonce=data["nonce"])


def calibrated_identity():
    term = json.loads(
        pinned(
            LAST / "terminal.json",
            "abea672783a967eda0fbc18a686eab7800d7efcce40d330ccd867527a72fbc8f",
        )
    )
    final = json.loads(
        pinned(
            LAST / "final-health.json",
            "2d839c7894a4bbc45e201a4ef9ff710253c43a13cbed447d5948c0da1208370d",
        )
    )
    require(
        term["rollback_transfer_completed"] is True
        and final["rollback_outcome_proved"] is True
        and final["resident_boot_healthy"] is True
        and final["health"]["target"] == owner.TARGET,
        "original source unproved",
    )
    return base.source_fields(final["health"])


def scope():
    return dict(
        partition="boot",
        candidate_attempt_maximum=1,
        rollback_attempt_maximum=1,
        approval_seconds=900,
        current_scope="loader prebranch into original Magisk; candidate-time tag and previous log",
        stock_source=calibrated_identity(),
        diagnostic_slot_bytes=128,
        header_writes=0,
        tag=PROP,
        physical_fallback=True,
        authenticated_adb_rollback=True,
        attendance_required=True,
        candidate_and_rollback_replay=False,
    )


def review():
    receipts = {
        EXP
        / "stock-reader.json": "3c7596517e2c454e6701795ce317f086f370bd82ec9c19c1bab93428d8a662eb",
        Path(base.__file__): PARENT_SHA,
        Path(stage.__file__): base.REVIEWED_STAGE,
        base.CAL_SOURCE: base.CAL_SHA,
        BUILD: BUILD_SHA,
        SRC
        / "handoff.patch": "9bf218bda9ceb5c29c94b66033dbb23cf1954837dfc56410aa0dd4bae93eeaa3",
        SRC
        / "stock-control-fdt.h": "a198510941265062d691980315ac03fb7a650a4a423f695685a124167e74b62b",
        EXP
        / "candidate3/stage.json": "d794a8cd1d5eedf049f386b7bf9e48a801e3793016f1f00fc9cfb49522a88a55",
        EXP
        / "qualification/final3/results.json": "08f89714bbffc25895bc922b4d325a418f00ab465aa9a1a18bf5c460174f526b",
    }
    policy = base.view.read_file(owner.CONTRACT).decode()
    inherited = {}
    for heading in (
        "## S20+ y2q early handoff pair under one attended approval\n",
        "## S20+ y2q mainline retained kernel stages attended F1\n",
    ):
        require(policy.count(heading) == 1, "inherited S20+ section missing")
        inherited[heading.strip()] = hashlib.sha256(
            policy.split(heading)[1].split("\n## ", 1)[0].encode()
        ).hexdigest()
    for path, pin in receipts.items():
        pinned(path, pin)
    return dict(
        **{k: v for k, v in base.old_stage_review().items() if k != "schema"},
        schema="s20plus_stock_direct_owner_v1",
        inherited_target_sections=inherited,
        frozen={str(k): v for k, v in receipts.items()},
    )


def tag_script(nonce, boot):
    shell = base.reader.shell(nonce, boot, base.reader.EARLY_STAGES)
    before, split, _ = shell.partition("scan() {")
    require(split, "unexpected reader prelude")
    return (
        before
        + f"""prop={PROP}
chosen=${{prop%/*}}
test -d "$chosen" && test -r "$chosen" && test -x "$chosen" || exit 4
test ! -L "$prop" || exit 4
if [ -e "$prop" ]; then
    test -f "$prop" && test -r "$prop" || exit 4
    value=$(/system/bin/head -c 36 "$prop" | /system/bin/od -An -v -tx1 | /system/bin/tr -d '[:space:]') || exit 4
    case "$value" in
      {(nonce + ":C").encode().hex()}00) state=C;;
      {(nonce + ":U").encode().hex()}00) state=U;;
      *) state=FOREIGN;;
    esac
else
    state=ABSENT
fi
same_boot || exit 4
/system/bin/printf 'Y2Q_TAG_%s\\n' "$state"
"""
    )


def tag_parse(out):
    if out not in (
        b"Y2Q_TAG_C\n",
        b"Y2Q_TAG_U\n",
        b"Y2Q_TAG_ABSENT\n",
        b"Y2Q_TAG_FOREIGN\n",
    ):
        raise ValueError("invalid live property record")
    return out[8:-1].decode()


def command(name, h):
    nonce = pair()["nonce"]
    boot = h["boot_id_sha256"]
    if name == "candidate-log":
        return base.reader.shell(nonce, boot, base.reader.EARLY_STAGES)
    require(
        name in ("source-tag", "candidate-tag", "recovery-tag", "original-tag"),
        "unknown property phase",
    )
    return tag_script(nonce, boot)


def receipt(run, name, h):
    ticket = base.ticket_dir(run)
    _, key = base.accepted(run)
    script = command(name, h)
    intent = {
        "grant": key,
        "phase": name,
        "boot": h["boot_id_sha256"],
        "script": hashlib.sha256(script.encode()).hexdigest(),
    }
    require(base.get(ticket, name + "-intent") == intent, "control read intent differs")
    cap = cal.engine.raw_capture
    path = ticket / (name + ".capture.json")
    if not path.exists():
        return {"state": "capture_gap"}
    handle = cap.load_handle(path)
    require(
        handle.name == name
        and handle.stdout_path == ticket / (name + ".stdout")
        and handle.stderr_path == ticket / (name + ".stderr"),
        "misbound capture",
    )
    out = cap.read_stdout(handle, maximum=96)
    err = cap.read_stderr(handle, maximum=1024)
    if (
        handle.timed_out
        or handle.output_exceeded
        or handle.producer_error_type
        or type(handle.returncode) != int
        or handle.returncode
        or err
    ):
        return {"state": "read_failed"}
    try:
        result = (
            base.reader.parse(0, out, err, base.reader.EARLY_STAGES)
            if name == "candidate-log"
            else {"state": tag_parse(out)}
        )
    except ValueError:
        return {"state": "read_failed"}
    return dict(**result, raw_sha256=owner.receipt(path)["sha256"])


def acquire(run, name, h, serial):
    owner.require_active()
    lease = owner.runtime._require_live_transaction()
    require(
        lease["run_dir"] == str(run) and not (run / "terminal.json").exists(),
        "not the live run",
    )
    entry = lease["entrypoint"]
    allowed = {
        "source-tag": {"prepare"},
        "candidate-tag": {"execute", "resume_run"},
        "candidate-log": {"execute", "resume_run"},
        "recovery-tag": {"execute", "resume_run"},
        "original-tag": {
            "execute",
            "resume_run",
            "confirm_physical_rollback",
            "finalize_resident",
        },
    }
    require(entry in allowed.get(name, set()), "phase outside admitted read")
    ticket = base.ticket_dir(run)
    v, key = base.accepted(run)
    source = v["health"]
    require(
        hashlib.sha256(serial.encode()).hexdigest()
        == h["serial_sha256"]
        == source["serial_sha256"]
        and h["topology_sha256"] == source["topology_sha256"],
        "target or topology changed",
    )
    if name == "source-tag":
        require(
            not (run / "initial-download-intent.json").exists()
            and h["boot_id_sha256"] == source["boot_id_sha256"],
            "source phase differs",
        )
    else:
        require(h["boot_id_sha256"] != source["boot_id_sha256"], "stale Android boot")
        prepared = owner.engine.read_json(run / "prepared.json", "prepared")
        if name == "original-tag":
            final = owner.engine.read_json(
                run / "final-health.json", "restored original"
            )
            require(final["health"] == h, "different original return")
            stage.restored_original(run, prepared, final)
        else:
            owner.transfer_receipt(run, "candidate", prepared["binding_sha256"])
            require(not (run / "rollback-intent.json").exists(), "late candidate read")
    script = command(name, h)
    base.put(
        ticket,
        name + "-intent",
        {
            "grant": key,
            "phase": name,
            "boot": h["boot_id_sha256"],
            "script": hashlib.sha256(script.encode()).hexdigest(),
        },
    )
    require(cal.exact_serial(h) == serial, "live property/log read endpoint changed")
    cal.engine.raw_capture.acquire_command(
        [
            str(owner.engine.ADB),
            "-s",
            serial,
            "shell",
            "-T",
            "su",
            "-c",
            shlex.quote(script),
        ],
        ticket,
        name,
        timeout=120 if name == "candidate-log" else 15,
        stdout_maximum=96,
        stderr_maximum=1024,
        stdout_name=name + ".stdout",
        stderr_name=name + ".stderr",
    )
    return receipt(run, name, h)


def health(run, name, expected_serial=None):
    h, serial = old_health(run, name, expected_serial)
    if name == "preflight-root":
        require(
            acquire(run, "source-tag", h, serial)["state"] == "ABSENT",
            "source property must be absent",
        )
    return h, serial


def classify(tag, scan):
    return (
        tag.get("state") == "C"
        and scan.get("state") == "prebranch_only"
        and scan.get("prebranch_count") == 1
        and scan.get("primary_entry_count") == 0
    )


def candidate_result(run, h, prepared):
    ticket = base.ticket_dir(run)
    owner.validate_root(run, h, "candidate-android-root")
    start = prepared["binding"]["preflight"]
    require(
        all(h[k] == start[k] for k in stage.IDENTITY[:2])
        and h["boot_id_sha256"] != start["boot_id_sha256"],
        "candidate health identity differs",
    )
    owner.transfer_receipt(run, "candidate", prepared["binding_sha256"])
    tag = receipt(run, "candidate-tag", h)
    require(tag["state"] in ("C", "U"), "Android has no exact current-boot control tag")
    scan = receipt(run, "candidate-log", h)
    after = base.get(ticket, "candidate-after-health")
    cal.RUN = ticket
    cal.validate_health(after, "control-after-root")
    require(
        base.source_fields(after) == base.source_fields(h),
        "candidate boot changed during read",
    )
    return dict(
        tag=tag,
        log=scan,
        root_after_sha256=cal.engine.digest(after),
        confirmed=classify(tag, scan),
    )


def observe(run, prepared):
    try:
        owner.transfer_receipt(run, "candidate", prepared["binding_sha256"])
        h, serial = owner.candidate_health(run, prepared["binding"]["preflight"])
        tag = acquire(run, "candidate-tag", h, serial)
        require(tag["state"] in ("C", "U"), "fresh Android attribution unavailable")
        acquire(run, "candidate-log", h, serial)
        ticket = base.ticket_dir(run)
        after, _ = cal.engine.resident_health_once(
            ticket, "control-after-root", h["serial_sha256"]
        )
        base.put(ticket, "candidate-after-health", after)
        evidence = candidate_result(run, h, prepared)
        base.put(ticket, "candidate-result", evidence)
        return {
            "environment": "resident-android",
            "transport_authorized": True,
            "resident_health": h,
            "claim_verdict": "PROVED" if evidence["confirmed"] else "NO_PROOF",
            "control_evidence_sha256": cal.engine.digest(evidence),
            "at": owner.engine.utc_now(),
        }, serial
    except Exception as error:
        failure = owner.failed_observation(error)
        if "h" in locals():
            failure["boot_id_sha256"] = h["boot_id_sha256"]
        return failure, None


def validate_observation(run, value, key, initial):
    owner.runtime._ENGINE_VALIDATE_CANDIDATE_OBSERVATION(run, value, key, initial)
    if value["environment"] == "observer-reporting-cut":
        require(
            value["transport_authorized"] is False
            and value["claim_verdict"] == "NO_PROOF",
            "invalid observation gap",
        )
        return
    require(
        value["environment"] == "resident-android", "unrecognized control environment"
    )
    prepared = owner.engine.read_json(run / "prepared.json", "prepared")
    evidence = candidate_result(run, value["resident_health"], prepared)
    require(
        evidence == base.get(base.ticket_dir(run), "candidate-result")
        and value["control_evidence_sha256"] == cal.engine.digest(evidence)
        and value["claim_verdict"]
        == ("PROVED" if evidence["confirmed"] else "NO_PROOF"),
        "control evidence changed",
    )


def validate_namespace(run):
    stage.validate_namespace(run)
    if (run / "initial-download-intent.json").exists():
        h = owner.engine.read_json(run / "mainline-baseline-intent.json", "baseline")[
            "health"
        ]
        require(
            receipt(run, "source-tag", h)["state"] == "ABSENT",
            "invalid source tag baseline",
        )


def publish(run, prepared, final):
    stage.restored_original(run, prepared, final)
    ticket = base.ticket_dir(run)
    h = final["health"]
    if (ticket / "candidate-tag-intent.json").exists():
        require(
            h["boot_id_sha256"] != base.get(ticket, "candidate-tag-intent")["boot"],
            "final health reused a candidate observation boot",
        )
    if not (ticket / "original-tag-intent.json").exists():
        require(
            not (run / "terminal.json").exists(),
            "terminal missing original-tag evidence",
        )
        serial = owner.validated_current_serial(prepared["binding"]["preflight"], h)
        acquire(run, "original-tag", h, serial)
    require(
        receipt(run, "original-tag", h)["state"] == "ABSENT",
        "original property absence unproved",
    )
    evidence = original_return(run, prepared, final)
    path = run / stage.paths("return")[2]
    if path.exists():
        require(
            owner.engine.read_json(path, "original return") == evidence,
            "restored receipt changed",
        )
    else:
        owner.engine.durable_json(path, evidence)
    with stage.bound_run(run):
        return owner.original_publish(run, prepared, final)


def original_return(run, prepared, final):
    transfer = stage.restored_original(run, prepared, final)
    tag = receipt(run, "original-tag", final["health"])
    require(tag["state"] == "ABSENT", "original property still present or unreadable")
    return {
        "phase": "return",
        "state": "original_magisk_health_and_tag_absence",
        "binding_sha256": prepared["binding_sha256"],
        "original_transfer_sha256": transfer,
        "health_sha256": owner.engine.digest(final),
        "tag": tag,
    }


def verdict(classification, claim, rollback):
    run = stage.CURRENT_RUN.get() or Path(
        owner.runtime._require_live_transaction()["run_dir"]
    )
    prepared = owner.engine.read_json(run / "prepared.json", "prepared")
    final = owner.engine.read_json(run / "final-health.json", "final")
    stage.restored_original(run, prepared, final)
    if not (run / "physical-rollback-arrival.json").exists():
        automatic_proof(run)
    require(
        receipt(run, "original-tag", final["health"])["state"] == "ABSENT",
        "original attribution failed",
    )
    observation = owner.engine.read_json(
        run / "candidate-observation.json", "candidate observation"
    )
    validate_observation(
        run,
        observation,
        prepared["binding_sha256"],
        prepared["binding"]["preflight"]["boot_id_sha256"],
    )
    require(
        claim == observation["claim_verdict"],
        "terminal claim disagrees with candidate observation",
    )
    if rollback and classification == "odin_transfer_completed" and claim == "PROVED":
        return "PROVED_STOCK_DIRECT_MARKER_ON_TAGGED_MAGISK_ORIGINAL_RESTORED", True
    return "NO_PROOF_STOCK_DIRECT_MARKER_ORIGINAL_MAGISK_RESTORED", False


def automatic_proof(run):
    """Join only the authenticated ADB control to its captured command."""
    e = owner.engine
    observation = e.read_json(run / "candidate-observation.json", "candidate")
    prepared = e.read_json(run / "prepared.json", "prepared")
    key = prepared["binding_sha256"]
    validate_observation(
        run, observation, key, prepared["binding"]["preflight"]["boot_id_sha256"]
    )
    require(
        observation["environment"] == "resident-android"
        and observation["transport_authorized"] is True,
        "no automatic return authority",
    )
    health = observation["resident_health"]
    tag = receipt(run, "recovery-tag", health)
    original_tag = receipt(run, "candidate-tag", health)
    require(
        tag["state"] in ("C", "U") and tag["state"] == original_tag["state"],
        "ADB return tag differs",
    )
    intent = e.read_json(run / "rollback-download-intent.json", "rollback control")
    require(
        intent["binding_sha256"] == key
        and intent["source_serial_sha256"] == health["serial_sha256"]
        and intent["source_boot_id_sha256"] == health["boot_id_sha256"],
        "ADB recovery intent differs",
    )
    ticket = base.ticket_dir(run)
    require(
        base.get(ticket, "adb-effect-source")
        == {
            "binding_sha256": key,
            "tag": tag["raw_sha256"],
            "identity": base.source_fields(health),
            "intent": e.digest(intent),
        },
        "ADB effect-time source differs",
    )
    result = e.read_json(run / "rollback-download-result.json", "rollback ADB dispatch")
    cap = cal.engine.raw_capture
    h = cap.load_handle(run / "rollback-reboot.capture.json")
    err = cap.read_stderr(h, maximum=cal.engine.MAX_ADB_BYTES)
    out = cap.read_stdout(h, maximum=cal.engine.MAX_ADB_BYTES)
    require(
        h.name == "rollback-reboot"
        and h.stdout_path == run / "rollback-reboot.stdout"
        and h.stderr_path == run / "rollback-reboot.stderr"
        and result["capture_receipt"]
        == dict(path=str(h.receipt_path), **owner.receipt(h.receipt_path))
        and cal.engine.raw_dispatch_proved(h, err)
        and result["outcome"] == "dispatched"
        and result["returncode"] == h.returncode
        and result["replay_permitted"] is False
        and result["stdout_sha256"] == hashlib.sha256(out).hexdigest()
        and result["stderr_sha256"] == hashlib.sha256(err).hexdigest(),
        "ADB return dispatch unproved",
    )


def _configure_runtime(module):
    original_rollback_command = module.engine.adb_reboot_download_capture
    old_configure(module)
    initial = module.engine.adb_reboot_download_capture

    def dispatch(run, serial, name):
        if name == "initial-reboot":
            return initial(run, serial, name)
        require(name == "rollback-reboot", "unknown reboot phase")
        obs = module.engine.read_json(
            run / "candidate-observation.json", "authenticated candidate"
        )
        prep = module.engine.read_json(run / "prepared.json", "prepared")
        validate_observation(
            run,
            obs,
            prep["binding_sha256"],
            prep["binding"]["preflight"]["boot_id_sha256"],
        )
        require(
            obs["environment"] == "resident-android"
            and obs["transport_authorized"] is True,
            "unauthenticated ADB rollback",
        )
        h = obs["resident_health"]
        expected = receipt(run, "candidate-tag", h)["state"]
        require(
            acquire(run, "recovery-tag", h, serial)["state"] == expected,
            "candidate boot changed at ADB control",
        )
        tag = receipt(run, "recovery-tag", h)
        intent = module.engine.read_json(
            run / "rollback-download-intent.json", "rollback control"
        )
        require(cal.exact_serial(h) == serial, "live ADB return endpoint changed")
        base.put(
            base.ticket_dir(run),
            "adb-effect-source",
            {
                "binding_sha256": prep["binding_sha256"],
                "tag": tag["raw_sha256"],
                "identity": base.source_fields(h),
                "intent": module.engine.digest(intent),
            },
        )
        require(
            cal.exact_serial(h) == serial,
            "live ADB return endpoint changed at dispatch",
        )
        return original_rollback_command(run, serial, name)

    module.engine.adb_reboot_download_capture = dispatch
    wait = module.engine.wait_download

    def bounded_arrival(baseline, timeout=None):
        lease = module._require_live_transaction()
        run = Path(lease["run_dir"])
        if (run / "rollback-download-observation-intent.json").exists() and not (
            run / "physical-rollback-intent.json"
        ).exists():
            try:
                automatic_proof(run)
            except Exception as error:
                raise module.engine.B0F1Error(
                    "no proved automatic control; physical recovery required"
                ) from error
        return wait(baseline, timeout)

    module.engine.wait_download = bounded_arrival
    before = module.engine.rollback_from_arrival

    def existing_arrival(run, prepared, endpoint):
        if not (run / "physical-rollback-arrival.json").exists():
            automatic_proof(run)
        return before(run, prepared, endpoint)

    module.engine.rollback_from_arrival = existing_arrival


def execute(run, token):
    active = initial_process.set(True)
    try:
        return old_execute(run, token)
    finally:
        initial_process.reset(active)


def restore(run):
    if (run / "terminal.json").exists() or (run / "rollback-intent.json").exists():
        return owner.engine.finalize_resident(run)
    if not (run / "physical-rollback-intent.json").exists():
        observed = run / "candidate-observation.json"
        candidate = (run / "candidate-intent.json").exists() or (
            run / "candidate-claim-intent.json"
        ).exists()
        # With an accepted ADB arrival, resume validates that original endpoint.
        # With a consumed control intent it cannot emit a second reboot.
        resume = (run / "rollback-download-arrival.json").exists()
        if candidate and not initial_process.get():
            resume = (
                resume
                or not observed.exists()
                or (run / "rollback-download-intent.json").exists()
            )
            if (
                observed.exists()
                and not (run / "rollback-download-intent.json").exists()
            ):
                obs = owner.engine.read_json(observed, "saved candidate observation")
                resume = resume or obs.get("transport_authorized") is True
        if resume:
            owner.engine.resume_run(run)
            if (run / "terminal.json").exists() or (
                run / "rollback-intent.json"
            ).exists():
                return owner.engine.finalize_resident(run)
    return old_restore(run)


def bind():
    base.ACTIVE, base.SCRIPT, base.PROFILE = ACTIVE, SCRIPT, VERSION
    base.RUN_ROOT = base.view.PRIVATE / "runs" / VERSION
    base.EXP, base.PAIR, base.PAIR_SHA, base.CANDIDATE = EXP, PAIR, PAIR_SHA, CANDIDATE
    base.HEADING, base.PREFIX = HEADING, PREFIX
    base.PACKAGER, base.PACKAGER_SHA = BUILD, BUILD_SHA
    base.CHECK = ROOT / "tests/test_s20plus_g986n_stock_direct_f1.py"
    base.calibrated_identity, base.pair, base.scope, base.review = (
        calibrated_identity,
        pair,
        scope,
        review,
    )
    base._configure_runtime, base.health, base.restore, base.verdict = (
        _configure_runtime,
        health,
        restore,
        verdict,
    )
    base.execute = execute
    old_bind()
    stage.APPROVAL = "S20PLUS-G986N-STOCK-DIRECT-BOUND:"
    stage.CONFIRM = "S20PLUS-G986N-STOCK-DIRECT-ARRIVAL:"
    owner.observe_candidate, owner.validate_candidate_observation = (
        observe,
        validate_observation,
    )
    owner.checked_terminal, owner.validate_namespace = publish, validate_namespace
    stage.first_return = original_return


if __name__ == "__main__":
    base.bind = bind
    try:
        base.main(sys.argv[1:])
    except Exception as err:
        print(
            json.dumps(
                {
                    "status": "STOP_STOCK_DIRECT",
                    "failure": type(err).__name__,
                    "reason": str(err)[:210]
                    if isinstance(err, (ValueError, owner.Stop))
                    else "",
                }
            )
        )
        raise SystemExit(2)
