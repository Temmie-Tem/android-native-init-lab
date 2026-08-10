#!/usr/bin/env python3
"""Close the exact H17 native-fallback incident without replay or device effect.

The consumed H17 arm/reboot/handoff is immutable.  This adapter binds its exact
five-record journal prefix and the exact private read-only diagnosis, performs
only freshly approved bounded reads, and appends the two original D1 terminal
records.  It cannot arm, reboot, hand off, mount, start or stop services,
transfer a payload, flash, clear state, or write userdata.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_boot_benchmark_v1 as benchmark  # noqa: E402
import a90_h17_ufs_f1_runner_v1 as f1  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402


QUALIFICATION_SCHEMA = "a90-h17-native-fallback-qualification-v1"
APPROVAL_SCHEMA = "a90-h17-native-fallback-approval-prepared-v1"
APPROVAL_BINDING_SCHEMA = "a90-h17-native-fallback-approval-binding-v1"
CAPABILITY = "A90_H17_NATIVE_FALLBACK_NO_REPLAY_FINALIZER_V1"
APPROVAL_PREFIX = "A90-H17-NATIVE-FALLBACK-CLOSE-D0-APPROVE:"
APPROVAL_TTL_SEC = 1800
RUN_ID = "a90-h17-ufs-f1-20260810-01"
MANIFEST_SHA256 = (
    "5f96d3b0223d0bd1729703bae69c576e789f0c84003d881b1c2184e6a350df52"
)
INSTALL_RESULT_SHA256 = (
    "a9f8308c8a6d4e0e57b4c26142d7aa086a6e526c8dade0c056e85f49d94c036a"
)
PREDECESSOR_EXECUTION_SHA256 = (
    "d95ceb7fc7423ccce208086f43e38998691ca83186d42ceab13b09ffd4155e7e"
)
INTENT_SHA256 = (
    "a812f05dd24795295d0cab74619969bbdf19301dd493a202bdbc1c7e8d5a6ae2"
)
DIAGNOSIS_SHA256 = (
    "15fde5c34d8d6277867048cdc49842eb6210e047ac93e05e0a5437418b7beedd"
)
H17_BOOT_DETAIL = (
    "A90 Linux init 0.11.185 "
    "(phase3-minimal-h17-ufs-ro-observer-auth-persistent-hud)"
)
FAILED_HANDOFF_STAGES = (
    "native_runtime_ready",
    "native_wifi_companion_async_started",
    "native_wifi_autoconnect_inactive",
    "native_ncm_handoff_ready",
    "native_direct_handoff_ready",
    "native_services_ready",
    "auto_handoff_check",
    "auto_handoff_dispatched",
    "handoff_begin",
    "userdata_identity_initial_done",
    "display_release_done",
    "userdata_identity_post_display_done",
    "root_mounted",
    "handoff_failed_native",
    "auto_handoff_returned_native",
    "native_fallback_ready",
)
PRIVATE_RUN_BASE = (REPO_ROOT / "workspace/private/runs/server-distro").resolve()
EXPECTED_MANIFEST_PATH = (PRIVATE_RUN_BASE / RUN_ID / "manifest.json").resolve()
EXPECTED_INSTALL_RESULT_PATH = (
    PRIVATE_RUN_BASE / RUN_ID / "h17-f1-live" / "result.json"
).resolve()
EXPECTED_TRANSACTION_DIR = (
    PRIVATE_RUN_BASE / RUN_ID / "h17-d1" / "run01"
).resolve()
EXPECTED_DIAGNOSIS_PATH = (
    PRIVATE_RUN_BASE
    / RUN_ID
    / "h17-d1"
    / "run01-native-readonly-diagnosis-01.json"
).resolve()
APPROVAL_PATH = (
    PRIVATE_RUN_BASE
    / RUN_ID
    / "h17-d1"
    / "run01-native-fallback-incident-approval-prepared.json"
).resolve()
QUALIFICATION_REL = (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h17/native-fallback-qualification.json"
)
REVIEW_REPORT_REL = (
    "docs/reports/"
    "A90_H17_NATIVE_FALLBACK_FINALIZER_INDEPENDENT_REVIEW_2026-08-10.json"
)
INCIDENT_REPORT_REL = (
    "docs/reports/A90_H17_POST_ROOT_MOUNT_NATIVE_FALLBACK_INCIDENT_2026-08-10.md"
)
TARGET_CONTRACT_REL = "docs/operations/targets/A90_TARGET_CONTRACT.md"
ADAPTER_REL = (
    "workspace/public/src/scripts/server-distro/"
    "a90_h17_native_fallback_finalizer_v1.py"
)
PREDECESSOR_D1_REL = (
    "workspace/public/src/scripts/server-distro/a90_h17_ufs_d1_runner_v1.py"
)
EXECUTION_RELS = tuple(
    sorted(
        (set(f1.EXECUTION_SOURCE_RELS) - {PREDECESSOR_D1_REL})
        | {INCIDENT_REPORT_REL, ADAPTER_REL}
    )
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
PREFIX_SHA256 = (
    "086d61dcd8a5941b48a9923bfe7ab7e3dedd8e514dfa3fccad7cbf31245a15a9",
    "a812f05dd24795295d0cab74619969bbdf19301dd493a202bdbc1c7e8d5a6ae2",
    "142ef19a4f8414006377400e09afe6f0bbf1de51281620a7ec8c4c8a55b58a6d",
    "cfc74bd2ee4ca0240ddaf49fd14dbc4d69c533c9335a940779b50b61a762f895",
    "ebe24ed8ba1063996d733d964e60487bf5821c15028018a85525af079ad8c5fe",
)
UNMOUNTED_RE = re.compile(
    r"^A90H17_NATIVE_FALLBACK devt=(?P<major>[0-9]+):"
    r"(?P<minor>[0-9]+) ufs_mount_count=(?P<count>[0-9]+) "
    r"userdata_write=0$"
)
STATUS_RE = re.compile(
    r"^A90AUTO_STATUS binding=(?P<binding>[01]) "
    r"enable=(?P<enable>-?[0-9]+) latch=(?P<latch>-?[0-9]+) "
    r"build=(?P<build>[a-z0-9._-]+)\r?$",
    re.MULTILINE,
)
JOURNAL_MAX_BYTES = 16 * 1024 * 1024


class ContractError(RuntimeError):
    """Raised before replay, effect, or overclaim in the exact incident close."""


def _effect_args() -> argparse.Namespace:
    return argparse.Namespace(
        bridge_host="127.0.0.1",
        bridge_port=54321,
        bridge_timeout=60.0,
        remote_timeout=60.0,
        flash_command_timeout=900.0,
        ssh_connect_timeout=8.0,
        poll_interval=3.0,
        transfer_timeout=1200.0,
    )


def execution_closure() -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    digest = hashlib.sha256()
    for relative in EXECUTION_RELS:
        path = (REPO_ROOT / relative).resolve(strict=True)
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise ContractError(f"native-fallback source is not regular: {relative}")
        sha = f1.sha256_file(path)
        files[relative] = {"size": info.st_size, "sha256": sha}
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(info.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(sha.encode("ascii"))
        digest.update(b"\0")
    return {"sha256": digest.hexdigest(), "files": files}


def _require_regular(path: Path, expected_sha256: str, label: str) -> Path:
    lexical = path.absolute()
    if lexical.is_symlink():
        raise ContractError(f"{label} is a symlink")
    resolved = lexical.resolve(strict=True)
    info = resolved.stat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or f1.sha256_file(resolved) != expected_sha256
    ):
        raise ContractError(f"{label} changed")
    return resolved


def _load_json(path: Path, expected_sha256: str, label: str) -> dict[str, Any]:
    resolved = _require_regular(path, expected_sha256, label)
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} is not exact JSON") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{label} root is not an object")
    return value


def _validate_manifest(value: dict[str, Any]) -> None:
    target = value.get("target")
    candidate = value.get("candidate_boot")
    authority = value.get("authority")
    if (
        value.get("schema") != f1.SCHEMA
        or value.get("run_id") != RUN_ID
        or value.get("status") != "ready-for-attended-f1"
        or value.get("capability") != f1.CAPABILITY
        or value.get("execution_closure", {}).get("sha256")
        != PREDECESSOR_EXECUTION_SHA256
        or not isinstance(target, dict)
        or target.get("profile") != "galaxy-a90-5g-native-init"
        or target.get("bridge_device") != f1.EXACT_BRIDGE_DEVICE
        or not isinstance(target.get("bridge_realpath"), str)
        or re.fullmatch(r"/dev/ttyACM[0-9]+", target["bridge_realpath"]) is None
        or not isinstance(candidate, dict)
        or candidate.get("expected_version") != f1.CANDIDATE_VERSION
        or candidate.get("expected_build") != f1.CANDIDATE_BUILD
        or candidate.get("partition") != "boot"
        or candidate.get("sha256")
        != "a86026735537e97020d24cf633429bb347f59bdb77a787f52b437d62828db814"
        or candidate.get("size") != 58384384
        or not isinstance(authority, dict)
        or authority.get("candidate_replay") is not False
        or authority.get("rootfs_payload_count") != 0
        or authority.get("sd_stage_count") != 0
        or authority.get("userdata_write_count") != 0
        or authority.get("manifest_grants_live_authority") is not False
    ):
        raise ContractError("H17 incident manifest binding changed")


def _validate_install_result(value: dict[str, Any]) -> None:
    if (
        value.get("schema") != f1.RESULT_SCHEMA
        or value.get("status") != "PASS_A90_H17_UFS_RESIDENT_INSTALLED"
        or value.get("run_id") != RUN_ID
        or value.get("manifest_sha256") != MANIFEST_SHA256
        or value.get("device_safety_state") != "RESIDENT_HEALTHY"
        or value.get("candidate_transfer_count") != 1
        or value.get("rollback_transfer_count") != 0
        or value.get("candidate_replay") is not False
        or value.get("rootfs_payload_count") != 0
        or value.get("sd_stage_count") != 0
        or value.get("userdata_write_count") != 0
    ):
        raise ContractError("H17 install terminal changed")


def _load_qualification(closure: dict[str, Any]) -> dict[str, Any]:
    path = REPO_ROOT / QUALIFICATION_REL
    report = REPO_ROOT / REVIEW_REPORT_REL
    if (
        path.is_symlink()
        or report.is_symlink()
        or not stat.S_ISREG(path.stat().st_mode)
        or not stat.S_ISREG(report.stat().st_mode)
    ):
        raise ContractError("native-fallback qualification files are not regular")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or value.get("schema") != QUALIFICATION_SCHEMA
        or value.get("capability") != CAPABILITY
        or value.get("verdict") != "PASS_GO"
        or value.get("execution_closure_sha256") != closure["sha256"]
        or value.get("execution_hashes") != closure["files"]
        or value.get("incident_run_id") != RUN_ID
        or value.get("predecessor_execution_closure_sha256")
        != PREDECESSOR_EXECUTION_SHA256
        or value.get("diagnosis_sha256") != DIAGNOSIS_SHA256
        or value.get("review_scope")
        != "exact-h17-run01-native-fallback-read-only-no-replay-close"
        or value.get("new_hazard_or_incident") is not True
        or value.get("read_only_approval_required") is not True
        or value.get("review_report") != REVIEW_REPORT_REL
        or value.get("review_report_sha256") != f1.sha256_file(report)
        or value.get("live_authority") is not False
    ):
        raise ContractError("native-fallback qualification is not current")
    return value


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _canonicalize_exact_writer_temp(path: Path, info: os.stat_result) -> os.stat_result:
    if info.st_nlink == 1:
        return info
    if info.st_nlink != 2:
        raise ContractError("H17 incident journal link count changed")
    prefix = f".{path.name}.tmp-"
    aliases: list[Path] = []
    for entry in path.parent.iterdir():
        if not entry.name.startswith(prefix):
            continue
        candidate = entry.lstat()
        if (
            not entry.is_symlink()
            and stat.S_ISREG(candidate.st_mode)
            and candidate.st_dev == info.st_dev
            and candidate.st_ino == info.st_ino
            and candidate.st_mode == info.st_mode
            and candidate.st_size == info.st_size
            and candidate.st_nlink == 2
        ):
            aliases.append(entry)
    if len(aliases) != 1:
        raise ContractError("H17 incident journal hardlink is not the exact writer temp")
    aliases[0].unlink()
    _fsync_directory(path.parent)
    current = path.lstat()
    if (
        current.st_dev != info.st_dev
        or current.st_ino != info.st_ino
        or current.st_mode != info.st_mode
        or current.st_size != info.st_size
        or current.st_nlink != 1
    ):
        raise ContractError("H17 incident journal changed during temp retirement")
    return current


def _read_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, name in enumerate(JOURNAL_NAMES):
        path = EXPECTED_TRANSACTION_DIR / name
        if not os.path.lexists(path):
            if any(
                os.path.lexists(EXPECTED_TRANSACTION_DIR / later)
                for later in JOURNAL_NAMES[index + 1 :]
            ):
                raise ContractError("H17 incident journal has a gap")
            break
        info = _canonicalize_exact_writer_temp(path, path.lstat())
        if (
            path.is_symlink()
            or not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
            or info.st_size <= 0
            or info.st_size > JOURNAL_MAX_BYTES
        ):
            raise ContractError("H17 incident journal file shape changed")
        if index < len(PREFIX_SHA256) and f1.sha256_file(path) != PREFIX_SHA256[index]:
            raise ContractError("H17 incident prefix changed")
        value = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or value.get("schema") != "a90-h17-ufs-d1-journal-v1"
            or value.get("sequence") != index
            or value.get("action") != JOURNAL_ACTIONS[index]
        ):
            raise ContractError("H17 incident journal record changed")
        records.append(value)
    if len(records) not in (5, 6, 7):
        raise ContractError("H17 incident journal is not a closable exact prefix")
    pending = records[4].get("result")
    if (
        not isinstance(pending, dict)
        or pending.get("status") != "NO_PROOF_A90_H17_PERSISTENT_SERVER_LIVE"
        or pending.get("intent_sha256") != INTENT_SHA256
        or pending.get("device_safety_state")
        != "HEALTH_PENDING_PERSISTENT_DEBIAN"
        or pending.get("resident_healthy") is not False
        or pending.get("ordinal_closed") is not False
        or pending.get("candidate_replay") is not False
        or pending.get("arm_dispatch_count") != 1
        or pending.get("reboot_dispatch_count") != 1
        or records[4].get("result_sha256") != f1.json_sha256(pending)
    ):
        raise ContractError("H17 incident pending result changed")
    return records


def _build_spec(manifest: dict[str, Any]) -> Any:
    target = manifest["target"]
    stage = SimpleNamespace(
        bridge_device=target["bridge_device"],
        bridge_realpath=target["bridge_realpath"],
    )
    return SimpleNamespace(
        stage=stage,
        candidate_version=f1.CANDIDATE_VERSION,
        candidate_build=f1.CANDIDATE_BUILD,
    )


def _approval_binding(
    closure: dict[str, Any],
    *,
    created_utc: str,
    expires_utc: str,
) -> dict[str, Any]:
    return {
        "schema": APPROVAL_BINDING_SCHEMA,
        "workflow": CAPABILITY,
        "authority_mode": "trial-retired-fresh-read-only-approval-required",
        "run_id": RUN_ID,
        "transaction_dir": str(EXPECTED_TRANSACTION_DIR),
        "manifest_sha256": MANIFEST_SHA256,
        "install_result_sha256": INSTALL_RESULT_SHA256,
        "predecessor_execution_closure_sha256": PREDECESSOR_EXECUTION_SHA256,
        "finalizer_execution_closure_sha256": closure["sha256"],
        "diagnosis_sha256": DIAGNOSIS_SHA256,
        "intent_sha256": INTENT_SHA256,
        "prefix_sha256": list(PREFIX_SHA256),
        "agents_contract_sha256": f1.sha256_file(REPO_ROOT / "AGENTS.md"),
        "target_profile": "galaxy-a90-5g-native-init",
        "bridge_device": f1.EXACT_BRIDGE_DEVICE,
        "read_only_commands": [
            ["version"],
            ["selftest"],
            ["status"],
            ["auto-handoff-status"],
            ["logcat"],
        ],
        "same_intent_script_sha256": hashlib.sha256(
            _same_intent_script().encode("utf-8")
        ).hexdigest(),
        "userdata_unmounted_script_sha256": hashlib.sha256(
            _unmounted_script().encode("utf-8")
        ).hexdigest(),
        "device_contact": "bounded-read-only",
        "device_effect": False,
        "arm_count": 0,
        "reboot_count": 0,
        "handoff_count": 0,
        "mount_count": 0,
        "service_control_count": 0,
        "payload_transfer_count": 0,
        "partition_write_count": 0,
        "userdata_write_count": 0,
        "candidate_replay": False,
        "operator_attendance_required": True,
        "duration_sec": APPROVAL_TTL_SEC,
        "created_utc": created_utc,
        "expires_utc": expires_utc,
    }


def prepare_approval(args: argparse.Namespace) -> dict[str, Any]:
    _, _, _, closure = _load_static_inputs(args)
    created = dt.datetime.now(dt.UTC).replace(microsecond=0)
    expires = created + dt.timedelta(seconds=APPROVAL_TTL_SEC)
    binding = _approval_binding(
        closure,
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
    f1.write_json_exclusive(APPROVAL_PATH, value)
    return value


def _validate_approval(args: argparse.Namespace, closure: dict[str, Any]) -> dict[str, Any]:
    info = APPROVAL_PATH.lstat()
    if (
        APPROVAL_PATH.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
    ):
        raise ContractError("native-fallback approval is not a private regular file")
    value = json.loads(APPROVAL_PATH.read_text(encoding="utf-8"))
    binding = value.get("approval_binding") if isinstance(value, dict) else None
    if not isinstance(binding, dict):
        raise ContractError("native-fallback approval binding is absent")
    expected = _approval_binding(
        closure,
        created_utc=str(binding.get("created_utc") or ""),
        expires_utc=str(binding.get("expires_utc") or ""),
    )
    binding_sha = f1.json_sha256(binding)
    created = f1.parse_utc(binding.get("created_utc"), "approval created_utc")
    expires = f1.parse_utc(binding.get("expires_utc"), "approval expires_utc")
    now = dt.datetime.now(dt.UTC)
    if (
        value.get("schema") != APPROVAL_SCHEMA
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
        raise ContractError("native-fallback approval is not fresh and exact")
    return value


def _parse_status(record: dict[str, Any]) -> dict[str, Any]:
    exact = base.require_exact_f1_command_receipt(
        record, ["auto-handoff-status"], "H17 native-fallback state"
    )
    lines = [
        line.strip()
        for line in str(exact.get("text") or "").replace("\r", "").splitlines()
        if line.strip().startswith("A90AUTO_STATUS")
    ]
    match = STATUS_RE.fullmatch(lines[0]) if len(lines) == 1 else None
    if match is None:
        raise ContractError("H17 native-fallback state is not unique")
    value = {
        "binding": int(match.group("binding")),
        "enable": int(match.group("enable")),
        "latch": int(match.group("latch")),
        "build": match.group("build"),
    }
    if value != {
        "binding": 1,
        "enable": 1,
        "latch": 1,
        "build": f1.CANDIDATE_BUILD,
    }:
        raise ContractError("H17 native-fallback state is not exact 1,1")
    return value


def _expected_h17_state(intent_sha256: str, state: str) -> bytes:
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
            'echo "A90H17_INTENT_BINDING intent=$EINT enable_sha256=$ES '
            'latch_sha256=$LS evidence_sha256=$RS"',
        )
    )


def _require_same_intent(effect_args: argparse.Namespace) -> dict[str, Any]:
    script = _same_intent_script()
    command = ["run", "/bin/busybox", "sh", "-c", script]
    record = base.run_f1_cmd(effect_args, command)

    return _parse_same_intent_record(record)


def _parse_same_intent_record(record: dict[str, Any]) -> dict[str, Any]:
    script = _same_intent_script()
    command = ["run", "/bin/busybox", "sh", "-c", script]
    exact = base.require_exact_f1_command_receipt(
        record, command, "H17 native-fallback same-intent binding"
    )
    lines = [
        line.strip()
        for line in str(exact.get("text") or "").replace("\r", "").splitlines()
        if line.strip().startswith("A90H17_INTENT_BINDING ")
    ]
    pattern = re.compile(
        r"^A90H17_INTENT_BINDING intent=(?P<intent>[0-9a-f]{64}) "
        r"enable_sha256=(?P<enable>[0-9a-f]{64}) "
        r"latch_sha256=(?P<latch>[0-9a-f]{64}) "
        r"evidence_sha256=(?P<evidence>[0-9a-f]{64})$"
    )
    match = pattern.fullmatch(lines[0]) if len(lines) == 1 else None
    expected = {
        "intent": INTENT_SHA256,
        "enable": hashlib.sha256(
            _expected_h17_state(INTENT_SHA256, "armed-after-native-health")
        ).hexdigest(),
        "latch": hashlib.sha256(
            _expected_h17_state(
                INTENT_SHA256, "automatic-handoff-dispatched-no-replay"
            )
        ).hexdigest(),
        "evidence": hashlib.sha256((INTENT_SHA256 + "\n").encode("ascii")).hexdigest(),
    }
    if match is None or match.groupdict() != expected:
        raise ContractError("H17 enable/latch/evidence intent binding changed")
    return {"proof": True, **expected, "userdata_write_count": 0, "record": record}


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
            'echo "A90H17_NATIVE_FALLBACK devt=$MAJ:$MIN '
            'ufs_mount_count=$C userdata_write=0"',
        )
    )


def _prove_userdata_unmounted(effect_args: argparse.Namespace) -> dict[str, Any]:
    script = _unmounted_script()
    command = ["run", "/bin/busybox", "sh", "-c", script]
    record = base.run_f1_cmd(effect_args, command)

    return _parse_unmounted_record(record)


def _parse_unmounted_record(record: dict[str, Any]) -> dict[str, Any]:
    script = _unmounted_script()
    command = ["run", "/bin/busybox", "sh", "-c", script]
    exact = base.require_exact_f1_command_receipt(
        record, command, "H17 native-fallback unmounted userdata"
    )
    lines = [
        line.strip()
        for line in str(exact.get("text") or "").replace("\r", "").splitlines()
        if line.strip().startswith("A90H17_NATIVE_FALLBACK ")
    ]
    match = UNMOUNTED_RE.fullmatch(lines[0]) if len(lines) == 1 else None
    if match is None or int(match.group("major")) <= 0 or int(match.group("count")) != 0:
        raise ContractError("H17 userdata is not the exact unmounted identity")
    device = f"{int(match.group('major'))}:{int(match.group('minor'))}"
    return {
        "proof": True,
        "device": device,
        "identity": "sole-PARTNAME-userdata-DEVNAME-sda33-runtime-devt",
        "mount_count": 0,
        "userdata_write_count": 0,
        "command_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "record": record,
    }


def _fallback_proof(log_record: dict[str, Any]) -> dict[str, Any]:
    exact = base.require_exact_f1_command_receipt(
        log_record, ["logcat"], "H17 native-fallback durable log"
    )
    text = str(exact.get("text") or "").replace("\r", "")
    boot_marker = f"detail={H17_BOOT_DETAIL}"
    boot_starts = [match.start() for match in re.finditer(re.escape(boot_marker), text)]
    if not boot_starts:
        raise ContractError("H17 native-fallback boot marker is absent")
    selected_boot = boot_starts[-1]
    segment = text[selected_boot:]
    runs = benchmark.parse_runs([segment])
    exact_run = (
        len(runs) == 1
        and tuple(record.get("stage") for record in runs[0].get("records", []))
        == FAILED_HANDOFF_STAGES
    )
    pre_boot_required = (
        f"auto-handoff: armed after native health intent_sha256={INTENT_SHA256}",
        f"auto-handoff: armed reboot dispatch intent_sha256={INTENT_SHA256}",
    )
    post_boot_required = (
        f"ondev-evidence: run published intent_sha256={INTENT_SHA256}",
        "server-distro: D4 handoff failure cleanup_clean=1 root_mounted=0 "
        "recovery_required=0 userdata_unchanged=1 userdata_write=0",
        "auto-handoff: handoff returned no replay rc=-1",
    )
    if (
        not exact_run
        or any(text.count(marker) != 1 for marker in pre_boot_required)
        or any(segment.count(marker) != 1 for marker in post_boot_required)
    ):
        raise ContractError("H17 native-fallback same-intent proof is not unique")
    arm_position, reboot_position = [
        text.index(marker) for marker in pre_boot_required
    ]
    prior_boot = boot_starts[-2] if len(boot_starts) >= 2 else -1
    post_positions = [segment.index(marker) for marker in post_boot_required]
    if (
        not (prior_boot < arm_position < reboot_position < selected_boot)
        or post_positions != sorted(post_positions)
    ):
        raise ContractError("H17 native-fallback same-intent markers are out of order")
    forbidden = (
        "A90H17 observer_auth=ready",
        "A90H17 firstboot_overlay=ready",
        "A90H17 persistent_hud=ready",
        "D4 read-only switch_root exec",
        "stage=switch_root_exec ",
    )
    if any(marker in segment for marker in forbidden):
        raise ContractError("H17 native-fallback contradicts successful handoff")
    selected = runs[0]["records"]
    by_stage = {record["stage"]: record for record in selected}
    return {
        "proof": True,
        "intent_sha256": INTENT_SHA256,
        "stages": list(FAILED_HANDOFF_STAGES),
        "root_mounted": True,
        "writable_set_ready": False,
        "switch_root_exec": False,
        "cleanup_clean": True,
        "recovery_required": False,
        "automatic_native_fallback": True,
        "candidate_replay": False,
        "userdata_write_count": 0,
        "handoff_begin_to_failure_ms": (
            by_stage["handoff_failed_native"]["boottime_ms"]
            - by_stage["handoff_begin"]["boottime_ms"]
        ),
        "root_mounted_to_failure_ms": (
            by_stage["handoff_failed_native"]["boottime_ms"]
            - by_stage["root_mounted"]["boottime_ms"]
        ),
    }


def _validate_native_status(record: dict[str, Any]) -> dict[str, Any]:
    exact = base.require_exact_f1_command_receipt(
        record, ["status"], "H17 native-fallback current status"
    )
    text = str(exact.get("text") or "").replace("\r", "")
    required = (
        f"init: {H17_BOOT_DETAIL}",
        "selftest: pass=11 warn=1 fail=0",
        "pid1guard: pass=12 warn=0 fail=0",
        "autohud: running",
        "transport.ncm=ready",
        "transport.tcpctl=ready",
    )
    if any(text.count(marker) != 1 for marker in required):
        raise ContractError("H17 native-fallback current native health changed")
    return {"proof": True, "required_markers": list(required), "record": record}


def _validate_diagnosis(value: dict[str, Any]) -> dict[str, Any]:
    records = value.get("records")
    if (
        value.get("schema") != "a90-h17-d1-native-readonly-diagnosis-v1"
        or value.get("device_safety_state")
        != "HEALTH_PENDING_PERSISTENT_DEBIAN"
        or value.get("arm_dispatch_count") != 1
        or value.get("reboot_dispatch_count") != 1
        or value.get("candidate_replay") is not False
        or value.get("new_device_effect") is not False
        or not isinstance(records, dict)
        or set(records) != {
            "version",
            "status",
            "selftest",
            "auto-handoff-status",
            "logcat",
        }
    ):
        raise ContractError("H17 private diagnosis changed")
    version = base.require_exact_f1_command_receipt(
        records["version"], ["version"], "diagnosis version"
    )
    selftest = base.require_exact_f1_command_receipt(
        records["selftest"], ["selftest"], "diagnosis selftest"
    )
    if (
        str(version.get("text") or "").count(H17_BOOT_DETAIL) != 1
        or str(selftest.get("text") or "").count(
            "selftest: pass=11 warn=1 fail=0"
        )
        != 1
    ):
        raise ContractError("H17 private diagnosis health changed")
    _validate_native_status(records["status"])
    _parse_status(records["auto-handoff-status"])
    proof = _fallback_proof(records["logcat"])
    return {"proof": True, "sha256": DIAGNOSIS_SHA256, "fallback": proof}


def _validate_terminal(value: Any, closure: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or any(
        not isinstance(value.get(name), dict)
        for name in (
            "read_only_approval_binding",
            "native_health",
            "native_status",
            "auto_handoff_status",
            "auto_handoff_status_record",
            "same_intent_binding",
            "native_fallback_proof",
            "post_fallback_userdata",
            "diagnosis_binding",
            "final_bridge",
            "durable_log_record",
            "original_observation",
        )
    ):
        raise ContractError("H17 native-fallback terminal evidence is absent")
    if not isinstance(value["original_observation"].get("guard_release"), dict):
        raise ContractError("H17 native-fallback original observation changed")
    if (
        value.get("schema") != "a90-h17-ufs-d1-result-v1"
        or value.get("status")
        != "REFUTED_H17_PERSISTENT_SERVER_NATIVE_FALLBACK_HEALTHY"
        or value.get("incident") != "H17_POST_ROOT_MOUNT_NATIVE_FALLBACK"
        or value.get("intent_sha256") != INTENT_SHA256
        or value.get("prior_current_result_sha256")
        != "7a702f27a1f68d082d117e289aaba775e57926e760f6d0359ef2b5e4b07d6b5a"
        or value.get("predecessor_execution_closure_sha256")
        != PREDECESSOR_EXECUTION_SHA256
        or value.get("finalizer_execution_closure_sha256") != closure["sha256"]
        or not isinstance(value.get("read_only_approval_binding_sha256"), str)
        or f1.HEX64_RE.fullmatch(value["read_only_approval_binding_sha256"]) is None
        or value.get("device_safety_state") != "RESIDENT_HEALTHY"
        or value.get("resident_healthy") is not True
        or value.get("ordinal_closed") is not True
        or value.get("inter_effect_health_barrier_satisfied") is not True
        or value.get("new_device_effect_authority") is not False
        or value.get("experiment_proof") != "REFUTED"
        or value.get("automatic_native_fallback") is not True
        or value.get("automatic_native_return") is not False
        or value.get("operator_physical_return") is not False
        or value.get("persistent_debian_reached") is not False
        or value.get("switch_root_exec_proven") is not False
        or value.get("persistent_server_proven") is not False
        or value.get("authenticated_ssh_proven") is not False
        or value.get("debian_pid1_proven") is not False
        or value.get("persistent_hud_proven") is not False
        or value.get("display_visible_proven") is not False
        or value.get("final_wifi_proven") is not False
        or value.get("candidate_replay") is not False
        or value.get("arm_dispatch_count") != 1
        or value.get("reboot_dispatch_count") != 1
        or value.get("handoff_dispatch_count") != 1
        or value.get("physical_return_reboot_dispatch_count") != 0
        or value.get("payload_transfer_count") != 0
        or value.get("partition_write_count") != 0
        or value.get("flash_count") != 0
        or value.get("sd_rootfs_stage_count") != 0
        or value.get("userdata_write_count") != 0
        or value.get("native_health", {}).get("exact_bridge") is not True
        or value.get("native_status", {}).get("proof") is not True
        or value.get("auto_handoff_status")
        != {
            "binding": 1,
            "enable": 1,
            "latch": 1,
            "build": f1.CANDIDATE_BUILD,
        }
        or value.get("same_intent_binding", {}).get("proof") is not True
        or value.get("same_intent_binding", {}).get("intent") != INTENT_SHA256
        or value.get("same_intent_binding", {}).get("userdata_write_count") != 0
        or value.get("native_fallback_proof", {}).get("proof") is not True
        or value.get("native_fallback_proof", {}).get("intent_sha256")
        != INTENT_SHA256
        or value.get("native_fallback_proof", {}).get("root_mounted") is not True
        or value.get("native_fallback_proof", {}).get("writable_set_ready")
        is not False
        or value.get("native_fallback_proof", {}).get("switch_root_exec")
        is not False
        or value.get("native_fallback_proof", {}).get("cleanup_clean") is not True
        or value.get("native_fallback_proof", {}).get("recovery_required")
        is not False
        or value.get("native_fallback_proof", {}).get("candidate_replay") is not False
        or value.get("native_fallback_proof", {}).get("userdata_write_count") != 0
        or value.get("post_fallback_userdata", {}).get("proof") is not True
        or not isinstance(value.get("post_fallback_userdata", {}).get("device"), str)
        or re.fullmatch(
            r"[1-9][0-9]*:[0-9]+",
            value["post_fallback_userdata"]["device"],
        )
        is None
        or value.get("post_fallback_userdata", {}).get("identity")
        != "sole-PARTNAME-userdata-DEVNAME-sda33-runtime-devt"
        or value.get("post_fallback_userdata", {}).get("mount_count") != 0
        or value.get("post_fallback_userdata", {}).get("userdata_write_count") != 0
        or value.get("diagnosis_binding", {}).get("proof") is not True
        or value.get("diagnosis_binding", {}).get("sha256") != DIAGNOSIS_SHA256
        or value.get("diagnosis_binding", {}).get("fallback", {}).get("proof")
        is not True
        or value.get("final_bridge", {}).get("selected_realpath") is None
        or value.get("original_observation", {}).get("proof") is not False
        or value.get("original_observation", {}).get("guard_release", {}).get(
            "released"
        )
        is not True
    ):
        raise ContractError("H17 native-fallback terminal changed")
    native_health = value["native_health"]
    try:
        health_facts = base.staging.validate_native_health_receipts(
            {
                "version": native_health.get("version"),
                "status": native_health.get("status"),
                "selftest": native_health.get("selftest"),
            },
            expected_version=f1.CANDIDATE_VERSION,
            expected_build=f1.CANDIDATE_BUILD,
        )
    except Exception as exc:
        raise ContractError("H17 native-fallback exact health receipts changed") from exc
    if native_health.get("facts") != health_facts:
        raise ContractError("H17 native-fallback exact health facts changed")
    return value


def _deep_validate_terminal(
    value: Any,
    closure: dict[str, Any],
    manifest: dict[str, Any],
    diagnosis_binding: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    result = _validate_terminal(value, closure)

    approval_binding = result["read_only_approval_binding"]
    created = f1.parse_utc(
        approval_binding.get("created_utc"),
        "terminal approval created_utc",
    )
    expires = f1.parse_utc(
        approval_binding.get("expires_utc"),
        "terminal approval expires_utc",
    )
    expected_approval = _approval_binding(
        closure,
        created_utc=str(approval_binding.get("created_utc") or ""),
        expires_utc=str(approval_binding.get("expires_utc") or ""),
    )
    approval_sha = f1.json_sha256(approval_binding)
    if (
        approval_binding != expected_approval
        or expires - created != dt.timedelta(seconds=APPROVAL_TTL_SEC)
        or result["read_only_approval_binding_sha256"] != approval_sha
    ):
        raise ContractError("H17 native-fallback terminal approval changed")

    expected_realpath = manifest.get("target", {}).get("bridge_realpath")
    native_health = result.get("native_health")
    receipt_values = (
        native_health.get("version") if isinstance(native_health, dict) else None,
        native_health.get("selftest") if isinstance(native_health, dict) else None,
        result.get("native_status", {}).get("record"),
        result.get("auto_handoff_status_record"),
        result.get("same_intent_binding", {}).get("record"),
        result.get("durable_log_record"),
        result.get("post_fallback_userdata", {}).get("record"),
    )
    if not isinstance(native_health, dict) or any(
        not isinstance(record, dict) for record in receipt_values
    ):
        raise ContractError("H17 native-fallback terminal health receipt is absent")
    version = base.require_exact_f1_command_receipt(
        receipt_values[0], ["version"], "terminal native version"
    )
    selftest = base.require_exact_f1_command_receipt(
        receipt_values[1], ["selftest"], "terminal native selftest"
    )
    if (
        str(version.get("text") or "").count(H17_BOOT_DETAIL) != 1
        or str(selftest.get("text") or "").count(
            "selftest: pass=11 warn=1 fail=0"
        )
        != 1
        or native_health.get("status") != receipt_values[2]
        or native_health.get("selected_realpath") != expected_realpath
        or result.get("final_bridge", {}).get("selected_realpath")
        != expected_realpath
    ):
        raise ContractError("H17 native-fallback terminal identity changed")

    native_status = _validate_native_status(receipt_values[2])
    auto_status = _parse_status(receipt_values[3])
    same_intent = _parse_same_intent_record(receipt_values[4])
    fallback = _fallback_proof(receipt_values[5])
    unmounted = _parse_unmounted_record(receipt_values[6])
    if (
        native_status != result.get("native_status")
        or auto_status != result.get("auto_handoff_status")
        or same_intent != result.get("same_intent_binding")
        or fallback != result.get("native_fallback_proof")
        or unmounted != result.get("post_fallback_userdata")
        or result.get("diagnosis_binding") != diagnosis_binding
        or result.get("prior_current_result_sha256")
        != records[4].get("result_sha256")
        or result.get("original_observation") != records[3].get("observation")
    ):
        raise ContractError("H17 native-fallback terminal evidence changed")
    return result


def _load_static_inputs(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], Any, list[dict[str, Any]], dict[str, Any]]:
    if args.expect_manifest_sha256 != MANIFEST_SHA256:
        raise ContractError("manifest SHA binding changed")
    if args.expect_install_result_sha256 != INSTALL_RESULT_SHA256:
        raise ContractError("install-result SHA binding changed")
    if args.expect_predecessor_execution_closure_sha256 != PREDECESSOR_EXECUTION_SHA256:
        raise ContractError("predecessor execution closure changed")
    if args.expect_diagnosis_sha256 != DIAGNOSIS_SHA256:
        raise ContractError("diagnosis SHA binding changed")
    if args.manifest.resolve(strict=True) != EXPECTED_MANIFEST_PATH:
        raise ContractError("manifest path changed")
    if args.install_result.resolve(strict=True) != EXPECTED_INSTALL_RESULT_PATH:
        raise ContractError("install-result path changed")
    if args.transaction_dir.resolve(strict=True) != EXPECTED_TRANSACTION_DIR:
        raise ContractError("transaction path changed")
    if args.diagnosis.resolve(strict=True) != EXPECTED_DIAGNOSIS_PATH:
        raise ContractError("diagnosis path changed")
    manifest = _load_json(EXPECTED_MANIFEST_PATH, MANIFEST_SHA256, "manifest")
    install = _load_json(
        EXPECTED_INSTALL_RESULT_PATH, INSTALL_RESULT_SHA256, "install result"
    )
    diagnosis = _load_json(
        EXPECTED_DIAGNOSIS_PATH, DIAGNOSIS_SHA256, "private diagnosis"
    )
    _validate_manifest(manifest)
    _validate_install_result(install)
    diagnosis_binding = _validate_diagnosis(diagnosis)
    records = _read_records()
    closure = execution_closure()
    if args.expect_finalizer_execution_closure_sha256 != closure["sha256"]:
        raise ContractError("native-fallback execution closure changed")
    _load_qualification(closure)
    if len(records) >= 6:
        result = _deep_validate_terminal(
            records[5].get("result"),
            closure,
            manifest,
            diagnosis_binding,
            records,
        )
        if records[5].get("result_sha256") != f1.json_sha256(result):
            raise ContractError("H17 native-fallback final-health hash changed")
    if len(records) == 7 and (
        records[6].get("result") != records[5].get("result")
        or records[6].get("result_sha256") != records[5].get("result_sha256")
    ):
        raise ContractError("H17 native-fallback closed result changed")
    return manifest, diagnosis_binding, records, closure


def _write_record(index: int, action: str, payload: dict[str, Any]) -> None:
    value = {
        "schema": "a90-h17-ufs-d1-journal-v1",
        "sequence": index,
        "action": action,
        **payload,
    }
    f1.write_json_exclusive(EXPECTED_TRANSACTION_DIR / JOURNAL_NAMES[index], value)


def _build_result(
    manifest: dict[str, Any],
    diagnosis_binding: dict[str, Any],
    records: list[dict[str, Any]],
    closure: dict[str, Any],
    approval: dict[str, Any],
) -> dict[str, Any]:
    effect_args = _effect_args()
    spec = _build_spec(manifest)
    native = base.verify_candidate_health(spec, effect_args)
    status_record = base.run_f1_cmd(effect_args, ["status"])
    native_status = _validate_native_status(status_record)
    health_facts = base.staging.validate_native_health_receipts(
        {
            "version": native["version"],
            "status": status_record,
            "selftest": native["selftest"],
        },
        expected_version=f1.CANDIDATE_VERSION,
        expected_build=f1.CANDIDATE_BUILD,
    )
    native["status"] = status_record
    native["facts"] = health_facts
    auto_status_record = base.run_f1_cmd(effect_args, ["auto-handoff-status"])
    auto_status = _parse_status(auto_status_record)
    same_intent = _require_same_intent(effect_args)
    log_record = base.run_f1_cmd(effect_args, ["logcat"])
    fallback = _fallback_proof(log_record)
    unmounted = _prove_userdata_unmounted(effect_args)
    final_bridge = base.staging.require_exact_bridge(spec.stage, effect_args)
    return {
        "schema": "a90-h17-ufs-d1-result-v1",
        "status": "REFUTED_H17_PERSISTENT_SERVER_NATIVE_FALLBACK_HEALTHY",
        "incident": "H17_POST_ROOT_MOUNT_NATIVE_FALLBACK",
        "intent_sha256": INTENT_SHA256,
        "prior_current_result_sha256": records[4]["result_sha256"],
        "predecessor_execution_closure_sha256": PREDECESSOR_EXECUTION_SHA256,
        "finalizer_execution_closure_sha256": closure["sha256"],
        "read_only_approval_binding": approval["approval_binding"],
        "read_only_approval_binding_sha256": approval["approval_binding_sha256"],
        "device_safety_state": "RESIDENT_HEALTHY",
        "resident_healthy": True,
        "ordinal_closed": True,
        "inter_effect_health_barrier_satisfied": True,
        "new_device_effect_authority": False,
        "experiment_proof": "REFUTED",
        "automatic_native_fallback": True,
        "automatic_native_return": False,
        "operator_physical_return": False,
        "persistent_debian_reached": False,
        "switch_root_exec_proven": False,
        "persistent_server_proven": False,
        "authenticated_ssh_proven": False,
        "debian_pid1_proven": False,
        "persistent_hud_proven": False,
        "display_visible_proven": False,
        "final_wifi_proven": False,
        "candidate_replay": False,
        "arm_dispatch_count": 1,
        "reboot_dispatch_count": 1,
        "handoff_dispatch_count": 1,
        "physical_return_reboot_dispatch_count": 0,
        "payload_transfer_count": 0,
        "partition_write_count": 0,
        "flash_count": 0,
        "sd_rootfs_stage_count": 0,
        "userdata_write_count": 0,
        "native_health": native,
        "native_status": native_status,
        "auto_handoff_status": auto_status,
        "auto_handoff_status_record": auto_status_record,
        "same_intent_binding": same_intent,
        "native_fallback_proof": fallback,
        "post_fallback_userdata": unmounted,
        "diagnosis_binding": diagnosis_binding,
        "final_bridge": final_bridge,
        "durable_log_record": log_record,
        "original_observation": records[3]["observation"],
    }


def close(args: argparse.Namespace) -> dict[str, Any]:
    if args.operator_attended is not True:
        raise ContractError("H17 native-fallback close is attended-only")
    manifest, diagnosis, records, closure = _load_static_inputs(args)
    if len(records) == 7:
        return _deep_validate_terminal(
            records[6].get("result"),
            closure,
            manifest,
            diagnosis,
            records,
        )
    if len(records) == 6:
        result = _deep_validate_terminal(
            records[5].get("result"),
            closure,
            manifest,
            diagnosis,
            records,
        )
        result_sha = records[5]["result_sha256"]
        _write_record(6, "closed", {"result_sha256": result_sha, "result": result})
        return result
    if args.approval is None:
        raise ContractError("H17 native-fallback close requires fresh exact approval")
    approval = _validate_approval(args, closure)
    result = _build_result(manifest, diagnosis, records, closure, approval)
    _deep_validate_terminal(result, closure, manifest, diagnosis, records)
    (
        fresh_manifest,
        fresh_diagnosis,
        fresh_records,
        fresh_closure,
    ) = _load_static_inputs(args)
    if (
        fresh_manifest != manifest
        or fresh_diagnosis != diagnosis
        or fresh_records != records
        or fresh_closure != closure
        or len(fresh_records) != 5
    ):
        raise ContractError("native-fallback static inputs changed during reads")
    _deep_validate_terminal(
        result,
        fresh_closure,
        fresh_manifest,
        fresh_diagnosis,
        fresh_records,
    )
    result_sha = f1.json_sha256(result)
    _write_record(5, "final-health", {"result_sha256": result_sha, "result": result})
    _write_record(6, "closed", {"result_sha256": result_sha, "result": result})
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-approval", action="store_true")
    mode.add_argument("--close", action="store_true")
    result.add_argument("--manifest", type=Path, required=True)
    result.add_argument("--expect-manifest-sha256", required=True)
    result.add_argument("--install-result", type=Path, required=True)
    result.add_argument("--expect-install-result-sha256", required=True)
    result.add_argument("--expect-predecessor-execution-closure-sha256", required=True)
    result.add_argument("--diagnosis", type=Path, required=True)
    result.add_argument("--expect-diagnosis-sha256", required=True)
    result.add_argument("--transaction-dir", type=Path, required=True)
    result.add_argument("--expect-finalizer-execution-closure-sha256", required=True)
    result.add_argument("--operator-attended", action="store_true")
    result.add_argument("--approval")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.prepare_approval:
            if args.approval is not None or args.operator_attended:
                raise ContractError("approval preparation accepts no live inputs")
            value = prepare_approval(args)
        else:
            value = close(args)
    except (
        ContractError,
        f1.ContractError,
        base.ContractError,
        benchmark.BenchmarkError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(
            f"H17_NATIVE_FALLBACK_FINALIZER_ERROR {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
