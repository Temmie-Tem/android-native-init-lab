#!/usr/bin/env python3
"""First original boot restoration after the deferred-worker observation miss."""
import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import s20plus_g986n_deferred_worker_f1 as trial

owner, base, stage, require = trial.owner, trial.base, trial.stage, trial.require
ROOT = trial.parent.ROOT
SCRIPT = Path(__file__).resolve()
RUN = trial.RUN_ROOT / "run-1795780019923307510"
TICKET = trial.RUN_ROOT / "ticket-1795780019923307510"
BINDING = "a883dae102a58a035c4aa36af4ba9ff925ec1d3538912f813c7fe36b321983c7"
ORIGINAL = trial.parent.ORIGINAL
POLICY = ROOT / "docs/operations/S20PLUS_DEFERRED_WORKER_ONE_RUN_RECOVERY_2026-11-27.md"
TEST = ROOT / "tests/test_s20plus_g986n_deferred_incident_recovery.py"
AUTH = TICKET / "incident-review.json"
PREFIX = "S20PLUS-ONE-ORIGINAL-RECOVERY:"
INTENT = "incident-identification-intent.json"
ARRIVAL = "incident-download-arrival.json"
HISTORY = {
    "prepared.json": "4bbff07ace23be2ded3f235a85bc017b0407c7f11a0b4fe6409fac2ffc94ddb3",
    "candidate-result.json": "86b5b76d81ed1f44140d709154d912d6b30a2d54bbdeeb82f4e23dd4472eafe7",
    "physical-observation-miss.json": "11efcad4b9ee490f7848194fc2bad12dcb9d08f6abf33c406c49a8aa1d051ccb",
}
OLD_ROOT = "2a178f6c5d39049ab3f2b1efaf1eb71bdd49635013ab27dfc84bc16fa98269ff"
OLD_ACTIVATION = "89cd0c71af973eca5560186ea4992d4948980f60d96418c8328e9ba881e06a52"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return owner.strict_private(path, compact=True)


def historical_common(data):
    # Reproduce the old ticket identity while binding the complete current
    # policy bytes separately in the independent incident authorization.
    old, marker, addition = data.partition(b"\nFor S20+ deferred-worker run ")
    require(bool(marker) and sha(old) == OLD_ROOT and addition.endswith(b"earlier physical observation stays consumed.\n"),
            "original common contract or incident adoption differs")
    return original_common(old)


original_common = owner.common_authority


def identity():
    files = [SCRIPT, TEST, POLICY, ROOT / "AGENTS.md", owner.CONTRACT,
             ROOT / "docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md"]
    return {"binding": BINDING, "original": ORIGINAL, "inherited": OLD_ACTIVATION,
            "files": {str(p.relative_to(ROOT)): sha(base.view.read_file(p)) for p in files}}


def reviewed():
    require(json.loads(base.view.read_file(AUTH, mode=0o400)) ==
            {"identity": identity(), "review": owner.REVIEW_PASS}, "incident execution review differs")


def history():
    for name, digest in HISTORY.items():
        base.pinned(RUN / name, digest)
    base.pinned(owner.ACTIVATION, OLD_ACTIVATION)
    ticket, _ = base.accepted(RUN)
    base.initial_proof(RUN, ticket)


def clear_owner():
    e = owner.engine
    e.require_guard(RUN)
    owner.require_new_effect_owner_clear()
    e.require_candidate_claim(RUN, BINDING)
    e.require_all_transfer_processes_quiescent(RUN, BINDING)


def grant(issued):
    return dict(run=str(RUN), binding=BINDING, original=ORIGINAL, issued=issued,
                expires=issued + 900, review=sha(base.view.read_file(AUTH, mode=0o400)))


def valid_token(token, *, fresh):
    issued = token.removeprefix(PREFIX).split("-", 1)[0]
    require(len(issued) == 10 and issued.isascii() and issued.isdigit(), "expected exact incident approval")
    value = grant(int(issued))
    key = owner.engine.digest(value)
    require(token == f"{PREFIX}{issued}-{key}" and read(TICKET / f"incident-grant-{issued}.json") == value,
            "incident approval differs")
    if fresh:
        require(value["issued"] <= time.time() < value["expires"], "incident grant expired")
    return value


def check_endpoint(endpoint):
    e = owner.engine
    e._validate_endpoint(endpoint, "incident Download")
    prepared = read(RUN / "prepared.json")["binding"]["endpoint"]
    require(endpoint["usb"] == prepared["usb"] and endpoint["topology_sha256"] == prepared["topology_sha256"],
            "incident Download differs from original port or USB identity")


def incident_arrival(run):
    require(run == RUN, "incident run differs")
    intent, arrival = read(run / INTENT), read(run / ARRIVAL)
    value = valid_token(intent["approval"], fresh=False)
    require(intent == {"binding": BINDING, "approval": intent["approval"], "original": ORIGINAL}
            and arrival == {"endpoint": arrival["endpoint"], "intent": owner.engine.digest(intent),
                            "observed": arrival["observed"]}
            and type(arrival["observed"]) is int and value["issued"] <= arrival["observed"] < value["expires"],
            "incident arrival lacks a timely accepted identification")
    check_endpoint(arrival["endpoint"])
    require(owner.engine.same_download_session(arrival["endpoint"], read(run / "rollback-intent.json")["endpoint"]),
            "rollback differs from incident endpoint")


def dispatch_check(run):
    require(run == RUN and owner.runtime._require_live_transaction() ==
            {"entrypoint": "confirm_physical_rollback", "run_dir": str(RUN)}, "incident transfer lost lease")
    reviewed()
    owner.engine.require_guard(run)
    incident_arrival(run)
    endpoint = read(run / "rollback-intent.json")["endpoint"]
    require(owner.engine.endpoint_stat(endpoint["device"]) == tuple(endpoint["endpoint_identity"]),
            "incident endpoint changed at dispatch")
    valid_token(read(run / INTENT)["approval"], fresh=True)


def check_branches(run):
    for node in run.iterdir():
        require(not node.name.startswith(("rollback-download-", "rollback-reboot.", "p0-physical-rollback-rebind",
                                         "abort-return-")) and node.name not in {
            "physical-rollback-arrival.json", "physical-resume-observation-intent.json",
            "candidate-transfer-cut.json", "rollback-transfer-cut.json",
        }, "conflicting recovery history")


def require_unused(run):
    check_branches(run)
    consumed = {INTENT, ARRIVAL, "final-health.json", "terminal.json"}
    require(not any(n.name in consumed or n.name.startswith(("rollback-", "rollback.", "p0-rollback-cage-"))
                    for n in run.iterdir()), "incident identification or rollback consumed")


def clean_baseline(run, prepared):
    source = stage.derive(run, "baseline", prepared["binding"]["preflight"])
    require(source["state"] == "no_record" and source == read(run / "mainline-baseline-evidence.json"),
            "source marker baseline differs")


def archived(run):
    e = owner.engine
    incident_arrival(run)
    check_branches(run)
    prepared = read(run / "prepared.json")
    final = read(run / "final-health.json")
    history()
    clean_baseline(run, prepared)
    trial.cstage.previous.archived_claim(run, BINDING)
    stage.restored_original(run, prepared, final)
    required = {"prepared", "approval", "candidate-intent", "candidate-result", "candidate-cage-quiescent",
                "candidate-observation-intent", "candidate-observation", "physical-rollback-intent",
                "physical-confirmation-intent", "physical-observation-intent", "physical-observation-miss",
                "rollback-intent", "rollback-cage-quiescent", "rollback-result", "final-health", "terminal"}
    require(all((run / (name + ".json")).is_file() for name in required), "incomplete archived incident")
    with stage.bound_run(run):
        e.validate_critical_records(run, {name + ".json" for name in required})
    return read(run / "terminal.json")


def recover(run, token):
    require(run == RUN and owner.runtime._require_live_transaction() ==
            {"entrypoint": "confirm_physical_rollback", "run_dir": str(run)}, "incorrect incident owner")
    history()
    reviewed()
    e = owner.engine
    if (run / "terminal.json").exists():
        result = archived(run)
        if os.path.lexists(owner.GUARD):
            e.require_guard(run)
            e.release_guard(run)
        return result
    clear_owner()
    check_branches(run)
    prepared = e.read_prepared(run, phase="rollback")
    clean_baseline(run, prepared)
    if os.path.lexists(run / "rollback-intent.json"):
        incident_arrival(run)
        owner.transfer_receipt(run, "final", BINDING)
        e.finalize_resident(run)
        return archived(run)
    require_unused(run)
    valid_token(token, fresh=True)
    intent = dict(binding=BINDING, approval=token, original=ORIGINAL)
    e.durable_json(run / INTENT, intent)
    endpoint = e.identify_download()
    check_endpoint(endpoint)
    valid_token(token, fresh=True)
    e.durable_json(run / ARRIVAL, dict(intent=e.digest(intent), observed=int(time.time()), endpoint=endpoint))
    stage.fresh_return_run = run
    try:
        e.rollback_from_arrival(run, prepared, endpoint)
    finally:
        stage.fresh_return_run = None
    return archived(run)


def bind():
    trial.bind()
    make_intent = stage.make_intent

    def scan_intent(run, phase, health):
        value = make_intent(run, phase, health)
        if phase == "return":
            incident_arrival(run)
            value["incident_arrival_sha256"] = owner.engine.digest(read(run / ARRIVAL))
        return value

    stage.make_intent = scan_intent
    owner.common_authority = historical_common
    parent_configure = trial.parent._configure_runtime

    def configure(module):
        parent_configure(module)
        module.P0_RUN_NODE_NAMES |= {INTENT, ARRIVAL}
        module._confirm_physical_rollback_with_rebind = recover
        module._incident_dispatch = dispatch_check
        # Only relax the missing normal arrival predicate on this private engine
        # instance. All other namespace and receipt validations remain intact.
        e = module.engine
        src = inspect.getsource(module._ENGINE_VALIDATE_NAMESPACE)
        fail = 'raise B0F1Error("rollback intent has no bound Download arrival")'
        require(src.count(fail) == 1 and owner.receipt(module.ENGINE_PATH)["sha256"] == owner.P0_ENGINE_SHA,
                "inherited namespace differs")
        release = e.release_guard

        def release_validated(run):
            archived(run)
            release(run)

        finish = e.final_health_and_terminal

        def after_proved_transfer(run, prepared):
            owner.transfer_receipt(run, "final", BINDING)
            return finish(run, prepared)

        e.final_health_and_terminal = after_proved_transfer
        e.release_guard = release_validated
        e._incident_arrival = incident_arrival
        local = {}
        exec(compile(src.replace(fail, "_incident_arrival(run_dir)"), str(module.ENGINE_PATH), "exec"),
             e.__dict__, local)
        module._ENGINE_VALIDATE_NAMESPACE = local["validate_namespace"]

    trial.parent._configure_runtime = configure
    original_source = stage.runtime_source

    def runtime_source():
        src = original_source()
        call = b"                result = original(argv, capture_dir, name, **kwargs)"
        require(src.count(call) == 1, "raw effect boundary differs")
        return src.replace(call, b'                if name == "rollback-transfer":\n'
                           b'                    _incident_dispatch(Path(capture_dir))\n' + call)
    stage.runtime_source = runtime_source


def issue():
    require(read(owner.GUARD) == owner.engine.guard_value(RUN), "original guard differs")
    require_unused(RUN)
    issued = int(time.time())
    value = grant(issued)
    base.put(TICKET, f"incident-grant-{issued}", value)
    print(json.dumps({"approval": f"{PREFIX}{issued}-{owner.engine.digest(value)}", "expires": value["expires"]}))


def main(argv):
    p = argparse.ArgumentParser()
    modes = p.add_mutually_exclusive_group(required=True)
    for mode in ("check", "issue", "restore", "resume"):
        modes.add_argument("--" + mode, action="store_true")
    p.add_argument("--approval", default="")
    p.add_argument("--inside", action="store_true")
    a = p.parse_args(argv)
    bind()
    if not a.inside:
        cmd = owner.namespace(["--recover", "--run-dir", str(RUN)], connected=a.restore or a.resume)
        cmd = cmd[:cmd.index(str(trial.SCRIPT))] + [str(SCRIPT), "--inside", *argv]
        return subprocess.run(cmd, env=base.view.clean_environment()).returncode
    base.cal.runtime()
    stage.enter_runtime()
    history()
    owner.require_active()
    if a.check:
        owner.retained_physical_recovery()
        owner.engine.validate_rollback_closure()
        print(json.dumps({"status": "INCIDENT_HOST_VERIFIED", "identity": identity()}))
        return 0
    reviewed()
    with base.exclusive(RUN):
        if a.issue:
            issue()
        else:
            require(a.restore or (RUN / "rollback-intent.json").exists(), "resume requires prior rollback intent")
            if (RUN / "terminal.json").exists() and (not os.path.lexists(owner.GUARD)
                    or read(owner.GUARD) != owner.engine.guard_value(RUN)):
                result = archived(RUN)
            else:
                result = owner.engine.confirm_physical_rollback(RUN, a.approval)
            trial.render(result, RUN)
            print(json.dumps({"verdict": result["verdict"]}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:
        print(json.dumps({"status": "STOP_S20PLUS_INCIDENT", "error": type(exc).__name__, "reason": str(exc)[:180]}))
        sys.exit(2)
