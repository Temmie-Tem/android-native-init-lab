#!/usr/bin/env python3
"""One-shot attended A90 H24 persistent Debian server handoff.

The runner arms one already-installed H24 resident, reboots once, observes the
existing read-only UFS appliance as Debian PID 1 over the same A90 USB/NCM
identity, and intentionally leaves Debian live.  It transfers no payload,
flashes no partition, sends no rootfs bytes, and never replays an uncertain arm
or reboot.  A later attended physical return is finalized only from the same
durable journal and never sends the return action itself.
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
import a90_h24_ufs_f1_runner_v1 as f1  # noqa: E402
import a90_h24_persistent_server_observer_v1 as persistent_observer  # noqa: E402
import a90_observation_pipeline as observation  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402


SCHEMA = "a90-h24-ufs-d1-journal-v1"
RESULT_SCHEMA = "a90-h24-ufs-d1-result-v1"
RECONCILE_SCHEMA = "a90-h24-ufs-d1-reconciliation-v1"
APPROVAL_SCHEMA = "a90-h24-ufs-d1-approval-prepared-v1"
APPROVAL_BINDING_SCHEMA = "a90-h24-ufs-d1-approval-binding-v1"
APPROVAL_PREFIX = "A90-H24-D1-APPROVE:"
APPROVAL_TTL_SEC = 1800
ARM_TOKEN = "AUTO-HANDOFF-BENCHMARK-V1-ARM"
STATUS_RE = re.compile(
    r"^A90AUTO_STATUS binding=(?P<binding>[01]) "
    r"enable=(?P<enable>-?[0-9]+) latch=(?P<latch>-?[0-9]+) "
    r"build=(?P<build>[a-z0-9._-]+)\r?$",
    re.MULTILINE,
)
UNMOUNTED_RE = re.compile(
    r"^A90H24_POST_PHYSICAL_RETURN devt=(?P<major>[0-9]+):"
    r"(?P<minor>[0-9]+) ufs_mount_count=(?P<count>[0-9]+) "
    r"userdata_write=0$"
)
INCIDENT_WINDOW_STAGES = frozenset(
    {
        "root-content",
        "writable-set-mount",
        "writable-set-verify",
        "observer-auth-overlay",
        "firstboot-overlay",
        "persistent-hud",
        "evidence-bind",
        "wifi-handoff-bind",
    }
)
NATIVE_FALLBACK_CURRENT_STATUSES = frozenset(
    {
        "REFUTED_H24_POST_ROOT_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_CURRENT",
        "REFUTED_H24_OTHER_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_CURRENT",
        "NO_PROOF_H24_FAILURE_ATTRIBUTION_NATIVE_FALLBACK_CURRENT",
    }
)
NATIVE_FALLBACK_FINAL_STATUSES = frozenset(
    {
        "REFUTED_H24_POST_ROOT_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_HEALTHY",
        "REFUTED_H24_OTHER_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_HEALTHY",
        "NO_PROOF_H24_FAILURE_ATTRIBUTION_NATIVE_FALLBACK_HEALTHY",
    }
)
JOURNAL_NAMES = (
    "0000-open.json",
    "0001-arm-reboot-intent.json",
    "0002-dispatch-result.json",
    "0003-persistent-observation.json",
    "0004-current-state.json",
    "0005-final-health.json",
    "0006-closed.json",
)
JOURNAL_ACTIONS = (
    "open-native-healthy-unarmed",
    "arm-reboot-intent",
    "dispatch-result",
    "persistent-observation",
    "current-state",
    "final-health",
    "closed",
)


class ContractError(RuntimeError):
    """Raised before replaying or widening the exact H24 D1 ordinal."""


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
        raise ContractError("H24 install result SHA256 changed")
    result = json.loads(path.read_text(encoding="utf-8"))
    journal = f1._journal_dir(manifest)  # noqa: SLF001 - same execution closure
    expected_result_path = journal.parent / "result.json"
    records = f1.read_journal(
        journal,
        manifest,
        manifest["_manifest_sha256"],
    )
    if (
        not isinstance(result, dict)
        or result.get("schema") != f1.RESULT_SCHEMA
        or result.get("status") != "PASS_A90_H24_UFS_RESIDENT_INSTALLED"
        or result.get("manifest_sha256") != manifest["_manifest_sha256"]
        or result.get("device_safety_state") != "RESIDENT_HEALTHY"
        or result.get("candidate_attempt_count") != 1
        or result.get("candidate_transfer_count") != 1
        or result.get("rollback_transfer_count") != 0
        or result.get("candidate_replay") is not False
        or result.get("rootfs_payload_count") != 0
        or result.get("sd_stage_count") != 0
        or result.get("userdata_write_count") != 0
        or path != expected_result_path.resolve(strict=True)
        or not records
        or records[-1].get("action") != "closed"
        or records[-1].get("result") != result
    ):
        raise ContractError("H24 resident install terminal is not exact")
    f1.validate_stored_candidate_health(result.get("final_health"), manifest)
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
        raise ContractError("H24 capability execution closure changed")
    f1.validate_qualification(manifest["execution_qualification"], closure)
    spec = f1._spec(manifest, args.manifest, args.expect_manifest_sha256)  # noqa: SLF001
    spec.bridge_realpath = spec.stage.bridge_realpath
    return manifest, spec, result


def parse_status(record: dict[str, Any]) -> dict[str, Any]:
    exact = base.require_exact_f1_command_receipt(
        record, ["auto-handoff-status"], "H24 auto-handoff status"
    )
    lines = [
        line.strip()
        for line in str(exact.get("text") or "").replace("\r", "").splitlines()
        if line.strip().startswith("A90AUTO_STATUS")
    ]
    if len(lines) != 1:
        raise ContractError("H24 auto-handoff status is not unique")
    match = STATUS_RE.fullmatch(lines[0])
    if match is None:
        raise ContractError("H24 auto-handoff status shape changed")
    enable = int(match.group("enable"), 10)
    latch = int(match.group("latch"), 10)
    if enable not in (0, 1) or latch not in (0, 1):
        raise ContractError("H24 auto-handoff status values are not binary")
    return f1.validate_h24_auto_status_record(
        record, enable=enable, latch=latch
    )


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
            f"H24 state is {status['enable']},{status['latch']}; "
            f"expected {enable},{latch}"
        )
    return record, status


def _exact_log_text(record: dict[str, Any], label: str) -> str:
    exact = base.require_exact_f1_command_receipt(record, ["logcat"], label)
    try:
        transcript = observation.parse_a90p1_transcript(exact["text"])
    except observation.ObservationContractError as exc:
        raise ContractError(f"{label} framing changed") from exc
    if len(transcript.frames) != 1 or transcript.transitions:
        raise ContractError(f"{label} does not contain one exact frame")
    frame = transcript.frames[0]
    if frame.begin != exact["begin"] or frame.end != exact["end"] or not frame.body:
        raise ContractError(f"{label} receipt and frame disagree")
    done = f"[done] logcat ({frame.end['duration_ms']}ms)"
    if frame.body[-1].text != done:
        raise ContractError(f"{label} completion line changed")
    payload = list(frame.body[:-1])
    if payload and payload[-1].text == "" and payload[-1].ending.value == "CRLF":
        payload.pop()
    return "".join(line.text + "\n" for line in payload)


def require_cancellation_fsync_proof(
    opening_log: dict[str, Any],
    final_log: dict[str, Any],
    intent_sha256: str,
) -> dict[str, Any]:
    before = _exact_log_text(opening_log, "H24 cancellation opening log")
    after = _exact_log_text(final_log, "H24 cancellation final log")
    pattern = re.compile(
        rf"^\[[0-9]+ms\] auto-handoff: reboot returned cancellation "
        rf"intent_sha256={re.escape(intent_sha256)} reboot_errno=[1-9][0-9]* "
        rf"cancel_rc=0$"
    )
    if len(after) <= len(before) or not after.startswith(before):
        raise ContractError("H24 cancellation log history is not an exact prefix")
    appended = after[len(before) :]
    before_candidates = [
        line
        for line in before.splitlines()
        if "auto-handoff: reboot returned cancellation " in line
    ]
    appended_candidates = [
        line
        for line in appended.splitlines()
        if "auto-handoff: reboot returned cancellation " in line
    ]
    if (
        before_candidates
        or len(appended_candidates) != 1
        or pattern.fullmatch(appended_candidates[0]) is None
    ):
        raise ContractError(
            "H24 no-effect close lacks one post-intent cancellation fsync proof"
        )
    return {
        "proof": True,
        "intent_sha256": intent_sha256,
        "opening_match_count": 0,
        "final_match_count": 1,
        "final_log_record": final_log,
    }


def native_fallback_attribution(
    opening_log: dict[str, Any],
    final_log: dict[str, Any],
) -> dict[str, Any]:
    before = _exact_log_text(opening_log, "H24 attribution opening log")
    after = _exact_log_text(final_log, "H24 attribution final log")
    diagnostic_pattern = re.compile(
        r"^\[[0-9]+ms\] server-distro: D4 handoff stop "
        r"stage=(?P<stage>[a-z0-9-]+) rc=(?P<rc>-[0-9]+) "
        r"errno=(?P<errno>[1-9][0-9]*) root_mounted=(?P<root>[01]) "
        r"writable_mounted=(?P<writable>[0-9]+) "
        r"evidence_bound=(?P<evidence>[01]) "
        r"wifi_handoff_bound=(?P<wifi>[01])$"
    )
    cleanup_pattern = re.compile(
        r"^\[[0-9]+ms\] server-distro: D4 handoff failure "
        r"cleanup_clean=(?P<clean>[01]) root_mounted=(?P<mounted>[01]) "
        r"recovery_required=(?P<recovery>[01]) "
        r"userdata_unchanged=1 userdata_write=0$"
    )

    if len(after) <= len(before) or not after.startswith(before):
        raise ContractError("H24 native log history is not an exact prefix")
    appended = after[len(before) :]
    appended_lines = appended.splitlines()
    diagnostic_candidates = [
        (index, line)
        for index, line in enumerate(appended_lines)
        if "server-distro: D4 handoff stop " in line
    ]
    cleanup_candidates = [
        (index, line)
        for index, line in enumerate(appended_lines)
        if "server-distro: D4 handoff failure " in line
    ]
    if len(cleanup_candidates) != 1:
        raise ContractError("H24 native fallback cleanup evidence is not unique")
    cleanup_index, cleanup_text = cleanup_candidates[0]
    cleanup = cleanup_pattern.fullmatch(cleanup_text)
    if cleanup is None:
        raise ContractError("H24 native fallback cleanup shape changed")
    if cleanup.groupdict() != {"clean": "1", "mounted": "0", "recovery": "0"}:
        raise ContractError("H24 native fallback cleanup is recovery-pending")
    if len(diagnostic_candidates) > 1:
        raise ContractError("H24 native fallback diagnostic is not unique")
    if not diagnostic_candidates:
        return {
            "proof": False,
            "status": "NO_PROOF_H24_FAILURE_ATTRIBUTION",
            "reason": "diagnostic record absent",
            "cleanup_proof": True,
            "cleanup_clean": True,
            "root_unmounted": True,
            "recovery_required": False,
            "record_persistence": "observed-a90-log-only",
            "power_loss_durable_journal": False,
            "final_log_record": final_log,
        }
    diagnostic_index, diagnostic_text = diagnostic_candidates[0]
    diagnostic = diagnostic_pattern.fullmatch(diagnostic_text)
    if diagnostic is None:
        raise ContractError("H24 native fallback diagnostic shape changed")
    facts = diagnostic.groupdict()
    rc = int(facts["rc"], 10)
    error = int(facts["errno"], 10)
    if rc >= 0 or error != -rc or diagnostic_index >= cleanup_index:
        raise ContractError("H24 native fallback diagnostic facts changed")
    stage = facts["stage"]
    root_mounted = facts["root"] == "1"
    window_match = stage in INCIDENT_WINDOW_STAGES and root_mounted
    return {
        "proof": True,
        "status": "PROVED_H24_FAILURE_ATTRIBUTION",
        "stage": stage,
        "rc": rc,
        "errno": error,
        "root_mounted_at_failure": root_mounted,
        "writable_mounted": int(facts["writable"], 10),
        "evidence_bound": facts["evidence"] == "1",
        "wifi_handoff_bound": facts["wifi"] == "1",
        "incident_window_match": window_match,
        "cleanup_proof": True,
        "cleanup_clean": True,
        "root_unmounted": True,
        "recovery_required": False,
        "record_persistence": "observed-a90-log-only",
        "power_loss_durable_journal": False,
        "final_log_record": final_log,
    }


def _expected_h24_state(intent_sha256: str, state: str) -> bytes:
    if f1.HEX64_RE.fullmatch(intent_sha256) is None:
        raise ContractError("H24 state intent SHA256 is invalid")
    if state not in {
        "armed-after-native-health",
        "automatic-handoff-dispatched-no-replay",
    }:
        raise ContractError("H24 state name is invalid")
    lines = (
        "schema=a90-auto-handoff-userdata-ro-v2",
        f"build={f1.CANDIDATE_BUILD}",
        "root_kind=userdata-ext4-ro-noload",
        f"userdata_devname={f1.UFS_IDENTITY['devname']}",
        f"userdata_devt_policy={f1.UFS_IDENTITY['devt_policy']}",
        f"userdata_sectors={f1.UFS_IDENTITY['sectors']}",
        f"userdata_label={f1.UFS_IDENTITY['label']}",
        f"userdata_marker={f1.UFS_IDENTITY['marker']}",
        f"userdata_uuid={f1.UFS_IDENTITY['uuid']}",
        "userdata_content_manifest_sha256="
        "e1950058627446d6bbd487d6a17b80f5766be4956b54cb56659b541dab09f8f6",
        f"intent_sha256={intent_sha256}",
        f"state={state}",
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _same_intent_script() -> str:
    return "\n".join(
        (
            "set -eu",
            f"E={f1.ENABLE_PATH}",
            f"L={f1.LATCH_PATH}",
            "R=/mnt/sdext/a90/runtime/evidence/a90-ondevice-evidence-run",
            "EINT=$(/bin/busybox sed -n 's/^intent_sha256=//p' \"$E\")",
            "LINT=$(/bin/busybox sed -n 's/^intent_sha256=//p' \"$L\")",
            "RINT=$(/bin/busybox cat \"$R\")",
            "case \"$EINT$LINT$RINT\" in *[!0-9a-f]*) exit 42 ;; esac",
            '[ "${#EINT}" = 64 ]',
            '[ "$EINT" = "$LINT" ]',
            '[ "$EINT" = "$RINT" ]',
            "ES=$(/bin/busybox sha256sum \"$E\" | /bin/busybox awk '{print $1}')",
            "LS=$(/bin/busybox sha256sum \"$L\" | /bin/busybox awk '{print $1}')",
            "RS=$(/bin/busybox sha256sum \"$R\" | /bin/busybox awk '{print $1}')",
            'echo "A90H24_INTENT_BINDING intent=$EINT enable_sha256=$ES '
            'latch_sha256=$LS evidence_sha256=$RS"',
        )
    )


def require_same_intent_state(
    effect_args: argparse.Namespace,
    intent_sha256: str,
) -> dict[str, Any]:
    script = _same_intent_script()
    command = ["run", "/bin/busybox", "sh", "-c", script]
    record = base.run_f1_cmd(effect_args, command)
    exact = base.require_exact_f1_command_receipt(
        record,
        command,
        "H24 exact enable/latch/evidence intent binding",
    )
    lines = [
        line.strip()
        for line in str(exact.get("text") or "").replace("\r", "").splitlines()
        if line.strip().startswith("A90H24_INTENT_BINDING ")
    ]
    pattern = re.compile(
        r"^A90H24_INTENT_BINDING intent=(?P<intent>[0-9a-f]{64}) "
        r"enable_sha256=(?P<enable>[0-9a-f]{64}) "
        r"latch_sha256=(?P<latch>[0-9a-f]{64}) "
        r"evidence_sha256=(?P<evidence>[0-9a-f]{64})$"
    )
    match = pattern.fullmatch(lines[0]) if len(lines) == 1 else None
    expected = {
        "intent": intent_sha256,
        "enable": hashlib.sha256(
            _expected_h24_state(intent_sha256, "armed-after-native-health")
        ).hexdigest(),
        "latch": hashlib.sha256(
            _expected_h24_state(
                intent_sha256,
                "automatic-handoff-dispatched-no-replay",
            )
        ).hexdigest(),
        "evidence": hashlib.sha256((intent_sha256 + "\n").encode("ascii")).hexdigest(),
    }
    if match is None or match.groupdict() != expected:
        raise ContractError("H24 enable/latch/evidence intent binding changed")
    return {
        "proof": True,
        "intent_sha256": intent_sha256,
        "enable_sha256": expected["enable"],
        "latch_sha256": expected["latch"],
        "evidence_sha256": expected["evidence"],
        "userdata_write_count": 0,
        "record": record,
    }


def _write_record(
    transaction_dir: Path,
    index: int,
    action: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if index >= len(JOURNAL_NAMES):
        raise ContractError("H24 D1 journal overflow")
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
                raise ContractError("H24 D1 journal has a gap")
            break
        value = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or value.get("schema") != SCHEMA
            or value.get("sequence") != index
            or value.get("action") != JOURNAL_ACTIONS[index]
        ):
            raise ContractError("H24 D1 journal record changed")
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
        f1.PRIVATE_RUN_BASE / manifest["run_id"] / "h24-d1"
    ).resolve()
    if resolved.parent != expected_parent or resolved.exists() == must_be_absent:
        state = "absent" if must_be_absent else "existing"
        raise ContractError(f"H24 D1 transaction path is not exact and {state}")
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
    observer = manifest["observer"]
    return {
        "schema": APPROVAL_BINDING_SCHEMA,
        "workflow": "A90_H24_ATTENDED_PERSISTENT_SERVER_D1_V1",
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
        "observer_private_key_sha256": observer["private_key"]["sha256"],
        "observer_public_key_sha256": observer["public_key_sha256"],
        "action_allowlist": [
            ["auto-handoff-arm-reboot", ARM_TOKEN, "<intent-sha256>"]
        ],
        "action_budget": 1,
        "duration_sec": APPROVAL_TTL_SEC,
        "payload_transfer_count": 0,
        "partition_write_count": 0,
        "userdata_write_count": 0,
        "candidate_replay": False,
        "automatic_native_return_expected": False,
        "persistent_debian_expected": True,
        "diagnostic_native_fallback_allowed": True,
        "diagnostic_record_required_for_attribution": True,
        "missing_diagnostic_record_verdict": "NO_PROOF_NO_REPLAY",
        "physical_return_dispatched_by_runner": False,
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
        raise ContractError("H24 D1 approval is not a private regular file")
    value = json.loads(path.read_text(encoding="utf-8"))
    binding = value.get("approval_binding") if isinstance(value, dict) else None
    if not isinstance(binding, dict):
        raise ContractError("H24 D1 approval binding is absent")
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
        raise ContractError("H24 D1 approval is not fresh and exact")
    return value


def _zero_effect_counts(result: dict[str, Any]) -> bool:
    return all(
        result.get(name) == expected
        for name, expected in {
            "arm_dispatch_count": 1,
            "reboot_dispatch_count": 1,
            "payload_transfer_count": 0,
            "partition_write_count": 0,
            "flash_count": 0,
            "sd_rootfs_stage_count": 0,
            "userdata_write_count": 0,
            "physical_return_reboot_dispatch_count": 0,
        }.items()
    )


def _valid_same_intent(value: Any, intent_sha256: str) -> bool:
    expected_enable = hashlib.sha256(
        _expected_h24_state(intent_sha256, "armed-after-native-health")
    ).hexdigest()
    expected_latch = hashlib.sha256(
        _expected_h24_state(
            intent_sha256,
            "automatic-handoff-dispatched-no-replay",
        )
    ).hexdigest()
    expected_evidence = hashlib.sha256(
        (intent_sha256 + "\n").encode("ascii")
    ).hexdigest()
    script = _same_intent_script()
    command = ["run", "/bin/busybox", "sh", "-c", script]
    try:
        base.require_exact_f1_command_receipt(
            value.get("record") if isinstance(value, dict) else None,
            command,
            "durable H24 same-intent binding",
        )
    except Exception:
        return False
    return bool(
        isinstance(value, dict)
        and value.get("proof") is True
        and value.get("intent_sha256") == intent_sha256
        and value.get("enable_sha256") == expected_enable
        and value.get("latch_sha256") == expected_latch
        and value.get("evidence_sha256") == expected_evidence
        and value.get("userdata_write_count") == 0
        and isinstance(value.get("record"), dict)
    )


def _valid_unmounted_userdata(value: Any) -> bool:
    script = _unmounted_script()
    command = ["run", "/bin/busybox", "sh", "-c", script]
    try:
        base.require_exact_f1_command_receipt(
            value.get("record") if isinstance(value, dict) else None,
            command,
            "durable H24 unmounted userdata",
        )
    except Exception:
        return False
    return bool(
        isinstance(value, dict)
        and value.get("proof") is True
        and isinstance(value.get("device"), str)
        and re.fullmatch(r"[1-9][0-9]*:[0-9]+", value["device"]) is not None
        and value.get("devt_policy") == "runtime-resolved-same-session"
        and value.get("mount_count") == 0
        and value.get("userdata_write_count") == 0
        and value.get("command_sha256")
        == hashlib.sha256(script.encode("utf-8")).hexdigest()
        and isinstance(value.get("record"), dict)
    )


def _valid_native_health(value: Any, manifest: dict[str, Any]) -> bool:
    try:
        f1.validate_candidate_native_health(value, manifest)
    except Exception:
        return False
    return True


def _valid_auto_handoff_11(result: dict[str, Any]) -> bool:
    status = result.get("auto_handoff_status")
    if status != {
        "binding": 1,
        "enable": 1,
        "latch": 1,
        "build": f1.CANDIDATE_BUILD,
    }:
        return False
    try:
        f1.validate_h24_auto_status_record(
            result.get("auto_handoff_status_record"), enable=1, latch=1
        )
    except Exception:
        return False
    return True


def _valid_auto_handoff_00(result: dict[str, Any]) -> bool:
    status = result.get("auto_handoff_status")
    if status != {
        "binding": 1,
        "enable": 0,
        "latch": 0,
        "build": f1.CANDIDATE_BUILD,
    }:
        return False
    try:
        f1.validate_h24_auto_status_record(
            result.get("auto_handoff_status_record"), enable=0, latch=0
        )
    except Exception:
        return False
    return True


def _valid_no_effect_result(
    result: Any,
    intent_sha256: str,
    manifest: dict[str, Any],
    opening_log: Any,
) -> bool:
    if not isinstance(result, dict) or not isinstance(opening_log, dict):
        return False
    cancellation = result.get("cancellation_fsync")
    if not isinstance(cancellation, dict):
        return False
    try:
        expected_cancellation = require_cancellation_fsync_proof(
            opening_log,
            cancellation.get("final_log_record"),
            intent_sha256,
        )
    except Exception:
        return False
    return bool(
        result.get("status") == "ABORTED_H24_ARM_REBOOT_NO_PERSISTENT_EFFECT"
        and result.get("arm_reboot_command_dispatch_count") == 1
        and result.get("arm_reboot_command_dispatch_count_max") == 1
        and result.get("arm_persistent_effect_count") == 0
        and result.get("reboot_dispatch_count") == 0
        and all(
            result.get(name) == 0
            for name in (
                "payload_transfer_count",
                "partition_write_count",
                "flash_count",
                "sd_rootfs_stage_count",
                "userdata_write_count",
            )
        )
        and _valid_auto_handoff_00(result)
        and _valid_native_health(result.get("native_health"), manifest)
        and cancellation == expected_cancellation
    )


def _valid_persistent_observation(value: Any, visible_confirmed: str) -> bool:
    if not isinstance(value, dict):
        return False
    server = value.get("server")
    server_proven = isinstance(server, dict) and server.get("proof") is True
    if not server_proven:
        return value.get("proof") is not True
    if (
        value.get("proof") is not True
        or value.get("guard_release", {}).get("released") is not True
        or visible_confirmed != "yes"
        or type(server.get("attempts")) is not int
        or server.get("attempts") < 1
        or not isinstance(server.get("transcript"), str)
    ):
        return False
    try:
        recomputed = persistent_observer.classify(
            server["transcript"],
            0,
            True,
        )
    except Exception:
        return False
    stored = {key: item for key, item in server.items() if key != "attempts"}
    return stored == recomputed


def _valid_physical_return_result(
    result: Any,
    intent_sha256: str,
    manifest: dict[str, Any],
    current: Any,
) -> bool:
    if not isinstance(result, dict) or not isinstance(current, dict):
        return False
    live_proven = current.get("status") == "PASS_A90_H24_PERSISTENT_SERVER_LIVE"
    expected_status = (
        "PASS_A90_H24_PERSISTENT_SERVER_PHYSICAL_RETURN_HEALTHY"
        if live_proven
        else "NO_PROOF_A90_H24_PERSISTENT_SERVER_PHYSICAL_RETURN_HEALTHY"
    )
    return bool(
        result.get("status") == expected_status
        and result.get("operator_physical_return") is True
        and result.get("automatic_native_return") is False
        and result.get("live_server_proven") is live_proven
        and result.get("live_result") == current
        and _zero_effect_counts(result)
        and _valid_auto_handoff_11(result)
        and _valid_same_intent(result.get("same_intent_binding"), intent_sha256)
        and _valid_native_health(result.get("native_health"), manifest)
        and _valid_unmounted_userdata(result.get("post_physical_return_userdata"))
    )


def _valid_native_fallback_result(
    result: Any,
    intent_sha256: str,
    manifest: dict[str, Any],
    opening_log: Any,
    *,
    final: bool,
) -> bool:
    attribution = (
        result.get("diagnostic_attribution") if isinstance(result, dict) else None
    )
    same_intent = (
        result.get("same_intent_binding") if isinstance(result, dict) else None
    )
    userdata = (
        result.get("native_fallback_userdata")
        if isinstance(result, dict)
        else None
    )
    expected_statuses = (
        NATIVE_FALLBACK_FINAL_STATUSES
        if final
        else NATIVE_FALLBACK_CURRENT_STATUSES
    )
    attribution_common = bool(
        isinstance(attribution, dict)
        and attribution.get("cleanup_proof") is True
        and attribution.get("cleanup_clean") is True
        and attribution.get("root_unmounted") is True
        and attribution.get("recovery_required") is False
        and attribution.get("record_persistence") == "observed-a90-log-only"
        and attribution.get("power_loss_durable_journal") is False
        and isinstance(attribution.get("final_log_record"), dict)
    )
    attribution_exact = False
    if attribution_common and attribution.get("proof") is False:
        attribution_exact = (
            attribution.get("status") == "NO_PROOF_H24_FAILURE_ATTRIBUTION"
            and attribution.get("reason") == "diagnostic record absent"
        )
    elif attribution_common and attribution.get("proof") is True:
        stage = attribution.get("stage")
        rc = attribution.get("rc")
        error = attribution.get("errno")
        root_mounted = attribution.get("root_mounted_at_failure")
        writable = attribution.get("writable_mounted")
        attribution_exact = bool(
            attribution.get("status") == "PROVED_H24_FAILURE_ATTRIBUTION"
            and isinstance(stage, str)
            and re.fullmatch(r"[a-z0-9-]+", stage) is not None
            and type(rc) is int
            and rc < 0
            and type(error) is int
            and error == -rc
            and isinstance(root_mounted, bool)
            and type(writable) is int
            and 0 <= writable <= 4
            and isinstance(attribution.get("evidence_bound"), bool)
            and isinstance(attribution.get("wifi_handoff_bound"), bool)
            and attribution.get("incident_window_match")
            is (stage in INCIDENT_WINDOW_STAGES and root_mounted)
        )
    if attribution_exact:
        try:
            attribution_exact = (
                native_fallback_attribution(
                    opening_log,
                    attribution.get("final_log_record"),
                )
                == attribution
            )
        except Exception:
            attribution_exact = False
    return bool(
        isinstance(result, dict)
        and isinstance(attribution, dict)
        and isinstance(same_intent, dict)
        and isinstance(userdata, dict)
        and result.get("status") in expected_statuses
        and result.get("status")
        == _native_fallback_status(attribution, final=final)
        and result.get("native_fallback") is True
        and attribution_exact
        and _zero_effect_counts(result)
        and result.get("server_proven") is False
        and _valid_auto_handoff_11(result)
        and _valid_same_intent(same_intent, intent_sha256)
        and _valid_native_health(result.get("native_health"), manifest)
        and _valid_unmounted_userdata(userdata)
    )


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
        raise ContractError("H24 D1 opening binding changed")
    opening_log = opening.get("opening_log")
    if not isinstance(opening_log, dict):
        raise ContractError("H24 D1 opening log is absent")
    _exact_log_text(opening_log, "H24 D1 durable opening log")
    approval_value = opening["approval_binding"]
    expected_approval = approval_binding(
        manifest,
        args,
        transaction_dir,
        created_utc=str(approval_value.get("created_utc") or ""),
        expires_utc=str(approval_value.get("expires_utc") or ""),
    )
    if approval_value != expected_approval:
        raise ContractError("H24 D1 consumed approval binding changed")
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
        raise ContractError("H24 D1 arm-reboot intent changed")
    intent_sha256 = f1.sha256_file(transaction_dir / JOURNAL_NAMES[1])
    if any(
        record.get("intent_sha256") != intent_sha256
        for record in records[2:4]
    ):
        raise ContractError("H24 D1 continuation intent binding changed")
    if len(records) >= 3 and (
        records[2].get("arm_reboot_command_dispatch_count") != 1
        or records[2].get("candidate_replay") is not False
        or not isinstance(records[2].get("dispatch_record"), dict)
    ):
        raise ContractError("H24 D1 dispatch result changed")
    if len(records) >= 4 and (
        records[3].get("arm_reboot_command_dispatch_count") != 1
        or records[3].get("candidate_replay") is not False
        or not isinstance(records[3].get("observation"), dict)
    ):
        raise ContractError("H24 D1 persistent observation changed")
    if len(records) >= 5:
        result = records[4].get("result")
        live_pending = (
            isinstance(result, dict)
            and isinstance(records[3].get("observation"), dict)
            and _valid_persistent_observation(
                records[3]["observation"],
                str(result.get("visible_confirmed") or ""),
            )
            and result
            == _live_result(
                records[3]["observation"],
                intent_sha256,
                str(result.get("visible_confirmed") or ""),
            )
            and result.get("device_safety_state")
            == "HEALTH_PENDING_PERSISTENT_DEBIAN"
            and result.get("resident_healthy") is False
            and result.get("ordinal_closed") is False
            and result.get("inter_effect_health_barrier_satisfied") is False
            and result.get("new_device_effect_authority") is False
        )
        no_effect = (
            _valid_no_effect_result(
                result,
                intent_sha256,
                manifest,
                opening_log,
            )
            and result.get("device_safety_state") == "RESIDENT_HEALTHY"
            and result.get("resident_healthy") is True
            and result.get("ordinal_closed") is False
            and result.get("inter_effect_health_barrier_satisfied") is False
            and result.get("new_device_effect_authority") is False
        )
        native_fallback_current = (
            _valid_native_fallback_result(
                result,
                intent_sha256,
                manifest,
                opening_log,
                final=False,
            )
            and result.get("device_safety_state") == "RESIDENT_HEALTHY"
            and result.get("resident_healthy") is True
            and result.get("ordinal_closed") is False
            and result.get("inter_effect_health_barrier_satisfied") is False
            and result.get("new_device_effect_authority") is False
            and result.get("native_fallback") is True
            and result.get("arm_dispatch_count") == 1
            and result.get("reboot_dispatch_count") == 1
        )
        if (
            not isinstance(result, dict)
            or result.get("schema") != RESULT_SCHEMA
            or result.get("intent_sha256") != intent_sha256
            or result.get("candidate_replay") is not False
            or not (live_pending or no_effect or native_fallback_current)
            or records[4].get("result_sha256") != f1.json_sha256(result)
        ):
            raise ContractError("H24 D1 current-state result changed")
    if len(records) >= 6:
        result = records[5].get("result")
        physical_return = (
            _valid_physical_return_result(
                result,
                intent_sha256,
                manifest,
                records[4].get("result"),
            )
        )
        no_effect_final = (
            _valid_no_effect_result(
                result,
                intent_sha256,
                manifest,
                opening_log,
            )
        )
        native_fallback_final = (
            _valid_native_fallback_result(
                result,
                intent_sha256,
                manifest,
                opening_log,
                final=True,
            )
        )
        if (
            not isinstance(result, dict)
            or result.get("schema") != RESULT_SCHEMA
            or result.get("intent_sha256") != intent_sha256
            or result.get("device_safety_state") != "RESIDENT_HEALTHY"
            or result.get("resident_healthy") is not True
            or result.get("candidate_replay") is not False
            or result.get("ordinal_closed") is not True
            or result.get("inter_effect_health_barrier_satisfied") is not True
            or result.get("new_device_effect_authority") is not False
            or result.get("prior_current_result_sha256")
            != records[4].get("result_sha256")
            or not (physical_return or no_effect_final or native_fallback_final)
            or records[5].get("result_sha256") != f1.json_sha256(result)
        ):
            raise ContractError("H24 D1 final health changed")
    if len(records) == 7 and (
        records[6].get("result") != records[5].get("result")
        or records[6].get("result_sha256") != records[5].get("result_sha256")
    ):
        raise ContractError("H24 D1 closed result changed")
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
    visible_confirmed: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "proof": False,
        "pre_reboot_binding": binding,
        "automatic_native_return_expected": False,
        "device_safety_state": "HEALTH_PENDING_PERSISTENT_DEBIAN",
    }
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
        result["server"] = persistent_observer.observe(
            spec.observer_key,
            deadline_seconds=90.0,
            connect_timeout=5.0,
            visible_hud=visible_confirmed == "yes",
        )
        legacy.validate_post_reboot_ncm_identity(binding, ncm, require_live=True)
        result["debian_ncm_continuity"]["after_ssh"] = True
        result["proof"] = result["server"].get("proof") is True
    except Exception as exc:  # bounded observation only; never replay the effect
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


def _live_result(
    observation: dict[str, Any],
    intent_sha256: str,
    visible_confirmed: str,
) -> dict[str, Any]:
    server = observation.get("server")
    server_proven = isinstance(server, dict) and server.get("proof") is True
    guard_released = observation.get("guard_release", {}).get("released") is True
    if server_proven and guard_released and visible_confirmed == "yes":
        status = "PASS_A90_H24_PERSISTENT_SERVER_LIVE"
    elif visible_confirmed == "no":
        status = "REFUTED_A90_H24_PERSISTENT_SERVER_DISPLAY"
    else:
        status = "NO_PROOF_A90_H24_PERSISTENT_SERVER_LIVE"
    return {
        "schema": RESULT_SCHEMA,
        "status": status,
        "intent_sha256": intent_sha256,
        "device_safety_state": "HEALTH_PENDING_PERSISTENT_DEBIAN",
        "resident_healthy": False,
        "ordinal_closed": False,
        "inter_effect_health_barrier_satisfied": False,
        "new_device_effect_authority": False,
        "automatic_native_return_expected": False,
        "physical_return_dispatched_by_runner": False,
        "candidate_replay": False,
        "arm_dispatch_count": 1,
        "reboot_dispatch_count": 1,
        "payload_transfer_count": 0,
        "partition_write_count": 0,
        "flash_count": 0,
        "sd_rootfs_stage_count": 0,
        "userdata_write_count": 0,
        "observation": observation,
        "visible_confirmed": visible_confirmed,
        "server_proven": server_proven,
        "guard_released": guard_released,
    }


def _dispatch_and_observe(
    spec: Any,
    args: argparse.Namespace,
    transaction_dir: Path,
    guard: Any,
    binding: dict[str, Any],
    intent_sha256: str,
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
    observation = _observe(
        spec,
        args,
        transaction_dir,
        guard,
        binding,
        visible_confirmed,
    )
    observation["arm_reboot_dispatch_record"] = dispatch_record
    _write_record(
        transaction_dir,
        3,
        "persistent-observation",
        {
            "intent_sha256": intent_sha256,
            "arm_reboot_command_dispatch_count": 1,
            "candidate_replay": False,
            "observation": observation,
        },
    )
    result = _live_result(
        observation,
        intent_sha256,
        visible_confirmed,
    )
    result_sha = f1.json_sha256(result)
    _write_record(
        transaction_dir,
        4,
        "current-state",
        {"result_sha256": result_sha, "result": result},
    )
    return result


def execute(args: argparse.Namespace) -> dict[str, Any]:
    if args.operator_attended is not True:
        raise ContractError("H24 automatic UFS handoff is attended-only")
    manifest, spec, install_result = load_inputs(args)
    transaction_dir = _require_transaction_dir(
        manifest,
        args.transaction_dir,
        must_be_absent=True,
    )
    effect_args = _effect_args()
    base.staging.require_exact_bridge(spec.stage, effect_args)
    native = base.verify_candidate_health(spec, effect_args)
    f1.validate_candidate_native_health(native, manifest)
    status_record, status = require_status(effect_args, enable=0, latch=0)
    opening_log = base.run_f1_cmd(effect_args, ["logcat"])
    base.require_auto_handoff_log_exclusively_unarmed(
        str(opening_log.get("text") or ""),
        "H24 first resident boot log",
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


def _unmounted_script() -> str:
    return "\n".join(
        (
            "set -eu",
            "N=0",
            "for U in /sys/class/block/*/uevent; do",
            "  /bin/busybox grep -q '^PARTNAME=userdata$' \"$U\" || continue",
            "  N=$((N + 1))",
            "  DEVNAME=$(/bin/busybox sed -n 's/^DEVNAME=//p' \"$U\")",
            "  MAJ=$(/bin/busybox sed -n 's/^MAJOR=//p' \"$U\")",
            "  MIN=$(/bin/busybox sed -n 's/^MINOR=//p' \"$U\")",
            "done",
            '[ "$N" = 1 ]',
            '[ "$DEVNAME" = sda33 ]',
            "C=$(/bin/busybox awk -v d=\"$MAJ:$MIN\" "
            "'$3 == d {n++} END {print n+0}' /proc/self/mountinfo)",
            '[ "$C" = 0 ]',
            'echo "A90H24_POST_PHYSICAL_RETURN devt=$MAJ:$MIN '
            'ufs_mount_count=$C userdata_write=0"',
        )
    )


def _prove_userdata_unmounted(effect_args: argparse.Namespace) -> dict[str, Any]:
    script = _unmounted_script()
    command = ["run", "/bin/busybox", "sh", "-c", script]
    record = base.run_f1_cmd(effect_args, command)
    exact = base.require_exact_f1_command_receipt(
        record,
        command,
        "H24 post-physical-return unmounted userdata",
    )
    lines = [
        line.strip()
        for line in str(exact.get("text") or "").replace("\r", "").splitlines()
        if line.strip().startswith("A90H24_POST_PHYSICAL_RETURN ")
    ]
    match = UNMOUNTED_RE.fullmatch(lines[0]) if len(lines) == 1 else None
    if match is None or int(match.group("count"), 10) != 0:
        raise ContractError("H24 userdata is not one exact unmounted identity")
    device = f"{int(match.group('major'), 10)}:{int(match.group('minor'), 10)}"
    return {
        "proof": True,
        "device": device,
        "devt_policy": "runtime-resolved-same-session",
        "mount_count": 0,
        "userdata_write_count": 0,
        "command_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "record": record,
    }


def finalize_physical_return(args: argparse.Namespace) -> dict[str, Any]:
    """Close after operator physical return using read-only native facts only."""
    if (
        args.operator_attended is not True
        or args.physical_return_confirmed is not True
    ):
        raise ContractError(
            "H24 physical-return finalization requires attended confirmation"
        )
    manifest, spec, _ = load_inputs(args)
    transaction_dir = _require_transaction_dir(
        manifest,
        args.transaction_dir,
        must_be_absent=False,
    )
    records = _read_records(transaction_dir)
    if len(records) not in (2, 3, 4, 5, 6, 7):
        raise ContractError(
            "physical-return finalization requires an exact dispatched prefix"
        )
    intent_sha256 = _validate_records(records, transaction_dir, args, manifest)
    assert intent_sha256 is not None
    if len(records) >= 5 and (
        records[4].get("result", {}).get("device_safety_state")
        != "HEALTH_PENDING_PERSISTENT_DEBIAN"
    ):
        raise ContractError("physical return contradicts the durable live state")
    if len(records) == 7:
        return records[6]["result"]
    if len(records) == 6:
        result = records[5]["result"]
        result_sha = records[5]["result_sha256"]
        _write_record(
            transaction_dir,
            6,
            "closed",
            {"result_sha256": result_sha, "result": result},
        )
        return result

    effect_args = _effect_args()
    base.staging.require_exact_bridge(spec.stage, effect_args)
    status_record, status = require_status(effect_args, enable=1, latch=1)
    same_intent = require_same_intent_state(effect_args, intent_sha256)
    native = base.verify_candidate_health(spec, effect_args)
    f1.validate_candidate_native_health(native, manifest)
    unmounted = _prove_userdata_unmounted(effect_args)
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
                    "dispatch_inferred_from_exact_latched_physical_return": True,
                },
            },
        )
        records = _read_records(transaction_dir)
    if len(records) == 3:
        observation: dict[str, Any] = {
            "proof": False,
            "pre_reboot_binding": records[1].get("pre_reboot_binding"),
            "automatic_native_return_expected": False,
            "device_safety_state": "HEALTH_PENDING_PERSISTENT_DEBIAN",
            "observer_error": {
                "type": "PhysicalReturnBeforeDurableObservation",
                "message": "persistent server proof unavailable without effect replay",
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
            "persistent-observation",
            {
                "intent_sha256": intent_sha256,
                "arm_reboot_command_dispatch_count": 1,
                "candidate_replay": False,
                "observation": observation,
            },
        )
        records = _read_records(transaction_dir)
    if len(records) == 4:
        observation = records[3]["observation"]
        live_result = _live_result(observation, intent_sha256, "unavailable")
        live_sha = f1.json_sha256(live_result)
        _write_record(
            transaction_dir,
            4,
            "current-state",
            {"result_sha256": live_sha, "result": live_result},
        )
        records = _read_records(transaction_dir)
    live_result = records[4]["result"]
    live_proven = live_result.get("status") == "PASS_A90_H24_PERSISTENT_SERVER_LIVE"
    result = {
        "schema": RESULT_SCHEMA,
        "status": (
            "PASS_A90_H24_PERSISTENT_SERVER_PHYSICAL_RETURN_HEALTHY"
            if live_proven
            else "NO_PROOF_A90_H24_PERSISTENT_SERVER_PHYSICAL_RETURN_HEALTHY"
        ),
        "intent_sha256": intent_sha256,
        "prior_current_result_sha256": records[4]["result_sha256"],
        "device_safety_state": "RESIDENT_HEALTHY",
        "resident_healthy": True,
        "ordinal_closed": True,
        "inter_effect_health_barrier_satisfied": True,
        "new_device_effect_authority": False,
        "operator_physical_return": True,
        "automatic_native_return": False,
        "physical_return_reboot_dispatch_count": 0,
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
        "same_intent_binding": same_intent,
        "native_health": native,
        "post_physical_return_userdata": unmounted,
        "live_server_proven": live_proven,
        "live_result": live_result,
    }
    result_sha = f1.json_sha256(result)
    _write_record(
        transaction_dir,
        5,
        "final-health",
        {"result_sha256": result_sha, "result": result},
    )
    _write_record(
        transaction_dir,
        6,
        "closed",
        {"result_sha256": result_sha, "result": result},
    )
    return result


def finalize_no_effect(args: argparse.Namespace) -> dict[str, Any]:
    if args.operator_attended is not True:
        raise ContractError("H24 no-effect finalization is attended-only")
    manifest, spec, _ = load_inputs(args)
    transaction_dir = _require_transaction_dir(
        manifest,
        args.transaction_dir,
        must_be_absent=False,
    )
    records = _read_records(transaction_dir)
    if len(records) not in (2, 3, 4, 5, 6, 7):
        raise ContractError("no-effect finalization requires an exact pending prefix")
    intent_sha256 = _validate_records(records, transaction_dir, args, manifest)
    assert intent_sha256 is not None
    if len(records) >= 5 and (
        records[4].get("result", {}).get("status")
        != "ABORTED_H24_ARM_REBOOT_NO_PERSISTENT_EFFECT"
    ):
        raise ContractError("no-effect finalization contradicts persistent Debian")
    if len(records) == 7:
        return records[6]["result"]
    if len(records) == 6:
        result = records[5]["result"]
        result_sha = records[5]["result_sha256"]
        _write_record(
            transaction_dir,
            6,
            "closed",
            {"result_sha256": result_sha, "result": result},
        )
        return result
    if len(records) == 5:
        current = records[4]["result"]
        result = {
            **current,
            "ordinal_closed": True,
            "inter_effect_health_barrier_satisfied": True,
            "prior_current_result_sha256": records[4]["result_sha256"],
        }
        result_sha = f1.json_sha256(result)
        _write_record(
            transaction_dir,
            5,
            "final-health",
            {"result_sha256": result_sha, "result": result},
        )
        _write_record(
            transaction_dir,
            6,
            "closed",
            {"result_sha256": result_sha, "result": result},
        )
        return result

    effect_args = _effect_args()
    base.staging.require_exact_bridge(spec.stage, effect_args)
    status_record, status = require_status(effect_args, enable=0, latch=0)
    native = base.verify_candidate_health(spec, effect_args)
    f1.validate_candidate_native_health(native, manifest)
    legacy.require_pre_reboot_observer_binding_current(
        spec,
        effect_args,
        records[1]["pre_reboot_binding"],
    )
    if len(records) == 4 and records[3]["observation"].get("proof") is True:
        raise ContractError("no-effect finalization contradicts a proved observation")
    opening_log = records[0].get("opening_log")
    if not isinstance(opening_log, dict):
        raise ContractError("H24 D1 opening log is absent")
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
            "persistent-observation",
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
    current = {
        "schema": RESULT_SCHEMA,
        "status": "ABORTED_H24_ARM_REBOOT_NO_PERSISTENT_EFFECT",
        "intent_sha256": intent_sha256,
        "device_safety_state": "RESIDENT_HEALTHY",
        "resident_healthy": True,
        "ordinal_closed": False,
        "inter_effect_health_barrier_satisfied": False,
        "new_device_effect_authority": False,
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
    current_sha = f1.json_sha256(current)
    _write_record(
        transaction_dir,
        4,
        "current-state",
        {"result_sha256": current_sha, "result": current},
    )
    result = {
        **current,
        "ordinal_closed": True,
        "inter_effect_health_barrier_satisfied": True,
        "prior_current_result_sha256": current_sha,
    }
    result_sha = f1.json_sha256(result)
    _write_record(
        transaction_dir,
        5,
        "final-health",
        {"result_sha256": result_sha, "result": result},
    )
    _write_record(
        transaction_dir,
        6,
        "closed",
        {"result_sha256": result_sha, "result": result},
    )
    return result


def _native_fallback_status(attribution: dict[str, Any], *, final: bool) -> str:
    suffix = "HEALTHY" if final else "CURRENT"
    if attribution.get("proof") is not True:
        return f"NO_PROOF_H24_FAILURE_ATTRIBUTION_NATIVE_FALLBACK_{suffix}"
    if attribution.get("incident_window_match") is True:
        return (
            "REFUTED_H24_POST_ROOT_FAILURE_ATTRIBUTED_"
            f"NATIVE_FALLBACK_{suffix}"
        )
    return f"REFUTED_H24_OTHER_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_{suffix}"


def finalize_native_fallback(args: argparse.Namespace) -> dict[str, Any]:
    """Close one returned H24 diagnostic handoff without replaying its effect."""
    if args.operator_attended is not True:
        raise ContractError("H24 native-fallback finalization is attended-only")
    manifest, spec, _ = load_inputs(args)
    transaction_dir = _require_transaction_dir(
        manifest,
        args.transaction_dir,
        must_be_absent=False,
    )
    records = _read_records(transaction_dir)
    if len(records) not in (2, 3, 4, 5, 6, 7):
        raise ContractError(
            "native-fallback finalization requires an exact dispatched prefix"
        )
    intent_sha256 = _validate_records(records, transaction_dir, args, manifest)
    assert intent_sha256 is not None
    if len(records) == 7:
        return records[6]["result"]
    if len(records) == 6:
        result = records[5]["result"]
        result_sha = records[5]["result_sha256"]
        _write_record(
            transaction_dir,
            6,
            "closed",
            {"result_sha256": result_sha, "result": result},
        )
        return result
    if len(records) == 5 and (
        records[4].get("result", {}).get("status")
        in NATIVE_FALLBACK_CURRENT_STATUSES
    ):
        current = records[4]["result"]
        result = {
            **current,
            "status": _native_fallback_status(
                current["diagnostic_attribution"],
                final=True,
            ),
            "ordinal_closed": True,
            "inter_effect_health_barrier_satisfied": True,
            "prior_current_result_sha256": records[4]["result_sha256"],
        }
        result_sha = f1.json_sha256(result)
        _write_record(
            transaction_dir,
            5,
            "final-health",
            {"result_sha256": result_sha, "result": result},
        )
        _write_record(
            transaction_dir,
            6,
            "closed",
            {"result_sha256": result_sha, "result": result},
        )
        return result

    effect_args = _effect_args()
    base.staging.require_exact_bridge(spec.stage, effect_args)
    status_record, status = require_status(effect_args, enable=1, latch=1)
    same_intent = require_same_intent_state(effect_args, intent_sha256)
    native = base.verify_candidate_health(spec, effect_args)
    f1.validate_candidate_native_health(native, manifest)
    unmounted = _prove_userdata_unmounted(effect_args)
    opening_log = records[0].get("opening_log")
    if not isinstance(opening_log, dict):
        raise ContractError("H24 D1 opening log is absent")
    final_log = base.run_f1_cmd(effect_args, ["logcat"])
    attribution = native_fallback_attribution(opening_log, final_log)

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
                    "dispatch_inferred_from_exact_latched_native_fallback": True,
                },
            },
        )
        records = _read_records(transaction_dir)
    if len(records) == 3:
        _write_record(
            transaction_dir,
            3,
            "persistent-observation",
            {
                "intent_sha256": intent_sha256,
                "arm_reboot_command_dispatch_count": 1,
                "candidate_replay": False,
                "observation": {
                    "proof": attribution.get("proof") is True,
                    "native_fallback": True,
                    "diagnostic_attribution": attribution,
                    "server_proven": False,
                },
            },
        )
        records = _read_records(transaction_dir)

    current = {
        "schema": RESULT_SCHEMA,
        "status": _native_fallback_status(attribution, final=False),
        "intent_sha256": intent_sha256,
        "device_safety_state": "RESIDENT_HEALTHY",
        "resident_healthy": True,
        "ordinal_closed": False,
        "inter_effect_health_barrier_satisfied": False,
        "new_device_effect_authority": False,
        "native_fallback": True,
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
        "same_intent_binding": same_intent,
        "native_health": native,
        "native_fallback_userdata": unmounted,
        "diagnostic_attribution": attribution,
        "server_proven": False,
        "physical_return_reboot_dispatch_count": 0,
    }
    if len(records) == 4:
        current_sha = f1.json_sha256(current)
        _write_record(
            transaction_dir,
            4,
            "current-state",
            {"result_sha256": current_sha, "result": current},
        )
        records = _read_records(transaction_dir)
    else:
        current_sha = records[4]["result_sha256"]

    result = {
        **current,
        "status": _native_fallback_status(attribution, final=True),
        "ordinal_closed": True,
        "inter_effect_health_barrier_satisfied": True,
        "prior_current_result_sha256": current_sha,
    }
    result_sha = f1.json_sha256(result)
    _write_record(
        transaction_dir,
        5,
        "final-health",
        {"result_sha256": result_sha, "result": result},
    )
    _write_record(
        transaction_dir,
        6,
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
    if len(records) < 2:
        return {
            "schema": RECONCILE_SCHEMA,
            "terminal": "NO_DURABLE_D1_EFFECT",
            "records_present": len(records),
            "candidate_replay": False,
            "arm_replay": False,
            "reboot_replay": False,
        }
    if len(records) == 7:
        return {
            "schema": RECONCILE_SCHEMA,
            "terminal": "CLOSED_EXACT_NO_REPLAY",
            "records_present": 7,
            "result": records[6]["result"],
            "candidate_replay": False,
            "arm_replay": False,
            "reboot_replay": False,
        }
    if len(records) == 6:
        return {
            "schema": RECONCILE_SCHEMA,
            "terminal": "FINAL_HEALTH_READY_TO_CLOSE_NO_REPLAY",
            "records_present": 6,
            "result": records[5]["result"],
            "candidate_replay": False,
            "arm_replay": False,
            "reboot_replay": False,
        }
    if len(records) == 5:
        current = records[4]["result"]
        if current.get("status") in NATIVE_FALLBACK_CURRENT_STATUSES:
            terminal = "NATIVE_FALLBACK_READY_TO_CLOSE_NO_REPLAY"
        elif (
            current.get("device_safety_state")
            == "HEALTH_PENDING_PERSISTENT_DEBIAN"
        ):
            terminal = "PERSISTENT_DEBIAN_LIVE_HEALTH_PENDING_NO_REPLAY"
        else:
            terminal = "NO_PERSISTENT_EFFECT_READY_FOR_FINALIZE"
        return {
            "schema": RECONCILE_SCHEMA,
            "terminal": terminal,
            "records_present": 5,
            "current_state": current,
            "candidate_replay": False,
            "arm_replay": False,
            "reboot_replay": False,
        }

    status = None
    status_error = None
    health = None
    health_error = None
    cancellation_evidence = None
    cancellation_error = None
    effect_args = _effect_args()
    base.staging.require_exact_bridge(spec.stage, effect_args)
    try:
        record = base.run_f1_cmd(effect_args, ["auto-handoff-status"])
        status = parse_status(record)
    except Exception as exc:
        status_error = {"type": type(exc).__name__, "message": str(exc)}
    try:
        health = base.verify_candidate_health(spec, effect_args)
        f1.validate_candidate_native_health(health, manifest)
    except Exception as exc:
        health_error = {"type": type(exc).__name__, "message": str(exc)}
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
    if (
        len(records) >= 2
        and isinstance(status, dict)
        and (status.get("enable"), status.get("latch")) == (1, 1)
        and health is not None
    ):
        terminal = "PHYSICAL_RETURN_READY_FOR_FINALIZE_NO_REPLAY"
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
        observed = (
            len(records) == 4
            and records[3].get("observation", {}).get("proof") is True
        )
        terminal = (
            "PERSISTENT_DEBIAN_OBSERVED_CURRENT_STATE_NOT_DURABLE_NO_REPLAY"
            if observed
            else "ARM_REBOOT_OR_PERSISTENT_DEBIAN_PENDING_NO_REPLAY"
        )
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
    modes.add_argument("--finalize-physical-return", action="store_true")
    modes.add_argument("--finalize-native-fallback", action="store_true")
    modes.add_argument("--finalize-no-effect", action="store_true")
    modes.add_argument("--reconcile", action="store_true")
    result.add_argument("--operator-attended", action="store_true")
    result.add_argument("--physical-return-confirmed", action="store_true")
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
            if (
                args.approval is not None
                or args.operator_attended
                or args.physical_return_confirmed
            ):
                raise ContractError(
                    "D1 approval preparation accepts no live authority inputs"
                )
            value = prepare_approval(args)
        elif args.execute:
            if args.approval is None:
                raise ContractError("H24 D1 execute requires fresh exact approval")
            if args.physical_return_confirmed:
                raise ContractError("D1 execute cannot confirm a later physical return")
            value = execute(args)
        elif args.finalize_physical_return:
            if args.approval is not None:
                raise ContractError("D1 continuation accepts no new approval")
            value = finalize_physical_return(args)
        elif args.finalize_native_fallback:
            if args.approval is not None or args.physical_return_confirmed:
                raise ContractError("D1 continuation accepts no new approval")
            value = finalize_native_fallback(args)
        elif args.finalize_no_effect:
            if args.approval is not None or args.physical_return_confirmed:
                raise ContractError("D1 continuation accepts no new approval")
            value = finalize_no_effect(args)
        else:
            if args.approval is not None or args.physical_return_confirmed:
                raise ContractError("D1 reconciliation accepts no new approval")
            value = reconcile(args)
    except (ContractError, f1.ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"H24_UFS_D1_ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
