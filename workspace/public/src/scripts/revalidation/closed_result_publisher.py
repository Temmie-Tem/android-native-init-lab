"""Publish one canonical result for an already-CLOSED Process-v2 F1 run.

Four consecutive S22+ runs (P3.23 through P3.26) closed on the device and then
stopped in the ordinary host publisher because their canonical
``live-result.json`` exceeded the shared 32 KiB record bound.  Each was resolved
by writing a fresh run-specific finalizer, and those four copies drifted: the
read-only journal repair that P3.24's review required reached three of them and
not the fourth.

This module generalises that pattern once.  It is deliberately *not* a wider
record bound.  The live path keeps ``MAX_RECORD`` at 32 KiB and never reaches
this module; only a canonical result reconstructed from an already-CLOSED run
may be published here, under a separate ``MAX_CLOSED_RESULT`` bound, and only
when 32 KiB genuinely was not enough.

Invariants, each enforced below:

* the live bound is untouched, and the dependency runs one way only - this
  module imports the Process-v2 runtime, and nothing in the runtime imports it;
* nothing is reconstructed or published until the journal reads ``CLOSED``;
* a result that would have fit inside the live bound is refused, so this path
  cannot become the default;
* the journal is only ever read through a non-repairing view;
* the run, its evidence and the verifier sources are pinned by exact size and
  digest, and any drift stops the run fail-closed;
* the result is derived deterministically from stored state and never
  reinterpreted;
* publication is atomic, exclusive, single-link and mode 0400;
* ``audit_only`` publishes nothing at all.

There is no device, ADB, USB, Odin, backend, transfer, rollback or replay path
in this module, and it creates no D0, D1, F1, recovery or live authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REVALIDATION = Path(__file__).resolve().parent

#: Publication bound for a canonical closed result.  This is intentionally a
#: different constant from the runtime's ``MAX_RECORD``; widening that one would
#: also widen every live and intermediate record, which is not the intent.
MAX_CLOSED_RESULT = 64 * 1024

#: The live bound this module refuses to replace.  Checked against the loaded
#: runtime so a runtime change cannot silently move it.
CORE_MAX_RECORD = 32 * 1024


class PublicationError(RuntimeError):
    """A pinned identity, ordering or bound requirement was not met."""


@dataclass(frozen=True)
class Artifact:
    """One file pinned by exact size and digest."""

    size: int
    sha256: str


@dataclass(frozen=True)
class JournalShape:
    """The exact terminal shape the run's journal must already have."""

    records: int
    terminal_sequence: int
    terminal_sha256: str
    state: str = "CLOSED"


@dataclass(frozen=True)
class TransferShape:
    """Transfer attempts that must exist, and attempts that must not."""

    names: Sequence[str] = ("candidate", "rollback")
    attempt: int = 1
    classification: str = "odin_transfer_completed"
    forbid_attempts: Sequence[int] = (2,)


@dataclass(frozen=True)
class ProjectionSpec:
    """One derived projection the run must already carry, checked by value."""

    method: str
    expected: Mapping[str, Any]
    state_key: str


@dataclass(frozen=True)
class ClosedResultSpec:
    """Everything that is specific to one closed run.

    Every field here is data about a run that has already finished.  The
    publication procedure itself lives in this module and is shared, so a
    correction to it reaches every run instead of one copy.
    """

    label: str
    schema: str
    root: Path
    manifest: Path
    run_dir: Path
    binding_sha256: str
    bundle_sha256: str
    journal: JournalShape
    state: Artifact
    result: Artifact
    verdict: str
    outcome: str
    audit_verdict: str
    exact_files: Mapping[str, tuple[Path, int, str]]
    state_expectations: Mapping[str, Any] = field(default_factory=dict)
    transfers: TransferShape = TransferShape()
    projection: ProjectionSpec | None = None
    lane_shim: Callable[[Any], Any] | None = None

    @property
    def state_path(self) -> Path:
        return self.run_dir / "live-state.json"

    @property
    def result_path(self) -> Path:
        return self.run_dir / "live-result.json"


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _metadata(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_mode,
        value.st_ino,
        value.st_dev,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
    )


def stable_bytes(path: Path, label: str, maximum: int = 1024 * 1024) -> bytes:
    """Read one direct, single-link regular file whose identity did not move."""

    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise PublicationError(f"{label} is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or len(payload) != before.st_size
        or len(payload) > maximum
        or _metadata(before) != _metadata(inside)
        or _metadata(before) != _metadata(after)
    ):
        raise PublicationError(f"{label} is not one stable direct file")
    return payload


def canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"


def verify_exact_files(spec: ClosedResultSpec) -> None:
    """Stop unless every pinned input still has its exact size and digest.

    This is what makes a later change to a shared verifier source, or to the
    run's own retained evidence, stop this module rather than let it publish
    against something other than what the run closed on.
    """

    for label, (path, size, digest) in spec.exact_files.items():
        payload = stable_bytes(path, label)
        if len(payload) != size or sha256(payload) != digest:
            raise PublicationError(f"{label} identity differs")


def load_runtime(spec: ClosedResultSpec) -> tuple[Any, Any]:
    verify_exact_files(spec)
    sys.path.insert(0, str(REVALIDATION))
    import device_action_f1_live_v2 as live  # noqa: PLC0415
    import device_action_f1_v2 as core  # noqa: PLC0415

    if (
        Path(live.__file__).resolve(strict=True) != spec.exact_files["live_source"][0]
        or Path(core.__file__).resolve(strict=True) != spec.exact_files["core_source"][0]
        or live.core is not core
        or core.MAX_RECORD != CORE_MAX_RECORD
    ):
        raise PublicationError("loaded Process-v2 runtime identity differs")
    return live, core


def read_only_journal(core: Any, path: Path, binding: str) -> Any:
    """Open a journal without the repairing ``reopen`` path.

    P3.24's review found that auditing through the common repairing reopen
    rewrote identical journal-head bytes and changed the retained evidence's
    inode and timestamps.  Construction plus ``records()`` reads the same state
    and writes nothing.
    """

    journal = core.Journal(path, binding)
    journal.records()
    return journal


@contextmanager
def _read_only_journals(core: Any):
    """Force every ``Journal.reopen`` inside the block to be non-repairing."""

    original = core.Journal.__dict__["reopen"]

    def replacement(cls: Any, path: Path, binding: str) -> Any:
        del cls
        return read_only_journal(core, path, binding)

    core.Journal.reopen = classmethod(replacement)
    try:
        yield
    finally:
        core.Journal.reopen = original


@contextmanager
def _stored_state(live: Any, state: Mapping[str, Any]):
    original = live._state  # noqa: SLF001
    live._state = lambda _prepared: state  # noqa: SLF001
    try:
        yield
    finally:
        live._state = original  # noqa: SLF001


@contextmanager
def _stored_lane(spec: ClosedResultSpec, live: Any):
    if spec.lane_shim is None:
        yield
        return
    restore = spec.lane_shim(live)
    try:
        yield
    finally:
        restore()


def reconstruct(spec: ClosedResultSpec) -> tuple[dict[str, Any], bytes, Any, Any, dict[str, Any]]:
    """Rebuild the canonical result of one already-CLOSED run.

    Nothing here interprets the run.  Every value is read back from what the run
    already durably recorded, and any disagreement stops the module.
    """

    if spec.run_dir.is_symlink() or spec.run_dir.absolute() != spec.run_dir.resolve(strict=True):
        raise PublicationError(f"exact {spec.label} run directory is indirect")
    live, core = load_runtime(spec)

    with _stored_lane(spec, live):
        prepared = live.load_prepared(spec.root, spec.manifest, spec.run_dir)
        if (
            prepared.binding_sha256 != spec.binding_sha256
            or prepared.bundle.sha256 != spec.bundle_sha256
            or prepared.run_dir != spec.run_dir
        ):
            raise PublicationError(f"prepared {spec.label} binding differs")

        journal = read_only_journal(core, spec.run_dir / "transaction", spec.binding_sha256)
        records = journal.records()
        terminal = records[-1] if records else {}
        if (
            journal.state() != spec.journal.state
            or len(records) != spec.journal.records
            or terminal.get("sequence") != spec.journal.terminal_sequence
            or terminal.get("state") != spec.journal.state
            or terminal.get("record_sha256") != spec.journal.terminal_sha256
        ):
            raise PublicationError(
                f"{spec.label} journal is not the exact "
                f"{spec.journal.state}/{spec.journal.records} run"
            )

        for name in spec.transfers.names:
            for forbidden in spec.transfers.forbid_attempts:
                for suffix in ("start", "result"):
                    path = spec.run_dir / f"{name}-attempt-{forbidden:02d}.{suffix}.json"
                    if path.exists() or path.is_symlink():
                        raise PublicationError(f"a transfer attempt {forbidden} exists")
        for name in spec.transfers.names:
            record = live._validate_transfer_result(  # noqa: SLF001
                prepared, name, spec.transfers.attempt
            )
            if record.get("classification") != spec.transfers.classification:
                raise PublicationError(f"{name} transfer differs")

        state_payload = stable_bytes(
            spec.state_path, f"{spec.label} live state", MAX_CLOSED_RESULT
        )
        if len(state_payload) != spec.state.size or sha256(state_payload) != spec.state.sha256:
            raise PublicationError(f"{spec.label} live state identity differs")
        state = live._state(prepared)  # noqa: SLF001
        if canonical(state) != state_payload:
            raise PublicationError(f"{spec.label} live state is not canonical")
        for key, expected in spec.state_expectations.items():
            if state.get(key) != expected:
                raise PublicationError(f"{spec.label} CLOSED live state differs at {key}")

        if spec.projection is not None:
            projection = getattr(live, spec.projection.method)(prepared, state)
            if not isinstance(projection, dict):
                raise PublicationError(f"{spec.label} projection is not a mapping")
            for key, expected in spec.projection.expected.items():
                if projection.get(key) != expected:
                    raise PublicationError(f"{spec.label} projection differs at {key}")
            if state.get(spec.projection.state_key) != projection:
                raise PublicationError(f"{spec.label} projection is not the stored one")

        verdict, outcome = live._closed_terminal_classification(prepared)  # noqa: SLF001
        if verdict != spec.verdict or outcome != spec.outcome:
            raise PublicationError(f"{spec.label} terminal classification differs")

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
        with _read_only_journals(core), _stored_state(live, state):
            live.validate_live_result(value, prepared)
        payload = canonical(value)

    if (
        len(payload) != spec.result.size
        or sha256(payload) != spec.result.sha256
        or len(payload) > MAX_CLOSED_RESULT
    ):
        raise PublicationError(f"{spec.label} reconstructed result identity differs")
    if len(payload) <= CORE_MAX_RECORD:
        raise PublicationError(
            f"{spec.label} result fits the live bound and must not use this path"
        )
    verify_exact_files(spec)
    return value, payload, live, prepared, state


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish(spec: ClosedResultSpec, payload: bytes) -> None:
    """Write the canonical result exactly once, atomically, read-only."""

    if len(payload) != spec.result.size or sha256(payload) != spec.result.sha256:
        raise PublicationError(f"{spec.label} result publication identity differs")
    target = spec.result_path
    if target.exists() or target.is_symlink():
        raise PublicationError(f"{spec.label} live result already exists")
    temporary = target.with_name(f".{target.name}.{os.getpid()}.{time.time_ns()}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o400,
    )
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            try:
                written = os.write(descriptor, payload[offset:])
            except InterruptedError:
                continue
            if written <= 0:
                raise PublicationError(f"{spec.label} result write made no progress")
            offset += written
        os.fsync(descriptor)
        complete = os.fstat(descriptor)
        if (
            not stat.S_ISREG(complete.st_mode)
            or stat.S_IMODE(complete.st_mode) != 0o400
            or complete.st_nlink != 1
            or complete.st_size != len(payload)
        ):
            raise PublicationError(f"{spec.label} result temporary identity differs")
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, target)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise PublicationError(f"{spec.label} result could not be placed") from exc
    finally:
        temporary.unlink(missing_ok=True)
    _fsync_dir(target.parent)
    if stable_bytes(target, f"published {spec.label} result", MAX_CLOSED_RESULT) != payload:
        raise PublicationError(f"published {spec.label} result differs")


def finalize(spec: ClosedResultSpec, *, audit_only: bool) -> dict[str, Any]:
    """Reconstruct, and publish only when not auditing."""

    value, payload, _live, _prepared, _state = reconstruct(spec)
    already_present = spec.result_path.exists() or spec.result_path.is_symlink()
    if already_present:
        retained = stable_bytes(
            spec.result_path, f"existing {spec.label} live result", MAX_CLOSED_RESULT
        )
        if retained != payload:
            raise PublicationError(f"existing {spec.label} live result differs")
        if not audit_only:
            raise PublicationError(f"{spec.label} live result is already published")
    elif not audit_only:
        publish(spec, payload)
    return {
        "schema": spec.schema,
        "verdict": spec.audit_verdict if audit_only else spec.verdict,
        "run_dir": str(spec.run_dir),
        "result": {
            "path": str(spec.result_path),
            "size": len(payload),
            "sha256": sha256(payload),
            "formal_verdict": value["verdict"],
            "outcome_class": value["outcome_class"],
            "current_state": value["current_state"],
            "recovery_required": value["recovery_required"],
        },
        "created": not audit_only,
        "already_present": already_present,
        "device_contact": False,
        "adb_invoked": False,
        "usb_revalidated": False,
        "odin_invoked": False,
        "candidate_transfer": False,
        "rollback_transfer": False,
        "live_authorized": False,
    }


def main(spec: ClosedResultSpec, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"Publish the {spec.label} closed result.")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = finalize(spec, audit_only=args.audit_only)
    except (PublicationError, OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {"schema": spec.schema, "verdict": "FAIL_CLOSED", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
