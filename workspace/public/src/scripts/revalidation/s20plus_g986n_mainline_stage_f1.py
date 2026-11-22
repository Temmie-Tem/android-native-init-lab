#!/usr/bin/env python3
"""One attended y2q Linux attempt, physical Download rollback, and first-return stage scan."""

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import sys
import time

import s20plus_g986n_twrp_observe_source_view_v1 as view

ACTIVE = True
SCRIPT = Path(__file__).resolve()
ROOT = view.ROOT
PARENT = SCRIPT.with_name("s20plus_g986n_uniloader_android_f1.py")
PARENT_SHA = "5a8d865ccac1d4c1dde94088fb2ea0550a0d0b80727d4d7e9d6da9b20fe53d42"
BUILD = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0/mainline-handoff"
READER = BUILD / "return_stage.py"
FILTER = BUILD / "return-stage.awk"
PACKAGER = BUILD / "package_stage.py"
PAIR = view.PRIVATE / "outputs/s20plus-y2q-mainline-stage-f1-20261123/pair/pair.json"
PAIR_SHA = "dba8524669dccfc8ef2d8a04974b93c8481629ddb62784edbc4da0989e4e1004"
RUN_ROOT = view.PRIVATE / "runs/s20plus-g986n-mainline-stage-f1"
HEADING = "## S20+ y2q mainline retained kernel stages attended F1\n"
PROFILE = "s20plus-g986n-mainline-stage-v1"
APPROVAL = "S20PLUS-G986N-MAINLINE-STAGE-F1-APPROVE:"
CONFIRM = "S20PLUS-G986N-MAINLINE-STAGE-PHYSICAL-ROLLBACK:"
NATIVE_IMAGE = "7cfe4759249119bd8ad2bfa373d59192aed6ee6bcf5d9ab8f481672fe1fb95a8"
CANDIDATE = "6ba1cf82de4c8385aa04cf3332416f77fd02c3b615b67252f344844a6a7eaf7f"
ROLLBACK = "1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2"
TEST = ROOT / "tests/test_s20plus_g986n_mainline_stage_f1.py"
IDENTITY = ("serial_sha256", "topology_sha256", "boot_id_sha256")
PHASES = ("baseline", "return")
PRECONTROL_CLOSE = "mainline-pre-control-close.json"
CURRENT_RUN = ContextVar("mainline_terminal_run", default=None)
# Populated only on a fresh physical confirmation in this single-shot process.
fresh_return_run = None


def load(path, name, sha):
    raw = view.read_file(path)
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError("changed " + path.name)
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location(name, path)
    )
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


owner = load(PARENT, "_s20_mainline_transport", PARENT_SHA)
reader = load(
    READER,
    "_s20_mainline_return",
    "1fc37c9a3bcf1b1cc6410628a766ad8b5b0f15db9104bc4f3327a6a07ef2f8e5",
)
require = owner.require
parent_review = owner.review_identity
parent_runtime = owner.retained_runtime_source
parent_configure = owner._configure_runtime
parent_section = owner.HEADING


def runtime_source():
    data = parent_runtime()
    old = PARENT.name.encode()
    require(data.count(old) == 1, "retained profile path differs")
    return data.replace(old, SCRIPT.name.encode())


def read_pair():
    raw = view.read_file(PAIR)
    require(hashlib.sha256(raw).hexdigest() == PAIR_SHA, "mainline AP pair changed")
    data = json.loads(raw)
    require(
        data["kind"] == "HOST_ONLY_S20PLUS_Y2Q_STAGE_AP_PAIR"
        and data["target"] == "SM-G986N/y2q/G986NKSS8IYC2"
        and data["raw"] == NATIVE_IMAGE
        and data["device_commands"] == 0
        and data["clear_frames_absent_from_both_boots"] is True,
        "stage qualification differs",
    )
    for role, expected in (("candidate", CANDIDATE), ("rollback", ROLLBACK)):
        part = data["archives"][role]
        require(
            part["ap"]["sha256"] == expected
            and Path(part["ap"]["path"]).name == "AP.tar.md5"
            and part["only_member"]["name"] == "boot.img.lz4"
            and part["decoded_boot"]["size"] == 67108864,
            "archive identity differs",
        )
    require(
        owner.receipt(FILTER)["sha256"]
        == "58c44217e5d523d74c2aa2ec15b1ff3673ec7892daf2c4e14d19e4f7affcdfc8"
        and hashlib.sha256(reader.shell(data["nonce"], "0" * 64).encode()).hexdigest()
        == data["return_template"],
        "first-return probe differs",
    )
    return dict(**data["archives"], nonce=data["nonce"])


def scope():
    return dict(
        partition="boot",
        candidate_attempt_maximum=1,
        rollback_attempt_maximum=1,
        candidate="instrumented-y2q-linux-6.18",
        candidate_host_commands=0,
        diagnostic_bytes_per_kernel_entry=256,
        permitted_header_stores=0,
        baseline_scans=1,
        return_scans=1,
        scan_deadline_seconds=120,
        physical_download_only_after_candidate=True,
        attendance_required=True,
        approval_seconds=900,
        preflight_and_terminal="exact-rooted-Magisk-Android",
        candidate_and_rollback_replay=False,
    )


def review_identity():
    value = parent_review()
    text = view.read_file(owner.CONTRACT).decode()
    require(
        text.count(parent_section) == 1, "missing inherited health/transport authority"
    )
    value["authority"]["inherited_transport"] = view.file_receipt(
        text.split(parent_section)[1].split("\n## ", 1)[0].encode()
    )
    value.update(
        schema="s20plus_y2q_native_stage_owner_v1",
        parent=owner.receipt(PARENT),
        stage_reader=owner.receipt(READER),
        stage_filter=owner.receipt(FILTER),
    )
    return value


def paths(phase):
    require(phase in PHASES, "invalid scan phase")
    return (
        f"mainline-{phase}-intent.json",
        f"mainline-{phase}-scan",
        f"mainline-{phase}-evidence.json",
    )


def names(phase):
    intent, raw, result = paths(phase)
    return {
        intent,
        result,
        *(raw + ext for ext in (".capture.json", ".stdout", ".stderr")),
    }


def capture_options(name):
    return dict(
        timeout=120,
        stdout_maximum=96,
        stderr_maximum=1024,
        stdout_name=name + ".stdout",
        stderr_name=name + ".stderr",
    )


def command(serial, boot):
    return [
        str(owner.engine.ADB),
        "-s",
        serial,
        "shell",
        "-T",
        "su",
        "-c",
        shlex.quote(reader.shell(owner.pair["nonce"], boot)),
    ]


def recovery_matches(health):
    proved = owner.retained_physical_recovery()
    require(
        health["target"] == proved["target"]
        and all(health[k] == proved[k] for k in IDENTITY[:2]),
        "physical recovery belongs to another endpoint",
    )


def restored_original(run, prepared, final):
    key = prepared["binding_sha256"]
    require(
        final["binding_sha256"] == key
        and final["rollback_transfer_completed"] is True
        and final["rollback_outcome_proved"] is True
        and final["resident_boot_healthy"] is True,
        "original Magisk rollback is not proved",
    )
    start, health = prepared["binding"]["preflight"], final["health"]
    owner.validate_root(run, health, "final-root")
    require(
        start["target"] == health["target"] == owner.TARGET
        and all(start[k] == health[k] for k in IDENTITY[:2])
        and start["boot_id_sha256"] != health["boot_id_sha256"],
        "restored Android identity or boot differs",
    )
    return owner.transfer_receipt(run, "final", key)


def eligible(run, prepared, final):
    if (
        not final["rollback_transfer_completed"]
        or not (run / "candidate-result.json").exists()
    ):
        return False
    result = owner.engine.read_json(run / "candidate-result.json", "candidate transfer")
    if result["classification"] != "odin_transfer_completed":
        return False
    owner.transfer_receipt(run, "candidate", prepared["binding_sha256"])
    owner.transfer_receipt(run, "final", prepared["binding_sha256"])
    return True


def make_intent(run, phase, health):
    engine = owner.engine
    prefix = "preflight-root" if phase == "baseline" else "final-root"
    owner.validate_root(run, health, prefix)
    intent = dict(
        schema="mainline-stage-read-v1",
        phase=phase,
        health=health,
        script_sha256=hashlib.sha256(
            reader.shell(owner.pair["nonce"], health["boot_id_sha256"]).encode()
        ).hexdigest(),
        pair_sha256=PAIR_SHA,
    )
    if phase == "return":
        prepared = engine.read_json(run / "prepared.json", "prepared")
        final = engine.read_json(run / "final-health.json", "original Magisk return")
        require(
            final["health"] == health and eligible(run, prepared, final),
            "unproved first return",
        )
        confirmation_name = "physical-confirmation-intent.json"
        rebind = owner.runtime.P0_PHYSICAL_REBIND_CONFIRM_NAME
        if (run / rebind).exists():
            confirmation_name = rebind
        confirmation = engine.read_json(
            run / confirmation_name, "physical rollback confirmation"
        )
        require(
            confirmation["binding_sha256"] == prepared["binding_sha256"],
            "physical confirmation differs",
        )
        intent.update(
            binding_sha256=prepared["binding_sha256"],
            rollback_sha256=restored_original(run, prepared, final),
            physical_confirmation=confirmation_name,
            physical_confirmation_sha256=engine.digest(confirmation),
            candidate_sha256=owner.transfer_receipt(
                run, "candidate", prepared["binding_sha256"]
            ),
            final_health_sha256=engine.digest(final),
        )
    return intent


def allowed(argv, run, name, kwargs):
    for phase in PHASES:
        intent, raw, result = paths(phase)
        if name != raw:
            continue
        owner.require_active()
        lease = owner.runtime._require_live_transaction()
        require(
            lease["run_dir"] == str(run)
            and kwargs == capture_options(raw)
            and all(not os.path.lexists(run / n) for n in names(phase) - {intent})
            and not os.path.lexists(run / "terminal.json"),
            "scan is outside a one-shot lease",
        )
        if phase == "baseline":
            require(
                lease["entrypoint"] == "prepare"
                and not os.path.lexists(run / "initial-download-intent.json"),
                "late baseline",
            )
        else:
            require(
                fresh_return_run == run
                and lease["entrypoint"] == "confirm_physical_rollback",
                "return acquisition lost continuity",
            )
        saved = owner.engine.read_json(run / intent, "scan intent")
        health = saved["health"]
        require(
            saved == make_intent(run, phase, health)
            and len(argv) > 2
            and argv == command(argv[2], health["boot_id_sha256"])
            and hashlib.sha256(argv[2].encode()).hexdigest() == health["serial_sha256"],
            "scan command or current target differs",
        )
        return True
    return False


def derive(run, phase, health):
    intent, raw, _ = paths(phase)
    engine = owner.engine
    stored = engine.read_json(run / intent, "scan intent")
    require(stored == make_intent(run, phase, health), "scan inputs changed")
    info = dict(
        phase=phase,
        intent_sha256=engine.digest(stored),
        boot_id_sha256=health["boot_id_sha256"],
    )
    receipt = run / (raw + ".capture.json")
    if not os.path.lexists(receipt):
        return dict(**info, state="capture_cut")
    cap = engine.raw_capture
    handle = cap.load_handle(receipt)
    stdout = cap.read_stdout(handle, maximum=96)
    stderr = cap.read_stderr(handle, maximum=1024)
    info["raw_receipt"] = owner.receipt(receipt)
    require(
        handle.name == raw
        and handle.stdout_path == run / (raw + ".stdout")
        and handle.stderr_path == run / (raw + ".stderr"),
        "stage capture stream identity differs",
    )
    if (
        type(handle.returncode) is not int
        or handle.timed_out
        or handle.output_exceeded
        or handle.producer_error_type
    ):
        return dict(**info, state="read_failed")
    try:
        parsed = reader.parse(handle.returncode, stdout, stderr)
    except ValueError:
        return dict(**info, state="read_failed")
    return dict(**info, **parsed)


def acquire(run, phase, health, serial):
    intent, raw, _ = paths(phase)
    owner.engine.durable_json(run / intent, make_intent(run, phase, health))
    owner.engine.raw_capture.acquire_command(
        command(serial, health["boot_id_sha256"]), run, raw, **capture_options(raw)
    )


def preflight(run, name, expected_serial=None):
    if name == "preflight-root":
        owner.require_new_effect_owner_clear()
    health, serial = owner.original_health(run, name, expected_serial)
    if name == "preflight-root":
        recovery_matches(health)
        acquire(run, "baseline", health, serial)
        value = derive(run, "baseline", health)
        owner.engine.durable_json(run / paths("baseline")[2], value)
        require(value["state"] == "no_record", "baseline stage absence not observed")
    return health, serial


def observe(run, prepared):
    # A host-only dwell gives the early kernel time; no candidate transport is trusted.
    if (run / "candidate-result.json").exists() and owner.engine.read_json(
        run / "candidate-result.json", "candidate"
    )["classification"] == "odin_transfer_completed":
        owner.transfer_receipt(run, "candidate", prepared["binding_sha256"])
        time.sleep(owner.engine.RECOVERY_ARRIVAL_SECONDS)
    return dict(
        environment="mainline-physical-return",
        transport_authorized=False,
        claim_verdict="NO_PROOF",
        at=owner.engine.utc_now(),
    ), None


def validate_observation(run, value, binding, initial):
    if value.get("environment") == "observer-reporting-cut":
        owner.runtime._ENGINE_VALIDATE_CANDIDATE_OBSERVATION(
            run, value, binding, initial
        )
    else:
        require(
            value
            == dict(
                schema="s20plus_g986n_b0_candidate_observation_v1",
                version=PROFILE,
                binding_sha256=binding,
                candidate_replay_permitted=False,
                environment="mainline-physical-return",
                transport_authorized=False,
                claim_verdict="NO_PROOF",
                at=value.get("at"),
            ),
            "unknown candidate observation",
        )
    require(
        value.get("claim_verdict") == "NO_PROOF"
        and value.get("transport_authorized") is False,
        "candidate observation granted control or boot proof",
    )


def first_return(run, prepared, final):
    intent, _, evidence = paths("return")
    if (run / intent).exists():
        return derive(run, "return", final["health"])
    return dict(
        phase="return",
        state="observation_gap"
        if eligible(run, prepared, final)
        else "transfer_unproved",
        binding_sha256=prepared["binding_sha256"],
        final_health_sha256=owner.engine.digest(final),
    )


@contextmanager
def bound_run(run):
    token = CURRENT_RUN.set(run)
    try:
        yield
    finally:
        CURRENT_RUN.reset(token)


def terminal_verdict(classification, claim, rollback):
    run = CURRENT_RUN.get()
    if run is None:
        run = Path(owner.runtime._require_live_transaction()["run_dir"])
    prepared = owner.engine.read_json(run / "prepared.json", "prepared")
    final = owner.engine.read_json(run / "final-health.json", "original Magisk return")
    result = first_return(run, prepared, final)
    require(
        result == owner.engine.read_json(run / paths("return")[2], "stage evidence"),
        "terminal evidence differs",
    )
    if rollback and classification == "odin_transfer_completed" and claim == "NO_PROOF":
        if result["state"] in ("paired", "unflatten_only"):
            return "PROVED_Y2Q_MAINLINE_POPULATED_ROOT_ORIGINAL_MAGISK_RETURNED", True
        if result["state"] == "fdt_only":
            return "PROVED_Y2Q_MAINLINE_FDT_ORIGINAL_MAGISK_RETURNED", True
    return "NO_PROOF_Y2Q_MAINLINE_RESIDENT_HEALTH_OBSERVED", False


def publish(run, prepared, final):
    intent, _, evidence = paths("return")
    restored_original(run, prepared, final)
    if not os.path.lexists(run / evidence):
        if (
            eligible(run, prepared, final)
            and fresh_return_run == run
            and not os.path.lexists(run / intent)
        ):
            serial = owner.validated_current_serial(
                prepared["binding"]["preflight"], final["health"]
            )
            acquire(run, "return", final["health"], serial)
        owner.engine.durable_json(run / evidence, first_return(run, prepared, final))
    with bound_run(run):
        return owner.original_publish(run, prepared, final)


def validate_namespace(run):
    with bound_run(run):
        owner.inherited_namespace(run)
    nodes = {p.name for p in run.iterdir()}
    if PRECONTROL_CLOSE in nodes:
        require_precontrol_history(run)
        require(
            owner.engine.read_json(run / PRECONTROL_CLOSE, "pre-control close")
            == precontrol_result(run),
            "pre-control close differs",
        )
    for phase in PHASES:
        intent, raw, evidence = paths(phase)
        if nodes & {raw + ".stdout", raw + ".stderr", raw + ".capture.json"}:
            require(intent in nodes, "capture without intent")
        if phase == "return" and nodes & names(phase):
            require(
                {"candidate-intent.json", "final-health.json"} <= nodes,
                "scan before original health",
            )
        if phase == "baseline" and evidence in nodes:
            health = owner.engine.read_json(run / intent, "baseline")["health"]
            value = derive(run, phase, health)
            require(
                owner.engine.read_json(run / evidence, "baseline evidence") == value,
                "baseline evidence differs",
            )
            if "initial-download-intent.json" in nodes:
                saved = owner.engine.read_json(run / "preflight.json", "preflight")
                require(
                    health
                    == {
                        k: v for k, v in saved.items() if k not in ("schema", "version")
                    }
                    and value["state"] == "no_record",
                    "baseline boot differs",
                )
        if phase == "return" and evidence in nodes:
            prepared = owner.engine.read_json(run / "prepared.json", "prepared")
            final = owner.engine.read_json(run / "final-health.json", "final return")
            require(
                owner.engine.read_json(run / evidence, "stage evidence")
                == first_return(run, prepared, final),
                "stage receipt differs",
            )
    if "initial-download-intent.json" in nodes:
        require(paths("baseline")[2] in nodes, "no qualified baseline")
    if {"terminal.json", "candidate-intent.json"} <= nodes:
        require(paths("return")[2] in nodes, "missing first-return result")
        restored_original(
            run,
            owner.engine.read_json(run / "prepared.json", "prepared"),
            owner.engine.read_json(run / "final-health.json", "original Magisk return"),
        )


def precontrol_result(run):
    return {
        "run_dir": str(run),
        "verdict": "CLOSED_BEFORE_DOWNLOAD_INTENT",
        "experiment_pass": False,
        "device_controls": 0,
    }


def require_precontrol_history(run):
    allowed_nodes = names("baseline") | {
        PRECONTROL_CLOSE,
        "preflight.json",
        "initial-download-baseline.json",
        "preflight-root.stdout",
        "preflight-root.stderr",
        "preflight-root.capture.json",
    }
    # validate_run_dir has already checked each numbered listing/cage name and file.
    require(
        all(
            p.name in allowed_nodes or p.name.startswith("p0-odin-listing-")
            for p in run.iterdir()
        ),
        "unexpected journal state before initial Download",
    )


def abort_pre_candidate(run):
    # A killed baseline reader may leave the prepare guard before any device control.
    engine = owner.engine
    run = engine.validate_run_dir(run)
    if os.path.lexists(run / "initial-download-intent.json"):
        return inherited_abort(run)
    lease = owner.runtime._require_live_transaction()
    require(
        lease["entrypoint"] == "abort_pre_candidate" and lease["run_dir"] == str(run),
        "pre-control close requires its transaction lock",
    )
    engine.require_guard(run)
    require_precontrol_history(run)
    require(not engine.candidate_claim_present(), "candidate already consumed")
    result = precontrol_result(run)
    if not os.path.lexists(run / PRECONTROL_CLOSE):
        engine.durable_json(run / PRECONTROL_CLOSE, result)
    engine.release_guard(run)
    return result


def published_precontrol(run):
    if (
        run.parent != RUN_ROOT
        or re.fullmatch(r"run-[0-9]{19}", run.name) is None
        or not run.is_dir()
        or run.resolve(strict=True) != run
        or os.path.lexists(owner.GUARD)
        or not os.path.lexists(run / PRECONTROL_CLOSE)
    ):
        return None
    require_precontrol_history(run)
    result = owner.strict_private(run / PRECONTROL_CLOSE, compact=True)
    require(result == precontrol_result(run), "saved pre-control closure differs")
    return result


def _configure_runtime(module):
    global inherited_abort
    parent_configure(module)
    engine = module.engine
    require(
        engine.EXPECTED_ANDROID_TOPOLOGY_SHA256
        in engine.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256,
        "original recovery port is outside the transport profile",
    )
    engine.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256 = frozenset(
        {engine.EXPECTED_ANDROID_TOPOLOGY_SHA256}
    )
    inherited_abort = engine.abort_pre_candidate
    engine.abort_pre_candidate = abort_pre_candidate
    module.APPROVAL_PREFIX = APPROVAL
    module.PHYSICAL_CONFIRM_PREFIX = CONFIRM
    module.PHYSICAL_REBIND_CONFIRM_PREFIX = (
        "S20PLUS-G986N-MAINLINE-STAGE-PHYSICAL-REENUM:"
    )
    module.P0_RUN_NODE_NAMES |= names("baseline") | names("return") | {PRECONTROL_CLOSE}


def enter_runtime():
    owner.pair = read_pair()
    # These retained helpers bind the endpoint identity and the payload-free abort.
    owner.marker = load(
        owner.MARKER_SOURCE, "_s20_mainline_endpoint_fields", owner.MARKER_SHA
    )
    owner.marker_source_pin = owner.receipt(owner.MARKER_SOURCE)
    owner.exit_d1 = load(
        owner.EXIT_SOURCE, "_s20_mainline_download_exit", owner.EXIT_SOURCE_SHA
    )
    name = "_s20plus_g986n_uniloader_runtime"
    runtime = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location(name, owner.P0)
    )
    runtime._uniloader_configure = _configure_runtime
    sys.modules[name] = runtime
    exec(compile(runtime_source(), str(owner.P0), "exec"), runtime.__dict__)
    runtime.install_profile()
    require(
        runtime._assert_profile_installed() is None
        and owner.engine.RECOVERY_ARRIVAL_SECONDS == 180
        and owner.engine.APPROVAL_LIFETIME_SECONDS == 900,
        "fixed runtime binding differs",
    )
    return runtime


def main(argv=None):
    global fresh_return_run
    argv = list(sys.argv[1:] if argv is None else argv)
    fresh_return_run = None
    owner.ACTIVE, owner.SCRIPT, owner.RUN_ROOT = ACTIVE, SCRIPT, RUN_ROOT
    owner.ACTIVATION = RUN_ROOT / "activation.json"
    owner.PAIR, owner.PAIR_SIZE, owner.PAIR_SHA = PAIR, 1639, PAIR_SHA
    owner.PROFILE, owner.HEADING, owner.PHASES = PROFILE, HEADING, {}
    owner.BUILDER, owner.BUILDER_SHA = PACKAGER, PACKAGER_SHA
    owner.TEST_SOURCE = TEST
    owner.effect_profile, owner.retained_runtime_source, owner.review_identity = (
        scope,
        runtime_source,
        review_identity,
    )
    owner.read_pair, owner.enter_runtime = read_pair, enter_runtime
    owner.resident_health, owner.allow_marker = preflight, allowed
    owner.observe_candidate, owner.validate_candidate_observation = (
        observe,
        validate_observation,
    )
    owner.terminal_verdict, owner.validate_namespace, owner.checked_terminal = (
        terminal_verdict,
        validate_namespace,
        publish,
    )
    if argv[:1] == ["--in-source-view"]:
        options = owner.parser().parse_args(argv[1:])
        if options.abort_pre_candidate and options.run_dir:
            closed = published_precontrol(options.run_dir.absolute())
            if closed is not None:
                print(json.dumps(closed, sort_keys=True))
                return 0
        if options.confirm_physical_rollback and options.run_dir:
            run = options.run_dir.absolute()
            if (
                run.parent == RUN_ROOT
                and run.is_dir()
                and run.resolve(strict=True) == run
                and not os.path.lexists(run / "rollback-intent.json")
            ):
                fresh_return_run = run
    return owner.main(argv)


PACKAGER_SHA = "672ea2268c813ef009ee0c2d1fc00260d494819b5084f5840be0e662c6066f7d"
if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            json.dumps(
                {
                    "verdict": "STOP_S20_MAINLINE_STAGE_F1",
                    "failure_class": type(exc).__name__,
                    **({"reason": str(exc)} if type(exc) is owner.Stop else {}),
                }
            )
        )
        raise SystemExit(2)
