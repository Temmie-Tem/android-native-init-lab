#!/usr/bin/env python3
"""Close the already-rolled-back P3.31 run without another device action.

The retained journal is already CLOSED after exactly one candidate and one
rollback transfer, and the stored final health is rooted FYG8 Android.  The
ordinary publisher stopped because P331's supplemental Carrier validation
fell through into the inherited P328 branch.  This finalizer changes only that
host-side dispatch while reconstructing the missing canonical live result.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent
MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p331_process_v2_ready_3.json"
)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "p331-ready3-prepared-20260903-1"
)
LIVE_SOURCE = REVALIDATION / "device_action_f1_live_v2.py"
CORE_SOURCE = REVALIDATION / "device_action_f1_v2.py"
EXPECTED_BINDING = "ced2c5985b5a01ff2fde46a2447856dfa978300334a7b16c24295a499ad0b68b"
EXPECTED_BUNDLE = "ee288a39967f20563e49307d1d0f5a8ccee9c9e1ee2af50fe50f0e537e98487e"
EXPECTED_FILES = {
    "manifest": (MANIFEST, 6_159, "7b64f82d6783ce6cdc22d14a504abba211d9992a4a09a36c874aac184ff1fca2"),
    "live_source": (LIVE_SOURCE, 442_942, "badee11c3308daba6dfc0bfb224c83535a28429de92522189fcda96cab71c862"),
    "core_source": (CORE_SOURCE, 124_903, "1f03903c0520ffa74bac1554c607400e26b724d44e6a74897a90786bac59fe18"),
    "prepared": (RUN_DIR / "prepared.json", 19_900, "e8139f3343db2b5217a9526a0cba2248dabcc95a058256aa33486d8da7dcd7c0"),
    "state": (RUN_DIR / "live-state.json", 12_605, "e17a3e03a0132d910ec8921a7a93c4d1d5ad56bec1e0ea15bd63c7081715d1a5"),
    "journal_head": (RUN_DIR / "transaction/journal-head.json", 276, "b4738a277dd08bfb1a25b867d8af8bf20acf1025c06e318f7c5134de1ceee8d7"),
    "candidate_result": (RUN_DIR / "candidate-attempt-01.result.json", 2_079, "9cbef6d3084a8ee03d8ff863090000fabd273873403621d117389b5c0efa488d"),
    "rollback_result": (RUN_DIR / "rollback-attempt-01.result.json", 2_030, "55d957f43f08a3a837627409870757e2972ad30e77d716f53ef75caf1994abd5"),
    "candidate_observer": (RUN_DIR / "candidate-observer.json", 6_733, "9af34b3d821314c70d97b754137f788e7a20fc15cf285911eea7b099c9221094"),
}
EXPECTED_RESULT = {
    "size": 15_182,
    "sha256": "172952c9ef7f0efb08dc516dd15a2b2565044c1d2911b82f3625d984e989acdf",
}
SCHEMA = "s22plus_fyg8_p331_closed_result_finalizer_v1"
AUDIT_VERDICT = "PASS_P331_CLOSED_RESULT_RECONSTRUCTED_HOST_ONLY"
PUBLISH_VERDICT = "PASS_P331_CLOSED_RESULT_PUBLISHED_HOST_ONLY"


class FinalizerError(RuntimeError):
    pass


def _stable(path: Path, label: str, maximum: int = 1024 * 1024) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise FinalizerError(f"{label} is unavailable") from exc
    identity = lambda item: (
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_nlink,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or len(payload) != before.st_size
        or len(payload) > maximum
        or identity(before) != identity(inside)
        or identity(before) != identity(after)
    ):
        raise FinalizerError(f"{label} is not one stable direct file")
    return payload


def _verify_inputs() -> None:
    for label, (path, size, digest) in EXPECTED_FILES.items():
        payload = _stable(path, label)
        if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
            raise FinalizerError(f"{label} identity differs")
    result_path = RUN_DIR / "live-result.json"
    if result_path.exists() or result_path.is_symlink():
        payload = _stable(result_path, "existing P3.31 live result")
        if {
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        } != EXPECTED_RESULT:
            raise FinalizerError("existing P3.31 live result differs")


@contextmanager
def _p331_dispatch_repair(live: Any, core: Any) -> Iterator[None]:
    """Mask inherited roles only inside P331 final-observer validation."""

    original_validate = live._validate_final_observer  # noqa: SLF001
    original_reopen = core.Journal.__dict__["reopen"]

    def validate(prepared: Any, evidence: Any) -> Any:
        names = tuple(f"_p{number}_bundle" for number in range(323, 331))
        originals = {name: getattr(live, name) for name in names}
        original_acm_primary = live._acm_primary_bundle  # noqa: SLF001
        try:
            for name, function in originals.items():
                setattr(
                    live,
                    name,
                    lambda bundle, prior=function: (
                        False if live._p331_bundle(bundle) else prior(bundle)  # noqa: SLF001
                    ),
                )
            live._acm_primary_bundle = lambda bundle: (  # noqa: SLF001
                True if live._p331_bundle(bundle) else original_acm_primary(bundle)  # noqa: SLF001
            )
            return original_validate(prepared, evidence)
        finally:
            live._acm_primary_bundle = original_acm_primary  # noqa: SLF001
            for name, function in originals.items():
                setattr(live, name, function)

    live._validate_final_observer = validate  # noqa: SLF001
    core.Journal.reopen = classmethod(
        lambda cls, run_dir, binding: cls(run_dir, binding)
    )
    try:
        yield
    finally:
        live._validate_final_observer = original_validate  # noqa: SLF001
        core.Journal.reopen = original_reopen


def reconstruct() -> tuple[dict[str, Any], bytes, Any]:
    _verify_inputs()
    if str(REVALIDATION) not in sys.path:
        sys.path.insert(0, str(REVALIDATION))
    import device_action_f1_live_v2 as live  # noqa: PLC0415
    import device_action_f1_v2 as core  # noqa: PLC0415

    if Path(live.__file__).resolve() != LIVE_SOURCE or Path(core.__file__).resolve() != CORE_SOURCE:
        raise FinalizerError("loaded Process-v2 source path differs")
    prepared = live.load_prepared(ROOT, MANIFEST, RUN_DIR)
    if prepared.binding_sha256 != EXPECTED_BINDING or prepared.bundle.sha256 != EXPECTED_BUNDLE:
        raise FinalizerError("P3.31 prepared binding differs")
    journal = core.Journal(RUN_DIR / "transaction", EXPECTED_BINDING)
    records = journal.records()
    state = live._state(prepared)  # noqa: SLF001
    if (
        journal.state() != "CLOSED"
        or len(records) != 19
        or state.get("candidate_completed") is not True
        or state.get("rollback_completed") is not True
        or state.get("final_verified") is not True
        or state.get("candidate_observer_accepted") is not False
        or state.get("candidate_observer_classification")
        != "authenticated-session-error"
        or state.get("session_count") != 1
        or state.get("successful_sessions") != 0
    ):
        raise FinalizerError("P3.31 closed no-proof state differs")
    with _p331_dispatch_repair(live, core):
        verdict, outcome = live._closed_terminal_classification(prepared)  # noqa: SLF001
        value = {
            "schema": live.LIVE_RESULT_SCHEMA,
            "adapter_version": live.ADAPTER_VERSION,
            "manifest_id": prepared.bundle.manifest["manifest_id"],
            "bundle_sha256": prepared.bundle.sha256,
            "approval_binding_sha256": prepared.binding_sha256,
            "journal": journal.receipt(),
            "current_state": journal.state(),
            "timeline": core.timeline(records),
            "live_state": state,
            "verdict": verdict,
            "outcome_class": outcome,
            "recovery_required": False,
        }
        live.validate_live_result(value, prepared)
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    return value, payload, live


def _publish(live: Any, value: dict[str, Any], payload: bytes) -> None:
    path = RUN_DIR / "live-result.json"
    if path.exists() or path.is_symlink():
        raise FinalizerError("P3.31 live result is already present")
    live._write_exclusive(path, value)  # noqa: SLF001
    retained = _stable(path, "published P3.31 live result")
    if retained != payload:
        raise FinalizerError("published P3.31 live result differs")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args(argv)
    try:
        value, payload, live = reconstruct()
        identity = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        if args.publish:
            if identity != EXPECTED_RESULT:
                raise FinalizerError("P3.31 result identity is not pinned")
            _publish(live, value, payload)
    except (FinalizerError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": PUBLISH_VERDICT if args.publish else AUDIT_VERDICT,
                "result": identity,
                "created": args.publish,
                "device_contact": False,
                "adb_invoked": False,
                "odin_invoked": False,
                "candidate_transfer": False,
                "rollback_transfer": False,
                "live_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
