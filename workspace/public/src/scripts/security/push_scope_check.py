#!/usr/bin/env python3
"""Report which commits in a push range touch review-triggering paths.

`AGENTS.md` "Review Rules" requires one independent review when a common or
target contract, an F1 runner, a schema, transfer/archive/recovery machinery, a
boundary, or a hazard changes. Routine work — verifiers, packagers, decoders,
static checkers, auditors, documentation — does not trigger it.

This also counts commits with an empty body. A body-less commit is not itself
an `AGENTS.md` violation — the required prose report can live under
`docs/reports/` instead — but a push where most commits carry no narrative at
all is harder for a reviewer to audit at the commit level, so it is worth
surfacing.

Neither check decides whether a review happened or a report was written, so
this reports and exits 0. Blocking here would only teach `--no-verify`, which
would also skip the identifier boundary check that must never be bypassed.

Usage:
    push_scope_check.py <range>          e.g. origin/main..HEAD, or <remote_sha>..<local_sha>
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Each pattern maps to a clause of the AGENTS.md review-trigger list. Keep the
# reason text: it is what makes a hit actionable rather than noise.
TRIGGERS: tuple[tuple[str, str], ...] = (
    ("AGENTS.md", "the binding safety contract itself"),
    ("docs/operations/DEVICE_ACTION_", "the common device-action contract"),
    ("docs/operations/targets/", "a target contract"),
    ("device_action_", "F1 runner and transfer/evidence machinery"),
    ("_recovery", "recovery machinery"),
    ("recovery_", "recovery machinery"),
    ("_schema", "a schema"),
    ("schema_", "a schema"),
)


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(f"could not locate repo root from {current}")


def changed_paths(root: Path, revision_range: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", revision_range],
        cwd=root, capture_output=True, text=True, check=True,
    )
    return [line for line in result.stdout.split("\n") if line.strip()]


def commits(root: Path, revision_range: str) -> list[str]:
    result = subprocess.run(
        ["git", "log", "--format=%h %s", revision_range],
        cwd=root, capture_output=True, text=True, check=True,
    )
    return [line for line in result.stdout.split("\n") if line.strip()]


def empty_body_commits(root: Path, revision_range: str) -> list[str]:
    """Return "<short-hash> <subject>" for each commit with no body text.

    Checks one commit at a time with `git show -s`, rather than one combined
    `git log` with a custom field separator, because a subject or body can
    itself contain the separator or a newline.
    """
    hashes = subprocess.run(
        ["git", "log", "--format=%H", revision_range],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout.split()

    empty: list[str] = []
    for full_hash in hashes:
        header = subprocess.run(
            ["git", "show", "-s", "--format=%h %s", full_hash],
            cwd=root, capture_output=True, text=True, check=True,
        ).stdout.strip()
        body = subprocess.run(
            ["git", "show", "-s", "--format=%b", full_hash],
            cwd=root, capture_output=True, text=True, check=True,
        ).stdout
        if not body.strip():
            empty.append(header)
    return empty


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[-1].strip(), file=sys.stderr)
        return 2
    revision_range = argv[1]
    root = repo_root()

    carried = commits(root, revision_range)
    paths = changed_paths(root, revision_range)
    empty_bodies = empty_body_commits(root, revision_range)

    hits: list[tuple[str, str]] = []
    for path in paths:
        for pattern, reason in TRIGGERS:
            if pattern in path:
                hits.append((path, reason))
                break

    print(f"push scope: {len(carried)} commit(s), {len(paths)} file(s)")
    for line in carried:
        print(f"  {line}")

    if hits:
        print()
        print(f"REVIEW TRIGGER — {len(hits)} path(s) require one independent review")
        print("(AGENTS.md, Review Rules)")
        for path, reason in sorted(hits):
            print(f"  {path}")
            print(f"      {reason}")

    if empty_bodies and carried:
        print()
        print(
            f"COMMIT BODY WARNING — {len(empty_bodies)}/{len(carried)} commit(s) "
            "have no body text"
        )
        print(
            "(informational; not an AGENTS.md requirement — check that the "
            "narrative evidence exists somewhere, e.g. docs/reports/)"
        )
        for line in empty_bodies:
            print(f"  {line}")

    if not hits and not empty_bodies:
        print("no review-triggering paths and no empty-body commits in this range")

    print()
    print("Reporting only; this does not block the push.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
