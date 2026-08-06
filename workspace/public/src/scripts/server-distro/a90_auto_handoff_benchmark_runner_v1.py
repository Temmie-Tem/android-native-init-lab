#!/usr/bin/env python3
"""One-ordinal attended A90 auto-handoff benchmark runner.

The runner consumes an installed-resident D1 manifest.  It proves the H6
resident healthy and unarmed, durably binds one arm intent, arms once, proves
the exact enable state, durably binds one reboot intent, reboots once, observes
Debian PID1/display/SSH, automatic native return, the retained latch, final
resident health, and one complete benchmark boot segment.  An uncertain arm or
reboot is never resent.  ``--reconcile`` is read-only; ``--resume-after-return``
can complete only a durably observed return's cleanup/final-health tail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_boot_benchmark_v1 as benchmark  # noqa: E402
import a90_phase3_d1_observer_v1 as phase3_observer  # noqa: E402
import a90_transition_d1_session_v1 as resident  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402


SCHEMA = "a90-auto-handoff-benchmark-runner-v2"
JOURNAL_SCHEMA = "a90-auto-handoff-benchmark-journal-v2"
RESULT_SCHEMA = "a90-auto-handoff-benchmark-result-v2"
RECONCILE_SCHEMA = "a90-auto-handoff-benchmark-reconciliation-v2"
EXPECTED_VERSION = "0.11.174"
EXPECTED_BUILD = "phase3-minimal-h6-observer-complete-baseline-auto-benchmark"
ARM_TOKEN = "AUTO-HANDOFF-BENCHMARK-V1-ARM"
STATUS_RE = re.compile(
    r"^A90AUTO_STATUS binding=(?P<binding>[01]) "
    r"enable=(?P<enable>-?[0-9]+) latch=(?P<latch>-?[0-9]+) "
    r"build=(?P<build>[a-z0-9._-]+)\r?$",
    re.MULTILINE,
)
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
EXECUTION_SOURCES = {
    "runner": Path(__file__).resolve(),
    "benchmark_parser": SCRIPT_DIR / "a90_boot_benchmark_v1.py",
    "resident_manifest_loader": SCRIPT_DIR / "a90_transition_d1_session_v1.py",
    "resident_f1_loader": SCRIPT_DIR / "a90_v3403_f1_orchestrator.py",
}
JOURNAL_NAMES = (
    "0000-open.json",
    "0001-arm-intent.json",
    "0002-arm-result.json",
    "0003-reboot-intent.json",
    "0004-observation.json",
    "0005-cleanup-intent.json",
    "0006-cleanup-result.json",
    "0007-final-health.json",
    "0008-result.json",
)
JOURNAL_ACTIONS = (
    "open-native-healthy-unarmed",
    "arm-intent",
    "arm-result",
    "reboot-intent",
    "observation",
    "cleanup-intent",
    "cleanup-result",
    "final-health",
    "closed",
)
COMMON_RECORD_KEYS = {"schema", "action", "timestamp_utc"}
PAYLOAD_KEYS = (
    {
        "manifest_sha256", "execution_closure", "candidate_sha256",
        "rollback_sha256", "rootfs_sha256", "opening_preflight",
        "auto_status", "auto_status_record", "first_boot_log",
        "first_boot_log_sha256", "first_boot_unarmed",
    },
    {
        "manifest_sha256", "execution_closure_sha256",
        "arm_dispatch_count_max", "reboot_dispatch_count", "candidate_replay",
    },
    {
        "intent_sha256", "arm_dispatch_count", "arm_record",
        "post_arm_status_record", "post_arm_status",
    },
    {
        "intent_sha256", "armed_preflight", "pre_reboot_epoch",
        "reboot_dispatch_count_max", "candidate_replay",
    },
    {
        "intent_sha256", "arm_dispatch_count", "reboot_dispatch_count",
        "candidate_replay", "observation",
    },
    {
        "intent_sha256", "manifest_sha256", "cleanup_dispatch_count_max",
        "arm_dispatch_count", "reboot_dispatch_count", "candidate_replay",
        "returned_status", "returned_status_record",
    },
    {
        "intent_sha256", "cleanup_dispatch_count", "cleanup_record",
        "absence_preflight", "inferred_from_absence", "candidate_replay",
    },
    {"intent_sha256", "result_sha256", "result"},
    {"result_sha256", "result"},
)


class ContractError(RuntimeError):
    """Raised before widening, replaying, or misclassifying a D1 effect."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def execution_closure() -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    digest = hashlib.sha256()
    for role, requested in sorted(EXECUTION_SOURCES.items()):
        path = requested.resolve()
        info = path.stat()
        if requested.is_symlink() or not stat.S_ISREG(info.st_mode):
            raise ContractError(f"execution source is not one regular file: {role}")
        try:
            relative = path.relative_to(REPO_ROOT).as_posix()
        except ValueError as exc:
            raise ContractError("execution source escapes repository") from exc
        file_sha256 = sha256_file(path)
        files[role] = {
            "path": relative,
            "size": info.st_size,
            "sha256": file_sha256,
        }
        digest.update(role.encode("utf-8"))
        digest.update(b"\0")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(info.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_sha256.encode("ascii"))
        digest.update(b"\0")
    return {"sha256": digest.hexdigest(), "files": files}


def validate_recorded_execution_closure(
    value: Any,
    expected_sha256: str,
) -> dict[str, Any]:
    """Validate a durable historical closure without rebinding current files."""

    if HEX64_RE.fullmatch(expected_sha256 or "") is None:
        raise ContractError("historical execution closure SHA256 is not exact")
    if not isinstance(value, dict) or set(value) != {"sha256", "files"}:
        raise ContractError("historical execution closure is not exact")
    files = value.get("files")
    if not isinstance(files, dict) or set(files) != set(EXECUTION_SOURCES):
        raise ContractError("historical execution closure roles changed")
    digest = hashlib.sha256()
    for role, requested in sorted(EXECUTION_SOURCES.items()):
        record = files.get(role)
        relative = requested.resolve().relative_to(REPO_ROOT).as_posix()
        if (
            not isinstance(record, dict)
            or set(record) != {"path", "size", "sha256"}
            or record.get("path") != relative
            or type(record.get("size")) is not int
            or record.get("size") < 1
            or HEX64_RE.fullmatch(str(record.get("sha256") or "")) is None
        ):
            raise ContractError(f"historical execution closure role changed: {role}")
        digest.update(role.encode("utf-8"))
        digest.update(b"\0")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["size"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(record["sha256"].encode("ascii"))
        digest.update(b"\0")
    if value.get("sha256") != expected_sha256 or digest.hexdigest() != expected_sha256:
        raise ContractError("historical execution closure digest changed")
    return value


def require_execution_closure(expected_sha256: str) -> dict[str, Any]:
    if HEX64_RE.fullmatch(expected_sha256 or "") is None:
        raise ContractError("expected execution closure SHA256 is not exact")
    value = execution_closure()
    if value["sha256"] != expected_sha256:
        raise ContractError(
            "execution closure changed: "
            f"got {value['sha256']} expected {expected_sha256}"
        )
    return value


def write_record(path: Path, action: str, payload: dict[str, Any]) -> None:
    if COMMON_RECORD_KEYS.intersection(payload):
        raise ContractError("journal payload attempts to replace common keys")
    resident.write_private_json_exclusive(
        path,
        {
            "schema": JOURNAL_SCHEMA,
            "action": action,
            "timestamp_utc": resident.utc_now(),
            **payload,
        },
    )


def exact_transaction_dir(spec: resident.SessionSpec, requested: Path) -> Path:
    path = requested.resolve()
    if path != spec.transaction_dir.resolve():
        raise ContractError("transaction directory differs from D1 manifest binding")
    try:
        path.relative_to(resident.PRIVATE_RUN_BASE)
    except ValueError as exc:
        raise ContractError("transaction directory escapes private A90 run root") from exc
    return path


def validate_preflight_evidence(
    spec: resident.SessionSpec,
    value: Any,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "resident_health",
        "source_preflight",
        "rollback_sha256",
        "recovery_profile",
    }:
        raise ContractError("resident preflight evidence keyset is not exact")
    if (
        value.get("rollback_sha256") != spec.rollback.sha256
        or value.get("recovery_profile") != spec.recovery_profile
    ):
        raise ContractError("resident preflight artifact binding changed")
    resident._validate_resident_native_health(  # noqa: SLF001
        value.get("resident_health"),
        expected_version=spec.candidate_version,
        expected_build=spec.candidate_build,
        expected_bridge_realpath=spec.bridge_realpath,
    )
    resident.require_exact_source_preflight_receipt(
        _f1_spec(spec),
        value.get("source_preflight"),
    )
    return value


def _read_record(path: Path) -> dict[str, Any]:
    info = path.stat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ContractError("durable journal member is not one regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("durable journal member is malformed") from exc
    if not isinstance(value, dict):
        raise ContractError("durable journal member is not an object")
    return value


def load_journal_prefix(
    spec: resident.SessionSpec,
    path: Path,
    expected_closure_sha256: str,
    *,
    journal_closure_sha256: str | None = None,
) -> list[dict[str, Any]]:
    closure = require_execution_closure(expected_closure_sha256)
    present = [name for name in JOURNAL_NAMES if (path / name).is_file()]
    if present != list(JOURNAL_NAMES[: len(present)]):
        raise ContractError("durable journal is not one contiguous prefix")
    unexpected = sorted(
        item.name
        for item in path.iterdir()
        if re.fullmatch(r"[0-9]{4}-.*\.json", item.name) is not None
        and item.name not in present
    )
    if unexpected:
        raise ContractError("durable journal has unexpected JSON members")
    records: list[dict[str, Any]] = []
    for index, name in enumerate(present):
        value = _read_record(path / name)
        if (
            set(value) != COMMON_RECORD_KEYS | PAYLOAD_KEYS[index]
            or value.get("schema") != JOURNAL_SCHEMA
            or value.get("action") != JOURNAL_ACTIONS[index]
            or not base.is_canonical_utc_timestamp(value.get("timestamp_utc"))
        ):
            raise ContractError(f"journal record {index} shape/action is not exact")
        records.append(value)
    if not records:
        return records

    opened = records[0]
    if journal_closure_sha256 is None:
        opened_closure = closure
        intent_closure_sha256 = expected_closure_sha256
    else:
        opened_closure = validate_recorded_execution_closure(
            opened.get("execution_closure"),
            journal_closure_sha256,
        )
        intent_closure_sha256 = journal_closure_sha256
    if (
        opened.get("manifest_sha256") != spec.manifest_sha256
        or opened.get("execution_closure") != opened_closure
        or opened.get("candidate_sha256") != spec.candidate.sha256
        or opened.get("rollback_sha256") != spec.rollback.sha256
        or opened.get("rootfs_sha256") != spec.rootfs.sha256
        or opened.get("first_boot_unarmed") is not True
    ):
        raise ContractError("journal opening binding changed")
    validate_preflight_evidence(spec, opened.get("opening_preflight"))
    status_record = base.require_exact_f1_command_receipt(
        opened.get("auto_status_record"),
        ["auto-handoff-status"],
        "journal opening status",
    )
    if opened.get("auto_status") != parse_auto_status(status_record):
        raise ContractError("journal opening status record changed")
    if opened["auto_status"].get("enable") != 0 or opened["auto_status"].get("latch") != 0:
        raise ContractError("journal opening state is not unarmed")
    first_log = base.require_exact_f1_command_receipt(
        opened.get("first_boot_log"),
        ["logcat"],
        "journal first-boot log",
    )
    require_first_boot_unarmed(first_log)
    if opened.get("first_boot_log_sha256") != hashlib.sha256(
        str(first_log.get("text") or "").encode("utf-8")
    ).hexdigest():
        raise ContractError("journal first-boot log hash changed")

    if len(records) >= 2:
        intent = records[1]
        if (
            intent.get("manifest_sha256") != spec.manifest_sha256
            or intent.get("execution_closure_sha256") != intent_closure_sha256
            or intent.get("arm_dispatch_count_max") != 1
            or intent.get("reboot_dispatch_count") != 0
            or intent.get("candidate_replay") is not False
        ):
            raise ContractError("arm intent binding changed")
        intent_sha256 = sha256_file(path / JOURNAL_NAMES[1])
    else:
        return records

    if len(records) >= 3:
        armed = records[2]
        post_status_value = armed.get("post_arm_status_record")
        if isinstance(post_status_value, dict) and "command" in post_status_value:
            post_status_record = base.require_exact_f1_command_receipt(
                post_status_value,
                ["auto-handoff-status"],
                "journal post-arm status",
            )
            post_status: dict[str, Any] | None = parse_auto_status(post_status_record)
        elif _is_unproved_receipt(post_status_value):
            post_status = None
        else:
            raise ContractError("journal post-arm status receipt is not exact")
        if (
            armed.get("intent_sha256") != intent_sha256
            or armed.get("arm_dispatch_count") != 1
            or armed.get("post_arm_status") != post_status
        ):
            raise ContractError("arm result binding changed")
        arm_record = armed.get("arm_record")
        if isinstance(arm_record, dict) and "command" in arm_record:
            _, arm_outcome = require_exact_arm_dispatch_receipt(
                arm_record,
                intent_sha256,
            )
        elif _is_unproved_receipt(arm_record):
            arm_outcome = "unproved"
        else:
            raise ContractError("journal arm dispatch record is not exact")
        state = None if post_status is None else (
            post_status.get("enable"),
            post_status.get("latch"),
        )
        if (
            (arm_outcome == "armed" and state != (1, 0))
            or (arm_outcome == "refused-unarmed" and state != (0, 0))
            or (arm_outcome == "unproved" and state not in (None, (0, 0), (1, 0)))
        ):
            raise ContractError("journal arm receipt and post-arm state disagree")
    if len(records) >= 4:
        reboot = records[3]
        if (
            records[2].get("post_arm_status") is None
            or records[2]["post_arm_status"].get("enable") != 1
            or records[2]["post_arm_status"].get("latch") != 0
            or (
            reboot.get("intent_sha256") != intent_sha256
            or reboot.get("reboot_dispatch_count_max") != 1
            or reboot.get("candidate_replay") is not False
            or not isinstance(reboot.get("pre_reboot_epoch"), dict)
            )
        ):
            raise ContractError("reboot intent binding changed")
        validate_preflight_evidence(spec, reboot.get("armed_preflight"))
    if len(records) >= 5:
        observed = records[4]
        observation = observed.get("observation")
        if (
            observed.get("intent_sha256") != intent_sha256
            or observed.get("arm_dispatch_count") != 1
            or observed.get("reboot_dispatch_count") != 1
            or observed.get("candidate_replay") is not False
            or not isinstance(observation, dict)
            or not isinstance(observation.get("reboot_record"), dict)
            or observation["reboot_record"].get("command") != ["reboot"]
            or observation["reboot_record"].get("dispatch_count") != 1
        ):
            raise ContractError("observation journal binding changed")
    if len(records) >= 6:
        cleanup_intent = records[5]
        returned_status_record = base.require_exact_f1_command_receipt(
            cleanup_intent.get("returned_status_record"),
            ["auto-handoff-status"],
            "journal pre-cleanup returned status",
        )
        returned_status = parse_auto_status(returned_status_record)
        if (
            cleanup_intent.get("intent_sha256") != intent_sha256
            or cleanup_intent.get("manifest_sha256") != spec.manifest_sha256
            or cleanup_intent.get("cleanup_dispatch_count_max") != 1
            or cleanup_intent.get("arm_dispatch_count") != 1
            or cleanup_intent.get("reboot_dispatch_count") != 1
            or cleanup_intent.get("candidate_replay") is not False
            or cleanup_intent.get("returned_status") != returned_status
            or returned_status.get("enable") != 1
            or returned_status.get("latch") != 1
        ):
            raise ContractError("cleanup intent binding changed")
    if len(records) >= 7:
        cleanup = records[6]
        if (
            cleanup.get("intent_sha256") != intent_sha256
            or cleanup.get("candidate_replay") is not False
        ):
            raise ContractError("cleanup result binding changed")
        if cleanup.get("inferred_from_absence") is False:
            if cleanup.get("cleanup_dispatch_count") != 1 or cleanup.get("absence_preflight") is not None:
                raise ContractError("cleanup dispatch result is not exact")
            resident.require_exact_cleanup_receipt(spec, cleanup.get("cleanup_record"))
        elif cleanup.get("inferred_from_absence") is True:
            if cleanup.get("cleanup_dispatch_count") is not None or cleanup.get("cleanup_record") is not None:
                raise ContractError("cleanup absence reconciliation is not exact")
            validate_preflight_evidence(spec, cleanup.get("absence_preflight"))
        else:
            raise ContractError("cleanup result disposition is not exact")
    if len(records) >= 8:
        final = records[7]
        result = validate_result(spec, final.get("result"))
        if (
            final.get("intent_sha256") != intent_sha256
            or final.get("result_sha256") != base.json_sha256(result)
        ):
            raise ContractError("final-health result binding changed")
    if len(records) >= 9:
        closed = records[8]
        result = validate_result(spec, closed.get("result"))
        if (
            closed.get("result_sha256") != base.json_sha256(result)
            or result != records[7].get("result")
        ):
            raise ContractError("closed result binding changed")
    return records


def parse_auto_status(record: dict[str, Any]) -> dict[str, Any]:
    text = str(record.get("text") or "")
    matches = list(STATUS_RE.finditer(text))
    if len(matches) != 1:
        raise ContractError("auto-handoff status response is not unique")
    match = matches[0]
    result = {
        "binding": int(match.group("binding"), 10),
        "enable": int(match.group("enable"), 10),
        "latch": int(match.group("latch"), 10),
        "build": match.group("build"),
    }
    if result["binding"] != 1 or result["build"] != EXPECTED_BUILD:
        raise ContractError("auto-handoff status binding/build is not exact H3")
    return result


def require_auto_status(
    args: argparse.Namespace,
    *,
    enable: int,
    latch: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    record, status = read_auto_status(args)
    if status["enable"] != enable or status["latch"] != latch:
        raise ContractError(
            "auto-handoff state differs: "
            f"got enable={status['enable']} latch={status['latch']} "
            f"expected enable={enable} latch={latch}"
        )
    return record, status


def read_auto_status(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any]]:
    record = base.require_exact_f1_command_receipt(
        base.run_f1_cmd(args, ["auto-handoff-status"]),
        ["auto-handoff-status"],
        "auto-handoff status receipt",
    )
    status = parse_auto_status(record)
    return record, status


def require_exact_arm_dispatch_receipt(
    value: Any,
    intent_sha256: str,
) -> tuple[dict[str, Any], str]:
    command = ["auto-handoff-arm", ARM_TOKEN, intent_sha256]
    if not isinstance(value, dict):
        raise ContractError("auto-handoff arm receipt is not an object")
    if value.get("rc") == 0:
        record = base.require_exact_f1_command_receipt(
            value,
            command,
            "auto-handoff arm receipt",
        )
        marker = f"A90AUTO_ARM armed=1 intent_sha256={intent_sha256}"
        if str(record.get("text") or "").count(marker) != 1:
            raise ContractError("auto-handoff arm success marker is not exact")
        return record, "armed"

    record = value
    begin = record.get("begin")
    end = record.get("end")
    rc = record.get("rc")
    if (
        set(record) != {"command", "rc", "status", "trust", "begin", "end", "text"}
        or record.get("command") != command
        or type(rc) is not int
        or rc >= 0
        or record.get("status") != "error"
        or record.get("trust") != "A90P1_V1_STRUCTURAL_ONLY"
        or type(record.get("text")) is not str
        or not isinstance(begin, dict)
        or set(begin) != {"argc", "cmd", "flags", "seq"}
        or begin.get("cmd") != command[0]
        or begin.get("argc") != str(len(command))
        or re.fullmatch(r"0x[0-9a-f]+", str(begin.get("flags") or "")) is None
        or not str(begin.get("seq") or "").isdigit()
        or not isinstance(end, dict)
        or set(end) != {"cmd", "duration_ms", "errno", "flags", "rc", "seq", "status"}
        or end.get("cmd") != command[0]
        or end.get("seq") != begin.get("seq")
        or end.get("flags") != begin.get("flags")
        or end.get("rc") != str(rc)
        or end.get("errno") != str(-rc)
        or end.get("status") != "error"
        or not str(end.get("duration_ms") or "").isdigit()
    ):
        raise ContractError("auto-handoff arm refusal receipt is not exact")
    marker = f"A90AUTO_ARM armed=0 rc={rc}"
    if str(record.get("text") or "").count(marker) != 1:
        raise ContractError("auto-handoff arm refusal marker is not exact")
    return record, "refused-unarmed"


def _is_unproved_receipt(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"error", "response_proof"}
        and isinstance(value.get("error"), dict)
        and value.get("response_proof") is False
    )


def require_first_boot_unarmed(log_record: dict[str, Any]) -> None:
    base.require_exact_f1_command_receipt(
        log_record,
        ["logcat"],
        "first H2 resident log receipt",
    )
    text = str(log_record.get("text") or "")
    state_lines: list[str] = []
    for line in text.replace("\r", "\n").splitlines():
        marker = line.find("A90AUTO state=")
        if marker >= 0:
            state_lines.append(line[marker:].strip())
    if not state_lines or any(
        line != "A90AUTO state=unarmed-stay-native" for line in state_lines
    ):
        raise ContractError("H2 resident log is not exclusively unarmed")


def _effect_args() -> argparse.Namespace:
    return resident._effect_args()  # noqa: SLF001 - exact reviewed D1 adapter


def _f1_spec(spec: resident.SessionSpec) -> base.F1Spec:
    return resident._f1_spec(spec)  # noqa: SLF001 - exact reviewed D1 adapter


def send_reboot_once(args: argparse.Namespace) -> dict[str, Any]:
    line = base.a90ctl.encode_cmdv1_line(["reboot"])
    record: dict[str, Any] = {
        "command": ["reboot"],
        "dispatch_count": 1,
        "accepted_transport_drop": True,
    }
    try:
        text = base.a90ctl.bridge_exchange(
            args.bridge_host,
            args.bridge_port,
            line,
            8.0,
            markers=(b"reboot: syncing and restarting", b"A90P1 END "),
            input_mode=base.F1_SERIAL_INPUT_MODE,
            input_char_delay_sec=base.F1_SERIAL_INPUT_CHAR_DELAY_SEC,
            require_prompt_after_end=False,
            post_marker_drain_sec=0.0,
        )
        record["text"] = text
        if "A90P1 END " in text and "reboot: syncing and restarting" not in text:
            raise ContractError("reboot command returned before reboot dispatch")
    except ContractError:
        raise
    except Exception as exc:  # transport loss is expected after one dispatch
        record["transport_error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
    return record


def _native_release_log(text: str) -> str:
    lines: list[str] = []
    for line in text.replace("\r", "\n").splitlines():
        index = line.find("A90D3DISPLAY ")
        if index >= 0:
            lines.append(line[index:])
    return "\n".join(lines) + ("\n" if lines else "")


def _bound_bridge_candidate_exists(
    payload: dict[str, Any],
    bridge_device: str,
) -> bool:
    candidates = payload.get("serial_candidates")
    if not isinstance(candidates, list):
        raise ContractError("exact bridge preflight omitted serial candidates")
    matches = [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict)
        and candidate.get("path") == bridge_device
    ]
    if (
        len(matches) != 1
        or type(matches[0].get("exists")) is not bool
    ):
        raise ContractError("exact bridge preflight has no unique bound candidate")
    return matches[0]["exists"]


def wait_for_bound_bridge_after_reboot(
    f1_spec: base.F1Spec,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Require the bound by-id endpoint to disappear and then return exactly."""

    device = Path(f1_spec.stage.bridge_device)
    deadline = time.monotonic() + base.HOST_NCM_REBIND_TIMEOUT_SEC
    last_error: Exception | None = None
    observed_absence = False
    while True:
        present = device.exists()
        if not observed_absence:
            if not present:
                observed_absence = True
            else:
                if time.monotonic() >= deadline:
                    raise ContractError(
                        "bound bridge did not disconnect before the observation deadline"
                    )
                time.sleep(base.HOST_NCM_REBIND_POLL_SEC)
                continue
        if not present:
            if time.monotonic() >= deadline:
                raise ContractError(
                    "bound bridge did not re-enumerate before the observation deadline"
                ) from last_error
            time.sleep(base.HOST_NCM_REBIND_POLL_SEC)
            continue
        try:
            bridge = base.staging.require_exact_bridge(f1_spec.stage, args)
        except base.staging.ContractError as exc:
            last_error = exc
            if device.exists():
                raise ContractError(
                    "bound bridge is present but exact post-reboot continuity failed"
                ) from last_error
        else:
            if (
                _bound_bridge_candidate_exists(
                    bridge,
                    f1_spec.stage.bridge_device,
                )
                and device.exists()
            ):
                return bridge
            last_error = ContractError(
                "exact bridge preflight observed the bound endpoint absent"
            )
        if time.monotonic() >= deadline:
            raise ContractError(
                "bound bridge did not re-enumerate before the observation deadline"
            ) from last_error
        time.sleep(base.HOST_NCM_REBIND_POLL_SEC)


def observe_auto_cycle(
    spec: resident.SessionSpec,
    args: argparse.Namespace,
    transaction_dir: Path,
    guard: Any,
) -> dict[str, Any]:
    f1_spec = _f1_spec(spec)
    result: dict[str, Any] = {"proof": False}
    try:
        result["bridge_reenumeration"] = wait_for_bound_bridge_after_reboot(
            f1_spec,
            args,
        )
        result["host_ncm_rebind"] = base.rebind_host_ncm_after_reenumeration(
            f1_spec,
            args,
        )
        result["ssh"] = base.observe_ssh(f1_spec, args)
        result["debian_return_epoch"] = base.capture_bridge_serial_epoch(
            f1_spec,
            args,
        )
        result["phase3_service"] = phase3_observer.observe_phase3_service(
            f1_spec,
            args,
        )
        result["candidate_return"] = base.wait_for_candidate_return_attended_once(
            f1_spec,
            args,
            result["debian_return_epoch"],
            return_guard=guard,
        )
    except Exception as exc:  # effect is never replayed; final D0 decides health
        result["observer_error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
    finally:
        try:
            result["guard_release"] = base.release_candidate_return_modemmanager_guard(
                guard,
                transaction_dir,
            )
        except Exception as exc:  # preserve primary observation
            result["guard_release"] = {
                "released": False,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
    if "candidate_return" in result:
        try:
            result["retained_pmsg"] = base.collect_and_clear_retained_pmsg(
                f1_spec,
                args,
                transaction_dir,
            )
        except Exception as exc:  # final health is independently established
            result["retained_pmsg_error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
    return result


def parse_appended_benchmark(
    opening_log_record: dict[str, Any],
    final_log_record: dict[str, Any],
) -> dict[str, Any]:
    """Select only markers appended after the hash-bound pre-arm log."""

    opening = base.require_exact_f1_command_receipt(
        opening_log_record,
        ["logcat"],
        "benchmark opening log",
    )
    final = base.require_exact_f1_command_receipt(
        final_log_record,
        ["logcat"],
        "benchmark final log",
    )
    before = list(benchmark.marker_lines([str(opening.get("text") or "")]))
    after = list(benchmark.marker_lines([str(final.get("text") or "")]))
    if (
        not before
        or len(after) <= len(before)
        or after[: len(before)] != before
    ):
        raise ContractError("benchmark log is not an exact appended marker suffix")
    appended = after[len(before) :]
    canonical = "".join(f"{benchmark.MARKER}{line}\n" for line in appended)
    parsed = benchmark.parse_run([canonical], require_complete=True)
    parsed["selection"] = {
        "contract": "opening-marker-prefix-appended-suffix-v1",
        "opening_marker_count": len(before),
        "appended_marker_count": len(appended),
        "opening_markers_sha256": hashlib.sha256(
            "".join(f"{line}\n" for line in before).encode("utf-8")
        ).hexdigest(),
        "appended_markers_sha256": hashlib.sha256(
            "".join(f"{line}\n" for line in appended).encode("utf-8")
        ).hexdigest(),
    }
    return parsed


def finalize_cycle(
    spec: resident.SessionSpec,
    args: argparse.Namespace,
    observation: dict[str, Any],
    *,
    opening_log_record: dict[str, Any],
    visible_confirmed: str,
    cleanup_evidence: dict[str, Any],
) -> dict[str, Any]:
    f1_spec = _f1_spec(spec)
    status_record, status = require_auto_status(args, enable=1, latch=1)
    final_preflight, final_evidence = resident.resident_d0_preflight(spec)
    final_preflight.validate()
    log_record = base.run_f1_cmd(args, ["logcat"])
    log_text = str(log_record.get("text") or "")
    parsed_benchmark = parse_appended_benchmark(opening_log_record, log_record)
    ssh = observation.get("ssh")
    service = observation.get("phase3_service")
    facts: dict[str, Any] = {}
    if isinstance(ssh, dict) and isinstance(service, dict):
        classified = base.display.classify_phase2_display_facts(
            handoff_log=_native_release_log(log_text),
            native_release_marker=str(ssh.get("native_release_marker_text") or ""),
            pid1_comm_init=ssh.get("pid1_comm_init"),
            proc1_exe_init=ssh.get("proc1_exe_init"),
            dropbear_started=service.get("proof") is True,
            display_status=str(ssh.get("display_status")),
        )
        facts = base.display.facts_to_dict(classified)
    mechanical = bool(facts) and all(
        facts[name]["state"] == "PROVEN"
        for name in (
            "native_release",
            "debian_pid1",
            "dropbear",
            "display_acquisition",
        )
    )
    returned = isinstance(observation.get("candidate_return"), dict)
    guard_released = observation.get("guard_release", {}).get("released") is True
    if returned and mechanical and guard_released:
        terminal = (
            "PASS_AUTO_HANDOFF_BENCHMARK_VISIBLE"
            if visible_confirmed == "yes"
            else "REFUTED_AUTO_HANDOFF_DISPLAY_VISIBILITY"
            if visible_confirmed == "no"
            else "PASS_AUTO_HANDOFF_BENCHMARK_NO_PROOF_VISIBILITY"
        )
    else:
        terminal = "NO_PROOF_OBSERVER_RESIDENT_HEALTHY"
    return {
        "schema": RESULT_SCHEMA,
        "terminal": terminal,
        "resident_healthy": True,
        "candidate_replay": False,
        "arm_dispatch_count": 1,
        "reboot_dispatch_count": 1,
        "auto_handoff_status": status,
        "auto_handoff_status_record": status_record,
        "final_preflight": final_evidence,
        "work_cleanup": cleanup_evidence,
        "observation": observation,
        "display_facts": facts,
        "visible_confirmed": visible_confirmed,
        "benchmark": parsed_benchmark,
        "telemetry_scope": (
            "temperature-clock-power-memory-load and absolute mmc counters; "
            "mmc counters are observer-inclusive, not isolated workload writes"
        ),
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
    }


def validate_result(
    spec: resident.SessionSpec,
    value: Any,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("benchmark result is not an object")
    expected_keys = {
        "schema", "terminal", "resident_healthy", "candidate_replay",
        "arm_dispatch_count", "reboot_dispatch_count", "auto_handoff_status",
        "auto_handoff_status_record", "final_preflight", "work_cleanup",
        "observation", "display_facts", "visible_confirmed", "benchmark",
        "telemetry_scope", "payload_transfer", "partition_write", "flash",
    }
    allowed_terminal = {
        "PASS_AUTO_HANDOFF_BENCHMARK_VISIBLE",
        "REFUTED_AUTO_HANDOFF_DISPLAY_VISIBILITY",
        "PASS_AUTO_HANDOFF_BENCHMARK_NO_PROOF_VISIBILITY",
        "NO_PROOF_OBSERVER_RESIDENT_HEALTHY",
    }
    if (
        set(value) != expected_keys
        or value.get("schema") != RESULT_SCHEMA
        or value.get("terminal") not in allowed_terminal
        or value.get("resident_healthy") is not True
        or value.get("candidate_replay") is not False
        or value.get("arm_dispatch_count") != 1
        or value.get("reboot_dispatch_count") != 1
        or value.get("visible_confirmed") not in {"yes", "no", "unavailable"}
        or value.get("telemetry_scope")
        != (
            "temperature-clock-power-memory-load and absolute mmc counters; "
            "mmc counters are observer-inclusive, not isolated workload writes"
        )
        or value.get("payload_transfer") is not False
        or value.get("partition_write") is not False
        or value.get("flash") is not False
        or not isinstance(value.get("observation"), dict)
        or not isinstance(value.get("display_facts"), dict)
    ):
        raise ContractError("benchmark result terminal contract changed")
    status_record = base.require_exact_f1_command_receipt(
        value.get("auto_handoff_status_record"),
        ["auto-handoff-status"],
        "result auto-handoff status",
    )
    status = parse_auto_status(status_record)
    if (
        value.get("auto_handoff_status") != status
        or status.get("enable") != 1
        or status.get("latch") != 1
    ):
        raise ContractError("benchmark result does not prove returned H2 latch")
    validate_preflight_evidence(spec, value.get("final_preflight"))
    cleanup = value.get("work_cleanup")
    if not isinstance(cleanup, dict) or set(cleanup) != {
        "dispatch_count", "inferred_from_absence", "receipt", "absence_preflight"
    }:
        raise ContractError("benchmark result cleanup evidence changed")
    if cleanup.get("inferred_from_absence") is False:
        if cleanup.get("dispatch_count") != 1 or cleanup.get("absence_preflight") is not None:
            raise ContractError("benchmark result cleanup dispatch changed")
        resident.require_exact_cleanup_receipt(spec, cleanup.get("receipt"))
    elif cleanup.get("inferred_from_absence") is True:
        if cleanup.get("dispatch_count") is not None or cleanup.get("receipt") is not None:
            raise ContractError("benchmark result cleanup inference changed")
        validate_preflight_evidence(spec, cleanup.get("absence_preflight"))
    else:
        raise ContractError("benchmark result cleanup disposition changed")
    parsed = value.get("benchmark")
    if (
        not isinstance(parsed, dict)
        or parsed.get("schema") != benchmark.RESULT_SCHEMA
        or parsed.get("status") != "complete"
        or parsed.get("missing_complete_stages") != []
        or [record.get("stage") for record in parsed.get("records", [])]
        not in (
            list(benchmark.COMPLETE_STAGES),
            list(benchmark.OPTIONAL_EARLY_STAGES + benchmark.COMPLETE_STAGES),
        )
        or parsed.get("boot_segments_total") is None
        or type(parsed.get("selected_segment_index")) is not int
    ):
        raise ContractError("benchmark result is not one complete ordered segment")
    selection = parsed.get("selection")
    if (
        not isinstance(selection, dict)
        or set(selection)
        != {
            "contract",
            "opening_marker_count",
            "appended_marker_count",
            "opening_markers_sha256",
            "appended_markers_sha256",
        }
        or selection.get("contract")
        != "opening-marker-prefix-appended-suffix-v1"
        or type(selection.get("opening_marker_count")) is not int
        or selection.get("opening_marker_count") <= 0
        or type(selection.get("appended_marker_count")) is not int
        or selection.get("appended_marker_count") <= 0
        or HEX64_RE.fullmatch(str(selection.get("opening_markers_sha256") or ""))
        is None
        or HEX64_RE.fullmatch(str(selection.get("appended_markers_sha256") or ""))
        is None
    ):
        raise ContractError("benchmark appended-marker selection changed")
    return value


def dispatch_arm_once_and_publish(
    args: argparse.Namespace,
    *,
    journal_path: Path,
    intent_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Dispatch once, publish every outcome, and continue only from exact armed state."""

    command = ["auto-handoff-arm", ARM_TOKEN, intent_sha256]
    try:
        arm_record: dict[str, Any] = base.run_f1_cmd(
            args,
            command,
            allow_error=True,
        )
    except Exception as exc:  # durable unknown; never replay
        arm_record = {
            "error": {"type": type(exc).__name__, "message": str(exc)},
            "response_proof": False,
        }
    try:
        post_arm_record, post_arm_status = read_auto_status(args)
    except Exception as exc:  # preserve the arm receipt before stopping observation
        post_arm_record = {
            "error": {"type": type(exc).__name__, "message": str(exc)},
            "response_proof": False,
        }
        post_arm_status = None
    write_record(
        journal_path,
        "arm-result",
        {
            "intent_sha256": intent_sha256,
            "arm_dispatch_count": 1,
            "arm_record": arm_record,
            "post_arm_status_record": post_arm_record,
            "post_arm_status": post_arm_status,
        },
    )

    if "command" in arm_record:
        _, arm_outcome = require_exact_arm_dispatch_receipt(
            arm_record,
            intent_sha256,
        )
    elif _is_unproved_receipt(arm_record):
        arm_outcome = "unproved"
    else:
        raise ContractError("published arm dispatch record is not exact")

    state = None if post_arm_status is None else (
        post_arm_status.get("enable"),
        post_arm_status.get("latch"),
    )
    if arm_outcome == "refused-unarmed":
        if state == (0, 0):
            raise ContractError("auto-handoff arm was explicitly refused with no effect")
        raise ContractError("auto-handoff arm refusal contradicts post-arm state")
    if state != (1, 0):
        raise ContractError("auto-handoff arm outcome is not exact armed state")
    return arm_record, post_arm_status


def execute(
    spec: resident.SessionSpec,
    *,
    transaction_dir: Path,
    expected_closure_sha256: str,
    operator_attended: bool,
    visible_confirmed: str,
) -> dict[str, Any]:
    if operator_attended is not True:
        raise ContractError("operator attendance is required for this D1 ordinal")
    if spec.candidate_version != EXPECTED_VERSION or spec.candidate_build != EXPECTED_BUILD:
        raise ContractError("installed resident is not the exact H2 benchmark candidate")
    closure = require_execution_closure(expected_closure_sha256)
    path = exact_transaction_dir(spec, transaction_dir)
    if path.exists() or path.is_symlink():
        raise ContractError("transaction directory already exists; use --reconcile")
    path.mkdir(parents=True, mode=0o700)
    os.chmod(path, 0o700)
    args = _effect_args()
    opening_preflight, opening_evidence = resident.resident_d0_preflight(spec)
    opening_preflight.validate()
    status_record, status = require_auto_status(args, enable=0, latch=0)
    first_log = base.run_f1_cmd(args, ["logcat"])
    require_first_boot_unarmed(first_log)
    write_record(
        path / JOURNAL_NAMES[0],
        "open-native-healthy-unarmed",
        {
            "manifest_sha256": spec.manifest_sha256,
            "execution_closure": closure,
            "candidate_sha256": spec.candidate.sha256,
            "rollback_sha256": spec.rollback.sha256,
            "rootfs_sha256": spec.rootfs.sha256,
            "opening_preflight": opening_evidence,
            "auto_status": status,
            "auto_status_record": status_record,
            "first_boot_log": first_log,
            "first_boot_log_sha256": hashlib.sha256(
                str(first_log.get("text") or "").encode("utf-8")
            ).hexdigest(),
            "first_boot_unarmed": True,
        },
    )
    require_execution_closure(expected_closure_sha256)
    arm_intent_path = path / JOURNAL_NAMES[1]
    write_record(
        arm_intent_path,
        "arm-intent",
        {
            "manifest_sha256": spec.manifest_sha256,
            "execution_closure_sha256": expected_closure_sha256,
            "arm_dispatch_count_max": 1,
            "reboot_dispatch_count": 0,
            "candidate_replay": False,
        },
    )
    intent_sha256 = sha256_file(arm_intent_path)
    dispatch_arm_once_and_publish(
        args,
        journal_path=path / JOURNAL_NAMES[2],
        intent_sha256=intent_sha256,
    )
    require_execution_closure(expected_closure_sha256)
    armed_preflight, armed_evidence = resident.resident_d0_preflight(spec)
    armed_preflight.validate()
    f1_spec = _f1_spec(spec)
    guard = base.arm_candidate_return_modemmanager_guard(f1_spec, args, path)
    pre_reboot_epoch = base.capture_bridge_serial_epoch(f1_spec, args)
    write_record(
        path / JOURNAL_NAMES[3],
        "reboot-intent",
        {
            "intent_sha256": intent_sha256,
            "armed_preflight": armed_evidence,
            "pre_reboot_epoch": pre_reboot_epoch,
            "reboot_dispatch_count_max": 1,
            "candidate_replay": False,
        },
    )
    require_execution_closure(expected_closure_sha256)
    reboot_record = send_reboot_once(args)
    observation = observe_auto_cycle(spec, args, path, guard)
    observation["reboot_record"] = reboot_record
    write_record(
        path / JOURNAL_NAMES[4],
        "observation",
        {
            "intent_sha256": intent_sha256,
            "arm_dispatch_count": 1,
            "reboot_dispatch_count": 1,
            "candidate_replay": False,
            "observation": observation,
        },
    )
    returned_status_record, returned_status = require_auto_status(
        args,
        enable=1,
        latch=1,
    )
    write_record(
        path / JOURNAL_NAMES[5],
        "cleanup-intent",
        {
            "intent_sha256": intent_sha256,
            "manifest_sha256": spec.manifest_sha256,
            "cleanup_dispatch_count_max": 1,
            "arm_dispatch_count": 1,
            "reboot_dispatch_count": 1,
            "candidate_replay": False,
            "returned_status": returned_status,
            "returned_status_record": returned_status_record,
        },
    )
    cleanup_record = resident.require_exact_cleanup_receipt(
        spec,
        base.run_f1_shell(args, resident._cleanup_script(spec)),  # noqa: SLF001
    )
    cleanup_evidence = {
        "dispatch_count": 1,
        "inferred_from_absence": False,
        "receipt": cleanup_record,
        "absence_preflight": None,
    }
    write_record(
        path / JOURNAL_NAMES[6],
        "cleanup-result",
        {
            "intent_sha256": intent_sha256,
            "cleanup_dispatch_count": 1,
            "cleanup_record": cleanup_record,
            "absence_preflight": None,
            "inferred_from_absence": False,
            "candidate_replay": False,
        },
    )
    result = finalize_cycle(
        spec,
        args,
        observation,
        opening_log_record=first_log,
        visible_confirmed=visible_confirmed,
        cleanup_evidence=cleanup_evidence,
    )
    result = validate_result(spec, result)
    result_sha256 = base.json_sha256(result)
    write_record(
        path / JOURNAL_NAMES[7],
        "final-health",
        {
            "intent_sha256": intent_sha256,
            "result_sha256": result_sha256,
            "result": result,
        },
    )
    write_record(
        path / JOURNAL_NAMES[8],
        "closed",
        {"result_sha256": result_sha256, "result": result},
    )
    return result


def resume_after_return(
    spec: resident.SessionSpec,
    *,
    transaction_dir: Path,
    expected_closure_sha256: str,
    expected_journal_closure_sha256: str | None = None,
    operator_attended: bool,
    visible_confirmed: str,
) -> dict[str, Any]:
    """Finish only cleanup/final health after a durably observed return."""

    if operator_attended is not True:
        raise ContractError("operator attendance is required for D1 finalization")
    if spec.candidate_version != EXPECTED_VERSION or spec.candidate_build != EXPECTED_BUILD:
        raise ContractError("installed resident is not the exact H2 benchmark candidate")
    path = exact_transaction_dir(spec, transaction_dir)
    if not path.is_dir() or path.is_symlink():
        raise ContractError("resume transaction directory is not exact")
    records = load_journal_prefix(
        spec,
        path,
        expected_closure_sha256,
        journal_closure_sha256=expected_journal_closure_sha256,
    )
    if len(records) < 5:
        raise ContractError("resume lacks one durable automatic-cycle observation")
    if expected_journal_closure_sha256 is not None and len(records) != 7:
        raise ContractError(
            "historical-closure tail repair requires the exact post-cleanup prefix"
        )
    if len(records) == len(JOURNAL_NAMES):
        return validate_result(spec, records[-1]["result"])
    if len(records) == 8:
        # Only the host-side publication record is absent.  Never turn this
        # append-only repair into a new device observation or D1 effect.
        result = validate_result(spec, records[7]["result"])
        result_sha256 = records[7]["result_sha256"]
        write_record(
            path / JOURNAL_NAMES[8],
            "closed",
            {"result_sha256": result_sha256, "result": result},
        )
        load_journal_prefix(
            spec,
            path,
            expected_closure_sha256,
            journal_closure_sha256=expected_journal_closure_sha256,
        )
        return result

    args = _effect_args()
    observation = records[4]["observation"]
    intent_sha256 = records[4]["intent_sha256"]

    if len(records) == 5:
        returned_status_record, returned_status = require_auto_status(
            args,
            enable=1,
            latch=1,
        )
        write_record(
            path / JOURNAL_NAMES[5],
            "cleanup-intent",
            {
                "intent_sha256": intent_sha256,
                "manifest_sha256": spec.manifest_sha256,
                "cleanup_dispatch_count_max": 1,
                "arm_dispatch_count": 1,
                "reboot_dispatch_count": 1,
                "candidate_replay": False,
                "returned_status": returned_status,
                "returned_status_record": returned_status_record,
            },
        )
        cleanup_record = resident.require_exact_cleanup_receipt(
            spec,
            base.run_f1_shell(args, resident._cleanup_script(spec)),  # noqa: SLF001
        )
        write_record(
            path / JOURNAL_NAMES[6],
            "cleanup-result",
            {
                "intent_sha256": intent_sha256,
                "cleanup_dispatch_count": 1,
                "cleanup_record": cleanup_record,
                "absence_preflight": None,
                "inferred_from_absence": False,
                "candidate_replay": False,
            },
        )
        cleanup_evidence = {
            "dispatch_count": 1,
            "inferred_from_absence": False,
            "receipt": cleanup_record,
            "absence_preflight": None,
        }
    elif len(records) == 6:
        # The cleanup intent may already have been dispatched.  Never resend it;
        # exact source/work-absence plus resident health can close the outcome.
        preflight, absence_evidence = resident.resident_d0_preflight(spec)
        preflight.validate()
        write_record(
            path / JOURNAL_NAMES[6],
            "cleanup-result",
            {
                "intent_sha256": intent_sha256,
                "cleanup_dispatch_count": None,
                "cleanup_record": None,
                "absence_preflight": absence_evidence,
                "inferred_from_absence": True,
                "candidate_replay": False,
            },
        )
        cleanup_evidence = {
            "dispatch_count": None,
            "inferred_from_absence": True,
            "receipt": None,
            "absence_preflight": absence_evidence,
        }
    else:
        cleanup_record = records[6]
        cleanup_evidence = {
            "dispatch_count": cleanup_record["cleanup_dispatch_count"],
            "inferred_from_absence": cleanup_record["inferred_from_absence"],
            "receipt": cleanup_record["cleanup_record"],
            "absence_preflight": cleanup_record["absence_preflight"],
        }

    records = load_journal_prefix(
        spec,
        path,
        expected_closure_sha256,
        journal_closure_sha256=expected_journal_closure_sha256,
    )
    if len(records) == 7:
        result = finalize_cycle(
            spec,
            args,
            observation,
            opening_log_record=records[0]["first_boot_log"],
            visible_confirmed=visible_confirmed,
            cleanup_evidence=cleanup_evidence,
        )
        result = validate_result(spec, result)
        result_sha256 = base.json_sha256(result)
        write_record(
            path / JOURNAL_NAMES[7],
            "final-health",
            {
                "intent_sha256": intent_sha256,
                "result_sha256": result_sha256,
                "result": result,
            },
        )
    else:
        result = validate_result(spec, records[7]["result"])
        result_sha256 = records[7]["result_sha256"]
    records = load_journal_prefix(
        spec,
        path,
        expected_closure_sha256,
        journal_closure_sha256=expected_journal_closure_sha256,
    )
    if len(records) == 8:
        write_record(
            path / JOURNAL_NAMES[8],
            "closed",
            {"result_sha256": result_sha256, "result": result},
        )
    load_journal_prefix(
        spec,
        path,
        expected_closure_sha256,
        journal_closure_sha256=expected_journal_closure_sha256,
    )
    return result


def reconcile(
    spec: resident.SessionSpec,
    *,
    transaction_dir: Path,
    expected_closure_sha256: str,
) -> dict[str, Any]:
    """Read-only device reconciliation; never arm, reboot, hand off, or replay."""

    require_execution_closure(expected_closure_sha256)
    path = exact_transaction_dir(spec, transaction_dir)
    if not path.is_dir() or path.is_symlink():
        raise ContractError("reconciliation transaction directory is not exact")
    try:
        records = load_journal_prefix(spec, path, expected_closure_sha256)
    except Exception as exc:
        return {
            "schema": RECONCILE_SCHEMA,
            "terminal": "JOURNAL_INCONSISTENT_STOP",
            "journal_error": {"type": type(exc).__name__, "message": str(exc)},
            "arm_dispatch_count": None,
            "reboot_dispatch_count": None,
            "candidate_replay": False,
            "device_effect": None,
        }
    present = list(JOURNAL_NAMES[: len(records)])
    if not records:
        return {
            "schema": RECONCILE_SCHEMA,
            "terminal": "NO_DURABLE_EFFECT_EVIDENCE",
            "journal_records_present": [],
            "arm_dispatch_count": 0,
            "reboot_dispatch_count": 0,
            "candidate_replay": False,
            "device_effect": False,
        }
    if len(records) == len(JOURNAL_NAMES):
        return {
            "schema": RECONCILE_SCHEMA,
            "terminal": "CLOSED_EXACT_NO_REPLAY",
            "journal_records_present": present,
            "result": records[-1]["result"],
            "arm_dispatch_count": 1,
            "reboot_dispatch_count": 1,
            "candidate_replay": False,
            "device_effect": True,
        }
    args = _effect_args()
    status_record: dict[str, Any] | None = None
    status: dict[str, Any] | None = None
    status_error: dict[str, str] | None = None
    try:
        status_record = base.require_exact_f1_command_receipt(
            base.run_f1_cmd(args, ["auto-handoff-status"]),
            ["auto-handoff-status"],
            "reconciliation auto-handoff status",
        )
        status = parse_auto_status(status_record)
    except Exception as exc:  # endpoint absence is HEALTH_PENDING, never replay
        status_error = {"type": type(exc).__name__, "message": str(exc)}
    health: dict[str, Any] | None = None
    health_error: dict[str, str] | None = None
    try:
        _, health = resident.resident_d0_preflight(spec)
    except Exception as exc:  # HEALTH_PENDING, never a reason to replay
        health_error = {"type": type(exc).__name__, "message": str(exc)}
    arm_dispatch_count: int | None = 1 if len(records) >= 3 else (
        None if len(records) >= 2 else 0
    )
    reboot_dispatch_count: int | None = 1 if len(records) >= 5 else (
        None if len(records) >= 4 else 0
    )
    device_effect: bool | None = None
    if len(records) >= 8:
        terminal = "RESULT_PUBLICATION_PENDING_NO_REPLAY"
        device_effect = True
    elif (
        len(records) >= 5
        and health is not None
        and status is not None
        and status["enable"] == 1
        and status["latch"] == 1
    ):
        terminal = "RETURNED_NATIVE_FINALIZATION_PENDING_NO_REPLAY"
        device_effect = True
    elif len(records) >= 4:
        terminal = "RECOVERY_PENDING_PARKED_NO_REPLAY"
        device_effect = True
    elif len(records) == 3:
        journal_status = records[2].get("post_arm_status")
        journal_arm = records[2].get("arm_record")
        if isinstance(journal_arm, dict) and "command" in journal_arm:
            _, journal_outcome = require_exact_arm_dispatch_receipt(
                journal_arm,
                records[2]["intent_sha256"],
            )
        else:
            journal_outcome = "unproved"
        if (
            journal_outcome == "refused-unarmed"
            and isinstance(journal_status, dict)
            and journal_status.get("enable") == 0
            and journal_status.get("latch") == 0
        ):
            terminal = "ARM_REFUSED_EXACT_NO_EFFECT_NO_REPLAY"
            device_effect = False
        elif (
            isinstance(journal_status, dict)
            and journal_status.get("enable") == 1
            and journal_status.get("latch") == 0
        ):
            terminal = "ARMED_REBOOT_NOT_DURABLY_INTENDED_NO_REPLAY"
            device_effect = True
        else:
            terminal = "ARM_OUTCOME_PENDING_NO_REPLAY"
    elif len(records) == 2:
        if status is not None and status["enable"] == 0 and status["latch"] == 0:
            terminal = "ARM_RESULT_PUBLICATION_MISSING_CURRENTLY_UNARMED_NO_REPLAY"
            device_effect = False
        else:
            terminal = "ARM_RESULT_PUBLICATION_MISSING_NO_REPLAY"
    else:
        terminal = "OPENED_NO_D1_INTENT"
        device_effect = False
    return {
        "schema": RECONCILE_SCHEMA,
        "terminal": terminal,
        "journal_records_present": present,
        "auto_handoff_status": status,
        "auto_handoff_status_record": status_record,
        "auto_handoff_status_error": status_error,
        "resident_health": health,
        "resident_health_error": health_error,
        "arm_dispatch_count": arm_dispatch_count,
        "reboot_dispatch_count": reboot_dispatch_count,
        "candidate_replay": False,
        "device_effect": device_effect,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-execution-closure", action="store_true")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expect-manifest-sha256")
    parser.add_argument("--expect-execution-closure-sha256")
    parser.add_argument("--expect-journal-execution-closure-sha256")
    parser.add_argument("--transaction-dir", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--resume-after-return", action="store_true")
    modes.add_argument("--reconcile", action="store_true")
    parser.add_argument("--operator-attended", action="store_true")
    parser.add_argument(
        "--visible-confirmed",
        choices=("yes", "no", "unavailable"),
        default="unavailable",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.print_execution_closure:
        print(json.dumps(execution_closure(), indent=2, sort_keys=True))
        return 0
    required = (
        args.manifest,
        args.expect_manifest_sha256,
        args.expect_execution_closure_sha256,
        args.transaction_dir,
    )
    if any(value is None for value in required):
        raise ContractError("manifest, closure, and transaction arguments are required")
    spec = resident.load_spec(args.manifest, args.expect_manifest_sha256)
    if (
        args.expect_journal_execution_closure_sha256 is not None
        and not args.resume_after_return
    ):
        raise ContractError(
            "historical journal closure is valid only for post-return tail repair"
        )
    if args.execute:
        result = execute(
            spec,
            transaction_dir=args.transaction_dir,
            expected_closure_sha256=args.expect_execution_closure_sha256,
            operator_attended=args.operator_attended,
            visible_confirmed=args.visible_confirmed,
        )
    elif args.resume_after_return:
        result = resume_after_return(
            spec,
            transaction_dir=args.transaction_dir,
            expected_closure_sha256=args.expect_execution_closure_sha256,
            expected_journal_closure_sha256=(
                args.expect_journal_execution_closure_sha256
            ),
            operator_attended=args.operator_attended,
            visible_confirmed=args.visible_confirmed,
        )
    elif args.reconcile:
        result = reconcile(
            spec,
            transaction_dir=args.transaction_dir,
            expected_closure_sha256=args.expect_execution_closure_sha256,
        )
    else:
        result = {
            "schema": SCHEMA,
            "host_only": True,
            "manifest_sha256": spec.manifest_sha256,
            "execution_closure": require_execution_closure(
                args.expect_execution_closure_sha256
            ),
            "transaction_dir": str(spec.transaction_dir),
            "live_authority": False,
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, resident.ContractError, base.ContractError) as exc:
        print(f"a90-auto-handoff-benchmark-runner-v1: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
