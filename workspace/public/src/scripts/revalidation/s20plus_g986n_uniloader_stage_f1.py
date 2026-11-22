#!/usr/bin/env python3
"""Exact successor S20+ UniLoader owner with one first-return pstore read."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import s20plus_g986n_twrp_observe_source_view_v1 as source_view

ACTIVE = True
SCRIPT = Path(__file__).resolve()
ROOT = source_view.ROOT
SCRIPTS = SCRIPT.parent
TEMPLATE = SCRIPTS / "s20plus_g986n_uniloader_android_f1.py"
TEMPLATE_SHA = "5a8d865ccac1d4c1dde94088fb2ea0550a0d0b80727d4d7e9d6da9b20fe53d42"
READER = SCRIPTS / "s20plus_g986n_uniloader_return_pstore.py"
TEST = ROOT / "tests/test_s20plus_g986n_uniloader_stage_f1.py"
RUN_ROOT = source_view.PRIVATE / "runs/s20plus-g986n-uniloader-stage-f1"
PAIR = source_view.PRIVATE / "outputs/s20plus-y2q-uniloader-stage-h0-20261122-final/physical-prep/artifact-pair.json"
PAIR_SIZE = 2_057
PAIR_SHA = "b536fc3eef2ef7c3cd1bb0bc6cc4cd06256ec244e9d89d47050d210992d4829a"
PROFILE = "s20plus-g986n-uniloader-stage-v1"
HEADING = "## S20+ UniLoader retained boot-stage attended F1\n"
APPROVAL_PREFIX = "S20PLUS-G986N-UNILOADER-STAGE-F1-APPROVE:"
CAPTURE = "uniloader-return-pstore"
INTENT = CAPTURE + "-intent.json"
EVIDENCE = CAPTURE + "-evidence.json"
RAW_NODE = CAPTURE + ".capture.json"
NODES = {INTENT, EVIDENCE, RAW_NODE, CAPTURE + ".stdout", CAPTURE + ".stderr"}


def load(path, name, raw):
    module = importlib.util.module_from_spec(importlib.util.spec_from_file_location(name, path))
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


template_raw = source_view.read_file(TEMPLATE)
if hashlib.sha256(template_raw).hexdigest() != TEMPLATE_SHA:
    raise ValueError("inherited UniLoader owner differs")
owner = load(TEMPLATE, "_s20plus_g986n_uniloader_stage_template", template_raw)
inherited_heading = owner.HEADING
reader_raw = source_view.read_file(READER)
reader = load(READER, "_s20plus_g986n_uniloader_return_pstore", reader_raw)
template_runtime = owner.retained_runtime_source
template_review = owner.review_identity
template_configure = owner._configure_runtime
template_pair = owner.read_pair
template_namespace = owner.validate_namespace
template_scope = owner.effect_profile
require = owner.require


def effect_profile():
    return {**template_scope(), "first_return_pstore": {
        "attempt_maximum": 1, "paths": ["/sys/fs/pstore/pmsg-ramoops-0",
                                        "/sys/fs/pstore/console-ramoops-0"],
        "deadline_seconds": reader.SECONDS, "digest_or_match_only": True,
        "original_health_and_fdt_absence_required": True,
    }}


def retained_runtime_source():
    raw = template_runtime()
    old, new = TEMPLATE.name.encode(), SCRIPT.name.encode()
    require(raw.count(old) == 1, "retained P0 stage owner path differs")
    return raw.replace(old, new)


def review_identity():
    value = template_review()
    authority = source_view.read_file(owner.CONTRACT).decode()
    require(authority.count(inherited_heading) == 1, "inherited UniLoader authority differs")
    inherited_section = authority.split(inherited_heading, 1)[1].split("\n## ", 1)[0]
    value["authority"]["inherited_uniloader_section"] = source_view.file_receipt(inherited_section.encode())
    value.update(schema="s20plus_g986n_uniloader_stage_f1_review_v1",
                 inherited_owner=owner.receipt(TEMPLATE), first_return_reader=owner.receipt(READER),
                 first_return_tests=owner.receipt(TEST))
    require(value["first_return_reader"] == source_view.file_receipt(reader_raw),
            "loaded return reader bytes differ")
    return value


def read_pair():
    value = template_pair()
    tag = value["retained_stage"]["tag"]
    require(type(tag) is str and reader.HEX.fullmatch(tag) is not None
            and reader.sha256(tag.encode() + b"\0") == value["marker"]["sha256_with_nul"],
            "retained stage marker differs")
    return value


def eligible_candidate(run, prepared):
    if not os.path.lexists(run / "candidate-result.json"):
        return None
    result = owner.engine.read_json(run / "candidate-result.json", "candidate transfer")
    if result["classification"] != "odin_transfer_completed":
        return None
    return owner.transfer_receipt(run, "candidate", prepared["binding_sha256"])


def make_intent(run, prepared, final):
    boot = final["health"]["boot_id_sha256"]
    stage = eligible_candidate(run, prepared)
    rollback = owner.transfer_receipt(run, "final", prepared["binding_sha256"])
    require(final["rollback_transfer_completed"] is True and stage is not None,
            "pstore read requires both proved transfers")
    owner.validate_root(run, final["health"], "final-root")
    return {"schema": "s20plus_g986n_uniloader_return_pstore_intent_v1",
            "binding_sha256": prepared["binding_sha256"], "candidate_result_sha256": stage,
            "rollback_result_sha256": rollback, "final_health_sha256": owner.engine.digest(final),
            "boot_sha256": boot, "reader_sha256":
                reader.sha256(reader.script(owner.pair["retained_stage"]["tag"], boot).encode())}


def capture_options():
    return {"timeout": reader.SECONDS, "stdout_maximum": reader.STDOUT, "stderr_maximum": reader.STDERR,
            "stdout_name": CAPTURE + ".stdout", "stderr_name": CAPTURE + ".stderr"}


def allow_read(command, run, name, kwargs):
    if name != CAPTURE:
        return owner.allow_marker(command, run, name, kwargs)
    owner.require_active()
    lease = owner.runtime._require_live_transaction()
    engine = owner.engine
    require(lease["run_dir"] == str(run) and len(command) >= 3
            and kwargs == capture_options()
            and not any(os.path.lexists(run / node) for node in NODES - {INTENT})
            and not os.path.lexists(run / "terminal.json"), "pstore read escaped exact final capture")
    prepared = engine.read_json(run / "prepared.json", "prepared binding")
    final = engine.read_json(run / "final-health.json", "original final health")
    intent = make_intent(run, prepared, final)
    require(engine.read_json(run / INTENT, "pstore read intent") == intent
            and command == reader.argv(command[2], owner.pair["retained_stage"]["tag"], intent["boot_sha256"])
            and reader.sha256(command[2].encode()) == final["health"]["serial_sha256"],
            "pstore read command or binding differs")
    return True


def derive_evidence(run, prepared, final):
    engine = owner.engine
    candidate = eligible_candidate(run, prepared)
    common = {"schema": "s20plus_g986n_uniloader_return_pstore_evidence_v1",
              "binding_sha256": prepared["binding_sha256"],
              "final_health_sha256": engine.digest(final), "boot_sha256": final["health"]["boot_id_sha256"]}
    if candidate is None:
        require(not any(os.path.lexists(run / name) for name in NODES - {EVIDENCE}),
                "pstore data appeared without a proved candidate")
        return {**common, "status": "SKIPPED_UNPROVED_CANDIDATE", "observation": None}
    intent = make_intent(run, prepared, final)
    require(engine.read_json(run / INTENT, "pstore read intent") == intent, "pstore read intent differs")
    if not os.path.lexists(run / RAW_NODE):
        return {**common, "intent_sha256": engine.digest(intent), "status": "CAPTURE_CUT", "observation": None}
    capture = engine.raw_capture
    handle = capture.load_handle(run / RAW_NODE)
    clean = not handle.timed_out and not handle.output_exceeded and not handle.producer_error_type
    stdout = capture.read_stdout(handle, maximum=reader.STDOUT)
    stderr = capture.read_stderr(handle, maximum=reader.STDERR)
    observation = reader.decode(handle.returncode if clean else None, stdout, stderr, intent["boot_sha256"])
    return {**common, "intent_sha256": engine.digest(intent), "raw_receipt": owner.receipt(run / RAW_NODE),
            "status": "READ_RESULT", "observation": observation}


def checked_terminal(run, prepared, final):
    engine = owner.engine
    require(final["rollback_transfer_completed"] is True, "original Magisk rollback is not proved")
    if not os.path.lexists(run / EVIDENCE):
        if eligible_candidate(run, prepared) is not None and not os.path.lexists(run / INTENT):
            intent = make_intent(run, prepared, final)
            serial = owner.validated_current_serial(prepared["binding"]["preflight"], final["health"])
            engine.durable_json(run / INTENT, intent)
            engine.raw_capture.acquire_command(
                reader.argv(serial, owner.pair["retained_stage"]["tag"], intent["boot_sha256"]),
                run, CAPTURE, **capture_options())
        engine.durable_json(run / EVIDENCE, derive_evidence(run, prepared, final))
    require(engine.read_json(run / EVIDENCE, "retained stage evidence") == derive_evidence(run, prepared, final),
            "retained stage evidence is not raw-derived")
    return owner.checked_terminal(run, prepared, final)


def validate_namespace(run):
    template_namespace(run)
    nodes = {entry.name for entry in run.iterdir()}
    if nodes & NODES:
        require({"final-health.json", "candidate-intent.json", "rollback-result.json"} <= nodes,
                "pstore observation escaped original return")
        if nodes & (NODES - {EVIDENCE}):
            require(INTENT in nodes, "pstore bytes have no durable intent")
    if "terminal.json" in nodes and "candidate-intent.json" in nodes:
        require(EVIDENCE in nodes, "closed stage run lacks the retained evidence result")
    if EVIDENCE in nodes:
        engine = owner.engine
        prepared = engine.read_json(run / "prepared.json", "prepared binding")
        final = engine.read_json(run / "final-health.json", "original final health")
        require(engine.read_json(run / EVIDENCE, "retained stage evidence") == derive_evidence(run, prepared, final),
                "retained stage evidence is not raw-derived")


def _configure_runtime(module):
    template_configure(module)
    module.APPROVAL_PREFIX = APPROVAL_PREFIX
    module.P0_RUN_NODE_NAMES |= NODES
    module._profile_read_command_allowed = allow_read
    owner.engine.publish_terminal_from_final = checked_terminal


def main(argv=None):
    owner.ACTIVE = ACTIVE
    owner.SCRIPT = SCRIPT
    owner.RUN_ROOT = RUN_ROOT
    owner.ACTIVATION = RUN_ROOT / "activation.json"
    owner.PAIR, owner.PAIR_SIZE, owner.PAIR_SHA = PAIR, PAIR_SIZE, PAIR_SHA
    owner.PROFILE, owner.HEADING = PROFILE, HEADING
    owner.read_pair, owner.review_identity = read_pair, review_identity
    owner.effect_profile = effect_profile
    owner.validate_namespace = validate_namespace
    owner.retained_runtime_source = retained_runtime_source
    owner._configure_runtime = _configure_runtime
    return owner.main(argv)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"verdict": "STOP_UNILOADER_STAGE_F1", "failure_class": type(exc).__name__,
                          **({"reason": str(exc)} if type(exc) is owner.Stop else {})}))
        raise SystemExit(2)
