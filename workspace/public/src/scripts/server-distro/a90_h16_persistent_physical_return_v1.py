#!/usr/bin/env python3
"""Close the exact H16 persistent-Debian run after an attended physical return.

This incident finalizer never arms, reboots, hands off, mounts, transfers, or
writes the device.  It validates the consumed run01 prefix, reads current H16
health and the current native log, proves userdata unmounted, and appends only
the two original D1 terminal journal records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_boot_benchmark_v1 as benchmark  # noqa: E402
import a90_h16_ufs_d1_runner_v1 as d1  # noqa: E402
import a90_h16_ufs_f1_runner_v1 as f1  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402


QUALIFICATION_SCHEMA = "a90-h16-physical-return-qualification-v1"
CAPABILITY = "A90_H16_PERSISTENT_DEBIAN_PHYSICAL_RETURN_V1"
RUN_ID = "a90-h16-ufs-f1-20260810-03"
MANIFEST_SHA256 = (
    "7af8e74e43417644d60e086e60ecb5952908ccfae0936a4ebf02a2e5455f0f55"
)
INSTALL_RESULT_SHA256 = (
    "ca5ed12bd01daf1c26a78e9e5f9cc65c3b24c562e11517131c869168dab79333"
)
PREDECESSOR_EXECUTION_SHA256 = (
    "2931949198a27821e1d7d5bb4046cc17de52f64527c8546e6b2b2454990d3f62"
)
INTENT_SHA256 = (
    "6103bef66403754b0ba8c0401dbb0c94b2238de0213b06b4802a67285a51d290"
)
EXPECTED_USERDATA_DEVT = (259, 17)
PRIVATE_RUN_BASE = (REPO_ROOT / "workspace/private/runs/server-distro").resolve()
EXPECTED_MANIFEST_PATH = (PRIVATE_RUN_BASE / RUN_ID / "manifest.json").resolve()
EXPECTED_INSTALL_RESULT_PATH = (
    PRIVATE_RUN_BASE / RUN_ID / "h16-f1-live" / "result.json"
).resolve()
EXPECTED_TRANSACTION_DIR = (
    PRIVATE_RUN_BASE / RUN_ID / "h16-d1" / "run01"
).resolve()
QUALIFICATION_REL = (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h16/physical-return-qualification.json"
)
REVIEW_REPORT_REL = (
    "docs/reports/"
    "A90_H16_PERSISTENT_PHYSICAL_RETURN_INDEPENDENT_REVIEW_2026-08-10.json"
)
INCIDENT_REPORT_REL = (
    "docs/reports/"
    "A90_H16_PERSISTENT_DEBIAN_RETURN_OBSERVER_INCIDENT_2026-08-10.md"
)
TARGET_CONTRACT_REL = "docs/operations/targets/A90_TARGET_CONTRACT.md"
ADAPTER_REL = (
    "workspace/public/src/scripts/server-distro/"
    "a90_h16_persistent_physical_return_v1.py"
)
JOURNAL_MAX_BYTES = 16 * 1024 * 1024
EXECUTION_RELS = tuple(
    sorted(set(f1.EXECUTION_SOURCE_RELS) | {INCIDENT_REPORT_REL, ADAPTER_REL})
)
H16_UFS_STAGES = (
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
    "writable_set_ready",
    "distro_init_verified",
    "display_marker_ready",
    "mount_moves_done",
    "switch_root_exec",
)
RETURN_STAGES = (
    "native_runtime_ready",
    "auto_handoff_check",
    "auto_handoff_latched_native",
)
UNMOUNTED_RE = re.compile(
    r"^A90H16_POST_PHYSICAL_RETURN devt=(?P<major>[0-9]+):"
    r"(?P<minor>[0-9]+) ufs_mount_count=(?P<count>[0-9]+) "
    r"userdata_write=0$"
)


class ContractError(RuntimeError):
    """Raised before widening, replaying, or overstating this incident close."""


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
            raise ContractError(f"physical-return source is not regular: {relative}")
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


def _load_qualification(closure: dict[str, Any]) -> dict[str, Any]:
    path = REPO_ROOT / QUALIFICATION_REL
    report = REPO_ROOT / REVIEW_REPORT_REL
    if (
        path.is_symlink()
        or report.is_symlink()
        or not stat.S_ISREG(path.stat().st_mode)
        or not stat.S_ISREG(report.stat().st_mode)
    ):
        raise ContractError("physical-return qualification files are not regular")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "schema",
            "capability",
            "verdict",
            "execution_closure_sha256",
            "execution_hashes",
            "incident_run_id",
            "predecessor_execution_closure_sha256",
            "review_scope",
            "new_hazard_or_incident",
            "review_report",
            "review_report_sha256",
            "live_authority",
        }
        or value.get("schema") != QUALIFICATION_SCHEMA
        or value.get("capability") != CAPABILITY
        or value.get("verdict") != "PASS_GO"
        or value.get("execution_closure_sha256") != closure["sha256"]
        or value.get("execution_hashes") != closure["files"]
        or value.get("incident_run_id") != RUN_ID
        or value.get("predecessor_execution_closure_sha256")
        != PREDECESSOR_EXECUTION_SHA256
        or value.get("review_scope")
        != "exact-h16-run01-persistent-debian-physical-return-no-replay-close"
        or value.get("new_hazard_or_incident") is not True
        or value.get("review_report") != REVIEW_REPORT_REL
        or value.get("review_report_sha256") != f1.sha256_file(report)
        or value.get("live_authority") is not False
    ):
        raise ContractError("physical-return qualification is not current")
    return value


def _validate_manifest(value: dict[str, Any]) -> None:
    candidate = value.get("candidate_boot")
    target = value.get("target")
    authority = value.get("authority")
    if (
        value.get("schema") != f1.SCHEMA
        or value.get("run_id") != RUN_ID
        or value.get("status") != "ready-for-attended-f1"
        or value.get("execution_closure", {}).get("sha256")
        != PREDECESSOR_EXECUTION_SHA256
        or not isinstance(candidate, dict)
        or candidate.get("expected_version") != f1.CANDIDATE_VERSION
        or candidate.get("expected_build") != f1.CANDIDATE_BUILD
        or candidate.get("sha256")
        != "d545082ed6fd5dcab6c050f1f6b0b6ffa8c7cdb8783a1cb262eec428e1451b88"
        or not isinstance(target, dict)
        or target.get("profile") != "galaxy-a90-5g-native-init"
        or target.get("bridge_device") != f1.EXACT_BRIDGE_DEVICE
        or not isinstance(authority, dict)
        or authority.get("candidate_replay") is not False
        or authority.get("rootfs_payload_count") != 0
        or authority.get("sd_stage_count") != 0
        or authority.get("userdata_write_count") != 0
    ):
        raise ContractError("H16 incident manifest binding changed")


def _validate_install_result(value: dict[str, Any]) -> None:
    if (
        value.get("schema") != f1.RESULT_SCHEMA
        or value.get("status") != "PASS_A90_H16_UFS_RESIDENT_INSTALLED"
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
        raise ContractError("H16 install terminal changed")


def _incident_args(manifest: Path, install_result: Path) -> argparse.Namespace:
    return argparse.Namespace(
        manifest=manifest,
        expect_manifest_sha256=MANIFEST_SHA256,
        install_result=install_result,
        expect_install_result_sha256=INSTALL_RESULT_SHA256,
        expect_execution_closure_sha256=PREDECESSOR_EXECUTION_SHA256,
        transaction_dir=EXPECTED_TRANSACTION_DIR,
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _canonicalize_exact_writer_temp(
    path: Path,
    info: os.stat_result,
) -> os.stat_result:
    if info.st_nlink == 1:
        return info
    if info.st_nlink != 2:
        raise ContractError("H16 incident journal link count changed")
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
        raise ContractError("H16 incident journal hardlink is not the exact writer temp")
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
        raise ContractError("H16 incident journal changed during temp retirement")
    return current


def _read_records() -> list[dict[str, Any]]:
    for index, name in enumerate(d1.JOURNAL_NAMES):
        path = EXPECTED_TRANSACTION_DIR / name
        if not os.path.lexists(path):
            if any(
                os.path.lexists(EXPECTED_TRANSACTION_DIR / later)
                for later in d1.JOURNAL_NAMES[index + 1 :]
            ):
                raise ContractError("H16 incident journal has a gap")
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
            raise ContractError("H16 incident journal file shape changed")
    return d1._read_records(EXPECTED_TRANSACTION_DIR)  # noqa: SLF001


def _validate_result(value: Any, closure: dict[str, Any]) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or value.get("schema") != d1.RESULT_SCHEMA
        or value.get("terminal")
        != "NO_PROOF_H16_PERSISTENT_DEBIAN_PHYSICAL_RETURN_HEALTHY"
        or value.get("incident")
        != "PERSISTENT_DEBIAN_RETURN_AND_OBSERVER_BINDING_MISMATCH"
        or value.get("intent_sha256") != INTENT_SHA256
        or value.get("physical_return_execution_closure_sha256")
        != closure["sha256"]
        or value.get("resident_healthy") is not True
        or value.get("operator_physical_return") is not True
        or value.get("automatic_native_return") is not False
        or value.get("switch_root_exec_proven") is not True
        or value.get("persistent_server_proven") is not False
        or value.get("authenticated_ssh_proven") is not False
        or value.get("debian_pid1_proven") is not False
        or value.get("drm_master_proven") is not False
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
        or value.get("auto_handoff_status", {}).get("binding") != 1
        or value.get("auto_handoff_status", {}).get("enable") != 1
        or value.get("auto_handoff_status", {}).get("latch") != 1
        or value.get("handoff_benchmark", {}).get("proof") is not True
        or value.get("handoff_benchmark", {}).get("switch_root_exec") is not True
        or value.get("post_physical_return_userdata", {}).get("proof") is not True
        or value.get("post_physical_return_userdata", {}).get("device") != "259:17"
        or value.get("post_physical_return_userdata", {}).get("mount_count") != 0
        or value.get("post_physical_return_userdata", {}).get("userdata_write_count")
        != 0
        or value.get("original_observation", {}).get("proof") is not False
        or value.get("original_observation", {}).get("guard_release", {}).get("released")
        is not True
    ):
        raise ContractError("H16 physical-return terminal changed")
    return value


def _load_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], Any, list[dict[str, Any]], dict[str, Any]]:
    if args.expect_manifest_sha256 != MANIFEST_SHA256:
        raise ContractError("manifest SHA binding changed")
    if args.expect_install_result_sha256 != INSTALL_RESULT_SHA256:
        raise ContractError("install-result SHA binding changed")
    if args.expect_predecessor_execution_closure_sha256 != PREDECESSOR_EXECUTION_SHA256:
        raise ContractError("predecessor execution closure changed")
    manifest_path = _require_regular(args.manifest, MANIFEST_SHA256, "manifest")
    install_path = _require_regular(
        args.install_result, INSTALL_RESULT_SHA256, "install result"
    )
    if manifest_path != EXPECTED_MANIFEST_PATH:
        raise ContractError("manifest path changed")
    if install_path != EXPECTED_INSTALL_RESULT_PATH:
        raise ContractError("install-result path changed")
    transaction = args.transaction_dir.absolute().resolve(strict=True)
    if transaction != EXPECTED_TRANSACTION_DIR:
        raise ContractError("H16 incident transaction directory changed")
    manifest = _load_json(manifest_path, MANIFEST_SHA256, "manifest")
    install = _load_json(install_path, INSTALL_RESULT_SHA256, "install result")
    _validate_manifest(manifest)
    _validate_install_result(install)
    records = _read_records()
    if len(records) not in (4, 5, 6):
        raise ContractError("H16 incident journal is not a closable no-replay prefix")
    intent = d1._validate_records(  # noqa: SLF001
        records,
        EXPECTED_TRANSACTION_DIR,
        _incident_args(manifest_path, install_path),
        manifest,
    )
    observation = records[3].get("observation")
    if (
        intent != INTENT_SHA256
        or records[2].get("arm_reboot_command_dispatch_count") != 1
        or records[2].get("candidate_replay") is not False
        or not isinstance(observation, dict)
        or observation.get("proof") is not False
        or observation.get("observer_error")
        != {
            "type": "ContractError",
            "message": "bound A90 NCM did not appear at a new USB epoch before deadline",
        }
        or observation.get("guard_release", {}).get("released") is not True
    ):
        raise ContractError("H16 consumed incident prefix changed")
    closure = execution_closure()
    if args.expect_physical_return_execution_closure_sha256 != closure["sha256"]:
        raise ContractError("physical-return execution closure changed")
    _load_qualification(closure)
    if len(records) >= 5:
        result = _validate_result(records[4].get("result"), closure)
        if records[4].get("result_sha256") != f1.json_sha256(result):
            raise ContractError("H16 final-health result hash changed")
    if len(records) == 6 and (
        records[5].get("result") != records[4].get("result")
        or records[5].get("result_sha256") != records[4].get("result_sha256")
    ):
        raise ContractError("H16 closed result changed")
    spec = f1._spec(manifest, manifest_path, MANIFEST_SHA256)  # noqa: SLF001
    spec.bridge_realpath = spec.stage.bridge_realpath
    return manifest, spec, records, closure


def _benchmark_proof(log_record: dict[str, Any], intent_sha256: str) -> dict[str, Any]:
    exact = base.require_exact_f1_command_receipt(
        log_record, ["logcat"], "H16 physical-return durable log"
    )
    text = str(exact.get("text") or "").replace("\r", "")
    runs = benchmark.parse_runs([text])
    stage_lists = [
        tuple(record.get("stage") for record in run.get("records", []))
        for run in runs
    ]
    matches = [index for index, stages in enumerate(stage_lists) if stages == H16_UFS_STAGES]
    returned = [index for index, stages in enumerate(stage_lists) if stages == RETURN_STAGES]
    required_markers = (
        f"auto-handoff: armed after native health intent_sha256={intent_sha256}",
        f"auto-handoff: armed reboot dispatch intent_sha256={intent_sha256}",
        f"ondev-evidence: run published intent_sha256={intent_sha256}",
        "server-distro: D4 read-only switch_root exec "
        "source=/dev/block/a90-userdata "
        "root=/mnt/sdext/a90/runtime/distro-root writable_set=4 "
        "evidence_bound=1 wifi_handoff_bound=1",
    )
    if len(matches) != 1 or len(returned) != 1:
        raise ContractError("H16 handoff and physical-return benchmark segments are not unique")
    if any(text.count(marker) != 1 for marker in required_markers):
        raise ContractError("H16 same-intent handoff markers are not exact")
    marker_positions = [text.index(marker) for marker in required_markers]
    if marker_positions != sorted(marker_positions):
        raise ContractError("H16 same-intent handoff markers are out of order")
    selected = runs[matches[0]]["records"]
    by_stage = {record["stage"]: record for record in selected}
    return {
        "proof": True,
        "intent_sha256": intent_sha256,
        "handoff_segment_index": matches[0],
        "physical_return_segment_index": returned[0],
        "handoff_stages": list(H16_UFS_STAGES),
        "physical_return_stages": list(RETURN_STAGES),
        "boot_to_switch_root_ms": by_stage["switch_root_exec"]["boottime_ms"],
        "handoff_begin_to_switch_root_ms": (
            by_stage["switch_root_exec"]["boottime_ms"]
            - by_stage["handoff_begin"]["boottime_ms"]
        ),
        "same_intent_markers": True,
        "switch_root_exec": True,
    }


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
            'echo "A90H16_POST_PHYSICAL_RETURN devt=$MAJ:$MIN '
            'ufs_mount_count=$C userdata_write=0"',
        )
    )


def _prove_userdata_unmounted(effect_args: argparse.Namespace) -> dict[str, Any]:
    script = _unmounted_script()
    command = ["run", "/bin/busybox", "sh", "-c", script]
    record = base.run_f1_cmd(effect_args, command)
    exact = base.require_exact_f1_command_receipt(
        record, command, "H16 post-physical-return unmounted userdata"
    )
    lines = [
        line.strip()
        for line in str(exact.get("text") or "").replace("\r", "").splitlines()
        if line.strip().startswith("A90H16_POST_PHYSICAL_RETURN ")
    ]
    if len(lines) != 1:
        raise ContractError("H16 unmounted-userdata marker is not unique")
    match = UNMOUNTED_RE.fullmatch(lines[0])
    if (
        match is None
        or (int(match.group("major")), int(match.group("minor")))
        != EXPECTED_USERDATA_DEVT
        or int(match.group("count")) != 0
    ):
        raise ContractError("H16 userdata is not the exact unmounted identity")
    return {
        "proof": True,
        "device": f"{EXPECTED_USERDATA_DEVT[0]}:{EXPECTED_USERDATA_DEVT[1]}",
        "mount_count": 0,
        "userdata_write_count": 0,
        "command_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "record": record,
    }


def _build_result(
    spec: Any,
    records: list[dict[str, Any]],
    closure: dict[str, Any],
) -> dict[str, Any]:
    effect_args = _effect_args()
    base.staging.require_exact_bridge(spec.stage, effect_args)
    status_record, status = d1.require_status(effect_args, enable=1, latch=1)
    native = base.verify_candidate_health(spec, effect_args)
    log_record = base.run_f1_cmd(effect_args, ["logcat"])
    handoff = _benchmark_proof(log_record, INTENT_SHA256)
    unmounted = _prove_userdata_unmounted(effect_args)
    return {
        "schema": d1.RESULT_SCHEMA,
        "terminal": "NO_PROOF_H16_PERSISTENT_DEBIAN_PHYSICAL_RETURN_HEALTHY",
        "incident": "PERSISTENT_DEBIAN_RETURN_AND_OBSERVER_BINDING_MISMATCH",
        "intent_sha256": INTENT_SHA256,
        "physical_return_execution_closure_sha256": closure["sha256"],
        "resident_healthy": True,
        "operator_physical_return": True,
        "automatic_native_return": False,
        "switch_root_exec_proven": True,
        "persistent_server_proven": False,
        "authenticated_ssh_proven": False,
        "debian_pid1_proven": False,
        "drm_master_proven": False,
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
        "auto_handoff_status": status,
        "auto_handoff_status_record": status_record,
        "native_health": native,
        "handoff_benchmark": handoff,
        "post_physical_return_userdata": unmounted,
        "original_observation": records[3]["observation"],
        "durable_log_record": log_record,
    }


def close(args: argparse.Namespace) -> dict[str, Any]:
    if args.operator_attended is not True or args.physical_return_confirmed is not True:
        raise ContractError("H16 physical-return close requires attended confirmation")
    _, spec, records, closure = _load_inputs(args)
    if len(records) == 6:
        return _validate_result(records[5].get("result"), closure)
    if len(records) == 5:
        result = _validate_result(records[4].get("result"), closure)
        result_sha = records[4]["result_sha256"]
        d1._write_record(  # noqa: SLF001
            EXPECTED_TRANSACTION_DIR,
            5,
            "closed",
            {"result_sha256": result_sha, "result": result},
        )
        return result
    result = _build_result(spec, records, closure)
    result_sha = f1.json_sha256(result)
    d1._write_record(  # noqa: SLF001
        EXPECTED_TRANSACTION_DIR,
        4,
        "final-health",
        {"result_sha256": result_sha, "result": result},
    )
    d1._write_record(  # noqa: SLF001
        EXPECTED_TRANSACTION_DIR,
        5,
        "closed",
        {"result_sha256": result_sha, "result": result},
    )
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--manifest", type=Path, required=True)
    result.add_argument("--expect-manifest-sha256", required=True)
    result.add_argument("--install-result", type=Path, required=True)
    result.add_argument("--expect-install-result-sha256", required=True)
    result.add_argument("--expect-predecessor-execution-closure-sha256", required=True)
    result.add_argument("--expect-physical-return-execution-closure-sha256", required=True)
    result.add_argument("--transaction-dir", type=Path, required=True)
    result.add_argument("--close", action="store_true", required=True)
    result.add_argument("--operator-attended", action="store_true")
    result.add_argument("--physical-return-confirmed", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        value = close(args)
    except (
        ContractError,
        d1.ContractError,
        f1.ContractError,
        benchmark.BenchmarkError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(
            f"H16_PHYSICAL_RETURN_ERROR {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
