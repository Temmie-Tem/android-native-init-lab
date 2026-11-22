#!/usr/bin/env python3
"""One attended S20+ PMSG calibration through physical Download and original AP."""

import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

import s20plus_g986n_twrp_observe_source_view_v1 as view

ACTIVE = False
SCRIPT = Path(__file__).resolve()
ROOT = view.ROOT
RUN_ROOT = view.PRIVATE / "runs/s20plus-g986n-pmsg-download-calibration-f1"
RUN = RUN_ROOT / "trial"
REGISTRY = view.PRIVATE / "consumed-candidate-registry-v1"
VERSION = "s20plus-g986n-pmsg-download-calibration-f1-v1"
APPROVAL = "S20PLUS-G986N-PMSG-DOWNLOAD-CALIBRATION-APPROVE:"
PHYSICAL = "S20PLUS-G986N-PMSG-DOWNLOAD-PHYSICAL:"
POLICY = ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
HEADING = "## S20+ PMSG physical Download retention calibration F1\n"
COMMON_DELEGATION = "S20PLUS_PMSG_PHYSICAL_DOWNLOAD_RETENTION_F1_V1"
TEST = ROOT / "tests/test_s20plus_g986n_pmsg_download_calibration_f1.py"
ENGINE = SCRIPT.with_name("s20plus_g986n_boot_recovery_canary_b0_f1.py")
WRITER = SCRIPT.with_name("s20plus_g986n_pmsg_warm_reboot_d1.py")
LEDGER = SCRIPT.with_name("consumed_candidate_registry_v1.py")
ENGINE_SHA = "82ec4cee48c3a39aa8dc4de6136e8fda3fbefe88d4821a71bdb0df55d2a17c2a"
WRITER_SHA = "f6c8f8faee6f9a4724d74060f1bb2385bc9a936d0b4e7dc86f118480a3df206a"
LEDGER_SHA = "e67d75137469f0435c3b9e8780c1b81d8bd5fda2d8142e03499d09784443cead"
AP_SHA = "1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2"
PRIOR = view.PRIVATE / "runs/s20plus-g986n-uniloader-stage-f1/run-1795356173121008409"
PRIOR_PINS = {
    "physical-rollback-arrival.json": "434bdb5fa8bf15d7bc5a575fc1c88e71d58de621911611957276e2b2a7674ef5",
    "rollback-result.json": "cb7c8d3ece4bbd7f1d68f5564da1ff7be12071093ac091ce114402f449ba9410",
    "rollback-transfer.capture.json": "94c896a70bebee73c3bbb9fe05e3c7f1b071307170ba5a8e9162af29724f5a07",
    "final-health.json": "9e13d1bf2f3de3104e57272371d45460f5c4024a54f3ca569595faa78019511e",
    "terminal.json": "6f9ece4fd2f0de8f8f64103a3a7c2e5a2e81a665e1273af6112c15a05f0fa47f",
}
CAGE_ROOT = Path("/sys/fs/cgroup")
PASS_GO = {"verdict": "PASS_GO", "high": 0, "medium": 0, "low": 0}
PROBE_CAPTURES = {"probe.capture.json", "probe.stdout", "probe.stderr"}
PRE_MARKER_NODES = PROBE_CAPTURES | {"prepared.json", "prepare-abort.json", "approval.json"}
ORIGINAL_BOOT = """chosen=/sys/firmware/devicetree/base/chosen
marker=$chosen/codex,y2q-uniloader-android-v1
[ -d "$chosen" ] && [ -r "$chosen" ] && [ -x "$chosen" ] || exit 64
[ ! -L "$marker" ] && [ ! -e "$marker" ] || exit 64
"""


class Stop(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise Stop(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path, expected, name):
    raw = view.read_file(path)
    require(digest(raw) == expected, f"{path.name} differs")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


warm = load(WRITER, WRITER_SHA, "_s20_pmsg_calibration_script_source")


def section(text, heading):
    require(text.count(heading) == 1, "policy section differs")
    return view.file_receipt(text.split(heading, 1)[1].split("\n## ", 1)[0].encode())


def review_identity():
    text = view.read_file(POLICY).decode()
    source = view.read_file(SCRIPT)
    dormant, count = re.subn(rb"^ACTIVE = (?:False|True)$", b"ACTIVE = False", source, flags=re.M)
    require(count == 1, "activation literal differs")
    active = dormant.replace(b"\nACTIVE = False\n", b"\nACTIVE = True\n", 1)
    agents = view.read_file(ROOT / "AGENTS.md")
    details = view.read_file(ROOT / "docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md")
    pins = re.findall(rb"The incorporated details have SHA-256:\s*`([a-f0-9]{64})`", agents)
    require(pins == [digest(details).encode()], "common policy pin differs")
    return {
        "version": VERSION, "owner_dormant": digest(dormant), "owner_active": digest(active),
        "section": section(text, HEADING),
        "readiness_section": section(text, "## S20+ Pstore/PMSG Readiness D0\n"),
        "source_view": view.view_receipt(),
        "files": {p.name: view.file_receipt(view.read_file(p)) for p in (
            ENGINE, WRITER, LEDGER, TEST, SCRIPT.with_name(warm.READINESS_NAME),
            ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md",
            ROOT / "docs/operations/DEVICE_ACTION_PROCESS_V2.md")},
        "common": digest(agents), "details": digest(details),
        "original_ap_sha256": AP_SHA, "physical_predecessor": PRIOR_PINS,
        "scope": {"marker": 1, "physical_download": 1, "boot_only_original_ap": 1,
                  "return_reader": 1, "attendance_required": True, "retry": False},
    }


def require_active():
    require(ACTIVE, "calibration is dormant")
    details = view.read_file(ROOT / "docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md")
    require(COMMON_DELEGATION.encode() in details and
            b"Status: **BINDING - PMSG DOWNLOAD CALIBRATION F1 ACTIVE**" in view.read_file(POLICY),
            "common and target calibration delegation is missing")
    identity = review_identity()
    activation = json.loads(view.read_file(RUN_ROOT / "activation.json", mode=0o400))
    require(activation == {"identity": identity, "review": PASS_GO}
            and digest(view.read_file(SCRIPT)) == identity["owner_active"], "reviewed activation differs")


def runtime():
    global engine, registry
    engine = load(ENGINE, ENGINE_SHA, "_s20_pmsg_calibration_b0")
    registry = load(LEDGER, LEDGER_SHA, "_s20_pmsg_calibration_registry")
    engine.RUN_ROOT = RUN_ROOT
    engine.CLAIM_ROOT = RUN_ROOT / "unused-candidate-roles"
    engine.VERSION = VERSION
    require(engine.ROLLBACK_AP_SHA256 == AP_SHA, "original AP identity differs")
    # The established B0 guard schema has this legacy field name.
    engine.CANDIDATE_AP_SHA256 = AP_SHA


def recovery_proof():
    records = {}
    for name, expected in PRIOR_PINS.items():
        raw = view.read_file(PRIOR / name, mode=0o400)
        require(digest(raw) == expected, "retained physical recovery evidence differs")
        records[name] = json.loads(raw)
    final, arrival, old, close = (records[name] for name in (
        "final-health.json", "physical-rollback-arrival.json", "rollback-result.json", "terminal.json"))
    handle = engine.raw_capture.load_handle(PRIOR / "rollback-transfer.capture.json")
    stdout = engine.raw_capture.read_stdout(handle, maximum=engine.MAX_RAW_BYTES)
    stderr = engine.raw_capture.read_stderr(handle, maximum=engine.MAX_RAW_BYTES)
    health = final["health"]
    require(len({record["binding_sha256"] for record in (final, arrival, old, close)}) == 1
            and arrival["branch"] == "attended-entry"
            and arrival["endpoint"]["topology_sha256"] == health["topology_sha256"]
            and health["target"] == engine.TARGET and close["rollback_transfer_completed"] is True
            and old["receipt"]["ap"]["sha256"] == AP_SHA and old["host_process_quiescence_proved"] is True
            and engine.classify_odin_capture(handle, stdout, stderr) == old["classification"]
            == "odin_transfer_completed", "retained original transfer or physical route is unproved")
    return {key: health[key] for key in ("serial_sha256", "topology_sha256")}


def probe_script(binding):
    return ORIGINAL_BOOT + warm.probe_script(binding)


def writer_script(binding):
    script = warm.write_script(binding)
    before = f"/system/bin/printf '\\n%s\\n' '{warm.marker_line(binding)}' >&4 || exit 66"
    after = before.replace(" >&4", " | /system/bin/cat >&4")
    require(script.count(before) == 1, "writer dispatch differs")
    return ORIGINAL_BOOT + "set -o pipefail\n" + script.replace(before, after)


def reader_script(binding, boot):
    script = warm.read_script(binding, boot)
    before = f"/system/bin/grep -aFx '{warm.marker_line(binding)}'"
    end = " | /system/bin/wc -l)"
    require(script.count(before) == script.count(end) == 1, "reader comparison differs")
    script = script.replace(before, "{ " + before + ' || [ "$?" = 1 ]; }')
    return ORIGINAL_BOOT + "set -o pipefail\n" + script.replace(end, end + " || exit 65")


def exists(name):
    return os.path.lexists(RUN / name)


def read(name):
    return engine.read_json(RUN / name, name)


def write(name, value):
    engine.durable_json(RUN / name, value)


def host_checks():
    return {"identity": engine.digest(review_identity()), "physical": recovery_proof(),
            "restore": engine.validate_rollback_closure(), "cage": engine.validate_process_cage_capability()}


def exact_serial(binding):
    rows = engine.adb_inventory(health_only=True)
    row = engine.exact_adb_row(rows, binding["serial_sha256"], "device")
    serial = row["serial"]
    require(digest(engine.adb_devpath(serial).encode()) == binding["topology_sha256"],
            "selected Android topology differs")
    return serial


def capture(prefix, serial, script):
    require_active()
    engine.require_guard(RUN)
    return engine.raw_capture.acquire_command(
        [str(engine.ADB), "-s", serial, "shell", "-T", "su", "-c", shlex.quote(script)],
        RUN, prefix, timeout=30, stdout_maximum=8192, stderr_maximum=1024,
        stdout_name=prefix + ".stdout", stderr_name=prefix + ".stderr")


def captured(prefix):
    path = RUN / (prefix + ".capture.json")
    handle = engine.raw_capture.load_handle(path)
    clean = not (handle.timed_out or handle.output_exceeded or handle.producer_error_type)
    return (handle.returncode if clean else None,
            engine.raw_capture.read_stdout(handle, maximum=8192),
            engine.raw_capture.read_stderr(handle, maximum=1024))


def prepare():
    require(not os.path.lexists(RUN), "one calibration trial already allocated")
    require(not engine.guard_present(), "another S20+ action is unresolved")
    closure = host_checks()
    engine.allocate_run_dir(RUN)
    engine.acquire_guard(RUN)
    try:
        backend = warm.ready.FixedBackend()
        readiness = warm.ready.collect(warm.ready.Recorder(backend))
        binding = warm.make_binding(readiness)
        require(all(binding[k] == v for k, v in closure["physical"].items()),
                "Android does not match the demonstrated physical recovery path")
        serial = exact_serial(binding)
        capture("probe", serial, probe_script(binding))
        probe = warm.parse_probe(captured("probe"))
        prepared = {"version": VERSION, "marker": binding, "probe": probe,
                    "closure": closure, "expires": int(time.time()) + 900, "at": engine.utc_now()}
        write("prepared.json", prepared)
    except Exception as error:
        if not exists("prepared.json"):
            write("prepare-abort.json", {"version": VERSION, "effects": 0, "reason": type(error).__name__})
            engine.release_guard(RUN)
        raise
    return {"status": "AWAITING_APPROVAL", "approval": APPROVAL + engine.digest(prepared),
            "expires": prepared["expires"]}


def prepared_run():
    engine.require_guard(RUN)
    prepared = read("prepared.json")
    require(prepared["version"] == VERSION and prepared["closure"]["identity"] == engine.digest(review_identity())
            and prepared["closure"]["physical"] == recovery_proof()
            and prepared["closure"]["restore"] == engine.validate_rollback_closure()
            and prepared["probe"] == warm.parse_probe(captured("probe")),
            "prepared calibration identity differs")
    warm.validate_binding(prepared["marker"])
    return prepared, engine.digest(prepared)


def write_proof(prepared, key):
    binding = prepared["marker"]
    require(read("approval.json") == {"binding_sha256": key}
            and read("marker-intent.json") == {
                "binding_sha256": key, "script_sha256": digest(writer_script(binding).encode())},
            "marker intent differs")
    result = warm.parse_write(captured("marker"), binding)
    require(read("marker-result.json") == result, "marker acceptance differs from capture")
    return result


def arm_from_writer(prepared, key):
    binding = prepared["marker"]
    require(read("approval.json") == {"binding_sha256": key}, "marker approval differs")
    require(read("marker-intent.json") == {
        "binding_sha256": key, "script_sha256": digest(writer_script(binding).encode())},
        "marker intent differs")
    if not exists("marker-result.json"):
        write("marker-result.json", warm.parse_write(captured("marker"), binding))
    source = read("source-baseline.json")
    require(source["binding_sha256"] == key, "source baseline belongs to another run")
    baseline = engine.validate_download_baseline(source["baseline"], "calibration baseline")
    arm = {"binding_sha256": key, "baseline": baseline,
           "marker_result_sha256": engine.digest(write_proof(prepared, key)),
           "expires": source["expires"]}
    if exists("download-arm.json"):
        require(read("download-arm.json") == arm, "saved physical arm differs")
    else:
        require(time.time() < arm["expires"], "physical arrival window expired")
        write("download-arm.json", arm)
    return arm


def armed_result(arm):
    return {"status": "MARKER_ACCEPTED_AWAITING_PHYSICAL_DOWNLOAD",
            "confirmation": PHYSICAL + engine.digest(arm), "expires": arm["expires"]}


def execute(approval):
    prepared, key = prepared_run()
    require({p.name for p in RUN.iterdir()} <= PRE_MARKER_NODES - {"approval.json", "prepare-abort.json"}
            and approval == APPROVAL + key and time.time() < prepared["expires"],
            "exact current approval or unused marker action is missing")
    # Establish the empty Download baseline while the exact Android boot is present.
    baseline = engine.download_baseline()
    binding = prepared["marker"]
    serial = exact_serial(binding)
    script = writer_script(binding)
    require(time.time() < prepared["expires"], "marker approval expired before intent")
    write("source-baseline.json", {"binding_sha256": key, "baseline": baseline,
                                   "expires": int(time.time()) + 900})
    write("approval.json", {"binding_sha256": key})
    write("marker-intent.json", {"binding_sha256": key, "script_sha256": digest(script.encode())})
    capture("marker", serial, script)
    return armed_result(arm_from_writer(prepared, key))


def arrival_record(arrival, prepared, key, arm):
    require(arrival is not None
            and datetime.fromisoformat(arrival["at"]).timestamp() <= arm["expires"]
            and arrival["endpoint"]["topology_sha256"] == prepared["marker"]["topology_sha256"]
            and arrival["baseline_sha256"] == engine.digest(arm["baseline"]),
            "exact physical Download arrival was not observed")
    return {**arrival, "binding_sha256": key}


def restore(prepared, key, arm):
    require(read("download-intent.json") == {"binding_sha256": key, "arm_sha256": engine.digest(arm)},
            "physical confirmation intent differs")
    arrival = read("download-arrival.json")
    require(arrival_record(arrival, prepared, key, arm) == arrival, "saved physical arrival differs")
    require_active()
    engine.require_guard(RUN)
    require(not exists("rollback-intent.json"), "original AP transfer is consumed")
    engine.transfer_boot(RUN, "rollback", arrival["endpoint"], key)
    return finalize(continuous=True)


def confirm(confirmation):
    prepared, key = prepared_run()
    arm = read("download-arm.json")
    require(arm["binding_sha256"] == key
            and arm["marker_result_sha256"] == engine.digest(write_proof(prepared, key))
            and confirmation == PHYSICAL + engine.digest(arm) and time.time() < arm["expires"]
            and not any(exists(name) for name in ("download-intent.json", "download-arrival.json",
                                                  "rollback-intent.json", "terminal.json")),
            "attended physical Download is unbound, expired or already consumed")
    write("download-intent.json", {"binding_sha256": key, "arm_sha256": engine.digest(arm)})
    try:
        arrival = engine.wait_download(arm["baseline"], timeout=min(180, arm["expires"] - time.time()))
        record = arrival_record(arrival, prepared, key, arm)
    except (engine.B0F1Error, Stop) as error:
        write("download-miss.json", {"binding_sha256": key, "reason": type(error).__name__})
        raise
    write("download-arrival.json", record)
    return restore(prepared, key, arm)


def resume():
    if exists("rollback-intent.json"):
        return finalize()
    prepared, key = prepared_run()
    arm = arm_from_writer(prepared, key)
    if not exists("download-intent.json"):
        require(time.time() < arm["expires"], "physical confirmation expired")
        return armed_result(arm)
    intent = {"binding_sha256": key, "arm_sha256": engine.digest(arm)}
    require(read("download-intent.json") == intent and not exists("download-miss.json"),
            "original physical observation failed or is unbound")
    if not exists("download-arrival.json"):
        require(not exists("resume-observation-intent.json") and time.time() < arm["expires"],
                "current Download reobservation was consumed or expired")
        write("resume-observation-intent.json", intent)
        endpoint = engine.identify_download()
        arrival = {"endpoint": endpoint, "baseline_sha256": engine.digest(arm["baseline"]),
                   "at": engine.utc_now(), "source": "bounded_current_read_after_reporting_cut"}
        write("download-arrival.json", arrival_record(arrival, prepared, key, arm))
    return restore(prepared, key, arm)


def wait_first_return(binding, key):
    deadline = time.monotonic() + 420
    first = read("first-observed-return.json") if exists("first-observed-return.json") else None
    while time.monotonic() < deadline:
        rows = engine.adb_inventory(health_only=True)
        exact = engine.target_adb_rows(rows)
        serial_rows = tuple(row for row in rows if digest(row["serial"].encode()) == binding["serial_sha256"])
        if not exact and not serial_rows:
            time.sleep(3)
            continue
        if len(serial_rows) == 1 and serial_rows[0]["state"] == "offline" and exact in ((), serial_rows):
            time.sleep(3)
            continue
        require(len(exact) == 1 and exact == serial_rows, "return Android selection differs")
        serial = engine.exact_adb_row(rows, binding["serial_sha256"], "device")["serial"]
        require(digest(engine.adb_devpath(serial).encode()) == binding["topology_sha256"],
                "return Android topology differs")
        raw = engine.base.bounded_command(
            [str(engine.ADB), "-s", serial, "exec-out", "sh", "-c", engine.PUBLIC_SNAPSHOT_SCRIPT],
            20, engine.MAX_ADB_BYTES)
        values = engine._ordered_output(raw, engine.PUBLIC_SNAPSHOT_KEYS, "calibration return")
        require(all(values[field] == engine.TARGET[key] for (field, key) in (
            ("model", "model"), ("device", "device"), ("product_name", "product"),
            ("incremental", "incremental"))) and values["selinux"] == "Enforcing"
                and engine.BOOT_ID_RE.fullmatch(values["boot_id"]) is not None
                and values["boot_completed"] in ("", "0", "1")
                and values["bootanim"] in ("", "running", "stopped"), "return Android state differs")
        boot = digest(values["boot_id"].encode())
        require(boot != binding["source_boot_sha256"], "return reused the source boot")
        arrived = {"binding_sha256": key, "boot_sha256": boot}
        if first is None:
            write("first-observed-return.json", arrived)
            first = arrived
        else:
            require(first == arrived, "observed return changed boots before Android completed")
        if (values["boot_completed"], values["bootanim"]) != ("1", "stopped"):
            time.sleep(3)
            continue
        engine.parse_public_snapshot(raw)
        return first
    raise Stop("original Android return is pending")


def validate_health(health, name):
    engine._validate_resident_health_receipt(RUN, health, "calibration original health", name)
    handle = engine.raw_capture.load_handle(Path(health["root_capture"]["path"]))
    require(handle.returncode == 0 and not (handle.timed_out or handle.output_exceeded
                                           or handle.producer_error_type), "root health producer failed")


def finalize(*, continuous=False):
    prepared, key = prepared_run()
    write_proof(prepared, key)
    intent = read("rollback-intent.json")
    endpoint = read("download-arrival.json")["endpoint"]
    require(intent["version"] == VERSION and intent["binding_sha256"] == key and intent["kind"] == "rollback"
            and intent["ap_sha256"] == AP_SHA and intent["attempt"] == 1 and intent["no_replay"] is True
            and engine.same_download_session(endpoint, intent["endpoint"]), "original transfer intent differs")
    engine._validate_process_cage_binding(intent["process_cage"], "rollback", key)
    engine.require_transfer_process_quiescence(RUN, "rollback", key)
    result = read("rollback-result.json")
    engine._validate_transfer_outcome(RUN, result, "rollback", key)
    require(result["classification"] == "odin_transfer_completed", "original AP transfer remains unproved")
    binding = prepared["marker"]
    if not exists("first-observed-return.json") and not continuous and not exists("return-observation-gap.json"):
        write("return-observation-gap.json", {"binding_sha256": key})
    if not exists("final-health.json"):
        arrival = wait_first_return(binding, key)
        health, _ = engine.resident_health_once(RUN, "final-root", binding["serial_sha256"])
        validate_health(health, "final-root")
        require(health["topology_sha256"] == binding["topology_sha256"]
                and health["boot_id_sha256"] == arrival["boot_sha256"], "return boot differs from first arrival")
        write("final-health.json", health)
    arrival = read("first-observed-return.json")
    require(arrival["binding_sha256"] == key, "return arrival belongs to another run")
    final = read("final-health.json")
    validate_health(final, "final-root")
    require(final["serial_sha256"] == binding["serial_sha256"] and final["topology_sha256"] == binding["topology_sha256"]
            and final["boot_id_sha256"] == arrival["boot_sha256"]
            and final["boot_id_sha256"] != binding["source_boot_sha256"], "saved return identity differs")
    boot = final["boot_id_sha256"]
    script = reader_script(binding, boot)
    intent = {"binding_sha256": key, "return_health_sha256": engine.digest(final),
              "rollback_sha256": engine.digest(result), "script_sha256": digest(script.encode())}
    if not exists("read-intent.json"):
        serial = exact_serial(binding)
        write("read-intent.json", intent)
        capture("comparison", serial, script)
    require(read("read-intent.json") == intent, "return observation intent differs")
    comparison = None
    if exists("comparison.capture.json"):
        try:
            comparison = warm.parse_read(captured("comparison"))
        except warm.health.RootHealthD0Error:
            pass  # The intent is consumed even when collection fails.
        except warm.MarkerError:
            pass
    if not exists("return-bracket.json"):
        after, _ = engine.resident_health_once(RUN, "after-comparison-root", binding["serial_sha256"])
        validate_health(after, "after-comparison-root")
        require(all(after[k] == final[k] for k in ("serial_sha256", "topology_sha256", "boot_id_sha256")),
                "same-boot health after comparison is unproved")
        write("return-bracket.json", after)
    after = read("return-bracket.json")
    validate_health(after, "after-comparison-root")
    require(all(after[k] == final[k] for k in ("serial_sha256", "topology_sha256", "boot_id_sha256")),
            "saved return bracket differs")
    gap = exists("return-observation-gap.json")
    require(not gap or read("return-observation-gap.json") == {"binding_sha256": key}, "return gap differs")
    value = {"binding_sha256": key, "version": VERSION, "observation_gap": gap,
             "verdict": "RETAINED" if comparison and comparison["matches"] == 1 and not gap else "NO_PROOF_RETENTION",
             "comparison": comparison, "final_health_sha256": engine.digest(final),
             "same_boot_after_sha256": engine.digest(after), "original_transfers": 1,
             "marker_writes": 1, "other_target_commands": 0, "replay": False}
    if exists("terminal.json"):
        require(read("terminal.json") == value, "terminal differs from capture")
    else:
        write("terminal.json", value)
    engine.release_guard(RUN)
    return value


def abort():
    engine.require_guard(RUN)
    require({p.name for p in RUN.iterdir()} <= PRE_MARKER_NODES - {"approval.json"},
            "an approved or attempted marker requires its owning recovery")
    if not exists("prepare-abort.json"):
        write("prepare-abort.json", {"version": VERSION, "effects": 0, "reason": "operator-abort"})
    engine.release_guard(RUN)
    return {"status": "ABORTED_BEFORE_MARKER"}


def cgroup_identity(path):
    require(path != CAGE_ROOT and path.is_relative_to(CAGE_ROOT)
            and path.resolve(strict=True) == path and path.is_dir(), "cgroup path is indirect")
    info = path.stat()
    require(info.st_uid == os.getuid(), "cgroup owner differs")
    return [info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid]


def recovery_cgroup():
    if not exists("rollback-intent.json") or exists("rollback-cage-quiescent.json"):
        return ()
    guard = json.loads(view.read_file(view.RUN_ROOT / "active-action.json", mode=0o400))
    require(guard == {"schema": "s20plus_g986n_boot_recovery_canary_b0_guard_v1",
                      "version": VERSION, "run_dir": str(RUN), "candidate_sha256": AP_SHA,
                      "unresolved": True}, "retained cage owner differs")
    prepared = json.loads(view.read_file(RUN / "prepared.json", mode=0o400))
    key = digest((json.dumps(prepared, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode())
    intent = json.loads(view.read_file(RUN / "rollback-intent.json", mode=0o400))
    bound = intent["process_cage"]
    parent = Path(bound["parent"])
    require(intent["binding_sha256"] == bound["binding_sha256"] == key
            and bound["version"] == VERSION and bound["kind"] == "rollback"
            and bound["cage"] == str(parent / f"s20plus-b0-rollback-{key[:20]}"),
            "retained cage binding differs")
    boot = digest(Path("/proc/sys/kernel/random/boot_id").read_text().strip().encode())
    if boot != bound["host_boot_id_sha256"]:
        require(not os.path.lexists(bound["cage"]), "prior-boot cage still exists")
        return ()
    require(cgroup_identity(parent) == bound["parent_identity"], "retained cage parent differs")
    return (parent,)


def source_view(argv, connected):
    prefix = view.command(observe=False)
    prefix = prefix[:prefix.index("--chdir")]
    group = Path("/proc/self/cgroup").read_text().strip().removeprefix("0::")
    cage = CAGE_ROOT / group.lstrip("/")
    require(group.startswith("/") and cgroup_identity(cage), "direct owned cgroup is unavailable")
    writable = (RUN_ROOT, cage)
    if connected:
        lock = REGISTRY / "target-session.lock"
        writable += (view.RUN_ROOT, lock, *recovery_cgroup())
        prefix += ["--dev-bind", "/dev/bus/usb", "/dev/bus/usb"]
    for path in dict.fromkeys(writable):
        require(path.resolve(strict=True) == path, "source-view write bind is indirect")
        prefix += ["--bind", str(path), str(path)]
    return [*prefix, "--chdir", str(SCRIPT.parent), "--", str(view.PYTHON), "-E", "-s", "-B",
            str(SCRIPT), "--in-source-view", *argv]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    inner = argv[:1] == ["--in-source-view"]
    if inner:
        argv.pop(0)
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    for mode in ("review-input", "validate-host", "prepare", "execute", "confirm-physical", "resume", "finalize", "abort"):
        modes.add_argument("--" + mode, action="store_true")
    parser.add_argument("--approval")
    parser.add_argument("--confirmation")
    args = parser.parse_args(argv)
    if args.review_input:
        print(json.dumps(review_identity(), sort_keys=True))
        return 0
    if not inner:
        if not args.validate_host:
            require_active()
        return subprocess.run(source_view(argv, not args.validate_host), env=view.clean_environment()).returncode
    runtime()
    if args.validate_host:
        print(json.dumps({"status": "PASS_CALIBRATION_HOST", "closure_sha256": engine.digest(host_checks()),
                          "device_commands": 0}))
        return 0
    require_active()
    with registry.target_session_lease(ROOT, research_read_only=args.finalize or args.abort):
        if args.prepare or args.execute:
            registry.require_no_f1_owner(ROOT)
            require(not os.path.lexists(view.CAMPAIGN_GUARD), "S20+ campaign already owns the target")
        if args.prepare:
            value = prepare()
        elif args.execute:
            value = execute(args.approval)
        elif args.confirm_physical:
            value = confirm(args.confirmation)
        elif args.resume:
            value = resume()
        elif args.finalize:
            value = finalize()
        else:
            value = abort()
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"status": "STOP_CALIBRATION", "failure_class": type(error).__name__,
                          **({"reason": str(error)} if type(error) is Stop else {})}))
        raise SystemExit(2)
