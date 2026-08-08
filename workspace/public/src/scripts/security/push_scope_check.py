#!/usr/bin/env python3
"""Report which commits in a push range touch review-triggering paths.

`AGENTS.md` "Review Rules" requires one independent review when a common or
target contract, an F1 runner, a schema, transfer/archive/recovery machinery, a
boundary, or a hazard changes. Routine work — verifiers, packagers, decoders,
static checkers, auditors, documentation — does not trigger it.

This tells you which of those a push would carry. It does **not** decide whether
the review happened, so it reports and exits 0. Blocking here would only teach
`--no-verify`, which would also skip the identifier boundary check that must
never be bypassed.

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


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[-1].strip(), file=sys.stderr)
        return 2
    revision_range = argv[1]
    root = repo_root()

    carried = commits(root, revision_range)
    paths = changed_paths(root, revision_range)

    hits: list[tuple[str, str]] = []
    for path in paths:
        for pattern, reason in TRIGGERS:
            if pattern in path:
                hits.append((path, reason))
                break

    print(f"push scope: {len(carried)} commit(s), {len(paths)} file(s)")
    for line in carried:
        print(f"  {line}")

    if not hits:
        print("no review-triggering paths in this range")
        return 0

    print()
    print(f"REVIEW TRIGGER — {len(hits)} path(s) require one independent review")
    print("(AGENTS.md, Review Rules)")
    for path, reason in sorted(hits):
        print(f"  {path}")
        print(f"      {reason}")
    print()
    print("Reporting only; this does not block the push.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
