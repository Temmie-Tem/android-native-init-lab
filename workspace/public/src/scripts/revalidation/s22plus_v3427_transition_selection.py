#!/usr/bin/env python3
"""Host-only V3427 phase-observer transition selection and classifier.

The selected transition is attended manual RDX/Download entry followed by the
first boot-only rollback boot. This module validates only host artifacts and
historical reports. It does not contact a device, create a candidate, flash,
reboot, or authorize live work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import s22plus_v3426_phase_observer_design as observer


SCHEMA = "s22plus_v3427_transition_selection_v1"
TARGET = observer.TARGET
OBSERVER_CONTRACT_SHA256 = observer.CONTRACT_SHA256
MAX_LAST_KMSG_BYTES = 2_097_136

MAGISK_ROLLBACK_AP = Path(
    "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
)
MAGISK_ROLLBACK_AP_SHA256 = (
    "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56"
)
MAGISK_ROLLBACK_BOOT_SHA256 = (
    "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
)
STOCK_ROLLBACK_AP = Path(
    "workspace/private/outputs/s22plus_native_init/"
    "odin4_stock_rollback_fyg8_raw_repacked_20260709/AP.tar.md5"
)
STOCK_ROLLBACK_AP_SHA256 = (
    "2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94"
)
STOCK_ROLLBACK_BOOT_SHA256 = (
    "4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae"
)
ODIN4 = Path("/usr/bin/odin4")

HISTORICAL_REPORTS = {
    Path("docs/reports/S22PLUS_NATIVE_INIT_M4T0_LIVE_RESULT_2026-07-07.md"): {
        "sha256": "c655b6b4bc90e1cf6e74dcf881ed30773f6363326a921c2c13dd0aab86170adb",
        "tokens": (
            "manual download-mode recovery: Odin device appeared",
            "Magisk boot-only rollback Odin rc=0",
            "/proc/last_kmsg bytes: 2097136",
        ),
    },
    Path(
        "docs/reports/NATIVE_INIT_V3414_S22PLUS_O3_MINIMAL_ACM_LIVE_MISS_2026-07-10.md"
    ): {
        "sha256": "b9253e57674f61de8e53b5dd9d2a1c02c2c7559fcf7dd745be394f6649aea297",
        "tokens": (
            "the operator entered Download",
            "rollback_rc=0",
            "android_restored=true",
        ),
    },
    Path(
        "docs/reports/NATIVE_INIT_V3417_S22PLUS_O3F_FREESTANDING_ACM_LIVE_MISS_2026-07-10.md"
    ): {
        "sha256": "87b268a38972cf791c4a85b9c0efe8d70d2aeccafca89148fdc0b30a93c5442b",
        "tokens": (
            "operator manually entered Download mode",
            "rollback_rc=0",
            "last_kmsg_bytes=2097136",
        ),
    },
    Path(
        "docs/reports/S22PLUS_M29_FIRST_ROLLBACK_CAPTURE_LIVE_RESULT_2026-07-09.md"
    ): {
        "sha256": "ed151e43bcb431680034cc4590d470ba70bc405cb3f2e66bb0863b9b29e9dba4",
        "tokens": (
            "manually entered Download mode",
            "last_kmsg_bytes=2097136",
            "android_reboot_download_count=1",
            "It retained an Android reboot/download boot",
        ),
    },
    Path(
        "docs/reports/NATIVE_INIT_V3420_S22PLUS_O3R1_NATIVE_RETAINED_SYSRQ_LIVE_NO_PROOF_2026-07-10.md"
    ): {
        "sha256": "537fcb6e09bb6ed4e6e499549c007f305558d663a7cb728b1b73149363c258f8",
        "tokens": (
            "rollback_entry=attended-manual",
            "rollback_flash_rc=0",
            "last_kmsg_bytes=2097136",
        ),
    },
}

TRANSITION_CORE: dict[str, Any] = {
    "schema": SCHEMA,
    "target": TARGET,
    "observer_contract_sha256": OBSERVER_CONTRACT_SHA256,
    "selection": {
        "name": "attended-manual-rdx-download-first-rollback-boot-capture",
        "candidate_terminal_state": "quiet_park_after_internal_final_readback",
        "post_final_userspace_log_writes": False,
        "kernel_background_log_volume": "UNVERIFIABLE_BOUNDED_BY_90_SECONDS",
        "host_pretransition_stage_a_signal": False,
        "operator_entry": "manual_rdx_then_download",
        "candidate_side_reboot": False,
        "minimum_wait_after_candidate_odin_disconnect_sec": 60,
        "maximum_wait_after_candidate_odin_disconnect_sec": 90,
        "primary_rollback": "magisk_boot_only",
        "fallback_rollback": "stock_boot_only_if_transfer_fails_and_download_remains",
        "fallback_result": "RECOVERY_ONLY_NO_PROOF_STOP",
        "collection_boot": "first_rooted_magisk_boot_only",
        "extra_reboot_before_collection": False,
    },
    "first_boot_collection": {
        "path": "/proc/last_kmsg",
        "read_to_eof": True,
        "repeat_reads": 2,
        "repeat_size_and_sha256_equal": True,
        "maximum_bytes": MAX_LAST_KMSG_BYTES,
        "required_markers": [observer.PHASE_PRECHECK, observer.PHASE_FINAL],
        "ordering": "embedded_sequence",
    },
    "classification": {
        "exact_pair": "PASS_STAGE_A_AND_CROSS_SESSION_RETENTION",
        "both_absent": "NO_PROOF_STAGE_A_VS_TRANSITION_UNRESOLVED_STOP",
        "partial_or_integrity_error": "FAIL_STOP",
        "unreadable_truncated_or_unstable": "UNAVAILABLE_STOP",
    },
    "provenance": {
        "positive": (
            "first rollback sec_log_buf probe snapshots reserved ring before current "
            "boot early-log pull and hook registration"
        ),
        "manual_download_recovery": "LIVE_PRECEDENT_REPEATED",
        "android_origin_ring_survival": "LIVE_PRECEDENT_M29",
        "direct_pid1_origin_ring_survival": "UNVERIFIABLE_UNTIL_POSITIVE",
        "negative_is_causal": False,
    },
    "required_before_candidate": {
        "same_transition_stock_origin_positive_control": True,
        "same_marker_encoder_and_classifier": True,
        "same_first_boot_double_read": True,
        "fresh_sha_pinned_exception": True,
        "explicit_operator_ack": True,
    },
    "rejected_transitions": {
        "candidate_reboot_download": "M4T0_M4T1_NO_SELF_DOWNLOAD",
        "cold_power_cycle": "MAXIMUM_RESERVED_MEMORY_LOSS_RISK",
        "panic_watchdog_sec_debug": "OBSERVER_POLICY_AND_BEHAVIOR_CONFOUND",
    },
    "candidate_source_authorized": False,
    "live_authorized": False,
}
TRANSITION_SHA256 = hashlib.sha256(observer.canonical_json(TRANSITION_CORE)).hexdigest()
PINNED_TRANSITION_SHA256 = "ad5a99b06e30e300fceb0e4fe882c001d1a4c131ce4a7e2b16b65af5bf2a12f1"
if TRANSITION_SHA256 != PINNED_TRANSITION_SHA256:
    raise RuntimeError(
        "transition contract changed without an explicit pin update: "
        f"{TRANSITION_SHA256} != {PINNED_TRANSITION_SHA256}"
    )


class TransitionError(ValueError):
    pass


def repo_root() -> Path:
    return observer.repo_root()


def sha256_file(path: Path) -> str:
    return observer.sha256_file(path)


def _tar_members(path: Path) -> list[str]:
    result = subprocess.run(
        ["tar", "-tf", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise TransitionError(f"tar member inspection failed: {result.stderr.strip()}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _verify_rollback(
    path: Path, expected_sha256: str, root: Path
) -> dict[str, Any]:
    if not path.is_file():
        raise TransitionError(f"rollback AP missing: {path}")
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise TransitionError(f"rollback AP SHA256 mismatch: {path}: {actual}")
    members = _tar_members(path)
    if members != ["boot.img.lz4"]:
        raise TransitionError(f"rollback AP is not boot-only: {path}: {members}")
    return {
        "path": str(path.relative_to(root)),
        "sha256": actual,
        "members": members,
    }


def _verify_historical_reports(root: Path) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for relative, expected in HISTORICAL_REPORTS.items():
        path = root / relative
        if sha256_file(path) != expected["sha256"]:
            raise TransitionError(f"historical report SHA256 mismatch: {relative}")
        text = path.read_text(encoding="utf-8")
        missing = [token for token in expected["tokens"] if token not in text]
        if missing:
            raise TransitionError(f"historical report tokens missing: {relative}: {missing}")
        verified.append(
            {
                "path": str(relative),
                "sha256": expected["sha256"],
                "required_tokens": list(expected["tokens"]),
            }
        )
    return verified


def classify_first_boot_capture(
    first: bytes,
    second: bytes,
    expectation: observer.MarkerExpectation,
    *,
    first_eof: bool,
    second_eof: bool,
) -> dict[str, Any]:
    if not first_eof or not second_eof:
        return {"verdict": "UNAVAILABLE_STOP", "reason": "read-not-to-eof"}
    if not first or len(first) > MAX_LAST_KMSG_BYTES:
        return {"verdict": "UNAVAILABLE_STOP", "reason": "first-size-invalid"}
    if first != second:
        return {"verdict": "UNAVAILABLE_STOP", "reason": "double-read-mismatch"}
    marker_result = observer.classify_marker_snapshot(
        "retention", first, expectation
    )
    if marker_result["pass"]:
        return {
            "verdict": "PASS_STAGE_A_AND_CROSS_SESSION_RETENTION",
            "reason": "exact-precheck-final-pair",
            "marker_result": marker_result,
        }
    if (
        not marker_result["current_run_markers"]
        and not marker_result["current_run_issues"]
        and f"run={expectation.run_id}".encode("ascii") not in first
    ):
        return {
            "verdict": "NO_PROOF_STAGE_A_VS_TRANSITION_UNRESOLVED_STOP",
            "reason": "current-run-markers-absent",
            "marker_result": marker_result,
        }
    return {
        "verdict": "FAIL_STOP",
        "reason": "partial-or-integrity-error",
        "marker_result": marker_result,
    }


def build_selection(root: Path) -> dict[str, Any]:
    observer_design = observer.build_design(root)
    if observer_design["contract_sha256"] != OBSERVER_CONTRACT_SHA256:
        raise TransitionError("observer contract pin mismatch")
    if not ODIN4.is_file() or not ODIN4.stat().st_mode & 0o111:
        raise TransitionError(f"Odin4 executable missing: {ODIN4}")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": "HOST_TRANSITION_SELECTION_PASS_NO_LIVE",
        "transition_sha256": TRANSITION_SHA256,
        "transition": TRANSITION_CORE,
        "observer_contract": {
            "schema": observer.SCHEMA,
            "sha256": OBSERVER_CONTRACT_SHA256,
        },
        "rollback": {
            "primary": _verify_rollback(
                root / MAGISK_ROLLBACK_AP, MAGISK_ROLLBACK_AP_SHA256, root
            ),
            "primary_boot_sha256": MAGISK_ROLLBACK_BOOT_SHA256,
            "fallback": _verify_rollback(
                root / STOCK_ROLLBACK_AP, STOCK_ROLLBACK_AP_SHA256, root
            ),
            "fallback_boot_sha256": STOCK_ROLLBACK_BOOT_SHA256,
            "odin4": str(ODIN4),
        },
        "historical_evidence": _verify_historical_reports(root),
        "next": "design stock-origin same-transition positive control; no candidate yet",
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "candidate_created": False,
            "exception_created": False,
            "live_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    selection = build_selection(root)
    rendered = json.dumps(selection, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        if args.check:
            if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
                raise SystemExit(f"generated selection is stale: {output}")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
