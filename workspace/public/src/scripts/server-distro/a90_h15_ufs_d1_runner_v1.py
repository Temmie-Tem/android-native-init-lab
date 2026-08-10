#!/usr/bin/env python3
"""One-shot attended A90 H15 direct-UFS automatic handoff and benchmark.

The runner arms one already-installed H15 resident, reboots once, observes the
existing UFS appliance as Debian PID 1 over the same A90 USB/NCM identity, and
requires a later exact H15 native return.  It transfers no payload, flashes no
partition, sends no rootfs bytes, and never replays an uncertain arm or reboot.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_auto_handoff_benchmark_runner_v1 as legacy  # noqa: E402
import a90_h15_ufs_f1_runner_v1 as f1  # noqa: E402
import a90_ondevice_evidence_v1 as ondevice  # noqa: E402
import a90_phase3_d1_observer_v1 as phase3_observer  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402


SCHEMA = "a90-h15-ufs-d1-journal-v1"
RESULT_SCHEMA = "a90-h15-ufs-d1-result-v1"
RECONCILE_SCHEMA = "a90-h15-ufs-d1-reconciliation-v1"
APPROVAL_SCHEMA = "a90-h15-ufs-d1-approval-prepared-v1"
APPROVAL_BINDING_SCHEMA = "a90-h15-ufs-d1-approval-binding-v1"
APPROVAL_PREFIX = "A90-H15-D1-APPROVE:"
APPROVAL_TTL_SEC = 1800
ARM_TOKEN = "AUTO-HANDOFF-BENCHMARK-V1-ARM"
STATUS_RE = re.compile(
    r"^A90AUTO_STATUS binding=(?P<binding>[01]) "
    r"enable=(?P<enable>-?[0-9]+) latch=(?P<latch>-?[0-9]+) "
    r"build=(?P<build>[a-z0-9._-]+)\r?$",
    re.MULTILINE,
)
JOURNAL_NAMES = (
    "0000-open.json",
    "0001-arm-reboot-intent.json",
    "0002-dispatch-result.json",
    "0003-observation.json",
    "0004-final-health.json",
    "0005-closed.json",
)
JOURNAL_ACTIONS = (
    "open-native-healthy-unarmed",
    "arm-reboot-intent",
    "dispatch-result",
    "observation",
    "final-health",
    "closed",
)


class ContractError(RuntimeError):
    """Raised before replaying or widening the exact H15 D1 ordinal."""


def _effect_args() -> argparse.Namespace:
    return argparse.Namespace(
        bridge_host="127.0.0.1",
        bridge_port=54321,
        bridge_timeout=180.0,
        remote_timeout=180.0,
        flash_command_timeout=900.0,
        ssh_connect_timeout=8.0,
        poll_interval=3.0,
        transfer_timeout=1200.0,
    )


def _load_install_result(
    value: Any,
    expected_sha256: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    path = f1.reopen_bound(value, "install_result")
    if f1.sha256_file(path) != expected_sha256:
        raise ContractError("H15 install result SHA256 changed")
    result = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(result, dict)
        or result.get("schema") != f1.RESULT_SCHEMA
        or result.get("status") != "PASS_A90_H15_UFS_RESIDENT_INSTALLED"
        or result.get("manifest_sha256") != manifest["_manifest_sha256"]
        or result.get("device_safety_state") != "RESIDENT_HEALTHY"
        or result.get("candidate_transfer_count") != 1
        or result.get("rollback_transfer_count") != 0
        or result.get("candidate_replay") is not False
        or result.get("rootfs_payload_count") != 0
        or result.get("sd_stage_count") != 0
        or result.get("userdata_write_count") != 0
    ):
        raise ContractError("H15 resident install terminal is not exact")
    return result


def load_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], Any, dict[str, Any]]:
    manifest = f1.load_manifest(args.manifest, args.expect_manifest_sha256)
    manifest = dict(manifest)
    manifest["_manifest_sha256"] = args.expect_manifest_sha256
    result_binding = {
        "path": str(Path(args.install_result).resolve(strict=True)),
        "size": Path(args.install_result).stat().st_size,
        "sha256": args.expect_install_result_sha256,
    }
    result = _load_install_result(
        result_binding,
        args.expect_install_result_sha256,
        manifest,
    )
    closure = f1.execution_closure()
    if args.expect_execution_closure_sha256 != closure["sha256"]:
        raise ContractError("H15 capability execution closure changed")
    f1.validate_qualification(manifest["capability_qualification"], closure)
    spec = f1._spec(manifest, args.manifest, args.expect_manifest_sha256)  # noqa: SLF001
    spec.bridge_realpath = spec.stage.bridge_realpath
    return manifest, spec, result


def parse_status(record: dict[str, Any]) -> dict[str, Any]:
    exact = base.require_exact_f1_command_receipt(
        record,
        ["auto-handoff-status"],
        "H15 auto-handoff status",
    )
    lines = [
        line.strip()
        for line in str(exact.get("text") or "").replace("\r", "").splitlines()
        if line.strip().startswith("A90AUTO_STATUS")
    ]
    if len(lines) != 1:
        raise ContractError("H15 auto-handoff status is not unique")
    match = STATUS_RE.fullmatch(lines[0])
    if match is None:
        raise ContractError("H15 auto-handoff status shape changed")
    value = {
        "binding": int(match.group("binding"), 10),
        "enable": int(match.group("enable"), 10),
        "latch": int(match.group("latch"), 10),
        "build": match.group("build"),
    }
    if value["binding"] != 1 or value["build"] != f1.CANDIDATE_BUILD:
        raise ContractError("auto-handoff status is not the exact H15 binding")
    return value


def require_status(
    args: argparse.Namespace,
    *,
    enable: int,
    latch: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    record = base.run_f1_cmd(args, ["auto-handoff-status"])
    status = parse_status(record)
    if (status["enable"], status["latch"]) != (enable, latch):
        raise ContractError(
            f"H15 state is {status['enable']},{status['latch']}; "
            f"expected {enable},{latch}"
        )
    return record, status


def _exact_log_text(record: dict[str, Any], label: str) -> str:
    exact = base.require_exact_f1_command_receipt(record, ["logcat"], label)
    return str(exact.get("text") or "").replace("\r", "")


def require_cancellation_fsync_proof(
    opening_log: dict[str, Any],
    final_log: dict[str, Any],
    intent_sha256: str,
) -> dict[str, Any]:
    before = _exact_log_text(opening_log, "H15 cancellation opening log")
    after = _exact_log_text(final_log, "H15 cancellation final log")
    pattern = re.compile(
        rf"^\[[0-9]+ms\] auto-handoff: reboot returned cancellation "
        rf"intent_sha256={re.escape(intent_sha256)} reboot_errno=[1-9][0-9]* "
        rf"cancel_rc=0$",
        re.MULTILINE,
    )
    before_matches = pattern.findall(before)
    after_matches = pattern.findall(after)
    if before_matches or len(after_matches) != 1:
        raise ContractError(
            "H15 no-effect close lacks one post-intent cancellation fsync proof"
        )
    return {
        "proof": True,
        "intent_sha256": intent_sha256,
        "opening_match_count": 0,
        "final_match_count": 1,
        "final_log_record": final_log,
    }


def native_failure_cleanup_disposition(
    opening_log: dict[str, Any],
    final_log: dict[str, Any],
    *,
    native_handoff_failed: bool,
) -> dict[str, Any]:
    before = _exact_log_text(opening_log, "H15 cleanup opening log")
    after = _exact_log_text(final_log, "H15 cleanup final log")
    pattern = re.compile(
        r"^\[[0-9]+ms\] server-distro: D4 handoff failure "
        r"cleanup_clean=(?P<clean>[01]) root_mounted=(?P<mounted>[01]) "
        r"recovery_required=(?P<recovery>[01]) "
        r"userdata_unchanged=1 userdata_write=0$",
        re.MULTILINE,
    )
    before_matches = [item.groupdict() for item in pattern.finditer(before)]
    after_matches = [item.groupdict() for item in pattern.finditer(after)]
    appended = after_matches[len(before_matches) :] if after_matches[: len(before_matches)] == before_matches else []
    if native_handoff_failed:
        if len(appended) != 1:
            raise ContractError("native handoff failure cleanup evidence is not unique")
        item = appended[0]
        proof = item == {"clean": "1", "mounted": "0", "recovery": "0"}
        if not proof:
            raise ContractError(
                "native handoff failure left mount cleanup recovery-pending"
            )
        return {
            "proof": True,
            "native_handoff_failed": True,
            "cleanup_clean": True,
            "root_unmounted": True,
            "recovery_required": False,
        }
    if appended:
        raise ContractError("successful handoff contradicts a native failure cleanup marker")
    return {
        "proof": True,
        "native_handoff_failed": False,
        "cleanup_clean": None,
        "root_unmounted": None,
        "recovery_required": False,
    }


def _write_record(
    transaction_dir: Path,
    index: int,
    action: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if index >= len(JOURNAL_NAMES):
        raise ContractError("H15 D1 journal overflow")
    value = {
        "schema": SCHEMA,
        "sequence": index,
        "action": action,
        **payload,
    }
    f1.write_json_exclusive(transaction_dir / JOURNAL_NAMES[index], value)
    return value


def _read_records(transaction_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, name in enumerate(JOURNAL_NAMES):
        path = transaction_dir / name
        if not path.exists():
            if any((transaction_dir / later).exists() for later in JOURNAL_NAMES[index + 1 :]):
                raise ContractError("H15 D1 journal has a gap")
            break
        value = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or value.get("schema") != SCHEMA
            or value.get("sequence") != index
            or value.get("action") != JOURNAL_ACTIONS[index]
        ):
            raise ContractError("H15 D1 journal record changed")
        records.append(value)
    return records


def _require_transaction_dir(
    manifest: dict[str, Any],
    transaction_dir: Path,
    *,
    must_be_absent: bool,
) -> Path:
    resolved = transaction_dir.resolve(strict=not must_be_absent)
    expected_parent = (
        f1.PRIVATE_RUN_BASE / manifest["run_id"] / "h15-d1"
    ).resolve()
    if resolved.parent != expected_parent or resolved.exists() == must_be_absent:
        state = "absent" if must_be_absent else "existing"
        raise ContractError(f"H15 D1 transaction path is not exact and {state}")
    return resolved


def _approval_path(transaction_dir: Path) -> Path:
    return transaction_dir.parent / f"{transaction_dir.name}-approval-prepared.json"


def approval_binding(
    manifest: dict[str, Any],
    args: argparse.Namespace,
    transaction_dir: Path,
    *,
    created_utc: str,
    expires_utc: str,
) -> dict[str, Any]:
    target = manifest["target"]
    return {
        "schema": APPROVAL_BINDING_SCHEMA,
        "workflow": "A90_D1_ATTENDED_SESSION_V1",
        "authority_mode": "trial-retired-fresh-approval-required",
        "run_id": manifest["run_id"],
        "transaction_dir": str(transaction_dir),
        "manifest_sha256": args.expect_manifest_sha256,
        "install_result_sha256": args.expect_install_result_sha256,
        "execution_closure_sha256": args.expect_execution_closure_sha256,
        "agents_contract_sha256": f1.sha256_file(f1.REPO_ROOT / "AGENTS.md"),
        "target_profile": target["profile"],
        "bridge_device": target["bridge_device"],
        "bridge_realpath": target["bridge_realpath"],
        "recovery_binding_sha256": f1.json_sha256(
            target["recovery_adb_identity_evidence"]
        ),
        "resident_version": f1.CANDIDATE_VERSION,
        "resident_build": f1.CANDIDATE_BUILD,
        "action_allowlist": [
            ["auto-handoff-arm-reboot", ARM_TOKEN, "<intent-sha256>"]
        ],
        "action_budget": 1,
        "duration_sec": APPROVAL_TTL_SEC,
        "payload_transfer_count": 0,
        "partition_write_count": 0,
        "userdata_write_count": 0,
        "candidate_replay": False,
        "operator_attendance_required": True,
        "created_utc": created_utc,
        "expires_utc": expires_utc,
    }


def prepare_approval(args: argparse.Namespace) -> dict[str, Any]:
    manifest, _, _ = load_inputs(args)
    transaction_dir = _require_transaction_dir(
        manifest,
        args.transaction_dir,
        must_be_absent=True,
    )
    created = dt.datetime.now(dt.UTC).replace(microsecond=0)
    expires = created + dt.timedelta(seconds=APPROVAL_TTL_SEC)
    binding = approval_binding(
        manifest,
        args,
        transaction_dir,
        created_utc=created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        expires_utc=expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    binding_sha = f1.json_sha256(binding)
    value = {
        "schema": APPROVAL_SCHEMA,
        "approval_binding": binding,
        "approval_binding_sha256": binding_sha,
        "approval_token": APPROVAL_PREFIX + binding_sha,
        "device_contact": False,
        "device_write": False,
        "live_authority_from_preparation": False,
    }
    f1.write_json_exclusive(_approval_path(transaction_dir), value)
    return value


def validate_approval(
    manifest: dict[str, Any],
    args: argparse.Namespace,
    transaction_dir: Path,
) -> dict[str, Any]:
    path = _approval_path(transaction_dir)
    info = path.lstat()
    if not path.is_file() or path.is_symlink() or info.st_mode & 0o077:
        raise ContractError("H15 D1 approval is not a private regular file")
    value = json.loads(path.read_text(encoding="utf-8"))
    binding = value.get("approval_binding") if isinstance(value, dict) else None
    if not isinstance(binding, dict):
        raise ContractError("H15 D1 approval binding is absent")
    expected = approval_binding(
        manifest,
        args,
        transaction_dir,
        created_utc=str(binding.get("created_utc") or ""),
        expires_utc=str(binding.get("expires_utc") or ""),
    )
    binding_sha = f1.json_sha256(binding)
    created = f1.parse_utc(binding.get("created_utc"), "D1 approval created_utc")
    expires = f1.parse_utc(binding.get("expires_utc"), "D1 approval expires_utc")
    now = dt.datetime.now(dt.UTC)
    if (
        set(value)
        != {
            "schema",
            "approval_binding",
            "approval_binding_sha256",
            "approval_token",
            "device_contact",
            "device_write",
            "live_authority_from_preparation",
        }
        or value.get("schema") != APPROVAL_SCHEMA
        or binding != expected
        or value.get("approval_binding_sha256") != binding_sha
        or value.get("approval_token") != APPROVAL_PREFIX + binding_sha
        or args.approval != value.get("approval_token")
        or value.get("device_contact") is not False
        or value.get("device_write") is not False
        or value.get("live_authority_from_preparation") is not False
        or expires - created != dt.timedelta(seconds=APPROVAL_TTL_SEC)
        or now < created
        or now > expires
    ):
        raise ContractError("H15 D1 approval is not fresh and exact")
    return value


def _validate_records(
    records: list[dict[str, Any]],
    transaction_dir: Path,
    args: argparse.Namespace,
    manifest: dict[str, Any],
) -> str | None:
    if not records:
        return None
    opening = records[0]
    if (
        opening.get("manifest_sha256") != args.expect_manifest_sha256
        or opening.get("install_result_sha256")
        != args.expect_install_result_sha256
        or opening.get("execution_closure_sha256")
        != args.expect_execution_closure_sha256
        or opening.get("approval_consumed") is not True
        or not isinstance(opening.get("approval_binding"), dict)
        or opening.get("approval_binding_sha256")
        != f1.json_sha256(opening.get("approval_binding"))
        or not isinstance(opening.get("approval_token_sha256"), str)
        or f1.HEX64_RE.fullmatch(opening.get("approval_token_sha256")) is None
        or opening.get("candidate_replay") is not False
        or opening.get("payload_transfer_count") != 0
        or opening.get("partition_write_count") != 0
        or opening.get("userdata_write_count") != 0
    ):
        raise ContractError("H15 D1 opening binding changed")
    opening_log = opening.get("opening_log")
    if not isinstance(opening_log, dict):
        raise ContractError("H15 D1 opening log is absent")
    _exact_log_text(opening_log, "H15 D1 durable opening log")
    approval_value = opening["approval_binding"]
    expected_approval = approval_binding(
        manifest,
        args,
        transaction_dir,
        created_utc=str(approval_value.get("created_utc") or ""),
        expires_utc=str(approval_value.get("expires_utc") or ""),
    )
    if approval_value != expected_approval:
        raise ContractError("H15 D1 consumed approval binding changed")
    if len(records) == 1:
        return None
    intent = records[1]
    if (
        intent.get("arm_reboot_command_dispatch_count_max") != 1
        or intent.get("approval_binding_sha256")
        != opening.get("approval_binding_sha256")
        or intent.get("transaction_dir") != str(transaction_dir)
        or intent.get("manifest_sha256") != args.expect_manifest_sha256
        or intent.get("candidate_replay") is not False
        or not isinstance(intent.get("pre_reboot_binding"), dict)
        or not isinstance(intent.get("guard"), dict)
    ):
        raise ContractError("H15 D1 arm-reboot intent changed")
    intent_sha256 = f1.sha256_file(transaction_dir / JOURNAL_NAMES[1])
    if any(
        record.get("intent_sha256") != intent_sha256
        for record in records[2:4]
    ):
        raise ContractError("H15 D1 continuation intent binding changed")
    if len(records) >= 3 and (
        records[2].get("arm_reboot_command_dispatch_count") != 1
        or records[2].get("candidate_replay") is not False
        or not isinstance(records[2].get("dispatch_record"), dict)
    ):
        raise ContractError("H15 D1 dispatch result changed")
    if len(records) >= 4 and (
        records[3].get("arm_reboot_command_dispatch_count") != 1
        or records[3].get("candidate_replay") is not False
        or not isinstance(records[3].get("observation"), dict)
    ):
        raise ContractError("H15 D1 observation changed")
    if len(records) >= 5:
        result = records[4].get("result")
        if (
            not isinstance(result, dict)
            or result.get("schema") != RESULT_SCHEMA
            or result.get("intent_sha256") != intent_sha256
            or result.get("candidate_replay") is not False
            or records[4].get("result_sha256") != f1.json_sha256(result)
        ):
            raise ContractError("H15 D1 final health changed")
    if len(records) == 6 and (
        records[5].get("result") != records[4].get("result")
        or records[5].get("result_sha256") != records[4].get("result_sha256")
    ):
        raise ContractError("H15 D1 closed result changed")
    return intent_sha256


def _arm_reboot_once(
    args: argparse.Namespace,
    intent_sha256: str,
) -> dict[str, Any]:
    command = ["auto-handoff-arm-reboot", ARM_TOKEN, intent_sha256]
    line = base.a90ctl.encode_cmdv1_line(command)
    result: dict[str, Any] = {
        "command": command,
        "dispatch_count": 1,
        "arm_count_max": 1,
        "reboot_count_max": 1,
        "candidate_replay": False,
        "response_proof": False,
    }
    try:
        result["text"] = base.a90ctl.bridge_exchange(
            args.bridge_host,
            args.bridge_port,
            line,
            12.0,
            markers=(b"A90AUTO_ARM_REBOOT", b"A90P1 END "),
            input_mode=base.F1_SERIAL_INPUT_MODE,
            input_char_delay_sec=base.F1_SERIAL_INPUT_CHAR_DELAY_SEC,
            require_prompt_after_end=False,
            post_marker_drain_sec=0.0,
        )
        marker = (
            "A90AUTO_ARM_REBOOT armed=1 reboot_dispatch=1 "
            f"intent_sha256={intent_sha256} build={f1.CANDIDATE_BUILD}"
        )
        result["response_proof"] = str(result["text"]).count(marker) == 1
    except Exception as exc:  # one dispatch; transport loss is expected on reboot
        result["transport_error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
    return result


def _observe(
    spec: Any,
    args: argparse.Namespace,
    transaction_dir: Path,
    guard: Any,
    binding: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {"proof": False, "pre_reboot_binding": binding}
    try:
        ncm = legacy.wait_for_bound_ncm_after_reboot(binding)
        result["debian_ncm_identity"] = ncm
        result["host_ncm_rebind"] = legacy.rebind_host_ncm_for_bound_identity(
            spec,
            binding,
            ncm,
        )
        result["debian_ncm_continuity"] = {}
        legacy.validate_post_reboot_ncm_identity(binding, ncm, require_live=True)
        result["debian_ncm_continuity"]["before_ssh"] = True
        result["ssh"] = base.observe_ssh(spec, args)
        legacy.validate_post_reboot_ncm_identity(binding, ncm, require_live=True)
        result["debian_ncm_continuity"]["after_ssh"] = True
        result["phase3_service"] = phase3_observer.observe_phase3_service(spec, args)
        legacy.validate_post_reboot_ncm_identity(binding, ncm, require_live=True)
        result["debian_ncm_continuity"]["after_service"] = True
        result["candidate_return"] = legacy.wait_for_native_return_after_bound_ncm(
            spec,
            args,
            binding,
            ncm,
            guard,
        )
        result["proof"] = True
    except Exception as exc:  # no replay; final native health decides safety
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
        except Exception as exc:
            result["guard_release_error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
    return result


def _finalize(
    spec: Any,
    args: argparse.Namespace,
    observation: dict[str, Any],
    intent_sha256: str,
    opening_log: dict[str, Any],
    visible_confirmed: str,
) -> dict[str, Any]:
    status_record, status = require_status(args, enable=1, latch=1)
    native = base.verify_candidate_health(spec, args)
    log_record = base.run_f1_cmd(args, ["logcat"])
    log_text = str(log_record.get("text") or "")
    durable = ondevice.evaluate(log_text, intent_sha256)
    wifi = legacy.h12_wifi_proven(durable)
    benchmark = legacy.parse_appended_benchmark(opening_log, log_record)
    cleanup = native_failure_cleanup_disposition(
        opening_log,
        log_record,
        native_handoff_failed=benchmark.get("native_handoff_failed") is True,
    )
    host_link = legacy.host_link_proven(spec, observation)
    guard_released = observation.get("guard_release", {}).get("released") is True
    if benchmark.get("native_handoff_failed") is True:
        terminal = "REFUTED_H15_NATIVE_HANDOFF_FAILED_RESIDENT_HEALTHY"
    elif durable.get("proof") is True and wifi and host_link and guard_released:
        terminal = (
            "PASS_H15_UFS_AUTO_HANDOFF_VISIBLE"
            if visible_confirmed == "yes"
            else "REFUTED_H15_UFS_DISPLAY_VISIBILITY"
            if visible_confirmed == "no"
            else "PASS_H15_UFS_AUTO_HANDOFF_NO_PROOF_VISIBILITY"
        )
    else:
        terminal = "NO_PROOF_H15_UFS_OBSERVER_RESIDENT_HEALTHY"
    return {
        "schema": RESULT_SCHEMA,
        "terminal": terminal,
        "intent_sha256": intent_sha256,
        "resident_healthy": True,
        "candidate_replay": False,
        "arm_dispatch_count": 1,
        "reboot_dispatch_count": 1,
        "payload_transfer_count": 0,
        "partition_write_count": 0,
        "flash_count": 0,
        "sd_rootfs_stage_count": 0,
        "userdata_write_count": 0,
        "auto_handoff_status": status,
        "auto_handoff_status_record": status_record,
        "native_health": native,
        "observation": observation,
        "ondevice_evidence": durable,
        "wifi_proven": wifi,
        "host_link_proven": host_link,
        "visible_confirmed": visible_confirmed,
        "benchmark": benchmark,
        "native_failure_cleanup": cleanup,
        "durable_evidence_log_record": log_record,
    }


def _dispatch_and_observe(
    spec: Any,
    args: argparse.Namespace,
    transaction_dir: Path,
    guard: Any,
    binding: dict[str, Any],
    intent_sha256: str,
    opening_log: dict[str, Any],
    visible_confirmed: str,
) -> dict[str, Any]:
    legacy.require_pre_reboot_observer_binding_current(spec, args, binding)
    require_status(args, enable=0, latch=0)
    if not guard.healthy(recheck=True):
        raise ContractError("candidate-return guard was lost before arm-reboot")
    dispatch_record = _arm_reboot_once(args, intent_sha256)
    _write_record(
        transaction_dir,
        2,
        "dispatch-result",
        {
            "intent_sha256": intent_sha256,
            "arm_reboot_command_dispatch_count": 1,
            "candidate_replay": False,
            "dispatch_record": dispatch_record,
        },
    )
    observation = _observe(spec, args, transaction_dir, guard, binding)
    observation["arm_reboot_dispatch_record"] = dispatch_record
    _write_record(
        transaction_dir,
        3,
        "observation",
        {
            "intent_sha256": intent_sha256,
            "arm_reboot_command_dispatch_count": 1,
            "candidate_replay": False,
            "observation": observation,
        },
    )
    result = _finalize(
        spec,
        args,
        observation,
        intent_sha256,
        opening_log,
        visible_confirmed,
    )
    result_sha = f1.json_sha256(result)
    _write_record(
        transaction_dir,
        4,
        "final-health",
        {"result_sha256": result_sha, "result": result},
    )
    _write_record(
        transaction_dir,
        5,
        "closed",
        {"result_sha256": result_sha, "result": result},
    )
    return result


def execute(args: argparse.Namespace) -> dict[str, Any]:
    if args.operator_attended is not True:
        raise ContractError("H15 automatic UFS handoff is attended-only")
    manifest, spec, install_result = load_inputs(args)
    transaction_dir = _require_transaction_dir(
        manifest,
        args.transaction_dir,
        must_be_absent=True,
    )
    effect_args = _effect_args()
    base.staging.require_exact_bridge(spec.stage, effect_args)
    native = base.verify_candidate_health(spec, effect_args)
    status_record, status = require_status(effect_args, enable=0, latch=0)
    opening_log = base.run_f1_cmd(effect_args, ["logcat"])
    base.require_auto_handoff_log_exclusively_unarmed(
        str(opening_log.get("text") or ""),
        "H15 first resident boot log",
    )
    approval = validate_approval(manifest, args, transaction_dir)
    transaction_dir.mkdir(parents=True, mode=0o700)
    os.chmod(transaction_dir, 0o700)
    _write_record(
        transaction_dir,
        0,
        "open-native-healthy-unarmed",
        {
            "manifest_sha256": args.expect_manifest_sha256,
            "install_result_sha256": args.expect_install_result_sha256,
            "execution_closure_sha256": args.expect_execution_closure_sha256,
            "approval_binding": approval["approval_binding"],
            "approval_binding_sha256": approval["approval_binding_sha256"],
            "approval_token_sha256": hashlib.sha256(
                str(approval["approval_token"]).encode("utf-8")
            ).hexdigest(),
            "approval_consumed": True,
            "native_health": native,
            "auto_status": status,
            "auto_status_record": status_record,
            "opening_log": opening_log,
            "candidate_replay": False,
            "payload_transfer_count": 0,
            "partition_write_count": 0,
            "userdata_write_count": 0,
            "install_result": install_result,
        },
    )
    guard = base.arm_candidate_return_modemmanager_guard(
        spec,
        effect_args,
        transaction_dir,
    )
    try:
        binding = legacy.capture_pre_reboot_observer_binding(spec, effect_args)
        legacy.require_pre_reboot_observer_binding_current(
            spec, effect_args, binding
        )
        require_status(effect_args, enable=0, latch=0)
        guard_evidence = base.modemmanager_guard_arm_evidence(
            transaction_dir,
            "candidate-return",
            guard,
        )
        _write_record(
            transaction_dir,
            1,
            "arm-reboot-intent",
            {
                "arm_reboot_command_dispatch_count_max": 1,
                "approval_binding_sha256": approval["approval_binding_sha256"],
                "transaction_dir": str(transaction_dir),
                "manifest_sha256": args.expect_manifest_sha256,
                "candidate_replay": False,
                "pre_reboot_binding": binding,
                "guard": guard_evidence,
            },
        )
        intent_sha256 = f1.sha256_file(transaction_dir / JOURNAL_NAMES[1])
        return _dispatch_and_observe(
            spec,
            effect_args,
            transaction_dir,
            guard,
            binding,
            intent_sha256,
            opening_log,
            args.visible_confirmed,
        )
    except Exception:
        if guard.process is not None and guard.process.poll() is None:
            try:
                base.release_candidate_return_modemmanager_guard(
                    guard, transaction_dir
                )
            except Exception:
                pass
        raise


def finalize_return(args: argparse.Namespace) -> dict[str, Any]:
    """Close only the read-only native-return health after one observed reboot."""
    if args.operator_attended is not True:
        raise ContractError("H15 return finalization is attended-only")
    manifest, spec, _ = load_inputs(args)
    transaction_dir = _require_transaction_dir(
        manifest,
        args.transaction_dir,
        must_be_absent=False,
    )
    records = _read_records(transaction_dir)
    if len(records) not in (2, 3, 4):
        raise ContractError("return finalization requires an exact pending prefix")
    intent_sha256 = _validate_records(records, transaction_dir, args, manifest)
    assert intent_sha256 is not None
    effect_args = _effect_args()
    # A 1,1 latch is the first read-only fact that proves the native command
    # reached the one-shot boot path.  Never synthesize a dispatch record from
    # an intent-only host prefix before this proof.
    require_status(effect_args, enable=1, latch=1)
    if len(records) == 2:
        _write_record(
            transaction_dir,
            2,
            "dispatch-result",
            {
                "intent_sha256": intent_sha256,
                "arm_reboot_command_dispatch_count": 1,
                "candidate_replay": False,
                "dispatch_record": {
                    "response_proof": False,
                    "reconciled_after_process_exit": True,
                },
            },
        )
        records = _read_records(transaction_dir)
    if len(records) == 3:
        observation = {
            "proof": False,
            "pre_reboot_binding": records[1].get("pre_reboot_binding"),
            "observer_error": {
                "type": "HostObserverExit",
                "message": "native return reconciled without replay",
            },
        }
        release_path = (
            transaction_dir / "candidate-return-modemmanager-guard-release.json"
        )
        if release_path.exists():
            observation["guard_release"] = json.loads(
                release_path.read_text(encoding="utf-8")
            )
        _write_record(
            transaction_dir,
            3,
            "observation",
            {
                "intent_sha256": intent_sha256,
                "arm_reboot_command_dispatch_count": 1,
                "candidate_replay": False,
                "observation": observation,
            },
        )
        records = _read_records(transaction_dir)
    observation = records[3].get("observation")
    opening_log = records[0].get("opening_log")
    if not isinstance(observation, dict) or not isinstance(opening_log, dict):
        raise ContractError("return finalization evidence shape changed")
    result = _finalize(
        spec,
        effect_args,
        observation,
        intent_sha256,
        opening_log,
        args.visible_confirmed,
    )
    result_sha = f1.json_sha256(result)
    _write_record(
        transaction_dir,
        4,
        "final-health",
        {"result_sha256": result_sha, "result": result},
    )
    _write_record(
        transaction_dir,
        5,
        "closed",
        {"result_sha256": result_sha, "result": result},
    )
    return result


def finalize_no_effect(args: argparse.Namespace) -> dict[str, Any]:
    if args.operator_attended is not True:
        raise ContractError("H15 no-effect finalization is attended-only")
    manifest, spec, _ = load_inputs(args)
    transaction_dir = _require_transaction_dir(
        manifest,
        args.transaction_dir,
        must_be_absent=False,
    )
    records = _read_records(transaction_dir)
    if len(records) not in (2, 3, 4):
        raise ContractError("no-effect finalization requires an exact pending prefix")
    intent_sha256 = _validate_records(records, transaction_dir, args, manifest)
    assert intent_sha256 is not None
    effect_args = _effect_args()
    status_record, status = require_status(effect_args, enable=0, latch=0)
    native = base.verify_candidate_health(spec, effect_args)
    legacy.require_pre_reboot_observer_binding_current(
        spec,
        effect_args,
        records[1]["pre_reboot_binding"],
    )
    if len(records) == 4 and records[3]["observation"].get("proof") is True:
        raise ContractError("no-effect finalization contradicts a proved observation")
    opening_log = records[0].get("opening_log")
    if not isinstance(opening_log, dict):
        raise ContractError("H15 D1 opening log is absent")
    final_log = base.run_f1_cmd(effect_args, ["logcat"])
    cancellation = require_cancellation_fsync_proof(
        opening_log,
        final_log,
        intent_sha256,
    )
    dispatch_count = 1
    if len(records) == 2:
        _write_record(
            transaction_dir,
            2,
            "dispatch-result",
            {
                "intent_sha256": intent_sha256,
                "arm_reboot_command_dispatch_count": 1,
                "candidate_replay": False,
                "dispatch_record": {
                    "response_proof": False,
                    "persistent_effect_inferred": False,
                    "dispatch_inferred_from_cancellation_fsync": True,
                },
            },
        )
        records = _read_records(transaction_dir)
    if len(records) == 3:
        _write_record(
            transaction_dir,
            3,
            "observation",
            {
                "intent_sha256": intent_sha256,
                "arm_reboot_command_dispatch_count": 1,
                "candidate_replay": False,
                "observation": {
                    "proof": False,
                    "persistent_effect_inferred": False,
                    "cancellation_fsync": cancellation,
                },
            },
        )
    result = {
        "schema": RESULT_SCHEMA,
        "terminal": "ABORTED_H15_ARM_REBOOT_NO_PERSISTENT_EFFECT",
        "intent_sha256": intent_sha256,
        "resident_healthy": True,
        "candidate_replay": False,
        "arm_reboot_command_dispatch_count": dispatch_count,
        "arm_reboot_command_dispatch_count_max": 1,
        "arm_persistent_effect_count": 0,
        "reboot_dispatch_count": 0,
        "payload_transfer_count": 0,
        "partition_write_count": 0,
        "flash_count": 0,
        "sd_rootfs_stage_count": 0,
        "userdata_write_count": 0,
        "auto_handoff_status": status,
        "auto_handoff_status_record": status_record,
        "native_health": native,
        "cancellation_fsync": cancellation,
    }
    result_sha = f1.json_sha256(result)
    _write_record(
        transaction_dir,
        4,
        "final-health",
        {"result_sha256": result_sha, "result": result},
    )
    _write_record(
        transaction_dir,
        5,
        "closed",
        {"result_sha256": result_sha, "result": result},
    )
    return result


def reconcile(args: argparse.Namespace) -> dict[str, Any]:
    manifest, spec, _ = load_inputs(args)
    transaction_dir = _require_transaction_dir(
        manifest,
        args.transaction_dir,
        must_be_absent=False,
    )
    records = _read_records(transaction_dir)
    _validate_records(records, transaction_dir, args, manifest)
    status = None
    status_error = None
    health = None
    health_error = None
    cleanup_recovery_required = False
    cleanup_evidence = None
    cleanup_error = None
    cancellation_evidence = None
    cancellation_error = None
    effect_args = _effect_args()
    try:
        record = base.run_f1_cmd(effect_args, ["auto-handoff-status"])
        status = parse_status(record)
    except Exception as exc:
        status_error = {"type": type(exc).__name__, "message": str(exc)}
    try:
        health = base.verify_candidate_health(spec, effect_args)
    except Exception as exc:
        health_error = {"type": type(exc).__name__, "message": str(exc)}
    if (
        len(records) >= 2
        and isinstance(status, dict)
        and (status.get("enable"), status.get("latch")) == (1, 1)
        and isinstance(records[0].get("opening_log"), dict)
    ):
        try:
            current_log = base.run_f1_cmd(effect_args, ["logcat"])
            benchmark = legacy.parse_appended_benchmark(
                records[0]["opening_log"],
                current_log,
            )
            cleanup_evidence = native_failure_cleanup_disposition(
                records[0]["opening_log"],
                current_log,
                native_handoff_failed=(
                    benchmark.get("native_handoff_failed") is True
                ),
            )
        except Exception as exc:
            cleanup_error = {"type": type(exc).__name__, "message": str(exc)}
            cleanup_recovery_required = True
    if (
        len(records) >= 2
        and isinstance(status, dict)
        and (status.get("enable"), status.get("latch")) == (0, 0)
        and isinstance(records[0].get("opening_log"), dict)
    ):
        try:
            intent_sha256 = f1.sha256_file(transaction_dir / JOURNAL_NAMES[1])
            current_log = base.run_f1_cmd(effect_args, ["logcat"])
            cancellation_evidence = require_cancellation_fsync_proof(
                records[0]["opening_log"],
                current_log,
                intent_sha256,
            )
        except Exception as exc:
            cancellation_error = {"type": type(exc).__name__, "message": str(exc)}
    if len(records) == 6:
        terminal = "CLOSED_EXACT_NO_REPLAY"
    elif cleanup_recovery_required:
        terminal = "RECOVERY_PENDING_MOUNT_CLEANUP_NO_REPLAY"
    elif (
        len(records) >= 2
        and isinstance(status, dict)
        and (status.get("enable"), status.get("latch")) == (1, 1)
        and health is not None
        and isinstance(cleanup_evidence, dict)
        and cleanup_evidence.get("proof") is True
    ):
        terminal = "RETURN_READY_FOR_FINALIZE_NO_REPLAY"
    elif (
        len(records) >= 2
        and isinstance(status, dict)
        and (status.get("enable"), status.get("latch")) == (0, 0)
        and health is not None
        and isinstance(cancellation_evidence, dict)
        and cancellation_evidence.get("proof") is True
    ):
        terminal = "NO_PERSISTENT_EFFECT_READY_FOR_FINALIZE"
    elif (
        len(records) >= 2
        and isinstance(status, dict)
        and (status.get("enable"), status.get("latch")) == (0, 0)
        and health is not None
    ):
        terminal = "ARM_REBOOT_DISPATCH_UNKNOWN_NO_REPLAY"
    elif (
        len(records) >= 2
        and isinstance(status, dict)
        and (status.get("enable"), status.get("latch")) == (1, 0)
    ):
        terminal = "RECOVERY_PENDING_ARMED_NO_REPLAY"
    elif len(records) >= 2:
        terminal = "ARM_REBOOT_OR_RETURN_PENDING_NO_REPLAY"
    else:
        terminal = "NO_DURABLE_D1_EFFECT"
    return {
        "schema": RECONCILE_SCHEMA,
        "terminal": terminal,
        "records_present": len(records),
        "auto_status": status,
        "auto_status_error": status_error,
        "resident_health": health,
        "resident_health_error": health_error,
        "native_failure_cleanup": cleanup_evidence,
        "native_failure_cleanup_error": cleanup_error,
        "cancellation_fsync": cancellation_evidence,
        "cancellation_fsync_error": cancellation_error,
        "candidate_replay": False,
        "arm_replay": False,
        "reboot_replay": False,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--manifest", type=Path, required=True)
    result.add_argument("--expect-manifest-sha256", required=True)
    result.add_argument("--install-result", type=Path, required=True)
    result.add_argument("--expect-install-result-sha256", required=True)
    result.add_argument("--expect-execution-closure-sha256", required=True)
    result.add_argument("--transaction-dir", type=Path, required=True)
    modes = result.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare-approval", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--finalize-return", action="store_true")
    modes.add_argument("--finalize-no-effect", action="store_true")
    modes.add_argument("--reconcile", action="store_true")
    result.add_argument("--operator-attended", action="store_true")
    result.add_argument("--approval")
    result.add_argument(
        "--visible-confirmed",
        choices=("yes", "no", "unavailable"),
        default="unavailable",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.prepare_approval:
            if args.approval is not None or args.operator_attended:
                raise ContractError(
                    "D1 approval preparation accepts no live authority inputs"
                )
            value = prepare_approval(args)
        elif args.execute:
            if args.approval is None:
                raise ContractError("H15 D1 execute requires fresh exact approval")
            value = execute(args)
        elif args.finalize_return:
            if args.approval is not None:
                raise ContractError("D1 continuation accepts no new approval")
            value = finalize_return(args)
        elif args.finalize_no_effect:
            if args.approval is not None:
                raise ContractError("D1 continuation accepts no new approval")
            value = finalize_no_effect(args)
        else:
            if args.approval is not None:
                raise ContractError("D1 reconciliation accepts no new approval")
            value = reconcile(args)
    except (ContractError, f1.ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"H15_UFS_D1_ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
