#!/usr/bin/env python3
"""Create one P2.94 candidate intent through the versioned contract."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Iterator

import s22plus_fyg8_p292_candidate_intent as base
import s22plus_fyg8_p294_source_contract as p294


SCHEMA = p294.INTENT_SCHEMA
PREIMAGE_SCHEMA = p294.PREIMAGE_SCHEMA
VERDICT = p294.INTENT_VERDICT
RUN_ID_DOMAIN = p294.RUN_ID_DOMAIN
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p294/intent")
TARGET = base.TARGET
PROFILE = p294.PROFILE
PROFILE_NUMBER = base.PROFILE_NUMBER
SUPPORTED_PROFILES = base.SUPPORTED_PROFILES
DEFAULT_SOURCE = p294.DRIVER_SOURCE_REFERENCE
DEFAULT_BASE_PATCH = base.DEFAULT_BASE_PATCH
DEFCONFIG = base.DEFCONFIG
BASE_FILES = {**base.BASE_FILES, **p294.DRIVER_SOURCE_RECEIPTS}
IntentError = base.IntentError
_INHERITED_BUILD_PATCH = base.build_patch

RUN_ID_DOMAINS = {**base.RUN_ID_DOMAINS, "E2": RUN_ID_DOMAIN}
SUPERSEDED_FOR_NEW_CANDIDATES = {
    **base.SUPERSEDED_FOR_NEW_CANDIDATES,
    base.p292.CONTRACT_ID: p294.CONTRACT_ID,
}


def build_patch(
    base_patch: bytes,
    run_id: bytes,
    unsat_tag: bytes,
    profile: str = PROFILE,
) -> bytes:
    if profile != p294.PROFILE:
        raise IntentError(f"unsupported P2.94 candidate profile: {profile}")
    replacements = (
        (
            (
                "+CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="
                f'"{p294.SOURCE_CHECK_RUN_ID.hex()}"'
            ).encode("ascii"),
            (
                "+CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="
                f'"{run_id.hex()}"'
            ).encode("ascii"),
        ),
        (
            (
                "+CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX="
                f'"{p294.SOURCE_CHECK_UNSAT_TAG.hex()}"'
            ).encode("ascii"),
            (
                "+CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX="
                f'"{unsat_tag.hex()}"'
            ).encode("ascii"),
        ),
    )
    old_counts = tuple(base_patch.count(old) for old, _new in replacements)
    if old_counts == (0, 0):
        return _INHERITED_BUILD_PATCH(base_patch, run_id, unsat_tag, profile)
    if old_counts != (1, 1):
        raise IntentError("P2.94 candidate config source binding differs")
    value = base_patch
    for old, new in replacements:
        value = value.replace(old, new)
    return value


def audit_patch(
    source: Path,
    patch: bytes,
    run_id: bytes,
    unsat_tag: bytes,
    profile: str = PROFILE,
) -> dict[str, Any]:
    """Verify all five P2.94 patch targets against one exact source tree."""
    if source.is_symlink() or not source.is_dir():
        raise IntentError("FYG8 source tree is missing or indirect")
    targets = re.findall(
        rb"^diff --git a/(\S+) b/\1$", patch, flags=re.MULTILINE
    )
    decoded_targets = [value.decode("ascii") for value in targets]
    if (
        set(decoded_targets) != set(BASE_FILES)
        or len(decoded_targets) != len(BASE_FILES)
    ):
        raise IntentError(f"candidate patch targets changed: {decoded_targets}")
    config_lines = [
        "CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE=y",
        f"CONFIG_S22PLUS_FYG8_E1_PROFILE={base.base.profile_number(profile)}",
        f'CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="{run_id.hex()}"',
        f'CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX="{unsat_tag.hex()}"',
    ]
    text = patch.decode("ascii")
    if any(text.count(f"+{line}") != 1 for line in config_lines):
        raise IntentError("candidate config binding cardinality changed")

    with tempfile.TemporaryDirectory(prefix="s22-p294-intent-") as temporary:
        tree = Path(temporary)
        for relative, expected in BASE_FILES.items():
            source_path = source / relative
            data = base.base.p233.read_direct(source_path, f"base {relative}")
            if hashlib.sha256(data).hexdigest() != expected:
                raise IntentError(f"base source identity mismatch: {relative}")
            target = tree / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        completed = subprocess.run(
            ["patch", "--batch", "--forward", "-p1"],
            cwd=tree,
            input=patch,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=30,
        )
        if completed.returncode != 0:
            detail = completed.stdout.decode("utf-8", "replace")[-2000:]
            raise IntentError(
                f"candidate patch does not apply cleanly: {detail}"
            )
        patched_files = {
            relative: hashlib.sha256((tree / relative).read_bytes()).hexdigest()
            for relative in sorted(BASE_FILES)
        }
    return {
        "targets": sorted(decoded_targets),
        "base_files": dict(sorted(BASE_FILES.items())),
        "patched_files": patched_files,
        "config_lines": config_lines,
        "clean_apply": True,
        "verified": True,
    }


def candidate_contract_ids() -> tuple[str, ...]:
    return tuple(
        contract_id
        for contract_id in base.base.source_contracts.contract_ids()
        if contract_id not in SUPERSEDED_FOR_NEW_CANDIDATES
    )


def selected_source_contract_for_candidate(
    source_contract_id: str | None,
    profile: str,
):
    replacement = SUPERSEDED_FOR_NEW_CANDIDATES.get(source_contract_id)
    if replacement is not None:
        raise IntentError(
            f"source contract {source_contract_id!r} is superseded for new "
            f"candidates by {replacement!r}"
        )
    try:
        return base.base.source_contracts.select(source_contract_id, profile)
    except base.base.source_contracts.SourceContractSelectionError as exc:
        raise IntentError(str(exc)) from exc


@contextmanager
def _base_context() -> Iterator[None]:
    replacements = {
        "SCHEMA": SCHEMA,
        "PREIMAGE_SCHEMA": PREIMAGE_SCHEMA,
        "VERDICT": VERDICT,
        "RUN_ID_DOMAIN": RUN_ID_DOMAIN,
        "RUN_ID_DOMAINS": RUN_ID_DOMAINS,
        "PROFILE": PROFILE,
        "PROFILE_NUMBER": PROFILE_NUMBER,
        "DEFAULT_OUT": DEFAULT_OUT,
        "DEFAULT_SOURCE": DEFAULT_SOURCE,
        "BASE_FILES": BASE_FILES,
        "SUPERSEDED_FOR_NEW_CANDIDATES": SUPERSEDED_FOR_NEW_CANDIDATES,
        "candidate_contract_ids": candidate_contract_ids,
        "selected_source_contract_for_candidate": selected_source_contract_for_candidate,
        "build_patch": build_patch,
        "audit_patch": audit_patch,
    }
    inherited = base.base
    previous = {name: getattr(inherited, name) for name in replacements}
    for name, value in replacements.items():
        setattr(inherited, name, value)
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(inherited, name, value)


def _configure() -> None:
    """Compatibility hook for downstream adapters."""


def __getattr__(name: str):
    return getattr(base, name)


def create(args):  # noqa: ANN001, ANN201
    with _base_context():
        return base.base.create(args)


def parse_args(argv: list[str] | None = None):
    with _base_context():
        return base.base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    with _base_context():
        return base.base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
