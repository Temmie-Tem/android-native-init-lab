#!/usr/bin/env python3
"""One-shot reconciliation for the A90 H27 pre-transfer EFBIG incident.

This is deliberately not a general recovery or retry interface.  It accepts no
caller-selected run, artifact, log, command, target, or outcome.  The fixed
incident journal and complete helper logs must prove that neither helper
reached adb push or any boot write/readback phase.  A fresh exact H24 health
observation is then published before the two fixed host guards are released.
"""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
from typing import Any

import a90_boot_only_f1_adapter_v1 as adapter
import a90_boot_only_f1_minimal_v1 as owner


SCHEMA = "a90-h27-pretransfer-abort-reconciliation-v1"
DECISION = "PRETRANSFER_ABORTED_NO_BOOT_WRITE"
RUN_ID = "a90-h27-f1-20260820-01"
MANIFEST_PATH = (
    owner.REPO_ROOT / "workspace/private/manifests/a90-h27-f1-20260820-01.json"
)
MANIFEST_SHA256 = "572fda0e714c9eb12dbf092fc85f6b199eb574a69e2e62e5822e2a8b9ff332c7"
HISTORICAL_REVIEW_PATH = (
    owner.REPO_ROOT
    / "docs/archive/reviews/A90_BOOT_ONLY_F1_MINIMAL_REVIEW_02a627cf_2026-08-20.json"
)
HISTORICAL_REVIEW_SHA256 = (
    "02a627cf1f361a8fec69d77f1fee17493ee5968567b740bca0f195e4b8bd145a"
)
HISTORICAL_REVIEW_SIZE = 1_159
CURRENT_REVIEW_PATH = (
    owner.REPO_ROOT
    / "docs/reports/A90_BOOT_ONLY_F1_MINIMAL_ACTIVATED_INDEPENDENT_REVIEW_2026-08-20.json"
)
CANDIDATE_RECEIPT_SHA256 = (
    "976bed166d41ff9efd801ee45e4ee46609737c4d5c2995d399f46628d32b8dba"
)
ROLLBACK_RECEIPT_SHA256 = (
    "6eb6ea2690fbff31823a8ba92760141899db89cf374e9cc343a71508e6e89b6e"
)
INCIDENT_RECORD_SHA256 = {
    "00-prepared.json": "9d1f7279be202b1a67112f68a862f6ac1907e1e5bb2fbfd8597f6e8d0ccf8a29",
    "10-approved.json": "40a4b8f17f1fbd9b28053a2bb2627e362a6086c30e6db29cee4320f67ebec71a",
    "20-candidate-intent.json": "5ef1bc4a85ed7af0611c231faf7b54d95cc9b95a1f439fdeb707aeee3ac1016f",
    "21-candidate-launched.json": "2c020e1261ac1164d289c0ece5653a968f70f224c7640226ae7f2ab5b343d251",
    "22-candidate-result.json": "09394b631df6d58c2c908794075200c6246106c5730cf0bfe847e415411204a8",
    "30-rollback-intent.json": "673054926c6db676439d58a1bf633f50c9afe6ee35eff47fe52eabf500c0e99c",
    "31-rollback-launched.json": "dd7e63fc673296e30b9aad3348f25e52b54abfb1324c3f0776e4bb9076003a2f",
    "32-rollback-result.json": "5cd2c2bb656949ba52ce75e9474909c16cd6f51726c101ae412089dd42e9d4d0",
    "40-terminal.json": "1fc94fbfcb25a6640c3d9db7bcfb2d04dde3355f915c151c93f5200a208fe31a",
}
EXECUTE_LOG_DIRECTORY = owner.RUN_ROOT / f"{RUN_ID}-execute-1-logs"
CANDIDATE_STDOUT = EXECUTE_LOG_DIRECTORY / "009-flash-candidate.stdout"
CANDIDATE_STDERR = EXECUTE_LOG_DIRECTORY / "009-flash-candidate.stderr"
ROLLBACK_STDOUT = EXECUTE_LOG_DIRECTORY / "011-flash-rollback.stdout"
ROLLBACK_STDERR = EXECUTE_LOG_DIRECTORY / "011-flash-rollback.stderr"
MAX_DURATION_MS = 600_000
ELAPSED = r"[0-9]+\.[0-9]{3}"


def _require_direct_private_directory(path: Path, label: str) -> None:
    metadata = path.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_gid != os.getgid()
        or metadata.st_mode & 0o077
    ):
        raise owner.ContractError(f"{label} is not direct and private")


def _load_incident_manifest() -> tuple[bytes, dict[str, Any]]:
    raw = owner._read_bounded_regular(
        MANIFEST_PATH, "fixed incident manifest", owner.MAX_JSON_BYTES
    )
    if owner.sha256_bytes(raw) != MANIFEST_SHA256:
        raise owner.ContractError("fixed incident manifest bytes changed")
    manifest = owner.validate_manifest(
        owner.parse_canonical(raw, "fixed incident manifest")
    )
    if manifest["runId"] != RUN_ID:
        raise owner.ContractError("fixed incident manifest run ID changed")
    return raw, manifest


def _verify_review_lineage(
    manifest: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    historical = owner._read_bounded_regular(
        HISTORICAL_REVIEW_PATH,
        "historical qualification review",
        owner.MAX_JSON_BYTES,
    )
    historical_binding = manifest["qualification"]["review"]
    if (
        len(historical) != HISTORICAL_REVIEW_SIZE
        or owner.sha256_bytes(historical) != HISTORICAL_REVIEW_SHA256
        or historical_binding["size"] != HISTORICAL_REVIEW_SIZE
        or historical_binding["sha256"] != HISTORICAL_REVIEW_SHA256
    ):
        raise owner.ContractError("historical qualification review is not exact")
    owner.parse_canonical(historical, "historical qualification review")

    current = owner._read_bounded_regular(
        CURRENT_REVIEW_PATH,
        "current qualification review",
        owner.MAX_JSON_BYTES,
    )
    current_sha256 = owner.sha256_bytes(current)
    rebound = dict(manifest)
    qualification = dict(manifest["qualification"])
    qualification["review"] = {
        "path": str(CURRENT_REVIEW_PATH),
        "size": len(current),
        "sha256": current_sha256,
    }
    rebound["qualification"] = qualification
    owner._verify_qualification_inputs(rebound)
    return rebound, current_sha256


class CurrentReviewLease:
    """Hold the exact current PASS_GO bytes across both guard removals."""

    def __init__(self, manifest: dict[str, Any], expected_sha256: str) -> None:
        self.path = CURRENT_REVIEW_PATH
        self.before = self.path.lstat()
        if (
            not stat.S_ISREG(self.before.st_mode)
            or self.before.st_nlink != 1
            or self.before.st_uid != os.getuid()
            or self.before.st_gid != os.getgid()
            or self.before.st_mode & 0o022
            or not 1 <= self.before.st_size <= owner.MAX_JSON_BYTES
        ):
            raise owner.ContractError("current review lease path is invalid")
        self.descriptor = os.open(
            self.path,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        )
        try:
            current = os.fstat(self.descriptor)
            if (
                not stat.S_ISREG(current.st_mode)
                or (current.st_dev, current.st_ino)
                != (self.before.st_dev, self.before.st_ino)
                or current.st_size != self.before.st_size
            ):
                raise owner.ContractError("current review lease identity changed")
            self.raw = os.pread(self.descriptor, current.st_size, 0)
            self.sha256 = owner.sha256_bytes(self.raw)
            if len(self.raw) != current.st_size or self.sha256 != expected_sha256:
                raise owner.ContractError("current review lease bytes changed")
            rebound = dict(manifest)
            qualification = dict(manifest["qualification"])
            qualification["review"] = {
                "path": str(self.path),
                "size": len(self.raw),
                "sha256": self.sha256,
            }
            rebound["qualification"] = qualification
            owner._validate_qualification_review(
                owner.parse_canonical(self.raw, "current review lease"), rebound
            )
        except BaseException:
            os.close(self.descriptor)
            raise

    def check(self) -> None:
        current = os.fstat(self.descriptor)
        pathname = self.path.lstat()
        if (
            (current.st_dev, current.st_ino, current.st_size)
            != (self.before.st_dev, self.before.st_ino, self.before.st_size)
            or (pathname.st_dev, pathname.st_ino, pathname.st_size)
            != (self.before.st_dev, self.before.st_ino, self.before.st_size)
            or owner.sha256_bytes(os.pread(self.descriptor, current.st_size, 0))
            != self.sha256
        ):
            raise owner.ContractError("current review lease drifted during cleanup")

    def close(self) -> None:
        os.close(self.descriptor)


def _read_log(path: Path, label: str) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise owner.ContractError(f"{label} cannot be inspected") from exc
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_uid != os.getuid()
        or before.st_gid != os.getgid()
        or before.st_mode & 0o022
        or not 0 <= before.st_size <= adapter.MAX_OUTPUT_BYTES
    ):
        raise owner.ContractError(f"{label} path identity mismatch")
    descriptor = os.open(
        path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    )
    try:
        current = os.fstat(descriptor)
        if (
            not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino)
            or current.st_size != before.st_size
        ):
            raise owner.ContractError(f"{label} changed before read")
        raw = os.pread(descriptor, current.st_size, 0)
        if len(raw) != current.st_size or os.pread(descriptor, 1, current.st_size):
            raise owner.ContractError(f"{label} changed during read")
        return raw
    finally:
        os.close(descriptor)


def bind_effect_receipt(
    *,
    expected_sha256: str,
    argv: tuple[str, ...],
    returncode: int,
    quiescent: bool,
    stdout: bytes,
    stderr: bytes,
    maximum_duration_ms: int,
) -> int:
    """Recover the sole duration whose canonical receipt matches the journal."""
    owner._sha(expected_sha256, "effect receipt")
    if type(maximum_duration_ms) is not int or maximum_duration_ms < 0:
        raise owner.ContractError("receipt duration bound is invalid")
    fixed = {
        "argv": list(argv),
        "returncode": returncode,
        "quiescent": quiescent,
        "stdoutSha256": owner.sha256_bytes(stdout),
        "stderrSha256": owner.sha256_bytes(stderr),
    }
    matches: list[int] = []
    for duration_ms in range(maximum_duration_ms + 1):
        receipt = dict(fixed)
        receipt["durationMs"] = duration_ms
        if owner.sha256_bytes(owner.canonical_json(receipt)) == expected_sha256:
            matches.append(duration_ms)
            if len(matches) > 1:
                break
    if len(matches) != 1:
        raise owner.ContractError("effect logs do not have one bound receipt duration")
    return matches[0]


def _require_line(text: str, pattern: str, label: str) -> None:
    if len(re.findall(pattern, text, flags=re.MULTILINE)) != 1:
        raise owner.ContractError(f"{label} is absent or non-unique")


def validate_pretransfer_logs(
    *, candidate_stderr: bytes, rollback_stderr: bytes, manifest: dict[str, Any]
) -> None:
    try:
        candidate = candidate_stderr.decode("utf-8")
        rollback = rollback_stderr.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise owner.ContractError("fixed helper stderr is not UTF-8") from exc

    candidate_artifact = manifest["candidate"]
    rollback_artifact = manifest["rollback"]
    for text, artifact, role in (
        (candidate, candidate_artifact, "candidate"),
        (rollback, rollback_artifact, "rollback"),
    ):
        _require_line(
            text,
            rf"^\[native-init-flash [0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}\] "
            rf"local image size: {artifact['size']}$",
            f"{role} local size",
        )
        _require_line(
            text,
            rf"^\[native-init-flash [0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}\] "
            rf"local image sha256: {artifact['sha256']}$",
            f"{role} local SHA256",
        )
        _require_line(
            text,
            rf"phase\.native_init_flash\.inspect_local_image\.elapsed_sec={ELAPSED} ok=1$",
            f"{role} local inspection",
        )
        _require_line(
            text,
            rf"phase\.native_init_flash\.total\.elapsed_sec={ELAPSED} ok=0$",
            f"{role} failed total",
        )

    _require_line(candidate, r"error: \[Errno 27\] File too large$", "candidate EFBIG")
    _require_line(
        candidate,
        rf"phase\.native_init_flash\.native_to_recovery\.elapsed_sec={ELAPSED} ok=1$",
        "candidate recovery request",
    )
    _require_line(
        candidate,
        rf"phase\.native_init_flash\.wait_recovery_adb\.elapsed_sec={ELAPSED} ok=1$",
        "candidate recovery arrival",
    )
    _require_line(
        rollback,
        r"error: ADB baseline already contains a recovery endpoint$",
        "rollback pre-transfer refusal",
    )

    forbidden = (
        "sealed local image copy:",
        "phase.native_init_flash.adb_push.",
        "phase.native_init_flash.remote_sha256.",
        "phase.native_init_flash.flash_boot_image.",
        "phase.native_init_flash.boot_dd_write.",
        "phase.native_init_flash.boot_readback_sha256.",
        "remote image sha256:",
        "boot block prefix sha256:",
        "requesting system boot through TWRP",
    )
    for token in forbidden:
        if token in candidate or token in rollback:
            raise owner.ContractError(f"pre-transfer log contains forbidden stage {token}")
    for token in (
        "requesting recovery from native init bridge",
        "phase.native_init_flash.native_to_recovery.",
        "phase.native_init_flash.wait_recovery_adb.",
    ):
        if token in rollback:
            raise owner.ContractError("rollback advanced beyond its bound baseline refusal")


def _require_incident_records(
    records: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
    manifest_sha256: str,
) -> None:
    if tuple(records) not in (owner.ROLLBACK_PATH, owner.PRETRANSFER_ABORT_PATH):
        raise owner.ContractError("incident journal is not the exact rollback terminal")
    if any(
        record.get("manifestSha256") != manifest_sha256
        for record in records.values()
    ):
        raise owner.ContractError("incident journal does not bind the fixed manifest")
    _require_fixed_record_hashes(records)
    terminal = records["40-terminal.json"]["payload"]
    if (
        terminal.get("schema") != owner.RESULT_SCHEMA
        or terminal.get("terminal") != "RECOVERY_REQUIRED"
        or terminal.get("reason") != "ROLLBACK_HEALTH_UNPROVED"
        or terminal.get("candidateReplay") is not False
    ):
        raise owner.ContractError("incident terminal is not exact")
    for name, expected_receipt in (
        ("22-candidate-result.json", CANDIDATE_RECEIPT_SHA256),
        ("32-rollback-result.json", ROLLBACK_RECEIPT_SHA256),
    ):
        payload = records[name]["payload"]
        if payload != {
            "returncode": 1,
            "completed": False,
            "quiescent": True,
            "receiptSha256": expected_receipt,
        }:
            raise owner.ContractError(f"{name} is not the fixed failed result")
    if records["20-candidate-intent.json"]["payload"] != {
        "sha256": manifest["candidate"]["sha256"]
    } or records["30-rollback-intent.json"]["payload"] != {
        "sha256": manifest["rollback"]["sha256"]
    }:
        raise owner.ContractError("incident intent artifacts changed")


def _require_fixed_record_hashes(records: dict[str, dict[str, Any]]) -> None:
    if set(INCIDENT_RECORD_SHA256) != set(owner.ROLLBACK_PATH):
        raise owner.ContractError("fixed incident record inventory is invalid")
    for name, expected in INCIDENT_RECORD_SHA256.items():
        record = records.get(name)
        if (
            type(record) is not dict
            or owner.sha256_bytes(owner.canonical_json(record)) != expected
        ):
            raise owner.ContractError(f"fixed incident record changed: {name}")


def _validate_reconciliation_payload(
    payload: dict[str, Any], current_review_sha256: str
) -> None:
    required = {
        "schema",
        "decision",
        "candidateRetryPermitted",
        "currentReviewSha256",
        "candidate",
        "rollback",
        "recoveredSnapshot",
    }
    if type(payload) is not dict or set(payload) != required:
        raise owner.ContractError("pre-transfer reconciliation fields mismatch")
    if (
        payload["schema"] != SCHEMA
        or payload["decision"] != DECISION
        or payload["candidateRetryPermitted"] is not True
        or payload["currentReviewSha256"] != current_review_sha256
    ):
        raise owner.ContractError("pre-transfer reconciliation decision is invalid")
    for role, receipt in (
        ("candidate", CANDIDATE_RECEIPT_SHA256),
        ("rollback", ROLLBACK_RECEIPT_SHA256),
    ):
        item = payload[role]
        if (
            type(item) is not dict
            or set(item)
            != {"receiptSha256", "durationMs", "transferStarted", "bootWriteStarted"}
            or item["receiptSha256"] != receipt
            or type(item["durationMs"]) is not int
            or item["durationMs"] < 0
            or item["durationMs"] > MAX_DURATION_MS
            or item["transferStarted"] is not False
            or item["bootWriteStarted"] is not False
        ):
            raise owner.ContractError(f"{role} reconciliation is invalid")
    snapshot = payload["recoveredSnapshot"]
    if (
        type(snapshot) is not dict
        or set(snapshot)
        != {
            "targetEvidenceSha256",
            "bootId",
            "version",
            "build",
            "healthy",
            "recoveryAvailable",
            "recoveryEvidenceSha256",
            "freshStateAbsent",
            "otherTargetsUntouched",
            "receiptSha256",
        }
    ):
        raise owner.ContractError("recovered H24 snapshot fields mismatch")
    recovered = owner.Snapshot(
        target_evidence_sha256=snapshot["targetEvidenceSha256"],
        boot_id=snapshot["bootId"],
        version=snapshot["version"],
        build=snapshot["build"],
        healthy=snapshot["healthy"],
        recovery_available=snapshot["recoveryAvailable"],
        recovery_evidence_sha256=snapshot["recoveryEvidenceSha256"],
        fresh_state_absent=snapshot["freshStateAbsent"],
        other_targets_untouched=snapshot["otherTargetsUntouched"],
        receipt_sha256=snapshot["receiptSha256"],
    )
    recovered.validate()
    if (
        re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", recovered.boot_id)
        is None
        or recovered.healthy is not True
        or recovered.recovery_available is not True
        or recovered.recovery_evidence_sha256 != current_review_sha256
        or recovered.fresh_state_absent is not True
        or recovered.other_targets_untouched is not True
        or recovered.version != "0.11.192"
        or recovered.build
        != "phase3-minimal-h24-ufs-auth-native-hud-private-card-root-minimal-debian-dev"
    ):
        raise owner.ContractError("recovered H24 snapshot is not exact")


def _release_guard_if_present(path: Path, expected: bytes, label: str) -> None:
    try:
        path.lstat()
    except FileNotFoundError:
        return
    actual = owner._verify_input(
        {"path": str(path), "size": len(expected), "sha256": owner.sha256_bytes(expected)},
        label,
    )
    if actual != expected:
        raise owner.ContractError(f"{label} identity mismatch")
    os.unlink(path)
    owner._fsync_directory(owner.RUN_ROOT)


def _cleanup_guards_with_review_lease(
    manifest: dict[str, Any], payload: dict[str, Any]
) -> None:
    lease = CurrentReviewLease(manifest, payload["currentReviewSha256"])
    try:
        active_path, active_expected = owner._active_guard(manifest)
        candidate_path, candidate_expected = owner._candidate_guard(manifest)
        lease.check()
        _release_guard_if_present(active_path, active_expected, "active run guard")
        lease.check()
        _release_guard_if_present(candidate_path, candidate_expected, "candidate guard")
        lease.check()
    finally:
        lease.close()


def reconcile() -> dict[str, Any]:
    raw, manifest = _load_incident_manifest()
    current_manifest, current_review_sha256 = _verify_review_lineage(manifest)
    owner.ensure_run_root()
    run_directory = owner.RUN_ROOT / RUN_ID
    owner._require_run_path(run_directory, RUN_ID)
    _require_direct_private_directory(EXECUTE_LOG_DIRECTORY, "fixed execute log directory")
    records = owner.read_records(run_directory)
    _require_incident_records(records, manifest, owner.sha256_bytes(raw))

    if "41-pretransfer-abort.json" not in records:
        owner._require_active_guard(manifest)
        owner._require_candidate_guard(manifest)
        candidate_stdout = _read_log(CANDIDATE_STDOUT, "candidate stdout")
        candidate_stderr = _read_log(CANDIDATE_STDERR, "candidate stderr")
        rollback_stdout = _read_log(ROLLBACK_STDOUT, "rollback stdout")
        rollback_stderr = _read_log(ROLLBACK_STDERR, "rollback stderr")
        serial_sha = manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"]
        candidate_duration = bind_effect_receipt(
            expected_sha256=CANDIDATE_RECEIPT_SHA256,
            argv=adapter.fixed_flash_argv(
                manifest["candidate"],
                recovery_serial_sha256=serial_sha,
                timeout_sec=manifest["timeouts"]["flashSec"],
            ),
            returncode=1,
            quiescent=True,
            stdout=candidate_stdout,
            stderr=candidate_stderr,
            maximum_duration_ms=MAX_DURATION_MS,
        )
        rollback_duration = bind_effect_receipt(
            expected_sha256=ROLLBACK_RECEIPT_SHA256,
            argv=adapter.fixed_flash_argv(
                manifest["rollback"],
                recovery_serial_sha256=serial_sha,
                timeout_sec=manifest["timeouts"]["flashSec"],
            ),
            returncode=1,
            quiescent=True,
            stdout=rollback_stdout,
            stderr=rollback_stderr,
            maximum_duration_ms=MAX_DURATION_MS,
        )
        validate_pretransfer_logs(
            candidate_stderr=candidate_stderr,
            rollback_stderr=rollback_stderr,
            manifest=manifest,
        )
        backend = owner._live_backend(
            current_manifest, "reconcile-pretransfer-abort"
        )
        recovered = backend.preflight(current_manifest)
        owner._require_start(recovered, current_manifest)
        payload = {
            "schema": SCHEMA,
            "decision": DECISION,
            "candidateRetryPermitted": True,
            "currentReviewSha256": current_review_sha256,
            "candidate": {
                "receiptSha256": CANDIDATE_RECEIPT_SHA256,
                "durationMs": candidate_duration,
                "transferStarted": False,
                "bootWriteStarted": False,
            },
            "rollback": {
                "receiptSha256": ROLLBACK_RECEIPT_SHA256,
                "durationMs": rollback_duration,
                "transferStarted": False,
                "bootWriteStarted": False,
            },
            "recoveredSnapshot": recovered.payload(),
        }
        _validate_reconciliation_payload(payload, current_review_sha256)
        owner.publish_record(
            run_directory,
            "41-pretransfer-abort.json",
            owner._record("PRETRANSFER_ABORT_RECONCILED", owner.sha256_bytes(raw), payload),
        )
    else:
        payload = records["41-pretransfer-abort.json"]["payload"]
        _validate_reconciliation_payload(payload, current_review_sha256)

    _cleanup_guards_with_review_lease(manifest, payload)
    return payload


def main() -> int:
    payload = reconcile()
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except owner.ContractError as exc:
        print(f"A90_H27_PRETRANSFER_ABORT_RECONCILE_V1 NO_GO: {exc}", file=os.sys.stderr)
        raise SystemExit(2) from exc
