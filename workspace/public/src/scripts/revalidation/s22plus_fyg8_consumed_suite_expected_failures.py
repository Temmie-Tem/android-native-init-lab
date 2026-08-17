#!/usr/bin/env python3
"""Account for every failing test in a consumed-campaign discovery set.

The raw-first observer boundary rewrote active S22+ observer sources.  Consumed
P3.18 machinery pins the pre-migration bytes of those sources on purpose, so a
fixed number of its tests now fail by design.  Recording that number in a commit
message is not enough: the next reader sees "188/209" and cannot tell a designed
reject from a new regression, so a real break hides inside the expected set.

This auditor freezes the expected set by exact test identity and reason.  It
fails closed in both directions.  An unexpected failure is a regression.  An
expected failure that starts passing means the pin was refreshed and the entry
must be removed, so the set can never quietly outlive its cause.

Host-only.  No target contact, no device authority, no live authority.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import unittest
from typing import Any


SCHEMA = "s22plus_fyg8_consumed_suite_expected_failures_v1"
VERDICT = "PASS_S22PLUS_FYG8_CONSUMED_SUITE_FULLY_ACCOUNTED_H0"
ROOT = Path(__file__).resolve().parents[5]
TESTS = ROOT / "tests"
DEFAULT_PATTERN = "*p318*"
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "consumed-suite-expected-failures-20260817-01.json"
)

CONSUMED_D1_ROTATION = (
    "consumed P3.18 D1 rotation adapter pins the pre-migration D0 runtime "
    "identity; the campaign closed 2026-08-16T07:24:34Z and cannot be replayed"
)
CONSUMED_F1_FINALIZER = (
    "consumed P3.18 post-rollback finalizer and its close audit pin the "
    "pre-migration D0 adapter identity; the campaign closed and cannot be "
    "replayed"
)
SUPERSEDED_STOP_VERSION = (
    "documentation pins D0_STOP_VERSION v1; the raw-first migration "
    "deliberately bumped the stop-receipt version to v2"
)
SUPERSEDED_QEMU_CONTROL = (
    "P3.18 QEMU control preserved the pre-migration observer bytes; the "
    "migrated common observer needs a fresh control run, which is blocked in "
    "this environment"
)

# Exact test identities.  Every entry states why the reject is designed.
EXPECTED_FAILURES: dict[str, str] = {
    "test_s22plus_fyg8_p318_baseline_rotation_d1.P318BaselineRotationD1Test"
    ".test_adb_execution_snapshot_is_exact_no_replace_and_executable": CONSUMED_D1_ROTATION,
    "test_s22plus_fyg8_p318_baseline_rotation_d1.P318BaselineRotationD1Test"
    ".test_binding_manifest_adapter_mutation_is_rejected": CONSUMED_D1_ROTATION,
    "test_s22plus_fyg8_p318_baseline_rotation_d1.P318BaselineRotationD1Test"
    ".test_binding_manifest_requires_exact_types_shape_and_finite_json": CONSUMED_D1_ROTATION,
    "test_s22plus_fyg8_p318_baseline_rotation_d1.P318BaselineRotationD1Test"
    ".test_fixture_runs_one_reboot_without_device_contact": CONSUMED_D1_ROTATION,
    "test_s22plus_fyg8_p318_baseline_rotation_d1.P318BaselineRotationD1Test"
    ".test_health_snapshot_topology_must_match_selection": CONSUMED_D1_ROTATION,
    "test_s22plus_fyg8_p318_baseline_rotation_d1.P318BaselineRotationD1Test"
    ".test_live_transport_allows_ephemeral_transport_id_rotation": CONSUMED_D1_ROTATION,
    "test_s22plus_fyg8_p318_baseline_rotation_d1.P318BaselineRotationD1Test"
    ".test_pass_go_manifest_still_rejects_wrong_approval_and_caller_adb": CONSUMED_D1_ROTATION,
    "test_s22plus_fyg8_p318_baseline_rotation_d1.P318BaselineRotationD1Test"
    ".test_pending_review_rejects_live_before_run_directory_or_device": CONSUMED_D1_ROTATION,
    "test_s22plus_fyg8_p318_baseline_rotation_d1.P318BaselineRotationD1Test"
    ".test_pinned_inputs_are_exact_and_historical_topology_is_not_authority": CONSUMED_D1_ROTATION,
    "test_s22plus_fyg8_p318_baseline_rotation_d1.P318BaselineRotationD1Test"
    ".test_verified_d0_runtime_ignores_ambient_local_module_injection": CONSUMED_D1_ROTATION,
    "test_s22plus_fyg8_p318_baseline_rotation_d1.P318BaselineRotationD1Test"
    ".test_wrong_serial_and_multiple_s22_candidates_fail_before_topology_read": CONSUMED_D1_ROTATION,
    "test_s22plus_fyg8_p318_baseline_rotation_d1_docs.P318BaselineRotationD1DocsTest"
    ".test_binding_manifest_self_binds_adapter_and_records_review": CONSUMED_D1_ROTATION,
    "test_s22plus_fyg8_p318_postrollback_finalize.P318PostrollbackFinalizeTest"
    ".test_authority_binds_reviewed_private_adb_not_system_path": CONSUMED_F1_FINALIZER,
    "test_s22plus_fyg8_p318_postrollback_finalize.P318PostrollbackFinalizeTest"
    ".test_authority_is_exact_deterministic_regeneration": CONSUMED_F1_FINALIZER,
    "test_s22plus_fyg8_p318_postrollback_finalize.P318PostrollbackFinalizeTest"
    ".test_consumed_generic_plan_exposes_the_known_closed_correlation_gap": CONSUMED_F1_FINALIZER,
    "test_s22plus_fyg8_p318_postrollback_finalize.P318PostrollbackFinalizeTest"
    ".test_live_rejects_unbound_adb_before_incident_reopen": CONSUMED_F1_FINALIZER,
    "test_s22plus_fyg8_p318_docs.P318DocumentationTest"
    ".test_postrollback_close_audit_private_receipt_is_exact_and_host_only": CONSUMED_F1_FINALIZER,
    "setUpClass (test_s22plus_fyg8_p318_postrollback_close_audit"
    ".P318PostrollbackCloseAuditTest)": CONSUMED_F1_FINALIZER,
    "test_s22plus_fyg8_p318_d0_stop_receipt_docs.P318D0StopReceiptDocsTest"
    ".test_adapter_exposes_distinct_success_and_stop_schemas": SUPERSEDED_STOP_VERSION,
    "setUpClass (test_s22plus_fyg8_p318_cdc_acm_qemu_e2e"
    ".P318CdcAcmQemuE2ETest)": SUPERSEDED_QEMU_CONTROL,
}


class ExpectedFailureError(RuntimeError):
    pass


def _identity(test: Any) -> str:
    # A subTest reports its parameters inside its own id, so one flaky
    # parameter would silently need its own manifest entry.  Collapse to the
    # owning test method; an _ErrorHolder has no test_case and keeps its
    # "setUpClass (module.Class)" identity.
    parent = getattr(test, "test_case", None)
    if parent is not None:
        return parent.id()
    try:
        return test.id()
    except AttributeError:
        return str(test)


def discover_failures(
    pattern: str = DEFAULT_PATTERN, tests: Path = TESTS
) -> dict[str, str]:
    """Run one discovery set in-process and return failing identity -> kind."""

    if not tests.is_dir():
        raise ExpectedFailureError("tests directory is absent")
    loader = unittest.TestLoader()
    suite = loader.discover(str(tests), pattern=pattern, top_level_dir=str(tests))
    result = unittest.TestResult()
    # Some suites print operator prompts; keep them out of the receipt stream.
    with open(os.devnull, "w", encoding="ascii") as sink:
        with contextlib.redirect_stdout(sink):
            suite.run(result)
    observed: dict[str, str] = {}
    for test, _ in result.failures:
        observed[_identity(test)] = "failure"
    for test, _ in result.errors:
        observed[_identity(test)] = "error"
    if result.testsRun < 1:
        raise ExpectedFailureError("discovery set is empty")
    return {
        "observed": observed,
        "tests_run": result.testsRun,
    }


def audit(
    pattern: str = DEFAULT_PATTERN, tests: Path = TESTS
) -> dict[str, Any]:
    run = discover_failures(pattern, tests)
    observed = run["observed"]
    expected = set(EXPECTED_FAILURES)
    unexpected = sorted(set(observed) - expected)
    if unexpected:
        raise ExpectedFailureError(
            "unaccounted test failure is a regression: " + ", ".join(unexpected)
        )
    repaired = sorted(expected - set(observed))
    if repaired:
        raise ExpectedFailureError(
            "expected failure now passes and must leave the manifest: "
            + ", ".join(repaired)
        )
    reasons: dict[str, int] = {}
    for reason in EXPECTED_FAILURES.values():
        reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "pattern": pattern,
        "tests_run": run["tests_run"],
        "expected_failures": len(expected),
        "accounted_tests": run["tests_run"],
        "unaccounted_failures": 0,
        "stale_manifest_entries": 0,
        "failures_by_reason": reasons,
        "expected_failure_identities": sorted(expected),
        "manifest_sha256": hashlib.sha256(
            json.dumps(
                EXPECTED_FAILURES,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
        ).hexdigest(),
        "device_contact": False,
        "live_authorized": False,
    }


def encode_receipt(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def write_receipt(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        metadata = path.stat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_nlink != 1
        ):
            raise ExpectedFailureError("receipt path identity differs")
        if path.read_bytes() != payload:
            raise ExpectedFailureError("receipt would change existing bytes")
        return
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o400
    )
    try:
        os.write(descriptor, payload)
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args(argv)
    value = audit(arguments.pattern)
    payload = encode_receipt(value)
    if arguments.output is not None:
        write_receipt(arguments.output, payload)
    sys.stdout.write(payload.decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
